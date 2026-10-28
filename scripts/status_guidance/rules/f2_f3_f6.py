# F-2 거주 / F-3 동반 / F-6 결혼이민 — transcribed from the 2026-10-19 manuals.
# Stay rules: 외국인체류 안내매뉴얼 거주(F-2) pp. 367–427, 동반(F-3) pp. 428–432, 결혼이민(F-6) pp. 484–507.
# Visa rules: 사증발급 안내매뉴얼 거주(F-2) p. 311–, 동반(F-3) p. 316–, 결혼이민(F-6) p. 327–.
# Runs inside author_rules.py (guidance, item, docdefs, residence, base_stay, VISA, STAY …).
# Only cells that had no rule are filled; existing F-2/F-3/F-6 extension and registration rules are untouched.
# Subcode chapters that live outside these sections (지역특화형비자 ch. 37, 톱티어 ch. 39) are not transcribed here.

docdefs(
    # visa forms
    f236_visa_form17=('사증발급신청서 (별지 제17호 서식)', 'Visa application form (Form 17)', 'applicant', None),
    f236_cvi_form21=('사증발급인정신청서 (별지 제21호 서식)', 'Application for a confirmation of visa issuance (Form 21)', 'inviter', None),
    # F-2-3 (spouse of a permanent resident)
    f236_spouse_guarantor=('국내 배우자의 신원보증서', 'Letter of guarantee from the spouse in Korea', 'principal_holder', None),
    f236_invitation=('초청장', 'Letter of invitation', 'inviter', None),
    f236_invitation_background=('초청장(붙임1 양식), 혼인배경 진술서(붙임2 양식)', 'Letter of invitation (annex 1 form) and marriage-background statement (annex 2 form)', 'inviter', None),
    f236_marriage_background=('혼인배경 진술서', 'Marriage-background statement', 'applicant', None),
    f236_marriage_proof_both=('양국간 혼인관계 입증서류(결혼증명서, 가족관계 기록에 관한 증명서)', 'Proof of the marriage in both countries (marriage certificate, family-relation record)', 'applicant', None),
    f236_marriage_proof_parties=('초청인 및 피초청인 양국 간 혼인관계 입증서류(결혼증명서, 가족관계 기록에 관한 증명서 등)', 'Proof of the marriage between inviter and invitee in both countries (marriage certificate, family-relation record, etc.)', 'applicant', None),
    f236_finance_income=('재정(소득) 입증관련 서류(재직증명서, 부동산 등기부등본, 예금잔고증명서 등)', 'Financial (income) documents (employment certificate, property register, bank balance certificate, etc.)', 'principal_holder', None),
    f236_finance_income_visa=('재정(소득) 입증서류(소득금액증명원, 재직증명서, 계좌거래내역 등)', 'Financial (income) documents (income certificate, employment certificate, account statements, etc.)', 'inviter', None),
    f236_spouse_guarantor_courtship=('국내 배우자의 신원보증서, 교제경위서 등', 'Guarantee from the spouse in Korea, account of how the couple met, etc.', 'principal_holder', None),
    f236_spouse_credit_report=('국내 배우자의 신용정보조회서(전국은행연합회 발행)', 'Credit report of the spouse in Korea (Korea Federation of Banks)', 'principal_holder', None),
    f236_inviter_credit_report=('초청인의 신용정보조회서(전국은행연합회 발행)', "Inviter's credit report (Korea Federation of Banks)", 'inviter', None),
    f236_crime_record_both=('혼인당사자 쌍방의 범죄경력에 관한 증명서(국적국 또는 거주국 관할 기관 발급)', 'Criminal record certificates of both spouses (issued by the country of nationality or residence)', 'applicant', None),
    f236_crime_record_parties=('초청인 및 피초청인 쌍방의 범죄경력에 관한 증명서(국적국 또는 거주국 관할 기관 발급)', 'Criminal record certificates of both inviter and invitee (issued by the country of nationality or residence)', 'applicant', None),
    f236_health_both=('혼인당사자 쌍방의 건강진단서', 'Health certificates of both spouses', 'applicant', None),
    f236_health_parties=('초청인 및 피초청인 쌍방의 건강진단서', 'Health certificates of both inviter and invitee', 'applicant', None),
    f236_prior_marriage_dissolution=('과거 혼인기록이 있는 경우 혼인 해소 여부를 입증할 수 있는 서류(이혼증 등)', 'Proof that any earlier marriage ended (divorce certificate, etc.)', 'applicant', None),
    f236_family_proof_birth=('가족관계 입증 서류(출생증명서, 결혼증명서, 호구부 등)', 'Proof of family relationship (birth certificate, marriage certificate, hukou, etc.)', 'applicant', None),
    # F-2-2 (minor child of a Korean national)
    f236_minor_child_proof=('국민의 미성년 자녀임을 입증할 수 있는 공적 서류', 'Official proof of being the minor child of a Korean national', 'applicant', None),
    f236_custody_relation_visa=('대한민국 국민과 해당 미성년자의 관계 및 양육권 보유관계를 입증할 수 있는 서류', 'Proof of the relationship to the Korean parent and of custody', 'applicant', None),
    f236_custodial_parent_guarantor=('양육권을 가진 대한민국국민인 부 또는 모의 신원보증서(그 부 또는 모가 배우자가 있을 경우 그 배우자의 신원보증서도 필요)', "Guarantee from the Korean parent with custody (and from that parent's spouse, if any)", 'inviter', None),
    f236_guardian_consent=('친권자 또는 후견인의 동의서(양육권 보유관계를 입증할 수 없을 경우)', 'Consent of the person with parental authority or the guardian (if custody cannot be proven)', 'other_third_party', None),
    f236_parentage_proof=('국민과 해당 미성년자와의 관계입증 서류(유전자 검사확인서류 또는 출생증명서 등)', 'Proof of parentage with the Korean national (DNA test result, birth certificate, etc.)', 'applicant', None),
    f236_korean_parent_guarantor=('대한민국 국민인 부 또는 모의 신원보증서', 'Guarantee from the Korean parent', 'inviter', None),
    f236_custody_proof_stay=('대한민국 국민과 해당 미성년자와의 관계 및 양육권 보유관계를 입증할 수 있는 서류(이혼판결문 등)', 'Proof of the relationship to the Korean parent and of custody (divorce judgment, etc.)', 'applicant', None),
    f236_foreign_child_proof=('국민의 외국인 자녀임을 입증할 수 있는 서류(출생증명서, 호구부 등)', 'Proof of being the foreign child of a Korean national (birth certificate, hukou, etc.)', 'applicant', None),
    f236_child_hukou_id=('자녀의 호구부 및 거민신분증', "Child's hukou and resident identity card", 'applicant', None),
    f236_parent_certs=('부모의 기본증명서, 가족관계증명서, 주민등록등본', "Parents' basic certificate, family-relation certificate and resident registration", 'inviter', None),
    f236_custodial_guarantor=('신원보증서(양육권을 가진 부 또는 모)', 'Letter of guarantee (from the parent with custody)', 'inviter', None),
    # F-2-4 / F-2-5
    f236_refugee_cert=('난민인정증명서', 'Refugee recognition certificate', 'applicant', None),
    f236_dispatch_or_income=('파견명령서 또는 재직증명서 또는 소득금액증명원(3년간)', 'Dispatch order, employment certificate or income certificates (3 years)', 'applicant', None),
    f236_fdi_report_or_reg=('외국인 투자신고서 또는 투자기업등록증 사본', 'Foreign-investment report or copy of the investment-company registration', 'applicant', None),
    f236_employee_contract_or_income=('피고용인에 대한 고용계약서 또는 소득금액증명원', 'Employment contracts or income certificates of the Korean employees', 'applicant', None),
    # F-2-7 family
    f236_principal_arc_if_registered=('외국인등록증(주체류자가 외국인등록을 마친 사람만 해당)', 'Residence card (only if the principal holder has registered)', 'principal_holder', None),
    f236_applicant_employment_docs=('신청자의 고용계약서, 재직증명서, 사업자등록증, 법인등기부등본, 소득금액증명, 학위취득(예정)증명서, 졸업(예정)증명서 등(해당자)', "Applicant's employment contract, employment certificate, business registration, corporate register, income certificate, degree or graduation (expected) certificate, etc. (as applicable)", 'applicant', None),
    f236_principal_employment_docs=('주체류자의 고용계약서, 재직증명서, 사업자등록증, 법인등기부등본, 소득금액증명, 학위취득(예정)증명서, 졸업(예정)증명서 등(해당자)', "Principal holder's employment contract, employment certificate, business registration, corporate register, income certificate, degree or graduation (expected) certificate, etc. (as applicable)", 'principal_holder', None),
    f236_principal_employment_docs_copy=('주체류자의 고용계약서 사본, 재직증명서, 사업자등록증, 법인등기부등본, 소득금액증명, 학위취득(예정)증명서, 졸업(예정)증명서 등(해당자)', "Copy of the principal holder's employment contract, employment certificate, business registration, corporate register, income certificate, degree or graduation (expected) certificate, etc. (as applicable)", 'principal_holder', None),
    f236_family_relation_principal=('가족관계 소명 서류(주체류자와의 법률상 가족관계 입증서류여야 함)', 'Proof of the legal family relationship with the principal holder', 'applicant', None),
    f236_points_table=('점수제 평가를 위한 점수를 기재한 점수표', 'Points table filled in for the points evaluation', 'applicant', None),
    f236_points_table_self=('신청인이 해당하는 점수를 기재한 점수표', 'Points table filled in by the applicant', 'applicant', None),
    f236_points_proof=('신청인이 기재한 평가 항목별 점수를 입증하는 서류', 'Evidence for each points item claimed', 'applicant', None),
    f236_points_proof_self=('신청인 본인이 기재한 평가 항목별 점수를 소명하는 서류', 'Evidence for each points item the applicant claimed', 'applicant', None),
    f236_points_extra=('추가서류: 가족관계 소명 서류(출생증명서 포함), 결핵검진 확인서, 학위취득(예정)증명서 또는 졸업(예정)증명서, 이공계 특성화 대학 총장 추천서, 재직증명서, 사업자등록증, 법인등기부등본, 소득금액증명 등(해당자)', 'Additional documents as applicable: family-relation proof (incl. birth certificate), TB check, degree or graduation (expected) certificate, recommendation from the president of a specialised science university, employment certificate, business registration, corporate register, income certificate, etc.', 'applicant', None),
    f236_examiner_requested=('심사관이 추가 제출을 요구한 서류', 'Documents the examiner asks for', 'applicant', None),
    f236_birth_cert=('출생증명서', 'Birth certificate', 'applicant', None),
    f236_same_as_change=('체류자격 변경 심사 서류와 동일', 'Same documents as for the change-of-status review', 'applicant', None),
    # F-2-8 / F-2-12 investors
    f236_arc_if_any=('외국인등록증(해당자)', 'Residence card (if held)', 'applicant', None),
    f236_property_contract_register=('부동산 매매계약서, 부동산 등기부등본(F-2 대상자에 한함)', 'Property sale contract and property register (F-2 applicants only)', 'applicant', None),
    f236_condo_membership=('분양회사가 (사)한국휴양콘도미니엄경영협회에서 확인받아 발급한 회원증서, 분양회사 발행 회원확인서 및 입금영수증(회원인 경우에 한함)', 'Membership certificate confirmed by the Korea Condominium Association, membership confirmation and payment receipt from the developer (members only)', 'applicant', None),
    f236_unsold_vacancy=('미분양주택 공실 확인서(미분양주택 투자자에 한함)', 'Vacancy confirmation for an unsold house (unsold-house investors only)', 'applicant', None),
    f236_move_in_list=('해당주택 전입세대 열람내역(미분양주택 투자자에 한함, 읍․면․동장 발행, 발급일로부터 5일 이내인 경우만 유효)', 'Record of households registered at the house (unsold-house investors only; issued by the eup/myeon/dong head, valid 5 days)', 'applicant', None),
    f236_fx_inflow_proof=('외환반입 관련 입증서류(국내 외국환은행에서 발급한 외화송금 전신문, 외국환매입증명서 등)', 'Proof of bringing in foreign currency (remittance telex, foreign-exchange purchase certificate from a Korean bank, etc.)', 'applicant', None),
    f236_fx_inflow_proof_public=('외화반입 관련 입증서류(공익투자 전담은행에서 발행한 외화송금 전신문, 외국환매입증명서 등)', 'Proof of bringing in foreign currency (remittance telex, foreign-exchange purchase certificate from the designated bank, etc.)', 'applicant', None),
    f236_overseas_remit_corp=('국외에서 해당 투자자 명의로 법인에 투자금을 송금 또는 지불하였음을 입증하는 서류(법인을 통해 투자한 경우에 한함)', "Proof that the investment was remitted or paid to the company from abroad in the investor's name (investment through a company only)", 'applicant', None),
    f236_corp_officer_proof=('투자한 법인의 현직 임원 또는 과점주주임을 입증하는 서류 및 당사자 명단이 명시된 해당 법인의 공문(법인의 임원 또는 주주 해당자에 한함)', "Proof of being a current officer or majority shareholder of the investing company and the company's official letter naming them (officers or shareholders only)", 'business_entity', None),
    f236_family_cert_dependants=('가족관계 증명서(배우자·미혼 자녀의 송금 또는 자격변경 신청에 한함)', 'Family-relation certificate (only when the spouse or unmarried child remits or applies)', 'applicant', None),
    f236_overseas_crime_6m=('국적국 또는 거주국의 해외범죄경력증명서(신청일로부터 6개월 이내 발급)', 'Criminal record certificate from the country of nationality or residence (issued within 6 months)', 'applicant', None),
    f236_investment_payment_proof=('투자금 납입 증명 서류(투자 유치기관 장의 직인이 날인된 투자확인서, 계좌이체 내역서 등)', 'Proof of paying in the investment (investment confirmation sealed by the head of the receiving institution, transfer records, etc.)', 'applicant', None),
    f236_register_or_membership=('부동산 등기부등본 또는 분양회사 발행 회원확인서(신청일 기준 5일 이내 발급된 것일 것)', 'Property register or membership confirmation from the developer (issued within 5 days of applying)', 'applicant', None),
    f236_family_cert_extension=('가족관계 증명서(배우자 또는 미혼자녀의 체류기간 연장신청 시에 한함)', 'Family-relation certificate (only for the spouse or an unmarried child extending)', 'applicant', None),
    f236_corp_status_maintained=('법인의 임원, 주주의 경우 자격변경 당시의 법인 임원, 주주의 지위를 계속 유지하고 있음을 입증하는 서류(해당 법인명의 공문, 재직증명서, 주식지분 확인자료 등)', 'For company officers or shareholders: proof of keeping that position since the status change (company letter, employment certificate, shareholding records, etc.)', 'business_entity', None),
    f236_investment_maintained=('투자금을 유지하고 있음을 입증하는 서류(최근 5일 이내 발급한 투자금 유치기관 장의 직인이 날인된 확인서 등)', 'Proof that the investment is maintained (confirmation sealed by the head of the receiving institution, issued within the last 5 days, etc.)', 'applicant', None),
    f236_family_cert_companion=('가족관계증명서(동반가족의 경우)', 'Family-relation certificate (accompanying family members)', 'applicant', None),
    # F-2-16 / F-2-99 / F-2-6
    f236_special_contribution_proof=('특별 기여 입증서류(훈․포장 증서 추천서, 그외 증빙 서류 등)', 'Proof of the special contribution (decoration certificate, recommendation, other evidence)', 'applicant', None),
    f236_application_reason=('신청사유서(서식 1)', 'Statement of reasons for the application (form 1)', 'applicant', None),
    f236_livelihood_docs=('생계유지 능력 입증서류(자산: 예금잔고증명, 부동산임대차계약서, 부동산등기부등본 등 / 소득: 소득금액증명원 등 세무서 발급 소득 입증서류 / 기타: 연금수령입증 서류 등)', 'Proof of the ability to support yourself (assets: bank balance, lease, property register / income: tax-office income certificate / other: pension receipts, etc.)', 'applicant', None),
    f236_econ_activity_docs=('경제활동 지속 입증서류(취업자: 고용계약서, 재직증명서, 사업자등록증 등 / 사업자: 법인등기사항전부증명서, 투자기업등록증 등)', 'Proof of continuing economic activity (employees: contract, employment certificate, business registration / business owners: corporate register, investment-company registration)', 'applicant', None),
    f236_basic_knowledge=('한국어와 한국문화에 대한 기본소양 입증서류', 'Proof of basic knowledge of the Korean language and culture', 'applicant', None),
    f236_dwelling_proof=('부동산 임대차 계약서 등 체류지(주거지) 입증서류', 'Proof of residence (lease contract, etc.)', 'applicant', None),
    f236_deposit_2000=('최근 1년 이상 2천만 원 이상의 예금잔고가 유지되었음을 증명할 수 있는 서류 또는 2천만 원 이상에 해당하는 부동산등기부등본·부동산전세계약서 사본', 'Proof of a bank balance of KRW 20 million or more kept for at least a year, or a property register or jeonse contract copy worth KRW 20 million or more', 'applicant', None),
    f236_past_employment=('재직(경력)증명서 등 과거 취업활동 사실을 증명할 수 있는 서류', 'Employment (career) certificate or other proof of past employment', 'applicant', None),
    f236_future_employment=('취업예정사실증명서, 표준근로계약서 등 종전 체류자격에 해당하는 분야의 취업(예정) 사실을 증명할 수 있는 서류', 'Proof of current or planned employment in the field of the earlier status (employment confirmation, standard labour contract, etc.)', 'applicant', None),
    f236_nationality_acquisition_cert=('국적취득증명서', 'Certificate of nationality acquisition', 'applicant', None),
    # F-3
    f236_family_relation_mb=('가족관계입증서류(결혼 또는 출생증명서 등)', 'Proof of family relationship (marriage or birth certificate, etc.)', 'applicant', None),
    f236_livelihood_inviter=('생계유지능력 입증서류(초청자의 재직증명서 및 납세사실증명서 등)', "Proof of financial capacity (inviter's employment certificate and tax payment certificate, etc.)", 'inviter', None),
    f236_dwelling_residence=('체류지 등 주거지 입증서류', 'Proof of residence (dwelling)', 'inviter', None),
    f236_f4_card_or_visa=('재외동포(F-4) 자격을 취득한 사람의 국내거소신고증 또는 사증발급 사항 사본(여권사본 포함)', 'Domestic residence report card of the F-4 holder or a copy of their visa details (including passport copy)', 'principal_holder', None),
    f236_h2_card_or_visa=('방문취업(H-2) 자격을 취득한 사람의 외국인등록증 또는 사증발급 사항 사본(여권사본 포함)', 'Residence card of the H-2 holder or a copy of their visa details (including passport copy)', 'principal_holder', None),
    f236_parent_arc=('부 또는 모의 외국인등록증', "Parent's residence card", 'principal_holder', None),
    f236_principal_arc=('주자격자(배우자 또는 부모)의 외국인등록증', "Principal holder's (spouse's or parent's) residence card", 'principal_holder', None),
    f236_stay_finance=('체류경비 등 재정능력 입증서류', 'Proof of financial capacity for stay costs', 'applicant', None),
    f236_change_reason=('체류자격 변경 사유서 및 관련 증빙 서류', 'Statement of reasons for the status change and supporting evidence', 'applicant', None),
    f236_family_birth_hukou=('가족관계 입증서류 (출생증명서, 호구부 등)', 'Proof of family relationship (birth certificate, hukou, etc.)', 'applicant', None),
    f236_common_docs_f3=('공통서류(신청서, 표준규격 사진, 여권 사본, 체류지 입증서류, 수수료 등)', 'Common documents (application, standard photo, passport copy, proof of residence, fee, etc.)', 'applicant', None),
    f236_principal_passport_arc=('주 자격자의 여권 사본 및 외국인등록증', "Principal holder's passport copy and residence card", 'principal_holder', None),
    f236_principal_requirement_proof=('주 자격자의 자격변경 요건 충족 입증서류', 'Proof that the principal holder meets the status-change requirements', 'principal_holder', None),
    f236_home_family_proof=('본국 정부 발급 가족관계 입증서류(혼인관계 증명서, 가족관계 증명서)', 'Family-relation proof issued by the home government (marriage certificate, family-relation certificate)', 'applicant', None),
    f236_birth_family_proof=('출생증명서 등 가족관계 입증서류', 'Birth certificate or other proof of family relationship', 'applicant', None),
    f236_rule76_docs=('규칙 제76조에 의한 체류자격별 첨부서류(신원보증서 생략)', 'Status-specific documents under Enforcement Rule Art. 76 (no letter of guarantee)', 'applicant', None),
    f236_standard_contract=('표준근로계약서', 'Standard labour contract', 'employer', None),
    f236_bizreg_or_corpreg=('사업자등록증 또는 법인등기부등본', 'Business registration or corporate register', 'employer', None),
    f236_employer_id_copy=('고용주 신분증 사본', "Copy of the employer's ID", 'employer', None),
    f236_korean_topik2=('한국어능력 증빙서류(TOPIK 2급 또는 사회통합프로그램 2급 이상)', 'Korean-ability proof (TOPIK level 2 or social integration program level 2 or higher)', 'applicant', None),
    f236_early_adaptation_proof=('조기적응프로그램 이수 증빙서류 (해당 프로그램 마련 시 까지 면제)', 'Early-adaptation program completion proof (waived until the program exists)', 'applicant', None),
    f236_agency_recommendation=('추천서(해당 기관장)', 'Recommendation from the head of the institution', 'employer', None),
    f236_degree_orig_copy=('학위증(원본 및 사본)', 'Degree certificate (original and copy)', 'applicant', None),
    f236_degree_e2=('학위증(E-2 자격요건과 동일)', 'Degree certificate (same as the E-2 requirement)', 'applicant', None),
    f236_crime_record_e2=('범죄경력증명서(E-2 자격요건과 동일)', 'Criminal record certificate (same as the E-2 requirement)', 'applicant', None),
    f236_medical_e2=('채용신체검사서(E-2 자격요건과 동일)', 'Pre-employment medical check (same as the E-2 requirement)', 'applicant', None),
    f236_teacher_license=("해당국교원 자격증 원본(교원자격증이 없는 경우 '학위증 및 경력증명서')", "Original teaching licence of the country (if none, degree and career certificates)", 'applicant', None),
    f236_principal_request=('학교장 요청서', "School principal's request letter", 'educational_institution', None),
    f236_foreign_teacher_status=('외국인교사 현황', 'List of foreign teachers', 'educational_institution', None),
    f236_passport_orig_copy=('여권 원본 및 사본', 'Passport original and copy', 'applicant', None),
    # F-6
    f236_visa_app=('비자 신청서(사증발급 신청서)', 'Visa application form', 'applicant', None),
    f236_passport_photo=('여권용 사진 1매', 'One passport photo', 'applicant', None),
    f236_applicant_passport_orig=('신청인(외국인 배우자) 여권 원본', 'Original passport of the applicant (foreign spouse)', 'applicant', None),
    f236_applicant_passport_copy=('신청인 여권 사본 1부', "Copy of the applicant's passport", 'applicant', None),
    f236_visa_fee=('비자 신청 수수료', 'Visa application fee', 'applicant', None),
    f236_spouse_invitation=('외국인 배우자 초청장', 'Letter of invitation for the foreign spouse', 'korean_spouse', None),
    f236_marriage_background_stmt=('외국인 배우자의 결혼배경진술서', "Foreign spouse's marriage-background statement", 'applicant', None),
    f236_ksp_passport_copy=('한국인 배우자 여권 사본 1부', "Copy of the Korean spouse's passport", 'korean_spouse', None),
    f236_ksp_basic_detail=('한국인 배우자의 기본증명서(상세)', "Korean spouse's basic certificate (detailed)", 'korean_spouse', None),
    f236_ksp_family_detail=('한국인 배우자의 가족관계증명서(상세)', "Korean spouse's family-relation certificate (detailed)", 'korean_spouse', None),
    f236_ksp_resident_reg_orig=('한국인 배우자의 주민등록등본 원본', "Korean spouse's resident registration (original)", 'korean_spouse', None),
    f236_intl_marriage_program_cert=('국제결혼 안내프로그램 이수증', 'International-marriage guidance program certificate', 'korean_spouse', None),
    f236_ksp_health=('한국인 배우자의 건강진단서 원본', "Korean spouse's health certificate (original)", 'korean_spouse', None),
    f236_foreign_marriage_cert=('결혼증명서 원본(정식 명칭 병기)', 'Original marriage certificate (with its official name)', 'applicant', None),
    f236_foreign_crime_record=('외국인 배우자의 범죄경력증명서 원본(정식명칭 병기)', "Foreign spouse's criminal record certificate (original, with its official name)", 'applicant', None),
    f236_foreign_health=('외국인 배우자의 건강진단서 원본', "Foreign spouse's health certificate (original)", 'applicant', None),
    f236_country_specific=('해당 국가에 특별히 적용되는 서류', 'Documents required specifically for your country', 'applicant', None),
    f236_income_req_docs=('한국인 배우자의 소득요건 관련 서류', "Documents for the Korean spouse's income requirement", 'korean_spouse', None),
    f236_comm_req_docs=('외국인 배우자의 의사소통 요건 관련 서류', "Documents for the foreign spouse's communication requirement", 'applicant', None),
    f236_housing_req_docs=('한국인 배우자의 주거요건 관련 서류', "Documents for the Korean spouse's housing requirement", 'korean_spouse', None),
    f236_courtship_docs=('교제 입증 서류', 'Proof of the relationship (how the couple met and dated)', 'applicant', None),
    f236_parentage_docs_visa=('가족(친자)관계 입증서류(자녀의 기본증명서, 출생증명서, 유전자 검사 확인서류 등)', "Proof of parentage (child's basic certificate, birth certificate, DNA test result, etc.)", 'applicant', None),
    f236_childcare_proof_visa=('자녀양육을 입증할 수 있는 서류(양육권내용이 포함된 판결문 등, 자녀의 5촌 이내의 한국인 친척의 양육 입증 확인서 등)', "Proof of raising the child (judgment including custody, confirmation from a Korean relative within the fifth degree, etc.)", 'applicant', None),
    f236_crime_health=('범죄경력증명서 및 건강진단서', 'Criminal record certificate and health certificate', 'applicant', None),
    f236_parentage_birth_dna=('가족(친자)관계 입증서류(출생증명서, 유전자검사 확인 서류)', 'Proof of parentage (birth certificate, DNA test result)', 'applicant', None),
    f236_childcare_proof_stay=('자녀양육 입증서류(양육권 관련 판결문, 자녀가 등재되어 있는 주민등록등본, 자녀의 5촌 이내 한국인 친척이나 주거지 통(반)장의 확인서 등)', 'Proof of raising the child (custody judgment, resident registration listing the child, confirmation from a Korean relative within the fifth degree or the neighbourhood head, etc.)', 'applicant', None),
    f236_marriage_end_proof=('혼인단절자(이혼, 사망, 실종 등)의 경우 그 사유를 입증하는 서류(해당자에 한함)', 'Proof of why the marriage ended (divorce, death, disappearance, etc.; if applicable)', 'applicant', None),
    f236_divorce_suit=('이혼관련 소송서류(소장, 이혼 판결문 등)', 'Divorce litigation documents (complaint, divorce judgment, etc.)', 'applicant', None),
)

