# 10 — Athena and Hestia strategy

Status: **RESEARCHED ONLY.** No Athena or Hestia model, adapter, prompt or
experiment was built, trained or run in Mission 001, and this document changes
no code. It is a strategy for the owner, drawn from verified research notes.
Nothing here is legal advice, and nothing here describes an approved or
official use by any public body.

Mission 001 "Waymaker Genesis". Research date 2026-10-19; written 2026-10-20.
Sources: [research-notes/training-distill.md](research-notes/training-distill.md),
[research-notes/models.md](research-notes/models.md),
[research-notes/cost.md](research-notes/cost.md),
[research-notes/ai-lifecycle.md](research-notes/ai-lifecycle.md),
[research-notes/law-stack.md](research-notes/law-stack.md),
[research-notes/law-stack-fixes.md](research-notes/law-stack-fixes.md),
[research-notes/law-identity.md](research-notes/law-identity.md) and
[research-notes/status-classifier.md](research-notes/status-classifier.md), each
read with its verification pass. Code citations are to the audited commit
`0713370` as the notes recorded them, except where a later file on `fc896c2` is
named. Evidence tags: `[CODE path:line]`, `[TEST …]`, `[DOC …]`, `[LIVE …]`,
`[WEB url, accessed 2026-10-19]`. Status words: VERIFIED, OBSERVED, README-ONLY,
INFERRED, UNVERIFIED.

## 0. Bottom line

1. **Most of Waymaker's legal-answer failures happen before the model reasons.**
   Of seven failure sources traced in §2, four concern what the model is given
   (missing evidence, incorrect evidence, temporal context, question
   decomposition), one concerns how its output is checked (verification) and
   one what is shown (unsafe generation). Only one is model reasoning itself,
   and that one is bounded by the evidence the model receives.
2. **Athena therefore starts with evidence and verification, not with a
   model.** In the short term Athena is an external or open-weight model that
   reasons only over a bounded WLIE `EvidencePackage` and answers in the
   structured contract of [07 §5](07-evidence-verification-design.md), with
   every claim passed back through the L1-L7 gate. No training.
3. **Long-term Athena work (adapters, preference tuning, verified distillation)
   starts only after the gates in [09 §5.4](09-training-and-distillation.md) and
   [12 §7.2](12-evaluation-methodology.md) pass.** It trains behaviour, never
   facts.
4. **Hestia: Option A now** (existing model + workflow + retrieval). Option B
   (shared base + LoRA) only after Option A has a frozen professional eval set
   and shows a gap that no rule or retrieval fix closes. Option C (a dedicated
   model) is not recommended in any current horizon.
5. **Government use is out of scope today.** Hestia is a research prototype:
   no official adoption, no connection to internal systems, no case files, and
   no institutional data sent to third-party models (§6).

## 1. Names and definitions

The names Artemis, Athena and Hestia appear nowhere in the repository or on the
owner's branch (`git grep -i`) VERIFIED (training-distill.md verifier, not
filled #4). The working definitions:

| Role | Definition used in this document set | Source |
|---|---|---|
| Artemis | Compact routing and extraction; labels only | [13 §1](13-artemis-experiment.md) |
| **Athena** | Advanced reasoning over a supplied evidence package | models.md header; [05 §4](05-legal-intelligence-architecture.md) |
| **Hestia** | Professional assistant on a shared base, possibly with LoRA adapters | models.md header |

training-distill.md §2.0 defined Hestia differently, as a self-hosted
verifier for claim-to-evidence entailment (INFERRED there). In this document set
claim verification is the deterministic WLIE gate
([07](07-evidence-verification-design.md)): L5 passes only on a deterministic
support signal, and a model judge can only ever advise (07 §3 L5). A
model verifier may exist as an advisory signal inside the Athena pipeline, but
it is not Hestia and it never decides a claim's status.
[15 §6](15-security-and-deployment.md) records both readings.

