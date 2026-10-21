# 11 — Dataset governance (normative for the dataset validator)

Status (2026-10-20, hardening pass): the validator's rules are **VERIFIED**
by the tests in `experiments/waymaker-ai/tests/test_dataset_*.py` (tiny
fixtures in `tests/fixtures_dataset/`). On the whole of benchmark v0 (4 example
files, 188 examples in all four suites) it reports **0 errors and 16
warnings**, all of them `case_template_dev_eval` (§6.1). That run checks the
data's format and consistency. It does **not** validate the labels: no label
has been reviewed by a person (`human_verified_examples: 0` in the manifest),
so the rules are still **IMPLEMENTED BUT NOT VALIDATED** as a guard of label
quality. No train split exists yet, so the train-against-eval rules
(`contamination`, `case_template`) have run only on fixtures. A CI job runs the
validator (§5.1). It was added in this pass and has not yet run on GitHub.

Code: `experiments/waymaker-ai/waymaker_ai/dataset/`
(`layout.py`, `schema.py`, `validate.py`, `pii.py`, `inventory.py`, `__main__.py`).
Fixed contracts it reads and never edits: `waymaker_ai/contracts.py`,
`waymaker_ai/dataset/tasks.py`, `schemas/example.schema.json`,
[06](06-temporal-law-and-source-identity.md) and
[07](07-evidence-verification-design.md).

This document is the rule list. Every rule id the validator reports appears in
§5.2, and a test (`tests/test_dataset_governance_doc.py`) fails if the code and
this table drift apart.

## 1. Status at a glance

| Item | Status |
|---|---|
| Example schema (`schemas/example.schema.json`, `waymaker-example/0.1`) | COMPLETED (fixed contract) |
| Hand-written schema interpreter (`schema.py`, standard library only) | COMPLETED, VERIFIED by tests |
| Per-record, evidence and cross-record rules (`validate.py`) | VERIFIED on fixtures; run on all of benchmark v0 (0 errors, 16 warnings); IMPLEMENTED BUT NOT VALIDATED as a check of label quality (no human-verified label) |
| One benchmark layout for the validator, the runner and the SFT leakage guard (`layout.py`, §5.1) | COMPLETED, VERIFIED by `tests/test_dataset_layout.py` |
| Status-code inventory from `visa_data.json` (`inventory.py`) | COMPLETED, VERIFIED against the file as checked out on 2026-10-20 |
| Personal-data screen (`pii.py`) | IMPLEMENTED BUT NOT VALIDATED (heuristic; recall never measured on a real corpus) |
| Teacher-generated examples | BLOCKED: `configs/teacher_policy.json` `legal_signoff.status` is `pending`, so every `teacher_generated` example is refused |
| Template-level split separation (`scenario.case_template`, rules `case_template` and `case_template_dev_eval`, §6.1) | VERIFIED by tests. On v0 every example names a template; the error branch (train against eval) has nothing to compare until a train split exists |
| Evidence-passage deduplication across splits | NOT STARTED (§6.3) |
| Validator in CI (`.github/workflows/waymaker-ai-experiments.yml`) | IMPLEMENTED BUT NOT VALIDATED: the workflow parses and its commands pass locally; it has not run on GitHub yet |
| Retention enforcement | NOT STARTED (§7 is policy, nothing enforces it) |

## 2. What an example is

One JSON object per example, in a `.jsonl` file (one per line), a `.json`
file holding a list, or a `.json` file holding `{"examples": [...]}`. These are
the shapes `waymaker_ai/evaluation/benchmark.py` reads, so anything the
validator passes is something the runner can score.

