# Model Priority, Cooldown, and Optional Ollama Fallback Scaffold (2026-05)

## Purpose

This note records the Paradiso AI provider behavior for the May 2026 model-priority update. The goal is to keep general immigration guidance useful when free online OpenRouter candidates are temporarily unavailable, without silently switching to an unapproved provider or inventing immigration content.

## Why free OpenRouter candidates can all fail

OpenRouter `:free` models can be unavailable because the upstream provider is rate-limited, overloaded, temporarily down, or has no healthy upstream instances. A single request can therefore see only retryable failures such as HTTP 429 or 503 across every configured candidate.

## New default priority

The built-in default ordered candidate list is now:

1. Nemotron Ultra — `nvidia/nemotron-3-ultra-550b-a55b:free`
2. Gemma — `google/gemma-4-31b-it:free`
3. Kimi — `openai/gpt-oss-120b:free`
4. Llama — `google/gemma-4-31b-it:free`

`OPENROUTER_MODEL` remains the primary model and is resolved first, then the comma-separated `OPENROUTER_MODEL_CANDIDATES` list is de-duplicated while preserving order. Random routing identifiers such as `openrouter/auto` or `openrouter/free` are surfaced as candidate warnings because Paradiso needs auditable model behavior.

## Cooldown behavior

Retryable per-model failures mark that model as cooling down in memory for `OPENROUTER_MODEL_COOLDOWN_SECONDS` seconds. Retryable failures include 429 rate limits, 503/no healthy upstream, temporary provider unavailability, and provider timeout classifications.

During cooldown, later requests skip the cooling model and try the next configured candidate. If all candidates are cooling down, Paradiso does **not** hammer the upstream again; it skips directly to the deterministic fallback path (or to an explicitly enabled fallback provider first). Cooldown state is process-local memory only and is cleared by process restart.

`/health` exposes non-secret cooldown fields: `cooling_down_models`, `model_cooldown_seconds`, and `cooldown_enabled`.

## Deterministic fallback answer behavior

When all OpenRouter candidates fail and no enabled fallback provider succeeds, Paradiso returns a normal answer envelope containing a concise `source_aware_preparation_note`. The fallback is generated from existing request/status/source metadata such as the question text, selected language, detected visa status, question type, answer-quality mode, source confidence, official-confirmation questions, related statuses, manual/law grounding state, and source availability.

The fallback does not invent document lists and does not claim final eligibility, approval, permission, or denial. It is designed to be copy-safe and mobile-readable, with metadata such as `deterministic_fallback_answer_used`, `llm_unavailable`, `provider_unavailable`, `fallback_answer`, and `copy_safe_answer`.

## Pre-LLM status and intent preservation

Status and intent detection run before provider calls. Explicit request `visa_code` values are treated as high-confidence status metadata, and explicit free-text status codes such as H-1, D-2, F-4, F-6, G-1, and E-7 are preserved even if every LLM candidate fails. Provider failure must not erase `visa_code_detected`, `task_type_detected`, `question_type_detected`, `risk_level_detected`, `answer_quality_mode`, `source_confidence_level`, `official_confirmation_questions`, or `related_statuses_not_sources`.

Law grounding in audit/enabled mode is attempted independently when the question warrants it. If law grounding is unavailable, deterministic fallback still renders and does not use law grounding to invent required documents.

## Optional Ollama scaffold

Ollama fallback is a future optional private fallback path only:

- disabled by default;
- no live Ollama server required;
- mock-tested only in CI;
- attempted once only after all OpenRouter candidates fail and `ENABLE_OLLAMA_FALLBACK=true`;
- falls back to the deterministic preparation note if Ollama fails or times out.

If Ollama succeeds, response metadata includes `ollama_fallback_used`, `ollama_model`, `final_model`, and `llm_provider: ollama`. If it fails, `ollama_error_type` is one of `ollama_unavailable`, `ollama_timeout`, `ollama_bad_response`, or `ollama_disabled`.

## Why Ollama is not enabled in production yet

Production Ollama would require separate compute, private networking, capacity planning, timeout management, security review, and quality evaluation for Korean immigration guidance. A public Ollama endpoint must not be exposed. Until those requirements are satisfied, production remains OpenRouter-first with deterministic fallback as the final safety net.

## Railway env vars

Recommended production posture:

```env
OPENROUTER_MODEL=nvidia/nemotron-3-ultra-550b-a55b:free
OPENROUTER_MODEL_CANDIDATES=nvidia/nemotron-3-ultra-550b-a55b:free,google/gemma-4-31b-it:free,openai/gpt-oss-120b:free,google/gemma-4-31b-it:free
OPENROUTER_MODEL_COOLDOWN_SECONDS=300
ALLOW_GROQ_FALLBACK=false
LAW_GROUNDING_MODE=audit
```

Optional future private Ollama variables:

```env
ENABLE_OLLAMA_FALLBACK=false
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen3:8b
OLLAMA_TIMEOUT_SECONDS=20
```

## Smoke commands

Local no-provider/static smoke:

```bash
python3 scripts/smoke_ai_live_quality.py --help
python3 scripts/smoke_ai_live_quality.py
```

Deployed smoke when network and deployment access are available:

```bash
BACKEND_URL="https://web-production-14f9a.up.railway.app" python3 scripts/smoke_ai_live_quality.py
```

The smoke report includes candidate order, cooling models, skipped models due to cooldown, final provider/model, Ollama enabled/used status, deterministic fallback status, answer-quality mode, source confidence, detected visa code, question type, and warning repetition count.

## Known limitations

- Free online models can still be rate-limited or unavailable.
- Cooldown is in-memory only and resets on process restart.
- Ollama needs separate compute if enabled later.
- Local models may be slower or lower quality than hosted models.
- Production Ollama requires private networking and security controls.
- Deterministic fallback is limited preparation guidance, not an AI-generated legal answer.

## Safety note

AI answers, deterministic fallback answers, local model fallback, law grounding, manual guidance, route explanations, deadline calculations, and checklists are preparation aids only and do not determine eligibility, approval, or final required documents.
