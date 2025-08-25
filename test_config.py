import os
import sys

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils.config_manager import ConfigManager

def test_config_manager():
    """测试配置管理器功能"""
    print("测试配置管理器...")
    
    # 创建配置管理器实例
    config_manager = ConfigManager("test_config.json")
    
    # 加载配置
    config = config_manager.load_config()
    print("初始配置:", config)
    
    # 修改配置
    config["base_url"] = "https://api.openai.com/v1"
    config["api_key"] = "test-key"
    config["model"] = "gpt-4"
    config["concurrency"] = 10
    
    # 保存配置
    config_manager.save_config(config)
    print("配置已保存")
    
    # 重新加载配置
    loaded_config = config_manager.load_config()
    print("重新加载的配置:", loaded_config)
    
    # 清理测试文件
    if os.path.exists("test_config.json"):
        os.remove("test_config.json")
        print("测试配置文件已删除")
    
    print("测试完成!")

if __name__ == "__main__":
    test_config_manager()