OFFICER_NOTE_VISA_KO = '재외공관의 장은 심사를 위해 필요한 경우 첨부서류를 일부 가감할 수 있습니다.'
OFFICER_NOTE_VISA_EN = 'The consul may add or waive some documents where the review requires it.'
CVI_NOTE_KO = '출입국·외국인청(사무소·출장소)장은 심사를 위해 첨부서류의 일부를 가감할 수 있으며, 사본을 제출할 때는 원본을 제시합니다.'
CVI_NOTE_EN = 'The immigration office may add or waive some documents; when you submit copies, show the originals.'
LAW_ABIDING_KO = '거주(F-2) 자격변경·연장 예정자 중 국내법 위반 사실이 확인되면 준법시민교육 대상이 됩니다(법위반 1회 이하이고 100만원 이하 벌금·범칙금·과태료 후 10년이 지난 사람 등은 제외).'
LAW_ABIDING_EXT_KO = '거주(F-2) 자격변경·연장 예정자 중 국내법 위반 사실이 확인되면 준법시민교육 대상이 됩니다(법위반 1회 이하이고 100만원 이하 벌금·범칙금·과태료를 받은 지 10년(자격변경) 또는 5년(연장)이 지난 사람은 제외). 최초 연장 때 대상이면 다음 연장 때까지 이수해야 합니다.'
LAW_ABIDING_EXT_EN = 'F-2 applicants with a confirmed violation of Korean law must take the law-abiding citizen course (exempt: one violation of KRW 1 million or less more than 10 years (change) or 5 years (extension) ago). If required at a first extension, complete it by the next extension.'
LAW_ABIDING_EN = 'Applicants for an F-2 change or extension with a confirmed violation of Korean law must take the law-abiding citizen course (exempt e.g. one violation of KRW 1 million or less more than 10 years ago).'


def f236_visa_base(anchor='① 사증발급신청서 (별지 제17호 서식), 여권, 표준규격사진 1매, 수수료'):
    return [item('f236_visa_form17', anchor=anchor), item('passport', anchor=anchor), item('photo', anchor=anchor), item('fee', anchor=anchor)]


def f236_stay_base(anchor, arc=False, photo=True, form='app_form_34', passport='passport'):
    docs = [item(form, anchor=anchor), item(passport, anchor=anchor)]
    if arc:
        docs.append(item('arc', anchor=anchor))
    if photo:
        docs.append(item('photo', anchor=anchor))
    docs.append(item('fee', anchor=anchor))
    return docs


# ==========================================================================
# F-2 거주 — 사증 (visa manual)
# ==========================================================================
F2_VISA_SEC = '사증발급 안내매뉴얼 거주(F-2) — 공관장 재량으로 발급할 수 있는 사증'

guidance('F-2-3', 'visa_issuance', manual=VISA, section=F2_VISA_SEC + ' 1. 영주(F-5) 자격 소지자의 배우자',
         anchor='영주(F-5) 자격 소지자의 배우자에 대한 체류기간 1년 이하의 거주(F-2-3) 단수사증',
         summary_ko='영주(F-5) 자격 소지자의 배우자는 재외공관에서 체류기간 1년 이하의 거주(F-2-3) 단수사증을 받을 수 있습니다. 국내 배우자의 신원보증서, 초청장·혼인배경 진술서, 양국 혼인관계 입증서류, 재정 서류, 초청인 신용정보조회서, 쌍방의 범죄경력증명서와 건강진단서를 냅니다.',
         summary_en='Spouses of permanent residents (F-5) can get a single-entry F-2-3 visa for a stay of up to one year at a Korean mission. Submit the guarantee from the spouse in Korea, the invitation and marriage-background statement, proof of the marriage in both countries, financial documents, the inviter\'s credit report, and both parties\' criminal record and health certificates.',
         docs=f236_visa_base() + [
             item('f236_spouse_guarantor', anchor='② 국내 배우자의 신원보증서'),
             item('f236_invitation_background', anchor='③ 초청장(붙임1 양식), 혼인배경 진술서(붙임2 양식)'),
             item('f236_marriage_proof_parties', anchor='④ 초청인 및 피초청인 양국 간 혼인관계 입증서류'),
             item('f236_finance_income_visa', anchor='⑤ 재정(소득) 입증서류'),
             item('f236_inviter_credit_report', anchor='⑥ 초청인의 신용정보조회서(전국은행연합회 발행)'),
             item('f236_crime_record_parties', anchor='국적국 또는 거주국의 관할 기관이 발급한 초청인 및 피초청인 쌍방의',
                  notes_ko=['영주(F-5) 자격 소지자 본인이 영주자격 변경 때 이미 냈다면 본인 것은 생략할 수 있으나, 그 뒤 해외에서 6개월 이상 체류했다면 그 기간 체류국 정부가 발행한 증명서를 냅니다.'],
                  notes_en=['The F-5 holder may skip their own certificate if it was filed for the F-5 change, unless they have since stayed abroad 6 months or more; then a certificate from that country is needed.']),
             item('f236_health_parties', anchor='⑧ 초청인 및 피초청인 쌍방의 건강진단서',
                  notes_ko=['병원급 의료기관이나 보건소가 발행한 것이어야 하며, 피초청인은 국적국 또는 거주국에서 통용되는 유사한 입증자료로 갈음할 수 있습니다.'],
                  notes_en=['Must be issued by a hospital-level institution or public health centre; the invitee may use an equivalent document accepted in their country.']),
             item('f236_prior_marriage_dissolution', 'CONDITIONAL_REQUIRED', anchor='⑨ 과거 혼인기록이 있는 경우 혼인 해소 여부를 입증할 수 있는 서류',
                  applies_when_ko='과거 혼인기록이 있는 경우', applies_when_en='If either party was married before'),
         ],
         conditions_ko=['난민인정자, 고액투자자, 영주자격 상실자, 7년 이상 장기체류자는 체류자격 부여 또는 변경 대상이므로 재외공관에서 거주(F-2) 사증을 발급하지 않습니다.'],
         conditions_en=['Recognised refugees, high-value investors, people who lost F-5 status and long-term residents of 7+ years are handled by status grant or change in Korea, so missions do not issue them an F-2 visa.'],
         notes_ko=[OFFICER_NOTE_VISA_KO], notes_en=[OFFICER_NOTE_VISA_EN])

guidance('F-2-2', 'visa_issuance', manual=VISA, section=F2_VISA_SEC + ' 2.·3. 국민의 미성년 외국인 자녀 / 국민과 혼인관계에서 출생한 자녀',
         anchor='국민의 미성년 외국인자녀에 대한 체류기간 90일 이하의 거주(F-2-2) 단수사증',
         summary_ko='국민의 미성년 외국인 자녀는 체류기간 90일 이하의 거주(F-2-2) 단수사증을, 국민과 혼인관계(사실혼 포함)에서 출생한 자녀는 5년간 유효한 체류기간 1년 이하의 거주(F-2-2) 복수사증을 받을 수 있습니다. 경우에 따라 관계·양육권 입증서류 또는 초청장·친자관계 입증서류와 부 또는 모의 신원보증서를 냅니다.',
         summary_en='A foreign minor child of a Korean national can get a single-entry F-2-2 visa for up to 90 days; a child born in a marriage (including de facto) with a Korean national can get a five-year multiple-entry F-2-2 visa for stays of up to one year. Depending on the case, submit proof of relationship and custody, or an invitation and proof of parentage, with the Korean parent\'s guarantee.',
         docs=f236_visa_base() + [
             item('f236_minor_child_proof', 'CONDITIONAL_REQUIRED', anchor='② 국민의 미성년 자녀임을 입증할 수 있는 공적 서류',
                  applies_when_ko='국민의 미성년 외국인 자녀(90일 이하 단수사증)', applies_when_en='Foreign minor child of a Korean national (single-entry, up to 90 days)'),
             item('f236_custody_relation_visa', 'CONDITIONAL_REQUIRED', anchor='③ 대한민국 국민과 해당 미성년자의 관계 및 양육권 보유관계를 입증할 수 있는 서류',
                  applies_when_ko='국민의 미성년 외국인 자녀(90일 이하 단수사증)', applies_when_en='Foreign minor child of a Korean national (single-entry, up to 90 days)'),
             item('f236_custodial_parent_guarantor', 'CONDITIONAL_REQUIRED', anchor='④ 양육권을 가진 대한민국국민인 부 또는 모의 신원보증서',
                  applies_when_ko='국민의 미성년 외국인 자녀(90일 이하 단수사증)', applies_when_en='Foreign minor child of a Korean national (single-entry, up to 90 days)'),
             item('f236_guardian_consent', 'CONDITIONAL_REQUIRED', anchor='⑤ 양육권 보유관계를 입증할 수 없을 경우에는 해당 미성년자와 동일한 국적을 보유한 해당 미성년자의 친권자 또는 후견인의 동의서',
                  applies_when_ko='양육권 보유관계를 입증할 수 없는 경우(친권자·후견인이 없으면 그 사실을 입증하는 관련국 공적 서류 또는 공증증서)', applies_when_en='If custody cannot be proven (if there is no such person, an official or notarised document proving it)'),
             item('f236_invitation', 'CONDITIONAL_REQUIRED', anchor='② 초청장',
                  applies_when_ko='국민과 혼인관계에서 출생한 자녀(5년 복수사증)', applies_when_en='Child born in a marriage with a Korean national (5-year multiple-entry)'),
             item('f236_parentage_proof', 'CONDITIONAL_REQUIRED', anchor='③ 국민과 해당 미성년자와의 관계입증 서류',
                  applies_when_ko='국민과 혼인관계에서 출생한 자녀(5년 복수사증)', applies_when_en='Child born in a marriage with a Korean national (5-year multiple-entry)'),
             item('f236_korean_parent_guarantor', 'CONDITIONAL_REQUIRED', anchor='④ 대한민국 국민인 부 또는 모의 신원보증서',
                  applies_when_ko='국민과 혼인관계에서 출생한 자녀(5년 복수사증)', applies_when_en='Child born in a marriage with a Korean national (5-year multiple-entry)'),
         ],
         conditions_ko=['국내입국 방편으로 입양된 경우에는 사증발급이 억제됩니다.',
                        '대한민국 국적을 보유한 복수국적자는 「복수국적자의 출입국 및 체류에 관한 지침」을 적용합니다.',
                        '병역 이행 또는 면제처분 없이 대한민국 국적을 이탈·상실해 외국인이 된 남성은 40세가 되는 해의 12월 31일까지 거주(F-2-2) 자격 부여가 제한됩니다(2018-05-01 이후 최초 이탈·상실자부터 적용).'],
         conditions_en=['Visas are withheld when the adoption was a means of entering Korea.',
                        'Dual nationals holding Korean nationality fall under the dual-nationals guideline.',
                        'Men who renounced or lost Korean nationality without completing or being exempted from military service cannot get F-2-2 until 31 December of the year they turn 40 (applies to those who renounced or lost it from 2018-05-01).'],
         notes_ko=[OFFICER_NOTE_VISA_KO], notes_en=[OFFICER_NOTE_VISA_EN])

F2_CVI_SEC = '사증발급 안내매뉴얼 거주(F-2) — 사증발급인정서 발급대상 1. 점수제 우수인재(상장법인·유망산업분야 종사자에 한함) 및 점수제 우수인재의 배우자 및 미성년 자녀'
F2_CVI_BASE = '① 사증발급인정신청서 (별지 제21호 서식), 여권, 외국인등록증(주체류자가 외국인등록을 마친 사람만 해당), 표준규격사진 1매'
F2_CVI_TB = '② 결핵 진단서(「외국인 결핵환자 사증발급 및 체류관리 지침 등」에 따름)'


def f236_cvi_base(anchor=F2_CVI_BASE, form='f236_cvi_form21'):
    return [item(form, anchor=anchor), item('passport', anchor=anchor),
            item('f236_principal_arc_if_registered', 'CONDITIONAL_REQUIRED', anchor=anchor, applies_when_ko='주체류자가 외국인등록을 마친 경우', applies_when_en='If the principal holder has registered'),
            item('photo', anchor=anchor)]


