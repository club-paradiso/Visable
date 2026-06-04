# Expanded Route Wizard + i18n Sweep (2026-05)

## 1. Purpose

Continue the route-wizard generalization and the i18n sweep started for
F-4/F-6/G-1, and **extend route-aware guidance to more route-complex statuses**:
F-2, D-10, H-2 (P0) plus E-7, D-4, F-1 (P1). The wizard maps each route to
**existing, source-referenced procedure variants** — no new scenario/document
data is invented. AI-modal and document-tab/procedure-stage chrome is fully
localized for the four main languages, and the provider-aware live AI quality
smoke is extended with the new route journeys.

No grounding semantics, manual sources, scenario data, disclaimers, or
verification flags were changed. No secrets were added, printed, or committed.

## 2. Remaining i18n gaps fixed

* AI modal description (`openAiModal`) routed through `tx('aiDescSpecial')` /
  `tx('aiDescGeneral')` (was ko/en-only → Korean in Chinese modes).
* AI empty/no-result/error states localized; new localized no-provider (503)
  notice `tx('aiNoProvider')`.
* Traditional Chinese AI-modal keys added (were missing → Korean fallback).
* Document-tab stage labels, section title, and missing-data notice localized
  (`documentTabLabels` / `documentSectionTitle` / `docTabMissingNotice`).

## 3. AI modal label localization

`aiDescSpecial`, `aiDescGeneral`, `aiEmptyInput`, `aiNoResult`, `aiError`,
`aiNoProvider`, plus the Traditional Chinese `aiActionLabels` / `aiModalTitle` /
`aiIntro` / `aiInputLabel` / `aiInputPlaceholder` are present for Korean,
English, Simplified Chinese, and Traditional Chinese. No AI-modal chrome remains
Korean-only in a supported full language.

## 4. Document-tab / procedure-stage label localization

`documentTabLabels` (Initial application (before entry) / Foreigner registration
/ Extension of stay), `documentSectionTitle`, and `docTabMissingNotice` are
localized for the four main languages; the tab render uses
`getDocumentTabLabel(cfg)`. Procedure-stage labels flow through the localized
`procedureLabels` array via `getProcedureLabelByKey()`, which returns a localized
fallback for unknown keys. Official Korean document item text is never
translated; the F-4 domestic residence report wording stays distinct from the
generic foreigner-registration label.

## 5. Route wizard architecture changes

The F-4-only array was replaced (in the preceding F-6/G-1 work) with a
data-driven `ROUTE_WIZARD_CONFIG` object keyed by status code. This PR adds six
more status entries to that same structure with no new one-off code. Each route
carries a localized label key, a localized description key, a procedure key to
highlight, and an optional `variantId`. `getRouteWizardConfig(v)` returns the
config for the record's status or `null`; `renderF4RouteChooser(v)` returns `''`
for unconfigured statuses; `selectF4Route()` activates the route's procedure tab,
de-emphasizes (never hides) the others, and — when a route maps to a source-backed
variant — selects that variant via the existing `selectProcedureVariant()`. The
reset/show-all control uses the unified `routeShowAll` label.

## 6. F-4 preservation / follow-through

F-4 keeps its five routes, labels, descriptions, procedure mapping, the labelled
selected-route banner, the distinct domestic-residence wording, and the
no-approval framing (B-2/C-3 → F-4 does not imply all short-stay entrants
qualify; H-2 → F-4 does not imply automatic approval). F-4 tests pass unchanged.

## 7. F-6 route options and behavior

Title "Which F-6 situation applies to you?"; 5 routes (spouse/marriage
maintained, child-raising, marriage breakdown, death/disappearance, extension)
mapped to existing F-6 variants. Cautious copy ("not automatically approved",
"not every breakdown case qualifies"). (Implemented in the preceding F-6/G-1
work; preserved here.)

## 8. G-1 route options and behavior

