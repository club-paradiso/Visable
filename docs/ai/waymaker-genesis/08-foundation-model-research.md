# 08 — Foundation model research: open-weight bases for Artemis, Athena and Hestia

Status: **RESEARCHED ONLY.** No model was downloaded, loaded, fine-tuned, served
or scored in Mission 001. Every capability number below was either reported by
the model's maker (or by a competitor comparing itself against it), or comes
from one independent study of 2025-generation models. The rankings in §9 are
ordered hypotheses for the Waymaker benchmark to test. None of them is a choice.
All Hugging Face (HF), OpenRouter and web data is a snapshot taken on
2026-10-19.

Source: [research-notes/models.md](research-notes/models.md), read in full,
including its Verification pass. Where the original text and the verifier
disagree, the verifier wins, and this document carries only the corrected
wording. Section references such as "models.md §5" point into that note.
Related documents:

- [research-notes/training-distill.md](research-notes/training-distill.md):
  role assumptions and distillation clauses;
- [09](09-training-and-distillation.md): training and distillation;
- [10](10-athena-and-hestia-strategy.md): Athena and Hestia strategy;
- [12](12-evaluation-methodology.md): metrics and gates;
- [13](13-artemis-experiment.md): the experiment that consumes §9.1;
- [14](14-hardware-and-cost-model.md): hardware and cost.

**Not legal advice.** The licence readings in §7 are an engineer's reading of
the texts at pinned revisions. The Korean licences in particular carry KCAB
arbitration and unilateral-amendment clauses, which counsel must review
(models.md §4).

Evidence tags: [CODE path:line], [TEST path (ran: …)], [DOC path],
[LIVE …, 2026-10-19], [WEB url, accessed 2026-10-19]. Status words: VERIFIED /
OBSERVED / README-ONLY / INFERRED / UNVERIFIED. Benchmark labels: see §3.3.

---

## 1. Summary

1. **Default, policy-aligned plan (INFERRED; models.md §9 Rec. 3).**
   - Artemis: `google/gemma-4-E4B-it`, or E2B if it scores within E4B's
     confidence interval.
   - Hestia: `google/gemma-4-31B-it` or `google/gemma-4-12B-it`, with LoRA.
   - Athena: keep the hosted Nemotron / gpt-oss / Gemma chain for now. Before
     committing GPUs, compare Solar Open 2, A.X K2 and K-EXAONE 2.0 on
     Waymaker evidence packs.
2. **The decision that changes the most shortlists belongs to the owner, not to
   a measurement.** The open question is whether the repo's China-origin
   model-route policy covers self-hosted open weights and Korean models built
   on Qwen. The policy as written is advisory: a `/health` warning and a test
   on the default chains, not a runtime filter. Until the owner rules, this
   document excludes Qwen, DeepSeek, GLM, Kimi and MiniMax from every
   Korean/English role (§4.2).
3. **No shortlisted 2026 model has an independent Korean measurement of any
   kind.** Among shortlisted models, only `openai/gpt-oss-120b` (2025) has an
   independent Korean legal number (KCL). Every Korean number for Gemma 4,
   Kanana 2, Granite 4.2, Solar Open 2, A.X K2 and K-EXAONE 2.0 is
   vendor-reported, and two vendors' tables contradict each other (§8).
4. **Licence blockers for a Korean immigration-information service** (§7):
   - non-commercial: EXAONE 4.x, MiniMax M2.7 and NCSOFT's VARCO-VISION;
   - a legal-services acceptable-use ban plus a competition clause:
     HyperCLOVA X SEED;
   - a revenue cap: Mistral Medium 3.5;
   - a third-party "making available" agreement: K-EXAONE-236B;
   - counsel review of an unlicensed-practice clause: Muse Spark Open and
     Llama 3.1 (the Llama text is unread). Google's Gemma Prohibited Use
     Policy has a similar clause, and whether it binds Apache-2.0 Gemma 4 is
     unresolved.
5. **Gemma 4 is Apache-2.0 and ungated** at the pinned SHAs. The repo's
   fine-tune scaffold still treats E4B and 12B as gated and stops without a
   token. The guard is stale and adds a failure mode for no benefit (§4.6).
6. **Benchmark v0 can select Artemis and test Athena's abstention. It cannot
   select a Hestia assistant on its own**, because it scores no free text
   ([12 §1](12-evaluation-methodology.md)). Hestia needs measurements that do
   not exist yet (§10.4).

## 2. Roles as used in this document

The names Artemis, Athena and Hestia appear nowhere in the repository or on
the owner's branch (training-distill.md §2.0 and its Verification pass,
item 4: VERIFIED absence by `git grep -i`). Both notes define the roles
themselves (INFERRED), and **they disagree about Hestia**:

| Role | models.md (used here) | training-distill.md §2.0 |
|---|---|---|
| Artemis | Compact model for status/subcode extraction, procedure classification, entity/date extraction, structured routing and multilingual intent. Cheap to fine-tune and serve | Small, fast specialist for routing, slot extraction, the Fast tier and Quick Answer wording; about 2-12B dense or 3-4B active |
| Athena | Advanced reasoning over a supplied `evidence_pack` | Grounded answer and synthesis model; about 12-31B, or teacher-class |
| Hestia | Professional assistant on a shared base with LoRA adapters | Self-hosted guardian and verifier: claim-to-evidence entailment, citation audit, PII-safe processing |

The shortlist in §9.3 is for the models.md reading. Under the
training-distill.md reading, the base-model constraints are similar
(self-hostable, permissive, policy-compatible), but what has to be measured
changes (§10.4). [10](10-athena-and-hestia-strategy.md) owns the
reconciliation.

Selection criteria per role (models.md §5):

| Role | Criteria |
|---|---|
| Artemis | About 9B total parameters or fewer (or a tiny active MoE); permissive licence; reliable JSON and tool output; good Korean tokenisation; QLoRA on a single T4/L4; Unsloth/TRL support; compatible with the model policy |
| Athena | Strong long-context reasoning; faithful to the evidence; reads Korean legal and administrative text; a permissive or clear commercial licence; hosting is feasible, either self-hosted or through an existing API |
| Hestia | Mid-size dense model, or a MoE with cheap active parameters, that LoRA-tunes on one 24-48 GB GPU; mature multi-LoRA serving; good Korean prose; the licence allows serving fine-tuned derivatives in-product; compatible with the model policy; ideally the same family as Artemis |

---

## 3. Method

### 3.1 Identity pinned by HF revision SHA

- **Revision SHAs.** Every model is identified by repo id plus revision SHA.
  The SHA is the repo HEAD returned by the public HF API (`/api/models/<id>`,
  no token) on 2026-10-19. Several repos changed in the 30 days before the
  snapshot, so a repo id alone does not identify the weights (models.md
  header). [LIVE HF API, 84 repos + 4 NVIDIA repos, HTTP 200] VERIFIED.
- **Parameters, context and gating.** Total parameters come from HF
  `safetensors.total`, and active parameters from the repo name or card.
  Context is `max_position_embeddings` from `config.json` fetched *at the
  pinned SHA*. "Gated" is the HF API flag.
  - `config.json`: 78 × HTTP 200.
  - HTTP 401 (gated): the three Llama repos, Muse Spark Open and HCX SEED
    1.5B.
  - HTTP 404: `Mistral-Large-3-675B-Instruct-2512`.

  (models.md §3a, §10.)
- **Re-check.** The verifier re-queried 15 repos, and every SHA matched
  (models.md Verification pass). VERIFIED.
- **Downstream use.** `experiments/waymaker-ai/tests/test_training_configs.py`
  fails if an Artemis config's base-model SHA differs from the one in
  models.md ([13 §4](13-artemis-experiment.md)). This document copies the SHAs
  from models.md mechanically and does not restate them by hand.

### 3.2 Licence files read at the pinned SHA

- **Fetch method.** Licence and notice files were fetched as
  `huggingface.co/<repo>/resolve/<sha>/<file>`: 34 × HTTP 200. Nemotron 3.5
  Bolt's LICENSE was 0 bytes (OBSERVED) (models.md §4, §10).
- **Verifier pass.** The verifier fetched 15 licence and policy files at the
  pinned SHAs. Fourteen returned HTTP 200, and Muse's `USE_POLICY.md` returned
  HTTP 401. The 12 files both agents saved are byte-identical by SHA-256
  (models.md Verification pass). VERIFIED.
