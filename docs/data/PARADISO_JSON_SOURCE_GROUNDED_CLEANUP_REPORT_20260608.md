# Paradiso JSON Source-Grounded Cleanup Report — 2026-06-08

**Scope of edit:** `visa_data.json` (+ its generated mirror `backend/data/visas.json`).
**`doc_master.json`:** audited, **no changes required** (already clean — see §6).
**Branch:** `claude/dreamy-goodall-99FGh`

**Official sources used (only these, per rules 5–6):**

| File | Role | Used for |
|---|---|---|
| `docs/source-manuals/2026-06/stay_manual_2026_06_01.pdf` (777 pp., readable text layer) | 체류민원(domestic stay/residence) | foreigner registration, extension, status change, F-5/G-1 framing |
| `docs/source-manuals/2026-05/incoming/visa_manual_2026_05_21_source.pdf` | 사증(visa issuance) | visa-issuance context |

Gemini/Qwen candidate JSON were **not** used as a base and were not needed (rules 1–4). The repo JSON was the structural base; all legal/procedure claims were grounded in the official manuals above or removed/narrowed.

---

## 0. Method — runtime usage understood before editing (Phase 1)

Key findings that shaped every decision (verified in `index.html`, `ai.html`, `backend/`, `scripts/`):

- **`visa_data.json`** is fetched into the global `VISA_DATA` array and records are looked up by **linear `VISA_DATA.find(v => v.code === code)`** (index.html, ai.html). There is no code→record map.
- **`doc_master.json` is NOT loaded at runtime.** The frontend uses a hardcoded `DOC_DICT` map for doc-id→label; `doc_master.json` is consumed only by validators. ⇒ I may only **reuse existing doc IDs** (I cannot add `DOC_DICT` labels), and every referenced id must resolve.
- **`cat`** drives rendering: `scn/faq/nhis` are **helper categories** — rendered as scenario/FAQ cards, **excluded from procedure tabs, the subcode grid, and category counts** (`SKIP_CATS`), with a special "AI 상황 분석" CTA for `scn`.
- **Helper records are live lookup targets** via the hardcoded `ALIAS_MAP` (`전자여행허가`→`K-ETA`, `불법체류`→`OVS-1`, `난민`→`RF-1`, …). Physically removing them would make `VISA_DATA.find()` return `null` and break the AI modal/search.
- **Placeholder suppression already exists** (`isDocPlaceholder`/`DOC_PLACEHOLDER_TOKENS`/`isDocFieldMissing`): `DATA_MISSING` is never shown raw, and `hikorea_task_type==="DATA_MISSING"` triggers a graceful task picker. Removing these sentinels from data is therefore **behavior-identical**.
- **The 17 helper records are already shadow-migrated** to `data/scenario_help_records.json` and **gated against removal until "E-4"** (a runtime cutover). `scripts/check_scenario_help_records.py` enforces that each live record **deep-equals its shadow copy byte-for-byte, with only `migrationMeta` allowed to differ.**

**Hard CI invariants (from `scripts/check_repo.sh`) that constrain edits:**
1. Every code matching `^[A-H]-\d` (plus `K-STAR`, `REGION-S`) MUST keep `procedures.extension` + `procedures.registration` (each with a non-empty `manualRefs` and a `requiredDocs.requiredDocs` **list**) and `manualRequiredDocAudit.manualVersion === "2026.5"`. Helper codes (`K-ETA`, `SCN-*`, `FAQ-*`, …) are exempt.
2. `backend/data/visas.json` must stay byte-identical to `visa_data.json` (`sync_visa_data.py --check`).
3. Doc-like-named fields not in the renderer allowlist must not carry useful values (coverage guard).

---

## 1. Classification summary (Phase 2)

58 records total → **41 canonical** + **17 scenario/help/FAQ**.

| Bucket | Count | Codes |
|---|---|---|
| **A. Canonical visa/status** | 41 | A-1, A-2, A-3, B-1, B-2, C-1, C-3, C-4, D-1, D-2, D-3, D-4, D-4-1, D-4-2K, D-5, D-6, D-7, D-8, D-9, D-10, E-1…E-10, F-1…F-6, G-1, H-1, H-2, K-STAR, REGION-S |
| **B. Scenario/help/FAQ (non-canonical)** | 17 | K-ETA, TB-1, SCN-1…SCN-6, OVS-1, NHIS-1, FAQ-1…FAQ-4, VW-1, COM-1, RF-1 |
| **C. Ambiguous-but-needed** | 0 distinct | (the 17 bucket-B records double as compatibility records: they are runtime lookup/search targets, so they are treated as compatibility-retained — see §2) |

