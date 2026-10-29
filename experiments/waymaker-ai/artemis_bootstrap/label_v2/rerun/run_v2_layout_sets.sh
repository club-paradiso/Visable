#!/bin/zsh
# Re-measure the six real-manual sets on label v2 with the 2026-10-28 fixes: --layout
# (HWP text with tables kept), --facts, the route cues in procedure_route.py, and the
# cross-check on the always-ask and mis-click sets. Waits for the charger (or >= 50% battery) before each set.
# One set at a time, each into a new run folder; waits for free disk before each set.
set -u
cd "$(dirname "$0")/../.." || exit 2
export HF_HOME=$HOME/.cache/waymaker-artemis/hf HF_HUB_OFFLINE=1
MODEL=mlx-community/gemma-4-e4b-it-4bit
REV=475b9088d29754a3379866cf5aeb6b41acd313c2
LOG=${TMPDIR:-/tmp}/artemis-v2-layout-runs
mkdir -p $LOG
free_gb() { python3 -I -c "print(round(__import__('shutil').disk_usage('$HOME').free/1e9,2))"; }
run() {
  local set=$1 suffix=$2; shift 2
  local out=runs/2026-10-28-e4b-it-4bit-m1-8gb-v2-$suffix-${RUN_SUFFIX:-layout}
  status() { python3 -I -c "import json;print(json.load(open('$out/run_record.json')).get('status'))" 2>/dev/null; }
  if [[ -e $out ]]; then
    [[ $(status) == completed ]] && { echo "$set: $out already completed, skipping"; return 0; }
    echo "$set: $out exists but is not completed, stopping"; exit 3
  fi
  for i in {1..15}; do
    [[ $(python3 -c "print(1 if $(free_gb) >= 5.0 else 0)") == 1 ]] && break
    echo "$(date +%T) $set: waiting for 5 GB free (now $(free_gb) GB)"; sleep 60
  done
  for i in {1..120}; do
    pmset -g batt | head -1 | grep -q "AC Power" && break
    [[ $(pmset -g batt | grep -oE "[0-9]+%" | tr -d %) -ge 50 ]] && break
    echo "$(date +%T) $set: waiting for the charger (battery $(pmset -g batt | grep -oE "[0-9]+%"))"; sleep 60
  done
  echo "$(date +%T) START $set -> $out (free $(free_gb) GB, $(sysctl -n vm.swapusage))"
  .venv/bin/python run_smoke.py --model $MODEL --revision $REV --out $out \
    --cases label_v2/${set}_cases.v2.json --min-free-disk-gb 5 --layout --facts "$@" > $LOG/$set.log 2>&1
  local rc=$?
  echo "$(date +%T) END $set rc=$rc (free $(free_gb) GB)"
  tail -3 $LOG/$set.log
  # run_smoke exits 1 when any case fails; only a record that is not "completed" stops the batch.
  [[ $(status) == completed ]] || { echo "stopping after $set (rc=$rc, status $(status))"; exit 4; }
}
run manual_oracle oracle --source-gate --integrity
run manual_routing routing-routed --source-gate --integrity --route
run manual_clarify clarify-route-clarify --source-gate --integrity --route --clarify
run manual_buttons buttons-buttons --source-gate --integrity --route --clarify
run manual_always_ask always-ask --source-gate --integrity --always-ask --cross-check
run manual_misclick misclick-label --source-gate --integrity --always-ask --label-switch --cross-check
echo "$(date +%T) ALL DONE"
