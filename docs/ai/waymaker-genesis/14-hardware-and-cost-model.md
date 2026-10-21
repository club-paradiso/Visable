# 14 — Hardware and cost model

Status: **RESEARCHED ONLY.** This document changes no code, spends no money and
ran no model. No GPU was rented or used. Every price below was read on
**2026-10-19** (UTC 03:57–04:50) by the cost researcher and its adversarial
verifier, and is recorded with its source URL in
[research-notes/cost.md](research-notes/cost.md). Where the verifier corrected
the researcher, the verifier's figure is used here. Volumes are scenarios, not
measurements: Waymaker records no request or token counts (§2.5).

Mission 001 "Waymaker Genesis". Audited code: origin/main `0713370`. The
worktree is now at `fc896c2`, and
`git diff --stat 0713370 HEAD -- backend/services/model_policy.py
backend/services/ai_runtime.py backend/paradiso_backend.py lib/ api/
backend/services/providers/ scripts/check_model_catalog.py` is empty, so every
`[CODE …]` line cited here is the same on `fc896c2` (re-checked 2026-10-20,
VERIFIED). `lib/` and `api/` are outside the sparse checkout and were read with
`git show HEAD:<path>`.

Conventions. Prices are USD list prices as shown on the cited page on
2026-10-19, before tax, regional premiums and negotiated discounts. Token prices
are per 1M tokens. A month is 730 GPU-hours or 30 days of a daily cap. "Per
question" means the standard profile of 5,000 input and 1,000 output tokens
(§3) unless a row says otherwise. Evidence tags: `[CODE path:line]`,
`[LIVE …]` (a live GET or run), `[DOC url, accessed 2026-10-19]` (a primary
page), `[WEB url, accessed 2026-10-19]` (a secondary source). Status words:
VERIFIED, OBSERVED, README-ONLY, INFERRED, UNVERIFIED, UNKNOWN. All arithmetic
is INFERRED, applied to the unit prices it names.

> **Open-source frameworks do not make GPUs free.** vLLM, SGLang, TGI, Unsloth,
> Axolotl and PEFT are free software. A self-hosted or fine-tuned model still
> needs a GPU, billed per hour or per second, and the bill runs whether or not
> the GPU is answering questions. Open weights remove the per-token fee. They do
> not remove hardware, idle time, redundancy, storage, monitoring or engineering
> time. [DOC cost.md header] (§8 has the numbers.)

## 1. Findings

1. **Waymaker is built to spend $0 on AI, and almost does.** The code-default
   general chains are all OpenRouter `:free` ids. Production differs in one
   place: its `enforcement_structured` chain is overridden to **paid** ids,
   costing about $0.00015–$0.0012 per call, and that chain needs a positive
   credit balance (§2.2). OBSERVED (config), INFERRED (spend).
2. **The real limit is OpenRouter's free quota, not money.** Free ids allow 20
   requests/min and 50/day, or 1,000/day once at least 10 credits have been bought.
   Failed attempts count toward the cap. That puts a zero-spend ceiling of about
   **1,500 or 30,000 LLM calls a month**, and /api/ask, Quick Answer,
   enforcement and the nationality coach all share it (§2.3). VERIFIED (limits),
   INFERRED (monthly ceiling).
3. **A real /api/ask call sends about 3.6k–5.4k input tokens** with law
   grounding off, including the 2,186-char system prompt. Production runs with
   grounding on, so its prompts are larger. The planning figure is 5k in + 1k
   out (§3). OBSERVED + INFERRED.
4. **Paying for the same open models is cheap**: $0.0006–$0.0054 per question,
   or **$14 (Gemma 4 31B) to $54 (Nemotron 3 Ultra) for 10k questions a
   month**, plus OpenRouter's 5.5% credit fee (§4.1). VERIFIED prices.
5. **Frontier reasoning APIs cost about 14–40x more than paid Gemma 4 31B**:
   $0.020–$0.055 per question, or $200–$550 for 10k questions a month (§4.2).
   VERIFIED prices, INFERRED ratio.
6. **Self-hosting does not pay at Waymaker's plausible volumes.** One 24/7 GPU
   costs $264–$8,075 a month, and that bill is the same with no traffic at all.
   Break-even against the same open model's API is 0.41–2.5M questions a month
   (2.4–14.9B tokens) for 8B and 0.35–5.8M (2.1–34.6B tokens) for 31B. For
   31B that is at or beyond what one GPU can serve. Two GPUs for availability
   double every figure (§8). INFERRED.
7. **Experiments are cheap; data review is not.** One LoRA run costs $4–$54
   managed, or $3–$33 self-run on a rented GPU. Expert review of a legally safe
   Korean immigration dataset costs far more than GPU time (§6.3). INFERRED.
8. **$0 is not free of other costs.** NVIDIA's trial terms, linked by OpenRouter
   for its Nvidia `:free` provider, exclude production use, and Google's free
   tier uses content to improve its products. Whether those terms bind
   OpenRouter-mediated calls is UNVERIFIED (REQUIRES LEGAL REVIEW). If they do,
   moving user questions to paid open-model endpoints costs about $15–$57 a
   month at 10k questions (Pilot option A) (§2.4, §7.4).

## 2. Current spend posture

### 2.1 Code defaults

| Path | Default chain | max_tokens | Paid? | Evidence |
|---|---|---|---|---|
| /api/ask Basic | `nvidia/nemotron-3-ultra-550b-a55b:free` → `google/gemma-4-31b-it:free` → `nvidia/nemotron-3-super-120b-a12b:free` → `thinkingmachines/inkling:free` | 1,400 | no | [CODE backend/services/model_policy.py:31-37] [CODE backend/paradiso_backend.py:325] VERIFIED |
| /api/ask Fast | `google/gemma-4-26b-a4b-it:free` → `nvidia/nemotron-3.5-lightning:free` → `thinkingmachines/inkling-small:free` → `google/gemma-4-31b-it:free` | 900 | no | [CODE model_policy.py:99-105] [CODE paradiso_backend.py:326] VERIFIED |
| Router, translation | `google/gemma-4-31b-it:free` | – | no | [CODE model_policy.py:23-24] VERIFIED |
| Verifier | `nvidia/nemotron-3-super-120b-a12b:free` | – | no | [CODE model_policy.py:118] VERIFIED |
| Enforcement structured (Python) | `google/gemma-4-26b-a4b-it:free` → `nvidia/nemotron-3-super-120b-a12b:free` | 900 | no | [CODE model_policy.py:112-116] [CODE paradiso_backend.py:8415-8440] VERIFIED |
| Chinese-language route | `minimax/minimax-m3` + two `inclusionai/ling-3.0-*:free` | – | **yes**, but no caller outside model_policy.py | [CODE model_policy.py:120-124] VERIFIED |
| Quick Answer (Node, Vercel) | `google/gemma-4-31b-it:free`, `openai/gpt-oss-120b:free`, `meta-llama/llama-3.3-70b-instruct:free`; env can override | 400 | no | [CODE lib/waymaker-quick-answer-ai.js:18-34, 131] VERIFIED |
| Enforcement grounded AI (Node) | `openai/gpt-oss-120b:free`, `nousresearch/hermes-3-llama-3.1-405b:free`, `google/gemma-4-31b-it:free`, `meta-llama/llama-3.3-70b-instruct:free` | 1,800 | no | [CODE lib/enforcement-grounded-ai.js:13-18, 209] VERIFIED |
| Enforcement confirm (Node) | `google/gemma-4-31b-it:free` | 220 | no | [CODE api/enforcement/confirm.js:3, 130] VERIFIED |
| Groq fallback | `llama-3.1-8b-instant` | – | price UNKNOWN (groq.com/pricing showed no table) | [CODE paradiso_backend.py:345, 1222-1229] VERIFIED |
| NVIDIA NIM direct | `nvidia/nemotron-3-ultra-550b-a55b`, fail-closed, `ENABLE_NVIDIA_NIM_EXPERIMENTAL` off | 1,200 | not wired to /api/ask | [CODE backend/services/providers/nvidia_nim.py:1-58] VERIFIED |

[DOC cost.md §1]. The policy document says "Cost posture: free tier by default"
[DOC docs/ai/AI_PROVIDER_AND_MODEL_POLICY.md:81-85] README-ONLY.

**Waymaker serves no model itself.** Every model call goes to a hosted API.
The production `/health` snapshot reports `ollama: false`, NVIDIA NIM
`enabled: false`, and Groq `fallback_allowed: false`
[LIVE research-notes/live_health.json, GET 2026-10-19 03:37 UTC] OBSERVED. So
Waymaker has no GPU cost today. Railway and Vercel hosting were not priced
(UNKNOWN) and are left out of every total in this document.

### 2.2 Production differs from the code defaults

The saved `/api/health/ai` snapshot (GET by another agent at 03:37 and 04:19 UTC
on 2026-10-19; the copy is tracked as
[research-notes/live_health_ai.json](research-notes/live_health_ai.json) and was
re-read on 2026-10-20) shows:

- `taskRoleModels.enforcement_structured` = `openai/gpt-oss-20b`,
  `google/gemma-4-31b-it`, `openai/gpt-oss-120b`. All three are **paid** ids:
  $0.018/$0.09, $0.20/$0.40 and $0.15/$0.60 per 1M
  [LIVE GET https://openrouter.ai/api/v1/models, verifier ~04:35 UTC
  2026-10-19, 471 models]. `OPENROUTER_ALLOW_MODEL_ENV_OVERRIDES` is set.
  OBSERVED.
- The chain is wired. `_enforcement_ai_provider` calls
  `resolve_task_models(ENFORCEMENT_STRUCTURED)` with `max_tokens=900`
  [CODE paradiso_backend.py:8415-8440] VERIFIED.
- Cost per 4k-input/900-output call: $0.00015 (gpt-oss-20b), $0.00114
  (gpt-oss-120b) or $0.00116 (Gemma 4 31B). INFERRED. Call volume is
  UNKNOWN, so the monthly amount is UNKNOWN too.
- Paid calls need a positive OpenRouter balance. A negative balance returns
  402, even for free models [DOC https://openrouter.ai/docs/api-reference/limits,
  accessed 2026-10-19] VERIFIED.
- The verifier chain leads with `openai/gpt-oss-120b:free`, which is no longer
  in the catalog: a dead id [DOC cost.md §1, verifier row]. Law grounding is
  `enabled`. OBSERVED.

[DOC cost.md §0 item 1 (verifier), §1, verification pass claim 1]. Whether the
paid enforcement chain is intended is an open owner question (also SEC-14 in
[15](15-security-and-deployment.md) §3.15). For a true $0 posture, the Railway
override has to be removed or reset to the code-default `:free` chain
[DOC cost.md §11 scenario 1 (verifier)] INFERRED.

### 2.3 The free quota is the binding limit

