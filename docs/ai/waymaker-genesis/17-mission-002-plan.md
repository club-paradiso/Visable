# 17 — Mission 002 plan

Status: **plan (NOT STARTED)**. The order is by risk to users first, then by what
unblocks measurement. Nothing here needs paid compute except where a step says so,
and every such step needs the owner's approval.

## 0. Owner decisions that block or shape the work

| # | Decision | Why it blocks | Evidence |
|---|---|---|---|
| OD-1 | ~~Fix the 시행규칙 제73조 data~~ **Done in PR #673 (2026-10-21)**: the text in force is shown now (no card payment; 등록증 fees cash or proof of cash payment only, 제1호 가목) and the amended text switches in automatically at 2027-09-16 00:00 KST | — | [01 §9](01-existing-system-audit.md) ESA-01 |
| OD-2 | Legal review of the production model channels | OpenRouter `:free` Nemotron routes are served under the NVIDIA API Trial terms, which forbid production use. The Thinking Machines free tier and the Google AI Studio unpaid tier also restrict personal data and output use. This affects the live answer path, not only distillation | [09 §6](09-training-and-distillation.md), [15](15-security-and-deployment.md) |
| OD-3 | Provenance remedy for `backend/services/law_query_normalizer.py` | It closely translates korean-law-mcp code, some of which is labelled as ported from LexDiff (BSL 1.1 since 2026-04-13). The notices are incomplete and two docs say no code was copied | [03](03-reference-provenance.md). The inaccurate "no code copied" statements and the missing LexDiff note were corrected on 2026-10-21; the legal review and the clean-room replacement remain |
| OD-4 | Merge or rebase `fix/waymaker-qa-2026-10-16` | The `/api/ask` wiring of the new guard, the reconciliation split and D4 all live in files that branch changes | [05 §3](05-legal-intelligence-architecture.md) |
| OD-5 | Branch protection on `main` (required checks) | Merges currently need no green CI. GitHub auto-merge cannot be used safely for that reason (observed with PR #666) | [15](15-security-and-deployment.md) |
| OD-6 | Who reviews benchmark labels | No label is human-verified. Only `PROVISIONAL_GO` is possible until the `critical` labels are reviewed by the owner or a licensed professional | [12](12-evaluation-methodology.md), [16](16-validation-results.md) |
| OD-7 | China-origin model route policy for ko/en roles | It excludes Qwen and DeepSeek from the Artemis and Athena shortlists | [08](08-foundation-model-research.md) |

## 1. Step 1 — close the user-facing and safety items (small, no new architecture)

1. **Data fixes:** (제73조 done in PR #673.) The superseded 출입국관리법
   (272921 → 290729) and 시행령 (289697 → 290501) versions in `author_rules.py`;
   the stale 국적법 시행령/시행규칙 ids; the F-4 notice number (제2026-35호 vs
   제2026-65호); the trainee-rule title; the stale `document_help.json` link.
   Each fix cites the law.go.kr capture of 2026-10-19 and goes through the normal
   review path. No data file is edited without the owner.
2. **`/api/ask` wiring (after OD-4):**
   - pass `article_evidence_from_law_pack(pack)` to `_apply_law_citation_guard`;
   - split "law located" from "article verified" in
     `_reconcile_law_verification_with_evidence`;
   - make `citationsTrustworthy` a per-answer fact;
   - fix D4 in `legal_analysis.py:718-719`;
   - read the request `context` field, which is currently truncated and ignored.
3. **Rate limits** on `/api/legal/*` and the Vercel law probe. These spend the
   owner's OC without limit.
4. **HTTP scheme swap:** look for `LAW_API_PLAINTEXT_RETRY_REACHED` in Railway
   logs (added by F8). If it never fires, make the plaintext retry opt-in.
5. **Deterministic classifier fixes ("B-fixed"),** each with benchmark items:
   - stop the silent subcode → parent fill in `understanding.understand`;
   - fix the hash-seed nondeterminism in `_detect_visa_codes`;
   - stop false positives such as `a 3` → A-3 and `2nd` → A-2;
   - fix the wrong-code truncation in `legal_analysis` (`D-4-2K` → `D-4-2`);
   - fix the Python task detector's missing visa-issuance and re-entry routes.

   Re-run benchmark v0 afterwards. This is the input to Artemis decision rule D1
   ([13 §6](13-artemis-experiment.md)).

## 2. Step 2 — make WLIE real (backend integration)

1. Pull a small typed law client out of `law_tools.py`, and route
   `precedent_sources`, `legal_evidence`, the cloud fallback and the legacy
   clients through it. Add the official version families: the `eflaw` list and
   body with `efYd`, `lsJoHstInf` per article, and the `lsHstInf` daily feed,
   plus 부칙 and 별표 parsing from the body ([04](04-official-api-capability-matrix.md)).
2. Capture sanitized, real DRF responses (with the owner's OC on Railway or a
   registered local OC, never committed) to replace the shape assumptions in
   fixtures.
3. Implement `LawToolsAdapter` (`contracts.LegalSourceAdapter` over the new
   client), and pass the same verification suite that runs over fixtures.
4. Move `waymaker_ai/legal/*` into `backend/services/legal_intelligence/` once the
   promotion criteria in [05 §3](05-legal-intelligence-architecture.md) hold.
   Then wire it into `/api/ask` in **audit mode** first: it computes and logs
   layer results but changes no answer. Compare it with the existing guard on
   real traffic for at least a week before enforcing.
5. Regulatory change monitor: a daily `lsHstInf` poll over the identity
   watch-list. It detects promulgated vs effective changes and
   future-effective amendments, and creates review tasks in the Knowledge
   Platform. It never auto-publishes.

## 3. Step 3 — benchmark v1 (measurement you can trust)

- Human review of every `critical` label (OD-6). Record reviewer and date in
  `label_review`.
- Re-capture 출입국관리법 and 시행령 article text from law.go.kr. The 2026-10-19
  captures of these were lost to the disk-full episode. Add real-evidence cases
  for B, C, I, L and a real J case (2026.9 manual vs the 2026-10-02 versions).
- More non-adversarial legal items in dev; splits by `case_template` only.
- Abstention items scored with real model baselines through the
  `openai_compatible` adapter against a local server.

## 4. Step 4 — first Artemis experiment (arm A, then decide)

Preconditions: steps 1.5 and 3 are done. Arm A (untuned Gemma 4 E4B at the pinned
revision) runs on a free Kaggle or Colab GPU, estimated $0–2 ([13](13-artemis-experiment.md),
[14](14-hardware-and-cost-model.md)). Then:

- if B-fixed already meets the targets, keep the rules and do not train;
- otherwise, and with a validated train split built by template, run arm B
  (SFT + QLoRA). Its budget needs the owner's approval.

Arm C (verified distillation) stays blocked until the teacher policy has a
named legal sign-off (`configs/teacher_policy.json`, `legal_signoff`).

## 5. Later (not before steps 1–3)

Athena over WLIE evidence packages with a stronger external or open-weight
reasoner ([10](10-athena-and-hestia-strategy.md)). The Hestia prototype as
option A: existing models plus a workflow, public sources only, and no
institutional data. A Waymaker MCP surface exposing typed WLIE results, only
after WLIE is in the backend.
