import os
import sys

# 앱 루트를 sys.path에 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st

from core.dicom_loader import extract_pixel_array, get_window_defaults, load_xray
from core.image_processor import apply_windowing, array_to_png_bytes
from utils.prompt_templates import PROMPT_TEMPLATES

st.set_page_config(
    page_title="LLM Analysis - Medical Readings",
    page_icon="🤖",
    layout="wide",
)

# 세션 상태 기본값
for key, val in {
    "current_image_bytes": None,
    "last_report": "",
}.items():
    if key not in st.session_state:
        st.session_state[key] = val


# ── LLM 가용성 확인 ──────────────────────────────────────────────────────────
@st.cache_data(ttl=30, show_spinner=False)
def check_availability() -> dict:
    avail = {}

    avail["GPT"] = bool(os.getenv("OPENAI_API_KEY"))
    avail["Gemini"] = bool(os.getenv("GOOGLE_API_KEY"))

    try:
        import torch  # noqa: F401
        import transformers  # noqa: F401
        avail["MedGemma"] = True
    except ImportError:
        avail["MedGemma"] = False

    try:
        import requests
        host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
        resp = requests.get(f"{host}/api/tags", timeout=2)
        avail["Ollama"] = resp.status_code == 200
    except Exception:
        avail["Ollama"] = False

    return avail


# ── 사이드바: LLM 설정 ────────────────────────────────────────────────────────
with st.sidebar:
    st.header("LLM 설정")

    availability = check_availability()

    # 상태 표시
    for name, avail in availability.items():
        icon = "🟢" if avail else "🔴"
        st.markdown(f"{icon} **{name}**")

    st.markdown("---")

    selected_llm = st.radio(
        "LLM 선택",
        list(availability.keys()),
        key="selected_llm_radio",
    )

    if not availability[selected_llm]:
        st.warning(f"{selected_llm}를 사용할 수 없습니다.\n환경변수 또는 서비스를 확인하세요.")

    st.markdown("---")
    st.subheader("모델 파라미터")

    # LLM별 파라미터 UI
    if selected_llm == "GPT":
        gpt_model = st.selectbox("Model", ["gpt-4o", "gpt-4o-mini"])
        temperature = st.slider("Temperature", 0.0, 1.0, 0.3, 0.05)
        max_tokens = st.number_input("Max Tokens", 256, 4096, 2048, step=256)

    elif selected_llm == "Gemini":
        gemini_model = st.selectbox(
            "Model", ["gemini-1.5-pro", "gemini-1.5-flash", "gemini-2.0-flash"]
        )
        temperature = st.slider("Temperature", 0.0, 1.0, 0.3, 0.05)
        max_tokens = st.number_input("Max Tokens", 256, 4096, 2048, step=256)

    elif selected_llm == "MedGemma":
        medgemma_model = st.selectbox(
            "Model", ["google/medgemma-4b-it", "google/medgemma-27b-it"]
        )
        max_new_tokens = st.number_input("Max New Tokens", 128, 1024, 512, step=64)
        if not availability["MedGemma"]:
            st.info(
                "MedGemma 사용을 위해:\n"
                "```\npip install torch transformers accelerate\n```"
            )

    elif selected_llm == "Ollama":
        ollama_model = "llava:13b"
        try:
            import requests as _req
            host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
            resp = _req.get(f"{host}/api/tags", timeout=3)
            if resp.status_code == 200:
                model_list = [m["name"] for m in resp.json().get("models", [])]
                if model_list:
                    ollama_model = st.selectbox("Model", model_list)
                else:
                    st.info("설치된 모델 없음\n`ollama pull llava:13b`")
                    ollama_model = st.text_input("Model name", "llava:13b")
            else:
                ollama_model = st.text_input("Model name", "llava:13b")
        except Exception:
            ollama_model = st.text_input("Model name", "llava:13b")
        temperature = st.slider("Temperature", 0.0, 1.0, 0.3, 0.05)


# ── 메인 콘텐츠 ──────────────────────────────────────────────────────────────
st.title("LLM Image Analysis")

left_col, right_col = st.columns([1, 1])

