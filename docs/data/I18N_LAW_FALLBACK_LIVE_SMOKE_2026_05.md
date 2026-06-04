# I18N + Law-Grounding Fallback + Provider-Aware Live Smoke (2026-05)

Hardening pass focused on production readiness and correctness, not new feature
breadth. Covers: English-mode Korean UI leaks, a manual-to-law grounding
fallback policy, explicit Groq fallback control, and provider-aware deployed
live smoke against the Railway backend.

Branch: `claude/hopeful-clarke-SeMC0` (suggested name `fix/i18n-law-fallback-live-smoke`).
Backend under test: `https://web-production-14f9a.up.railway.app`.

---

## 1. Purpose

The recently expanded surfaces (route wizard, i18n, selected-scenario handling,
checklist/deadline tools, law-grounding transparency) shipped a few rough
edges. This pass:

1. removes English-mode Korean UI chrome on tx()-driven surfaces;
2. adds a manual-to-law grounding **fallback** so legal/activity-scope questions
   with no manual document grounding still get statutory *context* (never an
   invented checklist);
3. makes Groq fallback explicit and **strict-by-default** (OpenRouter/Qwen-first routing);
4. adds provider-aware deployed live smoke + reproducible commands;
5. adds deterministic tests and this documentation.

---

## 2. English-mode Korean UI leaks fixed

All fixes route through the existing `UI_TRANSLATIONS` / `tx()` architecture
(no new i18n framework). New keys are added for **ko / en / zh / zhHant**.

| Surface | Before | After |
| --- | --- | --- |
| Document modal procedure-stage titles (`openDocModal`) | `currentLanguage === 'en' ? … : '신규 발급/신규 신청 구비서류'` (leaked Korean in **zh/zhHant**) | `tx('docModalTitleNew' \| 'docModalTitleExt' \| 'docModalTitleChange' \| 'docModalTitleSub' \| 'docModalTitleSubGeneric')`, `tx('docStageReference')`, `tx('docModalTitleChangeNote')` |
| Jurisdiction modal placeholders + error + result message | hard-coded `'시/도 선택'`, `'시/군/구 선택'`, `'관할 관서 정보가 누락되었습니다.'`, Korean result paragraph (leaked Korean in **en/zh/zhHant**) | `tx('jurSidoPlaceholder')`, `tx('jurSigunguPlaceholder')`, `tx('jurMissingInfo')`, `tx('jurResultMsg', { office })` |
| Source panel (zhHant) | `sourceStatusTitle` / `manualActionLabels` missing → fell back to Korean in Traditional Chinese | backfilled in the `zhHant` pack |
| Source panel manual-to-law fallback row | n/a | new `manualToLawFallbackLabel` / `manualToLawFallbackChecked` / `manualToLawFallbackNote` in all four packs |

A companion i18n leak guard (`scripts/check_i18n.js`) now verifies a curated
list of **required UI-chrome keys** across `ko/en/zh/zhHant` (present, non-empty,
and free of Korean Hangul outside `ko` unless allowlisted). The pre-existing
`ko`↔`en` full parity and "no Hangul in `en`" checks are retained.

The official document/procedure-stage label helper (`getProcedureLabelByKey`)
already resolves through `txAt('procedureLabels', …)`, so known procedure keys
(`visaIssuance`, `statusChange`, `extension`, `registration`) return localized
labels. The F-4 **domestic residence report** wording stays distinct from the
generic foreigner-registration document-tab label.

---

## 3. Intentionally Korean source / manual text policy

The sweep deliberately did **not** translate, and the leak guard **allowlists**,
text that must remain Korean to match official sources:

- official Korean **document names** and **subcode names** (data records);
- **statute / enforcement-decree / enforcement-rule** names (e.g. 출입국관리법,
  시행령, 시행규칙) and article references (제n조);
- **visa/status Korean names** and manual excerpts;
- **official institution names** (HiKorea, 1345, 출입국·외국인관서);
- copy that is explicitly *about* preserving Korean
  (`scenarioOfficialLabelsKoNote`, `officialDocumentNamesKoNote`,
  `partialLanguageNotice`).

The `${sub.name}` value inside `docModalTitleSub` is an official subcode name and
remains Korean; only the surrounding chrome ("additional documents") is
translated. The partial-language fallback notice remains intact.

---

## 4. Manual-to-law fallback policy

`/api/ask` now distinguishes **manual-grounded** answers from **manual-absent**
answers and exposes the decision in non-secret metadata:

