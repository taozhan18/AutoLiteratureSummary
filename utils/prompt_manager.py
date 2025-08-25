import json
import os
from typing import Dict, Any


class PromptManager:
    """提示词管理器，允许用户自定义提示词"""

    def __init__(self, config_dir: str = "."):
        self.config_dir = config_dir
        self.prompt_file = os.path.join(config_dir, "prompts.json")
        self.default_prompts = {
            "summary": {
                "system": "你是一位专业的学术文献分析师，能够准确提取和总结文献的核心内容。",
                "user": """请为以下学术文献生成一个结构化摘要，使用Markdown格式输出：
这里请给出文章标题：
1. 研究背景与目标
2. 方法论
3. 主要发现
4. 结论与意义
5. 局限性

文献内容：
{text}"""
            },
            "overall_report": {
                "system": "你是一位专业的学术研究报告撰写专家，能够综合分析多篇文献并产出深度分析报告。",
                "user": """基于以下多篇文献的摘要，生成一份总体报告，包括：
1. 研究主题分布
2. 共性结论
3. 方法对比
4. 待解决问题

文献摘要：
{summaries}"""
            },
            "question_answer": {
                "system": "你是一位专业的学术助手，能够基于文献内容准确回答用户问题。",
                "user": """文献内容：
{text}

问题：
{question}"""
            }
        }
        self.prompts = self.load_prompts()

    def load_prompts(self) -> Dict[str, Any]:
        """加载用户自定义提示词"""
        if os.path.exists(self.prompt_file):
            try:
                with open(self.prompt_file, 'r', encoding='utf-8') as f:
                    user_prompts = json.load(f)
                # 合并默认提示词和用户提示词
                prompts = self.default_prompts.copy()
                for key, value in user_prompts.items():
                    if key in prompts:
                        prompts[key].update(value)
                    else:
                        prompts[key] = value
                return prompts
            except Exception as e:
                print(f"加载提示词配置文件出错: {e}")
                return self.default_prompts
        else:
            # 如果配置文件不存在，创建默认配置文件
            self.save_default_prompts()
            return self.default_prompts

    def save_default_prompts(self):
        """保存默认提示词到配置文件"""
        try:
            with open(self.prompt_file, 'w', encoding='utf-8') as f:
                json.dump(self.default_prompts, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存提示词配置文件出错: {e}")

    def save_prompts(self, prompts: Dict[str, Any]):
        """保存用户自定义提示词"""
        try:
            with open(self.prompt_file, 'w', encoding='utf-8') as f:
                json.dump(prompts, f, ensure_ascii=False, indent=2)
            self.prompts = prompts
        except Exception as e:
            print(f"保存提示词配置文件出错: {e}")

    def get_prompt(self, prompt_type: str) -> Dict[str, str]:
        """获取指定类型的提示词"""
        return self.prompts.get(prompt_type, self.default_prompts.get(prompt_type, {}))

    def update_prompt(self, prompt_type: str, system_prompt: str = None, user_prompt: str = None):
        """更新指定类型的提示词"""
        if prompt_type not in self.prompts:
            self.prompts[prompt_type] = {}

        if system_prompt is not None:
            self.prompts[prompt_type]["system"] = system_prompt

        if user_prompt is not None:
            self.prompts[prompt_type]["user"] = user_prompt

        self.save_prompts(self.prompts)

    def reset_prompt(self, prompt_type: str):
        """重置指定类型的提示词为默认值"""
        if prompt_type in self.default_prompts:
            self.prompts[prompt_type] = self.default_prompts[prompt_type].copy()
            self.save_prompts(self.prompts)

    def reset_all_prompts(self):
        """重置所有提示词为默认值"""
        self.prompts = self.default_prompts.copy()
        self.save_prompts(self.prompts)