guidance('F-2-7', 'visa_issuance_confirmation', manual=VISA, section=F2_CVI_SEC + ' — 1) 상장 법인·유망산업분야 종사자',
         anchor='점수제 우수인재(상장법인·유망산업분야 종사자에 한함) 및 점수제',
         summary_ko='점수제 우수인재 중 상장법인 종사자와 유망산업분야 종사자는 사업장 주소지 관할 출입국·외국인청(사무소·출장소) 방문 또는 대한민국비자포털에서 거주(F-2-7, 단수, 90일) 사증발급인정서를 신청할 수 있습니다. 고용·소득·학위 서류, 점수표와 항목별 점수 입증서류, 체류지 입증서류를 냅니다.',
         summary_en='Points-system talent working for listed companies or in promising industries can apply for a confirmation of visa issuance for F-2-7 (single-entry, 90 days) at the immigration office for the workplace or on the Korea Visa Portal. Submit employment, income and degree documents, the points table with evidence for each item, and proof of residence.',
         docs=f236_cvi_base() + [
             item('tb_cert', anchor=F2_CVI_TB),
             item('f236_applicant_employment_docs', anchor='③ 신청자의 고용계약서, 재직증명서, 사업자등록증, 법인등기부등본, 소득금액증명'),
             item('f236_points_table_self', anchor='④ 신청인이 해당하는 점수를 기재한 점수표'),
             item('f236_points_proof', anchor='⑤ 신청인이 기재한 평가 항목별 점수를 입증하는 서류'),
             item('residence_proof', anchor='⑥ 체류지 입증서류'),
             item('f236_examiner_requested', 'MAY_BE_REQUESTED_BY_OFFICER', anchor='⑦ 심사관이 추가 제출을 요구한 서류'),
         ],
         conditions_ko=['상장법인 종사자: 유가증권시장(KOSPI)·코스닥(KOSDAQ) 상장법인 종사자 또는 취업 확정자로서 한국표준직업분류상 관리자·전문가 및 관련 종사자 직종에 취업 중이거나 취업이 확정된 외국인',
                        '유망산업분야 종사자: 「첨단기술 및 제품의 범위」에 따른 IT·기술경영·나노·디지털전자·바이오·수송 및 기계·신소재·환경 및 에너지 등 분야 종사자 또는 취업 확정자로서 소득금액증명원상 전년도 소득이 국민 1인당 GNI 1.5배 이상(취업 예정자는 고용계약서상 연봉)',
                        '소득금액증명은 신청일 기준 2년 이내 세무서에서 발급한 가장 최신년도 것입니다. 상장법인 취업(예정)자로서 소득금액증명 제출이 불가능한 경우에 한해 고용계약서상 연봉으로 연간소득을 산정합니다.'],
         conditions_en=['Listed-company staff: employed by (or hired by) a KOSPI/KOSDAQ-listed company in a manager, professional or related occupation under the Korean Standard Classification of Occupations.',
                        'Promising-industry staff: employed (or hired) in IT, technology management, nano, digital electronics, bio, transport and machinery, new materials, environment and energy, etc., with last year\'s income at least 1.5 × GNI per capita (the contract salary for new hires).',
                        'The income certificate is the latest one issued by the tax office within two years of applying. Only for listed-company hires who cannot submit one is the contract salary used.'],
         notes_ko=[CVI_NOTE_KO], notes_en=[CVI_NOTE_EN])

guidance('F-2-71', 'visa_issuance_confirmation', manual=VISA, section=F2_CVI_SEC + ' — 2) 점수제 우수인재의 배우자 및 미성년 자녀',
         anchor='점수제 우수인재의 배우자 및 미성년 자녀 : 초청자(F-2-7 체류자격자)의 주소지 관할 출입국·외국인청(사무소·출장소) 방문 신청',
         summary_ko='점수제 우수인재(F-2-7) 주체류자의 법률상 배우자와 미성년 자녀는 초청자의 주소지 관할 출입국·외국인청(사무소·출장소) 방문 또는 대한민국비자포털에서 거주(F-2-71, 단수, 90일) 사증발급인정서를 신청합니다. 주체류자의 소득기준(GNI 이상)을 충족하지 못하면(다른 요건 충족 시) 동반(F-3-18, 단수, 90일)으로 신청합니다.',
         summary_en='The legal spouse and minor children of an F-2-7 principal apply for an F-2-71 confirmation (single-entry, 90 days) at the immigration office for the inviter\'s address or on the Korea Visa Portal. If the principal does not meet the income standard (GNI or more) but meets the other requirements, they apply for F-3-18 (single-entry, 90 days).',
         docs=f236_cvi_base() + [
             item('tb_cert', anchor=F2_CVI_TB),
             item('f236_principal_employment_docs', anchor='③ 주체류자의 고용계약서, 재직증명서, 사업자등록증, 법인등기부등본, 소득금액증명'),
             item('f236_family_relation_principal', anchor='④ 가족관계 소명 서류(주체류자와의 법률상 가족관계 입증서류여야 함)'),
             item('f236_points_table', anchor='⑤ 점수제 평가를 위한 점수를 기재한 점수표'),
             item('f236_points_proof_self', anchor='⑥ 신청인 본인이 기재한 평가 항목별 점수를 소명하는 서류'),
             item('residence_proof', anchor='⑦ 체류지 입증서류'),
             item('f236_examiner_requested', 'MAY_BE_REQUESTED_BY_OFFICER', anchor='⑧ 심사관이 추가 제출을 요구한 서류'),
         ],
         conditions_ko=['주체류자는 점수제 평가항목 합산 80점 이상을 검증받고 F-2-7 자격을 받은 사람입니다(F-2-71은 초청자가 될 수 없음).',
                        '배우자는 법률상 배우자로서 진정한 혼인관계를 유지해야 하며 사실혼은 인정되지 않습니다. 미성년 자녀는 주체류자가 친권과 양육권을 가지고 있어야 합니다.',
                        '초청자가 F-2-7S이면 초청자가 자격변경허가를 받은 날부터 5년 동안은 소득요건 심사 없이, 5년이 지난 뒤에는 소득요건 심사 후 충족 시 F-2-71(단수, 90일)을 받습니다.'],
         conditions_en=['The principal is someone verified at 80+ points who holds F-2-7 (an F-2-71 holder cannot invite).',
                        'The spouse must be a legal spouse in a genuine marriage (de facto marriage not accepted); for minor children the principal must hold parental authority and custody.',
                        'If the inviter holds F-2-7S, F-2-71 (single-entry, 90 days) is issued without an income check for five years from the inviter\'s status change, and after that only if the income requirement is met.'],
         notes_ko=[CVI_NOTE_KO], notes_en=[CVI_NOTE_EN])

# ==========================================================================
# F-2 거주 — 체류자격 부여 (stay manual)
# ==========================================================================
guidance('F-2', 'status_grant', section='거주(F-2) 체류자격 부여 — 영주권자의 한국인배우자가 국적을 상실한 경우',
         anchor='영주(F-5) 자격을 가진 자의 한국인배우자가 그 배우자의 국적을 취득하여 대한민국 국적을 상실한 때에는 거주(F-2, 기간:1년간) 체류자격 부여',
         summary_ko='매뉴얼의 거주(F-2) 체류자격 부여 절은 영주(F-5) 자격자의 한국인 배우자가 그 배우자의 국적을 취득해 대한민국 국적을 상실한 경우를 다루며, 이때 거주(F-2) 자격을 1년간 부여합니다. 신청서·여권·사진·수수료와 국적취득증명서를 냅니다.',
         summary_en='The F-2 status-grant section covers the Korean spouse of an F-5 holder who acquires the spouse\'s nationality and so loses Korean nationality; F-2 is then granted for one year. Submit the form, passport, photo, fee and the certificate of nationality acquisition.',
         period_ko='1년', period_en='1 year',
         docs=f236_stay_base('① 신청서(별지 34호 서식), 여권, 표준규격사진 1매, 수수료') + [item('f236_nationality_acquisition_cert', anchor='② 국적취득증명서')],
         notes_ko=['점수제 우수인재(F-2-7)의 국내 출생 자녀에 대한 기준은 같은 절의 "1. 점수제 우수인재(F-2-7)의 국내 출생 자녀"에 따로 있습니다.', OFFICER_NOTE_KO],
         notes_en=['The rule for Korea-born children of points-system residents (F-2-7) is set out separately in the same section ("1. Korea-born children of F-2-7").', OFFICER_NOTE_EN])

guidance('F-2-71', 'status_grant', completeness='PARTIALLY_STRUCTURED', section='거주(F-2) 체류자격 부여 — 1. 점수제 우수인재(F-2-7)의 국내 출생 자녀',
         anchor='국내에서 출생한 점수제 우수인재(F-2-7, F-2-7S)의 미성년 자녀',
         summary_ko='국내에서 출생한 점수제 우수인재(F-2-7, F-2-7S)의 미성년 자녀는 결격사유가 없고, 주체류자(부 또는 모)가 F-2-7 또는 F-2-7S로 합법체류 중이며 주체류자의 연간소득이 최근 1인당 국민소득 이상이면(다른 요건 모두 충족) 체류자격을 받습니다. 체류자격과 체류기간은 주체류자가 아닌 부 또는 모와 같게 부여합니다.',
         summary_en='A Korea-born minor child of a points-system resident (F-2-7, F-2-7S) is granted status if there are no disqualifying grounds, the principal parent is lawfully staying as F-2-7 or F-2-7S, and the principal\'s annual income is at least the latest GNI per capita (all other requirements met). The child gets the same status and period as the parent who is not the principal.',
         docs=[item('f236_birth_cert', anchor='출생증명서, 신원보증서'), item('guarantor', anchor='출생증명서, 신원보증서'),
               item('f236_same_as_change', 'SOURCE_MENTIONS_BUT_NOT_STRUCTURED', anchor='체류자격 변경 심사 서류와 동일',
                    notes_ko=['매뉴얼은 나머지 서류를 "체류자격 변경 심사 서류와 동일"이라고만 적습니다.'], notes_en=['The manual only says the rest are "the same as for the change-of-status review".'])],
         conditions_ko=['부 또는 모의 체류자격이 국내에서 F-2-71로 변경할 요건을 충족하면 부·모 요건을 충족한 것으로 심사합니다. 부 또는 모가 단기 체류자격이나 국내 자격변경이 되지 않는 장기 체류자격(기타(G-1), 관광취업(H-1) 등)이면 충족하지 않습니다.',
                        '부 또는 모가 단기 체류자격(B-1, B-2, C-3)으로 입국해 국내에서 출생한 자녀는 장기 체류자격을 부여하지 않으며, 출국해 관련 비자를 받고 입국해야 합니다.',
                        '주체류자가 F-2-7S이면 소득요건과 관계없이 주체류자의 체류기간(5년 동안)과 같게 F-2-71 자격을 부여합니다.'],
         conditions_en=['If the parent\'s status meets the requirements for changing to F-2-71 in Korea, the parent requirement is treated as met; short-term statuses and long-term statuses that cannot be changed in Korea (G-1, H-1, etc.) do not qualify.',
                        'Children born in Korea to a parent who entered on a short-term status (B-1, B-2, C-3) are not granted long-term status; they must leave and enter on the proper visa.',
                        'If the principal holds F-2-7S, the child gets F-2-71 for the principal\'s period (during the five years) regardless of income.'],
         notes_ko=[OFFICER_NOTE_KO], notes_en=[OFFICER_NOTE_EN])

# ==========================================================================
# F-2 거주 — 체류자격 변경허가 (stay manual, by subcode)
# ==========================================================================
guidance('F-2-2', 'status_change', section='거주(F-2) 체류자격 변경허가 — 1. 국민의 외국인자녀에 대한 거주 자격으로 변경허가',
         anchor='1. 국민의 외국인자녀에 대한 거주 자격으로 변경허가',
         summary_ko='국민의 미성년 외국인 자녀와 국민과의 혼인관계(사실혼 포함)에서 출생한 자녀는 거주(F-2-2)로 자격을 바꿀 수 있습니다. 관계·양육권 입증서류, 국민의 외국인 자녀임을 입증하는 서류, 자녀의 호구부·거민신분증, 부모의 기본증명서·가족관계증명서·주민등록등본, 양육권을 가진 부 또는 모의 신원보증서를 냅니다.',
         summary_en='Foreign minor children of Korean nationals and children born in a marriage (including de facto) with a Korean national can change to F-2-2. Submit proof of relationship and custody, proof of being the foreign child of a Korean national, the child\'s hukou and resident ID, the parents\' basic, family-relation and resident-registration certificates, and a guarantee from the parent with custody.',
         docs=f236_stay_base('나. 제출서류 ① 신청서(별지 34호 서식), 여권, 표준규격사진 1매, 수수료') + [
             item('f236_custody_proof_stay', anchor='② 대한민국 국민과 해당 미성년자와의 관계 및 양육권 보유관계를 입증할 수 있는 서류',
                  notes_ko=["양육권 보유관계를 입증할 수 없으면 '친권자' 또는 '후견인'의 동의서(그런 사람이 없으면 그 사실을 입증하는 관련국의 공적서류 또는 공정증서)를 냅니다."],
                  notes_en=['If custody cannot be proven, submit the consent of the person with parental authority or the guardian (if none, an official or notarised document proving that).']),
             item('f236_foreign_child_proof', anchor='③ 국민의 외국인 자녀임을 입증할 수 있는 서류'),
             item('f236_child_hukou_id', anchor='④ 자녀의 호구부 및 거민신분증'),
             item('f236_parent_certs', anchor='⑤ 부모의 기본증명서, 가족관계증명서, 주민등록등본'),
             item('f236_custodial_guarantor', anchor='⑥ 신원보증서(양육권을 가진 부 또는 모)'),
         ],
         conditions_ko=['기존 방문동거(F-1-1)로 체류 중인 국민의 미성년 외국인 자녀는 확인 즉시 수수료 없이 거주(F-2-2)로 변경합니다.',
                        '재외동포(F-4) 자격부여 제한 대상자는 제외됩니다. 병역 이행 또는 면제처분 없이 국적을 이탈·상실해 외국인이 된 남성은 40세가 되는 해의 12월 31일까지 F-2-2 자격 부여가 제한됩니다(2018-05-01 이후 최초 이탈·상실자부터).',
                        '대한민국 국적을 보유한 복수국적자는 「복수국적자의 출입국 및 체류에 관한 지침」을 적용합니다.'],
         conditions_en=['Foreign minor children of nationals staying on the old F-1-1 are changed to F-2-2 on confirmation, without a fee.',
                        'People barred from F-4 status are excluded. Men who renounced or lost Korean nationality without military service or exemption cannot get F-2-2 until 31 December of the year they turn 40 (from those who did so on or after 2018-05-01).',
                        'Dual nationals holding Korean nationality fall under the dual-nationals guideline.'],
         notes_ko=[OFFICER_NOTE_KO], notes_en=[OFFICER_NOTE_EN])

F23_SPOUSE = {'applies_when_ko': '배우자가 신청하는 경우', 'applies_when_en': 'Spouse applicants'}
guidance('F-2-3', 'status_change', section='거주(F-2) 체류자격 변경허가 — 2. 영주자격 소지자의 배우자 및 미성년 자녀에 대한 거주자격 변경 허가',
         anchor='2. 영주자격 소지자의 배우자 및 미성년 자녀에 대한 거주자격 변경 허가',
         summary_ko='영주(F-5) 자격 소지자의 배우자와 미성년 자녀는 거주(F-2-3)로 자격을 바꿀 수 있습니다. 배우자는 국내 배우자의 신원보증서, 초청장, 혼인배경 진술서, 양국간 혼인관계 입증서류, 재정 서류, 신용정보조회서, 쌍방의 범죄경력증명서와 건강진단서 등을 내고, 미성년 자녀는 가족관계 입증서류를 냅니다.',
         summary_en='Spouses and minor children of F-5 permanent residents can change to F-2-3. Spouses submit the guarantee from the spouse in Korea, the invitation, marriage-background statement, proof of the marriage in both countries, financial documents, credit report, and both spouses\' criminal record and health certificates; minor children submit proof of family relationship.',
         docs=f236_stay_base('① 신청서(별지 34호 서식), 여권, 표준규격사진 1매, 수수료') + [
             item('f236_spouse_guarantor', 'CONDITIONAL_REQUIRED', anchor='② 국내 배우자의 신원보증서', **F23_SPOUSE),
             item('f236_invitation', 'CONDITIONAL_REQUIRED', anchor='③ 초청장', **F23_SPOUSE),
             item('f236_marriage_background', 'CONDITIONAL_REQUIRED', anchor='④ 혼인배경 진술서', **F23_SPOUSE),
             item('f236_marriage_proof_both', 'CONDITIONAL_REQUIRED', anchor='⑤ 양국간 혼인관계 입증서류', **F23_SPOUSE),
             item('f236_finance_income', 'CONDITIONAL_REQUIRED', anchor='⑥ 재정(소득) 입증관련 서류', **F23_SPOUSE),
             item('f236_spouse_guarantor_courtship', 'CONDITIONAL_REQUIRED', anchor='⑦ 국내 배우자의 신원보증서, 교제경위서 등', **F23_SPOUSE),
             item('f236_spouse_credit_report', 'CONDITIONAL_REQUIRED', anchor='⑧ 국내 배우자의 신용정보조회서', **F23_SPOUSE),
             item('f236_crime_record_both', 'CONDITIONAL_REQUIRED', anchor='국적국 또는 거주국의 관할 기관이 발급한 혼인당사자 쌍방의', **F23_SPOUSE,
                  notes_ko=['영주(F-5) 자격 소지자 본인이 영주자격 변경 때 이미 냈다면 본인 것은 생략할 수 있으나, 그 뒤 해외에서 6개월 이상 체류했다면 그 기간 체류국 정부가 발행한 증명서를 냅니다.'],
                  notes_en=['The F-5 holder may skip their own certificate if it was filed for the F-5 change, unless they have since stayed abroad 6 months or more.']),
             item('f236_health_both', 'CONDITIONAL_REQUIRED', anchor='⑩ 혼인당사자 쌍방의 건강진단서', **F23_SPOUSE,
                  notes_ko=['병원급 의료기관이나 보건소가 발행한 것이어야 하며, 외국인 배우자는 국적국 또는 거주국에서 통용되는 유사한 입증자료로 갈음할 수 있습니다.'],
                  notes_en=['Issued by a hospital-level institution or public health centre; the foreign spouse may use an equivalent document from their country.']),
             item('f236_prior_marriage_dissolution', 'CONDITIONAL_REQUIRED', anchor='⑪ 과거 혼인기록이 있는 경우 혼인 해소 여부를 입증할 수 있는 서류',
                  applies_when_ko='배우자 신청으로 과거 혼인기록이 있는 경우', applies_when_en='Spouse applicants with an earlier marriage'),
             item('f236_family_proof_birth', 'CONDITIONAL_REQUIRED', anchor='② 가족관계 입증 서류(출생증명서,',
                  applies_when_ko='미성년 자녀가 신청하는 경우', applies_when_en='Minor-child applicants'),
         ],
         notes_ko=['매뉴얼은 배우자와 미성년 자녀의 서류를 표 두 칸으로 나누어 적고 있으며, ①번 서류(신청서·여권·사진·수수료)는 배우자 칸에 적혀 있습니다.', OFFICER_NOTE_KO],
         notes_en=['The manual lists spouse and minor-child documents in two table columns; item ① (form, passport, photo, fee) appears in the spouse column.', OFFICER_NOTE_EN])

guidance('F-2-4', 'status_change', section='거주(F-2) 체류자격 변경허가 — 3. 난민인정을 받은 자에 대한 거주자격 변경허가',
         anchor='3. 난민인정을 받은 자에 대한 거주자격 변경허가',
         summary_ko='난민인정을 받은 사람은 신청서·여권·외국인등록증·사진·수수료, 난민인정증명서, 체류지 입증서류를 내고 거주(F-2-4)로 자격을 바꿉니다.',
         summary_en='Recognised refugees change to F-2-4 with the form, passport, residence card, photo, fee, the refugee recognition certificate and proof of residence.',
         docs=f236_stay_base('① 신청서(별지 34호 서식), 여권 및 외국인등록증, 표준규격사진 1매, 수수료', arc=True) + [
             item('f236_refugee_cert', anchor='② 난민인정증명서'),
             residence(anchor='③ 체류지 입증 서류(임대차계약서, 숙소제공 확인서', alts=[
                 {'ko': '임대차계약서', 'en': 'Lease contract'}, {'ko': '숙소제공 확인서', 'en': 'Accommodation provision confirmation'},
                 {'ko': '체류기간 만료예고 통지 우편물', 'en': 'Stay-expiry notice mail'}, {'ko': '공공요금 납부영수증', 'en': 'Utility bill receipt'},
                 {'ko': '기숙사비 영수증', 'en': 'Dormitory fee receipt'}, {'ko': '교회·난민지원시설·인권단체·UNHCR 등의 주거확인서', 'en': 'Housing confirmation from a church, refugee support facility, human-rights group, UNHCR, etc.'}]),
         ],
         notes_ko=[OFFICER_NOTE_KO], notes_en=[OFFICER_NOTE_EN])

