#!/usr/bin/env python3
"""
调试脚本：测试单个PDF文件的处理流程
"""

import os
import sys
import asyncio
import traceback
import json

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.processor import LiteratureProcessor
from utils.pdf_reader import PDFReader
from utils.llm_client import LLMClient
from utils.config_manager import ConfigManager


async def debug_single_pdf(pdf_path):
    """调试单个PDF文件的处理"""
    print(f"开始调试处理PDF文件: {pdf_path}")
    
    # 检查文件是否存在
    if not os.path.exists(pdf_path):
        print(f"错误: 文件不存在: {pdf_path}")
        return
    
    # 加载配置
    config_manager = ConfigManager()
    config = config_manager.load_config()
    
    print("配置信息:")
    print(f"  Base URL: {config.get('base_url', 'N/A')}")
    print(f"  API Key: {'*' * len(config.get('api_key', '')) if config.get('api_key') else 'N/A'}")
    print(f"  Model: {config.get('model', 'N/A')}")
    print(f"  Max Tokens: {config.get('max_tokens', 'N/A')}")
    
    # 初始化处理器
    processor = LiteratureProcessor()
    
    try:
        # 初始化LLM客户端
        print("\n初始化LLM客户端...")
        processor.initialize_llm_client(
            config['base_url'],
            config['api_key'],
            config['max_tokens'],
            config['model']
        )
        print("✓ LLM客户端初始化成功")
        
        # 提取文本
        print("\n提取PDF文本...")
        text = processor.pdf_reader.extract_text(pdf_path)
        print(f"✓ 文本提取成功，字符数: {len(text)}")
        
        if not text.strip():
            print("警告: 提取的文本为空")
            return
        
        # 保存原始文本用于调试
        text_file = pdf_path.replace('.pdf', '.debug.txt')
        with open(text_file, 'w', encoding='utf-8') as f:
            f.write(text)
        print(f"✓ 原始文本已保存到: {text_file}")
        
        # 生成摘要
        print("\n生成摘要...")
        summary = await processor.llm_client.generate_summary(text)
        print(f"✓ 摘要生成成功，字符数: {len(summary)}")
        
        if not summary.strip():
            print("警告: 生成的摘要为空")
            return
            
        # 保存摘要
        summary_path = pdf_path.replace('.pdf', '.debug.summary.md')
        with open(summary_path, 'w', encoding='utf-8') as f:
            f.write(summary)
        print(f"✓ 摘要已保存到: {summary_path}")
        
        # 显示摘要内容
        print("\n生成的摘要内容:")
        print("-" * 50)
        print(summary)
        print("-" * 50)
        
    except Exception as e:
        print(f"处理过程中出现错误: {str(e)}")
        print("详细错误信息:")
        print(traceback.format_exc())


def main():
    if len(sys.argv) != 2:
        print("使用方法: python debug_single_pdf.py <pdf文件路径>")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    asyncio.run(debug_single_pdf(pdf_path))


if __name__ == "__main__":
    main()