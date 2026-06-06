# Law Open Data Precedent Source-Family Scaffold (2026-06)

## Goal

Extend Paradiso's generalized official-evidence architecture toward the
**precedent-related** Law Open Data source families so the system can *later*
use court precedents, administrative-appeal decisions, legal interpretations,
and constitutional-court decisions in answers and general search — **without
fabricated citations and without leaking raw diagnostics**.

The four families scaffolded here:

| family id | Korean | English |
|-----------|--------|---------|
| `precedent` | 판례 | court precedent |
| `administrative_appeal` | 행정심판례 | administrative appeal decision |
| `legal_interpretation` | 법령해석례 | legal interpretation case |
| `constitutional_decision` | 헌재결정례 | Constitutional Court decision |

## Why this is scaffold-first, not fake live citation

The existing tooling (`law_tools`) reliably retrieves the **statute family**
(`target=law`), administrative rules (`target=admrul`), and legal terms
(`target=lstrm`). The four families above were named in the ontology but had no
adapter, no normalizer, and were never routed.

This PR adds the *interfaces, normalizers, routing, and a precedent
list-search builder* — but it deliberately does **not** claim production live
precedent search. Only the precedent **list** target (`prec`) is documented and
scaffolded; the **body/detail** lookup and the other three families' official
targets are not verified yet. Presenting an unverified adapter as "live" would
risk inventing case law, which is the single worst failure mode for a legal
assistant. So the families are reported as `scaffold_only` and surface to users
as public-safe "not connected yet / currently unavailable" — never as fake
authority.

## Credential convention — `LAW_API_OC`

`LAW_API_OC` is the **canonical** Law Open Data credential (the `OC` query
parameter on `law.go.kr` / `open.law.go.kr` DRF endpoints). It is already
configured in Railway by the project owner.

* `grounding_config.GroundingConfig` resolves `law_api_credential` as
  `LAW_API_OC` first, with the legacy `LAW_API_KEY` only as a backward-compatible
  fallback (a non-secret `LAW_API_OC_RECOMMENDED` advisory is emitted when only
  the legacy key is set). No new env var was introduced.
* The value is **never** printed, logged, committed, returned in URLs, or placed
  in any public payload. URL sanitization (`law_tools._sanitize_url`) and the
  HTTP transport are reused by the precedent scaffold so secret-redaction lives
  in exactly one place.
* Local Codespaces need not have `LAW_API_OC`. When it is absent the adapter
  returns a public-safe `not_configured` / `unavailable` envelope and never
  crashes. **No test requires a live credential** — everything is fixture/mock
  driven.

## Precedent `target=prec` list-search scaffold

`precedent_sources.search_precedents()` builds the documented list-search
request:

```
GET {host}/DRF/lawSearch.do?OC=<LAW_API_OC>&target=prec&type=JSON&query=<q>&display=<n>
```

It reuses the same injectable transport seam as `law_tools`, so it is fully
mockable and never needs the network in CI. It returns the normalized evidence
envelope described below.

`scripts/capture_law_api_shape.py` now maps `precedent → prec` so an operator
**with** `LAW_API_OC` can optionally capture the *sanitized* response shape
(`--family precedent`). With no credential the capture returns `not_configured`
and makes no network call. The other three families keep `None` targets — we do
not guess unconfirmed official targets.

> **Important:** `search_precedents()` is intentionally **not** wired into
> `law_tools.retrieve_official_source_family()` in this PR. That function still
> returns `unsupported` for `precedent`, so the production answer fan-out never
> silently fires an unverified live precedent call. Live wiring is a follow-up.

## Two-step list / body design

Court precedent retrieval is two steps and the normalizer keeps them distinct
via `resultKind`:

1. **list search** (`list_result`) — `lawSearch.do?target=prec` yields candidate
   cases with stable identifiers (판례일련번호, 사건번호, 법원명, 선고일자).
   A list result is **contextual** at best — it is a pointer to a case, never a
   verbatim quote source (`quoteSafe: false`).
2. **body / detail lookup** (`body_result`) — would use the list result's stable
   identifiers against `lawService.do?target=prec&ID=…` to fetch 판시사항 /
   판결요지 / 판례내용. Only a body result with stable identity *and* quotable
   text is graded `direct` (`quoteSafe: true`).

Body lookup is **not implemented** here; the normalizer supports the
`body_result` shape (and tests exercise it from a fixture) so the follow-up
adapter has a verified target to fill in.

## Source-family routing rules