F25_A = {'applies_when_ko': '미화 50만 달러 이상 투자 후 기업투자(D-8)로 3년 이상 계속 체류', 'applies_when_en': 'Invested USD 500,000+ and stayed 3+ years on D-8'}
F25_B = {'applies_when_ko': '미화 50만 달러 이상 투자한 외국법인이 국내 외국인투자기업에 파견한 임직원으로 3년 이상 계속 체류', 'applies_when_en': 'Staff dispatched for 3+ years by a foreign company that invested USD 500,000+'}
F25_C = {'applies_when_ko': '미화 30만 달러 이상 투자하여 2명 이상의 국민을 고용', 'applies_when_en': 'Invested USD 300,000+ and employ 2+ Korean nationals'}
guidance('F-2-5', 'status_change', section='거주(F-2) 체류자격 변경허가 — 4. 고액투자자에 대한 거주자격 변경허가',
         anchor='4. 고액투자자에 대한 거주자격 변경허가',
         summary_ko='「외국인투자촉진법」에 따른 고액투자자는 투자 유형(50만 달러 이상 투자 후 D-8 3년 이상, 50만 달러 이상 투자 법인의 파견 임직원 3년 이상, 30만 달러 이상 투자 후 국민 2명 이상 고용)에 따라 정해진 서류를 내고 거주(F-2-5)로 자격을 바꿉니다.',
         summary_en='High-value investors under the Foreign Investment Promotion Act change to F-2-5 with the documents for their case: USD 500,000+ invested and 3+ years on D-8; staff of a USD 500,000+ investor company dispatched for 3+ years; or USD 300,000+ invested with 2+ Korean employees.',
         docs=[item('app_form_34', anchor='① 신청서(별지 34호 서식), 여권 및 외국인등록증, 수수료'), item('passport', anchor='① 신청서(별지 34호 서식), 여권 및 외국인등록증, 수수료'),
               item('arc', 'CONDITIONAL_REQUIRED', anchor='① 신청서(별지 34호 서식), 여권 및 외국인등록증, 수수료',
                    applies_when_ko='50만 달러 이상 투자자(D-8 3년 이상) 또는 파견 임직원', applies_when_en='USD 500,000+ investors (3+ years on D-8) or dispatched staff'),
               item('fee', anchor='① 신청서(별지 34호 서식), 여권 및 외국인등록증, 수수료'),
               item('fdi_company_reg_copy', 'CONDITIONAL_REQUIRED', anchor='② 투자기업등록증 사본', **F25_A),
               item('f236_dispatch_or_income', 'CONDITIONAL_REQUIRED', anchor='② 파견명령서 또는 재직증명서 또는 소득금액증명원(3년간)', **F25_B),
               item('f236_fdi_report_or_reg', 'CONDITIONAL_REQUIRED', anchor='② 외국인 투자신고서 또는 투자기업등록증 사본', **F25_C),
               item('f236_employee_contract_or_income', 'CONDITIONAL_REQUIRED', anchor='③ 피고용인에 대한 고용계약서 또는 소득금액증명원', **F25_C)],
         conditions_ko=[LAW_ABIDING_KO], conditions_en=[LAW_ABIDING_EN],
         notes_ko=[OFFICER_NOTE_KO], notes_en=[OFFICER_NOTE_EN])

F27_BASE = '신청서, 여권, 외국인등록증, 사진, 수수료, 체류지 입증서류, 해외범죄경력증명서'
guidance('F-2-7', 'status_change', completeness='PARTIALLY_STRUCTURED', covers=['F-2-7S', 'F-2-71'], doc_page_window=9,
         section='거주(F-2) 체류자격 변경허가 — 5. 점수제 우수인재 및 동반가족의 거주자격 변경허가',
         anchor='5. 점수제 우수인재 및 동반가족의 거주자격 변경허가',
         summary_ko='상장법인·유망산업분야·전문직 종사자, 유학인재, 잠재적 우수인재(F-2-7S)와 그 배우자·미성년 자녀는 결격사유가 없고 점수표 합산 80점 이상이며 취업제한 분야 종사 사실이 없으면 거주 자격으로 바꿀 수 있습니다. 기본서류(신청서·여권·외국인등록증·사진·수수료·체류지 입증서류·해외범죄경력증명서·고용계약서)와 점수표, 항목별 점수 입증서류를 냅니다.',
         summary_en='Staff of listed companies or promising industries, professionals, Korean-educated graduates, potential talent (F-2-7S) and their spouses and minor children can change to residence status if they have no disqualifying grounds, score 80+ points and have not worked in a restricted field. Submit the basic documents (form, passport, residence card, photo, fee, proof of residence, overseas criminal record, employment contract) with the points table and evidence for each item.',
         docs=[item('app_form', anchor=F27_BASE), item('passport', anchor=F27_BASE), item('arc', anchor=F27_BASE), item('photo', anchor=F27_BASE), item('fee', anchor=F27_BASE),
               item('residence_proof', anchor=F27_BASE), item('overseas_criminal_record', anchor=F27_BASE),
               item('employment_contract', anchor='해외범죄경력증명서(연장신청시 6개월이상 해외체류시에만 제출), 고용계약서'),
               item('f236_points_table_self', anchor='① 신청인이 해당하는 점수를 기재한 점수표'),
               item('f236_points_proof', anchor='② 신청인이 기재한 평가 항목별 점수를 입증하는 서류',
                    notes_ko=['평가 항목별 입증서류는 매뉴얼의 별도 붙임(붙임 3)에 정해져 있습니다.'], notes_en=['The evidence for each item is set out in a separate annex (annex 3) of the manual.']),
               item('f236_points_extra', 'ADDITIONAL_IF_APPLICABLE', anchor='③ 추가서류 : 가족관계 소명 서류(출생증명서 포함)', applies_when_ko='해당자', applies_when_en='If applicable')],
         conditions_ko=['결격사유: 신청일로부터 5년 이내 금고 이상의 형 선고(집행유예 포함), 3년 이내 출입국관리법 3회 이상 위반으로 통고처분 합계 500만원 이상, 3년 이내 300만원 이상 벌금형, 3년 이내 허위서류 제출, 입국금지 사유 등.',
                        '신청일 이전 3년 이내 취업 제한 분야에 취업한 사실이 없어야 하고, 신청일 이전 6개월 이내 국내 노동시장·사회경제 질서에 부정적 영향을 미칠 수 있는 직종에 종사하지 않아야 합니다.',
                        '해외에서 발급받은 서류는 아포스티유 또는 대한민국 공관의 영사확인을 받아(국문 또는 영문 번역문 첨부) 내야 하며 발급일로부터 3개월간 유효합니다.',
                        '해외범죄경력증명서는 국내 출생 후 해외에서 6개월 이상 연속 체류하지 않은 사람, 과거 본국 범죄경력증명서를 낸 뒤 해외 6개월 이상 연속 체류가 없는 사람, 재외공관 사증발급 때 제출하고 3개월 이내 자격변경을 신청하는 사람은 면제됩니다.',
                        LAW_ABIDING_KO],
         conditions_en=['Disqualifying grounds include: a sentence of imprisonment without labour or heavier (incl. suspended) within 5 years; 3+ immigration-law violations with fines totalling KRW 5 million+ within 3 years; a fine of KRW 3 million+ within 3 years; false documents within 3 years; grounds for an entry ban.',
                        'No work in a restricted field within 3 years before applying, and none in an occupation harmful to the labour market or socio-economic order within 6 months.',
                        'Documents issued abroad need an apostille or Korean consular confirmation (with a Korean or English translation) and are valid for 3 months.',
                        'The overseas criminal record is waived for people born in Korea who have not stayed abroad 6+ consecutive months, those who filed one before and have not stayed abroad 6+ consecutive months since, and those who filed one for a visa and apply within 3 months of its issue.',
                        LAW_ABIDING_EN],
         notes_ko=[OFFICER_NOTE_KO], notes_en=[OFFICER_NOTE_EN])

F28_CORP = {'applies_when_ko': '법인의 임원 또는 주주 해당자', 'applies_when_en': 'Company officers or shareholders'}
guidance('F-2-8', 'status_change', covers=['F-2-81'], doc_page_window=5,
         section='거주(F-2) 체류자격 변경허가 — 6. 관광·휴양시설 투자 외국인에 대한 거주(F-2-8, F-2-81)자격 변경허가',
         anchor='6. 관광·휴양시설 투자 외국인에 대한 거주(F-2-8, F-2-81)자격 변경허가',
         summary_ko='법무부장관이 고시한 관광·휴양시설에 기준금액 이상을 본인 자금으로 투자한 외국인 또는 법인의 현직 임원·주주와 그 배우자·미혼자녀는 거주(F-2-8, F-2-81)로 자격을 바꿀 수 있습니다. 부동산 계약·등기 또는 회원증서, 외환반입 입증서류, 해외범죄경력증명서 등을 냅니다.',
         summary_en='Foreigners, or current officers and shareholders of a company, who invested at least the threshold of their own funds in a designated tourism or leisure facility, and their spouses and unmarried children, can change to F-2-8 / F-2-81. Submit the property contract and register or membership certificate, proof of bringing in foreign currency, an overseas criminal record, etc.',
         docs=f236_stay_base('① 신청서(별지 34호 서식), 여권, 외국인등록증(해당자), 표준규격사진 1매, 수수료') + [
             item('f236_arc_if_any', 'CONDITIONAL_REQUIRED', anchor='① 신청서(별지 34호 서식), 여권, 외국인등록증(해당자), 표준규격사진 1매, 수수료', applies_when_ko='해당자', applies_when_en='If held'),
             item('f236_property_contract_register', 'CONDITIONAL_REQUIRED', anchor='② 부동산 매매계약서, 부동산 등기부등본(F-2 대상자에 한함)', applies_when_ko='F-2 대상자에 한함', applies_when_en='F-2 applicants only'),
             item('f236_condo_membership', 'CONDITIONAL_REQUIRED', anchor='분양회사가 (사)한국휴양콘도미니엄경영협회에서 확인받아 발급한 회원증서', applies_when_ko='회원인 경우에 한함', applies_when_en='Members only'),
             item('f236_unsold_vacancy', 'CONDITIONAL_REQUIRED', anchor='④ 미분양주택 공실 확인서(미분양주택 투자자에 한함)', applies_when_ko='미분양주택 투자자에 한함', applies_when_en='Unsold-house investors only'),
             item('f236_move_in_list', 'CONDITIONAL_REQUIRED', anchor='⑤ 해당주택 전입세대 열람내역(미분양주택 투자자에 한함', applies_when_ko='미분양주택 투자자에 한함', applies_when_en='Unsold-house investors only'),
             item('f236_fx_inflow_proof', anchor='④ 외환반입 관련 입증서류',
                  notes_ko=['카드로 결제한 경우 은행 발행 결제정보 확인서, 신용카드 전면 및 매출전표 사본, 분양회사 입금영수증을 모두 냅니다.'], notes_en=['For card payments, submit the bank payment confirmation, a copy of the card front and sales slip, and the developer\'s receipt.']),
             item('f236_overseas_remit_corp', 'CONDITIONAL_REQUIRED', anchor='⑤ 국외에서 해당 투자자 명의로 법인에 투자금을 송금 또는 지불하였음을 입증하는 서류', applies_when_ko='법인을 통해 간접투자한 경우에 한함', applies_when_en='Indirect investment through a company only'),
             item('f236_corp_officer_proof', 'CONDITIONAL_REQUIRED', anchor='⑥ 투자한 법인의 현직 임원 또는 과점주주임을 입증하는 서류', **F28_CORP),
             item('f236_family_cert_dependants', 'CONDITIONAL_REQUIRED', anchor='⑦ 가족관계 증명서 (배우자·미혼 자녀의 송금 또는 자격변경 신청에 한함)',
                  applies_when_ko='배우자·미혼 자녀의 송금 또는 자격변경 신청에 한함(성년자녀는 미혼임을 확인하는 서류)', applies_when_en='Spouse or unmarried child remitting or applying (adult children: proof of being unmarried)'),
             item('f236_overseas_crime_6m', anchor='⑧ 국적국 또는 거주국의 해외범죄경력증명서'),
         ],
         conditions_ko=['투자 목적물 소재지 관할 출입국외국인관서에 사전심사를 신청하고, 사전심사 후 6개월 이내에 국내 외국환은행을 통해 투자금을 반입해야 합니다(6개월 이후 반입하려면 사전심사 재신청).',
                        '본인의 해외 자본을 본인 명의로 송금·수령해 투자해야 하며, 투자시설을 임대·담보·압류하거나 수익활동에 활용하지 않아야 합니다. 불법체류 중 형성된 국내 소득과 자산은 어떠한 경우에도 투자금으로 인정하지 않습니다.',
                        '신청기관은 투자시설 소재지(2곳 이상이면 투자금액이 많은 지역) 관할 관서이며, 등록외국인은 체류지 관할 관서에 신청합니다.',
                        LAW_ABIDING_KO],
         conditions_en=['Apply for a pre-review at the office for the location of the investment, then bring the funds in through a Korean foreign-exchange bank within 6 months (after 6 months, apply for the pre-review again).',
                        'You must remit and receive your own foreign capital in your own name; the facility must not be leased, mortgaged, seized or used for profit. Income or assets formed while staying illegally never count.',
                        'Apply at the office for the facility\'s location (the one with the larger investment if there are several); registered foreigners apply at the office for their address.',
                        LAW_ABIDING_EN],
         notes_ko=[OFFICER_NOTE_KO], notes_en=[OFFICER_NOTE_EN])

guidance('F-2-12', 'status_change', covers=['F-2-13'], doc_page_window=7,
         section='거주(F-2) 체류자격 변경허가 — 7. 공익사업투자 외국인에 대한 거주(F-2-12,13,14) 체류자격 변경허가',
         anchor='7. 공익사업투자 외국인에 대한 거주(F-2-12,13,14) 체류자격 변경허가',
         summary_ko='법무부장관이 공익사업 투자이민으로 고시한 대상에 15억 원 이상을 출자(예치)한 외국인과 법인의 임원·주주, 그리고 그 배우자·미혼자녀는 거주(F-2) 자격으로 바꿀 수 있습니다. 투자금 납입 증명, 외화반입 입증서류, 해외범죄경력증명서 등을 냅니다.',
         summary_en='Foreigners, and company officers and shareholders, who invested (deposited) KRW 1.5 billion or more in a designated public-interest investment, and their spouses and unmarried children, can change to residence status. Submit proof of payment, proof of bringing in foreign currency, an overseas criminal record, etc.',
         docs=f236_stay_base('① 신청서(별지 제34호 서식), 여권사본, 사진, 수수료', passport='passport_copy') + [
             item('f236_investment_payment_proof', anchor='② 투자금 납입 증명 서류'),
             item('f236_fx_inflow_proof_public', anchor='③ 외화반입 관련 입증서류'),
             item('f236_family_cert_dependants', 'CONDITIONAL_REQUIRED', anchor='④ 가족관계 증명서 (배우자·미혼 자녀의 송금 또는 자격변경 신청에 한함)', applies_when_ko='배우자·미혼 자녀의 송금 또는 자격변경 신청에 한함', applies_when_en='Spouse or unmarried child remitting or applying'),
             item('f236_overseas_remit_corp', 'CONDITIONAL_REQUIRED', anchor='서류 추가(개인이 법인을 통해 투자한 경우에 한함)', applies_when_ko='개인이 법인을 통해 투자한 경우에 한함', applies_when_en='Individuals investing through a company only'),
             item('f236_corp_officer_proof', 'CONDITIONAL_REQUIRED', anchor='해당 법인의 공문(법인의 임원 또는 주주 해당자에 한함) ⑦ 국적국 또는 거주국의 해외범죄경력증명서', **F28_CORP),
             item('f236_overseas_crime_6m', anchor='⑦ 국적국 또는 거주국의 해외범죄경력증명서'),
         ],
         conditions_ko=['법무부 글로벌인재비자센터 또는 제주청(제주도 체류자에 한함)에 사전심사를 신청하고, 사전심사 후 6개월 이내에 공익투자 전담은행을 통해 투자금을 반입해야 합니다.',
                        '투자자가 영주(F-5-21/23) 취득 후 투자를 유지하는 경우 동반가족은 F-2-3 또는 F-2-13 중 택해 신청할 수 있으나, 투자금을 회수했다면 F-2-3 신청 대상입니다.',
                        '자격변경 전담기관: 손익발생형은 개발사업자가 등록된 출입국관서, 원금보장·무이자형은 세종로출장소와 제주청(제주도 체류자에 한함)입니다.',
                        LAW_ABIDING_KO],
         conditions_en=['Apply for a pre-review at the Ministry\'s Global Talent Visa Center or Jeju office (Jeju residents only), then bring the funds in through the designated bank within 6 months.',
                        'If the investor keeps the investment after obtaining F-5-21/23, family members may choose F-2-3 or F-2-13; if the investment was withdrawn, they apply for F-2-3.',
                        'Handling offices: the office where the developer is registered (profit/loss type); Sejong-ro branch and Jeju office (principal-guaranteed, interest-free type; Jeju residents for Jeju).',
                        LAW_ABIDING_EN],
         notes_ko=[OFFICER_NOTE_KO], notes_en=[OFFICER_NOTE_EN])

F216_COMMON = '공통서류 : 신청서, 여권, 사진, 수수료, 체류지 입증서류, 해외범죄경력서'
guidance('F-2-16', 'status_change', doc_page_window=5,
         section='거주(F-2) 체류자격 변경허가 — 8. 대한민국에 특별한 기여를 했거나 공익 증진에 이바지한(F-2-16) 체류자격 변경허가',
         anchor='8. 대한민국에 특별한 기여를 했거나 공익 증진에 이바지한(F-2-16) 체류자격 변경허가',
         summary_ko='법무부장관이 대한민국에 특별한 기여를 했거나 공익 증진에 이바지했다고 인정하는 사람과 그 배우자·자녀는 국내 합법 체류 중 거주(F-2-16)로 자격을 바꿀 수 있습니다. 공통서류와 기본소양 입증서류, 특별 기여 입증서류(훈·포장 증서, 추천서 등)를 냅니다.',
         summary_en='People the Minister of Justice recognises as having made a special contribution to Korea or to the public interest, and their spouses and children, can change to F-2-16 while lawfully staying in Korea. Submit the common documents, proof of basic Korean knowledge and proof of the contribution (decoration certificate, recommendation, etc.).',
         docs=[item('app_form', anchor=F216_COMMON), item('passport', anchor=F216_COMMON), item('photo', anchor=F216_COMMON), item('fee', anchor=F216_COMMON),
               item('residence_proof', anchor=F216_COMMON), item('overseas_criminal_record', anchor=F216_COMMON,
                    notes_ko=['자국 정치 상황 등으로 발급이 불가능한 사람, 형사 미성년자, 국내 출생 후 해외 6개월 이상 연속 체류가 없는 사람 등은 해외범죄경력 확인을 생략할 수 있습니다.'],
                    notes_en=['Can be skipped e.g. if it cannot be issued because of the political situation, for minors under criminal age, or for people born in Korea without 6+ consecutive months abroad.']),
               item('f236_basic_knowledge', 'ADDITIONAL_IF_APPLICABLE', anchor='추가서류 : 기본소양 입증서류', applies_when_ko='추가서류', applies_when_en='Additional document'),
               item('f236_special_contribution_proof', anchor='특별 기여 입증서류(훈․포장 증서 추천서, 그외 증빙 서류 등)'),
               item('other_officer_docs', 'MAY_BE_REQUESTED_BY_OFFICER', anchor='기타 심사에 필요하다고 인정하는 서류(가족관계 입증서류 등)')],
         conditions_ko=['기본소양 요건(국내 3년 이상 체류, 사회통합프로그램 2단계 이상 이수, 사전평가 41점 이상, 국내 학교 졸업 등 중 하나)은 신청 당시 민법상 미성년자에게 적용하지 않습니다. 요건을 갖추지 못하면 다음 연장 때까지 충족하도록 안내하고 확인서를 받은 뒤 1년 이내로 허가합니다.',
                        '재학 여부, 직업 및 연간소득, 감염병 예방 관리(결핵) 해당자는 관련 서류를 냅니다.',
                        LAW_ABIDING_KO],
         conditions_en=['The basic-knowledge requirement (3+ years in Korea, social integration program level 2+, pre-assessment 41+, a Korean school diploma, etc.) does not apply to minors. If it is not met, approval is for up to one year after you sign a confirmation to meet it by the next extension.',
                        'Those concerned submit documents on school enrolment, occupation and annual income, and TB control.',
                        LAW_ABIDING_EN],
         notes_ko=[OFFICER_NOTE_KO], notes_en=[OFFICER_NOTE_EN])

