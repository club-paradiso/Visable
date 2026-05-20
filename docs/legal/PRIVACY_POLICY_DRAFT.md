# Paradiso & Paradiso.ai — Privacy Policy (DRAFT)

> **STATUS: DRAFT.** This document is a documentation-only working draft.
> It has **not** been reviewed by qualified legal counsel and must not be
> published as a production privacy policy without independent legal /
> data-protection review and operator-specific completion of every
> `[OPERATOR: ...]` placeholder.
>
> Producing this draft did not enable, change, or roll out any data
> collection, logging, analytics, cookie, tracking, email, SMS, auth, or
> server-side storage behavior. Law grounding remains disabled by default
> and is not production-ready.

---

## 1. Purpose

This draft describes, in plain language, what kinds of information the
Paradiso website (immigration / stay administration information access
platform) and the Paradiso.ai feature (AI-assisted administrative
information tool) may process when offered to end users. It is meant to
let an operator and reviewing counsel see the actual data surface of the
product as it exists in this repository, and to call out every place
where an operator-specific fact is currently unknown.

This draft is **not** itself a privacy notice that should be linked from
the live product. A production privacy notice should be derived from
this draft only after legal review and after the operator's identity,
jurisdiction, hosting, and third-party processor choices are confirmed.

## 2. Scope

This draft covers:

- The Paradiso website (currently a static `index.html` plus supporting
  assets) that lets users browse immigration / stay administration
  information.
- The Paradiso.ai assistant feature (currently a separate static page
  `ai.html` and a `backend/` FastAPI service) that answers
  administrative information questions.
- The reminder feature, which is presently scoped to the user's own
  browser (`localStorage`) plus optional calendar export, with no
  server-side push, email, or SMS.

This draft does **not** cover:

- Any future server-side user accounts, email/SMS notification, calendar
  sync, or analytics integrations. Any such feature would require a
  separate opt-in flow and a corresponding update to this policy before
  launch.
- Third-party websites that the product may link to (for example
  official government portals). Their privacy practices are their own.

## 3. Who is the operator (placeholder)

- `[OPERATOR: legal entity name]`
- `[OPERATOR: registered address]`
- `[OPERATOR: jurisdiction of establishment]`
- `[OPERATOR: data protection contact email / form URL]`
- `[OPERATOR: data protection representative, if required by applicable law]`

Paradiso is **not** a law firm, an administrative scrivener firm, a
public agency, or an official government decision-maker. It is an
information access and AI-assisted information tool. See the Terms of
Service draft and the AI Disclaimer draft.

## 4. Categories of data potentially processed

The categories below describe what the product *can* touch given how it
is built today. They are listed so that a reviewer can see the actual
data surface, not to imply that every category is actively collected on
a server.

### 4.1 Information the user enters into the AI assistant

When a user submits a question to Paradiso.ai, the question text is
sent to the backend (`/api/ask` style endpoint) so that an answer can be
produced. Free-text questions in this domain can contain personal or
sensitive information, including but not limited to:

- immigration / residence status, visa code, period of stay
- employment, employer, school, or program details
- nationality, family relationships, dependents
- prior administrative or legal history relevant to status
- contact or location hints volunteered by the user

Users should be told, in the product UI as well as in the production
privacy notice, **not** to send information that is more sensitive than
the question actually requires. Data minimization is the intended
default policy.

### 4.2 Information the reminder feature stores in the browser

The reminder feature currently writes reminder entries to the user's
own browser `localStorage`. These entries may include:

- a reminder title or label
- a date / time
- free-text notes the user has typed
- a derived calendar export (e.g. `.ics`) that the user chooses to
  download or open

