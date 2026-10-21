# Source Manuals

The Ministry of Justice immigration manuals in this directory are Paradiso's official source artifacts for extraction and grounding work. `source_manifest.json` is the canonical current/archived pointer.

Current manuals (see `source_manifest.json` `current` for the authoritative pointer). Both 2026.9 editions were made current by the owner's edition decision of 2026-10-16 (`audits/manual-edition-2026-09-promotion/README.md`); that decision is an edition choice, not a line-by-line certification of every extract derived from them.

- `2026-09/visa_manual_260901.pdf` - 사증발급 안내매뉴얼, 2026.9 / source date 2026-09-01, 519 pages. Page-anchored primary: `data/manual-corpus/visa_manual_2026_09_01_pdf.json`, text at `2026-09/extracted/visa_manual_2026_09_01_pdf.txt`.
  - Same edition, other container: `2026-09-01/visa_manual_260901.hwp` (배포용 HWP; ViewText extraction at `2026-09-01/extracted/full_text/visa_manual_260901.txt`; paragraph-anchored, not indexed).
- `2026-09/stay_manual_260918.pdf` - 외국인체류 안내매뉴얼, 2026.9 / source date 2026-09-18, 810 pages. Page-anchored primary: `data/manual-corpus/stay_manual_2026_09_18_pdf.json`, text at `2026-09/extracted/stay_manual_2026_09_18_pdf.txt`.
  - Same edition, other container: `2026-09/stay_manual_260918.hwp` (배포용 HWP; ViewText extraction at `2026-09/extracted/full_text/stay_manual_260918.txt`; paragraph-anchored, not indexed).

The 2026-07-31 HWP pair (`2026-07-31/`) is recorded as each role's `archived_previous_current`. The 2026.6 PDFs (`backend/data/sources/manuals/260617_visa_manual_exported.pdf`, `260623_stay_manual_exported.pdf`) stay in the repository and in the manifest history; their 2026-06-17 section extracts stay in the search index as `superseded`, never as direct evidence. `2026-09-01/stay_manual_260901.hwp` is the earlier 2026-09-01 stay edition, superseded by 2026-09-18 (`data/manual_approval_index.json`).

### Markdown derived texts (2026-10-19)

The owner supplied HWP→Markdown conversions of both current editions. They keep headings and HTML tables, which the PDF text layer flattens, but they have no page numbers.

- `2026-09/derived/visa_manual_260901.md` - derived from `2026-09-01/visa_manual_260901.hwp`
- `2026-09/derived/stay_manual_260918.md` - derived from `2026-09/stay_manual_260918.hwp`

Each is registered under `current.<role>.derived_texts` in `source_manifest.json` (SHA-256 pinned, provenance "owner-supplied HWP→Markdown conversion, 2026-10-19") and tracked in `data/manual_approval_index.json` as `needs_review` at document level. They are not registry editions: `data/source_registry.json` keeps one entry per container of an edition, and these texts carry no edition of their own.

`scripts/build_manual_markdown_corpus.py` splits each Markdown into chunks (by heading, table and PDF page; table rows rendered as "열이름: 값" text) and maps every chunk to the approved PDF page(s) by matching normalized text against the PDF page text. The result, with a confidence per chunk, is `data/manual-corpus/<id>.json`.

- A chunk mapped with high or medium confidence inherits the approval of its PDF edition for that page. It is direct evidence and is cited by that PDF page.
- Low, none, tied and out-of-sequence chunks are kept and searchable as `needs_review`, with no page. They are never direct evidence.
- This is machine verification against the approved edition text. Nobody has read the Markdown line by line.
- The images in the owner's zips (`images/260901`, `images/260918`) are not committed. They are not used for grounding, and image-only content stays checkable only on the PDF page.

| derived text | chunks | table chunks | high | medium | low | none | page-mapped (direct) | PDF pages covered |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| visa 260901 | 1,793 | 536 | 1,224 | 107 | 358 | 104 | 1,331 | 504 / 519 |
| stay 260918 | 1,504 | 904 | 1,004 | 130 | 239 | 131 | 1,134 | 775 / 810 |

12-gram containment of the Markdown text: 99.1% (visa) and 99.2% (stay) in the HWP extraction, 95.8% and 96.4% in the PDF text.

