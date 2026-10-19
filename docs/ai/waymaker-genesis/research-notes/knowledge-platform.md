# Waymaker Knowledge Platform, registries, eval corpora, experiments — audit notes

Mission 001 "Waymaker Genesis", 2026-10-19. Audited tree: worktree of `origin/main` @ `0713370`
(`/Users/seonjaekim/dev/Visable-genesis`), read-only. Paths below are repo-relative to that worktree
unless prefixed. Owner branch `fix/waymaker-qa-2026-10-16` (~/dev/Paradiso) is mentioned only where it
changes a conclusion.

Status vocabulary: VERIFIED (I checked primary evidence), OBSERVED (I ran it), README-ONLY, INFERRED,
UNVERIFIED. No network requests were made in this task.

---

## 0. Executive summary

* The Knowledge Platform (`backend/services/knowledge/`, 21 modules, ~5.5k LOC + one 462-line SQL
  migration) is a real, well-guarded system: SQLite store with DB-level triggers that make
  "AI output can never be published without a human" true even for raw SQL, a 9-state lifecycle,
  transactional publish/supersede, deterministic conflict and diff, a privacy-minimised learning loop and a
  persistent assertion-based eval corpus. [CODE backend/services/knowledge/migrations/0001_knowledge_foundation.sql:229-283] VERIFIED.
  [corrected by verifier: the triggers enforce lifecycle structure, not actor identity. Raw SQL can still UPDATE a
  published fact's citation (page, excerpt, `source_version_id`), INSERT extra citations, and rewrite
  `verified_by`/`effective_to`. Only citation DELETE, content-column UPDATE and audit UPDATE/DELETE are blocked
  (LIVE in-memory probe verifier/kp_verify4.py, 2026-10-19, OBSERVED). "Never published without a human" holds for
  the Python API, not for arbitrary raw SQL.]
* What it holds today is tiny: **42 PUBLISHED facts** (27 `required_document`, 15 `procedural_note`) in
  **3 variants** (D-2, D-4 [covers D-4-1, D-4-7], E-7 — all `extension`), all seeded from
  `backend/data/manual_grounding/stay_manual_grounding_2026_05.json`, all citing **one edition,
  `stay_manual_2026_06_23_pdf` (2026.6), which the registry marks `deprecated` and the approval index marks
  `superseded`** (never content-approved). The approved stay edition (2026.7 HWP) backs zero facts.
  [LIVE in-memory bootstrap probe, 2026-10-19] OBSERVED.
* Runtime gating is: `/api/ask` document grounding reads PUBLISHED facts only, and the Answer Guard
  post-checks model text. The **coverage decision is computed and logged but does not gate the answer path**
  in `paradiso_backend.py` (no code reads `decision.state`). [CODE backend/paradiso_backend.py:2751-2790, 4017-4049, 6209-6217; grep for `.decision`/`coverage_state` returned nothing] VERIFIED.
