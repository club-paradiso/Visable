# Official Web Overlay Parser Design

This POC adds the overlay container and seed manifest, but does not crawl or
promote any country/post page automatically.

## Allowed Inputs

Overlay candidates must be manifest entries from official domains only:

- `visa.go.kr`
- `hikorea.go.kr`
- `mofa.go.kr`
- `overseas.mofa.go.kr`
- `law.go.kr`

No blog, agency, consultant, SEO, Reddit, or unofficial summary page may be
stored as overlay evidence.

## Promotion Flow

1. Add a manifest seed for a country/post and expected visa code.
2. Manually verify the official page URL, title, and whether it is current.
3. Extract only local differences: submission method, appointment/e-form
   requirement, processing time, fees, local requirements, and notes.
4. Compare with the national manual record.
5. If the page conflicts with the manual, set `conflictsWithManual: true` and
   write `conflictNoteKo`.
6. If parsing is ambiguous, save the candidate to an audit report and do not
   add it to `data/official_web_overlays.json.records`.

## Non-overwrite Rule

Overlay records never replace `data/visa_issuance_records.json`. They only add
country/post-specific differences when the user selects or searches that
country/post.

## First Seed Scope

`data/official_web_overlays.json.seedManifest` currently seeds:

United States, China, Vietnam, Philippines, Indonesia, Mongolia, Uzbekistan,
Thailand, Japan, Singapore, and Hong Kong.
