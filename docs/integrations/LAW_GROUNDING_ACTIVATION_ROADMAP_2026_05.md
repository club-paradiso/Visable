# LAW GROUNDING ACTIVATION ROADMAP (2026-05)

Date (UTC): 2026-05-26  
Scope: Staged activation plan only; production enablement is out of scope.

## Architecture summary
Current backend law-grounding flow is integrated through:
- `backend/services/grounding_config.py` (env parsing, mode/defaults)
- `backend/services/law_grounding.py` (intent gating + orchestration)
- `backend/services/korean_law_client.py` (API client wrapper)
- `backend/paradiso_backend.py` (`/api/ask`, `/api/debug/law-grounding`, health flags)

Law grounding is intent-triggered for legal-basis-like queries and mode-gated before any API call attempt.

## Current mode and implementation state
- Current default mode: `LAW_GROUNDING_MODE=disabled`.
- Supported modes in config parser: `disabled`, `audit`, `enabled`.
- Implementation status: **partially implemented** (client + orchestration + debug path exist; production rollout gates not complete).
- Safe default status: **safe** (disabled by default unless explicitly configured).

## Environment variables (no secret exposure)
Required/related variables:
- `LAW_GROUNDING_MODE`
- `LAW_API_KEY`
- `LAW_API_BASE_URL`
- `LAW_API_SEARCH_PATH`
- `LAW_API_ARTICLE_PATH`
- `LAW_GROUNDING_TIMEOUT_SECONDS`
- `LAW_GROUNDING_CACHE_TTL_SECONDS`
- (provider context for ask pipeline) `OPENROUTER_API_KEY` or `GROQ_API_KEY`

Optional adjacent variables:
- `PUBLIC_DATA_API_KEY`
- `PUBLIC_DATA_BASE_URL` / path vars

## Source authority rules
1. Official stay/visa manuals are operational authority for required-document guidance.
2. Korean statutes/regulations are legal authority and high-level statutory basis.
3. Official HiKorea/MOJ/KIS pages are supplementary references.
4. Repository JSON is implementation output target, not primary legal authority.

## Activation stages
- **Stage 0 (current)**: Disabled mode (`LAW_GROUNDING_MODE=disabled`), no live law API dependency.
- **Stage 1**: Audit/debug endpoint verification only (`/api/debug/law-grounding`), non-user-facing validation.
- **Stage 2**: Internal smoke with official API response-shape validation and warning behavior checks.
- **Stage 3**: Limited backend grounding for source classification only (no authoritative citation claims in user answer unless verified).
- **Stage 4**: Opt-in AI grounding with explicit source warnings and failure markers.
- **Stage 5**: Production enablement only after test suite, observability, rollback, and config review sign-off.

## Failure modes and fallback behavior
Failure modes to handle explicitly:
- missing API key
- missing/invalid API base/path
- timeout/upstream HTTP errors
- parse errors
- unverifiable or mismatched citations

Fallback policy:
- Never fabricate law citations.
- Return warning markers (`LAW_GROUNDING_DISABLED`, `SOURCE_UNAVAILABLE`, etc.).
- Continue with non-law/manual-safe guidance when law source is unavailable.
- Do not silently pretend grounding succeeded.

## Test commands
- `bash scripts/smoke_law_grounding.sh` (optional; safe in disabled mode)
- `python3 -m pytest backend/tests/test_paradiso_backend.py -q` (if dependencies available)
- `curl -sS "$BACKEND_URL/health"`
- `curl -sS -X POST "$BACKEND_URL/api/debug/law-grounding" -H 'content-type: application/json' -d '{"question":"출입국관리법 제10조"}'`

## Rollback plan
If higher stages fail:
1. Set `LAW_GROUNDING_MODE=disabled`.
2. Redeploy backend with known-safe env.
3. Verify `/api/debug/law-grounding` returns disabled warnings.
4. Confirm `/api/ask` continues without forced law grounding.

## Production enablement criteria
All must be satisfied:
1. Stage 1-4 checks pass in reproducible environments.
2. Citation-verification behavior is tested for success/failure paths.
3. Logs/metrics detect silent degradation.
4. Clear rollback runbook is validated.
5. Source-authority policy checks are documented and reviewed.

## Must-never-happen list
- fabricated law citations
- unofficial-source legal authority substitution
- silent grounding failure masked as success
- production enablement without explicit env/config review