F299_FORM = '① 여권, 사진 1매, 수수료, 신청서 및 신청사유서(서식 1)'
guidance('F-2-99', 'status_change', doc_page_window=9,
         section='거주(F-2) 체류자격 변경허가 — 9. 기타 장기체류자에 대한 거주 자격 변경허가',
         anchor='9. 기타 장기체류자에 대한 거주 자격 변경허가',
         summary_ko='정해진 체류자격으로 대한민국에 5년 이상 계속 체류해 생활 근거지가 국내에 있는 사람은 품행단정, 생계유지 능력(본인 자산 2,000만원 이상, 전년도 연간소득 4,000만원 이상, 경제활동 지속), 기본소양, 체류지 요건을 모두 갖추면 기타 장기체류(F-2-99)로 바꿀 수 있습니다.',
         summary_en='People who have stayed in Korea continuously for 5+ years on an eligible status, with their base of life in Korea, can change to F-2-99 if they meet the good-conduct, self-support (own assets of KRW 20 million+, last year\'s income KRW 40 million+, continuing economic activity), basic-knowledge and residence requirements.',
         docs=[item('passport', anchor=F299_FORM), item('photo', anchor=F299_FORM), item('fee', anchor=F299_FORM), item('app_form', anchor=F299_FORM), item('f236_application_reason', anchor=F299_FORM),
               item('overseas_criminal_record', anchor='② 해외범죄경력증명서',
                    notes_ko=['공적 확인(아포스티유 또는 영사확인)을 받은 자국 정부 발급 증명서로, 접수일 기준 6개월 이내 발급분이어야 합니다. 만 14세 미만 등 면제 기준이 있습니다.'],
                    notes_en=['A government-issued certificate with an apostille or consular confirmation, issued within 6 months; exemptions exist (e.g. under age 14).']),
               item('f236_livelihood_docs', anchor='③ 생계유지 능력 입증서류',
                    notes_ko=['신청일 당시 소득금액증명원을 낼 수 없으면 근로소득원천징수영수증, 해당 소득이 입금된 계좌 증빙, 사업자(고용주) 및 신청인 서약서〔서식 2〕를 모두 냅니다.'],
                    notes_en=['If the income certificate cannot be submitted, submit the withholding receipt, the account records showing the income and the employer\'s and applicant\'s pledge (form 2).']),
               item('f236_econ_activity_docs', anchor='④ 경제활동 지속 입증서류'),
               item('f236_basic_knowledge', anchor='⑤ 한국어와 한국문화에 대한 기본소양 입증서류'),
               item('f236_dwelling_proof', anchor='⑥ 부동산 임대차 계약서 등 체류지(주거지) 입증서류')],
         conditions_ko=['신청 가능한 체류자격: D-1, D-5, D-6, D-7, D-8(투자금 1억원 이상), D-9, E-6-1·3, E-1~E-5, E-7, F-1(국내 출생 대만화교에 한함), F-3-18(F-2-99 체류자의 배우자에 한함).',
                        '단기 사증, 기타(G-1), 관광취업(H-1) 자격자, 불법체류자, 출국을 위한 체류기간연장 또는 출국기한유예 중인 사람은 자격변경이 억제됩니다.',
                        '고시원·모텔 등 사회통념상 지속적인 장기 거주가 불가능한 장소를 체류지로 하면 자격변경이 억제됩니다.',
                        '기본소양: 사회통합프로그램 4단계 이상 이수, 사전평가 81점 이상, 국내 초·중·고교 또는 대학 졸업, 검정고시 합격 중 하나를 충족해야 합니다.',
                        '국내 출생 대만 화교, 국내 10년 이상 체류한 종교(D-6) 자격자로서 중앙행정기관 또는 지방자치단체 장의 추천을 받은 사람은 생계유지능력 심사가 면제됩니다.',
                        LAW_ABIDING_KO],
         conditions_en=['Eligible statuses: D-1, D-5, D-6, D-7, D-8 (investment of KRW 100 million+), D-9, E-6-1/3, E-1 to E-5, E-7, F-1 (Korea-born Taiwanese Chinese only), F-3-18 (spouses of F-2-99 holders only).',
                        'Change is withheld for short-term visa holders, G-1, H-1, people staying illegally, and those on a departure extension or departure deferral.',
                        'Change is withheld if the address is a place unsuitable for long-term living (e.g. gosiwon, motel).',
                        'Basic knowledge: social integration program level 4+, pre-assessment 81+, graduation from a Korean school or university, or a qualifying equivalency exam.',
                        'Korea-born Taiwanese Chinese and D-6 holders of 10+ years recommended by a central or local government head are exempt from the self-support check.',
                        LAW_ABIDING_EN],
         notes_ko=[OFFICER_NOTE_KO], notes_en=[OFFICER_NOTE_EN])

# ==========================================================================
# F-2 거주 — 체류기간 연장 (cells with no rule yet)
# ==========================================================================
guidance('F-2-8', 'extension', covers=['F-2-81'], section='거주(F-2) 체류기간 연장허가 — 4. 관광･휴양시설 투자자에 대한 체류기간연장',
         anchor='4. 관광･휴양시설 투자자에 대한 체류기간연장',
         summary_ko='관광·휴양시설 투자로 거주 자격을 받은 투자자와 동반가족은 투자 기준금액을 잠식하지 않은 상태로 투자를 유지하면 체류지 관할 관서에서 연장할 수 있습니다. 부동산 등기부등본 또는 회원확인서(5일 이내 발급)와 체류지 입증서류 등을 냅니다.',
         summary_en='Tourism-facility investors with residence status and their families can extend at the office for their address if the investment is kept without falling below the threshold. Submit the property register or membership confirmation (issued within 5 days), proof of residence, etc.',
         docs=base_stay(anchor='① 신청서(별지 34호 서식), 여권 및 외국인등록증, 수수료') + [
             item('f236_register_or_membership', anchor='② 부동산 등기부등본 또는 분양회사 발행 회원확인서'),
             item('f236_move_in_list', 'CONDITIONAL_REQUIRED', anchor='③ 해당주택 전입세대 열람내역', applies_when_ko='미분양주택 투자자에 한함', applies_when_en='Unsold-house investors only'),
             item('f236_family_cert_extension', 'CONDITIONAL_REQUIRED', anchor='④ 가족관계 증명서(배우자 또는 미혼자녀의 체류기간 연장신청 시에 한함)',
                  applies_when_ko='배우자 또는 미혼자녀의 연장신청 시(성년자녀는 미혼임을 확인하는 서류)', applies_when_en='Spouse or unmarried child extending (adult children: proof of being unmarried)'),
             item('f236_corp_status_maintained', 'CONDITIONAL_REQUIRED', anchor='⑤ 법인의 임원, 주주의 경우 자격변경 당시의 법인 임원, 주주의 지위를 계속 유지하고 있음을 입증하는 서류', **F28_CORP),
             residence(anchor='⑥ 체류지 입증서류(임대차계약서, 숙소제공 확인서, 체류기간 만료예고 통지우편물, 공공요금 납부영수증, 기숙사비 영수증 등)'),
         ],
         conditions_ko=[LAW_ABIDING_EXT_KO], conditions_en=[LAW_ABIDING_EXT_EN],
         notes_ko=[OFFICER_NOTE_KO], notes_en=[OFFICER_NOTE_EN])

guidance('F-2-12', 'extension', covers=['F-2-13'], section='거주(F-2) 체류기간 연장허가 — 5. 공익사업투자 외국인에 대한 거주(F-2-12) 체류기간 연장허가',
         anchor='5. 공익사업투자 외국인에 대한 거주(F-2-12) 체류기간 연장허가',
         summary_ko='공익사업 투자로 거주 자격을 받은 투자자, 법인의 임원·주주와 그 배우자·미혼자녀는 투자 기준금액을 잠식하지 않은 상태로 투자를 유지하면, 체류기간 만료일 전에 체류지 관할 관서에서 연장을 신청할 수 있습니다. 손익발생형은 운영 손실이 나도 투자금을 회수하지 않는 한 투자를 유지한 것으로 봅니다.',
         summary_en='Public-interest investors, company officers and shareholders with residence status, and their spouses and unmarried children, can extend at the office for their address before their stay expires if the investment is kept without falling below the threshold. For the profit/loss type, operating losses do not count as withdrawal.',
         timing_ko='체류기간 만료일 전', timing_en='Before the stay expires',
         docs=[item('app_form_34', anchor='① 신청서(별지 제34호 서식), 여권(사본), 외국인등록증, 수수료'), item('passport_copy', anchor='① 신청서(별지 제34호 서식), 여권(사본), 외국인등록증, 수수료'),
               item('arc', anchor='① 신청서(별지 제34호 서식), 여권(사본), 외국인등록증, 수수료'), item('fee', anchor='① 신청서(별지 제34호 서식), 여권(사본), 외국인등록증, 수수료'),
               item('f236_investment_maintained', anchor='② 투자금을 유지하고 있음을 입증하는 서류'),
               item('f236_family_cert_companion', 'CONDITIONAL_REQUIRED', anchor='③ 가족관계증명서(동반가족의 경우)', applies_when_ko='동반가족의 경우', applies_when_en='Accompanying family members'),
               item('f236_corp_status_maintained', 'CONDITIONAL_REQUIRED', anchor='④ 법인의 임원, 주주의 경우 자격변경 당시의 법인 임원, 주주의 지위를 계속 유지하고 있음을 입증하는 서류', **F28_CORP),
               residence(anchor='⑤ 체류지 입증서류(임대차계약서, 숙소제공 확인서, 체류기간 만료예고 통지우편물, 공공요금 납부영수증, 기숙사비 영수증 등)')],
         conditions_ko=[LAW_ABIDING_EXT_KO], conditions_en=[LAW_ABIDING_EXT_EN],
         notes_ko=[OFFICER_NOTE_KO], notes_en=[OFFICER_NOTE_EN])

F26_FORM = '3. 제출 서류 ○ 여권, 사진 1매, 수수료, 신청서 및 신청사유서〔서식 1〕'
guidance('F-2-6', 'extension', section='거주(F-2) 체류기간 연장허가 — 6. 기타 장기체류자 【붙임 1】 숙련기능 거주 체류자격에 대한 체류기간 연장 심사 기준',
         anchor='숙련기능 거주 체류자격에 대한 체류기간 연장 심사 기준',
         summary_ko='숙련기능 거주(F-2-6) 체류자격은 2019-10-01 폐지되었습니다. 2019-10-04 이후 처음 연장을 신청하는 숙련기능 거주자는 최초 1회에 한해 이 기준으로 심사해 체류기간 2년을 일괄 부여하고, 허가되면 장기거주로 직권 정정됩니다. 2회 연장부터는 기타 장기체류자 연장 기준을 적용합니다.',
         summary_en='The F-2-6 skilled-worker residence status was abolished on 2019-10-01. Holders filing their first extension after 2019-10-04 are reviewed once under this standard and given two years; on approval the status is corrected to long-term residence. From the second extension the F-2-99 extension standard applies.',
         period_ko='2년 (최초 1회)', period_en='2 years (first extension only)',
         docs=[item('passport', anchor=F26_FORM), item('photo', anchor=F26_FORM), item('fee', anchor=F26_FORM), item('app_form', anchor=F26_FORM), item('f236_application_reason', anchor=F26_FORM),
               item('f236_deposit_2000', anchor='최근 1년 이상 2천만 원 이상의 예금잔고가 유지되었음을 증명할 수 있는 서류'),
               item('f236_past_employment', anchor='재직(경력)증명서 등 과거 취업활동 사실을 증명할 수 있는 서류',
                    notes_ko=['출입국관리정보시스템으로 확인할 수 있으면 면제할 수 있습니다.'], notes_en=['May be waived if it can be checked in the immigration system.']),
               item('f236_future_employment', anchor='취업예정사실증명서, 표준근로계약서 등')],
         conditions_ko=['중한범죄는 신청일 이전 10년 이내 1건도 없어야 하며(기소유예, 선고유예, 100만원 이하 벌금 포함), 세금은 완납해야 합니다.',
                        '신청인 또는 같은 체류지에서 생계를 같이하는 가족(배우자, 자녀, 배우자 부모까지)이 2천만원 이상의 자산을 보유해야 합니다.'],
         conditions_en=['No serious offence within 10 years before applying (suspended indictment, suspended sentence and fines up to KRW 1 million count), and all taxes paid.',
                        'You or family members sharing your household (spouse, children, spouse\'s parents) must hold assets of KRW 20 million or more.'],
         notes_ko=[OFFICER_NOTE_KO], notes_en=[OFFICER_NOTE_EN])

# ==========================================================================
# F-2 거주 — 체류자격외 활동 (summary only; the manual lists no documents)
# ==========================================================================
guidance('F-2-99', 'activities_outside_status', state='CONDITIONAL', completeness='SOURCE_ONLY',
         section='거주(F-2) 체류자격외 활동 — 1. 기타 장기체류자(F-2-99)의 체류자격외 활동허가 기준',
         anchor='1. 기타 장기체류자(F-2-99)의 체류자격외 활동허가 기준',
         summary_ko='기타 장기체류(F-2-99)자는 거주자격 취득 직전 체류자격 분야의 활동을 계속하면서 다른 취업활동을 하는 경우 체류자격외 활동허가가 필요 없습니다. 직전 분야 활동을 하지 않고 다른 취업활동을 하려는 경우, 또는 직전에 동반가족(배우자·미성년 자녀)으로서 F-2-99를 받은 사람이 취업하려는 경우에는 허가가 필요하며, 해당 취업활동 지침에 따라 결정하되 별도 규정이 없으면 허가합니다.',
         summary_en='F-2-99 holders who continue the activity of their previous status need no permission for other work. Permission is needed if they stop that activity and take other work, or if they received F-2-99 as an accompanying spouse or minor child and want to work; it is decided under the guideline for that work, and granted if that guideline has no specific rule.',
         notes_ko=['매뉴얼의 F-2-99 지침(취업활동 부분)은 직전 자격이 동반(F-3-18)이었던 사람은 취업 제한 분야를 제외하고 활동범위 제한 없이 취업할 수 있다고도 적고 있습니다. 두 설명이 다르므로 관할 관서에 확인하세요.'],
         notes_en=['The F-2-99 guideline\'s employment part also says that people whose previous status was F-3-18 may work without activity limits except in restricted fields. The two passages differ, so check with your immigration office.'])

guidance('F-2-71', 'activities_outside_status', state='CONDITIONAL', completeness='SOURCE_ONLY',
         section='거주(F-2) 체류자격외 활동 — 2. 점수이민제 우수인재(F-2-7)의 체류자격외 활동허가 기준',
         anchor='2. 점수이민제 우수인재(F-2-7)의 체류자격외 활동허가 기준',
         summary_ko='점수제 우수인재가 연간 소득요건을 충족하는 경우에 한해 동반가족도 거주가족(F-2-71)을 받은 뒤 출입국관리법 시행령 제23조제2항에 규정된 취업활동을 할 수 있습니다. 취업제한 분야나 국내 노동시장·사회경제질서에 부정적 영향을 미칠 수 있는 직종에 취업하면 체류기간 연장 제한 또는 체류허가 취소가 될 수 있습니다.',
         summary_en='Only when the points-system principal meets the annual income requirement may family members, after receiving F-2-71, take up the employment allowed by Art. 23(2) of the Enforcement Decree. Working in a restricted field or an occupation harmful to the labour market or socio-economic order can lead to a refused extension or cancelled permission.',
         conditions_ko=['우수인재가 소득요건을 충족하지 못하면 동반가족은 방문동거(F-1)로 체류할 수 있으나 취업과 각종 영리활동이 금지됩니다. 다만 외국어회화강사(E-2), 외국인학교교사(E-7), 교열요원(E-7) 요건을 갖추면 사전에 체류자격외 활동허가를 받아 취업할 수 있습니다.'],
         conditions_en=['If the principal does not meet the income requirement, family members may stay on F-1 but may not work or engage in profit-making; those qualifying as E-2 language instructors, E-7 foreign-school teachers or E-7 copy editors may work after prior permission.'])

# ==========================================================================
# F-2 거주 — 재입국허가
# ==========================================================================
REENTRY_DOCS = '신청서류 : 신청서(별지 34호서식), 여권 원본, 외국인등록증, 수수료'
REENTRY_MULTI = {'applies_when_ko': '복수재입국허가를 신청하는 경우', 'applies_when_en': 'When applying for a multiple re-entry permit'}


def f236_reentry(code, chapter_ko):
    guidance(code, 'reentry', section=f'{chapter_ko} 재입국허가', anchor='출국 후 체류기간 범위 내에서 1년을 초과하여 2년 내에 재입국을 하려는 경우',
             summary_ko='외국인등록을 마친 사람이 출국한 날부터 1년 이내(남은 체류기간이 1년보다 짧으면 체류기간 범위 내)에 재입국하면 재입국허가가 면제됩니다. 체류기간 범위 내에서 1년을 넘겨 2년 안에 재입국하려면 복수재입국허가를 신청합니다.',
             summary_en='Registered foreigners who return within one year of leaving (or within their remaining stay if shorter) are exempt from a re-entry permit. To return after more than one year but within two years (within the stay period), apply for a multiple re-entry permit.',
             docs=[item('app_form_34', anchor=REENTRY_DOCS, **REENTRY_MULTI), item('passport_original', anchor=REENTRY_DOCS, **REENTRY_MULTI),
                   item('arc', anchor=REENTRY_DOCS, **REENTRY_MULTI), item('fee', anchor=REENTRY_DOCS, **REENTRY_MULTI)],
             conditions_ko=['입국규제 및 사증발급규제자는 체류지 관할 청(사무소·출장소)에 방문하여 재입국허가를 받아야 합니다.',
                            '사우디아라비아, 이란, 리비아 국민은 복수재입국이 제한됩니다(이들 국가 국민 중 결혼이민(F-6), 유학(D-2), 일반연수(D-4)는 가능).'],
             conditions_en=['People under an entry or visa restriction must obtain a re-entry permit in person at the office for their address.',
                            'Nationals of Saudi Arabia, Iran and Libya cannot get a multiple re-entry permit (except F-6, D-2 and D-4 holders).'],
             notes_ko=[OFFICER_NOTE_KO], notes_en=[OFFICER_NOTE_EN])


f236_reentry('F-2', '거주(F-2)')

# ==========================================================================
# F-3 동반 — 사증 (visa manual)
# ==========================================================================
F3_VISA_SEC = '사증발급 안내매뉴얼 동반(F-3) — 공관장 재량으로 발급할 수 있는 사증'
F3_DOC_RULES_KO = ['가족관계 입증서류: 배우자는 본국의 결혼증명서 원본(공적 서류 입증 필수) 등(중국은 거민신분증, 결혼증, 호구부 등), 미성년 자녀는 본국의 출생증명서 원본, 국내 출생증명서(대한민국 내 출생 시), 본국의 가족관계증명서 등 친자관계 입증서류(중국은 거민신분증, 결혼증, 호구부 등)를 냅니다.',
                   '본국의 공적 서류는 번역자 확인서를 첨부하고, 협약국이면 아포스티유, 미체약국이면 주재국 대한민국 공관의 영사확인을 받아야 합니다.']
F3_DOC_RULES_EN = ['Family-relation proof: for a spouse, the original home-country marriage certificate (officially certified) etc. (China: resident ID, marriage certificate, hukou); for a minor child, the original home-country birth certificate, a Korean birth certificate (if born in Korea), or a home-country family-relation certificate (China: resident ID, marriage certificate, hukou).',
                   'Home-country official documents need a translator\'s confirmation, plus an apostille (Convention countries) or Korean consular confirmation (other countries).']
F3_LIVELIHOOD_EXEMPT_KO = 'E-1, E-3, E-4, E-5, F-4, H-2, E-7-T, E-7-S1, 기업투자(D-8) 자격 중 50만 불 이상 고액투자자의 가족은 제출 면제'
F3_LIVELIHOOD_EXEMPT_EN = 'Waived for families of E-1, E-3, E-4, E-5, F-4, H-2, E-7-T, E-7-S1 and D-8 investors of USD 500,000+'

