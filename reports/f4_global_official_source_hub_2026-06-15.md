# F-4 Global Official-Source Hub — Implementation Report

**Date:** 2026-06-15
**Branch:** `feature/f4-global-official-source-hub`
**Scope:** Rebuild the F-4 (재외동포 / Overseas Korean) guidance experience as a
search-first, country-ready, official-source navigator. No unrelated UI
refactors, visa-data cleanup, model-routing, or brand work are included.

> Critical posture: this PR does **not** fabricate immigration law, consular
> procedures, fees, processing times, document names, or country-specific
> requirements. Common F-4 rules are grounded in the stored official manuals;
> country specifics are shown only where an official source supports them, and
> everything else falls back to a clear official-check message.

---

## 1. Branch
`feature/f4-global-official-source-hub` (created from the session base).

## 2. Changed / new files

**New data (`data/f4/`):**
- `base.json` — common F-4 rules + hub section bodies (manual-grounded).
- `diagnostic.json` — the guided status diagnostic (questions, routing, CTAs).
- `faq.json` — procedure-based FAQ (3 groups).
- `countries.json` — global country registry (60 countries/territories).
- `country_overlays.json` — country-specific overlays (20 priority countries).
- `country_overlay_schema.json` — JSON Schema for overlay entries.
- `source_coverage_matrix.json` — per-country coverage matrix (60 rows).
- `sources.json` — rewritten/extended source registry (22 sources).

**Changed:**
- `assets/js/f4-route-guide.js` — fully rebuilt as the search-first diagnostic
  entry panel + accessible modal hub.
- `assets/js/short-stay-checker.js` — one stale label cross-reference updated.
- `scripts/check_f4_route_guide.mjs` — rewritten validator for the new model.
- `scripts/check_repo.sh` — wired the F-4 validators into CI (step 9c).

**Added:**
- `scripts/smoke_f4_hub.mjs` — automated stand-in for the Phase-11 manual QA.

**Deleted:**
- `data/f4/routes.json` — superseded; its country-neutral content moved to
  `base.json`, and its US-specific content moved into the US overlay.

**Untouched (protected / out of scope):** `visa_data.json`,
`backend/data/visas.json`, `doc_master.json`, `index.html`, `ai.html`,
`data/i18n/*`, and the generic `ROUTE_WIZARD_CONFIG` (F-6/G-1/F-2/etc.).

## 3. Architecture before → after

**Before:** A single `data/f4/routes.json` + `f4-route-guide.js` rendered a
US-centric, inline, auto-expanded "어떤 상황에 가까우신가요?" route picker into
`#f4RouteGuide`. FBI / U.S. Department of State apostille / a USD-45 fee were
treated as if broadly applicable.

**After:** Layered, country-ready model:
- **Common base** (`base.json`) — country-neutral rules, separate from country
  data.
- **Diagnostic** (`diagnostic.json`) — the search-first guided check.
- **Country layer** (`countries.json` + `country_overlays.json` +
  `country_overlay_schema.json` + `source_coverage_matrix.json`) — overlays only
  where official sources support them; safe fallback otherwise.
- **FAQ** (`faq.json`) — procedure-based, source-grounded.
- **Sources** (`sources.json`) — every claim is traceable.
- The guide JS renders a **compact diagnostic entry panel** first, and an
  **accessible modal hub** (diagnostic → result → full hub tabs) on demand.

`index.html` is unchanged: the existing `#f4RouteGuide` mount and deferred
`<script>` are reused, and the modal is created by the module itself — so no new
Korean strings were hardcoded into `index.html`.

## 4. Search-first diagnostic flow

An F-4-relevant search (`F-4`, `재외동포`, 거소증, 자격변경, 재외공관, FBI/아포스티유,
country + F-4, …) renders a **compact panel** titled
**"F-4 안내를 시작하기 전에 확인해주세요"** with the primary CTA **"F-4 절차 확인하기"**.
It never auto-expands the hub. The CTA opens a modal that runs the diagnostic:

1. 현재 대한민국 국적을 보유하고 있나요? *(routing/caution only — never eligibility)*
2. 현재 어디에서 절차를 진행하려고 하나요?
3. 이미 F-4 비자를 발급받았나요?
4. 한국 입국 후 국내거소신고를 했나요?
5. F-4로 입국한 지 90일이 지났나요? *(shown only if "entered with F-4")*
6. 신청 국가 또는 거주 국가를 선택하세요 *(affects country-specific guidance only)*

The result shows the recommended path, why it applies, what to check first,
context note, country-specific note (if a country is selected), an official-check
warning, and CTAs (`F-4 절차 자세히 보기`, `관할 재외공관 찾기`, `비자포털 확인하기`,
`HiKorea 확인하기`, `1345 확인 권장`). "F-4 절차 자세히 보기" opens the full hub
(F-4 한눈에 보기 / 재외공관 신청 / 국내거소신고·거소증 / 국내 자격변경 / 국가별 확인 / FAQ).

