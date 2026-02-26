"""파일 유틸리티 - ZIP 압축 해제, 임시 디렉터리 관리"""

import os
import shutil
import tempfile
import zipfile
from io import BytesIO
from pathlib import Path
from typing import List


def extract_zip_to_temp(zip_bytes: bytes) -> str:
    """ZIP bytes를 임시 디렉터리에 압축 해제, 경로 반환"""
    temp_dir = tempfile.mkdtemp(prefix="ct_upload_")
    with zipfile.ZipFile(BytesIO(zip_bytes), "r") as zf:
        zf.extractall(temp_dir)
    return temp_dir


def cleanup_temp_dir(temp_dir: str) -> None:
    """임시 디렉터리 삭제"""
    if temp_dir and os.path.exists(temp_dir):
        shutil.rmtree(temp_dir, ignore_errors=True)


def find_dicom_files(folder: str) -> List[str]:
    """폴더에서 DICOM 파일 경로 목록 반환"""
    result = []
    for root, _, files in os.walk(folder):
        for fname in files:
            fpath = os.path.join(root, fname)
            if fname.lower().endswith(".dcm") or "." not in fname:
                result.append(fpath)
    return result
