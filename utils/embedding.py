import httpx
import numpy as np


class EmbeddingClient:
    """ZhiPu embedding API 客户端（OpenAI 兼容端点）"""

    # 智谱嵌入 API 固定使用 OpenAI 兼容端点
    DEFAULT_BASE_URL = "https://open.bigmodel.cn/api/paas/v4"
    DEFAULT_MODEL = "embedding-3"

    def __init__(self, api_key: str, base_url: str = None, model: str = None):
        self.api_key = api_key
        self.base_url = (base_url or self.DEFAULT_BASE_URL).rstrip("/")
        self.model = model or self.DEFAULT_MODEL
        self._available = None

    async def embed(self, text: str) -> np.ndarray:
        """
        生成文本的嵌入向量

        Returns:
            numpy float32 数组

        Raises:
            Exception: API 调用失败
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "content-type": "application/json",
        }
        payload = {
            "model": self.model,
            "input": text,
        }
        async with httpx.AsyncClient(timeout=30, proxy=None) as client:
            resp = await client.post(
                f"{self.base_url}/embeddings",
                headers=headers,
                json=payload,
            )
            if resp.status_code != 200:
                raise Exception(
                    f"Embedding API HTTP {resp.status_code}: {resp.text[:200]}"
                )
            data = resp.json()
            vec = data["data"][0]["embedding"]
            return np.array(vec, dtype=np.float32)

    async def embed_batch(self, texts: list) -> list:
        """
        批量生成嵌入向量

        Returns:
            numpy float32 数组列表
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "content-type": "application/json",
        }
        payload = {
            "model": self.model,
            "input": texts,
        }
        async with httpx.AsyncClient(timeout=60, proxy=None) as client:
            resp = await client.post(
                f"{self.base_url}/embeddings",
                headers=headers,
                json=payload,
            )
            if resp.status_code != 200:
                raise Exception(
                    f"Embedding API HTTP {resp.status_code}: {resp.text[:200]}"
                )
            data = resp.json()
            results = []
            for item in sorted(data["data"], key=lambda x: x["index"]):
                results.append(np.array(item["embedding"], dtype=np.float32))
            return results

    async def is_available(self) -> bool:
        """测试嵌入 API 是否可用"""
        if self._available is not None:
            return self._available
        try:
            vec = await self.embed("test")
            self._available = len(vec) > 0
        except Exception:
            self._available = False
        return self._available
