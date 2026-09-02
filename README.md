# Visable / Paradiso

> 대한민국 비자·체류 정보를 조금 덜 미로처럼 만들기 위한 civic-tech 프로젝트.

**Visable**은 이 저장소의 이름이고, 현재 제품과 문서에서 사용하는 서비스명은 **Paradiso**입니다.

Paradiso는 대한민국의 비자 및 체류자격 정보를 탐색하고, 필요한 절차와 서류를 구조화해서 확인하고, AI에게 관련 질문을 할 수 있도록 만든 정보 안내 플랫폼입니다.

단, 출입국 행정은 "대충 비슷하겠지"가 꽤 위험한 분야입니다. 그래서 이 프로젝트는 답을 많이 하는 것보다 **근거 없는 답을 하지 않는 것**을 더 중요하게 봅니다.

## What it does

- **체류자격 탐색**: 대한민국의 주요 체류자격을 코드와 목적별로 탐색
- **절차별 정보 분리**: 사증발급, 체류기간 연장, 체류자격 변경, 외국인등록, 근무처 변경·추가 등 서로 다른 절차를 구분
- **서류 정보 구조화**: 필요한 서류와 주의사항을 데이터 기반으로 표시
- **Paradiso AI**: 자연어 질문에 대해 저장된 비자·체류 데이터와 가능한 공식 근거를 바탕으로 답변
- **법령 grounding**: 설정된 환경에서는 국가법령정보 공동활용 API를 이용한 법령 근거 확인 및 감사(audit) 흐름 지원
- **다국어 UI**: 한국어, 영어, 중국어 UI를 중심으로 확장 중
- **검증 도구**: 데이터 동기화, 정적 검사, 백엔드 회귀 테스트, AI golden evaluation을 포함한 저장소 검증 스크립트 제공

## Project status

**Alpha / active development**

이 저장소에는 실제 서비스용 코드와 함께 감사 보고서, 데이터 검증 도구, 디자인 시스템, 소스 모니터링 및 AI 안전성 관련 실험이 함께 들어 있습니다.

현재 데이터 중에는 `verified: false` 또는 수동 검토가 필요한 항목이 존재할 수 있습니다. Paradiso는 법률 자문이나 출입국·외국인관서의 공식 판단을 대체하지 않습니다.

최종 신청 전에는 반드시 **HiKorea, 대한민국 출입국·외국인정책본부, 관할 출입국·외국인관서, 재외공관 등 공식 채널**의 최신 안내를 다시 확인하세요.

## Design principle

Paradiso의 기본 원칙은 단순합니다.

1. **모르면 모른다고 한다.** 근거가 없는 행정정보를 생성하지 않습니다.
2. **사증과 체류를 섞지 않는다.** 비자를 받는 절차와 국내 체류 절차는 별개의 범위로 취급합니다.
3. **상위 코드와 세부 코드를 함부로 합치지 않는다.** 예를 들어 `G-1-5`의 요건을 `G-1` 전체의 요건처럼 보여주지 않습니다.
4. **데이터를 고치기 전에 렌더링 문제인지 확인한다.** 원문 데이터 훼손보다 안전한 표시 로직 수정을 우선합니다.
5. **불확실성을 숨기지 않는다.** 검토 필요, 공식 확인 필요, 근거 부족 같은 상태를 사용자에게 그대로 노출하는 방향을 지향합니다.

자세한 작업 규칙은 [`CLAUDE.md`](./CLAUDE.md)를 참고하세요.

## Architecture

| Layer | Implementation |
| --- | --- |
| Frontend | Vanilla HTML / CSS / JavaScript |
| Main UI | Static frontend pages and JSON datasets |
| Backend | FastAPI |
| AI providers | OpenRouter first, optional Groq fallback |
| Optional private fallback | Ollama scaffold |
| Law grounding | Korean Open Law API integration in audit-oriented flow |
| Backend deployment | Railway configuration included |
| Data | JSON-based visa, document and grounding datasets |
| Validation | Python scripts + shell repository checks + backend tests |

프론트엔드는 빌드 시스템 없이 정적 파일 중심으로 구성되어 있고, AI 및 일부 검색 기능은 별도의 FastAPI 백엔드가 담당합니다.

## Repository map

```text
.
├── index.html                 # main static entry
├── ai.html                    # AI experience
├── enforcement.html           # enforcement-related surface
├── agency-directory/          # agency/directory related assets
├── assets/                    # frontend assets
├── data/                      # frontend datasets and i18n data
├── backend/
│   ├── paradiso_backend.py    # FastAPI application
│   ├── data/                  # backend deploy-context data copies
│   ├── services/              # backend services
│   ├── tests/                 # backend regression tests
│   └── README.md              # backend setup and deployment details
├── docs/                      # audits, design docs, source/data policies
├── scripts/                   # validation, synchronization and evaluation tools
├── doc_master.json            # canonical document metadata
├── DESIGN.md                  # design tokens / visual direction
└── QA_AUDIT_REPORT.md         # pre-launch QA audit
```

