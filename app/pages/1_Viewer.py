import os
import sys

# 앱 루트를 sys.path에 추가 (컴포넌트/코어 임포트 보장)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st

from components.ct_viewer import render_ct_viewer
from components.xray_viewer import render_xray_viewer
from core.dicom_loader import load_nifti, load_xray

st.set_page_config(
    page_title="Viewer - Medical Readings",
    page_icon="🖼️",
    layout="wide",
)

# 세션 상태 기본값 초기화
for key, val in {
    "modality": None,
    "xray_dataset": None,
    "ct_volume": None,
    "ct_spacing": None,
    "current_image_bytes": None,
}.items():
    if key not in st.session_state:
        st.session_state[key] = val

# ── 페이지 헤더 ──────────────────────────────────────────────────────────────
st.title("Medical Image Viewer")

modality = st.radio(
    "Modality 선택",
    ["X-ray", "CT"],
    horizontal=True,
    key="viewer_modality_radio",
)
st.markdown("---")

# ── X-ray ────────────────────────────────────────────────────────────────────
if modality == "X-ray":
    st.subheader("X-ray DICOM Viewer")

    uploaded = st.file_uploader(
        "X-ray DICOM 파일 업로드 (.dcm)",
        type=["dcm"],
        key="xray_upload",
    )

    if uploaded is not None:
        with st.spinner("DICOM 로딩 중..."):
            try:
                ds = load_xray(uploaded.read())
                st.session_state.modality = "xray"
                st.session_state.xray_dataset = ds
                st.success(f"로드 완료: {uploaded.name}")
            except Exception as e:
                st.error(f"DICOM 로드 실패: {e}")

    if (
        st.session_state.get("modality") == "xray"
        and st.session_state.get("xray_dataset") is not None
    ):
        render_xray_viewer(st.session_state.xray_dataset)
    elif st.session_state.get("modality") != "xray":
        st.info("X-ray DICOM 파일을 업로드하세요.")

# ── CT ───────────────────────────────────────────────────────────────────────
else:
    st.subheader("CT NIfTI Viewer")

    st.info("CT NIfTI 파일(.nii 또는 .nii.gz)을 업로드하세요.")

    uploaded = st.file_uploader(
        "CT NIfTI 파일 업로드",
        type=["nii", "gz"],
        key="ct_upload",
    )

    if uploaded is not None:
        with st.spinner("CT 볼륨 로딩 중..."):
            try:
                volume, spacing = load_nifti(uploaded.read(), uploaded.name)

                st.session_state.modality = "ct"
                st.session_state.ct_volume = volume
                st.session_state.ct_spacing = spacing
                st.success(
                    f"로드 완료: 볼륨 {volume.shape[2]}×{volume.shape[1]}×{volume.shape[0]} "
                    f"| 간격 {spacing[2]:.2f}×{spacing[1]:.2f}×{spacing[0]:.2f} mm"
                )
            except Exception as e:
                st.error(f"CT 로드 실패: {e}")

    if (
        st.session_state.get("modality") == "ct"
        and st.session_state.get("ct_volume") is not None
    ):
        render_ct_viewer(
            st.session_state.ct_volume,
            st.session_state.ct_spacing,
        )
    elif st.session_state.get("modality") != "ct":
        st.info("CT NIfTI 파일을 업로드하세요.")

# ── 하단 안내 ────────────────────────────────────────────────────────────────
if st.session_state.get("current_image_bytes"):
    st.markdown("---")
    st.success("현재 뷰 이미지가 저장되었습니다. LLM Analysis 페이지에서 판독을 요청하세요.")
