# Open-weight model landscape and licence matrix for Waymaker (as of 2026-10-19)

Mission 001 "Waymaker Genesis". Scope: candidate open-weight base models for three Waymaker roles.

- **Artemis**: compact model for status/subcode extraction, procedure classification, entity/date extraction, structured routing and multilingual intent. It must be cheap to fine-tune and serve.
- **Athena**: advanced reasoning over supplied evidence (`evidence_pack`).
- **Hestia**: professional assistant on a shared base with LoRA adapters.

Audited repo: `/Users/seonjaekim/dev/Visable-genesis` at origin/main `0713370`, read-only. All Hugging Face (HF) data was pulled live on 2026-10-19 from the public API (`/api/models/<id>`), with no token. Every revision SHA below is the repo HEAD at query time. **Pin these SHAs.** Several repos changed in the last 30 days.

Evidence tags: [CODE path:line], [TEST path (ran: …)], [DOC path-or-URL], [LIVE …], [WEB url, accessed 2026-10-19]. Status: VERIFIED / OBSERVED / README-ONLY / INFERRED / UNVERIFIED.

Benchmark labels: **VENDOR-REPORTED** means the number is from a model card or report by the model's maker, or by a competitor comparing itself against that model. **INDEPENDENT** means a third party with no model in the comparison ran the evaluation.

---

## 0. TL;DR

