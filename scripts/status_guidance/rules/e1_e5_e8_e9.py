# E-1 교수 · E-2 회화지도 · E-3 연구 · E-4 기술지도 · E-5 전문직업 · E-8 계절근로 · E-9 비전문취업
# Transcribed from the 2026-10-19 manuals:
#   visa manual  — 교수(E-1) ~ 전문직업(E-5) chapters, 계절근로(E-8), 비전문취업(E-9)
#   stay manual  — 교수(E-1) ~ 전문직업(E-5) chapters, 계절근로(E-8), 비전문취업(E-9)
# Runs inside author_rules.py (guidance, item, docdefs, drop, residence, VISA, STAY ...).

docdefs(
    # ---- visa-manual forms and shared items
    e159_visa_app_form=('사증발급신청서 (별지 제17호 서식)', 'Visa application form (Form 17)', 'applicant', None),
    e159_cvi_app_form=('사증발급인정신청서 (별지 제21호 서식)', 'Application for a confirmation of visa issuance (Form 21)', 'applicant', None),
    e159_proxy_docs=('대리인 신청 시 위임장, 대리인 재직증명서, 대리인 신분증', 'If filed by a proxy: power of attorney, the proxy\'s employment certificate and ID', 'other_third_party', None),
    e159_same_as_visa_docs=('공관장 재량 사증 또는 사증발급인정서 발급대상자와 동일한 제출서류', 'The same documents as for the consular-discretion visa or the confirmation of visa issuance', 'applicant', None),
    # ---- E-1
    e159_career_and_degree=('경력증명서 및 학위증', 'Career certificate and degree certificate', 'applicant', None),
    e159_school_establishment_docs=('초청학교 설립관련 서류 (사업자등록증 사본 또는 법인등기사항전부증명서)', 'Inviting school\'s establishment documents (business registration copy or corporate register)', 'educational_institution', None),
    e159_moe_talent_recommendation=('교육부장관의 ‘고급과학기술인력’ 고용추천서', 'Minister of Education\'s employment recommendation as advanced science and technology personnel', 'educational_institution', None),
    e159_inviting_institution_docs=('초청기관 설립관련 서류 (사업자등록증 또는 법인등기사항전부증명서)', 'Inviting institution\'s establishment documents (business registration or corporate register)', 'educational_institution', None),
    e159_bk21_letter=('BK21 관련 공문 사본 (해당자에 한함)', 'Copy of the BK21-related official letter (if applicable)', 'educational_institution', None),
    e159_contract_or_appointment_orig=('고용계약서 원본 및 사본 (또는 임용예정 확인서)', 'Employment contract, original and copy (or appointment confirmation)', 'employer', None),
    e159_career_with_degree_copy=('경력증명서 (학위증 사본 첨부)', 'Career certificate (with a copy of the degree certificate)', 'applicant', None),
    e159_company_establishment_docs=('회사설립관련서류 (사업자등록증, 연구기관 입증서류)', 'Company establishment documents (business registration, proof of the research institution)', 'employer', None),
    e159_prev_employer_consent=('원 근무처장의 동의서', 'Consent of the head of the original workplace', 'employer', None),
    e159_degree_or_career_orig=('학위증 (원본 및 사본) 또는 경력증명서', 'Degree certificate (original and copy) or career certificate', 'applicant', None),
    e159_degree_or_career=('학위증 또는 경력증명서', 'Degree certificate or career certificate', 'applicant', None),
    e159_employer_establishment_docs=('고용업체 등 설립관련 서류 (사업자등록증, 등기부등본 등)', 'Employer\'s establishment documents (business registration, register extract, etc.)', 'employer', None),
    e159_graduation_cert=('졸업증명서', 'Graduation certificate', 'applicant', None),
    e159_president_recommendation=('총(학)장의 고용추천서', 'Employment recommendation from the university president or dean', 'educational_institution', None),
    e159_president_lecture_recommendation=('총(학)장의 추천서', 'Recommendation from the university president or dean', 'educational_institution', None),
    e159_unique_no_or_bizreg_copy=('고유번호증(사업자등록증) 사본', 'Copy of the unique-number certificate (business registration)', 'educational_institution', None),
    e159_moe_recommendation=('교육부장관의 고용추천서', 'Minister of Education\'s employment recommendation', 'educational_institution', None),
    e159_research_institution_proof=('연구기관 입증서류', 'Proof of the research institution', 'employer', None),
    e159_same_foundation_proof=('동일재단입증서류', 'Proof of belonging to the same foundation', 'employer', None),
    e159_org_establishment_permit=('해당단체 설립허가서', 'Establishment permit of the organisation', 'other_third_party', None),
    e159_workplace_report_form=('근무처변경·추가 신고서 (별지 제38호의3서식)', 'Workplace change/addition report form (Form 38-3)', 'applicant', None),
    # ---- E-2
    e159_e2_pass_cert=('원어민 영어 보조교사 또는 원어민 중국어보조교사 합격증 또는 TaLK 장학생 초청장 (국립국제교육원장 또는 시·도 교육감 발급)', 'Native English / Chinese assistant-teacher pass certificate or TaLK scholar invitation (issued by NIIED or a provincial superintendent)', 'educational_institution', None),
    e159_moe_contract=('시·도 교육감 등과 체결한 고용계약서', 'Employment contract with the provincial superintendent of education, etc.', 'educational_institution', None),
    e159_degree_cert_confirmed=('공적확인을 받은 학력증명서 (학위증 사본, 학위취득 증명서, 학위취득 사실이 기재된 졸업증명서 중 1종)', 'Officially confirmed proof of education (one of: degree copy, degree-conferral certificate, graduation certificate stating the degree)', 'applicant', None),
    e159_crime_record_home=('공적확인을 받은 자국정부 발급 범죄경력증명서 (자국 전역의 범죄경력 포함)', 'Officially confirmed national criminal record certificate issued by your government (covering the whole country)', 'applicant', None),
    e159_crime_record_third=('공적확인을 받은 제3국 범죄경력증명서', 'Officially confirmed criminal record certificate from a third country', 'applicant', None),
    e159_self_health_check=('자기건강확인서', 'Self-declaration of health', 'applicant', None),
    e159_contract_min_wage=('고용계약서 (최소 임금요건: 당해연도 최저임금 이상)', 'Employment contract (minimum wage: at least this year\'s statutory minimum wage)', 'employer', None),
    e159_academy_establishment=('학원 또는 단체 설립관련 서류', 'Establishment documents of the academy or organisation', 'employer', None),
    e159_e2_reference_docs=('기타 심사에 필요한 참고자료 (강사활용계획서, 수강생 및 직원현황 등)', 'Other reference material for review (instructor utilisation plan, student and staff numbers, etc.)', 'employer', None),
    e159_pass_notice=('시·도 교육감이나 국립국제교육원장이 발급한 합격통지서 또는 통지서', 'Pass notice issued by the provincial superintendent or the NIIED president', 'educational_institution', None),
    e159_school_bizreg_copy=('학교 사업자등록증 사본 (또는 고유번호증 사본)', 'Copy of the school\'s business registration (or unique-number certificate)', 'educational_institution', None),
    e159_pass_cert=('합격증명서', 'Pass certificate', 'educational_institution', None),
    e159_degree_confirmed_stay=('공적확인을 받은 학력증명서', 'Officially confirmed proof of education', 'applicant', None),
    e159_crime_record_6m=('신청일로부터 6개월 이내에 발급 받은 공적확인을 받은 범죄경력증명서', 'Officially confirmed criminal record certificate issued within 6 months of the application', 'applicant', None),
    e159_recruit_medical=('채용신체검사서', 'Pre-employment medical examination report', 'applicant', None),
    e159_lifelong_edu_reg_copy=('평생교육시설등록증 사본 (해당자)', 'Copy of the lifelong-education facility registration (if applicable)', 'employer', None),
    e159_crime_record_home_third=('범죄경력증명서 (자국 및 제3국(해당자))', 'Criminal record certificate (home country and, if applicable, third country)', 'applicant', None),
    e159_employer_establishment_e2=('고용업체 등 설립관련 서류 (사업자등록증, 학원설립증, 등기부등본 등)', 'Employer\'s establishment documents (business registration, academy registration, register extract, etc.)', 'employer', None),
    e159_scholar_pass_notice=('“대통령 영어봉사 장학생” 합격통지서 (국립국제교육원장 또는 시·도 교육감 발급)', '“Presidential English-service scholar” pass notice (issued by NIIED or a provincial superintendent)', 'educational_institution', None),
    e159_facility_establishment_docs=('시설 설립 관련서류', 'Facility establishment documents', 'employer', None),
    e159_contract_orig_and_copy=('고용계약서 원본과 사본', 'Employment contract, original and copy', 'employer', None),
    e159_crime_record_confirmed=('공적확인을 받은 범죄경력증명서', 'Officially confirmed criminal record certificate', 'applicant', None),
    e159_org_establishment=('단체 등 설립관련 서류', 'Establishment documents of the organisation', 'employer', None),
    e159_other_review_docs=('기타 심사에 필요한 입증자료 등', 'Other supporting evidence needed for review', 'applicant', None),
    e159_central_agency_head_recommendation=('소관 중앙행정기관의 장의 고용추천서 또는 고용의 필요성을 입증할 수 있는 서류', 'Employment recommendation from the head of the competent central agency, or documents proving the need for employment', 'employer', None),
    # ---- E-3
    e159_institution_docs=('고용기관 설립 관련 서류 (사업자등록증 또는 법인등기사항전부증명서 또는 연구기관 입증서류 등)', 'Employing institution\'s establishment documents (business registration, corporate register or proof of the research institution, etc.)', 'employer', None),
    e159_masters_degree_career=('석사 학위 이상 학위증, 경력증명서 (해당자)', 'Master\'s degree or higher certificate, career certificate (if applicable)', 'applicant', None),
    e159_graduation_expected_proof=('대학 대표자 명의로 발급된 졸업예정증명서·확인서 등과 학위수여 날짜를 확인할 수 있는 증명서 등 (해당자)', 'Expected-graduation certificate or confirmation issued in the university head\'s name and proof of the degree-conferral date (if applicable)', 'educational_institution', None),
    e159_paper_author_proof=('우수 학술논문의 저자임을 확인할 수 있는 입증자료 (해당자)', 'Proof of authorship of an excellent academic paper (if applicable)', 'applicant', None),
    e159_employment_recommendation=('고용추천서', 'Employment recommendation', 'employer', None),
    e159_invitation_letter_research=('초청 연구기관 명의의 초청 공문 (임금요건 불필요, 연구기간, 연구분야 명시)', 'Official invitation letter from the inviting research institution (no wage requirement; states the research period and field)', 'employer', None),
    e159_home_contract_proof=('원 소속 고용계약 입증 서류 (재직증명서, 고용계약서 등)', 'Proof of employment at the home institution (employment certificate, contract, etc.)', 'applicant', None),
    e159_bank_balance=('국내·외 은행 잔고 증명서 (해당자)', 'Domestic or overseas bank balance certificate (if applicable)', 'applicant', None),
    e159_orig_employer_consent=('원 고용주의 동의서', 'Consent of the original employer', 'employer', None),
    # ---- E-4
    e159_public_private_org_docs=('공사기관 설립관련 서류 (사업자등록증, 외국인투자기업등록증, 지사설치허가서 등)', 'Establishment documents of the public or private organisation (business registration, foreign-investment company registration, branch permit, etc.)', 'employer', None),
    e159_tech_import_docs=('기술도입계약신고수리서, 기술도입계약서(또는 용역거래 계약서) 또는 방산업체지정서 사본', 'Acceptance of the technology-import contract report, the technology-import contract (or service-transaction contract) or a copy of the defence-industry designation', 'employer', None),
    e159_tech_import_docs_stay=('기술도입계약신고수리서, 기술도입계약서(또는 용역거래인증서) 또는 방위산업체지정서 사본', 'Acceptance of the technology-import contract report, the technology-import contract (or service-transaction certificate) or a copy of the defence-industry designation', 'employer', None),
    e159_dispatch_order_or_employment=('파견명령서 (또는 재직증명서)', 'Dispatch order (or employment certificate)', 'employer', None),
    e159_ministry_recommendation_if_needed=('소관부처 장관의 고용추천서 (필요시)', 'Employment recommendation from the competent minister (if needed)', 'employer', None),
    # ---- E-5
    e159_degree_license_copy=('학위증 및 자격증(면허증) 사본', 'Copies of the degree certificate and licence', 'applicant', None),
    e159_central_agency_recommendation=('소관 중앙행정기관장의 고용추천서 또는 고용의 필요성을 입증할 수 있는 서류', 'Employment recommendation from the competent central agency head, or documents proving the need for employment', 'employer', None),
    e159_invitation_reason=('초청사유서', 'Statement of reasons for the invitation', 'employer', None),
    e159_degree_and_license_copy=('학위증 및 자격증 사본', 'Copies of the degree certificate and licence', 'applicant', None),
    e159_bizreg_or_permit=('사업자등록증 사본 또는 허가증이나 등록증 (특정사업 허가·등록 업체인 경우) 등', 'Copy of the business registration, or the permit or registration (for licensed or registered businesses), etc.', 'employer', None),
    e159_degree_copy_license_copy=('학위증 사본 및 자격증 사본', 'Copy of the degree certificate and copy of the licence', 'applicant', None),
    e159_ministry_recommendation=('소관부처 장관의 고용추천서', 'Employment recommendation from the competent minister', 'employer', None),
    # ---- E-8
    e159_standard_contract=('표준근로계약서', 'Standard labour contract', 'employer', None),
    e159_domestic_recruit_proof=('내국인 구인노력 증빙자료 (구인 광고내용 사본 및 최종 구인실적 등)', 'Proof of efforts to recruit Korean workers (copy of the job advertisement, final recruitment results, etc.)', 'employer', None),
    e159_farm_history=('본국에서의 농·어업 종사 이력', 'Record of farming or fishing work in the home country', 'applicant', None),
    e159_marriage_relative_docs=('결혼이민자 신분증, (국내용) 혼인관계증명서, (국내용) 가족관계증명서(혼인귀화자 해당), 기본증명서(혼인귀화자 해당), 결혼이민자의 친척 관계도, 거주국(체류국)에서 발급한 가족관계증명서', 'Marriage migrant\'s ID, (domestic) marriage certificate, (domestic) family-relation certificate (naturalised by marriage), basic certificate (naturalised by marriage), relatives chart, family-relation certificate issued in the country of residence', 'sponsor', None),
    e159_student_parent_docs=('유학생 외국인등록증, 재학증명서, 출생증명서 또는 가족관계증명서 등', 'The student\'s residence card, enrolment certificate, birth certificate or family-relation certificate, etc.', 'sponsor', None),
    e159_accommodation_table=('(계절근로자에게 제공 예정인) 숙소시설표', 'Table of the accommodation to be provided to the seasonal worker', 'employer', None),
    e159_mou_result=('업무협약(MOU) 체결 결과서 등', 'Report on the concluded MOU, etc.', 'local_government', None),
    e159_photo_3545=('사진 (35mm×45mm) 1매', 'One photo (35 mm × 45 mm)', 'applicant', None),
    e159_injury_insurance_e8=('산재보험 가입증명원(사업장 가입 신청 입증서류) 또는 농·어업인 안전보험 보험증권(안전보험 가입 확약서)', 'Industrial-accident insurance certificate (proof of the workplace\'s application) or farmers\'/fishers\' safety insurance policy (commitment to enrol)', 'employer', None),
    e159_travel_insurance=('여행자보험 가입증명서', 'Travel insurance certificate', 'applicant', None),
    e159_drug_test_e8=('마약검사 확인서 (검사결과는 밀봉상태로 제출)', 'Drug test certificate (submit the result sealed)', 'applicant', None),
    e159_lodging_inspection=('(지자체) 숙소점검 확인서', 'Accommodation inspection confirmation (local government)', 'local_government', None),
    # ---- E-9
    e159_crime_record_e9=('국적국의 권한 있는 기관이 발급한 범죄경력증명서', 'Criminal record certificate issued by the competent authority of your country of nationality', 'applicant', None),
    e159_health_status_form=('건강상태 확인서 (사증신청인 자필 기재)', 'Health status declaration (handwritten by the visa applicant)', 'applicant', None),
    e159_permit_and_contract_copy=('고용허가서 및 표준근로계약서 사본', 'Copies of the employment permit and the standard labour contract', 'employer', None),
    e159_workplace_survey=('사업장실태조사서', 'Workplace inspection report', 'employer', None),
    e159_construction_docs=('건설업등록증, 도급(하도급) 계약서', 'Construction business registration and the (sub)contract', 'employer', None),
    e159_construction_workforce_table=('건설현장에 대한 근무 중 외국인력 현황표 (해당 현장 책임건설업〈원 도급업체〉 작성)', 'Table of foreign workers at the construction site (prepared by the lead contractor)', 'business_entity', None),
    e159_farm_business_reg=('농업경영체등록(변경등록)확인서 (국립농산물품질관리원장 발급, 유효기간 1년)', 'Agricultural business registration confirmation (issued by NAQS, valid 1 year)', 'employer', None),
    e159_fishery_coastal=('연근해어업: 선박(어선)검사증서, 어업허가증(연안어업, 근해어업, 구획어업), 또는 어업면허증 및 관리선사용지정증(정치망어업)', 'Coastal/offshore fishing: vessel inspection certificate, fishing permit (coastal, offshore, zoned) or fishing licence and management-vessel designation (set-net)', 'employer', None),
    e159_fishery_aquaculture=('양식어업: 선박(어선)검사증서, 어업허가증 또는 어업면허증 또는 내수면어업신고필증', 'Aquaculture: vessel inspection certificate, fishing permit or licence, or inland-fishery report certificate', 'employer', None),
    e159_salt_permit=('천일염 생산 및 암염 채취업: 염제조업허가증 사본', 'Sea-salt / rock-salt production: copy of the salt-manufacturing permit', 'employer', None),
    e159_service_restaurant=('한식 음식점업: 사업자등록증 또는 영업신고증(지자체 발급), 위탁업체 또는 가맹점인 경우 위탁계약서·가맹계약서', 'Korean restaurants: business registration or business report (local government); outsourcing or franchise contract if applicable', 'employer', None),
    e159_service_hotel=('호텔·숙박업: 관광사업 등록증(지자체 발급)', 'Hotels and lodging: tourism business registration (local government)', 'employer', None),
    e159_forestry_docs=('임업: 산림사업시행법인(사업자등록증 및 산림사업법인 등록증), 국유림영림단(사업자등록증 및 국유림영림단 등록증), 산림조합·산림조합중앙회(사업자등록증 또는 위탁계약서), 원목생산업자(사업자등록증 및 목재생산업 등록증), 종묘생산법인(사업자등록증 또는 위탁계약서)', 'Forestry: forestry corporations (business registration and forestry-business registration), national-forest teams (business registration and team registration), forestry cooperatives (business registration or outsourcing contract), log producers (business registration and timber-production registration), seedling producers (business registration or outsourcing contract)', 'employer', None),
    e159_mining_docs=('광업원부(광업등록사무소 발급) 및 광물생산보고서', 'Mining register (issued by the mining registry) and mineral production reports', 'employer', None),
    e159_employment_change_form=('고용·연수 외국인 변동사유 발생신고서 (별지 32호 서식)', 'Report of a change concerning an employed or trainee foreigner (Form 32)', 'employer', None),
    e159_arc_copy=('외국인등록증 사본', 'Copy of the residence card', 'employer', None),
    e159_employer_id=('고용주 신분증 (고용주 직접 신고 시)', 'Employer\'s ID (when the employer reports in person)', 'employer', None),
    e159_staff_proxy_docs=('회사 직원 대리 신청 시 고용주 위임장, 재직증명서, 직원 신분증', 'If a staff member files: employer\'s power of attorney, employment certificate and staff ID', 'employer', None),
)

