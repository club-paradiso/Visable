# Full manual coverage audit — 2026-06-08

Source-grounded audit of the official 2026.5 visa issuance manual and 2026.5/2026-06-01 stay/residence manual against `visa_data.json` and `doc_master.json`.

## Sources & extraction

| Manual | File | Version | Source date | Pages | Extraction |
|---|---|---|---|---|---|
| 사증발급 안내매뉴얼 | docs/source-manuals/2026-05/visa_manual_2026_05.pdf | 2026.5 | 2026-05-21 | 484 | pdftotext -layout |
| 외국인체류 안내매뉴얼 | docs/source-manuals/2026-06/stay_manual_2026_06_01.pdf | 2026.5 | 2026-06-01 | 777 | pdftotext -layout |

> The May and June stay manuals are byte-identical for all cited pages (verified by per-page text hashing of 13 sampled pages spanning the document). No OCR was used.

## Summary

- **inventory_items**: 64
- **searchable**: 62
- **active_but_unsearchable**: 0
- **deprecated_or_abolished**: 1
- **reference_only**: 2
- **internal_system_marker**: 1
- **legacy**: 1
- **needs_manual_review**: 3

## Coverage by classification

### represented_exactly (2)

| Code | Label | Manual | Pages | Searchable | Note |
|---|---|---|---|---|---|
| `K-STAR` | K-STAR 비자트랙 제도 | stay | K-STAR 매뉴얼 | ✅ | Program record; official subcodes (F-2-7S/F-5-S1/F-2-71/F-5-S2) now exposed. |
| `REGION-S` | 지역특화·광역형 비자 시범사업 | stay | 지역특화형 p. 67 / 광역형 매뉴얼 | ✅ | Program record; all official 지역특화형 subcodes now searchable/visible. |

### represented_as_subCode (53)

