# Procedure Packet Builder & Safe Application Typing Helper (2026-06)

## Product rationale

Paradiso is evolving from an "AI visa search service" into an
**official-source-based stay/residence administration preparation platform**.
The goal is not merely to *display* public data — it is to use official public
data to help users **prepare real immigration/residence procedures**.

This PR adds the first safe scaffold for that direction:

1. a reusable **Procedure Packet Builder** that turns the official-source data
   the project already curates into source-graded preparation packets;
2. an **Official Source Lens** so every packet states how strongly it is
   source-backed;
3. **checklist / preparation-memo / document grouping** behavior; and
4. a **safe 통합신청서 typing-helper scaffold** that explains what a user may
   need to prepare before manually typing the official Integrated Application
   Form — without storing or transmitting any personal data.

### Relationship to public-data best practice

Public data is most valuable when it **prepares a real administrative action**,
not when it is merely rendered. A packet answers the practical questions a
person actually has before visiting an office: who the procedure is for, when to
apply, what to bring, what is conditional, what fees may apply, which channel to
use, what official sources support the guidance, what remains uncertain, and
what the next action is.

## What this builds on (and does not redo)

It reuses existing infrastructure: the source-confirmed structured manual
requirements (`backend/structured_requirements.py` →
`structured_requirements_2026_06_01.json`), the per-visa procedure document
lists and `feeInfo` in `visa_data.json`, and the public-safe source-status
conventions. It does **not** touch answer synthesis gates, the law/source
grounding architecture, the precedent scaffold, manual refresh, model/provider
policy, or the static visa result contract.

## Data diagnosis (where procedure content lives today)

* **Procedure documents** are modeled in two places:
  * `visa_data.json → procedures.{registration, extension, statusChange,
    activitiesOutsideStatus, workplaceChange, reentry, statusGrant,
    visaIssuance}.requiredDocs` — already grouped into
    `commonDocs/requiredDocs/conditionalDocs/additionalDocs`, but with
    `manualRefs` that are mostly `needs_review` / `auto_extracted` (not
    source-confirmed), and sometimes only a placeholder string like
    `"매뉴얼 확인 필요"`.
  * `structured_requirements_2026_06_01.json` — the **source-confirmed** layer
    (HIGH + `STRUCTURED_EVIDENCE_READY`), with manual page ranges. Today this is
    **18 entries**, covering only `registration` and `extension` for ~13 status
    codes (D-1/2/5/6/7/8, E-2/3/4/5/6/7/10).
* **Fees** are modeled procedure-specifically in
  `feeInfo.paradisoDefault202605.procedures.{foreignRegistration, extension,
  statusChange, grantStatus, visaIssuance}` but are explicitly
  `verified: false / needsManualReview: true` → display metadata only.
* **Timing / deadlines** are not source-confirmed (only coarse `period` and a
  `hikorea_task_type` string exist) → represented as source-limited.
* **HiKorea / reservation / office**: only a `hikorea_task_type` string; no
  reservation/office source data → represented as source-limited.
* **통합신청서 / 별지 제34호 서식**: present as a *document name* in
  `visa_data.json` (67×), `doc_master.json` (`doc_app_form` =
  "Integrated Application Form / 법정 서식(별지)"), and the structured layer
  (24×) — but **no official-form field structure** is parsed anywhere.

So the builder can safely produce source-confirmed document packets for
`registration`/`extension` on the covered codes, contextual packets where
`visa_data` has real (needs-review) document lists, and clearly-limited packets
everywhere else — never inventing content.

## The 통합신청서 in two layers (official form vs typing helper)

The 통합신청서 (Integrated Application Form, the 출입국관리법 시행규칙
**별지 제34호 서식**) is an **official immigration form/document**, not an
invented helper concept. The builder treats it on two separate layers:

