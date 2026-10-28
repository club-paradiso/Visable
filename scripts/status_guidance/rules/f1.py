# F-1 방문동거 — transcribed from the 2026-10-19 manuals.
#   VISA: 사증민원 매뉴얼 '방문동거(F-1)' (공관장 재량으로 발급할 수 있는 사증 / 사증발급인정서 발급대상).
#   STAY: 체류민원 매뉴얼 '방문동거(F-1)' (체류자격외 활동 / 체류자격 부여 / 체류자격 변경허가 / 재입국허가).
# The existing F-1 체류기간 연장 rules live in author_rules.py; this batch only adds missing cells.
# Runs inside author_rules.py (guidance, item, docdefs, drop, residence, base_stay, VISA, STAY …).

docdefs(
    f1_visa_app_form=('사증발급신청서 (별지 제17호 서식)', 'Visa application form (Form No. 17)', 'applicant', None),
    f1_cert_app_form=('사증발급인정신청서 (별지 제21호 서식)', 'Application for a visa issuance confirmation (Form No. 21)', 'inviter', None),
    f1_admission_or_enrollment=('입학허가서 또는 재학증명서', 'Letter of admission or certificate of enrollment', 'educational_institution', None),
    f1_family_relation_original=('가족관계 입증서류 (원본 및 번역본 첨부, 호구부, 출생증명서 등)', 'Proof of family relationship (original with translation; hukou, birth certificate, etc.)', 'applicant', None),
    f1_living_cost_proof=('국내 체류비용 부담능력 입증서류 (3개월 이상 계속 예치된 기준 이상 금액의 잔고증명서 등)', 'Proof of ability to cover living costs in Korea (balance certificate of at least the required amount held for 3+ months, etc.)', 'applicant', None),
    f1_financial_capacity_proof=('재정능력 입증서류 (불법체류 다발국가 국민에 한함)', 'Proof of financial capacity (nationals of high-overstay countries only)', 'applicant', None),
    f1_mission_coop_letter=('외국공관의 협조공문', 'Cooperation letter from the foreign mission', 'principal_holder', None),
    f1_mission_request_letter=('외국공관의 요청공문', 'Request letter from the foreign mission', 'principal_holder', None),
    f1_mission_request_letter_kr=('주한 해당공관의 요청공문', 'Request letter from the foreign mission in Korea', 'principal_holder', None),
    f1_employer_id_copy=('고용인의 신분증명서 사본', "Copy of the employer's identity document", 'employer', None),
    f1_employer_diplomat_id_copy=('고용인의 외교관신분증 사본', "Copy of the employer's diplomatic ID", 'employer', None),
    f1_employer_diplomat_id_copy_kr=('고용인의 외교관신분증명서 사본', "Copy of the employer's diplomatic identity certificate", 'employer', None),
    f1_employment_contract_copy=('고용계약서 사본', 'Copy of the employment contract', 'employer', None),
    f1_ip_rights_proof=('산업재산권, 그 밖에 이에 준하는 기술과 그 사용에 관한 권리 등을 보유하고 있음을 입증하는 서류', 'Proof of holding industrial property rights or equivalent technology and usage rights', 'employer', None),
    f1_employer_income_proof=('고용주의 소득 요건 입증 자료 (근로소득원천징수영수증, 소득금액 증명원, 급여명세서, 통장사본 등)', "Proof that the employer meets the income requirement (withholding receipt, income certificate, pay slips, bankbook copy, etc.)", 'employer', None),
    f1_employer_annual_income_proof=('고용주의 연간 소득 수준을 입증할 수 있는 자료 (근로소득원천징수영수증, 소득금액 증명원, 급여명세서, 통장사본 등)', "Proof of the employer's annual income (withholding receipt, income certificate, pay slips, bankbook copy, etc.)", 'employer', None),
    f1_korean_staff_proof=('고용중인 내국인 상시근로자 입증 서류 (근로소득 원천징수 영수증, 소득금액 증명원, 급여명세서, 통장사본 등)', 'Proof of Korean full-time employees (withholding receipts, income certificate, pay slips, bankbook copy, etc.)', 'employer', None),
    f1_helper_education_proof=('가사보조인의 졸업증명서 등 학력을 입증할 수 있는 서류', "Proof of the domestic helper's education (graduation certificate, etc.)", 'applicant', None),
    f1_helper_1y_service_proof=('1년 이상 고용주의 가사보조인으로 근무한 사실을 입증하는 서류 (고용계약서, 급여명세서, 통장사본 등)', 'Proof of at least one year of service as the employer\'s domestic helper (contract, pay slips, bankbook copy, etc.)', 'applicant', None),
    f1_kinship_proof=('친족관계를 입증하는 서류 (호구부, 거민신분증 등)', 'Proof of kinship (hukou, resident ID, etc.)', 'applicant', None),
    f1_cohabitation_need_proof=('동거 또는 장기체류 필요성을 입증하는 서류', 'Proof of the need to live together or stay long-term', 'applicant', None),
    f1_inviter_id_copy=('초청인 신분증 사본', "Copy of the inviter's ID", 'inviter', None),
    f1_invitation=('초청장', 'Letter of invitation', 'inviter', None),
    f1_illegal_stay_pledge=('불법체류･취업 방지 서약서', 'Pledge against illegal stay and employment', 'inviter', None),
    f1_home_family_proof=('결혼이민자의 직계가족 및 형제자매 모두를 확인할 수 있는 가족관계 증명서류 (해당 국가 정부에서 발급한 공적 서류)', "Family-relation documents showing all of the marriage migrant's lineal family and siblings (official documents issued by that country's government)", 'applicant', None),
    f1_parents_unable_proof=('결혼이민자의 부모 모두가 사망하거나 질병, 60세 이상 고령 등의 사유로 입국이 불가함을 확인할 수 있는 서류와 피초청인의 직계가족을 확인할 수 있는 가족관계 증명서류', "Proof that both of the marriage migrant's parents cannot come (death, illness, age 60+, etc.) and family-relation documents for the invitee's lineal family", 'applicant', None),
    f1_regional_stay_proof_visa=('비수도권 및 인구감소(관심)지역에 체류할 예정임을 입증하는 서류 (1개월 이상 임대차 계약서, 워케이션 특화시설 또는 숙소 예약확인서 등)', 'Proof of a planned stay outside the capital region or in a depopulation area (lease of 1+ month, workation facility or lodging reservation, etc.)', 'applicant', None),
    f1_other_consul_docs=('기타 재외공관장이 필요하다고 인정하는 서류', 'Other documents the consul deems necessary', 'applicant', None),
    f1_regional_stay_proof_stay=('비수도권 및 인구감소(관심)지역에 체류할 예정임을 입증하는 서류 (1개월 이상 임대차 계약서, 워케이션 특화시설 또는 숙소 예약확인서 등)', 'Proof of a planned stay outside the capital region or in a depopulation area (lease of 1+ month, workation facility or lodging reservation, etc.)', 'applicant', None),
    f1_intl_adoption_proof=('양국의 국제입양성립(진행)을 입증할 수 있는 서류 (국제입양절차 진행 협의서 사본 또는 협약준수입양증명서, 해당 시 임시양육 허가 증명서 사본)', 'Proof that the international adoption is completed or in progress in both countries (copy of the adoption-procedure agreement or Hague-compliance adoption certificate; copy of a temporary custody permit if applicable)', 'applicant', None),
    f1_child_identity_proof=('아동의 신원을 입증할 수 있는 서류 (출생증명서, 전혼 자녀는 양자의 가족관계를 확인할 수 있는 서류)', "Proof of the child's identity (birth certificate; for a child of a previous marriage, proof of the adoptee's family relations)", 'applicant', None),
    f1_adoptive_parent_identity=('양부모의 신원을 입증할 수 있는 서류 (부모의 가족관계증명서(상세본), 부모의 신분증)', "Proof of the adoptive parents' identity (parents' detailed family-relation certificate and IDs)", 'inviter', None),
    f1_criminal_record_14=('만 14세 이상인 경우 주재국 정부발행 범죄경력증명서', 'Criminal record certificate issued by the government of the country of residence (age 14 and over)', 'applicant', None),
    f1_invitation_reason=('초청사유서 (취업활동을 하지 않겠다는 내용 기재)', 'Statement of reasons for the invitation (stating no employment)', 'inviter', None),
    f1_income_investment_proof=('소득/투자금/체류경비 입증서류', 'Proof of income, investment or living funds', 'inviter', None),
    f1_family_kinship_proof=('가족 또는 친족관계 입증서류', 'Proof of family or kinship relationship', 'applicant', None),
    f1_divorce_marriage_cert=('이혼 사실이 기재된 혼인관계 증명서', 'Marriage-relation certificate showing the divorce', 'applicant', None),
    f1_naturalization_application_cert=('귀화허가 또는 국적회복허가 신청사실증명서', 'Certificate of a pending naturalization or nationality-restoration application', 'applicant', None),
    f1_korean_child_docs=('국민인 자녀의 주민등록등본, 기본증명서(상세), 가족관계증명서(상세)', "The Korean child's resident registration, detailed basic certificate and detailed family-relation certificate", 'applicant', None),
    f1_refugee_cert=('배우자 또는 그 부모의 난민인정증명서', "Refugee recognition certificate of the spouse or parent", 'principal_holder', None),
    f1_refugee_family_proof=('난민인정자의 가족임을 입증하는 서류', 'Proof of being a family member of the recognized refugee', 'applicant', None),
    f1_enrollment_if_applicable=('(해당시) 재학증명서 등 재학 중임을 알 수 있는 서류', 'Proof of school enrollment (if applicable)', 'applicant', None),
    f1_migrant_id_docs=('결혼이민자의 여권, 신분증(관련 국가), 외국인등록증', "The marriage migrant's passport, national ID and residence card", 'principal_holder', None),
    f1_child_birth_docs=('미성년 외국인 자녀의 여권, 관련 국가에서 발급한 출생 관련 공적 증명서류 원본 및 사본 (예: 중국 호구부, 출생증명서 등)', "The minor child's passport and the original and copy of official birth documents from the relevant country (e.g. Chinese hukou, birth certificate)", 'applicant', None),
    f1_custody_proof=('전혼 관계 출생 미성년 외국인 자녀에 대한 양육권 보유관계 입증서류 (이혼판결문 등)', 'Proof of custody of the minor child from the previous marriage (divorce judgment, etc.)', 'principal_holder', None),
    f1_migrant_spouse_guarantee=('양육권 등을 보유하고 미성년 외국인 자녀를 국내에서 양육하고 있는 결혼이민자와 한국인 배우자의 신원보증서', 'Letter of guarantee from the marriage migrant raising the child in Korea and the Korean spouse', 'principal_holder', None),
    f1_employment_recommendation=('주무부처 장의 고용추천서 또는 고용필요성 입증서류', 'Employment recommendation from the competent ministry or proof of the need to hire', 'employer', None),
    f1_degree_or_license=('학위증 또는 자격증', 'Degree certificate or qualification certificate', 'applicant', None),
    f1_degree_e2=('학위증 (E-2 자격요건과 동일)', 'Degree certificate (same as the E-2 requirement)', 'applicant', None),
    f1_criminal_record_e2=('범죄경력증명서 (E-2 자격요건과 동일)', 'Criminal record certificate (same as the E-2 requirement)', 'applicant', None),
    f1_medical_e2=('채용신체검사서 (E-2 자격요건과 동일)', 'Pre-employment medical report (same as the E-2 requirement)', 'applicant', None),
    f1_teacher_license=("해당국교원 자격증 원본 (교원자격증이 없는 경우 '학위증 및 경력증명서')", "Original teacher's licence of the home country (if none, degree and career certificates)", 'applicant', None),
    f1_principal_request=('학교장 요청서', "Request letter from the school principal", 'educational_institution', None),
    f1_foreign_teacher_status=('외국인교사 현황', 'Current list of foreign teachers', 'educational_institution', None),
    f1_agency_recommendation=('추천서 (해당 기관장)', 'Recommendation from the head of the institution', 'employer', None),
    f1_degree_original_copy=('학위증 (원본 및 사본)', 'Degree certificate (original and copy)', 'applicant', None),
)

