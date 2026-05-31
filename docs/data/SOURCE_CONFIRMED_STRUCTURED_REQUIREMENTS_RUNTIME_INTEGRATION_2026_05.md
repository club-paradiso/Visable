# Source-Confirmed Structured Requirements — Runtime Integration (2026-05)

## Why this PR follows PR #228

PR #228 added the structured manual-evidence layer
(`backend/data/manual_grounding/structured_requirements_2026_05.json`: 337 entries,
2,546 document items, 42 statuses) plus a validator, but **intentionally did not wire
it into runtime**, because 334 of 337 entries are candidate evidence pending human
review. Only the 3 locally-verified groundings are HIGH-confidence and READY.

This PR makes those **3 source-confirmed entries** usable at runtime — in the
backend helper, the API, the AI grounding prompt, and (safely) the detail UI — while
keeping every needs-review entry hidden from user-facing paths.

## Source-confirmed exposure policy

An entry is **source-confirmed** (and may reach users) only when **both**:

- `confidence == "HIGH"`, **and**
- `readinessLabel == "STRUCTURED_EVIDENCE_READY"`

Everything else (`needs_human_review`, `NEEDS_PAGE_CITATION`,
`NEEDS_SUBCODE_REVIEW`, `NEEDS_SCENARIO_REVIEW`, `SCHEMA_GAP`, `DO_NOT_USE`,
MEDIUM/LOW confidence) is candidate evidence and is **never** surfaced to user-facing
API/AI/UI. It is reachable only through an explicit internal/debug flag.

### Exact statuses exposed

| statusCode | procedure | scope | pages | document items |
|---|---|---|---|---|
| D-2 | extension (체류기간 연장) | parent-level (유학) | 43-44 | 8 |
| D-4 | extension | sub-codes D-4-1, D-4-7 only | 90-91 | 9 |
| E-7 | extension | parent-level (특정활동) | 226 | 10 |

- **Entries exposed:** 3
- **Document items exposed:** 27
- **Entries intentionally hidden:** 334 (of 337)
- **Statuses with source-confirmed evidence:** 3 (D-2, D-4, E-7)

## Backend / helper changes

New module `backend/structured_requirements.py`:

- Defensive cached loader (returns empty on missing/malformed file; never crashes startup).
- `get_structured_requirements(status_code, options)` — default returns **only**
  source-confirmed entries; `{"includeNeedsReview": True}` (internal) includes candidates.
- `get_source_confirmed_structured_requirements(status_code, options)` — always
  HIGH/READY only; honors `procedureType` / `subCode` / `readinessLabel` / `confidence` filters.
- `has_source_confirmed_structured_requirements(status_code)` → bool.
- `source_confirmed_status_codes()`, `is_source_confirmed(entry)`, `public_summary(entry)`
  (projects to a safe user-facing shape, omitting internal review fields).

## API changes

In `backend/paradiso_backend.py` (additive, backward-compatible):

- `/api/visas`: records for D-2/D-4/E-7 now carry an additive
  `sourceConfirmedStructuredRequirements` array (safe `public_summary` shape). All
  other records are unchanged; `count` and record identity are preserved. Candidate
  evidence is never included.
- New `GET /api/visas/{status_code}/structured-requirements`: returns source-confirmed
  entries by default; `?include_needs_review=true` is an **internal/debug** flag that
  additionally returns raw candidate entries under `internalNeedsReview` with an
  explicit warning. The two are never mixed into the default response.

## AI grounding changes

- New `_build_source_confirmed_structured_requirements_block(visa_code, visa_sub_code)`
  emits a block labelled **"Source-confirmed structured requirements from 2026-05
  official manuals"**, containing only HIGH/READY entries, with explicit page cites and
  sub-code scope (e.g. D-4 is marked `적용 세부약호: D-4-1, D-4-7`).
- `ask()` appends this block in both grounded and ungrounded paths, **after** the
  existing manual grounding and local-catalog block. It **supplements** and never
  overrides the manual grounding, warnings, disclaimers, or `manualRefs`.
- For any status without a source-confirmed entry (E-7-candidate rows, F-5, F-6, G-1,
  H-2, C-3, F-1, F-2, …), the block is empty — verified by tests.

## Frontend changes

- `index.html`: new `renderSourceConfirmedRequirements(v)` renders a
  **"출처 확인된 매뉴얼 요건 (Source-confirmed manual requirements)"** section in the
  visa detail view **only when** `v.sourceConfirmedStructuredRequirements` exists
  (i.e. D-2/D-4/E-7). It shows procedure type, sub-code scope, document items, and the
  page/section + manual citation. It reuses existing styled classes.
- The field reaches the UI only via `/api/visas`; the static `visa_data.json` fallback
  has no such field, so the section is simply absent offline (safe). No needs-review or
  MEDIUM/LOW content is ever rendered (the backend never sends it).

## Tests added

`backend/tests/test_structured_requirements.py` (14 tests):

1. helper loads (source-confirmed codes == D-2, D-4, E-7);
2. known READY status returns entries (all HIGH/READY);
3. needs-review excluded by default (high-risk statuses → 0; E-7 default → 1 confirmed only);
4. needs-review returned only with explicit internal option;
5. `/api/visas` exposes the field only for READY statuses + backward-compat shape/count;
6. AI prompt/block includes source-confirmed content for a READY status (D-4);
7. AI prompt/block excludes it for F-5/F-6/G-1/H-2/C-3;
8. dedicated endpoint defaults to source-confirmed only; internal flag gates candidates;
9. sub-code scope + `public_summary` field-omission checks.

## Test results

```
python3 -m pytest backend/tests/                # 223 passed (209 prior + 14 new)
python3 scripts/validate_structured_requirements.py <structured>   # PASS
python3 scripts/sync_visa_data.py --check       # OK (byte-identical; visa_data.json unchanged this PR)
python3 scripts/check_required_documents_coverage.py               # PASS (rc=0)
bash scripts/check_repo.sh                       # rc=0
```

## Known limitations

- Only 3 statuses (D-2, D-4, E-7), all `extension`, are exposed — that is the entire
  current source-confirmed set. The other 39 statuses remain candidate-only.
- D-4's exposed list is scoped to sub-codes D-4-1/D-4-7; other D-4 sub-codes are not
  covered and are explicitly labelled as such.
- `docMasterId` remains `null` in the structured layer; the runtime surfaces the
  verbatim Korean document text, not resolved doc IDs.
- No production document data (`visa_data.json`) was changed; exposure is at the
  API/serve layer only.

## Future promotion workflow

1. Human-review candidate entries for a high-risk status (priority: E-7 → F-5 → F-2 →
   F-1 → D-4 → F-6 → H-2 → G-1 → C-3 → D-10), confirming page/section/sub-code scope in
   the PDF.
2. Promote the verified entry in `structured_requirements_2026_05.json` to
   `confidence: "HIGH"` + `readinessLabel: "STRUCTURED_EVIDENCE_READY"` (and set
   `reviewStatus: "verified_locally"`).
3. Re-run `scripts/validate_structured_requirements.py` and the backend tests — the new
   entry then flows automatically into `/api/visas`, the endpoint, the AI block, and the
   UI, with no further code change.
4. Never set `verified=true` on production records or remove `needsManualReview`
   automatically; promotion is per-entry in the structured layer.
