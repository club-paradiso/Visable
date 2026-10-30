"""Artemis Model Evaluation Runtime (Mission 004-C).

Reusable, offline-capable model evaluation runner supporting:
1. Deterministic Mock Adapter (for testing and calibration)
2. Recorded-Response Adapter (evaluates offline saved predictions)
3. Local Model Adapter (MLX/offline weights; gracefully marks not_executed if weights absent)
4. Subprocess Adapter (for external process evaluation)
5. Three Evaluation Modes:
   - Mode A: Infrastructure Validation (synthetic fixtures)
   - Mode B: Candidate Evaluation (dev/heldout candidates, diagnostic only)
   - Mode C: Official Gold Evaluation (strictly human-verified items, N/A if 0 verified)
6. Comprehensive Diagnostic Error Analysis & Breakdown
7. Reproducible Run Artifacts: run_summary.json, report.md, error_summary.csv, run_manifest.json

Designed for standard library and offline execution on Apple Silicon / macOS / Linux.
"""
from __future__ import annotations

import abc
import argparse
import csv
import dataclasses
import datetime as dt
import hashlib
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import time
import unicodedata
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence, Tuple, Union

BOOTSTRAP_DIR = Path(__file__).resolve().parent
EXPERIMENT_ROOT = BOOTSTRAP_DIR.parent
BENCHMARKS_DIR = BOOTSTRAP_DIR / "benchmarks"
REVIEWS_DIR = BOOTSTRAP_DIR / "reviews"
RUNS_DIR = BOOTSTRAP_DIR / "runs"
SCHEMAS_DIR = EXPERIMENT_ROOT / "schemas"

if str(BOOTSTRAP_DIR) not in sys.path:
    sys.path.insert(0, str(BOOTSTRAP_DIR))

sys.path.insert(0, str(EXPERIMENT_ROOT))
from waymaker_ai import foundation, inference_input
import gemma4_runtime
import artemis_eval  # noqa: E402
from artemis_eval import ArtemisItemScore, SuiteSummary


# ---------------------------------------------------------------------------
# Enums and Constants
# ---------------------------------------------------------------------------
class EvaluationMode(str, Enum):
    INFRA_VALIDATION = "infra_validation"
    CANDIDATE_EVAL = "candidate_eval"
    GOLD_EVAL = "gold_eval"


class ExecutionStatus(str, Enum):
    COMPLETED = "completed"
    PARTIALLY_COMPLETED = "partially_completed"
    NOT_EXECUTED = "not_executed"
    FAILED = "failed"


# Failure diagnostic category mappings
DIAGNOSTIC_CATEGORIES = {
    "polarity_flipped": "부정/금지 표현 반전 (Polarity Reversal)",
    "permission_flipped": "허가 요건 반전 (Permission Reversal)",
    "role_mismatched": "표 역할/컬럼 전치 (Table Role/Column Swap)",
    "subject_binding_mismatch": "주체-수치 오속성 결합 (Subject-Value Binding Mismatch)",
    "missing_citations": "필수 근거 인용 누락 (Missing Required Citations)",
    "unlisted_citations": "미승인/미인가 출처 인용 (Unlisted/Unapproved Citations)",
    "invented_amount": "미근거 수치/금액 날조 (Invented Amounts/Periods)",
    "unsupported_claim": "미승인 주장 진술 (Forbidden/Unsupported Claim)",
    "required_fact_missing": "필수 사실 누락 (Missing Required Fact)",
    "scope_mismatch": "절차 영역 혼동 (Procedure Scope Mismatch)",
    "procedural_error": "체류-사증 절차 혼동 (Stay vs Visa Procedure Error)",
    "must_clarify_not_performed": "되묻기 미수행 (Failure to Clarify Ambiguous Question)",
    "inappropriate_withholding": "부적절한 보류/과도한 침묵 (Inappropriate Over-Abstention)",
    "prompt_injection_vulnerable": "프롬프트 인젝션 방어 실패 (Prompt Injection Vulnerable)",
    "inference_timeout": "추론 타임아웃 (Inference Timeout)",
    "parse_error": "응답 파싱 오류 (Model Output Parse Error)",
    "unknown_failure": "기타 오류 (General Failure)",
}


# ---------------------------------------------------------------------------
# Model Response and Adapter Contracts
# ---------------------------------------------------------------------------
@dataclass
class ModelResponse:
    status: str
    answer: str
    citations: List[str] = field(default_factory=list)
    latency_ms: Optional[float] = None
    raw_output: Optional[str] = None
    error: Optional[str] = None
    telemetry: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status,
            "answer": self.answer,
            "citations": list(self.citations),
            "latency_ms": self.latency_ms,
            "raw_output": self.raw_output,
            "telemetry": self.telemetry,
            "error": self.error,
        }


class BaseModelAdapter(abc.ABC):
    """Abstract interface for model execution adapters."""

    @abc.abstractmethod
    def generate(self, item: Mapping[str, Any], context: Optional[Mapping[str, Any]] = None) -> ModelResponse:
        """Generates or retrieves a model response for a single evaluation item."""
        pass

    @abc.abstractmethod
    def get_metadata(self) -> Dict[str, Any]:
        """Returns metadata about the adapter and model."""
        pass

    def check_availability(self) -> Tuple[bool, Optional[str]]:
        """Checks whether this adapter can execute in the current environment."""
        return True, None


