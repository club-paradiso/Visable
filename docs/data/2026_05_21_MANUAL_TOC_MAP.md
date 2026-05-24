# 2026.5 Manual TOC → Page Map

Branch: `data/audit-2026-05-21-manual-update-json`
Audit date: 2026-05-24
Source files inspected:

- `docs/source-manuals/2026-05/visa_manual_2026_05.pdf` (484 pages, SHA-256 `5a191aed…84063`)
- `docs/source-manuals/2026-05/stay_manual_2026_05.pdf` (774 pages, SHA-256 `0492683…b3ba`)

Extraction tooling used in this run: `pdftotext -layout` (poppler-utils 24.02.0), with form-feed page splitting and Korean section-title anchor detection. Per-page text files live under `tmp/manual-2026-05-21/{visa,stay}_pages/` (ignored by `.gitignore`, not committed).

> **Source-identity caveat:** The user's attached `_260521.pdf` files are not accessible from this remote execution environment. Cover page label and internal PDF metadata cannot prove that the repo PDFs are the user-claimed 2026-05-21 updated manuals. Per the audit's hard rules, this TOC map describes the **repo's "2026.5" PDFs** and does not claim 2026-05-21 verification. Page numbers are absolute PDF pages inside the committed source files.

---

## How section start pages were detected

Section titles in both manuals are typeset with a spaced Korean name followed by the visa code in parens, for example:

```
  외 교(A-1)
  공 무(A-2)
  유 학(D-2)
  무역경영(D-9)
```

These appear at the top of section start pages. A regex matching this pattern in the first ~5 non-empty lines of each PDF page was applied. Pages where no such title-line was found (because the section starts mid-page, the title is split across lines, or the title uses a different layout) are marked **`no-dedicated-header`** and the page range is approximated from neighbour sections.

Special sections at the end of each manual (Top-Tier, K-STAR, 지역특화형, 광역형, 청소년 취업·정주, 외국국적동포 sub-manual) were detected by direct keyword search in the title region of pages past page 400, then de-duplicated against the standard-code matches.

---

## Visa Manual — 사증발급 안내매뉴얼 (484 pages)

The cover TOC lists 40 numbered sections.

| # | Section Title | Code | Start Page | Approx Range | Confidence | Notes |
|---:|---|---|---:|---|---|---|
| 1 | 외 교 | A-1 | 7 | 7–9 | high | First section. Header page also carries "체류자격별 사증발급기준 및 첨부서류". |
| 2 | 공 무 | A-2 | 10 | 10–12 | high | |
| 3 | 협 정 | A-3 | 13 | 13 | high | One-page section. |
| 4 | 사증면제 | B-1 | 14 | 14–21 | high | Includes treaty-country tables. |
| 5 | 관광통과 | B-2 | 22 | 22–24 | high | Includes 무사증입국 허가대상 국가일람표. |
| 6 | 일시취재 | C-1 | 25 | 25–26 | high | |
| 7 | 단기방문 | C-3 | 27 | 27–50 | high | Long section; covers multiple sub-codes. |
| 8 | 단기취업 | C-4 | 51 | 51–59 | high | |
| 9 | 문화예술 | D-1 | 60 | 60–61 | high | |
| 10 | 유 학 | D-2 | 62 | 62–69 | high | Aligns with active grounding `d2_extension_2026_05` referencing stay manual pp.43–44. |
| 11 | 기술연수 | D-3 | 70 | 70–72 | high | |
| 12 | 일반연수 | D-4 | 73 | 73–87 | high | Contains D-4-1, D-4-2K, D-4-3, D-4-5, D-4-6, D-4-7 sub-codes. |
| 13 | 취 재 | D-5 | 88 | 88–89 | medium | Title likely split-line; cross-checked. |
| 14 | 종 교 | D-6 | 90 | 90–91 | medium | |
| 15 | 주 재 | D-7 | 92 | 92–101 | medium | |
| 16 | 기업투자 | D-8 | 102 | 102–115 | high | |
| 17 | 무역경영 | D-9 | 116 | 116–121 | high | |
| 18 | 구 직 | D-10 | 122 | 122–135 | medium | Contains D-10-1, D-10-2, D-10-3, D-10-T sub-codes. |
| 19 | 교 수 | E-1 | 136 | 136–141 | medium | |
| 20 | 회화지도 | E-2 | 142 | 142–149 | high | |
| 21 | 연 구 | E-3 | 150 | 150–156 | high | |
| 22 | 기술지도 | E-4 | 157 | 157–163 | high | |
| 23 | 전문직업 | E-5 | no-dedicated-header | ~164–167 | low | Strict title-anchor not found. Likely embedded in E-4 / surrounding pages; verify visually. |
| 24 | 예술흥행 | E-6 | no-dedicated-header | ~164–167 | low | Strict title-anchor not found. Likely embedded; verify visually. |
| 25 | 특정활동 | E-7 | 168 | 168–277 | high | Long section. Contains E-7-1, E-7-2, E-7-3, E-7-4, E-7-S, E-7-Y, E-7-T, E-7-91 sub-codes. |
| 26 | 계절근로 | E-8 | 278 | 278–283 | high | |
| 27 | 비전문취업 | E-9 | 284 | 284–293 | high | |
| 28 | 선원취업 | E-10 | 294 | 294–296 | high | |
| 29 | 방문동거 | F-1 | 297 | 297–307 | high | |
| 30 | 거 주 | F-2 | 308 | 308–312 | high | Contains F-2-2, F-2-3, F-2-7, F-2-99, F-2-T sub-codes. |
| 31 | 동 반 | F-3 | 313 | 313–317 | medium | |
| 32 | 재외동포 | F-4 | (pointer) | see §38 | n/a | Cover TOC: "※ 38.번 참조". The actual content for 재외동포(F-4) lives inside §38 알기쉬운 외국국적동포 업무매뉴얼. |
| 33 | 영 주 | F-5 | 318 | 318–323 | medium | The §38 sub-manual also covers 외국국적동포 영주(F-5). |
| 34 | 결혼이민 | F-6 | 324 | 324–335 | high | F-6-1/2/3 modeled in visa_data.json. |
| 35 | 기 타 | G-1 | 336 | 336–342 | medium | |
| 36 | 관광취업 | H-1 | 343 | 343–378 | high | |
| 37 | 방문취업 | H-2 | (pointer) | see §38 | n/a | Like F-4, the H-2 (외국국적동포 방문취업) is detailed inside §38. |
| 38 | 알기쉬운 외국국적동포 업무매뉴얼 | special | 379 | 379–444 | high | Bundled sub-manual dated "2026. 2." (Feb 2026) on its title page — a separate Feb-2026 sub-manual carried inside the May-2026 outer manual. Covers C-3-8, F-1, F-4, F-5, H-2 외국국적동포 사증·체류 분야. |
| 39 | 탑티어(Top-Tier) 비자 (D-10-T, E-7-T, F-2-T, F-5-T) | special | 445 | 445–455 | high | Title: "첨단분야 해외 인재 대상 탑티어(Top-Tier) 체류관리 매뉴얼". |
| 40 | K-STAR 비자트랙 제도 | special | 456 | 456–484 | high | Title: "「K-STAR* 비자트랙」 제도 안내 매뉴얼" (* Korea-Science & Technology Advanced Human-Resource). |