## 5. Diagnostic routes implemented
`재외공관 신청 안내` · `국내거소신고/거소증 안내` · `국내 자격변경 안내` ·
`국적/병역/자격 확인 필요` · `공식 확인 필요`. Routing is a pure function
(`computeRoute`) exercised by tests for all 7 Phase-11 scenarios, including:
current Korean national / nationality-unsure → `국적/병역/자격 확인 필요` (never
ordinary applicant guidance); entered + no report + ≤90d → residence report with
the 90-day warning; entered + no report + >90d → urgent `공식 확인 필요` (HiKorea/
1345, no legal conclusion).

## 6. Sources crawled / accepted / rejected

**Accepted (official / high-authority):**
- Stored official manuals: 2026.5 사증발급 안내매뉴얼 (재외동포편 + 별첨1 범죄경력 + 별첨2
  한국어능력) and 2026.6.1 외국인체류 안내매뉴얼 — read directly from the repo
  extraction; the basis for all common rules.
- 찾기쉬운 생활법령정보 (easylaw.go.kr) — F-4 overview & 90-day residence report.
- MOFA mission finder (overseas.mofa.go.kr / mofa.go.kr directory), Korea Visa
  Portal (visa.go.kr), HiKorea (hikorea.go.kr).
- HCCH Apostille Convention status table (hcch.net).
- MOFA mission F-4 pages: US, Canada, Japan, China, Australia (Melbourne), New
  Zealand, Russia, Kazakhstan (Almaty), Singapore.
- US-only: FBI Identity History Summary (fbi.gov), U.S. Department of State
  Office of Authentications (travel.state.gov).

**Rejected:** law-firm marketing pages, immigration-agency posts, Reddit/forums,
SEO pages (e.g. bangduty / immikorea / visaskorea) — used, if at all, only to
discover official URLs; never cited as authority.

**Source caveat:** during research, direct page fetch of easylaw.go.kr,
mofa.go.kr/overseas.mofa.go.kr, and hcch.net returned HTTP 403 (bot protection);
those facts were confirmed via the search engine's index of the exact official
pages. Mission-page specifics are therefore marked accordingly (medium
confidence / `needs_refresh` where appropriate) and pages should be re-read
directly before legal-grade reliance.

## 7. Common F-4 rules added / corrected
Grounded in the 2026.5 manual: F-4 is for foreign-national 외국국적동포 (본인
F-4-41 / 직계비속 F-4-42); current Korean nationals are not applicants; common
docs = 동포 입증서류 + 한국어능력(별첨2) + 해외 범죄경력증명서(별첨1, 6-month validity,
exemptions); 입국일부터 90일 이내 국내거소신고; 거소증 is domestic-only and never
issued overseas; 자격변경 conditions (국내 발급/시스템 확인 가능 시; CIS 동포 prior
동포 사증; mandatory 조기적응프로그램); H-2→F-4 is **not** automatic; 체류기간 1회 최대
3년; 취업 제한 범위; '18.5.1 male nationality-loss 40세 restriction; 2026.2.12 H-2→F-4
integration.

## 8. Country-specific overlays added (20 priority)

| Country | Verification state | Official mission F-4 page | Police-cert info | Authentication info | Overlay / fallback |
|---|---|---|---|---|---|
| United States | verified_official | yes | yes (FBI) | yes (US State apostille) | overlay |
| Canada | partial_official | yes | manual-common | apostille (HCCH, 2024-01) | overlay |
| Japan | partial_official | yes | manual-common | apostille (HCCH) | overlay |
| China | partial_official | yes | yes (공관 안내) | apostille (HCCH, 2023-11) | overlay |
| Australia | partial_official | yes (Melbourne) | manual-common | apostille (HCCH) | overlay |
| New Zealand | partial_official | yes | manual-common | apostille (HCCH) | overlay |
| United Kingdom | partial_official | no | manual-common | apostille (HCCH) | overlay |
| Germany | partial_official | no | manual-common | apostille (HCCH) | overlay |
| France | partial_official | no | manual-common | apostille (HCCH) | overlay |
| Russia | partial_official | yes | manual-common | apostille (HCCH) | overlay |
| Kazakhstan | partial_official | yes (Almaty) | manual-common | apostille (HCCH) | overlay |
| Uzbekistan | partial_official | no | manual-common | apostille (HCCH) | overlay |
| Vietnam | needs_refresh | no | manual-common | consular until 2026-09-11 → apostille | overlay |
| Philippines | partial_official | no | manual-common | apostille (HCCH, 2019-05) | overlay |
| Indonesia | partial_official | no | manual-common | apostille (HCCH, 2022-06) | overlay |
| Thailand | official_check_required | no | not verified | not verified | overlay (fallback-grade) |
| Malaysia | official_check_required | no | not verified | not verified | overlay (fallback-grade) |
| Singapore | partial_official | yes | yes (C.O.C.) | apostille (HCCH, 2021-09) | overlay |
| Brazil | partial_official | no | manual-common | apostille (HCCH) | overlay |
| Argentina | partial_official | no | manual-common | apostille (HCCH) | overlay |

