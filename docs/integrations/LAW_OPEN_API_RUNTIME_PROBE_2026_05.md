# Law Open API Runtime Probe - 2026.5

## Scope

This probe checks whether Paradiso can access official Korean law text through the National Law Information Open API before any DB field is marked as officially verified.

## Result

- Configured: `False`
- Status: `UNCONFIGURED`
- Matched live law sources: `0`

No live call was made because no API credential was found.

Set one of these environment variables before live probing:
- `LAW_API_OC`
- `LAW_API_KEY`
- `KOREAN_LAW_API_OC`
- `OPEN_LAW_API_OC`

## Laws checked


## Guardrails

- No `visa_data.json` mutation.
- No `verified=true` promotion.
- No legal-content generation.
- No credential stored in repo.

## Next step

Only after this probe returns stable `LIVE_SOURCE_MATCHED` results should a separate verifier PR add field-level `lawVerification` metadata to DB records.

