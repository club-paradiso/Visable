#!/usr/bin/env python3
"""Authoring source for data/guidance-rules-202609.json.

Every rule here is transcribed from the September 2026 Ministry of Justice
manuals. Each guidance entry and each document item carries an `anchor`: a
verbatim (whitespace-insensitive) substring of the manual text. The build
(scripts/build_status_coverage_manifest.py) resolves anchors to PDF pages and
HWP line numbers and FAILS when an anchor cannot be found, so nothing in this
file can drift away from the source without breaking the build.

Run:  python3 scripts/status_guidance/author_rules.py   (rewrites the JSON)
"""
import json
import re
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
OUT = os.path.join(ROOT, 'data', 'guidance-rules-202609.json')

STAY = 'stay_manual_2026_09_18'
VISA = 'visa_manual_2026_09_01'

# --------------------------------------------------------------------------
# Procedure catalog (one domain each — never mixed)
# --------------------------------------------------------------------------
PROCEDURES = [
    ('visa_issuance', 'visa', '사증발급', 'Visa issuance', ['사증발급', '사증 발급', '비자발급', '비자 발급', '비자 신청', '사증신청', '사증 신청', 'visa application', 'apply for a visa', 'visa issuance']),
    ('visa_issuance_confirmation', 'visa', '사증발급인정서', 'Confirmation of visa issuance', ['사증발급인정', '인정서', '발급인정서', 'confirmation of visa issuance', 'cvi']),
    ('electronic_visa', 'visa', '전자사증', 'Electronic visa', ['전자사증', '전자비자', 'e-visa', 'evisa', 'electronic visa']),
    ('status_grant', 'stay', '체류자격 부여', 'Status grant', ['자격부여', '자격 부여', '체류자격 부여', '국내출생', '국내 출생', '출생 자녀', 'status grant', 'born in korea']),
    ('status_change', 'stay', '체류자격 변경', 'Change of status', ['자격변경', '자격 변경', '체류자격 변경', '체류자격변경', '변경허가', '비자 변경', '비자변경', '으로 변경', '로 변경', 'change of status', 'status change', 'change visa', 'switch']),
    ('extension', 'stay', '체류기간 연장', 'Extension of stay', ['연장', '체류기간', '기간연장', 'extension', 'extend', 'renew', 'renewal']),
    ('registration', 'stay', '외국인등록', 'Foreign resident registration', ['외국인등록', '외국인 등록', '등록증 발급', 'registration', 'register', 'arc', 'residence card']),
    ('card_reissue', 'stay', '외국인등록증 재발급', 'Residence card reissue', ['재발급', '등록증 재발급', '분실', 'reissue', 'lost card', 'replace card']),
    ('activities_outside_status', 'stay', '체류자격외 활동', 'Activities outside status', ['자격외', '자격 외', '자격외활동', '겸직', 'outside status', 'other activities']),
    ('part_time_work', 'stay', '시간제 취업', 'Part-time work permission', ['아르바이트', '알바', '시간제', '시간제취업', 'part-time', 'part time', 'parttime']),
    ('workplace_change', 'stay', '근무처 변경·추가', 'Workplace change / addition', ['근무처', '근무처변경', '이직', '회사 변경', '사업장 변경', '직장 변경', '회사 옮', 'workplace', 'change employer', 'new employer', 'change job']),
    ('workplace_report', 'stay', '근무처 신고', 'Workplace reporting', ['취업개시 신고', '고용 신고', '근무처 신고', 'workplace report']),
    ('reentry', 'stay', '재입국허가', 'Re-entry permit', ['재입국', 're-entry', 'reentry', 'leave and return']),
    ('residence_report', 'stay', '체류지 변경 신고', 'Change-of-address report', ['주소 변경', '주소변경', '체류지 변경', '체류지변경', '이사', 'address change', 'moved', 'new address']),
    ('registration_info_report', 'stay', '등록사항 변경신고', 'Registration-information report', ['등록사항', '여권 변경', '여권변경', '학교 변경', '학교변경', '소속기관 변경', 'registration information', 'passport renewal report', 'school change']),
    ('program_condition_change', 'stay', '허가조건 변경', 'Program condition change', ['허가조건', '조건 변경', 'condition change']),
]

PROCEDURE_STATES = ['SUPPORTED', 'CONDITIONAL', 'NOT_APPLICABLE', 'GENERALLY_NOT_PERMITTED', 'EXCEPTION_ONLY', 'LEGACY_ONLY', 'SOURCE_ONLY', 'UNVERIFIED']
COVERAGE_STATES = ['SUPPORTED', 'PARTIAL', 'SOURCE_ONLY', 'UNVERIFIED', 'NOT_APPLICABLE', 'LEGACY_ONLY']
REQ_LEVELS = ['REQUIRED_BASELINE', 'CONDITIONAL_REQUIRED', 'ADDITIONAL_IF_APPLICABLE', 'ALTERNATIVE_DOCUMENT', 'MAY_BE_REQUESTED_BY_OFFICER', 'ADMIN_INFO_CHECKABLE', 'PREVIOUSLY_SUBMITTED_MAY_BE_OMITTED', 'SOURCE_MENTIONS_BUT_NOT_STRUCTURED', 'NOT_APPLICABLE', 'LEGACY_ONLY']
COMPLETENESS = ['FULLY_STRUCTURED', 'PARTIALLY_STRUCTURED', 'SOURCE_ONLY', 'REQUIRES_CLARIFICATION', 'UNVERIFIED']
ROLES = ['applicant', 'inviter', 'employer', 'educational_institution', 'korean_spouse', 'principal_holder', 'local_government', 'sponsor', 'business_entity', 'ship_owner', 'agency', 'medical_institution', 'other_third_party']

# --------------------------------------------------------------------------
# Reusable document definitions (names only — applicability is per guidance)
# --------------------------------------------------------------------------
DOCDEFS = {
    'app_form_34': ('통합신청서 (별지 제34호 서식)', 'Integrated application form (Form 34)', 'applicant', 'hikorea'),
    'app_form': ('신청서', 'Application form', 'applicant', 'hikorea'),
    'passport': ('여권', 'Passport', 'applicant', None),
    'passport_original': ('여권 원본', 'Passport (original)', 'applicant', None),
    'passport_copy': ('여권 사본', 'Passport copy', 'applicant', None),
    'arc': ('외국인등록증', 'Residence card (ARC)', 'applicant', None),
    'arc_copy': ('신분증 사본', 'Copy of ID card', 'applicant', None),
    'fee': ('수수료', 'Fee', 'applicant', None),
    'photo': ('표준규격 사진 1매', 'One standard-size photo', 'applicant', None),
    'residence_proof': ('체류지 입증서류', 'Proof of residence', 'applicant', None),
    'guarantor': ('신원보증서', 'Letter of guarantee', 'sponsor', None),
    'relative_resident_reg': ('국내 친·인척의 주민등록등본', 'Resident registration copy of the Korean relative', 'inviter', 'community_center'),
    'family_relation': ('가족관계 입증서류', 'Proof of family relationship', 'applicant', None),
    'family_relation_cert': ('가족관계기록사항에 관한 증명서', 'Certificate of family relations record', 'applicant', 'community_center'),
    'hukou': ('호구부·거민증 등 본인 신분 확인 서류', 'Household register / resident ID (identity proof)', 'applicant', None),
    'diplomat_id': ('공관원 신분증', 'Mission staff ID', 'principal_holder', None),
    'embassy_letter': ('주한대사관 협조공문', 'Cooperation letter from the embassy', 'principal_holder', None),
    'employment_contract': ('고용계약서', 'Employment contract', 'employer', None),
    'domestic_help_contract': ('가사보조인 고용계약서', 'Domestic helper employment contract', 'employer', None),
    'employer_cert': ('고용주의 재직증명서(신분증명서)', "Employer's certificate of employment (ID)", 'employer', None),
    'fdi_report': ('외국인투자신고서(법인등기사항전부증명서 또는 사업자등록증 사본) 또는 투자기업등록증 사본', 'Foreign investment report (corporate register / business registration copy) or investment company registration copy', 'employer', None),
    'divorce_marriage_cert': ('이혼 사실이 기재된 혼인관계증명서', 'Marriage-relation certificate showing the divorce', 'applicant', 'community_center'),
    'stay_necessity_proof': ('체류 불가피성 소명자료(사유서, 재산분할 관련 입증자료 등)', 'Evidence of unavoidable stay (statement, property-division evidence, etc.)', 'applicant', None),
    'other_officer_docs': ('기타 심사에 필요하다고 인정되는 서류', 'Other documents the officer considers necessary', 'applicant', None),
    'student_enrollment_proof': ('외국인유학생 재학 입증서류(재학증명서, 입학허가서 등)', "Proof of the student's enrollment (enrollment certificate, admission letter)", 'educational_institution', None),
    'living_cost_proof': ('국내 체류비용 부담능력 입증서류(3개월 이상 예치된 잔고증명서 또는 입출금내역서 등)', 'Proof of ability to cover living costs (balance certificate held 3+ months, transaction history)', 'applicant', 'bank'),
    'refugee_residence_proof': ('체류지 입증서류(주거확인서 포함)', 'Proof of residence (incl. housing confirmation)', 'applicant', None),
    'birth_family_proof': ('출생증명서, 가족관계 소명 서류 등', 'Birth certificate, family-relationship evidence', 'applicant', None),
    'f27_grant_docs': ('점수제 우수인재(F-2-7) 거주자격 부여허가 시 제출서류', 'Documents submitted for the F-2-7 status grant', 'principal_holder', None),
    'principal_passport_arc': ('주체류자와 그 배우자의 여권 및 외국인등록증 사본', "Principal holder's and spouse's passport and residence card copies", 'principal_holder', None),
    'principal_employment': ('주체류자의 고용계약서 또는 재직증명서', "Principal holder's employment contract or certificate of employment", 'principal_holder', None),
    'tb_cert': ('결핵진단서', 'Tuberculosis certificate', 'applicant', 'designated_hospital'),
    'non_employment_pledge': ('비취업서약서', 'Pledge not to work', 'applicant', 'hikorea'),
    'inviter_basic_cert': ('초청인의 기본증명서', "Inviter's basic certificate", 'inviter', 'community_center'),
    'inviter_family_cert': ('초청인의 가족관계증명서', "Inviter's family-relation certificate", 'inviter', 'community_center'),
    'inviter_marriage_cert': ('초청인의 혼인관계증명서', "Inviter's marriage-relation certificate", 'inviter', 'community_center'),
    'inviter_resident_reg': ('초청인의 주민등록표(등본)', "Inviter's resident registration copy", 'inviter', 'community_center'),
    'child_family_cert': ('자녀 명의 가족관계증명서', "Child's family-relation certificate", 'inviter', 'community_center'),
    'pregnancy_cert': ('임신진단서 또는 산모수첩', 'Pregnancy certificate or maternity handbook', 'inviter', 'hospital'),
    'adoption_cert': ('초청인의 입양관계증명서', "Inviter's adoption-relation certificate", 'inviter', 'community_center'),
    'full_adoption_cert': ('초청인의 친양자입양관계증명서', "Inviter's full-adoption relation certificate", 'inviter', 'community_center'),
    'child_enrollment': ('자녀 재학증명서', "Child's enrollment certificate", 'inviter', 'school'),
    'severe_illness_proof': ('중증질환·장애 증명서류(산정특례 기재 진료비 영수증, 장애인증명서 등)', 'Proof of severe illness/disability (special-case medical receipts, disability certificate)', 'inviter', 'hospital'),
    'adoption_progress': ('입양 절차 진행 입증서류', 'Proof that the adoption procedure is in progress', 'applicant', None),
    'spouse_basic_cert': ('결혼이민자의 한국인 배우자의 기본증명서', "Korean spouse's basic certificate", 'korean_spouse', 'community_center'),
    'spouse_family_cert': ('한국인 배우자의 가족관계증명서', "Korean spouse's family-relation certificate", 'korean_spouse', 'community_center'),
    'spouse_marriage_cert_detail': ('한국인 배우자의 혼인관계증명서(상세)', "Korean spouse's marriage-relation certificate (detailed)", 'korean_spouse', 'community_center'),
    'spouse_resident_reg': ('한국인 배우자의 주민등록등본', "Korean spouse's resident registration copy", 'korean_spouse', 'community_center'),
    'enrollment_cert': ('재학증명서', 'Enrollment certificate', 'educational_institution', 'school'),
    'employment_cert_1y': ('재직증명서(동일 업종 1년 이상 종사 입증)', 'Certificate of employment (1+ year in the same industry)', 'employer', None),
    'income_proof': ('급여명세서, 잔고증명 등 소득 증빙 서류', 'Income evidence (pay slips, balance certificate)', 'applicant', None),
    'criminal_record_health_ins': ('범죄경력증명서, 의료보험 가입 증명서', 'Criminal record certificate, health insurance certificate', 'applicant', None),
    'regional_stay_proof': ('비수도권·인구감소(관심)지역 체류 예정 입증서류(1개월 이상 임대차계약서, 워케이션 시설·숙소 이용기록 등)', 'Proof of planned stay outside the capital region / in a depopulation area (1+ month lease, workation facility records)', 'applicant', None),
    'employment_permit_copy': ('고용허가서 사본', 'Employment permit copy', 'employer', 'employment_center'),
    'standard_contract_copy': ('표준근로계약서 사본', 'Standard labor contract copy', 'employer', None),
    'business_reg_copy': ('사업자등록증 사본', 'Business registration copy', 'employer', None),
    'business_reg': ('사업자등록증', 'Business registration certificate', 'employer', None),
    'business_reg_or_corp': ('사업자등록증 사본 또는 법인등기부등본', 'Business registration copy or corporate register', 'employer', None),
    'reemployment_extension_cert': ('취업기간만료자 취업활동기간 연장확인서(고용노동부 발급)', 'Employment-period extension confirmation (Ministry of Employment and Labor)', 'employer', 'employment_center'),
    'voluntary_departure_pledge': ('자진출국 각서', 'Voluntary departure pledge', 'applicant', None),
    'job_seeking_cert': ('구직등록필증', 'Job-seeking registration certificate', 'applicant', 'employment_center'),
    'income_cert': ('개인 소득금액 증명(소득금액증명원 또는 근로소득원천징수부)', 'Personal income certificate (tax office certificate or withholding ledger)', 'applicant', 'tax_office'),
    'employer_tax_certs': ('고용주 납부내역증명, 납세증명서, 지방세 납세증명서', "Employer's payment record, tax clearance and local tax certificates", 'employer', 'tax_office'),
    'guarantor_original_occupations': ('신원보증서 원본', 'Letter of guarantee (original)', 'employer', None),
    'course_completion_cert': ('수료증명서, 지도교수 및 유학담당자 확인서', 'Course completion certificate; adviser and international-office confirmation', 'educational_institution', 'school'),
    'academic_progress_proof': ('학업을 정상적으로 수행하고 있음을 입증하는 서류(재학증명서, 성적증명서, 출석확인서 등)', 'Proof of normal academic progress (enrollment, transcript, attendance)', 'educational_institution', 'school'),
    'finance_proof': ('재정입증 서류', 'Proof of finances', 'applicant', 'bank'),
    'finance_proof_domestic': ('재정입증 서류(국내 본인계좌 예치금만 인정)', 'Proof of finances (own domestic account balance only)', 'applicant', 'bank'),
    'transcript_or_attendance': ('성적 또는 출석 증명서', 'Transcript or attendance certificate', 'educational_institution', 'school'),
    'korean_ability_proof': ('한국어 능력(영어 능력) 증빙서류', 'Proof of Korean (or English) proficiency', 'applicant', None),
    'pt_confirmation_univ': ('외국인 유학생 시간제취업 확인서', 'University confirmation for part-time work', 'educational_institution', 'school'),
    'pt_compliance_employer': ('외국인 유학생 시간제취업 요건 준수 확인서', "Employer's compliance confirmation for part-time work", 'employer', None),
    'business_reg_employer_id': ('사업자등록증 사본 및 고용주 신분증 사본', "Business registration copy and employer's ID copy", 'employer', None),
    'standard_contract_hourly': ('표준근로계약서 사본(시급·근무내용·시간 포함)', 'Standard labor contract copy (hourly wage, duties, hours)', 'employer', None),
    'passport_and_copy': ('여권 및 사본 1부', 'Passport and one copy', 'applicant', None),
    'enrollment_or_research_cert': ('재학(연구생)증명서', 'Enrollment (research student) certificate', 'educational_institution', 'school'),
    'tuition_payment_cert': ('등록금납입증명서', 'Tuition payment certificate', 'educational_institution', 'school'),
    'univ_cooperation_letter': ('협조요청서', "University's cooperation request", 'educational_institution', 'school'),
    'spouse_or_parent_arc': ('배우자 또는 부모의 외국인등록증', "Spouse's or parent's residence card", 'principal_holder', None),
    'residence_proof_f3': ('체류지 입증서류(임대차계약서, 부동산 등기부등본, 전세계약서, 매매계약서 등 및 숙소제공 확인서)', 'Proof of residence (lease, property register, jeonse/sale contract, accommodation confirmation)', 'applicant', None),
    'occupation_report': ('외국인 직업 신고서', 'Foreigner occupation report form', 'applicant', 'hikorea'),
    'marriage_cert_detail': ('혼인관계증명서(상세)', 'Marriage-relation certificate (detailed)', 'korean_spouse', 'community_center'),
    'resident_reg': ('주민등록등본', 'Resident registration copy', 'korean_spouse', 'community_center'),
    'separation_proof': ('별거사유 입증서류', 'Evidence of the reason for separation', 'applicant', None),
    'divorce_suit_docs': ('이혼소송 관련 서류(소제기 증명원 등)', 'Divorce-suit documents (certificate of filing, etc.)', 'applicant', 'court'),
    'missing_proof': ('실종사실 증명서류', 'Evidence that the spouse is missing', 'applicant', None),
    'child_basic_family_cert': ('자녀 명의 기본증명서·가족관계증명서(자녀가 국민인 경우)', "Child's basic and family-relation certificates (if the child is a Korean national)", 'applicant', 'community_center'),
    'child_care_proof': ('자녀를 계속 양육하고 있음을 입증하는 서류(학비 영수증, 병원비 영수증 등)', 'Proof of continued child-rearing (tuition receipts, medical receipts)', 'applicant', None),
    'death_proof': ('배우자의 사망 입증서류(사망진단서, 사망사실 기재 기본증명서 등)', "Proof of the spouse's death (death certificate, basic certificate)", 'applicant', None),
    'missing_judgment': ('실종사실 증명서류(실종선고심판서)', 'Proof of disappearance (court declaration)', 'applicant', 'court'),
    'divorce_suit_full': ('이혼관련 소송서류(이혼판결문, 조정조서, 화해권고결정문, 협의이혼 사유서 등)', 'Divorce documents (judgment, mediation record, settlement decision, consensual-divorce statement)', 'applicant', 'court'),
    'fault_proof': ('귀책사유 입증자료', "Evidence of the Korean spouse's fault", 'applicant', None),
    'industrial_accident_diag': ('산재로 인한 병원 진단서', 'Medical certificate for the industrial accident', 'applicant', 'hospital'),
    'kcomwel_card': ('근로복지공단 발행 진료계획 심사 결정 통지서(산재보험카드), 후유증상서비스 카드 등', 'KCOMWEL treatment-plan decision notice (industrial accident insurance card) etc.', 'applicant', 'kcomwel'),
    'g1_review_form': ('기타(G-1) 자격 심사확인서(별첨 2 서식)', 'G-1 status review confirmation (Annex 2 form)', 'applicant', 'hikorea'),
    'long_treatment_diag': ('의료기관 발행 진단서 등 장기치료 필요성 입증서류', 'Medical certificate showing need for long-term treatment', 'applicant', 'hospital'),
    'treatment_cost_proof': ('치료 및 체류 비용 조달 능력 입증서류', 'Proof of ability to fund treatment and stay', 'applicant', None),
    'family_relation_accompany': ('가족관계 입증서류(배우자 또는 직계가족 동반 시)', 'Proof of family relationship (if accompanied by spouse or direct family)', 'applicant', None),
    'lawsuit_docs': ('소장 사본, 소송제기 증명원, 법률구조결정서 사본 등 청구권 존재 확인 서류', 'Complaint copy, certificate of filing, legal-aid decision, etc.', 'applicant', 'court'),
    'family_or_guardian_proof': ('가족관계 또는 보호자 입증서류(가족·보호자에 한함)', 'Proof of family/guardian relationship (family or guardians only)', 'applicant', None),
    'wage_arrears_cert': ('노동부 발급 체불금품 확인원, 대한법률구조공단 접수증 등', 'Wage-arrears confirmation (Ministry of Labor), Korea Legal Aid receipt, etc.', 'applicant', 'labor_office'),
    'lawsuit_docs_if_any': ('소송관련 서류(소송 수행 중인 자에 한함)', 'Lawsuit documents (only if litigating)', 'applicant', 'court'),
    'diag_extension_need': ('진단서 등 연장 필요성을 입증하는 서류', 'Medical certificate or other proof of the need to extend', 'applicant', 'hospital'),
    'medical_opinion': ('의료기관 발급 소견서·진단서 등 장기체류 필요성 입증서류', 'Medical opinion/certificate showing need for long-term stay', 'medical_institution', 'hospital'),
    'family_caregiver_proof': ('가족관계 및 간병인 입증서류', 'Proof of family relationship and caregiver status', 'applicant', None),
    'proxy_docs': ('대리 신청 시 위임장·재직증명서', 'Power of attorney and certificate of employment (proxy filings)', 'medical_institution', None),
    'rights_relief_proof': ('소송관련 서류 등 권리구제 입증서류', 'Lawsuit documents or other proof of the remedy sought', 'applicant', None),
    'birth_cert_age_proof': ('출생증명서 등 부모와의 관계 및 미성년 자녀의 나이를 확인할 수 있는 서류', "Birth certificate or other proof of parentage and the child's age", 'applicant', None),
    'job_plan': ('구직활동계획서', 'Job-seeking plan', 'applicant', 'hikorea'),
    'stay_cost_proof_d10': ('체재비 입증서류(연도별 1인 가구 주거급여 기준액 × 체류개월 수 이상 예치된 은행잔고증명서 등)', 'Proof of living funds (bank balance ≥ housing-benefit standard × months of stay)', 'applicant', 'bank'),
    'points_docs': ('점수제 평가를 위해 필요하다고 인정되는 서류', 'Documents needed for the points evaluation', 'applicant', None),
    'intern_employment_cert': ('인턴 재직증명서', 'Internship certificate of employment', 'employer', None),
    'transfer_consent': ('이적동의서(이전 근무처 잔여 근로계약 1개월 이상인 경우)', 'Transfer consent (if 1+ month remains on the previous contract)', 'employer', None),
    'startup_plan': ('기술창업활동계획서', 'Technology start-up activity plan', 'applicant', 'hikorea'),
    'intern_company_docs': ('사업자등록증, 연구시설 및 연구인력 현황자료, 고용보험가입자 명부', 'Business registration, research facility/staff status, employment-insurance roster', 'employer', None),
    'intern_company_eligibility': ('첨단기술인턴(D-10-3) 초청 기업 자격 유지 입증서류', 'Proof that the inviting company still qualifies for D-10-3', 'employer', None),
    'necessity_proof': ('체류기간 연장의 필요성을 소명하는 서류', 'Evidence of the need to extend the stay', 'applicant', None),
    'seafarer_recommendation': ('외국인선원 고용추천서(E-10-1, E-10-3, 한국해운조합) 또는 선원취업활동기간연장 추천서(E-10-2, 수협중앙회)', 'Seafarer employment recommendation (E-10-1/3, KSA) or extension recommendation (E-10-2, NFFC)', 'ship_owner', None),
    'seafarer_recommendation_regional': ('외국인선원 고용추천서(지방해양수산청장 발급)', 'Seafarer employment recommendation (regional maritime office)', 'ship_owner', None),
    'seafarer_contract': ('선원근로계약서', 'Seafarer employment contract', 'ship_owner', None),
    'guarantor_if_expired': ('신원보증서(보증기간 도과 시)', 'Letter of guarantee (if the guarantee period has lapsed)', 'ship_owner', None),
    'pledge': ('각서', 'Written pledge', 'applicant', None),
    'contract_original_copy': ('고용계약서 원본 및 사본', 'Employment contract (original and copy)', 'employer', None),
    'academy_reg_copy': ('학원설립운영등록증 사본(해당자)', 'Private academy registration copy (if applicable)', 'employer', None),
    'timetable': ('강의시간표', 'Teaching timetable', 'employer', None),
    'income_cert_simple': ('소득금액증명', 'Income certificate', 'applicant', 'tax_office'),
    'contract_or_appointment': ('고용계약서 또는 임용예정확인서', 'Employment contract or appointment confirmation', 'employer', None),
    'institution_docs': ('고용기관 설립 관련 서류(사업자등록증, 법인등기사항전부증명서 또는 연구기관 입증서류 등)', 'Institution establishment documents (business registration, corporate register, research-institute proof)', 'employer', None),
    'dispatch_or_employment_cert': ('파견명령서(본사 발행) 또는 재직증명서', 'Dispatch order (head office) or certificate of employment', 'employer', None),
    'employment_recommendation': ('고용추천서 또는 공연추천서', 'Employment or performance recommendation', 'employer', None),
    'contract_or_performance': ('고용계약서(또는 공연계약서)', 'Employment (or performance) contract', 'employer', None),
    'guarantor_e62': ('신원보증서(E-6-2 자격만 징구)', 'Letter of guarantee (E-6-2 only)', 'employer', None),
    'training_schedule': ('연수기관이 작성한 연수일정표', 'Training schedule prepared by the institution', 'educational_institution', None),
    'culture_org_proof': ('사업자등록증 등 문화예술단체 입증서류', 'Business registration or other proof of the arts organization', 'educational_institution', None),
    'training_cert': ('연수증명서', 'Training certificate', 'educational_institution', None),
    'dispatch_or_cert_press': ('재직증명서 또는 파견명령서(본사 발행)', 'Certificate of employment or dispatch order (head office)', 'employer', None),
    'dispatch_or_cert_religion': ('재직증명서 또는 파송명령서(파송단체 발행)', 'Certificate of employment or mission order (sending body)', 'employer', None),
    'e8_extension_request': ('외국인 계절근로자(E-8) 체류기간 연장 추천 신청서', 'E-8 seasonal worker extension recommendation request', 'applicant', 'local_government'),
    'accommodation_confirmation': ('거주/숙소 제공 확인서', 'Accommodation provision confirmation', 'employer', None),
    'labor_contract': ('근로계약서', 'Labor contract', 'employer', None),
    'employer_id': ('고용주 신분증', "Employer's ID", 'employer', None),
    'trafficking_indicator': ('인신매매 피해 식별지표', 'Human-trafficking victim identification indicator', 'local_government', None),
    'e8_extension_recommendation': ('체류기간 만료 계절근로자 체류기간 연장 추천서', 'Extension recommendation for expiring seasonal workers', 'local_government', None),
    'passport_and_arc': ('여권 및 외국인등록증', 'Passport and residence card', 'applicant', None),
    'diplomat_status_docs': ('자국 대사관의 협조 공문, 파견·재직을 증명하는 서류', "Embassy cooperation letter; proof of dispatch/employment", 'principal_holder', None),
    'necessity_proof_press': ('체류기간연장 필요성 소명 서류(취재명령서, 파견증명서, 외신 보도증 사본, 재직증명서 등)', 'Evidence of the need to extend (assignment order, dispatch certificate, press card copy, employment certificate)', 'employer', None),
    'necessity_proof_c4': ('단기취업 관련 체류기간연장 필요성 소명 서류(고용계약서, 사업자등록증 사본 등)', 'Evidence of the need to extend the short-term employment (contract, business registration copy)', 'employer', None),
    'annual_income_docs': ('연간소득 관련 서류(해당자)', 'Annual income documents (if applicable)', 'applicant', None),
    'economic_activity_proof': ('경제활동 입증서류(해당자)', 'Proof of economic activity (if applicable)', 'applicant', None),
    'basic_knowledge_proof': ('기본소양 입증서류(해당자)', 'Proof of basic civic knowledge (if applicable)', 'applicant', None),
    'marriage_family_cert': ('혼인사실이 등재된 가족관계 기록사항에 관한 증명서', 'Family-relation record certificate showing the marriage', 'principal_holder', 'community_center'),
    'basic_docs_points': ('기본서류와 점수제 평가를 위한 서류', 'Basic documents and points-evaluation documents', 'applicant', None),
    'overseas_criminal_record': ('해외범죄경력증명서', 'Overseas criminal record certificate', 'applicant', None),
    'dispatch_order_head': ('파견명령서(외국본사 발행) 또는 외국본사 재직증명서', 'Dispatch order or certificate of employment from the foreign head office', 'employer', None),
    'branch_permit_copy': ('국내지사설치허가서 사본 또는 연락사무소 설치허가서 사본(외국환은행 발행)', 'Branch / liaison office establishment permit copy (foreign-exchange bank)', 'employer', None),
    'operating_funds_proof': ('영업자금도입실적증빙서류(외국환매입증명서, 임대차계약서 등)', 'Proof of operating funds brought in (foreign-exchange purchase certificate, lease, etc.)', 'employer', None),
    'personal_tax_proof': ('개인 납세사실증명 서류(납세사실증명원 원본, 근로소득원천징수영수증 또는 소득금액증명원)', 'Personal tax-payment proof (tax certificate, withholding receipt or income certificate)', 'applicant', 'tax_office'),
    'photo1': ('표준규격사진 1장', 'One standard-size photo', 'applicant', None),
    'corp_docs_d8': ('사업자등록증 사본, 법인등기사항전부증명서, 주주변동상황명세서 원본', 'Business registration copy, corporate register, shareholder-change statement (original)', 'business_entity', None),
    'fdi_company_reg_copy': ('투자기업등록증 사본', 'Foreign-invested company registration copy', 'business_entity', None),
    'dispatch_and_employment_d8': ('주재활동의 경우 파견명령서 및 재직증명서', 'Dispatch order and certificate of employment (for intra-company transferees)', 'business_entity', None),
    'investment_funds_proof': ('투자자금 도입 관련 입증서류', 'Proof of investment funds brought in', 'applicant', None),
    'vat_tax_docs': ('개인 납세사실 증명서류 또는 부가가치세 과세표준 확인증명 관련서류', 'Personal tax proof or VAT tax-base confirmation documents', 'applicant', 'tax_office'),
    'business_performance': ('영업실적(수출입실적 등) 증명서', 'Business performance certificate (import/export, etc.)', 'business_entity', None),
    'premises_proof': ('사업장 존재 입증서류(사무실 임대차계약서, 사업장 사진 등)', 'Proof of business premises (office lease, photos)', 'business_entity', None),
    'capital_use_proof': ('자본금 사용내역 입증서류', 'Proof of how the capital was used', 'business_entity', None),
    'home_country_business_docs': ('해당 업종·분야 사업 경험 관련 국적국 서류(필요시)', 'Home-country documents on business experience in the field (if requested)', 'applicant', None),
    'venture_docs': ('벤처기업확인서 또는 예비벤처기업확인서', 'Venture (or pre-venture) company confirmation', 'business_entity', None),
    'ip_proof': ('지식재산권 등 우수 기술력 입증서류(특허증, 실용신안·디자인·상표·저작권 등록증, 기술성 우수평가서 등)', 'Proof of technology / IP (patents, utility models, designs, trademarks, copyright registrations, technology evaluation)', 'business_entity', None),
    'business_results_proof': ('사업실적관련 입증서류', 'Proof of business results', 'business_entity', None),
    'tax_clearance': ('납세증명서', 'Tax clearance certificate', 'business_entity', 'tax_office'),
    'business_reg_corp_reg': ('사업자등록증 사본, 법인등기사항전부증명서', 'Business registration copy, corporate register', 'business_entity', None),
    'language_program_docs': ('모집요강(연수일정 명시) 또는 연수계획서(어학연수생에 한함)', 'Program guide with schedule or training plan (language trainees only)', 'educational_institution', 'school'),
    'enrollment_proof_generic': ('재학을 입증하는 서류(재학증명서, 교환학생 연장증명서, 연구생 증명서 등)', 'Proof of enrollment (enrollment certificate, exchange-student extension, research-student certificate)', 'educational_institution', 'school'),
    'extension_reason_plan': ('기간연장 사유서 및 인턴·연수 활동 계획서', 'Extension statement and internship/training plan', 'applicant', None),
    'tuition_history': ('학비 납부 내역서(수업료, 기숙사비, 입학금 등)', 'Tuition payment history (fees, dormitory, admission)', 'educational_institution', 'school'),
    'guardian_docs': ('후견보증서, 관계 증명 자료 및 재정능력 입증서류(후견인 변경 시)', 'Guardianship guarantee, relationship proof and financial proof (if the guardian changes)', 'sponsor', None),
    'dorm_admission_cert': ('학교장 명의 기숙사 입소확인서(후견인 면제 대상자)', "Dormitory admission confirmation from the principal (guardian-exempt students)", 'educational_institution', 'school'),
}


def docdef(id_):
    ko, en, role, where = DOCDEFS[id_]
    return {'id': id_, 'name_ko': ko, 'name_en': en, 'default_role': role, 'where_to_obtain': where}


def item(def_id, level='REQUIRED_BASELINE', **kw):
    assert def_id in DOCDEFS, def_id
    assert level in REQ_LEVELS, level
    d = {'ref': def_id, 'requirement_level': level}
    role = kw.pop('role', None)
    if role:
        assert role in ROLES, role
        d['applicant_role'] = role
    for k in ('applies_when_ko', 'applies_when_en', 'does_not_apply_when_ko', 'does_not_apply_when_en', 'anchor', 'alternatives_group', 'alternatives', 'original_or_copy', 'validity_period', 'issuer', 'notes_ko', 'notes_en', 'translation_required', 'apostille_required', 'consular_confirmation_required', 'administrative_information_exemption', 'previous_submission_exemption', 'substitution_allowed', 'substitute_documents', 'submission_channel'):
        if k in kw:
            d[k] = kw.pop(k)
    assert not kw, kw
    return d


RESIDENCE_ALTS = [
    {'ko': '임대차계약서', 'en': 'Lease contract'},
    {'ko': '숙소제공 확인서', 'en': 'Accommodation provision confirmation'},
    {'ko': '체류기간 만료예고 통지우편물', 'en': 'Stay-expiry notice mail'},
    {'ko': '공공요금 납부영수증', 'en': 'Utility bill receipt'},
    {'ko': '기숙사비 영수증', 'en': 'Dormitory fee receipt'},
]


def residence(anchor='체류지 입증서류', level='REQUIRED_BASELINE', alts=RESIDENCE_ALTS, **kw):
    return item('residence_proof', level, anchor=anchor, alternatives_group='residence', alternatives=alts, substitution_allowed=True, **kw)


def base_stay(anchor='신청서(별지 34호 서식), 여권 및 외국인등록증, 수수료', with_fee=True, form='app_form_34'):
    docs = [item(form, anchor=anchor), item('passport', anchor=anchor), item('arc', anchor=anchor)]
    if with_fee:
        docs.append(item('fee', anchor=anchor))
    return docs


GUIDANCE = []


