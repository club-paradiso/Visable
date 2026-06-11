# Phase 0 — Baseline Audit (short-stay checker · subcode collapse UX · F-4 route guide)

- Audit date: 2026-06-11
- Branch: `claude/compassionate-bohr-d4xd66` (session working branch; equals `origin/main` at start)
- Latest commit at baseline: `6dbe792` — "fix: correct document taxonomy after browser QA (#332)"
- Repo root: `/home/user/Paradiso`

## 1. Dependency branch / commit status

| Dependency | Status | Evidence |
| --- | --- | --- |
| `fix/backend-fastapi-starlette-compat` | **MERGED** | commit `c0cdf68` "fix: restore FastAPI Starlette compatibility (#330)" |
| `fix/rendered-document-dedupe-hotfix` | **MERGED** | commit `0c4bf55` "fix: wire rendered document dedupe into checklist (#331)"; `audits/post-merge-hotfix/check_rendered_document_duplicates.js` exists |
| `fix/browser-document-taxonomy-qa` | **MERGED** | commit `6dbe792` "fix: correct document taxonomy after browser QA (#332)"; `audits/browser-document-qa/check_document_taxonomy.js` exists |
| `fix/employment-info-online-report` | **NOT MERGED / NOT FOUND** | no matching commit or remote branch; old label `외국인 직업 신고서` still present 12× in `visa_data.json` (e.g. lines 14358, 14537) |
| `fix/document-terminology-and-fee-labels` | **NOT MERGED / NOT FOUND** | no matching commit or remote branch; standalone `"수수료"` document-array items still present 24× in `visa_data.json`; no `audits/terminology-normalization/` or `audits/fee-label-cleanup/` directories |

Remote branches available: only `origin/main` and `origin/claude/compassionate-bohr-d4xd66`.
The two unmerged fixes do not exist anywhere in the remote history — they appear to be
planned-but-never-landed work.

**Dependency decision:** the three rendering/taxonomy/dedupe dependencies that this feature
actually touches at runtime ARE merged. The two missing fixes are data-label cleanups inside
`visa_data.json` (protected file). This feature adds new, self-contained modules
(external JSON + new deferred JS + a generic subcode-grouping render path) and does not
read or rewrite those legacy labels, so it does not depend on them. Per the task rules we:

- do NOT rebuild those fixes inside this PR,
- keep all NEW user-facing content canonical (no plain `수수료`, no `외국인 직업 신고서`,
  `통합신청서(별지 제34호 서식)` where intended, F-4 fee wording procedure-specific),
- report the missing dependencies + recommended merge order in the final report.

Recommended merge order (unchanged from task): Starlette compat → rendered dedupe →
taxonomy QA → employment-info report guidance → terminology/fee labels → **this feature**.
The first three are already in `main`, so this branch is based on current `main` and only
the employment-info and terminology/fee PRs remain outstanding (they can land before or
after this PR; no file-level conflict expected — they target `visa_data.json` records,
this PR targets new files + render logic).

## 2. Current data shape

`visa_data.json` = array of **42 top-level records** (one per status family; subcodes are
nested under `subCodes`/`subcodes`). Relevant records:

- **B-1 사증면제협정** (`cat: short`): subcodes `B-1-1` "B-1 일반여권 유효 67개국"
  (full 67-country list with stay periods inside `addReq`, PDF 기준일 2024-12-04),
  `B-1-2` "B-1 일시정지 3개국" (방글라데시·파키스탄·라이베리아).
- **B-2 관광통과·무사증** (`cat: short`): subcodes `B-2-1` "일반 무사증 (45개국·지역)"
  (30/90일·6개월 그룹 목록 inside `addReq`, PDF 기준 2022-11-01),
  `B-2-2` "제주 무사증 입국" (체류 30일; **제외국 23개국 목록 — 이란 포함** — inside `addReq`).
- **C-3 단기방문**: 11 subcodes (C-3-1 단기일반(친족), C-3-2 단체관광, C-3-3 의료관광,
  C-3-4 일반상용, C-3-5 협정단기상용, C-3-6 단기상용, C-3-7 도착관광, C-3-8 동포방문,
  C-3-9 일반관광, C-3-10 순수환승, C-3-11 교대선원(폐지/deprecated)).
- **F-4 재외동포** (`cat: family`): 13 subcodes (F-4-11 … F-4-30), procedures
  extension/registration/statusChange each with 1 variant. `newReq` already carries the
  2026.2.12 H-2→F-4 통합 and 공통서류(한국어능력·해외 범죄경력증명서·동포입증·조기적응) summary.

No country lists are embedded in `index.html` (베트남 appears only as the Vietnamese
language label). The Jeju entry-denied / stay-area-expansion country data exists nowhere
in the repo outside the single `B-2-2.addReq` string.

### Known source discrepancies found at baseline (logged for manual review)

