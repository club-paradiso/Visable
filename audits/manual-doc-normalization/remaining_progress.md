# Remaining Run — Progress

**Branch:** `data/manual-doc-normalization-remaining` (from main @ 605110a)
**Status: ALL BATCHES COMPLETE — validation green — awaiting explicit commit instruction.**

## Batches
- [x] R01: B-1, B-2, C-3, C-4, D-1, D-2 (D-2 deep-check: 10 skip entries documented)
- [x] R02: D-3, D-4, D-4-1, D-7, D-8, D-9
- [x] R03: D-10, E-1, E-2, E-3, E-4, E-5 (**1 fix: D-10 결핵진단서**)
- [x] R04: E-6, E-7, E-8, E-9, E-10, F-1 (**1 fix: E-8 결핵진단서**)
- [x] R05: F-2, F-3, F-4, F-5, F-6, G-1
- [x] R06: H-1, H-2, A-1, A-2, A-3, C-1
- [x] R07: D-5, D-6, D-4-2K, K-STAR, REGION-S, YOUTH-STAY
- [x] sync backend/data/visas.json (scripts/sync_visa_data.py — in sync)
- [x] check_repo.sh PASS (baseline was also PASS)
- [ ] commit + draft PR (Phase 9: NOT automatic — commands printed in final summary)

## Confirmed fixes this run: 2 (both Type D, CONFIRMED_EXACT)
| # | Code | Field | Old → New | Authority |
|---|---|---|---|---|
| 1 | D-10 | documents_extension[9].name | 결핵건강진단서 → 결핵진단서 | stay manual (extension tab) |
| 2 | E-8 | documents_initial[3].name | 결핵건강진단서 → 결핵진단서 | identical term in both manuals |

## Scans executed (read-only, reproducible)
1. `scan_mechanical.py` re-run post-merge: 0 A / 0 B / 0 E / 1 N (D-10 — previously closed, not re-opened).
2. doc_master.json consistency: 0 dup ids; 3 dup-ko_name alias pairs (rich + `_generic`
   placeholder) and 12 placeholder en_names recorded → structural follow-up, outside A–E scope.
3. ID-array rendered-label duplicate scan (two ids → same ko_name in one array): 0.
4. Procedure arrays mixing doc_ id + literal with identical render: 0.
5. documents_extension (233 entries) + documents_registration (6) vs stay manual per-code
   sections: 32 exact, 3 norm-match, 204 not-verbatim → all classified standardized
   app template / umbrella / whitespace-style / fee-protected, EXCEPT the 2 결핵진단서 fixes.
6. documents_initial (156 entries): no `_source_notes` provenance (except D-2) →
   `AMBIGUOUS_MANUAL_MISMATCH` for C/D; Type A = 0. (E-8 fix exempt: term identical in
   both manuals → authority-independent.)
7. D-2 attributed documents_* deep check: 0 fixes, 10 documented skips.

## Files changed (working tree)
- `visa_data.json` (2 lines), `backend/data/visas.json` (2 lines, synced)
- `audits/manual-doc-normalization/mechanical_findings.json` (regenerated post-merge)
- new audit reports: `remaining_*.md`, `gen_remaining_reports.py`
