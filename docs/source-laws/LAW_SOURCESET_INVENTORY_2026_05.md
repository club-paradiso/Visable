# Paradiso official law/manual source-set inventory - 2026.5

## Executive status

Final source-set PR status: **READY_FOR_SOURCESET_PR**.

This inventory records the official Korean immigration/residence law, manual, and HiKorea source set needed before Paradiso performs any source-confirmed data patch. It is documentation-only. It does not authorize changes to `visa_data.json`, `backend/data/visas.json`, verification metadata, or AI grounding behavior.

The earlier broad `NOT_FOUND` framing should be retired for the core source set. Most remaining issues should be tracked with narrower labels: `DATE_VERIFICATION_GAP`, `ATTACHMENT_DOWNLOAD_GAP`, `FIELD_CROSSWALK_GAP`, and `SCHEMA_GAP`.

## Source role labels

| Role | Meaning |
| --- | --- |
| `canonical_legal_source` | law.go.kr legal text for statutes, enforcement decrees, and enforcement rules. |
| `official_source_directory` | Official HiKorea page linking to laws, manuals, or guidelines. |
| `official_manual_notice` | Official HiKorea notice that posts manual attachments. |
| `official_manual` | User-provided or repository-stored manual file matching the official notice/manual metadata. |
| `official_manual_revision_history` | Public revision-history attachment posted with the manuals. |
| `core_procedure_source` | HiKorea procedure guide page directly explaining a procedure. |
| `official_forms_source` | HiKorea official application/forms directory. |
| `supporting_service_source` | HiKorea service page useful for UI guidance but not substantive eligibility authority. |
| `implementation_target` | Paradiso data files. Not source authority. |

## Core official source directory

HiKorea `출입국관련 법령지침정보` should be treated as a core official source directory because it links the main law sets and administrative manuals used by Paradiso.

- Official route: `https://www.hikorea.go.kr/guide/LawLink.pt`
- Source role: `official_source_directory`
- Use: source discovery, retrieval path verification, and manual/law inventory anchoring.
- Do not use this directory alone to patch production data. Field-level patches still need the actual manual page, official guide page, or law article.

## Law source inventory

| Set | Korean title | Working English title | Source type | Official route | Access | Verification status |
| --- | --- | --- | --- | --- | --- | --- |
| Immigration | 출입국관리법 | Immigration Control Act | statute | `https://www.law.go.kr/법령/출입국관리법` | VIEW_ONLY | route confirmed; date already sampled |
| Immigration | 출입국관리법 시행령 | Enforcement Decree of the Immigration Control Act | enforcement decree | `https://www.law.go.kr/법령/출입국관리법시행령` | VIEW_ONLY | route confirmed; date verification may need final pass |
| Immigration | 출입국관리법 시행규칙 | Enforcement Rule of the Immigration Control Act | enforcement rule | `https://www.law.go.kr/법령/출입국관리법시행규칙` | VIEW_ONLY | route confirmed; date already sampled |
| Nationality | 국적법 | Nationality Act | statute | `https://www.law.go.kr/법령/국적법` | VIEW_ONLY | route confirmed; date verification may need final pass |
| Nationality | 국적법 시행령 | Enforcement Decree of the Nationality Act | enforcement decree | `https://www.law.go.kr/법령/국적법시행령` | VIEW_ONLY | route confirmed |
| Nationality | 국적법 시행규칙 | Enforcement Rule of the Nationality Act | enforcement rule | `https://www.law.go.kr/법령/국적법시행규칙` | VIEW_ONLY | route confirmed |
| Refugee | 난민법 | Refugee Act | statute | `https://www.law.go.kr/법령/난민법` | VIEW_ONLY | route confirmed |
| Refugee | 난민법 시행령 | Enforcement Decree of the Refugee Act | enforcement decree | `https://www.law.go.kr/법령/난민법시행령` | VIEW_ONLY | route confirmed; Refworld is secondary only |
| Refugee | 난민법 시행규칙 | Enforcement Rule of the Refugee Act | enforcement rule | `https://www.law.go.kr/법령/난민법시행규칙` | VIEW_ONLY | route confirmed; date verification pending |
| Overseas Koreans | 재외동포의 출입국과 법적 지위에 관한 법률 | Act on the Immigration and Legal Status of Overseas Koreans | statute | `https://www.law.go.kr/법령/재외동포의출입국과법적지위에관한법률` | VIEW_ONLY | route confirmed; KLRI is secondary only |
| Overseas Koreans | 재외동포의 출입국과 법적 지위에 관한 법률 시행령 | Enforcement Decree of the Overseas Koreans Act | enforcement decree | `https://www.law.go.kr/법령/재외동포의출입국과법적지위에관한법률시행령` | VIEW_ONLY | route confirmed; date verification pending |
| Overseas Koreans | 재외동포의 출입국과 법적 지위에 관한 법률 시행규칙 | Enforcement Rule of the Overseas Koreans Act | enforcement rule | `https://www.law.go.kr/법령/재외동포의출입국과법적지위에관한법률시행규칙` | VIEW_ONLY | route confirmed; date verification pending |
| Treatment of Foreigners | 재한외국인 처우 기본법 | Framework Act on Treatment of Foreigners Residing in Korea | statute | `https://www.law.go.kr/법령/재한외국인처우기본법` | VIEW_ONLY | route confirmed; date verification pending |
| Treatment of Foreigners | 재한외국인 처우 기본법 시행령 | Enforcement Decree of the Framework Act on Treatment of Foreigners | enforcement decree | `https://www.law.go.kr/법령/재한외국인처우기본법시행령` | VIEW_ONLY | route confirmed; date verification pending |

