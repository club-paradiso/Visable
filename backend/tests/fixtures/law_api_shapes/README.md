# Open Law API response-shape fixtures

These are **synthetic, sanitized** sample bodies that mirror the shapes the
National Law Information Open API (`open.law.go.kr` DRF endpoints) returns. They
contain **no OC / API-key values and no real response bodies** — they exist only
so the parser/normalizer taxonomy can be asserted deterministically and offline
(`backend/tests/test_law_api_shape_fixtures.py`).

Each `<name>.txt` file is a raw body; the expected parse outcome is encoded in
`expected.json` (`error_type`, `parser_status`, `response_shape_hint`).

To refresh real shape **metadata** (never raw bodies, never secrets) against the
live API, an operator can run, for example:

```
python3 scripts/capture_law_api_shape.py --family statute --query "출입국관리법 외국인등록"
python3 scripts/capture_law_api_shape.py --family enforcement_decree --query "출입국관리법 시행령 외국인등록 체류자격"
python3 scripts/capture_law_api_shape.py --family enforcement_rule --query "출입국관리법 시행규칙 외국인등록"
python3 scripts/capture_law_api_shape.py --family administrative_rule --query "E-7 근무처 변경 추가 신고"
python3 scripts/capture_law_api_shape.py --family legal_term --query "체류자격외활동"
python3 scripts/capture_law_api_shape.py --family statute --query "F-2-99 거주 취업활동"
python3 scripts/capture_law_api_shape.py --family statute --query "G-1 체류자격 활동범위"
```

The capture helper prints sanitized metadata only (shape hint, parser status,
root keys/error code), never the raw body or any credential.
