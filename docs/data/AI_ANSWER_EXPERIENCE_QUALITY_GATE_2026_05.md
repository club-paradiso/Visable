# AI Answer Experience Quality Gate (2026-05)

A focused quality pass on **how Paradiso AI answers**, not on which model or
provider serves the answer. It introduces a general answer-quality contract for
`/api/ask`, makes the prompt produce readable modern-LLM-style answers, keeps
source state honest (especially for related comparison statuses), and adds
deterministic tests + smoke quality signals.

Suggested branch: `fix/ai-answer-quality-readability`.
This is **not** a provider PR, **not** a route-wizard PR, **not** docs-only.

---

## 1. Purpose

Improve Paradiso AI's general answer quality and readability for normal
visa/status questions. Answers should be direct, readable, practical,
source-aware, not robotic, not overconfident, not a wall of warnings, and not a
long generic memo. The user must never be confused about what is official, what
is inferred, and what must be checked.

---

## 2. User-observed bad answer

Question:

> Can I take summer semester course in Korean universities even though I have a
> H-1 visa?

The answer was too generic, too long, and unpleasant to read, with
source-state inconsistencies:

* the source panel said the law source was unavailable, yet the answer still
  gave broad legal reasoning as if grounded;
* related D-2 / D-4 materials looked like direct source grounding;
* a mixed-language artifact appeared (e.g. `sojourn资格`);
* the same warnings were repeated several times;
* it did not feel like a helpful modern LLM response.

---

## 3. Why this is a general problem, not only an H-1 issue

The root cause was structural, not specific to H-1:

* the ungrounded prompt **forced a rigid six-section template** for every
  question, which produces long generic memos even for simple questions;
* there was **no contract** linking the grounding state to the answer shape, so
  a "law source unavailable" state could still yield confident legal reasoning;
* related comparison statuses were not modeled as distinct from source
  grounding, so they leaked into the source panel as if they answered the
  question;
* the answer-language instruction only handled ko/en and carried **no
  mixed-language guardrail**.

Fixing those at the contract/prompt level improves every visa/status answer,
with the H-1 study question as a golden regression case.

---

## 4. Answer quality modes

`backend/services/answer_quality.py` defines five modes, derived
deterministically from grounding state:

| Mode | Meaning | Confidence |
| --- | --- | --- |
| `source_confirmed` | Manual / source-confirmed requirement supports a practical answer. | high |
| `source_assisted` | Manual or law grounding gives useful context; official confirmation still needed. | moderate |
| `source_limited` | Related/partial info exists but direct source support is incomplete. | low |
| `source_unavailable` | Manual/law grounding is unavailable or insufficient. | low |
| `generic_advisory` | General AI fallback only. | none |

Non-secret metadata exposed on `/api/ask` (and on the no-provider 503 `detail`):
`answer_quality_mode`, `source_confidence_level`, `requires_official_confirmation`,
`official_confirmation_questions`, `related_statuses_not_sources`,
`grounded_answer_limited`, `answer_style_version`, `question_type_detected`.

A substantive question (activity/status-change/documents/deadline) with no
source is framed as `source_unavailable`, never as casual `generic_advisory`.

---

## 5. General answer contract

The prompt now asks for a flexible structure (NOT a fixed six-section template):

1. Lead with the direct, practical answer in the first one or two sentences.
2. Briefly explain why — the key rule or risk, in plain language.
3. Say what this means for the user / what would change the answer.
4. Give a concrete next step or the exact questions to ask.
5. End with **one** short source/verification note.

Short answers for simple questions; compact structure for medium ones; depth
only for genuinely complex scenarios. Tone: calm, concise, not robotic, not
legalistic unless necessary. Each caution is stated once.

---

## 6. Source-aware answer behavior

* **Strong source** → clear answer, cite/explain source status, steps if data
  supports it.
* **Manual present but activity-scope/law risk remains** → answer cautiously;
  separate confirmed manual facts from interpretation.
* **Manual absent, law grounding used** → say manual-specific guidance was not
  found; use legal context only as background; do not invent documents; provide
  official-confirmation questions.
* **Law grounding unavailable** → do not produce broad legal reasoning as if
  grounded; give a limited practical answer; say the source gap prevents a
  definitive answer; provide a short "ask 1345/HiKorea this exact question" set.
* **Generic fallback only** → short, marked as general reference, recommend
  official confirmation, no long speculative scenario trees.

---

## 7. Question-type templates

`classify_question_type()` maps a question to one of:

* `activity_on_status` — "Can I do X on status Y?" → direct cautious answer,
  main risk (permitted scope / outside-status activity / status change /
  reporting duty), what changes the answer, exact questions to ask, source note.
* `documents_needed` — "What documents do I need?" → show source-confirmed list
  grouped by purpose with conditional markers; never invent; otherwise say so
  and give the official route.
* `status_change` — "Can I change from A to B?" → no eligibility promise;
  route/risk; ask current status, entry route, duration, purpose; confirmation
  steps.
* `deadline_report` — confirmed deadline only if source-backed; label common
  rules; explain the triggering event; suggest a reminder; confirmation note.
* `special_situation` — restate, identify 2-4 key variables, avoid a final
  answer when facts are missing, give next questions + checklist steps.

---

## 8. H-1 study / activity-scope regression behavior

For the golden H-1 study question, the contract deterministically yields:

* `answer_quality_mode = source_limited`, `question_type = activity_on_status`;
* `related_statuses_not_sources = ["D-2", "D-4"]` (comparison statuses only);
* `grounding_used = false`, `grounding_sources = []` — D-2 / D-4 are never
  presented as direct manual source grounding;
* the exact seven official-confirmation questions (credit-bearing?
  degree-related? weeks/hours? main purpose? also working under H-1?
  D-2/D-4 required? outside-status activity or status change?);
