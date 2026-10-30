#!/bin/zsh
# Re-measure the six real-manual sets on label v2 with each set's original settings.
# One set at a time, each into a new run folder; waits for free disk before each set.
set -u
cd "$(dirname "$0")/../.." || exit 2
export HF_HOME=$HOME/.cache/waymaker-artemis/hf HF_HUB_OFFLINE=1
LOG=${TMPDIR:-/tmp}/artemis-v2runs
mkdir -p $LOG
free_gb() { python3 -I -c "print(round(__import__('shutil').disk_usage('$HOME').free/1e9,2))"; }
run() {
  local set=$1 suffix=$2; shift 2
  local out=runs/2026-10-28-e4b-it-4bit-m1-8gb-v2-$suffix-${RUN_SUFFIX:-r2}
  status() { python3 -I -c "import json;print(json.load(open('$out/run_record.json')).get('status'))" 2>/dev/null; }
  if [[ -e $out ]]; then
    [[ $(status) == completed ]] && { echo "$set: $out already completed, skipping"; return 0; }
    echo "$set: $out exists but is not completed, stopping"; exit 3
  fi
  for i in {1..15}; do
    [[ $(python3 -c "print(1 if $(free_gb) >= 5.0 else 0)") == 1 ]] && break
    echo "$(date +%T) $set: waiting for 5 GB free (now $(free_gb) GB)"; sleep 60
  done
  echo "$(date +%T) START $set -> $out (free $(free_gb) GB, $(sysctl -n vm.swapusage))"
  .venv/bin/python run_smoke.py --profile gemma4_e4b --runtime mlx_vlm --out $out \
    --cases label_v2/${set}_cases.v2.json --min-free-disk-gb 5 "$@" > $LOG/$set.log 2>&1
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
run manual_always_ask always-ask --source-gate --integrity --always-ask
run manual_misclick misclick-label --source-gate --integrity --always-ask --label-switch
echo "$(date +%T) ALL DONE"
