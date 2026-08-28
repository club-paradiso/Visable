#!/usr/bin/env python3
"""Keep the backend deploy-context copies in sync with the canonical files.

Why this exists:
  The Railway service is deployed with Root Directory = backend, so files at
  the repository root are not in the build context. The backend's loaders
  prefer the `backend/data/` copy (which IS in context) and degrade when it is
  missing — which is exactly the production failure this script prevents.

Synced pairs:
  visa_data.json  -> backend/data/visas.json
      Missing copy degrades /api/visas to a tiny DEFAULT_VISAS stub.
  doc_master.json -> backend/data/doc_master.json
      Missing copy makes load_document_labels() return an empty map, so every
      document ID passes through unresolved and the procedure-packet endpoints
      serve raw identifiers like `doc_fee_generic` as user-facing document
      names. Caught by review on PR #582, where the resolver fix passed CI and
      did nothing in production for precisely this reason.

Both targets are byte-identical copies. This script never edits content: it
copies, or reports drift. The canonical file at the repository root stays the
single source of truth.

Usage:
  scripts/sync_visa_data.py            # copy any drifted target, else no-op
  scripts/sync_visa_data.py --check    # exit 1 if any target drifted (CI mode)
"""
from __future__ import annotations

import argparse
import filecmp
import shutil
import sys
from pathlib import Path
from typing import List, Tuple

REPO_ROOT = Path(__file__).resolve().parents[1]

#: (canonical source, backend deploy-context copy)
SYNCED_PAIRS: Tuple[Tuple[Path, Path], ...] = (
    (REPO_ROOT / "visa_data.json", REPO_ROOT / "backend" / "data" / "visas.json"),
    (REPO_ROOT / "doc_master.json", REPO_ROOT / "backend" / "data" / "doc_master.json"),
)

# Back-compat for anything importing the old single-pair constants.
SOURCE, TARGET = SYNCED_PAIRS[0]


def _fail(msg: str) -> int:
    print(f"ERROR: {msg}", file=sys.stderr)
    return 1


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Exit 1 if any copy differs from its source, without copying.",
    )
    args = parser.parse_args(argv)

    status = 0
    for source, target in SYNCED_PAIRS:
        if not source.is_file():
            status = _fail(f"source missing: {source}") or 1
            continue

        if target.is_file() and filecmp.cmp(source, target, shallow=False):
            print(f"OK: {target.relative_to(REPO_ROOT)} matches "
                  f"{source.relative_to(REPO_ROOT)}")
            continue

        if args.check:
            status = _fail(
                f"{target.relative_to(REPO_ROOT)} is out of sync with "
                f"{source.relative_to(REPO_ROOT)}. "
                f"Run scripts/sync_visa_data.py to update."
            ) or 1
            continue

        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        print(f"Updated {target.relative_to(REPO_ROOT)} from "
              f"{source.relative_to(REPO_ROOT)}")

    return status


if __name__ == "__main__":
    raise SystemExit(main())
