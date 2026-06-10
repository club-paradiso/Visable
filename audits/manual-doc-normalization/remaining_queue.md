# Remaining Run — Queue

**Branch:** `data/manual-doc-normalization-remaining` (from main @ 605110a, post-#327)
**Baseline:** clean tree, JSON valid, check_repo.sh PASS.

## Manuals (confirmed readable)
- 사증발급 안내매뉴얼 2026.5 → `docs/data/claude_opus_manual_extraction_2026_05/visa_hwp_full.txt` (16,849 lines)
- 외국인체류 안내매뉴얼 2026.5 → `docs/data/claude_opus_manual_extraction_2026_05/stay_hwp_full.txt` (28,594 lines)
  (prompt referenced `docs/data/stay_hwp_full.txt` — does not exist; same file lives under
  the claude_opus_manual_extraction_2026_05/ dir, header-verified)

## Totals
- Top-level codes in visa_data.json: **42** (no duplicates)

## Prior completion (merged PR #327)
Previous run audited **42/42 codes** at these scopes (see `progress.md`, `final_summary.md`,
`batch_B0*.md` on main):
- procedure-tab doc arrays (top-level + variants): Type A/B/E/N mechanical + Type C/D naming scan → 5 Type E fixes (F-4 ×3, H-2 ×2, merged), 34 ambiguous skips (documented; NOT re-opened this run)
- ID arrays (newReqDocs etc.) + subCodes.addReqDocs: Type A
- documents_* arrays: Type A + near-dup only

## NOT covered by prior run → scope of THIS run (all 42 codes)
1. Re-verify mechanical state post-merge (A/B/E/N) — regression check.
2. `documents_*` arrays (39× documents_initial = 156 entries, 33× documents_extension = 233,
   1× documents_registration = 6): naming/semantic audit.
   ⚠️ PROVENANCE CONSTRAINT: only D-2's 3 arrays carry `_source_notes` manual attribution
   (stay manual). The other 70 arrays have NO provenance → cannot choose the authoritative
   manual → Type C/D categorically `AMBIGUOUS_MANUAL_MISMATCH` (skip); Type A still applies.
3. `doc_master.json` (101 entries): duplicate `id`s, duplicate `ko_name`s (mechanical).
4. Per-code audit entry in batch reports (full coverage, no code skipped).

## Uncertainty about prior completion
None material: prior reports enumerate all 42 codes. The extension above is new scope,
not a redo. Already-merged Type E fixes will NOT be re-applied; the 34 prior ambiguous
candidates stay closed unless new exact evidence appears.

## Batch order (7 × 6 codes, same grouping as prior run for traceability)
- R01: B-1, B-2, C-3, C-4, D-1, D-2
- R02: D-3, D-4, D-4-1, D-7, D-8, D-9
- R03: D-10, E-1, E-2, E-3, E-4, E-5
- R04: E-6, E-7, E-8, E-9, E-10, F-1
- R05: F-2, F-3, F-4, F-5, F-6, G-1
- R06: H-1, H-2, A-1, A-2, A-3, C-1
- R07: D-5, D-6, D-4-2K, K-STAR, REGION-S, YOUTH-STAY
