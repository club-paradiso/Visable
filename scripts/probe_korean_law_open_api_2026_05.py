#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

OUT_JSON = Path("docs/integrations/law_open_api_runtime_probe_2026_05.json")
OUT_MD = Path("docs/integrations/LAW_OPEN_API_RUNTIME_PROBE_2026_05.md")

LAW_NAMES = [
    "출입국관리법",
    "출입국관리법 시행령",
    "출입국관리법 시행규칙",
    "국적법",
    "국적법 시행령",
    "국적법 시행규칙",
    "난민법",
    "난민법 시행령",
    "난민법 시행규칙",
    "재외동포의 출입국과 법적 지위에 관한 법률",
    "재외동포의 출입국과 법적 지위에 관한 법률 시행령",
    "재외동포의 출입국과 법적 지위에 관한 법률 시행규칙",
    "재한외국인 처우 기본법",
    "재한외국인 처우 기본법 시행령",
]

ENV_CANDIDATES = [
    "LAW_API_OC",
    "LAW_API_KEY",
    "KOREAN_LAW_API_OC",
    "OPEN_LAW_API_OC",
]

SEARCH_ENDPOINT = "https://www.law.go.kr/DRF/lawSearch.do"
SERVICE_ENDPOINT = "https://www.law.go.kr/DRF/lawService.do"

def get_oc() -> str | None:
    for key in ENV_CANDIDATES:
        value = os.environ.get(key)
        if value and value.strip():
            return value.strip()
    return None

def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()

def fetch_url(url: str, timeout: int = 12) -> dict[str, Any]:
    started = time.time()
    try:
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Paradiso-law-open-api-probe/2026.05",
                "Accept": "application/json, application/xml, text/plain, */*",
            },
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
            elapsed_ms = round((time.time() - started) * 1000)
            text = raw.decode("utf-8", errors="replace")
            return {
                "ok": True,
                "status": getattr(resp, "status", None),
                "elapsed_ms": elapsed_ms,
                "content_type": resp.headers.get("Content-Type"),
                "bytes": len(raw),
                "sha256": sha256_text(text),
                "sample": text[:800],
            }
    except Exception as exc:
        elapsed_ms = round((time.time() - started) * 1000)
        return {
            "ok": False,
            "elapsed_ms": elapsed_ms,
            "error_type": type(exc).__name__,
            "error": str(exc),
        }

def parse_json_maybe(sample: str) -> Any | None:
    try:
        return json.loads(sample)
    except Exception:
        return None

def extract_law_candidates(response_sample: str) -> list[dict[str, Any]]:
    data = parse_json_maybe(response_sample)
    if data is None:
        return []

    candidates = []

    def walk(obj: Any):
        if isinstance(obj, dict):
            law_name = (
                obj.get("법령명한글")
                or obj.get("법령명")
                or obj.get("법령명_한글")
                or obj.get("lawName")
            )
            mst = obj.get("법령일련번호") or obj.get("MST") or obj.get("mst")
            law_id = obj.get("법령ID") or obj.get("lawId")
            if law_name or mst or law_id:
                candidates.append({
                    "law_name": law_name,
                    "mst": mst,
                    "law_id": law_id,
                    "raw_keys": sorted(obj.keys())[:20],
                })
            for v in obj.values():
                walk(v)
        elif isinstance(obj, list):
            for x in obj:
                walk(x)

    walk(data)
    return candidates[:10]

def build_search_url(oc: str, law_name: str) -> str:
    params = {
        "OC": oc,
        "target": "law",
        "type": "JSON",
        "query": law_name,
        "display": "20",
    }
    return SEARCH_ENDPOINT + "?" + urllib.parse.urlencode(params)

def build_service_url(oc: str, mst: str | None = None, law_id: str | None = None) -> str | None:
    params = {
        "OC": oc,
        "target": "law",
        "type": "JSON",
    }
    if mst:
        params["MST"] = str(mst)
    elif law_id:
        params["ID"] = str(law_id)
    else:
        return None
    return SERVICE_ENDPOINT + "?" + urllib.parse.urlencode(params)

