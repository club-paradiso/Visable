# E-6 예술흥행 · E-7 특정활동 · E-10 선원취업 — transcribed from the 2026-10-19 manuals.
# Visa procedures: 사증발급 안내매뉴얼 (VISA) chapters 예술흥행(E-6) / 특정활동(E-7) / 선원취업(E-10) (+ 전자사증 overview).
# Stay procedures: 체류자격별 안내매뉴얼 (STAY) chapters of the same names.
# Runs inside author_rules.py (guidance, item, docdefs, drop, residence, base_stay, VISA, STAY …).

docdefs(
    # --- shared visa-side forms ---
    e67_cvi_form=('사증발급인정신청서 (별지 제21호 서식)', 'Application for a confirmation of visa issuance (Form 21)', 'applicant', None),
    e67_visa_form=('사증발급신청서 (별지 제17호 서식)', 'Visa application form (Form 17)', 'applicant', None),
    e67_contract_copy=('고용계약서 사본', 'Copy of the employment contract', 'employer', None),
    e67_proxy_docs=('위임장, 대리인 재직증명서, 대리인 신분증 사본', 'Power of attorney, proxy\'s certificate of employment and copy of the proxy\'s ID', 'agency', None),
    # --- E-6 visa (사증발급인정서) ---
    e67_kmrb_rec_jeju=('영상물등급위원회(제주특별자치도의 경우 제주특별자치도지사)의 공연추천서', 'Performance recommendation from the Korea Media Rating Board (Jeju: the Jeju governor)', 'employer', None),
    e67_performance_plan=('공연계획서', 'Performance plan', 'employer', None),
    e67_guardian_consent=('법정대리인의 동의서', 'Consent of the legal guardian', 'applicant', None),
    e67_kmrb_rec=('영상물등급위원회의 공연추천서', 'Performance recommendation from the Korea Media Rating Board', 'employer', None),
    e67_entertainment_plan=('연예활동계획서', 'Entertainment activity plan', 'employer', None),
    e67_career_cert_3y=('자격증명서 또는 경력증명서 (3년 이상, 아포스티유 또는 자국소재 대한민국 공관 확인 필)', 'Qualification or career certificate (3+ years; apostille or confirmation by the Korean mission in your country)', 'applicant', None),
    e67_venue_status_cert=('공연시설 현황 확인서', 'Performance-venue status confirmation', 'employer', None),
    e67_dispatch_license=('근로자파견사업허가증', 'Worker-dispatch business licence', 'employer', None),
    e67_pop_culture_reg=('대중문화예술기획업 등록증', 'Popular culture and arts planning business registration', 'employer', None),
    e67_vat_base_cert=('부가가치세 과세표준증명(매출과세표준)', 'VAT tax-base certificate (sales)', 'employer', None),
    e67_company_soundness=('기타 기업의 건전성을 증빙하는 서류', 'Other documents showing the company is sound', 'employer', None),
    e67_guarantee_resume_consent=('신원보증서, 이력서, 보호자 동의서 (미성년인 경우)', 'Letter of guarantee, CV, and guardian consent (if a minor)', 'applicant', None),
    e67_domestic_activity_plan=('국내활동 계획서', 'Plan of activities in Korea', 'employer', None),
    e67_model_expertise=('기타 모델의 전문성을 입증할 수 있는 서류 (광고촬영·패션쇼 관련 광고주와의 계약서, 모델 사용 개요(광고주 작성), 포트폴리오 등)', 'Other proof of the model\'s expertise (contract with the advertiser, model-use outline written by the advertiser, portfolio, etc.)', 'employer', None),
    e67_ministry_rec_or_need_visa=('소관 중앙행정기관의 장의 고용추천서 또는 고용의 필요성을 입증하는 서류', 'Employment recommendation from the competent ministry, or proof of the need to employ', 'employer', None),
    # --- E-6 stay ---
    e67_emp_perf_rec_bodies=('고용․공연추천서 (문화체육관광부, 영상물등급위원회, 방송통신위원회, 프로스포츠 연맹 등 발급)', 'Employment/performance recommendation (Ministry of Culture, Sports and Tourism, Korea Media Rating Board, Korea Communications Commission, pro-sports leagues, etc.)', 'employer', None),
    e67_perf_rec_mcst=('공연추천서 (문화체육관광부 또는 방송통신위원회의 추천 필요)', 'Performance recommendation (from the Ministry of Culture, Sports and Tourism or the Korea Communications Commission)', 'employer', None),
    e67_org_establishment=('사업자등록증 등 단체 등 설립관련 서류', 'Business registration or other documents on the organization\'s establishment', 'employer', None),
    e67_prev_employer_consent_if=('원 근무처 장의 동의서 (해당자)', 'Consent of the head of the original workplace (if applicable)', 'employer', None),
    e67_mofa_recommendation=('외교부장관(외교사절담당관)의 추천서', 'Recommendation from the Minister of Foreign Affairs (diplomatic-mission officer)', 'other_third_party', None),
    e67_prev_employer_consent=('원 근무처 장의 동의서', 'Consent of the head of the original workplace', 'employer', None),
    e67_perf_rec_kmrb_issued=('공연 추천서 (영상물등급위원회 발행)', 'Performance recommendation (issued by the Korea Media Rating Board)', 'employer', None),
    e67_employment_change_report=('고용‧연수외국인 변동사유 발생신고서 (별지 제32호 서식)', 'Report of changes for an employed/trainee foreigner (Form 32)', 'employer', None),
    e67_biz_reg_both=('사업자등록증 (파견사업주, 사용사업주 모두)', 'Business registration (both the dispatching and the using employer)', 'employer', None),
    e67_employer_id_or_staff=('고용주 신분증 (직원의 경우 위임장, 재직증명서, 직원신분증)', 'Employer\'s ID (for an employee: power of attorney, certificate of employment, staff ID)', 'employer', None),
    e67_dispatch_contract=('파견사업자와 사용사업주 간 파견근로계약서', 'Worker-dispatch contract between the dispatching and the using employer', 'employer', None),
    e67_venue_facility_cert=('공연장소 시설확인서', 'Performance-venue facility confirmation', 'employer', None),
    # --- E-10 visa ---
    e67_crime_record_national=('국적국의 권한 있는 기관이 발급한 범죄경력증명서', 'Criminal record certificate issued by the competent authority of your country', 'applicant', None),
    e67_health_statement=('건강상태 확인서 (사증신청인 자필 기재, 붙임 3 양식)', 'Health-status statement (handwritten by the applicant, Annex 3 form)', 'applicant', None),
    e67_seafarer_report_acceptance=('외국인선원고용신고수리서 (지방해양항만청장 발급)', 'Acceptance of the foreign-seafarer employment report (regional maritime office)', 'ship_owner', None),
    e67_coastal_license_copy=('「해운법」에 따른 내항여객운송사업면허증·내항화물운송사업등록증 사본 (최초 신청 또는 등록사항 변경 시에만 제출)', 'Copy of the coastal passenger licence / coastal cargo registration under the Marine Transportation Act (first application or registration change only)', 'ship_owner', None),
    e67_crew_capacity_cert=('‘승선정원증서’ 또는 ‘500톤 미만 선박검사증서’ 등 기타 청(사무소·출장소)장이 필요하다고 인정하는 서류', 'Crew-capacity certificate, inspection certificate for ships under 500 t, or other documents the office deems necessary', 'ship_owner', None),
    e67_to_approval=('노사합의 선사별 T/O 운영승인서', 'Per-company quota (T/O) approval agreed by labour and management', 'ship_owner', None),
    e67_fishery_license_copy=('「수산업법」에 따른 정치망어업면허증 및 관리선사용지정(어선사용승인)증·근해어업허가증 사본 (최초 신청 또는 등록사항 변경 시에만 제출)', 'Copy of the set-net fishery licence and management-vessel designation / offshore fishery permit under the Fisheries Act (first application or registration change only)', 'ship_owner', None),
    e67_ship_inspection_cert=('선박검사증서', 'Ship inspection certificate', 'ship_owner', None),
    e67_fish_transport_reg=('어획물운반업등록증', 'Catch-transport business registration', 'ship_owner', None),
    e67_cruise_license_copy=('순항여객운송사업면허증 사본 (최초 신청 또는 등록사항 변경 시에만 제출)', 'Copy of the cruise passenger transport licence (first application or registration change only)', 'ship_owner', None),
    # --- E-10 stay ---
    e67_seafarer_rec_union=('한국해운조합 또는 수산업협동조합중앙회 발급 외국인 고용추천서', 'Foreign-worker employment recommendation from the Korea Shipping Association or the National Federation of Fisheries Cooperatives', 'ship_owner', None),
    e67_injury_docs=('산재서류 또는 진단서 (필요시)', 'Industrial-accident documents or medical certificate (if needed)', 'applicant', None),
    # --- E-7 visa ---
    e67_mission_request_letter=('주한 외국공관 협조요청 공문', 'Request letter from the foreign mission in Korea', 'employer', None),
    e67_edu_career_proof=('학력 및 경력 등 입증서류', 'Proof of education and career', 'applicant', None),
    e67_employer_establishment=('고용업체 설립관련서류', 'Documents on the employer\'s establishment', 'employer', None),
    e67_org_establishment_e7=('공․사기관 설립관련 서류 (사업자등록증, 고유번호증, 외국인투자기업등록증 등)', 'Documents on the establishment of the public/private organization (business registration, unique-number certificate, foreign-invested company registration, etc.)', 'employer', None),
    e67_tax_certs_visa=('납세증명서(국세완납증명서), 지방세 납세증명서', 'National tax payment certificate and local tax payment certificate', 'employer', None),
    e67_employment_need_proof=('외국인의 고용의 필요성을 입증할 수 있는 서류 (초청사유서, 외국인활용계획서 등, 소관 중앙행정기관의 장의 고용추천서 또는 관련 단체 등의 추천서)', 'Proof of the need to employ the foreigner (invitation reason, utilization plan, or a recommendation from the competent ministry or a related body)', 'employer', None),
    e67_qualification_proof=('자격요건 입증서류 (학위증, 경력증명서, 이력서, 유효한 자격증 등)', 'Proof of qualifications (degree, career certificate, CV, valid licences, etc.)', 'applicant', None),
    e67_occupation_extra_docs=('직종별 세부심사기준에 따른 추가 제출서류', 'Additional documents under the occupation-specific review criteria', 'applicant', None),
    e67_service_contract=('본인과 국내법인 또는 개인사업자 간의 서비스공급 계약서', 'Service-supply contract between you and the Korean company or sole proprietor', 'applicant', None),
    e67_corp_reg_or_biz=('국내법인 또는 개인사업자의 법인등기부등본 또는 사업자등록증 사본', 'Corporate register or copy of the business registration of the Korean company or sole proprietor', 'business_entity', None),
    e67_tax_fact_cert=('납세사실증명서', 'Certificate of tax payment', 'business_entity', None),
    e67_edu_career_cepa=('학력입증서류, 경력입증서류', 'Proof of education and of career', 'applicant', None),
    e67_service_need=('서비스공급의 필요성을 입증할 수 있는 서류 (활용계획서, 고용추천서 등)', 'Proof of the need for the service supply (utilization plan, recommendation, etc.)', 'business_entity', None),
    e67_occupation_docs_cepa=('기타 직종별 첨부서류', 'Other occupation-specific documents', 'applicant', None),
    # --- E-7 stay ---
    e67_employer_establishment_stay=('고용업체 등 설립관련 서류 (사업자등록증, 등기부등본 등)', 'Documents on the employer\'s establishment (business registration, register, etc.)', 'employer', None),
    e67_career_cert=('경력증명서', 'Career certificate', 'applicant', None),
    e67_ministry_rec_or_need=('주무부처 장의 고용추천서 또는 고용의 필요성을 입증하는 서류', 'Employment recommendation from the competent ministry, or proof of the need to employ', 'employer', None),
    e67_tax_certs_stay=('납세증명서(국세완납증명서), 지방세 납세증명', 'National tax payment certificate and local tax payment certificate', 'employer', None),
    e67_teacher_license=('해당국 교원자격증 (교원 자격증이 없는 경우 ‘학위증 및 경력증명서’)', 'Teacher\'s licence of the country concerned (if none: degree and career certificate)', 'applicant', None),
    e67_principal_recommendation=('학교장 추천서', 'Recommendation from the school principal', 'educational_institution', None),
    e67_school_establishment=('학교설립관련 서류', 'Documents on the school\'s establishment', 'educational_institution', None),
    e67_criminal_record_e2=('범죄경력증명서 (E-2 자격과 동일)', 'Criminal record certificate (same as for E-2)', 'applicant', None),
    e67_medical_exam=('채용신체검사서', 'Pre-employment medical examination', 'applicant', None),
    e67_career_or_degree=('경력증명서 (학사이상 학위소지자는 학위증 사본 첨부)', 'Career certificate (bachelor\'s or higher: attach a copy of the degree)', 'applicant', None),
    e67_minister_recommendation=('소관부처장관의 고용추천서', 'Employment recommendation from the competent minister', 'employer', None),
    e67_ministry_recommendation=('주무부처 장의 고용추천서', 'Employment recommendation from the competent ministry', 'employer', None),
    e67_degree_or_license=('학위증 또는 자격증', 'Degree or licence', 'applicant', None),
    e67_teacher_license_original=('해당국교원 자격증 원본 (교원자격증이 없는 경우 ‘학위증 및 경력증명서’)', 'Original teacher\'s licence of the country concerned (if none: degree and career certificate)', 'applicant', None),
    e67_medical_exam_e2=('채용신체검사서 (E-2 자격요건과 동일)', 'Pre-employment medical examination (same as for E-2)', 'applicant', None),
    e67_principal_request=('학교장 요청서', 'Request letter from the school principal', 'educational_institution', None),
    e67_foreign_teacher_status=('외국인교사 현황', 'List of foreign teachers', 'educational_institution', None),
    e67_agency_head_rec=('추천서 (해당 기관장)', 'Recommendation (from the head of the institution)', 'employer', None),
    e67_degree_original_copy=('학위증 (원본 및 사본)', 'Degree (original and copy)', 'applicant', None),
    e67_form_34_34_2=('통합신청서 (별지 제34호~제34호의2 서식)', 'Integrated application form (Forms 34 to 34-2)', 'applicant', 'hikorea'),
    e67_closure_or_arrears_proof=('휴․폐업사실증명서, 임금체불 관련 공적 입증서류, 매출감소 등 경영악화 사실을 입증할 수 있는 부가세신고서 등 (해당서류 중 1종)', 'One of: certificate of business suspension/closure, official proof of unpaid wages, or VAT returns showing worsening business such as falling sales', 'applicant', None),
    e67_transfer_consent=('원 고용주의 이적동의서', 'Transfer consent from the original employer', 'employer', None),
    e67_new_employer_review_docs=('새로 고용 계약한 업체의 자격요건 등을 심사할 수 있는 서류 (사증발급인정서 발급 신청 시 첨부서류에 준하여 제출)', 'Documents for reviewing the new employer\'s eligibility (as for a confirmation-of-visa-issuance application)', 'employer', None),
)

