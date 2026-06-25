# Blocked extraction report — 260623 체류민원 자격별 안내 매뉴얼 (stay manual)

**Date:** 2026-06-25
**Branch:** claude/paradiso-submission-readiness-7xa5d5
**Scope:** Submission-readiness source refresh. Document why the latest official
HiKorea stay manual (260623) could not be downloaded/extracted here, and what was
used instead. No substantive immigration guidance was changed from an unreadable
source.

## Target official source
- Notice: **체류자격별 통합 안내 매뉴얼(최신)**
- URL: https://www.hikorea.go.kr/board/BoardNtcDetailR.pt?BBS_SEQ=1&BBS_GB_CD=BS10&NTCCTT_SEQ=1062&page=1
- Authority: 법무부 출입국·외국인정책본부
- Requested attachment: `260623 체류민원 자격별 안내 매뉴얼.hwpx`
- Companion change log: `260623 사증.체류 민원 자격별 안내 매뉴얼 수정 이력.hwpx`

## What was blocked
- **Direct download failed.** This execution environment's network policy returns
  `HTTP 403` on the CONNECT tunnel for `*.go.kr` hosts:
  ```
  curl -sS "https://www.hikorea.go.kr/board/BoardNtcDetailR.pt?...NTCCTT_SEQ=1062..."
  curl: (56) CONNECT tunnel failed, response 403
  ```
  The HiKorea board, its attachments, and the Korea Visa Portal were all
  unreachable. A Playwright/browser-context download could not be attempted
  because the same outbound policy blocks the host.
- **HWPX/HWP body extraction is independently blocked** in this repo's tooling for
  distribution-mode files (documented across prior audits in
  `docs/source-manuals/source_manifest.json` → `audit_history`): ViewText sections
  are encrypted distribution-mode payloads; LibreOffice + h2orestart returns
  "source file could not be loaded"; pyhwp requires Python 2.7.

## What was used instead (readable, official, already in-repo)
- `docs/source-manuals/2026-06-17/extracted/full_text/stay_manual_260617.txt`
  - Cover: **외국인체류 안내매뉴얼 2026. 6.** / 법무부 출입국·외국인정책본부
  - 778 PDF pages of readable page-text (TOC covers A-1 … 광역형 비자 / K-STAR).
  - `sha256:a7c650e7b57fb31e3269bd90ce333b0177a933f214fc548fca6c0aa3dfcdbb42`
- This is the **2026.6 generation** of the official stay manual (the 260623 file is
  a within-June revision of the same edition; the 260623 "수정 이력" change log is the
  authoritative record of what differs).

## Decision (conservative, per project rules)
- **Did NOT** promote 2026.6 text into `visa_data.json` / `backend/data/visas.json`
  / `doc_master.json`. The active grounding manuals remain the verified 2026.5
  generation (stay `2026-06-01` PDF, visa `2026-05-21` PDF).
- **Registered** the readable 2026.6 extraction as a `not_configured`
  reference-only source in `data/source_registry.json`
  (`stay_manual_2026_06_17_txt`), and registered the 260623 notice itself
  (`hikorea_latest_manual_notice_260623`) so the latest official source is
  recorded with its URL.
- Source invariants (`scripts/check_source_grounding_metadata.py`) remain green
  because reference entries are `not_configured` and the active manual invariant
  is untouched.

## Follow-up to promote 260623 content (requires human review)
1. Obtain `260623 체류민원 자격별 안내 매뉴얼.hwpx` from a network-enabled context.
2. Read `260623 ... 수정 이력.hwpx` to scope exactly what changed vs 2026.6 base.
3. Diff against `stay_manual_260617.txt`; patch only source-confirmed deltas
   surgically (no bulk rewrite of protected data files).
4. Advance the active stay-manual invariant + manifest in the same reviewed PR.
