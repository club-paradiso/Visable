# POST PR #190 Main State Audit

Date (UTC): 2026-05-26
Branch audited: main tip at `4aa0d71`
Audit branch: `audit/post-pr-190-main-state-audit`

## Executive verdict
- **Main after PR #190 is consistent with intended merge direction for PRs #186–#190**: normalized Agent Mode audit doc exists, frontend accessibility smoke artifacts exist, and search precision PR A artifacts/code are present.
- **No data integrity regressions detected** in `visa_data.json` / `backend/data/visas.json` / `data/scenario_help_records.json` JSON validation and parity checks.
- **Frontend live-page smoke execution remains externally blocked in this environment** due to network/proxy `403` tunnel failures, so direct F/G/H-style visual-browser coverage is still not completed here.

## 1) PR #186–#190 merge summary (from git history)
Observed merge commits:
- `ad69baa` — Merge pull request #186 from `lucanomics/codex/normalize-agent-mode-audit-to-markdown`
- `3a86cca` — Merge pull request #187 from `lucanomics/codex/normalize-agent-mode-audit-to-markdown`
- `ad3b4a1` — Merge pull request #188 from `lucanomics/codex/normalize-agent-mode-audit-to-markdown`
- `892cae3` — Merge pull request #189 from `lucanomics/audit/frontend-accessibility-smoke-2026-05`
- `4aa0d71` — Merge pull request #190 from `lucanomics/fix/search-result-precision-pr-a-2026-05`

Related tip commits in last 10:
- `be4ddb5` — fix(search): improve exact-code result precision
- `56e0372` — audit(frontend): add GitHub Pages accessibility smoke diagnostics
- `fb6f358` — docs: normalize agent mode stay-status audit

## 2) Merged artifact inspection
Expected artifacts:
- ✅ `docs/audits/AGENT_MODE_STAY_STATUS_UI_SOURCE_AUDIT_NORMALIZED_2026_05.md`
- ✅ `docs/audits/FRONTEND_ACCESSIBILITY_SMOKE_2026_05.md`
- ✅ `docs/audits/SEARCH_RESULT_PRECISION_PR_A_2026_05.md`
- ✅ `scripts/smoke_frontend_accessibility.sh`

Additional post-#186 audit note(s) visible in `docs/audits` include:
- `POST_MERGE_DETAIL_ALIAS_DOCS_UI_QA_2026_05.md`

## 3) Architecture inspection snapshot
Inspected targets:
- `index.html`
- `ai.html`
- `visa_data.json`
- `backend/data/visas.json`
- `backend/paradiso_backend.py`
- `backend/tests/test_paradiso_backend.py`
- `scripts/check_repo.sh`
- `.github/workflows/*`

Notable observations:
- Search precision logic is present in `index.html` with code-like normalization, exact-match ranking, and exact-first filtering paths.
- Backend contains robust visa-code normalization and subcode-aware handling in `backend/paradiso_backend.py`, with extensive tests in `backend/tests/test_paradiso_backend.py`.
- Repo check script exists (`scripts/check_repo.sh`) and workflow set is present under `.github/workflows`.

## 4) Data integrity validation
Commands run:
- `python3 -m json.tool visa_data.json > /tmp/visa_data_check.json`
- `python3 -m json.tool backend/data/visas.json > /tmp/backend_visas_check.json`
- `python3 -m json.tool data/scenario_help_records.json > /tmp/scenario_help_records_check.json`
- `cmp -s visa_data.json backend/data/visas.json && echo "visa data parity OK" || echo "visa data parity differs"`

Results:
- ✅ All three JSON files parsed successfully.
- ✅ `visa_data.json` and `backend/data/visas.json` parity check: **OK**.

## 5) Frontend accessibility/smoke status
Smoke script execution:
- `bash scripts/smoke_frontend_accessibility.sh`
- Result: failed at network fetch stage with proxy/tunnel error: `curl: (56) CONNECT tunnel failed, response 403`.

Direct URL probes attempted:
- `https://lucanomics.github.io/Paradiso/`
- `https://lucanomics.github.io/Paradiso/?post_pr_190_smoke=1`

Observed HTTP status (from this environment):
- Both returned `HTTP/1.1 403 Forbidden` through envoy proxy path, with `curl` tunnel failure.

Interpretation:
- In this execution environment, live HTML marker verification, asset-path checks under `/Paradiso/`, and runtime API boot-failure diagnostics could not be fully observed because page content could not be fetched.
- This is an **environment/network access blocker**, not evidence of product regression by itself.

## 6) Search precision implementation audit (PR A)
Status: **Appears merged** (merge commit `4aa0d71`, implementation commit `be4ddb5`).

Evidence of exact-code handling in code/tests/docs includes support/coverage for:
- `A-1`
- `D2 -> D-2`
- `D-4-2K`
- `E-7-4`
- `F-1-6`
- `F-6-1`

Broad discovery preservation:
- `index.html` retains broader keyword scoring and fallback paths; exact-code flow narrows to exact-first where applicable, then falls back to broader scoring when no exact match exists.

Data/manual safety:
- Diff across `ad69baa..4aa0d71` shows only:
  - `docs/audits/FRONTEND_ACCESSIBILITY_SMOKE_2026_05.md`
  - `docs/audits/SEARCH_RESULT_PRECISION_PR_A_2026_05.md`
  - `index.html`
  - `scripts/smoke_frontend_accessibility.sh`
- No changes in `visa_data.json`, `backend/data/visas.json`, or manual-grounding JSON in that range.

## 7) Remaining blockers
- **Batch 2 / Batch 2 rerun F/G/H interactive visual-browser coverage remains incomplete** (consistent with prior known 502/visual-browser limitations and reaffirmed here by current environment’s external fetch blockade).
- Need a successful external browser-capable run to close frontend accessibility smoke items that require real page render checks.

## 8) Recommended next PR sequence
1. **Batch 2 interactive audit rerun** in a browser-capable environment (highest priority blocker removal).
2. If any accessibility defects are confirmed: **PR G0 frontend accessibility fix**.
3. If tab/modal consistency issues remain from interactive rerun: **PR B tab/modal consistency**.
4. Search precision PR A: **already merged**; follow-up only if new edge-case regressions are discovered.

## Validation/housekeeping commands run for this audit
- `git status --short`
- `git log --oneline -10`
- `git log --oneline --merges -20`
- `git diff --name-only ad69baa..4aa0d71`
- JSON/parity commands listed above
- `bash scripts/smoke_frontend_accessibility.sh`
- `curl -I -L --max-time 30 https://lucanomics.github.io/Paradiso/`
- `curl -I -L --max-time 30 "https://lucanomics.github.io/Paradiso/?post_pr_190_smoke=1"`

