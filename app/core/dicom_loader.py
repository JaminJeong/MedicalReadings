"""DICOM 파일/폴더 로딩 및 파싱 유틸리티"""

import os
from io import BytesIO
from pathlib import Path
from typing import List, Tuple

import numpy as np
import pydicom


def load_xray(file_data: bytes) -> pydicom.Dataset:
    """바이트에서 X-ray DICOM 로드"""
    return pydicom.dcmread(BytesIO(file_data))


def load_ct_series(folder_path: str) -> List[pydicom.Dataset]:
    """폴더에서 CT DICOM 시리즈 로드 (SliceLocation 기준 정렬)"""
    datasets = []
    folder = Path(folder_path)

    # .dcm 확장자 파일 탐색
    candidates = list(folder.rglob("*.dcm")) + list(folder.rglob("*.DCM"))

    # 확장자 없는 파일도 시도
    if not candidates:
        for f in folder.rglob("*"):
            if f.is_file() and f.suffix == "":
                candidates.append(f)

    for filepath in candidates:
        try:
            ds = pydicom.dcmread(str(filepath), force=True)
            if hasattr(ds, "pixel_array"):
                datasets.append(ds)
        except Exception:
            continue

    if not datasets:
        raise ValueError("DICOM 파일을 찾을 수 없습니다. ZIP 내부에 .dcm 파일이 있는지 확인하세요.")

    # 정렬 기준: SliceLocation → ImagePositionPatient[2] → InstanceNumber
    def sort_key(ds: pydicom.Dataset) -> float:
        if hasattr(ds, "SliceLocation"):
            return float(ds.SliceLocation)
        if hasattr(ds, "ImagePositionPatient"):
            return float(ds.ImagePositionPatient[2])
        if hasattr(ds, "InstanceNumber"):
            return float(ds.InstanceNumber)
        return 0.0

    datasets.sort(key=sort_key)
    return datasets


def extract_pixel_array(ds: pydicom.Dataset) -> np.ndarray:
    """RescaleSlope / RescaleIntercept 적용한 픽셀 배열 반환"""
    pixel_array = ds.pixel_array.astype(np.float32)
    slope = float(getattr(ds, "RescaleSlope", 1))
    intercept = float(getattr(ds, "RescaleIntercept", 0))
    return pixel_array * slope + intercept


def get_window_defaults(ds: pydicom.Dataset) -> Tuple[float, float]:
    """DICOM 헤더에서 기본 WindowCenter / WindowWidth 반환"""
    wc = getattr(ds, "WindowCenter", 40)
    ww = getattr(ds, "WindowWidth", 400)

    # MultiValue 처리
    if hasattr(wc, "__iter__") and not isinstance(wc, str):
        wc = float(list(wc)[0])
    else:
        wc = float(wc)

    if hasattr(ww, "__iter__") and not isinstance(ww, str):
        ww = float(list(ww)[0])
    else:
        ww = float(ww)

    return wc, ww
