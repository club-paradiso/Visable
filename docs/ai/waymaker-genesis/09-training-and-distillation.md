# 09 — Training and distillation

Status: **RESEARCHED ONLY.** No model was trained, distilled, served or
evaluated in Mission 001, and this document changes no code. The teacher policy
that §4 summarises is encoded in `experiments/waymaker-ai/configs/teacher_policy.json`
with its gate in `waymaker_ai/distillation/teacher_policy.py`; that code is
described in [13 §8](13-artemis-experiment.md) and its legal sign-off is
`pending`. Nothing here is legal advice. Items marked REQUIRES LEGAL REVIEW stay
open until counsel reads the captured terms.

Mission 001 "Waymaker Genesis". Research date 2026-10-19; written 2026-10-20.
Primary source: [research-notes/training-distill.md](research-notes/training-distill.md)
(§0-§7 plus its verification pass). Context:
[research-notes/models.md](research-notes/models.md) and
[research-notes/cost.md](research-notes/cost.md), both with their verification
passes. Code citations are to the audited commit `0713370` as the notes recorded
them. Evidence tags: `[CODE path:line]`, `[TEST …]`, `[DOC …]`, `[LIVE …]`,
`[WEB url, accessed 2026-10-19]`. Status words: VERIFIED, OBSERVED, README-ONLY,
INFERRED, UNVERIFIED. Where a verifier corrected a note, the corrected reading is
the one used here, and the correction is named.

## 0. Bottom line

1. **Training now is premature.** The live manual index held 2,626 chunks and
   **0 direct-evidence chunks** from an approved edition [LIVE GET
   /api/health/ai, 2026-10-19, 200] (re-OBSERVED by the verifier). There is no
   verified gold corpus, no frozen answer-level eval set and no legal sign-off
   on any teacher. The largest gains available today come from retrieval and
   deterministic rules (§2.4) (training-distill.md §0.7, §5).
2. **Train behaviour, never facts.** Seven stay-manual editions took effect
   between 2026-05-01 and 2026-09-18 [CODE data/manual_approval_index.json:47-300]
   VERIFIED. Fine-tuning on new facts raises hallucination, and retrieval beats
   fine-tuning for knowledge injection (§2.3). The only legitimate training
   targets are behaviours: following the evidence, abstaining, structure, Korean
   register, and keeping parent codes and subcodes apart (training-distill.md §0.6).
3. **What may be done with a model's outputs depends on the serving channel,
   not on the weights licence.** The same Nemotron weights are OpenMDW-1.1
   (no restriction on outputs) when self-hosted and trial-only through
   OpenRouter's `:free` route, which OpenRouter links to the NVIDIA API Trial
   Terms of Service (§3.1) (training-distill.md §0.2, §3.1 rows 2-3).
4. **No channel Waymaker uses today can be a teacher.** Every permitted teacher
   is self-hosted open weights: gpt-oss-120b/20b, Gemma 4, Nemotron 3 Ultra /
   3.5 Lightning / 3 Super, Inkling, Llama 3.1/3.3, each with notice conditions
   (§3.2). The practical first pair is gpt-oss-120b (one 80 GB GPU) and Gemma 4
   31B (training-distill.md §3.3).
5. **Teacher conclusions are candidate labels, never gold.** They become
   training targets only after deterministic checks and WLIE claim verification
   pass and a human legal reviewer approves. No teacher is ever asked for
   private chain-of-thought (§3.4).
6. **The experiment is specified, gated and NOT RUN.** The generic design (arms
   B0 / A / A+ / REF / B / C) is in §5; its first concrete instance is the
   Artemis experiment in [13](13-artemis-experiment.md), which starts with a
   decision on whether a model is needed at all.
7. **Production-terms risk (owner decision, REQUIRES LEGAL REVIEW).** The
   channel finding is not only about distillation. Real `/api/ask` questions
   reach channels whose published terms bar production use or personal data
   (§6). This is the most consequential finding in this document.

## 1. Providers and model ids in use today

All traffic goes through OpenRouter to open-weight models, plus Groq on one
path. No first-party Anthropic, OpenAI-API or Gemini-API call exists: `git grep`
finds direct calls only to openrouter.ai, api.groq.com and, in the unwired
scaffold, integrate.api.nvidia.com; first-party host names appear only in a CI
deny-list and an output-scrub regex [CODE backend/services/knowledge/guard.py:38-39]
VERIFIED (training-distill.md §1, verifier claim 1).

| Surface / role | Code default chain | Live chain (2026-10-19) | Upstream server | Evidence |
|---|---|---|---|---|
| `/api/ask` Basic final answer | `nvidia/nemotron-3-ultra-550b-a55b:free` → `google/gemma-4-31b-it:free` → `nvidia/nemotron-3-super-120b-a12b:free` → `thinkingmachines/inkling:free` | identical | Nvidia; Google AI Studio; Nvidia; Thinking Machines | [CODE backend/services/model_policy.py:31-37] [LIVE L28, L15] VERIFIED |
| Fast tier, search overview, nationality coach | `google/gemma-4-26b-a4b-it:free` → `nvidia/nemotron-3.5-lightning:free` → `thinkingmachines/inkling-small:free` → `google/gemma-4-31b-it:free` | identical | Google AI Studio; Nvidia; Thinking Machines; Google AI Studio | [CODE model_policy.py:99-105] [LIVE L28] VERIFIED |
| Router / translator | `google/gemma-4-31b-it:free` | identical | Google AI Studio | [CODE model_policy.py:23-24] VERIFIED |
| Verifier role | `nvidia/nemotron-3-super-120b-a12b:free` | leads with `openai/gpt-oss-120b:free`, which is absent from the catalog | — | [CODE model_policy.py:118] [LIVE L28, L7]. Verifier: the live value is OBSERVED, the env-override cause INFERRED, and no production code calls `TaskRole.VERIFIER` on main, so the chain is declared but unused |
| Enforcement structured (Python) | `google/gemma-4-26b-a4b-it:free` → `nvidia/nemotron-3-super-120b-a12b:free` | **paid** `openai/gpt-oss-20b` → `google/gemma-4-31b-it` → `openai/gpt-oss-120b` | DeepInfra, CoreWeave, Parasail, AkashML and others | [CODE model_policy.py:112-116] [CODE backend/paradiso_backend.py:8426,8468] [LIVE L28] VERIFIED; cause INFERRED |
| Chinese-language route | `minimax/minimax-m3` → two `inclusionai/ling-3.0-*:free` | not reported | Ling ids absent from the catalog | [CODE model_policy.py:120-124] [LIVE L7]; no caller outside the policy module (cost.md §1) |
| Vercel Quick Answer wording | `google/gemma-4-31b-it:free` → `openai/gpt-oss-120b:free` → `meta-llama/llama-3.3-70b-instruct:free` | same | the last two ids are dead, so the chain is one model deep | [CODE lib/waymaker-quick-answer-ai.js:18] [LIVE L7] VERIFIED |
| Vercel enforcement AI | `lib/enforcement-grounded-ai.js:13-18` (four ids, three dead); `api/enforcement/analyze.js:7-15` presets gemma `:free` → gpt-oss-120b `:free`; `confirm.js:3` gemma `:free` | not checked | — | verifier correction to training-distill.md §1; an analyze.js comment invites an operator opt-in to a Gemini model via OpenRouter, which would add Google's terms to that path |
| Groq | `llama-3.1-8b-instant` | `groq.configured: true` | Groq | `/api/ask`: opt-in only. `/api/nationality-coach`: called whenever `GROQ_API_KEY` is set and OpenRouter fails, with no opt-in [CODE paradiso_backend.py:7792-7798] VERIFIED (verifier correction) |
| Ollama | `qwen3:8b` on localhost | off unless `ENABLE_OLLAMA_FALLBACK` | local | [CODE paradiso_backend.py:257-259] VERIFIED |
| NVIDIA NIM scaffold | `nvidia/nemotron-3-ultra-550b-a55b` at integrate.api.nvidia.com | `wired_to_api_ask: False`; research and internal-QA modes only; personal data blocked | NVIDIA API Catalog | [CODE backend/services/providers/nvidia_nim.py:12-13,42-43,87-98] [TEST backend/tests/test_nvidia_nim_provider.py (ran: pass)] VERIFIED |

