from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QTextEdit,
                             QLineEdit, QPushButton, QMessageBox, QLabel)
from PyQt5.QtCore import Qt, pyqtSignal, QMetaObject
from PyQt5.QtGui import QFont
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
    
    def __init__(self, pdf_path, base_url, api_key, model="gpt-3.5-turbo", stream_output=True, parent=None):
        super().__init__(parent)
        self.pdf_path = pdf_path
        self.base_url = base_url
        self.api_key = api_key
        self.model = model
        self.stream_output = stream_output
        self.qa_file = pdf_path.replace('.pdf', '.qa.md')
        self.summary_file = pdf_path.replace('.pdf', '.summary.md')  # 修正摘要文件路径
        self.pdf_reader = PDFReader()
        self.llm_client = None
        # 限制内存中的对话历史长度，保留最近20轮对话（40条消息）
        self.conversation_history = []
        self.conversation_turns = 0  # 对话轮次计数器
        self.max_history_length = 40  # 每轮对话包含用户和助手两条消息
        self.summary_threshold = 10  # 当对话轮次超过多少次时生成摘要
        
        self.init_ui()
        self.load_summary()  # 加载文献总结内容
        self.load_qa_history()
        # 连接日志信号到处理槽
        self.log_signal.connect(self._handle_log_signal)

    def _handle_log_signal(self, message):
        """处理日志信号的槽函数"""
        self.history_display.append(message)

    def load_summary(self):
        """加载文献总结内容"""
        if os.path.exists(self.summary_file):
            try:
                with open(self.summary_file, 'r', encoding='utf-8') as f:
                    summary_content = f.read()
                # 在对话历史显示区域添加文献总结
                summary_header = "**文献总结内容**\n\n"
                self.history_display.append(summary_header)
                self.history_display.append(summary_content)
                self.history_display.append("\n---\n")
            except Exception as e:
                QMessageBox.warning(self, "警告", f"无法加载文献总结: {str(e)}")
        else:
            self.history_display.append("**文献总结内容**\n\n暂无文献总结内容\n\n---\n")

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
        self.llm_client = LLMClient(self.base_url, self.api_key, 2048, self.model, self.stream_output)
        
    def load_qa_history(self):
        """加载问答历史"""
        if os.path.exists(self.qa_file):
            with open(self.qa_file, 'r', encoding='utf-8') as f:
                content = f.read()
                # 不再将历史内容设置为整个内容，而是追加到已有内容后面
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

        # 显示历史对话内容（在总结内容之后）
        if markdown_content.strip():
            self.history_display.append(markdown_content)

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

            if self.llm_client.stream_output:
                # 流式输出模式
                loop.run_until_complete(
                    self._stream_answer(text, question, timestamp)
                )
            else:
                # 非流式输出模式
                answer = loop.run_until_complete(
                    self.llm_client.ask_question(text, question, self.conversation_history)
                )
                # 显示回答（需要在主线程中执行）
                self._show_answer(answer, timestamp, user_entry)

            loop.close()

        except Exception as e:
            error_entry = f"**错误** ({timestamp}):\n无法获取回答: {str(e)}\n\n"
            # 在主线程中更新UI
            if threading.current_thread() is threading.main_thread():
                self.history_display.insertPlainText(error_entry)
            else:
                self.log_signal.emit(error_entry)
            self.save_qa_entry(error_entry)

    async def _stream_answer(self, text, question, timestamp):
        """流式获取并显示回答"""
        # 显示助手标识和时间戳
        assistant_header = f"**助手** ({timestamp}):\n"
        if threading.current_thread() is threading.main_thread():
            self.history_display.insertPlainText(assistant_header)
        else:
            self.log_signal.emit(assistant_header)
        
        # 获取问答提示词
        qa_prompt = self.llm_client.prompt_manager.get_prompt("question_answer")

        messages = [
            {"role": "system", "content": qa_prompt["system"]},
        ]

        # 添加历史对话（如果存在）
        if self.conversation_history:
            messages.extend(self.conversation_history)

        # 添加当前文献内容和问题
        formatted_user_prompt = qa_prompt["user"].format(text=text[:self.llm_client.max_tokens*2], question=question)
        messages.append({"role": "user", "content": formatted_user_prompt})

        # 检查并修剪对话历史以适应token限制
        total_tokens = self.llm_client._count_tokens(messages)
        if total_tokens > self.llm_client.max_tokens:  # 如果超过最大token数，则进行修剪
            # 为响应留出一些空间（20%的max_tokens）
            max_allowed_tokens = int(self.llm_client.max_tokens * 0.8)
            messages = self.llm_client._trim_history(messages, max_allowed_tokens)

        try:
            # 流式获取回答
            response = await self.llm_client.client.chat.completions.create(
                model=self.llm_client.model,
                messages=messages,
                max_tokens=self.llm_client.max_tokens,
                temperature=0.7,
                stream=True
            )
            
            full_response = ""
            async for chunk in response:
                if chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    full_response += content
                    # 实时显示内容
                    if threading.current_thread() is threading.main_thread():
                        # 直接插入文本，不添加额外的换行符
                        self.history_display.insertPlainText(content)
                        # 滚动到最新内容
                        cursor = self.history_display.textCursor()
                        cursor.movePosition(cursor.End)
                        self.history_display.setTextCursor(cursor)
                        self.history_display.ensureCursorVisible()
                        # 强制更新界面
                        self.history_display.repaint()
                    else:
                        # 使用信号在主线程中更新UI
                        self.log_signal.emit(content)
            
            # 添加换行和空行（只添加一次）
            if threading.current_thread() is threading.main_thread():
                self.history_display.insertPlainText("\n\n")
            else:
                self.log_signal.emit("\n\n")
                
            # 更新对话历史
            self.conversation_history.append({"role": "user", "content": question})
            self.conversation_history.append({"role": "assistant", "content": full_response})

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

            # 保存问答记录
            user_entry = f"**用户** ({timestamp}):\n{question}\n\n"
            answer_entry = f"**助手** ({timestamp}):\n{full_response}\n\n"
            self.save_qa_entry(user_entry + answer_entry)
            
            return full_response
            
        except Exception as e:
            error_msg = f"\n\n**错误**: 无法获取回答: {str(e)}\n\n"
            if threading.current_thread() is threading.main_thread():
                self.history_display.insertPlainText(error_msg)
            else:
                self.log_signal.emit(error_msg)
            raise e

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

        # 保存问答记录
        self.save_qa_entry(user_entry + answer_entry)

    def save_qa_entry(self, entry):
        """保存问答记录"""
        try:
            with open(self.qa_file, 'a', encoding='utf-8') as f:
                f.write(entry)
        except Exception as e:
            QMessageBox.warning(self, "警告", f"无法保存问答记录: {str(e)}")
