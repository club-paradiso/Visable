# 12 — Evaluation methodology (normative)

Status (2026-10-20): the runner, the metrics, the baselines and the gates in
`experiments/waymaker-ai/waymaker_ai/evaluation/` are **VERIFIED** offline by
`tests/test_evaluation_*.py` on a tiny inline benchmark. They have been **run
on benchmark v0**. The labels are machine-checked or unreviewed, and v0 was
still being edited on 2026-10-20, so no run is on a frozen, human-verified
benchmark. The methodology is **IMPLEMENTED BUT NOT VALIDATED** as a measure of
legal quality.

* First-look report: `experiments/waymaker-ai/reports/benchmark-v0-2026-10-19.json`
  and `.md` (benchmark digest `db882bf2…5e141`, scoring digest
  `1f63a82f…74edc`). WLIE `PROVISIONAL_GO`; b1_python, b1_python_raw, b2_js,
  existing_law and mock_model `NO_GO`. The first look at the decision splits
  is `reports/benchmark-v0-2026-10-19-first-look.md`. Its JSON had the
  same scores as the 2026-10-19 report and was deleted on 2026-10-20. The
  2026-10-19 JSON was compacted the same day (§8). The two
  holdout looks at that digest are entries 1 and 2 of
  `reports/holdout-ledger.jsonl`. Adjudication of every
  WLIE-label disagreement: [research-notes/adjudication-log.md](research-notes/adjudication-log.md).
* 2026-10-20, CI-shaped verification run (scratch output, not a report) on the
  benchmark as edited that day (digest `49c28618…f6f0f5`, commit `e736072`):
  WLIE `PROVISIONAL_GO`, `--fail-on-hard-gates wlie` passed. It is recorded
  in the holdout ledger as that digest's first holdout look.
* Current report, after the hardening pass:
  `experiments/waymaker-ai/reports/benchmark-v0-2026-10-20.json` and `.md`
  (benchmark digest `24528514…bff3`, revision-2 labels, scoring digest
  `c83cb110…25dbfa1c`, clean commit `1481605`). The decisions are unchanged:
  WLIE `PROVISIONAL_GO`, all others `NO_GO`. Its holdout numbers are **post
  hoc** (ledger entry 8): the spec decisions of 2026-10-20 settled
  disagreements first seen on the 2026-10-19 look, so v0's holdout no longer
  holds anything out from WLIE. Side-by-side first-look numbers, the
  before/after of the law-stack fixes and the blind-label audit:
  [research-notes/adjudication-log.md](research-notes/adjudication-log.md) and
  [research-notes/blind-label-audit.md](research-notes/blind-label-audit.md).

No score in this document is a result: results are in the reports. Every
threshold in §7 is a **project hypothesis**, written down before any result
existed, not a validated standard.

Vocabulary: `waymaker_ai/contracts.py`. Example format and per-task label keys:
`schemas/example.schema.json` and `waymaker_ai/dataset/tasks.py`. Verification
rules being measured: [06](06-temporal-law-and-source-identity.md) and
[07](07-evidence-verification-design.md). Experiment that consumes the targets:
[13](13-artemis-experiment.md).

This is rendering, verification and data-hygiene measurement. A high score is
not a claim of legal correctness, and no metric here replaces review of a label
by a person.

## 1. What is measured, and what is not

The benchmark asks closed questions: a status code, a subcode, a procedure id,
a date with a role, a verification status per layer, an ordered list of
candidate version keys, a set of warnings, whether a conclusion must be
withheld. Every metric is an exact comparison of closed values.

**Text similarity is never a correctness measure.** No BLEU, ROUGE, embedding
distance or "close enough" threshold appears anywhere. An answer that is close
to a wrong answer is the failure this benchmark exists to catch. The only text
comparison is in abstention scoring (`forbidden_assertions`), and it is exact
equality after whitespace normalization, or an exact `assertion_key` match.

Out of scope: the quality of a free-text answer, its tone, its Korean style
(kolint covers that), and whether a requirement is legally right. The last one
needs a person.

## 2. Scoring rules

### 2.1 Three outcomes per metric and item

For each metric, each item is `correct`, `wrong` or `not_scorable`.
Not-scorable items are counted, and each one carries a reason. They **never
enter a denominator**. Every rate is reported as value, numerator,
denominator, not-scorable count, and a 95% Wilson interval
(`summary.wilson_interval`). Wilson is used because the denominators are small
and many rates sit at 0 or 1, where the normal approximation collapses to a
zero-width interval.

| Not-scorable reason | Meaning |
|---|---|
| `not_labelled` | The label does not carry this field, e.g. no `needs_clarification` |
| `not_emitted` | The baseline cannot produce the field at all |
| `baseline_emits_coarse_only` | The fine procedure for a coarse-only baseline (B1) |
| `roles_not_emitted` | Date roles for a baseline that returns dates without roles (B1) |
| `no_coarse_equivalent` | The fine label has no backend equivalent: `FINE_TO_COARSE` maps it to `None` |
| `layer_not_reported` | Per-layer agreement on a layer the baseline did not report (see §3.4 for the exception) |
| `label_not_unavailable`, `label_not_version_failure`, `label_not_rejection` | The metric applies only to items whose label is of that kind |
| `baseline_error` | The baseline crashed or its driver failed on the item |
| `baseline_unavailable` | The baseline could not run at all (no Node, no backend interpreter) |
| `not_equivalent_input` | The baseline cannot receive the item's input equivalently (§4) |
| `not_applicable` | The baseline does not answer this task |