`scripts/build_manual_search_index.py` indexes these chunks into `backend/data/manual_search_index.sqlite3` under their own source ids (`visa_manual_2026_09_01_md`, `stay_manual_2026_09_18_md`), next to the unchanged one-row-per-page PDF rows. Rebuild everything with `npm run build:current-manuals`. Verify with `npm run test:current-manuals` and `python3 scripts/check_source_manuals.py`.

Special program manuals (also registered in `source_manifest.json` under `special_program_manuals`):

- `backend/data/sources/manuals/260629_kcore_manual.hwp` - 「육성형 전문기술인력 제도」(K-CORE / E-7-M) 사증·체류관리 매뉴얼, 2026.6 (시행 2026-03-05, 배포 2026-06-29; standard HWP, body fully extracted)
- `backend/data/sources/manuals/260421_dongpo_manual.pdf` - 알기쉬운 외국국적동포 업무 매뉴얼, 2026.2 (standalone 붙임 배포본; 별첨 1–10 원문 대조용. 동일 계열 내용이 2026-06-23 체류 매뉴얼 pp. 529-579에 내장되어 있으며, 문구가 다를 경우 최신 체류 매뉴얼 내장본이 우선)

Superseded (archived) primary manuals:

- `2026-05/visa_manual_2026_05.pdf` - 사증발급 안내매뉴얼, 2026.5. (superseded by the 2026-06-17 visa manual)
- `2026-06/stay_manual_2026_06_01.pdf` - 외국인체류 안내매뉴얼, 2026.5 / source file 2026-06-01. (superseded by the 2026-06-23 stay manual)

Stored companion artifacts:

- `2026-05/visa_manual_2026_05_21.hwp` - 사증발급 안내매뉴얼, 2026.5. (HWP, filename-level 2026-05-21 source-truth artifact; body extraction blocked by distribution mode, see `source_manifest.json` and `docs/data/2026_05_21_MANUAL_EXTRACTION_REPORT.md`)
- `2026-05/stay_manual_2026_05_21.hwp` - 외국인체류 안내매뉴얼, 2026.5. (HWP, filename-level 2026-05-21 archived source artifact; body extraction blocked by distribution mode)
- `2026-06/stay_manual_2026_06_01.hwp` - 외국인체류 안내매뉴얼, 2026.5 / source file 2026-06-01. (HWP, official stored artifact only; distribution-mode body extraction is blocked, so it is not parsed or indexed)

Archived stay manual:

- `2026-05/stay_manual_2026_05.pdf` - 외국인체류 안내매뉴얼, 2026.5. Superseded by the 2026-06-01 stay manual for future extraction work. Keep it for audit history and comparison.

Older 2026.3 / 260414 manuals are superseded for future extraction work. Keep them available for audit history when they exist elsewhere in the project, but do not treat them as current for new extraction.

`visa_data.json` remains a structured fallback, audit, and display layer. It is useful for local rendering and compact grounding payloads, but it is not the ultimate source of truth.

User-facing decisions must still be verified with immigration offices, HiKorea, 1345, or a qualified professional. Paradiso provides reference information only and does not provide legal advice, filing services, or representation services.

This PR does not regenerate `visa_data.json` and does not perform full RAG ingestion, PDF chunking, or Supabase migration.

## 2026-06-01 stay manual refresh status

The user-provided June 1 stay manual files were installed on 2026-06-05:

- PDF source: `/Users/seonjaekim/Downloads/stay_manual_260601.pdf` -> `2026-06/stay_manual_2026_06_01.pdf`
- HWP source: `/Users/seonjaekim/Downloads/260601_체류민원_자격별_안내_매뉴얼(숙련기능인력 제도 개선사항 반영).hwp` -> `2026-06/stay_manual_2026_06_01.hwp`

The PDF is the current stay/residence manual source and is the only June artifact treated as parsed/indexed. The HWP is preserved as an official artifact, but local HWP inspection showed distribution-mode extraction returns only the warning/placeholder text, so the HWP is stored-only.

Existing broad structured requirement fixtures remain May-derived until a deliberate regeneration/audit PR updates their per-entry source references. The narrow runtime grounding fixture was pointed at the June PDF only after its cited pages (43, 44, 90, 91, 226) were rechecked and matched the previous canonical PDF by extracted text hash.
