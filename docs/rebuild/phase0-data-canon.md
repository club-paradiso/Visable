# Phase 0 — Duplicate JSON canon analysis

Date: 2026-11-03. Decision recorded as ADR-003 in DECISIONS.md.

## What the brief claimed
`jobcode_master.json` vs `data/jobcode_master.json` differ, `output.json` vs
`data/output.json` differ, and index.html references both paths of each.

## What the checkout actually contains (verified)
```
$ ls -la jobcode_master.json data/jobcode_master.json output.json data/output.json
ls: cannot access 'jobcode_master.json': No such file or directory
-rw-r--r-- 1 root root 2228283 Nov  3 18:09 data/jobcode_master.json
ls: cannot access 'output.json': No such file or directory
ls: cannot access 'data/output.json': No such file or directory
$ md5sum data/jobcode_master.json
5b0138f0e6e2dec5d5f90186e2494a1e  data/jobcode_master.json
$ git log --all --oneline -- output.json data/output.json jobcode_master.json
(empty — the clone is shallow, 161 commits; the deletion predates it)
```
Conclusion: there is no duplicate pair left to diff. Only `data/jobcode_master.json`
exists. No unique sourced records can be lost because there is no second copy, so
hard stop 3 ("sourced records exist only in the copy you would drop") is **not**
triggered.

## Who reads which path (verified with grep)
- `index.html:16931` — `const JOBCODE_JSON_PATHS = ['./data/jobcode_master.json', './data/output.json', './jobcode_master.json', './output.json'];`
  The loader tries each in order; today paths 2–4 produce a 404 and are skipped.
- `scripts/employment_data_loader.mjs`, `scripts/employment_code_analyzer.mjs`,
  `scripts/check_employment_*.mjs`, `scripts/build_employment_*.{mjs,py}`,
  `scripts/fetch_jobcodes.py`, `scripts/tests/test_employment_reporting_dataset.py`,
  `data/employment/*.json` (source_registry etc.) and `data/audits/jobcode_runtime_audit.json`
  reference `data/jobcode_master.json` (and in some test fixtures the historical names as
  strings). None of them reads a root-level `jobcode_master.json` or any `output.json`
  as a file that must exist (to be re-verified in Phase 1 before trimming).

## Official-source pipeline
`scripts/fetch_jobcodes.py` / `scripts/build_employment_reporting_dataset.py` write
`data/jobcode_master.json`; this is the `scripts/build_*` output the decision rule prefers.

## Decision
- Canonical: `data/jobcode_master.json`.
- Phase 1 action (behaviour-preserving): reduce `JOBCODE_JSON_PATHS` to the canonical
  path only after the golden suite has a test that loads the employment code finder from
  it; the three dead fallbacks currently only cost 404 round-trips when the first fetch
  fails, and never succeed.
- No legal/employment data is edited.

## Open items for Phase 1 verification
- Re-grep every script that mentions `output.json` / root `jobcode_master.json` and
  confirm each is either a string in a fixture or a dead fallback before removing.
