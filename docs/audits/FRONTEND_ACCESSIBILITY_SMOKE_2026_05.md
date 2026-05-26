# FRONTEND_ACCESSIBILITY_SMOKE_2026_05

## Background

Agent Mode Batch 2 and Batch 2 Rerun attempted to continue the stay-status UI/source audit after PR #186 (`docs: normalize Agent Mode stay-status UI/source audit (2026-05)`). Both runs were blocked before F/G/H and previously untested statuses could be exercised because the deployed frontend at:

`https://lucanomics.github.io/Paradiso/`

returned visual-browser failures reported as `502 Bad Gateway` / `Connection refused` in the Chromium-based Agent Mode browser.

The blocker was specific to interactive visual browser loading. Text-only retrieval could read static HTML content, so the static document was reachable through at least one non-visual path, but the interactive UI surface could not be loaded and exercised. Because of that, no F/G/H, sub-code, button, modal, or AI behavior should be considered audited by those blocked runs.

## Deployment Architecture Summary

- The human-facing frontend is a static app served from repository-root HTML files, primarily `index.html` and `ai.html`.
- The backend is a separate FastAPI service in `backend/paradiso_backend.py`.
- Existing backend deployment notes identify Railway as the configured backend deployment provider via `backend/Procfile` and `backend/railway.json`.
- No GitHub Actions workflow in `.github/workflows/` deploys the frontend. The repository contains validation and source-monitoring workflows only.
- The GitHub Pages deployment therefore appears to serve the repository's static root assets directly or through repository settings outside the checked-in workflow files.

## Static Assets Required By The Frontend

Key root-relative-to-page assets used by the static frontend include:

- `assets/brand/paradiso-favicon-o.png`
- `assets/brand/paradiso-wordmark-brush-white.png`
- `assets/hero/clary-garcia-QHlGCk9I_lY-unsplash.jpg`
- `assets/hero/ji-seongkwang-CX7fI2LXJgo-unsplash.jpg`
- `assets/hero/ws-chae--jVX4mW1Uac-unsplash.jpg`
- `assets/hero/yeonhee-VWLhifg5VMA-unsplash.jpg`
- `visa_data.json`
- `data/jobcode_master.json`
- `data/agent_registry_2026-04-30.json`
- `data/designated_medical_institutions_2026_04_30.json`

The asset paths inspected are relative paths such as `assets/...`, `data/...`, `./visa_data.json`, and `ai.html`, which are compatible with a GitHub Pages project path like `/Paradiso/` when the page is loaded from `https://lucanomics.github.io/Paradiso/`.

## Backend And API Calls

Both `index.html` and `ai.html` define the same API base pattern:

```js
const DEFAULT_API_BASE = "https://web-production-14f9a.up.railway.app";
const API_BASE = (window.PARADISO_BACKEND_URL && window.PARADISO_BACKEND_URL.trim())
    || ((location.hostname === 'localhost' || location.hostname === '127.0.0.1' || location.protocol === 'file:') ? "" : DEFAULT_API_BASE);
```

Observed frontend calls:

- `GET ${API_BASE}/api/visas`
- `POST ${API_BASE}/api/ask`
- `POST ${API_BASE}/api/jobcodekeywords`
- Static fallback/data calls such as `./visa_data.json`, `data/jobcode_master.json`, `data/agent_registry_2026-04-30.json`, and `data/designated_medical_institutions_2026_04_30.json`

Backend routes registered in `backend/paradiso_backend.py` include:

- `GET /`
- `GET /health`
- `GET /api/visas`
- `POST /api/ask`
- `POST /api/jobcodekeywords`
- `POST /api/debug/law-grounding`

## Frontend Boot Safety Inspection

The inspected `index.html` boot path renders static search UI markup before data loading. On `DOMContentLoaded`, it calls `loadVisaData()`.

`index.html` data loading behavior:

- First attempts `${API_BASE}/api/visas` when an API base is present.
- Catches API failures.
- Falls back to `./visa_data.json`.
- Catches static JSON failures.
- Disables search and displays a user-facing data-load failure message only if both API and static JSON loading fail.

`ai.html` data loading behavior:

- First attempts `${API_BASE}/api/visas` when an API base is present.
- Catches API failures.
- Falls back to `./visa_data.json`.
- Catches static JSON failures.
- Continues to render the AI page shell and sets the status to ready after the best-effort data load path completes.

Auxiliary frontend datasets inspected in `index.html` also catch fetch failures:

- Registered agent finder displays its local error state if `data/agent_registry_2026-04-30.json` fails.
- Medical institution finder displays its local error state if `data/designated_medical_institutions_2026_04_30.json` fails.
- Job-code data loading reports a modal-scoped load failure rather than blocking initial page render.
- Detail-code resolver catches `visa_data.json` failures and logs a warning while returning an empty local resolver dataset.

Based on this inspection, failed backend/API calls should not block the initial static rendering of the search UI. They can block dynamic data-backed search results, AI responses, or auxiliary finder content if both the backend and the static fallback fail.

## Potential Failure Points

- GitHub Pages deployment misconfiguration or transient serving failure for `https://lucanomics.github.io/Paradiso/`.
- Agent Mode visual browser network path/proxy failure distinct from simple text retrieval.
- Backend outage at `https://web-production-14f9a.up.railway.app`, affecting API-backed data and AI flows.
- Missing or failed static fallback assets, especially `visa_data.json`.
- External font CDN availability for Pretendard. Font loading should not block app logic, but can affect visual rendering.
- Browser/runtime support for newer APIs used in the static page, such as `color-mix`, optional chaining, `CSS.escape`, `navigator.clipboard`, and `localStorage`. Most inspected usages are guarded or non-critical, but browser differences can affect specific interactions.
- Any GitHub Pages path-base change away from `/Paradiso/` or direct root could affect relative links if the deployment URL changes.

## What Changed

- Added this diagnostic note to preserve the Batch 2 / Batch 2 Rerun blocker and document the inspected frontend accessibility surface.
- Added `scripts/smoke_frontend_accessibility.sh`, a dependency-light curl smoke check for the deployed GitHub Pages URL and key static HTML markers.

No runtime frontend code was changed because inspection did not identify a clear uncaught fetch/runtime error that would block initial interactive UI rendering.

## What Was Not Changed

- No visa/legal/manual data was changed.
- No required-document lists were changed.
- `visa_data.json` was not changed.
- `backend/data/visas.json` was not changed.
- Manual-grounding JSON was not changed.
- AI grounding behavior was not changed.
- The UI was not redesigned.
- F/G/H audit completion is not claimed.
- This diagnostic does not treat the Batch 2 blocker as a data issue.

## Manual Smoke Checklist

Run from the repository root:

```bash
bash scripts/smoke_frontend_accessibility.sh
```

Manual browser checks after the smoke script passes:

1. Open `https://lucanomics.github.io/Paradiso/` in a normal browser.
2. Confirm the landing page renders without a gateway/proxy error.
3. Confirm the search input or search toggle is visible and focusable.
4. Search for a known common status such as `D-2` or `F-6`.
5. Confirm result cards render from static or API-backed data.
6. Open a result detail drawer or document modal.
7. Open `https://lucanomics.github.io/Paradiso/ai.html`.
8. Confirm the AI page shell renders even if the backend is unavailable.
9. If AI is tested, distinguish backend/API failures from static frontend load failures.
10. Only after the interactive visual browser can load the deployed frontend, rerun the Batch 2 interactive audit for F/G/H and previously untested statuses.