VISA_CH = '사증민원 매뉴얼 방문동거(F-1)'
STAY_CH = '체류민원 매뉴얼 방문동거(F-1)'
VISA_APP = '사증발급신청서 (별지 제17호 서식), 여권, 표준규격사진 1매, 수수료'
CERT_APP = '사증발급인정신청서 (별지 제21호 서식), 여권, 표준규격사진 1매'
CONSUL_NOTE_KO = '재외공관의 장은 입국목적, 초청의 진정성, 초청자 및 피초청자의 자격 확인 등을 심사하기 위해 필요한 경우 첨부서류를 일부 가감할 수 있습니다.'
CONSUL_NOTE_EN = 'The head of the overseas mission may add or waive some documents to review the purpose of entry, the genuineness of the invitation and the eligibility of both parties.'
OFFICE_NOTE_KO = '출입국·외국인청(사무소·출장소)장은 초청의 진정성, 초청자 및 피초청자의 자격 확인 등을 심사하기 위해 첨부서류의 일부를 가감할 수 있습니다.'
OFFICE_NOTE_EN = 'The immigration office may add or waive some documents to review the genuineness of the invitation and the eligibility of both parties.'
FOREIGN_DOC_NOTE_KO = '해외 기관이 발급한 서류는 아포스티유 확인 또는 대한민국 공관의 영사확인을 받아 제출(국문 또는 영문 번역문 첨부)해야 합니다.'
FOREIGN_DOC_NOTE_EN = 'Documents issued abroad need an apostille or Korean consular confirmation (with a Korean or English translation).'


def visa_app(anchor=VISA_APP):
    return [item('f1_visa_app_form', anchor=anchor), item('passport', anchor=anchor), item('photo', anchor=anchor), item('fee', anchor=anchor)]


def cert_app(anchor=CERT_APP):
    return [item('f1_cert_app_form', anchor=anchor), item('passport', anchor=anchor), item('photo', anchor=anchor)]


def stay_app(anchor, arc=False, photo=True):
    docs = [item('app_form_34', anchor=anchor), item('passport', anchor=anchor)]
    if arc:
        docs.append(item('arc', anchor=anchor))
    if photo:
        docs.append(item('photo', anchor=anchor))
    docs.append(item('fee', anchor=anchor))
    return docs


LEASE_ONLY = [{'ko': '임대차계약서', 'en': 'Lease contract'}]

# ==========================================================================
# 사증발급 (visa manual — 공관장 재량으로 발급할 수 있는 사증)
# ==========================================================================
guidance('F-1-13', 'visa_issuance', manual=VISA, section=f'{VISA_CH} — 공관장 재량 사증 1. 외국인 유학생(고등학교 이하) 동반 부모(F-1-13)',
         anchor='외국인 유학생(고등학교 이하) 동반 부모(F-1-13)',
         summary_ko='고등학교 이하 교육기관에 입학 예정이거나 재학 중인 자비 부담 외국인유학생의 2촌 이내 친인척(유학생 1명당 1명)은 재외공관에서 체류기간 1년 이내 단수 사증을 신청합니다.',
         summary_en='A relative within the second degree of a self-funded international student admitted to or enrolled in a school up to high-school level (one per student) applies at the overseas mission for a single-entry visa of up to one year.',
         period_ko='체류기간 1년 이내, 단수', period_en='Up to 1 year, single entry',
         conditions_ko=['국내 체류 비용(1년간 생활비: 외국인 유학생 연간 생활비 기준액의 2배 상당 금액, 1인 기준) 부담능력이 있어야 합니다.',
                        '21개 국가 국민은 연간 소득이 전년도 GNI 이상이거나 자산이 「국민기초생활보장법」에 따른 중위 수준 이상이어야 합니다(택일, 부부 합산 가능).',
                        '정부기관 및 지방자치단체의 초청 장학생은 원칙적으로 동반 부모 사증 발급이 불가합니다.',
                        '신청인의 거주국 또는 외국인유학생의 최종학교 소재지 관할 공관에서 신청하는 것이 원칙입니다.'],
         conditions_en=['You must be able to cover living costs in Korea (one year: twice the annual living-cost standard for international students, per person).',
                        'Nationals of the 21 listed countries need annual income of at least last year\'s GNI or assets at or above the median level under the National Basic Living Security Act (either; spouses may combine).',
                        'Parents of scholarship students invited by government bodies or local governments are in principle not issued this visa.',
                        'Apply in principle at the mission covering your country of residence or the student\'s last school.'],
         docs=visa_app() + [
             item('f1_admission_or_enrollment', anchor='입학허가서 또는 재학증명서'),
             item('f1_family_relation_original', anchor='가족관계 입증서류 (원본 및 번역본 첨부, 호구부, 출생증명서 등)'),
             item('f1_living_cost_proof', anchor='국내 체류비용 부담능력 입증서류 (3개월 이상 계속 예치된'),
             item('f1_financial_capacity_proof', 'CONDITIONAL_REQUIRED', anchor='재정능력 입증서류 (불법체류 다발국가 국민에 한함)',
                  applies_when_ko='불법체류 다발국가 국민인 경우', applies_when_en='Nationals of high-overstay countries'),
         ],
         notes_ko=[CONSUL_NOTE_KO, OFFICER_NOTE_KO], notes_en=[CONSUL_NOTE_EN, OFFICER_NOTE_EN])

guidance('F-1-21', 'visa_issuance', manual=VISA, section=f'{VISA_CH} — 공관장 재량 사증 2. 주한 외국공관원의 동일국적 가사보조인(F-1-21)',
         anchor='주한 외국공관원의 가사보조인으로서 공관원과 동일국적을 가진 자에 대한 체류기간 1년 이하의 단수사증 (F-1-21)',
         summary_ko='주한 외국공관원과 같은 국적의 가사보조인은 재외공관에서 체류기간 1년 이하의 단수 사증을 신청합니다. 주재국 이외의 국가 국민은 법무부장관의 승인이나 사증발급인정서를 통해 사증이 발급됩니다.',
         summary_en='A domestic helper of the same nationality as the foreign mission member applies at the overseas mission for a single-entry visa of up to one year. Nationals of other countries get the visa through Ministry of Justice approval or a visa issuance confirmation.',
         period_ko='체류기간 1년 이하, 단수', period_en='Up to 1 year, single entry',
         docs=visa_app() + [
             item('f1_mission_coop_letter', anchor='외국공관의 협조공문'),
             item('employment_contract', anchor='③ 고용계약서', role='employer'),
             item('f1_employer_id_copy', anchor='고용인의 신분증명서 사본'),
         ],
         notes_ko=[CONSUL_NOTE_KO, OFFICER_NOTE_KO], notes_en=[CONSUL_NOTE_EN, OFFICER_NOTE_EN])

guidance('F-1-22', 'visa_issuance', manual=VISA, covers=['F-1-23', 'F-1-24'],
         section=f'{VISA_CH} — 공관장 재량 사증 3. 투자가 및 전문인력의 외국인 가사보조인(F-1-22, F-1-23, F-1-24)',
         anchor='투자가 및 전문인력의 외국인 가사보조인(F-1-22, F-1-23, F-1-24)',
         summary_ko='투자가 및 전문인력이 신청 시점 기준 1년 이상 국외에서 고용한 가사보조인은 자국 소재 한국공관에서 체류기간 1년 이하의 단수 사증을 신청합니다(고액투자자 F-1-22, 첨단투자자 F-1-23, 전문인력 F-1-24).',
         summary_en='A domestic helper employed abroad by an investor or professional for at least one year at the time of application applies at the Korean mission in their own country for a single-entry visa of up to one year (high-value investor F-1-22, advanced-technology investor F-1-23, professional F-1-24).',
         period_ko='체류기간 1년 이하, 단수', period_en='Up to 1 year, single entry',
         conditions_ko=['영주권 취득 또는 취업 등으로 제3국에서 장기 거주 중인 경우에는 거주국 소재 한국공관에 신청할 수 있습니다.',
                        "'우수 전문인력' 중 법무부장관의 승인 사항은 승인을 받은 후 사증이 발급됩니다."],
         conditions_en=['If you live long-term in a third country (permanent residence, employment, etc.) you may apply at the Korean mission there.',
                        "For 'top professionals' cases that need Ministry of Justice approval, the visa is issued after approval."],
         docs=visa_app(anchor=VISA_APP + ' ② 외국인투자신고서') + [
             item('fdi_report', anchor='외국인투자신고서(법인등기사항전부증명서 또는 사업자등록증사본) 또는 투자기업등록증사본', role='employer'),
             item('venture_docs', 'ALTERNATIVE_DOCUMENT', anchor='벤처기업확인서 또는 예비벤처기업확인서', role='employer',
                  applies_when_ko='영 별표 1의 17. 기업투자(D-8)란의 나목에 해당하는 고용주인 경우 외국인투자신고서 등을 갈음', applies_when_en='Replaces the investment documents for employers under D-8 item (b) of Annex 1 of the Enforcement Decree'),
             item('f1_ip_rights_proof', 'ALTERNATIVE_DOCUMENT', anchor='산업재산권, 그 밖에 이에 준하는 기술과 그 사용에 관한 권리 등을 보유하고 있음을 입증하는 서류',
                  applies_when_ko='영 별표 1의 17. 기업투자(D-8)란의 나목에 해당하는 고용주인 경우 외국인투자신고서 등을 갈음', applies_when_en='Replaces the investment documents for employers under D-8 item (b) of Annex 1 of the Enforcement Decree'),
             item('employer_cert', anchor='고용주의 재직증명서 (신분증명서)', role='employer'),
             item('f1_employer_income_proof', anchor='고용주의 소득 요건 입증 자료'),
             item('f1_korean_staff_proof', 'CONDITIONAL_REQUIRED', anchor='고용중인 내국인 상시근로자 입증 서류 (투자금액 미화 50만불 미만자)',
                  applies_when_ko='투자금액이 미화 50만불 미만인 경우', applies_when_en='Investment under USD 500,000'),
             item('domestic_help_contract', anchor='가사보조인 고용계약서', role='employer'),
             item('guarantor', anchor='⑦ 신원보증서'),
             item('f1_helper_education_proof', anchor='가사보조인의 졸업증명서 등 학력을 입증할 수 있는 서류'),
             item('f1_helper_1y_service_proof', anchor='1년 이상 고용주의 가사보조인으로 근무한 사실을 입증하는 서류'),
         ],
         notes_ko=[CONSUL_NOTE_KO, OFFICER_NOTE_KO], notes_en=[CONSUL_NOTE_EN, OFFICER_NOTE_EN])

