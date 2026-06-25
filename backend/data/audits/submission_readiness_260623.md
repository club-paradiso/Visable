# Paradiso submission-readiness audit — 260623 cycle

**Date:** 2026-06-25
**Branch:** `claude/paradiso-submission-readiness-7xa5d5`
**Goal:** Make Paradiso demo/judge-ready: refresh official source metadata, remove
visible test/placeholder artifacts, confirm Waymaker demo-safety, keep validation
green. Layer-1 (submission blockers) prioritized over Layer-2 (wider scraping).

## Official source files
- Notice: **체류자격별 통합 안내 매뉴얼(최신)** — 법무부 출입국·외국인정책본부
- URL: https://www.hikorea.go.kr/board/BoardNtcDetailR.pt?BBS_SEQ=1&BBS_GB_CD=BS10&NTCCTT_SEQ=1062&page=1
- Latest attachments referenced: `260623 체류민원 자격별 안내 매뉴얼.hwpx`,
  `260617 사증민원 자격별 안내 매뉴얼.hwp`, `260623 사증.체류 민원 자격별 안내 매뉴얼 수정 이력.hwpx`

## Extraction result (honest)
- **Direct download from HiKorea was BLOCKED** by this environment's outbound
  network policy: `curl: (56) CONNECT tunnel failed, response 403` on `*.go.kr`.
  No browser-context fallback was possible (same host policy).
- **HWP/HWPX distribution-mode body extraction remains blocked** by available
  tooling (documented in prior audits).
- **Readable official 2026.6 text already exists in-repo** and was used as the
  closest official reference (NOT promoted into protected data files):
  - `docs/source-manuals/2026-06-17/extracted/full_text/stay_manual_260617.txt`
    — 외국인체류 안내매뉴얼 2026.6, 778 pages, `sha256:a7c650e7…dfcdbb42`
  - `docs/source-manuals/2026-06-17/extracted/full_text/visa_issue_manual_260617.txt`
    — 사증발급 안내매뉴얼 2026.6, 487 pages, `sha256:9c9412ca…b8aa7d06`
- Blocked reports: `backend/data/audits/stay_manual_260623_blocked.md`,
  `backend/data/audits/visa_manual_260617_blocked.md`.

## What was updated
1. **Source registry** (`data/source_registry.json`) — added 3 entries, all
   `not_configured` (reference-only, no auto-fetch):
   - `stay_manual_2026_06_17_txt` (2026.6 stay extracted text)
   - `visa_manual_2026_06_17_txt` (2026.6 visa extracted text)
   - `hikorea_latest_manual_notice_260623` (the canonical latest-manual notice +
     URL, naming the 260623/260617 attachments)
   - Active grounding manuals (stay 2026-06-01, visa 2026-05-21) were **left
     unchanged**; source-grounding invariants stay green.
2. **Visible artifact removal** (UI polish):
   - Removed the disabled **"💎 Pro / 서비스 예정" (coming-soon)** answer-mode button
     from both `index.html` and `ai.html`; cleaned the now-dead pro/coming-soon
     toast handler. ("pro" remains a backend-reserved mode; only the user-visible
     coming-soon control was removed.)
   - Reworded the occupation-code coverage note from
     `직종 대·중분류(전체표 준비 중)` / `(full table coming soon)` to the honest
     stable label `직종 대·중분류` / `occupation major/sub groups`.
3. **Source visibility (landing)** — the "법무부 매뉴얼 기반" panel note now states
   that the manual links point to the latest official 2026.6 manuals while the
   structured guidance is verified against the 2026.5 manual, and to confirm
   latest changes in the linked official source.

## What was NOT updated (and why)
- No substantive immigration content was changed: `visa_data.json`,
  `backend/data/visas.json`, `doc_master.json` untouched. The 2026.6 source could
  not be read in a form that justifies surgical legal edits, so per project rules
  the verified 2026.5 baseline was preserved.
- Per-record `2026.5 매뉴얼 확인됨/확인 필요` badges were intentionally NOT relabeled to
  a June date — they honestly reflect the manual the data was verified against.
- Demo-flow modules (F-4 route guide, short-stay checker, complex-status guide,
  visa-route guide) were left as-is: triage confirmed they are already
  demo-ready, and their "prose fallback → 전체 보기" and disabled-`not_applicable`
  buttons are intentional, source-honest designs from prior audits.

## P0 demo flows checked (via read-only triage + existing regression suites)
- Search: D-2, D-4, D-10, E-7, F-2, F-4, F-5, F-6, G-1, G-1-2, G-1-5, C-3, B-1, B-2.
- F-4 route wizard: search-first, one-question-at-a-time, overseas-Korean
  distinction preserved, subcodes behind progressive disclosure — clean.
- Short-stay checker: B-1/B-2/C-3 handled separately with deterministic wording,
  no visa/stay mixing — clean.
- Document checklist: no duplicate rows; conditional docs not shown as universal;
  prose-only statuses hand off honestly to the full detail screen.
- Waymaker: 75s AbortController ceiling (no infinite hang), polished multilingual
  fallback (incl. HiKorea/1345 guidance), public-safe contract hides raw internal
  codes behind a dev flag, visa-vs-stay separation preserved.

## Test-looking artifacts removed
- "💎 Pro / 서비스 예정" coming-soon button (×2 files) + dead toast handler.
- "전체표 준비 중 / full table coming soon" occupation-code note.
- (Other "beta/PLANNED/debug" infra confirmed gated behind URL params / localStorage
  dev flags — not user-visible; left as-is.)

## Validation
- `ALLOW_BACKEND_TEST_SKIP=1 bash scripts/check_repo.sh` → pass (14/14 stages).
- `scripts/check_source_grounding_metadata.py` → pass (pre-existing freshness
  warnings only).
- i18n (`check_i18n.js`, `smoke_static_i18n.mjs`), hardcoded-text, popup-i18n,
  AI-shell semantics, F-4/short-stay/complex-status/waymaker UI checks → pass.

## Known limitations / follow-up after submission
- 260623/260617 HWP(X) attachments could not be downloaded here (network policy
  403). Promote 2026.6 content in a network-enabled, human-reviewed PR using the
  260623 change log to scope deltas.
- Mission-specific embassy/consulate overlays beyond the existing F-4 hub were not
  expanded (Layer-2). No claim of exhaustive global coverage is made.
- Reaching Level-A document checklists for D-2/D-4/E-7/G-1/F-5 requires a
  source-reviewed pass mapping prose document names to `doc_master` IDs.