def main() -> None:
    oc = get_oc()

    result: dict[str, Any] = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "purpose": "runtime probe for Korean Law Open API before any DB official-verification mutation",
        "configured": bool(oc),
        "env_candidates_checked": ENV_CANDIDATES,
        "credential_value_saved": False,
        "official_source": {
            "name": "국가법령정보 공동활용 LAW OPEN DATA",
            "guide_url": "https://open.law.go.kr/LSO/openApi/guideList.do",
            "search_endpoint_template": SEARCH_ENDPOINT,
            "service_endpoint_template": SERVICE_ENDPOINT,
        },
        "guardrails": {
            "mutated_visa_data": False,
            "set_verified_true": False,
            "created_legal_content": False,
            "stored_secret": False,
        },
        "laws": [],
    }

    if not oc:
        result["status"] = "UNCONFIGURED"
        result["message"] = "Set LAW_API_OC or LAW_API_KEY in Codespaces secrets/env before live probing."
    else:
        result["status"] = "PROBED"
        for law_name in LAW_NAMES:
            search_url = build_search_url(oc, law_name)
            search_resp = fetch_url(search_url)
            law_entry: dict[str, Any] = {
                "law_name_requested": law_name,
                "search": {
                    k: v for k, v in search_resp.items()
                    if k not in {"sample"}
                },
                "search_sample_hash": search_resp.get("sha256"),
                "candidates": [],
                "service": None,
                "verification_state": "SOURCE_UNAVAILABLE",
            }

            if search_resp.get("ok"):
                candidates = extract_law_candidates(search_resp.get("sample", ""))
                law_entry["candidates"] = candidates

                exact = None
                for c in candidates:
                    cname = str(c.get("law_name") or "")
                    if cname == law_name:
                        exact = c
                        break
                if not exact and candidates:
                    exact = candidates[0]

                if exact:
                    service_url = build_service_url(oc, exact.get("mst"), exact.get("law_id"))
                    if service_url:
                        service_resp = fetch_url(service_url)
                        law_entry["service"] = {
                            k: v for k, v in service_resp.items()
                            if k not in {"sample"}
                        }
                        if service_resp.get("ok"):
                            sample = service_resp.get("sample", "")
                            contains_name = law_name.replace(" ", "") in sample.replace(" ", "")
                            law_entry["service_sample_hash"] = service_resp.get("sha256")
                            law_entry["service_contains_requested_law_name"] = contains_name
                            law_entry["verification_state"] = (
                                "LIVE_SOURCE_MATCHED" if contains_name else "LIVE_SOURCE_RETURNED_NEEDS_MANUAL_REVIEW"
                            )
                        else:
                            law_entry["verification_state"] = "SERVICE_FETCH_FAILED"
                    else:
                        law_entry["verification_state"] = "SEARCH_MATCHED_NO_SERVICE_ID"
                else:
                    law_entry["verification_state"] = "SEARCH_RETURNED_NO_CANDIDATE"

            result["laws"].append(law_entry)

    OUT_JSON.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    matched = [
        x for x in result["laws"]
        if x.get("verification_state") == "LIVE_SOURCE_MATCHED"
    ]

    lines = []
    lines.append("# Law Open API Runtime Probe - 2026.5")
    lines.append("")
    lines.append("## Scope")
    lines.append("")
    lines.append("This probe checks whether Paradiso can access official Korean law text through the National Law Information Open API before any DB field is marked as officially verified.")
    lines.append("")
    lines.append("## Result")
    lines.append("")
    lines.append(f"- Configured: `{result['configured']}`")
    lines.append(f"- Status: `{result['status']}`")
    lines.append(f"- Matched live law sources: `{len(matched)}`")
    lines.append("")
    if not result["configured"]:
        lines.append("No live call was made because no API credential was found.")
        lines.append("")
        lines.append("Set one of these environment variables before live probing:")
        for key in ENV_CANDIDATES:
            lines.append(f"- `{key}`")
        lines.append("")
    lines.append("## Laws checked")
    lines.append("")
    for entry in result["laws"]:
        lines.append(f"- `{entry['law_name_requested']}`: `{entry['verification_state']}`")
    lines.append("")
    lines.append("## Guardrails")
    lines.append("")
    lines.append("- No `visa_data.json` mutation.")
    lines.append("- No `verified=true` promotion.")
    lines.append("- No legal-content generation.")
    lines.append("- No credential stored in repo.")
    lines.append("")
    lines.append("## Next step")
    lines.append("")
    lines.append("Only after this probe returns stable `LIVE_SOURCE_MATCHED` results should a separate verifier PR add field-level `lawVerification` metadata to DB records.")
    lines.append("")

    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(json.dumps({
        "configured": result["configured"],
        "status": result["status"],
        "matched_count": len(matched),
        "audit_json": str(OUT_JSON),
        "audit_md": str(OUT_MD),
    }, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
