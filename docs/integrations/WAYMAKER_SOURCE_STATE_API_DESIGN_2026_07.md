# Waymaker source-state API design — July 2026

Evidence support and prose provider are independent.

```json
{"source_state":{"manual":{"status":"confirmed"},"law":{"status":"audit_only","verified":false},"legal_evidence":{"status":"supplementary"},"confidence":"source_limited","source_limited":true,"official_confirmation_required":true},"generation_state":{"provider":"openrouter","experimental_provider_used":false,"provider_unavailable":false,"fallback_used":false}}
```

| Dimension | Values/meaning |
|---|---|
| Manual | `confirmed|related|absent|unavailable`; primary for procedures/documents/fees/deadlines. |
| Law | `disabled|audit_only|verified|no_results|failed`; audit never verified. |
| Legal evidence | `not_attempted|not_warranted|supplementary|no_results|unavailable`; never primary for current requirements. |
| LLM | `generated|fallback_generated|deterministic|unavailable`; prose only. |
| Confidence | `direct|related|source_limited|source_unavailable`; evidence-derived only. |

Invariants: keep manual/law/case arrays separate; case law stays fact-specific and supplementary; any LLM including NVIDIA has zero positive effect on confidence; fallback changes generation state only; experimental provider and sanitized unavailability are visible; audit-only never maps to verified; preserve source metadata when generation fails.

Simple Korean copy: `공식 안내서에서 확인했어요`, `현행 법령을 확인했어요`, `법령 근거를 추가 확인해야 해요`, `관련 판례가 있어요 · 개별 사건 참고용`, `확인된 근거가 제한적이에요`, `1345 또는 관할 출입국기관에 확인하세요`, `실험 기능으로 생성된 답변이에요`, `AI 답변을 만들지 못했어요 · 공식 확인 방법을 안내합니다`.

Migration after Fable 5: add `source_state`/`generation_state` without removing legacy fields; map source panel only to source state; contract-test that provider/model changes cannot change confidence for identical evidence; retire legacy fields only in a versioned change.
