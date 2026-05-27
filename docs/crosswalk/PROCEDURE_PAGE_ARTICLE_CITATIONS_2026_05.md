# Procedure Page and Article Citations - 2026.5

## Purpose

This document adds the first page/article citation layer for the 2026.5 Paradiso procedure crosswalk.

It is still documentation/crosswalk work. It is not a production data patch and it does not change AI answer generation.

## How to read this document

- `manual_page` means the physical PDF page in `docs/source-manuals/2026-05/stay_manual_2026_05.pdf` unless otherwise stated.
- `law_article` means the article number to verify on the official law.go.kr route before using it for metadata promotion.
- `support_level` distinguishes direct field support from contextual source support.
- `patch_readiness` remains conservative unless the source directly supports the future target field.

## Procedure citation matrix

| Procedure | Manual / guide citation | Law / rule citation | Support level | Patch readiness |
| --- | --- | --- | --- | --- |
| Foreigner registration | Stay manual p. 321 includes the integrated application/report form option for foreigner registration; status-specific sections also include registration document lists, e.g. H-1 registration on p. 517 | Immigration Control Act Art. 31; Enforcement Rule form basis to verify | contextual plus status-specific direct support | NEEDS_STATUS_SPECIFIC_PAGE |
| Extension of stay | Stay manual p. 5 lists extension fee; p. 6 explains passport-validity limits applied to extension; status-specific extension pages must be filled separately | Immigration Control Act Art. 25; Enforcement Rule Art. 72 for fees | contextual; status-specific documents pending | NEEDS_STATUS_SPECIFIC_PAGE |
| Change of status | Stay manual p. 5 lists change-of-status fee; p. 6 explains passport-validity limits applied to change of status; status-specific change pages must be filled separately | Immigration Control Act Art. 24; Enforcement Rule Art. 72 for fees | contextual; status-specific documents pending | NEEDS_STATUS_SPECIFIC_PAGE |
| Workplace change/addition | Stay manual p. 5 lists workplace change/addition fee; p. 6 references workplace change/addition as a procedure affected by passport validity; p. 676 gives a Top-Tier workplace-change example | Immigration Control Act Art. 21; Enforcement Rule Art. 72 for fees | contextual plus category-specific example | NEEDS_STATUS_SPECIFIC_PAGE |
| Passport or registration-information change | Stay manual p. 321 integrated application/report form includes change of information on registration; additional exact reporting page still needed | Immigration Control Act Art. 35 | contextual; exact reporting section pending | NEEDS_PAGE_CITATION |
| Residence/address change | Stay manual p. 321 integrated application/report form includes alteration of residence; p. 591 notes 15-day reporting issue in a regional visa context; separate address-change/fact-certificate manual still needs archive | Immigration Control Act Art. 36; Overseas Koreans Act Art. 6 for domestic residence-change reporting context | contextual plus category-specific example | NEEDS_ATTACHMENT_ARCHIVE |
| Electronic civil petition | Stay manual p. 299 and p. 526 show status/category examples using HiKorea electronic petition routes | HiKorea service page, procedure-dependent law basis | service/context only | DO_NOT_PATCH |
| Visit reservation | Stay manual p. 546 describes reservation guidance in overseas-Korean context; HiKorea reservation guide remains the service source | service guidance, not substantive legal basis | service/context only | DO_NOT_PATCH |
| Certificate issuance | Stay manual p. 5 includes fact-certificate fee row; separate address-change/fact-certificate manual still needs archive and page extraction | Immigration Control Act Art. 88; Enforcement Rule fee provisions; Overseas Koreans Act/Rule where applicable | contextual pending exact attachment | NEEDS_ATTACHMENT_ARCHIVE |
| Official forms | Stay manual p. 321 includes integrated application/report form; HiKorea forms directory is official forms source | form-dependent | form/context only | DO_NOT_PATCH |

## Citation notes by page

### Stay manual p. 5 - fee and procedure basis

