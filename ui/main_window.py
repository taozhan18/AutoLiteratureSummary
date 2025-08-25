import sys
import asyncio
import threading
import traceback
import os
import webbrowser
from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QLabel, QLineEdit, QTextEdit, 
                             QProgressBar, QCheckBox, QSpinBox, QGroupBox,
                             QFormLayout, QApplication, QFileDialog, QListWidget, QMessageBox, QComboBox,
                             QListWidgetItem)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from core.processor import LiteratureProcessor
from utils.config_manager import ConfigManager
from utils.llm_client import LLMClient


class ProcessWorker(QThread):
    # 定义信号
    log_signal = pyqtSignal(str)
    progress_signal = pyqtSignal(int)
    finished_signal = pyqtSignal(list)
    error_signal = pyqtSignal(str)
    
    def __init__(self, processor, config):
        super().__init__()
        self.processor = processor
        self.config = config
        
    def run(self):
        try:
            # 初始化LLM客户端
            self.processor.initialize_llm_client(
                self.config['base_url'],
                self.config['api_key'],
                self.config['max_tokens'],
                self.config['model']
            )
            
            # 设置API请求间隔
            if 'api_request_delay' in self.config:
                self.processor.set_api_request_delay(self.config['api_request_delay'])
            
            # 扫描PDF文件
            self.log_signal.emit("正在扫描PDF文件...")
            pdf_files = self.processor.scan_pdfs(self.config['folder_path'])
            
            if not pdf_files:
                self.log_signal.emit("未找到PDF文件")
                self.finished_signal.emit([])
                return
                
            self.log_signal.emit(f"找到 {len(pdf_files)} 个PDF文件: {', '.join([os.path.basename(f) for f in pdf_files])}")
            
            # 更新文献列表
            # 这里需要通过信号传递给主线程更新UI
            
            # 处理PDF文件
            self.log_signal.emit("开始处理PDF文件...")
            
            # 创建事件循环
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            results = loop.run_until_complete(
                self.processor.process_pdfs(
                    pdf_files, 
                    self.config['concurrency'], 
                    self.config['cache_text']
                )
            )
            
            loop.close()
            
            # 处理完成
            success_count = sum(1 for r in results if r['status'] == 'success')
            skip_count = sum(1 for r in results if r['status'] == 'skipped')
            fail_count = sum(1 for r in results if r['status'] == 'failed')
            
            self.log_signal.emit(f"处理完成: 成功 {success_count}, 跳过 {skip_count}, 失败 {fail_count}")
            
            # 显示失败详情
            for result in results:
                if result['status'] == 'failed':
                    filename = os.path.basename(result['pdf_path'])
                    self.log_signal.emit(f"处理失败 - {filename}: {result['error']}")
            
            # 如果需要生成总报告
            if self.config['generate_overall_report']:
                self.log_signal.emit("正在生成总报告...")
                summaries = [r['summary'] for r in results if r['status'] in ['success', 'skipped']]
                if summaries:
                    try:
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        report = loop.run_until_complete(
                            self.processor.generate_overall_report(summaries)
                        )
                        loop.close()
                        self.log_signal.emit("总报告已生成: overall_report.md")
                    except Exception as e:
                        error_details = f"{str(e)}\n{traceback.format_exc()}"
                        self.log_signal.emit(f"生成总报告失败: {error_details}")
                else:
                    self.log_signal.emit("没有可用的摘要生成总报告")
            
            self.finished_signal.emit(results)
            
        except Exception as e:
            error_details = f"{str(e)}\n{traceback.format_exc()}"
            self.error_signal.emit(error_details)


class APIConnectionTestWorker(QThread):
    """API连接测试工作线程"""
    log_signal = pyqtSignal(str)
    result_signal = pyqtSignal(bool)
    
    def __init__(self, base_url, api_key, model):
        super().__init__()
        self.base_url = base_url
        self.api_key = api_key
        self.model = model
        
    def run(self):
        try:
            self.log_signal.emit("正在测试API连接...")
            client = LLMClient(self.base_url, self.api_key, model=self.model)
            
            # 在新事件循环中运行异步测试
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            success = loop.run_until_complete(client.test_connection())
            loop.close()
            
            if success:
                self.log_signal.emit("✓ API连接测试成功!")
                self.result_signal.emit(True)
            else:
                self.log_signal.emit("✗ API连接测试失败!")
                self.result_signal.emit(False)
                
        except Exception as e:
            error_details = f"{str(e)}\n{traceback.format_exc()}"
            self.log_signal.emit(f"✗ API连接测试异常: {error_details}")
            self.result_signal.emit(False)