Notes:

- The owner's unpushed branch `fix/waymaker-qa-2026-10-16` removes
  `inkling:free` from the Basic chain after it returned 403
  `model_access_denied`. `inkling-small:free` stays in the Fast chain (cost.md
  verifier claim 15). This reduces, but does not remove, the Basic path's
  exposure to the Thinking Machines terms.
- Five configured ids are absent from the OpenRouter catalog [LIVE L7, V5]
  VERIFIED. On the free tier each failed attempt counts toward the daily cap
  (cost.md §0.2).
- The `:free` slugs in production (Gemma 4 31B and 26B-A4B, Nemotron 3 Ultra,
  Nemotron 3.5 Lightning) do not list `structured_outputs` in the OpenRouter
  catalog; only `nemotron-3-super-120b-a12b:free` and the paid slugs do
  (models.md §1 and §3b, verifier corrections) OBSERVED. This matters for any
  schema-strict answer contract (§2.2).
- Existing training work: `experiments/waymaker-gemma4-finetune` is a Colab
  LoRA/QLoRA wiring scaffold with 6 placeholder training and 8 eval examples,
  never run in the repository (knowledge-platform.md §4) VERIFIED. Its README
  treats Gemma 4 as gated; the HF API shows `gated: false` and Apache-2.0
  (models.md §0 item 2) VERIFIED. It is superseded for Artemis by
  `experiments/waymaker-ai` ([13 §13](13-artemis-experiment.md)).
- Project policy already rules out fine-tuning on user queries [DOC
  docs/paradiso_ai_safe_automation_architecture.md:41], and the golden set is
  flagged `"is_training_data": false` [CODE
  backend/data/eval/paradiso_ai_golden_questions.json:4] VERIFIED.

## 2. Technique comparison

### 2.1 Roles, and how the fit columns are read

The names Artemis, Athena and Hestia appear nowhere in the repository or on the
owner's branch (`git grep -i`, training-distill.md verifier, not filled #4)
VERIFIED. This document set uses:

| Role | Working definition | Defined in |
|---|---|---|
| **Artemis** | Compact routing and extraction: parent status, exact subcode, procedure, dates with roles. Writes labels, never prose, never a requirement | [13 §1](13-artemis-experiment.md) |
| **Athena** | Reasoning over a bounded WLIE `EvidencePackage`, answering in the structured contract of [07 §5](07-evidence-verification-design.md) | [05 §4](05-legal-intelligence-architecture.md); models.md header |
| **Hestia** | Professional assistant (checklists, drafts, missing-information detection, traceable answers) on a shared base, possibly with LoRA adapters | [10](10-athena-and-hestia-strategy.md); models.md header |

training-distill.md §2.0 scored its fit columns under different, self-made
definitions (INFERRED there): its Artemis also wrote Fast-tier and Quick Answer
wording, and its "H" column scored a **self-hosted verifier** for
claim-to-evidence entailment. In this document set claim verification is the
deterministic WLIE gate ([07](07-evidence-verification-design.md)), and a model
judge is advisory only (07 §3 L5). The tables below therefore show:

- **Ar** and **At**: the notes' values.
- **He†**: this document's remap for the professional-assistant Hestia, as the
  notes asked the parent to do. INFERRED, not from the notes.
- **V**: the notes' original "H" column, kept for the advisory model-verifier
  role.

Under [13](13-artemis-experiment.md)'s narrower Artemis (labels only), the
prose-related Artemis scores (multilingual SFT, response distillation) no longer
apply; only label SFT, structured output, LoRA/QLoRA and gated label
distillation remain relevant.

Compute classes (training-distill.md §2.0, INFERRED): C0 no GPU; C1 one
16-24 GB GPU (QLoRA to about 12B); C2 one 40-80 GB GPU (LoRA 12-31B, QLoRA to
about 70B); C3 multi-GPU node; C4 cluster.

### 2.2 MODEL TRAINING techniques (these change weights)

Data volumes are INFERRED unless a source is cited. Source: training-distill.md
§2.1 with its verifier corrections.

