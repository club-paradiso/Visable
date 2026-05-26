#!/usr/bin/env bash
set -euo pipefail

URL="${1:-https://lucanomics.github.io/Paradiso/}"
TMP_HTML="$(mktemp)"
TMP_HEADERS="$(mktemp)"

cleanup() {
  rm -f "$TMP_HTML" "$TMP_HEADERS"
}
trap cleanup EXIT

echo "INFO: Fetching ${URL}"

if ! HTTP_STATUS="$(curl -L -sS -D "$TMP_HEADERS" -o "$TMP_HTML" -w "%{http_code}" "$URL")"; then
  echo "ERROR: curl failed while fetching ${URL}" >&2
  exit 1
fi

if [[ "$HTTP_STATUS" != "200" ]]; then
  echo "ERROR: expected HTTP 200 from ${URL}, got ${HTTP_STATUS}" >&2
  echo "INFO: response headers:" >&2
  sed -n '1,40p' "$TMP_HEADERS" >&2
  exit 1
fi

check_marker() {
  local marker="$1"
  local label="$2"
  if ! grep -qi -- "$marker" "$TMP_HTML"; then
    echo "ERROR: missing expected HTML marker (${label}): ${marker}" >&2
    exit 1
  fi
}

check_marker "Paradiso" "brand"
check_marker "비자" "visa Korean text"
check_marker "체류" "stay/residence Korean text"

if ! grep -Eqi -- "search|검색" "$TMP_HTML"; then
  echo "ERROR: missing expected search marker: search or 검색" >&2
  exit 1
fi

echo "OK: ${URL} returned HTTP 200 and expected static HTML markers."