guidance('F-3', 'visa_issuance', manual=VISA, section=F3_VISA_SEC + ' 1. 동반가족 단수사증',
         anchor='배우자가 없는 자에 대한 체류기간 1년 이하의 단수사증에 대한 체류기간 1년 이하의 단수사증',
         summary_ko='문화예술(D-1)·유학(D-2)·일반연수(D-4)부터 특정활동(E-7)까지, 거주(F-2), 재외동포(F-4), 방문취업(H-2) 자격자의 배우자와 (배우자가 없는) 미성년 자녀는 재외공관에서 체류기간 1년 이하의 동반(F-3) 단수사증을 받을 수 있습니다. 가족관계 입증서류, 생계유지능력 입증서류, 신원보증서, 주거지 입증서류를 냅니다.',
         summary_en='Spouses and unmarried minor children of holders of D-1, D-2, D-4 through E-7, F-2, F-4 or H-2 can get a single-entry F-3 visa for a stay of up to one year at a Korean mission. Submit proof of family relationship, proof of financial capacity, a letter of guarantee and proof of residence.',
         docs=f236_visa_base() + [
             item('f236_family_relation_mb', anchor='② 가족관계입증서류(결혼 또는 출생증명서 등)'),
             item('f236_livelihood_inviter', 'CONDITIONAL_REQUIRED', anchor='③ 생계유지능력 입증서류 (E-1, E-3, E-4, E-5, F-4, H-2의 경우 제출 면제)',
                  does_not_apply_when_ko=F3_LIVELIHOOD_EXEMPT_KO, does_not_apply_when_en=F3_LIVELIHOOD_EXEMPT_EN,
                  notes_ko=['납세사실증명서 제출이 곤란한 경우(예: 일부 D계열, 주된 체류자격자와 동반 신청하는 경우) 기타 재정입증서류로 갈음합니다.'], notes_en=['If a tax-payment certificate is hard to obtain (e.g. some D statuses, or applying together with the principal), other financial proof may be used.']),
             item('guarantor', anchor='④ 신원보증서'),
             item('f236_dwelling_residence', 'CONDITIONAL_REQUIRED', anchor='⑤ 체류지 등 주거지 입증서류', does_not_apply_when_ko=F3_LIVELIHOOD_EXEMPT_KO, does_not_apply_when_en=F3_LIVELIHOOD_EXEMPT_EN),
         ],
         conditions_ko=F3_DOC_RULES_KO + ['취재(D-5) 자격자의 동반 입국자에 대한 동반(F-3) 사증은 국내 지사(국)가 개설되어 있어야 발급합니다.', '기술연수(D-3) 자격자의 가족은 동반(F-3) 대상이 아닙니다.'],
         conditions_en=F3_DOC_RULES_EN + ['F-3 visas for families of D-5 journalists require a branch office (bureau) in Korea.', 'Families of D-3 trainees are not eligible for F-3.'],
         notes_ko=[OFFICER_NOTE_VISA_KO], notes_en=[OFFICER_NOTE_VISA_EN])

guidance('F-3-19', 'visa_issuance', manual=VISA, section=F3_VISA_SEC + ' 2. 재외동포(F-4) 자격을 취득한 자의 가족',
         anchor='재외동포(F-4) 자격을 취득한 자의 가족에 대한 1년간 유효한 동반(F-3-19, 01년) 복수사증',
         summary_ko='재외동포(F-4) 자격을 취득한 사람의 배우자와 미성년 자녀는 1년간 유효한 동반(F-3-19) 복수사증을 받을 수 있습니다. 재외동포의 국내거소신고증 또는 사증발급 사항 사본과 가족관계 입증서류를 냅니다.',
         summary_en='Spouses and minor children of F-4 holders can get a one-year multiple-entry F-3-19 visa. Submit the F-4 holder\'s domestic residence report card or a copy of their visa details and proof of family relationship.',
         docs=f236_visa_base() + [item('f236_f4_card_or_visa', anchor='② 재외동포(F-4) 자격을 취득한 사람의 국내거소신고증 또는'),
                                  item('family_relation', anchor='③ 가족관계 입증서류')],
         notes_ko=['이 절의 본문은 "방문동거(F-3-19, 01년) 복수사증 발급"이라고도 적고 있습니다.', OFFICER_NOTE_VISA_KO],
         notes_en=['The body of this section also calls it a "visiting-cohabitation (F-3-19, 1 year) multiple-entry visa".', OFFICER_NOTE_VISA_EN])

guidance('F-3-20', 'visa_issuance', manual=VISA, section=F3_VISA_SEC + ' 3. 방문취업(H-2) 자격을 취득한 자의 가족',
         anchor='방문취업(H-2) 자격을 취득한 자의 가족에 대한 1년간 유효한 동반(F-3-20, 090일) 복수사증',
         summary_ko='방문취업(H-2) 자격을 취득한 사람의 배우자와 미성년 자녀는 1년간 유효한 동반(F-3-20, 90일) 복수사증을 받을 수 있습니다. 방문취업자의 외국인등록증 또는 사증발급 사항 사본과 가족관계 입증서류를 냅니다.',
         summary_en='Spouses and minor children of H-2 holders can get a one-year multiple-entry F-3-20 visa (90-day stays). Submit the H-2 holder\'s residence card or a copy of their visa details and proof of family relationship.',
         docs=f236_visa_base() + [item('f236_h2_card_or_visa', anchor='② 방문취업(H-2) 자격을 취득한 사람의 외국인등록증 또는'),
                                  item('family_relation', anchor='③ 가족관계 입증서류')],
         notes_ko=['이 절의 본문은 "방문동거(F-3-20, 090일) 복수사증 발급"이라고도 적고 있습니다.', OFFICER_NOTE_VISA_KO],
         notes_en=['The body of this section also calls it a "visiting-cohabitation (F-3-20, 90 days) multiple-entry visa".', OFFICER_NOTE_VISA_EN])

guidance('F-3-18', 'visa_issuance', manual=VISA, section=F3_VISA_SEC + ' 2. 점수제 우수인재(F-2-7)의 배우자 및 미성년자녀에 대한 90일간 유효한 단수사증(F-3-18)',
         anchor='점수제 우수인재(F-2-7)의 배우자 및 미성년자녀에 대한  90일간 유효한 단수사증(F-3-18)',
         summary_ko='점수제 우수인재(F-2-7) 주체류자의 법률상 배우자와 미성년 자녀는 재외공관에서 90일간 유효한 동반(F-3-18) 단수사증을 받을 수 있습니다. 주체류자의 고용·소득·학위 서류, 가족관계 소명 서류, 점수표와 항목별 점수 소명서류, 체류지 입증서류를 냅니다.',
         summary_en='The legal spouse and minor children of an F-2-7 principal can get a 90-day single-entry F-3-18 visa at a Korean mission. Submit the principal\'s employment, income and degree documents, proof of the family relationship, the points table with evidence, and proof of residence.',
         docs=[item('f236_visa_form17', anchor='① 사증발급신청서 (별지 제17호 서식), 여권, 외국인등록증(주체류자가 외국인등록을 마친 사람만 해당), 표준규격사진 1매'),
               item('passport', anchor='① 사증발급신청서 (별지 제17호 서식), 여권, 외국인등록증(주체류자가 외국인등록을 마친 사람만 해당), 표준규격사진 1매'),
               item('f236_principal_arc_if_registered', 'CONDITIONAL_REQUIRED', anchor='① 사증발급신청서 (별지 제17호 서식), 여권, 외국인등록증(주체류자가 외국인등록을 마친 사람만 해당), 표준규격사진 1매',
                    applies_when_ko='주체류자가 외국인등록을 마친 경우', applies_when_en='If the principal holder has registered'),
               item('photo', anchor='① 사증발급신청서 (별지 제17호 서식), 여권, 외국인등록증(주체류자가 외국인등록을 마친 사람만 해당), 표준규격사진 1매'),
               item('tb_cert', anchor=F2_CVI_TB),
               item('f236_principal_employment_docs_copy', anchor='③ 주체류자의 고용계약서 사본, 재직증명서, 사업자등록증, 법인등기부등본, 소득금액증명'),
               item('f236_family_relation_principal', anchor='④ 가족관계 소명 서류(주체류자와의 법률상 가족관계 입증서류여야 함)'),
               item('f236_points_table', anchor='⑤ 점수제 평가를 위한 점수를 기재한 점수표'),
               item('f236_points_proof_self', anchor='⑥ 신청인 본인이 기재한 평가 항목별 점수를 소명하는 서류'),
               item('residence_proof', anchor='⑦ 체류지 입증서류'),
               item('f236_examiner_requested', 'MAY_BE_REQUESTED_BY_OFFICER', anchor='⑧ 심사관이 추가 제출을 요구한 서류')],
         conditions_ko=['주체류자는 상장법인·유망산업분야·전문직 종사자 또는 유학인재로서 점수제 평가항목 합산 80점 이상을 검증받고 F-2-7 자격을 받은 사람입니다(F-2-71은 대상 아님).',
                        '배우자는 법률상 배우자로서 진정한 혼인관계를 유지해야 하며(사실혼 불인정), 미성년 자녀는 주체류자가 친권과 양육권을 가지고 있어야 합니다.',
                        '구체적인 내용은 「점수제 우수인재 거주(F-2) 체류자격 사증 및 체류관리 지침」에 따릅니다.'],
         conditions_en=['The principal works for a listed company, in a promising industry or a profession, or is a Korean-educated graduate, verified at 80+ points and holding F-2-7 (not F-2-71).',
                        'The spouse must be a legal spouse in a genuine marriage (de facto not accepted); for minor children the principal must hold parental authority and custody.',
                        'Details follow the points-system F-2 visa and stay guideline.'],
         notes_ko=[OFFICER_NOTE_VISA_KO], notes_en=[OFFICER_NOTE_VISA_EN])

guidance('F-3', 'visa_issuance_confirmation', manual=VISA, section='사증발급 안내매뉴얼 동반(F-3) — 사증발급인정서 발급대상 1.',
         anchor='원칙적으로 동반하는 본인(원자격자)과 함께 사증발급인정신청을 하는 경우에 한하여 사증발급인정서 발급',
         summary_ko='D-1, D-2, D-4부터 E-7까지, F-2, F-4, H-2 자격자의 배우자와 (배우자가 없는) 미성년 자녀에 대한 동반(F-3) 사증발급인정서는 원칙적으로 동반하는 본인(원자격자)과 함께 신청하는 경우에만 발급합니다. 가족관계 입증서류, 생계유지능력 입증서류, 신원보증서, 체류지 입증서류를 냅니다.',
         summary_en='An F-3 confirmation of visa issuance for spouses and unmarried minor children of D-1, D-2, D-4 to E-7, F-2, F-4 or H-2 holders is in principle issued only when filed together with the principal. Submit proof of family relationship, proof of financial capacity, a letter of guarantee and proof of residence.',
         docs=[item('f236_cvi_form21', anchor='① 사증발급인정신청서 (별지 제21호 서식), 여권사본, 표준규격사진 1매'),
               item('passport_copy', anchor='① 사증발급인정신청서 (별지 제21호 서식), 여권사본, 표준규격사진 1매'),
               item('photo', anchor='① 사증발급인정신청서 (별지 제21호 서식), 여권사본, 표준규격사진 1매'),
               item('f236_family_relation_mb', anchor='② 가족관계입증서류(결혼 또는 출생증명서 등)'),
               item('f236_livelihood_inviter', 'CONDITIONAL_REQUIRED', anchor='③ 생계유지능력 입증서류 (E-1, E-3, E-4, E-5, F-4, H-2의 경우 제출 면제)',
                    does_not_apply_when_ko='E-1, E-3, E-4, E-5, F-4, H-2 자격자의 가족은 제출 면제', does_not_apply_when_en='Waived for families of E-1, E-3, E-4, E-5, F-4 and H-2 holders',
                    notes_ko=['납세사실증명서 제출이 곤란한 경우 기타 재정입증서류로 갈음합니다.'], notes_en=['Other financial proof may replace a tax-payment certificate that is hard to obtain.']),
               item('guarantor', anchor='④ 신원보증서'),
               item('residence_proof', 'CONDITIONAL_REQUIRED', anchor='⑤ 체류지 입증서류 (E-1, E-3, E-4, E-5, F-4, H-2의 경우 제출 면제)',
                    does_not_apply_when_ko='E-1, E-3, E-4, E-5, F-4, H-2 자격자의 가족은 제출 면제', does_not_apply_when_en='Waived for families of E-1, E-3, E-4, E-5, F-4 and H-2 holders')],
         conditions_ko=F3_DOC_RULES_KO, conditions_en=F3_DOC_RULES_EN,
         notes_ko=[CVI_NOTE_KO], notes_en=[CVI_NOTE_EN])

guidance('F-3', 'electronic_visa', manual=VISA, state='CONDITIONAL', completeness='SOURCE_ONLY', section='사증발급 안내매뉴얼 동반(F-3) — 전자사증',
         anchor='교수(E-1), 연구(E-3), 기술지도(E-4), 전문직업(E-5) 및 첨단과학기술분야 고용추천서(GOLD CARD)를 발급받은 특정활동(E-7) 자격 외국인의 배우자 및 미성년 자녀로서 배우자가 없는 사람',
         summary_ko='전문 인력의 동반자, 곧 교수(E-1)·연구(E-3)·기술지도(E-4)·전문직업(E-5) 및 첨단과학기술분야 고용추천서(GOLD CARD)를 받은 특정활동(E-7) 외국인의 배우자와 (배우자가 없는) 미성년 자녀, 그리고 첨단분야 최우수인재(E-7-T)의 배우자와 미성년 자녀는 전자사증으로 신청할 수 있습니다. 제출서류는 동반(F-3) 자격 사증발급 심사 기준에 따릅니다.',
         summary_en='Dependants of professionals — spouses and unmarried minor children of E-1, E-3, E-4, E-5 holders and of E-7 holders with a GOLD CARD employment recommendation, and spouses and minor children of E-7-T — can apply for an electronic visa. Documents follow the F-3 visa issuance standard.')

# ==========================================================================
# F-3 동반 — 체류 (stay manual)
# ==========================================================================
F3_BASE_PHOTO = '① 신청서(별지 34호 서식), 여권, 표준규격사진 1매, 수수료'
F3_STAY_DOC_RULES_KO = ['가족관계 입증서류 제출 기준: 본국의 출생증명서 원본(공적 서류 입증 필수) 등, 국내 출생증명서(대한민국 내 출생 시), 본국의 가족관계증명서 등 친자관계 입증서류, 중국은 거민신분증·결혼증·호구부 등.',
                        '본국의 공적 서류는 번역자 확인서를 첨부하고, 협약국이면 아포스티유, 미체약국이면 주재국 대한민국 공관의 영사확인을 받아야 합니다.']
F3_STAY_DOC_RULES_EN = ['Family-relation proof: original home-country birth certificate (officially certified), Korean birth certificate (if born in Korea), home-country family-relation certificate or other proof of parentage; China: resident ID, marriage certificate, hukou.',
                        'Home-country official documents need a translator\'s confirmation, plus an apostille (Convention countries) or Korean consular confirmation (other countries).']

guidance('F-3', 'status_grant', section='동반(F-3) 체류자격 부여', anchor='② 부 또는 모의 외국인등록증',
         summary_ko='동반(F-3) 체류자격 부여는 신청서·여권·사진·수수료와 부 또는 모의 외국인등록증, 신원보증서, 가족관계 입증서류를 내고 신청합니다.',
         summary_en='For an F-3 status grant, submit the form, passport, photo, fee, the parent\'s residence card, a letter of guarantee and proof of family relationship.',
         docs=f236_stay_base(F3_BASE_PHOTO) + [item('f236_parent_arc', anchor='② 부 또는 모의 외국인등록증'), item('guarantor', anchor='③ 신원보증서'), item('family_relation', anchor='④ 가족관계 입증서류')],
         conditions_ko=F3_STAY_DOC_RULES_KO, conditions_en=F3_STAY_DOC_RULES_EN,
         notes_ko=[OFFICER_NOTE_KO], notes_en=[OFFICER_NOTE_EN])

guidance('F-3', 'status_change', section='동반(F-3) 체류자격 변경허가',
         anchor='국내 입국 후 임신·출산·양육·질병 등 사정변경으로 인한 인도적 고려가 필요한 자 중 아래에 해당하는 자에 한함',
         summary_ko='동반(F-3)으로의 자격변경은 국내 입국 후 임신·출산·양육·질병 등 사정변경으로 인도적 고려가 필요한 사람 중 사증면제(B-1)·관광통과(B-2)·단기사증으로 입국한 사람 또는 국내 합법 장기체류 외국인에 한합니다. 가족관계 입증서류, 재정능력 입증서류, 체류지 입증서류, 신원보증서, 변경 사유서를 내고, 주자격자의 외국인등록증을 추가로 냅니다.',
         summary_en='A change to F-3 is limited to people who, after entering Korea, need humanitarian consideration because of pregnancy, birth, childcare, illness or similar changes, and who entered visa-free (B-1), in transit (B-2) or on a short-term visa, or are lawful long-term residents. Submit proof of family relationship, financial capacity and residence, a guarantee and a statement of reasons, plus the principal holder\'s residence card.',
         docs=f236_stay_base(F3_BASE_PHOTO) + [
             item('f236_family_relation_mb', anchor='② 가족관계입증서류(결혼 또는 출생증명서 등)'),
             item('f236_stay_finance', anchor='③ 체류경비 등 재정능력 입증서류'),
             item('residence_proof', anchor='③ 체류지 입증서류'),
             item('guarantor', anchor='④ 신원보증서'),
             item('f236_change_reason', anchor='⑤ 체류자격 변경 사유서 및 관련 증빙 서류'),
             item('f236_principal_arc', 'ADDITIONAL_IF_APPLICABLE', anchor='⑥ 주자격자(배우자 또는 부모)의 외국인등록증', applies_when_ko='추가서류', applies_when_en='Additional document'),
         ],
         conditions_ko=['배우자의 가족관계 입증: 본국의 결혼증명서 원본(공적 서류 입증 필수) 등, 중국은 거민신분증·결혼증·호구부 등. 미성년 자녀: 본국의 출생증명서 원본, 국내 출생증명서(대한민국 내 출생 시), 본국의 가족관계증명서 등 친자관계 입증서류.',
                        F3_STAY_DOC_RULES_KO[1]],
         conditions_en=['Spouses: original home-country marriage certificate (officially certified) etc.; China: resident ID, marriage certificate, hukou. Minor children: original home-country birth certificate, Korean birth certificate (if born in Korea), or home-country proof of parentage.',
                        F3_STAY_DOC_RULES_EN[1]],
         notes_ko=['방문취업(H-2)·재외동포(F-4) 자격자의 가족(F-3-19, F-3-20)은 별도 안내를 따릅니다.', OFFICER_NOTE_KO],
         notes_en=['Families of H-2 and F-4 holders (F-3-19, F-3-20) follow their own guidance.', OFFICER_NOTE_EN])

guidance('F-3-19', 'status_change', covers=['F-3-20'], section='동반(F-3) 체류자격 변경허가 — 2. 방문취업(H-2), 재외동포(F-4) 자격자의 배우자 및 미성년자녀(F-3-19, F-3-20)',
         anchor='2. 방문취업(H-2), 재외동포(F-4) 자격자의 배우자 및 미성년자녀에 대한 방문동거 체류자격 변경허가(F-3-19, F-3-20)',
         summary_ko='국내에 합법체류 중인 방문취업(H-2) 자격자의 배우자·미성년 자녀는 방문취업자의 체류기간까지, 재외동포(F-4) 자격자의 미성년 자녀는 25세까지(혼인한 자녀 제외) 체류허가를 받을 수 있습니다. 신청서·여권·사진·수수료, 가족관계 입증서류(출생증명서, 호구부 등), 부 또는 모의 외국인등록증을 냅니다.',
         summary_en='Spouses and minor children of H-2 holders lawfully in Korea can be permitted to stay until the H-2 holder\'s stay ends, and minor children of F-4 holders until age 25 (not if married). Submit the form, passport, photo, fee, proof of family relationship (birth certificate, hukou, etc.) and the parent\'s residence card.',
         docs=f236_stay_base('① 신청서(별지 제34호 서식), 여권, 표준규격사진 1매, 수수료') + [
             item('f236_family_birth_hukou', anchor='② 가족관계 입증서류 (출생증명서, 호구부 등)'),
             item('f236_parent_arc', anchor='③ 부 또는 모의 외국인등록')],
         notes_ko=['이 절의 제목은 F-3-19, F-3-20으로의 변경허가이지만, 본문은 "방문동거(F-1) 자격으로 체류허가"라고 적고 있습니다. 어느 자격이 부여되는지는 관할 관서에 확인하세요.', OFFICER_NOTE_KO],
         notes_en=['The section heading names F-3-19 and F-3-20, but the body says the stay is permitted "as visiting cohabitation (F-1)". Check with the immigration office which status is granted.', OFFICER_NOTE_EN])

