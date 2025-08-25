from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QTextEdit, 
                             QLineEdit, QPushButton, QMessageBox)
from PyQt5.QtCore import Qt, pyqtSignal, QMetaObject
import os
import asyncio
import json
import threading
from datetime import datetime
from utils.llm_client import LLMClient
from utils.pdf_reader import PDFReader


class QADialog(QDialog):
    # 添加日志信号，用于线程安全的日志更新
    log_signal = pyqtSignal(str)
    
    def __init__(self, pdf_path, base_url, api_key, parent=None):
        super().__init__(parent)
        self.pdf_path = pdf_path
        self.base_url = base_url
        self.api_key = api_key
        self.qa_file = pdf_path.replace('.pdf', '.qa.md')
        self.summary_file = pdf_path.replace('.pdf', '_summary.json')
        self.summary_file = pdf_path.replace('.pdf', '_summary.json')
        self.pdf_reader = PDFReader()
        self.llm_client = None
        # 限制内存中的对话历史长度，保留最近20轮对话（40条消息）
        self.conversation_history = []
        self.conversation_turns = 0  # 对话轮次计数器
        self.max_history_length = 40  # 每轮对话包含用户和助手两条消息
        self.summary_threshold = 10  # 当对话轮次超过多少次时生成摘要
        
        self.init_ui()
        self.load_qa_history()
        # 连接日志信号到处理槽
        self.log_signal.connect(self._handle_log_signal)
        
    def _handle_log_signal(self, message):
        """处理日志信号的槽函数"""
        self.history_display.append(message)
        
    def init_ui(self):
        self.setWindowTitle(f'文献问答: {os.path.basename(self.pdf_path)}')
        self.setGeometry(200, 200, 800, 600)
        
        layout = QVBoxLayout()
        
        # 对话历史显示
        self.history_display = QTextEdit()
        self.history_display.setReadOnly(True)
        layout.addWidget(self.history_display)
        
        # 问题输入区域
        input_layout = QHBoxLayout()
        self.question_input = QLineEdit()
        self.question_input.returnPressed.connect(self.ask_question)
        ask_button = QPushButton("提问")
        ask_button.clicked.connect(self.ask_question)
        
        input_layout.addWidget(self.question_input)
        input_layout.addWidget(ask_button)
        layout.addLayout(input_layout)
        
        self.setLayout(layout)
        
        # 初始化LLM客户端
        self.llm_client = LLMClient(self.base_url, self.api_key)
        
    def load_qa_history(self):
        """加载问答历史"""
        if os.path.exists(self.qa_file):
            with open(self.qa_file, 'r', encoding='utf-8') as f:
                content = f.read()
                self.history_display.setMarkdown(content)
                # 从历史记录中恢复对话历史
                self._restore_history_from_markdown(content)
                
    def _restore_history_from_markdown(self, markdown_content):
        """从Markdown内容恢复对话历史"""
        lines = markdown_content.split('\n')
        current_role = None
        current_content = ""
        timestamp = ""
        
        for line in lines:
            if line.startswith('**用户**') or line.startswith('**助手**'):
                # 保存前一个条目
                if current_role and current_content:
                    self.conversation_history.append({
                        "role": "user" if current_role == "**用户**" else "assistant", 
                        "content": current_content.strip()
                    })
                # 解析新的条目
                current_role = "**用户**" if line.startswith('**用户**') else "**助手**"
                # 提取时间戳
                try:
                    timestamp_start = line.find('(') + 1
                    timestamp_end = line.find(')')
                    timestamp = line[timestamp_start:timestamp_end] if timestamp_start > 0 and timestamp_end > timestamp_start else ""
                except:
                    timestamp = ""
                current_content = ""
            elif current_role and line.strip() != "":
                current_content += line + "\n"
                
        # 保存最后一个条目
        if current_role and current_content:
            self.conversation_history.append({
                "role": "user" if current_role == "**用户**" else "assistant", 
                "content": current_content.strip()
            })
        
        # 限制历史长度
        if len(self.conversation_history) > self.max_history_length:
            self.conversation_history = self.conversation_history[-self.max_history_length:]
                
    def ask_question(self):
        """提问处理"""
        question = self.question_input.text().strip()
        if not question:
            return
            
        # 清空输入框
        self.question_input.clear()
        
        # 显示用户问题
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        user_entry = f"**用户** ({timestamp}):\n{question}\n\n"
        self.history_display.insertPlainText(user_entry)
        
        # 获取文献内容
        try:
            text = self.pdf_reader.extract_text(self.pdf_path)
        except Exception as e:
            QMessageBox.critical(self, "错误", f"无法读取文献内容: {str(e)}")
            return
            
        # 调用LLM回答问题
        self.answer_question(text, question, timestamp, user_entry)
        
    def answer_question(self, text, question, timestamp, user_entry):
        """回答问题"""
        # 在新线程中运行异步函数，避免阻塞UI
        thread = threading.Thread(target=self._run_async_answer, args=(text, question, timestamp, user_entry))
        thread.start()
        
    def _run_async_answer(self, text, question, timestamp, user_entry):
        """在新线程中运行异步回答"""
        try:
            # 创建新的事件循环
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # 运行异步函数
            answer = loop.run_until_complete(
                self.llm_client.ask_question(text, question, self.conversation_history)
            )
            
            loop.close()
            
            # 显示回答（需要在主线程中执行）
            self._show_answer(answer, timestamp, user_entry)
            
        except Exception as e:
            error_entry = f"**错误** ({timestamp}):\n无法获取回答: {str(e)}\n\n"
            # 在主线程中更新UI
            if threading.current_thread() is threading.main_thread():
                self.history_display.insertPlainText(error_entry)
            else:
                self.log_signal.emit(error_entry)
            self.save_qa_entry(error_entry)
            
    def _show_answer(self, answer, timestamp, user_entry):
        """在主线程中显示回答"""
        # 显示回答
        answer_entry = f"**助手** ({timestamp}):\n{answer}\n\n"
        if threading.current_thread() is threading.main_thread():
            self.history_display.insertPlainText(answer_entry)
        else:
            self.log_signal.emit(answer_entry)
        
        # 更新对话历史 - 使用与LLM一致的格式
        user_question = user_entry.split('\n')[1].strip()  # 提取用户问题
        self.conversation_history.append({"role": "user", "content": user_question})
        self.conversation_history.append({"role": "assistant", "content": answer})
        
        # 更新对话轮次
        self.conversation_turns += 1
        
        # 限制历史长度，防止内存占用过大
        if len(self.conversation_history) > self.max_history_length:
            # 保留最新的对话历史
            self.conversation_history = self.conversation_history[-self.max_history_length:]
        
        # 如果达到摘要阈值且尚未生成摘要，则生成摘要
        if self.conversation_turns >= self.summary_threshold and not hasattr(self, 'summary_generated'):
            self.generate_conversation_summary()
            self.summary_generated = True
            
        # 保存到文件
        self.save_qa_entry(user_entry + answer_entry)
        
    def save_qa_entry(self, entry):
        """保存问答记录"""
        try:
            with open(self.qa_file, 'a', encoding='utf-8') as f:
                f.write(entry)
        except Exception as e:
            QMessageBox.warning(self, "警告", f"无法保存问答记录: {str(e)}")