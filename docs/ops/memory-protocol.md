# Paradiso Memory Protocol

This protocol defines how Paradiso agents keep durable memory across work sessions. Slack can start or discuss work, but GitHub must hold the lasting state.

## Memory Layers

| Layer | Stores | GitHub location | Who can update |
| --- | --- | --- | --- |
| Project Memory | Mission, risk principles, source policy, production gates, durable-memory rules. | `docs/ops/project-memory.md`, `docs/ops/permission-model.md`, `docs/ops/agent-registry.md` | Human maintainers and Ops Orchestrator proposals reviewed by humans. |
| Agent Memory | Role scope, permissions, current state, blocked items, last report path. | `docs/ops/agents/*.md`, `data/ops/agent_state.template.json`, live state files derived from templates. | Each agent may update its own report/state proposal; structural changes need human review. |
| Task Memory | Task owner, status, priority, supporting agents, issue/PR/report links, next action. | GitHub Issues, PRs, `data/ops/task_registry.template.json`, task reports under `reports/`. | Ops Orchestrator and assigned owner agents. |
| Evidence Memory | Source checks, source status, citations, audit outcomes, unresolved claims. | `data/ops/source_index.template.json`, `reports/source-audits/`, GitHub Issues/PR comments. | Source Evidence Auditor, Immigration News Monitor, Risk Chair. |

## Required Read Order

Before starting work, every agent must read:

1. `docs/ops/project-memory.md`
2. `docs/ops/permission-model.md`
3. `docs/ops/agent-registry.md`
4. Its own file in `docs/ops/agents/`
5. Relevant task, source, regression, translation, or risk files
6. Linked GitHub Issue, PR, report, and decision-log entries

If an agent cannot access required memory, it must report `blocked` and create or update a GitHub Issue or report explaining the missing context.

## Writing Results Back

Every completed or blocked agent run must write durable results to GitHub memory:

| Result type | Required writeback |
| --- | --- |
| Daily or weekly operational summary | `reports/daily/` plus linked GitHub Issue when action is needed. |
| Source audit | `reports/source-audits/` and `data/ops/source_index` update proposal. |
| News signal | `reports/news-monitor/` and issue if source-confirmed follow-up is needed. |
| UX audit | `reports/ux-audits/` and linked issue/PR comment. |
| Regression run | `reports/regression/` and regression case update proposal. |
| Translation QA | `reports/translation/` and glossary update proposal. |
| Risk review | `reports/risk-reviews/` and PR/issue decision comment. |

## Slack Writeback Rule

Slack commands must not be treated as memory by themselves. A Slack command should trigger one of these durable writebacks:

| Slack action | Durable GitHub writeback |
| --- | --- |
| Request an audit | Create or update a GitHub Issue with owner agent, inputs, and acceptance criteria. |
| Request a report | Commit a report under `reports/` or attach it to a PR/Issue. |
| Approve a sensitive action | Record approval in the relevant PR/Issue with approver, date, scope, and limits. |
| Discuss a blocker | Update the task issue with blocker, owner, next action, and due date if known. |
| Route work to an agent | Update task registry fields or issue labels/comments. |

## Preventing Forgotten Issues

Unresolved claims, blocked tasks, stale evidence, failing regression cases, and pending approvals must remain visible in GitHub until closed. Agents must:

- Record every unresolved item in a GitHub Issue, report, or live registry file.
- Include a `nextAction` and `ownerAgent` for each unresolved task.
- Preserve `sourceStatus` and `riskStatus` rather than overwriting them with vague summaries.
- Re-open or comment on stale items during daily/weekly Ops Orchestrator summaries.
- Never mark a task complete from Slack discussion alone.
