# 2026-05-21 Manual TOC → Page Map (PR B, post PR #155)

Branch: `data/rebuild-2026-05-21-manual-crosswalk`
Audit date: 2026-05-25
Generator: `scripts/regenerate_2026_05_21_manual_crosswalk.py`

Canonical source files (installed by PR #155):

- `docs/source-manuals/2026-05/visa_manual_2026_05.pdf` — **484 pages**, SHA-256 `7fd79509…ae11c`, source_date `2026-05-21` (PDF internal export date 2026-05-24).
- `docs/source-manuals/2026-05/stay_manual_2026_05.pdf` — **777 pages**, SHA-256 `dd0d2f10…9c3e1`, source_date `2026-05-21` (PDF internal export date 2026-05-24).

Extraction tooling: `pdftotext -layout` (poppler-utils 24.02.0) with form-feed page splitting, plus `pdfinfo` / pypdf 6.12.1 for page-count verification. Section anchors were detected by a spaced-Korean-name + `(CODE)` top-of-page header regex; back-matter special sections were located by canonical-title substring search. The detector output is pinned in the generator so the artifacts regenerate deterministically. Per-page text was held under `/tmp/extract/` (not committed).

> **Supersedes:** This map supersedes the pre-PR #155 TOC map that was built against the earlier **774-page** stay PDF (sha256 `0492683…b3ba`) and the earlier visa PDF (sha256 `5a191aed…84063`) under the "source_date: unresolved / PDFs not accessible" assumptions. PR #155 installed the canonical 2026-05-21 PDFs, so the stay manual is now 777 pages and the special-section anchors are re-derived. **The pre-#155 source-identity caveat ("user PDFs not accessible / PDF created 2026-05-07") no longer applies — the canonical PDFs are committed in-repo.**

> **Scope caveat:** This is an internal audit artifact. Page numbers are absolute physical PDF pages. This map describes manual-section **location** only and does not verify any `visa_data.json` record. Every manual-dependent record remains `verified=false` / `needsManualReview=true`.

---

## Visa Manual — 사증발급 안내매뉴얼 (484 pages, 40 TOC sections)

The visa PDF page count is unchanged (484) and the cover/TOC are byte-identical to the prior canonical PDF per `source_manifest.json`. Re-detection on the canonical PDF reproduces the prior anchors exactly; no anchor changes.

| # | Section | Code | Start | Range | Conf. | Notes |
|---:|---|---|---:|---|---|---|
| 1 | 외 교 | A-1 | 7 | 7–9 | high | First section after TOC/preamble. |
| 2 | 공 무 | A-2 | 10 | 10–12 | high | |
| 3 | 협 정 | A-3 | 13 | 13 | high | One-page section. |
| 4 | 사증면제 | B-1 | 14 | 14–21 | high | Treaty-country tables. |
| 5 | 관광통과 | B-2 | 22 | 22–24 | high | 무사증입국 허가대상 국가일람표. |
| 6 | 일시취재 | C-1 | 25 | 25–26 | high | |
| 7 | 단기방문 | C-3 | 27 | 27–50 | high | C-3-1 … C-3-8. |
| 8 | 단기취업 | C-4 | 51 | 51–59 | high | |
| 9 | 문화예술 | D-1 | 60 | 60–61 | high | |
| 10 | 유 학 | D-2 | 62 | 62–69 | high | Active grounding `d2_extension_2026_05` cites stay pp.43–44. |
| 11 | 기술연수 | D-3 | 70 | 70–72 | high | |
| 12 | 일반연수 | D-4 | 73 | 73–87 | high | D-4-1/2K/3/5/6/7 sub-codes. |
| 13 | 취 재 | D-5 | 88 | 88–89 | high | |
| 14 | 종 교 | D-6 | 90 | 90–91 | high | |
| 15 | 주 재 | D-7 | 92 | 92–101 | high | |
| 16 | 기업투자 | D-8 | 102 | 102–115 | high | |
| 17 | 무역경영 | D-9 | 116 | 116–121 | high | |
| 18 | 구 직 | D-10 | 122 | 122–135 | high | D-10-1/2/3/T sub-codes. |
| 19 | 교 수 | E-1 | 136 | 136–141 | high | |
| 20 | 회화지도 | E-2 | 142 | 142–149 | high | |
| 21 | 연 구 | E-3 | 150 | 150–156 | high | |
| 22 | 기술지도 | E-4 | 157 | 157–163 | high | |
| 23 | 전문직업 | E-5 | no-dedicated-header | ~164–167 | low | Title-anchor not found; content embedded between E-4 and E-7. |
| 24 | 예술흥행 | E-6 | no-dedicated-header | ~164–167 | low | Title-anchor not found; embedded. |
| 25 | 특정활동 | E-7 | 168 | 168–277 | high | E-7-1/2/3/4/S/Y/T/91 sub-codes. |
| 26 | 계절근로 | E-8 | 278 | 278–283 | high | |
| 27 | 비전문취업 | E-9 | 284 | 284–293 | high | |
| 28 | 선원취업 | E-10 | 294 | 294–296 | high | |
| 29 | 방문동거 | F-1 | 297 | 297–307 | high | |
| 30 | 거 주 | F-2 | 308 | 308–312 | high | F-2-2/3/7/99/T sub-codes. |
| 31 | 동 반 | F-3 | 313 | 313–317 | medium | |
| 32 | 재외동포 | F-4 | (pointer) | see §38 | n/a | TOC: "※ 38.번 참조". Content inside §38 (detected anchor p415). |
| 33 | 영 주 | F-5 | 318 | 318–323 | medium | §38 sub-manual also covers 외국국적동포 영주(F-5). |
| 34 | 결혼이민 | F-6 | 324 | 324–335 | high | F-6-1/2/3 modeled in visa_data.json. |
| 35 | 기 타 | G-1 | 336 | 336–342 | medium | |
| 36 | 관광취업 | H-1 | 343 | 343–378 | high | |
| 37 | 방문취업 | H-2 | (pointer) | see §38 | n/a | H-2 외국국적동포 방문취업 inside §38. |
| 38 | 알기쉬운 외국국적동포 업무매뉴얼 | special | 379 | 379–444 | high | Bundled Feb-2026 sub-manual. Covers C-3-8, F-1, F-4, F-5, H-2. |
| 39 | 탑티어(Top-Tier) 비자 | special | 445 | 445–455 | high | 첨단분야 해외 인재 대상 탑티어(Top-Tier) 체류관리 매뉴얼. D-10-T, E-7-T, F-2-T, F-5-T. |
| 40 | K-STAR 비자트랙 제도 | special | 456 | 456–484 | high | 「K-STAR* 비자트랙」 제도 안내 매뉴얼. Ends on final visa page (484). |

---

## Stay Manual — 외국인체류 안내매뉴얼 (777 pages, 41 TOC sections)

The TOC (pages 2–13) lists 41 sections with no page-number column, so anchors were detected in the body. **Special-section anchors (§36–§41) shifted versus the pre-#155 774-page map and were re-derived from the canonical 777-page PDF.** The page count rose 774 → 777 (net **+3** pages, pp.775–777) in the K-STAR §41 우수인재 back-matter appendix block.

| # | Section | Code | Start | Range | Conf. | Notes |
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
| 10 | 유 학 | D-2 | 35 | 35–55 | high | Active grounding `d2_extension_2026_05` cites pp.43–44. |
| 11 | 기술연수 | D-3 | 56 | 56–82 | high | |
| 12 | 일반연수 | D-4 | 83 | 83–101 | high | Active grounding `d4_extension_2026_05` cites pp.90–91. |
| 13 | 취 재 | D-5 | 102 | 102–104 | high | |
| 14 | 종 교 | D-6 | 105 | 105–107 | high | |
| 15 | 주 재 | D-7 | 108 | 108–114 | high | |
| 16 | 기업투자 | D-8 | 115 | 115–129 | high | **Re-derived:** D-8 precedes D-9 in normal page order; the pre-#155 D-8/D-9 swap anomaly does NOT reproduce. |
| 17 | 무역경영 | D-9 | 130 | 130–141 | high | **Re-derived** to p130 (pre-#155 map had p112). |
| 18 | 구 직 | D-10 | 142 | 142–165 | high | D-10-T cross-refs §39 탑티어. |
| 19 | 교 수 | E-1 | 166 | 166–175 | high | |
| 20 | 회화지도 | E-2 | no-dedicated-header | ~176–184 | low | Embedded after E-1 (ends p175) and before E-3 (p185). |
| 21 | 연 구 | E-3 | 185 | 185–194 | high | |
| 22 | 기술지도 | E-4 | 195 | 195–199 | high | |
| 23 | 전문직업 | E-5 | 200 | 200–204 | high | |
| 24 | 예술흥행 | E-6 | 205 | 205–211 | high | |
| 25 | 특정활동 | E-7 | 212 | 212–323 | high | Active grounding `e7_extension_2026_05` cites p.226. |
| 26 | 계절근로 | E-8 | 324 | 324–325 | high | |
| 27 | 비전문취업 | E-9 | 326 | 326–335 | high | |
| 28 | 선원취업 | E-10 | 336 | 336–340 | high | |
| 29 | 방문동거 | F-1 | 341 | 341–359 | high | |
| 30 | 거 주 | F-2 | 360 | 360–420 | high | **Re-derived** range 360–420 (F-3 follows at p421). |
| 31 | 동 반 | F-3 | 421 | 421–425 | high | **Re-derived** to p421 (pre-#155 map had p425). |
| 32 | 영주(F-5):동포,난민제외 | F-5 | 426 | 426–473 | high | **Re-derived** to p426 (pre-#155 map had p442). 동포/난민 F-5 under §36/§34. |
| 33 | 결혼이민 | F-6 | 474 | 474–497 | high | **Re-derived** to p474 (pre-#155 map had p478). |
| 34 | 기 타 | G-1 | 498 | 498–513 | high | **Re-derived** to p498 (pre-#155 map had p502). |
| 35 | 관광취업 | H-1 | 514 | 514–517 | high | **Re-derived** to p514 (pre-#155 map had p518). |
| 36 | 외국국적동포 관련 | special | 518 | 518–584 | high | 알기쉬운 외국국적동포 업무 매뉴얼 (Feb 2026). C-3-8, F-1, H-2, F-4, F-5. **Re-derived** start p518 (was p522). |
| 37 | 지역특화형비자 | special | 585 | 585–654 | high | 지역특화형비자 체류제도 주요내용 알림. REGION-S. **Re-derived** start p585 (was p589). |
| 38 | 국내 성장 기반 외국인 청소년 취업·정주 체류제도 | special | 655 | 655–669 | high | **Re-derived** start p655 (was p652). |
| 39 | 탑티어(Top-Tier) 비자 | special | 670 | 670–685 | high | 첨단분야 해외 인재 대상 탑티어(Top-Tier) 체류관리 매뉴얼. **Re-derived** start p670 (was p667). |
| 40 | 광역형 비자 시범사업 | special | 686 | 686–748 | high | 사증발급 및 체류관리지침. **Re-derived** start p686 (was p683). |
| 41 | K-STAR 비자트랙 제도 | special | 749 | 749–777 | high | 「K-STAR* 비자트랙」 제도 안내 매뉴얼. **Re-derived** start p749 (was p746); now extends to **p777** (was 774). Includes the 우수인재 붙임 appendix block. |

---

## Stay manual back-matter (pp.769–777) — the +3 pages added by PR #155

PR #155 named three new back-matter appendices: **붙임 8 — 인구감소지역 지정 변경 고시**, **붙임 9 — 우수인재 특별귀화 평가기준**, and **붙임 10 — 우수인재 국적신청 상세기술서**. Page-cited extraction from the 777-page PDF confirms those titles and shows the full back-matter appendix block runs **붙임 7 through 붙임 12** across pp.769–777, all inside the K-STAR §41 우수인재 block:

| Appendix | Title (Korean) | Page(s) | Evidence note |
|---|---|---:|---|
| 붙임 7 | 평가항목별 입증서류 | 769 | Pre-existing in the 774p layout. |
| 붙임 8 | 인구감소지역 지정 변경 고시 (행안부고시 제2024-15호, 2024.2.27. 개정) | 770 | PR #155 listed as a new appendix; page-cited at p770. |
| 붙임 9 | 우수인재 특별귀화 평가기준 (국적법 시행령 제6조제2항 고시, 2024.4.12.) | 771–773 | PR #155 listed as a new appendix; page-cited at pp.771–773. |
| 붙임 10 | 우수인재 국적신청 상세기술서 | 774–775 | PR #155 listed as a new appendix; page-cited at pp.774–775. |
| 붙임 11 | 우수인재 가점 항목별 점수표 | 776 | Inside the +3 added pages (775–777). |
| 붙임 12 | 우수인재 추천서 | 777 | Final page; inside the +3 added pages (775–777). |

**Honest attribution caveat:** Strict per-붙임 "new vs. pre-existing" attribution cannot be re-derived in PR B because PR #155 replaced the prior 774-page PDF in place. What is verifiable from the committed 777-page PDF is the page-cited layout above and the net +3 pages (pp.775–777). PR #155's identification of 붙임 8/9/10 is recorded faithfully; the live back-matter additionally carries 붙임 11 and 붙임 12.

---

## Section-ordering notes (re-derived from the 777-page stay PDF)

1. **D-8/D-9 are in normal page order** in the 777-page stay PDF (D-8 p115–129, then D-9 p130–141). The "D-9 before D-8" body-order-swap anomaly reported in the pre-#155 774-page map does NOT reproduce here.
2. **Visa F-4/F-5/H-2 remain pointers/partials to §38**: visa TOC §32 재외동포(F-4) says "※ 38.번 참조"; §33 영주(F-5) is partly covered by §38; §37 방문취업(H-2) is inside §38.
3. **Visa E-5/E-6 lack dedicated headers** (content embedded between E-4 p157 and E-7 p168); **stay E-2 lacks a dedicated header** (embedded between E-1 p175 and E-3 p185).
4. **Bundled sub-manual**: visa §38 / stay §36 are both the Feb-2026 "알기쉬운 외국국적동포 업무 매뉴얼" bound inside the May-2026 outer manual.

The machine-readable `2026_05_21_manual_toc_map.json` carries the same data and is the input to `2026_05_21_manual_json_crosswalk.json`.