A baseline crash is never scored wrong and never silently dropped. It is
counted under `baseline_error`, and hard gate HG-9 fails on any crash.

### 2.2 Code hierarchy

The rules in the repository's CLAUDE.md apply. A 2-segment code (E-7, G-1,
D-10) is a parent. A code with 3 or more segments (E-7-4, G-1-5) is a subcode.
`*-T` variants (F-2-T, D-10-T) are subcodes of their parent. In scoring:

* A subcode is credited **only** from the prediction's own `subcode` field. A
  subcode in `status_code` makes the status wrong and the subcode wrong.
* A parent answer when a subcode is expected is wrong (`parent_fallback`).
* A parent written into the `subcode` field is wrong even when no subcode is
  expected (`parent_in_subcode_field`).
* A sibling subcode (E-7-1 for E-7-4) is wrong, with reason `sibling_subcode`.
  It is not a hierarchy violation.

`parent_fallback` and `parent_in_subcode_field` together are the
**hierarchy-violation** count (CLE-4), and they are a hard gate (HG-10).

### 2.3 Procedures

There are two taxonomies:

* Fine: the 16 ids of `data/status-guidance-202609.json`
  (`contracts.FINE_PROCEDURES`), as labelled.
* Coarse: the backend knowledge keys (`contracts.COARSE_PROCEDURES`). The label
  is mapped to coarse through `contracts.FINE_TO_COARSE`.

A baseline is scored on the taxonomy it emits. B1 (backend) emits coarse only,
so its fine accuracy is `not emitted`. A fine prediction is mapped to coarse for
the coarse metric. A label with no coarse equivalent (`electronic_visa`,
`card_reissue`, `part_time_work`, `workplace_report`,
`program_condition_change`) is not scorable for coarse. Separately, the
**visa-issuance vs stay scope** (`contracts.procedure_scope`) is checked on
whichever taxonomy the baseline emits. A visa-issuance procedure predicted for
a stay question, or the reverse, is a scope violation (CLE-3, hard gate HG-7).

### 2.4 Item verdict

Each task has primary metrics. An item is `wrong` when any primary metric is
wrong, `correct` when all scored primary metrics are correct, and
`not_scorable` when none could be scored.

| Task | Primary metrics |
|---|---|
| status_procedure_classification | `status_exact`, `subcode_exact`, `procedure_fine` (`procedure_coarse` when fine is not scorable) |
| entity_date_extraction | `dates_exact`, `dates_value_exact` |
| citation_verification | `overall_status` |
| temporal_version_selection | `candidates_exact`, `warnings_all_present`, `forbidden_warnings_absent` |
| abstention | `withhold_correct`, `required_issues_covered`, `forbidden_assertions_absent` |

## 3. Metric definitions

Headline names are the keys of `report.headline[<baseline>][<split>]`. Item
metrics are in `report.items[<baseline>][i].metrics`.

### 3.1 Classification (`status_procedure_classification`)

| Headline | Definition |
|---|---|
| `classification.status_exact_accuracy` | Predicted parent status equals the label's `status_code` (both may be null) |
| `classification.subcode_exact_accuracy` | Predicted `subcode` equals the label's `subcode` (both may be null), under §2.2 |
| `classification.subcode_accuracy_subcode_expected` | The same, only on items whose label has a subcode. This is doc 13's `subcode_exact` target |
| `classification.subcode_accuracy_no_subcode_expected` | The same, only on items whose label has no subcode |
| `classification.procedure_fine_accuracy` | Fine procedure equals the label |
| `classification.procedure_coarse_accuracy` | Coarse procedure equals `FINE_TO_COARSE[label]` |
| `classification.current_status_accuracy`, `target_status_accuracy` | For "from A to B" items: the status held now, and the status sought |
| `classification.clarification_precision` / `_recall` | Over items labelled with `needs_clarification`: TP = asked and needed, FP = asked and not needed, FN = needed and not asked |
| `classification.non_code_token_respected` | No predicted code comes from a token the label says is not a code ("a 3", "2nd year") |
| `classification.procedure_scope_violations` | Count of visa/stay scope mixes |
| `classification.hierarchy_violations` | Count of `parent_fallback` + `parent_in_subcode_field` |

Every classification headline is also reported on the **text-only slice**
(`report.headline_text_only`). The slice holds the items without
`payload_status_code`, where every baseline receives exactly the same input
(§4). Doc 13's D1 comparison reads this slice.

### 3.2 Date extraction (`entity_date_extraction`)

| Headline | Definition |
|---|---|
| `dates.value_precision` / `_recall` | Multiset of predicted date values against labelled values (role ignored), micro-averaged over items |
| `dates.value_role_precision` / `_recall` | The same on (value, role) pairs. Only for baselines that emit roles |
| `dates.value_exact_accuracy` | The item's value multiset matches exactly |
| `dates.exact_accuracy` | The item's (value, role) multiset matches exactly |

### 3.3 Citation verification (`citation_verification`)