FORM34 = '① 신청서(별지 34호서식), 여권 및 외국인등록증, 수수료'
FORM34_PHOTO = '① 신청서(별지 34호서식), 여권 및 외국인등록증, 표준규격사진1장, 수수료'
VISA17 = '① 사증발급신청서 (별지 제17호 서식), 여권, 표준규격사진 1매, 수수료'
CVI21 = '① 사증발급인정신청서 (별지 제21호 서식), 여권, 표준규격사진 1매'
PROXY = '대리인 신청시 : 위임장, 대리인 재직증명서, 대리인 신분증 추가 제출'
EVISA_SAME = '모두 해당되며, 각 해당자 제출서류도 동일'
NOTE = dict(notes_ko=[OFFICER_NOTE_KO], notes_en=[OFFICER_NOTE_EN])


def visa17(anchor=VISA17):
    return [item('e159_visa_app_form', anchor=anchor), item('passport', anchor=anchor), item('photo', anchor=anchor), item('fee', anchor=anchor)]


def cvi21(anchor=CVI21):
    return [item('e159_cvi_app_form', anchor=anchor), item('passport', anchor=anchor), item('photo', anchor=anchor)]


def proxy(anchor=PROXY):
    return item('e159_proxy_docs', 'CONDITIONAL_REQUIRED', anchor=anchor, applies_when_ko='대리인이 신청하는 경우', applies_when_en='When a proxy files the application')


def form34(anchor=FORM34, photo=False, arc=True, fee=True):
    docs = [item('app_form_34', anchor=anchor), item('passport', anchor=anchor)]
    if arc:
        docs.append(item('arc', anchor=anchor))
    if photo:
        docs.append(item('photo1', anchor=anchor))
    if fee:
        docs.append(item('fee', anchor=anchor))
    return docs


def consent(anchor, conditional_ko='원 근무처가 있는 경우', conditional_en='If there is an original workplace'):
    return item('e159_prev_employer_consent', 'CONDITIONAL_REQUIRED', anchor=anchor, applies_when_ko=conditional_ko, applies_when_en=conditional_en)


def evisa(code, section):
    guidance(code, 'electronic_visa', manual=VISA, section=section, anchor=EVISA_SAME, completeness='PARTIALLY_STRUCTURED',
             summary_ko=f'{code}은(는) 전자사증 발급대상(전문인력 E-1, E-3, E-4, E-5 등)으로, 재외공관 방문 없이 대한민국비자포털에서 외국인 본인 또는 초청자(대리신청)가 신청합니다. 공관장 재량 사증 대상자와 사증발급인정서 발급대상자 모두 해당되며 제출서류도 각각 동일합니다.',
             summary_en=f'{code} is eligible for the electronic visa (professionals E-1, E-3, E-4, E-5, etc.): the applicant or the inviter (as proxy) applies on the Korea Visa Portal without visiting a mission. It covers both consular-discretion and confirmation-of-visa-issuance applicants, with the same documents as each.',
             channel_ko='대한민국비자포털 (www.visa.go.kr)', channel_en='Korea Visa Portal (www.visa.go.kr)',
             docs=[item('e159_same_as_visa_docs', 'SOURCE_MENTIONS_BUT_NOT_STRUCTURED', anchor=EVISA_SAME,
                        notes_ko='공관장 재량 사증 또는 사증발급인정서 항목의 제출서류를 확인하세요.', notes_en='See the documents listed for the consular-discretion visa or the confirmation of visa issuance.')],
             **NOTE)


def reentry(code, section, exempt_anchor, docs_anchor='신청서류 : 신청서(별지 34호서식), 여권 원본, 외국인등록증, 수수료'):
    guidance(code, 'reentry', section=section, anchor=exempt_anchor,
             summary_ko='외국인등록을 한 사람이 출국한 날부터 1년 이내(남은 체류기간이 1년보다 짧으면 그 기간 이내)에 재입국하면 재입국허가가 면제됩니다. 출국 후 체류기간 범위 내에서 1년을 넘겨 2년 안에 재입국하려면 복수재입국허가를 받습니다.',
             summary_en='Registered residents re-entering within one year of departure (or within the remaining stay if shorter) are exempt from the re-entry permit. To return within your permitted stay after more than one year but within two, obtain a multiple re-entry permit.',
             conditions_ko=['입국규제 및 사증발급규제자는 체류지 관할 출입국·외국인관서를 방문하여 재입국허가를 받아야 합니다.', '사우디아라비아, 이란, 리비아 국민은 복수재입국이 제한됩니다(결혼이민(F-6), 유학(D-2), 일반연수(D-4)는 가능).'],
             conditions_en=['People under entry or visa-issuance restrictions must visit the immigration office for their address to obtain a re-entry permit.', 'Nationals of Saudi Arabia, Iran and Libya are restricted from multiple re-entry (F-6, D-2 and D-4 holders excepted).'],
             docs=[item('app_form_34', 'CONDITIONAL_REQUIRED', anchor=docs_anchor, applies_when_ko='복수재입국허가를 신청하는 경우', applies_when_en='When applying for a multiple re-entry permit'),
                   item('passport_original', 'CONDITIONAL_REQUIRED', anchor=docs_anchor, applies_when_ko='복수재입국허가를 신청하는 경우', applies_when_en='When applying for a multiple re-entry permit'),
                   item('arc', 'CONDITIONAL_REQUIRED', anchor=docs_anchor, applies_when_ko='복수재입국허가를 신청하는 경우', applies_when_en='When applying for a multiple re-entry permit'),
                   item('fee', 'CONDITIONAL_REQUIRED', anchor=docs_anchor, applies_when_ko='복수재입국허가를 신청하는 경우', applies_when_en='When applying for a multiple re-entry permit')],
             **NOTE)


def c45_lecture(code, section, anchor, docs_anchor, contract_def='contract_original_copy', contract_anchor='④고용계약서원본 및 사본', scenario=None):
    guidance(code, 'activities_outside_status', scenario=scenario, section=section, anchor=anchor,
             summary_ko=f'전문인력({code}) 자격 소지자가 대학에서 90일 이내 강의활동을 하려면 단기취업(C-4-5) 자격으로의 체류자격외 활동허가를 받습니다. 총(학)장의 추천서, 고유번호증(사업자등록증) 사본, 고용계약서, 원근무처장의 동의서를 냅니다.',
             summary_en=f'{code} professionals who will lecture at a university for up to 90 days obtain permission for activities outside status as short-term employment (C-4-5), with the president\'s recommendation, the university\'s unique-number (business registration) copy, the employment contract and the original employer\'s consent.',
             period_ko='90일 이내', period_en='Up to 90 days',
             docs=form34(docs_anchor) + [item('e159_president_lecture_recommendation', anchor='총(학)장의 추천서'), item('e159_unique_no_or_bizreg_copy', anchor='고유번호증(사업자등록증)사본'),
                                         item(contract_def, anchor=contract_anchor, role='educational_institution'), item('e159_prev_employer_consent', anchor='원근무처장의 동의서')],
             **NOTE)


def workplace_report(code, section, anchor, docs, conditions_ko=(), conditions_en=(), **kw):
    guidance(code, 'workplace_change', section=section, anchor=anchor,
             summary_ko=f'{code} 자격으로 외국인등록을 하고 체류 중인 사람은 변경·추가되는 근무처에서 활동하는 데 필요한 자격요건을 갖추면 사전허가 없이 신고만으로 근무처를 변경·추가할 수 있으며, 신고사유 발생일부터 15일 이내에 관할 출입국·외국인관서에 신고합니다(대리인 신고 허용). 본인 귀책사유로 해고되거나 중도 퇴직한 뒤 원 고용주의 이적동의를 받지 못한 사람은 제외됩니다.',
             summary_en=f'Registered {code} holders who meet the requirements for the new or additional workplace may change or add a workplace by report instead of prior permission, filing within 15 days at the immigration office (a proxy may file). People dismissed or who quit for reasons attributable to themselves without the original employer\'s transfer consent are excluded.',
             timing_ko='신고사유 발생일부터 15일 이내', timing_en='Within 15 days of the event',
             conditions_ko=['원 근무처 장의 동의서는 계약기간 만료일 또는 쌍방이 근무하기로 합의한 날짜까지 근무한 경우 면제되며, 원 근무처의 휴·폐업 및 임금체불 등의 사유가 있으면 입증서류 또는 사유서로 대체할 수 있습니다.'] + list(conditions_ko),
             conditions_en=['The original workplace head\'s consent is waived if you worked until the contract end or the agreed date, and may be replaced by proof or a statement of reasons if the original workplace closed, suspended business or failed to pay wages.'] + list(conditions_en),
             docs=docs, **NOTE, **kw)


CONSENT_WAIVER_KO = '계약기간 만료일 또는 쌍방이 근무하기로 합의한 날짜까지 근무한 경우 면제, 원 근무처의 휴·폐업 및 임금체불 등의 경우 입증서류 또는 사유서로 대체 가능'
CONSENT_WAIVER_EN = 'Waived if you worked until the contract end or agreed date; replaceable by proof or a statement of reasons if the workplace closed or failed to pay wages'


def consent_report(anchor):
    return item('e159_prev_employer_consent', 'CONDITIONAL_REQUIRED', anchor=anchor, does_not_apply_when_ko=CONSENT_WAIVER_KO, does_not_apply_when_en=CONSENT_WAIVER_EN)


# ==========================================================================
# E-1 교수
# ==========================================================================
guidance('E-1', 'visa_issuance', manual=VISA, section='교수(E-1) 공관장 재량으로 발급할 수 있는 사증 — 1. 한국과학기술원 교수활동자 단수사증',
         anchor='한국과학기술원에 고용되어 교수활동을 하고자 하는 자에 대한 체류기간 1년 이하의 단수사증',
         summary_ko='한국과학기술원법령에 따라 교수·부교수·조교수·초빙교수 등으로 채용되어 교수활동을 하는 사람에게는 재외공관장이 체류기간 1년 이하의 단수사증을 발급할 수 있습니다. 사증발급신청서와 경력증명서·학위증, 고용계약서 또는 임용예정확인서를 냅니다.',
         summary_en='People hired under the KAIST Act as professors, associate, assistant or visiting professors can receive a single-entry visa of up to one year at the mission\'s discretion, with the visa application, career and degree certificates and the employment contract or appointment confirmation.',
         period_ko='체류기간 1년 이하 단수사증', period_en='Single-entry visa, stay of up to 1 year',
         docs=visa17() + [item('e159_career_and_degree', anchor='② 경력증명서 및 학위증'), item('contract_or_appointment', anchor='③ 고용계약서 또는 임용예정확인서', role='educational_institution')],
         **NOTE)

guidance('E-1', 'visa_issuance_confirmation', manual=VISA,
         section='교수(E-1) 사증발급인정서 발급대상 — 1. 전문대학 이상 교육기관에서 91일 이상 교육 또는 연구·지도활동을 하는 교원',
         anchor='전문대학 이상 교육기관에서 91일 이상 교육 또는 연구․지도활동을 하는 대학의 장',
         summary_ko='전문대학 이상 교육기관에서 91일 이상 교육 또는 연구·지도활동을 하는 총·학장, 교수·부교수·조교수, 겸임교원·명예교수·초빙교원, 교환교수 등은 사증발급인정신청서, 경력증명서·학위증(조교수 이상 자격기준 해당 전임교수 등은 생략), 고용계약서 또는 임용예정확인서, 초청학교 설립관련 서류를 냅니다.',
         summary_en='Presidents, professors, adjunct, emeritus, visiting and exchange professors teaching or supervising research for 91+ days at a junior college or higher submit the application, career and degree certificates (omitted for full-time faculty meeting the assistant-professor standard), the employment contract or appointment confirmation and the school\'s establishment documents.',
         doc_page_window=3,
         docs=cvi21() + [
             item('e159_career_and_degree', 'CONDITIONAL_REQUIRED', anchor='경력증명서 및 학위증 - 조교수 이상의 자격기준에 해당하는 전임교수 등의 경우 제출 생략', does_not_apply_when_ko='조교수 이상의 자격기준에 해당하는 전임교수 등', does_not_apply_when_en='Full-time faculty meeting the assistant-professor standard or above'),
             item('contract_or_appointment', anchor='③ 고용계약서 또는 임용예정확인서 - 파견 또는 협약에 따른 교환교수', role='educational_institution',
                  notes_ko='파견 또는 협약에 따른 교환교수, 방문교수 등은 대학 명의의 위촉·초청 공문(임금요건 불필요)으로 대체할 수 있습니다(경력증명서 및 학위증 생략 가능).', notes_en='Exchange or visiting professors under a dispatch or agreement may substitute an appointment/invitation letter in the university\'s name (no wage requirement; career and degree certificates may be omitted).'),
             item('e159_school_establishment_docs', anchor='사업자등록증 사본 또는 법인등기사항전부증명서'),
             proxy()],
         **NOTE)

guidance('E-1', 'visa_issuance_confirmation', scenario='advanced-science-talent', manual=VISA,
         section='교수(E-1) 사증발급인정서 발급대상 — 2. 교육부장관의 추천을 받은 고급과학 기술인력',
         anchor='교육부장관의 추천을 받고 전문대학 이상의 교육기관에서 과학기술 분야의 교육․연구지도 활동에 종사하는 고급과학 기술인력',
         summary_ko='교육부장관의 추천을 받아 전문대학 이상 교육기관에서 과학기술 분야 교육·연구지도를 하는 고급과학 기술인력(이공계 박사 또는 이공계 석사 + 해당분야 3년 이상)은 사증발급인정신청서, 고용계약서 또는 임용예정확인서, 교육부장관의 ‘고급과학기술인력’ 고용추천서, 초청기관 설립관련 서류를 냅니다. 학위증과 경력증명서는 제출이 면제됩니다.',
         summary_en='Advanced science and technology personnel recommended by the Minister of Education (STEM PhD, or STEM master\'s plus 3 years of R&D) submit the application, employment contract or appointment confirmation, the Minister\'s recommendation and the institution\'s establishment documents; degree and career certificates are exempt.',
         docs=cvi21('① 사증발급인정신청서 (별지 제21호 서식), 여권, 표준규격사진 1매 ② 고용계약서 또는 임용예정확인서') + [
             item('contract_or_appointment', anchor='② 고용계약서 또는 임용예정확인서', role='educational_institution'),
             item('e159_moe_talent_recommendation', anchor='교육부장관의 ‘고급과학기술인력’ 고용추천서',
                  notes_ko='경제자유구역 내에서 취업활동을 하려는 사람은 관할 특별시장·광역시장·도지사의 고용추천서 또는 고용의 필요성을 입증할 수 있는 서류를 냅니다.', notes_en='For work in a free economic zone, a recommendation from the metropolitan mayor or governor, or proof of the need for employment.'),
             item('e159_inviting_institution_docs', anchor='④ 초청기관 설립관련 서류 (사업자등록증 또는 법인등기사항전부증명서)'),
             item('e159_bk21_letter', 'ADDITIONAL_IF_APPLICABLE', anchor='⑤ BK21 관련 공문 사본 (해당자에 한함)', applies_when_ko='BK21 관련 해당자', applies_when_en='BK21-related applicants'),
             proxy()],
         **NOTE)

evisa('E-1', '교수(E-1) 전자사증 — 1. 발급대상')