class MainWindow(QMainWindow):
    # 添加日志信号，用于线程安全的日志更新
    log_signal = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self.processor = LiteratureProcessor()
        self.worker = None
        self.api_test_worker = None
        self.config_manager = ConfigManager()
        self.config = self.config_manager.load_config()
        self.init_ui()
        self.load_config_to_ui()
        # 连接日志信号到处理槽
        self.log_signal.connect(self._handle_log_signal)
        
    def _handle_log_signal(self, message):
        """处理日志信号的槽函数"""
        self.log_display.append(message)
        # 自动滚动到底部
        self.log_display.moveCursor(self.log_display.textCursor().End)
        
    def init_ui(self):
        self.setWindowTitle('文献智能总结工具')
        self.setGeometry(100, 100, 1000, 700)
        
        # 创建中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # 配置区域
        config_group = QGroupBox("配置")
        config_layout = QFormLayout()
        
        # LLM配置
        self.base_url_input = QLineEdit()
        self.api_key_input = QLineEdit()
        self.api_key_input.setEchoMode(QLineEdit.Password)
        
        # 模型选择
        self.model_combo = QComboBox()
        self.model_combo.addItems([
            "gpt-3.5-turbo",
            "gpt-4",
            "gpt-4-turbo",
            "claude-3-haiku",
            "claude-3-sonnet",
            "claude-3-opus",
            "llama3",
            "mixtral",
            "qwen-turbo",
            "qwen-plus"
        ])
        self.model_combo.setEditable(True)  # 允许用户输入自定义模型
        
        # 文件夹路径
        folder_layout = QHBoxLayout()
        self.folder_path_input = QLineEdit()
        folder_browse_btn = QPushButton("浏览")
        folder_browse_btn.clicked.connect(self.browse_folder)
        folder_layout.addWidget(self.folder_path_input)
        folder_layout.addWidget(folder_browse_btn)
        
        # 并发数
        self.concurrency_spin = QSpinBox()
        self.concurrency_spin.setMinimum(1)
        self.concurrency_spin.setMaximum(20)
        
        # 最大token数
        self.max_token_spin = QSpinBox()
        self.max_token_spin.setMinimum(100)
        self.max_token_spin.setMaximum(8192)
        
        # API请求间隔
        self.api_delay_spin = QSpinBox()
        self.api_delay_spin.setMinimum(0)
        self.api_delay_spin.setMaximum(60)
        self.api_delay_spin.setSuffix(" 秒")
        
        # 选项
        self.generate_overall_report_check = QCheckBox("生成总报告")
        self.cache_text_check = QCheckBox("保留原始文本缓存")
        
        config_layout.addRow("LLM Base URL:", self.base_url_input)
        config_layout.addRow("API Key:", self.api_key_input)
        config_layout.addRow("模型:", self.model_combo)
        config_layout.addRow("文件夹路径:", folder_layout)
        config_layout.addRow("并发数:", self.concurrency_spin)
        config_layout.addRow("最大Token数:", self.max_token_spin)
        config_layout.addRow("API请求间隔:", self.api_delay_spin)
        config_layout.addRow(self.generate_overall_report_check)
        config_layout.addRow(self.cache_text_check)
        
        config_group.setLayout(config_layout)
        main_layout.addWidget(config_group)
        
        # 控制按钮
        control_layout = QHBoxLayout()
        self.start_btn = QPushButton("开始处理")
        self.start_btn.clicked.connect(self.start_processing)
        self.stop_btn = QPushButton("停止")
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self.stop_processing)
        self.refresh_btn = QPushButton("强制刷新")
        self.refresh_btn.clicked.connect(self.refresh_processing)
        self.test_api_btn = QPushButton("测试API连接")
        self.test_api_btn.clicked.connect(self.test_api_connection)
        self.save_config_btn = QPushButton("保存配置")
        self.save_config_btn.clicked.connect(self.save_config_from_ui)
        
        control_layout.addWidget(self.start_btn)
        control_layout.addWidget(self.stop_btn)
        control_layout.addWidget(self.refresh_btn)
        control_layout.addWidget(self.test_api_btn)
        control_layout.addWidget(self.save_config_btn)
        main_layout.addLayout(control_layout)
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        main_layout.addWidget(self.progress_bar)
        
        # 日志区域
        self.log_display = QTextEdit()
        self.log_display.setReadOnly(True)
        main_layout.addWidget(QLabel("日志:"))
        main_layout.addWidget(self.log_display)
        
        # 文献列表
        self.literature_list = QListWidget()
        self.literature_list.itemDoubleClicked.connect(self.open_qa_dialog)
        main_layout.addWidget(QLabel("文献列表:"))
        main_layout.addWidget(self.literature_list)
        
        # 底部按钮
        bottom_layout = QHBoxLayout()
        self.regenerate_single_btn = QPushButton("重新生成选中文献")
        self.regenerate_single_btn.clicked.connect(self.regenerate_single)
        self.regenerate_overall_btn = QPushButton("重新生成总报告")
        self.regenerate_overall_btn.clicked.connect(self.regenerate_overall)
        self.open_folder_btn = QPushButton("打开选中文件所在文件夹")
        self.open_folder_btn.clicked.connect(self.open_selected_file_folder)
        
        bottom_layout.addWidget(self.regenerate_single_btn)
        bottom_layout.addWidget(self.regenerate_overall_btn)
        bottom_layout.addWidget(self.open_folder_btn)
        main_layout.addLayout(bottom_layout)
        
    def load_config_to_ui(self):
        """将配置加载到UI控件"""
        self.base_url_input.setText(self.config.get('base_url', ''))
        self.api_key_input.setText(self.config.get('api_key', ''))
        self.model_combo.setCurrentText(self.config.get('model', 'gpt-3.5-turbo'))
        self.folder_path_input.setText(self.config.get('folder_path', ''))
        self.concurrency_spin.setValue(self.config.get('concurrency', 5))
        self.max_token_spin.setValue(self.config.get('max_tokens', 2048))
        self.api_delay_spin.setValue(self.config.get('api_request_delay', 0))
        self.generate_overall_report_check.setChecked(self.config.get('generate_overall_report', True))
        self.cache_text_check.setChecked(self.config.get('cache_text', True))
        
    def save_config_from_ui(self):
        """从UI控件保存配置"""
        self.config['base_url'] = self.base_url_input.text()
        self.config['api_key'] = self.api_key_input.text()
        self.config['model'] = self.model_combo.currentText()
        self.config['folder_path'] = self.folder_path_input.text()
        self.config['concurrency'] = self.concurrency_spin.value()
        self.config['max_tokens'] = self.max_token_spin.value()
        self.config['api_request_delay'] = self.api_delay_spin.value()
        self.config['generate_overall_report'] = self.generate_overall_report_check.isChecked()
        self.config['cache_text'] = self.cache_text_check.isChecked()
        
        self.config_manager.save_config(self.config)
        QMessageBox.information(self, "成功", "配置已保存")
        
    def test_api_connection(self):
        """测试API连接"""
        base_url = self.base_url_input.text().strip()
        api_key = self.api_key_input.text().strip()
        model = self.model_combo.currentText().strip()
        
        if not base_url:
            QMessageBox.warning(self, "警告", "请输入LLM Base URL")
            return
            
        self.test_api_btn.setEnabled(False)
        self.test_api_btn.setText("测试中...")
        
        # 启动测试线程
        self.api_test_worker = APIConnectionTestWorker(base_url, api_key, model)
        self.api_test_worker.log_signal.connect(self.log)
        self.api_test_worker.result_signal.connect(self.api_test_finished)
        self.api_test_worker.start()
        
    def api_test_finished(self, success):
        """API测试完成回调"""
        self.test_api_btn.setEnabled(True)
        self.test_api_btn.setText("测试API连接")
        if success:
            QMessageBox.information(self, "成功", "API连接测试成功!")
        else:
            QMessageBox.critical(self, "失败", "API连接测试失败，请检查配置!")
        
    def browse_folder(self):
        folder_path = QFileDialog.getExistingDirectory(self, "选择文献文件夹")
        if folder_path:
            self.folder_path_input.setText(folder_path)
            
    def start_processing(self):
        folder_path = self.folder_path_input.text().strip()
        if not folder_path:
            QMessageBox.warning(self, "警告", "请选择文献文件夹路径")
            return
            
        self.log("开始处理文献...")
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.progress_bar.setValue(0)
        
        # 获取配置
        config = {
            'base_url': self.base_url_input.text(),
            'api_key': self.api_key_input.text(),
            'model': self.model_combo.currentText(),
            'folder_path': folder_path,
            'concurrency': self.concurrency_spin.value(),
            'max_tokens': self.max_token_spin.value(),
            'generate_overall_report': self.generate_overall_report_check.isChecked(),
            'cache_text': self.cache_text_check.isChecked()
        }
        
        # 保存当前配置
        self.config.update(config)
        self.config_manager.save_config(self.config)
        
        # 启动处理线程
        self.worker = ProcessWorker(self.processor, config)
        self.worker.log_signal.connect(self.log)
        self.worker.progress_signal.connect(self.update_progress)
        self.worker.finished_signal.connect(self.processing_finished)
        self.worker.error_signal.connect(self.processing_error)
        self.worker.start()
        
    def stop_processing(self):
        if self.worker and self.worker.isRunning():
            self.worker.terminate()
            self.worker.wait()
            self.log("处理已停止")
            self.start_btn.setEnabled(True)
            self.stop_btn.setEnabled(False)
        
    def refresh_processing(self):
        self.log("强制刷新处理...")
        # 在实际应用中，这里应该设置一个标志位，让处理过程跳过已存在的文件检查
        
    def regenerate_single(self):
        self.log("重新生成选中文献...")
        # 在实际应用中，这里应该重新处理选中的文献
        
    def regenerate_overall(self):
        self.log("重新生成总报告...")
        # 在实际应用中，这里应该重新生成总报告
        
    def open_qa_dialog(self, item):
        """打开文献问答对话框"""
        # 从item的data中获取文件路径信息
        item_data = item.data(Qt.UserRole)
        
        if item_data and 'pdf_path' in item_data:
            pdf_path = item_data['pdf_path']
            
            # 获取LLM配置
            base_url = self.base_url_input.text()
            api_key = self.api_key_input.text()
            
            if not base_url or not api_key:
                QMessageBox.warning(self, "警告", "请先配置LLM Base URL和API Key")
                return
                
            # 创建并显示问答对话框
            from ui.qa_dialog import QADialog
            dialog = QADialog(pdf_path, base_url, api_key, self)
            dialog.exec_()
        else:
            QMessageBox.warning(self, "警告", "无法获取文献文件路径")
        
    def log(self, message):
        """在主线程中安全地更新日志显示"""
        # 确保GUI操作在主线程中执行
        if threading.current_thread() is threading.main_thread():
            self.log_display.append(message)
            # 自动滚动到底部
            self.log_display.moveCursor(self.log_display.textCursor().End)
        else:
            # 如果在非主线程中调用，使用信号机制
            self.log_signal.emit(message)
        
    def update_progress(self, value):
        self.progress_bar.setValue(value)
        
    def processing_finished(self, results):
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.progress_bar.setValue(100)
        
        # 更新文献列表
        self.literature_list.clear()
        for result in results:
            if result['status'] in ['success', 'skipped']:
                filename = os.path.basename(result['pdf_path'])
                summary_filename = filename.replace('.pdf', '.summary.md')
                # 在列表项中同时显示PDF文件名和摘要文件位置
                display_text = f"{filename} → {summary_filename}"
                item = QListWidgetItem(display_text)
                # 将完整路径信息存储在item的data中
                item.setData(Qt.UserRole, {
                    'pdf_path': result['pdf_path'],
                    'summary_path': result['summary_path'] if 'summary_path' in result else result['pdf_path'].replace('.pdf', '.summary.md')
                })
                self.literature_list.addItem(item)
        
        self.log("所有处理已完成")
        self.log("摘要文件已保存在对应的PDF文件同目录下，文件名后缀为.summary.md")
        
    def processing_error(self, error_msg):
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        QMessageBox.critical(self, "错误", f"处理过程中发生错误:\n{error_msg}")
        self.log(f"处理错误: {error_msg}")
        
    def open_selected_file_folder(self):
        """打开选中文件所在文件夹"""
        selected_items = self.literature_list.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "警告", "请先选择一个文献")
            return
            
        item = selected_items[0]
        item_data = item.data(Qt.UserRole)
        
        if item_data and 'pdf_path' in item_data:
            pdf_path = item_data['pdf_path']
            folder_path = os.path.dirname(pdf_path)
            try:
                # 跨平台打开文件夹
                if sys.platform == "win32":
                    os.startfile(folder_path)
                elif sys.platform == "darwin":  # macOS
                    os.system(f"open '{folder_path}'")
                else:  # linux
                    os.system(f"xdg-open '{folder_path}'")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"无法打开文件夹: {str(e)}")
        else:
            QMessageBox.warning(self, "警告", "无法获取文件路径")
