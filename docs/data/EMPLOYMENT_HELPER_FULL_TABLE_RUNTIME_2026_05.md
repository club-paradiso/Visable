# Employment Helper Full-Table Runtime — 2026-05

## What was wired

`scripts/fetch_jobcodes.py` now implements a **tiered data source**:

| Priority | Source | Status |
|---|---|---|
| 1 | `data/generated/employment_reporting_ksco8_full_candidate.json` + `…ksic11….json` | **Not present** (blocked — see below) |
| 2 | `data/generated/employment_reporting_ksco8_full_candidate.csv` + `…ksic11….csv` | **Not present** (blocked — see below) |
| 3 | `data/jobcode_master_ksco8_major_middle.csv` + `data/industrycode_master_ksic11_major.csv` | **Active (seed)** |

When full candidate files are placed at `data/generated/`, `fetch_jobcodes.py`
auto-detects them on the next run with no further code changes.

`scripts/extract_employment_reporting_full_tables.py` was updated to write
**both CSV and JSON** output so the runtime can load JSON directly without a
separate conversion step.

`index.html` (employment-helper modal only):

- Modal title updated: `직종(KSCO8)·업종(KSIC11)` — KSCO8 first to match HiKorea form order.
- Pane titles now show classification labels: `KSCO8 · 제8차 한국표준직업분류` and `KSIC11 · 제11차 한국표준산업분류`.
- Coverage note rendered dynamically (`jcCoverageNote`) after data loads: shows `seed` or `전체표`, record counts per category, and a reminder to confirm on HiKorea/1345.
- Disclaimer extended with two additional lines:
  - **코드 확정**: must confirm on HiKorea or 1345.
  - **적격성 심사 아님**: classification lookup is not E-7 or other status eligibility screening.

`data/jobcode_master.json` was regenerated from seed (no change in row counts).
`data/employment_reporting_helper_flow.json` was **not modified** — `full_extraction_status` remains `"pending"` because full candidate files are not present.

## Whether full candidate files were present or regenerated

**Full candidate files were not present in the repository.**

`data/generated/` does not exist. The manifest
(`data/employment_reporting_full_table_extraction_manifest_2026_05.json`) records
that extraction was completed from user-provided PDFs and that row counts matched
the official classification summaries (KSCO8: 1,999 rows; KSIC11: 2,038 rows),
but the generated files were not committed.

**No data was invented.** Runtime continues on seed data.

## Final row counts (current runtime — seed)

| Category | Classification | Levels | Records |
|---|---|---|---|
| 직업 (직종) | KSCO8 제8차 한국표준직업분류 | major, middle | 67 |
| 산업 (업종) | KSIC11 제11차 한국표준산업분류 | major | 21 |
| **Total** | | | **88** |

Expected full-table counts (from validated manifest, not yet in runtime):

| Category | Records |
|---|---|
| KSCO8 (all 5 levels) | 1,999 |
| KSIC11 (all 5 levels) | 2,038 |
| Total | 4,037 |

## Validation commands

```bash
# Verify JSON syntax of all touched files
python3 -m json.tool data/jobcode_master.json > /dev/null
python3 -m json.tool data/employment_reporting_helper_flow.json > /dev/null
python3 -m json.tool data/employment_reporting_full_table_extraction_manifest_2026_05.json > /dev/null
python3 -m json.tool data/employment_reporting_table_sample_validation_2026_05.json > /dev/null

# Check data source, coverage, and candidate file presence
python3 scripts/fetch_jobcodes.py --check

# Rebuild jobcode_master.json (auto-selects full or seed)
python3 scripts/fetch_jobcodes.py

# Validate occupation/industry separation
python3 -c "
import json
d = json.load(open('data/jobcode_master.json'))
occ = [r for r in d['data'] if r['분류'] == '직업']
ind = [r for r in d['data'] if r['분류'] == '산업']
assert '직업분류판' in occ[0] and '산업분류판' not in occ[0]
assert '산업분류판' in ind[0] and '직업분류판' not in ind[0]
print('separation OK', len(occ), 'occupation /', len(ind), 'industry')
"

# Full repo check
ALLOW_BACKEND_TEST_SKIP=1 bash scripts/check_repo.sh
```

### To regenerate full candidate files (when source PDFs are available)

```bash
# Step 1 — extract text from official PDFs
pdftotext -layout "(해설서) 제8차 한국표준직업분류(공개용)_24.6.24_(최종안).pdf" /tmp/ksco8.txt
pdftotext -layout "[별표2-2] 한국표준산업분류 제11차 개정 해설서(신구연계표 포함).pdf" /tmp/ksic11.txt

# Step 2 — extract and write CSV + JSON to data/generated/
python3 scripts/extract_employment_reporting_full_tables.py \
  --ksco-text /tmp/ksco8.txt \
  --ksic-text /tmp/ksic11.txt

# Step 3 — rebuild runtime (auto-detects full candidates)
python3 scripts/fetch_jobcodes.py

# Verify full data source is active
python3 scripts/fetch_jobcodes.py --check | grep data_source
```

After Step 3 completes with `data_source: full`, update
`data/employment_reporting_helper_flow.json` to set
`full_extraction_status: "active"` for both classifications.

## Remaining risks

| Risk | Severity | Mitigation |
|---|---|---|
| Full candidate files absent; runtime on major+middle seed only | Medium | Deterministic regeneration path documented above; fetch_jobcodes.py auto-promotes when files appear |
| UI performance with 4,037 combined rows not tested | Medium | Test in browser with `data/generated/` populated before marking full extraction active |
| PDF text extraction accuracy depends on pdftotext layout flag and PDF quality | Medium | Spot-check `--check` output row counts against manifest expectations (KSCO8 1,999; KSIC11 2,038) |
| Classification codes change with future revisions | Low | Manifest records classification/announcement/effective_date; re-run extraction when new PDFs published |
| Users misinterpreting candidate codes as confirmed | Low | UI disclaimer and coverage note both state "HiKorea/1345 확인 필수" |

## Non-goal (explicit)

**This PR does not treat KSCO8/KSIC11 classification lookup as E-7 eligibility screening.**

The employment reporting helper exists solely to assist users identify the correct
직종 and 업종 codes to enter in HiKorea 취업정보 온라인 신고 screens.
Classification lookup does not determine visa eligibility. E-7 and all other status
eligibility decisions require a separate assessment through official channels
(HiKorea, 1345, or the relevant immigration office).

The `eligibility_screening_note` field added to `jobcode_master.json` encodes this
constraint in the data file itself so future consumers of the file cannot overlook it.