`cat` values for bucket B: `scn` (SCN-1…6, TB-1, OVS-1, RF-1), `faq` (K-ETA, FAQ-1…4, VW-1, COM-1), `nhis` (NHIS-1).

---

## 2. Scenario/helper records — migrated, archived, stubbed (Phase 3)

**Decision: retain byte-for-byte, classify via the parity-exempt `migrationMeta`, archive a quarantine snapshot. Physical removal/stubbing is deferred to the E-4 runtime cutover.**

Why not physically remove or content-strip them now (both were considered):
- **Removal is unsafe**: the runtime looks these codes up directly and via `ALIAS_MAP`; removing them returns `null` and breaks the AI modal/search. `migrationMeta.removalFromVisaDataAllowed` is already `false`.
- **Stubbing (stripping prose) is also unsafe under the 2-file constraint**: `check_scenario_help_records.py` requires each live record to deep-equal its `data/scenario_help_records.json` shadow copy **except `migrationMeta`**. Stripping content would break that green test, and I may not edit the shadow store (or the runtime) to compensate.
- The runtime **already segregates** these (cat-gated): they never render as official procedure/document cards.

**Action taken (the only parity-safe edit):** enriched each record's `migrationMeta` with:
```
migrationMeta.sourceGroundedCleanup20260608 = {
  reviewedAt: "2026-06-08",
  classification: "non_canonical_scenario_help_faq",
  notOfficialVisaStatusGuidance: true,
  verified: false, needsManualReview: true,
  action: "Retained byte-for-byte for runtime + shadow-store parity; removal deferred to E-4",
  quarantineSnapshot: "data/removed_from_visa_data_scenario_records_20260608.json",
  canonicalStore: "data/scenario_help_records.json"
}
```
All 17 records changed **in `migrationMeta` only** (verified diff). The pre-existing E-3 gating fields (`migrationStatus="alias_deprecated_in_visa_data"`, `removalFromVisaDataAllowed=false`, `requiresParityBeforeRemoval=true`) are preserved, so `check_scenario_help_records.py` stays green.

**Archive deliverable:** `data/removed_from_visa_data_scenario_records_20260608.json` — classification + search anchors + runtime-dependency notes + full original snapshot for all 17, with `status: "archived_not_yet_removed"` and the E-4 removal plan.

**To finish the job (out of scope for a `visa_data.json`-only edit) — E-4 runtime PR:**
1. Point search/AI lookup at `data/scenario_help_records.json`.
2. Drop the 17 records from `visa_data.json` (+ mirror).
3. Flip `removalFromVisaDataAllowed=true` and update `check_scenario_help_records.py`.

---

## 3. Canonical status records changed (Phase 4)

41 canonical records changed. Change classes:

### 3a. OCR / glue-artifact de-corruption (whitespace only, all canonical records as applicable)
Pure spacing insertions — no semantic change, verified against the manual:
| Artifact | Fix | Manual basis |
|---|---|---|
| `연장허가1.` (22×) | `연장허가 1.` | stay manual idx 26: text is "체류기간 연장허가" then heading "1. 체류기간 연장 허가" |
| `및체류기간` (4×: B-1, B-2) | `및 체류기간` | manual reads "체류자격 변경 및 체류기간 연장" |
| `연장허가필수서류` (2×: F-5) | `연장허가 필수서류` | — |
| `서류필수서류` (2×: D-1) | `서류 필수서류` | — |
| `필수서류①` (4×: D-1, F-5) | `필수서류 ①` | — |

### 3b. DATA_MISSING hygiene (all 41 canonical records)
Removed 230 `DATA_MISSING` occurrences: dropped `note:"DATA_MISSING"` from document objects, removed whole-field `"DATA_MISSING"` sentinels in `documents_initial/registration/extension` and `hikorea_task_type`. Behavior-identical (renderer already suppresses these; registration tab falls back to `procedures.registration`).

### 3c. Migrated Korean-string doc refs → machine IDs (D-1, D-4, D-7, D-8, H-1)
In ID-reference arrays only, exact-match replacement using the established PR-D-batch-2 mapping (e.g. `수수료`→`doc_fee_generic`, `체류지 입증서류`→`doc_residence_proof_generic`, `여권`→`doc_passport_generic`). All target IDs already exist in `doc_master.json` and have `DOC_DICT` labels. **This clears a pre-existing failure of `scripts/check_doc_master_id_migration.py`.**

