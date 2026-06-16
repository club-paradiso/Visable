# Employment Code Analyzer (취업정보 신고용 직종·업종 찾기)

A natural-language finder that turns a plain Korean or English job/business
description into candidate **직종(occupation, KSCO8)** and **업종(industry,
KSIC11)** codes for **HiKorea 취업정보 신고** (employment-information reporting).

Module: `scripts/employment_code_analyzer.mjs`
CLI: `scripts/employment_analyze_cli.mjs`
Tests: `scripts/check_employment_code_analyzer.mjs`

---

## 1. What the feature does

The analyzer is a **deterministic retrieval pipeline**, not an LLM that guesses
codes. Given a description like "카페에서 바리스타로 일해요", it runs a fixed
sequence:

1. **Normalize** — lowercase, strip punctuation, collapse whitespace, strip
   trailing Korean particles (`카페에서` → `카페`, `바리스타로` → `바리스타`),
   drop stop-words, and tokenize.
2. **Entity extraction** — match a concept lexicon to detect the job role,
   workplace type, employer business activity, employment type, and visa status.
3. **Two-track classification** — search the occupation track (KSCO8) and the
   industry track (KSIC11) completely separately.
4. **Hybrid scoring** — score each canonical row against the raw query plus
   expanded synonym terms (code/name/alias hits, with depth- and leaf-bonuses).
5. **Ambiguity questions** — when the input is underspecified, emit follow-up
   questions with "더 정확히 고르기" chips instead of dumping everything.
6. **Warnings + source notes** — always attach legal caveats and provenance.

**Hard constraint: it never invents codes.** Every candidate it returns is
retrieved from `data/jobcode_master.json`. If a term has no match in the
official table, no candidate is produced. The regression tests enforce this as a
hard "no hallucinated code" assertion.

The module is environment-neutral and does no file or network I/O itself — data
is injected as dependencies, so the same code runs in Node (CLI + tests) and in
the browser.

---

## 2. Official sources used

Provenance is recorded in `data/jobcode_master.json` metadata and consolidated
(with a checksum) into `data/employment/classification_sources.json`.

**직종 / occupation — KSCO8**
- 제8차 한국표준직업분류 (KSCO8)
- 통계청 고시 제2024-328호 (announced 2024-07-01)
- Effective **2025-01-01**
- Runtime coverage: 728 rows (대/중/소/세분류 only; see Limitations)

**업종 / industry — KSIC11**
- 제11차 한국표준산업분류 (KSIC11)
- 통계청 고시 제2024-2호 (부칙개정 제2024-203호), announced 2024-01-01
- Effective **2024-07-01**
- Runtime coverage: 2,038 rows (full table)

**Issuing body / portal**
- 통계청 / 국가데이터처, 국가데이터처 통계분류포털 — https://kssc.mods.go.kr

**Reporting framework (MOJ / HiKorea)**
- 취업정보 신고 reports 직종 · 업종 · 연간소득 (income band)
- Legal basis: **출입국관리법 시행규칙 제47조 및 제49조의2**
- HiKorea 직종조회 = 표준직업분류표, 업종조회 = 표준산업분류표 (FAQ Q7, 붙임2)

These exact 고시 numbers and dates come from the data files — they are not
fabricated in the analyzer or in this doc.

---

## 3. 직종(occupation) vs 업종(industry)

These are two different questions and are scored on **two completely separate
tracks that are never mixed**:

- **직종 (occupation)** = *what the person actually does* (their duties).
  Classified with **KSCO8**.
- **업종 (industry)** = *the employer's main business activity*.
  Classified with **KSIC11**.

Because KSCO8 and KSIC11 share numeric code spaces, the index builds a
**type-segregated** parent set so a leaf in one classification is never mislabeled
by a parent in the other.

