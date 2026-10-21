"""Model baselines: one structured-output path, two clients.

Why the mock exists: the model path (prompt → constrained JSON → validation →
normalized prediction → scoring) has to be exercised in tests and CI, where no
model may run. ``mock_model`` sends the same request a real model would get to
a deterministic stub that always abstains or returns nulls. Its scores are a
floor, not a result.

``openai_compatible`` talks to a *local* OpenAI-compatible server (vLLM,
Ollama) and is available only when ``WAYMAKER_EVAL_MODEL_ENDPOINT`` is set.
The endpoint must be a loopback address: sending held-out items to a remote
service could leak them into someone's training data (contamination), so there
is no override. No API key is read or sent.

A model answers only the classification, entity and abstention tasks. It is
never asked to verify a citation or pick a law version; deterministic code
does that (predictions.MODEL_TASKS).

Prompts are built from ``input.question`` and ``input.payload_status_code``
only. Labels, scenario notes and source bundles never reach a prompt.
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence, Tuple
from urllib.parse import urlsplit

from waymaker_ai.contracts import FINE_PROCEDURES, VISA_SCOPE_PROCEDURES, AnchorKind, TemporalWarning, VerificationCode
from waymaker_ai.evaluation.baselines.base import Baseline, EvalItem, ItemResult, RunContext, measured
from waymaker_ai.evaluation.benchmark import payload_code_of, question_of
from waymaker_ai.evaluation.predictions import (
    MODEL_TASKS,
    SCHEMA_VIOLATIONS_KEY,
    model_output_schema,
    parse_model_output,
)

ENDPOINT_ENV = "WAYMAKER_EVAL_MODEL_ENDPOINT"
MODEL_ENV = "WAYMAKER_EVAL_MODEL_NAME"
TIMEOUT_ENV = "WAYMAKER_EVAL_MODEL_TIMEOUT"
LOOPBACK_HOSTS = frozenset({"localhost", "127.0.0.1", "::1"})
MAX_RAW_CHARS = 2000

#: Issue keys a model may use when it withholds a conclusion: the contract's
#: own warning and verification vocabulary, nothing taken from benchmark labels.
ISSUE_KEYS: Tuple[str, ...] = tuple(sorted(
    {w.value for w in TemporalWarning} | {c.value for c in VerificationCode}
))

DECODING: Dict[str, Any] = {"temperature": 0, "seed": 0, "max_tokens": 512}

_CLASSIFICATION_SYSTEM = (
    "You read one question about Korean immigration status (체류자격) for Waymaker and return ONE JSON object "
    "that matches the given schema. Do not answer the question.\n"
    "- status_code: the 2-segment parent code the question is about (for example E-7), or null.\n"
    "- subcode: the exact code with 3 or more segments only when the question states it (for example E-7-4); "
    "never repeat the parent code here; otherwise null.\n"
    "- procedure: one of {procedures}, or null. Visa-issuance procedures ({visa}) and stay procedures are "
    "different; never put one in place of the other.\n"
    "- current_status / target_status: for a change from one status to another, the status held now and the "
    "status sought; otherwise null.\n"
    "- dates: every calendar date the question states, as YYYY-MM-DD, with role one of {roles}, or null.\n"
    "- needs_clarification: true when a decisive fact (status, procedure or date) is missing or ambiguous."
)

_ABSTENTION_SYSTEM = (
    "You decide whether a reliable conclusion can be given for one question about Korean immigration law "
    "without facts, dates or official sources that are not provided. Return ONE JSON object that matches the "
    "given schema.\n"
    "- conclusion_withheld: true when a conclusion would depend on something missing.\n"
    "- issues: keys of the unresolved issues, chosen from: {issues}.\n"
    "- claims: each statement you would assert, as {{\"text\": ..., \"assertion_key\": ...}}; empty when you "
    "withhold the conclusion."
)


def system_prompt(task: str) -> str:
    if task == "abstention":
        return _ABSTENTION_SYSTEM.format(issues=", ".join(ISSUE_KEYS))
    return _CLASSIFICATION_SYSTEM.format(
        procedures=", ".join(FINE_PROCEDURES),
        visa=", ".join(sorted(VISA_SCOPE_PROCEDURES)),
        roles=", ".join(kind.value for kind in AnchorKind),
    )


def build_messages(example: Mapping[str, Any]) -> List[Dict[str, str]]:
    """Chat messages for one example. Reads only the question and the payload code."""
    user = question_of(example)
    payload = payload_code_of(example)
    if payload:
        user = f"[UI-selected status code: {payload}]\n{user}"
    return [{"role": "system", "content": system_prompt(example["task"])}, {"role": "user", "content": user}]


def build_request(example: Mapping[str, Any], model: str) -> Dict[str, Any]:
    task = example["task"]
    return {
        "model": model,
        "messages": build_messages(example),
        **DECODING,
        "response_format": {
            "type": "json_schema",
            "json_schema": {"name": f"waymaker_{task}", "strict": True, "schema": model_output_schema(task)},
        },
    }


@dataclass(frozen=True)
class ModelReply:
    content: str
    usage: Optional[Dict[str, int]] = None


class ModelCallError(Exception):
    pass


# ---------------------------------------------------------------------------
# Clients
# ---------------------------------------------------------------------------
class MockClient:
    """Deterministic stub: classification answers are all null, abstention always withholds."""

    model = "mock-abstain-v1"

    def complete(self, request: Mapping[str, Any], task: str) -> ModelReply:
        if task == "abstention":
            answer: Dict[str, Any] = {"conclusion_withheld": True, "issues": [], "claims": []}
        else:
            answer = {"status_code": None, "subcode": None, "procedure": None, "current_status": None,
                      "target_status": None, "dates": [], "needs_clarification": True}
        return ModelReply(json.dumps(answer, ensure_ascii=False), None)


Poster = Callable[[str, bytes, float], Tuple[int, bytes]]


def _urllib_post(url: str, body: bytes, timeout: float) -> Tuple[int, bytes]:
    request = urllib.request.Request(url, data=body, method="POST",
                                     headers={"Content-Type": "application/json", "Accept": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310 (loopback only)
            return int(getattr(response, "status", 200) or 200), response.read()
    except urllib.error.HTTPError as exc:
        return int(exc.code or 0), b""
    except (urllib.error.URLError, OSError) as exc:
        raise ModelCallError(f"endpoint unreachable: {type(exc).__name__}") from exc


def loopback_problem(endpoint: str) -> Optional[str]:
    """Why ``endpoint`` may not be used, or None. Only http(s) on a loopback host."""
    try:
        parts = urlsplit(endpoint)
        host = parts.hostname
    except ValueError:
        return "endpoint is not a URL"
    if parts.scheme not in ("http", "https"):
        return "endpoint must be http or https"
    if parts.username or parts.password:
        return "endpoint must not carry credentials"
    if host not in LOOPBACK_HOSTS:
        return "endpoint must be a loopback host (localhost, 127.0.0.1, ::1)"
    return None


class OpenAICompatibleClient:
    """POST ``<endpoint>/chat/completions`` on a local server; reads ``usage`` when present."""

    def __init__(self, endpoint: str, model: str, *, timeout: float = 120.0, post: Optional[Poster] = None) -> None:
        problem = loopback_problem(endpoint)
        if problem:
            raise ValueError(problem)
        self.url = endpoint.rstrip("/") + "/chat/completions"
        self.model = model
        self.timeout = timeout
        self._post = post or _urllib_post

    def complete(self, request: Mapping[str, Any], task: str) -> ModelReply:
        status, body = self._post(self.url, json.dumps(request, ensure_ascii=False).encode("utf-8"), self.timeout)
        if status != 200:
            raise ModelCallError(f"endpoint returned HTTP {status}")
        try:
            data = json.loads(body.decode("utf-8"))
            content = data["choices"][0]["message"]["content"]
        except (ValueError, KeyError, IndexError, TypeError) as exc:
            raise ModelCallError(f"response is not a chat completion: {type(exc).__name__}") from exc
        usage = data.get("usage") if isinstance(data.get("usage"), dict) else None
        tokens = None
        if usage:
            tokens = {key: int(usage[key]) for key in ("prompt_tokens", "completion_tokens", "total_tokens")
                      if isinstance(usage.get(key), int)}
        return ModelReply(str(content or ""), tokens)


# ---------------------------------------------------------------------------
# Baselines
# ---------------------------------------------------------------------------
class ModelBaseline(Baseline):
    kind = "model"
    emits = {
        "status_procedure_classification": frozenset({
            "status_code", "subcode", "procedure_fine", "current_status", "target_status",
            "needs_clarification", "mentioned_codes",
        }),
        "entity_date_extraction": frozenset({"dates", "date_roles", "status_codes"}),
        "abstention": frozenset({"conclusion_withheld", "issues", "claims"}),
    }
    memory_kind = "tracemalloc_peak_client"

    def client(self, ctx: RunContext) -> Any:
        raise NotImplementedError

    def run(self, items: Sequence[EvalItem], ctx: RunContext) -> Dict[str, ItemResult]:
        client = self.client(ctx)
        results: Dict[str, ItemResult] = {}
        for item in items:
            if item.task not in MODEL_TASKS:
                results[item.id] = ItemResult(item.id, "not_applicable")
                continue
            request = build_request(item.example, client.model)
            try:
                reply, latency, peak = measured(lambda: client.complete(request, item.task))
            except ModelCallError as exc:
                results[item.id] = ItemResult(item.id, "error", error=str(exc))
                continue
            prediction, violations = parse_model_output(reply.content, item.task)
            prediction[SCHEMA_VIOLATIONS_KEY] = len(violations)
            results[item.id] = ItemResult(
                item.id, "ok", prediction=prediction,
                raw={"content": reply.content[:MAX_RAW_CHARS], "violations": violations,
                     "prompt_chars": sum(len(m["content"]) for m in request["messages"])},
                latency_ms=latency, upstream_calls=1, tokens=reply.usage, peak_memory_bytes=peak,
                memory_kind=self.memory_kind,
                notes=[f"schema_violation:{v}" for v in violations],
            )
        return results


class MockModel(ModelBaseline):
    name = "mock_model"
    description = ("Deterministic structured-output stub (always abstains / returns nulls) driven through the real "
                   "prompt, JSON-schema and validation path. A floor and a harness check, not a model.")

    def client(self, ctx: RunContext) -> Any:
        return MockClient()


class OpenAICompatible(ModelBaseline):
    name = "openai_compatible"
    description = ("A local OpenAI-compatible endpoint (vLLM / Ollama) with JSON-schema constrained output. "
                   f"Enabled only when {ENDPOINT_ENV} (loopback) and {MODEL_ENV} are set.")

    def __init__(self, environ: Optional[Mapping[str, str]] = None, post: Optional[Poster] = None) -> None:
        self._environ = environ if environ is not None else os.environ
        self._post = post

    def available(self, ctx: RunContext) -> Tuple[bool, str]:
        endpoint = self._environ.get(ENDPOINT_ENV)
        if not endpoint:
            return False, f"{ENDPOINT_ENV} is not set (never set in tests or CI)"
        if not self._environ.get(MODEL_ENV):
            return False, f"{MODEL_ENV} is not set"
        problem = loopback_problem(endpoint)
        return (False, problem) if problem else (True, "")

    def client(self, ctx: RunContext) -> Any:
        try:
            timeout = float(self._environ.get(TIMEOUT_ENV) or 120.0)
        except ValueError:
            timeout = 120.0
        return OpenAICompatibleClient(self._environ[ENDPOINT_ENV], self._environ[MODEL_ENV], timeout=timeout,
                                      post=self._post)

    def describe(self) -> Dict[str, Any]:
        info = super().describe()
        info["model"] = self._environ.get(MODEL_ENV)
        info["decoding"] = dict(DECODING)
        return info
