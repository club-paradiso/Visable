# Visable

> 한국 비자·체류 정보를 더 명확하게 보고, 찾고, 이해하기 위한 civic-tech 플랫폼.

**Visable**은 대한민국의 비자·체류자격, 출입국 절차, 관련 서류와 공식 근거를 한곳에서 탐색할 수 있도록 만드는 정보 안내 서비스입니다.

이 프로젝트의 목표는 행정정보를 그럴듯하게 요약하는 것이 아닙니다. 출입국 분야에서 잘못된 한 문장은 실제 신청, 체류, 취업, 신고에 영향을 줄 수 있기 때문에 Visable은 **답을 많이 하는 것보다 근거 없는 답을 하지 않는 것**을 우선합니다.

## 주요 기능

- **비자·체류자격 탐색** — 체류자격 코드, 목적, 세부 자격별 정보 확인
- **통합 검색** — 비자, 체류, 서류, 절차와 관련된 정보를 한 번에 검색
- **절차별 안내** — 사증발급, 체류기간 연장, 체류자격 변경, 외국인등록, 근무처 변경·추가 등 서로 다른 행정 절차를 구분
- **서류 정보 구조화** — 제출 서류, 참고사항, 검토 필요 상태를 데이터 기반으로 표시
- **Waymaker / Visable AI** — 저장된 데이터와 검색된 근거를 바탕으로 비자·체류 질문에 답변
- **Employment Helper** — 자유 서술형 직무 설명을 구조화하고 고용 관련 탐색을 보조
- **Nationality / Naturalization tools** — 국적·귀화 관련 정보와 인터뷰 연습 기능
- **Enforcement Intelligence** — 출입국 사범처리 관련 법적 기준과 공개 근거를 분리해 보여주는 분석 도구
- **법령·근거 연결** — 가능한 경우 공식 법령 및 출처를 검색·검증하는 grounding 흐름 사용
- **다국어 UI** — 한국어, 영어, 중국어를 중심으로 제공 및 개선 중

## 현재 상태

**Active development**

Visable은 단순한 정적 비자 목록을 넘어 검색, AI 안내, 국적·귀화, 고용, 법률 리서치, 사범처리 분석 등 여러 기능을 하나의 출입국 정보 경험으로 통합하는 방향으로 개발되고 있습니다.

저장소에는 프로덕션 코드뿐 아니라 공식 매뉴얼 동기화 도구, 데이터 검증 스크립트, QA 문서, AI 안전성 테스트와 실험 코드도 함께 포함되어 있습니다.

일부 데이터는 여전히 수동 검토가 필요할 수 있으며, Visable은 법률 자문이나 출입국·외국인관서의 공식 판단을 대체하지 않습니다.

## 핵심 원칙

1. **모르면 모른다고 한다.** 근거가 없는 행정정보를 만들어내지 않습니다.
2. **사증과 체류를 섞지 않는다.** 해외에서 비자를 발급받는 절차와 국내 체류 절차를 별개로 취급합니다.
3. **상위 체류자격과 세부 체류자격을 구분한다.** 특정 하위 코드의 요건을 상위 코드 전체의 요건처럼 확대하지 않습니다.
4. **공식 근거를 우선한다.** 내부 데이터, 법령, 공식 매뉴얼과 답변이 충돌하면 확정적인 표현을 피합니다.
5. **불확실성을 숨기지 않는다.** 검토 필요, 출처 부족, 공식 확인 필요 같은 상태를 사용자에게 노출합니다.
6. **LLM이 행정 판단을 대신하지 않는다.** AI는 검색·정리·설명을 돕지만 최종 허가 여부나 법적 결론을 임의로 결정하지 않습니다.

자세한 데이터 작업 규칙은 [`CLAUDE.md`](./CLAUDE.md)를 참고하세요.

## Architecture

| Layer | Implementation |
| --- | --- |
| Frontend | Vanilla HTML / CSS / JavaScript |
| Main data | JSON-based visa, document, i18n and grounding datasets |
| Backend | FastAPI + serverless API surfaces |
| AI routing | OpenRouter first, optional Groq fallback |
| Optional local fallback | Ollama scaffold |
| Law grounding | Korean Open Law API and source-grounded retrieval flows |
| Deployment | Static frontend + backend deployment configuration |
| Validation | Python, Node.js and shell-based repository checks |

Visable의 AI 기능은 프론트엔드에서 모델 제공자에 직접 연결하지 않고 서버 측 API를 통해 동작하도록 구성되어 있습니다.

현재 AI 런타임에는 Waymaker, 통합 검색 AI Overview, 고용 해석, 국적·귀화 코치, 법률 리서치, Enforcement Intelligence 등이 포함되어 있으며, 가능한 경우 deterministic retrieval과 validation을 LLM 호출보다 먼저 수행합니다.

## Repository map

