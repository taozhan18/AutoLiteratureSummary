import os
import sys

def test_project_structure():
    """测试项目结构是否完整"""
    required_files = [
        'main.py',
        'requirements.txt',
        'README.md',
        'LICENSE',
        'ui/main_window.py',
        'ui/qa_dialog.py',
        'ui/__init__.py',
        'core/processor.py',
        'core/__init__.py',
        'utils/pdf_reader.py',
        'utils/llm_client.py',
        'utils/__init__.py'
    ]
    
    missing_files = []
    for file_path in required_files:
        if not os.path.exists(file_path):
            missing_files.append(file_path)
    
    if missing_files:
        print("以下文件缺失:")
        for file in missing_files:
            print(f"  - {file}")
        return False
    else:
        print("项目结构完整")
        return True

def test_imports():
    """测试导入是否正常"""
    try:
        # 添加当前目录到Python路径
        sys.path.append(os.path.dirname(os.path.abspath(__file__)))
        
        # 测试导入
        from ui.main_window import MainWindow
        from core.processor import LiteratureProcessor
        from utils.pdf_reader import PDFReader
        from utils.llm_client import LLMClient
        
        print("所有模块导入成功")
        return True
    except Exception as e:
        print(f"导入模块时出错: {e}")
        return False

if __name__ == "__main__":
    print("测试项目结构...")
    structure_ok = test_project_structure()
    
    print("\n测试模块导入...")
    imports_ok = test_imports()
    
    if structure_ok and imports_ok:
        print("\n所有测试通过!")
    else:
        print("\n存在错误，请检查!")