- **Where the text is not in the repo:**
  - **Gemma 4.** None of the five Gemma 4 repos ships a LICENSE file. "Apache-2.0"
    rests on HF `cardData.license` plus Google's licence page, which shows
    Apache 2.0 text but is now marked deprecated and points to gemma.ai
    [WEB https://ai.google.dev/gemma/docs/gemma_4_license]. Archive that page
    beside the SHA.
  - **A.X K2.** No LICENSE file either. Apache-2.0 is asserted only by
    metadata and the card (absence VERIFIED; terms README-ONLY).
  - **VAETKI.** The card says MIT, but the repo ships an Apache-2.0 text
    (VERIFIED metadata conflict).
- **Not read:**
  - the NVIDIA Nemotron Open Model License (Nemotron 3 Super/Nano);
  - the Llama 3.1 acceptable-use policy (the redirect chain ended in HTTP 404);
  - the Llama 4 licence (gated);
  - Google's Gemma Terms of Use page.

  All four stay UNVERIFIED (§11).

### 3.3 Vendor-reported versus independent numbers

| Label | Meaning (models.md header) |
|---|---|
| **VENDOR-REPORTED** | From a model card or report by the model's maker, **or by a competitor comparing itself against that model**. A competitor's table is still a party to the comparison |
| **INDEPENDENT** | A third party with no model in the comparison ran the evaluation |

An "independent" leaderboard that republishes a vendor's own figure counts as
vendor-reported. BenchLM's KMMLU-Pro figure for K-EXAONE equals LG's card
value (models.md §7).

### 3.4 Operations data

| Item | Source | Status |
|---|---|---|
| Hosted availability and endpoint features | OpenRouter catalog (`GET /api/v1/models`, 471 models) | OBSERVED |
| Unsloth support | About 19 HF searches for `author=unsloth` | VERIFIED |
| Axolotl support | Axolotl changelog [WEB https://docs.axolotl.ai/] | VERIFIED |
| Native loading (no `trust_remote_code`) | HF `custom_code` tag | INFERRED |
| VRAM | Arithmetic rules in models.md §6, never measured | INFERRED |

On OpenRouter, the verifier found a distinction that matters: the **paid**
slugs list `structured_outputs`, while the `:free` slugs production uses mostly
do not (§4.5).

### 3.5 The ENOSPC caveat

Most model-card content was not saved as files, for two reasons:

- **The disk filled during the research.** Benchmarks, tool-call parsers and
  release dates reached the notes through WebFetch summaries of HF pages, not
  raw file reads. Raw `README.md` files were saved for only four repos:
  Qwen3.5-4B, Qwen3.5-9B, Qwen3.6-27B and Qwen3.6-35B-A3B, whose tables were
  parsed locally.
- **Further README downloads failed with `ENOSPC`.** `df` showed 100% used,
  with free space fluctuating between 181-210 MiB and 0. Several Bash calls
  and one Edit failed the same way (models.md §8, §10).

**Consequence: every VENDOR-REPORTED number in this document is
README-ONLY-grade evidence**, except the Qwen tables above, and the Solar
Open 2, A.X K2 and K-EXAONE 2.0 cards, which the verifier re-fetched and
re-checked number by number. Licence texts are not affected. They were
fetched as files at the pinned SHAs (§3.2).

### 3.6 Re-checks made for this document (2026-10-20, current main `fc896c2`)

The research audited commit `0713370`. On 2026-10-20 I checked that the code
it cites still holds:

- `git diff --stat 0713370 fc896c2 -- backend/services/model_policy.py backend/services/knowledge/guard.py backend/tests/test_model_policy.py backend/paradiso_backend.py experiments/waymaker-gemma4-finetune`
  printed nothing, so every cited file is unchanged on current main.
- I re-read the cited lines in `model_policy.py`, `paradiso_backend.py`,
  `guard.py` and the fine-tune README at `fc896c2`. The only line shift is
  that the guard's provider pattern spans `guard.py:37-41`, which the
  verifier had already noted.
- `PYTHONDONTWRITEBYTECODE=1 <python3.11-venv>/bin/python -m pytest -q -p no:cacheprovider backend/tests/test_model_policy.py`
  returned `16 passed in 0.13s`.
- No HF, OpenRouter or web request was made for this document. Every external
  fact is as models.md recorded it on 2026-10-19.

---

## 4. Repository constraints on model choice

### 4.1 What production routes to today (hosted, OpenRouter)

| Route | Model id(s) | Evidence |
|---|---|---|
| Router / translation | `google/gemma-4-31b-it:free` | [CODE backend/services/model_policy.py:23-24] |
| Basic final-answer chain | `nvidia/nemotron-3-ultra-550b-a55b:free` → `google/gemma-4-31b-it:free` → `nvidia/nemotron-3-super-120b-a12b:free` → `thinkingmachines/inkling:free` | [CODE model_policy.py:31-37] |
| Fast tier | `google/gemma-4-26b-a4b-it:free` first | [CODE model_policy.py:99-105] |
| Enforcement (structured) | `google/gemma-4-26b-a4b-it:free`, `nvidia/nemotron-3-super-120b-a12b:free` | [CODE model_policy.py:112-116] |
| Verifier | `nvidia/nemotron-3-super-120b-a12b:free` | [CODE model_policy.py:118] |
| Chinese-language route | `minimax/minimax-m3` (declared only; no backend module outside model_policy.py and its test reads `chinese_model`) | [CODE model_policy.py:120-124] VERIFIED |

All rows are VERIFIED (models.md §1, re-read at `fc896c2`). The owner's
branch `fix/waymaker-qa-2026-10-16` replaces `thinkingmachines/inkling:free`,
which returned 403 `model_access_denied`, with
`google/gemma-4-26b-a4b-it:free` in the final chain. That increases reliance
on Gemma 4 and changes no conclusion here (models.md §1, VERIFIED by
`git show`). A stale comment says "verifier: gpt-oss", while the code's
verifier is Nemotron 3 Super [CODE backend/paradiso_backend.py:163-166 vs
model_policy.py:118] VERIFIED.

**Implication (INFERRED, models.md §1).** The policy-compatible open-weight
families already in production are Gemma 4, NVIDIA Nemotron 3/3.5 and OpenAI
gpt-oss. Choosing Artemis and Hestia from these families is the shortest
path. The Korean sovereign-programme models are the policy-neutral
alternative with the strongest Korean claims.

### 4.2 The China-origin model-route policy and its consequence

**What the policy says.**
`CHINESE_ONLY_MODEL_PREFIXES = ("deepseek/", "qwen/", "moonshotai/", "z-ai/", "minimax/", "inclusionai/")`
[CODE backend/services/model_policy.py:126-131]. The module docstring states
that China-origin families are reserved for Chinese-language tasks only
[CODE model_policy.py:9]. The policy notes repeat this for the DeepSeek,
Qwen, Kimi, Z.ai, MiniMax and InclusionAI families [CODE model_policy.py:220].
VERIFIED.

**How it is enforced (verifier correction, models.md §0 item 3 and
Verification pass claim 2).** The policy is advisory, not a runtime filter:

| Mechanism | What it does | Evidence |
|---|---|---|
| `_validate_model_candidates` | Emits a `/health` warning `MODEL_CANDIDATES_CHINESE_MODEL_RESTRICTED_TO_CHINESE` when a configured candidate matches a prefix | [CODE backend/paradiso_backend.py:329-343, 4846, 5072] |
| Tests | Assert that the *default* chains contain no prefixed family | [TEST backend/tests/test_model_policy.py:54-61,112-113 (ran: 16 passed)] |
| Prefix match | A lower-cased prefix test on OpenRouter-style ids. On HF repo ids it flags `Qwen/…` and `moonshotai/…`, but not `deepseek-ai/…`, `zai-org/…` or `MiniMaxAI/…` | [LIVE `model_family_is_chinese_only()` in `.venv-check`, 2026-10-19] OBSERVED |

**Where the repo is inconsistent with its own policy:**

- The fine-tune experiment's default smoke model is `Qwen/Qwen3-1.7B`
  [DOC experiments/waymaker-gemma4-finetune/README.md:36-42].
- The optional Ollama fallback defaults to `qwen3:8b`. It is off by default
  [CODE backend/paradiso_backend.py:257-259].

**Consequence for this document.** The policy text states the owner's intent
for hosted routes. **Whether it also covers self-hosted open weights is an
owner decision that the code does not settle** (models.md §0 item 3, §9
Rec. 2). Until the owner rules, the following are treated as
**POLICY-BLOCKED** for Korean/English Waymaker roles: Qwen3.5/3.6/3.8,
DeepSeek V4/V4.1, GLM-5.3, Kimi K3 and MiniMax M3. That has a measurable
cost on paper, all VENDOR-REPORTED:

| Role | Strongest policy-blocked option (models.md §5) | What it would have offered |
|---|---|---|
| Artemis | `Qwen/Qwen3.5-4B` / `Qwen/Qwen3.5-9B` | BFCL-V4 50.3 / 66.1, TAU2 79.9 / 79.1, MMMLU 76.1 / 81.2, INCLUDE 71.0 / 75.6; Unsloth and Axolotl support; Apache-2.0 |
| Hestia | `Qwen/Qwen3.6-27B` / `Qwen/Qwen3.8-27B` | Apache-2.0, Unsloth, MTP; 7.7M 30-day downloads for 3.8-27B |
| Athena | DeepSeek-V4/V4.1-Flash (MIT) | KMMLU-Pro 78.8/78.9 and KoBALT 75.3 in competitors' tables. On the independent general index of the Artificial Analysis page: GLM-5.3 45, Kimi K3 44 |

**The owner must rule on three questions:**

1. Does the policy cover self-hosted open weights, or only hosted
   Chinese-provider routes?
2. Does it cover Korean or other models fine-tuned from a Qwen checkpoint?
   Examples: `skt/A.X-4.0-Light` declares "Built with Qwen 2.5", and
   `microsoft/FrogNano-4B-2609` is a Qwen3.5-4B fine-tune.
3. Does it cover models that reuse only an architecture? Kanana-2-3B uses the
   Qwen3 architecture and is trained from scratch per its card;
   Kanana-2-30B-A3B uses the DeepseekV3 architecture.

Question 1 moves Qwen in or out of every shortlist. Questions 2 and 3 decide
A.X 4.0 Light and the Kanana pair (INFERRED).

### 4.3 Gemma's declared default role (added by this document)

The same policy module describes Gemma's *default* role as translation,
language detection and low-risk routing [CODE model_policy.py:5, :217]
VERIFIED. The same module already places Gemma 4 31B second in the Basic
final-answer chain and Gemma 4 26B-A4B first in the Fast tier (§4.1). A
Gemma-based Hestia or Athena-lite therefore matches what the code already
does, not what the note says. That is a policy-text update for the owner to
approve, not a technical obstacle (INFERRED).

### 4.4 The answer guard and licence-mandated attribution

The answer guard flags provider and model names in generated text as CRITICAL
`provider_model_leak` [CODE backend/services/knowledge/guard.py:37-41,
162-163] VERIFIED.

**What the pattern does not cover:** `exaone`, `kanana`, `solar`,
`hyperclova`, `a.x`, `midm`, `granite`, `phi`, `muse`, `minimax`,
`glm`/`zhipu`/`z.ai`, and bare "Llama" (the pattern needs a digit). So
"Built with Llama", "Built with MiniMax M3", "Powered by Kanana" and
"Built with Solar" would pass unflagged, while "Gemma" or "Mistral" would be
flagged (models.md §1, Verification pass claim 15).

**Rule.** Put licence-mandated attributions in a static about/licence page or
in the UI chrome. They never belong in model answers. The reason is that the
licences ask for display there; the guard would not reliably catch them.

### 4.5 Structured output on the free endpoints

On the live OpenRouter catalog [LIVE 2026-10-19, 471 models] OBSERVED:

| Endpoint | Lists |
|---|---|
| `google/gemma-4-31b-it:free`, `google/gemma-4-26b-a4b-it:free` | `response_format` and tools, **not** `structured_outputs` |
| `nvidia/nemotron-3-ultra-550b-a55b:free`, `nvidia/nemotron-3.5-lightning:free` | tools only |
| `nvidia/nemotron-3-super-120b-a12b:free` | `structured_outputs` (the only production free endpoint that does) |
| Paid gpt-oss-20b/120b, granite-4.2-8b, ministral-3b/8b/14b-2512, meta/muse-spark-open, nemotron-3.5-super-vl | tools and `structured_outputs` |

This contradicts the comment at [CODE model_policy.py:110-111], which says
both enforcement models are free endpoints with structured-output support.
It matters for Artemis: if Artemis stays hosted on `:free` Gemma slugs, its
schema-strict JSON is not guaranteed by the endpoint, so
`model.structured_output_valid_rate` (gate SG-8) has to be measured, not
assumed (models.md §1, §3b, Verification pass claim 13).

### 4.6 The stale gating assumption in the fine-tune scaffold

HF reports `license: apache-2.0` and `gated: False` for `google/gemma-4-E4B-it`
and `google/gemma-4-12B-it`. The repo's experiment still treats both as gated:

- the README marks them as needing a token
  [DOC experiments/waymaker-gemma4-finetune/README.md:41-42,171-173];
- notebook cell 4 sets them gated in `MODEL_PRESETS`;
- notebook cell 8 raises if no `HF_TOKEN` is set.

The guard is stale and adds a failure mode for no benefit (models.md §0
item 2; Verification pass claim 1: confirmed). [13](13-artemis-experiment.md)
uses no token and pins `revision=`.

---

## 5. Landscape snapshot (2026-10-19)

The landscape moved a great deal after mid-2026. Rows are condensed from
models.md §2 [LIVE HF API `/api/models?author=<org>&sort=createdAt`]
VERIFIED unless noted.

| Family | Newest open-weight releases | Licence note |
|---|---|---|
| Gemma (Google) | Gemma 4 E2B/E4B (createdAt 2026-03-02; public launch reported 2026-04-02), 26B-A4B and 31B (2026-03-11), 12B "Unified" (2026-05-23); official QAT q4_0 GGUF and w4a16 | Apache-2.0, ungated |
| Qwen (Alibaba) | Qwen3.5 0.8B-397B-A17B (2026-02), Qwen3.6-27B/35B-A3B (2026-04), Qwen3.8-27B (2026-08-05), Qwen3.8-Flash-Next (2026-08-24), Qwen3.8-2.4T-A95B (2026-08-08) | 27B and below, and Qwen3.6, are Apache-2.0. Flash-Next: Qwen Community License 1.0. 2.4T: Qwen3.8-Max License. Policy-blocked (§4.2) |
| Meta | Nothing new on `meta-llama` since Llama 4 (2025-04); no Llama 5. `meta-models/Muse-Spark-Open-816B-A42B` (created 2026-09-15, announced 2026-10-15) | Muse Model License; gated (manual) |
| Mistral | Ministral 3 3B/8B/14B (2512), Large 3 675B (2512), Small 4 119B MoE (2603), Medium 3.5 128B (2026-03-31) | Apache-2.0, except Medium 3.5 (Modified MIT with a revenue cap) |
| OpenAI | gpt-oss-20b/120b (2025-08), gpt-oss-safeguard (2025-09); no newer open LLM | Apache-2.0 |
| IBM Granite | Granite 4.2 3B/8B/30B dense (2026-08-07), with official GGUF/MLX/FP8/NVFP4; granite-switch-4.1 (2026-10-14) | Apache-2.0; Korean in the language list |
| NVIDIA Nemotron | Nemotron 3 Nano/Super/Ultra (Dec 2025-Jun 2026); 3.5 Lightning 30B-A3B (08), Super-VL 120B-A12B and Bolt 74B-A9B (10) | OpenMDW-1.1 (3 Ultra, 3.5), or the Nemotron Open Model License (3 Super/Nano, unread) |
| Microsoft Phi | Last LLM Phi-4-reasoning-vision-15B (2026-01). `FrogNano-4B-2609` is a Qwen3.5-4B fine-tune, not Phi | The line looks dormant (INFERRED) |
| DeepSeek, GLM, Kimi, MiniMax | V4/V4.1-Flash; GLM-5.3 / 5.3-Flash; Kimi K3 2.78T; MiniMax M3 427B, M2.7 | Policy-blocked (§4.2). M2.7 is also non-commercial |
| LG EXAONE | EXAONE 4.0/4.0.1 (2025-07), K-EXAONE-236B-A23B (2025-12-26), EXAONE 4.5-33B (2026-04-04), **K-EXAONE 2.0 750B-A37B (2026-07-29)** | 4.x non-commercial; 236B custom; **2.0 Apache-2.0** |
| SKT A.X | A.X 4.0 / 4.0-Light (Qwen2.5-based), A.X K1 519B (2025-12-29), **A.X K2 688B-A33B (2026-07-28)** | Apache-2.0 (K2: no LICENSE file) |
| Upstage Solar | Solar-Open-100B (2025-12-10), **Solar-Open2-250B (2026-07-22)** | Upstage Solar License (Apache plus naming duties) |
| Kakao Kanana | kanana-2-30b-a3b (2601 refresh 2026-01-14), kanana-2-3b and 1.3b (2026-07-24) | Kanana Open License / Kanana License |
| KT Mi:dm | Mi:dm 2.0 Base 11.5B and Mini 2.3B (2025-07-03); nothing newer | MIT |
| Naver HyperCLOVA X SEED | 0.5B/1.5B, Think-14B, Think-32B, Omni-8B; no 2026 releases | Custom licence |
| NC AI / NCSOFT | VAETKI 112B, 20B-A2B, 7B-A1B (2025-12). NCSOFT's VARCO-VISION family is `cc-by-nc-4.0`; `Llama-VARCO-8B-Instruct` is Llama 3.1; no 2026 NCSOFT releases | VAETKI: licence metadata conflict. VARCO: non-commercial (HF tags only) |
| Others (KR) | Trillion Labs Tri-21B-Think (2026-02), Gravity-30B-A5B (2026-09); Motif-2-12.7B (2025-10), Motif-3 315B (2026-08) | Apache-2.0 / MIT |

**Korean sovereign programme (독자 AI 파운데이션 모델).** The corrected
reading in models.md §2:

- **Stage 2.** The advancing teams were announced on 2026-08-18, under a
  benchmark 40 / expert 35 / user 25 weighting. The per-team totals were
  released by MSIT only on **2026-08-27**, after Motif objected:

  | Team | Total | Benchmark | Expert | User | Result |
  |---|---|---|---|---|---|
  | SKT | 70.6 | 22.2 | 29.3 | 19.1 | advanced |
  | Upstage | 69.9 | 22.7 | 29.1 | 18.1 | advanced |
  | LG | 69.0 | 20.6 | 29.5 | 18.9 | advanced |
  | Motif | 65.8 | 24.6 | 27.1 | 14.1 | eliminated |

  [WEB https://news.mtn.co.kr/news-detail/2026082720102251703] VERIFIED.
- **Motif** had the highest benchmark sub-score and lost on user evaluation.
- **"Final result in early 2027"** is not in the re-fetched mt.co.kr article:
  UNVERIFIED.
- **Motif's AAII score of 47** conflicts with the Artificial Analysis
  open-weights page, whose maximum is 46: UNVERIFIED.
- **Programme results are not a capability measurement for Waymaker's
  tasks.** They are a maturity and continuity signal for the three surviving
  vendors (INFERRED).

---

## 6. Candidate matrix

### 6.1 Identity, architecture and licence (pinned)

Copied mechanically from models.md §3a. Repo ids and SHAs are exactly as
recorded there and re-checked by the verifier. The last column is this
document's classification from §4.2 and §7.

- Rows are VERIFIED unless a cell says otherwise.
- "Ctx" is `max_position_embeddings` at the pinned SHA. "401" means the
  config is gated.
- For Gemma 4, "verified text" means HF `cardData` plus Google's licence page,
  because no Gemma 4 repo ships a LICENSE file (§3.2).
- "eligible" in the last column means no licence or policy blocker was found.
  It does not mean suitable, and it does not replace the counsel review in
  §7.2, which Gemma 4 still needs.

| Repo id @ revision SHA | Arch | Total / active | Ctx (config) | Licence (verified text) | Gated | 30-day DL | Waymaker status (this doc) |
|---|---|---|---|---|---|---|---|
| `google/gemma-4-E2B-it` @ 3e22461f65e89153144f8adb70e3b8c2cc9845a7 | dense, PLE, text+img+audio | 5.12B (2.3B effective) | 131,072 | Apache-2.0 | no | 2.7M | eligible |
| `google/gemma-4-E4B-it` @ ee0ef6023621cff504d758262d4e04895a5af4a2 | dense, PLE, text+img+audio | 8.00B (4.5B effective) | 131,072 | Apache-2.0 | no | 4.2M | eligible |
| `google/gemma-4-12B-it` @ 707f0a3b8a3c7ad586ed01e27eafbad8a27dd0f7 | dense "Unified" (encoder-free) | 11.96B | 262,144 | Apache-2.0 | no | 1.7M | eligible |
| `google/gemma-4-26B-A4B-it` @ 4d7ae4984b7db7de8f8457170b3f1a419ee76d52 | MoE 128e top-8 | 25.8B / 3.8B | 262,144 | Apache-2.0 | no | 10.5M | eligible |
| `google/gemma-4-31B-it` @ 842da3794eaa0b77d5f08bae87a17459d91ff475 | dense | 31.3B | 262,144 | Apache-2.0 | no | 9.0M | eligible |
| `Qwen/Qwen3.5-4B` @ 851bf6e806efd8d0a36b00ddf55e13ccb7b8cd0a | dense hybrid (GatedDeltaNet 3:1), VLM | 4.66B | 262,144 | Apache-2.0 | no | 7.9M | POLICY-BLOCKED (owner) |
| `Qwen/Qwen3.5-9B` @ c202236235762e1c871ad0ccb60c8ee5ba337b9a | dense hybrid, VLM | 9.65B | 262,144 | Apache-2.0 | no | 7.8M | POLICY-BLOCKED (owner) |
| `Qwen/Qwen3.6-35B-A3B` @ 995ad96eacd98c81ed38be0c5b274b04031597b0 | MoE 256e top-8, hybrid | 36.0B / ~3B | 262,144 | Apache-2.0 | no | 3.7M | POLICY-BLOCKED (owner) |
| `Qwen/Qwen3.8-27B` @ 1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0 | dense hybrid, VLM | 27.8B | 262,144 (→1M YaRN) | Apache-2.0 (tag; LICENSE file 11.5 KB) | no | 7.7M | POLICY-BLOCKED (owner) |
| `Qwen/Qwen3.8-Flash-Next` @ de4b8e4d43b917e7706784d8bb445c9af86a3540 | MoE 512e top-10+1 | 180B stored (125B + 51B n-gram + 4B MTP) / 6B | 262,144 | Qwen Community License 1.0 | no | 2.5M | POLICY-BLOCKED (owner); MaaS/AWA terms |
| `openai/gpt-oss-20b` @ 6cee5e81ee83917806bbde320786a8fb61efebee | MoE 32e top-4, MXFP4 | 20.9B / ~3.6B (UNVERIFIED active) | 131,072 | Apache-2.0 | no | 5.9M | eligible |
| `openai/gpt-oss-120b` @ b5c939de8f754692c1647ca79fbf85e8c1e70f8a | MoE 128e top-4, MXFP4 | 116.8B / ~5.1B (UNVERIFIED active) | 131,072 | Apache-2.0 | no | 3.2M | eligible |
| `ibm-granite/granite-4.2-3b` @ e459acceac81e5fe67c07d9cfc72329a332e7eb1 | dense | 3.66B | 131,072 | Apache-2.0 | no | 40k | eligible |
| `ibm-granite/granite-4.2-8b` @ f8de16cdcdbc6c779ca517604e050d82cc119e44 | dense | 8.79B | 131,072 (card: 512K ext.) | Apache-2.0 | no | 91k | eligible |
| `ibm-granite/granite-4.2-30b` @ 9e668ce1c538387ef24d3644e9b0606647762636 | dense | 29.3B | 131,072 | Apache-2.0 | no | 37k | eligible |
| `mistralai/Ministral-3-8B-Instruct-2512` @ 5b26027e7b19eeb4b7352e1fed3926375dd2cb4d | dense VLM, FP8 weights | 8.92B | 262,144 | Apache-2.0 | no | 119k | eligible |
| `mistralai/Ministral-3-14B-Instruct-2512` @ 29439f81c2be264d8d393273f99e7db9c0961120 | dense VLM, FP8 | 13.95B | 262,144 | Apache-2.0 | no | 119k | eligible |
| `mistralai/Mistral-Small-4-119B-2603` @ a11f36bebf709121056b1dbcc943d1c6afbe494d | MoE 128e top-4 | 119.4B | 1,048,576 | Apache-2.0 | no | 72k | eligible (not shortlisted) |
| `mistralai/Mistral-Medium-3.5-128B` @ 22b2b868a15677cfa6061277ed2f653d1349a9ab | dense | 127.7B | 262,144 | Modified MIT (revenue cap) | no | 75k | LICENCE-BLOCKED (revenue cap) |
| `microsoft/Phi-4-mini-instruct` @ cfbefacb99257ffa30c83adab238a50856ac3083 | dense | 3.84B | 131,072 | MIT | no | 371k | eligible; weakest KCL |
| `meta-llama/Llama-3.1-8B-Instruct` @ 0e9e39f249a16976918f6564b8830bc894c89659 | dense | 8.03B | 401 (gated) | Llama 3.1 Community | manual | 5.6M | CAUTION (AUP unread; attribution) |
| `meta-models/Muse-Spark-Open-816B-A42B` @ 0fb02478b02565b2ce7fc57e6051c91172774ac9 | MoE VLM | 822B / 42B | 401 (gated); 1M reported | Muse Model License | manual | 1.8k | CAUTION (counsel; attribution) |
| `nvidia/NVIDIA-Nemotron-3.5-Lightning-30B-A3B-BF16` @ a9904d24bcc1d289a1950fa9d2b978c47cf903b9 | hybrid MoE | 31.6B / 3B | n/a (not fetched) | OpenMDW-1.1 | no | — | eligible |
| `nvidia/NVIDIA-Nemotron-3.5-Super-VL-120B-A12B-BF16` @ 1f8953f7f0935358e3605150d22bc15df062061c | hybrid Mamba/MoE VLM, custom code | 124.5B / 12B | 1,048,576 | OpenMDW-1.1 | no | 12k | eligible |
| `nvidia/NVIDIA-Nemotron-3-Ultra-550B-A55B-NVFP4` @ 02462641f13d3af838b904f48195b9bb8a1e4ebc | hybrid MoE | 550B / 55B | n/a | OpenMDW-1.1 (ko listed) | no | — | eligible |
| `nvidia/NVIDIA-Nemotron-3-Super-120B-A12B-FP8` @ 744b1880a37996c5d56bf454ae164dfd74d77c4e | hybrid MoE | 123.6B / 12B | n/a | NVIDIA Nemotron Open Model License (not read) | no | — | licence text unread |
| `kakaocorp/kanana-2-3b-instruct` @ 6a5d7889964c4c590299d16e309eabab1f73f8a9 | dense (Qwen3 arch, from scratch per card) | 3.51B | 32,768 | Kanana Open License | no | 4.5k | eligible; attribution + naming |
| `kakaocorp/kanana-2-1.3b-instruct` @ bf4786aa2a1908adce942d53976270132732f720 | dense, custom code | 1.29B | 32,768 | Kanana Open License | no | 3.5k | eligible; attribution + naming |
| `kakaocorp/kanana-2-30b-a3b-instruct-2601` @ 4a781fe5027da4af8d8208cb21bc5108b913bb62 | MoE (DeepseekV3 arch, MLA) 128e top-6+2 | 30.7B / 3B | 32,768 (128K YaRN) | Kanana License (+10M MAU) | no | 1.5k | eligible; attribution + naming |
| `K-intelligence/Midm-2.0-Mini-Instruct` @ 383eb221c52a32278f1985257b264ade8d982e60 | dense (Llama arch) | 2.31B | 32,768 | MIT | no | 22k | eligible |
| `K-intelligence/Midm-2.0-Base-Instruct` @ 35479c5fc9a18a5db7cc6dbadcf1db68db7beab0 | dense (Llama arch, depth-up-scaled) | 11.5B | 32,768 | MIT | no | 82k | eligible |
| `skt/A.X-4.0-Light` @ ba21c20ea1b31ded1ec3e2fb432335077dc4be98 | dense (Qwen2.5-based) | 7.26B | 16,384 | Apache-2.0 + "Built with Qwen 2.5" note | no | 73k | OPEN POLICY QUESTION (Qwen2.5-based) |
| `skt/A.X-K2` @ 2287ca456927eed33b899c404c0b2ffaf17aa09f | MoE 256e top-8+1, MLA + sparse gated attn | 688B / 33B | 262,144 | Apache-2.0 (metadata/card; no LICENSE file in repo) | no | 15k | eligible; no LICENSE file |
| `LGAI-EXAONE/K-EXAONE-2.0-750B-A37B` @ fec0c8dd25fdd20ffd09869d5af5277966d5523d | MoE 256e top-8+1 | 749B / 37B | 262,144 | Apache-2.0 (LICENSE + NOTICE read) | no | 3.4k | eligible |
| `LGAI-EXAONE/K-EXAONE-236B-A23B` @ 61e6d578eb102b578e5704e2916ac841df9eca0a | MoE 128e top-8 | 237B / 23B | 262,144 | K-EXAONE AI Model License | no | 14k | LICENCE-BLOCKED (§2.2, needs LG agreement) |
| `LGAI-EXAONE/EXAONE-4.5-33B` @ 570aa4b15a4f45ba1133072b45f50198f6e3b4fd | dense VLM | 34.4B | 262,144 | EXAONE 1.2-**NC** | no | 45k | LICENCE-BLOCKED (NC) |
| `LGAI-EXAONE/EXAONE-4.0-1.2B` @ 3abf2810673c7c0778df64a73c2d52eab32d91c4 | dense | 1.28B | 65,536 | EXAONE 1.2-**NC** | no | 17k | LICENCE-BLOCKED (NC) |
| `upstage/Solar-Open2-250B` @ 9190fbe63a2ad8e17fc766ccceb36de7c66f004b | MoE 320e top-8+1, hybrid linear attn, NoPE | 250B / 15B | 1,048,576 | Upstage Solar License | no | 7.2k | eligible; naming if a derivative is made available |
| `upstage/Solar-Open-100B` @ 1f591439b14055004d1a5d1a975608953a022fea | MoE 128e top-8 | 102.7B / UNVERIFIED | 131,072 | Upstage Solar License | no | 9.4k | eligible; naming if a derivative is made available |
| `naver-hyperclovax/HyperCLOVAX-SEED-Think-32B` @ 3c2b6338613c4e5ede30788d868363125a262934 | dense VLM | 33.3B | 131,072 | HyperCLOVA X SEED 32B Think | no | 13k | LICENCE-BLOCKED (AUP + competition) |
| `naver-hyperclovax/HyperCLOVAX-SEED-Text-Instruct-1.5B` @ 0728a47d632019a8da5f53b663db1c175dc04115 | dense | 1.59B | 401 (gated auto) | HyperCLOVA X SEED | auto | 1.2k | LICENCE-BLOCKED (AUP + competition) |
| `nc-ai-consortium/VAETKI-20B-A2B` @ 91e960232f8561d300f5a3b2edfd8a726f1569d2 | MoE 128e top-8, custom code | 19.6B / ~2B | 32,768 | MIT tag / Apache text | no | 288 | licence metadata conflict |
| `trillionlabs/Gravity-30B-A5B-Preview` @ 4aec2238fef2c7e8adb8bed5f2b7a4198a265163 | MoE 64e top-8, custom code | 29.6B / 5B | 131,072 | Apache-2.0 | no | 397 | eligible (preview; not shortlisted) |
| `Motif-Technologies/Motif-3` @ 2ed2ed5cfabffa10fdabb2fc0d0288f8e6de893a | MoE 384e, custom code | 314.8B / UNVERIFIED | 262,144 | MIT | no | 2.2k | eligible licence; card benchmarks not fetched |

Policy-blocked large reference points, pinned for completeness (models.md
§3a):

- `deepseek-ai/DeepSeek-V4-Flash` @ 60d8d70770c6776ff598c94bb586a859a38244f1 (MIT, 291B, 1M ctx)
- `deepseek-ai/DeepSeek-V4.1-Flash` @ 314113f8a7dadb388215396ba5fbee2c610a04d6 (MIT, 763B)
- `zai-org/GLM-5.3-Flash` @ 46a050bec13002ad29ee795c16e61cf4fa3c4a9c (MIT, 321B)
- `zai-org/GLM-5.3` @ ba32f8c19c8738e2c57c71798c601d477a7bf844 (GLM-5.3 License, 753B)
- `moonshotai/Kimi-K3` @ f831ab66814297da540d832a5235f8e904f29d06 (Kimi K3 License, 2.78T)
- `MiniMaxAI/MiniMax-M3` @ f0e1c1e04d40177e4673a22097036854f536e9c0 (MiniMax Community, 427B)
- `Qwen/Qwen3.6-27B` @ 6a9e13bd6fc8f0983b9b99948120bc37f49c13e9 (Apache)
- `Qwen/Qwen3.5-122B-A10B` @ dc4d348443bc740c68e2d77492492c11606384d5 (Apache)

### 6.2 Capability and operations (condensed)

From models.md §3b, with the verifier's corrections applied. Abbreviations:

- **TC**: tool or function calling.
- **SO**: JSON-schema structured output.
- **"OR schema"**: OpenRouter lists `structured_outputs` for the **paid** slug
  (§4.5).

Every Korean number is VENDOR-REPORTED unless marked INDEPENDENT, and
README-ONLY-grade per §3.5. VRAM figures are INFERRED (models.md §6).

| Model | Korean evidence | TC / SO | Fine-tuning tooling | QLoRA VRAM | 4-bit inference VRAM | Maturity |
|---|---|---|---|---|---|---|
| Gemma 4 E2B-it | No Korean-specific number; MMMLU 67.4 | native TC; SO not stated | Unsloth (GGUF, MLX, NVFP4, QAT); Axolotl 2026/04; transformers v5.x | ~6-8 GB | ~4 GB | high |
| Gemma 4 E4B-it | MMMLU 76.6 | native TC | as above | ~9-12 GB (README: a T4 may OOM) | ~6 GB | high |
| Gemma 4 12B-it | MMMLU 83.4 | native TC | Unsloth (12b-it, GGUF, NVFP4) | ~12-16 GB | ~8-9 GB | medium-high (5 months) |
| Gemma 4 26B-A4B-it | MMMLU 86.3 | native TC; OR schema (paid) | Unsloth; MoE LoRA | ~20-26 GB | ~17 GB | high (in production) |
| Gemma 4 31B-it | MMMLU 88.4 | native TC; OR schema (paid) | Unsloth bnb-4bit, GGUF, MLX | ~24-30 GB | ~20 GB | high (in production) |
| gpt-oss-20b | No Korean benchmark found | TC (harmony format, UNVERIFIED); OR schema | Unsloth, Axolotl 2025/07 | ~16-22 GB (UNVERIFIED) | ~14-16 GB | high |
| gpt-oss-120b | **KCL-MCQA 29.2→64.1 with precedents; essay 31.6→56.0 (INDEPENDENT)** | TC; OR schema | Unsloth, Axolotl | ~70-80 GB | ~65-70 GB (one 80 GB GPU) | high |
| Granite 4.2 3B / 8B | Korean in the language list; MMLU-ProX-lite 61.06 (8B); no Korean-specific test | TC (`qwen3_coder` parser); OR schema (8B) | Axolotl lists "Granite 4" (2025/10); no Unsloth 4.2 repos | ~5-6 / ~9-12 GB | ~3 / ~6 GB | medium (2 months) |
| Ministral 3 8B / 14B | Korean in the language list; no Korean numbers | TC; OR schema | Unsloth, Axolotl 2025/12 | ~10-12 / ~13-17 GB | ~6 / ~9 GB | medium-high |
| Kanana-2-3B-instruct | KMMLU-CoT 43.32 vs Qwen3.5-2B 41.75; HAE-RAE-CoT 43.75 vs 27.84; KoMT 6.92 vs 5.21 | TC (BFCL-v3 reported); SO not stated | No Unsloth; Qwen3 architecture, so TRL/PEFT (INFERRED). Community-only GGUF/MLX | ~5-6 GB | ~3 GB | low (12 weeks, 4.5k DL) |
| Kanana-2-30B-A3B-2601 | KMMLU 68.26 vs Qwen3-30B-A3B-2507 67.56; HAE-RAE 75.57 vs 53.41; BFCL-v3 live 76.66 | TC (hermes/qwen parsers) | No Unsloth; DeepseekV3 architecture (INFERRED). Community-only AWQ/GPTQ/GGUF | ~24-30 GB | ~19-20 GB | low (1.5k DL) |
| Mi:dm 2.0 Mini / Base | Base: KMMLU 57.3, HAE-RAE 81.5, Ko-IFEval 82, Ko-MTBench 89.7; the card leans on KT-proprietary sets | TC through a custom vLLM parser | No Unsloth; Llama architecture, so generic TRL/PEFT/Axolotl (INFERRED) | ~4-5 / ~12-15 GB | ~2 / ~8 GB | medium (2025-07) |
| A.X 4.0 (Light is Qwen2.5-based) | **KCL A.X 4.0 (large): MCQA 49.1→71.3, essay 34.7→52.4 (INDEPENDENT)**; the best open no-evidence MCQA | — | generic | Light ~9-11 GB | Light ~5 GB | medium |
| A.X K2 | KMMLU-Pro 80.5, KoBALT 73.0, CLIcK 91.6 (thinking mode) | TC (`hermes`); SO not stated | transformers from source plus an SKT vLLM fork | n/a (8×80 GB or more) | ~400+ GB | low (12 weeks) |
| K-EXAONE 2.0 | KMMLU-Pro 69.1, CLIcK 84.2, HRM8K-KSM 91.1, Ko-LongBench 89.6, KGC-Safety 99.8 | TC (`qwen3_xml` / `qwen3_coder` parsers) | LG vLLM/SGLang forks required | n/a | ~420-450 GB | low |
| Solar Open 2 250B | KMMLU-Pro 78.4, CLIcK 90.7, HAE-RAE v1.1 73.8, **KBL 75.5**, KorMedMCQA 93.0 | TC (`solar_open2` parser, OpenAI schema) | vLLM recommended; Upstage transformers branch | n/a | ~150 GB (card minimum: 4×H200 at BF16) | low |
| Nemotron 3 Ultra / 3.5 Super-VL | Ultra KMMLU-Pro 69.2, CLIcK 84.1 (reported by competitor SKT); Super-VL lists no Korean | TC; OR schema (paid); the Ultra `:free` slug lacks SO | Axolotl context-parallel for Nemotron-H (2026/06); Unsloth 3.5 GGUF/NVFP4 | n/a | Super ~70 GB; Ultra ~300+ GB | high (in production) |
| HyperCLOVA X SEED Think 14B / 32B | KCL (14B) MCQA 31.3→57.6 (INDEPENDENT); the 32B card gives Korean scores only as an image | TC not documented | 14B needs custom code | ~24-30 GB (32B) | ~20 GB | licence-blocked (§7) |
| EXAONE 4.0 32B | KCL MCQA 36.4→72.3 (INDEPENDENT) | — | Unsloth (4.0-32B) | — | — | **non-commercial** |
| Phi-4-mini | KCL MCQA 22.0→30.6, essay 6.0→18.9 (INDEPENDENT, weakest) | TC | Unsloth/TRL | ~5-6 GB | ~3 GB | high, but weak in Korean |

**VRAM rules behind those figures (models.md §6, INFERRED):**

- **4-bit inference:** total parameters × ~0.6 GB per billion, plus 1-2 GB at
  8K context. For a MoE model, all experts stay resident, so total
  parameters set memory and active parameters set speed.
- **QLoRA:** ≈ 0.65 × B + 4 GB, at sequence length 2048, micro-batch 1,
  gradient checkpointing and r=8-16 on all projections. Vision and audio
  towers add 0.5-1.5 GB unless stripped.

None of these figures has been measured. See
[14](14-hardware-and-cost-model.md).

---

## 7. Licence blockers

Read from the LICENSE file at the pinned SHA unless stated (models.md §4,
Verification pass claims 3-8). VERIFIED as a reading of the text, which is
not a legal opinion. Clauses are paraphrased. The display strings are quoted
because the licences require those exact strings.

### 7.1 Disqualifying for production (models.md §5 disqualifiers, §9 Rec. 5)

| Licence (models) | Clause that disqualifies | Notes |
|---|---|---|
| EXAONE AI Model License 1.2-NC (EXAONE 4.0, 4.0.1, 4.5) | §2.1(a): research and education only. §3.1: no commercial use, and no use of the model, derivatives or outputs to build competing models | The texts at three SHAs are byte-identical. EXAONE 4.5-33B would otherwise be a strong single-GPU Korean reasoner |
| MiniMax M2.7 | Titled non-commercial; commercial use needs prior written authorisation | Also policy-blocked |
| NCSOFT VARCO-VISION family | `cc-by-nc-4.0` | From HF tags only; no LICENSE read |
| HyperCLOVA X SEED (Think 14B, Think 32B, Text 1.5B) | AUP Addendum A 1.d bans unauthorised or unlicensed professional services, including legal ones. §4 requires a separate licence if the product is substantially similar to, or competes directly with, a NAVER product. NAVER may amend the agreement unilaterally (§2.1, §12) | The competition clause has no threshold, and Naver runs consumer AI search and assistant products. A model distilled from SEED outputs is a "Derivative Model" (models.md §4; [13 §8](13-artemis-experiment.md)) |
| Mistral Medium 3.5 (Modified MIT) | No rights at all, derivatives included, if company monthly revenue exceeds US$20M | It also has no Korean evidence |
| K-EXAONE AI Model License (K-EXAONE-236B) | §2.2: distributing, sublicensing or making the model or its derivatives available to third parties for commercial purposes needs a separate agreement | Ambiguous for a hosted product, so treat it as requiring LG's agreement (INFERRED). §2.1 grants commercial use, and the "K-EXAONE" prefix applies on distribution |

### 7.2 Allowed only after counsel review

| Licence (models) | Issue | Status |
|---|---|---|
| Muse Model License (Muse Spark Open) | Usage Policy (Exhibit A 1.4) bans unauthorised or unlicensed practice of a profession, legal practice included. It is not intended for under-18s. **"Built with Muse Spark Open"** must be displayed by any product using the model or a derivative, and a model distilled from its outputs is a derivative. MaaS providers above US$20M 12-month revenue need an agreement | VERIFIED (LICENSE.md read; the separate `USE_POLICY.md` returned 401, but Exhibit A is the incorporated policy) |
| Llama 3.1 Community | **"Built with Llama"** display; "Llama" prefix for distributed derivatives, including models trained on outputs; acceptable-use policy incorporated by reference | The **AUP's legal-practice clause is UNVERIFIED**: the redirect chain ended in HTTP 404, and the repo `USE_POLICY.md` is gated. Korean is not an officially supported Llama 3.1 language |
| Gemma Prohibited Use Policy (Google page, last modified 2024-02-21) | §2.2 and §3.6 cover unlicensed practice. The page is scoped to "Gemma or Model Derivatives" and names neither Gemma 4 nor Apache 2.0 | **Whether it binds Apache-2.0 Gemma 4 is UNVERIFIED** (INFERRED: Apache-2.0 does not incorporate it). The Terms of Use page was not fetched. Until resolved, give Gemma 4 the same "information, not legal advice" counsel review as Muse and HyperCLOVA X |

**Consequence (models.md §0 item 4).** Waymaker has to stay
demonstrably "information, not legal advice" whichever base is chosen. The
disclaimers and review-needed warnings the repository rules protect are part
of licence compliance, not only product policy (INFERRED).

### 7.3 Obligations that do not disqualify but must be budgeted

| Obligation | Who | Notes |
|---|---|---|
| UI attribution | Kanana (**"Powered by Kanana"**), HyperCLOVA X ("Powered by HyperCLOVA X"), Llama ("Built with Llama"), Muse ("Built with Muse Spark Open"), MiniMax M3 ("Built with MiniMax M3"), Solar ("Built with Solar", only if a derivative model is distributed or made available) | Static about/licence page or UI chrome, never in answers (§4.4) |
| Derivative-name prefix | Kanana, HyperCLOVA X, Llama, Solar, K-EXAONE, EXAONE | It is triggered by distributing (or making available) a derivative model, not by serving answers |
| Distillation counts as a derivative | Muse, Kanana ("Derivative Works" include models trained on distilled or synthetic data), HyperCLOVA X. EXAONE 1.2-NC bans outputs for competing models | Matters for teacher selection: [09](09-training-and-distillation.md), [13 §8](13-artemis-experiment.md) |
| Kanana Open License (2-3B / 1.3B) | Own-service use is allowed. A separate licence is needed to resell API access, or to offer SI/on-prem or on-device deployment to third parties (§4.1). §9.4 bars using the model weights to train new models except as expressly permitted | The licence header reads "Kanana Release Date: July 17, 2025", an older template reused for Kanana-2-3B (createdAt 2026-07-24) |
| Kanana License (2-30B-A3B-2601) | As above, plus a separate licence above 10M MAU | **The MAU test is a one-time snapshot at the release date**, so it effectively never bites for a new service like Visable. The same holds for HyperCLOVA X (10M MAU) and Llama 3.1 (700M MAU) (Verification pass claims 5, 7) |
| Qwen Community License 1.0 / Qwen3.8-Max, Kimi K3, GLM-5.3 | MaaS / "AI Work Assistant" clauses and display thresholds | They do not bite unless raw inference is exposed as an API, and a domain assistant is outside Qwen's AWA definition (INFERRED). All are policy-blocked anyway |
| OpenMDW-1.1 (Nemotron 3 Ultra, 3.5) | Retain notices; no restrictions on outputs; termination on patent or copyright retaliation | Permissive. The Bolt LICENSE file is 0 bytes |
| Apache-2.0 / MIT | Keep the licence and NOTICE; mark modified files | The gpt-oss `USAGE_POLICY` (200 bytes) only asks for compliance with law (VERIFIED) |

### 7.4 Licence evidence gaps to close before adoption

- Gemma 4 and A.X K2: no LICENSE file in the repo. Archive the vendor page
  with the SHA, and ask SKT to add a file.
- VAETKI: the MIT tag and the Apache-2.0 text conflict.
- Nemotron Open Model License (3 Super/Nano): not read.
- Llama 3.1 AUP and the Llama 4 licence: not read.
- Gemma Terms of Use: not fetched.

---

## 8. Korean evidence quality

### 8.1 Independent evidence: KCL only, and only for 2025 models

KCL (LBox and University of Seoul; arXiv 2512.24572; listed as
2026.eacl-short.17 on the ACL Anthology) is the only independent Korean
*legal* benchmark with open-model numbers [WEB https://arxiv.org/html/2512.24572v2]
INDEPENDENT. The ACL Anthology page fetch failed, so the arXiv HTML was used.
About the benchmark:

- It covers 30+ models, mostly accessed around 2025-10-02.
- MCQA is reported vanilla and with supporting precedents. Essays are judged
  by Gemini 2.5 Flash.
- The verifier re-checked all 12 rows below against the arXiv tables.

| Model | MCQA: vanilla → with precedents | Essay: vanilla → with precedents |
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

What KCL supports, and what it does not:

- **It supports the evidence-pack design.** Supplying precedents raises MCQA
  by 9-36 points (×1.39 for Phi-4-mini up to ×2.2 for gpt-oss-120b). The
  original "roughly doubles" was corrected by the verifier. Waymaker's
  Athena reads over a supplied `evidence_pack` for the same reason.
- **It says nothing about any 2026 model** on the shortlists: not Gemma 4,
  Kanana 2, Granite 4.2, Solar Open 2, A.X K2, K-EXAONE 2.0 or Nemotron 3/3.5.
  Gemma 3 27B and Kanana 1.5 8B are earlier generations of shortlisted
  families. Their numbers do not carry over (INFERRED).
- **The dataset is CC-BY-NC-4.0** (README-ONLY, via a search summary of the
  HF dataset card). It is usable for internal evaluation only, never for
  training a commercial model.

### 8.2 Vendor-reported evidence: plentiful, partisan, and inconsistent

Every Korean number on the K-EXAONE 2.0, A.X K2, Solar Open 2, Kanana 2,
Mi:dm 2.0, Qwen3.5, Gemma 4 and Granite 4.2 cards is VENDOR-REPORTED.
Problems found (models.md §7, Verification pass claims 10-11):

| Problem | Detail |
|---|---|
| Competitors disagree about the same model | Qwen3.5 KMMLU-Pro is 77.4 on LG's table and 78.4 on SKT's; Qwen3.5 CLIcK is 88.9 (LG) and 88.4 (SKT); DeepSeek-V4-Flash KMMLU-Pro is 78.8 (SKT) and 78.9 (Upstage) |
| Self-reported "best" claims are tied or beaten in rivals' tables | LG's card gives DeepSeek-V4-Pro (max) exactly A.X K2's self-reported KMMLU-Pro 80.5 and CLIcK 91.6. On SKT's own table, DeepSeek-V4-Flash beats A.X K2 on KoBALT (75.3 vs 73.0) and KMO26 (94.4 vs 92.5). All SKT models were run in thinking mode |
| "Only Korean legal score" overstated | Upstage's table gives KBL for Solar Open 2 (75.5), Solar Open 100B (65.5), MiMo-V2.5 (69.8), DeepSeek-V4-Flash (72.8) and GPT-5.4 mini (75.3, 0.2 behind). DeepSeek-V4-Flash also beats Solar Open 2 on KMMLU-Pro (78.9 vs 78.4) and KorMedMCQA (94.1 vs 93.0). The accurate claim: Solar Open 2 is the only 2026 open model whose own vendor reports a Korean legal benchmark |
| Benchmark authored by a vendor | KMMLU-Pro was authored by LG AI Research with OneLineAI: 2,822 licensure-exam items, including 696 law items. LG reports on a benchmark it designed |
| Republished vendor numbers | BenchLM's K-EXAONE KMMLU-Pro of 67.3 equals LG's own card value |
| Proprietary sets | Mi:dm's card leans on KT-proprietary K-Refer / Ko-Sovereign sets |
| No Korean number at all | Gemma 4 (MMMLU only), Granite 4.2 (MMLU-ProX-lite only), Ministral 3, gpt-oss-20b, Nemotron 3.5 Super-VL |

**KBL.** KBL is a University of Seoul / LBox / Hanyang benchmark (EMNLP 2024
Findings; arXiv 2410.08731) with closed-book and RAG settings (README-ONLY,
search summary). Waymaker could run KBL itself as an independent check on
Upstage's 75.5 (models.md Verification pass).

### 8.3 General indices and unreadable leaderboards

- **Artificial Analysis open-weights page** (general, not Korean;
  INDEPENDENT): MiMo-V2.6-Pro 46, GLM-5.3 45, Kimi K3 44, GLM-5.3-Flash 42,
  DeepSeek V4.1 Flash 39, Muse Spark Open 39, Qwen3.8-27B 34, MiniMax-M3 29,
  Nemotron 3.5 Super VL 26, Inkling 25. Gemma 4, gpt-oss and the Korean models
  were not on the rendered page [WEB https://artificialanalysis.ai/models/open-source].
  The verifier did not re-check these figures.
- **Horangi v4 (W&B Korea).** The page is JS-rendered behind a redirect chain
  and returned no rows. Not readable (OBSERVED failure); not retried.
- **Not found:** any independent KMMLU-Redux/Pro, HAE-RAE, CLIcK, KoBEST or
  Ko-IFEval leaderboard covering Gemma 4, Qwen3.6+, A.X K2, K-EXAONE 2.0,
  Solar Open 2 or Kanana 2.

**Conclusion.** Treat every vendor Korean number as a hypothesis, and treat
"Korean-native" as a claim to measure, not a property. Waymaker has to
produce its own Korean evidence (§10).

---

## 9. Ranked shortlists

Ranks order **licence × policy × tooling × the strength of whatever Korean
evidence exists**. They are not measured quality, and every rank is INFERRED
(models.md §5). The verifier made no ranking changes. It softened the
"only/highest" framing for Solar Open 2 and A.X K2 and added two caveats to
Gemma 4 (hosted `:free` slugs lack schema-strict output; the prohibited-use
page is unresolved).

### 9.1 Artemis: compact extraction, classification and routing

| # | Candidate @ revision | For | Against |
|---|---|---|---|
| 1 | `google/gemma-4-E4B-it` @ ee0ef6023621cff504d758262d4e04895a5af4a2, with `google/gemma-4-E2B-it` @ 3e22461f65e89153144f8adb70e3b8c2cc9845a7 as the cheaper sibling | Apache-2.0 and ungated (VERIFIED). Native function calling (README-ONLY). 128K context. The widest tooling of any candidate. Same family as the production router and the repo's experiment, so Artemis and Hestia share one tokenizer and template | **No Korean-specific benchmark** (MMMLU 76.6 only, VENDOR). The multimodal towers inflate memory (the README warns of T4 OOM). The checkpoint is `Gemma4ForConditionalGeneration`, so a text-only `AutoModelForCausalLM` load and the PEFT target-module names are UNVERIFIED |
| 2 | `kakaocorp/kanana-2-3b-instruct` @ 6a5d7889964c4c590299d16e309eabab1f73f8a9 | Korean-native: trained from scratch per its card, which claims >30% better Korean tokenisation. Vendor Korean scores clearly above Qwen3.5-2B. Tool calling. Qwen3 architecture, so TRL/PEFT should work (INFERRED). ~5-6 GB QLoRA | "Powered by Kanana" display and "Kanana" prefix duties; §4.1 resale limits. 32K context. Low maturity (4.5k DL; community-only quantisations). Architecture lineage raises policy question 3 (§4.2) |
| 3 | `ibm-granite/granite-4.2-3b` @ e459acceac81e5fe67c07d9cfc72329a332e7eb1 / `ibm-granite/granite-4.2-8b` @ f8de16cdcdbc6c779ca517604e050d82cc119e44 | Apache-2.0. Korean in the language list. OpenAI-schema tool calling with thinking, non-thinking and low-effort modes. Official GGUF/MLX/FP8/NVFP4. Paid OpenRouter slug with schema output (8B). Policy-neutral | **Zero Korean evidence.** No Unsloth 4.2 repos; Axolotl lists only "Granite 4" |
| 4 | `K-intelligence/Midm-2.0-Mini-Instruct` @ 383eb221c52a32278f1985257b264ade8d982e60 | MIT. 2.3B. Korean-centric vendor scores. Llama architecture, the easiest fine-tuning path. Tool calling through a vLLM parser | July-2025 generation; 32K context; no thinking mode; KT-proprietary benchmarks dominate its card |
| 5 | `mistralai/Ministral-3-8B-Instruct-2512` @ 5b26027e7b19eeb4b7352e1fed3926375dd2cb4d | Apache-2.0. Korean in the language list. Mature tooling. Paid OpenRouter slug with schema output | No Korean evidence |
| — | *Policy-blocked:* `Qwen/Qwen3.5-4B` @ 851bf6e806efd8d0a36b00ddf55e13ccb7b8cd0a / `Qwen/Qwen3.5-9B` @ c202236235762e1c871ad0ccb60c8ee5ba337b9a | Technically the strongest compact option (§4.2 table) | `CHINESE_ONLY_MODEL_PREFIXES`; owner decision |

**Disqualified for Artemis:**

- `LGAI-EXAONE/EXAONE-4.0-1.2B`: non-commercial.
- `naver-hyperclovax/HyperCLOVAX-SEED-Text-Instruct-1.5B`: gated (auto), the
  legal-services AUP and the competition clause.
- `microsoft/Phi-4-mini-instruct`: the weakest Korean legal result in KCL
  (22.0→30.6, INDEPENDENT).
- Llama 3.2 1B/3B: Korean is not an officially supported language, and the
  AUP is unread.
- `nc-ai-consortium/VAETKI-7B-A1B`: custom code, 268 downloads and a licence
  metadata conflict.

**Design note.** Much of Artemis's work can be settled by a regular
expression: status codes, subcodes and dates. The workspace rule is to prefer
a deterministic check to a model call [DOC ~/.claude/AGENTS.md]. Artemis
should therefore handle only the residual ambiguous intent and procedure
cases, and the smallest model that passes evaluation wins: E2B,
Kanana-2-1.3B or Mi:dm Mini (models.md §5, INFERRED).
[13](13-artemis-experiment.md) operationalises this as "decide whether to
train at all", with arm A on E4B and the smoke run on E2B.

### 9.2 Athena: advanced reasoning over supplied evidence

| # | Candidate @ revision | For | Against |
|---|---|---|---|
| 1 | `upstage/Solar-Open2-250B` @ 9190fbe63a2ad8e17fc766ccceb36de7c66f004b | The only 2026 open model whose own vendor reports a Korean legal benchmark (KBL 75.5, VENDOR). KMMLU-Pro 78.4, CLIcK 90.7, HAE-RAE 73.8 (VENDOR). 15B active, 1M context, OpenAI-schema tool calling. Apache-based licence; naming duties only if a *derivative model* is distributed or made available. A sovereign stage-2 finalist | Not on OpenRouter (`solar-pro4` is a different, proprietary product). Card minimum 4×H200 at BF16; about 2×H100 at 4-bit (INFERRED). Only ~2.3% of its weights were carried over from Solar Open 1, so it is mostly a fresh pre-train (README-ONLY). 7.2k DL |
| 2 | `skt/A.X-K2` @ 2287ca456927eed33b899c404c0b2ffaf17aa09f | The highest Korean scores among policy-compatible open models (KMMLU-Pro 80.5, CLIcK 91.6; VENDOR, thinking mode), tied by DeepSeek-V4-Pro in a competitor's table. Apache-2.0, trained from scratch, 256K context, hermes tool calling. Top composite in sovereign stage 2 (70.6). Its predecessor A.X 4.0 has the best **independent** no-evidence KCL MCQA among open models (49.1) | 688B-A33B needs a multi-GPU node, a forked vLLM (`axk2-v0.23.0`) and transformers from source. No LICENSE file. Not on OpenRouter |
| 3 | `LGAI-EXAONE/K-EXAONE-2.0-750B-A37B` @ fec0c8dd25fdd20ffd09869d5af5277966d5523d | A clean Apache-2.0 LICENSE and NOTICE, a shift from LG's earlier licences. The best vendor safety numbers (KGC-Safety 99.8, ROK-Fortress 89.5). 262K context, tool calling | On LG's own table it trails Qwen3.5 and DeepSeek-V4-Pro on KMMLU-Pro (69.1 vs 77.4 / 80.5) and on CLIcK. Needs LG forks. The largest of the three |
| 4 | `openai/gpt-oss-120b` @ b5c939de8f754692c1647ca79fbf85e8c1e70f8a | Apache-2.0. Fits one 80 GB GPU (MXFP4). Very mature; paid OpenRouter slug with schema output. Policy-compatible. **The only shortlisted model with INDEPENDENT Korean legal numbers**: KCL MCQA 64.1 and essay 56.0 with precedents | 2025 vintage. Weak Korean knowledge without evidence (MCQA 29.2). Middling with evidence: it beats Gemma 3 27B, Kanana 1.5 8B and HCX 14B on essay, but trails EXAONE 4.0 32B and A.X 4.0 on MCQA |
| 5 | `nvidia/NVIDIA-Nemotron-3-Ultra-550B-A55B-NVFP4` @ 02462641f13d3af838b904f48195b9bb8a1e4ebc / `nvidia/NVIDIA-Nemotron-3.5-Super-VL-120B-A12B-BF16` @ 1f8953f7f0935358e3605150d22bc15df062061c | Already the production Basic and verifier chain. OpenMDW is permissive, with no output restrictions. Korean is listed for Ultra | Only competitor-reported Korean numbers (Ultra KMMLU-Pro 69.2 on SKT's card). Super-VL lists no Korean. The Ultra `:free` slug lacks structured output (§4.5) |
| lite | `google/gemma-4-31B-it` @ 842da3794eaa0b77d5f08bae87a17459d91ff475 | Apache-2.0. Single-GPU at 4-bit. MMMLU 88.4 (VENDOR). In production. The evidence-reasoning fallback, and the Hestia base | No Korean-specific evidence |

**Other Athena candidates:**

- **Policy-blocked:** DeepSeek-V4/V4.1-Flash, GLM-5.3, Kimi K3 and
  Qwen3.8-27B (§4.2).
- **Caution, not disqualified:** `meta-models/Muse-Spark-Open-816B-A42B` @
  0fb02478b02565b2ce7fc57e6051c91172774ac9. It scores 39 on the Artificial
  Analysis page and is on OpenRouter as `meta/muse-spark-open` with schema
  output. Its licence requires the "Built with Muse Spark Open" display and
  carries the legal-practice clause (§7.2).

**Disqualified for Athena:**

- EXAONE 4.5-33B: non-commercial.
- MiniMax M2.7: non-commercial.
- Mistral Medium 3.5: revenue cap, and no Korean evidence.
- HyperCLOVA X SEED Think 32B: the AUP and the competition clause.
- K-EXAONE-236B: §2.2.
- `Motif-Technologies/Motif-3`: custom code; eliminated in stage 2; its card
  benchmarks were never fetched (UNVERIFIED).

**Hosting reality.** None of the three Korean sovereign models is on
OpenRouter [LIVE OpenRouter catalog]. Each needs self-hosting on multiple
H100/H200-class GPUs with vendor forks. That is why the default plan keeps
the hosted chain and runs a bake-off first (§1 item 1;
[14](14-hardware-and-cost-model.md)).

### 9.3 Hestia: professional assistant, shared base plus LoRA

| # | Candidate @ revision | For | Against |
|---|---|---|---|
| 1 | `google/gemma-4-31B-it` @ 842da3794eaa0b77d5f08bae87a17459d91ff475 (quality) / `google/gemma-4-12B-it` @ 707f0a3b8a3c7ad586ed01e27eafbad8a27dd0f7 (cost; already the repo's planned quality run) | Apache-2.0, ungated, dense, so LoRA is simple. QLoRA ~24-30 GB / ~12-16 GB. Unsloth and Axolotl. Hosted 31B and 26B-A4B endpoints are in production. Shares a template with an E4B Artemis | No Korean-specific evidence. 12B is the newest, least battle-tested size (and its config sets `attention_k_eq_v: true`, so the LoRA target names are UNVERIFIED). 26B-A4B is cheaper to serve, but MoE LoRA is less mature |
| 2 | `kakaocorp/kanana-2-30b-a3b-instruct-2601` @ 4a781fe5027da4af8d8208cb21bc5108b913bb62 | The strongest vendor Korean profile at 3B active (KMMLU 68.26, HAE-RAE 75.57, KoMT 8.21; BFCL-v3 live 76.66; VENDOR). A Kanana-2 3B + 30B pairing is fully Korean-native | Kanana License: attribution, naming, §4.1 resale limits; distillation counts as a derivative. Native 32K context. 1.5k DL, no Unsloth |
| 3 | `K-intelligence/Midm-2.0-Base-Instruct` @ 35479c5fc9a18a5db7cc6dbadcf1db68db7beab0 | MIT with no attribution beyond the notice. 11.5B dense Llama architecture, the cheapest Korean-native LoRA base. Vendor HAE-RAE 81.5, Ko-IFEval 82 | July-2025 vintage; no reasoning mode; 32K context; leans on proprietary benchmarks |
| 4 | `openai/gpt-oss-20b` @ 6cee5e81ee83917806bbde320786a8fb61efebee | Apache-2.0. About 16 GB inference. Unsloth and Axolotl LoRA recipes. Policy-compatible | No Korean evidence for the 20B. The harmony chat format adds template work (UNVERIFIED) |
| 5 | `ibm-granite/granite-4.2-30b` @ 9e668ce1c538387ef24d3644e9b0606647762636 | Apache-2.0, dense 29B, Korean in the language list | No Korean evidence |
| — | *Policy-blocked:* `Qwen/Qwen3.6-27B` @ 6a9e13bd6fc8f0983b9b99948120bc37f49c13e9 / `Qwen/Qwen3.8-27B` @ 1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0 | Apache-2.0, Unsloth, MTP; 7.7M DL (3.8-27B) | Owner decision (§4.2) |

**Disqualified for Hestia:**

- EXAONE 4.5-33B: non-commercial.
- HyperCLOVA X SEED Think 32B: the AUP and the competition clause.
- Mistral Medium 3.5: revenue cap.

`upstage/Solar-Open-100B` has a workable licence, but LoRA on a 100B MoE is
costly. It is the most plausible upgrade if Solar becomes the Athena family.

### 9.4 Shared-base recommendation (INFERRED, models.md §5)

Pick one tokenizer family for Artemis and Hestia:

- **Gemma 4** (E4B + 31B/12B) is policy-aligned, the lowest-risk choice, and
  already in production.
- **Kanana 2** (3B + 30B-A3B) is the Korean-native alternative. It adds
  attribution and naming duties, a resale limit, and policy question 3.

Neither family has independent Korean evidence, so the choice between them is
an evaluation result, not a research result.

---

## 10. What must be measured on the Waymaker benchmark before choosing

No vendor number above can stand in for any of these measurements.

### 10.1 Decisions and checks that come before any measurement

| # | Item | Owner | Why first |
|---|---|---|---|
| 1 | Rule on the scope of the China-origin policy: the three questions in §4.2 | owner | It changes which models are measured at all |
| 2 | Counsel review of the unlicensed-practice clauses (Muse, Llama 3.1 once read, and Gemma's prohibited-use page) and of the Korean licences' arbitration and amendment clauses | counsel | A model that cannot ship is not worth scoring |
| 3 | Approve the Gemma default-role text change if Gemma becomes Hestia or Athena-lite (§4.3) | owner | The policy text and the code disagree |
| 4 | Pin `revision=` to the §6.1 SHA, and archive the licence page for repos without a LICENSE file | engineer | Reproducibility; [13](13-artemis-experiment.md) already enforces this for Artemis |
| 5 | Smoke load: does `AutoModelForCausalLM` load each `…ForConditionalGeneration` checkpoint text-only, and do all seven LoRA target names exist (Gemma 4 12B: `attention_k_eq_v: true`)? | engineer | UNVERIFIED (models.md §8). `train_qlora.py` refuses a target with no language-model match ([13 §4](13-artemis-experiment.md)) |
| 6 | Freeze the thresholds before the first scored run | engineer | [12 §7.2](12-evaluation-methodology.md): a threshold is never relaxed after a result is seen |

### 10.2 Artemis (benchmark v0 can decide this)

The tasks are `status_procedure_classification` and `entity_date_extraction`
[CODE experiments/waymaker-ai/waymaker_ai/dataset/tasks.py]. Metrics and gates
are from [12 §3.1-3.2, §3.6, §7.2](12-evaluation-methodology.md). Every
candidate is compared against the **fixed rules** (B-fixed) on the text-only
slice, because the first question is whether a model is needed at all
([13 §1](13-artemis-experiment.md), D1).

| What to measure | Metric / gate | Why it decides between candidates |
|---|---|---|
| No parent stands in for a subcode | `classification.hierarchy_violations` = 0 (HG-10) | The repository's code-hierarchy rule. A model that flattens a subcode into its parent is out, whatever its accuracy |
| No visa/stay scope mix | `classification.procedure_scope_violations` = 0 (HG-7) | 사증발급 and 체류 procedures never mix |
| Subcode and procedure accuracy | `subcode_accuracy_subcode_expected` ≥ 0.90 (SG-6), `procedure_fine_accuracy` ≥ 0.85 (SG-7), with Wilson intervals | The residual work rules cannot do; the reason Artemis exists |
| Schema-exact output | `model.structured_output_valid_rate` ≥ 1.0 (SG-8) | The production `:free` Gemma slugs do not list `structured_outputs` (§4.5). Measure on the endpoint that would actually serve |
| Dates with roles | `dates.exact_accuracy`, `dates.value_role_precision` / `_recall` | Anchor dates feed the temporal resolver ([06](06-temporal-law-and-source-identity.md)) |
| Adversarial slices | Results by class I (`subcode_confusion`) and K (`real_world_dates`) on `adversarial_holdout`, plus non-ko/en items | The vendor claims, Korean-native tokenisation included, are about exactly these cases |
| Tokens per question | `performance.tokens` (from server `usage`, never estimated) | Tests Kanana's ">30% better Korean tokenisation" claim and feeds cost |
| Latency | `performance.latency_ms` p95 (PG-1 ≤ 3500 ms; reported only) | Quick Answer's budget |
| E2B vs E4B (and Kanana-2-1.3B / Mi:dm Mini) | The same metrics; prefer the smaller model if it lies within the larger one's CI | The smallest model that passes wins (§9.1 design note) |

The runner's `performance.peak_memory_bytes` measures only the client side for
model baselines ([12 §3.6](12-evaluation-methodology.md)). GPU memory on the
serving host has to be measured separately, because every VRAM figure in §6.2
is INFERRED.

### 10.3 Athena (benchmark v0 covers part of it)

- **Abstention** (`abstention`, model baselines only):
  `abstention.withhold_accuracy` / `_precision` / `_recall`,
  `abstention.required_issue_coverage` and
  `abstention.forbidden_assertion_violations`, plus the failure-to-abstain
  rows of the critical-error list (CLE-9) ([12 §3.5, §7.1](12-evaluation-methodology.md)).
  This is where "faithful to the evidence" becomes measurable.
- **Evidence-pack conditions.** Score each candidate with and without the
  evidence pack, on the same items. KCL predicts a large gap (§8.1), and a
  candidate whose no-evidence score is close to its with-evidence score is
  answering from memory (INFERRED).
- **Adversarial slices.** Report class M (`missing_legal_source`),
  H (`upstream_failure`) and N (`source_injection`) separately. Withholding a
  conclusion when the source is missing or failed is the behaviour spec 07
  requires ([07](07-evidence-verification-design.md)).
- **Independent external checks (internal use only).**
  - KCL-MCQA with precedents: the dataset is non-commercial, so it is used for
    evaluation only, never for training.
  - KBL run by Waymaker as an independent check on Upstage's 75.5.

  Neither replaces the Waymaker benchmark.
- **Not decided by the model.** Citation verification and temporal version
  selection belong to the deterministic WLIE gate
  ([07](07-evidence-verification-design.md); [13 §5](13-artemis-experiment.md)).
  An Athena candidate is not scored as the verifier, and its output still has
  to pass that gate (HG-1 to HG-6).
- **Hosting.** For Solar Open 2, A.X K2 and K-EXAONE 2.0 the bake-off itself
  needs rented multi-GPU nodes and vendor forks. Cost and feasibility go to
  [14](14-hardware-and-cost-model.md) before the bake-off is authorised.

### 10.4 Hestia (benchmark v0 cannot decide this)

Benchmark v0 scores closed values only. The quality, tone and Korean style of
a free-text answer are explicitly out of scope
([12 §1](12-evaluation-methodology.md)). So:

- **Under the models.md reading (professional assistant):** before choosing,
  Waymaker needs the following. All are NOT STARTED:
  - format adherence to the 6-section answer (a Ko-IFEval-style check,
    models.md §9 Rec. 7);
  - abstention on the same suite as Athena;
  - Korean prose checked by `kolint --genre ux` (a lint that reports, never a
    rewriter, and never applied to legal or administrative wording);
  - critical-error review by a person;
  - multi-LoRA serving cost.
- **Under the training-distill.md reading (guardian/verifier):** a model
  verifier can only be advisory beside the deterministic gate. It would be
  measured on `citation_verification` with HG-1 to HG-5 as hard limits,
  above all **zero false absence declarations** (HG-1).

[10](10-athena-and-hestia-strategy.md) has to fix the role before the
measurement can be designed.

### 10.5 Cross-cutting rules

- Vendor Korean numbers are hypotheses. A rank in §9 changes only on a
  Waymaker measurement.
- The equivalent-input rule ([12 §4.1](12-evaluation-methodology.md)) applies
  to model baselines: every candidate gets the same prompt, schema and
  evidence.
- A hard-gate failure (`NO_GO`) disqualifies a candidate regardless of soft
  scores. `PROVISIONAL_GO` is not `GO` until the scored labels are
  `human_verified` ([12 §7.2](12-evaluation-methodology.md)).
- No score, in this document or elsewhere, is a claim of legal correctness.

---

## 11. Not verified, or still open

From models.md §8 and the "not filled" list in its Verification pass:

| Item | Status |
|---|---|
| Whether Google's Gemma Prohibited Use Policy binds Apache-2.0 Gemma 4; the Gemma Terms of Use page | UNVERIFIED (the policy page was read; its binding force was not established; ToU not fetched) |
| Llama 3.1 AUP text; Llama 4 licence | UNVERIFIED (404 / gated) |
| NVIDIA Nemotron Open Model License (3 Super/Nano) | not read |
| A.X K2 licence terms (no LICENSE file) | README-ONLY |
| Active parameters of gpt-oss-20b/120b and Solar-Open-100B | UNVERIFIED (not read from cards) |
| Fine-tuning tooling for Kanana 2, Mi:dm, A.X K2, Solar Open 2 and K-EXAONE | INFERRED from architecture. Unsloth has 0 repos for each (VERIFIED); Axolotl does not mention them |
| Text-only load and LoRA target names for Gemma 4 / Qwen3.5 `…ForConditionalGeneration` checkpoints | UNVERIFIED; smoke test (§10.1 item 5) |
| VRAM figures | INFERRED, never measured |
| Model-card numbers, parsers and dates | README-ONLY-grade (WebFetch summaries; ENOSPC, §3.5) |
| gpt-oss "harmony" chat format remark | UNVERIFIED (prior knowledge) |
| Motif AAII 47 vs the page maximum of 46 | unresolved |
| Sovereign-programme final timing ("early 2027") | UNVERIFIED |
| Artificial Analysis figures; the remaining Kanana, Mi:dm and Granite vendor numbers; the stage-1 elimination reasons | not re-checked by the verifier |
| Any independent Korean leaderboard covering 2026 models (Horangi, KMMLU-Redux, KoBEST, Ko-IFEval) | not found; Horangi unreadable and not retried |

## 12. Recommendations

From models.md §9, with the verifier's corrections:

1. **Fix the stale gating assumption** in
   `experiments/waymaker-gemma4-finetune`: drop the `HF_TOKEN` guard for
   Gemma 4 E4B/12B, and pin `revision=` to the §6.1 SHAs.
2. **Ask the owner to rule** on the three policy questions in §4.2 before any
   candidate list is final.
3. **Default plan:** Artemis = Gemma 4 E4B (E2B if the evaluation allows).
   Hestia = Gemma 4 31B or 12B with LoRA. Athena = the current hosted chain,
   plus a Solar Open 2 / A.X K2 / K-EXAONE 2.0 bake-off on Waymaker evidence
   packs before GPUs are committed.
4. **Korean-native contingency:** Kanana-2-3B + Kanana-2-30B-A3B. The live
   constraints are attribution and naming (§3.1(v)), the separate licence for
   third-party API, SI/on-prem or on-device access (§4.1), and the
   weights-for-training restriction (§9.4). The 10M-MAU clause is a
   release-date snapshot and unlikely to apply.
5. **Never adopt for production:** EXAONE 4.x (non-commercial), MiniMax M2.7
   (non-commercial), VARCO-VISION (non-commercial) and HyperCLOVA X SEED (the
   legal-services AUP and the competition clause). Muse Spark Open and Llama
   are acceptable only with counsel sign-off on the unlicensed-practice
   clause and with mandatory UI attribution. Gemma 4 gets the same counsel
   review until its prohibited-use page is resolved.
6. **Put licence-mandated attributions** on a static about/licence page.
   Consider extending the guard's provider pattern
   ([CODE backend/services/knowledge/guard.py:37-41]) to the Korean model
   names, MiniMax, GLM and bare "Llama". That is a guard change for a later
   mission, not this one.
7. **Build the Korean evaluation before any selection** (§10): the golden
   behaviour set; benchmark v0; KCL-MCQA with precedents (internal only);
   format adherence for the 6-section answer; and the JSON-schema validity
   rate for Artemis outputs.

## 13. Status by item

| Item | Status |
|---|---|
| Landscape snapshot and pinned candidate matrix (§5-6) | RESEARCHED ONLY (VERIFIED against the HF API on 2026-10-19; re-checked SHAs for 15 repos) |
| Licence readings (§7) | RESEARCHED ONLY (texts read at pinned SHAs; not a legal opinion; counsel review NOT STARTED) |
| Korean evidence review (§8) | RESEARCHED ONLY (vendor numbers README-ONLY-grade) |
| Shortlists (§9) | RESEARCHED ONLY (INFERRED rankings) |
| Owner ruling on the China-origin policy scope | NOT STARTED (owner decision) |
| Gemma 4 smoke load and LoRA-target check | NOT STARTED |
| Artemis measurement on benchmark v0 | NOT STARTED (configs prepared in [13](13-artemis-experiment.md), not run) |
| Athena bake-off (Solar Open 2 / A.X K2 / K-EXAONE 2.0) | NOT STARTED (needs multi-GPU hosting) |
| Hestia measurement | BLOCKED until [10](10-athena-and-hestia-strategy.md) fixes the role; benchmark v0 does not score free text |
