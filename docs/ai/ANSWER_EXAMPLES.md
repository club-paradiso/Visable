# Paradiso.ai — Answer Examples (DRAFT)

> **STATUS: DRAFT — documentation-first.**
>
> These examples illustrate how the answer-quality contract is
> applied. They are **illustrative**, not training data and not a
> source of truth for visa rules. They do **not** invent official
> source data; placeholder fields explicitly note where a real
> implementation would attach a real source.
>
> No runtime behavior changes. Law grounding remains **disabled by
> default**. Citation verification remains **partial / not fully
> wired**. No legal review has been performed.

---

## How to read these examples

Each example shows:

- the user question (or sketch of one),
- the **acceptable response structure** as an answer object,
- the **source / uncertainty treatment**,
- **high-risk handling**, if relevant,
- what the assistant **must not say** in this case.

Field names refer to `docs/ai/ANSWER_QUALITY_CONTRACT.md`.
Uncertainty / verification state names refer to
`docs/ai/CITATION_AND_UNCERTAINTY_SCHEMA.md`. High-risk rules refer
to `docs/ai/HIGH_RISK_ESCALATION_RULES.md`.

Placeholder source titles and URLs are intentionally **not** real
links. They mark where a real source attachment is required.

---

## Example 1 — D-2 체류기간 연장 구비서류

**User question (ko):** "D-2 체류기간 연장 구비서류 알려줘"

### Acceptable response structure

```jsonc
{
  "answer_id": "example-d2-extension-docs",
  "locale": "ko",
  "user_question": "D-2 체류기간 연장 구비서류 알려줘",
  "interpreted_intent": "D-2 visa extension required documents",
  "visa_code_or_topic": "D-2",
  "short_answer": "D-2 체류기간 연장은 보통 신청서, 여권/외국인등록증, 재학증명서, 성적증명서, 체류지 증빙, 수수료 등이 필요합니다. 정확한 구비서류와 인정 범위는 출입국·외국인청 안내(HiKorea 등)와 학교 국제처 안내로 최종 확인하세요.",
  "answer_type": "required_documents",
  "required_documents": {
    "common": [
      { "key": "application_form", "label": "통합신청서" },
      { "key": "passport", "label": "여권" },
      { "key": "arc", "label": "외국인등록증" },
      { "key": "fee", "label": "수수료" }
    ],
    "required": [
      { "key": "enrollment_cert", "label": "재학증명서" },
      { "key": "transcript", "label": "성적증명서" }
    ],
    "conditional": [
      { "key": "residence_proof", "label": "체류지 입증서류", "uncertainty_flag": { "state": "source_supported" } }
    ],
    "additional": [
      { "key": "tuition_receipt", "label": "등록금 납부 영수증", "uncertainty_flag": { "state": "source_supported" } }
    ],
    "missing_or_unverified": [
      { "key": "school_specific_letter", "label": "학교별 추가 요청 서류", "uncertainty_flag": { "state": "missing_source" } }
    ]
  },
  "procedure_steps": [
    "학교 국제처에서 재학·성적증명서 발급",
    "HiKorea 또는 관할 출입국에서 신청 접수 (예약 권장)",
    "현장 또는 온라인으로 서류 제출 및 수수료 납부",
    "결과 확인 후 외국인등록증 회수/갱신"
  ],
  "fees": [
    { "key": "extension_fee", "label": "체류기간 연장 수수료", "uncertainty_flag": { "state": "outdated_or_unknown" } }
  ],
  "appointment_guidance": "HiKorea 방문예약을 우선 권장합니다. 학기 시작·종료 시기에는 예약이 어렵습니다.",
  "hikorea_guidance": "전자민원으로 일부 신청이 가능하나, 학교/지역에 따라 방문 접수만 받는 경우가 있습니다.",
  "source_summary": "출입국·외국인 행정 매뉴얼 및 HiKorea 안내를 바탕으로 한 정보입니다. 일부 항목은 최신 검증이 되지 않았습니다.",
  "sources": {
    "official_manual_sources": [
      {
        "source_id": "manual.d2.extension.placeholder",
        "bucket": "official_manual_sources",
        "title": "D-2 stay extension — official civil manual (placeholder)",
        "publisher": "Ministry of Justice (placeholder)",
        "url": null,
        "locale": "ko",
        "retrieved_at": null,
        "verification_status": "source_linked_unverified"
      }
    ],
    "official_government_sources": [
      {
        "source_id": "hikorea.d2.extension.placeholder",
        "bucket": "official_government_sources",
        "title": "HiKorea — D-2 extension procedure page (placeholder)",
        "publisher": "HiKorea",
        "url": null,
        "locale": "ko",
        "retrieved_at": null,
        "verification_status": "source_linked_unverified"
      }
    ],
    "public_data_sources": [],
    "legal_sources": [],
    "internal_normalized_data_sources": [
      {
        "source_id": "paradiso.visa_data.d2",
        "bucket": "internal_normalized_data_sources",
        "title": "Paradiso normalized D-2 entry",
        "publisher": "Paradiso internal",
        "url": null,
        "locale": "ko",
        "retrieved_at": null,
        "verification_status": "not_applicable"
      }
    ]
  },
  "law_grounding": {
    "mode": "disabled",
    "attempted": false,
    "used": false,
    "warnings": [],
    "citation_verification_status": "disabled"
  },
  "uncertainty_flags": [
    { "state": "source_supported", "scope": "answer" },
    { "state": "outdated_or_unknown", "scope": "fee", "target": "extension_fee" }
  ],
  "high_risk_flags": [],
  "user_next_actions": [
    "학교 국제처에 학교별 추가 서류 확인",
    "HiKorea 예약 후 관할 출입국에서 최종 구비서류 확인",
    "수수료·납부 방법은 접수 시점에 다시 확인"
  ],
  "disclaimer_snippet": "이 답변은 정보 제공용입니다. 공식 결정 권한이 없습니다.",
  "last_verified_at": null,
  "freshness_status": "stale_unknown"
}
```

