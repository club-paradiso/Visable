# Paradiso.ai — High-Risk Escalation Rules (DRAFT)

> **STATUS: DRAFT — documentation-first.**
>
> Paradiso.ai is **not** a lawyer, law firm, administrative scrivener,
> government agency, or official decision-maker. Its answers are
> informational. This document defines the categories of questions
> that the answer pipeline must treat as **high-risk** and the
> behavior the pipeline must take in those cases.
>
> No runtime behavior changes. Law grounding remains **disabled by
> default**. Citation verification remains **partial / not fully
> wired**. No legal review has been performed.

---

## 1. Purpose

Some questions about immigration / stay administration have outcomes
serious enough that a wrong AI answer is not just inconvenient — it
can lead to overstay, removal, denial of future applications,
criminal exposure, family separation, loss of employment
authorization, or loss of long-term residence eligibility.

For those questions, the right behavior is **not** to try harder to
give a clean, confident answer. The right behavior is to give a
short informational pointer and route the user to an official agency
or a qualified professional.

This document defines:

1. which question categories trigger high-risk handling,
2. how the assistant must respond when one of those categories is
   triggered,
3. what the assistant must explicitly **not** say.

These rules are normative for the contract in
`docs/ai/ANSWER_QUALITY_CONTRACT.md`.

## 2. High-risk categories

The pipeline MUST treat a question as high-risk when it falls into
one or more of the following categories. Detection may be heuristic
(keyword, classifier) at first; the contract is about behavior given
detection, not about the detection model itself.

1. **Overstay risk.** The question concerns whether the user has
   already overstayed, is about to overstay, or how to handle an
   expired status.
2. **Removal / deportation / enforcement risk.** The question
   concerns deportation, removal orders, departure orders,
   enforcement actions, or detention.
3. **Denial / rejection / appeal.** The question concerns a denied
   application, a rejection, refusal of entry, refusal of extension
   / change, or how to appeal one.
4. **Criminal record / investigation / prosecution.** The question
   concerns a criminal record, ongoing investigation, prosecution,
   summary order, or how any of those interacts with stay status.
5. **False statement or document issue.** The question concerns a
   suspected false statement, fabricated document, altered document,
   or material omission in a prior filing.
6. **Employment authorization uncertainty.** The question concerns
   whether a specific job, side job, internship, contract, or
   business activity is permitted under the user's current status.
7. **Family / dependent / sponsorship consequences.** The question
   concerns whether the user's status decision will affect a
   spouse, child, parent, or sponsor — including F-class status,
   accompanying minor children, separated families, and divorce /
   separation cases.
8. **Permanent residence / naturalization eligibility.** The
   question concerns F-5, naturalization, period-of-stay counting
   for permanent residence, or any consequence to long-term
   eligibility.
9. **Status change with unclear eligibility.** The question
   concerns changing from one status to another (e.g. D-2 → E-7,
   E-7 → F-2, etc.) where eligibility is fact-specific and easily
   misstated.
10. **Deadlines or government notices.** The question concerns a
    specific deadline, summons, official letter, text message
    from an official channel, or a 14-day-style reporting
    obligation.
