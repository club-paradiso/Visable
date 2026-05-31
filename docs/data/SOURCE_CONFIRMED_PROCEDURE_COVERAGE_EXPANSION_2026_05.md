# Source-Confirmed Procedure Coverage Expansion — 2026-05

## Purpose

A single broad pass that expands the number of **source-confirmed** structured
procedure records in the 2026-05 manual-evidence layer
(`backend/data/manual_grounding/structured_requirements_2026_05.json`, mirrored
to `docs/data/structured_requirements_2026_05.json`), continuing the path
established by PR #228/#229/#230.

A record is *source-confirmed* and exposed at runtime only when it is
`confidence == "HIGH"` **and** `readinessLabel == "STRUCTURED_EVIDENCE_READY"`
(enforced by `backend/structured_requirements.py`). This pass independently
verified parent-level, single-procedure required-document lists against the
committed official PDF and promoted those that pass the strict promotion rule,
while documenting every other status as a structured blocker.

This is a data change, not a docs-only audit: it raises the runtime-exposed
source-confirmed count from **4 to 18** across **14 statuses**.

## Source files & method

- `docs/source-manuals/2026-05/stay_manual_2026_05.pdf` — the only authority
  used for the promotions below (외국인체류 안내매뉴얼, v2026.5).
- Extraction/verification via **PyMuPDF** (`pip install pymupdf`). The 2026-05
  stay PDF is 1:1 (printed footer `- N -` == 1-based PDF page N); every cited
  page's footer is re-verified at run time.
- Deterministic, idempotent, repeatable helpers committed in this PR:
  - `scripts/extract_manual_page_text.py` — per-page text + footer verification.
  - `scripts/promote_source_confirmed_procedures_2026_05.py` — embeds each
    verified record (page, section title, document mapping) and regenerates the
    structured file, its docs mirror, and the per-status index.

