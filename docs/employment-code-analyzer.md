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
   The richer extractor also returns `employerType`, `incomeStatus`
   (paid/unpaid/unknown), `performanceType` (singing/dancing/acting/…),
   `roleStatus` (owner/freelancer/trainee/instructor/employee), and a
   `legalSensitivity[]` list (e.g. `entertainment`, `tattoo`) that gates the
   legally-sensitive handling below.
3. **Umbrella decomposition** — vague or non-existent-as-a-single-code inputs
   (아이돌, 댄서, 타투이스트, 반영구화장, 알바, 회사원, 프리랜서, …) are matched
   against `data/employment/ambiguous_inputs.json` and **decomposed into real
   sub-role search terms**, never mapped to one invented code.
4. **Two-track classification** — search the occupation track (KSCO8) and the
   industry track (KSIC11) completely separately.
5. **Hybrid scoring** — score each canonical row against the raw query plus
   expanded synonym terms (code/name/alias hits, with depth- and leaf-bonuses).
   A `confidenceCap` from a broad/indirect concept can lower a candidate's
   confidence (e.g. tattoo work is capped to `low`).
6. **Ambiguity questions + follow-up chips** — when the input is underspecified,
   emit follow-up questions and a `followUpChips[]` list (clickable "더 정확히
   고르기" refinements) instead of dumping everything.
7. **Warnings + source notes** — always attach legal caveats and provenance,
   including governing-law notes for legally-sensitive inputs.

The output object now also carries `followUpChips[]`, and each **Candidate**
additionally exposes `officialName`, `classificationType`, `reasonKo`,
`reasonEn`, and `caveats[]` (see Public API).

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
- **「외국인 취업정보 온라인 신고제」** — confirmed **effective 2026-01-02**
  (확대 시행). 직종·업종 = 국가데이터처 표준직업/표준산업분류 참고; report changes
  within **15 days** (변경 15일 이내). Recorded as a `verified` entry in
  `classification_sources.json` `legal_sources` (`applies_to`:
  entertainment + tattoo). This is a 신고 (직종·업종·연간소득) obligation, not an
  adjudication of whether the activity is legally allowed.

**Governing-law source for legally-sensitive inputs**
- **문신사법 (Tattooist Act)** — passed the National Assembly on **2025-09-25**,
  **effective 2027-10-29** (2-year grace), covers 문신 and 반영구화장 as a tattoo
  act requiring a national license. Recorded as a `verified` `legal_sources`
  entry (`applies_to`: tattoo); confirm final text on 국가법령정보센터 (law.go.kr).
  As of 2026 it is passed but not yet in effect, and a code does not imply the
  activity is permitted. These legal notes are attached to the analysis output
  only when the input is legally sensitive.

These exact 고시 numbers, dates, and legal sources come from the data files —
they are not fabricated in the analyzer or in this doc.

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
- `trainee_status_unclear` — a 연습생 / trainee is present; asks whether the work
  is paid, training-only, public performance, an education program, or under a
  label contract (and caps confidence to `low`).
- `underspecified` — no usable role or workplace and no candidates; asks the user
  to describe both the work and the employer's business, with an example.

Umbrella terms matched from `data/employment/ambiguous_inputs.json` contribute
their own `question_ko` + `chips` directly, and a `followUpChips[]` list (general
chips, plus entertainment/tattoo domain chips when `legalSensitivity` applies)
gives one-click refinements.

---

## 5. Entertainment / performance inputs (댄서·아이돌·가수·배우·모델 등)

There is **no single official "아이돌" code** in the standard classifications.
Rather than invent one, the analyzer **decomposes** idol/entertainer umbrella
terms into the real sub-roles that actually exist in the table, via
`data/employment/ambiguous_inputs.json` (`idol`, `entertainer`, `dancer`,
`trainee` entries) plus the entertainment alias lexicon
(`data/employment/aliases.entertainment.{ko,en}.json`). For example `아이돌`
decomposes to 가수 / 무용가 / 안무 / 배우 / 아나운서 / 공연 예술가 and the
fixtures assert `notSingleExactName: "아이돌"` (no candidate name may equal the
umbrella term).

**Real codes used** (all verified to exist in `data/jobcode_master.json`; the
lexicon stores only the names as search keywords, never the codes):

- 직종 / occupation (KSCO8):
  - `2947` 무용가 및 안무가
  - `2946` 가수 및 성악가
  - `2945` 지휘자·작곡가 및 연주가
  - `2932` 배우 및 모델
  - `2933` 아나운서 및 리포터
  - `2647` 예능 강사
  - `3722` 연예인 및 스포츠 매니저
- 업종 / industry (KSIC11):
  - `9012` 공연단체
  - `9013` 자영 예술가
  - `90191` 공연 기획업
  - `8562` 예술학원

**Trainee (연습생) status.** A 연습생 / trainee input sets `roleStatus = "trainee"`,
raises the `trainee_status_unclear` ambiguity flag, and **caps confidence to
`low`**. A trainee's classification depends on whether they (1) work for pay,
(2) only train, (3) perform publicly, (4) are enrolled in an education program,
or (5) have a label contract — so the analyzer asks a follow-up rather than
guessing. **Whether a trainee has paid employment at all is itself a separate
question** (`incomeStatus` + the trainee follow-up), not something a code answers.

**Agency (연예기획사) mapping is indirect.** There is no exact standard-industry
code for a talent/entertainment agency, so 연예기획사 / 소속사 maps **indirectly
to 공연 기획업 (`90191`)**, is **capped to `medium`** confidence, and each
candidate carries a `candidate_caveat` saying so and pointing the user to HiKorea
업종조회.

---

## 6. Tattoo / cosmetic-tattoo inputs (타투이스트·문신사·반영구화장·눈썹문신)

There is **no dedicated 문신/타투 occupation or industry code** in KSCO8/KSIC11.
The tattoo lexicon (`data/employment/aliases.tattoo.{ko,en}.json`) therefore
produces only **broad indirect matches**, all **capped to `low` confidence**,
each carrying a `candidate_caveat`:

- 직종 / occupation: `4319` 기타 미용 관련 서비스 종사원, `4315` 메이크업 아티스트
  및 분장사, `431` 미용 관련 서비스 종사자.
- 업종 / industry: `96119` 기타 미용업, `96999` 그 외 기타 (달리 분류되지 않은)
  개인 서비스업, `96113` 피부 미용업.

**Legal caution (verified).** Tattoo inputs (`legalSensitivity` includes
`tattoo`) attach a 문신사법 (Tattooist Act) caution. The verified legal basis:
the **문신사법 passed the National Assembly on 2025-09-25** and is **effective
2027-10-29** (a 2-year grace period), and it treats both 문신 and 반영구화장 as a
tattoo act requiring a national license (면허). **As of 2026 it is passed but not
yet in effect.** This is recorded in `classification_sources.json` under
`legal_sources` (verified via 보건복지부 보도자료 / 국회 본회의 의결; the metadata is
press-release-based and the final wording must be confirmed on 국가법령정보센터,
law.go.kr). Crucially, **having a candidate code does NOT mean the activity is
legally permitted** — the analyzer is not a legal-permission checker.

**Cosmetic-tattoo boundary.** 반영구화장 / 눈썹문신 sits on the **beauty-vs-tattoo-
act boundary**: under existing classifications it can read as a beauty service
(매핑: 메이크업 아티스트 / 기타 미용 / 피부 미용업), but the 문신사법 counts it as a
tattoo act. Because the correct handling depends on the specifics, the analyzer
asks follow-ups distinguishing **시술 / 디자인만 / 강의 / 운영** and **직원 vs
사업주** before settling on candidates.

---

## 7. Limitations

- **KSCO8 is not fully loaded.** The runtime ships 대/중/소/세분류 only (728 rows);
  the 세세분류 (5-digit detailed unit) full table is pending. When the only
  occupation matches are non-leaf, a warning tells the user to confirm the detail
  code on HiKorea 직종조회. (KSIC11 *is* the full table, 2,038 rows.)
- **No dedicated tattoo or idol codes.** There is no 문신/타투 code and no single
  "아이돌" code. Tattoo work is matched **indirectly** (broad beauty/personal-
  service categories, `low` confidence) and idol/entertainer terms are
  **decomposed** into real sub-roles — neither is a precise match.
- **Talent-agency industry mapping is indirect.** 연예기획사 / 소속사 maps to 공연
  기획업, capped to `medium` with a caveat; there is no exact agency code.
- **Confidence caps are heuristic.** Confidence is computed relative to the top
  candidate's score (`high` / `medium` / `low`), not a calibrated probability,
  and the `low`/`medium` caps on sensitive inputs are deliberate guardrails.
- **The lexicon is alias-based.** Matching depends on the surface phrases in
  `synonyms.{ko,en}.json` and the entertainment/tattoo alias files; phrasings
  outside the lexicon fall back to raw-token retrieval only.
- **KSCO8 세세분류 is still pending.** The 5-digit detailed unit full table is not
  yet loaded (see above); detail codes must be confirmed on HiKorea 직종조회.
- **It is NOT a legal-permission checker.** Picking a code does not establish
  that the activity is allowed under a given 체류자격.
- **Final codes must be confirmed** on HiKorea / 1345 / 국가데이터처 통계분류포털
  (https://kssc.mods.go.kr).

---

## 8. How to update classification data

There are three layers; keep them separate.

1. **Canonical codes** — `data/jobcode_master.json` (a protected data file).
   Built by `scripts/build_employment_reporting_dataset.py`. This is the single
   source of truth for codes, names, levels, and paths. Do not hand-edit codes.
2. **Synonym / alias layer** — the concept lexicon, merged from several files by
   `scripts/employment_data_loader.mjs` (which the CLI and tests both use). All
   of these contain **no official codes** — only retrieval hints (`surface`,
   `occupation_terms`, `industry_terms`, `ambiguous_roles`, plus the richer
   `legal_sensitivity`, `confidence_cap`, `candidate_caveat`, `role_status`,
   `performance_type`, `employer_type` fields):
   - `data/employment/synonyms.{ko,en}.json` — base aliases.
   - `data/employment/aliases.entertainment.{ko,en}.json` — performance /
     entertainment roles and workplaces.
   - `data/employment/aliases.tattoo.{ko,en}.json` — tattoo / cosmetic-tattoo.
   - `data/employment/ambiguous_inputs.json` — umbrella terms and their
     decomposition (`decompose.occupation_terms` / `industry_terms`), follow-up
     `question_ko`, and `chips`. Add new phrasings to whichever file fits, to
     improve matching without touching canonical data.
3. **Source metadata + checksum** — `data/employment/classification_sources.json`,
   regenerated (together with its `legal_sources` array) by:

   ```
   node scripts/build_classification_sources.mjs
   ```

   This reads `jobcode_master.json`, derives consolidated provenance
   (classification names, 고시/revision, effective dates, portal, legal sources),
   and computes a `sha256` checksum of the canonical dataset. It **does not touch
   the codes**.

**Adapter approach for HiKorea dropdown mismatches.** If a HiKorea 직종/업종
dropdown differs from the public standard classification table, do **not** mutate
canonical data. Record the mismatch in the metadata's `known_mismatches` and
handle it in a runtime adapter layer (e.g. the KSCO8 세세분류 gap is surfaced as a
warning rather than by fabricating codes).

---

## 9. QA / test commands

```
# Regression suite: no hallucinated codes, tracks separated, source metadata
# present — now 51 fixtures including entertainment + tattoo cases.
node scripts/check_employment_code_analyzer.mjs

# Human-readable analysis of one description
node scripts/employment_analyze_cli.mjs "카페에서 바리스타로 일해요"

# Entertainment umbrella: decomposes 아이돌, trainee status, low confidence
node scripts/employment_analyze_cli.mjs "아이돌 연습생"

# Tattoo: JSON output, indirect low-confidence matches + 문신사법 caution
node scripts/employment_analyze_cli.mjs --json "타투이스트"

# Visa-aware entertainment example (agency-affiliated idol)
node scripts/employment_analyze_cli.mjs --visa E-6 "연예기획사 소속 아이돌"

# JSON output, with an explicit visa status
node scripts/employment_analyze_cli.mjs --json --visa E-7 "IT 스타트업 개발자"

# Regenerate consolidated source metadata + checksum (incl. legal_sources)
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

## 10. Safety & legal caution

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
    "employerType":     "…",   // 고용주 종류 (e.g. entertainment agency)
    "incomeStatus":     "paid" | "unpaid" | "unknown",
    "performanceType":  "…",   // singing|dancing|acting|broadcasting|… (연예)
    "roleStatus":       "…",   // owner|freelancer|trainee|instructor|employee
    "legalSensitivity": [ /* "entertainment" | "tattoo" | … */ ],
    "visaStatus":       "…",   // 체류자격 (explicit input wins)
    "language":         "ko" | "en" | "mixed" | "unknown"
  },
  "occupationCandidates": [ /* Candidate[] — 직종 KSCO8 */ ],
  "industryCandidates":   [ /* Candidate[] — 업종 KSIC11 */ ],
  "ambiguityQuestions":   [ /* { flag, question, chips[] } */ ],
  "followUpChips":        [ /* clickable refinement chips (string[]) */ ],
  "warnings":             [ /* legal caveats + final-confirm + visa + legal notes */ ],
  "sourceNotes":          [ /* per-track provenance + portal + legal_sources */ ]
}
```

(`analyze` also returns `ambiguityFlags` and `matchedConcepts` for debugging.)

### `Candidate`

```jsonc
{
  "code":              "…",              // exists in jobcode_master.json
  "name":              "…",
  "officialName":      "…",              // spec alias for name (name_ko/name_en)
  "nameEn":            "…",
  "classification":    "occupation" | "industry",
  "classificationType":"occupation" | "industry",  // spec alias
  "level":             "major|middle|minor|unit|detailed_unit",
  "levelLabel":        "대분류|중분류|소분류|세분류|세세분류",
  "isReportingLeaf":   true,             // a reporting 세부코드 vs an upper class
  "path":              "…",              // path_ko
  "score":             123,
  "confidence":        "high" | "medium" | "low",  // possibly capped to low/medium
  "matchedTerms":      ["…"],
  "reason":            "직종 세분류 · 신고용 세부코드 — '…' 키워드와 일치",
  "reasonKo":          "…",              // same as reason (Korean)
  "reasonEn":          "Occupation(KSCO8) unit · reporting-level code — matched terms: …",
  "caveats":           [ /* per-track caveats, e.g. tattoo/agency indirect-match notes */ ],
  "source":            { "classification": "…", "version": "…", "effectiveDate": "…" },
  "warning":           "…"               // present only when confidence is low
}
```

### Browser bridge

When the module is loaded in a browser it attaches its public functions to
`window.EmploymentCodeAnalyzer` (`normalize`, `tokenize`, `detectLanguage`,
`extractEntities`, `buildIndex`, `searchTrack`, `createEmploymentAnalyzer`,
`analyzeEmploymentText`) so the existing non-module inline UI can call into it.