## Run the frontend locally

No frontend build step is required.

```bash
python3 -m http.server 8080
```

Then open:

```text
http://localhost:8080/
```

Some AI-backed features require the backend to be running separately.

## Run the backend locally

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn paradiso_backend:app --reload --port 8000
```

Windows PowerShell에서는 가상환경 활성화 명령이 다릅니다.

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
uvicorn paradiso_backend:app --reload --port 8000
```

AI 질문 기능을 사용하려면 환경변수에 지원되는 LLM provider key가 필요합니다. 전체 환경변수와 Railway 배포 방법은 [`backend/README.md`](./backend/README.md)를 참고하세요.

## Validate the repository

저장소 루트에서:

```bash
bash scripts/check_repo.sh
```

백엔드 테스트만 직접 실행하려면:

```bash
python3 backend/tests/test_paradiso_backend.py
```

네트워크가 제한된 환경에서는 정적 검사와 Python syntax check만 수행하도록 제한 모드를 사용할 수 있습니다.

```bash
ALLOW_BACKEND_TEST_SKIP=1 bash scripts/check_repo.sh
```

이 모드는 CI나 실제 배포 검증을 대체하지 않습니다.

## Data update rules

핵심 비자·체류 데이터는 무작정 일괄 포맷팅하거나 자동 재작성하지 않습니다.

특히 다음 파일은 보호 대상으로 취급합니다.

- `visa_data.json`
- `backend/data/visas.json`
- `doc_master.json`
- `backend/data/doc_master.json`

백엔드 배포용 데이터 사본은 canonical 파일과 동기화되어야 합니다. 데이터 수정 후에는 저장소의 동기화 스크립트를 사용하세요.

```bash
python3 scripts/sync_visa_data.py
bash scripts/check_repo.sh
```

OCR 또는 추출 텍스트는 검토를 위한 보조 자료일 뿐, 그 자체가 새로운 행정 요건을 만들어낼 근거가 아닙니다.

## AI behavior

Paradiso AI는 현재 OpenRouter를 우선 사용하도록 설계되어 있으며, 설정에 따라 Groq 또는 실험적인 private fallback 경로를 사용할 수 있습니다.

중요한 점은 모델 이름보다 답변 정책입니다.

- 공식 근거와 내부 데이터가 충돌하면 확정적으로 단정하지 않기
- 세부 체류자격의 규칙을 상위 체류자격 전체에 확대하지 않기
- 정확한 수수료, 법적 결론, 최신 행정 요건처럼 검증이 필요한 정보는 근거 부족 시 제한적으로 답하기
- upstream provider 장애 시 그럴듯한 내용을 지어내기보다 제한된 fallback 안내를 반환하기

관련 문서:

- [`docs/paradiso_ai_golden_evals.md`](./docs/paradiso_ai_golden_evals.md)
- [`docs/paradiso_ai_coverage_matrix.md`](./docs/paradiso_ai_coverage_matrix.md)
- [`docs/agent-skills/PARADISO_CLAIM_VERIFICATION.md`](./docs/agent-skills/PARADISO_CLAIM_VERIFICATION.md)
- [`docs/agent-skills/PARADISO_OFFICIAL_SOURCE_AUDIT.md`](./docs/agent-skills/PARADISO_OFFICIAL_SOURCE_AUDIT.md)

## Known work in progress

Paradiso는 아직 완성품이 아닙니다. 특히 다음 영역은 지속적으로 검증·개선 중입니다.

- 체류자격별 공식 매뉴얼 대조 및 수동 검증
- 중국어를 포함한 다국어 번역 완성도
- 접근성 및 모바일 터치 타깃
- 공식 출처 링크와 문서 변경 모니터링
- AI 답변의 source grounding 및 citation verification
- 오래된 Paradiso/Visable 경로와 문서 참조 정리

현 상태를 냉정하게 보고 싶다면 [`QA_AUDIT_REPORT.md`](./QA_AUDIT_REPORT.md)를 보세요. 프로젝트 소개문보다 감사 보고서가 더 불친절하지만, 적어도 거짓말은 덜 합니다.

## Third-party notices

외부 자료와 라이브러리 관련 고지는 다음 문서를 참고하세요.

- [`ATTRIBUTIONS.md`](./ATTRIBUTIONS.md)
- [`THIRD_PARTY_NOTICES.md`](./THIRD_PARTY_NOTICES.md)

---

**Paradiso is an unofficial civic-tech project.**  
공식 출입국 행정기관의 서비스가 아니며, 실제 신청·신고·허가 여부는 관계 법령과 관할 기관의 최신 판단을 따릅니다.
