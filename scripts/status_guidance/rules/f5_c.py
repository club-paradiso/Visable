# F-5 영주 (incl. F-5-* subcodes) and C-1 일시취재 / C-3 단기방문 / C-4 단기취업.
# Transcribed only from the 2026-10-19 manuals:
#   visa manual  — 6. 일시취재(C-1), 7. 단기방문(C-3), 8. 단기취업(C-4), 33. 영주(F-5),
#                  알기쉬운 외국국적동포 업무 매뉴얼 2. 동포방문(C-3-8) 사증 발급 절차
#   stay manual  — 단기방문(C-3), 단기취업(C-4), 영주(F-5) chapters, 외국국적동포 영주(F-5) 세부절차,
#                  톱티어 비자(F-5-T, F-5-T1), K-STAR 영주(F-5-S1)
# Runs inside author_rules.py (guidance, item, docdefs, drop, residence, VISA, STAY …).

docdefs(
    # ---- visa-manual forms and common items
    f5_c_visa_app_17=('사증발급신청서 (별지 제17호 서식)', 'Visa application form (Form 17)', 'applicant', None),
    f5_c_visa_app=('사증발급신청서', 'Visa application form', 'applicant', None),
    f5_c_cert_app_21=('사증발급인정신청서 (별지 제21호 서식)', 'Application for a visa issuance confirmation (Form 21)', 'applicant', None),
    f5_c_cert_app=('사증발급인정신청서', 'Application for a visa issuance confirmation', 'applicant', None),
    f5_c_photo=('사진', 'Photo', 'applicant', None),
    f5_c_photo_std=('표준규격사진', 'Standard-size photo', 'applicant', None),
    # ---- C-1
    f5_c_c1_press_proof=('소속회사의 파견증명서, 재직증명서 또는 외신보도증', "Dispatch certificate or certificate of employment from your media company, or a foreign-press card", 'employer', None),
    f5_c_c1_proxy=('위임장, 대리인 재직증명서, 대리인 신분증 사본 (대리인 신청 시)', "Power of attorney, the agent's certificate of employment and a copy of the agent's ID (when an agent applies)", 'agency', None),
    # ---- C-3 visa
    f5_c_c31_purpose=('초청장 등 입국목적(행사, 일반연수 등)을 소명하는 서류', 'Invitation or other documents explaining the purpose of entry (event, general training, etc.)', 'inviter', None),
    f5_c_c32_guarantee=('보증관련 서류', 'Guarantee-related documents', 'agency', None),
    f5_c_c34_business_purpose=('초청장(초청회사의 사업자등록증 또는 등기부등본 사본 포함) 등 상용목적 입증서류', "Invitation (with a copy of the inviting company's business registration or corporate register) or other proof of the business purpose", 'inviter', None),
    f5_c_c35_india_corp=('인도 현지 소속 법인의 설립 관련 서류', 'Establishment documents of the Indian company you belong to', 'employer', None),
    f5_c_c35_india_employment=('재직기간이 명시된 재직증명서 또는 출장명령서', 'Certificate of employment stating the period of employment, or a business-trip order', 'employer', None),
    f5_c_c35_india_purpose=('초청장 등 상품이나 서비스판매를 위한 협상 목적 또는 투자회사 설립 준비 목적 입증서류', 'Invitation or other proof that you come to negotiate the sale of goods or services or to prepare an investment company', 'inviter', None),
    f5_c_c39_finance=('국내 체류 경비 지불을 위한 재정능력 또는 신분입증서류', 'Proof of financial capacity to pay for your stay in Korea, or identity-proof documents', 'applicant', None),
    f5_c_c310_travel_plan=('여행계획서【서식3】', 'Travel plan (Form 3)', 'applicant', None),
    f5_c_dongpo_public_doc=('외국국적동포임을 입증하는 국적국의 공적서류', 'Public document of your country of nationality proving that you are an ethnic Korean of foreign nationality', 'applicant', None),
    f5_c_invitation_return=('초청장(초청사유와 귀국보장 각서내용 포함)', 'Invitation (including the reason for inviting and a guarantee of return)', 'inviter', None),
    f5_c_inviter_id_copy=('초청자 신분증 사본', "Copy of the inviter's ID", 'inviter', None),
    # ---- C-3 visa issuance confirmation
    f5_c_realestate_contract=('부동산 매매계약서, 부동산 등기부등본', 'Real-estate sale contract and real-estate register', 'applicant', None),
    f5_c_remit_tourism=('국내 외국환은행에서 발행한 국제송금 전신문, 외국환매입증명서 등', 'International remittance telex, certificate of foreign-currency purchase, etc. issued by a Korean foreign-exchange bank', 'applicant', 'bank'),
    f5_c_family_cert=('가족관계 증명서', 'Family-relation certificate', 'applicant', None),
    f5_c_invest_payment_proof=('투자금 납입 증명 서류 (투자 유치기관 장의 직인이 날인된 투자 확인서, 계좌이체 내역서 등)', "Proof of payment of the investment (investment confirmation sealed by the head of the attracting institution, transfer records, etc.)", 'applicant', None),
    f5_c_remit_public=('공익투자 전담은행에서 발행한 국제송금 전신문, 외국환매입증명서 등', 'International remittance telex, certificate of foreign-currency purchase, etc. issued by the public-interest investment bank', 'applicant', 'bank'),
    f5_c_corp_officer_proof=('투자한 법인의 현직 임원 또는 과점주주로 신청 대상자임을 입증하는 서류 및 당사자 명단이 명시된 해당 법인의 공문', 'Proof that you are a current officer or controlling shareholder of the investing company, and the company\'s official letter naming the persons concerned', 'business_entity', None),
    f5_c_corp_remit_proof=('국외에서 해당 투자자 명의로 법인에 투자금을 송금 또는 지불하였음을 입증하는 서류', "Proof that the investment was remitted or paid to the company from abroad in the investor's name", 'applicant', None),
    f5_c_medical_purpose=('의료기관에서 발급한 의료목적 입증서류', 'Proof of the medical purpose issued by the medical institution', 'medical_institution', None),
    f5_c_treatment_funds=('치료 및 체류비용 조달 능력을 입증할 수 있는 서류', 'Proof of ability to pay for treatment and the stay', 'applicant', None),
    f5_c_agency_reg=('사업자등록증 사본 및 유치기관 등록증 사본', "Copies of the business registration and the patient-attraction institution registration", 'agency', None),
    f5_c_medical_family=('가족관계 입증서류 (결혼증명서·가족관계기록사항에 관한 증명서 또는 출생증명서 등)', 'Proof of family relationship (marriage certificate, family-relation record certificate or birth certificate, etc.)', 'applicant', None),
    f5_c_employment_cert=('재직증명서', 'Certificate of employment', 'employer', None),
    f5_c_preferred_invitation=('우대기업 발행 초청장', 'Invitation issued by the preferred company', 'inviter', None),
    # ---- C-4 visa
    f5_c_c4_recommendation=('소관부처(산하단체)의 고용추천서', 'Employment recommendation from the competent ministry (or its affiliated body)', 'employer', None),
    f5_c_c4_institution_docs=('공사기관 설립관련 서류 (사업자등록증, 법인등기부등본)', 'Establishment documents of the public or private institution (business registration, corporate register)', 'employer', None),
    f5_c_c4_service_contract=('용역계약서(또는 구매계약서, 사업수주계약서 등) 사본', 'Copy of the service contract (or purchase contract, project-award contract, etc.)', 'employer', None),
    f5_c_c4_dispatch_order=('파견명령서 또는 출장명령서', 'Dispatch order or business-trip order', 'employer', None),
    f5_c_c4_degree_verification=('학위관련 검증서류 (학위증 사본, 학위취득 증명서 또는 학위취득 사실이 기재된 졸업증명서 중 택1, 아포스티유 확인 또는 영사확인)', 'Degree verification (one of: degree copy, degree certificate or graduation certificate showing the degree; apostilled or consular-confirmed)', 'applicant', None),
    f5_c_c4_crime_record=('범죄경력증명서(아포스티유 또는 해외주재 대한민국 공관의 영사확인)', 'Criminal record certificate (apostilled or confirmed by a Korean mission abroad)', 'applicant', None),
    f5_c_c4_camp_institution=('사업자등록증, 법인등기부등본 또는 교육기관 설립관계 서류', 'Business registration, corporate register or establishment documents of the educational institution', 'employer', None),
    f5_c_c4_lifelong_edu=('평생교육시설등록증 등 평생교육시설 신고수리․지정관련 서류', 'Lifelong-education facility registration or other documents on its report acceptance or designation', 'employer', None),
    f5_c_c4_camp_schedule=('영어캠프 운영일정표 및 강의시간표(해당 외국인 참여시간 표기)', 'English-camp schedule and teaching timetable (showing your teaching hours)', 'employer', None),
    f5_c_c4_lecture_contract=('고용(강의․강연)계약서 또는 강의료 액수 등 수익금액이 기재되어 있는 초청장(사증발급 협조요청 문서)', 'Employment (lecture) contract, or an invitation stating the fee or other income (visa cooperation request)', 'inviter', None),
    f5_c_c4_degree_employment=('신청인의 학위증 사본 및 재직증명서', "Copy of your degree certificate and your certificate of employment", 'applicant', None),
    f5_c_c4_inviting_institution=('초청 교육기관 등의 설립관련 서류 (사업자등록증 사본 또는 법인등기사항전부증명서 등)', 'Establishment documents of the inviting institution (business registration copy, corporate register, etc.)', 'inviter', None),
    f5_c_c4_other_recommendation=('소관행정기관의 장의 고용추천서, 협조공한 또는 고용의 필요성을 입증할 수 있는 서류', 'Employment recommendation or cooperation letter from the competent agency, or proof of the need to employ you', 'employer', None),
    # ---- C-4 seasonal (C-4-1~4) visa issuance confirmation
    f5_c_c4s_std_contract=('표준근로계약서', 'Standard labor contract', 'employer', None),
    f5_c_c4s_recruit_effort=('내국인 구인노력 증빙자료(구인 광고내용 사본 및 최종 구인실적 등)', 'Proof of efforts to recruit Korean workers (copy of the job advert, final recruitment results, etc.)', 'employer', None),
    f5_c_c4s_worker_passport=('외국인 계절근로자 여권 사본', "Copy of the seasonal worker's passport", 'applicant', None),
    f5_c_c4s_mou_history=('본국에서의 농‧어업 종사 이력 (MOU 외국인)', 'Record of farming or fishing work in the home country (MOU workers)', 'applicant', None),
    f5_c_c4s_marriage_relative=('결혼이민자 신분증, 국내용 혼인‧가족관계 증명서, 기본증명서, 결혼이민자의 친척 관계도, 거주국(체류국)에서 발급한 가족관계증명서 등', "Marriage immigrant's ID, Korean marriage and family-relation certificates, basic certificate, relationship chart and family-relation certificate issued in the country of residence, etc.", 'other_third_party', None),
    f5_c_c4s_accommodation=('숙소 관련 서류(외국인 계절근로자에게 제공 예정인 ‘숙소시설표’)', "Accommodation documents (the 'accommodation facility sheet' for the seasonal workers)", 'employer', None),
    f5_c_c4s_mou_result=('업무협약(MOU) 체결 결과서 등', 'Report on the concluded MOU, etc.', 'local_government', None),
    # ---- C-4 workplace change
    f5_c_c4s_insurance=('산업재해보험가입 증명원 또는 농·어업인 안전보험 증서', 'Industrial-accident insurance certificate or farmers/fishers safety insurance certificate', 'employer', None),
    f5_c_c4s_health_ins=('건강보험 가입증명원 또는 신청 입증서류(해당자만 제출)', 'Health-insurance enrolment certificate or proof of application (only if applicable)', 'applicant', None),
    f5_c_c4s_employer_confirmation=('계절근로자 배치 대상 고용주 확인서(지자체에서 새 고용주에게 발급)', 'Confirmation of the employer to whom the seasonal worker is assigned (issued by the local government to the new employer)', 'local_government', None),
    f5_c_c4_company_docs=('회사 설립 관련 서류', 'Company establishment documents', 'employer', None),
    f5_c_c4_recommendation_if_any=('고용추천서(해당자)', 'Employment recommendation (if applicable)', 'employer', None),
    f5_c_c4_field_proof=('기타 해당 분야 입증 서류 등', 'Other documents proving the field of activity', 'applicant', None),
    f5_c_c4_change_explanation=('소명자료, 활동 계획서', 'Supporting explanation and activity plan', 'applicant', None),
    # ---- C-3 registration (Chile)
    f5_c_c34_chile_purpose=('거래실적, 초청장, 계약서, 수출입관련서류 등 입국목적을 증명하는 서류', 'Documents proving the purpose of entry (trading record, invitation, contract, import/export documents, etc.)', 'applicant', None),
    # ---- F-5 visa issuance
    f5_c_f55_fdi_reg_copy=('외국인투자기업 등록증명서 사본', 'Copy of the foreign-invested company registration certificate', 'business_entity', None),
    f5_c_f55_biz_corp_copy=('사업자 등록증 사본 및 법인 등기사항전부증명서', 'Copy of the business registration and the corporate register', 'business_entity', None),
    f5_c_f55_income_certs=('신청자 본인의 소득금액 증명원(세무서 발급) 및 고용 내국인 5인 이상의 소득금액 증명원(세무서 발급)', 'Income certificates (tax office) for yourself and for 5 or more Korean employees', 'business_entity', 'tax_office'),
    f5_c_f55_fulltime_proof=('고용 내국인의 정규직(전일제 상용고용 형태) 고용 입증서류(고용계약서, 정규직 고용확인서 등)', 'Proof that the Korean employees are full-time regular staff (employment contracts, regular-employment confirmation, etc.)', 'business_entity', None),
    f5_c_points_proof=('점수제 해당항목 입증서류', 'Proof for the points-system items', 'applicant', None),
    # ---- F-5 status grant
    f5_c_family_birth_proof=('가족관계 입증서류(출생증명서 등)', 'Proof of family relationship (birth certificate, etc.)', 'applicant', None),
    f5_c_national_id_proof=('국적국의 신분을 증명하는 서류', 'Document proving identity in the country of nationality', 'applicant', None),
    # ---- F-5 status change: common documents (외국적동포 제외)
    f5_c_app_form_stamp=('통합신청서(수입인지 포함)', 'Integrated application form (with revenue stamp)', 'applicant', 'hikorea'),
    f5_c_photo_fee_no_arc=('최근 6개월이내 촬영한 여권용 사진 1매 및 영주권 발급 수수료 (외국인등록증이 없는 경우)', 'One passport photo taken within 6 months and the permanent-residence card fee (if you have no residence card)', 'applicant', None),
    f5_c_tax_paid_proof=('국세, 지방세 등 납세 완납 관련 공적 증명 서류 (납세증명서 또는 체납증명서 등)', 'Official proof that national and local taxes are fully paid (tax clearance or arrears certificate, etc.)', 'applicant', 'tax_office'),
    f5_c_income_tax_proof=("총수익과 납부한 소득세 등이 기재된 '소득금액증명'(세무서 발급) 등 납부한 세금 관련 공적 증명 서류", "Income certificate (tax office) showing total income and income tax paid, or other official proof of taxes paid", 'applicant', 'tax_office'),
    f5_c_basic_knowledge=('기본소양 요건 입증 서류 (영주용·귀화용 종합평가 합격증, 사회통합프로그램 이수증(한국이민영주적격과정·한국이민귀화적격과정) 중 1개 이상)', 'Proof of basic knowledge (one or more of: permanent-residence or naturalisation comprehensive-test pass certificate, social integration program completion certificate)', 'applicant', None),
    f5_c_basic_info_form=('영주(F-5)자격 신청자 기본정보 (신청자 작성)', 'F-5 applicant basic information sheet (filled in by the applicant)', 'applicant', None),
    # ---- F-5 status change: subcode documents
    f5_c_f51_d7=('재직증명서 또는 파견명령서', 'Certificate of employment or dispatch order', 'employer', None),
    f5_c_f51_d8d9=('매출액 또는 수출액 입증서류 등', 'Proof of sales or export amount, etc.', 'business_entity', None),
    f5_c_f51_d10e7=('해당 학위증, 고용계약서 등', 'The relevant degree certificate, employment contract, etc.', 'applicant', None),
    f5_c_f54_family=('가족관계 입증 서류, 출생증명서 등', 'Proof of family relationship, birth certificate, etc.', 'applicant', None),
    f5_c_f55_corp_docs=('외국인투자기업 등록증명서, 법인등기사항전부증명서, 사업자등록증', 'Foreign-invested company registration certificate, corporate register, business registration', 'business_entity', None),
    f5_c_f55_employee_proof=('고용 내국인 정규직 고용 입증서류 (4대 보험 사업장 가입자 명부, 고용 내국인의 소득금액증명, 고용계약서, 정규직 고용확인서 등)', "Proof of full-time employment of Korean staff (social-insurance workplace enrolment list, the employees' income certificates, employment contracts, regular-employment confirmation, etc.)", 'business_entity', None),
    f5_c_f58_hukou=('화교협회 발행 호적등본, 출생증명서 등', 'Family register issued by the Overseas Chinese Association, birth certificate, etc.', 'applicant', None),
    f5_c_phd_copy=('박사 학위증 사본', 'Copy of the doctoral degree certificate', 'applicant', None),
    f5_c_degree_or_license_copy=('학위증 또는 자격증 사본', 'Copy of the degree certificate or technical qualification', 'applicant', None),
    f5_c_company_reg_employment=('소속기업 사업자등록증 사본, 재직증명서', "Copy of your company's business registration and your certificate of employment", 'employer', None),
    f5_c_regular_staff_proof=('4대 보험 사업장 가입자 명부, 고용 계약서 등 정규직 여부 확인서류 등', 'Proof of regular employment (social-insurance workplace enrolment list, employment contract, etc.)', 'employer', None),
    f5_c_f511_awards=('해당 분야 수상경력 또는 경력증명서', 'Record of awards in the field or certificate of career', 'applicant', None),
    f5_c_f511_papers=('과학기술논문 인용색인(SCI) 등 논문게재 또는 연구실적 증명서류', 'Proof of publications (SCI etc.) or research achievements', 'applicant', None),
    f5_c_f511_recognition=('과학, 경영 등 특정분야에서 인정받았음을 증명하는 서류', 'Proof of recognition in a specific field such as science or management', 'applicant', None),
    f5_c_f511_points=('기타 점수제 해당항목 입증서류', 'Other proof for the points-system items', 'applicant', None),
    f5_c_f512_docs=('사유서, 훈․포장 증서(수상자), 가족관계 및 기타 증빙 서류 등', 'Statement of reasons, order or medal certificate (recipients), family-relation and other supporting documents', 'applicant', None),
    f5_c_f513_pension=('연금증서 사본 및 연금입금통장', 'Copy of the pension certificate and the bankbook receiving the pension', 'applicant', None),
    f5_c_f516_employment=('소속기업 사업자등록증 사본, 고용계약서 사본, 재직증명서', "Copy of your company's business registration, copy of your employment contract, certificate of employment", 'employer', None),
    f5_c_family_proof_dependants=('가족관계 입증서류', 'Proof of family relationship', 'applicant', None),
    f5_c_unmarried_proof=('미혼임을 입증하는 서류', 'Proof of being unmarried', 'applicant', None),
    f5_c_f517_investment=('부동산 등기부등본 등 투자금을 유지하고 있음을 입증하는 서류(신청일 이전 최근 5일 이내 발급)', 'Real-estate register or other proof that the investment is maintained (issued within 5 days before applying)', 'applicant', None),
    f5_c_f520_family=('가족관계 입증서류(중국의 경우 호구부 등), 출생증명서 등', 'Proof of family relationship (hukou for China, etc.), birth certificate, etc.', 'applicant', None),
    f5_c_f520_no_korean_nationality=('대한민국 국적 미보유 확인서 (부 또는 모가 자필로 기재)', 'Confirmation of not holding Korean nationality (handwritten by the father or mother)', 'principal_holder', None),
    f5_c_f520_dna=('유전자 감정결과서', 'DNA test result', 'applicant', None),
    f5_c_f521_investment=('투자금을 유지하고 있음을 입증하는 서류(영주신청일 이전 5일 이내 발급)', 'Proof that the investment is maintained (issued within 5 days before applying)', 'applicant', None),
    f5_c_f523_assets=('투자금 이외 본인 또는 배우자의 국내 보유자산(3억원 이상) 입증 서류', 'Proof of domestic assets of you or your spouse, other than the investment (KRW 300 million or more)', 'applicant', None),
    f5_c_f524_corp=('사업자등록증, 법인등기사항전부증명서', 'Business registration, corporate register', 'business_entity', None),
    f5_c_f524_funding=('투자자로부터 3억원 이상의 투자금을 유치하였거나, 이에 준하는 자본금을 갖고 있음을 증명하는 서류(재무제표, 투자금 도입 내역서 등)', 'Proof of attracting KRW 300 million or more from investors, or of equivalent capital (financial statements, record of funds brought in, etc.)', 'business_entity', None),
    f5_c_f524_employees=('2명 이상의 국민을 6개월 이상 계속 고용하고 있음을 입증하는 서류 (4대 보험 사업장 가입자 명부, 고용 내국인의 소득금액증명, 고용계약서, 정규직 고용확인서 등)', 'Proof of employing 2 or more Korean nationals continuously for 6+ months (social-insurance workplace list, their income certificates, employment contracts, regular-employment confirmation, etc.)', 'business_entity', None),
    f5_c_f525_deposit=('투자금 예치확인서(한국산업은행 발행)', 'Investment deposit confirmation (issued by Korea Development Bank)', 'applicant', 'bank'),
    f5_c_f525_fx=('외화반입 관련 입증서류(외국환매입증명서 등)', 'Proof of bringing in foreign currency (certificate of foreign-currency purchase, etc.)', 'applicant', 'bank'),
    f5_c_f525_pledge=('투자유지 서약서', 'Pledge to maintain the investment', 'applicant', None),
    f5_c_f526_docs=('연구개발시설 지정서(산업통상자원부 공문) 사본, 파견명령서 또는 재직증명서, 소득금액증명 등', 'Copy of the R&D facility designation (Ministry of Trade, Industry and Energy letter), dispatch order or certificate of employment, income certificate, etc.', 'employer', None),
    f5_c_f528_family=('가족관계 등 입증 서류(국내 출생인 경우 국내 출생증명서)', 'Proof of family relationship etc. (Korean birth certificate if born in Korea)', 'applicant', None),
    # ---- F-5-2 / F-5-3 (결혼이민자·국민의 미성년 자녀)
    f5_c_f52_common=('여권, 외국인등록증, 통합신청서, 표준규격 사진, 수수료, 체류지 입증서류', 'Passport, residence card, integrated application form, standard photo, fee, proof of residence', 'applicant', None),
    f5_c_f52_spouse_certs=('한국인 배우자의 기본증명서, 혼인관계증명서, 가족관계증명서, 주민등록표 등본', "Korean spouse's basic certificate, marriage-relation certificate, family-relation certificate and resident registration copy", 'korean_spouse', 'community_center'),
    f5_c_f52_child_family=('(자녀가 있을 경우) 자녀의 가족관계증명서', "Child's family-relation certificate (if you have children)", 'applicant', None),
    f5_c_f52_couple_photos=('부부가 혼인생활 중 함께 찍은 사진(3장 이상)', 'Photos of the couple taken together during the marriage (3 or more)', 'applicant', None),
    f5_c_f52_crime_6m=('해외범죄경력증명(신청일로부터 6개월 이내 발급)', 'Overseas criminal record certificate (issued within 6 months before applying)', 'applicant', None),
    f5_c_f52_income=('본인 또는 생계를 같이하는 가족의 소득금액증명 (일인당 국민총소득 이상의 소득금액)', 'Income certificate of you or the family sharing your livelihood (income of at least GNI per capita)', 'applicant', 'tax_office'),
    f5_c_f52_assets=('본인과 생계를 같이하는 가족 모두의 자산 증빙서류(입출금거래내역, 예･적금증명, 전･월세계약서, 부동산등기사항전부증명 등) 및 신용정보조회서 (중위수준 이상의 가계 자산)', 'Asset evidence for you and all family members sharing your livelihood (bank statements, deposit certificates, lease contracts, real-estate register, etc.) and a credit report (household assets at or above the median)', 'applicant', None),
    f5_c_f52_kiip=('사회통합프로그램 이수증(한국이민영주적격과정 또는 한국이민귀화적격과정)', 'Social integration program completion certificate (permanent-residence or naturalisation course)', 'applicant', None),
    f5_c_f52_kiprat=('한국이민영주적격시험 합격증(KIPRAT) 또는 한국이민귀화적격시험 합격증(KINAT)', 'KIPRAT or KINAT pass certificate', 'applicant', None),
    f5_c_f52_other=('그 밖에 심사에 필요하다고 청장 등이 인정한 서류(요건 완화･면제 대상자의 해당 사유 소명 자료 등)', 'Other documents the office head considers necessary (e.g. evidence for relaxation or exemption of requirements)', 'applicant', None),
    f5_c_f52_ex_marriage=('한국인 (前)배우자와의 혼인관계증명서', 'Marriage-relation certificate with the Korean (former) spouse', 'applicant', 'community_center'),
    f5_c_f52_child_certs=('한국인 (前)배우자와의 관계에서 출생한 자녀의 기본증명서, 가족관계증명서', 'Basic and family-relation certificates of the child born to you and the Korean (former) spouse', 'applicant', 'community_center'),
    f5_c_f52_raising_photos=('그간 자녀를 양육하며 찍은 사진(3장 이상)', 'Photos taken while raising the child (3 or more)', 'applicant', None),
    f5_c_f52_child_expenses=('자녀양육에 필요한 비용(용돈, 학비, 의료비 등) 지출 내역', 'Records of child-rearing expenses (allowance, tuition, medical costs, etc.)', 'applicant', None),
    f5_c_f52_marriage_life=('혼인 중 함께 찍은 사진, 주고받은 메시지 내역, 주변인 확인서 등 혼인생활 확인 서류', 'Evidence of the married life (photos together, message history, statements from acquaintances, etc.)', 'applicant', None),
    f5_c_f52_fault_proof=('이혼판결문, 진단서, 수사 및 범죄경력증명 자료, 주변인 확인서 등 한국인 (前)배우자의 귀책사유 입증 서류', "Proof of the Korean (former) spouse's fault (divorce judgment, medical certificate, investigation or criminal records, statements from acquaintances, etc.)", 'applicant', None),
    f5_c_f53_parent_certs=('대한민국 국민인 부(父) 또는 모(母)의 기본증명서, 혼인관계증명서, 가족관계증명서, 주민등록표 등본', "Korean father's or mother's basic certificate, marriage-relation certificate, family-relation certificate and resident registration copy", 'korean_spouse', 'community_center'),
    f5_c_f53_child_birth=('미성년 자녀(신청인)의 출생증명서 등 가족관계증명 서류', "Birth certificate or other family-relation proof of the minor child (applicant)", 'applicant', None),
    f5_c_f53_school=('(정규교육 과정 이수자) 졸업증명서, 검정고시 합격증, 재학증명서 등', 'Graduation certificate, qualification-exam pass certificate, enrolment certificate, etc. (regular-school students or graduates)', 'educational_institution', 'school'),
    # ---- F-5 외국국적동포 (F-5-6, F-5-7, F-5-14)
    f5_c_dongpo_crime=('해외범죄 경력 확인서 (해외 범죄경력증명서 세부 제출기준 <별첨 1> 참조)', 'Overseas criminal record certificate (see Annex 1 submission criteria)', 'applicant', None),
    f5_c_f56_income=('소득금액 증명', 'Income certificate', 'applicant', 'tax_office'),
    f5_c_f56_pension=('연금증서(사본) 및 연금입금통장', 'Pension certificate (copy) and the bankbook receiving the pension', 'applicant', None),
    f5_c_f56_assets=('부동산 등기부 등본, 부동산 매매계약서, 임대차 계약서, 재산세 납세내역증명 또는 전·월세계약서 신용정보조회서 등', 'Real-estate register, sale contract, lease contract, property-tax payment record or deposit lease contract, credit report, etc.', 'applicant', None),
    f5_c_f56_trade=('재직증명서, 등기부등본 또는 사업자등록증 사본, 수출입 실적 증명서(선하증권 또는 송장 등), 연간 납세 증명서', 'Certificate of employment, corporate register or business registration copy, import/export record (bill of lading or invoice), annual tax certificate', 'business_entity', None),
    f5_c_f56_investment=('사업자 등록증사본 또는 등기부 등본, 사업장 및 주택임대차계약서 기타 외국인투자기업증명서 등 국내투자 증빙자료', 'Proof of investment in Korea (business registration copy or corporate register, business and housing lease contracts, foreign-invested company certificate, etc.)', 'business_entity', None),
    f5_c_f56_mission_recommendation=('재외공관장 추천서', 'Recommendation from the head of the Korean mission', 'other_third_party', None),
    f5_c_f57_passport_id=('여권 및 본국 신분증 사본(원본 제시) 등 외국국적동포 입증서류', 'Passport, copy of the home-country ID (show the original) and other proof of being an ethnic Korean of foreign nationality', 'applicant', None),
    f5_c_f57_arc=('외국인등록증(거소신고증)', 'Residence card (domestic residence report card)', 'applicant', None),
    f5_c_f57_kiip=('사회통합프로그램 한국이민영주적격과정이수증 또는 한국이민영주적격시험 합격증 (국적회복, 특별귀화대상자는 제출면제)', 'Social integration program permanent-residence course certificate or KIPRAT pass certificate (exempt for nationality-restoration and special-naturalisation cases)', 'applicant', None),
    f5_c_f57_livelihood=('생계유지능력 입증서류 (국적회복, 특별귀화대상자는 제출면제)', 'Proof of ability to support yourself (exempt for nationality-restoration and special-naturalisation cases)', 'applicant', None),
    # ---- F-5-T / F-5-T1 / F-5-S1
    f5_c_tt_common=('공통서류(신청서, 표준규격 사진, 여권 사본, 체류지 입증서류, 수수료 등)', 'Common documents (application form, standard photo, passport copy, proof of residence, fee, etc.)', 'applicant', None),
    f5_c_f5t_employment=('고용계약서, 재직증명서, 소득입증서류(소득금액증명원 등)', 'Employment contract, certificate of employment, proof of income (income certificate, etc.)', 'employer', None),
    f5_c_f5t_biz_reg=('사업자등록증 등 (기존과 근무처 변경이 없는 경우 제출 불요)', 'Business registration, etc. (not needed if your workplace has not changed)', 'employer', None),
    f5_c_f5t_korean=('한국어 능력 입증서류 (사회통합프로그램 3단계 이상 또는 한국어능력시험(TOPIK) 3단계 이상)', 'Proof of Korean ability (social integration program level 3+ or TOPIK level 3+)', 'applicant', None),
    f5_c_f5t1_principal=('주 자격자의 여권 사본 및 외국인등록증', "Principal holder's passport copy and residence card", 'principal_holder', None),
    f5_c_f5t1_family=('본국 정부 발급 가족관계 입증서류(가족관계증명서 등, 제출이력이 없는 경우)', 'Family-relation proof issued by the home government (family-relation certificate, etc.; if not submitted before)', 'applicant', None),
    f5_c_f5s1_basic=('기본서류 (신청서, 여권, 외국인등록증, 수수료(수입인지), 체류지 입증서류, 해외범죄경력증명서, 신원보증서)', 'Basic documents (application form, passport, residence card, fee (revenue stamp), proof of residence, overseas criminal record, letter of guarantee)', 'applicant', None),
    f5_c_f5s1_points_table=('신청인이 해당하는 점수를 기재한 점수표【붙임 6】', 'Points table filled in with your points (Attachment 6)', 'applicant', None),
    f5_c_f5s1_points_proof=('신청인이 기재한 평가 항목별 점수를 입증하는 서류【붙임 7】', 'Proof for the points you claimed per item (Attachment 7)', 'applicant', None),
)


