# Waymaker Genesis — Mission 001 documents

Mission 001 set out to establish the research, data, legal-source and evaluation
groundwork for Waymaker. The goal was to make later model decisions (Artemis,
Athena, Hestia) measurable before any training or production change. Start with
[00-executive-summary.md](00-executive-summary.md). The Korean final report is
[MISSION-001-REPORT.ko.md](MISSION-001-REPORT.ko.md).

Status vocabulary: COMPLETED, VERIFIED, PARTIALLY COMPLETED, IMPLEMENTED BUT NOT
VALIDATED, RESEARCHED ONLY, BLOCKED, DEFERRED, NOT STARTED.

| Doc | Subject | Status |
|---|---|---|
| [00](00-executive-summary.md) | Executive summary | COMPLETED |
| [01](01-existing-system-audit.md) | Existing system audit: lifecycle, components, 18 law-API questions, risk register | COMPLETED |
| [02](02-korean-law-mcp-study.md) | korean-law-mcp capability study and comparison matrix | RESEARCHED ONLY |
| [03](03-reference-provenance.md) | Reference provenance, licences, clean-room policy | RESEARCHED ONLY (one item REQUIRES LEGAL REVIEW) |
| [04](04-official-api-capability-matrix.md) | Official Open Law API catalogue, terms, identities as of 2026-10-19 | RESEARCHED ONLY |
| [05](05-legal-intelligence-architecture.md) | WLIE architecture decision | COMPLETED (decision); reference code IMPLEMENTED BUT NOT VALIDATED |
| [06](06-temporal-law-and-source-identity.md) | Identity and temporal resolver (normative) | IMPLEMENTED BUT NOT VALIDATED |
| [07](07-evidence-verification-design.md) | Seven-layer evidence verification (normative) | IMPLEMENTED BUT NOT VALIDATED |
| [08](08-foundation-model-research.md) | Open-weight model landscape and licence matrix | RESEARCHED ONLY |
| [09](09-training-and-distillation.md) | Training techniques, distillation feasibility, provider terms | RESEARCHED ONLY |
| [10](10-athena-and-hestia-strategy.md) | Athena and Hestia strategy | RESEARCHED ONLY |
| [11](11-dataset-governance.md) | Dataset schema, validator, provenance rules | IMPLEMENTED BUT NOT VALIDATED (no human-verified labels) |
| [12](12-evaluation-methodology.md) | Metrics, baselines, gates, runner | IMPLEMENTED; run on benchmark v0 |
| [13](13-artemis-experiment.md) | First Artemis experiment | NOT RUN (configs and runbook ready) |
| [14](14-hardware-and-cost-model.md) | Cost model with dated prices | RESEARCHED ONLY |
| [15](15-security-and-deployment.md) | Security and deployment | RESEARCHED ONLY; F1–F12 fixes IMPLEMENTED BUT NOT VALIDATED in production |
| [16](16-validation-results.md) | What was run, evidence ledger, red-team review | COMPLETED |
| [17](17-mission-002-plan.md) | Mission 002 plan and owner decisions | NOT STARTED |

`research-notes/` holds the evidence-tagged research notes. Each note ends with an
adversarial verification pass whose corrections take precedence. It also holds the
law-stack fix log, the adjudication log and the blind-label audit. Code and data live in
[`experiments/waymaker-ai/`](../../../experiments/waymaker-ai/README.md).