| Field | Meaning | Validator focus |
|---|---|---|
| `id` | `^[a-z0-9][a-z0-9-]{3,80}$`, unique across every file checked | `schema`, `duplicate_id` |
| `schema_version` | `waymaker-example/0.1` | `schema` |
| `suite`, `task` | One of the four suites and five tasks in `tasks.py`; the task fixes the suite | `schema`, `suite_task` |
| `language` | BCP-47-like tag (`ko`, `en`, `zh-Hans`) | `schema` |
| `input.question` | The user's text, 1-2000 characters | `schema`, `pii`, duplicates, contamination |
| `input.claim` | `citation_verification` only: `{text, citations[], quoted_text?, numbers?[], scope?, topic?, value?, asserted_version_key?, context_title?}`. `context_title` is the law that 같은 법 / 영 / 규칙 in the claim refer to (`contracts.ClaimInput.context_title`): a non-empty title or null | `input_shape` |
| `input.temporal_query` | `temporal_version_selection` only: `{stable_id, provision, anchor, secondary_anchors?[]}` | `input_shape`, `temporal_label` |
| `input.fixture_set` | The source bundle a legal example is scored against | `source_bundle` |
| `expected` | The label. Keys per task are `TASK_EXPECTED_KEYS` in `tasks.py` | `expected_keys`, `expected_value`, `layer_codes` |
| `scenario` | `adversarial_class` (A-N or null), `relevant_dates` (`RelevantDates` fields), `anchor` (`AnchorKind` or null), `facts`, `notes`, `case_template` (the id of the case template the example was written from, or null) | `scenario`, `hard_negative`, `case_template`, `case_template_dev_eval` |
| `source_refs` | What backs the label: `law_identity`, `source_bundle`, `visa_data`, `status_guidance`, `manual` or `none` | §3 |
| `provenance` | `authoring`, `authored_by`, `created_at`, `license`, `contains_personal_data` (always `false`), `teacher` (`{provider, model, channel, terms_ref, permitted}`, `teacher_generated` only), `derived_from` | §4 |
| `label_review` | `unreviewed`, `machine_checked`, `human_verified` or `disputed`, with `checks`, `reviewer`, `reviewed_at` | `label_review` |
| `split` | `train`, `dev`, `test` or `adversarial_holdout` | §6 |
| `critical`, `revision`, `revision_history` | Critical-error flag and an append-only change log | `schema`, `revision` |

Per-task labels (from `tasks.py`; the validator also checks every value
against the contract enums):

| Task | Required `expected` keys | Optional | Values checked against |
|---|---|---|---|
| `status_procedure_classification` | `status_code`, `subcode`, `procedure` | `current_status`, `target_status`, `needs_clarification`, `not_status_tokens` | inventory, `FINE_PROCEDURES` |
| `entity_date_extraction` | `dates` | `status_codes` | `AnchorKind`, ISO dates, inventory |
| `citation_verification` | `overall`, `layer_codes` | `forbidden_codes`, `max_highest_verified_layer`, `injection_flagged` | `OverallStatus`, `VerificationLayer`, `VerificationCode`, 07 §3 |
| `temporal_version_selection` | `candidate_version_keys`, `warnings` | `forbidden_warnings`, `determination` | `TemporalWarning`, the bundle's versions, 06 §3 |
| `abstention` | `must_withhold_conclusion`, `required_issue_keys` | `forbidden_assertions` | types only (scored on model answers) |

## 3. Facts and labels are kept apart

Factual legal evidence and training-ready examples are different artefacts with
different owners and different rules.

| Artefact | Where | Holds | Never holds |
|---|---|---|---|
| Source bundle | `datasets/fixtures/sources/<bundle_id>.json` | Identities, versions, provision text, 부칙, guidance and scripted lookup faults, each with provenance (format in the WLIE source bundle contract) | Labels, model output |
| Law identity registry | `datasets/registry/*.json` | One record per 법령ID or 행정규칙ID: titles, `version_id`, `effective_date`, pending versions, source URL, retrieval date | Statute text, labels |
| Example | `datasets/benchmark/...` (and a future train file) | A question, the label, references to evidence, provenance and review state | Copies of statute text presented as a label |

Rules that follow from the split, all enforced:

- An example points at evidence by id. A `law_identity` ref must name a
  `law_id` that exists in the registry; its `version_id` and `effective_date`,
  when given, must match a version the registry records (its own or a pending
  one). A title is never accepted as an identity: a ref that names a title
  gets an error that tells the author which `law_id` to use.
- `input.fixture_set` and every `source_bundle` ref must resolve to
  `datasets/fixtures/sources/<id>.json`. Bundle ids are file names and are
  refused if they could leave that directory. A ref's version must exist in
  the bundle; a provision missing from that version is a warning, because a
  deliberately missing article belongs in the claim, not in `source_refs`.
