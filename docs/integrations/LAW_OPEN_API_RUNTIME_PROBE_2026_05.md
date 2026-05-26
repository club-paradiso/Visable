# Law Open API Runtime Probe - 2026.5

## Scope

This probe checks whether Paradiso can access official Korean law text through the National Law Information Open API before any DB field is marked as officially verified.

## Result

- Configured: `True`
- Status: `PROBED`
- Matched live law sources: `0`

## Laws checked

- `출입국관리법`: `SEARCH_RETURNED_NO_CANDIDATE`
- `출입국관리법 시행령`: `SEARCH_RETURNED_NO_CANDIDATE`
- `출입국관리법 시행규칙`: `SEARCH_RETURNED_NO_CANDIDATE`
- `국적법`: `SEARCH_RETURNED_NO_CANDIDATE`
- `국적법 시행령`: `SEARCH_RETURNED_NO_CANDIDATE`
- `국적법 시행규칙`: `SEARCH_RETURNED_NO_CANDIDATE`
- `난민법`: `SEARCH_RETURNED_NO_CANDIDATE`
- `난민법 시행령`: `SEARCH_RETURNED_NO_CANDIDATE`
- `난민법 시행규칙`: `SEARCH_RETURNED_NO_CANDIDATE`
- `재외동포의 출입국과 법적 지위에 관한 법률`: `SEARCH_RETURNED_NO_CANDIDATE`
- `재외동포의 출입국과 법적 지위에 관한 법률 시행령`: `SEARCH_RETURNED_NO_CANDIDATE`
- `재외동포의 출입국과 법적 지위에 관한 법률 시행규칙`: `SEARCH_RETURNED_NO_CANDIDATE`
- `재한외국인 처우 기본법`: `SEARCH_RETURNED_NO_CANDIDATE`
- `재한외국인 처우 기본법 시행령`: `SEARCH_RETURNED_NO_CANDIDATE`

## Guardrails

- No `visa_data.json` mutation.
- No `verified=true` promotion.
- No legal-content generation.
- No credential stored in repo.

## Next step

Only after this probe returns stable `LIVE_SOURCE_MATCHED` results should a separate verifier PR add field-level `lawVerification` metadata to DB records.

