"""OpenAI GPT 클라이언트"""

import base64
import os
from typing import Iterator

from .base import BaseLLMClient


class GPTClient(BaseLLMClient):
    def __init__(
        self,
        model: str = "gpt-4o",
        temperature: float = 0.3,
        max_tokens: int = 2048,
    ):
        self._model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self._client = None

    def _get_client(self):
        if self._client is None:
            from openai import OpenAI
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OPENAI_API_KEY 환경변수가 설정되지 않았습니다.")
            self._client = OpenAI(api_key=api_key)
        return self._client

    @property
    def model_name(self) -> str:
        return self._model

    @property
    def supports_streaming(self) -> bool:
        return True

    @classmethod
    def is_available(cls) -> bool:
        return bool(os.getenv("OPENAI_API_KEY"))

    def _build_messages(self, image_bytes: bytes, prompt: str) -> list:
        b64 = base64.b64encode(image_bytes).decode()
        return [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{b64}",
                            "detail": "high",
                        },
                    },
                ],
            }
        ]

    def analyze(self, image_bytes: bytes, prompt: str, **kwargs) -> str:
        client = self._get_client()
        response = client.chat.completions.create(
            model=self._model,
            messages=self._build_messages(image_bytes, prompt),
            temperature=self.temperature,
            max_tokens=self.max_tokens,
        )
        return response.choices[0].message.content

    def stream_analyze(self, image_bytes: bytes, prompt: str, **kwargs) -> Iterator[str]:
        client = self._get_client()
        stream = client.chat.completions.create(
            model=self._model,
            messages=self._build_messages(image_bytes, prompt),
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            stream=True,
        )
        for chunk in stream:
            delta = chunk.choices[0].delta.content
            if delta is not None:
                yield delta