- A temporal label must name candidates that are versions of the queried
  identity in its bundle. It must follow 06 §3 where the outcome is mechanical:
  a bundle that faults `list_versions` for the identity means no candidate plus
  `version_history_unavailable`; an anchor whose date is absent from
  `scenario.relevant_dates` means no candidate plus `anchor_missing`.
- A citation label must use codes that 07 §3 reports at that layer, and its
  `overall` must be reachable from its `layer_codes` under
  `contracts.ClaimVerification.overall()` (the validator calls the contract's
  own roll-up). Unlisted layers are unknown, so they can only make the roll-up
  worse or complete it to `verified`.
- The validator never runs the resolver or the verifier to produce or check a
  label. Labels are written from 06 and 07; a disagreement between a label and
  the implementation is a finding for the benchmark, not something the
  validator should hide by agreeing with the code.

## 4. Provenance and licence rules

### 4.1 Official law text

- Statute text, 행정규칙 (고시·훈령), and court, Constitutional Court and
  행정심판 decisions are unprotected works under 저작권법 제7조 items 1-3
  (VERIFIED on law.go.kr; [research-notes/official-api.md §6](research-notes/official-api.md)).
  The notes read this as free to redistribute and to use for training; that
  reading is INFERRED and is not legal advice.
- Attribution is still required. open.law.go.kr lists using or providing
  법제처 law information without stating the source, or naming another agency
  as the source, under its 저작권법 제137조 / 제138조 warning (official-api.md
  §6, VERIFIED). Every bundle with law.go.kr evidence must carry
  `출처: 법제처 국가법령정보센터 (law.go.kr)` in `attribution`; the validator
  refuses one that does not.
- For state works used under 저작권법 제24조의2 (most plausibly MOJ manuals and
  법령해석례), 제37조 makes source attribution a statutory duty. That 제24조의2
  sits in the sub-section 제37조 covers is INFERRED in the notes, not verified.
- law.go.kr text has no legal effect; the 관보 prevails. No dataset artefact
  may present captured text as authoritative, and altered text must never be
  presented as official (the anti-forgery rule on both sites).
- Every verified record carries retrieval provenance: an `official_url` on an
  allowlisted official host (`contracts.OFFICIAL_SOURCE_HOSTS`), `retrieved_at`
  (an ISO date or timestamp), and either `content_sha256` of the capture file
  or a bundle-level `captures` list with the sha256 of every file read.
- No page fetched on open.law.go.kr or law.go.kr states AI-training licence
  terms (VERIFIED absence on the fetched pages, which is not evidence that
  법제처 has no position). The 2026-01-28 공공누리 AI-training type is
  RESEARCHED ONLY: its conditions sit in attachments nobody opened.

### 4.2 Manual editions

- A `manual` ref must name an edition id that exists in
  `data/manual_approval_index.json` (read-only). Use the index's own ids, for
  example `stay_manual_2026_09_18_hwp`; the shorter ids in
  `data/status-guidance-202609.json` (`stay_manual_2026_09_18`) are not edition
  ids and are refused.
- Only `approval_state: approved` is content-approved, mirroring
  `DIRECT_EVIDENCE_STATES` in `backend/services/manual_registry.py`. Any other
  state is the warning "label backed by unapproved manual edition". On
  2026-10-20 the approved editions are `stay_manual_2026_07_31_hwp` and
  `visa_manual_2026_07_31_hwp`; the 2026.9 editions are `needs_review`.
- A ref's `effective_date` must match the index.
- Visa-issuance and stay procedures never share evidence: a label whose
  procedure is visa-scope (`contracts.procedure_scope`) cannot be backed by a
  `stay_manual_*` edition, and the reverse.

### 4.3 Teacher outputs

- `teacher_generated` examples are allowed only as `configs/teacher_policy.json`
  permits. When that file does not exist every such example is the error
  "teacher policy missing".
- `provenance.teacher` must give `provider`, `model` and `channel` (the policy
  decides per serving channel, because the same weights can be permitted
  self-hosted and forbidden through a free API route), plus `permitted: true`.
  The block is checked before the policy is read, so a block without `channel`
  is reported even when the policy file is missing or pending. The validator
  asks the policy itself (`TeacherPolicy.is_permitted`); the example's own
  `permitted` flag is necessary, never sufficient.
