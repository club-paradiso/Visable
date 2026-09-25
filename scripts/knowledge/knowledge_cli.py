#!/usr/bin/env python3
"""Waymaker Knowledge Platform — operator / CI command line.

Everything the Knowledge Studio does is also available here, against a local
or explicitly chosen database. Mutating commands default to a preview.

    # state
    knowledge_cli.py overview
    knowledge_cli.py bootstrap                       # registry sync + legacy seed (idempotent)

    # ingestion (dry-run by default; --apply writes proposals to the review queue)
    knowledge_cli.py ingest --adapter status_guidance --status D-2 --dry-run
    knowledge_cli.py ingest --adapter status_guidance --status D-2 --apply --actor parser:status_guidance
    knowledge_cli.py ingest --adapter extraction_json --file out.json --validate

    # review (a named human operator is required for every action)
    knowledge_cli.py queue
    knowledge_cli.py act <fact_id> approve --operator alice --reason "matches p.43"

    # diff / evals / export
    knowledge_cli.py diff --from stay_manual_2026_06_23_pdf --to stay_manual_2026_09_18_pdf --status D-2
    knowledge_cli.py eval [--selector tag:ci] [--strict] [--json]
    knowledge_cli.py export > published.json
    knowledge_cli.py purge-observations

Database: --db PATH (default: $WAYMAKER_KNOWLEDGE_DB or backend/var/knowledge/...).
Use --db :memory: for a throwaway run (CI does this). The CLI never connects to
a remote database and never deploys anything.
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "backend"))


def _platform(args):
    if args.db:
        os.environ["WAYMAKER_KNOWLEDGE_DB"] = args.db
    from services.knowledge.runtime import KnowledgePlatform, set_platform_for_tests
    platform = KnowledgePlatform.create(args.db or None)
    set_platform_for_tests(platform)
    return platform


def _print(obj, as_json=True):
    print(json.dumps(obj, ensure_ascii=False, indent=2, default=str) if as_json else obj)


def cmd_overview(p, args):
    _print(p.overview())


def cmd_bootstrap(p, args):
    _print(p.bootstrap_report)


def cmd_ingest(p, args):
    from services.knowledge import adapters
    from services.knowledge.ingestion import as_report_text
    if args.adapter == "status_guidance":
        proposals = adapters.status_guidance_proposals(p.repo, statuses=args.status or None,
                                                       procedures=args.procedure or ["extension"])
        actor, kind = args.actor or "parser:status_guidance", "parser"
    elif args.adapter == "extraction_json":
        if not args.file:
            sys.exit("--file is required for extraction_json")
        proposals = adapters.extraction_json_proposals(args.file)
        actor, kind = args.actor or "ai_extractor:extraction_json", "ai_extractor"
    else:
        sys.exit(f"unknown adapter {args.adapter}")
    mode = "apply" if args.apply else "validate" if args.validate else "dry_run"
    report = p.ingestion.run(args.adapter, proposals, mode=mode, actor=actor, actor_kind=kind)
    _print(report.to_dict()) if args.json else print(as_report_text(report))


def cmd_queue(p, args):
    for t in p.review.queue(status=args.status):
        print(f"{t['priority_score']:>4}  {t['task_id']}  {t['task_kind']:<14} {t['variant_key']:<30} "
              f"{t['lifecycle_state']:<22} {t['value_text'][:60]}")


def cmd_act(p, args):
    from services.knowledge.models import ReviewActionRequest
    if not args.operator:
        sys.exit("--operator NAME is required: review actions are human acts")
    req = ReviewActionRequest(action=args.action, reason=args.reason or "", value_text=args.value)
    _print(p.review.act(args.fact_id, req, actor=args.operator))


def cmd_diff(p, args):
    from services.knowledge.diff import diff_versions
    key = args.source
    a = p.repo.find_source_version(key, args.from_edition)
    b = p.repo.find_source_version(key, args.to_edition)
    if not a or not b:
        sys.exit("unknown edition(s); see `overview` / sources")
    props = None if args.property == "all" else [args.property]
    d = diff_versions(p.repo, a["source_version_id"], b["source_version_id"], status_code=args.status,
                      procedure=args.procedure, properties=props, include_unchanged=not args.changes_only)
    if args.json:
        _print(d)
        return
    print(f"{d['source_key']}: {d['from']['version']} -> {d['to']['version']}  {d['summary']}")
    for r in d["records"]:
        before = (r["from"] or {}).get("value_text", "")
        after = (r["to"] or {}).get("value_text", "")
        print(f"  {r['change']:<9} {','.join(r['changed_fields']) or '-':<32} {before[:40]!r} -> {after[:40]!r}")


def cmd_eval(p, args):
    from services.knowledge.evals import report_text
    run = p.evals.run(selector=args.selector)
    if args.json:
        _print({k: v for k, v in run.items()})
    else:
        print(report_text(run))
    if args.strict and run["failed"]:
        sys.exit(1)


def cmd_export(p, args):
    _print(p.export_published())


def cmd_export_evals(p, args):
    _print({"cases": p.evals.list_cases()})


def cmd_purge(p, args):
    print(f"purged {p.learning.purge_expired()} expired observations")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--db", help="knowledge DB path (':memory:' for a throwaway run)")
    ap.add_argument("-v", "--verbose", action="store_true")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("overview")
    sub.add_parser("bootstrap")
    ing = sub.add_parser("ingest")
    ing.add_argument("--adapter", required=True, choices=["status_guidance", "extraction_json"])
    ing.add_argument("--status", action="append")
    ing.add_argument("--procedure", action="append")
    ing.add_argument("--file")
    ing.add_argument("--actor")
    grp = ing.add_mutually_exclusive_group()
    grp.add_argument("--dry-run", action="store_true", help="classify, write nothing (default)")
    grp.add_argument("--validate", action="store_true", help="validate only, write nothing")
    grp.add_argument("--apply", action="store_true", help="insert proposals + open review tasks")
    ing.add_argument("--json", action="store_true")
    q = sub.add_parser("queue")
    q.add_argument("--status", default="open")
    act = sub.add_parser("act")
    act.add_argument("fact_id")
    act.add_argument("action", choices=["start_review", "approve", "verify", "publish", "reject",
                                        "needs_evidence", "edit", "withdraw"])
    act.add_argument("--operator")
    act.add_argument("--reason")
    act.add_argument("--value")
    df = sub.add_parser("diff")
    df.add_argument("--source", default="stay_guide_manual")
    df.add_argument("--from", dest="from_edition", required=True)
    df.add_argument("--to", dest="to_edition", required=True)
    df.add_argument("--status")
    df.add_argument("--procedure")
    df.add_argument("--property", default="required_document",
                    help="fact property to compare (default required_document; 'all' for every property)")
    df.add_argument("--changes-only", action="store_true")
    df.add_argument("--json", action="store_true")
    ev = sub.add_parser("eval")
    ev.add_argument("--selector", default="all")
    ev.add_argument("--strict", action="store_true")
    ev.add_argument("--json", action="store_true")
    sub.add_parser("export")
    sub.add_parser("export-evals")
    sub.add_parser("purge-observations")
    args = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO if args.verbose else logging.WARNING)
    platform = _platform(args)
    {
        "overview": cmd_overview, "bootstrap": cmd_bootstrap, "ingest": cmd_ingest, "queue": cmd_queue,
        "act": cmd_act, "diff": cmd_diff, "eval": cmd_eval, "export": cmd_export,
        "export-evals": cmd_export_evals, "purge-observations": cmd_purge,
    }[args.cmd](platform, args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
