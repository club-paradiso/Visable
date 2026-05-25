# Full Manual → JSON Audit Report — PR B (rebuild against canonical 2026-05-21 PDFs)

Branch: `data/rebuild-2026-05-21-manual-crosswalk`
Audit date: 2026-05-25
Auditor: Claude Code (automated; human-reviewed PR required before merge)
Generator: `scripts/regenerate_2026_05_21_manual_crosswalk.py`

> **This document is an internal audit report. It is not legal advice and is not an official immigration decision.**

---

## Executive Summary

This is **PR B** of the 2026-05-21 manual-update workflow, following **PR #155** (merged), which installed the canonical 2026-05-21 PDF source files as `visa_manual_2026_05.pdf` (484p) and `stay_manual_2026_05.pdf` (777p) and updated `source_manifest.json` (source_date `2026-05-21`, stay page count 774 → 777, refreshed hashes/sizes, honest PDF internal export date 2026-05-24).

PR B regenerates the manual TOC map, the manual→JSON crosswalk, and the full-record audit artifacts **against the newly installed canonical PDFs**. It is audit/report-only: the sole code addition is the deterministic generator `scripts/regenerate_2026_05_21_manual_crosswalk.py`. **No `visa_data.json`, `backend/data/visas.json`, or `doc_master.json` edits. No legal/manual content patched.**

**Key result:** All page anchors are re-derived from the committed canonical 2026-05-21 source manuals. The stay manual's special-section anchors (§36–§41) shifted versus the pre-#155 774-page map and have been corrected; the stay manual now ends at page 777; and the pre-#155 source-identity caveat ("user PDFs not accessible / source_date unresolved / PDF created 2026-05-07") no longer applies.

**This report and its sibling artifacts supersede the pre-PR #155 audit artifacts that were based on the earlier 774-page stay PDF.**

---

## Source state confirmed (Task step 2)

| Field | Visa manual | Stay manual |
|---|---|---|
| File | `docs/source-manuals/2026-05/visa_manual_2026_05.pdf` | `docs/source-manuals/2026-05/stay_manual_2026_05.pdf` |
| Pages (`pdfinfo`) | **484** ✅ | **777** ✅ (was 774) |
| SHA-256 | `7fd79509…ae11c` ✅ | `dd0d2f10…9c3e1` ✅ |
| File size | 13,194,599 bytes | 14,884,075 bytes |
| `source_manifest.json` source_date | `2026-05-21` ✅ | `2026-05-21` ✅ |
| PDF internal export date | 2026-05-24 (Quartz PDFContext) | 2026-05-24 |

All facts cross-checked against `source_manifest.json` by the generator's `verify_source_state()`, which hard-fails on any mismatch.

---

## Tooling (Task step 3)

| Tool | Version | Use |
|---|---|---|
| `pdftotext -layout` | poppler-utils 24.02.0 | Full-text extraction (preferred) |
| `pdfinfo` | poppler-utils 24.02.0 | Page-count verification |
| `pypdf` | 6.12.1 | Page-count fallback |
| `python3 -m json.tool` | 3.x | JSON validation |

Extraction commands:

```
pdftotext -layout docs/source-manuals/2026-05/visa_manual_2026_05.pdf visa_layout.txt
pdftotext -layout docs/source-manuals/2026-05/stay_manual_2026_05.pdf stay_layout.txt
pdfinfo  docs/source-manuals/2026-05/visa_manual_2026_05.pdf   # Pages: 484
pdfinfo  docs/source-manuals/2026-05/stay_manual_2026_05.pdf   # Pages: 777
```

Extracted text was held under `/tmp/extract/` (not committed). Section anchors were detected by form-feed page splitting (verified offset-free: split page N = physical page N) plus a spaced-Korean-name + `(CODE)` top-of-page header regex; back-matter special sections were located by canonical-title substring search. The detector output is pinned in the generator so the artifacts regenerate deterministically.

---

## Regenerated artifacts (Task step 4)

