# Scenario Procedure Variants — 2026-05

## Why This Layer Exists

Paradiso's user-facing `procedures` object was parent-code scoped. That remains
correct for procedures such as the uniform re-entry records added in PR #232,
but it cannot safely represent many change-of-status, activity-outside-status,
workplace-change, or status-grant checklists.

The official stay manual often divides those procedures by sub-code or
application scenario. Copying one branch into a parent-level checklist would
incorrectly imply that it applies to every user. Leaving the parent checklist
empty is safer, but it produces a generic fallback even when a narrow official
manual-backed example is available.

## Data Shape

Each parent procedure may now contain optional `variants`:

```json
{
  "procedures": {
    "statusChange": {
      "available": true,
      "summary": "체류자격변경 제출서류는 세부 자격과 신청 사유별로 다릅니다.",
      "requiredDocs": {
        "commonDocs": [],
        "requiredDocs": [],
        "additionalDocs": [],
        "conditionalDocs": []
      },
      "variants": [
        {
          "id": "d-9-1-status-change",
          "labelKo": "무역업(D-9-1) 체류자격 변경허가",
          "statusCode": "D-9-1",
          "scenarioKo": "무역비자 점수제 요건을 충족하여 무역업(D-9-1)으로 변경하는 경우",
          "requiredDocs": {
            "commonDocs": [],
            "requiredDocs": [],
            "additionalDocs": [],
            "conditionalDocs": []
          },
          "manualRefs": [],
          "notes": []
        }
      ],
      "manualRefs": [],
      "notes": []
    }
  }
}
```

The parent `requiredDocs` stays empty when no universal parent checklist is
safe. Each populated variant has its own ID, visible label, grouped checklist,
manual references, and notes. Existing parent-level procedures remain valid
without `variants`.

## Seed Records

All three seeds were checked against
`docs/source-manuals/2026-05/stay_manual_2026_05.pdf`. The repository helper
`scripts/extract_manual_page_text.py` verified that each cited printed footer
matches its PDF page number.

| Parent status | Procedure | Variant | Official manual page | Why it stays a variant |
|---|---|---|---|---|
| D-9 | `statusChange` | `d-9-1-status-change` | p. 131 | Checklist applies to point-system trade status `D-9-1`, not every D-9 change |
| F-1 | `statusChange` | `f-1-13-status-change` | pp. 347-348 | Checklist applies to parents or close relatives accompanying a foreign student below high-school level |
| E-9 | `workplaceChange` | `e-9-3-agriculture-workplace-addition` | pp. 328-329 | Checklist applies to the seasonal agriculture workplace-addition program for `E-9-3` |

These are proof-of-model records only. They are not a broad extraction batch.
Every seed retains `needsManualReview: true`; no `verified=true` field was set.

## UI And Runtime Behavior

- Existing parent-level `requiredDocs` render first and exactly as before.
- When parent `requiredDocs` is empty and populated variants exist, the UI
  renders labeled variant cards instead of only the generic fallback.
- Variant cards show this warning:
  `세부 자격 또는 신청 사유에 따라 제출서류가 달라질 수 있습니다. 아래 항목은 해당되는 경우에만 적용됩니다.`
- `/api/visas` preserves variants because the backend and union resolver return
  the canonical record dictionaries without dropping unknown additive fields.
- `scripts/sync_visa_data.py` copies the canonical JSON byte-for-byte into
  `backend/data/visas.json`, so deploy-context data preserves variants too.

## Validation

`scripts/check_required_documents_coverage.py` now validates variants:

- `id`
- `labelKo` or `label`
- grouped `requiredDocs` shape
- non-empty checklist unless `available=false`
- populated variant `manualRefs`
- retained `needsManualReview: true`
- rejection of `verified=true`

## Follow-Up Extraction Plan

Future batches can add variants procedure by procedure after direct page review.
Priority targets remain the blocked `statusChange`, `activitiesOutsideStatus`,
`workplaceChange`, and `statusGrant` branches. Each follow-up should add only
isolated sub-code or scenario records with exact official manual page citations;
it should not flatten a scenario checklist into a parent procedure.

## Safety Note

Scenario-specific requirements are not flattened into parent-level procedures.
Variants are labeled and shown only as applicable examples.