| Field | Meaning |
| --- | --- |
| `manual_grounding_status` | `present` when deterministic manual grounding **or** source-confirmed structured requirements were available; otherwise `absent`. |
| `law_grounding_attempted` | `true` when a legal/activity-scope intent matched and `LAW_GROUNDING_MODE` is `audit`/`enabled`. |
| `manual_to_law_fallback_used` | `true` when manual grounding was **absent** for a legal/activity-scope question **and** law grounding was attempted (audit/enabled). |
| `manual_to_law_fallback_reason` | `manual_grounding_absent_law_intent` (attempted), or `manual_grounding_absent_law_intent_grounding_disabled` (warranted but `LAW_GROUNDING_MODE=disabled`). |

When the fallback is used, the prompt instructs the model to state that
manual-specific document guidance was **not found**, to explain only legal
basis / activity scope / reporting duties / deadlines / definitions in general
terms, to **never invent a required-document checklist**, and to point the user
to HiKorea / 1345 / the competent office. Official Korean legal/admin terms are
preserved; English/Chinese renderings are non-authoritative UI helpers.

The frontend source panel renders a distinct, cautious row
(`gp-row-law-fallback`, `state-partial`) using `manualToLawFallbackLabel` /
`manualToLawFallbackChecked` / `manualToLawFallbackNote`. It is visually
separate from source-confirmed manual grounding (`state-source-supported`) and
from needs-review scenario context (`state-needs-review`), and never reads as a
final official decision.

---

## 5. Source hierarchy

1. **Official manual / HiKorea / immigration-office official guidance** —
   authoritative for required documents, fees, deadlines, and operational steps.
2. **Korean statutes, enforcement decrees, enforcement rules, attached
   tables/forms** — legal basis and definitions (audit-mode law grounding).
3. **Law-grounding explanatory context** — supplemental framing only.
4. **Generic advisory fallback** — with explicit official-confirmation warning.

Law grounding never overrides (1). The manual-to-law fallback only reaches for
(2)/(3) when (1) is absent for a legal/activity-scope question.

---

## 6. What law grounding may and may not be used for

**May** be used for: legal basis; activity scope; activities outside status;
permission/reporting duties; deadlines; definitions; eligibility-risk framing;
status-change or extension legal framing.

**May not** be used for: inventing required-document checklists, fees, article
numbers, or deadlines; claiming final eligibility, approval, or definitive
document requirements; replacing manual/HiKorea/office guidance.

---

## 7. H-1 seasonal-course fallback behavior

Question: `H-1 비자인데 한국 대학에서 계절학기를 수강할 수 있을까요?` /
`Can I take a university class in Korea on H-1?`

- Intent reasons include `유학/수강/계절학기` and `관광취업/워킹홀리데이/H-1`.
- No manual document grounding exists for this question → `manual_grounding_status: absent`.
- `LAW_GROUNDING_MODE=audit` → `law_grounding_attempted: true`,
  `manual_to_law_fallback_used: true`,
  `manual_to_law_fallback_reason: manual_grounding_absent_law_intent`.
- `LAW_GROUNDING_MODE=disabled` → `law_grounding_status: disabled`,
  `manual_to_law_fallback_used: false`,
  reason `manual_grounding_absent_law_intent_grounding_disabled`.
- No document checklist is produced from law grounding.

---

## 8. F-4 domestic residence report terminology behavior

- The F-4 route-wizard label preserves the official Korean term **국내거소신고**
  with an English helper ("F-4 domestic residence report"), kept distinct from
  the generic foreigner-registration label (외국인등록 / "Foreigner registration").
- Law-grounding intent now also recognizes 거소신고 / 국내거소신고 / "domestic
  residence report" under the registration/reporting-duty reason, so a
  manual-absent F-4 거소신고 question triggers the manual-to-law fallback in
  audit mode.

---

## 9. Deployed Railway health status observed

Per the task brief, the deployed `/health` after the Railway env update reported:
backend `status: ok`; OpenRouter configured; model `qwen/qwen3-next-80b-a3b-instruct:free`;
provider `openrouter`; `law_api` true; `law_grounding_mode: audit`;
`groq_fallback_allowed: true`.

After this PR's code change, with OpenRouter still configured on Railway, the
resolved provider/model is unchanged (OpenRouter always takes precedence), and
`/health` now reports `groq_fallback_allowed: false` unless
`ALLOW_GROQ_FALLBACK=true` is explicitly set — surfacing
`llm.warnings: ["GROQ_FALLBACK_ENABLED"]` when it is.

---

## 10. Deployed live smoke attempted — result / blocker