Because users may type personal or sensitive information into reminder
notes (for example a status expiry date, a case number, or a family
member's situation), reminder data must be treated as potentially
sensitive even though it lives only in the user's browser.

This data is **not** transmitted to the Paradiso backend in the current
build. If a future version adds server-side reminders, push
notifications, email or SMS reminders, or calendar account sync, that
change requires its own opt-in flow and its own update to this policy
before launch.

### 4.3 Technical / request information

When the user loads the website or sends an AI question, basic
technical information is normally observable by whatever infrastructure
is in front of the service (for example a hosting provider or a CDN).
This typically includes:

- IP address
- approximate user agent / browser
- request timestamps
- request URL path

The exact retention, logging behavior, and operator visibility of this
information depends on the hosting and reverse-proxy configuration that
the operator actually deploys.

- `[OPERATOR: hosting / CDN provider(s)]`
- `[OPERATOR: whether access logs are retained, and for how long]`
- `[OPERATOR: who inside the operator can view raw logs]`

### 4.4 Information returned by third-party AI / API providers

If the deployed backend forwards the user's question to a third-party
AI provider in order to generate an answer, that provider will receive
the question text and may process it under its own privacy and
retention rules.

- `[OPERATOR: name(s) of any third-party AI / LLM API provider used in production]`
- `[OPERATOR: data region used at that provider, if configurable]`
- `[OPERATOR: link to that provider's data-handling / enterprise terms]`
- `[OPERATOR: whether prompts and answers are excluded from provider-side training, per contract]`

If the production deployment does **not** use a third-party AI API, the
corresponding sections of the production policy should say so plainly.

### 4.5 Public data, official manuals, and law-grounding metadata

Paradiso uses information drawn from official manuals, public data,
internally normalized data, and law-grounding metadata in order to
answer questions. These sources are not personal data of the user;
they are reference content about administrative rules and procedures.

Law grounding remains **disabled by default** in the current build and
is not considered production-ready. Citation verification is partial
and not fully wired. See the AI Disclaimer draft.

## 5. Purposes of processing

Where personal data is processed at all, the intended purposes are
limited to:

- responding to the user's question or interaction
- letting the user manage their own reminders in their own browser
- diagnosing errors and abuse on the service
- meeting legal obligations that apply to the operator

The product is **not** designed, in the state captured by this
repository, for marketing, advertising, profiling, behavioral
targeting, or sale of personal data.

## 6. Legal basis (placeholder)

The applicable legal basis for processing depends on the operator's
jurisdiction.

- `[OPERATOR: legal basis for processing under applicable law — e.g. consent, legitimate interest, performance of a service the user requested, legal obligation]`
- `[OPERATOR: jurisdiction-specific rules that apply — e.g. PIPA (KR), GDPR (EU/EEA), other]`

Counsel review must confirm these before the policy is published.

## 7. Retention (placeholder)

The current product surface is intentionally small. However, retention
behavior depends on what the operator actually configures at the
hosting, backend, and AI-API layers. The operator must determine and
disclose:

- `[OPERATOR: how long server access logs are kept]`
- `[OPERATOR: how long, if at all, AI prompts and answers are kept server-side]`
- `[OPERATOR: how long any error / diagnostic logs are kept]`
- `[OPERATOR: retention rules at any third-party AI / API provider]`

See `docs/legal/DATA_RETENTION_AND_LOGGING_NOTES.md` for the operator
questions that need to be answered before this section can be filled in.

Reminders stored in the user's own `localStorage` are kept until the
user clears them, clears their browser storage, or uses a different
browser or device.

## 8. Sharing and third-party processors

The categories of recipients that may exist in a production deployment
include:

- the hosting / CDN provider — `[OPERATOR: name]`
- the third-party AI / API provider, if used — `[OPERATOR: name]`
- the operator's own staff with a defined need to access the data
- public authorities, where the operator is legally required to comply

The product is **not** designed to sell personal data or to share it
with advertising networks.

## 9. Cross-border processing (placeholder)

If a third-party AI / API provider processes the user's question text
outside the operator's home jurisdiction, that constitutes cross-border
transfer of personal data and must be disclosed.

- `[OPERATOR: countries / regions where AI API processing occurs]`
- `[OPERATOR: safeguards used for cross-border transfer — e.g. standard contractual clauses, adequacy decision, user consent]`

If no third-party AI / API is used in production, the operator should
state that clearly.

## 10. User rights and deletion requests (placeholder)

Depending on the applicable law, users may have rights such as access,
correction, deletion, restriction, portability, and objection.

- `[OPERATOR: how a user can submit a request — e.g. email address, form URL]`
- `[OPERATOR: identity verification approach]`
- `[OPERATOR: target response time]`

Because the current product does not maintain user accounts, deletion
requests in practice cover server-side logs and any retained AI
prompt/answer records — not in-browser reminder data, which the user
can delete themselves by clearing their own browser storage.

## 11. Security

The operator is responsible for the security of the production
deployment, including transport encryption, access controls on logs
and any AI-API admin consoles, and incident response.

- `[OPERATOR: security contact]`
- `[OPERATOR: breach-notification procedure]`

## 12. Children

The product is general-information software about immigration /
administrative procedures. It is not designed for children, and a
production privacy notice should state the operator's age policy
explicitly.

- `[OPERATOR: minimum age policy]`

## 13. Changes to this policy

A production version of this policy will need a "last updated" date and
a description of how material changes will be communicated to users.

- `[OPERATOR: how policy changes will be announced]`

## 14. Contact

- `[OPERATOR: privacy contact email or form]`
- `[OPERATOR: postal contact, if required]`

---

## Launch checklist

Before this draft can be promoted to a production privacy notice,
**all** of the following must be true:

- [ ] Independent legal / data-protection review has been completed by
      qualified counsel in the operator's jurisdiction.
- [ ] Every `[OPERATOR: ...]` placeholder above has been filled in with
      a confirmed fact, or the corresponding section has been removed
      because the fact does not apply.
- [ ] The operator has confirmed which third-party AI / API providers,
      if any, are used in production, and the cross-border section
      reflects reality.
- [ ] The hosting / CDN log retention and access policy is documented
      and reflected in section 7.
- [ ] The user-rights / deletion contact channel actually exists and
      has been tested end-to-end.
- [ ] The product UI links to the published policy from the relevant
      surfaces (homepage footer, AI page, reminder feature).
- [ ] The AI Disclaimer draft has also been finalized and linked.
- [ ] Any future feature that would add tracking, analytics, cookies,
      email, SMS, push, or server-side user storage has its own opt-in
      flow and its own policy update merged **before** that feature is
      enabled in production.
- [ ] Law grounding is still gated behind the existing disable-by-
      default flag, or, if enabled, a corresponding update to the AI
      Disclaimer draft and to this policy has been merged first.