| Technique | Data · compute | Main legal-accuracy risk | Ar | At | He† | V | Now vs later |
|---|---|---|---|---|---|---|---|
| General SFT (broad instruction data) | 10k-1M pairs · C2-C3 | Dilutes careful legal behaviour; adds no domain safety | low | low | low | low | **No.** Instruct bases already have it |
| Task-specific SFT | 1-5k reviewed examples per task · C1-C2 | Memorises one edition's facts if examples carry real facts; placeholders avoid it | high | high | high | mid | Later, after G0 (arm B) |
| Structured-output SFT | 1-3k schema-valid examples · C1 | Schema-valid text with wrong content looks authoritative | high | mid | mid | high | Later; constrained decoding first (§2.3) |
| Multilingual SFT [WEB arxiv.org/abs/2401.01854] (title VERIFIED, content UNVERIFIED) | small multilingual share · C1-C2 | Mistranslated protected terms: status codes, form names, 체류자격 labels | mid | high | low | low | Later; glossary-protected translation and kolint first |
| LoRA [WEB arxiv.org/abs/2106.09685] | as SFT · C1-C2 | Learns less but forgets less than full fine-tuning [WEB arxiv.org/abs/2405.09673] VERIFIED, which suits behaviour-only tuning | high | high | high | high | Default PEFT method once training starts |
| QLoRA (NF4) [WEB arxiv.org/abs/2305.14314] | as SFT · C1 | Slightly below 16-bit LoRA (Unsloth guide, VERIFIED); Korean degradation needs its own check | high | high | high | mid | Default for arms B and C on budget |
| Adapter specialisation and composition (LoraHub [WEB arxiv.org/abs/2307.13269], AdapterFusion [WEB arxiv.org/abs/2005.00247], S-LoRA [WEB arxiv.org/abs/2311.03285]) | 1-3k per adapter · C1 each | Composition can blend procedure scopes, which CLAUDE.md forbids. Select deterministically, never merge | mid | high | high | mid | Later; hard routing by procedure scope |
| Full fine-tuning | 10k+ · C3 | More capacity to memorise statute text; more forgetting | low | low | low | low | **No** |
| Domain-adaptive / continued pretraining [WEB arxiv.org/abs/2004.10964] (legal example SaulLM [WEB arxiv.org/abs/2403.03883]) | 100M-10B+ tokens · C3-C4 | **Worst fit.** Bakes one law snapshot into the prior; the corpus is small and changes every few weeks | none | none | none | none | **No** |
| Response (sequence-level) distillation [WEB arxiv.org/abs/1606.07947] | 5-20k filtered teacher responses · C1-C2 | Imitation copies style, not factuality [WEB arxiv.org/abs/2305.15717] VERIFIED; commercial legal RAG tools still hallucinate 17-33% of the time [WEB arxiv.org/abs/2405.20362] VERIFIED | high | mid | mid | mid | Later, **verified outputs only** (arm C) |
| Logit-based KD [WEB arxiv.org/abs/1503.02531] | teacher logits · C2-C3 | Impossible through APIs (paid OpenRouter gpt-oss exposes `top_logprobs` at most). TRL `DistillationTrainer` needs a shared vocabulary; the experimental `GOLDTrainer` (TRL v1.16.0) does cross-tokenizer distillation, alignment for a Gemma student unmeasured (verifier claim 12) | low | low | low | low | Self-hosted only, same family or via GOLD |
| On-policy distillation (GKD [WEB arxiv.org/abs/2306.13649], MiniLLM [WEB arxiv.org/abs/2306.08543]) | prompts only · C2-C3 | The teacher's token distribution includes its legal errors | mid | mid | low | low | Later, self-hosted only |
| Task-specific distillation with rationales [WEB arxiv.org/abs/2305.02301] | 1-10k · C1 | Rationales are legal reasoning the teacher made up; asking for them invites private-CoT requests (§3.4) | high (extractor) | low | low | mid | Later, extraction only, rationales limited to verbatim evidence quotes |
| Multi-teacher distillation [WEB arxiv.org/abs/2402.13116] | 2-4 teachers · C1-C2 | Agreement does not make an answer legally true; teachers share biases | mid | mid | mid | high | Later; use disagreement to route items to human review, never to vote gold |
| Structured reasoning supervision (process supervision [WEB arxiv.org/abs/2305.20050]; RAFT [WEB arxiv.org/abs/2403.10131] VERIFIED) | 1-5k annotated traces · C1-C2 | Steps can look grounded without being grounded; requiring each quote to be a verbatim substring of the package makes it checkable | mid | **high** | high | high | Later; **the best training lever for Athena** |
| DPO [WEB arxiv.org/abs/2305.18290] | 1-10k pairs differing in correctness, not tone · C1-C2 | Can learn to prefer a confident style | mid | high | mid | mid | Later, after SFT; strong for "abstaining beats inventing" |
| ORPO [WEB arxiv.org/abs/2403.07691] | same pairs · C1 | As DPO, harder to diagnose | mid | mid | low | low | Optional when compute is tight |
| KTO [WEB arxiv.org/abs/2402.01306] | unpaired good/bad labels · C1 | A user's "INCORRECT" may itself be wrong; use only reviewer-confirmed labels | low | mid | mid | mid | Later; Knowledge Studio produces exactly such reviewed labels [DOC docs/ai/WAYMAKER_KNOWLEDGE_PLATFORM.md:288-294] |
| SimPO [WEB arxiv.org/abs/2405.14734] | pairs · C1 | Length normalisation may reward short answers that drop cautions | low | low | low | low | Not justified |
| RL with verifiable rewards (GRPO [WEB arxiv.org/abs/2402.03300]; Tülu 3 RLVR [WEB arxiv.org/abs/2411.15124]) | prompts + evidence packs; rewards are code · C2-C3 | Reward hacking (always abstain, always cite the first chunk); RLVR mostly sharpens what the base can already do [WEB arxiv.org/abs/2504.13837] VERIFIED | mid | high | mid | low | Later; Waymaker's answers are unusually checkable by code |
| Model merging (task arithmetic [WEB arxiv.org/abs/2212.04089], TIES [WEB arxiv.org/abs/2306.01708], DARE [WEB arxiv.org/abs/2311.03099]) | 2+ adapters · C0-C1 | Unpredictable interference; can bring back a superseded adapter's behaviour; hard to audit | low | low | low | low | No, unless an eval proves it |

### 2.3 RETRIEVAL, INFERENCE and ORCHESTRATION techniques (weights unchanged)

Source: training-distill.md §2.2, plus the WLIE gate row from
[07](07-evidence-verification-design.md).

| Technique | What it changes | State today | Legal-accuracy effect | When |
|---|---|---|---|---|
| RAG with edition-aware evidence packs [WEB arxiv.org/abs/2005.11401] | What the model sees per request | Index had 0 direct-evidence chunks live; the owner's branch page-maps the approved 2026.9 texts (commit messages, README-ONLY, not run) | The only way to track 7 editions in 4.5 months; RAG beats fine-tuning for new knowledge [WEB arxiv.org/abs/2312.05934] VERIFIED | **Now. Top priority** |
| Retrieval quality: effective-date (`efYd`) filters, history, 부칙 | Recall and currency | Law search matches names only and never sends `efYd` (law-stack.md); the backend reads no history and no 부칙 ([06 §5](06-temporal-law-and-source-identity.md)) | A temporally wrong source makes every downstream step wrong | **Now** (WLIE resolver; backend wiring in [17](17-mission-002-plan.md)) |
| Tool-augmented reasoning (ReAct [WEB arxiv.org/abs/2210.03629]) | The model calls deterministic tools | The six-tool registry (`lookup_status`, `calculate_deadline`, `search_law` …) is described by `/api/health/ai` but `/api/ask` does not call it (ai-lifecycle.md §2.7) VERIFIED | Deadlines, codes and fees come from code | Now; wire up what exists |
| Deterministic validators | Accept or reject model text | Quick Answer's `validateEnhancement` [CODE assets/js/waymaker-quick-answer.js:290-322] [TEST scripts/check_waymaker_quick_answer.mjs (ran: pass, 23 checks)]; statute guard [TEST backend/tests/test_statute_citation_guard.py (ran: pass)] | Blocks invented numbers, offices, overclaims and unconditional exemptions, whatever the model | **Now; extend to `/api/ask`** |
| WLIE claim gate L1-L7 | Per-claim verification before display | Offline reference implementation, IMPLEMENTED BUT NOT VALIDATED ([07](07-evidence-verification-design.md)) | Separates "the law exists" from "this sentence follows from that version's text" | Now offline; production in Mission 002 |
| Constrained decoding (XGrammar [WEB arxiv.org/abs/2411.15100]; vLLM structured outputs) | Guarantees valid syntax | Quick Answer uses `response_format` [CODE lib/waymaker-quick-answer-ai.js:131]; production `:free` endpoints mostly lack `structured_outputs` (§1) | Makes structured-output SFT unnecessary for syntax; content still needs validators | Now when self-hosting or on paid slugs |
| Deterministic model routing [CODE model_policy.py:234-295] [TEST backend/tests/test_model_policy.py (ran: pass)] | Which model answers | Escalation from Fast to Basic by reason code | Auditable; a learned router (RouteLLM, FrugalGPT) is not | Keep; a learned router only as an extra escalation signal later |
| Quantisation (GPTQ, AWQ, Gemma 4 QAT checkpoints) | Inference precision | Not used by Waymaker | Non-Latin scripts suffer most and metrics understate it: about 1.7% drop on automatic Japanese tasks vs about 16% in human evaluation [WEB arxiv.org/abs/2407.03211] VERIFIED | Later, gated on a Korean human eval |
| Efficient serving (vLLM, speculative decoding, multi-LoRA) | Latency and cost | No self-hosting | Neutral if outputs are identical | Later, once self-hosting |
| Model verifier / judge | A second pass over claims | None wired | Can flag unsupported claims, but only as an advisory signal (07 L5; [12 §4.2](12-evaluation-methodology.md) baseline 9) | Prompted, advisory only |