def one_of(group, first, *rest):
    """The manual accepts any one of these documents: one required item that lists the others as
    substitutes (the repository's alternatives pattern), not several separately required items."""
    d = dict(first)
    d['requirement_level'] = 'REQUIRED_BASELINE'
    d['alternatives_group'] = group
    d['substitution_allowed'] = True
    d['alternatives'] = [{'ko': DOCDEFS[r['ref']][0], 'en': DOCDEFS[r['ref']][1]} for r in rest]
    return d

VISA_NOTE_KO = '재외공관의 장은 입국목적, 초청의 진정성, 초청자 및 피초청자의 자격 확인 등을 심사하기 위해 필요한 경우 첨부서류를 일부 가감할 수 있습니다.'
VISA_NOTE_EN = 'The head of the Korean mission may add or remove some documents where needed to check the purpose of entry, the genuineness of the invitation and the eligibility of the inviter and invitee.'
CVI_NOTE_KO = '출입국·외국인청(사무소·출장소)장은 초청의 진정성, 초청자 및 피초청자의 자격 확인 등을 심사하기 위해 첨부서류의 일부를 가감할 수 있습니다.'
CVI_NOTE_EN = 'The immigration office head may add or remove some documents to check the genuineness of the invitation and the eligibility of the inviter and invitee.'

# ==========================================================================
# C-1 일시취재 — visa manual 6. 일시취재(C-1)
# ==========================================================================
C1_VISA_DOCS = '① 사증발급신청서 (별지 제17호 서식), 여권, 표준규격사진 1매, 수수료 ② 소속회사의 파견증명서, 재직증명서 또는 외신보도증'
guidance('C-1', 'visa_issuance', manual=VISA, section='일시취재(C-1) — 공관장 재량으로 발급할 수 있는 사증 1. 일시취재(C-1) 사증발급',
         anchor='체류자격 일시취재(C-1) 자격 해당자에 대한 체류기간 90일 이하의 단수사증 발급',
         summary_ko='일시취재(C-1) 자격 해당자에게는 재외공관장 재량으로 체류기간 90일 이하의 단수사증이 발급됩니다. 사증발급신청서·여권·사진·수수료와 소속회사의 파견증명서, 재직증명서 또는 외신보도증을 냅니다.',
         summary_en='People eligible for C-1 can get a single-entry visa for a stay of up to 90 days at the discretion of the mission head. Submit the visa application, passport, photo and fee with a dispatch certificate or employment certificate from your media company, or a foreign-press card.',
         period_ko='체류기간 90일 이하 (단수사증)', period_en='Stay of up to 90 days (single-entry)',
         docs=[item('f5_c_visa_app_17', anchor=C1_VISA_DOCS), item('passport', anchor=C1_VISA_DOCS), item('photo', anchor=C1_VISA_DOCS), item('fee', anchor=C1_VISA_DOCS),
               item('f5_c_c1_press_proof', anchor=C1_VISA_DOCS)],
         notes_ko=[VISA_NOTE_KO], notes_en=[VISA_NOTE_EN])

C1_CVI_DOCS = '① 사증발급인정신청서 (별지 제21호 서식), 여권사본, 표준규격사진 1매 ② 소속회사의 파견증명서, 재직증명서 또는 외신보도증'
guidance('C-1', 'visa_issuance_confirmation', manual=VISA, section='일시취재(C-1) — 사증발급인정서 발급대상 1. 특정국가 국민에 대한 일시취재(C-1) 사증발급인정서 발급',
         anchor='1. 특정국가 국민에 대한 일시취재(C-1) 사증발급인정서 발급',
         summary_ko='특정국가 국민은 원칙적으로 법무부장관이나 출입국·외국인청(사무소·출장소)장이 발급한 사증발급인정서로 일시취재(C-1) 사증을 받습니다. 사증발급인정신청서·여권사본·사진과 소속회사의 파견증명서, 재직증명서 또는 외신보도증을 냅니다.',
         summary_en='Nationals of specified countries in principle get a C-1 visa through a visa issuance confirmation issued by the Minister of Justice or an immigration office. Submit the confirmation application, passport copy and photo with a dispatch or employment certificate from your media company, or a foreign-press card.',
         conditions_ko=['사증발급인정서를 제출하지 않은 사람은 공관장이 법무부장관의 승인을 받아 사증을 발급할 수 있습니다.', '특정국가 거주 무국적자는 특정국가 국민의 사증발급기준에 준하여 처리합니다.'],
         conditions_en=['If no confirmation is submitted, the mission head may issue the visa with the approval of the Minister of Justice.', 'Stateless persons living in a specified country are handled under the criteria for that country\'s nationals.'],
         docs=[item('f5_c_cert_app_21', anchor=C1_CVI_DOCS), item('passport_copy', anchor=C1_CVI_DOCS), item('photo', anchor=C1_CVI_DOCS),
               item('f5_c_c1_press_proof', anchor=C1_CVI_DOCS),
               item('f5_c_c1_proxy', 'CONDITIONAL_REQUIRED', anchor='대리인 신청시 : 위임장, 대리인 재직증명서, 대리인 신분증 사본 추가 제출',
                    applies_when_ko='대리인이 신청하는 경우', applies_when_en='An agent applies on your behalf')],
         notes_ko=[CVI_NOTE_KO], notes_en=[CVI_NOTE_EN])

# ==========================================================================
# C-3 단기방문 — visa manual 7. 단기방문(C-3): 단수사증 발급 대상 (subcode sections)
# ==========================================================================
C3_SEC = '단기방문(C-3) — 공관장 재량으로 발급할 수 있는 사증 · 단수사증 발급 대상'

C31_DOCS = '① 사증발급신청서, 여권, 사진, 수수료 ② 초청장 등 입국목적(행사, 일반연수 등)을 소명하는 서류'
guidance('C-3-1', 'visa_issuance', manual=VISA, section=C3_SEC + ' 1. 단기일반(C-3-1)', anchor='1. 단기일반(C-3-1) 가. 발급 대상',
         summary_ko='단기일반(C-3-1) 단수사증은 친선경기·행사·회의 참가, 단기 기술·기능 연마 등 순수관광~일반관광(C-3-2~C-3-9)을 제외한 단기방문 목적에 발급되며, 사증발급신청서·여권·사진·수수료와 초청장 등 입국목적 소명서류를 냅니다.',
         summary_en='A C-3-1 single-entry visa is issued for short-visit purposes other than C-3-2 to C-3-9 (friendly matches, events, conferences, short skill training, etc.). Submit the visa application, passport, photo, fee and an invitation or other proof of the purpose of entry.',
         period_ko='체류기간 90일 이내, 유효기간 3월', period_en='Stay up to 90 days, valid for 3 months',
         docs=[item('f5_c_visa_app', anchor=C31_DOCS), item('passport', anchor=C31_DOCS), item('f5_c_photo', anchor=C31_DOCS), item('fee', anchor=C31_DOCS),
               item('f5_c_c31_purpose', anchor=C31_DOCS)],
         notes_ko=['입국목적 소명서류는 공관별로 주재국 실정에 맞게 지정하여 운영합니다.', '복수사증·더블사증은 별도 발급지침이 적용됩니다.', OFFICER_NOTE_KO],
         notes_en=['Each mission specifies the purpose-of-entry documents to suit local conditions.', 'Multiple- and double-entry visas follow separate guidelines.', OFFICER_NOTE_EN])

