# 통합신청서 작성 도우미 — Manual QA Checklist

- Tool: `form-helper.html`
- Phase: MVP Phase 1
- Date: 2026-06-08
- Form reference: 출입국관리법 시행규칙 별지 제34호서식 (2022. 4. 12.)

---

## Environment

- Browser: Chrome, Firefox, Safari, Edge (latest)
- Viewports: Desktop 1280px, Tablet 768px, Mobile 390px
- Themes: Light mode, Dark mode
- Entry: Direct URL `form-helper.html`, linked from `index.html` tools section

---

## A. 외국인등록 (Foreign Resident Registration)

| # | Scenario | Expected | Status |
|---|----------|----------|--------|
| A1 | Select 외국인등록 type card | Card highlights with green border; form checkbox shown as `☑ 외국인 등록` | NOT EXECUTED |
| A2 | Proceed to Step 4 | Photo reminder caution box appears | NOT EXECUTED |
| A3 | Proceed to Step 4 | Refund bank account field appears | NOT EXECUTED |
| A4 | Step 6 output | Section ① shows `☑ 외국인 등록` | NOT EXECUTED |
| A5 | Step 6 output | Section ④ lists "사진 필요: 최근 6개월 이내 여권용 사진" | NOT EXECUTED |
| A6 | Step 6 output | Section ④ mentions 반환용 계좌번호 | NOT EXECUTED |
| A7 | Live preview | Preview row shows "사진 필요" in coral/red color | NOT EXECUTED |
| A8 | Live preview | Preview row shows "반환계좌" field | NOT EXECUTED |

---

## B. 체류기간 연장허가 (Extension of Sojourn Period)

| # | Scenario | Expected | Status |
|---|----------|----------|--------|
| B1 | Select 체류기간 연장 type card | Form checkbox shown as `☑ 체류기간 연장허가` | NOT EXECUTED |
| B2 | Step 4 | Photo reminder does NOT appear | NOT EXECUTED |
| B3 | Step 4 | Refund bank account field does NOT appear | NOT EXECUTED |
| B4 | Step 4 | Current sojourn expiry date field appears | NOT EXECUTED |
| B5 | Step 4 | Extension reason textarea appears | NOT EXECUTED |
| B6 | Step 6 output | Section ① shows `☑ 체류기간 연장허가` | NOT EXECUTED |
| B7 | Step 5 validation | Error shown if current expiry date is empty | NOT EXECUTED |
| B8 | Step 5 validation | Warning shown if expiry date is before today | NOT EXECUTED |

---

## C. 체류자격외활동허가 (Activities Outside Status)

| # | Scenario | Expected | Status |
|---|----------|----------|--------|
| C1 | Select 체류자격외활동허가 type card | Form checkbox shown as `☑ 체류자격외 활동허가` | NOT EXECUTED |
| C2 | Step 2 | Desired activity/status field appears (required) | NOT EXECUTED |
| C3 | Step 2 | Activity description textarea appears | NOT EXECUTED |
| C4 | Step 2 | Activity institution field appears | NOT EXECUTED |
| C5 | Step 2 | Activity period field appears | NOT EXECUTED |
| C6 | Step 5 validation | Error shown if desired activity is empty | NOT EXECUTED |
| C7 | Step 2 | Caution/inquiry note about this type is visible | NOT EXECUTED |
| C8 | Step 6 output | Section ① shows `☑ 체류자격외 활동허가` | NOT EXECUTED |
| C9 | Step 6 output | Section ③ shows desired activity value when filled | NOT EXECUTED |

---

## D. 체류자격 변경허가 (Change of Status)

| # | Scenario | Expected | Status |
|---|----------|----------|--------|
| D1 | Select 체류자격 변경 type card | Form checkbox shown as `☑ 체류자격 변경허가` | NOT EXECUTED |
| D2 | Step 2 | Desired status field appears (required) | NOT EXECUTED |
| D3 | Step 5 validation | Error if desired status is empty | NOT EXECUTED |
| D4 | Step 6 output | Section ① shows `☑ 체류자격 변경허가` and desired status | NOT EXECUTED |
| D5 | Live preview | "희망 자격" row appears in preview when filled | NOT EXECUTED |