- While `legal_signoff.status` is not `approved`, every teacher-generated
  example is refused, whatever its entry says. On 2026-10-20 it is `pending`.
- A teacher's conclusion is a candidate label, never gold: a
  `teacher_generated` example in `dev`, `test` or `adversarial_holdout` must
  be `human_verified`.
- A `teacher` block on any other kind of example is an error.

### 4.4 Synthetic fixtures

- Synthetic laws use obviously fictional names (`가상체류관리법`,
  `가상체류관리법 시행규칙`) and the provenance `synthetic_fixture` on the bundle
  and on every record in it.
- A synthetic bundle must not reuse a registry `law_id` or title, use a
  digit-only id shaped like a 법령ID, name law.go.kr as provider, or carry an
  official URL. A synthetic title without a fictional marker is a warning.
- A synthetic bundle may back only `synthetic_authored` examples, and an
  example that uses one may not also cite a real `law_identity`.
- A verified bundle may not contain a single synthetic record.

### 4.5 What never enters a dataset

- Real case files, application packets, decisions addressed to a person, or
  anything copied from a consultation.
- 외국인등록번호, 주민등록번호, passport numbers, phone numbers, e-mail
  addresses or any other identifier of a real person.
- Refugee interview records or statements, even paraphrased or "anonymised".
- User data: chat logs, uploaded documents, analytics, support tickets.

`provenance.contains_personal_data` must be `false`, and the personal-data
screen (§5.3) runs on every string, keys included. The screen is a net, not a
permission: an example that passes it but came from a real person's case is
still forbidden.

## 5. The validator

### 5.1 Running it

```bash
cd experiments/waymaker-ai
/path/to/python -m waymaker_ai.dataset.validate <files or dirs> \
    [--registry datasets/registry] [--sources datasets/fixtures/sources] \
    [--inventory ../../visa_data.json] [--manual-index ../../data/manual_approval_index.json] \
    [--teacher-policy configs/teacher_policy.json] [--schema schemas/example.schema.json] \
    [--json out.json]
```

`python -m waymaker_ai.dataset` is the same command. Exit status: `0` no
errors (warnings may remain), `1` at least one error, `2` the command line or
the example schema itself is unusable. It reads `visa_data.json`, the manual
approval index and every bundle read-only, makes no network request, writes
nothing except the optional JSON report, and needs only the standard library.

CI: `.github/workflows/waymaker-ai-experiments.yml` runs
`python3 -m waymaker_ai.dataset.validate datasets/benchmark/v0` (default
registry, sources, inventory, manual index and teacher policy) on every pull
request and every push to `main` that touches `experiments/waymaker-ai/**` or
one of the six law-stack backend files. An error fails the job. Warnings do not.

Directory arguments are walked recursively. Which files under a directory are
examples is decided by `waymaker_ai/dataset/layout.py`, the one rule the
validator, the evaluation runner (`evaluation/benchmark.py`) and the SFT
leakage guard (`distillation/sft_dataset.py`) import. Before this module each
kept its own copy, and they drifted: the validator skipped evidence directories
that the runner still scored, so an example could be scored that no rule had
checked. `tests/test_dataset_layout.py` builds one tree with every kind of file
and checks that the three agree.

* A **data file** is a `.json` or `.jsonl` file whose name is neither a
  manifest (`MANIFEST`, `MANIFEST.json`, `MANIFEST.sha256`, `SHA256SUMS`,
  `MANIFEST.txt`) nor dot-named. The runner hashes every data file into the
  benchmark digest, because a rubric changes what a label means. The leakage
  guard reads every data file by content, so it reads at least what the
  runner scores.
* An **example file** is a data file that is none of these: under a hidden
  directory or a directory named `fixtures`, `registry`, `sources`, `config`,
  `configs`, `schemas` or `reports`; a rubric (`*_rubric.json`); a file listed
  under `non_example_files` in a `MANIFEST.json` of an enclosing directory
  inside the walk root (paths relative to that manifest's directory, as
  strings or `{"path": …}` objects). The validator checks example files and
  the runner scores them. The runner lists each other data file in its report
  with the reason (`benchmark.non_example_files`).
* Rule `layout`: a malformed `non_example_files` (not a list, an absolute
  path, `..`, a backslash, surrounding spaces) is an error. A declaration
  that names no file is a warning (stale, but it hides nothing). A rubric or
  a declared file that holds example records (objects with `id` and `task`)
  is an error, because those records would be neither validated nor scored.

