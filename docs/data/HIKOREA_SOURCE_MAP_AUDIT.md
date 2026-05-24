# HiKorea & Korea Immigration Service — Source Map Audit

**Date:** 2026-05-24
**Branch:** `audit/hikorea-source-map`
**Author:** AI audit — human/operator review required before any production change
**Scope:** Public information surfaces only. No login-walled, personal-data, or authenticated pages were inspected or proposed for ingestion.

---

## 0. Purpose and non-goals

Paradiso's current source-of-truth set is tightly scoped to visa/status records derived from the 2026.5 Ministry of Justice manuals plus a small set of curated reference artifacts (`visa_data.json`, `doc_master.json`, designated medical institutions list, jobcode master, agent registry, source registry). This audit prepares Paradiso to expand official-source coverage from "visa/status only" to a broader set of resident-foreigner workflows.

This document is the **planning artifact**. It does not:

- modify any user-facing data (`visa_data.json`, `doc_master.json`, etc.);
- enable any new scraping, fetcher, or ingestion job;
- propose automating any personal-data flow (e-Application submission, reservation booking, certificate issuance);
- attempt to bypass login, CAPTCHA, rate limits, or HiKorea access controls;
- promote any HiKorea or Immigration Service page to authoritative Paradiso content;
- introduce new runtime dependencies, packages, or env vars.

It produces three artifacts only:

1. `docs/data/HIKOREA_SOURCE_MAP_AUDIT.md` (this file)
2. `docs/data/HIKOREA_SOURCE_SCHEMA_PROPOSAL.md`
3. `data/sources/hikorea_source_catalog.example.json` (illustrative skeleton, not production data)

All URLs in this audit are treated as **candidate landings to be operator-verified before any retrieval**. No live fetch was performed.

---

## 1. Source hierarchy proposal for Paradiso

Today Paradiso's effective hierarchy (see `docs/EXTERNAL_SKILLS_AND_LEGAL_GROUNDING_STRATEGY.md` §3) is:

1. Official current law/regulations (법제처 / 국가법령정보센터)
2. Official government / HiKorea guidance
3. Visa/stay civil manuals (2026.5 Ministry of Justice PDFs)
4. Public data sources
5. Paradiso internal normalized data
6. LLM synthesis (never authoritative)

For the expanded scope, the hierarchy needs more granularity because HiKorea publishes a mixture of statute references, guide pages, FAQs, and operational portals. Proposed refinement:

| Tier | Source class | Examples | Why this tier |
|---|---|---|---|
| **T1 — Statute** | Statute, enforcement decree, enforcement rule, ministerial notice (고시) | 출입국관리법, 국적법, 재외동포의 출입국과 법적 지위에 관한 법률, 난민법 + enforcement rules | Legally binding text; versioned by amendment date |
| **T2 — Official manual** | Ministry of Justice published guide manuals (PDF) | 사증발급 안내매뉴얼 2026.5, 외국인체류 안내매뉴얼 2026.5 | Authoritative operational interpretation by the issuing authority |
| **T3 — Authority notice** | Dated notices, press releases, 공지사항, 보도자료 from MoJ Immigration HQ / HiKorea | HiKorea 공지사항, MoJ 보도자료 | Time-bounded, may amend manual content before next manual edition |
| **T4 — Authority guide page** | Persistent HiKorea / Immigration Service guide pages (e.g. nationality procedure, refugee procedure, KIIP guide) | HiKorea visa/stay guide, immigration.go.kr policy info | Official but version-implicit; can drift behind T1/T2 |
| **T5 — Operational portal** | Live transactional/lookup surfaces; not "content" but a service entry point | e-Application, 방문예약, 외국인등록증 진위확인, 관할 출입국관서 찾기 | Should be **linked**, generally **not scraped** |
| **T6 — Adjacent official** | Other government portals referenced from HiKorea/MoJ | Visa Portal (visa.go.kr), Soci-Net (socinet.go.kr), 1345.go.kr, 정부24, 법제처 OPEN API | Authoritative within their own domain; cite explicitly |
| **T7 — Paradiso normalized** | Curated structured records derived from T1–T4 | `visa_data.json`, `doc_master.json`, `data/jobcode_master.json` | Implementation data, audit and display layer, never source-of-truth |
| **T8 — LLM synthesis** | Model-generated explanations | `/api/ask` answers | Never authoritative; must carry citations and disclaimers |

