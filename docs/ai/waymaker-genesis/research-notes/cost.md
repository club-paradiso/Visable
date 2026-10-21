# Waymaker AI options: hardware and cost model (dated prices)

Mission 001 "Waymaker Genesis". All lookups made on **2026-10-19** (UTC 03:57-04:30).
Audited code: clean worktree of `origin/main` @ `0713370` at `/Users/seonjaekim/dev/Visable-genesis`.
All prices are USD list prices as displayed on the cited page on 2026-10-19 unless marked otherwise. Taxes, regional premiums and negotiated discounts are excluded.

Status legend: VERIFIED (I checked the primary evidence), OBSERVED (seen live), README-ONLY (only docs say so), INFERRED (my reasoning or arithmetic), UNVERIFIED (secondary source or failed fetch).

> **Open-source frameworks do not make GPUs free.** vLLM, SGLang, TGI, Unsloth, Axolotl, PEFT and similar are free software, but every self-hosted or fine-tuned model still needs a GPU billed per hour (or per second) whether or not it is answering questions. Open weights remove the per-token fee; they do not remove hardware, idle time, redundancy, storage, monitoring or engineering cost.

---

## 0. Executive summary

1. **Waymaker's live AI spend is designed to be $0.** Every default model id in the backend is an OpenRouter `:free` variant [CODE backend/services/model_policy.py:23-36, 99-118] VERIFIED; the policy doc says "Cost posture: free tier by default" [DOC docs/ai/AI_PROVIDER_AND_MODEL_POLICY.md:81-85] README-ONLY. The direct NVIDIA NIM provider is a fail-closed scaffold, "not wired to /api/ask" [CODE backend/services/providers/nvidia_nim.py:1, 47-58] VERIFIED. [corrected by verifier: "every default model id" holds for the general chains only. The code default `DEFAULT_CHINESE_MODEL = "minimax/minimax-m3"` is a paid id (unwired) [CODE model_policy.py:120], and Groq/NIM are non-OpenRouter. More importantly, **production is not all-`:free`**: the live `/api/health/ai` snapshot (saved at scratchpad/live/health_ai.json, GET by another agent 2026-10-19 03:37 UTC and again 04:19 UTC; re-read by verifier) shows `enforcement_structured` = `openai/gpt-oss-20b`, `google/gemma-4-31b-it`, `openai/gpt-oss-120b`, i.e. **paid ids** ($0.018/$0.09, $0.20/$0.40, $0.15/$0.60 per 1M [LIVE GET openrouter.ai/api/v1/models by verifier, 2026-10-19 ~04:35 UTC, 471 models]), and `model_env_overrides_allowed: true`. That chain is wired: `_enforcement_ai_provider` calls `resolve_task_models(ENFORCEMENT_STRUCTURED)` with `max_tokens=900` [CODE backend/paradiso_backend.py:8415-8440] VERIFIED. So production enforcement extraction/prediction spends real (small) money per call, about $0.00015 (gpt-oss-20b) to $0.0012 (Gemma 4 31B) per 4k-in/900-out call (INFERRED arithmetic). It also needs a positive OpenRouter balance; otherwise calls return 402. OBSERVED (config), INFERRED (spend)]
2. **The binding constraint is OpenRouter's free quota, not money.** Free variants allow 20 requests/min and **50/day if the account has bought fewer than 10 credits, 1,000/day after at least 10** [DOC https://openrouter.ai/docs/api-reference/limits, accessed 2026-10-19] VERIFIED. The pricing FAQ adds that **failed attempts count toward the cap** [DOC https://openrouter.ai/pricing, accessed 2026-10-19] VERIFIED (as summarised by the fetch tool). The model-variant guide says the threshold counts lifetime purchases and the limits are account-wide, not per model [DOC https://openrouter.ai/docs/guides/routing/model-variants/free, via search snippet 2026-10-19] UNVERIFIED-snippet; [corrected by verifier: re-fetched 2026-10-19, that guide page states neither the threshold nor account-wide scoping (it says only that free variants "may have different rate limits or availability"). The limits page itself says the threshold counts credits purchased "all-time", that extra accounts/keys do not raise limits ("we govern capacity globally"), and also that OpenRouter has "different rate limits for different models". The fetch tool also reported that the higher daily ceiling starts one credit early, at 9 credits. Account-wide scoping is documented only by the repo's own 429-body comment. DOC re-fetched by verifier] the runtime already treats the bucket as account-wide [CODE backend/services/ai_runtime.py:346-365] VERIFIED. At zero spend Waymaker therefore tops out near **1,500 LLM calls/month** (<10 credits ever bought) or **~30,000 LLM calls/month** (>=10 bought), shared by /api/ask, Quick Answer, enforcement and the nationality coach. INFERRED.
3. **The repo has no usage telemetry with request or token counts.** The `ask_routing` log line records models, latency and errors, not tokens [DOC docs/ai/WAYMAKER_ANSWER_PRODUCT_QUALITY_2026_09.md:100-103] README-ONLY; no code reads `usage` / `prompt_tokens` from provider responses (grep, section 2) VERIFIED. Volumes below are scenarios, not measurements.
4. **I measured the real /api/ask prompt offline**: 12.3k-14.1k characters, about **3.1k-4.8k input tokens**, `max_tokens` 900 (fast) / 1,400 (basic), with law grounding disabled [LIVE offline stub run, 2026-10-19, 5 cases, all HTTP 200] OBSERVED. Planning figure: **5k input + 1k output tokens per question**. [corrected by verifier: the stub captured only the user prompt. When `system_prompt` is None, `_call_openrouter` sends `_llm_messages`, which adds the default `WAYMAKER_SYSTEM_PROMPT` (2,186 chars, about 490-625 tokens) [CODE backend/paradiso_backend.py:1342-1353, 1381, 2954-2955] VERIFIED. Real input is therefore ~14.5k-16.3k chars, **~3.6k-5.4k tokens**, before chat-template overhead. Production also runs with law grounding **enabled** (`/health` and `/api/health/ai`: mode `enabled`, effective `enabled`, active [scratchpad/live/health*.json, 03:37 UTC]), so live prompts are larger than this offline measurement. The 5k planning figure is a reasonable middle value, not an upper bound. Verifier re-ran the script: identical char counts, 5/5 HTTP 200, worktree clean]
5. **Paying for the same open models is cheap.** The paid (non-`:free`) OpenRouter ids of the current chain cost $0.0006-$0.0054 per question at 5k/1k tokens: Gemma 4 31B $0.20/$0.40 per 1M, Nemotron 3 Ultra $0.60/$2.40 [LIVE GET https://openrouter.ai/api/v1/models, 2026-10-19, HTTP 200] VERIFIED. At 10k questions/month that is about $14 (Gemma 4 31B) to $54 (Nemotron 3 Ultra), plus OpenRouter's 5.5% credit-purchase fee.
6. **Frontier reasoning APIs cost 10-40x more per question**: Claude Sonnet 5.5 $2/$10, Opus 5.5 $4/$20 [DOC https://platform.claude.com/docs/en/about-claude/pricing]; GPT-5.6-terra $2/$12, GPT-5.6-sol $4/$20 [DOC https://developers.openai.com/api/docs/pricing]; Gemini 3.1 Pro Preview $2/$12 (<=200k) [DOC https://ai.google.dev/gemini-api/docs/pricing] VERIFIED. That is $0.020-$0.055 per question, or $200-$550 for 10k questions/month.
7. **Self-hosting does not beat the API at plausible Waymaker volumes.** A 24/7 L4 for a 7-9B model costs about $264-$588/month. A 24/7 A100-80GB/H100 for a 27-32B model costs about $488-$8,075/month depending on provider. Break-even against the equivalent open-model API is about **2.4-8 billion tokens/month for 8B** and **5.6-12.5 billion tokens/month for 31B** on reputable hosts, i.e. **~0.4-2 million questions/month**, which is at or beyond what one GPU serves. Two GPUs for availability double the break-even. INFERRED (section 9). [corrected by verifier: the arithmetic in section 9 checks out row by row, but these headline ranges are a selection. The 2.4 B low end is the Vast.ai marketplace row, not a "reputable host". Across every row in section 9 the range is 2.4-14.9 B tokens/month for 8B (Vast vs Qwen 9B, up to Modal vs Llama 8B) and 2.1-34.6 B tokens/month for 31B against the Gemma 4 31B API (Vast A100, up to GCP a3). On RunPod Secure, GCP and AWS alone it is 4.0-10.7 B for 8B and 5.6-34.6 B for 31B. INFERRED]
8. **Managed fine-tuning is affordable for experiments**: Together AI $0.34 per 1M training tokens up to 16B and $1.05 per 1M for Gemma 4 31B (minimum $4/job) [DOC https://www.together.ai/pricing]; Fireworks LoRA SFT $0.50 (<=16B) and $3.00 (16.1-80B) [DOC https://fireworks.ai/pricing] VERIFIED. **OpenAI's fine-tuning is being wound down and new users can no longer access it** [DOC https://developers.openai.com/api/docs/pricing] VERIFIED.
9. **Free endpoints carry trial or research terms.** OpenRouter's provider registry links the Nvidia free provider to the "NVIDIA API Trial Terms of Service" and Thinking Machines to a "free research API tier" ToS; Google's free tier uses content to improve its products [LIVE GET https://openrouter.ai/api/v1/providers, 2026-10-19] [DOC ai.google.dev pricing] VERIFIED. Whether those terms allow a public production service is not established (the NVIDIA PDF did not extract). UNVERIFIED. [corrected by verifier: the verifier extracted the NVIDIA PDF's text (FlateDecode streams inflated with Python stdlib `zlib`; file metadata dated 2025-10-07). §1.2 "Trial Access Rights" grants access "for limited trial purposes only and without use of the API Service or Generated Content in production". §1.4 "Trial Terms and Credits" says that without a separate Subscription "you may only use the API Service for internal testing and evaluation purposes, not in production" [DOC https://assets.ngc.nvidia.com/products/api-catalog/legal/NVIDIA%20API%20Trial%20Terms%20of%20Service.pdf, accessed 2026-10-19] VERIFIED. So the NVIDIA terms OpenRouter links for its Nvidia `:free` provider **exclude production use**. Whether they bind OpenRouter-mediated calls, as opposed to OpenRouter's own agreement with NVIDIA, is still UNVERIFIED. The Thinking Machines PDF's text uses glyph-encoded fonts and was not extractable: UNVERIFIED]

---

## 1. What Waymaker calls today (origin/main)

| Path | Model chain (in order) | max_tokens | Evidence |
|---|---|---|---|
| /api/ask Basic (default) | `nvidia/nemotron-3-ultra-550b-a55b:free` -> `google/gemma-4-31b-it:free` -> `nvidia/nemotron-3-super-120b-a12b:free` -> `thinkingmachines/inkling:free` | 1,400 (`OPENROUTER_MAX_TOKENS`) | [CODE backend/services/model_policy.py:31-37] [CODE backend/paradiso_backend.py:325] VERIFIED |
| /api/ask Fast | `google/gemma-4-26b-a4b-it:free` -> `nvidia/nemotron-3.5-lightning:free` -> `thinkingmachines/inkling-small:free` -> `google/gemma-4-31b-it:free` | 900 (`OPENROUTER_FAST_MAX_TOKENS`) | [CODE model_policy.py:99-105] [CODE paradiso_backend.py:326, 6484-6486] VERIFIED |
| Pro tier | not wired ("coming soon") | - | [CODE model_policy.py:47, 298-307] VERIFIED |
| Router / translation | `google/gemma-4-31b-it:free` | - | [CODE model_policy.py:23-24] VERIFIED |
| Verifier | `nvidia/nemotron-3-super-120b-a12b:free` | - | [CODE model_policy.py:118] VERIFIED [corrected by verifier: that is the code default only. `AI_VERIFIER_MODEL` is read through `_env`, not the opt-in-gated `_model_env` [CODE model_policy.py:210]. Production's `/api/health/ai` verifier chain leads with `openai/gpt-oss-120b:free` [scratchpad/live/health_ai.json, 03:37 UTC], which is absent from the catalog (dead id)] |
| Enforcement structured (Python) | `google/gemma-4-26b-a4b-it:free` -> `nvidia/nemotron-3-super-120b-a12b:free` | 900 | [CODE model_policy.py:112-116] VERIFIED [corrected by verifier: code default only. Production runs **paid** `openai/gpt-oss-20b` -> `google/gemma-4-31b-it` -> `openai/gpt-oss-120b` (env override, `model_env_overrides_allowed: true`) [scratchpad/live/health_ai.json]. The path is wired at [CODE paradiso_backend.py:8426-8438], max_tokens 900] |
| Chinese-language route | `minimax/minimax-m3` (a **paid** id) + two `inclusionai/ling-3.0-*:free` | - | [CODE model_policy.py:120-124] VERIFIED; grep finds no caller outside model_policy.py, so this is policy-only and spends nothing today VERIFIED |
| Quick Answer wording (Node on Vercel) | `google/gemma-4-31b-it:free`, `openai/gpt-oss-120b:free`, `meta-llama/llama-3.3-70b-instruct:free` (env can override) | 400 | [CODE lib/waymaker-quick-answer-ai.js:18-34, 131] VERIFIED |
| Enforcement grounded AI (Node) | `openai/gpt-oss-120b:free`, `nousresearch/hermes-3-llama-3.1-405b:free`, `google/gemma-4-31b-it:free`, `meta-llama/llama-3.3-70b-instruct:free` | 1,800 | [CODE lib/enforcement-grounded-ai.js:13-18, 209] VERIFIED |
| Enforcement confirm (Node) | `google/gemma-4-31b-it:free` | 220 | [CODE api/enforcement/confirm.js:3, 130] VERIFIED |
| Groq fallback (off by default) | `llama-3.1-8b-instant` | - | [CODE paradiso_backend.py:345, 1222-1229] VERIFIED; Groq price UNKNOWN (groq.com/pricing returned no price table) |
| NVIDIA NIM direct (research/internal QA only) | `nvidia/nemotron-3-ultra-550b-a55b`, fail-closed, `ENABLE_NVIDIA_NIM_EXPERIMENTAL` off by default | 1,200 | [CODE backend/services/providers/nvidia_nim.py:1-58] VERIFIED |

Catalog drift found while pricing (affects reliability and free quota, not cash):
- **Not in OpenRouter's catalog on 2026-10-19**: `openai/gpt-oss-120b:free`, `meta-llama/llama-3.3-70b-instruct:free`, `nousresearch/hermes-3-llama-3.1-405b:free`, `inclusionai/ling-3.0-flash-sante:free`, `inclusionai/ling-3.0-flash-fin:free` [LIVE GET /api/v1/models: 471 models, only 16 `:free` ids] VERIFIED. Three of these are defaults in the Node paths (`lib/waymaker-quick-answer-ai.js:18`, `lib/enforcement-grounded-ai.js:13-18`, `api/enforcement/analyze.js:13`) unless a Vercel env override replaces them; the deploy env was not inspected. Each dead id is a failed attempt, and **failed attempts count toward the free daily cap**. INFERRED.
- The owner's unpushed branch `fix/waymaker-qa-2026-10-16` swaps `thinkingmachines/inkling:free` out of the Basic chain for `google/gemma-4-26b-a4b-it:free`, because Inkling "answered every call with 403 model_access_denied (Waymaker QA 2026-10-16)" [CODE git show fix/waymaker-qa-2026-10-16:backend/services/model_policy.py] VERIFIED. Inkling is still listed as free in the catalog, so a listed free id does not prove access.
- Tests for this layer pass on main: `71 passed, 85 subtests passed` [TEST backend/tests/test_model_policy.py backend/tests/test_ai_runtime.py (ran: pass)] VERIFIED.

Who serves the free endpoints (matters for data handling and uptime) [LIVE GET https://openrouter.ai/api/v1/models/{id}/endpoints for 3 ids, 2026-10-19, HTTP 200] VERIFIED:
- `google/gemma-4-31b-it:free` and `google/gemma-4-26b-a4b-it:free`: one provider, **Google AI Studio**, max completion 32,768, uptime_last_1d 100.
- `nvidia/nemotron-3-ultra-550b-a55b:free`: one provider, **Nvidia**, uptime_last_1d 96.7, max completion 65,536. [verifier re-fetch ~04:40 UTC: still one provider (Nvidia), max completion 65,536, context 1,000,000, uptime_last_1d **98.75**. This is a rolling metric, so both readings stand as snapshots]
- Google's pricing page says free-tier content for Gemma 4 and the Flash models is **used to improve Google's products** (paid tier: no) [DOC https://ai.google.dev/gemini-api/docs/pricing, "Last updated 2026-10-16 UTC"] VERIFIED. OpenRouter routes Gemma `:free` to Google AI Studio, so the same terms probably apply; I did not verify OpenRouter's pass-through terms. INFERRED. OpenRouter has an account setting to avoid providers that train, with "separate settings for paid and free models" [DOC https://openrouter.ai/docs/guides/privacy/provider-logging] VERIFIED; its effect on free-model availability is not stated. The backend prompt contains the user's typed question, so this is a privacy point as well as a cost point.
- Provider terms linked by OpenRouter [LIVE GET https://openrouter.ai/api/v1/providers, 2026-10-19] VERIFIED: Google AI Studio -> Google Cloud terms; Nvidia -> "NVIDIA API Trial Terms of Service" (PDF); Thinking Machines -> "free research API tier" terms. The NVIDIA PDF downloaded but its text did not extract (compressed streams, no PDF renderer on this Mac), so its production-use clause is UNVERIFIED; forum users read it as evaluation-only [WEB https://forums.developer.nvidia.com/t/clarification-on-trial-api-use/334275, accessed 2026-10-19] UNVERIFIED. [corrected by verifier: text now extracted. §1.2 says "limited trial purposes only and without use of the API Service or Generated Content in production", and §1.4 says "internal testing and evaluation purposes, not in production" unless you hold a Subscription. VERIFIED for the document. Whether it applies to OpenRouter pass-through is UNVERIFIED (see section 0, item 9)]

## 2. Usage volume: what the repo tells us

- Telemetry: one `ask_routing` JSON line per /api/ask with mode, models, upstream statuses and latency; "No prompt, answer or secret is logged" [DOC docs/ai/WAYMAKER_ANSWER_PRODUCT_QUALITY_2026_09.md:100-103] README-ONLY. The line printed in my run had no token fields [LIVE offline run log, 2026-10-19] OBSERVED.
- No code reads provider `usage` / `prompt_tokens` / `completion_tokens` (grep over backend, lib and api hit only unrelated scripts) VERIFIED. docs/ai, docs/ops and reports/ contain no request-volume or cost figures (grep for cost, usd, credit, monthly, volume) VERIFIED.
- Per-IP rate limits (a per-user ceiling, not a volume): /api/ask 8/min and 300/day; legal_research 4/min, 60/day; nationality_coach 6/min, 100/day; search_unified_ai 10/min, 200/day [CODE backend/paradiso_backend.py:5695, 7219, 7828, 8056] VERIFIED.
- Conclusion: **current monthly request volume is UNKNOWN.** Real counts are probably available from Railway HTTP metrics or the OpenRouter activity page; I did not query production systems (outside "public read-only GETs").

### Measured tokens per question (offline)
I replaced `_openrouter_complete_with_candidates` with a recording stub, blocked all outbound HTTP at the transport level, ran with a clean environment (no keys) and `LAW_GROUNDING_MODE=disabled`, and posted 5 questions to /api/ask through FastAPI's TestClient. Script: `/private/tmp/claude-501/-Users-seonjaekim-Downloads/041beae0-a4bd-4695-9a73-27a290ffa1c7/scratchpad/costscripts/measure_prompt.py`. The worktree stayed clean (`git status --porcelain` empty). [LIVE offline run 2026-10-19] OBSERVED.

| Case | Mode | Prompt chars | Hangul chars | Est. input tokens | max_tokens | First model |
|---|---|---|---|---|---|---|
| "D-2 연장시 필수 서류" | fast | 12,277 | 1,422 | 3,123-4,523 | 900 | gemma-4-26b-a4b-it:free |
| same | basic | 12,277 | 1,422 | 3,123-4,523 | 1,400 | nemotron-3-ultra:free |
| E-7 근무처 변경 + 사전 허가 | basic | 14,141 | 833 | 3,374-4,635 | 1,400 | nemotron-3-ultra:free |
| F-6 연장 서류·수수료 | basic | 13,130 | 827 | 3,148-4,342 | 1,400 | nemotron-3-ultra:free |
| English D-2 extension | basic | 13,700 | 1,253 | 3,392-4,809 | 1,400 | nemotron-3-ultra:free |

The token band is INFERRED (no tokenizer installed): Hangul 1-2 chars/token, other text 3.5-4.5 chars/token. Each case made exactly one LLM call. Production prompts are probably larger: law grounding (disabled here), conversation history (up to 2,000 chars per item) and context (up to 8,000 chars) can be added [CODE paradiso_backend.py:446-450] VERIFIED. Output length is unmeasured; the cap is 1,400. [corrected by verifier: (1) the "Prompt chars" column excludes the default system prompt (2,186 chars, ~0.5-0.6k tokens) that `_llm_messages` prepends [CODE paradiso_backend.py:1342-1353]. Add it to every row. (2) The history cap is up to **24 items** x 2,000 chars [CODE paradiso_backend.py:447-448], so a long conversation can add up to ~48k chars (roughly 12k-20k tokens; INFERRED band), plus up to 8,000 context chars. A "long-thread" profile of ~15-25k input tokens is plausible for some users. (3) Production has law grounding enabled (see section 0, item 4)]

**Planning profiles (INFERRED):**
- *Standard*: 5,000 input + 1,000 output = 6,000 tokens per question.
- *Heavy reasoning*: 8,000 input + 3,000 output (reasoning models bill thinking tokens as output; the backend caps output at 1,400 today, but a paid reasoning model with a raised cap would use more).
- Scenario volumes: 1k / 10k / 100k questions/month = 6M / 60M / 600M tokens/month (standard).

## 3. Prices for the models Waymaker uses (OpenRouter, live catalog)

Source for every row: [LIVE GET https://openrouter.ai/api/v1/models, 2026-10-19 03:57 UTC, HTTP 200, 788,482 bytes] VERIFIED. Prices per 1M tokens; the headline price is OpenRouter's catalog price for the id.

| Model id | `:free` listed? | Paid input | Paid output | Context (paid) | $/question, standard (5k/1k) |
|---|---|---|---|---|---|
| google/gemma-4-31b-it | yes ($0) | $0.20 | $0.40 | 262,144 | $0.00140 |
| google/gemma-4-26b-a4b-it | yes ($0) | $0.0675 | $0.225 | 262,144 | $0.00056 |
| nvidia/nemotron-3-ultra-550b-a55b | yes ($0) | $0.60 | $2.40 | 262,144 | $0.00540 |
| nvidia/nemotron-3-super-120b-a12b | yes ($0) | $0.08 | $0.45 | 262,144 | $0.00085 |
| nvidia/nemotron-3.5-lightning | yes ($0) | $0.07 | $0.20 | 262,144 | $0.00055 |
| thinkingmachines/inkling | yes ($0; 403 per owner QA) | $1.00 | $4.05 | 524,288 | $0.00905 |
| thinkingmachines/inkling-small | yes ($0) | $0.45 | $1.20 | 524,288 | $0.00345 |
| openai/gpt-oss-120b | **no** (`:free` gone) | $0.15 | $0.60 | 131,072 | $0.00135 |
| meta-llama/llama-3.3-70b-instruct | **no** | $0.10 | $0.32 | 131,072 | $0.00082 |
| nousresearch/hermes-3-llama-3.1-405b | **no** | $1.00 | $1.00 | 131,072 | $0.00600 |
| minimax/minimax-m3 (Chinese route, unwired) | paid only | $0.30 | $1.20 | 1,048,576 | $0.00270 |

Provider spread behind the paid ids [WebFetch of https://openrouter.ai/api/v1/models/{id}/endpoints, 2026-10-19] VERIFIED:
- `google/gemma-4-31b-it`: 15 endpoints, input $0.10-$0.75 and output $0.32-$1.00 per 1M. The cheapest (CoreWeave, Venice, Chutes) run **fp4** quantization; bf16/fp8 endpoints (Crusoe, Parasail, DeepInfra fp8) are $0.14-$0.20 in / $0.40 out. Uptime_last_1d ranges from 65% (Novita) to 100%.
- `nvidia/nemotron-3-ultra-550b-a55b`: 5 endpoints (DeepInfra fp4, BaseTen fp4, Venice fp8), $0.40-$0.625 in / $1.76-$3.125 out.
- Pinning a provider and quantization matters for answer quality; the cheapest row is not automatically the right one. INFERRED.

OpenRouter platform terms [DOC https://openrouter.ai/pricing, accessed 2026-10-19] VERIFIED: Free plan (no purchases, "25+ free models from 4 free providers"); pay-as-you-go **5.5% fee on credit purchases** (Business 8%); BYOK free up to $25,000/month of list-price inference, then 5%. A negative balance returns 402 even for free models [DOC https://openrouter.ai/docs/api-reference/limits] VERIFIED.

Google direct (Gemini API) [DOC https://ai.google.dev/gemini-api/docs/pricing, "Last updated 2026-10-16 UTC"] VERIFIED: **Gemma 4 is free-tier only ("Not available" on the paid tier)**, and free-tier content is used to improve products. Free-tier RPM/TPM/RPD are not published; the rate-limit page says limits "can be viewed in Google AI Studio" [DOC https://ai.google.dev/gemini-api/docs/rate-limits] VERIFIED. Paid tiers: Tier 1 = linked billing (cap $250), Tier 2 = $100 paid + 3 days (cap $2,000), Tier 3 = $1,000 paid + 30 days. So paying for Gemma 4 with a no-training guarantee means a third-party host (OpenRouter paid providers; Together $0.39/$0.97 for Gemma 4 31B [DOC https://www.together.ai/pricing] VERIFIED) or self-hosting.

NVIDIA API catalog (build.nvidia.com) free trial: about **40 RPM**; limits "vary by model, use case, and traffic"; no official way to raise them on the same tier; production means deploying a NIM [DOC https://forums.developer.nvidia.com/t/request-for-nvidia-nim-api-rate-limit-increase-40-200-rpm/375340, thread dated 2026-07-02, moderator reply quoted second-hand] UNVERIFIED. Starting credits (1,000, requestable to 5,000) appear only in user posts and third-party guides UNVERIFIED. `https://build.nvidia.com/faq` returned **HTTP 404** [LIVE 2026-10-19]. NVIDIA AI Enterprise licence price: UNKNOWN (not looked up).

## 4. Stronger paid reasoning APIs, per 1M tokens

| Model | Input | Output | Cache read | $/q standard (5k/1k) | $/q heavy (8k/3k) | Source / status |
|---|---|---|---|---|---|---|
| Claude Opus 5.5 | $4 | $20 | $0.20 | $0.040 | $0.092 | [DOC platform.claude.com pricing] VERIFIED |
| Claude Sonnet 5.5 | $2 | $10 | $0.10 | $0.020 | $0.046 | same, VERIFIED |
| Claude Sonnet 5 | $2 | $10 | $0.20 | $0.020 | $0.046 | same; footnote: the $2/$10 intro price is now standard, VERIFIED |
| Claude Haiku 5.5 (prompts <=100k) | $0.10 | $0.50 | $0.01 | $0.0010 | $0.0023 | same, VERIFIED |
| Claude Haiku 4.5 | $1 | $5 | $0.10 | $0.010 | $0.023 | same, VERIFIED |
| Claude Fable 5.1 | $10 | $50 | $0.25 | $0.100 | $0.230 | same, VERIFIED |
| GPT-5.6-sol | $4.00 | $20.00 | $0.40 | $0.040 | $0.092 | [DOC developers.openai.com/api/docs/pricing] VERIFIED |
| GPT-5.6-terra | $2.00 | $12.00 | $0.20 | $0.022 | $0.052 | same, VERIFIED |
| GPT-5.5 (<272K) | $5.00 | $30.00 | $0.50 | $0.055 | $0.130 | same, VERIFIED |
| GPT-5.4 (<272K) | $2.50 | $15.00 | $0.25 | $0.0275 | $0.065 | same, VERIFIED |
| GPT-5.6-luna | $0.20 | $1.20 | $0.02 | $0.0022 | $0.0052 | same, VERIFIED |
| GPT-5-mini | $0.25 | $2.00 | $0.025 | $0.00325 | $0.008 | same, VERIFIED |
| Gemini 3.1 Pro Preview (<=200k) | $2.00 | $12.00 | - | $0.022 | $0.052 | [DOC ai.google.dev pricing] VERIFIED; no free tier |
| Gemini 2.5 Pro (<=200k) | $1.25 | $10.00 | - | $0.01625 | $0.040 | same; has a free tier, VERIFIED |
| Gemini 3.8 Flash | $0.75, rising to $1.50 on 2027-01-01 | $3.75, rising to $7.50 | - | $0.0075 -> $0.015 | $0.0173 -> $0.0345 | same, VERIFIED |
| Gemini 2.5 Flash-Lite | $0.10 | $0.40 | - | $0.0009 | $0.0020 | same, VERIFIED |
| google/gemini-4-argon (seen on OpenRouter only) | $2.00 | $10.00 | - | $0.020 | $0.046 | [LIVE OpenRouter catalog] VERIFIED; first-party price UNKNOWN |

Notes:
- OpenRouter lists the same list prices for these ids (for example `anthropic/claude-sonnet-5.5` $2/$10, `openai/gpt-5.6-terra` $2/$12, `google/gemini-3.1-pro-preview` $2/$12) plus `:batch` variants at 50% [LIVE OpenRouter catalog] VERIFIED. Buying through OpenRouter adds the 5.5% purchase fee; going direct does not.
- Anthropic says Claude 4.7 and later use a tokenizer that produces "approximately 30% more tokens for the same text" [DOC platform.claude.com pricing] VERIFIED, so Claude's cost per *question* can be ~1.3x the per-token comparison. The effect on Korean text is unmeasured.
- Prompt caching could cut input cost a lot if Waymaker's long instruction/evidence prefix is stable between calls (Sonnet 5.5 cache reads are 0.05x base). The static share of the prompt is unmeasured. INFERRED.
- Batch pricing (50% off) does not suit interactive answers but does suit offline evaluation and dataset generation. INFERRED.
- `openai.com/api/pricing/` returned **HTTP 403** to the fetch tool; `developers.openai.com/api/docs/pricing` worked [LIVE 2026-10-19].

### Monthly API cost by scenario (standard profile, list price, no fees)

| Model | 1k q/mo (6M tok) | 10k q/mo (60M tok) | 100k q/mo (600M tok) |
|---|---|---|---|
| Current chain, `:free` | $0, but capped (section 0, item 2) | not reachable on free quota | not reachable |
| Gemma 4 26B A4B, paid | $0.56 | $5.63 | $56 |
| Gemma 4 31B, paid | $1.40 | $14.00 | $140 |
| Nemotron 3 Ultra, paid | $5.40 | $54 | $540 |
| Claude Haiku 5.5 | $1.00 | $10 | $100 |
| Gemini 3.8 Flash (2026 / 2027 price) | $7.50 / $15 | $75 / $150 | $750 / $1,500 |
| Claude Sonnet 5.5 | $20 | $200 | $2,000 |
| GPT-5.6-terra or Gemini 3.1 Pro | $22 | $220 | $2,200 |
| Claude Opus 5.5 or GPT-5.6-sol | $40 | $400 | $4,000 |

All INFERRED arithmetic on VERIFIED unit prices. Add 5.5% when buying OpenRouter credits. Add a 5-10% margin for retries and calls that time out mid-stream (INFERRED; providers generally do not bill requests that return no tokens).

## 5. Free and low-cost GPU for experiments

| Service | What you get | Price | Evidence / status |
|---|---|---|---|
| Google Colab Free | Intermittent T4-class GPU, no guarantee | $0 | Not quantified on a primary page; UNVERIFIED |
| Colab Pro | 100 compute units/month | **$9.99/mo** | Signup HTML attribute `formattedProSubscriptionPrice="$9.99"` [LIVE curl https://colab.research.google.com/signup, 2026-10-19, page served for region KR] VERIFIED; the 100 CU allotment comes from plan naming and secondary sources, INFERRED |
| Colab Pro+ | 500 compute units/month | **$49.99/mo** | `formattedVeryProSubscriptionPrice="$49.99"` [same LIVE] VERIFIED; CU count INFERRED |
| Colab Pay As You Go | 100 CU or 500 CU packs | $9.99 / $49.99 | `formattedCCU100Price="$9.99"`, `formattedCCU500Price="$49.99"` [same LIVE] VERIFIED |
| Colab burn rates | T4 ~1.2-1.8 CU/h, A100 ~15 CU/h; L4/H100 unpublished | ~$0.12-0.18/h T4, ~$1.50/h A100 at $0.10/CU | Google publishes no table; third-party measurements [WEB https://gpuperhour.com/blog/google-colab-alternatives, accessed 2026-10-19] UNVERIFIED |
| Colab Enterprise (GCP) | T4 ~$0.42/h, L4 ~$0.672/h, A100 ~$3.52/h | per hour | Search snippet of https://cloud.google.com/colab/pricing; the page did not render in fetch. UNVERIFIED |
| Kaggle Notebooks | ~30 GPU-hours/week (P100 or 2x T4), 9-12 h sessions | $0 | Official pages returned only titles [LIVE WebFetch https://www.kaggle.com/docs/efficient-gpu-usage and /docs/notebooks]; figures from secondary guides [WEB https://gpuperhour.com/blog/free-cloud-gpus-and-credits] UNVERIFIED |
| Hugging Face ZeroGPU | Half an RTX Pro 6000 Blackwell (48 GB) per call; daily quota 2 min unauthenticated, 5 min free account, 40 min PRO/Team, 60 min Enterprise; beyond quota $1 per 10 min (PRO and up); Gradio only; free accounts can host 2 ZeroGPU Spaces, PRO 10 | $0 / PRO $9/mo | [DOC https://huggingface.co/docs/hub/spaces-zerogpu] VERIFIED |
| HF PRO | 8x ZeroGPU quota, $2/month compute credits, 1 TB private storage | $9/mo | [DOC https://huggingface.co/pricing] [DOC https://huggingface.co/docs/inference-providers/pricing] VERIFIED |
| HF Inference Providers | Pass-through provider prices, "no markup"; free users need purchased credits | per token | [DOC https://huggingface.co/docs/inference-providers/pricing] VERIFIED |
| HF Spaces GPU | T4 small $0.40/h, T4 medium $0.60, L4 $0.80, L40S $1.80, A10G small $1.00, A10G large $1.50, A100 large $2.50 | per hour | [DOC https://huggingface.co/pricing] VERIFIED |
| HF AutoTrain | Free when run locally; on Spaces billed per minute at the Spaces hardware rate | hardware rate | [DOC https://huggingface.co/docs/autotrain/en/cost] VERIFIED |
| Modal Starter | **$30/month free credits**; Team $250/mo including $100 credits | per second | [DOC https://modal.com/pricing] VERIFIED. $30 is ~37 L4-hours or ~7.6 H100-hours of GPU-only time (INFERRED; CPU and RAM are billed on top) |
| Lightning AI | Official page **HTTP 503, Retry-After: 3600** [LIVE WebFetch https://lightning.ai/pricing, 2026-10-19]. A tracker reports a Sept 2026 switch to a one-time grant of up to 30 credits (12-month expiry) and rates T4 $0.55, L4 $0.79, A100-40GB $2.19, H100 $4.50 [WEB https://www.usagepricing.com/blueprint/activity/lightning-ai-2026-09-21-gpu-rate-card-reprice] | - | UNVERIFIED |
| NVIDIA build.nvidia.com | Hosted trial inference ~40 RPM (no raw GPU) | $0 | UNVERIFIED (section 3) |

## 6. On-demand GPU rental (per GPU-hour)

| GPU (VRAM) | RunPod Secure / Community | Lambda (1x) | Vast.ai live (min / median, 1-GPU on-demand) | Modal (GPU only) | HF Inference Endpoints | Google Cloud us-central1 (whole VM: on-demand / spot) | AWS (whole instance: on-demand / spot) |
|---|---|---|---|---|---|---|---|
| T4 (16 GB) | not listed | not offered | $0.15 / $0.15 (n=3) | $0.59 | $0.50 | ~$0.35 per GPU + N1 VM (snippet, UNVERIFIED) | g4dn.xlarge $0.526 / $0.332 |
| L4 (24 GB) | $0.59 / $0.44 | not offered | $0.362 / $0.362 (n=4) | $0.80 | $0.80 | g2-standard-4 $0.7068 / $0.423 | g6.xlarge $0.8048 / $0.637 |
| A10 / A10G (24 GB) | not listed | A10 $1.29 | A10 $0.243 (n=2) | A10 $1.10 | not listed | n/a | g5.xlarge (A10G) $1.006 / $0.478 |
| L40S (48 GB) | $1.09 / $0.79 | - | $0.402 / $0.801 (n=9) | $1.95 | $1.80 | not fetched (UNKNOWN) | g6e.xlarge $1.861 / $1.713 |
| A100 40 GB | - | PCIe or SXM $1.99 | 40/80 GB mixed: PCIe $0.366 / $0.735 (n=16); SXM4 $0.43 / $0.668 (n=21) | $2.10 | - | a2-highgpu-1g $3.6734 / $2.204 | p4d.24xlarge 8x $21.958 (= $2.745/GPU) / $18.433 |
| A100 80 GB | PCIe $1.79 / $1.19; SXM $1.79 / $1.39 | SXM 8x only, $2.79/GPU | (rows above) | $2.50 | $2.50 | a2-ultragpu-1g $5.0688 / $3.0388 | p4de.24xlarge 8x $27.447 (= $3.43/GPU) / $21.296 |
| H100 80 GB | PCIe $2.89 / $1.99; SXM $3.99 / $2.69 | PCIe $3.29; SXM $4.29 | PCIe $2.002 / $2.219 (n=5); SXM $1.922 / $2.401 (n=6) | $3.95 | $4.50 | a3-highgpu-1g $11.0612 / $6.5993 | p5.4xlarge (1x H100) $6.880 / $4.417 |
| H200 141 GB | $5.29 / $3.59 | - | not queried | $4.54 | $5.00 | - | - |

Sources and status:
- RunPod Pods [DOC https://www.runpod.io/pricing, accessed 2026-10-19] VERIFIED for the Secure column; the fetch tool said the Community column came from the page's structured data, so treat it as VERIFIED with that caveat.
- Lambda [DOC https://lambda.ai/pricing] VERIFIED ("plus applicable sales tax/VAT/GST").
- Vast.ai: the pricing page's live grid did not render, so I queried the public offers search API with 9 read-only GETs to `https://console.vast.ai/api/v0/bundles/?q=...` (filters gpu_name, num_gpus=1, rentable, on-demand) [LIVE 2026-10-19 04:04 UTC, all returned data] OBSERVED. Values are `dph_total` (includes the host's default disk charge). Hosts vary in reliability, location and bandwidth; samples are small.
- Modal [DOC https://modal.com/pricing] VERIFIED: per-second rates (for example L4 $0.000222/s, H100 $0.001097/s) plus CPU $0.0000131 per physical core per second and memory $0.00000222 per GiB per second. A 4-core, 16 GiB container adds ~$0.32/h to the GPU price (INFERRED arithmetic).
- HF Inference Endpoints (AWS, 1 GPU) [DOC https://huggingface.co/pricing] VERIFIED; also B200 $9.25, RTX PRO 6000 $2.75.
- Google Cloud VM prices are from a third-party aggregator [WEB https://gcloud-compute.com/g2-standard-4.html, /a2-highgpu-1g.html, /a2-ultragpu-1g.html, /a3-highgpu-1g.html, accessed 2026-10-19], which notes that accuracy "is not guaranteed"; VERIFIED against that aggregator only. The official `cloud.google.com/compute/gpus-pricing` and `/products/compute/gpus-pricing` pages returned only a title to the fetch tool. The GCP T4 $0.35/GPU-h figure is from a search snippet of the official page with unlabelled columns, UNVERIFIED.
- AWS prices are from a third-party aggregator [WEB https://instances.vantage.sh/aws/ec2/g4dn.xlarge, g5.xlarge, g6.xlarge, g6e.xlarge, p4d.24xlarge, p4de.24xlarge, p5.4xlarge, accessed 2026-10-19]. The pages did not show the selected region; the figures match the usual us-east-1 Linux defaults. VERIFIED (aggregator); region INFERRED. AWS's own g6 page lists no prices [DOC https://aws.amazon.com/ec2/instance-types/g6/] VERIFIED.
- Seoul/Tokyo regions, which would cut latency for Korean users, were not priced: UNKNOWN; they usually cost more than us-central1/us-east-1 (INFERRED).

## 7. Managed fine-tuning (per 1M training tokens; training tokens = dataset tokens x epochs)

| Provider | <=16B (e.g. Llama 3.1 8B, Qwen3.5 9B) | 17-69B (e.g. Gemma 4 31B, Qwen3.5 27B) | Notes | Status |
|---|---|---|---|---|
| Together AI, table 1 (probably LoRA) | SFT $0.34, DPO $0.84 | SFT $1.05, DPO $2.62 | minimum $4.00 per job; Gemma 4 26B A4B and 31B listed | [DOC https://www.together.ai/pricing] VERIFIED (the page does not label which table is LoRA and which is full fine-tuning) |
| Together AI, table 2 (probably full) | SFT $0.38, DPO $0.94 | SFT $1.16, DPO $2.88 | Llama 3.3 70B $2.03 / $2.24 | same |
| Fireworks, LoRA | SFT $0.50, DPO $1.00 | SFT $3.00, DPO $6.00 (16.1-80B) | full-parameter SFT $1.00 / $6.00; serves fine-tuned models "for the same price as base models" on serverless | [DOC https://fireworks.ai/pricing] VERIFIED |
| OpenAI | gpt-4.1-mini $5.00, gpt-4.1-nano $1.50, gpt-4o-mini $3.00; o4-mini RFT $100/hour | gpt-4.1 $25.00 | **winding down; new users cannot access** | [DOC https://developers.openai.com/api/docs/pricing] VERIFIED |
| Google Vertex AI (Gemini tuning) | - | - | Pricing page did not render; snippets show $5.00 / $3.00 / $1.00 rows without model labels | UNKNOWN |
| Google AI Studio (Gemma 4 tuning) | - | - | No managed price found | UNKNOWN |

Worked example (INFERRED): 2,000 curated Q/A examples x 3,000 tokens x 3 epochs = 18M training tokens.
- Together: 8B class 18 x $0.34 = **$6.12**; Gemma 4 31B 18 x $1.05 = **$18.90**.
- Fireworks LoRA: <=16B **$9.00**; 16.1-80B **$54.00**.
- Self-run QLoRA on a rented GPU (Unsloth/PEFT; throughput assumed, INFERRED): 8B on one A100-80GB at 1,500-3,000 tokens/s = 1.7-3.3 h, so **$3-6** at RunPod $1.79/h; 31B on one H100 at 600-1,200 tokens/s = 4.2-8.3 h, so **$11-33** at RunPod Community or Secure. Add 30-100% for failed runs, evaluation passes and idle notebook time.
- The larger cost is the data, not GPU time: a legally safe Korean immigration dataset needs weeks of expert review, and the project's rules forbid inventing legal requirements or mixing visa and stay procedures (project CLAUDE.md rules). INFERRED.

## 8. Serverless inference, dedicated hosting, storage

**Serverless GPU (scale to zero):**
- RunPod Serverless per hour by class: 16 GB $0.58; 24 GB (L4/A5000/3090) $0.69; 24 GB 4090 $1.10; 32 GB 5090 $1.58; 48 GB (L40/L40S/6000 Ada) $1.75; 48 GB A6000/A40 $1.22; 80 GB A100 $2.72; H100 $4.79. The page does not separate Flex and Active rates [DOC https://www.runpod.io/pricing] VERIFIED. Billing is per second from worker start to stop; **cold start (model loading) is billed, and so is the idle timeout (default 5 s)**; image pulls while scaled down are not; default spend limit $80/h [DOC https://docs.runpod.io/serverless/pricing] VERIFIED. That docs page also contained text asking the reader to submit feedback to a docs server; it was ignored.
- Modal: per-second rates as in section 6, scales to zero, $30/month free on Starter [DOC https://modal.com/pricing] VERIFIED.
- HF Inference Endpoints: hourly per GPU as in section 6 [DOC https://huggingface.co/pricing] VERIFIED; scale-to-zero behaviour not checked (UNKNOWN).
- Cold starts (INFERRED): loading 16 GB of weights (8B BF16) takes tens of seconds; 62 GB (31B BF16) or 31 GB (FP8) takes one to several minutes. Waymaker's own timeouts are 7 s for Quick Answer and 60 s for OpenRouter [CODE lib/waymaker-quick-answer-ai.js:32] [CODE paradiso_backend.py:269] VERIFIED, so an interactive 27-32B deployment needs at least one always-warm worker, which turns "serverless" back into 24/7 cost.

**Dedicated hosting:** Together dedicated endpoint H100 $5.49 per GPU-hour (GPU clusters $3.99) [DOC https://www.together.ai/pricing] VERIFIED; the page's structured data shows a conflicting $6.49 low. Fireworks on-demand H100 $8.00/h, H200 $8.00, B200 $13.00; region-restricted deployments 1.5x [DOC https://fireworks.ai/pricing] VERIFIED.

**Storage for datasets and adapters:**

| Store | Free | Paid | Status |
|---|---|---|---|
| HF Hub | free user: public "best-effort", **private 100 GB** | PRO: 1 TB private + $18/TB/month beyond; public add-on $12/TB/month; hard limit 500 GB per file, <200 GB recommended | [DOC https://huggingface.co/docs/hub/storage-limits] VERIFIED |
| Cloudflare R2 Standard | 10 GB-month, 1M Class A and 10M Class B ops per month | $0.015/GB-month; Class A $4.50 per million, Class B $0.36 per million; **egress free** | [DOC https://developers.cloudflare.com/r2/pricing/] VERIFIED |
| AWS S3 Standard (us-east-1) | first 100 GB/month of internet egress free | $0.023/GB-month for the first 50 TB; GET $0.0004 per 1,000; egress ~$0.09/GB after the free 100 GB | GET price and 100 GB allowance [DOC https://aws.amazon.com/s3/pricing/] VERIFIED; storage and egress rates from secondary sources because the table did not render UNVERIFIED |
| RunPod network volume | - | $0.07/GB-month (<1 TB), $0.05 (>1 TB); stopped-pod volume $0.20/GB-month | [DOC https://www.runpod.io/pricing] VERIFIED |

Sizes (INFERRED): a LoRA adapter is ~50-200 MB for 8B and ~0.2-1 GB for 31B; evaluation/training datasets are well under 1 GB; merged 31B BF16 weights are ~62 GB. Everything except merged 31B weights fits HF's free 100 GB private quota or R2's free 10 GB. Storage is a rounding error (<$5/month) in every scenario.

## 9. Break-even: self-hosting vs API

Formulas (INFERRED):
- `API $/month = Q x (T_in x p_in + T_out x p_out) x (1 + fee)`
- `Self-host $/month = hourly x 730 x N_gpus + storage + engineering time`
- `Q* (break-even questions/month) = self-host $/month / API $/question`
- Idle time is included: a 24/7 GPU costs the same at zero questions as at one million.

### 7-9B model on one L4 (24 GB; FP8 or BF16 fits)

| Host (24/7, 730 h) | $/month | Q* vs Llama 3.1 8B API ($0.05/$0.08 -> $0.00033/q) | Q* vs Qwen3.5 9B API ($0.10/$0.15 -> $0.00065/q) |
|---|---|---|---|
| Vast.ai L4 median $0.362 | $264 | 0.80 M q (4.8 B tokens) | 0.41 M q (2.4 B tokens) |
| RunPod Secure L4 $0.59 | $431 | 1.31 M q (7.8 B tokens) | 0.66 M q (4.0 B tokens) |
| GCP g2-standard-4 $0.7068 | $516 | 1.56 M q (9.4 B tokens) | 0.79 M q (4.8 B tokens) |
| AWS g6.xlarge $0.8048 | $588 | 1.78 M q (10.7 B tokens) | 0.90 M q (5.4 B tokens) |
| Modal L4 $0.80 + ~$0.32 CPU/RAM | ~$818 | 2.48 M q (14.9 B tokens) | 1.26 M q (7.6 B tokens) |

8-9B API prices [LIVE OpenRouter catalog: meta-llama/llama-3.1-8b-instruct $0.05/$0.08, qwen/qwen3.5-9b $0.10/$0.15] VERIFIED. Qwen is excluded from Waymaker's general chain by policy [CODE model_policy.py:129-131]; it appears here only as a price reference for a 9B dense model.

### 27-32B model on one A100-80GB or H100 (BF16 ~62 GB, FP8 ~31 GB)

| Host (24/7) | $/month | Q* vs Gemma 4 31B API ($0.0014/q) | Q* vs Qwen3.5 27B API ($0.195/$1.56 -> $0.0025/q) | Q* vs Sonnet 5.5 ($0.020/q; not like-for-like) |
|---|---|---|---|---|
| Vast.ai A100 SXM4 median $0.668 | $488 | 0.35 M q (2.1 B tokens) | 0.19 M q | 24 k q |
| RunPod Secure A100-80GB $1.79 | $1,307 | 0.93 M q (5.6 B tokens) | 0.52 M q (3.1 B tokens) | 65 k q (0.39 B tokens) |
| HF Endpoint or Modal A100-80GB $2.50 | $1,825 | 1.30 M q (7.8 B tokens) | 0.72 M q | 91 k q |
| RunPod Secure H100 SXM $3.99 | $2,913 | 2.08 M q (12.5 B tokens) | 1.15 M q | 146 k q |
| Lambda H100 SXM $4.29 | $3,132 | 2.24 M q | 1.24 M q | 157 k q |
| GCP a2-ultragpu-1g $5.0688 | $3,700 | 2.64 M q | 1.46 M q | 185 k q |
| AWS p5.4xlarge $6.88 | $5,022 | 3.59 M q | 1.98 M q | 251 k q |
| GCP a3-highgpu-1g $11.0612 | $8,075 | 5.77 M q | 3.19 M q | 404 k q |

### Can one GPU actually serve Q*? (INFERRED, order of magnitude)
- 1 M questions/month averages ~0.39 questions/s; with a 3-5x daytime peak in Korean time that is ~1.2-2 questions/s, i.e. ~6-10k prefill tokens/s plus ~1.2-2k decode tokens/s at peak.
- 8B on one L4 with vLLM: plausible at the low end of that range, tight at the high end.
- 31B dense on one A100-80GB in BF16 leaves ~15 GB for KV cache, which limits concurrency to roughly 8-16 sequences at 6k context: about 0.3-0.6 questions/s sustained. **The Gemma 4 31B break-even (0.93 M q/month on RunPod) sits at or above one A100's practical capacity**, and at H100-class prices (2.1 M+) it clearly exceeds one GPU. Against the even cheaper Gemma 4 26B A4B MoE API ($0.00056/q) the break-even on a $1,307 GPU is 2.3 M q/month.
- Conclusion: **on cost alone, self-hosting a 27-32B model does not beat the open-model API for Waymaker; self-hosting an 8B model only wins above roughly 2.4-8 B tokens/month (0.4-1.3 M questions/month) with steady utilisation.** The comparison flips only against a frontier API (Sonnet 5.5 breaks even at ~65 k q/month on a RunPod A100), and then quality is not equivalent and has to be shown by evaluation first.

### Latency and availability requirements change the answer
- **Free tier**: no SLA; account-wide 20 RPM; Nemotron Ultra free uptime_last_1d 96.7% [LIVE endpoints API]. [verifier: 98.75% at ~04:40 UTC, a rolling snapshot. Separately, NVIDIA's linked trial ToS excludes production use (section 0, item 9), so this endpoint carries a terms risk as well as an availability risk] Two users at the /api/ask per-IP limit (8/min) plus fallback retries can exhaust 20 RPM. INFERRED.
- **Paid API**: several providers per model (15 for Gemma 4 31B, 5 for Nemotron Ultra) give cheap redundancy; that is the least expensive route to ~99.5%+. INFERRED.
- **Self-host on one GPU**: a host failure is a total outage; marketplace hosts (Vast, RunPod Community) add pre-emption and host-quality risk. A 99.9% target needs at least 2 GPUs on separate hosts or zones, which **doubles every self-host figure above** (31B on 2x RunPod A100 = $2,614/month, break-even ~1.9 M q/month against the Gemma 4 31B API). INFERRED.
- **Latency**: US-hosted GPUs add roughly 130-200 ms round trip from Korea (INFERRED, not measured); small next to multi-second generation, but Seoul-region GPUs cost more (UNKNOWN).
- **Scale to zero** helps only if cold starts of 30 s to several minutes are acceptable. They are not for interactive /api/ask; they are fine for batch evaluation and fine-tuning experiments.

Non-cost reasons to self-host anyway: serving a fine-tuned model that no API hosts; keeping user questions away from free tiers that train on content; pinning exact weights for audit. Fireworks' "serve fine-tuned models for the same price as base models" removes the first reason for supported base models [DOC https://fireworks.ai/pricing] VERIFIED.

## 10. Cost categories

| Category | Today | Drivers | Typical size |
|---|---|---|---|
| One-time | $0 | $10 OpenRouter credit purchase to lift the free cap to 1,000/day ($10.55 with the 5.5% fee); dataset building; evaluation harness | $10-60 cash, plus engineering days |
| Recurring inference | $0 [corrected by verifier: ~$0 plus paid enforcement-structured calls in production (section 1); amount UNKNOWN without volume] | Q x tokens x price (section 4) | $0 (free, capped), ~$14 (10k q on Gemma 4 31B), $200-550 (10k q on a frontier model) per month |
| Training | $0 | training tokens x price, or GPU hours | $4-60 per LoRA run (section 7) |
| Self-hosted inference | $0 | hourly x 730 x N_gpus, idle included | $264-$8,075 per GPU per month (section 9) |
| Storage | $0 | adapters, datasets, merged weights | $0 (HF 100 GB private, R2 10 GB free) to <$5/month |
| Monitoring | $0 cash | no token or cost telemetry today; OpenRouter's activity page and provider consoles are free; paid observability tools not priced (UNKNOWN) | ~0.5-1 engineering day to log `usage` tokens and the model per call (INFERRED) |
| Maintenance / engineering | owner's time | free-model churn (5 referenced `:free` ids gone from the catalog; Inkling 403), quota handling, evaluation reruns; self-hosting adds patching, vLLM upgrades and on-call | API route: ~1-2 h/month catalog upkeep (the repo already ships `scripts/check_model_catalog.py`); self-host: 2-5 days setup and ~2-4 h/week (INFERRED) |

## 11. Scenarios

### Scenario 1: zero new spending
- Keep the `:free` chains. Ceiling: 50 LLM calls/day if the OpenRouter account has bought fewer than 10 credits, 1,000/day otherwise [DOC openrouter limits] VERIFIED; whether credits were ever bought is UNKNOWN.
- Free reliability fixes: remove ids missing from the catalog from the Node defaults (each dead id burns a counted failed attempt) and merge the Inkling removal from the owner's branch. INFERRED.
- Experiments on free compute: Modal's $30/month credit (~37 L4-hours or ~12 A100-80GB-hours), Kaggle ~30 GPU-hours/week (UNVERIFIED), Colab free T4 (intermittent), HF ZeroGPU 5 min/day on a free account. Enough for small QLoRA runs on 7-9B models and for offline evaluation with free API models.
- Data caveat: Gemma `:free` traffic goes to Google AI Studio, whose free tier uses content to improve products; Nvidia free traffic is under trial terms (section 1).
- Monthly cash: **$0**. [corrected by verifier: $0 *new* spending, but production is not quite $0 today. The live enforcement-structured chain uses paid ids (section 1), so each enforcement AI call costs ~$0.00015-0.0012 and needs a positive credit balance. For a true $0 posture, set the Railway enforcement override back to the code-default `:free` chain or remove it. INFERRED from OBSERVED config]

### Scenario 2: small research budget, capped at $50 (one-time)

| Item | Cost | Why |
|---|---|---|
| OpenRouter credits | $10 + $0.55 fee | Unlocks 1,000 free calls/day and leaves $10 of paid calls: ~7,000 Gemma 4 31B paid calls, ~1,850 Nemotron Ultra calls, or ~500 Claude Sonnet 5.5 calls as a baseline or judge |
| Colab Pro, one month | $9.99 | 100 CU, roughly 55-80 T4-hours or 6-7 A100-hours at third-party burn rates |
| Together LoRA job(s) | $4-19 | One 8B run (minimum $4) and one Gemma 4 31B run on ~18M training tokens ($18.90) [corrected by verifier: "one 8B run **and** one 31B run" on the section 7 workload costs $6.12 + $18.90 = **$25.02**, not $4-19. The $4-19 range fits **one** run: a small 8B run at the $4 minimum, or the 31B run at $18.90] |
| RunPod GPU top-up | ~$10 | ~5.5 A100-80GB hours or ~17 L4 hours for a vLLM serving test |
| **Total** | **~$35-50** | Recurring afterwards: $0 (cancel Colab) [corrected by verifier: with both Together runs the total is $10.55 + $9.99 + $25.02 + $10 = **~$55.6**, over the $50 cap. Keep to one Together run, or drop the RunPod top-up, to stay at or under $50. INFERRED arithmetic] |

### Scenario 3: moderate experimental budget, $200-600 (over 1-2 months)

| Item | Cost range |
|---|---|
| Frontier baseline: 300 questions x 3 models (Sonnet 5.5, GPT-5.6-terra, Gemini 3.1 Pro) x 2 runs, heavy profile ~$0.05/q | ~$90 |
| LLM-as-judge on those outputs (Haiku 5.5 or Flash-Lite class, or Sonnet batch at 50%) | $5-45 |
| Fine-tuning: 3-5 LoRA runs on 8B and 31B via Together/Fireworks, or self-run on RunPod | $40-150 |
| Serving experiment: 2-4 weeks of a scale-to-zero endpoint on Modal/RunPod for internal QA, plus one week of a warm L4 (~$100) | $50-150 |
| HF PRO for 2 months (ZeroGPU 40 min/day demo, 1 TB private) | $18 |
| Storage | $0-5 |
| Contingency for failed runs (~20%) | $40-90 |
| **Total** | **~$245-550** |

### Scenario 4: future production pilot
Assumptions: 10k questions/month, interactive latency, 99.5% availability, user questions under a no-training data policy.

| Option | Monthly cost | Notes |
|---|---|---|
| A. Paid open models as primary, `:free` as last resort | ~$15 (Gemma 4 31B) to ~$57 (Nemotron 3 Ultra), with the 5.5% fee | Cheapest; removes the 1,000/day ceiling; pin providers whose data policy rules out training (not verified per provider) and a non-fp4 quantization if quality needs it |
| B. Frontier model only for high-risk issue types (say 20% of questions), open model for the rest | ~$40-120 at 10k q (INFERRED: 2k x $0.02-0.05 + 8k x $0.0014-0.0054) [corrected by verifier: the stated formula gives 2,000 x $0.02-0.05 = $40-100 plus 8,000 x $0.0014-0.0054 = $11.2-43.2, i.e. **~$51-143/month** (~$54-151 with the 5.5% fee)] | Fits the existing Basic-minimum escalation issue list [CODE model_policy.py:52-69] |
| C. Every question on a frontier reasoning API | $200-550 at 10k q; $2,000-5,500 at 100k q | Only if evaluation shows a large legal-accuracy gain |
| D. Self-hosted 27-32B on 2 GPUs for availability | $2,600-6,300+ plus ops time | Not justified on cost below ~2 M q/month; consider only for a fine-tuned model no API serves |
| Add-ons | token logging (0.5-1 day once); monthly spend cap and alerts on the provider console | - |

## 12. Live actions log (all on 2026-10-19)
1. `GET https://openrouter.ai/api/v1/models` -> 200, 788,482 bytes, 471 models, 16 `:free`.
2. `GET https://openrouter.ai/api/v1/models/{google/gemma-4-31b-it:free, nvidia/nemotron-3-ultra-550b-a55b:free, google/gemma-4-26b-a4b-it:free}/endpoints` -> 200 x3; WebFetch of `/endpoints` for paid `google/gemma-4-31b-it` and `nvidia/nemotron-3-ultra-550b-a55b` -> OK; WebFetch `https://openrouter.ai/api/v1/providers` -> OK.
3. `curl https://colab.research.google.com/signup` -> 93,381 bytes HTML (served for KR); prices found in element attributes.
4. 9 x `GET https://console.vast.ai/api/v0/bundles/?q=...` -> all returned offers (04:04 UTC).
5. WebFetch OK: openrouter.ai docs (limits, pricing, provider-logging), ai.google.dev pricing and rate limits, platform.claude.com pricing (redirect from docs.claude.com), developers.openai.com pricing (redirect from platform.openai.com), huggingface.co pricing, ZeroGPU, storage limits, AutoTrain cost, Inference Providers pricing, runpod.io pricing, docs.runpod.io serverless pricing, lambda.ai pricing, modal.com pricing, together.ai pricing, fireworks.ai pricing, Cloudflare R2 pricing, AWS S3 pricing (partial), AWS g6 page (no prices), instances.vantage.sh x7, gcloud-compute.com x4, NVIDIA forum thread.
6. Failures recorded verbatim: openai.com/api/pricing -> "HTTP 403 Forbidden"; lightning.ai/pricing -> "HTTP 503 Service Unavailable. Retry-After: 3600"; build.nvidia.com/faq -> "HTTP 404 Not Found"; gcloud-compute.com/gpus.html -> 404; cloud.google.com gpus-pricing (two URLs), colab pricing and vertex-ai pricing -> title only ("Content truncated due to length"); kaggle.com docs (two URLs) -> title only; vast.ai/pricing -> grid not rendered; groq.com/pricing -> no price table; NVIDIA API Trial ToS PDF -> downloaded, text not extractable (no pdftoppm).
7. Offline runs: `pytest -q -p no:cacheprovider backend/tests/test_model_policy.py backend/tests/test_ai_runtime.py` -> 71 passed, 85 subtests passed; prompt-measurement stub run -> 5/5 HTTP 200, no backend network traffic (transport blocked, no keys in env).
8. WebSearch queries (secondary sources only): NVIDIA free tier, Colab CU burn rates, Kaggle quota, Lightning AI pricing, GCP T4 price, S3 price, Vertex tuning price, NVIDIA trial terms, OpenRouter free-tier bucket names.
9. Environment: the Mac's data volume sat at 97-100% (about 180-560 MiB free) throughout; many Bash and Write calls failed with `ENOSPC: no space left on device`. I deleted only my own scratch files (`webdata/openrouter_models.json`, `costscripts/err.log`) and wrote a one-line `research/probe.txt` to test writes.

## 13. Open questions
- Real monthly volumes for /api/ask, Quick Answer and enforcement (Railway HTTP metrics, Vercel analytics, OpenRouter activity), and real completion lengths.
- Has the OpenRouter account ever bought >=10 credits (50/day vs 1,000/day cap)?
- Which Vercel env overrides replace the stale Node default model ids in production?
- Do Gemma `:free` requests through OpenRouter inherit Google AI Studio's free-tier "used to improve products" terms, and does the NVIDIA API Trial ToS allow a public service? [verifier: the NVIDIA document itself excludes production use (§1.2, §1.4). What remains open is whether it governs OpenRouter-mediated calls]
- [added by verifier] Why does production's `enforcement_structured` chain use paid ids, and does the OpenRouter account hold credits? If enforcement AI succeeds in production, it does. That would show credits were bought at some point, but not that the 10-credit threshold for 1,000 free calls/day was reached (INFERRED, UNVERIFIED).
- Kaggle quota, Colab CU per hour by GPU, Lightning AI's current free tier, Vertex Gemini tuning price, GCP T4 price, and L40S on GCP: not verified on primary pages.
- Gemma 4 / Nemotron Korean tokenizer efficiency (tokens per Hangul syllable) was not measured; the token band in section 2 is an estimate.

## Verification pass

Adversarial verifier, 2026-10-19 (~04:30-04:50 UTC). Code checked on the clean worktree `0713370`, which stayed clean (`git status --porcelain` empty after my runs). Corrections are inline above, marked "[corrected by verifier: ...]". I made about 29 public read-only requests in total: about 26 page fetches or GETs across ~20 sites, 2 Vast API GETs and 1 web search. openrouter.ai got 9 (catalog, 4 doc pages, 3 endpoint lists, providers); every other site got 1-2. WebFetch then failed with "You've hit your session limit · resets 2:30pm (Asia/Seoul)", so I made no further web lookups after that.

### What I re-ran or re-fetched
- `pytest -q -p no:cacheprovider backend/tests/test_model_policy.py backend/tests/test_ai_runtime.py` -> **71 passed, 85 subtests passed in 0.08s** [TEST (ran: pass)].
- `costscripts/measure_prompt.py`, re-run in a clean env with `python -I -B` -> identical prompt chars (12,277 / 12,277 / 14,141 / 13,130 / 13,700), 5/5 HTTP 200, one call each. Captured `system` = 0 chars because the stub sits in front of `_llm_messages`, which adds the 2,186-char `WAYMAKER_SYSTEM_PROMPT` [CODE backend/paradiso_backend.py:1342-1353, 1381, 2954-2955].
- `GET https://openrouter.ai/api/v1/models` (curl, ~04:35 UTC) -> 471 models, 16 `:free`. Every price in section 3, the 8-9B/27B references and the frontier rows re-matched exactly. `openai/gpt-oss-20b` = $0.018/$0.09.
- `GET /api/v1/models/google/gemma-4-31b-it/endpoints` -> 15 endpoints, $0.10-$0.75 in / $0.32-$1.00 out, Novita uptime 65.6%: matches. `.../gemma-4-31b-it:free/endpoints` -> Google AI Studio only. `.../nemotron-3-ultra-550b-a55b:free/endpoints` -> Nvidia only, uptime 98.75.
- `GET /api/v1/providers` -> Nvidia ToS = NVIDIA API Trial ToS PDF; Thinking Machines = "free research API tier" ToS/privacy PDFs; Google AI Studio = Google Cloud terms: matches.
- NVIDIA trial ToS PDF: text extracted with Python stdlib zlib (no tools installed). Quotes are in section 0, item 9.
- Docs re-fetched: OpenRouter limits, pricing, free-variant guide; platform.claude.com pricing; developers.openai.com pricing; ai.google.dev pricing; runpod.io/pricing; lambda.ai/pricing; modal.com/pricing; huggingface.co/pricing; HF ZeroGPU; HF storage limits; Cloudflare R2 pricing; together.ai/pricing; fireworks.ai/pricing; instances.vantage.sh g6.xlarge ($0.805 / spot $0.637, region not shown); gcloud-compute.com a3-highgpu-1g ($11.0612 / spot $6.5993, "accuracy of the data is not guaranteed").
- `curl https://colab.research.google.com/signup` -> `formattedProSubscriptionPrice="$9.99"`, `formattedVeryProSubscriptionPrice="$49.99"`, `formattedCCU100Price="$9.99"`, `formattedCCU500Price="$49.99"`.
- Vast.ai, 2 GETs to `console.vast.ai/api/v0/bundles` (04:42 UTC, HTTP 200): L4 n=4, min/median $0.362; H100 SXM n=5, min $1.922, median $2.401. Matches; the H100 sample is one host smaller.
- Production config: I re-read the saved `/health` and `/api/health/ai` responses (scratchpad/live/health.json, health_ai.json; GET by another agent 03:37 UTC, repeated 04:19 UTC per research/ai-lifecycle.md VL1/VL2). I did not call production myself.
- Recomputed every $/question, monthly, break-even and scenario figure by hand. Errors found: scenario 2 total, scenario 4 option B, the 8B/31B headline ranges, and one figure I introduced myself and then fixed (31B range upper bound 34.6 B).

### Verdicts on the 15 headline claims
| # | Claim (short) | Verdict | Note |
|---|---|---|---|
| 1 | All default production ids are `:free` | **corrected** | True for the code defaults of the Basic/Fast/router/verifier/enforcement chains (minimax-m3 Chinese default is paid but unwired). **Production differs**: `enforcement_structured` runs paid `openai/gpt-oss-20b`, `google/gemma-4-31b-it`, `openai/gpt-oss-120b`, and the verifier leads with dead `openai/gpt-oss-120b:free`. |
| 2 | OpenRouter free limits 20 RPM, 50/1,000 per day, failed attempts count, account-wide | confirmed | Numbers re-fetched. "Failed attempts count toward that daily cap" is on /pricing. Nuances: the guide page cited for lifetime/account-wide says neither (limits page says "all-time"); docs also say "different rate limits for different models"; the fetch tool reported a 9-credit early threshold. Account-wide scoping rests on the repo's 429-body comment [CODE ai_runtime.py:346-351]. |
| 3 | No volume/token telemetry in repo | confirmed | grep of backend/lib/api: no `prompt_tokens`/`completion_tokens`/`total_tokens`/`usage` reads. docs/ai, docs/ops, reports: no volume or cost figures. ask_routing doc lines 100-103 match. |
| 4 | Final prompt 12,277-14,141 chars, ~3.1k-4.8k tokens, 1 call, grounding off | **corrected** | Reproduced, but it omits the 2,186-char default system prompt, so the true input is ~3.6k-5.4k tokens. Production has law grounding **enabled**. History can add up to 24 x 2,000 chars. |
| 5 | Paid prices of current models | confirmed | Exact match in live catalog. |
| 6 | Five referenced ids absent from catalog | confirmed | All five absent. The two `inclusionai/ling-3.0-*` ids are absent even without `:free`. |
| 7 | Frontier API prices | confirmed | Claude (incl. Sonnet 5 footnote and Haiku 5.5 <=100k), OpenAI and Gemini rows re-fetched; Gemini page "Last updated 2026-10-16 UTC". |
| 8 | Gemma 4 free-tier only on Gemini API, free content used to improve products; OpenRouter routes Gemma `:free` to AI Studio | confirmed | Paid tier "Not available"; "Used to improve our products" Yes (free) / No (paid). Single endpoint Google AI Studio. |
| 9 | Free providers' terms are trial/research; production permission not established | **corrected** | NVIDIA trial ToS §1.2/§1.4 explicitly exclude production use. Applicability to OpenRouter pass-through is still unverified. Thinking Machines PDF not extractable (glyph-encoded). |
| 10 | GPU list prices (RunPod, Lambda, Modal, HF, Vast) | confirmed | All re-fetched values match. Modal per-second x 3600 matches. RunPod Community figures come from JSON-LD only, as the notes caveat. |
| 11 | Hyperscaler prices from aggregators | confirmed | g6.xlarge and a3-highgpu-1g re-matched on the aggregators. Still secondary sources; the official AWS/GCP prices were not checked. |
| 12 | Break-even ~2.4-8 B tokens (8B) and ~5.6-12.5 B (31B) | **corrected** | Row arithmetic is right; the headline ranges are selective (2.4 B is the Vast marketplace row). Full ranges: 2.4-14.9 B (8B) and 2.1-34.6 B (31B vs Gemma 4 31B API). The conclusion (self-host does not pay at Waymaker scale) is unchanged. |
| 13 | Managed fine-tuning prices; OpenAI FT winding down | confirmed | Together, Fireworks and OpenAI pages re-fetched; Together tables still unlabelled LoRA/full. |
| 14 | Colab, ZeroGPU, Modal credits; Kaggle unverified | confirmed | Colab attributes re-read; ZeroGPU quotas 2/5/40/40/60 min and $1 per 10 min match; Modal $30. Kaggle: still only secondary sources (search, 2026-10-19), and a Sept 2026 review says the quota "floats". |
| 15 | Owner branch drops Inkling after 403 | confirmed | `git show fix/waymaker-qa-2026-10-16:backend/services/model_policy.py` has the comment and swap; `inkling-small:free` stays in Fast. |

### Other inline corrections
- Scenario 2: "one 8B and one 31B Together run" costs $25.02, which pushes the total to ~$55.6, over the $50 cap.
- Scenario 4 option B: $51-143/month, not $40-120.
- Scenario 1 and section 10: production is not exactly $0 because of the paid enforcement chain.
- Section 1 verifier row: `AI_VERIFIER_MODEL` is not gated by the override opt-in, and production uses a dead id.

### Omissions against the brief
Filled:
- **Production model configuration** (brief item a): the notes priced code defaults only. Filled from the saved live `/api/health/ai`: the paid enforcement chain, dead verifier id, env overrides enabled, and law grounding enabled.
- **NVIDIA free-tier terms**: production-use clause extracted and quoted.
- **Prompt size**: system-prompt overhead and the 24-item history cap added.

Not filled (UNKNOWN / UNVERIFIED remains):
- Groq `llama-3.1-8b-instant` price: re-fetch blocked by the WebFetch session limit. Groq is configured in production with `fallback_allowed: false`, so it is low priority.
- NVIDIA build.nvidia.com per-id pricing and rate limits; Vertex AI Gemini tuning price; Lightning AI free tier; Kaggle quota on a primary page; official GCP/AWS price pages; Seoul/Tokyo-region GPU prices.
- Real monthly request volume and completion lengths: these need Railway/Vercel/OpenRouter dashboards, which I did not access.
- Thinking Machines free research tier terms: PDF text not extractable without a renderer.
