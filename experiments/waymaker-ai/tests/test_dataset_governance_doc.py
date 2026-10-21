"""The rules table in docs/ai/waymaker-genesis/11-dataset-governance.md matches the validator.

The validator's docstring promises that every rule id it reports is listed,
with its severity, in the governance document. This test reads the rule ids
and severities out of the validator's source (every ``out.error("rule", …)``,
``out.warning(…)``, ``file_issue(SEVERITY, "rule", …)``, ``Issue(SEVERITY,
"rule", …)`` and contamination pair report) and compares them with §5.2, so a
new rule cannot ship undocumented and a documented rule cannot silently go.
"""
from __future__ import annotations

import ast
from pathlib import Path
from typing import Dict, Set

from waymaker_ai.dataset import validate

REPO_ROOT = Path(__file__).resolve().parents[3]
GOVERNANCE_DOC = REPO_ROOT / "docs" / "ai" / "waymaker-genesis" / "11-dataset-governance.md"
SEVERITY_LETTERS = {"error": "E", "warning": "W"}


def _call_name(node: ast.Call) -> str:
    if isinstance(node.func, ast.Attribute):
        return node.func.attr
    if isinstance(node.func, ast.Name):
        return node.func.id
    return ""


def _is_rule_id(node: ast.expr) -> bool:
    return isinstance(node, ast.Constant) and isinstance(node.value, str)


def _is_severity(node: ast.expr) -> bool:
    return isinstance(node, ast.Name) and node.id in ("ERROR", "WARNING")


def rules_in_code() -> Dict[str, Set[str]]:
    """(rule id -> severity letters) for every call that names a literal rule id.

    Calls that only forward a rule variable (``Findings._add``, ``file_issue``'s
    own body) are skipped: the literal is at their call sites.
    """
    tree = ast.parse(Path(validate.__file__).read_text(encoding="utf-8"))
    rules: Dict[str, Set[str]] = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        name, args = _call_name(node), node.args
        if name in ("error", "warning") and args and _is_rule_id(args[0]):
            rules.setdefault(args[0].value, set()).add(SEVERITY_LETTERS[name])
        elif name in ("file_issue", "Issue") and len(args) >= 2 and _is_severity(args[0]) and _is_rule_id(args[1]):
            rules.setdefault(args[1].value, set()).add(SEVERITY_LETTERS[args[0].id.lower()])
        elif name == "_report_pairs" and len(args) >= 4 and _is_severity(args[2]) and _is_rule_id(args[3]):
            rules.setdefault(args[3].value, set()).add(SEVERITY_LETTERS[args[2].id.lower()])
    return rules


def rules_in_doc() -> Dict[str, Set[str]]:
    text = GOVERNANCE_DOC.read_text(encoding="utf-8")
    section = text.split("### 5.2 Rules", 1)[1].split("\n### ", 1)[0]
    rules: Dict[str, Set[str]] = {}
    for line in section.splitlines():
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) < 2 or not (cells[0].startswith("`") and cells[0].endswith("`")):
            continue
        rules[cells[0].strip("`")] = set(cells[1].split("/"))
    return rules


def test_every_rule_the_validator_reports_is_documented_with_its_severity():
    in_code, in_doc = rules_in_code(), rules_in_doc()
    assert len(in_code) >= 25, sorted(in_code)   # the scan itself found the rules
    assert sorted(set(in_code) - set(in_doc)) == [], "rules missing from 11-dataset-governance.md §5.2"
    assert sorted(set(in_doc) - set(in_code)) == [], "documented rules the validator never reports"
    mismatched = {rule: (sorted(in_code[rule]), sorted(in_doc[rule])) for rule in in_code if in_code[rule] != in_doc[rule]}
    assert mismatched == {}, "severity in code vs doc"