def guidance(code, procedure, *, section, anchor, manual=STAY, state='SUPPORTED', completeness='FULLY_STRUCTURED',
             summary_ko='', summary_en='', docs=None, scenario=None, period_ko=None, period_en=None, fee_ko=None, fee_en=None,
             channel_ko=None, channel_en=None, timing_ko=None, timing_en=None, filer=None, notes_ko=None, notes_en=None,
             conditions_ko=None, conditions_en=None, extra_sources=None, doc_page_window=2, covers=None):
    assert state in PROCEDURE_STATES, state
    for c in covers or []:
        assert re.match(r'^[A-Z]-\d{1,2}(-[0-9A-Z]{1,3})?$', c), c
    assert completeness in COMPLETENESS, completeness
    assert procedure in [p[0] for p in PROCEDURES], procedure
    entry = {
        'target': code, 'procedure': procedure, 'scenario': scenario, 'state': state, 'completeness': completeness,
        'summary_ko': summary_ko, 'summary_en': summary_en,
        'source': {'manual': manual, 'section': section, 'anchor': anchor, 'doc_page_window': doc_page_window},
        'documents': docs or [],
        'period_ko': period_ko, 'period_en': period_en, 'fee_ko': fee_ko, 'fee_en': fee_en,
        'channel_ko': channel_ko, 'channel_en': channel_en, 'timing_ko': timing_ko, 'timing_en': timing_en,
        'filer': filer, 'notes_ko': notes_ko or [], 'notes_en': notes_en or [],
        'conditions_ko': conditions_ko or [], 'conditions_en': conditions_en or [],
        'extra_sources': extra_sources or [],
        'covers': covers or [],
        'review_state': 'SEPT_2026_ORIGINAL_UNREVIEWED',
    }
    GUIDANCE.append(entry)
    return entry


OFFICER_NOTE_KO = '심사 과정에서 추가 서류가 요청되거나 일부 서류가 생략될 수 있습니다.'
OFFICER_NOTE_EN = 'The examining officer may request additional documents or waive some of them.'

# ==========================================================================
# F-1 방문동거 — 체류기간 연장 (stay manual pp. 356-363, 15 scenarios)
# ==========================================================================
guidance('F-1~relative-visit', 'extension', scenario='relative-visit',
         section='1. 국내 친․인척 방문목적으로 입국한 자의 체류기간연장', anchor='국내 친․인척 방문목적으로 입국한 자의 체류기간연장',
         summary_ko='국내 친·인척 방문 목적으로 입국한 F-1 체류자의 연장은 친·인척의 주민등록등본과 신원보증서(20세 이상), 체류지 입증서류를 함께 냅니다.',
         summary_en='F-1 holders who entered to visit relatives in Korea extend with the relative\'s resident registration, a letter of guarantee (age 20+) and proof of residence.',
         docs=base_stay() + [
             item('relative_resident_reg', anchor='국내 친․인척의 주민등록본', role='inviter', administrative_information_exemption=True),
             item('guarantor', 'CONDITIONAL_REQUIRED', anchor='신원보증서(20세 이상인 자에 한함)', applies_when_ko='신청인이 20세 이상인 경우', applies_when_en='Applicant is 20 or older'),
             residence(),
         ])

guidance('F-1~dongpo-first-generation', 'extension', scenario='dongpo-first-generation',
         section='2. 중국동포1세로서 방문동거(F-1) 사증을 소지하고 입국한 자 및 그 존비속과 친척방문으로 입국한 자에 대한 체류기간연장', anchor='중국동포1세로서 방문동거(F-1) 사증을 소지하고 입국한 자',
         summary_ko='중국동포 1세와 그 존비속의 친척방문 연장은 국내 친척의 신원보증이 있어야 하며, 허가일로부터 1년 범위에서 1년씩 연장됩니다.',
         summary_en='First-generation Chinese-Korean compatriots and their lineal relatives need a Korean relative\'s guarantee; the stay is extended one year at a time.',
         period_ko='허가일로부터 1년 범위 내 (1년씩 연장)', period_en='Within 1 year of approval, renewed a year at a time',
         docs=base_stay() + [
             item('family_relation_cert', anchor='가족관계기록사항에 관한 증명서, 기타 신분관계자료'),
             item('hukou', anchor='호구부, 거민증 등 기타 본인신분을 확인'),
             item('guarantor', 'CONDITIONAL_REQUIRED', anchor='신원보증서(20세 이상인 자에 한함)', applies_when_ko='신청인이 20세 이상인 경우', applies_when_en='Applicant is 20 or older'),
             residence(),
         ])

guidance('F-1~diplomat-household', 'extension', scenario='diplomat-household',
         section='3. 주한외국공관원의 비세대동거인 또는 가사보조인', anchor='주한외국공관원의 비세대동거인 또는 가사보조인',
         summary_ko='주한외국공관원의 비세대동거인·가사보조인은 공관원 신분증과 주한대사관 협조공문을 제출하며, 가사보조인은 고용계약서도 필요합니다.',
         summary_en='Non-household cohabitants and domestic helpers of foreign mission staff submit the staff member\'s ID and an embassy cooperation letter; helpers also submit the employment contract.',
         docs=base_stay() + [
             item('diplomat_id', anchor='공관원 신분증', role='principal_holder'),
             item('embassy_letter', anchor='주한대사관 협조공문', role='principal_holder'),
             item('employment_contract', 'CONDITIONAL_REQUIRED', anchor='고용계약서(가사보조인에 한함)', applies_when_ko='가사보조인인 경우', applies_when_en='Domestic helpers only'),
             residence(),
         ])

guidance('F-1-6', 'extension',
         section='5. 혼인단절 결혼이민자 가사정리를 위한 방문동거 체류기간 연장허가', anchor='혼인단절 결혼이민자 가사정리를 위한 방문동거 체류기간 연장허가',
         summary_ko='혼인이 단절되었지만 F-6-3에 해당하지 않는 사람이 재산분할·가사정리를 위해 체류하는 경우로, 매회 6개월 범위에서 연장되며 자격변경일로부터 1년까지만 허가됩니다.',
         summary_en='For people whose marriage ended but who do not qualify for F-6-3 and must stay to settle property or household matters. Extended up to 6 months at a time and only until one year from the status change.',
         period_ko='매회 6개월 범위 내 · 자격변경일로부터 1년까지', period_en='Up to 6 months per extension, at most 1 year from the status change',
         conditions_ko=['혼인단절 전 정상적인 혼인생활 유지 여부와 국내 체류의 불가피성을 심사합니다.', '채권·채무·보증금 반환 소송이 계속되면 1년 경과 후 기타(G-1) 자격으로 소송 종료 시까지 체류허가될 수 있습니다.'],
         conditions_en=['The office reviews whether the marriage was genuine before it ended and whether the stay is unavoidable.', 'If a lawsuit over debts or deposits continues past one year, stay may be allowed under G-1 until it ends.'],
         docs=[item('app_form_34', anchor='신청서(별지 제34호 서식), 여권 및 외국인등록증, 사진 1매, 수수료'), item('passport', anchor='신청서(별지 제34호 서식), 여권 및 외국인등록증, 사진 1매, 수수료'), item('arc', anchor='사진 1매, 수수료'), item('photo', anchor='사진 1매, 수수료'), item('fee', anchor='사진 1매, 수수료'),
               item('guarantor', 'CONDITIONAL_REQUIRED', anchor='신원보증서(신원보증기간이 남아있는 경우 생략 가능)', does_not_apply_when_ko='기존 신원보증기간이 남아 있는 경우 생략 가능', does_not_apply_when_en='May be omitted while an earlier guarantee is still valid', previous_submission_exemption=True),
               item('divorce_marriage_cert', anchor='이혼 사실이 기재된 혼인관계 증명서'),
               item('stay_necessity_proof', anchor='체류 불가피성에 대한 소명자료'),
               item('other_officer_docs', 'MAY_BE_REQUESTED_BY_OFFICER', anchor='기타 심사에 필요하다고 인정되는 서류'),
               residence()])

guidance('F-1~domestic-helper', 'extension', scenario='domestic-helper',
         section='6. 외국인투자자 및 우수전문인력의 가사보조인', anchor='외국인투자자 및 우수전문인력의 가사보조인',
         summary_ko='외국인투자자·우수전문인력의 가사보조인은 고용주의 체류기간 범위에서 최대 1년씩 연장되며, 고용주와 같은 주소에서 생활해야 하고 가사보조 외 취업은 금지됩니다.',
         summary_en='Domestic helpers of foreign investors and top professionals are extended up to one year within the employer\'s stay; they must live at the employer\'s address and may not take other work.',
         period_ko='고용주의 체류기간 범위 내 최대 1년', period_en='Up to 1 year within the employer\'s period of stay',
         conditions_ko=['초청자 1인당 외국인 가사보조인 고용은 1명으로 제한됩니다.', '고용계약 종료 등으로 자격을 상실하면 출국이 원칙입니다.'],
         conditions_en=['Each sponsor may employ one foreign domestic helper.', 'Loss of eligibility (end of contract etc.) normally means departure.'],
         docs=base_stay() + [
             item('domestic_help_contract', anchor='가사보조인 고용계약서', role='employer'),
             item('guarantor', anchor='② 가사보조인 고용계약서  ③ 신원보증서', role='employer'),
             item('employer_cert', anchor='고용주의 재직증명서(신분증명서)', role='employer'),
             item('fdi_report', anchor='외국인투자신고서', role='employer'),
             residence(),
         ])

guidance('F-1-13', 'extension',
         section='7. 고등학교 이하 외국인유학생 동반부모', anchor='고등학교 이하 외국인유학생 동반부모',
         summary_ko='고등학교 이하 외국인 유학생의 동반부모는 자녀의 재학 입증서류와 체류비용 부담 능력을 보여 2년 이내로 연장받습니다.',
         summary_en='Accompanying parents of K-12 international students extend for up to two years with proof of the child\'s enrollment and of funds for living costs.',
         period_ko='체류기간 2년 이내', period_en='Up to 2 years',
         docs=[item('app_form_34', anchor='신청서(별지 제34호 서식), 여권, 외국인등록증, 수수료'), item('passport', anchor='신청서(별지 제34호 서식), 여권, 외국인등록증, 수수료'), item('arc', anchor='신청서(별지 제34호 서식), 여권, 외국인등록증, 수수료'), item('fee', anchor='신청서(별지 제34호 서식), 여권, 외국인등록증, 수수료'),
               item('student_enrollment_proof', anchor='외국인유학생 재학 입증하는 서류', role='educational_institution'),
               item('living_cost_proof', anchor='국내 체류비용 부담 능력 입증서류'),
               residence()])

guidance('F-1~parent-of-talent-investor-student', 'extension', scenario='parent-of-talent-investor-student',
         section='8. 우수인재, 투자자 및 유학생 부모', anchor='우수인재, 투자자 및 유학생 부모',
         summary_ko='우수인재·투자자·유학생의 부모는 신원보증서와 가족관계 입증서류, 체류지 입증서류로 연장을 신청합니다.',
         summary_en='Parents of top talent, investors and university students extend with a letter of guarantee, proof of family relationship and proof of residence.',
         docs=[item('app_form_34', anchor='신청서(별지 제34호 서식), 여권, 외국인등록증, 수수료'), item('passport', anchor='신청서(별지 제34호 서식), 여권, 외국인등록증, 수수료'), item('arc', anchor='신청서(별지 제34호 서식), 여권, 외국인등록증, 수수료'), item('fee', anchor='신청서(별지 제34호 서식), 여권, 외국인등록증, 수수료'),
               item('guarantor', anchor='② 신원보증서'), item('family_relation', anchor='③ 가족관계 입증서류'), residence()])

guidance('F-1-16', 'extension',
         section='9. 난민인정자의 배우자 및 미성년 자녀', anchor='9. 난민인정자의 배우자 및 미성년 자녀',
         summary_ko='난민인정자의 배우자·미성년 자녀(배우자가 있는 미성년 자녀 제외)는 난민인정자의 체류기간 범위에서 최대 2년까지 연장됩니다.',
         summary_en='Spouses and minor children of recognized refugees (excluding married minors) are extended up to two years within the refugee\'s stay.',
         period_ko='난민인정자의 체류기간 범위 내 최대 2년', period_en='Up to 2 years within the refugee\'s period of stay',
         docs=base_stay() + [residence(anchor='교회·난민지원시설· 인권단체·UNHCR 등의 주거확인서', alts=RESIDENCE_ALTS + [{'ko': '교회·난민지원시설·인권단체·UNHCR 등의 주거확인서', 'en': 'Housing confirmation from a church, refugee shelter, human-rights group or UNHCR'}])])

guidance('F-1-28', 'extension',
         section='10. 귀화자의 외국국적 부모 등(F-1-28)에 대한 체류허가 기준', anchor='귀화자의 외국국적 부모 등(F-1-28)에 대한 체류허가 기준',
         state='CONDITIONAL', completeness='PARTIALLY_STRUCTURED',
         summary_ko='귀화자의 외국국적 부모 등(F-1-28)은 「결혼이민자의 부모 등 가족(F-1-5)」 기준을 준용합니다. 아래 F-1-5 안내를 참고하되 준용 여부는 관할 관서에서 확인하세요.',
         summary_en='Foreign-national parents of naturalized Koreans (F-1-28) are handled by applying the F-1-5 rules. Use the F-1-5 guidance below and confirm the application with the office.',
         notes_ko=['매뉴얼은 F-1-5 기준 준용만 명시하며 별도 서류 목록을 두지 않습니다.'], notes_en=['The manual only says the F-1-5 standard applies; it lists no separate documents.'])

guidance('F-1-12', 'extension',
         section='11. 점수제 우수인재(F-2-7)의 배우자 또는 미성년자녀', anchor='11. 점수제 우수인재(F-2-7)의 배우자 또는 미성년자녀',
         summary_ko='점수제 우수인재(F-2-7)의 연간소득이 1인당 국민소득 미만이어서 방문동거(F-1-12)로 체류하는 배우자·미성년 자녀의 연장입니다. 주체류자의 거주(F-2-71) 심사 기준에 따라 심사합니다.',
         summary_en='Extension for spouses and minor children staying as F-1-12 because the F-2-7 principal\'s annual income is below GNI per capita. Reviewed under the F-2-71 dependant criteria.',
         conditions_ko=['주체류자가 F-2-7S(K-STAR)인 경우 자격변경일부터 5년간은 소득요건과 무관하게 국내 출생 자녀에게 F-2-71이 부여됩니다.'],
         conditions_en=['If the principal is F-2-7S (K-STAR), Korea-born children receive F-2-71 for five years from the status change regardless of income.'],
         docs=[item('app_form_34', anchor='신청서(별지 제34호 서식), 여권, 표준규격사진 1매, 수수료'), item('passport', anchor='신청서(별지 제34호 서식), 여권, 표준규격사진 1매, 수수료'), item('photo', anchor='표준규격사진 1매, 수수료'), item('fee', anchor='표준규격사진 1매, 수수료'),
               item('birth_family_proof', anchor='출생증명서, 가족관계 소명 서류 등'),
               item('f27_grant_docs', anchor='점수제 우수인재(F-2-7) 거주자격 부여허가시 제출서류', role='principal_holder'),
               item('principal_passport_arc', anchor='점수제 우수인재(F-2-7)와 그 배우자의 여권 및 외국인등록증 사본', role='principal_holder'),
               item('principal_employment', anchor='점수제 우수인재(F-2-7)의 고용계약서 또는 재직증명서', role='principal_holder'),
               residence(anchor='⑥ 체류지 입증서류'), item('guarantor', anchor='⑦ 신원보증서'),
               item('tb_cert', 'ADDITIONAL_IF_APPLICABLE', anchor='⑧ 결핵확인서(해당자)', applies_when_ko='결핵진단서 제출 대상자인 경우', applies_when_en='If you are subject to the TB certificate rule')])

F15_FAMILY = [
    item('inviter_basic_cert', anchor='초청인의 기본증명서, 가족관계증명서, 혼인관계증명서, 주민등록표(등본)', role='inviter', administrative_information_exemption=True),
    item('inviter_family_cert', anchor='초청인의 기본증명서, 가족관계증명서, 혼인관계증명서, 주민등록표(등본)', role='inviter', administrative_information_exemption=True),
    item('inviter_marriage_cert', anchor='초청인의 기본증명서, 가족관계증명서, 혼인관계증명서, 주민등록표(등본)', role='inviter', administrative_information_exemption=True),
    item('inviter_resident_reg', anchor='초청인의 기본증명서, 가족관계증명서, 혼인관계증명서, 주민등록표(등본)', role='inviter', administrative_information_exemption=True),
    item('child_family_cert', anchor='자녀명의 가족관계증명서(임신한 경우 임신진단서 또는 산모수첩)', role='inviter', notes_ko='자녀가 2명 이상이면 모든 자녀의 가족관계증명서를 제출합니다.', notes_en='Submit one for every child if there are two or more.'),
    item('pregnancy_cert', 'ALTERNATIVE_DOCUMENT', anchor='임신한 경우 임신진단서 또는 산모수첩', applies_when_ko='임신 중인 경우 자녀 가족관계증명서를 대신함', applies_when_en='Replaces the child\'s certificate during pregnancy', role='inviter'),
]

guidance('F-1-5', 'extension', scenario='first-extension-childcare',
         section='12. 자녀양육 지원 등 목적으로 입국한 결혼이민자의 부모 등 가족(F-1-5) — 가. 외국인등록 및 최초 체류기간 연장 (자녀 양육지원)', anchor='자녀 양육지원 목적으로 ‘결혼이민자의 부모 등 가족(F-1-5)’ 사증을 발급받고 입국한 결혼이민자의 본국 가족',
         summary_ko='자녀 양육 지원 목적으로 F-1-5 사증으로 입국한 결혼이민자의 본국 가족이 외국인등록과 함께 처음 연장할 때의 안내입니다. 입국일로부터 1년 범위에서 자녀가 만 10세가 되는 해 3월 말까지 연장됩니다.',
         summary_en='For the marriage migrant\'s family who entered on an F-1-5 visa to help raise a child, registering and extending for the first time. Extended within one year of entry, until the end of March of the year the child turns 10.',
         period_ko='입국일로부터 1년 범위 내, 자녀(마지막 자녀)가 만 10세가 되는 해 3월 말까지 · 한부모·다자녀 가족은 만 13세', period_en='Within 1 year of entry, until end of March of the year the (youngest) child turns 10 (13 for single-parent or multi-child families)',
         conditions_ko=['자녀가 취학연령인데 초청인이 취학의무를 이행하지 않으면 연장이 제한됩니다.'], conditions_en=['If a school-age child is not enrolled, the extension is restricted.'],
         docs=[item('app_form_34', anchor='(기본 서류) 통합신청서, 여권, 체류지 입증서류*, 비취업서약서, 표준규격 사진, 수수료'), item('passport', anchor='(기본 서류) 통합신청서, 여권, 체류지 입증서류*, 비취업서약서, 표준규격 사진, 수수료'),
               residence(anchor='초청인 또는 양육지원 대상인 자녀의 주민등록표(등본)으로 대체 가능', alts=[{'ko': '초청인 또는 양육지원 대상 자녀의 주민등록표(등본)', 'en': 'Inviter\'s or child\'s resident registration copy'}]),
               item('non_employment_pledge', anchor='비취업서약서'), item('photo', anchor='표준규격 사진, 수수료'), item('fee', anchor='표준규격 사진, 수수료')] + F15_FAMILY + [
               item('adoption_cert', 'ADDITIONAL_IF_APPLICABLE', anchor='자녀가 양자의 경우 초청인의 입양관계증명서 추가 제출', applies_when_ko='자녀가 양자인 경우', applies_when_en='If the child is adopted', role='inviter')])

guidance('F-1-5', 'extension', scenario='first-extension-humanitarian',
         section='12. F-1-5 — 가. 외국인등록 및 최초 체류기간 연장 (인도적 사정)', anchor='‘중증질환’ 또는 ‘중증장애’가 있는 결혼이민 가정을 지원하기 위해',
         summary_ko='중증질환·중증장애가 있는 결혼이민 가정을 지원하기 위해 F-1-5 사증으로 입국한 가족의 최초 연장입니다. 입국일로부터 1년 범위에서 인도적 사정이 지속되는 동안 연장됩니다.',
         summary_en='First extension for family members who entered on F-1-5 to support a marriage-migrant household with a severe illness or disability. Extended within one year of entry while the humanitarian situation continues.',
         period_ko='입국일로부터 1년 범위 내, 인도적 사정이 지속될 때까지', period_en='Within 1 year of entry, while the humanitarian situation continues',
         docs=[item('app_form_34', anchor='(기본 서류) 통합신청서, 여권, 체류지 입증서류*, 비취업서약서, 표준규격 사진, 수수료'), item('passport', anchor='(기본 서류) 통합신청서, 여권, 체류지 입증서류*, 비취업서약서, 표준규격 사진, 수수료'),
               residence(anchor='초청인 또는 양육지원 대상인 자녀의 주민등록표(등본)으로 대체 가능', alts=[{'ko': '초청인 또는 양육지원 대상 자녀의 주민등록표(등본)', 'en': 'Inviter\'s or child\'s resident registration copy'}]),
               item('non_employment_pledge', anchor='비취업서약서'), item('photo', anchor='표준규격 사진, 수수료'), item('fee', anchor='표준규격 사진, 수수료')] + F15_FAMILY + [
               item('severe_illness_proof', anchor='(중증 질환･장애 증명서류)', role='inviter', notes_ko='장애인증명서의 종합 장애 정도가 ‘중증장애’ 또는 ‘장애 정도가 심한 장애’이면 중증장애로 인정됩니다.', notes_en='A disability certificate marked “severe” qualifies.')])

guidance('F-1-5', 'extension', scenario='extension-childcare',
         section='12. F-1-5 — 나. 체류기간 연장 (자녀 양육지원)', anchor='자녀 양육지원 목적으로 입국하여 ‘결혼이민자의 부모 등 가족(F-1-5)’ 자격으로 체류 중인 결혼이민자의 본국 가족',
         summary_ko='자녀 양육 지원 목적으로 F-1-5로 체류 중인 가족의 이후 연장입니다. 입국일로부터 3년 범위에서 자녀가 만 10세가 되는 해 3월 말까지 최대 1년씩 연장됩니다.',
         summary_en='Subsequent extensions for F-1-5 family members helping raise a child. Extended up to a year at a time within three years of entry, until the end of March of the year the child turns 10.',
         period_ko='입국일로부터 3년 범위 내, 최대 1년씩 · 자녀가 만 10세(한부모·다자녀 가족은 만 13세)가 되는 해 3월 말까지', period_en='Up to 1 year at a time within 3 years of entry, until end of March of the year the child turns 10 (13 for single-parent / multi-child families)',
         conditions_ko=['자녀가 취학연령인데 초청인이 취학의무를 이행하지 않으면 연장이 제한됩니다.'], conditions_en=['If a school-age child is not enrolled, the extension is restricted.'],
         docs=[item('app_form_34', anchor='(기본 서류) 통합신청서, 여권, 체류지 입증서류*, 표준규격 사진, 수수료'), item('passport', anchor='(기본 서류) 통합신청서, 여권, 체류지 입증서류*, 표준규격 사진, 수수료'),
               residence(anchor='초청인 또는 양육지원 대상인 자녀의 주민등록표(등본)으로 대체 가능', alts=[{'ko': '초청인 또는 양육지원 대상 자녀의 주민등록표(등본)', 'en': 'Inviter\'s or child\'s resident registration copy'}]),
               item('photo', anchor='표준규격 사진, 수수료'), item('fee', anchor='표준규격 사진, 수수료')] + F15_FAMILY + [
               item('full_adoption_cert', 'ADDITIONAL_IF_APPLICABLE', anchor='자녀가 친양자의 경우 초청인의 친양자입양관계증명서 추가 제출', applies_when_ko='자녀가 친양자인 경우', applies_when_en='If the child is a fully adopted child', role='inviter'),
               item('child_enrollment', 'CONDITIONAL_REQUIRED', anchor='(자녀가 취학연령인 경우) 재학증명서', applies_when_ko='자녀가 취학연령인 경우', applies_when_en='If the child is of school age', role='inviter')])

guidance('F-1-5', 'extension', scenario='extension-humanitarian',
         section='12. F-1-5 — 나. 체류기간 연장 (인도적 사정)', anchor='‘입국일로부터 3년’ 범위 내 인도적 사정이 지속될 때까지 최대 1년씩 체류기간 연장허가',
         summary_ko='중증질환·중증장애 가정을 지원하는 F-1-5 가족의 이후 연장입니다. 입국일로부터 3년 범위에서 인도적 사정이 지속되는 동안 최대 1년씩 연장됩니다.',
         summary_en='Subsequent extensions for F-1-5 family members supporting a household with a severe illness or disability: up to a year at a time within three years of entry while the situation continues.',
         period_ko='입국일로부터 3년 범위 내, 인도적 사정이 지속될 때까지 최대 1년씩', period_en='Up to 1 year at a time within 3 years of entry, while the humanitarian situation continues',
         docs=[item('app_form_34', anchor='(기본 서류) 통합신청서, 여권, 체류지 입증서류*, 표준규격 사진, 수수료'), item('passport', anchor='(기본 서류) 통합신청서, 여권, 체류지 입증서류*, 표준규격 사진, 수수료'),
               residence(anchor='초청인 또는 양육지원 대상인 자녀의 주민등록표(등본)으로 대체 가능', alts=[{'ko': '초청인 또는 양육지원 대상 자녀의 주민등록표(등본)', 'en': 'Inviter\'s or child\'s resident registration copy'}]),
               item('photo', anchor='표준규격 사진, 수수료'), item('fee', anchor='표준규격 사진, 수수료')] + F15_FAMILY + [
               item('severe_illness_proof', anchor='(중증 질환･장애 증명서류)', role='inviter')])

guidance('F-1-51', 'extension',
         section='13. 국제 입양 외국인(국내로 입양 아동, F-1-51)', anchor='13. 국제 입양 외국인(국내로 입양 아동, F-1-51)',
         summary_ko='입양 또는 국적취득 절차가 진행 중인 국내 체류 아동은 직전 허가 만료일로부터 1년 이내로 연장되며, 입양 절차 진행 입증서류 1건이 추가로 필요합니다.',
         summary_en='Children in Korea whose adoption or nationality procedure is under way are extended up to one year from the previous expiry, with one document proving the adoption is in progress.',
         period_ko='직전 체류허가 만료일로부터 1년 이내', period_en='Up to 1 year from the previous expiry',
         conditions_ko=['국제입양법상 입양 자격을 유지하고 있어야 합니다.'], conditions_en=['Adoption eligibility under the international adoption law must be maintained.'],
         docs=[item('app_form', anchor='(공통 서류) 신청서, 여권, 수수료, 체류지 입증서류, 가족관계증명 서류'), item('passport', anchor='(공통 서류) 신청서, 여권, 수수료, 체류지 입증서류, 가족관계증명 서류'), item('fee', anchor='(공통 서류) 신청서, 여권, 수수료, 체류지 입증서류, 가족관계증명 서류'),
               residence(anchor='(공통 서류) 신청서, 여권, 수수료, 체류지 입증서류, 가족관계증명 서류'), item('family_relation', anchor='가족관계증명 서류'),
               item('adoption_progress', anchor='입양 절차 진행 입증 서류(아래 서류 중 해당 서류 1건)', alternatives_group='adoption', substitution_allowed=True,
                    alternatives=[{'ko': '협약준수입양증명서 사본(체약국: 출신국 또는 보건복지부 발급)', 'en': 'Copy of the Hague-compliance adoption certificate'}, {'ko': '국내 법원 입양허가 재판 진행 증빙(청구서 또는 접수증)', 'en': 'Proof the Korean court adoption case is pending (petition or receipt)'}])])

guidance('F-1-52', 'extension',
         section='14. 결혼이민자의 전혼관계 출생 자녀(F-1-52)', anchor='14. 결혼이민자의 전혼관계 출생 자녀(F-1-52)',
         summary_ko='한국인 배우자에게 입양되지 않은 결혼이민자의 전혼 자녀는 미성년자는 재학 여부에 따라 2년 또는 1년, 성년자는 고교 졸업 연도 2월 말까지 연장됩니다.',
         summary_en='Children from a marriage migrant\'s previous marriage who were not adopted by the Korean spouse: minors get 2 years if enrolled in public-recognized school (1 year otherwise); adults until the end of February of their high-school graduation year.',
         period_ko='미성년: 재학 시 2년, 미재학 시 1년 · 성년(고교 재학): 1회 최장 1년, 졸업 연도 2월 말까지 · 결혼이민자의 체류기간 초과 불가', period_en='Minors: 2 years if enrolled, else 1 year; adults in high school: up to 1 year until graduation-year February; never beyond the marriage migrant\'s own stay',
         docs=[item('app_form_34', anchor='통합신청서, 여권, 외국인등록증, 수수료'), item('passport', anchor='통합신청서, 여권, 외국인등록증, 수수료'), item('arc', anchor='통합신청서, 여권, 외국인등록증, 수수료'), item('fee', anchor='통합신청서, 여권, 외국인등록증, 수수료'),
               item('spouse_basic_cert', anchor='결혼이민자의 한국인 배우자의 기본증명서, 가족관계증명서, 혼인관계증명서(상세증명서로 발급), 주민등록등본', role='korean_spouse', administrative_information_exemption=True),
               item('spouse_family_cert', anchor='결혼이민자의 한국인 배우자의 기본증명서, 가족관계증명서, 혼인관계증명서(상세증명서로 발급), 주민등록등본', role='korean_spouse', administrative_information_exemption=True),
               item('spouse_marriage_cert_detail', anchor='혼인관계증명서(상세증명서로 발급)', role='korean_spouse', administrative_information_exemption=True),
               item('spouse_resident_reg', anchor='혼인관계증명서(상세증명서로 발급), 주민등록등본', role='korean_spouse', administrative_information_exemption=True),
               item('enrollment_cert', 'CONDITIONAL_REQUIRED', anchor='재학증명서(공교육 인정 대상 학교에 재학 중인 경우)', applies_when_ko='공교육 인정 대상 학교에 재학 중인 경우', applies_when_en='If enrolled in a public-recognized school'),
               residence(anchor='체류지 입증서류(임대차계약서 등)'),
               item('tb_cert', 'CONDITIONAL_REQUIRED', anchor='결핵고위험국가의 경우 결핵진단서(필요시)', applies_when_ko='결핵고위험국가 국민인 경우(필요 시)', applies_when_en='Nationals of TB high-risk countries (when required)')])

guidance('F-1-D', 'extension',
         section='15. 디지털 노마드(워케이션) 비자(F-1-D)', anchor='15. 디지털 노마드(워케이션) 비자(F-1-D)',
         summary_ko='해외 법인과의 근로계약을 유지하며 소득요건을 충족하는 워케이션 체류자는 1회 1년씩 최장 3년까지 연장할 수 있습니다. 비수도권·인구감소지역 체류를 이유로 소득요건을 완화받았다면 실제 거주 여부를 확인합니다.',
         summary_en='Workation (digital nomad) residents who keep a contract with an overseas employer and meet the income test may extend one year at a time up to three years. If the income test was relaxed for staying outside the capital region, actual residence there is checked.',
         period_ko='1회 1년씩 최장 3년', period_en='1 year at a time, up to 3 years',
         conditions_ko=['소득요건 완화 후 허가기간 내 수도권으로 이주하면 수도권 소득기준 충족 또는 비수도권 재이동을 조건으로 6개월만 부여됩니다.'],
         conditions_en=['If you move to the capital region after a relaxed income test, only 6 months are granted unless you meet the capital-region income standard or move back.'],
         docs=[item('app_form_34', anchor='① 신청서(별지 34호 서식), 여권, 표준규격사진 1매, 수수료'), item('passport', anchor='① 신청서(별지 34호 서식), 여권, 표준규격사진 1매, 수수료'), item('photo', anchor='여권, 표준규격사진 1매, 수수료'), item('fee', anchor='여권, 표준규격사진 1매, 수수료'),
               item('employment_cert_1y', anchor='재직증명서(동일 업종에 1년 이상 종사 입증 필요)', role='employer'),
               item('income_proof', anchor='급여명세서, 잔고증명 등 소득 증빙 서류'),
               item('criminal_record_health_ins', anchor='범죄경력증명서, 의료보험 가입 증명서', notes_ko='해외범죄경력증명서 제출기준은 F-1-D 붙임을 따릅니다.', notes_en='Overseas criminal-record rules follow the F-1-D annex.'),
               item('family_relation', 'CONDITIONAL_REQUIRED', anchor='가족관계 입증서류(가족 동반시)', applies_when_ko='가족을 동반하는 경우', applies_when_en='If family members accompany you'),
               item('regional_stay_proof', 'CONDITIONAL_REQUIRED', anchor='(해당 시) 비수도권 및 인구감소(관심)지역에 체류할 예정임을 입증하는 서류', applies_when_ko='비수도권·인구감소(관심)지역 체류를 이유로 소득요건을 완화받는 경우', applies_when_en='If claiming the relaxed income test for staying outside the capital region'),
               item('other_officer_docs', 'MAY_BE_REQUESTED_BY_OFFICER', anchor='기타 출입국관서의 장이 심사에 필요하다고 인정하는 서류')])

# ==========================================================================
# D-2 유학 — 연장 / 시간제취업 / 외국인등록
# ==========================================================================
guidance('D-2', 'extension',
         section='유학(D-2) 체류기간 연장허가 — 다. 제출서류', anchor='수료증명서, 지도교수 및 유학담당자 확인서',
         summary_ko='학위과정(D-2-1~4, D-2-7)은 2년 이내에서 3월 말 또는 9월 말까지, 연구유학(D-2-5)은 1회 1년(총 2년 한도), 교환·방문학생(D-2-6, D-2-8)은 과정 종료일 기준 1월 말·7월 말까지 허가됩니다. 학점미달·가사휴학은 연장이 제한됩니다.',
         summary_en='Degree courses (D-2-1~4, D-2-7) are extended within 2 years to the end of March or September; research (D-2-5) one year at a time (2 years total); exchange/visiting students (D-2-6/8) to end of January or July around the course end. Leave for personal reasons or poor grades restricts extension.',
         period_ko='학위과정: 2년 이내(3월말·9월말) · 연구과정: 1회 1년, 총 2년 · 교환·방문학생: 과정 종료 후 1개월 내(1월말·7월말)', period_en='Degree: within 2 years (end-Mar/Sep) · Research: 1 year each, 2 years total · Exchange/visiting: within 1 month after the course (end-Jan/Jul)',
         conditions_ko=['우수인증대학·인증대학 재학생(평점 2.0 이상)은 재정입증 서류가 생략되고 1회 2년 상한이 적용됩니다(장관 고시 국가 등 제외).', '비자심사강화대학 재학생으로 평점 1.0 이하이면 첫 회 6개월만 연장되고 반복 시 제한됩니다.', '학위과정 재학 최대 기간(전문학사 3년, 학사 6년, 석사 5년, 박사 8년 등)을 넘기면 연장이 제한됩니다.'],
         conditions_en=['Students at certified universities with GPA ≥ 2.0 skip the financial proof and get the 2-year cap (with country exceptions).', 'Students at visa-review-strengthened universities with GPA ≤ 1.0 get one 6-month extension, then restrictions.', 'Extensions stop at the maximum course period (e.g. associate 3 y, bachelor 6 y, master 5 y, doctorate 8 y).'],
         docs=[item('app_form', anchor='신청서, 여권, 외국인등록증, 수수료'), item('passport', anchor='신청서, 여권, 외국인등록증, 수수료'), item('arc', anchor='신청서, 여권, 외국인등록증, 수수료'), item('fee', anchor='신청서, 여권, 외국인등록증, 수수료'),
               item('course_completion_cert', anchor='수료증명서, 지도교수 및 유학담당자 확인서', role='educational_institution'),
               item('academic_progress_proof', anchor='학업을 정상적으로 수행하고 있음을 입증하는 서류', role='educational_institution', alternatives_group='progress', substitution_allowed=True, alternatives=[{'ko': '재학증명서', 'en': 'Enrollment certificate'}, {'ko': '성적증명서', 'en': 'Transcript'}, {'ko': '출석확인서', 'en': 'Attendance confirmation'}]),
               item('finance_proof', 'CONDITIONAL_REQUIRED', anchor='재정입증 서류', does_not_apply_when_ko='우수인증대학·인증대학 학위과정 재학생으로 평점 2.0 이상인 경우 생략(장관 고시 국가 등 제외)', does_not_apply_when_en='Waived for certified-university degree students with GPA ≥ 2.0 (country exceptions apply)'),
               residence()])

