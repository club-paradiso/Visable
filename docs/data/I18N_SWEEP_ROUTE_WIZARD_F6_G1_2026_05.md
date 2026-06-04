# i18n Sweep + Route Wizard Extension to F-6 / G-1 (2026-05)

## 1. Purpose

PRs #233–#248 expanded Paradiso with scenario variants, a guided scenario
selector, the selected-scenario checklist, deadline/calendar tools, an AI
source/law-grounding panel, an F-4 route wizard, and core-journey UX polish. Four
risks remained after #248:

1. Some deeper AI modal strings were Korean-only (esp. in Chinese modes).
2. Document-tab / procedure-stage labels were Korean-only in some areas.
3. The route wizard was F-4-only by design.
4. Live AI-answer quality was not exercised (the local environment had no
   provider key), even though Railway has provider keys configured.

This PR closes those gaps: it completes the visible i18n sweep, generalizes the
route wizard so it is reusable and extends it to **F-6** and **G-1**, and adds a
**provider-aware live AI quality smoke** harness that is safe by default and only
runs live checks when a provider is actually configured (e.g. deployed Railway).

No grounding semantics, manual sources, scenario data, disclaimers, or
verification flags were changed. No new scenario variants were added — the wizard
maps to existing source-referenced variants only.

## 2. Remaining i18n gaps fixed

* AI modal description (`openAiModal`) was a ko/en-only ternary → Chinese modes
  showed Korean. Now routed through `tx('aiDescSpecial')` / `tx('aiDescGeneral')`.
* AI empty-input / no-result / error states were hardcoded Korean → now
  `tx('aiEmptyInput')`, `tx('aiNoResult')`, `tx('aiError')`.
* A new localized **no-provider (503)** notice (`tx('aiNoProvider')`) replaces the
  generic error when the LLM provider is not configured.
* Traditional Chinese (`zhHant`) was missing the AI-modal keys entirely (it fell
  back to Korean). Added `aiModalTitle`, `aiIntro`, `aiInputLabel`,
  `aiInputPlaceholder`, `aiActionLabels`, `closeModal`, `docModalTitle`,
  `faqModalTitle`, `jobCodeTitle`, `jurisdictionTitle` for Traditional Chinese.
* Document-tab stage labels and the document section title were hardcoded Korean
  → now `documentTabLabels[]` / `documentSectionTitle`, and the missing-data
  notice is `docTabMissingNotice`.

## 3. AI modal label localization

`aiDescSpecial`, `aiDescGeneral`, `aiEmptyInput`, `aiNoResult`, `aiError`,
`aiNoProvider` added for Korean, English, Simplified Chinese, and Traditional
Chinese. The existing `aiActionLabels` array (the four quick-action buttons) and
`aiModalTitle`/`aiIntro`/`aiInputLabel`/`aiInputPlaceholder` are now present for
Traditional Chinese as well, so no AI-modal chrome remains Korean-only in a
supported full language.

## 4. Document-tab / procedure-stage label localization

* `documentTabLabels` (Initial application (before entry) / Foreigner
  registration / Extension of stay) added for the four main languages; the tab
  render now uses `getDocumentTabLabel(cfg)`.
* `documentSectionTitle` ("Required documents") replaces the hardcoded `구비서류`
  heading and aria-label.
* `docTabMissingNotice` localizes the "no structured document data" notice.
* Procedure-stage labels continue to flow through the localized `procedureLabels`
  array via `getProcedureLabelByKey()`, which returns a localized fallback for
  unknown keys.
* Official Korean **document item** text is never translated — only the stage
  *chrome* is localized. The F-4 domestic residence report wording stays distinct
  from the generic foreigner-registration label.

## 5. Route wizard architecture changes

The F-4-only `F4_ROUTE_CONFIG` array was replaced with a data-driven
`ROUTE_WIZARD_CONFIG` object keyed by status code. Each status has a localized
title/intro/aria key and a list of routes; each route carries a localized label
key, a localized description key, a procedure key to highlight, and an optional
`variantId` to bring a source-backed scenario variant forward.

* `getRouteWizardConfig(v)` returns the config for the record's status, or `null`.
* `renderF4RouteChooser(v)` (name kept for the call site) renders any configured
  status and returns `''` for unconfigured statuses, so the wizard appears for
  **F-4, F-6, G-1 only**.
* `selectF4Route()` now reads `data-label-key` / `data-desc-key` / `data-variant-id`
  off the chosen chip (instead of building keys from an index), activates the
  route's procedure tab, de-emphasizes (never hides) the others, and — when the
  route maps to a source-backed variant — selects that variant in the scenario
  selector via the existing `selectProcedureVariant()` model.
