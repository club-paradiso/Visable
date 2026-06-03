# AI Answer Shell — Source Semantics Alignment (2026-05)

A frontend pass that aligns the **AI answer UI shell** (ai.html) with the
answer-quality metadata shipped in PR #256. PR #256 improved the answer *body*
and added the answer-quality contract; this PR fixes the *shell* around it —
the source chips, the source/status panel, the warnings, and the footer.

Suggested branch: `fix/ai-answer-shell-source-semantics`.

This is **not** a backend answer-quality PR, **not** a model-provider PR, **not**
a route-wizard PR, **not** docs-only.

---

## 1. Purpose

After PR #256 the answer body reads well, but the surrounding shell still
mislabeled sources and repeated warnings. This pass makes the shell honest:
related comparison statuses are not shown as direct manual sources, a compact
answer-basis row reflects `answer_quality_mode`, the law-unavailable state reads
as a supporting-source limitation rather than a whole-answer failure, warnings
are de-duplicated, and the English-mode footer no longer leaks Korean.

---

## 2. User-observed UI mismatch

Question:

> Can I take summer semester course in Korean universities even though I have a
> H-1 visa?

The answer body was readable, but the shell showed:

* `Manual: H-1`, `Manual: D-2`, `Manual: D-4` — as if all three were direct
  manual sources (D-2 / D-4 are related study statuses to verify, not source
  grounding for whether H-1 permits a summer semester);
* `Legal citation verification: Needs review (Law source unavailable)` too
  prominently, disconnected from the answer-quality mode;
* three near-identical caution blocks (source panel, generic-AI warning, footer);
* a Korean footer disclaimer (`본 서비스는 공개 법령·매뉴얼 기반…`) in English mode.

---

## 3. Answer body vs answer shell

