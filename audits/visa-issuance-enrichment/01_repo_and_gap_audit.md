# Visa Issuance Enrichment Repo And Gap Audit
Generated: 2026-06-12 KST. Scope: repository audit before code changes.
## Executive Summary
- Canonical parent status records in `visa_data.json` / `backend/data/visas.json`: 42.
- Status code occurrences including subcodes/program records: 218 (209 unique; duplicates include code aliases/program overlays where the repo already duplicates codes).
- Procedure packet builder sourceLens exists in `backend/services/procedure_packet_builder.py`; current parent/procedure lens counts: {'unavailable': 208, 'limited': 58, 'contextual': 50, 'source_confirmed': 20}.
- Current parent `visa_issuance` sourceLens counts before this PR: {'unavailable': 39, 'contextual': 3}.
- Main gap: `visa_issuance` is not a first-class separate evidence/data layer; most records have initial/new-application prose in `visa_data.json`, but not structured issuance modes, actors, application channels, or page-bound evidence.
- Existing domestic stay guidance should be preserved. It is concentrated in `visa_data.json` procedures and `backend/data/manual_grounding/structured_requirements_2026_06_01.json`, with user-facing source-confirmed access gated to HIGH + STRUCTURED_EVIDENCE_READY.

## Canonical Files And Logic
| Area | Current files / functions | Audit note |
|---|---|---|
| Canonical visa/status data | `visa_data.json`, `backend/data/visas.json` | Both currently contain the 42 parent records; backend loader prefers `backend/data/visas.json` when present. |
| Scenario/help data | `data/scenario_help_records.json`, `data/removed_from_visa_data_scenario_records_20260608.json`, `backend/record_store_union.py` | Scenario records are wrapped under `records[].record`; migration parity is still explicit. |
| SourceLens rendering/building | `backend/services/procedure_packet_builder.py` (`SOURCE_LENS_LABELS_KO`, `_source_lens`, `build_procedure_packet`) | Packet source lens exists only in backend packet builder; static `index.html` has a separate source evidence panel and procedure badges. |
| Procedure packet builder | `backend/services/procedure_packet_builder.py` | Builds deterministic packets for registration, extension, status change, status grant, workplace change, outside-status activities, reentry, visa issuance. |
| Structured requirements | `backend/data/manual_grounding/structured_requirements_2026_06_01.json`, `backend/structured_requirements.py` | Only HIGH + STRUCTURED_EVIDENCE_READY entries are user-facing source-confirmed. |
| Manual page crosswalk | `docs/data/2026_05_21_manual_json_crosswalk.json` | Useful section page anchors, but it explicitly says location is not data verification. |
| i18n/static UI | `index.html`, `ai.html` inline `UI_TRANSLATIONS` | No separate frontend source files; labels and UI strings are inline. |
| Search rendering | `index.html` functions `renderResults`, `calculateScore`, `getExactQueryMatchRank`, `getPrimaryCodeLikeQuery` | Exact-code routing exists but threshold constants are inconsistent with the current rank return values. |
| Validation/tests | `scripts/check_*.js`, `scripts/check_*.py`, `backend/tests/*` | Existing exact-code, placeholder, data integrity, manual grounding, and backend unit tests are available. |

## Priority Code Current Visa-Issuance State
| Code | Name | Manual visa section/pages | Current visa_issuance lens | Current docs backed | Root cause |
|---|---|---|---|---:|---|
| B-1 | 사증면제협정 | §4 사증면제(B-1) 14-21 | unavailable / 공식근거 확인 불가 | false | not_applicable_but_unclear_ui |
| B-2 | 관광통과·무사증 | §5 관광통과(B-2) 22-24 | unavailable / 공식근거 확인 불가 | false | not_applicable_but_unclear_ui |
| C-3 | 단기방문 | §7 단기방문(C-3) 27-50 | contextual / 관련 공식근거 있음 | false | placeholder_manual_ref |
| D-2 | 유학 | §10 유 학(D-2) 62-69 | unavailable / 공식근거 확인 불가 | false | missing_manual_page_ref |
| D-4 | 일반연수 | §12 일반연수(D-4) 73-87 | unavailable / 공식근거 확인 불가 | false | missing_manual_page_ref |
| D-10 | 구직 | §18 구 직(D-10) 122-135 | unavailable / 공식근거 확인 불가 | false | missing_manual_page_ref |
| E-7 | 특정활동 | §25 특정활동(E-7) 168-277 | unavailable / 공식근거 확인 불가 | false | missing_manual_page_ref |
| E-8 | 계절근로 | §26 계절근로(E-8) 278-283 | unavailable / 공식근거 확인 불가 | false | missing_manual_page_ref |
| E-9 | 비전문취업 | §27 비전문취업(E-9) 284-293 | unavailable / 공식근거 확인 불가 | false | missing_manual_page_ref |
| F-1 | 방문동거 | §29 방문동거(F-1) 297-307 | unavailable / 공식근거 확인 불가 | false | missing_manual_page_ref |
| F-2 | 거주 | §30 거 주(F-2) 308-312 | unavailable / 공식근거 확인 불가 | false | missing_manual_page_ref |
| F-4 | 재외동포 | §32 재외동포(F-4) → §38 see §38 (379-444) | unavailable / 공식근거 확인 불가 | false | missing_manual_page_ref |
| F-6 | 결혼이민 | §34 결혼이민(F-6) 324-335 | contextual / 관련 공식근거 있음 | false | placeholder_manual_ref |
| G-1 | 기타(난민등) | §35 기 타(G-1) 336-342 | unavailable / 공식근거 확인 불가 | false | missing_manual_page_ref |
| H-2 | 방문취업 (신규발급 중단) | §37 방문취업(H-2) → §38 see §38 (379-444) | unavailable / 공식근거 확인 불가 | false | missing_manual_page_ref |

