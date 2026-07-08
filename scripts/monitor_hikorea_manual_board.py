#!/usr/bin/env python3
"""Detect when a HiKorea manual board changes, so a new 안내 매뉴얼 is noticed
automatically instead of a maintainer polling the site by hand.

For each target in ``data/sources/hikorea_manual_board_watch.json`` this:
  1. Fetches the board index page (reusing the allowlisted, redirect-blocking,
     size-capped fetcher from ``check_source_updates.py`` — hikorea.go.kr /
     immigration.go.kr hosts only).
  2. Fingerprints the page (title + visible text → sha256, via the same
     ``_extract_index_snapshot``).
  3. Compares to the committed ``baseline_content_hash``.

It writes a machine result (JSON) and a Markdown brief. It is deliberately
*advisory*: it never downloads a manual, never edits production data, and never
bumps its own baseline. On a detected change the workflow opens a tracking issue
for a human; the human bumps the baseline here after handling it (same pattern
as ``hikorea_manual_sync.json``'s ``baseline_sha256``).

Reachability caveat: Korean government sites may block CI egress (403 / timeout).
An unreachable target is reported as ``unreachable`` (not a crash and not a
false "changed"), so the operator can see monitoring could not run.

Exit codes:
  0  no change (all targets unchanged, unreachable, or baseline-not-set)
  3  at least one target CHANGED (workflow opens/updates an issue)
  2  config / arg error

Network is OFF unless ``--allow-network`` is passed (offline default is safe for
CI gates and local runs; the scheduled monitor passes the flag).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import check_source_updates as csu  # noqa: E402  (reuse reviewed fetch+fingerprint)

CONFIG = ROOT / "data/sources/hikorea_manual_board_watch.json"
DEFAULT_TIMEOUT = 20.0
DEFAULT_MAX_BYTES = 1_000_000
ALLOWED_HOSTS = ("www.hikorea.go.kr", "hikorea.go.kr",
                 "www.immigration.go.kr", "immigration.go.kr")

# A fetcher matches check_source_updates._fetch_url's signature so tests can
# inject a fake without any network.
FetchFn = Callable[[str, float, int, Any], tuple]


def evaluate_targets(
    config: Dict[str, Any],
    allow_network: bool,
    fetcher: Optional[FetchFn] = None,
    timeout: float = DEFAULT_TIMEOUT,
    max_bytes: int = DEFAULT_MAX_BYTES,
) -> List[Dict[str, Any]]:
    fetch = fetcher or csu._fetch_url
    results: List[Dict[str, Any]] = []
    for target in config.get("targets", []):
        if not isinstance(target, dict):
            continue
        tid = target.get("id")
        url = target.get("url")
        baseline = target.get("baseline_content_hash")
        base = {
            "id": tid,
            "title": target.get("title_ko") or target.get("title_en"),
            "url": url,
            "baseline_content_hash": baseline,
        }
        host = csu._url_host(url)
        if host not in ALLOWED_HOSTS:
            results.append({**base, "state": "blocked", "reason": f"host_not_allowed:{host}"})
            continue
        if not allow_network:
            results.append({**base, "state": "skipped", "reason": "network_disabled"})
            continue
        try:
            body, content_type = fetch(url, timeout, max_bytes, ALLOWED_HOSTS)
            snapshot = csu._extract_index_snapshot(body, content_type)
        except csu._BlockedRedirectError as e:
            results.append({**base, "state": "blocked", "reason": f"redirect_blocked:{e}"})
            continue
        except Exception as e:  # noqa: BLE001 - 403/timeout/geoblock is expected, not fatal
            results.append({**base, "state": "unreachable", "reason": type(e).__name__ + ": " + str(e)[:200]})
            continue

        current = snapshot.get("content_hash")
        entry = {**base, "current_content_hash": current,
                 "title_seen": snapshot.get("title"), "text_length": snapshot.get("text_length")}
        if not baseline:
            entry["state"] = "baseline_unset"
            entry["reason"] = "no committed baseline yet; recording current fingerprint"
        elif current == baseline:
            entry["state"] = "unchanged"
        else:
            entry["state"] = "changed"
        results.append(entry)
    return results


def render_brief(results: List[Dict[str, Any]]) -> str:
    changed = [r for r in results if r["state"] == "changed"]
    unreachable = [r for r in results if r["state"] == "unreachable"]
    lines: List[str] = ["# HiKorea 매뉴얼 게시판 감지 결과", ""]
    if changed:
        lines.append("## ⚠️ 변경 감지 — 새 매뉴얼 가능성, 사람 확인 필요")
        lines.append("")
        for r in changed:
            lines += [
                f"### {r['title']} (`{r['id']}`)",
                f"- URL: {r['url']}",
                f"- baseline: `{r.get('baseline_content_hash')}`",
                f"- 현재:     `{r.get('current_content_hash')}`",
                f"- 게시판 제목: {r.get('title_seen') or '(제목 없음)'}",
                "",
            ]
        lines += [
            "### 다음 단계 (사람)",
            "1. 위 게시판을 열어 새/변경 매뉴얼이 실제로 올라왔는지 확인합니다.",
            "2. 새 매뉴얼이면 HWP를 내려받아 `hikorea-manual-sync` 워크플로에 dispatch "
            "(manual_hwp_visa / manual_hwp_stay)하면, 검증된 추출본과 함께 구조적 diff가 "
            "초안 PR에 첨부됩니다.",
            "3. 처리 후 `data/sources/hikorea_manual_board_watch.json`의 "
            "`baseline_content_hash`를 현재 값으로 갱신해 다음 변경을 새로 감지하게 합니다.",
            "",
        ]
    else:
        lines += ["## 변경 없음", "", "감시 대상 게시판에서 baseline 대비 변경이 감지되지 않았습니다.", ""]

    if unreachable:
        lines += ["## ℹ️ 접근 불가 (감시 미수행)", ""]
        for r in unreachable:
            lines.append(f"- {r['title']} (`{r['id']}`): {r.get('reason')}")
        lines += [
            "",
            "> 한국 정부 사이트가 CI에서 차단(403/타임아웃)됐을 수 있습니다. 감시가 실제로 "
            "수행되지 않았으므로, 이 상태가 지속되면 수동 확인이 필요합니다.",
            "",
        ]

    # Always surface the full state table for transparency.
    lines += ["## 전체 상태", "", "| 대상 | 상태 | 비고 |", "| --- | --- | --- |"]
    for r in results:
        note = r.get("reason") or r.get("current_content_hash") or ""
        lines.append(f"| {r.get('id')} | {r.get('state')} | {str(note)[:80]} |")
    lines.append("")
    return "\n".join(lines) + "\n"


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="Detect HiKorea manual-board changes")
    ap.add_argument("--allow-network", action="store_true",
                    help="permit fetching the allowlisted board URLs (off by default)")
    ap.add_argument("--config", default=str(CONFIG), help="watch config path")
    ap.add_argument("--out-json", help="write the machine result here")
    ap.add_argument("--out-md", help="write the Markdown brief here")
    args = ap.parse_args(argv)

    cfg_path = Path(args.config)
    if not cfg_path.exists():
        print(f"ERROR: watch config not found: {cfg_path}", file=sys.stderr)
        return 2
    try:
        config = json.loads(cfg_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        print(f"ERROR: invalid watch config JSON: {e}", file=sys.stderr)
        return 2

    results = evaluate_targets(config, allow_network=args.allow_network)
    changed = [r for r in results if r["state"] == "changed"]
    report = {
        "changed": bool(changed),
        "changed_ids": [r["id"] for r in changed],
        "results": results,
    }
    brief = render_brief(results)

    if args.out_json:
        p = Path(args.out_json)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.out_md:
        p = Path(args.out_md)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(brief, encoding="utf-8")

    print(json.dumps({"changed": report["changed"], "changed_ids": report["changed_ids"],
                      "states": {r["id"]: r["state"] for r in results}}, ensure_ascii=False))

    return 3 if changed else 0


if __name__ == "__main__":
    sys.exit(main())
