# 06 — Temporal law and source identity (normative)

Status: identity model and candidate-version resolver are **IMPLEMENTED BUT NOT
VALIDATED** against production traffic. Code:
`experiments/waymaker-ai/waymaker_ai/legal/temporal.py` and `identity.py`. The
facts about current identities come from law.go.kr public pages read on
2026-10-19, listed in [04 §identities](04-official-api-capability-matrix.md).

## 1. Identity

| Concept | Field | Official source field | Rule |
|---|---|---|---|
| Lineage | `SourceIdentity.stable_id` | 법령ID (e.g. 출입국관리법 `001707`), 행정규칙ID | Survives amendments and renames. The **only** identity. |
| Version | `SourceVersion.key` = `(version_id, effective_date)` | 법령일련번호 (MST / lsiSeq) + 시행일자 | One 법령일련번호 can appear under several 시행일자. law.go.kr lists 출입국관리법 시행규칙 `289833` at 2026-09-15 and again at 2027-09-16 (제73조). |
| Deferred provision | `SourceVersion.provision_effective_dates` | 조문시행일자 in the article JSON; inline "[시행일: …]" markers | Used when a deferred provision has no separate history row (외국인고용법 제4조제4항). |
| Title | `official_title`, `former_titles`, `short_titles` | 법령명한글, 법령명약칭, 제명변경여부 | A title is never a key. Matching is exact after `compact()` normalization. |
| Promulgation | `promulgation_date`, `promulgation_no` | 공포일자, 공포번호 | Kept separate from the effective date at every stage. The backend merges the two into one `version_or_date` field (`evidence_ontology.py:291-293`); WLIE keeps them apart. |
| Provenance | `provenance`, `retrieved_at`, `content_sha256`, `parse_status` | — | Every record states how it was obtained. Synthetic fixtures are typed `synthetic_fixture` and cannot reach users. |

Renamed, wholly amended, repealed and re-enacted laws are handled
conservatively:
* A 전부개정 keeps its 법령ID. Article numbers may change between versions, so
  L3 reports the other version that contains a missing article.
* A title missing from a current-title index is
  `historical_lookup_required`, not "never existed".
* After a repeal, the version that applies on the anchor date is the repeal, and
  the resolver returns no candidate together with the warning
  `source_repealed_before_anchor`.

## 2. Dates

The resolver needs to know which date the question turns on. `RelevantDates`
holds the question date, conduct date, application date, filing date, decision
date, departure date, return date, stay-expiry date and manual edition date. The
caller selects an `AnchorKind` from the issue type. The resolver never assumes
that current law governs a past event, and it never picks the anchor itself.

## 3. Candidate selection: `select_candidate_versions`

Inputs: the versions of one identity (from `list_versions`), the lookup result
for that history, `RelevantDates`, the primary anchor, optional secondary anchors,
an optional provision article key, and the question date.

1. History lookup failed: no candidates, `version_history_unavailable`.
2. Anchor missing, or its date not given: no candidates, `anchor_missing`.
3. The effective date of a version *for the provision* is
   `effective_date_for(provision_key)`.
4. The candidate is the version with the latest effective date ≤ anchor date.
   Ties on the same date (which should not happen) are kept as several
   candidates and add `anchors_select_different_versions`.
5. No version qualifies: no candidates, `anchor_before_known_history`. This
   happens when the earliest loaded version is later than the anchor; it never
   implies the law did not exist.
6. The candidate is a repeal: no candidates, `source_repealed_before_anchor`.
7. Any version with an effective date after the anchor date, whose
   `changed_provisions` includes the provision or is unknown (`None`), adds
   `future_version_pending`. **With no provision named, every later version
   counts.** The detail lists the pending version keys and their dates.
8. The candidate has an entry for the provision in `provision_effective_dates`
   whose date differs from its own effective date: add
   `provision_effective_date_differs`. The provision may be named at article
   level (`제4조`) or below it (`제4조제4항`). An exact key is matched first.
   An article key also matches entries for its own paragraphs, because a
   deferred paragraph means the article's text changes on that date.
9. The **primary** candidate's `has_transitional_provisions` is `None` (부칙
   not read) or `True`: add `transitional_provisions_unreviewed`. The resolver
   never applies a transitional clause itself. Secondary-anchor candidates are
   reported but do not add this warning.
10. A secondary anchor that selects a different version: add
    `anchors_select_different_versions` and append that version after the
    primary candidate.

The result is always `determination = "candidate_only"`. Deciding which version
governs in law depends on the issue, transitional rules, procedural timing and
exceptions. That decision belongs to L6 review and to people, not to this
function.

## 4. Real cases the benchmark uses (as captured 2026-10-19)

| Case | Facts (law.go.kr) | Expected resolver behaviour |
|---|---|---|
| 시행규칙 제73조 (수수료의 납부방법) | 법무부령 제1125호, 공포 2026-09-15. The rule takes effect on that date, but per 부칙 제1조 제73조 takes effect on 2027-09-16. Two history rows share 289833. | Anchor 2026-10-19: candidate (289833, 2026-09-15) with `future_version_pending`. Anchor 2027-10-01: candidate (289833, 2027-09-16). |
| 출입국관리법 | Current 290729 (법률 제21857호, 공포 2026-08-04, 시행 2026-10-02) | An anchor before 2026-10-02 must not select 290729 |
| 국적법 | Current 244609 (시행 2022-10-01). Pending 286415, 시행 2026-12-03 | Anchor 2026-10-19: 244609 + `future_version_pending` |
| 외국인고용법 | Current 276857. Pending 286817 with effective dates 2026-12-10 and 2027-06-10 (제22조의2, 제25조 on 2027-06-10) | Provision-level dates differ, so the pending warning depends on the provision |

## 5. What the existing backend does instead

The backend sends no `efYd`, uses no history target and reads no 부칙. It keeps
the promulgation date and the effective date separate only in its first
normalization step. `/api/legal/laws/search` returns `lifecycleStatus: ""`
(observed live 2026-10-19). WLIE's resolver needs the official `eflaw`,
`lsHistory` and `lsJoHstInf` families listed in [04](04-official-api-capability-matrix.md).
Wiring them into the backend client is Mission 002 work
([17](17-mission-002-plan.md)).