| Headline | Definition |
|---|---|
| `citation.overall_status_accuracy` | Predicted `OverallStatus` equals the label |
| `citation.layer_agreement.L<n>_<layer>` | Per-layer code agreement, on layers the baseline reported (not-scorable count shows what it did not report) |
| `citation.false_absence_declarations` | **FALSE ABSENCE DECLARATIONS.** Count of items whose label says the source **could not be checked** (overall `verification_unavailable`, or any layer code `verification_unavailable` / `historical_lookup_required` / `version_history_incomplete`) on which the baseline emitted `source_not_found` or `citation_not_found` anywhere. Denominator: those items. `forbidden_codes` does not make an item an unavailability item: authors also forbid `source_not_found` on items whose source exists (a verified or repealed law), and an absence code there is counted by the next two rows |
| `citation.unlabelled_absence_codes` | Count of items on which an absence code was emitted that the label does not contain (any label kind) |
| `citation.wrong_version_detection_rate` | On items whose label L2 is `wrong_version` / `future_not_yet_effective` / `source_outdated`: the exact L2 code was reported. A baseline that reports layers but **no L2** is counted as **not detecting**. The existing backend pins no version, and its rate must show that |
| `citation.accepted_version_failures` | On the same items: the overall status was `verified` or `verified_partial` |
| `citation.accepted_future_not_yet_effective`, `accepted_wrong_version`, `accepted_source_outdated` | The same, per labelled L2 code |
| `citation.unsupported_claim_acceptance_rate` | On items labelled `failed` or `human_review_required`: the share reported `verified` / `verified_partial` |
| `citation.forbidden_code_violations` | Items on which a code in `forbidden_codes` appeared |
| `citation.highest_layer_within_bound` | `highest_verified_layer` ≤ the label's `max_highest_verified_layer` |
| `citation.injection_flag_accuracy` | Instruction-like source text flagged as labelled (scenario N) |

### 3.4 Temporal version selection (`temporal_version_selection`)

| Headline | Definition |
|---|---|
| `temporal.candidate_exact_match` | Ordered list of `[version_id, effective_date]` keys equals the label exactly |
| `temporal.warning_recall` | Micro recall of required `warnings` |
| `temporal.all_required_warnings_present` | Per-item: every required warning present |
| `temporal.forbidden_warning_violations` | Count of items on which a `forbidden_warnings` value was emitted |
| `temporal.candidate_only_determination` | `determination` is `candidate_only` (a selected version is never a legal determination) |

### 3.5 Abstention (`abstention`, model baselines only)

| Headline | Definition |
|---|---|
| `abstention.withhold_accuracy` / `_precision` / `_recall` | `conclusion_withheld` against `must_withhold_conclusion` |
| `abstention.required_issue_coverage` | Micro recall of `required_issue_keys` among the answer's `issues` (rubric coverage) |
| `abstention.forbidden_assertion_violations` | Count of items asserting a `forbidden_assertions` entry (exact key, or exact normalized text) |

No deterministic baseline answers this task. The rubric is the label's key list,
not a judge model.

### 3.6 Model format, performance, cost

| Report field | Definition |
|---|---|
| `model.structured_output_valid_rate` | Model baselines only: the answer was exactly the structured-output contract (no missing, extra or ill-typed key, no non-code in a code field). This is doc 13 G4. A violation keeps the bad value, so it is also scored wrong on its field |
| `performance.latency_ms` | Per item: wall time of the baseline's own computation. For subprocess baselines this is measured **inside** the child, excluding interpreter start and imports (reported separately as `process.import_ms`). B1 runs one fixed unscored warm-up question first. Reported as n, mean, nearest-rank p50 / p95, max |
| `performance.upstream_calls` | WLIE: the sum of `LookupResult.calls` over adapter calls. existing_law: fake-transport requests, scheme-fallback retries included. Models: 1 per item |
| `performance.peak_memory_bytes` | Python baselines: `tracemalloc` peak per item (`tracemalloc_peak`; the model client side only for models). B2: V8 `heapUsed` after the item (`js_heap_used`), which is not a peak |
| `performance.tokens` | Model baselines only, as reported by the server's `usage`. Never estimated |

Timing is machine-dependent. It is reported, and checked by timing gate PG-1,
but it never enters the go/no-go decision or the scoring digest (§8).

## 4. Baselines and the equivalent-input rule

### 4.1 Equivalent-input rule

Every baseline reads the same fields of an example: `input.question`,
`input.payload_status_code`, and, for legal tasks, `input.claim`,
`input.temporal_query`, `input.fixture_set`, `scenario.relevant_dates` and
`scenario.anchor`. Each one receives that information only in the form its
interface accepts. Labels, `scenario.notes`, `source_refs` and review metadata
never reach a baseline. Where a baseline cannot receive an input equivalently,
the item is `not_equivalent_input` (never scored), or the gap is recorded on the
item as a note:

* **B2** has no channel for a UI payload code. Every item with
  `payload_status_code` is `not_equivalent_input` for B2. Use the text-only
  slice to compare B1 and B2.
* **existing_law** takes a question string only. The claim text is sent as the
  question. A cited string the text does not already contain is appended in
  parentheses (`citations_appended=N`). Quoted text, numbers, scope, topic and
  an asserted version key have no backend channel. When a quotation is not
  part of the text, the item carries `quoted_text_has_no_backend_channel`.
  This is a property of the existing system being measured. It is not repaired.
* **Models** receive only the question, plus a `[UI-selected status code: …]`
  line when a payload code exists.

### 4.2 Baselines

Numbering follows the baseline list of the Mission 001 brief as reconstructed
from [13 §3](13-artemis-experiment.md) and
[training-distill §4.2](research-notes/training-distill.md). Names in
`code` are `--baselines` values.

