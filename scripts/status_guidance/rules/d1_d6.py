# D-1 문화예술, D-2 유학, D-3 기술연수, D-4 일반연수, D-5 취재, D-6 종교 — 2026.10.19 manuals.
# Visa rules transcribe the visa-manual chapters (공관장 재량 사증 / 사증발급인정서 첨부서류);
# stay rules transcribe the stay-manual chapters. Only cells left SOURCE_ONLY by author_rules.py are filled.
# Runs inside author_rules.py (guidance, item, docdefs, residence, VISA, STAY …).

docdefs(
    # ---- shared visa forms
    d16_visa_app_17=('사증발급신청서 (별지 제17호 서식)', 'Visa application form (Form 17)', 'applicant', None),
    d16_cvi_app_21=('사증발급인정신청서 (별지 제21호 서식)', 'Application for a confirmation of visa issuance (Form 21)', 'inviter', None),
    d16_cvi_app=('사증발급인정신청서', 'Application for a confirmation of visa issuance', 'inviter', None),
    d16_visa_or_cvi_app=('사증발급(인정)신청서', 'Visa (or confirmation of visa issuance) application form', 'applicant', None),
    d16_photo_6m=('사진 1매 (6개월 이내 촬영 반명함)', 'One photo (half-length, taken within 6 months)', 'applicant', None),
    d16_proxy_docs=('위임장, 대리인 재직증명서, 대리인 신분증 사본', 'Power of attorney, proxy\'s certificate of employment and copy of the proxy\'s ID', 'inviter', None),
    d16_invite_reason=('초청사유서', 'Statement of reasons for the invitation', 'inviter', None),
    # ---- D-1
    d16_invitation=('초청장', 'Invitation letter', 'inviter', None),
    d16_d1_org_proof_visa=('문화예술단체임을 입증하는 서류 (전문가의 지도인 경우에는 그 자의 경력증명서)', 'Proof that the inviter is a culture/arts organisation (for training under an expert, that expert\'s career certificate)', 'inviter', None),
    d16_resume_or_career=('이력서 또는 경력증명서', 'CV or career certificate', 'applicant', None),
    d16_all_expense_proof=('체류 중 일체의 경비지불능력을 증명하는 서류', 'Proof of ability to pay all expenses during the stay', 'applicant', None),
    d16_d1_finance=('재정관계(학비, 체재비) 입증서류', 'Proof of finances (tuition, living costs)', 'applicant', None),
    d16_diplomat_id=('외교관신분증', 'Diplomatic ID card', 'applicant', None),
    d16_mofa_recommendation=('외교통상부 추천서', 'Recommendation from the Ministry of Foreign Affairs', 'other_third_party', None),
    d16_embassy_letter_or_consent=('대사관의 협조공문 또는 동의서', 'Embassy cooperation letter or consent', 'other_third_party', None),
    d16_org_docs_copy=('사업자 등록증 또는 고유번호증 등 관련단체 서류 사본', 'Copy of the organisation\'s documents (business registration or unique number certificate)', 'business_entity', None),
    d16_relevant_proof=('해당 입증서류', 'Supporting documents for the activity', 'applicant', None),
    # ---- D-2
    d16_school_biz_reg=('교육기관 사업자등록증 (또는 고유번호증) 사본', 'Copy of the school\'s business registration (or unique number) certificate', 'educational_institution', None),
    d16_standard_admission=('표준입학허가서 (대학 총·학장 발행)', 'Standard certificate of admission (issued by the university president/dean)', 'educational_institution', None),
    d16_final_education=('최종학력 입증서류', 'Proof of highest education', 'applicant', None),
    d16_finance_ability=('재정능력 입증서류', 'Proof of financial ability', 'applicant', None),
    d16_d25_guarantor_or_finance=('신원보증서 또는 재정능력 입증서류 (잔고증명, 연구수당 지급 확인서 등)', 'Letter of guarantee or proof of finances (bank balance, research-allowance confirmation, etc.)', 'applicant', None),
    d16_d25_research_proof=('특정연구과정임을 입증하는 서류 (총장의 연구생확인서 등)', 'Proof of the research programme (president\'s research-student confirmation, etc.)', 'educational_institution', None),
    d16_d26_home_recommendation=('소속 (본국) 대학의 장이 발급한 추천서', 'Recommendation from the head of the home university', 'educational_institution', None),
    d16_d26_exchange_proof=('교환학생임을 입증하는 서류 (초청 대학의 공문, 대학 간 체결한 학생교류 협정서 등)', 'Proof of exchange-student status (inviting university\'s letter, student-exchange agreement, etc.)', 'educational_institution', None),
    d16_d26_semester_proof=('1학기 이상을 외국 정규대학에서 수학하였음을 입증하는 서류 (본국 대학의 재학증명서 등)', 'Proof of at least one semester at a regular foreign university (home-university enrollment certificate, etc.)', 'applicant', None),
    d16_prev_course_grades=('이전 과정의 성적(출석/연수)증명서', 'Grade (attendance/training) certificate from the previous course', 'educational_institution', None),
    d16_research_institute_biz_reg=('연구원의 사업자등록증 사본', 'Copy of the research institute\'s business registration', 'employer', None),
    # ---- D-3
    d16_d3_local_corp_reg=('현지법인등록증(또는 설립인가서) 사본', 'Copy of the local subsidiary\'s registration (or establishment approval)', 'business_entity', None),
    d16_d3_local_employment=('현지법인의 장이 발급한 피초청자 재직증명서 및 여권사본', 'Certificate of employment issued by the head of the local subsidiary and passport copy', 'business_entity', None),
    d16_d3_korean_proof=('한국어능력입증자료', 'Proof of Korean ability', 'applicant', None),
    d16_d3_training_plan=('연수내용을 확인할 수 있는 연수계획서 (별첨 3)', 'Training plan showing the training content (Annex 3)', 'inviter', None),
    d16_inviter_guarantee=('초청자의 신원보증서', 'Inviter\'s letter of guarantee', 'inviter', None),
    d16_d3_company_eligibility=('초청업체가 연수허용대상 업체임을 입증할 수 있는 서류', 'Proof that the inviting company is eligible to host trainees', 'inviter', None),
    d16_d3_workforce=('초청업체의 내국인 상시 근로자 수 입증서류 (사업장별 피보험자격내역서)', 'Proof of the inviting company\'s number of regular Korean workers (insured-status record per workplace)', 'inviter', None),
    d16_d3_environment=('자체 연수시설(공정)과 적정한 숙박시설 구비 등 연수환경을 확인할 수 있는 자료 (기숙사 시설 내부 사진 등)', 'Material showing the training environment, such as in-house training facilities and suitable accommodation (photos of the dormitory, etc.)', 'inviter', None),
    d16_d3_ext_reason=('연수기간 연장신청 사유서 (별도서식)', 'Statement of reasons for extending the training period (separate form)', 'inviter', None),
    d16_d3_biz_factory=('사업자등록증과 공장등록증 (또는 공장등록증명서, 해당자만 제출)', 'Business registration and factory registration (or factory registration certificate, if applicable)', 'inviter', None),
    d16_d3_domestic_tax=('국내법인 납세증명서', 'Tax payment certificate of the Korean company', 'inviter', None),
    d16_d3_local_tax=('현지법인 납세사실 관련 증명 서류', 'Proof of tax payments by the local subsidiary', 'business_entity', None),
    d16_d3_wage_proof=('연수생 임금 및 연수수당 지급 여부 확인서류', 'Proof of payment of trainee wages and training allowances', 'inviter', None),
    d16_d3_insurance=('산업재해보상보험, 국민건강보험 가입증명서류 및 연수수당 등 체불에 대비한 보증보험 가입증명서류', 'Proof of industrial-accident and national health insurance, and of guarantee insurance against unpaid training allowances', 'inviter', None),
    d16_color_photo=('컬러사진 (3.5cm × 4.5cm) 1장', 'One colour photo (3.5 cm × 4.5 cm)', 'applicant', None),
    d16_health_cert=('건강진단서', 'Health certificate', 'applicant', None),
    d16_d3_reg_insurance=('산업재해보상보험 또는 보증보험 가입증명서류', 'Proof of industrial-accident insurance or guarantee insurance', 'inviter', None),
    # ---- D-4
    d16_d4_school_biz_reg=('교육기관 사업자등록증 사본 또는 고유번호증 사본', 'Copy of the school\'s business registration or unique number certificate', 'educational_institution', None),
    d16_d4_enroll_or_edu=('재학증명서 또는 최종학력 입증서류', 'Enrollment certificate or proof of highest education', 'applicant', None),
    d16_d4_finance=('재정 입증서류', 'Proof of finances', 'applicant', None),
    d16_family_cert=('가족관계증명서', 'Family relation certificate', 'applicant', None),
    d16_d4_lang_plan=('연수계획서 (강의시간표, 강사구성표, 연수시설 등의 내용을 포함)', 'Training plan (class timetable, instructor list, facilities, etc.)', 'educational_institution', None),
    d16_need_for_language_training=('어학연수 필요성 소명자료', 'Explanation of the need for language training', 'applicant', None),
    d16_d42_necessity=('연수의 필요성을 입증하는 서류 (취업확인서, 연수계획서 등)', 'Proof of the need for training (employment confirmation, training plan, etc.)', 'applicant', None),
    d16_d42_company=('외국인 투자기업 또는 외국에 투자한 국내기업임을 입증하는 서류', 'Proof that the company is a foreign-invested company or a Korean company that has invested abroad', 'business_entity', None),
    d16_2k_relation=('해외법인·국내 초청기업 관계 입증서류 (초청기업 사업자등록증, 해외 법인 설립 신고서 등)', 'Proof of the relationship between the overseas entity and the inviting Korean company (business registration, overseas incorporation report, etc.)', 'inviter', None),
    d16_2k_tax_workforce=('납세증명서(국세, 지방세), 상시 근로자 수 입증 서류', 'Tax payment certificates (national and local) and proof of the number of regular workers', 'inviter', None),
    d16_2k_plan=('인턴·연수 활동 계획서', 'Internship/training activity plan', 'inviter', None),
    d16_2k_mou=('현지 대학과의 산학협력 체결 입증서류 (MOU 등)', 'Proof of the industry–university cooperation agreement with the local university (MOU, etc.)', 'inviter', None),
    d16_2k_support=('기업이 맞춤형 인재로 양성·후원하는 입증서류', 'Proof that the company trains and sponsors the student as customised talent', 'inviter', None),
    d16_2k_enroll_korean=('재학증명서 및 한국어 능력 입증 서류', 'Enrollment certificate and proof of Korean ability', 'applicant', None),
    d16_2k_employment=('재직증명서 (담당 업무, 재직 기간 포함)', 'Certificate of employment (with duties and period of employment)', 'business_entity', None),
    d16_d43_admission=('입학허가서 (학교장 발행, 붙임 1 서식)', 'Certificate of admission (issued by the principal, Attachment 1 form)', 'educational_institution', None),
    d16_d43_final_edu=('최종 학력 입증서류 (졸업증명서 또는 재학증명서 등)', 'Proof of highest education (graduation or enrollment certificate, etc.)', 'applicant', None),
    d16_guardian_guarantee=('후견 보증서 (붙임 2 서식)', 'Guardianship guarantee (Attachment 2 form)', 'sponsor', None),
    d16_guardian_relation=('후견인과의 관계 증명서류 (친족관계가 아닌 경우 관계 소명 자료 등)', 'Proof of the relationship with the guardian (explanation if not a relative)', 'sponsor', None),
    d16_guardian_finance=('후견인 재정능력 입증서류', 'Proof of the guardian\'s financial ability', 'sponsor', None),
    d16_d43_scholarship=('전액 장학생 입증서류 (정부기관 및 지방자치단체의 공문)', 'Proof of a full scholarship (official letter from the government body or local government)', 'local_government', None),
    d16_d43_purpose=('초청 목적 입증서류 (교육 계획(안), 진로 지도(안) 등)', 'Proof of the purpose of the invitation (education plan, career-guidance plan, etc.)', 'local_government', None),
    d16_d43_admission_enroll=('입학허가서 (학교장 발행, 붙임 1 서식) 및 재학증명서 (해당자)', 'Certificate of admission (issued by the principal, Attachment 1 form) and enrollment certificate (if applicable)', 'educational_institution', None),
    d16_photo_half=('반명함판 사진 (3.5×4.5㎝) 1장', 'One half-length photo (3.5 × 4.5 cm)', 'applicant', None),
    d16_d45_edu_admission=('최종학력 입증서류 및 수라학교 입학허가서 (연수기관장 발행)', 'Proof of highest education and Sura School admission (issued by the head of the institution)', 'applicant', None),
    d16_d45_stay_cost=('국내 체제비 입증서류 (잔고증명, 부모 재정능력 등)', 'Proof of living costs in Korea (bank balance, parents\' finances, etc.)', 'applicant', None),
    d16_d45_fee_paid=('교육비 납입증명서', 'Proof of payment of training fees', 'educational_institution', None),
    d16_d45_korean=('한국어 기초능력 입증서류 (토픽 1급 상당) 또는 면제신청서류', 'Proof of basic Korean ability (TOPIK level 1 equivalent) or exemption request', 'applicant', None),
    d16_d45_recommendation=('한식 연수생 추천서 (붙임2 서식)', 'Korean-cuisine trainee recommendation (Attachment 2 form)', 'educational_institution', None),
    d16_d45_inst_docs=('연수기관 설립 관련 서류 (사업자등록증 또는 고유번호증 사본, 법인등기부등본 등)', 'Documents on the institution\'s establishment (copy of business registration or unique number certificate, corporate register, etc.)', 'educational_institution', None),
    d16_d45_designation=('수라학교 지정증 (붙임1 서식)', 'Sura School designation certificate (Attachment 1 form)', 'educational_institution', None),
    d16_d45_plan=('기관 연수계획서 (연수일정 포함)', 'Institution\'s training plan (with schedule)', 'educational_institution', None),
    d16_dorm_proof=('기숙사 보유 입증서류', 'Proof that the institution has a dormitory', 'educational_institution', None),
    d16_d45_enroll=('한식 연수과정 재학증명서 (연수기관 발행)', 'Enrollment certificate for the Korean-cuisine course (issued by the institution)', 'educational_institution', None),
    d16_d45_fee_cert=('연수비 납입증명서 (연수기관 발행)', 'Proof of payment of training fees (issued by the institution)', 'educational_institution', None),
    d16_d45_individual_plan=('개인별 연수 계획서 (旣 이수과정 성적·출석율 명시하여 연수기관 작성)', 'Individual training plan (written by the institution, with grades and attendance so far)', 'educational_institution', None),
    d16_d45_orientation=('입국 후 국내 적응 오리엔테이션 실시 결과 보고서', 'Report on the post-entry adaptation orientation', 'educational_institution', None),
    d16_d45_korean_ext=('한국어능력 입증서류 (기초·심화 과정 수료기준 충족여부 확인)', 'Proof of Korean ability (meeting the basic/advanced course completion standard)', 'applicant', None),
    d16_d45_health_ext=('건강진단서 (치료예정확인서 제출자에 한함)', 'Health certificate (only for those who submitted a planned-treatment confirmation)', 'applicant', None),
    d16_d45_school_biz_reg=('연수기관 사업자등록증 (또는 고유번호증) 사본', 'Copy of the training institution\'s business registration (or unique number) certificate', 'educational_institution', None),
    d16_d45_sura_designation_reg=('농식품부 발행 한식 전문인력 양성기관(수라학교) 지정증', 'Sura School designation as a Korean-cuisine training institution (issued by the Ministry of Agriculture)', 'educational_institution', None),
    d16_health_designated=('법무부 지정병원에서 발급한 건강진단서', 'Health certificate from a hospital designated by the Ministry of Justice', 'applicant', None),
    d16_d43_scholar_proof_reg=('장학생 입증서류 (해당자, 기관·단체의 공문)', 'Proof of scholarship (if applicable; official letter from the body)', 'other_third_party', None),
    d16_d46_edu_admission=('최종학력 입증서류(공증) 및 입학허가서 (교육기관장 발행)', 'Proof of highest education (notarised) and certificate of admission (issued by the head of the institution)', 'applicant', None),
    d16_d46_finance=('재정능력 입증서류 (잔고증명, 부모 재정능력 등)', 'Proof of financial ability (bank balance, parents\' finances, etc.)', 'applicant', None),
    d16_d46_fee_paid=('등록금 또는 교육비 납입증명서', 'Proof of payment of tuition or training fees', 'educational_institution', None),
    d16_d46_korean=('한국어 능력 입증서류 (토픽 1급이상, 세종학당 초급1 과정 이상 수료증)', 'Proof of Korean ability (TOPIK 1+ or King Sejong Institute Beginner 1+ certificate)', 'applicant', None),
    d16_d46_inst_docs=('교육기관설립관련 서류', 'Documents on the institution\'s establishment', 'educational_institution', None),
    d16_d46_corp_register=('교육기관 법인등기부등본 (등기사항전부증명서, 법원발행)', 'Institution\'s corporate register (certificate of registered matters, court-issued)', 'educational_institution', None),
    d16_d46_biz_reg=('사업자등록증 또는 고유번호증 사본', 'Copy of the business registration or unique number certificate', 'educational_institution', None),
    d16_d46_plan=('연수계획서 (강의시간표, 강사구성표, 연수시설, 학비 등의 내용 포함)', 'Training plan (timetable, instructor list, facilities, tuition, etc.)', 'educational_institution', None),
    d16_d46_academy_reg=('학원설립․운영 등록증 (교육청 발행, 직업기술과정)', 'Academy establishment/operation registration (education office, vocational courses)', 'educational_institution', None),
    d16_d46_training_corp=('직업능력개발훈련법인 설립허가서 (직업능력개발훈련법인에 한함)', 'Establishment permit of the vocational-training corporation (vocational-training corporations only)', 'educational_institution', None),
    d16_d46_listed_company=('상장기업입증서류 및 교육기관이 해당 기업과 연계 또는 기업에 의해 설립되었음을 입증하는 서류 (국내상장기업 연계 또는 설립기관에 한함)', 'Proof of the listed company and of the institution\'s link to or establishment by it (listed-company institutions only)', 'educational_institution', None),
    d16_d46_univ_affiliated=('대학부설 시설 전문교육기관임을 입증하는 서류 (대학부설 교육기관에 한함)', 'Proof of being a university-affiliated specialist institution (university-affiliated institutions only)', 'educational_institution', None),
    d16_d46_foreign_branch=('해외 교육기관의 국내지사 또는 독점 운영계약자임을 입증하는 서류 (해외교육기관 국내지사에 한함)', 'Proof of being the Korean branch or exclusive operator of a foreign institution (such branches only)', 'educational_institution', None),
    d16_d46_credit_recognition=('학습과정 평가 인정서 (교육부장관 발행, 학점인정 입증)', 'Course accreditation certificate (Minister of Education, credit recognition)', 'educational_institution', None),
    d16_d46_domestic_students=('교육기관의 국민 교육생 유치 실적 증빙 서류', 'Proof of the institution\'s record of enrolling Korean students', 'educational_institution', None),
    d16_d46_operation=('기타 교육기관 정상운영 및 교육과정 정상 운영 능력 입증 서류', 'Other proof that the institution and its courses operate normally', 'educational_institution', None),
    d16_d46_inst_ext=('연수기관 준비서류 (출석증명서, 기술연수 계획서, 기숙사 입실 확인서(해당자), 기타 연수를 정상적으로 수행하고 있음을 입증하는 서류)', 'Institution documents (attendance certificate, technical training plan, dormitory confirmation if applicable, other proof of normal training)', 'educational_institution', None),
    d16_d46_stay_cost_ext=('체류경비 입증서류 (은행발행 잔액증명 및 해당 계좌 최근 6개월간의 예금거래실적증명서)', 'Proof of living costs (bank balance certificate and the account\'s last 6 months of transactions)', 'applicant', None),
    d16_d46_fee_ext=('등록금(교육비) 납입 증명 (수강기간 및 수강료, 납부일 등 기재)', 'Proof of tuition payment (course period, fee and payment date)', 'educational_institution', None),
    d16_d46_enroll_ext=('재학(연수) 증명 (입학일, 전공 등 기재)', 'Enrollment (training) certificate (admission date, major, etc.)', 'educational_institution', None),
    d16_d46_plan_ext=('연수계획서 (체류기간 1년 초과자)', 'Training plan (for stays over one year)', 'educational_institution', None),
    d16_d4_other_training_proof=('연수(연구 활동)를 증명하는 서류 (연수일정이 포함된 연수계획서 등)', 'Proof of the training (research) activity (training plan with schedule, etc.)', 'inviter', None),
    # ---- D-5
    d16_dispatch_or_employment=('파견명령서 또는 재직증명서', 'Dispatch order or certificate of employment', 'employer', None),
    d16_press_permit_or_funds=('국내 지국·지사 설치허가증이나 국내 지국·지사 운영자금 도입실적 증빙서류', 'Permit for the bureau/branch in Korea or proof of operating funds brought in for it', 'employer', None),
    d16_mcst_cooperation=('주무부처(문화체육관광부 해외문화홍보원)의 협조공문', 'Cooperation letter from the competent ministry (Korean Culture and Information Service)', 'other_third_party', None),
    d16_dispatch_order_head=('파견명령서 (본사 발행)', 'Dispatch order (issued by the head office)', 'employer', None),
    d16_press_permit_or_bizreg=('지국․지사의 설치허가증 (문화체육관광부에서 발행) 또는 사업자등록증 사본', 'Bureau/branch establishment permit (issued by the Ministry of Culture) or copy of the business registration', 'employer', None),
    d16_longterm_need=('관계부처 협조공한 등 장기취재 필요성을 입증할 수 있는 서류', 'Proof of the need for long-term reporting, such as a cooperation letter from the relevant ministry', 'other_third_party', None),
    # ---- D-6
    d16_dispatch_order=('파견명령서', 'Dispatch order', 'employer', None),
    d16_religious_permit=('종교단체 설립허가서 또는 사회복지단체 설립허가서 사본', 'Copy of the religious or social-welfare organisation\'s establishment permit', 'employer', None),
    d16_org_expense_support=('소속단체의 체류경비 지원 관련서류', 'Documents on the organisation\'s support for living costs', 'employer', None),
    d16_unique_no_copy=('고유번호증 사본', 'Copy of the unique number certificate', 'employer', None),
    d16_same_foundation=('동일재단입증서류', 'Proof that both bodies belong to the same foundation', 'employer', None),
    d16_degree_cert=('학위증', 'Degree certificate', 'applicant', None),
    d16_original_employer_consent=('원근무처장의 동의서', 'Consent of the head of the original workplace', 'employer', None),
    d16_org_establishment_permit=('해당단체 설립허가서', 'Establishment permit of the organisation', 'employer', None),
)