**Attempted from the CI/sandbox environment and BLOCKED by network policy.**

```
$ curl -sS https://web-production-14f9a.up.railway.app/health
Host not in allowlist

$ BACKEND_URL="https://web-production-14f9a.up.railway.app" \
    python3 scripts/smoke_ai_live_quality.py
  reachable : False
  blocker   : backend /health not reachable at https://web-production-14f9a.up.railway.app
  SKIPPED: backend unreachable.   # exit 0 (safe-by-default)
```

The sandbox egress allowlist does not include the Railway host, so the deployed
backend cannot be reached from here. The smoke harness records this as a
non-fatal skip (exit 0) rather than a failure. A local, no-provider audit-mode
run of the same harness passed and exercised the full metadata path (see §15).

---

## 11. Exact user-run smoke commands (run these from a networked machine)

```bash
# 1) Health (provider, model, groq fallback, law mode)
curl -sS https://web-production-14f9a.up.railway.app/health | python3 -m json.tool

# 2) Law-grounding debug (no secrets; preflight + context)
curl -sS -X POST https://web-production-14f9a.up.railway.app/api/debug/law-grounding \
  -H "Content-Type: application/json" \
  -d '{"question":"H-1 비자인데 한국 대학에서 계절학기를 수강할 수 있을까요?"}' | python3 -m json.tool

# 3) H-1 seasonal-course /api/ask (Korean)
curl -sS -X POST https://web-production-14f9a.up.railway.app/api/ask \
  -H "Content-Type: application/json" \
  -d '{"question":"H-1 비자인데 한국 대학에서 계절학기를 수강할 수 있을까요?","visa_code":"H-1","lang":"ko"}' | python3 -m json.tool

# 4) H-1 university class /api/ask (English)
curl -sS -X POST https://web-production-14f9a.up.railway.app/api/ask \
  -H "Content-Type: application/json" \
  -d '{"question":"Can I take a university class in Korea on H-1?","visa_code":"H-1","lang":"en"}' | python3 -m json.tool

# 5) B-2 -> F-4 change framing
curl -sS -X POST https://web-production-14f9a.up.railway.app/api/ask \
  -H "Content-Type: application/json" \
  -d '{"question":"B-2로 들어와서 F-4로 바꿀 수 있나요?","visa_code":"F-4","lang":"ko"}' | python3 -m json.tool

# 6) F-6 divorce extension framing
curl -sS -X POST https://web-production-14f9a.up.railway.app/api/ask \
  -H "Content-Type: application/json" \
  -d '{"question":"F-6인데 이혼 후에도 체류기간 연장이 가능한가요?","visa_code":"F-6","lang":"ko"}' | python3 -m json.tool

# 7) G-1 medical-purpose framing
curl -sS -X POST https://web-production-14f9a.up.railway.app/api/ask \
  -H "Content-Type: application/json" \
  -d '{"question":"G-1으로 치료 목적 체류를 하려면 어떤 절차를 봐야 하나요?","visa_code":"G-1","lang":"ko"}' | python3 -m json.tool

# 8) Full provider-aware harness against the deployed backend
BACKEND_URL="https://web-production-14f9a.up.railway.app" \
  python3 scripts/smoke_ai_live_quality.py --json
```

Expected: no secrets in any response; OpenRouter/Qwen-first routing confirmed on `/health`;
law grounding reported as `audit`; H-1 activity-scope questions attempt law
grounding (or expose why not); answers avoid invented approval/prohibition and
do not guarantee eligibility; metadata/source/law-grounding status present.

---

## 12. Groq fallback control behavior

- Controlled by the existing `ALLOW_GROQ_FALLBACK` env var (we did **not** invent
  a new name). Its **code default is now `false`** (strict OpenRouter/Qwen Next).
- Precedence is unchanged: OpenRouter is used whenever `OPENROUTER_API_KEY` is
  set; Groq is reached only when OpenRouter is unset **and**
  `ALLOW_GROQ_FALLBACK=true`. There is no silent runtime switch from a failing
  OpenRouter call to Groq — an OpenRouter failure returns 502, and a fully
  unconfigured provider returns a safe 503 (`no_llm_provider_configured`) with
  metadata.
- `/health` reflects the resolved setting (`llm.groq_fallback_allowed`) and adds
  `llm.warnings` markers: `GROQ_FALLBACK_ENABLED` when armed, plus
  `GROQ_FALLBACK_ACTIVE` when Groq is actually the resolved provider.