| # | Baseline | `--baselines` | State | Tasks |
|---|---|---|---|---|
| 1 | Backend deterministic detectors (B1-python): `paradiso_backend._detect_visa_codes` + `_detect_task_type` + `services.knowledge.understanding.understand`. Procedure is coarse via `TASK_TYPE_TO_PROCEDURE`. `current/target` from `legal_analysis.extract_immigration_facts`, read literally. Dates from `immigration_tools`, without roles. Recipe: [status-classifier §9](research-notes/status-classifier.md) | `b1_python` (understood view), `b1_python_raw` (raw `_detect_*` view that `/api/ask` grounding uses) | **implemented** | classification, dates |
| 2 | JS resolver (B2-js): `VisableStatusGuidance.interpret` + `search-router` route + `nextStep` over `data/status-guidance-202609.json`. The subcode comes only from an exact code / `displayCode`. The parent comes from the bundle's own `kind` / `parent` records, so `*-T` and letter-suffixed codes are classified by data | `b2_js` | **implemented** | classification, mentioned codes |
| 3 | Existing backend law grounding: `services.law_grounding.build_law_grounding_context` with the claim as the question (search planning → `search_laws` + cloud fallback → `_verify_requested_articles` → `get_law_detail`), against a fake law.go.kr built from the source bundle (§5). Statuses mapped by [07 §4](07-evidence-verification-design.md) (§4.3) | `existing_law` | **implemented** | citation verification |
| 4 | WLIE reference implementation: `legal.verification.verify_claim` (L1–L7) and `legal.temporal.select_candidate_versions` over `legal.adapters.FixtureAdapter` | `wlie` | **implemented** | citation verification, temporal |
| 5 | Mock structured-output model: a deterministic stub that always abstains or returns nulls, driven through the real prompt → JSON-schema → validation → scoring path. A floor and a harness check, **not a model result** | `mock_model` | **implemented** | classification, dates, abstention |
| 6 | Untuned local model (Artemis arm A) through a local OpenAI-compatible server (vLLM / Ollama), with constrained JSON | `openai_compatible` | **adapter implemented, NOT RUN.** Enabled only when `WAYMAKER_EVAL_MODEL_ENDPOINT` (loopback only) and `WAYMAKER_EVAL_MODEL_NAME` are set. Never in tests or CI | classification, dates, abstention |
| 7 | B-fixed: the better of B1 and B2 after the cheap rule fixes of [13 §6](13-artemis-experiment.md) | — | **future** (not built in Mission 001) | classification |
| 8 | Tuned students: arm B (SFT QLoRA) and arm C (verified distillation), served locally and scored through `openai_compatible` | — | **future** (train split empty) | classification, dates, abstention |
| 9 | Reference production chain (REF) and frontier models as reference or judge | — | **future, not permitted offline**: needs a network and paid providers, and eval items may only go to providers after legal review (training-distill §4.2). A judge model would be advisory only, never a correctness metric | — |

The model contract is a single closed JSON object. For classification and dates
it is `status_code, subcode, procedure, current_status, target_status,
dates[{value, role}], needs_clarification`. For abstention it is
`conclusion_withheld, issues[], claims[{text, assertion_key}]`. A model is never
asked to verify a citation or to choose a law version: deterministic code does
that. Doc 13 notes an open gap. The Artemis SFT target is the per-task label
shape, while this contract asks one 7-key object for both classification
tasks. Reconcile the two before arm B is compared with arm A.

### 4.3 Existing-law status mapping

The runner maps what the backend **declares**, never what it should have
declared. If the mapping applied WLIE's own rules (for example "absence only
with complete coverage"), it would credit the backend with the behaviour being
measured.

| Backend citation status | WLIE layers |
|---|---|
| `verified` | L1 pass `source_verified`, L3 pass `citation_verified`. **No L2**: the backend pins no version |
| `failed_verification` + `CITED_LAW_NOT_FOUND` | L1 fail `source_not_found`, as declared. On an item labelled unavailable, this is a false absence declaration |
| `failed_verification` (detail lookup error) | L1 pass, L3 unavailable `verification_unavailable` |
| `source_linked_unverified` / `ARTICLE_TEXT_NOT_FOUND` | L1 pass, L3 unavailable `verification_unavailable`. The backend calls this state "unverified" and cannot tell a parser miss from an authoritative miss, so it is not mapped to `citation_not_found` |
| `error` (+ `SOURCE_UNAVAILABLE`) | L1 unavailable `verification_unavailable` |
| `extracted_only` / nothing looked up | L1 unavailable `not_checked` |
| No citation extracted: `verified_law_evidence` | L1 `source_verified` only |
| No citation extracted: `law_evidence_unavailable` / `law_api_unavailable` / `law_evidence_present_unverified` / `error` | L1 unavailable |

Several citations are combined as spec 07 §3 does: the worst outcome per layer
(fail, unavailable, needs_review, pass, not_applicable).

## 5. Offline sources and the fake law.go.kr

No baseline makes a network call. WLIE reads source bundles through
`FixtureAdapter`. The backend's own law stack is measured against
`evaluation/fake_drf.FakeDrfServer`. Inside the backend child process the fake
replaces both `urllib.request.urlopen` and `urllib.request.OpenerDirector.open`
(which every `build_opener()` opener uses), and answers from the item's
bundle. It does not return pre-parsed results, so the backend's real transport
(`_default_transport` → scheme fallback → `_http_get_once`) and its real
parsers stay in the path.

