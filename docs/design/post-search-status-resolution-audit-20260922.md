# Post-search status resolution audit — 2026-09-22

Scope: the searched state of `index.html` (query → result), measured against the
two Ministry of Justice September 2026 manuals that are the baseline for this
sprint:

| Manual | Edition | Files in repo | Extraction used here |
| --- | --- | --- | --- |
| 사증발급 안내매뉴얼 (체류자격별 대상 첨부서류 등) | 2026.9 / 2026-09-01 | `docs/source-manuals/2026-09/visa_manual_260901.pdf` (519 pp), `docs/source-manuals/2026-09-01/visa_manual_260901.hwp` | PDF page corpus `data/manual-corpus/visa_manual_2026_09_01_pdf.json` (page provenance); HWP ViewText `…/2026-09-01/extracted/full_text/visa_manual_260901.txt` (structure, tables) |
| 외국인체류 안내매뉴얼 | 2026.9 / 2026-09-18 | `docs/source-manuals/2026-09/stay_manual_260918.pdf` (810 pp), `docs/source-manuals/2026-09/stay_manual_260918.hwp` | PDF page corpus `data/manual-corpus/stay_manual_2026_09_18_pdf.json`; HWP text `…/2026-09/extracted/full_text/stay_manual_260918.txt` |

Both editions are registered in `docs/source-manuals/source_manifest.json` as
`pending_review` / `needs_review`. Nothing in this audit promotes them: every
user-facing claim built from them is labelled as September 2026 original text
that has not yet been reviewed line-by-line by a human (`review_state`).

## 1. Current post-search hierarchy (BEFORE)

Measured in Chromium at 1280×900, 390×844 and 320×568 with the backend
unreachable (which is also the production fallback when `/api/search/unified`
fails). Screenshots: `artifacts/post-search-before/`.

Order of the first viewport for `F-1 연장`:

1. Compact header with the query, then the red error line "통합 검색을 불러오지
   못했습니다" (the interpretation strip lives in `assets/js/unified-search.js`
   and only renders from a backend payload — with no backend there is no
   "이렇게 이해했어요" at all).
2. Reference disclaimer band.
3. Tabs 전체 / 체류자격 안내 / 매뉴얼 원문.
4. **"매뉴얼에서 찾은 내용" — 32 raw manual pages**, first hit "4. 관광·휴양시설
   투자자에 대한 체류기간연장" (an F-2 section that merely mentions F-1). On a
   390 px phone the first two screens are raw excerpts; the F-1 status card is
   below all six excerpts and the "결과 더 보기" button.
5. Status card `F-1` (`#rlist article.vc`) — parent-level 방문동거 card with
   procedure tabs; the extension tab shows a legacy summary blob extracted from
   the 2026.6 manual and three "commonDocs".
6. Below: legacy landing sections (입국 전/후 track cards, coverage stats, form
   helper promos) leak into the searched state.
7. Fixed `.ai-fab` ("AI로 더 자세히 묻기") overlapping the excerpt list at the
   bottom right on every viewport.

Findings:

