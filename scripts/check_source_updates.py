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

Exit codes:

- 0 by default in report mode, including when changes are detected.
- 0 when ``--strict`` is passed and all ``active`` local sources
  report ``unchanged``.
- 1 when ``--strict`` is passed and any ``active`` local source
  reports ``changed`` or ``missing``.
- 2 on registry parse / validation errors.

See ``docs/source_monitoring_pipeline.md``.
"""
from __future__ import annotations

import argparse
import hashlib
import html.parser
import json
import os
import re
import sys
from datetime import datetime, timezone
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener

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

# hwp_manual is the 배포용 HWP the ministry publishes; the PDF editions are
# exports of it. Both are local-file manuals and follow the same path below.
_MANUAL_TYPES = {"pdf_manual", "hwp_manual"}
_VALID_TYPES = _MANUAL_TYPES | {"law_api", "notice_index"}
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
_CATALOG_BOOLEAN_FIELDS = ("monitor_enabled", "scrape_allowed", "requires_login")
_CATALOG_CANDIDATE_ACTIVATION_STATUSES = {"candidate_only", "allowlist_test"}
_CATALOG_ALLOWED_DOMAINS = {"notices", "civil_forms"}
_CATALOG_ALLOWED_SOURCE_TYPES = {
    "notice_index",
    "form_catalog",
    "guide_index",
    "static_guide_index",
}
_CATALOG_OFFICIAL_HOST_SUFFIXES = ("hikorea.go.kr", "immigration.go.kr")
_CATALOG_USER_AGENT = (
    "Paradiso source-monitor research/0.1 "
    "(default-off allowlisted catalog check)"
)
_DEFAULT_FETCH_TIMEOUT_SECONDS = 5.0
_DEFAULT_FETCH_MAX_BYTES = 512 * 1024
_FetchResult = Tuple[bytes, str]
_FetchFn = Callable[[str, float, int, Iterable[str]], _FetchResult]


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
    if rec_type in _MANUAL_TYPES and not rec.get("local_path"):
        errors.append(
            f"sources[{idx}] id={rec.get('id')!r}: {rec_type} entries must "
            "declare local_path"
        )
    return errors


def _validate_catalog_record(rec: Dict[str, Any], idx: int, label: str) -> List[str]:
    errors: List[str] = []
    for field in sorted(_REQUIRED_CATALOG_FIELDS):
        if field not in rec:
            errors.append(f"{label}.sources[{idx}]: missing required field '{field}'")
    for field in _CATALOG_BOOLEAN_FIELDS:
        if field in rec and not isinstance(rec[field], bool):
            errors.append(
                f"{label}.sources[{idx}]: field '{field}' must be boolean"
            )
    return errors


def _disabled_reason(rec: Dict[str, Any]) -> Optional[str]:
    if rec["monitor_enabled"] is False:
        return "monitor_enabled=false"
    if rec["scrape_allowed"] is False:
        return "scrape_allowed=false"
    if rec["requires_login"] is True:
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

            record_errors = _validate_catalog_record(rec, idx, label)
            if record_errors:
                validation_errors.extend(record_errors)
                continue

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


def _url_host(url: Optional[str]) -> Optional[str]:
    if not url:
        return None
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        return None
    return parsed.hostname.lower()


def _is_official_catalog_host(host: Optional[str]) -> bool:
    if not host:
        return False
    return any(
        host == suffix or host.endswith(f".{suffix}")
        for suffix in _CATALOG_OFFICIAL_HOST_SUFFIXES
    )


def _candidate_allowed_hosts(catalogs: List[Tuple[str, Dict[str, Any]]]) -> List[str]:
    allowed_hosts = set()
    for _, catalog in catalogs:
        for rec in catalog.get("sources", []):
            if not isinstance(rec, dict):
                continue
            if rec.get("monitor_candidate") is not True:
                continue
            activation_status = rec.get("activation_status")
            if activation_status not in _CATALOG_CANDIDATE_ACTIVATION_STATUSES:
                continue
            if rec.get("scrape_allowed") is not True:
                continue
            if rec.get("requires_login") is not False:
                continue
            if rec.get("source_type") not in _CATALOG_ALLOWED_SOURCE_TYPES:
                continue
            if rec.get("domain") not in _CATALOG_ALLOWED_DOMAINS:
                continue

            host = _url_host(rec.get("url"))
            if _is_official_catalog_host(host):
                allowed_hosts.add(str(host))

    return sorted(allowed_hosts)


class _IndexHTMLTextExtractor(html.parser.HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._skip_depth = 0
        self._in_title = False
        self.title_parts: List[str] = []
        self.body_parts: List[str] = []

    def handle_starttag(
        self,
        tag: str,
        attrs: List[Tuple[str, Optional[str]]],
    ) -> None:
        if tag in ("script", "style", "noscript"):
            self._skip_depth += 1
        elif tag == "title":
            self._in_title = True

    def handle_endtag(self, tag: str) -> None:
        if tag in ("script", "style", "noscript") and self._skip_depth:
            self._skip_depth -= 1
        elif tag == "title":
            self._in_title = False

    def handle_data(self, data: str) -> None:
        if self._skip_depth:
            return
        text = data.strip()
        if not text:
            return
        if self._in_title:
            self.title_parts.append(text)
        else:
            self.body_parts.append(text)


def _normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _extract_index_snapshot(
    body: bytes,
    content_type: str = "text/html",
) -> Dict[str, Any]:
    charset = "utf-8"
    content_type_parts = content_type.split(";")
    for part in content_type_parts[1:]:
        key, _, value = part.strip().partition("=")
        if key.lower() == "charset" and value:
            charset = value.strip()
            break

    text = body.decode(charset, errors="replace")
    parser = _IndexHTMLTextExtractor()
    parser.feed(text)
    title = _normalize_text(" ".join(parser.title_parts))
    index_text = _normalize_text(" ".join(parser.body_parts))
    fingerprint_text = "\n".join(part for part in (title, index_text) if part)
    digest = hashlib.sha256(fingerprint_text.encode("utf-8")).hexdigest()

    return {
        "content_hash": f"sha256:{digest}",
        "title": title or None,
        "text_length": len(index_text),
    }


class _BlockedRedirectError(RuntimeError):
    pass


class _AllowlistedRedirectHandler(HTTPRedirectHandler):
    def __init__(self, allowed_hosts: Iterable[str]) -> None:
        self.allowed_hosts = set(allowed_hosts)
        super().__init__()

    def redirect_request(
        self,
        req: Request,
        fp: Any,
        code: int,
        msg: str,
        headers: Any,
        newurl: str,
    ) -> Optional[Request]:
        new_host = _url_host(newurl)
        if new_host not in self.allowed_hosts:
            raise _BlockedRedirectError(f"redirect blocked to host {new_host!r}")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _fetch_url(
    url: str,
    timeout_seconds: float,
    max_bytes: int,
    allowed_hosts: Iterable[str],
) -> _FetchResult:
    request = Request(
        url,
        headers={
            "User-Agent": _CATALOG_USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,text/plain;q=0.9,*/*;q=0.1",
        },
        method="GET",
    )
    opener = build_opener(_AllowlistedRedirectHandler(allowed_hosts))
    with opener.open(request, timeout=timeout_seconds) as response:
        body = response.read(max_bytes + 1)
        if len(body) > max_bytes:
            raise ValueError("response_too_large")
        content_type = response.headers.get("Content-Type", "text/html")
        return body, content_type


def _catalog_fetch_result_base(
    label: str,
    rec: Dict[str, Any],
) -> Dict[str, Any]:
    url = rec.get("url")
    return {
        "catalog": label,
        "source_id": rec.get("source_id"),
        "url": url,
        "host": _url_host(url),
    }


def _evaluate_catalog_fetches(
    catalogs: List[Tuple[str, Dict[str, Any]]],
    allow_network: bool,
    timeout_seconds: float,
    max_bytes: int,
    fetcher: Optional[_FetchFn] = None,
) -> List[Dict[str, Any]]:
    allowed_hosts = _candidate_allowed_hosts(catalogs)
    fetch = fetcher or _fetch_url
    results: List[Dict[str, Any]] = []

    for label, catalog in catalogs:
        for rec in catalog.get("sources", []):
            if not isinstance(rec, dict):
                continue

            result = _catalog_fetch_result_base(label, rec)
            if rec.get("monitor_candidate") is not True:
                results.append(
                    {**result, "state": "skipped", "reason": "candidate_disabled"}
                )
                continue
            activation_status = rec.get("activation_status")
            if activation_status not in _CATALOG_CANDIDATE_ACTIVATION_STATUSES:
                results.append(
                    {**result, "state": "skipped", "reason": "candidate_disabled"}
                )
                continue
            if rec.get("source_type") not in _CATALOG_ALLOWED_SOURCE_TYPES:
                results.append(
                    {**result, "state": "blocked", "reason": "unsupported_source_type"}
                )
                continue
            if rec.get("domain") not in _CATALOG_ALLOWED_DOMAINS:
                results.append(
                    {**result, "state": "blocked", "reason": "unsupported_domain"}
                )
                continue
            if rec.get("scrape_allowed") is not True:
                results.append(
                    {**result, "state": "blocked", "reason": "scrape_not_allowed"}
                )
                continue
            if rec.get("requires_login") is not False:
                results.append(
                    {**result, "state": "blocked", "reason": "requires_login"}
                )
                continue
            if not allow_network:
                results.append(
                    {**result, "state": "skipped", "reason": "network_disabled"}
                )
                continue
            if not rec.get("url"):
                results.append({**result, "state": "skipped", "reason": "no_url"})
                continue
            if result["host"] not in allowed_hosts:
                results.append({**result, "state": "blocked", "reason": "blocked_host"})
                continue

            try:
                body, content_type = fetch(
                    rec["url"],
                    timeout_seconds,
                    max_bytes,
                    allowed_hosts,
                )
                snapshot = _extract_index_snapshot(body, content_type)
            except _BlockedRedirectError:
                results.append(
                    {**result, "state": "blocked", "reason": "blocked_host"}
                )
            except ValueError as exc:
                results.append(
                    {**result, "state": "blocked", "reason": str(exc)}
                )
            except (HTTPError, URLError, OSError) as exc:
                results.append(
                    {
                        **result,
                        "state": "fetch_error",
                        "reason": exc.__class__.__name__,
                    }
                )
            else:
                results.append(
                    {
                        **result,
                        "state": "fetched",
                        "reason": "ok",
                        "fetched_at": _now_iso(),
                        **snapshot,
                    }
                )

    return results


def _check_local(rec: Dict[str, Any]) -> Dict[str, Any]:
    local_path = rec.get("local_path")
    if not local_path:
        return {"state": "skipped", "reason": "no_local_path"}
    abs_path = (
        local_path
        if os.path.isabs(local_path)
        else os.path.join(REPO_ROOT, local_path)
    )
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
    if rec_type in _MANUAL_TYPES:
        return {**base, **_check_local(rec)}
    if rec_type in ("law_api", "notice_index"):
        if rec_status == "not_configured":
            return {
                **base,
                "state": "skipped",
                "reason": "not_configured",
                "url": rec.get("url"),
            }
        return {**base, **_check_network_entry(rec, allow_network)}
    return {**base, "state": "skipped", "reason": f"unknown_type:{rec_type}"}


def _summarize(results: List[Dict[str, Any]]) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for r in results:
        counts[r["state"]] = counts.get(r["state"], 0) + 1
    counts["total"] = len(results)
    return counts


def _format_human(results: List[Dict[str, Any]], summary: Dict[str, int]) -> str:
    lines: List[str] = []
    lines.append("Paradiso source monitor — report-only")
    lines.append("=" * 60)
    for r in results:
        bits = [
            r.get("state", "?"),
            r.get("id", "?"),
            f"({r.get('type', '?')})",
        ]
        if "local_path" in r:
            bits.append(f"local_path={r['local_path']}")
        if "url" in r and r["url"]:
            bits.append(f"url={r['url']}")
        if "reason" in r:
            bits.append(f"reason={r['reason']}")
        if r.get("state") == "changed":
            bits.append(f"previous_hash={r.get('previous_hash')}")
            bits.append(f"current_hash={r.get('current_hash')}")
        lines.append("  - " + " ".join(str(b) for b in bits))
    lines.append("")
    lines.append("Summary:")
    for k in sorted(summary):
        lines.append(f"  {k}: {summary[k]}")
    lines.append("")
    lines.append(
        "Note: This script never modifies the registry, never writes "
        "state files, and never edits production data."
    )
    return "\n".join(lines)


def _parse_args(argv: Optional[List[str]]) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Report-only source monitor for Paradiso AI."
    )
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
        help=(
            "Permit network-backed entries. Legacy registry entries still do not "
            "fetch; catalog dry-runs may fetch tightly allowlisted candidates."
        ),
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
    p.add_argument(
        "--fetch-timeout-seconds",
        type=float,
        default=_DEFAULT_FETCH_TIMEOUT_SECONDS,
        help=(
            "HTTP timeout for allowlisted catalog fetches when --allow-network "
            "is passed (default: %(default)s)."
        ),
    )
    p.add_argument(
        "--fetch-max-bytes",
        type=int,
        default=_DEFAULT_FETCH_MAX_BYTES,
        help=(
            "Maximum response bytes for allowlisted catalog fetches when "
            "--allow-network is passed (default: %(default)s)."
        ),
    )
    return p.parse_args(argv)


def _run_catalog_dry_run(
    args: argparse.Namespace,
    fetcher: Optional[_FetchFn] = None,
) -> int:
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
    fetch_results = _evaluate_catalog_fetches(
        catalogs,
        allow_network=bool(args.allow_network),
        timeout_seconds=args.fetch_timeout_seconds,
        max_bytes=args.fetch_max_bytes,
        fetcher=fetcher,
    )
    if args.json:
        out = {
            "allow_network": bool(args.allow_network),
            "mode": "catalog_dry_run",
            "eligible": eligible,
            "disabled": disabled if args.list_disabled else [],
            "results": fetch_results,
            "summary": summary,
        }
        print(json.dumps(out, indent=2, ensure_ascii=False))
    else:
        mode_note = "allowlisted network enabled" if args.allow_network else "no network"
        print(f"Paradiso source monitor — catalog dry-run ({mode_note})")
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
        print("Allowlisted fetch adapter:")
        for result in fetch_results:
            if result["reason"] == "candidate_disabled" and not args.list_disabled:
                continue
            bits = [
                result.get("state", "?"),
                result.get("source_id", "?"),
                f"reason={result.get('reason')}",
            ]
            if result.get("host"):
                bits.append(f"host={result['host']}")
            if result.get("title"):
                bits.append(f"title={result['title']}")
            linestr = "  - " + " ".join(str(bit) for bit in bits)
            print(linestr)

    return 0


def main(argv: Optional[List[str]] = None) -> int:
    args = _parse_args(argv)
    if args.allow_network and args.local_only:
        print(
            "ERROR: --allow-network and --local-only are mutually exclusive",
            file=sys.stderr,
        )
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
        out = {
            "schema_version": "1.0",
            "checked_at": _now_iso(),
            "allow_network": allow_network,
            "results": results,
            "summary": summary,
        }
        print(json.dumps(out, indent=2, ensure_ascii=False))
    else:
        print(_format_human(results, summary))
    if args.strict:
        for r, rec in zip(results, sources):
            if rec.get("status") != "active":
                continue
            if r.get("state") in ("changed", "missing"):
                return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