NOTES = dict(notes_ko=[OFFICER_NOTE_KO], notes_en=[OFFICER_NOTE_EN])


def visa_base_17(anchor):
    return [item('d16_visa_app_17', anchor=anchor), item('passport', anchor=anchor), item('photo', anchor=anchor), item('fee', anchor=anchor)]


def cvi_base_21(anchor, passport='passport_copy'):
    return [item('d16_cvi_app_21', anchor=anchor), item(passport, anchor=anchor), item('photo', anchor=anchor)]


def proxy_item(anchor='대리인 신청시 : 위임장, 대리인 재직증명서, 대리인 신분증 사본 추가 제출'):
    return item('d16_proxy_docs', 'CONDITIONAL_REQUIRED', anchor=anchor, applies_when_ko='대리인이 신청하는 경우', applies_when_en='If a proxy files the application')


def multi_reentry(code, name_ko, name_en, anchor='출국 후 체류기간 범위 내에서 1년을 초과하여 2년 내에 재입국을 하려는 경우',
                  restricted_ko='입국규제 및 사증발급규제자는 체류지 관할 청(사무소·출장소)에 방문하여 재입국허가를 받아야 합니다.',
                  restricted_en='People subject to entry or visa restrictions must visit the local office and obtain a re-entry permit.'):
    doc_anchor = '신청서류 : 신청서(별지 34호서식), 여권 원본, 외국인등록증, 수수료'
    when_ko, when_en = '출국 후 체류기간 범위 내에서 1년을 초과하여 2년 내에 재입국하려는 경우 (복수재입국허가)', 'Re-entering more than 1 year but within 2 years of departure, within the stay period (multiple re-entry permit)'
    guidance(code, 'reentry', section=f'{name_ko} 재입국허가', anchor=anchor,
             summary_ko=f'{name_ko} 자격으로 등록한 사람이 출국한 날부터 1년 이내(남은 체류기간이 1년보다 짧으면 그 범위 내)에 재입국하면 재입국허가가 면제됩니다. 1년을 넘어 2년 내에 재입국하려면 복수재입국허가를 신청서·여권 원본·외국인등록증·수수료로 신청합니다.',
             summary_en=f'Registered {name_en} holders re-entering within one year of departure (or within the remaining stay if shorter) are exempt from a re-entry permit. To re-enter after more than one year but within two, apply for a multiple re-entry permit with the form, original passport, residence card and fee.',
             conditions_ko=[restricted_ko, '사우디아라비아, 이란, 리비아 국민은 복수재입국이 제한됩니다(이들 국가 국민 중 결혼이민(F-6), 유학(D-2), 일반연수(D-4)는 가능).'],
             conditions_en=[restricted_en, 'Multiple re-entry is restricted for nationals of Saudi Arabia, Iran and Libya (except F-6, D-2 and D-4 holders).'],
             docs=[item(d, anchor=doc_anchor, applies_when_ko=when_ko, applies_when_en=when_en) for d in ('app_form_34', 'passport_original', 'arc', 'fee')], **NOTES)


# ==========================================================================
# D-1 문화예술 (visa manual 문화예술(D-1) / stay manual 문화예술(D-1))
# ==========================================================================
D1_VISA_DOCS_TAIL = [
    item('d16_invitation', anchor='② 초청장'),
    item('d16_d1_org_proof_visa', anchor='문화예술단체임을 입증하는 서류'),
    item('d16_resume_or_career', anchor='④ 이력서 또는 경력증명서'),
    item('d16_all_expense_proof', anchor='체류 중 일체의 경비지불능력을 증명하는 서류'),
]
guidance('D-1', 'visa_issuance', manual=VISA, section='문화예술(D-1) — 공관장 재량으로 발급할 수 있는 사증', anchor='한국국제교류재단 및 한국문화예술위원회의 초청을 받아',
         summary_ko='한국국제교류재단·한국문화예술위원회의 초청을 받아 문화예술 활동을 하려는 사람은 재외공관에서 체류기간 1년 이하의 단수사증을 받을 수 있습니다. 그 밖의 경우는 모두 사증발급인정서로 사증이 발급됩니다.',
         summary_en='People invited by the Korea Foundation or the Arts Council Korea for culture/arts activities can get a single-entry visa of up to one year at a Korean mission. All other cases are issued on a confirmation of visa issuance.',
         docs=visa_base_17('① 사증발급신청서 (별지 제17호 서식), 여권, 표준규격사진 1매, 수수료') + D1_VISA_DOCS_TAIL,
         notes_ko=['재외공관의 장은 필요한 경우 첨부서류를 일부 가감할 수 있습니다.', OFFICER_NOTE_KO], notes_en=['The head of the mission may add or waive some documents when needed.', OFFICER_NOTE_EN])
guidance('D-1', 'visa_issuance_confirmation', manual=VISA, section='문화예술(D-1) — 사증발급인정서 발급대상', anchor='상기 󰡔공관장 재량으로 발급할 수 있는 사증󰡕 이외의 경우에는 모두 사증발급인정서에 의해 사증발급',
         summary_ko='공관장 재량 사증 대상(한국국제교류재단·한국문화예술위원회 초청) 이외의 문화예술(D-1)은 모두 사증발급인정서로 사증이 발급됩니다. 초청장, 문화예술단체 입증서류, 이력서 또는 경력증명서, 경비지불능력 증명서류를 냅니다.',
         summary_en='All D-1 cases other than the mission-discretion visa (Korea Foundation / Arts Council invitations) go through a confirmation of visa issuance, with an invitation, proof of the arts organisation, CV or career certificate and proof of ability to pay expenses.',
         docs=cvi_base_21('① 사증발급인정신청서 (별지 제21호 서식), 여권, 표준규격사진 1매', passport='passport') + [
             item('d16_invitation', anchor='② 초청장'),
             item('d16_d1_org_proof_visa', anchor='③ 문화예술단체임을 입증하는 서류'),
             item('d16_resume_or_career', anchor='④ 이력서 또는 경력증명서'),
             item('d16_all_expense_proof', anchor='⑤ 체류 중 일체의 경비지불능력을 증명하는 서류')],
         notes_ko=['출입국·외국인청(사무소·출장소)장은 첨부서류의 일부를 가감할 수 있습니다.', OFFICER_NOTE_KO], notes_en=['The immigration office may add or waive some documents.', OFFICER_NOTE_EN])

guidance('D-1', 'status_change', section='문화예술(D-1) 체류자격 변경허가', anchor='문화예술(D-1) 체류자격변경이 가능한 경우',
         summary_ko='매뉴얼은 문화예술(D-1)로 체류자격을 변경할 수 있는 경우로 해외입양으로 외국국적을 취득한 사람, 사증면제(B-1)로 입국한 독일인, 6개월 미만 체류하려는 캐나다 국민을 듭니다. 필수서류는 신청서·여권 원본·수수료, 연수일정표, 문화예술단체 입증서류입니다.',
         summary_en='The manual lists those who may change to D-1: people who acquired foreign nationality through overseas adoption, Germans who entered visa-free (B-1), and Canadians staying under six months. Required: the form, original passport, fee, the training schedule and proof of the arts organisation.',
         conditions_ko=['6개월 미만 체류하려는 캐나다 국민의 체류기간은 입국일로부터 6개월 미만입니다.', '재정입증서류를 제출하지 못하면 신원보증서를 징구합니다.'],
         conditions_en=['For Canadians staying under six months, the stay is less than six months from entry.', 'If financial proof cannot be submitted, a letter of guarantee is taken instead.'],
         docs=[item('app_form_34', anchor='①신청서(별지 제34호서식), 여권 원본, 수수료'),
               item('passport_original', anchor='①신청서(별지 제34호서식), 여권 원본, 수수료'),
               item('fee', anchor='①신청서(별지 제34호서식), 여권 원본, 수수료'),
               item('training_schedule', anchor='②연수기관이 작성한', role='educational_institution'),
               item('culture_org_proof', anchor='③문화예술단체 입증서류(사업자등록증 사본 등)', role='educational_institution'),
               item('d16_invite_reason', 'ADDITIONAL_IF_APPLICABLE', anchor='①초청사유서 ②연수증명서', applies_when_ko='심사에 필요한 추가서류', applies_when_en='Additional document for review'),
               item('training_cert', 'ADDITIONAL_IF_APPLICABLE', anchor='①초청사유서 ②연수증명서', role='educational_institution', applies_when_ko='심사에 필요한 추가서류', applies_when_en='Additional document for review'),
               item('d16_d1_finance', 'ADDITIONAL_IF_APPLICABLE', anchor='③재정관계(학비,체재비)입증서류', applies_when_ko='심사에 필요한 추가서류', applies_when_en='Additional document for review'),
               item('guarantor', 'ALTERNATIVE_DOCUMENT', anchor='재정입증서류를 제출하지 못하면 신원보증서 징구', applies_when_ko='재정입증서류를 제출하지 못하는 경우', applies_when_en='If financial proof cannot be submitted')],
         **NOTES)