| ID | Severity | Finding |
| --- | --- | --- |
| A-01 | P0 | Raw manual excerpts (page-level retrieval, unreviewed) occupy the entire first viewport; structured guidance is below the fold on all mobile widths. The product behaves as a PDF Ctrl+F. |
| A-02 | P0 | Query interpretation ("이렇게 이해했어요") depends on a network round-trip to the backend router; the static site and every backend outage lose it entirely. Intent (`연장`) is not used to select the procedure client-side: the status card opens on its default tab. |
| A-03 | P0 | `F-1 연장` returns a parent-level document list ("통합신청서 / 여권 / 외국인등록증") as if universal. The 2026-09-18 stay manual has 15 distinct F-1 extension scenarios (pp. 356–363) with different document sets. Rendering parent data as a checklist is source contamination. |
| A-04 | P0 | `E-9 호텔` opens the E-9 card whose extension list is the manufacturing/EPS baseline; the hotel/hospitality track is E-9-5 (visa manual §27, 허용업종 table). Industry is not a resolver dimension anywhere. |
| A-05 | P0 | `F-6 자격변경` renders "F-6 → statusChange" scenario variants keyed only by the target; the current status (short-stay B/C holders are excluded by default, H-1 cannot change to F-6, German B-1 exception) is not an input. |
| A-06 | P1 | `F-2-7 연장` (exact subcode) is answered by the F-2 parent card; the subcode is only highlighted in the subcode preview. No direct resolution to the F-2-7 rule (stay manual p. 421ff: 80-point table, income grace rules, dependants F-2-71 / F-3-18). |
| A-07 | P1 | `D-2 연장` shows no academic-course clarification although D-2-1~4/7, D-2-5, D-2-6/8 have different stay-period rules and D-2-8/D-4 have a six-month wait for part-time work. |
| A-08 | P1 | Structured records still cite the 2026.6 (2026-06-17 / 06-23) editions; the page shows "사증 2026.09.01 · 체류 2026.09.18" for the raw search and "2026.6" inside the cards without stating that they may disagree. |
| A-09 | P1 | Document lists are flat arrays (`commonDocs`, `requiredDocs`, `conditionalDocs`) with no applicant role, no alternatives, no validity/authentication, no item-level provenance. Alternatives such as "체류지 입증서류(임대차계약서, 숙소제공 확인서, … 등)" are rendered as one opaque string or as several cumulative items. |
| A-10 | P1 | Special programs (지역특화형, Top-Tier, K-STAR, 광역형, 국내성장 청소년, 동포 통합) are `REGION-S` / `K-STAR` / `YOUTH-STAY` pseudo-records with `needsManualReview=true` and no procedure states; nothing routes `F-2-R`, `E-7-4R`, `F-2-T`, `D-10-T`, `F-2-7S` to the program rule. |
| A-11 | P2 | Legacy landing content (track cards, stats, promos) is rendered under the results in searched state; the AI FAB covers content; the "결과 더 보기" loads 12 more raw pages before any answer. |
| A-12 | P2 | Heading hierarchy in searched state: `h2` "매뉴얼에서 찾은 내용" precedes any answer heading; the status card uses `h4`/`h5` inside an `article` with no `h2/h3`. |
| A-13 | P2 | No status announcement when guidance resolves; the excerpt dialog restores focus, but the procedure tabs are `button`s without `role=tab`/`aria-selected`. |
| A-14 | P3 | Mixed type scales (civic 16px body vs. legacy 0.83rem card chrome) inside one viewport. |

No horizontal overflow was measured at 320/390/1280 in the BEFORE state
(`document.scrollWidth === innerWidth`).

## 2. Manual coverage analysis

### 2.1 Chapters

Both manuals carry their own 目次. They are the inventory the coverage manifest
is built from (`scripts/build_status_coverage_manifest.py`).

- 외국인체류 안내매뉴얼 2026-09-18: 41 chapters — 35 ordinary statuses (A-1 …
  H-1; F-4 and H-2 are folded into ch. 36) + ch. 36 외국국적동포 관련 (C-3-8, F-1,
  H-2, F-4, F-5) + ch. 37 지역특화형비자 + ch. 38 국내 성장 기반 외국인 청소년 취업·정주
  체류제도 + ch. 39 톱티어 비자 (D-10-T, E-7-T, F-2-T, F-5-T) + ch. 40 광역형 비자
  시범사업 + ch. 41 K-STAR 비자트랙 제도. Two preambles: 각종 체류허가 신청 시 유의사항,
  공통사항 (체류 일반).
- 사증발급 안내매뉴얼 2026-09-01: 40 chapters — 37 statuses (A-1 … H-2; F-4, F-5
  동포, H-2 refer to ch. 38) + ch. 38 알기쉬운 외국국적동포 업무매뉴얼 + ch. 39 톱티어
  비자 + ch. 40 K-STAR 비자트랙 제도. No 지역특화형 / 광역형 / 국내성장 chapter in the
  visa manual (they are stay-side regimes; the manifest records them as
  NOT_APPLICABLE for the visa domain rather than silently missing).

Chapter page ranges are detected from the PDF page corpus by chapter-title
headings and cross-checked against the HWP text order; where the PDF heading
detector fails (e.g. "외교(A-1)" whose title page shares the page with the
preamble) the manifest uses the first page whose `status_codes_detected`
contains the code inside the expected order window and flags
`page_detection: "window"`.

### 2.2 Status / substatus taxonomy