guidance('D-2', 'part_time_work',
         section='시간제취업 활동 허가 — 마. 신청서류', anchor='외국인 유학생 시간제 취업 확인서',
         summary_ko='시간제취업은 D-2-1~4, D-2-6, D-2-7 유학생이 대상이며, 방문학생(D-2-8)과 어학연수생(D-4-1, D-4-7)은 자격변경일(또는 입국일)로부터 6개월이 지나야 합니다. 허용시간은 한국어능력과 과정에 따라 주중 10~35시간이고, 고용주가 바뀌면 다시 허가받아야 합니다. 수수료는 면제됩니다.',
         summary_en='Part-time work is for D-2-1~4, D-2-6 and D-2-7 students; visiting students (D-2-8) and language trainees (D-4-1/7) must wait six months after the status change or entry. Weekly hours range from 10 to 35 by Korean level and course; a new employer needs a new permit. No fee.',
         fee_ko='수수료 면제', fee_en='No fee', channel_ko='온라인 또는 방문 신청 (허가 스티커 부착 또는 온라인 허가서 출력)', channel_en='Online or in person (sticker or printed online permit)',
         conditions_ko=['허용시간: 전문학사·학사 1~2학년 주중 10시간(한국어 요건 충족 시 25시간), 학사 3~4학년 10/25시간, 석·박사 15/30시간, 인증대학·성적·한국어 우수자는 최대 30~35시간, 주말·방학은 제한 없음.', '제조업·건설업·선원 업종, 전문분야(E-1~E-7), 특수형태근로(배달·대리운전 등), 파견·도급, 원거리 근무는 제한됩니다(제조업은 TOPIK 4급 이상이면 예외).', '직전 학기 평점 2.0 미만이거나 최근 3개월 내 무허가·조건위반 처벌 이력이 있으면 제한됩니다.', '유학생(D-2)은 체류기간 내 최장 1년, 동시 2곳까지 허가됩니다.'],
         conditions_en=['Hours: associate/1st–2nd-year bachelor 10 h weekdays (25 h with the Korean requirement), 3rd–4th year 10/25 h, graduate 15/30 h, up to 30–35 h for certified-university / high-achieving students; weekends and vacations unlimited.', 'Manufacturing, construction, seafaring, professional fields (E-1~E-7), platform/delivery work, dispatch/subcontracting and remote work are restricted (manufacturing allowed with TOPIK 4+).', 'Restricted if last-semester GPA < 2.0 or if penalized for unpermitted work in the past 3 months.', 'D-2 students: up to 1 year within the stay, at most 2 workplaces at once.'],
         docs=[item('app_form', anchor='신청서, 여권, 외국인등록증 ※ 수수료 면제'), item('passport', anchor='신청서, 여권, 외국인등록증 ※ 수수료 면제'), item('arc', anchor='신청서, 여권, 외국인등록증 ※ 수수료 면제'),
               item('transcript_or_attendance', 'ADMIN_INFO_CHECKABLE', anchor='성적 또는 출석 증명서(유학생정보시스템으로 확인이 될 경우 생략)', administrative_information_exemption=True, role='educational_institution'),
               item('korean_ability_proof', anchor='한국어 능력(영어 능력) 증빙서류'),
               item('pt_confirmation_univ', anchor='외국인 유학생 시간제 취업 확인서', role='educational_institution'),
               item('pt_compliance_employer', 'CONDITIONAL_REQUIRED', anchor='사업자등록증에 제조업, 건설업이 포함된 경우에 한함', applies_when_ko='사업자등록증에 제조업·건설업이 포함된 경우', applies_when_en='If the business registration includes manufacturing or construction', role='employer'),
               item('business_reg_employer_id', anchor='사업자등록증 사본 및 고용주 신분증 사본', role='employer'),
               item('standard_contract_hourly', anchor='표준근로계약서 사본(시급 및 근무내용, 시간이 포함되어 있을 것)', role='employer')])

guidance('D-2', 'registration',
         section='유학(D-2) 외국인등록 — 1. 제출서류', anchor='재학(연구생)증명서',
         summary_ko='유학생 외국인등록은 신청서·여권·사진·수수료와 재학(연구생)증명서, 체류지 입증서류를 냅니다. 재정능력 입증서류는 필요 없고, 등록과 함께 연장을 신청하면 연장 수수료가 면제됩니다.',
         summary_en='Student registration needs the form, passport, photo, fee, an enrollment (research-student) certificate and proof of residence. No financial proof is required, and the extension fee is waived when filed together with registration.',
         fee_ko='등록 수수료 납부 · 등록과 동시 연장 신청 시 연장 수수료 면제', fee_en='Registration fee; extension fee waived when filed together',
         docs=[item('app_form', anchor='신청서, 여권 및 사본 1부, 표준규격사진 1매'), item('passport_and_copy', anchor='여권 및 사본 1부, 표준규격사진 1매'), item('photo', anchor='여권 및 사본 1부, 표준규격사진 1매'), item('fee', anchor='외국인등록 시, 체류기간 연장허가를 동시에 신청하는 경우에 한하여 연장 수수료 면제'),
               item('enrollment_or_research_cert', anchor='재학(연구생)증명서', role='educational_institution', substitution_allowed=True, alternatives_group='enrollment',
                    alternatives=[{'ko': '(인증대학 이상) 등록금납입증명서', 'en': 'Certified university: tuition payment certificate'}, {'ko': '(일반대학 이하, 개별접수) 협조요청서 및 등록금납입증명서', 'en': 'Other universities, individual filing: cooperation request + tuition payment certificate'}, {'ko': '(일반대학 이하, 단체접수) 등록금납입증명서', 'en': 'Other universities, group filing: tuition payment certificate'}]),
               residence(anchor='재정능력 입증서류 제출 불요')])

guidance('D-2', 'registration_info_report',
         section='유학(D-2) 외국인등록 — 2. 등록사항 변경신고', anchor='학교 변경 (명칭 변경 포함)',
         summary_ko='성명·성별·생년월일·국적, 여권정보, 학교(명칭 포함)가 바뀌면 15일 이내에 관할 관서 또는 온라인으로 신고합니다. 학교 변경은 동급 학위과정(D-2-1~4)에 한해 제한적으로 허용됩니다.',
         summary_en='Report changes of name, sex, birth date, nationality, passport details or school (including renaming) within 15 days at the office or online. Changing school is allowed only within the same degree level (D-2-1~4) and with conditions.',
         timing_ko='변경일로부터 15일 이내', timing_en='Within 15 days of the change', channel_ko='관할 청(사무소·출장소) 또는 온라인', channel_en='Local office or online',
         docs=[item('app_form', anchor='신청서, 여권, 외국인등록증'), item('passport', anchor='신청서, 여권, 외국인등록증'), item('arc', anchor='신청서, 여권, 외국인등록증'),
               item('enrollment_cert', 'CONDITIONAL_REQUIRED', anchor='(학교변경 시) 변경된 학교의 재학증명서 및 전 학교 제적증명서', applies_when_ko='학교를 변경하는 경우(전 학교 제적증명서 포함)', applies_when_en='If changing school (plus the previous school\'s withdrawal certificate)', role='educational_institution')])

# ==========================================================================
# E-9 비전문취업 — 연장 / 근무처 변경
# ==========================================================================
E9_BASE = [item('app_form_34', anchor='신청서(별지 34호 서식), 여권 및 외국인등록증, 수수료'), item('passport', anchor='신청서(별지 34호 서식), 여권 및 외국인등록증, 수수료'), item('arc', anchor='신청서(별지 34호 서식), 여권 및 외국인등록증, 수수료'), item('fee', anchor='신청서(별지 34호 서식), 여권 및 외국인등록증, 수수료')]
guidance('E-9', 'extension',
         section='비전문취업(E-9) 체류기간 연장허가 — 1. 제출 서류', anchor='② 고용허가서 사본 ③ 표준근로계약서 사본 ④ 사업자등록증 사본',
         summary_ko='고용허가제 근로자의 연장은 고용허가서·표준근로계약서·사업자등록증 사본과 체류지 입증서류를 냅니다. 입국 후 3년 만료 뒤 재고용으로 최대 1년 10개월을 추가 연장할 때는 고용노동부의 취업활동기간 연장확인서가 필요합니다. 업종(제조·건설·농축산·어업·서비스 등)에 관계없이 같은 서류 목록이 적용됩니다.',
         summary_en='EPS workers extend with copies of the employment permit, standard labor contract and business registration plus proof of residence. For the extra 1 year 10 months after the first 3 years, the Ministry of Employment and Labor\'s extension confirmation is required. The same list applies to every industry.',
         period_ko='최초 입국일로부터 3년 · 재고용 시 최대 4년 10개월', period_en='3 years from first entry; up to 4 years 10 months with re-employment',
         docs=E9_BASE + [item('employment_permit_copy', anchor='고용허가서 사본', role='employer'), item('standard_contract_copy', anchor='표준근로계약서 사본', role='employer'), item('business_reg_copy', anchor='사업자등록증 사본', role='employer'),
                         item('reemployment_extension_cert', 'CONDITIONAL_REQUIRED', anchor='취업기간만료자 취업활동기간 연장확인서(고용노동부 발급)', applies_when_ko='입국 후 3년 만료 후 재고용에 따라 최대 1년 10개월 추가 연장하는 경우', applies_when_en='When extending up to 1 year 10 months by re-employment after the first 3 years', role='employer'),
                         residence()])

guidance('E-9', 'extension', scenario='job-seeker-special',
         section='비전문취업(E-9) 체류기간 연장허가 — 3. 구직신청자 특례', anchor='구직등록 유효기간(구직신청일로부터 3개월) 이전에 체류기간만료일이 도래하는 자',
         summary_ko='구직등록 유효기간(신청일로부터 3개월) 안에 체류기간이 끝나고 사업장 변경 횟수가 남은 근로자는 구직등록필증 발급일로부터 90일 범위에서 수수료 없이 연장됩니다.',
         summary_en='Workers whose stay expires within the 3-month job-seeking registration period and who still have workplace changes left are extended without fee for up to 90 days from the registration certificate date.',
         period_ko='구직등록필증 발급일로부터 90일 범위 내', period_en='Up to 90 days from the job-seeking registration certificate', fee_ko='수수료 없음', fee_en='No fee',
         docs=[item('app_form_34', anchor='신청서(별지 34호서식), 여권 및 외국인등록증, 수수료 없음'), item('passport', anchor='신청서(별지 34호서식), 여권 및 외국인등록증, 수수료 없음'), item('arc', anchor='신청서(별지 34호서식), 여권 및 외국인등록증, 수수료 없음'),
               item('voluntary_departure_pledge', anchor='자진출국 각서'), item('job_seeking_cert', anchor='구직등록필증'),
               residence(level='CONDITIONAL_REQUIRED', does_not_apply_when_ko='체류지 입증서류 제출이 곤란하면 생략 가능(체류지 허위기재 시 처벌)', does_not_apply_when_en='May be omitted if hard to obtain; false address information is punishable')])

guidance('E-9', 'workplace_change',
         section='비전문취업(E-9) 근무처의 변경․추가 — 마. 제출 서류', anchor='건설현장에 대한 외국인력 현황표',
         summary_ko='고용허가제 근로자의 사업장 변경은 고용노동부 고용센터의 사업장변경 절차를 거친 뒤 출입국에 신고하며, 입국 후 3년 내 원칙 3회(재고용 기간 2회)로 제한됩니다. 휴·폐업 등 근로자 책임이 아닌 사유는 횟수에 포함되지 않습니다.',
         summary_en='EPS workers change workplace through the employment center first and then report to immigration; normally 3 changes within the first 3 years (2 during re-employment). Changes caused by closure or other reasons not attributable to the worker do not count.',
         timing_ko='근로계약 종료 후 1개월 이내 고용센터에 사업장 변경 신청, 신청일로부터 3개월 이내 근무처 변경', timing_en='Apply at the employment center within 1 month after the contract ends and change workplace within 3 months of applying',
         docs=[item('app_form_34', anchor='신청서(별지 34호서식), 여권, 외국인등록증, 수수료, 체류지 입증서류'), item('passport', anchor='신청서(별지 34호서식), 여권, 외국인등록증, 수수료, 체류지 입증서류'), item('arc', anchor='신청서(별지 34호서식), 여권, 외국인등록증, 수수료, 체류지 입증서류'), item('fee', anchor='신청서(별지 34호서식), 여권, 외국인등록증, 수수료, 체류지 입증서류'), residence(anchor='수수료, 체류지 입증서류'),
               item('employment_permit_copy', anchor='② 고용허가서 사본 ③ 표준근로계약서 사본', role='employer'), item('standard_contract_copy', anchor='② 고용허가서 사본 ③ 표준근로계약서 사본', role='employer'), item('business_reg', anchor='‘사업자등록증’ 등 사업장 관련 입증서류', role='employer'),
               item('business_reg', 'CONDITIONAL_REQUIRED', anchor='건설현장에 대한 외국인력 현황표', applies_when_ko='건설업체인 경우: 책임건설업체(원도급업체)가 작성한 “건설현장에 대한 외국인력 현황표”', applies_when_en='Construction: the lead contractor\'s “foreign workforce status table for the site”', role='business_entity')])

# ==========================================================================
# E-7 특정활동 — 연장
# ==========================================================================
guidance('E-7', 'extension',
         section='특정활동(E-7) 체류기간 연장허가 — 1. 제출 서류 및 확인사항', anchor='개인 소득금액 증명(필수)',
         summary_ko='E-7 연장은 고용계약서, 개인 소득금액 증명(필수), 사업자등록증 또는 법인등기부등본, 체류지 입증서류와 고용주의 납세 관련 증명을 냅니다. 신원보증서 원본은 매뉴얼이 정한 일부 직종(기계공학기술자, 주방장·조리사, 호텔접수사무원, 숙련기능 점수제 종사자 등)에만 요구됩니다. 세부약호(E-7-1~4, S, Y, T, 91)에 관계없이 같은 기본 목록이 적용되며 협정 대상자(CEPA 독립전문가, 한·러 협정)는 별도 특례가 있습니다.',
         summary_en='E-7 extensions take the employment contract, personal income proof (mandatory), business registration or corporate register, proof of residence and the employer\'s tax certificates. An original letter of guarantee is required only for occupations the manual lists (mechanical engineers, chefs/cooks, hotel receptionists, skilled points-system workers, etc.). The same base list applies to every subcode (E-7-1~4, S, Y, T, 91); treaty cases (CEPA independent professionals, Korea–Russia agreement) have separate rules.',
         docs=[item('app_form_34', anchor='① 신청서(별지 34호 서식), 여권 및 외국인등록증, 수수료 ② 고용계약서'), item('passport', anchor='① 신청서(별지 34호 서식), 여권 및 외국인등록증, 수수료 ② 고용계약서'), item('arc', anchor='① 신청서(별지 34호 서식), 여권 및 외국인등록증, 수수료 ② 고용계약서'), item('fee', anchor='① 신청서(별지 34호 서식), 여권 및 외국인등록증, 수수료 ② 고용계약서'),
               item('employment_contract', anchor='수수료 ② 고용계약서', role='employer'),
               item('income_cert', anchor='개인 소득금액 증명(필수)', alternatives_group='income', substitution_allowed=True, alternatives=[{'ko': '소득금액증명원(세무서 발급)', 'en': 'Income certificate (tax office)'}, {'ko': '근로소득원천징수부(소속회사 발급)', 'en': 'Withholding ledger (employer)'}]),
               item('business_reg_or_corp', anchor='사업자등록증 사본 또는 법인등기부등본', role='employer'),
               item('guarantor_original_occupations', 'CONDITIONAL_REQUIRED', anchor='신원보증서 원본(아래 직종에 한해 징구)', applies_when_ko='기계공학기술자(2351), 제도사(2395), 해외 온라인상품판매원, 디자이너(285), 판매사무원(31215), 주방장 및 조리사(441), 고객상담사무원(3991), 호텔접수사무원(3922), 의료코디네이터, 양식기술자(6301), 조선용접공(7430), 숙련기능 점수제 종사자 등 매뉴얼이 정한 직종', applies_when_en='Only for occupations the manual lists (mechanical engineers 2351, drafters 2395, overseas online sellers, designers 285, sales clerks 31215, chefs and cooks 441, customer-service clerks 3991, hotel receptionists 3922, medical coordinators, aquaculture technicians 6301, ship welders 7430, skilled points-system workers, etc.)', role='employer'),
               residence(),
               item('employer_tax_certs', anchor='고용주 납부내역증명, 납세증명서, 지방세 납세증명서', role='employer', administrative_information_exemption=True)])

guidance('E-7-91', 'extension',
         section='특정활동(E-7) 체류기간 연장허가 — 2. 협정상 특례 (한·인도 CEPA 독립전문가)', anchor='한·인도 포괄적경제동반자협정(CEPA) : 독립전문가(IP)',
         state='GENERALLY_NOT_PERMITTED', completeness='SOURCE_ONLY',
         summary_ko='CEPA 독립전문가(IP)는 계약기간을 체류기간으로 하는 최대 1년 단수사증발급인정서로 입국하며, 체류기간연장·근무처변경·자격변경·자격외활동이 제한됩니다. 사고·질병 등 인도적 사유가 있을 때만 일반 체류지침에 따라 처리됩니다.',
         summary_en='CEPA independent professionals enter on a single-entry confirmation for up to one year matching the contract; extension, workplace change, status change and outside-status activities are restricted. Only humanitarian cases (accident, illness) are handled under the general rules.')

# ==========================================================================
# F-2 거주 — 연장 (유형별)
# ==========================================================================
guidance('F-2-2', 'extension', section='거주(F-2) 체류기간연장 — 국민의 미성년자녀(F-2-2)', anchor='국민의 미성년자녀',
         summary_ko='국민의 미성년 자녀(F-2-2)는 신청서·여권·외국인등록증·수수료와 가족관계 입증서류로 연장합니다.', summary_en='Minor children of Korean nationals (F-2-2) extend with the form, passport, residence card, fee and proof of family relationship.',
         docs=[item('app_form_34', anchor='①신청서(별지 34호 서식), 여권 및 외국인등록증, 수수료'), item('passport', anchor='①신청서(별지 34호 서식), 여권 및 외국인등록증, 수수료'), item('arc', anchor='①신청서(별지 34호 서식), 여권 및 외국인등록증, 수수료'), item('fee', anchor='①신청서(별지 34호 서식), 여권 및 외국인등록증, 수수료'), item('family_relation', anchor='②가족관계 입증 서류')])
guidance('F-2-3', 'extension', section='거주(F-2) 체류기간연장 — 영주권자의 배우자 및 미성년자녀(F-2-3)', anchor='혼인사실이 등재된 가족관계 기록사항에 관한 증명서',
         summary_ko='영주권자의 배우자·미성년 자녀(F-2-3)는 혼인사실이 등재된 가족관계 기록사항 증명서와 체류지 입증서류를 냅니다.', summary_en='Spouses and minor children of permanent residents (F-2-3) submit the family-relation record showing the marriage and proof of residence.',
         docs=[item('app_form_34', anchor='①신청서(별지 34호 서식), 여권 및 외국인등록증, 수수료'), item('passport', anchor='①신청서(별지 34호 서식), 여권 및 외국인등록증, 수수료'), item('arc', anchor='①신청서(별지 34호 서식), 여권 및 외국인등록증, 수수료'), item('fee', anchor='①신청서(별지 34호 서식), 여권 및 외국인등록증, 수수료'),
               item('marriage_family_cert', anchor='②혼인사실이 등재된 가족관계 기록사항에 관한 증명서', role='principal_holder'), residence(anchor='③체류지 입증서류(임대차계약서 등)')])
guidance('F-2-4', 'extension', section='거주(F-2) 체류기간연장 — 난민인정자(F-2-4)', anchor='난민인정자',
         summary_ko='난민인정자(F-2-4)는 신청서·여권·외국인등록증·수수료와 체류지 입증서류로 연장합니다.', summary_en='Recognized refugees (F-2-4) extend with the form, passport, residence card, fee and proof of residence.',
         docs=[item('app_form_34', anchor='①신청서(별지 34호 서식), 여권 및 외국인등록증, 수수료'), item('passport', anchor='①신청서(별지 34호 서식), 여권 및 외국인등록증, 수수료'), item('arc', anchor='①신청서(별지 34호 서식), 여권 및 외국인등록증, 수수료'), item('fee', anchor='①신청서(별지 34호 서식), 여권 및 외국인등록증, 수수료'), residence()])
guidance('F-2-99', 'extension', section='거주(F-2) 체류기간연장 — 기타 장기체류자(F-2-99)', anchor='기타 장기체류자',
         summary_ko='기타 장기체류자(F-2-99)는 신원보증서와 해당자에 한해 연간소득·경제활동·기본소양 입증서류를 추가로 냅니다. 2019-10-01 폐지된 숙련생산기능 거주자격 소지자는 F-2-99로 직권 정정되어 이 기준으로 연장합니다.', summary_en='Other long-term residents (F-2-99) add a letter of guarantee and, where applicable, proof of annual income, economic activity and basic civic knowledge. Former skilled-production residents (abolished 2019-10-01) were converted to F-2-99 and use this rule.',
         docs=[item('app_form_34', anchor='①신청서(별지 34호 서식), 여권 및 외국인등록증, 수수료'), item('passport', anchor='①신청서(별지 34호 서식), 여권 및 외국인등록증, 수수료'), item('arc', anchor='①신청서(별지 34호 서식), 여권 및 외국인등록증, 수수료'), item('fee', anchor='①신청서(별지 34호 서식), 여권 및 외국인등록증, 수수료'),
               item('guarantor', anchor='②신원보증서'), item('annual_income_docs', 'ADDITIONAL_IF_APPLICABLE', anchor='연간소득 관련 서류(해당자)', applies_when_ko='해당자', applies_when_en='If applicable'), item('economic_activity_proof', 'ADDITIONAL_IF_APPLICABLE', anchor='④경제활동 입증서류(해당자)', applies_when_ko='해당자', applies_when_en='If applicable'), item('basic_knowledge_proof', 'ADDITIONAL_IF_APPLICABLE', anchor='⑤기본소양 입증서류(해당자)', applies_when_ko='해당자', applies_when_en='If applicable'),
               residence(anchor='⑥체류지 입증서류'), item('other_officer_docs', 'MAY_BE_REQUESTED_BY_OFFICER', anchor='⑦기타 심사에 필요하다고 인정하는 서류')])
guidance('F-2-7', 'extension', completeness='PARTIALLY_STRUCTURED', covers=['F-2-7S'],
         section='3. 점수제에 의한 우수인재 체류기간연장', anchor='점수제에 의한 우수인재 체류기간연장',
         summary_ko='점수제 우수인재(F-2-7, F-2-7S)는 결격사유가 없고 합산 80점 이상이어야 하며, 합산점수 또는 연간소득점수 중 유리한 쪽으로 1~5년의 체류기간을 받습니다(130점 이상 또는 소득 50점 이상 5년, 120~129점 3년, 110~119점 2년, 80~109점 1년). 80점 미만이라도 최저임금 이상 취업 중이면 1년 유예, 실직·최저임금 이하 소득이면 각서 후 연장하되 1년 이상 지속 시 불허될 수 있습니다. 제출서류는 기본서류와 점수제 평가 서류이며, 자격 취득 후 6개월 이상 연속 해외체류가 없으면 해외범죄경력증명서는 생략됩니다.',
         summary_en='Points-system residents (F-2-7, F-2-7S) need no disqualifying grounds and 80+ points; the stay is 1–5 years by whichever is better of total points or income points (130+ points or income 50+ = 5 y, 120–129 = 3 y, 110–119 = 2 y, 80–109 = 1 y). Below 80 points a one-year grace is given if employed at minimum wage or above; unemployment or sub-minimum income requires a pledge and may be refused after a year. Documents are the basic set plus points evidence; the overseas criminal record is waived if you have not stayed abroad 6+ consecutive months since obtaining the status.',
         period_ko='점수에 따라 1·2·3·5년 · 유예 1년', period_en='1, 2, 3 or 5 years by points; 1-year grace',
         conditions_ko=['주체류자의 연장이 불허되면 배우자·미성년 자녀(F-2-71, F-3-18)도 동시에 불허됩니다.', '거주(F-2) 변경·연장 예정자 중 국내법 위반이 확인되면 준법시민교육 대상이 됩니다.', '실직·최저임금 이하 소득이면 구직(D-10)으로 변경(최대 1년)할 수 있습니다.'],
         conditions_en=['If the principal is refused, dependants (F-2-71, F-3-18) are refused at the same time.', 'Applicants with confirmed legal violations must take the law-abiding citizen course.', 'Unemployed or sub-minimum-income holders may switch to D-10 (up to 1 year).'],
         docs=[item('basic_docs_points', 'SOURCE_MENTIONS_BUT_NOT_STRUCTURED', anchor='기본서류와 점수제 평가를 위한 서류 제출', notes_ko='매뉴얼은 "기본서류와 점수제 평가를 위한 서류"라고만 적고 개별 서류를 나열하지 않습니다.', notes_en='The manual says "basic documents and points-evaluation documents" without an itemised list.'),
               item('overseas_criminal_record', 'PREVIOUSLY_SUBMITTED_MAY_BE_OMITTED', anchor='6개월 이상 연속하여 해외에서 체류하지 않은 경우 해외범죄경력증명서는 생략 가능', does_not_apply_when_ko='점수제 거주 자격 취득 후 6개월 이상 연속 해외체류가 없는 경우 생략', does_not_apply_when_en='Waived if not abroad 6+ consecutive months since obtaining the status')])
guidance('F-2-71', 'extension', completeness='PARTIALLY_STRUCTURED',
         section='3. 점수제에 의한 우수인재 체류기간연장 — 2) 배우자 및 미성년 자녀(F-2-71)', anchor='점수제 우수인재의 배우자 및 미성년 자녀로서 거주자(F-2-71)',
         summary_ko='F-2-7 우수인재의 배우자·미성년 자녀(F-2-71)는 본인이 합법체류 중이고 결격사유·취업제한 직종 취업 사실이 없어야 하며, 주체류자가 80점 이상이고 연간소득이 전년도 1인당 GNI 이상이어야 합니다. 서류는 기본서류와 점수제 평가 서류입니다.',
         summary_en='Dependants of F-2-7 holders (F-2-71) must be lawfully staying with no disqualifying grounds or restricted-field employment, and the principal must have 80+ points and annual income at or above the previous year\'s GNI per capita. Documents are the basic set plus points evidence.',
         docs=[item('basic_docs_points', 'SOURCE_MENTIONS_BUT_NOT_STRUCTURED', anchor='기본서류와 점수제 평가를 위한 서류 제출'), item('overseas_criminal_record', 'PREVIOUSLY_SUBMITTED_MAY_BE_OMITTED', anchor='6개월 이상 연속하여 해외에서 체류하지 않은 경우 해외범죄경력증명서는 생략 가능')])

# ==========================================================================
# F-3 동반 — 연장
# ==========================================================================
guidance('F-3', 'extension', section='동반(F-3) 체류기간 연장허가', anchor='③ 배우자 또는 부모의 외국인등록증',
         summary_ko='동반(F-3) 연장의 필수서류는 신청서·여권·외국인등록증·수수료와 체류지 입증서류이며, 추가서류로 배우자 또는 부모(주체류자)의 외국인등록증을 냅니다. 점수제 우수인재의 가족(F-3-18)은 F-2-7 연장 규정에 따라 심사됩니다.',
         summary_en='F-3 extensions require the form, passport, residence card, fee and proof of residence, plus the principal holder\'s (spouse\'s or parent\'s) residence card. Families of points-system residents (F-3-18) are reviewed under the F-2-7 rule.',
         docs=base_stay() + [item('residence_proof_f3', anchor='체류지 입증서류(임대차계약서, 부동산 등기부등본, 전세계약서, 매매계약서 등 및 숙소제공 확인서)', alternatives_group='residence', substitution_allowed=True, alternatives=[{'ko': '임대차계약서', 'en': 'Lease contract'}, {'ko': '부동산 등기부등본', 'en': 'Property register'}, {'ko': '전세계약서', 'en': 'Jeonse contract'}, {'ko': '매매계약서', 'en': 'Sale contract'}, {'ko': '숙소제공 확인서', 'en': 'Accommodation confirmation'}]),
                             item('spouse_or_parent_arc', 'ADDITIONAL_IF_APPLICABLE', anchor='③ 배우자 또는 부모의 외국인등록증', role='principal_holder', applies_when_ko='추가서류', applies_when_en='Additional document')])

# ==========================================================================
# F-6 결혼이민 — 연장 (F-6-1 / F-6-2 / F-6-3)
# ==========================================================================
F6_BASE_FIRST = [item('app_form_34', anchor='신청서(별지 제 34호 서식), 여권, 표준규격사진 1매, 수수료'), item('passport', anchor='신청서(별지 제 34호 서식), 여권, 표준규격사진 1매, 수수료'), item('photo', anchor='여권, 표준규격사진 1매, 수수료'), item('fee', anchor='여권, 표준규격사진 1매, 수수료')]
guidance('F-6-1', 'extension', scenario='first-extension',
         section='국민의 배우자(F-6-1)에 대한 체류기간 연장허가 — 가. 최초 체류기간 연장허가', anchor='결혼이민(F-6-1, 90일) 사증으로 입국 후 90일 이내에 주소지 관할 청(사무소·출장소)에 체류기간 연장 및 외국인등록 신청',
         summary_ko='결혼이민(F-6-1, 90일) 사증으로 입국했다면 입국 후 90일 이내에 주소지 관할 관서에서 외국인등록과 함께 첫 연장을 신청합니다. 체류허가기간은 입국일로부터 1년이며, 국제결혼 안내프로그램 대상 7개국(중국·베트남·필리핀·태국·캄보디아·우즈베키스탄·몽골) 국민이 조기적응프로그램을 이수하면 2년입니다.',
         summary_en='If you entered on a 90-day F-6-1 visa, apply for registration and the first extension within 90 days at your local office. The stay is one year from entry; nationals of the seven international-marriage program countries (China, Vietnam, Philippines, Thailand, Cambodia, Uzbekistan, Mongolia) who complete the early-adaptation program get two years.',
         timing_ko='입국 후 90일 이내', timing_en='Within 90 days of entry', period_ko='입국일로부터 1년 (조기적응프로그램 이수 시 2년)', period_en='1 year from entry (2 years with the early-adaptation program)',
         docs=F6_BASE_FIRST + [item('spouse_marriage_cert_detail', anchor='한국인 배우자의 혼인관계증명서(상세) 및 주민등록등본', role='korean_spouse', administrative_information_exemption=True), item('spouse_resident_reg', anchor='한국인 배우자의 혼인관계증명서(상세) 및 주민등록등본', role='korean_spouse', administrative_information_exemption=True),
                               item('child_family_cert', 'CONDITIONAL_REQUIRED', anchor='(부부사이에 출생한 자녀가 있을 경우) 자녀명의 가족관계증명서', applies_when_ko='부부 사이에 출생한 자녀가 있는 경우', applies_when_en='If the couple has a child', role='korean_spouse'),
                               item('occupation_report', anchor='③ 외국인 직업 신고서'), residence()])
guidance('F-6-1', 'extension', scenario='extension',
         section='국민의 배우자(F-6-1)에 대한 체류기간 연장허가 — 나. 체류기간 연장허가', anchor='단, 한국인 배우자와의 사이에 출생한 자녀를 양육하고 있는 경우 3년 범위 내',
         summary_ko='국민의 배우자(F-6-1)로 체류 중인 사람의 일반 연장입니다. 1년 범위에서 허가되며, 한국인 배우자와의 자녀를 양육 중이면 3년 범위입니다.',
         summary_en='Regular extension for F-6-1 spouses of Korean nationals: within one year, or within three years if raising a child born to the Korean spouse.',
         period_ko='1년 범위 내 · 자녀 양육 시 3년 범위 내', period_en='Within 1 year; within 3 years if raising a child of the marriage',
         docs=[item('app_form_34', anchor='신청서(별지 제 34호 서식), 여권, 수수료'), item('passport', anchor='신청서(별지 제 34호 서식), 여권, 수수료'), item('fee', anchor='신청서(별지 제 34호 서식), 여권, 수수료'),
               item('marriage_cert_detail', anchor='② 혼인관계증명서(상세)  ③ 주민등록등본', role='korean_spouse', administrative_information_exemption=True), item('resident_reg', anchor='② 혼인관계증명서(상세)  ③ 주민등록등본', role='korean_spouse', administrative_information_exemption=True),
               item('child_family_cert', 'CONDITIONAL_REQUIRED', anchor='(부부사이에 출생한 자녀가 있을 경우) 자녀명의 가족관계증명서', applies_when_ko='부부 사이에 출생한 자녀가 있는 경우', applies_when_en='If the couple has a child', role='korean_spouse'),
               item('occupation_report', anchor='⑤ 외국인 직업 신고서'), residence(),
               item('other_officer_docs', 'MAY_BE_REQUESTED_BY_OFFICER', anchor='그밖에 심사에 필요하다고 인정되는 서류(요청시 제출)')])
guidance('F-6-1', 'extension', scenario='separation-divorce-suit-missing',
         section='2. 별거․이혼소송․배우자 실종의 경우 체류기간 연장허가(F-6-1)', anchor='별거․이혼소송․배우자 실종의 경우 체류기간 연장허가',
         summary_ko='배우자와 별거 중이거나(주말부부 제외), 이혼소송 진행·준비 중이거나, 배우자가 실종되었으나 실종선고 전인 F-6-1 체류자의 연장입니다. 공통서류에 더해 상황별 입증서류를 냅니다.',
         summary_en='Extension for F-6-1 holders who are separated (not merely living apart for work), in or preparing divorce proceedings, or whose spouse is missing without a court declaration yet. Situation-specific evidence is added to the common documents.',
         docs=base_stay(anchor='① 신청서(별지 제 34호 서식), 여권 및 외국인등록증, 수수료') + [
             item('spouse_marriage_cert_detail', anchor='② 한국인 배우자의 혼인관계증명서(상세) 및 주민등록등본', role='korean_spouse', administrative_information_exemption=True), item('spouse_resident_reg', anchor='② 한국인 배우자의 혼인관계증명서(상세) 및 주민등록등본', role='korean_spouse', administrative_information_exemption=True),
             item('child_family_cert', 'CONDITIONAL_REQUIRED', anchor='(부부사이에 출생한 자녀가 있을 경우) 자녀명의 가족관계증명서', applies_when_ko='부부 사이에 출생한 자녀가 있는 경우', applies_when_en='If the couple has a child', role='korean_spouse'),
             item('occupation_report', anchor='④ 외국인 직업 신고서'), residence(),
             item('separation_proof', 'CONDITIONAL_REQUIRED', anchor='별거사유 입증서류(예시)', applies_when_ko='별거 중인 경우(가출신고서, 진단서·증거사진, 보호시설 입소확인서, 형사판결문, 주변인·여성단체 확인서 등; 배우자 수감 시 수용증명서 필수)', applies_when_en='If separated (missing-person report, medical certificate or photos, shelter admission, criminal judgment, third-party or women\'s-group statements; spouse in prison: custody certificate required)'),
             item('divorce_suit_docs', 'CONDITIONAL_REQUIRED', anchor='이혼소송 관련 서류(소제기 증명원 등)', applies_when_ko='이혼소송 진행·준비 중인 경우', applies_when_en='If divorce proceedings are under way or being prepared'),
             item('missing_proof', 'CONDITIONAL_REQUIRED', anchor='실종사실을 증명하는 서류', applies_when_ko='배우자가 실종된 경우(실종선고심판 청구서, 실종신고서, 주변인·여성단체 확인서 등)', applies_when_en='If the spouse is missing (court petition, missing-person report, third-party or women\'s-group statements)'),
             item('other_officer_docs', 'MAY_BE_REQUESTED_BY_OFFICER', anchor='그 밖에 심사에 필요하다고 인정되는 서류')])
