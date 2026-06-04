# Grounding readiness, language fallback, and deadline source-status (2026-05)

Branch: `feat/grounding-readiness-user-transparency`
PR: `feat: harden grounding readiness and user transparency`

## 1. Purpose

A practical follow-up to PR #246 that materially improves production readiness
and user-facing transparency for: law-grounding readiness, H-1 / activity-scope
AI behavior, partial-language fallback transparency, deadline-calculator
source-status safety, model-configuration clarity, and deployed-operation
readiness. This is not an audit/smoke/docs-only PR — it ships backend, frontend,
test, script, and docs changes.

## 2. Actual implementation changes made

**Backend**
- `backend/services/law_grounding.py`: new `law_grounding_preflight()` (non-secret
  readiness report; no external call); study-intent pattern extended with
  `수업` / `강의` / `강좌` / `class` / `lecture` so "수업을 들을 수 있나요" triggers.
- `backend/paradiso_backend.py`: new `GET /api/debug/law-grounding/preflight`;
  `POST /api/debug/law-grounding` now embeds a `preflight` block (empty-body 400
  contract preserved; GET preflight covers the no-question case).

**Frontend (index.html)**
- Source panel: a single normalized **Law-grounding status** row driven by
  `law_grounding_status` (not_attempted/disabled/unavailable/used) with new
  localized labels; only `used` reads as verified.
- Partial-language transparency: `LANGUAGE_SUPPORT` map + `languageSupportLevel()`;
  the language menu shows a `Partial` badge on non-full languages and a
  non-blocking notice when a partial language is active.
- Deadline calculator: each computed date now carries a **source-status badge**
  (common-rule preparation date / custom reminder); ICS gains a cautious
  `DESCRIPTION` and the Google Calendar link a cautious `details=`.
- i18n: 10 new keys added to all four main packs (ko/en/zh/zhHant).

**Tests**
- `backend/tests/test_law_grounding.py`: H-1/activity-scope regression class +
  preflight unit tests.
- `backend/tests/test_paradiso_backend.py`: preflight endpoint tests + seasonal-course
  metadata coverage.
- `backend/tests/test_grounding_readiness_transparency.py` (new): law-status panel,
  partial-language notice, deadline source-status, F-4 follow-through, i18n parity.
- `scripts/check_deadline_helpers.js` (new): functional checks for the date/ICS/GCal helpers.

**Scripts / config**
- `scripts/smoke_law_grounding.sh`: rewritten with `--help`, mode + preflight
  reporting, five sample questions, and a secret-free JSON field reader.
- `backend/README.md`: documents the preflight endpoint + production law env vars.

## 3. Law grounding readiness improvements

`law_grounding_preflight()` reports, with **no secrets and no external call**:
`mode`, `external_calls` (disabled/audit_only/enabled), `law_api_key_configured`
(bool), `law_api_endpoint_configured` (bool), `ready_for_external_calls` (bool),
`sample_would_trigger`, `sample_intent_reasons`, `sample_law_search_query`, and
warning markers: `LAW_GROUNDING_DISABLED`, `LAW_GROUNDING_AUDIT_ONLY`,
`LAW_API_KEY_MISSING`, `LAW_API_ENDPOINT_MISSING`. Exposed via
`GET /api/debug/law-grounding/preflight` and embedded in the POST debug response.
It is useful even when external calls are disabled (the default).

## 4. `/api/ask` law-grounding metadata states

