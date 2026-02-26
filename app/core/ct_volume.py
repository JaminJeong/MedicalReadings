"""CT 3D 볼륨 구성 및 슬라이싱"""

from typing import List, Tuple

import numpy as np
import pydicom


def build_volume(
    datasets: List[pydicom.Dataset],
) -> Tuple[np.ndarray, Tuple[float, float, float]]:
    """DICOM 시리즈에서 3D 볼륨 구성

    Returns:
        volume: np.ndarray (Z x Y x X), HU 값
        spacing: (z_mm, y_mm, x_mm)
    """
    slices = []
    for ds in datasets:
        arr = ds.pixel_array.astype(np.float32)
        slope = float(getattr(ds, "RescaleSlope", 1))
        intercept = float(getattr(ds, "RescaleIntercept", 0))
        slices.append(arr * slope + intercept)

    volume = np.stack(slices, axis=0)  # Z x Y x X

    # 픽셀 간격
    ds0 = datasets[0]
    pixel_spacing = getattr(ds0, "PixelSpacing", [1.0, 1.0])
    y_spacing = float(pixel_spacing[0])
    x_spacing = float(pixel_spacing[1])

    # Z 간격
    if len(datasets) > 1:
        try:
            z0 = float(getattr(datasets[0], "SliceLocation",
                        getattr(datasets[0], "ImagePositionPatient", [0, 0, 0])[2]))
            z1 = float(getattr(datasets[1], "SliceLocation",
                        getattr(datasets[1], "ImagePositionPatient", [0, 0, 0])[2]))
            z_spacing = abs(z1 - z0)
        except Exception:
            z_spacing = float(getattr(ds0, "SliceThickness", 1.0))
    else:
        z_spacing = float(getattr(ds0, "SliceThickness", 1.0))

    z_spacing = max(z_spacing, 0.1)  # 0 방지

    return volume, (z_spacing, y_spacing, x_spacing)


def get_axial_slice(volume: np.ndarray, z_idx: int) -> np.ndarray:
    """Axial 슬라이스 (Y x X)"""
    z_idx = int(np.clip(z_idx, 0, volume.shape[0] - 1))
    return volume[z_idx, :, :]


def get_sagittal_slice(volume: np.ndarray, x_idx: int) -> np.ndarray:
    """Sagittal 슬라이스 (Z x Y)"""
    x_idx = int(np.clip(x_idx, 0, volume.shape[2] - 1))
    return volume[:, :, x_idx]


def get_coronal_slice(volume: np.ndarray, y_idx: int) -> np.ndarray:
    """Coronal 슬라이스 (Z x X)"""
    y_idx = int(np.clip(y_idx, 0, volume.shape[1] - 1))
    return volume[:, y_idx, :]