guidance('F-6-2', 'extension', scenario='first-extension',
         section='자녀 양육자(F-6-2)에 대한 체류기간 연장허가 — 가. 최초 체류기간 연장허가', anchor='자녀양육(F-6-2, 90일) 사증으로 입국 후 90일 이내',
         summary_ko='자녀양육(F-6-2, 90일) 사증으로 입국했다면 90일 이내에 외국인등록과 첫 연장을 함께 신청합니다. 허가기간은 입국일로부터 1년(조기적응프로그램 이수 시 2년)입니다.',
         summary_en='If you entered on a 90-day F-6-2 visa, file registration and the first extension within 90 days. The stay is one year from entry (two with the early-adaptation program).',
         timing_ko='입국 후 90일 이내', timing_en='Within 90 days of entry', period_ko='입국일로부터 1년 (조기적응프로그램 이수 시 2년)', period_en='1 year from entry (2 years with the early-adaptation program)',
         docs=F6_BASE_FIRST + [item('child_basic_family_cert', anchor='자녀명의 기본증명서․가족관계증명서(자녀가 국민인 경우)'), item('occupation_report', anchor='③ 외국인 직업 신고서'), residence()])
guidance('F-6-2', 'extension', scenario='extension',
         section='자녀 양육자(F-6-2)에 대한 체류기간 연장허가 — 나. 체류기간 연장허가', anchor='자녀를 계속 양육하고 있음을 입증하는 서류',
         summary_ko='자녀양육(F-6-2)으로 체류 중인 사람의 일반 연장은 3년 범위에서 허가되며, 자녀를 계속 양육하고 있음을 입증하는 서류(학비·병원비 영수증 등)가 필요합니다.',
         summary_en='Regular F-6-2 extensions are granted within three years and require proof that you are still raising the child (tuition or medical receipts, etc.).',
         period_ko='3년 범위 내', period_en='Within 3 years',
         docs=[item('app_form_34', anchor='신청서(별지 제 34호 서식), 여권, 수수료'), item('passport', anchor='신청서(별지 제 34호 서식), 여권, 수수료'), item('fee', anchor='신청서(별지 제 34호 서식), 여권, 수수료'),
               item('child_basic_family_cert', anchor='자녀명의 기본증명서․가족관계증명서(자녀가 국민인 경우)'), item('child_care_proof', anchor='자녀를 계속 양육하고 있음을 입증하는 서류'), item('occupation_report', anchor='⑤ 외국인 직업 신고서'), residence(), item('other_officer_docs', 'MAY_BE_REQUESTED_BY_OFFICER', anchor='그밖에 심사에 필요하다고 인정되는 서류(요청 시 제출)')])
F63_COMMON = [item('child_family_cert', 'CONDITIONAL_REQUIRED', anchor='(부부사이에 출생한 자녀가 있을 경우) 자녀명의 가족관계증명서', applies_when_ko='부부 사이에 출생한 자녀가 있는 경우', applies_when_en='If the couple had a child', role='applicant'), item('occupation_report', anchor='외국인 직업 신고서'), residence(), item('other_officer_docs', 'MAY_BE_REQUESTED_BY_OFFICER', anchor='그 밖에 심사에 필요하다고 인정되는 서류')]
guidance('F-6-3', 'extension', scenario='after-death',
         section='혼인단절자(F-6-3)에 대한 체류기간 연장허가 — 가. 국민의 배우자가 사망한 후 최초 체류기간 연장허가', anchor='국민의 배우자가 사망한 후 최초 체류기간 연장허가',
         summary_ko='정상적인 혼인생활 중 한국인 배우자가 사망한 경우의 첫 연장입니다. 사망 입증서류와 가족관계 입증서류를 냅니다.',
         summary_en='First extension after the Korean spouse died during a genuine marriage. Submit proof of death and of the family relationship.',
         docs=base_stay(anchor='① 신청서(별지 제34호 서식), 여권 및 외국인등록증, 수수료') + [item('death_proof', anchor='배우자의 사망 입증서류'), item('family_relation', anchor='가족관계 입증서류(혼인관계증명서(상세) 등)')] + F63_COMMON)
guidance('F-6-3', 'extension', scenario='after-missing',
         section='혼인단절자(F-6-3) — 나. 국민 배우자가 실종된 후 최초 체류기간 연장허가', anchor='국민 배우자가 실종된 후 최초 체류기간 연장허가',
         summary_ko='가정법원의 실종선고가 있는 경우의 첫 연장입니다. 실종선고심판서와 가족관계 입증서류를 냅니다.',
         summary_en='First extension after a family-court declaration that the Korean spouse is missing. Submit the court declaration and proof of family relationship.',
         docs=base_stay(anchor='① 신청서(별지 제34호 서식), 여권 및 외국인등록증, 수수료') + [item('missing_judgment', anchor='실종사실 증명서류(실종선고심판서)'), item('family_relation', anchor='가족관계 입증서류(혼인관계증명서(상세) 등)')] + F63_COMMON)
guidance('F-6-3', 'extension', scenario='after-divorce',
         section='혼인단절자(F-6-3) — 다. 국민 배우자와 이혼한 후 최초 체류기간 연장허가', anchor='국민 배우자와 이혼한 후 최초 체류기간 연장허가',
         summary_ko='자신에게 책임 없는 사유(배우자의 가출·폭력 등)로 이혼한 경우의 첫 연장입니다. 이혼 기재 혼인관계증명서, 이혼 소송서류, 귀책사유 입증자료를 냅니다.',
         summary_en='First extension after a divorce caused by the Korean spouse (desertion, violence, etc.). Submit the marriage certificate showing the divorce, the divorce documents and evidence of the spouse\'s fault.',
         docs=base_stay(anchor='① 신청서(별지 제34호 서식), 여권 및 외국인등록증, 수수료') + [item('divorce_marriage_cert', anchor='이혼사실이 기재된 혼인관계증명서(상세)'), item('divorce_suit_full', anchor='이혼관련 소송서류'), item('fault_proof', anchor='귀책사유 입증자료')] + F63_COMMON)
guidance('F-6-3', 'extension', scenario='extension',
         section='혼인단절자(F-6-3) — 라. 최초 기간연장 후 혼인단절(F-6-3)자격으로 체류 중인 외국인에 대한 체류기간연장 허가', anchor='최초 기간연장 후 혼인단절(F-6-3)자격으로 체류 중인 외국인에 대한 체류기간연장 허가',
         summary_ko='혼인단절(F-6-3) 자격으로 이미 체류 중인 사람의 이후 연장입니다.', summary_en='Subsequent extensions for people already staying as F-6-3.',
         docs=[item('app_form_34', anchor='① 신청서(별지 제34호 서식), 여권, 외국인등록증, 수수료'), item('passport', anchor='① 신청서(별지 제34호 서식), 여권, 외국인등록증, 수수료'), item('arc', anchor='① 신청서(별지 제34호 서식), 여권, 외국인등록증, 수수료'), item('fee', anchor='① 신청서(별지 제34호 서식), 여권, 외국인등록증, 수수료')] + F63_COMMON)

# F-6 registration (F-6-1 / F-6-2)
guidance('F-6-1', 'registration', section='결혼이민(F-6) 외국인등록 — 1. 국민의 배우자(F-6-1)', anchor='결혼이민(F-6-1)사증으로 입국 후 90일 이내에 주소지 관할 청(사무소ㆍ출장소)에 외국인등록',
         summary_ko='결혼이민(F-6-1) 사증으로 입국한 뒤 90일 이내에 주소지 관할 관서에 외국인등록을 합니다.', summary_en='Register as a foreign resident within 90 days of entering on an F-6-1 visa at your local office.',
         timing_ko='입국 후 90일 이내', timing_en='Within 90 days of entry',
         docs=F6_BASE_FIRST[:1] + [item('passport', anchor='신청서(별지 제34호 서식), 여권, 표준규격사진 1매, 수수료'), item('photo', anchor='신청서(별지 제34호 서식), 여권, 표준규격사진 1매, 수수료'), item('fee', anchor='신청서(별지 제34호 서식), 여권, 표준규격사진 1매, 수수료'),
               item('spouse_marriage_cert_detail', anchor='② 한국인 배우자의 혼인관계증명서(상세) ③ 한국인 배우자의 주민등록등본', role='korean_spouse', administrative_information_exemption=True), item('spouse_resident_reg', anchor='② 한국인 배우자의 혼인관계증명서(상세) ③ 한국인 배우자의 주민등록등본', role='korean_spouse', administrative_information_exemption=True),
               item('child_family_cert', 'CONDITIONAL_REQUIRED', anchor='부부 사이에 출생한 자녀가 있을 경우 자녀 명의 가족관계증명서', applies_when_ko='부부 사이에 출생한 자녀가 있는 경우', applies_when_en='If the couple has a child', role='korean_spouse')])
guidance('F-6-2', 'registration', section='결혼이민(F-6) 외국인등록 — 2. 자녀 양육자(F-6-2)', anchor='입국한 날로부터 90일을 초과하여 등록하는 경우에는 사범처리',
         summary_ko='자녀양육(F-6-2) 사증 입국자는 입국일로부터 90일 이내에 외국인등록을 해야 하며, 90일을 넘기면 사범처리 대상입니다. 체류허가기간은 입국일로부터 1년입니다.', summary_en='F-6-2 entrants must register within 90 days of entry; late registration is an offence. The stay is one year from entry.',
         timing_ko='입국 후 90일 이내', timing_en='Within 90 days of entry', period_ko='입국일로부터 1년', period_en='1 year from entry',
         docs=[item('app_form_34', anchor='신청서(별지 제34호 서식), 여권, 표준규격사진 1매, 수수료'), item('passport', anchor='신청서(별지 제34호 서식), 여권, 표준규격사진 1매, 수수료'), item('photo', anchor='신청서(별지 제34호 서식), 여권, 표준규격사진 1매, 수수료'), item('fee', anchor='신청서(별지 제34호 서식), 여권, 표준규격사진 1매, 수수료'),
               item('child_basic_family_cert', anchor='자녀가 국민인 경우 자녀 명의의 기본증명서․가족관계증명서'), residence(anchor='체류지를 입증할 수 있는 서류')])

# ==========================================================================
# G-1 기타 — 연장 (사유별)
# ==========================================================================
G1_BASE = [item('app_form_34', anchor='① 신청서(별지 제34호 서식), 여권, 외국인등록증, 수수료'), item('passport', anchor='① 신청서(별지 제34호 서식), 여권, 외국인등록증, 수수료'), item('arc', anchor='① 신청서(별지 제34호 서식), 여권, 외국인등록증, 수수료'), item('fee', anchor='① 신청서(별지 제34호 서식), 여권, 외국인등록증, 수수료')]
guidance('G-1-1', 'extension', section='기타(G-1) 체류기간 연장허가 — 1. 산업재해 청구 및 치료 중인 사람과 그 가족', anchor='1. 산업재해 청구 및 치료 중인 사람과 그 가족',
         summary_ko='산업재해 청구·치료 중인 사람과 그 가족은 원칙적으로 6개월(중증 환자는 1년) 범위에서 연장되며, 산재 진단서와 근로복지공단 서류, G-1 심사확인서를 냅니다.', summary_en='People claiming or being treated for an industrial accident (and their family) are extended within 6 months (1 year for severe cases) with the accident medical certificate, KCOMWEL documents and the G-1 review form.',
         period_ko='6개월 범위 내 (중증 환자 1년)', period_en='Within 6 months (1 year for severe cases)',
         docs=G1_BASE + [item('industrial_accident_diag', anchor='산재로 인한 병원 진단서'), item('kcomwel_card', anchor='근로복지공단 발행 ‘진료계획 심사 결정 통지서(산재보험카드)’, 후유증상서비스 카드 등'), item('g1_review_form', anchor='기타(G-1) 자격 심사확인서(별첨 2 서식)'), residence()])
guidance('G-1-2', 'extension', section='기타(G-1) 체류기간 연장허가 — 2. 질병, 사고로 치료 중인 사람과 그 가족', anchor='2. 질병, 사고로 치료 중인 사람과 그 가족',
         summary_ko='질병·사고로 치료 중인 사람과 가족은 1회 6개월 범위에서 연장되며, 장기치료 필요성 진단서와 비용 조달 능력 입증서류, 신원보증서, G-1 심사확인서를 냅니다.', summary_en='People under treatment for illness or accident (and family) are extended within 6 months at a time with a medical certificate showing the need for long-term treatment, proof of funds, a letter of guarantee and the G-1 review form.',
         period_ko='1회 6개월 범위 내', period_en='Within 6 months per extension',
         docs=G1_BASE + [item('long_treatment_diag', anchor='의료기관에서 발행한 진단서 등 장기치료의 필요성을 입증하는 서류'), item('treatment_cost_proof', anchor='치료 및 체류 비용 조달 능력 입증서류'), item('guarantor', anchor='④ 신원보증서'), item('g1_review_form', anchor='기타(G-1) 자격 심사확인서(별첨 2 서식)'),
                         item('family_relation_accompany', 'CONDITIONAL_REQUIRED', anchor='가족관계 입증서류(배우자 또는 직계가족 동반시만 해당)', applies_when_ko='배우자 또는 직계가족이 동반하는 경우', applies_when_en='If a spouse or direct family member accompanies'), residence()])
guidance('G-1-3', 'extension', section='기타(G-1) 체류기간 연장허가 — 3. 각종 소송진행 중인 사람 (G-1-3)', anchor='3. 각종 소송진행 중인 사람 (G-1-3)',
         summary_ko='소송 진행 중인 사람은 1회 6개월 범위에서 연장되며, 소장 사본·소송제기 증명원 등 청구권 확인 서류와 신원보증서, G-1 심사확인서를 냅니다.', summary_en='Litigants are extended within 6 months at a time with the complaint copy, certificate of filing or other proof of the claim, a letter of guarantee and the G-1 review form.',
         period_ko='1회 6개월 범위 내', period_en='Within 6 months per extension',
         docs=G1_BASE + [item('lawsuit_docs', anchor='소장 사본, 소송제기 증명원, 법률구조결정서 사본'), item('guarantor', anchor='③ 신원보증서'), item('g1_review_form', anchor='기타(G-1) 자격 심사확인서(별첨 2 서식)'),
                         item('family_or_guardian_proof', 'CONDITIONAL_REQUIRED', anchor='가족관계 또는 보호자 입증서류(가족․보호자에 한함)', applies_when_ko='가족·보호자로 체류하는 경우', applies_when_en='Family members or guardians only'), residence()])
guidance('G-1-4', 'extension', section='기타(G-1) 체류기간 연장허가 — 4. 임금체불 노동관서 중재중인 사람 (G-1-4)', anchor='4. 임금체불 노동관서 중재중인 사람 (G-1-4)',
         summary_ko='임금체불로 노동관서에서 중재 중인 사람은 6개월 범위(출국기간 유예자는 3개월)에서 연장되며, 체불금품 확인원 등과 신원보증서, G-1 심사확인서를 냅니다.', summary_en='Workers in wage-arrears mediation are extended within 6 months (3 months for those on departure deferral) with the arrears confirmation, a letter of guarantee and the G-1 review form.',
         period_ko='6개월 범위 내 (출국기간 유예자 3개월)', period_en='Within 6 months (3 months for departure-deferral cases)',
         docs=G1_BASE + [item('wage_arrears_cert', anchor='노동부 발급 체불금품 확인원, 대한법률구조공단 접수증 등'), item('lawsuit_docs_if_any', 'CONDITIONAL_REQUIRED', anchor='소송관련 서류 (소송 수행중인 자에 한함)', applies_when_ko='소송을 수행 중인 경우', applies_when_en='If litigating'), item('g1_review_form', anchor='기타(G-1) 자격부여 심사확인서(별첨 2 서식)'), item('guarantor', anchor='⑤ 신원보증서'), residence()])
guidance('G-1-5', 'extension', section='기타(G-1) 체류기간 연장허가 — 5. 난민신청자 및 난민불인정자 중 인도적 체류허가자', anchor='5. 난민신청자 및 난민불인정자 중 인도적 체류허가자',
         summary_ko='난민신청자는 매회 6개월~1년 범위에서 연장되며(소송 예정기간 등을 고려해 탄력 부여), 신청서·여권·외국인등록증과 체류지 입증서류를 냅니다. 수수료는 일반 체류외국인과 같습니다.', summary_en='Asylum applicants are extended 6 months to 1 year at a time (flexibly, considering pending litigation) with the form, passport, residence card and proof of residence. The fee is the same as for other residents.',
         period_ko='매회 6개월~1년 범위 내', period_en='6 months to 1 year per extension',
         docs=[item('app_form_34', anchor='① 신청서(별지 제34호 서식), 여권, 외국인등록증'), item('passport', anchor='① 신청서(별지 제34호 서식), 여권, 외국인등록증'), item('arc', anchor='① 신청서(별지 제34호 서식), 여권, 외국인등록증'), item('fee', anchor='수수료는 일반 체류외국인과 동일'), residence(anchor='② 체류지 입증서류')])
guidance('G-1-6', 'extension', section='기타(G-1) 체류기간 연장허가 — 5. 난민신청자 및 난민불인정자 중 인도적 체류허가자', anchor='(인도적 체류허가자) 그 사유가 소멸될 때까지 1회 1년의 범위 내에서 체류기간연장 허가',
         summary_ko='인도적 체류허가자는 사유가 소멸될 때까지 1회 1년 범위에서 연장되며, 신청서·여권·외국인등록증과 체류지 입증서류를 냅니다.', summary_en='Humanitarian stay holders are extended one year at a time until the grounds cease, with the form, passport, residence card and proof of residence.',
         period_ko='1회 1년 범위 내', period_en='Within 1 year per extension',
         docs=[item('app_form_34', anchor='① 신청서(별지 제34호 서식), 여권, 외국인등록증'), item('passport', anchor='① 신청서(별지 제34호 서식), 여권, 외국인등록증'), item('arc', anchor='① 신청서(별지 제34호 서식), 여권, 외국인등록증'), item('fee', anchor='수수료는 일반 체류외국인과 동일'), residence(anchor='② 체류지 입증서류')])
guidance('G-1-9', 'extension', section='기타(G-1) 체류기간 연장허가 — 6. 임신․출산 등 인도적 배려가 불가피한 사람', anchor='6. 임신․출산 등 인도적 배려가 불가피한 사람',
         summary_ko='임신·출산 등 인도적 배려가 불가피한 사람은 6개월 범위에서 연장되며, 진단서 등 연장 필요성 입증서류와 신원보증서를 냅니다.', summary_en='People needing humanitarian consideration for pregnancy or childbirth are extended within 6 months with a medical certificate proving the need and a letter of guarantee.',
         period_ko='6개월 범위 내', period_en='Within 6 months',
         docs=G1_BASE + [item('diag_extension_need', anchor='진단서 등 연장 필요성을 입증하는 서류'), item('guarantor', anchor='③ 신원보증서'), residence()])
guidance('G-1-10', 'extension', section='기타(G-1) 체류기간 연장허가 — 7. 외국인환자', anchor='G-1-10 자격으로 체류하고 있는 자로서 치료 또는 요양기간이 길어져 장기간 체류가 필요한 사람',
         summary_ko='치료·요양이 길어진 외국인환자와 동반가족·간병인은 1년 이내에서 연장되며, 의료기관 소견서와 비용 조달 능력 입증서류를 냅니다. 유치기관 또는 신원보증인이 보증하면 비용 서류는 생략됩니다.', summary_en='Medical-treatment patients whose care runs long (and accompanying family/caregivers) are extended within one year with a medical opinion and proof of funds; the funds proof is waived when a registered facilitator or guarantor vouches.',
         period_ko='체류기간 1년 이내', period_en='Within 1 year',
         docs=G1_BASE + [item('medical_opinion', anchor='의료기관에서 발급한 소견서, 진단서 등 장기체류의 필요성을 입증할 수 있는 서류', role='medical_institution'),
                         item('treatment_cost_proof', 'CONDITIONAL_REQUIRED', anchor='치료 및 체류 비용 조달 능력을 입증할 수 있는 서류', does_not_apply_when_ko='유치기관 또는 신원보증인이 신원을 보증하는 경우 제출 생략(최초 초청 유치기관 등 예외)', does_not_apply_when_en='Waived when a facilitator or guarantor vouches (exceptions for first-time facilitators etc.)'),
                         item('family_caregiver_proof', 'CONDITIONAL_REQUIRED', anchor='가족관계 및 간병인 입증서류', applies_when_ko='동반 배우자·가족·간병인에 한하며 기제출 시 생략', applies_when_en='Accompanying spouse/family/caregiver only; waived if already submitted', previous_submission_exemption=True),
                         item('proxy_docs', 'CONDITIONAL_REQUIRED', anchor='⑤ 대리 신청 시 추가서류', applies_when_ko='유치기관·의료기관이 대리 신청하는 경우(위임장, 재직증명서)', applies_when_en='If a facilitator or hospital files on your behalf (power of attorney, employment certificate)', role='medical_institution'), residence()])
guidance('G-1-11', 'extension', section='기타(G-1) 체류기간 연장허가 — 8. 성폭력피해자 등 인도적 고려가 필요한 사람', anchor='8. 성폭력피해자 등 인도적 고려가 필요한 사람',
         summary_ko='성폭력피해자 등 인도적 고려가 필요한 사람은 1년 범위에서 연장되며, 소송 서류 등 권리구제 입증서류와 신원보증서를 냅니다.', summary_en='Victims of sexual violence and similar humanitarian cases are extended within one year with proof of the remedy sought (lawsuit documents etc.) and a letter of guarantee.',
         period_ko='1년 범위 내', period_en='Within 1 year',
         docs=G1_BASE + [item('rights_relief_proof', anchor='소송관련 서류 등 권리구제 입증서류'), item('guarantor', anchor='③ 신원보증서'), residence()])
guidance('G-1-99', 'extension', section='기타(G-1) 체류기간 연장허가 — 9. 기타 사유에 해당되는 사람 (G-1-99)', anchor='다음 요건을 모두 충족한 난민신청자(G-1-5)의 국내 출생 자녀',
         summary_ko='이 항목의 대상은 합법체류 중인 난민신청자(G-1-5)의 국내 출생 자녀(17세 미만, 본인 난민신청 없음)이며, 부모의 체류기간 만료일까지 부여됩니다. 여권이 없으면 사유서로 갈음합니다.', summary_en='This item covers Korea-born children (under 17, not themselves asylum applicants) of lawfully staying asylum applicants; the stay matches the parent\'s expiry. A written explanation replaces a missing passport.',
         period_ko='부모(G-1-5)의 체류기간 만료일까지', period_en='Until the parent\'s (G-1-5) expiry',
         docs=[item('app_form_34', anchor='신청서(별지 제34호 서식), 여권*, 표준규격사진 1매, 수수료'), item('passport', anchor='난민 신청의 특수성으로 여권이 없을 경우 그 사유서로 갈음', substitution_allowed=True, substitute_documents=['사유서 (여권이 없는 경우)']), item('photo', anchor='표준규격사진 1매, 수수료'), item('fee', anchor='표준규격사진 1매, 수수료'), item('birth_cert_age_proof', anchor='출생증명서 등 부모와의 관계를 입증할 수 있는 서류')])
guidance('G-1-12', 'extension', section='기타(G-1) 체류기간 연장허가 — 10. 인도적 체류허가자의 가족 (G-1-12)', anchor='10. 인도적 체류허가자의 가족 (G-1-12)',
         summary_ko='인도적 체류허가자의 배우자·미성년 자녀(배우자가 있는 미성년자 제외)는 인도적 체류허가자의 체류기간 범위에서 연장되며, 신청서·여권·외국인등록증과 체류지 입증서류를 냅니다.', summary_en='Spouses and minor children of humanitarian stay holders (excluding married minors) are extended within the holder\'s stay with the form, passport, residence card and proof of residence.',
         period_ko='인도적 체류허가자의 체류기간 범위 내', period_en='Within the humanitarian holder\'s period of stay',
         docs=[item('app_form_34', anchor='신청서(별지 제34호 서식), 여권 및 외국인등록증'), item('passport', anchor='신청서(별지 제34호 서식), 여권 및 외국인등록증'), item('arc', anchor='신청서(별지 제34호 서식), 여권 및 외국인등록증'), item('fee', anchor='수수료는 일반 체류외국인과 동일'), residence(anchor='교회·난민지원시설·인권단체·UNHCR', alts=RESIDENCE_ALTS + [{'ko': '교회·난민지원시설·인권단체·UNHCR 등의 주거확인서', 'en': 'Housing confirmation from a church, refugee shelter, human-rights group or UNHCR'}])])

# ==========================================================================
# D-10 구직 — 연장 (유형별)
# ==========================================================================
D10_COMMON = [item('app_form', anchor='공통서류(신청서, 사진, 여권사본, 수수료, 신분증사본)'), item('photo', anchor='공통서류(신청서, 사진, 여권사본, 수수료, 신분증사본)'), item('passport_copy', anchor='공통서류(신청서, 사진, 여권사본, 수수료, 신분증사본)'), item('fee', anchor='공통서류(신청서, 사진, 여권사본, 수수료, 신분증사본)'), item('arc_copy', anchor='공통서류(신청서, 사진, 여권사본, 수수료, 신분증사본)')]
guidance('D-10-1', 'extension', scenario='points',
         section='구직(D-10) 체류기간 연장허가 — 1-1) 일반 구직(D-10-1): 점수제 적용 대상자', anchor='1-1) 일반 구직(D-10-1): 점수제 적용 대상자',
         summary_ko='점수제 적용 대상 일반구직자는 공통서류에 구직활동계획서, 체류지·체재비 입증서류(1인 가구 주거급여 기준액 × 체류개월 수 이상 잔고)와 점수제 평가 서류를 냅니다. 체류기간 상한은 합산 최대 3년입니다.', summary_en='Points-system D-10-1 holders add a job-seeking plan, proof of residence and living funds (≥ single-household housing-benefit standard × months) and points evidence. Total stay is capped at 3 years.',
         period_ko='합산 최대 3년', period_en='Up to 3 years in total',
         docs=D10_COMMON + [item('job_plan', anchor='❍ 구직활동계획서'), residence(anchor='❍ 체류지 입증서류'), item('stay_cost_proof_d10', anchor='연도별 1인 가구 주거급여 기준액 × 체류개월 수'), item('points_docs', 'ADDITIONAL_IF_APPLICABLE', anchor='기타 점수제 평가를 위해 필요하다고 인정되는 서류', applies_when_ko='점수제 평가에 필요한 경우', applies_when_en='As needed for the points evaluation')])
guidance('D-10-1', 'extension', scenario='exempt-korean-graduate',
         section='구직(D-10) 체류기간 연장허가 — 1-2) 점수제 면제 특례자 ⅰ) 국내 대학 졸업 한국어능력 우수자', anchor='ⅰ) 국내 대학 졸업 한국어능력 우수자',
         summary_ko='국내 대학 졸업 한국어능력 우수자(점수제 면제)는 공통서류와 구직활동계획서, 체류지 입증서류로 연장합니다.', summary_en='Korean-university graduates with strong Korean (points-exempt) extend with the common documents, a job-seeking plan and proof of residence.',
         docs=D10_COMMON + [item('job_plan', anchor='❍ 구직활동 계획서'), residence(anchor='❍ 체류지 입증서류')])
guidance('D-10-1', 'extension', scenario='exempt-domestic-youth',
         section='구직(D-10) 체류기간 연장허가 — 1-2) ⅱ) 국내 성장 기반 외국인 청소년', anchor='ⅱ) 국내 성장 기반 외국인 청소년',
         summary_ko='국내 성장 기반 외국인 청소년(점수제 면제)은 공통서류와 구직활동계획서(붙임6), 체류지 입증서류로 연장합니다.', summary_en='Domestically raised foreign youth (points-exempt) extend with the common documents, the job-seeking plan (Annex 6) and proof of residence.',
         docs=D10_COMMON + [item('job_plan', anchor='구직활동 계획서(붙임6)'), residence(anchor='❍ 체류지 입증서류')])
guidance('D-10-1', 'extension', scenario='exempt-promising-talent',
         section='구직(D-10) 체류기간 연장허가 — 1-2) ⅲ) 유망인재', anchor='ⅲ) 유망인재',
         summary_ko='유망인재(점수제 면제)는 공통서류와 구직활동계획서, 체류지 입증서류로 연장합니다.', summary_en='Promising talent (points-exempt) extend with the common documents, a job-seeking plan and proof of residence.',
         docs=D10_COMMON + [item('job_plan', anchor='❍ 구직활동 계획서'), residence(anchor='❍ 체류지 입증서류')])
guidance('D-10-1', 'extension', scenario='exempt-caregiver-trainee',
         section='구직(D-10) 체류기간 연장허가 — 1-2) ⅳ) 요양보호사 전문연수 과정 수료자', anchor='ⅳ) 요양보호사 전문연수 과정 수료자',
         summary_ko='요양보호사 전문연수 수료자는 공통서류에 인턴 재직증명서, 체류지·체재비 입증서류를 냅니다. 급여를 받는 인턴은 급여지급 내역서로 체재비 서류를 대체할 수 있습니다.', summary_en='Care-worker training graduates add an internship employment certificate plus proof of residence and living funds; paid interns may substitute a pay statement for the funds proof.',
         docs=D10_COMMON + [item('intern_employment_cert', anchor='❍ 인턴 재직증명서', role='employer'), residence(anchor='❍ 체류지 입증서류'), item('stay_cost_proof_d10', anchor='인턴활동으로 급여가 지급되는 경우 급여지급 내역서로 대체 가능', substitution_allowed=True, substitute_documents=['급여지급 내역서 (급여를 받는 인턴)'])])
guidance('D-10-1', 'extension', scenario='exempt-professional-experience',
         section='구직(D-10) 체류기간 연장허가 — 1-2) ⅴ) 전문직종(E-1~E-7) 근무 경력자', anchor='ⅴ) 전문직종(E-1~E-7) 근무 경력자',
         summary_ko='전문직종(E-1~E-7) 근무 경력자는 공통서류에 구직활동계획서, 출국 없이 새 근로계약이 가능함을 입증하는 서류(잔여 계약 1개월 이상이면 이적동의서), 체류지·체재비 입증서류를 냅니다.', summary_en='Former E-1~E-7 professionals add a job-seeking plan, proof that a new contract can be signed without leaving (a transfer consent if 1+ month remains on the old contract), and proof of residence and living funds.',
         docs=D10_COMMON + [item('job_plan', anchor='❍ 구직활동 계획서'), item('transfer_consent', 'CONDITIONAL_REQUIRED', anchor='이적동의서(이전 근무처에서 잔여 근로계약 기간이 1개월 이상 있는 경우)', applies_when_ko='이전 근무처의 잔여 근로계약 기간이 1개월 이상인 경우', applies_when_en='If 1+ month remains on the previous contract', role='employer'), residence(anchor='❍ 체류지 입증서류'), item('stay_cost_proof_d10', anchor='연도별 1인 가구 주거급여 기준액 × 체류개월 수')])
guidance('D-10-2', 'extension', section='구직(D-10) 체류기간 연장허가 — 2) 기술창업준비(D-10-2)', anchor='2) 기술창업준비(D-10-2)',
         summary_ko='기술창업준비(D-10-2)는 공통서류에 기술창업활동계획서, 체재비·체류지 입증서류를 냅니다. K-Startup 그랜드챌린지 참가자는 체류경비 입증서류가 면제됩니다.', summary_en='D-10-2 start-up preparers add a technology start-up activity plan and proof of living funds and residence; K-Startup Grand Challenge participants are exempt from the funds proof.',
         docs=D10_COMMON + [item('startup_plan', anchor='❍ 기술창업활동계획서'), item('stay_cost_proof_d10', 'CONDITIONAL_REQUIRED', anchor='K-Startup 그랜드챌린지 참가자는 체류경비 입증서류 면제', does_not_apply_when_ko='K-Startup 그랜드챌린지 참가자', does_not_apply_when_en='K-Startup Grand Challenge participants'), residence(anchor='❍ 체류지 입증서류')])
guidance('D-10-3', 'extension', section='구직(D-10) 체류기간 연장허가 — 3) 첨단기술인턴(D-10-3)', anchor='3) 첨단기술인턴(D-10-3)',
         summary_ko='첨단기술인턴(D-10-3)은 공통서류에 인턴사원 재직증명서, 초청기업의 사업자등록증·연구시설·인력 현황·고용보험 명부, 기업 자격 유지 입증서류, 구직(인턴)활동 계획서, 체재비·체류지 입증서류를 냅니다.', summary_en='D-10-3 high-tech interns add the internship employment certificate, the host company\'s registration, research facility/staff status and insurance roster, proof the company still qualifies, an internship plan and proof of living funds and residence.',
         docs=D10_COMMON + [item('intern_employment_cert', anchor='❍ 인턴사원 재직증명서', role='employer'), item('intern_company_docs', anchor='사업자등록증, 연구시설 및 연구인력 현황자료, 고용보험가입자 명부', role='employer'), item('intern_company_eligibility', anchor='첨단기술인턴(D-10-3) 초청 기업 자격 유지 입증 서류', role='employer'), item('job_plan', anchor='구직(인턴)활동 계획서'), item('stay_cost_proof_d10', anchor='인턴활동으로 급여가 지급되는 경우 급여지급 내역서로 대체 가능', substitution_allowed=True, substitute_documents=['급여지급 내역서 (급여를 받는 인턴)']), residence(anchor='❍ 체류지 입증서류')])
guidance('D-10-T', 'extension', section='구직(D-10) 체류기간 연장허가 — 4) 최우수인재(D-10-T)', anchor='4) 최우수인재(D-10-T)',
         summary_ko='예비톱티어 구직(D-10-T)은 공통서류(신청서, 사진, 여권 사본, 체류지 입증서류, 수수료)와 구직활동계획서로 연장합니다.', summary_en='Top-Tier job seekers (D-10-T) extend with the common documents (form, photo, passport copy, proof of residence, fee) and a job-seeking plan.',
         docs=[item('app_form', anchor='공통서류(신청서, 사진, 여권 사본, 체류지 입증서류, 수수료)'), item('photo', anchor='공통서류(신청서, 사진, 여권 사본, 체류지 입증서류, 수수료)'), item('passport_copy', anchor='공통서류(신청서, 사진, 여권 사본, 체류지 입증서류, 수수료)'), residence(anchor='공통서류(신청서, 사진, 여권 사본, 체류지 입증서류, 수수료)'), item('fee', anchor='공통서류(신청서, 사진, 여권 사본, 체류지 입증서류, 수수료)'), item('job_plan', anchor='❍ 구직활동계획서')])