### 3d. Known-issue legal-framing fixes
| Code | Issue | Action | Manual grounding (stay_manual_2026_06_01.pdf) |
|---|---|---|---|
| **F-5** | PR shown as ordinary extension; corrupted summary | Reframed `procedures.extension.summary`/`extReq`: F-5 has no stay-extension; **영주증 valid 10y, must be reissued before expiry** (distinct procedure). Source-cross-check note added; `needsManualReview` kept. | 영주(F-5) 절 "라. 영주증 발급 및 재발급 특례 — 영주증 유효기간: 발급일로부터 10년 / 유효기간 만료일 전 재발급(기간 도과 시 과태료)" |
| **G-1** | Sub-case docs (산재/질병/소송/임금체불) merged into one parent-level rule; wrong-code fragments (G 3, G 4) | Replaced parent extension list/summary with an honest **sub-code-specific** statement + common application docs only; removed the merged dump. G-1-5 stays searchable. `needsManualReview` kept; `pageRange` → `pp. 498-513`. | **p. 498** 기타(G-1) 해당자: 산업재해 청구·치료 / 질병·사고 치료 / 소송 진행 / 임금체불 중재 / 난민신청 등 — multiple sub-cases (G-1-6/-7/-11/-99 listed) |

### 3e. Known issues already correct in the base data — verified, left unchanged
| Code | Task concern | Verified state | Manual grounding |
|---|---|---|---|
| **B-1 / B-2** | don't mislabel B-1 as 관광통과; not ordinary registration | B-1 name "사증면제협정", B-2 "관광통과·무사증"; both registration summaries already say "원칙적으로 외국인등록 대상이 아닙니다" | B-1 section (idx 23) has no 외국인등록 (short-stay) |
| **C-3** | extension limited not impossible; registration only C-3-4 칠레 91+ | `procedures.extension.summary` already "…90일 범위 내에서 제한적으로 연장 가능"; registration already scoped to "단기상용(C-3-4)…91일 이상…칠레 국민" | idx 26–27: "입국일로부터 체류기간 90일 범위 내 연장 가능"; "단기상용(C-3-4) 소지자로 91일 이상 체류하고자 하는 칠레 국민 … C-3로 등록" |
| **D-2** | no financial proof as general registration doc | D-2 registration docs = 재학/등록금납입증명서 + 체류지 입증서류 only (**no** 재정입증); financial proof only under issuance/extension | (registration doc set carries no 재정/잔고 requirement) |

Parent/sub-code distinctions preserved throughout; no sub-code-only requirement was promoted to a parent code (rule 8) — G-1 fix specifically enforces this.

---

## 4. Procedure separation (Phase 4.2)

Canonical records retain the structured `procedures.*` keys the schema/renderer expect: `visaIssuance`, `certificateOfVisaIssuance`, `statusChange`, `extension`, `statusGrant`, `registration`, `activitiesOutsideStatus`, `workplaceChange`, `reentry`. The CI schema gate requires `extension` + `registration` (with `manualRefs` + `requiredDocs.requiredDocs` list) on every canonical code; these were preserved (F-5/G-1 corrected, not removed).

---

## 5. Manual source references (by file + page)

- **stay_manual_2026_06_01.pdf** — C-3 extension/registration **pp. ~26–27** (printed); G-1 category & sub-cases **p. 498**, G-1 procedures **pp. 498–513**; F-5 영주증 재발급 특례 (영주 section, "영주증 유효기간 10년"); D-2/D-1 registration sections; B-1 short-stay section (no registration).
- **visa_manual_2026_05_21_source.pdf** — visa-issuance context (no canonical issuance claims were added in this pass).

Page numbers are from the 2026-06-01 stay manual's text layer (printed page = PDF index + 1 in the main body; the 영주(F-5) section is separately paginated). F-5/G-1 framing was cross-checked against this text layer but retains `needsManualReview: true` (AI cross-check, not human sign-off).

---

## 6. doc_master changes (Phase 5)