Why both hooks: a backend that moves from `urlopen` to its own opener would
otherwise bypass the fake, hit the disabled socket, and report every law as
unavailable. That looks like a backend that never declares a false absence.
The driver counts every blocked socket connection per item
(`blocked_network_attempts` in the raw output). An item with any blocked
attempt becomes `error` (`baseline_error`, never scored), so HG-9 fails
instead of a harness gap passing as an answer.

The fake answers in these shapes:

* `lawSearch.do` → `{"LawSearch": {"law": [{법령명한글, 법령ID, 법령일련번호,
  공포일자, 시행일자, 법령구분명, 현행연혁코드, …}]}}`. With no query, it returns the
  가나다 dictionary listing that the cloud fallback pages through.
* `lawService.do` → `{"법령": {"기본정보": {…}, "조문": {"조문단위": […]},
  "부칙": …, "별표": …}}`. Heading units (조문여부 = 전문) stay in the list, as in
  the real API, so the backend's filtering is exercised.
* The version served is the one in force on the item's question date (the
  simulated "today"). A promulgated, not-yet-effective version is never
  current.
* Bundle faults become transport events. `html`, `empty`, `malformed_json`,
  `malformed_xml` and `official_error` are HTTP 200 bodies (the official error
  body is the missing-OC envelope observed live on 2026-10-19). `http_429` and
  `http_500` raise `HTTPError`. `timeout` raises `URLError(socket.timeout)`.
  Network failures raise a connection error.
* The credential is a fixed placeholder and is never recorded. Sockets are
  disabled in every driver before the backend is imported.

Known approximations, recorded per item where they apply:

* Title search is containment in the current official title or exact equality
  with a 약칭. Former titles are not searchable.
* An `ID=` lookup also accepts a version id, because synthetic version ids are
  not numeric.
* The backend fetches a whole law and filters the cited article locally. A
  `get_provision` fault naming a `provision_key` is therefore served on the
  `lawService.do` request made while the backend looks up **that** article. The
  driver records which article `get_law_detail` is asked for.
* The backend never asks for version history, 부칙 or guidance. Faults on those
  operations cannot reach it, and the item records
  `fault_not_exercised:<operation>:<stable_id>` for laws it touched.
* A version whose `parse_status` is not `complete` is served with only the
  captured provisions (`fixture_partial_version:` note). A missing article
  there is a fixture gap, and the mapping in §4.3 never turns it into an absence.

## 6. Splits, held-out policy and contamination

| Split | Use |
|---|---|
| `dev` | Development and debugging. It may be inspected and iterated on. It never decides a gate |
| `test` | Decides gates. **Never tuned on**: nobody changes code, prompts or thresholds after reading a test item's result and re-scores the same benchmark version as if it were a first look |
| `adversarial_holdout` | Decides gates. **Reported once per frozen benchmark version.** The runner prints a notice. With `--holdout-ledger <path>`, every holdout run is appended to a JSONL ledger keyed by the benchmark digest, and a repeat is marked `repeat: true` in the report and on stderr. A relabel gives a new digest, so a re-scoring of items already seen must also pass `--holdout-post-hoc REASON`: the ledger entry, the JSON and the Markdown then carry `post_hoc: true`, the reason and the number of earlier ledger entries under any digest |
| `train` | Never evaluated. The runner refuses `--splits train` |

Gates read only the decision splits (`test`, `adversarial_holdout`). A dev-only
run decides nothing (`INSUFFICIENT_EVIDENCE`).

CI (§10) scores the holdout on every qualifying pull request and push. That is
a pass/fail check, not a report. The job writes its JSON to the runner's temp
directory, uploads nothing, and does not write the ledger. Only the per-baseline
summary lines (decision, count of critical legal errors, scoring digest) and the
hard-gate result reach the log. A CI result is never quoted as a holdout
result. A reported holdout number comes from a run with `--holdout-ledger`.

Contamination prevention:

1. **Frozen bytes.** The report records the sha256 of every benchmark data
   file, every manifest file and every source bundle, plus one benchmark
   digest. A data file that is not an example file (a rubric, a file a
   `MANIFEST.json` declares under `non_example_files`, a file under an evidence
   directory; `waymaker_ai/dataset/layout.py`, 11 §5.1) is hashed but never read
   as examples, and `benchmark.non_example_files` lists it with the reason. The
   runner and the dataset validator import the same layout rule, so the runner
   scores exactly the files the validator checked. The manifest check reports
   mismatches and unlisted files. It never repairs them. An invalid example is
   listed with its reason and left out, never fixed.
2. **No labels in prompts.** Model prompts are built from the question and the
   payload code only. A test pins this with sentinel strings.
3. **No eval items off the machine.** The model endpoint must be a loopback
   address with no credentials in the URL, and no API key is read or sent.
   Sending held-out items to a remote service could put them into someone
   else's training data.
4. **Overlap check.** `--contamination-check <train.jsonl>` (repeatable)
   reports evaluated questions whose normalized text (NFC, collapsed
   whitespace, unified interpuncts, lower case) hashes equal to a training
   question, prompt or user message. This is exact matching only. Near-duplicate detection (n-gram /
   MinHash, training-distill §4.6) belongs to the dataset pipeline.
5. **Promotion retires.** An item promoted to training is retired from every
   evaluation split and replaced (training-distill §4.6). That needs a new
   benchmark version, so the new digest starts a new holdout ledger entry.

