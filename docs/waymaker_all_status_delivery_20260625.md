# Waymaker All-Status Procedure Navigator — Delivery Report

**Date:** 2026-06-25 · **Branch:** `waymaker-all-status-procedure-navigator-mobile-refactor` · **Not merged, not pushed.**

## 1. Architecture changes
Waymaker's **default surface is now a deterministic, official-source-grounded procedure navigator**, not an AI chatbot. The authoritative result is the existing backend **Procedure Packet** (`GET /api/procedure-packet`), rendered client-side; the LLM (`/api/ask`) is demoted to an optional, **secondary** "Ask about this packet" follow-up.

- **Reused, did not duplicate:** the backend `procedure_packet_builder`, `PACKET_TYPE_BY_PROCEDURE_KEY` enums, `SUPPORTED_PACKET_TYPES`, the source-lens levels, and `build_available_packets_for_status`. The frontend adapter **mirrors** the backend taxonomy (drift-guarded by a test) — no second visa/procedure/document taxonomy was introduced.
- **New self-contained frontend module** `assets/js/waymaker-navigator.js` (UMD; node-testable pure logic + browser UI controller) + `assets/css/waymaker-navigator.css` (mobile-first), mounted as the default surface of `ai.html`. The legacy chat is preserved but hidden behind an operator flag (`?legacyChat=1` / `localStorage.paradisoDevDiagnostics='1'`).
- **Bounded, additive backend change** to `procedure_packet_builder.py`: `coverageSummary{level,isLimited,hasDocuments}`, EN navigator-chrome labels (`SOURCE_LENS_LABELS_EN`, `sourceLens.overallLabelEn`, `finalAgencyNoteEn`, unknown-packet `titleEn`), and EN fields on the packet-selector summaries. **No legal/manual content was translated or invented.**
- **Default flow:** language → location → status (searchable, all 42 codes) → procedure → minimal situation questions → deterministic Action Packet (12 sections) → document checklist → HiKorea guidance → official-source coverage → optional AI follow-up.

## 2. Files changed
| File | Change |
|---|---|
| `assets/js/waymaker-navigator.js` | **new** — adapter, catalog, coverage, checklist, intake state machine, packet view, AI-context safety, analytics |
| `assets/css/waymaker-navigator.css` | **new** — mobile-first (360/390/430/768/desktop), ≥44px targets, sticky safe-area bar, archive_diary contrast, reduced-motion |
| `ai.html` | mount navigator as default; hide model-tier/quota/"AI 도우미" chrome; viewport `viewport-fit=cover` + pinch-zoom restored; AI follow-up forced to buffered (`stream:false`) gated path |
| `backend/services/procedure_packet_builder.py` | additive `coverageSummary` + EN labels (KO untouched) |
| `data/nationality_content.json` | homepage Waymaker copy → procedure-navigator framing ("내 절차 찾기 / Find my immigration procedure"); removed "AI 도우미"/"same engine" |
| `new-home.html` | locale-aware a11y labels (theme/brightness/close) so EN mode no longer exposes Korean labels |
| `scripts/check_waymaker_navigator.mjs` | **new** — 376 node checks (adapter parity, all-status, coverage, AI-context safety, i18n parity) |
| `scripts/check_waymaker_navigator_dom.mjs` | **new** — jsdom flow test (self-skips without jsdom) |
| `backend/tests/test_waymaker_navigator_contract.py` | **new** — coverageSummary/EN/no-fabrication + JS↔backend drift guard |
| `tests/e2e/waymaker-navigator.spec.mjs` | **new** — Playwright responsive matrix |
| `scripts/check_repo.sh` | new step `[9f]` runs the navigator + packet-builder + contract tests |
| `package.json`, `playwright.config.mjs`, `.gitignore` | jsdom devDep + `test:waymaker-navigator` alias; optional `PARADISO_PW_EXECUTABLE`; ignore test artifacts |

## 3. Inventory & matrix location
- Preflight inventory: **`docs/waymaker_all_status_preflight_20260625.md`**.
- Canonical status/procedure coverage matrix: **§2&3 of the preflight report** (all 42 statuses; 20 source_confirmed / 51 contextual / 59 limited packets; 36/42 have ≥1 contextual+ packet; every status yields a safe state).

## 4. Tests run & exact results
- `node scripts/check_waymaker_navigator.mjs` → **376/376 passed**
- `node scripts/check_waymaker_navigator_dom.mjs` (jsdom) → **32/32 passed**
- `python -m unittest backend.tests.test_procedure_packet_builder` → **36 OK** (incl. 5 FastAPI endpoint tests)
- `python -m unittest backend.tests.test_waymaker_navigator_contract` → **11 OK**
- `npx playwright test waymaker-navigator` → **25/25 passed** (5 tests × {360,390,430,768,1280})
- `backend/tests/test_paradiso_backend.py` → **251 OK** · `test_e7_workplace_change_law_grounding.py` → **26 OK**
- Golden eval (`evaluate_paradiso_ai_golden_questions.py`) → **All regression checks passed**
- `bash scripts/check_repo.sh` → **Success: repository validation passed** (i18n 1076 keys, route guides 127, visa-issuance 2846, F-4 80, subcode 223, branding clean, diff clean, + new `[9f]`)

## 5–10. Acceptance confirmations
- **Every canonical status has a safe procedure state** — verified for all 42 records (`test_every_status_has_a_safe_procedure_state`; 376-check sweep). None crash/blank.
- **`/api/ask` is not called before AI follow-up** — structurally (the navigator never calls it; the host's follow-up does) and verified in jsdom + Playwright.
- **D-2 extension deterministic packet works** — Playwright + jsdom drive D-2→extension to a full Action Packet with `stream`/`/api/ask` untouched.
- **F-6 ambiguous path asks clarification** — `needsSubStatusClarification('F-6', …) === true`; sub-status step rendered before a definitive packet.
- **Source-limited cases do not fabricate** — `test_all_status_coverage_limited_never_fabricates` (zero doc rows when limited, no raw diagnostics) + Playwright coverage-limited render.
- **Mobile checked at 360/390/430/768** (+desktop) — no horizontal overflow, ≥44px targets, readable in both themes. The e2e caught and we fixed two real CSS bugs (a 5px action-bar overflow; 40px small buttons).

## 11–15. Known limitations, deferred work, follow-ups
- **Packet body prose stays Korean** (document names, summaries) — these are official Korean administrative terms; only navigator chrome is EN. Full per-status EN packet prose is **deferred** (requires human-authored legal translation; out of safety scope).
- **HiKorea handoff** uses the official site + the packet's `channels.hikoreaReservation` + 1345; it does not deep-link a preselected service (HiKorea has no such URLs). Embedding `ParadisoReservationHelper`'s overlay into `ai.html` is a **follow-up**.
- **Streaming output-gate gap** (legacy chat `/api/ask` streaming bypasses post-gen gates) is mitigated for Waymaker (follow-up forces buffered); a broader backend streaming-gate fix is a **recommended follow-up PR**.
- **URL deep-link context** (`?visa_code=&selected_procedure_key=` from the index.html FAB) is not yet pre-seeded into the navigator intake — safe (starts fresh); a pre-seed option is a small **follow-up**.
- **Privacy-safe analytics** ships as a categorical-only no-op wrapper (`makeAnalytics`); backend wiring deferred per spec.

## Safety posture
No approval prediction, no application submission, no booking/login/payment automation, no personal identifiers requested/stored/logged/sent to the LLM (categorical selections only; checklist is local-only). Disclaimers preserved; the next action is never buried.