guidance('F-1-3', 'visa_issuance', manual=VISA, section=f'{VISA_CH} — 공관장 재량 사증 4. 외교(A-1)~협정(A-3) 자격자의 비세대 동거인(F-1-3)',
         anchor='세대에 속하지 아니한 자에 대한 체류기간 1년 이하의 방문동거(F-1-3) 단수사증',
         summary_ko='외교(A-1)~협정(A-3) 자격에 해당하는 사람의 동거인으로서 그 세대에 속하지 않는 사람은 재외공관에서 체류기간 1년 이하의 방문동거(F-1-3) 단수 사증을 신청합니다.',
         summary_en='A cohabitant of an A-1 to A-3 holder who is not part of that household applies at the overseas mission for a single-entry F-1-3 visa of up to one year.',
         period_ko='체류기간 1년 이하, 단수', period_en='Up to 1 year, single entry',
         conditions_ko=['SOFA 해당자의 배우자 및 21세 미만의 동반자녀와, 생계비의 반액 이상을 합중국 군대의 구성원 또는 군속에 의존하는 부모 및 21세 이상의 자녀 또는 기타 친척은 협정(A-3) 자격에 해당합니다.'],
         conditions_en=['Spouses and children under 21 of SOFA personnel, and parents, children 21 or older or other relatives who depend on a US forces member or civilian employee for at least half their living costs, fall under A-3 instead.'],
         docs=visa_app(anchor='표준규격사진 1매, 수수료 ② 친족관계를 입증하는 서류(호구부') + [
             item('f1_kinship_proof', anchor='친족관계를 입증하는 서류(호구부, 거민신분증 등)'),
             item('f1_cohabitation_need_proof', anchor='동거 또는 장기체류 필요성을 입증하는 서류'),
         ],
         notes_ko=[CONSUL_NOTE_KO, OFFICER_NOTE_KO], notes_en=[CONSUL_NOTE_EN, OFFICER_NOTE_EN])

guidance('F-1-5', 'visa_issuance', manual=VISA, section=f'{VISA_CH} — 공관장 재량 사증 7. 자녀양육 지원 등 목적으로 입국하는 결혼이민자의 부모 등 가족(F-1-5)',
         anchor='대한 방문동거(F-1-5, 90일 이하) 단수 사증', doc_page_window=4,
         summary_ko='자녀양육 지원 또는 인도적 사정(중증질환·중증장애)을 위해 결혼이민자의 부 또는 모(부모 모두 입국할 수 없고 본인에게 미성년 자녀가 없으면 형제자매, 전혼관계 출생 자녀)를 초청하는 90일 이하 단수 사증입니다. 인도적 사정은 중증질환·장애 증명서류를 추가로 냅니다.',
         summary_en='A single-entry visa of up to 90 days for a marriage migrant\'s father or mother (or, if neither parent can come and the invitee has no minor child, a sibling or a child from a previous marriage) invited to help raise a child or on humanitarian grounds (severe illness or disability). Humanitarian cases add proof of the illness or disability.',
         period_ko='90일 이하, 단수', period_en='Up to 90 days, single entry',
         conditions_ko=['초청 자격: 한국인 배우자 또는 국적·영주(F-5) 자격을 취득한 결혼이민자, 한부모 가족 결혼이민자. 인도적 사정은 결혼이민자, 한국인 배우자, 자녀 중 중증질환자 또는 중증장애인이 있는 경우입니다.',
                        '자녀양육 지원 초청 시기: 신청일 기준 결혼이민자(또는 그 배우자)가 임신했거나 자녀가 만 9세가 되는 해의 9월말까지(한부모·다자녀 가족은 만 12세가 되는 해의 9월말까지)입니다.',
                        '자녀양육 지원은 자녀 1명당 최대 2회 초청할 수 있습니다.',
                        '초청 인원은 1명이며, 부모에 한해 동시·순차 초청이 가능합니다.',
                        '초청인 또는 피초청인에게 국내법 위반 사실 등이 확인되면 일정 기간 F-1-5 사증 발급 목적의 초청이 제한됩니다.'],
         conditions_en=['Eligible inviters: the Korean spouse or a marriage migrant who has acquired nationality or F-5, and single-parent marriage migrants. Humanitarian grounds apply when the migrant, the Korean spouse or a child has a severe illness or severe disability.',
                        'Childcare invitations: on the application date the migrant (or spouse) is pregnant, or until the end of September of the year the child turns 9 (12 for single-parent and multi-child families).',
                        'Childcare invitations are limited to two per child.',
                        'One person may be invited; only parents may be invited together or one after the other.',
                        'If the inviter or invitee has broken Korean law, invitations for an F-1-5 visa are restricted for a period.'],
         docs=visa_app(anchor='(신청인) 사증발급신청서 (별지 제17호 서식), 여권, 표준규격사진 1매, 수수료') + [
             item('f1_inviter_id_copy', anchor='(초청인) 신분증 사본, 초청장'),
             item('f1_invitation', anchor='초청장, 신원보증서(보증기간 : 입국한 날로부터 3년)'),
             item('guarantor', anchor='신원보증서(보증기간 : 입국한 날로부터 3년)', role='inviter', validity_period='입국한 날로부터 3년 보증'),
             item('f1_illegal_stay_pledge', anchor='불법체류･취업 방지 서약서'),
             item('inviter_basic_cert', anchor='초청인의 기본증명서, 가족관계증명서, 혼인관계증명서, 주민등록표(등본)', role='inviter'),
             item('inviter_family_cert', anchor='초청인의 기본증명서, 가족관계증명서, 혼인관계증명서, 주민등록표(등본)', role='inviter'),
             item('inviter_marriage_cert', anchor='초청인의 기본증명서, 가족관계증명서, 혼인관계증명서, 주민등록표(등본)', role='inviter'),
             item('inviter_resident_reg', anchor='초청인의 기본증명서, 가족관계증명서, 혼인관계증명서, 주민등록표(등본)', role='inviter'),
             item('child_family_cert', anchor='자녀명의 가족관계증명서(임신한 경우 임신진단서 또는 산모수첩)', role='inviter',
                  notes_ko='자녀가 2명 이상이면 모든 자녀의 가족관계증명서를 제출합니다.', notes_en='Submit one for every child if there are two or more.'),
             item('pregnancy_cert', 'ALTERNATIVE_DOCUMENT', anchor='임신한 경우 임신진단서 또는 산모수첩', role='inviter',
                  applies_when_ko='임신한 경우 자녀 명의 가족관계증명서를 대신함', applies_when_en='Replaces the child\'s certificate during pregnancy'),
             item('full_adoption_cert', 'CONDITIONAL_REQUIRED', anchor='자녀가 친양자의 경우 초청인의 친양자입양관계증명서 추가 제출', role='inviter',
                  applies_when_ko='자녀가 친양자인 경우', applies_when_en='If the child is a full adoptee'),
             item('f1_home_family_proof', anchor='결혼이민자의 직계가족 및 형제자매 모두를 확인할 수 있는 가족관계 증명서류'),
             item('f1_parents_unable_proof', 'CONDITIONAL_REQUIRED', anchor='결혼이민자의 부모 모두가 사망하거나 질병, 60세 이상 고령 등의 사유로 입국이 불가함을 확인할 수 있는 서류',
                  applies_when_ko='피초청인이 부모 이외 본국 가족인 경우', applies_when_en='If the invitee is a family member other than a parent'),
             item('child_enrollment', 'CONDITIONAL_REQUIRED', anchor='(자녀가 취학연령인 경우) 재학증명서', role='inviter',
                  applies_when_ko='자녀양육 지원 목적이고 자녀가 취학연령인 경우', applies_when_en='Childcare purpose and the child is of school age'),
             item('severe_illness_proof', 'CONDITIONAL_REQUIRED', anchor='(중증질환･장애 증명서류)', role='inviter',
                  applies_when_ko='인도적 사정(중증질환·중증장애) 목적인 경우', applies_when_en='Humanitarian purpose (severe illness or disability)'),
         ],
         notes_ko=[CONSUL_NOTE_KO, OFFICER_NOTE_KO], notes_en=[CONSUL_NOTE_EN, OFFICER_NOTE_EN])