## 7. Critical legal errors and gates

### 7.1 Critical legal errors

The runner lists every critical legal error per baseline
(`report.critical_legal_errors`), with example id, split, task, adversarial
class and categories. An item is a critical legal error when any of these holds:

| Runner category | When | Taxonomy (training-distill §4.5) |
|---|---|---|
| `critical_example_wrong` | The example has `critical: true` and its verdict is `wrong` | whichever CLE the example was written for |
| `false_absence_declaration` | §3.3. The source could not be checked, and the baseline said it does not exist | CLE-8 (a fabricated citation verdict), and spec 07 invariant 1 |
| `accepted_future_not_yet_effective` | A claim drawn from a promulgated, not-yet-effective version was reported `verified` / `verified_partial` | CLE-5 |
| `accepted_wrong_version` | A later amendment applied to an earlier event was accepted | CLE-5 |
| `accepted_source_outdated` | A superseded version was accepted | CLE-5 |

These are reported next to the critical list, with their own hard gates:
hierarchy violations (CLE-4, HG-10), visa/stay scope mixes (CLE-3, HG-7),
unsupported claims accepted (CLE-8, HG-5), forbidden temporal warnings (HG-6),
and failures to abstain (CLE-9). CLE-1/2/6/7/10/11 concern free-text answers,
which this benchmark does not score.

### 7.2 Gates (project hypotheses)

Gates are evaluated per baseline over the decision splits combined. A hard gate
with an empty denominator is `insufficient_evidence`, never a pass: "zero false
absences out of zero unavailable items" proves nothing. A gate on a task the
baseline does not answer, or on a field it cannot emit, is `not_applicable`.

| Gate | Kind | Metric | Rule | Why |
|---|---|---|---|---|
| HG-1 | hard | `citation.false_absence_declarations` | = 0 | Failure is not absence (07 §2.1) |
| HG-2 | hard | `citation.accepted_future_not_yet_effective` | = 0 | Promulgated is not effective (scenario E) |
| HG-3 | hard | `citation.accepted_wrong_version` | = 0 | A later amendment must not govern a past event (D) |
| HG-4 | hard | `citation.accepted_source_outdated` | = 0 | Superseded text must not pass |
| HG-5 | hard | `citation.unsupported_claim_acceptance_rate` | = 0 | A failed or review-needed claim must not read as verified |
| HG-6 | hard | `temporal.forbidden_warning_violations` | = 0 | E.g. no false "anchor missing" when the anchor is known |
| HG-7 | hard | `classification.procedure_scope_violations` | = 0 | Visa and stay procedures never mix (CLE-3) |
| HG-8 | hard | critical legal errors (§7.1) | = 0 | |
| HG-9 | hard | baseline crashes on applicable items | = 0 | A crash is never scored, so it must never pass silently |
| HG-10 | hard | `classification.hierarchy_violations` | = 0 | No parent stands in for a subcode (CLE-4; doc 13 G1-safety) |
| SG-1 | soft | `citation.overall_status_accuracy` | ≥ 0.95 | |
| SG-2 | soft | `citation.wrong_version_detection_rate` | ≥ 0.90 | |
| SG-3 | soft | `temporal.candidate_exact_match` | ≥ 0.95 | |
| SG-4 | soft | `temporal.warning_recall` | ≥ 0.95 | |
| SG-5 | soft | `classification.status_exact_accuracy` | ≥ 0.90 | |
| SG-6 | soft | `classification.subcode_accuracy_subcode_expected` | ≥ 0.90 | doc 13 D1 target for `subcode_exact` |
| SG-7 | soft | `classification.procedure_fine_accuracy` | ≥ 0.85 | doc 13 D1 target for `procedure_fine` |
| SG-8 | soft | `model.structured_output_valid_rate` | ≥ 1.0 | doc 13 G4 |
| PG-1 | timing | p95 per-item latency | ≤ 3500 ms | Half of Quick Answer's 7 s timeout (doc 13 G6). Reported only; never in the decision |

Decision per baseline:

* `NO_GO`: any hard gate fails.
* `INSUFFICIENT_EVIDENCE`: no decision split was run, or a hard gate has no
  evidence.
* `HOLD`: hard gates pass, and some soft gate is not a pass (including
  insufficient evidence).
* `PROVISIONAL_GO`: every gate passes, but at least one scored label on the
  decision splits is not `human_verified`.
* `GO`: every gate passes, and every scored label on the decision splits is
  `human_verified`.

Soft thresholds are compared with the point estimate. The Wilson interval is
printed beside it, so a reader can see when a pass rests on a handful of items.
Doc 13's D1 ("is a model needed at all?") is a development decision, not a
gate. It reads SG-6 and SG-7's thresholds on the text-only slice of `dev`.

A threshold is never relaxed after a result is seen. Changing one requires a
new revision of this document, dated before the next scored run.

**Hard-gate exit status (CI).** `--fail-on-hard-gates BASELINE[,BASELINE]`
makes the runner exit 1, after the report is written, when for any named
baseline:

* the baseline was not run, or was unavailable (a gate that never ran proves
  nothing);
* no decision split was scored (a dev-only run cannot pass);
* any hard gate is `fail` **or `insufficient_evidence`** (an empty hard gate is
  never a pass).