GUARANTOR_E7_OCCUPATIONS_KO = '기계공학기술자(2351), 제도사(2395), 해외영업원(2742) 중 해외 온라인상품판매원, 디자이너(285), 판매사무원(31215), 주방장 및 조리사(441), 고객상담사무원(3991), 호텔접수사무원(3922), 의료코디네이터(S3922), 양식기술자(6301), 조선용접공(7430), 뿌리산업체 숙련기능공(S740) 직종인 경우'
GUARANTOR_E7_OCCUPATIONS_EN = 'Mechanical engineers (2351), drafters (2395), overseas online sellers among overseas sales staff (2742), designers (285), sales clerks (31215), chefs and cooks (441), customer-service clerks (3991), hotel receptionists (3922), medical coordinators (S3922), aquaculture technicians (6301), ship welders (7430), skilled root-industry workers (S740)'
E7_PRIOR_PERMIT_KO = '사전 허가대상 직종(기계공학기술자, 제도사, 해외 온라인상품판매원, 디자이너, 판매사무원, 주방장 및 조리사, 고객상담사무원, 호텔접수사무원, 의료코디네이터, 양식기술자, 조선용접공, 선박 전기원, 선박 도장공, 항공(부품) 제조원, 송전전기원, 자동차 부품제조원, 자동차 판금·도장원, 도축원, 건설기계부품제조원, 숙련기능 점수제 종사자)인 경우'
E7_PRIOR_PERMIT_EN = 'Occupations requiring prior permission (mechanical engineers, drafters, overseas online sellers, designers, sales clerks, chefs and cooks, customer-service clerks, hotel receptionists, medical coordinators, aquaculture technicians, ship welders, ship electricians, ship painters, aircraft (parts) manufacturing workers, power-line electricians, auto-parts manufacturing workers, auto body/paint workers, slaughterers, construction-machinery parts workers, skilled points-system workers)'
E7_POST_REPORT_KO = '사전 허가대상 직종을 제외한 특정활동(E-7) 자격 소지자인 경우(사후 신고)'
E7_POST_REPORT_EN = 'E-7 holders in any occupation not on the prior-permission list (post-change report)'


def reentry_rule(code, section, anchor, doc_anchor):
    guidance(code, 'reentry', section=section, anchor=anchor, completeness='PARTIALLY_STRUCTURED',
             summary_ko='등록을 마친 외국인은 출국한 날부터 1년 이내(남은 체류기간이 1년보다 짧으면 그 범위 내)에 재입국하면 재입국허가가 면제됩니다. 다만 입국규제 및 사증발급규제자는 체류지 관할 관서를 방문하여 재입국허가를 받아야 하며, 체류기간 범위 내에서 1년을 넘겨 2년 내에 재입국하려면 복수재입국허가를 신청합니다.',
             summary_en='Registered foreigners re-entering within one year of departure (or within the remaining stay if shorter) are exempt from the re-entry permit. People subject to entry or visa restrictions must visit the local immigration office for a permit, and to return after more than one year but within two years (within the stay period) you apply for a multiple re-entry permit.',
             conditions_ko=['사우디아라비아, 이란, 리비아 국민은 복수재입국이 제한됩니다(단, 동 국가 국민 중 결혼이민(F-6), 유학(D-2), 일반연수(D-4)는 가능).'],
             conditions_en=['Nationals of Saudi Arabia, Iran and Libya cannot get a multiple re-entry permit (except F-6, D-2 and D-4 holders of those countries).'],
             docs=[item(d, 'CONDITIONAL_REQUIRED', anchor=doc_anchor, applies_when_ko='복수재입국허가(출국 후 1년 초과 2년 이내 재입국)를 신청하는 경우', applies_when_en='Applying for a multiple re-entry permit (return after more than 1 year, within 2 years)')
                   for d in ('app_form_34', 'passport_original', 'arc', 'fee')],
             notes_ko=[OFFICER_NOTE_KO], notes_en=[OFFICER_NOTE_EN])


# ==========================================================================
# E-6 예술흥행 — 사증 (visa manual pp. 165–169)
# ==========================================================================
guidance('E-6', 'visa_issuance', manual=VISA, state='CONDITIONAL', completeness='SOURCE_ONLY',
         section='예술흥행(E-6) — 공관장 재량으로 발급할 수 있는 사증', anchor='예술흥행(E-6) 자격은 모두 사증발급인정서에 의해 사증발급',
         summary_ko='예술흥행(E-6) 사증은 모두 사증발급인정서에 의해 발급됩니다. E-6-2 신청인이 불법체류다발 고시국가(21개국), 테러지원국가(3개국), 제주무사증입국불허국가(10개국) 국민이면 원칙적으로 자국 공관에서 사증을 신청·발급받으며, 제3국의 영주권자이거나 2년 이상 계속 체류한 장기체류자는 제3국 소재 자국공관에서도 신청할 수 있습니다.',
         summary_en='All E-6 visas are issued on the basis of a confirmation of visa issuance. E-6-2 applicants who are nationals of the 21 designated high-overstay countries, the 3 state sponsors of terrorism or the 10 countries barred from Jeju visa-free entry in principle apply at their own country\'s mission; permanent residents of a third country or those who have lived there 2+ years may apply at their country\'s mission in that third country.')

guidance('E-6', 'visa_issuance_confirmation', manual=VISA, completeness='PARTIALLY_STRUCTURED', doc_page_window=4,
         section='예술흥행(E-6) — 사증발급인정서 발급대상 1. 체류기간 2년 이하의 예술흥행(E-6) 사증발급인정서 발급', anchor='체류기간 2년 이하의 예술흥행(E-6) 사증발급인정서 발급',
         summary_ko='예술흥행(E-6) 사증발급인정서는 공연추천기간, 고용추천기간, 근로계약기간 등을 종합적으로 참고하여 2년 이하의 체류기간으로 발급됩니다. 공통 서류(신청서·여권·사진, 사업자등록증 사본, 고용계약서 사본)에 더해 공연법상 공연, 호텔·유흥업소 공연, 광고 모델, 그 밖의 경우에 따라 추가 서류를 냅니다.',
         summary_en='An E-6 confirmation of visa issuance is granted for up to 2 years, based on the performance/employment recommendation and contract periods. On top of the common documents (application, passport, photo, business registration copy, employment contract copy), extra documents depend on whether it is a performance under the Performance Act, a hotel/entertainment-venue performance, advertising modelling, or another case.',
         docs=[
             item('e67_cvi_form', anchor='① 사증발급인정신청서 (별지 제21호 서식), 여권, 표준규격사진 1매'),
             item('passport', anchor='① 사증발급인정신청서 (별지 제21호 서식), 여권, 표준규격사진 1매'),
             item('photo', anchor='① 사증발급인정신청서 (별지 제21호 서식), 여권, 표준규격사진 1매'),
             item('business_reg_copy', anchor='② 사업자등록증 사본', role='employer'),
             item('e67_contract_copy', anchor='③ 고용계약서 사본'),
             item('e67_kmrb_rec_jeju', 'CONDITIONAL_REQUIRED', anchor='공연추천서(추천제외대상공연은 면제)',
                  applies_when_ko='공연법 규정에 의한 공연을 하려는 경우 (추천제외대상공연은 면제)', applies_when_en='Performances under the Performance Act (exempt performances excluded)'),
             item('e67_performance_plan', 'CONDITIONAL_REQUIRED', anchor='⑤ 공연계획서',
                  applies_when_ko='공연법 규정에 의한 공연을 하려는 경우', applies_when_en='Performances under the Performance Act'),
             item('e67_kmrb_rec', 'CONDITIONAL_REQUIRED', anchor='④ 영상물등급위원회의 공연추천서',
                  applies_when_ko='관광진흥법에 의한 호텔업시설, 유흥업소 등에서 공연 또는 연예활동에 종사하려는 경우', applies_when_en='Performing or entertaining at hotels or entertainment venues under the Tourism Promotion Act'),
             item('e67_entertainment_plan', 'CONDITIONAL_REQUIRED', anchor='⑤ 연예활동계획서',
                  applies_when_ko='호텔업시설, 유흥업소 등에서 공연 또는 연예활동에 종사하려는 경우', applies_when_en='Hotel/entertainment-venue performers'),
             item('e67_career_cert_3y', 'CONDITIONAL_REQUIRED', anchor='자격증명서 또는 경력증명서',
                  applies_when_ko='호텔업시설, 유흥업소 등에서 공연 또는 연예활동에 종사하려는 경우 (호텔·유흥(E-6-2) 자격으로 국내에 체류한 사실이 확인되면 면제)', applies_when_en='Hotel/entertainment-venue performers (waived if a previous E-6-2 stay in Korea is confirmed)'),
             item('e67_venue_status_cert', 'CONDITIONAL_REQUIRED', anchor='⑦ 공연시설 현황 확인서',
                  applies_when_ko='호텔업시설, 유흥업소 등에서 공연 또는 연예활동에 종사하려는 경우', applies_when_en='Hotel/entertainment-venue performers'),
             item('guarantor', 'CONDITIONAL_REQUIRED', anchor='⑧ 신원보증서',
                  applies_when_ko='호텔업시설, 유흥업소 등에서 공연 또는 연예활동에 종사하려는 경우', applies_when_en='Hotel/entertainment-venue performers'),
             item('e67_dispatch_license', 'CONDITIONAL_REQUIRED', anchor='⑩ 근로자파견사업허가증(해당자)',
                  applies_when_ko='호텔업시설, 유흥업소 등에서 공연하는 경우 중 해당자', applies_when_en='Hotel/entertainment-venue performers, where applicable'),
             item('e67_pop_culture_reg', 'CONDITIONAL_REQUIRED', anchor='④ 대중문화예술기획업 등록증',
                  applies_when_ko='광고 모델의 경우 (일반심사 기준)', applies_when_en='Advertising models (standard review)'),
             item('e67_vat_base_cert', 'CONDITIONAL_REQUIRED', anchor='⑤ 부가가치세 과세표준증명(매출과세표준)',
                  applies_when_ko='광고 모델의 경우 (일반심사 기준)', applies_when_en='Advertising models (standard review)'),
             item('tax_clearance', 'CONDITIONAL_REQUIRED', anchor='⑥ 납세증명서', role='employer',
                  applies_when_ko='광고 모델의 경우 (일반심사 기준)', applies_when_en='Advertising models (standard review)'),
             item('e67_company_soundness', 'CONDITIONAL_REQUIRED', anchor='⑦ 기타 기업의 건전성을 증빙하는 서류',
                  applies_when_ko='광고 모델의 경우 (일반심사 기준)', applies_when_en='Advertising models (standard review)'),
             item('e67_guarantee_resume_consent', 'CONDITIONAL_REQUIRED', anchor='⑧ 신원보증서, 이력서, 보호자 동의서 (미성년인 경우)',
                  applies_when_ko='광고 모델의 경우 (일반심사 기준)', applies_when_en='Advertising models (standard review)'),
             item('e67_domestic_activity_plan', 'CONDITIONAL_REQUIRED', anchor='⑨ 국내활동 계획서',
                  applies_when_ko='광고 모델의 경우 (일반심사 기준)', applies_when_en='Advertising models (standard review)'),
             item('e67_model_expertise', 'CONDITIONAL_REQUIRED', anchor='기타 모델의 전문성을 입증할 수 있는 서류',
                  applies_when_ko='광고 모델의 경우 (일반심사 기준)', applies_when_en='Advertising models (standard review)'),
             item('e67_ministry_rec_or_need_visa', 'CONDITIONAL_REQUIRED', anchor='소관 중앙행정기관의 장의 고용추천서 또는 고용의 필요성을 입',
                  applies_when_ko='그 밖의 경우', applies_when_en='All other cases'),
             item('e67_guardian_consent', 'CONDITIONAL_REQUIRED', anchor='피초청인이 미성년자인 경우, 법정대리인의 동의서',
                  applies_when_ko='피초청인이 미성년자인 경우 (공연법상 공연, 호텔·유흥업소 공연, 그 밖의 경우)', applies_when_en='The invitee is a minor (Performance Act performances, hotel/entertainment venues, other cases)'),
             item('e67_proxy_docs', 'CONDITIONAL_REQUIRED', anchor='대리인 신청 시 : 위임장, 대리인 재직증명서, 대리인 신분증 사본 추가 필요',
                  applies_when_ko='대리인이 신청하는 경우', applies_when_en='When a proxy files'),
         ],
         conditions_ko=['광고 모델 초청업체가 우대심사 기준(우수업체: 법인사업자, 대중문화예술기획업 등록, 최근 3년 이내 최소 5억원 이상 매출실적 등)에 해당하면 매뉴얼의 별도 서류 목록(법인등기부등본, 고용보험 가입자 명부 등)이 적용되니 원문을 확인하세요.'],
         conditions_en=['If the inviting company for an advertising model meets the preferential-review criteria (corporation, registered planning business, KRW 500 m+ sales in the last 3 years, etc.), the manual\'s separate list (corporate register, employment-insurance roster, etc.) applies; check the original page.'],
         notes_ko=['재외공관의 장은 입국목적, 초청의 진정성, 초청자 및 피초청자의 자격 확인 등을 심사하기 위해 필요한 경우 첨부 서류를 일부 가감할 수 있습니다.', OFFICER_NOTE_KO],
         notes_en=['The head of the mission may add or omit documents to check the purpose of entry, the genuineness of the invitation and the parties\' eligibility.', OFFICER_NOTE_EN])

