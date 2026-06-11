# Regression parity notes (2026-06-11)

Method: every existing validation script that touches the render path was run twice —
on a pristine `git worktree` of HEAD (`6dbe792`, = origin/main) and on this working
tree — and the FAIL lines were diffed.

| Script | HEAD (pristine) | This branch | Verdict |
| --- | --- | --- | --- |
| `audits/browser-document-qa/check_document_taxonomy.js` | PASS | PASS | no regression |
| `audits/post-merge-hotfix/check_rendered_document_duplicates.js` | PASS (0 unresolved) | PASS (0 unresolved) | no regression |
| `scripts/check_exact_code_search.js` | 16 passed / 1 failed (D-2 golden path) | identical FAIL list (diff empty) | pre-existing on main |
| `scripts/check_static_visa_result_cards.js` | failed (getProcedure structured-docs merge) | identical FAIL list (diff empty) | pre-existing on main |
| `scripts/check_placeholder_suppression.js` | 14 passed / 5 failed (chained meta-checks) | identical FAIL list (diff empty) | pre-existing on main |
| `scripts/check_deadline_helpers.js` | PASS (16 checks) | PASS | no regression |

Regression scripts named in the task but NOT present in the repo (their PRs are unmerged):

- `audits/terminology-normalization/check_terminology_labels.js` — does not exist
  (branch `fix/document-terminology-and-fee-labels` never landed).
- `audits/fee-label-cleanup/check_fee_labels.js` — does not exist (same).

Carry-forward protection applied to the NEW surfaces instead:
- `scripts/check_f4_route_guide.mjs` forbids any unqualified `수수료` in F-4 data/UI
  and pins the exact wording `미국 여권 기준 사증 수수료 USD 45(공관 기준 확인 필요)`.
- `scripts/check_short_stay_rules.mjs` forbids weak/guarantee wording and verifies the
  deterministic source-list phrasing.
- New content uses canonical labels only (`재외동포 통합신청서(별지 제1호서식)`,
  `표준규격사진 1매`, `체류지 입증서류`, `여권 및 사본`, `HiKorea`).

Known environment artifact (NOT a regression): one `console.error
ERR_CERT_AUTHORITY_INVALID` at page load — the pre-existing backend-first data fetch
(`API_BASE/api/visas`, index.html:17607) is blocked by the sandbox TLS proxy and the
page falls back to static `visa_data.json` as designed.
