# visa_data.json Domain Separation — Audit & Migration Plan (PR E-0)

Branch: `data/audit-visa-data-domain-separation`
Audit date: 2026-05-25
PR: **E-0** (after PR #168)

> **This document is an internal audit/design artifact. It is not legal advice and is not an official immigration decision. This PR does NOT delete, migrate, or rewrite any record.**

## Purpose

`visa_data.json` (58 records) currently mixes the visa/status master with scenario, FAQ, helper, risk-warning, and insurance/utility records. This PR **classifies** every record by domain and source-grounding and **designs a safe, staged migration** so scenario/help/AI-grounding data can be separated from the visa/status master **without breaking UI, search, backend sync, golden tests, or Paradiso AI**.

Machine-readable companion: `docs/data/2026_05_21_visa_data_domain_classification.json` (validated by `scripts/check_visa_data_domain_classification.py`).

---

## Classification summary (58 records)

**Primary type:** visa_status 39 · visa_track 1 (K-STAR) · special_program 1 (REGION-S) · faq 6 · scenario 5 · procedure_helper 3 · risk_warning 2 · insurance_or_utility 1.

**Source-grounding:** manual_grounded 37 · partially_manual_grounded 4 (F-4, H-2, K-STAR, REGION-S) · non_manual_operational 10 · scenario_policy_sensitive 7.

**Keep decision:** keep 41 (visa/status master) · migrate-later 16 (helpers/scenarios) · maybe-compat 1 (K-ETA).

### Records that MUST stay in the visa/status master (41)
All standard Korean status codes `A-1…H-2` (incl. the two `D-4-2K` rows), plus `K-STAR` (visa_track) and `REGION-S` (special_program). These are manual-grounded, validated by `check_repo.sh` (`[A-H]-\d|K-STAR|REGION-S` structure + required `C-3, D-2, F-6, K-STAR`), and drive the coverage matrix (D-2/D-4/E-7).

### Records that are candidates for a future scenario/help/AI-grounding store (17)
| Code | Name | Primary type | Why it doesn't belong in the visa/status master |
|---|---|---|---|
| K-ETA | 전자여행허가 종합 가이드 | faq | Travel-authorization guide, not a 체류자격 code |
| TB-1 | 결핵 진단서 제출 기준 | procedure_helper | Cross-cutting document-criteria card |
| SCN-1 | 글로벌 의사결정 매트릭스 | scenario | Decision-support scenario |
| SCN-2 | 실무 변수 체크리스트 | scenario | Practical checklist |
| SCN-3 | C-3 자격변경 시나리오 | scenario | Scenario walkthrough |
| SCN-4 | F-1-6 혼인단절 타이밍 시나리오 | scenario | Scenario walkthrough |
| SCN-5 | F-4/H-2 동포 제약 시나리오 | scenario | Scenario walkthrough |
| SCN-6 | 오버스테이 (불법체류) 시나리오 | risk_warning | **Overstay** risk guidance |
| OVS-1 | 불법체류다발국가 목록 | risk_warning | **Overstay/illegal-stay** country list |
| NHIS-1 | 건강보험 면제·감면 | insurance_or_utility | NHIS utility, not a status |
| FAQ-1 | 외국인등록 및 체류지 변경 | faq | FAQ |
| FAQ-2 | 체류기간 연장·자격 변경 | faq | FAQ |
| FAQ-3 | 재입국허가 | faq | FAQ |
| FAQ-4 | 전자팩스·오버스테이·국적 | faq | FAQ (**overstay**-related) |
| VW-1 | 무사증·사증면제 구분 | faq | Visa-waiver explainer |
| COM-1 | 비자 공통 구비서류·팁 | procedure_helper | Common-document tips |
| RF-1 | 난민인정신청 제출서류 | procedure_helper | Refugee-application doc helper (G-1 adjacent) |

### Overstay-related records (special attention)
`SCN-6`, `OVS-1`, and `FAQ-4` carry overstay/illegal-stay guidance. They are **policy-sensitive** and are referenced (indirectly) by the AI golden eval (8 overstay questions). They must NOT be deleted before golden-eval parity is proven against the new store.

---

## Required answers

**Should overstay/scenario records be deleted from visa_data.json immediately?**
**No — not immediately.** Immediate deletion would break: (a) `index.html` rendering (the `['faq','scn','nhis'].includes(visa.cat)` branch renders these as FAQ-style cards, plus the `CC`/`CL` color/label maps and `getLabels` are keyed by `cat`); (b) in-app **search** (`buildSearchText` includes these records' fields); (c) **backend tests** (`test_paradiso_backend.py` asserts the **K-ETA** record is present with its exact Korean name via `/api/visas`, and exercises the **`cat`** field in the AI context block); (d) **AI golden eval** (overstay questions grounded by `SCN-6`/`OVS-1`/`FAQ-4`). Safe migration with a compatibility layer is required.

**Which records are candidates for a future scenario/help/AI-grounding database?**
The 17 listed above (faq / scenario / risk_warning / procedure_helper / insurance_or_utility).

**Which records must remain in the visa/status master?**
The 41 status codes `A-1…H-2` (incl. both `D-4-2K`), `K-STAR`, `REGION-S`.

**What compatibility layer is needed?**
A resolver so consumers see the **union** of the visa/status master and the new scenario/help store. Concretely:
- Backend `/api/visas` must keep returning the full union (so the K-ETA test and any count/lookup expectations still pass) until tests are updated, OR add a parallel `/api/scenarios` and update tests in lockstep.
- The frontend `cat`-based rendering (`faq`/`scn`/`nhis` cards), `CC`/`CL` maps, `getLabels`, search index, and the AI context payload (`cat`) must continue to receive the scenario/help records — either by merging both files at load time or by the resolver.
- `doc_master` / `DOC_DICT` references in migrated records must still resolve.

**What UI/search/AI risks exist?**
- **UI:** scenario/faq/nhis cards disappear or lose color/labels if `cat`-keyed records vanish.
- **Search:** keyword/direct-code search loses these records' text.
- **AI:** golden-eval overstay answers and the `cat`-based context block degrade if grounding records are removed.
- **Backend tests:** `test_paradiso_backend.py` (K-ETA presence + `cat`) and `check_repo.sh` fail if the union shrinks or `cat` is dropped.

**What tests are needed before deletion or migration?**
1. A union-equivalence test: `/api/visas` (or merged client dataset) returns the same set of codes (incl. K-ETA) before/after.
2. A render-parity test: every `cat ∈ {faq,scn,nhis}` record still renders a card.
3. A search-parity test: scenario/helper keywords still match.
4. **AI golden-eval parity** (especially the 8 overstay questions) before/after.
5. Extend `check_visa_data_domain_classification.py` (already added) to keep the classification in sync.

**Which remaining source-grounded content PR should come next?**
The domain-separation track (E-1…E-4) is independent of content. The **next source-grounded content PR** should be **D-4-2K duplicate/sub-code resolution** (smallest, self-contained), then **F-4/H-2 sub-manual**, then **K-STAR**, then **REGION-S**. These stay separate content PRs and are NOT part of E-0…E-4.

---

## Staged migration plan (future PRs — none performed here)

- **PR E-1** — Introduce a separate scenario/help/AI-grounding data file (e.g. `scenario_help_data.json`) **with duplicated content** copied (not moved) from the 17 records, plus a compatibility resolver that merges it with `visa_data.json` for all consumers. No deletion. Add union-equivalence + render/search parity tests.
- **PR E-2** — Update AI grounding and search to read **both** `visa_data.json` and the scenario/help file via the resolver. Prove AI golden-eval parity (overstay included).
- **PR E-3** — Deprecate the 17 scenario/help records in `visa_data.json` with **aliases/redirects** (not deletion); resolver prefers the new store. Backend tests updated to read the union.
- **PR E-4** — Remove the scenario/help records from `visa_data.json` **only after** E-1…E-3 tests prove zero UI/search/AI/backend regressions.
- **D-content batches (parallel, separate):** `D-4-2K`, `F-4/H-2`, `K-STAR`, `REGION-S` substantive source-grounded content — independent of E-1…E-4.

---

## Dependency evidence (search results)

- `index.html`: `['faq', 'scn', 'nhis'].includes(visa.cat)` at lines ~10683, 10711, 11493, 11716, 12145, 12194, 12211, 12524; `CC`/`CL` maps keyed by `cat` (10555-10556); `getLabels(v)=CL[v.cat]` (10557); search text builder (11698); AI payload `cat: visa.cat` (11512).
- `backend/tests/test_paradiso_backend.py`: asserts `K-ETA` present + exact Korean name (≈150-167); uses `cat` in `_build_visa_data_context_block` (≈1975-1982); overstay intent tests (≈1185-1227, 1436-1440).
- `backend/data/eval/paradiso_ai_golden_questions.json`: 8 overstay questions (≈518-543).
- `scripts/check_repo.sh`: required `C-3, D-2, F-6, K-STAR` (line 73); `[A-H]-\d|K-STAR|REGION-S` structural validation (line 101).
- `backend/data/eval/paradiso_coverage_matrix.json`: active fixtures reference `D-2`, `D-4`, `E-7`.
- `prototype/index.html`, `prototype/ai.html`: **no** data-file load (standalone; not consumers).
- Backend Python: no `.cat`/scenario-code branching (records served generically).

---

## Changed files (this PR)

| File | Change |
|---|---|
| `docs/data/2026_05_21_VISA_DATA_DOMAIN_SEPARATION_PLAN.md` | this plan |
| `docs/data/2026_05_21_visa_data_domain_classification.json` | machine-readable classification (58 records) |
| `scripts/check_visa_data_domain_classification.py` | read-only classification validator |

**No production data changed.** `visa_data.json`, `backend/data/visas.json`, `doc_master.json`, `index.html`, `source_manifest.json`, and prototype files are untouched. No records deleted; no legal/admin content rewritten; no `verified` promotions; no `needsManualReview` removals.

## Legal Disclaimer

Paradiso is reference software. Nothing in this report or the repository's data files constitutes legal advice, an official immigration decision, or a guarantee of admissibility, eligibility, or processing outcome. Users must verify any specific case with 출입국·외국인청, HiKorea, 1345, or a qualified Korean immigration professional.
