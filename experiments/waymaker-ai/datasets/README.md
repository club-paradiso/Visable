# Waymaker datasets

Benchmark v0 for the Waymaker Legal Intelligence experiment (Mission 001, 2026-10-19,
aligned with the spec rules decided 2026-10-20), plus the evidence it is scored against.

**No item has been reviewed by a person.** `machine_checked` means a label's premises
were checked mechanically (see "Label status" below). It is not a legal review, and
none of these files is a statement about Korean law.

## Layout

| Path | What it is | Provenance |
|---|---|---|
| `registry/law_identity_2026-10-19.json` | Law identity registry: the 22 records of `docs/ai/waymaker-genesis/research-notes/law_identity_seed.json`, in seed order, every seed field unchanged (nulls and `verification_status` kept). | Research seed (law.go.kr public pages read 2026-10-19), sha256 of the seed recorded in `source`. |
| `fixtures/sources/law_go_kr_capture_2026_10_19.json` | Real source bundle (`bundle_version` 2): 15 identities, 506 version rows, 245 provision units (230 articles, 15 heading units), 19 부칙 clauses. | `verified_web`. Parsed offline (`python -I`) from raw law.go.kr captures only. |
| `fixtures/sources/synthetic_adversarial.json` | Fictional source bundle (`bundle_version` 2; 10 identities, all titles marked 가상) for mechanics the real capture cannot exercise. | `synthetic_fixture`, CC0-1.0. |
| `fixtures/sources/synthetic_core.json` | Fictional bundle owned by another component (unit tests). One benchmark item uses it read-only. | `synthetic_fixture`. |
| `benchmark/v0/classification.jsonl` | 91 items: 79 `status_procedure_classification`, 12 `entity_date_extraction`. | Synthetic questions; codes checked against `visa_data.json` (read-only). |
| `benchmark/v0/legal_verification.jsonl` | 58 `citation_verification` items: 23 on the real capture, 34 synthetic, 1 on `synthetic_core`. | Labels written by hand from spec 07. |
| `benchmark/v0/temporal.jsonl` | 28 `temporal_version_selection` items: 18 real (spec 06 §4 and the dev additions), 10 synthetic. | Labels written by hand from spec 06. |
| `benchmark/v0/abstention.jsonl` | 11 `abstention` items (K, L, M and outcome-prediction questions). | Answer behaviour only; no legal rule is asserted. |
| `benchmark/v0/abstention_rubric.json` | One-line definition of every `required_issue_key`. Not an example file. | — |
| `benchmark/v0/MANIFEST.json` | Counts by suite, task, language, split, class, label status; case-template summary (including the templates shared across splits); sha256 of every benchmark file and of the bundles and registry it depends on. | Generated. |

## The real capture bundle

Built only from raw captures of law.go.kr public pages (no Open API key), fetched on
2026-10-19 during the research and verification passes. Every capture is listed in the
bundle's `captures` with its sha256, byte size, URL, request time and HTTP status from
the request logs. The capture files themselves are local research data and are not in
the repository.

* Attribution: 출처: 법제처 국가법령정보센터 (law.go.kr). Statute text is not protected by
  copyright (저작권법 제7조).
* `history_coverage` is `complete` for all 15 identities: each 연혁 list was read back to
  its 제정 row and matched row by row against a second capture from the same day.
  `history_listing` keeps each row's 현행 flag and the 시행예정 icon.
* Provision text exists for: 국적법 244609 and 286415 (complete), 난민법 188376 (complete),
  재외동포법 268553 (complete), 외국인고용법 286817 at 2026-12-10 (complete) and 2027-06-10
  (제22조의2 and 제25조 only), 재외동포법 시행령 284843 and 난민법 시행령 273705 (articles,
  partial), and 출입국관리법 시행규칙 제73조 for (289833, 2026-09-15) and (289833, 2027-09-16).
  Every other version is a history row only (`not_parsed`).