# ==========================================================================
# E-6 예술흥행 — 체류 (stay manual pp. 207–213)
# ==========================================================================
guidance('E-6', 'activities_outside_status', completeness='PARTIALLY_STRUCTURED',
         section='예술흥행(E-6) 체류자격외 활동 — 1. 합법체류 등록외국인의 방송, 영화, 모델활동', anchor='합법체류 등록외국인(A-1, A-2, A-3 포함)으로서 방송*, 영화, 모델활동을',
         summary_ko='합법체류 등록외국인(A-1, A-2, A-3 포함)이 방송, 영화, 모델활동을 하려면 체류자격외 활동허가를 받으며, 세부약호 E-6-2 활동에 종사하려는 경우는 허가 대상에서 제외됩니다. 제출서류 및 체류실태 등을 종합 심사하여 허가 여부를 결정합니다.',
         summary_en='Registered foreigners staying lawfully (including A-1, A-2, A-3) need activities-outside-status permission for broadcasting, film or modelling; E-6-2 activities are excluded. The decision is based on the documents and the person\'s stay record as a whole.',
         docs=base_stay(anchor='① 신청서(별지 34호 서식), 여권 및 외국인등록증, 수수료 ② 고용계약서') + [
             item('employment_contract', anchor='② 고용계약서 ③ 공연추천서'),
             item('e67_perf_rec_mcst', anchor='공연추천서(문화체육관광부 또는 방송통신위원회의 추천 필요)'),
             item('e67_org_establishment', anchor='사업자등록증 등 단체 등 설립관련 서류'),
             item('e67_prev_employer_consent_if', 'CONDITIONAL_REQUIRED', anchor='원 근무처장의 동의서(해당자)',
                  applies_when_ko='원 근무처가 있는 해당자', applies_when_en='If you have an original workplace'),
             item('e67_mofa_recommendation', 'CONDITIONAL_REQUIRED', anchor='A-1, A-2자격 소지자의 경우 외교부장관(외교사절담당관)의 추천서',
                  applies_when_ko='A-1, A-2 자격 소지자', applies_when_en='A-1 or A-2 holders'),
         ],
         conditions_ko=['비영리목적으로 지상파방송에 게스트 등으로 임시(1회 및 비연속성) 출연하는 경우에는 일상생활의 부수적 활동으로 보아 별도의 허가 없이 활동할 수 있습니다(식비, 교통비 등 실비 수준의 사례금 수령 가능).',
                        '원래의 체류목적을 침해하지 않는 범위에서 정규교육기관(초·중·고 및 대학)의 교육을 받는 것은 체류기간 범위 내에서 별도 허가가 필요 없습니다.',
                        '전문 외국인력(E-1~E-5, E-6-2를 제외한 E-6, E-7) 등의 배우자는 단순노무(D-3, E-9) 등을 제외한 모든 직종에 대해 배우자의 체류기간까지 체류자격외 활동허가를 받을 수 있으며, 서류는 규칙 제76조의 체류자격별 첨부서류(신원보증서 생략)입니다.'],
         conditions_en=['A temporary (one-off, non-continuous) non-profit guest appearance on terrestrial TV is treated as incidental to daily life and needs no permission (expense-level honoraria allowed).',
                        'Attending a regular school (primary to university) without harming the original purpose of stay needs no separate permission within the stay period.',
                        'Spouses of professional foreign workers (E-1–E-5, E-6 except E-6-2, E-7) etc. can get permission for any occupation except simple labour (D-3, E-9) up to the spouse\'s stay; documents are those of Rule Art. 76 for the status concerned (no letter of guarantee).'],
         notes_ko=[OFFICER_NOTE_KO], notes_en=[OFFICER_NOTE_EN])


E6_CHANGE_DOC_ANCHOR = '①신청서(별지 34호서식), 여권 및 외국인등록증, 표준규격사진 1장, 수수료'
guidance('E-6', 'status_change', state='CONDITIONAL', completeness='PARTIALLY_STRUCTURED',
         section='예술흥행(E-6) 체류자격 변경허가 — 1. 유학(D-2), 구직(D-10) → E-6, 5. 전문외국인력의 배우자(F-3)', anchor='세부자격 약호 E-6-1 및 E-6-3에 해당하는 경우 제한적으로 허용',
         summary_ko='예술흥행(E-6)으로의 체류자격 변경은 세부약호 E-6-1과 E-6-3에 해당하는 경우에만 제한적으로 허용되며, 아래 변경 대상자 외에 국제적으로 명성이 있는 전문예술·체육인은 본부승인을 얻어 변경할 수 있습니다. 허가기간은 변경허가일로부터 최대 2년의 범위 내에서 근로계약기간+1개월입니다.',
         summary_en='Changing to E-6 is allowed only on a limited basis for E-6-1 and E-6-3; apart from the cases below, internationally renowned professional artists and athletes may change with headquarters approval. The permit runs for the employment contract period + 1 month, up to 2 years from approval.',
         period_ko='변경허가일로부터 최대 2년의 범위 내에서 근로계약기간 + 1개월', period_en='Contract period + 1 month, up to 2 years from approval',
         docs=[item('app_form_34', anchor=E6_CHANGE_DOC_ANCHOR), item('passport', anchor=E6_CHANGE_DOC_ANCHOR), item('arc', anchor=E6_CHANGE_DOC_ANCHOR),
               item('photo1', anchor=E6_CHANGE_DOC_ANCHOR), item('fee', anchor=E6_CHANGE_DOC_ANCHOR),
               item('contract_or_performance', anchor='②고용계약서(또는 공연계약서) ③사업자등록증', role='employer'),
               item('business_reg', anchor='②고용계약서(또는 공연계약서) ③사업자등록증', role='employer'),
               item('e67_emp_perf_rec_bodies', anchor='④ 고용․공연추천서(문화체육')],
         conditions_ko=['유학(D-2) 또는 구직(D-10) 자격으로 합법 체류 중이고, 취업하려는 분야가 E-1~E-7 자격에 해당하여 해당 자격요건 등을 갖추고, 취업하려는 기관·단체 등의 대표자와 고용계약을 체결하여야 합니다(유학(D-2)은 구직(D-10)으로 변경할 수 있는 요건을 갖춘 졸업예정자).',
                        '전문외국인력(E-1~E-5, E-6(E-6-2 제외), E-7)의 배우자로서 동반(F-3) 자격 소지자도 같은 서류로 전문직 자격으로 변경할 수 있습니다.',
                        '무사증(B-1·B-2) 또는 단기사증(C-3) 입국자는 불가피한 사유가 있거나 국익차원에서 필요한 경우에만 자격변경이 허용됩니다(입단 테스트 운동선수, 상금이 걸린 국제대회 참가자 등은 입증자료로 청장 재량 허가).',
                        '일반 체류자격으로 장기 체류 중인 사람이 현재 활동을 그만두고 귀국 전에 단기간 방송출연 또는 모델활동을 하려는 경우에도 E-6 변경허가를 받습니다(E-6 또는 F-2, F-4, F-5 등 취업제한이 없는 자격 소지자 제외).'],
         conditions_en=['You must be lawfully staying as D-2 or D-10, the intended work must fall under E-1–E-7 with its requirements met, and you must have an employment contract with the head of the organization (for D-2: a prospective graduate eligible to change to D-10).',
                        'F-3 spouses of professional foreign workers (E-1–E-5, E-6 except E-6-2, E-7) may change to a professional status with the same documents.',
                        'Visa-free (B-1, B-2) or short-term visa (C-3) entrants may change only for unavoidable reasons or in the national interest (e.g. athletes on trial, prize-competition participants, at the office head\'s discretion with proof).',
                        'Long-term residents who stop their current activity and want to do short broadcasting or modelling work before going home also change to E-6 (not for E-6 holders or unrestricted statuses such as F-2, F-4, F-5).'],
         notes_ko=[OFFICER_NOTE_KO], notes_en=[OFFICER_NOTE_EN])