* **Answer body** (PR #256): the model's text and the answer-quality contract
  that shapes it. Already improved.
* **Answer shell** (this PR): the chips above the answer, the source/status
  panel, the warning blocks, and the footer. These are rendered by ai.html and
  were still using a naive "every visa code in the text is a Manual source"
  heuristic and repeated disclaimers.

The shell now consumes the PR #256 metadata
(`answer_quality_mode`, `related_statuses_not_sources`, `visa_code_detected`,
`grounding_used`) so the UI matches the answer's actual basis.

---

## 4. Source chip semantics

`generateBadges()` now distinguishes:

| Chip | When | Label (en / ko) | Class |
| --- | --- | --- | --- |
| **Checked status** | the detected status, answer not manual-grounded | `Checked status` / `확인한 체류자격` | `bdg-checked` |
| **Manual source** | the detected status, answer manual-grounded (`grounding_used`) | `Manual source` / `매뉴얼 근거` | `bdg-visa` |
| **Related status to verify** | code is in `related_statuses_not_sources`, or any other code mentioned in the answer | `Related status to verify` / `함께 확인할 관련 체류자격` | `bdg-related` |

For the H-1 study question: H-1 → **Checked status** (not Manual, since the
answer is not grounded), D-2 / D-4 → **Related status to verify** chips. They
carry `data-chip-kind="checked"` / `"related"` for testability and use visually
distinct styling. Four-language labels (ko / en / zh / zhHant) are provided via a
new `tt()` helper.

---

## 5. Answer-basis row behavior

A compact **Answer basis** row driven by `answer_quality_mode` is shown first in
the source panel:

| Mode | en label | ko label |
| --- | --- | --- |
| `source_confirmed` | Source-confirmed manual guidance | 공식 매뉴얼 근거 확인 |
| `source_assisted` | Source-assisted guidance | 참고 근거 보조 안내 |
| `source_limited` | Source-limited guidance | 제한적 근거 안내 |
| `source_unavailable` | Source-unavailable guidance | 확인된 근거 없음 안내 |
| `generic_advisory` | General advisory guidance | 일반 참고 안내 |

It is styled more calmly than the legal-citation row, does not imply official
approval, and gives the answer its overall identity instead of letting the
law-citation warning define the whole card.

---

## 6. Law-source unavailable display

When law grounding is unavailable **and** the answer-quality mode is
`source_limited` / `source_unavailable` / `generic_advisory`, the panel shows a
friendly supporting-source line instead of the blunt
`Legal citation verification: Needs review (Law source unavailable)`:

* en: *Supporting legal source could not be retrieved for this answer.*
* ko: *이 답변에 사용할 보조 법령 근거를 가져오지 못했습니다.*
* zh / zhHant equivalents.

Raw codes like `SOURCE_UNAVAILABLE` remain only inside the technical-details
`<details>` block. The limitation is not hidden; it is just framed as a
supporting-source gap, not a whole-answer failure.

---

## 7. Warning de-duplication

The card previously repeated the same "confirm with 1345 / HiKorea /
immigration office" caution in three places. Now:

* the **source panel disclosure** is the single primary caution;
* the **generic-AI note** is suppressed when the answer-basis row already
  communicates `source_limited` / `source_unavailable` / `generic_advisory`, or
  whenever the panel renders;
* the trailing **msg-disc** line is suppressed when the panel renders, so the
  phrase is not repeated;
* the **footer** disclaimer remains (localized) but no longer duplicates the
  exact panel phrase.

Safety disclaimers are reduced, not removed.

---

## 8. Footer i18n fix

The footer (`#referenceDisclaimer`) text now comes from a single
`SHELL_FOOTER_DISCLAIMER` map (ko / en / zh / zhHant) applied via
`applyShellLanguage(lang)`, which runs when the user's language is detected on
submit. English questions no longer leave a Korean footer. Suggested English:

> Paradiso provides public law/manual-based reference information and is not
> legal advice or a filing service. Confirm final decisions with the competent
> immigration office, HiKorea, 1345, or a qualified professional.

Official Korean institution names are kept in Korean inside the localized text.

---

## 9. Tests added

* `scripts/check_ai_shell_semantics.js` — extracts and exercises the real
  `generateBadges` logic for the H-1 golden case (D-2/D-4 as related chips, H-1
  as a checked-status chip; grounded detected status as a manual chip) plus
  static assertions for labels, friendly law text, raw-code containment, and the
  four-language footer.
* `backend/tests/test_ai_shell_source_semantics.py` — runs the node checker as a
  subprocess and adds readable static assertions for each part.
* `scripts/smoke_ai_live_quality.py` — reports related-status / footer / raw-code
  shell signals (warn-only).

---

## 10. Validation results

All green locally:

* `json.tool` for visa_data.json / backend/data/visas.json / doc_master.json — OK
* `sync_visa_data.py --check` — matches; `check_required_documents_coverage.py` — PASS;
  `validate_structured_requirements.py …2026_05.json` — valid
* `py_compile` + `--help` for smoke — OK
* `node scripts/check_i18n.js` — OK; `node scripts/check_ai_shell_semantics.js` — OK
* `pytest backend/tests -q` — all pass; scenario variants — pass;
  `GoldenEvalSuiteTests` — pass; `test_answer_quality_contract.py` — pass
* `bash scripts/check_repo.sh` — all regression checks passed

Deployed Railway smoke: run from an environment with egress —
`BACKEND_URL="https://web-production-14f9a.up.railway.app" python3 scripts/smoke_ai_live_quality.py`.

---

## 11. Known limitations

* ai.html detects only ko/en from the user's text; the zh / zhHant shell labels
  are wired and tested but only render when a zh/zhHant language is supplied.
* Chip relabeling is metadata-driven; if `related_statuses_not_sources` is empty,
  any non-detected code mentioned in the answer is shown cautiously as a related
  status to verify rather than a manual source.
* The shell consumes existing PR #256 metadata; no backend behavior changed.

---

## 12. Safety note

Paradiso cannot determine final eligibility, permission, or required documents.
Users must confirm case-specific outcomes with 1345, HiKorea, or the competent
immigration office.