---

## Stay Manual — 외국인체류 안내매뉴얼 (774 pages)

The cover TOC lists 41 numbered sections (visa manual has 40; stay manual splits and adds 광역형 visa pilot as a separate section and adds 국내 성장 기반 외국인 청소년 취업·정주 체류제도, in addition to using 외국국적동포 관련 as a §36 header).

| # | Section Title | Code | Start Page | Approx Range | Confidence | Notes |
|---:|---|---|---:|---|---|---|
| 1 | 외 교 | A-1 | 14 | 14–17 | high | |
| 2 | 공 무 | A-2 | 18 | 18–20 | high | |
| 3 | 협 정 | A-3 | 21 | 21–23 | high | |
| 4 | 사증면제 | B-1 | 24 | 24 | high | |
| 5 | 관광통과 | B-2 | 25 | 25 | high | |
| 6 | 일시취재 | C-1 | 26 | 26 | high | |
| 7 | 단기방문 | C-3 | 27 | 27–28 | high | |
| 8 | 단기취업 | C-4 | 29 | 29–31 | high | |
| 9 | 문화예술 | D-1 | 32 | 32–34 | high | |
| 10 | 유 학 | D-2 | 35 | 35–55 | high | Active grounding `d2_extension_2026_05` cites stay pp.43–44 inside this section. |
| 11 | 기술연수 | D-3 | 56 | 56–82 | high | |
| 12 | 일반연수 | D-4 | 83 | 83–101 | high | Active grounding `d4_extension_2026_05` cites stay pp.90–91 (D-4-1/D-4-7 어학연수생 extension subsection). |
| 13 | 취 재 | D-5 | 102 | 102–104 | high | |
| 14 | 종 교 | D-6 | 105 | 105–107 | high | |
| 15 | 주 재 | D-7 | 108 | 108–111 | high | |
| 16 | 기업투자 | D-8 | 115 | 115–129 | medium | TOC order is non-monotonic in body: stay manual prints D-9 (p112–114) before D-8 (p115–). |
| 17 | 무역경영 | D-9 | 112 | 112–114 | medium | Appears before D-8 in body order. |
| 18 | 구 직 | D-10 | 142 | 142–165 | high | Body contains 4) 최우수인재(D-10-T) cross-reference around p146 to §39 탑티어. |
| 19 | 교 수 | E-1 | 166 | 166–175 | high | |
| 20 | 회화지도 | E-2 | no-dedicated-header | ~176–184 | low | Strict title-anchor not found; appears embedded after E-1. |
| 21 | 연 구 | E-3 | 185 | 185–194 | high | |
| 22 | 기술지도 | E-4 | 195 | 195–199 | high | |
| 23 | 전문직업 | E-5 | 200 | 200–204 | high | |
| 24 | 예술흥행 | E-6 | 205 | 205–211 | high | |
| 25 | 특정활동 | E-7 | 212 | 212–323 | high | Active grounding `e7_extension_2026_05` cites stay p.226 (general E-7 ext document list). |
| 26 | 계절근로 | E-8 | 324 | 324–325 | high | |
| 27 | 비전문취업 | E-9 | 326 | 326–335 | high | |
| 28 | 선원취업 | E-10 | 336 | 336–340 | high | |
| 29 | 방문동거 | F-1 | 341 | 341–359 | high | |
| 30 | 거 주 | F-2 | 360 | 360–424 | high | |
| 31 | 동 반 | F-3 | 425 | 425–441 | medium | Stay manual TOC orders 동반(F-3) before 영주(F-5). |
| 32 | 영주(F-5):동포,난민제외 | F-5 | 442 | 442–477 | medium | TOC explicitly excludes 동포 and 난민 from this F-5 section (they go to §36 / G-1). |
| 33 | 결혼이민 | F-6 | 478 | 478–501 | high | F-6-1/2/3 modeled in visa_data.json. |
| 34 | 기 타 | G-1 | 502 | 502–517 | high | |
| 35 | 관광취업 | H-1 | 518 | 518–521 | high | |
| 36 | 외국국적동포 관련 (C-3-8, F-1, H-2, F-4, F-5) | special | 522 | 522–588 | high | Body opens with "알기쉬운 외국국적동포 업무 매뉴얼" (Feb 2026 sub-manual). Identical or near-identical to visa §38 content. |
| 37 | 지역특화형비자 | special | 589 | 589–651 | high | Title: "지역특화형비자 체류제도 주요내용 알림". |
| 38 | 국내 성장 기반 외국인 청소년 취업·정주 체류제도 | special | 652 | 652–666 | high | Title: "국내 성장 기반 외국인 청소년 취업·정주 체류제도 알림". |
| 39 | 탑티어(Top-Tier) 비자 (D-10-T, E-7-T, F-2-T, F-5-T) | special | 667 | 667–682 | high | Title: "첨단분야 해외 인재 대상 탑티어(Top-Tier) 체류관리 매뉴얼". |
| 40 | 광역형 비자 시범사업 | special | 683 | 683–745 | high | Title: "광역형 비자 시범사업 — 사증발급 및 체류관리지침 제정(안)". |
| 41 | K-STAR 비자트랙 제도 | special | 746 | 746–774 | high | Title: "「K-STAR* 비자트랙」 제도 안내 매뉴얼". |

