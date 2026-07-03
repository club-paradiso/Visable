# NVIDIA NIM feasibility — July 2026

Audit date: 2026-07-02. Hosted API Catalog trial only; no live call or credential read.

## Decision

**Internal QA only**, using synthetic/public non-personal prompts. Do not route real Waymaker questions to NVIDIA. `production_ready=false`.

## 1. Official sources checked

- [Nemotron 3 Ultra](https://build.nvidia.com/nvidia/nemotron-3-ultra-550b-a55b)
- [Nemotron 3 Super](https://build.nvidia.com/nvidia/nemotron-3-super-120b-a12b)
- [Llama 3.3 Nemotron Super](https://build.nvidia.com/nvidia/llama-3_3-nemotron-super-49b-v1_5)
- [Ultra hosted API reference](https://docs.api.nvidia.com/nim/reference/nvidia-nemotron-3-ultra-550b-a55b-infer)
- [NIM LLM API reference](https://docs.nvidia.com/nim/large-language-models/latest/api-reference.html)
- [NVIDIA API Trial Terms](https://assets.ngc.nvidia.com/products/api-catalog/legal/NVIDIA%20API%20Trial%20Terms%20of%20Service.pdf)

Re-check mutable catalog/terms before any rollout.

## 2–4. Endpoint, models, free status

- Base URL: `https://integrate.api.nvidia.com/v1`; chat: `POST /chat/completions`.
- NVIDIA documents OpenAI-compatible JSON, bearer `NVIDIA_API_KEY`, and streaming.
- Checked IDs: `nvidia/nemotron-3-ultra-550b-a55b`, `nvidia/nemotron-3-super-120b-a12b`, `nvidia/llama-3.3-nemotron-super-49b-v1.5`.
- All checked catalog pages showed “Free Endpoint Available.” This means limited trial access, not free production service or SLA.
- Ultra advertises Korean support. The checked Super cards do not establish equivalent Korean suitability; benchmark separately.

## 5. Trial/production limits

Trial terms limit use to internal testing/evaluation and prohibit production use of the service/generated content without a separate NVIDIA or provider subscription. Credits, request count/duration, availability, privacy, and reliability may be limited; service can change or end. “Commercial use” in a model license does not override hosted trial-service terms.

No production subscription, DPA, SLA, region/retention commitment, or Korean privacy review was supplied. Production readiness is unconfirmed and therefore false.

## 6. Privacy/data risks

Trial terms restrict confidential, controlled, sensitive, personal, financial, health, and governmental information unless expressly permitted. They allow user/generated content collection for product/model improvement and security/fraud/abuse monitoring, including service providers.

Immigration status, nationality, family, employment, lawsuit, refugee, identifiers, and individualized legal facts are personal/sensitive. Do not send them. Redaction is not a general production authorization.

## 7–8. Can Visable use it now? Rollout stage

Only non-production internal QA/research with synthetic or public non-personal prompts. Real-user use: **do not use**. Recommended stage: **internal QA only**. Not approved for research containing user facts, limited fallback, or production.

## 9. Environment

```text
ENABLE_NVIDIA_NIM_EXPERIMENTAL=false
NVIDIA_API_KEY=
NVIDIA_NIM_BASE_URL=https://integrate.api.nvidia.com/v1
NVIDIA_NIM_MODEL=nvidia/nemotron-3-ultra-550b-a55b
NVIDIA_NIM_TIMEOUT_SECONDS=45
NVIDIA_NIM_MAX_TOKENS=1200
NVIDIA_NIM_REASONING_ENABLED=false
NVIDIA_NIM_ALLOWED_MODES=research,internal_qa
NVIDIA_NIM_ALLOW_PERSONAL_DATA=false
```

## 10. Operator steps

1. Keep the enable flag false in production.
2. Verify `/health.provider_status.nvidia_nim`: configured as expected, enabled false, personal data false, production ready false, wired to `/api/ask` false.
3. For an approved experiment use a separate non-production environment, an allowed mode, and explicit `public_non_personal` classification.
4. Re-check terms, license, quotas, region, retention, subprocessors, DPA, SLA, and subscription. Never paste/log/commit the key.

## 11. Tests

`backend/tests/test_nvidia_nim_provider.py`: configured/disabled posture, mode gate, unknown/sensitive fail-closed gates, mocked OpenAI shape, health secrecy, metadata, error redaction. No live NVIDIA call.

## 12. Remaining legal/terms risks

Production contract/data terms, PIPA cross-border review, retention/location, model license drift, quality, Korean legal accuracy, latency, rate limits, and endpoint continuity remain unresolved.
