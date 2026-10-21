# Deterministic status / subcode / procedure classification: baseline audit

Mission 001 "Waymaker Genesis". Audit date: 2026-10-19. Target: `origin/main` worktree
`/Users/seonjaekim/dev/Visable-genesis` at commit `0713370`. I read the code and ran it offline.
I edited nothing in the worktree. The knowledge store was forced to `:memory:`, and every run used
`env -i` with no API keys set.

Evidence tags: [CODE path:line], [TEST … (ran: pass/fail)], [LIVE … ], [DOC …]. Status: VERIFIED
means I checked the primary code, OBSERVED means I ran it, INFERRED means it is my reasoning.

Scratch scripts are in `/private/tmp/claude-501/-Users-seonjaekim-Downloads/041beae0-a4bd-4695-9a73-27a290ffa1c7/scratchpad/sc_work/`:
`run_py_baseline.py`, `run_js_baseline.mjs`, `probe_py.py`, `run_evals.py`, plus the raw outputs
`py_out.txt`, `js_out.txt` and `golden_out.txt`.

---

## 1. Summary

* **Two separate deterministic stacks exist, and they disagree.**
  * **Python (`/api/ask` and `/api/search/unified`).** It uses older code detectors and an
    11-value `task_type` enum. It never reads a subcode from free text, by design.
  * **JS (`status-guidance.js` + `search-router.js`).** The search page and the Waymaker quick
    answer use it. It reads exact subcodes from text, including the `*-T`, `-4R`, `-2K` and `-7S`
    variants. It uses a 16-procedure taxonomy that includes visa issuance, and it reports
    parent inheritance explicitly with `inherited` and `displayCode`.
  * [CODE backend/paradiso_backend.py:3843-3888] [CODE assets/js/status-guidance.js:165,194-292] VERIFIED.
* **The Python text detector discards every subcode.**
  * `_detect_visa_codes` returns `(None, None)` for "D-2-1 …", "E-7-4 …", "G-1-5 …" and similar.
    Its negative lookahead rejects the parent code whenever `-digit` follows it.
  * For "D-10-T …" it returns `D-10`.
  * `knowledge.understanding.understand()` then fills in the parent code from a second regex and
    leaves `subcode=None`.
  * [LIVE probe_py.py, 2026-10-19] OBSERVED.
* **This is a silent subcode→parent mapping.**
  * `KnowledgePlatform.plan("E-7-4 체류기간 연장 서류")` with no payload returns status E-7,
    subcode None, `VERIFIED_WITH_CONDITIONS`, and the **E-7 parent checklist (10 required items)**.
  * The same query with payload `E-7-4` returns `NO_DIRECT_SOURCE`.
  * D-4-2K behaves the same way: the D-4 parent checklist has 9 items.
  * The seed eval case `e7.extension.e7_4.never_inherits_parent` only passes because it supplies
    the payload.
  * `/api/ask`'s own `_select_grounding` returns `None` for these free-text queries, so the two
    Python paths disagree with each other.
  * [LIVE KnowledgePlatform.plan + _select_grounding, 2026-10-19] OBSERVED.
* **The Python code detector is not deterministic across processes.**
  * It iterates over a `frozenset` of code strings, sorted only by length. Python randomises
    string hashing per process, so for two codes of the same length the winner depends on
    `PYTHONHASHSEED`.
  * "F-6 배우자인데 E-9로 변경하고 싶어요" returned `F-6` for seeds 0, 2, 3, 5, 6, 7 and 8, and
    `E-9` for seeds 1, 4 and 9.
  * No tracked file pins `PYTHONHASHSEED`.
  * [CODE backend/paradiso_backend.py:3881] [LIVE PYTHONHASHSEED=0..9] OBSERVED.
