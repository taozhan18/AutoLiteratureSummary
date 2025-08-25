import PyPDF2
import os
from typing import Optional


class PDFReader:
    def __init__(self):
        pass
    
    def extract_text(self, pdf_path: str) -> str:
        """
        从PDF文件中提取文本
        
        Args:
            pdf_path: PDF文件路径
            
        Returns:
            提取的文本内容
        """
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"PDF文件不存在: {pdf_path}")
            
        text = ""
        try:
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                for page_num, page in enumerate(pdf_reader.pages):
                    try:
                        page_text = page.extract_text()
                        if page_text:
                            text += page_text + "\n"
                    except Exception as e:
                        print(f"警告: 无法提取第{page_num+1}页的文本: {str(e)}")
                        continue
                        
            # 检查提取的文本是否为空
            if not text.strip():
                raise ValueError("PDF文件中未提取到任何文本内容")
                
        except PyPDF2.errors.PdfReadError as e:
            raise Exception(f"PDF文件读取错误: {str(e)}")
        except Exception as e:
            raise Exception(f"解析PDF文件时出错: {str(e)}")
            
        return text