| File | Type | Content |
|---|---|---|
| `docs/data/2026_05_21_MANUAL_TOC_MAP.md` | report | Visa 40-section + stay 41-section TOC→page map; back-matter pp.769–777 |
| `docs/data/2026_05_21_manual_toc_map.json` | data | Machine-readable TOC map (schema 2.0) |
| `docs/data/2026_05_21_MANUAL_JSON_CROSSWALK.md` | report | 58-record crosswalk with 6-way classification |
| `docs/data/2026_05_21_manual_json_crosswalk.json` | data | Machine-readable crosswalk (schema 2.0) |
| `docs/data/2026_05_21_VISA_DATA_FULL_AUDIT.md` | report | Record-by-record audit |
| `docs/data/2026_05_21_visa_data_full_audit.json` | data | Machine-readable audit (schema 2.0) |
| `docs/data/2026_05_21_FULL_MANUAL_JSON_AUDIT_REPORT.md` | report | This report |

---

## TOC map (Task steps 6–7)

| Manual | TOC sections | High-confidence anchors | No-header / approximate | Pointer-only |
|---|---:|---:|---:|---:|
| Visa (484p) | 40 | 35 | 2 (E-5, E-6) | 3 (F-4, H-2 → §38; F-5 partial) |
| Stay (777p) | 41 | 39 | 1 (E-2) | 0 |

**Re-derivation deltas vs the pre-#155 774-page map:**