11. **Medical / legal / financial consequences.** The question
    asks the assistant to weigh medical, legal, or financial
    consequences (e.g. "should I", "is it worth it", "will I be
    fined", "do I have to pay this").

The categories are not mutually exclusive. A single question may
trigger several.

## 3. Required behavior when a high-risk category is triggered

When `high_risk_flags` is non-empty, the answer object MUST satisfy
all of the following:

### 3.1 Short informational answer only

- `short_answer` is **at most a few sentences**, plain-language,
  oriented toward "here is what kind of thing this is, and who can
  actually decide it".
- `short_answer` MUST NOT contain step-by-step legal strategy.
- `short_answer` MUST NOT predict an outcome
  ("you will be approved", "you will be deported", "this counts as
  X under the law").

### 3.2 No definitive legal determination

The assistant MUST NOT:

- assert that the user's situation **is** or **is not** illegal,
- assert that the user **will** or **will not** be deported,
  removed, fined, prosecuted, denied, approved, or detained,
- assert that a specific fact pattern **qualifies** or **does not
  qualify** under a specific statute or regulation,
- assert that the user's prior filing constitutes fraud, a false
  statement, or any criminal act,
- assert that a particular procedural remedy (appeal,
  reconsideration, lawsuit) will succeed.

It MAY say in plain language *that such determinations exist* and
are made by official authorities or qualified professionals.

### 3.3 Recommend official agency or qualified professional

The answer MUST direct the user to one or more of:

- the relevant **official agency** (immigration office, HiKorea
  inquiries, 1345, Ministry of Justice contact lines as appropriate
  to locale and topic),
- a **licensed administrative scrivener** (행정사 / 行政書士 /
  equivalent),
- a **qualified attorney**,
- the user's **employer / school's** designated officer where it
  is the appropriate first stop (e.g. for D-2 / D-4 academic
  affairs questions),
- the user's **sponsor** where relevant.

The selection of which to recommend SHOULD match the high-risk
category. Recommendation copy lives in the UI layer; the contract
only requires that *some appropriate recommendation* is present.

### 3.4 Show uncertainty clearly

- `uncertainty_flags` MUST include at minimum a `high_risk_defer`
  entry at `scope: "answer"`.
- Per-claim or per-document `uncertainty_flags` SHOULD also be set
  where applicable.
- `answer_type` MUST be `high_risk_defer` unless the question only
  *touches* a high-risk topic incidentally (e.g. a purely factual
  lookup of a public dataset that happens to be near a high-risk
  topic). When in doubt, prefer `high_risk_defer`.

### 3.5 Avoid pretending to make a legal determination

- The assistant MUST NOT roleplay as a lawyer, scrivener, judge,
  immigration officer, or government decision-maker, even if the
  user asks.
- The assistant MUST NOT produce documents that look like legal
  filings, sworn statements, or official forms.
- The assistant MUST NOT produce content that simulates an
  official agency's response or determination.
- If the user asks "is this answer official / legally binding",
  the assistant MUST clearly say it is informational and not
  binding.

## 4. What the assistant must not say

The following are concrete prohibitions. These apply whenever
`high_risk_flags` is non-empty.

- "You will not be deported."
- "You will be deported."
- "This is legal."
- "This is illegal."
- "You qualify for [status]."
- "You do not qualify for [status]."
- "Your application will be approved."
- "Your application will be denied."
- "You can ignore this notice."
- "This deadline does not apply to you."
- "Don't worry, it's fine."
- "As your lawyer / scrivener / immigration officer, I advise…"
- "This is the official position of [agency]."
- "This answer is legally binding."

The assistant MAY restate that *official authorities or qualified
professionals* can make those determinations.

## 5. Interaction with law grounding

While law grounding remains disabled by default, high-risk answers
MUST NOT claim a legal basis they have not actually retrieved and
verified. In practice this means:

- `law_grounding.mode` is typically `disabled` for production.
- `law_grounding.citation_verification_status` is typically
  `disabled` or `not_wired`.
- `answer_type = legal_grounding_explanation` SHOULD NOT be used
  inside a high-risk answer; the better answer_type is
  `high_risk_defer` with a recommendation to consult an official
  source or qualified professional.

When law grounding is later enabled in a future phase, the
high-risk rules in this document take precedence over any urge to
present grounded text as a determination. Grounded text is still
informational.

## 6. Detection guidance (non-normative)

Detection of high-risk categories is out of scope for this
contract. The pipeline SHOULD start with conservative keyword and
intent-classification heuristics (e.g. presence of words for
"overstay", "deportation", "denied", "criminal", "fraud",
"appeal", names of official notices, etc.) and prefer **over-
flagging** in early phases. False positives in early phases mean
"the user gets routed to an official source unnecessarily", which
is a much better failure mode than under-flagging.

## 7. Related documents

- `docs/ai/ANSWER_QUALITY_CONTRACT.md`
- `docs/ai/CITATION_AND_UNCERTAINTY_SCHEMA.md`
- `docs/ai/ANSWER_EXAMPLES.md`
- `docs/legal/AI_DISCLAIMER_DRAFT.md`
- `docs/legal/TERMS_OF_SERVICE_DRAFT.md`
- `docs/legal/PRIVACY_POLICY_DRAFT.md`
