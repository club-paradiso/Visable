# 05 — Waymaker Legal Intelligence (WLIE): architecture decision

Status: **architecture COMPLETED (decision); reference implementation IMPLEMENTED BUT NOT
VALIDATED; runtime integration NOT STARTED (deliberately)**.

WLIE is a provisional name for a set of responsibilities, not a new service. The
decision below reuses what Waymaker already has, adds the pieces that are missing,
and keeps every new piece offline until the benchmark can measure it.

## 1. Decision in one paragraph

Waymaker already has an official-law client (`backend/services/law_tools.py`), a
reviewed knowledge store with lifecycle and audit (`backend/services/knowledge/`), a
manual registry with fail-closed approval, two deterministic classifiers and an
answer guard ([01](01-existing-system-audit.md)). What it lacks is **legal identity
and time**: it cannot say which version of which provision governs a date. It also
cannot tell "the law was found" apart from "the claim is supported", and it reports
upstream failures as absence. WLIE therefore adds three pure-logic components:

1. an identity and temporal resolver,
2. a seven-layer claim verifier,
3. a bounded evidence-package builder.

These come with one shared contract module, and they live in
`experiments/waymaker-ai/` until the benchmark gates in
[12](12-evaluation-methodology.md) pass. This PR does not change the answer path
(`paradiso_backend.py`), because the owner has unpushed work there. The only
backend changes are surgical fixes to verified defects in the existing law client
([research-notes/law-stack-fixes.md](research-notes/law-stack-fixes.md)).

## 2. Responsibilities → concrete homes

| # | Responsibility (mission §15) | Exists today | Decision | Home |
|---|---|---|---|---|
| A | Official source connector | `law_tools.py` (typed `LAW_API_*` errors, injectable transport, URL sanitiser). It also has 5 overlapping wrappers and no `efYd`, history or 부칙 | **Extend, do not duplicate.** Surgical fixes now (F1–F8). In Mission 002, pull a small typed client out of `law_tools.py`, add the `eflaw`/`eflawjosub`, `lsHistory`, `lsJoHstInf` and `lsHstInf` targets ([04](04-official-api-capability-matrix.md)), and route `precedent_sources`, `legal_evidence` and the cloud fallback through it | backend (existing) |
| B | Legal identity resolver | Title matching by whitespace-stripped name; the public `source_id` prefers 법령ID; dates are collapsed | **New, small.** Exact-title resolution over official, former and short titles; near matches are reported, never substituted | `waymaker_ai/legal/identity.py` |
| C | Temporal law resolver | None | **New.** Candidate versions per anchor date, with ten warning rules ([06](06-temporal-law-and-source-identity.md)) | `waymaker_ai/legal/temporal.py` |
| D | Immigration norm graph | Knowledge Platform variants with `subcodes_covered`; manual registry; `law_sources` (14) in the status-guidance bundle | **No graph database.** Model the relationships as data: the law identity registry, delegation edges (from `lsDelegated`/`lsStmd` in Mission 002), and Knowledge Platform facts carrying a `Scope`. Revisit only if queries need multi-hop traversal | registry JSON + Knowledge Platform |
| E | Evidence retrieval | Knowledge Platform retrieval (reviewed facts only), `manual_search` (approved editions only), law client | **Reuse.** WLIE defines the provision-level retrieval contract (`LegalSourceAdapter`) so that retrieval stays swappable | contract in `contracts.py` |
| F | Claim verification | `citation_verifier`, `law_citation_guard` (token containment; blanket allow when "verified"), `statute_citation_guard` (wired only into search, with `evidence_available=False`) | **New gate, reusing the old vocabulary** (mapping in [07 §4](07-evidence-verification-design.md)). It replaces the token check on `/api/ask` in Mission 002, after the owner's branch lands | `waymaker_ai/legal/verification.py` |
| G | Immigration procedure engine | Knowledge Platform procedures and lifecycle; JS `status-guidance` resolver (16 procedures, explicit inheritance); procedure scope separation already enforced | **Reuse.** Fix detection, not modelling. Retrieval already refuses parent→subcode inheritance unless `subcodes_covered` allows it, but `understand()` silently fills in the parent when the text names a subcode ([01 §6](01-existing-system-audit.md)) | backend (existing) |
| H | Regulatory change monitor | `check_source_updates.py` only hashes local files; the HiKorea monitor has null baselines; law versions are pinned by hand and are already stale | **Extend the existing monitor.** Use the `lsHstInf` daily change feed filtered to the identity watch-list. Compare promulgated and effective dates. Emit review tasks into the Knowledge Platform. Never auto-publish | `scripts/` (Mission 002) |
| I | Model context builder | One flat prompt with law text appended | **New, bounded.** `EvidencePackage` with a public/diagnostic split, size caps and untrusted-content flags | `waymaker_ai/legal/evidence_package.py` |
| J | Audit and evaluation | Knowledge Platform audit log and eval corpus (69 cases, labels circular for detection) | **Add a benchmark and runner beside it**, not inside it, so labels and provenance can be governed separately | `waymaker_ai/dataset`, `waymaker_ai/evaluation` |

