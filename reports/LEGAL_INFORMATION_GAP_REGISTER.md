# Legal Information Gap & Discrepancy Register: VISABLE R2

**Date**: 2026-10-19  
**Source Edition**: 2026.09 Ministry of Justice Immigration Manual Compilation  
**Scope**: 647 Situational Records (Extension: 224, Change: 251, Registration: 172) across 26 Offices  
**Auditor**: Independent Legal Information QA & Immigration Reliability Review Team

---

## 1. Overview & Classification Framework

The 647 records in VISABLE derive from an authoritative compilation of the Ministry of Justice's September 2026 immigration manual. To ensure legal reliability and prevent applicants from facing rejected submissions, this register classifies records across five distinct operational categories:

1. **Category A (Standard Baseline)**: Explicit, corroborable statutory requirements.
2. **Category B (Statutory Restrictions & Ineligibility)**: Situations where application is legally prohibited domestically or governed by a separate procedure.
3. **Category C (Mandatory In-Person & Biometric Procedures)**: Situations where proxy submission is statutorily barred or where biometric enrollment is compulsory.
4. **Category D (Manual Compilation Gaps / Unlisted Scenarios)**: Cases where the source manual does not list standalone checklists.
5. **Category E (Regional Office Discretion & Discrepancies)**: Jurisdictional variations and discretionary evidentiary demands.

---

## 2. Category-by-Category Analysis & Register

### Category B: Statutory Ineligibility & In-Country Change Bans

| Status Code | Procedure | Source Line | Statutory / Manual Basis | Issue Description | VISABLE R2 Handling |
|---|---|---:|---|---|---|
| **F-5 (전체)** | 체류기간 연장 | e-0766 | 출입국관리법 제10조, 제25조; 시행규칙 제33조의2 | 영주(F-5) 자격은 체류기간에 상한이 없으므로 연장 대상이 아님. 단, 10년 주기 영주증(외국인등록증) 갱신 의무 존재. | Checklist checkboxes disabled. Renders `.restriction-card` explaining that permanent residents do not extend stay, directing them to the 10-year card renewal procedure. |
| **D-4-5** | 체류자격 변경 | c-0118 | 출입국관리법 시행령 제29조; 연수생 관리지침 | 한식조리 연수생(D-4-5)은 국내에서 타 자격으로 변경하거나, 타 자격에서 D-4-5로의 국내 변경이 원칙적으로 제한됨. | Renders `.restriction-card` stating domestic change is restricted by rule; advises overseas consulate visa issuance. |
| **D-3** | 체류자격 변경 | c-0114 | 외국인근로자의 고용 등에 관한 법률; 출입국관리법 | 기술연수(D-3) 자격은 국내 체류자격 변경 원칙적 불허. 연수 종료 후 출국 원칙. | Renders `.restriction-card` highlighting change prohibition and advising departure/re-entry. |
| **E-6-2** | 체류자격 변경 | c-0172 | 출입국관리법 기본지침 (호텔·유흥 취업) | 호텔유흥(E-6-2) 종사자는 국내에서의 무분별한 자격변경이 엄격히 통제됨. | Renders restriction advisory detailing required performance recommendation (영상물등급위원회) or overseas consular track. |
| **H-1 / H-2** | 체류자격 변경 | c-0280, c-0285 | 워킹홀리데이 양자협정; 동포 취업지침 | 협정상 원칙적으로 국내 자격변경 불가 (단, 특정 전문직·우수인재 예외 조항 존재). | Flags general prohibition while providing exception references. |

---

### Category C: In-Person Appearance & Biometric Registration

Under Immigration Act Article 31 (Foreigner Registration) and Article 38 (Collection of Biometric Information):

| Target Population | Statutory Rule | Operational Impact | VISABLE R2 Handling |
|---|---|---|---|
| **All Foreign Residents Aged 17 or Older** | Initial Alien Registration / Residence Report | Under Article 38(1), applicants aged 17+ must provide facial image and fingerprint data in person at the immigration office. | In all `registration` checklists, renders prominent attendance card: *"신규 외국인등록 및 국내거소신고는 17세 이상 등록대상자의 생체정보(지문 및 얼굴) 등록이 법률상 필수이므로 반드시 본인이 직접 관할 청에 출석해야 합니다."* |
| **Minor Dependents (Under 17)** | Exemption from biometric registration | Legal representative (parent) may apply on their behalf without minor appearing. | Indicated in proxy guidance notes. |
| **Proxy Applications (Extension/Change)** | Administrative Attorney / Registered Employer / Immediate Family | Proxy application is permitted under Article 89, but the immigration chief retains the right to summon the applicant in person for interview (출석요구권). | Explicitly noted in the Attendance & Proxy section of every card. |

---

### Category D: Manual Gaps & Unlisted Standalone Scenarios

Across the 251 change-of-status scenarios, **33 records** (IDs `c-0299` through `c-0331`) contain the text `"독립된 변경 제출목록 확인 불가"` or `"원문 미기재"`:

| Scenario IDs | Sample Codes | Description | Risk If Unhandled | VISABLE R2 Handling |
|---|---|---|---|---|
| `c-0299` to `c-0331` | C-3-1, G-1 세부트랙, 단기체류자 특례 | The official manual omits dedicated standalone lists for these niche sub-situations, deferring to general officer discretion. | Previous UI rendered blank checklist rows or fake checkbox counts (0/0). | Renders dedicated `.unlisted-card`: *"2026년 9월 공식 매뉴얼에 독립된 제출서류 목록이 수록되어 있지 않습니다. 관할 출입국관서 또는 1345에 확인하세요."* Progress bar displays `공식 서류 목록 개별 확인 필요`. |

---

### Category E: Regional Office Practice & Discretionary Demands

| Jurisdiction | Status | Confirmed Practice vs. National Baseline | Statutory Basis | VISABLE R2 Policy |
|---|---|---|---|---|
| **제주출입국·외국인청 (Jeju)** | D-2, D-4 (유학·어학연수) | 무사증 입국 특례지역 특성상, 유학생 체재비 입증 기준(은행 잔고증명) 및 출석률 요구가 내륙 청보다 엄격히 적용될 수 있음. | 제주특별자치도 설치 및 국제자유도시 조성을 위한 특별법; 출입국관리법 | In `local-overrides.json`, only corroborated official notices are published. When selected, displays `제주출입국·외국인청 추가 확인` badge. |
| **All 26 Offices (Default)** | General Cases | Section chiefs possess discretionary authority under Enforcement Rule Article 76 to request supplementary documentation (보완서류요구권). | 출입국관리법 시행규칙 제76조 | Unselected or non-override offices display `전국 기준 안내`. Never promises "공통 적용" (which implies immunity from local requests). |

---

## 3. Recommendations for Future Curation

1. **Subcode Expansion**: Transition remaining `COMPILED_NEEDS_REVIEW` items to verified legal status as individual official notices are published by the Ministry of Justice.
2. **Dynamic 1345 API / HiKorea Synchronization**: Where accessible, automate change-log monitoring for HiKorea manual revisions.
3. **User Feedback Channels**: Provide non-legal users a direct link to report unexpected document requests received during in-person counter interviews.
