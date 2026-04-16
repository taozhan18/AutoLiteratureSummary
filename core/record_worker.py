import os
import sys
import asyncio
import traceback
import json
import re
from typing import List

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt5.QtCore import QThread, pyqtSignal
from utils.text_extractor import TextExtractor, compute_content_hash, scan_all_files
from utils.database import DatabaseManager
from utils.llm_client import LLMClient


class RecordWorker(QThread):
    """批量入库工作线程"""
    log_signal = pyqtSignal(str)
    progress_signal = pyqtSignal(int)
    finished_signal = pyqtSignal(int)  # 处理的记录数量
    error_signal = pyqtSignal(str)

    def __init__(self, config: dict):
        super().__init__()
        self.config = config
        self.text_extractor = TextExtractor()
        self.db_manager = DatabaseManager(config.get('db_path', 'literature_records.db'))
        self.llm_client = None
        self._stop_flag = False

    def stop(self):
        """请求停止处理"""
        self._stop_flag = True

    def run(self):
        try:
            # 初始化 LLM 客户端
            self.llm_client = LLMClient(
                self.config['base_url'],
                self.config['api_key'],
                self.config.get('max_tokens', 2048),
                self.config.get('model', 'gpt-3.5-turbo')
            )

            # 初始化数据库
            self.db_manager.init_db()

            # 扫描所有支持的文件
            folder_path = self.config['folder_path']
            self.log_signal.emit(f"正在扫描文件夹: {folder_path}")
            all_files = scan_all_files(folder_path)

            if not all_files:
                self.log_signal.emit("未找到支持的文件（PDF/DOCX/MD）")
                self.finished_signal.emit(0)
                return

            self.log_signal.emit(f"找到 {len(all_files)} 个文件")

            # 创建事件循环处理异步任务
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            success_count = 0
            skip_count = 0
            fail_count = 0

            for i, (file_path, file_type) in enumerate(all_files):
                if self._stop_flag:
                    self.log_signal.emit("批量入库已停止")
                    break

                try:
                    filename = os.path.basename(file_path)
                    self.log_signal.emit(f"正在处理 [{i+1}/{len(all_files)}]: {filename}")

                    # 提取文本
                    text, _ = self.text_extractor.extract(file_path)

                    if not text.strip() or len(text.strip()) < 100:
                        self.log_signal.emit(f"  跳过: 文本过短或为空")
                        skip_count += 1
                        continue

                    # 去重检查
                    content_hash = compute_content_hash(text)
                    existing = self.db_manager.check_duplicate(content_hash)
                    if existing:
                        self.log_signal.emit(f"  跳过: 已存在于数据库中 ({existing.get('title', filename)})")
                        skip_count += 1
                        continue

                    # LLM 提取元数据
                    api_delay = self.config.get('api_request_delay', 0)
                    if api_delay > 0:
                        loop.run_until_complete(asyncio.sleep(api_delay))

                    raw_json = loop.run_until_complete(
                        self.llm_client.call_with_prompt_type("extract_metadata", text)
                    )
                    metadata = self._parse_metadata_json(raw_json)

                    title = metadata.get('title', filename)
                    keywords = metadata.get('keywords', '')
                    abstract = metadata.get('abstract', '')
                    is_english = metadata.get('is_english', False)

                    # 英文文献翻译摘要
                    abstract_cn = ''
                    if is_english and abstract:
                        if api_delay > 0:
                            loop.run_until_complete(asyncio.sleep(api_delay))
                        abstract_cn = loop.run_until_complete(
                            self.llm_client.call_with_prompt_type("translate_abstract", abstract)
                        )

                    # 生成中文概要
                    if api_delay > 0:
                        loop.run_until_complete(asyncio.sleep(api_delay))
                    summary = loop.run_until_complete(
                        self.llm_client.call_with_prompt_type("generate_record_summary", text)
                    )

                    # 插入数据库
                    record = {
                        'file_path': file_path,
                        'file_type': file_type,
                        'content_hash': content_hash,
                        'title': title,
                        'keywords': keywords,
                        'abstract': abstract,
                        'abstract_cn': abstract_cn,
                        'summary': summary,
                    }
                    self.db_manager.insert_record(record)
                    self.log_signal.emit(f"  已入库: {title}")
                    success_count += 1

                except Exception as e:
                    error_details = f"{str(e)}"
                    self.log_signal.emit(f"  处理失败: {error_details}")
                    fail_count += 1

                # 更新进度
                progress = int((i + 1) / len(all_files) * 100)
                self.progress_signal.emit(progress)

            loop.close()

            self.log_signal.emit(
                f"批量入库完成: 成功 {success_count}, 跳过 {skip_count}, 失败 {fail_count}"
            )
            self.finished_signal.emit(success_count)

        except Exception as e:
            error_details = f"{str(e)}\n{traceback.format_exc()}"
            self.error_signal.emit(error_details)

    def _parse_metadata_json(self, raw: str) -> dict:
        """解析 LLM 返回的 JSON 元数据"""
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            pass

        json_match = re.search(r'```(?:json)?\s*(.*?)```', raw, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(1).strip())
            except json.JSONDecodeError:
                pass

        brace_match = re.search(r'\{.*\}', raw, re.DOTALL)
        if brace_match:
            try:
                return json.loads(brace_match.group(0))
            except json.JSONDecodeError:
                pass

        self.log_signal.emit(f"警告: 无法解析元数据JSON")
        return {}