guidance('E-6-2', 'status_change', state='GENERALLY_NOT_PERMITTED', completeness='SOURCE_ONLY',
         section='예술흥행(E-6) 체류자격 변경허가', anchor='호텔․흥행(E-6-2) 분야에 해당하는 활동은 체류자격 변경을 금지',
         summary_ko='예술흥행(E-6)으로의 자격변경은 E-6-1과 E-6-3에 한해 제한적으로 허용되며, 호텔·흥행(E-6-2) 분야에 해당하는 활동은 체류자격 변경이 금지됩니다.',
         summary_en='Changes to E-6 are allowed only on a limited basis for E-6-1 and E-6-3; a change of status for hotel/entertainment (E-6-2) activities is prohibited.')

def e6_post_report_docs():
    return [
        item('app_form_34', anchor='①신청서[별지 제34호 서식], 여권 및 외국인등록증, 수수료 없음'),
        item('passport', anchor='①신청서[별지 제34호 서식], 여권 및 외국인등록증, 수수료 없음'),
        item('arc', anchor='①신청서[별지 제34호 서식], 여권 및 외국인등록증, 수수료 없음'),
        item('business_reg', anchor='수수료 없음 ②사업자등록증', role='employer'),
        item('e67_prev_employer_consent', anchor='③원 근무처 장의 동의서 ④고용계약서 ⑤고용추천서',
             notes_ko='계약기간 만료일 또는 쌍방이 근무하기로 합의한 날짜까지 근무한 경우에는 제출이 면제되고, 원 근무처의 휴·폐업 및 임금체불 등의 사유가 있으면 입증서류 또는 사유서로 대체할 수 있습니다.',
             notes_en='Waived if you worked until the contract end or the agreed date; if the original workplace closed or failed to pay wages, proof or a statement of reasons can replace it.'),
        item('employment_contract', anchor='④고용계약서 ⑤고용추천서'),
        item('employment_recommendation', anchor='⑤고용추천서 또는 공연 추천서', role='employer'),
    ]


E6_POST_REPORT_SUMMARY_KO = '예술흥행(E-6) 중 E-6-1(예술·방송연예)과 E-6-3(운동선수·프로팀 감독·매니저)은 사전허가 없이 사후 신고로 근무처를 변경·추가할 수 있으며, 사유가 발생한 날로부터 15일 이내에 관할 청(사무소·출장소)장에게 신고합니다(대리인 신고 가능, 방문신고 원칙). 호텔·유흥(E-6-2)은 이 신고 대상이 아니며 별도 절차를 따릅니다.'
E6_POST_REPORT_SUMMARY_EN = 'E-6-1 (arts/broadcast entertainment) and E-6-3 (athletes, pro-team coaches, managers) change or add a workplace by reporting afterwards, within 15 days of the change, to the local immigration office (a proxy may file; in-person filing is the rule). Hotel/entertainment (E-6-2) is not covered and follows a separate procedure.'
E6_POST_REPORT_CONDITIONS_KO = ['자격요건을 갖추었더라도 본인 귀책사유로 해고 또는 중도 퇴직한 자로서 원고용주의 이적동의를 받지 못한 자는 제외됩니다.', '사유서와 신원보증서는 원칙적으로 제출이 생략됩니다.']
E6_POST_REPORT_CONDITIONS_EN = ['Excluded: people dismissed or who quit early through their own fault without the original employer\'s transfer consent.', 'A statement of reasons and a letter of guarantee are in principle not required.']

for _proc in ('workplace_change', 'workplace_report'):
    guidance('E-6', _proc, section='예술흥행(E-6) 근무처의 변경․추가 — 사후 신고대상 E-6-1, E-6-3', anchor='호텔업 시설, 유흥업소 공연활동 종사자(E-6-2)를 제외한 예술흥행(E-6) 자격으로 외국인등록을 하고',
             summary_ko=E6_POST_REPORT_SUMMARY_KO, summary_en=E6_POST_REPORT_SUMMARY_EN,
             timing_ko='사유가 발생한 날로부터 15일 이내', timing_en='Within 15 days of the change', fee_ko='수수료 없음', fee_en='No fee',
             conditions_ko=E6_POST_REPORT_CONDITIONS_KO, conditions_en=E6_POST_REPORT_CONDITIONS_EN,
             docs=e6_post_report_docs(), notes_ko=[OFFICER_NOTE_KO], notes_en=[OFFICER_NOTE_EN])

guidance('E-6-2', 'workplace_change', section='예술흥행(E-6) 근무처의 변경․추가 — E-6-2 사전 허가대상 1. 고용주 변동이 있는 경우', anchor='소속된 공연기획사 등이 변경되거나 추가되어 고용주 변동이 있는 경우',
         summary_ko='호텔·유흥(E-6-2) 연예인은 소속된 공연기획사 등이 변경되거나 추가되어 고용주가 바뀌는 경우 미리 관할 출입국·외국인청장 등에게 허가를 신청해야 하며, 청장 등은 서류를 심사하여 최대 1년의 범위 내에서 고용계약기간 동안 체류기간을 부여합니다. 고용주 변동 없이 공연장소만 바꾸는 것은 허가 대상이 아니라 고용주 신고사항입니다.',
         summary_en='E-6-2 hotel/entertainment performers whose agency changes or is added (a change of employer) must apply in advance to the immigration office; the stay is granted for the contract period, up to 1 year. Changing only the venue without a change of employer is not a permit matter but an employer report.',
         period_ko='최대 1년의 범위 내에서 고용계약기간', period_en='The employment contract period, up to 1 year',
         docs=[item('app_form_34', anchor='①신청서(별지 제34호 서식), 여권 및 외국인등록증, 수수료 ②사업자등록증'),
               item('passport', anchor='①신청서(별지 제34호 서식), 여권 및 외국인등록증, 수수료 ②사업자등록증'),
               item('arc', anchor='①신청서(별지 제34호 서식), 여권 및 외국인등록증, 수수료 ②사업자등록증'),
               item('fee', anchor='①신청서(별지 제34호 서식), 여권 및 외국인등록증, 수수료 ②사업자등록증'),
               item('business_reg', anchor='①신청서(별지 제34호 서식), 여권 및 외국인등록증, 수수료 ②사업자등록증', role='employer'),
               item('e67_prev_employer_consent', anchor='원 근무처 장의 동의서 ④고용계약서 ⑤공연 추천서(영상물등급위원회 발행)'),
               item('employment_contract', anchor='④고용계약서 ⑤공연 추천서(영상물등급위원회 발행)'),
               item('e67_perf_rec_kmrb_issued', anchor='⑤공연 추천서(영상물등급위원회 발행)'),
               item('guarantor_original_occupations', anchor='신원보증서 원본', role='employer')],
         notes_ko=[OFFICER_NOTE_KO], notes_en=[OFFICER_NOTE_EN])

guidance('E-6-2', 'workplace_report', filer='employer', section='예술흥행(E-6) 근무처의 변경․추가 — E-6-2 2. 고용주 변동 없이 공연장소를 변경·추가하는 경우(고용주 신고사항)', anchor='파견근로자보호법령 절차에 따라 공연장소를 변경하거나 추가하는 경우(고용주 신고사항)',
         summary_ko='호텔·유흥(E-6-2) 연예인이 파견사업자(고용주)의 변동 없이 파견근로자보호법령 절차에 따라 공연장소를 변경하거나 추가하는 경우, 고용주가 변경일로부터 15일 이내에 관할 출입국·외국인청장 등에게 고용변동 신고를 합니다. 입국 후 6개월 이내에는 공연장소를 변경할 수 없으며, 원 공연장소의 휴·폐업 등 부득이한 사정이 있는 경우에만 가능합니다.',
         summary_en='When an E-6-2 performer\'s venue changes or is added under the Worker Dispatch Act without a change of the dispatching employer, the employer reports the employment change to the immigration office within 15 days. The venue cannot be changed within 6 months of entry unless the original venue closed or there is another unavoidable reason.',
         timing_ko='공연장소 변경일로부터 15일 이내', timing_en='Within 15 days of the venue change',
         docs=[item('e67_employment_change_report', anchor='①고용‧연수외국인 변동사유 발생신고서(별지 제32호 서식)', role='employer'),
               item('passport_and_arc', anchor='①고용‧연수외국인 변동사유 발생신고서(별지 제32호 서식), 여권 및 외국인등록증'),
               item('e67_biz_reg_both', anchor='②사업자등록증(파견사업주, 사용사업주 모두)'),
               item('e67_employer_id_or_staff', anchor='③고용주 신분증(직원의 경우 위임장, 재직증명서, 직원신분증)'),
               item('e67_dispatch_contract', anchor='④파견사업자와 사용사업주 간 파견근로계약서'),
               item('e67_perf_rec_kmrb_issued', anchor='④파견사업자와 사용사업주 간 파견근로계약서 ⑤공연 추천서(영상물등급위원회 발행)'),
               item('e67_venue_facility_cert', anchor='⑥공연장소 시설확인서')],
         notes_ko=[OFFICER_NOTE_KO], notes_en=[OFFICER_NOTE_EN])

reentry_rule('E-6', '예술흥행(E-6) 재입국허가', '체류기간이 1년보다 적게 남아있는 경우 체류기간 범위 내에서 재입국허가 면제',
             '신청서류 : 신청서(별지 34호서식), 여권 원본, 외국인등록증, 수수료')

# ==========================================================================
# E-10 선원취업 — 사증 (visa manual p. 295~)
# ==========================================================================
guidance('E-10', 'visa_issuance', manual=VISA, completeness='PARTIALLY_STRUCTURED',
         section='선원취업(E-10) — 공관장 재량으로 발급할 수 있는 사증', anchor='선원취업(E-10) 사증은 출입국ㆍ외국인청(사무소ㆍ출장소)장이 발급한 사증발급인정서에 의해서만 발급',
         summary_ko='선원취업(E-10) 사증은 출입국·외국인청(사무소·출장소)장이 발급한 사증발급인정서에 의해서만 발급되며, 사증발급 접수 시 범죄경력증명서와 건강상태 확인서를 내야 합니다.',
         summary_en='E-10 visas are issued only on the basis of a confirmation of visa issuance from an immigration office, and a criminal record certificate and a health-status statement must be submitted when applying for the visa.',
         docs=[item('e67_crime_record_national', anchor='국적국의 권한 있는 기관이 발급한 범죄경력증명서 제출',
                    notes_ko='자국 내의 모든 범죄경력이 포함되고 사증발급 신청일로부터 3개월 이내에 발급된 것이어야 합니다. 국적국의 확인 시스템이 미흡하면 거주지 관할 내무기관 등의 증명서로 대체할 수 있습니다.',
                    notes_en='Must cover all criminal records in your country and be issued within 3 months of the visa application; if your country\'s system is inadequate, a certificate from the local interior authority may be used instead.'),
               item('e67_health_statement', anchor='사증신청인이 자필 기재한 【붙임 3】양식의 건강상태 확인서를 제출',
                    notes_ko='결핵·B형간염·매독 등의 감염 여부, 마약복용 경험, 정신질환으로 인한 치료경험 등을 본인이 기재합니다.',
                    notes_en='You state in your own hand any tuberculosis, hepatitis B or syphilis infection, drug use, and psychiatric treatment.')],
         notes_ko=[OFFICER_NOTE_KO], notes_en=[OFFICER_NOTE_EN])

