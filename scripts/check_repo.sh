#!/usr/bin/env bash
set -euo pipefail

if ! command -v python3 >/dev/null 2>&1; then
  echo "ERROR: Python 3 is required for repository validation but was not found on PATH." >&2
  exit 1
fi


TEST_PYTHON="python3"

ensure_backend_test_runtime() {
  if python3 - <<'PY' >/dev/null 2>&1
import fastapi  # noqa: F401
import httpx  # noqa: F401
import pydantic  # noqa: F401
PY
  then
    return 0
  fi

  echo "INFO: Backend test dependencies not found in current interpreter. Bootstrapping local .venv-check..."

  if ! python3 -m venv .venv-check; then
    echo "ERROR: Failed to create .venv-check virtual environment." >&2
    exit 1
  fi

  if ! .venv-check/bin/python -m pip install --upgrade pip; then
    echo "ERROR: Failed to upgrade pip in .venv-check." >&2
    exit 1
  fi

  if ! .venv-check/bin/python -m pip install -r backend/requirements.txt; then
    echo "ERROR: Failed to install backend requirements into .venv-check." >&2
    echo "       Try running: .venv-check/bin/python -m pip install -r backend/requirements.txt" >&2
    exit 1
  fi

  TEST_PYTHON=".venv-check/bin/python"
}

echo "[1/12] Validating visa_data.json format..."
python3 -m json.tool visa_data.json > /tmp/visa_data_check.json

echo "[2/12] Scanning visa data for U+FFFD replacement characters..."
python3 scripts/check_visa_text_corruption.py

echo "[3/12] Validating representative manual-aware visa schema..."
python3 - <<'PY'
import json
import sys
import re

with open("visa_data.json", encoding="utf-8") as f:
    visas = json.load(f)
with open("doc_master.json", encoding="utf-8") as f:
    docs = json.load(f)

doc_ids = {d.get("id") for d in docs if isinstance(d, dict)}
records = {v.get("code"): v for v in visas if isinstance(v, dict)}
required = ["C-3", "D-2", "F-6", "K-STAR"]
missing = [code for code in required if code not in records]
if missing:
    raise SystemExit(f"Missing representative manual-aware records: {', '.join(missing)}")

def iter_doc_refs(value):
    if isinstance(value, list):
        for item in value:
            yield item
    elif isinstance(value, dict):
        for item in value.values():
            yield from iter_doc_refs(item)

errors = []
for code in required:
    record = records[code]
    for field in ("manualDomains", "procedures", "sourceManualStatus"):
        if field not in record:
            errors.append(f"{code}: missing {field}")
    status = record.get("sourceManualStatus") or {}
    if status.get("needsManualReview") is not True:
        errors.append(f"{code}: representative record must remain needsManualReview=true")
    procedures = record.get("procedures") or {}
    for proc_name, proc in procedures.items():
        for doc_ref in iter_doc_refs((proc or {}).get("requiredDocs", [])):
            if isinstance(doc_ref, str) and doc_ref.startswith("doc_") and doc_ref not in doc_ids:
                errors.append(f"{code}.{proc_name}: unknown doc_master id {doc_ref}")

status_code_re = re.compile(r"^(?:[A-H]-\d|K-STAR$|REGION-S$)")
for record in visas:
    code = record.get("code")
    if not isinstance(code, str) or not status_code_re.match(code):
        continue
    procedures = record.get("procedures") or {}
    audit = record.get("manualRequiredDocAudit")
    for proc_name in ("extension", "registration"):
        proc = procedures.get(proc_name)
        if not isinstance(proc, dict):
            errors.append(f"{code}: missing procedures.{proc_name}")
            continue
        refs = proc.get("manualRefs")
        docs_group = proc.get("requiredDocs")
        if not isinstance(refs, list) or not refs:
            errors.append(f"{code}.{proc_name}: missing manualRefs")
        if not isinstance(docs_group, dict) or not isinstance(docs_group.get("requiredDocs"), list):
            errors.append(f"{code}.{proc_name}: requiredDocs.requiredDocs must be a list")
    if not isinstance(audit, dict):
        errors.append(f"{code}: missing manualRequiredDocAudit")
    elif audit.get("manualVersion") != "2026.5":
        errors.append(f"{code}: manualRequiredDocAudit.manualVersion must be 2026.5")