### Source / uncertainty treatment

- Manual and HiKorea pages are referenced as
  `source_linked_unverified` because Paradiso does not currently
  re-fetch and content-check those pages per request.
- `visa_data.json` is internal normalized data and is labeled as
  such (level 5 of the source hierarchy).
- The fee carries `outdated_or_unknown` because fee amounts change
  and Paradiso does not guarantee freshness without verification.
- A `missing_or_unverified` document bucket is surfaced to make
  hidden gaps visible.

### High-risk handling

Not high-risk; `high_risk_flags` is empty.

### What the assistant must not say

- "These are *all* the documents you need." (Document lists vary
  by school / region / officer discretion.)
- "Extension is guaranteed if you submit these."
- "The fee is exactly ₩X." (Without a verified, fresh fee source.)

---

## Example 2 — E-7 근무처 변경

**User question (ko):** "E-7 근무처 변경 절차 알려줘"

### Acceptable response structure (summary)

- `answer_type`: `procedure_guidance`.
- `short_answer`: plain-language note that E-7 work-place change
  generally requires a procedure with immigration (notification or
  permission depending on case), and that the exact path depends on
  the user's specific sub-category and the new employer's
  documentation.
- `required_documents`: standard documents (application form,
  passport, ARC, new employer documents, prior employer release /
  termination evidence as applicable) plus a `missing_or_unverified`
  bucket noting that sub-category specifics may add documents.
- `procedure_steps`: appointment via HiKorea → submission at the
  competent immigration office → result.
- `sources`: official manual + HiKorea page as
  `source_linked_unverified`; internal normalized data labeled
  internal.
- `law_grounding`: `disabled` / `disabled`.
- `uncertainty_flags`: `source_supported` at answer scope;
  `partially_supported` for any sub-category-specific claim.
- `high_risk_flags`: empty by default, **but** if the user's
  question implies that they have already changed employer without
  notification, or that they are working at a new employer without
  approval, the pipeline MUST re-classify as high-risk
  (`employment_authorization_uncertainty`) and switch to
  `high_risk_defer`.

### What the assistant must not say

- "You can change employers freely without notifying immigration."
- "Working at the new employer before approval is fine."
- "Your specific sub-category definitely allows this change."

---

## Example 3 — 주소 이전 신고 (Address change notification)

**User question (ko):** "이사했는데 주소 이전 신고 어떻게 해?"

### Acceptable response structure (summary)

- `answer_type`: `procedure_guidance`.
- `short_answer`: plain-language note that registered foreign
  residents are generally required to report a change of address
  within a statutory window after moving, and that the report can
  typically be made at a community service center (주민센터) or via
  the official portal as applicable. The exact window MUST be
  surfaced as a `deadline_or_reminder`-flavored claim and labeled
  with the appropriate uncertainty if not freshly verified.
- `required_documents`: ARC, evidence of new address (e.g. lease /
  residence proof) as applicable.
- `procedure_steps`: 1) gather evidence of new address, 2) visit
  주민센터 or use the official portal, 3) receive confirmation.
- `sources`: official guidance page placeholder, internal
  normalized data, all labeled honestly.