```text
.
├── index.html                  # Visable main surface
├── ai.html                     # Waymaker / AI experience
├── enforcement.html            # Enforcement Intelligence
├── new-home.html               # nationality / naturalization surface
├── assets/                     # frontend assets, styles and scripts
├── data/                       # frontend datasets and i18n
├── api/                        # serverless API surfaces
├── backend/                    # FastAPI backend
│   ├── paradiso_backend.py     # legacy filename; current Visable backend
│   ├── data/                   # backend deploy-context data copies
│   ├── services/               # backend services
│   └── tests/                  # regression tests
├── docs/                       # audits, architecture and policy documents
├── scripts/                    # validation, sync and evaluation tools
├── visa_data.json              # canonical visa/status data
├── doc_master.json             # canonical document metadata
├── DESIGN.md                   # design system / visual direction
└── QA_AUDIT_REPORT.md          # QA audit
```

## 로컬 실행

프론트엔드는 별도의 빌드 단계 없이 정적 서버에서 실행할 수 있습니다.

```bash
python3 -m http.server 8080
```

브라우저에서 다음 주소를 엽니다.

```text
http://localhost:8080/
```

AI 및 일부 분석 기능은 별도의 백엔드가 필요합니다.

### Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn paradiso_backend:app --reload --port 8000
```

Windows PowerShell:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
uvicorn paradiso_backend:app --reload --port 8000
```

`paradiso_backend.py`와 일부 `PARADISO_*` 명칭은 리브랜딩 이전부터 유지된 **레거시 내부 식별자**입니다. 현재 서비스명은 **Visable**이며, 해당 이름들이 현재 브랜드를 의미하지는 않습니다.

환경변수와 백엔드 실행 세부사항은 [`backend/README.md`](./backend/README.md)를 참고하세요.

## Repository validation

저장소 루트에서 전체 검증:

```bash
bash scripts/check_repo.sh
```

백엔드 회귀 테스트:

```bash
python3 backend/tests/test_paradiso_backend.py
```

네트워크가 제한된 개발 환경에서는 제한 모드를 사용할 수 있습니다.

```bash
ALLOW_BACKEND_TEST_SKIP=1 bash scripts/check_repo.sh
```

이 모드는 정적 검사와 오프라인 가능한 검증을 위한 것이며, 실제 CI 또는 프로덕션 검증을 대체하지 않습니다.

## Data safety

핵심 데이터 파일은 무작정 일괄 포맷팅하거나 자동 재작성하지 않습니다.

특히 다음 파일은 보호 대상으로 취급합니다.

- `visa_data.json`
- `backend/data/visas.json`
- `doc_master.json`
- `backend/data/doc_master.json`

canonical 데이터 수정 후에는 동기화와 검증을 수행합니다.

```bash
python3 scripts/sync_visa_data.py
bash scripts/check_repo.sh
```

OCR 또는 추출 텍스트는 감사와 비교를 위한 보조자료일 뿐이며, 그 자체로 새로운 행정 요건을 만들어내는 근거로 사용하지 않습니다.

## AI safety model

Visable의 AI 경로는 가능한 한 **retrieval / deterministic logic → validation → LLM synthesis** 순서로 동작합니다.

주요 원칙은 다음과 같습니다.

- 모델이 검색되지 않은 법령, 판례, 서류 요건을 지어내지 못하도록 제한
- 세부 체류자격 규칙을 상위 자격 전체에 확대하지 않음
- 고용 해석 AI가 직접 KSCO/KSIC 코드나 취업 허가 여부를 결정하지 않도록 분리
- Enforcement Intelligence에서 AI가 임의의 확률이나 법적 범위를 생성하지 않도록 deterministic baseline 우선
- provider 장애 시 허구의 답을 생성하는 대신 제한된 fallback 결과를 반환
- AI 결과와 deterministic 검색 결과를 분리해, AI 기능이 실패해도 기본 검색이 함께 무너지지 않도록 구성

현행 AI 구조는 [`docs/ai/AI_RUNTIME_INVENTORY.md`](./docs/ai/AI_RUNTIME_INVENTORY.md)를 우선 참고하세요. 오래된 AI 설계 문서는 현재 코드와 다를 수 있습니다.

## Legacy naming

이 저장소는 과거 다른 브랜드명으로 개발된 이력이 있어 일부 오래된 문서, 함수명, 테스트명, 파일명에 `Paradiso` 또는 `PARADISO_*` 문자열이 남아 있습니다.

**이들은 현재 서비스 브랜드가 아닙니다.**

현재 사용자-facing 서비스명과 저장소의 기준 브랜드는 **Visable**입니다. 신규 문서와 사용자-facing 카피에서는 Visable을 기준으로 작성해야 하며, 레거시 명칭은 호환성 또는 역사적 문맥이 필요한 경우에만 유지합니다.

## Official-source reminder

Visable은 비공식 civic-tech 프로젝트입니다.

실제 비자·체류 신청, 신고, 허가 및 처분에 관한 최종 판단은 관계 법령과 관할 기관의 최신 기준을 따릅니다. 중요한 절차를 진행하기 전에는 HiKorea, 출입국·외국인정책본부, 관할 출입국·외국인관서 또는 재외공관의 최신 안내를 다시 확인하세요.

## Third-party notices

- [`ATTRIBUTIONS.md`](./ATTRIBUTIONS.md)
- [`THIRD_PARTY_NOTICES.md`](./THIRD_PARTY_NOTICES.md)

---

**Visable — visa and stay information, made visible.**
