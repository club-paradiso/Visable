# Manual grounding — expansion plan

This document tracks the deterministic manual-grounding entries shipped
with the Paradiso backend, how each entry was verified against the
committed source manuals, and which candidates remain deferred pending
verification.

This is **not** RAG. There is no embedding index, no live retrieval
against the law API, and no LLM-driven document chunking. The backend
ships a single JSON fixture, looks up an exact `(visa_code,
procedure_type)` pair, and injects the matching entry's documents,
caveats, and excerpt into the prompt sent to the LLM.

## Scope

- Backend only: `backend/paradiso_backend.py`,
  `backend/data/manual_grounding/stay_manual_grounding_2026_05.json`,
  and `backend/tests/test_paradiso_backend.py`.
- The frontend (`index.html`, `ai.html`), visa catalog
  (`visa_data.json`, `backend/data/visas.json`), and registered-agent
  finder UX are intentionally untouched.

## Source manual

- File: `docs/source-manuals/2026-05/stay_manual_2026_05.pdf`
- Title (Korean): 외국인체류 안내매뉴얼
- Date: 2026.5
- Issuing body: 법무부 출입국·외국인정책본부
- Total pages (PDF): 777
- Note: a related, separate file
  `docs/source-manuals/2026-05/visa_manual_2026_05.pdf` (visa-issuance
  manual) exists but is not used for stay/extension grounding.

## Verification method

1. `pdfinfo` + `pdftotext -layout` (poppler-utils) extract the PDF to
   a flat layout text file.
2. Candidate sections are located by:
   - searching for the visa header (e.g. `유학(D-2)`, `일반연수(D-4)`,
     `특정활동(E-7)`),
   - locating the `체류기간 연장허가` subsection within that visa's
     chapter,
   - reading the `제출서류` (required-documents) block verbatim.
3. PDF pages are confirmed by re-running
   `pdftotext -layout -f PAGE -l PAGE` on the candidate page range and
   checking that the printed footer (e.g. `- 226 -`) matches the
   absolute PDF page number returned by `pdftotext -f` / `-l`.
4. Entries that cannot be cleanly mapped to a single PDF page range are
   deferred rather than approximated.

Each entry stores both the PDF page range and a human-readable
`verification_note` describing the exact extraction step.

## Entries shipped in `stay_manual_grounding_2026_05.json`

| `visa_code` | `procedure_type`   | Section (Korean)                                   | PDF page(s) | Status            |
| ----------- | ------------------ | -------------------------------------------------- | ----------- | ----------------- |
| `D-2`       | `체류기간 연장허가`  | 유학(D-2)                                          | 43–44       | verified_locally |
| `D-4`       | `체류기간 연장허가`  | 일반연수(D-4) — 어학연수생(D-4-1, D-4-7)            | 90–91       | verified_locally |
| `E-7`       | `체류기간 연장허가`  | 특정활동(E-7) — 1. 제출 서류 및 확인사항             | 226         | verified_locally |

Each row in the JSON additionally carries:

- `required_documents` — list copied verbatim from the manual's
  `제출서류` block (translated to plain bullets, no paraphrase).
- `caveats` — caveats from the manual plus the standing
  "the immigration office may add or waive documents" disclaimer.
- `source_excerpt` — short verbatim excerpt of the manual subsection.
- `source_verification_status`, `source_confidence`,
  `verification_note` — provenance metadata for downstream auditing.

### D-4 entry — scope note

The shipped D-4 entry covers the **어학연수생 (D-4-1, D-4-7)** sub-track
only. The manual gives separate `제출서류` lists for:

- 기업 맞춤형 인턴십 (K-Trainee, D-4-2K)
- 고등학교 이하 외국인유학생 (D-4-3)
- 한식조리연수생 (D-4-5)
- 우수사설교육기관 외국인연수 (D-4-6)

These are intentionally **not** rolled into the D-4 entry because the
documents differ. They are tracked in the "Deferred entries" table
below.

### E-7 entry — scope note

The shipped E-7 entry covers the **general 제출서류** list on PDF page
226. Agreement-based special tracks (한·인도 CEPA 독립전문가, 한·러
국내채용 전문인력, 외국법자문법률사무소 파견 등) and the숙련기능인력
(E-7-4) point-system anchor have their own pages and are deferred.

## Deferred entries (verification incomplete)

| Candidate                                                | Why deferred                                                                                                                          |
| -------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------- |
| D-10 (구직) 체류기간 연장허가                              | Documents differ between D-10-1 점수제 적용, D-10-1 점수제 면제 특례자 (7+ sub-cases), D-10-2, D-10-3, D-10-T. A faithful single entry needs sub-code routing. |
| F-6 (결혼이민) 체류기간 연장허가                           | Splits into F-6-1 (국민의 배우자), F-6-2 (자녀 양육자), F-6-3 (혼인단절자), with separate 최초 vs. 후속 연장 brackets and humanitarian sub-cases. |
| D-4-2K, D-4-3, D-4-5, D-4-6 체류기간 연장허가              | Separate document lists per sub-code; D-4 fixture currently scopes to D-4-1/D-4-7 only.                                                |
| E-7 협정 특례 (CEPA / 한·러 협정 / 외국법자문법률사무소)   | Distinct document checklists; not part of the general E-7 page 226 list.                                                              |
| E-7-4 숙련기능인력 점수제 안내매뉴얼                       | The stay manual itself refers readers to a separate "숙련기능인력(E-7-4) 안내매뉴얼" not in this repository.                            |

