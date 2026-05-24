from __future__ import annotations

import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from types import SimpleNamespace

THIS_DIR = os.path.abspath(os.path.dirname(__file__))
REPO_ROOT = os.path.abspath(os.path.join(THIS_DIR, "..", ".."))
SCRIPTS_DIR = os.path.join(REPO_ROOT, "scripts")
FIXTURES_DIR = os.path.join(THIS_DIR, "fixtures")
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

import check_source_updates as csu  # noqa: E402


class SourceMonitorTests(unittest.TestCase):
    def _write_catalog(self, path: str, sources: list[dict]) -> None:
        with open(path, "w", encoding="utf-8") as fh:
            json.dump({"sources": sources}, fh)

    def _candidate_record(self, **overrides):
        record = {
            "source_id": "hikorea_notice_index",
            "source_type": "notice_index",
            "url": "https://www.hikorea.go.kr/board/notice",
            "domain": "notices",
            "monitor_enabled": False,
            "monitor_candidate": True,
            "activation_status": "candidate_only",
            "scrape_allowed": True,
            "requires_login": False,
        }
        record.update(overrides)
        return record

    def _run_catalog_json(self, h_sources: list[dict], i_sources: list[dict], *args):
        with tempfile.TemporaryDirectory() as td:
            h = os.path.join(td, "h.json")
            i = os.path.join(td, "i.json")
            self._write_catalog(h, h_sources)
            self._write_catalog(i, i_sources)

            buf = io.StringIO()
            with redirect_stdout(buf):
                rc = csu.main(
                    [
                        "--catalog-dry-run",
                        "--hikorea-catalog",
                        h,
                        "--immigration-catalog",
                        i,
                        "--json",
                        *args,
                    ]
                )
            return rc, json.loads(buf.getvalue())

    def test_catalog_loading(self):
        with tempfile.TemporaryDirectory() as td:
            p = os.path.join(td, "catalog.json")
            self._write_catalog(
                p,
                [
                    {
                        "source_id": "x",
                        "source_type": "notice",
                        "url": "https://a",
                        "domain": "a",
                        "monitor_enabled": True,
                        "scrape_allowed": True,
                        "requires_login": False,
                    }
                ],
            )
            loaded = csu._load_catalog(p)
            self.assertIn("sources", loaded)

    def test_required_field_validation(self):
        errors = csu._validate_catalog_record({"source_id": "x"}, 0, "test")
        self.assertTrue(any("missing required field" in e for e in errors))

    def test_catalog_boolean_fields_must_be_booleans(self):
        valid = {
            "source_id": "x",
            "source_type": "notice",
            "url": "https://a",
            "domain": "a",
            "monitor_enabled": True,
            "scrape_allowed": True,
            "requires_login": False,
        }

        for field in ("monitor_enabled", "scrape_allowed", "requires_login"):
            with self.subTest(field=field):
                rec = dict(valid)
                rec[field] = "false"
                errors = csu._validate_catalog_record(rec, 0, "test")
                self.assertTrue(
                    any(f"field '{field}' must be boolean" in e for e in errors)
                )

    def test_legacy_human_output_contains_summary_and_note(self):
        with tempfile.TemporaryDirectory() as td:
            reg = os.path.join(td, "registry.json")
            with open(reg, "w", encoding="utf-8") as fh:
                json.dump(
                    {
                        "sources": [
                            {
                                "id": "n1",
                                "type": "law_api",
                                "title": "t",
                                "status": "active",
                                "url": "https://example.com",
                            }
                        ]
                    },
                    fh,
                )

            buf = io.StringIO()
            with redirect_stdout(buf):
                rc = csu.main(["--registry", reg])
            out = buf.getvalue()

            self.assertEqual(rc, 0)
            self.assertIn("Summary:", out)
            self.assertIn("never modifies the registry", out)

    def test_all_disabled_records_dry_run(self):
        with tempfile.TemporaryDirectory() as td:
            h = os.path.join(td, "h.json")
            i = os.path.join(td, "i.json")
            disabled = [
                {
                    "source_id": "x",
                    "source_type": "notice",
                    "url": "https://a",
                    "domain": "a",
                    "monitor_enabled": False,
                    "scrape_allowed": True,
                    "requires_login": False,
                }
            ]
            self._write_catalog(h, disabled)
            self._write_catalog(i, disabled)
            rc = csu.main(
                [
                    "--catalog-dry-run",
                    "--hikorea-catalog",
                    h,
                    "--immigration-catalog",
                    i,
                ]
            )
            self.assertEqual(rc, 0)

    def test_catalog_dry_run_rejects_malformed_boolean(self):
        with tempfile.TemporaryDirectory() as td:
            h = os.path.join(td, "h.json")
            i = os.path.join(td, "i.json")
            record = {
                "source_id": "x",
                "source_type": "notice",
                "url": "https://a",
                "domain": "a",
                "monitor_enabled": True,
                "scrape_allowed": True,
                "requires_login": False,
            }
            malformed = dict(record)
            malformed["requires_login"] = "false"
            self._write_catalog(h, [malformed])
            self._write_catalog(i, [record])

            err = io.StringIO()
            with redirect_stderr(err):
                rc = csu.main(
                    [
                        "--catalog-dry-run",
                        "--hikorea-catalog",
                        h,
                        "--immigration-catalog",
                        i,
                    ]
                )

            self.assertEqual(rc, 2)
            self.assertIn("field 'requires_login' must be boolean", err.getvalue())

    def test_no_network_default_behavior(self):
        with tempfile.TemporaryDirectory() as td:
            reg = os.path.join(td, "registry.json")
            with open(reg, "w", encoding="utf-8") as fh:
                json.dump(
                    {
                        "sources": [
                            {
                                "id": "n1",
                                "type": "law_api",
                                "title": "t",
                                "status": "active",
                                "url": "https://example.com",
                            }
                        ]
                    },
                    fh,
                )

            buf = io.StringIO()
            with redirect_stdout(buf):
                rc = csu.main(["--registry", reg, "--json"])
            out = json.loads(buf.getvalue())

            self.assertEqual(rc, 0)
            self.assertEqual(out["results"][0]["reason"], "network_disabled")
            self.assertEqual(out["results"][0]["state"], "skipped")

    def test_catalog_dry_run_json_mode(self):
        with tempfile.TemporaryDirectory() as td:
            h = os.path.join(td, "h.json")
            i = os.path.join(td, "i.json")
            disabled = [
                {
                    "source_id": "x",
                    "source_type": "notice",
                    "url": "https://a",
                    "domain": "a",
                    "monitor_enabled": False,
                    "scrape_allowed": True,
                    "requires_login": False,
                }
            ]
            self._write_catalog(h, disabled)
            self._write_catalog(i, disabled)

            buf = io.StringIO()
            with redirect_stdout(buf):
                rc = csu.main(
                    [
                        "--catalog-dry-run",
                        "--hikorea-catalog",
                        h,
                        "--immigration-catalog",
                        i,
                        "--json",
                    ]
                )
            out = json.loads(buf.getvalue())

            self.assertEqual(rc, 0)
            self.assertEqual(out["mode"], "catalog_dry_run")
            self.assertFalse(out["allow_network"])

    def test_index_snapshot_extraction_from_fixture(self):
        fixture = os.path.join(FIXTURES_DIR, "hikorea_notice_index.html")
        with open(fixture, "rb") as fh:
            snapshot = csu._extract_index_snapshot(fh.read())

        self.assertEqual(snapshot["title"], "HiKorea Notices")
        self.assertTrue(snapshot["content_hash"].startswith("sha256:"))
        self.assertGreater(snapshot["text_length"], 20)

    def test_catalog_candidate_blocks_network_by_default(self):
        rc, out = self._run_catalog_json([self._candidate_record()], [])

        self.assertEqual(rc, 0)
        self.assertFalse(out["allow_network"])
        result = out["results"][0]
        self.assertEqual(result["source_id"], "hikorea_notice_index")
        self.assertEqual(result["state"], "skipped")
        self.assertEqual(result["reason"], "network_disabled")
        self.assertNotIn("content_hash", result)

    def test_catalog_candidate_blocks_unallowlisted_host(self):
        rc, out = self._run_catalog_json(
            [self._candidate_record(url="https://example.com/notices")],
            [],
            "--allow-network",
        )

        self.assertEqual(rc, 0)
        result = out["results"][0]
        self.assertEqual(result["host"], "example.com")
        self.assertEqual(result["state"], "blocked")
        self.assertEqual(result["reason"], "blocked_host")

    def test_catalog_candidate_blocks_requires_login(self):
        rc, out = self._run_catalog_json(
            [self._candidate_record(requires_login=True)],
            [],
            "--allow-network",
        )

        self.assertEqual(rc, 0)
        result = out["results"][0]
        self.assertEqual(result["state"], "blocked")
        self.assertEqual(result["reason"], "requires_login")

    def test_catalog_candidate_allowed_path_uses_fake_fetcher(self):
        with tempfile.TemporaryDirectory() as td:
            h = os.path.join(td, "h.json")
            i = os.path.join(td, "i.json")
            self._write_catalog(h, [self._candidate_record()])
            self._write_catalog(i, [])

            fixture = os.path.join(FIXTURES_DIR, "hikorea_notice_index.html")
            with open(fixture, "rb") as fh:
                body = fh.read()

            calls = []

            def fake_fetch(url, timeout_seconds, max_bytes, allowed_hosts):
                calls.append((url, timeout_seconds, max_bytes, tuple(allowed_hosts)))
                return body, "text/html; charset=utf-8"

            args = SimpleNamespace(
                hikorea_catalog=h,
                immigration_catalog=i,
                json=True,
                list_disabled=False,
                allow_network=True,
                fetch_timeout_seconds=1.0,
                fetch_max_bytes=4096,
            )
            buf = io.StringIO()
            with redirect_stdout(buf):
                rc = csu._run_catalog_dry_run(args, fetcher=fake_fetch)
            out = json.loads(buf.getvalue())

        self.assertEqual(rc, 0)
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0][0], "https://www.hikorea.go.kr/board/notice")
        self.assertIn("www.hikorea.go.kr", calls[0][3])
        result = out["results"][0]
        self.assertEqual(result["state"], "fetched")
        self.assertEqual(result["reason"], "ok")
        self.assertEqual(result["title"], "HiKorea Notices")
        self.assertIn("fetched_at", result)
        self.assertTrue(result["content_hash"].startswith("sha256:"))

    def test_single_catalog_dry_run_definition(self):
        script_path = os.path.join(SCRIPTS_DIR, "check_source_updates.py")
        with open(script_path, "r", encoding="utf-8") as fh:
            script_text = fh.read()
        self.assertEqual(script_text.count("def _run_catalog_dry_run"), 1)


if __name__ == "__main__":
    unittest.main()
