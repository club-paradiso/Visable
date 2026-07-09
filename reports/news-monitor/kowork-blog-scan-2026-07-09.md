# External source scan — kowork.kr/blog (2026-07-09)

Accessed: 2026-07-09
Scope: identify content on kowork.kr's blog that could be useful reference material or a staleness/gap signal for Paradiso, and propose how (if at all) to reflect it on the live site.

## Method note — read before using anything below

`kowork.kr` is blocked at the session's outbound-egress layer (`connect_rejected`, "policy denial" on `kowork.kr:443`, confirmed via the proxy status endpoint). A direct crawl/DOM scrape of the blog was not possible, and per the proxy's own operating rules, policy denials are not something to route around. Everything below was reconstructed from search-engine indexing (titles + snippets, some AI-summarized) of `kowork.kr/blog/*` pages, cross-checked across multiple queries.

Consequences:
- Treat every figure, date, and requirement below as **unverified secondhand paraphrase**, not a primary source. Kowork itself is a private recruitment company, not an authority — even a clean fetch of their page would still not be a primary legal source.
- Nothing here should be copied into `visa_data.json`, `backend/data/visas.json`, or `doc_master.json`. Anything judged worth adopting must first be re-verified against the primary source (law.go.kr, moj.go.kr notice, hikorea.go.kr, or the registered 사증발급/체류 manuals) — consistent with CLAUDE.md's "do not invent legal/immigration content" and "OCR/secondary text is a readable aid for auditing only" rules.
- If someone wants a true scrape later, it needs to run outside this session's egress policy (e.g., approved from an environment where `kowork.kr` is allowlisted), or the domain needs to be added to the org's allowed-egress list.

## Inventory of posts found

| Post | URL | Theme | Relevance to Paradiso |
|---|---|---|---|
| E-7 salary requirement change (2025-04-01) | `/blog/e7-visa-2025-salary-requirements` | E-7 wage floor, GNI-% system abolished | High — direct overlap with `visa_data.json` E-7 |
| E-7 salary requirement change (2026-02-01) | `/blog/e7-visa-2026-salary-requirements` | Updated E-7 won-amount wage floors | High |
| National employment protection review vs E-7 | `/blog/국민고용보호심사기준` | Common-misconception debunk (5-Korean-employee myth) | High |
| E-7 visa extension | `/en/blog/e7extension` | Required docs/timing for E-7 연장 | Medium — Paradiso's own extension section should already cover this; useful as a cross-check |
| F-2-7 points-based talent visa | `/blog/whatisF-2-7` | Eligibility, 80-point threshold, benefits | Medium |
| F-4 (재외동포) employment guide | `/blog/f4-guide` | Simple-labor job restrictions, misconception that F-4 = unrestricted work | High |
| D-10 part-time work | `/blog/d10-visa-parttime` | D-10 시간제근로 허가 vs 인턴등록 distinction | Medium |
| D-10-1 point-based job-seeking visa | `/en/blog/D-10-1-...` | Scoring, TOPIK exemption, 6-month internship cap, 2-week report rule | Medium — Paradiso's D-10-1 entry already looks materially more current (190-point scale, 2026.6 manual) |
| Immigration office visit guide (for employers) | `/blog/Immigration-Visit-Guide` | D-10→E-7 change-of-status logistics, HiKorea reservation, 2–7 week timeline | Low/Medium — HiKorea reservation flow already exists in Paradiso (`index.html`, `ai.html`) |
| TOPIK exam guide 2025 | `/blog/topik-한국어능력시험-가이드-2025` | TOPIK levels, PBT/IBT, schedule | Low — general public info already on topik.go.kr, tangential to 체류자격 scope |
| 2026 상반기 채용 준비 가이드 | `/blog/2026-Korea-recruitment-season-prep` | Resume/portfolio tips for foreign job seekers | Low — job-search coaching, outside Paradiso's civic-tech visa-info mission |
| HR recruiting-foreigners guide, benefits of hiring foreigners, hiring survey, platform intro | `/blog/guide4recruitingforeigners`, `/blog/BenefitsofHiringForeigner`, `/blog/survey`, `/blog/foreign-talent-recruitment-platform` | B2B marketing / employer sales content | Not relevant — this is kowork's own product marketing, not visa/status information |

## Content notes, by theme