Routing lives in one place (`evidence_ontology.SOURCE_FAMILY_ROUTING`,
consumed by `legal_analysis.build_generalized_source_plan`). Precedent-family
sources are routed **only for legally relevant issue types**, detected by
high-precision signals so ordinary questions never over-query case law.

Three adjudicative-leaning issue dimensions were added (detected last, after the
substantive procedure/activity issues keep priority):

* `denial_revocation_or_remedy` → `manual, statute, decree, rule, administrative_appeal, precedent, legal_interpretation`
  (불허/거부/취소/철회/출국명령/강제퇴거/행정심판/이의신청/불복/구제; denial/refusal/revocation/deportation/appeal/remedy/sanction)
* `constitutional_or_fundamental_rights` → `statute, decree, constitutional_decision, precedent, legal_interpretation`
  (헌법/위헌/기본권/평등권/적법절차/헌재; constitutional/unconstitutional/fundamental right/due process/equal protection)
* `discretionary_or_ambiguous_interpretation` → `statute, decree, rule, legal_interpretation, administrative_appeal, precedent`
  (법령해석/유권해석/해석상/재량/모호; legal interpretation/discretion/ambiguous)

Existing dimensions were also enriched: `overstay_or_risk` and
`nationality_or_refugee_context` now include `precedent` (deportation/sanction
and refugee/humanitarian procedural disputes are adjudicative).

**Not routed to case law:** simple document checklists, foreigner-registration
timing, routine extension document inquiries, ordinary work questions
(e.g. an H-1 interpreter side-job) — unless the user raises refusal, violation,
sanction, or remedy.

## Normalized evidence-item shape

Each precedent-family result normalizes into one public-safe evidence item
(`precedent_sources.build_source_family_evidence_item`):

```
{
  sourceFamily, resultKind, citationGrade, publicStatus, quoteSafe,
  title?, sourceName?, caseNumber?, decisionNumber?, serialNumber?,
  decisionDate?, courtOrAgency?, issueTags?, url?, snippet?, holdingSummary?,
  internalStatus?, retrievedAt?, supports?, limitations?
}
```

* `resultKind` ∈ `list_result | body_result | fixture | unavailable`
* `citationGrade` ∈ `direct | contextual | background | unavailable`
* `publicStatus` ∈ `available | temporarily_unavailable | unavailable | not_relevant`

**Citation grading rules**

* A precedent citation needs a case number (or stable decision identifier) **and**
  a court/source identity. Administrative-appeal needs a decision number + agency;
  constitutional needs a decision/case number + institution; legal interpretation
  needs an issuing body (+ stable id when available).
* A `list_result` with full identity is **contextual**, not direct.
* A `body_result` with full identity **and** quotable text is **direct**.
* Missing identity downgrades to **background**; unidentified text is **never**
  citation-grade. `internalStatus` is the only raw field and is internal-only.

## Citation verifier behavior

`citation_verifier.verify_case_decision_citations(text, evidence_items)` adds
adjudicative-citation verification on top of the existing statute-citation
checks:

* A cited **case/decision number** that maps to no evidence item →
  `unverified_fabricated` → **FAIL** (`FABRICATED_CASE_CITATION`).
* An **authority claim** for a family (판례/대법원 판시, 헌재 결정, 재결,
  법령해석례) with no retrieved evidence of that family →
  `unsupported_authority_claim` → **FAIL**.
* A **binding/direct** claim ("확립된 판례…", "반드시 취소") backed only by
  *contextual* evidence → `overclaimed_contextual` → **FAIL**.
* A **direct quotation** attributed to a decision that does not match a
  `quoteSafe` snippet/holding → `quote_mismatch` → **FAIL**.
* Plain procedure mentions ("행정심판을 청구할 수 있습니다") are **not** authority
  claims and never fail. With `evidence_items=None` the verifier runs in
  extract-only mode (never fails) for callers without an evidence pack.

This is available and unit-tested now; wiring it into the live answer repair
path is a follow-up (see below).

## Public-safe unavailable status

Routed-but-unwired precedent families surface to users as public-safe
"unavailable", never as raw codes:

* The internal status map (`source_grounding._INTERNAL_STATUS_MAP`) maps
  `unsupported` / `planned_not_wired` / `scaffold_only` → `not_configured` →
  public `unavailable`. The public projection (`project_public_source_status`)
  was verified to leak none of: `unsupported`, `not_attempted`, `bad_response`,
  `planned_not_wired`, `scaffold_only`, `parse_error`, `official_error`, raw
  bodies, or raw JSON/XML/HTML.
