# Visable frontend rebuild — final report (2026-11-04)

Branch `claude/visable-frontend-rebuild-0289z4`, PR #758 (draft): https://github.com/club-paradiso/Visable/pull/758
Resume point and per-step evidence: `docs/rebuild/STATUS.md`. Decisions: `docs/rebuild/DECISIONS.md` (ADR-001 … ADR-013).
Base: `main` at 5082d9d (merge of PR #757). 58 commits on the branch.

Every number below was measured in this session with the command noted in STATUS.md; "verified" means the
command was run here and its output seen. Nothing in this report is a prediction.

## 1. Phase status

| Phase | Scope | Status | Evidence |
|---|---|---|---|
| 0 | Inventory, legacy-check map, data canon, golden Playwright suite + CI workflow | done | STATUS §Phase 0; `tests/golden/` 11 specs / 57 tests + 20 visual states × 2 viewports |
| 1 | Repo diet and data canon | done (with owner decisions 3, 4) | STATUS §Phase 1, ADR-003/006/007 |
| 2 | Vite multi-page build, URL parity source ↔ dist | done | ADR-008; `node scripts/check_url_parity.mjs` 0 mismatches at every step |
| 3 | index.html inline JavaScript → ES modules under `src/` behind `window.Visable` | done with documented residue | STATUS §Phase 3; 193 one-line stubs + state owners stay inline (ADR-009 addendum 6) |
| 4 | CSS: tokens file, inline styles, dead-theme audit, `!important` audit | done; component split and a broad `!important` sweep deferred (owner decision 6) | STATUS §Phase 4, ADR-011 |
| 5 | Other pages (ai.html, new-home.html, nationality hub) | done | STATUS §Phase 5, ADR-012 |
| 6 | Backend split with contract test, no Railway redeploy | routers done; helper/services split deferred | STATUS §Phase 6, ADR-013 |
| 7 | Retire covered legacy checks, README, final measurements, this report | done | this file; `docs/rebuild/phase0-legacy-checks.md` retire mapping |

## 2. Implemented / verified / not verified / blocked

**Implemented and verified (command run here, output seen; also on CI where noted)**
- Golden suite: 120 functional tests (114 pass, 6 skipped as BLOCKED: live AI/backend/provider keys), run after every step on the source tree and on `dist/`; CI job `golden-local` green on the last pushed commits.
- Visual baselines: 20 states × 2 viewports; every Phase 4/5 step compared 38–40/40 pixel-stable against baselines taken immediately before the step on the same Chromium (ADR-005/011).
- Legacy static checks: the 52-script loop (scripts in `check_repo.sh` plus the manual ones that slice frontend source) is green except two failures that fail identically at the merge-base (`check_preview_mvp.mjs`: PreView page references index.html/Visable; `check_doc_master_id_migration.py`: two Korean-string doc ids in D-8/F-1 `requiredDocs`) — pre-existing, untouched (CLAUDE.md: no data edits).
- Backend register: `python3 scripts/run_backend_tests.py` PASS 102 / KNOWN 0 / NEW 0 after Phase 6 (101 modules + the API contract snapshot test).
- API contract: OpenAPI document (67 paths, 37 schemas), ordered route table (74 routes), middleware and exception handlers identical before and after the router split (`backend/tests/test_api_contract_snapshot.py`).
- Build: `npm run typecheck`, `npm run build`, URL parity 0 mismatches at every step; `dist/` serves the same 196 referenced URLs with the same status as the source tree.
- CI on PR #758 at the last full run: `validate`, `golden-local`, `golden-visual`, `mobile-webkit-qa`, `mobile-render-qa`, `landing-restoration-e2e` green on the Phase 5/6 commits; `webkit-e2e` green after one re-run (see §6).

**Implemented, not verified here**
- Production behaviour of the rebuilt frontend on Vercel: the preview deployment builds and deploys ("Ready" on every push), but the `golden-deployment` job is skipped until owner decision 1 (SSO-protected preview), and this environment cannot open the preview URL.
- Backend on Railway: nothing was deployed (deploy branch is `main`); the facade import, routes and the full register were verified locally only. The live `/health` could not be fetched from this environment (network policy); the latest Railway deploy log shows the config-as-code start command `uvicorn paradiso_backend:app` and 200s on `/health`, `/api/ask`.
- WebKit: the repo's `webkit-e2e` job runs in CI only; two WebKit-only intermittent failures were seen and re-run (see §6). WebKit cannot run in this sandbox.

**Blocked (owner action, listed in §5)**
- Golden suite against the preview deployment (decision 1); committing visual baselines (3); Railway index build so the 41.6 MB sqlite can leave git (4); the dead deadline calculator (5); a design-led CSS pass (6); the stale Railway dashboard start command (7).

## 3. Before / after (merge-base 5082d9d → HEAD)

| Metric | Before | After |
|---|---|---|
| index.html lines | 26,908 | 2,431 |
| index.html inline `<script>` lines (blocks without `src`) | 10,786 | 746 (4 first-paint scripts + state owners/data tables + 193 one-line stubs + 1 bootstrap line) |
| index.html inline `<style>` lines | 14,472 | 25 (first-paint skeleton `#civic-critical`) |
| index.html static `style=""` attributes | 21 | 7 (all JavaScript state hooks) |
| `src/` ES modules | 0 | 26 files / 10,956 lines (`src/main.js` → `window.Visable`) |
| ai.html lines (inline JS) | 3,356 (3,026) | 352 (18, two first-paint restores) |
| new-home.html lines (inline JS) | 1,229 (1,003) | 242 (15, two first-paint restores) |
| nationality-interview-hub.html lines (inline `<style>`) | 429 (213) | 217 (0) |
| `assets/js/pages/` classic page scripts | 0 | 5 files / 3,996 lines |
| `!important` (index.html + assets/css, same grep) | 3,308 | 3,280 (27 removed with 12 exact-duplicate rules; rest audited, deferred) |
| Design tokens | inside the inline `<style>` | `assets/css/tokens.css` (215 custom properties, DESIGN.md mapping in the header) |
| `backend/paradiso_backend.py` lines | 9,196 | 7,612 |
| `@app` route handlers in the facade | 28 | 0 (12 router modules, 1,829 lines) |
| Backend test modules | 101 | 102 (+ API contract snapshot) |
| Browser golden tests | 0 | 57 `test()` calls / 11 specs (120 runs across 2 viewports) + 40 visual shots |
| Legacy checks retired | — | 1 script deleted + 2 assertions removed, each mapped to the golden test that covers it |

## 4. Decisions (ADR index; full text in DECISIONS.md)
ADR-001 single harness branch · ADR-002 pre-installed Chromium 1243 · ADR-003 duplicate-JSON canon · ADR-004 preview verification in CI · ADR-005 visual baselines on the CI runner · ADR-006 `.vercelignore` explicit paths · ADR-007 generated data stays committed, CI proves currency · ADR-008 Vite multi-page, staged · ADR-009 (+6 addenda) module extraction mechanics, `window.Visable`, stubs, corpus for slicers · ADR-010 plain ES modules with JSDoc, not `.ts` yet · ADR-011 (+3 addenda) verbatim CSS extraction, local per-step baselines, sound-only `!important` removals · ADR-012 other pages → external classic scripts (parse-time order) · ADR-013 route handlers → `backend/routers/`, facade keeps state/helpers, contract snapshot.

## 5. Owner decisions needed (recommendation first)
1. **Preview access for CI** — create the Vercel *Protection Bypass for Automation* secret, add it as `VERCEL_AUTOMATION_BYPASS_SECRET`, set `GOLDEN_PREVIEW_ENABLED=true`; the `golden-deployment` job then runs the suite against every preview. Recommendation: do it (read-only, automation-scoped).
2. **Branching / merge** — one long-lived branch was used (ADR-001). Recommendation: review PR #758 as a whole (each phase is a contiguous run of commits, each with its verification in the message); or ask for it to be split by phase range into stacked PRs.
3. **Visual baselines** — generated on the CI runner and uploaded as an artifact. Recommendation: download `golden-visual` artifacts once, commit `tests/golden/__screenshots__/`, so the visual job starts comparing instead of generating.
4. **Manual search index on Railway** — 41.6 MB sqlite in git. Recommendation: add `python3 scripts/build_manual_search_index.py --out backend/data/manual_search_index.sqlite3` to the Railway build command, then drop the file.
5. **Dead deadline calculator** — `src/features/deadline.js` + 24 i18n keys + CSS are unreachable. Recommendation: delete, or mount on the legacy card with a golden test. Not a behaviour-preserving move, so not done.
6. **Design-led CSS pass** — 3,280 `!important`, CSS split by origin not component. Recommendation: after (3), add per-skin baselines (stamp/chrome/neon) and remove `!important` file by file with a visual diff per file.
7. **Railway dashboard start command** — names the legacy stub; config-as-code (`backend/railway.json`) overrides it today. Recommendation: align the dashboard field with `uvicorn paradiso_backend:app --host 0.0.0.0 --port $PORT`.

## 6. Risks and next steps
- **Monkeypatch coupling in the backend**: the router split keeps 20+ test-patched names on the facade by design; moving helpers into services later needs a patch-point review per helper cluster (ADR-013). Next step: start with the provider clients (`_call_openrouter`, `_openrouter_complete_with_candidates`) under their own patch surface.
- **Stubs and state owners in index.html**: 193 one-line stubs remain because `assets/js` scripts, e2e specs and legacy slicers call bare names. Next step: give those callers an import or a stable `window.Visable.*` path, then delete stubs cluster by cluster (each guarded by the golden suite).
- **Classic page scripts**: ai.html / new-home.html scripts are external but not modules (ADR-012) because they run at parse time. Converting them is a boot-order change that needs its own tests.
- **WebKit intermittents**: `webkit-e2e` failed twice on this PR on single WebKit-only tests (`landing-boot.spec.mjs:191`, `search-first-home.spec.mjs:226`), both passing on re-run or on neighbouring commits, and the second one is the same failure `main`'s merge commits for #745/#746/#755 record. Not fixed here (cannot run WebKit in this environment); worth a dedicated look.
- **`experiments` workflow**: red on this PR's Phase 6 commit (98 tests, `KeyError: 'stay_manual_2026_10_19_pdf'` in the experiments package's manual ledger) and red on `main` since the manual edition promotion of 2026-11-02 (run 171 on main at bd03d59 and PR #756 fail the same way). The rebuild changed no manual, catalog or experiments file; the job ran because its path filter includes `backend/paradiso_backend.py`. Not this PR's; noted on the PR.
- **Pre-existing check failures**: `check_preview_mvp.mjs` and `check_doc_master_id_migration.py` fail at the merge-base; both are data/content questions outside a structural rebuild (CLAUDE.md), logged for manual review.
- **Preview-only verification gap**: until decision 1, the golden suite never runs against a Vercel deployment; `dist/` is verified locally only.
