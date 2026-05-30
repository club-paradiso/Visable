# Employment Helper Full-Table Runtime — 2026-05

## Scope of this PR

This is **preparation work**, not actual full-table runtime wiring. The full
candidate files are not present in the repository, so the build path and UI
labels are prepared, but the committed runtime dataset is left untouched.

**Runtime coverage was NOT reduced.** `data/jobcode_master.json` remains the
existing full runtime dataset (`total_count: 3937`, 직업 1899 / 산업 2038,
`data_source: full_runtime_dataset_v1`).

## What was wired

### `scripts/fetch_jobcodes.py` — tiered source + coverage-protection guard

Data source priority (highest → lowest):

| Priority | Source | Status |
|---|---|---|
| 1 | `data/generated/employment_reporting_ksco8_full_candidate.json` + `…ksic11….json` | **Not present** |
| 2 | `data/generated/employment_reporting_ksco8_full_candidate.csv` + `…ksic11….csv` | **Not present** |
| 3 | seed CSV (`jobcode_master_ksco8_major_middle.csv`, `industrycode_master_ksic11_major.csv`) | build-path scaffolding only |

**Coverage-protection guard (the important part):** a seed-only build (88 rows)
must never overwrite a larger committed runtime dataset (3937 rows). When full
candidate files are absent:

- `python3 scripts/fetch_jobcodes.py` (no args) is a **no-op**. It prints what it
  would do and leaves `data/jobcode_master.json` unchanged.
- Writing the seed output requires the explicit `--allow-seed-downgrade` flag
  (testing / fresh-checkout bootstrap only).
- A full-candidate build always writes, because it increases (never reduces)
  coverage.

When full candidate files are placed at `data/generated/`, `fetch_jobcodes.py`
auto-detects them on the next run and writes the full dataset with no further
code changes.

### `scripts/extract_employment_reporting_full_tables.py`

Updated to write **both CSV and JSON** output so the runtime can load JSON
directly without a separate conversion step.

### `index.html` (employment-helper modal only)

- Modal title: `직종(KSCO8)·업종(KSIC11)` — KSCO8 first, matching HiKorea form order.
- Pane titles: `KSCO8 · 제8차 한국표준직업분류` and `KSIC11 · 제11차 한국표준산업분류`.
- Coverage note (`jcCoverageNote`) rendered dynamically after data loads, showing
  data source, record counts, and a reminder to confirm on HiKorea/1345. This
  reads `data_source`/`categories` if present and degrades gracefully on the
  existing runtime schema (which lacks those keys).
- Disclaimer extended with two lines:
  - **코드 확정**: must confirm final codes on HiKorea or 1345.
  - **적격성 심사 아님**: classification lookup is not E-7 (or any status) eligibility screening.

## Whether full generated data is present or absent

**Absent.** `data/generated/` does not exist in the repository. The extraction
manifest (`data/employment_reporting_full_table_extraction_manifest_2026_05.json`)
records that 1,999 KSCO8 rows and 2,038 KSIC11 rows were extracted from
user-provided PDFs and that sample validation passed, but the generated files
were not committed.

**No data was invented and runtime coverage was not reduced.**
`data/employment_reporting_helper_flow.json` was **not modified** —
`full_extraction_status` stays `"pending"`.

## Row counts

| | total_count | 직업 | 산업 |
|---|---|---|---|
| Committed runtime (unchanged by this PR) | 3937 | 1899 | 2038 |
| Seed build path (not written to runtime) | 88 | 67 | 21 |
| Full candidate target (when regenerated) | 4037 | 1999 | 2038 |

## Validation commands

```bash
# JSON syntax
python3 -m json.tool data/jobcode_master.json > /dev/null   # still 3937 rows

# Source / coverage / guard status
python3 scripts/fetch_jobcodes.py --check
#   data_source: seed, candidate_total: 88, committed_total: 3937, would_write: false

# Default run is a no-op when full candidates are absent
python3 scripts/fetch_jobcodes.py
#   SKIP: ... Refusing to overwrite committed runtime data ... left unchanged.

# Full repo check
ALLOW_BACKEND_TEST_SKIP=1 bash scripts/check_repo.sh
#   205 tests pass; git diff --check clean; "Success: repository validation passed."

# Diff stat must NOT show data/jobcode_master.json
git diff --stat origin/main
```

### To generate and commit full candidate data (future PR)

```bash
# Step 1 — extract text from official PDFs
pdftotext -layout "(해설서) 제8차 한국표준직업분류(공개용)_24.6.24_(최종안).pdf" /tmp/ksco8.txt
pdftotext -layout "[별표2-2] 한국표준산업분류 제11차 개정 해설서(신구연계표 포함).pdf" /tmp/ksic11.txt

# Step 2 — write CSV + JSON candidates to data/generated/
python3 scripts/extract_employment_reporting_full_tables.py \
  --ksco-text /tmp/ksco8.txt --ksic-text /tmp/ksic11.txt

# Step 3 — rebuild runtime (auto-detects full candidates, writes full dataset)
python3 scripts/fetch_jobcodes.py
python3 scripts/fetch_jobcodes.py --check | grep data_source   # → "full"
```

After Step 3 reports `data_source: full`, update
`data/employment_reporting_helper_flow.json` to set
`full_extraction_status: "active"` for both classifications.

## Remaining risks

| Risk | Severity | Mitigation |
|---|---|---|
| Full candidate files absent; full extraction still blocked | Medium | Deterministic regeneration path documented; guard prevents accidental downgrade |
| Two runtime schemas exist (committed `full_runtime_dataset_v1` vs. seed builder output) | Medium | UI coverage note degrades gracefully; full-candidate rebuild produces the builder schema — verify field names before flipping runtime |
| UI performance with ~4,000 rows | Low | Already serving 3937 rows today; no change |
| Users misinterpreting codes as confirmed / as eligibility | Low | Disclaimer states HiKorea/1345 confirmation and not-eligibility-screening |

## Non-goal (explicit)

**This PR does not treat KSCO8/KSIC11 classification lookup as E-7 eligibility
screening.** The employment reporting helper exists solely to help users identify
the correct 직종 and 업종 codes for HiKorea 취업정보 온라인 신고. Classification
lookup does not determine visa eligibility; E-7 and all other status decisions
require a separate assessment through official channels (HiKorea, 1345, or the
relevant immigration office).