### 1. E-7 wage floor — likely the most actionable lead

Kowork's posts describe two rule changes:
- **2025-04-01**: the old GNI-percentage system (GNI × 80% general / × 70% for SME/venture) was reportedly abolished in favor of a uniform standard.
- **2026-02-01**: MOJ notice reportedly set flat won-amount floors — paraphrased as E-7-1 ≈ ₩31.12M/yr, E-7-2/E-7-3 ≈ ₩25.89M/yr, E-7-4 ≈ ₩26M/yr (increases of ₩2.45M and ₩0.74M respectively over the prior year).

Paradiso's current `E-7.newReq` text still reads **"임금증빙(전년도 1인당 GNI 1배 이상)"**, and one subcode note reads **"연간 근로소득 GNI 2배↑"**. That GNI-multiple framing is exactly what kowork says was replaced by flat won amounts starting 2025-04-01 and revised again 2026-02-01.

→ This is a genuine staleness *signal*, not a confirmed error — the GNI-multiple language could still be correct for a different E-7 subcode/context, or the manual crosswalk may already account for it elsewhere. It needs verification against the actual MOJ notice (moj.go.kr 고시, "2026년 특정활동(E-7) 체류자격 임금요건 기준 공고") before touching the data file.

### 2. E-7 "5 Korean employees" myth

Kowork's post claims E-7-1 (전문인력) is exempt from 국민고용보호심사기준 (wage aside) except for 5 specific occupations flagged for excessive 초청장/추천서 issuance, and that "need 5 Korean employees" / "20% foreign-employee ratio" are misreadings that don't apply to most E-7-1 roles. Paradiso's E-7 entry doesn't currently surface this nuance in its FAQ. If verified, it's a good candidate for a short FAQ entry (pattern already used elsewhere in the E-7 record) rather than a rewrite of `newReq`.

### 3. F-4 employment restrictions

Kowork's F-4 post asserts: legally-binding simple-labor restrictions cover 37+ specific occupations (delivery, cleaning, security, etc.), a regional-exception program lets F-4 holders registered in 18 designated areas work some otherwise-restricted jobs, and a 2026 MOJ notice (2026-35) reportedly added 10 more open occupations (construction labor, gas station, warehouse sorting).

Paradiso's F-4 FAQ currently says only **"단순노무 일부 직종만 제한. 그 외 취업활동은 제한 없음"** — directionally consistent, but without the itemized occupation list or the regional-exception program. This is a plausible enrichment candidate, structurally similar to the existing E-7 occupation-code work (`scripts/employment_code_analyzer.mjs`), but it must be built from the actual MOJ 고시 text, not from kowork's paraphrase.

### 4. Lower-priority items

- E-7 연장, F-2-7, D-10 시간제, D-10-1, Immigration-office-visit content are broadly consistent with what Paradiso already has, in some cases (D-10-1's point scale, F-4's 2026-02-12 H-2 consolidation) Paradiso's own data is visibly *more current* than kowork's paraphrased posts. No action indicated beyond noting these as confirmatory, not novel.
- TOPIK guide and job-seeker/resume coaching content sit outside Paradiso's 체류자격 scope (civic-tech visa/status platform, not a job-matching or resume-coaching product) and pull toward kowork's own B2B/job-board mission. Recommend leaving these out.
- HR-facing marketing posts (recruiting tips, hiring benefits, hiring survey, platform intro) are kowork's own sales content, not informational for Paradiso's foreigner-facing users.

## Content intentionally not extracted or reflected

- No wage figure, occupation list, or eligibility threshold above has been written into any Paradiso data file.
- No FAQ or requirement text was added or changed as part of this scan.
- kowork.kr is not treated as an official/citable source anywhere in this report — it is used only as a *lead generator* pointing at which MOJ notices to go verify directly.

## Review note

Two items are worth a follow-up verification pass against primary sources before any data edit is considered:
1. Confirm current E-7 wage-floor phrasing (GNI-multiple vs. flat won amount) against the live MOJ 고시 and the registered 2026-06 사증발급 manual.
2. Confirm the F-4 단순노무 restricted-occupation list and regional-exception program against the MOJ 고시 (재외동포(F-4) 자격의 취업활동 제한범위 고시) before considering a structured enrichment.

Neither is executed in this report — this is a scan/lead document, not a data change.