`not_applicable` hard gates (a task or field the baseline does not answer) do
not fail the check. Soft and timing gates never enter it, so the check passes
for a `HOLD` or `PROVISIONAL_GO` decision and fails for `NO_GO` and
`INSUFFICIENT_EVIDENCE`. A named baseline that is not in `--baselines` is a
usage error (exit 2). Without the flag the exit status stays 0 whatever the
decision.

## 8. Report and determinism

`--out` writes JSON with sorted keys, indented, with each item record on one
line (`report.dumps`), so a changed verdict is a one-line diff. `--markdown`
writes the human report. Both record:

* the exact command (argv, cwd, shell form), the git commit
  (`git -C <repo> rev-parse HEAD`), the dirty measured paths, and the sha256 of
  every backend / JS / data file a baseline exercised and every experiment
  source file;
* `environment.backend`: the tree whose `backend/` the subprocess baselines
  (b1_python, b1_python_raw, existing_law) imported (`--backend-root`, else
  the repo root). It records `content_sha256`, a sha256 over the sorted
  `[path, sha256]` rows of every file under `backend/` (skipping
  `__pycache__`, `var`, `node_modules`, `*.pyc` and every dot-named file or
  directory, so a `.env` is never read), with the file count and bytes. When
  the tree is a git work tree it also records the HEAD commit, the
  `HEAD:backend` tree id and whether `backend/` is dirty. The same content
  gives the same digest whether it is a checkout or a `git archive`
  extraction. When no baseline of the run imports the backend, the tree is
  named but not hashed;
* Python, backend-Python and Node versions, and each child process's
  `PYTHONHASHSEED`, hash-randomization flag and import time;
* benchmark data file, manifest and source-bundle sha256s, the non-example
  data files with their reasons, invalid examples, label review counts;
* per baseline and split: aggregates per task, the headline, the text-only
  headline, verdicts per adversarial class, not-scorable reasons, violation
  flags, performance, critical legal errors, gates, and every item with its
  prediction, metrics, flags, verdict, notes and `raw_sha256`.

**Raw payloads.** A baseline's raw per-item output (driver payloads, call logs)
is not part of the score. By default an item keeps only `raw_sha256`, the
sha256 of the canonical JSON of that output, so two runs can still be compared
byte for byte. `--include-raw` keeps the payload as well, bounded to 4,000
characters (a larger one is replaced by its hash). `policy.raw_payloads` says
which rule a report used. `python -m waymaker_ai.evaluation.report compact
<report.json> [--out OUT]` applies the default to a report written before
payloads were omitted. It recomputes the scoring digest and refuses unless it
equals the recorded one. The canonical v0 report was compacted this way on
2026-10-20 (1,806,859 → 1,090,955 bytes). `compaction` in the file names the
source file's sha256, and the digest is unchanged.

Items are ordered by split, then task, then id. Baselines appear in command
order. `scoring_digest` is a sha256 over everything a re-run must reproduce:
benchmark files, bundles, per-item predictions, metrics, flags and verdicts,
aggregates, headlines, critical errors and gate decisions. It excludes
timestamps, latencies, memory and the timing gate. Two runs on the same inputs
and the same code give the same digest. A test pins this.

When the working tree has uncommitted changes in measured paths, the report
says so and lists them. **The scores then describe the working tree, not the
commit.** With `--backend-root`, the repo's own `backend/` is neither hashed nor
listed as dirty, because it is not what was measured.

**Before/after on one benchmark.** `--backend-root <tree>` points b1_python,
b1_python_raw and existing_law at another backend, for example a `git archive`
of main, while WLIE, B2, the benchmark, the bundles and the fake law.go.kr stay
the same. Two runs that differ only in `--backend-root` compare the backend
alone, and `environment.backend` names each tree. The runner refuses a tree
without `backend/paradiso_backend.py`. Passing the `backend/` directory itself
gets a hint to pass its parent.

An archive of `backend/` alone resolves repository-root data through the
`backend/data/` deploy copies (`backend/services/knowledge/paths.py`), as the
Railway service does. To pin the repository-root data as well, archive the
whole tree. `environment.backend` hashes `backend/` only.

On 2026-10-20 (dev and test only, b1_python and existing_law; scratch
output), `fc896c2` (main before the law-stack fixes, backend-only archive)
and `e736072` (with them) gave the same scoring digest. 7 of the 13
existing_law items had different raw payloads, but no prediction or verdict
changed. No dev or test item tells the fixes apart. Every adversarial
citation item is in `adversarial_holdout`, the upstream-failure class H
(9 items) included. The holdout comparison was not run, so as not to add a
holdout look for every backend tree.

## 9. Limitations

* **Labels are not human-verified.** Benchmark v0 labels are synthetic or
  machine-checked. Until a named person reviews them, the best possible
  decision is `PROVISIONAL_GO`, and every rate is the agreement with a label
  that may itself be wrong.
* **Synthetic fixtures.** Most legal items use fictional laws (가상체류관리법,
  `synthetic_fixture`). The recorded law.go.kr capture
  (`law_go_kr_capture_2026_10_19`, `verified_web`) captures only some
  provisions. Neither is a statement of current law, and synthetic text never
  reaches a user.
* **No live API.** Response shapes follow the documented DRF samples and the
  recorded captures, not a live session with a credential. The fake's
  approximations (§5) can make the existing backend look better or worse than
  it would live. They are listed so that a reader can discount them.
* **Mock model.** `mock_model` measures the harness, not a model. No model was
  served or scored in Mission 001.