1. **As an official document.** When a procedure's source data lists 통합신청서
   / 별지 제34호, the packet surfaces it as a real `PacketDocument`:
   * grouped under `commonDocs` (it is a universal official form),
   * with its official name preserved (`"통합신청서(별지 제34호 서식)…"`),
   * flagged `isOfficialForm: true` with a note tying it to the Enforcement Rule
     annex form,
   * source-backed by whatever manual/enforcement-rule source supports it
     (manual page ref → `source_confirmed`; needs-review visa_data ref →
     `contextual`).
   It is **never** reduced to a placeholder and **never** replaced by the helper.
2. **As a typing helper.** Separately, `applicationTypingHelper` explains what a
   user should prepare before manually typing the official form. It
   *references* the official 통합신청서 (name + Enforcement-Rule basis) and is
   `typing_guide_only` — it never fills, submits, or replaces it.

> Full official-form **field** extraction from the Enforcement Rule annex form
> is **not** done here (no such field map exists in current data). Field-level
> guidance is therefore generic and marked source-limited; exact-field
> extraction is a documented follow-up.

## Packet model

```
ProcedurePacket {
  packetId, packetType, statusCode, exactStatusCode, parentStatusCode,
  titleKo, titleEn?, userScenarioSummaryKo?,
  applicability { summaryKo, conditions[], limitations[] },
  timing { triggerEventKo?, stayPeriodHintKo?, sourceBacked, limitationKo? },
  documents { commonDocs[], requiredDocs[], conditionalDocs[], additionalDocs[],
              sourceBacked, limitationKo? },
  fees { items[], sourceBacked, limitationKo? },
  channels { hikoreaReservation?, immigrationOfficeVisit?, limitationKo? },
  officeAndJurisdiction { summaryKo?, limitationKo? },
  riskFlags[],
  sourceLens { overallLevel, overallLabelKo, sources[], finalAgencyDiscretionKo, limitationKo? },
  applicationTypingHelper { ... typing_guide_only ... },
  nextActions[], finalAgencyNoteKo
}
PacketDocument { nameKo, noteKo?, conditionKo?, isOfficialForm, sourceBacked, sourceRefs[] }
PacketSource  { sourceFamily, sourceNameKo, versionDate?, pageRange?, article?, url?, evidenceLevel }
```

Rules enforced: no invented documents/fees/deadlines/channels; missing coverage
→ a single concise `limitationKo` (never repeated placeholder rows); exact
sub-code preserved (`exactStatusCode`), parent used only to resolve the record;
document conditionality preserved (`(해당자)` → `conditionalDocs`).

## Supported packet types

| packet type | visa_data key | source today |
|---|---|---|
| `foreigner_registration` | `registration` | source_confirmed (covered codes) / contextual / limited |
| `extension` | `extension` | source_confirmed (covered codes) / contextual / limited |
| `status_change` | `statusChange` | contextual / limited |
| `activities_outside_status` | `activitiesOutsideStatus` | contextual / limited |
| `workplace_change` | `workplaceChange` | contextual / limited |
| `reentry_permit` | `reentry` | contextual / limited |
| `status_grant` | `statusGrant` | contextual / limited |
| `visa_issuance` | `visaIssuance` | contextual / limited |

## Official Source Lens scale

| level | public Korean label | meaning |
|---|---|---|
| `source_confirmed` | 공식근거 직접 확인 | official source directly supports the item |
| `contextual` | 관련 공식근거 있음 | related official source exists, needs review |
| `limited` | 공식근거 제한 | coverage incomplete / interpretation needed |
| `unavailable` | 공식근거 확인 불가 | no official source in current data |
| `final_agency_discretion` | 관할기관 최종심사 필요 | final decision is the office's |

Raw developer codes (`bad_response`, `unsupported`, `not_attempted`,
`planned_not_wired`, `needs_review`, `auto_extracted`, …), raw bodies, and stack
traces are never present in packet output (asserted by tests).

## Application typing helper scope

