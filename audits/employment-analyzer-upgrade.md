# Audit — 취업정보 신고용 직종·업종 analyzer upgrade

**Date:** 2026-06-18
**Scope:** Upgrade the natural-language analyzer behind **취업정보 신고용 직종·업종 찾기**
to handle vague, colloquial, multilingual, and field-worker-style inputs, grounded
in the MoJ 「외국인 취업정보 온라인 신고」 press release and the National Data Office
standard classifications. Rendering/data-hygiene work only — **not** a legal
revalidation, and **not** a visa-eligibility judgment.

---

## 1. Current implementation summary (before)

A mature deterministic analyzer already existed
(`scripts/employment_code_analyzer.mjs`) with: input normalization, a KO/EN
concept lexicon (`synonyms.*`, `aliases.entertainment.*`, `aliases.tattoo.*`),
umbrella decomposition (`ambiguous_inputs.json`), two-track retrieval against the
canonical `data/jobcode_master.json` (728 직종 / 2,038 업종 rows), confidence
scoring, entertainment/tattoo legal cautions, and a browser bridge consumed by the
`#jobCodeModalOverlay` UI in `index.html`. Regression: `check_employment_code_analyzer.mjs`
(51 fixtures, green).

**Gaps found** (verified by running the analyzer): field-worker inputs failed —
`한치잡이 배에서 한치잡아요`, `귤 따요`, `양식장에서 물고기 밥 줘요` returned **no
candidates**; `공장에서 박스 포장해요` matched packaging-*manufacturer* industries
and manager occupations (wrong). No structured place/object/action extraction, no
analyzer "modes", no income-bracket note in the result model, and a Latin
substring bug (`actor` matched inside `factory`). Coverage holes for many
professional/beauty terms (accountant, lawyer, doctor, architect, mechanic, nail
artist…).

## 2. Official source findings

| Source | Type | Use |
|---|---|---|
| MoJ 「외국인 취업정보 온라인 신고」 press release / overview (`data/sources/hikorea_employment_reporting_overview.hwpx`) | official | reporting items, scope, timing, HiKorea flows |
| HiKorea procedure (visit/e-civil) `…procedure_visit.hwpx`, FAQ `…faq.docx` | official | 직종/업종 separate search, classification basis, UX behavior |
| 제8차 한국표준직업분류 **KSCO8** (`ksco8_isco08_linkage_2026.xlsx`) | official | **primary occupation classification** |
| 제11차 한국표준산업분류 **KSIC11** (`ksic11_full_2038.csv`) | official | **primary industry classification** |
| 국가데이터처 통계분류포털 (kssc.mods.go.kr) | official | official confirmation destination |
| 출입국관리법 시행규칙 §47·§49의2 | official | legal basis for the reporting obligation |
| 문신사법 (2025-09-25 통과, 2027-10-29 시행 예정) | official | tattoo legal caution |
| 이민자 취업 통계 | statistics | **test prioritization only**, never classification truth |

Recorded in `data/employment/source_registry.json` with reliability + limitations.

## 3. Summary of the MoJ press release (facts reflected)

- **Reporting items:** 직종 · 업종 · 소득.
- **Targets** (profit-making activity): E-1, E-2, E-3, E-4, E-5, E-6, E-7, E-8,
  E-9, E-10, F-2, F-4, F-6, H-2, D-7, D-8, D-9.
- **Excluded:** **F-5(영주)**; and anyone not engaged in profit-making activity.
- **Timing:** at 외국인등록/체류지 신고 if already working; within **15 days** of a
  change to reported 직종/업종/연간소득 구간; within **15 days** of starting
  profit-making activity if not working at registration time.
- **Channels:** HiKorea **visit-reservation** flow, or **e-civil-petition** for
  initial/change reporting without a visit.
- **Classification basis:** 직종명 검색 = 국가데이터처 **표준직업분류**; 업종명 검색 =
  국가데이터처 **표준산업분류**; both checkable on the 통계분류포털.

Captured in `data/employment/visa_reporting_scope.json` + `income_brackets.json`,
cross-checked against `jobcode_master.json#employment_reporting_context` by the
source audit.

## 4. Classification source decision

- **Occupation → National Data Office 표준직업분류 (KSCO8)** is primary.
- **Industry → National Data Office 표준산업분류 (KSIC11)** is primary.
- HiKorea UI behavior (separate 직종/업종 search returning multiple labeled rows)
  is the primary **product** reference → the UI returns multiple candidate cards
  per track, never one forced answer.
- Statistics are auxiliary (test prioritization) only.

## 5. HiKorea 직종 search uses KSCO8 — confirmed