guidance('E-10', 'visa_issuance_confirmation', manual=VISA, doc_page_window=3,
         section='선원취업(E-10) — 사증발급인정서 발급대상 2. 사증발급인정신청서 접수처리 (첨부서류)', anchor='면허증 또는 등록증 상의 회사소재지 또는 동 회사의 ‘주된 영업소’가 있는 지역 관할',
         summary_ko='선원취업(E-10) 사증발급인정서는 고용주(초청업체의 장)가 면허증 또는 등록증 상의 회사소재지나 주된 영업소 관할 출입국·외국인청(사무소·출장소)에 신청하며, 업종별 대행기관(내항상선·순항여객선은 한국해운조합, 어선은 수협중앙회)의 신청 대행도 허용됩니다. 공통서류에 더해 내항선원(E-10-1), 어선원(E-10-2), 순항여객선원(E-10-3)별 추가서류를 냅니다.',
         summary_en='The employer files the E-10 confirmation at the immigration office for the company address or main place of business on its licence/registration; filing by the sector agency (Korea Shipping Association for coastal and cruise ships, NFFC for fishing vessels) is also allowed. Common documents plus extra documents by sector: coastal (E-10-1), fishing (E-10-2), cruise (E-10-3).',
         filer='employer',
         docs=[item('e67_cvi_form', anchor='① 사증발급인정신청서 (별지 제21호 서식), 여권, 사업자 등록증, 표준규격사진 1매'),
               item('passport', anchor='① 사증발급인정신청서 (별지 제21호 서식), 여권, 사업자 등록증, 표준규격사진 1매'),
               item('business_reg', anchor='① 사증발급인정신청서 (별지 제21호 서식), 여권, 사업자 등록증, 표준규격사진 1매', role='ship_owner'),
               item('photo', anchor='① 사증발급인정신청서 (별지 제21호 서식), 여권, 사업자 등록증, 표준규격사진 1매'),
               item('standard_contract_copy', anchor='② 표준근로계약서 사본', role='ship_owner'),
               item('guarantor', anchor='③ 신원보증서', role='ship_owner'),
               item('e67_seafarer_report_acceptance', anchor='④ 외국인선원고용신고수리서(지방해양항만청장 발급)'),
               item('e67_coastal_license_copy', 'CONDITIONAL_REQUIRED', anchor='󰡔해운법󰡕에 따른 내항여객운송사업면허증․내항화물운송사업등록증 사본',
                    applies_when_ko='내항선원(E-10-1), 최초 신청 또는 등록사항 변경 시', applies_when_en='Coastal seafarers (E-10-1), first application or registration change'),
               item('seafarer_recommendation_regional', 'CONDITIONAL_REQUIRED', anchor='외국인선원고용추천서(지방해양수산청장 발급)', role='ship_owner',
                    applies_when_ko='내항선원(E-10-1), 어선원(E-10-2), 순항여객선원(E-10-3) 업종별 추가서류', applies_when_en='Sector-specific extra document for E-10-1, E-10-2 and E-10-3'),
               item('e67_crew_capacity_cert', 'CONDITIONAL_REQUIRED', anchor='‘승선정원증서’ 또는 ‘500톤 미만 선박검사증서’ 등 기타',
                    applies_when_ko='내항선원(E-10-1)', applies_when_en='Coastal seafarers (E-10-1)'),
               item('e67_to_approval', 'CONDITIONAL_REQUIRED', anchor='노사합의 선사별 T/O 운영승인서 (선사별 총 정원제 적용 업체의 경우)',
                    applies_when_ko='내항선원(E-10-1), 선사별 총 정원제 적용 업체의 경우', applies_when_en='Coastal seafarers (E-10-1), companies under a per-company quota'),
               item('e67_fishery_license_copy', 'CONDITIONAL_REQUIRED', anchor='󰡔수산업법󰡕에 따른 정치망어업면허증 및 관리선사용지정(어선사용승인)증․근해어업허가증 사본',
                    applies_when_ko='어선원(E-10-2), 최초 신청 또는 등록사항 변경 시', applies_when_en='Fishing crew (E-10-2), first application or registration change'),
               item('e67_ship_inspection_cert', 'CONDITIONAL_REQUIRED', anchor='⑥ 선박검사증서',
                    applies_when_ko='어선원(E-10-2)', applies_when_en='Fishing crew (E-10-2)'),
               item('e67_fish_transport_reg', 'CONDITIONAL_REQUIRED', anchor='⑧ 어획물운반업등록증 (어획물운반업만 해당)',
                    applies_when_ko='어선원(E-10-2), 어획물운반업만 해당', applies_when_en='Fishing crew (E-10-2), catch-transport business only'),
               item('e67_cruise_license_copy', 'CONDITIONAL_REQUIRED', anchor='⑥ 순항여객운송사업면허증 사본(최초 신청 또는 등록사항',
                    applies_when_ko='순항여객선원(E-10-3), 최초 신청 또는 등록사항 변경 시', applies_when_en='Cruise crew (E-10-3), first application or registration change')],
         notes_ko=[OFFICER_NOTE_KO], notes_en=[OFFICER_NOTE_EN])

# ==========================================================================
# E-10 선원취업 — 체류 (stay manual pp. 338–340)
# ==========================================================================
guidance('E-10-2', 'activities_outside_status', state='CONDITIONAL', completeness='SOURCE_ONLY',
         section='선원취업(E-10) 체류자격외 활동 — 어선원(E-10-2) 「체류자격 외 활동」허가', anchor='어선원(E-10-2) 「체류자격 외 활동」허가',
         summary_ko='어선원(E-10-2)은 어획물에 대한 건조, 포장 등 어획물과 연계된 작업활동에 대해 비전문취업(E-9) 체류자격외 활동허가를 받을 수 있습니다. 원 고용주와 활동 예정 근무지 고용주가 같고 어획→위판 과정의 어획물 생산활동에 부수되는 작업이어야 하며, 조업기 중(금어기 중 신청 가능), 실제 근무 외국인선원의 1/3 이내, 체류허가기간의 1/3 이내로 허용됩니다.',
         summary_en='Fishing crew (E-10-2) can get outside-status permission for E-9 activities linked to the catch, such as drying and packing. The employer at the intended workplace must be the original employer and the work must be incidental to catch production up to the auction; it is allowed during the fishing season (applications possible in the closed season), for at most 1/3 of the foreign crew actually working on the vessel and for at most 1/3 of the stay period.')

guidance('E-10', 'workplace_change', section='선원취업(E-10) 근무처의 변경․추가', anchor='선원취업자가 사업장의 휴․폐업 등으로 정상적인 근로관계를 지속하기 곤란한 때에는',
         summary_ko='선원취업자는 사업장의 휴·폐업 등으로 정상적인 근로관계를 지속하기 곤란할 때 지방해양수산청장의 추천을 받아 근무처 변경을 신청할 수 있습니다. 동일 선사(선주)의 선박 간 이동근무 시에도 미리 근무처변경 허가를 받아야 하며, 이 경우 수수료는 면제됩니다.',
         summary_en='E-10 seafarers may apply for a change of workplace, with the regional maritime office\'s recommendation, when the business closes or the employment relationship otherwise cannot continue normally. Moving between ships of the same shipowner also needs prior permission, but without a fee.',
         docs=base_stay(anchor='① 신청서(별지 34호서식), 여권 및 외국인등록증, 수수료') + [
             item('e67_seafarer_rec_union', anchor='한국해운조합 또는 수산업협동조합중앙회 발급 외국인 고용추천서'),
             item('employment_contract', anchor='③ 고용계약서 ④ 사업자등록증', role='ship_owner'),
             item('business_reg', anchor='③ 고용계약서 ④ 사업자등록증', role='ship_owner'),
             item('e67_injury_docs', 'CONDITIONAL_REQUIRED', anchor='⑤ 산재서류 또는 진단서(필요시)', applies_when_ko='필요한 경우', applies_when_en='If needed'),
             item('guarantor', anchor='⑤ 산재서류 또는 진단서(필요시) ⑥ 신원보증서', role='ship_owner'),
         ],
         notes_ko=[OFFICER_NOTE_KO], notes_en=[OFFICER_NOTE_EN])

guidance('E-10', 'reentry', state='CONDITIONAL', completeness='SOURCE_ONLY',
         section='선원취업(E-10) 재입국허가', anchor='등록을 필한 외국인이 출국한 날부터 1년 이내에 재입국하려는 경우 재입국허가 면제',
         summary_ko='등록을 마친 외국인은 출국한 날부터 1년 이내(남은 체류기간이 1년보다 짧으면 그 범위 내)에 재입국하면 재입국허가가 면제됩니다. 다만 입국규제 및 사증발급규제자는 체류지 관할 청(사무소·출장소)을 방문하여 재입국허가를 받아야 합니다.',
         summary_en='Registered foreigners re-entering within one year of departure (or within the remaining stay if shorter) are exempt from the re-entry permit. People subject to entry or visa restrictions must visit the local immigration office to get a permit.')

# ==========================================================================
# E-7 특정활동 — 사증 (visa manual pp. 170~)
# ==========================================================================
guidance('E-7', 'visa_issuance', manual=VISA, completeness='PARTIALLY_STRUCTURED', doc_page_window=3,
         section='특정활동(E-7) — 공관장 재량으로 발급할 수 있는 사증', anchor='주한 외국공관에서 고용하는 행정요원 등(자국 국민에 한함)에 대한',
         summary_ko='공관장 재량으로 발급하는 특정활동(E-7) 사증은 ① 주한 외국공관 등에서 고용하는 자국 국적의 행정·기능요원(특수기관 행정요원, S2620)과 ② 국내 운수회사 등에 고용되어 국제여객선 등에서 근무하는 승무원(운송서비스 종사자, 431)에 대한 체류기간 1년 이하, 유효기간 3월의 단수사증입니다. E-7 허용직종에 90일 이하 단기간 취업하는 사람은 단기취업(C-4-5) 사증을 받습니다. 그 밖의 E-7은 사증발급인정서 절차를 따릅니다.',
         summary_en='Missions may issue an E-7 visa at their discretion only to (1) administrative/technical staff of their own nationality employed by foreign missions in Korea (S2620) and (2) crew employed by Korean transport companies on international passenger ships etc. (431): a single-entry visa for a stay of up to 1 year, valid 3 months. Work of 90 days or less in an E-7 occupation takes a short-term employment (C-4-5) visa. Other E-7 cases use the confirmation-of-visa-issuance route.',
         docs=[item('e67_visa_form', anchor='① 사증발급신청서 (별지 제17호 서식), 여권, 표준규격사진 1매, 수수료 ② 주한 외국공관 협조요청 공문'),
               item('passport', anchor='① 사증발급신청서 (별지 제17호 서식), 여권, 표준규격사진 1매, 수수료 ② 주한 외국공관 협조요청 공문'),
               item('photo', anchor='① 사증발급신청서 (별지 제17호 서식), 여권, 표준규격사진 1매, 수수료 ② 주한 외국공관 협조요청 공문'),
               item('fee', anchor='① 사증발급신청서 (별지 제17호 서식), 여권, 표준규격사진 1매, 수수료 ② 주한 외국공관 협조요청 공문'),
               item('employment_contract', anchor='③ 고용계약서 ④ 학력 및 경력 등 입증서류'),
               item('e67_mission_request_letter', 'CONDITIONAL_REQUIRED', anchor='② 주한 외국공관 협조요청 공문',
                    applies_when_ko='주한 외국공관 등에서 고용하는 행정·기능요원(S2620)', applies_when_en='Administrative/technical staff of a foreign mission in Korea (S2620)'),
               item('e67_edu_career_proof', 'CONDITIONAL_REQUIRED', anchor='④ 학력 및 경력 등 입증서류 등',
                    applies_when_ko='주한 외국공관 등에서 고용하는 행정·기능요원(S2620)', applies_when_en='Administrative/technical staff of a foreign mission in Korea (S2620)'),
               item('e67_employer_establishment', 'CONDITIONAL_REQUIRED', anchor='② 고용업체 설립관련서류',
                    applies_when_ko='국내 운수회사 등에 고용된 선박 등의 승무원(431)', applies_when_en='Crew employed by a Korean transport company (431)'),
               item('e67_edu_career_proof', 'CONDITIONAL_REQUIRED', anchor='학위증, 경력증명서, 이력서, 자격증 등 포함',
                    applies_when_ko='국내 운수회사 등에 고용된 선박 등의 승무원(431): 학위증, 경력증명서, 이력서, 자격증 등 포함', applies_when_en='Crew employed by a Korean transport company (431): degree, career certificate, CV, licences, etc.')],
         conditions_ko=['고용계약기간이 2년이라 하더라도 체류기간 1년의 사증이 발급됩니다.', '제3국인을 행정·기능요원으로 고용한 경우에는 법무부장관의 승인을 받거나 사증발급인정서를 제출받아 사증을 발급합니다.'],
         conditions_en=['Even with a 2-year contract the visa is issued for a 1-year stay.', 'Third-country nationals employed as administrative/technical staff need the Justice Minister\'s approval or a confirmation of visa issuance.'],
         notes_ko=['재외공관의 장은 입국목적, 초청의 진정성, 초청자 및 피초청자의 자격 확인 등을 심사하기 위해 필요한 경우 첨부서류를 일부 가감할 수 있습니다.', OFFICER_NOTE_KO],
         notes_en=['The head of the mission may add or omit documents to check the purpose of entry, the genuineness of the invitation and the parties\' eligibility.', OFFICER_NOTE_EN])