**Reconciliation (decided here, as [08 §2](08-foundation-model-research.md)
asks).** Hestia is the professional assistant of the models.md reading. The
guardian/verifier reading of training-distill.md §2.0 is not adopted for
Hestia. Its useful part survives in two places: verification stays the
deterministic WLIE gate, and keeping personal data on infrastructure the
deployer controls becomes a Hestia deployment condition (§6.2 item 1). If an
advisory model verifier is ever built, it is measured as
[08 §10.4](08-foundation-model-research.md) describes for that reading: on
`citation_verification`, with HG-1 to HG-5 as hard limits and zero false
absence declarations above all. This decision unblocks the Hestia measurement
design in §5.3.

## 2. Athena: where reasoning failures actually come from

Each row names an observed defect in the current answer path, what fixes it,
and whether a stronger model would.

| # | Failure source | Observed in Waymaker | Fix | Does a stronger model fix it? |
|---|---|---|---|---|
| 1 | **Missing evidence** | The live manual index held 2,626 chunks and 0 direct-evidence chunks from an approved edition [LIVE GET /api/health/ai, 2026-10-19, 200] (training-distill.md §0.7, re-OBSERVED by its verifier). Statute rows that `search_laws` returned were dropped before the evidence pack, so the prompt said law evidence was unavailable (law-stack.md §0.1, VERIFIED offline; production impact INFERRED). The six-tool registry is not called by `/api/ask` (ai-lifecycle.md §2.7). The client's `context` (nationality, interview mode, Quick Answer handoff, the navigator's packet-only instruction) is truncated and never read (ai-lifecycle.md R1, as corrected) | Index the approved editions (the owner's branch page-maps 2026.9 texts, README-ONLY); F1 in this branch restores statute rows to the pack, verified offline, and must ship with F2 (law-stack-fixes.md F1); wire existing tools; a server-built context block | **No.** No model can ground an answer on evidence it never receives |
| 2 | **Incorrect or untrusted evidence** | Client-supplied `visa_data` is presented to the model as manual-backed evidence and overrides status detection (ai-lifecycle.md R3, §5 item 3). The stored 출입국관리법 snapshot is `mst 272921 / 2026-01-23`; the current version is `290729 / 2026-10-02` (law-identity.md §6 item 2). Upstream failures were reported as "not found" on several paths (law-stack.md §0.3, conditional per its verifier) | Resolve `visa_data` server-side; WLIE identity (`stable_id`, version key) and invariant 1, failure is not absence ([07 §2](07-evidence-verification-design.md)); F3-F5 in this branch fix some failure-as-absence paths, others remain (law-stack-fixes.md) | **No.** A better reasoner over wrong evidence reaches a wrong answer more fluently |
| 3 | **Temporal context** | The backend sends no `efYd`, reads no history and no 부칙 ([06 §5](06-temporal-law-and-source-identity.md)). 시행규칙 제73조 takes effect on 2027-09-16 inside a version effective 2026-09-15 ([06 §4](06-temporal-law-and-source-identity.md)). The 2026.9 stay manual (2026-09-18) predates the 출입국관리법 and 시행령 versions in force from 2026-10-02 ([07 §3 L7](07-evidence-verification-design.md), scenario J). Seven stay-manual editions in 4.5 months [CODE data/manual_approval_index.json:47-300] | Temporal resolver with `candidate_only` determinations and warnings ([06 §3](06-temporal-law-and-source-identity.md)); `manual_predates_law_change` conflict records | **No.** A model cannot know which version governs a date unless the package states versions and dates; trained-in knowledge makes this worse (§4) |
| 4 | **Decomposition (question understanding)** | Python reads no subcode from free text; `understand()` silently fills the parent when the text names a subcode; the procedure is lost for zh, ja, vi and ru questions (status-classifier.md R4, R1, R12). Instructions, evidence and the question are concatenated into one user message with no data-not-instructions framing (ai-lifecycle.md §5 items 1-2) | Rule fixes first ([13 §6](13-artemis-experiment.md)); a structured package that quotes sources as data and carries the question's status, subcode, procedure, dates and anchor as fields ([05 §4](05-legal-intelligence-architecture.md)) | **Partly.** A model can help on phrasing no rule covers (Artemis decision D1), but parent/subcode and scope rules stay deterministic |
| 5 | **Model reasoning** | Supplying precedents raises Korean legal MCQA by 9-36 points across models, from about ×1.4 to ×2.2 (KCL, models.md §0 item 5 as corrected) INDEPENDENT; even with evidence, open models in that study stay well below a frontier reference (e.g. gpt-oss-120b 64.1, Gemini 2.5 Pro 89.3 MCQA; models.md §7). Commercial legal RAG tools still hallucinate 17-33% of the time [WEB arxiv.org/abs/2405.20362] VERIFIED | Choose the reasoner by evaluation on Waymaker packages (§3.2); structured supervision later (§4) | **Yes, this is the residual.** Interpreting conditions, combining provisions and deciding when to abstain improve with a better model, once rows 1-4 are fixed |
| 6 | **Unsafe generation** | Groq, Ollama and streaming paths bypass most answer guards; the Groq family fallback returns raw text without the confidence gate or metadata scrub (ai-lifecycle.md §2.1, R6). No data-not-instructions framing (§5) | One guard pipeline for every exit; data framing; deterministic validators such as Quick Answer's `validateEnhancement` [CODE assets/js/waymaker-quick-answer.js:290-322] | **No.** Guards must hold whatever the model |
| 7 | **Verification** | "Verified" meant a law title was found; when the flag was set, every article number the model wrote was allowed (law-stack.md §0.2; ai-lifecycle.md R5). Token matching ignores the law name. The case verifier can replace a correct answer that cites an injected case (ai-lifecycle.md R11, reproduced offline). The strongest guard, `statute_citation_guard`, is not wired to `/api/ask` (ai-lifecycle.md §2.8) | WLIE L1-L7 per claim ([07](07-evidence-verification-design.md)); F2 in this branch stops the blanket allow, verified offline; passing `article_evidence` from `/api/ask` remains Mission 002 work (law-stack-fixes.md F2, "Not done") | **No.** Verification is deterministic by design; a model judge is advisory only |

**Why evidence and verification come first.** Rows 1-4 and 7 are defects in
what the model is given or in how its output is checked; row 6 is a defect in
what is shown. Fixing them is deterministic, testable offline, and does not
expire when a manual edition changes. Row 5 is real, but the KCL result shows
that the same model moves by up to 36 points depending on whether evidence is
present, which is larger than the spread among most of that study's open models
once evidence is supplied (for example 64.1 for gpt-oss-120b to 76.9 for Qwen3
235B Thinking; models.md §7; the comparison is INFERRED). A stronger model
placed on today's path would inherit rows 1-4 and 7 unchanged. Training first
would be worse still: it would write one edition's facts into weights that
cannot cite them (training-distill.md §2.2, [09 §2.4](09-training-and-distillation.md)).

## 3. Athena, short term: external or open-weight reasoning over WLIE packages

### 3.1 Contract

- **Input.** A bounded `EvidencePackage` (at most 12 items, 2,400 characters
  each, 20,000 in total; truncation recorded, never silent), delivered as
  `public_view()`, with source text quoted as data and untrusted
  instruction-like text flagged ([07 §5](07-evidence-verification-design.md);
  [07 §2](07-evidence-verification-design.md) invariant 5). When verified
  provisions exist, a full legal corpus is never passed.
- **Output.** The structured form of [07 §5](07-evidence-verification-design.md):
  question interpretation, relevant facts, relevant dates and the anchor,
  potentially applicable provisions with version keys, confirmed and
  conditional requirements, unresolved factual questions, conflicting
  evidence, verification status per claim, and matters for human review.
- **What the model never does.** It never verifies a citation and never chooses
  a law version; deterministic code does both ([12 §4.2](12-evaluation-methodology.md)).
  It never names a source the package does not contain
  ([05 §4](05-legal-intelligence-architecture.md)).
- **After generation.** Every claim goes back through L1-L7. A claim whose
  overall status is not `verified` is shown with its qualification or held back
  ([05 §4](05-legal-intelligence-architecture.md)). Disclaimers and
  review-needed warnings are never weakened.

### 3.2 Which reasoner

Korean evidence for 2026 models is thin and mostly vendor-reported; no
independent Korean leaderboard covering Gemma 4, A.X K2, K-EXAONE 2.0 or Solar
Open 2 was found (models.md §7). The choice must come from Waymaker's own
evaluation on its own packages.

| Candidate | Licence (models.md §4) | Hosting (models.md §6, INFERRED) | Korean evidence (label) | Caveat |
|---|---|---|---|---|
| Current hosted chain: Nemotron 3 Ultra, Gemma 4 31B, Nemotron 3 Super | OpenMDW-1.1; Apache-2.0; Nemotron OML | OpenRouter today | Nemotron 3 Ultra KMMLU-Pro 69.2, competitor-reported (VENDOR) | The `:free` routes carry the production-terms risk ([09 §6](09-training-and-distillation.md)); most lack `structured_outputs` |
| gpt-oss-120b | Apache-2.0 | 1×80 GB (MXFP4), or paid OpenRouter hosts | KCL MCQA 29.2 → 64.1 with precedents (INDEPENDENT) | 2025 vintage; weak Korean knowledge without evidence |
| Gemma 4 31B-it ("Athena-lite") | Apache-2.0 | single GPU at 4-bit | MMMLU 88.4 (VENDOR); no Korean-specific number | Gemma Prohibited Use Policy applicability unresolved |
| Solar Open 2 250B-A15B | Upstage Solar License (naming duties only if a derivative model is distributed or made available) | about 2×H100 at 4-bit; not on OpenRouter | KBL 75.5, KMMLU-Pro 78.4 (VENDOR) | Not "the only" open model with a Korean legal score (verifier) |
| A.X K2 688B-A33B | Apache-2.0 by metadata; no LICENSE file in the repo | 8×H100 class; forked vLLM | KMMLU-Pro 80.5, CLIcK 91.6 (VENDOR, thinking mode), tied by competitor-reported DeepSeek-V4-Pro | Ask SKT for a LICENSE file |
| K-EXAONE 2.0 750B-A37B | Apache-2.0 (LICENSE and NOTICE read) | 8×H100 class; LG forks | KMMLU-Pro 69.1, KGC-Safety 99.8 (VENDOR) | Largest of the three |
| Frontier APIs (Claude, GPT, Gemini) | Provider terms | API | none for Waymaker | Reference or judge only, after legal review; never a correctness metric ([12 §4.2](12-evaluation-methodology.md) baseline 9). $0.020-0.055 per question at list price (cost.md §0.6) VERIFIED prices, INFERRED arithmetic |

How a candidate is scored is set out in
[08 §10.3](08-foundation-model-research.md): the benchmark's abstention task
and CLE-9 rows; each candidate scored with and without the evidence package on
the same items (a small gap means it answers from memory, INFERRED); the
adversarial classes for a missing legal source, an upstream failure and source
injection reported separately; KCL-MCQA with precedents and a Waymaker-run KBL
as internal-only external checks. The candidate is never scored as the
verifier, and its output must still pass HG-1 to HG-6.

Recommendation (models.md Rec. 3, adapted): keep a hosted open-weight reasoner
for now, but on a channel that passes legal review; run a bake-off of Solar Open
2, A.X K2, K-EXAONE 2.0 and gpt-oss-120b on Waymaker packages before committing
GPUs. The three Korean models are not on OpenRouter, so the bake-off needs
rented multi-GPU nodes and the owner's authorisation (Mission 002,
[17](17-mission-002-plan.md)). Licence-mandated "Built with / Powered by" lines
belong in UI chrome, not in answers (models.md Rec. 6).