C32_DOCS = '사증발급신청서, 여권, 사진, 수수료, 보증관련 서류'
guidance('C-3-2', 'visa_issuance', manual=VISA, section=C3_SEC + ' 2. 단체관광 등(C-3-2)', anchor='2. 단체관광 등(C-3-2) 가. 발급 대상',
         summary_ko='단체관광 등(C-3-2) 사증은 체류기간 경과 시 대행사(여행사)가 책임지는 단체사증·보증개별 사증 등으로, 사증발급신청서·여권·사진·수수료와 보증관련 서류를 냅니다.',
         summary_en='C-3-2 visas are group or guaranteed-individual visas for which the travel agency is responsible if the stay is exceeded. Submit the visa application, passport, photo, fee and guarantee documents.',
         period_ko='체류기간 90일(단체사증은 15일) 이내, 유효기간 3월', period_en='Stay up to 90 days (15 days for group visas), valid for 3 months',
         docs=[item('f5_c_visa_app', anchor=C32_DOCS), item('passport', anchor=C32_DOCS), item('f5_c_photo', anchor=C32_DOCS), item('fee', anchor=C32_DOCS),
               item('f5_c_c32_guarantee', anchor=C32_DOCS, role='agency')],
         notes_ko=['공관 사정을 고려하여 공관장의 판단하에 추가서류를 징구할 수 있습니다.'], notes_en=['The mission head may require additional documents depending on local conditions.'])

C34_DOCS = '라. 제출 서류 ① 사증발급신청서, 여권, 사진, 수수료'
guidance('C-3-4', 'visa_issuance', manual=VISA, section=C3_SEC + ' 3. 일반상용(C-3-4)', anchor='3. 일반상용(C-3-4) 가. 발급 대상',
         summary_ko='일반상용(C-3-4) 단수사증은 시장조사·업무연락·상담·계약·소규모 무역 등 상용 목적의 단기 체류자에게 발급되며(영리 목적자는 제외), 사증발급신청서·여권·사진·수수료와 초청장 등 상용목적 입증서류를 냅니다.',
         summary_en='A C-3-4 single-entry visa is issued for short business stays such as market research, business contacts, consultations, contracts or small-scale trade (not for profit-making work). Submit the visa application, passport, photo, fee and an invitation or other proof of the business purpose.',
         period_ko='체류기간 90일 이내, 유효기간 3월', period_en='Stay up to 90 days, valid for 3 months',
         docs=[item('f5_c_visa_app', anchor=C34_DOCS), item('passport', anchor=C34_DOCS), item('f5_c_photo', anchor=C34_DOCS), item('fee', anchor=C34_DOCS),
               item('f5_c_c34_business_purpose', anchor='② 초청장(초청회사의 사업자등록증 또는 등기부등본 사본 포함) 등 상용목적')],
         notes_ko=['상용목적 입증서류는 공관별로 주재국 실정에 맞게 지정하여 운영합니다.'], notes_en=['Each mission specifies the business-purpose documents to suit local conditions.'])

guidance('C-3-5', 'visa_issuance', manual=VISA, section=C3_SEC + ' 4. 협정상 일반상용(C-3-5)', anchor='4. 협정상 일반상용(C-3-5) 가. 발급 대상',
         summary_ko='협정상 일반상용(C-3-5) 사증은 한·인도 CEPA 대상자(인도법인 소속으로 상품·서비스 판매 협상이나 투자회사 설립 준비를 위해 방문하는 사람)와 한·칠레 자유무역협정 대상자에게 발급되며, 공통 서류에 대상별 서류를 더해 냅니다.',
         summary_en='C-3-5 visas are issued under the Korea-India CEPA (staff of an Indian company visiting to negotiate sales or prepare an investment company) and the Korea-Chile FTA. Submit the common documents plus those for your category.',
         period_ko='인도 CEPA: 체류기간 90일 이내·유효기간 3개월 / 칠레 FTA: 체류기간 6개월·유효기간 3개월', period_en='India CEPA: stay up to 90 days, valid 3 months / Chile FTA: stay 6 months, valid 3 months',
         docs=[item('f5_c_visa_app', anchor='① (공통) 사증발급신청서, 여권, 사진, 수수료'), item('passport', anchor='① (공통) 사증발급신청서, 여권, 사진, 수수료'),
               item('f5_c_photo', anchor='① (공통) 사증발급신청서, 여권, 사진, 수수료'), item('fee', anchor='① (공통) 사증발급신청서, 여권, 사진, 수수료'),
               item('f5_c_c35_india_corp', 'CONDITIONAL_REQUIRED', anchor='인도 현지 소속 법인의 설립 관련 서류', applies_when_ko='한·인도 CEPA 대상자', applies_when_en='Korea-India CEPA applicants'),
               item('f5_c_c35_india_employment', 'CONDITIONAL_REQUIRED', anchor='재직기간이 명시된 재직증명서 또는 출장명령서', applies_when_ko='한·인도 CEPA 대상자', applies_when_en='Korea-India CEPA applicants'),
               item('f5_c_c35_india_purpose', 'CONDITIONAL_REQUIRED', anchor='초청장 등 상품이나 서비스판매를 위한 협상 목적 또는 투자회사 설립 준비 목적 입증서류', applies_when_ko='한·인도 CEPA 대상자', applies_when_en='Korea-India CEPA applicants'),
               item('f5_c_c34_business_purpose', 'CONDITIONAL_REQUIRED', anchor='③ (발급 대상 ②의 경우) - 초청장(초청회사의 사업자등록증 또는 등기부등본 사본 포함) 등 상용목적 입증서류', applies_when_ko='한·칠레 자유무역협정 대상자', applies_when_en='Korea-Chile FTA applicants')])

C39_DOCS = '사증발급신청서, 여권, 사진, 수수료, 국내 체류 경비 지불을 위한 재정능력* 또는 신분입증서류**'
guidance('C-3-9', 'visa_issuance', manual=VISA, section=C3_SEC + ' 5. 일반관광(C-3-9)', anchor='5. 일반관광(C-3-9) 가. 발급 대상',
         summary_ko='일반관광(C-3-9) 사증은 단체관광 등(C-3-2)에 포함되지 않는 일반 관광객에게 발급되며, 사증발급신청서·여권·사진·수수료와 국내 체류 경비를 낼 재정능력 또는 신분입증서류를 냅니다.',
         summary_en='A C-3-9 visa is issued to general tourists not covered by C-3-2. Submit the visa application, passport, photo, fee and proof of funds for your stay or identity-proof documents.',
         period_ko='체류기간 90일 이내, 유효기간 3월', period_en='Stay up to 90 days, valid for 3 months',
         docs=[item('f5_c_visa_app', anchor=C39_DOCS), item('passport', anchor=C39_DOCS), item('f5_c_photo', anchor=C39_DOCS), item('fee', anchor=C39_DOCS),
               item('f5_c_c39_finance', anchor=C39_DOCS)],
         conditions_ko=['재정능력 입증서류는 최대 2종 범위 내에서 공관장이 지정하며, 복수사증발급대상자에 해당하면 증명할 수 있는 서류 1종만 징구합니다.',
                        '동남아 출신 학생은 재학증명서 또는 학생증과 부모의 재정능력 입증서류로 사증을 발급합니다.',
                        '인센티브 관광은 주관회사의 보증서를 제출하면 재정능력 입증서류를 생략합니다.'],
         conditions_en=['The mission head specifies up to two kinds of financial proof; those eligible for a multiple-entry visa submit only one.',
                        'Students from Southeast Asia are issued the visa with an enrolment certificate or student ID and their parents\' financial proof.',
                        'For incentive tours, financial proof is waived when the organising company submits a guarantee.'],
         notes_ko=['공관 사정에 따라 추가서류를 징구할 수 있습니다.'], notes_en=['Additional documents may be required depending on the mission.'])

C310_DOCS = '사증발급신청서, 여권, 사진, 수수료, 여행계획서*【서식3】'
guidance('C-3-10', 'visa_issuance', manual=VISA, section=C3_SEC + ' 6. 순수환승 (C-3-10)', anchor='6. 순수환승 (C-3-10) 가. 발급 대상',
         summary_ko='순수환승(C-3-10) 사증은 대한민국을 경유해 제3국으로 여행하려는 시리아·수단·예멘·이집트 일반여권 소지자에게 발급되며, 사증발급신청서·여권·사진·수수료와 여행계획서를 냅니다. 환승 목적으로만 쓸 수 있고 입국심사 목적으로는 사용할 수 없습니다.',
         summary_en='A C-3-10 visa is issued to ordinary-passport holders of Syria, Sudan, Yemen and Egypt transiting Korea to a third country. Submit the visa application, passport, photo, fee and a travel plan. It is for transfer only and cannot be used to pass immigration.',
         period_ko='단수사증 (유효기간 3개월, 체류기간 0일), 환승구역 내 72시간 임시 체재', period_en='Single-entry (valid 3 months, stay 0 days); up to 72 hours in the transit area',
         docs=[item('f5_c_visa_app', anchor=C310_DOCS), item('passport', anchor=C310_DOCS), item('f5_c_photo', anchor=C310_DOCS), item('fee', anchor=C310_DOCS),
               item('f5_c_c310_travel_plan', anchor=C310_DOCS)],
         conditions_ko=['외교·관용여권 소지자는 순수환승(C-3-10) 사증 없이 환승할 수 있습니다.'], conditions_en=['Diplomatic and official passport holders can transit without a C-3-10 visa.'])

# C-3-8 동포방문 — compatriot handbook (visa manual) 2. 동포방문(C-3-8) 사증 발급 절차
C38_DOCS = '사증발급신청서(별지 제17호 서식), 여권 및 사본, 표준규격사진 1매, 수수료'
guidance('C-3-8', 'visa_issuance', manual=VISA, section='알기쉬운 외국국적동포 업무 매뉴얼 — 2. 동포방문(C-3-8) 사증 발급 절차', anchor='동포방문(C-3-8) 자격 사증 발급에 관한 사항은 다음과 같습니다',
         summary_ko='동포방문(C-3-8) 사증은 「재외동포법」 제2조제2호의 외국국적동포에게 5년 유효한 복수사증(90일)으로 발급되며, 사증발급신청서·여권 및 사본·사진·수수료와 외국국적동포임을 입증하는 국적국의 공적서류를 냅니다.',
         summary_en='A C-3-8 visa is a 5-year multiple-entry visa (90-day stays) for ethnic Koreans of foreign nationality under Article 2(2) of the Overseas Koreans Act. Submit the visa application, passport and copy, photo, fee and a public document of your country proving Korean ethnicity.',
         period_ko='5년 유효 복수사증 (체류기간 90일)', period_en='5-year multiple-entry visa (90-day stays)',
         docs=[item('f5_c_visa_app_17', anchor=C38_DOCS), item('passport_with_copy', anchor=C38_DOCS), item('photo', anchor=C38_DOCS), item('fee', anchor=C38_DOCS),
               item('f5_c_dongpo_public_doc', anchor='외국국적동포임을 입증하는 국적국의 공적서류 다. 사증발급 내용')],
         conditions_ko=['국내에서 특정강력범죄, 마약, 보이스피싱, 상습음주운전(3회 이상) 등으로 형을 선고받은 사실이 있거나 기타 범죄로 금고 이상의 형을 선고받은 사람은 입국규제 여부와 관계없이 실질심사를 통해 사증발급이 제한될 수 있습니다.',
                        '국가, 출생지, 호구부 관할에 관계없이 사증발급을 신청할 수 있습니다.'],
         conditions_en=['People sentenced in Korea for specified violent crimes, drugs, voice phishing or repeat drunk driving (3+), or to imprisonment for other crimes, may be refused after a substantive review, regardless of any entry ban.',
                        'You can apply regardless of country, place of birth or household-register jurisdiction.'],
         notes_ko=['단기방문(C-3) 장의 중국동포 복수사증(C-3-8) 지침은 60세 이하 외국국적동포를 대상으로 하며, 사증발급신청서·여권 사본·동포 입증 공적서류와 함께 14세 이상 신청자의 해외범죄경력증명을 요구합니다(60세 이상, 13세 이하, 국가유공자(독립유공자)와 그 유족, 특별공로 동포는 면제).', OFFICER_NOTE_KO],
         notes_en=['The C-3 chapter\'s guideline on multiple-entry C-3-8 visas for Chinese-Korean compatriots asks applicants aged 14+ for an overseas criminal record together with the application, passport copy and public proof of Korean ethnicity (exempt: 60+, 13 or under, independence or national-merit patriots and their bereaved families, compatriots of special merit).', OFFICER_NOTE_EN])

# C-3 사증발급인정서 — visa manual 7. 단기방문(C-3) 사증발급인정서 발급대상
C31_CVI_SEC = '단기방문(C-3) — 사증발급인정서 발급대상 1. 관광·휴양시설 투자이민자 / 2. 공익사업 투자외국인 및 그 동반가족(C-3-1)'
guidance('C-3-1', 'visa_issuance_confirmation', manual=VISA, section=C31_CVI_SEC, anchor='1. 관광·휴양시설 투자이민자에 대한 복수사증 발급(C-3-1)',
         summary_ko='관광·휴양시설 투자이민자 또는 공익사업 투자외국인과 그 동반가족 중 외국인등록 없이 수시 방문하려는 사람에게는 단기일반(C-3-1, 체류기간 90일·유효기간 3년 복수사증) 사증발급인정서가 발급됩니다. 투자를 완료한 경우에만 대상이며, 투자 유형별 서류를 냅니다.',
         summary_en='Investors in tourism/resort facilities or public-interest projects, and their accompanying family, who want to visit frequently without registering can get a C-3-1 visa issuance confirmation (3-year multiple-entry, 90-day stays). Only completed investments qualify; documents depend on the investment type.',
         period_ko='체류기간 90일, 유효기간 3년 복수사증', period_en='3-year multiple-entry, 90-day stays',
         doc_page_window=3,
         docs=[item('f5_c_cert_app', 'CONDITIONAL_REQUIRED', anchor='① 사증발급인정신청서, 여권 사본', applies_when_ko='관광·휴양시설 투자이민자', applies_when_en='Tourism/resort facility investors'),
               item('passport_copy', anchor='① 사증발급인정신청서, 여권 사본'),
               item('f5_c_realestate_contract', 'CONDITIONAL_REQUIRED', anchor='② 부동산 매매계약서, 부동산 등기부등본', applies_when_ko='관광·휴양시설 투자이민자', applies_when_en='Tourism/resort facility investors'),
               item('f5_c_remit_tourism', 'CONDITIONAL_REQUIRED', anchor='③ 국내 외국환은행에서 발행한 국제송금 전신문, 외국환매입증명서 등', applies_when_ko='관광·휴양시설 투자이민자 (신용카드 결제 시 결제정보 확인서, 매출전표 사본 등)', applies_when_en='Tourism/resort facility investors (for card payments: payment confirmation, sales slip copy, etc.)'),
               item('f5_c_family_cert', 'CONDITIONAL_REQUIRED', anchor='④ 가족관계 증명서(배우자, 미혼 자녀의 송금 또는 동반 신청 시에 한함)', applies_when_ko='관광·휴양시설 투자: 배우자·미혼 자녀의 송금 또는 동반 신청 시', applies_when_en='Tourism/resort investment: remittance by, or joint application with, a spouse or unmarried child'),
               item('app_form', 'CONDITIONAL_REQUIRED', anchor='① 신청서, 여권사본, 수수료 ② 투자금 납입 증명 서류', applies_when_ko='공익사업 투자외국인', applies_when_en='Public-interest project investors'),
               item('fee', 'CONDITIONAL_REQUIRED', anchor='① 신청서, 여권사본, 수수료 ② 투자금 납입 증명 서류', applies_when_ko='공익사업 투자외국인', applies_when_en='Public-interest project investors'),
               item('f5_c_invest_payment_proof', 'CONDITIONAL_REQUIRED', anchor='② 투자금 납입 증명 서류 (투자 유치기관 장의 직인이 날인된 투자 확인서, 계좌이체 내역서 등)', applies_when_ko='공익사업 투자외국인', applies_when_en='Public-interest project investors'),
               item('f5_c_remit_public', 'CONDITIONAL_REQUIRED', anchor='③ 공익투자 전담은행에서 발행한 국제송금 전신문, 외국환매입증명서 등', applies_when_ko='공익사업 투자외국인', applies_when_en='Public-interest project investors'),
               item('f5_c_family_cert', 'CONDITIONAL_REQUIRED', anchor='④ 가족관계 증명서(투자자의 배우자 또는 미성년 자녀의 송금 또는 부모 등 가족 신청 시에 한함)', applies_when_ko='공익사업 투자: 배우자·미성년 자녀의 송금 또는 부모 등 가족 신청 시', applies_when_en='Public-interest investment: remittance by a spouse or minor child, or application by parents or other family'),
               item('f5_c_corp_officer_proof', 'CONDITIONAL_REQUIRED', anchor='⑤ 투자한 법인의 현직 임원 또는 과점주주로 신청 대상자(F-2 자격변경허가 기준)임을 입증하는 서류 및 당사자 명단이 명시된 해당 법인의 공문(법인의 임원 또는 주주 해당자에 한함)', applies_when_ko='공익사업 투자: 법인의 임원 또는 주주', applies_when_en='Public-interest investment: company officers or shareholders'),
               item('f5_c_corp_remit_proof', 'CONDITIONAL_REQUIRED', anchor='국외에서 해당 투자자 명의로 법인에 투자금을 송금 또는 지불 하였음을 입증하는 서류(법인의 임원 또는 주주 해당자에 한함)', applies_when_ko='공익사업 투자: 법인의 임원 또는 주주', applies_when_en='Public-interest investment: company officers or shareholders')],
         conditions_ko=['기준금액 이상이 본인의 해외자본으로 투자되었음을 입증해야 하며, 매뉴얼의 결격사유(금고 이상 실형 후 5년 미경과 등)에 해당하지 않아야 합니다.'],
         conditions_en=['You must prove that at least the threshold amount was invested from your own foreign capital and must not fall under the disqualifications listed in the manual (e.g. within 5 years of a prison sentence).'],
         notes_ko=[OFFICER_NOTE_KO], notes_en=[OFFICER_NOTE_EN])

