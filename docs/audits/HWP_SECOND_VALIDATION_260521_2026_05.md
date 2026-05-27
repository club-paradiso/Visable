# HWP second validation - 260521 manuals

## Purpose

This report records the additional review of the user-provided HWP source files associated with the 2026.5 manuals.

## Validated HWP files

| File role | Result |
| --- | --- |
| Visa manual HWP | HWP 5.0 source file was confirmed. Preview text matched the visa manual title, publication month, publisher, and expected table-of-contents scope. |
| Stay manual HWP | HWP 5.0 source file was confirmed. Preview text matched the stay manual title, publication month, publisher, and expected table-of-contents scope. |

## Important limitation

The HWP files should not be used as the main machine-extraction source in this PR. They appear to be distribution-mode HWP files, and full body extraction is not reliable enough for production data correction.

## Recommended use

- Use HWP files as origin/source-file corroboration.
- Use validated PDF conversions as the practical extraction baseline.
- Use official HiKorea manual notice and later attachment archive PR to preserve source provenance.

## Verdict

HWP sources support source provenance, but the production crosswalk should use the validated PDF baseline unless a later extraction pipeline can reliably parse the HWP body.