### 3.3 Channel and cost

Paid endpoints of the open models cost $0.0006-0.0054 per question at a 5k-in /
1k-out profile (cost.md §0.5) VERIFIED prices, and list `structured_outputs`,
which the `:free` routes mostly do not (models.md §3b, verifier). At 10k
questions per month that is about $15-57 including OpenRouter's fee (cost.md
§11 scenario 4 option A). Escalating only high-risk issue types to a frontier
model is about $51-143 per month at 10k questions (option B, as corrected by
the cost verifier). Self-hosting is not justified on cost below about 2M
questions per month (cost.md §9, §11;
[14 §7.4, §8](14-hardware-and-cost-model.md)). The channel decision is the
owner's, with counsel ([09 §6](09-training-and-distillation.md)).

### 3.4 Preconditions for Athena on the answer path

1. WLIE meets its promotion criteria ([05 §3](05-legal-intelligence-architecture.md)):
   benchmark gates pass on test and holdout; critical labels human-reviewed;
   live, sanitised responses replace fixture shape assumptions; the owner's
   branch merged; a `LawToolsAdapter` passes the same suite.
2. The hard gates HG-1 to HG-10 pass ([12 §7.2](12-evaluation-methodology.md)).
3. The abstention task is scored on human-verified labels
   ([12 §3.5](12-evaluation-methodology.md)).
