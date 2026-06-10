# Remaining Run — Final Summary

**Branch:** `data/manual-doc-normalization-remaining` (from main @ 605110a, post-#327)
**Date:** 2026-06-10

## Coverage
- Total top-level codes in `visa_data.json`: **42** (no duplicate codes)
- Codes audited in this remaining run: **42 / 42** (batches R01–R07, every code has a
  recorded entry in `remaining_batch_R0*.md`)
- Extended scope beyond merged PR #327: post-merge mechanical re-scan; `documents_extension`
  (233 entries) + `documents_registration` (6) validated against per-code stay-manual
  sections (extension/registration = stay tabs by the tab rule); `documents_initial`
  (156 entries) provenance-gated; `doc_master.json` (101 entries) internal consistency;
  ID-array rendered-label duplicate scan; D-2 attributed-array deep check.

## Confirmed fixes: 2 (both Type D, evidence `CONFIRMED_EXACT`)
| # | Code | Tab/array | Field | Old → New |
|---|---|---|---|---|
| 1 | D-10 | 체류기간연장 / documents_extension | `documents_extension[9].name` | `결핵건강진단서` → `결핵진단서` |
| 2 | E-8 | documents_initial | `documents_initial[3].name` | `결핵건강진단서` → `결핵진단서` |

Evidence: `결핵건강진단서` = **0 hits in both manuals**; official `결핵진단서` = 14 hits in
each (stay manual 공통 §5 "외국인 결핵진단서 제출 의무 관련 안내", L453–477, incl.
"결핵 고위험국가(35개국)" matching the entries' note "보건소/지정병원, 고위험 35개국 필수";
L461 explicitly covers 계절근로자 → E-8). Verified distinct from `결핵검진확인서`
(different document; F-2 점수제/영주/K-STAR contexts). E-8's array provenance is ambiguous,
but the official term is identical in BOTH manuals → authority-independent.

By type: A = 0 · B = 0 · C = 0 · D = 2 · E = 0 (no embedded-manual strings remain anywhere).

## Ambiguous / skipped (no change)
- **Standardized template labels (~200 entries across 33 visas):** documents_extension uses
  an intentional app-wide display template (`여권 원본 및 인적사항면 사본`, `외국인등록증 원본
  및 사본(거소증 해당자 포함)`, `통합신청서(별지 제34호 서식)`, fee-caution entries, 체류지
  guidance entry). Not per-visa manual transcriptions; none "clearly wrong"; mass rewrite =
  forbidden broad edit → skip.
- **Umbrella/compressed display forms:** `기타 체류목적 입증서류`, `신청 사유 입증서류`,
  `연수계속 입증서류`, `소득금액증명원 등 소득입증서류`, `TOPIK 성적표 또는 한국어능력
  입증서류`, `사회통합프로그램(KIIP) 이수증/합격증명서` (manual has multiple specific
  variants), etc. → not naming errors → skip.
- **0-manual-hit labels that cannot be confirmed OR removed:** `점수제 자기평가표 및
  증빙서류` (D-10/F-2), `외국인 취업정보 온라인 신고 내역` (F-6) → AMBIGUOUS; removal
  not sanctioned (manual coverage may be lossy) → skip, flagged for human review.
- **Whitespace/style-only:** `부가가치세 과세표준증명` vs manual `부가가치세과세표준증명`
  → explicitly out per "do not change whitespace differences" → skip.
- **D-2 deep-check (10 entries):** faithful decompositions/expansions, more-specific official
  form name, protected fee item, caution-note entry (removal would weaken a warning),
  style paraphrase (`정상 학업 수행 입증서류`) → all skip (detailed in R01 report).
- **documents_initial (155 entries excl. E-8 fix):** no provenance → `AMBIGUOUS_MANUAL_MISMATCH`.
- **doc_master.json:** 3 dup-ko_name alias pairs (`체류지 입증서류`, `통합신청서`, `여권` —
  rich entry + `_generic` placeholder) and 12 placeholder `Required Supporting Document`
  en_names → structural refactor outside A–E fix taxonomy → recorded as follow-up.
- **D-10 Type N near-dup:** previously closed in #327; no new evidence; not re-opened.

## Files changed
| File | Change |
|---|---|
| `visa_data.json` | 2 lines (Type D label fixes) |
| `backend/data/visas.json` | 2 lines — regenerated via `scripts/sync_visa_data.py` only |
| `audits/manual-doc-normalization/mechanical_findings.json` | regenerated post-merge (F-4/H-2 Type E findings now resolved on main) |
| `audits/manual-doc-normalization/remaining_*.md`, `gen_remaining_reports.py` | new audit artifacts |

Untouched: backend/AI/search/render logic, disclaimers, fee amounts, subcode data,
procedure logic, `doc_master.json`, `index.html` (0 embedded-manual strings).

## Validation
- `python3 -m json.tool` both files → VALID
- `scripts/sync_visa_data.py --check` → in sync
- `git diff --check` → clean
- `scripts/check_repo.sh` → **PASS** (baseline before edits also PASS)
- `grep "embedded manual pp\."` → none

## Remaining risks
1. `documents_initial` arrays remain unvalidatable until provenance (`_source_notes`) is
   recorded per visa — follow-up.
2. doc_master placeholder entries (`Required Supporting Document` en_names, `_generic`
   aliases) — structural cleanup follow-up.
3. Flattened D-10 `extension.requiredDocs` array (headings-as-documents) — unchanged,
   needs structured re-extraction (explicitly out of scope: no new extraction pipeline).

## Recommendation
**Safe to commit.** The diff is 2 surgical label corrections, both backed by exact,
authority-correct manual evidence, plus regenerated/new audit artifacts. Validation green,
no regression vs baseline.
