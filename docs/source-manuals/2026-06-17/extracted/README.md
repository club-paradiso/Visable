# 2026-06-17 manual text extraction

This directory contains extracted text for the 2026-06-17 official manuals used by Paradiso data refresh workflows.

Primary files:
- `full_text/stay_manual_260617.txt`
- `full_text/visa_issue_manual_260617.txt`
- `manifest.json`

Chunk files under `chunks_25_pages/` split each manual by PDF page ranges so Claude Code or Codex can use targeted `rg` searches instead of loading the full manuals at once.