**Rule:** When T1–T4 disagree, prefer the newer T1/T2 and mark the older T3/T4 as `needs_review`. A HiKorea T4 page alone is **not sufficient** to assert a legal conclusion in Paradiso UI; pair with T1 or T2 or mark as informational.

---

## 2. Public page categories found on HiKorea

The following categories are **known public surfaces** on `https://www.hikorea.go.kr/`. Exact URLs and 메뉴 codes change over time and **must be operator-verified** before any retrieval is attempted. They are listed here so the schema and PR plan in §10 can be reviewed without committing to specific paths.

| Category | What it contains | Surface type | Notes |
|---|---|---|---|
| Visa & status guide (사증/체류 안내) | Visa-category overviews, eligibility, period-of-stay summaries | T4 guide | Already partially covered by Paradiso's visa data; cross-reference, do not blindly overwrite |
| Stay procedures (체류) | Extension, change of status, status grant, registration, re-entry, activities outside status, workplace change | T4 guide | Maps to procedures we already structure per `MANUAL_BASED_DATA_MODEL.md` |
| Nationality & naturalization (국적) | General/simplified/special naturalization, recovery, renunciation, dual nationality | T4 guide + T1/T2 references | Outside current Paradiso scope — new |
| Overseas Koreans (재외동포 / F-4) | F-4 status, application paths, restrictions | T4 guide | Partially in Paradiso visa data; add procedural surface |
| Refugee procedures (난민) | Refugee status application, humanitarian status, appeal | T4 guide | Sensitive; **manual legal review required** before user-facing copy |
| Immigration certificates (사실증명) | 외국인등록사실증명, 출입국에 관한 사실증명, etc. | T4 guide → T5 service | Guide can be summarized; issuance is a T5 service — link only |
| Reporting obligations (각종 신고) | 체류지 변경신고, 근무처 변경/추가 신고, 등록사항 변경신고 | T4 guide | High-value: every long-term foreigner needs these |
| e-Application (전자민원) | Online filing portal for extension, change, registration etc. | T5 service | **Link only**; do not scrape; do not automate submission |
| Visit reservation (방문예약) | Office visit booking for in-person filings | T5 service | **Link only**; do not scrape personal/slot data |
| Civil petition forms (민원서식) | Downloadable PDFs/HWPs for each petition type | T4/T5 hybrid | Form metadata (name, code, last-updated) is high-value; mirror form *catalog*, link to original file |
| Office lookup (관할 출입국관서 찾기) | Jurisdiction-by-address lookup; office contact details | T5 service + T4 directory | Office directory (addresses, phones) is mirrorable as T4; the address→office query is a T5 service that should remain linked |
| Residence-card validity lookup (외국인등록증 진위확인) | Authenticity check for a registration card | T5 service | **Link only**, never scrape; involves personal data inputs |
| Social integration (사회통합프로그램 / KIIP) | Program overview, level test, course information | T4 guide; main portal is Soci-Net | Most operational detail lives at `socinet.go.kr` — see §3 |
| Seasonal workers (계절근로) | E-8 program, MoU LGUs, eligibility | T4 guide + MoJ notice | Updates often arrive as T3 notices |
| 1345 contact center | Phone/chat support metadata, language hours | T4 reference | Mirrorable as static reference |
| HiKorea notices (공지사항) | Dated announcements, system maintenance, policy changes | T3 notice | High-value for change monitoring |
| Press releases & news (보도자료, 새소식) | MoJ Immigration HQ announcements | T3 notice | High-value for change monitoring |
| Materials / 자료실 | Downloadable manuals, brochures, multi-language guides | T2/T3 mix | Some files here are the authoritative source we already mirror (manuals) |
| FAQ | Common questions | T4 informational | Useful for synonym mining; never authoritative |
| Site map / 도움말 | Navigation and help | T4 informational | Useful for crawling plan, not for content |