* Per-family public wording is available via
  `evidence_ontology.source_family_public_unavailable_label`, e.g.
  *"판례 직접 근거는 아직 연결되지 않았습니다."*,
  *"행정심판례 직접 근거는 현재 사용할 수 없습니다."* Raw diagnostics stay in
  `developer_source_diagnostics` (internal only).

## Live adapter status per family

| family | list target | live adapter status | notes |
|--------|-------------|---------------------|-------|
| `precedent` | `prec` (confirmed) | `scaffold_only` | list-search builder + list/body normalizers + capture hook; body lookup + live wiring are follow-ups |
| `administrative_appeal` | none (unconfirmed) | `scaffold_only` | fixture normalizer only; official target to be verified |
| `legal_interpretation` | none (unconfirmed) | `scaffold_only` | fixture normalizer only; official target to be verified |
| `constitutional_decision` | none (unconfirmed) | `scaffold_only` | fixture normalizer only; official target to be verified |

The richer `live_adapter_status` (`wired | scaffold_only | not_configured |
temporarily_unavailable`) is **additive**: the coarse
`source_family_support_status` contract (`wired | planned_not_wired`) is
unchanged, and `retrieve_official_source_family` still reports `unsupported` for
these families, so existing behavior and tests are preserved.

## Tests added

`backend/tests/test_law_open_data_precedent_scaffold.py` (47 tests) +
`backend/tests/fixtures/precedent_sources/` scaffold fixtures cover:

* `LAW_API_OC` canonical credential precedence; scaffold never exposes the OC.
* source-family definitions + `scaffold_only` live status for the four families;
  `support_status` contract preserved.
* `precedent` uses `target=prec`; the other three remain unconfirmed/scaffold;
  capture script target mapping; `retrieve_official_source_family` keeps
  precedent `unsupported`.
* routing: denial/remedy → precedent + appeal; constitutional → constitutional
  decision; ambiguous → legal interpretation; **document checklist / routine
  H-1 interpreter / registration do not route case law**; C-3 violation/remedy
  routes statute + appeal + precedent; every issue still routes.
* fixture normalizers for all four families (list + precedent body), with
  list=contextual / body=direct grading; unidentified text → background.
* official error + HTML responses → public-safe unavailable, no raw leak;
  not_configured / timeout states; public projection hides raw codes.
* citation verifier: fabricated precedent/appeal/constitutional/interpretation
  citations fail; fixture-backed citations pass; quote mismatch fails; quote
  match passes; contextual-only cannot support binding wording; procedure
  mentions not flagged; invented case in a model-style answer is rejected.

The full backend suite remains green except 4 **pre-existing**
`visa_data.json` population-script checks in
`test_scenario_procedure_variants.py` (unrelated to this PR — they fail
identically on `main`).

## Known limitations

* `precedent` body lookup is **not** implemented; only the list-search builder +
  normalizer shape exist.
* `target=prec` and the body shape are **documented hints**, not yet verified
  against the live API from this environment.
* `administrative_appeal` / `legal_interpretation` / `constitutional_decision`
  official targets and field names are **unconfirmed**; their fixtures are
  conservative synthetic scaffolds.
* The hardened case/decision citation verifier is available and unit-tested but
  **not yet wired** into the live answer repair/rejection path.
* The public source panel still shows the family id for routed-but-unwired
  families; localized per-family labels exist but full UI wiring is a follow-up.

## Follow-up PRs

1. **Official target verification + live shape capture** — confirm `target=prec`
   and the body shape; verify/identify the official targets for 행정심판례 /
   법령해석례 / 헌재결정례; capture sanitized fixtures.
2. **Precedent body-lookup adapter** — `lawService.do?target=prec&ID=…` two-step
   retrieval using list identifiers; promote verified body results to `direct`.
3. **Live adapters + answer integration** — wire the verified adapters into the
   retrieval fan-out and the answer pipeline (confirmed rule → analogical
   decision → source limitation → next action), with the citation verifier
   rejecting/repairing invented case law in generated answers.
4. **General search UI filters + ranking** — 법령 / 판례 / 재결 / 해석례 filters
   and result ranking, with localized per-family source-status labels.

## Safety note

* No invented precedents, case numbers, decision dates, courts, agencies,
  holdings, or citations. A case/decision is cited only when it maps to a
  normalized evidence item; the verifier fails fabricated or unidentified
  citations.
* Unofficial blogs / law-firm summaries / AI summaries are **not** legal
  authority; the blog `target=prec` note is treated as an implementation hint
  only. The official Open API guide and captured shapes are authoritative.
* No live external API is required in CI; all tests use fixtures/mocks.
* `LAW_API_OC` is never printed, logged, or committed; raw API failure strings
  and response bodies never reach user-facing UI or answers.