guidance('D-1', 'activities_outside_status', section='문화예술(D-1) 체류자격외 활동', anchor='주한외국공관원 가족(A-1, A-2 자격)의 문화예술(D-1) 자격외 활동',
         summary_ko='한국 고유문화·예술에 대한 전문가 지도, 대학부설 어학원의 한국어 연수, 비영리 자원봉사, (D-1 소지자의) 정규교육기관 교육은 체류기간 범위에서 별도 허가 없이 가능합니다. 주한외국공관원 가족(A-1, A-2)이 수익을 목적으로 하지 않는 학술·예술 활동을 하려면 허가가 필요합니다.',
         summary_en='Expert training in traditional Korean culture or arts, Korean study at a university language institute, non-profit volunteering and (for D-1 holders) regular schooling need no separate permit within the stay. Family members of foreign mission staff (A-1, A-2) need a permit for non-profit academic or artistic activities.',
         docs=[item('app_form_34', anchor='①신청서(별지34호 서식), 여권 원본, 외교관신분증, 수수료'),
               item('passport_original', anchor='①신청서(별지34호 서식), 여권 원본, 외교관신분증, 수수료'),
               item('d16_diplomat_id', anchor='①신청서(별지34호 서식), 여권 원본, 외교관신분증, 수수료'),
               item('fee', anchor='①신청서(별지34호 서식), 여권 원본, 외교관신분증, 수수료'),
               item('d16_mofa_recommendation', anchor='②외교통상부 추천서'),
               item('d16_embassy_letter_or_consent', anchor='③대사관의 협조공문 또는 동의서'),
               item('d16_org_docs_copy', anchor='④사업자 등록증 또는 고유번호증 등 관련단체 서류 사본'),
               item('d16_relevant_proof', anchor='⑤ 해당 입증서류')],
         conditions_ko=['자원봉사는 공공기관, 고아원, 양로원, 무료급식소, 자선바자회, 국제전시회, 국제행사 등에서 가능하며 식비 및 교통비 지급이 가능합니다.'],
         conditions_en=['Volunteering is allowed at public bodies, orphanages, care homes, free-meal centres, charity bazaars, international exhibitions and events; meals and transport may be paid.'],
         **NOTES)

guidance('D-1', 'workplace_change', state='NOT_APPLICABLE', completeness='SOURCE_ONLY', section='문화예술(D-1) 근무처의 변경․추가', anchor='근무처의 변경․추가 신고대상 아님',
         summary_ko='문화예술(D-1)은 근무처의 변경·추가 신고대상이 아닙니다. 소속기관 또는 단체의 변경(명칭변경 포함)이나 추가는 외국인등록사항 변경신고로 처리합니다.',
         summary_en='D-1 is not subject to workplace change/addition reporting. A change (including renaming) or addition of the affiliated institution or organisation is handled as a registration-information change report.')

multi_reentry('D-1', '문화예술(D-1)', 'D-1')

# ==========================================================================
# D-2 유학
# ==========================================================================
D2_COMMON_ANCHOR = '① 사증발급(인정)신청서, 여권사본, 사진 1매(6개월 이내 촬영 반명함)'


def d2_visa_docs():
    return [
        item('d16_visa_or_cvi_app', anchor=D2_COMMON_ANCHOR), item('passport_copy', anchor=D2_COMMON_ANCHOR), item('d16_photo_6m', anchor=D2_COMMON_ANCHOR),
        item('d16_school_biz_reg', anchor='② 교육기관 사업자등록증 (또는 고유번호증) 사본'),
        item('d16_standard_admission', anchor='③ 표준입학허가서 (대학 총․학장 발행)', notes_ko='국립국제교육원 및 국방부초청 정부 장학생은 교육원장 및 국방부장관이 발급한 초청장으로 대체합니다.', notes_en='Government scholars invited by NIIED or the Ministry of National Defense submit the invitation issued by them instead.'),
        item('tb_cert', 'CONDITIONAL_REQUIRED', anchor='④ 결핵진단서 (해당자에 한함)', applies_when_ko='해당자에 한함', applies_when_en='Only if applicable'),
        item('family_relation', 'CONDITIONAL_REQUIRED', anchor='⑤ 가족관계 입증서류 (부모의 잔고증명 등을 제출한 경우에 한함)', applies_when_ko='부모의 잔고증명 등을 제출한 경우', applies_when_en='If a parent\'s bank-balance certificate is submitted'),
        item('d16_final_education', anchor='⑥ 최종학력 입증서류', notes_ko='원본심사가 원칙이며, 국가별로 아포스티유 또는 영사확인(중국은 학력·학위인증센터 인증보고서 등)이 필요합니다.', notes_en='Originals are reviewed; apostille or consular confirmation is required depending on the country (for China, a verification report from the degree-verification centre, etc.).'),
        item('d16_finance_ability', anchor='⑦ 재정능력 입증서류', notes_ko='1년간 등록금 및 체재비 상당 금액, 국내·외 은행 잔고증명서(신청인·부모·부모 사망 시 형제자매 명의), 신청일 기준 30일 이내 발급.', notes_en='One year of tuition and living costs; bank balance certificate from a Korean or foreign bank (applicant, parents, or siblings if both parents died), issued within 30 days of applying.'),
        item('d16_final_education', 'CONDITIONAL_REQUIRED', anchor='최종학력 입증서류(석사학위이상 소지자를 원칙으로 함)', applies_when_ko='연구과정(D-2-5)', applies_when_en='Research programme (D-2-5)'),
        item('d16_d25_guarantor_or_finance', 'CONDITIONAL_REQUIRED', anchor='신원보증서 또는 재정능력 입증서류(잔고증명, 연구수당', applies_when_ko='연구과정(D-2-5)', applies_when_en='Research programme (D-2-5)'),
        item('d16_d25_research_proof', 'CONDITIONAL_REQUIRED', anchor='특정연구과정임을 입증하는 서류(총장의 연구생확인서 등)', applies_when_ko='연구과정(D-2-5)', applies_when_en='Research programme (D-2-5)'),
        item('d16_d26_home_recommendation', 'CONDITIONAL_REQUIRED', anchor='소속 (본국) 대학의 장이 발급한 추천서', applies_when_ko='교환학생(D-2-6)', applies_when_en='Exchange student (D-2-6)'),
        item('d16_d26_exchange_proof', 'CONDITIONAL_REQUIRED', anchor='교환학생임을 입증하는 서류 (초청 대학의 공문, 대학 간', applies_when_ko='교환학생(D-2-6)', applies_when_en='Exchange student (D-2-6)'),
        item('d16_d26_semester_proof', 'CONDITIONAL_REQUIRED', anchor='1학기 이상을 외국 정규대학에서 수학하였음을 입증하는 서류 (본국 대학의 재학증명서 등)', applies_when_ko='교환학생(D-2-6)', applies_when_en='Exchange student (D-2-6)'),
    ]


D2_VISA_SECTION = '유학(D-2) — 사증발급 일반 2. 제출서류'
guidance('D-2', 'visa_issuance', manual=VISA, section=D2_VISA_SECTION, anchor=D2_COMMON_ANCHOR, doc_page_window=4,
         summary_ko='유학(D-2) 사증은 공통서류(신청서·여권사본·사진, 교육기관 사업자등록증 사본, 표준입학허가서, 최종학력·재정능력 입증서류 등)에 연구과정(D-2-5)·교환학생(D-2-6)은 과정별 추가서류를 냅니다. 공관장 재량 사증은 사증발급인정서 발급 대상 이외의 유학생이 거주국 또는 최종학교 소재지 관할 공관에 신청합니다.',
         summary_en='A D-2 visa needs the common documents (form, passport copy, photo, the school\'s business registration copy, standard admission certificate, proof of education and finances, etc.), plus course-specific documents for research (D-2-5) and exchange (D-2-6) students. Students outside the CVI groups apply at the mission for their country of residence or last school.',
         conditions_ko=['사증 또는 사증발급인정서 중 어느 쪽으로 발급되는지는 대학 등급(우수인증대·인증대·일반대·비자심사강화대 등)과 국적에 따른 대상별 사증 발급 유형표에 따릅니다. 쿠바, 시리아, 마케도니아, 코소보 국민은 사증발급인정서만 발급됩니다.',
                        '발급내용: 전문학사~박사(D-2-1~4) 체류기간 2년 이내 단수, 연구과정(D-2-5)·교환학생(D-2-6)·방문학생(D-2-8) 1년 이내 단수.'],
         conditions_en=['Whether a visa or a confirmation of visa issuance is used follows the issuance table by university tier (excellent-certified, certified, general, visa-review-strengthened) and nationality. Nationals of Cuba, Syria, Macedonia and Kosovo receive a CVI only.',
                        'Issued: associate–doctorate (D-2-1~4) single entry up to 2 years; research (D-2-5), exchange (D-2-6) and visiting (D-2-8) students single entry up to 1 year.'],
         docs=d2_visa_docs(),
         notes_ko=['재외공관의 장은 필요한 경우 첨부서류를 일부 가감할 수 있습니다.', OFFICER_NOTE_KO], notes_en=['The head of the mission may add or waive some documents when needed.', OFFICER_NOTE_EN])
guidance('D-2', 'visa_issuance_confirmation', manual=VISA, section=D2_VISA_SECTION, anchor=D2_COMMON_ANCHOR, doc_page_window=4,
         summary_ko='유학(D-2) 사증발급인정서도 사증발급 일반의 공통서류(사증발급(인정)신청서 등)와 과정별 추가서류를 냅니다. 우수인증대학, 쿠바·시리아·마케도니아·코소보 국민, 중국·베트남·몽골·우즈베키스탄 국민 중 하위대학 어학연수·교환학생·방문학생 등이 대상이며, 입학예정대학 소재지 관할 출입국·외국인관서 또는 사증포털(유학생 담당자)로 신청합니다.',
         summary_en='A D-2 confirmation of visa issuance uses the same common documents (visa/CVI application form, etc.) and course-specific documents. It applies to excellent-certified universities, nationals of Cuba, Syria, Macedonia and Kosovo, and certain Chinese, Vietnamese, Mongolian and Uzbek students; file at the immigration office for the university\'s location or online via the visa portal (by the university\'s international-student officer).',
         docs=d2_visa_docs(),
         notes_ko=['재외공관의 장은 필요한 경우 첨부서류를 일부 가감할 수 있습니다.', OFFICER_NOTE_KO], notes_en=['The head of the mission may add or waive some documents when needed.', OFFICER_NOTE_EN])
guidance('D-2', 'electronic_visa', manual=VISA, completeness='SOURCE_ONLY', section='유학(D-2) — 전자비자', anchor='우수 인증대학 : 모든 유학과정(D-2-1~D-2-8)',
         summary_ko='전자비자는 우수 인증대학의 모든 유학과정(D-2-1~D-2-8)과 인증대 석사(D-2-3)·박사(D-2-4) 입학생이 대상이며(쿠바·시리아·마케도니아·코소보 국적 제외), 사증포털(www.visa.go.kr)로 신청하고 사증발급 일반 사항을 준용합니다.',
         summary_en='E-visas are available for all courses (D-2-1~D-2-8) at excellent-certified universities and for master\'s (D-2-3) and doctoral (D-2-4) entrants at certified universities (excluding nationals of Cuba, Syria, Macedonia and Kosovo); apply via the visa portal (www.visa.go.kr) under the general visa rules.')

guidance('D-2', 'status_change', section='유학(D-2) 체류자격 변경허가 — 다. 제출서류', anchor='유학(D-2) 체류자격 변경허가',
         summary_ko='외국인등록 후 합법 체류 중인 장기체류자는 유학(D-2)으로 변경할 수 있으나 기술연수(D-3), 계절근로(E-8), 비전문취업(E-9), 선원취업(E-10) 등은 제한되고, 단기체류자(B·C 계열)는 원칙적으로 제한됩니다. 신청서·여권 및 사본·사진·수수료에 교육기관 사업자등록증 사본, 표준입학허가서, 재정능력 입증서류 등을 냅니다.',
         summary_en='Registered long-term residents may change to D-2, but D-3, E-8, E-9, E-10 and certain G-1 holders are restricted, and short-term (B/C) holders are restricted in principle. Submit the form, passport and copy, photo and fee with the school\'s business registration copy, standard admission certificate and proof of finances.',
         conditions_ko=['단기체류자는 체류기간 만료일 내 진학 예정 과정의 개강이 예정되어 있는 등 매뉴얼의 일람표에 해당하는 예외에만 변경할 수 있습니다.', '재정능력 입증서류는 국내·외 은행 잔고증명서(신청인·부모·부모 사망 시 형제자매 명의)로, 신청일 기준 30일 이내 발급되어야 하며 체류허가기간 동안 유지해야 합니다.', '비자심사강화대학 입학·진학 예정자로 장관 고시국가 및 중점관리국가 국민은 한국어(또는 영어트랙의 영어) 능력 요건이 적용됩니다.'],
         conditions_en=['Short-term holders may change only in the exceptions listed in the manual table (e.g. the course starts before their stay expires).', 'Financial proof is a Korean or foreign bank balance certificate (applicant, parents, or siblings if both parents died) issued within 30 days and maintained during the stay.', 'Nationals of designated and priority-managed countries entering visa-review-strengthened universities must meet Korean (or, for English tracks, English) requirements.'],
         docs=[item('app_form', anchor='신청서, 여권 및 사본 1부, 표준규격사진 1매, 수수료'),
               item('passport_and_copy', anchor='신청서, 여권 및 사본 1부, 표준규격사진 1매, 수수료'),
               item('photo', anchor='신청서, 여권 및 사본 1부, 표준규격사진 1매, 수수료'),
               item('fee', anchor='GKS 장학증서 소지자는 수수료 면제', does_not_apply_when_ko='GKS 장학증서 소지자는 수수료 면제', does_not_apply_when_en='Waived for GKS scholarship-certificate holders'),
               item('d16_school_biz_reg', anchor='교육기관 사업자등록증(또는 고유번호증) 사본'),
               item('d16_standard_admission', anchor='❍ 표준입학허가서'),
               item('d16_prev_course_grades', 'CONDITIONAL_REQUIRED', anchor='이전 과정의 성적(출석/연수)증명서 제출(유학생정보시스템에서 확인되지 않는 경우)', applies_when_ko='어학연수(D-4)에서 유학(D-2)으로 변경하며 유학생정보시스템에서 확인되지 않는 경우', applies_when_en='Changing from D-4 to D-2 when it cannot be checked in FIMS'),
               item('d16_finance_ability', anchor='❍ 재정능력 입증서류'),
               item('family_relation', 'CONDITIONAL_REQUIRED', anchor='가족관계 입증서류(재정능력 입증서류로 부모의 잔고증명서 등을 제출한 경우)', applies_when_ko='재정능력 입증서류로 부모의 잔고증명서 등을 제출한 경우', applies_when_en='If a parent\'s bank-balance certificate is used as financial proof')],
         **NOTES)