E1_SC = '교수(E-1) 체류자격 변경허가'
guidance('E-1', 'status_change', section=f'{E1_SC} — 1. 외국고급인력의 교수(E-1)·연구(E-3)로의 변경 및 상호간 변경',
         anchor='부득이한 사유로 무사증입국하거나 비취업사증을 소지한 외국고급인력에 대한 교수(E-1), 연구(E-3)로 체류자격 변경 허가',
         summary_ko='부득이한 사유로 무사증입국하거나 비취업사증을 가진 외국고급인력이 전문대학 이상 교육기관이나 연구기관에 근무하려는 경우, 그리고 교수(E-1)·연구(E-3) 상호간 변경의 자격기준은 석사학위 이상 + 해당분야 경력 3년 또는 박사학위입니다. 고용계약서(또는 임용예정 확인서), 경력증명서, 회사설립관련서류 등을 냅니다.',
         summary_en='Highly skilled foreigners who entered visa-free or on a non-work visa for unavoidable reasons and will work at a junior college or higher or a research institute, and E-1↔E-3 changes, require a master\'s plus 3 years of experience or a doctorate. Submit the employment contract (or appointment confirmation), career certificate, company establishment documents, etc.',
         conditions_ko=['자격기준: 석사학위 이상으로 해당분야 경력 3년 종사한 경력이 있는 사람 또는 박사학위 소지자'], conditions_en=['Eligibility: master\'s degree or higher with 3 years in the field, or a doctorate'],
         docs=form34('① 신청서(제 34호 서식), 여권, 표준규격사진 1장, 수수료 ② 고용계약서 원본 및 사본(또는 임용예정 확인서)', photo=True, arc=False) + [
             item('e159_contract_or_appointment_orig', anchor='② 고용계약서 원본 및 사본(또는 임용예정 확인서)', role='employer'),
             item('e159_career_with_degree_copy', anchor='③경력증명서(학위증 사본 첨부)'),
             item('e159_company_establishment_docs', anchor='④ 회사설립관련서류(사업자등록증, 연구기관 입증서류)'),
             consent('⑤ 원 근무처장의 동의서(원 근무처가 있는 경우)')],
         **NOTE)

SPOUSE_KO = '전문외국인력《E-1 내지 E-5, E-6(E-6-2는 제외), E-7》 자격소지자의 배우자로서 동반(F-3) 자격을 가진 사람은 전문직에 해당하는 모든 직종으로 체류자격 변경허가를 받을 수 있으며, 사업자등록증, 학위증(원본 및 사본) 또는 경력증명서, 고용계약서(원본 및 사본) 등을 냅니다.'
SPOUSE_EN = 'Spouses holding F-3 of professionals (E-1 to E-5, E-6 except E-6-2, E-7) may change into any professional occupation, submitting the business registration, the degree certificate (original and copy) or a career certificate, the employment contract (original and copy), etc.'


def spouse_change(code, section, anchor, bizreg_anchor='② 사업자등록증 ③학위증(원본 및 사본) 또는 경력증명서'):
    guidance(code, 'status_change', scenario='professional-spouse', section=section, anchor=anchor, summary_ko=SPOUSE_KO, summary_en=SPOUSE_EN,
             docs=form34(FORM34_PHOTO, photo=True) + [
                 item('business_reg', anchor=bizreg_anchor, role='employer'),
                 item('e159_degree_or_career_orig', anchor='③학위증(원본 및 사본) 또는 경력증명서'),
                 item('contract_original_copy', anchor='④고용계약서 (원본 및 사본)', role='employer'),
                 consent('⑤원 근무처의 장의 동의서(원 근무처가 있는 경우만 해당)')],
             **NOTE)


D2D10_COND_KO = ['구직(D-10) 또는 유학(D-2) 자격으로 합법 체류 중이고, 취업하려는 분야가 E-1~E-7 체류자격에 해당하여 그 자격요건을 갖추었으며, 해당 기관·단체 대표자와 고용계약을 체결해야 합니다(세 요건 모두 충족).',
                 '유학(D-2) 자격 소지자는 구직(D-10)으로 변경할 수 있는 요건을 갖춘 졸업예정자를 뜻합니다. 다만 자국 또는 제3국 대학에서 이미 학사 이상 학위를 취득하고 필요한 경력요건 등을 갖춘 경우에는 재학 중이라도 변경이 허용됩니다.']
D2D10_COND_EN = ['You must be lawfully staying on D-10 or D-2, the intended work must fall under E-1 to E-7 with its requirements met, and you must have an employment contract with the head of the institution (all three).',
                 'A D-2 holder means a prospective graduate eligible to change to D-10; students who already hold a bachelor\'s or higher from their own or a third country and meet the experience requirements may change while still enrolled.']

spouse_change('E-1', f'{E1_SC} — 2. 전문외국인력의 배우자에 대한 전문직자격으로의 변경허가', '전문외국인력의 배우자에 대한 전문직자격으로의 변경허가')

guidance('E-1', 'status_change', scenario='from-d2-d10', section=f'{E1_SC} — 3. 유학(D-2), 구직(D-10) ➠ 교수(E-1)자격으로의 변경', anchor='유학(D-2), 구직(D-10) ➠ 교수(E-1)자격으로의 변경',
         summary_ko='유학(D-2) 또는 구직(D-10)에서 교수(E-1)로 변경하려면 고용계약서, 학위증 또는 경력증명서(조교수 이상 자격기준에 해당하는 전임교수 등은 생략), 고용업체 등 설립관련 서류를 냅니다.',
         summary_en='To change from D-2 or D-10 to E-1, submit the employment contract, a degree or career certificate (omitted for full-time faculty meeting the assistant-professor standard) and the employer\'s establishment documents.',
         conditions_ko=D2D10_COND_KO, conditions_en=D2D10_COND_EN,
         docs=form34() + [item('employment_contract', anchor='②고용계약서 ③ 학위증 또는 경력증명서', role='employer'),
                          item('e159_degree_or_career', 'CONDITIONAL_REQUIRED', anchor='③ 학위증 또는 경력증명서', does_not_apply_when_ko='조교수 이상의 자격기준에 해당하는 전임교수 등', does_not_apply_when_en='Full-time faculty meeting the assistant-professor standard or above'),
                          item('e159_employer_establishment_docs', anchor='④고용업체 등 설립관련 서류(사업자등록증, 등기부등본 등)')],
         **NOTE)

guidance('E-1', 'status_change', scenario='stem-graduate', section=f'{E1_SC} — 4. 이공계대학 졸업 유학생의 교육·과학기술 분야 연구·지도 활동',
         anchor='이공계대학 졸업 유학생 중 교육․과학기술 분야의 연구․지도 활동에 종사하려는 경우',
         summary_ko='이공계 대학을 졸업한 유학생 중 석사 이상 학위를 취득한 사람이 교육·과학기술 분야 연구·지도 활동에 종사하려면 졸업증명서, 고용계약서, 총(학)장의 고용추천서, 사업자등록증을 냅니다.',
         summary_en='International STEM graduates with a master\'s or higher who will do research or supervision in education or science and technology submit the graduation certificate, employment contract, the president\'s employment recommendation and the business registration.',
         docs=form34('①신청서(별지 34호서식), 여권 및 외국인등록증, 수수료 ②졸업증명서') + [
             item('e159_graduation_cert', anchor='②졸업증명서'), item('employment_contract', anchor='③고용계약서 ④총(학)장의 고용추천서', role='employer'),
             item('e159_president_recommendation', anchor='④총(학)장의 고용추천서'), item('business_reg', anchor='④총(학)장의 고용추천서 ⑤사업자등록증', role='employer')],
         **NOTE)

E1_AOS = '교수(E-1) 체류자격외 활동'
c45_lecture('E-1', f'{E1_AOS} — 3. 외국인투자기업 CEO 등 우수전문인력의 대학 강연활동', '외국인투자기업 CEO 등 우수전문인력의 대학 강연활동',
            '①신청서(별지 34호 서식), 여권 및 외국인등록증, 수수료 ②총(학)장의 추천서')

guidance('E-1', 'activities_outside_status', scenario='e1-e3-mutual', section=f'{E1_AOS} — 4. 외국고급과학 기술인력의 교수(E-1), 연구(E-3)간 상호 체류자격외 활동',
         anchor='교수(E-1) 또는 연구(E-3) 자격을 소지한 외국고급과학 기술인력에 대한 교수(E-1), 연구(E-3)간 상호 체류자격외 활동',
         summary_ko='교수(E-1) 또는 연구(E-3) 자격의 외국고급과학 기술인력이 교육부장관의 고용추천을 받아 이공계 교육·연구기관에서 상대 자격 활동을 하려면 체류자격외 활동허가를 받습니다. 이공계 석사 + 연구개발 3년 이상 또는 이공계 박사여야 하며, 고용계약서 또는 임용예정확인서, 원 고용주의 동의서, 교육부장관의 고용추천서 등을 냅니다.',
         summary_en='E-1 or E-3 advanced science personnel recommended by the Minister of Education who will also work in the other status at a STEM education or research institution need permission for activities outside status. They need a STEM master\'s plus 3 years of R&D or a STEM doctorate and submit the contract or appointment confirmation, the original employer\'s consent, the Minister\'s recommendation, etc.',
         conditions_ko=['자격기준: 이공계 석사학위 이상 소지자로서 해당분야 연구개발 업무에 3년 이상 종사한 경력이 있는 사람 또는 이공계 박사학위 소지자'], conditions_en=['Eligibility: STEM master\'s or higher with 3+ years of R&D in the field, or a STEM doctorate'],
         docs=form34('①신청서(별지 34호 서식), 여권 및 외국인등록증, 표준규격사진 1장, 수수료', photo=True) + [
             item('contract_or_appointment', anchor='② 고용계약서 또는 임용예정확인서 ③원 고용주의 동의서', role='employer'),
             item('e159_orig_employer_consent', anchor='③원 고용주의 동의서'), item('e159_moe_recommendation', anchor='④교육부장관의 고용추천서'),
             item('business_reg_copy', anchor='⑤ 사업자등록증 사본 ⑥ 연구기관 입증서류', role='employer'), item('e159_research_institution_proof', anchor='⑥ 연구기관 입증서류')],
         **NOTE)

guidance('E-1', 'activities_outside_status', scenario='e1-to-d6-same-foundation', section=f'{E1_AOS} — 9. 동일 종교재단 산하기관 근무자의 교수(E-1) → 종교(D-6)',
         anchor='나. 교수(E-1) → 종교(D-6)의 경우 제출서류',
         summary_ko='같은 종교재단 산하기관에서 근무하는 교수(E-1)가 종교(D-6) 활동을 하려면 동일재단 입증서류, 원근무처의 동의서, 해당단체 설립허가서를 냅니다.',
         summary_en='An E-1 professor working at an institution under the same religious foundation who will carry out D-6 religious activities submits proof of the same foundation, the original workplace\'s consent and the organisation\'s establishment permit.',
         docs=form34('①신청서(별지34호 서식). 여권 및 외국인등록증, 수수료 ②동일재단입증서류 ③원근무처의 동의서') + [
             item('e159_same_foundation_proof', anchor='②동일재단입증서류 ③원근무처의 동의서'), item('e159_prev_employer_consent', anchor='③원근무처의 동의서 ④ 해당단체 설립허가서'),
             item('e159_org_establishment_permit', anchor='④ 해당단체 설립허가서')],
         **NOTE)

workplace_report('E-1', '교수(E-1) 근무처의 변경·추가 — 신고제', '교수(E-1) 자격으로 외국인등록을 하고 체류하고 있는 자로 변경․추가되는 근무처에서 활동하는데 필요한 자격요건을 구비하고 있는 자',
                 [item('e159_workplace_report_form', anchor='①근무처변경‧추가 신고서[별지 제38호의3서식], 여권 및 외국인등록증, 수수료'),
                        item('passport', anchor='①근무처변경‧추가 신고서[별지 제38호의3서식], 여권 및 외국인등록증, 수수료'),
                        item('arc', anchor='①근무처변경‧추가 신고서[별지 제38호의3서식], 여권 및 외국인등록증, 수수료'),
                        item('fee', anchor='①근무처변경‧추가 신고서[별지 제38호의3서식], 여권 및 외국인등록증, 수수료'),
                        item('business_reg', anchor='②사업자등록증 ③원 근무처 장의 동의서', role='employer'),
                        consent_report('③원 근무처 장의 동의서 ④고용계약서'),
                        item('employment_contract', anchor='④고용계약서', role='employer')],
                 conditions_ko=['대학교수가 전공과 관련하여 일시적인 강연·강의·연구 등의 활동을 다른 대학에서 하는 경우에는 근무처 추가신고가 필요 없습니다.', '여권에 신고 스티커를 부착해야 하므로 방문신고가 원칙입니다(신고기한이 임박한 경우 FAX 선접수 후 방문).'],
                 conditions_en=['No additional-workplace report is needed when a professor gives temporary lectures, classes or research related to their field at another university.', 'Reports are filed in person because a sticker is attached to the passport (if the deadline is imminent, fax first and visit soon after).'])

reentry('E-1', '교수(E-1) 재입국허가', '등록을 필한 외국인이 출국한 날로부터 1년 이내에 재입국하려는 경우 재입국허가 면제')

# ==========================================================================
# E-2 회화지도
# ==========================================================================
# 공관장 재량 사증 = EPIK·CPIK·TaLK (E-2-2; FTA 영어보조교사는 E-2-91). 사증발급인정서 = E-2-1.
guidance('E-2-2', 'visa_issuance', manual=VISA, covers=['E-2-91'],
         section='회화지도(E-2) 공관장 재량으로 발급할 수 있는 사증 — 1. 시·도 교육감 등과 고용계약을 체결한 초·중·고등학교 외국어보조교사',
         anchor='외국어보조교사로 근무하고자 하는 자에 대한 체류기간 2년 이하의 단수사증',
         summary_ko='시·도 교육감 등과 고용계약을 체결하고 초·중·고등학교 등에서 회화지도를 하는 원어민 영어보조교사(EPIK)·중국어보조교사(CPIK)와 정부초청 해외 영어봉사장학생(TaLK)은 재외공관장 재량으로 단수사증(E-2-2, FTA 영어보조교사는 E-2-91)을 받습니다. 사증발급신청서, 합격증 또는 TaLK 장학생 초청장, 시·도 교육감 등과 체결한 고용계약서를 냅니다.',
         summary_en='Native English (EPIK) and Chinese (CPIK) assistant teachers and TaLK scholars under contract with a provincial superintendent receive a single-entry visa at the mission\'s discretion (E-2-2; E-2-91 for FTA English assistant teachers), with the visa application, the pass certificate or TaLK invitation and the employment contract with the superintendent.',
         period_ko='최대 2년 범위 내 계약기간 + 1개월 (단수사증, 미국인은 복수사증)', period_en='Contract period + 1 month, up to 2 years (single-entry; multiple-entry for US nationals)',
         conditions_ko=['해외 소재 대한민국 공관이면 어디서나 신청할 수 있습니다(중국어보조교사는 주중 대한민국공관에만 신청).', 'EPIK, CPIK, TaLK 프로그램을 통하지 않고 시·도 교육감이 자체 채용한 보조교사는 사증발급인정서를 통한 E-2-1 발급 대상입니다.'],
         conditions_en=['You may apply at any Korean mission abroad (Chinese assistant teachers only at missions in China).', 'Assistant teachers hired directly by a superintendent outside EPIK, CPIK or TaLK are issued E-2-1 through a confirmation of visa issuance.'],
         docs=visa17() + [
             item('e159_e2_pass_cert', anchor='원어민 영어 보조교사 또는 원어민 중국어보조교사 합격증 또는 Talk장학생 초청장',
                  notes_ko='국립국제교육원 또는 시·도교육감이 학력사항과 범죄경력 등을 검증한 뒤 합격통지서·초청장을 발급하므로 해당 서류는 원칙적으로 제출이 면제됩니다.', notes_en='NIIED or the superintendent verifies education and criminal records before issuing the pass notice or invitation, so those documents are in principle not required.'),
             item('e159_moe_contract', anchor='③ 시·도 교육감 등과 체결한 고용계약서')],
         **NOTE)

guidance('E-2-1', 'visa_issuance_confirmation', manual=VISA, doc_page_window=3,
         section='회화지도(E-2) 사증발급인정서 발급대상 — 1. 사증발급인정서에 의한 회화지도(E-2) 사증발급',
         anchor='사증발급인정서에 의한 회화지도(E-2) 사증발급',
         summary_ko='외국어학원, 초등학교 이상 교육기관·부설 어학연구소, 기관·단체 부설 연수원, 평생교육시설, 직업능력개발훈련시설, 어학기자재를 갖춘 법인기업·공공기관 등의 회화지도 강사는 회화지도(E-2-1) 사증발급인정서를 받습니다. 공적확인을 받은 학력증명서와 범죄경력증명서, 자기건강확인서, 고용계약서와 학원·단체 설립관련 서류 등을 냅니다.',
         summary_en='Conversation instructors at foreign-language academies, schools and their language institutes, in-house training centres, lifelong-education and vocational-training facilities, or companies and public bodies with language classrooms receive an E-2-1 confirmation of visa issuance. Submit officially confirmed education and criminal-record certificates, a self-declaration of health, the employment contract and the academy/organisation establishment documents.',
         period_ko='최대 2년 범위 내 계약기간 + 1개월', period_en='Contract period + 1 month, up to 2 years',
         conditions_ko=['국내 대학에서 학위를 취득한 경우 공적확인을 받지 않은 학위증 사본을 낼 수 있고, 과거에 공적확인을 받은 학력 입증서류를 낸 경우에는 제출이 면제됩니다.',
                        '범죄경력증명서는 접수일 기준 6개월 이내 발급분이어야 합니다. 과거에 공적확인을 받은 범죄경력증명서를 내고 체류하다 출국한 뒤 3개월 이내 재신청하면 면제되며, 재입국일 기준 해외 체류기간이 3개월을 넘으면 외국인등록 시 새로 냅니다.',
                        '사증신청과 심사·발급은 모든 해외 소재 대한민국 공관에서 할 수 있습니다.'],
         conditions_en=['Holders of a Korean university degree may submit an unconfirmed copy of the degree; those who submitted officially confirmed education proof before are exempt.',
                        'The criminal record must be issued within 6 months of filing. It is waived if you previously submitted a confirmed one and reapply within 3 months of departure; if you stayed abroad more than 3 months, submit a new one at registration.',
                        'The visa may be applied for and issued at any Korean mission abroad.'],
         docs=cvi21() + [
             item('e159_degree_cert_confirmed', anchor='학위증 사본, 학위취득 증명서, 학위취득 사실이 기재된 졸업증명서 중 1종만 제출'),
             item('e159_crime_record_home', anchor='을 받은 자국정부 발급 범죄경력증명서 (자국 전역의 범죄경력이 포함되어 있어야 함)', validity_period='접수일 기준 6개월 이내 발급'),
             item('e159_crime_record_third', 'CONDITIONAL_REQUIRED', anchor='④ 공적확인을 받은 제3국 범죄경력증명서', applies_when_ko='자국 이외의 국가에서 학위를 취득한 경우', applies_when_en='If your degree was obtained outside your country of nationality'),
             item('e159_self_health_check', anchor='⑤ 자기건강확인서'),
             item('e159_contract_min_wage', anchor='⑥ 고용계약서(최소 임금요건 : 당해연도 최저임금 이상)'),
             item('e159_academy_establishment', anchor='학원 또는 단체 설립관련 서류'),
             item('e159_e2_reference_docs', 'ADDITIONAL_IF_APPLICABLE', anchor='강사활용계획서, 수강생 및 직원현황 등'),
             proxy()],
         **NOTE)

