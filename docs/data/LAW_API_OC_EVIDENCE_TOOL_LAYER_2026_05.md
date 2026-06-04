# Law API OC + Evidence Tool Layer (2026-05)

## 1. Purpose

This change strengthens Paradiso's Korean visa/residence guidance by grounding
answers in official law/manual evidence more actively, while keeping the system
honest about what it can and cannot confirm. It adds:

- explicit `LAW_API_OC` support for the National Law Information Open API
  (open.law.go.kr), with `LAW_API_KEY` kept only as a backward-compatibility
  fallback;
- a small, internal, MCP-like **law tool layer** (`backend/services/law_tools.py`)
  with typed inputs, normalized outputs, a mockable HTTP boundary, and stable
  error types;
- deterministic **law query planning** keyed to the detected status / question
  type;
- a structured **evidence pack** that keeps manual evidence, law evidence,
  related (comparison) statuses, and source-confidence metadata strictly
  separate;
- answer-prompt + source-confidence integration so weak grounding produces
  cautious, source-aware wording instead of invented legal conclusions.

This is **not** a general legal chatbot, **not** a public MCP server, and does
**not** change the OpenRouter model policy, enable Ollama, or add paid model
fallback.

## 2. User configuration

Register at <https://open.law.go.kr/LSO/main.do> and use your OC value.

Railway env posture:

```
LAW_API_OC=paradiso
LAW_API_KEY=<existing Railway law API value, keep UNCHANGED>
LAW_GROUNDING_MODE=audit
```

- `LAW_API_OC` is **preferred**. `LAW_API_KEY` is a **fallback only**.
- Do **not** overwrite or remove the existing Railway `LAW_API_KEY`; just add
  `LAW_API_OC=paradiso` alongside it.
- If both are set, `LAW_API_OC` is used as the Open Law API `OC` parameter.
- If only `LAW_API_KEY` is set, it is used and a non-secret
  `LAW_API_OC_RECOMMENDED` warning is surfaced.
- If neither is set, law grounding degrades gracefully to unavailable.

## 3. Security rules

- Backend-only: the OC / API-key value is never sent to the frontend.
- `/health` exposes booleans only — `law_api_configured`,
  `law_api_oc_configured`, `law_api_key_fallback_configured`,
  `law_api_credential_source` (the env-var NAME, e.g. `LAW_API_OC`), and
  `law_grounding_mode`. It never exposes the value.
- Debug responses expose the same flags plus the deterministic plan; never the
  OC/key.
- Source URLs are sanitized at the tool boundary (`_sanitize_url` strips `OC` and
  any credential-ish parameter) before they reach any caller, log, or the
  evidence pack.
- Shipped HTML contains no OC/API-key value or `OC=` credential parameter. The
  non-secret status label `LAW_API_KEY_MISSING` is a warning code, not a key.

## 4. MCP-like design principles (reflected, not copied)

Inspired only by the operating principles discussed previously
(`korean-law-mcp`, `dot-studio`, `korean-privacy-terms`) — no third-party code
is used and no public MCP server is shipped:

- **Typed internal tools** — `search_laws`, `get_law_detail`,
  `search_admin_rules`, `search_law_terms` take typed inputs and return
  deterministic, normalized dicts.
- **Orchestration in explicit stages** — question → intent/status detection →
  tool plan → manual/law retrieval → normalization → evidence pack → answer
  prompt → source-aware final answer.
- **Source-of-truth separation** — manual evidence stays primary for
  documents/procedures; law evidence is context for legal/activity-scope/
  status-change concepts; the two are never collapsed.
- **Evidence pack** — a compact, normalized, secret-free structure (not a raw
  API dump) is what the answer prompt receives.
- **Graceful failure** — a law API failure downgrades source confidence
  (`source_limited` / `source_unavailable`) and records a typed error; it never
  crashes `/api/ask` and never hallucinates.
- **Testability** — the HTTP boundary is a single injectable `transport`; CI
  mocks it and never needs live Open Law API, OpenRouter, Railway, HiKorea, or
  data.go.kr access.

## 5. Manual vs law API roles

| Concern | Primary source | Law API role |
|---|---|---|
| Required documents / checklists | Manual / HiKorea / competent office | none — never invent a checklist from law-only grounding |
| Procedures, fees, deadlines | Manual / official | supporting context only |
| Legal basis, activity scope, 체류자격외활동 | Law evidence | primary context |
| Status-change framework | Manual route + law | law supports the framework |
| Final eligibility / permission | **No source** | never claimed — route to 1345 / HiKorea / office |

## 6. Law query planning

`plan_law_queries(question, visa_code, task_type, question_type, max_queries)`
returns a small (default 3-5), deterministic set of high-signal Korean queries
chosen from category templates keyed to the detected question type and status:

- activity-on-status: `출입국관리법 체류자격외활동 활동범위`, etc.
- working-holiday (H-1): `관광취업 H-1 체류자격 활동범위`, etc.
- student activity: `유학 어학연수 체류자격외활동`, `체류자격 변경 유학 D-2 D-4`.
- employment: `취업활동 근무처 변경 근무처 추가 신고`.
- overseas Korean / F-4: `재외동포 국내거소신고 체류자격 변경`,
  `재외동포의 출입국과 법적 지위에 관한 법률 …`.