4. A free-text answer evaluation exists for CLE-1/2/6/7/10/11, which the
   Mission 001 benchmark does not score ([12 §7.1](12-evaluation-methodology.md)).
   **Not built** (DEFERRED).
5. The channel has passed legal review, and eval items sent to any provider are
   synthetic or scrubbed.

## 4. Athena, long term: adapters, then distillation, only after gates

Order matters: each step needs the previous one's evidence. All steps need G0
(approved sectioned editions per procedure scope as direct evidence; eval frozen
at 600+ items with a manifest; legal sign-off on teachers; named reviewers) and
the per-arm gates G1-G6 ([09 §5.4](09-training-and-distillation.md)).

| Step | Technique | Why this order | Additional precondition |
|---|---|---|---|
| 1 | RAFT-style structured supervision: quote evidence → map to claim → conclude or abstain, with every quote a verbatim substring of the package [WEB arxiv.org/abs/2403.10131] | The best-fitting training lever for Athena; checkable by code (training-distill.md §2.1) | 1-5k annotated traces from approved editions |
| 2 | DPO or KTO on reviewer-confirmed failures | Teaches "abstaining beats inventing"; pairs must differ in correctness, not tone | Knowledge Studio reviewed labels; a user's report alone is never a label |
| 3 | RL with verifiable rewards (GRPO) on the deterministic checks | Waymaker's answers are unusually checkable; watch for reward hacking (always abstain, always cite the first chunk) | A frozen reward implementation identical to the eval verifier |
| 4 | Per-scope LoRA adapters (visa issuance vs stay), selected deterministically, never merged | Keeps procedure scopes apart (CLAUDE.md; [15 §6](15-security-and-deployment.md) B6) | A measured gap per scope |
| 5 | Verified response distillation (arm C) from permitted self-hosted teachers | Adds phrasing variety of verified behaviour (H2) | Teacher policy signed off; WLIE-verified and human-reviewed teacher conclusions only |
| 6 | A smaller or quantised student for cost and data control (H4) | Only once 1-5 hold on a 12B-class student | A Korean human eval of the quantised model (quantisation hurts non-Latin scripts beyond what metrics show [WEB arxiv.org/abs/2407.03211] VERIFIED) |

