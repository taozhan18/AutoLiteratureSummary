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
            },
            "extract_metadata": {
                "system": "你是一位专业的学术文献分析师。你的任务是从文献全文中提取结构化元数据。请严格按照JSON格式输出。",
                "user": """请从以下文献内容中提取以下信息，以JSON格式输出：

1. "title": 文章标题（如无法确定则输出文件名）
2. "keywords": 关键词列表，用逗号分隔（如无法提取则输出"未知"）
3. "abstract": 原文摘要（如原文有摘要部分则直接提取；如无则基于全文内容生成200字以内的摘要）
4. "is_english": 布尔值，判断文献是否主要为英文（true/false）

请严格输出合法JSON，不要添加任何额外说明文字。

文献内容：
{text}"""
            },
            "translate_abstract": {
                "system": "你是一位专业的学术翻译专家，擅长英中学术文献翻译。翻译时请保持学术严谨性，使用规范的中文学术术语。",
                "user": """请将以下英文摘要翻译为中文，保持学术风格：

{text}"""
            },
            "generate_record_summary": {
                "system": "你是一位专业的学术文献总结专家，能够简洁精炼地概括文献核心内容。",
                "user": """请为以下文献生成一段300字以内的中文概要，涵盖研究目的、方法、主要发现和结论：

{text}"""
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
