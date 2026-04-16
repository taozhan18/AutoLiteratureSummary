from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QTableWidget,
                             QTableWidgetItem, QTextEdit, QPushButton, QLabel,
                             QComboBox, QLineEdit, QFileDialog, QMessageBox,
                             QHeaderView, QGroupBox, QAbstractItemView)
from PyQt5.QtCore import Qt
from utils.database import DatabaseManager


class RecordBrowserDialog(QDialog):
    """文献记录浏览对话框"""

    def __init__(self, db_path: str = "literature_records.db", parent=None):
        super().__init__(parent)
        self.db_manager = DatabaseManager(db_path)
        self.db_manager.init_db()
        self.records = []
        self.is_search_mode = False
        self.init_ui()
        self.load_records()

    def init_ui(self):
        self.setWindowTitle('文献记录浏览')
        self.setGeometry(150, 150, 1100, 750)

        layout = QVBoxLayout()

        # 筛选区域
        filter_group = QGroupBox("筛选")
        filter_layout = QHBoxLayout()

        filter_layout.addWidget(QLabel("文件类型:"))
        self.type_filter = QComboBox()
        self.type_filter.addItems(["全部", "PDF", "DOCX", "MD"])
        self.type_filter.currentIndexChanged.connect(self.load_records)
        filter_layout.addWidget(self.type_filter)

        filter_layout.addWidget(QLabel("搜索:"))
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("搜索标题、关键词、摘要、文件路径... (支持多词空格分隔)")
        self.search_input.returnPressed.connect(self.search_records)
        filter_layout.addWidget(self.search_input)

        search_btn = QPushButton("搜索")
        search_btn.clicked.connect(self.search_records)
        filter_layout.addWidget(search_btn)

        reset_btn = QPushButton("重置")
        reset_btn.clicked.connect(self.reset_filter)
        filter_layout.addWidget(reset_btn)

        filter_group.setLayout(filter_layout)
        layout.addWidget(filter_group)

        # 记录表格
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["ID", "标题", "关键词", "文件类型", "文件路径", "记录时间"])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)
        self.table.setColumnWidth(0, 40)
        self.table.setColumnWidth(3, 70)
        self.table.setColumnWidth(5, 140)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.currentCellChanged.connect(self.show_detail)
        layout.addWidget(self.table)

        # 详情面板
        detail_group = QGroupBox("详情")
        detail_layout = QVBoxLayout()
        self.detail_display = QTextEdit()
        self.detail_display.setReadOnly(True)
        self.detail_display.setMaximumHeight(250)
        detail_layout.addWidget(self.detail_display)
        detail_group.setLayout(detail_layout)
        layout.addWidget(detail_group)

        # 底部按钮
        button_layout = QHBoxLayout()
        export_btn = QPushButton("导出 Excel")
        export_btn.clicked.connect(self.export_excel)
        delete_btn = QPushButton("删除选中记录")
        delete_btn.clicked.connect(self.delete_selected)
        refresh_btn = QPushButton("刷新")
        refresh_btn.clicked.connect(self.load_records)
        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(self.accept)

        button_layout.addWidget(export_btn)
        button_layout.addWidget(delete_btn)
        button_layout.addWidget(refresh_btn)
        button_layout.addStretch()
        button_layout.addWidget(close_btn)
        layout.addLayout(button_layout)

        self.setLayout(layout)

    def load_records(self):
        """加载所有记录"""
        self.is_search_mode = False
        type_map = {"全部": None, "PDF": "pdf", "DOCX": "docx", "MD": "md"}
        file_type = type_map.get(self.type_filter.currentText())
        self.records = self.db_manager.get_all_records(file_type)
        self._set_table_columns(normal=True)
        self.populate_table()
        self.detail_display.clear()

    def search_records(self):
        """使用 FTS5 全文检索"""
        query = self.search_input.text().strip()
        if not query:
            self.load_records()
            return
        self.is_search_mode = True
        self.records = self.db_manager.search_records(query)
        self._set_table_columns(normal=False)
        self.populate_table()

    def reset_filter(self):
        """重置筛选"""
        self.type_filter.setCurrentIndex(0)
        self.search_input.clear()
        self.load_records()

    def _set_table_columns(self, normal: bool):
        """切换表格列（普通模式 vs 搜索模式，搜索模式多一列相关性）"""
        self.table.blockSignals(True)
        if normal:
            self.table.setColumnCount(6)
            self.table.setHorizontalHeaderLabels(
                ["ID", "标题", "关键词", "文件类型", "文件路径", "记录时间"]
            )
            self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
            self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
            self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)
            self.table.setColumnWidth(0, 40)
            self.table.setColumnWidth(3, 70)
            self.table.setColumnWidth(5, 140)
        else:
            self.table.setColumnCount(7)
            self.table.setHorizontalHeaderLabels(
                ["ID", "标题", "关键词", "相关性", "文件类型", "文件路径", "记录时间"]
            )
            self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
            self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
            self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.Stretch)
            self.table.setColumnWidth(0, 40)
            self.table.setColumnWidth(3, 60)
            self.table.setColumnWidth(4, 70)
            self.table.setColumnWidth(6, 140)
        self.table.blockSignals(False)

    def populate_table(self):
        """填充表格"""
        self.table.setRowCount(len(self.records))
        for row, record in enumerate(self.records):
            col = 0
            # ID
            id_item = QTableWidgetItem(str(record.get('id', '')))
            id_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, col, id_item)
            col += 1

            # 标题
            self.table.setItem(row, col, QTableWidgetItem(record.get('title', '')))
            col += 1

            # 关键词
            self.table.setItem(row, col, QTableWidgetItem(record.get('keywords', '')))
            col += 1

            if self.is_search_mode:
                # 相关性分数
                rank = record.get('rank', 0)
                rank_item = QTableWidgetItem(f"{rank:.2f}")
                rank_item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(row, col, rank_item)
                col += 1

            # 文件类型
            type_item = QTableWidgetItem(record.get('file_type', '').upper())
            type_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, col, type_item)
            col += 1

            # 文件路径（仅显示文件名）
            fpath = record.get('file_path', '')
            self.table.setItem(row, col, QTableWidgetItem(fpath))
            col += 1

            # 记录时间
            self.table.setItem(row, col, QTableWidgetItem(record.get('created_at', '')))

    def show_detail(self, row, col, prev_row, prev_col):
        """显示选中记录的详情"""
        if row < 0 or row >= len(self.records):
            return

        record = self.records[row]
        detail = ""

        if record.get('title'):
            detail += f"**标题:** {record['title']}\n\n"
        if record.get('keywords'):
            detail += f"**关键词:** {record['keywords']}\n\n"
        if record.get('abstract'):
            detail += f"**摘要:**\n{record['abstract']}\n\n"
        if record.get('abstract_cn'):
            detail += f"**中文摘要:**\n{record['abstract_cn']}\n\n"
        if record.get('summary'):
            detail += f"**文章概要:**\n{record['summary']}\n\n"
        detail += f"**文件路径:** {record.get('file_path', '')}\n"

        self.detail_display.setMarkdown(detail)

    def export_excel(self):
        """导出到 Excel"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "导出 Excel", "literature_records.xlsx", "Excel 文件 (*.xlsx)"
        )
        if not file_path:
            return

        try:
            visible_ids = [r['id'] for r in self.records] if self.records else None
            self.db_manager.export_to_excel(file_path, visible_ids)
            QMessageBox.information(self, "成功", f"已导出到: {file_path}")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"导出失败: {str(e)}")

    def delete_selected(self):
        """删除选中记录"""
        current_row = self.table.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "警告", "请先选择一条记录")
            return

        record = self.records[current_row]
        reply = QMessageBox.question(
            self, "确认删除",
            f"确定要删除记录 \"{record.get('title', '')}\" 吗？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            try:
                self.db_manager.delete_record(record['id'])
                self.load_records()
            except Exception as e:
                QMessageBox.critical(self, "错误", f"删除失败: {str(e)}")