guidance('C-3-3', 'visa_issuance_confirmation', manual=VISA, section='단기방문(C-3) — 사증발급인정서 발급대상 3. 의료관광 유치기관의 초청을 받은 자(C-3-3)', anchor='3.  의료관광 유치기관의 초청을 받은 자(C-3-3)',
         summary_ko='의료관광 유치기관의 초청으로 국내 의료기관에서 진료·요양하려는 외국인 환자와 간병 등을 위해 동반입국이 필요한 가족은, 유치기관으로 등록한 초청자가 온라인(visa.go.kr)으로 신청하는 경우에만 사증발급인정서를 받을 수 있습니다. 치료·여행기간이 90일 이하면 C-3-3, 91일 이상이면 G-1-10이 발급됩니다.',
         summary_en='Foreign patients invited by a registered medical-tourism institution, and family needed to accompany them, can get a visa issuance confirmation only when the registered inviter applies online (visa.go.kr). C-3-3 is issued for treatment and travel of 90 days or less; G-1-10 for 91 days or more.',
         period_ko='C-3-3: 체류기간 90일 이내 (단수 3월·더블 6월·복수 5년 이내)', period_en='C-3-3: stay up to 90 days (single 3 months, double 6 months, multiple up to 5 years)',
         doc_page_window=3,
         docs=[item('f5_c_cert_app_21', anchor='① 사증발급인정신청서(별지 제21호 서식), 여권사본, 표준규격사진 1매 ② 의료기관에서 발급한 의료목적 입증서류'),
               item('passport_copy', anchor='① 사증발급인정신청서(별지 제21호 서식), 여권사본, 표준규격사진 1매 ② 의료기관에서 발급한 의료목적 입증서류'),
               item('photo', anchor='① 사증발급인정신청서(별지 제21호 서식), 여권사본, 표준규격사진 1매 ② 의료기관에서 발급한 의료목적 입증서류'),
               item('f5_c_medical_purpose', anchor='② 의료기관에서 발급한 의료목적 입증서류'),
               item('f5_c_treatment_funds', anchor='③ 치료 및 체류비용 조달 능력을 입증할 수 있는 서류', does_not_apply_when_ko='우수 유치기관이 초청하는 경우 생략 가능', does_not_apply_when_en='May be omitted when an excellent attraction institution invites you'),
               item('f5_c_agency_reg', anchor='④ 사업자등록증 사본 및 유치기관 등록증 사본', role='agency'),
               item('f5_c_medical_family', 'CONDITIONAL_REQUIRED', anchor='⑤ 가족관계 입증서류* (결혼증명서․가족관계기록사항에 관한 증명서 또는 출생증명서 등)', applies_when_ko='동반입국이 필요한 배우자 및 동반가족', applies_when_en='Spouse or family who need to accompany the patient')],
         conditions_ko=['베트남은 2016-04-01부터 사증발급인정서 및 전자사증 발급이 제한됩니다.'], conditions_en=['For Vietnam, visa issuance confirmations and e-visas have been restricted since 2016-04-01.'],
         notes_ko=['유치기관 회원가입자는 사업자등록증·유치기관 등록증 사본을 기존 서류 제출로 대체할 수 있습니다.', OFFICER_NOTE_KO], notes_en=['Registered member institutions may rely on documents already submitted for the registration copies.', OFFICER_NOTE_EN])

C36_DOCS = '① 사증발급인정신청서(별지 제21호서식), 여권, 표준규격사진 ② 재직증명서  ③ 우대기업 발행 초청장'
guidance('C-3-6', 'visa_issuance_confirmation', manual=VISA, section='단기방문(C-3) — 사증발급인정서 발급대상 4. 외국인 초청절차 우대기업의 초청을 받은 자(C-3-6)', anchor='4. 외국인 초청절차 우대기업의 초청을 받은 자(C-3-6)',
         summary_ko='대한민국 비자포털을 통해 우대기업으로 선정된 기업·단체(기 선정된 우대기업만 해당)의 초청을 받은 사람에게는 우대기업초청 단기상용(C-3-6) 사증발급인정서(체류기간 90일·유효기간 1년 복수사증)가 발급됩니다.',
         summary_en='People invited by a company or body already selected as a preferred company through the Korea Visa Portal can get a C-3-6 visa issuance confirmation (1-year multiple-entry, 90-day stays).',
         period_ko='체류기간 90일, 유효기간 1년 복수사증', period_en='1-year multiple-entry, 90-day stays',
         docs=[item('f5_c_cert_app_21', anchor=C36_DOCS), item('passport', anchor=C36_DOCS), item('f5_c_photo_std', anchor=C36_DOCS),
               item('f5_c_employment_cert', anchor=C36_DOCS), item('f5_c_preferred_invitation', anchor=C36_DOCS)],
         conditions_ko=['우대기업 선정은 종료되어 기 선정된 우대기업의 초청만 대상입니다.'], conditions_en=['Preferred-company selection has ended; only companies already selected qualify.'],
         notes_ko=[OFFICER_NOTE_KO], notes_en=[OFFICER_NOTE_EN])

# C-3 전자사증 — visa manual 7. 단기방문(C-3) 전자사증
C34_EVISA_DOCS = '(제출서류) ① 사증발급신청서, 여권, 사진, 수수료 ② 초청장(초청사유와 귀국보장 각서내용 포함) ③ 초청자 신분증 사본'
guidance('C-3-4', 'electronic_visa', manual=VISA, section='단기방문(C-3) — 전자사증 3. 상용목적 빈번 출입국자', anchor='3. 상용목적 빈번 출입국자',
         summary_ko='2012-01-01 이후 단기방문(C-3)으로 3회 이상 입국했고 국내 체류 중 불법체류·범법 사실이 없으며 상용목적으로 국내 기업의 초청을 받은 사람은 일반상용(C-3-4) 전자사증(체류기간 90일 이내, 유효기간 3월 단수)을 받을 수 있습니다.',
         summary_en='People who entered on C-3 three or more times since 2012-01-01, had no illegal stay or offences in Korea, and are invited by a Korean company for business can get a C-3-4 e-visa (single-entry, valid 3 months, stay up to 90 days).',
         period_ko='체류기간 90일 이내, 유효기간 3월 단수사증', period_en='Single-entry, valid 3 months, stay up to 90 days',
         docs=[item('f5_c_visa_app', anchor=C34_EVISA_DOCS), item('passport', anchor=C34_EVISA_DOCS), item('f5_c_photo', anchor=C34_EVISA_DOCS), item('fee', anchor=C34_EVISA_DOCS),
               item('f5_c_invitation_return', anchor=C34_EVISA_DOCS), item('f5_c_inviter_id_copy', anchor=C34_EVISA_DOCS)])

guidance('C-3-3', 'electronic_visa', manual=VISA, completeness='SOURCE_ONLY', section='단기방문(C-3) — 전자사증 2. 외국인 환자와 동반가족 및 간병인',
         anchor='2. 외국인 환자와 동반가족 및 간병인',
         summary_ko='보건복지부에 등록한 외국인환자 유치기관 중 법무부장관이 "의료관광 우수 유치기관"으로 지정한 기관이 초청한 외국인 환자와 그 동반자는 전자사증 발급 대상입니다. 이 부분에는 제출서류가 따로 적혀 있지 않습니다.',
         summary_en='Foreign patients, and those accompanying them, invited by an institution the Minister of Justice has designated as an excellent medical-tourism attraction institution (among those registered with the Ministry of Health and Welfare) are eligible for an e-visa. This part lists no documents.')

guidance('C-3-2', 'electronic_visa', manual=VISA, completeness='SOURCE_ONLY', section='단기방문(C-3) — 전자사증 4. 단체관광객',
         anchor='(발급대상) 재외공관장이 지정(법무부장관 승인)한 국외 전담여행사가 사증신청을 대행하는 단체관광객',
         summary_ko='재외공관장이 지정(법무부장관 승인)한 국외 전담여행사가 사증신청을 대행하는 단체관광객은 전자사증 발급 대상이며, 제출서류와 발급내용은 사증발급편람의 단체관광(C-3-2) 자격 사증발급 심사 기준 및 절차에 따릅니다.',
         summary_en='Group tourists whose visa applications are handled by an overseas designated travel agency (designated by the mission head with the Minister\'s approval) are eligible for an e-visa; documents and visa details follow the C-3-2 examination criteria in the visa issuance handbook.')

# ==========================================================================
# C-4 단기취업 — visa manual 8. 단기취업(C-4)
# ==========================================================================
C4_COMMON = '① 사증발급신청서 (별지 제17호 서식), 여권, 표준규격사진 1매, 수수료 ② 고용계약서  ③ 소관부처(산하단체)의 고용추천서'
guidance('C-4-5', 'visa_issuance', manual=VISA, completeness='PARTIALLY_STRUCTURED',
         section='단기취업(C-4) — 공관장 재량으로 발급할 수 있는 사증 1~6 (계절근로외 단기취업 C-4-5)', anchor='1. 아래 대상자에 대한 체류기간 90일 이하의 복수사증',
         summary_ko='계절근로외 단기취업(C-4-5) 사증은 공관장 재량으로 대상별(첨단기술 분야 종사자, 수입기계 설치·용역계약 파견자, 영어캠프 회화지도, 일시흥행·광고모델·상금 대회 참가자, 90일 이하 강의·연구, 그 밖의 C-4-5 해당자)로 발급되며, 공통 서류에 대상별 서류를 더해 냅니다. 단순노무 직종은 해당되지 않습니다.',
         summary_en='C-4-5 visas are issued at the mission head\'s discretion by category (high-tech fields, dispatch for machinery installation or service contracts, English-camp conversation teaching, entertainment/advertising/prize competitions, lectures or research of up to 90 days, other C-4-5 work). Submit the common documents plus those for your category. Simple-labour jobs are not covered.',
         period_ko='체류기간 90일 이하', period_en='Stay of up to 90 days',
         doc_page_window=8,
         docs=[item('f5_c_visa_app_17', anchor=C4_COMMON), item('passport', anchor=C4_COMMON), item('photo', anchor=C4_COMMON), item('fee', anchor=C4_COMMON),
               item('employment_contract', 'CONDITIONAL_REQUIRED', anchor=C4_COMMON, applies_when_ko='첨단기술 분야 종사자(1), 영어캠프 회화지도(3), 그 밖의 C-4-5 해당자(6)', applies_when_en='High-tech fields (1), English-camp teaching (3), other C-4-5 work (6)'),
               item('f5_c_c4_recommendation', 'CONDITIONAL_REQUIRED', anchor=C4_COMMON, applies_when_ko='첨단기술 분야 종사자(1)', applies_when_en='High-tech fields (1)'),
               item('f5_c_c4_institution_docs', 'CONDITIONAL_REQUIRED', anchor='④ 공사기관 설립관련 서류 (사업자등록증, 법인등기부등본)', applies_when_ko='첨단기술 분야 종사자(1)', applies_when_en='High-tech fields (1)'),
               item('f5_c_c4_service_contract', 'CONDITIONAL_REQUIRED', anchor='② 용역계약서(또는 구매계약서, 사업수주계약서 등) 사본', applies_when_ko='수입기계 설치·보수 등 용역·구매·사업수주 계약에 따른 파견자(2)', applies_when_en='Dispatched under service, purchase or project contracts, e.g. machinery installation (2)'),
               item('f5_c_c4_dispatch_order', 'CONDITIONAL_REQUIRED', anchor='③ 파견명령서 또는 출장명령서', applies_when_ko='용역·구매·사업수주 계약에 따른 파견자(2)', applies_when_en='Dispatched under a contract (2)'),
               item('f5_c_c4_degree_verification', 'CONDITIONAL_REQUIRED', anchor='② 학위관련 검증서류(아래 사항 중 택1)', applies_when_ko='영어캠프 등에서 90일 이하 회화지도(3)', applies_when_en='Conversation teaching at English camps for up to 90 days (3)'),
               item('f5_c_c4_crime_record', 'CONDITIONAL_REQUIRED', anchor='③ 범죄경력증명서(아포스티유 또는 해외주재 대한민국 공관의 영사확인)', applies_when_ko='영어캠프 회화지도(3)', applies_when_en='English-camp teaching (3)'),
               item('f5_c_c4_camp_institution', 'CONDITIONAL_REQUIRED', anchor='⑤ 사업자등록증, 법인등기부등본 또는 교육기관 설립관계 서류', applies_when_ko='영어캠프 회화지도(3)', applies_when_en='English-camp teaching (3)'),
               item('f5_c_c4_lifelong_edu', 'CONDITIONAL_REQUIRED', anchor='⑥ 평생교육시설등록증 등 평생교육시설 신고수리․지정관련 서류', applies_when_ko='영어캠프 회화지도(3)', applies_when_en='English-camp teaching (3)'),
               item('f5_c_c4_camp_schedule', 'CONDITIONAL_REQUIRED', anchor='⑦ 영어캠프 운영일정표 및 강의시간표(해당 외국인 참여시간 표기)', applies_when_ko='영어캠프 회화지도(3)', applies_when_en='English-camp teaching (3)'),
               item('f5_c_c4_lecture_contract', 'CONDITIONAL_REQUIRED', anchor='② 고용(강의․강연)계약서 또는 강의료 액수 등 수익금액이 기재되어 있는 초청장(사증발급 협조요청 문서)', applies_when_ko='E-1·E-7 대상자로서 90일 이하 강의·강연·연구(5)', applies_when_en='E-1/E-7-type lecturing or research for up to 90 days (5)'),
               item('f5_c_c4_degree_employment', 'CONDITIONAL_REQUIRED', anchor='③ 신청인의 학위증 사본 및 재직증명서', applies_when_ko='90일 이하 강의·강연·연구(5)', applies_when_en='Lecturing or research (5)'),
               item('f5_c_c4_inviting_institution', 'CONDITIONAL_REQUIRED', anchor='④ 초청 교육기관 등의 설립관련 서류 (사업자등록증 사본 또는 법인등기사항전부증명서 등)', applies_when_ko='90일 이하 강의·강연·연구(5)', applies_when_en='Lecturing or research (5)'),
               item('f5_c_c4_other_recommendation', 'CONDITIONAL_REQUIRED', anchor='③ 소관행정기관의 장의 고용추천서, 협조공한 또는 고용의 필요성을 입증할 수 있는 서류', applies_when_ko='그 밖의 C-4-5 해당자(6)', applies_when_en='Other C-4-5 work (6)')],
         conditions_ko=['일시흥행·광고·패션모델 활동이나 체재비를 넘는 보수를 받는 운동경기·바둑시합·가요 경연 참가자(4)는 활동 유형(공연법상 공연, 관광업소 공연, 대회 참가, 광고 모델, 그 밖의 경우)별로 별도의 서류를 냅니다.',
                        '평생교육시설이 등록(신고)된 위치를 벗어난 시설에서 캠프를 운영하기 위해 외국인강사를 초청하는 경우 사증발급이 불허됩니다.',
                        '정부·대학 등 비영리기관이 학술·공익 목적으로 초청한 1회성 강의·강연·자문은 일정 조건(기관 5개 이하, 활동 7일 이하)을 모두 충족하면 C-4-5 대신 단기 체류자격으로도 가능합니다.'],
         conditions_en=['Entertainment, advertising or fashion-model work, and paid participation in sports, baduk or singing contests (4), require separate documents depending on the activity type (Performance Act performances, tourist-venue performances, contests, advertising models, other).',
                        'A visa is refused when a lifelong-education facility invites a foreign instructor to run a camp outside its registered location.',
                        'One-off lectures, talks or advisory work invited by government, universities or other non-profits for academic or public purposes can be done on a short-term status instead of C-4-5 if all conditions are met (no more than 5 institutions, no more than 7 days of activity).'],
         notes_ko=[VISA_NOTE_KO], notes_en=[VISA_NOTE_EN])

guidance('C-4-1', 'visa_issuance_confirmation', manual=VISA, covers=['C-4-2', 'C-4-3', 'C-4-4'],
         section='단기취업(C-4) — 사증발급인정서 발급대상 □ 계절근로 단기취업(C-4-1~4)자에 대한 사증발급인정서 발급', anchor='계절근로 단기취업(C-4-1~4)자에 대한 사증발급인정서 발급',
         summary_ko='계절근로 단기취업(C-4-1~4) 사증발급인정서는 시·군·구 기초자치단체장이 비자포털(www.visa.go.kr)로 신청하며, 지자체가 고용주에게 배정한 해외 체류 외국인이 대상입니다. 표준근로계약서, 내국인 구인노력 증빙, 계절근로자 관련 서류, 숙소 관련 서류, MOU 체결 결과서 등을 첨부합니다.',
         summary_en='For seasonal C-4-1 to C-4-4 workers, the head of the city/county/district applies through the Visa Portal (www.visa.go.kr) for foreigners abroad whom the local government has assigned to employers. Attach the standard labor contract, proof of Korean recruitment efforts, worker documents, accommodation documents and the MOU result report.',
         period_ko='최대 체류기간 90일 (단수)', period_en='Up to 90 days (single-entry)', filer='local_government',
         doc_page_window=3,
         docs=[item('f5_c_c4s_std_contract', anchor='① 표준근로계약서 ② 내국인 구인노력 증빙자료', role='employer'),
               item('f5_c_c4s_recruit_effort', anchor='② 내국인 구인노력 증빙자료(구인 광고내용 사본 및 최종 구인실적 등)', role='employer'),
               item('f5_c_c4s_worker_passport', anchor='㉠ 외국인 계절근로자 여권 사본'),
               item('f5_c_c4s_mou_history', 'CONDITIONAL_REQUIRED', anchor='㉡ MOU 외국인 : 본국에서의 농‧어업 종사 이력', applies_when_ko='MOU 체결 외국지자체 추천 외국인 (C-4-1, C-4-3)', applies_when_en='Workers recommended by an MOU partner municipality (C-4-1, C-4-3)'),
               item('f5_c_c4s_marriage_relative', 'CONDITIONAL_REQUIRED', anchor='㉢ 결혼이민자의 4촌 이내 친척(배우자 포함) : 결혼이민자 신분증, 국내용 혼인‧가족관계 증명서, 기본증명서, 결혼이민자의 친척 관계도, 거주국(체류국)에서 발급한 가족관계증명서 등', applies_when_ko='결혼이민자의 4촌 이내 친척(배우자 포함) (C-4-2, C-4-4)', applies_when_en='Relatives (within the 4th degree, incl. spouse) of a marriage immigrant (C-4-2, C-4-4)'),
               item('f5_c_c4s_accommodation', anchor='외국인 계절근로자에게 제공 예정인 ‘숙소시설표’', role='employer'),
               item('f5_c_c4s_mou_result', anchor='⑤ 업무협약(MOU) 체결 결과서 등', role='local_government')],
         conditions_ko=['결혼이민자 또는 외국국적동포의 국내 체류 가족은 사증발급인정서 신청 대상이 아니고 체류자격외활동허가 신청 대상입니다.',
                        '표준근로계약서상의 근로일수와 사증별 체류기간이 부합해야 합니다.',
                        '영어 이외의 외국어로 된 친척관계 서류는 번역자 확인서와 번역문을 첨부합니다(공증 불요).'],
         conditions_en=['Family of marriage immigrants or ethnic Koreans already in Korea apply for permission for activities outside status, not for a confirmation.',
                        'The working days in the standard contract must match the stay period of the visa.',
                        'Relationship documents in a language other than English need a translator\'s confirmation and translation (no notarisation).'],
         notes_ko=[OFFICER_NOTE_KO], notes_en=[OFFICER_NOTE_EN])

# ==========================================================================
# C-3 / C-4 stay procedures — stay manual 단기방문(C-3), 단기취업(C-4)
# ==========================================================================
guidance('C-3-2', 'status_change', state='EXCEPTION_ONLY', completeness='SOURCE_ONLY',
         section='단기방문(C-3) — 체류기간 연장허가 2. 단체관광(C-3-2) 사증 소지자에 대한 체류기간연장 제한',
         anchor='단체관광객(C-3-2)과 보증개별사증(C-3-2)을 소지한 자에 대해서는 출국할 항공기 등이 없거나 영주․귀화신청 등 부득이한 사유가 있는 경우에 한하여 체류기간 연장 또는 체류자격 변경허가',
         summary_ko='단체관광객(C-3-2)과 보증개별사증(C-3-2) 소지자는 출국할 항공기 등이 없거나 영주·귀화신청 등 부득이한 사유가 있는 경우에만 체류자격 변경이 허가됩니다.',
         summary_en='Group-tour and guaranteed-individual C-3-2 holders are granted a status change only when there is no departing flight or another unavoidable reason such as a permanent-residence or naturalisation application.')