Never: continued pretraining or full fine-tuning on statute or manual text;
teacher conclusions as gold labels; private chain-of-thought; fine-tuning on
user queries (training-distill.md §6). Edition-shift and counterfactual splits
must show the student follows the evidence (G2: at least 98%, not below the
untuned model). An Athena experiment was **not prepared** in Mission 001; the
design in [09 §5](09-training-and-distillation.md) is its starting point.

## 5. Hestia

### 5.1 Scope: what Hestia is for

Hestia serves a professional reader (for example someone preparing or checking
an application; INFERRED, no user research was done), not a decision-maker.
Its value is accuracy against public sources and a record that someone else
can check.

| Capability | Meaning | Builds on | Boundary |
|---|---|---|---|
| Public-source accuracy | Every statement traces to a public source: statute text from law.go.kr or an approved manual edition | WLIE L1-L7; manual approval index (fail-closed); attribution "출처: 법제처 국가법령정보센터 (law.go.kr)" with URL, `retrieved_at` and `content_sha256` ([15 §6](15-security-and-deployment.md) B2) | No invented requirement; no superseded edition presented as current |
| Professional structure | Requirements split into confirmed, conditional, applicant-specific and office-discretion; legal basis separated from operational guidance | Knowledge Platform `requirement_level` and `condition_kind`; [05 §5](05-legal-intelligence-architecture.md); [07 §5](07-evidence-verification-design.md) response contract | A manual line never becomes a legal obligation; a statute that authorises a procedure does not supply its document list |
| Traceability | Each item links to its source, version key and effective date | `EvidencePackage` hash and audit record ([05 §4](05-legal-intelligence-architecture.md)) | Parent and subcode rules never merged; scope required per requirement |
| Checklists | Document checklists per status, subcode and procedure | Verified Knowledge Platform checklists (D-2, D-4, E-7 extension per the architecture doc, README-ONLY; ai-lifecycle.md §2.6). On `fc896c2` the Content Operations Studio adds checklist review states from `COMPILED_NEEDS_REVIEW` to `PUBLISHED` and viewer/editor/reviewer/publisher roles [CODE backend/services/knowledge/checklist_models.py:17-55] (OBSERVED for this document; added after the audit, not audited) | Only published, reviewed items reach a checklist; visa-issuance and stay attachments never mixed |
| Drafts | Draft explanations or notes for a professional to edit | The structured answer above, rendered as an editable draft | Always labelled as a draft for human review; never submitted on anyone's behalf; protected terms (status codes, form names, statute citations) unchanged, checked by kolint |
| Missing-information detection | Say what fact is missing before answering | WLIE `insufficient_context`, `anchor_missing`, `historical_lookup_required`; Artemis `needs_clarification`; the abstention task ([12 §3.5](12-evaluation-methodology.md)) | Ask or abstain; never fill a gap with a default (for example "current law") |
| Auditability | Reproduce any output later | Evidence-pack hash, model revision SHA, adapter id and prompt hash per answer ([15 §6](15-security-and-deployment.md) B9); Knowledge Platform audit log | No user content in logs beyond what the retention rules allow ([11 §7](11-dataset-governance.md)) |
| Human review | A person settles what code cannot | `human_review_required` and `needs_review` outcomes stay visible ([07 §1](07-evidence-verification-design.md)); named reviewers (G5) | Outputs are evidence packets with `candidate_only` version determinations, never approve/deny decisions ([15 §6](15-security-and-deployment.md) B1) |