E2_SC = '회화지도(E-2) 체류자격 변경허가'
E2_SC_COND_KO = ['등록외국인(A-1, A-2, A-3 포함)과 시·도교육감 초청 초·중등학교 영어보조교사로 채용되어 강의하려는 사람은 소지한 체류자격에 관계없이 청장 등이 허가합니다.',
                 '과거에 공적확인을 받은 학력·범죄경력증명서와 채용신체검사서를 낸 사실이 확인되고 구직(D-10) 등으로 자격을 변경하여 계속 체류 중인 사람은 이 서류들의 제출이 면제됩니다.',
                 '시·도교육감과 고용계약을 체결한 초·중등학교 영어보조교사(EPIK, CPIK, TaLK)는 학력·경력 증명서와 채용신체검사서 제출이 면제되고 합격증명서와 고용계약서 등 최소서류만 냅니다.',
                 '고용계약서상 임금이 당해연도 최저임금에 미달하면 원칙적으로 체류자격 변경허가가 억제됩니다.']
E2_SC_COND_EN = ['Registered foreigners (including A-1 to A-3) and people hired as English assistant teachers invited by a provincial superintendent are permitted by the office head regardless of their current status.',
                 'People confirmed to have submitted officially confirmed education and criminal records and a medical report before, and who stayed on by changing to D-10 etc., are exempt from those documents.',
                 'English assistant teachers under contract with a superintendent (EPIK, CPIK, TaLK) are exempt from education/career proof and the medical report and submit only minimal documents such as the pass certificate and contract.',
                 'If the contract wage is below this year\'s minimum wage, the change is in principle not permitted.']

guidance('E-2', 'status_change', section=f'{E2_SC} — 2. 회화지도(E-2) 요건을 갖춘 등록 외국인(A-1, A-2, A-3 포함)', anchor='회화지도(E-2)요건을 갖춘 등록 외국인(A-1,A-2,A-3포함)', doc_page_window=3,
         summary_ko='회화지도(E-2) 자격요건을 갖춘 등록외국인(A-1, A-2, A-3 포함)은 국내에서 E-2로 변경할 수 있습니다. 고용계약서 원본과 사본, 사업자등록증 사본, 공적확인을 받은 학력증명서와 범죄경력증명서(6개월 이내 발급), 채용신체검사서(밀봉 제출) 등을 냅니다. 범죄경력이 있으면 원칙적으로 불허됩니다.',
         summary_en='Registered foreigners (including A-1 to A-3) who meet the E-2 requirements may change to E-2 in Korea, submitting the employment contract (original and copy), business registration copy, officially confirmed education proof and criminal record (issued within 6 months) and a sealed pre-employment medical report. A criminal record in principle leads to refusal.',
         conditions_ko=E2_SC_COND_KO, conditions_en=E2_SC_COND_EN,
         docs=form34('① 신청서(별지 34호 서식), 여권 및 외국인등록증, 표준규격사진1장, 수수료 ② 고용계약서 원본과 사본', photo=True) + [
             item('e159_contract_orig_and_copy', anchor='② 고용계약서 원본과 사본 ③ 사업자등록증 사본', role='employer'),
             item('business_reg_copy', anchor='③ 사업자등록증 사본 ④ 공적확인', role='employer'),
             item('e159_degree_confirmed_stay', anchor='④ 공적확인*을 받은 학력증명서',
                  notes_ko='국내 대학에서 학위를 취득한 경우 공적확인을 받지 않은 학위증 사본 제출이 허용되고, 과거에 공적확인을 받은 학력 입증서류를 낸 경우 면제됩니다.', notes_en='A Korean-university degree may be submitted as an unconfirmed copy; exempt if confirmed proof was submitted before.'),
             item('e159_crime_record_6m', anchor='신청일로부터 6개월 이내에 발급 받은 공적확인*을 받은 범죄경력증명서',
                  notes_ko='과거에 공적확인을 받은 범죄경력증명서를 내고 체류하다 출국한 뒤 3개월 이내 신청하면 면제됩니다.', notes_en='Waived if you submitted a confirmed one before and apply within 3 months of departure.'),
             item('e159_crime_record_third', 'CONDITIONAL_REQUIRED', anchor='⑥ 공적확인을 받은 제3국 범죄경력증명서', applies_when_ko='자국 이외의 국가에서 학위를 취득한 경우', applies_when_en='If your degree was obtained outside your country of nationality'),
             item('recruit_medical_sealed', anchor='⑦ 채용신체검사서* (반드시 봉투에 밀봉된 상태로 제출, 개봉 불가)')],
         **NOTE)

guidance('E-2', 'status_change', scenario='moe-english-teacher', section=f'{E2_SC} — 1. 교육부(시·도 교육감) 초청 외국인영어강사',
         anchor='로 채용되어 초․중․고교생을 대상으로 강의를 하려는 자에 대하여는 소지한 자격에 상관없이 E-2 자격변경 가능',
         summary_ko='교육부(시·도 교육감) 초청 외국인영어강사로 채용되어 초·중·고교생을 가르치려는 사람은 소지한 자격에 관계없이 E-2로 변경할 수 있으며, 합격통지서, 고용계약서 원본과 사본, 학교 사업자등록증(또는 고유번호증) 사본을 냅니다.',
         summary_en='People hired as foreign English teachers invited by the Ministry of Education or a provincial superintendent to teach primary/secondary students may change to E-2 regardless of their status, submitting the pass notice, the employment contract (original and copy) and a copy of the school\'s business registration (or unique-number certificate).',
         conditions_ko=E2_SC_COND_KO[2:3], conditions_en=E2_SC_COND_EN[2:3],
         docs=[item('app_form_34', anchor='① 신청서(별지 34호 서식), 여권 및 외국인등록증(해당자), 표준규격사진 1장, 수수료'),
               item('passport', anchor='① 신청서(별지 34호 서식), 여권 및 외국인등록증(해당자), 표준규격사진 1장, 수수료'),
               item('arc', 'ADDITIONAL_IF_APPLICABLE', anchor='여권 및 외국인등록증(해당자)', applies_when_ko='외국인등록을 한 사람', applies_when_en='If you are registered'),
               item('photo1', anchor='표준규격사진 1장, 수수료 ② 시'), item('fee', anchor='표준규격사진 1장, 수수료 ② 시'),
               item('e159_pass_notice', anchor='교육감이나 국립국제교육원장이 발급한 합격통지서 또는 통지서'),
               item('e159_contract_orig_and_copy', anchor='③ 고용계약서 원본과 사본 ④ 학교', role='educational_institution'),
               item('e159_school_bizreg_copy', anchor='④ 학교 사업자등록증 사본(또는 고유번호증사본)')],
         **NOTE)

guidance('E-2', 'status_change', scenario='from-d2-d10', section=f'{E2_SC} — 3. 유학(D-2), 구직(D-10) ➠ 회화지도(E-2)자격으로의 변경', anchor='유학(D-2), 구직(D-10) ➠ 회화지도(E-2)자격으로의 변경',
         summary_ko='유학(D-2) 또는 구직(D-10)에서 회화지도(E-2)로 변경하려면 고용계약서, 학위증 또는 경력증명서, 고용업체 등 설립관련 서류, 범죄경력증명서(자국 및 해당자는 제3국), 채용신체검사서(밀봉 제출)를 냅니다.',
         summary_en='To change from D-2 or D-10 to E-2, submit the employment contract, a degree or career certificate, the employer\'s establishment documents, criminal record certificates (home country, and a third country if applicable) and a sealed pre-employment medical report.',
         conditions_ko=D2D10_COND_KO, conditions_en=D2D10_COND_EN,
         docs=form34('①신청서(별지 34호서식), 여권 및 외국인등록증, 수수료 ②고용계약서 ③ 학위증 또는 경력증명서') + [
             item('employment_contract', anchor='②고용계약서 ③ 학위증 또는 경력증명서 ④ 고용업체', role='employer'),
             item('e159_degree_or_career', anchor='③ 학위증 또는 경력증명서 ④ 고용업체 등 설립관련 서류(사업자등록증, 학원설립증'),
             item('e159_employer_establishment_e2', anchor='고용업체 등 설립관련 서류(사업자등록증, 학원설립증, 등기부등본 등)'),
             item('e159_crime_record_home_third', anchor='⑤ 범죄경력증명서(자국 및 제3국(해당자))'),
             item('recruit_medical_sealed', anchor='⑥ 채용신체검사서(반드시 봉투에 밀봉된 상태로 제출, 개봉 불가)')],
         **NOTE)

E2_AOS = '회화지도(E-2) 체류자격외 활동'
guidance('E-2', 'activities_outside_status', section=f'{E2_AOS} — 3. 회화지도(E-2) 자격요건을 갖춘 등록외국인(A-1, A-2, A-3 포함)', anchor='회화지도(E-2)자격 요건을 갖춘 등록외국인(A-1, A-2, A-3포함)', doc_page_window=3,
         summary_ko='다른 체류자격으로 등록한 외국인(A-1, A-2, A-3 포함)이 회화지도(E-2) 자격요건을 갖추면 회화지도 활동을 위한 체류자격외 활동허가를 받을 수 있습니다. 시·도교육감과 근로계약을 맺은 영어보조교사는 합격증명서와 고용계약서만 내고, 그 밖의 회화지도강사는 고용계약서, 사업자등록증 사본, 공적확인을 받은 학력증명서·범죄경력증명서, 채용신체검사서 등을 냅니다.',
         summary_en='Foreigners registered in another status (including A-1 to A-3) who meet the E-2 requirements may obtain permission for conversation-teaching as an activity outside status. English assistant teachers under contract with a superintendent submit only the pass certificate and contract; other instructors submit the contract, business registration copy, confirmed education and criminal records, a medical report, etc.',
         conditions_ko=['직장 내에서 동료직원 등을 대상으로 하는 외국어 회화지도(E-1~E-7, D-5~D-9 등록 합법 체류자)와 학교·종교 등 사회복지시설·주민센터 등에서 영리 또는 유상 목적이 아닌 사회봉사활동 차원의 회화지도는 체류자격외 활동 허가(신고) 대상이 아닙니다. 회화지도가 주된 활동이 되거나 허용기준을 벗어나면 제외됩니다.',
                        '범죄경력이 있으면 원칙적으로 불허됩니다.'],
         conditions_en=['Teaching colleagues at your own workplace (lawful E-1 to E-7 and D-5 to D-9 residents) and unpaid volunteer conversation teaching at schools, religious or welfare facilities or community centres need no permission or report; this does not apply where teaching becomes the main activity or exceeds those limits.',
                        'A criminal record in principle leads to refusal.'],
         docs=form34('① 신청서(별지 34호 서식), 여권 및 외국인등록증, 수수료 ② 합격증명서') + [
             item('e159_pass_cert', 'CONDITIONAL_REQUIRED', anchor='② 합격증명서  ③ 고용계약서', applies_when_ko='시·도교육감과 근로계약을 체결한 영어보조교사', applies_when_en='English assistant teachers under contract with a provincial superintendent',
                  notes_ko='학력·범죄경력증명서 및 채용신체검사서는 관할 교육청이 자율검증하므로 제출이 면제됩니다.', notes_en='Education, criminal-record and medical documents are verified by the education office and are not required.'),
             item('employment_contract', 'CONDITIONAL_REQUIRED', anchor='② 합격증명서  ③ 고용계약서', applies_when_ko='시·도교육감과 근로계약을 체결한 영어보조교사', applies_when_en='English assistant teachers under contract with a provincial superintendent', role='educational_institution'),
             item('e159_contract_orig_and_copy', 'CONDITIONAL_REQUIRED', anchor='② 고용계약서 원본과 사본 ③ 사업자등록증 사본', applies_when_ko='영어보조교사를 제외한 회화지도강사', applies_when_en='Other conversation instructors', role='employer'),
             item('business_reg_copy', 'CONDITIONAL_REQUIRED', anchor='③ 사업자등록증 사본 ④ 공적확인', applies_when_ko='영어보조교사를 제외한 회화지도강사', applies_when_en='Other conversation instructors', role='employer'),
             item('e159_degree_confirmed_stay', 'CONDITIONAL_REQUIRED', anchor='④ 공적확인*을 받은 학력증명서', applies_when_ko='영어보조교사를 제외한 회화지도강사 (과거 공적확인 학력서류 제출자는 면제, 국내 대학 학위는 공적확인 없는 학위증 사본)', applies_when_en='Other instructors (exempt if confirmed proof was submitted before; Korean degrees as an unconfirmed copy)'),
             item('e159_crime_record_6m', 'CONDITIONAL_REQUIRED', anchor='신청일로부터 6개월 이내에 발급 받은 공적확인*을 받은 범죄경력증명서', applies_when_ko='영어보조교사를 제외한 회화지도강사', applies_when_en='Other conversation instructors'),
             item('e159_recruit_medical', 'CONDITIONAL_REQUIRED', anchor='법무부장관이 지정하는 의료기관이 발급한 공무원채용신체검사규정 별지서식기준에 해당하는 신체검사', applies_when_ko='영어보조교사를 제외한 회화지도강사', applies_when_en='Other conversation instructors',
                  notes_ko='법무부장관이 지정한 의료기관이 발급한 것으로 HIV 및 마약검사(필로폰, 코카인, 아편, 대마 필수) 결과를 포함해야 합니다.', notes_en='Issued by a Ministry-designated medical institution, including drug test results (methamphetamine, cocaine, opium and cannabis are mandatory).'),
             item('academy_reg_copy', 'ADDITIONAL_IF_APPLICABLE', anchor='⑦ 학원설립운영등록증 사본(해당자)', applies_when_ko='학원 취업자', applies_when_en='Academy employees', role='employer'),
             item('e159_lifelong_edu_reg_copy', 'ADDITIONAL_IF_APPLICABLE', anchor='⑧평생교육시설등록증 사본(해당자)', applies_when_ko='평생교육시설 취업자', applies_when_en='Lifelong-education facility employees')],
         **NOTE)

guidance('E-2', 'activities_outside_status', scenario='presidential-english-scholar', section=f'{E2_AOS} — 4. 대통령 영어봉사 장학생에 대한 체류자격외 활동',
         anchor='대통령 영어봉사 장학생에 대한 체류자격외 활동',
         summary_ko='교육부(시·도교육감) 주관 “대통령 영어봉사 장학생”으로 선발된 유학(D-2) 대학생은 합격통지서, 고용계약서, 사업자등록증 사본을 내고 수수료 없이 체류자격외 활동허가를 받습니다.',
         summary_en='D-2 university students selected as “Presidential English-service scholars” by the Ministry of Education (provincial superintendents) obtain permission without fee, submitting the pass notice, employment contract and business registration copy.',
         fee_ko='수수료 면제', fee_en='No fee',
         conditions_ko=['영어를 모국어로 하는 국가 출신으로, 그 국가에서 대학 2년 이상을 이수했거나 10년 이상 영어로 정규교육을 받은 뒤 국내 대학에서 2년 이상 이수한 사람이어야 합니다.'],
         conditions_en=['You must be from a country whose native language is English and have completed 2+ years of university there, or 10+ years of English-medium schooling followed by 2+ years at a Korean university.'],
         docs=[item('app_form_34', anchor='① 신청서(별지 34호서식), 여권, 외국인등록증, 수수료 면제'), item('passport', anchor='① 신청서(별지 34호서식), 여권, 외국인등록증, 수수료 면제'), item('arc', anchor='① 신청서(별지 34호서식), 여권, 외국인등록증, 수수료 면제'),
               item('e159_scholar_pass_notice', anchor='“대통령 영어봉사 장학생” 합격통지서'), item('employment_contract', anchor='합격통지서(국립국제교육원장 또는 시․도 교육감 발급) ③고용계약서', role='educational_institution'),
               item('business_reg_copy', anchor='③고용계약서 ④ 사업자등록증 사본', role='educational_institution')],
         **NOTE)