The HWP text carries explicit 세부약호 tables for: C-3 (10), D-2 (8) + D-4 (2),
D-3 (4), D-10 (4), E-6 (3), E-7 (8 + E-7-4R), E-8 (9), E-9 (7 industries), F-5
(26+), F-6 (3), Top-Tier family table (F-2-T/F-2-T1/F-1-15/F-1-24, F-5-T/F-5-T1,
E-7-T/F-3-17, D-10-T/F-3-10), 지역특화형 table (F-2-R/F-3-1R, E-7-4R/F-3-3R,
F-4-R/F-3-2R, F-5-6R). Other families define subcodes inline in section titles
(F-1: F-1-4/5/6/12/13/15/16/24/28/51/52/D…; F-2: F-2-2/3/4/5/7/7S/71/8/81/99/R/T;
G-1: G-1-1…G-1-12, G-1-99; E-10: E-10-1/2/3; D-8: D-8-1/2/3/4/4S; D-9: D-9-1/4/5;
H-2: H-2-7; K-STAR: F-2-7S, F-5-S1, F-2-71, F-5-S2).

Existing `visa_data.json` (42 records) lists 228 subcodes. Cross-check against
the September text (see §9 and `docs/audit/immigration-source-conflicts-20260922.md`):

- codes present in `visa_data.json` but not found anywhere in either September
  manual are recorded `UNVERIFIED` (not deleted — the protected file is not
  edited);
- codes found in the September manuals but absent from `visa_data.json` are
  added to the manifest as `SOURCE_ONLY` (e.g. F-1-51, F-1-52, F-1-28, F-2-81,
  D-8-4S, E-7-4R, F-3-1R/2R/3R, F-5-6R);
- legacy/transitional markers found in the text drive the temporal fields:
  H-2 new issuance stopped 2026-02-12 (`new_application_allowed=false`,
  `existing_holder_only=true`, `superseded_by=F-4`); D-3-1 "’06.12.31.까지 등록자"
  (`LEGACY_ONLY`); E-7-91 "T6(구약호)" alias; F-2-6 숙련생산기능 abolished
  2019-10-01 and 직권 정정 to F-2-99 (`LEGACY_ONLY`, `superseded_by=F-2-99`);
  F-1-1 legacy holders → F-2-2 conversion rule (`legacy_holder_rule`).

### 2.3 Special frameworks (first-class)

| Program | Manual chapter | Codes | Discriminators |
| --- | --- | --- | --- |
| 외국국적동포 (F-4 통합) | stay 36 / visa 38 | C-3-8, H-2, F-4, F-4-R, F-5-6/7/14, F-3/F-1 family | nationality (중국·CIS), H-2 existing holder, Korean-language proof, age ≤13 |
| 지역특화형비자 | stay 37 | F-2-R, F-3-1R, E-7-4R, F-3-3R, F-4-R, F-3-2R, F-5-6R | region (인구감소지역), local-government recommendation, prior status (E-9/E-10/H-2 ≥2y for E-7-4R), 5-year re-participation bar |
| 국내 성장 기반 외국인 청소년 | stay 38 | D-10-1 (특례), E-7-Y, F-2-R | age 18–24, 7 years in Korea before 18, domestic K-12 graduation |
| 톱티어 (Top-Tier) | stay 39 / visa 39 | D-10-T, E-7-T, F-2-T, F-2-T1, F-5-T, F-5-T1, F-1-15, F-1-24, F-3-17, F-3-10 | track (첨단산업 산업통상부 추천 / 과학기술 과기정통부 추천), 유망/예비 tier, family role |
| 광역형 비자 시범사업 | stay 40 | D-2 (10 광역지자체), E-7 (5 광역지자체) | metropolitan/provincial government, program-specific recommendation |
| K-STAR 비자트랙 | stay 41 / visa 40 | F-2-7S, F-5-S1, F-2-71, F-5-S2 | participating university (32), degree, points (90/200) |

## 3. Procedure model

Procedure identifiers (single catalog, `data/guidance-rules-202609.json →
procedures`), each bound to one source domain:

| id | domain | ko | en |
| --- | --- | --- | --- |
| visa_issuance | visa | 사증발급 | Visa issuance |
| visa_issuance_confirmation | visa | 사증발급인정서 | Confirmation of visa issuance |
| electronic_visa | visa | 전자사증 | Electronic visa |
| status_grant | stay | 체류자격 부여 | Status grant |
| status_change | stay | 체류자격 변경 | Change of status |
| extension | stay | 체류기간 연장 | Extension of stay |
| registration | stay | 외국인등록 | Foreign resident registration |
| card_reissue | stay | 외국인등록증 재발급 | Residence card reissue |
| activities_outside_status | stay | 체류자격외 활동 | Activities outside status |
| part_time_work | stay | 시간제 취업 | Part-time work permission |
| workplace_change | stay | 근무처 변경·추가 | Workplace change / addition |
| workplace_report | stay | 근무처 신고 | Workplace reporting |
| reentry | stay | 재입국허가 | Re-entry permit |
| residence_report | stay | 체류지 변경 신고 | Change-of-address report |
| registration_info_report | stay | 등록사항 변경신고 | Registration-information report |
| program_condition_change | stay | 허가조건 변경 | Program condition change |

