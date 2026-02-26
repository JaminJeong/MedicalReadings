import streamlit as st

st.set_page_config(
    page_title="Medical Readings",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded",
)

# 세션 상태 초기화
_defaults = {
    "modality": None,           # "xray" or "ct"
    "xray_dataset": None,       # pydicom.Dataset
    "ct_volume": None,          # np.ndarray (Z x Y x X)
    "ct_spacing": None,         # (z_mm, y_mm, x_mm)
    "current_image_bytes": None, # PNG bytes (뷰어 → LLM 페이지 공유)
    "last_report": "",          # 마지막 판독문
}
for key, val in _defaults.items():
    if key not in st.session_state:
        st.session_state[key] = val

# ── 홈 페이지 ──────────────────────────────────────────────────────────────────
st.title("Medical Readings")
st.markdown("#### AI 기반 의료 영상 판독 서비스")
st.markdown("---")

col1, col2 = st.columns(2)

with col1:
    st.markdown(
        """
        ### 🖼️ Viewer
        - X-ray DICOM 단일 파일 뷰어
        - CT DICOM 3-plane 뷰어 (Axial / Sagittal / Coronal)
        - Window / Level 슬라이더 조절
        - CT Window Preset (Bone, Lung, Soft Tissue 등)
        """
    )
    if st.button("Viewer 열기", use_container_width=True, type="primary"):
        st.switch_page("pages/1_Viewer.py")

with col2:
    st.markdown(
        """
        ### 🤖 LLM Analysis
        - GPT-4o / GPT-4o-mini (OpenAI)
        - Gemini 1.5 Pro / Flash (Google)
        - MedGemma 4B-IT (로컬, 의료 특화)
        - Ollama Vision 모델 (로컬)
        """
    )
    if st.button("LLM 분석 열기", use_container_width=True, type="primary"):
        st.switch_page("pages/2_LLM_Analysis.py")

st.markdown("---")
st.info("사이드바 메뉴에서 페이지를 선택하거나 위 버튼을 클릭하세요.")

# 현재 로드 상태 표시
with st.expander("현재 세션 상태", expanded=False):
    modality = st.session_state.get("modality")
    if modality == "xray":
        ds = st.session_state.get("xray_dataset")
        if ds:
            st.success(f"X-ray 로드됨: {getattr(ds, 'Modality', 'N/A')} | {ds.pixel_array.shape}")
    elif modality == "ct":
        vol = st.session_state.get("ct_volume")
        if vol is not None:
            st.success(f"CT 로드됨: {vol.shape} (Z x Y x X)")
    else:
        st.info("로드된 영상 없음")

    if st.session_state.get("last_report"):
        st.success("판독문 생성됨 (LLM Analysis 페이지에서 확인)")
