# LLM 연동 상세

## 지원 LLM 목록

| LLM | 제공 방식 | Vision 지원 | 의료 특화 | API 키 필요 |
|-----|----------|------------|----------|-----------|
| GPT-4o / GPT-4o-mini | OpenAI API (클라우드) | O | X | O |
| Gemini 1.5 Pro / Flash | Google AI API (클라우드) | O | X | O |
| MedGemma 4B-IT | Hugging Face (로컬) | O | O | HF Token |
| Ollama (LLaVA 등) | 로컬 서버 | O (모델 의존) | X | X |

---

## 공통 인터페이스 설계

모든 LLM 클라이언트는 `BaseLLMClient`를 상속하여 동일한 방식으로 호출.

```python
# app/llm/base.py
from abc import ABC, abstractmethod
from typing import Iterator

class BaseLLMClient(ABC):
    """LLM 클라이언트 추상 기본 클래스"""

    @abstractmethod
    def analyze(self, image_bytes: bytes, prompt: str, **kwargs) -> str:
        """이미지와 프롬프트를 받아 판독문 반환 (블로킹)"""
        ...

    def stream_analyze(self, image_bytes: bytes, prompt: str, **kwargs) -> Iterator[str]:
        """스트리밍 판독문 반환 (미지원 모델은 단건 반환으로 폴백)"""
        yield self.analyze(image_bytes, prompt, **kwargs)

    @property
    @abstractmethod
    def model_name(self) -> str:
        ...

    @property
    def supports_streaming(self) -> bool:
        return False
```

---

## 각 LLM 상세

### 1. GPT-4o (OpenAI)

**파일**: `app/llm/gpt_client.py`

**연동 방식**:
- `openai` Python 패키지 사용
- 이미지를 base64 PNG로 인코딩 후 `content` 배열에 포함

**API 호출 구조**:
```json
{
  "model": "gpt-4o",
  "messages": [
    {
      "role": "user",
      "content": [
        {"type": "text", "text": "<프롬프트>"},
        {
          "type": "image_url",
          "image_url": {
            "url": "data:image/png;base64,<base64_string>",
            "detail": "high"
          }
        }
      ]
    }
  ],
  "max_tokens": 2048
}
```

**설정 파라미터**:
| 파라미터 | 기본값 | 설명 |
|---------|--------|------|
| model | gpt-4o | gpt-4o / gpt-4o-mini 선택 가능 |
| temperature | 0.3 | 의료 판독은 낮은 temperature 권장 |
| max_tokens | 2048 | 판독문 최대 길이 |
| detail | high | 이미지 해상도 (high/low) |

**스트리밍**: 지원 (`stream=True`)

---

### 2. Gemini (Google AI)

**파일**: `app/llm/gemini_client.py`

**연동 방식**:
- `google-generativeai` 패키지 사용
- `PIL.Image` 객체를 직접 전달 가능 (bytes → PIL 변환)

**API 호출 구조**:
```python
model = genai.GenerativeModel("gemini-1.5-pro")
response = model.generate_content([
    prompt_text,
    PIL.Image.open(BytesIO(image_bytes))
])
```

**설정 파라미터**:
| 파라미터 | 기본값 | 설명 |
|---------|--------|------|
| model | gemini-1.5-pro | gemini-1.5-pro / gemini-1.5-flash 선택 |
| temperature | 0.3 | |
| max_output_tokens | 2048 | |

**스트리밍**: 지원 (`stream=True`)

**주의사항**:
- Gemini API는 의료 영상 콘텐츠에 대해 safety filter가 강하게 적용될 수 있음
- `safety_settings`를 조정하여 의료 목적임을 명시하는 설정 필요

---

### 3. MedGemma (Google / Hugging Face)

**파일**: `app/llm/medgemma_client.py`

**모델 정보**:
- 모델: `google/medgemma-4b-it` (Instruction-tuned, Vision+Language)
- 의료 영상 특화 Fine-tuned 모델
- 로컬 실행 (인터넷 불필요, 초기 다운로드 이후)

**연동 방식**:
```python
from transformers import AutoProcessor, AutoModelForImageTextToText
import torch

processor = AutoProcessor.from_pretrained("google/medgemma-4b-it")
model = AutoModelForImageTextToText.from_pretrained(
    "google/medgemma-4b-it",
    torch_dtype=torch.bfloat16,
    device_map="auto"
)

inputs = processor(
    text=prompt,
    images=pil_image,
    return_tensors="pt"
).to(model.device)

output = model.generate(**inputs, max_new_tokens=512)
result = processor.decode(output[0], skip_special_tokens=True)
```

**설정 파라미터**:
| 파라미터 | 기본값 | 설명 |
|---------|--------|------|
| model_id | google/medgemma-4b-it | |
| max_new_tokens | 512 | |
| torch_dtype | bfloat16 | fp16/fp32도 가능 |
| device_map | auto | GPU 자동 배치 |

**시스템 요구사항**:
| 환경 | 최소 사양 |
|------|----------|
| GPU VRAM | 8GB (4B 모델 bfloat16) |
| RAM | 16GB |
| 디스크 | ~10GB (모델 가중치) |
| CPU only | 가능하나 추론 속도 매우 느림 (분 단위) |

**HuggingFace 접근**:
- `google/medgemma-4b-it`는 gated 모델 → HF 계정 접근 동의 필요
- `.env`의 `HF_TOKEN` 설정 필수