Per code+procedure state enum: `SUPPORTED`, `CONDITIONAL`, `NOT_APPLICABLE`,
`GENERALLY_NOT_PERMITTED`, `EXCEPTION_ONLY`, `LEGACY_ONLY`, `SOURCE_ONLY`,
`UNVERIFIED`. The manual's own "해당사항 없음" lines (e.g. F-5 체류기간 연장, D-8
근무처 변경 → 등록사항 변경신고, E-9 체류자격외 활동 억제) map to
`NOT_APPLICABLE` / `GENERALLY_NOT_PERMITTED` with the page anchor.

## 4. Transition model

`transitions[]` entries: `{from: [current codes or classes], to, procedure:
status_change, conditions, exclusions, exceptions, documents_ref, source}`.
Seeded from the September stay manual for the flows the brief names: → F-6-1
(short-stay holders excluded except 임신·출산·자녀양육 review, German B-1 exception,
H-1 barred), → F-2-7 (excluded prior statuses), → F-2-R (excluded D-3/D-4/E-6-2/
E-8/E-9/E-10/G-1/H-1, 5-year bar), E-9/E-10/H-2 → E-7-4R (≥2 years), D-2 → D-10
(graduates), G-1 → E-9 recovery, F-1 → F-2-2 legacy rule, F-2-7 → D-10 fallback
after extension refusal. When the user's current status is unknown and the
target has exclusions, the resolver asks for it before any checklist.

## 5. Document requirement model

Every document item in `guidance[*].documents[]`:

```
{ id, name_ko, name_en, requirement_level, applicant_role, applies_when,
  does_not_apply_when, alternatives_group, original_or_copy, validity_period,
  translation_required, apostille_required, consular_confirmation_required,
  issuer, where_to_obtain, submission_channel, substitution_allowed,
  substitute_documents, administrative_information_exemption,
  previous_submission_exemption, notes, source: {manual, section, anchor, page},
  review_state }
```

`requirement_level` ∈ REQUIRED_BASELINE, CONDITIONAL_REQUIRED,
ADDITIONAL_IF_APPLICABLE, ALTERNATIVE_DOCUMENT, MAY_BE_REQUESTED_BY_OFFICER,
ADMIN_INFO_CHECKABLE, PREVIOUSLY_SUBMITTED_MAY_BE_OMITTED,
SOURCE_MENTIONS_BUT_NOT_STRUCTURED, NOT_APPLICABLE, LEGACY_ONLY.

Checklist completeness ∈ FULLY_STRUCTURED, PARTIALLY_STRUCTURED, SOURCE_ONLY,
REQUIRES_CLARIFICATION, UNVERIFIED. Only FULLY_STRUCTURED lists may be titled
"필요한 서류"; everything else is titled "현재 확인된 기본 서류" or replaced by the
clarification prompt.

Every item carries an `anchor`: a whitespace-insensitive substring of the
manual text. The build resolves the anchor to a PDF page; the QA script fails if
the anchor is not found on that page (so a transcription that drifts from the
source cannot ship).

## 6. Common / global overlay model

From 유의사항 / 공통사항 (stay pp. 3–12, visa pp. 3–5), each with `applies_when`:

| overlay | condition | source |
| --- | --- | --- |
| 국내 발급 서류 유효기간 3개월 | any domestic certificate without its own validity | stay 유의사항 1 / visa 유의사항 1 |
| 기제출 서류 제출 생략 | document already on the registered-foreigner record | stay 유의사항 2 |
| 해외 발급 서류 아포스티유·영사확인 | document issued abroad | stay 유의사항 5 / visa 4 |
| 행정정보 공동이용 시 제출 생략 | 주민등록등본·가족관계증명서·사업자등록증·납세증명 등 | stay 유의사항 6 / visa 6 |
| 의료 서류 밀봉 제출 | 건강진단서·마약검사확인서·채용신체검사서 | stay 유의사항 7 |
| 신청 시 국내 체류 필수 | every stay procedure | stay 유의사항 8 |
| 심사수수료 반환 불가 + 수수료표 | fee-bearing stay procedures; F-6 reduced fees | stay 공통사항 1 |
| 여권 유효기간 내 체류기간 부여 | long-term statuses except A-1~A-3, F-5, 난민 F-2/F-1, G-1, 무국적 | stay 공통사항 2 |
| 직업·연간소득 신고 | D-7~D-9, E-1~E-10, F-2, F-4, F-6, H-2 on registration/any permit | stay 공통사항 3 |
| 만 6~18세 재학증명 | applicant aged 6–18 | stay 공통사항 4 |
| 결핵진단서 | 35 high-risk nationalities under listed triggers; exempt A-1~A-3, <6y, pregnant | stay 공통사항 5 / visa 공통사항 1 |
| 심사 시 서류 가감 가능 (officer discretion) | always shown once per checklist | both manuals' 유의사항 preamble |

Final guidance composition: status rule + procedure rule + transition rule (if
any) + special-program rule (if any) + overlays whose `applies_when` is met by
the resolved context.

## 7. Source-conflict findings (summary)

See `docs/audit/immigration-source-conflicts-20260922.md`. Headline items:

- Edition lag: every structured record cites 2026.6 (06-17 / 06-23) while the
  raw search cites 2026.9. Guidance built here cites 2026.9 pages and tells the
  user when the legacy card differs.
- E-7-4 income threshold 2,500만원 (legacy summary) vs 2,589만원 (2026.9).
- E-9 extension baseline unchanged, but hotel/hospitality (E-9-5) region and
  occupation limits exist only in the visa-manual industry table.
- H-2: legacy record label "(신규발급 중단)" is consistent with 2026-02-12 stop;
  the record still exposes a visa-issuance-shaped procedure list.
- F-2-6 in `visa_data.json` is an abolished code (2019-10-01) with no legacy
  marker.

No protected file is modified; conflicts are recorded and the new layer fails
closed (SOURCE_ONLY) wherever they matter.

## 8. Mobile / accessibility / visual issues (BEFORE)

- Mobile: excerpt list is the whole first two screens; the fixed FAB overlaps
  the last excerpt's action row at 320 px; the searched header repeats the
  disclaimer band (~110 px) above any content.
- Accessibility: no landmark/heading for the answer; interpretation strip is a
  `role=status` that never renders offline; procedure tabs lack tab semantics;
  no announcement on resolver step change (there is no resolver).
- Visual: cards inside cards (status card → manual-layout → doc-group grid →
  doc tiles), multiple equal-weight CTAs (view-mode toggle, next-action area,
  route chooser, AI CTA), badges in the card header.

## 9. Implementation plan

1. `scripts/build_status_coverage_manifest.py` → `data/status-coverage-202609.json`
   (+ `reports/data-coverage/status-coverage-202609.{md,json}`); `--check` mode
   for CI.
2. `data/guidance-rules-202609.json` (authored, anchored) → compiled
   `data/status-guidance-202609.json` by the same build (anchors → pages).
3. `assets/js/status-guidance.js` + `assets/css/status-guidance.css`: pure
   interpret/resolve/compose/render exposed on `globalThis.VisableStatusGuidance`;
   DOM mount above the manual results; KO/EN; resolver with back/unsure; evidence
   layer reusing the civic page dialog; contextual Waymaker link; FAB hidden in
   searched state.
4. QA: `scripts/check_status_coverage_manifest.mjs`,
   `scripts/check_document_guidance.mjs`, `scripts/check_status_resolver.mjs`
   wired into `scripts/check_repo.sh`; `tests/e2e/post-search-guidance.spec.mjs`
   (Chromium, 5 viewports); WebKit flow added to `scripts/mobile_webkit_qa.mjs`
   (runs in the PR `mobile-webkit-qa` job).
5. Visual QA before/after at desktop, 390, 320; EN.

Priority: P0 (A-01…A-05) and P1 (A-06…A-10) are addressed by the new layer;
A-11/A-12/A-13 by the shell/CSS; A-14 partially (legacy card typography is out
of scope).

## 10. Explicit non-goals

- No edit to `visa_data.json`, `doc_master.json` or their backend copies.
- No promotion of the 2026.9 editions to `current`/approved.
- No rewriting of the legacy status card renderer; it remains reachable below
  the new guidance and via the "체류자격 안내" tab.