**Worked example — "카페에서 바리스타로 일해요":**
- 직종 → **음료 조리원** (what you do — making drinks) from KSCO8.
- 업종 → **커피 전문점 / 비알코올 음료점업** (the employer's business) from KSIC11.

The lexicon keeps these honest: a `workplace` concept feeds `industry_terms`, a
`role` concept feeds `occupation_terms`, and only explicit `industry_terms` on a
role (e.g. translator, content creator) weakly cross into the industry track.

---

## 4. Why the analyzer asks follow-up questions

When the input does not pin down both tracks, the analyzer raises **ambiguity
flags** and emits targeted follow-up questions (each with a `flag`, a `question`,
and clickable `chips`) rather than guessing or dumping the whole table. Flags:

- `workplace_without_role` — a workplace is given but no concrete role. Asks
  *what do you actually do there?* using that workplace's `ambiguous_roles`
  (e.g. cafe → 바리스타 / 홀서빙 / 주방보조 / 매니저 / 사장).
- `role_without_workplace` — a role is given but no employer business. Asks
  *what is the employer's main business?* (chips: 식당/카페, 학원/교육,
  IT/소프트웨어, 제조/공장, 도소매/쇼핑몰, 병원/복지, 직접 입력).
- freelancer — needs both **service** (→ occupation) and **client/own business**
  (→ industry). Triggered by a `freelancer` concept or "프리랜서/freelanc".
- `owner_or_self_employed` — owner / 자영업: occupation is usually 관리자·경영,
  industry follows 사업자등록상 업태·종목.
- `underspecified` — no usable role or workplace and no candidates; asks the user
  to describe both the work and the employer's business, with an example.

---

## 5. Limitations

- **KSCO8 is not fully loaded.** The runtime ships 대/중/소/세분류 only (728 rows);
  the 세세분류 (5-digit detailed unit) full table is pending. When the only
  occupation matches are non-leaf, a warning tells the user to confirm the detail
  code on HiKorea 직종조회. (KSIC11 *is* the full table, 2,038 rows.)
- **Confidence is heuristic.** It is computed relative to the top candidate's
  score (`high` / `medium` / `low`), not a calibrated probability.
- **The lexicon is alias-based.** Matching depends on the surface phrases in
  `synonyms.{ko,en}.json`; phrasings outside the lexicon fall back to raw-token
  retrieval only.
- **It is NOT a legal-permission checker.** Picking a code does not establish
  that the activity is allowed under a given 체류자격.