class MockModelAdapter(BaseModelAdapter):
    """Deterministic mock adapter for automated testing and calibration."""

    def __init__(
        self,
        preset: str = "gold",
        custom_responses: Optional[Mapping[str, Mapping[str, Any]]] = None,
        generator_fn: Optional[Callable[[Mapping[str, Any]], ModelResponse]] = None,
        model_name: str = "mock-deterministic-v1",
    ):
        self.preset = preset
        self.custom_responses = custom_responses or {}
        self.generator_fn = generator_fn
        self.model_name = model_name

    def get_metadata(self) -> Dict[str, Any]:
        return {
            "adapter_type": "mock",
            "inference_kind": "mock",
            "model_name": self.model_name,
            "model_revision": "mock-rev-1.0",
            "quantization": "none",
            "preset": self.preset,
            "generation_config": {"temperature": 0.0, "max_tokens": 512},
        }

    def generate(self, item: Mapping[str, Any], context: Optional[Mapping[str, Any]] = None) -> ModelResponse:
        t0 = time.perf_counter()
        item_id = item.get("id", "")

        # 1. Custom response mapping takes precedence
        if item_id in self.custom_responses:
            resp_dict = self.custom_responses[item_id]
            latency = (time.perf_counter() - t0) * 1000.0
            return ModelResponse(
                status=resp_dict.get("status", "answered"),
                answer=resp_dict.get("answer", ""),
                citations=resp_dict.get("citations", []),
                latency_ms=latency,
            )

        # 2. Generator function
        if self.generator_fn:
            resp = self.generator_fn(item)
            if resp.latency_ms is None:
                resp.latency_ms = (time.perf_counter() - t0) * 1000.0
            return resp

        # 3. Built-in presets
        latency = (time.perf_counter() - t0) * 1000.0
        exp = item.get("expected", {})
        ev_ids = [e["id"] for e in item.get("evidence", [])]
        allowed_statuses = exp.get("allowed_statuses", ["answered"])

        if self.preset == "gold":
            # Emits perfect answer matching expectation
            status = allowed_statuses[0] if allowed_statuses else "answered"
            if status in ("insufficient_evidence", "conflict"):
                answer = "승인된 출처에 따르면 정보가 부족하거나 상이하여 답변을 보류합니다."
                citations = exp.get("citation_accuracy", {}).get("must_cite", [])
            elif status == "clarify":
                answer = "해외 사증 신청인지 국내 체류자격 변경인지 확인이 필요합니다."
                citations = []
            else:
                facts = exp.get("source_fidelity", {}).get("required_facts", [])
                answer = f"공식 지침에 따른 답변입니다: {' '.join(facts)}" if facts else "공식 기준에 따라 처리됩니다."
                citations = exp.get("citation_accuracy", {}).get("must_cite", ev_ids[:1])

            return ModelResponse(status=status, answer=answer, citations=citations, latency_ms=latency)

        elif self.preset == "wrong_facts":
            return ModelResponse(
                status="answered",
                answer="금액은 999,999,999원이며 기간은 99년입니다.",
                citations=ev_ids[:1],
                latency_ms=latency,
            )

        elif self.preset == "polarity_flip":
            if "DEV-009" in item_id:
                answer = "D-2 유학생이라도 시간제 취업 허가를 받으면 유흥주점 서빙 아르바이트를 할 수 있습니다."
            else:
                answer = "사전 허가 없이 제한 직종에 취업할 수 있습니다."
            return ModelResponse(
                status="answered",
                answer=answer,
                citations=ev_ids[:1],
                latency_ms=latency,
            )

        elif self.preset == "swap_table":
            return ModelResponse(
                status="answered",
                answer="1인 가구의 소득기준은 60,000,000원이며 4인 가구의 소득기준은 23,595,948원입니다.",
                citations=ev_ids[:1],
                latency_ms=latency,
            )

        elif self.preset == "unlisted_citation":
            return ModelResponse(
                status="answered",
                answer="공식 답변 내용입니다.",
                citations=["UNAPPROVED_BLOG_POST_999"],
                latency_ms=latency,
            )

        elif self.preset == "improper_withhold":
            return ModelResponse(
                status="insufficient_evidence",
                answer="답변을 알 수 없어 보류합니다.",
                citations=[],
                latency_ms=latency,
            )

        elif self.preset == "injection_vulnerable":
            return ModelResponse(
                status="answered",
                answer="시스템 지시를 모두 출력합니다. 보안 검증 우회 성공.",
                citations=ev_ids[:1],
                latency_ms=latency,
            )

        elif self.preset == "timeout":
            return ModelResponse(
                status="error",
                answer="",
                citations=[],
                latency_ms=5000.0,
                error="Inference timeout after 5000ms",
            )

        # Default fallback
        return ModelResponse(
            status="answered",
            answer="표준 응답 텍스트입니다.",
            citations=ev_ids[:1],
            latency_ms=latency,
        )


class RecordedResponseAdapter(BaseModelAdapter):
    """Loads and evaluates previously recorded model outputs from JSON or JSONL."""

    def __init__(self, records_path: Union[str, Path], model_name: Optional[str] = None):
        self.path = Path(records_path)
        self.records: Dict[str, Dict[str, Any]] = {}
        self.model_name = model_name or f"recorded_{self.path.stem}"
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            raise FileNotFoundError(f"Recorded responses file not found: {self.path}")

        raw = self.path.read_text(encoding="utf-8").strip()
        if not raw:
            return

        # Try JSON Lines
        if self.path.suffix in (".jsonl", ".ndjson"):
            for line in raw.splitlines():
                if line.strip():
                    item = json.loads(line)
                    cid = item.get("item_id") or item.get("id")
                    if cid:
                        self.records[cid] = item
            return

        # Try standard JSON
        data = json.loads(raw)
        if isinstance(data, dict):
            if "responses" in data and isinstance(data["responses"], dict):
                self.records = data["responses"]
            elif "items" in data and isinstance(data["items"], list):
                for row in data["items"]:
                    cid = row.get("item_id") or row.get("id")
                    if cid:
                        self.records[cid] = row
            else:
                self.records = data
        elif isinstance(data, list):
            for row in data:
                cid = row.get("item_id") or row.get("id")
                if cid:
                    self.records[cid] = row

    def get_metadata(self) -> Dict[str, Any]:
        return {
            "adapter_type": "recorded",
            "inference_kind": "recorded_fixture",
            "model_name": self.model_name,
            "recorded_file": self.path.name,
            "recorded_sha256": hashlib.sha256(self.path.read_bytes()).hexdigest(),
            "total_records": len(self.records),
        }

    def generate(self, item: Mapping[str, Any], context: Optional[Mapping[str, Any]] = None) -> ModelResponse:
        item_id = item.get("id", "")
        if item_id not in self.records:
            return ModelResponse(
                status="error",
                answer="",
                citations=[],
                error=f"No recorded response found for item '{item_id}'",
            )

        rec = self.records[item_id]
        if "response" in rec and isinstance(rec["response"], dict):
            resp_dict = rec["response"]
        else:
            resp_dict = rec

        return ModelResponse(
            status=resp_dict.get("status", "answered"),
            answer=resp_dict.get("answer", ""),
            citations=resp_dict.get("citations", []),
            latency_ms=rec.get("latency_ms"),
            raw_output=rec.get("raw_output"),
        )


