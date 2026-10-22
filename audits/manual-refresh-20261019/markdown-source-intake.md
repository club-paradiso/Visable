# 2026-10-19 HiKorea Markdown source intake

Two user-supplied Markdown conversions of the same 2026-10-19 visa/stay HWP manuals were inspected on 2026-10-22.

| Manual | UTF-8 bytes | SHA-256 | Lines | Table lines |
| --- | ---: | --- | ---: | ---: |
| Visa | 1,113,926 | c98677f307dcb362012bfa4935e746390cd80e7e59603201529ea5f352698959 | 12,010 | 2,458 |
| Stay | 1,679,699 | dd15cc8221c26e55f4d67aa5d4766782d1d79ba3b84efb9a0fb988981c76b563 | 20,291 | 3,270 |

The input ZIP is an uploaded chat attachment and is NOT itself present in this GitHub branch. The importer script is committed, but the two complete Markdown source files cannot be said to be checked in until they appear in the paths specified by that script.

To integrate the exact ZIP in a checkout, run:

    python3 scripts/ingest_hikorea_markdown_261019.py PATH_TO_ZIP

The importer verifies both hashes before writing, then stages the Markdown files and their metadata under the existing pending-review editions. It does not make October current, update applicant checklists, or let Waymaker cite this edition directly.

Verify the staged files using:

    python3 scripts/ingest_hikorea_markdown_261019.py PATH_TO_ZIP --check

The original ZIP was inspected and contains 38 parent visa/status codes in each source, but this is not evidence that the administrative requirements are correct or unchanged. The Markdown table rows may not preserve merged-cell relationships, PDF page numbers or images. Human source review and a real edition-to-edition diff are required before any legal rule changes.
