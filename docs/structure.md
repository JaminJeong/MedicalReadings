# Project Structure

## 디렉터리 트리

```
MedicalReadings/
├── docker-compose.yml          # 전체 서비스 오케스트레이션
├── .env.example                # 환경변수 예시 (API 키 등)
├── .env                        # 실제 환경변수 (git 제외)
├── .gitignore
├── docs/
│   ├── plan.md                 # 서비스 기획
│   ├── structure.md            # 프로젝트 구조 (현재 파일)
│   ├── environment.md          # 실행 환경 상세
│   └── llm.md                  # LLM 연동 상세
│
├── app/                        # Streamlit 앱 루트
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── main.py                 # Streamlit 진입점 (페이지 라우팅)
│   │
│   ├── pages/
│   │   ├── 1_Viewer.py         # 영상 뷰어 페이지
│   │   └── 2_LLM_Analysis.py   # LLM 분석 페이지
│   │
│   ├── components/
│   │   ├── xray_viewer.py      # X-ray 뷰어 컴포넌트
│   │   └── ct_viewer.py        # CT 뷰어 컴포넌트 (3-plane)
│   │
│   ├── core/
│   │   ├── dicom_loader.py     # DICOM 파일/폴더 로딩 & 파싱
│   │   ├── image_processor.py  # Window/Level, HU → PNG 변환
│   │   └── ct_volume.py        # CT 3D 볼륨 구성 및 슬라이싱
│   │
│   ├── llm/
│   │   ├── base.py             # LLM 추상 기본 클래스
│   │   ├── gemini_client.py    # Google Gemini 연동
│   │   ├── gpt_client.py       # OpenAI GPT 연동
│   │   ├── medgemma_client.py  # MedGemma (로컬 Hugging Face) 연동
│   │   └── ollama_client.py    # Ollama 로컬 서버 연동
│   │
│   └── utils/
│       ├── file_utils.py       # ZIP 압축 해제, 임시 파일 관리
│       └── prompt_templates.py # 기본 판독 프롬프트 템플릿
│
└── ollama/                     # Ollama 서비스 (Docker Compose 서비스)
    └── models/                 # Ollama 모델 볼륨 마운트 경로
```

---

## 핵심 모듈 설명

### `app/main.py`
- Streamlit 멀티페이지 앱의 진입점
- 사이드바 네비게이션: Viewer / LLM Analysis
- 세션 상태 초기화 (업로드된 DICOM 데이터 공유)

### `app/pages/1_Viewer.py`
- 업로드 방식 선택: X-ray (단일 .dcm) / CT (zip 폴더)
- X-ray: `xray_viewer` 컴포넌트 호출
- CT: `ct_viewer` 컴포넌트 호출
- 업로드된 볼륨 데이터를 `st.session_state`에 저장 → LLM 페이지에서 재사용

### `app/pages/2_LLM_Analysis.py`
- Viewer에서 로드한 데이터 사용 or 직접 재업로드
- LLM 선택 → 해당 클라이언트 인스턴스화
- 대표 이미지(PNG) 생성 → LLM API 호출
- 판독문 스트리밍 출력 (지원 모델의 경우)

### `app/components/xray_viewer.py`
```
입력: pydicom Dataset
출력: Streamlit 렌더링 (matplotlib figure)
기능:
  - W/L 슬라이더 (기본값: DICOM 헤더 WindowCenter/WindowWidth)
  - 이미지 반전 토글 (Invert)
  - 줌/패닝 (Streamlit image + st.slider)
```

### `app/components/ct_viewer.py`
```
입력: 3D numpy array (shape: Z x Y x X), spacing
출력: Streamlit 렌더링 (3-panel: Axial / Sagittal / Coronal)
기능:
  - 각 plane별 슬라이스 슬라이더
  - W/L 슬라이더 + Preset (Bone/Lung/Soft Tissue/Brain/Abdomen)
  - 현재 슬라이스 위치를 crosshair로 표시 (선택적)
```

### `app/core/dicom_loader.py`
```
- load_xray(file: BytesIO) → pydicom.Dataset
- load_ct_series(folder: str) → List[pydicom.Dataset] (SliceLocation 정렬)
- extract_pixel_array(ds: Dataset) → np.ndarray (rescale slope/intercept 적용)
```

### `app/core/image_processor.py`
```
- apply_windowing(array, window_center, window_width) → np.ndarray (0-255)
- array_to_png_bytes(array) → bytes
- get_window_presets() → Dict[str, Tuple[int,int]]
  (예: {"Bone": (400, 1800), "Lung": (-600, 1500), "Soft Tissue": (50, 400)})
```

### `app/core/ct_volume.py`
```
- build_volume(datasets: List[Dataset]) → np.ndarray (3D, Z x Y x X)
- get_axial_slice(volume, z_idx) → np.ndarray
- get_sagittal_slice(volume, x_idx) → np.ndarray
- get_coronal_slice(volume, y_idx) → np.ndarray
```

### `app/llm/base.py`
```python
class BaseLLMClient(ABC):
    @abstractmethod
    def analyze(self, image_bytes: bytes, prompt: str, **kwargs) -> str:
        ...

    @abstractmethod
    def stream_analyze(self, image_bytes: bytes, prompt: str, **kwargs) -> Iterator[str]:
        ...
```

---

## 세션 상태 설계 (`st.session_state`)

| 키 | 타입 | 설명 |
|----|------|------|
| `modality` | str | "xray" or "ct" |
| `xray_dataset` | pydicom.Dataset | X-ray DICOM 데이터 |
| `ct_volume` | np.ndarray | CT 3D 볼륨 (Z x Y x X) |
| `ct_spacing` | Tuple[float,float,float] | CT 복셀 간격 (z, y, x) mm |
| `window_center` | int | 현재 Window Center |
| `window_width` | int | 현재 Window Width |
| `selected_llm` | str | 선택된 LLM 이름 |
| `last_report` | str | 마지막 생성 판독문 |

---

## 의존성 관계

```
pages/ → components/ → core/
pages/ → llm/
llm/   → core/ (image_processor)
components/ → core/
```
