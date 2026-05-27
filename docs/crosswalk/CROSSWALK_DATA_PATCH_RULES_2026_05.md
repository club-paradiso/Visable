# Crosswalk Data Patch Rules - 2026.5

## Purpose

These rules define when a completed manual/law/HiKorea crosswalk may be used to patch Paradiso production data.

## Hard gates before patching

A data patch is allowed only when all of the following are true:

1. The source is official.
2. The source title, publication/effective date, URL or local path, and page or article are recorded.
3. The source directly supports the target field.
4. The target file and JSON path are recorded.
5. `visa_data.json` and `backend/data/visas.json` parity can be preserved.
6. Conditional requirements remain conditional.
7. Sub-code-specific requirements remain sub-code-specific.
8. Manual/law conflicts are marked for review, not silently patched.
9. `needsManualReview` is not removed in a data patch PR.
10. Verification metadata is not promoted in a data patch PR.

## Patch readiness labels

| Label | Meaning |
| --- | --- |
| READY_FOR_FIELD_PATCH | Exact source and target field are known and no conflict remains. |
| NEEDS_PAGE_CITATION | Manual/guide source exists but exact page/section is missing. |
| NEEDS_ARTICLE_CITATION | Law source exists but exact article is missing. |
| NEEDS_ATTACHMENT_ARCHIVE | Official attachment route exists but file/checksum archive is missing. |
| LAW_MANUAL_CONFLICT_REVIEW | Law and manual may conflict. Human review required. |
| SUBCODE_AMBIGUITY_REVIEW | Sub-code boundaries are unclear. Human review required. |
| SCHEMA_GAP | Existing JSON schema cannot represent the requirement safely. |
| DO_NOT_PATCH | Source support is insufficient or out of scope. |

## Forbidden patch behavior

Do not:

- turn conditional requirements into universal requirements,
- merge sub-code requirements into a top-level status without labels,
- delete review flags because a source exists,
- claim legal verification without full field coverage,
- use HiKorea service pages as a substitute for legal/manual authority when field-level procedure/document support is needed.

## Required checks for future data PRs

Future data PRs should run:

```bash
python3 -m json.tool visa_data.json > /tmp/visa_data_check.json
python3 -m json.tool backend/data/visas.json > /tmp/backend_visas_check.json
cmp -s visa_data.json backend/data/visas.json && echo "visa data parity OK" || echo "visa data parity differs"
```

A parity difference must be intentional, documented, and reviewed.
