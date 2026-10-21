# 16 — Validation results and evidence ledger

Status: **COMPLETED** (records what was run). Every number here comes from a command
run during Mission 001 (2026-10-19 to 2026-10-21). Paths are repository-relative.

## 1. Baselines before any change

| What | Where | Result |
|---|---|---|
| Backend suite, `scripts/run_backend_tests.py` | origin/main `0713370`, Python 3.11 | 81/81 modules pass (known 0, new 0, skip 0) |
| Repo validation, `scripts/check_repo.sh` | `0713370` | exit 0; Knowledge Platform eval 69/69 |
| CI on main | `fc896c2` (after PRs #659–#665 landed) | Repo Validation and Railway Live Smoke green |
| Backend suite, sparse local checkout | `fc896c2` | 77/82; the 5 failures were only tests that need files left out of the sparse checkout. After switching to a full checkout, all pass |

## 2. Final state of this branch

| Check | Command | Result |
|---|---|---|
| Experiment tests | `cd experiments/waymaker-ai && python -m pytest -q tests` | **1032 passed** |
| Backend suite | `python scripts/run_backend_tests.py` | **83/83 modules pass** (the new `test_law_stack_genesis_regressions.py` is module 83) |
| Dataset validator | `python -m waymaker_ai.dataset datasets/benchmark/v0 --registry datasets/registry` | **PASS**: 188 examples, 0 errors, 16 warnings (all `case_template_dev_eval`: a template shared by dev and an evaluation split) |
| Benchmark runner | `python -m waymaker_ai.evaluation.runner --benchmark datasets/benchmark/v0 --baselines wlie,b1_python,b1_python_raw,b2_js,existing_law,mock_model --splits dev,test,adversarial_holdout` | `reports/benchmark-v0-2026-10-20.{json,md}`, scoring digest `c83cb110…` |
| Hygiene scan of the branch diff | grep for keys, tokens, OC values, ID numbers, phone numbers and e-mail addresses | Only test dummies (`genesis-dummy-oc`, fake ID patterns used to test the PII screen). Local absolute paths were replaced with placeholders |
| CI workflow `.github/workflows/waymaker-ai-experiments.yml` | YAML parse, plus the same commands run locally | **Not yet run on GitHub**; it runs on this PR |

## 3. Benchmark v0 results

Labels are synthetic or machine-checked: 151 machine-checked, 37 unreviewed, **0
human-verified**. The best possible decision is therefore `PROVISIONAL_GO`.

### 3.1 Legal verification (WLIE vs the existing backend)

| Baseline | Split | Overall status accuracy | False absence declarations | Accepted version failures | Critical legal errors |
|---|---|---|---|---|---|
| WLIE, first look (2026-10-19, revision-1 labels) | holdout | 43/45 | 0/15 | 0/5 | 0 |
| WLIE, after the 2026-10-20 spec decisions (**POST-HOC**) | holdout | 45/45 | 0/14 | 0/5 | 0 |
| WLIE | dev / test | 10/10 / 3/3 | — | — | 0 |
| Existing backend at `fc896c2` (before) | holdout | 8/45 | 6/14 | 4/5 | 21 |
| Existing backend with F1–F12 (after) | holdout | 12/45 | 2/14 | 4/5 | 17 |

The 45/45 is not a first-look number. Two spec decisions (the blocked-layer rule
and per-provision `structure_complete`) were made after the holdout had been seen.
The holdout ledger (`reports/holdout-ledger.jsonl`) records 9 looks, so v0's
holdout no longer counts as held out for WLIE. Benchmark v1 needs a fresh, frozen
holdout.

All 4 existing-backend items that improved came from F9 (auth, empty, HTML and
official-error bodies no longer read as "law not found"). The 2 remaining false
absences are titles outside a partial index: the backend has no notion of
coverage. The version failures are unchanged because the backend sends no `efYd`
(Mission 002).

### 3.2 Temporal version selection

WLIE: candidate exact match 21/21 (holdout), 6/6 (dev), 1/1 (test). Warning
recall 30/30, with no forbidden warnings.

### 3.3 Deterministic classifiers (test split)

| Baseline | Status exact | Subcode exact (subcode expected) | Fine procedure | Critical errors (all splits) | Decision |
|---|---|---|---|---|---|
| B2 JS (`status-guidance.js` + `search-router.js`) | 49/55 (0.891) | 29/29 | 44/55 (0.800) | 9 | NO_GO |
| B1 Python (`_detect_visa_codes` + `understand`) | 47/55 (0.855) | 0/29 (it cannot read a subcode from text) | coarse only | 34 | NO_GO |
| mock model (floor) | 8/55 | — | — | 48 | NO_GO |

These are the inputs to Artemis decision rule D1: fix the rules first, and train
only if they still miss the targets ([13 §6](13-artemis-experiment.md)).

## 4. Blind label audit

Two blind annotators re-labelled all 73 citation and temporal items from the specs
and bundles alone, without labels or code ([research-notes/blind-label-audit.md](research-notes/blind-label-audit.md)).

- Overall status (n=50): annotator 1, annotator 2, the labels and WLIE agree 50/50 for every pair (Cohen's κ = 1.000; Wilson 95% [0.929, 1.000]).
- Every labelled layer cell (289/350): the annotators and WLIE all equal the label.
- Temporal (n=23): candidate keys and warning sets agree 23/23 for every pair.
- The annotators diverge on unlabelled L5 cells (33/50, κ 0.517). Eight spec gaps are recorded (SG-1…SG-8). Only SG-5 can flip an overall status.
- **Limitation:** the annotators, the label author and the WLIE implementer are one model family, and blindness rests on self-report. Agreement shows the spec is clear and consistently applied. It does not show legal correctness, which needs human review.

## 5. Adversarial reviews actually performed

| Review | Scope | Outcome |
|---|---|---|
| 12 research verifiers (one per research note) | Each tried to refute its note's key claims with primary evidence | Corrections are written into the notes; for example, "1 uvicorn worker" became a code default, not an observation |
| Integration adjudication, 2 rounds | Every WLIE-vs-label disagreement, judged against the spec | Round 1: 4 spec gaps, which led to the 2026-10-20 decisions. Round 2: 0 triggers |
| Blind label audit | §4 | 0 label, code or forbidden-code findings; 8 spec gaps recorded |
| Branch hygiene scan | §2 | Clean after the path cleanup |

**Not performed:** a separate final multi-reviewer red-team panel over the
finished branch. It was dropped to finish the mission promptly. The PR review
should cover provenance similarity (WLIE code vs the DO-NOT-USE reference files),
the backend diff and the claims in these documents.

## 6. Live and production observations (bounded, read-only)

| Date | What | Result |
|---|---|---|
| 2026-10-19 | Railway `/health`, `/api/health/ai`, preflight, `/api/legal/laws/search?q=출입국관리법` (4 GETs) | Commit `0713370`; law grounding enabled via `LAW_API_OC`; diagnostics mode `open`; 3 statute rows |
| 2026-10-19 | law.go.kr public pages (60 GETs, no credential) | 22 identity records ([04](04-official-api-capability-matrix.md)) |
| 2026-10-19 | 3 documented Open API sample requests | 200; real DRF JSON shape (the basis of the F7 fixture) |
| 2026-10-19 | Hosted korean-law-mcp (≤ 8 calls, public law names) | Behaviour observed ([02](02-korean-law-mcp-study.md)) |
| 2026-10-20 | Railway `/health` after PR #666 and the owner's token | `client_diagnostics_mode: token`; Railway Live Smoke green on `194a47a` |

No `/api/ask` POST was ever sent to production, and no secret value was read.