Note that HiKorea also exposes login-only personal-data sections (My Page, application status, payment history). **These are explicitly out of scope** for any ingestion or scraping work and are not listed.

---

## 3. Korea Immigration Service & adjacent official surfaces

`https://www.immigration.go.kr/` is the Ministry of Justice Immigration HQ site. HiKorea is the citizen-facing portal it operates; immigration.go.kr is the institutional/policy site. Both should be inspected together because policy-level updates often appear on immigration.go.kr before being reflected in HiKorea guide pages.

| Source | Public landing (operator-verify) | Role | Tier |
|---|---|---|---|
| Korea Immigration Service (출입국·외국인정책본부) | `https://www.immigration.go.kr/` | Policy info, nationality, refugee, overseas Koreans, KIIP overview, notices, press, manual downloads | T2/T3/T4 |
| HiKorea | `https://www.hikorea.go.kr/` | Citizen-facing portal: guides, e-application, reservation, lookups, notices, forms | T3/T4/T5 |
| Visa Portal | `https://www.visa.go.kr/` | Ministry of Foreign Affairs visa portal; pre-entry visa information, online application, embassy info | T4/T5 |
| Soci-Net (사회통합정보망) | `https://www.socinet.go.kr/` | KIIP enrollment, level test (KIIP-CBT/PBT), course listings, certificate verification | T4/T5 |
| 1345 외국인종합안내센터 | `https://www.1345.go.kr/` | Multilingual help center metadata, contact hours, languages, chat | T4 |
| 국가법령정보센터 | `https://www.law.go.kr/` | Statutes (T1), enforcement decree, ministerial notice; has OPEN API | T1 + adjacent API |
| 정부24 | `https://www.gov.kr/` | Cross-ministry civil services; references some foreigner services | T6 reference |
| 공공데이터포털 | `https://www.data.go.kr/` | Government open data API catalog; some MoJ datasets indexed | T6 reference |

Schema and catalog records in this audit (§7, §8) accommodate any of these as `source.host`.

---

## 4. High-value Paradiso integration candidates

These are the categories where structured ingestion (not just deep-linking) is likely worth the engineering and review cost. "Worth it" here means: high user value, content is durable enough to extract, and the legal-risk profile is manageable with disclaimers + manual review.

Ranked roughly by ratio of (user value × durability) ÷ (review cost):

1. **Civil petition forms catalog (민원서식)** — name, form code, last-updated, attached file URL, language. Pure metadata; form file itself stays linked. Helps every Paradiso user find the right form without guessing.
2. **Office directory (관할 출입국관서)** — name, address (KR + romanized), phone, hours, jurisdiction notes. Already partially modelable. Augment with HiKorea-listed offices; never replace the live address→office lookup with our own logic.
3. **Reporting-obligation guides** — 체류지 변경신고, 근무처 변경/추가 신고, 등록사항 변경신고. High-value, statute-anchored, manual-anchored. Map to existing procedure model.
4. **Nationality & naturalization overview** — general/simplified/special naturalization, renunciation, recovery, dual nationality. New domain; treat as topic cards with explicit `needs_legal_review` flag until reviewed.
5. **Overseas Koreans (F-4 / 재외동포)** — cross-reference Paradiso's existing F-4 record with HiKorea's overseas-Koreans guide and the 재외동포법.
6. **Immigration certificates catalog** — list of certificate types, where to obtain, fee, validity. Issuance flow stays linked, not automated.
7. **HiKorea + MoJ notice stream** — dated notice index for change monitoring (see §6). High value because it is the earliest signal that manuals will need a refresh.
8. **Seasonal worker (E-8) overview** — program description, MoU LGUs list (when published), eligibility outline. Updates arrive as T3 notices frequently.
9. **KIIP / social integration overview** — program structure, levels, mapping to F-2-R / naturalization benefits. Deep operational detail stays at Soci-Net.
10. **Refugee procedure overview** — high user value but **higher legal sensitivity**; defer to a separate dedicated PR after attorney/advocacy-org review.

Each item above maps to a **topic card** (see schema proposal §3).