### 5.2 Options

| | **A. Existing model + workflow + retrieval** | **B. Shared base + LoRA** | **C. Dedicated model** |
|---|---|---|---|
| What it is | A hosted or self-hosted open model reads WLIE packages and Knowledge Platform facts and fills the §5.1 structures; the workflow (review states, roles, audit) carries the professional value | One base shared with Artemis, e.g. Gemma 4 31B-it or 12B-it with an E4B Artemis; per-scope or per-task adapters served multi-LoRA (vLLM, S-LoRA) | A separately trained model: continued pretraining or full fine-tuning on Korean legal and administrative text |
| Reuses | Everything in §5.1; the Athena contract (§3.1) | Option A plus adapters | Little; duplicates the stack |
| Training data | None | 1-3k reviewed examples per adapter; evidence in the prompt; no real case data | 100M-10B+ tokens; the corpus is small and changes every few weeks |
| Cost signal | Cents per question on paid open endpoints (cost.md §0.5) | $4-60 per LoRA run (cost.md §10); self-hosted serving $264-8,075 per GPU per month, or a managed host that serves fine-tuned models at base price (cost.md §9) | C3-C4 compute; highest |
| Main risk | Channel terms ([09 §6](09-training-and-distillation.md)); no Korean eval yet | Adapters memorising one edition; composition blending scopes; licence duties of the base (Kanana: "Powered by Kanana" and naming) | Freezes a law snapshot in the prior (the worst fit in training-distill.md §2.1); unauditable |
| Justified when | Now | After A has a frozen professional eval set, shows a gap no rule or retrieval fix closes, and G0-G6 pass | Not in any current horizon |

### 5.3 Recommendation: Option A now

1. Hestia's distinctive value (traceability, checklists, missing-information
   detection, audit, human review) lives in the workflow and the evidence
   layer, which already exist in part and are deterministic.
2. Nothing in §5.1 requires new weights; every capability has an existing
   component or a WLIE contract.
3. There is no professional eval set and no reviewed training data, so Option B
   could not be measured.
4. Training would duplicate what the verifier must enforce anyway, and risks
   writing an edition into weights.
5. Option A keeps the base swappable while the Athena bake-off (§3.2) runs.

