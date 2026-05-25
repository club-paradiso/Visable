#!/usr/bin/env python3
"""Deterministically regenerate the 2026-05-21 manual TOC map, manual→JSON
crosswalk, and full-record audit artifacts against the canonical 2026-05-21
PDFs installed by PR #155.

This script is PR B of the 2026-05-21 manual-update workflow. It is an
audit/report generator only:

  * It reads `visa_data.json`, `backend/data/visas.json`, `doc_master.json`,
    `docs/source-manuals/source_manifest.json`, and the two canonical PDFs.
  * It WRITES only the audit/report artifacts under `docs/data/`.
  * It never edits any production data file and never advances a `verified`
    flag or removes a `needsManualReview` flag.

Section page anchors below were re-derived from the canonical 484-page visa
PDF and 777-page stay PDF (post PR #155) using `pdftotext -layout`
(poppler-utils 24.02.0) form-feed page splitting plus a spaced-Korean-name +
`(CODE)` top-of-page header regex, with the special back-matter sections
located by canonical-title substring search. The detector output is pinned
here so the artifacts regenerate deterministically without re-running the PDF
toolchain.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "docs" / "data"

# --- Canonical source facts (must match source_manifest.json after PR #155) ---
VISA_PDF = ROOT / "docs/source-manuals/2026-05/visa_manual_2026_05.pdf"
STAY_PDF = ROOT / "docs/source-manuals/2026-05/stay_manual_2026_05.pdf"
VISA_SHA = "7fd79509c8c92ccd5e3b026d83f6884d69d3e0dcbcdf8c2936daf886a92ae11c"
STAY_SHA = "dd0d2f101c893022f24233d746dd24fc6bd9432eef3ea135f173e54d25f9c3e1"
VISA_PAGES = 484
STAY_PAGES = 777
STAY_PREVIOUS_PAGES = 774
SOURCE_DATE = "2026-05-21"
PDF_EXPORT_DATE = "2026-05-24"
BRANCH = "data/rebuild-2026-05-21-manual-crosswalk"
AUDIT_DATE = "2026-05-25"
EXTRACTION_TOOLING = (
    "pdftotext -layout (poppler-utils 24.02.0); pypdf 6.12.1 / pdfinfo for "
    "page-count verification; form-feed page splitting; spaced-Korean-name + "
    "(CODE) top-of-page header regex; canonical-title substring search for "
    "back-matter special sections"
)
SUPERSEDE_NOTE = (
    "This artifact supersedes the pre-PR #155 audit artifacts that were built "
    "against the earlier 774-page stay PDF (stay sha256 0492683…b3ba) and the "
    "earlier visa PDF (sha256 5a191aed…84063) under the 'source_date: "
    "unresolved' / 'PDFs not accessible' assumptions. PR #155 installed the "
    "canonical 2026-05-21 PDFs (visa 484p sha256 7fd795…ae11c; stay 777p "
    "sha256 dd0d2f…9c3e1), so these page anchors are now re-derived from the "
    "committed canonical sources, the stay manual is 777 pages (was 774), and "
    "source_date is '2026-05-21'."
)
SOURCE_NOTE = (
    "Page numbers are absolute physical PDF pages inside the canonical "
    "2026-05-21 source manuals committed at docs/source-manuals/2026-05/ and "
    "registered in docs/source-manuals/source_manifest.json (source_date "
    "2026-05-21; PDF internal export date 2026-05-24). These artifacts "
    "describe manual-section location only; they do NOT verify any visa_data "
    "record. Every manual-dependent record remains verified=false and "
    "needsManualReview=true."
)
DISCLAIMER = (
    "Internal audit artifact. Not legal advice and not an official "
    "immigration decision."
)

# --- Visa manual sections (484p; anchors unchanged vs pre-#155, page count
#     unchanged and cover/TOC byte-identical per source_manifest.json). -------
VISA_SECTIONS = [
    (1, "외 교", "A-1", 7, "7-9", "high", "First section after TOC/preamble."),
    (2, "공 무", "A-2", 10, "10-12", "high", None),
    (3, "협 정", "A-3", 13, "13-13", "high", "One-page section."),
    (4, "사증면제", "B-1", 14, "14-21", "high", "Includes treaty-country tables."),
    (5, "관광통과", "B-2", 22, "22-24", "high", "Includes 무사증입국 허가대상 국가일람표."),
    (6, "일시취재", "C-1", 25, "25-26", "high", None),
    (7, "단기방문", "C-3", 27, "27-50", "high", "Long section; C-3-1 through C-3-8 sub-codes."),
    (8, "단기취업", "C-4", 51, "51-59", "high", None),
    (9, "문화예술", "D-1", 60, "60-61", "high", None),
    (10, "유 학", "D-2", 62, "62-69", "high", "Active grounding d2_extension_2026_05 cites stay pp.43-44."),
    (11, "기술연수", "D-3", 70, "70-72", "high", None),
    (12, "일반연수", "D-4", 73, "73-87", "high", "Contains D-4-1, D-4-2K, D-4-3, D-4-5, D-4-6, D-4-7 sub-codes."),
    (13, "취 재", "D-5", 88, "88-89", "high", None),
    (14, "종 교", "D-6", 90, "90-91", "high", None),
    (15, "주 재", "D-7", 92, "92-101", "high", None),
    (16, "기업투자", "D-8", 102, "102-115", "high", None),
    (17, "무역경영", "D-9", 116, "116-121", "high", None),
    (18, "구 직", "D-10", 122, "122-135", "high", "Contains D-10-1, D-10-2, D-10-3, D-10-T sub-codes."),
    (19, "교 수", "E-1", 136, "136-141", "high", None),
    (20, "회화지도", "E-2", 142, "142-149", "high", None),
    (21, "연 구", "E-3", 150, "150-156", "high", None),
    (22, "기술지도", "E-4", 157, "157-163", "high", None),
    (23, "전문직업", "E-5", None, "~164-167", "low", "no-dedicated-header: strict title-anchor not found; content embedded between E-4 (p157) and E-7 (p168)."),
    (24, "예술흥행", "E-6", None, "~164-167", "low", "no-dedicated-header: strict title-anchor not found; content embedded between E-4 and E-7."),
    (25, "특정활동", "E-7", 168, "168-277", "high", "Long section. E-7-1/2/3/4/S/Y/T/91 sub-codes."),
    (26, "계절근로", "E-8", 278, "278-283", "high", None),
    (27, "비전문취업", "E-9", 284, "284-293", "high", None),
    (28, "선원취업", "E-10", 294, "294-296", "high", None),
    (29, "방문동거", "F-1", 297, "297-307", "high", None),
    (30, "거 주", "F-2", 308, "308-312", "high", "Contains F-2-2, F-2-3, F-2-7, F-2-99, F-2-T sub-codes."),
    (31, "동 반", "F-3", 313, "313-317", "medium", None),
    (32, "재외동포", "F-4", None, "see §38", "n/a", "TOC pointer '※ 38.번 참조'. F-4 content is inside §38 외국국적동포 sub-manual (detected anchor p415, range 379-444)."),
    (33, "영 주", "F-5", 318, "318-323", "medium", "§38 sub-manual also covers 외국국적동포 영주(F-5)."),
    (34, "결혼이민", "F-6", 324, "324-335", "high", "F-6-1/2/3 modeled in visa_data.json."),
    (35, "기 타", "G-1", 336, "336-342", "medium", None),
    (36, "관광취업", "H-1", 343, "343-378", "high", None),
    (37, "방문취업", "H-2", None, "see §38", "n/a", "H-2 외국국적동포 방문취업 content is inside §38 sub-manual."),
    (38, "알기쉬운 외국국적동포 업무매뉴얼", "special-외국국적동포", 379, "379-444", "high", "Bundled sub-manual dated '2026. 2.' (Feb 2026). Covers C-3-8, F-1, F-4, F-5, H-2."),
    (39, "탑티어(Top-Tier) 비자", "special-TopTier", 445, "445-455", "high", "첨단분야 해외 인재 대상 탑티어(Top-Tier) 체류관리 매뉴얼. Covers D-10-T, E-7-T, F-2-T, F-5-T."),
    (40, "K-STAR 비자트랙 제도", "special-K-STAR", 456, "456-484", "high", "「K-STAR* 비자트랙」 제도 안내 매뉴얼. Last section; ends on the final visa page (484)."),
]

# --- Stay manual sections (777p; anchors RE-DERIVED from the canonical
#     2026-05-21 PDF post-#155). Special-section anchors shifted vs the
#     pre-#155 774-page map; D-8/D-9 are in normal page order in this PDF. ----
STAY_SECTIONS = [
    (1, "외 교", "A-1", 14, "14-17", "high", None),
    (2, "공 무", "A-2", 18, "18-20", "high", None),
    (3, "협 정", "A-3", 21, "21-23", "high", None),
    (4, "사증면제", "B-1", 24, "24-24", "high", None),
    (5, "관광통과", "B-2", 25, "25-25", "high", None),
    (6, "일시취재", "C-1", 26, "26-26", "high", None),
    (7, "단기방문", "C-3", 27, "27-28", "high", None),
    (8, "단기취업", "C-4", 29, "29-31", "high", None),
    (9, "문화예술", "D-1", 32, "32-34", "high", None),
    (10, "유 학", "D-2", 35, "35-55", "high", "Active grounding d2_extension_2026_05 cites pp.43-44."),
    (11, "기술연수", "D-3", 56, "56-82", "high", None),
    (12, "일반연수", "D-4", 83, "83-101", "high", "Active grounding d4_extension_2026_05 cites pp.90-91 (D-4-1/D-4-7 어학연수생 extension)."),
    (13, "취 재", "D-5", 102, "102-104", "high", None),
    (14, "종 교", "D-6", 105, "105-107", "high", None),
    (15, "주 재", "D-7", 108, "108-114", "high", None),
    (16, "기업투자", "D-8", 115, "115-129", "high", "Re-derived: D-8 precedes D-9 in normal page order in the 777-page PDF; the pre-#155 D-8/D-9 body-order-swap anomaly does NOT reproduce."),
    (17, "무역경영", "D-9", 130, "130-141", "high", "Re-derived header at p130 (was reported at p112 in the pre-#155 774-page map); follows D-8 normally."),
    (18, "구 직", "D-10", 142, "142-165", "high", "D-10-T cross-references §39 탑티어."),
    (19, "교 수", "E-1", 166, "166-175", "high", None),
    (20, "회화지도", "E-2", None, "~176-184", "low", "no-dedicated-header: content embedded after E-1 (ends p175) and before E-3 (p185)."),
    (21, "연 구", "E-3", 185, "185-194", "high", None),
    (22, "기술지도", "E-4", 195, "195-199", "high", None),
    (23, "전문직업", "E-5", 200, "200-204", "high", None),
    (24, "예술흥행", "E-6", 205, "205-211", "high", None),
    (25, "특정활동", "E-7", 212, "212-323", "high", "Active grounding e7_extension_2026_05 cites p.226. E-7-1/2/3/4/S/Y/T/91 sub-codes."),
    (26, "계절근로", "E-8", 324, "324-325", "high", None),
    (27, "비전문취업", "E-9", 326, "326-335", "high", None),
    (28, "선원취업", "E-10", 336, "336-340", "high", None),
    (29, "방문동거", "F-1", 341, "341-359", "high", None),
    (30, "거 주", "F-2", 360, "360-420", "high", "Re-derived range 360-420 (F-3 follows at p421). Covers F-2-1..F-2-99 incl. F-2-T."),
    (31, "동 반", "F-3", 421, "421-425", "high", "Re-derived header at p421 (was p425 in the pre-#155 map)."),
    (32, "영주(F-5):동포,난민제외", "F-5", 426, "426-473", "high", "Re-derived header at p426 (was p442). 동포 and 난민 F-5 handled under §36/§34."),
    (33, "결혼이민", "F-6", 474, "474-497", "high", "Re-derived header at p474 (was p478). F-6-1/2/3 modeled in visa_data.json."),
    (34, "기 타", "G-1", 498, "498-513", "high", "Re-derived header at p498 (was p502)."),
    (35, "관광취업", "H-1", 514, "514-517", "high", "Re-derived header at p514 (was p518)."),
    (36, "외국국적동포 관련", "special-외국국적동포", 518, "518-584", "high", "알기쉬운 외국국적동포 업무 매뉴얼 (Feb 2026 sub-manual). Covers C-3-8, F-1, H-2, F-4, F-5. Re-derived start p518 (was p522)."),
    (37, "지역특화형비자", "special-지역특화", 585, "585-654", "high", "지역특화형비자 체류제도 주요내용 알림. REGION-S pilot. Re-derived start p585 (was p589)."),
    (38, "국내 성장 기반 외국인 청소년 취업·정주 체류제도", "special-청소년취업정주", 655, "655-669", "high", "국내 성장 기반 외국인 청소년 취업·정주 체류제도 알림. Re-derived start p655 (was p652)."),
    (39, "탑티어(Top-Tier) 비자", "special-TopTier", 670, "670-685", "high", "첨단분야 해외 인재 대상 탑티어(Top-Tier) 체류관리 매뉴얼. Covers D-10-T, E-7-T, F-2-T, F-5-T. Re-derived start p670 (was p667)."),
    (40, "광역형 비자 시범사업", "special-광역형", 686, "686-748", "high", "광역형 비자 시범사업 — 사증발급 및 체류관리지침. Re-derived start p686 (was p683)."),
    (41, "K-STAR 비자트랙 제도", "special-K-STAR", 749, "749-777", "high", "「K-STAR* 비자트랙」 제도 안내 매뉴얼. Re-derived start p749 (was p746); now extends to p777 (was 774). The +3 back-matter pages (775-777) fall inside this section's 붙임 appendix block (see back_matter)."),
]

# --- Stay back-matter appendix block re-derived from the 777-page PDF. -------
# PR #155 named 붙임 8/9/10 as the new appendices; page-cited evidence shows
# the 777-page back-matter actually runs 붙임 7..12 across pp.769-777. The net
# +3 pages (775-777) land in this block. Strict "new vs pre-existing"
# attribution per 붙임 number cannot be re-derived in PR B because PR #155
# replaced the prior 774-page PDF, so we record the verifiable page cites.
STAY_BACK_MATTER = [
    ("붙임 7", "평가항목별 입증서류", 769, "pre-existing in 774p layout (within K-STAR §41 우수인재 appendix block)"),
    ("붙임 8", "인구감소지역 지정 변경 고시 (행정안전부고시 제2024-15호, 2024.2.27. 개정)", 770, "PR #155 listed 붙임 8 among the new back-matter appendices; page-cited at p770"),
    ("붙임 9", "우수인재 특별귀화 평가기준 (국적법 시행령 제6조제2항 고시, 2024.4.12.)", 771, "PR #155 listed 붙임 9 among the new back-matter appendices; page-cited at pp.771-773"),
    ("붙임 10", "우수인재 국적신청 상세기술서", 774, "PR #155 listed 붙임 10 among the new back-matter appendices; page-cited at pp.774-775"),
    ("붙임 11", "우수인재 가점 항목별 점수표", 776, "page-cited at p776; falls inside the +3 added back-matter pages (775-777)"),
    ("붙임 12", "우수인재 추천서", 777, "page-cited at p777 (final page); falls inside the +3 added back-matter pages (775-777)"),
]

# --- Per-record crosswalk/classification mapping, keyed by array index. ------
# classification taxonomy: confirmed | partial | missing | duplicate | stale | unresolved
#   confirmed  = manual section located with a high-confidence page anchor.
#   partial    = located but no dedicated header / split across sections / approximate range.
#   missing    = no immigration-manual section maps to this record (helper/scenario/FAQ by design).
#   duplicate  = duplicate visa code in visa_data.json.
#   stale      = record carries a stale date marker (Feb-2026 sub-manual or 2026.3 income note).
#   unresolved = large special section / multi-program record needing dedicated extraction.
# NOTE: "confirmed" refers to manual-section LOCATION confidence ONLY. It does
# NOT mean the record is data-verified. All manual-dependent records remain
# verified=false and needsManualReview=true.

HELPER = ("missing", "no-change", "low",
          "Helper / scenario / FAQ / infrastructure record; not sourced from the immigration manuals. No manual section maps to it by design.")

# code/index -> (visa_section_label, visa_pages, stay_section_label, stay_pages,
#                classification, action, risk, notes, pr_queue)
RECORD_MAP = {
    # Manual-dependent standard records
    "B-1": ("§4 사증면제(B-1)", "14-21", "§4 사증면제(B-1)", "24", "confirmed", "needs-page-review", "medium",
            "67개국 treaty list; dataDate 2026-04-14 (immigration.go.kr, not the manual).", "PR-C"),
    "B-2": ("§5 관광통과(B-2)", "22-24", "§5 관광통과(B-2)", "25", "confirmed", "needs-page-review", "medium",
            "45개국 무사증 list; dataDate 2026-04-14 (immigration.go.kr).", "PR-C"),
    "C-3": ("§7 단기방문(C-3)", "27-50", "§7 단기방문(C-3)", "27-28", "confirmed", "needs-page-review", "medium",
            "Long visa section (24pp); C-3-1..C-3-8. visaIssuance=needs_review.", "PR-C"),
    "C-4": ("§8 단기취업(C-4)", "51-59", "§8 단기취업(C-4)", "29-31", "confirmed", "needs-page-review", "low", None, "PR-C"),
    "D-1": ("§9 문화예술(D-1)", "60-61", "§9 문화예술(D-1)", "32-34", "confirmed", "needs-page-review", "low", None, "PR-C"),
    "D-2": ("§10 유 학(D-2)", "62-69", "§10 유 학(D-2)", "35-55", "confirmed", "needs-page-review", "medium",
            "Active grounding d2_extension_2026_05 cites stay pp.43-44.", "PR-C"),
    "D-3": ("§11 기술연수(D-3)", "70-72", "§11 기술연수(D-3)", "56-82", "confirmed", "needs-page-review", "low", None, "PR-C"),
    "D-4": ("§12 일반연수(D-4)", "73-87", "§12 일반연수(D-4)", "83-101", "confirmed", "needs-page-review", "high",
            "Active grounding d4_extension_2026_05 cites stay pp.90-91. Parent of duplicated D-4-2K code.", "PR-C"),
    "D-7": ("§15 주 재(D-7)", "92-101", "§15 주 재(D-7)", "108-114", "confirmed", "needs-page-review", "low", None, "PR-C"),
    "D-8": ("§16 기업투자(D-8)", "102-115", "§16 기업투자(D-8)", "115-129", "confirmed", "needs-page-review", "low",
            "Stay D-8 (p115-129) precedes D-9 (p130-141) in normal order in the 777p PDF.", "PR-C"),
    "D-9": ("§17 무역경영(D-9)", "116-121", "§17 무역경영(D-9)", "130-141", "confirmed", "needs-page-review", "low",
            "Stay D-9 re-derived to p130-141 (pre-#155 map had p112-114).", "PR-C"),
    "D-10": ("§18 구 직(D-10)", "122-135", "§18 구 직(D-10)", "142-165", "confirmed", "needs-page-review", "medium",
             "D-10-1/2/3/T; D-10-T cross-refs §39 탑티어.", "PR-C"),
    "E-1": ("§19 교 수(E-1)", "136-141", "§19 교 수(E-1)", "166-175", "confirmed", "needs-page-review", "low", None, "PR-C"),
    "E-2": ("§20 회화지도(E-2)", "142-149", "§20 회화지도(E-2)", "~176-184", "partial", "needs-page-review", "low",
            "Stay E-2 lacks a dedicated header; range ~176-184 approximated between E-1 and E-3.", "PR-C"),
    "E-3": ("§21 연 구(E-3)", "150-156", "§21 연 구(E-3)", "185-194", "confirmed", "needs-page-review", "low", None, "PR-C"),
    "E-4": ("§22 기술지도(E-4)", "157-163", "§22 기술지도(E-4)", "195-199", "confirmed", "needs-page-review", "low", None, "PR-C"),
    "E-5": ("§23 전문직업(E-5)", "~164-167", "§23 전문직업(E-5)", "200-204", "partial", "needs-page-review", "medium",
            "Visa E-5 lacks a dedicated header (low confidence); stay confident at p200.", "PR-C"),
    "E-6": ("§24 예술흥행(E-6)", "~164-167", "§24 예술흥행(E-6)", "205-211", "partial", "needs-page-review", "medium",
            "Visa E-6 lacks a dedicated header (low confidence); stay confident at p205.", "PR-C"),
    "E-7": ("§25 특정활동(E-7)", "168-277", "§25 특정활동(E-7)", "212-323", "confirmed", "needs-page-review", "high",
            "Active grounding e7_extension_2026_05 cites stay p.226. 110pp visa / 112pp stay; E-7-1/2/3/4/S/Y/T/91.", "PR-C"),
    "E-8": ("§26 계절근로(E-8)", "278-283", "§26 계절근로(E-8)", "324-325", "confirmed", "needs-page-review", "low", None, "PR-C"),
    "E-9": ("§27 비전문취업(E-9)", "284-293", "§27 비전문취업(E-9)", "326-335", "confirmed", "needs-page-review", "low", None, "PR-C"),
    "E-10": ("§28 선원취업(E-10)", "294-296", "§28 선원취업(E-10)", "336-340", "confirmed", "needs-page-review", "low", None, "PR-C"),
    "F-1": ("§29 방문동거(F-1)", "297-307", "§29 방문동거(F-1)", "341-359", "confirmed", "needs-page-review", "medium", None, "PR-C"),
    "F-2": ("§30 거 주(F-2)", "308-312", "§30 거 주(F-2)", "360-420", "confirmed", "needs-page-review", "medium",
            "F-2-T (Top-Tier) sub-code. Stay range re-derived 360-420.", "PR-C"),
    "F-3": ("§31 동 반(F-3)", "313-317", "§31 동 반(F-3)", "421-425", "confirmed", "needs-page-review", "low",
            "Stay F-3 re-derived to p421-425.", "PR-C"),
    "F-5": ("§33 영 주(F-5) + §38 동포 F-5", "318-323 + 379-444", "§32 영주(F-5):동포,난민제외", "426-473", "partial", "needs-page-review", "medium",
            "Split across stay §32 (excludes 동포/난민) and §36 (동포 F-5). Stay range re-derived 426-473.", "PR-C"),
    "G-1": ("§35 기 타(G-1)", "336-342", "§34 기 타(G-1)", "498-513", "confirmed", "needs-page-review", "medium",
            "Refugee-adjacent statuses. Stay re-derived 498-513.", "PR-C"),
    "H-1": ("§36 관광취업(H-1)", "343-378", "§35 관광취업(H-1)", "514-517", "confirmed", "needs-page-review", "low",
            "Long visa section (36pp); stay re-derived 514-517.", "PR-C"),
    "A-1": ("§1 외 교(A-1)", "7-9", "§1 외 교(A-1)", "14-17", "confirmed", "needs-page-review", "low", None, "PR-C"),
    "A-2": ("§2 공 무(A-2)", "10-12", "§2 공 무(A-2)", "18-20", "confirmed", "needs-page-review", "low", None, "PR-C"),
    "A-3": ("§3 협 정(A-3)", "13", "§3 협 정(A-3)", "21-23", "confirmed", "needs-page-review", "low", "Visa section is one page.", "PR-C"),
    "C-1": ("§6 일시취재(C-1)", "25-26", "§6 일시취재(C-1)", "26", "confirmed", "needs-page-review", "low", None, "PR-C"),
    "D-5": ("§13 취 재(D-5)", "88-89", "§13 취 재(D-5)", "102-104", "confirmed", "needs-page-review", "low", None, "PR-C"),
    "D-6": ("§14 종 교(D-6)", "90-91", "§14 종 교(D-6)", "105-107", "confirmed", "needs-page-review", "low", None, "PR-C"),
    # Stale / duplicate / unresolved (PR-D content patches with page evidence)
    "F-4": ("§32 재외동포(F-4) → §38", "see §38 (379-444)", "§36 외국국적동포 관련", "518-584", "stale", "needs-followup-pr", "high",
            "Pointer-only in outer manual; content from the Feb-2026 외국국적동포 sub-manual. dataDate=2026-02-12. Stay §36 re-derived 518-584.", "PR-D"),
    "F-6": ("§34 결혼이민(F-6)", "324-335", "§33 결혼이민(F-6)", "474-497", "stale", "needs-followup-pr", "high",
            "STALE: F-6 income note still references '2026.3' (3 occurrences). PR #145 blocker. Stay §33 re-derived 474-497.", "PR-D"),
    "H-2": ("§37 방문취업(H-2) → §38", "see §38 (379-444)", "§36 외국국적동포 관련", "518-584", "stale", "needs-followup-pr", "high",
            "Feb-2026 sub-manual; 신규발급 중단 since 2026-02-12. dataDate=2026-02-12. Stay §36 re-derived 518-584.", "PR-D"),
    "K-STAR": ("§40 K-STAR 비자트랙", "456-484", "§41 K-STAR 비자트랙 제도", "749-777", "unresolved", "needs-followup-pr", "high",
               "Full dedicated sub-manual both manuals. Stay §41 re-derived 749-777 (was 746-774); includes 우수인재 붙임 appendix block (붙임 7-12, pp.769-777). All fields needsManualReview.", "PR-D"),
    "REGION-S": ("(no visa section)", "n/a", "§37 지역특화형비자 + §40 광역형 비자 시범사업", "585-654 + 686-748", "unresolved", "needs-followup-pr", "high",
                 "Models two stay-only special programs. §37 지역특화형 re-derived 585-654; §40 광역형 re-derived 686-748. All fields needsManualReview.", "PR-D"),
}

# D-4-2K duplicate handled per array index.
D4_2K_MAP = {
    24: ("§12 일반연수(D-4)", "73-87", "§12 일반연수(D-4)", "83-101", "duplicate", "needs-followup-pr", "high",
         "DUPLICATE CODE (shared with array index 55). This entry = 한국어연수(K-연수생) 어학연수. Needs distinct code or sub-code with page evidence.", "PR-D"),
    55: ("§12 일반연수(D-4)", "73-87", "§12 일반연수(D-4)", "83-101", "duplicate", "needs-followup-pr", "high",
         "DUPLICATE CODE (shared with array index 24). This entry = 기업맞춤형인턴십(K-Trainee), 2025-10-29 신설. Needs distinct code (e.g. D-4-2T) with page evidence.", "PR-D"),
}


def fail(msg: str) -> None:
    raise SystemExit(f"[regenerate_2026_05_21] ERROR: {msg}")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def pdf_page_count(path: Path) -> int | None:
    pdfinfo = shutil.which("pdfinfo")
    if pdfinfo:
        proc = subprocess.run([pdfinfo, str(path)], text=True,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if proc.returncode == 0:
            for line in proc.stdout.splitlines():
                if line.startswith("Pages:"):
                    return int(line.split(":", 1)[1].strip())
    try:
        import pypdf  # type: ignore
        return len(pypdf.PdfReader(str(path)).pages)
    except Exception:
        return None


def verify_source_state() -> None:
    if not VISA_PDF.exists() or not STAY_PDF.exists():
        fail("canonical PDFs not found under docs/source-manuals/2026-05/")
    vs, ss = sha256(VISA_PDF), sha256(STAY_PDF)
    if vs != VISA_SHA:
        fail(f"visa PDF sha256 mismatch: {vs} != {VISA_SHA}")
    if ss != STAY_SHA:
        fail(f"stay PDF sha256 mismatch: {ss} != {STAY_SHA}")
    vp, sp = pdf_page_count(VISA_PDF), pdf_page_count(STAY_PDF)
    if vp is not None and vp != VISA_PAGES:
        fail(f"visa PDF page count {vp} != {VISA_PAGES}")
    if sp is not None and sp != STAY_PAGES:
        fail(f"stay PDF page count {sp} != {STAY_PAGES}")
    manifest = json.loads((ROOT / "docs/source-manuals/source_manifest.json").read_text(encoding="utf-8"))
    cur = manifest["current"]
    if cur["visa_issuance_manual"].get("source_date") != SOURCE_DATE:
        fail("manifest visa source_date != 2026-05-21")
    if cur["stay_residence_manual"].get("source_date") != SOURCE_DATE:
        fail("manifest stay source_date != 2026-05-21")
    if cur["stay_residence_manual"].get("pages") != STAY_PAGES:
        fail("manifest stay pages != 777")
    if cur["stay_residence_manual"].get("file_sha256") != STAY_SHA:
        fail("manifest stay sha256 mismatch")
    print(f"[regenerate_2026_05_21] source state OK (visa {VISA_PAGES}p, stay {STAY_PAGES}p, source_date {SOURCE_DATE})")


def section_objs(rows):
    out = []
    for num, title, code, start, rng, conf, notes in rows:
        out.append({
            "toc_num": num, "title_ko": title, "code": code,
            "start_page": start, "page_range": rng,
            "confidence": conf, "notes": notes,
        })
    return out


def write_json(path: Path, obj) -> None:
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"[regenerate_2026_05_21] wrote {path.relative_to(ROOT)}")


def write_text(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")
    print(f"[regenerate_2026_05_21] wrote {path.relative_to(ROOT)}")


def gen_toc_map_json():
    return {
        "schema_version": "2.0",
        "audit_date": AUDIT_DATE,
        "branch": BRANCH,
        "pr": "B (after PR #155)",
        "supersedes": SUPERSEDE_NOTE,
        "source_note": SOURCE_NOTE,
        "extraction_tooling": EXTRACTION_TOOLING,
        "visa_manual": {
            "file": "docs/source-manuals/2026-05/visa_manual_2026_05.pdf",
            "sha256": VISA_SHA,
            "source_date": SOURCE_DATE,
            "pdf_internal_export_date": PDF_EXPORT_DATE,
            "total_pages": VISA_PAGES,
            "toc_section_count": 40,
            "anchors_changed_vs_pre_155": False,
            "anchors_note": "Visa page count unchanged (484) and cover/TOC byte-identical per source_manifest.json; re-detection on the canonical PDF reproduces the prior anchors exactly.",
            "sections": section_objs(VISA_SECTIONS),
        },
        "stay_manual": {
            "file": "docs/source-manuals/2026-05/stay_manual_2026_05.pdf",
            "sha256": STAY_SHA,
            "source_date": SOURCE_DATE,
            "pdf_internal_export_date": PDF_EXPORT_DATE,
            "total_pages": STAY_PAGES,
            "previous_pages": STAY_PREVIOUS_PAGES,
            "toc_section_count": 41,
            "anchors_changed_vs_pre_155": True,
            "anchors_note": "Special-section anchors (§36-§41) shifted vs the pre-#155 774-page map and were re-derived from the canonical 777-page PDF. The D-8/D-9 body-order-swap anomaly reported pre-#155 does NOT reproduce: D-8 p115-129 precedes D-9 p130-141.",
            "added_back_matter_pages": "775-777 (net +3 vs 774p), inside the K-STAR §41 우수인재 붙임 appendix block",
            "back_matter": [
                {"appendix": a, "title_ko": t, "start_page": p, "evidence_note": n}
                for (a, t, p, n) in STAY_BACK_MATTER
            ],
            "back_matter_note": (
                "PR #155 named 붙임 8 (인구감소지역 지정 변경 고시), 붙임 9 (우수인재 특별귀화 평가기준), "
                "and 붙임 10 (우수인재 국적신청 상세기술서) as the three new back-matter appendices. Page-cited "
                "evidence in the 777-page PDF places back-matter appendices 붙임 7-12 across pp.769-777, all inside "
                "the K-STAR §41 우수인재 block. The net +3 pages are pp.775-777. Strict per-붙임 new-vs-pre-existing "
                "attribution cannot be re-derived in PR B because PR #155 replaced the prior 774-page PDF."
            ),
            "sections": section_objs(STAY_SECTIONS),
        },
    }


def build_records():
    """Build crosswalk + audit record lists from visa_data.json (read-only)."""
    vd = json.loads((ROOT / "visa_data.json").read_text(encoding="utf-8"))
    cross = []
    audit = []
    for idx, r in enumerate(vd):
        code = r.get("code")
        name = r.get("name", "")
        cat = r.get("cat", "")
        dd = r.get("dataDate", "")
        sms = r.get("sourceManualStatus") or {}
        has_sms = bool(sms)
        verified = sms.get("verified")
        nmr = sms.get("needsManualReview")
        vmv = sms.get("visaManualVersion")
        smv = sms.get("stayManualVersion")

        if idx in D4_2K_MAP:
            vsec, vpg, ssec, spg, cls, action, risk, notes, prq = D4_2K_MAP[idx]
        elif code in RECORD_MAP:
            vsec, vpg, ssec, spg, cls, action, risk, notes, prq = RECORD_MAP[code]
        else:
            # helper / non-manual record
            cls, action, risk, notes = HELPER
            vsec = vpg = ssec = spg = None
            prq = "none"

        manual_dependent = has_sms
        stale = []
        if code == "F-6":
            stale.append("2026.3 income note (3 occurrences)")
        if idx == 42 or idx == 48 or code in ("F-4", "H-2"):
            stale.append("Feb-2026 외국국적동포 sub-manual (dataDate 2026-02-12)")

        cross.append({
            "array_index": idx,
            "record_code": code,
            "record_name": name,
            "record_type": cat,
            "manual_dependent": manual_dependent,
            "visa_section": vsec,
            "visa_pages": vpg,
            "stay_section": ssec,
            "stay_pages": spg,
            "has_sourceManualStatus": has_sms,
            "verified": verified,
            "needsManualReview": nmr,
            "stale_markers": stale,
            "classification": cls,
            "risk": risk,
            "action": action,
            "pr_queue": prq,
            "action_notes": notes,
        })
        audit.append({
            "array_index": idx,
            "code": code,
            "name": name,
            "cat": cat,
            "dataDate": dd,
            "has_sourceManualStatus": has_sms,
            "sourceManualStatus_verified": verified,
            "sourceManualStatus_needsManualReview": nmr,
            "visaManualVersion": vmv,
            "stayManualVersion": smv,
            "visa_section": vsec,
            "visa_pages": vpg,
            "stay_section": ssec,
            "stay_pages": spg,
            "stale_markers": stale,
            "classification": cls,
            "risk": risk,
            "action": action,
            "pr_queue": prq,
            "notes": notes,
        })
    return vd, cross, audit


def classification_counts(rows):
    counts = {}
    for r in rows:
        counts[r["classification"]] = counts.get(r["classification"], 0) + 1
    return counts


def main():
    verify_source_state()
    DATA.mkdir(parents=True, exist_ok=True)

    vd, cross, audit = build_records()
    cls_counts = classification_counts(cross)
    helper = sum(1 for r in cross if not r["manual_dependent"])
    md_dep = sum(1 for r in cross if r["manual_dependent"])
    pr_c = sum(1 for r in cross if r["pr_queue"] == "PR-C")
    pr_d = sum(1 for r in cross if r["pr_queue"] == "PR-D")

    # 1) TOC map JSON
    write_json(DATA / "2026_05_21_manual_toc_map.json", gen_toc_map_json())

    # 2) Crosswalk JSON
    write_json(DATA / "2026_05_21_manual_json_crosswalk.json", {
        "schema_version": "2.0",
        "audit_date": AUDIT_DATE,
        "branch": BRANCH,
        "pr": "B (after PR #155)",
        "supersedes": SUPERSEDE_NOTE,
        "source_note": SOURCE_NOTE,
        "disclaimer": DISCLAIMER,
        "classification_legend": {
            "confirmed": "Manual section located with a high-confidence page anchor (location only; NOT data-verified).",
            "partial": "Located but no dedicated header / split across sections / approximate range.",
            "missing": "No immigration-manual section maps to this record (helper/scenario/FAQ by design).",
            "duplicate": "Duplicate visa code in visa_data.json.",
            "stale": "Record carries a stale date marker (Feb-2026 sub-manual or 2026.3 income note).",
            "unresolved": "Large special section / multi-program record needing dedicated extraction.",
        },
        "summary": {
            "total_rows": len(cross),
            "helper_missing": helper,
            "manual_dependent": md_dep,
            "classification_counts": cls_counts,
            "pr_c_candidates": pr_c,
            "pr_d_candidates": pr_d,
            "all_manual_dependent_verified_false": all(
                r["verified"] is False for r in cross if r["manual_dependent"]),
            "all_manual_dependent_needsManualReview_true": all(
                r["needsManualReview"] is True for r in cross if r["manual_dependent"]),
            "changes_to_visa_data_json_in_this_pr": 0,
        },
        "crosswalk": cross,
    })

    # 3) Full audit JSON
    write_json(DATA / "2026_05_21_visa_data_full_audit.json", {
        "schema_version": "2.0",
        "audit_date": AUDIT_DATE,
        "branch": BRANCH,
        "pr": "B (after PR #155)",
        "supersedes": SUPERSEDE_NOTE,
        "source_note": SOURCE_NOTE,
        "disclaimer": DISCLAIMER,
        "summary": {
            "total_records": len(audit),
            "helper_no_manual_status": helper,
            "manual_dependent": md_dep,
            "verified_false": sum(1 for r in audit if r["sourceManualStatus_verified"] is False),
            "needs_manual_review_true": sum(1 for r in audit if r["sourceManualStatus_needsManualReview"] is True),
            "classification_counts": classification_counts(audit),
            "stale_2026_3_marker_records": [r["code"] for r in audit if any("2026.3" in s for s in r["stale_markers"])],
            "duplicate_code_D4_2K_indices": [r["array_index"] for r in audit if r["code"] == "D-4-2K"],
            "pr_c_candidates": pr_c,
            "pr_d_candidates": pr_d,
            "changes_to_visa_data_json_in_this_pr": 0,
        },
        "records": audit,
    })

    print(f"[regenerate_2026_05_21] records: {len(cross)} (helper/missing={helper}, manual_dependent={md_dep})")
    print(f"[regenerate_2026_05_21] classification: {cls_counts}")
    print(f"[regenerate_2026_05_21] PR-C candidates={pr_c}, PR-D candidates={pr_d}")
    print("[regenerate_2026_05_21] JSON artifacts regenerated. Markdown reports are maintained as committed narrative artifacts.")


if __name__ == "__main__":
    main()