---

## 5. Link-only — do not scrape

The following surfaces are operational portals or contain personal-data interaction. Paradiso must **deep-link** to them with clear labels and never attempt to mirror, automate, or scrape them.

| Surface | Why link-only |
|---|---|
| e-Application (전자민원) submission flows | Requires authentication and personal data input; automating it is unauthorized agency |
| 방문예약 (visit reservation) booking | Personal-data input + slot allocation; scraping would compete with real users for slots |
| 외국인등록증 진위확인 (residence-card validity check) | Personal data input; we must not retain or proxy such queries |
| Address → office lookup query | Live service; jurisdiction logic belongs to MoJ, not Paradiso |
| Application status lookup / My Page | Login-walled and personal |
| Payment / fee transactions | Out of scope |
| KIIP enrollment, course booking, test booking on Soci-Net | Login-walled and personal |
| Visa Portal online application | Login-walled and personal |
| Embassy/consulate appointment systems | Out of scope |

For each, the Paradiso UI should provide:
- a clearly labeled outbound link (with language indication and "leaves Paradiso" affordance),
- the official phone number or 1345 fallback,
- a brief explainer card describing what the user will do at that destination.

No automated form-filling, headless-browser submission, or credential storage is in scope under any roadmap PR proposed below.

---

## 6. Update-monitoring candidates

The current `data/source_registry.json` already declares two placeholder notice indexes (`hikorea_notice_placeholder`, `moj_immigration_notice_placeholder`) with `status=not_configured`. This audit confirms that posture and extends it.

Recommended monitoring set (in priority order). Each must remain `status=not_configured` until an operator confirms the exact index URL, robots.txt posture, and rate-limit budget.

| Monitor | Cadence | Detection target | Action on change |
|---|---|---|---|
| HiKorea 공지사항 index | Daily (off-peak) | New notice rows | Queue summary card for manual review |
| MoJ Immigration HQ 보도자료 | Daily | New press releases | Queue for review; cross-check against affected manual section |
| MoJ Immigration HQ 공지사항 / 새소식 | Daily | New entries | Same as above |
| HiKorea 자료실 (materials) | Weekly | New/updated manual or brochure file | Compare hash to `source_registry.json`; if manual changed, open a manual-refresh PR |
| Visa Portal 공지 | Weekly | Policy/system changes affecting visa issuance abroad | Queue for review |
| Soci-Net 공지 | Weekly | KIIP schedule / curriculum changes | Queue for review |
| 1345 hours / language coverage | Monthly | Hours or language list change | Update the static 1345 reference card |
| 법제처 OPEN API — 출입국관리법 / 국적법 / 재외동포법 / 난민법 | On amendment | New amendment date for monitored law id | Trigger high-priority review; cross-check manual interpretation |

All of these are *monitors*, not ingestion pipelines. The monitor's job is to detect change and notify a human reviewer; promotion of any change into user-facing Paradiso content remains a separate, human-reviewed PR (same pattern as `scripts/check_source_updates.py` and `scripts/promote_grounding_candidate.py` already established).

Monitors must respect:
- `robots.txt`
- explicit rate limits (default: no more than one request per source per minute, with backoff)
- `If-Modified-Since` / `ETag` where available
- a clearly identifying `User-Agent` string
- a configurable kill switch (env var, default off)
- no parallel fetching across sources from the same IP

---

## 7. Pages requiring manual legal/admin review before user-facing use

The following extracted topic types must not be promoted from `candidate` to `published` without explicit legal/administrative review. The schema (§3 of the schema proposal) carries a `legal_review_required: true` flag for each.

| Topic type | Why review is required |
|---|---|
| Refugee procedures (난민) | Vulnerable population; mistakes can cause real harm; legally complex |
| Nationality & naturalization decisions | Discretionary criteria; outcomes are not fully rule-based |
| Long-term residency (F-5) substantive criteria | Discretionary, regularly amended |
| Marriage migrant (F-6) divorce / abuse / child-custody pathways | Sensitive; intersects with family law |
| Workplace-change rules for E-series | Frequently amended; misinterpretation can trigger overstay or unauthorized work |
| Seasonal worker (E-8) MoU and quota tables | Updated by individual notice; quoting stale numbers can mislead employers |
| Anything labeled as 한시적 / 시범 / 잠정 (temporary, pilot, provisional) | Designed to change; explicit caveats required |
| Fines, penalties, criminal liability descriptions | Must never be Paradiso AI synthesis |
| Anything that could read as "advice on how to qualify" | Paradiso must remain informational; advisory framing is not allowed |