**Measuring Hestia.** Benchmark v0 scores closed values only and cannot select
a Hestia assistant ([08 §10.4](08-foundation-model-research.md);
[12 §1](12-evaluation-methodology.md)). With the role fixed in §1, the
measurements Hestia needs are, all NOT STARTED: adherence to the structured
contract of [07 §5](07-evidence-verification-design.md) (a Ko-IFEval-style
format check; the old scaffold's 6-section format exists nowhere in production,
[13 §13](13-artemis-experiment.md)); abstention and missing-information
detection on the same suite as Athena; Korean prose checked by
`kolint --genre ux`, never applied to legal or administrative wording; a
person's review of critical errors; checklist correctness against published,
reviewed checklist items; and, for Option B only, multi-LoRA serving cost.

Exit criteria for considering Option B: a frozen professional eval set with
human-verified labels; a measured gap on a stable capability (structure,
register, missing-information detection) that rule and retrieval fixes did not
close; G0-G6 met; and an owner decision on the base family. If B is ever built,
the shortlist is Gemma 4 31B-it or 12B-it (policy-aligned, Apache-2.0), then
Kanana-2-30B-A3B (Korean-native vendor profile, attribution and naming duties),
Mi:dm 2.0 Base (MIT) and gpt-oss-20b (models.md §5 Hestia). None has independent
Korean evidence, so Waymaker's own eval decides.

## 6. Government-use boundaries

### 6.1 Current position: research prototype

| Boundary | Meaning today | Basis |
|---|---|---|
| Research prototype only | Hestia exists as a strategy; nothing is built | this document |
| No official adoption | No public body uses, endorses or has reviewed Hestia; no output is an official determination. law.go.kr states that its information has no legal effect and the 관보 is authoritative | [15 §6](15-security-and-deployment.md) B1 [DOC official-api.md §6] VERIFIED |
| No internal systems | No connection to any institution's internal system, case-management tool or network | INFERRED requirement |
| No case files | No real case files, application packets, decisions addressed to a person, refugee interview records or consultation copies, even "anonymised" | [11 §4.5](11-dataset-governance.md) |
| No institutional data to third-party models | Nothing an institution holds goes to a hosted model; free and trial channels bar personal data | [15 §6](15-security-and-deployment.md) B3; [09 §3.1](09-training-and-distillation.md) |
| No impersonation | Never presented as a 법무부, HiKorea or 법제처 service, and never uses their marks | [15 §6](15-security-and-deployment.md) B5 (INFERRED) |

### 6.2 Future enterprise requirements (only if the owner pursues institutional use)

Each item is a condition, not a commitment. B-numbers refer to
[15 §6](15-security-and-deployment.md).

1. **Infrastructure the institution controls.** Self-hosted weights pinned by
   revision SHA; no `:free`, trial or unreviewed paid channel (B3).
2. **A lawful basis for any personal data** under PIPA, plus data minimisation
   and retention rules ([11 §7](11-dataset-governance.md)). REQUIRES LEGAL REVIEW.
3. **Its own Open API credential.** The institution files its own OC
   application and registers its use; Waymaker's OC is never proxied (B4,
   SEC-07).
4. **Commercial-use status confirmed per law API family** with 법제처 before
   any paid offering (B7).
5. **Public-sector security, certification and procurement requirements.** Not
   researched in Mission 001 (B8, UNVERIFIED); no compliance claim may be made.
6. **Access control and separation of duties.** Reviewer and publisher are
   different people; one operator cannot publish alone (SEC-16).
7. **Reproducibility and audit.** Every output reproducible from its package
   hash, model revision, adapter id and prompt hash (B9); durable storage
   (SEC-21); no public diagnostics (SEC-01).
8. **Attribution and integrity of statute text.** Verbatim quotation with the
   law.go.kr attribution, URL, `retrieved_at` and `content_sha256` (B2).
9. **Named human reviewers** with an adjudication rule; review warnings never
   hidden (B1, G5).
10. **Evaluation before use.** The institution's own frozen eval set, the hard
    gates of [12 §7.2](12-evaluation-methodology.md), and re-evaluation on every
    new manual or law version (regulatory change monitor,
    [05 §2](05-legal-intelligence-architecture.md) row H).
11. **Scope separation.** Visa-issuance and stay procedures, and parent and
    subcode rules, separated in data, retrieval and any adapter (B6).
12. **Tool-surface hygiene** if an MCP or tool surface is exposed:
    server-side credentials only, advertised tools equal callable tools, refuse
    unauthenticated non-loopback binds (B10).
