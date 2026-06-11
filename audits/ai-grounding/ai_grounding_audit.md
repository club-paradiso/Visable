# AI 소스 그라운딩 감사 (PHASE 11)

생성: 2026-06-11 · 감사 우선, 수정 차선. 비밀값은 어디에도 출력하지 않음 (이름/존재 여부만).
코드 검색 원본: `audits/ai-grounding/grounding_code_search.txt` (1,068행)

## 1. 현재 채팅 요청 경로

```
ai.html (sendAi)
  → POST {API_BASE}/api/ask          (ai.html ~L2571; API_BASE 기본값
                                      https://web-production-14f9a.up.railway.app,
                                      window.PARADISO_BACKEND_URL로 재정의 가능,
                                      localhost/file://에서는 동일 출처)
  → backend/paradiso_backend.py ask() (L3418, FastAPI)
      1) 비자코드/업무유형 감지 (_detect_visa_codes / _detect_task_type)
      2) 매뉴얼 그라운딩 선택: backend/data/manual_grounding/
         stay_manual_grounding_2026_05.json → _build_grounded_prompt()로
         제출서류·유의사항·원문발췌를 프롬프트에 주입, grounding_sources 반환
      3) 법령 그라운딩: should_attempt_law_grounding() 인텐트 →
         LAW_GROUNDING_MODE ∈ {audit, enabled}일 때만
         KoreanLawClient(open.law.go.kr) 호출 → build_law_evidence_pack()
         정규화 → 프롬프트 주입 + law_sources 메타데이터 반환
      4) OpenRouter 호출 (모델 후보 순차 폴백; 전부 실패 시 결정적 폴백/Groq
         (옵트인)/503)
  → AskResponse (answer + grounding_used + grounding_sources + law_sources
     + law_grounding_status + citation_verification + 70여 메타필드)
  → ai.html appendAiAnswer() → renderGroundingSourcePanel() 출처 패널 렌더
```

## 2. 기존 환경변수 배선 (이름만 — 값 비공개)

| 변수 | 용도 | 미설정 시 동작 |
| --- | --- | --- |
| OPENROUTER_API_KEY | 기본 LLM 공급자 | /api/ask 503 (no_llm_provider_configured) |
| OPENROUTER_MODEL / OPENROUTER_MODEL_CANDIDATES / OPENROUTER_MODEL_COOLDOWN_SECONDS | 모델 선택·폴백 | 기본 후보 사용 |
| GROQ_API_KEY + ALLOW_GROQ_FALLBACK | 옵트인 폴백 공급자 | 폴백 비활성 |
| **LAW_GROUNDING_MODE** | disabled/audit/enabled | **기본 disabled — 법령 조회 자체를 건너뜀** |
| **LAW_API_OC** (선호) / LAW_API_KEY (레거시 폴백) | 국가법령정보 Open API 인증 | 법령 그라운딩 unavailable (오류 아님) |
| LAW_API_BASE_URL / SEARCH_PATH / ARTICLE_PATH / TIMEOUT / CACHE_TTL | 법령 API 세부 | 기본값 |
| PUBLIC_DATA_API_KEY / BASE_URL / VISA_PATH / JOB_PATH | 공공데이터 | 해당 기능 비활성 |
| CORS_ALLOW_ORIGINS, SITE_URL, SITE_TITLE, VISA_DATA_PATH, PORT, LOG_LEVEL | 배포 | 기본값 |

검증 지점: `backend/services/grounding_config.py` L34-51 (LAW_API_OC 우선, LAW_API_KEY 폴백,
`credential_env_name()`이 이름만 보고함), `backend/paradiso_backend.py` L257/3261/3509.
`/health`와 `/api/debug/law-grounding/preflight`는 **불리언/이름만** 노출 (비밀 없음 확인).

## 3. 기존 법령/판례/매뉴얼 검색 경로

- **매뉴얼**: 구현·작동 (요청별 in-memory 선택 → 프롬프트 주입 → grounding_sources 반환 →
  ai.html 출처 패널 렌더). 매칭 실패 시 `_build_ungrounded_korea_scoped_prompt()` +
  Manual-to-law fallback 블록(서류 발명 금지 지시).
- **법령(국가법령정보 Open API)**: 클라이언트(`services/korean_law_client.py`),
  인텐트(`services/law_grounding.py`), 증거팩(`services/law_tools.py`), 인용 검증
  (`services/citation_verifier.py`) 모두 구현됨. 단 **LAW_GROUNDING_MODE 게이트**가
  기본 disabled.
