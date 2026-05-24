#!/usr/bin/env python3
"""Paradiso source monitoring — report-only skeleton.

Reads ``data/source_registry.json`` and reports the state of every
declared source. By default this script does **no** network I/O:

- ``pdf_manual`` entries are compared against their committed
  ``local_path`` via sha256. Result is one of:
  ``unchanged``, ``changed``, ``missing``, ``no_baseline``.
- ``law_api`` and ``notice_index`` entries are **skipped** unless
  ``--allow-network`` is passed. Even with ``--allow-network`` this
  PR's skeleton does not actually fetch — it reports
  ``network_skipped: HTTP not implemented in skeleton``. The flag is
  honored for future PRs.

The script never modifies ``source_registry.json``, never writes
state files, never opens issues, never opens PRs, and never touches
the active grounding fixture.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DEFAULT_REGISTRY_PATH = os.path.join(REPO_ROOT, "data", "source_registry.json")
DEFAULT_HIKOREA_CATALOG_PATH = os.path.join(
    REPO_ROOT,
    "data",
    "sources",
    "hikorea_source_catalog.json",
)
DEFAULT_IMM_NOTICE_PATH = os.path.join(
    REPO_ROOT,
    "data",
    "sources",
    "immigration_notice_sources.json",
)

_VALID_TYPES = {"pdf_manual", "law_api", "notice_index"}
_VALID_STATUSES = {"active", "not_configured", "deprecated"}
_REQUIRED_CATALOG_FIELDS = {
    "source_id",
    "source_type",
    "url",
    "domain",
    "monitor_enabled",
    "scrape_allowed",
    "requires_login",
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _sha256_of_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return f"sha256:{h.hexdigest()}"


def _load_registry(path: str) -> Dict[str, Any]:
    if not os.path.isfile(path):
        raise SystemExit(f"ERROR: source registry not found at {path}")
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit(f"ERROR: failed to read {path}: {exc}")
    if not isinstance(data, dict) or not isinstance(data.get("sources"), list):
        raise SystemExit(f"ERROR: {path} must be a JSON object with a 'sources' list")
    return data


def _load_catalog(path: str) -> Dict[str, Any]:
    if not os.path.isfile(path):
        raise SystemExit(f"ERROR: source catalog not found at {path}")
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit(f"ERROR: failed to read {path}: {exc}")
    if not isinstance(data, dict) or not isinstance(data.get("sources"), list):
        raise SystemExit(f"ERROR: {path} must be a JSON object with a 'sources' list")
    return data


def _validate_record(rec: Dict[str, Any], idx: int) -> List[str]:
    errors: List[str] = []
    required = ("id", "type", "title", "status")
    for field in required:
        if field not in rec:
            errors.append(f"sources[{idx}]: missing required field '{field}'")
    rec_type = rec.get("type")
    if rec_type not in _VALID_TYPES:
        errors.append(
            f"sources[{idx}] id={rec.get('id')!r}: invalid type {rec_type!r}; "
            f"expected one of {sorted(_VALID_TYPES)}"
        )
    rec_status = rec.get("status")
    if rec_status not in _VALID_STATUSES:
        errors.append(
            f"sources[{idx}] id={rec.get('id')!r}: invalid status "
            f"{rec_status!r}; expected one of {sorted(_VALID_STATUSES)}"
        )
    if rec_type == "pdf_manual" and not rec.get("local_path"):
        errors.append(
            f"sources[{idx}] id={rec.get('id')!r}: pdf_manual entries must "
            "declare local_path"
        )
    return errors


def _validate_catalog_record(rec: Dict[str, Any], idx: int, label: str) -> List[str]:
    errors: List[str] = []
    for field in sorted(_REQUIRED_CATALOG_FIELDS):
        if field not in rec:
            errors.append(f"{label}.sources[{idx}]: missing required field '{field}'")
    return errors


def _disabled_reason(rec: Dict[str, Any]) -> Optional[str]:
    if not rec.get("monitor_enabled", False):
        return "monitor_enabled=false"
    if not rec.get("scrape_allowed", False):
        return "scrape_allowed=false"
    if rec.get("requires_login", False):
        return "requires_login=true"
    return None


def _prepare_catalog_candidates(
    catalogs: List[Tuple[str, Dict[str, Any]]],
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[str]]:
    eligible: List[Dict[str, Any]] = []
    disabled: List[Dict[str, Any]] = []
    validation_errors: List[str] = []

    for label, catalog in catalogs:
        for idx, rec in enumerate(catalog.get("sources", [])):
            if not isinstance(rec, dict):
                validation_errors.append(f"{label}.sources[{idx}]: not an object")
                continue

            validation_errors.extend(_validate_catalog_record(rec, idx, label))
            reason = _disabled_reason(rec)
            shaped = {
                "catalog": label,
                "source_id": rec.get("source_id"),
                "source_type": rec.get("source_type"),
                "domain": rec.get("domain"),
                "url": rec.get("url"),
                "reason": reason,
            }

            if reason is None:
                eligible.append(shaped)
            else:
                disabled.append(shaped)

    return eligible, disabled, validation_errors


def _summarize_catalog(eligible: List[Dict[str, Any]]) -> Dict[str, Dict[str, int]]:
    by_domain: Dict[str, int] = {}
    by_source_type: Dict[str, int] = {}

    for rec in eligible:
        domain = str(rec.get("domain") or "unknown")
        source_type = str(rec.get("source_type") or "unknown")
        by_domain[domain] = by_domain.get(domain, 0) + 1
        by_source_type[source_type] = by_source_type.get(source_type, 0) + 1

    return {"by_domain": by_domain, "by_source_type": by_source_type}


def _check_local(rec: Dict[str, Any]) -> Dict[str, Any]:
    local_path = rec.get("local_path")
    if not local_path:
        return {"state": "skipped", "reason": "no_local_path"}
    abs_path = local_path if os.path.isabs(local_path) else os.path.join(REPO_ROOT, local_path)
    if not os.path.isfile(abs_path):
        return {
            "state": "missing",
            "local_path": local_path,
            "reason": "file_not_found",
        }
    current_hash = _sha256_of_file(abs_path)
    baseline = rec.get("last_known_hash")
    if not baseline:
        return {
            "state": "no_baseline",
            "local_path": local_path,
            "current_hash": current_hash,
        }
    if baseline == current_hash:
        return {
            "state": "unchanged",
            "local_path": local_path,
            "current_hash": current_hash,
        }
    return {
        "state": "changed",
        "local_path": local_path,
        "current_hash": current_hash,
        "previous_hash": baseline,
    }


def _check_network_entry(rec: Dict[str, Any], allow_network: bool) -> Dict[str, Any]:
    if not allow_network:
        return {
            "state": "skipped",
            "reason": "network_disabled",
            "url": rec.get("url"),
        }
    return {
        "state": "network_skipped",
        "reason": "HTTP fetch not implemented in skeleton",
        "url": rec.get("url"),
    }

def _check_source(rec: Dict[str, Any], allow_network: bool) -> Dict[str, Any]:
    rec_type = rec.get("type")
    rec_status = rec.get("status")
    base = {
        "id": rec.get("id"),
        "type": rec_type,
        "status": rec_status,
        "title": rec.get("title"),
        "checked_at": _now_iso(),
    }

    if rec_status == "deprecated":
        return {**base, "state": "skipped", "reason": "deprecated"}
    if rec_type == "pdf_manual":
        return {**base, **_check_local(rec)}
    if rec_type in ("law_api", "notice_index"):
        if rec_status == "not_configured":
            return {**base,"state": "skipped","reason": "not_configured","url": rec.get("url")}
        return {**base, **_check_network_entry(rec, allow_network)}
    return {**base, "state": "skipped", "reason": f"unknown_type:{rec_type}"}


def _summarize(results: List[Dict[str, Any]]) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for r in results:
        counts[r["state"]] = counts.get(r["state"], 0) + 1
    counts["total"] = len(results)
    return counts

def _parse_args(argv: Optional[List[str]]) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Report-only source monitor for Paradiso AI.")
    p.add_argument(
        "--registry",
        default=DEFAULT_REGISTRY_PATH,
        help="Path to source_registry.json (default: %(default)s).",
    )
    p.add_argument(
        "--local-only",
        action="store_true",
        help="Force network-backed entries to be skipped (default behavior).",
    )
    p.add_argument(
        "--allow-network",
        action="store_true",
        help="Permit network-backed entries (this skeleton still does not fetch).",
    )
    p.add_argument(
        "--strict",
        action="store_true",
        help="Exit nonzero when any 'active' local source is changed/missing.",
    )
    p.add_argument(
        "--json",
        action="store_true",
        help="Emit JSON output instead of human-readable report.",
    )
    p.add_argument(
        "--catalog-dry-run",
        action="store_true",
        help="Dry-run monitor eligibility on HiKorea/KIS catalogs.",
    )
    p.add_argument(
        "--hikorea-catalog",
        default=DEFAULT_HIKOREA_CATALOG_PATH,
        help="Path to hikorea_source_catalog.json (default: %(default)s).",
    )
    p.add_argument(
        "--immigration-catalog",
        default=DEFAULT_IMM_NOTICE_PATH,
        help="Path to immigration_notice_sources.json (default: %(default)s).",
    )
    p.add_argument(
        "--list-disabled",
        action="store_true",
        help="List disabled catalog records with reasons.",
    )
    return p.parse_args(argv)

def _run_catalog_dry_run(args: argparse.Namespace) -> int:
    catalogs = [
        ("hikorea_source_catalog", _load_catalog(args.hikorea_catalog)),
        ("immigration_notice_sources", _load_catalog(args.immigration_catalog)),
    ]
    eligible, disabled, errors = _prepare_catalog_candidates(catalogs)
    if errors:
        for err in errors:
            print(f"ERROR: {err}", file=sys.stderr)
        return 2
    summary = _summarize_catalog(eligible)
    if args.json:
        print(json.dumps({"allow_network": False, "mode": "catalog_dry_run", "eligible": eligible, "disabled": disabled if args.list_disabled else [], "summary": summary}, indent=2, ensure_ascii=False))
    else:
        print("Paradiso source monitor — catalog dry-run (no network)")
        print("=" * 60)
        print(f"Eligible records: {len(eligible)}")
        print("By domain:")
        for k, v in sorted(summary["by_domain"].items()):
            print(f"  {k}: {v}")
        print("By source_type:")
        for k, v in sorted(summary["by_source_type"].items()):
            print(f"  {k}: {v}")
        if args.list_disabled:
            print("Disabled records:")
            for rec in disabled:
                print(f"  - {rec['catalog']}:{rec.get('source_id')} reason={rec.get('reason')}")
        if not eligible:
            print("No monitor-enabled records are currently eligible. Exiting cleanly.")
    return 0

def _run_catalog_dry_run(args: argparse.Namespace) -> int:
    catalogs = [
        ("hikorea_source_catalog", _load_catalog(args.hikorea_catalog)),
        ("immigration_notice_sources", _load_catalog(args.immigration_catalog)),
    ]
    eligible, disabled, errors = _prepare_catalog_candidates(catalogs)
    if errors:
        for err in errors:
            print(f"ERROR: {err}", file=sys.stderr)
        return 2

    summary = _summarize_catalog(eligible)
    if args.json:
        out = {
            "allow_network": False,
            "mode": "catalog_dry_run",
            "eligible": eligible,
            "disabled": disabled if args.list_disabled else [],
            "summary": summary,
        }
        print(json.dumps(out, indent=2, ensure_ascii=False))
    else:
        print("Paradiso source monitor — catalog dry-run (no network)")
        print("=" * 60)
        print(f"Eligible records: {len(eligible)}")
        print("By domain:")
        for domain, count in sorted(summary["by_domain"].items()):
            print(f"  {domain}: {count}")
        print("By source_type:")
        for source_type, count in sorted(summary["by_source_type"].items()):
            print(f"  {source_type}: {count}")
        if args.list_disabled:
            print("Disabled records:")
            for rec in disabled:
                print(
                    "  - "
                    f"{rec['catalog']}:{rec.get('source_id')} "
                    f"reason={rec.get('reason')}"
                )
        if not eligible:
            print("No monitor-enabled records are currently eligible. Exiting cleanly.")

    return 0


def main(argv: Optional[List[str]] = None) -> int:
    args = _parse_args(argv)
    if args.allow_network and args.local_only:
        print("ERROR: --allow-network and --local-only are mutually exclusive", file=sys.stderr)
        return 2

    if args.catalog_dry_run:
        return _run_catalog_dry_run(args)

    allow_network = bool(args.allow_network) and not args.local_only
    registry = _load_registry(args.registry)
    sources = registry.get("sources", [])
    validation_errors: List[str] = []
    for idx, rec in enumerate(sources):
        if not isinstance(rec, dict):
            validation_errors.append(f"sources[{idx}]: not an object")
            continue
        validation_errors.extend(_validate_record(rec, idx))
    if validation_errors:
        for err in validation_errors:
            print(f"ERROR: {err}", file=sys.stderr)
        return 2
    results = [_check_source(rec, allow_network) for rec in sources]
    summary = _summarize(results)
    if args.json:
        print(json.dumps({"schema_version": "1.0","checked_at": _now_iso(),"allow_network": allow_network,"results": results,"summary": summary}, indent=2, ensure_ascii=False))
    else:
        print("Paradiso source monitor — report-only")
        print("=" * 60)
        for r in results:
            bits = [r.get("state", "?"), r.get("id", "?"), f"({r.get('type', '?')})"]
            if "local_path" in r: bits.append(f"local_path={r['local_path']}")
            if "url" in r and r["url"]: bits.append(f"url={r['url']}")
            if "reason" in r: bits.append(f"reason={r['reason']}")
            print("  - " + " ".join(str(b) for b in bits))
    if args.strict:
        for r, rec in zip(results, sources):
            if rec.get("status") == "active" and r.get("state") in ("changed", "missing"):
                return 1
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