### 2.4 Why facts stay out of the weights, and where rules win

Facts in Waymaker live in versioned sources: seven stay-manual editions in 4.5
months, statutes amended on 2026-10-02 after the last law snapshot
(law-identity.md §3), and a fee-payment article whose effective date is
deferred to 2027-09-16 ([06 §4](06-temporal-law-and-source-identity.md)).
Techniques that write facts into weights (continued pretraining, full
fine-tuning, SFT or distillation on answers that state real facts without the
evidence in the prompt) freeze a snapshot that expires within weeks and cannot
cite where its facts came from. The evidence: fine-tuning on new knowledge
raises hallucination [WEB arxiv.org/abs/2405.05904] VERIFIED (closed-book QA
SFT), and RAG beats *unsupervised* fine-tuning for knowledge injection [WEB
arxiv.org/abs/2312.05934] VERIFIED (verifier nuance: not SFT). A vendor guide's
claim that fine-tuning can stand in for RAG is README-ONLY and contradicted by
both results for law that keeps changing (training-distill.md §2.2). Every
training arm therefore puts the evidence pack in the prompt and scores whether
the answer follows it.

Problems where a rule or retrieval beats any training (training-distill.md §5):

| Problem | Better fix |
|---|---|
| No direct legal evidence in the index | Section and index the approved editions (human review) |
| Facts change every few weeks | Edition-aware retrieval with effective dates and supersession |
| Invented fees, numbers and offices | Apply the Quick Answer validators to `/api/ask` |
| Status codes; parent vs subcode | Structured lookup against the inventory ([13 §6](13-artemis-experiment.md)) |
| Visa issuance vs stay procedures | Scope tags from the source registry; reject mismatches (WLIE L6) |
| Escalation Fast → Basic | Keep `resolve_question_answer_mode` and its reason codes |
| Deadlines | `calculate_deadline` |
| Law recall and currency | Retrieval parameters (`efYd`, history, 부칙) |
| Dead model ids | A catalog check in CI (`scripts/check_model_catalog.py` exists, cost.md §10) |
| Citation validity | Deterministic citation checks (WLIE L1-L4) |

Training helps only where no rule can produce the output: abstention behaviour,
keeping the answer structure under long evidence, following the right passage
among distractors (RAFT), Korean register and plain language, and a cheaper
self-hosted student that keeps data away from third parties, which matters
given §6.

### 2.5 Recommendation: now, later, never

| Horizon | Artemis | Athena | Hestia |
|---|---|---|---|
| **Now** | Rule fixes (B-fixed) and an untuned prompted model scored on the frozen benchmark; train only if decision D1 says so ([13 §6](13-artemis-experiment.md)) | No training. External or open-weight reasoning over WLIE evidence packages, on a channel that passes legal review ([10 §3](10-athena-and-hestia-strategy.md)) | Option A: existing model + workflow + retrieval, no training ([10 §5](10-athena-and-hestia-strategy.md)) |
| **Later, after G0-G6** | QLoRA SFT on reviewed labels (arm B); gated teacher labels (arm C) | RAFT-style structured supervision; DPO/KTO on reviewer-confirmed failures; RLVR with deterministic rewards; verified response distillation | Per-scope LoRA adapters on a shared base, served multi-LoRA, selected deterministically |
| **Never** | Continued pretraining or full fine-tuning on statute or manual text; teacher conclusions as gold labels; requesting private chain-of-thought; fine-tuning on user queries | same | same |

Operational recommendations that come first (training-distill.md §6 "Now"):
ship no trained model; get legal review of the production channels (§6); move
user-facing traffic to channels whose terms allow production use and the data
involved; pass G0; extend the deterministic validators to `/api/ask`; prune
catalog-dead ids.

## 3. Distillation feasibility

### 3.1 The serving-channel finding

