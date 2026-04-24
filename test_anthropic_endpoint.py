"""测试智谱 Anthropic 兼容端点 - 模拟 Claude Code 的调用方式"""
import json
import httpx
import asyncio

with open("config.json", "r", encoding="utf-8") as f:
    config = json.load(f)

API_KEY = config["api_key"]

# Claude Code 实际使用的端点
ANTHROPIC_URL = "https://open.bigmodel.cn/api/anthropic/v1/messages"
# 用户项目使用的 OpenAI 兼容端点
OPENAI_URL = "https://open.bigmodel.cn/api/paas/v4/chat/completions"

MODELS = [
    "glm-5",
    "glm-5-flash",
    "glm-4.7",
    "glm-4-plus",
    "glm-4",
    "glm-4-flash",
    "glm-4-air",
    "glm-4-long",
    "glm-z1-flash",
]


async def test_anthropic(model: str) -> dict:
    """通过 Anthropic 兼容端点测试"""
    headers = {
        "x-api-key": API_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    payload = {
        "model": model,
        "max_tokens": 50,
        "messages": [{"role": "user", "content": "你好，请回复'测试成功'"}],
    }
    result = {"endpoint": "anthropic", "model": model, "success": False, "error": None, "response": None}
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(ANTHROPIC_URL, headers=headers, json=payload)
            if resp.status_code == 200:
                data = resp.json()
                content = data.get("content", [{}])
                text = content[0].get("text", "") if content else ""
                result["success"] = True
                result["response"] = text[:100]
            else:
                result["error"] = f"HTTP {resp.status_code}: {resp.text[:200]}"
    except Exception as e:
        result["error"] = f"{type(e).__name__}: {e}"
    return result


async def test_openai(model: str) -> dict:
    """通过 OpenAI 兼容端点测试"""
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "content-type": "application/json",
    }
    payload = {
        "model": model,
        "max_tokens": 50,
        "messages": [{"role": "user", "content": "你好，请回复'测试成功'"}],
        "temperature": 0.1,
    }
    result = {"endpoint": "openai", "model": model, "success": False, "error": None, "response": None}
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(OPENAI_URL, headers=headers, json=payload)
            if resp.status_code == 200:
                data = resp.json()
                text = data["choices"][0]["message"]["content"]
                result["success"] = True
                result["response"] = text[:100]
            else:
                result["error"] = f"HTTP {resp.status_code}: {resp.text[:200]}"
    except Exception as e:
        result["error"] = f"{type(e).__name__}: {e}"
    return result


async def test_anthropic_with_extra_headers(model: str) -> dict:
    """通过 Anthropic 兼容端点测试，加上 Claude Code 风格的额外请求头"""
    headers = {
        "x-api-key": API_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
        "user-agent": "claude-code/1.0",
        "x-client": "claude-code",
    }
    payload = {
        "model": model,
        "max_tokens": 50,
        "messages": [{"role": "user", "content": "你好，请回复'测试成功'"}],
    }
    result = {"endpoint": "anthropic+headers", "model": model, "success": False, "error": None, "response": None}
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(ANTHROPIC_URL, headers=headers, json=payload)
            if resp.status_code == 200:
                data = resp.json()
                content = data.get("content", [{}])
                text = content[0].get("text", "") if content else ""
                result["success"] = True
                result["response"] = text[:100]
            else:
                result["error"] = f"HTTP {resp.status_code}: {resp.text[:200]}"
    except Exception as e:
        result["error"] = f"{type(e).__name__}: {e}"
    return result


async def main():
    print("=" * 70)
    print("智谱 API 端点对比测试")
    print(f"API Key: {API_KEY[:8]}...{API_KEY[-4:]}")
    print("=" * 70)

    for model in MODELS:
        print(f"\n--- 模型: {model} ---")
        # Anthropic 端点
        r1 = await test_anthropic(model)
        if r1["success"]:
            print(f"  [Anthropic端点]     ✅ 可用! 响应: {r1['response']}")
        else:
            print(f"  [Anthropic端点]     ❌ {r1['error'][:80]}")

        # Anthropic 端点 + 额外 header
        r2 = await test_anthropic_with_extra_headers(model)
        if r2["success"]:
            print(f"  [Anthropic+Headers] ✅ 可用! 响应: {r2['response']}")
        else:
            print(f"  [Anthropic+Headers] ❌ {r2['error'][:80]}")

        # OpenAI 端点
        r3 = await test_openai(model)
        if r3["success"]:
            print(f"  [OpenAI端点]        ✅ 可用! 响应: {r3['response']}")
        else:
            print(f"  [OpenAI端点]        ❌ {r3['error'][:80]}")

    # 汇总
    print("\n" + "=" * 70)
    print("汇总:")
    for model in MODELS:
        results = {}
        for test_fn in [test_anthropic, test_anthropic_with_extra_headers, test_openai]:
            r = await test_fn(model)
            key = r["endpoint"]
            results[key] = "✅" if r["success"] else "❌"
        print(f"  {model:20s} | Anthropic: {results['anthropic']} | +Headers: {results['anthropic+headers']} | OpenAI: {results['openai']}")

    print("\n测试完成。")


if __name__ == "__main__":
    asyncio.run(main())
