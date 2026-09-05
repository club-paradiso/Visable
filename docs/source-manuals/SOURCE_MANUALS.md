# Source Manuals

The Ministry of Justice immigration manuals in this directory are Paradiso's official source artifacts for extraction and grounding work. `source_manifest.json` is the canonical current/archived pointer.

Current manuals (see `source_manifest.json` for the authoritative pointer):

- `2026-09-01/visa_manual_260901.hwp` - 사증발급 안내매뉴얼, 2026.9 / source date 2026-09-01. (배포용 HWP; body read from ViewText by `scripts/decrypt_hwp_distribution.py`; full text at `2026-09-01/extracted/full_text/visa_manual_260901.txt`)
- `2026-09-01/stay_manual_260901.hwp` - 외국인체류 안내매뉴얼, 2026.9 / source date 2026-09-01. (배포용 HWP; body read from ViewText; full text at `2026-09-01/extracted/full_text/stay_manual_260901.txt`)

> **Content review pending.** Both 2026-09-01 editions are registered
> `needs_review` in `data/manual_approval_index.json`. The *extraction* is
> mechanically verified — the same script reproduces both approved 2026-07-31
> extractions byte-for-byte (SHA-256 match) — but no human has compared this
> edition's content against the original, so neither may back a direct AI
> assertion yet. Because the 2026-07-31 editions are now `superseded`, the
> direct-evidence gate for the visa/stay families is closed until a reviewer
> promotes 2026-09-01. That is the intended fail-closed behaviour.
> Start from the change review artifacts:
> `audits/manual-refresh-260901/visa_260731_to_260901.md` and
> `audits/manual-refresh-260901/stay_260731_to_260901.md`.

Last content-approved editions (superseded as source, kept for lineage):

- `2026-07-31/visa_manual_260731.hwp` - 사증발급 안내매뉴얼, 2026.7. (approved 2026-08-09; superseded by the 2026-09-01 edition)
- `2026-07-31/stay_manual_260731.hwp` - 외국인체류 안내매뉴얼, 2026.7. (approved 2026-08-09; superseded by the 2026-09-01 edition)

Earlier PDF extraction sources (superseded):

- `backend/data/sources/manuals/260617_visa_manual_exported.pdf` - 사증발급 안내매뉴얼, 2026.6 / source date 2026-06-17. (PDF; readable extraction + section index alongside it)
- `backend/data/sources/manuals/260623_stay_manual_exported.pdf` - 외국인체류 안내매뉴얼, 2026.6 / source date 2026-06-23. (PDF; readable extraction + section index alongside it)

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