- `uncertainty_flags`: any specific deadline carries
  `source_supported` or `outdated_or_unknown` if not verified.
- `high_risk_flags`: empty by default, **but** if the user implies
  the deadline has already passed, the pipeline MUST escalate to
  `deadlines_or_government_notices` and recommend contacting the
  appropriate office to clarify.

### What the assistant must not say

- "There is no deadline."
- "Nothing will happen if you don't report."
- A specific deadline figure without source backing.

---

## Example 4 — 여권정보 변경 신고 (Passport information change)

**User question (ko):** "여권 새로 발급받았어. 신고해야 돼?"

### Acceptable response structure (summary)

- `answer_type`: `procedure_guidance`.
- `short_answer`: yes, holders of foreigner registration are
  generally required to report changes to passport information
  (number, expiry, name) within a statutory window. Confirm the
  exact path (community service center vs. immigration office vs.
  online) via HiKorea / official guidance.
- `required_documents`: ARC, old passport (or copy), new passport,
  application form as applicable.
- `procedure_steps`: file change-of-passport-information report at
  the appropriate office or via the official portal.
- `sources`: HiKorea / official guidance placeholder, internal
  normalized data; all labeled honestly.
- `uncertainty_flags`: `source_supported` at answer scope. Any
  specific deadline claim that is not verified gets
  `outdated_or_unknown`.
- `high_risk_flags`: empty unless the user implies they have
  delayed reporting beyond the window, in which case re-classify
  under `deadlines_or_government_notices`.

### What the assistant must not say

- "You don't have to report passport changes."
- "It's automatic — immigration already knows."
- A specific deadline figure without source backing.

---

## Example 5 — F-6 배우자 체류기간 연장

**User question (ko):** "F-6 배우자 체류기간 연장 구비서류"

### Acceptable response structure (summary)

- `answer_type`: `required_documents` with a deliberate
  `partially_supported` posture, because F-6 cases are heavily
  fact-specific (marriage status, cohabitation, prior denials,
  domestic-violence protective grounds, children, etc.).
- `short_answer`: list of common documents (application form,
  passport, ARC, marriage certificate, spouse's documents, residence
  evidence, income / livelihood evidence, etc.) **as a starting
  point**, with explicit note that the exact set depends on the
  couple's specific situation.
- `required_documents.missing_or_unverified` MUST include items
  like "additional evidence requested in fact-specific cases (e.g.
  cohabitation, marriage authenticity, sponsor's livelihood)".
- `uncertainty_flags`: `partially_supported` at answer scope.
- `high_risk_flags`: **family_dependent_sponsorship_consequences**
  is set whenever the question implies a separated couple, an
  ongoing dispute, a prior denial, or an enforcement risk. In
  those cases `answer_type` becomes `high_risk_defer` and the
  recommendation is to contact a qualified administrative
  scrivener / attorney and the relevant immigration office.

### What the assistant must not say

- "Your F-6 extension will be approved if you bring these."
- "Separation / dispute does not matter."
- "You qualify for F-6 regardless of cohabitation."
- "Bring this and you will be fine."

---

## Example 6 — Unknown visa code

**User question:** "What documents do I need for a Z-99 extension?"

### Acceptable response structure (summary)

- `visa_code_or_topic`: `null` (Z-99 is not a recognized code).
- `answer_type`: `unsupported_or_uncertain`.
- `short_answer`: plain-language note that Paradiso does not
  recognize the code "Z-99" and asks the user to confirm the
  status code, optionally listing common adjacent codes for
  disambiguation **without** asserting any of them is the user's
  status.
- `required_documents`: all buckets empty, with one entry in
  `missing_or_unverified` explaining that the document list is not
  computed because the status code is unrecognized.
- `sources`: empty official buckets; internal normalized data may
  carry the list of known codes only as an *internal* reference.
- `uncertainty_flags`: `missing_source` at answer scope.
- `high_risk_flags`: empty.
- `user_next_actions`: ask the user to confirm the code, or to
  check the code printed on their ARC / visa label, or to contact
  HiKorea / 1345 for clarification.

### What the assistant must not say

- A confident document list "for Z-99".
- A guess like "you probably mean F-2" presented as fact.
- "There is no such visa, so you have no status." (That is a
  determination Paradiso must not make.)

---

## Example 7 — Overstay / deportation-risk question

**User question:** "I overstayed by 40 days. Will I be deported?"

### Acceptable response structure (summary)

- `answer_type`: `high_risk_defer`.
- `high_risk_flags`: `overstay_risk`,
  `removal_deportation_enforcement_risk`,
  `deadlines_or_government_notices`.
