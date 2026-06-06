# AI Answer Regressions, Sub-code Preservation & Public-Safe Source Diagnostics (2026-06)

Focused regression fix following live browser testing. This is **not** a
case-by-case patch: the concrete queries are used as regression tests, while the
fixes harden the generalized answer-shape gate, the deterministic-synthesis
repair, the detected-status projection, and the source-diagnostics rendering
contract.

## Live browser failures observed

1. **H-1 interpreter / employment** — "H-1 비자로 한국에 왔는데 혹시 통역사 일을
   할 수 있을까?" The answer framed paid interpretation under H-1 as a high risk
   of violating activity scope (outside-status activity) merely because it was
   paid, without distinguishing H-1 (Working Holiday) short-term employment from
   ordinary non-work statuses.
2. **H-1 foreigner registration** — "H-1 외국인등록은 언제 해야 하나요?" The
   answer led with source-limitation/uncertainty and gave only vague guidance
   ("예: 90일 이내 등") instead of a clear registration/reporting answer shape.
3. **G-1-5 study/activity** — "G-1-5로 체류 중인데 대학교에 등록하거나 청강하거나
   여름 계절학기를 수강할 수 있나요?" The answer text preserved G-1-5 but the
   public detected-status chip collapsed it to G-1.
4. **Raw developer diagnostics leaking** — the source/status panel exposed raw
   internal codes (`bad_response`, `not_attempted`, `unsupported`,
   `LAW_API_BAD_RESPONSE`, `statute:`/`enforcement_decree:` family dumps,
   `실시간 법령 조회 응답을 파싱하지 못했습니다`, literal `\n` escapes) to normal
   users, even when collapsed under "개발자 진단 정보 보기".

## Why this is not case-by-case

The fixes operate on reusable, visa-code-agnostic layers:

- a **generalized status work-capability model** (`work_authorized` /
  `work_limited` / `work_prohibited` / `unknown`) shared by the issue classifier
  and the answer-shape gate;
- the **issue-type answer-shape gate** (one new generalized detector, not an
  H-1 branch);
- the **deterministic-synthesis repair** (capability-driven posture for any
  work-limited status; richer registration framing for any status);
- the **detected-status projection** (sub-code preservation for any `L-NN-NN`);
- the **source-diagnostics rendering contract** (dev-mode gating for all codes).

## Answer-shape gate improvements

- New shared capability model `status_work_capability(parent_code)` in
  `backend/services/legal_analysis.py` with `_WORK_LIMITED = {"H-1"}` (Korean
  Working Holiday). Paid work on a work-limited status is classified as
  `employment_restriction` only — **not** `outside_status_activity` /
  `work_on_non_work_status`. Work-prohibited statuses (study/visit, e.g. D-2,
  D-4, C-3, D-10) keep their previous outside-status shape.
- New gate detector
  `paid_work_treated_as_outside_status_for_work_permitting_status` in
  `backend/services/answer_shape.py`: for work-restriction / activity-scope
  contracts where the current status may permit work (`work_authorized` /
  `work_limited`), it fails an answer that frames paid work as a high-risk
  outside-status violation **without** the nuance that short-term /
  agreement-limited work may be allowed. It is a structural failure, so it
  triggers deterministic synthesis. Work-prohibited statuses are excluded, so
  honest violation framing for study/visit statuses is preserved.

## Work-limited status reasoning (deterministic synthesis)

For `employment_restriction` on a work-limited status, the repaired answer:

- states paid work is **not** automatically an outside-status violation;
- says short-term work may be allowed within the status purpose and
  nationality-specific agreement limits;
- distinguishes (a) short-term general interpretation/translation support,
  (b) long-term/full-time/professional interpreter employment, (c)
  tourist-guide interpretation / tourist guiding, (d) foreign-language
  teaching/instruction;
- flags the decisive facts: job type, duration, nationality agreement terms,
  domestic license requirements, and main-purpose-of-stay alignment;
- points to 1345 / HiKorea / the competent office as **final confirmation**, not
  the whole answer;
- invents no exact hour limits, penalties, or country-specific rules.

## Registration / reporting answer-shape improvement

The registration deterministic synthesis now leads with practical framing and:

- names the trigger event (entry date or status grant/change date);
- gives the deadline basis (the 90-day stay/registration threshold) **while
  preserving uncertainty** ("정확한 등록 기한과 대상 여부는 … 달라질 수 있으므로");
- names the filing channel (HiKorea / competent immigration office);
- lists the required fact checks (entry date, granted stay period, 90-day
  threshold, address/jurisdiction);
- places the source-limitation note **after** the practical analysis;
- never drifts into study wording (university, credits, D-2/D-4, course,
  summer semester).

## Sub-code preservation

`/api/ask` now derives a **public** detected status from the extracted
immigration facts. When the user explicitly writes a sub-code (e.g. G-1-5), the
response carries `visa_code_detected = "G-1"` (parent, for internal family
lookup) and `visa_sub_code_detected = "G-1-5"` (exact, for public display).
Document **routing** stays payload-only as before — this changes only the public
projection. `ai.html`'s detected-status chip prefers
`visa_sub_code_detected || visa_code_detected`, so the chip shows G-1-5. D-2/D-4
remain comparison statuses (`related_statuses_not_sources`), never the detected
current status.

## Public-safe source diagnostics

- The developer-diagnostics block in both `ai.html` and `index.html` now renders
  **only** when an explicit developer/debug mode is enabled
  (`?debug=1` / `?dev=1`, `localStorage.paradisoDevDiagnostics === '1'`, or
  `window.PARADISO_DEV_DIAGNOSTICS`). The detection uses `typeof` guards so it is
  crash-safe under the headless check harness. By default, normal users never see
  raw codes (`bad_response`, `not_attempted`, `unsupported`, `LAW_API_*`,
  `statute:`/`enforcement_decree:` family dumps).
- The literal escaped-newline bug (`join('\\n')`) is fixed to `join('\n')` in
  both files, so `\n` no longer renders literally inside the diagnostics `<pre>`.
- The visible source panel continues to use the sanitized public projection
  (`public_source_status` labels and the friendly law-status copy); only the
  dev-gated block carries raw codes.

## Tests added

`backend/tests/test_ai_answer_regression_source_subcode_2026_06.py`:

- work-capability model + classifier (H-1 work-limited; D-4 still outside-status);
- gate fails the overbroad H-1 paid-work answer and stays quiet when nuance is
  present / for work-prohibited statuses;
- deterministic-synthesis quality for all three regressions;
- `/api/ask` repair path (mocked LLM) for the H-1 interpreter and registration
  cases, asserting repair + metadata;
- G-1-5 public sub-code metadata from both free-text and explicit payload;
- public source-status projection contains no raw codes for a malformed family;
- static guards that `ai.html` / `index.html` gate the dev block, fix the
  newline, and that the chip prefers the sub-code.

## Validation results

- `python3 -m pytest backend/tests` — 948 passed; only 4 pre-existing,
  unrelated failures in `test_scenario_procedure_variants.py` (idempotency of
  the scenario-variant population scripts against `visa_data.json`, untouched by
  this PR — confirmed failing on the clean tree).
- `node scripts/check_ai_shell_semantics.js` — OK.
- `node scripts/check_i18n.js` — OK.
- `python3 scripts/sync_visa_data.py --check` — OK.
- `python3 -m json.tool` on visa_data.json / backend/data/visas.json /
  doc_master.json — valid.
- `bash scripts/check_repo.sh` — passed.
- `python3 -m py_compile` on the changed backend modules — OK.

## Unresolved risks

- No live browser/API run was performed in this environment; verification is via
  unit/integration tests and static checks only.
- The deadline basis cites the general 90-day registration threshold; exact
  per-status deadlines still depend on official confirmation and are intentionally
  hedged rather than asserted.
- The work-limited set is currently `{"H-1"}`. Other conditional-work statuses
  (e.g. D-10) keep their prior classification to avoid scope creep; they can be
  added to the same model later if desired.
- The dev-diagnostics gate relies on the frontend flag; operators who need raw
  codes must opt in explicitly (documented above).

## Safety note

Paradiso remains a public-source reference tool, not legal advice. The repaired
answers avoid fabricated rules, fees, deadlines, and penalties; they lead with
practical analysis and route final decisions to 1345 / HiKorea / the competent
immigration office. No model/provider policy, law API credentials, manual data,
or static visa-result rendering contract were changed.
