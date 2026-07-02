#!/usr/bin/env python3
"""Build the full status-universe audit matrix (2026-07 post-submission pass).

Dynamically derives every parent status and subcode from:
  * backend/data/visa_authoring/statuses/*.json  (authoring source of truth)
  * visa_data.json                               (generated compatibility layer)
  * backend/data/visas.json                      (generated backend mirror)

and cross-references each record against the readable extractions of the
current official manuals:
  * backend/data/sources/manuals/260617_visa_manual_readable.txt  (사증, 2026.6)
  * backend/data/sources/manuals/260623_stay_manual_readable.txt  (체류, 2026.6)
  * backend/data/sources/manuals/260421_dongpo_manual_readable.txt (동포, 2026.2)
  * backend/data/sources/manuals/260629_kcore_manual_readable.txt (K-CORE, 2026.6)

Nothing is hard-coded about the number of statuses: the universe is computed.

Outputs:
  audits/status-universe-2026-07/status_universe_audit.json
  audits/status-universe-2026-07/status_universe_audit.md

This script is read-only over production data. It never edits visa_data.json,
backend/data/visas.json, doc_master.json, or any authoring file.
"""
from __future__ import annotations

import json
import re
from collections import OrderedDict
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
AUTHORING_DIR = REPO / "backend/data/visa_authoring/statuses"
VISA_DATA = REPO / "visa_data.json"
BACKEND_VISAS = REPO / "backend/data/visas.json"
OUT_DIR = REPO / "audits/status-universe-2026-07"

MANUALS = {
    "visa_2026_06_17": REPO / "backend/data/sources/manuals/260617_visa_manual_readable.txt",
    "stay_2026_06_23": REPO / "backend/data/sources/manuals/260623_stay_manual_readable.txt",
    "dongpo_2026_02": REPO / "backend/data/sources/manuals/260421_dongpo_manual_readable.txt",
    "kcore_2026_06_29": REPO / "backend/data/sources/manuals/260629_kcore_manual_readable.txt",
}

# Special/regional program parents that are not immigration-law status codes;
# they are matched by their Korean program names instead of a code regex.
PROGRAM_NAME_HINTS = {
    "K-STAR": ["K-STAR", "케이스타"],
    "REGION-S": ["지역특화", "광역형"],
    "YOUTH-STAY": ["성장 기반 외국인 청소년", "외국인 청소년"],
    "D-4-2K": ["한국어연수"],
}


def manual_hits(text: str, code: str, name_ko: str) -> int:
    """Count occurrences of a code (or program name) in a manual extraction."""
    hints = PROGRAM_NAME_HINTS.get(code)
    if hints:
        return sum(text.count(h) for h in hints)
    # Escape the code; require a non-code-char boundary after, so D-2 does not
    # match D-2-1 (subcode hits are counted for the subcode row itself).
    pat = re.compile(re.escape(code) + r"(?![-0-9A-Z])")
    n = len(pat.findall(text))
    if n == 0 and name_ko:
        n = text.count(f"{name_ko}({code}")
    return n


def doc_state(rec: dict) -> str:
    """Coarse document-coverage state for a parent record."""
    buckets = []
    for k in ("initialReqDocs", "extensionReqDocs", "changeReqDocs", "newReqDocs", "extReqDocs"):
        v = rec.get(k)
        if isinstance(v, list) and v:
            buckets.append(k)
    procs = rec.get("procedures") or {}
    proc_docs = [
        p for p, pv in procs.items()
        if isinstance(pv, dict) and (pv.get("requiredDocs") or pv.get("variants"))
    ]
    if proc_docs:
        return f"procedure_docs({len(proc_docs)})+legacy({len(buckets)})"
    if buckets:
        return f"legacy_only({len(buckets)})"
    return "none"


def proc_summary(rec: dict) -> OrderedDict:
    procs = rec.get("procedures") or {}
    out = OrderedDict()
    for name, pv in procs.items():
        if not isinstance(pv, dict):
            out[name] = "malformed"
            continue
        avail = pv.get("available")
        refs = pv.get("manualRefs") or []
        out[name] = f"available={avail}, manualRefs={len(refs)}"
    return out


def risk_level(row: dict) -> str:
    if row["status"] in ("legacy", "abolished", "deprecated"):
        return "low(legacy-labelled)" if row.get("statusNote") else "medium(legacy-unlabelled)"
    if row["manualRefsCount"] == 0 and row["visaManualHits"] == 0 and row["stayManualHits"] == 0:
        return "high(no-grounding)"
    if row["needsManualReview"]:
        return "medium(needs-manual-review)"
    if row["manualRefsCount"] == 0:
        return "medium(no-manual-refs)"
    return "low"


