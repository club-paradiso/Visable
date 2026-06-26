# HiKorea guide screenshots — `assets/hikorea-guide/`

These are the screenshot assets for the **하이코리아 방문예약 도우미 / HiKorea
Reservation Helper** photo guide rendered by
[`assets/js/hikorea-reservation-helper.js`](../js/hikorea-reservation-helper.js).

Screenshots are used **only as a practical navigation aid**. Paradiso is **not
affiliated** with HiKorea or the Ministry of Justice, and these images must never
be used as Paradiso branding. Do not add HiKorea logos or marks.

## Status

> **No screenshots are bundled yet.** Every step currently renders an accessible
> "스크린샷 준비 중 / Screenshot coming soon" placeholder. The placeholder shows
> the exact filename to drop in, so there are **no broken image paths and no
> 404s** until a real, sanitized capture is added.

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