Tiers 2/3 (40 more registry countries) render the common rules + the
official-check fallback. US-only specifics (FBI / U.S. Department of State
apostille / US fee) live **only** in the US overlay (enforced by tests).

## 9. Countries by verification state
- **verified_official:** US
- **partial_official:** CA, JP, CN, AU, NZ, GB, DE, FR, RU, KZ, UZ, PH, ID, SG,
  BR, AR
- **needs_refresh:** VN (apostille in force 2026-09-11)
- **official_check_required:** TH, MY + all tier-2/3 registry countries
- **not_available_or_unclear:** (none asserted)

## 10. UI / UX changes
- Compact diagnostic entry panel replaces the auto-expanded inline route guide.
- Accessible in-page modal hub (diagnostic → result → tabs).
- Country selector inside the diagnostic and the hub; common rules stay visibly
  separate from the country overlay; unverified countries show the fallback.
- Source-confidence badges on the entry panel, country overlay, and each section.
- FAQ retitled to **"F-4 자주 묻는 질문"**; old "어떤 상황에 가까우신가요?" removed.

## 11. Accessibility
`role="dialog"` + `aria-modal="true"` + labelled heading; Escape close; visible
close button; safe backdrop-click close; Tab focus trap (forward + shift); focus
restoration to the trigger; body scroll lock; mobile bottom-sheet layout;
`aria-live` result region; keyboard-operable options/tabs/selector.

## 12. i18n
F-4 strings live in `data/f4/*.json` + the module's `STR` object, matching the
pre-existing F-4 subsystem pattern (Korean-canonical). Country labels include
`labelKo`/`labelEn` (and `labelZh` for priority/major countries). `index.html`
and `data/i18n/*` are untouched; main-app language switching and the Korean
fallback are unaffected. No narrow no-break spaces or special Unicode introduced.

## 13. Validation results (all pass, offline)
- `node scripts/check_f4_route_guide.mjs` → **82 checks, 0 failures**
- `node scripts/smoke_f4_hub.mjs` → **59 checks, 0 failures**
- `node scripts/check_index_hardcoded_text.mjs` → OK
- `node scripts/smoke_static_i18n.mjs` → OK
- `node scripts/check_static_visa_result_cards.js` → OK
- `python3 scripts/check_visa_data_text_integrity.py` → PASS
- `node scripts/check_i18n.js` / `check_i18n_coverage.mjs` → OK (1031 keys match)
- `git diff --check` → clean. The F-4 validators are wired into
  `scripts/check_repo.sh` (step 9c).

## 14. Manual QA (automated stand-ins)
No browser/jsdom is available offline (the project is build-system-free), so
`smoke_f4_hub.mjs` exercises the real routing function and asserts render-input
completeness for: all 7 diagnostic scenarios; country preselect from
`미국/캐나다/일본/중국/호주 F-4`; every registry country rendering via overlay or safe
fallback; US-only specifics never surfacing for other countries; F-4 relevance of
all Phase-11 search terms; 90-day prominence; and no-legal-conclusion wording on
the >90-day path. A live click-through in a browser is still recommended before
release.

## 15. Known limitations
- Mission-page and HCCH facts were confirmed via search-index snippets (direct
  fetch 403). Re-verify pages directly for legal-grade certainty.
- US fee is intentionally generic (`needs_refresh`); the prior unverified
  "USD 45" figure was dropped rather than re-asserted.
- China mission page quoted figures (복수사증/체류기간) conflict with the national
  manual (체류기간 1회 최대 3년); the overlay surfaces the manual and flags the
  conflict instead of asserting the page figure.
- No live browser/a11y audit was run in this environment.

## 16. Remaining risks / official-review items
- Vietnam apostille in force 2026-09-11 → flip authentication after that date.
- Thailand / Malaysia apostille membership unverified → confirm on HCCH.
- Tier-2/3 countries need per-mission F-4 page discovery before overlays.

## 17. Recommended next PRs
1. Tier-2 overlay batch (MX, HK, MN, IN, KH, NL, IT, ES, CH …) once official F-4
   pages are confirmed.
2. Post-fetch re-verification once direct access to mofa/easylaw/hcch is
   available; promote snippet-confirmed items to higher confidence.
3. Optional `labelZh` completion for the full registry if zh-CN coverage of the
   F-4 hub is expanded.
4. A browser-based a11y + visual QA pass (focus order, bottom-sheet on mobile).