- `short_answer`: a few sentences in plain language saying that
  overstay can carry serious consequences including fines, entry
  bans, and removal procedures; the actual outcome depends on the
  specific facts and is decided by the immigration authority;
  the user should contact the relevant immigration office
  (and/or a qualified administrative scrivener / attorney)
  **as soon as possible**.
- `required_documents`: typically empty in this answer_type; the
  goal is not to walk the user through a self-service path.
- `procedure_steps`: empty or a single high-level item
  ("contact the immigration office / qualified professional").
- `sources`: minimal; do not fabricate citations.
- `law_grounding`: `disabled` / `disabled`.
- `uncertainty_flags`: at minimum `high_risk_defer` at answer
  scope.
- `user_next_actions`: contact immigration office / HiKorea /
  1345; contact a qualified administrative scrivener or attorney.
- `disclaimer_snippet`: locale-appropriate informational-only
  disclaimer.

### What the assistant must not say

- "You will be deported."
- "You will not be deported."
- "Overstay of 40 days is fine."
- "Just leave the country and you can come back next week."
- "Pay the fine and there will be no record."
- "I will file the report for you."
- Any specific fine amount or specific outcome presented as
  determined.

---

## Example 8 — User asks for legal strategy

**User question:** "My E-7 extension was denied. What's the best
appeal strategy?"

### Acceptable response structure (summary)

- `answer_type`: `high_risk_defer`.
- `high_risk_flags`: `denial_rejection_appeal`,
  `status_change_with_unclear_eligibility` (if a change-of-status
  pivot is implied), possibly
  `employment_authorization_uncertainty`.
- `short_answer`: a few sentences in plain language explaining that
  there are generally administrative remedies (administrative
  appeals / reconsideration / administrative litigation) for
  refused immigration decisions, that each has its own deadlines
  and prerequisites, and that the right path depends on the
  specific facts. Recommend contacting a qualified attorney or
  administrative scrivener and the relevant immigration office.
- `required_documents`: empty or limited to "the denial notice
  and any supporting evidence" as items to bring to a
  professional.
- `procedure_steps`: at most a high-level pointer
  ("preserve the denial notice; consult a professional within the
  appeal window").
- `uncertainty_flags`: `high_risk_defer` at answer scope.
- `user_next_actions`: contact a qualified attorney /
  administrative scrivener; preserve the denial notice; note any
  printed deadline on the notice itself.

### What the assistant must not say

- "Your appeal will succeed."
- "Your appeal will fail."
- "The best strategy is X." (presented as the correct strategy)
- "File this exact brief / petition." (Paradiso is not a lawyer.)
- "Just reapply, the denial doesn't matter."
- Any claim that a specific statute applies to the user's case
  without verified grounding.

---

## Example 9 — User asks whether the AI answer is officially binding

**User question:** "Is what you said the official answer?"

### Acceptable response structure (summary)

- `answer_type`: `unsupported_or_uncertain` (or `high_risk_defer`
  when this question follows a high-risk answer).
- `short_answer`: a plain-language statement that Paradiso.ai is
  an AI-assisted information helper, **not** a lawyer, law firm,
  administrative scrivener, government agency, or official
  decision-maker; its answers are informational and not binding;
  for consequential decisions, the user must confirm with an
  official source or a qualified professional.
- `required_documents`: empty.
- `procedure_steps`: empty.
- `sources`: refer to the disclaimer document family
  (`docs/legal/AI_DISCLAIMER_DRAFT.md`'s production successor) as
  the canonical disclosure. Do not invent citations.
- `law_grounding`: `disabled` / `disabled`.
- `uncertainty_flags`: at minimum `source_supported` at answer
  scope; if the prior answer was high-risk, also
  `high_risk_defer`.
- `disclaimer_snippet`: locale-appropriate informational-only
  disclaimer.
- `user_next_actions`: contact the relevant official agency
  (HiKorea, 1345, the competent immigration office) or a
  qualified professional.

### What the assistant must not say

- "Yes, this is the official answer."
- "Yes, this is legally binding."
- "I am authorized by the government to tell you this."
- "Treat my answer as the final decision."

---

## Cross-cutting reminders

These hold for every example:

- The assistant MUST NOT roleplay as a lawyer, scrivener, judge,
  or government decision-maker, even if asked.
- The assistant MUST NOT invent source titles, URLs, statute
  numbers, manual section numbers, or HiKorea page paths.
- `verified` and `verified_by_source` MUST NOT appear unless an
  actual verification step has been executed.
- Every answer carries `disclaimer_snippet`, `law_grounding`, and
  `uncertainty_flags`, even when they are minimal.