> Note: earlier environments could not extract these PDFs
> (`docs/data/manual_section_index_2026_05.json` records "PDFs image-only;
> pdfminer panics"). PyMuPDF succeeds here, which is what makes page-cited
> promotion possible in this pass. **No unofficial sources were used.**

## Summary counts

| Metric | Count |
|---|---|
| Status families inspected (A/B/C/D/E/F/G/H + repo-specific) | 8 families, 41 status codes + 6 repo-specific program records |
| **Procedure records promoted this PR** | **14** |
| New document mappings added | 47 |
| Existing source-confirmed records (prior PRs) — already covered | 4 |
| Total source-confirmed records after this PR | 18 |
| Total structured entries | 338 → 352 |
| Blocked targets (structured reason recorded) | see blocker table |
| `manualCoverageNotFound` targets | A-1/A-2/A-3/B-1/B-2/C-1 registration (diplomatic/short-term) |
| `sourcePageNotLocated` targets | E-1 registration, E-8 registration |

Validator after change:
`by procedureType {visa_issuance:18, other:315, extension:6, registration:13}`,
`by boundaryType {…, parent_code_level:17}`,
`by confidence {MEDIUM:201, LOW:133, HIGH:18}`,
`by readinessLabel {…, STRUCTURED_EVIDENCE_READY:18}`.

## Promoted records (all PDF-verified, parent_code_level, single procedure)

All from `stay_manual_2026_05.pdf`. Each list was verified to be a single
procedure for the **parent** status with no sub-code/scenario split inside the
list; applicant-type / substitute / sub-code conditions are preserved as
document-level `conditionKo` (never flattened into a separate universal
requirement). JSON path: `entries[]` with the new HIGH / STRUCTURED_EVIDENCE_READY
records (`evidenceSource: "pdf_verified"`).

| # | status | family | procedure | page | section title | docs | conditions preserved |
|---|---|---|---|---|---|---|---|
| 1 | D-1 | 문화예술 | registration | 44→34 | 문화예술(D-1) 외국인등록 / 1. 외국인등록 신청서류 | 3 | — |
| 2 | D-5 | 취재 | registration | 104 | 취재(D-5) 외국인등록 | 3 | 대체서류: 지국·지사 미보유 외신 협조공문 갈음 |
| 3 | D-5 | 취재 | extension | 103 | 취재(D-5) 체류기간 연장허가 / 1. 제출서류 | 3 | — |
| 4 | D-6 | 종교 | registration | 107 | 종교(D-6) 외국인등록 | 3 | — |
| 5 | D-6 | 종교 | extension | 107 | 종교(D-6) 체류기간 연장허가 / 1. 제출서류 | 3 | — |
| 6 | D-7 | 주재 | registration | 113 | 주재(D-7) 외국인등록 | 3 | 신청인 유형: 외국법자문법률사무소 등록증 해당자에 한함 |
| 7 | D-8 | 기업투자 | registration | 126 | 기업투자(D-8) 외국인등록 | 3 | 법인등기사항전부증명서는 법인기업인 경우 |
| 8 | E-2 | 회화지도 | registration | 173 | 회화지도(E-2) 외국인등록 | 3 | — |
| 9 | E-3 | 연구 | registration | 194 | 연구(E-3) 외국인등록 | 3 | — |
| 10 | E-4 | 기술지도 | registration | 199 | 기술지도(E-4) 외국인등록 | 3 | — |
| 11 | E-5 | 전문직업 | registration | 204 | 전문직업(E-5) 외국인등록 | 3 | — |
| 12 | E-6 | 예술흥행 | registration | 211 | 예술흥행(E-6) 외국인등록 / 가. 신청서류 | 4 | 채용신체검사서 **E-6-2만 제출**(conditional); 사업자등록증 고용·초청단체 범위 |
| 13 | E-7 | 특정활동 | registration | 228 | 특정활동(E-7) 외국인등록 | 4 | 채용신체검사서 **외국인학교 등의 교사만 해당**(conditional) |
| 14 | E-10 | 선원취업 | registration | 339 | 선원취업(E-10) 외국인등록 | 6 | 건강검진서·마약검사 확인서 밀봉 제출(개봉 불가) |

> "page 44→34": the D-1 list is on printed page **34** (footer `- 34 -`), the same
> uniform 외국인등록 신청서류 template independently confirmed for 유학(D-2) on p.44
> by PR #230. Every page footer above is re-verified by the generator.

### Why each mapping is safe

- The 외국인등록 신청서류 lists (`① 신청서·여권·사진·수수료 ② 소속/기관 입증서류 ③ 체류지 입증서류`)
  are a uniform single-procedure parent-level template; the same template was
  accepted for D-2 registration in PR #230.
- Where a document carries a sub-code/applicant/substitute condition (D-5, D-7,
  D-8, E-6, E-7, E-10) the condition is stored on that document's `conditionKo`
  (and `requiredness: "conditional"` for the E-6-2 / 교사 medical checks) with
  `boundary: "parent_code_level"` — so the validator's parent-level boundary
  invariant holds and nothing is over-generalized.
- The D-5/D-6 extension `1. 제출서류` lists are single-procedure parent-level
  lists with no sub-code branching.

## Already-covered targets (prior PRs — re-confirmed, no change)

| status | procedure | page | source/page metadata adequate? | improved? |
|---|---|---|---|---|
| D-2 | extension | 43 | yes (parent_code_level) | no change |
| D-2 | registration | 44 | yes (parent_code_level) | no change |
| D-4 | extension | 90-91 | yes (sub_code_specific, D-4-1/D-4-7 scoped) | no change |
| E-7 | extension | 226 | yes (parent_code_level) | no change |

## Blocked targets (structured reasons)

Blocker taxonomy: `subCodeSpecific`, `scenarioSplit`, `multiProcedure`,
`manualAmbiguous`, `requiresExternalNotice`, `notParentLevelSafe`,
`sourcePageNotLocated`, `manualCoverageNotFound`, `dataModelMismatch`,
`lowerPriorityAfterSafeBatchLimit`.

| status | family | intended procedure | blocker | explanation / what's still needed |
|---|---|---|---|---|
| A-1 | 외교 | registration | manualCoverageNotFound | 외교/공무/협정 자격은 외국인등록 면제 대상; no 외국인등록 신청서류 list in pp.14-17. |
| A-1/A-2/A-3 | 외교/공무/협정 | extension | notParentLevelSafe | 연장 narrative present but no isolated parent-level 제출서류 list; A-3-9 sub-scoping. |
| B-1 / B-2 | 사증면제/관광통과 | registration/extension | manualCoverageNotFound | Short-stay, no registration/extension document list in stay manual (pp.24-25). |
| C-1 | 일시취재 | registration | manualCoverageNotFound | Short-term; no 외국인등록 신청서류 list (p.26). |
| C-3 | 단기방문 | all | subCodeSpecific + scenarioSplit | Entirely C-3-1…C-3-11 scoped; no parent-level single-procedure list (pp.27-28). |
| C-4 | 단기취업 | all | subCodeSpecific | C-4-1/C-4-5 scoped short-term employment (pp.29-31). |
| D-3 | 기술연수 | registration/extension | notParentLevelSafe | Trainee program; D-3-1 scoping; no clean parent-level 외국인등록 신청서류 list. |
| D-9 | 무역경영 | registration | subCodeSpecific | 외국인등록 list is tied to 무역업(D-9-1) (p.136); not parent-level. |
| D-9 | 무역경영 | extension | subCodeSpecific | 주재(D-7) "가"목/"나"목-style applicant splits; not a single parent list. |
| D-10 | 구직 | other/extension | subCodeSpecific + multiProcedure | D-10-1/2/3 with mixed procedures (per PR #230, p.159). |
| E-1 | 교수 | registration | sourcePageNotLocated | No 외국인등록 신청서류 list located in pp.166-172 (likely 준용); page not isolable. |
| E-8 | 계절근로 | registration | sourcePageNotLocated | Seasonal-work program (pp.324-325); no isolated parent-level registration list. |
| E-9 | 비전문취업 | registration | scenarioSplit | The 외국인등록 list (p.330) embeds a 사업장 변경 scenario branch (item ③ + ☞ 추가서류); promoting would flatten a scenario. |
| F-1 | 방문동거 | registration | subCodeSpecific | Parent #1 list (신청서+체류지) is clean, but the section immediately splits into 외국인유학생 동반부모(F-1-13) sub-code list (p.359); kept blocked to avoid sub-code leakage and preserve F-1's high-risk classification. |
| F-2 | 거주 | all | subCodeSpecific | F-2-1…F-2-9 scoped residence procedures (pp.360-381). |
| F-3 | 동반 | all | subCodeSpecific + scenarioSplit | Dependent status; F-3-1/F-3-2 + relationship scenarios (pp.421-497). |
| F-4 | 재외동포 | all | notParentLevelSafe | Overseas-Korean; activity/reporting-driven, no clean parent-level document list (pp.548-560). |
| F-5 | 영주 | extension | dataModelMismatch | 영주(F-5) has no period-extension procedure (indefinite); F-5-x sub-coded grant criteria instead. |
| F-6 | 결혼이민 | extension | subCodeSpecific | F-6-1/F-6-2/F-6-3 distinct income/document conditions (per PR #230, pp.491-495). |
| G-1 | 기타 | all | scenarioSplit | Intrinsically heterogeneous (humanitarian/refugee/medical), G-1-1…G-1-9 scenario blocks (pp.498-513). |
| H-1 | 관광취업 | registration/extension | notParentLevelSafe | Working-holiday treaty-specific; no clean parent-level 외국인등록 신청서류 list (pp.514-547). |
| H-2 | 방문취업 | other | multiProcedure + requiresExternalNotice | Multi-procedure bundles; production marks 신규발급 중단 (per PR #230). |
| FORDIASP, K-STAR, METRO, REGIONAL, TOPTIER, YOUTH | repo-specific programs | various | dataModelMismatch | Program/scenario records (mostly visa_issuance), not standard parent statuses with a single stay-procedure document list. |
| D-1/E-2/E-3/E-4/E-5/E-7 | various | extension | lowerPriorityAfterSafeBatchLimit | Additional E-series extension lists likely share the clean template but were not hand-verified in this pass; deferred to keep the batch reviewable. D-1 extension also has a two-column continuation that could not be cleanly isolated this pass. |

## Runtime exposure notes

The promotions require **no loader change** — the accessor in
`backend/structured_requirements.py` exposes any HIGH/STRUCTURED_EVIDENCE_READY
entry automatically:

- `GET /api/visas` — the additive `sourceConfirmedStructuredRequirements` field
  now appears on all 14 promoted status records (verified by test
  `test_promoted_statuses_exposed_on_api`).
- `GET /api/visas/{code}/structured-requirements` — returns the new
  source-confirmed entries (`sourceConfirmedCount` reflects them).
- **AI grounding** — `_build_source_confirmed_structured_requirements_block`
  includes the promoted 외국인등록 / 연장 lists for the new statuses
  (verified by `test_ai_block_present_for_new_statuses`). No AI pipeline or UI
  redesign was performed.
- All needs-review / high-risk statuses (C-3, F-1, F-2, F-5, F-6, G-1, H-2, E-9,
  D-10, …) remain hidden (verified by `test_blocked_statuses_remain_hidden`).

## Validation commands & results

```
pip install pymupdf                                                   # extraction helper dep
python3 scripts/promote_source_confirmed_procedures_2026_05.py        # +14 entries, total 352, source-confirmed 18 (idempotent re-run = +0)
python3 scripts/validate_structured_requirements.py backend/data/manual_grounding/structured_requirements_2026_05.json
                                                                      # PASS (352 entries, 2597 docs, 18 HIGH/READY, parent_code_level:17)
python3 -m json.tool backend/data/manual_grounding/structured_requirements_2026_05.json   > /dev/null   # OK
python3 -m json.tool docs/data/structured_requirements_2026_05.json                       > /dev/null   # OK (byte-identical mirror)
python3 -m json.tool backend/data/manual_grounding/structured_requirements_index_2026_05.json > /dev/null   # OK
python3 -m json.tool visa_data.json / backend/data/visas.json / doc_master.json           > /dev/null   # OK (unchanged)
python3 -m pytest backend/tests/test_structured_requirements.py -q     # 26 passed
python3 -m pytest backend/tests/                                       # 235 passed
bash scripts/check_repo.sh                                             # PASS (golden eval: all regression checks passed)
python3 scripts/sync_visa_data.py --check                              # OK (byte-identical)
```

## Explicit safety note

No unofficial sources were used. No scenario-specific requirements were
flattened into parent-level records. Ambiguous targets were blocked instead of
promoted.

- No production JSON changed: `visa_data.json`, `backend/data/visas.json`,
  `doc_master.json` are byte-identical (sync check OK).
- No `verified=true` set on any production record; no `needsManualReview`
  removed; no law-grounding activation; no crawler/source-monitor added.
- All conditions (대체서류 / 면제 / 수수료 / 신청인 유형 / 학교·기관 유형 / 고용 유형 /
  봉인 제출 등) preserved at document level, never collapsed into universal
  requirements.