C34_REG_DOCS = '① 신청서(별지 제34호 서식), 여권원본, 표준규격사진 1장, 수수료'
guidance('C-3-4', 'registration', state='CONDITIONAL', section='단기방문(C-3) — 외국인등록 (단기상용(C-3-4) 칠레 국민)',
         anchor='단기상용(C-3-4) 소지자로 91일 이상 체류하고자 하는 칠레 국민',
         summary_ko='단기상용(C-3-4) 사증으로 91일 이상 체류하려는 칠레 국민은 신청서·여권원본·사진·수수료와 거래실적·초청장·계약서 등 입국목적 증명서류를 내고 C-3로 외국인등록을 합니다. 6개월 이상 체류하려면 D-7, D-8, D-9로 체류자격 변경허가를 받아야 합니다.',
         summary_en='Chilean nationals on C-3-4 who will stay 91 days or more register as C-3 with the application form, original passport, photo, fee and proof of the purpose of entry (trading record, invitation, contract, etc.). To stay 6 months or more, change to D-7, D-8 or D-9.',
         docs=[item('app_form_34', anchor=C34_REG_DOCS), item('passport_original', anchor=C34_REG_DOCS), item('photo1', anchor=C34_REG_DOCS), item('fee', anchor=C34_REG_DOCS),
               item('f5_c_c34_chile_purpose', anchor='② 거래실적, 초청장, 계약서, 수출입관련서류 등 입국목적을 증명하는 서류')],
         notes_ko=[OFFICER_NOTE_KO], notes_en=[OFFICER_NOTE_EN])

C4S_WC = '① 통합신청서, 여권 ※근무처변경 수수료 면제'
guidance('C-4-1', 'workplace_change', covers=['C-4-2', 'C-4-3', 'C-4-4'],
         section='단기취업(C-4) — 근무처의 변경․추가 □ 계절근로 단기취업(C-4-1~4)', anchor='근무처 변경시 지자체 담당자 동반 필요',
         summary_ko='계절근로 단기취업(C-4-1~4)은 근무처 추가가 불가하고, 고용주의 조건 위반 미시정, 근로자 귀책사유 없는 근로 계속 불가 등 사유가 있을 때 지자체 담당자와 동반하여 근무처를 변경할 수 있습니다. 근무처변경 수수료는 면제됩니다.',
         summary_en='Seasonal C-4-1 to C-4-4 workers cannot add a workplace. They may change workplace, accompanied by the local-government officer, for reasons such as an employer not correcting violations or being unable to keep working through no fault of their own. The fee is waived.',
         docs=[item('app_form_34', anchor=C4S_WC), item('passport', anchor=C4S_WC),
               item('accommodation_confirmation', anchor='② 거주/숙소 제공 확인서'),
               item('standard_contract_copy', anchor='③ 표준근로계약서 사본'),
               item('f5_c_c4s_insurance', anchor='④ 산업재해보험가입 증명원 또는 농·어업인 안전보험 증서', role='employer'),
               item('f5_c_c4s_health_ins', 'ADDITIONAL_IF_APPLICABLE', anchor='⑤ 건강보험 가입증명원 또는 신청 입증서류(해당자만 제출)', applies_when_ko='해당자만 제출', applies_when_en='Only if it applies to you'),
               item('f5_c_c4s_employer_confirmation', anchor='⑥ 계절근로자 배치 대상 고용주 확인서(지자체에서 새 고용주에게 발급)', role='local_government')],
         conditions_ko=['근무처 변경 사유: ① 고용주가 각종 조건 위반을 시정하지 않은 경우 ② 계절근로자의 귀책사유 없이 근로를 계속할 수 없는 경우 ③ 사회통념상 최초 계약한 고용주의 작업장에서 근무할 수 없는 경우 등',
                        '전 고용주는 출입국관서 및 지자체에 고용변동신고서를 제출합니다.'],
         conditions_en=['Grounds: (1) the employer did not correct violations; (2) the worker cannot keep working through no fault of their own; (3) by social norms the worker cannot work at the first employer\'s site, etc.',
                        'The previous employer files an employment-change report with the immigration office and the local government.'],
         notes_ko=[OFFICER_NOTE_KO], notes_en=[OFFICER_NOTE_EN])

C45_WC = '① 신청서(별지 제34호 서식), 여권 원본, 수수료 ② 고용계약서 ③ 회사 설립 관련 서류 ④ 고용추천서(해당자) ⑤ 기타 해당 분야 입증 서류 등'
guidance('C-4-5', 'workplace_change', section='단기취업(C-4) — 근무처의 변경․추가 □ 계절근로외 단기취업(C-4-5)', anchor='단기취업(C-4) 소지자의 근무처변경․추가허가 권한을 청(사무소·출장소)장에게 위임',
         summary_ko='계절근로외 단기취업(C-4-5)의 근무처 변경·추가는 청(사무소·출장소)장이 허가하며, 변경 시 주무부처 장의 고용추천서는 원칙적으로 불필요하고 추가 횟수 제한은 없습니다. 신청서·여권 원본·수수료, 고용계약서, 회사 설립 관련 서류 등을 냅니다.',
         summary_en='Workplace changes or additions for C-4-5 are approved by the immigration office head; a ministry employment recommendation is generally not needed for a change, and there is no limit on additions. Submit the application, original passport, fee, employment contract, company establishment documents, etc.',
         docs=[item('app_form_34', anchor=C45_WC), item('passport_original', anchor=C45_WC), item('fee', anchor=C45_WC),
               item('employment_contract', anchor=C45_WC), item('f5_c_c4_company_docs', anchor=C45_WC),
               item('f5_c_c4_recommendation_if_any', 'ADDITIONAL_IF_APPLICABLE', anchor=C45_WC, applies_when_ko='E-1부터 E-7에 해당되는 활동 중 고용추천서가 필수인 업종', applies_when_en='Activities in E-1 to E-7 fields where a recommendation is mandatory'),
               item('f5_c_c4_field_proof', 'MAY_BE_REQUESTED_BY_OFFICER', anchor=C45_WC)],
         conditions_ko=['소속사의 지시에 따라 E-6-1에 해당하는 공연을 위해 공연장소를 변경하는 경우 별도의 허가나 신고 없이 활동할 수 있습니다(E-6-2에 해당하는 활동은 고용주의 변동신고 필요).',
                        '사증 발급 시 허용된 범위가 아닌 다른 활동을 위한 변경은 활동 상호간의 관련성이 높고 필요한 자격요건을 갖춘 경우 청장이 허용할 수 있습니다.'],
         conditions_en=['Changing the venue for E-6-1-type performances on your agency\'s instructions needs no separate permission or report (E-6-2-type activities need the employer\'s change report).',
                        'A change for activities beyond those allowed at visa issuance can be allowed if the activities are closely related and you meet the requirements.'],
         notes_ko=[OFFICER_NOTE_KO], notes_en=[OFFICER_NOTE_EN])

C45_SC = '① 신청서, 여권 원본, 수수료 ② 소명자료, 활동 계획서'
guidance('C-4-5', 'status_change', state='EXCEPTION_ONLY', section='단기취업(C-4) — 체류자격 변경허가 □ 계절근로 외 단기취업(C-4-5)',
         anchor='무사증(B-1․B-2) 또는 단기방문(C-3) 입국자로 입단테스트 등을 위해 입국한 운동선수‧연주자‧무용가',
         summary_ko='무사증(B-1·B-2) 또는 단기방문(C-3)으로 입국한 운동선수·연주자·무용가, 상금이 걸린 국제대회 참가자, 강연 등을 하려는 노벨상 수상자 등 저명인사는 청(사무소·출장소)장 재량으로 단기취업(C-4-5)으로 변경할 수 있습니다. 불가피한 사유가 있거나 국익 차원에서 필요할 때 허용됩니다.',
         summary_en='Athletes, musicians or dancers who entered visa-free (B-1/B-2) or on C-3 for tryouts, participants in international prize competitions, and eminent persons such as Nobel laureates giving lectures may change to C-4-5 at the office head\'s discretion, when there is an unavoidable reason or it serves the national interest.',
         docs=[item('app_form', anchor=C45_SC), item('passport_original', anchor=C45_SC), item('fee', anchor=C45_SC), item('f5_c_c4_change_explanation', anchor=C45_SC)],
         conditions_ko=['허가 시 체류기간은 입국일로부터 기산합니다.', '예술흥행(E-6-2)에 해당하는 활동을 위한 체류자격변경은 불가합니다.'],
         conditions_en=['The permitted stay is counted from the date of entry.', 'Changes for E-6-2-type entertainment activities are not allowed.'],
         notes_ko=[OFFICER_NOTE_KO], notes_en=[OFFICER_NOTE_EN])

# ==========================================================================
# F-5 영주 — visa manual 33. 영주(F-5)
# ==========================================================================
F55_VISA = '① 사증발급신청서 (별지 제17호 서식), 여권, 표준규격사진 1매, 수수료 ② 외국인투자기업 등록증명서 사본'
guidance('F-5-5', 'visa_issuance', manual=VISA, section='영주(F-5) — 공관장 재량으로 발급할 수 있는 사증 1. 고액투자외국인에 대한 영주사증 발급', anchor='1. 고액투자외국인에 대한 영주사증 발급',
         summary_ko='영주자격 신청 시 「외국인투자 촉진법」에 따라 미화 50만 불 이상을 투자하고 국민을 5인 이상 고용한 외국투자가에게는 재외공관장 재량으로 영주사증이 발급됩니다.',
         summary_en='A foreign investor who has invested USD 500,000 or more under the Foreign Investment Promotion Act and employs 5 or more Korean nationals can be issued a permanent-residence visa at the mission head\'s discretion.',
         docs=[item('f5_c_visa_app_17', anchor=F55_VISA), item('passport', anchor=F55_VISA), item('photo', anchor=F55_VISA), item('fee', anchor=F55_VISA),
               item('f5_c_f55_fdi_reg_copy', anchor='② 외국인투자기업 등록증명서 사본'),
               item('guarantor', anchor='② 외국인투자기업 등록증명서 사본 ③ 신원보증서'),
               item('f5_c_f55_biz_corp_copy', anchor='④ 사업자 등록증 사본 및 법인 등기사항전부증명서'),
               item('f5_c_f55_income_certs', anchor='⑤ 신청자 본인의 소득금액 증명원(세무서 발급) 및 고용 내국인 5인 이상의 소득금액 증명원(세무서 발급)'),
               item('f5_c_f55_fulltime_proof', anchor='⑥ 고용 내국인의 정규직(전일제 상용고용 형태) 고용 입증서류(고용계약서, 정규직 고용확인서 등)')],
         notes_ko=[OFFICER_NOTE_KO], notes_en=[OFFICER_NOTE_EN])

F511_VISA = '① 신청서, 여권, 표준규격사진 1매, 수수료 ② 신원보증서 ③ 점수제 해당항목 입증서류'
guidance('F-5-11', 'visa_issuance', manual=VISA, doc_page_window=12,
         section='영주(F-5) — 공관장 재량으로 발급할 수 있는 사증 2. 특정분야의 능력소유자에 대한 영주사증 발급', anchor='2. 특정분야의 능력소유자에 대한 영주사증 발급 : 법무부장관 승인 필요',
         summary_ko='과학·경영·교육·문화예술·체육 등 특정 분야에서 탁월한 능력이 있는 사람 중 법무부장관이 인정하는 사람에게는 법무부장관 승인을 받아 영주사증이 발급됩니다. 필수항목 1개 이상을 갖추고 필수·선택항목 합산 점수가 기준에 해당해야 하며, 생계유지능력 요건은 면제됩니다.',
         summary_en='People with outstanding ability in science, management, education, culture and arts, sports or similar fields recognised by the Minister of Justice can be issued a permanent-residence visa with the Minister\'s approval. You need at least one mandatory item and a combined points score meeting the threshold; the livelihood requirement is waived.',
         docs=[item('app_form', anchor=F511_VISA), item('passport', anchor=F511_VISA), item('photo', anchor=F511_VISA), item('fee', anchor=F511_VISA),
               item('guarantor', anchor=F511_VISA), item('f5_c_points_proof', anchor=F511_VISA)],
         conditions_ko=['필수항목 30점 이상이면 합산 50점 이상(체류기간 무관), 20~29점이면 합산 100점 이상(체류기간 무관), 10~19점이면 합산 100점 이상이면서 외국인등록 후 1년 이상 국내 체류가 필요합니다.'],
         conditions_en=['Mandatory items 30+ points: total 50+ (any stay); 20–29: total 100+ (any stay); 10–19: total 100+ and at least 1 year in Korea after registration.'],
         notes_ko=[OFFICER_NOTE_KO], notes_en=[OFFICER_NOTE_EN])

guidance('F-5', 'visa_issuance_confirmation', manual=VISA, state='NOT_APPLICABLE', completeness='SOURCE_ONLY',
         section='영주(F-5) — 사증발급인정서 발급대상', anchor='☞ 사증발급인정서 발급대상 아님',
         summary_ko='영주(F-5)는 사증발급인정서 발급대상이 아닙니다.',
         summary_en='F-5 is not eligible for a visa issuance confirmation.')

# ==========================================================================
# F-5 영주 — stay manual 영주(F-5): 체류자격 부여, 재입국허가
# ==========================================================================
F5_GRANT = '① 신청서(별지 34호 서식), 여권, 표준규격사진 1매, 수수료 ② 가족관계 입증서류(출생증명서 등) ③ 국적국의 신분을 증명하는 서류'
guidance('F-5', 'status_grant', section='영주(F-5) — 체류자격 부여',
         anchor='대한민국에서 체류하고 있는 영주(F-5) 자격의 부 또는 모가 대한민국에서 출생한 자녀에 대하여 체류자격부여를 신청한 경우 영주(F-5)자격 부여',
         summary_ko='국내에 체류하는 영주(F-5) 자격의 부 또는 모가 대한민국에서 출생한 자녀에 대해 체류자격 부여를 신청하면 영주(F-5) 자격이 부여됩니다. 출생한 날부터 90일 이내에 신청하며, 해외에서 출생한 자녀는 제외됩니다.',
         summary_en='When a parent holding F-5 in Korea applies for status for a child born in Korea, the child is granted F-5. Apply within 90 days of birth; children born abroad are excluded.',
         timing_ko='출생한 날부터 90일 이내', timing_en='Within 90 days of birth',
         docs=[item('app_form_34', anchor=F5_GRANT), item('passport', anchor=F5_GRANT), item('photo', anchor=F5_GRANT), item('fee', anchor=F5_GRANT),
               item('f5_c_family_birth_proof', anchor=F5_GRANT), item('f5_c_national_id_proof', anchor=F5_GRANT)],
         notes_ko=[OFFICER_NOTE_KO], notes_en=[OFFICER_NOTE_EN])

guidance('F-5', 'reentry', state='CONDITIONAL', completeness='SOURCE_ONLY', section='영주(F-5) — 재입국허가',
         anchor='출국한 날부터 2년을 초과하고자 하는 경우 기간만료 전에 재외공관에서 재입국허가 연장 필요(허가기간 3월 이내)',
         summary_ko='영주(F-5)는 출국한 날부터 2년 이내에 재입국하면 재입국허가가 면제됩니다. 2년을 넘기려면 기간 만료 전에 재외공관에서 재입국허가 연장(허가기간 3월 이내)을 받아야 합니다.',
         summary_en='F-5 holders are exempt from a re-entry permit if they return within 2 years of departure. To stay away longer, extend the re-entry permit at a Korean mission before it expires (up to 3 months).',
         period_ko='면제: 출국일부터 2년 이내 / 재외공관 연장: 2년 만료 시점부터 3월 이내', period_en='Exempt within 2 years of departure / mission extension: up to 3 months from the end of the 2 years',
         conditions_ko=['재입국면제 기간(출국한 날부터 2년 이내) 또는 재입국허가 기간까지 대한민국에 입국하지 않으면 영주자격이 상실됩니다.'],
         conditions_en=['Permanent residence is lost if you do not return within the exemption period (2 years from departure) or the permitted re-entry period.'])

# ==========================================================================
# F-5 영주 — stay manual: 외국적동포를 제외한 영주(F-5) 체류자격 부여 (체류자격 변경허가)
#   □ 공통 서류 (p.443-445) + 영주자격별 다. 제출서류 (p.453-479)
# ==========================================================================
F5_CHANGE_ANCHOR = '공통 서류(영주자격별 개별 서류는 후술)'
F5_SEC = '영주(F-5) — 체류자격 변경허가 · 외국적동포를 제외한 영주(F-5) 체류자격 부여'

# Subcode groups named by the manual (exemption / exclusion lists).
F5_LIVELIHOOD_EXEMPT = {'F-5-5', 'F-5-11', 'F-5-12', 'F-5-17', 'F-5-19', 'F-5-20', 'F-5-21', 'F-5-22', 'F-5-23', 'F-5-24', 'F-5-25'}
F5_BASIC_EXEMPT = {'F-5-5', 'F-5-8', 'F-5-9', 'F-5-11', 'F-5-12', 'F-5-13', 'F-5-15', 'F-5-17', 'F-5-19', 'F-5-20', 'F-5-21', 'F-5-22', 'F-5-23', 'F-5-24', 'F-5-25', 'F-5-26'}
F5_GUARANTOR_EXCLUDED = {'F-5-17', 'F-5-19', 'F-5-21', 'F-5-22', 'F-5-23'}
F5_CRIME_CHECK_OMITTABLE = {'F-5-5', 'F-5-9', 'F-5-11', 'F-5-12', 'F-5-15'}


def f5_common_docs(code):
    docs = [
        item('f5_c_app_form_stamp', anchor='① 통합신청서(수입인지 포함)'),
        item('passport', anchor='① 통합신청서(수입인지 포함) ② 여권'),
        item('arc', anchor='② 여권 ③ 외국인등록증'),
        item('f5_c_photo_fee_no_arc', 'CONDITIONAL_REQUIRED', anchor='외국인등록증이 없는 경우 최근 6개월이내 촬영한 여권용 사진 1매 및 영주권 발급 수수료 추가',
             applies_when_ko='외국인등록증이 없는 경우', applies_when_en='If you have no residence card'),
        residence(anchor='④ 체류지 입증서류', alts=[{'ko': '부동산 임대차 계약서', 'en': 'Real-estate lease contract'}, {'ko': '등기부사항 전부 증명서', 'en': 'Real-estate register certificate'}]),
    ]
    if code in F5_CRIME_CHECK_OMITTABLE:
        docs.append(item('overseas_criminal_record', 'MAY_BE_REQUESTED_BY_OFFICER', anchor='⑤ 해외범죄경력증명서 ※ 제출 생략 가능자는 별도의 요구가 없을 경우 제출 제외',
                         applies_when_ko='고액 투자자(F-5-5)·첨단분야 박사(F-5-9)·일반분야 박사(F-5-15)·특정분야 능력 소유자(F-5-11)·특별공로자(F-5-12) 신청자는 제출 생략 대상이며, 별도 요구가 있을 때만 제출합니다.',
                         applies_when_en='F-5-5, F-5-9, F-5-15, F-5-11 and F-5-12 applicants may omit it unless specifically requested.'))
    else:
        docs.append(item('overseas_criminal_record', 'CONDITIONAL_REQUIRED', anchor='⑤ 해외범죄경력증명서 ※ 제출 생략 가능자는 별도의 요구가 없을 경우 제출 제외',
                         applies_when_ko='제출 생략 대상(신청일 기준 만 14세 미만, 국내에서 10년 이상 계속 합법 체류 등 매뉴얼의 제출기준)에 해당하지 않는 경우',
                         applies_when_en='Unless you fall under an omission case in the manual\'s criteria (under 14 on the application date, 10+ years of continuous lawful stay, etc.)'))
    if code not in F5_GUARANTOR_EXCLUDED:
        docs.append(item('guarantor', 'CONDITIONAL_REQUIRED', anchor='⑥ 신원보증서(※ 면제자 제출 제외)',
                         applies_when_ko='매뉴얼의 신원보증서 면제 대상(1948.8.15 이전 입국 재한화교와 그 직계존비속으로 기존 F-2 체류 중인 사람 등)이 아닌 경우',
                         applies_when_en='Unless you are exempt under the manual (e.g. overseas Chinese who entered before 1948-08-15 and their lineal relatives staying on F-2)'))
    if code not in F5_LIVELIHOOD_EXEMPT:
        docs += [
            item('f5_c_tax_paid_proof', anchor='㉠ 국세, 지방세 등 납세 완납 관련 공적 증명 서류 (납세증명서 또는 체납증명서 등)'),
            item('f5_c_income_tax_proof', anchor='총수익과 납부한 소득세 등이 기재된 ‘소득금액증명’(세무서 발급) 등 납부한 세금 관련 공적 증명 서류'),
        ]
    if code not in F5_BASIC_EXEMPT:
        docs.append(item('f5_c_basic_knowledge', 'CONDITIONAL_REQUIRED', anchor='⑧ 기본소양 요건 입증 서류(※ 면제자 제출 제외)',
                         applies_when_ko='기본소양 요건 면제 대상(만 15세 미만 미성년, 정규 교육기관 재학 중인 만 15세 이상 미성년 등)이 아닌 경우',
                         applies_when_en='Unless exempt from the basic-knowledge requirement (minors under 15, minors 15+ enrolled in a regular school, etc.)'))
    docs.append(item('f5_c_basic_info_form', anchor='⑨ 영주(F-5)자격 신청자 기본정보(※ 신청자가 작성하여 제출)'))
    return docs


