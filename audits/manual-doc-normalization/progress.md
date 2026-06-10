# Manual Document Normalization — Progress

**Task:** Audit & scoped fix of document labels, duplicates, and embedded-manual
page strings across all top-level records in `visa_data.json`.
**Mode:** Checkpointed full-coverage batch workflow (Opus carefulness).
**Commit/PR:** NOT until full queue complete + validation passes AND explicit go-ahead.

## Manuals (ground truth)
| Procedure tab | Manual | Path (stable, in-repo) | Lines |
|---|---|---|---|
| 사증발급 / visaIssuance | 사증발급 안내매뉴얼 2026.5 | `docs/data/claude_opus_manual_extraction_2026_05/visa_hwp_full.txt` | 16,849 |
| 체류 tabs (change/extend/grant/register/reentry/etc.) | 외국인체류 안내매뉴얼 2026.5 | `docs/data/claude_opus_manual_extraction_2026_05/stay_hwp_full.txt` | 28,594 |

> NOTE: Prompt named `/mnt/user-data/uploads/stay_manual_260601__1_.txt` and
> `docs/data/stay_manual_260601.txt`. **Neither exists.** The authoritative stay
> manual (외국인체류 안내매뉴얼 2026.5, header-verified) is already present at the
> stable repo path above (`stay_hwp_full.txt`). Used that; did NOT create a
> misleadingly-dated copy. Not a STOP condition — both manuals are accessible.

## Branch
`claude/vigilant-ritchie-49oja3`  (clean tree at start; no forbidden files modified)

## Full code queue (42, no duplicates)
B-1, B-2, C-3, C-4, D-1, D-2, D-3, D-4, D-4-1, D-7, D-8, D-9, D-10, E-1, E-2,
E-3, E-4, E-5, E-6, E-7, E-8, E-9, E-10, F-1, F-2, F-3, F-4, F-5, F-6, G-1,
H-1, H-2, A-1, A-2, A-3, C-1, D-5, D-6, D-4-2K, K-STAR, REGION-S, YOUTH-STAY

## Batches (6 codes each)
- B01: B-1, B-2, C-3, C-4, D-1, D-2
- B02: D-3, D-4, D-4-1, D-7, D-8, D-9
- B03: D-10, E-1, E-2, E-3, E-4, E-5
- B04: E-6, E-7, E-8, E-9, E-10, F-1
- B05: F-2, F-3, F-4, F-5, F-6, G-1        (← F-4 Type E ×3)
- B06: H-1, H-2, A-1, A-2, A-3, C-1        (← H-2 Type E ×2)
- B07: D-5, D-6, D-4-2K, K-STAR, REGION-S, YOUTH-STAY

## Global scans (read-only, reproducible)
- `scan_mechanical.py` → `mechanical_findings.json`
  - Type A (exact dup in array): **0**
  - Type B (commonDocs ∩ requiredDocs): **0**
  - Type E (embedded manual pp.): **5**  (F-4 ×3, H-2 ×2)
  - Type N (normalized near-dup): **1**  (D-10 extension — flattened artifact)
- `scan_naming.py` → `naming_candidates.json`
  - Type C/D label-like near-misses: **33** — all reviewed against manual,
    all resolve to already-faithful / flattened-artifact / protected-number →
    **0 confirmed fixes** (see batch reports for per-item reasons).

## Confirmed fixes (whole task)
| # | Code | Tab | Type | Field | Old → New |
|---|---|---|---|---|---|
| 1 | F-4 | extension     | E | procedures.extension.variants[0].manualRefs[0].pageRange     | `PDF pp. 530-531 (embedded manual pp. 10-11)` → `PDF pp. 530-531` |
| 2 | F-4 | registration  | E | procedures.registration.variants[0].manualRefs[0].pageRange  | `PDF p. 530 (embedded manual p. 10)` → `PDF p. 530` |
| 3 | F-4 | statusChange  | E | procedures.statusChange.variants[0].manualRefs[0].pageRange  | `PDF pp. 528-530 (embedded manual pp. 8-10)` → `PDF pp. 528-530` |
| 4 | H-2 | registration  | E | procedures.registration.variants[0].manualRefs[0].pageRange  | `PDF pp. 524-525 (embedded manual pp. 4-5)` → `PDF pp. 524-525` |
| 5 | H-2 | workplaceChange | E | procedures.workplaceChange.variants[0].manualRefs[0].pageRange | `PDF pp. 525-526 (embedded manual pp. 5-6)` → `PDF pp. 525-526` |

## Status — COMPLETE (awaiting commit authorization)
- [x] B01  - [x] B02  - [x] B03  - [x] B04  - [x] B05  - [x] B06  - [x] B07
- [x] 5 Type E fixes applied to visa_data.json (JSON valid)
- [x] sync backend/data/visas.json (via scripts/sync_visa_data.py)
- [x] check_repo.sh → PASS (baseline also PASS; no regression)
- [x] final_summary.md written
- [ ] (await explicit instruction) commit + PR

**Result:** 42/42 codes audited. Confirmed fixes = 5 (all Type E). Ambiguous/skipped = 34.
Files changed: visa_data.json (5 lines), backend/data/visas.json (5 lines, synced).

_Last updated: batches complete, validated, holding for commit go-ahead._