---

## E. 근무처 변경/추가 (Workplace Change or Addition)

| # | Scenario | Expected | Status |
|---|----------|----------|--------|
| E1 | Select 근무처 변경/추가 type card | Form checkbox shown as `☑ 근무처 변경ㆍ추가허가 / 신고` | NOT EXECUTED |
| E2 | Step 4 | Current workplace name field appears | NOT EXECUTED |
| E3 | Step 4 | New workplace name field appears (required) | NOT EXECUTED |
| E4 | Step 4 | Business registration number field appears | NOT EXECUTED |
| E5 | Step 4 | Workplace phone number field appears | NOT EXECUTED |
| E6 | Step 5 validation | Error if new workplace is empty | NOT EXECUTED |
| E7 | Step 6 output | Section ③ shows new workplace info | NOT EXECUTED |

---

## F. 재입국허가 (Reentry Permit)

| # | Scenario | Expected | Status |
|---|----------|----------|--------|
| F1 | Select 재입국허가 type card | Form checkbox shown as `☑ 재입국허가` | NOT EXECUTED |
| F2 | Step 2 | Single/Multiple radio buttons appear | NOT EXECUTED |
| F3 | Step 4 | Intended period of reentry field appears (required) | NOT EXECUTED |
| F4 | Step 5 validation | Error if reentry period is empty | NOT EXECUTED |
| F5 | Step 6 output | Section ① shows 단수 or 복수 and period | NOT EXECUTED |

---

## G. 등록증 재발급 (Card Reissuance)

| # | Scenario | Expected | Status |
|---|----------|----------|--------|
| G1 | Select 등록증 재발급 type card | Form checkbox shown as `☑ 등록증 재발급` | NOT EXECUTED |
| G2 | Step 4 | Photo reminder appears | NOT EXECUTED |
| G3 | Step 4 | Refund bank account field appears | NOT EXECUTED |
| G4 | Step 6 output | Photo and refund account notes present in Section ④ | NOT EXECUTED |

---

## H. 체류자격 부여 (Granting Status)

| # | Scenario | Expected | Status |
|---|----------|----------|--------|
| H1 | Select 체류자격 부여 type card | Form checkbox shown as `☑ 체류자격 부여` | NOT EXECUTED |
| H2 | Step 2 | Desired status field appears (required) | NOT EXECUTED |
| H3 | Step 5 validation | Error if desired status is empty | NOT EXECUTED |

---

## I. Privacy & Data Safety

| # | Scenario | Expected | Status |
|---|----------|----------|--------|
| I1 | Fill all fields, open DevTools → Network | No XHR/fetch request carrying form field values is sent | NOT EXECUTED |
| I2 | Fill all fields, press Reset | All visible input fields clear; preview resets to empty state | NOT EXECUTED |
| I3 | Fill sensitive fields (passport number, ARC number) | No value visible in page URL or query string | NOT EXECUTED |
| I4 | Navigate to another page and back | Fields are blank (session-only; not persisted in localStorage) | NOT EXECUTED |
| I5 | Inspect localStorage after filling fields | No sensitive field values (passport, address, phone, email, account) present | NOT EXECUTED |
| I6 | Copy guide output | Output text does not include raw passport number (shows last 4 digits only); ARC number not included | NOT EXECUTED |

---

## J. Navigation & Stepper

| # | Scenario | Expected | Status |
|---|----------|----------|--------|
| J1 | Load page | Step 1 panel is visible; other panels hidden | NOT EXECUTED |
| J2 | Step 1: no type selected → click Next | Button is disabled | NOT EXECUTED |
| J3 | Step 1: select type → click Next | Advances to Step 2; stepper updates | NOT EXECUTED |
| J4 | Click Prev on Step 2 | Returns to Step 1; previously selected type remains selected | NOT EXECUTED |
| J5 | Step 6: Next button | Hidden | NOT EXECUTED |
| J6 | Stepper dots update correctly (done=green, active=darker, pending=outline) | Visual match | NOT EXECUTED |