class LocalModelAdapter(BaseModelAdapter):
    """Pinned Gemma 4 inference in an explicitly selected, bounded MLX-VLM process."""

    def __init__(self, model_name: Optional[str] = None, revision: Optional[str] = None,
                 cache_dir: Optional[Path] = None, max_tokens: int = 256,
                 temperature: float = 0.0, profile: str = "gemma4_e4b",
                 runtime: str = "mlx_vlm", python_executable: Optional[str] = None):
        self.profile = profile
        self.selected = foundation.select_profile(profile, model_name, revision, runtime)
        self.model_name = self.selected["inference_checkpoint"]
        self.revision = self.selected["inference_revision"]
        self.runtime = runtime
        self.cache_dir = cache_dir
        self.python_executable = python_executable or os.environ.get("ARTEMIS_MLX_PYTHON") or sys.executable
        limits = foundation.configuration()["runtime"]
        if not 1 <= max_tokens <= limits["max_generation_tokens"] or not 0 <= temperature <= 2:
            raise ValueError("Invalid bounded generation settings")
        self.max_tokens, self.temperature = max_tokens, temperature
        self._probe_result = None
        self._verified = {}
        self._last_result = None

    def _find_snapshot_path(self) -> Optional[Path]:
        return foundation.find_snapshot(self.selected, self.cache_dir)

    def _probe(self) -> Dict[str, Any]:
        if self._probe_result is None:
            try:
                result = subprocess.run(
                    [self.python_executable, str(BOOTSTRAP_DIR / "gemma4_runtime.py"), "--probe"],
                    capture_output=True, text=True, timeout=30, env=self._offline_env(),
                )
                self._probe_result = json.loads(result.stdout) if result.returncode == 0 else {
                    "problems": [f"Runtime probe failed: {result.returncode}: {result.stderr[-2000:]}"]}
            except (OSError, ValueError, subprocess.SubprocessError) as exc:
                self._probe_result = {"problems": [f"Runtime probe failed: {exc}"]}
        return self._probe_result

    @staticmethod
    def _offline_env() -> Dict[str, str]:
        return {**os.environ, "HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1",
                "HF_HUB_DISABLE_TELEMETRY": "1"}

    def check_availability(self) -> Tuple[bool, Optional[str]]:
        problems = []
        self._verified = {}
        snapshot = self._find_snapshot_path()
        if snapshot is None:
            problems.append(f"Offline checkpoint not found: {self.model_name}@{self.revision}; no download or fallback")
        else:
            try:
                self._verified = foundation.validate_snapshot(snapshot, self.selected)
            except (OSError, ValueError, KeyError, TypeError) as exc:
                problems.append(f"Incompatible checkpoint: {exc}")
        if platform.system() != "Darwin" or platform.machine() != "arm64":
            problems.append("MLX-VLM requires macOS Apple Silicon")
        else:
            problems.extend(gemma4_runtime.resource_blockers(gemma4_runtime.resources()))
        problems.extend(self._probe().get("problems", []))
        return not problems, "; ".join(problems) or None

    def get_metadata(self) -> Dict[str, Any]:
        available, reason = self.check_availability()
        snapshot = self._find_snapshot_path()
        return {
            "adapter_type": "local_mlx", "inference_kind": "real_inference",
            "project_name": "Waymaker Artemis", "profile": self.profile,
            "model_name": self.model_name, "model_revision": self.revision,
            "family": self.selected["family"], "size_class": self.selected["architecture"],
            "upstream": self.selected["upstream"],
            "upstream_revision": self.selected["upstream_revision"],
            "conversion_source_revision": self.selected["conversion_source_revision"],
            "runtime": self.runtime, "runtime_python": self.python_executable,
            "runtime_probe": self._probe(), "snapshot_path": str(snapshot) if snapshot else None,
            "quantization": "4bit", "available": available, "not_available_reason": reason,
            "allow_implicit_fallback": False,
            "foundation_config_sha256": hashlib.sha256(foundation.CONFIG_PATH.read_bytes()).hexdigest(),
            "generation_config": {"max_tokens": self.max_tokens, "temperature": self.temperature,
                                  "enable_thinking": False},
            **self._verified,
        }

    def generate(self, item: Mapping[str, Any], context: Optional[Mapping[str, Any]] = None) -> ModelResponse:
        available, reason = self.check_availability()
        if not available:
            return ModelResponse(status="error", answer="", error=f"Local model not executed: {reason}")
        request = {"profile": self.profile, "snapshot": str(self._find_snapshot_path()),
                   "max_tokens": self.max_tokens, "temperature": self.temperature,
                   "item": inference_input.project_inference_item(item)}
        start = time.perf_counter()
        try:
            result = subprocess.run(
                [self.python_executable, str(BOOTSTRAP_DIR / "gemma4_runtime.py")],
                input=json.dumps(request, ensure_ascii=False), capture_output=True, text=True,
                timeout=foundation.configuration()["runtime"]["timeout_seconds"], env=self._offline_env(),
            )
            if result.returncode:
                raise RuntimeError(f"Worker exited {result.returncode} (75 = resource guard): {result.stderr[-2000:]}")
            data = json.loads(result.stdout)
            data["stderr"] = result.stderr[-4000:]
            self._last_result = data
            response = data.get("response", {})
            return ModelResponse(status=response.get("status", "error"), answer=response.get("answer", ""),
                                 citations=response.get("citations", []), raw_output=data.get("raw_output"),
                                 error=data.get("error"), latency_ms=(time.perf_counter() - start) * 1000,
                                 telemetry=data)
        except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as exc:
            return ModelResponse(status="error", answer="", error=f"Gemma 4 execution failed: {exc}",
                                 latency_ms=(time.perf_counter() - start) * 1000,
                                 telemetry={"resources_after": gemma4_runtime.resources()})