1. **Jeju entry-denied count**: task seed list = 22 countries (no 이란);
   existing `visa_data.json` B-2-2 record = "제외국 23개국" **including 이란**.
   → rules.json will keep 이란 flagged as denied (safe direction) with an explicit
   source-conflict note and `needs_refresh` freshness.
2. **B-2-1 아르헨티나**: 2026.5 visa manual table (2022-09-22 기준) says 30일;
   repo B-2-1 list (2022-11-01 기준) says 90일. Both are stored official copies of
   different dates → seeded from the newer repo copy, flagged for refresh.
3. **B-2-1 count**: manual region headers sum to 46 (incl. 괌 as separate 지역);
   repo subcode name says "45개국·지역" and its list contains 44 entries (괌 folded
   under 미국). Flagged; checker wording avoids hardcoding a count.

## 3. Current aliases & search behavior

- `ALIAS_MAP` (index.html ≈ line 15537) maps 제주무사증/제주 무사증/제주직항 → `B-2-2`,
  사증면제협정* → `B-1`, 무사증/무비자 → `B-2`, 전자여행허가 → `K-ETA`.
- `expandKeywords` adds `b-2-2` for "제주", `b-1` for "협정".
- `renderResults` (≈15767): code-like queries are reduced to exact-match records
  (`getExactQueryMatchRank`: top-level 10000 / nested subcode 5000 / alias 4000…), so a
  search for `C-3` or `B-2-2` renders exactly ONE parent card.
- Inside the card, `getMatchingSubcodes(v, kw)` does **substring matching**:
  query `C-3` matches every `C-3-x` subcode code → ALL 11 C-3 subcodes (13 for F-4,
  16 for G-1, 10 for F-2, 11 for E-7) are lifted into the "내 상황과 관련" matched group
  as full `manual-subcode-card`s at the top of the card.
- The remaining-group collapse (`manual-subcode-more`) only collapses groups after the
  first; with no/one group the whole list renders flat.

**→ Confirmed flooding mechanism for broad parent searches:** one parent card, but every
subcode rendered as a full card inside it (matched-group lift defeats the collapse).
Exact subcode searches (`C-3-9`, `B-2-2`, `G-1-5`) behave well already: only the one
matching subcode is lifted and highlighted.

## 4. Vietnam at baseline

| Where | Present? |
| --- | --- |
| General visa-free / K-ETA (B-1 일반여권 67 / B-2-1 목록) | **Not listed** (B-1 외교·관용만 90일) |
| Jeju entry-denied list (B-2-2 addReq 23개국) | **Not listed** |
| Jeju stay-area expansion permit list | **Not in repo at all** (no such list exists at baseline) |
| C-3 fallback logic | **None exists** (no nationality-based routing anywhere) |

## 5. F-4 baseline UI

- `ROUTE_WIZARD_CONFIG['F-4']` renders an in-card chooser titled
  **`F-4는 어떤 경로로 진행하시나요?`** (`f4RouteTitle`, ≈16066) with 5 procedure-keyed
  chips (사증발급/자격변경/거소신고/연장). It maps to procedure tabs — useful, but it asks
  the user to pick a *legal/procedural* route name first; no life-situation guidance,
  no nationality-loss / dual-national / military-service screening, no FBI·아포스티유
  preparation card, no US consular workflow, no 90-day 거소신고 timeline framing.
- No `data/f4/` directory, no external F-4 route data, no `assets/js/` directory at all.

## 6. Current user-facing gaps (what this task adds)

1. No nationality-based short-stay answer ("Can I enter visa-free? Jeju only? K-ETA?
   C-3-9?") — users must read B-1/B-2 legal text and country strings inside `addReq`.
2. Broad parent code searches flood the open card with every subcode as a full card.
3. F-4 guidance starts from a legal route name instead of the user's life situation;
   FBI/아포스티유, 국적상실/복수국적/병역, and post-entry 거소신고 are buried in prose.

## 7. Environment constraints recorded at baseline

- Outbound network to official sites (`www.k-eta.go.kr`, `www.hikorea.go.kr`) returns
  **403 via the environment proxy** → live source refresh impossible in this session →
  update script must run `--from-fixtures`, `sourceStatus: needs_refresh`, UI must show
  the official-refresh warning.
- Local official source material available:
  `docs/data/claude_opus_manual_extraction_2026_05/visa_hwp_full.txt` (2026.5 사증발급
  안내매뉴얼 extraction; B-1 협정 일람표 2022-09-22 기준, B-2 무사증 일람표, C-3 chapter,
  재외동포(F-4) chapter + 별첨1 해외 범죄경력증명서 제출기준 incl. FBI·아포스티유),
  `stay_hwp_full.txt` (2026-06-01 체류매뉴얼 extraction; 국내거소신고 절차).
- Playwright + Chromium 141 available → real browser QA feasible.
- Raw grep outputs: `baseline_occurrences.txt`, `manual_file_candidates.txt` (this dir).
