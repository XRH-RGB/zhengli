import hashlib
import json
import math
from urllib.parse import urlsplit

import httpx

from .github import ServiceError


class ModelClient:
    def __init__(self, settings):
        self.settings = settings

    @property
    def signature(self):
        identity = [self.settings.embedding_base_url.rstrip("/"), self.settings.embedding_model]
        return hashlib.sha256(json.dumps(identity).encode()).hexdigest()

    def post(self, kind, endpoint, payload):
        settings = self.settings
        base = getattr(settings, f"{kind}_base_url").rstrip("/")
        key = getattr(settings, f"{kind}_api_key")
        parsed = urlsplit(base)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc or parsed.username or parsed.query or parsed.fragment:
            raise ServiceError("模型接口地址格式不正确。")
        if not getattr(settings, f"{kind}_model"):
            raise ServiceError("请先在 .env 中配置模型名称。")
        headers = {"Authorization": f"Bearer {key}"} if key else {}
        with httpx.Client(timeout=settings.request_timeout, follow_redirects=False) as client:
            response = client.post(f"{base}/{endpoint}", headers=headers, json=payload)
        if response.status_code != 200:
            raise ServiceError(f"模型接口失败（HTTP {response.status_code}），请检查服务端模型配置。")
        return response.json()

    def embed(self, texts):
        vectors = []
        for start in range(0, len(texts), 32):
            batch = texts[start:start + 32]
            data = self.post("embedding", "embeddings", {
                "model": self.settings.embedding_model, "input": batch,
            })
            rows = sorted(data.get("data", []), key=lambda x: x["index"])
            if [r.get("index") for r in rows] != list(range(len(batch))):
                raise ServiceError("嵌入接口返回的向量序号不完整。")
            for row in rows:
                vector = row.get("embedding")
                if (not isinstance(vector, list) or not vector or
                    any(not isinstance(v, (int, float)) or not math.isfinite(v) for v in vector) or
                    sum(v * v for v in vector) == 0):
                    raise ServiceError("嵌入接口返回了无效向量。")
                if vectors and len(vector) != len(vectors[0]):
                    raise ServiceError("嵌入向量维度不一致。")
                vectors.append(vector)
        return vectors

    def complete(self, messages):
        response = self.post("llm", "chat/completions", {
            "model": self.settings.llm_model, "messages": messages,
            "temperature": 0.2, "max_tokens": 2400,
        })
        try:
            answer = response["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError):
            raise ServiceError("模型没有返回有效文本。") from None
        if not isinstance(answer, str) or not answer.strip():
            raise ServiceError("模型返回了空结果。")
        return answer
