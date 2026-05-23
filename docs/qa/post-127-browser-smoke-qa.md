# Post-127 Browser Smoke QA (PR #128)

- Date (UTC): 2026-05-23
- Target: `index.html`, `ai.html`
- Branch requested: `qa/browser-ui-smoke-post-127` (environment branch observed: `work`)

## Summary

Browser automation tooling was **not available** in this container (`playwright` and `selenium` missing), so full browser-driven PASS/FAIL execution could not be completed here.

Per instruction, matrix items are marked **NOT EXECUTED** (not faked as PASS), and manual QA steps are provided.

## Scope

- Verified post-127 string/code conditions in source for:
  - removal of AI modal “공식 결정” safety wording
  - grounding labels “출처 있음 / 미검증 / 기능 꺼짐”
  - `openHikoreaGuide` language sync (`hikoreaGuideState.lang = currentLanguage` for ko/en/zh/vi)
- Ran repository validation commands requested for PR #128.

## Browser/tooling environment

- OS/container: Codex execution container
- Local static server: `python3 -m http.server 8765`
- Browser automation:
  - Playwright: unavailable (`require('playwright')` failed)
  - Selenium: unavailable (Python module not installed)

## Desktop 1440 QA matrix

All items: **NOT EXECUTED** (tooling unavailable in container).

## Mobile 390 QA matrix

All items: **NOT EXECUTED** (tooling unavailable in container).

## Fixes made

- No runtime UI code changes.
- Added this final stabilization QA report document only.

## Validation results

- `node scripts/check_i18n.js` → PASS
- `python3 -m json.tool visa_data.json > /dev/null` → PASS
- `ALLOW_BACKEND_TEST_SKIP=1 bash scripts/check_repo.sh` → PASS with expected warnings:
  - backend dependency bootstrap blocked by package-index/proxy restrictions
  - backend tests and golden eval skipped accordingly
- `rg -n "[‘’“”]" index.html ai.html` → found smart quotes in i18n text (informational)
- Forbidden-claims grep run with provided pattern → no matches for the prohibited branding/legal-guarantee claims in target files

## Known limitations

- No automated browser engine available in this environment.
- Could not execute true UI interactions/console capture/screenshot capture via browser automation.

## Manual QA steps (exact)

1. Start server:
   - `python3 -m http.server 8765`
2. Open in desktop browser (1440):
   - `http://127.0.0.1:8765/index.html`
   - `http://127.0.0.1:8765/ai.html`
3. Open DevTools Console, keep “Preserve log” on.
4. Execute matrix sections 1–7 exactly as listed in PR #128 task.
5. Repeat all responsive checks using mobile emulation width `390px`.
6. Record each row as PASS/FAIL with screenshot + console snippet evidence.
7. If any regression appears, apply only tiny allowed fixes (overflow/z-index/data-action/aria/typo/smart-quote), re-run validations, and update this report.

## Recommended next steps

- Run the full matrix on a workstation with Playwright or a real browser available.
- Attach evidence artifacts (screenshots + console logs) and then convert matrix statuses from NOT EXECUTED to PASS/FAIL.
