# Paradiso Decision Log

Use this log for durable operational, source, risk, product, and governance decisions. Slack discussion is not enough; decisions must be recorded here or in a linked GitHub Issue/PR/report.

## Template

| Date | Decision | Context | Alternatives considered | Risk | Final owner | Follow-up required |
| --- | --- | --- | --- | --- | --- | --- |
| YYYY-MM-DD | Short decision title. | Why the decision was needed and what evidence was reviewed. | Options rejected or deferred. | Source, legal-information, UX, translation, regression, or operational risk. | Agent or human owner. | Issue, PR, report, or next action. |

## Starter Entry

| Date | Decision | Context | Alternatives considered | Risk | Final owner | Follow-up required |
| --- | --- | --- | --- | --- | --- | --- |
| 2026-06-07 | Establish GitHub as durable memory for Paradiso multi-agent operations. | Paradiso needs persistent agent memory for source audits, task state, evidence, QA, translation, regression, and risk review. Slack is useful for commands and discussion but cannot be the source of truth. | Slack-only memory; ad hoc local notes; autonomous production-data updates. | Losing unresolved immigration-sensitive issues or applying unsupported guidance. | Ops Orchestrator Agent with human maintainer oversight. | Implement Phase 1 alerts and GitHub report writeback before autonomous routing. |
