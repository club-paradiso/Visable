# Slack Agent Roadmap

Slack is the interface for commands, notifications, and discussion. GitHub remains the durable source of truth for memory, evidence, task state, reports, approvals, and decisions.

## Phase 1: Alerts and Health Reports

- Use one Slack app only.
- Send Slack Incoming Webhook alerts for GitHub Actions health reports and high-priority failures.
- Keep all durable results in GitHub reports, Issues, PRs, or files.
- Allow no autonomous editing.
- Route Slack messages to human-visible GitHub records before any agent work is considered complete.

## Phase 2: Commands and GitHub Writeback

- Add Slack slash commands for common requests such as source audit, regression run, UX audit, translation QA, and risk review.
- Use `workflow_dispatch` to trigger GitHub Actions jobs from approved commands.
- Write command outputs back to GitHub Issues or reports under `reports/`.
- Include task owner, source status, risk status, next action, and links in every writeback.
- Treat Slack discussion as transient context until it is recorded in GitHub.

## Phase 3: Logical Multi-Agent Routing

- Add logical routing through the Ops Orchestrator Agent.
- Use role-specific prompts and memory reads for each agent.
- Optionally run agents through OpenClaw or a cloud runner.
- Permit branch/PR creation only for scoped, non-production-data work unless all production gates are satisfied.
- Allow no production data edits without Source Evidence Auditor approval, Data Update Planner plan, Regression & Test pass, Risk Chair `GO`, and human approval.

## Phase 4: Long-Term Evidence Infrastructure

- Optionally add a cloud database or vector search for source snapshots and evidence retrieval.
- Maintain source snapshots for official manuals, notices, law pages, and source indexes.
- Build a long-term evidence index that links source claims, audit reports, task history, and production-data decisions.
- Keep GitHub as the canonical durable memory even if search/index infrastructure is added.