guidance('D-2', 'activities_outside_status', completeness='PARTIALLY_STRUCTURED', section='유학(D-2) 체류자격외 활동 — 2. 과학기술연구 분야 학생연구원으로의 자격외 활동 특례', anchor='과학기술연구 분야 학생연구원으로의 자격외 활동 특례',
         summary_ko='석·박사과정 재학 또는 수료 학생이 소속대학 이외의 정부출연연구기관에서 학생연구원으로 고용계약을 맺고 근무하려면 체류자격외 활동허가를 받으며, 고용계약서·연구원의 사업자등록증 사본·수수료를 냅니다. 일반 기업·단체의 연구원으로의 자격외 활동은 금지되며 자격변경으로만 취업할 수 있습니다.',
         summary_en='Master\'s or doctoral students (or graduates of the coursework) who sign an employment contract as a student researcher at a government-funded research institute outside their university need permission for activities outside status: the employment contract, a copy of the institute\'s business registration and the fee. Working as a researcher at an ordinary company or organisation is prohibited; that requires a change of status.',
         conditions_ko=['소속 대학이 아닌 외부 연구소로의 파견, 지원 근무는 엄격히 금지됩니다.', '과학기술연합대학원대학교(UST), KAIST 소속 학생이 소속 대학의 연구프로젝트에 참여하여 수당을 받는 경우는 별도 허가가 필요 없습니다.', '소속대학 외부 기관에서 학업과 무관한 연구·인턴에 참여하는 경우 체류자격외활동허가(E-3)가 필요합니다.', '유학생(D-2) 배우자(F-3)의 체류자격외 활동은 동반(F-3) 지침에 따릅니다.'],
         conditions_en=['Dispatch or support work at an outside research institute is strictly prohibited.', 'UST and KAIST students paid for their own university\'s research projects need no separate permission.', 'Research or internships at outside bodies unrelated to studies need permission for activities outside status (E-3).', 'Activities of a D-2 student\'s spouse (F-3) follow the F-3 guidelines.'],
         docs=[item('employment_contract', anchor='(제출서류) 고용계약서, 연구원의 사업자등록증 사본, 수수료', applies_when_ko='정부출연연구기관 학생연구원', applies_when_en='Student researcher at a government-funded institute'),
               item('d16_research_institute_biz_reg', anchor='(제출서류) 고용계약서, 연구원의 사업자등록증 사본, 수수료', applies_when_ko='정부출연연구기관 학생연구원', applies_when_en='Student researcher at a government-funded institute'),
               item('fee', anchor='(제출서류) 고용계약서, 연구원의 사업자등록증 사본, 수수료')],
         **NOTES)

guidance('D-2', 'reentry', completeness='SOURCE_ONLY', section='유학(D-2) 재입국허가', anchor='등록을 필한 외국인유학생(D-2)이 1년 이후 2년 이내에 재입국하고자 하는 경우에는 신청에 의하여 복수재입국 허가하고',
         summary_ko='외국인등록을 한 유학생이 출국한 날부터 1년 이내(남은 체류기간이 1년보다 짧으면 그 범위 내)에 재입국하면 재입국허가가 면제됩니다. 1년 이후 2년 이내에 재입국하려면 신청에 따라 복수재입국허가(2년, 남은 체류기간이 2년 미만이면 그 범위 내)를 받으며 수수료를 냅니다.',
         summary_en='Registered students re-entering within one year of departure (or within the remaining stay if shorter) need no re-entry permit. To re-enter after one year but within two, apply for a multiple re-entry permit (2 years, or the remaining stay if shorter) and pay the fee.',
         conditions_ko=['입국규제 등의 사유로 재입국허가를 받아야 하는 유학생은 체류지 관할 청(사무소·출장소)에서 재입국허가를 받아야 합니다.'],
         conditions_en=['Students who must obtain a re-entry permit because of entry restrictions apply at the local office.'])

# ==========================================================================
# D-3 기술연수
# ==========================================================================
guidance('D-3', 'visa_issuance', manual=VISA, completeness='SOURCE_ONLY', section='기술연수(D-3) — 공관장 재량으로 발급할 수 있는 사증', anchor='기술연수에 대한 사증발급은 반드시 출입국ㆍ외국인청(사무소ㆍ출장소)장이',
         summary_ko='기술연수(D-3) 사증은 반드시 출입국·외국인청(사무소·출장소)장이 발급한 사증발급인정서를 제출받아 그 인정서의 내용에 따라 발급됩니다. 서류는 사증발급인정서 안내를 확인하세요.',
         summary_en='A D-3 visa is always issued on the confirmation of visa issuance from the immigration office, following its content. See the confirmation of visa issuance for documents.')
guidance('D-3', 'visa_issuance_confirmation', manual=VISA, section='기술연수(D-3) — 사증발급인정서 발급대상', anchor='기술연수에 대한 사증발급은 출입국ㆍ외국인청(사무소ㆍ출장소)장이', doc_page_window=3,
         summary_ko='기술연수(D-3) 사증발급인정서는 해외 현지법인 생산직 직원 등 연수허용 대상자에게 발급되며, 연수생 요건 입증서류, 연수계획서, 초청자의 신원보증서, 초청업체의 연수허용대상 업체 입증서류와 상시 근로자 수 입증서류, 연수환경 확인자료를 냅니다.',
         summary_en='A D-3 confirmation of visa issuance is for eligible trainees such as production staff of overseas subsidiaries. Submit proof that the trainee meets the requirements, the training plan, the inviter\'s guarantee, proof that the company is an eligible host and of its regular workforce, and material on the training environment.',
         docs=cvi_base_21('사증발급인정신청서 (별지 제21호 서식), 여권사본, 표준규격사진 1매') + [
             item('d16_d3_local_corp_reg', anchor='① 현지법인등록증(또는 설립인가서) 사본', notes_ko='주재국에 우리공관이 있는 경우 영사확인이 필요합니다.', notes_en='Consular confirmation is required where there is a Korean mission.'),
             item('d16_d3_local_employment', anchor='② 현지법인의 장이 발급한 피초청자 재직증명서 및 여권사본', notes_ko='주재국에 우리공관이 있는 경우 영사확인이 필요합니다.', notes_en='Consular confirmation is required where there is a Korean mission.'),
             item('d16_d3_korean_proof', anchor='③ 한국어능력입증자료'),
             item('d16_d3_training_plan', anchor='연수내용을 확인할 수 있는 연수계획서(별첨 3)'),
             item('d16_inviter_guarantee', anchor='4. 초청자의 신원보증서'),
             item('d16_d3_company_eligibility', anchor='초청업체가 연수허용대상 업체임을 입증할 수 있는 서류', role='inviter', substitution_allowed=True, alternatives_group='d3-company',
                  alternatives=[{'ko': '해외직접투자산업체: 해외직접투자신고(수리)서, 송금영수증 또는 송금사실확인서(현금투자) 또는 수출면장 확인(현물투자)', 'en': 'Overseas direct investor: investment report, remittance receipt (cash) or export declaration (in kind)'},
                                {'ko': '기술수출산업체: 기술수출계약서(국문) 사본(승인 대상이면 승인서)', 'en': 'Technology exporter: Korean copy of the technology export contract (and approval, if required)'},
                                {'ko': '플랜트수출 산업체: 플랜트수출승인서(변경승인서 포함)', 'en': 'Plant exporter: plant export approval (including amendments)'}]),
             item('d16_d3_workforce', anchor='연수허용인원 산정에 필요한 초청업체의 내국인 상시 근로자 수 입증서류'),
             item('d16_d3_environment', anchor='기타 자체 연수시설(공정)과 적정한 숙박시설 구비 등 연수환경을 확인할 수 있는 자료'),
         ], **NOTES)

guidance('D-3', 'extension', section='기술연수(D-3) 체류기간 연장허가', anchor='최초 6개월, 이 후 입국한 날부터 2년 범위 내에서 연장허가',
         summary_ko='기술연수(D-3)의 연수기간은 원칙적으로 입국일부터 6개월이며, 추가 연수가 필요하다고 인정되면 입국한 날부터 2년 범위 내에서 연장됩니다. 연수기간 연장의 필요성, 과거 이탈율, 범법사항 등을 확인하여 결정합니다.',
         summary_en='D-3 training lasts six months from entry in principle and may be extended within two years of entry if further training is needed. The decision considers the need, past absconding rates and violations.',
         period_ko='최초 6개월, 이후 입국한 날부터 2년 범위 내', period_en='First 6 months, then within 2 years of entry',
         docs=[item('app_form_34', anchor='① 신청서(별지34호 서식), 여권원본, 외국인등록증, 수수료'), item('passport_original', anchor='① 신청서(별지34호 서식), 여권원본, 외국인등록증, 수수료'),
               item('arc', anchor='① 신청서(별지34호 서식), 여권원본, 외국인등록증, 수수료'), item('fee', anchor='① 신청서(별지34호 서식), 여권원본, 외국인등록증, 수수료'),
               item('d16_d3_ext_reason', anchor='② 연수기간 연장신청 사유서(별도서식)'),
               item('d16_d3_biz_factory', anchor='③ 사업자등록증과 공장등록증(또는 공장등록증명서, 해당자만 제출)'),
               item('d16_d3_domestic_tax', anchor='④ 국내법인 납세증명서'),
               item('d16_d3_local_tax', anchor='⑤ 현지법인 납세사실 관련 증명 서류'),
               item('d16_d3_wage_proof', anchor='⑥ 연수생 임금 및 연수수당 지급 여부 확인서류'),
               item('guarantor_original_occupations', anchor='⑦ 신원보증서 원본'),
               item('d16_d3_insurance', anchor='⑧ 산업재해보상보험, 국민건강보험 가입증명서류 및 연수수당 등 체불에 대비한 보증보험 가입증명서류'),
               residence(anchor='⑨ 체류지 입증서류')],
         **NOTES)

guidance('D-3', 'registration', section='기술연수(D-3) 외국인등록 — 1. 신청서류', anchor='①신청서(별지 34호 서식), 여권, 컬러사진(3.5cm × 4.5cm) 1장, 수수료',
         summary_ko='기술연수(D-3) 외국인등록은 신청서·여권·컬러사진·수수료와 사업자등록증, 건강진단서, 산업재해보상보험 또는 보증보험 가입증명서류, 체류지 입증서류를 냅니다.',
         summary_en='D-3 registration needs the form, passport, colour photo and fee with the business registration, a health certificate, proof of industrial-accident or guarantee insurance and proof of residence.',
         docs=[item('app_form_34', anchor='①신청서(별지 34호 서식), 여권, 컬러사진(3.5cm × 4.5cm) 1장, 수수료'), item('passport', anchor='①신청서(별지 34호 서식), 여권, 컬러사진(3.5cm × 4.5cm) 1장, 수수료'),
               item('d16_color_photo', anchor='①신청서(별지 34호 서식), 여권, 컬러사진(3.5cm × 4.5cm) 1장, 수수료'), item('fee', anchor='①신청서(별지 34호 서식), 여권, 컬러사진(3.5cm × 4.5cm) 1장, 수수료'),
               item('business_reg', anchor='②사업자등록증 ③건강진단서', role='inviter'),
               item('d16_health_cert', anchor='②사업자등록증 ③건강진단서'),
               item('d16_d3_reg_insurance', anchor='④산업재해보상보험 또는 보증보험 가입증명서류'),
               residence(anchor='⑤ 체류지 입증서류')],
         **NOTES)

guidance('D-3', 'reentry', completeness='SOURCE_ONLY', section='기술연수(D-3) 재입국허가', anchor='출국한 날부터 1년 이내에 재입국하고자 하는 자의 경우 면제',
         summary_ko='기술연수(D-3)는 출국한 날부터 1년 이내에 재입국하면 재입국허가가 면제되며, 체류기간이 1년보다 적게 남아 있으면 체류기간 범위 내에서 면제됩니다.',
         summary_en='D-3 holders re-entering within one year of departure are exempt from a re-entry permit; if less than a year of stay remains, the exemption covers the remaining stay.')

# ==========================================================================
# D-4 일반연수
# ==========================================================================
D4_LANG_VISA_ANCHOR = '① 사증발급신청서 (별지 제17호 서식), 여권, 표준규격사진 1매, 수수료'


def d4_lang_tail(doc_anchor_prefix=''):
    return [
        item('d16_d4_school_biz_reg', anchor='② 교육기관 사업자등록증 사본 또는 고유번호증 사본'),
        item('d16_standard_admission', anchor='③ 표준입학허가서* (대학 총․학장 발행)'),
        item('d16_d4_enroll_or_edu', anchor='재학증명서 또는 최종학력 입증서류'),
        item('d16_d4_finance', anchor='재정 입증서류*', notes_ko='원본심사가 원칙이며 잔고증명서는 30일 이내 발급분만 인정됩니다.', notes_en='Originals are reviewed; bank balance certificates must be issued within 30 days.'),
        item('d16_family_cert', 'CONDITIONAL_REQUIRED', anchor='부․모 잔고증명서 제출 시 가족관계증명서 추가 제출 필요', applies_when_ko='부·모 잔고증명서를 제출하는 경우', applies_when_en='If a parent\'s bank-balance certificate is submitted'),
        item('d16_d4_lang_plan', anchor='⑥ 연수계획서(강의시간표, 강사구성표, 연수시설 등의 내용을 포함)'),
    ]


for _code in ('D-4-1', 'D-4-7'):
    guidance(_code, 'visa_issuance', manual=VISA, section='일반연수(D-4) — 공관장 재량으로 발급할 수 있는 사증 1. 어학연수(D-4-1, D-4-7)', anchor='어학연수(한국어연수: D-4-1, 외국어연수: D-4-7) 자격', doc_page_window=3,
             summary_ko='어학연수(D-4-1 한국어, D-4-7 외국어) 사증은 유학(D-2) 사증발급 대상 대학 부설 어학원에서 연수하려는 고교 졸업 이상 학력자(D-4-7은 고등학교 이하 재학생 포함)가 거주국 또는 최종학교 소재지 관할 공관에 신청하며, 체류기간 6개월 이하 단수사증이 발급됩니다.',
             summary_en='Language-training visas (D-4-1 Korean, D-4-7 foreign language) are for high-school graduates (D-4-7 also school students) studying at a language institute attached to a D-2-eligible university; apply at the mission for your country of residence or last school. A single-entry visa of up to six months is issued.',
             conditions_ko=['쿠바·시리아·마케도니아·코소보 국민, 일반대학 또는 하위대학에 입학하는 몽골·베트남·우즈베키스탄·중국의 어학연수생은 사증발급인정서에 의해서만 사증이 발급됩니다.', '90일 이하 체류 어학연수생은 단기일반(C-3-1) 사증 발급 대상입니다.'],
             conditions_en=['Nationals of Cuba, Syria, Macedonia and Kosovo, and Mongolian, Vietnamese, Uzbek and Chinese language trainees entering general or lower-tier universities, receive a visa only through a confirmation of visa issuance.', 'Language trainees staying 90 days or less get a C-3-1 visa.'],
             docs=visa_base_17(D4_LANG_VISA_ANCHOR) + d4_lang_tail(),
             notes_ko=['재외공관의 장은 필요한 경우 첨부서류를 일부 가감할 수 있습니다.', OFFICER_NOTE_KO], notes_en=['The head of the mission may add or waive some documents when needed.', OFFICER_NOTE_EN])

