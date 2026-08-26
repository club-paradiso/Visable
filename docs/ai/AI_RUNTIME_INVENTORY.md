# Visable AI Runtime Inventory

Every AI/LLM-dependent path in Visable, derived from the code on `origin/main`
at the time of the 2026-08 AI architecture pass — not from earlier design docs.

**Read this before trusting any older AI document in this repository.** Several
prior notes describe states that are no longer true (most consequentially
"0 approved manual editions", which stopped being true in PR #566's lineage).

Method: repository-wide sweep for provider hosts, credential names, model
identifiers, completion/streaming call sites, prompt construction and SSE
handling across Python, JavaScript, inline HTML scripts, shell scripts,
workflows, tests and deployment configuration.

---

## 1. Summary

| | Count |
|---|---|
| HTTP endpoints that call an LLM | 8 |
| Endpoints that only *sound* AI-backed but are deterministic | 1 |
| Distinct provider transports | 4 (OpenRouter, Groq, Ollama, NVIDIA NIM) |
| Provider transports reachable in production | 2 (OpenRouter, Groq) |
| Frontend files that call an LLM provider directly | **0** |
| Features that had their own provider routing before this pass | 1 (nationality coach) |
| Endpoints that were **completely broken** before this pass | **2** |

---

## 2. Feature inventory

### 2.1 Waymaker — `POST /api/ask`

| Field | Value |
|---|---|
| Frontend | `ai.html` (`API_BASE + /api/ask`), `index.html` |
| Source | `backend/paradiso_backend.py` |
| Purpose of AI | Final answer synthesis over retrieved evidence |
| Deterministic parts | Source grounding, law grounding, answer-shape gate, safety guardrails, citation guard, deterministic fallback note |
| LLM parts | Final answer generation only |
| Provider | OpenRouter; Groq only if `ALLOW_GROQ_FALLBACK`; Ollama only if `ENABLE_OLLAMA_FALLBACK` |
| Model selection | `resolve_answer_mode_models(mode)` — fast/basic chains |
| Fallback | Candidate chain → cooldown skip → provider-family → deterministic note |
| Timeout | `OPENROUTER_TIMEOUT_SECONDS` (default 60) |
| Streaming | Yes (SSE), OpenRouter only |
| Grounding | Required; answer is gated when evidence is thin |
| Safety sensitivity | **Highest** — legal/immigration consequences |
| Personal data | User questions may contain personal facts; not logged by default |
| Input contract | `message` \| `query` \| `question` (aliases preserved) |
| Tests | `test_paradiso_backend`, `test_ai_answer_pipeline_contract`, `test_evidence_backed_answer_gates`, `test_waymaker_*`, `test_e7_workplace_change_law_grounding` |
| Status | **WORKING** (code + mock verified; needs live verification) |

### 2.2 Unified Search AI Overview — `POST /api/search/unified/ai-overview`

| Field | Value |
|---|---|
| Frontend | `assets/js/unified-search.js` |
| Purpose of AI | Optional summary over deterministic search results |
| Deterministic parts | `run_unified_search` (always independently available), statute citation guard |
| Provider | OpenRouter |
| Fallback | Quiet `unavailable`; organic results untouched |
| Streaming | Yes, separate `/stream` endpoint |
| Grounding | Hard-required: model may only speak from retrieved cards |
| **Architectural problem found** | **Unpacked the completion result dict as a 2-tuple → `ValueError` on every call → a broad `except` reported a healthy provider as `unavailable`. The feature had never produced output in production.** Also read non-existent `provider`/`model` keys, and called `_classify_openrouter_error(exc)` with an exception in the `status` slot so every failure read `unknown_provider_error`. |
| Tests before | Only the no-provider branch — which returns before the model is called |
| Tests now | `test_ai_endpoint_success_paths.UnifiedAiOverviewSuccessTests` |
| Status | **FIXED — WORKING** (mock + local end-to-end verified) |

### 2.3 Employment interpretation — `POST /api/employment/interpret`

| Field | Value |
|---|---|
| Frontend | `index.html` employment reporting helper |
| Purpose of AI | Normalize a free-text job description into structured facts |
| Deterministic parts | `employment_nl.validate_extraction` (drops codes, unknown fields, determination sentences), the deterministic analyzer that produces the actual KSCO/KSIC codes |
| **Never does** | Produce a classification code, decide employment permission, or fabricate a visa code |
| Fallback | Guided deterministic analyzer, with the raw sentence always passed through |
| **Architectural problem found** | **Same dict-unpack defect as 2.2. Never produced an extraction in production.** |
| Tests now | `test_ai_endpoint_success_paths.EmploymentInterpretSuccessTests` |
| Status | **FIXED — WORKING** (mock + local end-to-end verified) |

### 2.4 Nationality / naturalization coach — `POST /api/nationality-coach`

| Field | Value |
|---|---|
| Frontend | `assets/js/nationality-interview-hub.js` |
| Purpose of AI | Interview practice feedback; nationality-services general guidance |
| **Never does** | Fabricate biography, invent supporting facts, or claim an adjudication outcome |
| **Architectural problem found** | Carried its **own** Groq-first → OpenRouter routing: one model per provider, no candidate chain, no cooldown, no error taxonomy, and it ignored `ALLOW_GROQ_FALLBACK` entirely. A deployment on strict OpenRouter-first still answered nationality questions from an ungoverned model, and a single 429 meant no feedback at all. |
| Now | Shared runtime, `NATIONALITY_COACH` task role, OpenRouter-first with Groq as a working provider-family fallback |
| Tests before | **None** |
| Tests now | `test_nationality_coach` (14 tests: routing matrix, shared cooldown, safety invariants) |
| Status | **FIXED — WORKING** |

### 2.5 Legal research — `POST /api/legal/research` and `/stream`

| Field | Value |
|---|---|
| Purpose of AI | Optional source-grounded synthesis, strictly after retrieval |
| Deterministic parts | Issue extraction, source planning, law/precedent retrieval, source-strength labels — the deterministic result is always the fallback |
| Validation | `legal_synthesis.validate_synthesis` rejects phantom sources, fabricated statute/case numbers, final-advice language, raw HTML |
| Status | **WORKING** (synthesis is `deterministic` without a provider, by design) |

### 2.6 Enforcement Outcome Intelligence — `/api/enforcement/extract`, `/analyze`

| Field | Value |
|---|---|
| Deterministic layer | `enforcement_rules.calculate_legal_baseline` — statutory range, primary |
| Evidence layer | `enforcement_evidence.retrieve_enforcement_evidence` |
| AI layer | Fact extraction + bounded outcome explanation; heuristic extraction is the fallback |
| Provider contract | Correctly reads the result dict (`isinstance(raw, dict) and "ok" in raw`) — this call site did **not** have the 2.2/2.3 defect |
| Probability | No AI-manufactured probability; unavailable baseline yields `unavailable_prediction` |
| Status | **WORKING — evidence/deterministic-first** |

### 2.7 Job code keywords — `POST /api/jobcodekeywords`

| Field | Value |
|---|---|
| **Purpose of AI** | **None.** `_extract_keywords` is regex tokenization + a stopword list |
| Status | **NOT LLM-BACKED** — the name suggests otherwise; documented here so nobody assumes an AI dependency that does not exist |

### 2.8 NVIDIA NIM — experimental

| Field | Value |
|---|---|
| Source | `backend/services/providers/nvidia_nim.py` |
| Wired to `/api/ask` | **No** |
| Posture | Fail-closed: disabled by default, requires explicit data classification, refuses personal/sensitive data unless separately enabled, `production_ready: false` |
| Status | **NOT IN PRODUCTION** — correctly gated |

### 2.9 Other paths checked and found clean

* `backend/moonshot_backend_fastapi.py` — legacy reference backend, no LLM, not wired to production.
* Ollama — disabled by default, reached only after OpenRouter fails, never during `/health`.
* Frontend — **no file calls a provider directly**; every AI call goes through a Visable endpoint. Enforced by `check_ai_architecture.py`.

---

## 3. Root causes found

1. **A mapping mistaken for a tuple, twice.** `_openrouter_complete_with_candidates` returns a 16-key dict. Two call sites wrote `text, meta = await ...`, which unpacks the *keys* and raises `ValueError`. A broad `except Exception` converted that into `provider_error`. Both features were 100% dead and reported the failure as a provider outage.

2. **Tests that asserted only the degradation branch.** Both endpoints had tests — for the no-provider path, which returns before the model is called. Asserting "it degrades safely" without asserting "it works" cannot distinguish graceful degradation from permanent breakage.

3. **CI ran 5 of 47 backend test modules.** The other 42 were committed, maintained, and never executed. Thirteen were failing on main while `check_repo.sh` printed "Success".

4. **Provider fragmentation.** The coach had its own routing, its own provider order, and its own (absent) error handling, and ignored the deployment's fallback policy.

5. **Six copies of the backend origin**, each with its own localhost logic.

6. **No AI readiness signal.** `/health` answered "is the web server alive?", which is a different question from "is the AI up?".

7. **Approved manual evidence unreachable in production.** The registry holds 2 human-approved editions, but the FTS index that surfaces them is a build artifact that nothing builds at deploy time. Nothing reported this.

---

## 4. Architecture after

```
                   frontend (no provider access, ever)
                                 |
                        Visable backend endpoints
                                 |
        +------------------------+------------------------+
        |                                                 |
  services.ai_runtime                          services.immigration_tools
  - AIErrorType taxonomy                       - EvidenceItem / EvidencePack
  - classify_provider_error                    - approval decided deterministically
  - ModelCooldownRegistry (shared)             - RETRIEVAL_FAILED != NO_RESULTS
  - TaskRole -> candidate chain                - MCP-ready tool registry
  - AIResult (dataclass, not a dict)                       |
  - AIRuntime candidate orchestration          existing deterministic services
        |                                      (manual / law / status / enforcement)
  provider transports (OpenRouter, Groq, Ollama)
```

---

## 5. Verification status

| Level | What it covers |
|---|---|
| **CODE VERIFIED** | Every item in this inventory read from `origin/main` source |
| **MOCK VERIFIED** | 8 AI endpoints exercised with mocked providers, success *and* failure paths |
| **LOCAL END-TO-END VERIFIED** | Real application, real HTTP, stubbed transport: 15 PASS / 1 DEGRADED / 0 FAILED, `LIVE AI VERIFIED` |
| **LIVE PRODUCTION — NOT VERIFIED** | The deployed backend and `openrouter.ai` are unreachable from the environment this pass ran in (network policy returns 403 on CONNECT). See `AI_PRODUCTION_RUNBOOK.md` for the exact operator commands. |
