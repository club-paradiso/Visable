# Official external-source augmentation — 2026-06

Accessed: 2026-06-28
Scope: bounded reconciliation of official sources beyond the registered 2026-06 visa and stay manuals.

## Decision

The central visa/stay manuals remain Paradiso's primary structured guidance. External sources are added only as supporting evidence, correction signals, official handoffs, nationality/KIIP enrichment, and mission-specific filing notes. No mission checklist becomes a global requirement.

When sources differ, Paradiso uses this order: (1) current legal text, (2) central MOJ/immigration services, (3) the competent overseas mission for local filing, and (4) government-affiliated reference material. The required mission caution is shown beside every applicable mission-source list.

## Central official sources inspected

| Source | Tier | Use in Paradiso |
|---|---:|---|
| [Korea Immigration Service — Nationality Division](https://www.immigration.go.kr/immigration/1550/subview.do) | 2 | Nationality category scope and authority handoff |
| [MOJ Online Civil Service — nationality affairs](https://mojminwon.moj.go.kr/minwon/2014/subview.do) | 2 | General/simplified/special naturalization, restoration, determination, loss/renunciation, interview-material handoff |
| [Soci-Net](https://www.socinet.go.kr/soci/main/main.jsp?MENU_TYPE=S_TOP_SY) | 2 | KIIP application, schedule, and status handoff |
| [KIS — immigrant social integration](https://www.immigration.go.kr/immigration/1518/subview.do) | 2 | KIIP purpose and cautious relationship to some stay/nationality procedures |
| [MOJ — social integration program](https://www.moj.go.kr/moj/369/subview.do) | 2 | Central KIIP policy handoff |
| [Korea Visa Portal](https://www.visa.go.kr/) | 2 | Pre-entry visa category/application-status handoff |
| [HiKorea](https://www.hikorea.go.kr/) | 2 | Post-entry stay, e-petition, and visit-reservation handoff |
| [Immigration Contact Center 1345](https://www.immigration.go.kr/moj/196/subview.do) | 2 | Multilingual official contact and routing |
| [Nationality Act — current official text](https://www.law.go.kr/LSW/LsiJoLinkP.do?languageType=KO&lsNm=%EA%B5%AD%EC%A0%81%EB%B2%95&paras=1) | 1 | Current legal-authority handoff |
| [Nationality Act amendment promulgated 2026-06-02](https://www.law.go.kr/lsInfoP.do?lsiSeq=286415&viewCls=lsRvsDocInfoR) | 1 | Correction signal only; effective 2026-12-03 and not treated as current law |

## Representative mission review

Ten official `overseas.mofa.go.kr` sources were recorded in `data/official_web_overlays.json`: United States, China, Japan, Vietnam, Philippines, Thailand, Mongolia, Uzbekistan, Canada, and Australia. Each record includes mission, page title, URL, visible source/update date (or a null date), accessed date, covered status types, local-only scope, appointment/submission notes, conflict state, and reflection decision.

All ten records have `globalRuleEligible: false`. Mongolia's list title/date mismatch and the absence of visible dates on the Canada and Australia pages are preserved as audit limitations; those records are used as handoffs, not copied requirements.

## Static audit classifications

- Already source-grounded: manual-backed visa/stay data and existing legal-search safety boundaries.
- Needs official source metadata: nationality sources, homepage official handoffs, mission overlay records.
- Needs wording improvement: “귀화 가능성 진단” and KIIP/assessment wording that could imply a determination.
- Needs cautious disclaimer: consular filing differences, KIIP recognition/exemption, future-effective law, and non-affiliation.
- Outdated or risky: the 2026-12-03 Nationality Act amendment if applied early; mission pages without visible dates; Mongolia's inconsistent list metadata.
- No action needed: canonical visa/stay requirements and Waymaker/Legal Research AI packet policy.

## Content intentionally not changed

- No central manual rule or manual review flag was removed.
- No embassy/consulate document was promoted to a universal requirement.
- No nationality eligibility, KIIP exemption, interview exemption, or approval outcome is determined.
- No uncaptured external webpage was placed in model context.
- Generated English remains product copy and is not presented as an official translation.

## Review note

The source registries and UI are reviewable, additive changes. A narrow legal/content review should recheck the future-effective Nationality Act record and the three mission records with date ambiguity before merge.
