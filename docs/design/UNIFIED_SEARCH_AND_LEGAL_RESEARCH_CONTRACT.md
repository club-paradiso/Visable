# Unified Search & Legal Research — Design Contract

Implementation contract for the unified hero search, the AI Overview, the legal
evidence surface, and the employment-reporting flow. Written so a follow-up
Figma session can build the components without re-deriving the data model, and so
the code and the design stay describable in the same vocabulary.

- **Figma file:** `pInhK8Oyg04lpL4PMSCB4l` — page `01 Design System · 로고·버튼·오로라` (`14:2`)
- **Code:** `assets/js/unified-search.js`, `index.html` (`.us-*` styles),
  `backend/services/unified_search.py`
- **Status:** code shipped; Figma components for the new surfaces **not yet drawn**

---

## 1. Existing design-system inventory (as read from the Figma file)

The follow-up design work must build on these, not beside them.

| Node | Name | Variants |
| --- | --- | --- |
| `26:22` | **Button** | `Type=Primary\|Secondary` × `State=Default\|Hover\|Pressed\|Disabled` × `Theme=Light\|Dark` (16) |
| `185:14` | **Button / CTA · Hover** | `State=Default\|Hover` |
| `50:25` | **Card** | `Theme=Light` (`14:22`), `Theme=Dark` (`50:22`) |
| `55:9` | **Pill** | `Theme=Light` (`14:16`), `Theme=Dark` (`55:7`) |
| `55:12` | **Chip** | `Theme=Light` (`14:19`), `Theme=Dark` (`55:10`) |
| `55:17` | **Source Row** | `Theme=Light` (`14:26`), `Theme=Dark` (`55:13`) |
| `17:13` | **Aurora / Animated** | `State=A\|B\|C` — landing hero background only |
| `14:8` | Logo / Visable Wordmark | — |
| `203:13` / `204:13` / `205:17` | New Home / Waymaker / Club Paradiso wordmarks | — |

House rules already recorded in the file (`59:68` DS Usage Guide), carried forward
unchanged:

- Every screen is composed from instances of these components.
- Light/dark is an instance **property** (`Theme`), never a duplicated frame.
- Aurora is hero-background only — result, document and source screens stay calm.
- Chip/Pill text uses hug auto-layout so Korean never mid-word wraps.
- Primary button = deep emerald + neutral text (WCAG AAA), max one per screen.
- **Official-source and disclaimer copy is never weakened.**

