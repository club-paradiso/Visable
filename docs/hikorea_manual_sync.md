# HiKorea manual sync

Keeps the repo's copies of the HiKorea **사증민원 자격별 안내 매뉴얼** and
**체류민원 자격별 안내 매뉴얼** followable when HiKorea posts an update (the
updates are irregular and hard to track manually).

> **Design principle (CLAUDE.md + the safe-automation architecture):** legal
> content is never modified automatically. This pipeline only *detects*,
> *stages*, and *proposes* — it opens a **draft PR** that a human reviews and
> merges. It never edits `visa_data.json`, `doc_master.json`, the verified
> `*_hwp_full.txt`, or any production data.

## Why a human stays in the loop

The manuals ship as **배포용(distribution) HWP** (FileHeader flag `0x4`): the
`BodyText` is a stub and `ViewText` is encrypted, so no open-source tool extracts
them fully. The committed `docs/data/claude_opus_manual_extraction_2026_05/
*_hwp_full.txt` were produced by verified human/AI-assisted extraction. The
automation surfaces the new file + a *best-effort* extraction with a completeness
report; the reviewer performs the real extraction before anything is promoted.

## Components

| File | Purpose |
| --- | --- |
| `data/sources/hikorea_manual_sync.json` | Config: per-manual download_url (nullable), committed HWP/txt paths, baseline sha256. |
| `scripts/convert_manual_hwp.py` | Best-effort HWP→text across several optional backends; scores each output and writes a benchmark matrix + an overall classification (`confident` / `low_confidence` / `blocked_distribution_hwp` / `failed`). |
| `scripts/tests/test_convert_manual_hwp.py` | Tests: missing backends, stub output, fake-confident backend, blocked-distribution classification, benchmark generation, production data untouched. |
| `scripts/sync_hikorea_manuals.py` | Obtain candidate HWP (manual input or best-effort download), sha256-compare to baseline, stage + convert changed ones, emit `build/manual-sync/{summary.json,pr_body.md}`. No production writes. |
| `.github/workflows/hikorea-manual-sync.yml` | Twice-monthly + `workflow_dispatch`; installs tooling; on change opens a draft PR. |

## Optional converter backends

`convert_manual_hwp.py` runs every *available* backend and benchmarks them. Each
is optional: if its tool is not installed (or, for the external CLIs, its command
env var is unset), it is reported as `missing` and skipped — the pipeline never
fails because one converter is absent. None of these tools are vendored into the
repo (no GPL code is copied in); they are detected and invoked at runtime.

| backend | tool | how it is detected |
| --- | --- | --- |
| `olefile` | builtin HWP5 BodyText parser | always (pure Python) |
| `soffice_pdftotext` | LibreOffice + poppler `pdftotext` | `soffice`/`libreoffice` + `pdftotext` on PATH |
| `hwp5txt` | [pyhwp](https://github.com/mete0r/pyhwp) | `hwp5txt` on PATH (`$HWP5TXT_CMD`) |
| `hwp2md_hephaex` | [hephaex/hwp2md](https://github.com/hephaex/hwp2md) (Rust) | `$HWP2MD_HEPHAEX_CMD` (default `hwp2md`) |
| `kordoc` | [chrisryugj/kordoc](https://github.com/chrisryugj/kordoc) (Python) | `$KORDOC_CMD` (default `kordoc`) |
| `hwp2md_roboco` | [roboco-io/hwp2md](https://github.com/roboco-io/hwp2md) (Go) | `$HWP2MD_ROBOCO_CMD` (no default — its binary name collides with hephaex's) |

### Installing / testing a backend locally

```sh
# hephaex/hwp2md (Rust)
git clone https://github.com/hephaex/hwp2md && (cd hwp2md && cargo build --release)
export HWP2MD_HEPHAEX_CMD="$PWD/hwp2md/target/release/hwp2md {input}"

# roboco-io/hwp2md (Go) — set its own env so it does not collide with hephaex
go install github.com/roboco-io/hwp2md@latest
export HWP2MD_ROBOCO_CMD="$HOME/go/bin/hwp2md {input}"

# chrisryugj/kordoc (Python)
pipx install kordoc   # or per the repo's README
export KORDOC_CMD="kordoc {input}"

# then benchmark against a real file
python3 scripts/convert_manual_hwp.py docs/source-manuals/2026-05/visa_manual_2026_05_21.hwp --outdir /tmp/bench
python3 scripts/tests/test_convert_manual_hwp.py
```

The command env var is a template; `{input}` (and optional `{output}`) are
substituted. In CI, set these as repo *Variables* and the workflow passes them
through.

### Protected / distribution HWP may be unextractable

Even with every backend installed, **배포용(distribution) HWP may be impossible to
fully extract with these tools.** kordoc, for example, only handles distribution
documents via the **Hancom Office COM API on Windows**; the Rust/Go/olefile
backends cannot decrypt them at all. When the best output is a stub the benchmark
classifies the result `blocked_distribution_hwp` and the draft PR carries the
"do not merge as a verified update" banner.

## How it runs

- **Auto attempt:** the scheduled job runs the sync. Best-effort download only
  happens when `download_url` is configured *and* `--allow-network` is passed
  (dispatch input). Official hosts often block CI (HTTP 403); that is handled
  gracefully and reported, not fatal.
- **Manual fallback (recommended while `download_url` is null):** a maintainer
  downloads the updated HWP from HiKorea, adds it to the checkout, and runs the
  workflow via *Run workflow* with `manual_hwp_visa` / `manual_hwp_stay` set to
  its path. The rest (hash compare, staging, extraction, draft PR) is automatic.

## Reviewer checklist (in the draft PR)

1. Confirm the staged HWP under `docs/source-manuals/incoming/` is the genuine
   official file.
2. Perform a verified (human/AI-assisted) full extraction — do **not** trust the
   best-effort text.
3. Move the HWP to its canonical `docs/source-manuals/<period>/` path and update
   the verified `*_hwp_full.txt`.
4. Update `baseline_sha256` in `data/sources/hikorea_manual_sync.json`.
5. Run the data audits and decide, with review, whether any grounding-data
   changes follow (separate from this PR if needed).

## Maintainer decision flow after a draft PR

When `hikorea-manual-sync` opens a draft PR, read the converter benchmark matrix
in the PR body and decide:

- **overall `confident`** (a backend produced substantial, manual-like text):
  still review it — diff the candidate text against the committed
  `*_hwp_full.txt`, sanity-check headings/codes, then promote it as a verified
  text update with the canonical paths + baseline sha256 updated.
- **`low_confidence`**: treat the extraction as a draft only. Do a verified
  (human/AI-assisted) extraction; do not ship the best-effort text as-is.
- **`blocked_distribution_hwp`** (the current reality for these manuals): the
  upstream file genuinely changed but no tool could extract it. Confirm the
  staged HWP is authentic, perform the verified extraction yourself, then update
  the canonical files + baseline.
- **`failed`**: no backend ran (or the file is not an HWP). Investigate the
  staged file before doing anything else.

In every case the PR is a *detection + staging* artifact. Promotion of legal
text and any downstream grounding-data change stays a reviewed, manual step.

## Enabling auto-download later

When a maintainer verifies the official direct download URL, set it as
`download_url` in the config (human-reviewed PR) and enable `allow_network` on
the schedule. Until then the manual fallback covers the same flow safely.