`mode: "typing_guide_only"`, `privacyMode: "no_storage_no_llm_for_personal_data"`.
Generic, non-personal field groups (applicant identity, current stay status,
request type, address/contact, workplace/school/activity, passport/ARC
reference, accompanying family, signature/date) — each field carries an
explanation, a `requiredness`, `doNotStore`, and "type this from your official
document" guidance. **No field accepts or stores a value.** It references the
official 통합신청서 (별지 제34호 서식) and never replaces, fills, submits, or
predicts approval.

## Privacy and safety guardrails

The builder/helper does **not**: ask for or collect passport/ARC numbers,
phone, address, employer, school ID, or any personal identifier; store or log
personal data; send personal data to an LLM; auto-fill or submit official forms;
generate a completed official form; predict approval; or present a
source-limited packet as complete.

Required safety note carried on every packet and helper (`finalAgencyNoteKo`):

> 이 패킷과 통합신청서 작성 도우미는 신청 준비를 돕는 안내이며, 실제 허가 여부와
> 제출 가능 여부는 관할 출입국·외국인관서 및 공식 신청서 기준에 따릅니다.

## API

* `GET /api/procedure-packet?status=<code>&procedure=<key>&locale=ko` — returns a
  packet. Non-personal inputs only; deterministic; no LLM; public-safe labels;
  invalid procedure → clean `400 unsupported_procedure`.
* `GET /api/visas/{status_code}/packets` — lists buildable packets for a status.

No endpoint accepts application field values or stores any personal data.

## Tests added

`backend/tests/test_procedure_packet_builder.py` (36 tests): packet model +
sub-code preservation + limited-not-fake; document grouping (no placeholder /
"문서명 미상" / "비고 정보 없음" rows; conditional preserved); source lens +
no-raw-diagnostics; procedure-key mapping; typing helper (mode/privacy, field
guidance not values, personal fields `doNotStore`, references official form,
no completed form); regression fixtures (D-2/E-7/F-6/H-1/G-1); the 통합신청서
official-document tests (appears as a `PacketDocument`, not suppressed, not
replaced by the helper, grouped as a common official form, manual-/limited-
backed source lens); and API endpoint behavior.

## What this PR intentionally does NOT do

* No official-form auto-fill, no form generation, no PDF export.
* No personal-data intake, storage, logging, or LLM processing of identifiers.
* No approval prediction.
* No official-form **field** extraction from the Enforcement Rule annex form
  (field guidance is generic + source-limited for now).
* No account system, no large frontend/modal redesign, no multilingual generator.

## Known limitations

* Source-confirmed documents exist only for `registration`/`extension` on ~13
  codes; all other procedures are contextual or limited by data, not by design.
* Fees are display metadata (`verified:false`) → never `source_confirmed`.
* Timing/deadlines, reservation, and exact jurisdiction are source-limited.
* The 통합신청서 field guide is generic (official field map not parsed yet).
* No frontend packet preview is included in this PR.

## Follow-up PRs

1. Packet preview UI (compact, public-safe) — deferred from this PR.
2. Document **issuer / "where to get this document"** mapping (using
   `doc_master.json`).
3. Deadline & overstay risk checker (source-backed timing).
4. Safe client-side typed **draft** mode after a privacy review (still no
   server storage / no LLM for personal data).
5. Official 통합신청서 **field** extraction from the Enforcement Rule annex form
   (별지 제34호 서식) → upgrade helper field guidance from limited to
   source-confirmed.
6. Multilingual notice generator from source-backed packets.
7. Institution mode (universities / employers / counselors) — no personal data.
8. Exportable checklist (NOT the official form) after review.

## Safety note

This feature prepares administrative action; it does not perform it. Every
packet and helper states its source lens and carries the final-agency note.
Source-limited coverage is shown honestly as limited/unavailable, never as fake
documents, fake fees, fake deadlines, or raw diagnostics. The official
통합신청서 is treated as an official document and is never auto-filled,
submitted, or replaced by the typing helper.
