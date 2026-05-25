# 2026-05-21 Safe Metadata / Doc-Ref Patch Report (PR C)

Branch: `data/patch-2026-05-21-safe-metadata`
Audit date: 2026-05-25
PR: **C** (after PR #157)

> **This document is an internal audit artifact. It is not legal advice and is not an official immigration decision.**

This is **PR C**, the safe-hygiene follow-up to **PR #157** (merged), which regenerated the manual TOC map, manual→JSON crosswalk, and full-record audit artifacts against the canonical **484-page visa** and **777-page stay** PDFs installed by PR #155.

**Scope statement:** This PR applies safe, mechanical, source-grounded metadata / doc-reference hygiene **only**. **No `requiredDocuments`, eligibility, fees, income, stay periods, procedures, aliases, or legal/admin guidance content was rewritten. No `verified=true` promotions. No `needsManualReview` removals. No production JSON (`visa_data.json`, `backend/data/visas.json`, `doc_master.json`) or `source_manifest.json` was edited.**

---

## Changes applied

| File | Field | Change | Evidence | Why safe |
|---|---|---|---|---|
| `docs/manual_grounding_expansion_plan.md` | Source block, "Total pages (PDF)" (line 29) | `774` → `777` | `source_manifest.json` `current.stay_residence_manual.pages = 777`; `docs/data/2026_05_21_manual_toc_map.json` `stay_manual.total_pages = 777` (PR #155/#157) | Living tracker describing the current committed source PDF by its current path. Factual page-count metadata only; no legal/manual content; the line carries no superseded hash, so the fix does not falsify a point-in-time snapshot. |
| `docs/data/2026_05_21_SAFE_METADATA_PATCH_REPORT.md` | — | new report | — | report artifact |
| `docs/data/2026_05_21_safe_metadata_patch_report.json` | — | new machine-readable report | — | report artifact |

**Changed records:** none. **Changed doc IDs:** none.

Because `visa_data.json` was not edited, `scripts/sync_visa_data.py` was not required (and `backend/data/visas.json` is unchanged and still in sync).

---

## Re-assessment of PR #157's doc_master findings (audited carefully)

PR #157 reported **12 corrupted `doc_master.json` IDs** (Korean text in the `id` field) plus **1 unused ID** (`doc_arc_fee`). On careful audit, **none is a safe mechanical hygiene target** — all are load-bearing references. They are routed to PR D.

### The 12 "corrupted" IDs are all actively referenced

Every one of the 12 Korean-string IDs is referenced **verbatim** as a document reference inside `visa_data.json`:

`개별 사안별 증빙서류(…)`, `변경 사유 입증서류(…)`, `사증발급신청서(별지 제17호 서식)`, `사진 1매(해당 시)`, `수수료`, `여권`, `여권 및 외국인등록증`, `체류자격별 개별 첨부서류(…)`, `체류지 입증서류`, `통합신청서`, `통합신청서(체류자격변경허가 신청 포함)`, `표준규격사진 1매`.

Renaming them to stable machine IDs would require **coordinated updates to every referencing record's document list**, which changes user-facing document requirements. → **PR D**, not PR C.

### `doc_arc_fee` is NOT unused

PR #157 flagged `doc_arc_fee` as unused based on `visa_data.json` references only. It is in fact referenced by the **live frontend** `index.html` in the `COMMON_NEW` document array (`index.html` ~line 10102, defined ~line 10108: `외국인등록증 발급 및 재발급 수수료 35,000원`). Removing it would break common-document rendering. → **Do not remove.** PR #157's "unused" assessment is corrected here.

---

## Deliberately not changed (and why)

| Item | Reason | Route |
|---|---|---|
| `visa_data.json` `manualRef.pageRange` / `manualRequiredDocAudit.sectionPageRange` | Document-list **sub-ranges**, not full section ranges. Several are stale vs the PR #157 re-derived anchors (e.g. F-3 `pp. 425-428`, H-1 `pp. 518-525` now point outside their re-derived sections F-3 421-425 / H-1 514-517), but a precise sub-range correction needs **page-cited evidence**. | PR D |
| `visa_data.json` `manualRequiredDocAudit.updatedAt = "2026-05-07"` | Historical audit timestamp (when the audit field was last set), not a source-date. Rewriting falsifies the audit history. | no action |
| `doc_master.json` (12 corrupted + `doc_arc_fee`) | All load-bearing references (see above). | PR D / no action |
| `docs/data/2026_05_HIGH_RISK_GAP_PATCH_AUDIT.md`, `JSON_MANUAL_LAW_AUDIT_2026_05.md`, `MANUAL_REQUIRED_DOC_AUDIT_2026_05.md`, `MANUAL_SOURCE_AUDIT_QUEUE.md` | Dated, point-in-time historical audit snapshots referencing superseded hashes (`fcc0b89…`, `0492683…`) and old filenames (`체류민원_0504.pdf`). Accurate as of their date; superseded by PR #157. Rewriting only their `774` would falsify history and create hash/page inconsistencies. | no action (superseded) |
| `backend/data/manual_grounding/candidates/f6_divorce_status_change/REVIEW.md` (`774 PDF pages`) | Past-tense record of an extraction done against the then-774-page PDF; F-6 is explicitly excluded from PR C. | PR D |

---

## PR D queue (page-cited substantive content work)

1. **F-6** — stale `2026.3` income note + F-6-1 income eligibility (stay §33 pp.474–497, visa §34 pp.324–335), page-cited.
2. **D-4-2K duplicate** (array indices 24 + 55) — assign a distinct code or sub-code (visa §12 pp.73–87 / stay §12 pp.83–101).
3. **F-4 + H-2** — Feb-2026 외국국적동포 sub-manual extraction; H-2 신규발급 중단 (stay §36 pp.518–584).
4. **K-STAR** — full sub-manual extraction incl. 우수인재 붙임 7–12 (visa §40 pp.456–484 / stay §41 pp.749–777).
5. **REGION-S** — 지역특화형 (stay §37 pp.585–654) + 광역형 (stay §40 pp.686–748).
6. **doc_master corrupted-id remap** — assign stable machine IDs to the 12 Korean-string IDs and update every referencing `visa_data.json` document list in lockstep.
7. **visa_data.json page-anchor sub-ranges** — re-derive doc-list sub-ranges for shifted stay sections (F-3, F-5, G-1, H-1, …) with exact page citations.

---

## No legal content patched

This PR rewrote **no** eligibility, requiredDocuments, fees, income, stay-period, procedure, alias, or legal/admin guidance content; promoted **no** record to `verified=true`; and removed **no** `needsManualReview` flag. PR D remains required for all page-cited substantive content patches.

## Legal Disclaimer

Paradiso is reference software. Nothing in this report or the repository's data files constitutes legal advice, an official immigration decision, or a guarantee of admissibility, eligibility, or processing outcome. Users must verify any specific case with 출입국·외국인청, HiKorea, 1345, or a qualified Korean immigration professional.