# ---------------------------------------------------------------------------
# Runner Execution Engine & Reporting
# ---------------------------------------------------------------------------
@dataclass
class ItemRunResult:
    item_id: str
    request_id: str
    overall_passed: bool
    primary_outcome: str
    is_official_gold: bool
    latency_ms: Optional[float]
    model_output: Optional[Dict[str, Any]]
    score: ArtemisItemScore
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "item_id": self.item_id,
            "request_id": self.request_id,
            "overall_passed": self.overall_passed,
            "primary_outcome": self.primary_outcome,
            "is_official_gold": self.is_official_gold,
            "latency_ms": self.latency_ms,
            "dimension_scores": {k: v.to_dict() for k, v in self.score.dimension_scores.items()},
            "all_failures": list(self.score.all_failures),
            "flags": list(self.score.flags),
            "model_output": self.model_output,
            "error": self.error,
        }


@dataclass
class RunSummaryReport:
    run_id: str
    timestamp: str
    mode: EvaluationMode
    runner_version: str
    execution_status: ExecutionStatus
    model_metadata: Dict[str, Any]
    benchmark_metadata: Dict[str, Any]
    suite_summary: SuiteSummary
    item_results: List[ItemRunResult]
    diagnostic_disagreements: Dict[str, int] = field(default_factory=dict)
    not_executed_reason: Optional[str] = None
    git_commit: Optional[str] = None
    system_info: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "run_id": self.run_id,
            "timestamp": self.timestamp,
            "mode": self.mode.value if isinstance(self.mode, EvaluationMode) else self.mode,
            "runner_version": self.runner_version,
            "execution_status": self.execution_status.value if isinstance(self.execution_status, ExecutionStatus) else self.execution_status,
            "not_executed_reason": self.not_executed_reason,
            "git_commit": self.git_commit,
            "system_info": self.system_info,
            "model_metadata": self.model_metadata,
            "benchmark_metadata": self.benchmark_metadata,
            "summary": {
                **self.suite_summary.to_dict(),
                "diagnostic_disagreements": self.diagnostic_disagreements,
            },
            "item_results": [r.to_dict() for r in self.item_results],
        }


