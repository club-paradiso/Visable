# 2026-10-19 edition comparison: reviewer intake

## Versions in scope

| Family | Approved edition still used by Visable | New received edition | Review state |
|---|---|---|---|
| Visa (사증민원) | 2026-09-01, source `visa_manual_2026_09_01_pdf` | 2026-10-19 filename-date HWP text, `visa_manual_2026_10_19_hwp_text` | needs_review |
| Stay (체류민원) | 2026-09-18, source `stay_manual_2026_09_18_pdf` | 2026-10-19 filename-date HWP text, `stay_manual_2026_10_19_hwp_text` | needs_review |

## What changed, and what has not been established

The two 2026-10-19 uploads were stored as extracted text, with SHA-256 checksums and source registry entries. The approved September source was not replaced. **No verified edition-to-edition rule diff has yet been produced.** The new HWP extraction was performed through a different pipeline from the approved PDF page extracts; a raw line-by-line diff would therefore conflate paragraph/table reordering with genuine changes. It would be misleading to label every differing line a change of requirements.

Until originals are checked, the following comparison remains an **unresolved review checklist**, not a claim that any rule changed:

| Review topic | Compare for each relevant status/subcode and procedure |
|---|---|
| Eligibility and exceptions | Status and substatus, applicant class, permitted activities, conditional exemptions |
| Extension and status change | Documents, filing timing, proof of means, employment and study conditions |
| Initial registration / ARC | Registration/photo/form obligations, issue fees and return documents |
| Employers and representatives | Workplace change/addition, agency filing rights, employer required papers |
| Visa issuance | Certificate of issuance procedures, invitation and guarantor evidence |
| Special programs | New region-specific rules and implementation dates; do not extrapolate to Jeju |

## Required source verification before rule promotion

1. Place the original HWP binaries in controlled source storage and verify their SHA-256 hashes against the source registry record.
2. Re-extract new HWP through the repository's `scripts/decrypt_hwp_distribution.py` (and old HWP counterparts where available). Compare same-family, same-method output. Verify table headers/merged cells visually in the original.
3. Use `scripts/diff_manual_versions.py` with compatible page/section extraction; review every affected subcode and procedure with citations, plus currently effective legislation.
4. Publish the resulting verified diff here or link a new documented report, record a named reviewer/date, then update the authoring source and rebuild generated data. Do not mark content approved solely because its file hash matches.

**Promotion blocked** until these steps are complete. Existing approved September editions and their runtime citations remain authoritative for the current Visable build.