guidance('D-4-1', 'visa_issuance_confirmation', manual=VISA, section='일반연수(D-4) — 사증발급인정서 발급대상 1. 어학연수(D-4-1) 자격', anchor='체류기간 6개월 이하 단수 일반연수(D-4) 사증발급인정서', doc_page_window=3,
         summary_ko='어학연수(D-4-1) 사증발급인정서는 시리아·마케도니아·코소보 국민과 일반대학·하위대학에 입학하는 몽골·베트남·우즈베키스탄·중국 어학연수생이 대상이며, 입학예정대학 소재지 관할 출입국·외국인관서 또는 사증포털(유학생담당자)로 신청합니다. 체류기간 6개월 이하 단수로 발급됩니다.',
         summary_en='A D-4-1 confirmation of visa issuance applies to nationals of Syria, Macedonia and Kosovo and to Mongolian, Vietnamese, Uzbek and Chinese trainees at general or lower-tier universities; file at the immigration office for the university or online via the visa portal (international-student officer). Issued single-entry for up to six months.',
         docs=[item('d16_cvi_app_21', anchor='① 사증발급인정신청서 (별지 제21호 서식), 여권, 표준규격사진 1매, 수수료'), item('passport', anchor='① 사증발급인정신청서 (별지 제21호 서식), 여권, 표준규격사진 1매, 수수료'),
               item('photo', anchor='① 사증발급인정신청서 (별지 제21호 서식), 여권, 표준규격사진 1매, 수수료'), item('fee', anchor='① 사증발급인정신청서 (별지 제21호 서식), 여권, 표준규격사진 1매, 수수료'),
               item('d16_d4_school_biz_reg', anchor='② 교육기관 사업자등록증 사본 또는 고유번호증 사본'),
               item('d16_standard_admission', anchor='③ 표준입학허가서* (대학 총․학장 발행)', notes_ko='유학생정보시스템(FIMS) 정보확인으로 제출에 갈음하고, 국립국제교육원 초청 장학생은 교육원장이 발급한 초청장으로 대체합니다.', notes_en='Replaced by a FIMS check; NIIED scholars submit the NIIED invitation instead.'),
               item('d16_d4_enroll_or_edu', anchor='④ 재학증명서 또는 최종학력 입증서류'),
               item('d16_d4_finance', anchor='⑤ 재정 입증서류', notes_ko='잔고증명서는 30일 이내 발급분만 인정되며, 베트남은 지급유보방식의 별도 유학경비 잔고증명서를 냅니다.', notes_en='Bank balance certificates must be issued within 30 days; Vietnamese applicants submit a separate blocked-account study-fund certificate.'),
               item('d16_family_cert', 'CONDITIONAL_REQUIRED', anchor='부․모 잔고증명서 제출 시 가족관계증명서 추가 제출 필요', applies_when_ko='부·모 잔고증명서를 제출하는 경우', applies_when_en='If a parent\'s bank-balance certificate is submitted'),
               item('d16_d4_lang_plan', anchor='⑥ 연수계획서(강의시간표, 강사구성표, 연수시설 등의 내용을 포함)')],
         notes_ko=['재외공관의 장은 필요한 경우 첨부서류를 일부 가감할 수 있습니다.', OFFICER_NOTE_KO], notes_en=['The head of the mission may add or waive some documents when needed.', OFFICER_NOTE_EN])

guidance('D-4-2K', 'visa_issuance_confirmation', manual=VISA, section='일반연수(D-4) — 2. 기업 맞춤형 인턴십(K-Trainee, D-4-2K) 자격 사증발급인정서 발급', anchor='기업 맞춤형 인턴십(K-Trainee, D-4-2K) 자격 사증발급인정서 발급', doc_page_window=3,
         summary_ko='기업 맞춤형 인턴십(D-4-2K)은 베트남·중국·태국·일본·인도·인도네시아·말레이시아·싱가포르·필리핀 9개국에 진출한 국내 기업이 초청하며, 공통서류에 더해 맞춤형 우수대학생 또는 현지법인 전문인력 유형별 추가서류를 냅니다. 초청기업 소재지 관할 출입국·외국인관서에 신청하고 체류기간 6개월 이내 단수로 발급됩니다.',
         summary_en='K-Trainee (D-4-2K) invitations come from Korean companies operating in nine countries (Vietnam, China, Thailand, Japan, India, Indonesia, Malaysia, Singapore, the Philippines). Submit the common documents plus those for your type (customised university student or local-subsidiary professional) at the office for the inviting company; issued single-entry for up to six months.',
         conditions_ko=['초청인원은 사업장별 상시 근로자 수의 10% 이내이며 동시 인턴십 인원은 100명을 초과할 수 없습니다.', '맞춤형 우수대학생: 산학협력 체결 대학 학사과정 3학년 이상(석·박사 포함), 토픽 2급 이상, 29세 이하.', '현지법인 전문인력: E-7-1·E-7-2 77개 직종 분야 국내 본사 인턴십 참여자(생산직 제외).'],
         conditions_en=['Up to 10% of the workplace\'s regular workers, never more than 100 interns at once.', 'Customised students: 3rd year or above (incl. graduate) at a partner university, TOPIK 2+, age 29 or under.', 'Local-subsidiary professionals: head-office internships in the 77 E-7-1/E-7-2 occupations (production staff excluded).'],
         docs=[item('d16_cvi_app', anchor='① 사증발급인정신청서'),
               item('passport_copy', anchor='② 여권사본 및 표준규격 사진 1매'), item('photo', anchor='② 여권사본 및 표준규격 사진 1매'),
               item('d16_2k_relation', anchor='③ 해외법인·국내 초청기업 관계 입증서류'),
               item('d16_2k_tax_workforce', anchor='④ 납세증명서(국세, 지방세), 상시 근로자 수 입증 서류'),
               item('tb_cert', 'CONDITIONAL_REQUIRED', anchor='⑤ 결핵진단서(해당자)', applies_when_ko='해당자', applies_when_en='If applicable'),
               item('d16_2k_plan', anchor='⑥ 인턴·연수 활동 계획서'),
               item('d16_2k_mou', 'CONDITIONAL_REQUIRED', anchor='① 현지 대학과의 산학협력 체결 입증서류(MOU 등)', applies_when_ko='맞춤형 우수대학생', applies_when_en='Customised university student'),
               item('d16_2k_support', 'CONDITIONAL_REQUIRED', anchor='② 기업이 맞춤형 인재로 양성·후원하는 입증서류', applies_when_ko='맞춤형 우수대학생 (산학협력 체결서에 양성·후원 내용이 포함되면 생략 가능)', applies_when_en='Customised university student (may be omitted if the agreement covers the sponsorship)'),
               item('d16_2k_enroll_korean', 'CONDITIONAL_REQUIRED', anchor='③ 재학증명서 및 한국어 능력 입증 서류', applies_when_ko='맞춤형 우수대학생', applies_when_en='Customised university student'),
               item('d16_2k_employment', 'CONDITIONAL_REQUIRED', anchor='① (필수) 재직증명서', applies_when_ko='현지법인 전문인력', applies_when_en='Local-subsidiary professional')],
         **NOTES)

D43_CVI_COMMON = '① 사증발급인정신청서 (별지 제21호 서식), 여권사본, 표준규격사진 1매'
guidance('D-4-3', 'visa_issuance_confirmation', manual=VISA, section='일반연수(D-4) — 3. 고등학교 이하 교육기관 유학생에 대한 일반연수(D-4-3) 자격 사증발급인정서 발급', anchor='고등학교 이하 교육기관 유학생에 대한 일반연수(D-4-3) 자격 사증발급인정서 발급', doc_page_window=3,
         summary_ko='고등학교 이하 교육기관 유학생(D-4-3) 사증발급인정서는 21개 불법체류 다발국가 국민 중 자비부담 유학생과 정부기관·지방자치단체 초청 의무(무상)교육기관 유학생이 대상이며, 입학예정 학교 소재지 관할 출입국·외국인관서에 신청합니다. 공통서류에 자비부담 또는 정부·지자체 초청 유형별 추가서류를 냅니다.',
         summary_en='The D-4-3 confirmation of visa issuance (K-12 students) applies to self-funded students from the 21 designated countries and to students invited by government bodies or local governments to free compulsory schools; file at the office for the school. Submit the common documents plus those for your type.',
         conditions_ko=['자비부담 유학생은 학비 전액을 자비로 납부하고 국내 체류 비용 부담능력이 있으며 지정된 후견인이 있어야 합니다. 고등학교 전·입학자로 해당학교 기숙사 입소자는 후견인이 면제됩니다(학교장 명의 입소확인서 필요).', '체류기간 1년 이내 단수로 발급됩니다.'],
         conditions_en=['Self-funded students must have paid all tuition themselves, be able to cover living costs and have a designated guardian; high-school entrants living in the school dormitory are exempt from the guardian requirement (principal\'s dormitory confirmation).', 'Issued single-entry for up to one year.'],
         docs=[item('d16_cvi_app_21', anchor=D43_CVI_COMMON), item('passport_copy', anchor=D43_CVI_COMMON), item('photo', anchor=D43_CVI_COMMON),
               item('d16_school_biz_reg', anchor='② 교육기관 사업자등록증(또는 고유번호증) 사본'),
               item('d16_d43_admission', anchor='③ 입학허가서(학교장 발행, 붙임 1 서식)'),
               item('d16_d43_final_edu', anchor='④ 최종 학력 입증서류(졸업증명서 또는 재학증명서 등)'),
               item('tuition_history', 'CONDITIONAL_REQUIRED', anchor='⑤ 학비 납부 내역서(수업료･기숙사비･입학금 등 유학관련 비용 일체)', applies_when_ko='자비부담 외국인유학생', applies_when_en='Self-funded student'),
               item('living_cost_proof', 'CONDITIONAL_REQUIRED', anchor='3개월 이상 계속 예치된 기준 이상 금액의 잔고증명서 또는 입출금내역서 등', applies_when_ko='자비부담 외국인유학생', applies_when_en='Self-funded student'),
               item('d16_guardian_guarantee', 'CONDITIONAL_REQUIRED', anchor='⑦ 후견 보증서* (붙임 2 서식)', applies_when_ko='자비부담 외국인유학생 (부모가 후견인이 되는 경우에도 작성)', applies_when_en='Self-funded student (also when a parent is the guardian)'),
               item('dorm_admission_cert', 'ALTERNATIVE_DOCUMENT', anchor='후견인 면제 대상자는 학교장 명의 ‘기숙사 입소확인서’ 제출', applies_when_ko='후견인 면제 대상자', applies_when_en='Guardian-exempt students'),
               item('d16_guardian_finance', 'CONDITIONAL_REQUIRED', anchor='⑧ 후견인 재정능력 입증서류 (불법체류 다발국가 국민에 한함)', applies_when_ko='불법체류 다발국가 국민', applies_when_en='Nationals of the designated high-overstay countries'),
               item('d16_guardian_relation', 'CONDITIONAL_REQUIRED', anchor='후견인과의 관계 증명서류 (친족관계가 아닌 경우 관계 소', applies_when_ko='자비부담 외국인유학생', applies_when_en='Self-funded student'),
               item('family_relation', 'CONDITIONAL_REQUIRED', anchor='⑨ 가족관계 입증서류 (불법체류 다발국가 국민에 한함)', applies_when_ko='불법체류 다발국가 국민 (번역본 첨부 원칙)', applies_when_en='Nationals of the designated high-overstay countries (translation attached)'),
               item('d16_d43_scholarship', 'CONDITIONAL_REQUIRED', anchor='⑤ 전액 장학생 입증서류(정부기관 및 지방자치단체의 공문)', applies_when_ko='정부기관 또는 지방자치단체 초청 외국인유학생', applies_when_en='Student invited by a government body or local government'),
               item('d16_d43_purpose', 'CONDITIONAL_REQUIRED', anchor='⑥ 초청 목적 입증서류(교육 계획(안), 진로 지도(안) 등)', applies_when_ko='정부기관 또는 지방자치단체 초청 외국인유학생', applies_when_en='Student invited by a government body or local government')],
         **NOTES)

guidance('D-4-5', 'visa_issuance_confirmation', manual=VISA, section='일반연수(D-4) — 4. 한식조리연수생(D-4-5)에 대한 사증발급인정서 발급', anchor='한식조리연수생(D-4-5)에 대한 사증발급인정서 발급', doc_page_window=3,
         summary_ko='한식조리연수(D-4-5) 사증발급인정서는 수라학교 연수가 확정되어 농식품부(한식진흥원) 추천을 받은 18세 이상 고졸 이상 학력자가 대상이며, 연수기관 대표가 초청자로 신청합니다. 체류기간 6개월 이하 단수로 발급됩니다.',
         summary_en='The D-4-5 confirmation of visa issuance (Korean-cuisine trainees) is for people aged 18+ with at least a high-school education, confirmed for a Sura School course and recommended by the Ministry of Agriculture (Korean Food Promotion Institute); the head of the institution applies as inviter. Issued single-entry for up to six months.',
         conditions_ko=['한국어 기초능력(TOPIK 1급 상당)이 필요하며, 동일 언어권 대상 프로그램 참가자나 수라학교 한국어교육 참여 예정자는 면제신청서로 면제될 수 있습니다.', '재정 부담 능력: 등록금 외 통장잔고증명 USD 10,000 이상, 1개월 이상 예치.'],
         conditions_en=['Basic Korean (TOPIK 1 equivalent) is required; participants in single-language programmes or the school\'s Korean course may be exempted with an exemption request.', 'Finances: bank balance of USD 10,000+ besides tuition, held for at least one month.'],
         docs=[item('d16_cvi_app', anchor='(공통서류) 사증발급인정신청서, 반명함판 사진(3.5×4.5㎝) 1장, 여권사본'),
               item('d16_photo_half', anchor='(공통서류) 사증발급인정신청서, 반명함판 사진(3.5×4.5㎝) 1장, 여권사본'),
               item('passport_copy', anchor='(공통서류) 사증발급인정신청서, 반명함판 사진(3.5×4.5㎝) 1장, 여권사본'),
               item('d16_d45_edu_admission', anchor='최종학력 입증서류 및 수라학교 입학허가서(연수기관장 발행)'),
               item('d16_d45_stay_cost', anchor='국내 체제비 입증서류(잔고증명, 부모 재정능력 등)'),
               item('d16_d45_fee_paid', anchor='- 교육비 납입증명서'),
               item('d16_d45_korean', anchor='한국어 기초능력 입증서류(토픽 1급 상당) 또는 면제신청서류'),
               item('d16_d45_recommendation', anchor='한식 연수생 추천서(붙임2 서식)'),
               item('d16_d45_inst_docs', anchor='연수기관 설립 관련 서류(사업자등록증 또는 고유번호증 사본, 법인등기부등본 등)'),
               item('d16_d45_designation', anchor='수라학교 지정증(붙임1 서식)'),
               item('d16_d45_plan', anchor='기관 연수계획서(연수일정*포함)'),
               item('d16_dorm_proof', anchor='- 기숙사 보유 입증서류*'),
               item('guarantor', 'MAY_BE_REQUESTED_BY_OFFICER', anchor='신원보증서 (법무부장관이 특히 필요하다고 인정하는 경우에 한함)', applies_when_ko='법무부장관이 특히 필요하다고 인정하는 경우', applies_when_en='If the Minister of Justice deems it necessary'),
               item('proxy_docs', 'CONDITIONAL_REQUIRED', anchor='초청기관 대표가 아닌 직원이 대리 신청 시 위임장, 재직증명서, 신분증 사본 등 제출 요청', applies_when_ko='초청기관 대표가 아닌 직원이 대리 신청하는 경우', applies_when_en='If an employee rather than the head files on the institution\'s behalf')],
         **NOTES)


