# Paradiso Claim Verification

## Purpose

Use this guide to verify individual claims in AI answers, data records, docs, and review reports. Verification happens at claim level, not paragraph level. A paragraph can contain both supported and unsupported claims.

## Claim categories

Every claim must use one category:

| Category | Examples |
|---|---|
| `legal duty` | Must report, must register, must maintain status, must not work outside scope. |
| `eligibility` | Qualifying status, income condition, sponsor relation, program condition. |
| `required document` | Application form, passport copy, photo, certificate, proof document. |
| `deadline` | Within 14 days, before expiration, by a notice date. |
| `fee` | Revenue stamp, issuance fee, exemption, per-person fee. |
| `procedure` | Apply online, visit office, submit extension, change status, register. |
| `warning/disclaimer` | Not legal advice, confirm with office, high-risk uncertainty, source gap. |
| `office/jurisdiction` | Which office, call center, institution, or agency owns the step. |
| `reservation guidance` | Whether booking is needed, where booking occurs, link-only service guidance. |
| `status-specific exception` | Sub-code exception, nationality exception, helper scenario, overstay edge case. |

## Required claim record

Use this shape for audit output, fixtures, review notes, and future answer-grounding traces:

```json
{
  "claimText": "Exact claim or shortest faithful paraphrase.",
  "claimCategory": "required document",
  "sourceType": "official_manual",
  "sourceLocator": "docs/source-manuals/2026-06/stay_manual_2026_06_01.pdf p. 44, section: Foreign registration / required documents",
  "sourceQuoteKo": "Exact quote when available, or null when using a precise section locator only.",
  "preciseSectionReference": "Manual version 2026-06-01, printed page 44, section heading ...",
  "supportLevel": "direct",
  "supportRelation": "direct",
  "lastChecked": "YYYY-MM-DD",
  "reviewerNotes": "Scope is D-2 registration only; does not verify extension or sub-code exceptions."
}
```

## Required fields

Each claim must include:

- `claimText`
- `claimCategory`
- `sourceType`
- `sourceLocator`
- `sourceQuoteKo` or `preciseSectionReference`
- `supportLevel`
- `supportRelation`

`supportLevel` and `supportRelation` both use:

| Value | Meaning |
|---|---|
| `direct` | The official source states the claim in the same scope. |
| `partial` | The official source supports only part of the claim. |
| `contextual` | The source helps explain the claim but does not prove it. |
| `unavailable` | No official source evidence is available in the audit context. |

## Verification rules

- A claim is verified only when an official source directly supports that exact claim and scope.
- A source for one category does not verify another category. A document list does not verify a fee; a fee table does not verify eligibility.
- A parent status locator does not verify a sub-code, exception, helper scenario, or overstay rule unless the source explicitly covers that scope.
- A general HiKorea service page can support where to apply or reserve, but not eligibility or legal duty unless it states those directly.
- A warning/disclaimer claim may be supported by Paradiso policy docs, but that does not verify the underlying immigration claim.
- When source support is missing, the correct result is `supportLevel: "unavailable"` with a clear note. Do not fill the gap with AI reasoning.

## AI answer behavior

- Directly supported claims may be stated plainly with a citation or source panel entry.
- Partially supported claims must name the unsupported portion or be narrowed.
- Contextual claims must be phrased as guidance, not official certainty.
- Unavailable claims must either be omitted, explicitly marked uncertain, or routed to manual confirmation.
- High-impact categories such as legal duty, eligibility, deadline, fee, and status-specific exception require direct support before confident wording.
