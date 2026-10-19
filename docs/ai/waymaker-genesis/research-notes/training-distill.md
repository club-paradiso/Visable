# Waymaker model specialisation: training techniques, distillation feasibility, provider terms

Mission 001 "Waymaker Genesis". Date: 2026-10-19.

- **Tree audited:** `/Users/seonjaekim/dev/Visable-genesis` at origin/main `0713370`, read-only.
- **Owner's branch:** `fix/waymaker-qa-2026-10-16` is cited only where it changes a conclusion.

**Evidence tags:**
- `[CODE path:line]`, `[TEST ...]`, `[DOC ...]`, `[LIVE Ln]` (log in section 7), `[WEB url, accessed 2026-10-19]`.
- Status words: VERIFIED, OBSERVED, README-ONLY, INFERRED, UNVERIFIED.
- All paper IDs and titles were resolved through the arXiv API [LIVE L25]. They are VERIFIED.
- A paper *finding* marked VERIFIED means I read its abstract page today [LIVE L29].
- A finding marked UNVERIFIED comes from my own prior reading. I did not re-read it today.

**Copyright handling:**
- The task asked for verbatim clause quotes of up to 25 words.
- My operating rules allow at most one short verbatim quote per response.
- Section 3 therefore paraphrases each clause closely and gives the section number and URL.
- The single verbatim quote is the NVIDIA trial clause, because it carries the most weight.
- The full texts I captured are kept locally for a legal reviewer in `scratchpad/research/td_raw/*.txt`. They are not reproduced here.

**Disk warning:**
- The host disk filled up (ENOSPC) several times during this task.
- Each time, Bash and file writes stopped working for a while.
- One arXiv abstract batch request was lost this way (see L30).

---

## 0. Bottom line

1. **Waymaker uses no first-party frontier API today.**
   - Every production LLM call goes through OpenRouter to open-weight models: Nemotron 3 Ultra, Super and 3.5 Lightning; Gemma 4 31B and 26B-A4B; Inkling and Inkling-Small; gpt-oss-20b and 120b; Llama 3.3 70B; Hermes 3 405B; MiniMax M3.
   - Groq (Llama 3.1 8B) and Ollama (Qwen3 8B) are opt-in fallbacks. [corrected by verifier: Groq is opt-in only for `/api/ask` (needs OPENROUTER_API_KEY unset and ALLOW_GROQ_FALLBACK true, [CODE backend/paradiso_backend.py:345-361]). For `/api/nationality-coach`, Groq is called whenever GROQ_API_KEY is set and the OpenRouter chain fails, with no opt-in [CODE backend/paradiso_backend.py:7792-7798] [DOC docs/ai/AI_PROVIDER_AND_MODEL_POLICY.md §1]. The live health endpoint reports `groq.configured: true` [LIVE GET /api/health/ai, 2026-10-19, 200], so in production Groq is a reachable fallback for the coach. VERIFIED]
   - NVIDIA NIM is an unwired scaffold.
   - No Anthropic, OpenAI-API or Gemini-API calls exist [CODE, LIVE L28] VERIFIED.
2. **What may be done with outputs depends on the serving channel, not the weights licence.**
   - OpenRouter's `:free` Nemotron endpoints are served by NVIDIA [LIVE L15].
   - OpenRouter's own provider registry links them to the **NVIDIA API Trial Terms of Service** [LIVE L16].
   - Those terms (all VERIFIED, [LIVE L14]):
     - restrict use to trial purposes;
     - forbid production use and redistribution of Generated Content;
     - forbid uploading personal information.
   - The same Nemotron weights are released under OpenMDW-1.1, which places no restriction on outputs [LIVE L8, L9] VERIFIED.
3. **Side finding, critical, REQUIRES LEGAL REVIEW.** These terms bind the production answer path, not only distillation:
   - the NVIDIA trial clause above;
   - the Thinking Machines free research tier: no personal data, plus a perpetual licence for TML to train on prompts and outputs;
   - Google AI Studio's unpaid-tier terms: "do not submit personal information", and human reviewers may read traffic. [corrected by verifier: whether these Unpaid Services terms bind OpenRouter's Gemma `:free` route is INFERRED, not verified. OpenRouter's provider registry links "Google AI Studio" to `cloud.google.com/terms/`, not to the Gemini API Additional Terms [LIVE GET openrouter.ai/api/v1/providers, 2026-10-19, 200], and whether OpenRouter's own upstream account is on Paid or Unpaid Services cannot be seen from outside. REQUIRES LEGAL REVIEW]
   - [added by verifier] The NVIDIA trial terms also let NVIDIA collect User Content and Generated Content to improve its products and services, including AI models (§3.3(iv)). Production use needs a separate Subscription (§1.4) [WEB NVIDIA API Trial ToS PDF; local capture td_raw/nv_api_trial.txt] VERIFIED.
4. **Permitted teachers**, subject to the conditions in section 3.3:
   - gpt-oss (Apache-2.0), self-hosted or on a host with suitable terms;
   - Nemotron 3 Ultra and 3.5 Lightning (OpenMDW-1.1);
   - Nemotron 3 Super (NVIDIA Nemotron Open Model License);
   - Gemma 4 (Apache-2.0);
   - Inkling weights (Apache-2.0);
   - Llama 3.1/3.3 (naming and attribution conditions).
5. **Teachers that are not permitted, or need legal review:**
   - **Not permitted:** OpenAI API, Anthropic API, Thinking Machines free API tier, NVIDIA API Trial endpoints, and MiniMax M3 for commercial use. [corrected by verifier: MiniMax M3 belongs under REQUIRES LEGAL REVIEW. Its licence provides for commercial use with notices (see row 14).]
   - **REQUIRES LEGAL REVIEW:**
     - the Gemini API;
     - paid third-party hosts such as DeepInfra and CoreWeave;
     - Qwen and DeepSeek. Their licences allow distillation, but Waymaker's own policy restricts China-origin families to Chinese-language routes.
6. **Facts must not be trained into weights.**
   - Seven stay-manual editions took effect between 2026-05-01 and 2026-09-18 [CODE data/manual_approval_index.json:47-300] VERIFIED.
   - Fine-tuning on new facts raises hallucination [WEB arxiv.org/abs/2405.05904] VERIFIED.
   - Retrieval beats fine-tuning for injecting knowledge [WEB arxiv.org/abs/2312.05934] VERIFIED. [corrected by verifier: the Ovadia et al. comparison is RAG vs *unsupervised* fine-tuning (continued training on raw text), not SFT. Gekhman et al. (2405.05904) covers the SFT case. Abstracts re-read via export.arxiv.org, 2026-10-19]
   - Train only behaviour: following the evidence, abstaining, structure, Korean register, and keeping parent codes and subcodes apart.
7. **Training now is premature.**
   - The live manual index holds 2,626 chunks but **0 direct-evidence chunks** from an approved edition. Source: a sibling agent's capture, `research/live_health_ai.json`. OBSERVED by that agent, not by me. [verifier: re-OBSERVED, LIVE GET web-production-14f9a.up.railway.app/api/health/ai, 2026-10-19, HTTP 200: indexedChunks 2626, indexedDirectEvidenceChunks 0, needs_review 1361, superseded 1265. Caveat: the owner's unpushed branch would change this. Commit fd6109b page-maps the approved 2026.9 Markdown texts into the index (its message reports 1,331 + 1,134 page-mapped direct-evidence chunks), and 9bf8849 grounds `/api/ask` in them [DOC git -C ~/dev/Paradiso log fix/waymaker-qa-2026-10-16]. Not deployed, and not verified by running it.]
   - So no verified gold corpus exists yet.
   - The largest gains available today come from retrieval and deterministic rules (section 5).
8. **The A/B/C experiment is specified in section 4.**
   - It must not start until gate G0 passes: an approved, sectioned evidence edition; a frozen eval set; legal sign-off on teachers.
9. **Never request private chain-of-thought from any teacher.**
   - A teacher's legal conclusions are only candidate labels.
   - They become gold only after deterministic checks against the evidence and human legal review.

---

## 1. Providers and model ids Waymaker uses today