guidance('E-7', 'visa_issuance_confirmation', manual=VISA, completeness='PARTIALLY_STRUCTURED', doc_page_window=3,
         section='특정활동(E-7) — 사증발급인정서 발급대상 2. 공통 제출서류 및 신청절차', anchor='초청업체 소재지 관할 출입국ㆍ외국인청(사무소ㆍ출장소)에 신청하고',
         summary_ko='특정활동(E-7) 사증발급인정서는 초청업체 소재지 관할 출입국·외국인청(사무소·출장소)에 신청하며, 주무부처 등의 우수인재 고용추천을 받은 경우 온라인(대한민국 비자포털)으로도 신청할 수 있습니다. 아래 공통 제출서류에 더해 직종별 세부심사기준에 따른 추가 서류를 냅니다.',
         summary_en='The E-7 confirmation is filed at the immigration office for the inviting company\'s location, or online (Korea Visa Portal) if a ministry etc. has recommended the hire as top talent. Submit the common documents below plus any extra documents under the occupation-specific criteria.',
         docs=[item('e67_cvi_form', anchor='① 사증발급인정신청서 (별지 제21호 서식), 여권사본, 표준규격사진 1매 ② 공․사기관 설립관련 서류'),
               item('passport_copy', anchor='① 사증발급인정신청서 (별지 제21호 서식), 여권사본, 표준규격사진 1매 ② 공․사기관 설립관련 서류'),
               item('photo', anchor='① 사증발급인정신청서 (별지 제21호 서식), 여권사본, 표준규격사진 1매 ② 공․사기관 설립관련 서류'),
               item('e67_org_establishment_e7', anchor='사업자등록증, 고유번호증, 외국인투자기업등록증 등'),
               item('e67_contract_copy', anchor='③ 고용계약서 사본 ④ 납세증명서(국세완납증명서), 지방세 납세증명서'),
               item('e67_tax_certs_visa', anchor='④ 납세증명서(국세완납증명서), 지방세 납세증명서'),
               item('e67_employment_need_proof', anchor='외국인의 고용의 필요성을 입증할 수 있는 서류',
                    notes_ko='매뉴얼이 정한 주무부처 고용추천 필수 직종(국내복귀기업의 생산관리자, 생명과학전문가, 호텔접수사무원, 의료코디네이터, 조선 용접공, 도축원 등)은 소관 중앙행정기관의 장의 고용추천서가 필요합니다.',
                    notes_en='For the occupations the manual lists as requiring a ministry recommendation (e.g. production managers of reshored companies, life-science experts, hotel receptionists, medical coordinators, ship welders, slaughterers), the competent ministry\'s recommendation is required.'),
               item('guarantor', 'CONDITIONAL_REQUIRED', anchor='신원보증서 제출이 필요한 직종',
                    applies_when_ko=GUARANTOR_E7_OCCUPATIONS_KO, applies_when_en=GUARANTOR_E7_OCCUPATIONS_EN),
               item('e67_qualification_proof', anchor='학위증, 경력증명서, 이력서, 유효한 자격증 등'),
               item('e67_occupation_extra_docs', 'SOURCE_MENTIONS_BUT_NOT_STRUCTURED', anchor='직종별 세부심사기준 (직종 설명, 자격요건, 심사기준, 추가 제출서류 등)',
                    notes_ko='직종별 추가 제출서류는 매뉴얼 후단 별첨의 직종별 세부심사기준을 확인하세요.', notes_en='See the occupation-specific criteria annexed at the end of the chapter for extra documents.'),
               item('e67_proxy_docs', 'CONDITIONAL_REQUIRED', anchor='대리인 신청 시 : 위임장, 대리인 재직증명서, 대리인 신분증 사본 추가 필요',
                    applies_when_ko='대리인이 신청하는 경우', applies_when_en='When a proxy files')],
         conditions_ko=['KOTRA·중진공의 골드카드 고용추천을 받은 경우 온라인 신청 시 고용추천서 외 첨부서류가 면제되고 나머지 서류는 외국인등록 시 제출합니다.',
                        '국세청 지정 성실납세기업, 대한민국 일자리 으뜸기업, 동반성장지수 평가 우수(양호)기업, 출소자·제대군인 고용 우수기업은 고용업체 설립 관련 서류 및 고용의 필요성 입증서류 등이 면제됩니다.'],
         conditions_en=['With a KOTRA/KOSME Gold Card recommendation, an online application needs only the recommendation; the rest is submitted at registration.',
                        'Designated compliant or socially contributing companies (NTS faithful taxpayers, best job-creating companies, shared-growth top-rated companies, companies hiring ex-offenders or veterans) are exempt from the establishment documents and proof of need to employ.'],
         notes_ko=['출입국·외국인청(사무소·출장소)장은 초청의 진정성, 초청자 및 피초청자의 자격 확인 등을 심사하기 위해 첨부서류의 일부를 가감할 수 있습니다.', OFFICER_NOTE_KO],
         notes_en=['The immigration office may add or omit documents to check the genuineness of the invitation and the parties\' eligibility.', OFFICER_NOTE_EN])

for _code in ('E-7-91', 'E-7-91FTA'):
  guidance(_code, 'visa_issuance_confirmation', manual=VISA, completeness='PARTIALLY_STRUCTURED',
         section='특정활동(E-7) — 3. 국가 간 근로협정 등 적용대상자 가. 한․인도 사증절차간소화협정 관련 사증발급 대상자 (독립전문가)', anchor='한․인도 사증절차간소화협정 관련 사증발급 대상자',
         summary_ko='한·인도 협정에 따른 독립전문가는 인도 법인에 소속되지 않은 자영업자로서 우리나라 법인 또는 개인과 서비스 공급계약을 체결해 입국하는 사람이며, 한-인도 CEPA 전문가 양허직종(162개) 관련 학사 이상 학위와 해당 분야 1년 이상 경력이 필요합니다(생물학자·생화학자는 박사학위 또는 동등 자격).',
         summary_en='Independent professionals under the Korea–India agreement are self-employed people not attached to an Indian company who enter to perform a service-supply contract with a Korean company or individual; they need a bachelor\'s or higher degree related to one of the 162 CEPA professional occupations and 1+ year of experience (biologists and biochemists: a doctorate or equivalent).',
         docs=[item('e67_cvi_form', anchor='① 사증발급인정신청서 (별지 제21호 서식), 여권사본, 표준규격사진 1매 ② 본인과 국내법인'),
               item('passport_copy', anchor='① 사증발급인정신청서 (별지 제21호 서식), 여권사본, 표준규격사진 1매 ② 본인과 국내법인'),
               item('photo', anchor='① 사증발급인정신청서 (별지 제21호 서식), 여권사본, 표준규격사진 1매 ② 본인과 국내법인'),
               item('e67_service_contract', anchor='본인과 국내법인 또는 개인사업자 간의 서비스공급 계약서'),
               item('e67_corp_reg_or_biz', anchor='국내법인 또는 개인사업자의 법인등기부등본 또는 사업자등록증 사본'),
               item('e67_tax_fact_cert', anchor='④ 납세사실증명서'),
               item('e67_edu_career_cepa', anchor='⑤ 학력입증서류, 경력입증서류'),
               item('e67_service_need', anchor='서비스공급의 필요성을 입증할 수 있는 서류'),
               item('e67_occupation_docs_cepa', 'SOURCE_MENTIONS_BUT_NOT_STRUCTURED', anchor='⑦ 기타 직종별 첨부서류'),
               item('e67_proxy_docs', 'CONDITIONAL_REQUIRED', anchor='대리인 신청 시 : 위임장, 대리인 재직증명서, 대리인 신분증 사본 추가 필요',
                    applies_when_ko='대리인이 신청하는 경우', applies_when_en='When a proxy files')],
         notes_ko=['출입국·외국인청(사무소·출장소)장은 초청의 진정성, 초청자 및 피초청자의 자격 확인 등을 심사하기 위해 첨부서류의 일부를 가감할 수 있습니다.', OFFICER_NOTE_KO],
         notes_en=['The immigration office may add or omit documents to check the genuineness of the invitation and the parties\' eligibility.', OFFICER_NOTE_EN])

guidance('E-7-4', 'visa_issuance_confirmation', manual=VISA, state='SOURCE_ONLY', completeness='SOURCE_ONLY',
         section='특정활동(E-7) — 숙련기능 점수제 종사자 (3개 직종, E-7-4)', anchor='숙련기능인력(E-7-4) 체류관리 기준 참조',
         summary_ko='숙련기능 점수제 종사자(E-7-4)는 사증발급 안내매뉴얼의 E-7 직종별 기준에서 별도로 다루지 않고 숙련기능인력(E-7-4) 체류관리 기준을 참조하도록 되어 있습니다. 원문을 확인하세요.',
         summary_en='For skilled points-system workers (E-7-4), the visa manual\'s E-7 occupation criteria refer to the separate E-7-4 stay-management standard. Check the original source.')

guidance('E-7', 'electronic_visa', manual=VISA, state='CONDITIONAL', completeness='SOURCE_ONLY',
         section='전자사증 — 전문인력 및 전문인력의 동반가족', anchor='전문직업(E-5), 첨단과학기술분야 고용추천서(GOLD CARD',
         summary_ko='특정활동(E-7) 중 전자사증 대상은 첨단과학기술분야 고용추천서(GOLD CARD)를 발급받은 사람입니다. 골드카드 고용추천서는 KOTRA 또는 중소기업진흥공단이 국내 공·사기관에서 근무하려는 해외 우수기술인재에게 발급합니다.',
         summary_en='Within E-7, only holders of a high-tech employment recommendation (GOLD CARD) are eligible for an electronic visa. The Gold Card recommendation is issued by KOTRA or the Korea SMEs and Startups Agency to highly skilled overseas talent who will work for a Korean public or private organization.')

# ==========================================================================
# E-7 특정활동 — 체류 (stay manual pp. 220–229)
# ==========================================================================
E7_TEACHER_KO = '외국인학교 교사로 근무하기 위해 채용 절차를 밟고 있는 합법체류자 (4. 외국인학교 교사(E-7)로의 자격변경)'
E7_TEACHER_EN = 'Lawful residents being hired as foreign-school teachers (section 4)'
E7_IT_KO = '부득이한 사유로 무사증 입국하거나 비취업사증을 소지한 첨단기술분야 외국 우수인력 (5. IT·e-business·BT·NT 등 분야)'
E7_IT_EN = 'Highly skilled high-tech professionals who entered visa-free or on a non-work visa for an unavoidable reason (section 5: IT, e-business, BT, NT, etc.)'
E7_FROM_LONG_KO = 'D-1, D-2, D-4~D-10, E-1~E-6(E-6-2 제외) 자격으로 합법 체류 중인 등록외국인 및 그 동반 배우자(F-3) (2. 특정활동(E-7)자격으로의 변경)'
E7_FROM_LONG_EN = 'Registered foreigners lawfully staying as D-1, D-2, D-4–D-10 or E-1–E-6 (not E-6-2), and their F-3 spouses (section 2)'

