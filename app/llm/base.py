"""LLM 클라이언트 추상 기본 클래스"""

from abc import ABC, abstractmethod
from typing import Iterator


class BaseLLMClient(ABC):
    """모든 LLM 클라이언트의 공통 인터페이스"""

    @abstractmethod
    def analyze(self, image_bytes: bytes, prompt: str, **kwargs) -> str:
        """이미지 + 프롬프트 → 판독문 (블로킹)"""
        ...

    def stream_analyze(self, image_bytes: bytes, prompt: str, **kwargs) -> Iterator[str]:
        """스트리밍 판독문 반환 (미지원 시 단건 yield)"""
        yield self.analyze(image_bytes, prompt, **kwargs)

    @property
    @abstractmethod
    def model_name(self) -> str:
        ...

    @property
    def supports_streaming(self) -> bool:
        return False

    @classmethod
    def is_available(cls) -> bool:
        """LLM 사용 가능 여부 (API 키, 서버 상태 등)"""
        return True