guidance('F-1-D', 'visa_issuance', manual=VISA, section=f'{VISA_CH} — 공관장 재량 사증 8. 디지털노마드(워케이션) 비자(F-1-D)',
         anchor='디지털노마드(워케이션) 비자(F-1-D)에 대한 사증발급',
         summary_ko='해외 사업체 소유자 또는 해외기업 소속으로 원격근무가 가능하고 1년 이상 동일 업종에 근무하는 만 18세 이상 외국인(동반가족 자녀는 연령 예외)과 그 가족에게 유효기간 1년의 복수 사증이 발급됩니다.',
         summary_en='Foreigners aged 18 or over (accompanying children excepted) who own an overseas business or work for an overseas company, can work remotely and have worked in the same field for at least one year, and their families, receive a multiple-entry visa valid for one year.',
         period_ko='복수사증, 유효기간 1년', period_en='Multiple-entry visa valid for 1 year',
         conditions_ko=['소득요건: 신청일 기준 한국은행 고시 전년도 1인당 GNI를 기준으로, 수도권은 18~34세 GNI 1.5배·35세 이상 GNI 2배, 비수도권 및 인구감소(관심)지역은 각각 GNI 1배·1.5배입니다.',
                        '수도권에 가족(배우자 및 미성년 자녀)을 동반하면 연령과 관계없이 GNI 2배(비수도권 및 인구감소(관심)지역은 GNI 1.5배)가 적용됩니다.',
                        '병원 치료 및 본국 후송을 위한 보장액 1억원 이상의 개인 의료보험에 가입해야 합니다.'],
         conditions_en=['Income test, based on last year\'s per-capita GNI published by the Bank of Korea: in the capital region 1.5x GNI for ages 18–34 and 2x for 35+; outside the capital region or in depopulation areas 1x and 1.5x.',
                        'Bringing a spouse or minor children to the capital region requires 2x GNI regardless of age (1.5x outside the capital region or in depopulation areas).',
                        'Private medical insurance covering at least KRW 100 million for treatment and repatriation is required.'],
         docs=visa_app() + [
             item('employment_cert_1y', anchor='재직증명서(동일 업종에 1년 이상 종사 입증 필요)', role='employer'),
             item('income_proof', anchor='급여명세서, 잔고증명 등 소득 증빙 서류'),
             item('criminal_record_health_ins', anchor='범죄경력증명서*, 의료보험 가입 증명서',
                  notes_ko='해외범죄경력증명서 제출기준은 매뉴얼의 F-1-D 붙임을 따릅니다.', notes_en='Overseas criminal-record rules follow the F-1-D annex in the manual.'),
             item('family_relation', 'CONDITIONAL_REQUIRED', anchor='가족관계 입증서류(가족 동반시)', applies_when_ko='가족을 동반하는 경우', applies_when_en='If family members accompany you'),
             item('f1_regional_stay_proof_visa', 'CONDITIONAL_REQUIRED', anchor='(해당 시) 비수도권 및 인구감소(관심)지역에 체류할 예정임을 입증하는 서류(1개월 이상 임대차 계약서, 워케이션 특화시설 또는 숙소 예약확인서 등)',
                  applies_when_ko='비수도권·인구감소(관심)지역 체류로 완화된 소득요건을 적용받는 경우', applies_when_en='If claiming the relaxed income test for staying outside the capital region or in a depopulation area'),
             item('f1_other_consul_docs', 'MAY_BE_REQUESTED_BY_OFFICER', anchor='기타 재외공관장이 필요하다고 인정하는 서류'),
         ],
         notes_ko=[CONSUL_NOTE_KO, OFFICER_NOTE_KO], notes_en=[CONSUL_NOTE_EN, OFFICER_NOTE_EN])

guidance('F-1-51', 'visa_issuance', manual=VISA, section=f'{VISA_CH} — 공관장 재량 사증 9. 국제 입양 외국인(국내로 입양 아동, F-1-51)',
         anchor='국제 입양 외국인(국내로 입양 아동, F-1-51)에 대한 사증발급',
         summary_ko='외국에 상거소를 두고 국내 입양 절차가 진행 중이거나 완료된 18세 미만 외국국적 아동이 대상입니다. 입양 절차가 진행 중이면 2년(단수) 사증이, 완료된 경우에는 거주(F-2-3) 또는 영주(F-5-3) 자격 지침이 적용됩니다.',
         summary_en='For foreign children under 18 habitually resident abroad whose adoption into Korea is in progress or completed. A 2-year single-entry visa is issued while the adoption is in progress; once completed, the F-2-3 or F-5-3 rules apply.',
         period_ko='입양 절차 진행 중: 2년(단수)', period_en='Adoption in progress: 2 years (single entry)',
         docs=visa_app(anchor='여권, 사증발급신청서, 표준규격사진 1매, 수수료') + [
             item('f1_intl_adoption_proof', anchor='양국의 국제입양성립(진행)을 입증할 수 있는 서류'),
             item('f1_child_identity_proof', anchor='아동의 신원을 입증할 수 있는 서류'),
             item('f1_adoptive_parent_identity', anchor='양부모의 신원을 입증할 수 있는 서류'),
             residence(anchor='체류지 입증서류(임대차계약서 등)', alts=LEASE_ONLY),
             item('f1_criminal_record_14', 'CONDITIONAL_REQUIRED', anchor='만 14세 이상인 경우 주재국 정부발행 범죄경력증명서',
                  applies_when_ko='만 14세 이상인 경우', applies_when_en='Age 14 or over',
                  does_not_apply_when_ko='만 14세 미만에 입국하여 만 14세 이후 해외에서 6개월 이상 연속 체류하지 않은 사람, 본국 법령상 발급이 어려운 사람(입증 필요)', does_not_apply_when_en='Entered before 14 and has not stayed abroad 6+ consecutive months since turning 14, or cannot obtain one under home-country law (must be proven)'),
             item('tb_cert', 'CONDITIONAL_REQUIRED', anchor='결핵고위험국가의 경우 결핵진단서(6세 미만 소아 제출면제)',
                  applies_when_ko='결핵고위험국가 국민인 경우', applies_when_en='Nationals of TB high-risk countries',
                  does_not_apply_when_ko='6세 미만 소아', does_not_apply_when_en='Children under 6'),
         ],
         conditions_ko=[FOREIGN_DOC_NOTE_KO + ' 접수일 기준 6개월 이내 발급된 것이어야 합니다.'],
         conditions_en=[FOREIGN_DOC_NOTE_EN + ' They must be issued within 6 months before filing.'],
         notes_ko=[OFFICER_NOTE_KO], notes_en=[OFFICER_NOTE_EN])

# ==========================================================================
# 사증발급인정서 (visa manual — 사증발급인정서 발급대상)
# ==========================================================================
guidance('F-1-15', 'visa_issuance_confirmation', manual=VISA, section=f'{VISA_CH} — 사증발급인정서 발급대상 1. 우수인재, 투자자 및 유학생 부모(F-1-15)',
         anchor='초청자가 관할 출입국ㆍ외국인청(사무소ㆍ출장소))에  방문동거(F-1-15), 90일 이하 단수 사증발급인정서 신청',
         summary_ko='우수인재·투자자·유학생인 초청자가 본인 또는 배우자의 부모(최대 2명 동시 체류)를 위해 관할 출입국·외국인관서에 방문동거(F-1-15) 90일 이하 단수 사증발급인정서를 신청합니다.',
         summary_en='An inviter who is top talent, an investor or a graduate student applies at the local immigration office for a single-entry F-1-15 visa issuance confirmation (up to 90 days) for their own or their spouse\'s parents (up to two at a time).',
         period_ko='90일 이하, 단수', period_en='Up to 90 days, single entry',
         conditions_ko=['(우수인재) D-5, D-7, D-8, D-9, E-1~E-7 자격자로서 연간 소득이 전년도 GNI 2배 이상인 사람(해당 활동범위를 유지하며 F-2, F-5 등으로 변경한 경우 포함)',
                        '(투자자) 국내에 3억원 이상을 투자한 후 외국인등록을 하고 6개월 이상 계속 국내 체류 중인 사람',
                        '(유학생) 국내 대학의 석·박사과정에서 6개월 이상 유학하며 체류 중인 사람. 피초청자를 포함한 동반가족이 3명 이상이면 학비 외에 전년도 GNI 50% 이상의 연간 체류경비 보유를 입증해야 합니다.'],
         conditions_en=['(Top talent) D-5, D-7, D-8, D-9 or E-1 to E-7 holders with annual income of at least twice last year\'s GNI (including those who changed to F-2, F-5, etc. while keeping that activity)',
                        '(Investor) invested KRW 300 million or more in Korea, registered, and has stayed 6+ months continuously',
                        '(Student) in a Korean master\'s or doctoral program for 6+ months. With three or more accompanying family members including the invitee, proof of annual living funds of at least 50% of last year\'s GNI beyond tuition is required.'],
         docs=cert_app() + [
             item('f1_invitation_reason', anchor='초청사유서(취업활동을 하지 않겠다는 내용 기재)'),
             item('guarantor', anchor='③ 신원보증서', role='inviter'),
             item('family_relation', anchor='④ 가족관계입증서류'),
             item('f1_income_investment_proof', anchor='소득/투자금/체류경비 입증서류'),
         ],
         notes_ko=[OFFICE_NOTE_KO, OFFICER_NOTE_KO], notes_en=[OFFICE_NOTE_EN, OFFICER_NOTE_EN])

guidance('F-1-22', 'visa_issuance_confirmation', manual=VISA, covers=['F-1-24'],
         section=f'{VISA_CH} — 사증발급인정서 발급대상 2. 고액투자가(F-1-22) 및 해외우수인재(F-1-24)의 가사보조인',
         anchor='고액투자가(F-1-22) 및 해외우수인재(F-1-24)의 가사보조인',
         summary_ko="고액투자가(F-1-22)·해외우수인재(F-1-24)의 가사보조인 중 '공관장 재량으로 발급할 수 있는 사증' 대상이 아닌 사람은 사증발급인정서를 통해 체류기간 90일 이하 단수 사증을 받습니다.",
         summary_en="Domestic helpers of high-value investors (F-1-22) and top overseas talent (F-1-24) who do not fall under the consul-discretion visa receive a single-entry visa of up to 90 days through a visa issuance confirmation.",
         period_ko='체류기간 90일 이하, 단수', period_en='Up to 90 days, single entry',
         docs=cert_app() + [
             item('fdi_report', anchor='외국인투자신고서(법인등기사항전부증명서 또는 사업자등록증) 또는 투자기업등록증사본', role='employer'),
             item('venture_docs', 'ALTERNATIVE_DOCUMENT', anchor='벤처기업확인서 또는 예비벤처기업확인서', role='employer',
                  applies_when_ko='영 별표 1의 17. 기업투자(D-8)란의 나목에 해당하는 고용주인 경우 외국인투자신고서 등을 갈음', applies_when_en='Replaces the investment documents for employers under D-8 item (b) of Annex 1 of the Enforcement Decree'),
             item('f1_ip_rights_proof', 'ALTERNATIVE_DOCUMENT', anchor='산업재산권, 그 밖에 이에 준하는 기술과 그 사용에 관한 권리 등을 보유하고 있음을 입증하는 서류',
                  applies_when_ko='영 별표 1의 17. 기업투자(D-8)란의 나목에 해당하는 고용주인 경우 외국인투자신고서 등을 갈음', applies_when_en='Replaces the investment documents for employers under D-8 item (b) of Annex 1 of the Enforcement Decree'),
             item('f1_employment_contract_copy', anchor='③ 고용계약서 사본'),
             item('employer_cert', anchor='④ 고용주의 재직증명서 (신분증명서)', role='employer'),
             item('guarantor', anchor='⑤ 신원보증서'),
             item('f1_helper_education_proof', anchor='⑥ 가사보조인의 졸업증명서 등 학력을 입증할 수 있는 서류'),
             item('f1_employer_annual_income_proof', anchor='고용주의 연간 소득 수준을 입증할 수 있는 자료'),
             item('f1_korean_staff_proof', 'CONDITIONAL_REQUIRED', anchor='투자금액 미화 50만불 미만자 추가 서류',
                  applies_when_ko='투자금액이 미화 50만불 미만인 경우', applies_when_en='Investment under USD 500,000'),
         ],
         notes_ko=[OFFICE_NOTE_KO, OFFICER_NOTE_KO], notes_en=[OFFICE_NOTE_EN, OFFICER_NOTE_EN])

