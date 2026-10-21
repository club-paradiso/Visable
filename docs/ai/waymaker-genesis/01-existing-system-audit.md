# 01 — Existing system audit

Status: **COMPLETED** for the audit of origin/main `0713370` (2026-10-19) and its
re-baseline on `fc896c2` (2026-10-20). Each row carries its own evidence status. This
document changes no code.

[research-notes/law-stack-fixes.md](research-notes/law-stack-fixes.md) appeared while this
document was being written. It records eight law-stack fixes, F1–F8, made in this PR's
worktree. They are uncommitted (the orchestrator commits) and VERIFIED offline only. The
register rows those fixes cover read **FIXED IN THIS PR**: ESA-08, -09a, -10a, -32a, -34a
and -35a. Every other row reads **OPEN**. §1–§8 describe main (`fc896c2`), not the fixed
worktree. §4.1 lists what the fixes change.

Mission 001 "Waymaker Genesis". This is the mission's required existing-system audit. It
synthesizes five verified research notes:

| Note | Scope |
|---|---|
| [research-notes/law-stack.md](research-notes/law-stack.md) | Official law API integration, the 18 questions, failure taxonomy, fan-out, secrets |
| [research-notes/ai-lifecycle.md](research-notes/ai-lifecycle.md) | Runtime topology, request lifecycle, model configuration, guards, exposure |
| [research-notes/knowledge-platform.md](research-notes/knowledge-platform.md) | Knowledge Platform, registries, eval corpora, fine-tune scaffold |
| [research-notes/sources-monitoring.md](research-notes/sources-monitoring.md) | Source documents, extraction, change monitoring, CI |
| [research-notes/status-classifier.md](research-notes/status-classifier.md) | Deterministic status, subcode and procedure classification |

[research-notes/law-stack-fixes.md](research-notes/law-stack-fixes.md) is used only for the
fix status of register rows and for §4.1.

It also uses three cross-references:

- [research-notes/law-identity.md](research-notes/law-identity.md) §5–§6: stored law identities and the 시행규칙 제73조 defect.
- [research-notes/training-distill.md](research-notes/training-distill.md) §0, §1 and §3: serving-channel terms.
- [research-notes/ref-ops-license.md](research-notes/ref-ops-license.md) §2.3 and §3.3: provenance of `law_query_normalizer.py`.

Every note ends with an adversarial "Verification pass". **Where a verifier corrected a
note, this document states the corrected version.**

Conventions:

- **Evidence tags** are kept from the notes: `[CODE path:line]`, `[TEST … (ran: pass/fail)]`, `[DOC …]`, `[LIVE …]`, `[WEB url, accessed 2026-10-19]`.
- **Status words:** VERIFIED (primary evidence checked), OBSERVED (seen live or run), README-ONLY, INFERRED, UNVERIFIED.
- **"Live"** means a request to the production Railway or Vercel deployment, or to law.go.kr or GitHub, on 2026-10-19, as recorded in the notes. **"Offline"** means a local run of repository code with no network.
- **Paths** are repo-relative. Line numbers are at `0713370`. For the law stack and `backend/paradiso_backend.py` they are unchanged at `fc896c2` (§0.2). The uncommitted F1–F8 edits shift the law-stack line numbers in this worktree.

> **Worktree state at the time of writing.** This worktree
> (`research/waymaker-genesis-legal-intelligence`, HEAD `fc896c2`) is a sparse checkout. It
> holds this PR's **uncommitted** law-stack fixes F1–F8:
>
> - edited: `law_tools.py`, `law_grounding.py`, `law_citation_guard.py`, `legal_evidence.py` and one existing test (+464/−45);
> - new: `backend/tests/test_law_stack_genesis_regressions.py` and the fixture `backend/tests/fixtures/law_api_shapes/genesis_law_detail_sample.json`.
>
> The audit describes main, without these edits. They show up only as the FIXED IN THIS PR
> rows in §9 and in §4.1.

---

## 0. Baseline

### 0.1 Audit commit `0713370` (2026-10-19)

| Item | Value | Evidence |
|---|---|---|
| Audited commit | origin/main `0713370673526f57ee035fdcc81e2d97dfb87373` (merge of PR #658) | [LIVE Railway `/health` 03:37Z, 04:19Z, 04:29Z: `build.commit` = that SHA via `RAILWAY_GIT_COMMIT_SHA`] OBSERVED ([ai-lifecycle §0 L1, VL1](research-notes/ai-lifecycle.md); [law-stack verification claim 10](research-notes/law-stack.md)) |
| Worktree | Clean: `git status --short` was empty before and after every audit and verification pass | Each note's Verification pass. VERIFIED |
| Branches | At the last local fetch: 155 remote branches under `origin` (156 refs including the `origin` HEAD alias) and 18 local branches. The owner's `fix/waymaker-qa-2026-10-16` has **no remote ref** (unpushed) | [LIVE `git for-each-ref`, 2026-10-20, no re-fetch] OBSERVED |
| Open PRs | None | Orchestrator check, 2026-10-19 (not re-checked here) |
| CI on main | Green. repo-validation run 38292940589 logged "81 modules (via pytest) PASS 81 KNOWN 0 SKIP 0 NEW 0 FIXED 0". railway-live-smoke run 38292940698 saw production switch from `283983f` to `0713370` about 2 min after the push | [LIVE `gh run view`] OBSERVED ([sources-monitoring §4.3, §3.3 and verification claims 10–11](research-notes/sources-monitoring.md)) |
| Backend suite | 81/81 modules pass | Orchestrator local run, 2026-10-19, plus the CI log above. OBSERVED |
| `scripts/check_repo.sh` | Exit 0. The knowledge eval corpus (step 14b, `--strict`) passes 69/69 | Orchestrator run, 2026-10-19. Independently reproduced: `knowledge_cli.py --db :memory: eval --selector all --strict` gave 69/69 ([knowledge-platform verification claim 8](research-notes/knowledge-platform.md)). OBSERVED |
| Production configuration | Law grounding `enabled`, effective `enabled`, active, credential source `LAW_API_OC`. `client_diagnostics_mode: "open"`. OpenRouter configured. Groq configured, `fallback_allowed: false`. Manual index has 2,626 chunks and **0 direct-evidence chunks** (`needs_review` 1,361, `superseded` 1,265) | [LIVE `/health`, `/api/health/ai`, 2026-10-19] OBSERVED ([law-stack §0 L1–L3](research-notes/law-stack.md); [ai-lifecycle §0](research-notes/ai-lifecycle.md)) |
| Vercel static site | `ai.html` served byte-identical to the worktree file: SHA-256 `fc8ed692…a9338a2`, 238,708 bytes | [LIVE GET 2026-10-19 03:38Z and 04:19Z] OBSERVED ([ai-lifecycle L4 as corrected](research-notes/ai-lifecycle.md)) |

### 0.2 Re-baseline on `fc896c2` (2026-10-20)

Main moved after the audit. `git log 0713370..fc896c2` lists **seven** merges, #659–#665.
The orchestrator's brief names #660–#665. #659 (`210c82e`, "체류서류 647개 상황별 데이터…",
the immigration-checklist data and UI) also landed after `0713370`. In total 285 files
changed, +58,933/−555 [LIVE `git diff --stat`, 2026-10-20] OBSERVED.