Even after review, user-facing copy must keep Paradiso's existing disclaimer line and refer users to 1345 or 관할 출입국관서 for binding determinations.

---

## 8. Risk levels per information category

| Category | Risk level | Primary risk | Mitigation |
|---|---|---|---|
| Office directory (name/address/phone/hours) | Low | Stale phone/hours | Re-fetch monthly; show `last_verified` date |
| Petition forms catalog (metadata only) | Low | Stale form version | Hash-watch the form file URL; show form version |
| Visa/status guide cross-reference | Low–Medium | Conflict with our manual extracts | Mark conflicts as `needs_review`; manual wins by tier rule |
| Reporting obligations | Medium | Deadline / penalty errors | Cite statute article; no fine amounts without T1 source |
| KIIP / social integration overview | Medium | Schedule / level mapping changes | Link to Soci-Net for operational detail |
| Overseas Koreans (F-4) | Medium | Restricted-activity list updates | Re-anchor to 재외동포법 and current notice |
| Nationality & naturalization | High | Discretionary criteria; serious downstream consequences | Legal review before publish; informational framing only |
| Seasonal workers (E-8) | High | Frequent MoU/quota updates | Notice-driven; do not freeze quota tables |
| Refugee procedures | High | Vulnerable population; legal complexity | Defer to dedicated reviewed PR; advocacy-org input |
| Immigration certificates issuance flow | Medium | Method/place of issuance change | Link to official issuance flow; do not mirror UI |
| e-Application / 방문예약 / 진위확인 (link-only) | High if scraped | Personal data, ToS, access controls | Link only; never scrape; never automate |
| Notice / press stream (raw index) | Low (metadata) / Medium (content summary) | Misclassification of a notice | Human triage before any summary is published |
| Adjacent law text (T1) | Low if cited verbatim; High if paraphrased | Misquotation, missed amendment | Use 법제처 API + `time_travel`; show retrieval date |

---

## 9. Compliance and ethical constraints

These apply to every PR that consumes this audit.

- **No login-walled pages.** No scraping behind authentication, CAPTCHA, or session cookies.
- **No personal-data proxying.** Paradiso must not become a man-in-the-middle for residence-card checks, application submissions, or reservation booking.
- **Respect robots.txt and rate limits.** Default-off ingestion; explicit operator opt-in; per-host budgets; backoff on errors.
- **Attribution.** Every extracted topic card must carry its source URL, source title, retrieval date, language, and source authority. Display attribution near user-facing content.
- **No legal advice framing.** Paradiso remains an information and guidance platform. No "you should…", "you must qualify…", "we recommend you apply for…" language derived from these sources. Use neutral informational verbs.
- **Disclaimer continuity.** Existing Paradiso disclaimer (베타, 법적 효력 없음, 1345 또는 관할 출입국관서 확인) remains on every surface that consumes HiKorea-derived content.
- **License / reuse.** Korean government works are typically reusable under KOGL (공공누리) but **terms differ per work**. Each ingested source must record its KOGL type (1/2/3/4) or "unknown — needs review" in the catalog.
- **Personal data hygiene.** Even though Paradiso does not collect application data, any cached/mirrored material must be inspected to ensure no incidentally embedded personal data is mirrored (e.g., sample-completed forms).

---

## 10. Recommended PR sequence after this audit

This audit is intentionally scoped to documentation. The work it unblocks should be sequenced so each PR is independently reviewable and revertable, and so behavior change is gated behind explicit operator action.