guidance('F-1-21', 'visa_issuance_confirmation', manual=VISA, section=f'{VISA_CH} — 사증발급인정서 발급대상 3. 주한 외국공관원의 가사보조인(F-1-21)',
         anchor='주한외국공관원과 동일국적이 아닌 가사보조인을 초청하는 경우',
         summary_ko='주한외국공관원과 같은 국적이 아닌 가사보조인을 초청하는 경우 사증발급인정서를 통해 방문동거(F-1-21) 체류기간 90일 이하 단수 사증을 받습니다. 같은 국적의 가사보조인은 공관장 재량으로 발급합니다.',
         summary_en='A domestic helper who is not of the same nationality as the foreign mission member receives a single-entry F-1-21 visa of up to 90 days through a visa issuance confirmation. Same-nationality helpers are issued at the consul\'s discretion.',
         period_ko='체류기간 90일 이하, 단수', period_en='Up to 90 days, single entry',
         docs=cert_app() + [
             item('f1_mission_request_letter', anchor='② 외국공관의 요청공문'),
             item('f1_employment_contract_copy', anchor='③ 고용계약서 사본'),
             item('f1_employer_diplomat_id_copy', anchor='고용인의 외교관신분증 사본'),
         ],
         notes_ko=[OFFICE_NOTE_KO, OFFICER_NOTE_KO], notes_en=[OFFICE_NOTE_EN, OFFICER_NOTE_EN])

# ==========================================================================
# 체류자격 변경허가 (stay manual)
# ==========================================================================
F1_CHG_DIPLO = '주한 외국공관 등에 주재근무하는 자의 비세대동거인 및 가사보조인에 대한 방문동거(F-1) 체류자격 변경허가'
guidance('F-1-3', 'status_change', section=f'{STAY_CH} — 체류자격 변경허가 1. {F1_CHG_DIPLO} (비세대동거인)', anchor=F1_CHG_DIPLO,
         summary_ko='외교(A-1)·공무(A-2)·협정(A-3) 자격에 해당하는 사람의 동거인으로서 그 세대에 속하지 않는 사람이 방문동거로 변경할 때는 주한 해당공관의 요청공문, 공관원신분증, 가족 또는 친족관계 입증서류를 냅니다.',
         summary_en='A cohabitant of an A-1, A-2 or A-3 holder who is not part of that household changes to F-1 with a request letter from the mission in Korea, the mission member\'s ID and proof of family or kinship.',
         docs=stay_app('신청서(별지 34호 서식), 여권, 표준규격사진 1매, 수수료') + [
             item('f1_mission_request_letter_kr', anchor='주한 해당공관의 요청공문'),
             item('diplomat_id', anchor='③ 공관원신분증', role='principal_holder'),
             item('f1_family_kinship_proof', anchor='가족 또는 친족관계 입증서류'),
         ],
         notes_ko=[OFFICER_NOTE_KO], notes_en=[OFFICER_NOTE_EN])

guidance('F-1-21', 'status_change', section=f'{STAY_CH} — 체류자격 변경허가 1. {F1_CHG_DIPLO} (외교·공무 자격자의 가사보조인)', anchor=F1_CHG_DIPLO,
         summary_ko='주한 외국공관원(외교·공무 자격자)의 가사보조인이 방문동거로 변경할 때는 주한 해당공관의 요청공문, 고용계약서, 고용인의 외교관신분증명서 사본을 냅니다.',
         summary_en='A domestic helper of a foreign mission member (A-1/A-2 holder) changes to F-1 with a request letter from the mission in Korea, the employment contract and a copy of the employer\'s diplomatic ID.',
         docs=stay_app('신청서(별지 34호 서식), 여권, 표준규격사진 1매, 수수료') + [
             item('f1_mission_request_letter_kr', anchor='주한 해당공관의 요청공문'),
             item('employment_contract', anchor='③ 고용계약서', role='employer'),
             item('f1_employer_diplomat_id_copy_kr', anchor='고용인의 외교관신분증명서 사본'),
         ],
         notes_ko=[OFFICER_NOTE_KO], notes_en=[OFFICER_NOTE_EN])

guidance('F-1-22', 'status_change', covers=['F-1-23', 'F-1-24'], state='GENERALLY_NOT_PERMITTED', completeness='SOURCE_ONLY',
         section=f'{STAY_CH} — 체류자격 변경허가 1. 가. 대상자 (투자가 및 전문인력의 외국인 가사보조인)',
         anchor='투자가 및 전문인력의 외국인 가사보조인은 국내에서 체류자격 변경불가',
         summary_ko='투자가 및 전문인력의 외국인 가사보조인은 국내에서 체류자격을 변경할 수 없으며, 공관 사증발급이나 사증발급인정서를 통해 입국해야 합니다.',
         summary_en='Foreign domestic helpers of investors and professionals cannot change status inside Korea; they must enter with a visa from a mission or through a visa issuance confirmation.')

guidance('F-1-6', 'status_change', section=f'{STAY_CH} — 체류자격 변경허가 2. 혼인단절 결혼이민자 가사정리를 위한 방문동거 체류자격 변경허가',
         anchor='혼인단절 결혼이민자 가사정리를 위한 방문동거 체류자격 변경허가',
         summary_ko='국민과 혼인이 단절되었으나 혼인단절자(F-6-3)에 해당하지 않는 사람으로서 재산분할·가사정리 등으로 국내 체류가 불가피한 사람의 변경입니다. 6개월 범위 내에서 허가되며 F-1-6 자격의 체류허가 기간은 자격변경일로부터 1년까지입니다.',
         summary_en='For people whose marriage to a Korean ended but who do not qualify as F-6-3 and must stay for property division or household matters. Granted within 6 months; F-1-6 stay is allowed only until one year from the status change.',
         period_ko='6개월 범위 내 · 자격변경일로부터 1년까지', period_en='Within 6 months; at most 1 year from the status change',
         conditions_ko=['혼인단절 전 정상적인 혼인 생활 유지 여부와 국내 체류의 불가피성 여부 등을 심사합니다.'],
         conditions_en=['The office reviews whether a normal married life was maintained before the marriage ended and whether the stay is unavoidable.'],
         docs=stay_app('신청서(별지 제34호 서식), 여권 및 외국인등록증, 사진 1매, 수수료', arc=True) + [
             item('guarantor', anchor='② 신원보증서 ③ 이혼 사실이 기재된 혼인관계 증명서'),
             item('f1_divorce_marriage_cert', anchor='이혼 사실이 기재된 혼인관계 증명서'),
             item('stay_necessity_proof', anchor='체류 불가피성에 대한 소명자료(사유서, 재산분할 관련 입증자료 등)'),
             item('other_officer_docs', 'MAY_BE_REQUESTED_BY_OFFICER', anchor='⑤ 기타 심사에 필요하다고 인정되는'),
             residence(anchor='⑥ 체류지 입증서류(임대차계약서, 숙소제공 확인서, 체류기간 만료예고 통지우편물, 공공요금 납부영수증, 기숙사비 영수증 등)'),
         ],
         notes_ko=[OFFICER_NOTE_KO], notes_en=[OFFICER_NOTE_EN])

F1_F27_DOCS_ANCHOR = '① 신청서(별지 제34호 서식), 여권, 표준규격사진 1매, 수수료'


def f1_f27_docs():
    return stay_app(F1_F27_DOCS_ANCHOR) + [
        item('birth_family_proof', anchor='출생증명서, 가족관계 소명 서류 등'),
        item('f27_grant_docs', anchor='점수제 우수인력(F-2-7) 거주자격 부여허가시 제출서류', role='principal_holder'),
        item('principal_passport_arc', anchor='점수제 우수인재(F-2-7)와 그 배우자의 여권 및 외국인등록증 사본', role='principal_holder'),
        item('principal_employment', anchor='점수제 우수인재(F-2-7)의 고용계약서 또는 재직증명서', role='principal_holder'),
        item('residence_proof', anchor='⑥ 체류지 입증서류'),
        item('guarantor', anchor='⑦ 신원보증서'),
        item('tb_cert', 'ADDITIONAL_IF_APPLICABLE', anchor='⑧ 결핵확인서(해당자)', applies_when_ko='결핵확인서 제출 대상자인 경우', applies_when_en='If you are subject to the TB certificate rule'),
    ]


guidance('F-1-12', 'status_change', section=f'{STAY_CH} — 체류자격 변경허가 4. 점수제 우수인재(F-2-7)의 배우자 또는 미성년자녀에 대한 방문동거 자격으로 변경허가',
         anchor='점수제 우수인재(F-2-7)의 배우자 또는 미성년자녀에 대한 방문동거 자격으로 변경허가',
         summary_ko='점수제 우수인재(F-2-7)의 연간소득이 최근 1인당 국민소득 미만인 경우 그 배우자 및 미성년 자녀가 방문동거로 변경하는 경우입니다. 거주(F-2-71) 자격 변경 기준에 따라 심사합니다.',
         summary_en='For the spouse and minor children of an F-2-7 points-system resident whose annual income is below the latest per-capita national income. Reviewed under the F-2-71 change criteria.',
         docs=f1_f27_docs(), notes_ko=[OFFICER_NOTE_KO], notes_en=[OFFICER_NOTE_EN])

guidance('F-1-4', 'status_change', section=f'{STAY_CH} — 체류자격 변경허가 4. 대한민국 국적의 혼외 미성년자 자녀 양육자(F-1-4)의 체류자격 변경허가',
         anchor='대한민국 국적의 혼외 미성년자 자녀 양육자(F-1-4)의 체류자격 변경허가',
         summary_ko='대한민국 국적인 혼외 미성년 자녀를 양육하는 외국인 부 또는 모로서 결혼이민(F-6) 등 다른 자격으로 체류할 수 없는 사람이 대상이며, 체류지 관할 청(사무소·출장소)에서 처리합니다.',
         summary_en='For a foreign father or mother raising a Korean-national minor child born out of wedlock who cannot stay under F-6 or another status. Handled by the local immigration office.',
         docs=stay_app('신청서(별지 34호서식), 여권, 표준규격사진 1매, 수수료') + [
             item('f1_korean_child_docs', anchor='국민인 자녀의 주민등록등본, 기본증명서(상세), 가족관계증명서(상세)'),
             item('residence_proof', anchor='③ 체류지 입증서류   ④ 결핵확인서(해당자)'),
             item('tb_cert', 'ADDITIONAL_IF_APPLICABLE', anchor='④ 결핵확인서(해당자)', applies_when_ko='결핵확인서 제출 대상자인 경우', applies_when_en='If you are subject to the TB certificate rule'),
         ],
         notes_ko=['필요하면 자녀의 출생증명서나 유전자감정결과서 등을 요구할 수 있습니다.', OFFICER_NOTE_KO],
         notes_en=["The office may ask for the child's birth certificate or a DNA test result if needed.", OFFICER_NOTE_EN])