* **English false positives exist in every code regex.** [corrected by verifier: not every one.
  `immigration_tools._STATUS_CODE_RE` requires a hyphen and returned no code for either sentence,
  and `pb._detect_visa_codes` is not fooled by "a 2nd" (it returned None). Affected: "a 3" in
  `_detect_visa_codes`, `legal_analysis`, `unified_search` and JS; "a 2nd" in `legal_analysis`,
  `unified_search` and JS. LIVE re-run 2026-10-19.]
  * "Can I get a 3 month extension?" produces `A-3`. In JS it resolves to a definitive A-3
    extension answer. [corrected by verifier: `nextStep` is `resolved`, target A-3, confidence
    HIGH, and the quick answer is `mode=answer`, confidence HIGH, 2 required documents. The
    rendered resolver HTML does, however, carry the notice "A-3-MONTH is not a code found in the
    September 2026 sources". So the answer is definite, but the page is not entirely silent.]
  * "I am a 2nd year student" produces `A-2`.
  * " to" and " E" get glued on as subcodes: "D-10 to" becomes `D-10-TO`, and
    "D-10 E-7" becomes `D-10-E`, which drops E-7.
  * [LIVE probe, 2026-10-19] OBSERVED.
* **An offline eval runner already exists and passes.**
  * `EvalService.run()` (knowledge/evals.py:267) passed 69/69: 19 seed cases + 50 golden cases.
  * `scripts/evaluate_paradiso_ai_golden_questions.py` passed 50/50.
  * The golden set's `visa_code`/`visa_sub_code` labels are fed to the detector **as the payload**
    (scripts/evaluate_paradiso_ai_golden_questions.py:94-101), so they do not test detection from
    text. Only `expected_task_type` is a real text-derived label. [corrected by verifier: mostly
    true, but 3 of the 15 no-payload items (`gq_d2_extension_no_payload_01`,
    `gq_e7_extension_ko_01`, `gq_d4_extension_no_subcode_01`) assert `visa_code_detected:D-2/E-7/D-4`
    through `expected_must_include_metadata` (evaluator :154-171). So parent-code detection from
    text is tested in 3/50 items. Subcode detection from text is tested in 0/50.]
  * OBSERVED.
* **Recommendation.** The new runner should record two baselines side by side. Do not pick one.
  * **B1 (Python, production `/api/ask` contract):** `_detect_visa_codes(None, None, q)` +
    `_detect_task_type(q)`, plus `understand()`.
  * **B2 (JS, search/quick-answer contract):** `VisableStatusGuidance.interpret(q, bundle)`,
    then `.route` and `nextStep`.
  * Score status, subcode and procedure separately, through an explicit crosswalk (section 7).
  * Never let the parent fallback count as a subcode hit.

---

## 2. Component catalogue

### 2.1 Python

| # | Component / entry | Input → output contract | Enum / taxonomy | Languages | Notes |
|---|---|---|---|---|---|
| P1 | `paradiso_backend._normalize_visa_code(code)` [CODE backend/paradiso_backend.py:3729] | `str` → `'A-N'` / `'A-N-SUB'` or input upper-cased | uses `_VALID_MAIN_CODES` (38 codes incl. non-real `F-10`) [3715-3726] | n/a | payload normaliser: `d101`→`D-10-1`, `d42k`→`D-4-2K` |
| P2 | `_split_visa_code(norm)` [:3803] | → `(top, sub)`; sub when ≥3 segments and 2nd is digits | | | `K-ETA` passes through unsplit |
| P3 | `_detect_visa_codes(payload_code, visa_data, text)` [:3843] | → `(top, sub)`. Payload/`visa_data.detected_code`/`visa_data.code` win; **text path returns `(top, None)` only** | top ∈ `_VALID_MAIN_CODES` | code tokens only | Lookahead `(?!-?\d)` [:3885] rejects `D-2` in `D-2-1`, so it returns None, not the parent. IGNORECASE plus optional space lets "a 3" match `A-3` |
| P4 | `_detect_task_type(text)` [:3891-3989] | → one of 11 task types or `None` (priority-ordered `if` ladder) | `foreigner_registration, marriage_divorce_status_change, academic_status_change, overstay_deadline_risk, status_change, workplace_change, activities_outside_status, address_report, passport_info_report, family_status_change, extension` | ko + en substrings/regex | **No** visa-issuance, re-entry or 사증발급인정서 branch. Misses "A에서 B로 변경" (Korean) and "change from X to Y" (English) |
| P5 | `_risk_level_for_task(task)` [:3992-4010] | → `low/medium/high` | | | |
| P6 | `services.knowledge.understanding.understand(text, *, status_code, subcode, task_type, risk_level, lang, legal_issue_types)` [CODE backend/services/knowledge/understanding.py:93-166] | → `QueryUnderstanding` dataclass (`query_language, status_code, subcode, procedure, task_type, intent, retrieval_procedure, intents[], risk_level, needs_current_source, needs_law_source, missing_decisive_facts[], ambiguity, source_requirement, mentioned_statuses[], legal_issue_types[]`) | `Intent` (17) [models.py:168-185]; `AmbiguityState` (5) [models.py:200-205]; procedure via `TASK_TYPE_TO_PROCEDURE` [models.py:142-154] | language: ko/zh/en from script (Hangul→ko, Han→zh, else en) [:82-90] | It composes existing detectors and says it is "NOT a second router". When P3 gives no status and there is exactly one mentioned parent, it takes that parent [:124-131]. The subcode only ever comes from the payload |
| P7 | `KnowledgePlatform.plan(query, payload_code=…, visa_data=…, lang=…)` [CODE backend/services/knowledge/runtime.py:129-163] | → `AnswerPlan` (understanding + retrieval + `CoverageDecision`) | `CoverageState` (9) [models.py:211-220]; `AnswerPath` (8) | | The full deterministic "understand → retrieve → decide" path. `EvalService.observe_case` uses it [evals.py:170-196]; on `/api/ask` it is advisory only [paradiso_backend.py:2751-2764, 6209] |
| P8 | `services.legal_analysis.extract_immigration_facts(question, *, visa_code=None)` [CODE backend/services/legal_analysis.py:434-505] | → dict: `current_status, current_parent_status, current_sub_status, previous_*, target_*, status_transition_detected, proposed_activities[], activity_facts{…tri-state}, user_question_language`, plus `entry_date`, `registration_deadline_basis_days`, `registration_deadline_date` when a date is present | `ACTIVITY_TYPES` (24) [:56-66] | ko + en keywords; language label ko/zh/zhHant/en/unknown [:298-305] | Code regex `_STATUS_RE` [:75]: letters A–H, **digit-only** subcode, so `F-2-7S`→`F-2-7`, `D-4-2K`→`D-4-2` (wrong existing code), `E-7-4R`→`E-7-4`, `d21`→`D-21`. **A→B transition**: on main, `current_status` = target |
| P9 | `classify_activity_types(q)` [:308-423]; `classify_legal_issue_types(q, facts)` [:508-634]; `is_registration_deadline_query(q)` [:211-243] | → `List[str]` / `bool` | `LEGAL_ISSUE_TYPES` (26) [:37-54] | ko + en | Multi-label issue tagger. It is the only Python component with "deadline", "reporting duty" and "re-entry" as issue labels |
| P10 | `extract_entry_date(q)` [:264-279]; `add_calendar_days` [:282] | → ISO date or None | | `YYYY년 M월 D일`, `YYYY[-./]M[-./]D` | No relative dates, no `M월 D일` without a year, no English month names (OBSERVED) |
| P11 | `services.immigration_tools.extract_immigration_facts(text)` [CODE backend/services/immigration_tools.py:738-789] | → `{statusCodes[], dates[], paidActivity, workplaceChange, statusChange, extension, registration, reentry, overstay}` | booleans | ko + en | `_STATUS_CODE_RE` [:735]: letters A–H, K, M; subcode `\d{1,2}` plus optional `-T`. `F-2-7S`→`F-2`, `D-4-2K`→`D-4`, `E-7-4R`→`E-7`, `D-10-T` kept |
| P12 | `missing_decisive_facts(facts)` [:804]; `calculate_deadline(trigger_date, period=…)` [:616-685]; `lookup_status(code, visa_records=…)` [:317-377] | `ToolResult` (`.public_dict()`) | `_STATUTORY_PERIODS`: `foreign_resident_registration` 90, `workplace_change_report` 15, `domestic_residence_report` 30 [:594-613] | | `lookup_status` keeps parent and subcodes structurally separate (`subcodeRulesAreNotParentRules`). The legal bases of the periods were not verified by me (UNVERIFIED) |
| P13 | `services.unified_search.run_unified_search(query, *, visa_data, valid_main_codes, manual_search=None, limit=10)` [CODE backend/services/unified_search.py:749-803]; `detect_visa_codes` [:199-239]; `classify_intent` [:242-344] | → `{query, intent, detectedVisaCodes[], interpretation{intent, intentRule, confidence, signals, recognizedVisaCodes, unrecognizedCodeLikeTokens}, organicResults[], suggestionRows[], …}` | intents (8) [:34-47]: `exact_visa_code, visa_keyword, visa_situation, procedure_question, legal_question, employment_reporting, feature_navigation, unknown` | ko keyword lists (English only incidental) | Validates codes against the dataset (parents + nested subcodes) [:358-383], and reports unknown subcodes as `unrecognized`. Its `\b` boundary fails before Hangul, so `D-2-1비자` silently gives `D-2` and `E-7-1로` silently gives `E-7` (OBSERVED). This is a search intent, not a procedure |
| P14 | `services.employment_nl.sanitize_visa_status(value, allowed_codes)` [CODE backend/services/employment_nl.py:117-134]; `validate_extraction` [:143-230] | → `(code, rejected[])` | | | The trust boundary for **LLM** extraction. **Maps an unknown subcode to its parent when the parent is allowed** [:131-133]. This is a deliberate subcode→parent fallback |
| P15 | `services.law_query_normalizer.*` (`expand_law_query`, `resolve_law_alias`, `rank_law_candidates`) [CODE backend/services/law_query_normalizer.py:305,382,516] | statute-name normalisation and alias resolution | evidence statuses (9) | ko | **Not a status classifier.** Ported from korean-law-mcp (MIT) per its docstring [:24-30] |
| P16 | `services.model_policy.resolve_question_answer_mode(mode, *, question, legal_issue_types, risk_level)` [CODE backend/services/model_policy.py:234-295] | → `{effective_mode, escalation_reasons[]…}` | fast/basic/pro | ko + en regex | A deterministic complexity router, not an intent classifier. Useful as a "high-risk" signal only |

The "Korean intent routing" in `paradiso_backend.py` is P3–P5 together with the
`legal_analysis` issue tagger. Commit a8a924a (#653) says it "correct[ed] four Korean intent
misroutes in legal analysis" [LIVE git show a8a924a --stat].

Two other procedure-key mappers sit downstream of P4:

* `_procedure_variant_key_for_task` maps `status_change`, `workplace_change` and
  `activities_outside_status` to camelCase keys, and maps to `statusGrant` only when the text
  explicitly mentions birth or a status grant [CODE backend/paradiso_backend.py:4303-4339].
* `GROUNDABLE_TASKS` covers 5 task types [CODE understanding.py:48-50].

### 2.2 JavaScript

| # | Component / entry | Contract | Enums | Languages | Notes |
|---|---|---|---|---|---|
| J1 | `VisableStatusGuidance.normalizeCode(raw, bundle.codes)` [CODE assets/js/status-guidance.js:170-188] | → canonical code, `{unknownSub, parent}`, or null | validated against the 269 `bundle.codes` | | Tries splits of contiguous digits (`F27`→`F-2-7`, `G15`→`G-1-5`, `D10T`→`D-10-T`). An unknown subcode falls back to the parent and is flagged |
| J2 | `VisableStatusGuidance.interpret(query, bundle, opts)` [:194-292] | → `{codes[{code, exact, role?, fromUnknown?, fromAlias?}], unknownCodes[], transitionFrom, aliasCandidates[], aliasQuestion, procedure, procedureCandidates[], preAnswers{dim:opt}, confidence HIGH/MEDIUM/LOW, program, keywords[], route, office, conditions, isQuestion, facet}` | procedures = `bundle.procedures` (16) / `PROCEDURE_ORDER` [:165] | ko + en lexicons in the bundle | The longest procedure keyword wins [:249-256]. Natural-language aliases resolve to candidate sets (35 alias groups). The A→B role logic reorders codes so the target comes first [:214-232]. Family dimension aliases pre-answer subtype questions (for example "호텔" → E-9 industry) [:257-268] |
| J3 | `VisableSearchRouter.route(query, bundle, {localPractice})` [CODE assets/js/search-router.js:145-216] | → `{intent, structure, isQuestion, facet, status, statusExact, substatus, statusCandidates, procedure, procedureCandidates, procedureAmbiguous, procedureWhy, objects, actions, office, program, userProgram, conditions, contextRequirement, needs[], confidence}` | `INTENTS` (8) [:30]: `STATUS_ONLY, STATUS_PROCEDURE, PROCEDURE_ONLY, ADMINISTRATIVE_TASK, NATURAL_LANGUAGE_QUESTION, SPECIAL_PROGRAM, AMBIGUOUS, UNKNOWN`; facets `fee, documents, deadline, eligibility, how` [:50-56] | ko + en | Object × action composition: card reissue, registration-info report, address report [:116-136]. Office entity extraction from `local-practice-202609.json` [:84-97]. `interpret()` calls it automatically |
| J4 | `VisableStatusGuidance.nextStep(state, bundle)` [:343-…] | `state={interp, answers, procedure, status, history, lang}` → `{kind: resolved / question / need-status / source-only / unresolved / procedure / program / no-status, target, displayCode, inherited, dimension, options[], scenario, confidence}` | | | The progressive-disambiguation resolver. `inherited:true` + `target` (the parent) + `displayCode` (the subcode) makes parent inheritance explicit |
| J5 | `VisableStatusGuidance.renderModel(step, state, bundle).model.quick` → `VisableQuickAnswer.build(ctx)` [CODE assets/js/waymaker-quick-answer.js:169-245]; `validateModel` [:257] | → `{mode: answer/fee/clarify/fallback, interpretation{status, substatus, procedure, facet, office, program, confidence}, documents{…}, fees[], sources[]}` | | | Built only for question-shaped queries (`isQuestion`). "E-9 근무처 변경 신고 기한" gave `quick=null` (OBSERVED) |
| J6 | `WaymakerNavigator.filterStatusCatalog(buildStatusCatalog(visa_data), q)` [CODE assets/js/waymaker-navigator.js:163-206] | → catalog rows (top-level records only) | `PACKET_TYPE_BY_PROCEDURE_KEY` (8) [:46-55]; `MATERIALLY_AMBIGUOUS_FAMILIES` (11) [:109-112] | 15 UI locales (labels only) | **A guided intake (language → location → status → procedure → sub-status), not a free-text classifier.** The filter is a substring search: "D-2-1" returns `[D-2]`, and "E-7-1" returns `[E-7, D-4-2K]` (OBSERVED) |

**Multilingual understanding is limited to ko and en in every component.**

| Query | Python result | JS result |
|---|---|---|
| zh `D-2签证延期需要什么材料?` | status D-2 kept; procedure lost; `intent=general_explanation`; issue `non_immigration_adjacent_issue` | `procedure=null` |
| vi | same as zh; `query_language` labelled `en` | `procedure=null` |
| ja | same as zh; `query_language` labelled `zh` | `procedure=null` |
| ru | same as zh; `query_language` labelled `en` | `procedure=null` |

[LIVE ml.txt run, 2026-10-19] OBSERVED.

---

## 3. Live offline runs on the four mandated questions

Environment: Python 3.11 `.venv-check`, Node v24.14.0, `WAYMAKER_KNOWLEDGE_DB=:memory:`, no API
keys. All exit codes were 0.

### 3.1 Python (compact; full JSON in `sc_work/py_out.txt`)

```
Q1 "D-2-1 비자 연장하려면 어떤 서류가 필요해요?"
 pb._detect_visa_codes      = [null, null]          pb._detect_task_type = "extension" (risk medium)
 understand                 = status D-2, subcode null, procedure extension, intent required_documents,
                              intents [required_documents, extension], ambiguity clear, mentioned [D-2-1]
 legal_analysis facts       = current D-2-1 (parent D-2, sub D-2-1); activities [document_preparation, status_extension]
 legal issues               = [documents_needed, extension]
 immigration_tools          = statusCodes [D-2-1], extension true; missing_decisive_facts [dates]
 unified_search             = procedure_question / procedure_vocabulary; recognized [D-2-1]; cards subcode D-2-1, parent D-2
 KnowledgePlatform.plan     = D-2 / null / extension / VERIFIED_WITH_CONDITIONS / deterministic_with_conditions

Q2 "What documents do I need to change from D-10 to E-7-1?"
 pb._detect_visa_codes      = ["D-10", null]        pb._detect_task_type = null (risk low)
 understand                 = status D-10, procedure null, intent required_documents, ambiguity missing_procedure,
                              missing [procedure], mentioned [D-10, E-7-1], query_language en
 legal_analysis facts       = previous D-10, target E-7-1, current E-7-1 (main branch semantics), transition true
 legal issues               = [documents_needed, status_change]
 immigration_tools          = statusCodes [D-10, E-7-1]; statusChange FALSE (regex needs 체류자격 변경 / change of status)
 unified_search             = visa_situation / code_with_context; recognized [D-10, E-7-1]; unrecognized ["D-10-TO"]
 KnowledgePlatform.plan     = D-10 / null / null / NEEDS_CLARIFICATION / ask_clarification

Q3 "F-6 결혼이민 외국인등록 대리 신청 가능한가요?"
 pb._detect_visa_codes      = ["F-6", null]         pb._detect_task_type = "foreigner_registration" (medium)
 understand                 = F-6 / null / registration / intent registration, intents [registration, eligibility]
 legal issues               = [registration_deadline, deadline_trigger, reporting_duty, registration_or_residence_report]
                              (is_registration_deadline_query = true although no deadline is asked)
 immigration_tools          = registration true; missing [dates]
 unified_search             = procedure_question; recognized [F-6]
 KnowledgePlatform.plan     = F-6 / null / registration / NO_DIRECT_SOURCE / limited_guidance / gap NO_VERIFIED_KNOWLEDGE
 (no component extracts the "대리 신청" = proxy-filer entity)

Q4 "E-9 근무처 변경 신고 기한"
 pb._detect_visa_codes      = ["E-9", null]         pb._detect_task_type = "workplace_change" (medium)
 understand                 = E-9 / null / workplace_change / intent deadline, intents [deadline, workplace_change],
                              needs_current_source true
 legal issues               = [reporting_duty, workplace_change_addition, status_purpose_alignment,
                               employment_condition, extension, activity_scope]   <- "extension" is spurious
 immigration_tools          = workplaceChange true
 unified_search             = procedure_question; recognized [E-9]
 KnowledgePlatform.plan     = E-9 / null / workplace_change / NO_DIRECT_SOURCE / limited_guidance / NO_VERIFIED_KNOWLEDGE
```

### 3.2 JS (compact; full lines in `sc_work/js_out.txt`)

```
Q1 SG.interpret  codes [D-2-1 exact]; procedure extension; confidence HIGH; facet documents; isQuestion true
   route          NATURAL_LANGUAGE_QUESTION / STATUS_PROCEDURE; substatus D-2-1; contextRequirement STATUS_AND_SUBSTATUS_REQUIRED
   nextStep       resolved, target D-2, displayCode D-2-1, inherited TRUE, confidence HIGH
   quick          mode answer, 6 required + 1 conditional docs, validateModel ok
   navigator      filter("D-2-1") -> [D-2]
Q2 SG.interpret  codes [E-7-1 exact role=target, D-10 (fromUnknown "D-10-TO")]; unknownCodes [D-10-TO];
                  transitionFrom NULL; procedure status_change
   route          STATUS_PROCEDURE; status E-7-1; contextRequirement CURRENT_AND_TARGET_STATUS_REQUIRED
   nextStep       source-only;  quick mode fallback (LOW)
Q3 SG.interpret  codes [F-6]; procedure registration; facet eligibility
   nextStep       question, dimension subtype, options [spouse, childcare, ended]; quick mode clarify
Q4 SG.interpret  codes [E-9]; procedure workplace_change; facet deadline; isQuestion false
   nextStep       resolved, target E-9, confidence MEDIUM; quick = null (not question-shaped)
```

**Reading.**

* Q1: JS keeps the exact subcode and states the inheritance. Python free text loses the subcode.
* Q2: Only `legal_analysis` and the JS role logic notice the status change. JS loses the
  current status because of the "D-10 to" token bug. Python `_detect_task_type` returns no
  procedure.
* Q3 and Q4: both stacks agree on status and procedure.

---

## 4. Edge-case probes (offline)

[LIVE probe_py.py and run_js_baseline.mjs with probes.txt, 2026-10-19] OBSERVED.

| Query | pb `_detect_visa_codes` | pb task | legal_analysis current | immigration_tools | unified_search recognized / unrecognized | JS interpret |
|---|---|---|---|---|---|---|
| `D-2-1 연장` | None | extension | D-2-1 | D-2-1 | D-2-1 / – | D-2-1*, inherits D-2 |
| `D-2-1비자 연장` | None | extension | D-2-1 | D-2-1 | **D-2** / – (silent) | D-2-1* |
| `D-10-T 연장` | **D-10** | extension | D-10 | D-10-T | D-10-T | D-10-T* |
| `F-2-7S 연장` | None | extension | **F-2-7** | **F-2** | F-2-7S | F-2-7S*, inherits F-2-7 |
| `D-4-2K 연장` | None | extension | **D-4-2** (another real code) | **D-4** | D-4-2K | D-4-2K* |
| `E-7-4R 연장` | None | extension | **E-7-4** | **E-7** | E-7-4R | E-7-4R*, inherits E-7 |
| `d21 연장` | None | extension | **D-21** | – | D-2-1 | D-2-1* |
| `Can I get a 3 month extension?` | **A-3** | extension | **A-3** | – | **A-3** | **A-3 → resolved A-3 extension** |
| `I am a 2nd year student` | None | None | **A-2** | – | **A-2** / A-2-ND | **A-2** |
| `D-10에서 E-7-1로 변경` | D-10 | **None** | E-7-1 (prev D-10) | D-10, E-7-1 | **E-7 only** | E-7-1 target, from D-10 ✓ |
| `change of status from D-10 to E-7` | D-10 | status_change | E-7 (prev D-10) | D-10, E-7 | D-10, E-7 / **D-10-TO** | from **null** (D-10-TO) |
| `체류자격 변경 D-10 E-7` | D-10 | status_change | E-7 (prev D-10) | D-10, E-7 | D-10 / **D-10-E** (E-7 lost) | D-10 only (E-7 lost) |
| `re-entry permit for F-5` | F-5 | **None** | F-5 | reentry true | F-5 | reentry |
| `visa issuance for E-7` | E-7 | **None** | E-7 | – | E-7 | visa_issuance |
| `사증발급인정서 E-7` | E-7 | **None** | E-7 | – | E-7 | visa_issuance_confirmation |
| `F-10 비자` | **F-10** (no such status) | None | F-10 | F-10 | – / F-10 ✓ | F-1 with unknown F-1-0 |
| `F-6 배우자인데 E-9로 변경하고 싶어요` | F-6 **or E-9 depending on hash seed** | None | – | – | – | E-9 target, from null |
| [added by verifier] same row, filled in | (seed 0: F-6) | None | E-9 (prev F-6, target E-9) | F-6, E-9 | **F-6 only** (`E-9로` missed by `\b`) | E-9 target, from null |
| [added by verifier] `E-9 사업장 변경 신고` | E-9 | **None** | E-9 | E-9 (`workplaceChange` false) | E-9 | workplace_change, resolved E-9 |

Two more observations from the probes:

* **Date extraction** [LIVE]:
  * Works: `2026년 3월 2일`, `2026.3.2`, `2026-03-02`.
  * Fails: `3월 2일` (no year), `March 2, 2026`, `어제`, `26.3.2`.
* **`calculate_deadline`** returned `preparationDeadline 2026-05-31` for
  `foreign_resident_registration` from 2026-03-02, with `isOfficialDeadline: False`.

---

## 5. Canonical status / subcode inventory

### 5.1 `visa_data.json` and `backend/data/visas.json`

**Files.**

* The two files are byte-identical: sha256 `2f86aee1…f4` for both, and `cmp` reports identical.
  `scripts/sync_visa_data.py` keeps them in sync [DOC backend/services/knowledge/paths.py:1-12].
* The backend load order is: the `VISA_DATA_PATH` env var, then `record_store_union`, then
  `backend/data/visas.json`, then the root file [CODE paradiso_backend.py:3521-3653].

**Records and codes.**

* There are 42 top-level records. 37 are real two-segment statuses:
  * A-1..3, B-1..2, C-1, C-3, C-4
  * D-1..D-10 (all except D-11…; D-5 and D-6 included)
  * E-1..E-10, F-1..F-6, G-1, H-1, H-2
* The other 5 are special records:
  * `D-4-1` and `D-4-2K` are 3-segment codes promoted to top level. They are **also** subcodes
    of D-4.
  * `K-STAR`, `REGION-S` and `YOUTH-STAY` are program records. The navigator flags them, together
    with D-4-2K, as non-canonical [CODE waymaker-navigator.js:117-119].
* The "39 체류자격 categories" in CLAUDE.md does not match any count I computed. The real
  statuses are 37, and the records are 42 (INFERRED).

**Subcodes.**

* Subcodes are nested under `subCodes`: 228 entries in 30 records. A `subcodes` key duplicates
  the identical list in 29 records. [corrected by verifier: 30 records carry a `subCodes` key, but
  only 29 lists are non-empty (`YOUTH-STAY` has an empty list). The duplicate `subcodes` key is
  present, and identical, in all 30. LIVE python count, 2026-10-19.]
* Subcode fields: `code, name, addReq, addReqDocs, note, searchAliases, needsManualReview, status`
  (statuses: active 207, legacy 14, suspended 4, abolished 2, reference_only 1), plus `manualRefs`
  (215), `group`, `nameKo` and `manualReviewReason`.
* 227 subcodes have 3 segments. One, `C-2` under `C-3`, has 2.
* **`*-T` variants** are stored only as subcodes: D-10-T, E-7-T, F-2-T, F-5-T. Nothing else
  marks them as T variants.
* **Some subcodes sit under a parent whose code they do not start with:**
  * `C-3 → C-2`
  * `K-STAR → F-2-7S, F-2-71, F-5-S1, F-5-S2`
  * `REGION-S → F-2-R, E-7-4R, F-3-1R/2R/3R, F-4-R, F-5-6R, REGIONAL-D-2, REGIONAL-E-7`
* **7 subcodes are placed twice**, under the natural parent and under the program:
  E-7-4R, F-2-7S, F-2-71, F-2-R, F-5-S1, F-5-S2, F-5-6R.
* Consequences:
  * `unified_search.build_visa_index` keeps the first placement it sees [:375-382].
  * `lookup_status` only finds subcodes by prefix, so `K-STAR` lists none of its F-codes as
    subcodes (INFERRED from [immigration_tools.py:339-348]).
* [LIVE inv.py / inv2.py] OBSERVED.

**Document fields by procedure.**

* Legacy flat lists:
  * `newReqDocs` (= `initialReqDocs` in 40/42)
  * `extReqDocs` (= `extensionReqDocs` in 42/42)
  * `changeReqDocs` (non-empty in 3)
  * `documents_initial` (`[{name, note}]`, 39)
  * `documents_extension` (33)
  * `documents_registration` (1)
* Subcodes: `addReqDocs`.
* Structured procedures:
  * `procedures.<key>` has `{available, summary, requiredDocs{commonDocs, requiredDocs,
    additionalDocs, conditionalDocs}, notes[], manualRefs[{manualName, manualVersion, pageRange,
    section, confidence, needsManualReview, sourceId…}], variants?}`.
  * Procedure keys and how many records have them:

    | Key | Records |
    |---|---|
    | extension | 41 |
    | registration | 41 |
    | statusChange | 20 |
    | reentry | 17 |
    | workplaceChange | 13 |
    | activitiesOutsideStatus | 6 |
    | statusGrant | 5 |
    | visaIssuance | 4 |
    | partTimeWork | 2 |
    | schoolChange | 1 |

  * There are 78 `variants` (`{id, labelKo, scenarioKo, requiredDocs{4 buckets}, manualRefs,
    notes, statusCode?}`). 64 carry a `statusCode`, and 41 of those are subcode-scoped.
* Provenance metadata: `sourceManualStatus{visaManualVersion '2026.6', stayManualVersion…}`,
  `manualRequiredDocAudit`, `structuredRequirementsRef`, `feeInfo`.

`python3 scripts/check_status_variant_indexing.py` passed: 42 records, 270 searchable tokens, and
"every variant statusCode is searchable" (ran: pass).

### 5.2 `data/status-coverage-202609.json`

Generated by `scripts/build_status_coverage_manifest.py` from the 2026.9 manuals: stay manual
2026-09-18 (43 chapters) and visa manual 2026-09-01 (42 chapters).

* **Records.** 269 records: 37 `status`, 221 `substatus`, 5 `scenario` (`F-1~…`), 6 `program`
  (`PROGRAM:…`).
* **Record fields.** `code, kind, parent, substatus, coverage_state, has_resolver (160 true),
  legacy_record, procedures{16 keys → {state, document_guidance, source{manual, pdf_page,
  section}, inherited_from_parent}}, clarification_dimensions, document_guidance, lifecycle,
  temporal`.
* **Coverage states.** SUPPORTED 67, PARTIAL 50, SOURCE_ONLY 116, UNVERIFIED 35, LEGACY_ONLY 1.
* **Procedure states.** SUPPORTED 205, CONDITIONAL 31, NOT_APPLICABLE 355, GENERALLY_NOT_PERMITTED
  40, EXCEPTION_ONLY 14, SOURCE_ONLY 1744, UNVERIFIED 1739.
  [corrected by verifier: the "16 keys" applies only to the 258 `status` and `substatus` records.
  The 6 `program` records have 0 procedures and the 5 `scenario` records have 1. Counted over all
  269 records, SUPPORTED is 210; 205 is the count for status and substatus records only. In the JS
  bundle, `codes[*].procedures` is sparse: between 0 and 15 entries per code, never 16. LIVE python
  count, 2026-10-19.]
* **Conflicts.** 77.
* **Codes in the manifest but not in visa_data (14):** F-5-27/28/29, the five `F-1~…` scenarios
  and the six `PROGRAM:` entries.
* **Codes in visa_data but not in the manifest (6):** C-2, K-STAR, REGION-S, REGIONAL-D-2,
  REGIONAL-E-7, YOUTH-STAY.
* `node scripts/check_status_coverage_manifest.mjs`: "475 checks passed over 269 records"
  (ran: pass).

### 5.3 `data/status-guidance-202609.json` (the JS bundle)

* `procedures` (16, each `{id, domain visa/stay, ko, en, keywords[]}`) and `procedure_registry`
  (16, with `context_requirement`, one of 6 values: `STATUS_INDEPENDENT, STATUS_OPTIONAL,
  STATUS_REQUIRED, STATUS_AND_SUBSTATUS_REQUIRED, CURRENT_AND_TARGET_STATUS_REQUIRED,
  CONTEXT_DEPENDENT`).
* `codes` (269, each `{kind, parent, name_ko, name_en, coverage_state, procedures{pid: {s state,
  d doc-guidance, p pdf_page, m manual, i inherits, t}}}`).
* `families` (15 parents with clarification `dimensions`):

  | Family | Dimensions |
  |---|---|
  | F-1 | 8 |
  | F-6 | subtype, f61/f62/f63_phase |
  | E-9 | industry |
  | G-1 | ground |
  | D-10 | subtype, d101_track |
  | others | (see bundle) |

* `aliases` (35 natural-language groups, for example 학생비자 → [D-2, D-4] and 배우자 →
  [F-6, F-3, F-1]).
* `guidance` (115 entries, 89 of them extension), plus `transitions` (8), `fees` (15), `overlays`
  (14), `programs` (6) and `law_sources` (14).

---

## 6. How parent / subcode / `*-T` are handled per component

| Component | Exact subcode from text | `*-T` | Letter-suffixed subcodes (-2K, -4R, -7S) | Parent fallback |
|---|---|---|---|---|
| P3 `_detect_visa_codes` text | never (returns None) | collapses to parent | None | none (returns None); payload path keeps subcodes |
| P6 `understand` | never | – | – | **fills parent silently** when one family is mentioned |
| P8 `legal_analysis` | yes, digits only | → parent | **truncated to the wrong code** | n/a |
| P11 `immigration_tools` | yes, digits only, `-T` kept | kept | **→ parent** | silent |
| P13 `unified_search` | yes (dataset-validated) | kept | kept | unknown subcode → parent + `unrecognized` row; Hangul-glued → **silent parent** |
| P14 `employment_nl` | allow-list | – | – | unknown subcode → parent, recorded in `rejected` |
| J1/J2 `interpret` | yes (dataset-validated, compact forms) | kept | kept | unknown → parent with `fromUnknown`; inheritance shown as `inherited` |
| J6 navigator | parent catalog only, asks sub-status for 11 families | – | – | by design |

---

## 7. Procedure taxonomy crosswalk

| Canonical (knowledge `ALL_PROCEDURES`) [models.py:124-139] | backend `task_type` [paradiso_backend.py:3891] | JS bundle procedure id [status-guidance.js:165] | visa_data `procedures` key / packet type [procedure_packet_builder.py:58-67] | legal_analysis issue |
|---|---|---|---|---|
| visa_issuance (사증발급) | – | visa_issuance | visaIssuance / visa_issuance | – |
| visa_issuance_confirmation (사증발급인정서) | – | visa_issuance_confirmation | – | – |
| – | – | electronic_visa | – | – |
| registration (외국인등록) | foreigner_registration | registration | registration / foreigner_registration | registration_deadline, registration_or_residence_report |
| extension | extension, overstay_deadline_risk | extension | extension | extension |
| status_change | status_change, marriage_divorce_status_change | status_change | statusChange | status_change |
| status_grant (체류자격 부여) | family_status_change | status_grant | statusGrant | – |
| workplace_change (근무처 변경·추가) | workplace_change | workplace_change | workplaceChange | workplace_change_addition |
| – | – | workplace_report (근무처 신고) | – | reporting_duty |
| activities_outside_status | activities_outside_status | activities_outside_status | activitiesOutsideStatus | outside_status_activity |
| – | – | part_time_work | partTimeWork | – |
| reentry | – (only the `understand` facet) | reentry | reentry / reentry_permit | reentry |
| address_report | address_report | residence_report | – | registration_or_residence_report |
| reporting_duty | passport_info_report, academic_status_change | registration_info_report | schoolChange | reporting_duty |
| – | – | card_reissue | – | – |
| – | – | program_condition_change | – | – |

Notes on the crosswalk:

* The knowledge layer keeps stay and visa procedures in separate families (`procedure_family`)
  [models.py:157-162], as CLAUDE.md requires.
* No Python text detector can output `visa_issuance` or `visa_issuance_confirmation`.

---

## 8. Existing labelled question → status / subcode / procedure examples

| Source | Count | Labels | Text-derived? | Authorship (git log) |
|---|---|---|---|---|
| `backend/data/eval/paradiso_ai_golden_questions.json` | 50 (ko 30 / en 20) | `visa_code` (35 non-null), `visa_sub_code` (8), `expected_task_type` (41 non-null; 9 null), `expected_risk_level`, `expected_grounding_status` | **task type only.** The codes are passed as the payload (evaluator :94-101; `EvalService._import_golden` :160) [corrected by verifier: also 3 no-payload items assert a text-detected parent code through `expected_must_include_metadata`. `gq_activity_permission_ko_01` is labelled `expected_task_type: null`, but the detector now returns `activities_outside_status`; the evaluator's `_NULL_TASK_EXPECTED` allow-list (:68-77) hides this mismatch, so the label is stale] | commits "Claude" (2026-05-18, 2026-06-01) + Luca Kim (2026-06-07). AI-drafted, owner-committed; human review not evidenced |
| `backend/data/knowledge/eval_corpus_seed.json` | 19 (ko 18 / en 1) | assertions: EXPECTED_STATUS 13, EXPECTED_PROCEDURE 7, EXPECTED_INTENT 7, EXPECTED_SUBCODE 2 (both via `payload_visa_code`), EXPECTED_COVERAGE_STATE 19, … | mostly yes (status/procedure); subcode no | 1 commit "Claude" 2026-09-25 (Co-Authored-By AI). Provenance claims the facts come from the verified stay-manual grounding |
| `backend/data/eval/scenario_grounding_audit_cases_2026_06.json` | 17 | `visa_code`, `expect_status_contains`, `expect_activities_any`, `expect_issues_any` | issues/activities yes | "Claude" 2026-06-08 |
| `backend/data/eval/paradiso_coverage_matrix.json` | 20 rows | `visa_code, visa_sub_code, procedure_type, expected_task_type, requires_subcode` | not questions | – |
| `scripts/check_status_resolver.mjs` | ≈52 distinct query literals + 21-row MATRIX | expected `step.kind`, `target`, `displayCode`, `procedure`, dimension sequence | yes (JS) | Luca Kim commits (#631, #632) |
| `scripts/check_search_router.mjs` | ≈29 literals + ≈30 in loop arrays | `route.procedure`, `intent`, `office`, `facet`, transition target | yes (JS) | Luca Kim (#632, #635, #653; #653 Co-Authored-By Claude) |
| `scripts/check_waymaker_quick_answer.mjs` | 12 mandatory CASES (21 literals) | intent, step kind, mode, fee, document minimums | yes (JS) | Luca Kim (#635, #655) |
| `backend/tests/*` | `_detect_task_type` 32 call lines (3 files); `_detect_visa_codes` 14; `classify_legal_issue_types` 36 (8 files); `extract_immigration_facts` 40 (9 files); unified_search intent asserts 26 | inline asserts | yes | mixed |

**Run results.**

* `EvalService.run()` passed 69/69 (19 seed + 50 golden) [LIVE run_evals.py].
* `evaluate_paradiso_ai_golden_questions.py` passed 50/50 with 0 known gaps (exit 0).
* The JS checks passed: search_router 29, status_resolver 61, navigator 404, quick_answer 23,
  coverage manifest 475.
* pytest passed `292 passed, 23 subtests passed in 5.17s` over test_unified_search,
  test_employment_nl, test_immigration_tools, test_knowledge_platform, test_law_query_normalizer,
  test_legal_analysis_deterministic_fallback and test_ai_answer_regression_source_subcode_2026_06.

**Authorship.** None of these corpora shows evidence of independent human labelling. They were
written together with the code they test, often by AI-assisted commits. Treat them as regression
fixtures, not as a gold standard (INFERRED).

**A policy contradiction sits inside the labels.**

* `check_status_resolver.mjs` asserts "E-7-4 연장 inherits the E-7 common rule and says so".
* The Python seed case `e7.extension.e7_4.never_inherits_parent` expects `NO_DIRECT_SOURCE`.
* The two stacks therefore encode opposite inheritance policies for the same question.
* JS draws on the 2026.9 bundle; Python draws on 2026.6 grounding. A person must decide which is
  correct, and I did not.

---

## 9. Recommendation for "baseline: existing deterministic classifier"

**Report two baselines.** Neither one alone represents "the existing system".

### B1-python: the production `/api/ask` contract

Recipe, from any directory, with no repo writes:

```bash
env -i HOME=$HOME PATH=/usr/bin:/bin PYTHONDONTWRITEBYTECODE=1 LOG_LEVEL=ERROR \
  WAYMAKER_KNOWLEDGE_DB=:memory: WAYMAKER_SAFETY_LOG_DIR=/tmp/<scratch> PYTHONHASHSEED=0 \
  /Users/seonjaekim/dev/Visable-genesis/.venv-check/bin/python -W ignore -c "
import sys; sys.path.insert(0,'/Users/seonjaekim/dev/Visable-genesis/backend')
import paradiso_backend as pb
from services.knowledge.understanding import understand
from services import legal_analysis as la
q=sys.argv[1]; top,sub=pb._detect_visa_codes(None,None,q); t=pb._detect_task_type(q)
u=understand(q,status_code=top,subcode=sub,task_type=t,risk_level=pb._risk_level_for_task(t)).to_dict()
f=la.extract_immigration_facts(q)
print({'raw_status':top,'raw_task':t,'status':u['status_code'],'subcode':u['subcode'],'procedure':u['procedure'],
       'intent':u['intent'],'intents':u['intents'],'ambiguity':u['ambiguity'],'mentioned':u['mentioned_statuses'],
       'la_current':f['current_status'],'la_prev':f['previous_status'],'la_target':f['target_status'],
       'issues':la.classify_legal_issue_types(q,f)})" "E-7-4 연장 준비물 알려줘"
```

What to record:

* Record **both** `raw_status` and `raw_task` (what `/api/ask` actually uses for grounding) and
  the `understand()` output (what the knowledge plan and eval use).
* Pin `PYTHONHASHSEED`, or the run is not reproducible.
* For a coverage-level baseline, `KnowledgePlatform.create(":memory:").plan(q)` gives
  status, subcode, procedure, intent and coverage. It carries the silent parent risk (section 10).

### B2-js: the search page and quick answer

```bash
node -e "const fs=require('fs');const R='/Users/seonjaekim/dev/Visable-genesis';const b=JSON.parse(fs.readFileSync(R+'/data/status-guidance-202609.json','utf8'));b.local_practice=JSON.parse(fs.readFileSync(R+'/data/local-practice-202609.json','utf8'));for(const f of ['status-guidance','search-router','waymaker-quick-answer'])new Function(fs.readFileSync(R+'/assets/js/'+f+'.js','utf8'))();const SG=globalThis.VisableStatusGuidance;const q=process.argv[1];const i=SG.interpret(q,b);const st={interp:i,answers:{},procedure:null,status:null,history:[],lang:/[가-힣]/.test(q)?'ko':'en',query:q};const s=SG.nextStep(st,b);console.log(JSON.stringify({codes:i.codes.map(c=>c.code),exact:i.codes.map(c=>c.exact),unknown:i.unknownCodes,procedure:i.procedure,intent:i.route.intent,facet:i.route.facet,step:s.kind,target:s.target||null,inherited:!!s.inherited,displayCode:s.displayCode||null,dimension:s.dimension||null}))" "E-7-4 연장 준비물 알려줘"
# -> {"codes":["E-7-4"],"exact":[true],"procedure":"extension","intent":"NATURAL_LANGUAGE_QUESTION","facet":"documents","step":"resolved","target":"E-7","inherited":true,"displayCode":"E-7-4",...}
```

* The batch versions are `sc_work/run_py_baseline.py --questions-file F` and
  `QFILE=F node sc_work/run_js_baseline.mjs`.

### Scoring rules the runner should enforce

1. **The subcode is scored only from an explicit subcode field.**
   * Python: `understand().subcode`, which is always None from text.
   * JS: `codes[0].code` when `exact` is true, or `displayCode`.
   * Never score a subcode from `status_code` or `target`. Never award a subcode hit when the
     output equals the parent.
2. **Keep three labels per question:** `status_parent`, `subcode` (nullable), and `procedure`
   (canonical, mapped through section 7). Map backend `task_type` with `TASK_TYPE_TO_PROCEDURE`
   and keep the raw value as well.
   * The mapping loses meaning in two places: `overstay_deadline_risk` becomes `extension`, and
     `academic_status_change` becomes `reporting_duty`.
3. **For A→B questions, label `current` and `target` separately.** The semantics of
   `legal_analysis` differ between main and the owner's branch (section 11).
4. **Treat golden `visa_code`/`visa_sub_code` as a payload.**
   * Re-label those questions for text-only detection, or run them in two modes: with payload
     and without.
5. **Add negative and multilingual items.**
   * Include "a 3 month", "2nd year", zh/ja/vi questions and Hangul-glued codes. The current
     corpora have almost none: 1 English seed case and 0 non-ko/en cases.

---

## 10. Risks

| ID | Severity | Risk | Evidence |
|---|---|---|---|
| R1 | critical | **Silent subcode→parent mapping in the knowledge plan / eval path.** A free-text "E-7-4 …" or "D-4-2K …" gets the parent checklist as `VERIFIED_WITH_CONDITIONS`. This violates "Parent records must NOT render subcode-specific rules as universal" | [LIVE plan(): E-7 / 10 items, D-4 / 9 items; with payload: NO_DIRECT_SOURCE] [CODE understanding.py:126-131] |
| R2 | high | **Hash-seed nondeterminism** in `_detect_visa_codes` for same-length codes. Runs and production workers can disagree | [CODE paradiso_backend.py:3881] [LIVE seeds 0-9: 7×F-6, 3×E-9] |
| R3 | high | **English article/number false positives** ("a 3" → A-3, "a 2nd" → A-2) in P3, P8, P13 and J2. JS returns a resolved A-3 extension answer | [LIVE probes] |
| R4 | high | **Python free text cannot identify subcodes at all**, and maps `*-T` to its parent. Any "exact subcode" metric for B1 is 0 by construction | [CODE paradiso_backend.py:3855-3860, 3885] [LIVE] |
| R5 | high | **Wrong-code truncation** in `legal_analysis` (`D-4-2K`→`D-4-2`, a different real subcode; `F-2-7S`→`F-2-7`; `d21`→`D-21`) and parent truncation in `immigration_tools`. Both feed the LLM prompt (`immigration_facts`) | [CODE legal_analysis.py:75,123-128; immigration_tools.py:735] [LIVE] |
| R6 | medium | **Token glue**: "D-10 to" → `D-10-TO`, "D-10 E-7" → `D-10-E` (E-7 dropped) in unified_search and JS. The JS transition loses the current status for English "from X to Y" | [CODE unified_search.py:74; status-guidance.js:200] [LIVE] |
| R7 | medium | **Procedure gaps in the Python task detector**: no visa issuance / CVI / re-entry; Korean "A에서 B로 변경" and English "change from … to" are not status_change. `immigration_tools.statusChange` is false for Q2 | [CODE paradiso_backend.py:3931-3935] [LIVE] |
| R8 | medium | **Two stacks with conflicting inheritance policy** (E-7-4 extension: JS inherits E-7, Python seed says never inherit). The baseline "truth" depends on which stack is asked | [CODE check_status_resolver.mjs:57; eval_corpus_seed.json e7_4 case] |
| R9 | medium | **Circular golden labels**: codes passed as the payload, so a 50/50 pass says nothing about text detection | [CODE scripts/evaluate_paradiso_ai_golden_questions.py:94-127; evals.py:160] |
| R10 | medium | **Over-tagging**: Q3 is tagged `registration_deadline` without asking about a deadline; Q4 adds `extension` for any work-status workplace change. These tags drive source routing and model-tier escalation | [CODE legal_analysis.py:211-243, 549-559; model_policy.py:58-71] |
| R11 | medium | **Data shape hazards**: subcodes placed under programs and under foreign parents (`C-3 → C-2`), 7 duplicate placements, D-4-1 and D-4-2K both top-level and nested, and `F-10` accepted by the Python main-code list | [LIVE inv2.py] [CODE paradiso_backend.py:3714-3725] |
| R12 | low | **Multilingual**: zh/ja/vi/ru lose the procedure and intent entirely, and ja and vi/ru get the wrong language label | [LIVE ml.txt] |
| R13 | low | **Hangul-boundary misses** in unified_search (`D-2-1비자` → D-2 silently, `D-10에서` missed). The Python backend and JS are fine here | [LIVE] |
| R14 | low | `employment_nl.sanitize_visa_status` intentionally degrades an unknown subcode to the parent. It records this in `rejected`, but a consumer reading only the first tuple element sees the parent | [CODE employment_nl.py:131-133] |

---

## 11. The owner's unpushed branch (`fix/waymaker-qa-2026-10-16`)

[LIVE git -C ~/dev/Paradiso diff 0713370 fix/waymaker-qa-2026-10-16]

* **Detectors.** `_detect_visa_codes` and `_detect_task_type` are unchanged. The inventory is
  also unchanged: same 42 codes and 228 subcodes. `visa_data.json` has content edits only.
* **`legal_analysis.extract_immigration_facts` changes meaning for planned A→B questions.**
  * A new `_COMPLETED_TRANSITION_RE` means `current_status` stays the *source* (`D-10`) unless
    the wording says the change already happened.
  * On main, Q2 gives `current_status = E-7-1`. On the branch it would give `D-10` (INFERRED from
    the diff; not run). [corrected by verifier: now OBSERVED. I executed the branch's
    `legal_analysis.py`, taken from `git show`, against main's other modules. Q2 gave current D-10,
    previous D-10, target E-7-1 on the branch, and E-7-1 / D-10 / E-7-1 on main. "I changed from
    D-10 to E-7 last month" gave current E-7 on both. A `git diff --stat` shows no changes to
    `assets/js`, `unified_search.py`, `immigration_tools.py`, `knowledge/understanding.py` or the
    guidance bundle. In `paradiso_backend.py` the detector names appear only in a context line.]
  * `nationality_or_refugee_context` now needs a 국적-procedure phrase.
  * `post_status_change_residual_duty` now needs a completed change.
  * Runner labels for current and target must therefore record which commit was measured.
* **`knowledge/evals.py`** adds `_refresh_seed_case`, which keeps seed cases in step with the
  seed file. The runner semantics are otherwise unchanged.

---

## 12. Out-of-scope note: korean-law-mcp

The reference repo (read-only, untrusted, not executed) has no residence-status or procedure
classifier.

* `src/tools/compact-query-planner.ts`, `chains.ts` and `scenarios/index.ts` have 0 matches for
  출입국/체류/visa/사증 (grep).
* Its planner extracts statute and precedent query axes.
* Visable already ports only its statute-name normalisation, in `law_query_normalizer.py`
  (MIT attribution [:24-30]).

It is not a source for a status-classifier baseline.

---

## Verification pass

Verifier: adversarial re-check, 2026-10-19. Worktree `/Users/seonjaekim/dev/Visable-genesis` at
`0713370` (confirmed with `git log -1`). I did not edit the worktree.

**How I ran things.** The disk was full during this pass (`df`: 100%, about 180 MiB free), so the
Bash tool and `Write` kept failing with `ENOSPC`. Some runs went through a terminal tab instead,
as ASCII python `-c` one-liners. The Korean text came from `chr()` code points or from the prior
agent's `sc_work/probes.txt` and `ml.txt`. Every run was offline and read-only:

* `env -i`
* `PYTHONDONTWRITEBYTECODE=1`
* `WAYMAKER_KNOWLEDGE_DB=:memory:`
* `PYTHONHASHSEED=0` unless stated
* pytest with `-p no:cacheprovider`

I created no script files; only this notes file was edited.

### Verdicts on the 15 headline claims

| # | Claim (short) | Verdict | Evidence I checked |
|---|---|---|---|
| 1 | Python text detector returns no status for free-text subcodes; `*-T` gives the parent | **confirmed** | [CODE backend/paradiso_backend.py:3855-3860 says sub-code detection is payload-only; :3881-3887 lookahead `(?!-?\d)`]. [LIVE 2026-10-19]: `D-2-1`, `G-1-5`, `E-7-4R`, `D-4-2K`, `F-2-7S` and `d21` + 연장 all gave `(None, None)`; `D-10-T 연장` gave `('D-10', None)`; `E-7-T 연장` gave `('E-7', None)`. OBSERVED |
| 2 | `understand()` / `plan()` replace a free-text subcode with its parent and serve the parent checklist | **confirmed** | [CODE understanding.py:124-131]. The code comment presents the parent fill as deliberate; the output does not flag it. [LIVE plan(), :memory:]: `E-7-4 체류기간 연장 서류` gave E-7 / None / VERIFIED_WITH_CONDITIONS / 10 required documents. With payload E-7-4 it gave NO_DIRECT_SOURCE / gap UNKNOWN_SUBCODE / 0 documents. `D-4-2K …` gave D-4 / 9 documents (with payload: NO_DIRECT_SOURCE). `D-2-1 연장 서류` gave D-2 / 8 documents. OBSERVED |
| 3 | `/api/ask` grounding gives no checklist for free-text subcodes; the two Python paths disagree | **confirmed** (evidence string corrected) | [CODE paradiso_backend.py:4017-4049, 5834-5841]. [LIVE]: `_select_grounding(top, task, sub)` returned None for `D-2-1 연장 서류`, `E-7-4 연장 서류` and `E-7-4 체류기간 연장 서류`, and 8 documents for `D-2 연장 서류`. The signature is `(visa_code, task_type, visa_sub_code)`. The cited expression `_select_grounding(*_detect_visa_codes(…), task)` swaps the arguments, and with it D-2 returns None (I ran this). The conclusion holds with the correct order. The `/api/ask` knowledge plan [:6209-6217] still carries the parent-filled status into the conflict view and the answer guard, but not into the checklist. OBSERVED |
| 4 | `_detect_visa_codes` differs across processes for same-length codes | **confirmed** | [CODE :3881]. [LIVE PYTHONHASHSEED=0..9]: F-6 for 0,2,3,5,6,7,8 and E-9 for 1,4,9, exactly as reported. `git grep PYTHONHASHSEED` found no matches. OBSERVED |
| 5 | English words trigger false codes in every detector; JS gives a definite A-3 answer | **corrected** | [LIVE]: "a 3 month" gave A-3 in `_detect_visa_codes`, `legal_analysis`, `unified_search` and JS. "a 2nd year" gave A-2 in `legal_analysis`, `unified_search` and JS, but None in `_detect_visa_codes`. `immigration_tools` returned no code for either, because [CODE immigration_tools.py:735] needs a hyphen. JS: resolved A-3 with confidence HIGH, and the quick answer was `mode=answer` with 2 required documents. The page does show the notice "A-3-MONTH is not a code found in the September 2026 sources". Inline fix in section 1 |
| 6 | JS is the only rule-based component that reads exact subcodes from text and reports inheritance | **corrected** | [LIVE JS]: D-2-1 → target D-2, inherited, displayCode D-2-1. D-10-T, D-4-2K and G-1-5 resolved exactly. F-2-7S inherited F-2-7, and E-7-4R inherited E-7. But `unified_search.detect_visa_codes` also reads exact, dataset-validated subcodes from text (D-2-1, D-10-T, F-2-7S, D-4-2K, E-7-4R, G-1-5) [LIVE], and `legal_analysis` and `immigration_tools` read digit-only subcodes. Corrected statement: JS is the only component that **both** reads exact subcodes **and** reports rule inheritance (`inherited`, `displayCode`). Section 6 of the notes already reflects this |
| 7 | Task detector: 11 values; no visa issuance / CVI / re-entry; misses A→B wording | **confirmed** | [CODE :3891-3989]: 11 values, counted. [LIVE]: Q2, `D-10에서 E-7-1로 변경`, `visa issuance for E-7`, `사증발급인정서 E-7` and `re-entry permit for F-5` all gave None. JS gave status_change ×2, visa_issuance, visa_issuance_confirmation and reentry. OBSERVED |
| 8 | `legal_analysis` / `immigration_tools` truncate letter-suffixed subcodes | **confirmed** | [CODE legal_analysis.py:75,123-128; immigration_tools.py:735]. [LIVE]: `legal_analysis` gave D-4-2, F-2-7, E-7-4 and D-21; `immigration_tools` gave D-4, F-2 and E-7. D-4-2 is a real subcode of D-4 in visa_data. OBSERVED |
| 9 | `unified_search` and JS glue the next token on as a fake subcode | **confirmed** | [CODE unified_search.py:74; status-guidance.js:200-231]. In JS, a code that came from an unknown token has no `at` position, so it can never be marked "from". [LIVE]: D-10-TO; D-10-E with E-7 lost; JS `transitionFrom` null for "change of status from D-10 to E-7" and for Q2. Extra case: JS read the Vietnamese "D-2 cần" as unknown D-2-C. OBSERVED |
| 10 | Offline evals pass; golden code labels are payload, so they don't test text detection | **corrected** | [LIVE]: EvalService total 69, passed 69, failed 0. The golden evaluator gave 50 passed, 0 failed, 0 gaps, exit 0. But 3 no-payload golden items assert `visa_code_detected` D-2/E-7/D-4 from text [CODE evaluator :154-171]. So parent detection from text is tested 3 times, and subcode from text 0 times. Inline fixes in sections 1 and 8 |
| 11 | Inventory: identical files, 42 records, 228 subcodes, `*-T` only nested, 7 dual placements | **confirmed** (one count corrected) | [LIVE]: `cmp` identical; sha256 `2f86aee197e55b4f…` for both. 42 records; non-standard top-level codes D-4-1, D-4-2K, K-STAR, REGION-S, YOUTH-STAY; 228 subcodes; the 4 T-variants are nested only; the duplicate list matches; C-2 sits under C-3. Correction: 29 non-empty subCodes lists, not 30 (inline) |
| 12 | Manifest and bundle hold 269 records each; 16 procedures per record; state counts; 475 checks | **corrected** | [LIVE]: 269 records with kinds 37/221/5/6 in both files. Coverage-state counts as stated. 475 checks passed. `procedure_registry` has 16 entries with `context_requirement`. But only the 258 status and substatus manifest records have 16 procedures: programs have 0, scenarios have 1, and bundle codes have 0-15. SUPPORTED is 210 overall (205 for status and substatus). Inline fix |
| 13 | JS and Python labels contradict on E-7-4 inheritance | **confirmed** | [CODE scripts/check_status_resolver.mjs:57]. [DOC eval_corpus_seed.json:104-115]: with payload E-7-4, expects NO_DIRECT_SOURCE, UNKNOWN_SUBCODE and no 고용계약서. Both pass today (resolver 61/61; EvalService 69/69). VERIFIED. Which policy is correct is not established |
| 14 | No zh/vi/ja/ru understanding beyond the status code | **confirmed** (one probe per language) | [LIVE ml.txt]: Python gave procedure None, intent general_explanation and issue `non_immigration_adjacent_issue` for all four. Language labels: zh for zh and ja, en for vi and ru [CODE understanding.py:82-90]. JS gave procedure null and step `question` for all four. OBSERVED |
| 15 | Owner's branch: detectors unchanged; planned A→B keeps the source as current | **confirmed** (upgraded to OBSERVED) | [LIVE git diff 0713370..fix/waymaker-qa-2026-10-16 (9bf8849)]: `_COMPLETED_TRANSITION_RE` added, and `current_status = target_status if completed_transition else previous_status`. No diff in `assets/js`, `unified_search.py`, `immigration_tools.py`, `understanding.py` or the bundle. `_detect_*` appear only in a context line. Running the branch's `legal_analysis.py` against main's other modules: Q2 gave current D-10 on the branch and E-7-1 on main. Inline fix in section 11 |

### Other spot-checks (all re-run, all matched the notes)

* Q3 is tagged `registration_deadline` + `deadline_trigger`, and `is_registration_deadline_query`
  is true.
* Q4 issue tags include a spurious `extension`.
* B1 recipe (section 9) ran verbatim: status E-7, subcode None, mentioned [E-7-4],
  la_current E-7-4.
* B2 recipe ran verbatim: target E-7, inherited true, displayCode E-7-4.
* JS checks:
  * search_router 29
  * status_resolver 61
  * navigator 404
  * quick_answer 23
  * coverage manifest 475
* `check_status_variant_indexing.py`: 42 records, 270 tokens, PASS.
* pytest over the 7 cited files: `292 passed, 5 warnings, 23 subtests passed in 5.63s`.
* Seed corpus:
  * 19 cases (ko 18, en 1)
  * EXPECTED_STATUS 13, PROCEDURE 7, INTENT 7, SUBCODE 2 (both via payload), COVERAGE_STATE 19
  * `git log`: "Claude", 2026-09-25
* Golden commits: "Claude" (2026-05-18, 2026-06-01) and Luca Kim (2026-06-07).

### Omissions from the brief that I filled

1. **Per-component invocation table.** The brief asked for one per component; the notes give
   B1, B2 and batch scripts only. Each call below was run in this pass:

   | Component | Call | Read from the result |
   |---|---|---|
   | backend detectors | `pb._detect_visa_codes(None, None, q)`, `pb._detect_task_type(q)`, `pb._risk_level_for_task(t)` | `(top, sub)`, task or None |
   | `/api/ask` checklist | `pb._select_grounding(top, task, sub)` (argument order matters) | `required_documents`, or None |
   | understanding | `understand(q, status_code=top, subcode=sub, task_type=t, risk_level=…)` | `.to_dict()` |
   | knowledge plan | `KnowledgePlatform.create(":memory:").plan(q, payload_code=None)` | `.understanding`, `.decision.to_dict()`, `.grounding["required_documents"]` |
   | legal_analysis | `extract_immigration_facts(q)`, `classify_legal_issue_types(q, facts)`, `is_registration_deadline_query(q)` | current, previous and target status; issue list |
   | immigration_tools | `extract_immigration_facts(q)` | `statusCodes`, procedure booleans |
   | unified_search | `detect_visa_codes(q, set(pb._VALID_MAIN_CODES), set(build_visa_index(visa_list).keys()))` | `recognized`, `unrecognized` |
   | JS resolver | `SG.interpret(q, bundle)`, then `SG.nextStep({interp, answers:{}, procedure:null, status:null, history:[], lang}, bundle)`, then `SG.renderModel(step, state, bundle).model.quick` | `codes[]`, `procedure`, `kind`, `target`, `inherited`, `displayCode` |
   | eval runner | `KnowledgePlatform.create(":memory:").evals.run(persist=False)` | total, passed, failed |

   I always imported `paradiso_backend` first, because it registers the detectors that
   `plan()` uses [CODE paradiso_backend.py:4014]. I did not test `plan()` without that import.
2. **E-9 "사업장 변경" gap** (row added in section 4).
   * `E-9 사업장 변경 신고` gives task None in `_detect_task_type` and procedure None in
     `understand()`. `immigration_tools.workplaceChange` is false. `legal_analysis` still tags
     `workplace_change_addition`.
   * JS gives `workplace_change`.
   * The Python list knows only 근무처 / 직장 / 이직 / 고용주 wording [CODE paradiso_backend.py:3938-3941].
3. **Stale golden label hidden by an allow-list.**
   * `gq_activity_permission_ko_01` expects task null, but the detector now returns
     `activities_outside_status`.
   * The id is in `_NULL_TASK_EXPECTED` [CODE scripts/evaluate_paradiso_ai_golden_questions.py:68-77,
     137], so the mismatch is neither a failure nor a gap.
   * The labels record past behaviour, not ground truth.
4. **More token-glue and boundary cases.**
   * JS turns the Vietnamese `D-2 cần` into unknown D-2-C.
   * `unified_search` drops `E-9로` in the F-6/E-9 question.
   * `F-10` is accepted by `pb`, and JS turns `F-10 비자` into F-1 / F-1-0. Both re-confirmed.

### Omissions I could not fill

* Independent human labelling of any corpus. `git log` shows only commit authors.
* The legal basis of `_STATUTORY_PERIODS` (90 / 15 / 30 days). Still UNVERIFIED.
* Which E-7-4 inheritance policy is correct. That needs manual review against the 2026.9 stay
  manual.
* Multilingual coverage beyond one probe per language, and the navigator's 15 UI locales. Not
  exercised.
* The "≈" literal counts in section 8 for `check_search_router.mjs` and
  `check_status_resolver.mjs`. Not recounted.