| # | Branch (suggested) | Title | Scope | Gate |
|---|---|---|---|---|
| **PR-A (this PR)** | `audit/hikorea-source-map` | Audit: HiKorea source map for Paradiso expansion | Docs only: this audit + schema proposal + example catalog | Review only |
| **PR-B** | `data/hikorea-source-catalog-v1` | Catalog: initial HiKorea/Immigration source records | Populate `data/sources/hikorea_source_catalog.json` with operator-verified landing URLs; all entries `status=not_configured`; extend `data/source_registry.json` with confirmed entries | No fetcher wired; CI validates JSON schema only |
| **PR-C** | `scripts/source-monitor-extension` | Extend `check_source_updates.py` to handle notice indexes | Add notice-index discovery (HiKorea, MoJ); still default-off; respects existing `--allow-network` flag | No promotion; only emits a candidate file |
| **PR-D** | `data/petition-forms-catalog` | Petition forms catalog (metadata only) | New JSON: form_code, name (ko/en), url, last_updated, language, KOGL type | Forms themselves linked, not mirrored |
| **PR-E** | `data/office-directory-augment` | Augment office directory from HiKorea-listed offices | Mirror name/address/phone/hours; no address→office lookup logic | Validated against jurisdiction data we already have |
| **PR-F** | `data/reporting-obligations-topic-cards` | Reporting obligations topic cards (체류지/근무처/등록사항) | Statute-anchored topic cards; `needs_review` until manual-checked | Disclaimer continuity verified |
| **PR-G** | `data/nationality-overview-topic-cards` | Nationality & naturalization overview cards | Informational only; `legal_review_required=true` | Held for explicit legal review |
| **PR-H** | `data/overseas-koreans-and-kiip` | Overseas Koreans + KIIP overview cards | Cross-reference visa data; link to Soci-Net | Soci-Net deep-linked only |
| **PR-I** | `data/seasonal-worker-overview` | Seasonal worker (E-8) overview + notice anchor | Anchored to current MoJ notice id; no quota table mirroring | Notice id versioned |
| **PR-J** | `data/refugee-procedure-overview` | Refugee procedure informational cards | **Held** for external review (legal + advocacy) | Do not merge without sign-off |
| **PR-K** | `ui/source-attribution-affordance` | UI: source attribution + outbound-link affordance | Add a small "공식 출처" panel + "leaves Paradiso" indicator on outbound links | After PR-B at minimum |

PRs B–I are independently mergeable once the schema (PR-A) is in place. PR-J should not be opened until the operator has lined up reviewers. PR-K is UI work and can run in parallel.

---

## 11. Open questions for the operator

These need answers before PR-B can be opened.

1. **Allowed monitoring posture.** Daily polling of HiKorea + immigration.go.kr notice indexes — approved? Any constraints from prior contact with the agencies?
2. **User-Agent and contact email.** What identifier should the source monitor present? Is there an operator email to expose for takedown requests?
3. **KOGL classification per source.** Operator confirmation that each ingested artifact's reuse license is recorded; default to "unknown — needs review" until confirmed.
4. **Refugee/nationality reviewer.** Who reviews PR-G and PR-J? An attorney, an 행정사, or an advocacy partner?
5. **Soci-Net depth.** Mirror only the program overview, or also the level/curriculum static descriptions? (Recommendation: overview only.)
6. **Visa Portal scope.** Cross-reference for pre-entry visa info only, or also embassy/consulate metadata? (Recommendation: visa info only in this phase.)
7. **Language coverage.** Source pages are mostly ko/en, some zh/vi/ja. Target Paradiso languages remain ko/en/zh/vi — confirm we capture ko original + the matching target language when available.

---

## 12. What this audit explicitly does not deliver

- No HiKorea or immigration.go.kr page was fetched.
- No URLs are claimed authoritative; all are candidates pending operator verification.
- No scraping, monitoring, or ingestion job was enabled.
- No user-facing copy was written or translated.
- No existing dataset was modified.
- No new dependencies, env vars, or runtime code paths were added.
- No legal opinion is offered; this audit is informational planning.

---

*End of audit. See `HIKOREA_SOURCE_SCHEMA_PROPOSAL.md` for the proposed JSON schemas and `data/sources/hikorea_source_catalog.example.json` for an illustrative skeleton.*