# ── 왼쪽: 이미지 ─────────────────────────────────────────────────────────────
with left_col:
    st.subheader("이미지")

    current_bytes = st.session_state.get("current_image_bytes")

    if current_bytes:
        st.image(current_bytes, caption="Viewer에서 불러온 이미지", use_column_width=True)
        if st.button("이미지 초기화", key="clear_img"):
            st.session_state.current_image_bytes = None
            st.rerun()
    else:
        st.info("Viewer 페이지에서 이미지를 로드하거나, 아래에서 직접 업로드하세요.")

    with st.expander("직접 업로드 (DICOM / PNG / JPG)", expanded=not bool(current_bytes)):
        direct_upload = st.file_uploader(
            "파일 선택",
            type=["dcm", "png", "jpg", "jpeg"],
            key="llm_direct_upload",
        )
        if direct_upload is not None:
            try:
                if direct_upload.name.lower().endswith(".dcm"):
                    ds = load_xray(direct_upload.read())
                    pixel = extract_pixel_array(ds)
                    wc, ww = get_window_defaults(ds)
                    windowed = apply_windowing(pixel, wc, ww)
                    img_bytes = array_to_png_bytes(windowed)
                else:
                    img_bytes = direct_upload.read()

                st.session_state.current_image_bytes = img_bytes
                st.image(img_bytes, caption=direct_upload.name, use_column_width=True)
            except Exception as e:
                st.error(f"이미지 로드 실패: {e}")

# ── 오른쪽: 분석 ─────────────────────────────────────────────────────────────
with right_col:
    st.subheader("판독 요청")

    prompt_key = st.selectbox("프롬프트 템플릿", list(PROMPT_TEMPLATES.keys()))
    prompt = st.text_area(
        "프롬프트",
        value=PROMPT_TEMPLATES[prompt_key],
        height=200,
        key="llm_prompt_area",
    )

    can_analyze = availability[selected_llm] and bool(
        st.session_state.get("current_image_bytes")
    )

    analyze_btn = st.button(
        f"🔍 {selected_llm}로 판독 요청",
        type="primary",
        disabled=not can_analyze,
        use_container_width=True,
    )

    if not st.session_state.get("current_image_bytes"):
        st.warning("이미지를 먼저 불러오세요.")
    elif not availability[selected_llm]:
        st.warning(f"{selected_llm}가 사용 불가 상태입니다.")

    st.markdown("---")
    st.subheader("판독 결과")

    report_placeholder = st.empty()

    # 이전 판독문 표시
    if st.session_state.get("last_report"):
        report_placeholder.markdown(st.session_state.last_report)

    if analyze_btn:
        image_bytes = st.session_state.current_image_bytes
        report_text = ""

        try:
            # 클라이언트 인스턴스 생성
            if selected_llm == "GPT":
                from llm.gpt_client import GPTClient
                client = GPTClient(
                    model=gpt_model,
                    temperature=temperature,
                    max_tokens=int(max_tokens),
                )
            elif selected_llm == "Gemini":
                from llm.gemini_client import GeminiClient
                client = GeminiClient(
                    model=gemini_model,
                    temperature=temperature,
                    max_tokens=int(max_tokens),
                )
            elif selected_llm == "MedGemma":
                from llm.medgemma_client import MedGemmaClient
                client = MedGemmaClient(
                    model=medgemma_model,
                    max_new_tokens=int(max_new_tokens),
                )
            elif selected_llm == "Ollama":
                from llm.ollama_client import OllamaClient
                client = OllamaClient(
                    model=ollama_model,
                    temperature=temperature,
                )

            # 스트리밍 또는 블로킹 분석
            if client.supports_streaming:
                report_placeholder.markdown("분석 중...")
                for chunk in client.stream_analyze(image_bytes, prompt):
                    report_text += chunk
                    report_placeholder.markdown(report_text + " ▌")
                report_placeholder.markdown(report_text)
            else:
                with st.spinner(f"{selected_llm} 분석 중..."):
                    report_text = client.analyze(image_bytes, prompt)
                report_placeholder.markdown(report_text)

            st.session_state.last_report = report_text

        except Exception as e:
            st.error(f"분석 실패: {e}")
            report_text = ""

    # 다운로드 버튼
    if st.session_state.get("last_report"):
        st.download_button(
            "📄 판독문 다운로드 (.md)",
            data=st.session_state.last_report,
            file_name="radiology_report.md",
            mime="text/markdown",
            use_container_width=True,
        )