Press release / FAQ state 직종명 검색 displays the 국가데이터처 표준직업분류 list.
Mirrored in `source_registry.json#national_data_office_ksco8` and the UI tag
"KSCO8 · 제8차 한국표준직업분류".

## 6. HiKorea 업종 search uses KSIC11 — confirmed

Press release / FAQ state 업종명 검색 displays the 국가데이터처 표준산업분류 list.
Mirrored in `source_registry.json#national_data_office_ksic11` and the UI tag
"KSIC11 · 제11차 한국표준산업분류".

## 7. Reporting scope by visa/status

17 included statuses + **F-5 excluded** (§3 above), condition = profit-making
activity. `visa_reporting_scope.json` carries the codes, labels, and the explicit
caution that scope ≠ work-permission eligibility. The analyzer surfaces a
status-specific note when a 체류자격 is supplied, without judging eligibility.

## 8. Reporting timing & the 15-day change rule

Encoded in `visa_reporting_scope.json` (`change_deadline_days: 15`, three timing
branches, pre-tax bracket basis, main-job rule for multiple jobs). The result
model now always includes `incomeReportingNote` reminding that 연간소득 구간 is
reported alongside 직종·업종.

## 9. Data model changes

New, code-free files under `data/employment/`:

- `colloquial_field_terms_ko.json` / `_en.json` — place/object/action/tool signals
  with verified retrieval terms + sector + disambiguation refs.
- `disambiguation_rules.json` — 9 fork rules (vessel↔land, aquaculture↔processing,
  farm↔food-factory, golf direct↔contractor, factory↔warehouse, factory product
  unknown, restaurant↔outsourced, construction labor↔install, hospitality role).
- `source_registry.json`, `visa_reporting_scope.json`, `income_brackets.json`,
  `README.md`.
- `synonyms.{ko,en}.json` extended with ~16 professional + beauty concepts
  (회계사/변호사/의사/수의사/약사/건축가/엔지니어/정비/데이터 분석가/컨설턴트/해외영업/
  사진가/실험실 보조/네일/메이크업 …), all with verified retrieval terms.

Each record supports the spec fields via the existing schema + new `signal`,
`sector`, `disambiguation`, source/reliability metadata. **No official codes were
added to any of these files** (enforced by `audit_employment_sources.mjs`).

## 10. Analyzer architecture

`scripts/employment_code_analyzer.mjs` (additive, backward-compatible):