guidance('F-1-13', 'status_change', section=f'{STAY_CH} — 체류자격 변경허가 5. 고등학교 이하의 외국인 유학생 동반부모에 대한 방문동거(F-1-13) 체류자격 변경허가',
         anchor='고등학교 이하의 외국인 유학생 동반부모에 대한 방문동거(F-1-13) 체류자격 변경허가',
         summary_ko='고등학교 이하 유학(D-4-3) 사증발급 대상 교육기관에서 입학허가를 받았거나 재학 중인 외국인유학생의 2촌 이내 친인척으로서 국내에 합법체류 중인 사람이 대상이며, 외국인유학생 체류기간 범위에서 2년 이내로 허가됩니다.',
         summary_en='For a relative within the second degree of an international student admitted to or enrolled in a school eligible for D-4-3, who is lawfully staying in Korea. Granted for up to 2 years within the student\'s period of stay.',
         period_ko='체류기간 2년 이내 (외국인유학생 체류기간 범위 내)', period_en='Up to 2 years (within the student\'s period of stay)',
         conditions_ko=['단기체류자격 소지자, 기술연수(D-3), 비전문취업(E-9), 선원취업(E-10), 기타(G-1), 방문취업(H-2) 자격 소지자는 체류자격 변경이 불가합니다.',
                        '국내 체류 비용(1년간 생활비: 외국인 유학생 연간 생활비 기준액의 2배 상당 금액, 1인 기준) 부담능력이 있어야 하며, 불법체류 다발국가 국민은 연간 소득이 전년도 GNI 이상이거나 자산이 중위 수준 이상이어야 합니다.',
                        '유학생의 유학경비를 부모의 체류비용 및 재정능력 심사자료로 중복 사용할 수 없습니다.'],
         conditions_en=['Holders of short-term statuses, D-3, E-9, E-10, G-1 or H-2 cannot change.',
                        'You must be able to cover living costs (one year: twice the annual living-cost standard for international students, per person); nationals of high-overstay countries also need annual income of at least last year\'s GNI or assets at or above the median level.',
                        "The student's own study funds cannot be counted again for the parent's living-cost or financial review."],
         docs=[item('app_form_34', anchor='신청서(별지 34호 서식), 여권, 외국인등록증(해당자), 표준규격사진 1매, 수수료'),
               item('passport', anchor='신청서(별지 34호 서식), 여권, 외국인등록증(해당자), 표준규격사진 1매, 수수료'),
               item('arc', 'ADDITIONAL_IF_APPLICABLE', anchor='외국인등록증(해당자)', applies_when_ko='외국인등록을 한 경우', applies_when_en='If you are registered'),
               item('photo', anchor='외국인등록증(해당자), 표준규격사진 1매, 수수료'),
               item('fee', anchor='외국인등록증(해당자), 표준규격사진 1매, 수수료'),
               item('f1_admission_or_enrollment', anchor='외국인유학생 입학허가서 또는 재학증명서'),
               item('family_relation', anchor='③ 가족관계 입증서류',
                    notes_ko='원본을 제출하고(번역본 첨부 원칙), 부모의 영문성명을 알 수 있는 여권 사본 등을 첨부합니다.', notes_en="Submit the original (with a translation as a rule) and attach a passport copy or similar showing the parent's name in English."),
               item('f1_living_cost_proof', anchor='국내 체류비용 부담능력 입증서류 (3개월 이상 계속 예치된'),
               item('f1_financial_capacity_proof', 'CONDITIONAL_REQUIRED', anchor='재정능력 입증서류 (불법체류 다발국가 국민에 한함)',
                    applies_when_ko='불법체류 다발국가 국민인 경우', applies_when_en='Nationals of high-overstay countries')],
         notes_ko=[OFFICER_NOTE_KO], notes_en=[OFFICER_NOTE_EN])

guidance('F-1-16', 'status_change', section=f'{STAY_CH} — 체류자격 변경허가 9. 난민인정자의 배우자 및 미성년 자녀에 대한 방문동거(F-1-16) 체류자격 변경허가',
         anchor='난민인정자의 배우자 및 미성년 자녀에 대한 방문동거(F-1-16) 체류자격 변경허가',
         summary_ko='난민인정자의 배우자 및 미성년 자녀(배우자가 있는 미성년 자녀 제외)는 난민인정자의 체류기간 범위에서 최대 2년의 체류기간으로 변경허가를 받습니다.',
         summary_en="Spouses and minor children of recognized refugees (excluding married minors) change status for up to 2 years within the refugee's period of stay.",
         period_ko='난민인정자의 체류기간 범위 내 최대 2년', period_en="Up to 2 years within the refugee's period of stay",
         docs=stay_app('신청서(별지 34호 서식), 여권 및 외국인등록증, 표준규격사진 1매, 수수료', arc=True) + [
             item('f1_refugee_cert', anchor='배우자 또는 그 부모의 난민인정증명서'),
             item('f1_refugee_family_proof', anchor='난민인정자의 가족임을 입증하는 서류'),
             residence(anchor='교회·난민지원시설· 인권단체·UNHCR 등의 주거확인서', alts=RESIDENCE_ALTS + [{'ko': '교회·난민지원시설·인권단체·UNHCR 등의 주거확인서', 'en': 'Housing confirmation from a church, refugee shelter, human-rights group or UNHCR'}]),
         ],
         notes_ko=[OFFICER_NOTE_KO], notes_en=[OFFICER_NOTE_EN])

guidance('F-1-51', 'status_change', section=f'{STAY_CH} — 체류자격 변경허가 11. 국제 입양 외국인(국내로 입양 아동, F-1-51)에 대한 체류자격 변경허가',
         anchor='국제 입양 외국인(국내로 입양 아동, F-1-51)에 대한 체류자격 변경허가',
         summary_ko='국내 입양 절차가 진행 중이거나 완료된 18세 미만 외국국적 아동으로서 무사증 또는 단기방문(C-3) 사증으로 입국한 뒤 변경하려는 경우입니다. 입양 절차 진행 중이면 2년이 허가되고, 완료되면 거주(F-2-3) 또는 영주(F-5-3) 자격 지침이 적용됩니다.',
         summary_en='For foreign children under 18 whose adoption into Korea is in progress or completed and who entered visa-free or on a C-3 visa. Two years are granted while the adoption is in progress; once completed, the F-2-3 or F-5-3 rules apply.',
         period_ko='입양 절차 진행 중: 2년', period_en='Adoption in progress: 2 years',
         docs=[item('passport', anchor='여권, 통합신청서, 표준규격사진 1매, 수수료'), item('app_form_34', anchor='여권, 통합신청서, 표준규격사진 1매, 수수료'),
               item('photo', anchor='여권, 통합신청서, 표준규격사진 1매, 수수료'), item('fee', anchor='여권, 통합신청서, 표준규격사진 1매, 수수료'),
               item('f1_intl_adoption_proof', anchor='양국의 국제입양성립(진행)을 입증할 수 있는 서류'),
               item('f1_child_identity_proof', anchor='아동의 신원을 입증할 수 있는 서류'),
               item('f1_adoptive_parent_identity', anchor='양부모의 신원을 입증할 수 있는 서류'),
               item('f1_enrollment_if_applicable', 'ADDITIONAL_IF_APPLICABLE', anchor='(해당시) 재학증명서 등 재학 중임을 알 수 있는 서류', applies_when_ko='재학 중인 경우', applies_when_en='If enrolled in school'),
               residence(anchor='체류지 입증서류(임대차계약서 등)', alts=LEASE_ONLY),
               item('f1_criminal_record_14', 'CONDITIONAL_REQUIRED', anchor='만 14세 이상인 경우 주재국 정부발행 범죄경력증명서',
                    applies_when_ko='만 14세 이상인 경우', applies_when_en='Age 14 or over',
                    does_not_apply_when_ko='사증발급 시 제출한 경우, 만 14세 미만에 입국하여 만 14세 이후 해외에서 6개월 이상 연속 체류하지 않은 사람, 본국 법령상 발급이 어려운 사람(입증 필요)', does_not_apply_when_en='Already submitted for the visa; entered before 14 and has not stayed abroad 6+ consecutive months since turning 14; or cannot obtain one under home-country law (must be proven)'),
               item('tb_cert', 'CONDITIONAL_REQUIRED', anchor='결핵고위험국가의 경우 결핵진단서',
                    applies_when_ko='결핵고위험국가 국민인 경우', applies_when_en='Nationals of TB high-risk countries',
                    does_not_apply_when_ko='사증발급 시 제출한 경우, 6세 미만 소아', does_not_apply_when_en='Already submitted for the visa, or children under 6')],
         conditions_ko=[FOREIGN_DOC_NOTE_KO + ' 접수일 기준 6개월 이내 발급된 것이어야 합니다.'],
         conditions_en=[FOREIGN_DOC_NOTE_EN + ' They must be issued within 6 months before filing.'],
         notes_ko=[OFFICER_NOTE_KO], notes_en=[OFFICER_NOTE_EN])