* The reset/show-all control uses a unified `routeShowAll` label
  ("전체 경로 보기" / "Show all routes" / "查看全部路径" / "查看全部路徑").

F-4 behavior is preserved: the same five F-4 routes, labels, descriptions, and
procedure mapping are retained.

## 6. F-6 route options and behavior

Title: "Which F-6 situation applies to you?" (localized in four languages).
Routes (mapped to existing, source-referenced F-6 variants where available):

1. Spouse of a Korean national / marriage maintained → `extension`
   (`f-6-1-marriage-maintenance-extension`).
2. Raising a child in Korea → `statusChange` (`f-6-2-child-rearing-status-change`).
3. Marriage breakdown, divorce, or separation → `statusChange`
   (`f-6-3-marriage-terminated-status-change`).
4. Death, disappearance, or other reasons not attributable to you → `extension`
   (`f-6-1-spouse-missing-extension`).
5. F-6 extension of stay → `extension` (general; shows all extension variants).

Copy is cautious: child-rearing "is not automatically approved"; "not every
breakdown case qualifies". No new variants were added.

## 7. G-1 route options and behavior

Title: "Which G-1 reason applies to you?" (localized in four languages).
Routes (mapped to existing G-1 `statusChange` variants where available):

1. Refugee application or refugee-related stay → `g-1-5-6-refugee-humanitarian-status-change`.
2. Humanitarian stay → `g-1-5-6-refugee-humanitarian-status-change`.
3. Litigation or rights-remedy procedure → `g-1-3-litigation-status-change`.
4. Medical treatment or health-related stay → `g-1-10-medical-patient-status-change`.
5. Industrial accident, unpaid wages, or other protected-stay reason →
   `g-1-1-industrial-accident-status-change`.
6. G-1 extension of stay → `extension` (G-1 has no extension variants, so this
   route shows the explanation + official-confirmation guidance only).

Copy is cautious: refugee recognition "is decided through a separate review, and
choosing this route does not guarantee recognition"; humanitarian stay "is not
guaranteed". No new variants were added.

## 8. F-4 preservation / follow-through

F-4 keeps its five routes, the labelled selected-route banner, procedure
highlighting, the distinct domestic-residence wording, and the no-approval
framing. The `test_core_journey_ux_hardening.py` F-4 tests were updated to match
the generalized config (same behavior, new mechanism) and still pass.

## 9. Checklist / deadline / AI integration

* Selecting a route → selecting a scenario variant still drives the existing
  checklist, deadline calculator, source panel, and selected-variant AI handoff.
* When a route maps to a source-backed variant, the wizard brings that variant
  forward; when a route has no matching variant (e.g. G-1 extension), it shows
  the explanation + official-confirmation guidance and does **not** render an
  empty checklist or invent documents.
* The AI payload still sends only `selected_procedure_key` /
  `selected_procedure_variant_id`. Local checklist and reminder state are never
  sent to the backend or AI.

## 10. Provider-aware live AI quality smoke behavior

`scripts/smoke_ai_live_quality.py` is **safe by default**:

* Reads the non-secret `/health` descriptor (provider booleans, public model id,
  law-grounding mode). It never reads or prints API keys.
* In no-provider mode, `/api/ask` returns 503; the harness records a
  **skipped-live** status, verifies the safe no-provider behavior, and exits 0
  (so CI stays green).
* When a provider is configured (deployed Railway), it checks each sample answer
  for obviously-unsupported approval/guarantee language (a small denylist; it
  does not overfit to LLM wording) and confirms metadata/source/law-grounding
  status is present.
* Reports backend URL, provider-configured boolean, model, law-grounding mode,
  whether the live check was skipped or executed, whether law grounding was
  attempted, and whether selected route/variant context was echoed.
* `--require-live` makes it fail when no provider is configured / backend is
  unreachable; off by default.

Sample questions exercised: H-1 seasonal course, F-4 domestic residence report,
B-2 → F-4 change, F-6 divorce extension (with F-6 route/variant context), and
G-1 medical treatment (with G-1 route/variant context).

## 11. Railway provider-key context

* **Provider keys are configured in Railway** (per the deployment context). This
  PR does not add, request, print, or commit any secrets.
* Verification was done only through safe preflight/debug metadata:
  `/health` exposes `providers` booleans, the public `model` id, and
  `law_grounding_mode`; `/api/debug/law-grounding/preflight` exposes the
  law-grounding mode and readiness booleans. No key values are ever exposed.