# F-3-18 for dependants of F-2-99 holders (기타 장기체류자 지침 — 동반가족 체류 관리)
F318_COMMON = '① 공통서류(신청서, 표준규격 사진, 여권 사본, 체류지 입증서류, 수수료 등)'
F318_SCOPE_KO = '이 안내는 매뉴얼의 기타 장기(F-2-99) 지침 중 동반가족 체류 관리 부분을 옮긴 것으로, 주 자격자가 기타 장기(F-2-99) 자격자인 경우에 해당합니다.'
F318_SCOPE_EN = 'This is transcribed from the F-2-99 guideline\'s section on accompanying family and applies when the principal holds F-2-99.'
guidance('F-3-18', 'status_change', section='거주(F-2) 기타 장기체류자 지침 — 라. 동반가족 — 동반가족 체류 관리(체류자격 변경)',
         anchor='③ 주 자격자의 기타 장기(F-2-99) 체류자격 변경요건 충족 여부',
         summary_ko='기타 장기(F-2-99) 자격자의 배우자와 미성년 자녀는 체류허가 제한 대상이 아니고, 혼인이 진정하며 당사국 법령에 따라 성립했고, 주 자격자가 F-2-99 변경요건을 충족하면 동반(F-3-18)으로 바꿀 수 있습니다. 체류기간은 주 자격자와 같게 부여합니다.',
         summary_en='The spouse and minor children of an F-2-99 holder can change to F-3-18 if they are not subject to stay restrictions, the marriage is genuine and valid under the relevant law, and the principal meets the F-2-99 change requirements. The period matches the principal\'s.',
         docs=[item('f236_common_docs_f3', anchor=F318_COMMON), item('f236_principal_passport_arc', anchor='② 주 자격자의 여권 사본 및 외국인등록증'),
               item('f236_principal_requirement_proof', anchor='③ 주 자격자의 자격변경 요건 충족 입증서류'),
               item('f236_home_family_proof', anchor='④ 본국 정부 발급 가족관계 입증서류(혼인관계 증명서, 가족관계 증명서)')],
         conditions_ko=[F318_SCOPE_KO, '배우자는 국내 법령상 배우자로 인정될 수 있는 법률상 배우자에 한하며(동성·사실혼 배우자 제외, 일부다처제 국가라도 1인만 인정), 자녀는 주 자격자가 친권과 양육권을 가진 미혼 미성년 자녀입니다.'],
         conditions_en=[F318_SCOPE_EN, 'Spouses must be legal spouses recognised under Korean law (no same-sex or de facto spouses; one spouse only even where polygamy is allowed); children must be unmarried minors over whom the principal holds parental authority and custody.'],
         notes_ko=[OFFICER_NOTE_KO], notes_en=[OFFICER_NOTE_EN])

guidance('F-3-18', 'status_grant', section='거주(F-2) 기타 장기체류자 지침 — 라. 동반가족 — 동반가족 체류 관리(체류자격 부여)',
         anchor='(대상자) 기타 장기(F-2-99) 자격자의 국내 출생 자녀',
         summary_ko='기타 장기(F-2-99) 자격자의 국내 출생 자녀는 공통서류, 주 자격자의 여권 사본과 외국인등록증, 출생증명서 등 가족관계 입증서류를 내고 주 자격자와 같은 체류기간의 동반(F-3-18) 자격을 받습니다.',
         summary_en='A Korea-born child of an F-2-99 holder is granted F-3-18 for the same period as the principal with the common documents, the principal\'s passport copy and residence card, and a birth certificate or other proof of family relationship.',
         docs=[item('f236_common_docs_f3', anchor=F318_COMMON), item('f236_principal_passport_arc', anchor='② 주 자격자의 여권 사본 및 외국인등록증'),
               item('f236_birth_family_proof', anchor='③ 출생증명서 등 가족관계 입증서류')],
         conditions_ko=[F318_SCOPE_KO], conditions_en=[F318_SCOPE_EN],
         notes_ko=[OFFICER_NOTE_KO], notes_en=[OFFICER_NOTE_EN])

F3_PRO = {'applies_when_ko': '전문인력 등 배우자 자격외 활동(1.)', 'applies_when_en': 'Spouses of professionals etc. (section 1)'}
F3_LABOR = {'applies_when_ko': '단순노무분야(H-2 취업범위 중 농업·임업·축산업) 활동 시', 'applies_when_en': 'Simple labour (agriculture, forestry, livestock within the H-2 scope)'}
F3_EDIT = {'applies_when_ko': '국가기관·공공단체의 외국어교열요원(E-7) 활동(3.)', 'applies_when_en': 'Foreign-language copy editor (E-7) at a state agency or public body (section 3)'}
F3_TEACH = {'applies_when_ko': '외국어회화강사(E-2)·외국인학교교사(E-7) 활동(4.)', 'applies_when_en': 'Foreign-language instructor (E-2) or foreign-school teacher (E-7) (section 4)'}
F3_E2 = {'applies_when_ko': '외국어회화강사(E-2) 활동(4.)', 'applies_when_en': 'Foreign-language instructor (E-2) (section 4)'}
F3_E7T = {'applies_when_ko': '외국인학교교사(E-7) 활동(4.)', 'applies_when_en': 'Foreign-school teacher (E-7) (section 4)'}
F3_SPECIAL = {'applies_when_ko': '우수인재 배우자 특례의 최초 포괄허가(5.)', 'applies_when_en': 'First blanket permission under the talent-spouse special rule (section 5)'}
F3_ACT_BASE = '① 신청서(별지 34호 서식), 여권 및 외국인등록증, 수수료'
guidance('F-3', 'activities_outside_status', state='CONDITIONAL', completeness='PARTIALLY_STRUCTURED', doc_page_window=3,
         section='동반(F-3) 체류자격외 활동', anchor='1. 전문인력 등 배우자에 대한 자격 외 활동허가',
         summary_ko='동반(F-3) 자격자의 체류자격외 활동은 매뉴얼이 정한 경우에 허가됩니다: 전문인력(E-1~E-5, E-6-2 제외 E-6, E-7) 및 F-2·F-4·H-2 자격자의 성년 배우자의 전문직종·단순노무(농업·임업·축산업) 활동, 국가기관 등의 외국어교열요원(E-7), 외국어회화강사(E-2)·외국인학교교사(E-7), 그리고 시범운영 중인 우수인재 배우자 특례. 정규교육기관(초·중·고 및 대학) 교육은 별도 허가가 필요 없습니다.',
         summary_en='F-3 holders may be permitted outside activities in the cases the manual sets out: professional or simple-labour (agriculture, forestry, livestock) work by adult spouses of professionals (E-1 to E-5, E-6 except E-6-2, E-7) and of F-2, F-4 and H-2 holders; foreign-language copy editing (E-7) at state bodies; E-2 language instruction or E-7 foreign-school teaching; and the pilot talent-spouse special rule. Study at regular schools and universities needs no permission.',
         docs=[item('f236_rule76_docs', 'SOURCE_MENTIONS_BUT_NOT_STRUCTURED', anchor='라. 제출서류 : 규칙 제76조에 의한 체류자격별 첨부서류(신원보증서 생략)', **F3_PRO,
                    notes_ko=['특정활동(E-7)에 종사하려면 E-7 자격 사증발급인정서 발급 지침을 준용합니다.'], notes_en=['For E-7 work the E-7 confirmation-of-visa-issuance guideline applies.']),
               item('f236_standard_contract', 'CONDITIONAL_REQUIRED', anchor='① 표준근로계약서 ② 사업자 등록증 또는 법인등기부등본', **F3_LABOR),
               item('f236_bizreg_or_corpreg', 'CONDITIONAL_REQUIRED', anchor='② 사업자 등록증 또는 법인등기부등본', **F3_LABOR),
               item('f236_employer_id_copy', 'CONDITIONAL_REQUIRED', anchor='③ 고용주 신분증 사본', **F3_LABOR),
               item('f236_korean_topik2', 'CONDITIONAL_REQUIRED', anchor='④ 한국어능력 증빙서류(TOPIK 2급 또는 사회통합프로그램 2급 이상)', **F3_LABOR),
               item('f236_early_adaptation_proof', 'ADDITIONAL_IF_APPLICABLE', anchor='⑤ 조기적응프로그램 이수 증빙서류', **F3_LABOR),
               item('app_form_34', 'CONDITIONAL_REQUIRED', anchor=F3_ACT_BASE, applies_when_ko='외국어교열요원(E-7) 또는 외국어회화강사(E-2)·외국인학교교사(E-7) 활동(3.·4.)', applies_when_en='Sections 3 and 4'),
               item('passport', 'CONDITIONAL_REQUIRED', anchor=F3_ACT_BASE, applies_when_ko='외국어교열요원(E-7) 또는 외국어회화강사(E-2)·외국인학교교사(E-7) 활동(3.·4.)', applies_when_en='Sections 3 and 4'),
               item('arc', 'CONDITIONAL_REQUIRED', anchor=F3_ACT_BASE, applies_when_ko='외국어교열요원(E-7) 또는 외국어회화강사(E-2)·외국인학교교사(E-7) 활동(3.·4.)', applies_when_en='Sections 3 and 4'),
               item('fee', 'CONDITIONAL_REQUIRED', anchor=F3_ACT_BASE, applies_when_ko='외국어교열요원(E-7) 또는 외국어회화강사(E-2)·외국인학교교사(E-7) 활동(3.·4.)', applies_when_en='Sections 3 and 4'),
               item('employment_contract', 'CONDITIONAL_REQUIRED', anchor='② 고용계약서 ③ 사업자등록증 사본 ④ 추천서(해당 기관장)', **F3_EDIT),
               item('business_reg_copy', 'CONDITIONAL_REQUIRED', anchor='③ 사업자등록증 사본 ④ 추천서(해당 기관장)', **F3_EDIT),
               item('f236_agency_recommendation', 'CONDITIONAL_REQUIRED', anchor='④ 추천서(해당 기관장)', **F3_EDIT),
               item('f236_degree_orig_copy', 'CONDITIONAL_REQUIRED', anchor='⑤ 학위증(원본 및 사본)', **F3_EDIT),
               item('employment_contract', 'CONDITIONAL_REQUIRED', anchor='② 고용계약서 ③ 사업자등록증', **F3_TEACH),
               item('business_reg', 'CONDITIONAL_REQUIRED', anchor='② 고용계약서 ③ 사업자등록증', **F3_TEACH),
               item('f236_degree_e2', 'CONDITIONAL_REQUIRED', anchor='④ 학위증(E-2 자격요건과 동일)', **F3_E2),
               item('f236_crime_record_e2', 'CONDITIONAL_REQUIRED', anchor='⑤ 범죄경력증명서(E-2 자격요건과 동일)', **F3_TEACH),
               item('f236_medical_e2', 'CONDITIONAL_REQUIRED', anchor='채용신체검사서(E-2 자격요건과 동일)', **F3_TEACH),
               item('f236_teacher_license', 'CONDITIONAL_REQUIRED', anchor='④ 해당국교원 자격증 원본', **F3_E7T),
               item('f236_principal_request', 'CONDITIONAL_REQUIRED', anchor='⑦ 학교장 요청서', **F3_E7T),
               item('f236_foreign_teacher_status', 'CONDITIONAL_REQUIRED', anchor='⑧ 외국인교사 현황', **F3_E7T),
               item('app_form', 'CONDITIONAL_REQUIRED', anchor='신청서, 여권 원본 및 사본, 외국인등록증, 수수료', **F3_SPECIAL),
               item('f236_passport_orig_copy', 'CONDITIONAL_REQUIRED', anchor='신청서, 여권 원본 및 사본, 외국인등록증, 수수료', **F3_SPECIAL),
               item('arc', 'CONDITIONAL_REQUIRED', anchor='신청서, 여권 원본 및 사본, 외국인등록증, 수수료', **F3_SPECIAL),
               item('fee', 'CONDITIONAL_REQUIRED', anchor='신청서, 여권 원본 및 사본, 외국인등록증, 수수료', **F3_SPECIAL)],
         conditions_ko=['전문인력 등 배우자의 허가기간은 본인의 체류기간 내 최대 1년(고용계약이 있으면 그 범위 내)입니다.',
                        "우수인재 배우자 특례('26.3.30.~'27.3.29. 시범운영, 이후 종료될 수 있음): 국내 석사(D-2-3)·박사(D-2-4) 재학생과 E-1·E-3·E-4·E-5 자격자의 성년 배우자는 취업제한 분야를 제외한 모든 활동에 대해 본인의 체류기간 동안 포괄허가를 받을 수 있으며, 근로 시작·종료 시 15일 이내에 신고해야 합니다.",
                        '원래의 체류목적을 침해하지 않는 범위에서 정규교육기관(초·중·고 및 대학)의 교육을 받는 것은 별도 허가가 필요 없습니다.'],
         conditions_en=['For spouses of professionals, permission runs up to one year within your stay (within the employment contract if there is one).',
                        "Talent-spouse special rule (pilot 2026-03-30 to 2027-03-29, may end): adult spouses of Korean master's (D-2-3) or doctoral (D-2-4) students and of E-1, E-3, E-4 and E-5 holders may get blanket permission for any work except restricted fields for their stay, and must report the start and end of work within 15 days.",
                        'Studying at regular schools and universities without harming the original purpose of stay needs no separate permission.'],
         notes_ko=[OFFICER_NOTE_KO], notes_en=[OFFICER_NOTE_EN])

guidance('F-3', 'workplace_report', state='CONDITIONAL', section='동반(F-3) 체류자격외 활동 — 5. 우수인재 배우자에 대한 자격 외 활동허가의 특례',
         anchor='② 취업개시 신고(온라인만 가능)',
         summary_ko="우수인재 배우자 특례('26.3.30.~'27.3.29. 시범운영)로 포괄적 체류자격외 활동허가를 받은 동반(F-3) 자격자는 근로를 시작하거나 끝낼 때 15일 이내에 온라인으로 신고합니다. 취업개시 신고에는 사업자등록증 또는 법인등기부등본을 첨부하고, 취업종료 신고는 별도 서류가 필요 없습니다.",
         summary_en='F-3 holders with blanket outside-status permission under the talent-spouse special rule (pilot 2026-03-30 to 2027-03-29) report the start and end of work online within 15 days. Attach the business registration or corporate register to a start report; an end report needs no documents.',
         timing_ko='근로개시 및 종료 시 15일 이내', timing_en='Within 15 days of starting or ending work',
         docs=[item('f236_bizreg_or_corpreg', anchor='사업자등록증 또는 법인등기부등본 첨부', applies_when_ko='취업개시 신고', applies_when_en='Start-of-work report')],
         conditions_ko=['미신고가 적발되면 자격외 허가가 취소됩니다.', '여러 근무처에서 일하면 모두 각각 신고하며, 계약기간 연장 등 계약사항이 바뀔 때도 신고합니다. 고용계약서상 만료일까지 근무했다면 종료 신고는 필요 없습니다.'],
         conditions_en=['Failing to report leads to cancellation of the permission.', 'Report each workplace separately and any contract change such as an extension; no end report is needed if you worked until the contract end date.'])

f236_reentry('F-3', '동반(F-3)')

# ==========================================================================
# F-6 결혼이민 — 사증 (visa manual)
# ==========================================================================
F6_PROGRAM = {'applies_when_ko': '국제결혼 안내프로그램 대상 국가 국민과 결혼한 경우(면제 대상자 제외)', 'applies_when_en': 'Marriage to a national of an international-marriage program country (unless exempt)'}
F6_HEALTH_EXEMPT_KO = '국제결혼 안내프로그램 면제 대상자(상대국 6개월 이상 또는 제3국 장기체류 중 교제, 외국인 배우자의 국내 장기체류자격 91일 이상 합법 체류 중 교제, 임신·출산 등 인도적 고려)는 제출 불필요'
F6_HEALTH_EXEMPT_EN = 'Not needed for those exempt from the program (dated while living 6+ months in the partner\'s country or long-term in a third country, dated while the foreign spouse lawfully stayed 91+ days on a long-term status, or pregnancy, birth or other humanitarian grounds)'


def f236_f6_spouse_docs(form_item, comm_anchor='3. 외국인 배우자의 의사소통 요건 관련 서류'):
    return [form_item,
            item('f236_passport_photo', anchor='여권용 사진 1매'),
            item('f236_applicant_passport_orig', anchor='신청인(외국인 배우자) 여권 원본'),
            item('f236_applicant_passport_copy', anchor='신청인 여권 사본 1부'),
            item('f236_visa_fee', anchor='비자 신청 수수료'),
            item('f236_spouse_invitation', anchor='외국인 배우자 초청장'),
            item('guarantor', anchor='1-7 신원보증서', role='korean_spouse'),
            item('f236_marriage_background_stmt', anchor='외국인 배우자의 결혼배경진술서'),
            item('f236_ksp_passport_copy', anchor='한국인 배우자 여권 사본 1부'),
            item('f236_ksp_basic_detail', anchor='기본증명서(상세)'),
            item('spouse_marriage_cert_detail', anchor='혼인관계증명서(상세)'),
            item('f236_ksp_family_detail', anchor='가족관계증명서(상세)'),
            item('f236_ksp_resident_reg_orig', anchor='주민등록등본 원본'),
            item('f236_intl_marriage_program_cert', 'CONDITIONAL_REQUIRED', anchor='국제결혼 안내프로그램 이수증', **F6_PROGRAM),
            item('f236_ksp_health', 'CONDITIONAL_REQUIRED', anchor='건강진단서 원본', does_not_apply_when_ko=F6_HEALTH_EXEMPT_KO, does_not_apply_when_en=F6_HEALTH_EXEMPT_EN,
                 notes_ko=['병원급 의료기관, 보건소 또는 공무원채용 신체검사 실시 검진기관에서 공무원채용 응시 건강검진표 양식으로 발급되고 사증 신청일로부터 6개월 이내 발급된 것이어야 합니다.'],
                 notes_en=['Must be issued on the civil-service recruitment health-check form by a hospital-level institution, public health centre or designated check-up centre, within 6 months of the visa application.']),
            item('f236_foreign_marriage_cert', 'ADDITIONAL_IF_APPLICABLE', anchor='결혼증명서 원본(정식 명칭 병기)', applies_when_ko='본국에서의 중혼 여부 등을 확인하기 위해 필요한 경우에 한함', applies_when_en='Only where needed to check for bigamy in the home country, etc.'),
            item('f236_foreign_crime_record', 'CONDITIONAL_REQUIRED', anchor='범죄경력증명서 원본(정식명칭', does_not_apply_when_ko='한국인 배우자가 면제 대상이면 외국인 배우자도 제출 면제', does_not_apply_when_en='Waived if the Korean spouse is exempt',
                 notes_ko=['발급일로부터 3개월 이내의 것이어야 합니다.'], notes_en=['Must be issued within the last 3 months.']),
            item('f236_foreign_health', 'CONDITIONAL_REQUIRED', anchor='건강진단서 원본', does_not_apply_when_ko='한국인 배우자가 면제 대상이면 외국인 배우자도 면제(단, 결핵 관련 진단서는 제출)', does_not_apply_when_en='Waived if the Korean spouse is exempt (a TB certificate is still required)',
                 notes_ko=['사증 신청일로부터 6개월 이내 발급되고 병원명·주소·연락처·담당의사 서명이 기재된 컴퓨터 작성 문서여야 하며, 결핵(TB) 검사 항목이 포함되어야 합니다.'],
                 notes_en=['Issued within 6 months of the visa application, computer-generated with the hospital name, address, contact and doctor\'s signature, and including a TB test.']),
            item('f236_country_specific', 'ADDITIONAL_IF_APPLICABLE', anchor='해당 국가에 특별히 적용되는 서류', applies_when_ko='해당 국가에 특별히 적용되는 경우', applies_when_en='If your country has specific requirements'),
            item('f236_income_req_docs', 'SOURCE_MENTIONS_BUT_NOT_STRUCTURED', anchor='2. 한국인 배우자의 소득요건 관련 서류',
                 notes_ko=['초청인이 소득요건을 충족하려고 활용하는 항목에 따라 선택적으로 준비하며(공통 필수 서류는 필수), 소득요건 면제 대상자는 내지 않습니다. 세부 서류는 매뉴얼 표를 확인하세요.'],
                 notes_en=['Prepared according to how the inviter meets the income requirement (the common mandatory items are required); not needed if exempt. See the manual\'s table for details.']),
            item('f236_comm_req_docs', 'SOURCE_MENTIONS_BUT_NOT_STRUCTURED', anchor=comm_anchor,
                 notes_ko=['매뉴얼 표의 서류 중 하나를 선택해 냅니다. 면제 대상이 아닌데도 서류를 내지 않으면 불허될 수 있습니다.'], notes_en=['Choose one of the documents in the manual\'s table.']),
            item('f236_housing_req_docs', 'SOURCE_MENTIONS_BUT_NOT_STRUCTURED', anchor='4. 한국인 배우자의 주거요건 관련 서류',
                 notes_ko=['자가는 등기부등본, 임대는 등기부등본과 임대차계약서 사본을 내며, 주소지는 주민등록등본상 주소와 같아야 합니다.'], notes_en=['Owned: property register; rented: register and lease copy. The address must match the resident registration.']),
            item('f236_courtship_docs', 'SOURCE_MENTIONS_BUT_NOT_STRUCTURED', anchor='5. 교제 입증 서류')]