A file named on the command line is always read as an example file. A JSON
object that is not `{"examples": [...]}` is an error when the file was named on
the command line and a skipped-file warning when it was found in a directory.
Benchmark v0's `abstention_rubric.json` is a rubric by name, so it no longer
raises that warning.

Output: a summary with counts by suite, task, language, split, adversarial
class, label status and authoring, then every error and warning, then
`result: PASS` or `FAIL`. Everything is sorted, so two runs over the same files
print identical text. `--json` writes the same report
(`waymaker-dataset-report/0.1`) with sorted keys.

Every issue's id, path and message passes through the personal-data redactor
when it is created, and so do the count buckets. An id such as
`900101-5234567` matches the id pattern and an object key can be anything, so
without this the report would itself carry the value it reports.

### 5.2 Rules

Severity `E` is an error (exit 1), `W` a warning.

| Rule id | Sev. | What it checks | Source of the rule |
|---|---|---|---|
| `parse` | E/W | Valid UTF-8 JSON, no duplicate keys, no NaN/Infinity, each example an object, paths exist, at least one file; a non-container JSON object is E when named, W when discovered | Determinism |
| `schema` | E | `schemas/example.schema.json`: types, enums, const, required, top-level `additionalProperties: false`, patterns (a trailing `$` means end of string), lengths, minimum, `format: date` as an assertion (`YYYY-MM-DD`, a real calendar date). An unsupported schema keyword stops the run (exit 2) | Fixed contract |
| `suite_task` | E | `suite` is the suite of `task` | `tasks.TASK_SUITE` |
| `expected_keys` | E | Required `expected` keys present, no keys outside required plus optional | `tasks.TASK_EXPECTED_KEYS` |
| `expected_value` | E | Values are contract enum members (`FINE_PROCEDURES`, `AnchorKind`, `OverallStatus`, `VerificationLayer`, `VerificationCode`, `TemporalWarning`), dates are ISO, version keys are `[version_id, date or null]`, no code both expected and forbidden, `determination` is `candidate_only`, `not_status_tokens` occur in the question | contracts, 06 §3 |
| `layer_codes` | E | Each layer code is one 07 §3 reports at that layer (plus `verification_unavailable`, `human_review_required`, `not_checked`); `overall` is reachable from the codes under `ClaimVerification.overall()` | 07 §1, §3 |
| `input_shape` | E | `claim` only on citation examples, `temporal_query` only on temporal ones, `fixture_set` on both; claim and query fields typed and in their enums; `claim.context_title` a non-empty string or null | Benchmark conventions, `contracts.ClaimInput` |
| `scenario` | E | `scenario.anchor` is an `AnchorKind` or null; `relevant_dates` keys are `RelevantDates` fields; citation and temporal examples have `relevant_dates.question_date`; `case_template` a non-empty id without surrounding whitespace, or null | contracts, task brief |
| `temporal_label` | E | Query anchor equals scenario anchor; a faulted history means no candidate and `version_history_unavailable`; an absent anchor date means no candidate and `anchor_missing`; the stable id and every candidate exist in the bundle | 06 §3 |
| `hard_negative` | E | An adversarial example sits in `test` or `adversarial_holdout`, and expects more than a clean pass: citation `overall` not `verified` or non-empty `forbidden_codes`; temporal non-empty `warnings` or `forbidden_warnings`; abstention `must_withhold_conclusion` or non-empty `forbidden_assertions`. Classification and extraction labels carry no pass/fail signal, so only the split part applies to them | Task brief, §6.1 |
| `split_policy` | E/W | E: a `teacher_generated` example in an eval split must be `human_verified`. W: an `adversarial_holdout` example without an adversarial class | §4.3, §6.1 |
| `inventory` | E | Every status or subcode code in `expected` (`status_code`, `subcode`, `current_status`, `target_status`, `status_codes`) and in `visa_data` / `status_guidance` refs exists in `visa_data.json`; an unreadable inventory is a file-level error | Repository data |
| `subcode_hierarchy` | E/W | E: a subcode as `status_code`, `subcode` equal to `status_code`, a subcode with a null `status_code`, a parent code as `subcode`, a subcode under the wrong parent. W: a program record as `status_code`, a subcode placed only under a program, the C-2-under-C-3 irregularity | CLAUDE.md code hierarchy |
| `procedure_scope` | E | A visa-scope procedure is not backed by a stay manual edition, nor the reverse | CLAUDE.md procedure scope |
| `source_refs` | E | `kind: none` is not combined with other refs | Schema semantics |
| `law_identity` | E | Registry present; `law_id` exists (a title gets a "use law_id …" hint); version matches the registry record | 06 §1 |
| `source_bundle` | E/W | Bundle id safe and present; synthetic bundle backs only `synthetic_authored` and never sits next to a real `law_identity`; ref version in the bundle (missing provision is W); bundle-level problems (E) and notices (W), listed in §5.5 | Source bundle contract, §4.1, §4.4 |
| `registry` | E | Registry files are valid JSON lists (or `{"records": [...]}`) of objects | Determinism |
| `manual_edition` | E/W | Edition exists in the approval index (E), is approved (W otherwise), effective date matches (E); a missing index is E | §4.2 |
| `teacher` | E | Teacher block complete (`provider`, `model`, `channel`), checked whatever the state of the policy file; `permitted: true`; policy file present and valid; policy permits (provider, model, channel); legal sign-off approved; no teacher block on other examples | §4.3 |
| `provenance` | W | `derived_from_repository_data` examples name the files they came from | §4 |
| `label_review` | E | `human_verified` has `reviewer` and `reviewed_at`; `reviewed_at` is not before `created_at` | Task brief |
| `revision` | E | `revision_history` revisions increase strictly and end at `revision` | Append-only log |
| `pii` | E | No personal-data shape in any string or key (§5.3) | §4.5 |
| `duplicate_id` | E | Ids unique across all files checked | Task brief |
| `duplicate_question` | E | Same task, same normalized question and same remaining input as an earlier example, same label | Task brief, §6.2 |
| `contradiction` | E | As above but the same language and a different `expected` | Task brief, §6.2 |
| `question_reuse` | W | Same task and normalized question, different remaining input (claim, bundle, query, dates, anchor, facts) | §6.2 |
| `contamination` | E | Character-3-gram Jaccard ≥ 0.85 between a `train` example and any `dev`, `test` or `adversarial_holdout` example | Task brief, §6.3 |
| `contamination_dev_test` | W | The same between `dev` and `test` | Task brief, §6.3 |
| `case_template` | E | A `scenario.case_template` used by a `train` example and by a `dev`, `test` or `adversarial_holdout` example; reported on each eval example | §6.1 |
| `case_template_dev_eval` | W | A `scenario.case_template` used by a `dev` example and by a `test` or `adversarial_holdout` example; reported on each of the latter | §6.1 |
| `layout` | E/W | E: a malformed `non_example_files` declaration in a `MANIFEST.json`; a rubric or declared non-example file that holds example records. W: a declared non-example file that does not exist | §5.1, `layout.py` |