guidance('E-7', 'status_change', completeness='PARTIALLY_STRUCTURED', doc_page_window=3,
         section='특정활동(E-7) 체류자격 변경허가 — 1. 일반기준, 2. 장기체류자격 → E-7, 4. 외국인학교 교사, 5. 첨단기술분야 우수인력', anchor='특정활동(E-7) 자격 허용직종별 요건을 갖춘 체류외국인',
         summary_ko='특정활동(E-7) 허용직종별 요건을 갖춘 체류외국인은 E-7으로 자격을 변경할 수 있으며, 첨부서류와 심사기준은 사증발급인정서 신청 시의 것을 준용합니다. 단기체류(B·C 계열), 기술연수(D-3), 계절근로(E-8), 비전문취업(E-9), 선원취업(E-10), 기타(G-1) 자격은 자격변경이 제한됩니다. 장기체류자격 소지자, 외국인학교 교사, 첨단기술분야 우수인력은 아래의 유형별 서류를 냅니다.',
         summary_en='Foreigners in Korea who meet the requirements of an E-7 occupation can change to E-7; documents and criteria follow those of the confirmation-of-visa-issuance application. Changes from short-term (B, C), D-3, E-8, E-9, E-10 and G-1 are restricted. Long-term status holders, foreign-school teachers and high-tech professionals submit the documents listed by type below.',
         docs=[item('app_form_34', anchor='①신청서(별지 34호서식), 여권 및 외국인등록증, 표준규격사진 1장, 수수료 ②고용계약서 ③고용업체'),
               item('passport', anchor='①신청서(별지 34호서식), 여권 및 외국인등록증, 표준규격사진 1장, 수수료 ②고용계약서 ③고용업체'),
               item('arc', anchor='①신청서(별지 34호서식), 여권 및 외국인등록증, 표준규격사진 1장, 수수료 ②고용계약서 ③고용업체'),
               item('photo1', anchor='①신청서(별지 34호서식), 여권 및 외국인등록증, 표준규격사진 1장, 수수료 ②고용계약서 ③고용업체'),
               item('fee', anchor='①신청서(별지 34호서식), 여권 및 외국인등록증, 표준규격사진 1장, 수수료 ②고용계약서 ③고용업체'),
               item('employment_contract', anchor='②고용계약서 ③고용업체 등 설립관련 서류'),
               item('e67_tax_certs_stay', anchor='납세증명서(국세완납증명서), 지방세 납세증명',
                    notes_ko='2.·4.·5. 유형 모두 제출합니다.', notes_en='Required for sections 2, 4 and 5 alike.'),
               item('e67_employer_establishment_stay', 'CONDITIONAL_REQUIRED', anchor='③고용업체 등 설립관련 서류(사업자등록증, 등기부등본 등)',
                    applies_when_ko=E7_FROM_LONG_KO, applies_when_en=E7_FROM_LONG_EN),
               item('e67_career_cert', 'CONDITIONAL_REQUIRED', anchor='④ 경력증명서 ⑤ 주무부처 장의 고용추천서',
                    applies_when_ko=E7_FROM_LONG_KO, applies_when_en=E7_FROM_LONG_EN),
               item('e67_ministry_rec_or_need', 'CONDITIONAL_REQUIRED', anchor='⑤ 주무부처 장의 고용추천서 또는 고용의 필요성을 입증하는 서류',
                    applies_when_ko=E7_FROM_LONG_KO + ' — 국내 전문학사 및 학사학위 소지자는 학사+1년 이상 경력이 요구되는 직종에서도 고용추천서 제출 생략(고용추천 필수 직종 제외)',
                    applies_when_en=E7_FROM_LONG_EN + ' — Korean associate/bachelor graduates may omit the recommendation even for bachelor+1-year occupations (except where a recommendation is mandatory)'),
               item('e67_teacher_license', 'CONDITIONAL_REQUIRED', anchor='해당국 교원자격증(교원 자격증이 없는 경우 ‘학위증 및 경력증명서’)',
                    applies_when_ko=E7_TEACHER_KO, applies_when_en=E7_TEACHER_EN),
               item('e67_principal_recommendation', 'CONDITIONAL_REQUIRED', anchor='④ 학교장 추천서',
                    applies_when_ko=E7_TEACHER_KO, applies_when_en=E7_TEACHER_EN),
               item('e67_prev_employer_consent_if', 'CONDITIONAL_REQUIRED', anchor='⑤ 원 근무처 장의 동의서(해당자) ⑥ 신원보증서',
                    applies_when_ko=E7_TEACHER_KO + ' 중 해당자', applies_when_en=E7_TEACHER_EN + ', where applicable'),
               item('guarantor', 'CONDITIONAL_REQUIRED', anchor='⑥ 신원보증서 ⑦ 학교설립관련 서류',
                    applies_when_ko=E7_TEACHER_KO, applies_when_en=E7_TEACHER_EN),
               item('e67_school_establishment', 'CONDITIONAL_REQUIRED', anchor='⑦ 학교설립관련 서류',
                    applies_when_ko=E7_TEACHER_KO, applies_when_en=E7_TEACHER_EN),
               item('e67_criminal_record_e2', 'CONDITIONAL_REQUIRED', anchor='⑧ 범죄경력증명서(E-2 자격과 동일)',
                    applies_when_ko=E7_TEACHER_KO + ' — 해당국 교원자격증 소지자, 채용박람회를 통해 채용된 교사, 최근 5년 이내 국내에서 E-2 또는 E-7 교사로 3년 이상 근무한 자는 면제',
                    applies_when_en=E7_TEACHER_EN + ' — waived for holders of a teacher\'s licence, teachers hired through a recruitment fair, and those who taught in Korea as E-2 or E-7 for 3+ years in the last 5 years'),
               item('e67_medical_exam', 'CONDITIONAL_REQUIRED', anchor='⑧ 범죄경력증명서(E-2 자격과 동일) ⑨ 채용신체검사서',
                    applies_when_ko=E7_TEACHER_KO + ' — 법무부장관 지정 의료기관 발급, 마약검사 포함, 최근 3개월 이내 발급',
                    applies_when_en=E7_TEACHER_EN + ' — issued by a designated hospital within 3 months, including a drug test'),
               item('e67_career_or_degree', 'CONDITIONAL_REQUIRED', anchor='경력증명서(학사이상 학위소지자는 학위증 사본 첨부)',
                    applies_when_ko=E7_IT_KO, applies_when_en=E7_IT_EN),
               item('business_reg', 'CONDITIONAL_REQUIRED', anchor='④ 사업자등록증 ⑤ 소관부처장관의 고용추천서', role='employer',
                    applies_when_ko=E7_IT_KO, applies_when_en=E7_IT_EN),
               item('e67_minister_recommendation', 'CONDITIONAL_REQUIRED', anchor='⑤ 소관부처장관의 고용추천서',
                    applies_when_ko=E7_IT_KO, applies_when_en=E7_IT_EN)],
         conditions_ko=['원칙적으로 국민고용자의 20% 범위 내에서 E-7 외국인 고용이 허용되며, 5명 미만의 국민을 고용 중인 내수 위주 업체 등은 체류자격변경이 원칙적으로 불허됩니다(주무부처 추천 시 예외 기준 있음).',
                        '급여총액(연봉)이 당해연도 최저임금 기준 미만이면 제한되며, 고용계약서에 월 급여총액(연봉) 대비 근로시간을 명시해야 합니다.',
                        '외국인학교 교사로의 최초 자격변경 시 체류기간은 고용계약기간을 감안하여 1년 범위 내에서 부여됩니다.'],
         conditions_en=['E-7 hiring is in principle allowed up to 20% of the Korean workforce; domestic-market firms with fewer than 5 Korean employees etc. are in principle refused (exceptions with a ministry recommendation).',
                        'Pay below the current minimum wage is not accepted, and the contract must state working hours against the total monthly pay (annual salary).',
                        'A first change to foreign-school teacher is granted for up to 1 year, considering the contract period.'],
         notes_ko=[OFFICER_NOTE_KO], notes_en=[OFFICER_NOTE_EN])

guidance('E-7-4', 'status_change', state='SOURCE_ONLY', completeness='SOURCE_ONLY',
         section='특정활동(E-7) 체류자격 변경허가 — 6. 숙련기능인력 점수제 특정활동(E-7-4) 체류자격 변경허가', anchor='허가요건 등 세부사항은 숙련기능인력(E-7-4) 안내매뉴얼 참조',
         summary_ko='비전문취업(E-9) 자격 등으로 4년 이상 제조업 등에 합법취업 중인 사람의 숙련기능인력 점수제(E-7-4) 체류자격 변경허가는 허가요건 등 세부사항을 숙련기능인력(E-7-4) 안내매뉴얼에서 정합니다. 원문을 확인하세요.',
         summary_en='For changing to the skilled points-system E-7-4 after 4+ years of lawful work in manufacturing etc. (e.g. as E-9), the requirements and details are set in the separate E-7-4 guide. Check the original source.')