def f5_change(code, subsec, summary_ko, summary_en, extra_docs, covers=None, conditions_ko=None, conditions_en=None):
    guidance(code, 'status_change', section=f'{F5_SEC} — {subsec}', anchor=F5_CHANGE_ANCHOR, doc_page_window=40, covers=covers,
             summary_ko=summary_ko, summary_en=summary_en,
             docs=f5_common_docs(code) + extra_docs,
             conditions_ko=(conditions_ko or []) + ['신청인은 대한민국 국적을 보유한 복수국적자가 아니어야 합니다.'],
             conditions_en=(conditions_en or []) + ['You must not be a dual national holding Korean nationality.'],
             notes_ko=['공통 서류는 모든 영주자격에 공통으로 적용되며, 영주자격별 개별 서류를 함께 냅니다.', OFFICER_NOTE_KO],
             notes_en=['The common documents apply to every F-5 subtype, together with the documents for your subtype.', OFFICER_NOTE_EN])


f5_change('F-5-1', '1. 일반 영주자〔F-5-1〕',
          '일반 영주(F-5-1)는 성년으로서 주재(D-7)~특정활동(E-7) 또는 거주(F-2) 자격으로 신청일 기준 5년 이상 계속 체류한 사람이 신청합니다. 공통 서류에 신청 당시 체류자격별(D-7, D-8·D-9, D-10·E-7) 서류를 더해 냅니다.',
          'General permanent residence (F-5-1) is for adults who have stayed continuously for 5+ years on D-7 to E-7 or F-2. Submit the common documents plus those for your current status (D-7, D-8/D-9, D-10/E-7).',
          [item('f5_c_f51_d7', 'CONDITIONAL_REQUIRED', anchor='○ D-7 : 재직증명서 또는 파견명령서', applies_when_ko='주재(D-7) 자격인 경우', applies_when_en='You hold D-7'),
           item('f5_c_f51_d8d9', 'CONDITIONAL_REQUIRED', anchor='○ D-8, D-9 : 매출액 또는 수출액 입증서류 등', applies_when_ko='기업투자(D-8)·무역경영(D-9) 자격인 경우', applies_when_en='You hold D-8 or D-9'),
           item('f5_c_f51_d10e7', 'CONDITIONAL_REQUIRED', anchor='○ D-10, E-7 : 해당 학위증, 고용계약서 등', applies_when_ko='구직(D-10)·특정활동(E-7) 자격인 경우', applies_when_en='You hold D-10 or E-7')],
          conditions_ko=['생계유지능력: 전년도 1인당 GNI 2배 이상 소득 또는 전년도 평균 순자산 1.5배 이상 자산 (E-5 레지던트는 GNI 이상)', 'D-8은 이전 2년간 연평균 매출액 10억원 이상, D-9는 연평균 수출액 5억원 이상 또는 매출액 10억원 이상이 필요합니다.'],
          conditions_en=['Livelihood: income of 2x GNI per capita or assets of 1.5x average net assets (GNI for E-5 residents)', 'D-8 needs average annual sales of KRW 1 billion over the prior 2 years; D-9 needs exports of KRW 500 million or sales of KRW 1 billion.'])

f5_change('F-5-4', '3. 일반 영주자의 배우자 또는 미성년 자녀〔F-5-4〕',
          '영주자격(F-5)을 가진 사람의 배우자 또는 미성년 자녀로서 거주(F-2) 자격으로 2년 이상 가족관계를 유지하며 체류 중인 사람(F-5-4)은 공통 서류에 가족관계 입증 서류·출생증명서 등을 더해 냅니다. 점수제 영주자·관광휴양시설 투자자·공익사업투자자의 가족은 별도 규정을 따릅니다.',
          'Spouses or minor children of an F-5 holder who have stayed 2+ years on F-2 keeping the family relationship (F-5-4) submit the common documents plus proof of family relationship, birth certificate, etc. Families of points-based, tourism-resort and public-interest investors follow separate rules.',
          [item('f5_c_f54_family', anchor='○ 가족관계 입증 서류, 출생증명서 등 4. 고액 투자자')],
          conditions_ko=['생계유지능력: 전년도 1인당 GNI 이상 소득 또는 전년도 평균 순자산 이상 자산', '심사 결정일까지 혼인관계를 유지해야 합니다(이혼 또는 사실혼은 불허).'],
          conditions_en=['Livelihood: income of at least GNI per capita or assets of at least average net assets', 'The marriage must continue until the decision (divorce or de facto marriage is refused).'])

f5_change('F-5-5', '4. 고액 투자자〔F-5-5〕',
          '고액 투자자(F-5-5)는 「외국인투자 촉진법」에 따라 미화 50만 달러 이상 투자를 유지하고 국민 5명 이상을 6개월 이상 정규직으로 직접 고용 중인 투자자 본인이 신청합니다(생계유지능력 요건 면제). 공통 서류에 투자기업·고용 입증 서류를 더해 냅니다.',
          'High-value investors (F-5-5) who keep an investment of USD 500,000+ under the Foreign Investment Promotion Act and directly employ 5+ Korean nationals full-time for 6+ months apply in person (livelihood requirement waived). Submit the common documents plus company and employment proof.',
          [item('f5_c_f55_corp_docs', anchor='○ 외국인투자기업 등록증명서, 법인등기사항전부증명서, 사업자등록증'),
           item('f5_c_f55_employee_proof', anchor='○ 고용 내국인 정규직 고용 입증서류')],
          conditions_ko=['투자자 본인 이외에 임직원이나 직원은 대상이 아니며, 공동 투자 시 본인 투자금액이 미화 50만 달러 미만이면 신청자격이 없습니다.'],
          conditions_en=['Only the investor qualifies, not officers or staff; in a joint investment, your own share must be at least USD 500,000.'])

f5_change('F-5-8', '5. 대한민국 출생 재한화교〔F-5-8〕',
          '대한민국에서 출생한 재한화교로서 종전 거주(F-2) 체류자격을 가졌던 사람(F-5-8)은 공통 서류에 화교협회 발행 호적등본, 출생증명서 등을 더해 냅니다.',
          'Overseas Chinese born in Korea who held the former F-2 status (F-5-8) submit the common documents plus the family register issued by the Overseas Chinese Association, a birth certificate, etc.',
          [item('f5_c_f58_hukou', anchor='○ 화교협회 발행 호적등본, 출생증명서 등')],
          conditions_ko=['생계유지능력: 동거가족 2인 이하는 전년도 1인당 GNI의 70% 이상, 3인 이상은 GNI 이상 (미충족 시 생계를 같이하는 가족 명의 자산 6천만원 이상이면 인정)'],
          conditions_en=['Livelihood: 70% of GNI per capita for households of 2 or fewer, GNI for 3+ (or family assets of KRW 60 million if income falls short)'])

F59_EXTRA = [item('f5_c_phd_copy', anchor='○ 박사 학위증 사본'),
             item('f5_c_company_reg_employment', anchor='○ 박사 학위증 사본 ※ 성적증명서’ 등을 추가 징구 가능 ○ 소속기업 사업자등록증 사본, 재직증명서'),
             item('f5_c_regular_staff_proof', anchor='○ 박사 학위증 사본 ※ 성적증명서’ 등을 추가 징구 가능 ○ 소속기업 사업자등록증 사본, 재직증명서 ○ 4대 보험 사업장 가입자 명부, 고용 계약서 등 정규직 여부 확인서류 등')]
f5_change('F-5-9', '6. 첨단분야 박사〔F-5-9〕',
          '첨단기술 분야의 해외 박사학위를 취득한 후 국내기업 등에서 학위 관련 분야에 1년 이상 전일제로 계속 근무 중인 사람(F-5-9)은 공통 서류에 박사 학위증 사본, 소속기업 사업자등록증 사본·재직증명서, 정규직 여부 확인서류를 더해 냅니다.',
          'Holders of a foreign doctorate in a high-tech field who have worked full-time for 1+ year in a related field at a Korean company (F-5-9) submit the common documents plus a copy of the doctorate, the company registration and employment certificate, and proof of regular employment.',
          F59_EXTRA,
          conditions_ko=['생계유지능력: 전년도 1인당 GNI 이상 소득 또는 전년도 평균 순자산 이상 자산', '성적증명서 등을 추가로 요구할 수 있습니다.'],
          conditions_en=['Livelihood: income of at least GNI per capita or assets of at least average net assets', 'Transcripts may additionally be requested.'])
f5_change('F-5-15', '6. 일반분야 박사〔F-5-15〕',
          '국내 대학원에서 정규 박사과정을 이수하고 박사학위를 취득한 후 국내기업에서 1년 이상 전일제로 계속 근무 중인 사람(F-5-15)은 공통 서류에 박사 학위증 사본, 소속기업 사업자등록증 사본·재직증명서, 정규직 여부 확인서류를 더해 냅니다.',
          'People who completed a regular doctoral programme at a Korean graduate school and have worked full-time for 1+ year at a Korean company (F-5-15) submit the common documents plus a copy of the doctorate, the company registration and employment certificate, and proof of regular employment.',
          F59_EXTRA,
          conditions_ko=['생계유지능력: 전년도 1인당 GNI 이상 소득 또는 전년도 평균 순자산 이상 자산', '성적증명서 등을 추가로 요구할 수 있습니다.'],
          conditions_en=['Livelihood: income of at least GNI per capita or assets of at least average net assets', 'Transcripts may additionally be requested.'])

f5_change('F-5-10', '7. 학사․석사 학위증 및 자격증 소지자〔F-5-10〕',
          '법무부장관이 정하는 학사 이상 학위증 또는 기술자격증이 있고 국내에 3년 이상 체류하며 국내기업에 정규직으로 1년 이상 근무 중인 사람(F-5-10)은 공통 서류에 학위증 또는 자격증 사본, 소속기업 사업자등록증 사본·재직증명서, 정규직 여부 확인서류를 더해 냅니다.',
          'Holders of a qualifying bachelor\'s or higher degree or technical qualification who have stayed 3+ years and work full-time for 1+ year at a Korean company (F-5-10) submit the common documents plus a copy of the degree or qualification, the company registration and employment certificate, and proof of regular employment.',
          [item('f5_c_degree_or_license_copy', anchor='○ 학위증 또는 자격증 사본'),
           item('f5_c_company_reg_employment', anchor='○ 학위증 또는 자격증 사본 ※ 성적증명서’ 등을 추가 징구 가능 ○ 소속기업 사업자등록증 사본, 재직증명서'),
           item('f5_c_regular_staff_proof', anchor='○ 학위증 또는 자격증 사본 ※ 성적증명서’ 등을 추가 징구 가능 ○ 소속기업 사업자등록증 사본, 재직증명서 ○ 4대 보험 사업장 가입자 명부, 고용 계약서 등 정규직 여부 확인서류 등')],
          conditions_ko=['생계유지능력: 전년도 1인당 GNI 이상 소득 (신청인만 소득주체로 인정)'],
          conditions_en=['Livelihood: income of at least GNI per capita (only your own income counts)'])

f5_change('F-5-11', '8. 특정분야 능력 소유자〔F-5-11〕',
          '과학·경영·교육·문화예술·체육 등 특정 분야에서 탁월한 능력이 있어 법무부장관이 인정하는 사람(F-5-11)은 점수제 요건을 충족해야 하며(생계유지능력 요건 면제), 공통 서류에 수상경력·경력증명서, 논문·연구실적 증명서류 등을 더해 냅니다.',
          'People with outstanding ability in science, management, education, culture and arts, sports or similar fields recognised by the Minister (F-5-11) must meet the points requirement (livelihood waived) and submit the common documents plus awards or career certificates, publications or research records, etc.',
          [item('f5_c_f511_awards', anchor='○ 해당 분야 수상경력 또는 경력증명서'),
           item('f5_c_f511_papers', anchor='○ 과학기술논문 인용색인(SCI) 등 논문게재 또는 연구실적 증명서류'),
           item('f5_c_f511_recognition', anchor='○ 과학, 경영 등 특정분야에서 인정받았음을 증명하는 서류'),
           item('f5_c_f511_points', anchor='○ 기타 점수제 해당항목 입증서류')])

f5_change('F-5-12', '9. 특별 공로자〔F-5-12〕',
          '대한민국에 특별한 공로가 있다고 법무부장관이 인정하는 사람(국가유공자와 그 배우자·자녀 등, F-5-12)은 생계유지능력 요건이 면제되며, 공통 서류에 사유서, 훈·포장 증서, 가족관계 및 기타 증빙 서류 등을 더해 냅니다.',
          'People recognised by the Minister as having made a special contribution to Korea (persons of national merit and their spouses and children, etc., F-5-12) are exempt from the livelihood requirement and submit the common documents plus a statement of reasons, order or medal certificate, family-relation and other supporting documents.',
          [item('f5_c_f512_docs', anchor='○ 사유서, 훈․포장 증서(수상자), 가족관계 및 기타 증빙 서류 등')])

f5_change('F-5-13', '10. 연금 수혜자〔F-5-13〕',
          '60세 이상으로서 신청일 이전 최근 1년 동안 국외로부터 받은 연간 연금액이 전년도 1인당 GNI의 2배 이상인 사람(F-5-13)은 공통 서류에 연금증서 사본 및 연금입금통장을 더해 냅니다.',
          'People aged 60+ whose annual pension from abroad over the last year is at least 2x GNI per capita (F-5-13) submit the common documents plus a copy of the pension certificate and the bankbook receiving it.',
          [item('f5_c_f513_pension', anchor='○ 연금증서 사본 및 연금입금통장')])

F516_EMP = '○ 소속기업 사업자등록증 사본, 고용계약서 사본, 재직증명서'
f5_change('F-5-16', '11. 점수제 영주자〔F-5-16〕',
          '점수제 거주(F-2-7) 자격으로 신청일 기준 3년 이상 계속 체류 중인 사람(F-5-16)은 공통 서류에 소속기업 사업자등록증 사본, 고용계약서 사본, 재직증명서를 더해 냅니다.',
          'People who have stayed continuously for 3+ years on points-based F-2-7 (F-5-16) submit the common documents plus the company registration copy, employment contract copy and certificate of employment.',
          [item('f5_c_f516_employment', anchor=F516_EMP)],
          conditions_ko=['생계유지능력: 전년도 1인당 GNI 2배 이상 소득 또는 전년도 평균 순자산 1.5배 이상 자산'],
          conditions_en=['Livelihood: income of 2x GNI per capita or assets of 1.5x average net assets'])
f5_change('F-5-18', '11. 점수제 영주자의 배우자 또는 미성년 자녀〔F-5-18〕',
          '점수제 영주자(F-5-16)의 배우자 또는 미성년 자녀로서 거주(F-2-71) 자격으로 2년 이상 가족관계를 유지하며 체류 중인 사람(F-5-18)은 공통 서류에 가족관계 입증서류를 더해 냅니다.',
          'Spouses or minor children of an F-5-16 holder who have stayed 2+ years on F-2-71 keeping the family relationship (F-5-18) submit the common documents plus proof of family relationship.',
          [item('f5_c_family_proof_dependants', anchor='○ 가족관계 입증서류(점수제 영주자의 배우자 또는 미성년 자녀 해당)')],
          conditions_ko=['생계유지능력: 전년도 1인당 GNI 이상 소득 또는 전년도 평균 순자산 이상 자산', '심사 결정일까지 혼인관계를 유지해야 합니다(이혼 또는 사실혼은 불허).'],
          conditions_en=['Livelihood: income of at least GNI per capita or assets of at least average net assets', 'The marriage must continue until the decision (divorce or de facto marriage is refused).'])

F517_INV = '○ 부동산 등기부등본 등 투자금을 유지하고 있음을 입증하는 서류(신청일 이전 최근 5일 이내 발급)'
f5_change('F-5-17', '12. 관광·휴양시설 투자자〔F-5-17〕',
          '관광·휴양시설 투자 거주(F-2-8) 자격으로 총 5년 이상 계속 투자를 유지 중인 사람(F-5-17)은 생계유지능력 요건이 면제되며, 공통 서류(신원보증서 제외)에 투자금 유지 입증서류를 더해 냅니다.',
          'People who have kept a tourism/resort-facility investment on F-2-8 for a total of 5+ years (F-5-17) are exempt from the livelihood requirement and submit the common documents (no letter of guarantee) plus proof that the investment is maintained.',
          [item('f5_c_f517_investment', anchor=F517_INV)])
f5_change('F-5-19', '12. 관광·휴양시설 투자자의 배우자 또는 미혼 자녀〔F-5-19〕',
          '관광·휴양시설 투자자(F-5-17)의 배우자 또는 미혼 자녀로서 거주(F-2-8·F-2-81) 자격을 5년 이상 유지하며 국내에 계속 체류 중인 사람(F-5-19)은 공통 서류(신원보증서 제외)에 투자금 유지 입증서류, 가족관계 입증서류, (미혼 자녀) 미혼 입증서류를 더해 냅니다.',
          'Spouses or unmarried children of an F-5-17 holder who have kept F-2-8/F-2-81 for 5+ years in Korea (F-5-19) submit the common documents (no letter of guarantee) plus proof the investment is maintained, proof of family relationship and, for unmarried children, proof of being unmarried.',
          [item('f5_c_f517_investment', anchor=F517_INV),
           item('f5_c_family_proof_dependants', anchor='○ 가족관계 입증서류 (배우자 또는 미혼 자녀 해당) ○ 미혼임을 입증하는 서류 (미혼 자녀만 해당)     13. 영주권자의 국내 출생자녀'),
           item('f5_c_unmarried_proof', 'CONDITIONAL_REQUIRED', anchor='○ 미혼임을 입증하는 서류 (미혼 자녀만 해당)     13. 영주권자의 국내 출생자녀', applies_when_ko='미혼 자녀', applies_when_en='Unmarried children')],
          conditions_ko=['동반신청의 경우 배우자 또는 부모가 F-5-17 자격변경을 허가받지 못하면 신청인의 영주자격 변경도 자동 불허됩니다.'],
          conditions_en=['In a joint application, if the spouse or parent is not granted F-5-17, your change is automatically refused.'])