# ==========================================================================
# Short-stay B / C
# ==========================================================================
for code, sec in (('B-1', '사증면제(B-1) 체류자격변경 및 체류기간연장'), ('B-2', '관광통과(B-2) 체류자격변경 및 체류기간연장')):
    guidance(code, 'extension', state='EXCEPTION_ONLY', section=sec, anchor='사증면제협정 또는 관광통과 목적으로 입국한 자에 대하여는 원칙적으로 체류기간 연장이나 체류자격 변경허가를 하지 아니하므로',
             summary_ko='사증면제협정·관광통과 목적 입국자는 원칙적으로 체류기간 연장이나 체류자격 변경이 허가되지 않습니다. 부득이한 경우에만 신청서·여권 원본·수수료와 연장 필요성 소명서류로 심사됩니다.',
             summary_en='Visa-waiver and tourist-transit entrants are in principle not granted extensions or status changes. Only unavoidable cases are reviewed, with the form, original passport, fee and evidence of the need to extend.',
             docs=[item('app_form', anchor='① 신청서(34호 서식), 여권 원본, 수수료'), item('passport_original', anchor='① 신청서(34호 서식), 여권 원본, 수수료'), item('fee', anchor='① 신청서(34호 서식), 여권 원본, 수수료'), item('necessity_proof', anchor='② 체류기간 연장의 필요성을 소명하는 서류')])
    guidance(code, 'status_change', state='EXCEPTION_ONLY', completeness='SOURCE_ONLY', section=sec, anchor='사증면제협정 또는 관광통과 목적으로 입국한 자에 대하여는 원칙적으로 체류기간 연장이나 체류자격 변경허가를 하지 아니하므로',
             summary_ko='사증면제(B-1)·관광통과(B-2) 입국자의 체류자격 변경은 원칙적으로 허가되지 않습니다. 사증면제(B-1)로 입국한 독일인의 결혼이민(F-6) 변경 등 개별 예외는 해당 목표 자격 안내를 확인하세요.',
             summary_en='Status changes for B-1/B-2 entrants are in principle not granted. Individual exceptions (e.g. German B-1 entrants changing to F-6) are described under the target status.')
guidance('C-1', 'extension', section='일시취재(C-1) 체류기간 연장허가', anchor='입국일로부터 90일 미만 사증으로 입국한 자 또는 90일 미만 체류기간 받은 자에 대하여 입국일로부터 90일까지 연장',
         summary_ko='일시취재(C-1)는 입국일로부터 90일까지만 연장되며, 신청서·여권 원본·수수료와 취재명령서·파견증명서·재직증명서 등 필요성 소명서류를 냅니다.', summary_en='C-1 journalists may extend only up to 90 days from entry, with the form, original passport, fee and evidence such as an assignment order, dispatch or employment certificate.',
         period_ko='입국일로부터 최장 90일', period_en='Up to 90 days from entry',
         docs=[item('app_form', anchor='① 신청서(34호 서식), 여권 원본, 수수료'), item('passport_original', anchor='① 신청서(34호 서식), 여권 원본, 수수료'), item('fee', anchor='① 신청서(34호 서식), 여권 원본, 수수료'), item('necessity_proof_press', anchor='체류기간연장 필요성 소명 서류', role='employer')])
guidance('C-3', 'extension', section='단기방문(C-3) 체류기간 연장허가', anchor='단기방문(C-3) 활동 범위에 해당하고, 불법취업의 의심이 없으며 연장의 필요성이 인정되는 경우에 입국일로부터 체류기간 90일 범위 내 연장 가능',
         summary_ko='단기방문(C-3)은 활동범위 안에서 불법취업 의심이 없고 필요성이 인정될 때 입국일로부터 90일 범위에서 연장됩니다(출국 항공편 부재, 사고·질병, 친지방문, 선적 지연 등). 단체관광(C-3-2)·보증개별 사증 소지자는 출국편 부재나 영주·귀화 신청 같은 부득이한 사유에만 허가됩니다.',
         summary_en='C-3 visitors are extended within 90 days of entry when the activity is in scope, no illegal work is suspected and the need is recognised (no flight, accident or illness, family visit, shipping delays). Group-tour (C-3-2) and guaranteed-individual visa holders qualify only for unavoidable reasons such as no departure flight or a permanent-residence/naturalisation application.',
         period_ko='입국일로부터 90일 범위 내', period_en='Within 90 days of entry',
         docs=[item('app_form', anchor='① 신청서(34호 서식), 여권 원본, 수수료'), item('passport_original', anchor='① 신청서(34호 서식), 여권 원본, 수수료'), item('fee', anchor='① 신청서(34호 서식), 여권 원본, 수수료'), item('necessity_proof', anchor='② 체류기간 연장의 필요성을 소명하는 서류')])
guidance('C-3-2', 'extension', state='EXCEPTION_ONLY', section='단기방문(C-3) — 2. 단체관광(C-3-2) 사증 소지자에 대한 체류기간연장 제한', anchor='단체관광(C-3-2) 사증 소지자에 대한 체류기간연장 제한',
         summary_ko='단체관광객(C-3-2)과 보증개별사증(C-3-2) 소지자는 출국할 항공기가 없거나 영주·귀화 신청 등 부득이한 사유가 있을 때만 연장 또는 자격변경이 허가됩니다.', summary_en='Group-tour and guaranteed-individual C-3-2 holders are extended or changed only when there is no departure flight or another unavoidable reason such as a permanent-residence or naturalisation application.',
         docs=[item('app_form', anchor='① 신청서(34호 서식), 여권 원본, 수수료'), item('passport_original', anchor='① 신청서(34호 서식), 여권 원본, 수수료'), item('fee', anchor='① 신청서(34호 서식), 여권 원본, 수수료'), item('necessity_proof', anchor='② 체류기간 연장의 필요성을 소명하는 서류')])
guidance('C-4', 'extension', section='단기취업(C-4) 체류기간 연장허가', anchor='단기취업과 관련된 체류기간연장 필요성 소명 서류',
         summary_ko='단기취업(C-4)은 2010-08-23부터 원칙적으로 90일 사증으로 발급되어 입국일로부터 90일을 초과할 수 없고, 출국을 위한 연장은 출국편 부재 등 부득이한 경우에만 허가됩니다. 신청서·여권 원본·수수료와 고용계약서·사업자등록증 사본 등 소명서류를 냅니다.', summary_en='C-4 short-term employment visas are issued for 90 days (since 2010-08-23) and cannot exceed 90 days from entry; extensions for departure are allowed only when leaving is impossible. Submit the form, original passport, fee and evidence such as the contract and business registration copy.',
         period_ko='입국일로부터 90일 초과 불가', period_en='Cannot exceed 90 days from entry',
         docs=[item('app_form', anchor='① 신청서(별지 34호 서식), 여권 원본, 수수료'), item('passport_original', anchor='① 신청서(별지 34호 서식), 여권 원본, 수수료'), item('fee', anchor='① 신청서(별지 34호 서식), 여권 원본, 수수료'), item('necessity_proof_c4', anchor='단기취업과 관련된 체류기간연장 필요성 소명 서류', role='employer')])

# ==========================================================================
# A-series, D-1, D-4, D-5, D-6, D-7, D-8, D-9, E-1..E-6, E-8, E-10, F-5, H-1, H-2
# ==========================================================================
for code, sec, anc in (('A-1', '외교(A-1) 체류기간 연장허가', '재임기간 범위 내 체류기간연장'),):
    guidance(code, 'extension', section=sec, anchor=anc, completeness='PARTIALLY_STRUCTURED',
             summary_ko='외교(A-1)는 재임기간 범위에서 연장되며 제출서류는 체류자격 변경허가와 같고 수수료는 면제됩니다: 신청서, 여권, 자국 대사관 협조공문(외교사절단·영사기관 구성원), 파견·재직 증명서류; 동반가족은 출생증명서·가족관계증명서 등과 주체류자의 신분증.', summary_en='A-1 diplomats are extended within their term; the documents are the same as for the status change and there is no fee: form, passport, the embassy\'s cooperation letter (mission/consular members), proof of dispatch/employment; family members add birth and family-relation certificates and the principal\'s ID.',
             fee_ko='수수료 면제', fee_en='No fee', period_ko='재임기간 범위 내', period_en='Within the term of office',
             docs=[item('app_form', anchor='제출 서류 : 체류자격 변경허가와 동일(수수료 면제)'), item('passport', anchor='제출 서류 : 체류자격 변경허가와 동일(수수료 면제)'), item('diplomat_status_docs', 'SOURCE_MENTIONS_BUT_NOT_STRUCTURED', anchor='제출 서류 : 체류자격 변경허가와 동일(수수료 면제)', role='principal_holder', notes_ko='세부 목록은 외교(A-1) 체류자격 변경허가 항목(자국 대사관 협조공문, 파견·재직 증명서류, 동반가족은 가족관계 입증서류)을 따릅니다.', notes_en='The detailed list follows the A-1 status-change item (embassy cooperation letter, proof of dispatch/employment; family members add relationship proof).')])
guidance('A-2', 'extension', state='SOURCE_ONLY', completeness='SOURCE_ONLY', section='공무(A-2) 체류기간 연장허가', anchor='주재 목적이 아니라 단기 공무수행 목적으로 입국한 공무(A-2) 체류자격 소지자가 90일 이상 장기체류를 희망할 경우',
         summary_ko='공무(A-2)는 공무수행 기간 범위에서 연장되며, 단기 공무수행 목적 입국자가 90일 이상 장기체류를 희망하는 경우의 처리 기준이 별도로 있습니다. 세부 제출서류는 원문을 확인하세요.', summary_en='A-2 is extended within the official-duty period; short-term duty entrants who want to stay 90+ days are handled under a separate rule. See the original text for documents.')
guidance('A-3', 'extension', completeness='PARTIALLY_STRUCTURED', section='협정(A-3) 체류기간 연장허가 — 1. Fulbright 협정 대상자', anchor='연장기간은 I/D 카드 상의 기간 및 한미교육위원단 협조공한상 요청기간을 확인하여 부여',
         summary_ko='협정(A-3) 중 Fulbright 협정 대상자는 신청서, 여권, Fulbright I/D 카드, 한미교육위원단 협조공한으로 연장하며 I/D 카드와 협조공한상의 기간이 부여됩니다. 그 밖의 협정 대상자는 원문을 확인하세요.', summary_en='Fulbright grantees under A-3 extend with the form, passport, Fulbright ID card and the Korean-American Educational Commission letter; the period follows the ID card and letter. Other agreement holders: see the original text.',
         docs=[item('app_form', anchor='신청서(별지34호), 여권, Fulbright I/D 카드, 한미교육위원단 협조공한'), item('passport', anchor='신청서(별지34호), 여권, Fulbright I/D 카드, 한미교육위원단 협조공한'), item('other_officer_docs', 'SOURCE_MENTIONS_BUT_NOT_STRUCTURED', anchor='Fulbright I/D 카드, 한미교육위원단 협조공한', notes_ko='Fulbright I/D 카드와 한미교육위원단 협조공한', notes_en='Fulbright ID card and the Korean-American Educational Commission letter')])
for code in ('A-1', 'A-2', 'A-3'):
    guidance(code, 'workplace_change', state='NOT_APPLICABLE', completeness='SOURCE_ONLY', section=f'{code} 근무처의 변경․추가', anchor='해당사항 없음', summary_ko='근무처 변경·추가는 해당사항 없음.', summary_en='Workplace change/addition does not apply.')
    guidance(code, 'registration', state='CONDITIONAL', completeness='SOURCE_ONLY', section=f'{code} 외국인등록', anchor='외국인등록 면제 대상이나 본인이 원할 경우 외국인등록증 발급', summary_ko='외국인등록 면제 대상이지만 본인이 원하면 외국인등록증을 발급받을 수 있습니다.', summary_en='Exempt from registration, but a residence card is issued on request.')
    guidance(code, 'reentry', state='CONDITIONAL', completeness='SOURCE_ONLY', section=f'{code} 재입국허가', anchor='출국한 날로부터 1년 이내 재입국하려는 경우 면제', summary_ko='출국한 날로부터 1년 이내 재입국하면 재입국허가가 면제됩니다.', summary_en='Re-entry within one year of departure is exempt from the permit.')

guidance('D-1', 'extension', section='문화예술(D-1) 체류기간 연장허가', anchor='연수기관이 작성한 연수일정표',
         summary_ko='문화예술(D-1) 연장의 필수서류는 신청서·여권 원본·외국인등록증·수수료, 연수기관의 연수일정표, 문화예술단체 입증서류(사업자등록증 등), 체류지 입증서류이고, 추가서류로 연수증명서를 냅니다.', summary_en='D-1 extensions require the form, original passport, residence card, fee, the institution\'s training schedule, proof of the arts organisation (business registration) and proof of residence; a training certificate is an additional document.',
         docs=[item('app_form_34', anchor='①신청서(별지 제34호서식), 여권 원본, 외국인등록증, 수수료'), item('passport_original', anchor='①신청서(별지 제34호서식), 여권 원본, 외국인등록증, 수수료'), item('arc', anchor='①신청서(별지 제34호서식), 여권 원본, 외국인등록증, 수수료'), item('fee', anchor='①신청서(별지 제34호서식), 여권 원본, 외국인등록증, 수수료'), item('training_schedule', anchor='연수기관이 작성한 연수일정표', role='educational_institution'), item('culture_org_proof', anchor='문화예술단체 입증서류', role='educational_institution'), residence(), item('training_cert', 'ADDITIONAL_IF_APPLICABLE', anchor='①연수증명서', role='educational_institution', applies_when_ko='추가서류', applies_when_en='Additional document')])
guidance('D-4-1', 'extension', section='일반연수(D-4) — 1. 어학연수생(D-4-1, D-4-7)에 대한 체류기간 연장허가', anchor='어학연수생(D-4-1, D-4-7)에 대한 체류기간 연장허가',
         summary_ko='어학연수생(D-4-1, D-4-7)은 재학 입증서류, 학업 수행 입증서류(성적·출석), 국내 본인 계좌 재정입증, 모집요강 또는 연수계획서, 체류지 입증서류로 연장합니다. 가사휴학은 연장이 제한되고, 학교 변경은 원칙적으로 출국 후 재입국이지만 폐쇄 등 귀책 없는 사유나 TOPIK 3급 이상이면 예외입니다.', summary_en='Language trainees (D-4-1/7) extend with proof of enrollment, academic progress (grades/attendance), financial proof from their own Korean account, the program guide or plan and proof of residence. Personal leave restricts extension; changing school normally requires re-entry unless the school closed or you hold TOPIK 3+.',
         docs=[item('app_form_34', anchor='① 신청서 (별지 34호 서식), 여권, 외국인등록증, 수수료'), item('passport', anchor='① 신청서 (별지 34호 서식), 여권, 외국인등록증, 수수료'), item('arc', anchor='① 신청서 (별지 34호 서식), 여권, 외국인등록증, 수수료'), item('fee', anchor='① 신청서 (별지 34호 서식), 여권, 외국인등록증, 수수료'), item('enrollment_proof_generic', anchor='재학을 입증하는 서류', role='educational_institution'), item('academic_progress_proof', anchor='학업을 정상적으로 수행하고 있음을 입증하는 서류', role='educational_institution'), item('finance_proof_domestic', anchor='재정입증 서류(국내 본인계좌 예치금만 인정)'), item('language_program_docs', anchor='모집요강 (연수일정 명시) 또는 연수계획서 (어학연수생에 한함)', role='educational_institution'), residence()])
GUIDANCE[-1]['aliases'] = ['D-4-7']
guidance('D-4-2K', 'extension', section='일반연수(D-4) — 2. 기업 맞춤형 인턴십(K-Trainee, D-4-2K)의 체류기간연장 제출서류', anchor='기업 맞춤형 인턴십(K-Trainee, D-4-2K)의 체류기간연장 제출서류',
         summary_ko='K-Trainee(D-4-2K) 인턴기간은 원칙적으로 6개월을 넘을 수 없으나 필요 시 입국일로부터 1년 이내에서 연장되며, 체류지 입증서류와 기간연장 사유서·활동계획서를 냅니다.', summary_en='K-Trainee (D-4-2K) internships normally last up to 6 months; when needed they can be extended within one year of entry with proof of residence and an extension statement plus activity plan.',
         period_ko='입국일로부터 1년 이내', period_en='Within 1 year of entry',
         docs=[item('app_form_34', anchor='① 신청서(별지 제34호 서식), 여권, 외국인등록증, 수수료'), item('passport', anchor='① 신청서(별지 제34호 서식), 여권, 외국인등록증, 수수료'), item('arc', anchor='① 신청서(별지 제34호 서식), 여권, 외국인등록증, 수수료'), item('fee', anchor='① 신청서(별지 제34호 서식), 여권, 외국인등록증, 수수료'), residence(anchor='② 체류지 입증서류'), item('extension_reason_plan', anchor='기간연장 사유서 및 인턴·연수 활동 계획서')])
guidance('D-4-3', 'extension', section='일반연수(D-4) — 3. 고등학교 이하 교육기관 외국인유학생(D-4-3)의 체류기간연장 제출서류', anchor='고등학교 이하 교육기관 외국인유학생(D-4-3)의 체류기간연장 제출서류',
         summary_ko='고등학교 이하 유학생(D-4-3)은 재학증명서, 학비 납부 내역서, 체류비용 부담능력 입증서류, 후견인 변경 시 후견보증서 등(후견인 면제자는 기숙사 입소확인서), 체류지 입증서류로 연장합니다.', summary_en='K-12 students (D-4-3) extend with an enrollment certificate, tuition payment history, proof of funds, guardianship documents if the guardian changed (dormitory confirmation for guardian-exempt students) and proof of residence.',
         docs=[item('app_form_34', anchor='① 신청서(별지 제34호 서식), 여권, 외국인등록증, 수수료'), item('passport', anchor='① 신청서(별지 제34호 서식), 여권, 외국인등록증, 수수료'), item('arc', anchor='① 신청서(별지 제34호 서식), 여권, 외국인등록증, 수수료'), item('fee', anchor='① 신청서(별지 제34호 서식), 여권, 외국인등록증, 수수료'), item('enrollment_cert', anchor='② 재학증명서', role='educational_institution'), item('tuition_history', anchor='학비 납부 내역서', role='educational_institution'), item('living_cost_proof', anchor='국내 체류 비용 부담능력 입증서류'), item('guardian_docs', 'CONDITIONAL_REQUIRED', anchor='후견보증서, 관계 증명 자료 및 재정능력 입증서류(후견인이 변경되는 경우)', applies_when_ko='후견인이 변경되는 경우', applies_when_en='If the guardian changes', role='sponsor'), item('dorm_admission_cert', 'ALTERNATIVE_DOCUMENT', anchor='후견인 면제 대상자는 학교장 명의 ‘기숙사 입소확인서’ 제출', applies_when_ko='후견인 면제 대상자', applies_when_en='Guardian-exempt students', role='educational_institution'), residence()])
guidance('D-5', 'extension', section='취재(D-5) 체류기간 연장허가', anchor='② 재직증명서 또는 파견명령서(본사발행)',
         summary_ko='취재(D-5)는 신청서·여권·외국인등록증·수수료와 본사 발행 재직증명서 또는 파견명령서, 체류지 입증서류로 연장합니다.', summary_en='D-5 journalists extend with the form, passport, residence card, fee, a head-office certificate of employment or dispatch order and proof of residence.',
         docs=[item('app_form_34', anchor='① 신청서(별지34호 서식), 여권 및 외국인등록증, 수수료'), item('passport', anchor='① 신청서(별지34호 서식), 여권 및 외국인등록증, 수수료'), item('arc', anchor='① 신청서(별지34호 서식), 여권 및 외국인등록증, 수수료'), item('fee', anchor='① 신청서(별지34호 서식), 여권 및 외국인등록증, 수수료'), item('dispatch_or_cert_press', anchor='재직증명서 또는 파견명령서(본사발행)', role='employer'), residence(anchor='③체류지 입증서류')])
guidance('D-6', 'extension', section='종교(D-6) 체류기간 연장허가', anchor='②재직증명서 또는 파송명령서(파송단체 발행)',
         summary_ko='종교(D-6)는 신청서·여권·외국인등록증·수수료와 파송단체 발행 재직증명서 또는 파송명령서, 체류지 입증서류로 연장합니다.', summary_en='D-6 religious workers extend with the form, passport, residence card, fee, a certificate of employment or mission order from the sending body and proof of residence.',
         docs=[item('app_form_34', anchor='①신청서(별지34호 서식), 여권 및 외국인등록증, 수수료'), item('passport', anchor='①신청서(별지34호 서식), 여권 및 외국인등록증, 수수료'), item('arc', anchor='①신청서(별지34호 서식), 여권 및 외국인등록증, 수수료'), item('fee', anchor='①신청서(별지34호 서식), 여권 및 외국인등록증, 수수료'), item('dispatch_or_cert_religion', anchor='재직증명서 또는 파송명령서(파송단체 발행)', role='employer'), residence(anchor='③체류지 입증서')])
guidance('D-7', 'extension', scenario='branch-transferee', section='주재(D-7) 체류기간 연장허가 — 영 별표 1의 16. 주재(D-7)란의 “가”목 해당자', anchor='연락사무소 설치허가서 사본', doc_page_window=3,
         summary_ko='외국 본사에서 국내 지사·연락사무소로 파견된 주재원(“가”목)은 파견명령서 또는 본사 재직증명서, 지사·연락사무소 설치허가서 사본, 영업자금 도입 실적 증빙, 개인 납세사실 증명, 체류지 입증서류로 연장합니다. 급여를 해외 본사에서 받는 경우에도 국내 납세 증명이 요구됩니다.', summary_en='Transferees from a foreign head office to a Korean branch/liaison office (item “가”) extend with the dispatch order or head-office employment certificate, the branch/liaison establishment permit copy, proof of operating funds, personal tax-payment proof and proof of residence. Tax proof is required even when salary is paid abroad.',
         docs=[item('app_form_34', anchor='① 신청서(별지34호 서식), 여권 및 외국인등록증, 수수료'), item('passport', anchor='① 신청서(별지34호 서식), 여권 및 외국인등록증, 수수료'), item('arc', anchor='① 신청서(별지34호 서식), 여권 및 외국인등록증, 수수료'), item('fee', anchor='① 신청서(별지34호 서식), 여권 및 외국인등록증, 수수료'), item('dispatch_order_head', anchor='파견명령서(외국본사 발행)', role='employer'), item('branch_permit_copy', anchor='연락사무소 설치허가서 사본', role='employer'), item('operating_funds_proof', anchor='영업자금도입실적증빙서류', role='employer'), item('personal_tax_proof', anchor='개인 납세사실증명원 원본'), residence()])
guidance('D-8-1', 'extension', section='기업투자(D-8) — 1. 법인에 투자(D-8-1)한 외국인에 대한 체류기간 연장허가', anchor='1. 법인에 투자(D-8-1)한 외국인에 대한 체류기간 연장허가',
         summary_ko='법인 투자자(D-8-1)는 사업자등록증 사본·법인등기사항전부증명서·주주변동상황명세서, 투자기업등록증 사본, 투자자금 도입 입증서류, 납세 증명, 영업실적 증명, 사업장 존재 입증서류, 체류지 입증서류를 냅니다. 투자금 3억원 미만 개인투자자는 자본금 사용내역과 사업 경험 서류가 추가됩니다.', summary_en='Corporate investors (D-8-1) submit the business registration copy, corporate register and shareholder-change statement, FDI company registration copy, proof of investment funds, tax proof, business performance, proof of premises and proof of residence. Individual investors under KRW 300 million add capital-use records and business-experience documents.',
         docs=[item('app_form_34', anchor='① 신청서(별지34호 서식), 여권 및 외국인등록증, 표준규격사진1장'), item('passport', anchor='① 신청서(별지34호 서식), 여권 및 외국인등록증, 표준규격사진1장'), item('arc', anchor='① 신청서(별지34호 서식), 여권 및 외국인등록증, 표준규격사진1장'), item('photo1', anchor='표준규격사진1장'), item('corp_docs_d8', anchor='사업자등록증 사본, 법인등기사항전부증명서, 주주변동상황명세서 원본', role='business_entity'), item('fdi_company_reg_copy', anchor='③ 투자기업등록증 사본', role='business_entity'), item('dispatch_and_employment_d8', 'CONDITIONAL_REQUIRED', anchor='주재활동의 경우 파견명령서', applies_when_ko='주재활동(파견)인 경우', applies_when_en='Intra-company transferees', role='business_entity'), item('investment_funds_proof', anchor='투자자금 도입관련 입증서류'), item('vat_tax_docs', anchor='개인 납세사실 증명서류 또는 부가가치세 과세표준 확인증명 관련서류'), item('business_performance', anchor='영업실적(수출입실적 등) 증명서', role='business_entity'), item('premises_proof', anchor='사업장 존재 입증 서류', role='business_entity'), residence(), item('capital_use_proof', 'CONDITIONAL_REQUIRED', anchor='자본금 사용내역 입증서류', applies_when_ko='투자금액 3억원 미만 개인투자자', applies_when_en='Individual investors under KRW 300 million', role='business_entity'), item('home_country_business_docs', 'MAY_BE_REQUESTED_BY_OFFICER', anchor='해당 업종 또는 분야의 사업 경험 관련 국적국 서류 (필요시 징구)', applies_when_ko='투자금액 3억원 미만 개인투자자(필요 시)', applies_when_en='Individual investors under KRW 300 million (if requested)')])
guidance('D-8-2', 'extension', section='기업투자(D-8) — 2. 벤처 투자(D-8-2) 외국인에 체류기간 연장허가', anchor='2. 벤처 투자(D-8-2) 외국인에 체류기간 연장허가',
         summary_ko='벤처 투자자(D-8-2)는 사업자등록증·법인등기사항전부증명서, 벤처기업(예비벤처)확인서, 지식재산권 등 기술력 입증서류, 사업실적 입증서류, 납세증명서, 체류지 입증서류로 연장합니다.', summary_en='Venture investors (D-8-2) extend with the business registration and corporate register, the (pre-)venture company confirmation, proof of technology/IP, proof of business results, a tax clearance certificate and proof of residence.',
         docs=[item('app_form_34', anchor='① 신청서(별지34호 서식), 여권, 외국인등록증(해당자), 표준규격사진1장'), item('passport', anchor='① 신청서(별지34호 서식), 여권, 외국인등록증(해당자), 표준규격사진1장'), item('arc', 'ADDITIONAL_IF_APPLICABLE', anchor='외국인등록증(해당자)', applies_when_ko='해당자', applies_when_en='If applicable'), item('photo1', anchor='표준규격사진1장'), item('business_reg_corp_reg', anchor='② 사업자등록증 사본, 법인등기사항전부증명서', role='business_entity'), item('venture_docs', anchor='벤처기업확인서 또는 예비벤처기업확인서', role='business_entity'), item('ip_proof', anchor='지식재산권을 보유하는 등 우수한 기술력을 가지고 있음을 입증하는 서류', role='business_entity'), item('business_results_proof', anchor='⑤ 사업실적관련 입증서류', role='business_entity'), item('tax_clearance', anchor='⑥ 납세증명서', role='business_entity'), residence()])
guidance('D-9-1', 'extension', section='무역경영(D-9) — 1. 점수제 무역비자(D-9-1) 소지자의 기간연장', anchor='1. 점수제 무역비자(D-9-1) 소지자의 기간연장',
         summary_ko='점수제 무역비자(D-9-1)는 총 50점 중 필수항목 5점 이상이어야 연장되며, 사업자등록증·사업장 존재 입증서류, 주거지 입증서류, 무역실적(수출입실적증명서·수출실적증명원·온라인몰 거래내역 중 택1)·내국인 고용·납세실적 등 점수 입증서류를 냅니다.', summary_en='Points-based trade visa holders (D-9-1) need 5+ points on the mandatory items (of 50) and submit the business registration, proof of premises, proof of residence and points evidence — trade results (one of: import/export certificate, bank export certificate, online-mall records), Korean-employee insurance records and tax records.',
         docs=[item('app_form_34', anchor='신청서 (별지 제34호 서식), 여권, 외국인등록증, 수수료 등'), item('passport', anchor='신청서 (별지 제34호 서식), 여권, 외국인등록증, 수수료 등'), item('arc', anchor='신청서 (별지 제34호 서식), 여권, 외국인등록증, 수수료 등'), item('fee', anchor='신청서 (별지 제34호 서식), 여권, 외국인등록증, 수수료 등'), item('business_reg_copy', anchor='사업자등록증 사본, 사업장 존재 입증서류(임대차계약서 등)', role='business_entity'), item('premises_proof', anchor='사업장 존재 입증서류(임대차계약서 등)', role='business_entity'), residence(anchor='주거지 입증 서류 (임대차계약서, 월세 지급 입증서류 등)', alts=[{'ko': '임대차계약서', 'en': 'Lease contract'}, {'ko': '월세 지급 입증서류', 'en': 'Proof of rent payments'}]),
               item('points_docs', anchor='점수제 해당 점수 입증서류', notes_ko='무역실적 입증서류는 수출입실적증명서(한국무역협회·한국무역통계진흥원), 외국환은행 수출실적 증명원, 온라인몰 거래내역(미신고 내역 중 최대 40%) 중 하나를 냅니다.', notes_en='Trade results: one of the KITA/KTSPI import-export certificate, a bank export certificate or online-mall records (up to 40% of unreported trade).')])
guidance('E-1', 'extension', section='교수(E-1) 체류기간 연장허가', anchor='교원활용계획서, 수강생 현황, 근로소득원천징수부',
         summary_ko='교수(E-1)는 신청서·여권·사진·수수료와 고용계약서 원본·사본, 필요 시 교원활용계획서·수강생 현황·근로소득원천징수부 등 1~2종, 체류지 입증서류로 연장합니다.', summary_en='E-1 professors extend with the form, passport, photo, fee, the employment contract (original and copy), one or two supporting items if needed (faculty plan, student roster, withholding ledger) and proof of residence.',
         docs=[item('app_form_34', anchor='① 신청서(제 34호 서식), 여권, 표준규격사진 1장, 수수료'), item('passport', anchor='① 신청서(제 34호 서식), 여권, 표준규격사진 1장, 수수료'), item('photo1', anchor='표준규격사진 1장, 수수료'), item('fee', anchor='표준규격사진 1장, 수수료'), item('contract_original_copy', anchor='고용계약서 원본 및 사본', role='employer'), item('other_officer_docs', 'MAY_BE_REQUESTED_BY_OFFICER', anchor='기타 심사에 필요한 자료*(필요시 1~2종 제출)', role='employer'), residence()])
guidance('E-2', 'extension', section='회화지도(E-2) 체류기간 연장허가', anchor='학원설립운영등록증 사본(해당자)',
         summary_ko='회화지도(E-2)는 고용계약서 원본·사본, 사업자등록증 사본, 학원설립운영등록증 사본(해당자), 소득금액증명, 체류지 입증서류, 강의시간표로 연장합니다. 사업소득으로 신고된 경우 경정 청구가 필요하며, 교육부·시도교육감 초청 원어민 강사는 범죄경력·학력·신체검사 서류가 필요 없습니다.', summary_en='E-2 language instructors extend with the employment contract (original and copy), business registration copy, academy registration copy (if applicable), income certificate, proof of residence and teaching timetable. Income filed as business income must be corrected; instructors invited by the Ministry of Education or provincial offices skip criminal-record, degree and medical documents.',
         docs=[item('app_form_34', anchor='① 신청서(별지 34호서식), 여권 및 외국인등록증, 수수료'), item('passport', anchor='① 신청서(별지 34호서식), 여권 및 외국인등록증, 수수료'), item('arc', anchor='① 신청서(별지 34호서식), 여권 및 외국인등록증, 수수료'), item('fee', anchor='① 신청서(별지 34호서식), 여권 및 외국인등록증, 수수료'), item('contract_original_copy', anchor='② 고용계약서 원본 및 사본', role='employer'), item('business_reg_copy', anchor='③ 사업자등록증 사본', role='employer'), item('academy_reg_copy', 'ADDITIONAL_IF_APPLICABLE', anchor='학원설립운영등록증 사본(해당자)', applies_when_ko='학원 취업자', applies_when_en='Private academy employees', role='employer'), item('income_cert_simple', anchor='⑦ 소득금액증명'), residence(anchor='⑧ 체류지 입증서류'), item('timetable', anchor='⑨ 강의시간표', role='employer'), item('other_officer_docs', 'MAY_BE_REQUESTED_BY_OFFICER', anchor='범죄경력증명서 및 학력입증서류 보완대상인 기존 체류자의 경우에는 해당서류 보완 필요', notes_ko='범죄경력·학력 보완 대상자는 해당 서류를 보완해야 합니다.', notes_en='Holders flagged for criminal-record or degree supplementation must supply those documents.')])
guidance('E-3', 'extension', section='연구(E-3) 체류기간 연장허가', anchor='고용계약서 또는 임용예정확인서',
         summary_ko='연구(E-3)는 고용계약서 또는 임용예정확인서, 고용기관 설립 관련 서류, 체류지 입증서류로 연장하며, 해당자는 초청 공문·원 소속 고용계약 입증서류·은행 잔고증명서를 추가로 냅니다.', summary_en='E-3 researchers extend with the employment contract or appointment confirmation, institution establishment documents and proof of residence; where applicable add the invitation letter, home-institution contract proof and a bank balance certificate.',
         docs=[item('app_form_34', anchor='① 신청서(별지 34호서식), 여권 및 외국인등록증, 수수료'), item('passport', anchor='① 신청서(별지 34호서식), 여권 및 외국인등록증, 수수료'), item('arc', anchor='① 신청서(별지 34호서식), 여권 및 외국인등록증, 수수료'), item('fee', anchor='① 신청서(별지 34호서식), 여권 및 외국인등록증, 수수료'), item('contract_or_appointment', anchor='고용계약서 또는 임용예정확인서', role='employer'), item('institution_docs', anchor='고용기관 설립 관련 서류', role='employer'), residence(anchor='④ 체류지 입증서류(임대차계약서, 숙소제공 확인서)', alts=RESIDENCE_ALTS[:2]), item('other_officer_docs', 'ADDITIONAL_IF_APPLICABLE', anchor='초청 연구기관 명의의 초청 공문(해당자)', applies_when_ko='해당자: 초청 공문, 원 소속 고용계약 입증서류, 국내·외 은행 잔고증명서', applies_when_en='If applicable: invitation letter, home-institution contract proof, bank balance certificate')])
guidance('E-4', 'extension', section='기술지도(E-4) 체류기간 연장허가', anchor='② 파견명령서(본사발행) 또는 재직증명서 ③ 기술도입계약신고',
         summary_ko='기술지도(E-4)는 신청서·여권·외국인등록증·수수료와 본사 발행 파견명령서 또는 재직증명서, 기술도입계약 신고 관련 서류, 체류지 입증서류로 연장합니다.', summary_en='E-4 technical instructors extend with the form, passport, residence card, fee, a head-office dispatch order or employment certificate, the technology-import contract report and proof of residence.',
         completeness='PARTIALLY_STRUCTURED',
         docs=[item('app_form_34', anchor='① 신청서(별지 34호 서식), 여권 및 외국인등록증, 수수료'), item('passport', anchor='① 신청서(별지 34호 서식), 여권 및 외국인등록증, 수수료'), item('arc', anchor='① 신청서(별지 34호 서식), 여권 및 외국인등록증, 수수료'), item('fee', anchor='① 신청서(별지 34호 서식), 여권 및 외국인등록증, 수수료'), item('dispatch_or_employment_cert', anchor='파견명령서(본사발행) 또는 재직증명서', role='employer'), item('other_officer_docs', 'SOURCE_MENTIONS_BUT_NOT_STRUCTURED', anchor='기술도입계약신고', notes_ko='기술도입계약 신고 관련 서류와 이후 항목은 원문 페이지를 확인하세요.', notes_en='See the original page for the technology-import contract report and the remaining items.')])