1. **The landscape moved a lot after mid-2026.** As of today HF hosts Qwen3.5 (Feb), Qwen3.6 (Apr) and Qwen3.8 (Aug). It also hosts the Gemma 4 family (E2B, E4B, 12B, 26B-A4B and 31B; 12B added 2026-05-23), DeepSeek V4/V4.1 and Kimi K3. Other new releases: GLM-5.3, MiniMax M3, Mistral Small 4 (119B MoE) and Granite 4.2 (dense 3B/8B/30B). NVIDIA has Nemotron 3.5 (Lightning 30B-A3B, Super-VL 120B-A12B, Bolt 74B-A9B). Meta has **Muse Spark Open 816B-A42B** (2026-10-15); no Llama 5 exists on `meta-llama`. The Korean sovereign-programme models are K-EXAONE 2.0 750B-A37B, A.X K2 688B-A33B, Solar Open 2 250B-A15B and Motif-3. [LIVE HF API listings, 2026-10-19] VERIFIED.
2. **Gemma 4 is Apache-2.0 and no longer gated.** HF API shows `license: apache-2.0`, `gated: False` for `google/gemma-4-E4B-it` and `google/gemma-4-12B-it`. Google's licence page shows Apache 2.0 text [WEB https://ai.google.dev/gemma/docs/gemma_4_license]. The repo's experiment README and notebook still treat both as gated and requiring a token and licence click [DOC experiments/waymaker-gemma4-finetune/README.md:41-42,171-173; notebook cell 4 `MODEL_PRESETS` marks them `True`, cell 8 raises if no `HF_TOKEN`]. That is stale: the token guard is now an unnecessary failure mode. VERIFIED.
3. **The repo's own policy blocks the technically strongest compact and mid models.** `CHINESE_ONLY_MODEL_PREFIXES = ("deepseek/", "qwen/", "moonshotai/", "z-ai/", "minimax/", "inclusionai/")` restricts those families to Chinese-language routes [CODE backend/services/model_policy.py:126-131,216-221]. The test suite enforces it [TEST backend/tests/test_model_policy.py (ran: 16 passed)]. Qwen3.5/3.6/3.8, DeepSeek V4.x, GLM-5.3, Kimi K3 and MiniMax M3 are therefore **policy-disqualified** for Korean/English Waymaker roles unless the owner changes the policy. Policy question: whether Korean models built on Qwen (A.X 4.0 Light declares "Built with Qwen 2.5") also fall under it. INFERRED. [corrected by verifier: enforcement is advisory, not a runtime filter. The prefixes are only checked by `_validate_model_candidates`, which emits a `/health` warning `MODEL_CANDIDATES_CHINESE_MODEL_RESTRICTED_TO_CHINESE` [CODE backend/paradiso_backend.py:329-343,4846,5072], and the tests only assert the *default* chains contain none of them [TEST backend/tests/test_model_policy.py:54-61,112-113 (ran: 16 passed)]. The match is a lower-cased prefix on OpenRouter-style ids: run against HF repo ids it flags `Qwen/…` and `moonshotai/…` but not `deepseek-ai/…`, `zai-org/…` or `MiniMaxAI/…` [LIVE `model_family_is_chinese_only()` called in .venv-check, 2026-10-19] OBSERVED. `DEFAULT_CHINESE_MODEL` / `chinese_fallback_models` are declared in model_policy.py:120-124,213-214 but no other backend module reads them (grep) VERIFIED. The repo's own fine-tune notebook defaults to `Qwen/Qwen3-1.7B` for smoke tests. So "policy-disqualified" is the owner's stated intent for hosted routes; whether it covers self-hosted open weights is an open owner decision (see Rec. 2), not something the code settles.]
4. **Licence traps that matter for a Korean immigration-information service:**
   - Non-commercial: EXAONE 4.0/4.0.1/4.5 (EXAONE AI Model License 1.2-NC) and MiniMax M2.7.
   - Revenue cap: Mistral Medium 3.5 grants no rights above US$20M monthly company revenue.
   - "Unlicensed practice of law" acceptable-use clauses: HyperCLOVA X SEED (AUP 1.d), Muse Spark Open (Usage Policy 1.4) and Llama 3.1 (AUP by reference). Waymaker must stay demonstrably "information, not legal advice". [corrected by verifier: only the HyperCLOVA X SEED and Muse clauses were read in licence text (both re-read at the pinned SHAs). The Llama 3.1 AUP was **not** read: the LICENSE only links to it, and the redirect chain llama.com → developer.meta.com → dev.meta.ai ended in HTTP 404 again on 2026-10-19. Llama 3.1's clause is UNVERIFIED, not VERIFIED. Google's Gemma Prohibited Use Policy (last modified 2024-02-21) also has an unlicensed-practice clause (§2.2, §3.6) [WEB https://ai.google.dev/gemma/prohibited_use_policy]. Whether it binds Apache-2.0 Gemma 4 is unclear (see §8).]
   - Competitor clause: HyperCLOVA X SEED §4.
   - Mandatory "Built with / Powered by" UI attribution: Kanana, HyperCLOVA X, Llama, Muse, MiniMax M3, Solar (derivatives only).
   - Derivative-name prefixes: Kanana, HyperCLOVA X, Llama, Solar, K-EXAONE, EXAONE.
   - Third-party "making available" clause: K-EXAONE-236B §2.2 needs a separate agreement. VERIFIED (licence texts read at pinned SHAs).
5. **Korean evidence is thin and mostly vendor-reported.** The only independent Korean *legal* benchmark with open-model numbers is LBox's KCL (EACL 2026). It covers 2025-generation models only. Supplying precedents roughly doubles MCQA accuracy (e.g. A.X 4.0 49.1→71.3; EXAONE 4.0 32B 36.4→72.3). [corrected by verifier: the numbers match the arXiv tables, but "roughly doubles" overstates. Gains are ×1.39 (Phi-4-mini, 22.0→30.6) to ×2.2 (gpt-oss-120b, 29.2→64.1), and A.X 4.0 is ×1.45. Say "raises MCQA by 9-36 points".] That supports Waymaker's evidence-pack design but says nothing about Gemma 4, Qwen3.6+ or the sovereign 2026 models [WEB https://arxiv.org/html/2512.24572v2]. INDEPENDENT. The Horangi v4 leaderboard could not be read (JS-rendered).
6. **Shortlists** (detail in §5):
   - **Artemis:** Gemma 4 E4B-it, then Kanana-2-3B-instruct, Granite 4.2 3B/8B, Mi:dm 2.0 Mini. Qwen3.5-4B/9B is the best technical fallback but policy-blocked.
   - **Athena:** Solar Open 2 250B-A15B, A.X K2, K-EXAONE 2.0, gpt-oss-120b and Nemotron 3 Ultra / 3.5 Super-VL. Gemma 4 31B serves as "Athena-lite".
   - **Hestia:** Gemma 4 31B-it / 12B-it shared base, then Kanana-2-30B-A3B, Mi:dm 2.0 Base, gpt-oss-20b.

---

## 1. Repository context that constrains model choice

| Fact | Evidence | Status |
|---|---|---|
| Current routing (OpenRouter, hosted): router/translation `google/gemma-4-31b-it:free`; Basic final-answer chain `nvidia/nemotron-3-ultra-550b-a55b:free` → `google/gemma-4-31b-it:free` → `nvidia/nemotron-3-super-120b-a12b:free` → `thinkingmachines/inkling:free`; Fast tier `google/gemma-4-26b-a4b-it:free` first; verifier `nvidia/nemotron-3-super-120b-a12b:free`; Chinese route `minimax/minimax-m3` | [CODE backend/services/model_policy.py:23-24,31-37,99-105,112-118,120-124] | VERIFIED [corrected by verifier: the Chinese route is declared in the policy dict only; no backend module outside model_policy.py and its test reads `chinese_model`. Live OpenRouter catalog (2026-10-19): the `:free` endpoints `gemma-4-31b-it`, `gemma-4-26b-a4b-it`, `nemotron-3-ultra-550b-a55b` and `nemotron-3.5-lightning` do **not** list `structured_outputs`; the Gemma ones list `response_format` only. Of the production free endpoints, only `nemotron-3-super-120b-a12b:free` lists it. That contradicts the comment at model_policy.py:110-111 that both enforcement models are free endpoints with structured-output support. OBSERVED] |
| China-origin families excluded from default chains; tested | [CODE backend/services/model_policy.py:126-131]; [TEST backend/tests/test_model_policy.py:54-59,112-113 (ran: 16 passed)] | VERIFIED |
| A stale comment says "verifier: gpt-oss", but the code's verifier is Nemotron 3 Super | [CODE backend/paradiso_backend.py:163-166] vs [CODE backend/services/model_policy.py:118] | VERIFIED |
| Optional Ollama fallback defaults to `qwen3:8b`, which is inconsistent with the Chinese-only policy if enabled | [CODE backend/paradiso_backend.py:257-259] | VERIFIED (default off) |
| Answer guard flags provider/model names in generated text (`gemma`, `qwen`, `llama\d`, `mistral` and others). "Built with X" licence attributions must go in UI chrome/about page/docs, not in model answers. The regex does not cover `exaone`, `kanana`, `solar`, `hyperclova`, `a.x`, `midm`, `granite`, `phi`, `muse` | [CODE backend/services/knowledge/guard.py:37-40] | VERIFIED (gap: INFERRED relevance) [corrected by verifier: it also misses `minimax`, `glm`/`zhipu`/`z.ai`, and bare "Llama" (the pattern needs a digit, `llama[\s-]?\d`). So "Built with Llama", "Built with MiniMax M3", "Powered by Kanana" and "Built with Solar" would all pass the guard, while "Gemma" or "Mistral" would be flagged CRITICAL `provider_model_leak` (guard.py:162-163). Putting attributions in UI chrome is still the right call, but because licences ask for it there, not because the guard would always catch them. The owner branch does not change guard.py.] |
| Fine-tune experiment targets `google/gemma-4-E4B-it` (smoke) and `google/gemma-4-12B-it` (quality run). Default smoke model is `Qwen/Qwen3-1.7B`. QLoRA NF4, r=8, alpha 16, all attention+MLP projections, AutoModelForCausalLM | [DOC experiments/waymaker-gemma4-finetune/README.md:36-42]; notebook cells 4 and 8 | VERIFIED |
| Owner branch `fix/waymaker-qa-2026-10-16` replaces `thinkingmachines/inkling:free` (403 `model_access_denied`) with `google/gemma-4-26b-a4b-it:free` in the final chain. It does not change any conclusion here; it increases reliance on Gemma 4 | `git show` diff of model_policy.py | VERIFIED |

Implication (INFERRED): the policy-compatible open-weight families already in production are **Gemma 4, NVIDIA Nemotron 3/3.5 and OpenAI gpt-oss**. Choosing Artemis/Hestia from these families gives the shortest path. The Korean sovereign models are the policy-neutral alternative with the strongest Korean claims.

---

## 2. Landscape by family (what exists today)

All rows: [LIVE HF API `/api/models?author=<org>&sort=createdAt`, 2026-10-19], VERIFIED unless noted.

| Family | Latest open-weight text/VLM releases (HF createdAt) | Notes |
|---|---|---|
| Qwen (Alibaba) | Qwen3.5 0.8B/2B/4B/9B/27B/35B-A3B/122B-A10B/397B-A17B (2026-02); Qwen3.6-27B, 35B-A3B (2026-04); Qwen3.8-27B (2026-08-05), Qwen3.8-Flash-Next 125B-A6B+51B n-gram emb (2026-08-24), Qwen3.8-2.4T-A95B (2026-08-08) | ≤27B and Qwen3.6 are Apache-2.0. Flash-Next is under the new "Qwen Community License 1.0". 2.4T is under the "Qwen3.8-Max License". All are VLMs (`…ForConditionalGeneration`) except 2.4T |
| Gemma (Google) | gemma-4 E2B/E4B (createdAt 2026-03-02; public launch reported 2026-04-02), 26B-A4B and 31B (2026-03-11), 12B "Unified" (2026-05-23); QAT q4_0 GGUF and w4a16 variants (Apr–Jun) | Apache-2.0, not gated. diffusiongemma-26B-A4B is also out |
| Llama / Meta | Nothing new on `meta-llama` since Llama 4 (2025-04). Meta now publishes `meta-models/Muse-Spark-Open-816B-A42B` (2026-09-15, announced 2026-10-15) | Muse Model License; gated (manual). [WEB https://thenewstack.io/meta-muse-spark-open/] |
| Mistral | Ministral 3 3B/8B/14B (2512), Mistral Large 3 675B (2512), Mistral Small 4 119B MoE (2603), Mistral Medium 3.5 128B (2026-03-31) | Medium 3.5 is under a "Modified MIT" with a revenue cap; the others are Apache-2.0 |
| DeepSeek | V4-Flash 291B and V4-Pro 1.6T (2026-04-22); V4.1-Flash 763B (2026-09-10), V4.1-Flash-1017 (2026-10-17) | MIT. Policy-blocked |
| OpenAI | gpt-oss-20b/120b (2025-08), gpt-oss-safeguard (2025-09); no newer open LLM | Apache-2.0 |
| Microsoft Phi | Last LLMs: Phi-4-reasoning-vision-15B (2026-01). `FrogNano-4B-2609` is a Qwen3.5-4B coding-agent fine-tune, not Phi [WEB https://huggingface.co/microsoft/FrogNano-4B-2609] | Phi line looks dormant (INFERRED) |
| IBM Granite | granite-4.2 3B/8B/30B dense (2026-08-07) with official GGUF/MLX/FP8/NVFP4; granite-switch-4.1 (2026-10-14) | Apache-2.0; Korean listed |
| GLM (Z.ai) | GLM-4.7-Flash (2026-01), GLM-5 (02), 5.1 (04), 5.2 (06), GLM-5.3 and 5.3-Flash (2026-08-25) | 5.3-Flash MIT; 5.3 custom. Policy-blocked |
| Kimi (Moonshot) | Kimi-K2.5 (2026-01), K2.6 (04), K3 2.78T (2026-06-13) | Custom MIT variants. Policy-blocked |
| MiniMax | M2.5 (02), M2.7 (04, non-commercial), M3 427B VLM (2026-06-02, community licence) | Policy-blocked (M3 is the repo's Chinese-route model via API) |
| NVIDIA Nemotron | Nemotron 3 Nano/Super/Ultra (Dec 2025–Jun 2026); 3.5 Lightning 30B-A3B (08), Super-VL 120B-A12B and Bolt 74B-A9B (10) | OpenMDW-1.1 (3 Ultra, 3.5) or NVIDIA Nemotron Open Model License (3 Super/Nano) |
| LG EXAONE | EXAONE 4.0/4.0.1 (2025-07), K-EXAONE-236B-A23B (2025-12-26), EXAONE 4.5-33B VLM (2026-04-04), **K-EXAONE 2.0 750B-A37B (2026-07-29)** | 4.x non-commercial; K-EXAONE custom; **K-EXAONE 2.0 Apache-2.0** |
| Naver HyperCLOVA X SEED | Text-Instruct 0.5B/1.5B, Vision 3B (2025-04), Think-14B (2025-07), Think-32B and Omni-8B (2025-12-23) | Custom licence. No 2026 releases on HF |
| Kakao Kanana | kanana-2-30b-a3b (2025-12, 2601 refresh 2026-01-14), kanana-2-3b and 1.3b (2026-07-24) | Kanana Open License / Kanana License |
| SKT A.X | A.X 4.0 / 4.0-Light (Qwen2.5-based), 3.1 (2025-07), A.X K1 519B (2025-12-29), **A.X K2 688B-A33B (2026-07-28)** | Apache-2.0 |
| Upstage Solar | Solar-Open-100B (2025-12-10), **Solar-Open2-250B (2026-07-22)** | Upstage Solar License (Apache + naming) |
| KT Mi:dm | Midm-2.0 Base 11.5B and Mini 2.3B (2025-07-03); no newer official release | MIT |
| NC AI / VAETKI | `NC-AI-consortium-VAETKI/VAETKI` 112B (2025-12-16), `nc-ai-consortium/VAETKI-20B-A2B`, `-7B-A1B` (2025-12-29) | Card says MIT, but the repo ships an Apache-2.0 text file (metadata inconsistency, VERIFIED) [added by verifier: NCSOFT's own **VARCO** repos are all older and unsuitable. VARCO-VISION 14B / 2.0-14B / 2.0-1.7B / -OCR and GME-VARCO-VISION-Embedding are tagged `cc-by-nc-4.0` (**non-commercial**). `Llama-VARCO-8B-Instruct` (2024-09) is `llama3.1`. There are no 2026 NCSOFT releases [LIVE HF /api/models?author=NCSOFT, 9 repos, 2026-10-19] VERIFIED (licence from HF tags only).] |
| Others (KR) | Trillion Labs Tri-21B-Think (2026-02), Gravity-30B-A5B (2026-09); Motif-2-12.7B (2025-10), Motif-3 315B (2026-08) | Apache-2.0 / MIT |

### Korean sovereign programme (독자 AI 파운데이션 모델)

- **Stage 1 (Jan 2026).** LG AI Research, SKT and Upstage advanced. Naver Cloud was eliminated for failing the from-scratch/independence criterion (use of a Chinese model's encoder/weights was reported). NC AI was eliminated on score. A repechage call drew Motif and Trillion Labs [WEB https://www.smarttoday.co.kr/ko-kr/articles/101222; https://www.unicornfactory.co.kr/article/2026012011314144167]. Motif appears as the 4th team in stage 2, so it was the added team (INFERRED from stage-2 reporting).
- **Stage 2 (announced 2026-08-18).** Weighting: benchmark 40, expert 35, user 25. SKT 70.6, Upstage 69.9 and LG 69.0 advanced; Motif (65.8) was eliminated despite the top AAII score (47) [WEB https://www.mt.co.kr/article/2026081812375747016; https://wikidocs.net/blog/@goodhosup/28868/]. Stage 3 narrows three to two, with a final result expected in early 2027. The ministry is considering restructuring. [corrected by verifier: the 2026-08-18 mt.co.kr article gives the advancing teams, the 40/35/25 weighting, Motif's AAII 47 and only category averages (benchmark 22.5, expert 28.8, user 17.6); it has **no per-team totals**. The totals were released by MSIT on **2026-08-27**, after Motif objected. Per MTN: SKT 70.6 (benchmark 22.2 / expert 29.3 / user 19.1), Upstage 69.9 (22.7/29.1/18.1), LG 69.0 (20.6/29.5/18.9), Motif 65.8 (24.6/27.1/14.1). Motif had the **highest benchmark sub-score** and lost on user evaluation [WEB https://news.mtn.co.kr/news-detail/2026082720102251703, accessed 2026-10-19] VERIFIED. The wikidocs blog returned HTTP 403 on re-fetch. The mt.co.kr article did not mention an "early 2027" final date; it says MSIT will announce the new direction "soon" (UNVERIFIED here).]
- The AAII figure of 47 for Motif conflicts with Artificial Analysis's public open-weights page, whose top score is 46 (MiMo-V2.6-Pro) [WEB https://artificialanalysis.ai/models/open-source]. The index version or date probably differs. UNVERIFIED.

---

## 3. Candidate matrix

### 3a. Identity, architecture and licence (pinned)

Parameters come from HF `safetensors.total` and active parameters from the repo name or card. Context is `max_position_embeddings` from `config.json` at the pinned SHA [LIVE HF config.json fetches]. "Gated" is the HF API flag. [corrected by verifier: for Gemma 4, "verified text" means HF `cardData.license: apache-2.0` plus Google's web page, which shows Apache 2.0 text. None of the five Gemma 4 repos ships a LICENSE file (siblings list re-checked 2026-10-19). That is the same gap these notes flag for A.X K2, so archive Google's licence page alongside the pinned SHA. Re-queried SHAs for 15 repos matched this table exactly.]

| Repo id @ revision SHA | Arch | Total / active | Ctx (config) | Licence (verified text) | Gated | 30-day DL |
|---|---|---|---|---|---|---|
| `google/gemma-4-E2B-it` @ 3e22461f65e89153144f8adb70e3b8c2cc9845a7 | dense, PLE, text+img+audio | 5.12B (2.3B effective) | 131,072 | Apache-2.0 | no | 2.7M |
| `google/gemma-4-E4B-it` @ ee0ef6023621cff504d758262d4e04895a5af4a2 | dense, PLE, text+img+audio | 8.00B (4.5B effective) | 131,072 | Apache-2.0 | no | 4.2M |
| `google/gemma-4-12B-it` @ 707f0a3b8a3c7ad586ed01e27eafbad8a27dd0f7 | dense "Unified" (encoder-free) | 11.96B | 262,144 | Apache-2.0 | no | 1.7M |
| `google/gemma-4-26B-A4B-it` @ 4d7ae4984b7db7de8f8457170b3f1a419ee76d52 | MoE 128e top-8 | 25.8B / 3.8B | 262,144 | Apache-2.0 | no | 10.5M |
| `google/gemma-4-31B-it` @ 842da3794eaa0b77d5f08bae87a17459d91ff475 | dense | 31.3B | 262,144 | Apache-2.0 | no | 9.0M |
| `Qwen/Qwen3.5-4B` @ 851bf6e806efd8d0a36b00ddf55e13ccb7b8cd0a | dense hybrid (GatedDeltaNet 3:1), VLM | 4.66B | 262,144 | Apache-2.0 | no | 7.9M |
| `Qwen/Qwen3.5-9B` @ c202236235762e1c871ad0ccb60c8ee5ba337b9a | dense hybrid, VLM | 9.65B | 262,144 | Apache-2.0 | no | 7.8M |
| `Qwen/Qwen3.6-35B-A3B` @ 995ad96eacd98c81ed38be0c5b274b04031597b0 | MoE 256e top-8, hybrid | 36.0B / ~3B | 262,144 | Apache-2.0 | no | 3.7M |
| `Qwen/Qwen3.8-27B` @ 1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0 | dense hybrid, VLM | 27.8B | 262,144 (→1M YaRN) | Apache-2.0 (tag; LICENSE file 11.5 KB) | no | 7.7M |
| `Qwen/Qwen3.8-Flash-Next` @ de4b8e4d43b917e7706784d8bb445c9af86a3540 | MoE 512e top-10+1 | 180B stored (125B + 51B n-gram + 4B MTP) / 6B | 262,144 | Qwen Community License 1.0 | no | 2.5M |
| `openai/gpt-oss-20b` @ 6cee5e81ee83917806bbde320786a8fb61efebee | MoE 32e top-4, MXFP4 | 20.9B / ~3.6B (UNVERIFIED active) | 131,072 | Apache-2.0 | no | 5.9M |
| `openai/gpt-oss-120b` @ b5c939de8f754692c1647ca79fbf85e8c1e70f8a | MoE 128e top-4, MXFP4 | 116.8B / ~5.1B (UNVERIFIED active) | 131,072 | Apache-2.0 | no | 3.2M |
| `ibm-granite/granite-4.2-3b` @ e459acceac81e5fe67c07d9cfc72329a332e7eb1 | dense | 3.66B | 131,072 | Apache-2.0 | no | 40k |
| `ibm-granite/granite-4.2-8b` @ f8de16cdcdbc6c779ca517604e050d82cc119e44 | dense | 8.79B | 131,072 (card: 512K ext.) | Apache-2.0 | no | 91k |
| `ibm-granite/granite-4.2-30b` @ 9e668ce1c538387ef24d3644e9b0606647762636 | dense | 29.3B | 131,072 | Apache-2.0 | no | 37k |
| `mistralai/Ministral-3-8B-Instruct-2512` @ 5b26027e7b19eeb4b7352e1fed3926375dd2cb4d | dense VLM, FP8 weights | 8.92B | 262,144 | Apache-2.0 | no | 119k |
| `mistralai/Ministral-3-14B-Instruct-2512` @ 29439f81c2be264d8d393273f99e7db9c0961120 | dense VLM, FP8 | 13.95B | 262,144 | Apache-2.0 | no | 119k |
| `mistralai/Mistral-Small-4-119B-2603` @ a11f36bebf709121056b1dbcc943d1c6afbe494d | MoE 128e top-4 | 119.4B | 1,048,576 | Apache-2.0 | no | 72k |
| `mistralai/Mistral-Medium-3.5-128B` @ 22b2b868a15677cfa6061277ed2f653d1349a9ab | dense | 127.7B | 262,144 | Modified MIT (revenue cap) | no | 75k |
| `microsoft/Phi-4-mini-instruct` @ cfbefacb99257ffa30c83adab238a50856ac3083 | dense | 3.84B | 131,072 | MIT | no | 371k |
| `meta-llama/Llama-3.1-8B-Instruct` @ 0e9e39f249a16976918f6564b8830bc894c89659 | dense | 8.03B | 401 (gated) | Llama 3.1 Community | manual | 5.6M |
| `meta-models/Muse-Spark-Open-816B-A42B` @ 0fb02478b02565b2ce7fc57e6051c91172774ac9 | MoE VLM | 822B / 42B | 401 (gated); 1M reported | Muse Model License | manual | 1.8k |
| `nvidia/NVIDIA-Nemotron-3.5-Lightning-30B-A3B-BF16` @ a9904d24bcc1d289a1950fa9d2b978c47cf903b9 | hybrid MoE | 31.6B / 3B | n/a (not fetched) | OpenMDW-1.1 | no | — |
| `nvidia/NVIDIA-Nemotron-3.5-Super-VL-120B-A12B-BF16` @ 1f8953f7f0935358e3605150d22bc15df062061c | hybrid Mamba/MoE VLM, custom code | 124.5B / 12B | 1,048,576 | OpenMDW-1.1 | no | 12k |
| `nvidia/NVIDIA-Nemotron-3-Ultra-550B-A55B-NVFP4` @ 02462641f13d3af838b904f48195b9bb8a1e4ebc | hybrid MoE | 550B / 55B | n/a | OpenMDW-1.1 (ko listed) | no | — |
| `nvidia/NVIDIA-Nemotron-3-Super-120B-A12B-FP8` @ 744b1880a37996c5d56bf454ae164dfd74d77c4e | hybrid MoE | 123.6B / 12B | n/a | NVIDIA Nemotron Open Model License (not read) | no | — |
| `kakaocorp/kanana-2-3b-instruct` @ 6a5d7889964c4c590299d16e309eabab1f73f8a9 | dense (Qwen3 arch, from scratch per card) | 3.51B | 32,768 | Kanana Open License | no | 4.5k |
| `kakaocorp/kanana-2-1.3b-instruct` @ bf4786aa2a1908adce942d53976270132732f720 | dense, custom code | 1.29B | 32,768 | Kanana Open License | no | 3.5k |
| `kakaocorp/kanana-2-30b-a3b-instruct-2601` @ 4a781fe5027da4af8d8208cb21bc5108b913bb62 | MoE (DeepseekV3 arch, MLA) 128e top-6+2 | 30.7B / 3B | 32,768 (128K YaRN) | Kanana License (+10M MAU) | no | 1.5k |
| `K-intelligence/Midm-2.0-Mini-Instruct` @ 383eb221c52a32278f1985257b264ade8d982e60 | dense (Llama arch) | 2.31B | 32,768 | MIT | no | 22k |
| `K-intelligence/Midm-2.0-Base-Instruct` @ 35479c5fc9a18a5db7cc6dbadcf1db68db7beab0 | dense (Llama arch, depth-up-scaled) | 11.5B | 32,768 | MIT | no | 82k |
| `skt/A.X-4.0-Light` @ ba21c20ea1b31ded1ec3e2fb432335077dc4be98 | dense (Qwen2.5-based) | 7.26B | 16,384 | Apache-2.0 + "Built with Qwen 2.5" note | no | 73k |
| `skt/A.X-K2` @ 2287ca456927eed33b899c404c0b2ffaf17aa09f | MoE 256e top-8+1, MLA + sparse gated attn | 688B / 33B | 262,144 | Apache-2.0 (metadata/card; no LICENSE file in repo) | no | 15k |
| `LGAI-EXAONE/K-EXAONE-2.0-750B-A37B` @ fec0c8dd25fdd20ffd09869d5af5277966d5523d | MoE 256e top-8+1 | 749B / 37B | 262,144 | Apache-2.0 (LICENSE + NOTICE read) | no | 3.4k |
| `LGAI-EXAONE/K-EXAONE-236B-A23B` @ 61e6d578eb102b578e5704e2916ac841df9eca0a | MoE 128e top-8 | 237B / 23B | 262,144 | K-EXAONE AI Model License | no | 14k |
| `LGAI-EXAONE/EXAONE-4.5-33B` @ 570aa4b15a4f45ba1133072b45f50198f6e3b4fd | dense VLM | 34.4B | 262,144 | EXAONE 1.2-**NC** | no | 45k |
| `LGAI-EXAONE/EXAONE-4.0-1.2B` @ 3abf2810673c7c0778df64a73c2d52eab32d91c4 | dense | 1.28B | 65,536 | EXAONE 1.2-**NC** | no | 17k |
| `upstage/Solar-Open2-250B` @ 9190fbe63a2ad8e17fc766ccceb36de7c66f004b | MoE 320e top-8+1, hybrid linear attn, NoPE | 250B / 15B | 1,048,576 | Upstage Solar License | no | 7.2k |
| `upstage/Solar-Open-100B` @ 1f591439b14055004d1a5d1a975608953a022fea | MoE 128e top-8 | 102.7B / UNVERIFIED | 131,072 | Upstage Solar License | no | 9.4k |
| `naver-hyperclovax/HyperCLOVAX-SEED-Think-32B` @ 3c2b6338613c4e5ede30788d868363125a262934 | dense VLM | 33.3B | 131,072 | HyperCLOVA X SEED 32B Think | no | 13k |
| `naver-hyperclovax/HyperCLOVAX-SEED-Text-Instruct-1.5B` @ 0728a47d632019a8da5f53b663db1c175dc04115 | dense | 1.59B | 401 (gated auto) | HyperCLOVA X SEED | auto | 1.2k |
| `nc-ai-consortium/VAETKI-20B-A2B` @ 91e960232f8561d300f5a3b2edfd8a726f1569d2 | MoE 128e top-8, custom code | 19.6B / ~2B | 32,768 | MIT tag / Apache text | no | 288 |
| `trillionlabs/Gravity-30B-A5B-Preview` @ 4aec2238fef2c7e8adb8bed5f2b7a4198a265163 | MoE 64e top-8, custom code | 29.6B / 5B | 131,072 | Apache-2.0 | no | 397 |
| `Motif-Technologies/Motif-3` @ 2ed2ed5cfabffa10fdabb2fc0d0288f8e6de893a | MoE 384e, custom code | 314.8B / UNVERIFIED | 262,144 | MIT | no | 2.2k |

Policy-blocked large reference points, pinned for completeness:
- `deepseek-ai/DeepSeek-V4-Flash` @ 60d8d70770c6776ff598c94bb586a859a38244f1 (MIT, 291B, 1M ctx)
- `deepseek-ai/DeepSeek-V4.1-Flash` @ 314113f8a7dadb388215396ba5fbee2c610a04d6 (MIT, 763B)
- `zai-org/GLM-5.3-Flash` @ 46a050bec13002ad29ee795c16e61cf4fa3c4a9c (MIT, 321B)
- `zai-org/GLM-5.3` @ ba32f8c19c8738e2c57c71798c601d477a7bf844 (GLM-5.3 License, 753B)
- `moonshotai/Kimi-K3` @ f831ab66814297da540d832a5235f8e904f29d06 (Kimi K3 License, 2.78T)
- `MiniMaxAI/MiniMax-M3` @ f0e1c1e04d40177e4673a22097036854f536e9c0 (MiniMax Community, 427B)
- `Qwen/Qwen3.6-27B` @ 6a9e13bd6fc8f0983b9b99948120bc37f49c13e9 (Apache)
- `Qwen/Qwen3.5-122B-A10B` @ dc4d348443bc740c68e2d77492492c11606384d5 (Apache)

### 3b. Capability and operations

Abbreviations: TC = tool/function calling (from card / serving parser); SO = structured (JSON-schema) output. "OR json_schema" means OpenRouter lists `structured_outputs` for the hosted endpoint [LIVE GET openrouter.ai/api/v1/models, 471 models]. [corrected by verifier: true for the **paid** slugs only. Re-fetched 2026-10-19 (471 models). The `:free` slugs the repo actually routes to lack `structured_outputs`: `google/gemma-4-31b-it:free` and `google/gemma-4-26b-a4b-it:free` (have `response_format`, tools), `nvidia/nemotron-3-ultra-550b-a55b:free` and `nvidia/nemotron-3.5-lightning:free` (tools only). `nvidia/nemotron-3-super-120b-a12b:free` does list it. Paid `gpt-oss-20b/120b`, `granite-4.2-8b`, `ministral-3b/8b/14b-2512`, `meta/muse-spark-open` and `nemotron-3.5-super-vl` list tools + structured_outputs. OBSERVED] FT = fine-tuning tooling: Unsloth repos [LIVE HF search `author=unsloth`] and Axolotl changelog [WEB https://docs.axolotl.ai/]. TRL/PEFT work for any architecture that transformers loads, so "native" means no `trust_remote_code` (from the HF `custom_code` tag; INFERRED). VRAM assumptions are in §6.

| Model | Korean evidence (label) | TC / SO | FT tooling | Quantisations seen | QLoRA VRAM | 4-bit infer VRAM | Maturity |
|---|---|---|---|---|---|---|---|
| Gemma 4 E2B-it | No Korean-specific numbers; MMMLU 67.4 (VENDOR-REPORTED, card) | native TC; SO not stated; OR n/a | Unsloth (GGUF, MLX, NVFP4, QAT); Axolotl 2026/04; native transformers (needs v5.x) | official QAT q4_0 GGUF, w4a16, mobile | ~6–8 GB | ~4 GB | high |
| Gemma 4 E4B-it | MMMLU 76.6 (VENDOR) | native TC | as above | as above | ~9–12 GB (README: T4 may OOM) | ~6 GB | high |
| Gemma 4 12B-it | MMMLU 83.4 (VENDOR) | native TC | Unsloth (12b-it, GGUF, NVFP4) | official QAT GGUF / w4a16 | ~12–16 GB | ~8–9 GB | medium-high (5 months) |
| Gemma 4 26B-A4B-it | MMMLU 86.3 (VENDOR) | native TC; OR json_schema | Unsloth (GGUF, NVFP4, MLX); MoE LoRA | official QAT GGUF | ~20–26 GB | ~17 GB | high (in production via OR) |
| Gemma 4 31B-it | MMMLU 88.4 (VENDOR) | native TC; OR json_schema | Unsloth bnb-4bit, GGUF, MLX | official QAT GGUF / w4a16 | ~24–30 GB | ~20 GB | high (in production via OR) |
| Qwen3.5-4B / 9B | MMMLU 76.1/81.2, INCLUDE 71.0/75.6, BFCL-V4 50.3/66.1 (VENDOR) | TC (`qwen3_coder` parser) | Unsloth, Axolotl 2026/03 | official GPTQ-Int4 (larger sizes), Unsloth GGUF/MLX | ~6–8 / ~10–13 GB | ~3.5 / ~7 GB | high — **policy-blocked** |
| Qwen3.6-35B-A3B / Qwen3.8-27B | No Korean numbers on card. Qwen3.5 (397B) KMMLU-Pro 77.4 per LG vs 78.4 per SKT (VENDOR, competitor-reported, mutually inconsistent) | TC; OR json_schema | Unsloth, Axolotl (Qwen3.6 2026/09) | FP8, GGUF, MLX, NVFP4 | ~27–33 / ~22–28 GB | ~23 / ~18 GB | high — **policy-blocked** |
| gpt-oss-20b | No Korean benchmark found; KCL only for 120B | TC (harmony); OR json_schema | Unsloth (bnb-4bit, GGUF, BF16), Axolotl 2025/07 | native MXFP4, GGUF | ~16–22 GB (UNVERIFIED) | ~14–16 GB | high |
| gpt-oss-120b | KCL-MCQA 29.2→64.1 with precedents; KCL-Essay 31.6→56.0 (INDEPENDENT) | TC; OR json_schema | Unsloth, Axolotl | native MXFP4 | ~70–80 GB | ~65–70 GB (1×80 GB) | high |
| Granite 4.2 3B / 8B | Korean listed; MMLU-ProX-lite 61.06 for 8B (VENDOR); no Korean-specific test | TC (`qwen3_coder`); OR json_schema (8B) | Axolotl lists Granite 4 (2025/10); no Unsloth 4.2 repos | official GGUF, MLX, FP8, NVFP4, MXFP4 | ~5–6 / ~9–12 GB | ~3 / ~6 GB | medium (2 months) |
| Ministral 3 8B / 14B | Korean listed; no Korean numbers | TC; OR json_schema | Unsloth, Axolotl 2025/12 | official GGUF; FP8 weights | ~10–12 / ~13–17 GB | ~6 / ~9 GB | medium-high |
| Kanana-2-3B-instruct | KMMLU-CoT 43.32 vs Qwen3.5-2B 41.75; HAE-RAE-CoT 43.75 vs 27.84; KoMT 6.92 vs 5.21 (VENDOR) | TC (`qwen3_coder`, BFCL-v3 reported); SO not stated | no Unsloth; native Qwen3 arch → TRL/PEFT (INFERRED) | none official seen (UNVERIFIED) [corrected by verifier: community-only quantisations exist: `mradermacher/kanana-2-3b-instruct-GGUF` (+i1), `mlx-community/kanana-2-3b-instruct-4bit/6bit/8bit`. Kanana-2-30B-A3B-2601 has community AWQ/GPTQ w4a16 and GGUF (e.g. `lee5j/…-awq-w4a16`, `mykor/…-thinking-2601-GGUF`). Nothing official [LIVE HF search, 2026-10-19]] | ~5–6 GB | ~3 GB | low (12 weeks, 4.5k DL) |
| Kanana-2-30B-A3B-2601 | KMMLU 68.26 vs Qwen3-30B-A3B-2507 67.56; HAE-RAE 75.57 vs 53.41; BFCL-v3 live 76.66 (VENDOR) | TC (hermes/qwen parsers) | no Unsloth; native DeepseekV3 arch (INFERRED) | not checked | ~24–30 GB | ~19–20 GB | low (1.5k DL) |
| Mi:dm 2.0 Mini / Base | Base: KMMLU 57.3, HAE-RAE 81.5, Ko-IFEval 82, Ko-MTBench 89.7 (VENDOR; K-Refer/Ko-Sovereign are KT-proprietary sets) | TC via custom vLLM parser (`midm-parser`, vLLM v0.11.0) | no Unsloth; Llama arch → TRL/PEFT/Axolotl generic (INFERRED) | many community GGUF/AWQ/FP8 | ~4–5 / ~12–15 GB | ~2 / ~8 GB | medium (2025-07; older) |
| A.X 4.0 (Light is Qwen2.5-based) | KCL: A.X 4.0 (large) 49.1→71.3 MCQA, 34.7→52.4 essay (INDEPENDENT; best open MCQA without precedents) | — | generic | — | Light ~9–11 GB | Light ~5 GB | medium |
| A.X K2 | KMMLU-Pro 80.5, KoBALT 73.0, CLIcK 91.6 (VENDOR, thinking mode) | TC (`hermes`); SO not stated | needs transformers from source + SKT vLLM fork | official FP8 (repo default), NVFP4, GGUF, EAGLE3 | n/a (≥8×80 GB) | ~400+ GB | low (12 weeks) |
| K-EXAONE 2.0 | KMMLU-Pro 69.1, CLIcK 84.2, HRM8K-KSM 91.1, Ko-LongBench 89.6, KGC-Safety 99.8 (VENDOR) | TC (`qwen3_xml` / `qwen3_coder` parsers) | LG vLLM/SGLang forks required | official FP8, NVFP4, DSpark | n/a | ~420–450 GB | low |
| Solar Open 2 250B | KMMLU-Pro 78.4, CLIcK 90.7, HAE-RAE v1.1 73.8, **KBL 75.5**, KorMedMCQA 93.0 (VENDOR) | TC (`solar_open2` parser, OpenAI schema) | vLLM recommended; Upstage transformers branch | NotaAI GGUF (per card) | n/a | ~150 GB (card min 4×H200 BF16) | low |
| Nemotron 3 Ultra / 3.5 Super-VL | Nemotron 3 Ultra KMMLU-Pro 69.2, CLIcK 84.1 (VENDOR, reported by competitor SKT) | TC; OR json_schema | Axolotl context-parallel for Nemotron-H (2026/06); Unsloth 3.5 GGUF/NVFP4 | NVFP4 official | n/a | Super ~70 GB; Ultra ~300+ GB | high (in production via OR) |
| HyperCLOVA X SEED Think 32B / 14B | KCL (14B): 31.3→57.6 MCQA (INDEPENDENT); 32B card lists Korean benchmarks only as an image (no text numbers) | TC not documented | 14B custom code | — | ~24–30 GB (32B) | ~20 GB | medium |
| EXAONE 4.0 32B | KCL 36.4→72.3 MCQA (INDEPENDENT) | — | Unsloth (4.0-32B) | official AWQ/GPTQ/GGUF | — | — | **NC licence** |
| Phi-4-mini | KCL 22.0→30.6 MCQA, essay 6.0→18.9 (INDEPENDENT, weakest) | TC | Unsloth/TRL | ONNX/GGUF | ~5–6 GB | ~3 GB | high but weak in Korean |

---

## 4. Licence matrix (key terms, read from the LICENSE file at the pinned SHA unless stated)

All [LIVE GET huggingface.co/<repo>/resolve/<sha>/<file>, 2026-10-19, HTTP 200], VERIFIED unless marked. This is a reading of the texts, not legal advice; the Korean licences carry KCAB-arbitration and unilateral-change clauses that counsel should review.

| Licence (models) | Commercial use | Attribution / naming for derivatives | Acceptable-use / field restrictions | Output / distillation clauses | Thresholds |
|---|---|---|---|---|---|
| Apache-2.0: Gemma 4, Qwen3.5/3.6, Qwen3.8-27B, gpt-oss, Granite 4.2, Ministral 3, Mistral Small 3.2/4, Large 3, Kanana 1.5, A.X 4.0/K1/K2, K-EXAONE 2.0, Trillion | yes | keep licence/NOTICE; mark modified files | none in licence. Gemma 4 has separate "Prohibited use"/terms pages not read (UNVERIFIED). gpt-oss usage-policy file not checked (UNVERIFIED) [corrected by verifier: gpt-oss `USAGE_POLICY` @ 6cee5e81… (200 bytes, HTTP 200) only asks users to comply with applicable law, with no field restrictions. VERIFIED. The Gemma Prohibited Use Policy page was read: it is scoped to "Gemma or Model Derivatives", dated 2024-02-21, does not name Gemma 4 or Apache 2.0, and has unlicensed-practice clauses (§2.2, §3.6). Whether it binds Gemma 4 is UNVERIFIED (INFERRED: Apache-2.0 does not incorporate it)] | none | none |
| MIT: Phi-4, Mi:dm 2.0, Motif-3, DeepSeek V3.2/V4.x (tag only), GLM-5.3-Flash/4.7-Flash/4.5-Air, Kimi-Linear | yes | keep notice | none | none | none |
| OpenMDW-1.1: Nemotron 3 Ultra, 3.5 Lightning/Super-VL/Bolt | yes | retain notices | none | explicitly none on outputs | none; patent/copyright retaliation termination [WEB https://openmdw.ai/license/1-1/]. The Bolt repo's LICENSE file is 0 bytes (OBSERVED) |
| Qwen Community License 1.0 (Qwen3.8-Flash-Next) | yes, **except** licensees running a "Model as a Service" or "AI Work Assistant" (coding/office) business, which need a separate licence. Domain assistants are excluded from the AWA definition | copyright notice. Model name must be displayed on the UI if >100M MAU or >US$20M monthly revenue | must comply with law / no IP infringement | none | 100M MAU / $20M monthly revenue (display) |
| Qwen3.8-Max License (2.4T) | as above, but the MaaS/AWA separate licence applies only above US$50M 12-month revenue | same | same | none | $50M |
| Kimi K2.6 (modified MIT) | yes | "Kimi K2.6" on UI if >100M MAU or >$20M monthly revenue | none | none | as stated |
| Kimi K3 | yes; MaaS businesses >$20M 12-month revenue need an agreement; internal use exempt | "Kimi K3" on UI above thresholds | law compliance | none | 100M MAU / $20M |
| GLM-5.3 | yes; MaaS >US$10B revenue → Z.ai security review | notice | law compliance | none | $10B |
| MiniMax Community (M3) | grant text says "non-commercial purposes", yet §2 permits commercial use with **"Built with MiniMax M3"** display plus a one-time notice email (authorisation needed above $20M yearly revenue). Internally inconsistent | display required for any commercial use | prohibited-use appendix (military, harm to minors, harmful disinformation, discrimination incl. immigration status) | none explicit | $20M yearly revenue |
| MiniMax M2.7 | **non-commercial**; commercial requires prior written authorisation | "Built with MiniMax M2.7" | same appendix | — | — |
| Mistral Medium 3.5 (Modified MIT) | yes, **unless company monthly revenue > US$20M** (no rights at all above it, including derivatives) | attribution notice | none | none | $20M/month |
| Muse Model License (Muse Spark Open) | yes; MaaS providers >$20M 12-month revenue need an agreement; own-product features exempt | **"Built with Muse Spark Open" must be displayed** (UI, docs, website or settings) for any product using it or any derivative. Derivatives include models distilled from its outputs | Usage Policy incl. **"unauthorized or unlicensed practice of any profession including … legal"**; not intended for under-18s; disclose known dangers | distillation permitted, but the distilled model is a "Derivative" bound by the licence | $20M |
| Llama 3.1 Community | yes | **"Built with Llama"** display; "Llama" prefix for distributed derivative models (incl. trained on outputs); Notice file | AUP by reference (Llama 3.1 AUP not fetched; its legal-practice clause is UNVERIFIED in this task) | outputs used to improve models → naming rule | 700M MAU |
| Llama 4 Community | not read (config/licence gated, 401 on config) | UNVERIFIED | UNVERIFIED (EU multimodal restriction recalled from prior knowledge only) | — | — |
| Kanana Open License (kanana-2-3b/1.3b) | own service yes (§4.2); a separate licence is needed to resell API access, SI/on-prem or on-device | for products/services containing Kanana: **"Powered by Kanana"** display and Notice file; "Kanana" prefix for distributed models trained on Kanana or its outputs | Kakao Responsible AI guidelines incorporated | "Derivative Works" include distillation/synthetic-data-trained models | none for own service |
| Kanana License (kanana-2-30b-a3b-2601) | as above, **plus** a separate licence if >10M MAU at release date | same | same | same | 10M MAU |
| HyperCLOVA X SEED (14B/32B/1.5B) | yes, but a separate licence is required if >10M MAU **or** the product is "substantially similar to or directly competes with" any NAVER product [corrected by verifier: the MAU test is a snapshot "as of the Model Release Date" (32B Think: 2025-12-29; >10M MAU in the preceding calendar month), not an ongoing cap (§4). Kanana's 10M MAU (§4.2) and Llama 3.1's 700M MAU are likewise measured at release date. For a new service like Visable they effectively never bite. The NAVER competition clause has no such limit and stays the real risk.] | **"Powered by HyperCLOVA X"**; "HyperCLOVA X" prefix on derived models; Notice file | AUP 1.d forbids **"unauthorized or unlicensed professional services … legal"**; NAVER may amend the agreement unilaterally | distillation from outputs = Derivative Model | 10M MAU; competition clause |
| Upstage Solar License (Solar Open / Open 2) | yes (Apache-based) | only if you **distribute or make available** a derivative AI model: name must start with "Solar", plus "Built with Solar" display | Apache trademark clause | — | none |
| K-EXAONE AI Model License (K-EXAONE-236B) | §2.1 commercial use granted, irrevocable; **§2.2 distribution, sublicensing or making the model/derivatives available to third parties for commercial purposes requires a separate agreement** | derivative names must begin with "K-EXAONE" [verifier: per §2.1 the prefix applies "in the event the Model or Derivative Work is distributed"] | ethical-use list (no misinformation, discrimination, etc.); termination for breach | Licensor claims no output rights | none stated |
| EXAONE AI Model License 1.2-NC (EXAONE 4.0, 4.0.1, 4.5) | **no** — research/education only | "EXAONE" prefix | — | **outputs may not be used to develop competing models** | — |
| VAETKI | MIT tag vs Apache-2.0 text file shipped | — | — | — | metadata conflict to resolve |

**Applicability to Visable (INFERRED, needs counsel):**
- The Qwen/Kimi/Muse MaaS clauses do not bite unless Visable exposes raw model inference as an API.
- Visable's domain assistant is outside Qwen's "AI Work Assistant" definition.
- The HyperCLOVA X "unlicensed legal services" AUP item and its competition clause (Naver runs consumer AI search/assistant products) are the highest-risk terms for an immigration information product.
- Muse's legal-practice AUP is similar.
- K-EXAONE-236B §2.2 is ambiguous for a hosted product and should be treated as requiring LG's agreement.

---

## 5. Ranked shortlists

### Artemis — compact extraction/classification/routing

Selection criteria: ≤~9B total parameters (or tiny active MoE); permissive licence; reliable JSON/tool output; Korean tokenisation; QLoRA on a single T4/L4; Unsloth/TRL support; policy-compatible.

1. **`google/gemma-4-E4B-it` @ ee0ef602…** (with `gemma-4-E2B-it` @ 3e22461f… as the cheaper sibling).
   - For: Apache-2.0 and ungated (VERIFIED). Native function calling (README-ONLY, card). 128K ctx. The widest tooling of any candidate (Unsloth GGUF/MLX/NVFP4/QAT, Axolotl 2026/04, official QAT GGUF). Same family as the production router/translation model and as the repo's own experiment, so one tokenizer/template across Artemis and Hestia.
   - Against: no Korean-specific benchmark at all (only MMMLU 76.6, VENDOR-REPORTED). Multimodal towers inflate memory (README warns of T4 OOM). The checkpoint is `Gemma4ForConditionalGeneration`, so confirm `AutoModelForCausalLM` + PEFT target modules load cleanly in the smoke test (UNVERIFIED).
2. **`kakaocorp/kanana-2-3b-instruct` @ 6a5d7889…**
   - For: Korean-native (from scratch per card, >30% better Korean tokenisation claimed). Vendor Korean scores clearly above Qwen3.5-2B (HAE-RAE-CoT 43.75 vs 27.84; KoMT 6.92 vs 5.21, VENDOR-REPORTED). Tool calling. Qwen3 architecture loads natively, so TRL/PEFT should work (INFERRED). ~5–6 GB QLoRA.
   - Against: Kanana Open License requires "Powered by Kanana" on the service and a "Kanana" prefix for any distributed derivative. 32K ctx. Released 2026-07-27, 4.5k downloads, no Unsloth or official GGUF seen. [corrected by verifier: HF `createdAt` is 2026-07-24 (§2 is right). The LICENSE header reads "Kanana Release Date: July 17, 2025", so the Kanana-2 3B licence reuses an older template. Community GGUF/MLX builds do exist (see §3b).] Its Qwen3-architecture lineage may trigger an owner policy question (architecture only, not weights, per card).
3. **`ibm-granite/granite-4.2-3b` @ e459acce… / `granite-4.2-8b` @ f8de16cd…**
   - For: Apache-2.0, Korean in the supported-language list, OpenAI-schema tool calling with thinking / non-thinking / low-effort modes, official GGUF/MLX/FP8/NVFP4, available on OpenRouter with json_schema (8B). Policy-neutral (US vendor).
   - Against: zero Korean benchmark evidence (VENDOR MMLU-ProX-lite 61.06 only). Unsloth has no 4.2 repos; Axolotl lists only "Granite 4".
4. **`K-intelligence/Midm-2.0-Mini-Instruct` @ 383eb221…**
   - For: MIT, 2.3B, Korean-centric vendor scores, Llama architecture (easiest FT path), tool calling via a vLLM parser.
   - Against: July-2025 generation, 32K ctx, no thinking mode, KT-proprietary benchmarks dominate its card.
5. **`mistralai/Ministral-3-8B-Instruct-2512` @ 5b26027e…**
   - For: Apache, Korean listed, mature tooling (Unsloth, Axolotl, official GGUF), OpenRouter json_schema.
   - Against: no Korean evidence.
6. *(Policy-blocked, technically strongest)* **`Qwen/Qwen3.5-4B` / `Qwen3.5-9B`.** BFCL-V4 50.3/66.1 and TAU2 79.9/79.1 (VENDOR), Unsloth+Axolotl, Apache. Blocked by `CHINESE_ONLY_MODEL_PREFIXES`.

**Top disqualifiers:**
- EXAONE-4.0-1.2B: non-commercial.
- HyperCLOVAX-SEED-Text-1.5B: gated auto, legal-services AUP, competition clause.
- Phi-4-mini: weakest Korean legal result in KCL, 22.0→30.6 (INDEPENDENT).
- Llama 3.2 1B/3B: Korean not an officially supported language (Llama 3.1 card language list: en, de, fr, it, pt, hi, es, th), plus the AUP.
- VAETKI-7B-A1B: custom code, 268 downloads, licence-metadata conflict.

**Design note (INFERRED):** much of Artemis's work (status-code/subcode extraction, dates) is regex-settleable. The workspace rule "prefer a deterministic check to a model call" [DOC ~/.claude/AGENTS.md] suggests Artemis should handle only the residual ambiguous intent/procedure classification, which favours the smallest model that passes evals (E2B / Kanana-2-1.3B / Mi:dm Mini).

### Athena — advanced reasoning over supplied evidence

Selection criteria: strong long-context reasoning; faithfulness to evidence; Korean legal/administrative reading; permissive or clear commercial licence; feasible hosting (self-host or an existing API).

1. **`upstage/Solar-Open2-250B` @ 9190fbe6…**
   - For: the only open model with a vendor-reported **Korean legal benchmark (KBL 75.5)**, ahead of DeepSeek-V4-Flash 72.8 in the same VENDOR table. [corrected by verifier: the numbers re-check against the card, but "only" is too strong. The same Upstage table reports KBL for three other open models (Solar Open 100B 65.5, MiMo-V2.5 69.8, DeepSeek-V4-Flash 72.8) and for GPT-5.4 mini (75.3, only 0.2 behind). DeepSeek-V4-Flash also beats Solar Open 2 on KMMLU-Pro (78.9 vs 78.4) and KorMedMCQA (94.1 vs 93.0). The independent KCL also scores open models (§7). Accurate wording: "the only 2026 open model whose own vendor reports a Korean legal benchmark". The card does not describe KBL. Per a WebSearch summary, KBL is a University of Seoul / LBox / Hanyang benchmark (EMNLP 2024 Findings, DOI 10.18653/v1/2024.findings-emnlp.319; arXiv 2410.08731) with closed-book and RAG settings, README-ONLY.] KMMLU-Pro 78.4, CLIcK 90.7, HAE-RAE 73.8 (all VENDOR-REPORTED). Only 15B active, 1M ctx, OpenAI-schema tool calling. Licence is Apache-based; naming duties apply only if a *derivative model* is distributed or made available. Sovereign stage-2 finalist (Upstage 69.9).
   - Against: not on OpenRouter (Upstage's hosted `solar-pro4` is a different, proprietary product). Card minimum is 4×H200 (BF16), roughly 2×H100 at 4-bit (INFERRED). Initialised by weight transfer from Solar Open 1 (not from scratch). 7.2k downloads. [corrected by verifier: per the card, only ~2.3% of weights survived the architecture change and were carried over. The rest were randomly initialised, so it is mostly a fresh pre-train (README-ONLY).]
2. **`skt/A.X-K2` @ 2287ca45…**
   - For: highest vendor Korean scores seen (KMMLU-Pro 80.5, CLIcK 91.6; VENDOR-REPORTED by SKT against competitors). [corrected by verifier: not the highest. LG's K-EXAONE 2.0 card gives DeepSeek-V4-Pro (max) exactly the same KMMLU-Pro 80.5 and CLIcK 91.6. On SKT's own table DeepSeek-V4-Flash beats A.X K2 on KoBALT (75.3 vs 73.0) and on KMO26 (94.4 vs 92.5). Accurate wording: the highest Korean scores among policy-compatible open models, tied by competitor-reported DeepSeek-V4-Pro. All of SKT's models were run in thinking mode.] Apache-2.0, from scratch, 256K ctx, hermes tool calling. Top composite in sovereign stage 2 (70.6). Its predecessor A.X 4.0 had the best **independent** no-evidence KCL-MCQA among open models (49.1).
   - Against: 688B-A33B needs a multi-GPU node, a forked vLLM (`axk2-v0.23.0`) and transformers from source. No LICENSE file in the repo (only metadata/card), so ask SKT to add one. Not on OpenRouter.
3. **`LGAI-EXAONE/K-EXAONE-2.0-750B-A37B` @ fec0c8dd…**
   - For: clean Apache-2.0 LICENSE+NOTICE (a notable shift from LG's earlier NC/custom licences). Best vendor safety numbers (KGC-Safety 99.8, ROK-Fortress 89.5; VENDOR). 262K ctx, tool calling.
   - Against: on LG's own table it trails Qwen3.5 and DSV4-Pro on KMMLU-Pro (69.1 vs 77.4/80.5) and CLIcK (VENDOR). Requires LG forks. Largest of the three.
4. **`openai/gpt-oss-120b` @ b5c939de…**
   - For: Apache-2.0, fits one 80 GB GPU (MXFP4), very mature, OpenRouter json_schema, policy-compatible. **INDEPENDENT** KCL numbers exist: with precedents, MCQA 64.1 and essay 56.0. That is middling: it beats Gemma 3 27B, Kanana 1.5 8B and HCX 14B on essay but trails EXAONE 4.0 32B / A.X 4.0 on MCQA.
   - Against: 2025 vintage, weak Korean knowledge without evidence (29.2).
5. **NVIDIA Nemotron 3 Ultra 550B-A55B (OpenMDW) / Nemotron 3.5 Super-VL 120B-A12B @ 1f8953f7…**
   - For: already the production Basic/verifier chain via OpenRouter (free and paid endpoints, json_schema). [corrected by verifier: `nemotron-3-ultra-550b-a55b:free` (the Basic primary) lists tools but **not** `structured_outputs`. Only `nemotron-3-super-120b-a12b:free` and the paid slugs list it (OpenRouter catalog, 2026-10-19).] OpenMDW is permissive with no output restrictions. Korean is listed for Ultra.
   - Against: only competitor-reported Korean numbers (Ultra KMMLU-Pro 69.2 on SKT's card). Super-VL lists no Korean.
- **Athena-lite:** `google/gemma-4-31B-it` @ 842da379… (Apache, single-GPU 4-bit, MMMLU 88.4 VENDOR, in production). Use as the evidence-reasoning fallback and as the Hestia base.
- *(Policy-blocked)* DeepSeek-V4/V4.1-Flash (MIT; KMMLU-Pro 78.8/78.9 and KoBALT 75.3 in competitors' VENDOR tables), GLM-5.3 (AAII 45 on the Artificial Analysis page, INDEPENDENT general index), Kimi K3 (44), Qwen3.8-27B (34).
- *Caution, not disqualified:* `meta-models/Muse-Spark-Open-816B-A42B` (AAII 39 on the Artificial Analysis page, on OpenRouter as `meta/muse-spark-open` with json_schema). Its licence forces a "Built with Muse Spark Open" display and carries the legal-practice AUP.

**Top disqualifiers:**
- EXAONE 4.5-33B: NC (it would otherwise be a strong single-GPU Korean reasoner).
- MiniMax M2.7: NC.
- Mistral Medium 3.5: revenue cap, and no Korean evidence.
- HyperCLOVA X SEED Think 32B: legal-services AUP plus competition clause.
- K-EXAONE-236B: §2.2 third-party availability clause.
- Motif-3: custom code, MIT, but eliminated in stage 2; no card benchmarks fetched (UNVERIFIED).

### Hestia — professional assistant, shared base + LoRA

Selection criteria: mid-size dense or cheap-active MoE that LoRA-tunes on 1×24–48 GB; mature multi-LoRA serving; Korean prose quality; licence allows serving fine-tuned derivatives in-product; policy-compatible; ideally the same family as Artemis.

1. **`google/gemma-4-31B-it` @ 842da379…** (quality) **/ `google/gemma-4-12B-it` @ 707f0a3b…** (cost; already the repo's planned quality run).
   - For: Apache, ungated, dense, so LoRA is simple. QLoRA ~24–30 GB / ~12–16 GB. Unsloth/Axolotl support. Hosted 31B and 26B-A4B endpoints are already in production. Shares a template with an E4B Artemis.
   - Against: no Korean-specific evidence. The 12B is the newest and least battle-tested size. The 26B-A4B is cheaper to serve but MoE LoRA is less mature.
2. **`kakaocorp/kanana-2-30b-a3b-instruct-2601` @ 4a781fe5…**
   - For: strongest vendor Korean profile at 3B active (KMMLU 68.26, HAE-RAE 75.57, KoMT 8.21; BFCL-v3 live 76.66; VENDOR-REPORTED). A Kanana-2 3B (Artemis) + 30B (Hestia) pairing is fully Korean-native.
   - Against: Kanana License (10M MAU cap, "Powered by Kanana", "Kanana" naming for distributed derivatives, distillation counts as derivative). Native 32K ctx. 1.5k downloads, no Unsloth.
3. **`K-intelligence/Midm-2.0-Base-Instruct` @ 35479c5f…**
   - For: MIT with no attribution beyond the notice, 11.5B dense Llama architecture (cheapest Korean-native LoRA base). Vendor HAE-RAE 81.5 and Ko-IFEval 82.
   - Against: July-2025 vintage, no reasoning mode, 32K ctx, its vendor benchmarks lean on KT-proprietary sets.
4. **`openai/gpt-oss-20b` @ 6cee5e81…**
   - For: Apache, about 16 GB inference, Unsloth/Axolotl LoRA recipes, policy-compatible.
   - Against: no Korean evidence for the 20B. The harmony chat format adds template work.
5. **`ibm-granite/granite-4.2-30b` @ 9e668ce1…**
   - For: Apache dense 29B, Korean listed.
   - Against: no Korean evidence.
6. *(Policy-blocked, technically strongest)* `Qwen/Qwen3.6-27B` / `Qwen/Qwen3.8-27B` (Apache, Unsloth, MTP; 7.7M downloads for 3.8-27B).

**Top disqualifiers:**
- EXAONE 4.5-33B (NC).
- HyperCLOVA X SEED Think 32B (AUP/competition).
- Mistral Medium 3.5 (revenue cap).
- Solar-Open-100B: viable licence, but 100B MoE LoRA is costly; it is the most plausible upgrade if Solar becomes the Athena family.

**Shared-base recommendation (INFERRED):** pick one tokenizer family for Artemis+Hestia. Gemma 4 (E4B + 31B/12B) is policy-aligned and lowest-risk. Kanana 2 (3B + 30B-A3B) is the Korean-native alternative but adds attribution and MAU terms. Neither has independent Korean evidence, so a Waymaker-specific eval is mandatory before choosing.

---

## 6. VRAM assumptions (all INFERRED estimates)

- **4-bit inference:** weights ≈ total parameters × ~0.6 GB per billion (Q4_K_M/AWQ ≈ 4.5–5 bits/weight incl. scales). Add 1–2 GB for KV cache and runtime at 8K context, single stream. For MoE, *all* experts stay resident, so total (not active) parameters drive memory; active parameters drive speed only. gpt-oss ships MXFP4, so its native footprint ≈ 0.55 GB/B. Long contexts (128K+) add several to tens of GB of KV cache depending on attention type. Hybrid linear-attention models (Qwen3.5+, Solar Open 2, Granite H) grow KV more slowly.
- **QLoRA training:** NF4 base (~0.6–0.65 GB/B incl. double-quant constants) + LoRA r=8–16 on all attention+MLP projections + paged 8-bit AdamW on adapters only. Sequence 2048, micro-batch 1, gradient checkpointing, bf16 compute: activations and overhead ≈ 3–6 GB. Rule: ≈ 0.65 × B + 4 GB. Vision/audio towers (Gemma 4 E-models, Qwen3.5 VLMs) add 0.5–1.5 GB unless stripped. The repo notebook's `ULTRA_LOW_MEM` (512 tokens) lowers the activation term.
- **GPU fit examples:**
  - T4 16 GB: E2B, Kanana-2-3B, Mi:dm Mini, Granite 3B; E4B is borderline (matches README:41).
  - L4 24 GB: E4B, 12B, Granite 8B, Mi:dm Base.
  - A100 40 GB / L40S 48 GB: 26B-A4B, 31B, Kanana-2-30B-A3B, gpt-oss-20b.
  - Athena self-host: 1×H100 80 GB for gpt-oss-120b; ~2×H100 for Solar Open 2 (4-bit); 8×H100-class for A.X K2 / K-EXAONE 2.0.

---

## 7. Korean benchmark evidence — what is and is not known

**INDEPENDENT:**
- **KCL (LBox; arXiv 2512.24572, EACL 2026).** Covers 30+ models, mostly accessed around 2025-10-02. MCQA vanilla → with supporting precedents; Essay judged by Gemini 2.5 Flash [WEB https://arxiv.org/html/2512.24572v2]:

  | Model | MCQA vanilla → with precedents | Essay vanilla → with precedents |
  |---|---|---|
  | Qwen3 235B Thinking | 41.5 → 76.9 | 39.2 → 63.9 |
  | A.X 4.0 | 49.1 → 71.3 | 34.7 → 52.4 |
  | EXAONE 4.0 32B | 36.4 → 72.3 | 32.6 → 47.5 |
  | Llama 4 Maverick | 43.3 → 72.3 | 25.6 → 44.3 |
  | DeepSeek-V3 | 37.3 → 69.3 | 34.3 → 57.6 |
  | Qwen3 32B | 35.0 → 65.4 | 29.2 → 55.4 |
  | gpt-oss-120b | 29.2 → 64.1 | 31.6 → 56.0 |
  | HCX SEED Think 14B | 31.3 → 57.6 | 26.2 → 42.8 |
  | Gemma 3 27B | 35.1 → 53.6 | 23.6 → 44.0 |
  | Kanana 1.5 8B | 29.4 → 47.5 | 21.8 → 49.1 |
  | Phi-4-mini | 22.0 → 30.6 | 6.0 → 18.9 |
  | Gemini 2.5 Pro (reference) | 66.1 → 89.3 | 60.5 → 74.9 |

  The dataset is CC-BY-NC-4.0, so it is usable for internal eval only, not for training a commercial model (README-ONLY via search summary of the HF dataset card).
- **Artificial Analysis open-weights page** (general, not Korean): MiMo-V2.6-Pro 46, GLM-5.3 45, Kimi K3 44, GLM-5.3-Flash 42, DeepSeek V4.1 Flash 39, Muse Spark Open 39, Qwen3.8-27B 34, MiniMax-M3 29, Nemotron 3.5 Super VL 26, Inkling 25. Gemma 4, gpt-oss and the Korean models were not on the rendered page [WEB https://artificialanalysis.ai/models/open-source].
- **Horangi v4 (W&B Korea).** horangi.ai → wandb.ai → forge.coreweave.com redirect chain; the page is JS-rendered and returned no rows. Not readable [WEB https://horangi.ai, OBSERVED failure].

**VENDOR-REPORTED** (summarised in §3b): K-EXAONE 2.0 card, A.X K2 card, Solar Open 2 card, Kanana 2 cards, Mi:dm 2.0 card, Qwen3.5 card, Gemma 4 card, Granite 4.2 card.

**Inconsistencies seen:**
- Qwen3.5 KMMLU-Pro is 77.4 on LG's table but 78.4 on SKT's.
- DeepSeek-V4-Flash is 78.8 (SKT) vs 78.9 (Upstage).
- [added by verifier] Qwen3.5 CLIcK is 88.9 on LG's table vs 88.4 on SKT's. DeepSeek-V4-Pro (max) on LG's table (KMMLU-Pro 80.5, CLIcK 91.6) exactly equals A.X K2's self-reported numbers [WEB https://huggingface.co/LGAI-EXAONE/K-EXAONE-2.0-750B-A37B; https://huggingface.co/skt/A.X-K2, re-fetched 2026-10-19] VENDOR-REPORTED.
- The K-EXAONE 67.3 KMMLU-Pro figure on BenchLM equals LG's own card value, i.e. it is not independent [WEB https://benchlm.ai/benchmarks/kmmluPro].
- KMMLU-Pro itself was authored by LG AI Research with OneLineAI. It covers 2,822 items from Korean licensure exams, including 696 law items (judicial scrivener, lawyer, labour attorney, patent attorney). The EXAONE vendor therefore designed the benchmark it reports on [WEB https://huggingface.co/datasets/LGAI-EXAONE/KMMLU-Pro].

**Not found:** any independent KMMLU-Redux/Pro, HAE-RAE, CLIcK, KoBEST or Ko-IFEval leaderboard covering Gemma 4, Qwen3.6+, A.X K2, K-EXAONE 2.0, Solar Open 2 or Kanana 2. **Waymaker must run its own Korean eval**: the golden behaviour set plus a held-out set of real evidence packs, plus KCL-MCQA with precedents for Athena (internal use only, given NC data).

---

## 8. What I could not verify

- Gemma 4 "Prohibited use policy" and "Terms of use" pages are linked from the licence page but not fetched. Whether Google still attaches a separate use policy to Apache-licensed Gemma 4 is UNVERIFIED. [partly resolved by verifier: the Prohibited Use Policy page was fetched (see §4 Apache row). Its binding force on Gemma 4 is still UNVERIFIED. The Gemma 4 licence page is now marked deprecated and points to gemma.ai. The Terms of Use page was not fetched.]
- Llama 3.1 AUP text and the Llama 4 licence were not fetched (gated). Their legal-practice clause and EU multimodal restriction are UNVERIFIED in this task.
- gpt-oss usage-policy file: not checked. Active parameters for gpt-oss and Solar-Open-100B: not read from cards. [verifier: the gpt-oss `USAGE_POLICY` has now been read, a single comply-with-law sentence. Active parameters are still unread.]
- NVIDIA Nemotron Open Model License (Nemotron 3 Super/Nano): not read. `nvidia/NVIDIA-Nemotron-3.5-Bolt-74B-A9B-BF16` LICENSE file returned HTTP 200 with 0 bytes (OBSERVED).
- A.X K2 has no LICENSE file in the repo; Apache-2.0 is asserted only by metadata and card (VERIFIED absence; terms README-ONLY).
- FT tooling for Korean models (Kanana 2, Mi:dm, A.X K2, Solar Open 2, K-EXAONE) was inferred from architecture. No Unsloth repos exist for them (VERIFIED by HF search); Axolotl's changelog does not mention them.
- Unsloth search for granite-4.2, kanana, Midm, A.X, Solar-Open and K-EXAONE returned 0 repos (VERIFIED).
- Whether `AutoModelForCausalLM` (used by the notebook) loads the Gemma 4 / Qwen3.5 `…ForConditionalGeneration` checkpoints text-only, and whether all seven LoRA target-module names exist in Gemma 4 (its 12B config sets `attention_k_eq_v: true`), is UNVERIFIED. Check in the smoke test.
- VRAM numbers are estimates (INFERRED), not measurements.
- Most model-card content (benchmarks, TC parsers, release dates) came through WebFetch summaries of HF pages, not raw file reads. That makes them README-ONLY-grade even where marked VENDOR-REPORTED. Raw README.md files were saved only for Qwen3.5-4B/9B and Qwen3.6-27B/35B-A3B (tables parsed locally). Further README downloads failed because the local disk filled (ENOSPC; see live actions).
- The KCL ACL Anthology page fetch failed (`socket hang up`). The arXiv HTML was used instead.
- Motif AAII 47 vs the Artificial Analysis page maximum of 46: unresolved.

---

## 9. Recommendations

1. **Fix the stale gating assumption** in `experiments/waymaker-gemma4-finetune`. Gemma 4 E4B/12B are ungated Apache-2.0 at the pinned SHAs, so the `MODEL_IS_GATED` guard and README rows 41-42 and 171-173 are stale. Pin `revision=` to the SHAs above in `from_pretrained`.
2. **Ask the owner to rule explicitly** on whether `CHINESE_ONLY_MODEL_PREFIXES` covers self-hosted fine-tunes and Qwen-derived Korean models (A.X 4.0 Light; FrogNano). This single decision moves Qwen3.5/3.6/3.8 in or out of every shortlist.
3. **Default plan:** Artemis = Gemma 4 E4B (E2B if evals allow); Hestia = Gemma 4 31B (or 12B) with LoRA; Athena = keep the hosted Nemotron/gpt-oss/Gemma chain now, and run a bake-off of Solar Open 2 vs A.X K2 vs K-EXAONE 2.0 on Waymaker evidence packs before committing GPUs.
4. **Korean-native contingency:** Kanana-2-3B + Kanana-2-30B-A3B. Budget for "Powered by Kanana" UI attribution and the 10M-MAU clause. [corrected by verifier: the 10M-MAU clause (Kanana License §4.2) is tested "as of Kanana Release Date", a one-time snapshot, so it is unlikely to apply to Visable. The live constraints are §4.1 (a separate licence to offer API/cloud access, SI/on-prem or on-device to third parties), §3.1(v) attribution/naming, and §9.4 (no use of Model Weights to train new models except as expressly permitted).]
5. **Never adopt** EXAONE 4.x (NC), MiniMax M2.7 (NC) or HyperCLOVA X SEED (legal-services AUP + competition clause) for production. Treat Muse Spark Open and Llama as acceptable only with counsel sign-off on the "unlicensed practice of law" AUP and with mandatory UI attribution.
6. **Put licence-mandated attributions** ("Built with …", "Powered by …") in a static about/licence page. The answer guard [CODE backend/services/knowledge/guard.py:37-40] would otherwise flag vendor names in answers. Consider extending its provider regex to the Korean model names.
7. **Build a Korean eval harness before any selection:**
   - golden behaviour set (repo);
   - KCL-MCQA with precedents (internal, NC);
   - Ko-IFEval-style format adherence for the 6-section answer;
   - JSON-schema validity rate for Artemis outputs.

   Treat all vendor Korean numbers as hypotheses.

---

## 10. Live actions log (2026-10-19)

- HF API org listings for 19 orgs (Qwen, google, meta-llama, mistralai, deepseek-ai, openai, microsoft, ibm-granite, zai-org, moonshotai, MiniMaxAI, LGAI-EXAONE, naver-hyperclovax, kakaocorp, skt, upstage, K-intelligence, NCSOFT, nvidia): JSON returned.
- About 16 HF search queries: JSON returned. The `author=meta-llama&sort=lastModified` query returned a non-list error object.
- `/api/models/<id>` for 84 repos plus 4 NVIDIA repos: HTTP 200.
- `config.json` at pinned SHA: 78 × 200; 401 for the 3 Llama repos, Muse-Spark-Open and HCX-SEED-1.5B; 404 for Mistral-Large-3-675B-Instruct-2512.
- LICENSE/NOTICE at pinned SHA: 34 × 200 (Nemotron 3.5 Bolt LICENSE is 0 bytes).
- README.md downloads: 4 saved, then `ENOSPC` (local disk full; df showed 100% used, 181–210 MiB free fluctuating to 0). Several Bash calls and one Edit also failed with `ENOSPC` during this task.
- About 19 HF Unsloth-org searches.
- OpenRouter `GET /api/v1/models`: 471 models. No K-EXAONE / A.X K2 / Solar Open 2 / Kanana / Mi:dm / HyperCLOVA X endpoints; `upstage/solar-pro4` and `solar-mini4` (proprietary) are present.
- WebFetch OK:
  - Gemma 4 licence page; OpenMDW 1.1;
  - HF cards: K-EXAONE 2.0, Qwen3.8-27B, Qwen3.8-Flash-Next, Gemma 4 31B, A.X K2, Solar Open 2, Kanana-2-30B-A3B-2601, Kanana-2-3B, Mi:dm 2.0 Base, HCX SEED Think 32B, Granite 4.2 8B, FrogNano-4B;
  - mt.co.kr stage-2 article; artificialanalysis.ai open-source page; arXiv 2512.24572v2; docs.axolotl.ai.
- WebFetch failed:
  - horangi.ai (redirect chain to a JS-only page, no data);
  - aclanthology.org/2026.eacl-short.17 (`socket hang up`);
  - Llama 3.1 use policy (llama.meta.com → llama.com → developer.meta.com → dev.meta.ai, final **HTTP 404**), so the Llama AUP stays UNVERIFIED.
- WebSearch: 10 queries.
- Test: `.venv-check/bin/python -m pytest -q -p no:cacheprovider backend/tests/test_model_policy.py` → `16 passed in 0.04s`.
- The gpt-oss "harmony" chat-format remark is prior knowledge, not re-verified here (UNVERIFIED).

---

## Verification pass

Adversarial re-check by a second agent, 2026-10-19. Method: I re-read the cited repo lines in `/Users/seonjaekim/dev/Visable-genesis` @ 0713370 (worktree left clean) and re-ran the test. I re-queried the HF API for 15 repos; every SHA matched. I fetched 15 licence/policy files at the pinned SHAs into `scratchpad/verifier/models_v/`: 14 returned HTTP 200 and Muse `USE_POLICY.md` returned 401. The 12 that the original agent had also saved in `hf/lic2/` match it byte-for-byte (SHA-256). I also re-fetched the OpenRouter catalog and re-fetched or searched the cited web pages. Inline fixes are tagged `[corrected by verifier: …]` / `[added by verifier]`.

### Verdicts on the 15 key claims

| # | Claim (short) | Verdict | Primary evidence re-checked |
|---|---|---|---|
| 1 | Gemma 4 Apache-2.0, ungated; repo experiment still treats E4B/12B as gated | **confirmed** | [LIVE HF /api/models: gemma-4-12B-it sha 707f0a3b…, E4B ee0ef602…, `gated: False`, `license: apache-2.0`; E2B/26B/31B same in saved JSON] [WEB ai.google.dev/gemma/docs/gemma_4_license shows Apache 2.0, page now marked deprecated] [DOC README.md:41-42,171-173] [notebook cell 4 `is_gated=True`; cell 8 raises `RuntimeError` without `hf_token`]. Caveat: no Gemma 4 repo ships a LICENSE file |
| 2 | China-only prefix policy removes Qwen/DeepSeek/GLM/Kimi/MiniMax from KR/EN roles | **corrected** | [CODE model_policy.py:126-131,216-221; paradiso_backend.py:329-343,4846,5072] [TEST test_model_policy.py (ran: 16 passed in 0.04s)]. The policy text is as stated, but enforcement is a `/health` warning plus a default-chain test, not a runtime filter. Prefix matching on HF ids flags `Qwen/`, `moonshotai/` and not `deepseek-ai/`, `zai-org/`, `MiniMaxAI/` (OBSERVED via `model_family_is_chinese_only`). `chinese_model` is never consumed outside the policy module |
| 3 | EXAONE 4.0/4.0.1/4.5 are NC 1.2 and bar outputs for competing models | **confirmed** | [LIVE LICENSE @ EXAONE-4.5-33B 570aa4b1…, 4.0-1.2B 3abf2810…, and additionally 4.0.1-32B a6b0bd4b…: byte-identical (sha256 8c1762fb…), title "EXAONE AI Model License Agreement 1.2 - NC", §2.1(a) research/education only, §3.1 commercial ban + no use of Model/Derivatives/Output to build competing models] |
| 4 | K-EXAONE 2.0 Apache-2.0; K-EXAONE-236B needs agreement to distribute or make available commercially, plus "K-EXAONE" prefix | **confirmed** | [LIVE LICENSE+NOTICE @ fec0c8dd… = Apache 2.0, © 2026 LG AI Research] [LIVE LICENSE @ 61e6d578… §2.1-2.2]. Nuance: the prefix duty is triggered by distribution (§2.1) |
| 5 | HyperCLOVA X SEED: legal-services AUP ban, >10M MAU / competitor licence, "Powered by HyperCLOVA X" + prefix | **corrected** | [LIVE LICENSE @ 3c2b6338… §3.1, §4, Addendum A 1.d] confirm all three terms. Correction: the 10M MAU test is "as of the Model Release Date" (2025-12-29), not ongoing. The prefix applies to AI models trained on the Model/Outputs that are distributed or made available. NAVER may amend unilaterally (§2.1, §12) |
| 6 | Muse Spark Open: "Built with Muse Spark Open", unlicensed-practice ban, MaaS >$20M agreement | **confirmed** | [LIVE LICENSE.md @ 0fb02478… §2, §3, Exhibit A 1.4 (HTTP 200)]. The separate `USE_POLICY.md` returned HTTP 401 (gated), but Exhibit A in LICENSE.md is the incorporated policy. Derivatives include distilled models (§2) |
| 7 | Kanana Open License: own-service use OK, "Powered by Kanana", "Kanana" prefix; Kanana License adds 10M MAU | **confirmed** | [LIVE LICENSE @ 6a5d7889… §3.1(v), §4.1-4.2; @ 4a781fe5… §4.2]. Nuance: the 10M MAU is "as of Kanana Release Date" (header: July 17, 2025), and §4.1 requires a separate licence to resell API/SI/on-device access |
| 8 | Mistral Medium 3.5 no rights >$20M monthly revenue; MiniMax M2.7 NC; Qwen Community 1.0 MaaS/AWA licence | **confirmed** | [LIVE LICENSE @ 22b2b868… cond. 2; @ d494266a… title "NON-COMMERCIAL LICENSE", cond. 3; @ de4b8e4d… cond. 2 + definitions excluding domain assistants] |
| 9 | KCL: precedents roughly double MCQA (4 cited pairs); 2025-gen only | **corrected** | [WEB arxiv.org/html/2512.24572v2, re-fetched]: all 12 table rows in §7 match exactly. "Roughly doubles" overstates (×1.39-×2.2). Authors are University of Seoul / LBOX. The arXiv page names no venue, but an aclanthology search hit lists it as 2026.eacl-short.17 |
| 10 | Solar Open 2 the only open model with a Korean legal score; KBL 75.5 vs DSV4-Flash 72.8, KMMLU-Pro 78.4, CLIcK 90.7 | **corrected** | [WEB huggingface.co/upstage/Solar-Open2-250B, re-fetched] numbers exact. But the same table gives KBL for three other open models plus GPT-5.4 mini 75.3, and KCL covers open models, so "only" is wrong. KBL is not described on the card |
| 11 | A.X K2 highest vendor Korean scores (80.5/91.6/73.0); Qwen3.5 77.4 (LG) vs 78.4 (SKT) | **corrected** | [WEB A.X-K2 card; K-EXAONE-2.0 card, re-fetched]: numbers and the 77.4/78.4 disagreement confirmed. But LG's card gives DSV4-Pro the identical 80.5/91.6, and SKT's own card shows DSV4-Flash higher on KoBALT (75.3) |
| 12 | Stage 2 (2026-08-18): SKT 70.6, Upstage 69.9, LG 69.0 advanced; Motif 65.8 out; 40/35/25 | **corrected** | [WEB mt.co.kr 2026081812375747016 re-fetched: advancement, weighting, AAII 47 confirmed; **no team totals**] [WEB news.mtn.co.kr 2026082720102251703: totals and sub-scores released by MSIT 2026-08-27]. Scores right, date/source misattributed. wikidocs re-fetch: HTTP 403 |
| 13 | No Korean sovereign/Kanana/Mi:dm/HCX on OpenRouter; Gemma 4 26B/31B, gpt-oss, Nemotron, Granite 4.2 8B, Ministral 3 present with tools + json_schema | **corrected** | [LIVE GET openrouter.ai/api/v1/models, HTTP 200, 471 models, 2026-10-19]. The absence of Korean models is confirmed; only Upstage's proprietary `solar-pro4`, `solar-mini4`, `solar-pro-3` appear. Tools + structured_outputs hold for the paid slugs. The `:free` Gemma 4 26B/31B, Nemotron 3 Ultra and 3.5 Lightning slugs used in production lack `structured_outputs` |
| 14 | Unsloth repos for Gemma 4, Qwen3.5/3.6/3.8, gpt-oss, Ministral 3, Nemotron 3.5, GLM-5.3, none for Granite 4.2/Kanana/Mi:dm/A.X/Solar Open/K-EXAONE; Axolotl Gemma 4 2026/04, Qwen3.5 2026/03, Qwen3.6 2026/09 | **confirmed** | [LIVE HF /api/models?author=unsloth&search=… ×16: counts gemma-4 100, Qwen3.5 32, Qwen3.6 18, Qwen3.8 9, gpt-oss 15, Ministral-3 36, Nemotron-3.5 6, GLM-5.3 5, granite-4.2 0, kanana 0, Midm 0, A.X 0, Solar-Open 0, K-EXAONE 0. Unsloth has granite-4.1 and EXAONE-4.0-32B] [WEB docs.axolotl.ai: dates exact; Granite listed only as "Granite 4" 2025/10] |
| 15 | Guard flags vendor names, so attributions go in UI/docs; pattern misses Korean names | **confirmed** | [CODE guard.py:37-41,162-163]. Precision added: it also misses `minimax`, `glm` and bare "Llama" (needs a digit), so several mandated phrases would pass the guard unflagged |

### Omissions and thin spots, filled or not

Filled (with evidence, inline above):
- **NC VARCO** (named in the brief, absent from the notes): VARCO-VISION family is CC-BY-NC-4.0 and Llama-VARCO-8B is Llama 3.1. No 2026 NCSOFT releases. Disqualified for production [LIVE HF author=NCSOFT].
- **gpt-oss usage policy**: read; comply-with-law only.
- **Gemma Prohibited Use Policy**: read; it has an unlicensed-practice clause. Its applicability to Apache-2.0 Gemma 4 is unclear, so Gemma 4 should get the same "information, not legal advice" counsel review as Muse/HCX until resolved.
- **OpenRouter free-tier structured outputs**: production free endpoints lack `structured_outputs`. This bears on Artemis-style JSON routing if it stays hosted on `:free` slugs, and on the model_policy.py:110-111 comment.
- **MAU thresholds** (Kanana, HCX, Llama) are release-date snapshots, so their practical weight in rankings is lower than the notes imply.
- **KBL identity**: University of Seoul / LBox / Hanyang benchmark, EMNLP 2024 Findings (search summary, README-ONLY). Waymaker could run KBL itself as an independent check on Upstage's 75.5.
- **Kanana quantisations**: community GGUF/MLX (3B) and AWQ/GPTQ/GGUF (30B-A3B) exist; none official.
- **Gemma 4 has no LICENSE file in-repo**, matching the A.X K2 concern.

Not filled / still open:
- Llama 3.1 AUP text (redirect chain ends HTTP 404 at dev.meta.ai; repo `USE_POLICY.md` is gated). Llama 4 licence still unread.
- Gemma Terms of Use page not fetched, so the binding effect of the Gemma Prohibited Use Policy on Gemma 4 is unresolved.
- NVIDIA Nemotron Open Model License (3 Super/Nano) still unread.
- No independent Korean leaderboard (Horangi, KMMLU-Redux, KoBEST, Ko-IFEval) covering 2026 models was found; I did not retry Horangi.
- Not re-checked: the Artificial Analysis figures, the remaining VENDOR numbers for Kanana, Mi:dm and Granite, the stage-1 elimination reasons, and the VRAM estimates. The VRAM numbers remain INFERRED; I saw no arithmetic error in the §6 rule, which matches the per-model rows.
- "Final result expected in early 2027" (§2): not in the re-fetched mt.co.kr article; UNVERIFIED.

Net effect on the shortlists: no ranking changes. Gemma 4 stays the policy-aligned default. Two operational caveats added: hosted `:free` Gemma lacks schema-strict output, and Gemma's prohibited-use page is unresolved. Solar Open 2 and A.X K2 keep their Athena slots, but their "only/highest" framing is softened. The HyperCLOVA X disqualification stands on the competition clause and the legal-services AUP, not on MAU.
