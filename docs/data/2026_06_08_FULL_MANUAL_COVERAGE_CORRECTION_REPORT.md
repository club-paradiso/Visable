# Full manual coverage correction — deliverables report (2026-06-08)

Source-grounded correction of Paradiso's visa/status data coverage, exact-code
search, and result UI against the official 2026.5 manuals.

## 1. Source files used

| Manual | File | Version | Source date | Pages | Extraction |
|---|---|---|---|---|---|
| 사증발급 안내매뉴얼 | `docs/source-manuals/2026-05/visa_manual_2026_05.pdf` | 2026.5 | 2026-05-21 | 484 | `pdftotext -layout` (poppler 24.02), no OCR |
| 외국인체류 안내매뉴얼 | `docs/source-manuals/2026-06/stay_manual_2026_06_01.pdf` | 2026.5 | 2026-06-01 | 777 | `pdftotext -layout` (poppler 24.02), no OCR |

Located via `docs/source-manuals/source_manifest.json`. PDFs were **not** edited.
The May and June stay manuals were confirmed byte-identical for all cited pages
(per-page text hashing of 13 sampled pages spanning the document).

## 2. Codes patched (active / searchable)

**G-1 family (re-grounded from stay manual pp. 497–512) — fixed 4 label conflicts:**
- `G-1-1` 산업재해 청구·치료자와 그 가족 *(was mislabeled 난민인정 신청자)*
- `G-1-2` 질병·사고로 치료 중인 사람과 그 가족 *(headline: previously unsearchable — only existed as a procedure variant)*
- `G-1-3` 각종 소송 진행 중인 사람 · `G-1-4` 임금체불 중재 중인 사람
- `G-1-5` 난민신청자 *(was mislabeled 난민 가족결합)* · `G-1-6` 난민불인정자 중 인도적 체류허가자
- `G-1-7` 사고 등 사망자의 가족 · `G-1-9` 임신·출산 인도적 배려 · `G-1-10` 외국인환자 *(label/source normalized)*
- `G-1-11` 성폭력피해자 등 *(was mislabeled 국내출생 외국국적 아동)* · `G-1-12` 인도적 체류허가자의 가족 *(was mislabeled 긴급구제)*
- `G-1-8 / G-1-13 / G-1-14` 장기체류 아동 체계 *(needsManualReview=true)* · `G-1-99` 기타 사유

**Seasonal work (visa manual pp. 277–279):**
- `C-4-5` 계절근로 외 단기취업 (active)
- `E-8-1 … E-8-8, E-8-99` (all active — the current seasonal-worker path)

**Arrival tourism / talent / startup / nomad / trade:**
- `C-3-7` 도착관광 · `A-3-99` Fulbright 협정대상자 · `D-8-4S` 스타트업 코리아 특별비자
- `D-9-5` 유학생 무역경영자 · `F-1-D` 디지털노마드(워케이션) · `H-2-7` 만기출국 후 재입국한 사람
- `E-7-S1` 네거티브 고소득자 / `E-7-S2` 네거티브 첨단산업 *(kept distinct, not collapsed into E-7-S)*

**Promoted from procedure-variant-only to searchable subcodes (grounded):**
- `F-1-16` 난민인정자 가족 · `F-1-52` 결혼이민자 전혼관계 자녀 · `F-2-8` / `F-2-81` 관광·휴양시설 투자

**K-STAR track:** `F-2-7S` 거주 · `F-2-71` 거주 동반가족 · `F-5-S1` 영주 · `F-5-S2` 영주 동반가족
(exposed as `K-STAR` subcodes + on `F-2`/`F-5`; not merged with 점수제 거주 F-2-7).

**Top-Tier:** `D-10-T` · `E-7-T` · `F-2-T` · `F-5-T` (verified searchable).

**지역특화형 (REGION-S):** `F-2-R`, `F-3-1R`, `F-3-2R`, `F-3-3R`, `E-7-4R`, `F-4-R`, `F-5-6R`,
plus `REGIONAL-D-2`/`REGIONAL-E-7` (광역형). All searchable by code and natural-language names.

**Program helper record:** `YOUTH-STAY` 국내 성장 기반 외국인 청소년 취업·정주 체류제도 —
findable by `국내 성장 기반 외국인 청소년`, `외국인 청소년 취업 정주`, `청소년 정주`, `D-10 청소년 특례`.
Clearly labeled as a manual program/framework, **not** a formal 체류자격 code.

## 3. Codes intentionally quarantined (NOT shown as active)

| Code | Classification | Reason (source) |
|---|---|---|
| `C-3-11` 교대선원 | deprecated | 코로나19 한시 지침, '22.6. 사증발급 정상화로 폐지 (visa p. 33) |
| `C-4-1`–`C-4-4` 계절근로 단기취업 | suspended | '25년부터 사증발급 중단; 현행은 E-8 (visa pp. 277–278) |
| `D-3-1` | legacy | '06.12.31.까지 등록자; 현행 D-3-11/12/13 (visa p. 352) |
| `G-1-19` | reference_only | E-8-5/E-8-6 재입국 추천 연계 표기일 뿐, 사용자 안내용 자격 항목 아님 (visa pp. 278–279) |
| `C-3-91` 칭다오·충칭 호구자 | reference_only | 지역 복수사증 분류 마커 (visa p. 36) |
| `E-7-H` | internal_system_marker | 체류자격외활동 입력용 전산기호 (stay p. 499) — 체류자격 코드 아님; subcode로 추가하지 않음 |

## 4. UI changes (index.html)

