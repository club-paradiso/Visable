# API/provider architecture audit — July 2026

Audit date: 2026-07-02. Runtime secrets were not inspected. Operator-confirmed fact: NVIDIA key exists, enable flag false. No UI, visa/status, generated data, deployment, or Fable branch changes.

## Inventory

| Integration | Env/status | Timeout/retry/cache/failure | Visibility, tests, risk/action |
|---|---|---|---|
| OpenRouter | Key + model/candidate/tier/token/cooldown vars; primary `/api/ask` when keyed. Runtime key unknown. | 60s/call; explicit candidates; 429/503/timeout retry and 300s process-local cooldown; SSE/buffered; no completion cache. Retry exhaustion gives deterministic note; nonretryable gives safe 503. | Model/fallback shown; extensive mocks. Medium: keep primary, review privacy/catalog and add request-level deadline. |
| Groq | Key/model; `/api/ask` fallback requires `ALLOW_GROQ_FALLBACK=true` (default false). Nationality coach is separately Groq-first. | 60s ask, 20s coach; no cooldown/cache. | Configured vs allowed now separate. Medium: preserve restriction; move to sanitized adapter before expansion. |
| NVIDIA | Nine vars; operator says key exists. Disabled, experimental, not `/api/ask`, not production ready. | Scaffold 45s; no retry/cache/runtime route; mode+explicit data classification before transport. | Non-secret health; mock-only tests. High if user-enabled, low while disabled; internal QA only. |
| Open Law | `LAW_API_OC` preferred, legacy key, mode/timeout/TTL/endpoints. Secret presence unknown. | 8s; host scheme fallback; request-local de-dup. Enabled without credential becomes effective disabled. | Granular verification/warnings; large mocks. Medium: keep audit until live validation supports enabled. |
| Legal evidence | Shares OC; optional appeal targets. Supplementary and issue-gated; `prec` confirmed, other targets uncertain. | 8s; 2 retries/0.5s exponential backoff; in-memory 86400s success cache; 2 fast/3 basic cases. | Separate metadata/caution; no wholesale body. Medium-high: never primary for current requirements. |
| Public data | Key/base/visa/job placeholders; production endpoint unknown. | 8s, no retry/cache, graceful unavailable. | No dedicated health; medium: remain off until schema/terms/query minimization verified. |
| DB/Supabase | DB URL/Supabase URL/service key. | Only configuration booleans found in inspected backend. | Low now; add adapter/connectivity health only for a real use case. |
| Frontend API | `window.PARADISO_BACKEND_URL`, else Railway URL; local/file empty base. | 75s browser ceiling; SSE ask. | Generic localized errors, source/model badges. Medium: deploy-configure later; provider must not imply source confidence. |

Secrets are documented, not proven present, except operator-confirmed NVIDIA. `.env.example` now leaves secret-equivalent `LAW_API_OC` blank. Static scan finds no hard-coded provider keys or obvious key logging. CORS defaults `*` and should be restricted in production. Nationality-coach exception text should eventually use shared sanitization.

## 1–3. Provider chain and policies

`/api/ask`: explicit OpenRouter model chain → Groq only if explicitly allowed → optional private Ollama → deterministic source-aware note for retryable exhaustion. Without OpenRouter, Groq is selected only with key plus opt-in. NVIDIA is absent. Random OpenRouter routing is forbidden. Nationality coach separately uses Groq → OpenRouter → local frontend heuristic.

## 4–5. Law and legal evidence

Law `disabled|audit|enabled` has a distinct effective mode. Audit retrieval never becomes “verified.” Manuals/HiKorea/office sources control operational documents/fees/deadlines. Law supplies legal context. Case law/adjudication is separate, bounded, fact-specific, supplementary, and cannot establish current administrative requirements.

## 6. Health visibility

Additive `provider_status` now reports:

- `openrouter.configured/enabled`
- `groq.configured/fallback_allowed`
- `law_grounding.mode/effective_mode`
- `legal_evidence.configured`
- `nvidia_nim.configured/enabled/allowed_modes/personal_data_allowed/production_ready=false`

Health is configuration-only and never returns keys, OC, headers, or live raw errors.

## 7. Timing

Browser 75s versus sequential 60s provider attempts can cause client abort before full chain exhaustion. Cooldown is process-local. Law is 8s with request cache; legal evidence adds bounded retry and TTL cache. Recommend an overall backend request deadline and cancellation propagation.

## 8–10. Coupling and confidence risk

`paradiso_backend.py` combines routing, HTTP, classification, cooldown, SSE, source metadata, and endpoints; nationality coach duplicates a provider loop. Flat `providers.*` could conflate configured and active; structured status fixes the audited providers. Model badges near source panels can imply model quality raises authority. It never does: only verified manual/law evidence determines confidence.

## 11. Future adapter

```python
provider_name; configured; enabled; allowed_modes; personal_data_allowed
chat_completion(); stream_chat_completion(); health_check(); sanitize_error(); metadata()
```

Migrate incrementally behind current contracts. Required invariants: fail closed on unknown experimental-provider data classification; explicit provider-family fallback; bounded cancellation; no raw errors/secrets; provider output cannot increase source confidence; experimental use is separately visible.

## Failure audit

| Scenario | Result/gap |
|---|---|
| No provider | Safe 503 `no_llm_provider_configured`, but not full deterministic official-confirmation guidance: remaining gap. |
| OpenRouter configured/timeout/429/503 | Mocked chain, retry/cooldown, safe deterministic exhaustion. |
| Groq disabled/enabled | Explicit default-off gate tested; do not weaken. Direct Groq-only failure is less graceful than OpenRouter exhaustion. |
| NVIDIA configured+disabled / mode denied / unknown or sensitive data | Structured health; all blocked before transport and mock tested. |
| Law disabled/audit/enabled without credential | Distinct effective status; no false verification. |
| Legal evidence unavailable | Non-fatal supplementary state. |
| All providers unavailable | Retryable OpenRouter path is safe; no-provider and direct-Groq paths need unified deterministic fallback. |