## Official manual and HiKorea guide inventory

| Korean title | Source role | Official route | Access | Use in Paradiso |
| --- | --- | --- | --- | --- |
| 체류자격별 통합 안내 매뉴얼(최신) | official_manual_notice | `https://www.hikorea.go.kr/board/BoardNtcDetailR.pt?BBS_GB_CD=BS10&BBS_SEQ=1&NTCCTT_SEQ=1062&page=1` | ACCESSIBLE | Confirms official 260521 manual attachments. |
| 사증발급 안내매뉴얼 | official_manual | `docs/source-manuals/2026-05/visa_manual_2026_05.pdf` | LOCAL_PDF | Primary extraction source for visa issuance records. |
| 외국인체류 안내매뉴얼 / 체류민원 안내매뉴얼 | official_manual | `docs/source-manuals/2026-05/stay_manual_2026_05.pdf` | LOCAL_PDF | Primary extraction source for stay/residence procedures. |
| 사증·체류 민원 자격별 안내 매뉴얼 수정 이력(공개) | official_manual_revision_history | HiKorea manual notice attachment | NEEDS_ATTACHMENT_ARCHIVE | Citation drift and update-history tracking. |
| 출입국/체류안내 메인 | official_source_directory | `https://www.hikorea.go.kr/info/InfoMain.pt` | ACCESSIBLE | Directory for official procedure pages. |
| 외국인등록 | core_procedure_source | `https://www.hikorea.go.kr/info/InfoDatail.pt?CAT_SEQ=176&PARENT_ID=139` | ACCESSIBLE | Registration tab and checklist framing. |
| 체류기간 연장 | core_procedure_source | `https://www.hikorea.go.kr/info/InfoDatail.pt?CAT_SEQ=181&PARENT_ID=140` | ACCESSIBLE | Extension tab framing. |
| 체류자격변경 | core_procedure_source | `https://www.hikorea.go.kr/info/InfoDatail.pt?CAT_SEQ=184&PARENT_ID=141` | ACCESSIBLE | Change-of-status tab framing. |
| 근무처변경/추가 | core_procedure_source | `https://www.hikorea.go.kr/info/InfoDatail.pt?CAT_SEQ=189&PARENT_ID=143` | ACCESSIBLE | Workplace-change guidance. |
| 외국인등록사항 변경 신고의무 / 여권정보 변경 | core_procedure_source | `https://www.hikorea.go.kr/info/InfoDatail.pt?CAT_SEQ=196&PARENT_ID=146` | ACCESSIBLE | Passport/change reporting guidance. |
| 체류지변경 신고의무 | core_procedure_source | `https://www.hikorea.go.kr/info/InfoDatail.pt?CAT_SEQ=197&PARENT_ID=146` | ACCESSIBLE | Address-change reporting guidance. |
| 전자민원 안내 | supporting_service_source | `https://www.hikorea.go.kr/cvlappl/CvlapplInfoPageR.pt` | ACCESSIBLE | Online application UI guidance. |
| 방문예약 안내 | supporting_service_source | `https://www.hikorea.go.kr/resv/ResvIntroR.pt` | ACCESSIBLE | Reservation/help UI guidance. |
| 민원서식 | official_forms_source | `https://www.hikorea.go.kr/board/BoardApplicationListR.pt` | ACCESSIBLE | Official form names and application-form references. |

## Implementation targets, not source authority

- `visa_data.json`
- `backend/data/visas.json`
- `doc_master.json`
- frontend display code
- AI answer generation logic

These files must not be treated as source authority. They may only be patched after a full manual/law/HiKorea crosswalk proves field-level support.