## 3. Why the new code lives in `experiments/` for now

* **Measured before trusted.** The verification rules are new. The benchmark labels
  are synthetic or machine-checked, and none is human-verified yet. Putting the gate
  in the answer path before people review a label set would amount to claiming
  legal reliability from passing unit tests.
* **No collision with in-flight work.** The answer path (`paradiso_backend.py`,
  `legal_analysis.py`, `ai_runtime.py`, `model_policy.py`) is being changed on the
  owner's unpushed branch `fix/waymaker-qa-2026-10-16`.
* **Standard library only.** The package imports without FastAPI or pydantic, so the
  runner can call the backend as a subprocess baseline instead of sharing its process
  state.

Promotion criteria to `backend/services/` (Mission 002):

1. the benchmark gates in [12](12-evaluation-methodology.md) pass on test and
   holdout;
2. a human has reviewed at least the `critical` labels;
3. live DRF responses (sanitized) have replaced the shape assumptions in fixtures;
4. the owner's branch has been merged;
5. a `LawToolsAdapter` implementing `LegalSourceAdapter` over the extracted client
   passes the same suite.

## 4. Data flow (target state)

```
question ─► deterministic understanding (status, subcode, procedure, dates, anchor)
         ─► retrieval: reviewed facts (Knowledge Platform) + approved manual chunks
                       + law client (identity → versions → provision → 부칙)
         ─► temporal resolver (candidate versions, warnings)
         ─► EvidencePackage (bounded; public/diagnostic split; source text quoted as data)
         ─► model (Artemis for routing/extraction, Athena for reasoning over the package)
         ─► structured answer with claims
         ─► claim verifier (L1–L7 per claim) ─► answer guard (existing) ─► render
         └─► audit record (package hash, versions used, layer results)
```

Any claim whose overall status is not `verified` is shown with its qualification, or
held back. The model never receives authority to name a source the package does not
contain.

## 5. Immigration norm and procedure model (mission §21–23)

The model reuses the Knowledge Platform fact schema (`requirement_level`,
`condition_kind` ∈ always / conditional / applicant_specific / office_discretion,
`authority_type`, lifecycle, citation) and adds three things as data, without
changing the schema in this PR:

* **Scope on every requirement:** `status_codes`, `subcodes`, `procedures`, and
  `all_subcodes_explicit`. A rule stated for E-7 says nothing about E-7-4 unless
  the source says it covers every subcode. This matches the existing
  `subcodes_covered` rule in retrieval.
* **Legal basis vs operational basis.** A requirement records whether its support
  is a legislative family (statute, decree, rule), an administrative rule or
  operational guidance (manual, HiKorea). A manual line does not become a legal
  obligation, and a statute that authorises a procedure does not supply the
  document list.
* **Procedure-specific predicates instead of universal rules.** Scenario L
  (representation) is modelled as separate, evidence-backed conditions per
  procedure: who may file, identity verification, delegation documents, and an
  in-person requirement. WLIE has no default answer to "can a family member file
  this?"; with no evidence for that procedure, the claim is
  `human_review_required`.

Procedure scope separation (visa manual vs stay manual) is enforced twice: in the
Knowledge Platform (`PROCEDURE_SCOPE_MISMATCH`) and in WLIE L6
(`procedure_scope_mismatch`).

## 6. MCP decision

Waymaker does not need an MCP server now. MCP is a transport, and the value lies in
verified identity, time and claim checks, which belong in an internal service first.
User questions are not routed to the third-party hosted korean-law-mcp: it returns
prose, its verification is weaker than its README claims, and it relies on an
anti-bot bypass ([02](02-korean-law-mcp-study.md)). A Waymaker MCP surface for
professional tools (Hestia: status-scoped grounding, verified source packets,
temporal queries, manual-edition comparison) becomes worthwhile only after WLIE is
in the backend and the gates pass. It would expose WLIE results with typed fields,
not prose.

## 7. What was deliberately not built

A full legal-system rewrite, a graph database, an MCP server, a second law client,
large-scale scraping, any model training, and any change to `/api/ask` behaviour
other than the surgical law-client fixes. See [17](17-mission-002-plan.md) for the
ordered next steps.