---

## K. Output Actions

| # | Scenario | Expected | Status |
|---|----------|----------|--------|
| K1 | Click 작성 가이드 복사 | Clipboard receives plain-text guide; button briefly shows "✓ 복사됨" | NOT EXECUTED |
| K2 | Click 인쇄용 보기 | Print dialog opens | NOT EXECUTED |
| K3 | Print preview | Header, stepper, nav, aside panel hidden; output content visible | NOT EXECUTED |
| K4 | Click 초기화 and confirm | All fields reset; preview clears; returns to step 1 | NOT EXECUTED |
| K5 | Click 초기화 and cancel | State unchanged | NOT EXECUTED |

---

## L. URL Deep-link

| # | Scenario | Expected | Status |
|---|----------|----------|--------|
| L1 | Open `form-helper.html?type=sojourn_extension` | 체류기간 연장 pre-selected on Step 1 | NOT EXECUTED |
| L2 | Open `form-helper.html?type=foreign_registration&status=D-2` | 외국인등록 pre-selected; current status field pre-filled with D-2 | NOT EXECUTED |
| L3 | Open `form-helper.html?type=invalid_id` | No type pre-selected; no error thrown | NOT EXECUTED |

---

## M. Entry Point (index.html)

| # | Scenario | Expected | Status |
|---|----------|----------|--------|
| M1 | Scroll to tools section on index.html | New "통합신청서 작성 도우미" card is visible with LIVE badge | NOT EXECUTED |
| M2 | Click the card | Navigates to `form-helper.html` | NOT EXECUTED |
| M3 | Change language on index.html (KO→EN) | Existing 5 tool cards update; 6th card remains in Korean (acceptable MVP) | NOT EXECUTED |

---

## N. Accessibility

| # | Scenario | Expected | Status |
|---|----------|----------|--------|
| N1 | Tab through Step 1 type cards | Focus visible on each card; Enter/Space selects | NOT EXECUTED |
| N2 | Tab through all form inputs in Steps 2-4 | All inputs reachable by keyboard | NOT EXECUTED |
| N3 | Screen reader on Step 1 type cards | `role="radio"` and `aria-checked` state announced | NOT EXECUTED |
| N4 | Screen reader on stepper | Step status (완료/현재/대기) announced via aria-label | NOT EXECUTED |
| N5 | All inputs have visible labels | No unlabelled inputs | NOT EXECUTED |
| N6 | Error/warning text | Not conveyed by color alone (icons + text present) | NOT EXECUTED |

---

## O. Responsive / Mobile

| # | Scenario | Expected | Status |
|---|----------|----------|--------|
| O1 | 390px viewport — Step 1 | Type cards render as 2-column grid | NOT EXECUTED |
| O2 | 390px viewport — Step 3 | Field rows stack to single column | NOT EXECUTED |
| O3 | 390px viewport — aside panel | Stacks below wizard; no horizontal overflow | NOT EXECUTED |
| O4 | 900px viewport | Two-column layout (wizard + aside) | NOT EXECUTED |
| O5 | Stepper at 390px | Step labels hidden; dots only visible | NOT EXECUTED |

---

## Limitations (Phase 1)

- Partial language support: the tool is Korean-first; English labels appear as secondary sub-labels on inputs. Full EN/ZH/JA mode is Phase 2.
- The 6th tool card in `index.html` does not participate in the i18n `toolTitles`/`toolDescs` arrays (those have 5 entries); it displays static Korean for all language settings.
- No automated browser tests exist for this feature; all QA is manual.
- The copy-to-clipboard fallback uses `document.execCommand('copy')` on older browsers.
- Passport number is partially masked in the live preview (last 4 digits), but is stored in plaintext in the JavaScript `state` object for the session lifetime.
