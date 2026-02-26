import os
import shutil
import sys
import tempfile
import zipfile
from io import BytesIO

# 앱 루트를 sys.path에 추가 (컴포넌트/코어 임포트 보장)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st

from components.ct_viewer import render_ct_viewer
from components.xray_viewer import render_xray_viewer
from core.ct_volume import build_volume
from core.dicom_loader import load_ct_series, load_xray

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
    st.subheader("CT DICOM Viewer")

    st.info(
        "CT DICOM 파일들이 담긴 폴더를 ZIP으로 압축하여 업로드하세요. "
        "(폴더 내 .dcm 파일 포함)"
    )

    uploaded = st.file_uploader(
        "CT DICOM ZIP 파일 업로드",
        type=["zip"],
        key="ct_upload",
    )

    if uploaded is not None:
        temp_dir = None
        with st.spinner("CT 시리즈 로딩 중... 파일 수에 따라 시간이 걸릴 수 있습니다."):
            try:
                temp_dir = tempfile.mkdtemp(prefix="ct_")
                with zipfile.ZipFile(BytesIO(uploaded.read()), "r") as zf:
                    zf.extractall(temp_dir)

                datasets = load_ct_series(temp_dir)
                volume, spacing = build_volume(datasets)

                st.session_state.modality = "ct"
                st.session_state.ct_volume = volume
                st.session_state.ct_spacing = spacing
                st.success(
                    f"로드 완료: {len(datasets)}장 슬라이스 | "
                    f"볼륨: {volume.shape[2]}×{volume.shape[1]}×{volume.shape[0]}"
                )
            except Exception as e:
                st.error(f"CT 로드 실패: {e}")
            finally:
                if temp_dir:
                    shutil.rmtree(temp_dir, ignore_errors=True)

    if (
        st.session_state.get("modality") == "ct"
        and st.session_state.get("ct_volume") is not None
    ):
        render_ct_viewer(
            st.session_state.ct_volume,
            st.session_state.ct_spacing,
        )
    elif st.session_state.get("modality") != "ct":
        st.info("CT DICOM ZIP 파일을 업로드하세요.")

# ── 하단 안내 ────────────────────────────────────────────────────────────────
if st.session_state.get("current_image_bytes"):
    st.markdown("---")
    st.success("현재 뷰 이미지가 저장되었습니다. LLM Analysis 페이지에서 판독을 요청하세요.")