guidance('E-2', 'workplace_change', section='회화지도(E-2) 근무처의 변경·추가 — 신고제', anchor='회화지도 강사들에 대해서도 신고만으로 근무처를 변경․추가할 수 있도록 허용',
         summary_ko='회화지도 강사는 신고만으로 근무처를 변경·추가할 수 있으며, 신고사유 발생일부터 15일 이내에 근무처변경·추가신고서와 첨부서류를 관할 청장 등에게 냅니다(대리인 신고 허용, 방문신고 원칙). 고용계약기간까지 정상 근무 후 변경하거나 휴·폐업으로 변경한 사람, 본인 귀책으로 해고·퇴직한 뒤 원 고용주의 이적동의를 받은 사람, 현 고용주의 동의를 받아 추가 고용계약을 맺은 사람 등이 신고대상입니다.',
         summary_en='Conversation instructors may change or add a workplace by report, filing the report and attachments within 15 days of the event (a proxy may file; in person in principle). Reportable cases include changing after completing the contract or because of closure, changing after dismissal or quitting with the original employer\'s transfer consent, and adding a contract with the current employer\'s consent.',
         timing_ko='신고사유 발생일부터 15일 이내', timing_en='Within 15 days of the event',
         conditions_ko=['본인 귀책사유로 해고되거나 중도 퇴직한 후 원 고용주의 이적이나 근무처 추가 동의를 받지 못한 사람과, 자격요건을 갖추지 못한 정부초청 청소년영어봉사장학생은 신고 대상에서 제외됩니다.',
                        '현 고용주의 지시에 따라 월 평균 강의시간의 1/3 범위 내에서 다른 업체에서 강의하고 별도 보수를 받는 사람도 신고대상입니다.',
                        '잔여 체류기간이 (새 고용계약기간 + 1개월)보다 짧으면 체류기간 연장허가를 받아야 하며 연장허가 심사에 필요한 서류를 추가로 냅니다.'],
         conditions_en=['People dismissed or who quit for reasons attributable to themselves without the original employer\'s transfer or addition consent, and government-invited youth English-service scholars who do not meet the requirements, cannot use the report.',
                        'Instructors who, on the current employer\'s instruction, teach at another business within one third of their average monthly hours for separate pay are also reportable.',
                        'If the remaining stay is shorter than the new contract + 1 month, an extension is required with its documents.'],
         docs=[item('app_form_34', anchor='신청서(별지 34호서식), 여권, 외국인등록증, 고용계약서, 사업자등록증'), item('passport', anchor='신청서(별지 34호서식), 여권, 외국인등록증, 고용계약서, 사업자등록증'),
               item('arc', anchor='신청서(별지 34호서식), 여권, 외국인등록증, 고용계약서, 사업자등록증'), item('employment_contract', anchor='외국인등록증, 고용계약서, 사업자등록증', role='employer'),
               item('business_reg', anchor='고용계약서, 사업자등록증, 원 근무처 장의 동의서', role='employer'), consent_report('사업자등록증, 원 근무처 장의 동의서*, 시설 설립 관련서류 등'),
               item('e159_facility_establishment_docs', anchor='원 근무처 장의 동의서*, 시설 설립 관련서류 등')],
         **NOTE)

reentry('E-2', '회화지도(E-2) 재입국허가', '등록을 필한 외국인이 출국한 날로부터 1년 이내에 재입국하려는 경우 재입국허가 면제')

# ==========================================================================
# E-3 연구
# ==========================================================================
E3_COND_KO = ['자격요건: 박사 학위 소지자(취득 예정자) 또는 석사 학위 소지자로서 3년 이상 경력자. 국내 석사, 해외 우수대학(TIMES 200위 또는 QS 500위 이내) 석사, 우수 학술논문(SCIE, A&HCI, SCI, SSCI 등재) 저자는 경력요건이 면제됩니다.']
E3_COND_EN = ['Eligibility: a doctorate (or expected doctorate), or a master\'s with 3+ years of experience. Domestic master\'s holders, master\'s holders from top universities abroad (TIMES top 200 or QS top 500) and authors of indexed papers (SCIE, A&HCI, SCI, SSCI) are exempt from the experience requirement.']


def e3_core(inst, masters, contract, grad='대학 대표자 명의로 발급된 졸업예정증명서·확인서 등과 학위수여 날짜를 확인할 수 있는 증명서 등(해당자)', paper='우수 학술논문의 저자임을 확인할 수 있는 입증자료(해당자)'):
    return [item('e159_institution_docs', anchor=inst),
            item('e159_masters_degree_career', anchor=masters),
            item('contract_or_appointment', anchor=contract, role='employer'),
            item('e159_graduation_expected_proof', 'ADDITIONAL_IF_APPLICABLE', anchor=grad, applies_when_ko='박사 학위 취득 예정자 등 해당자', applies_when_en='If applicable (e.g. expected doctorate)'),
            item('e159_paper_author_proof', 'ADDITIONAL_IF_APPLICABLE', anchor=paper, applies_when_ko='우수 학술논문 저자로 경력요건 면제를 받는 경우', applies_when_en='If claiming the experience exemption as an indexed-paper author')]


guidance('E-3', 'visa_issuance', manual=VISA, section='연구(E-3) 공관장 재량으로 발급할 수 있는 사증 — 1. 정부출연 연구기관 과학기술자 · 2. 방위사업법 규정 연구기관',
         anchor='개발을 연구하는 과학기술자에 대한 체류기간 1년 이하의 단수사증 (중국, 특정국가 제외)',
         summary_ko='정부의 연구출연금을 받는 연구기관에서 자연과학분야·고도 산업기술 개발을 연구하는 과학기술자와, 국방부장관의 위촉을 받은 방위사업법 규정 연구기관의 과학기술자에게는 재외공관장이 체류기간 1년 이하의 단수사증을 발급할 수 있습니다(중국, 특정국가 제외). 고용기관 설립 관련 서류, 학위증·경력증명서(해당자), 고용계약서 또는 임용예정확인서 등을 냅니다.',
         summary_en='Scientists researching natural science or advanced industrial technology at government-funded research institutes, and scientists at defence research institutes commissioned by the Minister of National Defense, can receive a single-entry visa of up to one year at the mission\'s discretion (not for China or specified countries). Submit the institution\'s establishment documents, degree/career certificates (if applicable), the contract or appointment confirmation, etc.',
         period_ko='체류기간 1년 이하 단수사증', period_en='Single-entry visa, stay of up to 1 year',
         conditions_ko=['중국 및 특정국가 국민은 이 공관장 재량 사증 대상에서 제외됩니다.'] + E3_COND_KO, conditions_en=['Nationals of China and specified countries are excluded from this consular-discretion visa.'] + E3_COND_EN,
         docs=visa17() + e3_core('② 고용기관 설립 관련 서류(사업자등록증 또는 법인등기사항전부증명서 또는 연구기관 입증서류 등)', '③ 석사 학위 이상 학위증, 경력증명서(해당자)', '④ 고용계약서 또는 임용예정확인서'),
         **NOTE)

E3_CVI = '연구(E-3) 사증발급인정서 발급대상'
guidance('E-3', 'visa_issuance_confirmation', manual=VISA, section=f'{E3_CVI} — 1~3. 연구기관·방위사업 연구기관·산업기술 연구 과학기술자 (공통)', anchor='분야의 연구자 또는 산업상의 고도기술의 연구개발에 종사하는 과학기술자',
         summary_ko='정부출연 등 연구기관의 연구자, 방위사업법 규정 연구기관의 과학기술자, 기업부설연구소·대학·국공립 연구기관 등과 계약하여 연구하는 과학기술자는 사증발급인정신청서, 고용기관 설립 관련 서류, 학위증·경력증명서(해당자), 고용계약서 또는 임용예정확인서 등을 냅니다.',
         summary_en='Researchers at government-funded and similar institutes, scientists at defence research institutes, and scientists researching under contract with corporate labs, universities or public institutes submit the application, the institution\'s establishment documents, degree/career certificates (if applicable), the contract or appointment confirmation, etc.',
         conditions_ko=E3_COND_KO + ['박사 취득 예정자가 학위 취득 확정을 관련 서류로 입증하면 체류기간 6개월 이내에서 조건부로 사증 발급 등을 허가할 수 있습니다.'], conditions_en=E3_COND_EN + ['Expected doctorates who prove the degree is confirmed may be granted a conditional visa for up to 6 months.'],
         docs=cvi21() + e3_core('② 고용기관 설립 관련 서류(사업자등록증 또는 법인등기사항전부증명서 또는 연구기관 입증서류 등) ③ 석사 학위 이상 학위증, 경력증명서(해당자) ④ 고용계약서 또는 임용예정확인서 ➠', '③ 석사 학위 이상 학위증, 경력증명서(해당자) ④ 고용계약서 또는 임용예정확인서 ➠', '④ 고용계약서 또는 임용예정확인서 ➠ 대리인', grad='➠ 대리인 신청시 : 위임장, 대리인 재직증명서, 대리인 신분증 추가 제출 ⑤ 대학 대표자 명의로 발급된 졸업예정증명서·확인서 등과 학위수여 날짜를 확인할 수 있는 증명서 등(해당자)', paper='수 있는 증명서 등(해당자) ⑥ 우수 학술논문의 저자임을 확인할 수 있는 입증자료(해당자) ※ 청(사무소·출장소)장은 초청의') + [proxy('④ 고용계약서 또는 임용예정확인서 ➠ 대리인 신청시 : 위임장, 대리인 재직증명서, 대리인 신분증 추가 제출')],
         **NOTE)

guidance('E-3', 'visa_issuance_confirmation', scenario='advanced-science-talent', manual=VISA, section=f'{E3_CVI} — 4. 고급과학 기술인력', anchor='과학기술정보통신부장관의 고용추천이 있는 자',
         summary_ko='과학기술정보통신부장관의 고용추천을 받아 이공계 연구기관에서 연구개발에 종사하려는 고급과학 기술인력은 사증발급인정신청서, 고용기관 설립 관련 서류, 고용계약서 또는 임용예정확인서, 학위증·경력증명서(해당자), 고용추천서 등을 냅니다.',
         summary_en='Advanced science personnel recommended by the Minister of Science and ICT for R&D at STEM research institutes submit the application, the institution\'s establishment documents, the contract or appointment confirmation, degree/career certificates (if applicable), the employment recommendation, etc.',
         period_ko='고용계약기간 범위 내 최장 5년', period_en='Within the contract period, up to 5 years',
         conditions_ko=['중국 및 특정국가 국민은 사증발급인정서에 의해 사증을 발급받습니다.'], conditions_en=['Nationals of China and specified countries are issued visas through a confirmation of visa issuance.'],
         docs=cvi21('첨부서류 ① 사증발급인정신청서 (별지 제21호 서식), 여권, 표준규격사진 1매 ② 고용기관 설립 관련 서류') + e3_core('② 고용기관 설립 관련 서류(사업자등록증 또는 법인등기사항전부증명서 또는 연구기관 입증서류 등) ③ 고용계약서 또는 임용예정확인서 ④ 석사 학위 이상 학위증, 경력증명서(해당자) ⑤ 고용추천서', '② 고용기관 설립 관련 서류(사업자등록증 또는 법인등기사항전부증명서 또는 연구기관 입증서류 등) ③ 고용계약서 또는 임용예정확인서 ④ 석사 학위 이상 학위증, 경력증명서(해당자) ⑤ 고용추천서', '② 고용기관 설립 관련 서류(사업자등록증 또는 법인등기사항전부증명서 또는 연구기관 입증서류 등) ③ 고용계약서 또는 임용예정확인서 ④ 석사 학위 이상 학위증, 경력증명서(해당자) ⑤ 고용추천서', grad='⑤ 고용추천서 ➠ 대리인 신청시 : 위임장, 대리인 재직증명서, 대리인 신분증 추가 제출 ⑥ 대학 대표자 명의로 발급된 졸업예정증명서·확인서 등과 학위수여 날짜를 확인할 수 있는 증명서 등(해당자) ⑦ 우수 학술논문의 저자임을 확인할 수 있는 입증자료(해당자)', paper='⑤ 고용추천서 ➠ 대리인 신청시 : 위임장, 대리인 재직증명서, 대리인 신분증 추가 제출 ⑥ 대학 대표자 명의로 발급된 졸업예정증명서·확인서 등과 학위수여 날짜를 확인할 수 있는 증명서 등(해당자) ⑦ 우수 학술논문의 저자임을 확인할 수 있는 입증자료(해당자)') + [item('e159_employment_recommendation', anchor='② 고용기관 설립 관련 서류(사업자등록증 또는 법인등기사항전부증명서 또는 연구기관 입증서류 등) ③ 고용계약서 또는 임용예정확인서 ④ 석사 학위 이상 학위증, 경력증명서(해당자) ⑤ 고용추천서'), proxy('⑤ 고용추천서 ➠ 대리인 신청시 : 위임장, 대리인 재직증명서, 대리인 신분증 추가 제출')],
         **NOTE)

guidance('E-3', 'visa_issuance_confirmation', scenario='humanities-researcher', manual=VISA, section=f'{E3_CVI} — 6. 기타 사회과학·인문학·예체능 분야 연구인력', anchor='기타 사회과학·인문학·예체능 분야 연구인력',
         summary_ko='전문대학 이상 교육기관 또는 기타 학술연구기관에서 사회과학·인문학·예체능 분야 연구를 하려는 사람은 사증발급인정신청서, 고용기관 설립 관련 서류, 고용계약서 또는 임용예정확인서, 학위증·경력증명서(해당자) 등을 냅니다.',
         summary_en='People who will research social sciences, humanities, arts or sports at a junior college or higher or another academic research institute submit the application, the institution\'s establishment documents, the contract or appointment confirmation, degree/career certificates (if applicable), etc.',
         period_ko='고용계약기간 범위 내 최장 5년', period_en='Within the contract period, up to 5 years',
         docs=cvi21('유효기간은 사증발급 시 발급일로부터 체류기간과 동일하게 보유 첨부서류 ① 사증발급인정신청서 (별지 제21호 서식), 여권, 표준규격사진 1매') + e3_core('표준규격사진 1매 ② 고용기관 설립 관련 서류(사업자등록증 또는 법인등기사항전부증명서 또는 연구기관 입증서류 등) ③ 고용계약서 또는 임용예정확인서 ④ 석사 학위 이상 학위증, 경력증명서(해당자) ➠ 대리인 신청시', '표준규격사진 1매 ② 고용기관 설립 관련 서류(사업자등록증 또는 법인등기사항전부증명서 또는 연구기관 입증서류 등) ③ 고용계약서 또는 임용예정확인서 ④ 석사 학위 이상 학위증, 경력증명서(해당자) ➠ 대리인 신청시', '표준규격사진 1매 ② 고용기관 설립 관련 서류(사업자등록증 또는 법인등기사항전부증명서 또는 연구기관 입증서류 등) ③ 고용계약서 또는 임용예정확인서 ④ 석사 학위 이상 학위증, 경력증명서(해당자) ➠ 대리인 신청시', grad='경력증명서(해당자) ➠ 대리인 신청시 : 위임장, 대리인 재직증명서, 대리인 신분증 추가 제출 ➄ 대학 대표자 명의로 발급된 졸업예정증명서·확인서 등과 학위수여 날짜를 확인할 수 있는 증명서 등(해당자)', paper='⑥ 우수 학술논문의 저자임을 확인할 수 있는 입증자료(해당자) ※ 출입국ㆍ외국인청(사무소ㆍ출장소)장은 초청의') + [proxy('경력증명서(해당자) ➠ 대리인 신청시 : 위임장, 대리인 재직증명서, 대리인 신분증 추가 제출')],
         **NOTE)

guidance('E-3', 'visa_issuance_confirmation', scenario='visiting-researcher', manual=VISA, section='연구(E-3) 기타 — 1. 방문연구원에 대한 특례', anchor='국외 소재 기관에 소속되어 국내 연구기관 등의 초청에 따라 국내에 체류하면서 연구 활동에 종사하려는 자',
         summary_ko='국외 기관에 소속된 채 국내 연구기관의 초청으로 연구하면서 국내에서 보수를 받지 않는 방문연구원은 사증발급(인정서)신청서, 고용기관 설립 관련 서류, 학위증·경력증명서(해당자), 초청 연구기관 명의의 초청 공문, 원 소속 고용계약 입증 서류 등을 냅니다. 왕복 항공권·숙소 등 실비 보전 수준의 지원은 받을 수 있습니다.',
         summary_en='Visiting researchers who stay affiliated with an overseas institution, research at the invitation of a Korean institute and receive no pay in Korea submit the visa (confirmation) application, the institution\'s establishment documents, degree/career certificates (if applicable), the inviting institute\'s official letter, proof of employment at the home institution, etc. Expense-level support such as flights and lodging is allowed.',
         docs=[item('e159_visa_app_form', anchor='① 사증발급(인정서)신청서(별지 제17호 서식), 여권, 표준규격사진 1매, 수수료'), item('passport', anchor='① 사증발급(인정서)신청서(별지 제17호 서식), 여권, 표준규격사진 1매, 수수료'),
               item('photo', anchor='① 사증발급(인정서)신청서(별지 제17호 서식), 여권, 표준규격사진 1매, 수수료'), item('fee', anchor='① 사증발급(인정서)신청서(별지 제17호 서식), 여권, 표준규격사진 1매, 수수료'),
               item('e159_institution_docs', anchor='② 고용기관 설립 관련 서류(사업자등록증 또는 법인등기사항전부증명서 또는 연구기관 입증서류 등) ③ 석사 학위 이상 학위증, 경력증명서(해당자) ④ 초청 연구기관'),
               item('e159_masters_degree_career', anchor='③ 석사 학위 이상 학위증, 경력증명서(해당자) ④ 초청 연구기관 명의의 초청 공문'),
               item('e159_invitation_letter_research', anchor='초청 연구기관 명의의 초청 공문(임금요건 불필요, 연구기간, 연구분야 명시)'),
               item('e159_home_contract_proof', anchor='원 소속 고용계약 입증 서류(재직증명서, 고용계약서 등)'),
               item('e159_graduation_expected_proof', 'ADDITIONAL_IF_APPLICABLE', anchor='고용계약서 등) ⑥ 대학 대표자 명의로 발급된 졸업예정증명서·확인서 등과 학위수여 날짜를 확인할 수 있는 증명서 등(해당자) ⑦ 국내‧외 은행', applies_when_ko='해당자', applies_when_en='If applicable'),
               item('e159_bank_balance', 'ADDITIONAL_IF_APPLICABLE', anchor='국내‧외 은행 잔고 증명서(해당자)', applies_when_ko='해당자', applies_when_en='If applicable')],
         **NOTE)

