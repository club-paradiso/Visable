# 2026-06-01 Stay Manual Data Refresh Report

## Scope

This pass compares the current repository stay manual
`docs/source-manuals/2026-06/stay_manual_2026_06_01.pdf` against the production
data surfaces that consume manual-derived content:

- `visa_data.json`
- `backend/data/visas.json`
- `doc_master.json`
- `backend/data/manual_grounding/structured_requirements_2026_06_01.json`
- `backend/data/manual_grounding/structured_requirements_index_2026_06_01.json`
- `index.html`
- `prototype/index.html`
- manual extraction / candidate-generation helper scripts

The user-provided `/Users/seonjaekim/Downloads/stay_manual_260601.pdf` is
byte-identical to the committed repository PDF:

`e25e97c3c2a05b5676ca3648a04226dcdc2433ab7c89a2f5105e6f8be49778b0`

## 1:1 Comparison Result

The existing June refresh audit already compares all stay-manual structured
evidence pages against the prior current stay PDF:

- stay entries inspected: 225
- entries relabelled to the 2026-06-01 PDF because cited page text matched: 218
- entries requiring re-extraction because cited page text changed: 7
- changed pages: 299, 619, 620, 621, 623, 624, 627

The changed pages affect only:

- `E-7` / E-7-4 숙련기능인력(K-point E74)
- `REGIONAL` / 지역특화형 비자 family and regional-diaspora sections

No broad rewrite was applied to records whose cited pages matched the prior
source. Those records already point to the current June structured layer and
remain candidate or source-confirmed according to their existing confidence
gates.

## Applied Changes

### E-7 / E-7-4

Updated `visa_data.json` and `backend/data/visas.json` so the E-7-4 sub-code
reflects the 2026-06-01 K-point E74 criteria:

- selection quota: 33,000
- recent 10-year E-9/E-10/H-2 residence history: 4 years or more
- current registered foreigner, normally working at the current workplace
- current workplace E-7-4 employment contract for at least 2 future years
- salary threshold: KRW 26 million, relaxed to KRW 25 million for agriculture,
  livestock, fisheries, and coastal merchant vessels
- current employer recommendation after at least 1 year of work
- 300-point scale, at least 200 points total, with average income and Korean
  ability minimum scores preserved
- temporary Korean-language supplementation path through the first extension
  when the non-Korean score condition is met
- required-document ids expanded to include the E-7-4 score sheet, bio statement,
  employment contract, income proof, Korean proof, guarantee, business/tax/social
  insurance proofs, and employer recommendation

### REGION-S

Replaced the previous over-specific `extReq` text, which had been clipped from a
single regional D-2 internship paragraph, with a conservative track-specific
summary. Added representative sub-track entries for:

- `F-2-R`
- `E-7-4R`
- `F-3-3R`
- `F-4-R`
- `REGIONAL-D-2`
- `REGIONAL-E-7`

The REGION-S parent record intentionally does not flatten these into one common
document list. Regional-special and metropolitan pilot visa requirements vary by
track, local recommendation, family status, residence, employment, enrollment,
and local government notice.

### Document Master

Updated reusable document definitions:

- `doc_emp_recom` now covers employer/company recommendations as well as
  ministry/local-government recommendations where applicable.
- `doc_employment_insurance_list` now covers the 4 major social-insurance
  workplace subscriber list used by E-7-4.
- Added `doc_personal_statement` for the E-7-4 신상기술서.

### Runtime / UI Wiring

- `structuredRequirementsRef.source` in production records now points to
  `backend/data/manual_grounding/structured_requirements_2026_06_01.json`.
- Manual refs now carry the 2026-06-01 stay source date/file where available.
- `index.html` displays source dates when a manual ref provides them.
- `prototype/index.html` no longer labels the current stay source as merely the
  2026-05 edition.
- `scripts/extract_manual_page_text.py` and
  `scripts/generate_candidate_from_matrix.py` now default to the current
  2026-06-01 stay manual.

## Guardrails

- No `verified=true` promotion was made.
- No `needsManualReview=false` demotion was made.
- No sub-code/scenario-specific list was promoted to a universal parent-level
  document list.
- Visa issuance manual references remain on the existing 2026-05 source.
- HWP body text remains stored-only and is not treated as parsed source evidence.