These will be added in subsequent batches as separate
`(visa_code, visa_sub_code, procedure_type)` entries — only when each
page range and document list can be verified end-to-end against the
committed PDF. The `visa_sub_code` field and sub-code-aware selector
landed in schema version 1.2 (see "Schema 1.2: sub-code and scenario
metadata" below) so future batches do not need a fresh architectural
change.

## Schema 1.2: sub-code and scenario metadata

Version 1.2 of `stay_manual_grounding_2026_05.json` adds optional fields
to each grounding entry without changing the behavior of existing
records. All three currently shipped entries (D-2, D-4 어학연수생, E-7
general) explicitly populate the new fields with the conservative
defaults documented below.

| Field                                              | Purpose                                                                                                                              | Example values                                  |
| -------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------ | ----------------------------------------------- |
| `visa_sub_code`                                    | Sub-code that an entry is specifically scoped to. Null for "general" entries.                                                        | `"D-4-2K"` (future), `null` (current entries)   |
| `sub_codes_covered`                                | Explicit allow-list of sub-codes a general entry covers. `null` means "no sub-code coverage" — sub-code requests fall through.        | `["D-4-1", "D-4-7"]`, `null`                    |
| `scenario`                                         | Distinguishes scenarios within a single (visa_code, visa_sub_code), e.g. initial vs. follow-up extension, humanitarian cases.        | `"general"`, `"initial"`, `"follow_up"`, `null` |
| `scenarios_covered`                                | Explicit allow-list of scenarios a general entry covers.                                                                              | `["general"]`, `null`                           |
| `requires_clarification_when_missing_subcode`      | When true, a request whose sub-code/scenario cannot be determined should NOT silently fall through to the general entry.              | `false` (current default)                       |

### Selector behavior

`_select_grounding(visa_code, task_type, visa_sub_code=None)` resolves
in this order:

1. **Top-level gate** — only `("extension", code-in-_GROUNDED_VISA_CODES)`
   pairs are considered. Codes whose top-level is not grounded (e.g.
   `D-10`, `F-6`) return `None` regardless of sub-code.
2. **Exact sub-code match** — when `visa_sub_code` is set, an entry
   whose `visa_sub_code` matches exactly is preferred.
3. **General-entry fallback** — if no exact match exists, a general
   entry (`visa_sub_code is null`) is considered **only** when the
   requested sub-code appears in that entry's `sub_codes_covered` list.
   A general entry with `sub_codes_covered = null` is treated as
   covering no specific sub-codes; sub-code requests then fall through
   with `grounding_used = false`.
4. **No-subcode request** — when `visa_sub_code` is null, only general
   entries (`visa_sub_code is null`) are eligible. The existing D-2 /
   D-4 / E-7 top-level paths continue to ground exactly as before.

### Normalization

`_normalize_visa_code` accepts sub-code variants with or without
separators by using a static list (`_VALID_MAIN_CODES`) as a parsing
oracle. Examples:

| Input        | Normalized   |
| ------------ | ------------ |
| `d4`         | `D-4`        |
| `D-4-2K`     | `D-4-2K`     |
| `d42k`       | `D-4-2K`     |
| `D4-2K`      | `D-4-2K`     |
| `d43`        | `D-4-3`      |
| `d10`        | `D-10`       |
| `d101`       | `D-10-1`     |
| `D-10-T`     | `D-10-T`     |
| `f61`        | `F-6-1`      |
| `F6-1`       | `F-6-1`      |
| `e74`        | `E-7-4`      |
| `K-ETA`      | `K-ETA`      |

`_detect_visa_codes` returns a `(top_visa_code, visa_sub_code)` tuple.
Sub-code detection is **payload-only** — free-text mentions of a
sub-code in the user prompt are not parsed. The `/api/ask` response
gains an additive `visa_sub_code_detected` field (null when no sub-code
is supplied).

### Warning: top-level visa codes must not overgeneralize

The biggest hazard in expanding the fixture is using a single
`visa_code` entry to answer a request whose sub-code has a materially
different document list. The shipped D-4 어학연수생 entry is the
canonical example: it explicitly enumerates
`sub_codes_covered = ["D-4-1", "D-4-7"]` so that a D-4-2K, D-4-3, D-4-5,
or D-4-6 request returns no grounding rather than silently borrowing the
어학연수생 document list. New entries must follow the same discipline —
either ship a sub-code-specific entry or leave the request ungrounded.

## Why not full RAG yet?

The deterministic-lookup approach was chosen to:

- Keep responses faithful to a specific, auditable PDF snapshot
  (`stay_manual_2026_05.pdf`).
- Avoid introducing embeddings, a vector store, chunking heuristics,
  retrieval evaluation, or new runtime dependencies before the legal /
  source-attribution shape of the product is settled.
- Make every grounded answer traceable to a precise `page_range` and
  `verification_note` that a human can re-check in seconds.

Full RAG, law-API retrieval, and embeddings/vector search are
explicitly **out of scope** for this PR.

## Backend wiring

- `_GROUNDED_VISA_CODES` in `backend/paradiso_backend.py` enumerates the
  visa codes that have a fixture entry. Text-based detection is bounded
  by this tuple so a free-text mention of an ungrounded code (e.g.
  `F-2`) does **not** trigger a phantom detection.
- Explicit `visa_code` (or `visa_data.code`) values in the request
  payload are still normalized via `_normalize_visa_code` for any code
  — that path is unchanged. Variants like `d4`, `D4`, `D 4`, `e7`,
  `E7`, `e-7` all resolve to `D-4` / `E-7`.
- `_select_grounding(visa_code, task_type)` returns an entry only when
  `task_type == "extension"` and the visa code is in
  `_GROUNDED_VISA_CODES` **and** the fixture contains a matching
  `(visa_code, "체류기간 연장허가")` record.
- `_build_grounded_prompt` no longer hard-codes the D-2 section title;
  each entry's `section` / `procedure_type` flow through into the
  prompt.

## Reproducing the verification locally

```bash
# Poppler tools
which pdfinfo pdftotext || sudo apt-get install -y poppler-utils

# Sanity-check the manual
pdfinfo docs/source-manuals/2026-05/stay_manual_2026_05.pdf

# Extract the whole manual to a flat text file
pdftotext -layout docs/source-manuals/2026-05/stay_manual_2026_05.pdf /tmp/stay_manual_2026_05.txt

# Spot-check the three grounded sections
pdftotext -layout -f 43  -l 44  docs/source-manuals/2026-05/stay_manual_2026_05.pdf -   # D-2
pdftotext -layout -f 90  -l 91  docs/source-manuals/2026-05/stay_manual_2026_05.pdf -   # D-4 어학연수
pdftotext -layout -f 226 -l 226 docs/source-manuals/2026-05/stay_manual_2026_05.pdf -   # E-7
```

## Next batches (suggested order)

With schema 1.2 in place, the recommended next batches are:

1. **D-10-1 점수제 적용 체류기간 연장허가** — separate sub-code entries
   for D-10-1, D-10-2, D-10-3, D-10-T. Each entry carries
   `visa_sub_code` set to the specific code so the selector chooses the
   right document list per request.
2. **F-6-1 국민의 배우자 체류기간 연장허가** with an `initial` vs.
   `follow_up` (and humanitarian) split using the `scenario` field;
   F-6-2 and F-6-3 follow as separate entries.
3. **Remaining D-4 sub-codes** (D-4-2K K-Trainee, D-4-3 외국인유학생,
   D-4-5 한식조리연수생, D-4-6 우수사설교육기관) — each as its own
   `visa_sub_code`-scoped entry. The current D-4 어학연수생 entry stays
   as-is.
4. **E-7 협정 특례 tracks** (한·인도 CEPA 독립전문가, 한·러 협정,
   외국법자문법률사무소) — separate entries; do not extend the general
   E-7 entry's `sub_codes_covered`. **E-7-4 숙련기능인력 is deliberately
   out of scope** — it depends on a separate external manual not
   committed to this repository.
5. F-2 (거주) 체류기간 연장허가.

Each batch must include:

- Updated fixture entries with PDF page range + verification note.
- Selector / detection updates only if the new code is not already in
  `_GROUNDED_VISA_CODES`.
- Tests covering: grounded selection, payload-variant normalization,
  task gating (non-extension does not ground), text-only detection
  (where applicable), and absence of generic global wording.
- Documentation update to this file.

## Fallback if PDF extraction is not available

If a future environment cannot run `pdftotext` (e.g. read-only CI
without poppler), do **not** add new grounding entries. Instead:

- Leave the fixture unchanged.
- Open a doc-only PR that records the candidate section, the user's
  reasoning, and the verification step that could not be performed.
- Defer the entry to a batch that runs in an environment with
  `poppler-utils` (or equivalent) available.

## Related documents

- [`docs/paradiso_ai_safe_automation_architecture.md`](paradiso_ai_safe_automation_architecture.md) —
  end-to-end safe automation architecture (PR sequence A–H).
- [`docs/source_monitoring_pipeline.md`](source_monitoring_pipeline.md) —
  what `scripts/check_source_updates.py` does and does not do.
- [`docs/privacy_safe_coverage_analytics.md`](privacy_safe_coverage_analytics.md) —
  input contract for `scripts/analyze_coverage_gaps.py`.
- [`backend/data/manual_grounding/candidates/README.md`](../backend/data/manual_grounding/candidates/README.md) —
  draft-only candidate directory contract.