> `get_variable_defs` returned `{}` for the Card component — the file styles
> colours directly rather than through published variables. The follow-up design
> pass should decide whether to promote the `--bg1/--bg2/--bd/--t1/--t2/--t3/--ac`
> set (already the code's contract, see §6) into Figma variables before adding
> more surfaces.

---

## 2. Screens

| ID | Screen | Entry | Code |
| --- | --- | --- | --- |
| `S1` | Hero (pre-search) | landing | `index.html` `#searchForm` |
| `S2` | Search results | submit / `?q=` | `#unifiedSearchLayer` + `#rlist` |
| `S3` | Legal research panel | intent `legal_question`, or CTA | `assets/js/legal-source-search.js` |
| `S4` | Employment reporting | intent `employment_reporting`, or tool | `index.html` `.jc2-*` |
| `S5` | Waymaker answer | "Waymaker에서 더 자세히" | `ai.html` |

`S2` layering, top to bottom — **this order is load-bearing**:

```
┌ Interpretation strip ──────── (deterministic, instant)
├ AI Overview slot ──────────── (async, may never arrive)
├ Extra cards (manual/tool) ─── (deterministic)
├ Suggestion chips ──────────── (deterministic)
├ Source panel ──────────────── (deterministic)
└ #rlist organic results ────── (existing renderer, unchanged)
```

The AI Overview sits *above* organic results but is fetched *after* them. It must
never reserve blocking space: in `loading` it renders a bounded skeleton, and in
`hidden` it renders nothing at all.

---

## 3. Components to build

### 3.1 `Search / Unified Input` (S1, S2)

| Property | Values |
| --- | --- |
| `State` | `Idle` · `Focused` · `Typing` · `Loading` · `Disabled` |
| `Theme` | `Light` · `Dark` |
| `Size` | `Hero` (landing) · `Compact` (sticky, post-search) |

Accessibility contract (already implemented in markup):
`role="search"` on the form; input `type="search"` with `aria-label`;
autocomplete list is `role="listbox"` with `aria-controls` / `aria-expanded` on
the input and `role="option"` per row; ↑/↓ move focus, `Esc` closes, `Enter`
submits. Minimum target 44×44.

### 3.2 `Search / Interpretation Strip` (S2)

Slots: label · intent Pill · 0–n code Chips · "수정" ghost button · optional
unrecognized-code warning.

| Property | Values |
| --- | --- |
| `Intent` | `ExactCode` · `Keyword` · `Situation` · `Procedure` · `Legal` · `Employment` · `Feature` · `Unknown` |
| `HasUnknownCode` | `true` · `false` |

`HasUnknownCode=true` is a real state, not an edge case: it fires whenever the
user typed something code-shaped that is **not in `visa_data.json`** (`D-2-99`,
`Z-9`). Copy names the token and says we do not have it. It must never look like
a status card.

### 3.3 `Search / AI Overview` (S2)

| Property | Values |
| --- | --- |
| `State` | `Loading` · `Ready` · `Unavailable` · `NoEvidence` |
| `CitationWarning` | `none` · `unverified` |
| `Theme` | `Light` · `Dark` |

- `Loading` — 3-line shimmer + "results below are already available".
- `Ready` — 2–5 sentences, next action, action buttons, confirm-with-official line.
- `Unavailable` — **a visible quiet-failure card.** Never collapse to nothing: a
  user who watched a spinner is owed the information that it stopped.
- `NoEvidence` — retrieval found nothing groundable, so nothing was written.
- `CitationWarning=unverified` — amber note: a statute reference in the summary
  could not be confirmed against retrieved evidence.

Always carries the `참고용 요약 / Reference summary` badge. Never renders an
eligibility verdict.

### 3.4 `Result / Status Card` and `Result / Subcode Card` (S2)

Two **distinct** components. A subcode card always shows its parent as a separate
labelled card — never merged, because a parent record must not present
subcode-specific rules as universal (`CLAUDE.md` code hierarchy).

| Property | Values |
| --- | --- |
| `Kind` | `Status` (2 segments) · `Subcode` (3+ segments) |
| `MatchReason` | `ExactCode` · `ParentOfExactCode` · `Keyword` |

### 3.5 `Evidence / Source Card` (S2, S3)

| Property | Values |
| --- | --- |
| `SourceType` | `OfficialPortal` · `OfficialLaw` · `OfficialHelpline` · `Manual` · `Precedent` · `Structured` |
| `LinkState` | `Linked` · `PlainText` |

`LinkState=PlainText` when the URL fails the government-host allow-list — the
card degrades to text rather than becoming an untrusted anchor.

### 3.6 `Evidence / Confidence Badge` and `Evidence / Legal Status Badge`

| Component | Values |
| --- | --- |
| Confidence | `High` · `Medium` · `Low` |
| Manual approval | `Approved` · `NeedsReview (검토 전)` · `Superseded` |
| Law lifecycle | `Verified` · `Repealed` · `Scheduled` · `Ambiguous` |
| Lookup failure | `Unavailable` · `Forbidden` · `Timeout` · `ParseFailed` · `NotFound` |

These are **four different scales** and must not share one visual ramp.
`NotFound` ("we checked, it is not there") and `Unavailable` ("we could not
check") are different claims and need different treatments.

### 3.7 `Employment / Editable Interpretation Card` (S4)

Shows extracted `role` / `workplace` / `employerMainBusiness` as **separately
editable** fields. 직종 and 업종 are never adjacent in a way that implies they
are the same axis.

| Property | Values |
| --- | --- |
| `State` | `Reading` · `Editing` · `Reanalyzing` |
| `HasAmbiguity` | `true` · `false` |

### 3.8 `Employment / Clarification Card` (S4)

Exactly **one** question at a time, with 2–4 answer chips. Never asserts a
reporting duty — the backend strips any determination the model emits.

### 3.9 `Employment / Occupation Candidate` and `Employment / Industry Candidate`

Two components, never one with a type switch, so they cannot be visually confused.

Slots: official classification name · code · track badge (`직종 KSCO8` /
`업종 KSIC11`) · confidence · "왜 맞을 수 있는지" · "왜 다른 후보일 수 있는지" ·
official source · select / deselect / compare.

| Property | Values |
| --- | --- |
| `Track` | `Occupation` · `Industry` |
| `Rank` | `Primary` (top 2, expanded) · `Secondary` (behind 더 보기) |
| `Selection` | `Unselected` · `Selected` · `Comparing` |
| `Certainty` | `NearestCandidate` · `ConfirmedCode` |

`Certainty` is not decoration: `NearestCandidate` and `ConfirmedCode` must be
visually unmistakable, because only HiKorea confirms the latter.

### 3.10 `Employment / Final Checklist` (S4)

The HiKorea confirmation step. The HiKorea row can never render as complete.

---

## 4. Data contract

`POST /api/search/unified` → organic, deterministic, no AI, no outbound HTTP:

```json
{
  "query": "D-2-1",
  "intent": "exact_visa_code",
  "detectedVisaCodes": ["D-2-1"],
  "interpretation": {
    "intent": "exact_visa_code", "intentRule": "code_only",
    "confidence": "high", "signals": ["visa_code"],
    "recognizedVisaCodes": ["D-2-1"],
    "unrecognizedCodeLikeTokens": [], "editable": true
  },
  "organicResults": [
    { "kind": "subcode_card", "code": "D-2-1", "parentCode": "D-2",
      "title": "전문학사과정", "summary": "…",
      "matchReason": "exact_code", "score": 1000 }
  ],
  "suggestions": ["D-2-1 체류기간 연장"],
  "sourceCards": [{ "id": "hikorea", "title": "…", "url": "https://…",
                    "sourceType": "official_portal", "note": "…" }],
  "manualEvidence": { "status": "ok", "approvedCount": 0, "reviewPendingCount": 3 },
  "aiOverview": null,
  "aiOverviewStatus": "pending",
  "fallbackAvailable": true,
  "requestId": "…",
  "latency": { "deterministicMs": 12 }
}
```

`POST /api/search/unified/ai-overview` → `status` is one of
`ok` · `unavailable` · `no_evidence` · `not_applicable`, plus
`citationVerification`, `evidenceState`, `requiresOfficialConfirmation`, and a
localized `message` for every non-`ok` state.

`POST /api/employment/interpret` → validated facts only. **Never** contains a
KSCO8/KSIC11 code; codes come from the deterministic analyzer.

`kind` values: `status_card` · `subcode_card` · `procedure_card` ·
`legal_card` · `employment_tool` · `feature_card` · `manual_card`.

---

## 5. Breakpoints & layout

| Breakpoint | Layout |
| --- | --- |
| ≥ 1024px | Results 1 column max 760px; source panel may become a right rail |
| 768–1023px | Single column, full-width cards |
| 481–767px | Single column, condensed padding |
| **≤ 480px** | Stacked; action buttons full width; **390px must not scroll horizontally** |

Wide content (tables, long codes, statute text) scrolls inside its own
`overflow-x:auto` container. `overflow-wrap: anywhere` on every user/upstream
string.

---

## 6. Theme tokens (the code's actual contract)

| Token | Role |
| --- | --- |
| `--bg1` / `--bg2` | Surface / raised surface |
| `--bd` / `--bd2` | Border / subtle divider |
| `--t1` / `--t2` / `--t3` | Primary / secondary / tertiary text |
| `--ac` / `--acL` | Accent / accent wash |
| `--sh1` / `--shD` | Card / dropdown elevation |
| `--sp-1..8` | Spacing scale |
| `--ff-display` | Display face |

Dark mode is `body[data-theme="dark"]`. Every `.us-*` rule resolves through these,
so the new surfaces follow the page theme with no second palette.

---

## 7. Interaction

| Action | Behaviour |
| --- | --- |
| Submit | Organic results render immediately; AI Overview requested in parallel |
| Type | Debounced (150ms) suggestions; ARIA combobox |
| Chip click | Fills input, resubmits, pushes history |
| "수정" | Focuses + selects the input |
| Back / Forward | `popstate` restores query and results |
| Reload | `?q=` re-runs the search |
| Share | URL carries `?q=` |
| Language switch | Layer re-renders; AI Overview is not re-requested |

Requests are token-guarded: a newer query invalidates an in-flight older response
so a slow AI answer can never overwrite a newer search.

---

## 8. Copy — empty / error / loading

| State | KO | EN |
| --- | --- | --- |
| AI loading | AI 요약을 만드는 중입니다. 아래 결과는 이미 확인할 수 있어요. | Generating an AI overview. The results below are already available. |
| AI unavailable | AI 요약을 사용할 수 없습니다. 아래 검색 결과와 공식 출처를 확인하세요. | The AI overview is unavailable. Please use the results and official sources below. |
| AI no evidence | 근거를 찾지 못해 요약을 만들지 않았습니다. | No grounded evidence was found, so no overview was generated. |
| Unknown code | 입력하신 %s 은(는) 저희 데이터에 없는 코드입니다. 오타가 아닌지 확인해 주세요. | %s is not a code in our dataset. Please check for a typo. |
| Review pending | 검토 전 — 사람이 원문과 대조·승인하기 전 상태입니다. | Not yet reviewed — this text has not been checked against the original. |
| Citation unverified | 인용 확인 실패 — 요약에 인용된 법령 조문을 확인하지 못했습니다. | Citation not verified — a statute reference could not be verified. |
| Confirm | 최종 확인은 하이코리아 또는 1345에서 하세요. | Confirm with HiKorea or 1345. |

Untranslated Korean statute text is labelled **공식 원문 (한국어)** rather than
machine-translated.

---

## 9. Code mapping

| Component | File | Symbol |
| --- | --- | --- |
| Unified layer | `assets/js/unified-search.js` | `buildUnifiedLayerHtml` |
| Interpretation strip | `assets/js/unified-search.js` | `buildInterpretationHtml` |
| AI Overview | `assets/js/unified-search.js` | `buildAiOverviewHtml` |
| Source panel | `assets/js/unified-search.js` | `buildSourceCardsHtml` |
| Extra cards | `assets/js/unified-search.js` | `buildExtraResultsHtml` |
| Styles | `index.html` | `.us-*` |
| Intent router | `backend/services/unified_search.py` | `classify_intent` |
| Organic results | `backend/services/unified_search.py` | `build_organic_results` |
| Law lifecycle badge | `backend/services/law_query_normalizer.py` | `classify_law_lifecycle` |
| Approval badge | `backend/services/manual_registry.py` | `evidence_gate` |
| Employment extraction | `backend/services/employment_nl.py` | `validate_extraction` |
| Occupation/industry candidates | `scripts/employment_code_analyzer.mjs` | `searchTrack` |

---

## 10. Handoff to the Figma session

Build, in order:

1. `Search / Unified Input` (5 states × 2 themes × 2 sizes)
2. `Search / Interpretation Strip` (8 intents × unknown-code boolean)
3. `Search / AI Overview` (4 states × citation-warning × 2 themes)
4. `Result / Status Card` + `Result / Subcode Card`
5. `Evidence / Source Card`, `Confidence Badge`, `Legal Status Badge`
6. `Employment / Editable Interpretation`, `Clarification`,
   `Occupation Candidate`, `Industry Candidate`, `Final Checklist`
7. `S2` desktop + 390px assemblies

Constraints that are **not** negotiable in design:

- The AI Overview may never occupy blocking space before organic results.
- The failure state is visible, not absent.
- 직종 and 업종 candidates are visually separate systems.
- Parent and subcode cards stay distinct.
- Disclaimers, official-source pointers and uncertainty notices are never
  shortened, greyed to illegibility, or moved below the fold.
- "Nearest candidate" and "confirmed code" never look alike.