`/api/ask` continues to return (from PR #246, compatible) `law_grounding_used`,
`law_grounding_attempted`, `law_grounding_warnings`, `citation_verification`, plus
the normalized `law_grounding_status` ∈ {`not_attempted`, `disabled`,
`unavailable`, `used`}, `law_grounding_intent_reasons`, and `law_search_query`.
The 503 no-provider path returns the same metadata. No raw API bodies or secrets
are ever returned, and legal verification is never claimed when mode is disabled
or the external API is unavailable.

## 5. H-1 / activity-scope regression coverage

Deterministic regressions (no live calls) for all four required questions:
`H-1 비자인데 한국 대학에서 계절학기를 수강할 수 있을까요?`,
`H-1으로 한국에서 수업을 들을 수 있나요?`,
`Can I take a university class in Korea on H-1?`,
`Can I work or study with this status?` — each triggers grounding intent
(study/course/activity-scope + H-1/working-holiday) and, disabled-by-default,
reports `law_grounding_status="disabled"` with intent reasons and the statutory
query (anchors: `출입국관리법`, `시행령`, `활동범위`, `체류자격외활동`, `관광취업`,
`H-1`, `유학`, `수강`, `계절학기`). No permission/prohibition is invented.

## 6. Law smoke script behavior

`scripts/smoke_law_grounding.sh`:
- `--help` documents usage; `BACKEND_URL` selects the target.
- Calls `/health`, the GET preflight, the POST debug for five sample questions
  (H-1 seasonal course, activity outside status, foreigner registration,
  G-1/refugee, re-entry/travel), and `/api/ask`.
- Prints backend URL, resolved mode, preflight readiness booleans, per-sample
  trigger, and the `/api/ask` law status. Prints **no secrets**.
- Works in disabled mode (verifies non-crash) and audit/enabled mode if env is
  present. CI never depends on a live external law API.

## 7. Partial language-pack notice behavior

`LANGUAGE_SUPPORT = { ko, en, zh, zhHant } = full`; every other selectable
language resolves to `partial`. When a partial language is active, the language
menu appends a non-blocking notice that some text may appear in Korean and that
official document names stay in Korean; partial languages also get a `Partial`
badge. Full languages show neither. Official Korean document-name helpers are
untouched. Partial languages are not removed and not claimed to be complete.

## 8. Site-wide i18n consistency improvements

`node scripts/check_i18n.js` passes (ko/en key parity, en Hangul-free). The 10
new keys are present in all four main packs; tests assert the law-status labels,
partial-language notice, F-4 route labels, deadline labels, and HiKorea caution
remain localized across ko/en/zh/zhHant. No official document data was translated.

## 9. Deadline calculator source-status hardening

Each computed date is tagged with a source-status badge: the entry+90
registration estimate and the extension reminders are **common-rule preparation
dates** (`공통 규칙 기반 준비 참고일`), and user reminders are **custom reminders**.
The 90-day estimate is never presented as an official deadline (its caution says
so explicitly). ICS `DESCRIPTION` and Google Calendar `details=` carry cautious
wording, not just the summary. The calculator remains ephemeral — no
`localStorage`, and nothing is sent to the backend or AI.

## 10. Model configuration status

Model resolution was hardened in PR #246 and is confirmed here by tests:
`_resolve_llm_config()` defaults `OPENROUTER_MODEL` to the approved
`qwen/qwen3-next-80b-a3b-instruct:free`, honors an env override, and returns provider
`none` (safe 503, no secret leak) when no key is set. Gemma remains an explicit
OpenRouter fallback candidate. `ALLOW_GROQ_FALLBACK` gates Groq when OpenRouter is absent. `/health` reports
provider/model (public ids only). No code change was needed; coverage is proven
by `ModelConfigResolutionTests` and the env vars are documented below.

## 11. F-4 route-aware UI follow-through

F-4 route-aware guidance (PR #246) still works after the i18n/source-panel
changes: route labels remain localized in all four languages, the domestic
residence report stays distinct from generic foreigner registration, no route is
auto-selected (generic F-4 doesn't force a route), and route selection implies no
eligibility/approval. Guarded by `F4RouteFollowThroughTests`.

## 12. Required env vars for production

| Variable | Purpose |
| --- | --- |
| `OPENROUTER_API_KEY` | Enables `/api/ask` via OpenRouter (preferred). |
| `OPENROUTER_MODEL` | Defaults to `qwen/qwen3-next-80b-a3b-instruct:free`; Gemma remains a fallback candidate; override if catalog changes. |
| `ALLOW_GROQ_FALLBACK` | Allows Groq only when explicitly enabled; `false` hard-requires OpenRouter/Qwen-first routing. |
| `LAW_GROUNDING_MODE` | `disabled` (default) / `audit` / `enabled`. |
| `LAW_API_KEY` | Required for any external law call (audit/enabled). |
| `LAW_API_BASE_URL` | Law API base URL (audit/enabled). |
| `LAW_API_SEARCH_PATH` | Law search path; with the base URL it makes the endpoint "configured". |
| `LAW_API_ARTICLE_PATH` | Optional article-lookup path. |

Never commit secrets; set these only in the deploy environment (e.g. Railway).

## 13. Tests added

- `H1ActivityScopeRegressionTests`, `LawGroundingPreflightTests` (test_law_grounding.py).
- `LawGroundingPreflightEndpointTests` + seasonal-course metadata test (test_paradiso_backend.py).
- `test_grounding_readiness_transparency.py`: 26 deterministic frontend tests.
- `scripts/check_deadline_helpers.js`: 16 functional JS checks.

## 14. Validation results

- `node scripts/check_i18n.js` → OK (484 keys in ko/en).
- `node scripts/check_deadline_helpers.js` → OK (16 functional checks).
- `node --check` on the inline main script → OK.
- `python3 -m pytest backend/tests -q` → all pass.
- JSON validators, `sync_visa_data.py --check`, coverage, structured-requirements,
  smoke `--help`, and `bash scripts/check_repo.sh` → see PR body. No data files changed.
- Local no-provider smokes: variant 28/28, all-status 58/0, `smoke_law_grounding.sh`
  reports preflight + per-sample triggers + status with no secrets.

## 15. Known limitations

- Live law-API grounding is still unverified end-to-end (network-blocked); it
  stays disabled-by-default and must be enabled deliberately. The preflight now
  makes the deployed configuration state inspectable without secrets.
- Partial language packs (ja, vi, …) still fall back to Korean for non-new
  surfaces; this PR adds transparency, not full translation.
- The 90-day registration figure is a common-rule preparation aid, not a
  per-status confirmed deadline.
- The route wizard remains F-4-specific (broad multi-status support is deferred).

## 16. Safety note

> Law grounding, deadline calculations, route explanations, and checklists are
> preparation aids only and do not replace official confirmation by HiKorea,
> 1345, or the competent immigration office.
