# Electronic-service fee eligibility audit — 2026-09-25

## Scope

Visable previously attached the Enforcement Rule Article 74(2) 20% electronic-filing reduction directly to generic fee rows. That made the UI advertise the reduction even when the applicant's status or change-of-status route is not eligible for HiKorea electronic filing.

This audit separates the statutory reduction from operational electronic-service eligibility.

## Authoritative source

- **전자민원 대상 업무** (Korea Immigration Service / Korean Law Information Center)
- Checked: 2026-09-25
- Source: https://www.law.go.kr/LSW/flDownload.do?bylClsCd=200201&flSeq=151064273

## Eligibility matrix implemented

| Procedure | Electronic filing rule used by Visable |
| --- | --- |
| Ordinary extension of stay | Eligible except D-3, D-8, E-7, F-2, F-6, G-1; F-1 is listed only as partially eligible, so generic F-1 fails closed |
| Change of status | D-4 -> D-2; H-2 -> F-4-24/25/27/28; E-9/E-10/H-2 -> E-7-4 or E-7-4R |
| Workplace change/addition permit | E-9 only |
| Re-entry permit | All statuses |

The official table separately lists an extension for departure as eligible for all statuses. Visable's ordinary `extension` procedure is not treated as that special departure procedure.

## Runtime rule

A fee may retain `online_reduction.rate = 0.2` as the statutory fee rule. The UI may render that reduction only when `electronicServiceEligibility(...).eligible === true`.

For partial or under-specified cases, especially generic F-1 and status-change requests without a target status, Visable fails closed and does not advertise the reduction.

## Regression coverage

The fee suite checks positive and negative eligibility across extension, change of status, workplace change and re-entry. It also verifies that:

- F-6-1 extension keeps the KRW 30,000 base fee but does not show a 20% online reduction.
- G-1 extension does not show the reduction.
- D-2 extension still shows the reduction.
- Waymaker Quick Answer and its handoff payload do not reintroduce the suppressed F-6 discount.
