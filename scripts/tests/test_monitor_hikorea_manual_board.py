#!/usr/bin/env python3
"""Tests for scripts/monitor_hikorea_manual_board.py — HiKorea board detection.

Standalone (`python3 scripts/tests/test_monitor_hikorea_manual_board.py`) or
pytest. No network: a fake fetcher is injected. Verifies unchanged/changed/
baseline-unset/unreachable classification, host allowlisting, the offline
default, and that detection writes to no protected data file.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import monitor_hikorea_manual_board as mon  # noqa: E402
import check_source_updates as csu  # noqa: E402

PROTECTED = ["visa_data.json", "doc_master.json", "backend/data/visas.json",
             "data/sources/hikorea_manual_board_watch.json"]


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else "absent"


def _html(title: str, body: str) -> bytes:
    return f"<html><head><title>{title}</title></head><body>{body}</body></html>".encode("utf-8")


def _fingerprint(title: str, body: str) -> str:
    snap = csu._extract_index_snapshot(_html(title, body), "text/html; charset=utf-8")
    return snap["content_hash"]


def _cfg(baseline):
    return {"targets": [{
        "id": "hikorea_materials_board",
        "title_ko": "자료실",
        "url": "https://www.hikorea.go.kr/board/BoardDataListR.pt?page=1",
        "baseline_content_hash": baseline,
    }]}


def _fetcher(title, body):
    def f(url, timeout, max_bytes, allowed_hosts):
        return _html(title, body), "text/html; charset=utf-8"
    return f


def test_unchanged():
    fp = _fingerprint("자료실", "매뉴얼 목록 A B C")
    res = mon.evaluate_targets(_cfg(fp), allow_network=True, fetcher=_fetcher("자료실", "매뉴얼 목록 A B C"))
    assert res[0]["state"] == "unchanged", res


def test_changed():
    old = _fingerprint("자료실", "매뉴얼 목록 A B C")
    res = mon.evaluate_targets(_cfg(old), allow_network=True,
                               fetcher=_fetcher("자료실", "매뉴얼 목록 A B C D 신규매뉴얼"))
    assert res[0]["state"] == "changed", res
    assert res[0]["current_content_hash"] != old


def test_baseline_unset():
    res = mon.evaluate_targets(_cfg(None), allow_network=True,
                               fetcher=_fetcher("자료실", "매뉴얼 목록"))
    assert res[0]["state"] == "baseline_unset", res


def test_unreachable_is_not_a_crash_or_change():
    def boom(url, timeout, max_bytes, allowed_hosts):
        raise TimeoutError("gov site blocked CI egress")
    res = mon.evaluate_targets(_cfg("sha256:abc"), allow_network=True, fetcher=boom)
    assert res[0]["state"] == "unreachable", res
    # unreachable must NOT be reported as changed
    assert res[0]["state"] != "changed"


def test_offline_default_skips():
    res = mon.evaluate_targets(_cfg("sha256:abc"), allow_network=False, fetcher=_fetcher("x", "y"))
    assert res[0]["state"] == "skipped"
    assert res[0]["reason"] == "network_disabled"


def test_host_allowlist_blocks_offhost():
    cfg = {"targets": [{"id": "evil", "title_ko": "x",
                        "url": "https://evil.example.com/board", "baseline_content_hash": None}]}
    res = mon.evaluate_targets(cfg, allow_network=True, fetcher=_fetcher("x", "y"))
    assert res[0]["state"] == "blocked"
    assert res[0]["reason"].startswith("host_not_allowed")


def test_committed_config_is_valid_and_hikorea_only():
    cfg = json.loads((ROOT / "data/sources/hikorea_manual_board_watch.json").read_text(encoding="utf-8"))
    assert cfg["targets"], "watch config must declare targets"
    for t in cfg["targets"]:
        host = csu._url_host(t["url"])
        assert host in mon.ALLOWED_HOSTS, f"non-allowlisted host {host}"


def test_no_protected_file_writes(tmp_path):
    before = {f: _sha(ROOT / f) for f in PROTECTED}
    out_json = tmp_path / "r.json"
    out_md = tmp_path / "r.md"
    # offline run against the real committed config
    rc = mon.main(["--out-json", str(out_json), "--out-md", str(out_md)])
    assert rc == 0  # offline -> skipped -> no change
    assert out_json.exists() and out_md.exists()
    after = {f: _sha(ROOT / f) for f in PROTECTED}
    assert before == after, "detection must never modify protected/config files"


def _run_all_standalone() -> int:
    import inspect
    import tempfile
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    failed = 0
    for t in tests:
        try:
            if inspect.signature(t).parameters:
                with tempfile.TemporaryDirectory() as td:
                    t(Path(td))
            else:
                t()
            print(f"PASS {t.__name__}")
        except Exception as e:  # noqa: BLE001
            failed += 1
            print(f"FAIL {t.__name__}: {e}")
    print(f"\n{len(tests) - failed}/{len(tests)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(_run_all_standalone())