1. **Normalization** — case-folding, punctuation, Korean particle stripping,
   ko/en/mixed/**zh** language detection.
2. **Signal extraction** — `extractFieldSignals()` → `parsedSignals` { places,
   objects, actions, tools, sectors, employerHints, workSettingHints,
   visaContextHints }. Fixed a Latin **substring** bug so single English words
   require an exact token (`actor` no longer matches `factory`).
3. **Alias/umbrella expansion** — concepts + field signals + ambiguous
   decomposition contribute verified retrieval terms on each track.
4. **Matching** — exact/alias/token/substring scoring against KSCO8/KSIC11, leaf
   and depth preference, confidence relative to the top candidate, confidence
   caps for broad/indirect mappings.
5. **Mode detection** — `detectMode()` → `field_labor_mode` / `professional_mode`
   / `service_mode` / `arts_entertainment_mode` / `ambiguous_mode`. A field
   **action** is decisive; a field place/object yields field mode only when no
   competing professional/service role is present.
6. **Disambiguation** — `evaluateDisambiguation()` fires sector-gated fork rules,
   ranked by how many signals agree, surfaced **one question at a time**.
7. **Output model** — adds `input, detectedLanguage, mode, parsedInterpretation,
   parsedSignals, incomeReportingNote, clarificationRequired, clarificationQuestion,
   cautionNotes, sourceStatus, noOfficialCodeFound` while keeping every legacy
   field. `sourceStatus = needs_confirmation` drives the "공식 코드 확인 필요" state.

## 11. UI changes (`index.html`)

- Analyzer builder now loads the field-term, disambiguation, and income-bracket
  files (same composition as the Node loader).
- Interpretation panel: **field-labor banner** ("입력하신 내용은 ‘장소 + 작업 내용’
  기준으로 분석했어요."), a **mode chip**, a parsed-interpretation line ("골프장 +
  청소 — 미화 기준으로 분석됨"), place/object/action rows, an **income reminder**, and a
  **공식 코드 확인 필요** pending banner when mapping is unverified.
- No-result guard: when signals were detected, empty result panes show "입력은
  이해했어요 — 공식 코드는 확인이 필요해요" instead of a bare 검색 결과 없음.
- Two-track candidate cards (직종 KSCO8 / 업종 KSIC11) and disambiguation chips are
  retained; legal cautions stay pulled to the top.

## 12. Field-labor mode details

Prioritizes **place + object + action** over formal titles. Verified mappings
(examples): 어선/한치/잡다 → `6302 어부 및 해녀` + `031 어로 어업`; 양식장/먹이 →
`6301 양식원` + `0321 양식 어업`; 과수원/귤/따다 → `6113 과수작물 재배원` +
`0113 과실 재배업`; 골프장/청소 → `9411 건물 청소원` + `74211 청소업` / `91121 골프장
운영업`; 창고/택배/나르다 → `9211 하역 및 적재 단순 종사원` + `창고`. Every required
spec example now returns field mode with parsed signals and the right fork
question. (Note: a factory whose product is unknown legitimately yields broad
업종 candidates — handled by the `factory_product_unknown` clarification + the
"공식 코드 확인 필요" caution, not by guessing.)

## 13. Ambiguous job handling

Occupation vs industry are never merged. Umbrella/forking inputs ask **one**
targeted question and keep both candidate clusters: 골프장 청소 → "직접 고용 vs
청소·시설관리 업체"; 한치 어선 → "승선 어로 vs 육상 가공"; 아이돌/걸그룹 → decomposed to
가수/무용/배우 with entertainment caution; **tattoo** → low-confidence beauty/personal-
service indirect match + 문신사법 caution, no legal conclusion.

## 14. Test coverage summary

Generated by `scripts/build_employment_test_cases.mjs`, run by
`scripts/check_employment_analyzer_modes.mjs`:

| Suite | Cases | Min |
|---|---|---|
| field-labor | **193** | 150 |
| professional/office | **104** | 100 |
| service/hospitality/retail/logistics | **82** | 80 |
| arts/entertainment/creator/beauty | **65** | 60 |
| ambiguous/fuzzy/misspelled/multilingual | **60** | 60 |
| **total** | **504** | — |

Hard invariants per case: no hallucinated codes, track separation, source notes,
income note, legality-never-implied, expected mode (field/arts strict; svc↔pro &
ambiguous-fallback tolerated), parsed signals present, legal sensitivity /
confidence ceiling / warning text when asserted, and **never a silent dead-end**.
Aggregate gates: cluster coverage 88.0% (≥80%), mode precision 91.7% (≥70%). The
original 51-fixture regression still passes. `audit:employment-sources` confirms
all 329 retrieval tracks resolve to a real KSCO8/KSIC11 row and no lexicon file
contains a code.

## 15. Remaining risks

1. **Industry breadth for unspecified employers** (e.g., generic factory) — by
   design we show multiple 업종 candidates + a clarification; raw tokens like
   "포장" can still surface packaging-*manufacturer* rows. Mitigated by the
   `factory_product_unknown` question and the 공식 코드 확인 필요 caution; not fully
   eliminated.
2. **KSCO8 세세분류(5단계)** is not fully loaded at runtime — deepest occupation
   codes must be confirmed on HiKorea (warned in the UI).
3. **Income bracket labels are `unverified`** — mirror the overview, but exact live
   HiKorea thresholds must be confirmed.
4. **Vocabulary coverage** is broad but finite; uncovered terms fall back to
   `ambiguous_mode` + clarification (honest, never a wrong confident answer).
5. **Static app** — failure logging is in-memory/localStorage with a documented
   backend seam; no server persistence yet.

## 16. Follow-up tasks

- Wire `createFailureLogger({ persist })` to a backend endpoint and run
  `employment_failure_report.mjs` periodically to mine real misses → new aliases.
- Verify live HiKorea income-bracket labels; flip `income_brackets.source_status`
  to `verified`.
- Load the full KSCO8 세세분류 table when available; drop the "상위 분류만" warning.
- Optional semantic/embedding retrieval layer if/when the project adds one.
- Periodically reconcile HiKorea dropdowns vs the public 표준분류 via the adapter
  note in `classification_sources.json` (record mismatches, don't edit canon).

## 17. Source files & URLs/paths

- `data/sources/hikorea_employment_reporting_overview.hwpx` (press release/overview)
- `data/sources/hikorea_employment_reporting_procedure_visit.hwpx` (procedure)
- `data/sources/hikorea_employment_reporting_faq.docx` (FAQ)
- `data/sources/ksco8_isco08_linkage_2026.xlsx` (KSCO8)
- `data/sources/ksic11_full_2038.csv` (KSIC11)
- `data/jobcode_master.json` (canonical 직종/업종 codes + reporting context)
- `data/employment/source_registry.json` (provenance registry)
- https://kssc.mods.go.kr — 국가데이터처 통계분류포털
- https://www.hikorea.go.kr — HiKorea reporting
- https://www.law.go.kr — 출입국관리법 시행규칙 §47·§49의2, 문신사법
