import os
import sys
import asyncio
import traceback
import json
from typing import List, Dict
import time

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.pdf_reader import PDFReader
from utils.llm_client import LLMClient
from utils.text_extractor import compute_content_hash
from utils.database import DatabaseManager


class LiteratureProcessor:
    def __init__(self):
        self.pdf_reader = PDFReader()
        self.llm_client = None
        self.api_request_delay = 0  # API请求间隔（秒）
        self.db_manager = None
        self.auto_record_enabled = False
        
    def initialize_llm_client(self, base_url: str, api_key: str, max_tokens: int, model: str = "gpt-3.5-turbo"):
        """初始化LLM客户端"""
        self.llm_client = LLMClient(base_url, api_key, max_tokens, model)
        
    def set_api_request_delay(self, delay: int):
        """设置API请求间隔"""
        self.api_request_delay = delay

    def initialize_database(self, db_path: str = "literature_records.db"):
        """初始化数据库管理器"""
        self.db_manager = DatabaseManager(db_path)
        self.db_manager.init_db()

    def enable_auto_record(self, enabled: bool = True):
        """启用或禁用自动记录"""
        self.auto_record_enabled = enabled
        
    def scan_pdfs(self, folder_path: str) -> List[str]:
        """扫描文件夹中的所有PDF文件"""
        pdf_files = []
        for root, dirs, files in os.walk(folder_path):
            for file in files:
                if file.lower().endswith('.pdf'):
                    pdf_files.append(os.path.join(root, file))
        return pdf_files
    
    async def process_single_pdf(self, pdf_path: str, cache_text: bool = True) -> Dict:
        """处理单个PDF文件"""
        try:
            # 生成摘要文件路径
            summary_path = pdf_path.replace('.pdf', '.summary.md')
            
            # 检查是否已存在摘要
            if os.path.exists(summary_path):
                with open(summary_path, 'r', encoding='utf-8') as f:
                    summary = f.read()
                return {
                    'pdf_path': pdf_path,
                    'summary_path': summary_path,
                    'summary': summary,
                    'status': 'skipped'
                }
            
            # 提取文本
            text = self.pdf_reader.extract_text(pdf_path)
            
            # 检查文本是否为空
            if not text.strip():
                return {
                    'pdf_path': pdf_path,
                    'error': '提取的文本为空',
                    'status': 'failed'
                }
            
            # 检查文本长度
            if len(text.strip()) < 100:
                return {
                    'pdf_path': pdf_path,
                    'error': f'提取的文本过短，可能不是有效的学术文献，文本长度: {len(text.strip())}',
                    'status': 'failed'
                }
            
            # 缓存原始文本
            if cache_text:
                # 确保缓存目录存在
                os.makedirs('cache/texts', exist_ok=True)
                text_cache_path = os.path.join('cache', 'texts', os.path.basename(pdf_path).replace('.pdf', '.txt'))
                with open(text_cache_path, 'w', encoding='utf-8') as f:
                    f.write(text)
            
            # 生成摘要
            if not self.llm_client:
                raise ValueError("LLM客户端未初始化")
                
            # 如果设置了API请求间隔，则等待
            if self.api_request_delay > 0:
                await asyncio.sleep(self.api_request_delay)
                
            summary = await self.llm_client.generate_summary(text)
            
            # 检查生成的摘要是否为空
            if not summary or not summary.strip():
                return {
                    'pdf_path': pdf_path,
                    'error': '生成的摘要为空',
                    'status': 'failed'
                }
            
            # 保存摘要
            with open(summary_path, 'w', encoding='utf-8') as f:
                f.write(summary)

            # 自动记录到数据库
            if self.auto_record_enabled and self.db_manager:
                try:
                    await self._auto_record(pdf_path, text, 'pdf')
                except Exception as e:
                    print(f"自动记录失败: {str(e)}")
                
            return {
                'pdf_path': pdf_path,
                'summary_path': summary_path,
                'summary': summary,
                'status': 'success'
            }
        except Exception as e:
            # 记录详细的错误信息
            error_details = f"{str(e)}\n{traceback.format_exc()}"
            return {
                'pdf_path': pdf_path,
                'error': error_details,
                'status': 'failed'
            }
    
    async def process_pdfs(self, pdf_paths: List[str], concurrency: int = 5, 
                          cache_text: bool = True) -> List[Dict]:
        """并行处理多个PDF文件"""
        # 创建任务列表
        semaphore = asyncio.Semaphore(concurrency)
        
        async def process_with_semaphore(pdf_path):
            async with semaphore:
                return await self.process_single_pdf(pdf_path, cache_text)
        
        # 并行执行任务
        tasks = [process_with_semaphore(pdf_path) for pdf_path in pdf_paths]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 处理结果
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                # 记录详细的异常信息
                error_details = f"{str(result)}\n{traceback.format_exc()}"
                processed_results.append({
                    'pdf_path': pdf_paths[i],
                    'error': error_details,
                    'status': 'failed'
                })
            else:
                processed_results.append(result)
                
        return processed_results
    
    async def generate_overall_report(self, summaries: List[str]) -> str:
        """生成总体报告"""
        if not self.llm_client:
            raise ValueError("LLM客户端未初始化")
            
        # 如果设置了API请求间隔，则等待
        if self.api_request_delay > 0:
            await asyncio.sleep(self.api_request_delay)
            
        report = await self.llm_client.generate_overall_report(summaries)
        
        # 在总体报告后追加各个文献的摘要
        report_with_summaries = report + "\n\n---\n\n# 附录：各文献摘要详情\n\n"
        
        for i, summary in enumerate(summaries, 1):
            report_with_summaries += f"## 文献 {i} 摘要\n\n{summary}\n\n---\n\n"
        
        # 保存总报告
        report_path = 'overall_report.md'
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report_with_summaries)
            
        return report_with_summaries

    async def _auto_record(self, file_path: str, text: str, file_type: str):
        """自动记录文献到数据库"""
        # 计算内容哈希并检查重复
        content_hash = compute_content_hash(text)
        existing = self.db_manager.check_duplicate(content_hash)
        if existing:
            print(f"文献已存在于数据库中: {existing.get('title', file_path)}")
            return

        # LLM 提取元数据
        raw_json = await self.llm_client.call_with_prompt_type("extract_metadata", text)
        # 解析 JSON 响应（尝试提取 JSON 部分）
        metadata = self._parse_metadata_json(raw_json)

        title = metadata.get('title', os.path.basename(file_path))
        keywords = metadata.get('keywords', '')
        abstract = metadata.get('abstract', '')
        is_english = metadata.get('is_english', False)

        # 如果是英文文献，翻译摘要
        abstract_cn = ''
        if is_english and abstract:
            if self.api_request_delay > 0:
                await asyncio.sleep(self.api_request_delay)
            abstract_cn = await self.llm_client.call_with_prompt_type("translate_abstract", abstract)

        # 生成中文概要
        if self.api_request_delay > 0:
            await asyncio.sleep(self.api_request_delay)
        summary = await self.llm_client.call_with_prompt_type("generate_record_summary", text)

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
        print(f"已记录到数据库: {title}")

    def _parse_metadata_json(self, raw: str) -> Dict:
        """解析 LLM 返回的 JSON 元数据"""
        # 尝试直接解析
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            pass

        # 尝试提取 JSON 块（可能被 markdown 代码块包裹）
        import re
        json_match = re.search(r'```(?:json)?\s*(.*?)```', raw, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(1).strip())
            except json.JSONDecodeError:
                pass

        # 尝试找最外层的 { }
        brace_match = re.search(r'\{.*\}', raw, re.DOTALL)
        if brace_match:
            try:
                return json.loads(brace_match.group(0))
            except json.JSONDecodeError:
                pass

        # 解析失败，返回空字典
        print(f"警告: 无法解析元数据JSON: {raw[:200]}")
        return {}