#!/usr/bin/env python3
"""Offline architecture guard for Visable's AI layer.

Runs with no network, no provider credentials and no LLM calls, so it belongs
in ordinary PR CI. It asserts the structural invariants that, once broken,
produce the failure modes this codebase has already lived through:

  1. Provider fragmentation. Every feature that grew its own provider routing
     also grew its own idea of retries, timeouts and fallback. That is how one
     endpoint kept answering from an ungoverned model long after the
     deployment switched to strict OpenRouter-first.

  2. Scattered model identifiers. A model string hardcoded outside the policy
     module is a model nobody updates when the catalog changes.

  3. Scattered credential reads. A credential read outside the approved
     adapters is a credential the readiness endpoint cannot see and the
     operator cannot audit.

  4. Result-contract misuse. Unpacking the completion result as a tuple raised
     ValueError that a broad `except` swallowed into a permanent fake outage.
     Two production endpoints shipped that way.

  5. Secrets in source. A committed key is a rotated key.

  6. Frontend-to-provider calls. The browser must never hold a provider key.

Usage:
    python3 scripts/check_ai_architecture.py
    python3 scripts/check_ai_architecture.py --json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Dict, List

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND = REPO_ROOT / "backend"

# ---------------------------------------------------------------------------
# Allowlists
# ---------------------------------------------------------------------------

#: The only modules permitted to name a provider host. Everything else must go
#: through the shared runtime. Adding a file here is a deliberate architectural
#: decision and should be reviewed as one.
PROVIDER_HOST_ALLOWLIST = {
    "backend/paradiso_backend.py",          # owns the OpenRouter/Groq/Ollama transports
    "backend/services/providers/nvidia_nim.py",  # experimental, fail-closed, not wired
    "backend/services/ai_runtime.py",       # taxonomy + orchestration (no HTTP of its own)
}

#: Modules permitted to read a provider credential from the environment.
CREDENTIAL_READ_ALLOWLIST = {
    "backend/paradiso_backend.py",
    "backend/services/providers/nvidia_nim.py",
    "backend/services/ai_runtime.py",
}

#: Modules permitted to define model identifiers.
MODEL_ID_ALLOWLIST = {
    "backend/services/model_policy.py",
    "backend/services/ai_runtime.py",
    "backend/services/providers/nvidia_nim.py",
}

PROVIDER_HOSTS = [
    "openrouter.ai",
    "api.groq.com",
    "integrate.api.nvidia.com",
    "api.openai.com",
    "api.anthropic.com",
    "generativelanguage.googleapis.com",
]

CREDENTIAL_ENV_NAMES = [
    "OPENROUTER_API_KEY",
    "GROQ_API_KEY",
    "NVIDIA_API_KEY",
    "ANTHROPIC_API_KEY",
    "OPENAI_API_KEY",
]

#: Committed-secret shapes. Deliberately narrow so a documented variable NAME
#: never trips it — only something that looks like an actual value.
SECRET_VALUE_PATTERNS = [
    (re.compile(r"sk-or-v1-[A-Za-z0-9_-]{16,}"), "OpenRouter API key"),
    (re.compile(r"\bgsk_[A-Za-z0-9]{20,}"), "Groq API key"),
    (re.compile(r"\bnvapi-[A-Za-z0-9_-]{16,}"), "NVIDIA API key"),
    (re.compile(r"\bsk-ant-[A-Za-z0-9_-]{16,}"), "Anthropic API key"),
    (re.compile(r"\bsk-proj-[A-Za-z0-9_-]{16,}"), "OpenAI project key"),
]

#: A model id looks like "vendor/model" or "vendor/model:tag".
MODEL_ID_RE = re.compile(r"[\"'][a-z0-9][a-z0-9._-]*/[a-z0-9][a-z0-9._:-]+[\"']")

#: Vendor prefixes that indicate a real catalog model rather than an arbitrary
#: path-shaped string.
MODEL_VENDOR_PREFIXES = (
    "openai/", "google/", "meta-llama/", "nousresearch/", "deepseek/", "qwen/",
    "moonshotai/", "mistralai/", "anthropic/", "nvidia/", "z-ai/", "microsoft/",
    "cohere/", "perplexity/", "x-ai/",
)

#: Random-routing ids: unauditable model selection for legal answers.
RANDOM_ROUTING_IDS = {"openrouter/auto", "openrouter/free", "auto", "free"}


class Finding:
    def __init__(self, rule: str, path: str, line: int, detail: str):
        self.rule, self.path, self.line, self.detail = rule, path, line, detail

    def as_dict(self) -> Dict[str, object]:
        return {"rule": self.rule, "path": self.path, "line": self.line, "detail": self.detail}

    def __str__(self) -> str:
        return f"[{self.rule}] {self.path}:{self.line}\n      {self.detail}"


def rel(path: Path) -> str:
    return str(path.relative_to(REPO_ROOT)).replace("\\", "/")


def python_sources() -> List[Path]:
    return [
        p for p in BACKEND.rglob("*.py")
        if "__pycache__" not in p.parts and "/tests/" not in rel(p) and p.parent.name != "tests"
    ]


def frontend_sources() -> List[Path]:
    files = list(REPO_ROOT.glob("*.html"))
    js = REPO_ROOT / "assets" / "js"
    if js.exists():
        files += [p for p in js.rglob("*.js")]
    return files


def strip_comment(line: str) -> str:
    """Drop trailing `#` comments so prose about a host is not a violation."""
    stripped = line.lstrip()
    if stripped.startswith("#"):
        return ""
    return line.split("#", 1)[0] if "#" in line else line


# ---------------------------------------------------------------------------
# Rules
# ---------------------------------------------------------------------------


def check_provider_hosts(findings: List[Finding]) -> None:
    """Rule 1 — only the approved adapters may name a provider host."""
    for path in python_sources():
        relpath = rel(path)
        if relpath in PROVIDER_HOST_ALLOWLIST:
            continue
        for num, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            code = strip_comment(line)
            for host in PROVIDER_HOSTS:
                if host in code:
                    findings.append(Finding(
                        "provider-host-outside-adapter", relpath, num,
                        f"names provider host {host!r}. Route the call through "
                        f"services.ai_runtime instead, or add this module to "
                        f"PROVIDER_HOST_ALLOWLIST as a reviewed decision.",
                    ))


def check_credential_reads(findings: List[Finding]) -> None:
    """Rule 3 — credentials are read in one place the operator can audit."""
    for path in python_sources():
        relpath = rel(path)
        if relpath in CREDENTIAL_READ_ALLOWLIST:
            continue
        text = path.read_text(encoding="utf-8")
        for num, line in enumerate(text.splitlines(), 1):
            code = strip_comment(line)
            if "environ" not in code and "getenv" not in code:
                continue
            for name in CREDENTIAL_ENV_NAMES:
                if name in code:
                    findings.append(Finding(
                        "credential-read-outside-runtime", relpath, num,
                        f"reads {name} directly. Provider configuration belongs to "
                        f"services.ai_runtime so readiness reporting stays accurate.",
                    ))


def check_model_identifiers(findings: List[Finding]) -> None:
    """Rule 2 — model ids live in the policy module, not scattered in features."""
    for path in python_sources():
        relpath = rel(path)
        if relpath in MODEL_ID_ALLOWLIST:
            continue
        for num, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            code = strip_comment(line)
            for match in MODEL_ID_RE.finditer(code):
                value = match.group(0).strip("\"'").lower()
                if value.startswith(MODEL_VENDOR_PREFIXES):
                    findings.append(Finding(
                        "model-id-outside-policy", relpath, num,
                        f"hardcodes model id {value!r}. Ask for a TaskRole and let "
                        f"services.model_policy resolve the chain, so a catalog "
                        f"change is one edit rather than a search.",
                    ))


#: A line that DEFINES the denylist naturally contains the very ids it forbids.
#: Flagging it would punish the code doing the right thing, so recognise the
#: declaration and skip it.
_DENYLIST_DECLARATION_RE = re.compile(
    r"RANDOM_ROUTING|FORBIDDEN_MODEL|DISALLOWED_MODEL|BANNED_MODEL", re.IGNORECASE
)


def check_random_routing(findings: List[Finding]) -> None:
    """Model selection for legal answers must stay auditable."""
    for path in python_sources():
        relpath = rel(path)
        for num, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            code = strip_comment(line)
            if _DENYLIST_DECLARATION_RE.search(code):
                continue
            for match in MODEL_ID_RE.finditer(code):
                value = match.group(0).strip("\"'").lower()
                if value in RANDOM_ROUTING_IDS or value.endswith("/auto"):
                    findings.append(Finding(
                        "random-model-routing", relpath, num,
                        f"selects {value!r}. Random routing makes the answering model "
                        f"unauditable, which is not acceptable for immigration answers.",
                    ))


def check_result_contract_misuse(findings: List[Finding]) -> None:
    """Rule 4 — the exact defect that broke two endpoints for their whole life.

    `a, b = await _openrouter_complete_with_candidates(...)` unpacks a mapping
    to its KEYS and raises ValueError, which a broad `except` turns into a
    permanent fake outage. Nothing about that failure looks like a bug at
    runtime, so it has to be caught statically.
    """
    pattern = re.compile(
        r"^\s*[A-Za-z_][\w]*\s*,\s*[A-Za-z_][\w]*\s*=\s*await\s+"
        r"[\w.]*(?:_openrouter_complete_with_candidates|complete_with_candidates)\b"
    )
    for path in python_sources():
        for num, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if pattern.match(line):
                findings.append(Finding(
                    "completion-result-unpacked-as-tuple", rel(path), num,
                    "unpacks the completion result as a tuple. It is a mapping: this "
                    "raises ValueError on EVERY call, and a broad `except` reports it "
                    "as a provider outage. Read the documented keys instead.",
                ))


def check_committed_secrets(findings: List[Finding]) -> None:
    """Rule 5 — a committed key is a rotated key."""
    targets = python_sources() + frontend_sources()
    for extra in ("backend/.env.example", "docs", "scripts"):
        target = REPO_ROOT / extra
        if target.is_dir():
            targets += [p for p in target.rglob("*") if p.suffix in {".md", ".py", ".mjs", ".js", ".sh"}]
        elif target.exists():
            targets.append(target)

    for path in dict.fromkeys(targets):
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for num, line in enumerate(text.splitlines(), 1):
            for pattern, label in SECRET_VALUE_PATTERNS:
                if pattern.search(line):
                    findings.append(Finding(
                        "committed-secret", rel(path), num,
                        f"looks like a committed {label}. Rotate it and move the value "
                        f"into deploy configuration; only variable NAMES belong in git.",
                    ))


def check_frontend_provider_calls(findings: List[Finding]) -> None:
    """Rule 6 — the browser must never hold a provider key."""
    for path in frontend_sources():
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for num, line in enumerate(text.splitlines(), 1):
            for host in PROVIDER_HOSTS:
                if host in line:
                    findings.append(Finding(
                        "frontend-calls-provider-directly", rel(path), num,
                        f"references provider host {host!r}. A browser call needs a key "
                        f"in the browser. Every AI call must go through a Visable "
                        f"backend endpoint.",
                    ))


def check_ai_consumers_use_shared_runtime(findings: List[Finding]) -> None:
    """Rule 1b — the backend must actually import the shared runtime.

    A weak but load-bearing check: if paradiso_backend stops importing
    ai_runtime, the taxonomy and cooldown have been forked again.
    """
    backend_file = BACKEND / "paradiso_backend.py"
    text = backend_file.read_text(encoding="utf-8")
    if "ai_runtime" not in text:
        findings.append(Finding(
            "shared-runtime-not-used", rel(backend_file), 1,
            "no longer imports services.ai_runtime. Provider semantics have been "
            "forked back out of the shared runtime.",
        ))
    for symbol in ("classify_provider_error", "ModelCooldownRegistry"):
        if symbol not in text:
            findings.append(Finding(
                "shared-runtime-not-used", rel(backend_file), 1,
                f"does not use ai_runtime.{symbol}; the shared behaviour has been "
                f"reimplemented locally.",
            ))


RULES = (
    check_provider_hosts,
    check_credential_reads,
    check_model_identifiers,
    check_random_routing,
    check_result_contract_misuse,
    check_committed_secrets,
    check_frontend_provider_calls,
    check_ai_consumers_use_shared_runtime,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    findings: List[Finding] = []
    for rule in RULES:
        rule(findings)

    if args.json:
        print(json.dumps({
            "ok": not findings,
            "findings": [f.as_dict() for f in findings],
            "rules_run": [r.__name__ for r in RULES],
        }, ensure_ascii=False, indent=2))
        return 1 if findings else 0

    print(f"AI architecture guard — {len(RULES)} rules, offline, no credentials")
    print("=" * 64)
    if not findings:
        print("OK — no architecture violations.")
        print("  * provider hosts confined to approved adapters")
        print("  * credentials read in one auditable place")
        print("  * model ids governed by services.model_policy")
        print("  * no random model routing")
        print("  * completion result never unpacked as a tuple")
        print("  * no committed secrets")
        print("  * no frontend-to-provider calls")
        return 0

    by_rule: Dict[str, List[Finding]] = {}
    for finding in findings:
        by_rule.setdefault(finding.rule, []).append(finding)
    for rule, items in sorted(by_rule.items()):
        print(f"\n{rule} ({len(items)}):")
        for item in items:
            print(f"  {item}")
    print(f"\nFAILED — {len(findings)} violation(s).")
    return 1


if __name__ == "__main__":
    sys.exit(main())
