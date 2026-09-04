#!/usr/bin/env python3
"""Measure Visable's real enforcement extract -> analyze path with synthetic cases.

No user data is sent. Reports contain only case ids, timings, coarse runtime
configuration and prediction status/model metadata. Synthetic narratives are
never written to the report or logs.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import statistics
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

DEFAULT_BASE_URL = "https://web-production-14f9a.up.railway.app"
DEFAULT_TIMEOUT_SECONDS = 90.0

CASES = [
    {"id": "d2_part_time_first_offense", "text": "D-2 유학생인데 시간제취업 허가 없이 음식점에서 18일 아르바이트했습니다. 이번이 처음입니다.", "assessmentDate": "2026-09-04"},
    {"id": "c3_unauthorized_work", "text": "C-3 체류자격인데 취업 허가 없이 음식점에서 12일 일했습니다. 처음입니다.", "assessmentDate": "2026-09-04"},
    {"id": "e7_outside_designated_workplace", "text": "E-7인데 지정된 근무처가 아닌 다른 사업장에서 허가 없이 20일 근무했습니다. 이번이 처음입니다.", "assessmentDate": "2026-09-04"},
    {"id": "e7_workplace_change", "text": "E-7-4인데 근무처 변경 허가를 받지 않고 다른 회사로 옮겨 2개월 3일 일했습니다. 이전 위반은 없습니다.", "assessmentDate": "2026-09-04"},
    {"id": "overstay_voluntary", "text": "D-10 체류기간이 지난 뒤 6일 초과체류했고 이번이 처음입니다. 스스로 출입국관서에 자진 방문했습니다.", "assessmentDate": "2026-09-04"},
    {"id": "d2_prior_and_detected", "text": "D-2인데 시간제취업 허가 없이 45일 일했고 이전에도 같은 위반으로 1회 처분받았습니다. 이번에는 단속으로 적발됐습니다.", "assessmentDate": "2026-09-04"},
]


def _percentile(values: list[float], q: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    return round(ordered[max(0, min(len(ordered) - 1, math.ceil(q * len(ordered)) - 1))], 1)


def _summary(values: list[float]) -> dict[str, Any]:
    if not values:
        return {"samples": 0, "meanMs": None, "p50Ms": None, "p95Ms": None, "minMs": None, "maxMs": None}
    return {
        "samples": len(values),
        "meanMs": round(statistics.fmean(values), 1),
        "p50Ms": _percentile(values, 0.50),
        "p95Ms": _percentile(values, 0.95),
        "minMs": round(min(values), 1),
        "maxMs": round(max(values), 1),
    }


def _decode(raw: bytes) -> dict[str, Any]:
    try:
        value = json.loads(raw.decode("utf-8", errors="replace"))
        return value if isinstance(value, dict) else {"_unexpectedShape": True}
    except json.JSONDecodeError:
        return {"_invalidJson": True}


def _get_json(url: str, timeout: float) -> tuple[int, dict[str, Any], float]:
    request = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": "Visable-Enforcement-Benchmark/1.1"})
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310 - operator-selected HTTPS endpoint
            return int(response.status), _decode(response.read()), (time.perf_counter() - started) * 1000
    except urllib.error.HTTPError as exc:
        return int(exc.code), _decode(exc.read()), (time.perf_counter() - started) * 1000


def _post_json(url: str, payload: dict[str, Any], timeout: float) -> tuple[int, dict[str, Any], float, dict[str, str]]:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8"),
        headers={"Content-Type": "application/json", "Accept": "application/json", "User-Agent": "Visable-Enforcement-Benchmark/1.1"},
        method="POST",
    )
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310
            return int(response.status), _decode(response.read()), (time.perf_counter() - started) * 1000, {k.lower(): v for k, v in response.headers.items()}
    except urllib.error.HTTPError as exc:
        return int(exc.code), _decode(exc.read()), (time.perf_counter() - started) * 1000, {k.lower(): v for k, v in exc.headers.items()}


def _retry_after_seconds(headers: dict[str, str], fallback: float) -> float:
    try:
        value = float(headers.get("retry-after", ""))
        if value >= 0:
            return min(value, 90.0)
    except (TypeError, ValueError):
        pass
    return fallback


def _post_with_retry(url: str, payload: dict[str, Any], timeout: float, retry_delay: float) -> tuple[int, dict[str, Any], float, int]:
    total_ms = 0.0
    retries = 0
    for attempt in range(2):
        status, data, elapsed_ms, headers = _post_json(url, payload, timeout)
        total_ms += elapsed_ms
        if status != 429 or attempt == 1:
            return status, data, total_ms, retries
        retries += 1
        time.sleep(_retry_after_seconds(headers, retry_delay))
    raise AssertionError("unreachable")


def _safe_health(base_url: str, timeout: float) -> dict[str, Any]:
    try:
        status, body, elapsed = _get_json(f"{base_url}/health", min(timeout, 30.0))
    except Exception as exc:  # noqa: BLE001
        return {"status": None, "errorType": type(exc).__name__}
    providers = body.get("providers") if isinstance(body.get("providers"), dict) else body.get("providers_configured")
    return {
        "status": status,
        "latencyMs": round(elapsed, 1),
        "provider": body.get("provider") or body.get("llm_provider"),
        "model": body.get("model") or body.get("llm_model"),
        "providers": providers if isinstance(providers, dict) else None,
        "openrouterConfigured": body.get("openrouter_configured"),
        "warnings": body.get("warnings") if isinstance(body.get("warnings"), list) else None,
        "lawGroundingMode": body.get("law_grounding_mode"),
    }


def run_once(base_url: str, case: dict[str, str], timeout: float, retry_delay: float) -> dict[str, Any]:
    extract_status, extract_body, extract_ms, extract_retries = _post_with_retry(
        f"{base_url}/api/enforcement/extract",
        {"text": case["text"], "assessmentDate": case["assessmentDate"]},
        timeout,
        retry_delay,
    )
    record: dict[str, Any] = {
        "caseId": case["id"], "extractStatus": extract_status, "extractMs": round(extract_ms, 1),
        "extractRetries": extract_retries, "analyzeStatus": None, "analyzeMs": None, "analyzeRetries": 0,
        "totalMs": None, "modelId": None, "predictionStatus": None, "legalBaselineStatus": None,
        "violationCode": None, "predictionLimitations": [], "ok": False,
    }
    if extract_status != 200 or not isinstance(extract_body.get("case"), dict):
        record["failureStage"] = "extract"
        return record

    structured_case = extract_body["case"]
    record["violationCode"] = structured_case.get("violationCode")
    analyze_status, analyze_body, analyze_ms, analyze_retries = _post_with_retry(
        f"{base_url}/api/enforcement/analyze", {"caseData": structured_case}, timeout, retry_delay,
    )
    record.update({"analyzeStatus": analyze_status, "analyzeMs": round(analyze_ms, 1), "analyzeRetries": analyze_retries, "totalMs": round(extract_ms + analyze_ms, 1)})
    if analyze_status != 200:
        record["failureStage"] = "analyze"
        return record

    prediction = analyze_body.get("prediction") if isinstance(analyze_body.get("prediction"), dict) else {}
    baseline = analyze_body.get("legalBaseline") if isinstance(analyze_body.get("legalBaseline"), dict) else {}
    limitations = prediction.get("limitations") if isinstance(prediction.get("limitations"), list) else []
    record.update({
        "modelId": prediction.get("modelId"),
        "predictionStatus": prediction.get("status"),
        "legalBaselineStatus": baseline.get("status"),
        "predictionLimitations": [str(item)[:240] for item in limitations[:4]],
        "ok": baseline.get("status") == "AVAILABLE" and prediction.get("status") in {"AVAILABLE", "LIMITED", "UNAVAILABLE"},
    })
    return record


def build_report(base_url: str, repetitions: int, delay: float, timeout: float, retry_delay: float) -> dict[str, Any]:
    runtime = _safe_health(base_url, timeout)
    print("SAFE_RUNTIME=" + json.dumps(runtime, ensure_ascii=False, sort_keys=True), flush=True)
    runs: list[dict[str, Any]] = []
    total_planned = len(CASES) * repetitions
    completed = 0
    for repetition in range(1, repetitions + 1):
        for case in CASES:
            completed += 1
            print(f"[{completed}/{total_planned}] {case['id']} repetition={repetition}", flush=True)
            try:
                record = run_once(base_url, case, timeout, retry_delay)
            except Exception as exc:  # noqa: BLE001
                record = {"caseId": case["id"], "ok": False, "failureStage": "transport", "errorType": type(exc).__name__}
            record["repetition"] = repetition
            runs.append(record)
            if completed < total_planned and delay > 0:
                time.sleep(delay)

    completed_runs = [run for run in runs if run.get("ok") is True]
    extract_values = [float(run["extractMs"]) for run in completed_runs if isinstance(run.get("extractMs"), (int, float))]
    analyze_values = [float(run["analyzeMs"]) for run in completed_runs if isinstance(run.get("analyzeMs"), (int, float))]
    total_values = [float(run["totalMs"]) for run in completed_runs if isinstance(run.get("totalMs"), (int, float))]
    models: dict[str, int] = {}
    statuses: dict[str, int] = {}
    for run in runs:
        model = str(run.get("modelId") or "NO_VALID_MODEL")
        models[model] = models.get(model, 0) + 1
        status = str(run.get("predictionStatus") or "NO_STATUS")
        statuses[status] = statuses.get(status, 0) + 1

    return {
        "schemaVersion": "1", "benchmark": "visable-enforcement-runtime-v1", "target": base_url,
        "syntheticCasesOnly": True, "rawNarrativesIncludedInReport": False, "runtime": runtime,
        "caseCount": len(CASES), "repetitions": repetitions, "plannedRuns": total_planned,
        "completedRuns": len(completed_runs), "transportOrHttpFailures": total_planned - len(completed_runs),
        "summary": {
            "extract": _summary(extract_values), "analyze": _summary(analyze_values), "endToEnd": _summary(total_values),
            "modelSelections": models, "predictionStatuses": statuses,
        },
        "runs": runs,
    }


def print_human(report: dict[str, Any]) -> None:
    summary = report["summary"]
    print("\n=== Visable Enforcement Runtime Benchmark ===")
    print(f"completed HTTP pipeline: {report['completedRuns']}/{report['plannedRuns']}")
    for label, key in (("extract", "extract"), ("analyze", "analyze"), ("end-to-end", "endToEnd")):
        item = summary[key]
        print(f"{label:11s} p50={item['p50Ms']} ms  p95={item['p95Ms']} ms  mean={item['meanMs']} ms")
    print("models:", json.dumps(summary["modelSelections"], ensure_ascii=False, sort_keys=True))
    print("prediction statuses:", json.dumps(summary["predictionStatuses"], ensure_ascii=False, sort_keys=True))
    if summary["predictionStatuses"].get("UNAVAILABLE"):
        reasons = sorted({item for run in report["runs"] for item in (run.get("predictionLimitations") or [])})
        print("unavailable limitations:", json.dumps(reasons, ensure_ascii=False))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default=os.environ.get("ENFORCEMENT_BENCHMARK_BASE_URL", DEFAULT_BASE_URL))
    parser.add_argument("--repetitions", type=int, default=1)
    parser.add_argument("--delay", type=float, default=11.0)
    parser.add_argument("--retry-delay", type=float, default=15.0)
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT_SECONDS)
    parser.add_argument("--output", default="")
    args = parser.parse_args()
    repetitions = max(1, min(args.repetitions, 5))
    base_url = str(args.base_url).strip().rstrip("/")
    if not base_url.startswith("https://") and not base_url.startswith("http://localhost"):
        print("Refusing non-HTTPS benchmark target.", file=sys.stderr)
        return 2
    report = build_report(base_url, repetitions, max(0.0, args.delay), max(1.0, args.timeout), max(0.0, args.retry_delay))
    print_human(report)
    encoded = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(encoded, encoding="utf-8")
        print(f"wrote {output}")
    else:
        print(encoded)
    return 0 if report["completedRuns"] > 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
