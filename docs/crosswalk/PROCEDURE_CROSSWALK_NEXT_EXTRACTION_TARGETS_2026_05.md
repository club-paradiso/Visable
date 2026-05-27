# Procedure Crosswalk Next Extraction Targets - 2026.5

## Purpose

This document defines the next extraction pass after the initial procedure crosswalk.

The current PR records official routes and procedure-level mapping, but it intentionally does not fill exact manual pages or law articles. The next PR should add those citations.

## Extraction targets

| Priority | Procedure | Needed source detail | Patch gate impact |
| --- | --- | --- | --- |
| 1 | Foreigner registration | stay manual page, law article, rule article | required before registration checklist data patch |
| 2 | Extension of stay | status-specific stay manual pages, fee/rule basis if shown | required before extension checklist data patch |
| 3 | Change of status | status-specific change pages | required before change checklist data patch |
| 4 | Workplace change/addition | applicable status categories and manual pages | required before workplace-change guidance/data patch |
| 5 | Passport/registration-info change | reporting deadline, required documents, legal basis | required before passport-change guidance/data patch |
| 6 | Residence/address change | address-change manual attachment, page, legal basis | required before address-change guidance/data patch |
| 7 | Certificate issuance | fact-certificate manual section and HiKorea certificate route | required before certificate guidance/data patch |

## Minimum citation fields to fill

Each crosswalk record should be updated with:

- `source_refs[].page` for PDF/manual support,
- `source_refs[].article` for law/rule support,
- `source_refs[].section_label` for HiKorea route support,
- `source_refs[].support_level` set to `direct` when the source directly supports the field,
- `patch_readiness` updated only when all required support exists.

## Do not patch yet

Even after this extraction pass, data patching should still be separate. Keep future patch PRs small and scoped.
