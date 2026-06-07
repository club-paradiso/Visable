# Paradiso Agent Permission Model

The permission model limits what agents may do without human approval. Higher levels include the ability to perform lower-risk reporting actions only when explicitly granted by role.

## Permission Levels

| Level | Meaning | Examples | Default production-data access |
| --- | --- | --- | --- |
| `read-only` | May inspect GitHub files, Issues, PRs, and reports. | Read memory, source indexes, audit reports. | None. |
| `report-only` | May create reports or comments that do not change product behavior. | Source audit report, UX audit report, risk review report. | None. |
| `issue-create` | May create or update GitHub Issues for tracked work. | Open a source-follow-up task, file a regression gap. | None. |
| `branch-create` | May create branches for non-production-data work. | Documentation branch, test-only branch. | None unless explicitly gated. |
| `PR-create` | May open PRs for reviewed changes within role scope. | Docs PR, test PR, non-user-facing infra PR. | None unless explicitly gated. |
| `production-data-edit` | May edit production visa/status data only after all gates are satisfied. | Source-confirmed correction to status data. | Gated and exceptional. |
| `merge-approval` | May provide release recommendation, but final merge remains human-controlled. | Risk Chair `GO`, `NO-GO`, or `GO WITH WARNING`. | Does not replace human approval. |

## Protected Production Data

The following files and any official-source mapped production data files are protected:

- `visa_data.json`
- `backend/data/visas.json`
- `doc_master.json`
- official-source mapped production data files
- existing visa/residence content unless explicitly required for documentation references

## Production Data Edit Gate

Production visa/status data edits require:

1. Source Evidence Auditor approval with `source-confirmed` evidence.
2. Data Update Planner plan naming affected files, tests, and rollback risks.
3. Regression & Test pass for relevant answer, grounding, search, UI, and translation cases.
4. Risk Chair `GO`.
5. Explicit human approval recorded in GitHub.

If any gate is missing, the only allowed outputs are reports, issues, comments, or plans. The change must not be merged into production data.

## Release Authority

No agent can approve production immigration data changes by itself. The Risk Chair can recommend release status, but human maintainers retain final authority for legal/immigration-sensitive changes and merges.