| Surface / role | Model id chain (code default) | Live chain (deployed) | Upstream server (OpenRouter endpoints API) | Evidence |
|---|---|---|---|---|
| `/api/ask` Basic final answer, LEGAL_SYNTHESIS, ENFORCEMENT_EXPLAINER | `nvidia/nemotron-3-ultra-550b-a55b:free` → `google/gemma-4-31b-it:free` → `nvidia/nemotron-3-super-120b-a12b:free` → `thinkingmachines/inkling:free` | identical | Nvidia; Google AI Studio; Nvidia; Thinking Machines | [CODE backend/services/model_policy.py:31-37] [CODE backend/services/ai_runtime.py:283-341] [LIVE L28, L15] VERIFIED |
| Fast tier, SEARCH_OVERVIEW, NATIONALITY_COACH (fast, then basic) | `google/gemma-4-26b-a4b-it:free` → `nvidia/nemotron-3.5-lightning:free` → `thinkingmachines/inkling-small:free` → `google/gemma-4-31b-it:free` | identical | Google AI Studio; Nvidia (nvfp4); Thinking Machines; Google AI Studio | [CODE model_policy.py:99-105] [LIVE L28] VERIFIED |
| Router / translator | `google/gemma-4-31b-it:free` | identical, then the fast chain | Google AI Studio | [CODE model_policy.py:23-24] [LIVE L28] VERIFIED |
| Verifier | `nvidia/nemotron-3-super-120b-a12b:free` | **`openai/gpt-oss-120b:free` first** (env override) | that id is **absent from the OpenRouter catalog today** | [CODE model_policy.py:118] [LIVE L28, L7] VERIFIED [corrected by verifier: the live chain value is OBSERVED (re-fetched 2026-10-19). That an env override causes it is INFERRED: `verifier_model` reads `AI_VERIFIER_MODEL` without the override opt-in gate [CODE model_policy.py:210], and the health endpoint does not list that variable. Also, on origin/main no production code calls `TaskRole.VERIFIER`. `git grep` finds it only in `ai_runtime.py:317` and the health listing, so this chain is declared but unused] |
| ENFORCEMENT_STRUCTURED (Python) | `google/gemma-4-26b-a4b-it:free` → `nvidia/nemotron-3-super-120b-a12b:free` | **`openai/gpt-oss-20b` → `google/gemma-4-31b-it` → `openai/gpt-oss-120b`** (paid ids) | DeepInfra, CoreWeave, Parasail, AkashML and others | [CODE model_policy.py:112-116] [LIVE L28, L15] VERIFIED [verifier: the live chain is re-OBSERVED, and it is really called, from [CODE paradiso_backend.py:8426,8468]. The env-override cause is INFERRED: `OPENROUTER_ENFORCEMENT_MODEL(_CANDIDATES)` is read via `_model_env`, and the opt-in flag is present live, but the health endpoint does not list those variable names] |
| Chinese-language route | `minimax/minimax-m3` → `inclusionai/ling-3.0-flash-sante:free` → `-fin:free` | not reported | both Ling `:free` ids are absent from the catalog | [CODE model_policy.py:120-124] [LIVE L7] VERIFIED |
| Vercel Quick Answer wording (`/api/waymaker/quick-answer`) | `google/gemma-4-31b-it:free` → `openai/gpt-oss-120b:free` → `meta-llama/llama-3.3-70b-instruct:free` | sibling capture L3 shows the same chain | the last two ids are absent from the catalog, so the chain is effectively one model deep | [CODE lib/waymaker-quick-answer-ai.js:18] [LIVE L7] VERIFIED |
| Vercel enforcement AI | `openai/gpt-oss-120b:free` → `nousresearch/hermes-3-llama-3.1-405b:free` → `google/gemma-4-31b-it:free` → `meta-llama/llama-3.3-70b-instruct:free` | not checked | three of the four ids are absent from the catalog | [CODE lib/enforcement-grounded-ai.js:13-18] [LIVE L7] VERIFIED [corrected by verifier: those lib defaults apply only to `api/enforcement/extract.js`. `api/enforcement/analyze.js:7-15` presets ENFORCEMENT_OPENROUTER_MODEL(_CANDIDATES) to `google/gemma-4-31b-it:free` → `openai/gpt-oss-120b:free` when unset, which is also effectively one model deep. `api/enforcement/confirm.js:3` defaults to `google/gemma-4-31b-it:free`. A comment at analyze.js:4-6 says operators may opt into a premium verifier "for example Gemini 3 Flash" through OpenRouter. That would add Google's terms to the path] |
| Groq fallback | `llama-3.1-8b-instant` | configured; `fallback_allowed: false` for `/api/ask` | Groq | [CODE backend/paradiso_backend.py:345,359] [LIVE L28] VERIFIED [corrected by verifier: `/api/nationality-coach` calls Groq whenever GROQ_API_KEY is set and OpenRouter fails, with no opt-in gate [CODE paradiso_backend.py:7792-7798]. That path is live] |
| Ollama fallback | `qwen3:8b` at localhost:11434 | off unless `ENABLE_OLLAMA_FALLBACK` is set | local | [CODE paradiso_backend.py:258-259] VERIFIED |
| NVIDIA NIM scaffold | `nvidia/nemotron-3-ultra-550b-a55b` at `integrate.api.nvidia.com` | `wired_to_api_ask: False`; allowed modes are research and internal_qa; personal data blocked | NVIDIA API Catalog | [CODE backend/services/providers/nvidia_nim.py:12-13,42-43,87-98] [TEST backend/tests/test_nvidia_nim_provider.py (ran: pass)] VERIFIED |

Notes on the table:

- **Stale comment.** A comment says the verifier is gpt-oss and that gpt-oss is in the final chain [CODE paradiso_backend.py:163-165].
  - The code says the verifier is Nemotron Super.
  - The live service uses gpt-oss through an env override.
  - VERIFIED.
- **No first-party frontier APIs.** I found no call to Anthropic, OpenAI's API or the Gemini API.
  - The only mentions are in a regex that strips provider names out of answers [CODE backend/services/knowledge/guard.py:38-39].
  - VERIFIED by grep.
- **Owner's branch.** On `fix/waymaker-qa-2026-10-16`, `inkling:free` is removed from the Basic chain after it returned 403 `model_access_denied` [DOC git show branch:backend/services/model_policy.py] VERIFIED.
  - This reduces the Basic path's exposure to the Thinking Machines terms.
  - It does not change any distillation conclusion. [corrected by verifier: the branch *does* materially change the data-readiness conclusions in sections 0.6-0.7, 4.3 (S3) and 4.7 (G0). (a) On the branch, `visa_manual_2026_09_01_hwp/pdf`, `stay_manual_2026_09_18_hwp/pdf` are `approved` (reviewed_at 2026-10-16), and both 2026-07-31 HWP editions are `superseded` [DOC git show fix/waymaker-qa-2026-10-16:data/manual_approval_index.json] VERIFIED. (b) Commit fd6109b page-maps the 2026.9 Markdown texts into the manual index as direct evidence, and 9bf8849 grounds `/api/ask` in approved excerpts, scoped by procedure and subcode-aware (commit messages, README-ONLY; not run). (c) Commit 52f7f4f adds `scripts/benchmark_waymaker_models.py`, an offline per-model benchmark through the real `/api/ask` handler with deterministic scoring. It is the natural harness for arms A/REF. If merged, G0's first condition may already be met, and S3 must train on the 2026.9 editions rather than 2026-07-31, because 3.3 forbids superseded evidence.]
- **Existing training work.** `experiments/waymaker-gemma4-finetune` is a Colab LoRA/QLoRA wiring experiment [DOC experiments/waymaker-gemma4-finetune/README.md]:
  - placeholder evidence only, not wired to production;
  - 6 training examples and 8 eval examples;
  - Qwen3-1.7B as the default smoke-test model, and `google/gemma-4-12B-it` as the quality-run target. [verifier: the README calls gemma-4-12B-it "gated" and in need of an accepted Gemma licence. The HF API capture shows `gated: false` and an Apache-2.0 licence link for gemma-4-12B-it, 26B-A4B, 31B and E4B [DOC scratchpad/hf/api/google_gemma-4-*.json], so that README line looks stale (README-ONLY). Notebook cell 8 also sets `bnb_4bit_compute_dtype` and `torch_dtype` to bfloat16, not only cell 10's `bf16=True`]
- **Experiment status:**
  - Its validator passes on the samples with 0 errors [TEST scripts/validate_dataset.py (ran: pass)].
  - Not run, INFERRED: the notebook sets `bf16=True` but recommends a free T4 GPU, which has no native bf16. The claim that the run is "green on T4" is README-ONLY.
- **Project policy on training data:**
  - It already rules out fine-tuning on user queries [DOC docs/paradiso_ai_safe_automation_architecture.md:41].
  - It also says future training data may come only from "reviewed, anonymized, approved eval cases" [DOC docs/ai/WAYMAKER_KNOWLEDGE_PLATFORM.md:295]. That rule is a leakage hazard (see 4.6).
  - The golden set is flagged `"is_training_data": false` [CODE backend/data/eval/paradiso_ai_golden_questions.json:4].
  - VERIFIED.

---

## 2. Technique comparison

### 2.0 Working assumption for Artemis / Athena / Hestia (INFERRED)

I found none of the three names anywhere I searched, so I defined them myself:

- the worktree;
- the owner's branch;
- the sibling research notes;
- `~/Downloads`.

The absence was VERIFIED by grep. If these roles mean something else, the parent should remap the fit columns:

- **Artemis**: a small, fast specialist for routing, fact or slot extraction, the Fast tier and Quick Answer wording. Roughly 2-12B dense, or about 3-4B active parameters in a mixture-of-experts model.
- **Athena**: the grounded answer and synthesis model, covering Basic/Pro final answers, legal synthesis and enforcement explanations. Roughly 12-31B, or a teacher-class model.
- **Hestia**: a self-hosted guardian and verifier for claim-to-evidence entailment, citation audit and PII-safe processing. Because it stays on Waymaker's own infrastructure, personal data never goes to a third party.

**Compute classes (INFERRED):**

| Class | Hardware | What fits |
|---|---|---|
| C0 | no GPU (rules or CPU) | — |
| C1 | one 16-24 GB GPU | QLoRA up to about 12B |
| C2 | one 40-80 GB GPU | LoRA at 12-31B, or QLoRA up to about 70B |
| C3 | multi-GPU node | full fine-tuning up to about 30B, or LoRA on large MoE models |
| C4 | cluster | continued pretraining at scale |

### 2.1 Model-training techniques (these change weights)

Data volumes are INFERRED unless a source is cited.

| Technique | What it changes | Data needed / volume | Compute | Main legal-accuracy risk | Fit A / At / H | Now vs later |
|---|---|---|---|---|---|---|
| General SFT (broad instruction data) | General instruction following | 10k-1M general pairs | C2-C3 | Dilutes careful legal behaviour and adds no domain safety | low / low / low | **No.** Instruct base models already have it |
| Task-specific SFT | One task's behaviour, e.g. the 6-section evidence-grounded answer, deferring or asking to clarify | 1-5k reviewed examples per task. QLoRA paper: data quality matters more than size (UNVERIFIED re-read) | C1-C2 | Memorises one edition's facts if the examples contain real facts. The existing experiment rightly uses placeholders [DOC experiments/.../README.md] | high / high / mid | **Later**, after G0 (arm B) |
| Structured-output SFT | Emitting the JSON schema (citations array, uncertainty fields, typed documents) | 1-3k schema-valid examples | C1 | Schema-valid text with wrong content looks authoritative | high / mid / high | Later. Constrained decoding first (2.2) |
| Multilingual SFT | Answer language and register (ko, en, others) | A small multilingual share is enough [WEB arxiv.org/abs/2401.01854] (title VERIFIED; content UNVERIFIED) | C1-C2 | Mistranslating protected terms: status codes, form names, 체류자격 labels | mid / high / low | Later. Glossary-protected translation and kolint first |
| LoRA [WEB arxiv.org/abs/2106.09685] [WEB huggingface.co/docs/peft/main/en/developer_guides/lora] | Low-rank weight deltas; base model frozen | Same as SFT | C1-C2 | Learns less but also forgets less than full fine-tuning [WEB arxiv.org/abs/2405.09673] VERIFIED. That trade-off suits behaviour-only tuning | high / high / high | Default PEFT method once training starts |
| QLoRA [WEB arxiv.org/abs/2305.14314] | LoRA on top of a frozen 4-bit NF4 base model | Same | C1 | Slightly less accurate than 16-bit LoRA [WEB unsloth.ai/docs/get-started/fine-tuning-llms-guide/lora-hyperparameters-guide] VERIFIED. Korean degradation needs its own check (see quantisation) | high / high / mid | Default for arms B and C, for budget reasons |
| Adapter specialisation and composition (per-scope LoRA; LoraHub [WEB arxiv.org/abs/2307.13269]; AdapterFusion [WEB arxiv.org/abs/2005.00247]; multi-LoRA serving: S-LoRA [WEB arxiv.org/abs/2311.03285], [WEB docs.vllm.ai/en/latest/features/lora.html]) | Separate adapters (e.g. visa issuance vs stay procedures, or ko vs en wording), chosen per request | 1-3k examples per adapter | C1 per adapter | Composing adapters can blend procedure scopes, which CLAUDE.md forbids. Pick adapters deterministically and never merge them | mid / high / mid | Later. Hard routing by procedure scope is attractive |
| Full fine-tuning | All weights | 10k+ | C3 | More capacity to memorise statute text, and more forgetting | low / low / low | **No** |
| Domain-adaptive or continued pretraining [WEB arxiv.org/abs/2004.10964], [WEB arxiv.org/abs/2403.08763]; legal example: SaulLM [WEB arxiv.org/abs/2403.03883] | The model's language prior over the domain | 100M-10B+ tokens of Korean legal text | C3-C4 | **Worst fit.** It bakes one law snapshot into the prior, and the corpus (statutes plus 7 manual editions) is small and changes over time | none / none / none | **No** |
| Response (sequence-level) distillation [WEB arxiv.org/abs/1606.07947] | The student imitates the teacher's text | 5-20k teacher responses, filtered | C1-C2 | Imitation copies style, not factuality [WEB arxiv.org/abs/2305.15717] VERIFIED. It passes teacher errors on; commercial legal RAG tools still hallucinate 17-33% of the time [WEB arxiv.org/abs/2405.20362] VERIFIED | high / mid / mid | Later, and **only with verified outputs** (arm C) |
| Logit-based KD [WEB arxiv.org/abs/1503.02531] | The student matches the teacher's token distribution | Teacher logits over the same tokens | C2-C3 (teacher forward passes) | Impossible through APIs, which do not return full logits. TRL's trainer also requires teacher and student to share a vocabulary [WEB huggingface.co/docs/trl/distillation_trainer] VERIFIED, so Nemotron cannot teach Gemma [corrected by verifier: true only of `DistillationTrainer`. The docs say the teacher "must share the student's vocabulary". But TRL v1.16.0 also ships the experimental `trl.experimental.gold.GOLDTrainer`, which does cross-tokenizer logit distillation (ULD with span alignment). It inherits GKD's on-policy mixing and runs mixed families, e.g. a Qwen teacher with a Llama student [WEB https://huggingface.co/docs/trl/gold_trainer, accessed 2026-10-19] VERIFIED. A self-hosted Nemotron → Gemma pair is therefore *possible*, not impossible. Caveat: GOLD advises `use_extended_uld=False` for SentencePiece-style tokenizers, so alignment quality for a Gemma student is weaker and unmeasured (INFERRED). API teachers stay response-level only. Paid OpenRouter gpt-oss endpoints expose only `top_logprobs` [DOC td_raw/openrouter_models_subset.json], not full distributions] | low / low / low | Only within one model family (e.g. Gemma 4 31B to Gemma 4 E4B), self-hosted [verifier: or cross-family via the experimental GOLD trainer, self-hosted] |
| On-policy distillation (GKD [WEB arxiv.org/abs/2306.13649]; MiniLLM [WEB arxiv.org/abs/2306.08543]; TRL `DistillationTrainer` / `GKDTrainer` [WEB huggingface.co/docs/trl/gkd_trainer]) | The student generates; the teacher scores each token (generalised JSD; `beta` from 0 to 1 moves between forward and reverse KL) | Prompts only | C2-C3 | Same shared-vocabulary constraint [corrected by verifier: GOLDTrainer (experimental) lifts it, see the row above; `AsyncDistillationTrainer` can score against a teacher served over HTTP, which must still be a self-hosted server returning logprobs]. The teacher's distribution includes its legal errors | mid / mid / low | Later, same family, self-hosted only |
| Task-specific distillation, e.g. distilling step-by-step [WEB arxiv.org/abs/2305.02301] | The student learns labels plus rationales for one task | 1-10k | C1 | The rationales are legal reasoning the teacher made up, and asking for them invites private-CoT requests, which section 3 forbids | high (extractor) / low / mid | Later, for extraction tasks only, with visible rationales that quote the evidence |
| Multi-teacher distillation (survey [WEB arxiv.org/abs/2402.13116]) | Labels from teacher consensus or the best teacher | 2-4 teachers × prompts | C1-C2 + API | Teachers agreeing does not make an answer legally true; they share training-data biases | mid / mid / high (verifier ensembles) | Later. Use disagreement to send items to human review, not to vote on gold labels |
| Structured reasoning supervision (process supervision [WEB arxiv.org/abs/2305.20050]; RAFT-style evidence quoting [WEB arxiv.org/abs/2403.10131] VERIFIED) | Teaches visible steps: quote evidence → map it to a claim → conclude or abstain | 1-5k annotated traces | C1-C2 | Steps can look grounded without being grounded. Requiring each quote to be a verbatim substring of the evidence pack makes this checkable | mid / **high** / high | Later. The best training lever for Athena (RAFT teaches the model to ignore distractors and cite the exact span) |
| DPO [WEB arxiv.org/abs/2305.18290] [WEB huggingface.co/docs/trl/dpo_trainer] | Preference between a chosen and a rejected answer | 1-10k pairs, where the rejected answer has a real critical error (invented fee, scope mix) | C1-C2 | Can learn to prefer a confident style. The two answers must differ in correctness, not tone | mid / high / mid | Later, after SFT. Strong for "abstaining beats inventing" |
| ORPO [WEB arxiv.org/abs/2403.07691] [WEB huggingface.co/docs/trl/orpo_trainer] | SFT and preference learning in one stage, with no reference model | Same pairs | C1 | Same as DPO, and harder to diagnose | mid / mid / low | Optional alternative to SFT followed by DPO when compute is tight |
| KTO [WEB arxiv.org/abs/2402.01306] [WEB huggingface.co/docs/trl/kto_trainer] | Learns from unpaired good/bad labels | Binary labels. These fit Waymaker's fixed feedback reasons (INCORRECT, OUTDATED, …) [DOC docs/ai/WAYMAKER_KNOWLEDGE_PLATFORM.md:288-294] | C1 | A user's "INCORRECT" may itself be wrong. Use it only after a reviewer confirms it | low / mid / mid | Justified **later**, because Knowledge Studio produces exactly this kind of unpaired reviewed label |
| SimPO [WEB arxiv.org/abs/2405.14734] | Preference learning with no reference model and length normalisation | Pairs | C1 | Length normalisation may reward short answers that drop cautions | low / low / low | Not justified now |
| RL with verifiable rewards (GRPO [WEB arxiv.org/abs/2402.03300]; R1 [WEB arxiv.org/abs/2501.12948]; Tülu 3 RLVR [WEB arxiv.org/abs/2411.15124]; TRL GRPO accepts custom Python reward functions and vLLM generation [WEB huggingface.co/docs/trl/grpo_trainer] VERIFIED) | Optimises the policy against rewards computed by code | Prompts plus evidence packs; rewards are code | C2-C3 | Reward hacking, e.g. always abstaining or always citing the first chunk. RLVR mostly sharpens what the base model can already do [WEB arxiv.org/abs/2504.13837] VERIFIED | mid / high / low | **Later.** Waymaker's answers are unusually easy to check by code (section 4.4) |
| Model merging (task arithmetic [WEB arxiv.org/abs/2212.04089]; TIES [WEB arxiv.org/abs/2306.01708]; DARE [WEB arxiv.org/abs/2311.03099]; mergekit [WEB arxiv.org/abs/2403.13257]; [WEB huggingface.co/docs/peft/main/en/developer_guides/model_merging]) | Combines weight deltas | Two or more adapters | C0-C1 | Unpredictable interference; can bring back a superseded adapter's behaviour; hard to audit | low / low / low | No, unless an eval proves it |

### 2.2 Retrieval, inference and orchestration techniques (weights unchanged)

| Technique | What it changes | Needs | Legal-accuracy effect | Fit | Now vs later |
|---|---|---|---|---|---|
| RAG with edition-aware evidence packs [WEB arxiv.org/abs/2005.11401] | What the model sees per request | An approved, sectioned corpus with effective dates. Today the index has 0 direct-evidence chunks [LIVE, sibling capture] | The only way to keep up with 7 editions in 4.5 months. RAG beats fine-tuning for new knowledge [WEB arxiv.org/abs/2312.05934] VERIFIED | all | **Now. Top priority** |
| Retrieval quality: law search recall, effective-date (`efYd`) filters, precedent body search | Recall and currency | Code changes in law_tools and precedent_sources | Sibling notes say law search matches names only and never sends `efYd` [DOC research/law-stack.md:52,62] (sibling, UNVERIFIED by me) | At, H | **Now** |
| Tool-augmented reasoning (ReAct [WEB arxiv.org/abs/2210.03629]; Toolformer [WEB arxiv.org/abs/2302.04761]; Waymaker's own registry: `lookup_status`, `calculate_deadline`, `search_law` …) | The model calls deterministic tools | The registry exists, but `/api/ask` does not call it [DOC research/ai-lifecycle.md:113] (sibling) | Deadlines, codes and fees come from code, not from weights | At | Now. Wire up the tools that already exist |
| Deterministic validators: Quick Answer's `validateEnhancement`, plus the citation and statute guards | Accepts or rejects model text | Already present [CODE assets/js/waymaker-quick-answer.js:290-322] [TEST scripts/check_waymaker_quick_answer.mjs (ran: pass, 23 checks)] [TEST backend/tests/test_statute_citation_guard.py (ran: pass)] | Blocks invented numbers, offices, overclaims and unconditional exemptions, whatever model is used | all | **Now. Extend to `/api/ask`** |
| Constrained decoding / structured outputs (XGrammar [WEB arxiv.org/abs/2411.15100]; vLLM structured outputs [WEB docs.vllm.ai/en/latest/features/structured_outputs.html]) | Guarantees valid syntax | A JSON schema | Makes structured-output SFT unnecessary for syntax. Content still needs validators | A, H | Now when self-hosting. Today the Quick Answer call uses `response_format` [CODE lib/waymaker-quick-answer-ai.js:136] [corrected by verifier: line 131] |
| Model routing (deterministic today [CODE model_policy.py:234-295] [TEST backend/tests/test_model_policy.py (ran: pass)]; learned routers: RouteLLM [WEB arxiv.org/abs/2406.18665], FrugalGPT [WEB arxiv.org/abs/2305.05176]) | Which model answers | Labelled difficulty data, for a learned router | The current deterministic escalation from Fast to Basic on risky issue types is auditable; a learned router is not | A | Keep it deterministic. Add a learned router later only as an extra escalation signal |
| Quantisation (GPTQ [WEB arxiv.org/abs/2210.17323]; AWQ [WEB arxiv.org/abs/2306.00978]; Gemma 4 QAT checkpoints [DOC scratchpad/hf/s_author_google_search_gemma-4.json] (sibling capture)) | Weight precision at inference | Korean calibration data | Non-Latin-script languages suffer most, and automatic metrics understate the damage. For Japanese the paper reports about a 1.7% drop on automatic tasks but about 16% in human evaluation [WEB arxiv.org/abs/2407.03211] VERIFIED | A, H | Later, gated on a Korean human eval |
| Efficient inference (vLLM PagedAttention [WEB arxiv.org/abs/2309.06180]; speculative decoding [WEB arxiv.org/abs/2211.17192]; multi-LoRA serving) | Latency and cost | A self-hosted GPU | Neutral as long as outputs are identical (speculative decoding is lossless by design) | all | Later, once self-hosting |
| Verifier / judge (Hestia) | A second pass checks each claim against the evidence | Claim extraction plus entailment; can start as a prompted open model | Catches unsupported claims before they are shown | H | Now as a prompted, self-hostable model; a distilled verifier later |

**Why facts must stay out of the weights (INFERRED from the evidence above):**

- In Waymaker, facts live in versioned sources.
  - Seven stay-manual editions took effect between 2026-05-01 and 2026-09-18.
  - Two editions are currently approved: the 2026-07-31 visa and stay HWP files [CODE data/manual_approval_index.json].
- Some techniques write facts into the weights:
  - continued pretraining;
  - full fine-tuning;
  - SFT or distillation on answers that state real facts without the evidence in the prompt.
- Each of these freezes a snapshot that expires within weeks and cannot cite where its facts came from.
- Unsloth's guide claims fine-tuning "can replicate" RAG [WEB unsloth.ai/docs/get-started/fine-tuning-llms-guide]. This is a README-ONLY vendor claim.
  - For law that keeps changing, the Gekhman and Ovadia results above show the claim is wrong.
- Every training arm below therefore puts the evidence pack in the prompt, and scores answers on whether they follow it.

---

## 3. Distillation policy

### 3.1 Clauses on using outputs to train other models

All clauses are paraphrased and were accessed on 2026-10-19.

| # | Provider / licence (channel Waymaker uses) | Clause, paraphrased (section) | Source | Verdict for distilling a Waymaker student |
|---|---|---|---|---|
| 1 | **OpenRouter** ToS, last updated 2026-08-31 (carries all LLM traffic) | §5: users must comply with each model's own terms ("Model Terms"); who owns the output is set by those terms. §6.1: some models may train on inputs; OpenRouter opts out "where possible". §7: users may not resell API access or build a competing service. There is no separate ban on training with outputs. | [WEB https://openrouter.ai/terms] [LIVE L1] VERIFIED | **Pass-through.** The upstream provider's terms decide (rows 2, 4, 6, 7) |
| 2 | **NVIDIA API Trial ToS** (PDF metadata date 2025-10-07) [corrected by verifier: the document's own footer reads "v. September 19, 2025"; the captured text also has §3.3(iv), under which NVIDIA collects User and Generated Content to improve its products and AI models, and §1.4, under which production needs a Subscription]. It covers OpenRouter's `nvidia/*:free` models and is the NIM scaffold's endpoint | §1.2, verbatim: "for limited trial purposes only and without use of the API Service or Generated Content in production". §4.2: Generated Content may not be copied, transferred or distributed. §4.3: no personal information. §4.12: Generated Content may not be used to develop or improve products that compete with the API Service. | [WEB https://assets.ngc.nvidia.com/products/api-catalog/legal/NVIDIA%20API%20Trial%20Terms%20of%20Service.pdf]. OpenRouter links this document as the "Nvidia" provider's ToS [LIVE L16] [LIVE L14] VERIFIED | **Not permitted.** Building production training data from trial Generated Content conflicts with §1.2 and §4.2. Internal research use only, and that REQUIRES LEGAL REVIEW |
| 3a | **OpenMDW-1.1**: weights of Nemotron 3 Ultra 550B-A55B and Nemotron 3.5 Lightning 30B-A3B | Lets users deal in the model materials without restriction, and places no restriction or obligation on using, modifying or sharing outputs. Redistributed copies must keep the licence and notices. Suing over patents or copyright ends the licence. | [WEB https://openmdw.ai/license/1-1/] (site licensed CC-BY-4.0) [LIVE L8, L9] VERIFIED | **Permitted** with self-hosted weights, or on a host whose ToS allows it. Keep the notices if weights are redistributed |
| 3b | **NVIDIA Nemotron Open Model License** (last modified 2025-12-15): weights of Nemotron 3 Super 120B-A12B | The works are commercially usable. Derivative Works may be created and distributed. NVIDIA claims no ownership of outputs. Redistribution needs a copy of the licence and a notice line. Litigation ends the licence. | [WEB https://www.nvidia.com/en-us/agreements/enterprise-software/nvidia-nemotron-open-model-license/] [LIVE L10] VERIFIED | **Permitted** (self-hosted or on a permitted host), with notices |
| 4 | **Google Gemini API Additional Terms** (effective 2026-03-23; page updated 2026-04-28). Google AI Studio serves OpenRouter's `google/gemma-4-*:free` | Use Restrictions: the Services may not be used to develop models that compete with them, and no part of them may be reverse engineered, extracted or replicated. Unpaid Services: Google uses content to improve its products, human reviewers may read inputs and outputs, and users must not submit personal information. Grounded results may not be used for training. | [WEB https://ai.google.dev/gemini-api/terms] [LIVE L4] VERIFIED. OpenRouter lists `cloud.google.com/terms` as this provider's ToS [LIVE L16] | Gemini models as teacher: **REQUIRES LEGAL REVIEW.** A narrow domain student is arguably not a competitor, but the extract/replicate wording is broad. Gemma via AI Studio: avoid; self-host Gemma instead |
| 5a | **Gemma 4 licence: Apache-2.0** (31B, 26B-A4B, 12B, E4B, E2B) | The page titled "Apache License 2.0 · Gemma" carries the standard Apache-2.0 text. The HF model cards say `apache-2.0`. | [WEB https://ai.google.dev/gemma/docs/gemma_4_license] [LIVE L5]; HF card fields [DOC scratchpad/hf/api/google_gemma-4-*.json] (sibling capture) VERIFIED | **Permitted** (self-hosted). Keep the Apache NOTICE and attribution when redistributing |
| 5b | **Gemma Terms of Use** for Gemma 1-3 (updated 2026-04-01) | §1(e): "Model Derivatives" include any model built by transferring patterns from Gemma's outputs, explicitly including distillation through synthetic data. The outputs themselves are not Model Derivatives. | [WEB https://ai.google.dev/gemma/terms] [LIVE L6] VERIFIED | If Gemma 1-3 is the teacher, the student becomes a Model Derivative bound by Gemma's use restrictions. **Prefer Gemma 4** |
| 6 | **Thinking Machines Free Research API Tier ToS** (last updated 2026-08-20). It serves OpenRouter's `thinkingmachines/inkling*:free` | Acceptable use: without written consent, users may not develop, train, fine-tune, distil or materially improve a competing model or service, nor systematically collect outputs to build such datasets. Users grant TML a perpetual licence to keep and use prompts and outputs, including to train TML's and other models. No personal, children's or sensitive data. Weights may not be obtained or trained through the API. | [WEB https://thinkingmachines.ai/legal/tml-free-research-api-tier-terms-of-service.pdf] [LIVE L17] VERIFIED | **API channel not permitted.** The Inkling weights are Apache-2.0 [LIVE L8], so self-hosting them is permitted |
| 7 | **OpenAI Services Agreement** "ONLINE v. 010126" (CDN copy) | §3.3(e): Output may not be used to develop AI models that compete with OpenAI's products. The only "Permitted Exception" covers internal, non-distributed classifiers or embedding models, and fine-tuning OpenAI's own models. §3.3(f): no extracting data outside the Services. | [WEB https://cdn.openai.com/osa/openai-services-agreement.pdf] [LIVE L19] VERIFIED. The openai.com policy pages returned **HTTP 403** to WebFetch [LIVE L18] | **Not permitted** for a generative student. A non-distributed internal classifier may fit the exception; REQUIRES LEGAL REVIEW [verifier note: the OpenAI §3.3(e), Anthropic §D.4 and Gemini "compete with the Services" clauses are all scoped to *competing* models. The notes call OpenAI and Anthropic "not permitted" but Gemini "REQUIRES LEGAL REVIEW". "Not permitted" is a sound conservative policy for all three, but whether a Korean-immigration domain student "competes" is the same open legal question in each. Treat all three consistently] |
| 8 | **gpt-oss-20b/120b** weights: Apache-2.0 plus the gpt-oss usage policy | Apache-2.0 permits use, modification and distribution. The usage policy asks for safe, responsible use that complies with applicable law. | [LIVE L8] (HF `apache-2.0`); [WEB https://raw.githubusercontent.com/openai/gpt-oss/main/USAGE_POLICY] [LIVE L23] VERIFIED | **Permitted** when self-hosted. The 120B model fits on one 80 GB GPU using MXFP4 [WEB https://huggingface.co/openai/gpt-oss-120b] [LIVE L31] VERIFIED. Paid OpenRouter hosts (DeepInfra, CoreWeave, Parasail, AkashML …) add their own ToS, which I did not review: REQUIRES LEGAL REVIEW for each host |
| 9 | **Anthropic Commercial Terms** (effective 2025-06-17) and **Consumer Terms** (effective 2025-10-08; the Korean version was served) | Commercial §D.4: no accessing the Services to build a competing product, including training competing AI models, unless Anthropic approves; no reverse engineering. Consumer §3: no developing competing products, including developing or training AI/ML models. | [WEB https://www.anthropic.com/legal/commercial-terms] [WEB https://www.anthropic.com/legal/consumer-terms] [LIVE L2, L3] VERIFIED | **Not permitted** without express approval. Waymaker does not use Anthropic today |
| 10 | **Groq Services Agreement** (last modified 2026-06-22). Third-party model terms govern use of each model | §6.3(e): the Cloud Services may not be used to develop similar or competing offerings. §4.1: each model's own terms control its use. Outputs are Customer Data, and Groq does not train on them. | [WEB https://console.groq.com/docs/legal/services-agreement] [LIVE L20] VERIFIED | **Permitted, subject to the Llama licence** (row 11). A domain student does not compete with an inference cloud (INFERRED); light legal review |
| 11 | **Llama 3.1 / 3.3 Community License** (Groq `llama-3.1-8b-instant`; Vercel `llama-3.3-70b:free`; Hermes 3 is tagged `llama3`) | §1.b.i: if Llama outputs are used to create or improve an AI model that is then distributed or made available, the model's name must start with "Llama". Also required: a "Built with Llama" notice and compliance with the AUP. A clause covers services with over 700M monthly users. | [WEB https://raw.githubusercontent.com/meta-llama/llama-models/main/models/llama3_3/LICENSE] [LIVE L21] VERIFIED; Llama 3.1 text [DOC scratchpad/hf/lic2/meta-llama_Llama-3.1-8B-Instruct__LICENSE:39-58] (sibling capture) VERIFIED. The llama.com licence URL returned 404 [LIVE L12] | **Permitted with conditions:** the name prefix if the student is made available, attribution, and the AUP |
| 12 | **Qwen** (Ollama's `qwen3:8b`; Qwen3.5/3.6/3.8 open weights) | Apache-2.0 [corrected by verifier: not for all of Qwen3.8. `Qwen3.8-27B` is apache-2.0, but `Qwen3.8-2.4T-A95B` is `other`/`qwen3.8-max` and `Qwen3.8-Flash-Next` is `other`/`qwen-community-1.0` [DOC scratchpad/hf/api/Qwen_Qwen3.8-*.json cardData]. Qwen3-8B apache-2.0 re-confirmed via HF API 2026-10-19] | [LIVE L8] for Qwen3-8B; Qwen3.5/3.6/3.8 [DOC scratchpad/hf/api/Qwen_*.json] (sibling) VERIFIED | Licence: **permitted**. **Conflicts with product policy**, which reserves `qwen/` for Chinese routes [CODE model_policy.py:129-131]. The owner must decide |
| 13 | **DeepSeek** (V3.2, V4, V4.1 Flash; R1) | MIT. The R1 model card explicitly allows derivative works, including distillation to train other LLMs. | [WEB https://huggingface.co/deepseek-ai/DeepSeek-R1] [LIVE L22] VERIFIED; V3.2/V4 are `mit` [DOC sibling HF capture] | Licence: **permitted**. Same product-policy conflict (`deepseek/`). I did not review the DeepSeek API ToS |
| 14 | **MiniMax M3** (`minimax/minimax-m3`, Chinese route) | MiniMax Community License: the grant covers non-commercial use only. Commercial use requires a "Built with MiniMax M3" notice and either a one-off notice or prior authorisation (authorisation above US$20M yearly revenue). Commercial use explicitly includes deploying post-trained or fine-tuned derivatives. The prohibited uses include discrimination based on immigration status. | [DOC scratchpad/hf/lic2/MiniMaxAI_MiniMax-M3__LICENSE:3-17] (sibling capture of the HF LICENSE file) VERIFIED. The MiniMax platform ToS redirected (307) to a JavaScript-only page with no retrievable text [LIVE L24] | **Not permitted** as a teacher without written terms from MiniMax. Whether a distilled student counts as a "derivative work" REQUIRES LEGAL REVIEW [corrected by verifier: the licence text itself allows commercial use under US$20M yearly revenue with a "Built with MiniMax M3" notice and a one-time notice email; prior written authorisation is needed only above that threshold [DOC hf/lic2/MiniMaxAI_MiniMax-M3__LICENSE:2-8]. The grant sentence names non-commercial purposes while clause 2 provides for commercial use, so the drafting is internally ambiguous. "Not permitted" is a conservative policy choice, not what the licence says: REQUIRES LEGAL REVIEW. The licence does not mention outputs] |
| 15 | **InclusionAI Ling 3.0 Flash** | MIT (HF `mit`) | [LIVE L13] VERIFIED | The licence permits it. The configured `:free` ids are missing from the catalog, and policy reserves this family for Chinese routes |

### 3.2 Decision rule

A teacher is permissible only if **all three** of these say yes:

1. **Weights licence or provider terms.** The weights licence (or, for a closed model, the provider's terms) allows its outputs to train a student that is distributed or used commercially.
2. **Serving channel.** The terms of the channel actually used allow:
   - production use, retention and redistribution of outputs;
   - the kind of data sent to it.
   Rows 2, 4 and 6 show that a channel can forbid what the licence allows.
3. **Waymaker's policy.** Waymaker's own model policy accepts the model family [CODE model_policy.py:126-131].

**Provenance.** Every distilled example must carry:
- teacher id and weights licence id;
- serving host, plus its ToS URL and version date;
- request date;
- prompt hash and evidence-pack hash.

Without this record, the dataset cannot be audited.

### 3.3 Conclusion

**Permissible**, with the condition after each:

| Teacher | Condition |
|---|---|
| gpt-oss-120b/20b, self-hosted | Apache-2.0 notice |
| Nemotron 3 Ultra and 3.5 Lightning, self-hosted | OpenMDW notices |
| Nemotron 3 Super, self-hosted | Nemotron OML notice line |
| Gemma 4 31B/26B-A4B, self-hosted | Apache-2.0 |
| Inkling, self-hosted | Apache-2.0 |
| Llama 3.1/3.3 | "Llama" name prefix if the student is made available; "Built with Llama"; AUP |

- Self-hosting Inkling (975B total parameters) or Nemotron Ultra (550B) needs C3-C4 hardware (INFERRED).
- The practical first teachers are therefore gpt-oss-120b (one 80 GB GPU) and Gemma 4 31B.

**Not permissible:**
- OpenAI API (§3.3(e));
- Anthropic API (§D.4);
- the Thinking Machines free API tier;
- NVIDIA API Trial endpoints, including OpenRouter's `nvidia/*:free` routes and the NIM scaffold;
- MiniMax M3 for commercial use [corrected by verifier: move to REQUIRES LEGAL REVIEW; see the row 14 correction];
- Gemma 1-3, unless the student accepts the Gemma Terms.

**REQUIRES LEGAL REVIEW:**
- Gemini API and Google AI Studio.
- The ToS of every paid OpenRouter host.
- Qwen and DeepSeek: the licence allows them, but Waymaker's policy does not.
- Any reuse of production logs as training prompts.
  - User questions may contain personal data.
  - Repurposing them for training needs a lawful basis under Korea's PIPA. INFERRED; this note draws no legal conclusion.
  - Current policy already forbids fine-tuning on user queries [DOC docs/paradiso_ai_safe_automation_architecture.md:41].

**Production-path side finding (critical, REQUIRES LEGAL REVIEW):**
- `/api/ask` sends real user questions to production through:
  - a primary Basic model served under trial-only terms that ban personal data (row 2);
  - Basic and Fast fallbacks that include a research tier which bans personal data and takes a perpetual training licence (row 6);
  - Gemma routes on an unpaid tier where human reviewers may read traffic (row 4).

**Mandatory rules for any distillation run:**
- **Never request private chain-of-thought.**
  - Disable reasoning traces. The NIM scaffold already keeps `reasoning_enabled` false by default [CODE nvidia_nim.py:41].
  - Request only the final structured answer plus verbatim evidence quotes.
- **A teacher's legal conclusions are never gold labels.** They become training targets only after both:
  - the deterministic checks in 4.4 pass;
  - human legal review: at least a stratified sample, and 100% of high-risk issue types.
- **Teachers see evidence packs from approved editions only.**
  - Never superseded editions.
  - The one exception is a deliberately labelled case testing that a stale edition gets flagged.

---

## 4. Experiment design

### 4.1 Hypotheses

- **H1 (behaviour, not facts).**
  - Compared with the same untuned base model given the same evidence packs, SFT+QLoRA on reviewed, evidence-conditioned examples:
    - lowers the rate of critical legal errors (CLE);
    - raises correct abstention.
- **H2 (verified distillation).**
  - Adding teacher responses that passed the deterministic verifier and human review (arm C) beats arm B at equal training tokens.
  - The reason: C sees more varied phrasings of the same verified behaviour.
- **H3 (no memorisation).**
  - Neither B nor C gets worse at tracking evidence.
  - When the evidence changes (counterfactual numbers, or a newer edition), their answers follow it at least as reliably as untuned A.
- **H4 (a small student is viable).**
  - A tuned 12B student (an Artemis or Athena candidate) matches the production chain's CLE rate.
  - It does so at lower latency and without sending data to third parties.
- **H0 (null).**
  - Better retrieval plus validators, with an untuned model, closes most of the gap.
  - This is tested by arm A+.

### 4.2 Arms and baselines

All arms share these settings:

- **Student base:** the Apache-2.0 `google/gemma-4-12B-it`, the existing quality-run target [DOC experiments/.../README.md]. `gemma-4-26B-A4B-it` is an optional second student for Athena.
- **Identical inputs:** the same prompt template and the same evidence packs.
- **Identical decoding:** temperature 0.2, matching the production wording call [CODE lib/waymaker-quick-answer-ai.js:136] [corrected by verifier: line 131].
- **Identical output format:** the same JSON schema, with constrained decoding.

| Arm | Definition | Training data | Notes |
|---|---|---|---|
| **B0** | Deterministic only: structured answer plus Quick Answer, no LLM | none | Floor for CLE (invented facts should be about 0) and ceiling for unhelpfulness |
| **A** | Untuned Gemma 4 12B-it plus the evidence pack | none | Main control |
| **A+** | A plus the retrieval and validator improvements in section 5 | none | Tests H0 |
| **REF** | The current production chain (Nemotron 3 Ultra …) on the eval set | none | Reference only. Evaluation is not production use, but the trial terms still bar personal data, so eval items must be synthetic or scrubbed. REQUIRES LEGAL REVIEW |
| **B** | SFT+QLoRA. Settings: NF4; r=16; alpha=32; all linear projections; lr 2e-4; 1-3 epochs; loss on assistant tokens only. Sources: [WEB unsloth.ai/docs/.../lora-hyperparameters-guide] and [WEB huggingface.co/docs/trl/sft_trainer]; the TRL options `assistant_only_loss` and `completion_only_loss` are VERIFIED | 1,500-3,000 examples written or corrected by humans | Same token budget as C |
| **C** | Verified response distillation plus SFT. Steps: (1) permissible teachers (gpt-oss-120b and Gemma 4 31B, self-hosted) answer the training prompts with evidence; (2) the 4.4 verifier filters their answers; (3) humans review them; (4) the survivors are mixed with B's gold data, e.g. 1:1 | 5-20k teacher candidates. If 30-60% pass (INFERRED), 3-10k are kept | Subsampled to the same steps and tokens as B |

**Controls:**
- 3 seeds per arm;
- identical tokenizer and chat template;
- results reported as mean ± 95% bootstrap CI.

**Optional arm C-DPO:** preference pairs that set a verifier-failed answer against a verifier-passed answer to the same prompt.

### 4.3 Evaluation splits

| Split | How it is built | What it tests |
|---|---|---|
| S1 in-distribution | Random hold-out by **case template**, not by individual example | Basic quality |
| S2 status-family hold-out | Leave every case of, e.g., F-6 and G-1-5 out of training | Generalisation without memorising specific codes. G-1-5 must not inherit G-1's rules [DOC CLAUDE.md "Code hierarchy"] |
| S3 edition shift | Train on evidence from the approved 2026-07-31 editions. Test on the 2026-09-01 and 2026-09-18 editions wherever a fact changed [CODE data/manual_approval_index.json:278] [corrected by verifier: the 2026-09-18 effective date is at line 280; the change summaries are at lines 209, 234 and 297. On the owner's branch the 2026-07-31 editions are `superseded` and the 2026.9 editions `approved`. Once that merges, invert S3: train on 2026.9 and keep 2026-07-31 → 2026.9 diffs only as labelled stale-edition probes] | Whether the answer follows the newer evidence |
| S4 counterfactual evidence | Alter fees, day counts and document names inside the evidence pack | A direct probe for memorisation: the answer must track the change |
| S5 insufficient evidence | Remove the decisive passage | Abstention recall |
| S6 adversarial | Overclaim bait; parent/subcode bait; visa-vs-stay scope bait; prompt injection inside evidence; distractor passages (RAFT-style) | Robustness |
| S7 language | ko, en, mixed script, plus the user base's other languages (INFERRED; the list needs confirming) | Register and protected-term integrity (kolint `--genre ux`) |
| Frozen sets | Golden 50 (`is_training_data: false`) [corrected by verifier: the same file also sets `"is_llm_eval": false`. Its 50 items test the deterministic routing helpers and carry `expected_task_type`, `expected_risk_level`, `expected_grounding_status`, `expected_must_include_metadata` and `expected_must_not_include_terms`, with no reference answer or evidence pack [CODE backend/data/eval/paradiso_ai_golden_questions.json:4-12]. It can serve as LLM *prompts* with must-not-include checks, as the owner's branch benchmark does, but it cannot score CLE until reference answers and evidence are added]; the 19 seed cases [DOC docs/ai/WAYMAKER_KNOWLEDGE_PLATFORM.md:299-303]; the 17 scenario cases [CODE backend/data/eval/scenario_grounding_audit_cases_2026_06.json] | Never trained on, never shown to teachers |

**Minimum size (INFERRED):**
- at least 600 scored items, with at least 50 per S-split;
- that is enough to separate CLE-rate differences of a few points;
- high-risk issue types are oversampled.

### 4.4 Deterministic verifier

The verifier is code, not a model. It plays three roles:

- filter for arm C;
- reward for later RLVR;
- metric for every arm.

Checks:

1. Every cited source id and span appears verbatim in the evidence pack.
2. Every number, amount, period, form id and office name in the answer appears in the evidence. This reuses the logic of `validateEnhancement` [CODE assets/js/waymaker-quick-answer.js:290-322].
3. Status codes parse with the pattern used in `sanitizeModel` [CODE lib/waymaker-quick-answer-ai.js:52] [corrected by verifier: the status pattern is at line 56]. A rule specific to a subcode is never stated for its parent code.
4. The procedure scope of every cited source (visa issuance or stay) matches the scope of the question. Scope comes from the source registry.
5. No overclaim or guarantee wording appears, and the disclaimers and uncertainty notices are present (see `eval_outputs.py` [CODE experiments/.../scripts/eval_outputs.py]).
6. When the evidence is insufficient, the answer abstains or asks a clarifying question.
7. The output is schema-valid.

Human legal review then covers what code cannot check:
- whether the interpretation is correct;
- whether the answer is complete enough to act on.

### 4.5 Critical legal error taxonomy

| Code | Error | Example | Checked automatically? |
|---|---|---|---|
| CLE-1 | Invented requirement (document, fee, period, eligibility) | A required document that is not in the evidence | yes (check 2) |
| CLE-2 | Number contradicts the evidence | Says 30 days where the evidence says 15 | yes (check 2) |
| CLE-3 | Procedure scopes mixed | Lists visa-issuance attachments for an extension | yes (check 4) |
| CLE-4 | Hierarchy error | Applies a G-1-5 rule to G-1, or treats G-1-5 as top-level | partly (check 3) |
| CLE-5 | Stale-edition claim | States a superseded rule instead of the evidence's edition | yes, on S3/S4 |
| CLE-6 | False permission or guarantee | "Allowed without prior permission" when permission is required; absolute wording | partly (check 5) plus human review |
| CLE-7 | Missed risk or deadline warning | Overstay, a reporting deadline or a fine is not mentioned | human review plus rules |
| CLE-8 | Fabricated or mismatched citation | Cites an article or page that is not in the evidence, or that does not support the claim | yes (check 1) plus entailment |
| CLE-9 | Failure to abstain | Answers decisively on S5 | yes (check 6) |
| CLE-10 | Disclaimer or uncertainty removed | Drops a review-needed warning | yes (check 5) |
| CLE-11 | Protected term corrupted | A status code, form name or statute citation is changed in translation | yes (kolint protection plus regex) |

Non-critical failures (style, length, over-abstention) are tracked but do not block a run.

### 4.6 Leakage prevention

- **Split units.** Split by case template and evidence section, never by individual example.
- **Deduplication.** Dedupe training data against eval data using exact hashes plus n-gram or MinHash near-duplicate detection. Apply it to **both** questions and evidence passages.
- **Frozen eval set.**
  - Commit a hash manifest of the eval set.
  - Teachers never see eval prompts.
- **Doc conflict to resolve.**
  - The docs currently say training candidates come only from approved eval cases [DOC docs/ai/WAYMAKER_KNOWLEDGE_PLATFORM.md:295].
  - Change the rule to: a case promoted to training is retired from every eval split and replaced.
- **Contamination checks.**
  - Put canary strings in eval items.
  - Run black-box contamination tests on the base models [WEB arxiv.org/abs/2310.17623].
  - The edition-shift split (S3) also acts as a temporal guard.
- **Recursive data.** Do not keep training on model-generated data without fresh human anchors [WEB arxiv.org/abs/2305.17493] (UNVERIFIED re-read).

### 4.7 Go / no-go gates

All thresholds are proposals (INFERRED).

| Gate | Condition |
|---|---|
| **G0 (before any training)** | At least one approved, sectioned edition per procedure scope is indexed as direct evidence (today the index has 0 such chunks). The eval set is frozen at 600 or more items, with a manifest. Teachers and channels have legal sign-off (section 3). Reviewers are named |
| G1 safety | Zero CLE-1/2/3/4/6/8 on the golden 50 [corrected by verifier: only after the golden 50 gain reference answers and evidence packs, because it is `is_llm_eval: false` today]. On the full set, the upper 95% CI bound of the CLE rate is at or below REF's point estimate. No CLE category is worse than arm A |
| G2 memorisation | Evidence-tracking on S3/S4 is at least 98% and not below arm A |
| G3 abstention | Abstention recall on S5 is at least 95%. Over-abstention on answerable items is at most 10% |
| G4 format and language | 100% schema validity under constrained decoding. No new kolint errors in the `ux` genre. CLE-11 = 0 |
| G5 human review | 200 stratified outputs, two independent reviewers, agreement measured (e.g. κ ≥ 0.6), every disagreement adjudicated |
| G6 operations | p95 latency fits the tier budget (Quick Answer's timeout is 7 s [CODE lib/waymaker-quick-answer-ai.js:31]). The hosting and cost plan avoids trial-tier endpoints |

- A no-go on G1, G2 or G3 ends that arm.
- Never relax a threshold to make an arm pass.

### 4.8 What each experiment needs

| Need | B0 / A / A+ | B | C |
|---|---|---|---|
| Evidence corpus | Approved, sectioned editions (G0) | same | same |
| Labelled data | Eval set only | 1.5-3k reviewed SFT examples: synthetic or scrubbed questions, with answers written or corrected by trained reviewers | Everything in B, plus 5-20k teacher candidates; human review of at least 10% of kept items and 100% of high-risk ones |
| People | Eval reviewers | Plus about 2 legal-domain authors (INFERRED) | Plus licence and legal review of teachers and hosts |
| Compute | Inference only (C1) | C1-C2: QLoRA on 12B with one 24-80 GB GPU (INFERRED); the existing README suggests a Colab Pro L4/A100 | Teacher inference: gpt-oss-120b on one 80 GB GPU [LIVE L31] VERIFIED; Gemma 4 31B on C2 |
| Tooling | The existing `eval_outputs.py`, extended with the 4.4 verifier | TRL `SFTTrainer` or Unsloth; PEFT | Plus a provenance ledger and a teacher serving stack (vLLM) |
| Outputs | Frozen manifest; CLE report | Adapter; data card; licence notices | Plus a teacher provenance table |

---

## 5. Where deterministic rules or better retrieval beat training

| Problem | Better fix | Why training loses | Evidence |
|---|---|---|---|
| No direct legal evidence in the index (0 approved chunks) | Section and index the approved 2026-07-31 editions (needs human review) | No model can ground an answer on evidence it cannot retrieve | [LIVE, sibling health capture] OBSERVED by sibling |
| Facts change every few weeks (7 stay-manual editions in 4.5 months) | Edition-aware retrieval with effective dates and supersession; diffs between editions | Weights freeze a single edition | [CODE data/manual_approval_index.json] VERIFIED |
| Invented fees, numbers and offices | Apply the deterministic validators already used by Quick Answer to `/api/ask` | Training cannot guarantee zero inventions; a validator can | [CODE assets/js/waymaker-quick-answer.js:296-322] [TEST check_waymaker_quick_answer.mjs (ran: pass)] VERIFIED |
| Parsing status codes; keeping parent and subcode apart | Structured lookup (`lookup_status`) and regex | Exact and auditable; a model blurs subcodes | [CODE lib/waymaker-quick-answer-ai.js:52] VERIFIED [corrected by verifier: line 56] |
| Keeping visa and stay procedures separate | Scope tags from the source registry, and rejection of mismatches | This is a rule, not a judgement call | [DOC CLAUDE.md "Procedure scope"] |
| Escalating from Fast to Basic | Keep the deterministic `resolve_question_answer_mode` | Its reason codes are auditable | [CODE model_policy.py:234-295] [TEST test_model_policy.py (ran: pass)] VERIFIED |
| Deadlines | The `calculate_deadline` tool | Deadlines are arithmetic on encoded periods | [LIVE L28 tool registry] OBSERVED |
| Law recall and currency (name-only search, no `efYd`) | Fix the retrieval parameters | Recall is a property of retrieval, not of the model | [DOC research/law-stack.md:52,62] (sibling) UNVERIFIED by me |
| Unavailable models (5 configured ids missing from the catalog) | A catalog check in CI, and pruning dead ids | This is an operations problem, not a modelling one | [LIVE L7] VERIFIED |
| Citation validity | `citation_verifier` / `statute_citation_guard` | Checking a citation is deterministic | [TEST test_statute_citation_guard.py (ran: pass)] VERIFIED |

Training helps where no rule can produce the output:

- abstention behaviour;
- keeping the 6-section structure under long evidence;
- following the right evidence among distractors (RAFT);
- Korean register and plain language;
- a cheaper, self-hosted student that stops data going to third parties. This matters given section 3.3.

---

## 6. Recommendations

**Now:**
1. Ship no trained model.
2. Get legal review of the production channels: the NVIDIA trial terms, the TML research tier and AI Studio's unpaid tier.
3. Move user-facing traffic to channels whose terms allow production use and the kinds of data involved.
4. Pass G0:
   - section the approved editions;
   - freeze the eval set;
   - adopt the CLE taxonomy and the 4.4 verifier.
5. Extend the deterministic validators to `/api/ask`.
6. Prune catalog-dead ids.

**Next, after G0:**
1. Run arms A, A+, B and C offline.
2. Use gpt-oss-120b and Gemma 4 31B, self-hosted, as teachers.
3. Use Gemma 4 12B-it as the student.
4. Record provenance for every training example.

**Later:**
- RAFT-style structured supervision for Athena;
- DPO or KTO on failures that reviewers have confirmed;
- RLVR (GRPO) using the 4.4 rewards;
- per-scope LoRA adapters, served multi-LoRA;
- a self-hosted Hestia verifier;
- a quantised Artemis, but only after a Korean human eval.

**Never:**
- continued pretraining or full fine-tuning on statute or manual text;
- using teacher conclusions as gold labels;
- requesting private chain-of-thought;
- fine-tuning on user queries.

---

## 7. Live actions log

All requests were public, read-only GETs with no keys. Times are UTC.

| Id | Request | Result |
|---|---|---|
| L1-L6 | 03:57:58-03:58:02: openrouter.ai/terms; anthropic.com commercial and consumer terms; ai.google.dev gemini-api/terms, gemma_4_license and gemma/terms | all HTTP 200 (consumer terms served in Korean) |
| L7 | openrouter.ai/api/v1/models | 200, 788,326 bytes. Missing ids: openai/gpt-oss-120b:free, meta-llama/llama-3.3-70b-instruct:free, nousresearch/hermes-3-llama-3.1-405b:free, inclusionai/ling-3.0-flash-sante:free, inclusionai/ling-3.0-flash-fin:free |
| L8 | huggingface.co/api/models for Nemotron-3-Ultra-BF16, Nemotron-3-Super-FP8, Nemotron-3.5-Lightning, Inkling, Inkling-Small, gpt-oss-120b, Qwen3-8B, Hermes-3-405B, MiniMax-M3; plus an inclusionAI author search | all 200. Licences, in order: openmdw-1.1; nvidia-nemotron-open-model-license; openmdw-1.1; apache-2.0 (Inkling, Inkling-Small, gpt-oss-120b, Qwen3-8B); llama3; minimax-community |
| L9-L13 | 04:00:18-04:00:21: openmdw.ai 1-1; NVIDIA Nemotron OML; NVIDIA OML; llama.com/llama3_3/license/; HF Ling-3.0-flash | 200, 200, 200, **404**, 200 (mit) |
| L14 | NVIDIA API Trial ToS PDF. WebFetch could not parse it, so I extracted the text locally | 200, 209.7 KB |
| L15 | openrouter.ai/api/v1/models/{id}/endpoints, 8 models | 200. Nemotron free → Nvidia; Gemma free → Google AI Studio; Inkling → Thinking Machines; gpt-oss → DeepInfra, CoreWeave and others |
| L16 | openrouter.ai/api/v1/providers | 200; ToS URL for each provider |
| L17 | Thinking Machines free-research-tier ToS PDF | 200, 226,576 bytes. WebFetch could not read it; parsed locally |
| L18 | openai.com/policies/services-agreement/ and /row-terms-of-use/ (WebFetch) | **403 Forbidden** for both |
| L19 | WebSearch for the OpenAI clause, which pointed to cdn.openai.com/osa/openai-services-agreement.pdf | 200, 161,411 bytes, version 010126 |
| L20 | groq.com/terms-of-use; console.groq.com/docs/legal/services-agreement | 200, 200 |
| L21-L23 | GitHub raw Llama 3.3 LICENSE; HF DeepSeek-R1 card; gpt-oss USAGE_POLICY | all 200 |
| L24 | minimax.io ToS | 307 redirect to platform.minimax.io; the page is JavaScript-rendered and has no terms text |
| L25 | export.arxiv.org API, 55 ids | 200; all 55 resolved |
| L26 | 13 documentation URLs: TRL sft/dpo/orpo/kto/grpo/gkd/distillation; PEFT lora and merging; Unsloth (2); vLLM lora and structured outputs | all 200. The Unsloth URLs later returned 301 → unsloth.ai/docs |
| L27 | WebFetch of the TRL distillation, SFT and GRPO pages, and the Unsloth guides | 200 (TRL v1.16.0) |
| L28 | web-production-14f9a.up.railway.app/api/health/ai | 200 in 0.38 s; chains as in section 1 |
| L29 | arxiv.org/abs pages: 2405.05904, 2312.05934, 2407.03211, 2305.15717, 2403.10131, 2405.20362, 2405.09673, 2504.13837 | all 200 |
| L30 | export.arxiv.org abstracts batch | **Not executed.** The local disk was full (ENOSPC), so the shell could not run |
| L31 | huggingface.co/openai/gpt-oss-120b model card (WebFetch) | 200: fits one 80 GB GPU (H100/MI300X) using MXFP4; Apache 2.0 |
| Tests | `.venv-check/bin/python -m pytest -q -p no:cacheprovider` on test_model_policy, test_ai_runtime, test_nvidia_nim_provider, test_answer_quality_contract, test_statute_citation_guard | **132 passed**, 85 subtests passed, 5 warnings |
| Tests | `node scripts/check_waymaker_quick_answer.mjs` | OK, 23 checks passed |
| Tests | `python3 -I experiments/waymaker-gemma4-finetune/scripts/validate_dataset.py` on the sample sets | 0 errors, 0 warnings |

I did not use or run the korean-law-mcp reference repository for this task.

---

## Verification pass

Adversarial verifier, 2026-10-19. Tree: `/Users/seonjaekim/dev/Visable-genesis` at `0713370`, read-only. Corrections above are marked inline with "[corrected by verifier: ...]". No other text was rewritten.

### Method and what was re-run

| Id | Action | Result |
|---|---|---|
| V1 | Read `model_policy.py`, `ai_runtime.py:270-345`, `paradiso_backend.py` (lines 155-170, 250-265, 335-365, 7778-7815, 8426/8468), `lib/waymaker-quick-answer-ai.js`, `lib/enforcement-grounded-ai.js`, `api/enforcement/{analyze,confirm,extract}.js`, `providers/nvidia_nim.py`, `docs/ai/AI_PROVIDER_AND_MODEL_POLICY.md`; `git grep` for provider hosts and `TaskRole.*` callers | as cited inline |
| V2 | `.venv-check/bin/python -m pytest -q -p no:cacheprovider` on test_model_policy, test_ai_runtime, test_nvidia_nim_provider, test_answer_quality_contract, test_statute_citation_guard | **132 passed**, 85 subtests passed, 5 warnings (ran: pass) |
| V3 | `node scripts/check_waymaker_quick_answer.mjs` | OK, 23 checks passed (ran: pass) |
| V4 | `python3 -I -B experiments/waymaker-gemma4-finetune/scripts/validate_dataset.py dataset/train.sample.jsonl dataset/eval.sample.jsonl` | 6 + 8 examples, 0 errors, 0 warnings, exit 0 (ran: pass) |
| V5 | GET openrouter.ai/api/v1/models | 200, 788,485 bytes, 471 models; the five ids are absent |
| V6 | GET openrouter.ai/api/v1/providers | 200, 112 providers; Nvidia → NVIDIA API Trial ToS PDF; Thinking Machines → TML Free Research API Tier ToS PDF; Google AI Studio → cloud.google.com/terms/ |
| V7 | GET openrouter.ai/api/v1/models/{nemotron-3-ultra:free, gemma-4-31b-it:free, inkling:free}/endpoints | 200 ×3; sole providers Nvidia, Google AI Studio, Thinking Machines (nvfp4) |
| V8 | GET web-production-14f9a.up.railway.app/api/health/ai | 200 in 0.40 s; chains and manual counts as in the notes |
| V9 | WebFetch HF API: Nemotron-3-Ultra-BF16, Nemotron-3.5-Lightning-BF16, Nemotron-3-Super-FP8, thinkingmachines/Inkling, Qwen/Qwen3-8B; HF card deepseek-ai/DeepSeek-R1 | license_name openmdw-1.1, openmdw-1.1, nvidia-nemotron-open-model-license; apache-2.0 (not gated); apache-2.0; mit, with distillation explicitly allowed |
| V10 | WebFetch TRL docs distillation_trainer and gold_trainer (v1.16.0) | see claim 12 |
| V11 | GET export.arxiv.org API ×2 (8 ids: 2405.05904, 2312.05934, 2305.15717, 2407.03211, 2405.20362, 2504.13837, 2405.09673, 2403.10131) | 200; abstracts match the notes, with the nuance in claim 11 |
| V12 | GET raw.githubusercontent.com meta-llama llama3_3/LICENSE | 200; §1.b.i name-prefix clause present. The notes' own capture `td_raw/llama33.txt` holds only 13 bytes of junk, so this re-fetch is the primary evidence |
| V13 | Re-read local captures `td_raw/{nv_api_trial,openmdw11,nv_nemotron_oml,tml,gemini_api_terms,gemma_terms,gemma4_license,osa,anthropic_commercial}.txt`, `hf/lic2/{MiniMax-M3,Llama-3.1-8B}`, `hf/api/*.json`, `live/qa_get.json`, `live_health_ai.json` | as cited |
| V14 | `git -C ~/dev/Paradiso` diff/log/show on `fix/waymaker-qa-2026-10-16` | the branch changes the data-readiness conclusions (claims 10 and 13) |

- Shell writes failed several times with ENOSPC during this pass (about 0.6 GB free). Read-only work continued through the Read and WebFetch tools.
- No OC=/key=/token= values were printed. No korean-law-mcp code was run.

### Verdicts

| # | Claim (short) | Verdict | Evidence / correction |
|---|---|---|---|
| 1 | No Anthropic/OpenAI-API/Gemini-API calls; all LLM traffic via OpenRouter; Groq and Ollama opt-in | **corrected** | `git grep` finds direct calls only to openrouter.ai, api.groq.com (`paradiso_backend.py:1508`) and, in the unwired scaffold, integrate.api.nvidia.com. First-party host names appear only in a CI deny-list (`scripts/check_ai_architecture.py:72-79`) and the output-scrub regex. **But** Groq is not opt-in for `/api/nationality-coach`: it is called whenever GROQ_API_KEY is set (`paradiso_backend.py:7792-7798`), and live health shows `groq.configured: true`. Ollama is opt-in (`ENABLE_OLLAMA_FALLBACK`, default False, line 257) |
| 2 | Live verifier chain leads with gpt-oss-120b:free; enforcement_structured uses paid gpt-oss-20b, gemma-4-31b-it, gpt-oss-120b; both are env overrides of code defaults | **corrected** | Chain values re-OBSERVED (V8) and code defaults confirmed (`model_policy.py:112-118`). The env-override *cause* is INFERRED: the health endpoint does not list AI_VERIFIER_MODEL or OPENROUTER_ENFORCEMENT_MODEL*. Also `TaskRole.VERIFIER` has no production caller on main, so the verifier chain is declared but never invoked; `ENFORCEMENT_STRUCTURED` is invoked (`paradiso_backend.py:8426,8468`) |
| 3 | Five configured ids absent from the OpenRouter catalog; Quick Answer effectively one model deep | **confirmed** | V5: all five absent; `gemma-4-31b-it:free` present. Live Quick Answer GET [DOC live/qa_get.json] shows the default 3-id chain, so only the first id resolves. The Vercel `/api/enforcement/analyze` default chain (gemma:free → gpt-oss-120b:free) is likewise effectively one model deep |
| 4 | Nemotron :free served by "Nvidia"; registry ToS = NVIDIA API Trial ToS; §1.2, §4.2, §4.3, §4.12 | **confirmed** | V6, V7, and the captured PDF text. All four clauses read as paraphrased. Additions: §3.3(iv) data use for model improvement; §1.4 Subscription needed for production; document version "v. September 19, 2025" |
| 5 | Nemotron 3 Ultra and 3.5 Lightning under OpenMDW-1.1 (no output restrictions); Super under Nemotron OML (no output ownership claimed; derivatives allowed) | **confirmed** | V9 license_name fields. OpenMDW text: "does not impose any restrictions or obligations with respect to any use, modification, or sharing of any outputs". Nemotron OML preamble, last modified 2025-12-15 [td_raw/nv_nemotron_oml.txt:667-673] |
| 6 | TML Free Research Tier ToS (2026-08-20) forbids distilling/training competing models and personal data, grants TML a perpetual training licence; Inkling weights Apache-2.0 | **confirmed** | [td_raw/tml.txt]: header "Last updated August 20, 2026"; competing-model/distil clause; irrevocable perpetual licence covering training "Company Models and other AI models"; personal-data ban; no weights access via the API. HF Inkling apache-2.0, not gated (V9) |
| 7 | Gemma 4 Apache-2.0; older Gemma Terms define distilled models as Model Derivatives; Gemini API forbids competing models; unpaid tier bars personal data and allows human review | **confirmed** | [td_raw/gemma4_license.txt] has the full Apache 2.0 text. [td_raw/gemma_terms.txt] §1(e) explicitly covers distillation via synthetic data (last modified 2026-04-01). [td_raw/gemini_api_terms.txt]: effective 2026-03-23, page updated 2026-04-28. HF gemma-4 cards: apache-2.0, `gated: false`. Caveat (inline): whether the unpaid terms bind OpenRouter's AI Studio route is INFERRED |
| 8 | OpenAI OSA v.010126 §3.3(e) bars Output for competing models, except non-distributed classifiers/embeddings and OpenAI fine-tuning; Anthropic Commercial §D.4 bars training competing models without approval | **confirmed** | [td_raw/osa.txt]: §3.3(e) and the "Permitted Exception" definition match. [td_raw/anthropic_commercial.txt]: effective June 17, 2025, §D.4 matches. Consistency note added inline (all three "compete" clauses share one interpretive question) |
| 9 | Llama 3.1/3.3 allow outputs to improve other models with a "Llama" name prefix if distributed; Qwen3 Apache-2.0; DeepSeek MIT and explicit distillation; MiniMax M3 non-commercial unless conditions/authorisation met | **corrected** | Llama confirmed (V12; Llama 3.1 text in hf/lic2); the prefix applies when the model is "distributed **or made available**". Qwen3-8B apache-2.0 confirmed, but two of the three Qwen3.8 repos are not Apache (`qwen3.8-max`, `qwen-community-1.0`). DeepSeek-R1 MIT and distillation confirmed (V9). MiniMax: commercial use is allowed under US$20M yearly revenue with notices; authorisation is needed only above it. The notes' "not permitted" is stricter than the text, so it moves to REQUIRES LEGAL REVIEW |
| 10 | Seven stay-manual editions (2026-05-01 → 2026-09-18); only the 2026-07-31 HWP pair approved; 2026-09 editions await review | **confirmed** (origin/main) | `data/manual_approval_index.json`: stay editions 05-01, 06-01, 06-17 (txt), 06-23, 07-31, 09-01, 09-18 = 7; approved = visa/stay 07-31 HWP; all 2026-09 entries `needs_review`. **Materially changed on the owner's branch:** 2026.9 visa and stay editions `approved` (2026-10-16), 07-31 `superseded` |
| 11 | FT on new knowledge raises hallucination; RAG > FT for knowledge injection; imitation copies style not factuality; quantisation hurts non-Latin scripts beyond what metrics show | **confirmed** | V11 abstracts. Nuance: Ovadia et al. compare RAG with *unsupervised* fine-tuning; Gekhman et al. is closed-book QA SFT. The 1.7% → 16.0% Japanese figure is confirmed |
| 12 | TRL logit/on-policy distillation needs a shared vocabulary, so API teachers and cross-family pairs are limited to response-level | **corrected** | `DistillationTrainer` docs (v1.16.0): teacher "must share the student's vocabulary". But TRL v1.16.0 also ships the experimental `GOLDTrainer`, which supports cross-tokenizer (mixed-family) logit distillation with GKD-style on-policy mixing. A self-hosted Nemotron → Gemma pair is possible, though the alignment caveat for SentencePiece-style tokenizers applies. API teachers remain response-level only: no full distributions, top_logprobs at most |
| 13 | Live index: 0 direct-evidence chunks of 2,626; no verified gold corpus | **confirmed** (production) | Re-OBSERVED (V8), now by me. Caveat: the owner's unpushed branch adds page-mapped direct-evidence chunks from the approved 2026.9 editions and grounds `/api/ask` in them (commit messages; README-ONLY). "No gold corpus" still holds, since none of this is a reviewed training set |
| 14 | Fine-tune experiment is placeholder LoRA/QLoRA wiring (6/8 examples) for gemma-4-12B-it; validator passes; notebook bf16=True while recommending T4 | **confirmed** | V4. README lines 25-26, 36-42, 84-86. Notebook cell 10 `bf16=True`; cell 8 bfloat16 compute dtype too; README recommends a free T4. T4 lacking native bf16 is general hardware knowledge (INFERRED; not run). Extra: the README's "gated" note on gemma-4-12B-it conflicts with HF `gated: false` |
| 15 | Docs say future training candidates come only from approved eval cases, which is a leakage hazard; golden set `is_training_data: false` | **confirmed** | `docs/ai/WAYMAKER_KNOWLEDGE_PLATFORM.md:295-296` (the sentence spans two lines); golden file line 4. Extra correction (inline): the same file line 5 is `"is_llm_eval": false`, and the 50 items have no reference answers, so they cannot score CLE as G1 assumes |

### Omissions against the brief

Filled by the verifier (inline above, with evidence):
1. **Unlisted Vercel model surfaces.** `api/enforcement/analyze.js` presets its own two-id chain. `confirm.js` defaults to `gemma-4-31b-it:free`. An analyze.js comment invites an operator opt-in to Gemini 3 Flash via OpenRouter, which would bring Google's terms onto that path.
2. **Groq's live path through the nationality coach.** Llama 3.1 8B outputs, under the Llama licence and Groq's terms, can reach users today.
3. **NVIDIA trial §3.3(iv) and §1.4.** These strengthen the production-path side finding: NVIDIA may use the traffic to improve its models, and production use requires a paid Subscription.
4. **GOLDTrainer.** Cross-family logit/on-policy distillation is available, experimentally, in TRL v1.16.0.
5. **The owner's branch.** It approves the 2026.9 editions, adds direct-evidence manual excerpts to `/api/ask` and adds an offline deterministic model benchmark. Gate G0 and split S3 need revisiting once it merges.
6. **The golden 50 are a routing set, not an LLM answer eval** (`is_llm_eval: false`).
7. **Licence-coverage gaps.** Qwen3.8 licence heterogeneity, and the MiniMax commercial-use mechanics.

Not filled (could not, or out of bounds):
1. **Verbatim clause quotes.** The brief asked for quotes of up to 25 words for each clause. The notes paraphrase every clause except NVIDIA §1.2, and I kept that approach. My operating rules also cap verbatim reproduction, so I added only the single OpenMDW quote under claim 5. Full texts for a legal reviewer stay in `scratchpad/research/td_raw/`.
2. **Paid-host terms not reviewed.** These are the paid OpenRouter hosts for gpt-oss and Gemma (DeepInfra, CoreWeave, Parasail, AkashML), the DeepSeek API ToS, the MiniMax platform ToS (it rendered only with JavaScript), and NVIDIA's paid or self-hosted NIM licence (NVIDIA AI Enterprise). They remain REQUIRES LEGAL REVIEW.
3. **Paid or unpaid Google tier.** Whether OpenRouter's upstream Google AI Studio account is on Paid or Unpaid Services cannot be determined from public data.
4. **The brief's Artemis / Athena / Hestia definitions.** I could not locate them either. `git grep -i` for all three names returns nothing on the worktree or on the owner's branch (VERIFIED). The notes' working definitions are the original agent's own INFERRED definitions.
5. **No empirical check of GOLD.** I did not measure GOLD alignment quality for a Gemma (SentencePiece) student, or whether `bf16=True` fails or silently emulates on a T4. Neither was run.
