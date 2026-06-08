# Paradiso AI model role policy

Date: 2026-06

## Decision

Paradiso separates model roles instead of treating one free OpenRouter model as
the whole immigration assistant.

| Role | Default model | Purpose |
| --- | --- | --- |
| Router / query classification | `google/gemma-4-31b-it:free` | Low-risk language detection, status-code extraction, task classification |
| UI / site translation | `google/gemma-4-31b-it:free` | Language-setting translation and multilingual UI support |
| Final Paradiso answer | `nvidia/nemotron-3-ultra-550b-a55b:free` | Core visa/status answer generation from the prepared source/evidence packet |
| Final fallback 1 | `nvidia/nemotron-3-super-120b-a12b:free` | Retryable primary-model fallback |
| Final fallback 2 / verifier family | `openai/gpt-oss-120b:free` | Structured answer audit / source-boundary checking |
| Last final fallback | `google/gemma-4-31b-it:free` | Last-resort free-model fallback when stronger free candidates fail |
| Chinese-language route | `deepseek/deepseek-r1-0528:free` | Chinese-language questions/translation only |
| Chinese fallback | `qwen/qwen3-next-80b-a3b-instruct:free`, `moonshotai/kimi-k2.6:free` | Chinese-language fallback only |

## Rationale

Gemma is useful, but Paradiso should not make it the default final legal/status
answer owner. Core answers need deeper multi-step reasoning and stronger
source-boundary discipline. Therefore the default final-answer chain moves to
Nemotron first, with gpt-oss reserved as the structured verifier / audit model.

China-origin model families are intentionally excluded from the default core
Korean immigration answer chain. They remain available for Chinese-language
routes where their language coverage is useful.

## Non-goals

This PR does not change visa/status data, legal content, source mappings, search
behavior, or official disclaimers. It only clarifies and wires the model-role
policy used by the backend defaults and operator-facing configuration.