## Status Code Inventory
| Code | Parent | Kind | Name | Occurrences | Visa guidance exists | Dedicated visa procedure | Domestic stay guidance exists | SourceLens exists | Visa lens | Docs backed | Timing backed | Fees backed | Channels backed |
|---|---|---|---|---:|---:|---:|---:|---:|---|---:|---:|---:|---:|
| B-1 |  | parent | 사증면제협정 | 1 | true | false | true | true | unavailable | false | false | false | false |
| B-1-1 | B-1 | subcode | B-1 일반여권 유효 67개국 | 1 | true | false | true | true | unavailable | false | false | false | false |
| B-1-2 | B-1 | subcode | B-1 일시정지 3개국 | 1 | true | false | true | true | unavailable | false | false | false | false |
| B-2 |  | parent | 관광통과·무사증 | 1 | true | false | true | true | unavailable | false | false | false | false |
| B-2-1 | B-2 | subcode | 일반 무사증 (45개국·지역) | 1 | true | false | true | true | unavailable | false | false | false | false |
| B-2-2 | B-2 | subcode | 제주 무사증 입국 | 1 | true | false | true | true | unavailable | false | false | false | false |
| C-3 |  | parent | 단기방문 | 1 | true | true | true | true | contextual | false | false | false | false |
| C-3-1 | C-3 | subcode | 단기일반(친족) | 1 | true | true | true | true | contextual | false | false | false | false |
| C-3-2 | C-3 | subcode | 단체관광 | 1 | true | true | true | true | contextual | false | false | false | false |
| C-3-3 | C-3 | subcode | 의료관광 | 1 | true | true | true | true | contextual | false | false | false | false |
| C-3-4 | C-3 | subcode | 일반상용 | 1 | true | true | true | true | contextual | false | false | false | false |
| C-3-5 | C-3 | subcode | 협정단기상용 | 1 | true | true | true | true | contextual | false | false | false | false |
| C-3-6 | C-3 | subcode | 단기상용 | 1 | true | true | true | true | contextual | false | false | false | false |
| C-3-8 | C-3 | subcode | 동포방문 | 1 | true | true | true | true | contextual | false | false | false | false |
| C-3-9 | C-3 | subcode | 일반관광 | 1 | true | true | true | true | contextual | false | false | false | false |
| C-3-10 | C-3 | subcode | 순수환승 | 1 | true | true | true | true | contextual | false | false | false | false |
| C-3-7 | C-3 | subcode | 도착관광 | 1 | true | true | true | true | contextual | false | false | false | false |
| C-3-11 | C-3 | subcode | 교대선원 (폐지) | 1 | true | true | true | true | contextual | false | false | false | false |
| C-4 |  | parent | 단기취업 | 1 | true | false | true | true | unavailable | false | false | false | false |
| C-4-1 | C-4 | subcode | 계절근로 단기취업 — MOU 체결 외국지자체, 농업 (2025년 발급중단) | 1 | false | false | true | true | unavailable | false | false | false | false |
| C-4-2 | C-4 | subcode | 계절근로 단기취업 — 결혼이민자 추천 친척, 농업 (2025년 발급중단) | 1 | false | false | true | true | unavailable | false | false | false | false |
| C-4-3 | C-4 | subcode | 계절근로 단기취업 — MOU 체결 외국지자체, 어업 (2025년 발급중단) | 1 | false | false | true | true | unavailable | false | false | false | false |
| C-4-4 | C-4 | subcode | 계절근로 단기취업 — 결혼이민자 추천 친척, 어업 (2025년 발급중단) | 1 | false | false | true | true | unavailable | false | false | false | false |
| C-4-5 | C-4 | subcode | 계절근로 외 단기취업 | 1 | true | false | true | true | unavailable | false | false | false | false |
| D-1 |  | parent | 문화예술 | 1 | true | false | true | true | unavailable | true | false | false | false |
| D-1-00 | D-1 | subcode | 문화예술연수 | 1 | true | false | true | true | unavailable | true | false | false | false |
| D-2 |  | parent | 유학 | 1 | true | false | true | true | unavailable | true | false | false | false |
| D-2-1 | D-2 | subcode | 전문학사과정 | 1 | true | false | true | true | unavailable | true | false | false | false |
| D-2-2 | D-2 | subcode | 학사과정 | 1 | true | false | true | true | unavailable | true | false | false | false |
| D-2-3 | D-2 | subcode | 석사과정 | 1 | true | false | true | true | unavailable | true | false | false | false |
| D-2-4 | D-2 | subcode | 박사과정 | 1 | true | false | true | true | unavailable | true | false | false | false |
| D-2-5 | D-2 | subcode | 연구과정 | 1 | true | false | true | true | unavailable | true | false | false | false |
| D-2-6 | D-2 | subcode | 교환학생 | 1 | true | false | true | true | unavailable | true | false | false | false |
| D-2-7 | D-2 | subcode | 일-학습연계 유학 | 1 | true | false | true | true | unavailable | true | false | false | false |
| D-2-8 | D-2 | subcode | 방문학생 | 1 | true | false | true | true | unavailable | true | false | false | false |
| D-3 |  | parent | 기술연수 | 1 | true | false | true | true | unavailable | false | false | false | false |
| D-3-11 | D-3 | subcode | 해외직접기술연수 | 1 | true | false | true | true | unavailable | false | false | false | false |
| D-3-12 | D-3 | subcode | 기술수출연수 | 1 | true | false | true | true | unavailable | false | false | false | false |
| D-3-13 | D-3 | subcode | 플랜트수출연수 | 1 | true | false | true | true | unavailable | false | false | false | false |
| D-3-1 | D-3 | subcode | 구 D-3-1 자격 등록자 (해외투자/기술수출/산업설비, 레거시) | 1 | false | false | true | true | unavailable | false | false | false | false |
| D-4 |  | parent | 일반연수 | 1 | true | false | true | true | unavailable | true | false | false | false |
| D-4-1 | D-4 | subcode | 대학부설어학원 | 2 | true | false | true | true | unavailable | true | false | false | false |
| D-4-2 | D-4 | subcode | 기타기관연수 | 1 | true | false | true | true | unavailable | true | false | false | false |
| D-4-2K | D-4 | subcode | 기업 맞춤형 인턴십(K-Trainee) | 2 | true | false | true | true | unavailable | true | false | false | false |
| D-4-3 | D-4 | subcode | 초중고생연수 | 1 | true | false | true | true | unavailable | true | false | false | false |
| D-4-5 | D-4 | subcode | 한식조리연수 | 1 | true | false | true | true | unavailable | true | false | false | false |
| D-4-6 | D-4 | subcode | 사설기관연수 | 1 | true | false | true | true | unavailable | true | false | false | false |
| D-4-7 | D-4 | subcode | 외국어연수 | 1 | true | false | true | true | unavailable | true | false | false | false |
| D-4-1 |  | parent | 한국어연수 (대학부설어학원) | 2 | true | false | true | true | unavailable | true | false | false | false |
| D-7 |  | parent | 주재 | 1 | true | false | true | true | unavailable | true | false | false | false |
| D-7-1 | D-7 | subcode | 외국기업 주재 | 1 | true | false | true | true | unavailable | true | false | false | false |
| D-7-2 | D-7 | subcode | 내국기업 주재 | 1 | true | false | true | true | unavailable | true | false | false | false |
| D-7-91 | D-7 | subcode | FTA전근 | 1 | true | false | true | true | unavailable | true | false | false | false |
| D-7-92 | D-7 | subcode | FTA계약 | 1 | true | false | true | true | unavailable | true | false | false | false |
| D-8 |  | parent | 기업투자 | 1 | true | false | true | true | unavailable | true | false | false | false |
| D-8-1 | D-8 | subcode | 법인에 투자 | 1 | true | false | true | true | unavailable | true | false | false | false |
| D-8-2 | D-8 | subcode | 벤처기업 | 1 | true | false | true | true | unavailable | true | false | false | false |
| D-8-3 | D-8 | subcode | 개인기업투자 | 1 | true | false | true | true | unavailable | true | false | false | false |
| D-8-4 | D-8 | subcode | 기술창업 | 1 | true | false | true | true | unavailable | true | false | false | false |
| D-8-91 | D-8 | subcode | FTA전근 | 1 | true | false | true | true | unavailable | true | false | false | false |
| D-8-4S | D-8 | subcode | 스타트업 코리아 특별비자 (기술창업 특례) | 1 | true | false | true | true | unavailable | true | false | false | false |
| D-9 |  | parent | 무역경영 | 1 | true | false | true | true | unavailable | false | false | false | false |
| D-9-1 | D-9 | subcode | 무역고유거래 | 1 | true | false | true | true | unavailable | false | false | false | false |
| D-9-2 | D-9 | subcode | 수출설비 | 1 | true | false | true | true | unavailable | false | false | false | false |
| D-9-3 | D-9 | subcode | 선박설비 | 1 | true | false | true | true | unavailable | false | false | false | false |
| D-9-4 | D-9 | subcode | 경영영리사업 | 1 | true | false | true | true | unavailable | false | false | false | false |
| D-9-5 | D-9 | subcode | 유학생 무역경영자 | 1 | true | false | true | true | unavailable | false | false | false | false |
| D-10 |  | parent | 구직 | 1 | true | false | true | true | unavailable | false | false | false | false |
| D-10-1 | D-10 | subcode | 구직활동 | 1 | true | false | true | true | unavailable | false | false | false | false |
| D-10-2 | D-10 | subcode | 기술창업활동 | 1 | true | false | true | true | unavailable | false | false | false | false |
| D-10-3 | D-10 | subcode | 첨단기술인턴 | 1 | true | false | true | true | unavailable | false | false | false | false |
| D-10-T | D-10 | subcode | 최우수인재 구직 | 1 | true | false | true | true | unavailable | false | false | false | false |
| E-1 |  | parent | 교수 | 1 | true | false | true | true | unavailable | false | false | false | false |
| E-2 |  | parent | 회화지도 | 1 | true | false | true | true | unavailable | true | false | false | false |
| E-2-1 | E-2 | subcode | 일반회화강사 | 1 | true | false | true | true | unavailable | true | false | false | false |
| E-2-2 | E-2 | subcode | 학교보조교사 | 1 | true | false | true | true | unavailable | true | false | false | false |
| E-2-91 | E-2 | subcode | FTA영어 | 1 | true | false | true | true | unavailable | true | false | false | false |
| E-3 |  | parent | 연구 | 1 | true | false | true | true | unavailable | true | false | false | false |
| E-4 |  | parent | 기술지도 | 1 | true | false | true | true | unavailable | true | false | false | false |
| E-5 |  | parent | 전문직업 | 1 | true | false | true | true | unavailable | true | false | false | false |
| E-6 |  | parent | 예술흥행 | 1 | true | false | true | true | unavailable | true | false | false | false |
| E-6-1 | E-6 | subcode | 예술연예 | 1 | true | false | true | true | unavailable | true | false | false | false |
| E-6-2 | E-6 | subcode | 호텔유흥 | 1 | true | false | true | true | unavailable | true | false | false | false |
| E-6-3 | E-6 | subcode | 운동 | 1 | true | false | true | true | unavailable | true | false | false | false |
| E-7 |  | parent | 특정활동 | 1 | true | false | true | true | unavailable | true | false | false | false |
| E-7-1 | E-7 | subcode | 전문인력(67개 직종) | 1 | true | false | true | true | unavailable | true | false | false | false |
| E-7-2 | E-7 | subcode | 준전문인력(10개 직종) | 1 | true | false | true | true | unavailable | true | false | false | false |
| E-7-3 | E-7 | subcode | 일반기능인력(14개 직종) | 1 | true | false | true | true | unavailable | true | false | false | false |
| E-7-4 | E-7 | subcode | 숙련기능인력(K-point E74, 점수제) | 1 | true | false | true | true | unavailable | true | false | false | false |
| E-7-S | E-7 | subcode | 네거티브 방식 전문인력 | 1 | true | false | true | true | unavailable | true | false | false | false |
| E-7-Y | E-7 | subcode | 국내성장인력 | 1 | true | false | true | true | unavailable | true | false | false | false |
| E-7-T | E-7 | subcode | 최우수인재 특정활동 | 1 | true | false | true | true | unavailable | true | false | false | false |
| E-7-91 | E-7 | subcode | FTA독립전문가 | 1 | true | false | true | true | unavailable | true | false | false | false |
| E-7-S1 | E-7 | subcode | 네거티브 방식 전문인력 — 고소득자 | 1 | true | false | true | true | unavailable | true | false | false | false |
| E-7-S2 | E-7 | subcode | 네거티브 방식 전문인력 — 첨단산업분야 종사(예정)자 | 1 | true | false | true | true | unavailable | true | false | false | false |
| E-7-4R | E-7 | subcode | 지역특화형 숙련기능인력 (지역숙련인력) | 2 | true | false | true | true | unavailable | true | false | false | false |
| E-8 |  | parent | 계절근로 | 1 | true | false | true | true | unavailable | false | false | false | false |
| E-8-1 | E-8 | subcode | 계절근로 — 국내지자체·외국지자체 간 MOU 방식, 농업 | 1 | true | false | true | true | unavailable | false | false | false | false |
| E-8-2 | E-8 | subcode | 계절근로 — 결혼이민자가 해외 거주 4촌 이내 친척 추천, 농업 | 1 | true | false | true | true | unavailable | false | false | false | false |
| E-8-3 | E-8 | subcode | 계절근로 — 국내지자체·외국지자체 간 MOU 방식, 어업 | 1 | true | false | true | true | unavailable | false | false | false | false |
| E-8-4 | E-8 | subcode | 계절근로 — 결혼이민자가 해외 거주 4촌 이내 친척 추천, 어업 | 1 | true | false | true | true | unavailable | false | false | false | false |
| E-8-5 | E-8 | subcode | 계절근로 — 기타(G-1) 자격 활동 후 재입국 추천, 농업 | 1 | true | false | true | true | unavailable | false | false | false | false |
| E-8-6 | E-8 | subcode | 계절근로 — 기타(G-1) 자격 활동 후 재입국 추천, 어업 | 1 | true | false | true | true | unavailable | false | false | false | false |
| E-8-7 | E-8 | subcode | 계절근로 — 유학생(D-2)의 부모, 농업 | 1 | true | false | true | true | unavailable | false | false | false | false |
| E-8-8 | E-8 | subcode | 계절근로 — 유학생(D-2)의 부모, 어업 | 1 | true | false | true | true | unavailable | false | false | false | false |
| E-8-99 | E-8 | subcode | 계절근로 — 언어소통 도우미 등 기타 보조 인력 | 1 | true | false | true | true | unavailable | false | false | false | false |
| E-9 |  | parent | 비전문취업 | 1 | true | false | true | true | unavailable | false | false | false | false |
| E-9-1 | E-9 | subcode | 제조업 | 1 | true | false | true | true | unavailable | false | false | false | false |
| E-9-2 | E-9 | subcode | 건설업 | 1 | true | false | true | true | unavailable | false | false | false | false |
| E-9-3 | E-9 | subcode | 농업 | 1 | true | false | true | true | unavailable | false | false | false | false |
| E-9-4 | E-9 | subcode | 어업 | 1 | true | false | true | true | unavailable | false | false | false | false |
| E-9-5 | E-9 | subcode | 서비스업 | 1 | true | false | true | true | unavailable | false | false | false | false |
| E-9-9 | E-9 | subcode | 임업 | 1 | true | false | true | true | unavailable | false | false | false | false |
| E-9-10 | E-9 | subcode | 광업 | 1 | true | false | true | true | unavailable | false | false | false | false |
| E-9-R | E-9 | subcode | 외국인등록 제출서류 | 1 | true | false | true | true | unavailable | false | false | false | false |
| E-9-JS | E-9 | subcode | 구직신청자 특례 | 1 | true | false | true | true | unavailable | false | false | false | false |
| E-10 |  | parent | 선원취업 | 1 | true | false | true | true | unavailable | true | false | false | false |
| E-10-1 | E-10 | subcode | 내항선원 | 1 | true | false | true | true | unavailable | true | false | false | false |
| E-10-2 | E-10 | subcode | 어선원 | 1 | true | false | true | true | unavailable | true | false | false | false |
| E-10-3 | E-10 | subcode | 순항선원 | 1 | true | false | true | true | unavailable | true | false | false | false |
| F-1 |  | parent | 방문동거 | 1 | true | false | true | true | unavailable | false | false | false | false |
| F-1-3 | F-1 | subcode | 외교동거 | 1 | true | false | true | true | unavailable | false | false | false | false |
| F-1-5 | F-1 | subcode | 결혼이민자 부모·가족 | 1 | true | false | true | true | unavailable | false | false | false | false |
| F-1-9 | F-1 | subcode | 동포배우자 등 | 1 | true | false | true | true | unavailable | false | false | false | false |
| F-1-13 | F-1 | subcode | 유학생부모 | 1 | true | false | true | true | unavailable | false | false | false | false |
| F-1-21 | F-1 | subcode | 외교가사보조 | 1 | true | false | true | true | unavailable | false | false | false | false |
| F-1-22 | F-1 | subcode | 고액가사보조 | 1 | true | false | true | true | unavailable | false | false | false | false |
| F-1-23 | F-1 | subcode | 첨단가사보조 | 1 | true | false | true | true | unavailable | false | false | false | false |
| F-1-24 | F-1 | subcode | 전문가사보조 | 1 | true | false | true | true | unavailable | false | false | false | false |
| F-1-D | F-1 | subcode | 디지털노마드(워케이션) 비자 | 1 | true | false | true | true | unavailable | false | false | false | false |
| F-1-16 | F-1 | subcode | 난민인정자의 배우자 및 미성년 자녀 (방문동거) | 1 | true | false | true | true | unavailable | false | false | false | false |
| F-1-52 | F-1 | subcode | 결혼이민자의 전혼관계 출생 미성년 자녀 (방문동거) | 1 | true | false | true | true | unavailable | false | false | false | false |
| F-2 |  | parent | 거주 | 1 | true | false | true | true | unavailable | false | false | false | false |
| F-2-2 | F-2 | subcode | 국민자녀 | 1 | true | false | true | true | unavailable | false | false | false | false |
| F-2-3 | F-2 | subcode | 영주자가족 | 1 | true | false | true | true | unavailable | false | false | false | false |
| F-2-7 | F-2 | subcode | 점수제 거주 | 1 | true | false | true | true | unavailable | false | false | false | false |
| F-2-99 | F-2 | subcode | 기타 거주 | 1 | true | false | true | true | unavailable | false | false | false | false |
| F-2-T | F-2 | subcode | 최우수인재 거주 | 1 | true | false | true | true | unavailable | false | false | false | false |
| F-2-7S | F-2 | subcode | K-STAR 거주 (과학기술 우수인재) | 2 | true | false | true | true | unavailable | false | false | false | false |
| F-2-71 | F-2 | subcode | K-STAR 거주자의 동반가족 | 2 | true | false | true | true | unavailable | false | false | false | false |
| F-2-R | F-2 | subcode | 지역특화형 우수인재 (지역우수인재) | 2 | true | false | true | true | unavailable | false | false | false | false |
| F-2-8 | F-2 | subcode | 관광·휴양시설 투자 거주 | 1 | true | false | true | true | unavailable | false | false | false | false |
| F-2-81 | F-2 | subcode | 관광·휴양시설 투자자의 배우자·자녀 거주 | 1 | true | false | true | true | unavailable | false | false | false | false |
| F-3 |  | parent | 동반 | 1 | true | false | true | true | unavailable | false | false | false | false |
| F-3-1 | F-3 | subcode | 동반 기본 | 1 | true | false | true | true | unavailable | false | false | false | false |
| F-3-2 | F-3 | subcode | 소득요건(25.7.1 개편) | 1 | true | false | true | true | unavailable | false | false | false | false |
| F-3-3 | F-3 | subcode | 소득요건 면제 | 1 | true | false | true | true | unavailable | false | false | false | false |
| F-4 |  | parent | 재외동포 | 1 | true | false | true | true | unavailable | false | false | false | false |
| F-4-11 | F-4 | subcode | 재외동포 본인 | 1 | true | false | true | true | unavailable | false | false | false | false |
| F-4-12 | F-4 | subcode | 직계비속 | 1 | true | false | true | true | unavailable | false | false | false | false |
| F-4-13 | F-4 | subcode | D·E계열 6개월↑ | 1 | true | false | true | true | unavailable | false | false | false | false |
| F-4-14 | F-4 | subcode | 대학 졸업자 | 1 | true | false | true | true | unavailable | false | false | false | false |
| F-4-15 | F-4 | subcode | OECD영주자 | 1 | true | false | true | true | unavailable | false | false | false | false |
| F-4-16 | F-4 | subcode | 법인대표 등 | 1 | true | false | true | true | unavailable | false | false | false | false |
| F-4-17 | F-4 | subcode | 10만불 기업가 | 1 | true | false | true | true | unavailable | false | false | false | false |
| F-4-18 | F-4 | subcode | 다국적기업 종사자 | 1 | true | false | true | true | unavailable | false | false | false | false |
| F-4-19 | F-4 | subcode | 동포단체대표 | 1 | true | false | true | true | unavailable | false | false | false | false |
| F-4-20 | F-4 | subcode | 공무원 등 | 1 | true | false | true | true | unavailable | false | false | false | false |
| F-4-21 | F-4 | subcode | 교원 | 1 | true | false | true | true | unavailable | false | false | false | false |
| F-4-25 | F-4 | subcode | 60세 이상자 | 1 | true | false | true | true | unavailable | false | false | false | false |
| F-4-30 | F-4 | subcode | 국내 초·중·고 재학 동포 자녀 | 1 | true | false | true | true | unavailable | false | false | false | false |
| F-5 |  | parent | 영주 | 1 | true | false | true | true | unavailable | false | false | false | false |
| F-5-3 | F-5 | subcode | 결혼이민 영주 | 1 | true | false | true | true | unavailable | false | false | false | false |
| F-5-5 | F-5 | subcode | 고액투자 영주 | 1 | true | false | true | true | unavailable | false | false | false | false |
| F-5-11 | F-5 | subcode | 특정능력 영주 | 1 | true | false | true | true | unavailable | false | false | false | false |
| F-5-16 | F-5 | subcode | 점수제 영주 | 1 | true | false | true | true | unavailable | false | false | false | false |
| F-5-T | F-5 | subcode | 최우수인재 영주 | 1 | true | false | true | true | unavailable | false | false | false | false |
| F-5-S1 | F-5 | subcode | K-STAR 영주 (과학기술 우수인재) | 2 | true | false | true | true | unavailable | false | false | false | false |
| F-5-S2 | F-5 | subcode | K-STAR 영주자의 동반가족 | 2 | true | false | true | true | unavailable | false | false | false | false |
| F-5-6R | F-5 | subcode | 지역특화형 재외동포영주 (지역동포영주) | 2 | true | false | true | true | unavailable | false | false | false | false |
| F-6 |  | parent | 결혼이민 | 1 | true | true | true | true | contextual | false | false | false | false |
| F-6-1 | F-6 | subcode | 국민배우자 | 1 | true | true | true | true | contextual | false | false | false | false |
| F-6-2 | F-6 | subcode | 자녀양육자 | 1 | true | true | true | true | contextual | false | false | false | false |
| F-6-3 | F-6 | subcode | 혼인단절자(배우자 사망) | 1 | true | true | true | true | contextual | false | false | false | false |
| G-1 |  | parent | 기타(난민등) | 1 | true | false | true | true | unavailable | false | false | false | false |
| G-1-1 | G-1 | subcode | 산업재해 청구 및 치료 중인 사람과 그 가족 | 1 | true | false | true | true | unavailable | false | false | false | false |
| G-1-5 | G-1 | subcode | 난민신청자 | 1 | true | false | true | true | unavailable | false | false | false | false |
| G-1-6 | G-1 | subcode | 난민불인정자 중 인도적 체류허가자 | 1 | true | false | true | true | unavailable | false | false | false | false |
| G-1-10 | G-1 | subcode | 외국인환자 (입국 후 장기치료가 필요한 환자와 그 가족) | 1 | true | false | true | true | unavailable | false | false | false | false |
| G-1-11 | G-1 | subcode | 성폭력피해자 등 인도적 고려가 필요한 사람 | 1 | true | false | true | true | unavailable | false | false | false | false |
| G-1-12 | G-1 | subcode | 인도적 체류허가자의 가족 | 1 | true | false | true | true | unavailable | false | false | false | false |
| G-1-2 | G-1 | subcode | 질병·사고로 치료 중인 사람과 그 가족 | 1 | true | false | true | true | unavailable | false | false | false | false |
| G-1-3 | G-1 | subcode | 각종 소송 진행 중인 사람 | 1 | true | false | true | true | unavailable | false | false | false | false |
| G-1-4 | G-1 | subcode | 임금체불로 노동관서에서 중재 중인 사람 | 1 | true | false | true | true | unavailable | false | false | false | false |
| G-1-7 | G-1 | subcode | 사고 등으로 사망한 사람의 가족 | 1 | true | false | true | true | unavailable | false | false | false | false |
| G-1-8 | G-1 | subcode | 장기체류 아동 | 1 | true | false | true | true | unavailable | false | false | false | false |
| G-1-9 | G-1 | subcode | 임신·출산 등 인도적 배려가 불가피한 사람 | 1 | true | false | true | true | unavailable | false | false | false | false |
| G-1-13 | G-1 | subcode | 장기체류 아동 (장기체류 아동 체계) | 1 | true | false | true | true | unavailable | false | false | false | false |
| G-1-14 | G-1 | subcode | 장기체류 아동 (장기체류 아동 체계) | 1 | true | false | true | true | unavailable | false | false | false | false |
| G-1-99 | G-1 | subcode | 기타 사유에 해당되는 사람 | 1 | true | false | true | true | unavailable | false | false | false | false |
| G-1-19 | G-1 | subcode | 기타(G-1) 계절근로 참여자 (재입국 추천 연계 표기) | 1 | false | false | true | true | unavailable | false | false | false | false |
| H-1 |  | parent | 관광취업 | 1 | true | false | true | true | unavailable | false | false | false | false |
| H-2 |  | parent | 방문취업 (신규발급 중단) | 1 | true | false | true | true | unavailable | false | false | false | false |
| H-2-7 | H-2 | subcode | 만기출국 후 재입국한 사람 | 1 | true | false | true | true | unavailable | false | false | false | false |
| A-1 |  | parent | 외교 | 1 | true | false | true | true | unavailable | false | false | false | false |
| A-2 |  | parent | 공무 | 1 | true | false | true | true | unavailable | false | false | false | false |
| A-3 |  | parent | 협정 | 1 | true | false | true | true | unavailable | false | false | false | false |
| A-3-99 | A-3 | subcode | Fulbright 협정대상자 | 1 | true | false | true | true | unavailable | false | false | false | false |
| C-1 |  | parent | 일시취재 | 1 | true | false | true | true | unavailable | false | false | false | false |
| D-5 |  | parent | 취재 | 1 | true | false | true | true | unavailable | true | false | false | false |
| D-6 |  | parent | 종교 | 1 | true | false | true | true | unavailable | true | false | false | false |
| D-4-2K |  | parent | 기업맞춤형인턴십(K-Trainee) | 2 | true | false | true | true | unavailable | true | false | false | false |
| K-STAR |  | parent | K-STAR 비자트랙 | 1 | true | true | true | true | contextual | false | false | false | false |
| F-2-7S | K-STAR | subcode | K-STAR 거주 (2단계) | 2 | true | true | true | true | unavailable | false | false | false | false |
| F-5-S1 | K-STAR | subcode | K-STAR 영주 (3단계) | 2 | true | true | true | true | unavailable | false | false | false | false |
| F-2-71 | K-STAR | subcode | K-STAR 거주자의 동반가족 | 2 | true | true | true | true | unavailable | false | false | false | false |
| F-5-S2 | K-STAR | subcode | K-STAR 영주자의 동반가족 | 2 | true | true | true | true | unavailable | false | false | false | false |
| REGION-S |  | parent | 지역특화·광역형 비자 시범사업 | 1 | true | false | true | true | unavailable | false | false | false | false |
| F-2-R | REGION-S | subcode | 지역특화형 우수인재 (지역우수인재) | 2 | true | false | true | true | unavailable | false | false | false | false |
| E-7-4R | REGION-S | subcode | 지역특화형 숙련기능인력 (지역숙련인력) | 2 | true | false | true | true | unavailable | true | false | false | false |
| F-3-3R | REGION-S | subcode | 지역숙련인력가족 (지역특화 숙련기능인력 동반가족) | 1 | true | false | true | true | unavailable | false | false | false | false |
| F-4-R | REGION-S | subcode | 지역특화형 재외동포 (지역재외동포) | 1 | true | false | true | true | unavailable | false | false | false | false |
| REGIONAL-D-2 | REGION-S | subcode | 광역형 비자 유학생 (시범사업) | 1 | true | false | true | true | unavailable | false | false | false | false |
| REGIONAL-E-7 | REGION-S | subcode | 광역형 비자 특정활동 (시범사업) | 1 | true | false | true | true | unavailable | false | false | false | false |
| F-3-1R | REGION-S | subcode | 지역인재가족 (지역특화 우수인재 동반가족) | 1 | true | false | true | true | unavailable | false | false | false | false |
| F-3-2R | REGION-S | subcode | 지역동포가족 (지역특화 재외동포 동반가족) | 1 | true | false | true | true | unavailable | false | false | false | false |
| F-5-6R | REGION-S | subcode | 지역특화형 재외동포영주 (지역동포영주) | 2 | true | false | true | true | unavailable | false | false | false | false |
| YOUTH-STAY |  | parent | 국내 성장 기반 외국인 청소년 취업·정주 체류제도 | 1 | true | false | true | true | unavailable | false | false | false | false |