* **Small denominators.** Intervals are wide, and a single item can move a
  rate by many points. There is no paired significance test between baselines
  yet. Doc 13's "95% CI that excludes 0" comparisons need a paired bootstrap
  over items, which is future work.
* **Coverage of the existing system.** `existing_law` exercises the
  question-citation path of `/api/ask` grounding only. The answer-side
  `law_citation_guard`, the Knowledge Platform plan and the LLM wording step
  are not measured.
* **Latency and memory** are measured on one developer machine, inside the
  baseline's own computation. B2's memory figure is heap used, not a peak.
  They are indicators, not service-level numbers.
* **Scope.** No metric evaluates legal correctness, completeness or the wording
  of an answer. Those need human legal review (training-distill §4.4).

## 10. Commands

From `experiments/waymaker-ai`, with the backend's interpreter (`$BACKEND_PY`;
in Mission 001 the backend checkout's `.venv-check` Python 3.11). The runner
itself is standard-library only. The backend interpreter is needed only because
B1 and existing_law run it in child processes (`--backend-python`; default
`$WAYMAKER_EVAL_BACKEND_PYTHON`, else `<repo>/.venv-check/bin/python` when it
exists, else the running interpreter).

```bash
# Full run (dev + decision splits), JSON + Markdown
$BACKEND_PY -m waymaker_ai.evaluation.runner \
  --benchmark datasets/benchmark/v0 \
  --baselines b1_python,b2_js,wlie,existing_law,mock_model \
  --splits dev,test,adversarial_holdout \
  --out reports/<name>.json --markdown reports/<name>.md \
  --holdout-ledger reports/holdout-ledger.jsonl

# Development only (dev split), one task
$BACKEND_PY -m waymaker_ai.evaluation.runner --benchmark datasets/benchmark/v0 \
  --baselines b1_python,b2_js --splits dev --tasks status_procedure_classification \
  --out reports/dev-classification.json

# Before/after: the same benchmark against another backend tree (here main),
# extracted outside the repository
mkdir -p "$SCRATCH/main" && git -C ../.. archive origin/main backend | tar -x -C "$SCRATCH/main"
$BACKEND_PY -m waymaker_ai.evaluation.runner --benchmark datasets/benchmark/v0 \
  --baselines b1_python,existing_law --splits dev,test \
  --backend-root "$SCRATCH/main" --out "$SCRATCH/before.json"
$BACKEND_PY -m waymaker_ai.evaluation.runner --benchmark datasets/benchmark/v0 \
  --baselines b1_python,existing_law --splits dev,test --out "$SCRATCH/after.json"

# The CI command: exit 1 unless WLIE's hard gates pass (or are not applicable)
$BACKEND_PY -m waymaker_ai.evaluation.runner --benchmark datasets/benchmark/v0 \
  --baselines wlie,b1_python,b2_js,existing_law,mock_model \
  --splits dev,test,adversarial_holdout --out "$SCRATCH/ci.json" --fail-on-hard-gates wlie

# Replace raw payloads in an older report by raw_sha256 (refuses if the scores would change)
$BACKEND_PY -m waymaker_ai.evaluation.report compact reports/<name>.json

# A local model (never in tests or CI): loopback endpoint only, no key
WAYMAKER_EVAL_MODEL_ENDPOINT=http://127.0.0.1:8000/v1 WAYMAKER_EVAL_MODEL_NAME=<served-name> \
  $BACKEND_PY -m waymaker_ai.evaluation.runner --benchmark datasets/benchmark/v0 \
  --baselines openai_compatible,mock_model --splits dev --out reports/<name>.json

# Tests (offline; the subprocess tests skip cleanly without the backend or Node)
$BACKEND_PY -m pytest -q -p no:cacheprovider tests/test_evaluation_*.py tests/test_dataset_layout.py
```

Runner flags added on 2026-10-20: `--backend-root PATH` (§8), `--fail-on-hard-gates
BASELINE[,BASELINE]` (§7.2), `--include-raw` (§8) and `--holdout-post-hoc REASON`
(§6; it needs `--holdout-ledger` and a non-empty reason).

**CI.** `.github/workflows/waymaker-ai-experiments.yml` runs on pull requests,
and on pushes to `main`, that touch `experiments/waymaker-ai/**`, the workflow
itself, or one of the six law-stack files the existing_law baseline measures
(`backend/services/law_tools.py`, `law_grounding.py`, `law_citation_guard.py`,
`legal_evidence.py`, `citation_verifier.py`, `law_cloud_fallback.py`). On
Python 3.11 with `backend/requirements-dev.txt` and Node 22 it runs the
experiment tests, the dataset validator on benchmark v0, and the CI command
above. It reads no secret and sets no model endpoint. `openai_compatible` is not
among its baselines. No step after the dependency install opens a network
connection: every baseline answers from fixtures, and the backend drivers
disable sockets before importing backend code. The workflow is **IMPLEMENTED
BUT NOT VALIDATED**: its YAML parses and each command passes locally, but it has
not run on GitHub yet.

Child processes get a complete, minimal environment and inherit nothing:
`PATH=/usr/bin:/bin`, a scratch `HOME` / `TMPDIR`, `PYTHONHASHSEED=0`,
`WAYMAKER_KNOWLEDGE_DB=:memory:`, `LOG_LEVEL=ERROR`, and no API keys. B1 also
gets `LAW_GROUNDING_MODE=disabled`. The JS baseline runs
`waymaker_ai/evaluation/drivers/b2_driver.mjs` under Node.
