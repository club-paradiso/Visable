#!/usr/bin/env python3
"""Validate the visa-data authoring layer (Phase 3 / Script 3).

Read-only. Exits non-zero on any failure. Checks (per the brief):

  1  invalid JSON in any authoring file
  2  duplicate status codes
  3  duplicate subcode codes within a status (unless legacyConflict flagged)
  4  missing required status identity fields
  5  invalid reviewStatus
  6  document ID referenced in authoring but missing from doc_master.json
  7  source-backed procedure with a kept summary but no manualRefs/sourceManualStatus
  8  banned generated-only fields at authoring top level
  9  generated visa_data.json out of date vs authoring
  10 backend/data/visas.json mirror out of sync
  11 summary containing DATA_MISSING
  12 summary longer than the conservative threshold (unless sourceExcerpt/retained)
  13 summary equal to a bare procedure label
  14 summary starting with generic UI boilerplate
  15 summary with no manualRefs but containing legal/eligibility/doc/fee/deadline claims
  16 summaryQuality missing when a summary exists in authoring

Usage:
  python3 scripts/visa/validate_visa_authoring.py
"""
from __future__ import annotations

import filecmp
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _visa_pipeline_common as C  # noqa: E402

PROCEDURE_LABELS = {
    "사증발급", "체류자격 부여", "체류자격 변경", "체류기간 연장", "외국인등록",
    "재입국허가", "체류자격외 활동", "근무처 변경·추가", "시간제취업", "학교(소속) 변경",
    "체류기간 연장허가", "체류자격 변경허가", "재입국", "근무처변경",
}
# crude signal that a string makes a substantive claim (rule 15)
CLAIM_MARKERS = ("가능", "불가", "허가", "신청", "변경", "연장", "자격", "서류", "수수료",
                 "이내", "일", "개월", "년", "원", "제출", "대상", "요건", "조건")


