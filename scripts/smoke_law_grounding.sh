#!/usr/bin/env bash
set -u

BACKEND_URL="${BACKEND_URL:-http://localhost:8000}"

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

call_json() {
  local method="$1"
  local path="$2"
  local data="${3:-}"
  local url="${BACKEND_URL}${path}"

  local tmp
  tmp="$(mktemp)"
  local code

  if [[ -n "$data" ]]; then
    code="$(curl -sS -o "$tmp" -w '%{http_code}' -X "$method" "$url" -H 'content-type: application/json' -d "$data" || echo '000')"
  else
    code="$(curl -sS -o "$tmp" -w '%{http_code}' -X "$method" "$url" || echo '000')"
  fi

  local body
  body="$(cat "$tmp")"
  rm -f "$tmp"

  echo "[$method $path] status=$code"
  compact_print "$body"
  echo

  if [[ "$path" == "/api/debug/law-grounding" ]]; then
    if printf '%s' "$body" | rg -q 'LAW_GROUNDING_DISABLED'; then
      echo "WARNING: LAW_GROUNDING_MODE appears disabled (expected-safe default)."
      echo
    fi
  fi
}

echo "Running law-grounding smoke checks against: $BACKEND_URL"
echo "(opt-in script; no secrets printed)"
echo

call_json GET /health
call_json POST /api/debug/law-grounding '{"question":"출입국관리법 제10조"}'
call_json POST /api/ask '{"question":"출입국관리법 제10조 근거를 알려줘"}'

echo "Done."
