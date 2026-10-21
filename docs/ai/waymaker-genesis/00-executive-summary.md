# 00 — Executive summary (Mission 001, Waymaker Genesis)

Status: **COMPLETED** for the research and evaluation groundwork. No model was
trained and nothing was deployed by this branch. One separate security PR (#666)
was merged by the owner.

## What is now true

1. **The existing system is mapped, with evidence** ([01](01-existing-system-audit.md)).
   The audit answers 18 questions about the law-API integration and consolidates a
   risk register. The most serious user-facing defect found is in the
   status-guidance runtime data: it presents the 2027-09-16 text of 출입국관리법
   시행규칙 제73조 as the text in force today. As a result, one line tells users
   that registration-card fees may be paid by card, while the provision in force on
   2026-10-19 says cash or proof of cash payment only. At the owner's instruction this
   is fixed in PR #673: the text in force is shown now, and the amended text switches
   in automatically at 2027-09-16 00:00 KST.
2. **The law-API client had measurable failure-as-absence defects, and 12 surgical
   fixes landed on this branch** (F1–F12,
   [research-notes/law-stack-fixes.md](research-notes/law-stack-fixes.md)). Among
   them: statute rows were dropped on `/api/ask`; a title-only hit authorised every
   article number; empty, HTML or official-error bodies were read as "law not
   found"; an off-host 302 redirect sent the owner's OC to the other host; and a
   deeply nested body could take seconds of CPU or escape the parser. Each fix
   has a regression test that fails on `main`. On the benchmark, the backend's
   false absence declarations went from 6/14 to 2/14. The F10 rule keeps the UI's
   uncertainty notice honest: "verified" now requires article text that was
   fetched and matched.
3. **An original legal-intelligence design exists, built on the official API and
   not copied from the reference project** ([05](05-legal-intelligence-architecture.md),
   [06](06-temporal-law-and-source-identity.md), [07](07-evidence-verification-design.md)).
   - A source's identity is its 법령ID. A version is the pair
     (법령일련번호, 시행일), because a single promulgation can carry several
     effective dates (시행일).
   - The temporal resolver returns candidate versions with warnings. It never
     makes a legal determination.
   - A seven-layer verifier keeps "the law exists" apart from "the claim follows",
     and never reports a lookup failure as absence.
   - The reference implementation lives in `experiments/waymaker-ai/`
     (standard library only) and is not yet wired into `/api/ask`.
4. **Measurement is in place** ([11](11-dataset-governance.md), [12](12-evaluation-methodology.md), [16](16-validation-results.md)).
   - Dataset schema and a deterministic validator.
   - Benchmark v0 with 188 examples. Its real law fixtures were captured from
     law.go.kr with provenance.
   - A runner that compares six baselines.
   - Blind re-labelling by two independent annotators, who agreed with the labels
     on all 50 overall statuses.
   - Results: WLIE reached PROVISIONAL_GO with 0 critical legal errors. The
     existing backend and both deterministic classifiers are NO_GO. No label is
     human-verified yet.
5. **Model, training and cost research is done; nothing was trained**
   ([08](08-foundation-model-research.md), [09](09-training-and-distillation.md),
   [10](10-athena-and-hestia-strategy.md), [13](13-artemis-experiment.md),
   [14](14-hardware-and-cost-model.md)).
   - Artemis: the first experiment is prepared, not run. It uses Gemma 4 E4B, an
     Apache-2.0 model pinned to an exact revision, with arms A, B and C, gates,
     a runbook, and a teacher policy that denies by default.
   - Deterministic rule fixes come before any training.
   - Self-hosting only pays off at roughly 0.4–2 million questions a month.

## What needs the owner

The owner decisions are listed in [17 §0](17-mission-002-plan.md):

- **legal review of the production model channels**: OpenRouter `:free`
  Nemotron routes are served under NVIDIA API Trial terms that forbid production
  use;
- the provenance of `law_query_normalizer.py`, which was ported from korean-law-mcp
  and partly from LexDiff, now under BSL 1.1;
- merging the unpushed QA branch, so that the new guard can be wired into
  `/api/ask`;
- branch protection on `main`;
- who reviews the benchmark labels.

## Honest limits

- The benchmark labels are synthetic or machine-checked.
- The v0 holdout has been looked at 9 times and is no longer held out.
- The CI workflow has not run on GitHub yet.
- No live Open API call was made with an owner credential.
- A separate final red-team panel was not run ([16 §5](16-validation-results.md)).
