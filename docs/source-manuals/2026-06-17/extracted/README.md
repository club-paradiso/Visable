# 2026-06-17 manual text extraction import target

This directory is the import target for extracted text from the 2026-06-17 official manuals used by Paradiso data refresh workflows.

Only this README is tracked initially. In a fresh checkout, the generated extraction files are not present.

After running `scripts/import_260617_extract.py`, this directory should contain:
- `manifest.json`
- `full_text/stay_manual_260617.txt`
- `full_text/visa_issue_manual_260617.txt`
- `chunks_25_pages/...`

These files may be generated or imported locally before running Claude Code or Codex manual refresh workflows. Chunk files under `chunks_25_pages/` split each manual by PDF page ranges so those workflows can use targeted `rg` searches instead of loading the full manuals at once.