**캐시 전략**:
- 컨테이너 재시작 시 재다운로드 방지를 위해 HF 캐시를 볼륨으로 마운트
- `~/.cache/huggingface` → Docker volume

**스트리밍**: 미지원 (TextStreamer 사용 가능하나 Streamlit 연동 복잡)

---

### 4. Ollama (로컬 LLM 서버)

**파일**: `app/llm/ollama_client.py`

**연동 방식**:
- `ollama` Python 패키지 또는 직접 HTTP 요청 (`requests`)
- Docker Compose 내부 네트워크로 `http://ollama:11434` 접속

**추천 Vision 모델**:
| 모델 | 크기 | 특징 |
|------|------|------|
| llava:13b | ~8GB | 기본 Vision 모델, 균형 잡힌 성능 |
| llava:7b | ~4GB | 경량, 빠름 |
| llava-llama3:8b | ~5GB | LLaMA3 기반, 고품질 |
| bakllava:7b | ~5GB | Mistral 기반 Vision |
| minicpm-v:8b | ~5GB | 소형 고성능 Vision 모델 |

**API 호출 구조**:
```python
import ollama

response = ollama.chat(
    model="llava:13b",
    messages=[{
        "role": "user",
        "content": prompt_text,
        "images": [image_bytes]  # raw bytes 또는 base64
    }]
)
result = response["message"]["content"]
```

**설정 파라미터**:
| 파라미터 | 기본값 | 설명 |
|---------|--------|------|
| model | llava:13b | UI에서 동적으로 목록 조회 가능 |
| temperature | 0.3 | Modelfile 옵션 |
| num_predict | 2048 | 최대 토큰 수 |

**모델 목록 동적 조회**:
```python
# 설치된 모델 목록 가져오기
models = ollama.list()
vision_models = [m for m in models["models"] if "llava" in m["name"].lower()]
```

**스트리밍**: 지원 (`stream=True`)

---

## 이미지 전처리 전략

### X-ray → LLM 입력

```
DICOM pixel array
    ↓ rescale (slope/intercept)
HU 값 배열
    ↓ Window/Level 적용 (뷰어와 동일 설정 사용)
0-255 uint8 배열
    ↓ PIL → PNG bytes
    ↓ base64 인코딩 (또는 raw bytes)
LLM API 입력
```

### CT → LLM 입력 (대표 슬라이스 전략)

CT는 수백 장의 슬라이스로 구성되어 전체를 LLM에 전달 불가.
아래 전략 중 UI에서 선택 가능하도록 구현:

| 전략 | 설명 | 장단점 |
|------|------|--------|
| 단일 슬라이스 | 뷰어에서 선택한 슬라이스 1장 | 빠름, 정보 제한 |
| 3-plane 중앙 | Axial/Sagittal/Coronal 각 중앙 슬라이스 합성 | 전반적 구조 파악 |
| 등간격 다중 | Axial 기준 N장 (기본 5장) 격자 합성 | 더 많은 정보 |

**3-plane 합성 이미지 예시**:
```
+----------+----------+
|  Axial   | Sagittal |
|          |          |
+----------+----------+
| Coronal  |          |
|          |          |
+----------+----------+
```
→ 하나의 PNG로 합성하여 LLM에 단일 이미지로 전달

---

## 기본 판독 프롬프트 템플릿

**X-ray 판독 (영문)**:
```
You are an expert radiologist. Analyze this chest X-ray image and provide a structured radiology report including:
1. Technical adequacy (rotation, penetration, inspiration)
2. Lung fields (any opacities, consolidations, effusions)
3. Heart (size, contour)
4. Mediastinum
5. Bones and soft tissues
6. Impression and recommendations

Be concise but thorough. Use standard radiological terminology.
```

**CT 판독 (영문)**:
```
You are an expert radiologist. Analyze this CT scan (shown as axial/sagittal/coronal views) and provide a structured radiology report:
1. Technique and contrast
2. Findings by organ system
3. Any incidental findings
4. Impression
5. Recommendations

Use standard radiological terminology.
```

**한국어 판독 프롬프트**:
```
당신은 전문 영상의학과 의사입니다. 다음 영상을 분석하여 표준 판독문 형식으로 작성해주세요:
1. 기술적 적절성
2. 주요 소견
3. 결론 및 인상
4. 추천 사항
```

---

## 오류 처리 및 폴백

| 오류 상황 | 처리 방식 |
|----------|----------|
| API 키 미설정 | 해당 LLM 선택 불가 + 안내 메시지 |
| API Rate Limit | 재시도 버튼 제공 + 대기 시간 표시 |
| MedGemma VRAM 부족 | CPU 모드 폴백 옵션 제공 |
| Ollama 서버 미응답 | 연결 상태 체크 후 안내 메시지 |
| 이미지 너무 큰 경우 | 자동 리사이즈 (최대 1024x1024) |

---

## LLM 선택 UI 설계

```
┌─────────────────────────────────────┐
│ LLM 선택                            │
│ ○ GPT-4o  ○ Gemini  ○ MedGemma  ○ Ollama │
│                                     │
│ [GPT-4o 선택 시]                    │
│ Model: [gpt-4o      ▼]             │
│ Temperature: [━━━●━━] 0.3          │
│ Max Tokens: [2048      ]           │
│                                     │
│ [Ollama 선택 시]                    │
│ Model: [llava:13b   ▼] (설치된 목록) │
│ 상태: ● 연결됨                      │
└─────────────────────────────────────┘
```
