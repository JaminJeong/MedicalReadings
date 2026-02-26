# Medical Readings

DICOM 의료 영상(X-ray, CT)을 LLM으로 분석하여 판독문을 생성하는 데모 서비스입니다.
Streamlit 웹 인터페이스와 Docker Compose 실행 환경을 제공합니다.

---

## 주요 기능

### 영상 뷰어 (Viewer)
- **X-ray**: 단일 DICOM 파일 업로드 및 시각화
- **CT**: DICOM 폴더를 ZIP으로 업로드, Axial / Sagittal / Coronal 3면 동시 표시
- **Window / Level**: 슬라이더로 밝기·대비 실시간 조절
- **CT Preset**: Bone, Lung, Soft Tissue, Brain, Abdomen 등 8종 제공
- **Crosshair**: CT 3면 뷰 간 위치 연동 표시

### LLM 판독 분석 (LLM Analysis)
- Viewer에서 로드한 이미지를 그대로 LLM에 전달
- 4종 LLM 지원: **GPT-4o**, **Gemini 1.5 Pro**, **MedGemma 4B-IT**, **Ollama**
- 스트리밍 출력 (GPT, Gemini, Ollama)
- 한국어 / 영어 판독 프롬프트 템플릿 제공
- 판독문 Markdown 파일 다운로드

---

## 스크린샷

```
┌─────────────────────────────────────────────┐
│  사이드바 메뉴                               │
│  ├── Home                                   │
│  ├── Viewer      ← X-ray / CT 영상 뷰어     │
│  └── LLM Analysis ← 판독문 생성              │
└─────────────────────────────────────────────┘
```

---

## 시스템 요구사항

| 항목 | 최소 사양 |
|------|----------|
| OS | Linux / macOS / Windows (WSL2 권장) |
| Docker | 24.0+ |
| Docker Compose | 2.0+ |
| RAM | 8GB+ |
| 디스크 | 20GB+ (Ollama 모델 포함) |
| GPU (선택) | NVIDIA GPU, VRAM 8GB+ (MedGemma 또는 Ollama GPU 가속 시) |

---

## 빠른 시작

### 1. 저장소 클론

```bash
git clone https://github.com/your-org/MedicalReadings.git
cd MedicalReadings
```

### 2. 환경변수 설정

```bash
cp .env.example .env
```

`.env` 파일을 열어 사용할 LLM의 API 키를 입력합니다.

```bash
# OpenAI GPT 사용 시
OPENAI_API_KEY=sk-...

# Google Gemini 사용 시
GOOGLE_API_KEY=AIza...

# MedGemma 사용 시 (Hugging Face 계정 필요)
HF_TOKEN=hf_...
```

> Ollama는 별도 API 키 없이 로컬에서 실행됩니다.

### 3. Docker Compose 실행

```bash
docker compose up --build -d
```

빌드 완료 후 http://localhost:8501 에서 접속합니다.

### 4. Ollama Vision 모델 설치 (최초 1회)

```bash
docker compose exec ollama ollama pull llava:13b
```

> 모델 크기는 약 8GB입니다. 경량 모델을 원할 경우 `llava:7b` (~4GB) 를 사용하세요.

---

## 서비스 관리

```bash
# 시작
docker compose up -d

# 중지
docker compose down

# 로그 확인
docker compose logs -f streamlit
docker compose logs -f ollama

# 재빌드 (코드 변경 후)
docker compose up --build -d
```

---

## 사용법

### X-ray 판독

1. 사이드바에서 **Viewer** 선택
2. Modality를 **X-ray** 선택
3. `.dcm` 파일 업로드
4. Window Center / Width 슬라이더로 영상 조정
5. 사이드바에서 **LLM Analysis** 선택
6. LLM 및 프롬프트 템플릿 선택
7. **판독 요청** 버튼 클릭

### CT 판독

1. CT DICOM 폴더를 ZIP으로 압축
   ```bash
   # 예시: ct_folder/ 안에 .dcm 파일들이 있는 경우
   zip -r ct_series.zip ct_folder/
   ```
2. 사이드바에서 **Viewer** 선택
3. Modality를 **CT** 선택
4. ZIP 파일 업로드
5. Axial / Sagittal / Coronal 슬라이더로 슬라이스 탐색
6. Window Preset 또는 슬라이더로 조정
7. **LLM Analysis** 페이지에서 판독 요청

---

## 지원 LLM

| LLM | 종류 | Vision | 의료 특화 | 설정 |
|-----|------|--------|----------|------|
| GPT-4o / GPT-4o-mini | 클라우드 (OpenAI) | ✅ | ❌ | `OPENAI_API_KEY` |
| Gemini 1.5 Pro / Flash | 클라우드 (Google) | ✅ | ❌ | `GOOGLE_API_KEY` |
| MedGemma 4B-IT | 로컬 (HuggingFace) | ✅ | ✅ | `HF_TOKEN` + GPU 권장 |
| Ollama (LLaVA 등) | 로컬 (Ollama 서버) | ✅ | ❌ | 모델 pull 필요 |

