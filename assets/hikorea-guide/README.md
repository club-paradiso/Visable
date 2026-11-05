# HiKorea guide screenshots — `assets/hikorea-guide/`

These are the screenshot assets for the **하이코리아 방문예약 도우미 / HiKorea
Reservation Helper** photo guide rendered by
[`assets/js/hikorea-reservation-helper.js`](../js/hikorea-reservation-helper.js).

Screenshots are used **only as a practical navigation aid**. Paradiso is **not
affiliated** with HiKorea or the Ministry of Justice, and these images must never
be used as Paradiso branding. Do not add HiKorea logos or marks.

## Status

> **6 of 13 steps ship a real screen example** (bundled 2026-11-05, see the
> provenance table below). The remaining 7 steps stay text-only — the helper
> **does not render empty screenshot placeholders** for them. The unbundled
> steps sit behind real identity verification (office / purpose / date-time
> selection, confirmation, change / cancel) or had no verified, personal-data-
> free capture available (account-info form, login page); per the safety rules
> below they were left text-only rather than filled with unverified images.
> Every bundled image was visually inspected before commit: form fields are
> empty, and the only numbers visible are a one-time CAPTCHA sample and the
> official specimen (견본) registration card in the identity-verification
> example — no real person's data. Booking and lookup always happen on the
> [official HiKorea visit-reservation page](https://www.hikorea.go.kr/resv/ResvIntroR.pt)
> or the [non-member reservation lookup page](https://www.hikorea.go.kr/mypage/MypgNonRegResvPageR.pt).
> An account is optional for visit reservations.

## Bundled screenshots — provenance (verified 2026-11-05)

| Filename | What it shows | Source of the capture |
| --- | --- | --- |
| `hikorea-signup-01-language.png` | HiKorea homepage: top-right 로그인·회원가입·한국어/ENGLISH/中文, 방문예약 box | Screencapture of hikorea.go.kr published by KorealtyUSA (Feb 2026), https://korealtyusa.com/하이코리아-예약/ |
| `hikorea-signup-02-terms.png` | Signup terms: 이용약관 + 개인정보 보호정책 with 동의 checkboxes | Ewha Womans University ISA HiKorea manual (2022), official university guide PDF |
| `hikorea-signup-03-identity-verification.png` | Signup identity check for 등록외국인: 등록번호·성명·입력확인 fields (empty) + official specimen card | Ewha Womans University ISA HiKorea manual (2022) |
| `hikorea-login-02-verification.png` | Identity verification, 여권번호 신원인증 tab: passport-number field (empty), nationality choices | Real-screen capture published by dikr.co.kr, https://dikr.co.kr/출입국관리사무소-예약-신청-온라인-방문-접수-및-민/ |
| `hikorea-reservation-01-entry.png` | Visit-reservation guidance screen: 이용안내 / 인증 / 신청서 작성 tabs + official warnings | Real-screen capture published by dikr.co.kr (same article) |
| `hikorea-reservation-06-reservation-check.png` | Non-member reservation lookup identity check, 신분증 신원인증 tab: 등록(거소)번호·발급일자 fields (empty) | Real-screen capture published by dikr.co.kr (same article) |

The underlying screens are all hikorea.go.kr itself; the publishers above only
distributed the captures. Blog header / footer framing was cropped out, leaving
only the HiKorea UI. Live public pages were re-checked on 2026-11-05 (homepage,
reservation guidance, login, signup terms, non-member lookup all load without
any login) and the step text was corrected where the live site differed
(login methods, the three identity-verification tabs, the member / non-member
reservation buttons).

## File naming convention

Drop sanitized PNG (or WebP/JPG) captures here using these exact names:

| Tab (회원가입/로그인/방문예약/확인) | Filename |
| --- | --- |
| 회원가입 — 언어 선택·가입 시작 | `hikorea-signup-01-language.png` |
| 회원가입 — 약관 동의 | `hikorea-signup-02-terms.png` |
| 회원가입 — 본인인증 | `hikorea-signup-03-identity-verification.png` |
| 회원가입 — 계정 정보 입력 | `hikorea-signup-04-account-info.png` |
| 로그인 — 로그인 화면 | `hikorea-login-01-login-page.png` |
| 로그인 — 간편/비회원 인증 | `hikorea-login-02-verification.png` |
| 방문예약 — 메뉴 진입 | `hikorea-reservation-01-entry.png` |
| 방문예약 — 관서 선택 | `hikorea-reservation-02-office-select.png` |
| 방문예약 — 민원(목적) 선택 | `hikorea-reservation-03-purpose-select.png` |
| 방문예약 — 날짜/시간 | `hikorea-reservation-04-date-time.png` |
| 방문예약 — 예약 확인/저장 | `hikorea-reservation-05-confirmation.png` |
| 예약 확인·변경 — 예약 내역 | `hikorea-reservation-06-reservation-check.png` |
| 예약 확인·변경 — 변경/취소 | `hikorea-reservation-07-change-cancel.png` |

If the exact HiKorea flow differs, map the closest screenshot to the closest
filename — do not invent steps.

## How to enable a screenshot (the only code edit needed)

1. Sanitize the capture (see Privacy below) and save it here with the name above.
2. In `assets/js/hikorea-reservation-helper.js`, find the `GUIDE_STEPS` entry
   with the matching `file:` and flip `available: false` → `available: true`.
3. That is it. The guide will lazy-load the image, show it full-width, and let
   users tap to enlarge it in a lightbox. The `alt` text comes from the step
   title string, so accessibility is already handled.

## Privacy & legal safety (required before adding any image)

Mask or remove **all** personal / sensitive data before committing a screenshot:

- names, phone numbers, email addresses
- 외국인등록번호 / alien registration numbers, passport numbers, any ID numbers
- reservation numbers, addresses
- QR codes / barcodes
- faces or signatures

If a capture contains any of the above and cannot be cleanly masked, **do not
commit it** — recapture with dummy data or blur the region first. When in doubt,
leave the placeholder in place; the text instructions stand on their own.

## Optimization

- Keep each image roughly ≤ 1600px on the long edge and compressed (PNG/WebP).
- The guide already lazy-loads below-the-fold images (`loading="lazy"`), so
  adding several screenshots will not noticeably slow the initial page load.