evisa('E-3', '연구(E-3) 전자사증 — 1. 발급대상')

E3_SC = '연구(E-3) 체류자격 변경허가'
guidance('E-3', 'status_change', section=f'{E3_SC} — 1. 외국고급인력의 교수(E-1)·연구(E-3)로의 변경 및 상호간 변경',
         anchor='부득이한 사유로 무사증입국하거나 비취업사증을 소지한 외국고급인력에 대한 교수(E-1), 연구(E-3)로 체류자격 변경 허가',
         summary_ko='부득이한 사유로 무사증입국하거나 비취업사증을 가진 외국고급인력이 전문대학 이상 교육기관이나 연구기관에 근무하려는 경우, 그리고 교수(E-1)·연구(E-3) 상호간 변경은 연구(E-3) 자격기준(박사 또는 석사 + 3년 경력)을 갖춰야 합니다. 고용계약서 또는 임용예정확인서, 학위증·경력증명서(해당자), 고용기관 설립 관련 서류 등을 냅니다.',
         summary_en='Highly skilled foreigners who entered visa-free or on a non-work visa for unavoidable reasons and will work at a junior college or higher or a research institute, and E-1↔E-3 changes, must meet the E-3 requirements (doctorate, or master\'s plus 3 years). Submit the contract or appointment confirmation, degree/career certificates (if applicable), the institution\'s establishment documents, etc.',
         conditions_ko=E3_COND_KO, conditions_en=E3_COND_EN,
         docs=form34('① 신청서(제 34호 서식), 여권, 표준규격사진 1장, 수수료 ② 고용계약서 또는 임용예정확인서', photo=True, arc=False) +
              e3_core('④ 고용기관 설립 관련 서류(사업자등록증 또는 법인등기사항전부증명서 또는 연구기관 입증서류 등) ⑤ 원 근무처장의 동의서', '③ 석사 학위 이상 학위증, 경력증명서(해당자) ④ 고용기관', '② 고용계약서 또는 임용예정확인서  ③ 석사') + [consent('⑤ 원 근무처장의 동의서(원 근무처가 있는 경우)')],
         **NOTE)

guidance('E-3', 'status_change', scenario='research-institution-employee', section=f'{E3_SC} — 2. 특정 연구기관·방위산업·국공립 연구기관 근무예정 연구원', anchor='아래 단체에 근무예정인 연구원 대하여는 소지자격에 관계 없이 연구(E-3)자격으로 변경허가',
         summary_ko='특별법의 적용을 받는 연구기관, 방위산업 연구기관, 국·공립 연구기관에 근무할 예정인 연구원은 소지자격에 관계없이 연구(E-3)로 변경할 수 있으며, 고용기관 설립 관련 서류, 학위증·경력증명서(해당자), 고용계약서 또는 임용예정확인서 등을 냅니다.',
         summary_en='Researchers who will work at institutes under special acts, defence research institutes or national/public research institutes may change to E-3 regardless of current status, submitting the institution\'s establishment documents, degree/career certificates (if applicable), the contract or appointment confirmation, etc.',
         conditions_ko=E3_COND_KO, conditions_en=E3_COND_EN,
         docs=form34('① 신청서(별지 34호 서식), 여권 및 외국인등록증, 표준규격사진 1장, 수수료 ② 고용기관', photo=True) +
              e3_core('② 고용기관 설립 관련 서류(사업자등록증 또는 법인등기사항전부증명서 또는  연구기관 입증서류 등) ③', '③ 석사 학위 이상 학위증, 경력증명서(해당자) ④고용계약서 또는 임용예정확인서 ⑤원 근무처의 장의 동의서', '④고용계약서 또는 임용예정확인서 ⑤원 근무처의 장의 동의서', grad='대학 대표자 명의로 발급된 졸업예정증명서·확인서', paper='우수 학술논문의 저자임을 확인할 수 있는 입증자료(해당자) 다. 자격기준') + [consent('⑤원 근무처의 장의 동의서(원 근무처')],
         **NOTE)

guidance('E-3', 'status_change', scenario='professional-spouse', section=f'{E3_SC} — 3. 전문외국인력의 배우자에 대한 전문직자격으로의 변경허가', anchor='전문외국인력의 배우자에 대한 전문직자격으로의 변경허가',
         summary_ko='전문외국인력《E-1 내지 E-5, E-6(E-6-2는 제외), E-7》 자격소지자의 배우자는 전문직에 해당하는 모든 직종으로 체류자격 변경허가를 받을 수 있으며, 연구(E-3)로 변경할 때는 고용기관 설립 관련 서류, 학위증·경력증명서(해당자), 고용계약서 또는 임용예정확인서 등을 냅니다.',
         summary_en='Spouses of professionals (E-1 to E-5, E-6 except E-6-2, E-7) may change into any professional occupation; for E-3 they submit the institution\'s establishment documents, degree/career certificates (if applicable), the contract or appointment confirmation, etc.',
         docs=form34('① 신청서(별지 34호서식), 여권 및 외국인등록증, 표준규격사진1장, 수수료 ② 고용기관 설립 관련 서류(사업자등록증 또는 법인등기사항전부증명서 또는 연구기관 입증서류 등) ③ 석사 학위 이상 학위증, 경력증명서(해당자) ④고용계약서 또는 임용예정확인서 ⑤원 근무처의 장의 동의서(원 근무처가 있는 경우만 해당)', photo=True) +
              e3_core('① 신청서(별지 34호서식), 여권 및 외국인등록증, 표준규격사진1장, 수수료 ② 고용기관 설립 관련 서류(사업자등록증 또는 법인등기사항전부증명서 또는 연구기관 입증서류 등) ③ 석사 학위 이상 학위증, 경력증명서(해당자) ④고용계약서 또는 임용예정확인서 ⑤원 근무처의 장의 동의서(원 근무처가 있는 경우만 해당)', '① 신청서(별지 34호서식), 여권 및 외국인등록증, 표준규격사진1장, 수수료 ② 고용기관 설립 관련 서류(사업자등록증 또는 법인등기사항전부증명서 또는 연구기관 입증서류 등) ③ 석사 학위 이상 학위증, 경력증명서(해당자) ④고용계약서 또는 임용예정확인서 ⑤원 근무처의 장의 동의서(원 근무처가 있는 경우만 해당)', '① 신청서(별지 34호서식), 여권 및 외국인등록증, 표준규격사진1장, 수수료 ② 고용기관 설립 관련 서류(사업자등록증 또는 법인등기사항전부증명서 또는 연구기관 입증서류 등) ③ 석사 학위 이상 학위증, 경력증명서(해당자) ④고용계약서 또는 임용예정확인서 ⑤원 근무처의 장의 동의서(원 근무처가 있는 경우만 해당)', grad='(원 근무처가 있는 경우만 해당) ➅ 대학 대표자 명의로 발급된 졸업예정증명서·확인서 등과 학위수여 날짜를 확인할 수 있는 증명서 등(해당자) ⑦ 우수 학술논문의 저자임을 확인할 수 있는 입증자료(해당자)', paper='(원 근무처가 있는 경우만 해당) ➅ 대학 대표자 명의로 발급된 졸업예정증명서·확인서 등과 학위수여 날짜를 확인할 수 있는 증명서 등(해당자) ⑦ 우수 학술논문의 저자임을 확인할 수 있는 입증자료(해당자)') + [consent('① 신청서(별지 34호서식), 여권 및 외국인등록증, 표준규격사진1장, 수수료 ② 고용기관 설립 관련 서류(사업자등록증 또는 법인등기사항전부증명서 또는 연구기관 입증서류 등) ③ 석사 학위 이상 학위증, 경력증명서(해당자) ④고용계약서 또는 임용예정확인서 ⑤원 근무처의 장의 동의서(원 근무처가 있는 경우만 해당)')],
         **NOTE)

guidance('E-3', 'status_change', scenario='from-d2-d10', section=f'{E3_SC} — 5. 유학(D-2), 구직(D-10) ➠ 연구(E-3)자격으로의 변경', anchor='유학(D-2), 구직(D-10) ➠ 연구(E-3)자격으로의 변경',
         summary_ko='유학(D-2) 또는 구직(D-10)에서 연구(E-3)로 변경하려면 고용계약서 또는 임용예정확인서, 학위증·경력증명서(해당자), 고용기관 설립 관련 서류 등을 냅니다.',
         summary_en='To change from D-2 or D-10 to E-3, submit the contract or appointment confirmation, degree/career certificates (if applicable), the institution\'s establishment documents, etc.',
         conditions_ko=D2D10_COND_KO, conditions_en=D2D10_COND_EN,
         docs=form34('①신청서(별지 34호서식), 여권 및 외국인등록증, 수수료 ②고용계약서 또는 임용예정확인서 ③') +
              e3_core('④ 고용기관 설립 관련 서류(사업자등록증 또는 법인등기사항전부증명서 또는 연구기관 입증서류 등) ➄', '②고용계약서 또는 임용예정확인서 ③ 석사 학위 이상 학위증, 경력증명서(해당자) ④', '①신청서(별지 34호서식), 여권 및 외국인등록증, 수수료 ②고용계약서 또는 임용예정확인서', grad='입증서류 등) ➄ 대학 대표자 명의로 발급된 졸업예정증명서·확인서', paper='증명서 등(해당자) ⑥ 우수 학술논문의 저자임을 확인할 수 있는 입증자료(해당자) 6. 방문연구원'),
         **NOTE)

guidance('E-3', 'status_change', scenario='visiting-researcher', section=f'{E3_SC} — 6. 방문연구원에 대한 특례', anchor='6. 방문연구원에 대한 특례',
         summary_ko='국외 기관에 소속된 채 국내 연구기관의 초청으로 연구하면서 국내에서 보수를 받지 않는 방문연구원은 고용기관 설립 관련 서류, 학위증·경력증명서(해당자), 초청 연구기관 명의의 초청 공문, 원 소속 고용계약 입증 서류 등을 냅니다. 체류기간은 연구 기간 + 1개월로 부여됩니다.',
         summary_en='Visiting researchers affiliated with an overseas institution who research at a Korean institute\'s invitation without pay in Korea submit the institution\'s establishment documents, degree/career certificates (if applicable), the inviting institute\'s official letter, proof of home-institution employment, etc. The stay is granted for the research period + 1 month.',
         period_ko='연구 기간 + 1개월', period_en='Research period + 1 month',
         docs=[item('app_form_34', anchor='① 통합신청서(별지 34호서식) 여권, 표준규격사진 1매, 수수료'), item('passport', anchor='① 통합신청서(별지 34호서식) 여권, 표준규격사진 1매, 수수료'),
               item('photo', anchor='① 통합신청서(별지 34호서식) 여권, 표준규격사진 1매, 수수료'), item('fee', anchor='① 통합신청서(별지 34호서식) 여권, 표준규격사진 1매, 수수료'),
               item('e159_institution_docs', anchor='① 통합신청서(별지 34호서식) 여권, 표준규격사진 1매, 수수료 ② 고용기관 설립 관련 서류'),
               item('e159_masters_degree_career', anchor='③ 석사 학위 이상 학위증, 경력증명서(해당자) ④ 초청 연구기관 명의의 초청 공문'),
               item('e159_invitation_letter_research', anchor='초청 연구기관 명의의 초청 공문(임금요건 불필요, 연구기간, 연구분야 명시) ※ 체류기간은 연구 기간 + 1개월로 부여'),
               item('e159_home_contract_proof', anchor='원 소속 고용계약 입증 서류(재직증명서, 고용계약서 등)'),
               item('e159_graduation_expected_proof', 'ADDITIONAL_IF_APPLICABLE', anchor='고용계약서 등) ⑥ 대학 대표자 명의로 발급된 졸업예정증명서·확인서', applies_when_ko='해당자', applies_when_en='If applicable'),
               item('e159_paper_author_proof', 'ADDITIONAL_IF_APPLICABLE', anchor='⑦ 우수 학술논문의 저자임을 확인할 수 있는 입증자료(해당자) ⑧ 국내‧외 은행', applies_when_ko='해당자', applies_when_en='If applicable'),
               item('e159_bank_balance', 'ADDITIONAL_IF_APPLICABLE', anchor='⑧ 국내‧외 은행 잔고 증명서(해당자)', applies_when_ko='해당자', applies_when_en='If applicable')],
         **NOTE)

E3_AOS = '연구(E-3) 체류자격외 활동'
c45_lecture('E-3', f'{E3_AOS} — 2. 외국인투자기업 CEO 등 우수전문인력의 대학 강연활동', '외국인투자기업 CEO 등 우수전문인력의 대학 강연활동',
            '①신청서(별지 34호 서식), 여권 및 외국인등록증, 수수료 ②총(학)장의 추천서', contract_def='employment_contract', contract_anchor='③고유번호증(사업자등록증)사본 ④고용계약서 ⑤원근무처장의 동의서')

guidance('E-3', 'activities_outside_status', scenario='e1-e3-mutual', section=f'{E3_AOS} — 3. 외국고급과학 기술인력의 교수(E-1), 연구(E-3)간 상호 체류자격외 활동',
         anchor='교수(E-1) 또는 연구(E-3) 자격을 소지한 외국고급과학 기술인력에 대한 교수(E-1), 연구(E-3)간 상호 체류자격외 활동',
         summary_ko='교수(E-1) 또는 연구(E-3) 자격의 외국고급과학 기술인력이 전문대학 이상 교육기관이나 이공계 연구기관에서 상대 자격 활동을 하려면 체류자격외 활동허가를 받습니다. 고용계약서 또는 임용예정확인서, 원 고용주의 동의서, 고용기관 설립 관련 서류, 학위증·경력증명서(해당자) 등을 냅니다.',
         summary_en='E-1 or E-3 advanced science personnel who will also work in the other status at a junior college or higher or a STEM research institute need permission for activities outside status, submitting the contract or appointment confirmation, the original employer\'s consent, the institution\'s establishment documents, degree/career certificates (if applicable), etc.',
         conditions_ko=E3_COND_KO + ['연구(E-3) 자격자가 동일한 대학 또는 연구기관에서 강의하는 경우에는 체류자격외 활동허가(교수(E-1)) 없이 허용되며, 원 체류자격의 근무시간 또는 보수를 상회하면 체류자격 변경이 안내됩니다. 다른 대학·연구기관에서는 원 근무처장의 동의를 얻어 허가를 받아야 합니다.'],
         conditions_en=E3_COND_EN + ['E-3 holders lecturing at their own university or institute need no permission; if it exceeds the working hours or pay of the original status, a change of status is advised. At another university or institute, permission with the original head\'s consent is required.'],
         docs=form34('①신청서(별지 34호 서식), 여권 및 외국인등록증, 표준규격사진 1장, 수수료 ② 고용계약서 또는 임용예정확인서 ③원 고용주의 동의서 ④ 고용기관', photo=True) +
              e3_core('③원 고용주의 동의서 ④ 고용기관 설립 관련 서류(사업자등록증 또는 법인등기사항전부증명서 또는 연구기관 입증서류 등) ⑤ 석사', '⑤ 석사 학위 이상 학위증, 경력증명서(해당자) ➅ 대학 대표자 명의로 발급된 졸업예정증명서·확인서 등과 학위수여 날짜를 확인할 수 있는 증명서 등(해당자) ⑥', '② 고용계약서 또는 임용예정확인서 ③원 고용주의 동의서 ④ 고용기관') +
              [item('e159_orig_employer_consent', anchor='② 고용계약서 또는 임용예정확인서 ③원 고용주의 동의서 ④ 고용기관')],
         **NOTE)

workplace_report('E-3', '연구(E-3) 근무처의 변경·추가 — 신고제', '연구(E-3) 자격으로 외국인등록을 하고 체류하고 있는 자로 변경․추가되는 근무처에서 활동하는데 필요한 자격요건을 구비하고 있는 자',
                 [item('app_form_34', anchor='①통합신청서[별지 제34호서식], 여권 및 외국인등록증, 수수료 없음'), item('passport', anchor='①통합신청서[별지 제34호서식], 여권 및 외국인등록증, 수수료 없음'),
                  item('arc', anchor='①통합신청서[별지 제34호서식], 여권 및 외국인등록증, 수수료 없음'),
                  item('e159_institution_docs', anchor='②(사업자등록증 또는 법인등기사항전부증명서 또는 연구기관 입증서류 등)'),
                  consent_report('③원 근무처 장의 동의서 ④고용계약서 또는 임용예정확인서'), item('contract_or_appointment', anchor='④고용계약서 또는 임용예정확인서 ※', role='employer')],
                 conditions_ko=['근무처변경·추가 신고는 체류허가 신청이 아닌 신고이므로, 잔여 체류기간이 [변경된 고용계약기간 + 1개월]보다 적으면 연장신청을 받아 그 기간까지 연장하고, 많으면 그 기간으로 단축 조정됩니다.', '신고기한을 넘기면 과태료 처분 후 신고가 수리됩니다.'],
                 conditions_en=['The report is not a stay permit: if the remaining stay is shorter than the new contract + 1 month it is extended to that date on application, and if longer it is shortened to it.', 'Late reports are accepted after a fine.'],
                 fee_ko='수수료 없음', fee_en='No fee')

reentry('E-3', '연구(E-3) 재입국허가', '등록을 필한 외국인이 출국한 날로부터 1년 이내에 재입국하려는 경우')

