# Paradiso & Paradiso.ai — Data Retention and Logging Notes (DRAFT)

> **STATUS: DRAFT.** This document is a documentation-only working draft.
> It captures what the current repository actually shows about data
> handling, and lists the operator-specific questions that must be
> answered before the Privacy Policy draft can be finalized.
>
> Producing this draft did not enable, change, or roll out any
> collection, logging, retention, analytics, cookie, tracking, email,
> SMS, auth, or storage behavior.

---

## 1. Purpose

This draft enumerates what we *can* say about data retention based on
the code and documentation in this repository, and what we *cannot*
say without operator-specific input. It is intended to be used as a
worksheet by the operator and reviewing counsel when finalizing
`docs/legal/PRIVACY_POLICY_DRAFT.md`.

## 2. Scope

In scope:

- Reminder data stored in the user's own browser.
- AI question data submitted to the Paradiso.ai backend.
- Server-side logs at the hosting / backend layer.
- Third-party AI / API processor retention, if applicable.
- Future opt-in channels (email / SMS / push / calendar sync) and
  their implications.

Out of scope:

- Detailed log configuration of any specific cloud provider that has
  not yet been chosen by the operator.
- Tracking, analytics, or marketing pipelines (none exist in the
  current build).

## 3. What the repository currently shows

### 3.1 Reminder feature — client-side only

The reminder feature is presently scoped to the user's own browser. It
uses `localStorage` for persistence and offers a calendar export
(downloadable `.ics`-style file) that the user actively chooses to
generate. There is, in the current build:

- no server-side reminder store
- no push notification channel
- no email channel
- no SMS channel
- no calendar account sync

User-entered reminder notes may contain personal or sensitive
information (status expiry dates, case identifiers, family
circumstances). Even though that information never leaves the user's
browser in the current build, the design should continue to treat it
as potentially sensitive.

### 3.2 AI question data — sent to backend

When the user submits a question to Paradiso.ai, the question text is
sent to the backend in order to be answered. Free-text questions in
this domain are inherently likely to contain personal or sensitive
information about the user's immigration / residence situation. Data
minimization should be the default policy in the product UI and in any
production disclosure.

### 3.3 Law grounding — disabled by default, citation verification partial

Law grounding remains disabled by default in the current build and is
not considered production-ready. Citation verification is partial and
not fully wired. These facts are reflected in the AI Disclaimer draft
and should be reflected in any production privacy / terms surface.

### 3.4 Tracking / analytics — none in the current build

The repository does not include analytics, advertising, marketing
pixels, A/B testing infrastructure, or cookie-based tracking
integrations.

## 4. Operator-specific questions (unanswered)

The following questions must be answered, in writing, before the
Privacy Policy draft can be finalized. Each answer should land both in
this file and in the corresponding section of the privacy notice.

### 4.1 Hosting / CDN logs

- `[OPERATOR: hosting / CDN provider]`
- `[OPERATOR: do raw access logs include IP address and user agent?]`
- `[OPERATOR: retention period for access logs]`
- `[OPERATOR: who has access to raw access logs]`
- `[OPERATOR: are access logs forwarded to any third party (e.g. log SaaS)?]`

### 4.2 Backend application logs

- `[OPERATOR: does the backend write request logs to disk or stdout?]`
- `[OPERATOR: do those logs include the user's question text?]`
- `[OPERATOR: do those logs include the answer returned to the user?]`
- `[OPERATOR: retention period for backend logs]`
- `[OPERATOR: are backend logs centralized in a log management system?]`
- `[OPERATOR: who has access to backend logs]`

### 4.3 AI / LLM provider retention

If the production deployment forwards the question to a third-party AI
provider:

- `[OPERATOR: name of third-party AI / LLM provider]`
- `[OPERATOR: data region]`
- `[OPERATOR: is the request excluded from provider-side training, per contract?]`
- `[OPERATOR: provider-side retention of prompts]`
- `[OPERATOR: provider-side retention of completions]`
- `[OPERATOR: provider-side abuse-monitoring retention]`
- `[OPERATOR: link to the provider's data-handling terms]`

If no third-party AI provider is used in production, the operator
should record that fact here so that the Privacy Policy can say so
plainly instead of leaving placeholders.

### 4.4 Error / diagnostic telemetry

- `[OPERATOR: is any error-reporting service (e.g. Sentry-style) used?]`
- `[OPERATOR: if so, what payload is captured and for how long?]`
- `[OPERATOR: who has access?]`

### 4.5 Backups

- `[OPERATOR: are backups taken of logs or any user-facing data?]`
- `[OPERATOR: backup retention]`
- `[OPERATOR: backup access controls]`

## 5. Future channels and the opt-in requirement

The following channels do **not** exist in the current build and must
**not** be enabled without a prior, channel-specific opt-in flow and a
corresponding update to the Privacy Policy and the AI Disclaimer:

- email reminders or email notifications
- SMS reminders or SMS notifications
- push notifications
- calendar account sync (as opposed to one-shot `.ics` export)
- account-based server-side reminder storage
- analytics, A/B testing, or marketing pixels

If any of these are added, the operator must, **before** enabling them:

1. Introduce a clear, granular, channel-specific opt-in surface in the
   product UI.
2. Update the Privacy Policy and the AI Disclaimer to describe the new
   data flow, retention, third-party processors, and cross-border
   processing implications.
3. Update this file's "what the repository currently shows" section to
   reflect the new reality, so this document stays an honest mirror of
   the codebase.

## 6. Recommended retention-minimization policy

The product team's working stance, pending operator decisions, is:

- **Default to not logging** the user's question text and the assistant's
  answer text in any long-lived store, beyond what is strictly required
  to operate the service.
- **Default to short retention** (single-digit days) for any operational
  logs that incidentally contain question text or other personal data.
- **Default to no analytics, no cookies, no tracking** in the absence of
  a specific, documented need approved by counsel.
- **Default to data minimization** in the AI input UI itself — encourage
  the user not to paste identifiers or other sensitive content that the
  question does not actually require.
- **Default to in-browser-only** for reminder data unless and until a
  specific, opt-in server-side channel is approved and disclosed.

These defaults are recommendations, not facts about the current
deployment. They become facts only when the operator confirms them and
documents them in the production privacy notice.

## 7. Cross-references

- `docs/legal/PRIVACY_POLICY_DRAFT.md`
- `docs/legal/TERMS_OF_SERVICE_DRAFT.md`
- `docs/legal/AI_DISCLAIMER_DRAFT.md`
- `docs/audits/POST_PR_95_106_MAIN_STATE_AUDIT.md` (main-state
  readiness context that motivated this draft pass)

---

## Launch checklist

Before the Privacy Policy can be finalized, **all** of the following
must be true:

- [ ] Every `[OPERATOR: ...]` question in section 4 has been answered
      in writing.
- [ ] Section 5 ("Future channels and the opt-in requirement") still
      describes reality, i.e. no channel listed there has been silently
      enabled.
- [ ] The recommended retention-minimization defaults in section 6
      have either been adopted as operator policy or been explicitly
      overridden, with the override reflected in the Privacy Policy.
- [ ] Law grounding remains disabled by default unless a separate
      production-readiness review for that feature has been merged and
      the AI Disclaimer and Privacy Policy have been updated to match.
- [ ] Citation verification limitations are still disclosed
      accurately in the AI Disclaimer.
- [ ] This file has been re-read end-to-end after operator answers
      land, to confirm it still matches the deployed reality.