* Left out because the captures do not support them reliably: article text of 출입국관리법
  and its 시행령 (only amendment markers were kept), every 별표/별지, and the bodies of the
  other 시행령/시행규칙 (deleted after extraction during a disk-full incident).
* The bundle's `notes` list every value that does not come straight from a capture.
* `structure_complete` (added 2026-10-20) is set on every provision unit. It is `true` when
  the unit holds the article's whole printed 항/호 structure: the lead text, every printed 항
  under `paragraphs` and every printed 호 under `items`, with 목 kept verbatim inside their
  호. Only then is a cited 항/호 that the unit lacks an authoritative absence (spec 07 §3 L3).
  It is `false` on the 15 heading units and on 난민법 188376 제33조, where the parser merged ②
  into the text of ①. The value was decided from the bundle text itself (an audit of circled
  paragraph markers, item markers and "다음 각 호/목" lead-ins), not by re-reading raw pages.
  A second, independent audit on 2026-10-20 (paragraph numbering, item numbering per 항,
  lead-ins without items and items without lead-ins) agreed on 240 of the 245 units. Its
  heuristics flagged the other 5, which were read by hand and are whole as printed: dates such
  as "2007. 10. 15." read as item markers, the lead-in "다음과 같다" of 난민법 제2조, and
  재외동포법 268553 제7조, whose ① still prints the deleted items "1. 삭제" and "2. 삭제".
  It is independent of `parse_status`, which says whether the version holds every article:
  출입국관리법 시행규칙 제73조 is `structure_complete` at both 289833 rows although the
  version is `partial`.
* A version's 부칙 counts as read when `has_transitional_provisions` is `true` or `false`;
  `null` means not read (or printed with clauses omitted, as in 재외동포법 268553).

## The synthetic bundle

`synthetic_adversarial.json` holds fictional laws only. Real status codes (E-7, E-7-1)
appear only as scope labels on fictional rules. It covers: decoy and shared short titles
(A), heading units that share an article key and an invented article (B), wrong content
(C), a four-version history with a pending version and a deferred provision (D/E),
transitional and application 부칙 (F), a renamed law under a current-titles-only index and
a repealed law (G), one scripted fault per failure kind (H), parent-only, explicit-subcode
and all-subcodes scopes plus visa-scope and stay-scope rules (I), manual editions older and
newer than a law version (J) and instruction-like text inside a provision (N).

Its title index is `partial` on purpose (scenario G). Authoritative title absence
(`source_not_found`) therefore needs a complete index, and the single item that tests it
uses `synthetic_core`. Every article unit is `structure_complete: true` (each fictional
article is complete as written); heading units are `false`.

## How labels were written

* Classification: the procedure label is the procedure the user asks about, a linguistic
  reading of the question, not a judgement that the procedure applies or is available.
  For "from A to B" questions, `status_code`/`subcode` name the target and
  `current_status`/`target_status` give the codes as written. 2-segment codes are parents,
  3+-segment codes (including `*-T` and letter-suffixed codes such as E-7-4R, F-2-7S,
  D-4-2K) are subcodes under their parent. Ambiguous aliases (학생비자, 취업비자, 배우자 비자)
  get no code and `needs_clarification: true`.
* Verification and temporal labels were applied by hand from specs 07 and 06. They were
  **not** produced by running `waymaker_ai.legal.verification` or `waymaker_ai.legal.temporal`,
  so a disagreement with the implementation is a finding, not a label to change.
  `layer_codes` lists only the layers the spec determines for that input.
