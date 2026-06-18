#!/usr/bin/env python3
"""Extract human-editable authoring files from the live visa_data.json.

Phase 3 / Script 1. Splits the generated compatibility file
(visa_data.json, repo root) into:

  backend/data/visa_authoring/statuses/<CODE>.json   (one per status)
  backend/data/visa_authoring/common/*.json          (shared fees/warnings/labels/doc catalog)
  backend/data/visa_authoring/audit/*.json           (relocated audit/migration fields + summary cleanup)

Guarantees:
  * Lossless: every status file records the exact original top-level key order
    and the source of each key, so `build` reproduces visa_data.json
    byte-for-byte. Extraction self-checks this before writing anything.
  * Idempotent-safe: refuses to overwrite existing status files unless --force.
  * Summary cleanup (Phase 3.5): low-value / boilerplate / OCR-like summaries
    are removed from the human authoring view but preserved verbatim in the
    generated compatibility layer; classifications are logged to
    audit/summary_cleanup_audit.json.

Usage:
  python3 scripts/visa/extract_authoring_from_visa_data.py [--force]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _visa_pipeline_common as C  # noqa: E402


def _derive_review_status(sms: dict) -> str:
    if not isinstance(sms, dict):
        return "needs_review"
    if sms.get("verified") is True and sms.get("needsManualReview") is False:
        return "verified"
    if sms.get("needsManualReview") is True:
        return "needs_review"
    return "partial"


def _shared_fee(records: list) -> dict:
    fees = [r["feeInfo"] for r in records if "feeInfo" in r]
    if not fees:
        return {}
    first = C.json.dumps(fees[0], ensure_ascii=False, sort_keys=True)
    if all(C.json.dumps(f, ensure_ascii=False, sort_keys=True) == first for f in fees):
        return fees[0]
    return {}


def _shared_warnings(records: list):
    warns = [r["commonWarnings"] for r in records if "commonWarnings" in r]
    if not warns:
        return None
    first = C.json.dumps(warns[0], ensure_ascii=False, sort_keys=True)
    if all(C.json.dumps(w, ensure_ascii=False, sort_keys=True) == first for w in warns):
        return warns[0]
    return None


def extract(force: bool) -> int:
    records = C.load_json(C.VISA_DATA)
    if not isinstance(records, list):
        print("ERROR: visa_data.json is not a list", file=sys.stderr)
        return 1

    shared_fee = _shared_fee(records)
    shared_warn = _shared_warnings(records)
    shared_fee_json = C.json.dumps(shared_fee, ensure_ascii=False, sort_keys=True) if shared_fee else None
    shared_warn_json = C.json.dumps(shared_warn, ensure_ascii=False, sort_keys=True) if shared_warn is not None else None

    audit_by_code = {b: {} for b in set(C.AUDIT_RELOCATED.values())}
    sms_by_code = {}
    summary_audit = []
    authoring_files = {}
    fee_codes, warn_codes = [], []

    for idx, rec in enumerate(records):
        code = rec.get("code")
        authoring = {}
        compat = {}
        removed_summaries = {}
        key_source = {}
        key_order = list(rec.keys())

        # --- procedures (with summary cleanup) ---
        proc_order, proc_key_order = [], {}
        cleaned_procs = {}
        if "procedures" in rec and isinstance(rec["procedures"], dict):
            for pname, pval in rec["procedures"].items():
                proc_order.append(pname)
                proc_key_order[pname] = list(pval.keys()) if isinstance(pval, dict) else []
                cp = {}
                has_refs = bool(isinstance(pval, dict) and pval.get("manualRefs"))
                for pk, pv in (pval.items() if isinstance(pval, dict) else []):
                    if pk == "summary":
                        cls = C.classify_summary(pv, has_refs)
                        path = f"procedures.{pname}.summary"
                        summary_audit.append({
                            "code": code, "path": path,
                            "originalText": pv,
                            "classification": cls["classification"],
                            "summaryQuality": cls["summaryQuality"],
                            "removedFromAuthoring": not cls["keep"],
                            "preservedInCompat": not cls["keep"],
                            "summaryCleanupStatus": cls["summaryCleanupStatus"],
                            "manualRefs": pval.get("manualRefs") if isinstance(pval, dict) else None,
                            "risk": cls["risk"],
                        })
                        if cls["keep"]:
                            cp["summary"] = pv
                            cp["summaryQuality"] = cls["summaryQuality"]
                        else:
                            removed_summaries[path] = pv
                            cp["summaryQuality"] = cls["summaryQuality"]
                            cp["summaryHiddenInUi"] = True
                            cp["summaryCleanupStatus"] = cls["summaryCleanupStatus"]
                    else:
                        cp[pk] = pv
                cleaned_procs[pname] = cp

        # --- walk original keys, assign exactly one source each ---
        for k in key_order:
            v = rec[k]
            if k in C.IDENTITY_FIELDS:
                authoring[k] = v
                key_source[k] = "identity"
            elif k == "manualRefs":
                authoring["manualRefs"] = v
                key_source[k] = "manualRefs"
            elif k == "sourceManualStatus":
                authoring["sourceManualStatus"] = v
                key_source[k] = "sourceManualStatus"
            elif k == "subCodes":
                authoring["subcodes"] = v          # normalize camelCase -> human subcodes
                key_source[k] = "subcodes"
            elif k == "procedures":
                authoring["procedures"] = cleaned_procs
                key_source[k] = "procedures"
            elif k == "feeInfo" and shared_fee_json is not None and \
                    C.json.dumps(v, ensure_ascii=False, sort_keys=True) == shared_fee_json:
                key_source[k] = "feeRef"
                fee_codes.append(code)
            elif k == "commonWarnings" and shared_warn_json is not None and \
                    C.json.dumps(v, ensure_ascii=False, sort_keys=True) == shared_warn_json:
                key_source[k] = "warnRef"
                warn_codes.append(code)
            elif k in C.AUDIT_RELOCATED:
                basename = C.AUDIT_RELOCATED[k]
                audit_by_code[basename][code] = v
                key_source[k] = f"audit:{basename}"
            else:
                compat[k] = v
                key_source[k] = "compat"

        if isinstance(rec.get("sourceManualStatus"), dict):
            sms_by_code[code] = rec["sourceManualStatus"]

        generated = {"compat": compat}
        if removed_summaries:
            generated["removedSummaries"] = removed_summaries

        authoring["reviewStatus"] = _derive_review_status(rec.get("sourceManualStatus", {}))
        authoring["editorNotes"] = ""
        authoring["_generated"] = generated
        authoring["_authoring"] = {
            "schemaVersion": C.SCHEMA_VERSION,
            "recordIndex": idx,
            "keyOrder": key_order,
            "keySource": key_source,
            "procOrder": proc_order,
            "procKeyOrder": proc_key_order,
            "note": "GENERATED by extract_authoring_from_visa_data.py. "
                    "Edit the human-editable top-level fields; do not hand-edit _generated/_authoring.",
        }
        authoring_files[code] = authoring

    # ---- write common + audit context, then self-check, then write statuses ----
    fees_doc = {
        "feeInfo": shared_fee,
        "_meta": {
            "note": "Shared paradisoDefault fee block. Statuses whose feeInfo equals "
                    "this are emitted by reference (feeRef) during build.",
            "usedByCodes": fee_codes,
        },
    }
    warnings_doc = {
        "commonWarnings": shared_warn if shared_warn is not None else [],
        "_meta": {
            "note": "Shared commonWarnings block, referenced by build where a status "
                    "matched it exactly.",
            "usedByCodes": warn_codes,
            "needsMigrationReview": shared_warn is None,
        },
    }

    ctx = C.BuildContext(fees=fees_doc, warnings=warnings_doc, audit=audit_by_code)
    rebuilt = [C.reconstruct_record(authoring_files[r["code"]], ctx) for r in records]
    if C.dump_visa_json(rebuilt) != C.dump_visa_json(records):
        print("FATAL: self-check failed — reconstruction is not byte-identical. "
              "No files written.", file=sys.stderr)
        for a, b in zip(rebuilt, records):
            if C.dump_visa_json(a) != C.dump_visa_json(b):
                print(f"  first mismatch at code {b.get('code')}", file=sys.stderr)
                break
        return 2
    print(f"self-check OK: {len(rebuilt)} records reconstruct byte-identically.")

    # refuse to clobber unless --force
    existing = list(C.STATUSES_DIR.glob("*.json"))
    if existing and not force:
        print(f"ERROR: {len(existing)} authoring status files already exist in "
              f"{C.STATUSES_DIR.relative_to(C.REPO_ROOT)}. Re-run with --force to overwrite.",
              file=sys.stderr)
        return 1

    C.STATUSES_DIR.mkdir(parents=True, exist_ok=True)
    C.COMMON_DIR.mkdir(parents=True, exist_ok=True)
    C.AUDIT_DIR.mkdir(parents=True, exist_ok=True)

    for code, authoring in authoring_files.items():
        (C.STATUSES_DIR / f"{code}.json").write_text(C.dump_authoring_json(authoring), encoding="utf-8")

    (C.COMMON_DIR / "fees_2026_05.json").write_text(C.dump_authoring_json(fees_doc), encoding="utf-8")
    (C.COMMON_DIR / "common_warnings_2026_05.json").write_text(C.dump_authoring_json(warnings_doc), encoding="utf-8")
    (C.COMMON_DIR / "procedure_labels.json").write_text(C.dump_authoring_json(_procedure_labels()), encoding="utf-8")
    (C.COMMON_DIR / "doc_catalog.json").write_text(C.dump_authoring_json(_doc_catalog(authoring_files)), encoding="utf-8")

    for basename, by_code in audit_by_code.items():
        doc = {"_meta": {"note": f"Relocated '{_orig_key(basename)}' fields, re-injected verbatim "
                                 "by build. Generated; do not hand-edit.",
                         "needsMigrationReview": False},
               "byCode": by_code}
        (C.AUDIT_DIR / f"{basename}.json").write_text(C.dump_authoring_json(doc), encoding="utf-8")

    (C.AUDIT_DIR / "source_manual_status.json").write_text(C.dump_authoring_json({
        "_meta": {"note": "Consolidated read-only view of each status's sourceManualStatus "
                          "(the editable copy lives in the status file). Not a build input."},
        "byCode": sms_by_code,
    }), encoding="utf-8")

    counts = _summary_counts(summary_audit)
    (C.AUDIT_DIR / "summary_cleanup_audit.json").write_text(C.dump_authoring_json({
        "_meta": {
            "note": "Per-summary classification (Phase 3.5). 'removedFromAuthoring' summaries "
                    "are preserved verbatim in the generated compatibility output.",
            "counts": counts,
        },
        "entries": summary_audit,
    }), encoding="utf-8")

    print(f"Wrote {len(authoring_files)} status files + common/ + audit/ context.")
    print("Summary cleanup:", counts)
    return 0


def _orig_key(basename: str) -> str:
    for k, v in C.AUDIT_RELOCATED.items():
        if v == basename:
            return k
    return basename


def _summary_counts(entries: list) -> dict:
    out = {"total": len(entries), "kept": 0, "removedFromAuthoring": 0,
           "compatOnly": 0, "movedToAudit": 0, "needsHumanReview": 0, "byQuality": {}}
    for e in entries:
        out["byQuality"][e["summaryQuality"]] = out["byQuality"].get(e["summaryQuality"], 0) + 1
        if not e["removedFromAuthoring"]:
            out["kept"] += 1
        else:
            out["removedFromAuthoring"] += 1
            if e["summaryCleanupStatus"] == "compat_only":
                out["compatOnly"] += 1
            if e["classification"] == "move_to_source_excerpt_or_audit":
                out["movedToAudit"] += 1
            if e["classification"] == "needs_human_review":
                out["needsHumanReview"] += 1
    return out


def _procedure_labels() -> dict:
    # UI labels only (not legal content). Keys are the procedure names seen in
    # visa_data.json; values are display labels for the procedure system.
    return {
        "_meta": {"note": "UI display labels for procedure keys. Reference data; "
                          "not legal content. A procedure label is NOT a summary."},
        "labels": {
            "visaIssuance": "사증발급",
            "statusGrant": "체류자격 부여",
            "statusChange": "체류자격 변경",
            "extension": "체류기간 연장",
            "registration": "외국인등록",
            "reentry": "재입국허가",
            "activitiesOutsideStatus": "체류자격외 활동",
            "workplaceChange": "근무처 변경·추가",
            "partTimeWork": "시간제취업",
            "schoolChange": "학교(소속) 변경",
        },
    }


def _doc_catalog(authoring_files: dict) -> dict:
    # Thin index over doc_master.json (the active dictionary). We do NOT
    # duplicate doc content here; doc_master.json stays the source of truth.
    doc_ids = []
    try:
        dm = C.load_json(C.DOC_MASTER)
        doc_ids = sorted({d.get("id") for d in dm if isinstance(d, dict) and d.get("id")})
    except Exception:
        pass
    return {
        "_meta": {"note": "Index of document IDs available in doc_master.json (the active "
                          "dictionary). Source of truth is doc_master.json; this file is a "
                          "convenience index for authoring/validation.",
                  "source": "doc_master.json"},
        "docIds": doc_ids,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--force", action="store_true",
                    help="overwrite existing authoring status files")
    args = ap.parse_args()
    return extract(force=args.force)


if __name__ == "__main__":
    raise SystemExit(main())