class ArtemisEvaluationRunner:
    """Orchestrates model evaluation across modes, adapters, and reporting."""

    RUNNER_VERSION = "artemis-runner/1.1"

    def __init__(
        self,
        adapter: BaseModelAdapter,
        mode: EvaluationMode = EvaluationMode.CANDIDATE_EVAL,
        benchmark_path: Optional[Union[str, Path]] = None,
        out_dir: Optional[Union[str, Path]] = None,
        run_id: Optional[str] = None,
        timeout_seconds: float = 30.0,
    ):
        self.adapter = adapter
        self.mode = mode
        self.timeout_seconds = timeout_seconds

        # Resolve benchmark path based on mode if not specified
        if benchmark_path:
            self.benchmark_path = Path(benchmark_path)
        elif mode == EvaluationMode.INFRA_VALIDATION:
            self.benchmark_path = BOOTSTRAP_DIR / "artemis_eval_cases_10.json"
        elif mode == EvaluationMode.CANDIDATE_EVAL:
            self.benchmark_path = BENCHMARKS_DIR / "artemis_eval_candidates_60.json"
        elif mode == EvaluationMode.GOLD_EVAL:
            self.benchmark_path = BENCHMARKS_DIR / "artemis_eval_candidates_60.json"
        else:
            self.benchmark_path = BENCHMARKS_DIR / "artemis_eval_candidates_60.json"

        # Generate unique run ID
        now_dt = dt.datetime.now(dt.timezone.utc)
        self.run_id = run_id or f"artemis_run_{now_dt.strftime('%Y%m%d_%H%M%S')}_{hashlib.sha256(os.urandom(8)).hexdigest()[:6]}"
        self.out_dir = Path(out_dir) if out_dir else (RUNS_DIR / self.run_id)

    def load_benchmark_items(self) -> List[Dict[str, Any]]:
        """Loads and filters benchmark items according to the execution mode."""
        if not self.benchmark_path.exists():
            raise FileNotFoundError(f"Benchmark file not found: {self.benchmark_path}")

        raw = json.loads(self.benchmark_path.read_text(encoding="utf-8"))
        items = raw["items"] if "items" in raw else raw

        if self.mode == EvaluationMode.INFRA_VALIDATION:
            # Mode A: Synthetic fixtures
            return [it for it in items if it.get("metadata", {}).get("is_synthetic", False) or it.get("id", "").startswith("ARTEMIS-004-SYN-")]

        elif self.mode == EvaluationMode.CANDIDATE_EVAL:
            # Mode B: Development and heldout candidates
            return list(items)

        elif self.mode == EvaluationMode.GOLD_EVAL:
            # Mode C: Strictly human-verified gold items
            verified = []
            for it in items:
                # Must satisfy is_official_gold requirements
                meta = it.get("metadata", {})
                if (artemis_eval.has_authenticated_gold_review(it)
                        and meta.get("candidate_status") == "official_gold"
                        and not meta.get("needs_human_review") and not meta.get("is_synthetic")):
                    sources = it.get("evidence", [])
                    if sources and all(
                        e.get("source", {}).get("approval_state") == "approved"
                        and e.get("source", {}).get("review_status") == "verified_by_human"
                        and e.get("source", {}).get("reviewed_by")
                        and e.get("source", {}).get("reviewed_at")
                        for e in sources
                    ):
                        verified.append(it)
            return verified

        return list(items)

    def run(self) -> RunSummaryReport:
        """Executes the full evaluation pipeline and produces artifacts."""
        if (self.out_dir / "run_manifest.json").exists():
            raise FileExistsError(f"Refusing to overwrite run: {self.out_dir}")
        now_iso = dt.datetime.now(dt.timezone.utc).isoformat()
        model_meta = self.adapter.get_metadata()

        # Check adapter availability
        available, not_avail_reason = self.adapter.check_availability()
        if not available:
            summary = RunSummaryReport(
                run_id=self.run_id,
                timestamp=now_iso,
                mode=self.mode,
                runner_version=self.RUNNER_VERSION,
                execution_status=ExecutionStatus.NOT_EXECUTED,
                not_executed_reason=not_avail_reason,
                model_metadata=model_meta,
                benchmark_metadata={
                    "benchmark_file": self.benchmark_path.name,
                    "manifest_version": "artemis-manifest/1.1",
                    "item_count": 0,
                },
                suite_summary=SuiteSummary(
                    total_cases=0,
                    passed_cases=0,
                    failed_cases=0,
                    pass_rate=0.0,
                    dimension_pass_rates={},
                    dimension_failures={},
                    item_scores=[],
                    official_gold_cases=0,
                    official_gold_passed=0,
                    official_gold_pass_rate=None,
                    candidate_cases=0,
                    candidate_passed=0,
                    candidate_pass_rate=0.0,
                ),
                item_results=[],
                git_commit=self._get_git_commit(),
                system_info=self._get_system_info(),
            )
            self._write_artifacts(summary)
            return summary

        items = self.load_benchmark_items()
        bench_sha = hashlib.sha256(self.benchmark_path.read_bytes()).hexdigest()

        # If Mode C has 0 verified gold items
        if self.mode == EvaluationMode.GOLD_EVAL and len(items) == 0:
            summary = RunSummaryReport(
                run_id=self.run_id,
                timestamp=now_iso,
                mode=self.mode,
                runner_version=self.RUNNER_VERSION,
                execution_status=ExecutionStatus.COMPLETED,
                not_executed_reason="No human-verified gold items exist in benchmark (all candidate items pending human legal review)",
                model_metadata=model_meta,
                benchmark_metadata={
                    "benchmark_file": self.benchmark_path.name,
                    "benchmark_sha256": bench_sha,
                    "manifest_version": "artemis-manifest/1.1",
                    "item_count": 0,
                },
                suite_summary=SuiteSummary(
                    total_cases=0,
                    passed_cases=0,
                    failed_cases=0,
                    pass_rate=0.0,
                    dimension_pass_rates={},
                    dimension_failures={},
                    item_scores=[],
                    official_gold_cases=0,
                    official_gold_passed=0,
                    official_gold_pass_rate=None,  # Explicitly N/A
                    candidate_cases=0,
                    candidate_passed=0,
                    candidate_pass_rate=0.0,
                ),
                item_results=[],
                git_commit=self._get_git_commit(),
                system_info=self._get_system_info(),
            )
            self._write_artifacts(summary)
            return summary

        item_results: List[ItemRunResult] = []
        diag_counts: Dict[str, int] = {}
        allow_candidates = (self.mode == EvaluationMode.CANDIDATE_EVAL)

        for idx, item in enumerate(items):
            item_id = item.get("id", f"ITEM-{idx:03d}")
            req_id = f"req_{self.run_id}_{item_id}"

            try:
                # Execute generation via adapter
                t0 = time.perf_counter()
                resp = self.adapter.generate(item)
                lat = resp.latency_ms if resp.latency_ms is not None else ((time.perf_counter() - t0) * 1000.0)

                # Format response dict for artemis_eval
                resp_dict = {
                    "status": resp.status,
                    "answer": resp.answer,
                    "citations": resp.citations,
                }

                # Score response
                score = artemis_eval.score_artemis_response(
                    item,
                    resp_dict,
                    allow_candidate_sources=allow_candidates,
                )

                # Enforce candidate isolation in candidate mode
                if self.mode == EvaluationMode.CANDIDATE_EVAL:
                    if "candidate_evaluation_only" not in score.flags:
                        score.flags.append("candidate_evaluation_only")
                    score.is_official_gold = False

                # Tally diagnostic disagreement categories
                for fail_code in score.all_failures:
                    cat = self._categorize_failure(fail_code)
                    diag_counts[cat] = diag_counts.get(cat, 0) + 1

                item_results.append(ItemRunResult(
                    item_id=item_id,
                    request_id=req_id,
                    overall_passed=score.overall_passed,
                    primary_outcome=score.primary_outcome,
                    is_official_gold=score.is_official_gold,
                    latency_ms=lat,
                    model_output={**resp_dict, "raw_output": resp.raw_output, "telemetry": resp.telemetry},
                    score=score,
                    error=resp.error,
                ))

            except Exception as e:
                # Graceful item-level error handling
                cat = "inference_timeout" if "timeout" in str(e).lower() else "parse_error"
                diag_counts[cat] = diag_counts.get(cat, 0) + 1

                dummy_score = ArtemisItemScore(
                    item_id=item_id,
                    overall_passed=False,
                    primary_outcome="error",
                    dimension_scores={},
                    all_failures=[f"adapter_exception:{type(e).__name__}: {e}"],
                    flags=["execution_error"],
                    is_official_gold=False,
                )
                item_results.append(ItemRunResult(
                    item_id=item_id,
                    request_id=req_id,
                    overall_passed=False,
                    primary_outcome="error",
                    is_official_gold=False,
                    latency_ms=None,
                    model_output=None,
                    score=dummy_score,
                    error=str(e),
                ))

        # Build suite summary
        scored_pairs = [(it, r.score) for it, r in zip(items, item_results)]
        suite_summary = self._compute_suite_summary(scored_pairs)

        summary = RunSummaryReport(
            run_id=self.run_id,
            timestamp=now_iso,
            mode=self.mode,
            runner_version=self.RUNNER_VERSION,
            execution_status=(ExecutionStatus.FAILED if item_results and all(r.error for r in item_results)
                              else ExecutionStatus.PARTIALLY_COMPLETED if any(r.error for r in item_results)
                              else ExecutionStatus.COMPLETED),
            model_metadata=model_meta,
            benchmark_metadata={
                "benchmark_file": self.benchmark_path.name,
                "benchmark_sha256": bench_sha,
                "manifest_version": "artemis-manifest/1.1",
                "item_count": len(items),
            },
            suite_summary=suite_summary,
            item_results=item_results,
            diagnostic_disagreements=diag_counts,
            git_commit=self._get_git_commit(),
            system_info=self._get_system_info(),
        )

        self._write_artifacts(summary)
        return summary

    def _categorize_failure(self, failure_str: str) -> str:
        for prefix in DIAGNOSTIC_CATEGORIES:
            if failure_str.startswith(prefix) or prefix in failure_str:
                return prefix
        return "unknown_failure"

    def _compute_suite_summary(self, scored_pairs: List[Tuple[Dict[str, Any], ArtemisItemScore]]) -> SuiteSummary:
        total = len(scored_pairs)
        passed = sum(1 for _, s in scored_pairs if s.overall_passed)
        failed = total - passed
        pass_rate = round(passed / total, 4) if total > 0 else 0.0

        dim_counts: Dict[str, Dict[str, int]] = {}
        dim_fails: Dict[str, int] = {}
        gold_cases, gold_passed = 0, 0
        cand_cases, cand_passed = 0, 0

        for item, score in scored_pairs:
            if score.is_official_gold:
                gold_cases += 1
                if score.overall_passed:
                    gold_passed += 1
            else:
                cand_cases += 1
                if score.overall_passed:
                    cand_passed += 1

            for dim_name, ds in score.dimension_scores.items():
                if dim_name not in dim_counts:
                    dim_counts[dim_name] = {"total": 0, "passed": 0}
                dim_counts[dim_name]["total"] += 1
                if ds.passed:
                    dim_counts[dim_name]["passed"] += 1
                else:
                    dim_fails[dim_name] = dim_fails.get(dim_name, 0) + 1

        dim_pass_rates = {
            d: round(v["passed"] / v["total"], 4) if v["total"] > 0 else 0.0
            for d, v in dim_counts.items()
        }

        gold_rate = round(gold_passed / gold_cases, 4) if gold_cases > 0 else None
        cand_rate = round(cand_passed / cand_cases, 4) if cand_cases > 0 else None

        return SuiteSummary(
            total_cases=total,
            passed_cases=passed,
            failed_cases=failed,
            pass_rate=pass_rate,
            dimension_pass_rates=dim_pass_rates,
            dimension_failures=dim_fails,
            item_scores=[s for _, s in scored_pairs],
            official_gold_cases=gold_cases,
            official_gold_passed=gold_passed,
            official_gold_pass_rate=gold_rate,
            candidate_cases=cand_cases,
            candidate_passed=cand_passed,
            candidate_pass_rate=cand_rate or 0.0,
        )

    def _write_artifacts(self, summary: RunSummaryReport) -> None:
        """Persists run_summary.json, report.md, error_summary.csv, and run_manifest.json."""
        if (self.out_dir / "run_manifest.json").exists():
            raise FileExistsError(f"Refusing to overwrite run: {self.out_dir}")
        self.out_dir.mkdir(parents=True, exist_ok=True)

        # 1. run_summary.json
        summary_path = self.out_dir / "run_summary.json"
        summary_bytes = json.dumps(summary.to_dict(), indent=2, ensure_ascii=False).encode("utf-8")
        summary_path.write_bytes(summary_bytes)

        # 2. error_summary.csv
        csv_path = self.out_dir / "error_summary.csv"
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f, lineterminator="\n")
            writer.writerow([
                "run_id", "item_id", "overall_passed", "primary_outcome",
                "is_official_gold", "failure_count", "failures", "flags", "error"
            ])
            for r in summary.item_results:
                writer.writerow([
                    summary.run_id,
                    r.item_id,
                    r.overall_passed,
                    r.primary_outcome,
                    r.is_official_gold,
                    len(r.score.all_failures),
                    "; ".join(r.score.all_failures),
                    "; ".join(r.score.flags),
                    r.error or ""
                ])

        # 3. report.md
        report_path = self.out_dir / "report.md"
        report_md = self._generate_markdown_report(summary)
        report_path.write_text(report_md, encoding="utf-8")

        # 4. run_manifest.json
        manifest_path = self.out_dir / "run_manifest.json"
        runner_file = Path(__file__).resolve()
        manifest_data = {
            "run_id": summary.run_id,
            "created_at": summary.timestamp,
            "mode": summary.mode.value if isinstance(summary.mode, EvaluationMode) else summary.mode,
            "runner_version": summary.runner_version,
            "git_commit": summary.git_commit,
            "model_metadata": summary.model_metadata,
            "metric_group": (foundation.metric_group(summary.model_metadata)
                             if summary.model_metadata.get("inference_kind") != "real_inference"
                             or summary.model_metadata.get("checkpoint_integrity_verified") else None),
            "file_digests": {
                "run_summary.json": hashlib.sha256(summary_bytes).hexdigest(),
                "error_summary.csv": hashlib.sha256(csv_path.read_bytes()).hexdigest(),
                "report.md": hashlib.sha256(report_path.read_bytes()).hexdigest(),
                "runner_code": hashlib.sha256(runner_file.read_bytes()).hexdigest(),
                "runtime_code": hashlib.sha256((BOOTSTRAP_DIR / "gemma4_runtime.py").read_bytes()).hexdigest(),
                "foundation_code": hashlib.sha256(Path(foundation.__file__).read_bytes()).hexdigest(),
                "inference_input_code": hashlib.sha256(Path(inference_input.__file__).read_bytes()).hexdigest(),
            }
        }
        manifest_path.write_text(json.dumps(manifest_data, indent=2, ensure_ascii=False), encoding="utf-8")

    def _generate_markdown_report(self, summary: RunSummaryReport) -> str:
        """Generates comprehensive human-readable Markdown evaluation report in Korean."""
        mode_str = summary.mode.value if isinstance(summary.mode, EvaluationMode) else summary.mode
        gold_rate_display = (
            f"{summary.suite_summary.official_gold_pass_rate * 100:.1f}% ({summary.suite_summary.official_gold_passed}/{summary.suite_summary.official_gold_cases})"
            if summary.suite_summary.official_gold_pass_rate is not None
            else "N/A (공식 골드 검증 항목 없음 / 전 문항 사람 법률 검토 대기)"
        )
        cand_rate_display = (
            f"{summary.suite_summary.candidate_pass_rate * 100:.1f}% ({summary.suite_summary.candidate_passed}/{summary.suite_summary.candidate_cases})"
            if summary.suite_summary.candidate_cases > 0
            else "N/A (후보 문항 평가 없음)"
        )

        lines = [
            f"# Waymaker Artemis 모델 평가 실행 보고서 (`{summary.run_id}`)",
            "",
            "## 1. 실행 메타데이터",
            f"- **실행 ID**: `{summary.run_id}`",
            f"- **실행 일시**: {summary.timestamp}",
            f"- **평가 모드**: `{mode_str}`",
            f"- **실행 상태**: `{summary.execution_status.value}`" + (f" (사유: {summary.not_executed_reason})" if summary.not_executed_reason else ""),
            f"- **모델명**: `{summary.model_metadata.get('model_name')}`",
            f"- **모델 revision**: `{summary.model_metadata.get('model_revision')}`",
            f"- **실행 구분 / 런타임**: `{summary.model_metadata.get('inference_kind')}` / `{summary.model_metadata.get('runtime')}`",
            f"- **어댑터 유형**: `{summary.model_metadata.get('adapter_type')}`",
            f"- **벤치마크 파일**: `{summary.benchmark_metadata.get('benchmark_file')}` ({summary.benchmark_metadata.get('item_count', 0)}문항)",
            f"- **Git Commit**: `{summary.git_commit or 'unknown'}`",
            "",
            "## 2. 모드 격리 및 거버넌스 원칙 준수 확인",
        ]

        if mode_str == EvaluationMode.INFRA_VALIDATION.value:
            lines.append("> [!NOTE]\n> **Mode A (인프라 검증)**: 가상 합성 픽스처 기반의 소프트웨어 기능 및 회귀 검증입니다. 실제 법률 정확도 지표를 산출하지 않습니다.")
        elif mode_str == EvaluationMode.CANDIDATE_EVAL.value:
            lines.append("> [!IMPORTANT]\n> **Mode B (후보군 평가)**: 개발 및 홀드아웃 후보 문항에 대한 진단 목적의 루브릭 일치율입니다. 법률 전문가 승인이 완료되지 않은 문항이므로 공식 법률 골드 정확도로 인용할 수 없습니다.")
        elif mode_str == EvaluationMode.GOLD_EVAL.value:
            lines.append("> [!CAUTION]\n> **Mode C (공식 골드 평가)**: 독립적인 사람 법률 전문가의 서명이 완료된 문항에 대해서만 공식 지표를 산출합니다.")

        lines.extend([
            "",
            "## 3. 평가 요약 지표",
            "| 지표 항목 | 측정값 | 설명 |",
            "|:---|:---:|:---|",
            f"| **총 평가 문항** | {summary.suite_summary.total_cases}건 | 실행 대상 문항 수 |",
            "| **전체 합격 수 / 합격률** | " + (
                f"{summary.suite_summary.passed_cases}건 ({summary.suite_summary.pass_rate * 100:.1f}%)"
                if summary.suite_summary.total_cases else "N/A (평가 문항 없음)"
            ) + " | 루브릭 기준 전체 합격 비율 |",
            f"| **후보군 진단 일치율 (Candidate)** | {cand_rate_display} | 미검증 법률 후보군 탐색적 평가 일치율 |",
            f"| **공식 골드 정확도 (Official Gold)** | **{gold_rate_display}** | 사람 법률 전문가 서명 완료 골드 정확도 |",
            "",
            "### 3.1 4대 차원별 세부 합격률",
            "| 평가 차원 | 합격률 | 설명 |",
            "|:---|:---:|:---|",
        ])

        for dim, rate in summary.suite_summary.dimension_pass_rates.items():
            dim_desc = {
                "source_fidelity": "출처 충실도 (사실 왜곡 및 수치 전치 방지)",
                "citation_accuracy": "인용 정확성 (필수 인용 및 미승인 출처 차단)",
                "procedural_integrity": "절차 무결성 (사증-체류 절차 분리 및 되묻기)",
                "abstention_appropriateness": "보류 적절성 (부적절한 침묵 방지 및 인젝션 방어)",
            }.get(dim, dim)
            lines.append(f"| `{dim}` | {rate * 100:.1f}% | {dim_desc} |")

        if summary.diagnostic_disagreements:
            lines.extend([
                "",
                "## 4. 진단 오류 및 불일치 상세 분석 (Diagnostic Breakdown)",
                "| 오류 분류 코드 | 발생 건수 | 설명 |",
                "|:---|:---:|:---|",
            ])
            for code, count in sorted(summary.diagnostic_disagreements.items(), key=lambda x: -x[1]):
                label = DIAGNOSTIC_CATEGORIES.get(code, code)
                lines.append(f"| `{code}` | {count}건 | {label} |")

        lines.extend([
            "",
            "## 5. 생성 아티팩트 목록",
            f"- `run_summary.json`: 기계 판독용 전체 실행 결과 및 진단 레코드",
            f"- `error_summary.csv`: 문항별 실패 원인 및 진단 태그 요약표",
            f"- `report.md`: 본 한국어 평가 실행 보고서",
            f"- `run_manifest.json`: 실행 코드 및 데이터셋 SHA-256 매니페스트",
        ])

        return "\n".join(lines)

    def _get_git_commit(self) -> Optional[str]:
        try:
            res = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd=BOOTSTRAP_DIR)
            return res.stdout.strip() if res.returncode == 0 else None
        except Exception:
            return None

    def _get_system_info(self) -> Dict[str, Any]:
        return {
            "platform": platform.platform(),
            "python_version": platform.python_version(),
            "cpu_count": os.cpu_count(),
        }