f5_change('F-5-20', '13. 영주권자의 국내 출생자녀〔F-5-20〕',
          '출생 당시 부 또는 모가 영주자격(F-5)으로 국내에 체류하고 있는 국내 출생 친생자녀(F-5-20)는 출생한 날로부터 1년 미만에 신청하며(생계유지능력 요건 면제), 공통 서류에 가족관계 입증서류·출생증명서, 대한민국 국적 미보유 확인서 등을 더해 냅니다.',
          'Biological children born in Korea whose father or mother held F-5 at the time of birth (F-5-20) apply within 1 year of birth (livelihood waived) and submit the common documents plus proof of family relationship and birth, and a confirmation of not holding Korean nationality.',
          [item('f5_c_f520_family', anchor='○ 가족관계 입증서류*(중국의 경우 호구부 등), 출생증명서 등'),
           item('f5_c_f520_no_korean_nationality', anchor='○ 대한민국 국적 미보유 확인서*', role='principal_holder'),
           item('f5_c_f520_dna', 'CONDITIONAL_REQUIRED', anchor='부모의 법률상 가족관계 유지 기간이 신청자의 출생일 이전으로부터 1년 미만으로 친생자 여부의 확인이 필요한 경우 해당',
                applies_when_ko='부모의 법률상 가족관계 유지 기간이 출생일 이전 1년 미만이라 친생자 확인이 필요한 경우', applies_when_en='Parents\' legal family relationship began less than 1 year before the birth and parentage must be confirmed')],
          conditions_ko=['영주자격이 없는 부 또는 모는 계절근로(E-8), 비전문취업(E-9), 선원취업(E-10), 관광취업(H-1), 기타(G-1)를 제외한 장기 체류자격으로 국내에 합법 체류 중이어야 합니다.', '부모가 법률상 혼인 관계여야 하며, 신청자가 태어난 뒤 부모가 혼인신고를 한 경우는 대상이 아닙니다.', '출생한 날로부터 1년을 초과하면 이 영주자격(F-5-20)을 신청할 수 없으며, 90일을 초과하여 신청하면 범칙금 납부대상입니다.', '해외에서 출생한 사람과 양자관계에 의한 가족은 대상이 아닙니다.'],
          conditions_en=['A parent without permanent residence must be lawfully staying on a long-term status other than E-8, E-9, E-10, H-1 or G-1.', 'The parents must be legally married; if they registered the marriage after the child was born, the child is not covered.', 'After 1 year from birth you cannot apply for F-5-20; applying after 90 days incurs a fine.', 'Children born abroad and adoptive relationships are not covered.'])

F521_INV = '○ 투자금을 유지하고 있음을 입증하는 서류(영주신청일 이전 5일 이내 발급)'
f5_change('F-5-21', '14. 공익사업 일반투자자〔F-5-21〕',
          '공익사업 투자 거주(F-2) 자격으로 총 5년 이상 계속 투자를 유지 중인 사람(F-5-21)은 생계유지능력 요건이 면제되며, 공통 서류(신원보증서 제외)에 투자금 유지 입증서류를 더해 냅니다.',
          'People who have kept a public-interest project investment on F-2 for a total of 5+ years (F-5-21) are exempt from the livelihood requirement and submit the common documents (no letter of guarantee) plus proof that the investment is maintained.',
          [item('f5_c_f521_investment', anchor=F521_INV)])
f5_change('F-5-23', '14. 공익사업 은퇴이민 투자자〔F-5-23〕',
          '은퇴이민 투자 거주(F-2) 자격으로 총 5년 이상 계속 투자를 유지하고 투자금 외 본인 또는 배우자의 국내 보유자산이 3억원 이상인 사람(F-5-23)은 공통 서류(신원보증서 제외)에 투자금 유지 입증서류와 국내 보유자산 입증서류를 더해 냅니다.',
          'Retirement investors who have kept the investment on F-2 for 5+ years and whose (or whose spouse\'s) domestic assets besides the investment are KRW 300 million or more (F-5-23) submit the common documents (no letter of guarantee) plus proof the investment is maintained and proof of domestic assets.',
          [item('f5_c_f521_investment', anchor=F521_INV),
           item('f5_c_f523_assets', anchor='○ 은퇴이민자는 투자금 이외 본인 또는 배우자의 국내 보유자산(3억원 이상)입증하는 서류 추가')])
f5_change('F-5-22', '14. 공익사업 투자자의 배우자 또는 미혼 자녀〔F-5-22〕',
          '공익사업 투자자(F-5-21·F-5-23)의 배우자 또는 미혼 자녀로서 그 거주(F-2) 자격을 5년 이상 소지하고 국내에 계속 체류 중인 사람(F-5-22)은 공통 서류(신원보증서 제외)에 투자금 유지 입증서류, 가족관계 입증서류, (미혼 자녀) 미혼 입증서류를 더해 냅니다.',
          'Spouses or unmarried children of an F-5-21/F-5-23 holder who have held the related F-2 for 5+ years in Korea (F-5-22) submit the common documents (no letter of guarantee) plus proof the investment is maintained, proof of family relationship and, for unmarried children, proof of being unmarried.',
          [item('f5_c_f521_investment', anchor=F521_INV),
           item('f5_c_family_proof_dependants', anchor='○ 가족관계 입증서류 (배우자 또는 미혼 자녀 해당) ○ 미혼임을 입증하는 서류 (미혼 자녀만 해당)     15. 기술창업 투자자'),
           item('f5_c_unmarried_proof', 'CONDITIONAL_REQUIRED', anchor='○ 미혼임을 입증하는 서류 (미혼 자녀만 해당)     15. 기술창업 투자자', applies_when_ko='미혼 자녀', applies_when_en='Unmarried children')],
          conditions_ko=['동반신청의 경우 배우자 또는 부모의 영주자격 변경이 허가되지 않으면 신청인의 영주자격 변경도 불허됩니다.'],
          conditions_en=['In a joint application, if the spouse\'s or parent\'s change is not granted, yours is refused too.'])

f5_change('F-5-24', '15. 기술창업 투자자〔F-5-24〕',
          '기술창업(D-8-4) 자격으로 3년 이상 계속 체류하며 3억원 이상 투자금을 유치(또는 이에 준하는 자본금 확보)하고 국민 2명 이상을 6개월 이상 전일제로 고용 중인 사람(F-5-24)은 생계유지능력 요건이 면제되며, 공통 서류에 법인 서류, 투자금 유치 증명서류, 고용 입증서류를 더해 냅니다.',
          'Tech start-up founders on D-8-4 for 3+ years who attracted KRW 300 million or more (or hold equivalent capital) and employ 2+ Korean nationals full-time for 6+ months (F-5-24) are exempt from the livelihood requirement and submit the common documents plus company documents, proof of funding and proof of employment.',
          [item('f5_c_f524_corp', anchor='○ 사업자등록증, 법인등기사항전부증명서, 사업자등록증'),
           item('f5_c_f524_funding', anchor='○ 투자자로부터 3억원 이상의 투자금을 유치하였거나, 이에 준하는 자본금을 갖고 있음을 증명하는 서류(재무제표, 투자금 도입 내역서 등)'),
           item('f5_c_f524_employees', anchor='○ 2명 이상의 국민을 6개월 이상 계속 고용하고 있음을 입증하는 서류')])

f5_change('F-5-25', '16. 조건부 고액투자자〔F-5-25〕',
          '한국산업은행의 공익사업 투자이민 펀드(원금보장 무이자형)에 30억 원 이상을 예치하고 5년간 투자 유지를 서약한 사람(F-5-25)은 생계유지능력 요건이 면제되며, 공통 서류에 투자금 예치확인서, 외화반입 입증서류, 투자유지 서약서를 더해 냅니다.',
          'People who deposited KRW 3 billion or more in the Korea Development Bank public-interest immigrant investment fund (principal-guaranteed, interest-free) and pledge to keep it for 5 years (F-5-25) are exempt from the livelihood requirement and submit the common documents plus the deposit confirmation, proof of bringing in foreign currency and the pledge.',
          [item('f5_c_f525_deposit', anchor='○ 투자금 예치확인서(한국산업은행 발행),'),
           item('f5_c_f525_fx', anchor='○ 외화반입 관련 입증서류(외국환매입증명서 등)'),
           item('f5_c_f525_pledge', anchor='○ 외화반입 관련 입증서류(외국환매입증명서 등) ○ 투자유지 서약서')],
          conditions_ko=['예치한 금액 중 일부 또는 전부를 중도 인출하면 영주자격이 취소됩니다.'],
          conditions_en=['Withdrawing any part of the deposit early cancels the permanent residence.'])

f5_change('F-5-26', '17. 외국인투자기업의 연구개발 인력〔F-5-26〕',
          '기업투자(D-8) 가목 자격으로 외국인투자 연구개발시설의 필수전문인력으로 3년 이상 계속 근무하고 학사 이상 학위가 있는 사람(F-5-26)은 공통 서류에 연구개발시설 지정서 사본, 파견명령서 또는 재직증명서, 소득금액증명 등을 더해 냅니다.',
          'Essential R&D staff of a foreign-invested R&D facility who have worked 3+ years on D-8 (a) and hold a bachelor\'s or higher degree (F-5-26) submit the common documents plus a copy of the facility designation, a dispatch order or employment certificate, an income certificate, etc.',
          [item('f5_c_f526_docs', anchor='○ 연구개발시설 지정서(산업통상자원부 공문) 사본, 파견명령서 또는 재직증명서, 소득금액증명 등')],
          conditions_ko=['생계유지능력: 전년도 1인당 GNI 2배 이상 소득 또는 전년도 평균 순자산 1.5배 이상 자산'],
          conditions_en=['Livelihood: income of 2x GNI per capita or assets of 1.5x average net assets'])

F528_DOC = '◦ 가족관계 등 입증 서류(국내 출생인 경우 국내 출생증명서)'
f5_change('F-5-28', '18. 특별기여자〔F-5-28〕',
          '거주(F-2) 카목(특별기여자) 자격으로 신청일 현재 2년 이상 국내에 계속 체류한 사람(F-5-28)이 신청하며, 생계유지능력·품행단정·기본소양 요건을 갖춰야 합니다. 공통 서류에 가족관계 등 입증 서류를 함께 냅니다.',
          'People who have stayed continuously for 2+ years on F-2 (special contributors) (F-5-28) apply and must meet the livelihood, good-conduct and basic-knowledge requirements. Submit the common documents with proof of family relationship etc.',
          [],
          conditions_ko=['생계유지능력: 전년도 1인당 GNI 이상 소득 또는 전년도 가구당 평균 순자산 이상 자산'],
          conditions_en=['Livelihood: income of at least GNI per capita or assets of at least average household net assets'])
f5_change('F-5-29', '18. 특별기여자의 배우자 및 미성년 자녀〔F-5-29〕',
          '영주자격(F-5-28)을 가진 사람의 배우자 또는 미성년 자녀로서 특별기여자(F-2-16) 자격으로 2년 이상 국내에 체류한 사람(F-5-29)은 공통 서류에 가족관계 등 입증 서류(국내 출생인 경우 국내 출생증명서)를 더해 냅니다.',
          'Spouses or minor children of an F-5-28 holder who have stayed 2+ years on F-2-16 (F-5-29) submit the common documents plus proof of family relationship etc. (Korean birth certificate if born in Korea).',
          [item('f5_c_f528_family', anchor=F528_DOC)],
          conditions_ko=['생계유지능력: 전년도 1인당 GNI 이상 소득 또는 전년도 가구당 평균 순자산 이상 자산', '심사 결정일까지 법률상 혼인관계 및 실제 가족관계를 유지해야 합니다(이혼 또는 사실혼 불인정).'],
          conditions_en=['Livelihood: income of at least GNI per capita or assets of at least average household net assets', 'The legal marriage and actual family relationship must continue until the decision (divorce or de facto marriage not recognised).'])

# --------------------------------------------------------------------------
# F-5-2 / F-5-3 — 2. 결혼이민자(F-5-2), 국민의 미성년 자녀(F-5-3) (별도 지침, own document list)
# --------------------------------------------------------------------------
F52_SEC = f'{F5_SEC} — 2. 결혼이민자(F-5-2), 국민의 미성년 자녀(F-5-3)'
F52_COMMON = '공통 서류 ･ 여권, 외국인등록증, 통합신청서, 표준규격 사진, 수수료, 체류지 입증서류 가족관계 확인 서류 ･ 한국인 배우자의 기본증명서'


def f52_tail():
    return [
        item('f5_c_f52_crime_6m', anchor='품행단정 요건 서류 ･ 해외범죄경력증명(신청일로부터 6개월 이내 발급)'),
        one_of('f52_livelihood', item('f5_c_f52_income', 'ALTERNATIVE_DOCUMENT', anchor='(일인당 국민총소득 이상의 소득금액) 본인 또는 생계를 같이하는 가족의 소득금액증명'), item('f5_c_f52_assets', 'ALTERNATIVE_DOCUMENT', anchor='(중위수준 이상의 가계 자산) 본인과 생계를 같이하는 가족 모두의 자산 증빙서류')),
        one_of('f52_basic', item('f5_c_f52_kiip', 'ALTERNATIVE_DOCUMENT', anchor='(사회통합프로그램 이수) “사회통합프로그램 이수증”(한국이민영주적격과정 또는 한국이민귀화적격과정)'), item('f5_c_f52_kiprat', 'ALTERNATIVE_DOCUMENT', anchor='(종합평가 60점 이상) “한국이민영주적격시험 합격증”(KIPRAT) 또는 “한국이민귀화적격시험 합격증”(KINAT)')),
        item('f5_c_f52_other', 'MAY_BE_REQUESTED_BY_OFFICER', anchor='그 밖에 심사에 필요하다고 청장 등이 인정한 서류(요건 완화･면제 대상자의 해당 사유 소명 자료 등) 등'),
    ]


guidance('F-5-2', 'status_change', section=F52_SEC, anchor='2. 결혼이민자(F-5-2), 국민의 미성년 자녀(F-5-3)', doc_page_window=4,
         summary_ko='결혼이민자 영주(F-5-2)는 결혼이민(F-6) 자격으로 2년 이상 국내에 계속 체류한 사람으로서 ① 한국인 배우자와 정상적인 혼인생활을 유지하는 사람, ② 한국인 (전)배우자와의 자녀를 국내에서 양육하는 부 또는 모, ③ 한국인 배우자의 사망·실종 등 본인에게 책임이 없는 사유로 혼인관계를 유지할 수 없는 사람이 신청합니다. 공통 서류, 유형별 가족관계·혼인생활 확인 서류, 해외범죄경력증명, 생계유지능력·기본소양 요건 서류를 냅니다.',
         summary_en='Marriage-immigrant permanent residence (F-5-2) is for people who have stayed 2+ years on F-6 and (1) keep a normal marriage with a Korean spouse, (2) raise in Korea a child of a Korean (former) spouse, or (3) cannot continue the marriage because of the Korean spouse\'s death, disappearance or another reason not their fault. Submit the common documents, the family and marriage documents for your case, an overseas criminal record and proof of livelihood and basic knowledge.',
         docs=[item('f5_c_f52_common', anchor=F52_COMMON),
               item('f5_c_f52_spouse_certs', 'CONDITIONAL_REQUIRED', anchor='한국인 배우자의 기본증명서, 혼인관계증명서, 가족관계증명서, 주민등록표 등본', applies_when_ko='① 한국인 배우자와 혼인생활 유지', applies_when_en='(1) Marriage continuing with a Korean spouse', role='korean_spouse'),
               item('f5_c_f52_child_family', 'CONDITIONAL_REQUIRED', anchor='(자녀가 있을 경우) 자녀의 가족관계증명서', applies_when_ko='① 혼인생활 유지 + 자녀가 있는 경우', applies_when_en='(1) With children'),
               item('f5_c_f52_couple_photos', 'CONDITIONAL_REQUIRED', anchor='그간 부부가 혼인생활 중 함께 찍은 사진(3장 이상)', applies_when_ko='① 한국인 배우자와 혼인생활 유지', applies_when_en='(1) Marriage continuing with a Korean spouse'),
               item('f5_c_f52_ex_marriage', 'CONDITIONAL_REQUIRED', anchor='가족관계 확인 서류 ･ 한국인 (前)배우자와의 혼인관계증명서 ･ 한국인 (前)배우자와의 관계에서 출생한 자녀의 기본증명서', applies_when_ko='② 자녀양육 또는 ③ 혼인단절', applies_when_en='(2) Child-rearing or (3) marriage breakdown'),
               item('f5_c_f52_child_certs', 'CONDITIONAL_REQUIRED', anchor='한국인 (前)배우자와의 관계에서 출생한 자녀의 기본증명서, 가족관계증명서', applies_when_ko='② 자녀양육 (③ 혼인단절은 자녀가 있는 경우)', applies_when_en='(2) Child-rearing ((3) marriage breakdown, if there are children)'),
               item('f5_c_f52_raising_photos', 'CONDITIONAL_REQUIRED', anchor='그간 자녀를 양육하며 찍은 사진(3장 이상)', applies_when_ko='② 자녀양육', applies_when_en='(2) Child-rearing'),
               item('f5_c_f52_child_expenses', 'CONDITIONAL_REQUIRED', anchor='자녀양육에 필요한 비용(용돈, 학비, 의료비 등) 지출 내역', applies_when_ko='② 자녀양육', applies_when_en='(2) Child-rearing'),
               item('f5_c_f52_marriage_life', 'CONDITIONAL_REQUIRED', anchor='혼인 중 함께 찍은 사진, 주고받은 메시지 내역, 주변인 확인서 등 혼인생활 확인 서류', applies_when_ko='③ 혼인단절', applies_when_en='(3) Marriage breakdown'),
               item('f5_c_f52_fault_proof', 'CONDITIONAL_REQUIRED', anchor='이혼판결문, 진단서, 수사 및 범죄경력증명 자료, 주변인 확인서 등 한국인 (前)배우자의 귀책사유 입증 서류', applies_when_ko='③ 혼인단절', applies_when_en='(3) Marriage breakdown'),
               ] + f52_tail(),
         conditions_ko=['생계유지능력: 본인 또는 생계를 같이하는 가족의 소득합산금액이 전년도 1인당 GNI 이상이거나 자산 합계가 중위수준(순자산 중앙값) 이상 (소득·자산 합산 불가)',
                        '기본소양: 사회통합프로그램 이수 또는 종합평가 60점 이상',
                        '법무부고시(영주자격 요건 완화 및 면제 기준 고시)에 따라 생계유지능력·기본소양 요건을 완화 또는 면제받을 수 있습니다(1345 또는 관할 출입국·외국인관서 문의).'],
         conditions_en=['Livelihood: combined income of you or the family sharing your livelihood of at least GNI per capita, or total assets at or above the median net assets (income and assets cannot be combined)',
                        'Basic knowledge: completion of the social integration program or a comprehensive-test score of 60+',
                        'The livelihood and basic-knowledge requirements may be relaxed or waived under the Ministry notice (ask 1345 or your immigration office).'],
         notes_ko=[OFFICER_NOTE_KO], notes_en=[OFFICER_NOTE_EN])