**No edits.** Audit result:
- Schema preserved (flat **array** of `{id, ko_name, en_name, description}`) — not converted to `{documents:[…]}` (rule 4). ✔
- **No duplicate IDs** (80 ids). ✔
- **All 79 doc IDs referenced from `visa_data.json` resolve.** ✔
- No `DATA_MISSING`/OCR artifacts in user-facing fields. ✔
- No second ID system introduced; no new IDs needed (all repaired refs reuse existing IDs). ✔
- The one "orphan" `doc_arc_fee` is **kept** — it is referenced by the frontend `COMMON_NEW` default set in `index.html` (not a true orphan).
- Near-duplicate families (passport/fee/application-form variants) were **not merged** — merging is only allowed when references are safely migrated (rule 6) and carries net risk for no user-facing benefit.

**doc IDs added / removed / merged: none.** doc IDs **re-pointed** (in `visa_data.json` only): 5 Korean-string refs → existing machine IDs (§3c).

---

## 7. Validation results

**Full CI gate `bash scripts/check_repo.sh`: PASS** (all 14 steps), including:
- JSON valid; U+FFFD scan; representative manual schema; source manuals registered; `git diff --check` clean; i18n; branding scan; **`sync_visa_data.py --check` (mirror in sync)**; required-documents coverage; **backend pytest `test_paradiso_backend.py`**; **golden eval** (all `gq_*` pass, incl. `gq_f5_renewal_ko_01`, `gq_f5_card_en_01`, `gq_g1_humanitarian_generic_ko_01`).

**Node regression suite: PASS** — `check_placeholder_suppression`, `check_d2_student_journey`, `check_priority_status_journeys`, `check_remaining_status_journeys`, `check_exact_code_search`, `check_static_visa_result_cards`, `check_ai_shell_semantics`, `check_procedure_journey_audit`, `audit_procedure_journeys`, `check_i18n`.

**Python validators: PASS** — `check_visa_text_corruption`, `check_required_documents_coverage`, **`check_scenario_help_records` (parity preserved)**, **`check_doc_master_id_migration` (was failing at baseline → now PASS)**, `check_record_store_union_parity`, `check_visa_data_domain_classification`, `check_visa_data_text_integrity`, `check_source_manuals`.

**Task checklist `scripts/validate_source_grounded_cleanup_20260608.py`: 8/8 PASS** — parses ×2; no dup doc IDs; all refs resolve; no DATA_MISSING in user-facing doc names/notes; no OCR artifacts (canonical); all 18 priority codes present; G-1-5 searchable (subCode + searchAlias).

**Idempotency:** `cleanup_…py --check` ⇒ OK (re-running is a no-op).

---

## 8. Unresolved risks

1. **Scenario-record removal is deferred to E-4 (runtime work).** The 17 helper records still physically live in `visa_data.json` (parity/runtime-gated). They are clearly classified non-canonical and cat-segregated, but full "visa_data contains only canonical records" requires the runtime cutover described in §2.
2. **F-5/G-1 reframes are AI-cross-checked, not human-verified** (`needsManualReview: true` retained). A human should confirm the manual framing before flipping `verified`.
3. **Residual auto-extracted corruption in non-priority records.** Some `extReq`/`procedures.*.summary` fields still contain wrong-code fragments from noisy PDF extraction (e.g. D-4 "어학연수생(D 1, D 7)", F-6's doubled legacy `extReq`). These are in fields already flagged `needsManualReview` and (for F-6) not the displayed summary. Per "don't overfit to noisy extraction / missing-but-honest > confident nonsense," they were left flagged rather than reconstructed by guess.
4. **`backend/data/visas.json` was regenerated** via the repo's own `scripts/sync_visa_data.py` (a generated mirror, required by CI step 11). This is a build artifact, not a hand-edit, but it is a third changed file beyond the two source files.
5. **`feeInfo` boilerplate** (identical generic block on every canonical record, `verified:false`) was left intact — out of scope, already caution-flagged.

---

## 9. Final verdict

### SAFE AFTER HUMAN REVIEW

- **Mergeable now from a safety/runtime standpoint:** every automated gate is green (full `check_repo.sh`, node + python validators, custom checklist), the backend mirror is in sync, and no runtime contract was broken. The canonical changes are predominantly subtractive (OCR/DATA_MISSING) plus two manual-grounded legal-framing corrections.
- **Human review recommended before flipping review flags** for: (2) F-5/G-1 manual framing confirmation, (1) the decision to schedule the E-4 runtime cutover that physically removes the scenario records, and (3) the remaining flagged auto-extracted procedure text.

No confident-but-unsourced content was added. Where the manual did not directly support a claim, the claim was removed, narrowed, or left `needsManualReview` (rules 5–8).