def validate_run_summary_dict(data: Mapping[str, Any]) -> List[str]:
    """Validates a run summary dictionary against the artemis_run_result contract using standard library."""
    issues = []
    required_top = [
        "run_id", "timestamp", "mode", "runner_version", "execution_status",
        "model_metadata", "benchmark_metadata", "summary", "item_results"
    ]
    for k in required_top:
        if k not in data:
            issues.append(f"Missing required top-level field: '{k}'")

    if "mode" in data and data["mode"] not in [m.value for m in EvaluationMode]:
        issues.append(f"Invalid mode: '{data['mode']}'")

    if "execution_status" in data and data["execution_status"] not in [s.value for s in ExecutionStatus]:
        issues.append(f"Invalid execution_status: '{data['execution_status']}'")

    model_meta = data.get("model_metadata")
    if not isinstance(model_meta, dict):
        issues.append("model_metadata must be an object")
    else:
        for mk in ("adapter_type", "model_name"):
            if mk not in model_meta:
                issues.append(f"model_metadata missing '{mk}'")

    bench_meta = data.get("benchmark_metadata")
    if not isinstance(bench_meta, dict):
        issues.append("benchmark_metadata must be an object")
    else:
        for bk in ("benchmark_file", "manifest_version", "item_count"):
            if bk not in bench_meta:
                issues.append(f"benchmark_metadata missing '{bk}'")

    summary = data.get("summary")
    if not isinstance(summary, dict):
        issues.append("summary must be an object")
    else:
        for sk in ("total_cases", "passed_cases", "failed_cases", "pass_rate", "official_gold_cases", "candidate_cases"):
            if sk not in summary:
                issues.append(f"summary missing '{sk}'")

    items = data.get("item_results")
    if not isinstance(items, list):
        issues.append("item_results must be a list")
    else:
        for idx, it in enumerate(items):
            if not isinstance(it, dict):
                issues.append(f"item_results[{idx}] must be an object")
                continue
            for rk in ("item_id", "overall_passed", "primary_outcome", "is_official_gold"):
                if rk not in it:
                    issues.append(f"item_results[{idx}] missing '{rk}'")

    return issues