guidance('F-1-52', 'status_change', section=f'{STAY_CH} — 체류자격 변경허가 12. 결혼이민자의 전혼관계 출생 미성년 자녀(F-1-52)에 대한 체류자격 변경허가',
         anchor='결혼이민자의 전혼관계 출생 미성년 자녀(F-1-52)에 대한 체류자격 변경허가',
         summary_ko='국민과 혼인관계를 유지하고 있는 결혼이민자(F-6, F-5-2)의 전혼관계 출생 친생 자녀로서 한국인 배우자에게 입양되지 않고 국내에 체류 중인 미성년 자녀가 대상입니다. 공교육 인정 대상 학교에 재학 중이면 2년, 아니면 1년이 허가됩니다.',
         summary_en='For minor biological children from a previous marriage of a marriage migrant (F-6, F-5-2) still married to a Korean, who were not adopted by the Korean spouse and are staying in Korea. Two years if enrolled in a public-recognized school, otherwise one year.',
         period_ko='공교육 인정 대상 학교 재학 시 2년, 미재학 시 1년', period_en='2 years if enrolled in a public-recognized school, otherwise 1 year',
         docs=[item('passport', anchor='여권, 통합신청서, 표준규격사진 1매, 수수료, 외국인등록증(해당자)'), item('app_form_34', anchor='여권, 통합신청서, 표준규격사진 1매, 수수료, 외국인등록증(해당자)'),
               item('photo', anchor='여권, 통합신청서, 표준규격사진 1매, 수수료, 외국인등록증(해당자)'), item('fee', anchor='여권, 통합신청서, 표준규격사진 1매, 수수료, 외국인등록증(해당자)'),
               item('arc', 'ADDITIONAL_IF_APPLICABLE', anchor='수수료, 외국인등록증(해당자)', applies_when_ko='외국인등록을 한 경우', applies_when_en='If registered'),
               item('spouse_basic_cert', anchor='결혼이민자의 한국인 배우자의 기본증명서, 가족관계증명서, 혼인관계증명서(상세증명서로 발급), 주민등록등본', role='korean_spouse'),
               item('spouse_family_cert', anchor='결혼이민자의 한국인 배우자의 기본증명서, 가족관계증명서, 혼인관계증명서(상세증명서로 발급), 주민등록등본', role='korean_spouse'),
               item('spouse_marriage_cert_detail', anchor='혼인관계증명서(상세증명서로 발급)', role='korean_spouse'),
               item('spouse_resident_reg', anchor='혼인관계증명서(상세증명서로 발급), 주민등록등본', role='korean_spouse'),
               item('f1_migrant_id_docs', anchor='결혼이민자의 여권, 신분증(관련 국가), 외국인등록증'),
               item('f1_child_birth_docs', anchor='미성년 외국인 자녀의 여권, 관련 국가에서 발급한 출생 관련 공적 증명서류 원본 및 사본'),
               item('f1_custody_proof', anchor='전혼 관계 출생 미성년 외국인 자녀에 대한 양육권 보유관계 입증서류(이혼판결문 등)'),
               item('f1_migrant_spouse_guarantee', anchor='양육권 등을 보유하고 미성년 외국인 자녀를 국내에서 양육하고 있는 결혼이민자와 한국인 배우자의 신원보증서'),
               item('enrollment_cert', 'CONDITIONAL_REQUIRED', anchor='재학증명서(공교육 인정 대상 학교에 재학 중인 경우)', applies_when_ko='공교육 인정 대상 학교에 재학 중인 경우', applies_when_en='If enrolled in a public-recognized school'),
               residence(anchor='⑧ 체류지 입증서류(임대차계약서 등), 결핵고위험국가의 경우 결핵진단서', alts=LEASE_ONLY),
               item('tb_cert', 'CONDITIONAL_REQUIRED', anchor='결핵고위험국가의 경우 결핵진단서', applies_when_ko='결핵고위험국가 국민인 경우', applies_when_en='Nationals of TB high-risk countries')],
         conditions_ko=[FOREIGN_DOC_NOTE_KO + ' 발급일로부터 6개월간 유효합니다.'],
         conditions_en=[FOREIGN_DOC_NOTE_EN + ' They are valid for 6 months from issuance.'],
         notes_ko=[OFFICER_NOTE_KO], notes_en=[OFFICER_NOTE_EN])

guidance('F-1-D', 'status_change', section=f'{STAY_CH} — 체류자격 변경허가 13. 디지털노마드(워케이션) 비자(F-1-D)에 대한 체류자격 변경허가',
         anchor='디지털노마드(워케이션) 비자(F-1-D)에 대한 체류자격 변경허가',
         summary_ko='단기체류자격(B-1, B-2, C-3)으로 국내 체류 중인 외국인(다른 체류자격 소지자도 요건을 갖추면 허용)이 워케이션(F-1-D)으로 변경하는 경우이며, 체류기간 1년이 부여됩니다.',
         summary_en='For foreigners staying on a short-term status (B-1, B-2, C-3) who change to workation (F-1-D); holders of other statuses may also change if they qualify. One year is granted.',
         period_ko='체류기간 1년', period_en='1 year',
         conditions_ko=['해외 사업체 소유자 또는 해외 기업에 소속된 외국인으로서 원격근무가 가능하고 1년 이상 동일 업종에 근무한 사람과 그 가족이 대상이며, 만 18세 이상이어야 합니다(동반가족 자녀는 예외).',
                        '소득요건: 신청일 기준 한국은행 고시 전년도 1인당 GNI를 기준으로, 수도권은 18~34세 GNI 1.5배·35세 이상 GNI 2배, 비수도권 및 인구감소(관심)지역은 각각 GNI 1배·1.5배입니다. 수도권에 가족을 동반하면 연령과 관계없이 GNI 2배(비수도권 등은 1.5배)입니다.',
                        '병원 치료 및 본국 후송을 위한 보장액 1억원 이상의 개인 의료보험에 가입해야 합니다.'],
         conditions_en=['For people who own an overseas business or work for an overseas company, can work remotely and have worked in the same field for at least one year, and their families; applicants must be 18 or over (accompanying children excepted).',
                        "Income test, based on last year's per-capita GNI published by the Bank of Korea: capital region 1.5x GNI for ages 18–34 and 2x for 35+; outside the capital region or in depopulation areas 1x and 1.5x. Bringing family to the capital region requires 2x regardless of age (1.5x elsewhere).",
                        'Private medical insurance covering at least KRW 100 million for treatment and repatriation is required.'],
         docs=stay_app('① 신청서(별지 34호 서식), 여권, 표준규격사진 1매, 수수료') + [
             item('employment_cert_1y', anchor='재직증명서(동일 업종에 1년 이상 종사 입증 필요)', role='employer'),
             item('income_proof', anchor='급여명세서, 잔고증명 등 소득 증빙 서류'),
             item('criminal_record_health_ins', anchor='범죄경력증명서*, 의료보험 가입 증명서',
                  notes_ko='해외범죄경력증명서 제출기준은 매뉴얼의 F-1-D 붙임을 따릅니다.', notes_en='Overseas criminal-record rules follow the F-1-D annex in the manual.'),
             item('family_relation', 'CONDITIONAL_REQUIRED', anchor='가족관계 입증서류(가족 동반시)', applies_when_ko='가족을 동반하는 경우', applies_when_en='If family members accompany you'),
             item('f1_regional_stay_proof_stay', 'CONDITIONAL_REQUIRED', anchor='(해당 시) 비수도권 및 인구감소(관심)지역에 체류할 예정임을 입증하는 서류*(1개월 이상 임대차 계약서, 워케이션 특화시설 또는 숙소 예약확인서 등)',
                  applies_when_ko='비수도권·인구감소(관심)지역 체류로 완화된 소득요건을 적용받는 경우', applies_when_en='If claiming the relaxed income test for staying outside the capital region or in a depopulation area',
                  notes_ko='비수도권 지역 등록자는 본인 명의로 제출해야 합니다.', notes_en='Registrants outside the capital region must submit it in their own name.'),
             item('other_officer_docs', 'MAY_BE_REQUESTED_BY_OFFICER', anchor='기타 출입국관서의 장이 심사에 필요하다고 인정하는 서류'),
         ],
         notes_ko=[OFFICER_NOTE_KO], notes_en=[OFFICER_NOTE_EN])

# ==========================================================================
# 체류자격 부여 (stay manual)
# ==========================================================================
guidance('F-1-12', 'status_grant', section=f'{STAY_CH} — 체류자격 부여 5. 점수제 우수인재(F-2-7)의 국내 출생 미성년자녀에 대한 방문동거 자격 부여',
         anchor='점수제 우수인재(F-2-7)의 국내 출생 미성년자녀에 대한 방문동거 자격 부여',
         summary_ko='점수제 우수인력(F-2-7)의 연간소득이 최근 1인당 국민소득 미만인 경우 그 국내 출생 미성년 자녀에게 방문동거 자격을 부여합니다. 주체류자가 F-2-7S이면 자격변경허가일부터 5년 동안은 소득요건과 무관하게 F-2-71이 부여되고, 5년 경과 후 소득요건 미충족 시 F-1-12가 부여됩니다.',
         summary_en='Korea-born minor children of an F-2-7 points-system resident whose annual income is below the latest per-capita national income are granted F-1. If the principal is F-2-7S, the child gets F-2-71 regardless of income for five years from the status change, and F-1-12 afterwards if the income test is not met.',
         conditions_ko=['신청인(미성년 자녀)은 국내에서 출생했고 결격사유에 해당하지 않아야 합니다.',
                        '부 또는 모는 F-2-7 또는 F-2-7S로 합법체류 중이어야 합니다(부 또는 모가 F-1-12 변경 요건을 충족한 경우 포함).',
                        '부 또는 모가 단기 체류자격(B-1, B-2, C-3)으로 입국하여 국내에서 출생한 자녀는 장기 체류자격 부여를 허용하지 않으며, 출국하여 관련 비자를 받고 입국해야 합니다.'],
         conditions_en=['The child must be born in Korea and not fall under any disqualification.',
                        'The father or mother must be lawfully staying as F-2-7 or F-2-7S (or meet the requirements to change to F-1-12).',
                        'A child born in Korea to a parent who entered on a short-term status (B-1, B-2, C-3) is not granted a long-term status and must leave and enter with the relevant visa.'],
         docs=f1_f27_docs(), notes_ko=[OFFICER_NOTE_KO], notes_en=[OFFICER_NOTE_EN])

# ==========================================================================
# 체류자격외 활동 (stay manual)
# ==========================================================================
F1_AOS_EXEMPT_KO = '원래의 체류목적을 침해하지 않는 범위에서 정규교육기관(초·중·고 및 대학)의 교육을 받으려는 경우에는 체류기간 범위 내에서 별도의 허가 절차가 필요 없습니다.'
F1_AOS_EXEMPT_EN = 'Attending a regular educational institution (primary, secondary school or university) within your period of stay, without undermining the original purpose of stay, needs no separate permission.'
F1_AOS_BASE = '① 신청서(별지 34호 서식), 여권 및 외국인등록증, 수수료'

guidance('F-1', 'activities_outside_status', scenario='dongpo-e1-e7',
         section=f'{STAY_CH} — 체류자격외 활동 2. 중국동포의 교수(E-1)~특정활동(E-7) 자격외 활동',
         anchor='방문동거(F-1) 자격을 소지한 중국동포 중 취업자격 구비 등 일정요건에 해당하는 자에 대한 교수(E-1) 내지 특정활동(E-7)으로의 자격외 활동 허가',
         summary_ko='방문동거(F-1) 자격을 가진 중국동포 중 취업자격 구비 등 일정 요건에 해당하는 사람은 교수(E-1)~특정활동(E-7) 활동을 위한 체류자격외 활동허가를 받을 수 있습니다.',
         summary_en='Chinese-Korean compatriots holding F-1 who meet certain requirements, such as job qualifications, can get permission for E-1 to E-7 activities outside their status.',
         conditions_ko=[F1_AOS_EXEMPT_KO], conditions_en=[F1_AOS_EXEMPT_EN],
         docs=base_stay(anchor=F1_AOS_BASE) + [
             item('f1_employment_recommendation', anchor='주무부처 장의 고용추천서 또는 고용필요성 입증서류'),
             item('employment_contract', anchor='③ 고용계약서 ④ 사업자등록증', role='employer'),
             item('business_reg', anchor='④ 사업자등록증 ⑤ 학위증 또는 자격증', role='employer'),
             item('f1_degree_or_license', anchor='⑤ 학위증 또는 자격증'),
         ],
         notes_ko=[OFFICER_NOTE_KO], notes_en=[OFFICER_NOTE_EN])