---

## Section ordering anomalies

These anomalies are characteristic of the **repo's 2026.5 PDFs** and would need to be re-checked if the PDFs are replaced with the user's 2026-05-21 source files:

1. **Stay manual D-8/D-9 order swap**: D-9 무역경영 (p112–114) prints BEFORE D-8 기업투자 (p115–129) in body order, despite TOC numbering 16 → 17. The TOC numbers are 16. 기업투자(D-8) and 17. 무역경영(D-9). The page-order reversal looks intentional or a binder-level reordering rather than a body misprint.
2. **Visa manual F-4/F-5 are pointers to §38**: TOC §32 재외동포(F-4) explicitly says "※ 38.번 참조". TOC §33 영주(F-5) is partially covered by §38 외국국적동포 sub-manual for 외국국적동포 영주.
3. **Visa manual E-5, E-6 lack dedicated title-line headers**: their content lives between p157 (E-4 start) and p168 (E-7 start). Sub-section titles may appear inline rather than as full-page headers. Page-level review required to confirm exact start pages.
4. **Stay manual E-2 lacks dedicated header**: its content appears embedded after E-1 (p166–175). Likely between p176 and p184.
5. **Bundled sub-manuals**: §38 in visa and §36 in stay are both copies of the "알기쉬운 외국국적동포 업무 매뉴얼", which is itself a separate Feb 2026 sub-manual bound inside the May 2026 outer manual.

---

## Summary

- Visa manual: 40 TOC sections. 35 of 40 have confident page anchors. 2 (E-5, E-6) lack dedicated title-line headers. 2 (F-4, F-5) are pointers to §38. 1 (H-2) is similarly a pointer to §38.
- Stay manual: 41 TOC sections. 38 of 41 have confident page anchors. 1 (E-2) lacks a dedicated title-line header. All 6 special sections (§36 외국국적동포 관련, §37 지역특화형, §38 청소년 취업·정주, §39 탑티어, §40 광역형, §41 K-STAR) located with high confidence.

The accompanying `2026_05_21_manual_toc_map.json` carries the same data machine-readably and is the input to `2026_05_21_manual_json_crosswalk.json`.

> **Reminder**: All page numbers above are from the repo's currently-committed "2026.5" PDFs. They have not been independently confirmed to be the user's 2026-05-21 updated manuals. If the user's `_260521.pdf` files are introduced and the page numbers shift, this map must be regenerated.