guidance('E-5', 'extension', section='전문직업(E-5) 체류기간 연장허가', anchor='② 고용계약서 사본',
         summary_ko='전문직업(E-5)은 신청서·여권 원본·사진·수수료와 고용계약서 사본, 사업자등록증, 체류지 입증서류로 연장합니다.', summary_en='E-5 professionals extend with the form, original passport, photo, fee, a copy of the employment contract, the business registration and proof of residence.',
         docs=[item('app_form_34', anchor='① 신청서(별지34호 서식), 여권원본, 표준규격사진1장, 수수료'), item('passport_original', anchor='① 신청서(별지34호 서식), 여권원본, 표준규격사진1장, 수수료'), item('photo1', anchor='표준규격사진1장, 수수료'), item('fee', anchor='표준규격사진1장, 수수료'), item('employment_contract', anchor='② 고용계약서 사본', role='employer', original_or_copy='copy'), item('business_reg', anchor='‘부가가치세법’에 따른 사업자등록증', role='employer'), residence()])
guidance('E-6', 'extension', section='예술흥행(E-6) 체류기간 연장허가', anchor='② 고용추천서 또는 공연추천서',
         summary_ko='예술흥행(E-6)은 고용추천서 또는 공연추천서(영상물등급위원회·문화체육관광부·방송통신위원회 등), 고용(공연)계약서, 사업자등록증 사본, 체류지 입증서류로 연장하며 신원보증서는 E-6-2만 냅니다. 허가기간은 E-6-1·E-6-3이 근로계약기간+1개월(최대 2년), E-6-2는 공연추천·근로계약기간(최대 1년, 연소자 유해 판정 시 6개월)입니다.', summary_en='E-6 artists extend with an employment or performance recommendation (KMRB, Ministry of Culture, KCC etc.), the employment/performance contract, business registration copy and proof of residence; a letter of guarantee is required only for E-6-2. The period is contract + 1 month (max 2 years) for E-6-1/3 and the recommendation/contract period (max 1 year, 6 months if rated harmful to minors) for E-6-2.',
         period_ko='E-6-1·E-6-3: 근로계약기간+1개월(최대 2년) · E-6-2: 공연추천 또는 근로계약기간(최대 1년)', period_en='E-6-1/3: contract + 1 month (max 2 y) · E-6-2: recommendation/contract period (max 1 y)',
         docs=[item('app_form_34', anchor='① 신청서(별지 34호서식), 여권 및 외국인등록증, 수수료'), item('passport', anchor='① 신청서(별지 34호서식), 여권 및 외국인등록증, 수수료'), item('arc', anchor='① 신청서(별지 34호서식), 여권 및 외국인등록증, 수수료'), item('fee', anchor='① 신청서(별지 34호서식), 여권 및 외국인등록증, 수수료'), item('employment_recommendation', anchor='② 고용추천서 또는 공연추천서', role='employer'), item('contract_or_performance', anchor='③ 고용계약서 (또는 공연계약서)', role='employer'), item('business_reg_copy', anchor='④사업자등록증 사본', role='employer'), item('guarantor_e62', 'CONDITIONAL_REQUIRED', anchor='⑤신원보증서(E-6-2자격만 징구)', applies_when_ko='E-6-2(호텔·유흥) 자격인 경우', applies_when_en='E-6-2 (hotel/entertainment) only', role='employer'), residence(anchor='⑥ 체류지 입증서류')])
guidance('E-8', 'extension', section='계절근로(E-8) 체류기간 연장허가', anchor='외국인 계절근로자(E-8) 체류기간 연장 추천 신청서',
         summary_ko='계절근로자(E-8) 연장은 만료 60~40일 전에 관할 지방자치단체에 신청하면 지자체가 출입국에 일괄 신청하고, 40일 이내에는 지자체 추천서를 받아 본인이 신청합니다. 수수료는 면제이며 총 체류기간은 8개월을 넘을 수 없습니다.', summary_en='E-8 seasonal workers apply to the local government 60–40 days before expiry (the government files in bulk) or, within 40 days, obtain its recommendation and file themselves. No fee; total stay cannot exceed 8 months.',
         fee_ko='수수료 면제', fee_en='No fee', timing_ko='만료 60~40일 전 지자체 신청 · 40일 이내는 추천서 발급 후 출입국 신청', timing_en='60–40 days before expiry via the local government; within 40 days with its recommendation', filer='local_government',
         docs=[item('e8_extension_request', anchor='외국인 계절근로자(E-8) 체류기간 연장 추천 신청서', role='local_government'), item('passport_and_arc', anchor='② 여권 및 외국인등록증'), item('accommodation_confirmation', anchor='③ 거주/숙소 제공 확인서', role='employer', notes_ko='고용주의 등기부등본·임대차계약서 등 추가서류는 필요 없습니다.', notes_en='No further landlord documents are needed.'), item('labor_contract', anchor='④ 근로계약서', role='employer'), item('employer_id', anchor='⑤ 고용주 신분증', role='employer'), item('trafficking_indicator', anchor='⑥ 인신매매 피해 식별지표', role='local_government'), item('e8_extension_recommendation', 'CONDITIONAL_REQUIRED', anchor='⑦ 체류기간 만료 계절근로자 체류기간 연장 추천서', applies_when_ko='출입국·외국인관서에 직접 신청하는 경우(②~⑧)', applies_when_en='When filing at the immigration office yourself (items ②–⑧)', role='local_government'), item('app_form_34', 'CONDITIONAL_REQUIRED', anchor='⑧ 통합신청서', applies_when_ko='출입국·외국인관서에 직접 신청하는 경우', applies_when_en='When filing at the immigration office yourself')])
guidance('E-10', 'extension', section='선원취업(E-10) 체류기간 연장허가 — 1. 연장 기준 및 절차', anchor='1회 부여할 수 있는 선원취업자의 체류기간은 3년 이내로 하고 최초 입국 후 최대 3년까지 체류 허용',
         summary_ko='선원취업(E-10)은 1회 3년 이내, 최초 입국 후 최대 3년(재고용 시 4년 10개월)까지 허용되며, 고용계약서·사업자등록증 사본·신원보증서와 선원 고용추천서(E-10-1·3은 한국해운조합, E-10-2는 수협중앙회의 연장 추천서), 체류지 입증서류를 냅니다. 고용해지 후 구직 중이면 3개월 범위에서 수수료 없이 연장됩니다.', summary_en='E-10 seafarers get up to 3 years per grant and 3 years from first entry (4 y 10 m with re-employment), submitting the employment contract, business registration copy, letter of guarantee, the seafarer recommendation (KSA for E-10-1/3, NFFC extension recommendation for E-10-2) and proof of residence. Job seekers after termination get up to 3 months without fee.',
         period_ko='1회 3년 이내 · 최초 입국 후 최대 3년(재고용 4년 10개월)', period_en='Up to 3 years each; 3 years from first entry (4 y 10 m with re-employment)',
         docs=[item('app_form_34', anchor='① 신청서(별지 34호서식), 여권 및 외국인등록증, 수수료'), item('passport', anchor='① 신청서(별지 34호서식), 여권 및 외국인등록증, 수수료'), item('arc', anchor='① 신청서(별지 34호서식), 여권 및 외국인등록증, 수수료'), item('fee', anchor='① 신청서(별지 34호서식), 여권 및 외국인등록증, 수수료'), item('employment_contract', anchor='② 고용계약서 ③ 사업자등록증 사본 ④ 신원보증서', role='ship_owner'), item('business_reg_copy', anchor='② 고용계약서 ③ 사업자등록증 사본 ④ 신원보증서', role='ship_owner'), item('guarantor', anchor='② 고용계약서 ③ 사업자등록증 사본 ④ 신원보증서', role='ship_owner'), item('seafarer_recommendation', anchor='외국인선원 고용추천서(E-10-1, E-10-3, 한국해운조합), 선원취업활동기간연장 추천서(E-10-2, 수협중앙회)', role='ship_owner'), residence()])
guidance('E-10', 'extension', scenario='reemployment', section='선원취업(E-10) — 2. 선원취업기간 만료자 취업활동기간 연장 절차(재고용 특례)', anchor='선원취업기간 만료자 취업활동기간 연장 절차(재고용 특례)',
         summary_ko='최초 입국 후 3년 취업기간이 만료되었지만 고용주가 재고용을 희망하는 E-10-1·2·3 선원은 만료 2개월 전부터 신청하며, 지방해양수산청장 발급 고용추천서, 선원근로계약서, 사업자등록증 사본, 보증기간이 지난 경우 신원보증서, 체류지 입증서류를 냅니다. 총 체류는 최초 입국일로부터 4년 10개월을 넘을 수 없습니다.', summary_en='E-10-1/2/3 seafarers whose 3-year period expired but whose employer wants to re-hire apply from 2 months before expiry with the regional maritime office recommendation, seafarer contract, business registration copy, a new guarantee if the old one lapsed and proof of residence. Total stay cannot exceed 4 years 10 months from first entry.',
         timing_ko='체류기간 만료일 2개월 전부터 만료일까지', timing_en='From 2 months before expiry until the expiry date', period_ko='총 체류 최초 입국일로부터 4년 10개월 이내', period_en='Total stay within 4 years 10 months of first entry',
         docs=[item('app_form_34', anchor='① 신청서(별지 34호서식), 여권 및 외국인등록증, 수수료'), item('passport', anchor='① 신청서(별지 34호서식), 여권 및 외국인등록증, 수수료'), item('arc', anchor='① 신청서(별지 34호서식), 여권 및 외국인등록증, 수수료'), item('fee', anchor='① 신청서(별지 34호서식), 여권 및 외국인등록증, 수수료'), item('seafarer_recommendation_regional', anchor='외국인선원 고용추천서(지방해양수산청장 발급)', role='ship_owner'), item('seafarer_contract', anchor='③ 선원근로계약서 ④ 사업자등록증 사본', role='ship_owner'), item('business_reg_copy', anchor='③ 선원근로계약서 ④ 사업자등록증 사본', role='ship_owner'), item('guarantor_if_expired', 'CONDITIONAL_REQUIRED', anchor='신원보증서(보증기간 도과시)', applies_when_ko='기존 신원보증 기간이 지난 경우', applies_when_en='If the previous guarantee period has lapsed', role='ship_owner'), residence()])
guidance('F-5', 'extension', state='NOT_APPLICABLE', completeness='SOURCE_ONLY', section='영주(F-5) 체류기간 연장허가', anchor='출국한 날부터 2년 이내에 재입국하고자 하는 자에 대하여는 재입국허가 면제',
         summary_ko='영주(F-5)는 체류기간 연장허가가 해당사항 없음입니다. 출국일부터 2년 이내 재입국은 재입국허가가 면제되고, 2년을 넘기려면 만료 전 재외공관에서 재입국허가 연장(3개월 이내)이 필요합니다.', summary_en='Permanent residents (F-5) do not extend their stay. Re-entry within 2 years of departure is exempt from the permit; to stay abroad longer, extend the re-entry permit (up to 3 months) at a Korean mission before it expires.')
guidance('F-5', 'activities_outside_status', state='NOT_APPLICABLE', completeness='SOURCE_ONLY', section='영주(F-5) 체류자격외 활동', anchor='해당사항 없음', summary_ko='영주(F-5)는 체류자격외 활동허가가 해당사항 없음입니다.', summary_en='Activities-outside-status permission does not apply to F-5.')
guidance('F-5', 'workplace_change', state='NOT_APPLICABLE', completeness='SOURCE_ONLY', section='영주(F-5) 근무처의 변경․추가', anchor='해당사항 없음', summary_ko='영주(F-5)는 근무처 변경·추가 허가가 해당사항 없음입니다.', summary_en='Workplace change/addition does not apply to F-5.')
guidance('H-1', 'extension', completeness='PARTIALLY_STRUCTURED', section='관광취업(H-1) 체류기간 연장허가', anchor='입국한 날로부터 1년 범위 내에서 연장',
         summary_ko='관광취업(H-1)은 입국한 날로부터 1년 범위에서 연장되며, 협정에 따라 미국은 1년 6개월, 영국·캐나다는 2년까지 가능합니다. 제출서류는 매뉴얼에 별도로 나열되어 있지 않습니다.', summary_en='Working-holiday (H-1) stays are extended within one year of entry; by agreement the US allows 1 year 6 months and the UK and Canada 2 years. The manual does not list separate documents.',
         period_ko='입국일로부터 1년 · 미국 1년 6개월 · 영국·캐나다 2년', period_en='1 year from entry · US 1 y 6 m · UK/Canada 2 y',
         conditions_ko=['국적별 협정에 따라 상한이 다릅니다(미국 1년 6개월, 영국·캐나다 2년).'], conditions_en=['The cap depends on the nationality agreement (US 1 y 6 m; UK and Canada 2 y).'])
guidance('H-1', 'status_change', state='GENERALLY_NOT_PERMITTED', completeness='SOURCE_ONLY', section='관광취업(H-1) 체류자격 변경허가', anchor='(기준) 원칙적으로 자격변경 제한',
         summary_ko='관광취업(H-1)은 원칙적으로 체류자격 변경이 제한됩니다. 결혼이민(F-6)으로의 변경도 관광취업 지침에 따라 불가합니다.', summary_en='Status changes from H-1 are restricted in principle; changing to F-6 is not allowed under the working-holiday guidelines.')
guidance('H-2', 'extension', completeness='PARTIALLY_STRUCTURED', section='알기쉬운 외국국적동포 업무 매뉴얼 — 3. 방문취업제 체류관리 절차 □ 체류기간 연장허가', anchor='고용부에서 “취업기간 만료자 취업활동 기간연장 확인서”를 받은 경우 입국일(또는 체류자격변경허가일)로부터 4년 10개월 내에서 허가',
         summary_ko='방문취업(H-2) 사증은 2026-02-12부터 신규 발급이 중단되어 기존 소지자에게만 적용됩니다. 외국인등록 시 최대 3년이 부여되고, 고용노동부의 취업활동 기간연장 확인서를 받으면 입국일(또는 자격변경일)로부터 4년 10개월 안에서 연장됩니다. 2019-09-02 이전 사증 발급자와 체류 중인 사람은 연장 시 한국어능력 서류가 면제됩니다.', summary_en='H-2 visas stopped being newly issued on 2026-02-12, so this applies to existing holders only. Registration grants up to 3 years; with the Ministry of Employment and Labor\'s extension confirmation the stay can run to 4 years 10 months from entry (or status change). Holders issued before 2019-09-02 are exempt from the Korean-language proof on extension.',
         period_ko='등록 시 최대 3년 · 연장확인서 보유 시 4년 10개월', period_en='Up to 3 years on registration; 4 y 10 m with the extension confirmation',
         docs=[item('reemployment_extension_cert', 'CONDITIONAL_REQUIRED', anchor='고용부에서 “취업기간 만료자 취업활동 기간연장 확인서”를 받은 경우', applies_when_ko='취업활동 기간연장 확인서를 받은 경우', applies_when_en='If you hold the employment-period extension confirmation', role='employer')])
guidance('H-2', 'registration', completeness='PARTIALLY_STRUCTURED', section='알기쉬운 외국국적동포 업무 매뉴얼 — 3. 방문취업제 체류관리 절차 □ 먼저 외국인등록을 하여야 합니다', anchor='방문취업 사증으로 입국한 동포는 입국일로부터 90일 이내에 체류지 관할 출입국ㆍ외국인청(사무소ㆍ출장소)에 아래 서류를 준비하여 외국인등록을 신고',
         summary_ko='방문취업(H-2) 사증으로 입국한 동포는 입국일로부터 90일 이내에 체류지 관할 관서에 외국인등록을 합니다. 건강상태 확인 절차가 있습니다.', summary_en='Compatriots who entered on an H-2 visa register within 90 days of entry at the office for their address; a health-status check is part of the process.',
         timing_ko='입국일로부터 90일 이내', timing_en='Within 90 days of entry')

# ==========================================================================
# Procedure-state overrides read directly from the stay manual section
# headings ("해당사항 없음", "억제", "불가 원칙"). Anchored like everything else.
# ==========================================================================
STATE_OVERRIDES = [
    # code, procedure, state, anchor, ko, en
    ('D-1', 'status_grant', 'NOT_APPLICABLE', '해당사항 없음', '체류자격 부여는 해당사항 없음.', 'Status grant does not apply.'),
    ('D-2', 'status_grant', 'NOT_APPLICABLE', '해당사항 없음', '체류자격 부여는 해당사항 없음.', 'Status grant does not apply.'),
    ('D-2', 'workplace_change', 'NOT_APPLICABLE', '해당사항 없음', '근무처 변경·추가 허가 대상이 아닙니다. 학교 변경은 등록사항 변경신고로 처리합니다.', 'Workplace change does not apply; a change of school is a registration-information report.'),
    ('D-3', 'activities_outside_status', 'GENERALLY_NOT_PERMITTED', '원칙적으로 체류자격외 활동 억제', '기술연수(D-3)는 원칙적으로 체류자격외 활동이 억제됩니다.', 'Activities outside status are restrained in principle for D-3.'),
    ('D-3', 'workplace_change', 'NOT_APPLICABLE', '해당사항 없음', '근무처 변경·추가는 해당사항 없음.', 'Workplace change does not apply.'),
    ('D-3', 'status_grant', 'NOT_APPLICABLE', '해당사항 없음', '체류자격 부여는 해당사항 없음.', 'Status grant does not apply.'),
    ('D-3', 'status_change', 'GENERALLY_NOT_PERMITTED', '체류자격 변경 불가 원칙', '기술연수(D-3)는 체류자격 변경 불가가 원칙입니다.', 'Status change from D-3 is not allowed in principle.'),
    ('D-4', 'activities_outside_status', 'GENERALLY_NOT_PERMITTED', '원칙적으로 체류자격외 활동 억제(확인 필요)', '일반연수(D-4)는 원칙적으로 체류자격외 활동이 억제되며, 어학연수생의 시간제취업은 별도 요건(6개월 경과 등)을 따릅니다.', 'Activities outside status are restrained for D-4; language trainees\' part-time work follows separate conditions (6-month wait, etc.).'),
    ('D-4', 'workplace_change', 'NOT_APPLICABLE', '해당사항 없음', '근무처 변경·추가는 해당사항 없음.', 'Workplace change does not apply.'),
    ('D-4', 'status_grant', 'NOT_APPLICABLE', '해당사항 없음', '체류자격 부여는 해당사항 없음.', 'Status grant does not apply.'),
    ('D-5', 'status_grant', 'NOT_APPLICABLE', '해당사항 없음', '체류자격 부여는 해당사항 없음.', 'Status grant does not apply.'),
    ('D-6', 'status_grant', 'NOT_APPLICABLE', '해당사항 없음', '체류자격 부여는 해당사항 없음.', 'Status grant does not apply.'),
    ('D-6', 'status_change', 'EXCEPTION_ONLY', '【원칙적 불가 ➭ 예외적으로 아래의 경우만 가능】', '종교(D-6)로의 체류자격 변경은 원칙적으로 불가하며 매뉴얼이 정한 예외에만 허용됩니다.', 'Changing to D-6 is not allowed in principle; only the listed exceptions apply.'),
    ('D-7', 'status_grant', 'NOT_APPLICABLE', '해당사항 없음', '체류자격 부여는 해당사항 없음.', 'Status grant does not apply.'),
    ('D-8', 'status_grant', 'NOT_APPLICABLE', '해당사항 없음', '체류자격 부여는 해당사항 없음.', 'Status grant does not apply.'),
    ('D-8', 'workplace_change', 'NOT_APPLICABLE', '기업투자(D-8) 자격은 ‘근무처 변경․추가 허가(신고)’ 대상 아님 : 외국인등록사항 변경신고', '기업투자(D-8)는 근무처 변경·추가 허가 대상이 아니며 외국인등록사항 변경신고로 처리합니다.', 'D-8 is not subject to workplace-change permission; changes are filed as a registration-information report.'),
    ('D-9', 'status_grant', 'NOT_APPLICABLE', '해당사항 없음', '체류자격 부여는 해당사항 없음.', 'Status grant does not apply.'),
    ('D-10', 'workplace_change', 'NOT_APPLICABLE', '해당사항 없음', '근무처 변경·추가는 해당사항 없음.', 'Workplace change does not apply.'),
    ('D-10', 'status_grant', 'NOT_APPLICABLE', '해당사항 없음', '체류자격 부여는 해당사항 없음.', 'Status grant does not apply.'),
    ('E-1', 'status_grant', 'NOT_APPLICABLE', '해당사항 없음', '체류자격 부여는 해당사항 없음.', 'Status grant does not apply.'),
    ('E-2', 'status_grant', 'NOT_APPLICABLE', '해당사항 없음', '체류자격 부여는 해당사항 없음.', 'Status grant does not apply.'),
    ('E-3', 'status_grant', 'NOT_APPLICABLE', '해당사항 없음', '체류자격 부여는 해당사항 없음.', 'Status grant does not apply.'),
    ('E-4', 'status_grant', 'NOT_APPLICABLE', '해당사항 없음', '체류자격 부여는 해당사항 없음.', 'Status grant does not apply.'),
    ('E-5', 'status_grant', 'NOT_APPLICABLE', '해당사항 없음', '체류자격 부여는 해당사항 없음.', 'Status grant does not apply.'),
    ('E-6', 'status_grant', 'NOT_APPLICABLE', '해당사항 없음', '체류자격 부여는 해당사항 없음.', 'Status grant does not apply.'),
    ('E-6', 'status_change', 'CONDITIONAL', '세부자격 약호 E-6-1 및 E-6-3에 해당하는 경우 제한적으로 허용', '예술흥행(E-6)으로의 변경은 E-6-1·E-6-3에 한해 제한적으로 허용됩니다.', 'Changing to E-6 is allowed only in limited cases for E-6-1 and E-6-3.'),
    ('E-7', 'status_grant', 'NOT_APPLICABLE', '해당사항 없음', '체류자격 부여는 해당사항 없음.', 'Status grant does not apply.'),
    ('E-8', 'activities_outside_status', 'GENERALLY_NOT_PERMITTED', '계절근로자(C-4, E-8)는 계절근로 이외의 다른 활동을 위한 체류자격외 활동허가를 허용하지 않음', '계절근로자(E-8)는 계절근로 외 활동을 위한 체류자격외 활동허가가 허용되지 않습니다.', 'Seasonal workers (E-8) are not granted outside-status permission for activities other than seasonal work.'),
    ('E-8', 'workplace_change', 'CONDITIONAL', '근무처 추가는 허용되지 않음', '계절근로자의 근무처 변경(고용주 재배정)은 고용주 귀책 해지 등 정해진 사유에만 가능하고 근무처 추가는 허용되지 않습니다.', 'Seasonal workers may change employer only for listed reasons; adding a workplace is not allowed.'),
    ('E-9', 'activities_outside_status', 'GENERALLY_NOT_PERMITTED', '체류자격외 활동 억제', '비전문취업(E-9)은 체류자격외 활동이 억제됩니다.', 'Activities outside status are restrained for E-9.'),
    ('E-9', 'status_grant', 'NOT_APPLICABLE', '해당사항 없음', '체류자격 부여는 해당사항 없음.', 'Status grant does not apply.'),
    ('E-10', 'status_grant', 'NOT_APPLICABLE', '해당사항 없음', '체류자격 부여는 해당사항 없음.', 'Status grant does not apply.'),
    ('E-10', 'status_change', 'NOT_APPLICABLE', '해당사항 없음', '선원취업(E-10)으로의 체류자격 변경은 해당사항 없음.', 'Status change to E-10 does not apply.'),
    ('F-1', 'workplace_change', 'NOT_APPLICABLE', '해당사항 없음', '근무처 변경·추가는 해당사항 없음.', 'Workplace change does not apply.'),
    ('F-2', 'workplace_change', 'NOT_APPLICABLE', '해당사항 없음', '근무처 변경·추가는 해당사항 없음.', 'Workplace change does not apply.'),
    ('F-3', 'workplace_change', 'NOT_APPLICABLE', '해당사항 없음', '근무처 변경·추가는 해당사항 없음.', 'Workplace change does not apply.'),
    ('F-6', 'activities_outside_status', 'NOT_APPLICABLE', '체류자격 구분에 따른 취업활동의 제한을 받지 않음', '결혼이민(F-6)은 체류자격 구분에 따른 취업활동 제한을 받지 않아 별도 허가가 필요 없습니다.', 'F-6 holders face no status-based work restrictions, so no permission is needed.'),
    ('F-6', 'workplace_change', 'NOT_APPLICABLE', '해당사항 없음', '근무처 변경·추가는 해당사항 없음.', 'Workplace change does not apply.'),
    ('H-1', 'status_grant', 'NOT_APPLICABLE', '해당사항 없음', '체류자격 부여는 해당사항 없음.', 'Status grant does not apply.'),
]

# ==========================================================================
# Global conditional overlays (유의사항 / 공통사항)
# ==========================================================================
OVERLAYS = [
    {'id': 'domestic_doc_validity_3m', 'manual': STAY, 'anchor': '주민등록등본 등 국내에서 발급․제출하는 서류의 유효기간은 별도의 유효기간이 설정되지 않은 경우 발급일로부터 3개월 이내',
     'scope': {'domains': ['stay']}, 'kind': 'validity',
     'ko': '국내에서 발급된 서류(주민등록등본 등)는 별도 유효기간이 없으면 발급일로부터 3개월 이내여야 합니다.', 'en': 'Documents issued in Korea (resident registration etc.) must be no older than 3 months unless another validity applies.'},
    {'id': 'previously_submitted_omitted', 'manual': STAY, 'anchor': '이미 제출하여 등록외국인기록에 보관 중인 서류는 제출 생략',
     'scope': {'domains': ['stay']}, 'kind': 'exemption',
     'ko': '사증발급·체류자격 변경 등을 신청할 때 이미 제출해 등록외국인기록에 보관 중인 서류는 다시 내지 않아도 됩니다.', 'en': 'Documents already on file from an earlier visa or status application need not be submitted again.'},
    {'id': 'foreign_doc_apostille', 'manual': STAY, 'anchor': '해외에서 발급된 서류는 자국 정부의 아포스티유(Apostille) 확인 또는 주재국 대한민국 공관의 영사확인을 받아 첨부',
     'scope': {'domains': ['stay', 'visa']}, 'kind': 'authentication',
     'ko': '해외에서 발급된 서류는 자국 정부의 아포스티유 또는 주재국 대한민국 공관의 영사확인을 받아야 합니다.', 'en': 'Documents issued abroad need an apostille from the issuing country or consular confirmation by the Korean mission there.'},
    {'id': 'admin_info_sharing', 'manual': STAY, 'anchor': '전자정부법 제36조 제1항에 따른 행정정보의 공동이용을 통하여 정보의 내용을 확인할 수 있는 경우에는 제출하지 아니함',
     'scope': {'domains': ['stay', 'visa']}, 'kind': 'exemption',
     'ko': '주민등록등본·가족관계증명서·사업자등록증·납세사실증명 등 행정정보 공동이용으로 확인할 수 있는 서류는 동의하면 제출을 생략할 수 있습니다.', 'en': 'Resident registration, family-relation certificates, business registration and tax records can be checked through administrative information sharing if you consent, so they need not be submitted.'},
    {'id': 'sealed_medical_docs', 'manual': STAY, 'anchor': '건강진단서, 마약검사확인서 및 채용신체검사서 등의 서류는 발급한 의료기관에서 봉투에 밀봉된 상태로 제출',
     'scope': {'domains': ['stay']}, 'kind': 'format',
     'ko': '건강진단서·마약검사확인서·채용신체검사서는 발급 의료기관이 밀봉한 상태로 제출해야 합니다(개봉 불가).', 'en': 'Health, drug-test and pre-employment medical certificates must be submitted sealed by the issuing institution.'},
    {'id': 'must_be_in_korea', 'manual': STAY, 'anchor': '각종 체류허가 신청을 하고자 하는 외국인은 반드시 국내에 체류 중에 있어야 하며',
     'scope': {'domains': ['stay']}, 'kind': 'presence',
     'ko': '체류허가는 국내에 체류 중일 때만 신청할 수 있고, 신청 후 출국하면 불허될 수 있습니다. 출국 중에는 대행기관 신청도 할 수 없습니다.', 'en': 'Stay permits can only be applied for while you are in Korea; leaving after filing may lead to refusal, and agencies cannot file for someone abroad.'},
    {'id': 'fees_non_refundable', 'manual': STAY, 'anchor': '수수료는 심사수수료로써 민원이 접수되면 반환되지 않음',
     'scope': {'domains': ['stay']}, 'kind': 'fee',
     'ko': '체류허가 수수료는 심사수수료이므로 접수 후에는 반환되지 않습니다.', 'en': 'Permit fees are examination fees and are not refunded once the application is accepted.'},
    {'id': 'fee_table', 'manual': STAY, 'anchor': '각종 체류허가 등에 관한 심사수수료', 'scope': {'domains': ['stay']}, 'kind': 'fee',
     'table': [{'procedure': 'activities_outside_status', 'ko': '12만원', 'en': 'KRW 120,000'}, {'procedure': 'workplace_change', 'ko': '12만원', 'en': 'KRW 120,000'}, {'procedure': 'status_grant', 'ko': '8만원 (결혼이민 F-6: 4만원)', 'en': 'KRW 80,000 (F-6: 40,000)'}, {'procedure': 'status_change', 'ko': '10만원 (영주 F-5 변경: 20만원)', 'en': 'KRW 100,000 (to F-5: 200,000)'}, {'procedure': 'extension', 'ko': '6만원 (결혼이민 F-6: 3만원)', 'en': 'KRW 60,000 (F-6: 30,000)'}, {'procedure': 'reentry', 'ko': '단수 3만원 · 복수 5만원', 'en': 'Single KRW 30,000 · multiple 50,000'}, {'procedure': 'registration', 'ko': '외국인등록증 발급·재발급 3만 5천원', 'en': 'Card issue/reissue KRW 35,000'}, {'procedure': 'card_reissue', 'ko': '3만 5천원', 'en': 'KRW 35,000'}],
     'ko': '체류허가 수수료는 출입국관리법 시행규칙 제72조에 따릅니다.', 'en': 'Fees follow Article 72 of the Immigration Act Enforcement Rule.'},
    {'id': 'passport_validity_cap', 'manual': STAY, 'anchor': '여권 유효기간 범위 내 체류기간 부여 안내',
     'scope': {'domains': ['stay'], 'procedures': ['status_grant', 'extension', 'status_change', 'workplace_change'], 'exclude_codes': ['A-1', 'A-2', 'A-3', 'F-5', 'F-2-4', 'F-1-16', 'G-1']}, 'kind': 'period',
     'ko': '체류기간은 원칙적으로 여권 유효기간 범위 안에서 부여됩니다. 여권 재발급이 사실상 불가능하면 1회에 한해 유효기간을 6개월로 간주할 수 있습니다.', 'en': 'The period of stay is granted within the passport validity; if renewal is impossible, validity may be treated as 6 months once.'},
    {'id': 'occupation_income_report', 'manual': STAY, 'anchor': '취업할 수 있는 체류자격 외국인의 직업 및 연간소득금액 신고 의무',
     'scope': {'domains': ['stay'], 'procedures': ['registration', 'status_change', 'activities_outside_status', 'workplace_change', 'status_grant', 'extension'], 'include_parents': ['D-7', 'D-8', 'D-9', 'E-1', 'E-2', 'E-3', 'E-4', 'E-5', 'E-6', 'E-7', 'E-8', 'E-9', 'E-10', 'F-2', 'F-4', 'F-6', 'H-2']}, 'kind': 'report',
     'ko': '취업 가능 체류자격자는 외국인등록과 각종 체류허가 신청 시 「외국인 직업 신고서」로 직업을, 통합신청서의 연 소득금액란으로 연간소득을 신고합니다(F-4는 소득 기재 불요). 소득금액증명은 국세청 연계로 제출이 생략됩니다.', 'en': 'Holders of work-eligible statuses report their occupation (occupation report form) and annual income (on the integrated form) at registration and every permit application (F-4 skips income). The income certificate is checked with the tax office, not submitted.'},
    {'id': 'school_enrollment_6_18', 'manual': STAY, 'anchor': '만 6세 이상 만 18세 이하 체류외국인의 재학증명서 제출 의무',
     'scope': {'domains': ['stay'], 'procedures': ['registration', 'status_change', 'activities_outside_status', 'workplace_change', 'status_grant', 'extension'], 'age_range': [6, 18]}, 'kind': 'report',
     'ko': '만 6세 이상 18세 이하 신청인은 통합신청서의 재학 여부란을 기재하고, 재학 중이면 재학증명서를 냅니다(미취학은 표시만).', 'en': 'Applicants aged 6 to 18 fill in the school-enrollment field and, if enrolled, attach an enrollment certificate.'},
    {'id': 'tb_certificate', 'manual': STAY, 'anchor': '외국인 결핵진단서 제출 의무 관련 안내',
     'scope': {'domains': ['stay', 'visa'], 'procedures': ['visa_issuance', 'registration', 'status_change', 'extension'], 'exclude_codes': ['A-1', 'A-2', 'A-3']}, 'kind': 'document',
     'ko': '결핵 고위험국가(35개국) 국민은 장기체류 사증 신청, 전자사증 입국 후 외국인등록, 단기→장기 자격변경, 2016-03-02 이후 결핵진단서를 낸 적이 없는 경우, 최근 1년 내 고위험국가에서 연속 6개월 이상 체류한 뒤의 연장·변경 시 결핵진단서를 냅니다. A-1~A-3, 만 6세 미만, 임신부, 거동 불가자는 제외됩니다.', 'en': 'Nationals of the 35 TB high-risk countries submit a TB certificate for long-term visas, at registration after an e-visa entry, for short-to-long status changes, if none was filed since 2016-03-02, and for extensions or changes after 6+ consecutive months in a high-risk country in the past year. A-1~A-3, children under 6, pregnant women and the immobile are exempt.'},
    {'id': 'officer_discretion', 'manual': STAY, 'anchor': '출입국·외국인청(사무소·출장소)장은 심사를 위해 특히 필요하다고 인정되는 때에는 본 매뉴얼상의 제출서류를 가감할 수 있으며',
     'scope': {'domains': ['stay', 'visa']}, 'kind': 'discretion', 'ko': OFFICER_NOTE_KO, 'en': OFFICER_NOTE_EN},
    {'id': 'guarantee_4y_cap', 'manual': STAY, 'anchor': '신원보증서의 보증기간이 4년 이상인 때에도 4년을 한도로 하여 이를 인정하며',
     'scope': {'domains': ['stay', 'visa'], 'requires_doc': 'guarantor'}, 'kind': 'validity',
     'ko': '신원보증서의 보증기간은 최대 4년까지만 인정되며, 허가기간은 보증기간을 넘을 수 없습니다.', 'en': 'A letter of guarantee counts for at most 4 years, and the permit cannot exceed the guarantee period.'},
]

