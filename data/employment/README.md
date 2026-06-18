# `data/employment/` — 취업정보 신고용 직종·업종 analyzer data module

Data behind the **취업정보 신고용 직종·업종 찾기** feature: it translates ordinary,
colloquial, field-worker, and multilingual work descriptions into candidate
**직종(occupation, KSCO8)** and **업종(industry, KSIC11)** categories for HiKorea
**외국인 취업정보 신고**.

> This module helps users *find likely reporting categories*. It does **not**
> decide visa eligibility or whether an activity is permitted under a status, and
> it never invents official codes. Final codes are confirmed on HiKorea / 1345 /
> the 국가데이터처 통계분류포털.

## Source of truth

- **Canonical codes** live in [`../jobcode_master.json`](../jobcode_master.json)
  (`type: occupation|industry`, with `source_*` provenance). **Nothing in this
  folder contains official codes** — only retrieval keywords, aliases, rules and
  metadata. `scripts/audit_employment_sources.mjs` enforces this.
- **Classification authorities** (per the MoJ press release): HiKorea 직종명 검색 =
  **국가데이터처 표준직업분류 (KSCO8)**; 업종명 검색 = **국가데이터처 표준산업분류 (KSIC11)**.

## Files

| File | Role |
|------|------|
| `synonyms.ko.json` / `synonyms.en.json` | Everyday role/workplace **concepts** → occupation/industry retrieval terms. |
| `colloquial_field_terms_ko.json` / `_en.json` | **Field-labor signals**: place / object / action / tool → retrieval terms + sector + disambiguation refs (drives `field_labor_mode`). |
| `aliases.entertainment.{ko,en}.json` | Performance/arts vocabulary (legally sensitive → cautions). |
| `aliases.tattoo.{ko,en}.json` | Tattoo/cosmetic-tattoo vocabulary (no dedicated code; low-confidence + 문신사법 caution). |
| `ambiguous_inputs.json` | Umbrella terms (아이돌, 댄서, 타투이스트, 알바…) **decomposed** into real sub-roles, with follow-up questions. |
| `disambiguation_rules.json` | One-at-a-time clarifying questions for genuine occupation/industry forks (vessel vs land, golf direct vs contractor, factory vs warehouse…). |
| `source_registry.json` | Provenance for every classification / legal / vocabulary / test-priority source, with reliability + limitations. |
| `visa_reporting_scope.json` | Reporting scope by 체류자격 (17 included; F-5 excluded; 직종·업종·소득; 15-day change rule). |
| `income_brackets.json` | Annual income bracket labels (`source_status: unverified` — confirm live on HiKorea). |
| `classification_sources.json` | Consolidated KSCO8/KSIC11 source metadata + checksum (generated). |
| `*_test_cases.json` | Generated mode suites (see below). |
| `analyzer_test_cases.json` | Original behavioral regression fixtures. |

## Record shapes

**Concept** (`synonyms.*`, `aliases.*`): `{ id, type: role|workplace|employment_type|visa, surface[], label_ko, occupation_terms[], industry_terms[], … }`.

**Field signal** (`colloquial_field_terms.*`): `{ id, signal: place|object|action|tool, sector, mode, surface[], label_ko|label_en, occupation_terms[], industry_terms[], disambiguation[] }`.

All `occupation_terms` / `industry_terms` are **keywords verified to substring-match
a real KSCO8/KSIC11 name** in `jobcode_master.json` (no dead-ends — audited).

## Analyzer & modes

Logic: [`../../scripts/employment_code_analyzer.mjs`](../../scripts/employment_code_analyzer.mjs)
(pure ES module; runs identically in Node and in `index.html`). Loader:
[`../../scripts/employment_data_loader.mjs`](../../scripts/employment_data_loader.mjs).

Modes: `field_labor_mode`, `professional_mode`, `service_mode`,
`arts_entertainment_mode`, `ambiguous_mode`. Occupation (what you do) and industry
(what the employer's business is) are always retrieved and reported on **separate
tracks**.

## Commands

```bash
node scripts/build_employment_test_cases.mjs   # regenerate the mode suites
npm run test:employment-analyzer               # behavioral + mode suites
npm run audit:employment-sources               # sources, scope, no hallucinated codes/vocab
node scripts/employment_analyze_cli.mjs "골프장 청소해요"   # ad-hoc check
node scripts/employment_failure_report.mjs     # coverage report from query logs
```

## Editing rules

- **Never** add official codes here. Add **retrieval keywords** that already
  match a real classification name (the audit will fail otherwise).
- Keep occupation vs industry terms on the correct track.
- Keep / strengthen cautions and "confirm officially" language — never weaken them.
- After edits: regenerate test cases and run the two npm scripts above.