### 5.3 Personal-data screen

`pii.py` reports a kind and a character span, never the value. Text is
NFKC-normalized first, so full-width digits and signs cannot slip past.

| Kind | Flagged when |
|---|---|
| `alien_registration_number` / `resident_registration_number` | `######-#######` with any dash, always; 13 bare digits, or 6 + space + 7, when the first six digits read as YYMMDD. The 7th digit only picks the label (5-8: foreigner). The YYMMDD condition keeps 13-digit 행정규칙일련번호 such as `2100000275060` (month `00`) from being flagged; a real registration number always has a valid month and day |
| `passport_number` | A letter-led token of 7-10 characters with at least 6 digits, or 9 bare digits, within 30 characters of 여권 / passport / 护照 / 護照 / 旅券 / パスポート |
| `mobile_number` | 010, 011, 016-019 or +82 1x numbers, with or without separators, not part of a longer digit run |
| `email_address` | `local@domain.tld` |

Hex tokens of 32 characters or more (sha256 digests) are skipped. False
positives are acceptable (rewrite the example); false negatives are not, so
the screen errs toward flagging. It cannot recognise a name, an address or a
narrative that identifies a person, which is why §4.5 is a sourcing rule and
not only a scan.

### 5.4 Status-code inventory

`inventory.py` reads `visa_data.json` read-only (42 top-level records, 261
codes when checked on 2026-10-20). It collects top-level `code`s and both
`subCodes` and `subcodes` lists. Hierarchy follows the repository rule: two
segments make a parent, three or more a subcode, so D-4-1 and D-4-2K count as
subcodes of D-4 although they also have records of their own. The `*-T`
variants (D-10-T, E-7-T, F-2-T, F-2-T1, F-5-T, F-5-T1) exist only as subcodes.
Program records (K-STAR, REGION-S, YOUTH-STAY) are not statuses of stay; six
codes sit only under a program (F-3-1R, F-3-2R, F-3-3R, F-4-R, REGIONAL-D-2,
REGIONAL-E-7), so their parent cannot be checked and a label using one gets a
review warning instead. G-1-5 is a subcode of G-1, never a family. C-3 lists
the two-segment C-2 as a subcode; the inventory keeps both facts and the
validator turns any label that depends on the choice into a review warning.