### Ollama 추천 Vision 모델

```bash
# 고성능 (8GB VRAM 권장)
docker compose exec ollama ollama pull llava:13b

# 경량 (4GB VRAM 또는 CPU)
docker compose exec ollama ollama pull llava:7b

# LLaMA3 기반 고품질
docker compose exec ollama ollama pull llava-llama3:8b
```

---

## MedGemma 활성화 (선택)

MedGemma는 Google의 의료 영상 특화 Vision-Language 모델입니다.
기본 Docker 이미지에는 포함되지 않으며, 별도 설정이 필요합니다.

**요구사항**: GPU VRAM 8GB+, Hugging Face 계정 및 모델 접근 승인

1. `app/Dockerfile`에서 아래 주석을 해제합니다.

   ```dockerfile
   # 아래 두 줄 주석 해제
   COPY requirements-medgemma.txt .
   RUN pip install --no-cache-dir -r requirements-medgemma.txt
   ```

2. `.env`에 HuggingFace 토큰 입력

   ```bash
   HF_TOKEN=hf_...
   ```

3. 재빌드

   ```bash
   docker compose up --build -d
   ```

> HuggingFace에서 `google/medgemma-4b-it` 모델 접근 동의가 필요합니다.
> https://huggingface.co/google/medgemma-4b-it

---

## GPU 지원 (Ollama)

NVIDIA GPU가 있을 경우 `docker-compose.yml`의 `ollama` 서비스에서 아래 블록 주석을 해제합니다.

```yaml
ollama:
  ...
  deploy:
    resources:
      reservations:
        devices:
          - driver: nvidia
            count: all
            capabilities: [gpu]
```

NVIDIA Container Toolkit이 설치되어 있어야 합니다.

```bash
# NVIDIA Container Toolkit 설치 확인
docker run --rm --gpus all nvidia/cuda:12.0-base nvidia-smi
```

---

## 프로젝트 구조

```
MedicalReadings/
├── docker-compose.yml
├── .env.example
├── docs/                        # 설계 문서
│   ├── plan.md
│   ├── structure.md
│   ├── environment.md
│   └── llm.md
└── app/
    ├── Dockerfile
    ├── requirements.txt
    ├── requirements-medgemma.txt
    ├── main.py                  # 홈 페이지
    ├── pages/
    │   ├── 1_Viewer.py          # 영상 뷰어
    │   └── 2_LLM_Analysis.py   # LLM 판독
    ├── components/
    │   ├── xray_viewer.py       # X-ray 뷰어 컴포넌트
    │   └── ct_viewer.py         # CT 3-plane 뷰어 컴포넌트
    ├── core/
    │   ├── dicom_loader.py      # DICOM 파싱
    │   ├── image_processor.py   # Window/Level, PNG 변환
    │   └── ct_volume.py         # CT 3D 볼륨 처리
    ├── llm/
    │   ├── base.py              # 공통 인터페이스
    │   ├── gpt_client.py
    │   ├── gemini_client.py
    │   ├── medgemma_client.py
    │   └── ollama_client.py
    └── utils/
        ├── file_utils.py        # ZIP 처리
        └── prompt_templates.py  # 판독 프롬프트
```

---

## 문제 해결

**Q. 포트 8501이 이미 사용 중입니다.**

`docker-compose.yml`의 포트 매핑을 변경합니다.
```yaml
ports:
  - "8502:8501"  # 호스트 포트를 8502로 변경
```

**Q. CT 업로드가 느립니다.**

CT 시리즈는 수백 장의 DICOM 슬라이스로 구성되어 있어 로딩에 시간이 걸립니다.
ZIP 파일 크기를 줄이거나, 슬라이스 수를 줄인 서브셋을 사용하세요.

**Q. Ollama 모델 응답이 없습니다.**

```bash
# Ollama 서비스 상태 확인
docker compose exec ollama ollama list

# 서비스 재시작
docker compose restart ollama
```

**Q. MedGemma 로딩 중 CUDA OOM 오류가 발생합니다.**

VRAM이 부족한 경우 `medgemma_client.py`에서 `device_map="cpu"`로 변경하세요.
CPU 모드는 추론 속도가 매우 느립니다 (수 분 소요).

**Q. Gemini API에서 이미지 분석이 거부됩니다.**

Gemini의 Safety Filter가 의료 영상을 차단할 수 있습니다.
`gemini_client.py`에서 `safety_settings`를 조정하거나 GPT/Ollama를 사용하세요.

---

## 주의사항

> 본 서비스는 **데모 목적**으로 제작되었습니다.
> LLM이 생성한 판독문은 **의료 진단의 근거로 사용할 수 없습니다.**
> 실제 임상 환경에서는 반드시 전문 영상의학과 의사의 판독이 필요합니다.

---

## 라이선스

MIT License