| Limit | Value | Evidence |
|---|---|---|
| Free ids, per minute | 20 requests/min | [DOC https://openrouter.ai/docs/api-reference/limits, accessed 2026-10-19] VERIFIED |
| Free ids, per day | 50/day if fewer than 10 credits were ever bought; 1,000/day after at least 10 | same, VERIFIED. The limits page counts lifetime credit purchases. The verifier's fetch tool reported the higher ceiling starting at 9 credits (UNVERIFIED) |
| Failed attempts | count toward the daily cap | [DOC https://openrouter.ai/pricing, accessed 2026-10-19] VERIFIED (as summarised by the fetch tool) |
| Scope | the repo treats the bucket as account-wide (`free-models-per-day`, `free-models-per-min` in the 429 body) | [CODE backend/services/ai_runtime.py:346-365] VERIFIED. The limits page says extra keys or accounts do not raise limits, and also that some models have their own limits; the guide page cited for account-wide scoping does not say so (verifier) |
| Per-IP limits (per-user ceiling, not a volume) | /api/ask 8/min, 300/day; legal_research 4/min, 60/day; nationality_coach 6/min, 100/day; search_unified_ai 10/min, 200/day | [CODE paradiso_backend.py:5695, 7219, 7828, 8056] VERIFIED |

What the free quota allows at $0 (INFERRED): **about 1,500 LLM calls a month**
(below 10 credits ever bought) or **about 30,000** (10 or more). That is calls,
not questions. All of these draw on it: /api/ask, Quick Answer, Node
enforcement, the nationality coach, fallback attempts within a chain, CI
smoke traffic (3 /api/ask and 1 enforcement POST per push, per
[15](15-security-and-deployment.md) §3.15), and every attempt on a dead id.
Whether the account has ever bought 10 credits is UNKNOWN. If the paid
enforcement chain succeeds in production, credits were bought at some point,
but that does not show that the 10-credit threshold was reached (verifier open
question).

Catalog drift costs quota rather than cash. Five referenced ids were absent
from the catalog on 2026-10-19: `openai/gpt-oss-120b:free`,
`meta-llama/llama-3.3-70b-instruct:free`,
`nousresearch/hermes-3-llama-3.1-405b:free`, and the two
`inclusionai/ling-3.0-*` ids, which are absent even without `:free`
[LIVE GET https://openrouter.ai/api/v1/models, 2026-10-19: 471 models, 16
`:free`] VERIFIED. Three of them are Node defaults, unless a Vercel override
replaces them; the deploy env was not inspected. The owner's unpushed branch
`fix/waymaker-qa-2026-10-16` drops `thinkingmachines/inkling:free` from Basic
after "403 model_access_denied", so a listed free id does not prove access
[CODE git show fix/waymaker-qa-2026-10-16:backend/services/model_policy.py]
VERIFIED. [DOC cost.md §0 item 2, §1 catalog drift, §2]

Under load the per-minute cap binds too: two users at the /api/ask per-IP
limit (8/min each), plus fallback retries, can exhaust 20 RPM [DOC cost.md §9]
INFERRED.

### 2.4 What $0 does not buy

- **No SLA.** `nemotron-3-ultra:free` has one provider (Nvidia), with
  uptime_last_1d 96.7% in the researcher's fetch and 98.75% in the verifier's
  (~04:40 UTC). Both Gemma `:free` ids have one provider, Google AI Studio, at
  100%
  [LIVE GET https://openrouter.ai/api/v1/models/{id}/endpoints, 2026-10-19]
  VERIFIED. Uptime is a rolling metric, so these are snapshots.
- **Terms.** OpenRouter links its Nvidia free provider to the NVIDIA API Trial
  Terms of Service. Its §1.2 limits access to trial purposes and bars use of
  the service or its output in production, and §1.4 limits use without a
  Subscription to internal testing and evaluation [DOC https://assets.ngc.nvidia.com/products/api-catalog/legal/NVIDIA%20API%20Trial%20Terms%20of%20Service.pdf,
  accessed 2026-10-19] VERIFIED (document text). Whether those terms bind
  OpenRouter-mediated calls is UNVERIFIED. The Thinking Machines "free research
  API tier" terms could not be extracted (UNVERIFIED)
  [LIVE GET https://openrouter.ai/api/v1/providers, 2026-10-19].
- **Data use.** Google uses free-tier content for Gemma 4 and the Flash models
  to improve its products, but not paid-tier content
  [DOC https://ai.google.dev/gemini-api/docs/pricing, accessed 2026-10-19, page "Last updated 2026-10-16 UTC"] VERIFIED. Gemma 4 is
  free-tier only on the Gemini API (no paid-tier offer), so a no-training
  route for Gemma 4 means a third-party host or self-hosting. OpenRouter routes
  Gemma `:free` to Google AI Studio, so the same terms probably apply
  (INFERRED, pass-through terms not verified). OpenRouter has account settings
  that avoid training providers, separately for paid and free models
  [DOC https://openrouter.ai/docs/guides/privacy/provider-logging, accessed
  2026-10-19] VERIFIED; their effect on free-model availability is not stated.

[DOC cost.md §0 item 9 (verifier), §1]. [15](15-security-and-deployment.md) T9
recommends treating every `:free` and trial channel as unable to receive user
questions until counsel rules (REQUIRES LEGAL REVIEW). The cost of that
decision is Pilot option A in §7.4.

### 2.5 No usage telemetry

The `ask_routing` log line records the mode, models, upstream statuses and
latency, and no tokens [DOC docs/ai/WAYMAKER_ANSWER_PRODUCT_QUALITY_2026_09.md:100-103]
README-ONLY. A live offline run printed no token fields (OBSERVED). No code in
backend, lib or api reads provider `usage`, `prompt_tokens` or
`completion_tokens`, and docs/ai, docs/ops and reports hold no volume or cost
figures (grep, VERIFIED). **Monthly request volume is therefore UNKNOWN.**
Railway HTTP metrics, Vercel analytics or the OpenRouter activity page would
probably have it; none were accessed. [DOC cost.md §0 item 3, §2]

## 3. Measured prompt size

**Method.** The researcher replaced `_openrouter_complete_with_candidates`
with a recording stub. All outbound HTTP was blocked at the transport, the
environment was clean (no keys), and `LAW_GROUNDING_MODE` was `disabled`.
Five questions were posted to /api/ask through FastAPI's TestClient. Each made
exactly one LLM call, and all returned HTTP 200. The verifier re-ran the
script with `python -I -B` and got identical character counts
[LIVE offline run, 2026-10-19, script
`scratchpad/costscripts/measure_prompt.py`; verifier output
`scratchpad/verify_cost/m.out`, re-read 2026-10-20] OBSERVED.

**Correction.** The stub sat in front of `_llm_messages`, which prepends the
default `WAYMAKER_SYSTEM_PROMPT` whenever `system_prompt` is None
[CODE paradiso_backend.py:1342-1353, 1381, 2954-2955] VERIFIED. That prompt
is 2,186 characters with no Hangul (`ast` read of
[CODE paradiso_backend.py:1303] on `fc896c2`, 2026-10-20, VERIFIED): about
486–625 tokens at 3.5–4.5 chars/token. It is added to every row below.

| Case | Mode | User prompt chars (measured) | Hangul | + system prompt chars | Est. input tokens, corrected | max_tokens | First model |
|---|---|---|---|---|---|---|---|
| "D-2 연장시 필수 서류" | fast | 12,277 | 1,422 | 14,463 | 3,609–5,148 | 900 | gemma-4-26b-a4b-it:free |
| same | basic | 12,277 | 1,422 | 14,463 | 3,609–5,148 | 1,400 | nemotron-3-ultra:free |
| E-7 workplace change + prior permission | basic | 14,141 | 833 | 16,327 | 3,860–5,260 | 1,400 | nemotron-3-ultra:free |
| F-6 extension documents and fee | basic | 13,130 | 827 | 15,316 | 3,634–4,967 | 1,400 | nemotron-3-ultra:free |
| English D-2 extension | basic | 13,700 | 1,253 | 15,886 | 3,878–5,434 | 1,400 | nemotron-3-ultra:free |

The token band is INFERRED. No tokenizer was installed, so it assumes Hangul
at 1–2 chars/token and other text at 3.5–4.5 chars/token, before chat-template
overhead. Output length was not measured; the caps are 900 and 1,400.
[DOC cost.md §2 table and verifier note; verification pass claim 4]

**Why production prompts are larger.** Production runs with law grounding
enabled, and this run had it off. History can add up to **24 items × 2,000
chars** (about 48k chars, roughly 12k–20k tokens), and context up to 8,000 chars
[CODE paradiso_backend.py:447-449] VERIFIED (caps), INFERRED (tokens).
Anthropic says its tokenizer for Claude 4.7 and later produces about 30% more
tokens for the same text
[DOC https://platform.claude.com/docs/en/about-claude/pricing, accessed
2026-10-19] VERIFIED. Its effect on Korean was not measured.

**Planning profiles** (INFERRED) [DOC cost.md §2]:

| Profile | Input | Output | Use |
|---|---|---|---|
| Standard | 5,000 | 1,000 | all tables, unless a row says otherwise; a middle value, not an upper bound |
| Heavy reasoning | 8,000 | 3,000 | paid reasoning models bill thinking as output; today's cap is 1,400 |
| Long thread | ~15,000–25,000 | 1,000 | a plausible minority (verifier); at 20k in, Gemma 4 31B costs $0.0044, Nemotron 3 Ultra $0.0144, Sonnet 5.5 $0.050 and Opus 5.5 $0.100 per question (INFERRED) |

Volumes of 1k, 10k and 100k questions a month are 6M, 60M and 600M tokens on
the standard profile.

## 4. Unit prices

### 4.1 Models in the current chain (OpenRouter paid ids)

Source for every row:
[LIVE GET https://openrouter.ai/api/v1/models, 2026-10-19 03:57 UTC, HTTP 200,
788,482 bytes; re-fetched by the verifier ~04:35 UTC, all prices matched]
VERIFIED. [DOC cost.md §3]

| Model id | `:free` listed? | Input | Output | Context | $/question (5k/1k) | 1k q/mo | 10k q/mo | 100k q/mo |
|---|---|---|---|---|---|---|---|---|
| google/gemma-4-26b-a4b-it | yes | $0.0675 | $0.225 | 262,144 | $0.00056 | $0.56 | $5.63 | $56 |
| nvidia/nemotron-3.5-lightning | yes | $0.07 | $0.20 | 262,144 | $0.00055 | $0.55 | $5.50 | $55 |
| meta-llama/llama-3.3-70b-instruct | **no** | $0.10 | $0.32 | 131,072 | $0.00082 | $0.82 | $8.20 | $82 |
| nvidia/nemotron-3-super-120b-a12b | yes | $0.08 | $0.45 | 262,144 | $0.00085 | $0.85 | $8.50 | $85 |
| openai/gpt-oss-120b | **no** (`:free` gone) | $0.15 | $0.60 | 131,072 | $0.00135 | $1.35 | $13.50 | $135 |
| google/gemma-4-31b-it | yes | $0.20 | $0.40 | 262,144 | $0.00140 | $1.40 | $14.00 | $140 |
| minimax/minimax-m3 (Chinese route, unwired) | paid only | $0.30 | $1.20 | 1,048,576 | $0.00270 | $2.70 | $27 | $270 |
| thinkingmachines/inkling-small | yes | $0.45 | $1.20 | 524,288 | $0.00345 | $3.45 | $34.50 | $345 |
| nvidia/nemotron-3-ultra-550b-a55b | yes | $0.60 | $2.40 | 262,144 | $0.00540 | $5.40 | $54 | $540 |
| nousresearch/hermes-3-llama-3.1-405b | **no** | $1.00 | $1.00 | 131,072 | $0.00600 | $6.00 | $60 | $600 |
| thinkingmachines/inkling | yes (403 per owner QA) | $1.00 | $4.05 | 524,288 | $0.00905 | $9.05 | $90.50 | $905 |
| openai/gpt-oss-20b (production enforcement) | – | $0.018 | $0.09 | – | $0.00018 | $0.18 | $1.80 | $18 |

The gpt-oss-20b price comes from the verifier's re-fetch; its context was not
recorded.

**Providers behind the paid ids.** Prices come from
[LIVE https://openrouter.ai/api/v1/models/{id}/endpoints, 2026-10-19]
VERIFIED. `google/gemma-4-31b-it` has 15 endpoints, at $0.10–$0.75 input and
$0.32–$1.00 output. The cheapest (CoreWeave, Venice, Chutes) run **fp4**. The
bf16/fp8 endpoints (Crusoe, Parasail, DeepInfra fp8) charge $0.14–$0.20 input
and $0.40 output, so the headline $0.20/$0.40 already covers a non-fp4 pin.
Uptime_last_1d ranges from 65% (Novita) to 100%.
`nvidia/nemotron-3-ultra-550b-a55b` has 5 endpoints, at $0.40–$0.625 input
and $1.76–$3.125 output. The cheapest endpoint is not automatically the right
one for answer quality (INFERRED).

### 4.2 Stronger paid reasoning APIs

| Model | Input | Output | Cache read | $/q standard (5k/1k) | $/q heavy (8k/3k) | Source, accessed 2026-10-19 |
|---|---|---|---|---|---|---|
| Claude Haiku 5.5 (prompts ≤100k) | $0.10 | $0.50 | $0.01 | $0.0010 | $0.0023 | [DOC https://platform.claude.com/docs/en/about-claude/pricing] VERIFIED |
| Gemini 2.5 Flash-Lite | $0.10 | $0.40 | – | $0.0009 | $0.0020 | [DOC https://ai.google.dev/gemini-api/docs/pricing] VERIFIED |
| GPT-5.6-luna | $0.20 | $1.20 | $0.02 | $0.0022 | $0.0052 | [DOC https://developers.openai.com/api/docs/pricing] VERIFIED |
| GPT-5-mini | $0.25 | $2.00 | $0.025 | $0.00325 | $0.008 | same, VERIFIED |
| Gemini 3.8 Flash | $0.75, rising to $1.50 on 2027-01-01 | $3.75, rising to $7.50 | – | $0.0075 → $0.015 | $0.0173 → $0.0345 | [DOC https://ai.google.dev/gemini-api/docs/pricing] VERIFIED |
| Claude Haiku 4.5 | $1 | $5 | $0.10 | $0.010 | $0.023 | [DOC https://platform.claude.com/docs/en/about-claude/pricing] VERIFIED |
| Gemini 2.5 Pro (≤200k) | $1.25 | $10.00 | – | $0.01625 | $0.040 | [DOC https://ai.google.dev/gemini-api/docs/pricing] VERIFIED; has a free tier |
| Claude Sonnet 5.5 | $2 | $10 | $0.10 | $0.020 | $0.046 | [DOC https://platform.claude.com/docs/en/about-claude/pricing] VERIFIED |
| Claude Sonnet 5 | $2 | $10 | $0.20 | $0.020 | $0.046 | same; footnote: the $2/$10 intro price is now standard, VERIFIED |
| google/gemini-4-argon (OpenRouter only) | $2.00 | $10.00 | – | $0.020 | $0.046 | [LIVE https://openrouter.ai/api/v1/models] VERIFIED; first-party price UNKNOWN |
| GPT-5.6-terra | $2.00 | $12.00 | $0.20 | $0.022 | $0.052 | [DOC https://developers.openai.com/api/docs/pricing] VERIFIED |
| Gemini 3.1 Pro Preview (≤200k) | $2.00 | $12.00 | – | $0.022 | $0.052 | [DOC https://ai.google.dev/gemini-api/docs/pricing] VERIFIED; no free tier |
| GPT-5.4 (<272K) | $2.50 | $15.00 | $0.25 | $0.0275 | $0.065 | [DOC https://developers.openai.com/api/docs/pricing] VERIFIED |
| Claude Opus 5.5 | $4 | $20 | $0.20 | $0.040 | $0.092 | [DOC https://platform.claude.com/docs/en/about-claude/pricing] VERIFIED |
| GPT-5.6-sol | $4.00 | $20.00 | $0.40 | $0.040 | $0.092 | [DOC https://developers.openai.com/api/docs/pricing] VERIFIED |
| GPT-5.5 (<272K) | $5.00 | $30.00 | $0.50 | $0.055 | $0.130 | same, VERIFIED |
| Claude Fable 5.1 | $10 | $50 | $0.25 | $0.100 | $0.230 | [DOC https://platform.claude.com/docs/en/about-claude/pricing] VERIFIED |

[DOC cost.md §4; verification pass claim 7]. OpenRouter lists the same prices
for these ids, plus `:batch` variants at 50% [LIVE OpenRouter catalog]
VERIFIED. `openai.com/api/pricing/` returned HTTP 403, and the
developers.openai.com page was used instead [LIVE 2026-10-19].

Levers (INFERRED). Prompt caching could cut input cost substantially if
Waymaker's instruction and evidence prefix is stable between calls: Sonnet 5.5
cache reads cost 0.05x the base price. The stable share of the prompt was not
measured. Batch pricing (50% off) does not suit interactive answers, but it
does suit offline evaluation and dataset generation.

### 4.3 Platform fees and channel terms

| Item | Value | Source, accessed 2026-10-19 |
|---|---|---|
| OpenRouter pay-as-you-go | **5.5% fee on credit purchases** (Business 8%) | [DOC https://openrouter.ai/pricing] VERIFIED |
| OpenRouter BYOK | free up to $25,000/month of list-price inference, then 5% | same, VERIFIED |
| OpenRouter Free plan | no purchases; 25+ free models from 4 free providers | same, VERIFIED |
| Gemini API paid tiers | Tier 1 = linked billing (cap $250); Tier 2 = $100 paid + 3 days (cap $2,000); Tier 3 = $1,000 paid + 30 days | [DOC https://ai.google.dev/gemini-api/docs/pricing] VERIFIED |
| Gemini API free-tier rate limits | not published; shown only inside Google AI Studio | [DOC https://ai.google.dev/gemini-api/docs/rate-limits] VERIFIED |
| Together, Gemma 4 31B serverless | $0.39 / $0.97 per 1M | [DOC https://www.together.ai/pricing] VERIFIED |
| NVIDIA build.nvidia.com trial | ~40 RPM; limits vary by model, use case and traffic; production means deploying a NIM | [WEB https://forums.developer.nvidia.com/t/request-for-nvidia-nim-api-rate-limit-increase-40-200-rpm/375340, accessed 2026-10-19] UNVERIFIED (moderator reply quoted second-hand); `build.nvidia.com/faq` HTTP 404 |
| NVIDIA starting credits (1,000, requestable to 5,000) | user posts and third-party guides only | UNVERIFIED |
| NVIDIA AI Enterprise licence | not looked up | UNKNOWN |

Budget 5–10% on top of API figures for retries and calls that time out
mid-stream. Providers generally do not bill requests that return no tokens
(INFERRED) [DOC cost.md §4].

## 5. Hardware sizing

Waymaker has no GPU in production (§2.1). Mission 001's preparation machine had
no GPU either ([13](13-artemis-experiment.md), status line). Its data volume
sat at 97–100% used during the research [DOC cost.md §12 item 9] and was still
98% used on 2026-10-20 (`df`, OBSERVED). That machine cannot even hold an 8B
BF16 checkpoint (~16 GB), let alone 31B (INFERRED). Every hardware row below
is therefore a rented or free cloud GPU.

| Workload | Weights (INFERRED) | Minimum GPU | Notes |
|---|---|---|---|
| 7–9B dense inference | ~16 GB BF16; FP8 about half | 1x L4 24 GB | vLLM on one L4 is plausible at the low end of 1–2 questions/s at peak and tight at the high end [DOC cost.md §9] INFERRED |
| 27–32B dense inference | ~62 GB BF16; ~31 GB FP8 | 1x A100-80GB or H100 80 GB | BF16 on an A100-80GB leaves ~15 GB of KV cache: about 8–16 sequences at 6k context, or **~0.3–0.6 questions/s sustained** [DOC cost.md §9] INFERRED |
| QLoRA SFT, 8B | – | 1x A100-80GB | assumed 1,500–3,000 training tokens/s [DOC cost.md §7] INFERRED |
| QLoRA SFT, 31B | – | 1x H100 | assumed 600–1,200 training tokens/s [DOC cost.md §7] INFERRED |
| Artemis compact model | QLoRA in about 9–12 GB ([13](13-artemis-experiment.md) §4, INFERRED) | a 16–24 GB GPU | arm budgets are in [13](13-artemis-experiment.md) §11 |
| Adapters and datasets | LoRA ~50–200 MB (8B), ~0.2–1 GB (31B); datasets well under 1 GB | – | merged 31B BF16 weights ~62 GB [DOC cost.md §8] INFERRED |

**Peak load.** One million questions a month averages about 0.39 questions/s.
A 3–5x daytime peak in Korean time makes that about 1.2–2 questions/s, which
means roughly 6–10k prefill tokens/s and 1.2–2k decode tokens/s at peak
[DOC cost.md §9] INFERRED. One A100 running 31B and sized for peak
(0.3–0.6 q/s) therefore serves on average only about **0.16–0.53M questions a
month** (0.3/5 to 0.6/3 of peak capacity, times 2.63M seconds). INFERRED
arithmetic from the note's capacity estimate.

**Cold starts** (INFERRED). Loading 16 GB of weights (8B BF16) takes tens of
seconds. Loading 62 GB (31B BF16) or 31 GB (FP8) takes one to several minutes.
The Quick Answer timeout is 7 s and the OpenRouter timeout 60 s
[CODE lib/waymaker-quick-answer-ai.js:31] [CODE paradiso_backend.py:269]
VERIFIED. (The note cites line 32; on `HEAD` the 7 s default is on line 31.) An interactive 27–32B deployment therefore needs at least one
always-warm worker, which turns "serverless" back into a 24/7 cost
[DOC cost.md §8].

**Region.** US-hosted GPUs add roughly 130–200 ms of round trip from Korea
(INFERRED, not measured). That is small next to multi-second generation.
Seoul and Tokyo GPU prices were not looked up (UNKNOWN); they are usually
higher than us-central1 or us-east-1 (INFERRED) [DOC cost.md §6, §9].

## 6. Cost categories

### 6.1 One-time

| Item | Cash | Effort | Evidence |
|---|---|---|---|
| OpenRouter credits to lift the free cap to 1,000/day | $10 + 5.5% = $10.55 | – | [DOC https://openrouter.ai/docs/api-reference/limits] [DOC https://openrouter.ai/pricing], accessed 2026-10-19, VERIFIED |
| Remove dead ids from the Node defaults; merge the Inkling removal | $0 | hours | INFERRED |
| Token and model logging per call | $0 | ~0.5–1 engineering day | INFERRED [DOC cost.md §10] |
| Evaluation harness and benchmark | $0 cash | engineering and reviewer days | see [12](12-evaluation-methodology.md) |
| Self-host setup, if ever chosen | GPU hours during setup | 2–5 days | INFERRED [DOC cost.md §10] |

Typical one-time total: $10–60 cash plus engineering days [DOC cost.md §10].

### 6.2 Recurring inference (API)

`API $/month = Q × (T_in × p_in + T_out × p_out) × (1 + fee)` [DOC cost.md §9]
INFERRED. Standard profile, list price, no fees:

| Model | 1k q/mo (6M tok) | 10k q/mo (60M tok) | 100k q/mo (600M tok) |
|---|---|---|---|
| Current chain, `:free` | $0, capped (§2.3) | not reachable on free quota | not reachable |
| Gemma 4 26B A4B, paid | $0.56 | $5.63 | $56 |
| Gemma 4 31B, paid | $1.40 | $14.00 | $140 |
| Nemotron 3 Ultra, paid | $5.40 | $54 | $540 |
| Claude Haiku 5.5 | $1.00 | $10 | $100 |
| Gemini 3.8 Flash (2026 / 2027 price) | $7.50 / $15 | $75 / $150 | $750 / $1,500 |
| Claude Sonnet 5.5 | $20 | $200 | $2,000 |
| GPT-5.6-terra or Gemini 3.1 Pro | $22 | $220 | $2,200 |
| Claude Opus 5.5 or GPT-5.6-sol | $40 | $400 | $4,000 |

Unit prices: §4.1 and §4.2, all accessed 2026-10-19. Add 5.5% when buying
through OpenRouter credits, and 5–10% for retries. [DOC cost.md §4 monthly table]

Today's recurring inference is $0 on the free chains, plus the paid production
enforcement calls; their amount is UNKNOWN without volume (§2.2).

### 6.3 Training

Managed fine-tuning, per 1M training tokens (dataset tokens × epochs):

| Provider | ≤16B (e.g. Llama 3.1 8B, Qwen3.5 9B) | 17–69B (e.g. Gemma 4 31B, Qwen3.5 27B) | Notes | Source, accessed 2026-10-19 |
|---|---|---|---|---|
| Together AI, table 1 (probably LoRA) | SFT $0.34, DPO $0.84 | SFT $1.05, DPO $2.62 | minimum $4.00 per job; Gemma 4 26B A4B and 31B listed | [DOC https://www.together.ai/pricing] VERIFIED; the page does not say which table is LoRA and which is full |
| Together AI, table 2 (probably full) | SFT $0.38, DPO $0.94 | SFT $1.16, DPO $2.88 | Llama 3.3 70B $2.03 / $2.24 | same |
| Fireworks, LoRA | SFT $0.50, DPO $1.00 | SFT $3.00, DPO $6.00 (16.1–80B) | full-parameter SFT $1.00 / $6.00; fine-tuned models served on serverless at base-model prices | [DOC https://fireworks.ai/pricing] VERIFIED |
| OpenAI | gpt-4.1-mini $5.00, gpt-4.1-nano $1.50, gpt-4o-mini $3.00; o4-mini RFT $100/hour | gpt-4.1 $25.00 | **being wound down; new users cannot access it** | [DOC https://developers.openai.com/api/docs/pricing] VERIFIED |
| Google Vertex AI (Gemini tuning) | – | – | page did not render; snippets show unlabelled $5.00 / $3.00 / $1.00 rows | UNKNOWN |
| Google AI Studio (Gemma 4 tuning) | – | – | no managed price found | UNKNOWN |

Worked example (INFERRED) [DOC cost.md §7]: 2,000 curated Q/A examples ×
3,000 tokens × 3 epochs = 18M training tokens.

| Route | 8B class | 31B class |
|---|---|---|
| Together (table 1) | 18 × $0.34 = **$6.12** | 18 × $1.05 = **$18.90** |
| Fireworks LoRA | **$9.00** | **$54.00** |
| Self-run QLoRA (Unsloth/PEFT) on RunPod | 1.7–3.3 h on an A100-80GB at $1.79/h = **$3–6** | 4.2–8.3 h on an H100 at $2.69–$3.99/h = **$11–33** |

Add 30–100% to self-run figures for failed runs, evaluation passes and idle
notebook time. **The larger cost is the data, not GPU time.** A legally safe
Korean immigration dataset needs weeks of expert review. The project rules
forbid inventing legal requirements and mixing visa-issuance and stay
procedures, and nothing in a dataset may be relaxed to make a run cheaper
(INFERRED; project CLAUDE.md). Governance is in
[11](11-dataset-governance.md), and the training plan in
[09](09-training-and-distillation.md).

Free and low-cost GPU for experiments [DOC cost.md §5]:

| Service | What you get | Price | Source, accessed 2026-10-19 / status |
|---|---|---|---|
| Google Colab Free | intermittent T4-class GPU, no guarantee | $0 | not quantified on a primary page; UNVERIFIED |
| Colab Pro | 100 compute units/month | **$9.99/mo** | [LIVE curl https://colab.research.google.com/signup, page served for region KR, attribute `formattedProSubscriptionPrice="$9.99"`] VERIFIED; the 100 CU allotment is INFERRED |
| Colab Pro+ | 500 compute units/month | **$49.99/mo** | same page, `formattedVeryProSubscriptionPrice="$49.99"` VERIFIED; CU count INFERRED |
| Colab Pay As You Go | 100 CU or 500 CU packs | $9.99 / $49.99 | same page, `formattedCCU100Price`, `formattedCCU500Price` VERIFIED |
| Colab burn rates | T4 ~1.2–1.8 CU/h, A100 ~15 CU/h; L4/H100 unpublished | ~$0.12–0.18/h T4, ~$1.50/h A100 at $0.10/CU | [WEB https://gpuperhour.com/blog/google-colab-alternatives] UNVERIFIED |
| Colab Enterprise (GCP) | T4 ~$0.42/h, L4 ~$0.672/h, A100 ~$3.52/h | per hour | search snippet of https://cloud.google.com/colab/pricing, page did not render; UNVERIFIED |
| Kaggle Notebooks | ~30 GPU-hours/week (P100 or 2x T4), 9–12 h sessions; a Sept 2026 review says the quota varies | $0 | official pages returned titles only; [WEB https://gpuperhour.com/blog/free-cloud-gpus-and-credits] UNVERIFIED |
| Hugging Face ZeroGPU | half an RTX Pro 6000 Blackwell (48 GB) per call; daily quota 2 min unauthenticated, 5 min free account, 40 min PRO/Team, 60 min Enterprise; beyond quota $1 per 10 min (PRO and up); Gradio only; 2 Spaces free, 10 on PRO | $0 / PRO $9/mo | [DOC https://huggingface.co/docs/hub/spaces-zerogpu] VERIFIED |
| HF PRO | 8x ZeroGPU quota, $2/month compute credits, 1 TB private storage | $9/mo | [DOC https://huggingface.co/pricing] [DOC https://huggingface.co/docs/inference-providers/pricing] VERIFIED |
| HF Inference Providers | pass-through provider prices without markup; free users need purchased credits | per token | [DOC https://huggingface.co/docs/inference-providers/pricing] VERIFIED |
| HF Spaces GPU | T4 small $0.40/h, T4 medium $0.60, L4 $0.80, L40S $1.80, A10G small $1.00, A10G large $1.50, A100 large $2.50 | per hour | [DOC https://huggingface.co/pricing] VERIFIED |
| HF AutoTrain | free when run locally; on Spaces, billed per minute at the hardware rate | hardware rate | [DOC https://huggingface.co/docs/autotrain/en/cost] VERIFIED |
| Modal Starter | **$30/month free credits**; Team $250/mo including $100 credits | per second | [DOC https://modal.com/pricing] VERIFIED. $30 is ~37 L4-hours, ~12 A100-80GB-hours or ~7.6 H100-hours of GPU-only time; CPU and RAM are billed on top (INFERRED) |
| Lightning AI | official page HTTP 503, Retry-After 3600. A tracker reports a one-time grant of up to 30 credits (12-month expiry) from Sept 2026, and T4 $0.55, L4 $0.79, A100-40GB $2.19, H100 $4.50 | – | [WEB https://www.usagepricing.com/blueprint/activity/lightning-ai-2026-09-21-gpu-rate-card-reprice] UNVERIFIED |
| NVIDIA build.nvidia.com | hosted trial inference ~40 RPM (no raw GPU) | $0 | UNVERIFIED (§4.3) |

None of the free tiers (Colab Free, Kaggle, ZeroGPU) offers an 80 GB GPU. Only
Modal's $30 monthly credit buys any 80 GB time (~12 A100-80GB-hours,
GPU-only). A 31B QLoRA run or teacher pass therefore needs paid or credited
rental ([13](13-artemis-experiment.md) §11, arm C). INFERRED.

### 6.4 Inference hosting (self-hosted or dedicated)

On-demand GPU rental, per GPU-hour [DOC cost.md §6]:

| GPU (VRAM) | RunPod Secure / Community | Lambda (1x) | Vast.ai live (min / median, 1-GPU on-demand) | Modal (GPU only) | HF Inference Endpoints | Google Cloud us-central1 (whole VM: on-demand / spot) | AWS (whole instance: on-demand / spot) |
|---|---|---|---|---|---|---|---|
| T4 (16 GB) | not listed | not offered | $0.15 / $0.15 (n=3) | $0.59 | $0.50 | ~$0.35 per GPU + N1 VM (UNVERIFIED) | g4dn.xlarge $0.526 / $0.332 |
| L4 (24 GB) | $0.59 / $0.44 | not offered | $0.362 / $0.362 (n=4) | $0.80 | $0.80 | g2-standard-4 $0.7068 / $0.423 | g6.xlarge $0.8048 / $0.637 |
| A10 / A10G (24 GB) | not listed | A10 $1.29 | A10 $0.243 (n=2) | A10 $1.10 | not listed | n/a | g5.xlarge (A10G) $1.006 / $0.478 |
| L40S (48 GB) | $1.09 / $0.79 | – | $0.402 / $0.801 (n=9) | $1.95 | $1.80 | not fetched (UNKNOWN) | g6e.xlarge $1.861 / $1.713 |
| A100 40 GB | – | PCIe or SXM $1.99 | 40/80 GB mixed: PCIe $0.366 / $0.735 (n=16); SXM4 $0.43 / $0.668 (n=21) | $2.10 | – | a2-highgpu-1g $3.6734 / $2.204 | p4d.24xlarge 8x $21.958 (= $2.745/GPU) / $18.433 |
| A100 80 GB | PCIe $1.79 / $1.19; SXM $1.79 / $1.39 | SXM 8x only, $2.79/GPU | (rows above) | $2.50 | $2.50 | a2-ultragpu-1g $5.0688 / $3.0388 | p4de.24xlarge 8x $27.447 (= $3.43/GPU) / $21.296 |
| H100 80 GB | PCIe $2.89 / $1.99; SXM $3.99 / $2.69 | PCIe $3.29; SXM $4.29 | PCIe $2.002 / $2.219 (n=5); SXM $1.922 / $2.401 (n=6) | $3.95 | $4.50 | a3-highgpu-1g $11.0612 / $6.5993 | p5.4xlarge (1x H100) $6.880 / $4.417 |
| H200 141 GB | $5.29 / $3.59 | – | not queried | $4.54 | $5.00 | – | – |

Column sources, all accessed 2026-10-19:

- **RunPod**: [DOC https://www.runpod.io/pricing] VERIFIED for Secure. The
  Community column comes from the page's structured data only.
- **Lambda**: [DOC https://lambda.ai/pricing] VERIFIED; prices exclude sales
  tax, VAT and GST.
- **Vast.ai**: [LIVE GET https://console.vast.ai/api/v0/bundles/?q=…, 9
  read-only GETs at 04:04 UTC; the verifier re-checked L4 and H100 SXM with 2
  GETs at 04:42 UTC]
  OBSERVED. Values are `dph_total`, which includes the host's default disk
  charge. Samples are small, and hosts vary in reliability, location and
  bandwidth.
- **Modal**: [DOC https://modal.com/pricing] VERIFIED. Per-second rates (for
  example L4 $0.000222/s, H100 $0.001097/s) plus CPU at $0.0000131 per physical
  core-second and memory at $0.00000222 per GiB-second. A 4-core, 16 GiB
  container adds ~$0.32/h (INFERRED).
- **HF Inference Endpoints** (AWS, 1 GPU): [DOC https://huggingface.co/pricing]
  VERIFIED. Also B200 $9.25, RTX PRO 6000 $2.75. Scale-to-zero behaviour was
  not checked (UNKNOWN).
- **Google Cloud**: [WEB https://gcloud-compute.com/g2-standard-4.html,
  /a2-highgpu-1g.html, /a2-ultragpu-1g.html, /a3-highgpu-1g.html] VERIFIED
  against that aggregator only, which disclaims its own accuracy. The
  official GCP GPU pricing pages returned only a title. The T4 figure is from a
  search snippet with unlabelled columns (UNVERIFIED).
- **AWS**: [WEB https://instances.vantage.sh/aws/ec2/g4dn.xlarge, g5.xlarge,
  g6.xlarge, g6e.xlarge, p4d.24xlarge, p4de.24xlarge, p5.4xlarge] VERIFIED
  against that aggregator only. The region is INFERRED to be us-east-1 Linux.
  AWS's own g6 page lists no prices [DOC https://aws.amazon.com/ec2/instance-types/g6/]
  VERIFIED.

Spot and marketplace rows are cheaper per hour, but they add pre-emption and
host-quality risk. Without redundancy, that does not fit an interactive answer
path (INFERRED) [DOC cost.md §9].

**Serverless GPU (scale to zero)** [DOC https://www.runpod.io/pricing]
[DOC https://docs.runpod.io/serverless/pricing], accessed 2026-10-19, VERIFIED.
RunPod Serverless charges per hour by class: 16 GB $0.58; 24 GB (L4/A5000/3090)
$0.69; 24 GB 4090 $1.10; 32 GB 5090 $1.58; 48 GB (L40/L40S/6000 Ada) $1.75;
48 GB A6000/A40 $1.22; 80 GB A100 $2.72; H100 $4.79. The page does not
separate Flex and Active rates. Billing is per second from worker start to
stop. **The cold start (model loading) is billed, and so is the idle timeout
(default 5 s).** Image pulls while scaled down are not billed. The default
spend limit is $80/h. Modal scales to zero at the §6.4 rates
[DOC https://modal.com/pricing] VERIFIED. That RunPod docs page also held text
asking the reader to send feedback to a docs server; the researcher ignored it.

**Dedicated hosting.** A Together dedicated endpoint costs $5.49 per H100-hour
(GPU clusters $3.99) [DOC https://www.together.ai/pricing, accessed
2026-10-19] VERIFIED; the page's structured data shows a conflicting $6.49
low. Fireworks on-demand charges H100 $8.00/h, H200 $8.00 and B200 $13.00,
with region-restricted deployments at 1.5x [DOC https://fireworks.ai/pricing,
accessed 2026-10-19] VERIFIED.

### 6.5 Storage

| Store | Free | Paid | Source, accessed 2026-10-19 / status |
|---|---|---|---|
| HF Hub | public storage best-effort; **private 100 GB** on a free account | PRO: 1 TB private + $18/TB/month beyond; public add-on $12/TB/month; hard limit 500 GB per file, under 200 GB recommended | [DOC https://huggingface.co/docs/hub/storage-limits] VERIFIED |
| Cloudflare R2 Standard | 10 GB-month, 1M Class A and 10M Class B ops per month | $0.015/GB-month; Class A $4.50 per million, Class B $0.36 per million; **egress free** | [DOC https://developers.cloudflare.com/r2/pricing/] VERIFIED |
| AWS S3 Standard (us-east-1) | first 100 GB/month of internet egress | $0.023/GB-month for the first 50 TB; GET $0.0004 per 1,000; egress ~$0.09/GB after the free 100 GB | [DOC https://aws.amazon.com/s3/pricing/] VERIFIED for the GET price and the 100 GB allowance; storage and egress rates from secondary sources, UNVERIFIED |
| RunPod network volume | – | $0.07/GB-month (<1 TB), $0.05 (>1 TB); stopped-pod volume $0.20/GB-month | [DOC https://www.runpod.io/pricing] VERIFIED |

Everything except merged 31B weights fits within HF's free 100 GB private quota
or R2's free 10 GB. **Storage is under $5 a month in every scenario**
[DOC cost.md §8] INFERRED.

### 6.6 Monitoring

Monitoring costs nothing in cash today, because there is nothing to monitor:
no token or cost telemetry exists (§2.5). The OpenRouter activity page and the
provider consoles are free. Paid observability tools were not priced
(UNKNOWN). The minimum is to log `usage` tokens and the model id per call
(about 0.5–1 engineering day), keep daily counters per upstream (free bucket,
paid spend, law.go.kr calls), set a monthly spend cap and alert on the provider
console, and tag synthetic traffic [DOC cost.md §10]
[15](15-security-and-deployment.md) §3.15. INFERRED (effort).

### 6.7 Maintenance and engineering effort

| Route | Recurring effort (INFERRED) | Drivers |
|---|---|---|
| API (free or paid) | ~1–2 h/month of catalog upkeep; `scripts/check_model_catalog.py` already ships (present at `fc896c2`, VERIFIED) | free-model churn (five referenced ids gone, Inkling 403), quota handling, evaluation reruns |
| Self-hosted | 2–5 days setup, then ~2–4 h/week (~9–17 h/month) | OS and driver patching, vLLM upgrades, capacity tuning, on-call for a single point of failure |

[DOC cost.md §10]. No hourly rate is assumed. The work is the owner's time,
and its cash value is UNKNOWN. The break-even tables in §8 count GPU cost
only; adding this effort raises every self-host break-even further.

### 6.8 Category summary

| Category | Today | Typical size | Evidence |
|---|---|---|---|
| One-time | $0 | $10–60 cash plus engineering days | §6.1 |
| Recurring inference | ~$0, plus paid enforcement calls (UNKNOWN volume) | $0 (free, capped); ~$14 (10k q on Gemma 4 31B); $200–550 (10k q on a frontier model) per month | §2.2, §6.2 |
| Training | $0 | $3–54 per LoRA run on the §6.3 workload, before the failure margin (the note rounds to $4–60) | §6.3 |
| Self-hosted inference | $0 | $264–$8,075 per GPU per month, idle included | §8 |
| Storage | $0 | $0 to under $5/month | §6.5 |
| Monitoring | $0 cash | ~0.5–1 engineering day to add token logging | §6.6 |
| Maintenance and engineering | owner's time | API ~1–2 h/month; self-host 2–5 days + 2–4 h/week | §6.7 |

[DOC cost.md §10, with the verifier's correction to "Recurring inference"].

## 7. Scenarios

| Scenario | Cash | Period | Ceiling or volume | Section |
|---|---|---|---|---|
| 1. Zero new spending | **$0** new; production adds a small, unmeasured enforcement spend | monthly | 1,500 or 30,000 LLM calls/month, shared | §7.1 |
| 2. Small research budget | **$34.54–$49.44** with one Together run; $55.56 with both runs (over the cap) | one-time, $50 cap | experiments only | §7.2 |
| 3. Moderate experimental budget | **~$245–550** | 1–2 months | experiments plus a frontier baseline | §7.3 |
| 4. Production pilot | A **~$15–57** and B **~$54–151** (with the 5.5% fee); C **$200–550** (direct; +5.5% via OpenRouter); D **$2,600–6,300+** plus ops | monthly | 10k questions/month | §7.4 |

### 7.1 Scenario 1: zero new spending

- **Assumptions.** Keep the `:free` chains, buy no credits and rent no
  hardware.
- **Ceiling.** 50 LLM calls/day if the account has bought fewer than 10 credits,
  1,000/day otherwise (§2.3). Whether credits were ever bought is UNKNOWN.
- **Free fixes** (INFERRED). Remove the ids missing from the catalog from the
  Node defaults, because each dead id burns a counted failed attempt. Merge the
  owner's Inkling removal.
- **Experiments on free compute.** Modal's $30/month credit (~37 L4-hours or
  ~12 A100-80GB-hours), Kaggle at ~30 GPU-hours/week (UNVERIFIED), Colab Free
  T4 (intermittent), and HF ZeroGPU at 5 min/day on a free account. That is
  enough for small QLoRA runs on 7–9B models and for offline evaluation with
  free API models. Of these, only the Modal credit reaches an 80 GB GPU, and
  only for ~12 hours a month.
- **Data and terms caveat.** Gemma `:free` traffic goes to Google AI Studio,
  whose free tier uses content to improve products. Nvidia free traffic is
  under trial terms that exclude production use (§2.4).
- **Monthly cash.** $0 new. Production today is not exactly $0, because the
  enforcement-structured override uses paid ids at ~$0.00015–0.0012 per call
  and needs a positive balance. A true $0 needs that override removed (§2.2).

[DOC cost.md §11 scenario 1 with verifier correction]

### 7.2 Scenario 2: small research budget, capped at $50 one-time

| Item | Cost | What it buys |
|---|---|---|
| OpenRouter credits | $10 + $0.55 fee = $10.55 | Unlocks 1,000 free calls/day and leaves $10 of paid calls: ~7,100 Gemma 4 31B calls, ~1,850 Nemotron 3 Ultra calls or ~500 Claude Sonnet 5.5 calls, as a baseline or judge |
| Colab Pro, one month | $9.99 | 100 CU: roughly 55–80 T4-hours or 6–7 A100-hours at the UNVERIFIED third-party burn rates |
| **One** Together LoRA job | $4.00–$18.90 | either a small 8B run at the $4 minimum, or the 31B run on 18M training tokens ($18.90) |
| RunPod GPU top-up | ~$10 | ~5.5 A100-80GB-hours or ~17 L4-hours, for a vLLM serving test |
| **Total** | **$34.54–$49.44** | Afterwards $0 recurring (cancel Colab) |

The verifier corrected this scenario. Running **both** an 8B and a 31B Together
job on the §6.3 workload costs $6.12 + $18.90 = $25.02, and the total becomes
$10.55 + $9.99 + $25.02 + $10 = **$55.56, over the $50 cap**. To stay within
$50, keep to one Together run or drop the RunPod top-up. [DOC cost.md §11
scenario 2 with verifier corrections] INFERRED arithmetic on prices accessed
2026-10-19.

### 7.3 Scenario 3: moderate experimental budget, $200–600 over 1–2 months

| Item | Cost range |
|---|---|
| Frontier baseline: 300 questions × 3 models (Sonnet 5.5, GPT-5.6-terra, Gemini 3.1 Pro) × 2 runs, heavy profile ~$0.05/q | ~$90 |
| LLM-as-judge on those outputs (Haiku 5.5 or Flash-Lite class, or Sonnet batch at 50%) | $5–45 |
| Fine-tuning: 3–5 LoRA runs on 8B and 31B via Together or Fireworks, or self-run on RunPod | $40–150 |
| Serving experiment: 2–4 weeks of a scale-to-zero endpoint on Modal or RunPod for internal QA, plus one week of a warm L4 (~$100) | $50–150 |
| HF PRO for 2 months (ZeroGPU 40 min/day demo, 1 TB private) | $18 |
| Storage | $0–5 |
| Contingency for failed runs (~20%) | $40–90 |
| **Total** | **~$245–550** (the row ranges sum to $243–548) |

[DOC cost.md §11 scenario 3] INFERRED. The unit prices are those in §4.2,
§6.3 and §6.4, all accessed 2026-10-19. A frontier baseline is only useful
scored against the frozen benchmark and its gates in
[12](12-evaluation-methodology.md). The teacher-label rules in
[09](09-training-and-distillation.md) and `configs/teacher_policy.json`
(default deny) govern any use of frontier outputs as training data.

### 7.4 Scenario 4: future production pilot

Assumptions: 10k /api/ask questions a month, interactive latency, 99.5%
availability, and user questions under a no-training data policy. Quick Answer
and enforcement calls are extra. Railway and Vercel hosting are not included
(UNKNOWN).

| Option | Monthly cost | Notes |
|---|---|---|
| A. Paid open models as primary, `:free` as last resort | **~$15** (Gemma 4 31B) to **~$57** (Nemotron 3 Ultra), with the 5.5% fee | Cheapest. Removes the 1,000/day ceiling. Pin providers whose data policy rules out training (not verified per provider), and a non-fp4 quantization if quality needs it; the $0.20/$0.40 Gemma price already covers bf16/fp8 endpoints (§4.1) |
| B. Frontier model only for high-risk issue types (say 20% of questions), open model for the rest | **~$51–143** (~$54–151 with the 5.5% fee) | 2,000 × $0.02–0.05 = $40–100, plus 8,000 × $0.0014–0.0054 = $11.2–43.2. Fits the existing Basic-minimum escalation issue list [CODE backend/services/model_policy.py:52-69] |
| C. Every question on a frontier reasoning API | **$200–550** at 10k q; $2,000–5,500 at 100k q; +5.5% via OpenRouter | Only if evaluation shows a large gain in legal accuracy |
| D. Self-hosted 27–32B on 2 GPUs for availability | **$2,600–6,300+** plus ops time | 2x RunPod A100-80GB ($2,613) to 2x Lambda H100 ($6,263); on hyperscalers 2x AWS p5.4xlarge is $10,044 and 2x GCP a3-highgpu-1g $16,150 (INFERRED). Not justified on cost below ~2M q/month. Consider it only for a fine-tuned model that no API serves |
| Add-ons | token logging (0.5–1 day, once); monthly spend cap and alerts on the provider console | – |

[DOC cost.md §11 scenario 4 with verifier correction to option B]. Option A is
also the cheapest route to the [15](15-security-and-deployment.md) T9
recommendation of moving user questions off trial and free channels. Whether
specific paid providers meet that policy needs per-provider review and counsel
(REQUIRES LEGAL REVIEW, not done).

## 8. Break-even analysis for self-hosting

### 8.1 Formulas

- `Self-host $/month = hourly × 730 × N_gpus + storage + engineering time`
- `API $/question = T_in × p_in + T_out × p_out`
- `Q* (break-even questions/month) = self-host $/month ÷ API $/question`

The tables below count GPU cost only. Storage (under $5) and engineering time
(§6.7) would raise every Q*. [DOC cost.md §9] INFERRED.

### 8.2 Idle GPU cost

A 24/7 GPU costs the same at zero questions as at one million. Spread over
Waymaker-scale volumes (INFERRED arithmetic on §6.4 prices):

| GPU (24/7) | $/month | $/question at 1k q/mo | at 10k q/mo | at 100k q/mo | Same open model by API |
|---|---|---|---|---|---|
| RunPod Secure L4 $0.59/h (8B) | $431 | $0.43 | $0.043 | $0.0043 | Llama 3.1 8B $0.00033/q |
| RunPod Secure A100-80GB $1.79/h (31B) | $1,307 | $1.31 | $0.13 | $0.013 | Gemma 4 31B $0.0014/q |

At 10k questions a month, a single A100 serving 31B (capacity ~0.3–0.6 q/s,
§5) would be busy about **0.6–1.3% of the time**. At 100k it would be busy
6–13%. The rest is paid idle time (INFERRED). At 10k questions, the
self-hosted 31B question costs about 90x the API question.

### 8.3 7–9B model on one L4 (24 GB; FP8 or BF16 fits)

| Host (24/7, 730 h) | $/month | Q* vs Llama 3.1 8B API ($0.05/$0.08 → $0.00033/q) | Q* vs Qwen3.5 9B API ($0.10/$0.15 → $0.00065/q) |
|---|---|---|---|
| Vast.ai L4 median $0.362 | $264 | 0.80M q (4.8B tokens) | 0.41M q (2.4B tokens) |
| RunPod Secure L4 $0.59 | $431 | 1.31M q (7.8B tokens) | 0.66M q (4.0B tokens) |
| GCP g2-standard-4 $0.7068 | $516 | 1.56M q (9.4B tokens) | 0.79M q (4.8B tokens) |
| AWS g6.xlarge $0.8048 | $588 | 1.78M q (10.7B tokens) | 0.90M q (5.4B tokens) |
| Modal L4 $0.80 + ~$0.32 CPU/RAM | ~$818 | 2.48M q (14.9B tokens) | 1.26M q (7.6B tokens) |

API prices: [LIVE GET https://openrouter.ai/api/v1/models, 2026-10-19:
meta-llama/llama-3.1-8b-instruct $0.05/$0.08, qwen/qwen3.5-9b $0.10/$0.15]
VERIFIED. Qwen is excluded from Waymaker's general chain by policy
[CODE model_policy.py:129-131] and appears here only as a price reference for a
9B dense model. GPU prices are from §6.4.

### 8.4 27–32B model on one A100-80GB or H100 (BF16 ~62 GB, FP8 ~31 GB)

| Host (24/7) | $/month | Q* vs Gemma 4 31B API ($0.0014/q) | Q* vs Qwen3.5 27B API ($0.195/$1.56 → $0.0025/q) | Q* vs Sonnet 5.5 ($0.020/q; not like-for-like) |
|---|---|---|---|---|
| Vast.ai A100 SXM4 median $0.668 | $488 | 0.35M q (2.1B tokens) | 0.19M q | 24k q |
| RunPod Secure A100-80GB $1.79 | $1,307 | 0.93M q (5.6B tokens) | 0.52M q (3.1B tokens) | 65k q (0.39B tokens) |
| HF Endpoint or Modal A100-80GB $2.50 | $1,825 | 1.30M q (7.8B tokens) | 0.72M q | 91k q |
| RunPod Secure H100 SXM $3.99 | $2,913 | 2.08M q (12.5B tokens) | 1.15M q | 146k q |
| Lambda H100 SXM $4.29 | $3,132 | 2.24M q (13.4B tokens) | 1.24M q | 157k q |
| GCP a2-ultragpu-1g $5.0688 | $3,700 | 2.64M q (15.9B tokens) | 1.46M q | 185k q |
| AWS p5.4xlarge $6.88 | $5,022 | 3.59M q (21.5B tokens) | 1.98M q | 251k q |
| GCP a3-highgpu-1g $11.0612 | $8,075 | 5.77M q (34.6B tokens) | 3.19M q | 404k q |

The cheaper Gemma 4 26B A4B MoE API ($0.00056/q) moves the break-even for a
$1,307 GPU to 2.3M questions a month. [DOC cost.md §9]. For the token
columns, the 13.4B, 15.9B and 21.5B figures were added here with the same
arithmetic (INFERRED).

**Corrected headline ranges** (verifier, [DOC cost.md §0 item 7, verification
pass claim 12]):

| Model class | All rows | RunPod Secure, GCP and AWS only |
|---|---|---|
| 8B vs 8–9B API | 2.4–14.9B tokens/month (0.41–2.48M q) | 4.0–10.7B tokens/month |
| 31B vs Gemma 4 31B API | 2.1–34.6B tokens/month (0.35–5.77M q) | 5.6–34.6B tokens/month |

The researcher's original "2.4–8B / 5.6–12.5B" was a selection of rows, and the
2.4B low end is the Vast.ai marketplace row. The conclusion does not change.

### 8.5 Can one GPU serve Q*?

No, not for 31B. The Gemma 4 31B break-even on RunPod (0.93M q/month) is at or
above one A100's practical capacity. With a 3–5x daytime peak, one A100 sized
for peak serves about 0.16–0.53M questions a month on average (§5). At
H100-class prices (2.1M+), Q* is well beyond one GPU. An 8B model on one L4 is
plausible at the low end of the 8B break-even range and tight at the high end
[DOC cost.md §9] INFERRED.

### 8.6 Two GPUs for availability

A single self-hosted GPU is a single point of failure. Marketplace hosts
(Vast.ai, RunPod Community) add pre-emption and host-quality risk. A 99.9%
target needs at least 2 GPUs on separate hosts or zones, which **doubles every
self-host figure** [DOC cost.md §9] INFERRED:

| Pair | $/month | Q* |
|---|---|---|
| 2x RunPod Secure L4 (8B) | $861 | 2.61M q vs Llama 3.1 8B; 1.33M q vs Qwen3.5 9B |
| 2x RunPod Secure A100-80GB (31B) | $2,613 | ~1.9M q vs Gemma 4 31B API |
| 2x Lambda H100 SXM (31B) | $6,263 | ~4.5M q vs Gemma 4 31B API |

Paid APIs offer redundancy almost for free: 15 endpoints for Gemma 4 31B and
5 for Nemotron 3 Ultra (§4.1). That is the cheapest route to ~99.5%+
(INFERRED). The free tier has no SLA (§2.4).

### 8.7 Scale to zero

Scale to zero helps only when a 30 s to several-minute cold start is
acceptable, and it is billed on RunPod (§6.4). That rules out interactive
/api/ask, given the 7 s and 60 s timeouts in §5. It is fine for batch
evaluation and fine-tuning experiments [DOC cost.md §9] INFERRED.

### 8.8 Verdict

On cost alone, self-hosting a 27–32B model does not beat the open-model API for
Waymaker. Self-hosting an 8B model wins only above roughly 2.4–15B tokens a
month (0.4–2.5M questions) with steady utilisation, and the number doubles
with a second GPU. The comparison flips only against a frontier API: Sonnet 5.5
breaks even at ~65k questions a month on a RunPod A100. Quality is not
equivalent there, though, and has to be shown by evaluation first
([12](12-evaluation-methodology.md)). [DOC cost.md §9] INFERRED.

There are non-cost reasons to self-host anyway: serving a fine-tuned model that
no API hosts, keeping user questions away from free tiers that train on
content, and pinning exact weights for audit. Fireworks serves fine-tuned
models at base-model prices [DOC https://fireworks.ai/pricing,
accessed 2026-10-19] VERIFIED, which removes the first reason for its
supported base models.

**Again: open-source frameworks do not make GPUs free.** vLLM or Unsloth
removes the licence fee, not the $264–$8,075 a month per GPU, the idle hours,
the second GPU for availability, or the on-call time.

## 9. Evidence quality and caveats

- **ENOSPC during research.** The Mac's data volume sat at 97–100% used
  (about 180–560 MiB free) for the whole cost research. Many Bash and Write
  calls failed with `ENOSPC: no space left on device`. The researcher deleted
  only its own scratch files, including `webdata/openrouter_models.json`, the
  788,482-byte catalog capture behind §4.1 [DOC cost.md §12 item 9]. On
  2026-10-20, `scratchpad/webdata/` held only the three `:free` endpoint JSONs
  (OBSERVED). So **no local capture or sha256 exists for the catalog prices**.
  Their evidence is two independent live fetches (03:57 and ~04:35 UTC) that
  matched. Most pricing pages were read through a fetch tool that summarises,
  so they carry a URL and access date but no capture hash. Re-checking any
  price means fetching it again. The prompt-measurement script and the
  verifier's output survived (§3).
- **Secondary sources.** GCP and AWS prices come from aggregators, not the
  official pages, which did not render. Colab burn rates, Colab Enterprise,
  Kaggle quotas and Lightning AI are UNVERIFIED.
- **Fetch failures**, recorded verbatim in the note: openai.com/api/pricing HTTP
  403; lightning.ai/pricing HTTP 503 (Retry-After 3600); build.nvidia.com/faq
  HTTP 404; gcloud-compute.com/gpus.html 404; the cloud.google.com GPU,
  Colab and Vertex AI pricing pages returned titles only; kaggle.com docs
  returned titles only; the vast.ai/pricing grid did not render; groq.com/pricing
  had no price table [DOC cost.md §12 item 6].
- **Drift.** Prices, endpoint counts and uptime are snapshots from 2026-10-19.
  Gemini 3.8 Flash has an announced increase on 2027-01-01. Free ids disappear
  from the catalog without notice (§2.3).
- **The verifier stopped early.** After ~29 requests its web fetch tool hit a
  session limit, so the Groq price could not be re-fetched [DOC cost.md,
  verification pass].
- **No network was used to write this document.** Every price is the note's
  value; nothing was re-fetched on 2026-10-20.

## 10. Open questions and not done

- Real monthly volumes for /api/ask, Quick Answer and enforcement (Railway HTTP
  metrics, Vercel analytics, OpenRouter activity), and real completion lengths:
  UNKNOWN.
- Has the OpenRouter account ever bought 10 or more credits (50/day vs
  1,000/day)? UNKNOWN.
- Is the paid production enforcement chain intended, and how much does it
  spend? UNKNOWN (owner question; SEC-14).
- Which Vercel env overrides replace the dead Node default ids? Not inspected.
- Do the NVIDIA trial terms and Google's free-tier data terms bind
  OpenRouter-mediated calls? UNVERIFIED (REQUIRES LEGAL REVIEW). The Thinking
  Machines research-tier terms were not extractable.
- Not priced (UNKNOWN): the Groq `llama-3.1-8b-instant` price; NVIDIA
  build.nvidia.com per-id pricing and limits; NVIDIA AI Enterprise; Vertex AI
  Gemini tuning; Gemma 4 managed tuning; Lightning AI's current free tier; the
  Kaggle quota on a primary page; official GCP and AWS GPU pages; L40S on GCP;
  Seoul and Tokyo region GPUs; paid observability tools; Railway and Vercel
  hosting.
- Korean tokenizer efficiency of Gemma 4 and Nemotron (tokens per Hangul
  syllable) was not measured. The §3 band is an estimate.
- The stable share of the prompt (the upside from caching) was not measured.
- No throughput was measured on any GPU. Every capacity and QLoRA speed figure
  in §5 and §6.3 is an assumption.

## 11. Research-note sections drawn from

- [research-notes/cost.md](research-notes/cost.md): header (open-source
  statement); §0 items 1–9 with every verifier correction; §1 (chains,
  catalog drift, free providers, terms); §2 (telemetry, measured prompt,
  planning profiles); §3 (OpenRouter prices, provider spread, platform terms,
  Google direct, NVIDIA catalog); §4 (frontier prices, notes, monthly table);
  §5 (free and low-cost GPU); §6 (GPU rental and its sources); §7 (managed
  fine-tuning, worked example); §8 (serverless, dedicated, storage, sizes);
  §9 (break-even, capacity, latency and availability, non-cost reasons); §10
  (categories); §11 (scenarios 1–4 with verifier corrections); §12 (live
  actions, failures, ENOSPC); §13 (open questions); verification pass (claims
  1–15, other corrections, omissions).
- [research-notes/live_health.json](research-notes/live_health.json) and
  [research-notes/live_health_ai.json](research-notes/live_health_ai.json):
  production provider and model configuration, re-read 2026-10-20.
- Related documents: [00](00-executive-summary.md),
  [01](01-existing-system-audit.md), [08](08-foundation-model-research.md),
  [09](09-training-and-distillation.md), [10](10-athena-and-hestia-strategy.md),
  [11](11-dataset-governance.md), [12](12-evaluation-methodology.md),
  [13](13-artemis-experiment.md) §11 (Artemis arm costs),
  [15](15-security-and-deployment.md) §3.15 and T9,
  [16](16-validation-results.md), [17](17-mission-002-plan.md).
