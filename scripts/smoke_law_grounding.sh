#!/usr/bin/env bash
#
# scripts/smoke_law_grounding.sh
#
# Opt-in law-grounding smoke. Safe in the disabled-by-default mode and also
# usable in audit/enabled mode when env vars are present. It NEVER prints
# secrets (only booleans/markers from the non-secret preflight). CI must not
# depend on a live external law API.
#
# Usage:
#   BACKEND_URL=http://127.0.0.1:8000 bash scripts/smoke_law_grounding.sh
#   bash scripts/smoke_law_grounding.sh --help
set -u

BACKEND_URL="${BACKEND_URL:-http://localhost:8000}"

usage() {
  cat <<'USAGE'
smoke_law_grounding.sh — opt-in law-grounding smoke (no secrets printed)

Environment:
  BACKEND_URL   Target backend (default: http://localhost:8000)

What it does (read-only; no external API dependency required):
  1. GET  /health                         — backend + resolved law_grounding_mode
  2. GET  /api/debug/law-grounding/preflight — non-secret readiness report
  3. POST /api/debug/law-grounding         — per-sample intent + query, for:
       - H-1 seasonal course
       - activity outside status
       - foreigner registration
       - G-1 / refugee
       - re-entry / travel
  4. POST /api/ask                         — end-to-end metadata (may be 503 with
                                              no provider; that is expected)

Modes:
  - disabled (default): verifies non-crash behavior + LAW_GROUNDING_DISABLED.
  - audit/enabled: also reports whether the external law API is reachable.

Flags:
  -h, --help    Show this help and exit.
USAGE
}

case "${1:-}" in
  -h|--help) usage; exit 0 ;;
esac

have_jq=0
if command -v jq >/dev/null 2>&1; then
  have_jq=1
fi

compact_print() {
  local body="$1"
  if [[ $have_jq -eq 1 ]]; then
    printf '%s' "$body" | jq -c . 2>/dev/null || printf '%s\n' "$body"
  else
    printf '%s\n' "$body"
  fi
}

# Extract a JSON value by key (recursive, best-effort, no secrets). Uses
# python3 (already required by the repo's validation commands). The body is
# piped on stdin; the program is passed via -c so stdin stays the JSON body.
field() {
  local body="$1" key="$2"
  printf '%s' "$body" | python3 -c '
import json, sys
key = sys.argv[1]
try:
    data = json.load(sys.stdin)
except Exception:
    print(""); sys.exit(0)
def find(o):
    if isinstance(o, dict):
        if key in o:
            return o[key]
        for v in o.values():
            r = find(v)
            if r is not None:
                return r
    elif isinstance(o, list):
        for v in o:
            r = find(v)
            if r is not None:
                return r
    return None
v = find(data)
print("" if v is None else v)
' "$key" 2>/dev/null || true
}

call() {
  local method="$1"
  local path="$2"
  local data="${3:-}"
  local url="${BACKEND_URL}${path}"
  local tmp code body
  tmp="$(mktemp)"
  if [[ -n "$data" ]]; then
    code="$(curl -sS -o "$tmp" -w '%{http_code}' -X "$method" "$url" -H 'content-type: application/json' -d "$data" || echo '000')"
  else
    code="$(curl -sS -o "$tmp" -w '%{http_code}' -X "$method" "$url" || echo '000')"
  fi
  body="$(cat "$tmp")"; rm -f "$tmp"
  echo "[$method $path] status=$code"
  compact_print "$body"
  echo
  LAST_BODY="$body"
}

echo "Running law-grounding smoke checks against: $BACKEND_URL"
echo "(opt-in script; no secrets printed)"
echo

call GET /health
echo "Resolved law_grounding_mode: $(field "$LAST_BODY" law_grounding_mode || echo unknown)"
echo

call GET /api/debug/law-grounding/preflight
echo "Preflight mode=$(field "$LAST_BODY" mode), external_calls=$(field "$LAST_BODY" external_calls), key_configured=$(field "$LAST_BODY" law_api_key_configured), endpoint_configured=$(field "$LAST_BODY" law_api_endpoint_configured), ready=$(field "$LAST_BODY" ready_for_external_calls)"
if printf '%s' "$LAST_BODY" | grep -q 'LAW_GROUNDING_DISABLED'; then
  echo "NOTE: LAW_GROUNDING_DISABLED (expected-safe default)."
fi
if printf '%s' "$LAST_BODY" | grep -q 'LAW_GROUNDING_AUDIT_ONLY'; then
  echo "NOTE: LAW_GROUNDING_AUDIT_ONLY (audit mode; no user-facing legal claims)."
fi
echo

# Sample questions that SHOULD trigger law-grounding intent.
SAMPLES=(
  'H-1 비자인데 한국 대학에서 계절학기를 수강할 수 있을까요?'
  '지금 체류자격으로 체류자격외활동(아르바이트)이 가능한가요?'
  'E-7로 입국했는데 외국인등록 전 고용계약이 해지되면 어떻게 되나요?'
  'G-1-5 비자로 제주에 입국한지 2달차인데, 일본을 갈 수 있나요?'
  '재입국허가 없이 출국했다가 다시 들어올 수 있나요?'
)
for q in "${SAMPLES[@]}"; do
  call POST /api/debug/law-grounding "{\"question\":$(printf '%s' "$q" | python3 -c 'import json,sys;print(json.dumps(sys.stdin.read()))')}"
  echo "  -> sample_would_trigger=$(field "$LAST_BODY" sample_would_trigger), attempted=$(field "$LAST_BODY" attempted)"
  echo
done

call POST /api/ask '{"question":"H-1 비자인데 한국 대학에서 계절학기를 수강할 수 있을까요?"}'
echo "  -> law_grounding_status=$(field "$LAST_BODY" law_grounding_status)"

echo
echo "Done. (No secrets were printed. External law-API calls only happen in audit/enabled mode with keys.)"