* `OPENROUTER_MODEL` resolves to `qwen/qwen3-next-80b-a3b-instruct:free` by default
  (`backend/paradiso_backend.py`), overridable per-deploy by the `OPENROUTER_MODEL`
  env var.
* `LAW_GROUNDING_MODE` defaults to `disabled` (safe-by-default). Live law
  grounding is therefore **configured but reported as not active** unless the
  deploy sets `LAW_GROUNDING_MODE=audit` or `enabled`. Locally it returns
  `law_grounding_status=disabled`.
* **Deployed live smoke status:** the discoverable Railway URL
  (`https://web-production-14f9a.up.railway.app`, from `index.html`
  `DEFAULT_API_BASE`) was **not reachable from this environment — the sandbox
  egress returned HTTP 403 Forbidden**. The harness degraded safely (reported the
  blocker, exit 0). To run the deployed live smoke yourself:

  ```bash
  BACKEND_URL="https://web-production-14f9a.up.railway.app" \
      python3 scripts/smoke_ai_live_quality.py
  # law-grounding preflight (no secrets printed):
  curl -s "https://web-production-14f9a.up.railway.app/api/debug/law-grounding/preflight"
  # H-1 seasonal-course /api/ask:
  curl -s -X POST "https://web-production-14f9a.up.railway.app/api/ask" \
      -H 'Content-Type: application/json' \
      -d '{"question":"H-1 비자인데 한국 대학에서 계절학기를 수강할 수 있을까요?","consent":true,"lang":"ko","visa_data":{"code":"H-1"}}'
  ```

## 12. Localization coverage

All new route-wizard, AI-modal, and document-tab UI labels are provided for
Korean, English, Simplified Chinese, and Traditional Chinese. Partial languages
fall back to Korean and continue to show the partial-language notice. Official
Korean document names are not translated. `node scripts/check_i18n.js` passes.

## 13. Tests added

* `backend/tests/test_i18n_sweep_route_wizard.py` — AI modal labels/descriptions/
  no-provider/error states in four languages; document-tab labels + helper;
  known/unknown procedure-key labels; domestic-residence distinctness; route
  wizard config includes F-4/F-6/G-1 and excludes unconfigured statuses; F-6 and
  G-1 titles/labels in four languages; F-4 preservation; unified show-all label;
  no-approval copy; routes map to existing variants; checklist/AI integration and
  payload safety; source/law-grounding labels; partial-language notice; smoke
  harness compiles / `--help` / no-provider-skip / never-prints-secrets;
  documentation includes the exact deployed-run command.
* `backend/tests/test_core_journey_ux_hardening.py` — two F-4 tests updated for
  the generalized config (same behavior).

## 14. Validation results

* `node scripts/check_i18n.js` → OK.
* `python3 -m json.tool` on `visa_data.json`, `backend/data/visas.json`,
  `doc_master.json` → valid.
* `sync_visa_data.py --check`, `check_required_documents_coverage.py`,
  `validate_structured_requirements.py` → pass.
* `py_compile` + `--help` for `smoke_ai_variant_grounding.py`,
  `smoke_ai_all_status_safeguards.py`, `smoke_ai_live_quality.py`;
  `smoke_law_grounding.sh --help` → OK.
* `python3 -m unittest discover -s backend/tests` → all pass.
* `bash scripts/check_repo.sh` → all regression + golden-eval passed.
* Local no-provider backend smoke (uvicorn @127.0.0.1:8000): variant grounding
  28/0, `--selected-variant-smoke` 28/0, all-status safeguards 58 OK/0 fail,
  `smoke_ai_live_quality.py` → 5 sample questions all safe no-provider 503 skip,
  exit 0. Inline JS syntax validated with `node --check`.
* Deployed Railway live smoke: **blocked (sandbox egress HTTP 403)** — exact
  user-run commands provided above.

## 15. Known limitations

* Live AI answer quality could not be exercised here (no local provider key; the
  deployed backend is unreachable from the sandbox). The harness is ready and the
  exact deployed commands are documented.
* The route wizard now covers F-4/F-6/G-1; other route-complex statuses can be
  added by config but are out of scope.
* Some deep utility-modal strings (job-code disclaimer text, jurisdiction form
  internals) remain partly Korean and are tracked for a later sweep.
* `LAW_GROUNDING_MODE` is disabled by default, so live law grounding stays
  "configured but not active" until a deploy enables audit/enabled mode.

## 16. Safety note

Route explanations, AI guidance, law grounding, and scenario guidance are
preparation aids only and do not determine eligibility, approval, or final
required documents.