| Code | Label | Manual | Pages | Searchable | Note |
|---|---|---|---|---|---|
| `G-1-1` | 산업재해 청구 및 치료 중인 사람과 그 가족 | stay | p. 503 | ✅ | Prior data mislabeled G-1-1 as '난민인정 신청자' — corrected. |
| `G-1-2` | 질병·사고로 치료 중인 사람과 그 가족 | stay | pp. 503-504 | ✅ | Headline bug: previously not searchable (existed only as a procedure variant). Now a searchable subcode. |
| `G-1-3` | 각종 소송 진행 중인 사람 | stay | p. 504 | ✅ | 민사·형사·가사·행정 소송. |
| `G-1-4` | 임금체불로 노동관서에서 중재 중인 사람 | stay | pp. 504-505 | ✅ |  |
| `G-1-5` | 난민신청자 | stay | p. 505 | ✅ | Prior data mislabeled G-1-5 as '난민 가족결합' — corrected to 난민신청자. |
| `G-1-6` | 난민불인정자 중 인도적 체류허가자 | stay | p. 505 | ✅ |  |
| `G-1-7` | 사고 등으로 사망한 사람의 가족 | stay | pp. 497-498 | ✅ |  |
| `G-1-9` | 임신·출산 등 인도적 배려가 불가피한 사람 | stay | pp. 505-506 | ✅ |  |
| `G-1-10` | 외국인환자 (입국 후 장기치료 환자와 그 가족) | stay | p. 506 | ✅ | Normalized label/source (was '치료요양'). |
| `G-1-11` | 성폭력피해자 등 인도적 고려가 필요한 사람 | stay | pp. 506-507 | ✅ | Prior data mislabeled G-1-11 as '국내출생 외국국적 아동' — corrected. |
| `G-1-12` | 인도적 체류허가자의 가족 | stay | pp. 507-508 | ✅ | Prior data mislabeled G-1-12 as '긴급구제' — corrected. |
| `G-1-99` | 기타 사유에 해당되는 사람 | stay | pp. 503, 507 | ✅ | needsManualReview kept true (scenario-specific docs). |
| `C-3-7` | 도착관광 | visa | p. 27 | ✅ | In C-3 약호표; added as subcode. |
| `C-4-1` | 계절근로 단기취업 — MOU 외국지자체, 농업 | visa | pp. 277-278 | ✅ | '25년부터 단기취업 계절근로(C-4-1~4) 발급 중단. 현행은 E-8. |
| `C-4-2` | 계절근로 단기취업 — 결혼이민자 친척, 농업 | visa | pp. 277-278 | ✅ |  |
| `C-4-3` | 계절근로 단기취업 — MOU 외국지자체, 어업 | visa | pp. 277-278 | ✅ |  |
| `C-4-4` | 계절근로 단기취업 — 결혼이민자 친척, 어업 | visa | pp. 277-278 | ✅ |  |
| `C-4-5` | 계절근로 외 단기취업 | visa | pp. 277-278 | ✅ | 공연·강연·기술지도 등 90일 이하. 단순노무 제외. |
| `E-8-1` | 계절근로 — MOU 외국지자체, 농업 | visa | pp. 278-279 | ✅ |  |
| `E-8-2` | 계절근로 — 결혼이민자 4촌 친척, 농업 | visa | pp. 278-279 | ✅ |  |
| `E-8-3` | 계절근로 — MOU 외국지자체, 어업 | visa | pp. 278-279 | ✅ |  |
| `E-8-4` | 계절근로 — 결혼이민자 4촌 친척, 어업 | visa | pp. 278-279 | ✅ |  |
| `E-8-5` | 계절근로 — 기타(G-1) 활동 후 재입국 추천, 농업 | visa | pp. 278-279 | ✅ |  |
| `E-8-6` | 계절근로 — 기타(G-1) 활동 후 재입국 추천, 어업 | visa | pp. 278-279 | ✅ |  |
| `E-8-7` | 계절근로 — 유학생(D-2)의 부모, 농업 | visa | pp. 278-279 | ✅ |  |
| `E-8-8` | 계절근로 — 유학생(D-2)의 부모, 어업 | visa | pp. 278-279 | ✅ |  |
| `E-8-99` | 계절근로 — 언어소통 도우미 등 기타 보조 인력 | visa | pp. 278-279 | ✅ |  |
| `A-3-99` | Fulbright 협정대상자 | visa | p. 13 | ✅ |  |
| `D-8-4S` | 스타트업 코리아 특별비자 (기술창업 특례) | visa | pp. 106-107 | ✅ |  |
| `D-9-5` | 유학생 무역경영자 | stay | p. 133 | ✅ |  |
| `E-7-S1` | 네거티브 방식 전문인력 — 고소득자 | visa | pp. 169, 247 | ✅ | Distinct from E-7-S2; not collapsed into vague E-7-S. |
| `E-7-S2` | 네거티브 방식 전문인력 — 첨단산업분야 종사(예정)자 | visa | pp. 169, 247-248 | ✅ |  |
| `E-7-4R` | 지역특화형 숙련기능인력 | stay | p. 67 | ✅ | Linked to REGION-S. |
| `H-2-7` | 만기출국 후 재입국한 사람 | stay/visa | stay p. 33 / visa p. 405 | ✅ |  |
| `F-1-D` | 디지털노마드(워케이션) 비자 | visa | p. 303 | ✅ |  |
| `F-1-16` | 난민인정자의 배우자 및 미성년 자녀 (방문동거) | stay | p. 348 | ✅ | Promoted from procedure variant to searchable subcode. |
| `F-1-52` | 결혼이민자의 전혼관계 출생 미성년 자녀 (방문동거) | stay | pp. 350, 230 | ✅ | Promoted from procedure variant. |
| `F-2-7S` | K-STAR 거주 | visa/stay | visa p. 473 / stay K-STAR | ✅ | Distinct from F-2-7 점수제 거주. |
| `F-2-71` | K-STAR 거주자의 동반가족 | visa/stay | visa p. 480 / stay K-STAR | ✅ |  |
| `F-2-8` | 관광·휴양시설 투자 거주 | stay | pp. 375-378 | ✅ | Promoted from variant. |
| `F-2-81` | 관광·휴양시설 투자자의 배우자·자녀 거주 | stay | p. 378 | ✅ |  |
| `F-2-R` | 지역특화형 우수인재 | stay | p. 67 | ✅ | Also in REGION-S. |
| `F-2-T` | 최우수인재 거주 (Top-Tier) | stay | Top-Tier 매뉴얼 | ✅ |  |
| `F-5-S1` | K-STAR 영주 | visa/stay | visa p. 479 / stay K-STAR | ✅ |  |
| `F-5-S2` | K-STAR 영주자의 동반가족 | visa/stay | visa p. 480 / stay K-STAR | ✅ |  |
| `F-5-6R` | 지역특화형 재외동포영주 | stay | p. 67 | ✅ | Also in REGION-S. |
| `F-5-T` | 최우수인재 영주 (Top-Tier) | stay | Top-Tier 매뉴얼 | ✅ |  |
| `F-3-1R` | 지역인재가족 | stay | p. 67 | ✅ |  |
| `F-3-2R` | 지역동포가족 | stay | p. 67 | ✅ |  |
| `F-3-3R` | 지역숙련인력가족 | stay | p. 67 | ✅ |  |
| `F-4-R` | 지역특화형 재외동포 | stay | p. 67 | ✅ |  |
| `D-10-T` | 최우수인재 구직 (Top-Tier) | stay | p. 6 / Top-Tier 매뉴얼 | ✅ | '25.4 신설. Pre-existing; verified searchable. |
| `E-7-T` | 최우수인재 특정활동 (Top-Tier) | stay | Top-Tier 매뉴얼 | ✅ |  |

