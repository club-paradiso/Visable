# Source-Grounded Targeted Corrections — 2026-05

Inspection of all stay/visa status records with the intent to directly patch
only source-confirmed, low-risk data issues. After a full inspection, **no field
change qualified** under the safe-correction bar, so no data was modified. This
document records what was inspected and why nothing was patched.

> Honesty note: the intent of this PR was direct correction, not report-only.
> The outcome is zero corrections **because** the hard constraints
> ("do not invent source evidence", "do not patch without exact source
> support", "be extra conservative on high-risk codes") were applied strictly,
> and nothing cleared that bar.

## What was inspected

- **`visa_data.json`** — a JSON array of **58** stay/visa/scenario records.
- **`backend/data/visas.json`** — byte-identical to `visa_data.json` (parity OK).
- **`doc_master.json`** — a JSON array of **79** document definitions
  (`id` / `ko_name` / `en_name`).
- **1,207** document references across all `newReqDocs` / `extReqDocs` /
  `initialReqDocs` / `extensionReqDocs` / `changeReqDocs` / sub-code `addReqDocs`
  arrays.
- Committed crosswalk files under `docs/crosswalk/`.

## Findings

- **Document-reference integrity: clean.** All 1,207 references resolve to a
  `doc_master.json` id. **0 broken/missing doc-id references.**
- **No whitespace/typo anomalies** in core user-facing fields
  (`name`, `cat`, `period`, `newReq`, `extReq`, `note`, `addReq`).
- **Sub-code structure consistent:** all 139 sub-code entries use the same shape
  (`code`, `name`, `addReq`, `addReqDocs`, `note`, optional `aliases`).
- **`DATA_MISSING` sentinels** are widespread and deliberate:
  `documents_registration` ×58, `documents_extension` ×25,
  `documents_initial` ×19, `hikorea_task_type` ×48. These mark
  not-yet-sourced fields; filling them needs exact manual citations that are not
  committed in usable form.

## Corrections applied

**None (0).** No candidate satisfied all of: official/committed source support,
exact page/section/article or committed crosswalk record, clear target JSON path,
clear conditional/sub-code boundary, and preservable parity.

## Skipped items (and why)

- **`D-4-2K` appears twice.** This duplicate is intentional and is asserted by a
  backend regression test (`D-4-2K pre-existing duplicate … must still appear
  twice`). Not a defect → not touched.
- **`DATA_MISSING` fields / empty manual citations.** Every committed crosswalk
  file is explicitly self-marked non-authoritative
  (`TEMPLATE_NOT_SOURCE_VERIFIED`, `DRAFT_PLACEHOLDER`, `PLANNING_ONLY`) with
  empty or `pending`/placeholder entries. Populating data from them would invent
  source evidence → skipped.
- **High-risk codes** (`F-6`, `G-1`, `H-2`, `D-10`, `E-7-4`, `D-4` subcodes,
  `C-3` subcodes, `B-2` / Jeju, scenario/helper records). No exact
  sub-code/scenario source support is committed in a usable (non-placeholder)
  form → no content patched.

## Validation (run against the unchanged data)

```
python3 -m json.tool visa_data.json                       # PASS
python3 -m json.tool backend/data/visas.json              # PASS
python3 -m json.tool doc_master.json                      # PASS
python3 scripts/sync_visa_data.py --check                 # OK (in parity)
python3 scripts/check_required_documents_coverage.py      # PASS (58 statuses, rc=0)
bash scripts/check_repo.sh                                 # rc=0 (incl. backend tests)
ALLOW_BACKEND_TEST_SKIP=1 bash scripts/check_repo.sh      # rc=0
```

## Non-goals

- No full legal verification claim.
- No metadata promotion (no `verified=true`; no removal of review flags).
- No law grounding activation.
- No unsourced corrections (no invented citations / `manualRefs`).
- No UI redesign; no changes to employment helper files or
  `data/jobcode_master.json`.