| Area | Changed since `0713370`? | Effect on this audit |
|---|---|---|
| Law stack (`law_tools`, `law_grounding`, `citation_verifier`, `law_citation_guard`, `legal_evidence`, `law_cloud_fallback`, `korean_law_client`), `backend/paradiso_backend.py`, `backend/rate_limit.py`, `backend/railway.json`, `backend/Procfile`, `backend/requirements.txt`, `lib/`, `api/` | No | §1–§4 stand as written. VERIFIED (`git diff --stat 0713370 fc896c2 -- <paths>` is empty) |
| Data: `visa_data.json`, `backend/data/visas.json`, `doc_master.json`, both copies of `status-guidance-202609.json`, `data/source_registry.json`, `data/manual_approval_index.json`, `scripts/status_guidance/author_rules.py`, `data/sources/*` (board baselines still `null`), `backend/data/eval`, `backend/data/knowledge` | No | §5, §7 and ESA-01 stand. `data/status-guidance-202609.json:1877` and `author_rules.py:316-318,339` were re-read on `fc896c2`: unchanged. OBSERVED |
| Knowledge Platform | Added: `checklist_api.py`, `checklist_models.py`, `checklist_repository.py`, `migrations/0002_checklist_operations.sql` (R3 Content Operations Studio, #662). `api.py` +2 lines. New `test_checklist_operations.py`. One line in `test_knowledge_platform.py` | **Not audited by the notes.** One planning consequence: migration slot `0002` is now taken, so the additive eval-provenance migration proposed in [knowledge-platform §5](research-notes/knowledge-platform.md) must be `0003` or later. VERIFIED (file listing) |
| JS classifiers | `status-guidance.js`: the `codeRe` subcode regex was rewritten (#664). A word after a space is no longer read as a subcode, and a number followed by a unit is not a subcode. `search-router.js`: new `WORKPLACE_MOVE` and `FIRST_ARRIVAL` phrase fallbacks | Part of §6 changes. Re-checked below |
| CI | `repo-validation.yml` installs the manual-reader dependencies and runs the new `search-first-home` and `manual-reader` specs. `check_repo.sh` gains step [5d/14] (manual reader) and `check_search_suggest.mjs`. New workflow `immigration-checklists-mobile-qa.yml`, so there are now 12 workflows. Tracked e2e specs went from 18 to 22, and backend test modules from 81 to 82 | §8 counts are given as of `0713370` unless stated. VERIFIED (`git ls-tree`, `ls`) |

Orchestrator results on `fc896c2`:

- **CI is green** for Repo Validation and Railway Live Smoke (orchestrator, 2026-10-20).
- **Local sparse-checkout run:** 77 of 82 modules pass. The 5 failures come only from files outside the sparse checkout.
- **The failing modules.** Four are named in the brief this document was written from:
  - `test_ai_shell_source_semantics`, `test_i18n_law_fallback_live_smoke` and `test_i18n_sweep_route_wizard` each fail one documentation test.
  - `test_source_grounding_pipeline` needs the binary manuals.
  - The fifth module is not named in that brief.
- Any other backend failure would be real.

A later run, made by the law-stack fix agent on the fixed worktree, reports
`scripts/run_backend_tests.py` exit 0 with "83 modules: PASS 83". The 83 include the new
regression module. In that run the expected sparse-checkout failures did not occur.
[DOC research-notes/law-stack-fixes.md "Commands run"]. That is the agent's report; it was
not re-run for this document. The two results disagree, and this document does not try to
reconcile them.

Re-checks run for this document on 2026-10-20. All ran offline in this worktree: `.venv-check`
Python 3.11, `env -i`, `WAYMAKER_KNOWLEDGE_DB=:memory:`, Node v24, nothing written into the
repo. The probed functions do not depend on the uncommitted law-stack edits (INFERRED).

| Probe | Result on `fc896c2` | Same as `0713370`? |
|---|---|---|
| `pb._detect_visa_codes(None, None, "F-6 배우자인데 E-9로 변경하고 싶어요")`, `PYTHONHASHSEED` 0–9 | F-6 for seeds 0, 2, 3, 5, 6, 7 and 8; E-9 for seeds 1, 4 and 9 | Yes (ESA-06). OBSERVED |
| `_detect_visa_codes` on `E-7-4 연장` and on `Can I get a 3 month extension?` | `(None, None)` and `('A-3', None)` | Yes. OBSERVED |
| `KnowledgePlatform.create(":memory:").plan("E-7-4 체류기간 연장 서류")` | No payload: E-7 / subcode None / `VERIFIED_WITH_CONDITIONS` / 10 documents. Payload E-7-4: `NO_DIRECT_SOURCE` / 0 documents. `D-4-2K …` without payload: D-4 / `VERIFIED_WITH_CONDITIONS` / 9 documents | Yes (ESA-05). OBSERVED |
| JS `interpret` + `nextStep` + `renderModel`, "Can I get a 3 month extension?" | codes `[A-3]`, `unknownCodes []`, resolved A-3, quick answer `mode=answer`, confidence HIGH, 2 required documents. The render model no longer contains "A-3-MONTH" or "not a code" | **Partly.** The false positive remains. The unknown-token trigger for the warning notice is gone, so the page is probably now silent (INFERRED) (ESA-20) |
| JS, "I am a 2nd year student" | codes `[A-2]`, unknown `[A-2-ND]` | Yes. OBSERVED |
| JS, "change of status from D-10 to E-7" and "체류자격 변경 D-10 E-7" | `transitionFrom` is D-10 and both codes are kept | **No: the token glue is fixed in JS** (`D-10-TO` and `D-10-E` no longer appear). Python `unified_search.py` is unchanged, so its glue is presumably still there (INFERRED) (ESA-46) |
| JS, Vietnamese "D-2 cần gia hạn" | codes `[D-2]` | No: the earlier unknown `D-2-C` is gone. OBSERVED |
| JS, "F-10 비자" | codes `[F-1]`, unknown `[F-1-0]` | Yes. OBSERVED |
| JS, "E-7-4 연장 준비물 알려줘" and "D-2-1 비자 연장하려면…" | resolved, target E-7 (or D-2), `inherited: true`, `displayCode` E-7-4 (or D-2-1) | Yes. OBSERVED |

### 0.3 The owner's branches

**`fix/waymaker-qa-2026-10-16`** is in `~/dev/Paradiso` and has no remote ref. Head `9bf8849`,
7 commits on top of `0713370` and 7 behind `fc896c2` [LIVE `git rev-list`, 2026-10-20]
OBSERVED. It will need a rebase onto `fc896c2` before it can merge (INFERRED). What it
changes, from the notes' `git show`/`git diff` reads:

| Area | Change on the branch | Conclusion it changes | Source |
|---|---|---|---|
| Model policy | The Basic chain replaces `thinkingmachines/inkling:free` with `google/gemma-4-26b-a4b-it:free` (403 `model_access_denied`). `ModelCooldownRegistry` gains a 45 s transient cooldown and half-open probing | §2 model tables if merged | [ai-lifecycle §11](research-notes/ai-lifecycle.md) VERIFIED on branch |
| Manual evidence | New `backend/services/manual_evidence.py`. `/api/ask` reads the FTS index read-only and injects approved 2026.9 excerpts before the question, under a "발췌 사용 규칙" block. Adds 4 `AskResponse` fields (`manual_evidence_used`, `_status`, `_scopes`, `_sources`). `fd6109b` page-maps the 2026.9 Markdown texts into the index; its commit message reports 1,331 + 1,134 direct-evidence chunks | ESA-14 (0 approved chunks). A new evidence package must not collide with these field names | [ai-lifecycle §2.7, §7.2, §11](research-notes/ai-lifecycle.md); [training-distill §0.7 verifier note](research-notes/training-distill.md). Not run, not deployed |
| Approval index | Four editions approved 2026-10-16: `visa_manual_2026_09_01_hwp`/`_pdf` and `stay_manual_2026_09_18_pdf`/`_hwp`. The 2026.7 pair and `stay_manual_2026_09_01_hwp` become `superseded`. Two new `*_md` entries are `needs_review`. The manifest `current` becomes the 2026.9 PDFs | ESA-14 and SRC-04 once pushed | [knowledge-platform §2.2 as corrected](research-notes/knowledge-platform.md); [sources-monitoring §7](research-notes/sources-monitoring.md) VERIFIED on branch |
| Knowledge seed | Legacy seed `source_file` → `docs/source-manuals/2026-09/stay_manual_260918.pdf`. Adds `_only_legacy_published` and `_retire_dropped_legacy_facts`. Seed eval cases switch `SOURCE_MUST_BE` from 2026.6 to 2026.9 (D-4 pp. 90–91 become 90–92). `knowledge/evals.py` gains `_refresh_seed_case`. The re-seed still publishes as the `legacy_import` actor, so the 2026.9 re-verification is recorded in a JSON note, not as a Studio review | ESA-14 ("resolves KP-1" is INFERRED; the branch was not run) | [knowledge-platform verification claim 14](research-notes/knowledge-platform.md) |
| `visa_data.json` | 955 manualRefs relabelled to 2026.9; 313 superseded refs remain. Content edits only: the same 42 codes and 228 subcodes | Shrinks SRC-05 (ESA-40) | [sources-monitoring verification claim 14](research-notes/sources-monitoring.md); [status-classifier §11](research-notes/status-classifier.md) |
| Extraction | `*_md` derived corpora whose parser turns HTML tables into `열이름: 값` rows with a page map (`scripts/build_manual_markdown_corpus.py`). `check_source_manuals.py` gains alternate-file and derived-text pinning that refuses any approval claim on derived texts | Partly addresses EXT-01 (ESA-19), still unapproved | [sources-monitoring §7](research-notes/sources-monitoring.md) |
| `legal_analysis` | New `_COMPLETED_TRANSITION_RE`. For a planned A→B change, `current_status` stays the source. Example Q2: D-10 on the branch, E-7-1 on main | Runner labels for current and target must record the commit measured | [status-classifier §11, verification claim 15](research-notes/status-classifier.md) OBSERVED (branch module run against main) |
| `data/source_registry.json` | 36 lines rewritten; the same single `law_api_placeholder` | None | [law-identity §5](research-notes/law-identity.md) |

**Unchanged on the branch** [notes, VERIFIED]:

- the `context` truncation (ESA-04) and both Python detectors;
- the law stack files, `THIRD_PARTY_NOTICES.md` and `ATTRIBUTIONS.md`;
- `author_rules.py:316-318` (stale pins) and the backend 260731 stay binary;
- the board-monitor baselines;
- CI-01 to CI-04, SUP-01/02 and the undeclared `olefile`.

**`fix/visable-diagnostics-token`** is a second, pushed owner branch: `c69c117`, 2026-10-20,
one commit on top of `fc896c2`, not merged.

- The backend reads `VISABLE_DIAGNOSTICS_TOKEN` first and falls back to `PARADISO_DIAGNOSTICS_TOKEN`.
- The live smoke and smoke scripts accept either name.
- Its commit message states that the behaviour is unchanged until an operator sets a token: with neither name set, `/health` still reports `client_diagnostics_mode: "open"`.

[LIVE `git show c69c117`, 2026-10-20] OBSERVED. This branch does not close ESA-03.

---

## 1. Runtime topology and entry points

Sources: [ai-lifecycle §1, §2.3, §6](research-notes/ai-lifecycle.md),
[law-stack §(a), §(e)](research-notes/law-stack.md),
[sources-monitoring §3.3](research-notes/sources-monitoring.md).

| Component | Where it runs | Entry point | Evidence |
|---|---|---|---|
| Static frontend (`ai.html`, `index.html`, `enforcement.html`, `assets/js`) | Vercel `visable-mu.vercel.app`, no build step. `vercel.json` only sets `github.silent` | `ai.html`: Waymaker chat and navigator. `index.html`: search, Quick Answer, AI panel | [CODE vercel.json:1-6] [LIVE L4] VERIFIED/OBSERVED |
| FastAPI backend | Railway `web-production-14f9a.up.railway.app`, NIXPACKS, Root Directory `backend`, healthcheck `/health` | `uvicorn paradiso_backend:app` | [CODE backend/railway.json:1-14; backend/Procfile:1]. The start command passes no `--workers`. uvicorn 0.30.6 honours `WEB_CONCURRENCY`, which was not read on Railway, so "one worker" is the code default (INFERRED) |
| Browser → backend origin | One literal origin | `window.VisableBackend.origin()` | [CODE assets/js/backend-origin.js:35] VERIFIED |
| Vercel serverless | Same Vercel project, `api/` | `api/waymaker/quick-answer.js`; `api/enforcement/{analyze,extract,confirm,law-probe,openrouter-probe}.js`; `api/local-practice/report.js` | [CODE api/**] VERIFIED. Quick-answer OBSERVED live. The enforcement functions were not probed |
| Knowledge store | SQLite at `WAYMAKER_KNOWLEDGE_DB` or `backend/var/knowledge/…`; in-memory fallback if it cannot be opened | `services/knowledge/runtime.py:get_platform`, warmed in lifespan | [CODE runtime.py:359-374; paradiso_backend.py:503-536] VERIFIED. Production volume UNVERIFIED |
| Legacy | `backend/moonshot_backend_fastapi.py` stub, not served. `docs/AI_PIPELINE_DIAGNOSIS.md` (2026-05) is historical | — | README-ONLY |
| Deploy coupling | A push to `main` reaches Railway about 2 min later. `main` has no branch protection and no rulesets (`/protection` → 404; `/rulesets` and `/rules/branches/main` → `[]`) | — | [LIVE gh api, smoke run 38292940698, 2026-10-19] OBSERVED. Vercel Git deploy on push is INFERRED |

Entry points (Railway unless noted). Rate limits come from `backend/rate_limit.py`, an
in-memory sliding window keyed on the first `X-Forwarded-For` token.

| Endpoint | LLM | Rate limit | Notes | Evidence |
|---|---|---|---|---|
| `POST /api/ask` (buffered; SSE when `stream: true`) | yes | 8/min, 300/day | Callers: `ai.html` `sendAi` (2609), the navigator follow-up (3098-3146) and the `index.html` AI panel (18381). All send `stream: false` or no `stream`, and all send a `context` string that is dropped (ESA-04) | [CODE] VERIFIED |
| `/api/search/unified/ai-overview` (+ `/stream`) | yes | 10/min, 200/day | Default Basic chain; `TaskRole.SEARCH_OVERVIEW` is unused. The stream path calls a single model with no fallback | [CODE paradiso_backend.py:8054, 8230] VERIFIED |
| `/api/legal/research` (+ `/stream`) | yes | 4/min, 60/day | Answer-mode candidates; `legal_synthesis.validate_synthesis` | [CODE 7217, 7242] VERIFIED |
| `/api/nationality-coach` | yes | 6/min, 100/day | The only caller of `ai_runtime.AIRuntime`. Calls Groq whenever `GROQ_API_KEY` is set and OpenRouter fails, with no opt-in. Returns `provider`/`model` publicly | [CODE 7771-7800, 7901-7905] VERIFIED |
| `/api/employment/interpret` | yes | 12/min, 300/day | Default chain; `EMPLOYMENT_INTERPRETER` role unused | [CODE 8580] VERIFIED |
| `/api/enforcement/{extract,analyze,provider-probe}` | yes | 10/8/2 per min | `TaskRole.ENFORCEMENT_STRUCTURED`, 8 s chain budget, deterministic baseline first. Live chain uses non-`:free` ids | [CODE 8426-8440, 8531-8565] [LIVE L2] |
| `GET /api/procedure-packet` | no | none | `procedure_packet_builder` (navigator) | [CODE 5273] VERIFIED |
| `/api/legal/laws/search`, `/api/legal/precedents/{search,detail}` | no | **none** | Public proxies that spend the owner's OC | [CODE 6898-6990] VERIFIED |
| `/api/debug/law-grounding/{selftest,netdiag}` | no | 5/min | 404 unless `PARADISO_ENABLE_DEBUG_ENDPOINTS` is set; `/preflight` is open (booleans only) | [CODE 453-469, 7294-7540] VERIFIED |
| `/health`, `/api/health/ai` | no | none | Provider booleans, model ids, cooldowns, chain budgets, env-var presence map, manual-index composition, tool registry | [LIVE L1/L2] OBSERVED |
| `/api/knowledge/published`; `/api/knowledge/studio/*` (24 operator routes) | no | — | Full export of PUBLISHED facts. Studio uses bearer tokens from `WAYMAKER_OPERATOR_TOKENS` and returns 503 when unset | [CODE services/knowledge/api.py:52-78, 144-146] VERIFIED |
| Vercel `POST /api/waymaker/quick-answer` | yes | **none** | Wording enhancement of a deterministic answer. Returns the model id. GET exposes `modelCandidates` | [CODE lib/waymaker-quick-answer-ai.js] [LIVE L3] |
| Vercel `api/enforcement/*`, `api/enforcement/law-probe.js` | yes / no | none | Separate OpenRouter and law.go.kr clients. `enforcement.html` defaults to the Railway origin | [CODE] VERIFIED. Liveness UNVERIFIED |

---

## 2. AI request lifecycle per runtime

Sources: [ai-lifecycle §2.1–§2.9, §3.4, Verification pass V1–V2](research-notes/ai-lifecycle.md).

### 2.1 Railway `POST /api/ask`, buffered path (default for every shipping caller)

| # | Stage | Code | What happens | Status |
|---|---|---|---|---|
| 1 | Client | `ai.html` `sendAi`, `buildAskContext` (827), `buildVisaDataPayload` (706) | Body: `question, consent, context, lang, answer_mode, diagnostics?, stream:false, visa_data, history, selected_procedure_*`. Client cap 500 chars, 75 s abort (`ai.html:355`) | VERIFIED |
| 2 | Rate limit | `rate_limit("ask", 8/min, 300/day)` | Key = first `X-Forwarded-For` IP (`rate_limit.py:65-87`) | VERIFIED |
| 3 | Validation | `_ask_internal` (5735-5793) | `prompt_too_long` above 4,000. History capped at 24×2,000 and used only by the repeat-abuse classifier (V2 #1). `context` truncated to 8,000 and **never read**. `visa_data` above 300k → 400 | VERIFIED |
| 4 | Safety (pre) | `_evaluate_request_safety` (5494) → `safety_guardrails.classify_request` (399) | Deterministic. Block, escalate or emergency → refusal with no model call. Fails closed | VERIFIED |
| 5 | Status and task | `_detect_visa_codes` (3843), `_detect_task_type` (3891), `_risk_level_for_task` | Payload `visa_code` → `visa_data.detected_code` → `visa_data.code` → regex. Subcodes never come from free text (§6) | VERIFIED |
| 6 | Understanding | `build_law_evidence_pack` → `legal_analysis.extract_immigration_facts`, `classify_legal_issue_types`; `evidence_ontology.plan_evidence_queries`; `answer_quality.classify_answer_quality`; a second pass in `knowledge/understanding.understand` | Facts, issue types, query plan | VERIFIED |
| 7 | Knowledge retrieval | `_select_grounding` (4017) → `KnowledgePlatform.grounding_for`; later `_build_knowledge_plan` (2751) → `plan` | PUBLISHED facts only. Retrieval **runs twice**. `source_verification_status: "verified_locally"` on every fact (`runtime.py:289`) | VERIFIED |
| 8 | Local catalog | `_build_visa_data_context_block` (4161), `_build_procedure_variant_context_block` (4457) | **Client-supplied** `visa_data` fields (240 chars each) and variant docs and notes (180 chars per field, at most 5 docs per group, at most 3 notes) go into the prompt with no server-side check (ESA-13) | VERIFIED |
| 9 | Official law | `law_grounding.build_law_grounding_context` (421) → `law_tools.search_laws`, `_verify_requested_articles` → `get_law_detail`; pack `retrieve_planned_official_sources`; `_maybe_retrieve_legal_evidence` (5345) | Only when the intent qualifies and the mode is audit or enabled. 12 s budget for the statute stage only. **Blocking `urllib` inside the async handler** | VERIFIED |
| 10 | Evidence normalization | `build_law_evidence_pack`; `_reconcile_law_verification_with_evidence` (1039); `enforce_source_confidence_invariants` | On main, statute rows are lost here (ESA-08; fixed in this PR by F1). Fails closed to `law_grounding_used_without_normalized_evidence` | VERIFIED (offline probes through the real app) |
| 11 | Model routing | `resolve_question_answer_mode` (model_policy.py:234) | Fast auto-promotes to Basic on complex, high-risk or source-heavy questions. Pro → Basic, `available: false` | VERIFIED |
| 12 | Prompt | `_build_grounded_prompt` (4079) or `_build_ungrounded_korea_scoped_prompt` (4692), plus pack, legal evidence, directives, citation safety, shape contract | One **system** message (`WAYMAKER_SYSTEM_PROMPT`, 1303). Everything else is one concatenated **user** message. No data-not-instructions framing (ESA-31) | VERIFIED |
| 13 | Inference | `_openrouter_complete_with_candidates` (2853) → `_call_openrouter` (1357) | Cooldown-aware chain, 45 s budget (cap 60), 12 s reserve, 3.5 s minimum slice, free-bucket block, 403 skip once the key is proven. Not `AIRuntime`. The budget starts here, after law retrieval (V2 #2) | VERIFIED |
| 14 | Answer guards | `_confidence_gate_answer_text` → `scrub_internal_metadata` → structured finalize or `_apply_answer_shape_gate` (with the case-citation verifier) → `_apply_law_citation_guard` → `_knowledge_guard` → `post_generation_review` | Soften → scrub → shape → statute notice → Answer Guard (critical ⇒ deterministic fallback) → post-generation safety (⇒ refusal) | VERIFIED |
| 15 | Fallbacks | Groq if `ALLOW_GROQ_FALLBACK`; Ollama if enabled; else `_build_deterministic_fallback_payload` (2526) | The Groq family fallback returns raw text with no confidence gate or scrub (6697-6711). Ollama gets the confidence gate only | VERIFIED |
| 16 | Response | `_public_ask_payload` (5615) unless diagnostics are on | Drops routing, `law_evidence_pack` and `knowledge_plan`; masks vendor names. About 130 fields are still public. With `diagnostics:true` the caller gets the full internal payload, and that opt-in is open live (ESA-03) | VERIFIED; live payload INFERRED |
| 17 | Telemetry | `_log_ask_routing_telemetry` (5631), `_record_knowledge_observation`, `safety_events` | stdout JSON with no prompt, no answer and no law fields | VERIFIED |

`AskResponse` declares **162 fields** (programmatic count by the verifier, VC1). Any new
evidence package must project into these names and must not collide with the branch's
`manual_evidence_*` fields ([ai-lifecycle §7](research-notes/ai-lifecycle.md)).

### 2.2 Comparison across runtimes

| Runtime / path | Orchestrator | Retrieval | Guards that run | Fallback | Public exposure |
|---|---|---|---|---|---|
| `/api/ask` buffered | `_openrouter_complete_with_candidates` | Knowledge ×2, statute stage, pack families, `legal_evidence` | Full chain (§2.1 #14) | Groq / Ollama / deterministic | Public projection; diagnostics open |
| `/api/ask` SSE (no shipping caller) | `_sse_answer_stream` (3294), per-candidate TTFT | Same as buffered | Only `_StreamMetadataScrubber` and post-stream safety. Skips the confidence gate, shape gate, case verifier, statute guard, Answer Guard and structured finalize | Deterministic note | `_public_sse_stream` |
| Unified AI overview | Default Basic chain (stream: `candidates[0]` only) | Manual FTS (`_unified_manual_search`, 8096/8269) | `statute_citation_guard` with `[]` evidence and `evidence_available=False`, so every citation is `unverifiable`. The UI shows `citation_failed` when `unverifiableCount > 0` | none (stream) | — |
| Nationality coach | `AIRuntime` (no chain budget; up to 7 × 60 s worst case, INFERRED) | none | JSON parse only | Groq without opt-in | `provider`, `model`, `modelFallbackUsed` |
| Enforcement (Railway) | Task-role chain, 8 s + 1.5 s grace | Deterministic `enforcement_rules` baseline; precedent bodies via `precedent_sources` (`enforcement_evidence.py:246-248`) | Baseline first; case text framed as untrusted data | — | — |
| Navigator (`/api/procedure-packet`) | none (deterministic) | `visa_data.json` + `structured_requirements` | n/a | n/a | The AI follow-up is an unrelated `/api/ask` run: the packet is never sent and `context` is dropped (ESA-04) |
| Vercel Quick Answer | `callOpenRouter`: sequential, 7 s per model, at most 3 models, `json_object` | Browser-side `status-guidance.js` over `data/status-guidance-202609.json` | `validateEnhancement` rejects numbers, fees, documents and offices not in the input. Facts are checked only against what the client sent (V2 #3) | none | Model id in the POST response; GET lists candidates |
| Vercel enforcement | Own client in `lib/enforcement-grounded-ai.js` (35 s); `confirm.js` makes a further call | Own law.go.kr JS clients | Outside `check_ai_architecture.py`, which scans only `backend/**/*.py`, root `*.html` and `assets/js` | — | — |

Live model chains on 2026-10-19 [LIVE L1/L2/L3] OBSERVED ([ai-lifecycle §3.2](research-notes/ai-lifecycle.md), [training-distill §1](research-notes/training-distill.md)):

- **Basic** equals the code default, `nvidia/nemotron-3-ultra-550b-a55b:free` → `google/gemma-4-31b-it:free` → `nvidia/nemotron-3-super-120b-a12b:free` → `thinkingmachines/inkling:free`.
- **Fast** equals the code default, led by `google/gemma-4-26b-a4b-it:free` and `nvidia/nemotron-3.5-lightning:free`.
- **Verifier** leads with `openai/gpt-oss-120b:free`. That id is absent from the OpenRouter catalog, and no production code calls this role.
- **Enforcement structured** uses the paid ids `openai/gpt-oss-20b`, `google/gemma-4-31b-it` and `openai/gpt-oss-120b`. That an env override causes this is INFERRED.
- **Vercel Quick Answer** uses gemma-4-31b-it:free, gpt-oss-120b:free and llama-3.3-70b-instruct:free. The last two are absent from the catalog, so the chain is effectively one model deep.

"Verified" means five different things in this code:

- a law search hit;
- an article-text match;
- a local human check (`verified_locally`);
- a case-number match;
- an approved manual edition.

[ai-lifecycle §8](research-notes/ai-lifecycle.md) VERIFIED. The cleanest existing vocabulary
is `immigration_tools` ApprovalState / VerificationState / ToolStatus, which already keeps
`retrieval_failed` apart from `no_results` (INFERRED recommendation).

---

## 3. Component inventory and decisions

Decisions come from the notes: [ai-lifecycle §4 D1–D13](research-notes/ai-lifecycle.md),
[law-stack §(c)](research-notes/law-stack.md),
[knowledge-platform §5 and O1](research-notes/knowledge-platform.md),
[status-classifier §9](research-notes/status-classifier.md) and
[sources-monitoring §9](research-notes/sources-monitoring.md).

| Component | Location | Decision | Rationale | Regression risk (what guards it) |
|---|---|---|---|---|
| Law API core: request building, injectable transport, typed `LAW_API_*` errors, parse taxonomy, sanitizer | `backend/services/law_tools.py` (2,491 lines; also holds planning, prompt copy and the evidence pack) | **Extend**, by extracting a small typed client out of `law_tools`, not by building a parallel one | Keep the transport seam, the typed errors and `_sanitize_url`. Fix the lossy `_normalize_candidate` (ESA-08), the monkey patch, the missing cache and budget, and sync-only I/O. This PR's F1–F8 fix defects inside `law_tools` without the extraction | Medium-high: `test_law_tools` (91), `test_law_grounding_scenarios` (51), `test_law_query_normalizer` (51) and more; 505 tests in 17 files |
| Cloud title-scan fallback | `law_cloud_fallback.install_cloud_resilient_search`, monkey-patched in `services/__init__.py:6-10` | **Consolidate** into the client | Invisible at call sites; maps any phrase to core titles (ESA-09b) | Medium: `test_law_cloud_korean_search` (5) |
| Precedent clients | `precedent_sources` (no retry, no cache) and `legal_evidence.LawOpenDataClient` (retry, 24 h cache) | **Consolidate** into one client, one call per request, with the `search` mode chosen deliberately | Precedent is searched twice per request by two clients (ESA-36) | Medium: `test_legal_evidence` (35), `test_law_open_data_precedent_scaffold` (55) |
| Legacy law clients | `korean_law_client.KoreanLawClient`, `public_data_client.PublicDataClient` | **Replace (retire)**; do not build on them | Bearer auth to any configured host; imported only by tests | Low: `test_paradiso_backend.py:1745-1802` |
| Vercel JS law and AI clients | `lib/enforcement-*.js`, `api/enforcement/*`, `lib/waymaker-quick-answer-ai.js` | **Leave untouched** for Waymaker work (D9). The owner decides between retiring them and governing them with shared policy and fixtures | Separate runtime, own model lists, no behaviour tests | Low for Waymaker. `check_enforcement_ui.mjs` makes only static checks |
| Candidate-chain orchestrator | `_openrouter_complete_with_candidates`, the SSE loop, `AIRuntime.complete`, JS clients | **Consolidate** into `ai_runtime` (move the budget, reserve and 403 rules into `AIRuntime`; keep `to_legacy_dict`) | Three Python orchestrators with different budgets | High: `test_openrouter_model_candidates`, enforcement latency and Live Smoke depend on exact metadata keys |
| Error classification | `ai_runtime.classify_provider_error` and wrappers | **Reuse** | Port the 403-after-key-proven rule | Medium: labels reach error cards |
| Cooldown registry | `_MODEL_COOLDOWNS` / `ModelCooldownRegistry` | **Leave** | Shared and sound; Vercel is stateless | Low |
| Model policy | `model_policy.py`; `_resolve_openrouter_candidates` (202); 3 JS `DEFAULT_MODELS` lists | **Consolidate** Railway on `resolve_task_models`. **Replace** the JS lists with a committed JSON policy, or route Vercel AI through Railway | Unused roles; JS lists differ | Medium: overview and employment latency |
| Status-code extraction | 7 Python regexes (`_detect_visa_codes`, `legal_analysis._codes`, `immigration_tools._STATUS_CODE_RE`, `knowledge/guard`, `law_grounding._status_codes`, `law_tools.extract_status_codes`, `answer_shape`) and JS hints | **Consolidate** the backend behind `_detect_visa_codes` plus one subcode parser. **Leave** the JS, but add a parity fixture | Subcode rules are product-critical (ESA-05, ESA-21) | **High**: G-1-5 and `*-T` handling. `test_ai_answer_regression_source_subcode_2026_06`, seed case `e7.extension.e7_4.never_inherits_parent` |
| Procedure / intent detection | `_detect_task_type`, `understand`, `classify_legal_issue_types`, `search-router.composeProcedure` | **Reuse** `_detect_task_type` + `understand` as the single Python contract, and fix its gaps (ESA-45) | `register_detectors` already shares them | Medium |
| Fact extraction | `legal_analysis.extract_immigration_facts` vs `immigration_tools.extract_immigration_facts` | **Consolidate** into one schema | Different truncation bugs (ESA-21) | Medium |
| Document-list sources | Knowledge PUBLISHED facts; `structured_requirements`; `visa_data.json` procedures and variants; `status-guidance-202609.json` | **Replace** the client-supplied `visa_data` prompt path with a server-side lookup by code. PUBLISHED facts become the one answer source | ESA-13, ESA-27 | **High**: protected data files, `test_procedure_packet_builder`, the Fast public contract in Live Smoke |
| Citation guards | `law_citation_guard` (`/api/ask`), `statute_citation_guard` (overview), `_verify_requested_articles`, `citation_verifier` (cases), JS `validateEnhancement` | **Consolidate** on `statute_citation_guard` semantics for `/api/ask`, fed with article-level evidence. That feed does not exist on main. This PR's F2 adds `article_evidence` binding to `law_citation_guard` (ESA-09a) | ESA-09b | High: answers with article numbers will change. `test_statute_citation_guard` (22) |
| Evidence object | `law_evidence_pack` dict, unused `immigration_tools.EvidencePack`, knowledge `RetrievalResult`, packet `sourceLens`, Quick Answer `sources` | **Reuse** the `immigration_tools.EvidenceItem` vocabulary and `RetrievalResult.public()`; project into the existing `AskResponse` fields | One package, not a sixth shape | Medium: `test_knowledge_grounding_is_equivalent_to_the_legacy_file` |
| Answer guards | Confidence gate, scrubbers, `knowledge/guard`, `answer_shape`, post-generation safety | **Reuse**, as one ordered pipeline callable from the buffered, stream and fallback exits | ESA-28 | Medium |
| Retrieval calls | Knowledge `grounding_for` + `plan`; statute stage + pack families; precedents in the pack + `legal_evidence` | **Consolidate** to one retrieval per family per request | Latency; verifier inputs change | Medium |
| Knowledge store, lifecycle, review, conflicts, diff, learning loop | `backend/services/knowledge/` (21 modules, about 5.5k LOC, migration 0001) | **Reuse**. **Extend** with a publish gate on the cited edition's `content_review_state`, separation of duties and a server-side publish reason | Well-guarded design (§5) | `test_knowledge_platform` (62 + 19 subtests); migration checksum immutability (`store.py:124-126`) |
| Eval corpora and runner | `EvalService` (19 seed + 50 golden), golden runner, enforcement `run_benchmark` | **Extend**: add label-provenance fields (who, which edition and page), `is_synthetic`, split, a live mode | ESA-23 | CI step 14b must stay strict and offline. Seed cases pin 2026.6 pages |
| Enforcement ground-truth protocol | `enforcement_outcome_intake.py`, `enforcement_prediction_freeze.py`, `enforcement_outcome_evaluation.py` and their schemas | **Reuse the pattern** (stages, provenance rules, freeze, `NOT_EVALUABLE`), not the enforcement fields | Strongest existing provenance discipline; 0 records | 5 test files, 43 passed + 2 subtests |
| Gemma 4 fine-tune scaffold | `experiments/waymaker-gemma4-finetune/` | **Leave** as scaffolding only. Reuse `validate_dataset.py` and the label-masking cell | 14 synthetic examples, never run (ESA-48) | None (isolated) |
| Manual extraction | `scripts/decrypt_hwp_distribution.py`, `build_current_manual_corpus.py` | **Reuse** (byte-for-byte reproducible). **Extend** with passage-level flags | ESA-19 | `check_source_manuals.py` hash pins |
| Source monitoring | `check_source_updates.py`, `monitor_hikorea_manual_board.py`, `sync_hikorea_manuals.py` | **Extend / fix**: baselines, row-level diff, a law-identity poller | Detection is structurally off (ESA-17, ESA-12) | `test_monitor_hikorea_manual_board` |
| Statute name normalizer | `backend/services/law_query_normalizer.py` | **Leave untouched pending the owner's decision** (ESA-07). In this mission, do not consult the third-party repository | Provenance unresolved | `test_law_query_normalizer` (51) |
| JS status resolver | `assets/js/status-guidance.js`, `search-router.js`, `waymaker-quick-answer.js` | **Reuse** as baseline B2. It is the only stack that reports inheritance explicitly | §6 | `check_status_resolver.mjs` (61), `check_search_router.mjs` (29), `check_waymaker_quick_answer.mjs` (23) |

---

## 4. Official law API integration: the 18 questions

Source: [law-stack §(b), §(d), §(e), §(f) and the Verification pass](research-notes/law-stack.md).
Verifier corrections are already applied below. The notes' offline probes replaced
`law_tools._default_transport` with a fake and blocked sockets. Live traffic was 4 GETs to
the Railway backend (L1–L4) and 1 verifier GET of `/health`.

| # | Question | Answer | Evidence / status |
|---|---|---|---|
| 1 | Which endpoints are implemented? | Only `DRF/lawSearch.do` and `DRF/lawService.do` on `www.law.go.kr`. Railway Python covers targets `law`, `admrul`, `lstrm`, `prec` and `decc` (an env default, labelled unconfirmed). Vercel JS covers `law` and `prec`, plus the 별표 parameters `BD=ON,BT=1,BN=7`. The frontend calls only backend `/api/legal/*` | [CODE law_tools.py:127-129; legal_evidence.py:77-94; lib/enforcement-*.js; assets/js/legal-source-search.js:1593-1595] VERIFIED |
| 2 | Which parameters are used? | `OC, target, type=JSON, query, display`. `display` is 5 by default, 100 in the ranked search, 1 for name→detail and 10 for the `/api/legal/laws/search` proxy. Detail uses `MST` (all digits) or `ID`. **Never sent:** `search` for `target=law` (so law search is a title-substring search), `efYd`, `date`, `ancYd`, `JO`, and `page` (except in the fallback). Python precedent search is a name search; Vercel uses body search (`search=2`) | [CODE law_tools.py:631-634, 753-838, 888-947; paradiso_backend.py:6821; precedent_sources.py:629; legal_evidence.py:877; enforcement-precedent-grounding.js:146] VERIFIED for what is sent; the effect on recall is INFERRED |
| 3 | Which source types are supported? | Wired: statute, decree and rule (all `target=law`; the type is inferred from the name or `법령구분명`), `admrul`, `lstrm`, `prec`, `decc`. Scaffold only: legal interpretation, constitutional decision, intelligent search (targets `None`). `/api/ask` itself queries only `law` and `prec`. The official API offers many more targets (history, effective-version, old/new comparison) that Visable does not use | [CODE law_tools.py:386-391, 1213-1234; precedent_sources.py:64-69] VERIFIED; offline probe p17. The wider API capability is README-ONLY in the note; see [04](04-official-api-capability-matrix.md) |
| 4 | How are names and identifiers normalized? | Three regimes. (i) The `/api/ask` planner uses fixed anchors per intent plus names from citations; a cited name must match the result exactly (whitespace-insensitive); **no aliases**, so "출입국법 제18조" is not resolved. (ii) The research path uses `law_query_normalizer` (NFC, dash and space folding, `§`→`제`, typo map, a 22-entry alias table, loose-match guard, ranking). (iii) The cloud fallback compacts to alphanumerics and seeds 10 core names. `법령ID→law_id`, `법령일련번호/MST→law_serial_no`. The detail fetch sends `MST` whenever a value is all digits, so a zero-padded `법령ID` alone would go out as `MST` (INFERRED edge case). The JS normalizer folds `·` but not `ㆍ` | [CODE law_grounding.py:161-187, 284-334; law_query_normalizer.py:131-148, 176-282, 382-466; law_cloud_fallback.py:28-94; law_tools.py:382-399, 924-927; enforcement-law-grounding.js:99-101] VERIFIED |
| 5 | How are versions identified? | **Not pinned.** MST is captured, but only for whatever version the search returns. The public `grounding_items.source_id` prefers `law_id` (the lineage id) over MST. `version_or_date` holds a single date. The registry entry `law_api_placeholder` reads `version: null`, `status: not_configured`, which is stale against production. There is no content hash and no retrieval record | [CODE evidence_ontology.py:282-293; source_grounding.py:363; data/source_registry.json:203-216] VERIFIED |
| 6 | Are promulgation and effective dates kept apart? | Only at the first normalization step (`공포일자→promulgation_date`, `시행일자→enforcement_date`), and `/api/legal/laws/search` returns both. Afterwards they collapse: the family adapter writes `enforcement_date` into `decision_date` and drops the promulgation date. Vercel falls back to `공포일자`. Article-level `조문시행일자` is never read. `lifecycleStatus` comes back empty | [CODE law_tools.py:406-407, 1119-1128; enforcement-law-grounding.js:116] VERIFIED; [LIVE L4] OBSERVED |
| 7 | Are historical versions supported? | No. Nothing sends `efYd` or uses the history targets. `git grep` for `efYd/lsHistory/eflaw/oldAndNew/lsJoHstInf/ancYd` finds 0 hits. Knowledge facts have `as_of`, but law evidence never enters that store. 시행예정 amendments are not visible either (INFERRED) | [CODE knowledge/retrieval.py:17-19,163,176] VERIFIED |
| 8 | Are 부칙 retrievable? | No. "부칙" appears nowhere in the services or JS law modules, and `_extract_articles` walks only `조문*` keys | [CODE law_tools.py:950-1025] VERIFIED |
| 9 | How are citations parsed? | Four regex families with no shared parser. `citation_verifier._CITATION_PATTERN` is used for questions on `/api/ask`: it drops 항/호, misses names ending in `법률` and does not handle "같은 법". `statute_citation_guard` handles brackets, 항 (①) and 호, plus law-name carry-forward. `law_citation_guard._ARTICLE_RE` matches article tokens with no law name, plus 별표. The research normalizer has its own name pattern | [CODE citation_verifier.py:7-40; statute_citation_guard.py:58-166; law_citation_guard.py:21-44; law_query_normalizer.py:431-437] VERIFIED |
| 10 | Are citations checked against the source text? | Only citations in the **user's question** (`_verify_requested_articles` fetches `lawService`). Article numbers in the model's answer pass a token-presence check in the evidence texts with no binding to a law name. When `law_grounding_verified` is true, the check is skipped entirely (`allowed_verified`). The stronger containment guard runs only in the overview, with empty evidence | [CODE law_grounding.py:308-418; law_citation_guard.py:47-52,100-141; paradiso_backend.py:8165-8166, 8305-8307] VERIFIED |
| 11 | Are article identifiers validated? | Partly. The 6-digit encoding and 가지번호 become an `(article, branch)` tuple. **No `조문여부` filter**, so a heading unit can satisfy "verified". **Only `조문내용`** is captured, so for an article whose rule text sits in 항/호 the snippet is just the title line. 항/호 are dropped from citations. JS `findArticle` ignores 가지번호. The real nesting of 항/호 text was INFERRED from synthetic bodies; this PR's F7 has since confirmed it from a documented API sample (§4.1) | [CODE law_tools.py:953-1025; law_grounding.py:369-373; enforcement-law-grounding.js:145-166] VERIFIED; probes p2/p9 |
| 12 | Can law and manual evidence conflict? How is that handled? | Yes, and **nothing detects it**: there is no conflict logic in the law path, only prompt-text precedence. It matters now. The Act took effect 2026-10-02 (promulgated 2026-08-04, before the 2026-09-18 stay manual). The Decree was promulgated 2026-09-29, after the manual. The Rule took effect 2026-09-15, before it. Whether the manual reflects the Act amendment is unknown | [CODE paradiso_backend.py:6229-6236]; `git grep -i conflict` returns 0; [LIVE L4]. VERIFIED (nuance from verifier claim 9) |
| 13 | Are API failures confused with missing data? | Yes, on specific paths (D1–D12; ESA-10a/10b). Corrected statement: a timed-out cited-law search is reported as `CITED_LAW_NOT_FOUND` / `failed_verification` **whenever no other query returned that law**. The status becomes `attempted_no_results` only if, in addition, no query returned any row. Budget exhaustion and a **successful** lookup both become statute `no_results` / public `temporarily_unavailable`. The all-timeout case is classified correctly (`attempted_failed`) | [CODE law_grounding.py:343-346, 652-655; law_tools.py:2104-2108, 832-869] VERIFIED; verifier probes ls_v3 (cases A/B), p15, p16 |
| 14 | Is there unnecessary fan-out? | Yes. With a fake transport where every precedent search is empty and the page cache is cold: **12** upstream calls for an E-7 workplace-change question (`law` ×6, `gana` ×1, `prec` ×5) and **11** for a question with a citation. These are not a measured production typical. A pro research request makes 22 sequential calls, 12 of them 100-row fallback pages. Precedent is searched by two clients. Five of six planner queries are natural-language phrases sent to a title search. Worst case: `legal_evidence` makes 24 attempts (12 per type, for precedent plus admin appeal) | [CODE legal_evidence.py:1005-1027; law_tools.py:2148-2173] VERIFIED; verifier ls_v4/ls_v5 reproduced exactly |
| 15 | Do secrets leak into logs or URLs? | **Not found.** `_sanitize_url` drops OC and key names; OC-bearing links in bodies are sanitized; the law modules have no logger calls; L4 contained no `OC=`. In transit: a `network` error makes the http↔https swap resend the OC **over plaintext HTTP**, to `*.law.go.kr` only (timeouts do not swap). Inside `legal_evidence` that can mean up to 6 sends (INFERRED). Python does not host-check `LAW_API_BASE_URL`, while an older strategy doc suggests a third-party host. `KoreanLawClient` sends the credential as a Bearer header to any host | [CODE law_tools.py:198-259, 484-490, 625-634; korean_law_client.py:59-63; DOC docs/EXTERNAL_SKILLS_AND_LEGAL_GROUNDING_STRATEGY.md §2.1] VERIFIED |
| 16 | How does review state affect answers? | Knowledge facts: PUBLISHED only (SUPERSEDED for a past `as_of`). Manuals: only `approved` editions can be direct evidence, and production has **0** approved direct chunks. **Law API evidence bypasses review entirely.** Its trust label `citationsTrustworthy = enabled && configured` is a configuration fact, not a per-answer fact | [CODE knowledge/retrieval.py:17-19,107-121; manual_registry.py:20-27; paradiso_backend.py:5140] VERIFIED; [LIVE L2] OBSERVED |
| 17 | Does production actually activate legal grounding? | **Configuration:** yes. **The `/api/legal` proxy reaching law.go.kr:** yes, 3 rows in 0.93 s. **Answer-level statute grounding on `/api/ask`:** the rows are dropped (ESA-08), the status ends at `law_grounding_used_without_normalized_evidence`, and the prompt reads "Law evidence: attempted but unavailable". Supplementary case law (`legal_evidence`) is active. Vercel grounding: UNVERIFIED | [LIVE L1–L4] OBSERVED; the `/api/ask` drop is VERIFIED offline through the real app (TestClient) and **INFERRED for production** (no AI POST was allowed) |
| 18 | Do live smokes validate answer quality? | **For law grounding, only availability and configuration.** The Railway smoke checks `/health` booleans and that `/api/legal/laws/search?q=출입국관리법` returns rows. It never checks `law_grounding_status_detail`, citation verification or answer text against the law. It does check other answer contracts: a D-2 answer from a live model, the exact Fast common labels 신청서/여권/외국인등록증/수수료, no leaks or Markdown, and the 2,000,000 KRW enforcement baseline. Each push sends 3 `/api/ask` POSTs and 1 enforcement POST to production | [DOC .github/workflows/railway-live-smoke.yml:110-135, 203-226, 278-405, 453-458] VERIFIED (corrected by the verifier) |

### 4.1 What this PR's uncommitted fixes change

Source: [research-notes/law-stack-fixes.md](research-notes/law-stack-fixes.md). The fix
agent showed fails-before and passes-after for each fix: 24 tests plus 19 subtests fail on a
pristine HEAD copy, and all 33 tests pass on the fix. Re-run for this document on
2026-10-20, offline with credentials unset:

```
pytest -q -p no:randomly -p no:cacheprovider \
  backend/tests/test_law_stack_genesis_regressions.py \
  backend/tests/test_e7_workplace_change_law_grounding.py \
  backend/tests/test_law_tools.py backend/tests/test_law_grounding.py \
  backend/tests/test_legal_evidence.py
```

Result: **202 passed, 32 subtests passed** [TEST (ran: pass)]. Production behaviour after
deploy is INFERRED.

| Q | Change in the worktree | What still stands |
|---|---|---|
| 10, 17 | **F1:** already-normalized rows now pass through `build_law_evidence_pack` (`_normalize_context_law_row`), so successful lookups reach `law_sources`. **F2:** `guard_answer_citations` no longer allows every article number because of the flag alone. An article token must be bound to a fetched (law, article) pair, or it must appear in the collected evidence texts | `/api/ask` passes no `article_evidence` (`paradiso_backend.py` was off limits). Title-only hits now make `law_grounding_verified` true again, so ai.html shows the "실시간 법령 확인" row. The **streamed** path has no post-hoc guard (ESA-09b). `statute_citation_guard` is still not wired |
| 11 | **F7:** units whose `조문여부` is not `조문` are skipped; nested 항/호/목 text is captured. The real shape was confirmed from the documented Open API sample (`s2_law_detail.json`) | `조문시행일자`, 부칙 and 별표 units are still not read. JS `findArticle` is unchanged |
| 13 | **F3:** a failed cited-law search becomes `error` / `SOURCE_UNAVAILABLE`, and a real `error_type` outranks no-results in the status detail. **F4:** budget exhaustion → `timeout`, unknown errors → `unavailable`. **F5:** the ranked ladder keeps the first infrastructure error | D4, D6, D7, D11 and D12. A detail-fetch failure after a successful search is still `failed_verification`. The exception path of `build_law_grounding_context` has no `error_type` |
| 15 | **F8:** `LAW_API_BASE_URL` is accepted only for `https://www.law.go.kr` or `https://law.go.kr`; anything else falls back to the default and logs `LAW_API_BASE_URL_IGNORED`. The plaintext retry is now limited to law.go.kr and logged | The http↔https swap still resends the OC over HTTP on connection failure (behaviour deliberately unchanged; owner decision). `KoreanLawClient` and the HTTP-first operator scripts are unchanged |
| D8 | **F6:** `legal_evidence` caches parsed successes only | Unbounded dicts; no credential fingerprint in keys |

---

## 5. Knowledge Platform and source registries

Sources: [knowledge-platform §0–§5, §7 and the Verification pass](research-notes/knowledge-platform.md);
[ai-lifecycle §2.6](research-notes/ai-lifecycle.md).

**Design** (VERIFIED from code):

- **Store.** stdlib SQLite with checksum-immutable migrations, `BEGIN IMMEDIATE` transactions and an append-only audit log.
- **Lifecycle.** 9 states: DRAFT, AI_EXTRACTED, HUMAN_REVIEW_REQUIRED, HUMAN_REVIEWED, VERIFIED, PUBLISHED, SUPERSEDED, WITHDRAWN, REJECTED. The transition whitelist is identical in Python and in SQL triggers.
- **Facts.** One immutable row per version. `slot_key` is `variant_key|property|item_key`.
- **Variants.** Each carries an explicit `subcodes_covered` list and `procedure_family IN ('stay','visa')`, which keeps visa and stay scopes separate.
- **Conflicts.** Detected deterministically, slot by slot, in 4 kinds. A conflict blocks publish.
- **Learning loop.** Privacy-minimised: redacted excerpts of at most 200 characters, 90-day expiry, and answers never become facts.

**Corrected trigger scope.** The DB triggers enforce lifecycle structure, not actor identity.
A raw-SQL probe on a PUBLISHED fact showed:

- **Allowed:** UPDATE of a citation's page, excerpt or `source_version_id`; INSERT of an extra citation; UPDATE of `verified_by` and `effective_to`; UPDATE of a version's `content_review_state`.
- **Blocked:** citation DELETE, UPDATE of `value_text`, audit UPDATE or DELETE.

So "never published without a human" holds for the Python API, not for raw SQL [LIVE in-memory
probe kp_verify4.py] OBSERVED.

**What it holds** [LIVE in-memory bootstrap] OBSERVED:

- 42 PUBLISHED facts: 27 `required_document` and 15 `procedural_note`.
- 3 variants, all `extension`: D-2, D-4 (covers D-4-1 and D-4-7) and E-7.
- **All 42 cite `stay_manual_2026_06_23_pdf` (2026.6).** The registry marks that edition `deprecated` and the approval index `superseded`; it was never content-approved.
- The approved 2026.7 stay edition backs zero facts.
- D-2 and E-7 still decide `VERIFIED_WITH_CONDITIONS`. Staleness surfaces only as the reason string `freshness:newer_edition_available`, and `to_grounding` stamps every fact `verified_locally`.

**Runtime gating:**

| Gate | Behaviour | Evidence |
|---|---|---|
| Current queries | PUBLISHED only; a historical `as_of` may return SUPERSEDED | [CODE retrieval.py:163,176] VERIFIED |
| Subcode inheritance in retrieval | A subcode never inherits its parent unless it is listed in `subcodes_covered`. But `understand()` fills in the parent before retrieval when the text names a subcode (ESA-05) | [CODE retrieval.py:120-134; understanding.py:124-131] VERIFIED; OBSERVED on `fc896c2` |
| Coverage decision (`NO_DIRECT_SOURCE`, `NEEDS_CLARIFICATION`, …) | **Advisory only.** No reader of `decision.state` on the answer path. `/api/ask` builds the plan with `build_structured=False`. `guard.check` ignores `coverage_state` | [CODE runtime.py:160,184; guard.py:142,197-200; paradiso_backend.py:2758] VERIFIED |
| Cited edition `content_review_state` | **Not a publish gate.** Ingestion only warns. The end-to-end test publishes against the unapproved 2026.9 edition | [CODE review.py:227-239; ingestion.py:173-174] [TEST test_knowledge_platform.py:279-308 (ran: pass)] VERIFIED |
| Answer Guard | Critical → text withheld and deterministic fallback; high → structured summary dropped | [CODE paradiso_backend.py:2817-2820, 6606-6633] VERIFIED |
| Separation of duties | None. One operator may approve, verify and publish. The publish reason is required only by the Studio UI. The CLI accepts a free-text `--operator` with no token | [CODE repository.py:385-413; models.py:505-507; knowledge-studio.js:299-303] VERIFIED |
| Durability | No volume in `railway.json`. On an ephemeral filesystem the default path opens fine and reports `durable=True`, so the flag cannot detect loss on redeploy. Failures are logged, not silent | [CODE store.py:41, 62-90; runtime.py:359-374] VERIFIED; production volume UNVERIFIED |

**Registries** [CODE files; `python3 -I` parse] VERIFIED:

| File | Content | Findings |
|---|---|---|
| `data/source_registry.json` (16 entries; deploy copy byte-identical) | active 2, deprecated 7, not_configured 4, needs_manual_review 3 | Only the 2026.7 HWP pair is active and approved. The 2026.9 PDFs and HWP are `needs_manual_review` → `staged`. The law API is a single `not_configured` placeholder. Missing entries: `visa_manual_2026_09_01_hwp`, `stay_manual_2026_09_01_hwp`, K-CORE and dongpo. The note "No production code path reads this file" is false, because `bootstrap()` reads it on every start |
| `data/manual_approval_index.json` (18 documents, generated 2026-08-09) | approved 2, superseded 7, needs_review 5, draft 4 | Approval covers body text only, and table warnings remain. "Only 'approved' content may back a direct assertion" is enforced in `manual_registry.py`, not in the knowledge platform |
| `docs/source-manuals/source_manifest.json` | `current` = the 2026-07-31 HWP pair; pending 2026.9 editions are hash-pinned | `SOURCE_MANUALS.md` still says the 2026.6 PDFs are current (doc drift) |

**Eval and benchmark corpora** (from [knowledge-platform §3](research-notes/knowledge-platform.md)
and [status-classifier §8](research-notes/status-classifier.md)):

| Corpus | Count | In CI | Label provenance |
|---|---|---|---|
| `backend/data/knowledge/eval_corpus_seed.json` | 19 cases (18 ko, 1 en), 96 assertions | Yes, strict (step 14b) | Hand or agent authored. Expectations derive from the same 2026.6 legacy file that seeds the facts. Auto-approved by `seed:eval_corpus_seed.json`. 1 case tagged `synthetic` |
| `backend/data/eval/paradiso_ai_golden_questions.json` | 50 (30 ko, 20 en) | Yes (step 14 non-strict, plus 14b) | "Artificial examples". The codes are passed as the **payload**. Parent detection from text is tested in 3 of 50, subcode detection in 0 of 50. A stale label (`gq_activity_permission_ko_01`) is hidden by the `_NULL_TASK_EXPECTED` allow-list |
| Scenario audit cases | 17 | Via the backend suite | Hand authored |
| Enforcement benchmark | 36 + 10 + 13 | pytest | Per-case provenance is structural only. Abstention precision and recall default to 1.0 when the denominator is 0 |
| Employment analyzer cases | 583 | Yes | Generated |
| Gemma fine-tune JSONL | 6 + 8 | No | Synthetic, AI-generated |

Only 1 of 69 knowledge cases declares `depends_on_slots`. The eval runner calls the Answer
Guard with `verified_facts=[]`, and only on deterministic text. `eval_runs.mode` allows
`live`, but only `offline` exists. None of these corpora records independent human
labelling. Treat them as regression fixtures, not gold (INFERRED; ESA-23).

**Status guidance outside the lifecycle.** `data/status-guidance-202609.json` powers the
front-end Quick Answer: 697 of 700 entries are `SEPT_2026_ORIGINAL_UNREVIEWED`. The UI labels
it 검토 전 원문 and shows a disclaimer [CODE assets/js/status-guidance.js:74, 134, 144]. The
knowledge adapter also reads it (`adapters.py:56`). This is the file that carries the 제73조
defect (ESA-01).

---

## 6. Deterministic classifiers

Source: [status-classifier §1–§10 and the Verification pass](research-notes/status-classifier.md);
re-checks on `fc896c2` in §0.2.

**There are two stacks, and they disagree:**

- **Python** serves `/api/ask` and `/api/search/unified`. Its parts are `_detect_visa_codes`, `_detect_task_type` (11 task types), `understand()`, `legal_analysis`, `immigration_tools` and `unified_search`. It never reads a subcode from free text, by design.
- **JS** serves the search page and Quick Answer. Its parts are `VisableStatusGuidance.interpret` / `nextStep` and `VisableSearchRouter.route`. It reads exact subcodes, including `*-T`, `-2K`, `-4R` and `-7S`, uses a 16-procedure taxonomy that includes visa issuance, and reports inheritance explicitly with `inherited` and `displayCode`.

**Behaviour per component** (OBSERVED offline at `0713370`; the last column is the 2026-10-20 re-check):

| Behaviour | Python | JS | On `fc896c2` |
|---|---|---|---|
| Free-text subcode ("D-2-1 연장") | `_detect_visa_codes` → `(None, None)`; `understand()` fills in **D-2** silently; `plan()` serves the parent checklist as `VERIFIED_WITH_CONDITIONS` | D-2-1 exact, resolved, `inherited`, `displayCode` D-2-1 | Unchanged (Python plan and JS re-run) |
| `*-T` ("D-10-T 연장") | → D-10 | D-10-T exact | Python unchanged (code identical) |
| Letter suffixes | `legal_analysis`: D-4-2K → **D-4-2** (another real subcode), F-2-7S → F-2-7, `d21` → D-21. `immigration_tools`: → parent | Kept | Python code identical |
| Hash seed | Same-length codes iterate over a `frozenset`, so the winner depends on `PYTHONHASHSEED`; no tracked file pins it | n/a | **Reproduced**: 7 seeds F-6, 3 seeds E-9 |
| English false positives | "a 3 month" → A-3 (`_detect_visa_codes`, `legal_analysis`, `unified_search`); "a 2nd" → A-2 (`legal_analysis`, `unified_search`). `immigration_tools` is immune (needs a hyphen) | A-3 → definite A-3 extension answer, HIGH; A-2 | A-3 persists, and the warning trigger is gone (§0.2); A-2 persists |
| Token glue | `unified_search`: "D-10 to" → `D-10-TO`; "D-10 E-7" → `D-10-E`, dropping E-7; `\b` misses before Hangul ("D-2-1비자" → D-2 silently) | Same glue; `transitionFrom` null for "from X to Y" | **JS fixed by #664**; Python presumably unchanged (INFERRED) |
| Procedures | No visa issuance, CVI or re-entry branch; misses "A에서 B로 변경", "change from … to" and "사업장 변경" | All recognised | Python code identical |
| Over-tagging | Q3 tagged `registration_deadline` with no deadline asked; Q4 adds a spurious `extension` | — | Not re-run |
| Multilingual | zh/vi/ja/ru keep only the code, lose procedure and intent; ja → `zh`, vi/ru → `en` | `procedure=null` | Vietnamese no longer glued (D-2) |
| Unknown code | `F-10` accepted by `_VALID_MAIN_CODES` | "F-10 비자" → F-1 / unknown F-1-0 | Unchanged |
| Deliberate fallback | `employment_nl.sanitize_visa_status` maps an unknown subcode to its parent and records it in `rejected` | `fromUnknown` flagged | — |

**Inventory** [LIVE parse] OBSERVED:

- `visa_data.json` and `backend/data/visas.json` are byte-identical (sha256 `2f86aee1…`).
- There are 42 top-level records: 37 real two-segment statuses plus `D-4-1`, `D-4-2K`, `K-STAR`, `REGION-S` and `YOUTH-STAY`. The 39 categories that CLAUDE.md mentions match no count computed here (INFERRED).
- There are 228 subcodes. 30 records carry a `subCodes` key; 29 lists are non-empty.
- The four `*-T` variants (D-10-T, E-7-T, F-2-T, F-5-T) exist only as nested subcodes.
- Some subcodes sit under foreign parents, e.g. `C-3 → C-2` and the programs `K-STAR` and `REGION-S`.
- 7 subcodes are placed twice.
- `data/status-coverage-202609.json` and the JS bundle each hold 269 records: 37 status, 221 substatus, 5 scenario and 6 program.

**Procedure crosswalk.** The canonical procedure list (`knowledge.models.ALL_PROCEDURES`), the
backend `task_type`, the 16 JS procedure ids, the `visa_data` procedure keys and the
`legal_analysis` issues do not map 1:1 [status-classifier §7].

- Mapping `TASK_TYPE_TO_PROCEDURE` loses meaning in two places: `overstay_deadline_risk` becomes `extension`, and `academic_status_change` becomes `reporting_duty`.
- The knowledge layer keeps stay and visa procedures in separate families.

**Policy contradiction.** For E-7-4 extension, `check_status_resolver.mjs:57` expects JS to
inherit the E-7 common rule, and the Python seed case `e7.extension.e7_4.never_inherits_parent`
expects `NO_DIRECT_SOURCE`. Both pass today. Which policy is correct needs a human decision
against the 2026.9 stay manual (ESA-22).

**Baselines for the benchmark.** Report two baselines side by side:

- **B1-python**: `_detect_visa_codes` + `_detect_task_type` + `understand()`, with `PYTHONHASHSEED` pinned.
- **B2-js**: `interpret` → `nextStep`.

Score status, subcode and procedure separately through the crosswalk. Never count the
parent fallback as a subcode hit. Treat the golden `visa_code` labels as payload. The exact
recipes are in [status-classifier §9](research-notes/status-classifier.md).

---

## 7. Sources, extraction and change monitoring

Sources: [sources-monitoring §1–§3, §5, §7 and the Verification pass](research-notes/sources-monitoring.md);
[law-identity §5–§6](research-notes/law-identity.md).

**Manual editions** (MoJ 출입국·외국인정책본부), condensed:

| Edition | Format | Extraction | Status on main |
|---|---|---|---|
| 2026.7 visa and stay (2026-07-31) | 배포용 HWP | `decrypt_hwp_distribution.py` (ViewText AES → `PARA_TEXT`) | **approved** 2026-08-09; manifest `current` |
| 2026.7 stay, **second binary** `backend/data/sources/manuals/260731_stay_manual.hwp` (sha `bde0e845…`) | 배포용 HWP | pyhwp | Not registered (documented only in an audit). It differs from the approved text in exactly one line, the E-7-4 시행일자: '24. 11. 27. against the approved '26. 7. 9. It backs 10 `visa_data.json` refs (ESA-18) |
| 2026.9 visa (09-01) and stay (09-01, 09-18) | 배포용 HWP + PDF (519 / 810 pages) | Decrypt script; PyMuPDF corpus | `needs_review` (approved only on the owner's branch) |
| 2026.6, 2026.5 | PDF exports, HWPX | pdf text layer; HWPX sections `UNREADABLE` (encrypted) | superseded |
| K-CORE (E-7-M) 2026.6; dongpo 2026.2 | HWP; 2-up PDF | olefile; pypdf | Neither is in `source_registry.json`. K-CORE is also absent from the approval index (manifest `special_program_manuals`: current). Dongpo defaults to `needs_review`, the most restrictive state |

- **Reproduced byte-for-byte** with the repo's own extractor: visa 07-31, stay 07-31 and stay 09-18 HWP texts match their committed hashes, with U+FFFD = 0 [LIVE local run, verifier re-run] VERIFIED.
- The approved edition (2026.7) is about 7 weeks behind the received 2026.9 edition. The 2026.9 deltas (e.g. the E-7-4 threshold change cited in the repo's own change review) exist only as 검토 전 material on main [DOC audits/manual-refresh-260901/README.md] VERIFIED that the doc says so. The legal content itself was not checked.

**Extraction fidelity** (approved HWP path):

- **Approved text is a faithful linear text layer.** Table structure, merged and empty cells, embedded images and footnote linkage are flattened. Example: the 심사수수료 table becomes a run of cell lines. Another: the 붙임13 photo specification is followed directly by the next chapter.
- **Glyphs.** Hancom private-use glyphs pass through unmapped: 281, 436 and 455 PUA characters in the three texts. Circled list numbers appear as U+F02B1…
- **Whitespace.** Tab and NBSP controls are dropped without a space.
- **PDF pages.** In the 2026.9 corpus, `has_images` is recorded per page but nothing reads it. Near-empty pages pass silently, and there is no OCR anywhere.
- **Warnings stay at document level.** `table_extraction_warnings` reaches only `manual_registry.py` and a summary endpoint. **No passage-level flag reaches retrieval or answers** [CODE decrypt_hwp_distribution.py:51-53, 226-238, 268-270; manual_search.py:214-226] VERIFIED.

**Law identities and pins** ([law-identity §5–§6](research-notes/law-identity.md), live
law.go.kr history pages, 2026-10-19):

| Stored | Current | Where | Status |
|---|---|---|---|
| 출입국관리법 `mst 272921, effective 2026-01-23` | 290729 (법률 제21857호, 공포 2026-08-04, 시행 2026-10-02) | `author_rules.py:316` → `data/status-guidance-202609.json:379,395,411`, `guidance-rules-202609.json` and the knowledge_deploy copy | Stale identity. The cited 제35조, 제36조 and 제87조 are textually unchanged (marker-based check) |
| 시행령 `mst 289697, 2026-09-15` | 290501 (대통령령 제36728호, 2026-09-29 / 2026-10-02) | `author_rules.py:317`; 4 article refs | Stale identity. The cited 제40/42/44/45조 are unchanged |
| 시행규칙 `mst 289833, 2026-09-15` | Current, **but the same MST carries a 2027-09-16 date for 제73조** (제01125호 부칙 제1조 단서) | `author_rules.py:318,339`; `status-guidance-202609.json:560-567, 1877` | **The 제73조 quote is the 2027 text, labelled current (ESA-01).** `data/form_schemas.json` records the pending date on eight annex templates, but not on 제73조 |
| 국적법 시행령 lsiSeq 243829 (marked `official_legal_text_identity_verified`, checked 2026-06-28) | 246165 (since 2022-12-20) | `data/nationality_sources.json:371,380-381`; `nationality_service_sources.json:45` | Was already stale when "verified" |
| 국적법 시행규칙 lsiSeq 262177 | 291055 (법무부령 제1161호, 2026-10-02) | `nationality_sources.json:398`; `nationality_service_sources.json:61` | Stale; form-level changes UNVERIFIED |
| `data/document_help.json:31` 시행규칙 lsiSeq 266161 | three versions newer | — | Stale |
| 외국인고용법 trio | Current 276857. Pending 286817 takes effect 2026-12-10, with 제22조의2 and 제25조 on 2027-06-10 | Absent from `docs/source-laws` | Coverage gap; relevant to E-9 workplace-change content |
| F-4 취업활동 제한범위 고시 "제2026-35호" (in the manual's own text) | law.go.kr: 제2026-65호, same date; no 2026-35 anywhere in its history | 31 corpus and extract files | Mismatch; needs human check against 관보 or the MoJ notice |

**Change detection today:**

| Mechanism | What it actually does | Observation |
|---|---|---|
| `check_source_updates.py` (CI step 5, report-only) | sha256 of **committed** files against `last_known_hash`. Law and notice entries return `skipped: not_configured`. The catalog's real allowlisted fetcher has 0 eligible records | 16 total, 5 unchanged, 11 skipped. Detects tampering with the repo, not upstream change. OBSERVED |
| `hikorea-manual-board-monitor.yml` (weekly) | Whole-page hash of the 자료실 and 공지 lists | **Both baselines are `null`**, so every run returns `baseline_unset` with conclusion success (runs on 09-28, 10-05 and 10-12). Still `null` on `fc896c2`. OBSERVED |
| `hikorea-manual-sync.yml` (1st and 15th) | sha of a supplied HWP | `download_url: null`, so it is a no-op. Cron runs never pass `--allow-network`, so setting a URL alone would not fetch. OBSERVED |
| `diff_manual_versions.py`, `diff_manual_paragraph_editions.py` | Structured edition diffs with affected codes | Good, but manual-only. The paragraph tool's test is not in CI |
| Knowledge `evaluate_source_refresh` + `diff.py` | Edition-level `refresh_due` | Never fires while the newer edition is unapproved |
| Runtime law lifecycle (`classify_law_lifecycle`) | Query-time 시행예정 and repealed. **연혁 rows are labelled `verified`**, the same as current rows | Nothing persists law identities or compares them over time |

- **Auto-publish.** No workflow edits production data or deploys. But `main` is unprotected and a merge deploys, so the human-in-the-loop guarantee is procedural (ESA-16).
- **Stale citations.** 1,268 of 1,292 `visa_data.json` `sourceFile` refs point at superseded 2026.6 and 2026.5 files. CI step 3 **requires** `manualVersion == "2026.5"` (`check_repo.sh:121-122`, unchanged on `fc896c2`) (ESA-40).

---

## 8. CI and tests

Sources: [sources-monitoring §4 and verification claims 11–13](research-notes/sources-monitoring.md),
[ai-lifecycle §9](research-notes/ai-lifecycle.md), [law-stack §(g)](research-notes/law-stack.md),
[knowledge-platform §6](research-notes/knowledge-platform.md),
[status-classifier §8](research-notes/status-classifier.md); §0 for the baseline runs.

**Workflows** (11 at `0713370`, last 3 runs per `gh run list` on 2026-10-19; `fc896c2` adds
`immigration-checklists-mobile-qa.yml`):

| Workflow | Trigger | What it proves | Notes |
|---|---|---|---|
| repo-validation | PR; push to main/feat/fix/test | `check_repo.sh` (Py 3.11, PyMuPDF 1.28.2), the full backend suite via `run_backend_tests.py`, golden and knowledge evals, mobile and WebKit QA, Playwright specs | Green. `KNOWN_FAILING` is empty. A 0-test module counts as failure |
| railway-live-smoke | push to main | Deploy identity, provider and law configuration, law-search rows, D-2 answer contract, enforcement baseline | A *reported but different* commit fails after about 5 min with a misleading "no usable law rows" message. Spends production quota and the OC on every push |
| hikorea-manual-board-monitor / -manual-sync | cron | See §7 | Structurally no-op behind green |
| short-stay-freshness | monthly | Date-based staleness issue | Works |
| manual-code-coverage | data paths | `build_visa_data.py --check`, coverage | Unpinned runner `python3` |
| enforcement-model-benchmark / -runtime-benchmark, converter benchmark, source-monitoring, source-monitor-smoke | dispatch | Benchmarks and monitors | The runtime benchmark POSTs to production. Unpinned `cargo`/`go`/`npm @latest` installs |

**What CI does not cover:**

- 6 script tests never run (they pass locally: 50 passed + 3 subtests).
- About 25 check scripts are never invoked. One of them, `check_260617_subcode_inventory_coverage.py`, **fails on main**: 13 F-4 subcodes (F-4-11…21, F-4-25, F-4-30) lack source, manualRefs and review flags, and F-2-6 is shown active although abolished. Its committed report still says `passes: true`, and the "check" script writes into a tracked file.
- The DOM tests self-skip because the validate job never installs jsdom. There is no lockfile.
- 8 of the 18 e2e specs at `0713370` were not in CI. `fc896c2` adds 4 specs:
  - `search-first-home` and `manual-reader` run in repo-validation;
  - `immigration-checklists` runs in the new mobile-QA workflow;
  - `content-studio` is referenced by no workflow.

  The full count was not redone.
- No job decrypts a real committed HWP, and `olefile` is in no requirements file (4 scripts import it).
- Python is unpinned in several jobs (runner `python3`) and in production (NIXPACKS without `runtime.txt` or `.python-version`). Node is unpinned for `check_repo.sh`, and there is no `.nvmrc`.
- starlette 0.38.6 is in range for CVE-2024-47874 and CVE-2025-54121. Exposure is low (no multipart handling) [WEB https://api.osv.dev/v1/vulns/GHSA-f96h-pmfr-66vw, accessed 2026-10-19].

**Test runs recorded by the notes** (all offline, credentials unset):

| Scope | Command (abbreviated) | Result | Source |
|---|---|---|---|
| 17 law-stack files | `pytest -q -p no:randomly <17 files>` | **505 passed**, 61 subtests (re-run by the verifier: same) | law-stack §(g) |
| 7 adjacent grounding files | pytest | 146 passed, 54 subtests | law-stack §(g) |
| `test_waymaker_production_truth_audit.py` | pytest | 13 passed | law-stack §(g) |
| 12 AI-lifecycle files (+ `test_legal_evidence`) | pytest | 375 passed + 126 subtests (410 with legal_evidence) | ai-lifecycle T1/VT1 |
| `scripts/check_ai_architecture.py` | python -B | pass | ai-lifecycle VT2 |
| `test_knowledge_platform.py` | pytest | 62 passed + 19 subtests | knowledge-platform §6 |
| `test_knowledge_deploy_context.py` | pytest | 1 passed originally. The verifier's re-run **failed with ENOSPC** (environmental) | knowledge-platform §6 |
| Knowledge eval corpus | `knowledge_cli.py --db :memory: eval --selector all --strict` | **69/69** | knowledge-platform §6 |
| Golden questions | `evaluate_paradiso_ai_golden_questions.py --strict` | 50/50 | knowledge-platform §6 |
| 7 classifier pytest files | pytest | 292 passed + 23 subtests | status-classifier §8 |
| JS classifier checks | node | search_router 29, status_resolver 61, navigator 404, quick_answer 23, coverage manifest 475 | status-classifier §8 |
| Script tests not in CI | pytest (6 modules) | 50 passed + 3 subtests | sources-monitoring §4.4 |
| `check_260617_subcode_inventory_coverage.py` | via import, write redirected | **FAIL** (rc 1) | sources-monitoring claim 12 |
| `test_law_tools` + `test_law_query_normalizer` | pytest | 142 passed | ref-ops-license T1 |
| `node scripts/check_enforcement_ui.mjs` | node | 62 static checks pass | law-stack §(g) |
| This PR: `test_law_stack_genesis_regressions.py` on a pristine HEAD copy vs the fixed worktree | pytest | HEAD: exit 1 (24 tests + 19 subtests fail, 6 controls pass). Fix: 33 passed + 19 subtests. The 17 law files: 505 passed on both | law-stack-fixes.md (fix agent's runs) |
| This PR, re-run for this document (2026-10-20) | pytest, 5 files (§4.1) | 202 passed, 32 subtests | §4.1 |

**Coverage gaps that matter for the law stack:**

- The law fixtures are synthetic: no `조문여부`, no 항/호, no OC in links.
- **On main, no test sends a successful real-shape `law_context` through `build_law_evidence_pack`.** That is why ESA-08 passed CI. This PR adds one (`F1EvidencePackTests`, using the real-shape fixture `genesis_law_detail_sample.json`).
- The JS law grounding has static string checks only.
- The fixture IDs `001386`, `001387` and `267581` are synthetic (the real 법령IDs are 001707 and 005256) and must never be promoted into data [law-identity §5].

---

## 9. Consolidated risk register

The register dedupes all five notes' registers, plus the cross-referenced items.
`Sources` lists the note IDs:

- `LS-` [law-stack](research-notes/law-stack.md)
- `AL-` [ai-lifecycle](research-notes/ai-lifecycle.md)
- `KP-` [knowledge-platform](research-notes/knowledge-platform.md)
- `SRC-`, `EXT-`, `CI-`, `SUP-` [sources-monitoring](research-notes/sources-monitoring.md)
- `SC-` [status-classifier §10](research-notes/status-classifier.md)
- `LI §6` [law-identity](research-notes/law-identity.md)
- `TD` [training-distill](research-notes/training-distill.md)
- `RO` [ref-ops-license](research-notes/ref-ops-license.md)

`SEC-` is the matching row in [15](15-security-and-deployment.md). Severity is the source
note's own. "(set here)" marks a severity assigned in this document (INFERRED). "Owner
decision" means a decision only the owner or counsel can make.

**Status.** **FIXED IN THIS PR** is used only for the defects listed in
[research-notes/law-stack-fixes.md](research-notes/law-stack-fixes.md) (F1–F8). Those fixes
are uncommitted in this worktree and VERIFIED offline (§4.1). Where a fix covers only part
of a source risk, the row is split: the `a` row is fixed, the `b` row stays open. Every other
row is **OPEN**. Changes on main since `0713370` close no row; partial upstream progress is
noted in the Risk column (ESA-20, ESA-46).

| ID | Sev | Area | Risk | Evidence | Remedy | Owner decision | Status |
|---|---|---|---|---|---|---|---|
| ESA-01 | **critical** (set here; LI §6 ranks it first) | User-facing legal data | **시행규칙 제73조: the quote is the 2027-09-16 text, labelled current.** The status-guidance record carries `mst 289833, effective 2026-09-15, review_state CURRENT_TEXT_READ`, and its quote adds 신용카드ㆍ직불카드 throughout and drops 가목. A user-facing line says registration-card fees may be paid in cash or a cash-payment voucher "(또는 카드·전자결제)" under 제73조 제1호. The text in force on 2026-10-19 requires 외국인등록증 issue and reissue fees in cash or a cash-payment voucher. The data is read at runtime (`adapters.py:56`, labelled unreviewed) and by the front-end status guidance. Counter practice may already accept cards; the cited legal basis does not say so before 2027-09-16. Sources: LI §6 item 1, verifier claims 3–4 | [CODE scripts/status_guidance/author_rules.py:339; data/status-guidance-202609.json:560-567, 1877] [LIVE law.go.kr lsHstListR 008494 and 제73조 at efYd 20260915 vs 20270916, 2026-10-19] VERIFIED (statute text). User impact INFERRED. Re-read unchanged on `fc896c2` (OBSERVED 2026-10-20) | Fix `author_rules.py` and regenerate (the data file is generated). Re-word the `:1877` line until 2027-09-16, or show both texts with dates. Give article-level citations their own 시행일 | **Yes**: legal wording change, review before publishing | OPEN |
| ESA-02 | **critical** (TD §0.3; REQUIRES LEGAL REVIEW) | Model providers / terms | **The production answer path runs on free channels whose published terms forbid production use.** OpenRouter's `nvidia/*:free` routes (Basic lead `nemotron-3-ultra-550b-a55b:free`, Fast `nemotron-3.5-lightning:free`, Basic 3rd `nemotron-3-super-120b-a12b:free`) are served by NVIDIA, and OpenRouter links them to the **NVIDIA API Trial Terms of Service**. Those terms limit use to trial purposes and bar production use of the service or its output (§1.2). They also forbid redistribution of output (§4.2) and personal information (§4.3), let NVIDIA use content to improve its models (§3.3(iv)), and require a Subscription for production (§1.4). Also: the Thinking Machines free research tier (no personal data; perpetual licence to train on traffic). Whether Google AI Studio unpaid terms bind the Gemma `:free` route is INFERRED. The weights' own licences (OpenMDW-1.1, Nemotron OML) do not restrict outputs; the serving channel does | [CODE backend/services/model_policy.py:31-37, 99-105] [LIVE openrouter.ai/api/v1/providers and /models/{id}/endpoints, 2026-10-19] [WEB https://assets.ngc.nvidia.com/products/api-catalog/legal/NVIDIA%20API%20Trial%20Terms%20of%20Service.pdf, accessed 2026-10-19] VERIFIED. Whether these terms bind OpenRouter-mediated calls is UNVERIFIED (SEC-02) | Legal review of the production channels. Move user-facing traffic to channels whose terms allow production use and the data involved. Never use trial output as training data | **Yes**, with counsel | OPEN |
| ESA-03 | high | Access control | **The diagnostics opt-in is open in production.** Any caller sending `diagnostics:true` or `X-Paradiso-Diagnostics: 1` gets the full internal payload: attempted models, upstream statuses, `law_evidence_pack` including `grounding_context_prompt`, and `knowledge_plan`. `_diagnostics_token_ok` returns true when no token is set. The smoke already sends a token secret, but the server reports none configured. The owner's pushed branch `fix/visable-diagnostics-token` (`c69c117`) renames the variable and keeps the "open when unset" behaviour. Sources: AL-R4, SEC-01 | [LIVE /health `client_diagnostics_mode: "open"`, 2026-10-19 03:37Z and 04:19Z] OBSERVED. [CODE paradiso_backend.py:5562-5600] VERIFIED. Payload contents INFERRED (no diagnostics request sent). Not re-observed after 2026-10-19 | Set the token on Railway with the same value as the repository secret, or set `PARADISO_CLIENT_DIAGNOSTICS=0` | **Yes**: Railway configuration | **RESOLVED 2026-10-20** (PR #666 merged as `8cae0cf`; owner set `VISABLE_DIAGNOSTICS_TOKEN` on Railway and as the repository secret; `/health` reports `client_diagnostics_mode: token`, OBSERVED) |
| ESA-04 | high | Request lifecycle | **Request context is ignored.** `/api/ask` truncates `context` to 8,000 characters and never reads it. Lost: nationality and interview-prep lines, the Quick-Answer handoff facts and the navigator's "explain the packet only" instruction. The answer language still arrives through `_answer_language_instruction(req.lang)`. `history` feeds only the repeat-abuse classifier, so every call is single-turn for the model. The navigator follow-up and the Quick-Answer handoff are therefore not bound to the facts the user saw and can contradict the packet. Unchanged on the branch. Sources: AL-R1 (corrected), AL-R2, AL V2 #1 | [CODE paradiso_backend.py:434-440, 568, 5764-5777; ai.html:2665, 3119; index.html:18387] VERIFIED; impact INFERRED | Either wire in a validated, size-capped, server-labelled context block, or stop sending it and rebuild the facts server-side from a packet id or status+procedure | **Yes**: which design. The callers live in `ai.html`/`index.html` | OPEN |
| ESA-05 | **critical** (SC-R1) | Classification | **Silent subcode→parent fallback.** When the text names a subcode and no payload is sent, `understand()` takes the mentioned parent and leaves `subcode=None`. `plan()` then serves the **parent checklist as `VERIFIED_WITH_CONDITIONS`**: E-7 with 10 items for "E-7-4 …", D-4 with 9 for "D-4-2K …". With the payload, the same question gives `NO_DIRECT_SOURCE`. This violates the rule that parent records must not present subcode rules as universal. `/api/ask`'s own `_select_grounding` returns None for these queries, but the plan still carries the parent-filled status into the conflict view and the answer guard. Related deliberate fallbacks: `employment_nl.sanitize_visa_status` (SC-R14) and the Hangul-boundary silent parent in `unified_search` (SC-R13) | [CODE backend/services/knowledge/understanding.py:124-131] [LIVE plan(), 2026-10-19] OBSERVED; **re-observed on `fc896c2`, 2026-10-20** | Never fill the subcode slot from the parent. Carry `mentioned_subcode` explicitly and route to `NO_DIRECT_SOURCE` / clarification. Add no-payload eval cases | No (the rule already exists); see ESA-22 for inheritance | OPEN |
| ESA-06 | high (SC-R2) | Classification | **Hash-seed nondeterminism.** `_detect_visa_codes` iterates a `frozenset` sorted only by length. For same-length codes, the winner depends on `PYTHONHASHSEED`, so different processes and workers can disagree. "F-6 배우자인데 E-9로 변경하고 싶어요" → F-6 for 7 seeds, E-9 for 3. No tracked file pins the seed | [CODE paradiso_backend.py:3881] [LIVE seeds 0–9] OBSERVED; **reproduced on `fc896c2`** | Sort deterministically (position in text, then code). Add a multi-seed test | No | OPEN |
| ESA-07 | medium (set here; licence) | Provenance | **`law_query_normalizer.py` provenance.** It closely translates the upstream korean-law-mcp `search-normalizer.ts` and `law-search.ts`: the same normalisation step order, the six 법 typo substitutions in upstream order, 48 of 60 non-law keywords shared (first 25 in identical order), the same loose-match rule and relevance weights. `THIRD_PARTY_NOTICES.md` acknowledges korean-law-mcp (MIT). It does not say that the normaliser, typo map and alias mechanism come from an upstream file headed "ported from LexDiff". LexDiff has been under BSL 1.1 since 2026-04-13 and had no licence before that. `law_tools.py`'s docstring says no third-party code was copied, while THIRD_PARTY_NOTICES says the fallback ladder was ported. Two integration docs still say "conceptual inspiration only" | [CODE backend/services/law_query_normalizer.py:24-30, 113-148, 419-486; law_tools.py:1-17, 786-860; THIRD_PARTY_NOTICES.md:9-115] VERIFIED (overlap re-checked by an independent script). Derivation judgement and licence status INFERRED; not legal advice. RO §2.3, §3.3, rec. 8 | (a) Disclose the LexDiff lineage and get the author's written confirmation that the korean-law-mcp copies are MIT; or (b) clean-room re-implement and remove the port claim. Fix the docstring inconsistency | **Yes**: owner or counsel | OPEN |
| ESA-08 | high (LS-R1) | Law grounding | **Live statute rows are dropped from the `/api/ask` evidence pack.** `build_law_evidence_pack` runs `_normalize_candidate` again on already-normalized rows. That function only recognises raw DRF keys, so every row becomes `None` and `law_sources=[]`. The status ends at `law_grounding_used_without_normalized_evidence`; the prompt reads "Law evidence: attempted but unavailable"; the panel shows statute `no_results` / public `temporarily_unavailable`. Knock-on: case-law expansion never gets statute anchors. Fails closed, so the system does not overclaim today. The same line is on the owner's branch | [CODE law_tools.py:381-385, 2090-2093; paradiso_backend.py:1039-1077, 5387-5389] VERIFIED offline through the real app (probes p12/p13/p15/p17; verifier ls_v1, ls_v4, ls_v6). Production impact INFERRED (no AI POST). Fix: F1 `_normalize_context_law_row` and `_downgrade_decree_families_without_rows` [TEST test_law_stack_genesis_regressions.py `F1EvidencePackTests` (ran: pass, 2026-10-20; fails on HEAD per law-stack-fixes.md)] | Done in this PR (F1). F1 must not ship without F2 (ESA-09a). It makes ESA-09b visible | No | **FIXED IN THIS PR** |
| ESA-09a | high (LS-R2, AL-R5) | Citation guard | **The guard allowed every article number once "verified".** When `law_grounding_verified` was true, `guard_answer_citations` accepted every article number the model wrote, unchecked (`allowed_verified`). ESA-08 hid this; fixing ESA-08 alone would have switched it on | [CODE law_citation_guard.py:122-128 (main)]. Fix: F2, an `article_evidence` binding with a law-reference scanner that fails closed [TEST `F2CitationGuardTests`, `test_f2_backend_guard_does_not_blanket_allow_after_f1` (ran: pass, 2026-10-20)]. One existing test was inverted because it asserted the defect (`test_e7_workplace_change_law_grounding.py`, see law-stack-fixes.md) | Done in this PR (F2). Residual: multi-word law names cannot be bound, so they fall back to the local-evidence path (fail closed) | No | **FIXED IN THIS PR** |
| ESA-09b | high (LS-R2, AL-R5, AL V2 #6) | Verification semantics | **"Verified" still means "a law title was found".** A list hit becomes `verified_law_evidence`. The cloud fallback maps any phrase containing a core name to that law's title rows (5 of 5 issue queries → `ok`). After F1, title-only hits keep `law_grounding_verified` and `law_grounding_status_detail = law_grounding_verified`. ai.html then shows the "실시간 법령 확인" row, and the prompt gets the VERIFIED citation directive. On the **streamed** path that directive is the only control. `citationsTrustworthy` is derived from configuration. `/api/ask` passes no `article_evidence` to the guard. `statute_citation_guard` runs only in the overview, with empty evidence, so it is a blanket `unverifiable` | [CODE citation_verifier.py:116,136; law_grounding.py:524, 648-651; law_cloud_fallback.py:79-94; ai.html:1684-1697; paradiso_backend.py:1016-1036, 5140, 6280-6291, 8165, 8305] VERIFIED; probe p10 re-run. The post-F1 behaviour is from law-stack-fixes.md "Behaviour the owner should know" item 1 (VERIFIED offline; production INFERRED) | Split "law located" from "article text verified" in the reconcile step and the status detail. Pass `article_evidence_from_law_pack(pack)` in `_apply_law_citation_guard`. Per-answer trust. Wire `statute_citation_guard` with real evidence. All of this is in `paradiso_backend.py` (owner's file) | **Yes**: deploying F1+F2 before this split changes what users see | OPEN |
| ESA-10a | high (LS-R4) | Failure taxonomy | **Failure shown as absence, on the paths this PR fixes.** D1: a cited law whose search timed out → `CITED_LAW_NOT_FOUND` when no other query returned it. D2: no-results outranked a real error. D3: budget exhaustion and a successful lookup both became `no_results`. D5: the ranked ladder kept the last attempt. D10: the prompt said "unavailable" after a success (a consequence of D3 and ESA-08) | [CODE law_grounding.py:331-346, 652-655; law_tools.py:832-869, 2104-2108, 2483-2484 (main)]; verifier ls_v3 A/B, p15, p16. Fixes F3 (`_failed_search_error`, error precedence), F4 (`_context_family_status`), F5 (first infrastructure error) and F1 [TEST `F3CitedLawFailureTests`, `F4FamilyStatusTests`, `F5RankedSearchTests` (ran: pass, 2026-10-20)] | Done in this PR | No | **FIXED IN THIS PR** |
| ESA-10b | high (LS-R4; AL-R14, LS-R15 low) | Failure taxonomy | **Failure shown as absence, on the remaining paths.** D4: planned but never queried → `no_results` (`legal_analysis.py`, owner's file). D6: an empty 200 → `law_api_no_results`. D7: empty fallback pages cached for 15 min. D9: a detail fetch where the name key is not recognised (the heading and 항 parts are fixed by F7). D11: JS `fetchJson` returns `null` for every failure. D12: relevance-filtered precedents labelled `no_results`. A detail-fetch failure after a successful search is still `failed_verification`. The exception path of `build_law_grounding_context` has no `error_type`. The public projection maps `no_results` to `temporarily_unavailable` (AL-R14). The official-error heuristic flags any `message` containing "not", "error" or "fail" (LS-R15) | [CODE law_tools.py:524-527, 583-584, 2188-2203; law_grounding.py:362-392, 547-558; legal_analysis.py:718-719; law_cloud_fallback.py:160-161, 296-301; source_grounding.py:66; enforcement-precedent-grounding.js:29-42] VERIFIED; residual list in law-stack-fixes.md "Not done here" | Classify per query; map every error type; treat an empty 200 as an anomaly; separate "nothing found" from "could not look" in public states; match `resultCode` only | No | OPEN |
| ESA-11 | high (LS-R3; AL-R9 medium) | Latency / availability | **Blocking `urllib` on the event loop, no end-to-end deadline, unbudgeted retries.** `/api/ask`, `/api/legal/*` and research make sync calls inside `async def` handlers. Only enforcement uses `to_thread`. `legal_evidence` has no total budget: 3 attempts per request, up to 24 attempts, about 190 s at 8 s timeouts (INFERRED). The 45 s model budget starts only after law retrieval, so the worst case exceeds the 75 s client abort. Worker count: one by the code default; `WEB_CONCURRENCY` on Railway was not read | [CODE law_tools.py:165-194; paradiso_backend.py:5957, 6522-6527; legal_evidence.py:777-839, 967-1036; enforcement_service.py:541-551; backend/railway.json:6] VERIFIED; timing INFERRED (SEC-04) | `asyncio.to_thread` or an async client. One per-request law budget shared by all stages. A circuit breaker. No retries on timeout inside a user request | No | OPEN |
| ESA-12 | high (SRC-02; LS-R6 medium) | Law identity / time | **No law-version identity, history or 부칙, and the stored pins are already stale.** Nothing sends `efYd` or reads `조문시행일자`. Dates collapse. `source_id` prefers 법령ID. There is no content hash or retrieval record. Stale: Act 272921 → 290729, Decree 289697 → 290501 (both effective 2026-10-02). They ship in `backend/data/knowledge_deploy/status-guidance-202609.json`. Also stale: 국적법 시행령 (stale since 2022 while marked verified), 국적법 시행규칙 and `document_help.json`. The 외국인고용법 trio is untracked, including its pending 2026-12-10 / 2027-06-10 changes. No law/manual conflict detection (Q12). `docs/audit/law_crosscheck_2026_06.md` confuses 공포일 with 시행일 | [CODE author_rules.py:316-318; status-guidance-202609.json:379-475; nationality_sources.json:371-408; document_help.json:31; data/source_registry.json:203-216] [LIVE law.go.kr lsHstListR, 2026-10-19] VERIFIED. LI §6 items 2–7, 10 | A law-identity registry keyed by 법령ID + lsiSeq + efYd, polled from the history list. Persist 공포일 and 시행일 per version. Article-level effective dates. Flag facts that cite a changed law. Update the stale pins and regenerate. See [06](06-temporal-law-and-source-identity.md) | No (data hygiene); re-verification of the 국적법 forms needs review | OPEN |
| ESA-13 | high (AL-R3) | Prompt evidence | **Client-supplied `visa_data` becomes "manual-backed" prompt evidence.** Catalog fields (240 characters) and variant docs and notes (180) are taken verbatim from the request under headings that say they come from official manual pages. `visa_data.code` also overrides free-text status detection. The only server check is a 300k size cap. Anyone can make Waymaker present their own text as manual-backed in their session | [CODE paradiso_backend.py:3858-3870, 4161-4549, 5778-5794] VERIFIED (SEC-08) | Resolve `visa_data` by code from the server's `visa_data.json`; ignore the client's record content | No | OPEN |
| ESA-14 | high (KP-1, SRC-04; AL-R12 medium) | Manual evidence edition | **Runtime evidence cites a superseded, never-approved edition, and the approved one backs nothing.** All 42 PUBLISHED facts cite 2026.6 (`stay_manual_2026_06_23_pdf`), yet coverage still reads `VERIFIED_WITH_CONDITIONS` and staleness is shown only to operators. The approved 2026.7 edition backs 0 facts. The production manual index has 0 approved direct-evidence chunks. The 2026.9 deltas are 검토 전 on main. The owner's branch approves 2026.9 and re-seeds; that "resolves" this is INFERRED (not run) | [LIVE /api/health/ai 2026-10-19] [LIVE in-memory bootstrap] OBSERVED; [CODE retrieval.py:255-263; coverage.py:112-129; runtime.py:289] VERIFIED | Land and verify the branch's re-seed on approved 2026.9, or show a public `outdated_or_unknown` flag until re-verified. Add an "approved edition older than newest received" alarm | **Yes**: merge and review of the branch | OPEN |
| ESA-15 | high (KP-2) | Knowledge governance | **Publish does not require the cited edition to be content-approved.** Ingestion only warns. This contradicts the approval index rule that only approved content may back a direct assertion. A dry run of the 2026.9 status-guidance adapter produced 423 proposals, all carrying the warning | [CODE review.py:227-239; ingestion.py:173-174] [TEST test_knowledge_platform.py:279-308 (ran: pass)] VERIFIED | A publish check on `content_review_state == 'approved'` (or an explicit, audited override) plus a DB trigger | No | OPEN |
| ESA-16 | high (CI-01) | Deployment | **`main` is unprotected and every merge deploys.** No branch protection and no rulesets, including at org level. Production follows main within about 2 minutes. Any merged change to `visa_data.json` or the approval index goes live with no required checks | [LIVE gh api `branches/main/protection` → 404; `/rulesets`, `/rules/branches/main` → `[]`; smoke run 38292940698] OBSERVED (SEC-03) | Protect `main`; require repo-validation and manual-code-coverage | **Yes** | OPEN |
| ESA-17 | high (SRC-01) | Change monitoring | **HiKorea change detection is off behind green runs.** Both board-monitor baselines are `null`, so every run returns `baseline_unset` with success. The scheduled manual sync is a no-op (`download_url: null`, and cron never passes `--allow-network`). Even with a baseline, a whole-page hash would fire on every unrelated notice (INFERRED) | [CODE data/sources/hikorea_manual_board_watch.json:24,31 (still null on `fc896c2`); monitor_hikorea_manual_board.py:96-97] [LIVE gh runs 36382717727, 37270107456, 38211467187, 38688541847] OBSERVED | Commit baselines. Diff parsed notice rows (title, date, attachments). Make persistent `baseline_unset` or `no_source` a failure or an issue | **Yes**: first baselines are human-bumped by design | OPEN |
| ESA-18 | high (SRC-03) | Source identity | **Two different "260731 stay manual" binaries disagree on an E-7-4 시행일자** ('26. 7. 9. vs '24. 11. 27.). The unregistered backend copy, via its pyhwp text, feeds 10 `visa_data.json` refs. The '24.11.27 value also appears in the older 260709 extract. Which binary HiKorea served is UNVERIFIED. The branch keeps both | [LIVE shasum + extraction diff (exactly one line, 8237), verifier re-run] VERIFIED | Register or retire the backend copy. Re-point the refs to the approved text. Add a guard that every manual binary in the repo is registered | **Yes**: which binary is authentic; `visa_data.json` is protected | OPEN |
| ESA-19 | high (EXT-01; EXT-02/04 medium; EXT-03 low) | Extraction | **Structure is flattened and warned about only per document.** Tables (merged and empty cells), images (no placeholder) and footnote links are lost. Hancom PUA glyphs are unmapped (281/436/455). Tab and NBSP are dropped without whitespace. Near-empty or image-only PDF pages pass silently, and there is no OCR. `has_images` is unused. **No passage-level flag reaches retrieval or answers** | [CODE decrypt_hwp_distribution.py:51-53, 226-238, 268-270; build_current_manual_corpus.py:89; manual_search.py:214-226] VERIFIED | Passage-level flags (`in_table`, `image_omitted`, `pua_glyph`, near-empty page) carried into hits and answers. A PUA normalisation table applied in search and display only. A table-aware path (the branch's Markdown tables are a start) | No | OPEN |
| ESA-20 | high (SC-R3) | Classification | **English article and number false positives.** "Can I get a 3 month extension?" → A-3 in `_detect_visa_codes`, `legal_analysis`, `unified_search` and JS. JS resolves a definite A-3 extension answer (HIGH, 2 documents). "I am a 2nd year student" → A-2. On `fc896c2` the JS `unknownCodes` for the A-3 case is empty, so the "A-3-MONTH is not a code" notice no longer has a trigger: the answer is probably now silent (INFERRED) | [CODE paradiso_backend.py:3885; legal_analysis.py:75; unified_search.py:74; status-guidance.js codeRe] [LIVE probes 2026-10-19; re-run 2026-10-20] OBSERVED | Require a hyphen or an uppercase letter adjacent to the digit, or a word boundary that excludes English articles. Add negative cases | No | OPEN |
| ESA-21 | high (SC-R4, SC-R5) | Classification | **Python cannot read subcodes from text and truncates some to the wrong code.** `_detect_visa_codes` returns `(None, None)` for "D-2-1 …" and collapses `*-T` to the parent, so any exact-subcode metric for B1 is 0 by construction. `legal_analysis` truncates D-4-2K → **D-4-2** (a different real subcode), F-2-7S → F-2-7 and d21 → D-21. `immigration_tools` truncates to the parent. Both feed `immigration_facts` into the prompt | [CODE paradiso_backend.py:3855-3860, 3885; legal_analysis.py:75,123-128; immigration_tools.py:735] [LIVE] OBSERVED | One dataset-validated subcode parser shared by the backend (cf. `unified_search` and JS `normalizeCode`) | No | OPEN |
| ESA-22 | medium (SC-R8) | Policy | **The two stacks encode opposite inheritance policies** for E-7-4 extension. JS inherits the E-7 common rule and says so; the Python seed case expects `NO_DIRECT_SOURCE`. Both pass. JS draws on the 2026.9 bundle, Python on 2026.6 grounding | [CODE scripts/check_status_resolver.mjs:57; DOC eval_corpus_seed.json:104-115] VERIFIED | Decide per subcode against the 2026.9 stay manual; encode it once | **Yes**: needs manual review | OPEN |
| ESA-23 | medium (KP-6, SC-R9; KP-8 low) | Evaluation | **Eval corpora are narrow and self-referential.** Labels are hand- or agent-authored, seed cases are auto-approved by a seed actor, and expectations come from the file that seeds the facts. 1 of 69 cases declares slot dependencies. The guard runs with no verified facts. Golden codes are payload, so text detection is tested 3 of 50 for parents and 0 of 50 for subcodes. A stale label is hidden by an allow-list. Enforcement provenance checks are structural only. No case records independent human labelling. The golden runner opens the on-disk dev DB by default | [CODE evals.py:130-131, 184-187; scripts/evaluate_paradiso_ai_golden_questions.py:68-77, 94-101; enforcement_benchmark.py:69-121, 402-403; store.py:62-63] [LIVE] VERIFIED | Label-provenance fields and human sign-off. Text-only re-labels. Slot dependencies. Verified facts passed to the guard. Force `:memory:` in CI scripts | **Yes**: who signs off labels | OPEN |
| ESA-24 | medium (KP-5) | Answer gating | **The coverage decision is advisory.** `NO_DIRECT_SOURCE` and `NEEDS_CLARIFICATION` do not constrain generation, so uncovered questions go to the LLM pipeline as before | [CODE paradiso_backend.py:2751-2790, 6209-6217; runtime.py:160,184] VERIFIED | Decide which coverage states constrain generation. Add served-path eval assertions | **Yes** (open question in KP §8) | OPEN |
| ESA-25 | medium (KP-3) | Privilege | **No separation of duties.** One operator token can approve, verify and publish. The publish reason is enforced only in the UI. The CLI takes a free-text operator name. Raw SQL can edit published citations and `verified_by` | [CODE repository.py:385-413; review.py:220-268; evals.py:83-95; knowledge-studio.js:299-303] [LIVE kp_verify4.py] VERIFIED/OBSERVED (SEC-16) | Require verifier ≠ reviewer for PUBLISHED. Server-side reason. Triggers on citation UPDATE for reviewed facts | **Yes** | OPEN |
| ESA-26 | medium (KP-4) | Durability | **The knowledge store may be ephemeral.** `railway.json` declares no volume. On an ephemeral filesystem the default path opens and reports `durable=True`. Operator edits, gaps, feedback and eval runs would be lost on redeploy | [CODE store.py:41, 62-90; runtime.py:359-374] VERIFIED; production volume UNVERIFIED (SEC-21) | Confirm the volume and `WAYMAKER_KNOWLEDGE_DB`; alert when the configured path is not a mounted volume | **Yes** | OPEN |
| ESA-27 | medium (KP-7) | Second truth | **Unreviewed 2026.9 status guidance powers Quick Answer outside the lifecycle.** 697 of 700 entries are `SEPT_2026_ORIGINAL_UNREVIEWED`. Partly mitigated: the UI says 검토 전 원문. ESA-01 lives in this file | [DATA data/status-guidance-202609.json] [CODE assets/js/status-guidance.js:74,134,144] VERIFIED | Migrate Quick Answer to `GET /api/knowledge/published` as planned | **Yes**: may it keep serving unreviewed text? | OPEN |
| ESA-28 | medium (AL-R6; KP-11 low) | Guards | **The stream and fallback paths bypass most answer guards.** SSE skips the confidence gate, shape gate, case verifier, statute guard and Answer Guard (no shipping caller streams). The Groq family fallback returns raw text with no scrub. The Groq-primary path applies only the confidence gate. The nationality coach reaches Groq with no opt-in, and Groq is configured live | [CODE paradiso_backend.py:3294, 6697-6776, 7792-7798] VERIFIED; [LIVE groq.configured true] OBSERVED (SEC-13) | One ordered guard pipeline for every exit. Keep the stream off until parity | **Yes**: Groq for the coach | OPEN |
| ESA-29 | medium (AL-R7) | Cost / policy | **The enforcement structured chain uses paid model ids** (`openai/gpt-oss-20b`, `google/gemma-4-31b-it`, `openai/gpt-oss-120b`), while the policy doc says free by default. The env-override cause and "paid" are both INFERRED (no `:free` suffix) | [LIVE /api/health/ai taskRoleModels] OBSERVED; [CODE model_policy.py:112-116, 190-201] (SEC-14) | Confirm intent; record it in policy; add a spend alert | **Yes** | OPEN |
| ESA-30 | medium (AL-R8; LS-R14 low) | Second runtime | **The Vercel AI functions are ungoverned.** They have their own model lists (including `meta-llama` and `nousresearch`), env precedence with no opt-in gate, no rate limit, public model ids and provider error codes, and sit outside `check_ai_architecture.py`. The Quick Answer validator checks facts only against client input, which makes it an open provider-quota sink (bounded by the validator and 400 tokens). The Vercel precedent path ignores `LAW_GROUNDING_MODE` and grades any body mentioning 출입국 as DIRECT | [CODE lib/waymaker-quick-answer-ai.js:18-37, 177-182; lib/enforcement-grounded-ai.js:13-41; lib/enforcement-precedent-grounding.js:96-140; scripts/check_ai_architecture.py:128-141] [LIVE L3] (SEC-12) | Extend the guard to `lib/` and `api/`. A shared policy JSON. A per-IP limit. Drop `model` from public responses. Or retire the functions | **Yes**: retire or govern | OPEN |
| ESA-31 | medium (set in SEC-09) | Prompt injection | **No data-not-instructions framing.** One concatenated user message with bracketed headings, no fences or escaping. In the ungrounded prompt the user question is the last block. Only the enforcement prompts mark case text as untrusted. Output-side mitigations exist on the buffered path only. The branch adds usage rules but no data framing | [CODE paradiso_backend.py:1303-1339, 4079-4136, 6219-6316] VERIFIED; exploitability INFERRED (AL §5) | Delimit retrieved and user text as data; put rules in the system message; one guard pipeline (ESA-28) | No | OPEN |
| ESA-32a | medium (LS-R7) | Credential host trust | **The Python `LAW_API_BASE_URL` override sent the OC to any host.** On HEAD, three OC-bearing URLs went to a third-party host when it was configured, while a strategy doc suggests exactly such a host | [CODE law_tools.py:625-634 (main); DOC docs/EXTERNAL_SKILLS_AND_LEGAL_GROUNDING_STRATEGY.md §2.1]. Fix: F8 `_trusted_base_url` accepts only https `www.law.go.kr` / `law.go.kr`; anything else logs `LAW_API_BASE_URL_IGNORED` [TEST `F8HostTrustTests` (ran: pass, 2026-10-20)] | Done in this PR (F8). If Railway sets `LAW_API_BASE_URL` to a proxy, the next deploy stops using it; check the preflight after deploy | No | **FIXED IN THIS PR** |
| ESA-32b | medium (LS-R7) | Credentials in transit | **The OC can still be resent over plaintext HTTP.** After a connection-level failure the http↔https swap resends it (now only to law.go.kr, and logged as `LAW_API_PLAINTEXT_RETRY_*`). Inside `legal_evidence` that can mean up to 3 plaintext sends per request. The fix agent deliberately left the swap unchanged: the history does not show that production is independent of it. The legacy `KoreanLawClient` still sends a Bearer credential to any host. Operator scripts try HTTP first. The netdiag remediation text (`paradiso_backend.py:7508`) still recommends a proxy through `LAW_API_BASE_URL`, which no longer works | [CODE law_tools.py:198-232; korean_law_client.py:59-63; scripts/sync_official_terms.py:40-43; scripts/probe_korean_law_open_api_2026_05.py:47-52] [TEST test_law_tools.py:105-175 asserts the fallback (ran: pass)] VERIFIED; law-stack-fixes.md F8 (SEC-06) | After deploy, search the Railway logs for `LAW_API_PLAINTEXT_RETRY_REACHED`. If it never appears, gate the http retry behind an opt-in. Delete the legacy clients; make the scripts https-first; reword the netdiag text | **Yes**: whether the HTTP fallback goes | OPEN |
| ESA-33 | medium (LS-R8) | Rate limits | **Unauthenticated, un-rate-limited law proxies spend the owner's OC.** `/api/legal/laws/search` and `/precedents/*` have no limit, and neither does the Vercel `law-probe`. One query can become 13 upstream calls through the fallback pages | [CODE paradiso_backend.py:6898-6961; api/enforcement/law-probe.js:51-66; law_cloud_fallback.py:19-20] VERIFIED (SEC-07) | `rate_limit` dependencies; a shared response cache; restrict or remove the probe | **Yes**: keep them public? | OPEN |
| ESA-34a | medium (LS-R9, D8) | Negative caching | **`legal_evidence` cached any response below HTTP 400 before parsing it**, so official-error (credential or IP allowlist) and empty bodies were replayed for 24 h | [CODE legal_evidence.py:813-839 (main); grounding_config.py:10,149]; verifier ls_v5. Fix: F6 `_is_cacheable_response` caches only parsed successes with at least one record [TEST `F6LegalEvidenceCacheTests` (ran: pass, 2026-10-20)] | Done in this PR (F6). A repeated no-results question now costs one more request | No | **FIXED IN THIS PR** |
| ESA-34b | medium (LS-R9) | Caching | **The remaining cache problems.** Unbounded module dicts. No cross-request statute cache. Keys ignore credential rotation. The cloud fallback caches empty pages for 15 min | [CODE legal_evidence.py:734-760; law_cloud_fallback.py:41, 117-162] VERIFIED | A bounded LRU; a credential fingerprint and API version in the key; short, typed negative TTLs | No | OPEN |
| ESA-35a | medium (LS-R5) | Article parsing (Python) | **Only `조문내용` was read, with no `조문여부` filter.** A heading unit ("제1장 총칙" shares 조문번호 1) could satisfy "verified", and 항/호 text was dropped, so a "verified" snippet could be a bare title line | [CODE law_tools.py:950-1025 (main); law_grounding.py:369-373]. The real shape was confirmed from the documented Open API sample (`s2_law_detail.json`, sha256 `c5fb59c0…94ad75`). Fix: F7 `_is_article_unit`, `_article_unit_text`, with a real-shape fixture carrying law.go.kr attribution [TEST `F7ArticleExtractionTests` (ran: pass, 2026-10-20)] | Done in this PR (F7). `조문시행일자`, 부칙 and 별표 are still not read (ESA-12) | No | **FIXED IN THIS PR** |
| ESA-35b | low (set here; LS-R5) | Article parsing (JS) | **JS `findArticle` still ignores `조문여부` and 가지번호** on the Vercel enforcement path | [CODE lib/enforcement-law-grounding.js:145-166] VERIFIED | Port the F7 rules, or route through Railway (ESA-30) | No | OPEN |
| ESA-36 | medium (LS-R10; AL D13) | Fan-out | **Duplicate retrieval.** Precedent is searched by two clients per request (pack ×1 + `legal_evidence` ×4 variants). Knowledge retrieval runs twice. Python uses name search and JS body search | [CODE law_tools.py:2148-2173; legal_evidence.py:1005-1027; precedent_sources.py:629] VERIFIED; ls_v4 | One retrieval per family per request; choose the search mode deliberately | No | OPEN |
| ESA-37 | medium (LS-R11) | Relevance | **Relevance confirms itself.** The haystack includes the backend's own query, so title-only rows are upgraded from background to related | [CODE legal_analysis.py:742-748] VERIFIED; probe p11 | Score against source content only | No | OPEN |
| ESA-38 | medium (AL-R11) | Case citations | **Correctly cited `legal_evidence` cases can be flagged fabricated and the answer replaced.** Injected cases are not in `precedent_evidence_items`. Reproduced offline: citing `2019두12345` gave `case_decision_citation_repaired: true`, and the model text was replaced by the deterministic synthesis | [CODE paradiso_backend.py:2641, 2685-2712, 5417-5439; citation_verifier.py:352-410] OBSERVED offline (verifier VX1) | Feed `legal_evidence` cases into `verify_case_decision_citations` | No | OPEN |
| ESA-39 | medium (AL-R10) | Rate limits | **The rate-limit key is the first `X-Forwarded-For` token.** If Railway appends rather than replaces, rotating fake IPs bypass the `/api/ask` limits | [CODE backend/rate_limit.py:65-87] VERIFIED; proxy behaviour UNVERIFIED (SEC-11) | Use the right-most trusted hop or Railway's client-IP header | No | OPEN |
| ESA-40 | medium (SRC-05) | Citation freshness | **Stale citations are not detected, and CI pins staleness.** 1,268 of 1,292 refs point at superseded files. `check_repo.sh:121-122` requires `manualVersion == "2026.5"`. The branch moves 955 refs | [CODE scripts/check_repo.sh:121-122] [LIVE count] VERIFIED; unchanged on `fc896c2` | A citation-freshness check against registry status; replace the version pin with "cites a registered, non-deprecated edition or is flagged" | No | OPEN |
| ESA-41 | medium (CI-02) | Hidden failing invariant | **`check_260617_subcode_inventory_coverage.py` fails on main, and its committed report says it passes.** 13 F-4 subcodes lack source or review flags; F-2-6 is shown active although abolished. About 25 checks and 6 script tests never run, and the check script writes into a tracked path | [TEST (ran via import: rc 1, FAIL)] [CODE docs/data/2026_06_17_subcode_coverage_report.json] VERIFIED | Add the check to CI as check-only. "Check" scripts must never write tracked files | **Yes**: are the 13 F-4 subcodes intentionally unsourced? | OPEN |
| ESA-42 | medium (CI-03) | Extraction CI | **No CI job decrypts a real HWP, and `olefile` is undeclared.** The 4 scripts that import it would fail in a clean venv. `extracted_text_sha256` of the current entries is not re-verified | [CODE scripts/tests/test_decrypt_hwp_distribution.py; check_source_manuals.py] VERIFIED (venv `ModuleNotFoundError`) | Pin `olefile`; a CI step that re-extracts and compares hashes, including current entries | No | OPEN |
| ESA-43 | medium (CI-04) | Frontend CI | **DOM tests self-skip** (no jsdom in the validate job). E2E specs are not all in CI. No lockfile; caret ranges | [LIVE CI log "jsdom not installed … SKIP"] OBSERVED; spec counts as of `0713370` | `npm ci` with a committed lockfile; wire the remaining specs | No | OPEN |
| ESA-44 | medium (SUP-01) | Supply chain | **Unpinned installs.** pip, npm, go and cargo `@latest` installs; tag-pinned actions; a write-token job with unpinned installs; shell-interpolated dispatch inputs; unpinned production Python | [CODE .github/workflows/*] VERIFIED (SEC-15, SEC-18) | Pin versions and hashes; SHA-pin actions; pass inputs via env | Partly | OPEN |
| ESA-45 | medium (SC-R7, SC-R10) | Classification | **Procedure gaps and over-tagging in Python.** `_detect_task_type` has no visa-issuance, CVI or re-entry branch and misses "A에서 B로 변경", "change from … to" and "E-9 사업장 변경". `immigration_tools.statusChange` is false for "change from D-10 to E-7-1". Issue tags over-fire (`registration_deadline` with no deadline asked; a spurious `extension`), and those tags drive source routing and tier escalation | [CODE paradiso_backend.py:3891-3989; legal_analysis.py:211-243, 549-559; model_policy.py:58-71] [LIVE] OBSERVED | Extend the task ladder through the procedure crosswalk; tighten the tag triggers; add cases | No | OPEN |
| ESA-46 | medium (SC-R6; SC-R13 low) | Classification | **Token glue and boundaries.** "D-10 to" → `D-10-TO` and "D-10 E-7" → `D-10-E` (E-7 lost). JS lost the current status for "from X to Y". `unified_search`'s `\b` fails before Hangul ("D-2-1비자" → D-2 silently). **On `fc896c2` the JS glue no longer reproduces** (#664 `codeRe` rewrite). `unified_search.py` is unchanged, so its glue is presumably still present (INFERRED) | [CODE unified_search.py:74] [LIVE 2026-10-19; JS re-run 2026-10-20] OBSERVED | Port the #664 rule to `unified_search`; Hangul-aware boundaries; parity fixture | No | OPEN |
| ESA-47 | medium (SC-R11) | Data shape | **Data shape hazards.** Subcodes sit under programs and foreign parents (`C-3 → C-2`, `K-STAR`, `REGION-S`). 7 subcodes are placed twice (`unified_search` keeps the first; `lookup_status` finds subcodes only by prefix). `D-4-1` and `D-4-2K` are both top-level and nested. `F-10` is accepted by the Python main-code list | [LIVE inv2.py] [CODE paradiso_backend.py:3714-3726; immigration_tools.py:339-348] OBSERVED | Index subcodes by code, not by placement; remove `F-10`; record program membership separately | **Yes**: `visa_data.json` is protected | OPEN |
| ESA-48 | medium if pursued (KP-10) | Training assets | **The Gemma fine-tune scaffold is not a usable asset.** 14 synthetic AI-generated examples; never run (0 notebook outputs). The eval set is never scored, and the build script leaks eval into train. bf16 on a T4; unpinned dependencies; an off-contract 6-section format. The default preset is actually Qwen3-1.7B | [CODE experiments/waymaker-gemma4-finetune/*] [LIVE ipynb parse] VERIFIED | Treat it as scaffolding; real data only from published facts and approved eval cases with provenance (see [11](11-dataset-governance.md), [13](13-artemis-experiment.md)) | No | OPEN |
| ESA-49 | low (set here) | Source text | **Identifier and title drift that answers can inherit.** The F-4 고시 number is 제2026-35호 in the manual corpus (31 files) but 제2026-65호 on law.go.kr. `visa_data.json` uses the old spacing "법적지위" and "…관한 지침" where the official title ends in 훈령 | [LIVE admRulScListR, 2026-10-19] [CODE visa_data.json:6098, 6374, 30450, 32712] VERIFIED (mismatch). LI §6 items 8–9 | Flag for human check against 관보 or the MoJ notice; never auto-edit the manual text | **Yes** | OPEN |
| ESA-50 | low (LS-R12, AL-R15; CI-05 low) | Monitoring | **Health and smoke prove configuration only, for law.** `citationsTrustworthy` is derived from configuration. The preflight shows the concatenated query and a false `LAW_API_ENDPOINT_MISSING`. A mismatched commit fails the smoke with a misleading message. Each push spends production model quota and the OC | [CODE paradiso_backend.py:5140; law_grounding.py:684, 709-710; railway-live-smoke.yml:99-110, 206-208] [LIVE L2/L3] VERIFIED (SEC-20) | A CI assertion with a law question checking `law_grounding_status_detail` and evidence count; fix the preflight; a clear commit-mismatch failure; tag synthetic traffic | No | OPEN |
| ESA-51 | low (AL §6, AL-R17, AL-R13) | Exposure | **Public responses expose internal state.** About 130 fields go to anonymous `/api/ask` callers (query plans, family statuses, safety reason). `/health` and `/api/health/ai` show model ids, cooldowns and an env presence map, and report unused roles (router, translator, verifier, Chinese) as if wired. The coach returns provider and model. Quick Answer returns the model id | [CODE paradiso_backend.py:5523-5629, 7901-7905] [LIVE L1–L3] OBSERVED (SEC-19) | Decide what may be public; project the coach like `/api/ask`; report `wired: false` per role | **Yes** | OPEN |
| ESA-52 | low (SUP-02) | Dependencies | **starlette 0.38.6 has two multipart DoS CVEs**; exposure is low. FastAPI 0.115.0 caps starlette below 0.39, so the two must be upgraded together | [WEB https://api.osv.dev/v1/vulns/GHSA-2c2j-9gv5-cj73, accessed 2026-10-19] VERIFIED | Bump FastAPI and Starlette together | No | OPEN |
| ESA-53 | low (SC-R12) | Multilingual | **zh, ja, vi and ru lose procedure and intent**, and ja, vi and ru get the wrong language label. There are 0 non-ko/en eval cases | [CODE understanding.py:82-90] [LIVE ml.txt] OBSERVED | Add multilingual cases before claiming support | No | OPEN |
| ESA-54 | low (set in SEC-17) | Secrets hygiene | **Unused secrets are configured.** `DATABASE_URL`, `SUPABASE_URL` and `SUPABASE_SERVICE_KEY` are present live but unused by AI code | [LIVE L1 booleans] OBSERVED; AL §3.3 | Remove them if unused | **Yes** | OPEN |
| ESA-55 | low (LS-R13, AL-R16, KP-9, DOC-01) | Documentation | **Doc and registry drift.** The precedent docstring says "not invoked by production fan-out". The logging notes say law is off by default. The registry says `not_configured`. The runbook says audit mode. The model-role and provider policy docs disagree with the code. The golden doc says 45 (it is 50). `SOURCE_MANUALS.md` says 2026.6 is current. The sync docs call 배포용 HWP unextractable. `OPENROUTER_GEMMA_PIN_AND_LAW_GROUNDING_NEXT_STEPS.md` is stale | Files cited in the source notes. VERIFIED | Doc-hygiene PR; generate the registry status and model tables from code | No | OPEN |

---

## 10. Not verified, and open questions

These were left open by the notes and are not settled here:

- **Production `/api/ask` behaviour for a law question.** No AI POST was allowed, so ESA-08 in production is INFERRED from offline runs through the real app.
- **Railway environment values:** `WEB_CONCURRENCY` (worker count), `OPENROUTER_TIMEOUT_SECONDS`, `OPENROUTER_ENFORCEMENT_MODEL*`, `LAW_API_BASE_URL` and `LAW_GROUNDING_TIMEOUT_SECONDS`. Also whether a volume is mounted, and whether `WAYMAKER_OPERATOR_TOKENS` is set.
- **The real `lawService` JSON nesting** (`조문여부` heading units, 항/호). The audit could not observe it. This PR's F7 has since confirmed the shape from the documented Open API sample `s2_law_detail.json` (건강가정기본법). It is still not observed with the production OC (§4.1, ESA-35a).
- **Vercel:** credential state, deploy-on-push, and liveness of `api/enforcement/*` and `law-probe.js`.
- **HiKorea:** which 260731 stay binary it actually served; whether the 자료실 HTML carries per-request tokens.
- **Law identities:** whether MST 272921's 시행일 is 2026-01-23 (per law-identity and `author_rules.py`) or 2025-07-22 (per the crosscheck snapshot header). law-identity's history query supports 2026-01-23, with 2025-07-22 as the 공포일.
- **Product decisions:** the correct E-7-4 inheritance policy, and whether the 13 F-4 subcodes are intentionally unsourced.
- **Serving-channel terms:** whether they bind OpenRouter-mediated calls (ESA-02), and the Gemma 4 licence terms.
- **The fifth module** in the orchestrator's 77/82 local `fc896c2` run, and why the fix agent's later run passed 83/83 (§0.2).
- **How F1–F8 behave in production after deploy.** In particular: the visibility change in ESA-09b, and the `LAW_API_BASE_URL` and plaintext-retry checks in ESA-32a and ESA-32b. The fixes are VERIFIED offline only.
- **New code on `fc896c2`:** the R3 checklist modules (`checklist_*.py`, migration 0002), the manual reader, the search-first home and the immigration-checklist data were not audited by any note.

## 11. Related documents

- [00 — Executive summary](00-executive-summary.md)
- [04 — Official API capability matrix](04-official-api-capability-matrix.md)
- [05 — Legal intelligence architecture](05-legal-intelligence-architecture.md): the decisions that build on §3.
- [06 — Temporal law and source identity](06-temporal-law-and-source-identity.md): addresses ESA-01 and ESA-12.
- [07 — Evidence verification design](07-evidence-verification-design.md): addresses ESA-09b and ESA-10b.
- [11 — Dataset governance](11-dataset-governance.md) and [12 — Evaluation methodology](12-evaluation-methodology.md): address ESA-23.
- [15 — Security and deployment](15-security-and-deployment.md): the SEC register this register maps to.
- [16 — Validation results](16-validation-results.md)
- [17 — Mission 002 plan](17-mission-002-plan.md)