### program_helper (1)

| Code | Label | Manual | Pages | Searchable | Note |
|---|---|---|---|---|---|
| `YOUTH-STAY` | 국내 성장 기반 외국인 청소년 취업·정주 체류제도 | stay | pp. 134-135 | ✅ | No independent 체류자격 code in the manual; modeled as a searchable program helper linked to D-10 등 절차. |

### needs_manual_review (3)

| Code | Label | Manual | Pages | Searchable | Note |
|---|---|---|---|---|---|
| `G-1-8` | 장기체류 아동 | stay | pp. 2-3, 497 | ✅ | 장기체류 아동(G-1-8,13,14) 체계. Exact 8/13/14 split needs manual review. |
| `G-1-13` | 장기체류 아동 (체계) | stay | pp. 2-3 | ✅ | 장기체류 아동 체계. |
| `G-1-14` | 장기체류 아동 (체계) | stay | pp. 2-3 | ✅ | 장기체류 아동 체계. |

### deprecated_or_abolished (1)

| Code | Label | Manual | Pages | Searchable | Note |
|---|---|---|---|---|---|
| `C-3-11` | 교대선원 | visa | p. 33 | ✅ | 코로나19 한시 지침, '22.6. 폐지. Searchable but flagged 폐지/비활성. |

### reference_only (2)

| Code | Label | Manual | Pages | Searchable | Note |
|---|---|---|---|---|---|
| `G-1-19` | 기타(G-1) 계절근로 참여자 (재입국 추천 연계 표기) | visa | pp. 278-279 | ✅ | Quarantined: appears only as E-8-5/E-8-6 re-entry recommendation marker; not user-facing status guidance. |
| `C-3-91` | 칭다오·충칭 지역 호구자 (복수사증 지역 분류) | visa | p. 36 | ❌ | Local hukou-based multiple-entry classification; not added as an active subcode. |

### internal_system_marker (1)

| Code | Label | Manual | Pages | Searchable | Note |
|---|---|---|---|---|---|
| `E-7-H` | (체류자격외활동 전산기호) | stay | p. 499 | ❌ | Quarantined: 전산기호 for 자격외활동 입력, NOT a user-facing status code. Not added as a subcode. |

### legacy (1)

| Code | Label | Manual | Pages | Searchable | Note |
|---|---|---|---|---|---|
| `D-3-1` | 구 D-3-1 자격 등록자 (레거시) | visa | p. 352 | ✅ | '06.12.31.까지 등록. 현행은 D-3-11/12/13. |

## Quarantined (not shown as active options)

- `C-3-11` 교대선원 — deprecated (코로나19 한시 지침, '22.6. 폐지).
- `C-4-1`~`C-4-4` 계절근로 단기취업 — suspended ('25년부터 발급 중단; 현행 E-8).
- `D-3-1` — legacy ('06.12.31.까지 등록자; 현행 D-3-11/12/13).
- `G-1-19` — reference_only (E-8 재입국 추천 연계 표기).
- `C-3-91` 칭다오·충칭 호구자 — reference_only (지역 복수사증 분류).
- `E-7-H` — internal_system_marker (체류자격외활동 전산기호, not a status code).
