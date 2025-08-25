import os
import sys
from utils.pdf_reader import PDFReader

def test_pdf_processing(pdf_path):
    """测试PDF处理功能"""
    print(f"测试PDF文件: {pdf_path}")
    
    # 检查文件是否存在
    if not os.path.exists(pdf_path):
        print(f"错误: 文件不存在: {pdf_path}")
        return
        
    # 检查文件大小
    file_size = os.path.getsize(pdf_path)
    print(f"文件大小: {file_size} 字节")
    
    # 尝试提取文本
    try:
        reader = PDFReader()
        text = reader.extract_text(pdf_path)
        print(f"成功提取文本，字符数: {len(text)}")
        print(f"前500个字符预览:")
        print(text[:500])
        print("..." if len(text) > 500 else "")
    except Exception as e:
        print(f"提取文本时出错: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python debug_pdf.py <pdf文件路径>")
        sys.exit(1)
        
    pdf_path = sys.argv[1]
    test_pdf_processing(pdf_path)