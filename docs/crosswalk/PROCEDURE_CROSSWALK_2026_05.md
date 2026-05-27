# Procedure Crosswalk - 2026.5

## Purpose

This document starts the 2026.5 Paradiso procedure crosswalk. It maps common user-facing procedures to official HiKorea/manual/law sources before any production data correction.

This is not a data patch. It does not modify `visa_data.json`, `backend/data/visas.json`, frontend behavior, verification metadata, or AI grounding behavior.

## Source roles

| Role | Use |
| --- | --- |
| official_manual | Primary source for detailed document/procedure requirements. |
| core_procedure_source | Official HiKorea procedure page for user-facing procedural guidance. |
| canonical_legal_source | law.go.kr legal basis, duties, fees, penalties, and authority. |
| official_forms_source | Official application/form names and form directory. |
| supporting_service_source | UI/navigation guidance such as e-petition and reservation flows. |

## Procedure summary matrix

| Procedure | Primary HiKorea source | Manual source | Legal/source basis | Crosswalk status | Patch readiness |
| --- | --- | --- | --- | --- | --- |
| Foreigner registration | `alien_registration` | `stay_manual_pdf` | `immigration_act`, `immigration_rule` | source route recorded; exact page/article pending | NEEDS_PAGE_CITATION |
| Extension of stay | `extension_of_stay` | `stay_manual_pdf` | `immigration_act`, `immigration_rule` | source route recorded; exact page/article pending | NEEDS_PAGE_CITATION |
| Change of status | `change_of_status` | `stay_manual_pdf` | `immigration_act`, `immigration_rule` | source route recorded; exact page/article pending | NEEDS_PAGE_CITATION |
| Workplace change/addition | `workplace_change` | `stay_manual_pdf` | `immigration_act`, `immigration_rule` | source route recorded; exact page/article pending | NEEDS_PAGE_CITATION |
| Passport/registration-info change | `passport_change` | `stay_manual_pdf` | `immigration_act`, `immigration_rule` | source route recorded; exact page/article pending | NEEDS_PAGE_CITATION |
| Residence/address change | `address_change` | `stay_manual_pdf`, `address_change_certificate_manual` | `immigration_act`, `immigration_rule`, `overseas_koreans_act` | source route recorded; exact page/article pending | NEEDS_ATTACHMENT_ARCHIVE |
| Electronic civil petition | `electronic_petitions` | `stay_manual_pdf` | procedure-dependent | service route recorded; field-level authority pending | DO_NOT_PATCH |
| Visit reservation | `reservation_guide` | none | service guidance | service route recorded | DO_NOT_PATCH |
| Certificate issuance | `certificate_issuance` | `address_change_certificate_manual` | `immigration_act`, `immigration_rule`, `overseas_koreans_rule` | source route recorded; exact source pending | NEEDS_ATTACHMENT_ARCHIVE |
| Official forms | `forms_directory` | procedure-dependent | form-dependent | source route recorded | DO_NOT_PATCH |

## Interpretation rules

1. A HiKorea procedure page can support user-facing procedure explanations and UI routing.
2. A manual page is required before patching required-document fields.
3. A law article is required before patching legal-basis, duty, fee, penalty, or authority fields.
4. A service page such as e-petition or reservation is not enough to patch eligibility or required-document fields.
5. Conditional or sub-code-specific requirements must stay conditional or sub-code-specific.
6. Any conflict between law, manual, and HiKorea guidance must be flagged as `LAW_MANUAL_CONFLICT_REVIEW`.

## Next extraction pass

The next PR should fill exact pages/sections for:

1. foreigner registration,
2. extension of stay,
3. change of status,
4. workplace change/addition,
5. passport/registration-information change,
6. residence/address change,
7. certificate issuance.

Only after page/article coverage is filled should scoped production data correction begin.
