import os
import sys
import asyncio
import traceback
from typing import List, Dict
import time

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.pdf_reader import PDFReader
from utils.llm_client import LLMClient


class LiteratureProcessor:
    def __init__(self):
        self.pdf_reader = PDFReader()
        self.llm_client = None
        self.api_request_delay = 0  # API请求间隔（秒）
        
    def initialize_llm_client(self, base_url: str, api_key: str, max_tokens: int, model: str = "gpt-3.5-turbo"):
        """初始化LLM客户端"""
        self.llm_client = LLMClient(base_url, api_key, max_tokens, model)
        
    def set_api_request_delay(self, delay: int):
        """设置API请求间隔"""
        self.api_request_delay = delay
        
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