F53_COMMON = '공통 서류 ･ 여권, 외국인등록증, 통합신청서, 표준규격 사진, 수수료, 체류지 입증서류 가족관계 확인 서류 ･ 대한민국 국민인 부(父) 또는 모(母)의 기본증명서'
guidance('F-5-3', 'status_change', section=F52_SEC.replace('2. 결혼이민자(F-5-2), 국민의 미성년 자녀(F-5-3)', '2. 라. 국민의 미성년 자녀(F-5-3)'),
         anchor='라. 국민의 미성년 외국인 자녀로서, 거주(F-2) 자격으로 2년 이상 국내에 계속 체류하고 있는 사람', doc_page_window=3,
         summary_ko='국민의 미성년 외국인 자녀로서 거주(F-2) 자격으로 2년 이상 국내에 계속 체류한 사람(F-5-3)은 생계유지능력 요건이 적용되지 않으며, 공통 서류, 가족관계 확인 서류, 해외범죄경력증명(형사미성년자 제외), 기본소양 요건 서류를 냅니다. 나이와 재학 여부에 따라 기본소양 요건이 면제될 수 있습니다.',
         summary_en='Minor foreign children of Korean nationals who have stayed 2+ years on F-2 (F-5-3) are not subject to the livelihood requirement. Submit the common documents, family-relation documents, an overseas criminal record (not for those under the age of criminal responsibility) and basic-knowledge documents; the basic-knowledge requirement may be waived depending on age and schooling.',
         docs=[item('f5_c_f52_common', anchor=F53_COMMON),
               item('f5_c_f53_parent_certs', anchor='대한민국 국민인 부(父) 또는 모(母)의 기본증명서, 혼인관계증명서, 가족관계증명서, 주민등록표 등본', role='korean_spouse'),
               item('f5_c_f53_child_birth', anchor='미성년 자녀(신청인)의 출생증명서 등 가족관계증명 서류'),
               item('f5_c_f52_crime_6m', 'CONDITIONAL_REQUIRED', anchor='품행단정 요건 서류(형사미성년자는 제외) ･ 해외범죄경력증명(신청일로부터 6개월 이내 발급)', applies_when_ko='형사미성년자가 아닌 경우', applies_when_en='Unless under the age of criminal responsibility'),
               one_of('f53_basic', item('f5_c_f52_kiip', 'ALTERNATIVE_DOCUMENT', anchor='(사회통합프로그램 이수) “사회통합프로그램 이수증”(한국이민영주적격과정 또는 한국이민귀화적격과정) ･ (종합평가 60점 이상) “한국이민영주적격시험 합격증”(KIPRAT) 또는 “한국이민귀화적격시험 합격증”(KINAT) ･ (정규교육 과정 이수자)'), item('f5_c_f52_kiprat', 'ALTERNATIVE_DOCUMENT', anchor='“한국이민귀화적격시험 합격증”(KINAT) ･ (정규교육 과정 이수자) 졸업증명서, 검정고시 합격증, 재학증명서 등'), item('f5_c_f53_school', 'ALTERNATIVE_DOCUMENT', anchor='(정규교육 과정 이수자) 졸업증명서, 검정고시 합격증, 재학증명서 등')),
               item('f5_c_f52_other', 'MAY_BE_REQUESTED_BY_OFFICER', anchor='(정규교육 과정 이수자) 졸업증명서, 검정고시 합격증, 재학증명서 등 그 밖에 심사에 필요하다고 청장 등이 인정한 서류 등')],
         conditions_ko=['기본소양 요건: 취학 의무 연령 미만은 면제, 취학 의무 연령 이상~15세 미만은 「초·중등교육법」 학교(외국인학교 제외) 재학 시 면제 가능, 15세 이상은 해당 학교 졸업·졸업학력 검정고시 합격·2년 이상 재학 중 하나에 해당하면 면제 가능'],
         conditions_en=['Basic knowledge: waived below compulsory school age; from compulsory school age to under 15, may be waived if enrolled in a school under the Elementary and Secondary Education Act (not a foreign school); 15+, may be waived if graduated, passed the equivalency exam, or enrolled 2+ years in such a school'],
         notes_ko=[OFFICER_NOTE_KO], notes_en=[OFFICER_NOTE_EN])

# --------------------------------------------------------------------------
# F-5-6 / F-5-7 / F-5-14 — 외국국적동포 영주(F-5) 자격 부여 세부절차 (stay manual compatriot handbook)
# --------------------------------------------------------------------------
DONGPO_F5_SEC = '알기쉬운 외국국적동포 업무 매뉴얼 — 5. 외국국적동포 영주자격(F-5) 부여 세부절차 나. 부여 대상 및 신청서류'
DONGPO_CRIME = '□ 해외범죄 경력 확인서 제출(공통) ○ 해외 범죄경력증명서 세부 제출기준 참조  <별첨 1>'
guidance('F-5-6', 'status_change', completeness='PARTIALLY_STRUCTURED', section=DONGPO_F5_SEC + ' (F-5-6)', anchor=DONGPO_CRIME, doc_page_window=3,
         summary_ko='재외동포(F-4) 자격으로 2년 이상 계속 체류한 사람(F-5-6)은 소득(GNI 이상), 해외 연금(60세 이상), 재산, 국내 기업과의 교역실적(20억 원 이상), 미화 50만 불 이상 투자, 동포단체·법인 대표로서 재외공관장 추천 중 하나의 요건을 갖추어 신청하며, 해외범죄 경력 확인서와 해당 요건의 입증서류를 냅니다.',
         summary_en='People who have stayed 2+ years on F-4 (F-5-6) apply by meeting one of: income of GNI or more, an overseas pension (60+), assets, annual trade of KRW 2 billion+ with Korean companies, an investment of USD 500,000+, or a mission-head recommendation as head of a compatriot organisation or company. Submit an overseas criminal record certificate and proof for the requirement you meet.',
         docs=[item('f5_c_dongpo_crime', anchor=DONGPO_CRIME),
               item('f5_c_f56_income', 'CONDITIONAL_REQUIRED', anchor='• 소득금액 증명', applies_when_ko='연간 소득이 전년도 1인당 GNI 이상인 경우', applies_when_en='Annual income of at least GNI per capita'),
               item('f5_c_f56_pension', 'CONDITIONAL_REQUIRED', anchor='• 연금증서(사본) 및 연금입금통장', applies_when_ko='해외 연금을 받는 60세 이상으로 연간 연금액이 GNI 이상인 경우', applies_when_en='Aged 60+ with an overseas pension of at least GNI per capita'),
               item('f5_c_f56_assets', 'CONDITIONAL_REQUIRED', anchor='재산세 납세내역증명', applies_when_ko='전년도 재산세 50만 원 이상 납부 또는 본인명의 순자산이 평균순자산 이상인 경우', applies_when_en='Property tax of KRW 500,000+ last year, or net assets in your name at or above the average'),
               item('f5_c_f56_trade', 'CONDITIONAL_REQUIRED', anchor='수출입 실적 증명서(선하증권 또는 송장 등), 연간 납세 증명서', applies_when_ko='대한민국 기업과의 연간 교역실적이 20억 원 이상인 경우', applies_when_en='Annual trade of KRW 2 billion+ with Korean companies'),
               item('f5_c_f56_investment', 'CONDITIONAL_REQUIRED', anchor='외국인투자기업증명서 등 국내투자 증빙자료', applies_when_ko='대한민국에 미화 50만 불 이상을 투자한 경우', applies_when_en='Investment of USD 500,000+ in Korea'),
               item('f5_c_f56_mission_recommendation', 'CONDITIONAL_REQUIRED', anchor='• 재외공관장 추천서', applies_when_ko='거주국 정부가 공인한 동포단체 대표 또는 법인기업체 대표로서 재외공관장이 추천한 경우', applies_when_en='Head of a government-recognised compatriot organisation or of a company, recommended by the mission head')],
         conditions_ko=['국내 거소신고를 한 경우 국외에서 거주한 기간도 2년 이상 계속 체류기간에 포함됩니다.', '동거가족과 소득을 합산하는 경우 신청인의 소득이 기준액의 50% 이상이어야 합니다.'],
         conditions_en=['If you filed a domestic residence report, time living abroad counts toward the 2 years.', 'When income is combined with cohabiting family, your own income must be at least 50% of the threshold.'],
         notes_ko=['신청서 등 기본 서류는 매뉴얼의 이 부분에 따로 적혀 있지 않습니다.', OFFICER_NOTE_KO], notes_en=['This part of the manual does not separately list the basic application documents.', OFFICER_NOTE_EN])

guidance('F-5-7', 'status_change', completeness='PARTIALLY_STRUCTURED', section=DONGPO_F5_SEC + ' (F-5-7)',
         anchor='「재외동포의 출입국과 법적지위에 관한 법률」제2조제2호의 외국국적동포로 「국적법」에 따른 국적취득요건을 갖춘 사람(F-5-7)', doc_page_window=3,
         summary_ko='「국적법」에 따른 국적취득요건을 갖춘 외국국적동포(F-5-7)는 공통 제출서류(신청서, 여권 및 본국 신분증 사본 등 동포 입증서류, 외국인등록증(거소신고증), 사회통합프로그램·영주적격시험 서류, 생계유지능력 입증서류)에 일반귀화·간이귀화·특별귀화·국적회복 등 해당 유형별 추가서류를 더해 냅니다.',
         summary_en='Ethnic Koreans of foreign nationality who meet the nationality-acquisition requirements of the Nationality Act (F-5-7) submit the common documents (application, passport and home-country ID copy proving Korean ethnicity, residence card, social-integration or KIPRAT document, proof of livelihood) plus the additional documents for their type (general, simplified or special naturalisation, nationality restoration).',
         docs=[item('f5_c_dongpo_crime', anchor=DONGPO_CRIME),
               item('app_form', anchor='공통 제출서류 ○ 신청서 ○ 여권 및 본국 신분증 사본(원본 제시) 등 외국국적동포 입증서류'),
               item('f5_c_f57_passport_id', anchor='○ 여권 및 본국 신분증 사본(원본 제시) 등 외국국적동포 입증서류'),
               item('f5_c_f57_arc', anchor='○ 외국인등록증(거소신고증)'),
               item('f5_c_f57_kiip', 'CONDITIONAL_REQUIRED', anchor='○ 사회통합프로그램 한국이민영주적격과정이수증 또는 한국이민영주적격시험 합격증', applies_when_ko='국적회복·특별귀화 대상자가 아닌 경우', applies_when_en='Unless you are a nationality-restoration or special-naturalisation case'),
               item('f5_c_f57_livelihood', 'CONDITIONAL_REQUIRED', anchor='○ 생계유지능력 입증서류  (국적회복, 특별귀화대상자는 제출면제)', applies_when_ko='국적회복·특별귀화 대상자가 아닌 경우', applies_when_en='Unless you are a nationality-restoration or special-naturalisation case')],
         conditions_ko=['일반귀화(국적법 제5조), 간이귀화(제6조제1항제1호·제6조제2항), 특별귀화(제7조제1항제1호), 국적회복(제9조제1항) 대상자별로 가족관계·친자관계·친척관계 입증 등 추가서류가 정해져 있습니다.',
                        '영주(F-5-7) 신청자가 가족 동거를 희망하면 신청자가 재외동포(F-4)로 자격 변경한 후 가족에게 동반(F-3) 자격이 부여됩니다.'],
         conditions_en=['Additional documents (proof of family, parentage or kinship, etc.) are set for each type: general naturalisation (Art. 5), simplified (Art. 6(1)1, 6(2)), special (Art. 7(1)1) and nationality restoration (Art. 9(1)).',
                        'If an F-5-7 applicant wants family to live with them, the applicant changes to F-4 first and the family is granted F-3.'],
         notes_ko=[OFFICER_NOTE_KO], notes_en=[OFFICER_NOTE_EN])

guidance('F-5-14', 'status_change', completeness='PARTIALLY_STRUCTURED', section=DONGPO_F5_SEC + ' (F-5-14)',
         anchor=DONGPO_CRIME, doc_page_window=3,
         summary_ko='방문취업(H-2) 자격으로 제조업·농축산업·어업·간병인·가사보조인으로 동일업체에서 4년 이상 계속 근무하고, 기술·기능 자격을 취득했거나 연간 소득이 전년도 1인당 GNI 70% 이상(본인 소득만)인 사람(F-5-14)이 대상입니다. 이 부분에는 공통인 해외범죄 경력 확인서 외 개별 서류가 따로 적혀 있지 않습니다.',
         summary_en='F-5-14 is for H-2 workers in manufacturing, agriculture/livestock, fishing, caregiving or domestic help who have worked 4+ years continuously at the same company and hold a technical qualification or earn at least 70% of GNI per capita (own income only). Apart from the common overseas criminal record, this part lists no separate documents.',
         docs=[item('f5_c_dongpo_crime', anchor=DONGPO_CRIME)],
         conditions_ko=['임금체불·휴폐업 등 불가피한 사유로 3개월 이내 동일 업종으로 근무처를 변경한 경우 계속 취업으로 인정합니다.', '재외동포(F-4) 자격 변경자도 포함됩니다.'],
         conditions_en=['A change to the same industry within 3 months for unavoidable reasons (unpaid wages, closure) still counts as continuous work.', 'People who changed to F-4 are included.'],
         notes_ko=[OFFICER_NOTE_KO], notes_en=[OFFICER_NOTE_EN])

# --------------------------------------------------------------------------
# F-5-T / F-5-T1 — 톱티어 비자 (stay manual); F-5-S1 — K-STAR 영주 (stay manual)
# --------------------------------------------------------------------------
F5T_COMMON = '① 공통서류(신청서, 표준규격 사진, 여권 사본, 체류지 입증서류, 수수료 등) ② 고용계약서, 재직증명서, 소득입증서류(소득금액증명원 등)'
guidance('F-5-T', 'status_change', section='톱티어 비자 — 톱티어 영주 (F-5-T) □ 체류 관리 ❍ 체류자격 변경',
         anchor='톱티어 거주(F-2-T) 자격으로 3년 이상 체류하며', doc_page_window=1,
         summary_ko='톱티어 거주(F-2-T) 자격으로 3년 이상 체류하며 첨단산업 분야(산업통상부 추천형) 또는 과학기술 분야(과기정통부 추천형)에 종사하고 연간 근로소득이 1인당 GNI 3배 이상이고 사회통합프로그램 3단계 이상을 이수한 사람은 톱티어 영주(F-5-T)로 변경할 수 있습니다. 공통서류, 고용계약서·재직증명서·소득입증서류, 사업자등록증 등, 한국어 능력 입증서류, 해외 범죄경력증명서를 냅니다.',
         summary_en='People who have stayed 3+ years on F-2-T working in a high-tech industry field (MOTIE-recommended track) or a science and technology field (MSIT-recommended track), earn at least 3x GNI per capita and completed level 3+ of the social integration program can change to F-5-T. Submit the common documents, employment contract, employment certificate and income proof, business registration etc., proof of Korean ability and an overseas criminal record.',
         docs=[item('f5_c_tt_common', anchor=F5T_COMMON),
               item('f5_c_f5t_employment', anchor=F5T_COMMON),
               item('f5_c_f5t_biz_reg', 'CONDITIONAL_REQUIRED', anchor='종사(창업도 인정) 여부 확인 ④ 한국어 능력 입증서류', applies_when_ko='기존과 근무처가 변경된 경우', applies_when_en='If your workplace has changed'),
               item('f5_c_f5t_korean', anchor='④ 한국어 능력 입증서류 ※ 사회통합프로그램 3단계 이상 또는 한국어능력시험(TOPIK) 3단계 이상'),
               item('overseas_criminal_record', anchor='④ 한국어 능력 입증서류 ※ 사회통합프로그램 3단계 이상 또는 한국어능력시험(TOPIK) 3단계 이상 ⑤ 해외 범죄경력증명서')],
         notes_ko=[OFFICER_NOTE_KO], notes_en=[OFFICER_NOTE_EN])

F5T1_DOCS = '① 공통서류(신청서, 표준규격 사진, 여권 사본, 체류지 입증서류, 수수료 등) ② 주 자격자의 여권 사본 및 외국인등록증 ③ 본국 정부 발급 가족관계 입증서류'
guidance('F-5-T1', 'status_change', section='톱티어 비자 — □ 동반가족(배우자·미성년자녀)의 영주 (F-5-T1) ❍ 사증발급·자격변경',
         anchor='동반가족(배우자·미성년자녀)의 영주 (F-5-T1)', doc_page_window=1,
         summary_ko='톱티어 동반 거주(F-2-T1)로 국내에 3년 이상 체류했거나, 톱티어가 영주자격(F-5-T)을 취득한 뒤 동반가족으로 입국해 F-2-T1로 2년 이상 체류한 배우자·미성년 자녀는 톱티어 동반 영주(F-5-T1)로 변경할 수 있습니다. 공통서류, 주 자격자의 여권 사본·외국인등록증, 본국 가족관계 입증서류, 해외 범죄경력증명서를 냅니다.',
         summary_en='Spouses and minor children who have stayed 3+ years on F-2-T1, or 2+ years on F-2-T1 after entering once the principal obtained F-5-T, can change to F-5-T1. Submit the common documents, the principal\'s passport copy and residence card, home-country family-relation proof and an overseas criminal record.',
         docs=[item('f5_c_tt_common', anchor=F5T1_DOCS),
               item('f5_c_f5t1_principal', anchor=F5T1_DOCS, role='principal_holder'),
               item('f5_c_f5t1_family', anchor=F5T1_DOCS),
               item('overseas_criminal_record', anchor='※ 해외 발급 서류는 아포스티유 첨부 또는 대한민국 재외공관 영사확인 필요 ④ 해외 범죄경력증명서 - (체류자격) 톱티어 동반 영주(F-5-T1) 자격 부여')],
         conditions_ko=['해외 발급 서류는 아포스티유 첨부 또는 대한민국 재외공관 영사확인이 필요합니다.', '체류허가 제한 대상 해당 여부, 품행 단정 요건 및 법무부장관이 정하는 요건 충족 여부 등을 종합적으로 심사합니다.'],
         conditions_en=['Documents issued abroad need an apostille or consular confirmation by a Korean mission.', 'The review considers restrictions on stay permission, good conduct and the Minister\'s requirements as a whole.'],
         notes_ko=[OFFICER_NOTE_KO], notes_en=[OFFICER_NOTE_EN])

guidance('F-5-S1', 'status_change', section='K-STAR 비자트랙 — Ⅲ. K-STAR 영주(F-5-S1) 4. 제출서류',
         anchor='법무부장관 선정한 대학의 과학기술분야 석·박사 학위 소지자로서', doc_page_window=4,
         summary_ko='법무부장관이 선정한 대학의 과학기술분야 석·박사 학위 소지자로서 K-STAR 거주(F-2-7S) 또는 점수제 우수인재 거주(F-2-7)로 3년 이상 계속 체류하고 점수제 요건(90/200점)을 충족한 사람은 K-STAR 영주(F-5-S1)로 변경할 수 있습니다. 기본서류와 점수표, 항목별 점수 입증서류를 냅니다.',
         summary_en='Holders of a science or technology master\'s or doctorate from a university selected by the Minister who have stayed 3+ years on F-2-7S or F-2-7 and meet the points requirement (90/200) can change to F-5-S1. Submit the basic documents, the points table and proof for each item.',
         docs=[item('f5_c_f5s1_basic', anchor='(기본서류) 신청서, 여권, 외국인등록증, 수수료(수입인지), 체류지 입증서류, 해외범죄경력증명서, 신원보증서'),
               item('f5_c_f5s1_points_table', anchor='신청인이 해당하는 점수를 기재한 점수표【붙임 6】'),
               item('f5_c_f5s1_points_proof', anchor='신청인이 기재한 평가 항목별 점수를 입증하는 서류【붙임 7】')],
         conditions_ko=['생계유지능력 및 기본소양 요건은 K-STAR 영주 점수제의 한국어능력·연간 소득 항목 심사로 대체합니다.', '품행단정 결격사유에 해당하면 원칙적으로 영주자격으로 자격변경이 불가합니다.'],
         conditions_en=['The livelihood and basic-knowledge requirements are replaced by the Korean-ability and annual-income items of the K-STAR points system.', 'If you fall under a good-conduct disqualification, the change to permanent residence is in principle not allowed.'],
         notes_ko=[OFFICER_NOTE_KO], notes_en=[OFFICER_NOTE_EN])