## Where Weak Labels Appear
| File | Term counts |
|---|---|
| `backend/data/visas.json` | manual: 2258, 확인 필요: 48, 매뉴얼 확인 필요: 32 |
| `visa_data.json` | manual: 2258, 확인 필요: 48, 매뉴얼 확인 필요: 32 |
| `backend/data/manual_grounding/structured_requirements_2026_06_01.json` | manual: 2270, 확인 필요: 7 |
| `backend/data/manual_grounding/structured_requirements_2026_05.json` | manual: 1799, 확인 필요: 7 |
| `docs/data/structured_requirements_2026_05.json` | manual: 1799, 확인 필요: 7 |
| `index.html` | 공식근거 제한: 1, 공식근거 직접 확인: 1, 관련 공식근거 있음: 1, limited: 13, unavailable: 21, manual: 783, 확인 필요: 25, 매뉴얼 확인 필요: 10, 정보 없음: 4 |
| `docs/data/manual_section_index_2026_05.json` | manual: 445 |
| `docs/data/json_manual_law_audit_2026_05_matrix.json` | manual: 316 |
| `docs/data/foreign_registration_full_coverage_2026_05.json` | manual: 237, 확인 필요: 1 |
| `backend/paradiso_backend.py` | limited: 33, unavailable: 45, manual: 110, 확인 필요: 3 |
| `docs/data/ALL_STATUS_DATA_GAP_INVENTORY_2026_05.json` | manual: 155, 확인 필요: 1, 매뉴얼 확인 필요: 1 |
| `audits/ai-grounding/grounding_code_search.txt` | limited: 8, unavailable: 24, manual: 107 |
| `docs/data/ALL_STATUS_SOURCE_CONFIRMED_PATCH_CANDIDATES_2026_05.json` | manual: 138 |
| `docs/data/2026_05_21_manual_json_crosswalk.json` | manual: 112 |
| `scripts/apply_full_manual_coverage_corrections_2026_06_08.py` | manual: 102, 확인 필요: 6, 매뉴얼 확인 필요: 1 |
| `docs/data/FOREIGN_REGISTRATION_FULL_COVERAGE_AUDIT_2026_05.md` | manual: 79, 확인 필요: 1, 매뉴얼 확인 필요: 1 |
| `backend/tests/test_scenario_procedure_variants.py` | unavailable: 1, manual: 76, 확인 필요: 1, 매뉴얼 확인 필요: 1, 정보 없음: 1 |
| `backend/services/procedure_packet_builder.py` | 공식근거 제한: 1, 공식근거 확인 불가: 1, 공식근거 직접 확인: 1, 관련 공식근거 있음: 1, sourceLens: 7, limited: 10, unavailable: 6, sourceBacked: 11, limitationKo: 13, manual: 19, 확인 필요: 3, 매뉴얼 확인 필요: 2, 정보 없음: 2, TBD: 1, N/A: 1 |
| `docs/data/2026_06_08_full_manual_coverage_audit.json` | manual: 76 |
| `ai.html` | limited: 18, unavailable: 17, manual: 34, 확인 필요: 2 |
| `docs/data/manual_patch_candidates_2026_05.json` | manual: 53, 확인 필요: 8, 매뉴얼 확인 필요: 8 |
| `docs/source-manuals/source_manifest.json` | unavailable: 1, manual: 67 |
| `scripts/regenerate_2026_05_21_manual_crosswalk.py` | manual: 67 |
| `docs/audits/MANUAL_LAW_DATA_CORRECTION_READINESS_2026_05.md` | unavailable: 1, manual: 64 |
| `docs/data/2026_05_21_visa_data_domain_classification.json` | manual: 64 |
| `backend/services/law_tools.py` | unavailable: 5, manual: 56 |
| `scripts/audit_foreign_registration_full_coverage.py` | manual: 57, 확인 필요: 2, 매뉴얼 확인 필요: 1 |
| `backend/tests/test_paradiso_backend.py` | limited: 9, unavailable: 5, manual: 44, 확인 필요: 1 |
| `backend/tests/test_procedure_packet_builder.py` | 공식근거 직접 확인: 1, sourceLens: 20, limited: 14, unavailable: 7, sourceBacked: 3, limitationKo: 3, manual: 4, 확인 필요: 1, 매뉴얼 확인 필요: 1, 정보 없음: 3 |
| `docs/data/STAY_MANUAL_SOURCE_REFRESH_2026_06.md` | unavailable: 1, manual: 56 |
| `backend/services/source_grounding.py` | limited: 7, unavailable: 18, manual: 26, 확인 필요: 1 |
| `docs/data/2026_05_21_visa_data_full_audit.json` | manual: 52 |
| `docs/data/PROCEDURE_PACKET_AND_APPLICATION_HELPER_2026_06.md` | 공식근거 제한: 1, 공식근거 확인 불가: 1, 공식근거 직접 확인: 1, 관련 공식근거 있음: 1, sourceLens: 1, limited: 22, unavailable: 2, sourceBacked: 4, limitationKo: 7, manual: 9, 확인 필요: 1, 매뉴얼 확인 필요: 1, 정보 없음: 1 |
| `scripts/smoke_ai_live_quality.py` | limited: 12, unavailable: 19, manual: 20 |
| `backend/tests/test_generalized_source_grounding_regression.py` | limited: 1, unavailable: 5, manual: 43, 확인 필요: 1 |
| `docs/INDEX_MANUAL_CONSISTENCY_AUDIT.md` | unavailable: 3, manual: 44, 확인 필요: 1, 매뉴얼 확인 필요: 1 |
| `backend/data/manual_grounding/structured_requirements_index_2026_05.json` | manual: 44 |
| `docs/data/I18N_LAW_FALLBACK_LIVE_SMOKE_2026_05.md` | unavailable: 2, manual: 42 |
| `docs/data/STRUCTURED_REQUIREMENTS_PROMOTION_CANDIDATES_2026_05.json` | manual: 44 |
| `scripts/generate_manual_coverage_audit_2026_06_08.py` | manual: 44 |
| `backend/data/manual_grounding/structured_requirements_index_2026_06_01.json` | manual: 43 |
| `docs/data/2026_05_HIGH_RISK_GAP_PATCH_AUDIT.md` | unavailable: 1, manual: 42 |
| `docs/CODEX_SAFE_AUTOMATION_IMPLEMENTATION_BRIEF.md` | manual: 42 |
| `backend/tests/test_i18n_law_fallback_live_smoke.py` | manual: 41 |
| `docs/data/2026_05_21_REPO_JSON_INVENTORY.md` | manual: 41 |
| `docs/data/2026_05_21_FULL_MANUAL_JSON_AUDIT_REPORT.md` | limited: 1, manual: 39 |
| `backend/services/precedent_sources.py` | unavailable: 39 |
| `docs/data/2026_05_21_pdf_source_install_report.json` | manual: 39 |
| `docs/data/DATA_COVERAGE_AUDIT_2026_05_MANUALS.md` | limited: 6, manual: 31 |
| `docs/data/JSON_MANUAL_LAW_AUDIT_2026_05.md` | limited: 1, unavailable: 5, manual: 31 |
| `backend/services/evidence_ontology.py` | unavailable: 11, manual: 25 |
| `docs/FULL_REWRITE_PHASE_1_2_ANALYSIS.md` | manual: 36 |
| `backend/services/answer_shape.py` | limited: 12, unavailable: 6, manual: 15, 확인 필요: 2 |
| `backend/services/legal_analysis.py` | limited: 7, unavailable: 7, manual: 20 |
| `docs/crosswalk/g1_f_h_high_risk_procedure_citations_2026_05.json` | limited: 8, manual: 26 |
| `docs/manual_grounding_expansion_plan.md` | manual: 34 |
| `docs/paradiso_ai_safe_automation_architecture.md` | limited: 2, unavailable: 1, manual: 31 |
| `audits/manual-doc-normalization/naming_candidates.json` | manual: 33 |
| `backend/data/eval/paradiso_coverage_matrix.json` | limited: 1, manual: 32 |
| `docs/crosswalk/procedure_crosswalk_2026_05.json` | manual: 28, N/A: 4 |
| `docs/audits/BATCH_2_FINAL_INTERACTIVE_RERUN_NORMALIZED_2026_05.md` | manual: 31 |
| `docs/crosswalk/procedure_page_article_citations_2026_05.json` | manual: 31 |
| `docs/data/2026_05_21_SOURCE_FILE_INTAKE_REPORT.md` | manual: 29 |
| `docs/MOONSHOT_TO_PARADISO_MIGRATION_GAP_AUDIT.md` | manual: 26, N/A: 2 |
| `docs/data/2026_05_21_MANUAL_EXTRACTION_REPORT.md` | manual: 28 |
| `docs/data/2026_05_21_manual_extraction_report.json` | manual: 28 |
| `docs/data/2026_05_21_repo_json_inventory.json` | manual: 28 |
| `docs/data/CLAUDE_OPUS_MANUAL_EXTRACTION_INGESTION_REPORT_2026_05.md` | limited: 4, manual: 24 |
| `scripts/regenerate_2026_06_01_structured_stay_manual_indexes.py` | manual: 28 |
| `docs/audits/AGENT_MODE_STAY_STATUS_UI_SOURCE_AUDIT_NORMALIZED_2026_05.md` | manual: 27 |
| `docs/data/2026_05_21_anchor_ref_stability_patch_report.json` | manual: 25, 확인 필요: 1, 매뉴얼 확인 필요: 1 |
| `docs/data/ALL_STATUS_MANUAL_SOURCED_CORRECTIONS_2026_05.md` | manual: 22, 확인 필요: 2, 매뉴얼 확인 필요: 2, N/A: 1 |
| `docs/data/FOREIGN_REGISTRATION_PROCEDURE_AUDIT_2026_05.md` | unavailable: 3, manual: 22, 확인 필요: 1, 매뉴얼 확인 필요: 1 |
| `docs/data/REMAINING_COMPLEX_SUBTYPE_SCENARIO_COVERAGE_2026_05.md` | limited: 1, manual: 26 |
| `backend/services/answer_quality.py` | limited: 8, unavailable: 7, manual: 11 |
| `backend/tests/test_legal_analysis_deterministic_fallback.py` | limited: 5, unavailable: 14, manual: 7 |
| `docs/data/2026_05_21_SOURCE_IDENTITY_REPORT.md` | manual: 25 |
| `docs/data/GENERALIZED_LEGAL_GROUNDING_SOURCE_STATUS_2026_06.md` | limited: 3, unavailable: 7, manual: 14, 확인 필요: 1 |
| `docs/source-laws/LAW_SOURCESET_INVENTORY_2026_05.md` | manual: 25 |
| `docs/crosswalk/PROCEDURE_PAGE_ARTICLE_CITATIONS_2026_05.md` | manual: 24 |

## Files Needing Editing In This Focused PR
- `audits/visa-issuance-enrichment/*` for audit reports and matrices.
- `data/visa_issuance_records.json` for first-class issuance-mode POC records.
- `data/procedure_evidence_bindings.json` for source evidence and limitation explanations.
- `data/official_web_overlays.json` and an overlay seed manifest for conservative official web overlay design.
- `index.html` for loading optional issuance/evidence data, rendering issuance scenario cards, improving source-limitation explanations, and tightening exact-code ranking.
- `scripts/validate_visa_issuance_enrichment.js` for JSON/schema/source-lens validation.
- `scripts/check_exact_code_search.js` / `scripts/check_exact_code_search_coverage.py` for priority exact-code regression checks.

## Recommended PR Slicing
- PR 1 (this patch): audits, schema, priority-code POC records, frontend shell, validation, exact-code regression.
- PR 2: manual extraction review for all remaining statuses, replacing placeholder manual refs only when verified.
- PR 3: official web overlay fetch/parser, with allowlisted domains and manually reviewed overlays only.
- PR 4: backend packet-builder integration so API packets consume the new evidence layer, after static UI proves the shape.
- PR 5: i18n polish and country/post overlay UX after data quality stabilizes.
