# Paradiso Project Memory

Paradiso is an AI-powered Korean visa and residence information platform for foreigners in Korea. Its purpose is to help users understand immigration and residence processes in a careful, source-grounded way without replacing official guidance, licensed legal advice, or direct confirmation from Korean authorities.

## Target Users

Paradiso serves foreigners in Korea and people preparing to come to Korea, including students, workers, spouses and family members, long-term residents, employers, school staff, and support organizations. Many users may be navigating immigration rules in a second or third language, so the product must be accurate, cautious, and clear about uncertainty.

## Official-Source-First Principle

Paradiso must ground immigration and residence claims in official sources first. Preferred sources include HiKorea, Ministry of Justice immigration materials, official immigration manuals, Korean statutes, enforcement decrees, enforcement rules, and official notices.

Agents must not invent immigration guidance. If a claim cannot be tied to an official source, the claim must be treated as uncertain and must not be promoted into production data or user-facing guidance.

## Evidence Status

Paradiso uses these evidence classifications:

| Status | Meaning | Allowed use |
| --- | --- | --- |
| `source-confirmed` | Directly supported by an official source that was checked and recorded. | May support reports, issue recommendations, and gated data update plans. |
| `contextual-only` | Helpful background from non-primary sources or prior internal notes, but not enough for production immigration guidance. | May inform research direction only. |
| `unavailable` | No reliable source is currently available or accessible. | Must not support production guidance. |
| `unresolved` | The claim is still under review, contradictory, stale, or incomplete. | Must remain open in GitHub memory until resolved. |

## Production Data Update Gate

Production visa/status data includes `visa_data.json`, `backend/data/visas.json`, `doc_master.json`, and official-source mapped production data files. These files must not be changed by routine agent work.

Production visa/status data edits require all of the following:

1. Source Evidence Auditor approval.
2. Data Update Planner plan.
3. Regression & Test pass.
4. Risk Chair `GO`.
5. Explicit human approval.

Agents may create reports, plans, GitHub Issues, or PR comments about production data concerns, but they must not autonomously update production immigration data.

## Durable Memory Rule

Slack is only the command, notification, and discussion interface. Slack threads, reactions, and messages are not durable operational memory.

GitHub is the durable source of truth. Important agent memory, task state, evidence, audit results, decisions, and unresolved risks must be written back to GitHub files, GitHub Issues, pull requests, or reports under `reports/`.

## Human Approval Requirement

Any legal, immigration-sensitive, or production-data-impacting change requires explicit human approval before implementation or release. When uncertainty remains, agents must preserve the uncertainty in GitHub memory and escalate rather than presenting a confident answer.