- **Final codes must be confirmed** on HiKorea / 1345 / 국가데이터처 통계분류포털
  (https://kssc.mods.go.kr).

---

## 6. How to update classification data

There are three layers; keep them separate.

1. **Canonical codes** — `data/jobcode_master.json` (a protected data file).
   Built by `scripts/build_employment_reporting_dataset.py`. This is the single
   source of truth for codes, names, levels, and paths. Do not hand-edit codes.
2. **Synonym / alias layer** — `data/employment/synonyms.ko.json` and
   `synonyms.en.json`. These contain **no official codes** — only retrieval
   hints (`surface`, `occupation_terms`, `industry_terms`, `ambiguous_roles`).
   Add new phrasings here to improve matching without touching canonical data.
3. **Source metadata + checksum** — `data/employment/classification_sources.json`,
   regenerated by:

   ```
   node scripts/build_classification_sources.mjs
   ```

   This reads `jobcode_master.json`, derives consolidated provenance
   (classification names, 고시/revision, effective dates, portal), and computes a
   `sha256` checksum of the canonical dataset. It **does not touch the codes**.

**Adapter approach for HiKorea dropdown mismatches.** If a HiKorea 직종/업종
dropdown differs from the public standard classification table, do **not** mutate
canonical data. Record the mismatch in the metadata's `known_mismatches` and
handle it in a runtime adapter layer (e.g. the KSCO8 세세분류 gap is surfaced as a
warning rather than by fabricating codes).

---

## 7. QA / test commands

```
# Regression suite: no hallucinated codes, tracks separated, source metadata present
node scripts/check_employment_code_analyzer.mjs

# Human-readable analysis of one description
node scripts/employment_analyze_cli.mjs "카페에서 바리스타로 일해요"

# JSON output, with an explicit visa status
node scripts/employment_analyze_cli.mjs --json --visa E-7 "IT 스타트업 개발자"

# Regenerate consolidated source metadata + checksum
node scripts/build_classification_sources.mjs
```

The regression suite also runs in CI via `scripts/check_repo.sh`, step
**[9b/14]** ("Validating HiKorea employment-reporting helper dataset & UI
logic").

CLI flags: `--json` (raw JSON), `--visa <CODE>` (e.g. `E-7`),
`--locale <ko|en>`. Each test fixture in
`data/employment/analyzer_test_cases.json` asserts behavior (min candidate
counts, expected substrings per track, ambiguity expectations) and resolves
expected codes from `jobcode_master.json` at test time, so fixtures cannot drift
into hallucination.

---

## 8. Safety & legal caution

This tool helps **find candidate classification codes for reporting only**. It is
**not a legal-permission checker**. Selecting a 직종/업종 code does **not** make
an activity legal, and does **not** confirm that the activity is allowed under a
person's 체류자격 (자격외활동 허가 등은 별도 사안). Every result carries a base
caveat and a final-confirmation notice. Always confirm the final reporting code
and your reporting obligation on HiKorea, 1345, or the 국가데이터처 통계분류포털.

---

## Public API

The module is a pure ES module exporting the helpers plus two entry points.

### `createEmploymentAnalyzer({ data, lexicon, sources, context })`

- `data` — the canonical jobcode dataset (the object with `.data`, or the array).
- `lexicon` — `{ ko: { concepts: [...] }, en: { concepts: [...] } }`.
- `sources` — `{ occupation: {...}, industry: {...} }` source metadata.
- `context` — the `employment_reporting_context` block (target/excluded statuses,
  portal URL, etc.). Falls back to `data.employment_reporting_context`.

Returns `{ analyze, index }`, where `index` is the reusable prebuilt search index
and `analyze(input)` runs the pipeline. `input` may be a plain string or
`{ text, visaStatus, locale }`.

### `analyzeEmploymentText(input, deps)`

Convenience one-shot wrapper equivalent to
`createEmploymentAnalyzer(deps).analyze(input)`.

### `EmploymentCodeAnalysis` (output of `analyze`)

```jsonc
{
  "normalizedInput": "…",
  "extracted": {
    "jobRole":          "…",   // 본인이 하는 일
    "workplaceType":    "…",   // 근무처 종류
    "businessActivity": "…",   // 근무처의 사업 활동
    "employmentType":   "…",   // 고용형태
    "visaStatus":       "…",   // 체류자격 (explicit input wins)
    "language":         "ko" | "en" | "mixed" | "unknown"
  },
  "occupationCandidates": [ /* Candidate[] — 직종 KSCO8 */ ],
  "industryCandidates":   [ /* Candidate[] — 업종 KSIC11 */ ],
  "ambiguityQuestions":   [ /* { flag, question, chips[] } */ ],
  "warnings":             [ /* legal caveats + final-confirm + visa notes */ ],
  "sourceNotes":          [ /* per-track provenance + portal */ ]
}
```

(`analyze` also returns `ambiguityFlags` and `matchedConcepts` for debugging.)

### `Candidate`

```jsonc
{
  "code":           "…",                 // exists in jobcode_master.json
  "name":           "…",
  "classification": "occupation" | "industry",
  "level":          "major|middle|minor|unit|detailed_unit",
  "levelLabel":     "대분류|중분류|소분류|세분류|세세분류",
  "isReportingLeaf": true,               // a reporting 세부코드 vs an upper class
  "path":           "…",                 // path_ko
  "score":          123,
  "confidence":     "high" | "medium" | "low",
  "matchedTerms":   ["…"],
  "reason":         "직종 세분류 · 신고용 세부코드 — '…' 키워드와 일치",
  "source":         { "classification": "…", "version": "…", "effectiveDate": "…" },
  "warning":        "…"                  // present only when confidence is low
}
```

### Browser bridge

When the module is loaded in a browser it attaches its public functions to
`window.EmploymentCodeAnalyzer` (`normalize`, `tokenize`, `detectLanguage`,
`extractEntities`, `buildIndex`, `searchTrack`, `createEmploymentAnalyzer`,
`analyzeEmploymentText`) so the existing non-module inline UI can call into it.