F6_SPOUSE_CONDITIONS_KO = ['국제결혼 안내프로그램 면제 대상자: ① 외국인 배우자의 국가에서 6개월 이상 또는 제3국에서 유학·파견근무 등으로 장기사증으로 계속 체류하면서 교제한 사실을 입증할 수 있는 사람 ② 외국인 배우자가 장기체류자격으로 91일 이상 합법 체류하면서 초청인과 교제한 사실을 입증할 수 있는 사람 ③ 임신, 출산 그 밖에 인도적인 고려가 필요하다고 인정되는 사람.',
                           '국제결혼 안내프로그램 대상 국가 이외의 국민과 결혼한 경우에는 별도의 서류 목록이 적용되며, 부부 사이에 출생한 자녀가 있는 경우 등 서류 간소화 사례별 목록이 있습니다.']
F6_SPOUSE_CONDITIONS_EN = ['Exempt from the international-marriage program: (1) those who can prove they dated while living 6+ months in the partner\'s country or long-term in a third country for study or work; (2) those who can prove they dated while the foreign spouse lawfully stayed 91+ days on a long-term status; (3) pregnancy, birth or other humanitarian grounds.',
                           'A separate list applies to marriages with nationals of countries outside the program, and simplified lists exist for cases such as couples who have a child together.']

guidance('F-6-1', 'visa_issuance', manual=VISA, completeness='PARTIALLY_STRUCTURED', doc_page_window=8,
         section='사증발급 안내매뉴얼 결혼이민(F-6) — 공관장 재량으로 발급할 수 있는 사증 1. 국민의 배우자(F-6-1)',
         anchor='국민의 배우자(F-6-1)에 대한 체류기간 90일 이하의 단수사증 발급',
         summary_ko='국민의 배우자(F-6-1)에게는 재외공관에서 체류기간 90일 이하의 단수사증(미국인은 복수사증)을 발급하며, 입국 후 90일 이내에 외국인등록과 체류기간 연장을 해야 합니다. 기본서류에 더해 한국인 배우자의 소득요건·주거요건 서류, 외국인 배우자의 의사소통 요건 서류, 교제 입증 서류를 냅니다.',
         summary_en='Spouses of Korean nationals (F-6-1) get a single-entry visa for up to 90 days (multiple-entry for US citizens) at a Korean mission and must register and extend within 90 days of entry. Besides the basic documents, submit the Korean spouse\'s income and housing documents, the foreign spouse\'s communication documents and proof of the relationship.',
         timing_ko='입국 후 90일 이내 외국인등록 및 체류기간 연장', timing_en='Register and extend within 90 days of entry',
         docs=f236_f6_spouse_docs(item('f236_visa_app', anchor='비자 신청서(사증발급 신청서)')),
         conditions_ko=F6_SPOUSE_CONDITIONS_KO + ['초청장 및 혼인관계증명서 등 제출 서류의 유효기간은 별도 규정이 없으면 작성일·발급일로부터 3개월 이내입니다.'],
         conditions_en=F6_SPOUSE_CONDITIONS_EN + ['Unless stated otherwise, documents such as the invitation and marriage certificate are valid for 3 months from writing or issue.'],
         notes_ko=['접수 및 심사과정에서 일부 서류가 가감될 수 있으며, 재외공관의 장은 규정된 서류 외에 추가서류를 요구할 수 있습니다.'],
         notes_en=['Some documents may be added or waived during review, and the mission may ask for documents beyond those listed.'])

guidance('F-6-2', 'visa_issuance', manual=VISA, section='사증발급 안내매뉴얼 결혼이민(F-6) — 공관장 재량으로 발급할 수 있는 사증 2. 자녀양육(F-6-2)',
         anchor='자녀양육 (F-6-2)을 위해 입국하고자 하는 자에 대한 체류기간 90일 이하의 단수사증 발급',
         summary_ko='자녀양육(F-6-2)을 위해 입국하려는 사람은 체류기간 90일 이하의 단수사증(미국인은 복수사증)을 받으며, 입국 후 90일 이내에 외국인등록과 체류기간 연장을 해야 합니다. 가족(친자)관계 입증서류, 자녀양육 입증서류, 범죄경력증명서와 건강진단서를 냅니다.',
         summary_en='People entering to raise a child (F-6-2) get a single-entry visa for up to 90 days (multiple-entry for US citizens) and must register and extend within 90 days of entry. Submit proof of parentage, proof of raising the child, and a criminal record and health certificate.',
         timing_ko='입국 후 90일 이내 외국인등록 및 체류기간 연장', timing_en='Register and extend within 90 days of entry',
         docs=f236_visa_base('사증발급신청서 (별지 제17호 서식), 여권, 표준규격사진 1매, 수수료') + [
             item('f236_parentage_docs_visa', anchor='② 가족(친자)관계 입증서류',
                  notes_ko=['사실혼 관계에서 자녀가 출생했다면 그 사실을 증명하는 서류를 냅니다.'], notes_en=['If the child was born in a de facto marriage, submit proof of that.']),
             item('f236_childcare_proof_visa', anchor='③ 자녀양육을 입증할 수 있는 서류'),
             item('f236_crime_health', anchor='④ 범죄경력증명서 및 건강진단서')],
         notes_ko=['재외공관장은 특히 필요하다고 인정되는 경우 제출서류를 일부 가감하거나 추가 서류를 받을 수 있습니다.'],
         notes_en=['The consul may add or waive documents where specially needed.'])

guidance('F-6', 'visa_issuance_confirmation', manual=VISA, state='GENERALLY_NOT_PERMITTED', completeness='SOURCE_ONLY',
         section='사증발급 안내매뉴얼 결혼이민(F-6) — 사증발급인정서 발급대상', anchor='☞ 사증발급인정서 발급 대상 아님',
         summary_ko='결혼이민(F-6)은 사증발급인정서 발급 대상이 아닙니다. 국민의 배우자(F-6-1)와 자녀양육(F-6-2) 사증은 재외공관에서 체류기간 90일 이하의 사증으로 신청합니다.',
         summary_en='F-6 is not eligible for a confirmation of visa issuance. F-6-1 and F-6-2 visas are applied for at a Korean mission as visas for stays of up to 90 days.')

# ==========================================================================
# F-6 결혼이민 — 체류 (stay manual)
# ==========================================================================
guidance('F-6', 'status_grant', completeness='SOURCE_ONLY', section='결혼이민(F-6) 체류자격 부여',
         anchor='1. 국내 체류 중 대한민국 국적을 상실한 사람에 대해 체류목적에 따라 결혼이민(F-6) 체류자격 부여',
         summary_ko='국내 체류 중 대한민국 국적을 상실한 사람과 주한미군 현지 제대자에게 체류목적에 따라 결혼이민(F-6) 체류자격을 부여합니다. 제출서류와 체류허가 기간은 체류자격 변경허가에 준합니다. 국적을 상실·이탈한 날부터 30일 이내에 체류자격을 받아야 합니다(출입국관리법 제23조).',
         summary_en='People who lose Korean nationality while in Korea, and US Forces Korea members discharged in Korea, are granted F-6 according to their purpose of stay. Documents and period follow the change-of-status rules. Status must be obtained within 30 days of losing or renouncing nationality (Immigration Act Art. 23).',
         timing_ko='국적 상실·이탈 등 사유 발생일부터 30일 이내', timing_en='Within 30 days of losing nationality or the other ground')

F61_FORM = item('app_form_34', anchor='통합신청서(별지34호)')
guidance('F-6-1', 'status_change', completeness='PARTIALLY_STRUCTURED', doc_page_window=8,
         section='결혼이민(F-6) 체류자격 변경허가 — 1. 국민의 배우자(F-6-1)에 대한 체류자격 변경허가',
         anchor='1. 국민의 배우자(F-6-1)에 대한 체류자격 변경허가',
         summary_ko='국내 합법체류자 중 국민의 배우자(F-6-1)로 바꾸려는 사람은 국민의 배우자 사증발급 때의 서류를 준용해 신청하며, 체류허가기간은 1년 이내입니다. 단기사증 소지자, 불법체류자, 출국을 위한 체류기간 연장허가를 받은 사람, 일반 형사범 등은 원칙적으로 변경이 불가하고 출국 후 재외공관에서 사증을 받아야 합니다.',
         summary_en='Lawful residents changing to F-6-1 apply with the documents used for the F-6-1 visa; the period is up to one year. Short-term visa holders, people staying illegally, those on a departure extension and general criminal offenders cannot in principle change and must leave and apply for a visa abroad.',
         period_ko='1년 이내', period_en='Up to 1 year',
         docs=f236_f6_spouse_docs(F61_FORM, comm_anchor='(의사소통 요건 적용 면제)'),
         conditions_ko=['변경 불가 대상: 1. 단기사증 소지자(B-1·B-2 및 C-1~C-4), 2. 불법체류자(밀입국자, 위·변조여권행사자 포함), 3. 출국을 위한 체류기간 연장허가를 받은 사람(출국기한유예자는 대상 아님), 4. 일반 형사범(단순 벌금 제외), 5. 위 신분으로 체류 중 기타(G-1) 자격을 받은 사람. 다만 사증면제(B-1)로 입국한 독일인은 변경할 수 있습니다.',
                        '임신·출산 또는 부부 사이에서 출생한 자녀(양자·친양자 제외) 양육 등으로 국내 변경이 불가피하다고 판단되면 심사 후 변경할 수 있습니다.',
                        '관광취업(H-1) 자격으로 체류하는 사람은 결혼이민(F-6)으로 변경할 수 없습니다.'] + F6_SPOUSE_CONDITIONS_KO,
         conditions_en=['Cannot change: 1. short-term visa holders (B-1, B-2, C-1 to C-4); 2. illegal residents (incl. smuggled entry or forged passports); 3. holders of a departure extension (not departure deferral); 4. general criminal offenders (simple fines excluded); 5. people who got G-1 while in those situations. German nationals who entered on B-1 may change.',
                        'Where a change in Korea is unavoidable because of pregnancy, birth or raising the couple\'s child (not adopted), a change may be allowed after review.',
                        'H-1 working-holiday holders cannot change to F-6.'] + F6_SPOUSE_CONDITIONS_EN,
         notes_ko=['접수 및 심사과정에서 일부 서류가 가감될 수 있습니다.', OFFICER_NOTE_KO],
         notes_en=['Some documents may be added or waived during review.', OFFICER_NOTE_EN])

guidance('F-6-2', 'status_change', section='결혼이민(F-6) 체류자격 변경허가 — 자녀 양육자에 대한 체류자격(F-6-2) 변경허가',
         anchor='자녀 양육자에 대한 체류자격(F-6-2) 변경허가',
         summary_ko='결혼이민(F-6) 이외의 체류자격으로 체류 중이면서 국민과의 혼인관계(사실혼 포함)에서 출생한 미성년 자녀를 국내에서 양육하는 부 또는 모는 자녀양육(F-6-2)으로 바꿀 수 있으며, 체류허가기간은 1년입니다.',
         summary_en='A parent staying on a status other than F-6 who is raising in Korea a minor child born in a marriage (including de facto) with a Korean national can change to F-6-2; the period is one year.',
         period_ko='1년', period_en='1 year',
         docs=f236_stay_base('① 신청서(별지 제34호 서식), 여권, 외국인등록증(해당자), 표준규격사진 1매, 수수료') + [
             item('f236_arc_if_any', 'CONDITIONAL_REQUIRED', anchor='① 신청서(별지 제34호 서식), 여권, 외국인등록증(해당자), 표준규격사진 1매, 수수료', applies_when_ko='해당자', applies_when_en='If held'),
             item('child_basic_family_cert', 'CONDITIONAL_REQUIRED', anchor='② 자녀가 국민인 경우 자녀 명의의 기본증명서', applies_when_ko='자녀가 국민인 경우', applies_when_en='If the child is a Korean national'),
             item('f236_parentage_birth_dna', anchor='③ 가족(친자)관계 입증서류'),
             item('f236_childcare_proof_stay', anchor='④ 자녀양육 입증서류'),
             item('f236_marriage_end_proof', 'CONDITIONAL_REQUIRED', anchor='⑤ 혼인단절자(이혼,사망,실종등)의 경우 그 사유를 입증하는 서류', applies_when_ko='혼인단절자(이혼·사망·실종 등)에 한함', applies_when_en='Only if the marriage ended (divorce, death, disappearance, etc.)'),
             item('f236_crime_health', anchor='⑥ 범죄경력증명서 및 건강진단서', does_not_apply_when_ko='이미 제출한 사람으로서 해외에서 6개월 이상 연속하여 체류한 사실이 없으면 면제', does_not_apply_when_en='Waived if already submitted and you have not stayed abroad 6+ consecutive months'),
             item('other_officer_docs', 'MAY_BE_REQUESTED_BY_OFFICER', anchor='⑦ 그 밖에 심사에 필요하다고 인정되는 서류')],
         notes_ko=[OFFICER_NOTE_KO], notes_en=[OFFICER_NOTE_EN])

F63_DEATH = {'applies_when_ko': '배우자가 사망한 경우', 'applies_when_en': 'If the spouse died'}
F63_DIVORCE = {'applies_when_ko': '이혼한 경우', 'applies_when_en': 'If divorced'}
F63_MISSING = {'applies_when_ko': '배우자가 실종된 경우', 'applies_when_en': 'If the spouse is missing'}
F63_FORM = '신청서(별지 제 34호 서식), 여권, 외국인등록증, 표준규격사진 1매, 수수료'
guidance('F-6-3', 'status_change', section='결혼이민(F-6) 체류자격 변경허가 — 혼인단절자(사망, 실종, 이혼)에 대한 체류자격(F-6-3) 변경허가',
         anchor='혼인단절자(사망,실종,이혼)에 대한 체류자격(F-6-3) 변경허가',
         summary_ko='결혼이민(F-6) 이외의 자격으로 체류 중인 사람으로서 국민과 정상적인 혼인생활 중 한국인 배우자의 사망·실종이나 자신에게 책임 없는 사유로 혼인이 단절된 사람은 혼인단절(F-6-3)로 바꿀 수 있으며, 체류허가기간은 1년입니다. 공통서류와 사유별(사망·이혼·실종) 입증서류를 냅니다.',
         summary_en='People staying on a status other than F-6 whose marriage to a Korean national ended through the spouse\'s death or disappearance or for reasons not their fault can change to F-6-3; the period is one year. Submit the common documents and evidence for the specific case (death, divorce, disappearance).',
         period_ko='1년', period_en='1 year',
         docs=f236_stay_base(F63_FORM, arc=True) + [
             item('f236_crime_health', anchor='범죄경력증명서 및 건강진단서(旣제출자로서 해외에서 6개월 이상 연속하여 체류한 사실이 없는 자는 제출 면제)',
                  does_not_apply_when_ko='이미 제출한 사람으로서 해외에서 6개월 이상 연속하여 체류한 사실이 없으면 면제', does_not_apply_when_en='Waived if already submitted and you have not stayed abroad 6+ consecutive months'),
             item('death_proof', 'CONDITIONAL_REQUIRED', anchor='배우자의 사망 입증서류', **F63_DEATH),
             item('family_relation', 'CONDITIONAL_REQUIRED', anchor='가족관계 입증서류(혼인관계 증명서 등)', applies_when_ko='배우자가 사망하거나 실종된 경우', applies_when_en='If the spouse died or is missing'),
             item('divorce_marriage_cert', 'CONDITIONAL_REQUIRED', anchor='이혼사실이 기재된 혼인관계 증명서', **F63_DIVORCE),
             item('f236_divorce_suit', 'CONDITIONAL_REQUIRED', anchor='이혼관련 소송서류(소장, 이혼 판결문 등)', **F63_DIVORCE),
             item('fault_proof', 'CONDITIONAL_REQUIRED', anchor='‣ 귀책사유 입증자료', **F63_DIVORCE,
                  notes_ko=['예: 한국인 배우자의 가출신고서, 배우자의 폭행 등으로 인한 병원 진단서, 검찰의 불기소결정문, 공인된 여성관련 단체 확인서, 국민 배우자의 4촌 이내 친척의 확인서, 혼인관계가 중단된 때 거주하던 통(반)장의 확인서 등'],
                  notes_en=['E.g. a missing-person report on the Korean spouse, a medical certificate for injuries from the spouse\'s violence, a prosecutor\'s non-indictment decision, confirmation from a recognised women\'s organisation, a relative of the Korean spouse within the fourth degree, or the neighbourhood head where you lived.']),
             item('missing_judgment', 'CONDITIONAL_REQUIRED', anchor='실종사실 증명서류(실종선고심판서)', **F63_MISSING),
             item('other_officer_docs', 'MAY_BE_REQUESTED_BY_OFFICER', anchor='☞ 그 밖에 심사에 필요하다고 인정되는 서류')],
         conditions_ko=['단기체류자, 형사범(단순 벌금형 제외), 출국을 위한 체류기간 연장허가를 받은 사람과, 이러한 제한 대상이었다가 기타(G-1) 체류허가를 받은 사람은 제외됩니다.',
                        '신청 당시 국민의 배우자(F-6-1)로 체류 중이면 체류기간 연장허가 대상입니다.'],
         conditions_en=['Excluded: short-term residents, criminal offenders (simple fines excluded), holders of a departure extension, and people who received G-1 while in those situations.',
                        'If you are staying as F-6-1 when applying, you apply for an extension instead.'],
         notes_ko=[OFFICER_NOTE_KO], notes_en=[OFFICER_NOTE_EN])

guidance('F-6', 'reentry', completeness='SOURCE_ONLY', section='결혼이민(F-6) 재입국허가',
         anchor='결혼이민(F-6, 기존 F-2-1, F-2-10 포함)자격으로 등록을 필한 사람으로서 출국한 날로부터 1년 초과 2년 이내에 재입국하려는 사람',
         summary_ko='결혼이민(F-6, 기존 F-2-1·F-2-10 포함)으로 외국인등록을 마친 사람은 출국한 날부터 1년 이내 재입국하면 재입국허가가 면제되고(체류기간 만료일이 1년보다 적게 남았으면 그 범위 내), 1년 초과 2년 이내에 재입국하려면 허가기간 2년의 복수 재입국허가를 받습니다(체류기간 만료일이 2년보다 적게 남았으면 그 범위 내). 입국규제자는 본부 승인을 받아 재입국허가를 받아야 합니다.',
         summary_en='Registered F-6 holders (including the former F-2-1 and F-2-10) are exempt from a re-entry permit if they return within one year (or within their remaining stay); to return after one but within two years they get a two-year multiple re-entry permit (within their remaining stay). People under an entry restriction need headquarters approval.')
