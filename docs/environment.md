# 실행 환경 (Docker Compose)

## 아키텍처 개요

```
┌─────────────────────────────────────────────┐
│              Docker Compose                 │
│                                             │
│  ┌─────────────┐      ┌──────────────────┐  │
│  │  streamlit  │      │     ollama       │  │
│  │  (port 8501)│      │  (port 11434)    │  │
│  │             │─────▶│                  │  │
│  │  Streamlit  │      │  Vision 모델     │  │
│  │  Web App    │      │  (llava 등)      │  │
│  └─────────────┘      └──────────────────┘  │
│         │                                   │
│         ▼ (외부 API)                        │
│   Gemini / GPT / MedGemma (HuggingFace)    │
└─────────────────────────────────────────────┘
```

---

## Docker Compose 서비스 구성

### 서비스 1: `streamlit`

| 항목 | 내용 |
|------|------|
| 베이스 이미지 | `python:3.11-slim` |
| 포트 | `8501:8501` |
| 볼륨 | `./app:/app`, `./data/uploads:/tmp/uploads` |
| 환경변수 | `.env` 파일에서 주입 |
| 의존성 | `ollama` 서비스 |
| 헬스체크 | `curl -f http://localhost:8501/_stcore/health` |

**Dockerfile 주요 내용:**
```dockerfile
FROM python:3.11-slim

# 시스템 의존성 (pydicom, matplotlib, scipy 등)
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8501
CMD ["streamlit", "run", "main.py", \
     "--server.port=8501", \
     "--server.address=0.0.0.0", \
     "--server.maxUploadSize=2048"]
```

**주요 설정:**
- `--server.maxUploadSize=2048` : CT zip 업로드를 위해 2GB까지 허용
- `--server.fileWatcherType=none` : 컨테이너 환경에서 파일 감시 비활성화

---

### 서비스 2: `ollama`

| 항목 | 내용 |
|------|------|
| 이미지 | `ollama/ollama:latest` |
| 포트 | `11434:11434` |
| 볼륨 | `ollama_models:/root/.ollama` (named volume, 모델 영속화) |
| GPU | NVIDIA GPU 사용 시 `deploy.resources.reservations` 설정 |
| 헬스체크 | `curl -f http://localhost:11434/api/tags` |

**GPU 지원 설정 (선택적):**
```yaml
deploy:
  resources:
    reservations:
      devices:
        - driver: nvidia
          count: all
          capabilities: [gpu]
```

GPU가 없는 환경에서는 해당 블록을 제거하고 CPU 모드로 실행.

---

## `docker-compose.yml` 전체 구조

```yaml
version: '3.8'

services:
  streamlit:
    build:
      context: ./app
      dockerfile: Dockerfile
    ports:
      - "8501:8501"
    volumes:
      - ./app:/app
      - uploads:/tmp/uploads
    env_file:
      - .env
    environment:
      - OLLAMA_HOST=http://ollama:11434
    depends_on:
      ollama:
        condition: service_healthy
    restart: unless-stopped

  ollama:
    image: ollama/ollama:latest
    ports:
      - "11434:11434"
    volumes:
      - ollama_models:/root/.ollama
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:11434/api/tags"]
      interval: 30s
      timeout: 10s
      retries: 5
    restart: unless-stopped

volumes:
  ollama_models:
  uploads:
```

---

## 환경변수 (`.env`)

```bash
# OpenAI
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o

# Google Gemini
GOOGLE_API_KEY=AIza...
GEMINI_MODEL=gemini-1.5-pro

# MedGemma (Hugging Face)
HF_TOKEN=hf_...
MEDGEMMA_MODEL=google/medgemma-4b-it

# Ollama
OLLAMA_HOST=http://ollama:11434
OLLAMA_MODEL=llava:13b

# 앱 설정
MAX_UPLOAD_SIZE_MB=2048
TEMP_DIR=/tmp/uploads
```

---

## `requirements.txt` 주요 패키지

```
# Streamlit
streamlit>=1.32.0

# DICOM
pydicom>=2.4.0

# 이미지 처리
numpy>=1.26.0
scipy>=1.12.0
Pillow>=10.0.0
matplotlib>=3.8.0

# LLM 클라이언트
openai>=1.20.0
google-generativeai>=0.5.0
ollama>=0.1.8

# MedGemma (로컬 추론)
torch>=2.2.0
transformers>=4.40.0
accelerate>=0.28.0

# 유틸리티
python-dotenv>=1.0.0
```

> **Note**: MedGemma 로컬 추론 시 VRAM 최소 8GB 필요 (4B 모델 기준).
> CPU 전용 환경에서는 `torch` 설치 생략 가능하며 MedGemma 선택 시 안내 메시지 표시.

---

## 실행 방법

### 최초 실행

```bash
# 1. 환경변수 설정
cp .env.example .env
# .env 파일에 API 키 입력

# 2. 컨테이너 빌드 및 실행
docker compose up --build -d

# 3. Ollama 모델 다운로드 (최초 1회)
docker compose exec ollama ollama pull llava:13b

# 4. 앱 접속
# http://localhost:8501
```

### 일상 실행

```bash
docker compose up -d
docker compose down
docker compose logs -f streamlit
```

### GPU 미지원 환경

`docker-compose.yml`의 `ollama` 서비스에서 `deploy` 블록 전체 제거 후 실행.
Ollama CPU 모드는 속도가 느리므로 소형 모델(llava:7b) 권장.

---

## 포트 충돌 방지

| 서비스 | 기본 포트 | 변경 시 |
|--------|-----------|---------|
| Streamlit | 8501 | `.env`에 `STREAMLIT_PORT` 추가 후 compose 수정 |
| Ollama | 11434 | 외부 노출 불필요 시 `ports` 제거 가능 |