- **Doc-id resolution:** `DOC_DICT` synced with `doc_master.json` (3 leaking ids fixed + 16 new generic docs). Unknown ids now render `문서 정의 필요` with the raw id only in a debug `data-doc-id` attribute — **never visible**.
- **Exact-search index extended:** `getExactQueryMatchRank` now also indexes `procedures.*.variants[].statusCode` so codes that live only in a procedure variant remain searchable by exact code.
- **Subcode grid redesigned (`renderSubcodes`):** category grouping (e.g., G-1 → 산재·치료 / 소송·임금 / 난민·인도적 / 아동·가족 / 기타), a compact first group with a full-width `더 보기 / 접기` toggle (auto-opens when a hidden group holds a match — `접기` no longer floats mid-layout).
- **Matched-subcode banner:** searching an exact subcode shows `일치 세부코드: CODE · official label`, a source/status chip, and a `이 세부코드 보기` button that scrolls to the highlighted card.
- **Source/status chips:** `공식근거 있음` / `매뉴얼 확인 필요` / `자동추출 검토 필요` / `폐지/비활성` per subcode; deprecated/suspended/legacy/reference-only subcodes render dimmed/dashed (`is-inactive`) and never as active options.
- **Floating AI button:** extra bottom clearance for document/checklist controls on small screens (`max-width: 60vw`, `.rlist` padding).
- New i18n keys added to **both** ko and en packs (counts stay balanced; `check_i18n.js` passes).
- **Preserved:** all legal disclaimers, official-source warnings, `needsManualReview` warnings, the source/evidence panel, and `verified=true` was never introduced.

## 5. JSON changes

- **`visa_data.json`** — 58 → **59** records (+`YOUTH-STAY`); G-1 subcodes re-grounded; ~80 active subcodes added/normalized across C-3, C-4, E-8, D-8, D-9, D-3, A-3, F-1, E-7, H-2, F-2, F-5, REGION-S, K-STAR; every new subcode carries `searchAliases` + `manualRefs` (manualName/manualVersion/sourceDate/sourceFile/pageRange/confidence/needsManualReview) + `status`. Lowercase/uppercase `subcodes`/`subCodes` arrays kept in sync (frontend reads lowercase first).
- **`doc_master.json`** — 80 → **101** entries (16 new source-grounded generic docs + 5 frontend-parity ids). Every doc id referenced by `visa_data.json` now exists in `doc_master.json` **and** `DOC_DICT`.
- **`docs/data/2026_05_21_visa_data_domain_classification.json`** — +1 (`YOUTH-STAY`).

## 6. Validation outputs

```
python3 -m json.tool visa_data.json            → valid
python3 -m json.tool doc_master.json           → valid
python3 -m json.tool backend/data/visas.json   → valid
scripts/check_doc_master_integrity.py          → PASS (95 referenced, 101 master, 101 DOC_DICT)
scripts/check_exact_code_search_coverage.py    → PASS (42 smoke queries)
scripts/check_status_variant_indexing.py       → PASS
scripts/check_manual_code_coverage.py          → PASS (missing: 0; quarantined: 7)
scripts/check_exact_code_search.js (existing)  → 17 passed, 0 failed
scripts/sync_visa_data.py --check              → in sync
bash scripts/check_repo.sh                      → Success (full CI gate, incl. golden eval)
backend full pytest                             → 1058 passed, 7 pre-existing failures (see §8)
```

## 7. Manual smoke-test results

Resolution exercised against the **real** frontend functions extracted from
`index.html` (`normalizeVisaCode`, `getVisaSubcodes`, `getExactQueryMatchRank`,
`normalizeCodeLikeQuery`, `isCodeLikeQuery`) — **29/29 code queries resolve**,
including the headline `G-1-2`, plus `C-4-5`, `E-8-1…99`, `D-8-4S`, `D-9-5`,
`E-7-S1/S2`, `F-1-D`, `F-2-7S`, `F-3-1R`, `F-5-S1/S2`, `H-2-7`, `D-10-T`,
`E-7-T`, `F-2-T`, `F-5-T`, `A-3-99`, `F-4-R`, `F-5-6R`, `E-7-4R`. Natural-language
program queries (`국내 성장 기반 외국인 청소년`, `디지털노마드`) also resolve.
`check_exact_code_search_coverage.py` additionally asserts every active subcode resolves.

## 8. Remaining risks

- **7 pre-existing test failures** in `backend/tests/test_scenario_procedure_variants.py` /
  `test_reentry_procedure_coverage.py` exist **on the base branch** (an incomplete prior
  May→June migration: those tests hardcode the May stay-manual path and the
  `populate_*/promote_*` `--check` idempotency tests are already red). This PR introduces
  **zero new failures** there (verified by baseline diff). These are **not** run by the CI
  gate `check_repo.sh`, which passes fully.
- **Stay-manual path migration deferred:** 71 pre-existing scenario-variant `sourceFile`
  refs still cite the May path. They are accurate (May≡June for those pages) and are
  codified by the above tests, so completing the dataset-wide repoint is tracked as a
  follow-up rather than forced here. All **new** records cite the current June manual.
- **needsManualReview retained** on most new subcodes: subcode cards expose a representative
  document subset; the authoritative page-cited document lists live in the procedure
  variants. No detailed permanent-residence requirements were invented.
- `G-1-8/13/14` exact split and some special-program detailed requirements remain
  `needsManualReview=true` pending finer page-level transcription.

## 9. backend/data/visas.json

**Generated, not hand-edited.** It is a verbatim sync of `visa_data.json` produced by
`python3 scripts/sync_visa_data.py` (`--check` confirms parity). The Railway build context
is `backend/`, so this synced copy is the deploy artifact.
