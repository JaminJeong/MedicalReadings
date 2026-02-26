# Medical Readings Service - Plan

## 개요

의료 영상(X-ray, CT)을 DICOM 형식으로 입력받아 LLM이 이미지를 분석하고 판독문을 생성하는 데모 서비스.
Streamlit을 프론트엔드로, Docker Compose로 전체 실행 환경을 구성한다.

---

## 서비스 목표

| 항목 | 내용 |
|------|------|
| 입력 | X-ray: 단일 DICOM 파일 / CT: DICOM 파일이 담긴 폴더 |
| 출력 | LLM 판독문 (자연어 리포트) |
| 인터페이스 | Streamlit 웹 앱 |
| 실행 환경 | Docker Compose |
| 지원 LLM | MedGemma, Gemini, GPT, Ollama |

---

## 페이지 구성

### 1. Viewer 페이지

**X-ray 뷰어**
- 단일 DICOM 파일 업로드
- Window / Level 슬라이더로 밝기·대비 조절
- 이미지 표시 (matplotlib 또는 PIL)

**CT 뷰어**
- DICOM 폴더 업로드 (zip 압축 후 업로드 → 서버 측 압축 해제)
- 3-plane 뷰: Axial / Sagittal / Coronal
- 각 plane별 슬라이스 슬라이더
- Window / Level 슬라이더 (Preset: Bone, Lung, Soft Tissue 등)

### 2. LLM 분석 페이지

- 이미지 선택 (Viewer에서 로드된 이미지 재사용 또는 새로 업로드)
- LLM 선택 드롭다운 (MedGemma / Gemini / GPT / Ollama)
- 모델별 파라미터 설정 (model name, temperature 등)
- 분석 요청 프롬프트 입력 (기본 프롬프트 제공)
- 판독문 출력 영역
- 결과 다운로드 (txt / markdown)

---

## 데이터 흐름

```
사용자 업로드 (DICOM / ZIP)
    ↓
Streamlit 앱 (파일 파싱)
    ↓
pydicom → numpy array 변환
    ↓
Viewer: matplotlib 렌더링 (W/L 적용)
    ↓
LLM 분석: DICOM → PNG 변환 → API 호출 or 로컬 모델
    ↓
판독문 → 화면 출력 / 다운로드
```

---

## 기술 스택

| 레이어 | 기술 |
|--------|------|
| Frontend | Streamlit |
| DICOM 파싱 | pydicom |
| 이미지 처리 | numpy, scipy (3D interpolation), PIL, matplotlib |
| LLM 연동 | openai, google-generativeai, ollama (HTTP), transformers (MedGemma) |
| 컨테이너 | Docker, Docker Compose |
| 패키지 관리 | pip + requirements.txt |

---

## 주요 고려사항

### 이미지 변환 전략
- DICOM → numpy array (HU 값 보존)
- Window/Level 적용 → 0–255 정규화 → PNG
- CT의 경우 3D 볼륨 구성 후 각 축으로 슬라이싱

### LLM에 이미지 전달 방식
- **Gemini / GPT-4o**: base64 인코딩된 PNG를 API에 직접 전달
- **MedGemma (로컬)**: Hugging Face transformers 통해 로컬 추론
- **Ollama**: 로컬 Ollama 서버의 `/api/generate` 또는 `/api/chat` 엔드포인트 호출 (vision 지원 모델 사용)

### CT LLM 분석 전략
- 대표 슬라이스 자동 선택 (중앙 슬라이스 or 3-plane 각 중앙)
- 다수 슬라이스 병렬 분석 후 취합 (선택적)

### 보안 / API 키 관리
- `.env` 파일로 API 키 관리
- Docker Compose의 `env_file` 옵션으로 주입

---

## 개발 단계

1. **Phase 1 - 문서화** (현재)
   - plan.md, structure.md, environment.md, llm.md 작성

2. **Phase 2 - 기반 구조**
   - 프로젝트 디렉터리 및 Docker Compose 설정
   - Streamlit 앱 뼈대 (페이지 라우팅)

3. **Phase 3 - Viewer 구현**
   - DICOM 파싱 유틸리티
   - X-ray 뷰어 (W/L)
   - CT 뷰어 (3-plane, 슬라이스)

4. **Phase 4 - LLM 연동**
   - LLM 추상화 인터페이스
   - 각 모델 구현체
   - 분석 페이지 UI

5. **Phase 5 - 통합 및 테스트**
   - 전체 플로우 테스트
   - UI 개선 및 에러 처리