# ==========================================================================
# E-4 기술지도
# ==========================================================================
# 공관장 재량 사증: the E-4 visa chapter has no such section (no visa_issuance rule).
guidance('E-4', 'visa_issuance_confirmation', manual=VISA, section='기술지도(E-4) 사증발급인정서 발급대상 — 1. 산업상 고도기술 제공',
         anchor='국내에서 구할 수 없는 산업상의 고도기술 등을 국내 공․사기관에 제공하는 자 - 외국의 용역발주업체에서 파견되어',
         summary_ko='국내에서 구할 수 없는 산업상의 고도기술 등을 국내 공·사기관에 제공하는 사람(외국 용역발주업체에서 파견되어 특수분야 기술을 제공하거나 국내 산업체가 도입한 특수기술 등을 제공하는 사람)은 사증발급인정신청서, 공사기관 설립관련 서류, 기술도입계약 관련 서류, 파견명령서(또는 재직증명서)를 냅니다.',
         summary_en='People providing advanced industrial technology unavailable in Korea to public or private organisations (dispatched by a foreign service contractor, or providing special technology imported by a Korean company) submit the application, the organisation\'s establishment documents, the technology-import contract documents and the dispatch order (or employment certificate).',
         docs=cvi21('첨부서류 ① 사증발급인정신청서 (별지 제21호 서식), 여권, 표준규격사진 1매 ② 공사기관 설립관련 서류') + [
             item('e159_public_private_org_docs', anchor='사업자등록증, 외국인투자기업등록증, 지사설치허가서 등'),
             item('e159_tech_import_docs', anchor='기술도입계약신고수리서, 기술도입계약서(또는 용역거래 계약서) 또는 방산업체지정서 사본',
                  notes_ko='용역거래는 거주자와 국외 특수관계자 간의 경영관리, 금융자문, 지급보증, 전산지원 및 기술지원 등 사업상 필요하다고 인정되는 거래입니다.', notes_en='A service transaction means management, financial advice, guarantees, IT or technical support and similar business transactions between a resident and a related party abroad.'),
             item('e159_dispatch_order_or_employment', anchor='④ 파견명령서(또는 재직증명서)'),
             proxy()],
         **NOTE)

evisa('E-4', '기술지도(E-4) 전자사증 — 1. 발급대상')

E4_SC = '기술지도(E-4) 체류자격 변경허가'
guidance('E-4', 'status_change', section=f'{E4_SC} — 1. 유학(D-2), 구직(D-10) ➠ 기술지도(E-4)자격으로의 변경', anchor='유학(D-2), 구직(D-10) ➠ 기술지도(E-4)자격으로의 변경',
         summary_ko='유학(D-2) 또는 구직(D-10)에서 기술지도(E-4)로 변경하려면 본사 발행 파견명령서 또는 재직증명서, 기술도입계약 관련 서류, 사업자등록증 사본, 필요하면 소관부처 장관의 고용추천서를 냅니다.',
         summary_en='To change from D-2 or D-10 to E-4, submit the head-office dispatch order or employment certificate, the technology-import contract documents, a business registration copy and, if needed, the competent minister\'s employment recommendation.',
         conditions_ko=D2D10_COND_KO, conditions_en=D2D10_COND_EN,
         docs=form34('①신청서(별지 34호서식), 여권 및 외국인등록증, 수수료 ②파견명령서(본사발행) 또는 재직증명서') + [
             item('dispatch_or_employment_cert', anchor='②파견명령서(본사발행) 또는 재직증명서 ③ 기술도입계약신고수리서', role='employer'),
             item('e159_tech_import_docs_stay', anchor='③ 기술도입계약신고수리서, 기술도입계약서(또는 용역거래인증서) 또는 방위산업체지정서 사본 ④ 사업자등록증 사본 ⑤ 소관부처'),
             item('business_reg_copy', anchor='④ 사업자등록증 사본 ⑤ 소관부처 장관의 고용추천서(필요시)', role='employer'),
             item('e159_ministry_recommendation_if_needed', 'CONDITIONAL_REQUIRED', anchor='⑤ 소관부처 장관의 고용추천서(필요시)', applies_when_ko='필요한 경우', applies_when_en='If needed')],
         **NOTE)

guidance('E-4', 'status_change', scenario='technology-provider', completeness='SOURCE_ONLY', section=f'{E4_SC} — 2. 기술을 제공하려는 기술자 (소지자격에 관계없이 변경)',
         anchor='산업상의 특수분야에 속하는 기술을 제공하려는 아래 기술자에 대하여는 소지자격에 관계없이 기술지도(E-4)자격으로 변경허가',
         summary_ko='외국인투자촉진법·조세특례제한법·항공우주산업개발촉진법에 따른 기술도입계약으로 기술을 제공하는 사람, 방위산업체에 기술을 제공하는 사람, 정부 또는 정부투자기관과의 계약으로 산업상 기술을 제공하는 사람은 소지자격에 관계없이 기술지도(E-4)로 변경허가를 받을 수 있습니다. 이 항목에는 별도 제출서류 목록이 없습니다.',
         summary_en='People providing technology under a technology-import contract (Foreign Investment Promotion Act, Restriction of Special Taxation Act, Aerospace Industry Development Promotion Act), to a defence-industry company, or under a contract with the government or a government-invested body may change to E-4 regardless of current status. No separate document list is given for this item.')

spouse_change('E-4', f'{E4_SC} — 4. 전문외국인력의 배우자에 대한 전문직자격으로의 변경허가', '전문외국인력의 배우자에 대한 전문직자격으로의 변경허가')

c45_lecture('E-4', '기술지도(E-4) 체류자격외 활동 — 2. 외국인투자기업 CEO 등 우수전문인력의 대학 강연활동', '외국인투자기업 CEO 등 우수전문인력의 대학 강연활동',
            '①신청서(별지 34호 서식), 여권 및 외국인등록증, 수수료 ②총(학)장의 추천서')

REC_CHANGE = dict(applies_when_ko='근무처를 변경하는 경우', applies_when_en='When changing workplace')
workplace_report('E-4', '기술지도(E-4) 근무처의 변경·추가 — 신고제', '기술지도(E-4) 자격으로 외국인등록을 하고 체류하고 있는 자로 변경․추가되는 근무처에서 활동하는데 필요한 자격요건을 구비하고 있는 자',
                 [item('e159_workplace_report_form', anchor='①근무처변경‧추가 신고서[별지 제38호의3서식], 여권 및 외국인등록증, 수수료 없음 ②사업자등록증 ③원 근무처 장의 동의서 ④고용계약서 ⑤기술도입'),
                  item('passport', anchor='①근무처변경‧추가 신고서[별지 제38호의3서식], 여권 및 외국인등록증, 수수료 없음 ②사업자등록증 ③원 근무처 장의 동의서 ④고용계약서 ⑤기술도입'),
                  item('arc', anchor='①근무처변경‧추가 신고서[별지 제38호의3서식], 여권 및 외국인등록증, 수수료 없음 ②사업자등록증 ③원 근무처 장의 동의서 ④고용계약서 ⑤기술도입'),
                  item('business_reg', anchor='수수료 없음 ②사업자등록증 ③원 근무처 장의 동의서 ④고용계약서 ⑤기술도입', role='employer'),
                  consent_report('②사업자등록증 ③원 근무처 장의 동의서 ④고용계약서 ⑤기술도입'),
                  item('employment_contract', anchor='③원 근무처 장의 동의서 ④고용계약서 ⑤기술도입', role='employer'),
                  item('e159_tech_import_docs_stay', anchor='⑤기술도입계약신고수리서, 기술도입계약서(또는 용역거래인증서) 또는 방위산업체지정서 사본 등'),
                  item('e159_ministry_recommendation', 'CONDITIONAL_REQUIRED', anchor='방위산업체지정서 사본 등 ※ 근무처 변경 시 소관부처 장관의 고용추천서 필요', **REC_CHANGE)],
                 fee_ko='수수료 없음', fee_en='No fee')

reentry('E-4', '기술지도(E-4) 재입국허가', '등록을 필한 외국인이 출국한 날로부터 1년 이내에 재입국하려는 경우')

# ==========================================================================
# E-5 전문직업
# ==========================================================================
guidance('E-5', 'visa_issuance', manual=VISA, section='전문직업(E-5) 공관장 재량으로 발급할 수 있는 사증 — 1. 항공기 조종사 · 2. 선박운항 필수전문요원',
         anchor='국내 항공사에 고용되어 항공기 조종사로 근무하고자 하는 자에 대한',
         summary_ko='국내 항공사에 고용된 항공기 조종사와, 국내 운수회사 등에 고용되어 선장 등 선박운항 필수전문요원으로 근무하려는 사람에게는 재외공관장이 체류기간 1년 이하의 단수사증을 발급할 수 있습니다. 학위증 및 자격증(면허증) 사본, 소관 중앙행정기관장의 고용추천서 또는 고용의 필요성 입증서류, 고용계약서를 냅니다.',
         summary_en='Airline pilots employed by a Korean airline and essential ship-operation staff such as captains employed by a Korean transport company can receive a single-entry visa of up to one year at the mission\'s discretion, with copies of the degree and licence, the competent central agency head\'s employment recommendation or proof of the need for employment, and the employment contract.',
         period_ko='체류기간 1년 이하 단수사증', period_en='Single-entry visa, stay of up to 1 year',
         docs=visa17() + [
             item('e159_degree_license_copy', anchor='② 학위증 및 자격증(면허증) 사본'),
             item('e159_central_agency_recommendation', anchor='③ 소관 중앙행정기관장의 고용추천서',
                  notes_ko='경제자유구역 내에서 취업활동을 하려는 사람은 관할 특별시장·광역시장·도지사의 고용추천서 또는 고용의 필요성을 입증할 수 있는 서류를 냅니다.', notes_en='For work in a free economic zone, a recommendation from the metropolitan mayor or governor, or proof of the need for employment.'),
             item('employment_contract', anchor='또는 고용의 필요성을 입증할 수 있는 서류 ④ 고용계약서', role='employer')],
         **NOTE)

guidance('E-5', 'visa_issuance_confirmation', manual=VISA, section='전문직업(E-5) 사증발급인정서 발급대상 — 1. 공관장 재량 대상을 제외한 모든 전문직업(E-5)',
         anchor='공관장 재량으로 발급할 수 있는 경우를 제외한 모든 전문직업(E-5) 자격에 대한 사증발급은 사증발급인정서를 통해 사증발급',
         summary_ko='공관장 재량 사증 대상을 제외한 모든 전문직업(E-5) 사증은 사증발급인정서로 발급되며, 사증발급인정신청서, 초청사유서, 학위증 및 자격증 사본, 소관 중앙행정기관의 장의 고용추천서 또는 고용의 필요성 입증서류, 고용계약서를 냅니다.',
         summary_en='All other E-5 visas are issued through a confirmation of visa issuance; submit the application, a statement of reasons for the invitation, copies of the degree and licence, the competent central agency head\'s recommendation or proof of the need for employment, and the employment contract.',
         docs=cvi21('① 사증발급인정신청서 (별지 제21호 서식), 여권, 표준규격사진 1매 ② 초청사유서') + [
             item('e159_invitation_reason', anchor='② 초청사유서'),
             item('e159_degree_and_license_copy', anchor='③ 학위증 및 자격증 사본'),
             item('e159_central_agency_head_recommendation', anchor='④ 소관 중앙행정기관의 장의 고용추천서 또는 고용의 필요성을 입증할 수 있는 서류',
                  notes_ko='경제자유구역 내에서 취업활동을 하려는 사람은 관할 특별시장·광역시장·도지사의 고용추천서 또는 고용의 필요성을 입증할 수 있는 서류를 냅니다.', notes_en='For work in a free economic zone, a recommendation from the metropolitan mayor or governor, or proof of the need for employment.'),
             item('employment_contract', anchor='⑤ 고용계약서', role='employer')],
         **NOTE)

evisa('E-5', '전문직업(E-5) 전자사증 — 1. 발급대상')

E5_SC = '전문직업(E-5) 체류자격 변경허가'
guidance('E-5', 'status_change', section=f'{E5_SC} — 1. 유학(D-2), 구직(D-10) ➠ 전문직업(E-5)자격으로의 변경', anchor='유학(D-2), 구직(D-10) ➠ 전문직업(E-5)자격으로의 변경',
         summary_ko='유학(D-2) 또는 구직(D-10)에서 전문직업(E-5)으로 변경하려면 고용계약서 사본, 사업자등록증 사본 또는 허가증·등록증(특정사업 허가·등록 업체), 학위증 사본 및 자격증 사본, 소관부처 장관의 고용추천서를 냅니다.',
         summary_en='To change from D-2 or D-10 to E-5, submit a copy of the employment contract, a copy of the business registration or the permit/registration (for licensed businesses), copies of the degree and licence, and the competent minister\'s employment recommendation.',
         conditions_ko=D2D10_COND_KO, conditions_en=D2D10_COND_EN,
         docs=form34('① 신청서(별지 34호서식), 여권 및 외국인등록증, 수수료 ②고용계약서 사본') + [
             item('employment_contract', anchor='②고용계약서 사본 ③ 사업자등록증 사본 또는 허가증', role='employer', original_or_copy='copy'),
             item('e159_bizreg_or_permit', anchor='③ 사업자등록증 사본 또는 허가증이나 등록증(특정사업 허가·등록 업체인 경우) 등'),
             item('e159_degree_copy_license_copy', anchor='④ 학위증 사본 및 자격증 사본'),
             item('e159_ministry_recommendation', anchor='④ 학위증 사본 및 자격증 사본 ⑤ 소관부처 장관의 고용추천서')],
         **NOTE)

spouse_change('E-5', f'{E5_SC} — 3. 전문외국인력의 배우자에 대한 전문직자격으로의 변경허가', '전문외국인력의 배우자에 대한 전문직자격으로의 변경허가')

c45_lecture('E-5', '전문직업(E-5) 체류자격외 활동 — 3. 외국인투자기업 CEO 등 우수전문인력의 대학 강연활동', '외국인투자기업 CEO 등 우수전문인력의 대학 강연활동',
            '① 신청서(별지 34호 서식), 여권 및 외국인등록증, 수수료, ② 총(학)장의 추천서')

workplace_report('E-5', '전문직업(E-5) 근무처의 변경·추가 — 신고제', '전문직업(E-5) 자격으로 외국인등록을 하고 체류하고 있는 자로 변경․추가되는 근무처에서 활동하는데 필요한 자격요건을 구비하고 있는 자',
                 [item('e159_workplace_report_form', anchor='①근무처변경‧추가 신고서[별지 제38호의3서식], 여권 및 외국인등록증, 수수료 없음 ②사업자등록증 ③원 근무처 장의 동의서* ④고용계약서'),
                  item('passport', anchor='①근무처변경‧추가 신고서[별지 제38호의3서식], 여권 및 외국인등록증, 수수료 없음 ②사업자등록증 ③원 근무처 장의 동의서* ④고용계약서'),
                  item('arc', anchor='①근무처변경‧추가 신고서[별지 제38호의3서식], 여권 및 외국인등록증, 수수료 없음 ②사업자등록증 ③원 근무처 장의 동의서* ④고용계약서'),
                  item('business_reg', anchor='수수료 없음 ②사업자등록증 ③원 근무처 장의 동의서* ④고용계약서', role='employer'),
                  consent_report('②사업자등록증 ③원 근무처 장의 동의서* ④고용계약서'),
                  item('employment_contract', anchor='③원 근무처 장의 동의서* ④고용계약서', role='employer'),
                  item('e159_ministry_recommendation', 'CONDITIONAL_REQUIRED', anchor='근무처 변경 시 소관부처 장관의 고용추천서 필요', **REC_CHANGE)],
                 fee_ko='수수료 없음', fee_en='No fee')

reentry('E-5', '전문직업(E-5) 재입국허가', '등록을 필한 외국인이 출국한 날부터 1년 이내에 재입국하려는 경우')

# ==========================================================================
# E-8 계절근로
# ==========================================================================
E8_CVI_ONLY = '계절근로(E-8) 사증은 청장ㆍ사무소장 또는 출장소장이 발급한 사증발급인정서에 의해서만 발급'
guidance('E-8', 'visa_issuance', manual=VISA, completeness='SOURCE_ONLY', section='계절근로(E-8) 사증발급인정서', anchor=E8_CVI_ONLY,
         summary_ko='계절근로(E-8) 사증은 출입국·외국인관서의 장이 발급한 사증발급인정서에 의해서만 발급됩니다. 제출서류는 사증발급인정서 항목을 확인하세요.',
         summary_en='E-8 visas are issued only on the basis of a confirmation of visa issuance from an immigration office. See the confirmation item for documents.')

