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
    """批量入库工作线程，支持并行 API 调用"""
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
            self.llm_client = LLMClient(
                self.config['base_url'],
                self.config['api_key'],
                self.config.get('max_tokens', 2048),
                self.config.get('model', 'gpt-3.5-turbo'),
                api_type=self.config.get('api_type', 'openai')
            )

            self.db_manager.init_db()

            folder_path = self.config['folder_path']
            self.log_signal.emit(f"正在扫描文件夹: {folder_path}")

            enabled_types = ['pdf']
            if self.config.get('process_docx', True):
                enabled_types.append('docx')
            if self.config.get('process_md', True):
                enabled_types.append('md')

            all_files = scan_all_files(folder_path, enabled_types)

            if not all_files:
                self.log_signal.emit("未找到支持的文件（PDF/DOCX/MD）")
                self.finished_signal.emit(0)
                return

            self.log_signal.emit(f"找到 {len(all_files)} 个文件")

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(self._run_parallel(all_files))
            finally:
                loop.close()

        except Exception as e:
            error_details = f"{str(e)}\n{traceback.format_exc()}"
            self.error_signal.emit(error_details)

    async def _run_parallel(self, all_files: list):
        concurrency = self.config.get('concurrency', 3)
        semaphore = asyncio.Semaphore(concurrency)
        db_lock = asyncio.Lock()
        api_delay = self.config.get('api_request_delay', 0)
        total = len(all_files)
        done = 0
        success_count = 0
        skip_count = 0
        fail_count = 0

        async def process_one(i, file_path, file_type):
            nonlocal done, success_count, skip_count, fail_count

            if self._stop_flag:
                return

            async with semaphore:
                if self._stop_flag:
                    return

                filename = os.path.basename(file_path)
                self.log_signal.emit(f"正在处理 [{i+1}/{total}]: {filename}")

                try:
                    # 提取文本（同步操作，每个任务独立，线程安全）
                    text, _ = self.text_extractor.extract(file_path)

                    if not text.strip() or len(text.strip()) < 100:
                        self.log_signal.emit(f"  跳过: 文本过短或为空 ({filename})")
                        skip_count += 1
                        return

                    content_hash = compute_content_hash(text)

                    # 去重检查（加锁保护 SQLite 读 + 写一致性）
                    async with db_lock:
                        existing = self.db_manager.check_duplicate(content_hash)
                        if existing:
                            self.log_signal.emit(
                                f"  跳过: 已存在于数据库中 ({existing.get('title', filename)})"
                            )
                            skip_count += 1
                            return

                    # LLM 调用（并行执行，不持锁）
                    if api_delay > 0:
                        await asyncio.sleep(api_delay)

                    raw_json = await self.llm_client.call_with_prompt_type("extract_metadata", text)
                    metadata = self._parse_metadata_json(raw_json)

                    title = metadata.get('title', filename)
                    keywords = metadata.get('keywords', '')
                    abstract = metadata.get('abstract', '')
                    is_english = metadata.get('is_english', False)
                    is_academic = metadata.get('is_academic', True)
                    citation = metadata.get('citation', '')

                    if not is_academic:
                        self.log_signal.emit(f"  跳过: 非学术文献 ({title})")
                        skip_count += 1
                        return

                    abstract_cn = ''
                    if is_english and abstract:
                        if api_delay > 0:
                            await asyncio.sleep(api_delay)
                        abstract_cn = await self.llm_client.call_with_prompt_type(
                            "translate_abstract", abstract
                        )

                    if api_delay > 0:
                        await asyncio.sleep(api_delay)
                    summary = await self.llm_client.call_with_prompt_type(
                        "generate_record_summary", text
                    )

                    # 写入数据库（加锁防止并发写入冲突）
                    async with db_lock:
                        record = {
                            'file_path': file_path,
                            'file_type': file_type,
                            'content_hash': content_hash,
                            'title': title,
                            'keywords': keywords,
                            'abstract': abstract,
                            'abstract_cn': abstract_cn,
                            'summary': summary,
                            'citation': citation,
                        }
                        self.db_manager.insert_record(record)

                    self.log_signal.emit(f"  已入库: {title}")
                    success_count += 1

                except Exception as e:
                    self.log_signal.emit(f"  处理失败 ({filename}): {str(e)}")
                    fail_count += 1

                finally:
                    done += 1
                    progress = int(done / total * 100)
                    self.progress_signal.emit(progress)

        tasks = [
            asyncio.create_task(process_one(i, fp, ft))
            for i, (fp, ft) in enumerate(all_files)
        ]
        await asyncio.gather(*tasks)

        self.log_signal.emit(
            f"批量入库完成: 成功 {success_count}, 跳过 {skip_count}, 失败 {fail_count}"
        )
        self.finished_signal.emit(success_count)

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

        self.log_signal.emit("警告: 无法解析元数据JSON")
        return {}