# ==========================================================================
# Status transitions (current status is a first-class input)
# ==========================================================================
SHORT_STAY = ['B-1', 'B-2', 'C-1', 'C-3', 'C-4']
TRANSITIONS = [
    {'id': 'to-F-6-1', 'to': 'F-6-1', 'procedure': 'status_change', 'manual': STAY,
     'anchor': '국내 합법체류자 중 국민의 배우자(F-6-1) 자격으로 변경하려는 사람',
     'from_allowed_ko': '국내 합법체류 중인 장기체류자격 소지자', 'from_allowed_en': 'Lawful long-term residents in Korea',
     'exclusions': [
         {'from': SHORT_STAY, 'class': 'SHORT_STAY', 'state': 'GENERALLY_NOT_PERMITTED', 'anchor': '단기사증 입국자 : 사증면제(B-1)․관광통과(B-2) 및 일시취재(C-1)부터 단기취업(C-4)까지의 사증 소지자',
          'ko': '단기사증(B-1·B-2, C-1~C-4) 입국자는 원칙적으로 국내에서 F-6-1로 변경할 수 없고 출국 후 재외공관에서 사증을 받아야 합니다.', 'en': 'Short-stay entrants (B-1/B-2, C-1~C-4) cannot normally change to F-6-1 in Korea; they must leave and obtain a visa abroad.',
          'exceptions': [{'anchor': '사증면제(B-1) 자격으로 입국한 독일인은 결혼이민(F-6) 체류자격 변경 가능', 'ko': '사증면제(B-1)로 입국한 독일인은 변경할 수 있습니다.', 'en': 'German nationals who entered on B-1 may change.'},
                         {'anchor': '임신․출산 또는 부부사이에서 출생한 자녀(양자, 친양자 제외) 양육 등의 사유로 국내에서 체류자격 변경이 불가피하다고 판단되는 경우에는 심사 후', 'ko': '임신·출산이나 부부 사이 출생 자녀 양육 등으로 국내 변경이 불가피하면 심사 후 허가될 수 있습니다.', 'en': 'Pregnancy, childbirth or raising a child of the marriage may justify an in-country change after review.'}]},
         {'from': ['H-1'], 'class': 'H-1', 'state': 'GENERALLY_NOT_PERMITTED', 'anchor': '관광취업(H-1) 자격으로 국내에 체류하는 사람은 ｢관광취업(H-1) 자격 사증발급 및 체류관리 지침｣에 따라 결혼이민(F-6)으로 체류자격 변경 불가',
          'ko': '관광취업(H-1) 체류자는 결혼이민(F-6)으로 변경할 수 없습니다.', 'en': 'Working-holiday (H-1) holders cannot change to F-6.', 'exceptions': []},
         {'from': ['ILLEGAL'], 'class': 'ILLEGAL', 'state': 'GENERALLY_NOT_PERMITTED', 'anchor': '불법체류자(밀입국자, 위･변조여권행사자 포함)', 'ko': '불법체류자(밀입국·위변조여권 포함)와 출국을 위한 연장을 받은 사람은 변경 대상이 아닙니다.', 'en': 'Overstayers (incl. illegal entrants) and people on a departure extension are not eligible.', 'exceptions': []},
     ],
     'period_ko': '1년 이내', 'period_en': 'Up to 1 year',
     'documents_note_ko': '제출서류는 국민의 배우자(F-6-1) 사증발급 시 제출서류를 준용하며 접수·심사 과정에서 가감될 수 있습니다. 세부 체크리스트(국제결혼 안내프로그램 대상 국가 여부에 따라 다름)는 원문 표를 확인하세요.', 'documents_note_en': 'The documents follow the F-6-1 visa issuance list and may be adjusted during review. The detailed checklist (which differs for international-marriage program countries) is in the original table.',
     'documents_state': 'SOURCE_ONLY'},
    {'id': 'to-F-2-7', 'to': 'F-2-7', 'procedure': 'status_change', 'manual': STAY, 'anchor': '5. 점수제 우수인재 및 동반가족의 거주자격 변경허가',
     'from_allowed_ko': '국내 합법체류 외국인(호텔·관광유흥업소 종사자 E-6-2, 준전문·일반기능·숙련기능인력 E-7-2~E-7-4 제외)', 'from_allowed_en': 'Lawful residents (excluding E-6-2 entertainment workers and E-7-2~E-7-4 semi-professional/skilled workers)',
     'exclusions': [{'from': ['E-6-2', 'E-7-2', 'E-7-3', 'E-7-4'], 'class': 'EXCLUDED_WORKERS', 'state': 'GENERALLY_NOT_PERMITTED', 'anchor': '*호텔·관광유흥업소 종사자(E-6-2), 준전문·일반기능·숙련기능인력(E-7-2 ~ E-7-4) 제외', 'ko': 'E-6-2, E-7-2~E-7-4 체류자는 점수제 우수인재 변경 대상에서 제외됩니다.', 'en': 'E-6-2 and E-7-2~E-7-4 holders are excluded.', 'exceptions': []}],
     'documents_state': 'SOURCE_ONLY', 'documents_note_ko': '점수표와 제출서류는 원문(거주 F-2 체류자격 변경허가 5항)을 확인하세요.', 'documents_note_en': 'See the original points table and document list (F-2 status change, item 5).'},
    {'id': 'to-F-2-R', 'to': 'F-2-R', 'procedure': 'status_change', 'manual': STAY, 'anchor': 'Ⅱ. 지역특화형 우수인재(F-2) (인구감소지역)',
     'from_allowed_ko': '국내 합법 체류외국인', 'from_allowed_en': 'Lawful residents in Korea',
     'exclusions': [{'from': ['D-3', 'D-4', 'E-6-2', 'E-8', 'E-9', 'E-10', 'G-1', 'H-1'], 'class': 'EXCLUDED_STATUSES', 'state': 'GENERALLY_NOT_PERMITTED', 'anchor': '기술연수(D-3), 일반연수(D-4), 호텔유흥(E-6-2), 계절근로(E-8), 비전문취업(E-9), 선원취업(E-10), 기타(G-1), 관광취업(H-1)', 'ko': 'D-3, D-4, E-6-2, E-8, E-9, E-10, G-1, H-1 체류자(및 직전 자격이 이에 해당하는 D-10 체류자)는 제외됩니다.', 'en': 'D-3, D-4, E-6-2, E-8, E-9, E-10, G-1 and H-1 holders (and D-10 holders whose previous status was one of these) are excluded.', 'exceptions': []},
                    {'from': ['SHORT_STAY'], 'class': 'SHORT_STAY', 'state': 'GENERALLY_NOT_PERMITTED', 'anchor': '단기체류자격을 소지한', 'ko': '단기체류자격 소지자는 제외됩니다.', 'en': 'Short-stay holders are excluded.', 'exceptions': []}],
     'conditions_ko': ['최근 5년 이내 지역특화형 비자 또는 동반가족 자격으로 체류한 사람은 제외됩니다.', '학력 또는 소득요건과 지자체장의 추천이 필요합니다.'], 'conditions_en': ['Excluded if you held a regional visa or dependant status in the past 5 years.', 'Education or income requirements plus a local-government recommendation apply.'],
     'documents_state': 'SOURCE_ONLY'},
    {'id': 'to-E-7-4R-from-E-7-4', 'to': 'E-7-4R', 'procedure': 'extension', 'manual': STAY, 'anchor': '현 근무처가 인구감소지역 또는 인구감소관심지역인 숙련기능인력(E-7-4)으로서 동일 근무처에서 계속하여 근무하려는 사람은 광역지자체장의 추천서를 발급받아 체류기간 연장 시 지역특화형 숙련기능인력(E-7-4R)으로 전환 가능',
     'from_allowed_ko': '인구감소(관심)지역 근무처의 숙련기능인력(E-7-4)', 'from_allowed_en': 'E-7-4 skilled workers whose workplace is in a depopulation (or at-risk) area', 'exclusions': [],
     'conditions_ko': ['광역지자체장의 추천서를 받아 체류기간 연장 시 세부약호만 E-7-4 → E-7-4R로 바뀌며 체류자격 변경허가 대상이 아닙니다.'], 'conditions_en': ['With the provincial recommendation the subcode changes from E-7-4 to E-7-4R at extension; it is not a status change.'], 'documents_state': 'SOURCE_ONLY'},
    {'id': 'D-2-to-D-10-1', 'to': 'D-10-1', 'procedure': 'status_change', 'manual': STAY, 'anchor': '(국내 대학 졸업 후 최초 구직 자격 변경)',
     'from_allowed_ko': '국내 대학 전문학사 이상 학위과정 유학생(D-2)', 'from_allowed_en': 'D-2 students who earned an associate degree or higher at a Korean university', 'exclusions': [],
     'conditions_ko': ['국내 대학 졸업 후 최초로 구직(D-10-1)으로 변경할 때는 점수제가 적용되지 않습니다(과거 D-10을 받은 사람은 제외).'], 'conditions_en': ['The first change from D-2 to D-10-1 after graduating in Korea is exempt from the points system (not for people who previously held D-10).'], 'documents_state': 'SOURCE_ONLY'},
    {'id': 'G-1-to-E-9-recovery', 'to': 'E-9', 'procedure': 'status_change', 'manual': STAY, 'anchor': '기타(G-1) 자격 소지자의 비전문취업(E-9) 자격 회복절차',
     'from_allowed_ko': '산업재해 치료 등으로 기타(G-1)로 변경했던 고용허가제 근로자(체류기간 상한 미도래)', 'from_allowed_en': 'EPS workers who switched to G-1 for accident treatment and have not reached the stay cap', 'exclusions': [], 'documents_state': 'SOURCE_ONLY'},
    {'id': 'F-1-1-legacy-to-F-2-2', 'to': 'F-2-2', 'procedure': 'status_change', 'manual': STAY, 'anchor': '기존 방문동거(F-1-1)자격으로 체류하고 있는 국민의 미성년 외국인 자녀에 대해서는 확인즉시 수수료 없이 거주(F-2-2)자격 변경',
     'from_allowed_ko': '기존 방문동거(F-1-1)로 체류 중인 국민의 미성년 외국인 자녀', 'from_allowed_en': 'Minor foreign children of Korean nationals still staying as legacy F-1-1', 'exclusions': [],
     'conditions_ko': ['확인 즉시 수수료 없이 거주(F-2-2)로 변경됩니다.'], 'conditions_en': ['Converted to F-2-2 without fee as soon as confirmed.'], 'documents_state': 'SOURCE_ONLY', 'legacy': True},
    {'id': 'F-2-7-to-D-10', 'to': 'D-10', 'procedure': 'status_change', 'manual': STAY, 'anchor': '다음 요건을 갖춘 주체류자는 구직(D-10) 체류자격으로 변경 허가 가능',
     'from_allowed_ko': '실직 또는 최저임금 이하 소득으로 연장이 어려운 점수제 우수인재(F-2-7)', 'from_allowed_en': 'F-2-7 residents who are unemployed or below minimum wage', 'exclusions': [],
     'conditions_ko': ['구직(D-10)으로는 최대 1년 체류(추가 연장 불가), 가족은 동반(F-3)으로 변경 가능.'], 'conditions_en': ['Up to 1 year as D-10 (no further extension); family may change to F-3.'], 'documents_state': 'SOURCE_ONLY'},
]

# ==========================================================================
# Families: resolver dimensions. Options map to targets (subcodes or scenario
# ids). A dimension is asked only when the procedure is in `procedures` and
# its options still lead to more than one distinct guidance outcome.
# ==========================================================================
def opt(id_, ko, en, targets, aliases=None, hint_ko=None, hint_en=None):
    return {'id': id_, 'ko': ko, 'en': en, 'targets': targets, 'aliases': aliases or [], 'hint_ko': hint_ko, 'hint_en': hint_en}


def dim(id_, q_ko, q_en, options, procedures=None, kind='reason', unsure_ko=None, unsure_en=None):
    return {'id': id_, 'kind': kind, 'question_ko': q_ko, 'question_en': q_en, 'procedures': procedures, 'options': options,
            'unsure_ko': unsure_ko, 'unsure_en': unsure_en}


FAMILIES = {
    'F-1': {'dimensions': [
        dim('stay_reason', 'F-1(방문동거)을 어떤 이유로 받으셨어요?', 'Why were you given F-1 (visiting / family stay)?', [
            opt('relative', '국내 친척·가족을 방문하거나 함께 살기 위해', 'To visit or live with relatives in Korea', ['F-1~relative-visit', 'F-1~dongpo-first-generation'], ['친척', '가족방문', '동거']),
            opt('marriage_family', '결혼이민자(한국인과 결혼한 가족)를 돕기 위해 온 부모·가족', 'Parent or family member of a marriage migrant, here to help', ['F-1-5', 'F-1-28'], ['결혼이민자 부모', '양육', '손자']),
            opt('student_parent', '초·중·고 유학생인 자녀의 부모', 'Parent of a K-12 student in Korea', ['F-1-13'], ['유학생 부모', '자녀 유학']),
            opt('talent_family', '우수인재·투자자·유학생의 부모 또는 점수제 우수인재(F-2-7)의 가족', 'Parent of talent/investor/student, or family of an F-2-7 points-system resident', ['F-1~parent-of-talent-investor-student', 'F-1-12'], ['우수인재', '투자자 부모', 'F-2-7 가족']),
            opt('helper', '가사보조인 또는 외국공관원의 동거인', 'Domestic helper, or cohabitant of foreign mission staff', ['F-1~domestic-helper', 'F-1~diplomat-household'], ['가사보조', '공관']),
            opt('marriage_ended', '한국인 배우자와 혼인이 끝난 뒤 가사정리 중', 'Settling affairs after a marriage to a Korean ended', ['F-1-6'], ['이혼', '가사정리', '혼인단절']),
            opt('refugee_family', '난민인정자의 배우자·자녀', 'Spouse or child of a recognised refugee', ['F-1-16'], ['난민']),
            opt('child_cases', '결혼이민자의 전혼 자녀 또는 국제입양 절차 중인 아동', 'Child from a marriage migrant\'s previous marriage, or child in an international adoption', ['F-1-52', 'F-1-51'], ['전혼', '입양']),
            opt('workation', '디지털노마드(워케이션)', 'Digital nomad / workation', ['F-1-D'], ['워케이션', '노마드', 'workation', 'nomad']),
        ], procedures=['extension'], unsure_ko='외국인등록증 앞면의 체류자격란에 F-1 뒤에 숫자나 글자가 있으면 그 코드로 검색해 보세요. 모르면 아래에서 가장 가까운 상황을 고르거나 관할 출입국·외국인관서(1345)에 확인하세요.', unsure_en='Check the status field on your residence card: if a number or letter follows F-1, search that code. Otherwise pick the closest situation below or confirm with the immigration office (1345).'),
        dim('relative_kind', '어느 쪽에 가까우세요?', 'Which is closer to your case?', [
            opt('general', '일반 친·인척 방문', 'General visit to relatives', ['F-1~relative-visit']),
            opt('dongpo', '중국동포 1세 또는 그 존비속의 친척 방문', 'First-generation Chinese-Korean compatriot (or descendant) visiting relatives', ['F-1~dongpo-first-generation'], ['동포']),
        ], procedures=['extension']),
        dim('marriage_family_kind', '초청한 가족은 누구인가요?', 'Who invited you?', [
            opt('marriage_migrant', '한국인과 결혼해 F-6 등으로 체류 중인 결혼이민자', 'A marriage migrant (F-6 etc.) married to a Korean', ['F-1-5']),
            opt('naturalized', '귀화해서 한국 국적을 취득한 가족', 'A family member who naturalised as Korean', ['F-1-28'], ['귀화']),
        ], procedures=['extension']),
        dim('f15_phase', '이번 신청은 어떤 단계인가요?', 'Which stage is this application?', [
            opt('first', '입국 후 외국인등록과 함께 하는 첫 연장', 'First extension, filed with registration after entry', ['F-1-5#first-extension-childcare', 'F-1-5#first-extension-humanitarian']),
            opt('subsequent', '이미 F-1-5로 체류 중이고 다시 연장', 'Already staying as F-1-5, extending again', ['F-1-5#extension-childcare', 'F-1-5#extension-humanitarian']),
        ], procedures=['extension'], kind='phase'),
        dim('f15_purpose', '초청 목적은 무엇이었나요?', 'What was the purpose of the invitation?', [
            opt('childcare', '자녀(손자녀) 양육 지원', 'Helping raise the child', ['F-1-5#first-extension-childcare', 'F-1-5#extension-childcare'], ['양육']),
            opt('humanitarian', '중증질환·중증장애가 있는 가정 지원', 'Supporting a household with severe illness or disability', ['F-1-5#first-extension-humanitarian', 'F-1-5#extension-humanitarian'], ['질환', '장애']),
        ], procedures=['extension']),
        dim('talent_family_kind', '어느 쪽에 해당하나요?', 'Which applies?', [
            opt('parent', '우수인재·투자자·유학생의 부모', 'Parent of talent, investor or student', ['F-1~parent-of-talent-investor-student']),
            opt('f27_family', '점수제 우수인재(F-2-7)의 배우자·미성년 자녀', 'Spouse or minor child of an F-2-7 resident', ['F-1-12']),
        ], procedures=['extension']),
        dim('helper_kind', '어느 쪽에 해당하나요?', 'Which applies?', [
            opt('investor_helper', '외국인투자자·우수전문인력의 가사보조인', 'Domestic helper of a foreign investor / top professional', ['F-1~domestic-helper']),
            opt('diplomat', '주한외국공관원의 비세대동거인·가사보조인', 'Cohabitant or helper of foreign mission staff', ['F-1~diplomat-household']),
        ], procedures=['extension']),
        dim('child_kind', '어느 쪽에 해당하나요?', 'Which applies?', [
            opt('prev_marriage', '결혼이민자의 전혼관계 출생 자녀', 'Child from the marriage migrant\'s previous marriage', ['F-1-52']),
            opt('adoption', '국제입양 절차 중인 아동', 'Child in an international adoption', ['F-1-51']),
        ], procedures=['extension']),
    ]},
    'D-2': {'dimensions': [
        dim('course', '어떤 과정에 재학 중이세요?', 'Which course are you enrolled in?', [
            opt('degree', '학위과정 (전문학사·학사·석사·박사)', 'Degree course (associate, bachelor, master, doctorate)', ['D-2-1', 'D-2-2', 'D-2-3', 'D-2-4'], ['학사', '석사', '박사', '전문학사', '대학원']),
            opt('research', '연구과정', 'Research course', ['D-2-5'], ['연구']),
            opt('exchange', '교환학생 또는 방문학생', 'Exchange or visiting student', ['D-2-6', 'D-2-8'], ['교환', '방문학생']),
            opt('work_study', '일-학습연계 유학', 'Work-study linked program', ['D-2-7'], ['일학습']),
        ], procedures=['extension', 'part_time_work'], unsure_ko='재학증명서나 외국인등록증의 체류자격란(D-2-1~D-2-8)을 확인해 보세요.', unsure_en='Check your enrollment certificate or the status field on your residence card (D-2-1 to D-2-8).'),
        dim('exchange_kind', '교환학생인가요, 방문학생인가요?', 'Exchange student or visiting student?', [
            opt('exchange', '교환학생', 'Exchange student', ['D-2-6']), opt('visiting', '방문학생', 'Visiting student', ['D-2-8']),
        ], procedures=['part_time_work']),
    ]},
    'E-9': {'dimensions': [
        dim('industry', '어떤 업종에서 일하세요?', 'Which industry do you work in?', [
            opt('manufacturing', '제조업', 'Manufacturing', ['E-9-1'], ['제조', '공장', 'factory', 'manufacturing']),
            opt('construction', '건설업', 'Construction', ['E-9-2'], ['건설', 'construction']),
            opt('agriculture', '농축산업', 'Agriculture and livestock', ['E-9-3'], ['농업', '농장', '축산', 'farm']),
            opt('fishery', '어업', 'Fishery', ['E-9-4'], ['어업', '어선', '양식', 'fishing']),
            opt('service', '서비스업 (호텔·숙박, 건설폐기물, 냉장·냉동, 한식 음식점 등)', 'Service (hotel/lodging, construction waste, cold storage, Korean restaurants, etc.)', ['E-9-5'], ['호텔', '숙박', '호스텔', '콘도', '음식점', '식당', '냉동', '냉장', '폐기물', 'hotel', 'restaurant', 'service']),
            opt('forestry', '임업', 'Forestry', ['E-9-9'], ['임업', '벌목', 'forestry']),
            opt('mining', '광업', 'Mining', ['E-9-10'], ['광업', '광산', 'mining']),
        ], procedures=['extension', 'workplace_change', 'registration'], unsure_ko='고용허가서나 표준근로계약서에 업종이 적혀 있습니다. 모르면 고용주에게 확인하세요.', unsure_en='The industry is on your employment permit or standard labor contract; ask your employer if unsure.'),
    ]},
    'E-7': {'dimensions': [
        dim('subtype', '어떤 E-7 유형인가요?', 'Which E-7 type do you hold?', [
            opt('professional', '전문인력 (E-7-1)', 'Professional (E-7-1)', ['E-7-1'], ['전문인력']),
            opt('semi', '준전문인력 (E-7-2)', 'Semi-professional (E-7-2)', ['E-7-2']),
            opt('general', '일반기능인력 (E-7-3)', 'General skilled (E-7-3)', ['E-7-3']),
            opt('skilled', '숙련기능인력 점수제 (E-7-4)', 'Skilled worker, points system (E-7-4)', ['E-7-4'], ['숙련', '점수제']),
            opt('regional_skilled', '지역특화형 숙련기능인력 (E-7-4R)', 'Regional skilled worker (E-7-4R)', ['E-7-4R'], ['지역특화']),
            opt('negative', '네거티브 방식 전문인력 (E-7-S)', 'Negative-list professional (E-7-S)', ['E-7-S'], ['고소득']),
            opt('youth', '국내성장인력 (E-7-Y)', 'Domestically raised talent (E-7-Y)', ['E-7-Y']),
            opt('top_tier', '유망톱티어 (E-7-T)', 'Top-Tier (E-7-T)', ['E-7-T'], ['톱티어', 'top-tier', 'top tier']),
            opt('fta', 'FTA 독립전문가 (E-7-91)', 'FTA independent professional (E-7-91)', ['E-7-91'], ['FTA', 'CEPA']),
        ], procedures=['extension', 'workplace_change', 'status_change'], unsure_ko='외국인등록증의 체류자격란에 E-7 뒤의 숫자·글자가 유형입니다. 고용계약서의 직종으로도 확인할 수 있습니다.', unsure_en='The number or letter after E-7 on your residence card is the type; your contract\'s occupation also tells you.'),
    ]},
    'E-8': {'dimensions': [
        dim('sector', '농업인가요, 어업인가요?', 'Agriculture or fishery?', [
            opt('agri', '농업', 'Agriculture', ['E-8-1', 'E-8-2', 'E-8-5', 'E-8-7'], ['농업', '농장']),
            opt('fish', '어업', 'Fishery', ['E-8-3', 'E-8-4', 'E-8-6', 'E-8-8'], ['어업']),
            opt('other', '언어소통 도우미 등 보조 인력', 'Support staff such as interpreters', ['E-8-99']),
        ], procedures=['extension', 'registration', 'workplace_change']),
        dim('pathway', '어떤 경로로 선정되었나요?', 'How were you selected?', [
            opt('mou', '지자체 간 MOU', 'Local-government MOU', ['E-8-1', 'E-8-3'], ['MOU']),
            opt('relative', '결혼이민자의 4촌 이내 친척 추천', 'Recommended as a marriage migrant\'s relative (within 4th degree)', ['E-8-2', 'E-8-4'], ['친척']),
            opt('reentry', 'G-1 자격으로 계절근로 후 재입국 추천', 'Re-entry after seasonal work under G-1', ['E-8-5', 'E-8-6']),
            opt('student_parent', '유학생의 부모', 'Parent of an international student', ['E-8-7', 'E-8-8']),
        ], procedures=['extension', 'registration', 'workplace_change']),
    ]},
    'F-2': {'dimensions': [
        dim('subtype', '어떤 거주(F-2) 유형인가요?', 'Which F-2 residence type do you hold?', [
            opt('child', '국민의 미성년 자녀 (F-2-2)', 'Minor child of a Korean national (F-2-2)', ['F-2-2'], ['미성년 자녀']),
            opt('pr_family', '영주권자의 배우자·미성년 자녀 (F-2-3)', 'Spouse or minor child of a permanent resident (F-2-3)', ['F-2-3'], ['영주권자 가족']),
            opt('refugee', '난민인정자 (F-2-4)', 'Recognised refugee (F-2-4)', ['F-2-4'], ['난민']),
            opt('points', '점수제 우수인재 (F-2-7)', 'Points-system resident (F-2-7)', ['F-2-7'], ['점수제', '우수인재']),
            opt('points_family', '점수제 우수인재의 배우자·자녀 (F-2-71)', 'Spouse or child of a points-system resident (F-2-71)', ['F-2-71']),
            opt('kstar', 'K-STAR 거주 (F-2-7S)', 'K-STAR residence (F-2-7S)', ['F-2-7S'], ['K-STAR', 'kstar']),
            opt('long_term', '기타 장기체류자 (F-2-99)', 'Other long-term resident (F-2-99)', ['F-2-99'], ['장기체류']),
            opt('regional', '지역특화형 우수인재 (F-2-R)', 'Regional talent (F-2-R)', ['F-2-R'], ['지역특화']),
            opt('top_tier', '톱티어 거주 (F-2-T)', 'Top-Tier residence (F-2-T)', ['F-2-T'], ['톱티어', 'top-tier']),
            opt('investor', '투자자 (F-2-5 고액투자, F-2-8 부동산, F-2-12 공익사업)', 'Investor (F-2-5, F-2-8, F-2-12)', ['F-2-5', 'F-2-8', 'F-2-12'], ['투자']),
        ], procedures=['extension', 'activities_outside_status'], unsure_ko='외국인등록증의 체류자격란에 F-2 뒤의 숫자·글자가 유형입니다.', unsure_en='The number or letter after F-2 on your residence card is the type.'),
    ]},
    'F-6': {'dimensions': [
        dim('subtype', '어떤 결혼이민(F-6) 유형인가요?', 'Which F-6 type do you hold?', [
            opt('spouse', '국민의 배우자 (F-6-1)', 'Spouse of a Korean national (F-6-1)', ['F-6-1'], ['배우자']),
            opt('childcare', '자녀 양육자 (F-6-2)', 'Parent raising a Korean child after the marriage ended (F-6-2)', ['F-6-2'], ['자녀양육']),
            opt('ended', '혼인단절자 (F-6-3)', 'Marriage ended through death, disappearance or the spouse\'s fault (F-6-3)', ['F-6-3'], ['혼인단절', '사망', '실종']),
        ], procedures=['extension', 'registration']),
        dim('f61_phase', '지금 상황에 가장 가까운 것은요?', 'Which best describes your situation?', [
            opt('first', 'F-6-1 사증으로 입국해서 처음 외국인등록·연장을 함께 신청', 'Entered on an F-6-1 visa; first registration and extension together', ['F-6-1#first-extension']),
            opt('normal', '이미 F-6-1로 체류 중이고 혼인생활을 유지 중', 'Already staying as F-6-1 and the marriage continues', ['F-6-1#extension']),
            opt('trouble', '별거 중이거나 이혼소송 중이거나 배우자가 실종 상태', 'Separated, in divorce proceedings, or the spouse is missing', ['F-6-1#separation-divorce-suit-missing'], ['별거', '이혼', '실종']),
        ], procedures=['extension'], kind='phase'),
        dim('f62_phase', '이번 신청은 어떤 단계인가요?', 'Which stage is this application?', [
            opt('first', 'F-6-2 사증으로 입국해서 처음 외국인등록·연장', 'Entered on an F-6-2 visa; first registration and extension', ['F-6-2#first-extension']),
            opt('normal', '이미 F-6-2로 체류 중', 'Already staying as F-6-2', ['F-6-2#extension']),
        ], procedures=['extension'], kind='phase'),
        dim('f63_phase', '어떤 상황이세요?', 'Which situation applies?', [
            opt('death', '배우자 사망 후 첫 연장', 'First extension after the spouse\'s death', ['F-6-3#after-death'], ['사망']),
            opt('missing', '배우자 실종선고 후 첫 연장', 'First extension after the spouse was declared missing', ['F-6-3#after-missing'], ['실종']),
            opt('divorce', '배우자 귀책 이혼 후 첫 연장', 'First extension after a divorce caused by the spouse', ['F-6-3#after-divorce'], ['이혼']),
            opt('normal', '이미 F-6-3으로 체류 중', 'Already staying as F-6-3', ['F-6-3#extension']),
        ], procedures=['extension'], kind='phase'),
    ]},
    'G-1': {'dimensions': [
        dim('ground', '어떤 사유로 G-1을 받으셨어요?', 'On what grounds were you given G-1?', [
            opt('industrial', '산업재해 청구·치료 중 (본인 또는 가족)', 'Industrial accident claim or treatment (you or family)', ['G-1-1'], ['산재']),
            opt('illness', '질병·사고로 치료 중 (본인 또는 가족)', 'Treatment for illness or accident (you or family)', ['G-1-2'], ['치료', '질병', '사고']),
            opt('lawsuit', '소송 진행 중', 'Ongoing lawsuit', ['G-1-3'], ['소송']),
            opt('wages', '임금체불로 노동관서 중재 중', 'Wage-arrears mediation at a labour office', ['G-1-4'], ['임금체불', '체불']),
            opt('asylum', '난민신청자', 'Asylum applicant', ['G-1-5'], ['난민신청', '난민']),
            opt('humanitarian', '인도적 체류허가자', 'Humanitarian stay holder', ['G-1-6'], ['인도적']),
            opt('pregnancy', '임신·출산 등 인도적 배려', 'Pregnancy, childbirth or similar humanitarian reasons', ['G-1-9'], ['임신', '출산']),
            opt('patient', '외국인환자 (장기 치료·요양)', 'Medical-treatment patient (long-term care)', ['G-1-10'], ['환자', '요양']),
            opt('victim', '성폭력피해자 등 인도적 고려', 'Victim of sexual violence or similar', ['G-1-11'], ['피해자']),
            opt('humanitarian_family', '인도적 체류허가자의 가족', 'Family of a humanitarian stay holder', ['G-1-12']),
            opt('asylum_child', '난민신청자의 국내 출생 자녀 (G-1-99)', 'Korea-born child of an asylum applicant (G-1-99)', ['G-1-99'], ['출생 자녀']),
        ], procedures=['extension'], unsure_ko='외국인등록증의 체류자격란에 G-1 뒤의 숫자가 사유 코드입니다.', unsure_en='The number after G-1 on your residence card is the grounds code.'),
    ]},
    'D-10': {'dimensions': [
        dim('subtype', '어떤 구직(D-10) 유형인가요?', 'Which D-10 type do you hold?', [
            opt('general', '일반구직 (D-10-1)', 'General job seeker (D-10-1)', ['D-10-1'], ['일반구직']),
            opt('startup', '기술창업준비 (D-10-2)', 'Start-up preparation (D-10-2)', ['D-10-2'], ['창업']),
            opt('intern', '첨단기술인턴 (D-10-3)', 'High-tech intern (D-10-3)', ['D-10-3'], ['인턴']),
            opt('top', '예비톱티어 최우수인재 (D-10-T)', 'Top-Tier job seeker (D-10-T)', ['D-10-T'], ['톱티어']),
        ], procedures=['extension'], unsure_ko='외국인등록증의 체류자격란에 D-10 뒤의 숫자·글자가 유형입니다.', unsure_en='The number or letter after D-10 on your residence card is the type.'),
        dim('d101_track', '일반구직(D-10-1)의 어떤 경우인가요?', 'Which D-10-1 case applies?', [
            opt('points', '점수제 적용 대상', 'Points-system applicant', ['D-10-1#points']),
            opt('korean_grad', '국내 대학 졸업 한국어능력 우수자 (점수제 면제)', 'Korean-university graduate with strong Korean (points-exempt)', ['D-10-1#exempt-korean-graduate'], ['졸업']),
            opt('youth', '국내 성장 기반 외국인 청소년', 'Domestically raised foreign youth', ['D-10-1#exempt-domestic-youth']),
            opt('promising', '유망인재', 'Promising talent', ['D-10-1#exempt-promising-talent']),
            opt('caregiver', '요양보호사 전문연수 수료자', 'Care-worker training graduate', ['D-10-1#exempt-caregiver-trainee'], ['요양보호사']),
            opt('professional', '전문직종(E-1~E-7) 근무 경력자', 'Former E-1~E-7 professional', ['D-10-1#exempt-professional-experience'], ['경력']),
        ], procedures=['extension']),
    ]},
    'D-4': {'dimensions': [
        dim('subtype', '어떤 연수인가요?', 'Which kind of training?', [
            opt('language', '한국어·외국어 어학연수 (D-4-1, D-4-7)', 'Korean / foreign-language training (D-4-1, D-4-7)', ['D-4-1'], ['어학연수', '어학']),
            opt('ktrainee', '기업 맞춤형 인턴십 K-Trainee (D-4-2K)', 'K-Trainee corporate internship (D-4-2K)', ['D-4-2K'], ['K-Trainee', '인턴십']),
            opt('k12', '고등학교 이하 유학 (D-4-3)', 'K-12 study (D-4-3)', ['D-4-3'], ['고등학교', '초등', '중학']),
            opt('other', '그 밖의 연수 (D-4-2, D-4-5, D-4-6 등)', 'Other training (D-4-2, D-4-5, D-4-6 etc.)', ['D-4-5', 'D-4-6', 'D-4-2']),
        ], procedures=['extension'])]},
    'D-8': {'dimensions': [
        dim('subtype', '어떤 투자 유형인가요?', 'Which investment type?', [
            opt('corp', '법인에 투자 (D-8-1)', 'Investment in a corporation (D-8-1)', ['D-8-1'], ['법인']),
            opt('venture', '벤처 투자 (D-8-2)', 'Venture investment (D-8-2)', ['D-8-2'], ['벤처']),
            opt('individual', '개인기업에 투자 (D-8-3)', 'Investment in a sole proprietorship (D-8-3)', ['D-8-3']),
            opt('startup', '기술창업 (D-8-4, D-8-4S)', 'Technology start-up (D-8-4, D-8-4S)', ['D-8-4', 'D-8-4S'], ['창업', '스타트업']),
        ], procedures=['extension'])]},
    'F-3': {'dimensions': [
        dim('principal', '주체류자(배우자 또는 부모)의 체류자격은 무엇인가요?', 'What is the principal holder\'s (spouse\'s or parent\'s) status?', [
            opt('general', 'D-1~E-7 등 일반 장기체류자', 'A general long-term status (D-1 to E-7 etc.)', ['F-3']),
            opt('points', '점수제 우수인재 (F-2-7)', 'Points-system resident (F-2-7)', ['F-3-18'], ['점수제']),
            opt('regional', '지역특화형 비자 (F-2-R, E-7-4R, F-4-R)', 'Regional visa holder (F-2-R, E-7-4R, F-4-R)', ['F-3-1R', 'F-3-3R', 'F-3-2R'], ['지역특화']),
            opt('top_tier', '톱티어 (E-7-T, D-10-T)', 'Top-Tier (E-7-T, D-10-T)', ['F-3-17', 'F-3-10'], ['톱티어']),
        ], procedures=['extension'])]},
    'E-10': {'dimensions': [
        dim('phase', '어떤 연장인가요?', 'Which kind of extension?', [
            opt('normal', '최초 입국 후 3년 이내의 연장', 'Extension within the first 3 years', ['E-10']),
            opt('reemployment', '3년 취업기간 만료 후 재고용 연장', 'Re-employment extension after the 3-year period', ['E-10#reemployment'], ['재고용']),
        ], procedures=['extension'], kind='phase')]},
    'C-3': {'dimensions': [
        dim('group_tour', '단체관광(C-3-2) 또는 보증개별 사증으로 입국하셨나요?', 'Did you enter on a group-tour or guaranteed-individual (C-3-2) visa?', [
            opt('yes', '예', 'Yes', ['C-3-2']), opt('no', '아니요', 'No', ['C-3']),
        ], procedures=['extension'], kind='yesno')]},
    'H-1': {'dimensions': [
        dim('nationality_group', '국적이 어디인가요?', 'What is your nationality?', [
            opt('us', '미국', 'United States', ['H-1'], ['미국', 'usa', 'american']), opt('uk_ca', '영국 또는 캐나다', 'United Kingdom or Canada', ['H-1'], ['영국', '캐나다', 'uk', 'canada']), opt('other', '그 외 협정국', 'Another agreement country', ['H-1']),
        ], procedures=['extension'], kind='nationality')]},
}

