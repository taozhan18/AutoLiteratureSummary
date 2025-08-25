import asyncio
import sys
import os

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils.llm_client import LLMClient
from langchain_openai import ChatOpenAI
from langchain_core.messages import AIMessage, SystemMessage, HumanMessage
def test(base_url: str, api_key: str, model: str = "gpt-3.5-turbo"):
    llm = ChatOpenAI(
                model=model,  # 或者换成你对应的模型
                base_url=base_url,
                api_key=api_key,
            )
    llm.invoke(
        [
            SystemMessage(content='You are a helpful assistant that helps people find information.'),
            HumanMessage(content='hello world'),
        ]
    )

async def test_api_connection(base_url: str, api_key: str, model: str = "gpt-3.5-turbo"):
    """
    测试API连接

    Args:
        base_url: LLM API的基础URL
        api_key: API密钥
        model: 要测试的模型名称
    """
    print(f"测试API连接...")
    print(f"Base URL: {base_url}")
    print(f"Model: {model}")

    try:
        # 创建LLM客户端
        client = LLMClient(base_url, api_key, model=model)

        # 测试连接
        print("正在测试连接...")
        success = await client.test_connection()

        if success:
            print("✓ API连接成功!")

            # 测试生成摘要功能
            print("正在测试生成摘要功能...")
            test_text = "这是一个测试文本，用于验证API是否正常工作。"
            try:
                summary = await client.generate_summary(test_text)
                print("✓ 生成摘要功能正常!")
                print(f"生成的摘要预览:\n{summary[:200]}...")
            except Exception as e:
                print(f"✗ 生成摘要功能异常: {e}")
        else:
            print("✗ API连接失败!")

    except Exception as e:
        print(f"测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()

def main():
    # if len(sys.argv) < 3:
    #     print("用法: python test_api.py <base_url> <api_key> [model]")
    #     print("示例: python test_api.py http://localhost:8000/v1 sk-xxxxxxxx gpt-3.5-turbo")
    #     return

    # base_url = sys.argv[1]
    # api_key = sys.argv[2]
    # model = sys.argv[3] if len(sys.argv) > 3 else "gpt-3.5-turbo"

    base_url = "https://api.gptsapi.net/v1"
    api_key = "sk-zpEbcc35d7b6b4c4648c3ae46ed3efb8d1177eca612fMJHH"
    model = "gpt-4o-mini"

    asyncio.run(test_api_connection(base_url, api_key, model))

if __name__ == "__main__":
    # main()