- family/marriage, humanitarian/G-1, refugee, short-term, reporting/deadline,
  urgent/risk, nationality — each has its own template set.

The plan is preserved verbatim in the evidence pack and debug metadata. Raw API
payloads are never passed to the LLM; the API is not called for casual
non-immigration chat.

### H-1 summer-semester example (Part 8)

Question: *"Can I take summer semester course in Korean universities even though
I have a H-1 visa?"*

- `visa_code` = H-1, `question_type` = `activity_on_status`, risk = medium.
- planned queries include `활동범위`, `체류자격외활동`, `체류자격 변경`, `관광취업`.
- D-2 / D-4 are `related_statuses_not_sources` — **not** direct H-1 evidence.
- `answer_quality_mode` = `source_limited` → the answer leads with source-limited
  caution: *"Paradiso cannot confirm from currently verified sources that an H-1
  holder may take a credit-bearing university summer course in Korea."* A casual,
  non-credit cultural program *"may be assessed differently, but official
  confirmation is required."*

## 7. Evidence pack schema

`build_law_evidence_pack(...)` returns (secret-free, JSON-serializable):

| Field | Meaning |
|---|---|
| `direct_manual_sources` | manual sources that directly answer the question |
| `related_manual_sources` | related manual sources |
| `law_sources` | normalized law candidates (name, id/serial, source_type) |
| `planned_law_queries` | the deterministic plan |
| `law_queries_attempted` | queries actually issued |
| `law_grounding_status` | `not_attempted` / `disabled` / `unavailable` / `used` |
| `manual_grounding_status` | `present` / `absent` |
| `related_statuses_not_sources` | comparison statuses to verify (e.g. D-2/D-4) |
| `source_confidence_level` | `high` / `moderate` / `low` / `none` |
| `answer_quality_mode` | `source_confirmed` / `source_assisted` / `source_limited` / `source_unavailable` / `generic_advisory` |
| `official_confirmation_questions` | canonical (EN) confirmation questions |
| `official_confirmation_questions_localized` | ko/en localized questions |
| `risk_level`, `source_status`, `target_status`, `evidence_summary`, … | planning + compact prompt summary |

## 9. Expanded scenario coverage

`backend/tests/test_law_grounding_scenarios.py` covers families A-L (42 scenarios)
plus cross-cutting invariants: H-1/working-holiday, D-2/D-4 study, D-10 job
seeking, E-7 employment, F-4 overseas Korean, F-6 marriage edge cases, G-1
humanitarian, short-term statuses, registration/reporting/deadlines, overstay/
urgent risk, and nationality/refugee topics. Tests assert intent detection,
planned queries, evidence-pack construction, source-confidence mode, and
direct-vs-related semantics — never exact LLM prose or invented legal
conclusions.

## 10. Debug endpoint behavior

`POST /api/debug/law-grounding` (`{question, visa_code?, status?}`) returns the
non-secret grounding context plus an `evidence_pack` and a `debug` block: mode,
the configured flags, detected status, question type, planned law queries,
`law_api_attempted`, normalized evidence count, `law_grounding_status`,
`source_confidence_level`, and the error type if any. `GET
/api/debug/law-grounding/preflight` is a no-call readiness probe. Both are safe
in audit mode and never expose the OC/key.

## 11. Smoke commands

```
BACKEND_URL="https://web-production-14f9a.up.railway.app" python3 scripts/smoke_ai_live_quality.py --json
BACKEND_URL="https://web-production-14f9a.up.railway.app" bash scripts/smoke_law_grounding.sh
```

The smoke harness reports `law_api_oc_configured`,
`law_api_key_fallback_configured`, `law_grounding_mode`, planned law queries,
`law_grounding_attempted`, `law_grounding_status`, law evidence count,
`source_confidence_level`, `answer_quality_mode`, `risky_phrase_warnings`,
`final_model`, and `deterministic_fallback_answer_used` — without printing
secrets. CI does not fail because the live law API is unreachable; CI uses mocks.

## 12. Tests added

- `backend/tests/test_law_tools.py` — config/security, typed tools, stable error
  types, evidence pack, source-confidence modes, risky-phrase guard.
- `backend/tests/test_law_grounding_scenarios.py` — 42 immigration scenarios +
  language/frontend checks.
- A precondition fix in `backend/tests/test_openrouter_model_candidates.py`
  (`DeterministicFallbackAndOllamaTests` now sets `LAW_GROUNDING_MODE=audit`,
  which its `law_grounding_attempted=True` assertion requires).

## 13. Validation results

`python3 -m pytest backend/tests -q` → all tests pass (700+), no live external
access required. JSON validators, coverage checks, `check_i18n.js`, and
`check_ai_shell_semantics.js` pass. See the PR description for the captured run.

## 14. Known limitations

- The law API may not answer highly specific scenario questions directly.
- Official determination still requires **1345 / HiKorea / the competent
  immigration office**.
- Law grounding is **context, not final adjudication**.
- Manual absence must remain visible (it downgrades source confidence).
- data.go.kr is **not** the main target of this PR.

## 15. Safety note

> Paradiso cannot determine final eligibility, permission, or required documents.
> Users must confirm case-specific outcomes with 1345, HiKorea, or the competent
> immigration office.
