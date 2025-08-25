import sys
import os

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_imports():
    """测试导入是否正常"""
    try:
        from utils.llm_client import LLMClient
        print("✓ LLMClient导入成功")
        return True
    except Exception as e:
        print(f"✗ LLMClient导入失败: {e}")
        return False

def test_api_connection_class():
    """测试API连接类是否存在"""
    try:
        from utils.llm_client import LLMClient
        # 检查是否有test_connection方法
        if hasattr(LLMClient, 'test_connection'):
            print("✓ test_connection方法存在")
            return True
        else:
            print("✗ test_connection方法不存在")
            return False
    except Exception as e:
        print(f"✗ 检查API连接类时出错: {e}")
        return False

if __name__ == "__main__":
    print("测试API测试功能...")
    
    success = True
    success &= test_imports()
    success &= test_api_connection_class()
    
    if success:
        print("\n✓ 所有测试通过，API测试功能应该正常工作")
    else:
        print("\n✗ 部分测试失败，请检查代码")