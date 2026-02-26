"""Ollama 로컬 서버 클라이언트"""

import base64
import json
import os
from typing import Iterator, List

import requests

from .base import BaseLLMClient


class OllamaClient(BaseLLMClient):
    def __init__(self, model: str = "llava:13b", temperature: float = 0.3):
        self._model = model
        self.temperature = temperature
        self.host = os.getenv("OLLAMA_HOST", "http://localhost:11434")

    @property
    def model_name(self) -> str:
        return self._model

    @property
    def supports_streaming(self) -> bool:
        return True

    @classmethod
    def is_available(cls) -> bool:
        host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
        try:
            resp = requests.get(f"{host}/api/tags", timeout=3)
            return resp.status_code == 200
        except Exception:
            return False

    def get_available_models(self) -> List[str]:
        """설치된 Ollama 모델 목록 반환"""
        try:
            resp = requests.get(f"{self.host}/api/tags", timeout=5)
            if resp.status_code == 200:
                return [m["name"] for m in resp.json().get("models", [])]
        except Exception:
            pass
        return []

    def _build_payload(self, image_bytes: bytes, prompt: str, stream: bool) -> dict:
        b64 = base64.b64encode(image_bytes).decode()
        return {
            "model": self._model,
            "messages": [
                {
                    "role": "user",
                    "content": prompt,
                    "images": [b64],
                }
            ],
            "stream": stream,
            "options": {"temperature": self.temperature},
        }

    def analyze(self, image_bytes: bytes, prompt: str, **kwargs) -> str:
        payload = self._build_payload(image_bytes, prompt, stream=False)
        resp = requests.post(
            f"{self.host}/api/chat",
            json=payload,
            timeout=300,
        )
        resp.raise_for_status()
        return resp.json()["message"]["content"]

    def stream_analyze(self, image_bytes: bytes, prompt: str, **kwargs) -> Iterator[str]:
        payload = self._build_payload(image_bytes, prompt, stream=True)
        with requests.post(
            f"{self.host}/api/chat",
            json=payload,
            stream=True,
            timeout=300,
        ) as resp:
            resp.raise_for_status()
            for line in resp.iter_lines():
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    content = data.get("message", {}).get("content", "")
                    if content:
                        yield content
                    if data.get("done"):
                        break
                except json.JSONDecodeError:
                    continue