### 5.5 Bundle-level checks (reported once per bundle, rule `source_bundle`)

- Shape: every top-level key of the shared format with the right JSON type;
  `bundle_id` equals the file name; `bundle_version ≥ 1`; enums for
  `provenance`, coverage, `family`, `parse_status`, record `provenance`,
  `unit_kind`, addendum `kind`, fault `operation`, `status` and
  `raw_body_kind`.
- Integrity: unique identity stable ids; every version, provision and addendum
  belongs to a known identity and version; no duplicate version keys; unique
  `evidence_id` among addressable units. Heading units (조문여부 = 전문) are
  exempt, as in the fixture adapter: they are never returned, and the official
  JSON puts a chapter and a section heading on one article number (제4장 and
  제1절 both before 난민법 제30조), so their ids collide by construction.
- Synthetic and verified rules from §4.1 and §4.4, and the personal-data
  screen over the whole bundle.

### 5.6 Probe against the real evidence files

On 2026-10-20, two scratch examples were validated with the default registry,
sources, inventory, manual index and teacher policy: a temporal 제73조 example
on `law_go_kr_capture_2026_10_19` with a `law_identity` ref to 008494, and a
synthetic citation example on `synthetic_core`. Result: 0 errors, 0 warnings.
The registry loads 16 law ids with no problems, and both bundles pass every
bundle-level check. The scratch files were deleted afterwards; this is a smoke
test of the formats, not a validation of any label.

## 6. Splits and contamination

### 6.1 Split policy

- `train` is never scored. `dev` is for iteration, `test` is the reported
  number, `adversarial_holdout` holds hard negatives that nobody tunes on.
- Every example with an adversarial class (A-N, `tasks.ADVERSARIAL_CLASSES`)
  belongs in `test` or `adversarial_holdout`, and its label must expect a
  failure, an abstention or a warning (rule `hard_negative`).
- Teacher-generated examples reach an eval split only after human
  verification. A case promoted from eval to training is retired from every
  eval split and replaced (training-distill.md §4.6).
- Split by case template and evidence section, never by individual example
  (training-distill.md §4.6, 13 §5). Near-identical variants written from one
  template (the same facts with another date or code) can be worded apart
  enough to pass the character-3-gram check of §6.3, so the template is named
  on the example (`scenario.case_template`, schema 2026-10-20) and the rule is
  on the id, not on the text:
  - a template used in `train` and in `dev`, `test` or `adversarial_holdout`
    is an error (`case_template`): a template sits on one side of the
    train/eval boundary;
  - a template used in `dev` and in `test` or `adversarial_holdout` is a
    warning (`case_template_dev_eval`). The brief names dev and test. The
    validator also warns on dev and adversarial_holdout, the more
    conservative reading, because dev is tuned on and the holdout must not
    be. Benchmark v0's manifest lists the same pairs under
    `case_templates.shared_by_dev_and_an_eval_split`;
  - an example without a template (null or absent) is not compared. Evidence
    sections are not compared yet (§6.3).

  On v0 (2026-10-20) all 188 examples name one of 127 templates. 13 templates
  are shared by dev and a decision split (9 dev/test, 2 dev/holdout) or by
  test and the holdout (2, allowed). That gives 16 `case_template_dev_eval`
  warnings and no error. Whether to move those examples is the benchmark
  owner's call: a warning never edits a label or a split.