OpenRouter's own terms (last updated 2026-08-31) pass ownership and use of
outputs through to each model's terms (§5), opt out of provider training only
where OpenRouter is able to (§6.1), and contain no separate ban on training with outputs
[WEB https://openrouter.ai/terms] [LIVE L1] VERIFIED. The upstream channel
therefore decides. Three channels carry production traffic today:

| Channel (OpenRouter routes) | Terms OpenRouter links | Clauses as verified (paraphrased) | Status |
|---|---|---|---|
| Nvidia: `nvidia/*:free` (Nemotron 3 Ultra, 3 Super, 3.5 Lightning) and the NIM scaffold endpoint | **NVIDIA API Trial Terms of Service**, footer "v. September 19, 2025" (PDF metadata 2025-10-07) [WEB https://assets.ngc.nvidia.com/products/api-catalog/legal/NVIDIA%20API%20Trial%20Terms%20of%20Service.pdf] | §1.2 trial purposes only, with no production use of the service or Generated Content; §1.4 production needs a separate Subscription, otherwise internal testing and evaluation only; §3.3(iv) NVIDIA may collect User Content and Generated Content to improve its products, including AI models; §4.2 Generated Content may not be copied, transferred or distributed; §4.3 no personal information; §4.12 Generated Content may not be used to develop competing products | VERIFIED [LIVE L14, L16; verifier V6, claim 4; local capture td_raw/nv_api_trial.txt] |
| Thinking Machines: `thinkingmachines/inkling:free`, `inkling-small:free` | **TML Free Research API Tier ToS**, last updated 2026-08-20 [WEB https://thinkingmachines.ai/legal/tml-free-research-api-tier-terms-of-service.pdf] | Without written consent, no developing, training, fine-tuning or distilling a competing model or service, and no systematic collection of outputs to build such datasets; users grant TML a perpetual, irrevocable licence to keep and use prompts and outputs, including to train TML's and other models; no personal, children's or sensitive data; weights cannot be obtained or trained through the API | VERIFIED [LIVE L17; verifier claim 6, td_raw/tml.txt]. cost.md §0.9 could not extract this PDF (glyph-encoded fonts); training-distill.md parsed it locally and its verifier re-read the capture, so its reading is the one used |
| Google AI Studio: `google/gemma-4-31b-it:free`, `gemma-4-26b-a4b-it:free` (sole provider) | OpenRouter's registry links `cloud.google.com/terms/`, **not** the Gemini API Additional Terms [LIVE GET openrouter.ai/api/v1/providers, 2026-10-19, 200] | Gemini API Additional Terms (effective 2026-03-23, page updated 2026-04-28) [WEB https://ai.google.dev/gemini-api/terms]: on Unpaid Services Google uses content to improve its products, human reviewers may read inputs and outputs, and users must not submit personal information; the services may not be used to develop competing models, and no part may be extracted or replicated. Google's pricing page: Gemma 4 is free-tier only on the Gemini API, and free-tier content is used to improve products (cost.md §3) VERIFIED | The clauses are VERIFIED; that they bind the OpenRouter `:free` route is **INFERRED** (verifier correction). Whether OpenRouter's upstream account is on Paid or Unpaid Services cannot be seen from outside |

The same weights under their own licences: Nemotron 3 Ultra and 3.5 Lightning
are OpenMDW-1.1, which places no restriction or obligation on outputs [WEB
https://openmdw.ai/license/1-1/] [LIVE L8, L9]; Nemotron 3 Super is under the
NVIDIA Nemotron Open Model License, which claims no ownership of outputs; Inkling
weights and Gemma 4 are Apache-2.0 (training-distill.md §3.1 rows 3a, 3b, 5a, 6)
VERIFIED. **The permission travels with the weights, not with the route.**
Self-hosting is the only way to use these permissions.

Whether the trial, research and unpaid terms govern calls that OpenRouter
mediates, as opposed to OpenRouter's own upstream agreement, is UNVERIFIED in
every note (cost.md §0.9 verifier; [15](15-security-and-deployment.md) SEC-02).
That is the question for counsel.

### 3.2 Teacher verdicts, with clause references as verified

Decision rule (training-distill.md §3.2): a teacher is permissible only if all
three say yes:

1. the weights licence (or, for a closed model, the provider's terms) allows its
   outputs to train a student that is distributed or used commercially;
2. the serving channel's terms allow production use, retention and
   redistribution of outputs, and the kind of data sent;
3. Waymaker's own model policy accepts the family [CODE model_policy.py:126-131].

**Permitted, with conditions (self-hosted weights only):**

| Teacher | Licence and clause | Condition |
|---|---|---|
| gpt-oss-120b / 20b | Apache-2.0 (HF `apache-2.0`) [LIVE L8]; gpt-oss `USAGE_POLICY` asks only for lawful, responsible use [LIVE L23] (models.md verifier) | Apache notice. 120B fits one 80 GB GPU in MXFP4 [WEB https://huggingface.co/openai/gpt-oss-120b] [LIVE L31] VERIFIED |
| Nemotron 3 Ultra 550B-A55B, Nemotron 3.5 Lightning 30B-A3B | OpenMDW-1.1: no restriction on outputs; redistributed copies keep the licence and notices; patent or copyright litigation ends the licence [LIVE L8, L9] | OpenMDW notices. Ultra needs C3-C4 hardware (INFERRED) |
| Nemotron 3 Super 120B-A12B | NVIDIA Nemotron Open Model License (last modified 2025-12-15): commercial use, Derivative Works allowed, no ownership claim on outputs; redistribution needs the licence and a notice line; litigation ends it [LIVE L10] | Notice line |
| Gemma 4 (31B, 26B-A4B, 12B, E4B, E2B) | Apache-2.0 per Google's licence page and HF `cardData` [LIVE L5] | Apache NOTICE. No Gemma 4 repo ships a LICENSE file, so archive the licence page beside the pinned SHA; whether Google's Gemma Prohibited Use Policy (which has unlicensed-practice clauses) binds Gemma 4 is UNVERIFIED (models.md §4, §8) |
| Inkling, Inkling-Small | Apache-2.0, not gated [LIVE L8; verifier V9] | Apache notice. Inkling is 975B total parameters, so C3-C4 (INFERRED) |
| Llama 3.1 / 3.3 | Community License §1.b.i: if Llama outputs are used to create or improve a model that is distributed **or made available**, its name must start with "Llama"; "Built with Llama" notice; AUP; a clause for services over 700M monthly users [WEB https://raw.githubusercontent.com/meta-llama/llama-models/main/models/llama3_3/LICENSE] [LIVE L21; verifier V12] | Name prefix if the student is made available; attribution; AUP. The Llama 3.1 AUP text itself was not read (redirect chain ended HTTP 404), so its legal-practice clause is UNVERIFIED (models.md §0 item 4, verifier) |

**Not permitted:**

| Teacher / channel | Clause |
|---|---|
| NVIDIA API Trial endpoints: OpenRouter `nvidia/*:free`, build.nvidia.com trial, the NIM scaffold | §1.2 and §4.2 (also §1.4, §3.3(iv), §4.3, §4.12), §3.1 above. Internal research use only, and that REQUIRES LEGAL REVIEW |
| Thinking Machines free research tier (OpenRouter `:free` and direct) | Acceptable-use ban on distilling competing models; perpetual licence on prompts and outputs; no personal data (§3.1). The Apache-2.0 weights can be self-hosted instead |
| OpenAI API | Services Agreement "ONLINE v. 010126" §3.3(e): Output may not be used to develop competing AI models; the only Permitted Exception covers internal, non-distributed classifiers or embedding models and fine-tuning OpenAI's own models; §3.3(f) no extraction outside the Services [WEB https://cdn.openai.com/osa/openai-services-agreement.pdf] [LIVE L19]. A non-distributed internal classifier may fit the exception: REQUIRES LEGAL REVIEW |
| Anthropic API | Commercial Terms (effective 2025-06-17) §D.4: no use of the Services to build a competing product, including training competing AI models, without approval; Consumer Terms (effective 2025-10-08) §3 likewise [WEB https://www.anthropic.com/legal/commercial-terms] [LIVE L2, L3] |
| Gemma 1-3 | Gemma Terms of Use (updated 2026-04-01) §1(e): a model built by transferring patterns from Gemma outputs, explicitly including distillation through synthetic data, is a Model Derivative bound by Gemma's use restrictions [WEB https://ai.google.dev/gemma/terms] [LIVE L6]. Prefer Gemma 4 |
| EXAONE 4.0 / 4.0.1 / 4.5 | EXAONE AI Model License 1.2-NC §2.1(a) research and education only; §3.1 no commercial use, and outputs may not be used to build competing models (models.md §4, verifier claim 3) |
| HyperCLOVA X SEED | Distillation from outputs creates a Derivative Model; AUP 1.d forbids unlicensed legal services; §4 requires a separate licence for a product that competes with NAVER (models.md §4, verifier claim 5) |

The verifier's consistency note applies: the OpenAI §3.3(e), Anthropic §D.4 and
Gemini "compete" clauses raise the same interpretive question, whether a
Korean-immigration domain student "competes". "Not permitted" for OpenAI and
Anthropic is a conservative policy choice, not a settled reading; treat all
three the same way in review (training-distill.md §3.1 row 7, verifier note).
Waymaker uses none of the three today.

**REQUIRES LEGAL REVIEW:**

| Teacher / channel | Why |
|---|---|
| Gemini API; Gemma through Google AI Studio or OpenRouter `:free` | Use Restrictions (compete, extract, replicate) and the Unpaid Services terms; grounded results may not be used for training. For Gemma, self-host instead |
| Every paid OpenRouter host (DeepInfra, CoreWeave, Parasail, AkashML …) for gpt-oss or Gemma | Host terms not reviewed |
| NVIDIA NIM subscription / NVIDIA AI Enterprise | Not reviewed |
| Groq (`llama-3.1-8b-instant`) | Services Agreement (last modified 2026-06-22) §6.3(e) bars developing similar or competing offerings; §4.1 model terms control; outputs are Customer Data and Groq does not train on them [LIVE L20]. The notes call it permitted subject to the Llama licence with light review; the policy file is stricter, because "a domain student does not compete with an inference cloud" is INFERRED ([13 §8](13-artemis-experiment.md)) |
| gpt-oss, Llama and Hermes `:free` routes | Absent from the catalog; channel terms unknown |
| Qwen | Apache-2.0 for Qwen3-8B and Qwen3.8-27B, but not uniformly: Qwen3.8-2.4T is `qwen3.8-max`, Qwen3.8-Flash-Next is `qwen-community-1.0` (verifier claim 9). Waymaker's `CHINESE_ONLY_MODEL_PREFIXES` reserves `qwen/` for Chinese routes; enforcement is a `/health` warning plus a default-chain test, not a runtime filter (models.md §0 item 3, verifier). Owner decision |
| DeepSeek | MIT; the R1 card explicitly allows distillation [LIVE L22]. Same product-policy conflict; the DeepSeek API terms were not reviewed |
| MiniMax M3 | The grant sentence names non-commercial use while clause 2 provides for commercial use with a "Built with MiniMax M3" notice and a one-time notice email, with prior authorisation only above US$20M yearly revenue; prohibited uses include discrimination based on immigration status; the licence is silent on outputs. Internally ambiguous: moved here from "not permitted" by the verifier (training-distill.md §3.1 row 14) |
| InclusionAI Ling 3.0 Flash | MIT [LIVE L13]; configured ids absent; Chinese-route policy |
| Muse Spark Open | Derivatives include models distilled from its outputs; "Built with Muse Spark Open" display; Usage Policy (Exhibit A 1.4) bans unlicensed practice of a profession including legal (models.md §4, verifier claim 6) |
| Kanana 2 | Derivative Works include distillation and synthetic-data-trained models; "Powered by Kanana"; "Kanana" prefix for distributed derivatives; §9.4 limits using the weights to train new models (models.md §4, Rec. 4 verifier) |
| Any reuse of production logs as training prompts | User questions may contain personal data; repurposing needs a lawful basis under PIPA (INFERRED; no legal conclusion drawn). Current policy already forbids fine-tuning on user queries |

A family no note assessed (K-EXAONE 2.0, for example) is denied by default
([13 §8](13-artemis-experiment.md)). `configs/teacher_policy.json` encodes these
readings per serving channel: 34 entries, 6 `permitted_with_conditions`, 9
`not_permitted`, 19 `requires_legal_review`, `legal_signoff.status: pending`
(counted from the file on 2026-10-20, §8).

### 3.3 What distillation is technically possible

| Level | Possible with | Not possible with |
|---|---|---|
| Response-level (the student imitates final structured answers) | Any permitted teacher, including self-hosted gpt-oss-120b on one 80 GB GPU and Gemma 4 31B on a C2 GPU | Any channel in §3.1 |
| Logit-level, same vocabulary | Self-hosted, same family (e.g. Gemma 4 31B → Gemma 4 E4B) with TRL `DistillationTrainer` | Any API (no full distributions) |
| Logit-level, cross-family | Self-hosted, experimental TRL `GOLDTrainer` (cross-tokenizer ULD with span alignment); alignment for a SentencePiece-style Gemma student is weaker and unmeasured (INFERRED) | Any API |

Provenance is mandatory for every distilled example: teacher id and weights
licence id, serving host with its terms URL and version date, request date,
prompt hash and evidence-pack hash (training-distill.md §3.2). The
`TeacherRecord` schema carries these fields ([13 §8](13-artemis-experiment.md)),
and the dataset validator refuses a `teacher_generated` example without them
([11 §4.3](11-dataset-governance.md)).

### 3.4 Policy

These rules bind every distillation run (training-distill.md §0.9, §3.3; [11
§4.3](11-dataset-governance.md); [13 §8](13-artemis-experiment.md)):

1. **No private chain-of-thought.** Reasoning traces are disabled (the NIM
   scaffold already defaults `reasoning_enabled` to false [CODE
   nvidia_nim.py:41]). Teachers are asked only for the final structured answer
   plus verbatim evidence quotes. `gate_record` refuses a record that requested
   reasoning or carries reasoning keys or `<think>` markers.
2. **A teacher's legal conclusion is never a gold label** without WLIE claim
   verification and human legal review. It becomes a training target only after
   the deterministic checks of §5.3 pass, WLIE reports it `verified`, and a named
   human reviewer approves it: at least a stratified sample, and 100% of
   high-risk issue types. A `teacher_generated` example in an eval split must be
   `human_verified`.
3. **Prioritise stable capabilities.** Train what does not change between
   editions: evidence-following, abstention, structure, register, hierarchy and
   scope discipline, label extraction. These survive a new manual edition; a
   fact does not.
4. **Do not memorise one law edition in weights.** Teachers see evidence packs
   from approved editions only, never superseded ones, except deliberately
   labelled stale-edition probes. Edition-shift and counterfactual splits (§5.2)
   test that the student follows the evidence rather than its memory.
5. **Teachers never see eval prompts.** The eval set is frozen with a hash
   manifest first (§5.4).
6. **Legal sign-off gates everything.** While `legal_signoff.status` is not
   `approved`, every teacher record and every `teacher_generated` example is
   refused, whatever its entry says.

## 4. The policy in code (pointer)

The policy and gate are not re-described here. [13 §8](13-artemis-experiment.md)
documents `configs/teacher_policy.json` (default deny; most restrictive match
wins; an API route id with a `:` suffix cannot be declared self-hosted; only
families the model policy accepts may be permitted; one verbatim fragment only)
and `waymaker_ai/distillation/teacher_policy.py` (`load_policy`,
`is_permitted(provider, model, channel)`, `TeacherRecord`, `gate_record`).
[11 §4.3](11-dataset-governance.md) documents how the dataset validator consults
the same policy.

## 5. Experiment design: A / A+ / B / C

### 5.1 Hypotheses and arms (training-distill.md §4.1-§4.2)

| Hypothesis | Claim |
|---|---|
| H1 behaviour, not facts | SFT+QLoRA on reviewed, evidence-conditioned examples lowers the critical-legal-error (CLE) rate and raises correct abstention against the same untuned base with the same packs |
| H2 verified distillation | Adding teacher responses that passed the deterministic verifier and human review (C) beats B at equal training tokens |
| H3 no memorisation | Neither B nor C tracks changed evidence (counterfactual numbers, newer edition) less reliably than untuned A |
| H4 small student viable | A tuned 12B student matches the production chain's CLE rate at lower latency, without third-party data flow |
| H0 null | Better retrieval and validators with an untuned model close most of the gap (tested by A+) |

| Arm | Definition | Training data |
|---|---|---|
| B0 | Deterministic only: structured answer plus Quick Answer, no LLM. Floor for invented facts, ceiling for unhelpfulness | none |
| **A** | Untuned student base (`google/gemma-4-12B-it`, Apache-2.0) plus the evidence pack | none |
| **A+** | A plus the retrieval and validator improvements of §2.4 | none |
| REF | Current production chain on the eval set; reference only. The trial terms still bar personal data, so eval items must be synthetic or scrubbed: REQUIRES LEGAL REVIEW | none |
| **B** | SFT+QLoRA: NF4, r=16, alpha=32, all linear projections, lr 2e-4, 1-3 epochs, loss on assistant tokens only (TRL `assistant_only_loss` / `completion_only_loss` VERIFIED) | 1,500-3,000 human-written or corrected examples |
| **C** | Verified response distillation plus SFT: permitted self-hosted teachers (gpt-oss-120b, Gemma 4 31B) answer training prompts with evidence; the §5.3 verifier filters; humans review; survivors mixed about 1:1 with B's gold, subsampled to B's tokens and steps | 5-20k candidates; if 30-60% pass (INFERRED), 3-10k kept |
| C-DPO (optional) | Pairs of a verifier-failed and a verifier-passed answer to the same prompt | pairs |

Shared controls: identical prompt template, evidence packs, decoding
(temperature 0.2 for answer wording) and output schema under constrained
decoding; 3 seeds per arm; mean ± 95% bootstrap CI.

### 5.2 Splits and frozen sets (training-distill.md §4.3)

S1 in-distribution, held out by case template; S2 status-family hold-out (for
example all F-6 and G-1-5; G-1-5 must not inherit G-1's rules); S3 edition
shift; S4 counterfactual evidence (altered fees, day counts, document names);
S5 insufficient evidence (decisive passage removed); S6 adversarial (overclaim,
parent/subcode and visa/stay bait, injection inside evidence, RAFT-style
distractors); S7 language (ko, en, mixed script and others, kolint `--genre ux`).
Minimum about 600 scored items, at least 50 per split (INFERRED).

Verifier corrections that change the design:

- **The golden 50 are a routing set, not an answer eval.** The file sets
  `"is_llm_eval": false`, and its items carry routing expectations with no
  reference answer or evidence pack [CODE
  backend/data/eval/paradiso_ai_golden_questions.json:4-12]. They can serve as
  prompts with must-not-include checks, but cannot score CLE until reference
  answers and evidence are added.
- **S3 must be inverted once the owner's branch lands.** On that branch the
  2026.9 visa and stay editions are `approved` (reviewed 2026-10-16) and the
  2026-07-31 editions `superseded`. Train on 2026.9 and keep 2026-07-31 → 2026.9
  diffs only as labelled stale-edition probes, because §3.4 rule 4 forbids
  superseded evidence.
- **G0's first condition may already be met on that branch** (page-mapped
  direct-evidence chunks; commit messages README-ONLY, not run).

### 5.3 Deterministic verifier and CLE taxonomy (training-distill.md §4.4-§4.5)

The verifier is code, not a model. It filters arm C, would reward later RLVR,
and measures every arm. Checks: cited source ids and spans appear verbatim in
the pack; every number, amount, period, form id and office name appears in the
evidence; status codes parse and a subcode rule is never stated for its parent;
procedure scope of every source matches the question; no overclaim wording and
all disclaimers present; abstention or a clarifying question when evidence is
insufficient; schema validity. In this document set the citation part is the
WLIE gate ([07](07-evidence-verification-design.md)).

Critical legal errors: CLE-1 invented requirement; CLE-2 number contradicts the
evidence; CLE-3 procedure scopes mixed; CLE-4 hierarchy error; CLE-5
stale-edition claim; CLE-6 false permission or guarantee; CLE-7 missed risk or
deadline warning; CLE-8 fabricated or mismatched citation; CLE-9 failure to
abstain; CLE-10 disclaimer or uncertainty removed; CLE-11 protected term
corrupted. [12 §7.1](12-evaluation-methodology.md) maps the benchmark's runner
categories onto this taxonomy; CLE-1/2/6/7/10/11 concern free-text answers,
which the Mission 001 benchmark does not score.

### 5.4 Gates (training-distill.md §4.7; thresholds are proposals)

| Gate | Condition |
|---|---|
| **G0** before any training | At least one approved, sectioned edition per procedure scope indexed as direct evidence; eval set frozen at 600+ items with a manifest; legal sign-off on teachers and channels; named reviewers |
| G1 safety | Zero CLE-1/2/3/4/6/8 on the golden set once it has reference answers; full-set CLE upper 95% bound at or below REF's point estimate; no category worse than A |
| G2 memorisation | Evidence-tracking on S3/S4 ≥ 98% and not below A |
| G3 abstention | Abstention recall on S5 ≥ 95%; over-abstention ≤ 10% |
| G4 format and language | 100% schema validity; no new kolint errors (`ux`); CLE-11 = 0 |
| G5 human review | 200 stratified outputs, two reviewers, agreement measured (e.g. κ ≥ 0.6), every disagreement adjudicated |
| G6 operations | p95 within the tier budget (Quick Answer timeout 7 s [CODE lib/waymaker-quick-answer-ai.js:31]); no trial-tier hosting |

A no-go on G1, G2 or G3 ends the arm. A threshold is never relaxed to let an arm
pass. [12 §7.2](12-evaluation-methodology.md) adds the benchmark's hard gates
HG-1 to HG-10.

### 5.5 How [13](13-artemis-experiment.md) instantiates the design for Artemis

| Generic arm | Artemis ([13 §3](13-artemis-experiment.md)) | Differences |
|---|---|---|
| B0 | B1-python and B2-js, the existing deterministic classifiers | — |
| A | Untuned `google/gemma-4-E4B-it` (E2B for the smoke run), constrained 7-key JSON | E4B, not 12B: Artemis is a compact role |
| A+ | B-fixed (rule fixes), plus the prompted model only for items the rules cannot settle (decision D1 step 3) | Mapping is this document's (INFERRED); 13 does not use the name A+ |
| B | QLoRA SFT on reviewed labels | Targets are labels with no facts, so H3 applies only as template memorisation, guarded by the leakage check |
| C | B plus gated teacher labels from self-hosted gpt-oss-120b and Gemma 4 31B-it | Labels, not prose; teacher harness specified, not built |
| REF | not used | Eval items may go to providers only after legal review ([12 §4.2](12-evaluation-methodology.md) baseline 9) |

Decoding there is temperature 0 for labels, not 0.2. The train split is EMPTY,
no GPU was used, paid runs are not authorised (`cost.paid_runs_authorised:
false`), and every config is NOT RUN ([13 §14, §16](13-artemis-experiment.md)).
**An Athena experiment was not prepared in Mission 001** (DEFERRED to
[17](17-mission-002-plan.md)); its starting points are §5.1-§5.4, the old
scaffold's `eval_outputs.py` heuristics ([13 §13](13-artemis-experiment.md)) and
the benchmark's abstention task ([12 §3.5](12-evaluation-methodology.md)).

### 5.6 Cost

GPU time is small; review time dominates. Arm A $0-2, arm B $0-15, arm C $10-50
for the Artemis experiment ([13 §11](13-artemis-experiment.md)). Managed LoRA on
an 18M-token workload is about $6 (8B class) to $19 (Gemma 4 31B) at Together,
and $9-54 at Fireworks; a self-run QLoRA on a rented GPU is about $3-33 before a
30-100% allowance for failed runs (cost.md §7, INFERRED arithmetic on VERIFIED
prices, accessed 2026-10-19). OpenAI's fine-tuning is being wound down for new
users (cost.md §0.8) VERIFIED. Detail is in
[14](14-hardware-and-cost-model.md).

## 6. PRODUCTION-TERMS RISK — owner decision, REQUIRES LEGAL REVIEW

> **This is the most consequential finding in this document, and it is not
> about training.** Today `/api/ask` sends real user questions, which may
> contain personal data, through:
>
> 1. **a primary Basic model served under trial-only terms** (Nemotron 3 Ultra
>    `:free` → NVIDIA API Trial ToS). §1.2 grants access "without use of the API
>    Service or Generated Content in production"; §1.4 requires a Subscription
>    for production; §4.3 bars personal information; §3.3(iv) lets NVIDIA
>    collect User and Generated Content to improve its products and models;
> 2. **Basic and Fast fallbacks on a free research tier** (Inkling and
>    Inkling-Small `:free` → TML Free Research API Tier ToS): no personal data,
>    and a perpetual licence for TML to keep and train on prompts and outputs.
>    The owner's branch drops `inkling:free` from Basic; `inkling-small:free`
>    stays in Fast;
> 3. **Gemma routes on what may be an unpaid tier** (Gemma 4 `:free` → Google
>    AI Studio): on unpaid services Google uses content to improve its
>    products, human reviewers may read traffic, and personal information must
>    not be submitted. That these terms bind the OpenRouter route is INFERRED.
>
> Related exposures: the nationality coach reaches Groq without an opt-in, and
> Vercel Quick Answer runs on Gemma `:free` alone (§1).
>
> **Open legal question:** whether these channel terms govern OpenRouter-mediated
> calls at all (UNVERIFIED in every note). Until counsel answers, the
> conservative reading is that the production answer path relies on terms that
> exclude it.
>
> **Options for the owner (not a recommendation of counsel's answer):**
>
> | Option | Cost signal (cost.md §11 scenario 4; [14 §7.4](14-hardware-and-cost-model.md); INFERRED on VERIFIED prices) | Residual question |
> |---|---|---|
> | Keep the `:free` chains, with counsel's written reading | $0 cash; capped at 50 or 1,000 free calls/day | the exposure above |
> | Paid endpoints of the same open models as primary, `:free` last or removed | about $15 (Gemma 4 31B) to $57 (Nemotron 3 Ultra) per month at 10k questions, with the 5.5% fee | each paid host's terms and data policy (REQUIRES LEGAL REVIEW; providers not verified individually) |
> | Self-host for user-facing traffic | $2,600-6,300+ per month for two GPUs, plus operations | not justified on cost below about 2M questions/month; justified only by data control or a fine-tuned model no API serves |
>
> Evaluation is not production use, but the same personal-data bars apply, so
> eval items sent to REF must be synthetic or scrubbed. This finding is
> register item SEC-02 and owner decision 2 in
> [15](15-security-and-deployment.md) §1 and §7.

## 7. Not established by this document

- No technique in §2 was run on Waymaker data. Every fit value is a reading of
  the literature and the code, and the He† column is this document's own
  inference.
- Terms not reviewed: paid OpenRouter hosts, the DeepSeek API, the MiniMax
  platform (JavaScript-only page), NVIDIA's paid NIM / AI Enterprise licence,
  Llama 3.1's AUP text, Gemma's Terms of Use page (training-distill.md verifier,
  not filled #2; models.md §8).
- The notes paraphrase every clause except NVIDIA §1.2; full captured texts for
  a legal reviewer are kept outside the repository (`scratchpad/research/td_raw/`).
- Whether Google's paid or unpaid tier sits behind OpenRouter's Gemma route
  cannot be determined from public data.
- GOLD alignment quality for a Gemma student, and whether `bf16=True` fails on a
  T4 in the old scaffold, were not measured.
- Every threshold in §5.4 is a proposal.

## 8. Checks made for this document

- Read `experiments/waymaker-ai/configs/teacher_policy.json` with the
  `.venv-check` interpreter (`python -I`, standard library only) on 2026-10-20:
  34 entries; `output_use_for_training` = 6 `permitted_with_conditions`, 9
  `not_permitted`, 19 `requires_legal_review`; `legal_signoff.status`
  `pending`. This matches [13 §8](13-artemis-experiment.md).
- No test, training or network request was run for this document. The test
  results quoted above are the notes' own (training-distill.md §7 and V2-V4:
  132 passed and 85 subtests on the five backend modules; 23 Quick Answer
  checks; the old scaffold's validator 0 errors).

## 9. Sources

- [research-notes/training-distill.md](research-notes/training-distill.md):
  §0, §1, §2.0-§2.2, §3.1-§3.3, §4.1-§4.8, §5, §6, §7, and the verification pass
  (claims 1-15; omissions filled 1-7; not filled 1-5).
- [research-notes/models.md](research-notes/models.md): §0 items 2-5, §1, §3b,
  §4, §5, §8, §9 and the verification pass (claims 1-7, 13).
- [research-notes/cost.md](research-notes/cost.md): §0.2, §0.8, §0.9, §1, §3,
  §7, §9, §11 scenario 4, §13 and the verification pass (claims 1, 9, 15).
- [research-notes/knowledge-platform.md](research-notes/knowledge-platform.md) §4;
  [research-notes/ai-lifecycle.md](research-notes/ai-lifecycle.md) §2.7;
  [research-notes/law-identity.md](research-notes/law-identity.md) §3.
- Related documents: [00](00-executive-summary.md),
  [05](05-legal-intelligence-architecture.md),
  [06](06-temporal-law-and-source-identity.md),
  [07](07-evidence-verification-design.md),
  [08](08-foundation-model-research.md),
  [10](10-athena-and-hestia-strategy.md),
  [11](11-dataset-governance.md), [12](12-evaluation-methodology.md),
  [13](13-artemis-experiment.md), [14](14-hardware-and-cost-model.md),
  [15](15-security-and-deployment.md), [17](17-mission-002-plan.md).