The fee table records several procedure names that map to Paradiso procedure tabs: workplace change/addition, change of status, extension of stay, foreigner registration card issuance/reissuance, residence card issuance/reissuance, and certificates of fact. The same table cites Immigration Control Act Art. 87 and Enforcement Rule Art. 72, plus Overseas Koreans Act Enforcement Rule Art. 12.

Use this page for fee-source context only. Do not use it as a document-list source.

### Stay manual p. 6 - passport validity limit

This page explains that passport validity limits apply to status grant, extension of stay, change of status, and workplace change/addition procedures, with exclusions.

Use this page as common procedural context. Do not use it as a required-document source.

### Stay manual p. 7 - occupation and annual income reporting

This page cites Enforcement Rule Arts. 47 and 49-2 and explains occupation/annual income reporting duties for employment-capable statuses during registration and stay-permit procedures.

Use this only for occupation/income reporting crosswalk fields, not for universal document requirements.

### Stay manual p. 8 - school attendance reporting for minors

This page cites Enforcement Rule Arts. 47 and 49-2 and explains school attendance reporting for registered/resident foreign minors.

Use this only for minor/school-attendance reporting fields, not for universal adult procedure requirements.

### Stay manual p. 321 - integrated application/report form

This page contains the integrated application/report form with checkboxes for foreigner registration, extension of stay, change of status, workplace change/addition, alteration of residence, and change of information on registration.

Use this page for official form-option mapping and UI wording. Do not use it alone for required-document lists.

### Stay manual p. 517 - H-1 registration example

This page gives a status-specific registration example for H-1, including the requirement that persons intending to stay over 90 days register and listing H-1 registration documents.

Use this as evidence that registration document lists are status-specific and must not be universalized.

### Stay manual p. 591 - regional visa address-change context

This page notes a 15-day timing issue for residence/address reporting in a regional-visa context.

Use this as category-specific context only. The general address-change rule still requires the HiKorea address-change guide, Immigration Control Act Art. 36, and the address-change/fact-certificate manual.

### Stay manual p. 676 - Top-Tier workplace-change context

This page provides a Top-Tier workplace-change/addition reporting example, including a 15-day reporting rule and required documents for that specific track.

Use this as category-specific support only. Do not universalize it across all work statuses.

## Article anchors for future verification

| Topic | Article anchor | Official route |
| --- | --- | --- |
| Foreigner registration | Immigration Control Act Art. 31 | `https://www.law.go.kr/법령/출입국관리법` |
| Change of status | Immigration Control Act Art. 24 | `https://www.law.go.kr/법령/출입국관리법` |
| Extension of stay | Immigration Control Act Art. 25 | `https://www.law.go.kr/법령/출입국관리법` |
| Workplace change/addition | Immigration Control Act Art. 21 | `https://www.law.go.kr/법령/출입국관리법` |
| Change in registration information | Immigration Control Act Art. 35 | `https://www.law.go.kr/법령/출입국관리법` |
| Residence/place of stay change | Immigration Control Act Art. 36 | `https://www.law.go.kr/법령/출입국관리법` |
| Fees | Immigration Control Act Art. 87; Enforcement Rule Art. 72 | `https://www.law.go.kr/법령/출입국관리법`, `https://www.law.go.kr/법령/출입국관리법시행규칙` |
| Certificates of fact | Immigration Control Act Art. 88 | `https://www.law.go.kr/법령/출입국관리법` |
| Overseas Korean domestic residence change | Overseas Koreans Act Art. 6 | `https://www.law.go.kr/법령/재외동포의출입국과법적지위에관한법률` |

## What this enables

This citation layer enables the next data-readiness step: changing some procedure records from route-only status to page/article-cited status.

It does not yet enable direct data patching for required-document fields because status-specific pages still need to be filled for each visa/status record.

## Relation to law grounding

This PR is not the same as enriching law-grounded answers at runtime. It prepares the citation map that later backend/AI grounding PRs can use.

Runtime answer enrichment should be a separate implementation PR after the crosswalk has enough direct support and after audit/debug behavior is verified.
