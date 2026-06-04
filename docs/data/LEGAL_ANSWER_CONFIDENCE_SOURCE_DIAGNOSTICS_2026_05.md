# Legal Answer Confidence and Source Diagnostics (2026-05)

## 1. Problem

After the scenario-specific legal-analysis fixes, Paradiso could correctly recognize the E-7 → F-2-99 side-job question, but the answer body could still sound more certain than the available sources supported. In the same response, the source panel could say that live law citation verification needed review while the first sentence stated a definitive conclusion about the old E-7 workplace-reporting duty.

That mismatch is unsafe: a helpful legal analysis is still useful, but the wording strength must track direct authority and citation quality.

## 2. Product principle

Paradiso should provide structured legal analysis even when direct official authority is limited. However, the answer must not present a final administrative determination unless the backend has direct, verified authority for the exact issue.

In source-limited states, the answer should:

- identify the current status, activity type, and legal issue;
- distinguish direct authority from related/comparative context;
- explain decisive facts to confirm with 1345, HiKorea, or the competent immigration office;
- avoid definitive permission/denial/reporting-duty conclusions.

## 3. Certainty levels

The backend exposes `answer_certainty_level`:

| Level | Meaning | Wording posture |
| --- | --- | --- |
| `direct` | Direct evidence exists and citation verification is `verified`. | Stronger language may be used, still with office-final caveat. |
| `contextual` | Related or analogical evidence exists, but not direct verified authority. | Explain legal context; avoid final conclusion verbs. |
| `limited` | Legal analysis exists, but direct law/manual lookup failed or direct evidence is absent. | Provide structured analysis and decisive facts; avoid definitive outcomes. |
| `unavailable` | No legal analysis and no usable source context. | Source-unavailable state may be shown; preparation-only guidance. |

Additional metadata includes `source_panel_confidence`, `direct_authority_available`, `direct_citation_available`, `legal_analysis_available`, `law_lookup_failed`, and `law_lookup_error_type`.

## 4. E-7 → F-2-99 before/after wording

### Before

The answer could begin with a definitive statement such as:

> 체류자격이 E-7(특정활동)에서 F-2-99(거주)로 변경되었다면, 원칙적으로 이전 자격인 E-7에 묶여 있던 근무처 변경·추가 신고 의무는 더 이상 적용되지 않습니다.

That was too strong when direct authority was missing or live law lookup returned a technical error.

### After

In a low/direct-source-limited state, Paradiso should use wording like:

> F-2-99로 체류자격 변경이 완료되었다면, 부업 여부는 이전 E-7 기준만으로 판단할 사안은 아니고 현재 F-2-99의 활동범위와 승인 조건을 기준으로 다시 검토해야 합니다. 다만 E-7의 근무처 추가 신고 의무가 자동으로 계속 적용되는지, 또는 전혀 적용되지 않는지는 개별 승인 조건과 부업의 형태를 확인해야 합니다.

The issue framing is:

- current F-2-99 status is primary;
- prior E-7 is related/comparative context;
- decisive facts include F-2-99 approval conditions, side activity form, employment/freelance/business structure, employer/client, industry, hours, and compensation.

## 5. Source panel copy changes

When legal analysis exists but direct citation is limited, the source panel should emphasize structured analysis rather than a raw source failure.

Preferred Korean default labels:

- `structured_legal_analysis_available`: **구조화된 법률 분석 사용** — 직접 법령 인용은 제한되지만, 답변은 체류자격·활동유형·쟁점 분석을 기준으로 구성되었습니다.
- `live_law_lookup_technical_issue`: **실시간 법령 조회 확인 필요** — 법령 조회에 기술 문제가 있어 직접 인용은 제한됩니다. 다만 구조화된 법률 분석은 계속 제공됩니다.
- `no_direct_authority_found`: **직접 근거 제한** — 현재 확인된 자료에서 이 정확한 상황을 직접 다루는 근거는 제한적입니다. 관련 쟁점 분석으로 안내합니다.

Raw codes such as `SOURCE_UNAVAILABLE`, `LAW_API_BAD_RESPONSE`, and `CITATION_VERIFICATION_NOT_WIRED` must not be default source-panel labels.

## 6. Developer diagnostics behavior

Technical details are developer diagnostics, not ordinary user-facing source status.

The default UI keeps raw codes collapsed. When expanded, the diagnostic section first shows human-readable text, such as:

- 실시간 법령 조회 응답을 파싱하지 못했습니다.
- 직접 법령 인용은 제한됩니다.

Raw codes may appear only after that developer-oriented explanation and must not be included in copied answer text.

## 7. Tests added

Coverage was added or strengthened for:

- E-7 → F-2-99 side-job low-direct-authority wording;
- direct mocked authority producing `answer_certainty_level=direct`;
- H-1 study source-limited non-definitive framing;
- C-3 paid work source-limited no invented penalty / no overconfident conclusion;
- source-panel metadata for legal analysis plus `LAW_API_BAD_RESPONSE`;
- static UI checks that raw codes are not default labels and developer diagnostics are clearly labeled.

The smoke script now reports certainty/source-panel fields and warns on overconfident wording, source-panel trust mismatches, default raw-code leaks, and copy-answer raw-code leaks.

## 8. Known limitations

- The live law API may still fail or return an unsupported shape.
- Direct authority may not exist for every scenario.
- Related or analogical evidence can support useful analysis, but it is not the same as direct authority.
- Final agency interpretation remains with 1345, HiKorea, and the competent immigration office.

## 9. Safety note

Paradiso’s legal answers are reference guidance. Users should not treat a source-limited answer as permission, denial, exemption, or a final reporting-duty determination. When the source state is limited, the product should make the next official confirmation step concrete rather than filling the gap with confident language.
