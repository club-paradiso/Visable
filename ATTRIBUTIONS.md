This Figma Make file includes components from [shadcn/ui](https://ui.shadcn.com/) used under [MIT license](https://github.com/shadcn-ui/ui/blob/main/LICENSE.md).

This Figma Make file includes photos from [Unsplash](https://unsplash.com) used under [license](https://unsplash.com/license).

## 필수서류 작성 도우미 (form-helper.html)

- [pdf-lib](https://github.com/Hopding/pdf-lib) — MIT license. Vendored at `assets/forms/vendor/pdf-lib.min.js`. Used to overlay user input onto blank official PDF forms entirely in the browser.
- [@pdf-lib/fontkit](https://github.com/Hopding/fontkit) — MIT license. Vendored at `assets/forms/vendor/fontkit.umd.min.js`. Enables Korean (Hangul) font embedding for pdf-lib.
- [Nanum Gothic](https://fonts.google.com/specimen/Nanum+Gothic) by Sandoll Communications — [SIL Open Font License 1.1](https://openfontlicense.org/). Vendored (pre-subset to Latin + Hangul) at `assets/forms/fonts/NanumGothic-Regular.ttf`, embedded into generated PDFs.

## 행정사 사무소 찾기 현장 QR 포스터 (agency-directory/qr.html)

- [qrcode-generator](https://github.com/kazuhikoarase/qrcode-generator) by Kazuhiko Arase — MIT license. Vendored at `agency-directory/vendor/qrcode.js`. Generates the scannable QR code for the on-site (immigration office) 행정사 사무소 검색 poster entirely in the browser. "QR Code" is a registered trademark of DENSO WAVE INCORPORATED.

Blank official forms under `assets/forms/pdf/` are Korean government public forms: 통합신청서 (출입국관리법 시행규칙 별지 제34호서식), 재외동포(F-4) 통합신청서·국내거소신고서 (재외동포법 시행규칙 별지 제1호서식), 거주/숙소제공확인서 (HiKorea 민원서식, 개정 2024. 5.), 신원보증서 (출입국관리법 시행규칙 별지 제129호서식), 통합신청서 중문 병기 (별지 제34호의3서식), and 재외동포(F-4) 통합신청서 중문 병기 (재외동포법 시행규칙 별지 제1호의2서식), retained verbatim from the official sources catalogued in `docs/forms_official/`.
