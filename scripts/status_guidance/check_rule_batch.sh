#!/usr/bin/env bash
# Validate one rule batch (scripts/status_guidance/rules/<file>.py) in isolation:
#   1. author the rules with only that batch loaded, into a scratch folder;
#   2. run the real coverage build on them (every anchor must be found in the manual, or it fails);
#   3. walk the resulting bundle through the resolver (grid audit) and list the batch's cells.
# Usage: scripts/status_guidance/check_rule_batch.sh <batch.py> <scratch-dir> [code-prefix ...]
set -euo pipefail
batch="$1"; dir="$2"; shift 2
root="$(cd "$(dirname "$0")/../.." && pwd)"
mkdir -p "$dir"
RULE_BATCH_ONLY="$batch" python3 "$root/scripts/status_guidance/author_rules.py" --out "$dir/rules.json"
python3 "$root/scripts/build_status_coverage_manifest.py" --rules "$dir/rules.json" --out-dir "$dir" > "$dir/build.log"
node "$root/scripts/audit_status_procedure_grid.mjs" --bundle "$dir/status-guidance-202609.json" --csv "$dir" | head -6
if [ "$#" -gt 0 ]; then
  pat="$(printf '^%s|' "$@")"; pat="${pat%|}"
  echo "cells for: $*"
  cut -d, -f1,7,11 "$dir/inventory.csv" | grep -E "$pat" | sed 's/^/  /'
fi