- Visa: page count unchanged (484), cover/TOC byte-identical → anchors reproduce exactly. No change.
- Stay: standard sections A-1…D-6 match; **D-7 108–114, D-8 115–129, D-9 130–141** (the pre-#155 "D-9 before D-8" body-order-swap anomaly does **not** reproduce); **F-2 360–420, F-3 421–425, F-5 426–473, F-6 474–497, G-1 498–513, H-1 514–517**; special sections **§36 518–584, §37 585–654, §38 655–669, §39 670–685, §40 686–748, §41 749–777**.

### Back-matter pp.775–777 (the +3 pages added by PR #155)

PR #155 named three new appendices: **붙임 8 — 인구감소지역 지정 변경 고시**, **붙임 9 — 우수인재 특별귀화 평가기준**, **붙임 10 — 우수인재 국적신청 상세기술서**. Page-cited extraction confirms those titles and shows the full K-STAR §41 back-matter appendix block runs **붙임 7–12 across pp.769–777**:

| Appendix | Title | Page(s) |
|---|---|---:|
| 붙임 7 | 평가항목별 입증서류 | 769 |
| 붙임 8 | 인구감소지역 지정 변경 고시 | 770 |
| 붙임 9 | 우수인재 특별귀화 평가기준 | 771–773 |
| 붙임 10 | 우수인재 국적신청 상세기술서 | 774–775 |
| 붙임 11 | 우수인재 가점 항목별 점수표 | 776 |
| 붙임 12 | 우수인재 추천서 | 777 |

**Honest attribution:** strict per-붙임 new-vs-pre-existing attribution cannot be re-derived in PR B because PR #155 replaced the prior 774-page PDF in place. The verifiable facts are the page-cited layout above and the net +3 pages (pp.775–777, falling on 붙임 10's tail through 붙임 12). PR #155's 붙임 8/9/10 identification is recorded faithfully; the live back-matter additionally carries 붙임 11 and 붙임 12.

---

## Crosswalk + record classification (Task steps 8–10)

Every one of the 58 `visa_data.json` records was mapped to its manual section(s) and classified into exactly one of `confirmed | partial | missing | duplicate | stale | unresolved`:

| Classification | Count |
|---|---:|
| `confirmed` (manual section located, high confidence) | 30 |
| `partial` (no header / split / approximate) | 4 |
| `missing` (helper / scenario / FAQ, not in manual) | 17 |
| `duplicate` (D-4-2K ×2) | 2 |
| `stale` (F-4, H-2 Feb-2026 sub-manual; F-6 2026.3) | 3 |
| `unresolved` (K-STAR, REGION-S) | 2 |

**`confirmed` does not mean verified.** All 41 manual-dependent records remain `verified=false` / `needsManualReview=true`.

The audit explicitly covers each required topic:

- **D-4-2K duplicate/sub-code issue** — indices 24 (한국어연수 K-연수생) and 55 (기업맞춤형인턴십 K-Trainee) share one code → `duplicate` → PR D.
- **F-6 stale income notes** — 3 occurrences of `"2026.3"` in the income note → `stale` → PR D; target stay §33 pp.474–497.
- **Top-Tier visa records** — modeled as sub-codes D-10-T/E-7-T/F-2-T/F-5-T; dedicated section visa §39 pp.445–455 / stay §39 pp.670–685.
- **K-STAR visa track records** — index 56 → `unresolved` → PR D; visa §40 pp.456–484 / stay §41 pp.749–777.
- **지역특화형비자** — stay §37 pp.585–654 (REGION-S, index 57) → `unresolved` → PR D.
- **광역형 비자 시범사업** — stay §40 pp.686–748 (REGION-S) → `unresolved` → PR D.
- **국내 성장 기반 외국인 청소년 취업·정주 체류제도** — stay §38 pp.655–669 (no dedicated visa_data record; flagged for PR D coverage decision).
- **F-4 / H-2 / 외국국적동포 records** — Feb-2026 sub-manual; visa §38 pp.379–444 / stay §36 pp.518–584 → `stale` → PR D.
- **Manual-dependent helper records** — 17 `missing` helper/scenario/FAQ records; not manual-sourced; no action.
- **doc_master.json alignment** — 79 entries: 66 referenced, **12 corrupted Korean-string ids**, 1 unused (`doc_arc_fee`) → hygiene cleanup queued for PR C.

---

## Patch policy (Task step 11–12)

Per the hard rules, **no** substantive patch was applied:

- No stale date marker corrected (requires page-cited evidence → PR D).
- No eligibility, income, fee, stay-period, or procedure claim updated.
- No `verified` flag advanced; no `needsManualReview` removed.
- No requiredDocuments / aliases / UI copy rewritten.
- No `visa_data.json`, `backend/data/visas.json`, or `doc_master.json` change.

### Follow-up patch queue

**PR C — safe source-grounded metadata / doc-ref only (34 candidates):** update `sourceManualStatus` page citations on `confirmed`+`partial` records to the re-derived 484/777-page anchors; doc_master.json hygiene (remove 12 corrupted ids, verify `doc_arc_fee`). No legal/content change.

**PR D — limited requiredDocuments / content patches, page-cited only (7 candidates):** F-6 income note (stay §33 pp.474–497), D-4-2K dedup (visa §12 / stay §12), F-4+H-2 sub-manual (stay §36 pp.518–584), K-STAR (visa §40 / stay §41 pp.749–777), REGION-S (stay §37 + §40). Each patch requires exact page/section evidence.

**Neither PR C nor PR D is performed in this branch.**

---

## Validation (Task step "Validation")

| Check | Result |
|---|---|
| `python3 -m json.tool` on all 3 regenerated JSON + manifest + 3 production JSON | ✅ valid |
| `scripts/check_source_manuals.py` | ✅ OK (484 / 777) |
| `scripts/check_source_updates.py --local-only` | ✅ OK |
| `scripts/sync_visa_data.py --check` | ✅ OK (no edit) |
| `scripts/check_visa_data_text_integrity.py` | ✅ PASS |
| `scripts/check_required_documents_coverage.py` | ✅ no regressions |
| `scripts/validate_coverage_matrix.py` | ✅ OK |
| `scripts/validate_manual_grounding_candidate.py` | ✅ OK |
| `scripts/check_repo.sh` (`ALLOW_BACKEND_TEST_SKIP=1`) | ✅ pass |

See the PR description for the captured command output.

---

## Legal Disclaimer

Paradiso is reference software. Nothing in this report, the audited JSON files, or any rendered output constitutes legal advice, an official immigration decision, or a guarantee of admissibility, eligibility, or processing outcome. Korean immigration law and Ministry of Justice manuals change irregularly. Users must verify any specific case with 출입국·외국인청, HiKorea (`hikorea.go.kr`), 1345 종합민원안내, or a qualified Korean immigration professional. Where this audit could not verify a specific page, statute, or source-date claim, the underlying record is left flagged with `needsManualReview = true`.