- No new legal requirements: every document/condition string is anchored to
  manual text.
- No homepage rebuild, no framework migration, no AI chatbot replacement.

## 11. Results (AFTER) — 2026-09-22

Measured with the same Chromium harness (backend unreachable, 1280×900 /
390×844 / 320×568). Screenshots: `docs/design/screenshots/post-search-20260922/`
(`before-*` vs `after-*`) and the full set in `artifacts/post-search-after/`
(local, not committed).

Hierarchy now rendered for `F-1 연장` (all three viewports, zero console errors,
`document.scrollWidth === innerWidth`, AI FAB hidden in the searched state):

1. "F-1 · 체류기간 연장(으)로 이해했어요 방문동거" + 수정 (procedure chips, code field).
2. Question "F-1(방문동거)을 어떤 이유로 받으셨어요?" — 9 options + 잘 모르겠어요;
   subsequent questions only when they still split the remaining candidates
   (marriage family → marriage migrant / naturalized → first / subsequent →
   childcare / humanitarian); back link; answered chips with 변경.
3. Answer "F-1-5 결혼이민자의 부모 등 가족 — 외국인등록 및 최초 체류기간 연장 (자녀 양육지원)"
   with 체류기간 / 수수료 facts and 확인할 조건.
4. 준비할 서류 grouped 필수 / 조건부 / 해당 시 / 행정정보 / 기제출 / 심사관 요청 with
   per-item page provenance, alternatives, and the officer note exactly once.
5. 공통으로 확인할 것 (overlays whose condition is met).
6. 다음 할 일 (HiKorea guide, form helper, 1345, legacy card, contextual Waymaker
   link `ai.html?visa_code=F-1-5&selected_procedure_key=extension`).
7. 공식 매뉴얼 근거 (stay manual 2026-09-18 page buttons → civic page dialog, PDF
   `#page=` links). 8. 관련 절차.

| Finding | Status after |
| --- | --- |
| A-01 raw excerpts first | fixed — guidance mounts above the manual results; excerpt list starts at 3 hits |
| A-02 interpretation needs backend | fixed — `interpret()` runs client-side from the bundle |
| A-03 parent list as universal | fixed — parent codes ask first; unresolved/parent states never render a required list (QA-guarded) |
| A-04 E-9 호텔 → manufacturing | fixed — 호텔 pre-answers E-9-5; the procedure is asked, not guessed |
| A-05 F-6 change ignores current status | fixed — transition asks the current status; short-stay / H-1 outcomes with the German B-1 and pregnancy exceptions |
| A-06 F-2-7 exact | fixed — exact subcode skips questions; F-2-7S served by the F-2-7 rule with the K-STAR program note |
| A-07 D-2 clarification | partially — extension / part-time / registration resolved by intent; course-type dimension asked only where it splits the rule |
| A-08 edition lag | disclosed — every answer cites 2026.9 pages; conflicts report lists all 37 records |
| A-09 flat document arrays | fixed in the new layer (legacy card untouched) |
| A-10 special programs | fixed — 6 program records, first-class answers for 톱티어 / K-STAR / 지역특화형 / 광역형 / 청소년 / 동포 |
| A-11 FAB / legacy sections | FAB hidden in searched state; legacy sections out of scope (see non-goals) |
| A-12 / A-13 heading & announcements | guidance has `h2` answer title, `role=status` interpretation, focus moves to the answer title on each step |
| A-14 type scale | not addressed (legacy card) |

Counts (from `python3 scripts/build_status_coverage_manifest.py --check`):
chapters stay 41 (+2 preambles) / visa 40 (+2 preambles); status 37; substatus
221; scenario 5; special programs 6; coverage SUPPORTED 67 / PARTIAL 50 /
SOURCE_ONLY 116 / UNVERIFIED 35 / LEGACY_ONLY 1; guidance entries 110; document
items 687 (84 fully structured / 9 partially / 17 source-only procedures);
source conflicts 77.

QA: `check_status_coverage_manifest.mjs` 470 checks, `check_document_guidance.mjs`
913 checks, `check_status_resolver.mjs` 61 flows, `tests/e2e/post-search-guidance.spec.mjs`
12 tests × 2 projects (24 passed, Chromium). WebKit journeys (F-1 연장, E-7, E-9,
D-2) are added to `scripts/mobile_webkit_qa.mjs`, which only runs in the CI
`mobile-webkit-qa` job (the WebKit download is blocked in the authoring sandbox).