def d46_docs():
    return [
        item('d16_d46_edu_admission', anchor='최종학력 입증서류(공증) 및 입학허가서(교육기관장 발행)'),
        item('d16_d46_finance', anchor='재정능력 입증서류(잔고증명, 부모 재정능력 등)'),
        item('d16_d46_fee_paid', anchor='등록금 또는 교육비 납입증명서'),
        item('d16_d46_korean', anchor='한국어 능력 입증서류(토픽 1급이상, 세종학당 초급1 과정 이상 수료증)', notes_ko='2026.1.1.부터 토픽 2급 이상, 세종학당 초급2 과정 이상으로 상향', notes_en='From 2026-01-01: TOPIK 2+ or King Sejong Institute Beginner 2+'),
        item('d16_d46_inst_docs', anchor='교육기관설립관련 서류'),
        item('d16_d46_corp_register', anchor='교육기관 법인등기부등본(등기사항전부증명서, 법원발행)'),
        item('d16_d46_biz_reg', anchor='사업자등록증 또는 고유번호증 사본'),
        item('d16_d46_plan', anchor='연수계획서(강의시간표, 강사구성표, 연수시설, 학비 등의 내용 포함)'),
        item('d16_dorm_proof', anchor='기숙사 보유 입증서류'),
        item('d16_d46_academy_reg', 'CONDITIONAL_REQUIRED', anchor='학원설립․운영 등록증(교육청 발행, 직업기술과정)', applies_when_ko='직업기술과정 학원', applies_when_en='Vocational academies'),
        item('d16_d46_training_corp', 'CONDITIONAL_REQUIRED', anchor='직업능력개발훈련법인 설립허가서(직업능력개발 훈련법인 입증 등 관련입증서류, 직업능력개발훈련법인에 한함)', applies_when_ko='직업능력개발훈련법인', applies_when_en='Vocational-training corporations'),
        item('d16_d46_listed_company', 'CONDITIONAL_REQUIRED', anchor='상장기업입증서류 및 교육기관이 해당 기업과 연계 또는', applies_when_ko='국내상장기업 연계 또는 설립기관', applies_when_en='Institutions linked to or set up by a listed company'),
        item('d16_d46_univ_affiliated', 'CONDITIONAL_REQUIRED', anchor='대학부설 시설 전문교육기관임을 입증하는 서류(대학부설 교육기관에 한함)', applies_when_ko='대학부설 교육기관', applies_when_en='University-affiliated institutions'),
        item('d16_d46_foreign_branch', 'CONDITIONAL_REQUIRED', anchor='해외 교육기관의 국내지사 또는 독점 운영계약자임을 입증하는 서류(해외교육기관 국내지사에 한함)', applies_when_ko='해외교육기관 국내지사', applies_when_en='Korean branches of foreign institutions'),
        item('d16_d46_credit_recognition', 'CONDITIONAL_REQUIRED', anchor='학습과정 평가 인정서(교육부장관 발행, 학점인정 입증) 해당자에 한함', applies_when_ko='해당자에 한함', applies_when_en='If applicable'),
        item('d16_d46_domestic_students', anchor='교육기관의 국민 교육생 유치 실적 증빙 서류'),
        item('d16_d46_operation', anchor='기타 교육기관 정상운영 및 교육과정 정상 운영 능력 입증 서류'),
    ]


D46_COND_KO = ['연수생은 만 18세 이상 30세 이하의 고등학교 이상 학력소지자로 연수기간 국내 체재비를 입증하고 한국어능력(TOPIK 1급 이상 또는 세종학당 초급1 이상, 2026.1.1.부터 TOPIK 2급 등으로 상향)을 갖춰야 합니다.', '연수기관은 설립 1년 이상, 학비 반기 400만원 이상, 주중 4일·주 15시간 이상 주간 운영, 기숙사와 자체 교육장 보유 등 요건을 모두 충족해야 합니다.']
D46_COND_EN = ['Trainees must be 18–30, hold at least a high-school education, prove living costs and have Korean ability (TOPIK 1+ or King Sejong Beginner 1+, raised to TOPIK 2 etc. from 2026-01-01).', 'Institutions must meet all requirements, including 1+ year of operation, tuition of KRW 4 million+ per half-year, daytime classes 4+ days and 15+ hours a week, and their own dormitory and classrooms.']
guidance('D-4-6', 'visa_issuance_confirmation', manual=VISA, section='일반연수(D-4) — 5. 우수사설 교육기관 외국인 연수(D-4-6)', anchor='사증발급인정서로만 사증발급이 가능하며, 공관장 재량으로 사증 발급 불가', doc_page_window=4,
         summary_ko='우수사설 교육기관 외국인 연수(D-4-6)는 사증발급인정서로만 사증이 발급되며(공관장 재량 발급 불가) 연수기관 소재지 관할 출입국·외국인관서장이 체류기간 6개월 이하 단수로 발급합니다. 연수생 준비서류와 연수기관 준비서류를 함께 냅니다.',
         summary_en='D-4-6 (training at an excellent private institution) is issued only through a confirmation of visa issuance (no mission-discretion visa), by the office for the institution, single-entry for up to six months. Submit the trainee\'s and the institution\'s documents.',
         conditions_ko=D46_COND_KO, conditions_en=D46_COND_EN, docs=d46_docs(), **NOTES)

# ---- D-4 stay: 체류자격 변경
D4_LANG_CHANGE_ANCHOR = '① 신청서, 여권, 외국인등록증 (소지자), 사진 1매, 수수료'
for _code in ('D-4-1', 'D-4-7'):
    guidance(_code, 'status_change', section='일반연수(D-4) 체류자격 변경허가 — 1. 어학연수(D-4-1, D-4-7)', anchor='어학연수(한국어연수: D-4-1, 외국어연수: D-4-7) 체류자격 변경허가',
             summary_ko='외국인등록 후 합법 체류 중인 장기체류자는 어학연수(D-4-1, D-4-7)로 변경할 수 있고, 단기체류자(B·C 계열)는 원칙적으로 제한됩니다. 고등학교 졸업 이상 학력자만 가능하며(D-4-7은 고등학교 이하 재학생도 가능), 학력입증 절차는 유학(D-2) 비자 신청 시와 같습니다.',
             summary_en='Registered long-term residents may change to language training (D-4-1, D-4-7); short-term (B/C) holders are restricted in principle. Only high-school graduates qualify (D-4-7 also school students), and education is proven as for a D-2 visa.',
             conditions_ko=['기술연수(D-3), 비전문취업(E-9), 선원취업(E-10), 인도적체류허가자(G-1-6)를 제외한 기타(G-1) 등록외국인은 자격변경이 제한됩니다.'],
             conditions_en=['Registered D-3, E-9, E-10 and G-1 holders (other than G-1-6) are restricted from changing status.'],
             docs=[item('app_form', anchor=D4_LANG_CHANGE_ANCHOR), item('passport', anchor=D4_LANG_CHANGE_ANCHOR),
                   item('arc', 'CONDITIONAL_REQUIRED', anchor=D4_LANG_CHANGE_ANCHOR, applies_when_ko='소지자', applies_when_en='If you hold one'),
                   item('photo', anchor=D4_LANG_CHANGE_ANCHOR), item('fee', anchor=D4_LANG_CHANGE_ANCHOR),
                   item('d16_d4_school_biz_reg', anchor='② 교육기관 사업자등록증 또는 고유번호증 사본'),
                   item('d16_standard_admission', anchor='③ 표준입학허가서* (대학 총․학장 발행)', notes_ko='유학생정보시스템(FIMS) 정보확인으로 제출에 갈음하고, 국립국제교육원 초청 장학생은 교육원장이 발급한 초청장으로 대체합니다.', notes_en='Replaced by a FIMS check; NIIED scholars submit the NIIED invitation instead.'),
                   item('d16_finance_ability', anchor='④ 재정능력입증서류*'),
                   item('d16_family_cert', 'CONDITIONAL_REQUIRED', anchor='부․모 잔고증명서 제출 시 가족관계증명서 추가 제출 필요', applies_when_ko='부·모 잔고증명서를 제출하는 경우', applies_when_en='If a parent\'s bank-balance certificate is submitted'),
                   item('d16_d4_enroll_or_edu', anchor='⑤ 재학증명서 또는 최종학력입증서류'),
                   item('d16_d4_lang_plan', anchor='⑥ 연수계획서(강의시간표, 강사구성표, 연수시설 등의 내용을 포함)'),
                   item('d16_need_for_language_training', 'MAY_BE_REQUESTED_BY_OFFICER', anchor='어학연수 필요성 소명자료를 추가로 요구할', applies_when_ko='법무부장관 고시국가 국민으로 연령 등을 고려할 때 어학연수 필요성이 적다고 판단되는 경우', applies_when_en='Nationals of designated countries when, given age etc., the need for language training seems low')],
             **NOTES)

guidance('D-4-2', 'status_change', section='일반연수(D-4) 체류자격 변경허가 — 2. 졸업생에 대한 일반연수(D-4-2) 자격 등으로의 변경', anchor='졸업생에 대한 일반연수(D-4-2) 자격 등으로의 변경',
         summary_ko='국내대학(전문대 포함) 졸업자로서 취업한 해외 소재 내국인 투자기업의 국내 모기업·외국지사, 해외 소재 외국기업의 국내 본사·지사·계열사, 국제기구·주한공관(상공회의소) 등에서 연수가 필요하다고 인정되면 일반연수(D-4-2) 등으로 변경할 수 있습니다.',
         summary_en='Graduates of Korean universities (including colleges) may change to D-4-2 when training is needed at the Korean parent or foreign branch of the overseas Korean-invested company they joined, the Korean head office/branch/affiliate of the overseas foreign company they joined, or an international organisation or foreign mission (chamber of commerce).',
         docs=[item('app_form', anchor='① 신청서, 여권, 외국인등록증, 사진 1매, 수수료'), item('passport', anchor='① 신청서, 여권, 외국인등록증, 사진 1매, 수수료'),
               item('arc', anchor='① 신청서, 여권, 외국인등록증, 사진 1매, 수수료'), item('photo', anchor='① 신청서, 여권, 외국인등록증, 사진 1매, 수수료'), item('fee', anchor='① 신청서, 여권, 외국인등록증, 사진 1매, 수수료'),
               item('d16_d42_necessity', anchor='② 연수의 필요성을 입증하는 서류 (취업확인서, 연수계획서 등)'),
               item('d16_d42_company', anchor='③ 외국인 투자기업 또는 외국에 투자한 국내기업임을 입증하는 서류')],
         **NOTES)

D43_CHANGE_COMMON = '① 신청서 (별지 제34호 서식), 여권, 외국인등록증(소지자), 표준규격사진 1매, 수수료'
guidance('D-4-3', 'status_change', section='일반연수(D-4) 체류자격 변경허가 — 3. 고등학교 이하 외국인유학생(D-4-3) 자격으로 변경', anchor='고등학교 이하 외국인유학생(D-4-3) 자격으로 변경', doc_page_window=3,
         summary_ko='국내에 합법적으로 외국인등록을 하고 장기체류 중인 사람으로 고등학교 이하 교육기관의 입학허가를 받은 자비부담 유학생은 D-4-3으로 변경할 수 있습니다(단기체류자격 및 G-1 소지자는 불가). 공통서류에 학비 납부 내역, 체류비용 부담능력, 후견 관련 서류 등을 냅니다.',
         summary_en='Registered long-term residents admitted to a K-12 school as self-funded students may change to D-4-3 (not short-term or G-1 holders). Submit the common documents plus tuition payment history, proof of living costs and guardianship documents.',
         conditions_ko=['학비 전액 자비 납부, 국내 체류 비용 부담능력, 지정된 후견인이 필요합니다. 고등학교 전·입학자로 해당학교 기숙사 입소자는 후견인이 면제됩니다(학교장 명의 입소확인서 필요).', '의무(무상) 교육기관은 제외됩니다.'],
         conditions_en=['Full self-paid tuition, ability to cover living costs and a designated guardian are required; high-school entrants in the school dormitory are exempt from the guardian requirement (principal\'s confirmation).', 'Free compulsory schools are excluded.'],
         docs=[item('app_form_34', anchor=D43_CHANGE_COMMON), item('passport', anchor=D43_CHANGE_COMMON),
               item('arc', 'CONDITIONAL_REQUIRED', anchor=D43_CHANGE_COMMON, applies_when_ko='소지자', applies_when_en='If you hold one'),
               item('photo', anchor=D43_CHANGE_COMMON), item('fee', anchor=D43_CHANGE_COMMON),
               item('d16_school_biz_reg', anchor='② 교육기관 사업자등록증(또는 고유번호증) 사본'),
               item('d16_d43_admission_enroll', anchor='③ 입학허가서(학교장 발행, 붙임 1 서식)* 및 재학증명서(해당자)', notes_ko='D-4-3 자격변경자는 재학여부와 관계없이 입학허가서를 내야 합니다.', notes_en='The admission certificate is required whether or not you are already enrolled.'),
               item('d16_d43_final_edu', anchor='④ 최종 학력 입증서류(졸업증명서 또는 재학증명서 등)'),
               item('tuition_history', anchor='⑤ 학비 납부 내역서(수업료･기숙사비･입학금 등 유학관련 비용 일체)'),
               item('living_cost_proof', anchor='3개월 이상 계속 예치된 기준 이상 금액의 잔고증명서 또는 입출금내역서 등'),
               item('d16_guardian_guarantee', anchor='⑦ 후견 보증서* (붙임 2 서식)'),
               item('dorm_admission_cert', 'ALTERNATIVE_DOCUMENT', anchor='후견인 면제 대상자는 학교장 명의 ‘기숙사 입소확인서’ 제출', applies_when_ko='후견인 면제 대상자', applies_when_en='Guardian-exempt students'),
               item('d16_guardian_relation', anchor='⑧ 후견인과의 관계 증명서류(친족관계가 아닌 경우 관계 소명'),
               item('d16_guardian_finance', 'CONDITIONAL_REQUIRED', anchor='⑨ 후견인 재정능력 입증서류 (불법체류 다발국가 국민에 한함)', applies_when_ko='불법체류 다발국가 국민', applies_when_en='Nationals of the designated high-overstay countries'),
               item('family_relation', 'CONDITIONAL_REQUIRED', anchor='⑩ 가족관계 입증서류 (불법체류 다발국가 국민에 한함)', applies_when_ko='불법체류 다발국가 국민 (번역본 첨부 원칙)', applies_when_en='Nationals of the designated high-overstay countries (translation attached)'),
               residence(anchor='⑪ 체류지 입증서류')],
         notes_ko=['출입국·외국인청(사무소·출장소)장은 첨부서류의 일부를 가감할 수 있습니다.', OFFICER_NOTE_KO], notes_en=['The immigration office may add or waive some documents.', OFFICER_NOTE_EN])

guidance('D-4-5', 'status_change', state='GENERALLY_NOT_PERMITTED', completeness='SOURCE_ONLY', section='일반연수(D-4) 체류자격 변경허가 — 4. 한식조리연수(D-4-5)', anchor='다른 체류자격 소지자의 한식조리연수(D-4-5) 자격으로의 체류자격 변경 불가',
         summary_ko='다른 체류자격 소지자는 한식조리연수(D-4-5)로 체류자격을 변경할 수 없습니다. 국내 체류 외국인이 연수생으로 선발되면 사증발급인정서를 받아 출국한 뒤 재외공관에서 사증을 받아 재입국합니다.',
         summary_en='Holders of other statuses cannot change to D-4-5. A foreign resident selected as a trainee obtains a confirmation of visa issuance, leaves, gets the visa at a Korean mission and re-enters.')

