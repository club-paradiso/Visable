#!/usr/bin/env python3
"""Build the generated compatibility visa_data.json from the authoring layer.

Phase 3 / Script 2. Reads backend/data/visa_authoring/ and regenerates the
repo-root visa_data.json (a generated compatibility artifact), then keeps
backend/data/visas.json in sync via the existing sync script.

All legacy/compat fields (newReq, documents_*, subCodes, faq, feeInfo,
manualRefs, sourceManualStatus, _source_notes, _searchAliasAudit,
structuredRequirementsRef, manualRequiredDocAudit, summary, ...) are
regenerated. Low-value summaries removed from authoring are re-injected from
the compatibility layer so runtime output is byte-identical.

Determinism: build twice => no diff.

Usage:
  python3 scripts/visa/build_visa_data.py            # write visa_data.json + sync mirror
  python3 scripts/visa/build_visa_data.py --check    # exit 1 if generated != checked-in (no write)
  python3 scripts/visa/build_visa_data.py --out PATH # write generated output to PATH (audit; no sync)
  python3 scripts/visa/build_visa_data.py --no-sync  # write visa_data.json but skip mirror sync
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _visa_pipeline_common as C  # noqa: E402


def build_records() -> list:
    ctx = C.load_build_context()
    records = C.load_status_files()
    return [C.reconstruct_record(r, ctx) for r in records]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true",
                    help="exit 1 if generated output differs from checked-in visa_data.json")
    ap.add_argument("--out", type=str, default=None,
                    help="write generated output to this path instead of production")
    ap.add_argument("--no-sync", action="store_true",
                    help="do not sync backend/data/visas.json")
    args = ap.parse_args()

    rendered = C.dump_visa_json(build_records())

    if args.check:
        current = C.VISA_DATA.read_text(encoding="utf-8") if C.VISA_DATA.exists() else ""
        if rendered != current:
            print("ERROR: generated visa_data.json is OUT OF DATE relative to the "
                  "authoring layer. Run scripts/visa/build_visa_data.py.", file=sys.stderr)
            return 1
        print("OK: generated visa_data.json matches the authoring layer.")
        return 0

    if args.out:
        Path(args.out).write_text(rendered, encoding="utf-8")
        print(f"Wrote generated output to {args.out} ({len(rendered.encode('utf-8'))} bytes)")
        return 0

    C.VISA_DATA.write_text(rendered, encoding="utf-8")
    print(f"Wrote {C.VISA_DATA.relative_to(C.REPO_ROOT)} "
          f"({len(rendered.encode('utf-8'))} bytes, {rendered.count(chr(10))} lines)")

    if not args.no_sync:
        sync = C.REPO_ROOT / "scripts" / "sync_visa_data.py"
        res = subprocess.run([sys.executable, str(sync)], capture_output=True, text=True)
        sys.stdout.write(res.stdout)
        sys.stderr.write(res.stderr)
        if res.returncode != 0:
            return res.returncode
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
