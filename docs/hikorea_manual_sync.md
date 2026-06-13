# HiKorea manual sync

Keeps the repo's copies of the HiKorea **사증민원 자격별 안내 매뉴얼** and
**체류민원 자격별 안내 매뉴얼** followable when HiKorea posts an update (the
updates are irregular and hard to track manually).

> **Design principle (CLAUDE.md + the safe-automation architecture):** legal
> content is never modified automatically. This pipeline only *detects*,
> *stages*, and *proposes* — it opens a **draft PR** that a human reviews and
> merges. It never edits `visa_data.json`, `doc_master.json`, the verified
> `*_hwp_full.txt`, or any production data.

## Why a human stays in the loop

The manuals ship as **배포용(distribution) HWP** (FileHeader flag `0x4`): the
`BodyText` is a stub and `ViewText` is encrypted, so no open-source tool extracts
them fully. The committed `docs/data/claude_opus_manual_extraction_2026_05/
*_hwp_full.txt` were produced by verified human/AI-assisted extraction. The
automation surfaces the new file + a *best-effort* extraction with a completeness
report; the reviewer performs the real extraction before anything is promoted.

## Components

| File | Purpose |
| --- | --- |
| `data/sources/hikorea_manual_sync.json` | Config: per-manual download_url (nullable), committed HWP/txt paths, baseline sha256. |
| `scripts/convert_manual_hwp.py` | Best-effort HWP→text via olefile / LibreOffice→pdftotext / hwp5txt; writes each result + an extraction report (flags distribution format + low completeness). |
| `scripts/sync_hikorea_manuals.py` | Obtain candidate HWP (manual input or best-effort download), sha256-compare to baseline, stage + convert changed ones, emit `build/manual-sync/{summary.json,pr_body.md}`. No production writes. |
| `.github/workflows/hikorea-manual-sync.yml` | Twice-monthly + `workflow_dispatch`; installs tooling; on change opens a draft PR. |

## How it runs

- **Auto attempt:** the scheduled job runs the sync. Best-effort download only
  happens when `download_url` is configured *and* `--allow-network` is passed
  (dispatch input). Official hosts often block CI (HTTP 403); that is handled
  gracefully and reported, not fatal.
- **Manual fallback (recommended while `download_url` is null):** a maintainer
  downloads the updated HWP from HiKorea, adds it to the checkout, and runs the
  workflow via *Run workflow* with `manual_hwp_visa` / `manual_hwp_stay` set to
  its path. The rest (hash compare, staging, extraction, draft PR) is automatic.

## Reviewer checklist (in the draft PR)

1. Confirm the staged HWP under `docs/source-manuals/incoming/` is the genuine
   official file.
2. Perform a verified (human/AI-assisted) full extraction — do **not** trust the
   best-effort text.
3. Move the HWP to its canonical `docs/source-manuals/<period>/` path and update
   the verified `*_hwp_full.txt`.
4. Update `baseline_sha256` in `data/sources/hikorea_manual_sync.json`.
5. Run the data audits and decide, with review, whether any grounding-data
   changes follow (separate from this PR if needed).

## Enabling auto-download later

When a maintainer verifies the official direct download URL, set it as
`download_url` in the config (human-reviewed PR) and enable `allow_network` on
the schedule. Until then the manual fallback covers the same flow safely.