13. **Licence-mandated attributions** for the chosen base model shown in UI
    chrome or an about page (models.md Rec. 6).

## 7. Decisions for the owner

1. **Athena's reasoning channel.** Which channels may receive real questions
   ([09 §6](09-training-and-distillation.md); SEC-02). REQUIRES LEGAL REVIEW.
2. **Whether government or institutional use is in scope at all**, and which
   requirements in §6.2 become binding (SEC-23).
3. **China-origin families for self-hosted weights.** Whether
   `CHINESE_ONLY_MODEL_PREFIXES` covers self-hosted fine-tunes and Qwen-derived
   Korean models (models.md Rec. 2). This moves Qwen in or out of every shortlist.
4. **The Athena bake-off.** Authorise rented multi-GPU time for Solar Open 2,
   A.X K2 and K-EXAONE 2.0 (Mission 002).
5. **Reviewers.** Name the people who adjudicate labels and outputs (G0, G5).

## 8. Not established by this document

- No Athena or Hestia component was built, and no model was evaluated on
  Waymaker packages. All candidate scores in §3.2 are vendor-reported except the
  KCL figures.
- The failure analysis in §2 is from the audited commit and offline probes;
  production behaviour of `/api/ask` on legal questions was not observed (AI
  POSTs were out of bounds for every agent; [15 §8](15-security-and-deployment.md)).
- The law-stack fixes F1-F8 are uncommitted in this branch and verified offline
  only (law-stack-fixes.md); their production effect is INFERRED.
- The checklist modules on `fc896c2` were read for their roles and states only,
  not audited.
- Public-sector security and procurement requirements, and whether any channel
  terms bind OpenRouter-mediated calls, were not researched or are UNVERIFIED.

## 9. Sources

- [research-notes/training-distill.md](research-notes/training-distill.md):
  §0.6-§0.9, §2.0-§2.2, §3.3, §4.1-§4.7, §5, §6 and the verification pass
  (claims 10, 13; not filled #4).
- [research-notes/models.md](research-notes/models.md): header, §0 items 3-5,
  §3b, §4, §5 (Athena, Hestia), §6, §7, §9 Recs. 2, 3, 6, and the verification
  pass (claims 9-13).
- [research-notes/cost.md](research-notes/cost.md): §0.5, §0.6, §9, §10, §11
  scenario 4 and the verification pass.
- [research-notes/ai-lifecycle.md](research-notes/ai-lifecycle.md): §2.1, §2.6,
  §2.7, §2.8, §5, §10 (R1, R3, R5, R6, R11, R12) and the verification pass.
- [research-notes/law-stack.md](research-notes/law-stack.md) §0 findings 1-3;
  [research-notes/law-stack-fixes.md](research-notes/law-stack-fixes.md) F1-F5,
  "Behaviour the owner should know", "Not done here";
  [research-notes/law-identity.md](research-notes/law-identity.md) §3, §6;
  [research-notes/status-classifier.md](research-notes/status-classifier.md) §10.
- Document-set sections relied on: [05 §2-§5](05-legal-intelligence-architecture.md),
  [06 §3-§5](06-temporal-law-and-source-identity.md),
  [07 §1-§5](07-evidence-verification-design.md),
  [08 §2, §10.3, §10.4](08-foundation-model-research.md),
  [11 §4.5, §7](11-dataset-governance.md),
  [12 §1, §3.5, §4.2, §7](12-evaluation-methodology.md),
  [13 §1, §6, §13](13-artemis-experiment.md),
  [14 §7.4, §8](14-hardware-and-cost-model.md),
  [15 §1, §6, §8](15-security-and-deployment.md).
- Related documents: [00](00-executive-summary.md),
  [01](01-existing-system-audit.md),
  [05](05-legal-intelligence-architecture.md),
  [06](06-temporal-law-and-source-identity.md),
  [07](07-evidence-verification-design.md),
  [08](08-foundation-model-research.md),
  [09](09-training-and-distillation.md), [11](11-dataset-governance.md),
  [12](12-evaluation-methodology.md), [13](13-artemis-experiment.md),
  [14](14-hardware-and-cost-model.md), [15](15-security-and-deployment.md),
  [17](17-mission-002-plan.md).
