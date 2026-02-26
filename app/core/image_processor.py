"""Window/Level 적용 및 이미지 변환 유틸리티"""

from io import BytesIO
from typing import Dict, Tuple

import numpy as np
from PIL import Image


def apply_windowing(
    array: np.ndarray,
    window_center: float,
    window_width: float,
) -> np.ndarray:
    """Window / Level 적용 후 0-255 uint8 배열 반환"""
    window_width = max(window_width, 1)  # 0 나누기 방지
    lower = window_center - window_width / 2
    upper = window_center + window_width / 2

    windowed = np.clip(array, lower, upper)
    windowed = ((windowed - lower) / (upper - lower) * 255).astype(np.uint8)
    return windowed


def array_to_png_bytes(array: np.ndarray) -> bytes:
    """0-255 numpy 배열을 PNG bytes로 변환 (RGB)"""
    img = Image.fromarray(array.astype(np.uint8))
    if img.mode != "RGB":
        img = img.convert("RGB")
    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def get_window_presets() -> Dict[str, Tuple[int, int]]:
    """Window Preset 딕셔너리 반환 (center, width)"""
    return {
        "Default":       (40,   400),
        "Bone":          (400, 1800),
        "Lung":          (-600, 1500),
        "Soft Tissue":   (50,   400),
        "Brain":         (35,    80),
        "Abdomen":       (60,   400),
        "Mediastinum":   (50,   500),
        "Liver":         (60,   160),
    }