Title "Which G-1 reason applies to you?"; 6 routes (refugee, humanitarian,
litigation, medical, industrial accident/wage, extension) mapped to existing G-1
`statusChange` variants; the extension route (no G-1 extension variant) shows
explanation + official guidance only. Cautious copy ("does not guarantee
recognition", "is not guaranteed").

## 9. F-2 route options and behavior

Title "Which F-2 residence situation applies to you?". 4 routes:

1. Points-based talent (F-2-7) → `statusChange` (`f-2-7-point-based-talent-status-change`).
2. Tourism/leisure investment (F-2-8) → `statusChange` (`f-2-8-tourism-investment-status-change`).
3. Family of a national or permanent resident → `statusChange`
   (`f-2-permanent-resident-family-status-change`).
4. F-2 extension of stay → `extension` (explanation + official guidance).

All copy is cautious and confirms eligibility/documents with the competent
office. No new variants added.

## 10. D-10 route options and behavior

Title "Which D-10 job-seeking situation applies to you?". 4 routes:

1. Points-based job-seeking (D-10-1) → `statusChange` (`d-10-1-points-status-change`).
2. Tech start-up preparation (D-10-2) → `statusChange` (`d-10-2-tech-startup-status-change`).
3. High-tech internship (D-10-3) → `statusChange` (`d-10-3-high-tech-intern-status-change`).
4. D-10 extension of stay → `extension` (`d-10-1-points-extension`).

## 11. H-2 route options and behavior

Title "Which H-2 procedure are you looking for?". 4 routes:

1. Foreigner registration → `registration` (`h-2-existing-holder-registration`).
2. Employment-start / workplace-change report → `workplaceChange`
   (`h-2-employment-start-workplace-change-report`).
3. Change from H-2 to F-4 → `statusChange` (no H-2-side variant → explanation +
   official guidance; copy explicitly states it is **not automatically approved**).
4. H-2 extension of stay → `extension` (explanation + official guidance).

## 12. P1 route statuses implemented or skipped

**Implemented (clear existing variant data):**

* **E-7** — 3 routes: occupation/industry-code check (statusChange, explanation +
  code-tool caution), workplace change/addition (`e-7-registered-workplace-change`),
  extension.
* **D-4** — 4 routes: language training (`d-4-1-7-language-training-status-change`),
  graduate training (`d-4-2-graduate-training-status-change`), school student
  (`d-4-3-school-student-status-change`), extension.
* **F-1** — 4 routes: visiting/cohabitation (`f-1-13-status-change`),
  post-divorce affairs (`f-1-6-marriage-cleanup-status-change`), family of a
  recognized refugee (`f-1-16-refugee-family-status-change`), extension.

**Skipped (documented):**

* **D-2, C-3, C-4, F-5** — these records currently have **no procedure variants**
  in `visa_data.json`. A route wizard for them would be explanation-only chrome
  with no source-backed variant to bring forward; per the "if unsure, add
  explanatory route only or skip — do not invent documents" rule, they are
  skipped to avoid low-value chrome and any risk of implying structure that the
  data does not support. They can be added later if/when source-backed variants
  exist.

## 13. Checklist / deadline / AI integration

Route → variant selection still drives the existing scenario checklist, deadline
calculator, source panel, and selected-variant AI handoff. When a route has no
matching variant, the wizard shows the explanation + official-confirmation
guidance and does not render an empty checklist or invent documents. The AI
payload sends only `selected_procedure_key` / `selected_procedure_variant_id`
(safe identifiers); local checklist and reminder state are never sent.

## 14. Provider-aware live AI quality smoke behavior

`scripts/smoke_ai_live_quality.py` is safe by default: it reads only the
non-secret `/health` descriptor (provider booleans, public model id,
law-grounding mode), records a **skipped-live** status and exits 0 in no-provider
mode, and only performs answer-quality checks (against a small approval/guarantee
denylist; no wording overfit) when a provider is configured. Sample questions now
include the two new journeys — **D-10 → E-7** and **H-2 → F-4** — alongside the
H-1 seasonal course, F-4 domestic residence report, B-2 → F-4, F-6 divorce
extension, and G-1 medical treatment (the F-6/G-1/D-10 ones carry safe route/
variant context). `--require-live` opts into failing when no provider/backend is
available.

## 15. Railway provider-key context

* Provider keys are configured in Railway. This PR added/printed/committed no
  secrets and verified only through safe metadata.
* `OPENROUTER_MODEL` resolves to `qwen/qwen3-next-80b-a3b-instruct:free` by default
  (`backend/paradiso_backend.py`); `/health` exposes `providers` booleans, the
  public `model` id, `llm.configured`, `llm.groq_fallback_allowed`, and
  `law_grounding_mode` — never key values.
* `LAW_GROUNDING_MODE` defaults to `disabled`. The user reportedly updated
  Railway settings; **this could not be confirmed from the sandbox** because the
  deployed backend was unreachable (see below). Locally it reports
  `law_grounding_mode=disabled` and `groq_fallback`/provider as unconfigured.
* **Deployed smoke status:** the deployed backend
  `https://web-production-14f9a.up.railway.app` returned **HTTP 403 Forbidden**
  for `/health` and `/api/debug/law-grounding/preflight` from this sandbox
  (egress blocked). The harness degraded safely (reported the blocker, exit 0).
  To verify the live provider/model/law-grounding state and run the live smoke
  yourself (no secrets printed):

  ```bash
  # safe metadata only (provider booleans, model id, law mode):
  curl -s "https://web-production-14f9a.up.railway.app/health"
  curl -s "https://web-production-14f9a.up.railway.app/api/debug/law-grounding/preflight"
  # provider-aware live answer-quality smoke (7 route-relevant questions):
  BACKEND_URL="https://web-production-14f9a.up.railway.app" \
      python3 scripts/smoke_ai_live_quality.py
  # H-1 seasonal-course /api/ask:
  curl -s -X POST "https://web-production-14f9a.up.railway.app/api/ask" \
      -H 'Content-Type: application/json' \
      -d '{"question":"H-1 비자인데 한국 대학에서 계절학기를 수강할 수 있을까요?","consent":true,"lang":"ko","visa_data":{"code":"H-1"}}'
  ```

## 16. Localization coverage

All new route-wizard titles/intros/labels/descriptions, AI-modal strings, and
document-tab labels are provided for Korean, English, Simplified Chinese, and
Traditional Chinese (`node scripts/check_i18n.js` → 599/599). Partial languages
fall back to Korean and keep the partial-language notice. Official Korean
document names are not translated.

## 17. Tests added

* `backend/tests/test_expanded_route_wizard.py` — config includes
  F-4/F-6/G-1/F-2/D-10/H-2/E-7/D-4/F-1; F-2/D-10/H-2 titles + labels in four
  languages; P1 (E-7/D-4/F-1) titles/intros/labels in four languages; routes map
  to existing variants; H-2 → F-4 not-automatic copy; every new status has an
  extension route; wizard exposes no raw `requiredDocs`/`manualRefs`/`visa_data`/
  `JSON.stringify`; chips carry only safe identifiers.
* `backend/tests/test_i18n_sweep_route_wizard.py` — AI-modal/doc-tab i18n, F-6/G-1
  coverage, smoke-harness behavior, documentation command (carried from the
  preceding work; the unconfigured-status check updated since E-7 is now
  configured).
* `backend/tests/test_core_journey_ux_hardening.py` — F-4 tests on the
  generalized config.

## 18. Validation results

* `node scripts/check_i18n.js` → OK (599/599); inline JS validated with
  `node --check`.
* `python3 -m json.tool` on `visa_data.json`, `backend/data/visas.json`,
  `doc_master.json` → valid; `sync_visa_data.py --check`,
  `check_required_documents_coverage.py`, `validate_structured_requirements.py`
  → pass.
* `py_compile` + `--help` for `smoke_ai_variant_grounding.py`,
  `smoke_ai_all_status_safeguards.py`, `smoke_ai_live_quality.py`;
  `smoke_law_grounding.sh --help` → OK.
* `python3 -m unittest discover -s backend/tests` → **476 OK**.
* `bash scripts/check_repo.sh` → all regression + golden-eval passed.
* Local no-provider backend smoke (uvicorn @127.0.0.1:8000): variant grounding
  28/0, all-status 58 OK/0 fail, `smoke_ai_live_quality.py` 7/7 safe no-provider
  503 skip (exit 0).
* Deployed Railway smoke: **blocked (sandbox egress HTTP 403)** — exact user-run
  commands provided above.

## 19. Known limitations

* Live AI answer quality could not be exercised here (no local provider key; the
  deployed backend is unreachable from the sandbox). The harness is ready and
  exact deployed commands are documented.
* Live law-grounding mode / Groq-fallback state on Railway could not be confirmed
  from the sandbox (egress 403); verify via `/health` using the commands above.
* D-2, C-3, C-4, F-5 route wizards were skipped (no source-backed variants);
  documented above.
* Some deep utility-modal strings (job-code disclaimer, jurisdiction form
  internals) remain partly Korean and are tracked for a later sweep.

## 20. Safety note

Route explanations, AI guidance, law grounding, and scenario guidance are
preparation aids only and do not determine eligibility, approval, or final
required documents.