if errors:
    raise SystemExit("\\n".join(errors))
PY

echo "[4/12] Validating current source manuals..."
python3 scripts/check_source_manuals.py

echo "[5/12] Running source-monitoring report (local-only)..."
# Report-only. Network entries are skipped. Not flaky: only fails if
# data/source_registry.json itself is malformed.
python3 scripts/check_source_updates.py --local-only > /dev/null

echo "[6/12] Validating manual-grounding candidates (if any)..."
# Passes cleanly when no candidate.json files exist. Only fails if a
# committed candidate file is structurally invalid.
python3 scripts/validate_manual_grounding_candidate.py > /dev/null

echo "[7/12] Validating Paradiso coverage matrix..."
# Structural validation only. The matrix is metadata, not read by
# /api/ask. Fails only if a row claims active_grounded for a fixture
# that does not exist, or otherwise breaks the schema rules in
# scripts/validate_coverage_matrix.py.
python3 scripts/validate_coverage_matrix.py > /dev/null

echo "[8/14] Running git diff --check..."
git diff --check -- index.html ai.html visa_data.json doc_master.json scripts/check_repo.sh scripts/check_source_manuals.py scripts/check_visa_text_corruption.py scripts/check_i18n.js scripts/smoke_ai_payload.js docs/data docs/design docs/source-manuals docs/i18n docs/backend

echo "[9/14] Validating EN/KO UI translations..."
if [[ -f scripts/check_i18n.js ]]; then
  if command -v node >/dev/null 2>&1; then
    node scripts/check_i18n.js
  else
    echo "ERROR: Node.js is required to run scripts/check_i18n.js but was not found on PATH." >&2
    echo "       Install Node.js (>=14) or run via your existing Node toolchain." >&2
    exit 1
  fi
else
  echo "INFO: scripts/check_i18n.js not present; skipping i18n validation."
fi

echo "[10/14] Scanning key user-facing files for forbidden branding strings..."
KEY_FILES=(
  "index.html"
  "ai.html"
  "visa_data.json"
  "moonshot_backend_fastapi.py"
)

FORBIDDEN_REGEX='Moonshot|moonshot|Paradiso 39|PARADISO 39|paradiso 39|Paradiso39|PARADISO39|paradiso39|P/39|p39'

EXISTING_FILES=()
for file in "${KEY_FILES[@]}"; do
  if [[ -f "$file" ]]; then
    EXISTING_FILES+=("$file")
  else
    echo "INFO: Skipping missing optional file: $file"
  fi
done

if [[ ${#EXISTING_FILES[@]} -eq 0 ]]; then
  echo "WARNING: No key files found to scan."
else
  if command -v rg >/dev/null 2>&1; then
    if rg -n -i -e "$FORBIDDEN_REGEX" "${EXISTING_FILES[@]}"; then
      echo "ERROR: Found forbidden branding string(s) in key user-facing files." >&2
      exit 1
    fi
  else
    echo "INFO: ripgrep (rg) not found; using grep fallback."
    if grep -RniE "$FORBIDDEN_REGEX" "${EXISTING_FILES[@]}"; then
      echo "ERROR: Found forbidden branding string(s) in key user-facing files." >&2
      exit 1
    fi
  fi
fi

echo "[11/14] Verifying backend deploy-context visa data file is in sync..."
python3 scripts/sync_visa_data.py --check

echo "[12/14] Checking required-documents rendering coverage..."
python3 scripts/check_required_documents_coverage.py

echo "[13/14] Running backend regression tests..."
ensure_backend_test_runtime
$TEST_PYTHON backend/tests/test_paradiso_backend.py

echo "[14/14] Running Paradiso AI golden eval (non-strict)..."
# Non-strict: known gaps are reported but do not fail the repo check.
# Regression failures (a previously-passing expectation now fails) still
# exit nonzero because the runner returns 0 in non-strict mode only when
# there are zero regression failures.
${TEST_PYTHON} scripts/evaluate_paradiso_ai_golden_questions.py

echo "Success: repository validation passed. JSON is valid, representative manual schema is valid, source manuals are registered, git diff check is clean, and no forbidden branding strings were found in existing key user-facing files."