guidance('D-4-6', 'status_change', section='일반연수(D-4) 체류자격 변경허가 — 5. 우수사설 교육기관 외국인 연수(D-4-6)', anchor='국내 합법적으로 체류하는 등록외국인으로 연수생 기준에 해당하는 자', doc_page_window=4,
         summary_ko='국내에 합법적으로 체류하는 등록외국인으로 연수생 기준에 해당하면 우수사설 교육기관 외국인 연수(D-4-6)로 변경할 수 있습니다. B-2·C-3 소지자와 기술연수(D-3), 비전문취업(E-9), 선원취업(E-10), 기타(G-1)는 변경이 제한됩니다.',
         summary_en='Registered foreign residents who meet the trainee criteria may change to D-4-6. B-2 and C-3 holders and D-3, E-9, E-10 and G-1 holders are restricted.',
         conditions_ko=D46_COND_KO, conditions_en=D46_COND_EN, docs=d46_docs(), **NOTES)

# ---- D-4 stay: 체류기간 연장 (D-4-7 shares the D-4-1 section; D-4-5, D-4-6 have their own)
D41_EXT_ANCHOR = '① 신청서 (별지 34호 서식), 여권, 외국인등록증, 수수료'
guidance('D-4-7', 'extension', section='일반연수(D-4) — 1. 어학연수생(D-4-1, D-4-7)에 대한 체류기간 연장허가', anchor='어학연수생(D-4-1, D-4-7)에 대한 체류기간 연장허가',
         summary_ko='어학연수생(D-4-1, D-4-7)은 재학 입증서류, 학업 수행 입증서류(성적·출석), 국내 본인 계좌 재정입증, 모집요강 또는 연수계획서, 체류지 입증서류로 연장합니다. 가사휴학은 연장이 제한되고, 학교 변경은 원칙적으로 출국 후 재입국이지만 어학원 폐쇄 등 귀책 없는 사유나 TOPIK 3급 이상이면 예외입니다.',
         summary_en='Language trainees (D-4-1/7) extend with proof of enrollment, academic progress (grades/attendance), financial proof from their own Korean account, the programme guide or plan and proof of residence. Leave for personal reasons restricts extension; changing school normally requires re-entry unless the institute closed or you hold TOPIK 3+.',
         docs=[item('app_form_34', anchor=D41_EXT_ANCHOR), item('passport', anchor=D41_EXT_ANCHOR), item('arc', anchor=D41_EXT_ANCHOR), item('fee', anchor=D41_EXT_ANCHOR),
               item('enrollment_proof_generic', anchor='재학을 입증하는 서류', role='educational_institution'),
               item('academic_progress_proof', anchor='학업을 정상적으로 수행하고 있음을 입증하는 서류', role='educational_institution'),
               item('finance_proof_domestic', anchor='재정입증 서류(국내 본인계좌 예치금만 인정)'),
               item('language_program_docs', anchor='모집요강 (연수일정 명시) 또는 연수계획서 (어학연수생에 한함)', role='educational_institution'),
               residence(anchor='⑥ 체류지 입증서류')],
         **NOTES)

D45_EXT_ANCHOR = '① 신청서 (별지 34호 서식), 여권, 외국인등록증, 수수료'
guidance('D-4-5', 'extension', section='일반연수(D-4) — 4. 한식조리연수생(D-4-5)의 체류기간연장 제출서류', anchor='한식조리연수생(D-4-5)의 체류기간연장 제출서류',
         summary_ko='농식품부가 지정한 한식조리 연수기관의 정규 프로그램 참여 시 입국일로부터 최대 2년 이내에서 연장할 수 있습니다. 재학증명서, 연수비 납입증명서, 개인별 연수 계획서, 오리엔테이션 결과 보고서, 한국어능력 입증서류, 체류지 입증서류 등을 냅니다.',
         summary_en='Trainees in a regular programme at a Korean-cuisine institution designated by the Ministry of Agriculture may extend up to two years from entry, with an enrollment certificate, proof of fee payment, individual training plan, orientation report, proof of Korean ability and proof of residence.',
         period_ko='입국일로부터 최대 2년 이내', period_en='Up to 2 years from entry',
         docs=[item('app_form_34', anchor=D45_EXT_ANCHOR), item('passport', anchor=D45_EXT_ANCHOR), item('arc', anchor=D45_EXT_ANCHOR), item('fee', anchor=D45_EXT_ANCHOR),
               item('d16_d45_enroll', anchor='② 한식 연수과정 재학증명서(연수기관 발행)'),
               item('d16_d45_fee_cert', anchor='③ 연수비 납입증명서 (연수기관 발행)', substitution_allowed=True, alternatives_group='d45-fee', alternatives=[{'ko': '연수기관이 연수비 및 체재경비 등을 부담하는 경우 연수기관이 발행한 경비부담 확인서', 'en': 'Cost-coverage confirmation from the institution, if it pays fees and living costs'}]),
               item('d16_d45_individual_plan', anchor='④ 개인별 연수 계획서 (旣 이수과정 성적·출석율 명시하여 연수기관 작성)'),
               item('d16_d45_orientation', anchor='⑤ 입국 후 국내 적응 오리엔테이션 실시 결과 보고서'),
               item('d16_d45_korean_ext', anchor='⑥ 한국어능력 입증서류 (기초·심화 과정 수료기준 충족여부 확인)'),
               item('d16_d45_health_ext', 'CONDITIONAL_REQUIRED', anchor='⑦ 건강진단서 (치료예정확인서 제출자에 한함)', applies_when_ko='치료예정확인서 제출자', applies_when_en='If you submitted a planned-treatment confirmation'),
               residence(anchor='⑧ 체류지 입증서류')],
         **NOTES)

guidance('D-4-6', 'extension', section='일반연수(D-4) — 5. 우수사설교육기관 외국인연수(D-4-6)의 체류기간연장 제출서류', anchor='우수사설교육기관 외국인연수(D-4-6)의 체류기간연장 제출서류',
         summary_ko='우수사설교육기관 외국인연수(D-4-6)는 연수기관 준비서류(출석증명서, 기술연수 계획서 등)와 신청자 준비서류(체류경비·등록금 납입·재학 증명)로 연장하며, 체류기간 1년 초과자는 연수계획서를 추가로 냅니다. 일반연수 기간은 원칙적으로 입국일로부터 최대 1년입니다.',
         summary_en='D-4-6 trainees extend with the institution\'s documents (attendance, technical training plan, etc.) and their own (living costs, tuition payment, enrollment); those staying over a year also submit a training plan. General training lasts up to one year from entry in principle.',
         docs=[item('app_form_34', anchor=D45_EXT_ANCHOR), item('passport', anchor=D45_EXT_ANCHOR), item('arc', anchor=D45_EXT_ANCHOR), item('fee', anchor=D45_EXT_ANCHOR),
               item('d16_d46_inst_ext', anchor='② 연수기관 준비서류 : 출석증명서'),
               item('d16_d46_stay_cost_ext', anchor='체류경비 입증서류 : 체류 기간에 따른 은행발행 ‘잔액증명’'),
               item('d16_d46_fee_ext', anchor='등록금(교육비) 납입 증명 : 수강기간 및 수강료, 납부일 등 기재'),
               item('d16_d46_enroll_ext', anchor='재학(연수) 증명 : 입학일, 전공 등 기재'),
               item('d16_d46_plan_ext', 'CONDITIONAL_REQUIRED', anchor='④ 연수계획서 (체류기간 1년 초과자)', applies_when_ko='체류기간 1년 초과자', applies_when_en='Stays over one year')],
         **NOTES)

# ---- D-4 stay: 시간제 취업 — the D-4 chapter refers to the D-2 chapter, whose section covers D-4-1 and D-4-7.
PT_BASE = '신청서, 여권, 외국인등록증 ※ 수수료 면제'
for _code in ('D-4-1', 'D-4-7'):
    guidance(_code, 'part_time_work', section='유학(D-2) — 시간제취업 활동 허가 (어학연수 D-4-1, D-4-7 포함)', anchor='어학연수생(D-4): 체류기간 내에서 최장 6개월, 장소 1곳 한정',
             summary_ko='어학연수(D-4-1, D-4-7) 자격은 변경일(사증소지자는 입국일)로부터 6개월이 지나야 시간제취업 허가 대상이 되며, 체류기간 내에서 최장 6개월, 장소 1곳으로 한정됩니다. 수수료는 면제되고, 고용주가 바뀌면 사전에 새로 허가를 받아야 합니다.',
             summary_en='Language trainees (D-4-1, D-4-7) become eligible six months after the status change (or entry, for visa holders); permission lasts up to six months within the stay and covers one workplace. No fee; a new employer needs a new permit in advance.',
             fee_ko='수수료 면제', fee_en='No fee',
             conditions_ko=['어학연수과정은 전체 이수학기 평균 출석률 90% 미만이면 제한되며, 최근 3개월 이내 무허가 취업 또는 허가조건 위반으로 처벌받은 경력이 있으면 제한됩니다.', '전문분야(E-1~E-7) 활동, 제조업(한국어능력 4급 이상이면 허용)·건설업·선원 업종, 특수형태근로(택배·배달·대리운전 등), 파견·도급·알선, 원거리 근무 등은 제한됩니다.'],
             conditions_en=['Restricted if average attendance across all terms is below 90%, or if penalised for unpermitted work or condition violations in the past three months.', 'Professional (E-1~E-7) work, manufacturing (allowed with Korean level 4+), construction and seafaring, platform/delivery work, dispatch/subcontracting/brokering and remote work are restricted.'],
             docs=[item('app_form', anchor=PT_BASE), item('passport', anchor=PT_BASE), item('arc', anchor=PT_BASE),
                   item('transcript_or_attendance', 'ADMIN_INFO_CHECKABLE', anchor='성적 또는 출석 증명서(유학생정보시스템으로 확인이 될 경우 생략)', administrative_information_exemption=True, role='educational_institution'),
                   item('korean_ability_proof', anchor='한국어 능력(영어 능력) 증빙서류'),
                   item('pt_confirmation_univ', anchor='외국인 유학생 시간제 취업 확인서', role='educational_institution'),
                   item('pt_compliance_employer', 'CONDITIONAL_REQUIRED', anchor='사업자등록증에 제조업, 건설업이 포함된 경우에 한함', applies_when_ko='사업자등록증에 제조업·건설업이 포함된 경우', applies_when_en='If the business registration includes manufacturing or construction', role='employer'),
                   item('business_reg_employer_id', anchor='사업자등록증 사본 및 고용주 신분증 사본', role='employer'),
                   item('standard_contract_hourly', anchor='표준근로계약서 사본(시급 및 근무내용, 시간이 포함되어 있을 것)', role='employer')],
             **NOTES)

# ---- D-4 stay: 외국인등록
D4_REG_BASE = '① 신청서(별지34호 서식), 여권원본, 표준규격사진1장, 수수료'
guidance('D-4', 'registration', section='일반연수(D-4) 외국인등록 — 1. 외국인등록 제출서류', anchor='② 재학증명서, ③ 체류지 입증서류',
         summary_ko='일반연수(D-4) 외국인등록은 신청서·여권 원본·사진·수수료와 재학증명서, 체류지 입증서류를 냅니다. 한식조리연수(D-4-5), 고등학교 이하 유학생(D-4-3), 기업 맞춤형 인턴십(D-4-2K)은 별도 서류를 확인하세요.',
         summary_en='D-4 registration needs the form, original passport, photo and fee with an enrollment certificate and proof of residence. D-4-5, D-4-3 and D-4-2K have their own lists.',
         docs=[item('app_form_34', anchor=D4_REG_BASE), item('passport_original', anchor=D4_REG_BASE), item('photo', anchor=D4_REG_BASE), item('fee', anchor=D4_REG_BASE),
               item('enrollment_cert', anchor='② 재학증명서, ③ 체류지 입증서류', role='educational_institution'),
               residence(anchor='② 재학증명서, ③ 체류지 입증서류')],
         **NOTES)
guidance('D-4-5', 'registration', section='일반연수(D-4) 외국인등록 — 2. 한식조리연수생(D-4-5)의 외국인등록 제출서류', anchor='한식조리연수생(D-4-5)의 외국인등록 제출서류',
         summary_ko='한식조리연수생(D-4-5) 외국인등록은 신청서·여권 원본·사진·수수료와 연수기관 사업자등록증 사본, 수라학교 지정증, 법무부 지정병원 건강진단서, 체류지 입증서류를 냅니다.',
         summary_en='D-4-5 registration needs the form, original passport, photo and fee with the institution\'s business registration copy, the Sura School designation, a health certificate from a Ministry-designated hospital and proof of residence.',
         docs=[item('app_form_34', anchor=D4_REG_BASE), item('passport_original', anchor=D4_REG_BASE), item('photo', anchor=D4_REG_BASE), item('fee', anchor=D4_REG_BASE),
               item('d16_d45_school_biz_reg', anchor='② 연수기관 사업자등록증 (또는 고유번호증) 사본'),
               item('d16_d45_sura_designation_reg', anchor='③ 농식품부 발행 한식 전문인력 양성기관(수라학교) 지정증'),
               item('d16_health_designated', anchor='④ 법무부 지정병원에서 발급한 건강진단서'),
               residence(anchor='⑤ 체류지 입증서류')],
         **NOTES)
guidance('D-4-3', 'registration', section='일반연수(D-4) 외국인등록 — 3. 고등학교 이하 외국인유학생(D-4-3) 제출서류', anchor='고등학교 이하 외국인유학생(D-4-3) 제출서류',
         summary_ko='고등학교 이하 유학생(D-4-3) 외국인등록은 신청서·여권·사진·수수료(정부 등 초청 국비 장학생도 납부)와 재학 증명서, 장학생 입증서류(해당자), 체류지 입증서류를 냅니다.',
         summary_en='D-4-3 registration needs the form, passport, photo and fee (government scholars also pay) with an enrollment certificate, scholarship proof if applicable and proof of residence.',
         docs=[item('app_form_34', anchor='① 신청서(별지34호 서식), 여권, 사진(6개월 내 촬영 반명함) 1장, 수수료*'), item('passport', anchor='① 신청서(별지34호 서식), 여권, 사진(6개월 내 촬영 반명함) 1장, 수수료*'),
               item('d16_photo_6m', anchor='① 신청서(별지34호 서식), 여권, 사진(6개월 내 촬영 반명함) 1장, 수수료*'), item('fee', anchor='정부 등 초청 국비 장학생도 시행규칙 제74조에 의거 등록 및 등록증 (재)발급 수수료 납부 대상자임'),
               item('enrollment_cert', anchor='② 재학 증명서**', role='educational_institution', substitution_allowed=True, alternatives_group='d43-reg', alternatives=[{'ko': '입학 전 외국인등록 시 학교장의 직인이 날인된 학비 납부 내역서', 'en': 'Before admission: tuition payment history sealed by the principal'}]),
               item('d16_d43_scholar_proof_reg', 'CONDITIONAL_REQUIRED', anchor='③ 장학생 입증서류 (해당자, 기관·단체의 공문)', applies_when_ko='해당자', applies_when_en='If applicable'),
               residence(anchor='④ 체류지 입증서류')],
         **NOTES)