guidance('F-1', 'activities_outside_status', scenario='e2-e7-teacher',
         section=f'{STAY_CH} — 체류자격외 활동 3. 외국어회화강사(E-2), 외국인학교교사(E-7)로의 자격외 활동',
         anchor='방문동거(F-1), 동반(F-3)자격 소지자의 외국어회화강사(E-2), 외국인학교교사(E-7)로의 자격외 활동',
         summary_ko='방문동거(F-1) 자격 소지자가 외국어회화강사(E-2) 또는 외국인학교교사(E-7)로 활동하려면 공통 서류(신청서, 고용계약서, 사업자등록증 등)에 E-2 또는 E-7별 서류를 더해 체류자격외 활동허가를 받습니다.',
         summary_en='F-1 holders who want to work as a foreign-language instructor (E-2) or foreign-school teacher (E-7) apply for permission with the common documents (application, employment contract, business registration) plus the E-2 or E-7 documents.',
         conditions_ko=[F1_AOS_EXEMPT_KO], conditions_en=[F1_AOS_EXEMPT_EN],
         docs=base_stay(anchor=F1_AOS_BASE) + [
             item('employment_contract', anchor='② 고용계약서 ③ 사업자등록증', role='employer'),
             item('business_reg', anchor='② 고용계약서 ③ 사업자등록증', role='employer'),
             item('f1_degree_e2', 'CONDITIONAL_REQUIRED', anchor='④ 학위증(E-2 자격요건과 동일)', applies_when_ko='외국어회화강사(E-2) 활동', applies_when_en='E-2 instructor activity'),
             item('f1_criminal_record_e2', 'CONDITIONAL_REQUIRED', anchor='범죄경력증명서(E-2 자격요건과 동일)', applies_when_ko='E-2 또는 E-7 활동', applies_when_en='E-2 or E-7 activity'),
             item('f1_medical_e2', 'CONDITIONAL_REQUIRED', anchor='채용신체검사서(E-2 자격요건과 동일', applies_when_ko='E-2 또는 E-7 활동', applies_when_en='E-2 or E-7 activity'),
             item('f1_teacher_license', 'CONDITIONAL_REQUIRED', anchor='해당국교원 자격증 원본(교원자격증이 없는 경우 ‘학위증 및 경력증명서’)', applies_when_ko='외국인학교교사(E-7) 활동', applies_when_en='E-7 foreign-school teacher activity'),
             item('f1_principal_request', 'CONDITIONAL_REQUIRED', anchor='⑦학교장 요청서', applies_when_ko='외국인학교교사(E-7) 활동', applies_when_en='E-7 foreign-school teacher activity'),
             item('f1_foreign_teacher_status', 'CONDITIONAL_REQUIRED', anchor='⑧외국인교사 현황', applies_when_ko='외국인학교교사(E-7) 활동', applies_when_en='E-7 foreign-school teacher activity'),
         ],
         notes_ko=[OFFICER_NOTE_KO], notes_en=[OFFICER_NOTE_EN])

guidance('F-1', 'activities_outside_status', scenario='e7-proofreader',
         section=f'{STAY_CH} — 체류자격외 활동 4. 국가기관 및 공공단체 외국어교열요원(E-7)',
         anchor='방문동거(F-1), 동반(F-3)자격 소지자의 국가기관 및 공공단체(지방자치단체, 정부투자기관)에서 외국어교열요원(E-7)',
         summary_ko='방문동거(F-1) 자격 소지자가 국가기관 및 공공단체(지방자치단체, 정부투자기관)에서 외국어교열요원(E-7)으로 활동하려면 고용계약서, 사업자등록증 사본, 해당 기관장 추천서, 학위증을 내고 체류자격외 활동허가를 받습니다.',
         summary_en='F-1 holders who want to work as a foreign-language copy editor (E-7) at a state agency or public body (local government, government-invested institution) apply with the employment contract, a copy of the business registration, a recommendation from the head of the institution and a degree certificate.',
         conditions_ko=[F1_AOS_EXEMPT_KO], conditions_en=[F1_AOS_EXEMPT_EN],
         docs=base_stay(anchor=F1_AOS_BASE) + [
             item('employment_contract', anchor='② 고용계약서 ③ 사업자등록증 사본', role='employer'),
             item('business_reg_copy', anchor='③ 사업자등록증 사본 ④ 추천서(해당 기관장)', role='employer'),
             item('f1_agency_recommendation', anchor='추천서(해당 기관장)'),
             item('f1_degree_original_copy', anchor='학위증(원본 및 사본)'),
         ],
         notes_ko=[OFFICER_NOTE_KO], notes_en=[OFFICER_NOTE_EN])

guidance('F-1-12', 'activities_outside_status', state='EXCEPTION_ONLY', completeness='SOURCE_ONLY',
         section=f'{STAY_CH} — 체류자격외 활동 5. 점수제 우수인재의 배우자 및 미성년 자녀로서 방문동거자(F-1-12)',
         anchor='점수제 우수인재의 배우자 및 미성년 자녀로서 방문동거자(F-1-12)',
         summary_ko='점수제 우수인재의 배우자 및 미성년 자녀(F-1-12)는 원칙적으로 취업 및 영리활동이 불가합니다. 다만 외국인 관서장이 필요성이 있다고 판단하고 전문직·준전문직(E-1~E-7, E-6-2·E-7-4 제외) 취업 요건을 갖춘 경우 사전에 체류자격외 활동허가를 받아 취업할 수 있으며, 해당 체류자격에서 요구하는 서류를 냅니다.',
         summary_en='Spouses and minor children of points-system residents (F-1-12) may not work or engage in profit-making activities in principle. If the office finds it necessary and they meet the requirements for professional or semi-professional work (E-1 to E-7, excluding E-6-2 and E-7-4), they may work after getting prior permission, submitting the documents required for that status.')

guidance('F-1-4', 'activities_outside_status', state='CONDITIONAL', completeness='SOURCE_ONLY',
         section=f'{STAY_CH} — 체류자격외 활동 6. 대한민국 국적의 혼외 미성년자 자녀 양육자(F-1-4)의 체류자격외 활동허가',
         anchor='대한민국 국적의 혼외 미성년자 자녀 양육자(F-1-4)의 체류자격외 활동허가',
         summary_ko='대한민국 국적의 혼외 미성년 자녀 양육자(F-1-4)는 체류지 관할 청(사무소·출장소)에서 체류자격외 활동허가를 받아 사행행위·선량한 풍속에 반하는 행위 등 취업제한 분야를 제외한 단순노무 분야에 취업할 수 있습니다. 전문분야(E-1~E-7)에 취업하려면 관련 법령에서 정하는 자격을 갖춰야 합니다.',
         summary_en='Parents raising a Korean-national child born out of wedlock (F-1-4) can get permission from the local immigration office to work in simple-labor jobs, except restricted fields such as gambling or businesses contrary to public morals. Professional work (E-1 to E-7) requires the qualifications set by the relevant laws.',
         notes_ko=['매뉴얼은 이 항목의 제출서류를 따로 나열하지 않습니다.'], notes_en=['The manual lists no separate documents for this item.'])

# ==========================================================================
# 재입국허가 (stay manual, F-1 chapter)
# ==========================================================================
guidance('F-1', 'reentry', section=f'{STAY_CH} — 재입국허가',
         anchor='재입국허가 면제 제도 시행(‘10.12.1.자 개정 시행규칙)',
         summary_ko='등록을 마친 외국인이 출국한 날부터 1년 이내(남은 체류기간이 1년보다 짧으면 그 범위 내)에 재입국하면 재입국허가가 면제됩니다. 1년을 초과하여 2년 내에 재입국하려면 체류기간 범위 내에서 복수재입국허가를 받습니다.',
         summary_en='Registered foreigners re-entering within one year of departure (or within the remaining stay if shorter) are exempt from a re-entry permit. To re-enter after more than one year and within two years, get a multiple re-entry permit within your period of stay.',
         conditions_ko=['입국규제 및 사증발급규제자는 체류지 관할 청(사무소·출장소)에 방문하여 재입국허가를 받아야 합니다.',
                        '사우디아라비아, 이란, 리비아 국민은 복수재입국이 제한됩니다.'],
         conditions_en=['People subject to entry or visa restrictions must visit the local immigration office for a re-entry permit.',
                        'Nationals of Saudi Arabia, Iran and Libya are restricted from multiple re-entry permits.'],
         docs=[item('app_form_34', anchor='신청서(별지 34호서식), 여권 원본, 외국인등록증, 수수료'),
               item('passport_original', anchor='신청서(별지 34호서식), 여권 원본, 외국인등록증, 수수료'),
               item('arc', anchor='신청서(별지 34호서식), 여권 원본, 외국인등록증, 수수료'),
               item('fee', anchor='신청서(별지 34호서식), 여권 원본, 외국인등록증, 수수료')],
         notes_ko=['제출서류는 복수재입국허가 신청서류입니다.', OFFICER_NOTE_KO], notes_en=['The documents are those for a multiple re-entry permit.', OFFICER_NOTE_EN])

# ==========================================================================
# 체류기간 연장 — existing scenario rules: name the subcodes the manual ties to them.
#   diplomat-household: the stay manual's 1. 대상자 equates 주한 외국공관 비세대동거인 with
#     "외교(A-1)~협정(A-3) 자격에 해당하는 자의 동거인으로서 그 세대에 속하지 아니한 자" (visa: F-1-3)
#     and 주한 외국공관원의 가사보조인 (visa: F-1-21).
#   domestic-helper: 투자가 및 전문인력의 외국인 가사보조인 (visa: F-1-22, F-1-23, F-1-24).
#   parent-of-talent-investor-student: 우수인재, 투자자 및 유학생 부모 (visa: F-1-15).
# ==========================================================================
def _f1_add_covers(target, procedure, codes):
    hits = [g for g in GUIDANCE if g['target'] == target and g['procedure'] == procedure]
    assert len(hits) == 1, (target, procedure, len(hits))
    for c in codes:
        assert re.match(r'^[A-Z]-\d{1,2}(-[0-9A-Z]{1,3})?$', c), c
        if c not in hits[0]['covers']:
            hits[0]['covers'].append(c)


_f1_add_covers('F-1~diplomat-household', 'extension', ['F-1-3', 'F-1-21'])
_f1_add_covers('F-1~domestic-helper', 'extension', ['F-1-22', 'F-1-23', 'F-1-24'])
_f1_add_covers('F-1~parent-of-talent-investor-student', 'extension', ['F-1-15'])