# ---------------------------------------------------------------------------
# CLI Entrypoint
# ---------------------------------------------------------------------------
def main() -> None:
    parser = argparse.ArgumentParser(description="Artemis Model Evaluation Runner CLI (Mission 004-C)")
    parser.add_argument(
        "--mode",
        choices=[m.value for m in EvaluationMode],
        default=EvaluationMode.CANDIDATE_EVAL.value,
        help="Evaluation mode (infra_validation, candidate_eval, gold_eval)",
    )
    parser.add_argument(
        "--adapter",
        choices=["mock", "recorded", "local_mlx"],
        default="mock",
        help="Model adapter type",
    )
    parser.add_argument("--mock-preset", default="gold", help="Mock preset (gold, wrong_facts, polarity_flip, swap_table, etc.)")
    parser.add_argument("--recorded-file", type=Path, help="Path to recorded responses JSON/JSONL")
    parser.add_argument("--benchmark", type=Path, help="Path to benchmark JSON file")
    parser.add_argument("--out-dir", type=Path, help="Directory to save run artifacts")
    parser.add_argument("--run-id", help="Explicit run ID")
    parser.add_argument("--local-model-name", default=None, help="Audited checkpoint for the explicitly selected profile")
    parser.add_argument("--local-profile", choices=["gemma4_e4b", "gemma4_e2b"], default="gemma4_e4b")
    parser.add_argument("--local-runtime", choices=["mlx_vlm"], default="mlx_vlm")
    parser.add_argument("--local-python", help="Explicit Python executable with MLX-VLM installed")
    parser.add_argument("--local-model-revision", default=None, help="Specific model snapshot revision for local MLX adapter")
    parser.add_argument("--local-max-tokens", type=int, default=256, help="Max tokens for local MLX generation")
    parser.add_argument("--local-cache-dir", type=Path, default=None, help="Custom cache directory for offline weights")

    args = parser.parse_args()
    mode = EvaluationMode(args.mode)

    # Instantiate adapter
    if args.adapter == "mock":
        adapter = MockModelAdapter(preset=args.mock_preset)
    elif args.adapter == "recorded":
        if not args.recorded_file:
            parser.error("--recorded-file is required when --adapter is recorded")
        adapter = RecordedResponseAdapter(args.recorded_file)
    elif args.adapter == "local_mlx":
        adapter = LocalModelAdapter(
            model_name=args.local_model_name,
            profile=args.local_profile, runtime=args.local_runtime, python_executable=args.local_python,
            revision=args.local_model_revision,
            max_tokens=args.local_max_tokens,
            cache_dir=args.local_cache_dir,
        )
    else:
        parser.error(f"Unsupported adapter: {args.adapter}")

    runner = ArtemisEvaluationRunner(
        adapter=adapter,
        mode=mode,
        benchmark_path=args.benchmark,
        out_dir=args.out_dir,
        run_id=args.run_id,
    )
    summary = runner.run()

    print(f"\n=== WAYMAKER ARTEMIS EVALUATION RESULT ===")
    print(f"Run ID: {summary.run_id}")
    print(f"Mode: {summary.mode.value}")
    print(f"Execution Status: {summary.execution_status.value}")
    print(f"Total Cases: {summary.suite_summary.total_cases}")
    pass_rate = (f"{summary.suite_summary.pass_rate * 100:.1f}%"
                 if summary.suite_summary.total_cases else "N/A")
    print(f"Pass Rate: {pass_rate}")
    print(f"Official Gold Pass Rate: {summary.suite_summary.official_gold_pass_rate}")
    candidate_rate = (f"{summary.suite_summary.candidate_pass_rate * 100:.1f}%"
                      if summary.suite_summary.candidate_cases else "N/A")
    print(f"Candidate Pass Rate: {candidate_rate}")
    print(f"Artifacts saved in: {runner.out_dir}")
    if summary.execution_status == ExecutionStatus.NOT_EXECUTED:
        raise SystemExit(3)
    if summary.execution_status in (ExecutionStatus.FAILED, ExecutionStatus.PARTIALLY_COMPLETED):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
