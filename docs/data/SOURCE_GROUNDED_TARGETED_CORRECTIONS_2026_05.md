# Source-Grounded Targeted Corrections — 2026-05

Direct, conservative source-grounded correction pass over all stay/visa status
records. Only fields with **exact official-manual evidence committed in the repo**
were patched.

## Pass 2 — live official web sources (visa.go.kr / hikorea.go.kr)

A follow-up pass attempted to source-ground additional corrections from the live
official public sites (Korea Visa Portal for visa issuance; HiKorea for
stay/extension/change/registration). **Both origins returned HTTP 403 Forbidden**
to this environment's egress IP (TLS succeeds, origin refuses), and `WebSearch`
is restricted to non-`.go.kr` domains here. Per task policy this is recorded as
`SOURCE_ACCESS_BLOCKED_OR_DYNAMIC`; no access-control bypass was attempted and no
data was patched from memory.

- **Live-web corrections applied: 0** (sources unreachable — see
  `docs/data/OFFICIAL_WEB_SOURCE_EVIDENCE_2026_05.md` and
  `docs/data/official_web_source_evidence_2026_05.json` for the full access log).
- The local-grounding correction below (D-4) stands unchanged from Pass 1.

## Source authority used

The committed, source-verified extraction
`backend/data/manual_grounding/stay_manual_grounding_2026_05.json`
(`source_file: docs/source-manuals/2026-05/stay_manual_2026_05.pdf`,
`외국인체류 안내매뉴얼` 2026.5, 법무부 출입국·외국인정책본부). Each grounding entry
carries `source_verification_status: "verified_locally"`,
`source_confidence: "high"`, a verbatim Korean `source_excerpt`, and an exact
absolute-PDF `page_range` with a `verification_note` describing the
`pdftotext` extraction used.

> Why this source: the raw PDFs under `docs/source-manuals/2026-05/` are
> image-based and have **no extractable text** in this environment (and no
> `pdftotext`/PDF library is available), so direct re-extraction was not
> possible. Per the task ("if extracted text already exists in repo, use it"),
> the committed `verified_locally` grounding artifact is the exact-source
> authority. The placeholder crosswalk files
> (`TEMPLATE_NOT_SOURCE_VERIFIED` / `DRAFT_PLACEHOLDER` / `PLANNING_ONLY`) and
> the `candidate_unverified` F-6 candidate were **not** used.

## Numbers

- **Records inspected:** 58
- **Records with an exact, verified manual section located:** 3
  (D-2, D-4, E-7 — `체류기간 연장허가` extension document lists)
- **Corrections applied:** 1
- **Files changed:** `visa_data.json`, `backend/data/visas.json` (synced)

## Corrections applied

| Code | Field / JSON path | Old | New | Source page / section | Reason |
| --- | --- | --- | --- | --- | --- |
| D-4 | `procedures.extension.manualRefs[0].pageRange` | `"p. 90"` | `"pp. 90-91"` | stay manual 2026.5 **pp. 90-91**, section `일반연수(D-4) — 1. 어학연수생(D-4-1, D-4-7)에 대한 체류기간 연장허가` (`나. 제출서류`); committed grounding `d4_extension_2026_05`, `verified_locally`/`high` | The live single-page citation omits **p. 91**, where the `나. 제출서류` list completes per the verified grounding's `verification_note`. Completing the range makes the citation point to the full document list. No scope change, no content change. `confidence` and `needsManualReview: true` left unchanged. |

## Records located but **not** changed (already adequate / exact)

- **D-2** `procedures.extension.manualRefs[0].pageRange = "pp. 42-44"` — the
  verified grounding (`d2_extension_2026_05`, pages **43-44**) is fully covered by
  the existing range. Narrowing to `43-44` would risk dropping p. 42; the source
  does not establish that p. 42 is wrong → **no change**.
- **E-7** `procedures.extension.manualRefs[0].pageRange = "p. 226"` — exact match
  to the verified grounding (`e7_extension_2026_05`, page **226**) → **no change**.

## Skipped high-risk / unsupported items

- **F-6** — the only committed F-6 artifact
  (`backend/data/manual_grounding/candidates/f6_divorce_status_change/candidate.json`)
  is explicitly `source_verification_status: "candidate_unverified"`,
  `source_confidence: "low"`, `manual_section: "TBD"`, empty `required_documents`,
  with a `verification_note` stating "NOT source-verified." No exact evidence →
  not patched.
- **G-1, H-2, D-10, E-7-4, D-4 subcodes, C-3 subcodes, B-2 / Jeju,
  scenario/helper records** — no committed `verified_locally` manual extraction
  exists for these in the repo; the only verified groundings cover D-2/D-4/E-7
  general extension. Patching would require unsourced inference → not patched.
- **`매뉴얼 확인 필요` placeholder `manualRefs`** on non-extension procedures
  (visaIssuance, statusChange, registration, etc.) — the verified grounding
  covers only the **extension** procedure; filling other procedures' placeholders
  would overgeneralize the extension page → not patched.
- **`DATA_MISSING` document notes** — replacing these is a high-impact change to
  user-facing required-document content; the verified grounding's verbatim lists
  map to specific items and per-item mapping is not low-risk → deferred.

## Validation

```
python3 -m json.tool visa_data.json                       # PASS
python3 -m json.tool backend/data/visas.json              # PASS
python3 -m json.tool doc_master.json                      # PASS
python3 scripts/sync_visa_data.py --check                 # OK (byte-identical parity)
python3 scripts/check_required_documents_coverage.py      # PASS (58 statuses, rc=0)
bash scripts/check_repo.sh                                 # rc=0 (backend tests passed)
```

## Non-goals

- No full legal verification claim.
- No metadata promotion (no `verified=true`; `needsManualReview: true` retained;
  `confidence` label unchanged).
- No law grounding activation.
- No unsourced corrections.
- No UI redesign; no changes to employment helper files or
  `data/jobcode_master.json`.
- No overgeneralization of sub-code/scenario requirements onto parent records.
