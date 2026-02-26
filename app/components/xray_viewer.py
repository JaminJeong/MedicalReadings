"""X-ray DICOM 뷰어 컴포넌트"""

from io import BytesIO

import matplotlib.pyplot as plt
import numpy as np
import pydicom
import streamlit as st

from core.dicom_loader import extract_pixel_array, get_window_defaults
from core.image_processor import apply_windowing


def render_xray_viewer(ds: pydicom.Dataset) -> None:
    """X-ray 뷰어 렌더링 (W/L 슬라이더 포함)"""

    pixel_array = extract_pixel_array(ds)
    default_wc, default_ww = get_window_defaults(ds)
    pmin = float(pixel_array.min())
    pmax = float(pixel_array.max())

    # 레이아웃: 이미지(좌) | 컨트롤(우)
    img_col, ctrl_col = st.columns([3, 1])

    with ctrl_col:
        st.markdown("### Window Settings")

        wc = st.slider(
            "Window Center",
            min_value=int(pmin),
            max_value=int(pmax),
            value=int(np.clip(default_wc, pmin, pmax)),
            key="xray_wc",
        )
        ww = st.slider(
            "Window Width",
            min_value=1,
            max_value=max(1, int(pmax - pmin)),
            value=int(np.clip(default_ww, 1, pmax - pmin)),
            key="xray_ww",
        )
        invert = st.checkbox("Invert", key="xray_invert")

        st.markdown("---")
        st.markdown("### Image Info")
        st.markdown(f"**Size**: {pixel_array.shape[1]} × {pixel_array.shape[0]}")
        st.markdown(f"**Pixel range**: [{int(pmin)}, {int(pmax)}]")
        st.markdown(f"**Modality**: {getattr(ds, 'Modality', 'N/A')}")

        patient = str(getattr(ds, "PatientName", "N/A"))
        study_date = str(getattr(ds, "StudyDate", "N/A"))
        st.markdown(f"**Patient**: {patient}")
        st.markdown(f"**Study Date**: {study_date}")

    with img_col:
        # W/L 적용
        windowed = apply_windowing(pixel_array, wc, ww)
        if invert:
            windowed = 255 - windowed

        # matplotlib 렌더링 (검은 배경)
        fig, ax = plt.subplots(figsize=(8, 8), facecolor="black")
        ax.imshow(windowed, cmap="gray", aspect="equal", interpolation="bilinear")
        ax.axis("off")
        plt.tight_layout(pad=0)

        buf = BytesIO()
        fig.savefig(buf, format="png", dpi=150, bbox_inches="tight", facecolor="black")
        plt.close(fig)
        buf.seek(0)
        img_bytes = buf.getvalue()

        st.image(img_bytes, use_column_width=True)

        # LLM 페이지에서 재사용할 수 있도록 세션 저장
        st.session_state.current_image_bytes = img_bytes
