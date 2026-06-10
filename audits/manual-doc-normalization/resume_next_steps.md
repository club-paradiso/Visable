# Resume / Next Steps

**State:** Audit COMPLETE. All 42 codes audited (B01–B07). 5 Type E fixes applied
and validated. Working tree holds a 2-file, 10-line change. NOT committed.

## The only remaining action
Commit + draft PR — **blocked pending explicit authorization** (per instruction:
"Do not commit or create PR unless explicitly instructed").

When authorized, run:
```bash
git add visa_data.json backend/data/visas.json audits/manual-doc-normalization/
git commit  # use the message from the task's Phase 4 (fix(data): normalize document labels…)
git push -u origin claude/vigilant-ritchie-49oja3
# then open a DRAFT PR
```

## Regenerate / re-verify anytime (read-only)
```bash
python3 audits/manual-doc-normalization/scan_mechanical.py   # A/B/E/N findings
python3 audits/manual-doc-normalization/scan_naming.py        # C/D candidates
python3 audits/manual-doc-normalization/gen_reports.py        # batch reports
python3 scripts/sync_visa_data.py --check                     # backend in sync?
bash scripts/check_repo.sh                                    # full validation
```

## If reopening the audit
- Confirmed-fix ledger + skip reasons: `final_summary.md`
- Per-batch detail: `batch_B0*.md`
- Manuals: `docs/data/claude_opus_manual_extraction_2026_05/{visa,stay}_hwp_full.txt`
  (NOTE: prompt's `stay_manual_260601__1_.txt` does not exist; stay_hwp_full.txt
  is the authoritative 외국인체류 안내매뉴얼 2026.5, header-verified.)
