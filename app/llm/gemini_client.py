"""Google Gemini 클라이언트"""

import os
from io import BytesIO
from typing import Iterator

from PIL import Image

from .base import BaseLLMClient


class GeminiClient(BaseLLMClient):
    def __init__(
        self,
        model: str = "gemini-1.5-pro",
        temperature: float = 0.3,
        max_tokens: int = 2048,
    ):
        self._model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self._genai = None

    def _get_genai(self):
        if self._genai is None:
            import google.generativeai as genai
            api_key = os.getenv("GOOGLE_API_KEY")
            if not api_key:
                raise ValueError("GOOGLE_API_KEY 환경변수가 설정되지 않았습니다.")
            genai.configure(api_key=api_key)
            self._genai = genai
        return self._genai

    @property
    def model_name(self) -> str:
        return self._model

    @property
    def supports_streaming(self) -> bool:
        return True

    @classmethod
    def is_available(cls) -> bool:
        return bool(os.getenv("GOOGLE_API_KEY"))

    def _get_model(self):
        genai = self._get_genai()
        return genai.GenerativeModel(
            self._model,
            generation_config=genai.GenerationConfig(
                temperature=self.temperature,
                max_output_tokens=self.max_tokens,
            ),
        )

    def _to_pil(self, image_bytes: bytes) -> Image.Image:
        return Image.open(BytesIO(image_bytes)).convert("RGB")

    def analyze(self, image_bytes: bytes, prompt: str, **kwargs) -> str:
        model = self._get_model()
        response = model.generate_content([prompt, self._to_pil(image_bytes)])
        return response.text

    def stream_analyze(self, image_bytes: bytes, prompt: str, **kwargs) -> Iterator[str]:
        model = self._get_model()
        response = model.generate_content(
            [prompt, self._to_pil(image_bytes)], stream=True
        )
        for chunk in response:
            try:
                if chunk.text:
                    yield chunk.text
            except Exception:
                continue
