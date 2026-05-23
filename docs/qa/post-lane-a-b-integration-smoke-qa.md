# Post Lane A/B integration smoke QA (PR #129 + PR #130)

- Date (UTC): 2026-05-23
- Branch: `qa/post-lane-a-b-smoke`
- Scope: UI QA/stabilization only (no backend/data updates)

## Summary

This pass focused on validating that the Lane A landing restoration (PR #129) and Lane B AI visa payload behavior (PR #130) remain intact, and that no safety-copy regressions were introduced.

Result: **No blocking regressions found by static + script QA.**

## Browser/manual QA matrix status

> Note: This environment does not provide an interactive browser session, so visual and network-panel checks are documented as **pending manual verification**.

### 1) Landing / brand restoration

- [x] `#brandHero` exists in `index.html`.
- [x] `#brandFeature` exists in `index.html`.
- [x] DIASPORA → PARADISO narrative strings are present in landing copy.
- [x] source/trust themed section structure remains present.
- [x] footer CTA content remains present.
- [x] forbidden product-branding strings check passes (`Paradiso 39`, `v38`, `v39`).
- [ ] Visual rendering confirmation in real browser (pending).

### 2) Mobile 390px

- [ ] Horizontal overflow check at 390px (pending manual browser QA).
- [ ] Hero/gateway card readability at 390px (pending manual browser QA).
- [ ] Restored brand/anagram/source/footer readability (pending manual browser QA).
- [ ] Section overlap check (pending manual browser QA).

### 3) Search / drawer / HiKorea flow

- [x] Relevant action hooks remain in place in `index.html` (`open-doc-modal`, `open-ai-modal`, HiKorea CTA wiring patterns retained).
- [ ] End-to-end interaction checks (palette/search/results/drawer/modal/Esc/backdrop/HiKorea open) pending manual browser QA.

### 4) `ai.html` payload behavior (D-2 / E-7 / fallback)

- [x] Local visa data load path remains active (`./visa_data.json`).
- [x] `/api/ask` request still sends `visa_data: visaPayload` in JSON body.
- [x] Local matching fallback paths retained for no-match and no-local-data conditions.
- [x] Example chips and textarea/send button wiring remains present.
- [ ] Network-panel payload inspection for live D-2/E-7 prompts pending manual browser QA.

### 5) Safety copy

- [x] Forbidden string scan passes for `index.html` and `ai.html`.

## Commands run

- `node scripts/check_i18n.js` → pass.
- `python3 -m json.tool visa_data.json > /dev/null` → pass.
- `ALLOW_BACKEND_TEST_SKIP=1 bash scripts/check_repo.sh` → pass with expected backend dependency bootstrap warnings in restricted package-index conditions.
- `rg -n "[‘’“”]" index.html ai.html` → no smart-quote regressions requiring patch.
- `rg -n "Paradiso 39|v39|v38|legally verified|official decision|guaranteed|approved|government-certified|production-ready law grounding|verified official decision|검증 완료|공식 결정|승인 보장" index.html ai.html` → no forbidden string matches.

## Fixes made

- No production behavior change applied.
- Added this QA record only.

## AI payload verification notes

Based on source inspection, `ai.html` still constructs local visa payload candidates and includes them as `visa_data` in the `/api/ask` body. Manual browser network inspection is still recommended to confirm exact runtime payload for:

- `D-2 연장 서류`
- `E-7 근무처 변경`

## Remaining issues / follow-up

1. Run full manual browser smoke (desktop + 390px mobile viewport) and capture screenshots.
2. Confirm live network payloads for D-2/E-7 prompts in DevTools.
3. Re-run backend tests in an environment with package index access (current run used skip-safe path).

## Recommended next step

Execute a short human QA pass in a real browser (desktop + iPhone 12/390px equivalent), then update this note with pass/fail outcomes and any tiny CSS/action-hook patch if a concrete regression is observed.
