# Blocked extraction report — 260617 사증민원 자격별 안내 매뉴얼 (visa issuance manual)

> Superseded on 2026-06-26 by the readable PDF refresh in
> `backend/data/audits/full_2026_pdf_refresh_audit.md`. This report remains as a
> historical record of the protected HWP/HWPX body-extraction blocker and should
> not be read as the current active-source decision.

**Date:** 2026-06-25
**Branch:** claude/paradiso-submission-readiness-7xa5d5
**Scope:** Submission-readiness source refresh. Document why the latest official
HiKorea visa-issuance manual (260617) could not be downloaded/extracted here, and
what was used instead. No substantive immigration guidance was changed from an
unreadable source.

## Target official source
- Notice: **체류자격별 통합 안내 매뉴얼(최신)**
- URL: https://www.hikorea.go.kr/board/BoardNtcDetailR.pt?BBS_SEQ=1&BBS_GB_CD=BS10&NTCCTT_SEQ=1062&page=1
- Authority: 법무부 출입국·외국인정책본부
- Requested attachment: `260617 사증민원 자격별 안내 매뉴얼.hwp`

## What was blocked
- **Direct download failed.** Outbound network policy returns `HTTP 403` on the
  CONNECT tunnel for `*.go.kr` hosts (HiKorea board, attachments, and Korea Visa
  Portal all unreachable). Browser-context download could not be attempted for the
  same reason.
- **HWP distribution-mode body extraction is independently blocked** by available
  tooling (see `docs/source-manuals/source_manifest.json` → `audit_history`).

## What was used instead (readable, official, already in-repo)
- `docs/source-manuals/2026-06-17/extracted/full_text/visa_issue_manual_260617.txt`
  - Cover: **사증발급 안내매뉴얼 (체류자격별 대상 첨부서류 등) 2026. 6.**
  - 487 PDF pages of readable page-text.
  - `sha256:9c9412cade8bc6826444c77cabf01821a00545a4ec365dad32b223fbb8aa7d06`
- This is the **2026.6 generation** of the official visa-issuance manual. The
  260617 attachment is the HiKorea HWP packaging of the same edition.

## Decision (conservative, per project rules)
- **Did NOT** promote 2026.6 text into protected data files. The active
  visa-issuance grounding manual remains `visa_manual_2026_05_pdf` (2026.5 /
  2026-05-21).
- **Registered** the readable 2026.6 extraction as a `not_configured`
  reference-only source (`visa_manual_2026_06_17_txt`) and recorded the latest
  HiKorea notice (`hikorea_latest_manual_notice_260623`).
- 사증발급(visa issuance) and 체류(stay) sources are kept strictly separate, per
  project rules.

## Follow-up to promote 260617 content (requires human review)
1. Obtain `260617 사증민원 자격별 안내 매뉴얼.hwp` from a network-enabled context.
2. Diff against `visa_issue_manual_260617.txt`; patch only source-confirmed deltas
   surgically.
3. Advance the active visa-manual invariant + manifest in the same reviewed PR.