- **Migration note:** a deployment that ran Groq-only and relied on the previous
  default (`true`) must now set `ALLOW_GROQ_FALLBACK=true` explicitly.
  Deployments that configure `OPENROUTER_API_KEY` (the intended production setup,
  including Railway) are unaffected.

---

## 13. Required / recommended Railway env vars

| Variable | Recommended value | Notes |
| --- | --- | --- |
| `OPENROUTER_API_KEY` | (secret) | Required for live answers; intended production provider. |
| `OPENROUTER_MODEL` | `qwen/qwen3-next-80b-a3b-instruct:free` | Also the code default; Gemma remains a fallback candidate. |
| `ALLOW_GROQ_FALLBACK` | `false` | Strict OpenRouter/Qwen-first routing. Leave unset to inherit the strict default; set `true` only for an intentional Groq-only deployment. |
| `LAW_GROUNDING_MODE` | `audit` | Enables law-grounding intent + audit-mode external calls. |
| `LAW_API_KEY` | (secret) | Needed for real law-API calls in audit/enabled mode. |
| `LAW_API_BASE_URL` | (endpoint) | Law-API base URL (audit/enabled). |
| `LAW_API_SEARCH_PATH` | (path) | Law-API search path. |
| `LAW_API_ARTICLE_PATH` | (path) | Law-API article path. |

Non-secret assignments (set the secret values in the Railway dashboard, not here):

```
OPENROUTER_MODEL=qwen/qwen3-next-80b-a3b-instruct:free
ALLOW_GROQ_FALLBACK=false
LAW_GROUNDING_MODE=audit
```

Do **not** paste secrets into chat or commit them. Configure
`OPENROUTER_API_KEY` / `LAW_API_KEY` and the law endpoint vars as Railway
Project Variables. The model id is a public catalog identifier, not a secret.

---

## 14. Tests added

`backend/tests/test_i18n_law_fallback_live_smoke.py` (new), covering:

- i18n leak guard (`check_i18n.js`) catches an injected Korean leak in a required
  key and allows intentional official Korean source text;
- manual-to-law fallback metadata present + correct keys exist in all four packs;
- AI modal / doc-stage / jurisdiction / source-panel labels translated in en/zh/zhHant;
- manual-absent + audit → fallback used + law attempted (Korean + English H-1);
- manual-absent + disabled → safe disabled status, fallback not "used";
- manual-present (D-2 extension) → no over-trigger;
- law fallback never adds document-checklist items;
- Groq fallback default false; disabled → Groq not used; enabled → fallback
  explicit; no-provider → safe 503, no secret leak; `/health` reports the
  resolved fallback setting + warnings;
- provider-aware smoke supports deployed URL / no-provider skip and never prints
  API keys.

Existing suites still pass (route wizard, scenario, checklist, deadline, source,
AI payload, law-grounding metadata).

---

## 15. Validation results

Run locally in this environment (deployed Railway egress blocked — see §10):

- `node scripts/check_i18n.js` → OK (632 en / 632 ko / 522 zh / 352 zhHant; 29
  required UI keys verified across ko/en/zh/zhHant).
- `python3 scripts/smoke_ai_live_quality.py --help` → OK.
- Local audit-mode backend smoke (no provider) → exit 0; `groq_fallback_allowed:
  false`, `law_grounding_mode: audit`, `manual->law fallback hit: True`; H-1 and
  F-4 거소신고 questions show `manual=absent law=unavailable m2l=True`; live
  answer recorded as **skipped** (not passed), no-provider 503 safe.
- `python3 -m pytest backend/tests -q` → all pass.
- JSON validators (`visa_data.json`, `backend/data/visas.json`, `doc_master.json`)
  → valid.

---

## 16. Known limitations

- The deployed Railway live-answer smoke could not run from this sandbox
  (egress allowlist). Use the §11 commands from a networked machine.
- Audit-mode law grounding still depends on `LAW_API_KEY` + endpoint vars; with
  them unset, law grounding reports `unavailable` (intent + query are still
  exposed honestly).
- Several long-form **landing-page** keys remain untranslated in `zh`/`zhHant`
  (pre-existing, out of scope here). They fall back to Korean and are **not** in
  the required-key guard list. The local Korean-only reminder/deadline widget is
  outside the `tx()` system and was intentionally not converted in this pass.
- Local live-answer checks are recorded as **skipped**, not passed, when no
  provider key is present.

---

## 17. Safety note

Manual guidance, law grounding, AI answers, route explanations, deadline
calculations, and checklists are preparation aids only and do not determine
eligibility, approval, or final required documents. Always confirm with HiKorea,
1345, or the competent immigration office.