### 6.2 Duplicates and contradictions

Questions are compared after `contracts.normalize_text` (NFC, whitespace,
interpuncts) and `casefold()`. Within one task:

- same question and the same remaining input (claim, `fixture_set`,
  `temporal_query`, relevant dates, anchor, facts): a duplicate, or a
  contradiction when the language is the same and `expected` differs (errors);
- same question but a different remaining input: allowed, reported as
  `question_reuse` (warning) so the reuse is deliberate.

The second case is a deliberate reading of the brief. The 제73조 fee question
asked on 2026-10-19 and on 2027-10-01 has two correct answers (06 §4), and one
user question verified against a correct claim and a wrong-article claim (class
B) is two items with two labels. Calling those duplicates or contradictions
would force authors to vary the question text artificially.

### 6.3 Contamination

- Text compared: the normalized question plus the claim text.
- Measure: character 3-grams, Jaccard similarity, threshold 0.85 compared
  exactly in integers (no float rounding at the boundary).
- `train` against `dev`, `test` and `adversarial_holdout`: error. `dev`
  against `test`: warning.
- A prefix filter (grams ordered by global frequency) finds exactly the pairs
  an all-pairs comparison finds; a test checks this against brute force. 4,000
  synthetic template questions took about 1.6 s.
- Pass the train file and the benchmark directory in one run, or the
  cross-split rules have nothing to compare.
  `waymaker_ai.distillation.sft_dataset.run_dataset_validator` does this, and
  the SFT builder adds its own stricter word-3-gram (Jaccard 0.5) leakage guard
  at build time (13 §5).

Template-level separation is checked by id (§6.1), on top of this text check.

Not covered (NOT STARTED): evidence passages are not deduplicated across
splits, only questions and claims; no canary strings or black-box
contamination tests on base models (training-distill.md §4.6).

## 7. Retention and minimisation

- Keep what a label needs and nothing else. An example carries a question, a
  label and references; statute text lives once, in a bundle, with its
  provenance.
- Raw captures stay out of the repository. A bundle records each capture's
  URL, retrieval time and sha256, so the bytes can be re-fetched and checked
  instead of stored.
- Fixtures stay small: metadata-only fixtures where text is not needed, short
  synthetic text where it is.
- Validator reports carry no personal data (§5.1) and no secrets; the
  validator reads no credentials.
- Labels are never deleted silently: a change appends to `revision_history`,
  and a doubtful label becomes `disputed` rather than disappearing.
- When an example is found to contain personal data, it is removed from every
  split and from every SFT file built from it, and any model trained on it is
  listed for retraining (policy only; nothing enforces it yet).

## 8. Not done, and open items

| Item | Status |
|---|---|
| Running the validator over the full benchmark v0 | COMPLETED 2026-10-20: 188 examples, 0 errors, 16 `case_template_dev_eval` warnings |
| Running it over a train split together with the benchmark | NOT STARTED: no train split exists |
| CI job that runs the validator on benchmark v0 | IMPLEMENTED BUT NOT VALIDATED (workflow added 2026-10-20, not yet run on GitHub) |
| Resolving `status_guidance` refs against `data/status-guidance-202609.json` targets (today only the code part is checked against the inventory) | NOT STARTED |
| Template-level split check | COMPLETED, VERIFIED by tests (§6.1). Moving the 16 warned examples is the benchmark owner's decision |
| Evidence-passage deduplication across splits | NOT STARTED |
| PII recall measurement on a realistic corpus; names and addresses | NOT STARTED |
| Teacher-generated data | BLOCKED on counsel's `legal_signoff` |
| 공공누리 AI-training type conditions | RESEARCHED ONLY |
| Retention enforcement (§7) | NOT STARTED |
| One definition of "which files are examples" for the validator, the runner and `sft_dataset.py` | COMPLETED: `waymaker_ai/dataset/layout.py` (§5.1); the three modules import it and `tests/test_dataset_layout.py` checks that they agree |
| A `MANIFEST.json` above the walk root is not read: walking `v0/sub` alone ignores a declaration in `v0/MANIFEST.json`, which the runner (rooted at `v0`) honours | OPEN, by design for now. Validate the benchmark root, as CI does |
