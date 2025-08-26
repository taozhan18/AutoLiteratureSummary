import json
import os
from typing import Dict, Any


class ConfigManager:
    def __init__(self, config_file: str = "config.json"):
        self.config_file = config_file
        self.default_config = {
            "base_url": "http://localhost:8000/v1",
            "api_key": "",
            "model": "gpt-3.5-turbo",
            "concurrency": 5,
            "max_tokens": 2048,
            "generate_overall_report": True,
            "cache_text": True,
            "folder_path": "",
            "api_request_delay": 0,  # API请求间隔（秒）
            "stream_output": True    # 是否启用流式输出
        }
        
    def load_config(self) -> Dict[str, Any]:
        """
        从配置文件加载配置，如果文件不存在则返回默认配置
        
        Returns:
            配置字典
        """
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    # 确保所有必需的键都存在
                    for key, value in self.default_config.items():
                        if key not in config:
                            config[key] = value
                    return config
            except Exception as e:
                print(f"加载配置文件时出错: {e}")
                return self.default_config.copy()
        else:
            # 如果配置文件不存在，创建默认配置文件
            self.save_config(self.default_config)
            return self.default_config.copy()
            
    def save_config(self, config: Dict[str, Any]) -> None:
        """
        保存配置到文件
        
        Args:
            config: 配置字典
        """
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存配置文件时出错: {e}")