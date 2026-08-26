# Visable AI Production Runbook

Operator guide for the AI layer. **Variable names only — never paste a value
into this file, a ticket, a log, or a chat message.**

---

## 1. Is the AI actually up?

Three questions, three different checks. They are not interchangeable.

```bash
# 1. Is the web server alive?          (cheap, no AI)
curl -s https://<BACKEND_HOST>/health | python3 -m json.tool

# 2. Is the AI *configured* to work?   (cheap, no provider call, no billing)
curl -s https://<BACKEND_HOST>/api/health/ai | python3 -m json.tool

# 3. Does the AI *actually* answer?    (real completions — the only proof)
python3 scripts/smoke_ai_runtime.py --backend-url https://<BACKEND_HOST> \
    --require-live --pace 8
```

Only **3** proves the AI works. `/api/health/ai` reports configuration
readiness and hardcodes `liveVerification.performed: false` precisely so it can
never be mistaken for proof.

Read the smoke output as:

* `PASS` — the feature produced real output.
* `DEGRADED` — it failed safely. Good resilience, **not** a working feature.
* `FAILED` — broken.
* `SKIPPED` — Visable's own rate limiter intervened; re-run with `--pace 8`.
  A skipped check is not a passing check.

Bottom line is either `LIVE AI VERIFIED` or `LIVE AI NOT VERIFIED`. There is no
third state, and the absence of a check is never reported as health.

---

## 2. Outstanding operator actions

These could not be performed from the environment where the 2026-08 pass ran
(its network policy returns 403 on CONNECT to both the deployed backend and
`openrouter.ai`). Each is a real, verifiable step.

### 2.1 Verify the production AI end to end — **required**

```bash
python3 scripts/smoke_ai_runtime.py --backend-url https://<BACKEND_HOST> \
    --require-live --pace 8 --json > ai-smoke.json
```

Confirm `AI Overview` and `employment interpretation` now report `ok`. Both
were **permanently broken in production** before this change — every request
returned `unavailable`. They are verified against the real application locally,
but only this run proves it on the deployed instance.

### 2.2 Build the manual search index at deploy time — **required for manual grounding**

`/api/health/ai` currently reports:

```
grounding.manual.blocker:
  "approved manual editions exist but the FTS index is not built on this
   deployment; run scripts/build_manual_search_index.py during the build"
```

The registry holds human-approved manual editions, but the FTS index that
surfaces them is a build artifact and nothing builds it. **Approved manual
evidence is therefore unreachable in production**, and answers degrade to
`index_unavailable` — honest, but far weaker than the evidence Visable actually
holds.

Fix: add to the Railway build (or a start hook):

```bash
python3 scripts/build_manual_search_index.py
```

Then confirm `grounding.manual.ready` is `true` and the blocker is empty.

### 2.3 Decide the law grounding posture — **judgement call**

Production runs `LAW_GROUNDING_MODE=audit` with `LAW_API_OC` set. In audit mode
retrieval runs but citations are never marked verified, so answers say "law not
verified" even though the credential exists. That is deliberate.

**Do not flip to `enabled` blind.** First run:

```bash
curl -s https://<BACKEND_HOST>/api/debug/law-grounding/preflight
curl -s https://<BACKEND_HOST>/api/debug/law-grounding/selftest
```

Confirm search works, parsing works, law-name matching works, article retrieval
works, repealed/current status is handled, citation verification works, and no
credential appears in any surfaced URL. Only then set
`LAW_GROUNDING_MODE=enabled`. The unverified-citation guardrail protects every
non-verified state in the meantime, so audit mode is safe to stay in.

### 2.4 Check the model catalog — **recommended before each deploy**

```bash
python3 scripts/check_model_catalog.py
```

Needs no credential. Reports ids that no longer exist, `:free` ids that have
started pricing, and dead chains where no candidate remains — the last meaning
that task role cannot answer at all. It never auto-edits model selection.

---

## 3. Diagnosing a failure

Start from `/api/health/ai`, then the classified error.

| Symptom | Meaning | Action |
|---|---|---|
| `activeProvider: "none"` | No key, or Groq set without `ALLOW_GROQ_FALLBACK` | Set `OPENROUTER_API_KEY` |
| `invalid_provider_config` (401/403) | Bad/expired key. **Not** transient — the chain stops immediately by design | Rotate the key |
| `rate_limited` (429) | Free-tier limit | Expected; chain + cooldown absorb it. Persistent → deepen `OPENROUTER_MODEL_CANDIDATES` |
| `model_not_found` (404) | Slug renamed or withdrawn | `check_model_catalog.py`, then update candidates |
| `upstream_unavailable` (502/503/504) | Provider capacity | Transient; chain handles it |
| `all_candidates_cooling_down` | Every model failed recently | **Zero requests are being issued** — deliberate. Check `cooldown.cooling_down_models` |
| `policy_or_safety_rejection` (451) | Content filter. Never an outage | Do not retry as capacity |
| Answers work but are shallow | Grounding, not the model | Check `grounding.manual.ready` and `grounding.law.citationsTrustworthy` |
| `candidateWarnings` non-empty | Malformed id, random routing, or a stale env override | Inspect `llm.model_env_override` on `/health` |

**A stale environment variable pins the model.** `OPENROUTER_MODEL` overrides
the committed default, so an old Railway value keeps the answer model on an old
id after a merge. `/health` reports `model_env_override` and
`code_default_model` to make that diagnosable.

---

## 4. CI gates

| Gate | Needs secrets? | Fails on |
|---|---|---|
| `scripts/check_ai_architecture.py` | No | provider host outside an adapter, credential read outside the runtime, model id outside the policy, random routing, committed secret, frontend→provider call, completion result unpacked as a tuple, duplicated backend origin |
| `scripts/run_backend_tests.py` | No | any NEW test failure; also any registered known-failure that starts passing |
| `scripts/check_model_catalog.py --strict` | No | catalog drift |
| `scripts/smoke_ai_runtime.py --require-live` | Backend must be deployed | unreachable backend, unconfigured provider, real completion failure |

Normal PR CI runs the first two. `--require-live` is for a deploy gate, not PRs.

---

## 5. Rollback

Every change in this pass is additive or a bug fix. Nothing is destructive.

**By layer, safest first:**

1. **Frontend backend origin** — revert `assets/js/backend-origin.js` and the
   consumers. Each consumer keeps an inline fallback, so removing the resolver
   script alone degrades to the previous behaviour without breaking pages.
2. **AI readiness endpoint** — `/api/health/ai` is additive; removing it affects
   nothing else. `/health` is unchanged.
3. **Nationality coach routing** — reverting restores Groq-first single-model
   routing. You lose the candidate chain and shared cooldown; the feature works.
4. **Shared AI runtime** — `paradiso_backend` delegates classification and
   cooldown to it. Reverting means restoring the inline implementations; the
   wire-format error labels are identical either way, so no client changes.
5. **Immigration tool layer** — additive; nothing depends on it yet at runtime.
6. **The endpoint fix (`d86d495`)** — **do not revert.** It is the difference
   between AI Overview and employment interpretation working at all and
   returning `unavailable` on every request.

**CI gates** can be disabled independently by removing their steps from
`scripts/check_repo.sh` without touching application code.