# Ask-current-status dimension used by transitions (status_change to a target)
CURRENT_STATUS_QUESTION = {
    'id': 'current_status', 'question_ko': '지금 한국에 어떤 체류자격으로 계세요?', 'question_en': 'What status are you currently in Korea on?',
    'options': [
        opt('long_term', '외국인등록을 한 장기체류자격 (D·E·F·G·H 계열)', 'A registered long-term status (D, E, F, G or H series)', ['LONG_TERM']),
        opt('short_stay', '무사증 또는 단기비자 (B-1·B-2, C-1~C-4)', 'Visa-free or short-term visa (B-1/B-2, C-1~C-4)', ['SHORT_STAY']),
        opt('h1', '관광취업 (H-1)', 'Working holiday (H-1)', ['H-1']),
        opt('illegal', '체류기간이 지났거나 등록되지 않음', 'Overstayed or unregistered', ['ILLEGAL']),
    ],
    'unsure_ko': '외국인등록증이 있으면 장기체류자격입니다. 없다면 여권의 입국 스탬프나 비자를 확인하세요.', 'unsure_en': 'If you have a residence card you hold a long-term status; otherwise check the visa or entry stamp in your passport.',
}

# ==========================================================================
# Natural-language aliases → status candidates (ask when >1)
# ==========================================================================
ALIASES = [
    {'terms': ['학생비자', '유학비자', '유학생', '유학', 'student visa', 'student'], 'candidates': ['D-2', 'D-4'], 'question_ko': '어떤 과정이에요?', 'question_en': 'Which course?', 'options': [opt('degree', '대학 이상 학위과정 (D-2)', 'Degree course at a university (D-2)', ['D-2']), opt('language', '어학연수·기타 연수 (D-4)', 'Language or other training (D-4)', ['D-4'])]},
    {'terms': ['배우자 비자', '배우자비자', '배우자', 'spouse visa', 'spouse', '남편', '아내', '와이프'], 'candidates': ['F-6', 'F-3', 'F-1'], 'question_ko': '배우자가 한국 국민인가요?', 'question_en': 'Is your spouse a Korean national?', 'options': [opt('korean', '예, 한국 국민', 'Yes, a Korean national', ['F-6']), opt('foreign', '아니요, 외국인 체류자(취업·유학 등)', 'No, a foreign resident (work, study, etc.)', ['F-3']), opt('f27', '아니요, 점수제 우수인재(F-2-7)', 'No, a points-system resident (F-2-7)', ['F-2-71', 'F-1-12'])]},
    {'terms': ['취업비자', '취업 비자', '일하는 비자', 'work visa', 'working visa', 'employment visa'], 'candidates': ['E-7', 'E-9'], 'question_ko': '어떤 취업 경로인가요?', 'question_en': 'Which employment route?', 'options': [opt('e7', '전문·숙련 인력 (E-7)', 'Professional / skilled worker (E-7)', ['E-7']), opt('e9', '고용허가제 EPS (E-9)', 'Employment Permit System (E-9)', ['E-9']), opt('e10', '선원 (E-10)', 'Seafarer (E-10)', ['E-10']), opt('e8', '계절근로 (E-8)', 'Seasonal worker (E-8)', ['E-8'])]},
    {'terms': ['가족비자', '가족 비자', 'family visa', '가족동반', '동반비자', '부모님'], 'candidates': ['F-1', 'F-3'], 'question_ko': '어떤 가족 체류인가요?', 'question_en': 'Which kind of family stay?', 'options': [opt('f3', '취업·유학 중인 배우자·부모의 동반 (F-3)', 'Dependant of a working or studying spouse/parent (F-3)', ['F-3']), opt('f1', '방문동거·부양·가사정리 등 (F-1)', 'Visiting / living with family, support, household matters (F-1)', ['F-1'])]},
    {'terms': ['결혼이민', '결혼비자', '결혼 비자', '국제결혼', 'marriage visa', 'marriage migrant'], 'candidates': ['F-6']},
    {'terms': ['워홀', '워킹홀리데이', 'working holiday', '관광취업'], 'candidates': ['H-1']},
    {'terms': ['동포', '재외동포', '방문취업', '조선족', '고려인'], 'candidates': ['F-4', 'H-2'], 'question_ko': '현재 어떤 자격인가요?', 'question_en': 'Which status do you hold?', 'options': [opt('f4', '재외동포 (F-4)', 'Overseas Korean (F-4)', ['F-4']), opt('h2', '방문취업 (H-2, 기존 소지자)', 'Visiting employment (H-2, existing holders)', ['H-2']), opt('c38', '동포방문 단기 (C-3-8)', 'Short-term compatriot visit (C-3-8)', ['C-3-8'])]},
    {'terms': ['영주', '영주권', 'permanent residence', 'permanent resident', 'pr'], 'candidates': ['F-5']},
    {'terms': ['난민', 'refugee', 'asylum', '인도적체류', '인도적 체류'], 'candidates': ['G-1']},
    {'terms': ['구직', '구직비자', 'job seeker', 'job-seeking'], 'candidates': ['D-10']},
    {'terms': ['투자', '투자비자', 'investor', 'investment'], 'candidates': ['D-8']},
    {'terms': ['교수', 'professor'], 'candidates': ['E-1']},
    {'terms': ['원어민', '회화지도', '영어강사', 'english teacher', 'language instructor'], 'candidates': ['E-2']},
    {'terms': ['연구원', '연구비자', 'researcher'], 'candidates': ['E-3']},
    {'terms': ['계절근로', 'seasonal'], 'candidates': ['E-8']},
    {'terms': ['선원', 'seafarer', 'crew'], 'candidates': ['E-10']},
    {'terms': ['고용허가제', 'eps', '비전문취업'], 'candidates': ['E-9']},
    {'terms': ['방문동거'], 'candidates': ['F-1']}, {'terms': ['거주비자', '거주 비자'], 'candidates': ['F-2']}, {'terms': ['동반'], 'candidates': ['F-3']},
    {'terms': ['디지털노마드', '디지털 노마드', '워케이션', 'digital nomad', 'workation'], 'candidates': ['F-1-D']},
    {'terms': ['점수제', 'points system', 'points-based'], 'candidates': ['F-2-7']},
    {'terms': ['톱티어', 'top-tier', 'top tier', 'toptier'], 'candidates': ['PROGRAM:top-tier']},
    {'terms': ['지역특화', '지역특화형', 'regional visa'], 'candidates': ['PROGRAM:regional']},
    {'terms': ['k-star', 'kstar', 'k star'], 'candidates': ['PROGRAM:k-star']},
    {'terms': ['광역형', '광역형 비자'], 'candidates': ['PROGRAM:metro']},
    {'terms': ['외국인 청소년', '청소년 정주', '국내 성장'], 'candidates': ['PROGRAM:youth']},
    {'terms': ['단기방문', '관광비자', 'tourist visa', 'tourist'], 'candidates': ['C-3']},
    {'terms': ['외교', 'diplomat'], 'candidates': ['A-1']},
    {'terms': ['종교', 'religious', 'missionary'], 'candidates': ['D-6']},
    {'terms': ['주재원', 'intra-company', 'expat transfer'], 'candidates': ['D-7']},
    {'terms': ['무역', 'trade visa'], 'candidates': ['D-9']},
    {'terms': ['예술흥행', '연예', 'entertainer', 'artist visa'], 'candidates': ['E-6']},
    {'terms': ['기술연수', 'technical trainee'], 'candidates': ['D-3']},
    {'terms': ['어학연수', 'language course', 'language training'], 'candidates': ['D-4-1']},
]

# ==========================================================================
# Special programs — first-class rules
# ==========================================================================
PROGRAMS = [
    {'id': 'dongpo', 'name_ko': '외국국적동포 통합 체류제도 (F-4 통합)', 'name_en': 'Overseas-Korean (compatriot) framework', 'manual': STAY, 'chapter_key': 'DONGPO', 'anchor': '동포 체류자격 통합에 따라 방문취업(H-2) 사증의 신규 발급 중단',
     'codes': ['C-3-8', 'H-2', 'H-2-7', 'F-4', 'F-4-R', 'F-5-6', 'F-5-7', 'F-5-14', 'F-3-19', 'F-3-20', 'F-1-11'], 'applies_to_parents': ['F-1', 'F-3'], 'visa_manual_chapter': True,
     'effective_from': '2026-02-12', 'summary_ko': '2026-02-12부터 방문취업(H-2)과 재외동포(F-4)로 나뉘어 있던 동포 체류자격이 재외동포(F-4)로 통합되어 중국·CIS 동포에게도 F-4가 발급되고 H-2 신규 발급은 중단되었습니다. 기존 H-2 소지자는 외국인등록 시 최대 3년이 부여되며 요건 충족 시 F-4·F-5로 이동할 수 있습니다.', 'summary_en': 'Since 2026-02-12 the compatriot statuses H-2 and F-4 have been merged into F-4: Chinese and CIS compatriots now receive F-4 and no new H-2 visas are issued. Existing H-2 holders get up to 3 years at registration and can move to F-4 or F-5 if eligible.',
     'dimensions_ko': ['국적(중국·CIS 등)', '기존 H-2 소지 여부', '한국어능력 입증 여부', '연령(만 13세 이하)'], 'dimensions_en': ['Nationality (China, CIS, etc.)', 'Existing H-2 holder', 'Korean-language proof', 'Age (13 or under)']},
    {'id': 'regional', 'name_ko': '지역특화형비자', 'name_en': 'Regional specialised visa', 'manual': STAY, 'chapter_key': 'REGION', 'anchor': 'Ⅰ. 지역특화형비자 사업 개요',
     'codes': ['F-2-R', 'F-3-1R', 'E-7-4R', 'F-3-3R', 'F-4-R', 'F-3-2R', 'F-5-6R'], 'visa_manual_chapter': False,
     'summary_ko': '인구감소지역 정착을 위한 제도로, 지자체장의 추천을 받은 우수인재(F-2-R), 숙련기능인력(E-7-4R), 재외동포(F-4-R)와 그 동반가족(F-3-1R/3R/2R), 동포영주(F-5-6R)를 포함합니다. 일반 코드만으로는 판단할 수 없고 지역·추천·거주·취업 조건이 추가됩니다.', 'summary_en': 'A settlement scheme for depopulating regions covering talent (F-2-R), skilled workers (E-7-4R) and overseas Koreans (F-4-R) recommended by local governments, their dependants (F-3-1R/3R/2R) and compatriot permanent residence (F-5-6R). Region, recommendation, residence and employment conditions apply on top of the ordinary code.',
     'dimensions_ko': ['사업지역(인구감소지역·관심지역)', '지자체 추천', '거주·근무 지역 유지', '직전 체류자격(E-9·E-10·H-2 2년 이상 등)', '최근 5년 참여 이력'], 'dimensions_en': ['Program area (depopulation / at-risk area)', 'Local-government recommendation', 'Continued residence and work in the area', 'Previous status (e.g. 2+ years on E-9/E-10/H-2)', 'Participation in the past 5 years']},
    {'id': 'youth', 'name_ko': '국내 성장 기반 외국인 청소년 취업·정주 체류제도', 'name_en': 'Domestically raised foreign youth employment and settlement scheme', 'manual': STAY, 'chapter_key': 'YOUTH', 'anchor': '국내 성장 기반 외국인 청소년이 고교 졸업 이후 구직(D-10-1), 국내성장인력(E-7-Y), 지역특화 우수인재(F-2-R) 체류자격 변경허가',
     'codes': ['E-7-Y'], 'applies_to_parents': ['D-10-1', 'F-2-R'], 'visa_manual_chapter': False,
     'summary_ko': '18~24세로 18세 전 국내 7년 이상 체류하고 국내 초·중·고를 졸업한 외국인 청소년이 고교 졸업 후 구직(D-10-1), 국내성장인력(E-7-Y), 지역특화 우수인재(F-2-R)로 변경할 수 있는 제도입니다.', 'summary_en': 'Foreign youth aged 18–24 who lived in Korea 7+ years before 18 and graduated from Korean K-12 schools may change to D-10-1, E-7-Y or F-2-R after high school.',
     'dimensions_ko': ['연령(18~24세)', '18세 이전 국내 체류 7년', '10~18세 해외 연속 3년 체류 여부', '국내 초·중·고 졸업'], 'dimensions_en': ['Age 18–24', '7 years in Korea before 18', 'No 3 consecutive years abroad between 10 and 18', 'Korean K-12 graduation']},
    {'id': 'top-tier', 'name_ko': '톱티어(Top-Tier) 비자', 'name_en': 'Top-Tier visa', 'manual': STAY, 'chapter_key': 'TOPTIER', 'anchor': '톱티어(Top-Tier) 사증발급 및 체류관리 지침',
     'codes': ['D-10-T', 'E-7-T', 'F-2-T', 'F-2-T1', 'F-5-T', 'F-5-T1', 'F-1-15', 'F-1-24', 'F-3-17', 'F-3-10'], 'visa_manual_chapter': True,
     'summary_ko': '첨단산업(산업통상부 추천형)과 과학기술(과기정통부 추천형) 분야 최우수인재를 위한 제도로 톱티어 거주(F-2-T)·영주(F-5-T), 유망톱티어 특정활동(E-7-T), 예비톱티어 구직(D-10-T)과 배우자·자녀(F-2-T1, F-5-T1, F-3-17, F-3-10), 부모(F-1-15), 가사보조인(F-1-24)을 포함합니다. 서울출입국 우수인재·투자지원센터가 전담합니다.', 'summary_en': 'For top talent in advanced industries (Ministry of Trade track) and science/technology (Ministry of Science track): F-2-T residence, F-5-T permanent residence, E-7-T rising talent, D-10-T pre-Top-Tier job seekers, dependants (F-2-T1, F-5-T1, F-3-17, F-3-10), parents (F-1-15) and domestic helpers (F-1-24). Handled by the Seoul Immigration Office talent centre.',
     'dimensions_ko': ['추천 트랙(산업통상부 / 과기정통부)', '등급(톱티어·유망·예비)', '가족 역할(배우자·자녀·부모·가사보조인)'], 'dimensions_en': ['Recommendation track (Trade / Science)', 'Tier (top, rising, pre)', 'Family role (spouse, child, parent, helper)']},
    {'id': 'metro', 'name_ko': '광역형 비자 시범사업', 'name_en': 'Metropolitan / provincial visa pilot', 'manual': STAY, 'chapter_key': 'METRO', 'anchor': '광역형 비자 시범사업',
     'codes': [], 'applies_to_parents': ['D-2', 'E-7'], 'visa_manual_chapter': False, 'pilot_program': True,
     'summary_ko': '법무부와 광역지자체가 지역 특성에 맞춘 요건으로 유학(D-2, 서울·부산·인천·광주·강원·충북·충남·전북·전남·제주)과 특정활동(E-7, 대구·울산·경기·경북·경남)을 운영하는 시범사업입니다. 지자체 추천서와 지자체별 요건이 필요합니다.', 'summary_en': 'A pilot in which the Ministry of Justice and provincial governments run D-2 (Seoul, Busan, Incheon, Gwangju, Gangwon, Chungbuk, Chungnam, Jeonbuk, Jeonnam, Jeju) and E-7 (Daegu, Ulsan, Gyeonggi, Gyeongbuk, Gyeongnam) with region-specific requirements and a local recommendation.',
     'dimensions_ko': ['광역지자체', '지자체 추천서', '지자체별 요건(직종·한국어·기량검증 등)'], 'dimensions_en': ['Province / metropolitan city', 'Local recommendation', 'Region-specific requirements (occupation, Korean, skills test)']},
    {'id': 'k-star', 'name_ko': 'K-STAR 비자트랙', 'name_en': 'K-STAR visa track', 'manual': STAY, 'chapter_key': 'KSTAR', 'anchor': 'K-STAR 영주 점수제 항목 및 점수표',
     'codes': ['F-2-7S', 'F-5-S1', 'F-5-S2'], 'applies_to_parents': ['F-2-71'], 'visa_manual_chapter': True,
     'summary_ko': '법무부 선정 K-STAR 참여대학(32개교) 석·박사 유학생을 위한 거주(F-2-7S)와 200점 만점 중 90점 이상으로 얻는 영주(F-5-S1), 동반가족(F-2-71, F-5-S2)과 우수인재 특별귀화를 포함합니다.', 'summary_en': 'For master\'s and doctoral students at the 32 designated K-STAR universities: F-2-7S residence, F-5-S1 permanent residence (90 of 200 points), dependants (F-2-71, F-5-S2) and special naturalisation.',
     'dimensions_ko': ['참여대학 여부', '학위(석사·박사)', '연구경력·실적 점수'], 'dimensions_en': ['Participating university', 'Degree (master\'s / doctorate)', 'Research experience and output points']},
]

# ==========================================================================
# Display names for substatus codes (navigational labels only; the Korean
# label follows the manual's 세부약호 table or section title, English is a
# plain rendering of it — never a legal definition).
# ==========================================================================
SUBCODE_NAMES = {
    'A-3-99': ('Fulbright 협정 대상자', 'Fulbright agreement grantee'),
    'C-3-1': ('단기일반', 'Short-term general'), 'C-3-2': ('단체관광 등', 'Group tour etc.'), 'C-3-3': ('의료관광', 'Medical tourism'), 'C-3-4': ('단기상용', 'Short-term business'), 'C-3-5': ('협정상 단기상용', 'Short-term business under agreement'), 'C-3-6': ('우대기업 초청 단기상용', 'Preferred-company invited business'), 'C-3-7': ('도착관광', 'Visa on arrival tourism'), 'C-3-8': ('동포방문', 'Compatriot visit'), 'C-3-9': ('일반관광', 'General tourism'), 'C-3-10': ('순수환승', 'Pure transit'), 'C-3-11': ('교대선원', 'Crew change'),
    'C-4-1': ('계절근로 단기취업 (MOU, 농업)', 'Seasonal short-term work (MOU, agriculture)'), 'C-4-2': ('계절근로 단기취업 (결혼이민자 친척, 농업)', 'Seasonal short-term work (marriage migrant relative, agriculture)'), 'C-4-3': ('계절근로 단기취업 (MOU, 어업)', 'Seasonal short-term work (MOU, fishery)'), 'C-4-4': ('계절근로 단기취업 (결혼이민자 친척, 어업)', 'Seasonal short-term work (marriage migrant relative, fishery)'), 'C-4-5': ('대학 90일 이내 강의', 'University lecturing within 90 days'),
    'D-2-1': ('전문학사과정', 'Associate degree'), 'D-2-2': ('학사과정', "Bachelor's degree"), 'D-2-3': ('석사과정', "Master's degree"), 'D-2-4': ('박사과정', 'Doctoral degree'), 'D-2-5': ('연구과정', 'Research course'), 'D-2-6': ('교환학생', 'Exchange student'), 'D-2-7': ('일-학습연계 유학', 'Work-study linked study'), 'D-2-8': ('방문학생', 'Visiting student'),
    'D-3-1': ('구 기술연수 (2006-12-31까지 등록자)', 'Legacy technical training (registered by 2006-12-31)'), 'D-3-11': ('해외직접투자 연수', 'Overseas direct investment trainee'), 'D-3-12': ('기술투자 연수', 'Technology export trainee'), 'D-3-13': ('플랜트수출 연수', 'Plant export trainee'),
    'D-4-1': ('한국어 연수', 'Korean language training'), 'D-4-2': ('국공립기관 연수', 'Public institution training'), 'D-4-3': ('고등학교 이하 외국인유학생', 'K-12 international student'), 'D-4-5': ('한식조리연수생', 'Korean cuisine trainee'), 'D-4-6': ('사설기관 연수', 'Private institution training'), 'D-4-7': ('외국어 연수', 'Foreign language training'), 'D-4-2K': ('기업 맞춤형 인턴십 (K-Trainee)', 'K-Trainee corporate internship'),
    'D-8-1': ('법인에 투자', 'Investment in a corporation'), 'D-8-2': ('벤처 투자', 'Venture investment'), 'D-8-3': ('개인기업에 투자', 'Investment in a sole proprietorship'), 'D-8-4': ('기술창업', 'Technology start-up'), 'D-8-4S': ('기술창업 스타트업코리아 특별비자', 'Startup Korea special visa'),
    'D-9-1': ('점수제 무역비자', 'Points-based trade visa'), 'D-9-4': ('개인사업자 무역경영', 'Sole-proprietor trade'), 'D-9-5': ('유학생 무역경영자', 'International-student trader'),
    'D-10-1': ('일반구직', 'General job seeker'), 'D-10-2': ('기술창업준비', 'Start-up preparation'), 'D-10-3': ('첨단기술인턴', 'High-tech intern'), 'D-10-T': ('예비톱티어 최우수인재', 'Top-Tier job seeker'),
    'E-2-1': ('일반 회화지도', 'General language instruction'), 'E-2-2': ('학교보조교사', 'School assistant teacher'), 'E-2-91': ('FTA 영어보조교사', 'FTA English assistant teacher'),
    'E-6-1': ('예술·연예', 'Arts and entertainment'), 'E-6-2': ('호텔·유흥', 'Hotel and entertainment venues'), 'E-6-3': ('운동', 'Sports'),
    'E-7-1': ('전문인력', 'Professional'), 'E-7-2': ('준전문인력', 'Semi-professional'), 'E-7-3': ('일반기능인력', 'General skilled'), 'E-7-4': ('숙련기능인력 (점수제)', 'Skilled worker (points system)'), 'E-7-4R': ('지역특화형 숙련기능인력', 'Regional skilled worker'), 'E-7-91': ('FTA 독립전문가', 'FTA independent professional'), 'E-7-S': ('네거티브 방식 전문인력', 'Negative-list professional'), 'E-7-S1': ('고소득자', 'High-income professional'), 'E-7-S2': ('첨단산업분야 종사 예정자', 'Advanced-industry professional'), 'E-7-Y': ('국내성장인력', 'Domestically raised talent'), 'E-7-T': ('유망톱티어 특정활동', 'Top-Tier specific activities'), 'E-7-M': ('K-CORE 육성형 전문기술인력', 'K-CORE cultivated technical talent'),
    'E-8-1': ('농업 · 지자체 MOU', 'Agriculture · local-government MOU'), 'E-8-2': ('농업 · 결혼이민자 친척 추천', 'Agriculture · marriage migrant relative'), 'E-8-3': ('어업 · 지자체 MOU', 'Fishery · local-government MOU'), 'E-8-4': ('어업 · 결혼이민자 친척 추천', 'Fishery · marriage migrant relative'), 'E-8-5': ('농업 · G-1 계절근로 후 재입국', 'Agriculture · re-entry after G-1 seasonal work'), 'E-8-6': ('어업 · G-1 계절근로 후 재입국', 'Fishery · re-entry after G-1 seasonal work'), 'E-8-7': ('농업 · 유학생의 부모', 'Agriculture · parent of a student'), 'E-8-8': ('어업 · 유학생의 부모', 'Fishery · parent of a student'), 'E-8-99': ('언어소통 도우미 등 보조 인력', 'Support staff such as interpreters'),
    'E-9-1': ('제조업', 'Manufacturing'), 'E-9-2': ('건설업', 'Construction'), 'E-9-3': ('농축산업', 'Agriculture and livestock'), 'E-9-4': ('어업', 'Fishery'), 'E-9-5': ('서비스업', 'Service industry'), 'E-9-9': ('임업', 'Forestry'), 'E-9-10': ('광업', 'Mining'),
    'E-10-1': ('내항선원', 'Coastal vessel crew'), 'E-10-2': ('어선원', 'Fishing vessel crew'), 'E-10-3': ('순항여객선원', 'Cruise ship crew'),
    'F-1-1': ('구 방문동거 (국민의 미성년 외국인 자녀)', 'Legacy visiting stay (minor foreign child of a national)'), 'F-1-3': ('외교·국제기구 직원의 동거인', 'Cohabitant of diplomatic / international-organisation staff'), 'F-1-4': ('국민의 혼외 미성년 자녀 양육자', 'Parent raising a national\'s child born out of wedlock'), 'F-1-5': ('결혼이민자의 부모 등 가족', 'Parent or family of a marriage migrant'), 'F-1-6': ('가사정리', 'Settling household affairs after a marriage ended'), 'F-1-D': ('디지털노마드 (워케이션)', 'Digital nomad (workation)'), 'F-1-11': ('재외동포(F-4) 동반가족', 'Family of an overseas Korean (F-4)'), 'F-1-12': ('점수제 우수인재의 배우자·미성년 자녀', 'Spouse or minor child of a points-system resident'), 'F-1-13': ('고등학교 이하 유학생 동반부모', 'Parent accompanying a K-12 student'), 'F-1-15': ('우수인재(톱티어) 부모', 'Parent of Top-Tier talent'), 'F-1-16': ('난민인정자의 배우자·미성년 자녀', 'Spouse or minor child of a recognised refugee'), 'F-1-21': ('공관원 동일국적 동거인', 'Same-nationality cohabitant of mission staff'), 'F-1-22': ('고액투자가 가족', 'Family of a high-value investor'), 'F-1-23': ('첨단 가사보조인', 'Domestic helper (advanced-industry talent)'), 'F-1-24': ('톱티어 가사보조인', 'Domestic helper of Top-Tier talent'), 'F-1-28': ('귀화자의 외국국적 부모 등', 'Foreign-national parent of a naturalised Korean'), 'F-1-51': ('국제입양 아동', 'Child in international adoption'), 'F-1-52': ('결혼이민자의 전혼관계 출생 자녀', 'Child from a marriage migrant\'s previous marriage'), 'F-1-72': ('난민인정자 가족 (구 약호)', 'Refugee family (legacy code)'),
    'F-2-1': ('결혼이민 (구 약호, 현 F-6)', 'Marriage migrant (legacy, now F-6)'), 'F-2-2': ('국민의 미성년 자녀', 'Minor child of a Korean national'), 'F-2-3': ('영주권자의 배우자·미성년 자녀', 'Spouse or minor child of a permanent resident'), 'F-2-4': ('난민인정자', 'Recognised refugee'), 'F-2-5': ('고액투자자', 'High-value investor'), 'F-2-6': ('숙련생산기능 거주 (2019-10-01 폐지)', 'Skilled production resident (abolished 2019-10-01)'), 'F-2-7': ('점수제 우수인재', 'Points-system resident'), 'F-2-8': ('관광·휴양시설 투자 거주', 'Tourism / leisure facility investor'), 'F-2-10': ('결혼이민 (구 약호, 현 F-6)', 'Marriage migrant (legacy, now F-6)'), 'F-2-12': ('공익사업투자 거주', 'Public-interest investment resident'), 'F-2-13': ('공익사업 투자자의 배우자·미혼자녀', 'Spouse or unmarried child of a public-interest investor'), 'F-2-16': ('특별기여·공익증진자', 'Special contributor'), 'F-2-71': ('점수제 우수인재의 배우자·미성년 자녀 (거주)', 'Spouse or minor child of a points-system resident'), 'F-2-7S': ('K-STAR 거주', 'K-STAR residence'), 'F-2-81': ('관광·휴양시설 투자자의 미혼자녀', 'Unmarried child of a tourism-facility investor'), 'F-2-99': ('기타 장기체류자', 'Other long-term resident'), 'F-2-R': ('지역특화형 우수인재', 'Regional talent'), 'F-2-T': ('톱티어 거주', 'Top-Tier residence'), 'F-2-T1': ('톱티어 동반 거주', 'Top-Tier dependant residence'),
    'F-3-10': ('예비톱티어 구직(D-10-T) 동반', 'Dependant of a Top-Tier job seeker (D-10-T)'), 'F-3-17': ('유망톱티어 특정활동(E-7-T) 동반', 'Dependant of Top-Tier specific activities (E-7-T)'), 'F-3-18': ('점수제 우수인재 동반', 'Dependant of a points-system resident'), 'F-3-19': ('재외동포(F-4) 가족 동반', 'Family of an overseas Korean (F-4)'), 'F-3-20': ('방문취업(H-2) 동반가족', 'Family of an H-2 holder'), 'F-3-1R': ('지역특화 우수인재 동반가족', 'Family of regional talent'), 'F-3-2R': ('지역특화 재외동포 동반가족', 'Family of a regional overseas Korean'), 'F-3-3R': ('지역특화 숙련기능인력 동반가족', 'Family of a regional skilled worker'),
    'F-4-R': ('지역특화형 재외동포', 'Regional overseas Korean'), 'F-4-41': ('재외동포 본인 (국적 보유자)', 'Overseas Korean (former national)'), 'F-4-42': ('재외동포 직계비속', 'Descendant of an overseas Korean'),
    'F-5-1': ('일반 영주자', 'General permanent resident'), 'F-5-2': ('국민의 배우자', 'Spouse of a Korean national'), 'F-5-3': ('국민의 미성년 자녀', 'Minor child of a Korean national'), 'F-5-4': ('일반 영주자의 배우자·미성년 자녀', 'Spouse or minor child of a permanent resident'), 'F-5-5': ('고액 투자자', 'High-value investor'), 'F-5-6': ('재외동포 2년 체류자', 'Overseas Korean resident for 2+ years'), 'F-5-7': ('국적취득 요건 동포', 'Compatriot meeting nationality requirements'), 'F-5-8': ('재한화교', 'Korea-born ethnic Chinese'), 'F-5-9': ('첨단분야 박사', 'Advanced-industry doctorate holder'), 'F-5-10': ('학사·석사 및 자격증 소지자', "Bachelor's/master's or certificate holder"), 'F-5-11': ('특정분야 능력 소유자', 'Person of exceptional ability'), 'F-5-12': ('특별 공로자', 'Person of special merit'), 'F-5-13': ('연금 수혜자', 'Pension recipient'), 'F-5-14': ('방문취업 장기근속자', 'Long-serving H-2 worker'), 'F-5-15': ('국내 박사학위 취득자', 'Domestic doctorate holder'), 'F-5-16': ('점수제 영주자', 'Points-system permanent resident'), 'F-5-17': ('관광·휴양시설 투자자', 'Tourism / leisure facility investor'), 'F-5-18': ('점수제 영주자의 배우자·미성년 자녀', 'Spouse or minor child of a points-system permanent resident'), 'F-5-19': ('관광·휴양시설 투자자의 배우자·미성년 자녀', 'Spouse or minor child of a tourism-facility investor'), 'F-5-20': ('국내 출생 영주자 자녀', 'Korea-born child of a permanent resident'), 'F-5-21': ('공익사업 일반투자자', 'Public-interest general investor'), 'F-5-22': ('공익사업 투자자의 배우자·미성년 자녀', 'Spouse or minor child of a public-interest investor'), 'F-5-23': ('공익사업 은퇴이민 투자자', 'Public-interest retirement investor'), 'F-5-24': ('기술창업 투자자', 'Technology start-up investor'), 'F-5-25': ('30억원 이상 투자 서약자', 'KRW 3 billion+ investor'), 'F-5-26': ('연구개발시설 필수전문인력', 'Essential R&D professional'), 'F-5-27': ('난민 거주 2년 체류자', 'Refugee resident for 2+ years'), 'F-5-28': ('특별기여자', 'Special contributor'), 'F-5-29': ('특별기여자의 배우자·미성년 자녀', 'Spouse or minor child of a special contributor'), 'F-5-6R': ('지역특화형 재외동포 영주', 'Regional overseas-Korean permanent residence'), 'F-5-S1': ('K-STAR 영주', 'K-STAR permanent residence'), 'F-5-S2': ('K-STAR 동반가족 영주', 'K-STAR dependant permanent residence'), 'F-5-T': ('톱티어 영주', 'Top-Tier permanent residence'), 'F-5-T1': ('톱티어 동반 영주', 'Top-Tier dependant permanent residence'),
    'F-6-1': ('국민의 배우자', 'Spouse of a Korean national'), 'F-6-2': ('자녀 양육자', 'Parent raising a Korean child'), 'F-6-3': ('혼인단절자', 'Marriage ended without fault'),
    'G-1-1': ('산업재해 청구·치료 중인 사람과 가족', 'Industrial accident claimant/patient and family'), 'G-1-2': ('질병·사고 치료 중인 사람과 가족', 'Illness/accident patient and family'), 'G-1-3': ('소송 진행 중인 사람', 'Litigant'), 'G-1-4': ('임금체불 중재 중인 사람', 'Wage-arrears mediation'), 'G-1-5': ('난민신청자', 'Asylum applicant'), 'G-1-6': ('인도적 체류허가자', 'Humanitarian stay holder'), 'G-1-7': ('사고 등으로 사망한 사람의 가족', 'Family of a person who died in an accident'), 'G-1-8': ('장기체류 아동', 'Long-term resident child'), 'G-1-9': ('임신·출산 등 인도적 배려', 'Pregnancy / childbirth humanitarian case'), 'G-1-10': ('외국인환자 (장기치료·요양)', 'Medical patient (long-term care)'), 'G-1-11': ('성폭력피해자 등 인도적 고려', 'Victim of sexual violence etc.'), 'G-1-12': ('인도적 체류허가자의 가족', 'Family of a humanitarian stay holder'), 'G-1-19': ('기타 (구 약호)', 'Other (legacy code)'), 'G-1-99': ('기타 사유 (난민신청자의 국내 출생 자녀 등)', 'Other grounds (e.g. Korea-born child of an asylum applicant)'),
    'H-2-7': ('만기출국 후 재입국자', 'Re-entrant after completing the term'),
}


def main():
    data = {
        'schema_version': 1, 'generated_by': 'scripts/status_guidance/author_rules.py', 'source_editions': {'stay': STAY, 'visa': VISA},
        'enums': {'procedure_states': PROCEDURE_STATES, 'coverage_states': COVERAGE_STATES, 'requirement_levels': REQ_LEVELS, 'completeness': COMPLETENESS, 'roles': ROLES},
        'procedures': [{'id': p[0], 'domain': p[1], 'ko': p[2], 'en': p[3], 'keywords': p[4]} for p in PROCEDURES],
        'document_definitions': [docdef(k) for k in DOCDEFS],
        'guidance': GUIDANCE,
        'state_overrides': [{'target': c, 'procedure': p, 'state': s, 'anchor': a, 'ko': ko, 'en': en, 'manual': STAY} for c, p, s, a, ko, en in STATE_OVERRIDES],
        'overlays': OVERLAYS,
        'transitions': TRANSITIONS,
        'families': FAMILIES,
        'current_status_question': CURRENT_STATUS_QUESTION,
        'aliases': ALIASES,
        'programs': PROGRAMS,
        'subcode_names': {k: {'ko': v[0], 'en': v[1]} for k, v in SUBCODE_NAMES.items()},
        'officer_note': {'ko': OFFICER_NOTE_KO, 'en': OFFICER_NOTE_EN},
    }
    text = json.dumps(data, ensure_ascii=False, indent=1) + '\n'
    if '--check' in sys.argv[1:]:
        try:
            current = open(OUT, encoding='utf-8').read()
        except FileNotFoundError:
            current = None
        if current != text:
            print(f'ERROR: {OUT} is stale — run: python3 scripts/status_guidance/author_rules.py', file=sys.stderr)
            sys.exit(1)
        print(f'guidance rules are current: {len(GUIDANCE)} guidance entries, {sum(len(g["documents"]) for g in GUIDANCE)} document items')
        return
    with open(OUT, 'w', encoding='utf-8') as fh:
        fh.write(text)
    print(f'wrote {OUT}: {len(GUIDANCE)} guidance entries, {sum(len(g["documents"]) for g in GUIDANCE)} document items')


if __name__ == '__main__':
    main()
