# Search intelligence · Waymaker Quick Answer · document accuracy audit — 2026-09-22

Scope: the searched state of `index.html` (query → guidance), the Waymaker
handoff, the document/fee data behind it, the homepage source copy and the
language UX. Measured on the committed tree at `10c57e5` (PR #631) served
statically with `/api/*` aborted, which is also the production fallback when
the Railway backend is unreachable. Screenshots:
`docs/design/screenshots/search-waymaker-20260922/before/`.

Source baseline used for every claim in this audit and in the implementation
that follows it:

| Tier | Source | Edition / date | How it is used |
| --- | --- | --- | --- |
| 1 | 출입국관리법 | 법률, 시행 2026-01-23 (law.go.kr MST 272921) | 제35조 등록사항 변경신고 사항, 제36조 체류지 변경신고, 제87조 수수료 |
| 2 | 출입국관리법 시행령 | 대통령령, 시행 2026-09-15 (MST 289697) | 제40조 외국인등록, 제42조 외국인등록증 재발급, 제44조 등록사항 변경신고, 제45조 체류지 변경신고 |
| 3 | 출입국관리법 시행규칙 | 법무부령, 시행 2026-09-15 (MST 289833); 별지·별표 text `docs/source-manuals/law/rule_1106_full.txt` (제1106호) | 제44조의2 재입국허가 면제, 제49조의2 등록사항 변경 범위, 제49조의3 체류지 변경 첨부서류·서식, 제72조 수수료, 제73조 납부방법, 제74조 감면, 별지 제34호 통합신청서, 별표 5의2 |
| 7 | 사증발급 안내매뉴얼 | 2026.9 / 2026-09-01 | 사증 절차 (unchanged in this sprint) |
| 7 | 외국인체류 안내매뉴얼 | 2026.9 / 2026-09-18 (`docs/source-manuals/2026-09/extracted/full_text/stay_manual_260918.txt`, PDF corpus) | 체류 절차 문서 목록, 공통사항 수수료표(p.4), D-2 등록사항·체류지 변경, 수수료 면제 문구 |
| 10 | Product-owner supplied cases | this brief | Jeju F-6-1, GKS, G-1-99 — treated as *investigation inputs*, never as evidence |

Blogs, cafés, agencies and SEO pages were not consulted and are not cited.

Severity scale: **P0** incorrect immigration guidance, source contamination,
document-form or fee fabrication, AI hallucination · **P1** broken
procedure-only routing, broken Quick Answer, missing required context,
misleading documents/fees, major mobile failure · **P2** hierarchy, design,
readability · **P3** polish.

---

## 1. Current search routing

`assets/js/status-guidance.js` owns interpretation and resolution:

- `interpret()` extracts status codes (regex + `normalizeCode`), one alias
  (longest term), one procedure (longest keyword), and family pre-answers.
  Its output shape is `{codes, aliasCandidates, procedure, program, preAnswers,
  confidence}` — a *visa code + keyword* model.
- `nextStep()` resolves program → alias question → **`if (!status) return
  { kind: 'no-status' }`** → procedure question → transition → subtype
  dimensions → resolved / unresolved / source-only.
- The unified layer (`unified-search.js`) renders an interpretation strip only
  from a backend payload; with no backend it prints the red line "통합 검색을
  불러오지 못했습니다" at the top of every result.
- The manual corpus search (`civic-search.js`) renders "매뉴얼에서 찾은 내용"
  with page counts and "매뉴얼 범위" filter under tabs 전체 / 체류자격 안내 /
  매뉴얼 원문.

| ID | Sev | Finding |
| --- | --- | --- |
| R-01 | P1 | There is no intent layer. A query is either "has a code" or "has nothing"; procedure, object (등록증/여권/주소), office (제주), program (GKS), user conditions (분실/훼손) and question form are not extracted separately. |
| R-02 | P1 | Procedure keyword matching is "longest substring wins, ties by catalog order". `ARC 재발급` ties `arc` (registration) with `재발급` (card_reissue) and resolves to **registration**. `등록증 잃어버렸어` and `등록증 훼손됐어` match nothing (no 잃어버/훼손 lexicon). `residence card reissue` → `residence card` (registration) beats `reissue`. |
| R-03 | P1 | Object words (`arc`, `residence card`, `등록증 발급`) live inside the *registration* procedure keyword list, so any card-related query is pulled toward 외국인등록. |
| R-04 | P2 | Confidence is a three-valued label with `HIGH` for any code + procedure; it never reflects a mismatch between object and procedure. |

## 2. Procedure-only failure (confirmed regression)

Reproduced at 1280 / 390 / 320 (`before/*card-reissue*.png`): `외국인등록증
재발급` → interpretation strip reads "외국인등록증 재발급(으)로 이해했어요",
`data-sg-kind="no-status"`, heading **"체류자격을 찾지 못했어요"**, then the
manual tabs and four raw excerpts of the 통합신청서 annex.

| ID | Sev | Finding |
| --- | --- | --- |
| P-01 | P1 | `nextStep()` discards a correctly identified procedure whenever no status is present. Card reissue, address report, registration-information report and re-entry all have a nationwide common rule in law that does not depend on status (시행령 제42조·제44조·제45조, 시행규칙 제44조의2·제49조의3·제72조·제73조). |
| P-02 | P1 | The procedure catalog has no notion of *context requirement*. Extension genuinely needs a status; card reissue does not; the router cannot tell them apart. |
| P-03 | P1 | The bundle has **zero** guidance entries for `card_reissue` and `residence_report`, and one (D-2) for `registration_info_report`. The builder marks these procedures `UNVERIFIED` for every code because the manual has no per-status section for them — the common rule lives in the 시행령/시행규칙 and in the manual's 공통사항 / D-2 chapter, none of which the authoring layer models. |
| P-04 | P2 | The dead-end copy tells the user to add a code "(예: F-6, D-2-1)" although a code would not change the card-reissue answer. |

Source facts established for the common layer (verbatim sources bound in
`scripts/status_guidance/author_rules.py`):

- **외국인등록증 재발급** — 시행령 제42조: reasons ① 분실 ② 헐어서 못 쓰게 됨
  ③ 적는 난 부족 ④ 체류자격 변경허가 ⑤ 법 제35조 제1호 사항 변경신고 ⑥ 일괄
  갱신; application = 재발급 신청서 + **사진 1장**; for reasons ②–⑥ the
  **original card is attached** (분실 제외). Form = 별지 제34호 통합신청서
  ("등록증 재발급" checkbox; "외국인 등록 및 등록증 재발급 시에만 사진 부착";
  반환용 계좌번호 기재). Fee = 시행규칙 제72조 제10호 **3만 5천원**, paid in
  **현금 또는 현금 납입 증표** (제73조 제1호 괄호 — *not* 수입인지), no online
  reduction (제74조 제2항 lists only 근무처·자격변경·연장·재입국), exemption only
  when the reissue is due to an issuing error (제74조 제1항 제7호); the stay
  manual states twice that 정부초청장학생 등 수수료 면제 대상자도 등록증
  발급·재발급 수수료는 납부 (p. D-2 chapter, lines 1305 / 2538).
- **체류지 변경신고** — 법 제36조 (15일 이내, 새 체류지 시·군·구/읍·면·동 or
  출입국관서), 시행령 제45조 (신고서 + 법무부령 서류; 정보통신망 신고 가능),
  시행규칙 제49조의3 (별지 제34호/34호의2/34호의3 at the immigration office,
  별지 제34호의4~8 at the local government; 첨부서류 = 임대차계약서 / 매매계약서
  / 그 밖에 체류지 이전 사실을 확인할 수 있는 서류). Manual D-2 chapter:
  "체류지변경신고서, 여권 및 외국인등록증". No fee item exists in 제72조.
- **등록사항 변경신고** — 법 제35조 (성명·성별·생년월일·국적 / 여권번호·발급일
  ·유효기간 / 법무부령 사항), 시행규칙 제49조의2 (소속기관 변경 for D-1, D-2,
  D-4~D-9; 재학 여부; D-10 연수기관; H-2 취업개시·변경; 직업·연간소득), 시행령
  제44조 (신고서 + 외국인등록증 + 여권; 제35조 제1호 변경 시 등록증 재발급).
  Manual: "수수료 없음" (D-2 p. 2552, D-8/D-9 etc.), D-2 학교 변경 adds
  재학증명서 + 前 학교 제적증명서.
- **재입국허가** — 시행규칙 제72조 제7·8호 (단수 3만원 / 복수 5만원), 제74조
  제2항 제3호 (온라인 20% 감경), 제44조의2 (등록외국인 1년 이내 / F-5 2년 이내
  면제).

## 3. Status resolution

The subtype resolver (PR #631) is sound for the families it covers (F-1, D-2,
E-9, E-7, E-8, F-2, F-6, G-1, D-10, D-4, D-8, F-3, E-10, C-3, H-1). Gaps:

| ID | Sev | Finding |
| --- | --- | --- |
| S-01 | P1 | When the procedure is known but the status is not (`체류기간 연장`, `가족비자 연장하고 싶어`), the layer shows the dead end instead of asking *which status* in ordinary language. The alias table already carries plain-language options (배우자/학생/취업/가족) but is only consulted when the query contains an alias term. |
| S-02 | P2 | The "수정" editor exposes a raw code field first; there is no ordinary-language status picker. |
| S-03 | P2 | `GKS`, `정부초청장학생` are not recognised as a user condition; `제주` is not recognised as an office. |

## 4. Waymaker Quick Answer

There is none. `waymaker-navigator.js` (ai.html) is a separate guided intake
(language → location → status → procedure) backed by `/api/procedure-packet`;
the searched state only links to it ("상황이 복잡한가요? Waymaker로 추가
분석"). A sentence such as `F-6 연장하려면 뭐 필요해?` is treated exactly like
`F-6 연장` — correct data, no answer-shaped summary, no fee at a glance, no
follow-up carrying context.

| ID | Sev | Finding |
| --- | --- | --- |
| W-01 | P1 | No Quick Answer model, composer, renderer or tests exist. |
| W-02 | P1 | The AI follow-up handoff (`ai.html?visa_code=…&selected_procedure_key=…`) carries only identifiers; documents, forms, fees, local practice and sources are rediscovered by the chatbot. |
| W-03 | P0 (risk) | Nothing prevents an AI enhancement from originating facts: there is no validator that binds AI wording to a structured model. Must be built before any AI wording is shown. |

## 5. Document requirements

`data/guidance-rules-202609.json` → 110 entries / 687 items, every item
anchored to a manual page. Requirement levels, roles, alternatives, admin-info
exemption and officer discretion are modelled.

| ID | Sev | Finding |
| --- | --- | --- |
| D-01 | P1 | **수수료 is a document.** `item('fee')` appears in the 필수서류 group of every structured procedure (`before/desktop-1280-f6-1-resolved-full.png`: ✓ 통합신청서 ✓ 여권 ✓ 수수료). |
| D-02 | P1 | The fee fact row shows the unresolved table string "6만원 (결혼이민 F-6: 3만원)" for a resolved **F-6-1** answer instead of the applicable 3만원. |
| D-03 | P2 | Document rows are visually identical accordions; no physical-form signal on the collapsed row. |
| D-04 | P2 | Group labels are correct but the "행정정보 공동이용" tag repeats on every eligible row instead of grouping. |

## 6. Original / copy model

| ID | Sev | Finding |
| --- | --- | --- |
| F-01 | P1 | There is no physical-form field on document items (`original_or_copy` exists in the item schema but is set nowhere). Form is only visible when it is baked into the document *name* (`여권 원본`, `여권 사본`, `고용계약서 원본 및 사본`, `사업자등록증 사본`). |
| F-02 | P0 (latent) | Because form lives in the name, a global document definition (`passport`) cannot carry different forms per procedure, and nothing stops a future edit from adding "원본 및 사본" to the shared `passport` definition. The manual itself varies: D-2 외국인등록 "여권 및 사본 1부" (p. 1302), B-1 연장 "여권 원본" (p. 678), D-10 "여권사본" (p. 4057), F-6-1 연장 "여권" (unspecified). |
| F-03 | P1 | No coverage report exists; the share of items whose form is source-explicit is unknown (measured below by the new report: see §17). |

## 7. Fees

| ID | Sev | Finding |
| --- | --- | --- |
| E-01 | P1 | Fees are a single overlay table keyed by procedure with free-text amounts (`'6만원 (결혼이민 F-6: 3만원)'`). No amount as a number, no payment instrument, no channel, no exemption structure, no per-status resolution, no source article. |
| E-02 | P0 | The overlay says "체류허가 수수료는 출입국관리법 시행규칙 제72조에 따릅니다" but the card-issue/reissue fee is *not* payable by 수입인지 (제73조 제1호). Any UI that said "수입인지" for the card fee would be wrong; today the UI says nothing, which is the lesser problem. |
| E-03 | P1 | Regulation vs manual disagreement: 시행규칙 제72조 제2호 단서 sets **2만원** for D-2/D-4 시간제 취업 허가, the 2026.9 stay manual D-2 chapter says "※ 수수료 면제" (line 1108). Recorded in `docs/audit/immigration-source-conflicts-20260922.md`; the UI must show 확인 필요, not pick one. |
| E-04 | P1 | Online reductions (제74조 제2항: 근무처 변경·추가, 자격변경, 연장, 재입국 20% 감경) are absent. |

## 8. Fee exemptions

Investigation of the product-owner cases:

| Case | Finding | Handling |
| --- | --- | --- |
| F-6 extension fee | 시행규칙 제72조 제6호 단서: 3만원 (일반 6만원). Manual p.4 table agrees. Online −20% applies (제74조 제2항 제2호). | structured, `VERIFIED` |
| GKS extension-fee exemption | The stay manual's only GKS fee statement is in the **D-4→D-2 체류자격 변경** section ("GKS 장학증서 소지자는 수수료 면제", line 1182). 시행규칙 제74조 제1항 제2호 exempts 자격변경·연장·재입국 for D-1/D-2/D-4 holders invited by the Government or 정부출연연구기관 that bears 학비 등 국내체재비 — it does not name GKS. The manual also states GKS-type exemptees **still pay the card issue/reissue fee** (lines 1305, 2538). | extension: `CONDITIONAL` exemption citing 제74조 제1항 제2호 with "확인 필요"; status change: `VERIFIED` manual statement; card fees: explicit "면제 안 됨" |
| G-1-99 extension-fee exemption | The G-1 chapter says "수수료는 일반 체류외국인과 동일" (line 14795) for the humanitarian/lawsuit cases and lists 수수료 for G-1-99 (line 14826). No exemption found in 제74조. | not structured; UI shows "면제 근거 확인되지 않음" |
| D-2 registration + extension together | Manual: "외국인등록 시, 체류기간 연장허가를 동시에 신청하는 경우에 한하여 연장 수수료 면제" (line 1304). | structured, manual-only, `NEEDS_REVIEW` |
| Card reissue due to issuing error | 제74조 제1항 제7호. | structured, `VERIFIED` |
| Re-entry within 1 year (F-5: 2 years) | 제44조의2: permit itself not required → no fee. | structured, `VERIFIED` |

## 9. Local practice

| ID | Sev | Finding |
| --- | --- | --- |
| L-01 | P1 | No layered truth model exists. `data/official_web_overlays.json` covers consular (visa) overlays only; nothing represents a domestic office. |
| L-02 | P0 (risk) | The Jeju F-6-1 case has **no authoritative source**: the 2026.9 stay manual mentions 제주 31 times, none about 체류지 입증서류 waivers (mentions are 영어교육도시, 무사증, 특별법). It must be stored as an unverified report, never rendered as guidance. |

## 10. User reports

None exist. Backend inspection: `backend/paradiso_backend.py` exposes no
report/feedback route; `api/` (Vercel) has only enforcement functions; there is
no datastore. A submission endpoint that pretends to persist would be
dishonest (§38 of the brief). Decision: ship the schema, the client flow, a
validating Vercel function that forwards to an operator-configured webhook when
`LOCAL_PRACTICE_REPORTS_WEBHOOK_URL` is set and otherwise returns an explicit
`NOT_CONFIGURED` state that the UI shows truthfully.

## 11. Source hierarchy

The structured layer cites the manuals only. Where the manual is silent
(card reissue, address report) or where the manual and the regulation disagree
(시간제 취업 fee), the regulation must be bound as a source with its article and
law.go.kr identifiers. The manuals remain the authority for status-specific
document lists; the regulation is the authority for fees, payment method,
exemptions and the common procedures.

## 12. Source UX

| ID | Sev | Finding |
| --- | --- | --- |
| U-01 | P2 | Primary copy is manual-centric: "매뉴얼에서 찾은 내용", "매뉴얼 범위", "사증 2026.09.01 · 체류 2026.09.18 · 4 쪽 검색됨", "공식 매뉴얼 근거", "2026.09 원문 · 검토 전", "매뉴얼 원문 검색 결과 더 보기", tab "매뉴얼 원문", tool "매뉴얼 본문 검색", disclaimer "2026년 9월 판 매뉴얼 원문을 구조화한 참고 정보이며…". |
| U-02 | P2 | Evidence list is fully expanded with page numbers as decoration; the excerpt panel dominates the first viewport at 390 px after the dead end. |

## 13. AI grounding

`ai.html` `/api/ask` already runs through backend safety guardrails, but the
searched state has no AI at all. Requirements for the new layer: AI may only
rephrase a validated model; a validator must reject any number, document name,
office or fee not present in the model; failure must fall back to the
deterministic card; deterministic questions (fee amount) must not call the model.

## 14. Global language UX

| ID | Sev | Finding |
| --- | --- | --- |
| G-01 | P1 | Two overlapping systems: the civic home shows only **KO / EN** pills (`.cs-languages`), while the 15-language selector (`#languageMenu`, `LANGUAGE_OPTIONS`) lives in `#topCtrls`, which civic mode hides (`.civic-refresh #topCtrls { display:none }`). 13 languages are unreachable from the home. |
| G-02 | P1 | In the searched state there is no language control at all (`#civicLanding` is hidden). |
| G-03 | P2 | The legacy menu shows codes + English exonyms; native names are secondary. No search. |
| G-04 | P2 | Arabic RTL rules exist for the legacy menu only; the civic surfaces have no RTL audit. |

State that must be preserved: `paradiso:language` (localStorage), `?lang=`,
`applyLanguage()` (sets `lang`/`dir`, zh-TW conversion via `zh-traditional.js`,
dispatches `paradiso-language-applied`), `selectedLocale` vs `currentLanguage`.
`new-home.html` has its own selector (PR #630) and is not touched.

## 15. Mobile

| ID | Sev | Finding |
| --- | --- | --- |
| M-01 | P1 | 390 px first viewport for `외국인등록증 재발급`: red error line → grey disclaimer band (5 lines) → interpretation → dead end. Zero useful guidance above the fold. |
| M-02 | P2 | At 320 px the F-6-1 result needs ~9 screens; documents are identical rows; the fee amount is a small fact cell. |
| M-03 | P3 | Legacy landing content (green cards) leaks below the result (`before/mobile-390-f6-1-resolved-full.png`, lower half). Out of scope for this sprint except that it must not regress. |

No horizontal overflow measured at 320/390/1280.

## 16. Accessibility

Present: `role=status` interpretation strip, `aria-expanded/controls` on 수정,
`tabindex=-1` focus targets, 44 px controls, `<details>` accordions, evidence
dialog focus return. Gaps: no announcement when a Quick Answer arrives; the
language sheet must trap focus and return it; fee/form details need
`aria-expanded`; RTL for the new sections; `prefers-reduced-motion` for the
sheet.

## 17. Physical-form coverage (measured after modelling)

Generated by `scripts/check_document_physical_form.mjs` into
`reports/data-coverage/document-physical-form-202609.md`. The report is the
source of truth for the counts quoted in the PR; the audit does not claim more
than it measures.

## 18. Implementation plan

1. **Procedure registry** (`author_rules.py` → `procedure_registry` in the
   bundle): per procedure `context_requirement` ∈ {STATUS_INDEPENDENT,
   STATUS_OPTIONAL, STATUS_REQUIRED, STATUS_AND_SUBSTATUS_REQUIRED,
   CURRENT_AND_TARGET_STATUS_REQUIRED, CONTEXT_DEPENDENT}, legal basis,
   discriminators, object lexicon.
2. **Common procedure rules** targeted `COMMON` (card_reissue,
   residence_report, registration_info_report, reentry) with regulation sources
   (`law_sources`) and manual anchors; status additions stay on the status
   entries (D-2 registration_info_report).
3. **Physical form** on every document item: `submission_form` derived only
   from the verbatim source phrase of that rule, default
   `SOURCE_DOES_NOT_SPECIFY`; a build-time guard forbids a form on a generic
   definition without a source phrase.
4. **Fee registry** (`fees`): amount, instrument (제73조), channel, online
   reduction, exemptions with conditions and evidence, scope, sources, review
   state. Renderer removes `fee` from document groups and renders 비용 / 납부.
5. **Local practice** (`data/local-practice-202609.json`): offices, layered
   variation records, Jeju case as `UNVERIFIED_USER_REPORT`; report schema,
   Vercel endpoint with honest states.
6. **Search router** (`assets/js/search-router.js`): intents, extraction,
   procedure-first routing; `nextStep()` gains `procedure` / `need-status`
   kinds and loses the no-status short-circuit for known procedures.
7. **Result UX**: hierarchy per §11 of the brief, restrained source copy,
   concise disclaimer with "안내 기준 보기", collapsed evidence.
8. **Waymaker Quick Answer** (`assets/js/waymaker-quick-answer.js` +
   `api/waymaker/quick-answer.js`): validated model, deterministic composer,
   optional wording enhancement with validator, follow-up handoff via
   `sessionStorage` + `ai.html` context line.
9. **Language UX**: one `cs-lang` control on home and in the searched header,
   popover / sheet, 15 native names, search, RTL, focus management.
10. **Tests**: router, physical form, fee, local practice, Quick Answer,
    adversarial, Playwright (desktop + mobile), WebKit QA flows, screenshots.

## 19. Non-goals

- No edits to protected files (`visa_data.json`, `doc_master.json`,
  `backend/data/*`).
- No promotion of the 2026.9 manuals from `needs_review`.
- No new locale system; no change to `new-home.html`.
- No framework, no bundler, no new analytics provider.
- No legal revalidation of the 110 existing entries beyond the fee / form /
  common-procedure cross-checks listed here.