- **판례/유권해석**: `services/` 및 `tests/fixtures/precedent_sources/`에 스캐폴드만 존재,
  **검색 파이프라인에 미배선** (이번 패치 범위 밖 — 후속 계획 문서 참조).

## 4. 실패 지점 분류

| # | 실패 지점 | 분류 | 근거 |
| --- | --- | --- | --- |
| F1 | Railway 환경에서 `LAW_GROUNDING_MODE`가 미설정(=disabled)이면 법령 근거가 답변에 절대 도달하지 않음 | **설정/배선(런타임 확인 필요)** | backend 기본값 disabled (L3509); `.env.example`은 audit 권장 |
| F2 | 매뉴얼·법령·공공데이터가 전부 비어도 사용자에게 "공식 근거 미확인" 경고가 **명시적으로** 노출되지 않는 경우 존재 (출처 패널 자체가 생략될 수 있음) | **프런트 표시 격차 → 본 패치에서 수정** | renderGroundingSourcePanel: rows가 비면 패널 미출력이던 구조 |
| F3 | 판례/유권해석 미배선 | 기능 부재 (후속) | precedent_sources 스캐폴드 |
| F4 | 프런트 하드코딩 Railway URL | 위험 낮음 (재정의 훅 존재) | ai.html L1299-1300 |

## 5. 현재 소스 그라운딩 동작 (수정 전)

- 매뉴얼 매칭 성공 → grounded 프롬프트 + 출처 패널 (정상).
- 매뉴얼 실패 + 법령 disabled → 일반 안내 + `law_grounding_status="disabled"`;
  패널은 상황에 따라 생략 가능 → **근거 없음이 침묵될 수 있음** (F2).
- 법령 enabled + API 실패 → status `unavailable`, 답변은 계속, 허위 인용 없음 (안전).
- 비밀: 리포지토리에 하드코딩 키 없음. URL 정규화 시 OC/key 제거 로직 존재.

## 6. 위험 평가

- 법적 위험: 낮음→중간. F2(침묵된 무근거)가 가장 중요했고 본 패치로 해소.
- 보안 위험: 낮음. 비밀 노출 경로 없음(이번 감사에서 재확인).
- 가용성: OpenRouter 429/503 → 후보 폴백 + 쿨다운 구현됨.

## 7. 이번 패치에서 적용한 국소 수정 (PHASE 11 허용 범위 내)

1. **소스-불가 가드 (ai.html, PARADISO_SOURCE_UNAVAILABLE_GUARD_20260611)**
   - `grounding_used`·`law_grounding_used`·manual/public/law 소스가 모두 부재하면
     출처 패널 최상단에 role="alert" 경고 행을 **항상** 렌더:
     - KO: "공식 근거를 확인하지 못했습니다. 하이코리아/1345 또는 관할 출입국기관에서 재확인하세요."
     - EN: "Official source grounding was not available. Please verify with HiKorea, 1345, or the competent immigration office."
     - zh/zhHant 동등 문구 포함.
   - 고대비 스타일(`.source-unavailable-warning`, "NO SOURCE" 배지) — 색상 단독 의존 아님.
   - 백엔드 무변경: 기존 메타데이터 필드만 소비 (국소·테스트 가능).
2. 그 외 백엔드/제공자/검색 로직 무변경 (요청 경로·쿼터·전송 동작 보존).

## 8. Railway 런타임에서 확인이 필요한 항목 (이 PR로는 검증 불가)

레포에서 안전하게 확인할 수 없는 런타임 상태 — 운영자가 Railway 대시보드에서 확인:
- [ ] `LAW_GROUNDING_MODE` 값 (`audit` 권장 → 검증 후 `enabled`)
- [ ] `LAW_API_OC` 존재 여부 (값 아님 — `/api/debug/law-grounding/preflight`가 불리언으로 보고)
- [ ] `OPENROUTER_API_KEY` 유효성 (`/health`)
- [ ] 적용 후 `scripts/smoke_law_grounding.sh` 실행 (외부 API 불필요한 preflight 포함)

새 키 요청 없음 · 신규 공급자 없음 · 아키텍처 변경 없음 · 비밀 출력 없음.
전면 RAG가 필요한 부분은 구현하지 않고 후속 계획으로 분리: `manual_extraction_rag_plan.md`.