guidance('E-7', 'activities_outside_status', completeness='PARTIALLY_STRUCTURED', doc_page_window=3,
         section='특정활동(E-7) 체류자격외 활동 — 2. 우수전문인력의 대학 강연활동, 6.~8. F-1·F-3 자격 소지자의 E-7 활동', anchor='외국인투자기업 CEO 등 우수전문인력의 대학 강연활동',
         summary_ko='특정활동(E-7) 장의 체류자격외 활동은 유형별로 다릅니다. 전문인력(E-1, E-3~E-5, E-7) 자격 소지자 등은 대학에서 90일 이내 강의활동을 하려면 단기취업(C-4-5) 자격외 활동허가를 받고, 방문동거(F-1) 중국동포나 F-1·F-3 소지자가 E-7 활동(외국인학교 교사, 외국어교열요원 등)을 하려면 유형별 서류로 허가를 받습니다.',
         summary_en='Outside-status activities in the E-7 chapter vary by case. Professionals (E-1, E-3–E-5, E-7) etc. lecturing at a university for up to 90 days get permission for short-term employment (C-4-5); Chinese-Korean F-1 holders or F-1/F-3 holders taking E-7 work (foreign-school teacher, foreign-language editor, etc.) apply with the documents for their case.',
         docs=base_stay(anchor='①신청서(별지 34호 서식), 여권 및 외국인등록증, 수수료 ②주무부처 장의 고용추천서') + [
             item('e67_ministry_recommendation', 'CONDITIONAL_REQUIRED', anchor='②주무부처 장의 고용추천서 ③사업자등록증 사본',
                  applies_when_ko='대학에서 90일 이내 강의활동(C-4-5)을 하려는 투자자 등(D-7~D-9 상근이사 이상) 또는 전문인력(E-1, E-3~E-5, E-7)', applies_when_en='Investors etc. (D-7–D-9, standing director or above) or professionals (E-1, E-3–E-5, E-7) lecturing at a university for up to 90 days (C-4-5)'),
             item('business_reg_copy', 'CONDITIONAL_REQUIRED', anchor='③사업자등록증 사본 ④고용계약서 ⑤원 근무처장의 동의서', role='employer',
                  applies_when_ko='대학 강의활동(C-4-5) 또는 F-1·F-3 소지자의 외국어교열요원(E-7) 활동', applies_when_en='University lecturing (C-4-5) or F-1/F-3 holders working as foreign-language editors (E-7)'),
             item('employment_contract', 'CONDITIONAL_REQUIRED', anchor='④고용계약서 ⑤원 근무처장의 동의서',
                  applies_when_ko='대학 강의활동(C-4-5), F-1 중국동포의 E-7 활동, F-1·F-3 소지자의 외국인학교교사·외국어교열요원(E-7) 활동', applies_when_en='University lecturing (C-4-5), E-7 work by Chinese-Korean F-1 holders, or F-1/F-3 holders as foreign-school teachers or language editors'),
             item('e67_prev_employer_consent', 'CONDITIONAL_REQUIRED', anchor='⑤원 근무처장의 동의서',
                  applies_when_ko='대학 강의활동(C-4-5)을 하려는 경우', applies_when_en='University lecturing (C-4-5)'),
             item('e67_ministry_rec_or_need', 'CONDITIONAL_REQUIRED', anchor='② 주무부처 장의 고용추천서 또는 고용필요성 입증서류',
                  applies_when_ko='방문동거(F-1) 중국동포 중 취업자격 구비 등 요건에 해당하는 사람의 E-1~E-7 활동', applies_when_en='Chinese-Korean F-1 holders meeting the job requirements, for E-1–E-7 work'),
             item('business_reg', 'CONDITIONAL_REQUIRED', anchor='④ 사업자등록증 ⑤ 학위증 또는 자격증', role='employer',
                  applies_when_ko='방문동거(F-1) 중국동포의 E-1~E-7 활동, F-1·F-3 소지자의 외국인학교교사(E-7) 활동', applies_when_en='Chinese-Korean F-1 holders (E-1–E-7 work) or F-1/F-3 holders as foreign-school teachers (E-7)'),
             item('e67_degree_or_license', 'CONDITIONAL_REQUIRED', anchor='⑤ 학위증 또는 자격증',
                  applies_when_ko='방문동거(F-1) 중국동포의 E-1~E-7 활동', applies_when_en='Chinese-Korean F-1 holders, for E-1–E-7 work'),
             item('e67_teacher_license_original', 'CONDITIONAL_REQUIRED', anchor='해당국교원 자격증 원본(교원자격증이 없는 경우 ‘학위증 및 경력증명서’)',
                  applies_when_ko='F-1·F-3 소지자의 외국어회화강사(E-2)·외국인학교교사(E-7) 활동', applies_when_en='F-1/F-3 holders as conversation instructors (E-2) or foreign-school teachers (E-7)'),
             item('e67_criminal_record_e2', 'CONDITIONAL_REQUIRED', anchor='⑤범죄경력증명서(E-2 자격요건과 동일)',
                  applies_when_ko='F-1·F-3 소지자의 외국어회화강사(E-2)·외국인학교교사(E-7) 활동', applies_when_en='F-1/F-3 holders as conversation instructors (E-2) or foreign-school teachers (E-7)'),
             item('e67_medical_exam_e2', 'CONDITIONAL_REQUIRED', anchor='⑥채용신체검사서(E-2 자격요건과 동일)',
                  applies_when_ko='F-1·F-3 소지자의 외국어회화강사(E-2)·외국인학교교사(E-7) 활동', applies_when_en='F-1/F-3 holders as conversation instructors (E-2) or foreign-school teachers (E-7)'),
             item('e67_principal_request', 'CONDITIONAL_REQUIRED', anchor='⑦학교장 요청서',
                  applies_when_ko='F-1·F-3 소지자의 외국어회화강사(E-2)·외국인학교교사(E-7) 활동', applies_when_en='F-1/F-3 holders as conversation instructors (E-2) or foreign-school teachers (E-7)'),
             item('e67_foreign_teacher_status', 'CONDITIONAL_REQUIRED', anchor='⑧외국인교사 현황',
                  applies_when_ko='F-1·F-3 소지자의 외국어회화강사(E-2)·외국인학교교사(E-7) 활동', applies_when_en='F-1/F-3 holders as conversation instructors (E-2) or foreign-school teachers (E-7)'),
             item('e67_agency_head_rec', 'CONDITIONAL_REQUIRED', anchor='④ 추천서(해당 기관장)',
                  applies_when_ko='F-1·F-3 소지자의 국가기관 및 공공단체 외국어교열요원(E-7) 활동', applies_when_en='F-1/F-3 holders as foreign-language editors at state agencies or public bodies (E-7)'),
             item('e67_degree_original_copy', 'CONDITIONAL_REQUIRED', anchor='⑤ 학위증(원본 및 사본)',
                  applies_when_ko='F-1·F-3 소지자의 국가기관 및 공공단체 외국어교열요원(E-7) 활동', applies_when_en='F-1/F-3 holders as foreign-language editors at state agencies or public bodies (E-7)'),
         ],
         conditions_ko=['원래의 체류목적을 침해하지 않는 범위에서 정규교육기관(초·중·고 및 대학)의 교육을 받는 것은 체류기간 범위 내에서 별도 허가가 필요 없습니다.',
                        '주한외국공관원 가족의 국내취업은 상호주의에 따라 외교부장관(외교사절담당관)의 추천을 받은 사람에 한해 허가되며, A-1·A-2 소지자의 자격외활동은 외교부(외교사절담당관)의 고용추천서가 필수입니다.',
                        '전문 외국인력(E-1~E-5, E-6-2를 제외한 E-6, E-7) 등의 배우자는 단순노무(D-3, E-9) 등을 제외한 모든 직종에 대해 배우자의 체류기간까지 허가받을 수 있으며, 서류는 규칙 제76조의 체류자격별 첨부서류(신원보증서 생략)이고 E-7에 종사하려면 E-7 사증발급인정서 발급 지침을 준용합니다.',
                        '제주영어교육도시 종사자(국제학교 보조교사·강사 등, 상업시설 판매종사자)에 대한 별도 특례가 있습니다.'],
         conditions_en=['Attending a regular school (primary to university) without harming the original purpose of stay needs no separate permission within the stay period.',
                        'Family members of foreign mission staff may work only with the Foreign Minister\'s recommendation on a reciprocity basis; A-1/A-2 holders need an employment recommendation from the Ministry of Foreign Affairs.',
                        'Spouses of professional foreign workers (E-1–E-5, E-6 except E-6-2, E-7) etc. may work in any occupation except simple labour (D-3, E-9) up to the spouse\'s stay, with the Rule Art. 76 documents for that status (no letter of guarantee); for E-7 work the E-7 confirmation-of-visa-issuance guidelines apply.',
                        'There is a separate special rule for workers in the Jeju English Education City (international-school assistants/instructors, retail staff).'],
         notes_ko=[OFFICER_NOTE_KO], notes_en=[OFFICER_NOTE_EN])

guidance('E-7', 'workplace_change', completeness='PARTIALLY_STRUCTURED', doc_page_window=3,
         section='특정활동(E-7) 근무처의 변경․추가 — 1. 근무처변경 추가 신고, 2. 근무처 변경 추가 허가', anchor='판매사무원 등 14개 직종을 제외한 특정활동(E-7) 자격 소지자로서 외국인등록을 하고',
         summary_ko='특정활동(E-7)은 매뉴얼이 정한 사전 허가대상 직종을 제외하면 사후 신고로 근무처를 변경·추가할 수 있으며, 신고사유 발생일로부터 15일 이내에 관할 출입국·외국인청(사무소·출장소)장에게 신고합니다(대리인 신고 가능, 방문신고 원칙). 고용업체별 허용인원 제한 등으로 사전관리가 필요한 직종(판매사무원, 주방장 및 조리사, 숙련기능 점수제 종사자 등)은 미리 근무처 변경·추가 허가를 받아야 합니다.',
         summary_en='Except for the occupations the manual lists for prior permission, E-7 holders change or add a workplace by reporting within 15 days of the change to the local immigration office (a proxy may file; in-person filing is the rule). Occupations needing prior control because of per-employer quotas (sales clerks, chefs and cooks, skilled points-system workers, etc.) must get a workplace change/addition permit in advance.',
         docs=[item('e67_form_34_34_2', 'CONDITIONAL_REQUIRED', anchor='①통합신청서[별지 제34호~제34호의2 서식], 여권 및 외국인등록증, 수수료 없음',
                    applies_when_ko=E7_POST_REPORT_KO, applies_when_en=E7_POST_REPORT_EN),
               item('passport', 'CONDITIONAL_REQUIRED', anchor='①통합신청서[별지 제34호~제34호의2 서식], 여권 및 외국인등록증, 수수료 없음',
                    applies_when_ko=E7_POST_REPORT_KO, applies_when_en=E7_POST_REPORT_EN),
               item('arc', 'CONDITIONAL_REQUIRED', anchor='①통합신청서[별지 제34호~제34호의2 서식], 여권 및 외국인등록증, 수수료 없음',
                    applies_when_ko=E7_POST_REPORT_KO, applies_when_en=E7_POST_REPORT_EN),
               item('e67_ministry_rec_or_need', 'CONDITIONAL_REQUIRED', anchor='②주무부처 장의 고용추천서 또는 고용의 필요성을 입증하는 서류',
                    applies_when_ko=E7_POST_REPORT_KO, applies_when_en=E7_POST_REPORT_EN),
               item('employment_contract', 'CONDITIONAL_REQUIRED', anchor='③ 고용계약서 ④원 근무처 장의 동의서',
                    applies_when_ko=E7_POST_REPORT_KO, applies_when_en=E7_POST_REPORT_EN),
               item('e67_prev_employer_consent', 'CONDITIONAL_REQUIRED', anchor='④원 근무처 장의 동의서',
                    applies_when_ko=E7_POST_REPORT_KO, applies_when_en=E7_POST_REPORT_EN,
                    notes_ko='계약기간 만료일 또는 쌍방이 근무하기로 합의한 날짜까지 근무한 경우에는 제출이 면제되고, 원 근무처의 휴·폐업 및 임금체불 등의 사유가 있으면 입증서류 또는 사유서로 대체할 수 있습니다.',
                    notes_en='Waived if you worked until the contract end or the agreed date; if the original workplace closed or failed to pay wages, proof or a statement of reasons can replace it.'),
               item('business_reg', 'CONDITIONAL_REQUIRED', anchor='⑤고용계약서 ⑥사업자등록증', role='employer',
                    applies_when_ko=E7_POST_REPORT_KO, applies_when_en=E7_POST_REPORT_EN),
               item('e67_closure_or_arrears_proof', 'CONDITIONAL_REQUIRED', anchor='휴․폐업사실증명서, 임금체불 관련 공적 입증서류',
                    applies_when_ko=E7_PRIOR_PERMIT_KO, applies_when_en=E7_PRIOR_PERMIT_EN),
               item('e67_transfer_consent', 'CONDITIONAL_REQUIRED', anchor='원 고용주의 이적동의서 (휴․폐업, 임금체불 등 부당행위',
                    applies_when_ko=E7_PRIOR_PERMIT_KO + ' — 휴·폐업, 임금체불 등 부당행위, 고용계약조건 위반 행위, 고용계약기간 종료 시까지 근무한 경우는 제외',
                    applies_when_en=E7_PRIOR_PERMIT_EN + ' — not needed after closure, unpaid wages or other unfair acts, breach of contract terms, or when you worked until the contract ended'),
               item('e67_new_employer_review_docs', 'CONDITIONAL_REQUIRED', anchor='새로 고용 계약한 업체의 자격요건 등을 심사할 수 있는 서류',
                    applies_when_ko=E7_PRIOR_PERMIT_KO, applies_when_en=E7_PRIOR_PERMIT_EN)],
         conditions_ko=['사후 신고는 자격요건을 갖추었더라도 본인 귀책사유로 해고 또는 중도 퇴직한 사람이 원고용주의 이적동의를 받지 못하면 적용되지 않으며, 이 경우 근무처변경허가 또는 사증발급인정서 신청 대상입니다.',
                        '사후 신고 시 사유서와 신원보증서는 원칙적으로 제출이 생략되며 수수료가 없습니다.',
                        '주방장 및 조리사는 원 근무처 외 타 근무처에서의 근무시간이 원 근무처 근무시간의 1/3을 넘지 못합니다.'],
         conditions_en=['The post-change report does not apply to people dismissed or who quit early through their own fault without the original employer\'s transfer consent; they need a workplace-change permit or a new confirmation of visa issuance.',
                        'For the report, a statement of reasons and a letter of guarantee are in principle not required, and there is no fee.',
                        'Chefs and cooks may not work at another workplace for more than 1/3 of their hours at the original workplace.'],
         notes_ko=[OFFICER_NOTE_KO], notes_en=[OFFICER_NOTE_EN])

reentry_rule('E-7', '특정활동(E-7) 재입국허가', '등록을 필한 외국인이 출국한 날부터 1년 이내에 재입국하려는 경우 재입국허가 면제',
             '신청서류 : 신청서(별지 34호서식), 여권 원본, 외국인등록증, 수수료')

# E-7-91 (한·인도 CEPA 독립전문가): the stay chapter restricts every in-country permit except on humanitarian grounds.
E791_ANCHOR = '체류기간연장허가, 근무처변경·추가허가, 체류자격변경허가, 체류자격외'
E791_SECTION = '특정활동(E-7) — 2. 협정상 사증․체류허가 특례적용대상자 가. 한·인도 CEPA 독립전문가(IP) 체류특례'
for _proc, _ko, _en in (('status_change', '체류자격변경허가', 'change of status'),
                        ('workplace_change', '근무처변경·추가허가', 'workplace change/addition'),
                        ('activities_outside_status', '체류자격외활동허가', 'activities-outside-status permission')):
  for _code in ('E-7-91', 'E-7-91FTA'):
    guidance(_code, _proc, section=E791_SECTION, anchor=E791_ANCHOR, state='GENERALLY_NOT_PERMITTED', completeness='SOURCE_ONLY',
               summary_ko=f'한·인도 CEPA 독립전문가(IP)는 체류특례에 따라 {_ko}가 제한됩니다. 사고·질병 등 인도적 사유로 체류허가의 필요성이 인정되는 경우에만 일반 체류지침에 따라 처리됩니다.',
               summary_en=f'Under the stay rules for Korea–India CEPA independent professionals, {_en} is restricted. Only where humanitarian grounds such as an accident or illness justify it is the case handled under the general stay rules.')