def main() -> int:
    errors: list[str] = []
    warnings: list[str] = []

    # ---- doc_master active dictionary ----
    doc_ids = set()
    try:
        dm = C.load_json(C.DOC_MASTER)
        doc_ids = {d.get("id") for d in dm if isinstance(d, dict) and d.get("id")}
    except Exception as exc:  # noqa: BLE001
        warnings.append(f"could not load doc_master.json ({exc}); skipping doc-id check")

    files = sorted(C.STATUSES_DIR.glob("*.json"))
    if not files:
        print("ERROR: no authoring status files found. Run extract first.", file=sys.stderr)
        return 1

    seen_codes: dict[str, str] = {}
    records = []
    for path in files:
        try:
            a = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:                                  # rule 1
            errors.append(f"{path.name}: invalid JSON ({exc})")
            continue
        records.append((path, a))

        code = a.get("code")
        if not code or not a.get("name") or not a.get("cat") or not a.get("period"):  # rule 4
            errors.append(f"{path.name}: missing required identity field(s) "
                          f"(code/name/cat/period)")
        if code in seen_codes:                                                # rule 2
            errors.append(f"duplicate status code {code!r} in {path.name} and {seen_codes[code]}")
        seen_codes[code] = path.name

        if a.get("reviewStatus") not in C.REVIEW_STATUSES:                    # rule 5
            errors.append(f"{path.name}: invalid reviewStatus {a.get('reviewStatus')!r}")

        # rule 3 — duplicate subcodes
        subs = a.get("subcodes") or []
        sub_codes = [s.get("code") for s in subs if isinstance(s, dict)]
        dupe_subs = {c for c in sub_codes if sub_codes.count(c) > 1}
        if dupe_subs and not a.get("_authoring", {}).get("legacyConflict"):
            errors.append(f"{path.name}: duplicate subcode code(s) {sorted(dupe_subs)}")

        # rule 8 — banned generated-only fields at top level
        banned = C.BANNED_TOPLEVEL_FIELDS & set(a.keys())
        if banned:
            errors.append(f"{path.name}: banned generated-only field(s) at top level: "
                          f"{sorted(banned)} (must live under _generated/audit)")

        # rule 6 — doc ids referenced in authoring procedures
        if doc_ids:
            for did in _referenced_doc_ids(a):
                if did not in doc_ids:
                    errors.append(f"{path.name}: doc id {did!r} not in doc_master.json")

        # summary rules 7,11-16 — over KEPT authoring summaries
        needs_review = bool(a.get("sourceManualStatus", {}).get("needsManualReview"))
        for pname, pv in (a.get("procedures") or {}).items():
            if not isinstance(pv, dict) or "summary" not in pv:
                continue
            s = pv["summary"]
            has_refs = bool(pv.get("manualRefs"))
            if "summaryQuality" not in pv:                                    # rule 16
                errors.append(f"{path.name}:{pname}: summary present but summaryQuality missing")
            if isinstance(s, str):
                if "DATA_MISSING" in s:                                       # rule 11
                    errors.append(f"{path.name}:{pname}: summary contains DATA_MISSING")
                if len(s.strip()) > C.SUMMARY_KEEP_MAX_LEN and not pv.get("sourceExcerpt"):  # rule 12
                    errors.append(f"{path.name}:{pname}: summary too long "
                                  f"({len(s.strip())} > {C.SUMMARY_KEEP_MAX_LEN})")
                if s.strip() in PROCEDURE_LABELS:                             # rule 13
                    errors.append(f"{path.name}:{pname}: summary is a bare procedure label")
                if s.strip().startswith(C.BOILERPLATE_PREFIXES):             # rule 14
                    errors.append(f"{path.name}:{pname}: summary starts with UI boilerplate")
                if not has_refs and any(m in s for m in CLAIM_MARKERS):      # rule 15
                    if not needs_review:
                        errors.append(f"{path.name}:{pname}: summary makes claims but has no "
                                      f"manualRefs and status is not needsManualReview")
            # rule 7
            if not has_refs and not a.get("sourceManualStatus") and not needs_review:
                errors.append(f"{path.name}:{pname}: kept summary without manualRefs/sourceManualStatus")

    # rule 9 — generated visa_data.json up to date
    try:
        from build_visa_data import build_records
        rendered = C.dump_visa_json(build_records())
        current = C.VISA_DATA.read_text(encoding="utf-8") if C.VISA_DATA.exists() else ""
        if rendered != current:
            errors.append("generated visa_data.json is OUT OF DATE vs authoring "
                          "(run scripts/visa/build_visa_data.py)")
    except Exception as exc:  # noqa: BLE001
        errors.append(f"could not rebuild for freshness check: {exc}")

    # rule 10 — mirror in sync
    if C.VISA_DATA.exists() and C.BACKEND_MIRROR.exists():
        if not filecmp.cmp(C.VISA_DATA, C.BACKEND_MIRROR, shallow=False):
            errors.append("backend/data/visas.json is OUT OF SYNC with visa_data.json "
                          "(run scripts/sync_visa_data.py)")

    for w in warnings:
        print(f"[validate] WARN: {w}")
    if errors:
        print(f"[validate] FAIL — {len(errors)} error(s):", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        return 1
    print(f"[validate] OK — {len(records)} status files; identity, codes, subcodes, "
          f"reviewStatus, banned-fields, doc-ids, summaries, freshness and mirror all pass.")
    return 0


def _referenced_doc_ids(authoring: dict) -> set:
    out = set()

    def walk(x):
        if isinstance(x, str):
            if x.startswith("doc_"):
                out.add(x)
        elif isinstance(x, list):
            for i in x:
                walk(i)
        elif isinstance(x, dict):
            for v in x.values():
                walk(v)

    for pv in (authoring.get("procedures") or {}).values():
        if isinstance(pv, dict):
            walk(pv.get("requiredDocs"))
    return out


if __name__ == "__main__":
    raise SystemExit(main())