* On 2026-10-20 every citation and temporal label was re-read against the rules the specs
  mark "decided 2026-10-20". Each changed label has `revision` + 1 and a `revision_history`
  entry naming the rule. In short:
  * **Blocked layers** (07 §3): after L1 finds no identity, L2, L3, L4 and L6 are labelled
    `not_checked` (they carry L1's outcome); after L2 finds no candidate, L3, L4 and L6; after
    L3 finds no provision, L4. L5 is left unlabelled in blocked cases, because 07 does not
    settle whether guidance-only support or the no-quote/no-number rule applies.
    `ver-syn-shared-short-title` is therefore `human_review_required`, not
    `verification_unavailable`.
  * **L7 without a topic** is `not_checked`, never `no_conflict_detected`. Positive controls
    still roll up to `verified`, because `not_applicable` counts as present.
  * **L3 checks the candidate version.** Items where L2 attributes the quote to another
    version now label L3 on the candidate (`ver-real-nationality-pending-quote`:
    `citation_not_found`, because 244609 제6조 is `structure_complete` and has no 제3항), and L4
    on the attributed version.
  * **L3 sub-unit absence** needs `structure_complete`: `ver-real-r73-item4-absent` keeps
    `citation_not_found`.
  * **L7 with both rules**: `ver-syn-manual-conflicts-and-predates` is `contradictory_evidence`.
    `ver-syn-manual-predates-law-version` keeps `manual_predates_law_change`. 제10조 is not in
    the known `changed_provisions` of A1-0003 or A1-0002, but A1-0001's list is unknown, so the
    conservative fallback (C's effective date) applies.
  * **06 §3 step 9 counts the primary candidate only**: `tmp-syn-diverging-anchors` now forbids
    `transitional_provisions_unreviewed`.
  * **L1 rows returned but none exact** (`source_ambiguous`) has no item. A bundle title index
    answers a near title with no rows (NOT_FOUND), so `ver-core-near-title-complete-index`
    stays `source_not_found` and the partial-index items stay `historical_lookup_required`.
* Abstention items describe answer behaviour only (`required_issue_keys`,
  `forbidden_assertions`). They assert no legal rule.

## Label status

| Suite | `machine_checked` means |
|---|---|
| classification | Every labelled code exists in `visa_data.json`; the status is a 2-segment parent; the subcode is listed under it (or shares its first two segments); every code is written in the question; `not_status_tokens` occur in the question; a status-guidance keyword for the procedure occurs in the question; alias candidates match status-guidance. Items whose wording has no keyword (zh, ja, vi, ru) and all date-extraction items (roles are a reading, not checkable) are `unreviewed`. |
| legal_verification | The premises of the label were recomputed from the bundle: which identity the title resolves to (or which fault fires), the candidate version on the anchor date, which versions contain the quoted words, whether the cited 항/호 exists and whether the provision is `structure_complete`, which numbers occur, which 부칙 clause reaches the article and whether the 부칙 was read, which guidance exists. The expected codes themselves follow the spec by hand. |
| temporal | The ten steps of spec 06 §3 were re-applied to the bundle's versions by an independent throwaway script; candidate keys matched exactly, every labelled warning was produced and no forbidden warning was. |
| abstention | Always `unreviewed`. |

## Splits and case templates

`adversarial_holdout` holds every item with an adversarial class (including the K, L and M
abstention items, because the validator requires adversarial items to sit in `test` or
`adversarial_holdout`). Every other item created on 2026-10-19 is `dev` when
`int(sha256(id)[:8], 16) % 10 < 4`, otherwise `test`. The 13 items created on 2026-10-20
(`ver-dev-*`, `tmp-dev-*`) were written for `dev`. They are non-adversarial positive controls and
ordinary negatives on the existing bundles: in-force quotes with matching numbers, a claimed
heading, numbers without a quote, a `같은 법` citation resolved through `input.claim.context_title`,
a valid article without a quote, and temporal queries on histories that are complete in the
bundle. Each has its own case template, and no `test` or `adversarial_holdout` item shares it.
`dev` now holds 10 citation and 6 temporal items. There is no `train` split in v0.

Every item has `scenario.case_template`. Items share a template when one was written as a
variant of the other: a translation or paraphrase of the same case, the same case on another
date or anchor, or the same claim with a different citation, quote or scope. Slot-filled
classification questions with a different code or procedure are different cases. Because v0
was split per item before templates existed, 11 templates span `dev` and an evaluation split
(listed in `MANIFEST.json` under `case_templates.shared_by_dev_and_an_eval_split`, and reported
by the validator as `case_template_dev_eval` warnings). Two of them are legal:
`tpl-cv-syn-residence-report-deadline` (`ver-syn-short-title-pending-change` in dev,
`ver-syn-later-amendment-past-event` in the holdout) and `tpl-tv-ewa-286817-rows`
(`tmp-real-ewa-art25-after-deferral` in dev, three holdout items). They were not re-split,
because moving items would change the scored test and holdout sets. Moving the dev members to
`test` is the obvious fix for v1. The templates shared only by `test` and
`adversarial_holdout` are positive controls paired with their adversarial variants. Neither
split is tuned on.

## Known gaps and spec ambiguities

The four ambiguities in `docs/ai/waymaker-genesis/research-notes/adjudication-log.md` (A1–A4)
are resolved by the 2026-10-20 rules (see "How labels were written"). What remains:

* Version attribution when the quoted words occur in the candidate and in another version
  is read as "attributed to the candidate" (e.g. `ver-real-nationality-unchanged-numbers`).
* L6 codes for `not_applicable`, L1–L4 codes for a claim without citations, and L5 in a
  blocked claim without guidance are not named by the spec and are never labelled.
* L4 after a sub-unit absence in the candidate is not labelled when the quote sits in another
  (attributed) version (`ver-real-nationality-pending-quote`). It is unclear whether that
  absence blocks L4.
* After a repeal at L1 (`ver-syn-repealed-law-current`), 07 §3 L2 does not say what L2
  reports, so L2 is unlabelled. L3, L4 and L6 are `not_checked`.
* 07 §3 L7's fallback "when `changed_provisions` is unknown" does not say whose list is meant.
  The labels apply it whenever the walk back from C reaches a version whose list is unknown
  before one that names the provision (`ver-syn-manual-predates-law-version`). There the
  unknown list belongs to the enactment (제정, A1-0001). Reading an enactment as the last
  change of every provision it holds would end the walk there and give `pass`. That reading
  is less conservative and was not used.
* Not exercised by any item, because the bundle format cannot express it or no item was
  written for it in the holdout:
  * L1 "rows returned, none exact". The bundles are exact title indexes (doc 05, component
    B: exact-title resolution over official, former and short titles). A near title gets no
    rows, so it is NOT_FOUND, and coverage then decides between `source_not_found` and
    `historical_lookup_required`. Neither the bundle schema nor the adapter protocol states
    this outright.
  * L2 `version_history_incomplete` from a partial history. Only SYN-ADV-ACT-07 is partial,
    and only a temporal item uses it.
  * The article key matching a paragraph-level deferral in 06 §3 step 8 (외국인고용법 276857
    `제4조제4항` for a query on `제4조`). 276857 is the only version with a paragraph-level
    entry. A dev item on it would give away the candidate (276857 on 2026-10-19, 286817
    pending) that the holdout item `tmp-real-ewa-art25-question-date` tests, so none was
    written. A synthetic paragraph-level deferral in the holdout is the v1 fix.
  * 07 §3 L6's unread-부칙 rule on a claim. Only `ver-real-decree-cited-for-rule` (blocked at
    L3) and `ver-syn-fault-addenda-timeout` (also faulted) reach a version with
    `has_transitional_provisions: null`. A claim on 재외동포법 268553 (부칙 printed with
    clauses omitted) would exercise it. It belongs in the holdout as class F, not in dev.
* `synthetic_core.json` is owned elsewhere. Only 2 of its 34 provisions carry
  `structure_complete`, so a cited sub-unit missing from any other provision there is
  `unavailable`, not `citation_not_found`. The one item on that bundle never reaches L3.

## Checking

```bash
cd experiments/waymaker-ai
python -m waymaker_ai.dataset datasets/benchmark/v0 --registry datasets/registry   # dataset validator
python -m pytest -q -p no:cacheprovider tests                                      # package tests (offline)
```
