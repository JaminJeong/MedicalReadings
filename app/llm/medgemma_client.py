"""MedGemma 로컬 추론 클라이언트 (Hugging Face transformers)

요구사항:
  - pip install torch transformers accelerate
  - GPU VRAM 8GB+ 권장 (4B 모델 bfloat16 기준)
  - HF_TOKEN 환경변수 (gated 모델 접근용)
"""

import os
from io import BytesIO
from typing import Optional

from PIL import Image

from .base import BaseLLMClient


class MedGemmaClient(BaseLLMClient):
    def __init__(
        self,
        model: str = "google/medgemma-4b-it",
        max_new_tokens: int = 512,
    ):
        self._model_id = model
        self.max_new_tokens = max_new_tokens
        self._processor = None
        self._model = None

    def _load_model(self):
        if self._model is not None:
            return

        import torch
        from transformers import AutoModelForImageTextToText, AutoProcessor

        hf_token = os.getenv("HF_TOKEN")
        dtype = torch.bfloat16 if torch.cuda.is_available() else torch.float32

        self._processor = AutoProcessor.from_pretrained(
            self._model_id, token=hf_token
        )
        self._model = AutoModelForImageTextToText.from_pretrained(
            self._model_id,
            torch_dtype=dtype,
            device_map="auto",
            token=hf_token,
        )

    @property
    def model_name(self) -> str:
        return self._model_id

    @classmethod
    def is_available(cls) -> bool:
        try:
            import torch  # noqa: F401
            import transformers  # noqa: F401
            return True
        except ImportError:
            return False

    def analyze(self, image_bytes: bytes, prompt: str, **kwargs) -> str:
        self._load_model()
        import torch

        pil_image = Image.open(BytesIO(image_bytes)).convert("RGB")

        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "image", "image": pil_image},
                    {"type": "text", "text": prompt},
                ],
            }
        ]

        inputs = self._processor.apply_chat_template(
            messages,
            add_generation_prompt=True,
            tokenize=True,
            return_dict=True,
            return_tensors="pt",
        ).to(self._model.device)

        with torch.inference_mode():
            output = self._model.generate(
                **inputs,
                max_new_tokens=self.max_new_tokens,
            )

        input_len = inputs["input_ids"].shape[-1]
        result = self._processor.decode(
            output[0][input_len:], skip_special_tokens=True
        )
        return result