guidance('D-4-2K', 'registration', section='일반연수(D-4) 외국인등록 — 4. 기업 맞춤형 인턴십(K-Trainee, D-4-2K) 제출서류', anchor='기업 맞춤형 인턴십(K-Trainee, D-4-2K) 제출서류',
         summary_ko='기업 맞춤형 인턴십(D-4-2K) 외국인등록은 신청서·여권·사진(6개월 내 촬영 반명함)·수수료와 체류지 입증서류를 냅니다.',
         summary_en='D-4-2K registration needs the form, passport, photo (half-length, taken within 6 months), fee and proof of residence.',
         docs=[item('app_form_34', anchor='① 신청서(별지34호 서식), 여권, 사진(6개월 내 촬영 반명함) 1장, 수수료'), item('passport', anchor='① 신청서(별지34호 서식), 여권, 사진(6개월 내 촬영 반명함) 1장, 수수료'),
               item('d16_photo_6m', anchor='① 신청서(별지34호 서식), 여권, 사진(6개월 내 촬영 반명함) 1장, 수수료'), item('fee', anchor='① 신청서(별지34호 서식), 여권, 사진(6개월 내 촬영 반명함) 1장, 수수료'),
               residence(anchor='② 체류지 입증서류')],
         **NOTES)

multi_reentry('D-4', '일반연수(D-4)', 'D-4', restricted_ko='입국규제 등의 사유로 재입국허가를 받아야 하는 유학생은 체류지 관할 청(사무소·출장소)에 재입국허가를 받아야 합니다.',
              restricted_en='Students who must obtain a re-entry permit because of entry restrictions apply at the local office.')

# ==========================================================================
# D-5 취재
# ==========================================================================
guidance('D-5', 'visa_issuance', manual=VISA, section='취재(D-5) — 공관장 재량으로 발급할 수 있는 사증', anchor='국내에 지사나 지국이 이미 개설된 보도기관에 파견되어 활동 하고자',
         summary_ko='국내에 지사나 지국이 이미 개설된 보도기관에 파견되어 활동하려는 사람과 그 동반가족(F-3)은 재외공관에서 체류기간 1년 이하의 단수사증을 받을 수 있습니다. 파견명령서 또는 재직증명서와 국내 지국·지사 설치허가증 또는 운영자금 도입실적 증빙서류를 냅니다.',
         summary_en='People dispatched to a media organisation that already has a bureau or branch in Korea, and their accompanying family (F-3), can get a single-entry visa of up to one year at a mission, with a dispatch order or certificate of employment and the bureau\'s permit or proof of operating funds.',
         docs=visa_base_17('① 사증발급신청서 (별지 제17호 서식), 여권, 표준규격사진 1매, 수수료') + [
             item('d16_dispatch_or_employment', anchor='② 파견명령서 또는 재직증명서'),
             item('d16_press_permit_or_funds', anchor='③ 국내 지국․지사 설치허가증이나 국내 지국․지사 운영자금 도입실적 증빙서류')],
         notes_ko=['재외공관의 장은 필요한 경우 첨부서류를 일부 가감할 수 있습니다.', OFFICER_NOTE_KO], notes_en=['The head of the mission may add or waive some documents when needed.', OFFICER_NOTE_EN])
guidance('D-5', 'visa_issuance_confirmation', manual=VISA, section='취재(D-5) — 사증발급인정서 발급대상', anchor='외국의 보도기관과의 계약에 의하여 국내에서 주재하면서 취재',
         summary_ko='외국 보도기관에서 파견되거나 외국 보도기관과의 계약으로 국내에 주재하며 취재·보도하는 사람은 사증발급인정서로 신청하며, 파견명령서 또는 재직증명서와 국내 지국·지사 설치허가증 또는 운영자금 도입실적 증빙서류를 냅니다. 국내 지국·지사가 없거나 증명을 받을 수 없으면 주무부처 협조공문으로 갈음할 수 있습니다.',
         summary_en='Journalists dispatched by, or under contract with, a foreign media organisation to report from Korea apply for a confirmation of visa issuance with a dispatch order or certificate of employment and the bureau\'s permit or proof of operating funds; without a bureau, a cooperation letter from the competent ministry can replace it.',
         docs=cvi_base_21('① 사증발급인정신청서 (별지 제21호 서식), 여권사본, 표준규격사진 1매') + [
             item('d16_dispatch_or_employment', anchor='② 파견명령서 또는 재직증명서'),
             item('d16_press_permit_or_funds', anchor='③ 국내지국․지사 설치허가증이나 국내 지국․지사 운영자금 도입실적 증빙서류'),
             item('d16_mcst_cooperation', 'ALTERNATIVE_DOCUMENT', anchor='국내에 지국･지사가 없거나 증명을 발급받을 수 없는 외신은 주무부처 (문화체육관광부 해외문화홍보원)의 협조공문으로 갈음할 수 있음', applies_when_ko='국내에 지국·지사가 없거나 증명을 발급받을 수 없는 외신', applies_when_en='Foreign media without a bureau in Korea or unable to obtain the certificate'),
             proxy_item()],
         notes_ko=['출입국·외국인청(사무소·출장소)장은 첨부서류의 일부를 가감할 수 있습니다.', OFFICER_NOTE_KO], notes_en=['The immigration office may add or waive some documents.', OFFICER_NOTE_EN])

guidance('D-5', 'status_change', section='취재(D-5) 체류자격 변경허가', anchor='일시취재(C-1) 자격 소지자에 대하여 국내 장기취재 필요성이 입증될 경우 장기취재(D-5) 자격으로의 변경허가',
         summary_ko='일시취재(C-1) 소지자는 국내 장기취재 필요성이 입증되면 취재(D-5)로 변경할 수 있고, 사증면제(B-1)로 입국한 독일인도 장기체류자격으로 변경할 수 있습니다. 신청서·여권·수수료, 본사 발행 파견명령서, 지국·지사 설치허가증 또는 사업자등록증 사본을 냅니다.',
         summary_en='C-1 holders may change to D-5 when the need for long-term reporting is proven, and Germans who entered visa-free (B-1) may change to a long-term status. Submit the form, passport and fee, a head-office dispatch order and the bureau permit or business registration copy.',
         docs=[item('app_form_34', anchor='①신청서 (별지 34호 서식), 여권, 수수료 ② 파견명령서(본사 발행)'), item('passport', anchor='①신청서 (별지 34호 서식), 여권, 수수료 ② 파견명령서(본사 발행)'), item('fee', anchor='①신청서 (별지 34호 서식), 여권, 수수료 ② 파견명령서(본사 발행)'),
               item('d16_dispatch_order_head', anchor='② 파견명령서(본사 발행)'),
               item('d16_press_permit_or_bizreg', anchor='③ 지국․지사의 설치허가증(문화체육관광부에서 발행) 또는 사업자등록증 사본'),
               item('d16_mcst_cooperation', 'ALTERNATIVE_DOCUMENT', anchor='국내에 지국･지사가 없거나 증명을 발급받을 수 없는 외신은 주무부처(문화체육관광부 해외문화홍보원)의 협조공문으로 갈음할 수 있음', applies_when_ko='국내에 지국·지사가 없거나 증명을 발급받을 수 없는 외신', applies_when_en='Foreign media without a bureau in Korea or unable to obtain the certificate'),
               item('d16_longterm_need', 'CONDITIONAL_REQUIRED', anchor='허가 시에는 관계부처 협조공한 등 장기취재 필요성을 입증할 수 있는 서류를 징구할 것', applies_when_ko='일시취재(C-1)에서 변경하는 경우', applies_when_en='Changing from C-1')],
         **NOTES)

guidance('D-5', 'activities_outside_status', completeness='SOURCE_ONLY', section='취재(D-5) 체류자격외 활동', anchor='체류자격외 활동 허가(신고)대상이 아닌 회화지도(E-2) 활동',
         summary_ko='원래의 체류목적을 침해하지 않는 범위에서 정규교육기관(초·중·고 및 대학)의 교육을 받는 것은 별도 허가가 필요 없습니다. 소속 직장 내 동료직원 대상 외국어 회화지도와 영리·유상 목적이 아닌 사회봉사 차원의 회화지도도 허가(신고) 대상이 아니지만, 회화지도가 주된 활동이 되거나 허용기준을 벗어나면 제외됩니다.',
         summary_en='Regular schooling (primary to university) within the original purpose needs no permit. Teaching foreign-language conversation to colleagues at your own workplace, or as unpaid community service, needs no permit or report either, unless it becomes your main activity or goes beyond these limits.')

guidance('D-5', 'workplace_change', state='NOT_APPLICABLE', completeness='SOURCE_ONLY', section='취재(D-5) 근무처의 변경․추가', anchor='근무처 변경․추가 신고대상 아님',
         summary_ko='취재(D-5)는 근무처 변경·추가 신고대상이 아닙니다. 소속기관 또는 단체의 명칭이 변경되는 경우에는 외국인등록사항 변경신고로 처리합니다.',
         summary_en='D-5 is not subject to workplace change/addition reporting. A change in the name of the affiliated organisation is handled as a registration-information change report.')

multi_reentry('D-5', '취재(D-5)', 'D-5')

# ==========================================================================
# D-6 종교
# ==========================================================================
guidance('D-6', 'visa_issuance', manual=VISA, section='종교(D-6) — 공관장 재량으로 발급할 수 있는 사증', anchor='국내 종교․사회복지단체로부터 초청되어 사회복지활동에만 종사 하고자 하는 자에 대한 체류기간 1년 이하의 단수사증',
         summary_ko='국내 종교·사회복지단체의 초청으로 사회복지활동에만 종사하려는 사람은 재외공관에서 체류기간 1년 이하의 단수사증을 받을 수 있으며, 파견명령서, 종교단체 또는 사회복지단체 설립허가서 사본, 소속단체의 체류경비 지원 관련서류를 냅니다.',
         summary_en='People invited by a Korean religious or social-welfare organisation solely for social-welfare work can get a single-entry visa of up to one year at a mission, with a dispatch order, a copy of the organisation\'s establishment permit and proof of the organisation\'s support for living costs.',
         docs=visa_base_17('① 사증발급신청서 (별지 제17호 서식), 여권, 표준규격사진 1매, 수수료') + [
             item('d16_dispatch_order', anchor='② 파견명령서'),
             item('d16_religious_permit', anchor='③ 종교단체 설립허가서 또는 사회복지단체 설립허가서 사본'),
             item('d16_org_expense_support', anchor='④ 소속단체의 체류경비 지원 관련서류')],
         notes_ko=['재외공관의 장은 필요한 경우 첨부서류를 일부 가감할 수 있습니다.', OFFICER_NOTE_KO], notes_en=['The head of the mission may add or waive some documents when needed.', OFFICER_NOTE_EN])
guidance('D-6', 'visa_issuance_confirmation', manual=VISA, section='종교(D-6) — 사증발급인정서 발급대상', anchor='국내 종교단체의 추천을 받아 그 종교단체에서 수도, 수련, 연구 활동을 하는 자',
         summary_ko='외국 종교·사회복지단체에서 국내 지부나 유관 종교단체로 파견되는 사람, 소속 종교단체가 운영하는 의료·교육·구호단체의 초청으로 선교·사회복지 활동을 하는 사람(보수를 받는 사람 제외), 국내 종교단체 추천으로 수도·수련·연구하는 사람은 사증발급인정서로 신청합니다.',
         summary_en='People dispatched by a foreign religious or welfare organisation to its Korean branch or a related religious body, invited by a medical, educational or relief body run by their religious organisation for mission or welfare work (unpaid), or recommended by a Korean religious body for monastic practice, training or research apply for a confirmation of visa issuance.',
         docs=cvi_base_21('① 사증발급인정신청서 (별지 제21호 서식), 여권사본, 표준규격사진 1매') + [
             item('d16_invite_reason', anchor='② 초청사유서'),
             item('d16_dispatch_order', anchor='③ 파견명령서'),
             item('d16_religious_permit', anchor='④ 종교단체 설립허가서 또는 사회복지단체 설립허가서 사본'),
             item('d16_unique_no_copy', anchor='⑤ 고유번호증 사본', notes_ko='종교단체 초청인 경우 종단(교단)과 단위교회(사찰) 모두 제출합니다.', notes_en='For a religious inviter, submit it for both the denomination and the individual church or temple.'),
             item('d16_org_expense_support', anchor='⑥ 소속단체의 체류경비 지원 관련서류'),
             proxy_item()],
         notes_ko=['출입국·외국인청(사무소·출장소)장은 첨부서류의 일부를 가감할 수 있습니다.', OFFICER_NOTE_KO], notes_en=['The immigration office may add or waive some documents.', OFFICER_NOTE_EN])

D6_AOS_BASE = '①신청서(별지34호 서식). 여권 및 외국인등록증, 수수료 ②동일재단입증서류'
D6_TO_E1 = dict(applies_when_ko='종교(D-6) → 교수(E-1)', applies_when_en='D-6 holder doing E-1 work')
E1_TO_D6 = dict(applies_when_ko='교수(E-1) → 종교(D-6)', applies_when_en='E-1 holder doing D-6 work')
guidance('D-6', 'activities_outside_status', section='종교(D-6) 체류자격외 활동 — 3. 동일 종교재단 산하기관 근무자의 종교(D-6), 교수(E-1) 상호간 체류자격외 활동', anchor='동일 종교재단 산하기관 근무자의 종교(D-6), 교수(E-1) 상호간 체류자격외 활동 가능',
         summary_ko='동일 종교재단 산하기관 근무자는 종교(D-6)와 교수(E-1) 상호간 체류자격외 활동이 가능하며, 방향에 따라 동일재단 입증서류, 고용계약서·학위증·사업자등록증 사본 또는 해당단체 설립허가서, 원근무처의 동의서를 냅니다. 정규교육기관 교육과 일정 범위의 회화지도 활동은 별도 허가가 필요 없습니다.',
         summary_en='Staff of bodies under the same religious foundation may do D-6 and E-1 activities for each other with permission, submitting proof of the same foundation, the employment contract, degree certificate and business registration copy (or the organisation\'s establishment permit), and the original workplace\'s consent. Regular schooling and limited conversation teaching need no permit.',
         docs=[item('app_form_34', anchor=D6_AOS_BASE), item('passport', anchor=D6_AOS_BASE), item('arc', anchor=D6_AOS_BASE), item('fee', anchor=D6_AOS_BASE),
               item('d16_same_foundation', anchor=D6_AOS_BASE),
               item('contract_original_copy', 'CONDITIONAL_REQUIRED', anchor='③고용계약서 원본 및 사본 ④ 학위증 ⑤사업자등록증 사본 ⑥원근무처장의 동의서', **D6_TO_E1),
               item('d16_degree_cert', 'CONDITIONAL_REQUIRED', anchor='④ 학위증 ⑤사업자등록증 사본', **D6_TO_E1),
               item('business_reg_copy', 'CONDITIONAL_REQUIRED', anchor='⑤사업자등록증 사본 ⑥원근무처장의 동의서', **D6_TO_E1),
               item('d16_original_employer_consent', 'CONDITIONAL_REQUIRED', anchor='⑥원근무처장의 동의서', **D6_TO_E1),
               item('d16_original_employer_consent', 'CONDITIONAL_REQUIRED', anchor='③원근무처의 동의서 ④ 해당단체 설립허가서', **E1_TO_D6),
               item('d16_org_establishment_permit', 'CONDITIONAL_REQUIRED', anchor='④ 해당단체 설립허가서', **E1_TO_D6)],
         **NOTES)

guidance('D-6', 'workplace_change', state='NOT_APPLICABLE', completeness='SOURCE_ONLY', section='종교(D-6) 근무처의 변경․추가', anchor='근무처 변경․추가 허가(신고) 대상 아님',
         summary_ko='종교(D-6)는 근무처 변경·추가 허가(신고) 대상이 아닙니다. 소속기관 또는 단체의 명칭이 변경되는 경우에는 외국인등록사항 변경신고로 처리합니다.',
         summary_en='D-6 is not subject to workplace change/addition permission or reporting. A change in the name of the affiliated organisation is handled as a registration-information change report.')

multi_reentry('D-6', '종교(D-6)', 'D-6')