* no invented document checklist, no final approval/prohibition;
* prompt directives forbid mixed-language artifacts like `资格`.

The expected first line is essentially: *Paradiso cannot confirm from currently
verified sources that an H-1 holder may take this university summer course.*

---

## 9. Source chip semantics

The frontend source panel (`renderGroundingSourcePanel` in `index.html`) now:

* shows a compact **Answer basis** row reflecting `answer_quality_mode`;
* renders **Related status to verify** as distinct chips (blue `state-related`
  styling), separate from source grounding, with a note that they are
  comparison statuses, not a source that answers the question;
* never labels related statuses as `Manual: D-2` / `Manual: D-4`;
* keeps direct manual grounding, manual-to-law fallback, public data, and
  needs-review scenario context as separate, honestly-labeled rows.

Labels (ko / en / zh / zhHant):

* Related status to verify — `함께 확인할 관련 체류자격` / `Related status to verify`
  / `需一并确认的相关居留资格` / `需一併確認的相關居留資格`.

---

## 10. Terminology guardrails

* English mode: no Chinese legal fragments (`资格`, `签证`, `滞留`, …); no hybrid
  terms like `sojourn资格`. Official Korean terms allowed in parentheses.
* Korean mode: plain accurate Korean; official terms kept; avoid government-
  notice tone unless quoting.
* Chinese modes: Simplified/Traditional used consistently; Hangul allowed only
  inside parentheses as an official-term reference.

Canonical English helper translations injected in English mode: 체류자격 = sojourn
status; 체류자격외활동 = activities outside the scope of status; 체류자격 변경 = change of
sojourn status; 국내거소신고 = domestic residence report; 활동범위 = permitted scope of
activities; 관광취업 = working holiday / H-1.

`scan_mixed_language_artifacts()` is the deterministic guard used by tests and
the smoke harness.

---

## 11. Warning de-duplication

* One primary caution lives in the answer body (prompt: "state each caution
  once").
* The source panel carries technical/source status; the answer-basis row
  summarizes state instead of repeating the long disclaimer.
* The footer disclosure remains but does not duplicate the same limitation
  phrase.
* The smoke harness reports a `warning_repetition_count` per live answer.

---

## 12. Frontend readability changes

* Compact **Answer basis** row at the top of the source panel.
* **Related status** chips visually distinct from grounding (blue pill chips).
* Technical law-grounding warnings stay collapsed in a `<details>` block.
* The advisory fallback row is only added when there is no other signal, so the
  panel is less dense.

No site-wide redesign — changes are scoped to the AI answer source panel and its
i18n keys.

---

## 13. Tests added

* `backend/tests/test_answer_quality_contract.py` — unit tests for language
  instructions, question-type classification, related-status detection, mode
  classification, prompt directives, the mixed-language guard, and prompt
  integration (29 tests).
* `backend/tests/test_paradiso_backend.py::AnswerQualityGoldenSuiteTests` — the
  Part J golden case list (H-1 ko/en, F-4 report, B-2→F-4, F-6 divorce, G-1
  medical, D-2 extension, E-7 workplace, D-2 part-time, F-6 documents) plus
  cross-cutting invariants (12 tests).
* `backend/tests/test_paradiso_backend.py::GoldenEvalSuiteTests` — extended with
  H-1 contract metadata, D-2 source-confirmed, and metadata-always-present
  regression checks.
* `scripts/check_i18n.js` — the eight new answer-quality i18n keys added to
  `REQUIRED_UI_KEYS` (enforced across ko/en/zh/zhHant).

---

## 14. Validation results

All green locally:

* `python3 -m json.tool` for `visa_data.json`, `backend/data/visas.json`,
  `doc_master.json` — OK.
* `python3 scripts/sync_visa_data.py --check` — matches.
* `python3 scripts/check_required_documents_coverage.py` — PASS.
* `python3 scripts/validate_structured_requirements.py …structured_requirements_2026_05.json` — valid.
* `python3 -m py_compile scripts/smoke_ai_live_quality.py` + `--help` — OK.
* `node scripts/check_i18n.js` — OK (42 required UI keys across ko/en/zh/zhHant).
* `python3 -m pytest backend/tests -q` — 586 passed, 66 subtests.
* `python3 -m pytest backend/tests/test_scenario_procedure_variants.py -q` — 87 passed.
* `python3 -m pytest backend/tests/test_paradiso_backend.py::GoldenEvalSuiteTests -q` — 20 passed.
* `bash scripts/check_repo.sh` — all regression checks passed.
* No-provider local smoke (`BACKEND_URL=http://127.0.0.1:8000 python3
  scripts/smoke_ai_live_quality.py`) — all questions report the expected
  contract metadata; H-1 ko/en report `source_limited` + `["D-2","D-4"]`.

Deployed Railway live smoke: to exercise live answer wording, run against the
deployed backend (provider keys live there, not locally):

```
BACKEND_URL="https://web-production-14f9a.up.railway.app" python3 scripts/smoke_ai_live_quality.py
```

---

## 15. Known limitations

* Related-status detection is rule-based and currently covers the study/H-1
  comparison case (D-2 / D-4); other comparison sets can be added as needed.
* The mixed-language guard is a conservative artifact check, not a full
  linguistic validator.
* Live answer wording still depends on the model; the smoke harness reports
  quality signals as warnings and never fails CI on LLM wording.
* `answer_quality_mode` is derived from grounding state + question type, not
  from the final answer text; it describes the *basis*, not a content audit.

---

## 16. Safety note

Paradiso cannot determine final eligibility, permission, or required documents.
Users must confirm case-specific outcomes with 1345, HiKorea, or the competent
immigration office.