* Eval assets: knowledge seed corpus (19 cases) + 50 golden routing questions run strictly in CI (69/69
  pass, OBSERVED); plus enforcement benchmark corpora (36+10+13), employment analyzer fixtures (583),
  scenario audit cases (17), coverage matrix (20 rows). **None of them has human-verified label provenance
  recorded per case**; the strongest provenance discipline is the enforcement benchmark schema 2.0.0.
  [corrected by verifier: this is true of the populated corpora. A stricter human-review ground-truth protocol
  exists but has no records yet: backend/data/enforcement/*.schema.json plus
  enforcement_outcome_intake/prediction_freeze/outcome_evaluation.py. See Verification pass O1.]
* The Gemma 4 fine-tune experiment is a Colab scaffold with **14 synthetic placeholder examples
  (6 train / 8 eval), AI-generated from a build prompt, never run in-repo (0 notebook outputs, no result
  files)**, with several latent defects (eval set never scored, eval merged into train by the build script,
  output format diverges from the production answer contract). Its `validate_dataset.py` runs clean offline.
* Tests: `test_knowledge_platform.py` 62 passed + 19 subtests; `test_knowledge_deploy_context.py` 1 passed;
  `validate_dataset.py` 0 errors/0 warnings. OBSERVED. [verifier: the deploy-context pass could not be
  reproduced in the verifier's run because the disk was full (ENOSPC); see §6.]

---

## 1. Component inventory (a)

### 1.1 Module map

| Module | Role | Notes |
|---|---|---|
| `models.py` | enums + pydantic boundary schemas (`FactProposal`, `SourceLocation`, `ReviewActionRequest`, `EvalCaseIn`, `FeedbackIn`) | `KNOWLEDGE_PLATFORM_VERSION = "2026-09-knowledge-platform-v1"` [CODE models.py:21] |
| `store.py` | stdlib `sqlite3`, migrations with checksum immutability, `BEGIN IMMEDIATE` transactions, append-only audit | in-memory fallback, `durable=False` [CODE store.py:78-90, 107-142] |
| `lifecycle.py` | transition whitelist + allowed actor kinds per target | mirrored by DB table+trigger; test asserts equality |
| `repository.py` | the only writer; idempotent `insert_proposal` on `proposal_hash` | |
| `conflicts.py` | deterministic slot-level conflict/update classifier | |
| `review.py` | queue, transparent priority, actions, transactional publish, impact | |
| `ingestion.py` | validate / classify / `dry_run`/`validate`/`apply`; never publishes | |
| `adapters.py` | `source_registry` sync, `legacy_grounding` seed (publishes), `status_guidance` (2026.9 → proposals), `extraction_json` (forced `ai_extraction`) | |
| `diff.py` | ADDED/REMOVED/CHANGED/UNCHANGED per slot between two editions of one source | |
| `retrieval.py` | `retrieve(status, procedure, subcode, intent, as_of)`; LRU cache keyed on store revision | |
| `understanding.py` | composes existing detectors; keyword facets | "not a second router" |
| `coverage.py` | `decide()` → `CoverageState` + `AnswerPath` + gap reason | |
| `guard.py` | regex Answer Guard (critical/high/medium/low) | |
| `privacy.py`, `learning.py` | observations, deduplicated gaps, feedback, gap→eval promotion | |
| `evals.py` | persistent eval corpus + offline runner | |
| `evidence.py` | reviewer evidence view by reference (corpus page text / legacy excerpt / citation excerpt) | |
| `runtime.py` | facade, `/api/ask` adapter `to_grounding`, singleton with in-memory fallback | |
| `api.py` | FastAPI router: 2 public + 24 operator routes under `/api/knowledge/studio` | bearer tokens from `WAYMAKER_OPERATOR_TOKENS`, 503 when unset [CODE api.py:52-78] |
| `paths.py` | repo-root file with `backend/data/knowledge_deploy/` fallback (Railway root = backend) | deploy copies byte-identical (cmp, VERIFIED) |

### 1.2 Data model — exact fields and enum values (VERIFIED from `migrations/0001_knowledge_foundation.sql` and `models.py`)

**Fact** (`knowledge_facts`, one immutable row per version): `fact_id, lineage_id, version_no(>=1), variant_id,
property, item_key, slot_key (=variant_key|property|item_key), value_text (canonical Korean), value_json,
condition_kind, condition_text, display_translations (non-authoritative), sort_order, authority_type, origin,
extraction_confidence (0..1, "never an approval input"), extraction_warnings, lifecycle_state, effective_from,
effective_to, published_at, superseded_at, supersedes_fact_id, superseded_by_fact_id, reviewed_by, reviewed_at,
verified_by, verified_at, reviewer_kind, created_by, created_by_kind, created_at, proposal_hash (UNIQUE)`.
[CODE 0001_knowledge_foundation.sql:134-196]

| Enum | Values |
|---|---|
| `lifecycle_state` | DRAFT, AI_EXTRACTED, HUMAN_REVIEW_REQUIRED, HUMAN_REVIEWED, VERIFIED, PUBLISHED, SUPERSEDED, WITHDRAWN, REJECTED |
| `property` | required_document, eligibility_rule, fee, deadline, appointment, online_service, reporting_duty, exception, condition, procedural_note |
| `condition_kind` | always, conditional, applicant_specific, office_discretion |
| `requirement_level` (in `value_json`) | common, required, conditional, additional |
| `origin` | legacy_repository_verified, operator_manual, ai_extraction, parser_extraction |
| `authority_type` | statute, approved_manual, official_guidance, consular_guidance, administrative_source, precedent, structured_data, unapproved_extraction (reused from `services.immigration_tools.AuthorityType`) |
| `reviewer_kind` | human_operator, legacy_repository_verification |
| `created_by_kind` / audit `actor_kind` | human_operator, ai_extractor, parser, legacy_import, system |

**Variant** (`procedure_variants`): `variant_key = status|subcode-or-*|procedure|scenario`, parent `status_code`,
exact `subcode` or NULL + explicit `subcodes_covered` JSON, `procedure`, `procedure_family IN ('stay','visa')`,
CHECK subcode belongs to status. Procedures: stay = extension, status_change, registration, reentry,
activities_outside_status, workplace_change, status_grant, address_report, reporting_duty; visa = visa_issuance,
visa_issuance_confirmation. [CODE models.py:124-139]

**Source / version / section**: `sources(source_key UNIQUE, authority_type, procedure_family IN
('stay','visa','law','general'), refresh_state IN ('current','refresh_due','superseded','unavailable'),
registry_ref, ...)`; `source_versions(edition_ref, version_label, revision_date, published_date,
effective_from NULL=unknown, content_sha256, artifact_ref (internal), page_count, status IN
('active','staged','superseded','future_effective','withdrawn'), content_review_state IN
('approved','needs_review','rejected','not_applicable'), supersedes_version_id)`; `source_sections` page anchors.
**Citation** (`fact_citations`): source_version_id, section_title, page_start/end, locator, evidence_excerpt
(≤4000), `locator_verified` 0/1, internal `verification_note`. [CODE 0001:24-84, 207-224]

### 1.3 Persistence

SQLite via stdlib, path `WAYMAKER_KNOWLEDGE_DB`, default `backend/var/knowledge/waymaker_knowledge.sqlite3`
(git-ignored), WAL mode, one connection + RLock. Unopenable path or init exception → in-memory store,
re-seeded from committed files, `durable=False` surfaced in Studio. [CODE store.py:40-100; runtime.py:359-374]
`backend/railway.json` declares no volume; doc says mounting one is an operator step "not performed by this PR".
[CODE backend/railway.json; DOC docs/ai/WAYMAKER_KNOWLEDGE_PLATFORM.md §12] VERIFIED (config); production
volume state UNVERIFIED. `backend/tests/conftest.py:9` forces `:memory:` for pytest, but standalone scripts
(e.g. the golden-eval runner) use the default on-disk path — OBSERVED: my golden-eval run logged
`registry existing 12, seed existing 42`, i.e. it opened a pre-existing git-ignored DB in the worktree
(file mtime unchanged; transient WAL files only). [corrected by verifier: the worktree's `backend/var/` was
  created 2026-10-19 12:34:48, after the 12:26:59 checkout (`stat`). The DB was therefore produced by a process
  run during this mission, not by a developer.]

### 1.4 Ingestion

Pipeline: registry sync → proposal (pydantic) → referential validation (status universe = 269 codes from
`data/status-guidance-202609.json`; source version exists, not withdrawn; page ≤ page_count; stay/visa scope
match → `PROCEDURE_SCOPE_MISMATCH`; approved_manual needs page or locator; AI extraction must carry
`evidence_excerpt`) → classify (`add/update/reconfirm/duplicate/conflict/invalid`) → apply inserts proposals
and opens one review task per fact. Initial state by origin: ai_extraction→AI_EXTRACTED; parser, operator,
legacy→HUMAN_REVIEW_REQUIRED. [CODE ingestion.py:55-66, 120-178, 181-218] VERIFIED.
A content-unapproved cited edition is only a **warning** (`ingestion.py:173-174`). Dry-run of the 2026.9
status-guidance adapter over six stay procedures: 423 proposals → add 398, update 13, reconfirm 12; every one
warns "cited source edition's content is not yet approved". [LIVE kp_probe dry-run, no writes] OBSERVED.

### 1.5 Review workflow and approval states

Transitions (identical in Python and SQL): DRAFT/AI_EXTRACTED→HUMAN_REVIEW_REQUIRED|REJECTED;
HUMAN_REVIEW_REQUIRED→HUMAN_REVIEWED|REJECTED; HUMAN_REVIEWED→VERIFIED|HUMAN_REVIEW_REQUIRED|REJECTED;
VERIFIED→PUBLISHED|HUMAN_REVIEW_REQUIRED|REJECTED; PUBLISHED→SUPERSEDED|WITHDRAWN. Actor rules:
HUMAN_REVIEWED/VERIFIED/PUBLISHED only `human_operator` or `legacy_import` (and legacy only for
`legacy_repository_verified` origin); WITHDRAWN human only. [CODE lifecycle.py:26-53; repository.py:393-398]
DB triggers: insert-only-as-proposal, AI must enter AI_EXTRACTED, whitelist, publish requires ≥1 citation,
reviewed content immutable, reviewed citations undeletable, reviewed facts undeletable, audit append-only.
[CODE 0001:229-283, 325-328] Review tasks: kinds new_fact/update_fact/conflict/source_refresh/gap_resolution,
status open/needs_evidence/resolved/rejected, one open task per fact, transparent `priority_factors`
(gap frequency, feedback, procedure risk, authority rank, affected evals, open conflicts, age, update-of-published).
[CODE review.py:74-112] Publish: VERIFIED only, citations non-empty, cited version not `withdrawn`, stay/visa
family match, no open conflicts, then supersede or end-date predecessor in one transaction.
[CODE review.py:220-268] Edit = new version, old proposal REJECTED. Reject and conflict resolution require a
reason (`review.py:271, 362`); **publish reason is enforced only in the Studio UI**
(`assets/js/knowledge-studio.js:303`), not API/CLI. **No separation of duties**: the same operator may
approve, verify and publish (the end-to-end test does exactly that with one `OPERATOR`).
[TEST backend/tests/test_knowledge_platform.py:279-308 (ran: pass)] VERIFIED.

### 1.6 How review state gates runtime answers

| Gate | Mechanism | Evidence |
|---|---|---|
| Only PUBLISHED facts answer "current" queries; historical `as_of` may return SUPERSEDED | `retrieval.py:163,176` | VERIFIED |
| Variants with only proposals are never selectable | `answerable_variants` [CODE retrieval.py:106-118] | VERIFIED |
| Sub-code never inherits parent unless in `subcodes_covered` | [CODE retrieval.py:120-134] | VERIFIED |
| `/api/ask` document grounding = PUBLISHED-only `grounding_for` | [CODE paradiso_backend.py:4017-4049; runtime.py:115-126] | VERIFIED |
| Conflicts reach public coverage only if every side is human-backed (reviewed or operator_manual); then disputed items move to `missing_or_unverified` + uncertainty flag | [CODE retrieval.py:213-228; runtime.py:329-349; paradiso_backend.py:6214-6217] | VERIFIED |
| Answer Guard: critical → text withheld / deterministic fallback; high → structured summary dropped | [CODE paradiso_backend.py:2817-2820, 6606-6633] | VERIFIED |
| Coverage decision (`NO_DIRECT_SOURCE`, `NEEDS_CLARIFICATION`, …) | **advisory only** — recorded in `knowledge_plan` diagnostics, observations and gaps, asserted by evals; not read by the answer path | VERIFIED (grep) |
| Source freshness (`newer_edition_available`) | operator-only; not shown in the public payload | [CODE retrieval.py:255-263; grep structured_answer.py/paradiso_backend.py for `freshness` = no hits] VERIFIED. [corrected by verifier: freshness is not a coverage input either. D-2
  and E-7 still decide `VERIFIED_WITH_CONDITIONS`, with only the reason string `freshness:newer_edition_available`
  (coverage.py:112-129; LIVE verifier/kp_verify2.py)] |
| Cited edition `content_review_state` | **not a publish or retrieval gate** | [CODE review.py:233-238; ingestion.py:173] VERIFIED |

### 1.7 Conflict records

`knowledge_conflicts(conflict_id, fact_a_id, fact_b_id (sorted, UNIQUE pair, a≠b), slot_key, conflict_kind IN
('value_mismatch','authority_contradiction','version_contradiction','temporal_overlap'), status IN
('open','resolved','dismissed'), detected_at, resolved_at, resolution)`. Classification: equal value signature
(text, condition_kind, requirement_level) = corroboration; same source newer edition vs published = `update`
(not a conflict); same version disagreeing = value_mismatch; older edition = version_contradiction; both
explicit effective dates overlapping = temporal_overlap; different authority rank = authority_contradiction.
Conflicts block approve/verify/publish of either side; resolution keeps A/B (loser REJECTED if unpublished) or
dismisses, reason required, audited. [CODE conflicts.py:27-126; review.py:211-218, 357-381] VERIFIED. Detection
is slot-key equality only (normalized item name), so semantic contradictions across differently worded items
are not detected (INFERRED).

### 1.8 Learning loop / privacy (brief)

Observations keep features + ≤200-char redacted excerpt + fingerprint, `expires_at` (default 90 days), never
raw text; gaps deduplicated on `status|subcode|procedure|intent|reason`; four feedback reasons feed gaps;
user-fact gaps (clarifications) never queued; answers never become facts.
[CODE privacy.py:28-80; learning.py:43-99; TEST test_knowledge_platform.py LearningLoopTests (pass)] VERIFIED.

---

## 2. Registries (b)

### 2.1 `data/source_registry.json` (schema_version "1.0", 16 entries)

Entry fields (all 16): `id, type, title, title_en, authority, version, local_path, url, last_known_hash,
last_checked_at, update_frequency, status, notes`; partial: `source_date`(10), `language`(7),
`confidence`(7), `superseded_by`(7). Types: hwp_manual, pdf_manual, notice_index, law_api. Statuses: active (2),
deprecated (7), not_configured (4), needs_manual_review (3). [LIVE python3 -I parse] VERIFIED.

| id | version | registry status | approval_state | in knowledge store as |
|---|---|---|---|---|
| visa_manual_2026_07_31_hwp | 2026.7 | active | approved | active / approved |
| stay_manual_2026_07_31_hwp | 2026.7 | active | approved | active / approved |
| visa_manual_2026_06_17_pdf, _txt | 2026.6 | deprecated | superseded | superseded / needs_review |
| stay_manual_2026_06_23_pdf | 2026.6 | deprecated | superseded | superseded / needs_review — **cited by all 42 published facts** |
| stay_manual_2026_06_17_txt, _06_01_pdf, _05_pdf; visa_manual_2026_05_pdf | 2026.5–6 | deprecated | superseded | superseded / needs_review |
| visa_manual_2026_09_01_pdf (519 corpus pages) | 2026.9 | needs_manual_review | needs_review | staged / needs_review |
| stay_manual_2026_09_18_pdf (810 corpus pages), stay_manual_2026_09_18_hwp | 2026.9 | needs_manual_review | needs_review | staged / needs_review |
| hikorea/moj notice placeholders, law_api_placeholder | — | not_configured | draft | skipped by sync |

Sync maps registry `active→active`, `deprecated→superseded`, `needs_manual_review→staged`; approval
`approved→approved`, `rejected→rejected`, anything else (incl. `superseded`) → `needs_review`.
[CODE adapters.py:64-69, 87-134] 12 versions created across 2 sources (`stay_guide_manual`,
`visa_issuance_manual`); `dongpo_manual` family defined but has no registry entries. OBSERVED.
Drift: registry `notes` still say "No production code path reads this file" — false since `bootstrap()` reads
it on every process start. [DOC data/source_registry.json:6; CODE adapters.py:295-305] VERIFIED.

### 2.2 `data/manual_approval_index.json` (schema_version "1.0", generated 2026-08-09, 18 documents)

Per-document fields: `approval_state` (18), `source_confidence` (15), `effective_date` (14), `section_locator`
(14), `extraction_warnings` (14), `parser` (12), `has_tables_or_annexes` (10), `reviewer`/`reviewed_at` (9),
`table_extraction_warnings` (9), `source_path`/`source_sha256`/`extracted_text_path` (7), `superseded_date` (6),
`would_supersede`/`manifest_slot`/`change_review_artifact` (3). States: approved 2, superseded 7, needs_review 5,
draft 4. The two approved documents carry a named reviewer (the owner) and `reviewed_at 2026-08-09`; approval
covers body text only; table warnings remain. Index notes: "Only 'approved' content may back a direct assertion
in an AI answer" and fail-closed on a corrupt index (enforced in `services/manual_registry.py`, not in the
knowledge platform). [DOC data/manual_approval_index.json notes] VERIFIED.

**Approved for runtime on main: `visa_manual_2026_07_31_hwp`, `stay_manual_2026_07_31_hwp` only.**
Orphans: `visa_manual_2026_09_01_hwp`, `stay_manual_2026_09_01_hwp` are in the approval index but not the
registry, so they never reach the knowledge store. VERIFIED (set difference).

**Material branch change**: on `fix/waymaker-qa-2026-10-16` the 2026.9 PDFs/HWPs are `approved` [corrected by verifier: four editions are approved
(visa_manual_2026_09_01_hwp/pdf, stay_manual_2026_09_18_pdf/hwp); stay_manual_2026_09_01_hwp becomes `superseded`;
two new *_md entries are `needs_review`]
(`reviewed_at 2026-10-16`), 2026.7 becomes `superseded`, the legacy seed's `source_file` becomes
`docs/source-manuals/2026-09/stay_manual_260918.pdf` (2026.9), `seed_legacy` gains supersede-and-retire logic,
and seed eval cases switch `SOURCE_MUST_BE` from 2026.6 to 2026.9 (D-4 pages 90-91 → 90-92). If merged, the
"runtime cites a superseded, unapproved edition" finding is resolved. [git show/diff fix/waymaker-qa-2026-10-16] VERIFIED.

---

## 3. Eval / golden / benchmark corpora (c)

| Path | Count | Task | Label provenance | Scoring code | CI? |
|---|---|---|---|---|---|
| `backend/data/knowledge/eval_corpus_seed.json` | 19 cases (18 ko, 1 en), 96 assertions | knowledge behaviour: status/subcode/procedure/intent/coverage, bucket, source, clarify, gap, leaks | hand-authored; file `provenance` says expected facts = legacy verified grounding (2026.6); `is_training_data:false`; imported as `approved` with `approved_by="seed:eval_corpus_seed.json"` (non-human actor); 1 case is tagged `synthetic` (H-2) | `EvalService.evaluate` [CODE evals.py:198-265] | yes, strict, `check_repo.sh` step 14b [CODE scripts/check_repo.sh:546-559]; OBSERVED 69/69 incl. golden |
| `backend/data/eval/paradiso_ai_golden_questions.json` | 50 (30 ko/20 en); grounding: scoped_fallback 35, active_grounded 9, candidate_only 4, unsupported 2 | routing/detection/grounding selection, no LLM | "artificial examples written to exercise code paths" [DOC docs/paradiso_ai_golden_evals.md]; doc still says 45 questions (drift) | `scripts/evaluate_paradiso_ai_golden_questions.py`; also imported as 50 knowledge eval cases (`golden_questions_v1`) | yes: step 14 (non-strict, regression-fails) + 14b; OBSERVED `--strict` 50/50 |
| `backend/data/eval/scenario_grounding_audit_cases_2026_06.json` | 17 | nuanced-scenario classification / contract, any-of assertions | hand-authored audit cases | `backend/tests/test_scenario_grounding_audit_2026_06.py` | via full backend suite (`run_backend_tests.py`, step 13) — not run by me |
| `backend/data/eval/paradiso_coverage_matrix.json` | 20 rows (scoped_fallback 13, active_grounded 3, candidate_only 2, clarification_needed 2) | control plane, not a test set | hand-authored | `scripts/validate_coverage_matrix.py` | yes (step ~180) — not run by me |
| `backend/tests/fixtures/enforcement_v3_benchmark_corpus.json` | 36 (narrative 28, structured 8; suites: classification-boundary 13, colloquial-extraction 8, rule-engine 8, security-fail-closed 7) | enforcement extraction + rule engine + abstention + invariants | schema 2.0.0 requires per-case `provenance.sourceFile/sourceTest`; "promoted from already-checked repository tests; no new legal outcome labels" | `services/enforcement_benchmark.py` `validate_benchmark_dataset`, `run_benchmark` | pytest modules in full suite; live model comparison only via `workflow_dispatch` workflows |
| `…/enforcement_v3_benchmark_seed.json` | 10 | same, schema 1.0.0 | promoted from parity fixture | same | same |
| `…/enforcement_extraction_parity.json` | 13 | Python/JS extraction parity | "expectations assert only facts the text establishes" | Python test + `scripts/check_enforcement_extraction_quality.mjs` | yes |
| `data/employment/*_test_cases.json` | 79 + 60 + 65 + 193 + 104 + 82 = 583 | job-code analyzer modes | generated by `scripts/build_employment_test_cases.mjs`; codes resolved from `jobcode_master.json` at test time | `scripts/check_employment_*.mjs` | yes [CODE check_repo.sh:221-232] |
| `tests/fixtures/waymaker/d2_documents_*.json` | 3 | committed `/api/ask` answer-card fixtures | generated (`scripts/build_waymaker_answer_fixtures.py`) | Playwright `waymaker-answer-card.spec.mjs` | yes (e2e job) |
| `experiments/waymaker-gemma4-finetune/dataset/*.jsonl` | 6 + 8 | fine-tune behaviour/format | synthetic, AI-generated placeholders (§4) | `validate_dataset.py`, `eval_outputs.py` | no |
| Owner branch only: `scripts/benchmark_waymaker_models.py` | reuses golden questions | live/dry-run model comparison through real `/api/ask` | — | deterministic scoring, no LLM judge | not in CI (branch) |

Other harness worth reusing as a pattern: `services/enforcement_evaluation_plan.py` — a preregistered,
hash-identified evaluation plan with fixed metric whitelist, minimum-sample suppression and an explicit
`allowPerformanceVerdict: false` policy (JSON Schema in `backend/data/enforcement/evaluation_plan.schema.json`).
[CODE enforcement_evaluation_plan.py:1-60] VERIFIED.

Weak spots (VERIFIED in code): only **1 of 69** knowledge eval cases declares `depends_on_slots` (2 slots), so
review-impact analysis and the `affected_evals` priority factor are near-empty [LIVE probe `eval deps: (2, 1)`];
the eval runner calls the Answer Guard with `verified_facts=[]`, so the `unsupported_document` and
`conditional_promoted_to_universal` checks are never exercised by the corpus [CODE evals.py:185-187];
`eval_runs.mode` allows `live` but only `offline` exists [CODE 0001:448; evals.py:288].

---

## 4. Gemma 4 fine-tune experiment (d)

* **What it does**: Colab notebook (15 cells) for LoRA/QLoRA SFT on `messages` JSONL (system/user/assistant),
  loss masked to the assistant turn, model presets qwen-0.6b/1.7b(default)/4b, gemma-4-E4B-it, gemma-4-12B-it;
  ULTRA_LOW_MEM default (seq 512, `max_steps` 30); saves adapter to `/content`, optional Drive and private Hub
  push; 4 hardcoded inference behaviour probes; scores them with `eval_outputs.py`. Goal: behaviour/format
  only (answer from `evidence_pack`, defer, no invented fees/periods/docs, 6-section Korean structure).
  [DOC experiments/waymaker-gemma4-finetune/README.md; CODE notebook cells 4, 8-13] VERIFIED.
* **Dataset**: 6 train + 8 eval = 14 examples, only `messages` key, avg assistant 569/505 chars, every
  excerpt marked `[플레이스홀더 …]`. Provenance: synthetic, generated by an agent from
  `prompts/fable5_colab_build_prompt.md` ("the specification used to generate" the directory); no human label
  review recorded. Status codes covered: train D-2, D-10, E-7, F-2-7, F-4; eval D-2, D-10, E-7, F-2, F-4, F-6,
  G-1, G-1-5. [LIVE validate_dataset.py output] OBSERVED.
* **Did training run?** No evidence in repo: notebook has 0 code cells with outputs and 0 execution counts;
  no adapters, outputs.jsonl, logs or result files; git history is three scaffold commits (#359 2026-06-12,
  #399/#402 2026-06-15). [LIVE ipynb parse; git log -- experiments/] VERIFIED (absence in repo; runs outside the
  repo UNVERIFIED).
* **Latent defects** (VERIFIED from code unless marked):
  1. The 8-row "golden eval set" is never scored: inference uses 4 hardcoded cases; `eval.sample.jsonl` rows
     lack `expected_behavior`/`evidence_pack`/`output` that `eval_outputs.py` expects; it is passed as
     `eval_dataset` but `TrainingArguments` sets no eval strategy (default is no evaluation — INFERRED).
  2. `build_colab_dataset.py` defaults to merging train **and eval** samples, then re-splits → eval leakage into
     training if used as documented.
  3. `bf16=True` and bf16 compute dtype are hard-coded while the README targets a T4 (no native bf16) —
     may error or run emulated (INFERRED, UNVERIFIED).
  4. `%pip install -q -U transformers accelerate peft bitsandbytes datasets huggingface_hub` — unpinned.
  5. Target 6-section format exists nowhere in production; `git grep` for its section headers outside
     `experiments/` returns nothing; production uses `structured_answer` + answer-shape gate
     (`ANSWER_SHAPE_VERSION = "2026-05-answer-shape-gate-v1"`).
  6. The production Answer Guard's provider regex matches "gemma"/"qwen", so any self-identifying output is
     withheld (fine, but shows the experiment was not designed against the guard).
* **License/governance**: Gemma presets are gated and need licence acceptance (README-ONLY); exact Gemma 4
  licence terms UNVERIFIED (no network in this task). Qwen3 presets are described as open (README-ONLY).
  Platform doc: "Fine-tuning is not implemented. A future training candidate may come only from reviewed,
  anonymized, approved eval cases" [DOC WAYMAKER_KNOWLEDGE_PLATFORM.md §10] — no such export path exists
  (`export-evals` exports eval cases, not training pairs). Experiment is isolated: only referenced from one audit
  doc. [git grep] VERIFIED.
* **Reusable**: `validate_dataset.py` (stdlib, structural + overclaim/fee/period/section/disclaimer checks,
  code-stripping before number scans), the messages-JSONL schema, the assistant-only label-masking cell,
  `eval_outputs.py` heuristics (overlap with `guard.py` `_CERTAINTY_RE`; guard is broader).

---

## 5. REUSE MAP (e)

| Capability | Waymaker already provides? | Extendable? | What would regress if changed |
|---|---|---|---|
| **Dataset schema** | Yes, three: `EvalCaseIn` + `eval_cases` table (case_key pattern, query, language, expected, typed assertions, risk_category, tags, payload_visa_code, depends_on_slots; origin ∈ seed_foundation/golden_questions_v1/promoted_gap/operator; state draft/approved/retired); golden-question JSON; enforcement benchmark schema 2.0.0 with mandatory per-case provenance. Gemma messages JSONL is separate. | Yes. Missing: per-case label provenance (who verified the expected answer, against which edition/page), `is_synthetic`, split. Add via migration `0002_*` (additive columns). Changing the `origin` CHECK needs a SQLite table rebuild. | Migration checksum immutability (`store.py:124-126`) — never edit 0001; CI 14b strict corpus; `test_migrations_are_idempotent_and_immutable`; branch `_refresh_seed_case` logic. |
| **Dataset validator** | Partly: pydantic `EvalCaseIn` (on import), `validate_benchmark_dataset` (enforcement), `validate_dataset.py` (gemma), `validate_coverage_matrix.py`, `check_source_grounding_metadata.py`. No JSON Schema for `eval_corpus_seed.json` or golden questions. | Yes — model a knowledge-corpus validator on `validate_benchmark_dataset` (duplicate ids, required provenance, kind/suite). | Seed import runs at every bootstrap (`runtime.py:108-111`, failures swallowed); a stricter validator raising there would be hidden — must run in CI separately. |
| **Benchmark fixtures** | Yes (§3): 19 + 50 knowledge, 17 scenario, 36+10+13 enforcement, 583 employment, 3 answer-card, 14 gemma. | Yes; biggest gap is breadth — published knowledge covers only D-2/D-4/E-7 extension. | Seed cases pin `SOURCE_MUST_BE edition 2026.6` and page ranges; any re-seed to a newer edition fails 3 cases until updated (the branch does this). D-2 answer-card fixtures are byte-compared in e2e. |
| **Evaluation runner** | Yes: `EvalService.run` (offline, selector all/tag/key, persisted runs/results, JSON/text report via `knowledge_cli.py eval`); golden runner; enforcement `run_benchmark`; branch adds live model benchmark. | Yes — `mode='live'` already in schema; add a live mode reusing branch benchmark harness. | CI step 14b must stay offline/no-network; `observe_case` uses `platform.plan()` so understanding/coverage changes shift outcomes. |
| **Scoring** | Binary pass/fail per case with failure strings (17 assertion types) — no aggregate metrics. Enforcement harness has exact-match, material-fact accuracy, abstention precision/recall, latency p50/p95, per-suite. Gemma heuristics. | Yes — port enforcement metrics (abstention ≈ NEEDS_CLARIFICATION/LIMITED_GUIDANCE) and preregistered plan pattern. | `report_text` / Studio `last_result` shape consumed by `knowledge-studio.js` and `KnowledgeStudioContractTests`. |
| **Conflict records** | Yes: `knowledge_conflicts` (4 kinds, 3 statuses, resolution, audit), publish blocking, public conflict view. | Yes — statute sources fit (`sources.procedure_family='law'`, `authority_contradiction`). Semantic (non-slot) conflicts would need a new detector. | `test_conflicting_proposals_are_detected_blocked…`, `…operator_contradiction…downgrades_coverage`, `…unreviewed_parser_update_never_changes_public_answers`; changing the "human-backed both sides" rule would let junk extractions degrade verified answers. |
| **Verification states** | Several unaligned vocabularies: fact `lifecycle_state` (9), version `status` (5) + `content_review_state` (4), source `refresh_state` (4), approval index `approval_state`, `CoverageState` (9), guard outcome (4); plus the DRAFT `docs/ai/CITATION_AND_UNCERTAINTY_SCHEMA.md` (8 uncertainty + 7 citation-verification states, "target state, not implemented") and `data/schemas/source_grounding_schema.json` (SourceRecord/EvidenceRecord/AnswerGrounding). No crosswalk between the knowledge platform and the draft schema. | Yes — a mapping table (e.g. PUBLISHED+approved edition → `verified`; PUBLISHED+superseded edition → `outdated_or_unknown`) is additive. | `to_grounding` hard-codes `source_verification_status: "verified_locally"` for every published fact (`runtime.py:289`) — legacy consumers and parity test depend on it. |
| **Evidence package** | Yes: `RetrievalResult.internal()/public()`, `to_grounding` + private `_knowledge` bundle, `evidence_for_fact` (by reference: parsed corpus page window → legacy excerpt → citation excerpt), `export_published` (`waymaker-published-knowledge/1`). Separate `law_evidence_pack` in `paradiso_backend`. | Yes — `public()` is the right seed for a model-facing evidence pack. Note corpus text exists only for the two 2026.9 PDFs, so the 2026.6-cited facts fall back to legacy excerpts. | `test_knowledge_grounding_is_equivalent_to_the_legacy_file`, `test_public_export_has_no_review_or_internal_metadata`, `_public_ask_payload` stripping `knowledge_plan`; prompt builder/source card read the legacy dict shape. |

Reference repo `korean-law-mcp` (untrusted, not executed): filename search shows unit tests around a
citation-verification tool and a knowledge-base tool (`src/tools/verify-citations*.ts`,
`src/tools/knowledge-base*.ts`) and 17 `test/*.cjs` scripts, but no labelled immigration eval corpus. [file
listing only] INFERRED — not a source of reusable eval data for Waymaker.

---

## 6. Test / tool runs (f)

| Command | Result |
|---|---|
| `.venv-check/bin/python -m pytest -q backend/tests/test_knowledge_platform.py backend/tests/test_knowledge_deploy_context.py -p no:cacheprovider` | **63 passed, 5 warnings (pydantic `model_` namespace), 19 subtests passed in 6.61s** — OBSERVED |
| same, per file | platform: 62 passed + 19 subtests (5.24s); deploy context: 1 passed (1.07s) — OBSERVED. [verifier rerun 2026-10-19: the platform result was reproduced
  (62 passed + 19 subtests); deploy context FAILED with `[Errno 28] No space left on device` inside the test's
  copytree. The failure is environmental, and the original pass was not reproduced.] |
| `python3 -I scripts/validate_dataset.py dataset/train.sample.jsonl dataset/eval.sample.jsonl` (Python 3.14.7, cwd experiment dir) | train 6 ex / 0 err / 0 warn, 6/6 defer language, 6/6 six-section; eval 8 / 0 / 0, 8/8, 8/8; `Total errors: 0`, exit 0 — OBSERVED |
| `knowledge_cli.py --db :memory: eval --selector all --strict` (CI step 14b equivalent, cwd scratchpad) | `total 69 passed 69 failed 0`, exit 0 — OBSERVED |
| `evaluate_paradiso_ai_golden_questions.py --strict` | 50/50 passed, 0 known gaps, exit 0; side effect: opened the pre-existing git-ignored `backend/var/knowledge/waymaker_knowledge.sqlite3` (content mtime unchanged) — OBSERVED |
| scratchpad `kp_probe.py` (in-memory bootstrap + dry-run ingest, no writes) | numbers quoted in §§0-3 — OBSERVED |

---

## 7. Risk register (g)

| ID | Sev | Risk | Evidence | Remedy |
|---|---|---|---|---|
| KP-1 | high | All 42 runtime facts cite a superseded, never content-approved stay edition (2026.6), while the approved 2026.7 edition backs nothing; staleness (`refresh_due`, `newer_edition_available`) is operator-only and not shown to users. | LIVE probe; CODE retrieval.py:255-263, adapters.py:153-174; DOC platform §9 ("not a public downgrade") | Merge/finish the branch re-seed on approved 2026.9, or surface an `outdated_or_unknown` flag publicly until re-verified. |
| KP-2 | high | Publish does not require the cited edition to be content-approved; only an ingestion warning. Contradicts the approval index rule that only approved content may back a direct assertion. | CODE review.py:233-238, ingestion.py:173-174; TEST test_knowledge_platform.py:279-300 publishes 2026.9 (needs_review) citations | Add a publish check `content_review_state == 'approved'` (or explicit override + audit) and a DB trigger. |
| KP-3 | medium | No separation of duties: one operator token can approve, verify and publish; eval cases can be created and approved by the same operator; publish reason enforced only client-side. | CODE repository.py:393-413, review.py:220-268, evals.py:83-95, knowledge-studio.js:303 | Require verifier ≠ reviewer for PUBLISHED; server-side reason requirement. |
| KP-4 | medium | Durability: SQLite on ephemeral Railway FS unless a volume is mounted; failure silently falls back to in-memory re-seed — operator edits, gaps, feedback, eval runs lost on redeploy. Production volume state unknown. | CODE store.py:78-90, runtime.py:359-374; backend/railway.json (no volume) | Confirm volume + `WAYMAKER_KNOWLEDGE_DB`; alert when `durable=false` in production. [corrected by verifier: the fallback is logged, not silent. Also,
  `durable=false` only flags a path that cannot be opened. The default path on an ephemeral filesystem opens fine
  and reports `durable=True`, so the alert should check that the configured path is a mounted volume.] |
| KP-5 | medium | Coverage decision is advisory; `/api/ask` answer path is not gated by `NO_DIRECT_SOURCE`/`NEEDS_CLARIFICATION`, so uncovered questions still go to the existing LLM pipeline. | CODE paradiso_backend.py:2751-2790, 6209-6217 (no reader of `decision.state`) | Decide explicitly which coverage states must constrain generation; add eval assertions on the served path. |
| KP-6 | medium | Eval corpus is narrow and self-referential: labels hand/agent-authored, seed cases auto-"approved" by a seed actor, expectations derived from the same legacy file that seeds the facts; 1/69 cases has slot dependencies; guard runs with no verified facts in evals. | DATA eval_corpus_seed.json `provenance`; CODE evals.py:130-131, 185-187; LIVE `eval deps (2,1)` | Add label-provenance fields, human sign-off, slot dependencies; pass verified facts to the guard in evals. |
| KP-7 | medium | Unreviewed 2026.9 status guidance (697 docs `SEPT_2026_ORIGINAL_UNREVIEWED`) powers the front-end Quick Answer — a second, unreviewed truth outside the lifecycle. | DATA data/status-guidance-202609.json; CODE assets/js/status-guidance.js, index.html; DOC platform §13.4 | Migrate Quick Answer to `GET /api/knowledge/published` as planned. [verifier: partly mitigated. The UI labels this
  content 검토 전 원문 and shows a disclaimer that the guides are unreviewed (assets/js/status-guidance.js:74, 134, 144).] |
| KP-8 | low | Non-pytest scripts (golden runner) use the default on-disk DB; local results can depend on a stale/edited dev DB. | OBSERVED golden run log `existing 12 / 42`; CODE store.py:62-63 | Force `:memory:` in CI scripts or pass `--db`. |
| KP-9 | low | Documentation/data drift: registry note "No production code path reads this file"; golden doc says 45 (is 50); adapters comment says manual-corpus not deployed (it is, 3.2 MB); 2 approval-index editions absent from registry; `verified_locally` stamped on all published facts. | VERIFIED citations in §§2-3, runtime.py:289 | Doc/data hygiene PR. |
| KP-10 | medium (if pursued) | Gemma experiment is not a usable training/eval asset: 14 synthetic AI-generated examples, never run, eval never scored, eval→train leakage in build script, bf16 on T4, unpinned deps, off-contract output format, licence unverified. | §4 | Treat as scaffolding only; any real dataset must come from published facts + approved eval cases with provenance, target the production answer contract, and pin deps. |
| KP-11 | low | Streaming answers are not guarded pre-display. | DOC platform §9 (README-ONLY) | Verify in the streaming path before relying on the guard. |

---

## 8. Open questions

1. Is a Railway volume mounted and `WAYMAKER_KNOWLEDGE_DB` set in production? Are `WAYMAKER_OPERATOR_TOKENS`
   set (is the Studio live)?
2. Will the owner branch (2026.9 approval + re-seed) be pushed/merged, and was the 2026-10-16 approval a
   line-by-line content review of the five pages the 42 facts cite?
3. Should the coverage decision gate generation, or remain diagnostics-only by design?
4. Gemma 4 licence terms and whether any Colab run happened outside the repo (no artefacts here).
5. Is the intended source of fine-tune/eval labels the PUBLISHED knowledge export, the approved eval corpus,
   or a new human-labelled set?

---

## Verification pass

Adversarial re-check by a second agent, 2026-10-19, against the same worktree (`0713370`, confirmed with
`git rev-parse`). All runs used an in-memory store (`WAYMAKER_KNOWLEDGE_DB=:memory:`), so nothing was written into
the worktree. The verifier scripts are in `scratchpad/verifier/`. The host disk was at 100% during this pass
(about 180 MB free, with repeated `ENOSPC` errors), which affected one test (claim 13).

### Verdicts on the 15 headline claims

| # | Claim (short) | Verdict | Evidence / correction |
|---|---|---|---|
| 1 | 42 PUBLISHED facts (27 documents + 15 notes), 3 extension variants, nothing pending | **confirmed** | [LIVE verifier/kp_verify.py] `states {'PUBLISHED': 42}`; 27 `required_document` and 15 `procedural_note`. Variants are D-2, D-4 (`["D-4-1","D-4-7"]`) and E-7, all `extension`. Conflicts 0, gaps 0, open tasks 0. This matches the seed file: D-2 has 8 documents and 5 notes, D-4 has 9 and 4, E-7 has 10 and 6 [DOC backend/data/manual_grounding/stay_manual_grounding_2026_05.json]. OBSERVED. |
| 2 | All 42 cite the superseded `stay_manual_2026_06_23_pdf`; the approved 2026.7 edition backs nothing; staleness is shown only to operators | **confirmed (strengthened)** | [LIVE kp_verify.py] `cited [('stay_manual_2026_06_23_pdf','superseded','needs_review',42)]`. The bootstrap `refresh_due` names that edition as stale and `stay_manual_2026_07_31_hwp` as current. New finding [LIVE kp_verify2.py]: D-2 and E-7 extension questions still decide `VERIFIED_WITH_CONDITIONS`. Staleness appears only as the reason string `freshness:newer_edition_available`, because `decide()` downgrades only on `cited_edition_withdrawn` [CODE coverage.py:112-129]. `public()` has no freshness field, and `to_grounding` stamps `verified_locally` [CODE runtime.py:289]. This is by design [DOC WAYMAKER_KNOWLEDGE_PLATFORM.md:256-258]. |
| 3 | Publishing does not require an approved cited edition; ingestion only warns; the end-to-end test publishes against the unapproved 2026.9 edition | **confirmed** | [CODE review.py:227-239] has no `content_review_state` check. [CODE ingestion.py:173-174] only warns. [TEST test_knowledge_platform.py:279-308 (ran: pass)] asserts `("2026.9", 540)`. [LIVE kp_verify3.py] dry run of 423 proposals (add 398, update 13, reconfirm 12); all 423 carry the "not yet approved" warning. VERIFIED. |
| 4 | Triggers enforce: insert only as a proposal, AI output enters as AI_EXTRACTED, a transition whitelist, publish needs a citation, **reviewed content and citations are immutable and undeletable**, append-only audit | **corrected** | Most of the claim holds [CODE 0001:113-133, 186-196, 229-283, 325-328]. However, **citations are undeletable, not immutable.** [LIVE kp_verify4.py, raw SQL on an in-memory store, PUBLISHED fact] These were ALLOWED: UPDATE of a citation's page and excerpt, UPDATE of a citation's `source_version_id`, INSERT of an extra citation, UPDATE of `verified_by` and `effective_to`, and UPDATE of a version's `content_review_state`. These were BLOCKED: citation DELETE, UPDATE of `value_text`, UPDATE of the audit log. The triggers check states, not who the actor is. |
| 5 | The coverage decision is advisory; nothing reads `decision.state` to gate generation | **confirmed (refined)** | [LIVE grep `\.decision\b` in non-test backend code] Hits only in runtime.py:83, 184, 197-201 and evals.py:188. runtime.py:184 passes `coverage_state` to the guard, but `guard.check` never uses that parameter [CODE guard.py:142, 197-200]. runtime.py:160 runs only when `build_structured=True`, and `/api/ask` passes `False` [CODE paradiso_backend.py:2758]. `knowledge_plan` is removed from the public payload [CODE paradiso_backend.py:5600, 5616-5620]. VERIFIED. |
| 6 | No separation of duties; the publish reason is enforced only in the Studio UI | **confirmed** | [CODE repository.py:385-413] no check that the reviewer and verifier differ. [CODE api.py:52-78] tokens map to names only; there are no roles. [CODE models.py:505-507] `reason` defaults to `""`. [CODE knowledge-studio.js:299-303] the UI is the only place that requires a reason. [CODE evals.py:83-95] the same actor can create and approve eval cases. Addition: the CLI accepts a free-text `--operator <name>` with no token [DOC scripts/knowledge/knowledge_cli.py:16-18]. |
| 7 | Registry has 16 entries (2/7/4/3); approval index has 18 (2/7/5/4); only the 2026.7 HWP pair is approved; the 2026-09-01 HWP pair appears only in the index | **confirmed** | Recounted from both files, including the partial-field counts. The deploy copies are byte-identical (`cmp`). VERIFIED. |
| 8 | Knowledge eval passes 69/69 in strict mode; golden set passes 50/50 in strict mode | **confirmed** | [LIVE `knowledge_cli.py --db :memory: eval --selector all --strict`] `total 69 passed 69 failed 0`, exit 0. [LIVE golden runner `--strict` with an in-memory DB] 50 `[PASS]`, exit 0, fresh bootstrap `created 12 / published 42`. CI: `repo-validation.yml:39` runs `check_repo.sh`; step 14 runs the golden set non-strict and step 14b runs the knowledge corpus strict [CODE check_repo.sh:531-559]. OBSERVED. |
| 9 | Label provenance is weak; seed cases are auto-approved by a seed actor; 1 of 69 cases has slot dependencies; the guard gets `verified_facts=[]` | **confirmed** | [LIVE kp_verify.py] `approved_by` is `seed:eval_corpus_seed.json` (19 cases) and `seed:paradiso_ai_golden_questions.json` (50 cases). `evaldeps (2, 1)`: only `d2.extension.documents.ko` has dependencies. [CODE evals.py:130, 184-186]. 19 cases (18 ko, 1 en), 96 assertions, 1 tagged `synthetic`. Addition: offline evals run the guard on *deterministic* text only, never on model output. |
| 10 | The enforcement benchmark (schema 2.0.0, 36 cases) is the only corpus with mandatory per-case provenance and has the richest harness | **confirmed (qualified)** | [CODE enforcement_benchmark.py:69-121] The provenance check is structural only: it does not verify that `sourceFile` or `sourceTest` exists. Suites 13/8/8/7; kinds narrative 28, structured 8. Scoring caveat: abstention precision and recall default to 1.0 when the denominator is 0 [CODE :402-403]. A stricter human-label protocol exists but has no records (O1). |
| 11 | Gemma: 14 synthetic placeholder examples; never trained in the repo | **confirmed** | [LIVE ipynb parse] 15 cells, 12 of them code, 0 outputs, every `execution_count` None. `git ls-files` lists 8 files and no results; 3 commits (#359, #399, #402). Nuance: the notebook's default preset is **`Qwen/Qwen3-1.7B`**; the Gemma 4 presets are opt-in and gated [CODE notebook cell 4]. |
| 12 | The eval set is never scored; eval rows lack the fields eval_outputs.py needs; no eval strategy; the build script merges eval into train; the 6-section format is absent in production | **confirmed** | [CODE notebook cells 7, 10, 12, 13; eval_outputs.py:4-10; build_colab_dataset.py:23-26, 79-83]. The notebook's own default ("Option A") loads the sample files directly. The leak therefore happens only through the build script's defaults or its docstring example; the README's real-data command (`--input <your>.jsonl`) does not merge. [LIVE `git grep` for 3 of the section headers outside experiments/] no hits. |
| 13 | The required test suites and the dataset validator pass | **corrected (environment)** | Platform tests: 62 passed + 19 subtests, reproduced [TEST (ran: pass)]. Deploy-context test: **failed in the verifier's run** with `shutil.Error … [Errno 28] No space left on device` while copying the backend tree [TEST (ran: fail, environmental)]. The original "1 passed" could not be reproduced and stays UNVERIFIED by the verifier; the failure says nothing about the code. Validator: `Total errors: 0`, exit 0, same statistics as the notes [LIVE python3 -I, Python 3.14.7]. |
| 14 | The owner branch approves 2026.9, re-seeds to the 2026-09-18 PDF, adds supersede-and-retire logic and moves the eval cases to 2026.9; merging it resolves KP-1 | **corrected (minor)** | [LIVE `git show` of the branch approval index] `visa_manual_2026_09_01_hwp`/`_pdf` and `stay_manual_2026_09_18_pdf`/`_hwp` are approved (2026-10-16). **`stay_manual_2026_09_01_hwp` is `superseded`, not approved.** Two new `*_md` entries are `needs_review`. The branch is 7 commits ahead. The seed notes say the lists were re-checked on 2026-10-16 word for word (D-4 now pp. 90-92). `_only_legacy_published` and `_retire_dropped_legacy_facts` are added. "Resolves KP-1" is INFERRED: the branch was not run. The re-seed still publishes under the `legacy_import` actor, so the 2026.9 re-verification is recorded in a git-reviewed JSON note, not as a Studio review. |
| 15 | SQLite on a repo path, silent in-memory fallback, no volume in railway.json, production state unknown | **corrected (minor)** | [CODE store.py:41, 62-90; runtime.py:359-374; backend/railway.json]. "Silent" is too strong: failures are logged (`knowledge_store_open_failed`, `knowledge_platform_init_failed`) and the Studio overview shows `durable=false`. The bigger gap: on an ephemeral filesystem the default path **opens fine and reports `durable=True`**, so the flag cannot detect data loss on redeploy (INFERRED). Railway volumes are normally configured outside `railway.json`. An edited 0001 migration raises `RuntimeError` [CODE store.py:124-126], which also triggers the in-memory fallback. |

### Omissions against the brief

* **O1 (filled): the enforcement outcome ground-truth protocol was not inventoried.**
  - Code: `backend/services/enforcement_outcome_intake.py` (502 LOC), `enforcement_prediction_freeze.py` (447),
    `enforcement_outcome_evaluation.py` (316) and `scripts/evaluate_enforcement_v3_preregistered.py` (126).
  - Schemas: `backend/data/enforcement/{outcome_intake,outcome_ground_truth,blind_case_set,prediction_freeze}.schema.json`.
  - Review stages run `STAGED → SOURCE_VERIFIED → INDEPENDENTLY_REVIEWED | REJECTED`, with rejection reasons that
    include `PREDICTION_DERIVED` and `REVIEW_CONFLICT`.
  - Each record needs a `reviewerRole` (enum) and `independentFromPrediction`.
  - Provenance must be an official, court or verified administrative record; `SYNTHETIC`, `MODEL_GENERATED` and
    `LLM_GENERATED` sources are forbidden.
  - A blind case set carries fact digests. A prediction freeze records the engine and prompt versions.
  - Empty data returns `NOT_EVALUABLE`.
  - `outcome_ground_truth.template.json` has 0 records. `enforcement_evaluation_plan.py` imports the freeze module
    [CODE :17-22], so the "plan" in §3 is one stage of this pipeline.

  [CODE enforcement_outcome_intake.py:1-40; enforcement_prediction_freeze.py:1-25; enforcement_outcome_evaluation.py:1-30]
  [TEST 5 files test_enforcement_{outcome_intake,prediction_freeze,evaluation_plan,outcome_intake_authority_scope,outcome_evaluation}.py (ran: pass, 43 passed + 2 subtests)].
  Effect on the REUSE MAP: this is the strongest existing pattern for a dataset schema with label provenance, for
  verification states, and for a runner that refuses to score without reviewed labels. Reuse the stage,
  provenance, freeze and NOT_EVALUABLE patterns, not the enforcement outcome fields.
* **O2 (filled): an existing live benchmark already targets Gemma 4.** `scripts/benchmark_enforcement_models.py`
  defaults to `google/gemma-4-31b-it:free` and `openai/gpt-oss-120b:free`. It uses synthetic `StructuredCase`
  objects only and never prints completions. `enforcement-model-benchmark.yml` runs it on `workflow_dispatch` or on
  a push to one perf branch, and includes a `--dry-run` job [CODE scripts/benchmark_enforcement_models.py:1-60;
  DOC .github/workflows/enforcement-model-benchmark.yml:1-40]. This is relevant to (d) and (e).
* **O3 (filled): KP-7 is partly mitigated.** The front-end status guidance labels its content "검토 전 원문" and
  shows a disclaimer that the 2026.9 guides have not been reviewed line by line [CODE
  assets/js/status-guidance.js:74, 134, 144]. 697 of 700 entries are `SEPT_2026_ORIGINAL_UNREVIEWED` [LIVE parse].
  The disclosure runs the opposite way to claim 2: the unreviewed layer says it is unreviewed, while knowledge
  answers that cite a superseded edition carry no notice.
* **O4 (filled): where the worktree DB came from.** `backend/var/` was created at 12:34:48, after the worktree
  checkout at 12:26:59 (`stat`). The DB mentioned in §1.3 was therefore produced by a run during this mission.
  KP-8 still stands as a design risk.
* **O5 (could not fill):** whether production has a Railway volume and the required environment variables set;
  whether any Colab run happened outside the repo; the Gemma 4 licence terms (no network use in this pass). The
  raw-SQL single-actor publish walk-through (`verifier/kp_verify5.py`) was written but could not run because of
  `ENOSPC`, so that point stays INFERRED from the trigger bodies.
* **O6 (noted, not audited):** `docs/paradiso_ai_coverage_matrix.md`, the files in `data/schemas/*` other than
  `source_grounding_schema.json`, `scripts/benchmark_enforcement_{v3,runtime}.py` and `benchmark_summary.py`.

### Inline corrections made

The verifier changed these places in the notes:
- §0, bullet 1 (scope of raw-SQL protection) and bullet 4 (the unpopulated ground-truth protocol).
- §0, tests bullet.
- §1.3 (where the DB came from).
- §1.6, freshness row: coverage is still reported as verified.
- §2.2, branch approvals: the stay 2026-09-01 HWP is superseded.
- §6, deploy-context row: the verifier's rerun failed with ENOSPC.
- KP-4: the `durable` flag cannot detect an ephemeral filesystem.
- KP-7: the UI discloses the unreviewed state.
