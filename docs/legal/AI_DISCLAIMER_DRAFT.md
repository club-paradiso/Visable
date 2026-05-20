# Paradiso.ai — AI Disclaimer (DRAFT)

> **STATUS: DRAFT.** This document is a documentation-only working draft.
> It has **not** been reviewed by qualified legal counsel and must not
> be published as a production AI disclaimer without independent legal
> review.
>
> Producing this draft did not enable, change, or roll out law
> grounding, citation verification, or any other backend behavior. Law
> grounding remains disabled by default and is not production-ready.

---

## 1. Purpose

This draft explains, in plain language, what the Paradiso.ai assistant
is and is **not**, so that users have a realistic understanding of how
much weight to give its answers. It is intended both as the basis for
in-product disclosure (for example, a notice shown near the AI input)
and as a reference document that the Privacy Policy and Terms of
Service drafts can point to.

## 2. Scope

This draft covers:

- The Paradiso.ai assistant feature (`ai.html` and the associated
  backend `/api/ask` endpoint).
- The source hierarchy the assistant is intended to follow.
- The known current limitations of grounding and citation verification.

It does not cover the non-AI parts of the Paradiso website beyond the
extent that those parts surface AI-produced text.

## 3. Plain-language summary

- Paradiso.ai is an **information helper**, not a lawyer.
- It can be wrong, out of date, or incomplete.
- It is not a substitute for a lawyer, an administrative scrivener
  (行政書士 / 행정사 / similar licensed professional), or the relevant
  government authority.
- For anything high-stakes — status renewal, change of status, denial
  risk, removability, employment authorization, family-status
  filings, residency-time counting, fee calculations, deadlines — the
  user should confirm with an official source or a qualified
  professional before acting.

## 4. What Paradiso.ai is

Paradiso.ai is an AI-assisted administrative information tool. It is
designed to help users understand publicly available immigration / stay
administration information more easily, by:

- letting users ask questions in natural language;
- attempting to retrieve relevant administrative information from the
  product's underlying data;
- producing a structured answer that a user can read alongside the
  original source material.

## 5. What Paradiso.ai is **not**

Paradiso.ai is **not**:

- a lawyer, a law firm, or attorney-client representation;
- an administrative scrivener (行政書士 / 행정사) or any other
  licensed professional service;
- a government agency or an official government decision-maker;
- a final or authoritative interpretation of the law;
- a guaranteed-correct or guaranteed-current source of administrative
  rules;
- a filing service that submits applications to any authority on the
  user's behalf.

AI answers must **not** be treated as official legal advice or as
final government interpretation.

## 6. Source hierarchy

When Paradiso.ai answers an administrative-information question, it is
designed to draw on, in order of preference:

1. **Official manuals** issued by the relevant administrative
   authority, where one is registered to the product.
2. **Legal / regulatory text** that the official manual itself relies
   on.
3. **Publicly available data** from authoritative government sources.
4. **Internally normalized data** maintained inside the product to
   keep the answer set consistent across questions.
5. **Law-grounding metadata**, where it exists.

When sources at a higher tier are unavailable, the assistant may
fall back to a lower tier or may decline to answer.

Important caveats:

- Law grounding remains **disabled by default** in the current build
  and is not considered production-ready. Where it is not enabled, the
  assistant is not actively cross-checking answers against the
  registered legal-grounding corpus at runtime.
- Citation verification is currently **partial and not fully wired**.
  A citation shown alongside an answer is **not** a guarantee that the
  cited text actually says what the answer claims it says.

## 7. Uncertainty markers

The assistant is intended to communicate uncertainty when it exists,
for example by:

- naming the source it relied on, where one is available;
- distinguishing between "this is what the manual says" and "this is a
  general explanation";
- pointing the user to the relevant official authority for
  confirmation when the question is high-risk;
- declining to answer, or recommending professional consultation, when
  the question requires a judgment that depends on the user's specific
  facts.

If the assistant does **not** show an uncertainty marker for a given
answer, that absence is not itself a guarantee of correctness. The
user should still confirm any decision against an official source or
a qualified professional.

## 8. High-risk situations requiring official or professional confirmation

The following are examples of situations where the user **must not**
rely solely on a Paradiso.ai answer:

- decisions about whether to apply for, extend, change, or relinquish
  a particular residence or visa status;
- decisions that depend on whether a specific employer or program
  qualifies under a particular status;
- decisions that depend on counting days of residence, days of
  absence, or eligibility periods;
- responses to government notices, deadlines, or formal correspondence;
- anything involving potential denial of entry, removal, or other
  enforcement action;
- anything involving family members, dependents, sponsorship, or
  derivative status;
- anything where giving wrong information to an authority could itself
  carry legal consequences.

In these situations, the user should consult the relevant official
authority, a qualified lawyer, or a licensed administrative
scrivener / immigration professional in the relevant jurisdiction.

## 9. Citation verification limitations

The product may show citations alongside an AI answer (for example, a
manual reference, a section number, or a URL). The user should treat
these citations as **pointers to verify**, not as proof.

Specifically:

- The citation system in the current build is partial. Some citations
  may render as references without having been independently
  re-checked against the cited source at the moment of the answer.
- The cited source may have been updated since the product last
  ingested it.
- The cited source may itself have been amended or superseded by a
  newer manual or regulation.

The user is responsible for opening the underlying source and
confirming that it actually says what the answer claims it says before
relying on it for any consequential decision.

## 10. Data minimization in AI questions

The user should be told, in product UI and in the production
disclaimer, **not** to send information that is more sensitive than the
question requires. For example, a question about a visa category does
not normally require a passport number, an alien registration number,
or a case ID. See the Privacy Policy draft for the corresponding data
treatment.

## 11. Reminder feature

The reminder feature is currently scoped to the user's own browser
(`localStorage`) plus optional calendar export. It is not an
AI-generated legal calendar and it does not file or submit anything to
any agency.

- The user is responsible for the accuracy of any dates entered.
- The user should not treat a reminder firing — or not firing — as
  evidence that any administrative action is or is not due.

Any future server-side notification feature (email, SMS, push,
calendar account sync) would require its own opt-in flow and an
update to this disclaimer before launch.

## 12. Operator and contact placeholders

- `[OPERATOR: legal entity name]`
- `[OPERATOR: contact email or form URL for AI-related concerns]`
- `[OPERATOR: name(s) of any third-party AI / LLM provider used in production]`

---

## Launch checklist

Before this draft can be promoted to a production AI disclaimer,
**all** of the following must be true:

- [ ] Independent legal review has been completed by qualified counsel
      in the operator's jurisdiction.
- [ ] Every `[OPERATOR: ...]` placeholder has been resolved.
- [ ] The product UI surfaces a clear, plain-language version of this
      disclaimer near the AI input — not buried in a footer link only.
- [ ] The disclaimer is linked from both the Privacy Policy and the
      Terms of Service.
- [ ] If law grounding is being turned on for the first time, the
      disclaimer's source-hierarchy and citation-verification sections
      have been updated to reflect what is actually wired, and a
      production-readiness review for that feature has been merged
      first.
- [ ] If a third-party AI / API provider is used in production, this
      disclaimer and the Privacy Policy both name it and describe the
      cross-border processing implication.
- [ ] If a future feature adds email, SMS, push, calendar sync, or
      account-based reminders, that feature's opt-in flow and policy
      update have been merged **before** the feature is enabled.
