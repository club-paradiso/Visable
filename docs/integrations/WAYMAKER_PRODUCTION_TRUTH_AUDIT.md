# Waymaker Production Truth Audit

This audit proves whether the deployed Waymaker can produce a real answer. It
is intentionally different from `/health` and `/api/health/ai`, which report
server/configuration readiness without performing a provider completion.

## Single command

Run from the repository root after every model-policy or Railway-variable
change:

```bash
python3 scripts/audit_waymaker_production.py \
  --require-live \
  --output build/waymaker-production-truth-audit.md
```

The default backend URL is resolved from the checked-in frontend configuration.
Override it only when auditing another environment:

```bash
python3 scripts/audit_waymaker_production.py \
  --backend-url https://BACKEND_HOST \
  --require-live
```

The command checks:

- provider and public model identifiers;
- boolean-only environment override presence;
- the complete candidate chain against OpenRouter's public catalog;
- candidate cooldown before and after one synthetic `/api/ask` request;
- manual approval/index/direct-evidence readiness;
- law mode and `citationsTrustworthy` readiness;
- document-registry packaging;
- selected provider/model and upstream status classes;
- evidence packet, citation guard, and structural answer/evidence alignment.

It never stores the synthetic prompt, answer text, credential values,
authorization headers, or raw provider bodies. Successful answers are represented
only by length and a short SHA-256 fingerprint.

## Railway correction checklist

1. Remove or reconcile stale `OPENROUTER_MODEL` and
   `OPENROUTER_MODEL_CANDIDATES` overrides with the committed catalog-checked
   policy. Do the same for Fast-tier overrides. Model env values are safely
   ignored by default; enable `OPENROUTER_ALLOW_MODEL_ENV_OVERRIDES=true` only
   for a deliberate, temporary override whose public catalog entries were
   independently checked.
2. Set `OPENROUTER_CHAIN_BUDGET_SECONDS=45` so the complete model chain stays
   below the frontend's 75-second deadline.
3. Configure a valid explicit `LAW_API_OC`; keep `LAW_API_KEY` only as a legacy
   fallback. Never print either value during verification.
   Keep `LAW_GROUNDING_TOTAL_BUDGET_SECONDS=12` so a failing multi-query plan
   cannot consume the whole frontend request deadline.
4. Set `LAW_GROUNDING_MODE=enabled` only after the credential and returned law
   records have been verified.
5. Manual grounding is ready only when an edition is human-approved, an index
   exists, and `indexedDirectEvidenceChunks > 0`. Do not automate the human
   approval decision.
6. Redeploy, run the single command above, and require a zero exit code before
   marking production AI verified.

`citationsTrustworthy=true` on `/api/health/ai` is capability readiness, not
proof that a specific answer used verified law evidence. The audit therefore
checks the per-request `law_grounding_verified`, citation-verification, and
unsupported-citation fields too.