def main() -> int:
    visa_data = json.loads(VISA_DATA.read_text(encoding="utf-8"))
    backend_data = json.loads(BACKEND_VISAS.read_text(encoding="utf-8"))
    authoring = {
        p.stem: json.loads(p.read_text(encoding="utf-8"))
        for p in sorted(AUTHORING_DIR.glob("*.json"))
    }
    manual_texts = {k: p.read_text(encoding="utf-8") if p.exists() else "" for k, p in MANUALS.items()}

    vd_map = {r["code"]: r for r in visa_data}
    be_map = {r["code"]: r for r in backend_data}

    consistency = {
        "authoring_only": sorted(set(authoring) - set(vd_map)),
        "visa_data_only": sorted(set(vd_map) - set(authoring)),
        "backend_mirror_only": sorted(set(be_map) - set(vd_map)),
        "visa_data_vs_backend_equal": vd_map == be_map,
    }

    rows = []
    for code in sorted(vd_map):
        rec = vd_map[code]
        subrecs = rec.get("subcodes") if isinstance(rec.get("subcodes"), list) else rec.get("subCodes") or []
        parent_refs = rec.get("manualRefs") or []
        proc_refs = sum(
            len(pv.get("manualRefs") or [])
            for pv in (rec.get("procedures") or {}).values()
            if isinstance(pv, dict)
        )
        name_ko = rec.get("name", "")
        row = {
            "parent": code,
            "subcode": None,
            "nameKo": name_ko,
            "category": rec.get("cat"),
            "status": rec.get("status", "active"),
            "statusNote": bool(rec.get("statusNote")),
            "needsManualReview": bool(rec.get("needsManualReview")),
            "manualRefsCount": len(parent_refs) + proc_refs,
            "visaManualHits": manual_hits(manual_texts["visa_2026_06_17"], code, name_ko),
            "stayManualHits": manual_hits(manual_texts["stay_2026_06_23"], code, name_ko),
            "dongpoManualHits": manual_hits(manual_texts["dongpo_2026_02"], code, name_ko),
            "searchAliases": len(rec.get("searchAliases") or rec.get("aliases") or []),
            "procedures": proc_summary(rec),
            "docCoverage": doc_state(rec),
            "sourceManualStatus": (rec.get("sourceManualStatus") or {}).get("state")
            if isinstance(rec.get("sourceManualStatus"), dict) else rec.get("sourceManualStatus"),
            "subcodeCount": len(subrecs),
            "inAuthoring": code in authoring,
        }
        row["risk"] = risk_level(row)
        rows.append(row)

        for s in subrecs:
            if not isinstance(s, dict):
                continue
            scode = s.get("code", "?")
            srow = {
                "parent": code,
                "subcode": scode,
                "nameKo": s.get("nameKo") or s.get("name", ""),
                "category": rec.get("cat"),
                "status": s.get("status", "active"),
                "statusNote": bool(s.get("statusNote")),
                "needsManualReview": bool(s.get("needsManualReview")),
                "manualRefsCount": len(s.get("manualRefs") or []),
                "visaManualHits": manual_hits(manual_texts["visa_2026_06_17"], scode, s.get("name", "")),
                "stayManualHits": manual_hits(manual_texts["stay_2026_06_23"], scode, s.get("name", "")),
                "dongpoManualHits": manual_hits(manual_texts["dongpo_2026_02"], scode, s.get("name", "")),
                "searchAliases": len(s.get("searchAliases") or []),
                "procedures": {},
                "docCoverage": "subcode_addReqDocs" if s.get("addReqDocs") else "none",
                "sourceManualStatus": None,
                "subcodeCount": 0,
                "inAuthoring": code in authoring,
            }
            srow["risk"] = risk_level(srow)
            rows.append(srow)

    parents = [r for r in rows if r["subcode"] is None]
    subs = [r for r in rows if r["subcode"] is not None]
    status_hist: dict = {}
    for r in rows:
        status_hist[r["status"]] = status_hist.get(r["status"], 0) + 1
    risk_hist: dict = {}
    for r in rows:
        risk_hist[r["risk"]] = risk_hist.get(r["risk"], 0) + 1

    summary = {
        "generated_by": "scripts/build_status_universe_audit_2026_07.py",
        "parents": len(parents),
        "subcodes": len(subs),
        "total_records": len(rows),
        "status_histogram": status_hist,
        "risk_histogram": risk_hist,
        "consistency": consistency,
        "manual_sources": {k: str(p.relative_to(REPO)) for k, p in MANUALS.items()},
    }

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "status_universe_audit.json").write_text(
        json.dumps({"summary": summary, "rows": rows}, ensure_ascii=False, indent=1) + "\n",
        encoding="utf-8",
    )

    md = ["# Status universe audit — 2026-07 post-submission pass", ""]
    md.append(f"- parents: **{summary['parents']}**, subcodes: **{summary['subcodes']}**, total: **{summary['total_records']}**")
    md.append(f"- status histogram: `{json.dumps(status_hist, ensure_ascii=False)}`")
    md.append(f"- risk histogram: `{json.dumps(risk_hist, ensure_ascii=False)}`")
    md.append(f"- store consistency: `{json.dumps(consistency, ensure_ascii=False)}`")
    md.append("")
    md.append("| parent | subcode | 한글명 | status | refs | 사증hits | 체류hits | 동포hits | aliases | risk |")
    md.append("|---|---|---|---|---|---|---|---|---|---|")
    for r in rows:
        md.append(
            f"| {r['parent']} | {r['subcode'] or ''} | {r['nameKo'][:24]} | {r['status']} "
            f"| {r['manualRefsCount']} | {r['visaManualHits']} | {r['stayManualHits']} "
            f"| {r['dongpoManualHits']} | {r['searchAliases']} | {r['risk']} |"
        )
    (OUT_DIR / "status_universe_audit.md").write_text("\n".join(md) + "\n", encoding="utf-8")

    print(json.dumps(summary, ensure_ascii=False, indent=1))
    high = [f"{r['parent']}/{r['subcode'] or '-'}" for r in rows if r["risk"].startswith("high")]
    print("HIGH RISK:", high if high else "none")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
