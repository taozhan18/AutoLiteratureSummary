import openai
import asyncio
from typing import List, Dict
import traceback
import tiktoken  # 用于计算token数量
from utils.prompt_manager import PromptManager


class LLMClient:
    def __init__(self, base_url: str, api_key: str, max_tokens: int = 2048, model: str = "gpt-3.5-turbo"):
        """
        初始化LLM客户端

        Args:
            base_url: LLM API的基础URL
            api_key: API密钥
            max_tokens: 最大token数
            model: 要使用的模型名称
        """
        self.client = openai.AsyncOpenAI(
            base_url=base_url,
            api_key=api_key
        )
        self.max_tokens = max_tokens
        self.model = model
        # 初始化tokenizer
        try:
            self.tokenizer = tiktoken.encoding_for_model(model)
        except KeyError:
            # 如果模型不支持，则使用默认的cl100k_base编码
            self.tokenizer = tiktoken.get_encoding("cl100k_base")

        # 初始化提示词管理器
        self.prompt_manager = PromptManager()

    def _count_tokens(self, messages: List[Dict]) -> int:
        """计算消息列表的token数量"""
        total_tokens = 0
        for message in messages:
            # 每条消息都有一定的token开销
            total_tokens += 4  # 每条消息的基础开销
            for key, value in message.items():
                total_tokens += len(self.tokenizer.encode(str(value)))
                if key == "name":
                    total_tokens += -1  # name字段的特殊处理
        total_tokens += 2  # 请求的整体开销
        return total_tokens

    def _trim_history(self, messages: List[Dict], max_allowed_tokens: int) -> List[Dict]:
        """根据最大允许token数修剪对话历史"""
        # 保留系统消息
        system_message = messages[0]  # 系统消息
        content_messages = messages[1:]  # 历史对话（包括文献内容和问题）

        # 计算系统消息的token数
        system_tokens = self._count_tokens([system_message])

        # 如果系统消息已经超限，只保留系统消息（这种情况很少见）
        if system_tokens >= max_allowed_tokens:
            return [system_message]

        # 计算可用于其他内容的token数
        available_tokens = max_allowed_tokens - system_tokens

        # 从最新的历史对话开始添加，直到达到token限制
        trimmed_history = []
        current_tokens = 0

        # 从后往前遍历历史对话（最新的在前面）
        for i in range(len(content_messages) - 1, -1, -1):
            message = content_messages[i]
            message_tokens = self._count_tokens([message])

            if current_tokens + message_tokens <= available_tokens:
                trimmed_history.insert(0, message)  # 插入到列表开头保持顺序
                current_tokens += message_tokens
            else:
                # 如果添加当前消息会超限，则停止添加
                break

        return [system_message] + trimmed_history

    async def test_connection(self) -> bool:
        """
        测试API连接

        Returns:
            连接是否成功
        """
        try:
            # 发送一个简单的请求来测试连接
            response = await self.client.models.list()
            return True
        except openai.APIConnectionError as e:
            print(f"API连接错误: {str(e)}")
            return False
        except openai.AuthenticationError as e:
            print(f"API认证错误: {str(e)}")
            return False
        except Exception as e:
            print(f"测试连接时发生未知错误: {str(e)}")
            return False

    async def generate_summary(self, text: str) -> str:
        """
        生成单篇文献摘要

        Args:
            text: 文献文本内容

        Returns:
            Markdown格式的结构化摘要
        """
        # 获取摘要提示词
        summary_prompt = self.prompt_manager.get_prompt("summary")

        prompt = summary_prompt["user"].format(text=text[:self.max_tokens*4])

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": summary_prompt["system"]},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=self.max_tokens,
                temperature=0.3
            )

            summary_content = response.choices[0].message.content

            # 检查返回的摘要是否为空
            if not summary_content or not summary_content.strip():
                raise Exception("LLM返回的摘要内容为空")

            return summary_content
        except openai.APIError as e:
            raise Exception(f"调用LLM API错误: {str(e)}")
        except openai.AuthenticationError as e:
            raise Exception(f"LLM API认证错误: {str(e)}")
        except openai.RateLimitError as e:
            raise Exception(f"LLM API调用频率超限: {str(e)}")
        except openai.APIConnectionError as e:
            raise Exception(f"LLM API连接错误: {str(e)}")
        except Exception as e:
            raise Exception(f"调用LLM生成摘要时出错: {str(e)}\n{traceback.format_exc()}")

    async def generate_overall_report(self, summaries: List[str]) -> str:
        """
        生成总体报告

        Args:
            summaries: 所有文献摘要的列表

        Returns:
            Markdown格式的总体报告
        """
        # 获取总体报告提示词
        report_prompt = self.prompt_manager.get_prompt("overall_report")

        combined_summaries = "\n\n---\n\n".join(summaries)
        prompt = report_prompt["user"].format(summaries=combined_summaries)

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": report_prompt["system"]},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=self.max_tokens,
                temperature=0.3
            )

            return response.choices[0].message.content
        except openai.APIError as e:
            raise Exception(f"调用LLM API错误: {str(e)}")
        except openai.AuthenticationError as e:
            raise Exception(f"LLM API认证错误: {str(e)}")
        except openai.RateLimitError as e:
            raise Exception(f"LLM API调用频率超限: {str(e)}")
        except openai.APIConnectionError as e:
            raise Exception(f"LLM API连接错误: {str(e)}")
        except Exception as e:
            raise Exception(f"调用LLM生成总体报告时出错: {str(e)}\n{traceback.format_exc()}")

    async def ask_question(self, text: str, question: str, history: List[Dict] = None) -> str:
        """
        针对文献内容回答问题

        Args:
            text: 文献原文
            question: 用户问题
            history: 对话历史

        Returns:
            问题的回答
        """
        # 获取问答提示词
        qa_prompt = self.prompt_manager.get_prompt("question_answer")

        messages = [
            {"role": "system", "content": qa_prompt["system"]},
        ]

        # 添加历史对话（如果存在）
        if history:
            messages.extend(history)

        # 添加当前文献内容和问题
        formatted_user_prompt = qa_prompt["user"].format(text=text[:self.max_tokens*2], question=question)
        messages.append({"role": "user", "content": formatted_user_prompt})

        # 检查并修剪对话历史以适应token限制
        total_tokens = self._count_tokens(messages)
        if total_tokens > self.max_tokens:  # 如果超过最大token数，则进行修剪
            # 为响应留出一些空间（20%的max_tokens）
            max_allowed_tokens = int(self.max_tokens * 0.8)
            messages = self._trim_history(messages, max_allowed_tokens)

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=self.max_tokens,
                temperature=0.7
            )

            return response.choices[0].message.content
        except openai.APIError as e:
            raise Exception(f"调用LLM API错误: {str(e)}")
        except openai.AuthenticationError as e:
            raise Exception(f"LLM API认证错误: {str(e)}")
        except openai.RateLimitError as e:
            raise Exception(f"LLM API调用频率超限: {str(e)}")
        except openai.APIConnectionError as e:
            raise Exception(f"LLM API连接错误: {str(e)}")
        except Exception as e:
            raise Exception(f"调用LLM回答问题时出错: {str(e)}\n{traceback.format_exc()}")