guidance('E-8', 'visa_issuance_confirmation', manual=VISA, section='계절근로(E-8) 사증발급인정서 — 사증발급인정서 신청', anchor='제출서류(비자포털에 첨부)',
         summary_ko='계절근로(E-8) 사증발급인정서는 기초자치단체장(시·군·구)이 비자포털로 신청하며, 지자체가 고용주에게 배정한 해외 체류 외국인이 대상입니다. 표준근로계약서, 내국인 구인노력 증빙자료, 계절근로자 여권 사본과 선정 방식별 서류(MOU 외국인, 결혼이민자의 친척, 유학생의 부모), 숙소시설표, 업무협약(MOU) 체결 결과서 등을 첨부합니다.',
         summary_en='The E-8 confirmation of visa issuance is filed on the Visa Portal by the head of the city/county/district for foreigners abroad whom it has assigned to employers. Attach the standard labour contract, proof of efforts to recruit Koreans, the worker\'s passport copy and documents for the selection route (MOU foreigners, relatives of marriage migrants, parents of international students), the accommodation table and the MOU result report.',
         filer='local_government', channel_ko='비자포털 (www.visa.go.kr)', channel_en='Visa Portal (www.visa.go.kr)',
         timing_ko='사증발급인정서 발급에 신청일로부터 약 10일 소요', timing_en='About 10 days from filing to issuance',
         conditions_ko=['결혼이민자 등의 국내 체류 가족은 사증발급인정서 신청 대상이 아니고 체류자격 외 활동허가 신청 대상입니다.', '추천자와 허용분야를 확인해 정확한 사증 종류(E-8-1~E-8-8, E-8-99, 모두 단수, 최대 8개월)를 신청해야 합니다.'],
         conditions_en=['Family members of marriage migrants already in Korea are not CVI applicants; they apply for permission for activities outside status.', 'Apply for the correct visa type for the recommender and field (E-8-1 to E-8-8, E-8-99; all single-entry, up to 8 months).'],
         docs=[item('e159_standard_contract', anchor='제출서류(비자포털에 첨부) ① 표준근로계약서'),
               item('e159_domestic_recruit_proof', anchor='② 내국인 구인노력 증빙자료(구인 광고내용 사본 및 최종 구인실적 등)'),
               item('passport_copy', anchor='외국인 계절근로자 여권 사본'),
               item('e159_farm_history', 'CONDITIONAL_REQUIRED', anchor='MOU 외국인 : 본국에서의 농‧어업 종사 이력', applies_when_ko='MOU 방식으로 선정된 외국인 (E-8-1, E-8-3)', applies_when_en='Foreigners selected under an MOU (E-8-1, E-8-3)'),
               item('e159_marriage_relative_docs', 'CONDITIONAL_REQUIRED', anchor='결혼이민자 신분증, (국내용) 혼인관계증명서', applies_when_ko='결혼이민자의 4촌 이내 친척(배우자 포함) (E-8-2, E-8-4)', applies_when_en='Relatives within the fourth degree of a marriage migrant, including spouses (E-8-2, E-8-4)',
                    notes_ko='국내 결혼이민자와의 가족(친척)관계가 입증되어야 하며, 영어 이외의 외국어로 되어 있으면 번역자 확인서와 번역문을 첨부합니다(공증 불요).', notes_en='The family relationship with the marriage migrant must be proven; documents in a language other than English need a translation and translator\'s confirmation (no notarisation).'),
               item('e159_student_parent_docs', 'CONDITIONAL_REQUIRED', anchor='유학생 외국인등록증, 재학증명서, 출생증명서 또는 가족관계증명서 등', applies_when_ko='유학생의 부모 (E-8-7, E-8-8)', applies_when_en='Parents of international students (E-8-7, E-8-8)'),
               item('e159_accommodation_table', anchor='(계절근로자에게 제공 예정인) 숙소시설표'),
               item('e159_mou_result', anchor='⑤ 업무협약(MOU) 체결 결과서 등')],
         **NOTE)

guidance('E-8', 'registration', section='계절근로(E-8) 외국인등록', anchor='① 통합신청서, 여권, 사진(35mm×45mm) 1매, 수수료',
         summary_ko='계절근로자(E-8)의 외국인등록은 통합신청서, 여권, 사진, 수수료와 거주/숙소 제공 확인서, 산재보험 또는 농·어업인 안전보험 가입 서류, 여행자보험 가입증명서, 마약검사 확인서(밀봉 제출), 지자체 숙소점검 확인서로 합니다.',
         summary_en='E-8 seasonal workers register with the integrated form, passport, photo and fee plus the accommodation confirmation, industrial-accident or farmers\'/fishers\' safety insurance documents, travel insurance certificate, a sealed drug test certificate and the local government\'s accommodation inspection confirmation.',
         docs=[item('app_form_34', anchor='① 통합신청서, 여권, 사진(35mm×45mm) 1매, 수수료'), item('passport', anchor='① 통합신청서, 여권, 사진(35mm×45mm) 1매, 수수료'),
               item('e159_photo_3545', anchor='① 통합신청서, 여권, 사진(35mm×45mm) 1매, 수수료'), item('fee', anchor='① 통합신청서, 여권, 사진(35mm×45mm) 1매, 수수료'),
               item('accommodation_confirmation', anchor='② 거주/숙소 제공 확인서 ※ 고용주의 등기부등본, 임대차계약서 등 추가서류 불요', role='employer', notes_ko='고용주의 등기부등본, 임대차계약서 등 추가서류는 필요 없습니다.', notes_en='No further landlord documents such as the register extract or lease are needed.'),
               item('e159_injury_insurance_e8', anchor='③ 산재보험 가입증명원(사업장 가입 신청 입증서류) 또는 농·어업인 안전보험 보험증권(안전보험 가입 확약서)'),
               item('e159_travel_insurance', anchor='④ 여행자보험 가입증명서'),
               item('e159_drug_test_e8', anchor='⑤ 마약검사 확인서 ※검사결과는 밀봉상태로 제출',
                    notes_ko='법무부장관 지정 의료기관(www.hikorea.go.kr에서 확인) 또는 지역보건법에 따라 설립된 보건소·보건의료원에서 검사합니다.', notes_en='Tested at a Ministry-designated medical institution (see www.hikorea.go.kr) or a public health centre under the Regional Public Health Act.'),
               item('e159_lodging_inspection', anchor='⑥ (지자체) 숙소점검 확인서 ※ 지자체에서 일괄 공문 제출', notes_ko='지자체에서 일괄 공문으로 제출합니다.', notes_en='Submitted in bulk by the local government by official letter.')],
         **NOTE)

# ==========================================================================
# E-9 비전문취업
# ==========================================================================
guidance('E-9', 'visa_issuance', manual=VISA, completeness='PARTIALLY_STRUCTURED', section='비전문취업(E-9) 공관장 재량으로 발급할 수 있는 사증',
         anchor='비전문취업(E-9) 사증은 출입국ㆍ외국인청(사무소ㆍ출장소)장이 발급한',
         summary_ko='비전문취업(E-9) 사증은 출입국·외국인관서의 장이 발급한 사증발급인정서에 의해서만 발급됩니다. 사증 신청 시 국적국의 권한 있는 기관이 발급한 범죄경력증명서와 본인이 자필 기재한 건강상태 확인서를 냅니다.',
         summary_en='E-9 visas are issued only on the basis of a confirmation of visa issuance from an immigration office. When applying for the visa, submit a criminal record certificate from the competent authority of your country and a handwritten health status declaration.',
         conditions_ko=['재입국 취업특례자의 사증 신청은 송출기관에 의한 단체 신청만 가능하고 개별 발급은 불가합니다. 귀국 후 송출기관의 안내에 따라 건강검진을 받은 뒤 신청하고 지정된 날짜에 단체로 입국합니다.'],
         conditions_en=['Re-entry special-case workers can apply only as a group through the sending agency (no individual issuance); after returning home they take a health check as instructed, apply and enter as a group on the set date.'],
         docs=[item('e159_crime_record_e9', anchor='국적국의 권한 있는 기관이 발급한 범죄경력증명서 제출', validity_period='사증발급 신청일로부터 3개월 이내 발급',
                    notes_ko='자국 내의 모든 범죄경력이 포함되어야 합니다. 국적국의 확인 시스템이 미흡하면 거주지(중국은 호구지) 관할 내무기관 등의 증명서로 대체할 수 있습니다.', notes_en='It must cover all criminal records in your country; if the national system is inadequate, a certificate from the interior authority for your residence (hukou place for China) may substitute.'),
               item('e159_health_status_form', anchor='사증신청인이 자필 기재한 양식의 건강상태 확인서를 제출',
                    notes_ko='결핵·B형간염·매독 등 감염 여부, 마약복용 경험, 정신질환 치료경험 등을 본인이 기재합니다.', notes_en='You declare infections such as TB, hepatitis B and syphilis, any drug use and any psychiatric treatment.')],
         **NOTE)

E9_CVI = '사증발급인정신청서 (별지 제21호 서식), 여권, 표준규격사진 1매 - 사업자등록증 사본'


def industry(def_id, anchor, ko, en):
    return item(def_id, 'CONDITIONAL_REQUIRED', anchor=anchor, applies_when_ko=ko, applies_when_en=en)


guidance('E-9', 'visa_issuance_confirmation', manual=VISA, section='비전문취업(E-9) 사증발급인정서 발급대상 — 1. 비전문취업(E-9) 자격 사증발급인정서 발급', anchor='비전문취업(E-9) 자격 사증발급인정서 발급',
         summary_ko='비전문취업자를 초청하려는 사업장의 장이 사업장 주소지 관할 출입국·외국인관서에 직접 방문하거나 대한민국비자포털에서 사증발급인정서를 신청하며, 초청업무를 위임한 경우 업종별 대행기관이 신청할 수 있습니다. 공통서류(신청서·여권·사진, 사업자등록증 사본, 고용허가서 및 표준근로계약서 사본, 사업장실태조사서)에 업종별 추가서류를 냅니다(제조업은 추가서류 없음).',
         summary_en='The head of the inviting workplace applies in person at the immigration office for the workplace address or on the Korea Visa Portal; an industry agency may file if delegated. Submit the common documents (application, passport, photo, business registration copy, copies of the employment permit and standard labour contract, workplace inspection report) plus industry-specific documents (none for manufacturing).',
         filer='employer', channel_ko='사업장 주소지 관할 출입국·외국인관서 방문 또는 대한민국비자포털 (건설업은 공사현장 소재지 관할)', channel_en='Immigration office for the workplace address or the Korea Visa Portal (construction: office for the site)',
         conditions_ko=['업종별 대행기관: 제조업 중소기업중앙회, 건설업 대한건설협회, 어업·냉장·냉동창고업 수협중앙회, 농축산업 농협중앙회', '제조업은 추가서류가 없습니다.'],
         conditions_en=['Industry agencies: manufacturing – Korea Federation of SMEs; construction – Construction Association of Korea; fishery and cold storage – NFFC; agriculture and livestock – NACF.', 'Manufacturing needs no additional documents.'],
         docs=[item('e159_cvi_app_form', anchor=E9_CVI), item('passport', anchor=E9_CVI), item('photo', anchor=E9_CVI),
               item('business_reg_copy', anchor=E9_CVI, role='employer'),
               item('e159_permit_and_contract_copy', anchor='고용허가서 및 표준근로계약서 사본 - 사업장실태조사서'),
               item('e159_workplace_survey', anchor='고용허가서 및 표준근로계약서 사본 - 사업장실태조사서'),
               industry('e159_construction_docs', '건설업등록증, 도급(하도급) 계약서', '건설업', 'Construction'),
               industry('e159_construction_workforce_table', '건설현장에 대한 근무 중 외국인력 현황표', '건설업', 'Construction'),
               industry('e159_farm_business_reg', '농업경영체등록(변경등록)확인서(국립농산물품질관리원장', '농축산업', 'Agriculture and livestock'),
               industry('e159_fishery_coastal', '연근해어업 : 선박(어선)검사증서, 어업허가증(연안어업, 근해어업,', '어업 중 연근해어업', 'Coastal/offshore fishing'),
               industry('e159_fishery_aquaculture', '양식어업 : 선박(어선)검사증서, 어업허가증 또는 어업면허증 또는 내수면어업신고필증', '어업 중 양식어업', 'Aquaculture'),
               industry('e159_salt_permit', '천일염 생산 및 암염 채취업 : 염제조업허가증사본', '천일염 생산 및 암염 채취업', 'Sea-salt / rock-salt production'),
               industry('e159_service_restaurant', '한식 음식점업 : 사업자등록증 또는 영업신고증(지자체 발급), 위탁업체 또는 가맹점인 경우 위탁계약서‧가맹계약서', '서비스업 중 한식 음식점업', 'Korean restaurants'),
               industry('e159_service_hotel', '호텔‧숙박업 : 관광사업 등록증(지자체 발급)', '서비스업 중 호텔·숙박업', 'Hotels and lodging'),
               industry('e159_forestry_docs', '산림사업시행법인 : 사업자등록증 및 산림사업법인 등록증', '임업', 'Forestry'),
               industry('e159_mining_docs', '광업원부(광업등록사무소 발급) 및 광물생산보고서', '광업', 'Mining')],
         **NOTE)

guidance('E-9', 'status_change', completeness='SOURCE_ONLY', section='비전문취업(E-9) 체류자격 변경허가 — 1. 기타(G-1) 자격 소지자의 비전문취업(E-9) 자격 회복절차',
         anchor='기타(G-1) 자격 소지자의 비전문취업(E-9) 자격 회복절차',
         summary_ko='고용허가제 등으로 입국한 뒤 산업재해 치료 등을 위해 기타(G-1)로 변경해 체류하던 외국인근로자 중 국내 체류기간 상한이 도래하지 않은 사람은 비전문취업(E-9) 자격을 회복할 수 있습니다. 체류기간 상한은 입국일부터 3년이며, 3년 만기 체류자 중 고용주가 재고용한 경우 1년 10개월 이내입니다. 이 항목에는 별도 제출서류 목록이 없습니다.',
         summary_en='Workers who entered under the employment permit system and changed to G-1 for industrial-accident treatment etc. may restore E-9 if their maximum stay has not been reached: 3 years from entry, or up to 1 year 10 months more for those re-employed after 3 years. No separate document list is given for this item.')

guidance('E-9', 'workplace_report', section='비전문취업(E-9) 고용변동 신고', anchor='비전문취업(E-9) 외국인근로자를 고용한 자',
         summary_ko='비전문취업(E-9) 외국인근로자를 고용한 사람은 해고·중도 퇴직, 사망, 소재불명, 고용계약의 중요 내용 변경(계약기간, 고용주·대표자, 근무처 명칭·소재지 변경) 사유가 발생한 사실을 안 날부터 15일 이내에 출입국·외국인관서에 고용변동 신고를 합니다. 계약기간 만료로 인한 퇴직은 신고하지 않습니다.',
         summary_en='Employers of E-9 workers report within 15 days of learning of a dismissal or mid-term resignation, death, disappearance, or a material change to the contract (term, employer/representative, workplace name or address). Departures at contract expiry need no report.',
         filer='employer', timing_ko='사유가 발생한 사실을 안 날부터 15일 이내', timing_en='Within 15 days of learning of the event',
         channel_ko='체류지 관할 출입국·외국인관서 방문, 팩스(1577-1346) 또는 하이코리아 전자민원', channel_en='In person at the immigration office, by fax (1577-1346) or via HiKorea e-application',
         conditions_ko=['팩스·하이코리아 신고는 관할 구분 없이 가능하며 신고기한(15일)을 넘기지 않은 경우만 처리됩니다. 하이코리아 신고는 고용노동부 고용변동신고와 일원화되어 있습니다.', '국가기관, 지방자치단체, 교육기관, 법인의 대표자 변경은 신고대상이 아닙니다.'],
         conditions_en=['Fax and HiKorea reports are accepted regardless of jurisdiction and only within the 15-day deadline; HiKorea reports are unified with the Ministry of Employment and Labor\'s report.', 'A change of representative of a state agency, local government, educational institution or corporation is not reportable.'],
         docs=[item('e159_employment_change_form', anchor='고용·연수 외국인 변동사유 발생신고서(별지 32호 서식), 외국인등록증 사본(소재불명 신고의'),
               item('e159_arc_copy', anchor='외국인등록증 사본(소재불명 신고의 경우에는 대상자의 휴대폰 번호, 예상소재지 등을 반드시 포함하여야 함)',
                    notes_ko='소재불명 신고는 대상자의 휴대폰 번호, 예상소재지 등을 반드시 포함해야 합니다.', notes_en='Disappearance reports must include the worker\'s phone number and likely whereabouts.'),
               item('business_reg_copy', anchor='② 사업자등록증 사본 ③ 고용주 신분증(고용주 직접 신고 시)', role='employer'),
               item('e159_employer_id', 'CONDITIONAL_REQUIRED', anchor='③ 고용주 신분증(고용주 직접 신고 시)', applies_when_ko='고용주가 직접 신고하는 경우', applies_when_en='When the employer reports in person'),
               item('e159_staff_proxy_docs', 'CONDITIONAL_REQUIRED', anchor='④ 회사 직원 대리 신청 : 고용주 위임장, 재직증명서, 직원 신분증', applies_when_ko='회사 직원이 대리 신청하는 경우', applies_when_en='When a staff member files on the employer\'s behalf')],
         **NOTE)

E9_RE = '신청서 (별지 34호 서식), 여권, 외국인등록증, 수수료(단수 3만원, 복수 5만원)'
guidance('E-9', 'reentry', section='비전문취업(E-9) 재입국허가', anchor='등록을 필한 외국인이 출국한 날부터 1년 이내에 재입국하려는 경우',
         summary_ko='외국인등록을 한 사람이 출국한 날부터 1년 이내(남은 체류기간이 1년보다 짧으면 그 기간 이내)에 재입국하면 재입국허가가 면제됩니다. 재입국허가를 받을 때는 신청서, 여권, 외국인등록증과 수수료(단수 3만원, 복수 5만원)를 냅니다.',
         summary_en='Registered residents re-entering within one year of departure (or within the remaining stay if shorter) are exempt from the re-entry permit. When a permit is needed, submit the form, passport, residence card and fee (KRW 30,000 single, 50,000 multiple).',
         fee_ko='단수 3만원, 복수 5만원', fee_en='KRW 30,000 single / 50,000 multiple',
         conditions_ko=['입국규제 및 사증발급규제자는 체류지 관할 출입국·외국인관서를 방문하여 재입국허가를 받아야 하며 수수료 제출 대상입니다.'],
         conditions_en=['People under entry or visa-issuance restrictions must visit the immigration office for their address for a re-entry permit and pay the fee.'],
         docs=[item('app_form_34', anchor=E9_RE), item('passport', anchor=E9_RE), item('arc', anchor=E9_RE), item('fee', anchor=E9_RE)],
         **NOTE)
