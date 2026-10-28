# D-7 주재 · D-8 기업투자 · D-9 무역경영 · D-10 구직 · A-1 외교 · A-2 공무 · A-3 협정 · B-1 사증면제 · B-2 관광통과
# Transcribed from the 2026-10-19 manuals:
#   visa manual (사증민원 안내매뉴얼): A-1~A-3 pp. 7-13, B-1 p. 14, B-2 p. 22, D-7 p. 94, D-8 p. 104, D-9 p. 118, D-10 p. 124
#   stay manual (체류민원 안내매뉴얼): A-1~A-3 pp. 14-21, D-7 pp. 109-114, D-8 pp. 116-127, D-9 pp. 131-137, D-10 pp. 145-160
# Runs inside author_rules.py (guidance, item, docdefs, drop, residence, VISA, STAY, FAMILIES, dim, opt …).
# Nothing here covers 전자사증 (electronic_visa): the manual does not list these statuses as e-visa eligible.

docdefs(
    # ---- shared visa-manual forms
    d7ab_visa_app=('사증발급신청서 (별지 제17호 서식)', 'Visa application form (Form 17)', 'applicant', None),
    d7ab_cvi_app=('사증발급인정신청서 (별지 제21호 서식)', 'Application for a confirmation of visa issuance (Form 21)', 'inviter', None),
    d7ab_cvi_common=('사증발급인정신청서, 여권사본 등 공통제출 서류', 'Confirmation application, passport copy and the other common documents', 'inviter', None),
    d7ab_invitation_reason=('초청사유서', 'Statement of reasons for the invitation', 'inviter', None),
    d7ab_proxy_docs=('위임장, 대리인 재직증명서, 대리인 신분증 (대리인 신청 시)', 'Power of attorney, the agent\'s certificate of employment and ID (when an agent applies)', 'agency', None),
    d7ab_app_form=('신청서', 'Application form', 'applicant', None),
    # ---- A-1 / A-2 / A-3
    d7ab_a1_dispatch_or_mofa=('파견, 재직을 증명하는 서류 또는 해당국 외교부장관의 협조공한', 'Proof of dispatch/employment, or a cooperation letter from your foreign minister', 'applicant', None),
    d7ab_a1_family_proof=('본국에서 발급한 가족관계증명서, 출생증명서 등 가족관계 입증서류', 'Family-relationship proof issued at home (family-relation certificate, birth certificate, etc.)', 'applicant', None),
    d7ab_a2_dispatch_or_letter=('파견, 재직을 증명하는 서류 또는 해당국 외교부장관이나 소속부처 장관의 공한 (공무수행임을 입증하는 내용 명시)', 'Proof of dispatch/employment, or a letter from your foreign minister or ministry stating the official duty', 'applicant', None),
    d7ab_birth_cert_copy=('출생증명서 사본', 'Copy of the birth certificate', 'applicant', None),
    d7ab_embassy_letter=('대사관 협조공한', 'Cooperation letter from the embassy', 'principal_holder', None),
    d7ab_supporter_mission_id=('부양자의 외국공관원 신분증', 'The supporting parent\'s foreign-mission staff ID', 'principal_holder', None),
    d7ab_home_embassy_letter=('자국 대사관의 협조 공문', 'Cooperation letter from your embassy', 'principal_holder', None),
    d7ab_dispatch_employment=('파견·재직을 증명하는 서류', 'Proof of dispatch / employment', 'principal_holder', None),
    d7ab_family_birth_proof=('출생증명서, 가족관계증명서 등 가족관계 입증서류', 'Birth certificate, family-relation certificate or other family-relationship proof', 'applicant', None),
    d7ab_principal_id=('주체류자(① 또는 ②에 해당하는 사람)의 신분증', 'ID of the principal (mission member or privileged person)', 'principal_holder', None),
    d7ab_a2_dispatch_or_ministry=('파견․재직을 입증하는 서류 또는 자국 소속부처의 장의 협조공문', 'Proof of dispatch/employment or a cooperation letter from the head of your ministry', 'applicant', None),
    d7ab_status_relation_proof=('출생증명서 등 신분관계 입증서류', 'Birth certificate or other proof of the family relationship', 'applicant', None),
    d7ab_supporter_duty_id=('부양자의 공무수행을 증명하는 신분증', 'ID proving the supporting family member\'s official duty', 'principal_holder', None),
    d7ab_mofa_employment_rec=('외교부(외교사절담당관)에서 받은 고용추천서', 'Employment recommendation from the Ministry of Foreign Affairs (diplomatic mission officer)', 'other_third_party', None),
    d7ab_target_status_docs=('해당 체류자격별 체류자격외 활동 필요서류 (자격요건 등 구비)', 'The documents required for the target status\'s activity (meeting its requirements)', 'applicant', None),
    d7ab_photo_half=('반명함판 천연색 사진 (3.5×4.5㎝)', 'Colour photo (3.5 × 4.5 cm)', 'applicant', None),
    d7ab_mission_id_proof=('주한외국공관원 신분증 등 신분 입증서류', 'Foreign-mission staff ID or other proof of status', 'applicant', None),
    d7ab_diplomat_id=('외교관 신분증', 'Diplomatic ID card', 'applicant', None),
    d7ab_employment_proof=('재직 증명 서류', 'Proof of employment', 'applicant', None),
    d7ab_service_cert=('복무확인서', 'Certificate of service', 'principal_holder', None),
    d7ab_sofa_id=('S.O.F.A ID 카드', 'SOFA ID card', 'applicant', None),
    d7ab_target_status_papers=('해당 자격 관련 서류', 'Documents for the target status', 'applicant', None),
    d7ab_sponsor_consent=('소속 기관장(고용주)의 동의서 (SPONSOR인 경우)', 'Consent of the head of your unit / employer (if you are the SPONSOR)', 'employer', None),
    d7ab_a3_family_proof=('출생증명서 등 가족관계 입증서류', 'Birth certificate or other family-relationship proof', 'applicant', None),
    d7ab_supporter_id=('부양자의 신분증명서', 'The supporting family member\'s ID', 'principal_holder', None),
    d7ab_invitation_contractor_docs=('초청계약자 등이 발급한 복무확인서․재직증명서 또는 초청계약서', 'Certificate of service / employment issued by the invited contractor etc., or the invitation contract', 'principal_holder', None),
    d7ab_sponsor_service_cert=('SPONSOR 복무확인서(현역) 또는 재직증명서(군속)', 'SPONSOR certificate of service (active duty) or certificate of employment (civilian component)', 'applicant', None),
    d7ab_invitation_contract=('초청계약서 (초청계약자)', 'Invitation contract (invited contractors)', 'applicant', None),
    d7ab_parent_sofa_id=('11세 미만자는 부․모의 SOFA ID 카드 (11세 이상인 경우 본인 ID 카드)', 'Under 11: a parent\'s SOFA ID card (11 or older: your own ID card)', 'principal_holder', None),
    d7ab_fulbright_id=('Fulbright I/D 카드', 'Fulbright ID card', 'applicant', None),
    d7ab_kaec_letter=('한미교육위원단 협조공한', 'Cooperation letter from the Korean-American Educational Commission', 'other_third_party', None),
    d7ab_sofa_id_both=('SOFA ID카드 (SPONSOR와 Dependent 모두 필요)', 'SOFA ID cards (both SPONSOR and dependants)', 'applicant', None),
    d7ab_service_cert_departure=('복무확인서 (재직증명서: 출국일과 동반 가족 기재된 것)', 'Certificate of service (employment certificate showing the departure date and accompanying family)', 'principal_holder', None),
    # ---- D-7 / D-8 / D-9 shared stay items
    d7ab_dean_rec=('총(학)장의 추천서', 'Recommendation from the university president / dean', 'educational_institution', None),
    d7ab_unique_no_copy=('고유번호증(사업자등록증) 사본', 'Copy of the university\'s unique-number (business registration) certificate', 'educational_institution', None),
    d7ab_origin_employer_consent=('원근무처장의 동의서', 'Consent of the head of your current workplace', 'employer', None),
    # ---- D-7 visa / confirmation
    d7ab_foreign_company_employment=('외국 소재 회사 등 재직증명서', 'Certificate of employment from the company abroad', 'employer', None),
    d7ab_dispatch_order=('파견명령서', 'Dispatch order', 'employer', None),
    d7ab_branch_permit=('국내지점 등 설치 입증서류 (지사 또는 연락사무소 설치허가서 사본)', 'Proof of the Korean branch (copy of the branch or liaison-office establishment permit)', 'business_entity', None),
    d7ab_branch_permit_cvi=('국내지점 등 설치 입증서류 (지사나 연락사무소 설치허가서 사본 또는 신고수리서 사본)', 'Proof of the Korean branch (copy of the branch/liaison-office permit or of the acceptance of its report)', 'business_entity', None),
    d7ab_branch_operation_proof=('지사 또는 연락사무소가 정상적으로 운영되고 있음을 입증하는 서류 (영업자금 도입실적, 신규일 경우 지사 또는 연락사무소 운영계획서, 납세실적 등)', 'Proof the branch or liaison office operates normally (operating-fund inflows; if new, its operating plan, tax records, etc.)', 'business_entity', None),
    d7ab_essential_staff_proof=('필수전문인력임을 입증하는 서류 (이력서, 경력증명서 등)', 'Proof you are essential professional staff (CV, career certificate, etc.)', 'applicant', None),
    d7ab_hq_register_optional=('본사의 등기사항전부증명서 (본사가 공공기업인 경우 생략 가능)', 'Head office\'s certificate of registered matters (may be omitted for a public enterprise)', 'business_entity', None),
    d7ab_hq_register=('본사의 등기사항전부증명서', 'Head office\'s certificate of registered matters', 'business_entity', None),
    d7ab_odi_report=('해외직접투자신고수리서 또는 해외지점설치신고수리서', 'Acceptance of the overseas direct-investment report or of the overseas-branch report', 'business_entity', None),
    d7ab_remittance_proof=('해외 송금확인 입증서류', 'Proof of the overseas remittance', 'business_entity', None),
    d7ab_overseas_branch_reg=('해외지사의 법인등기사항전부증명서 또는 사업자등록증', 'Corporate register or business registration of the overseas branch', 'business_entity', None),
    d7ab_overseas_employment_tax=('해외지사에서의 재직증명서 및 납세사실증명', 'Certificate of employment at the overseas branch and proof of tax payment', 'applicant', None),
    d7ab_hq_tax=('본사의 납세사실증명', 'Head office\'s proof of tax payment', 'business_entity', None),
    d7ab_personnel_order=('인사명령서(파견명령서) : 파견기간이 명시된 명령서', 'Personnel (dispatch) order stating the dispatch period', 'business_entity', None),
    d7ab_hq_dispatch_order=('본사발생 파견명령서', 'Dispatch order issued by the head office', 'employer', None),
    d7ab_fx_funds_proof=('외국환매입증명서 등 영업자금 도입실적 입증서류', 'Proof of operating-fund inflows (foreign-exchange purchase certificate, etc.)', 'business_entity', None),
    d7ab_tax_payment_proof=('납세사실증명', 'Proof of tax payment', 'business_entity', None),
    d7ab_vat_biz_reg=('‘부가가치세법’에 따른 사업자등록증', 'Business registration under the VAT Act', 'business_entity', None),
    d7ab_flc_office_reg=('외국법자문법률사무소 등록증 (대한변호사협회 발행)', 'Foreign legal consultant office registration (issued by the Korean Bar Association)', 'business_entity', None),
    d7ab_branch_report_bizreg=('국내지점 등 설치 신고서 (외국환은행 발행) 및 사업자등록증', 'Korean branch establishment report (issued by a foreign-exchange bank) and business registration', 'business_entity', None),
    d7ab_dispatch_order_period=('파견명령서 (본사발행, 파견기간 명시)', 'Dispatch order (issued by the head office, stating the period)', 'employer', None),
    d7ab_flc_consultant_reg=('외국법자문사 등록증 (대한변호사협회 발행)', 'Foreign legal consultant registration (issued by the Korean Bar Association)', 'applicant', None),
    d7ab_career_cert_hq=('경력증명서 (본사 1년 이상 근무요건 충족 여부 확인)', 'Career certificate (to confirm one year or more at the head office)', 'applicant', None),
    # ---- D-7 stay
    d7ab_change_reason=('신청사유서', 'Statement of reasons for the application', 'applicant', None),
    d7ab_dispatch_or_prospective=('파견명령서(외국본사 발행) 원본 또는 재직예정증명서', 'Original dispatch order (issued by the foreign head office) or certificate of prospective employment', 'employer', None),
    d7ab_foreign_branch_permit=('외국기업의 국내지사 설치허가서 사본 또는 연락사무소 설치허가서 사본 (외국환은행 발행)', 'Copy of the foreign company\'s Korean branch or liaison-office establishment permit (issued by a foreign-exchange bank)', 'business_entity', None),
    d7ab_same_group_proof=('동일계열 외국기업 입증 서류 (법인등기사항전부증명서 등)', 'Proof the companies belong to the same group (corporate register, etc.)', 'business_entity', None),
    d7ab_target_company_funds=('근무하려는 기업의 연간납세증명서 또는 외국환매입증명서 등 영업자금 도입실적 증명서류', 'Annual tax certificate of the company you will work for, or proof of its operating-fund inflows (foreign-exchange purchase certificate, etc.)', 'business_entity', None),
    d7ab_office_lease_original=('사무실 임대차 계약서 원본', 'Original office lease', 'business_entity', None),
    d7ab_foreign_staff_list=('근무 중인 외국인 현황', 'List of foreign employees currently working there', 'business_entity', None),
    d7ab_personal_tax_original=('개인 납세사실증명원 원본 (근로소득원천징수영수증(작년) 또는 소득금액증명원(최근 기록))', 'Original personal tax-payment certificate (last year\'s withholding receipt or latest income certificate)', 'applicant', None),
    d7ab_hq_dispatch_order_stay=('파견명령서 (본사 발행)', 'Dispatch order (issued by the head office)', 'employer', None),
    d7ab_branch_proof_stay=('국내 지점 등 설치 입증서류 (지사 또는 연락사무소 설치허가서 등)', 'Proof of the Korean branch (branch or liaison-office permit, etc.)', 'business_entity', None),
    d7ab_cv_or_career=('이력서 또는 경력증명서', 'CV or career certificate', 'applicant', None),
    d7ab_annual_tax=('연간 납세사실증명서', 'Annual tax-payment certificate', 'business_entity', None),
    d7ab_same_group_original=('원근무처와 동일계열사 입증서류 (법인등기사항전부증명서 원본 등)', 'Proof the new workplace is in the same group as the current one (original corporate register, etc.)', 'business_entity', None),
    d7ab_branch_report_docs=('외국기업의 국내지사설치 신고(허가)관련 서류 (지사 설치허가서 등)', 'Documents on the foreign company\'s Korean branch report/permit (branch establishment permit, etc.)', 'business_entity', None),
    d7ab_sales_record_corp=('영업실적증명 서류 (법인 납세사실증명원 등)', 'Proof of business performance (corporate tax-payment certificate, etc.)', 'business_entity', None),
    # ---- D-8
    d7ab_dispatch_employment_period=('주재활동의 경우 파견명령서(파견기간 명시) 및 재직증명서', 'For intra-company transferees: dispatch order (stating the period) and certificate of employment', 'business_entity', None),
    d7ab_fdi_reg_copy=('외국인투자기업등록증 사본', 'Copy of the foreign-invested company registration', 'business_entity', None),
    d7ab_investment_funds=('투자자금 도입관련 입증서류 (현금출자: 외화반출허가(신고)서(해당자), 투자자금 도입 내역서 / 현물출자: 현물출자완료 확인서 사본, 세관 수입신고필증 사본)', 'Proof of the investment inflow (cash: foreign-currency export permit/report if applicable and the inflow record; in kind: copy of the in-kind contribution confirmation and the customs import declaration)', 'applicant', None),
    d7ab_capital_use=('자본금 사용내역 입증서류 (물품구매 영수증, 사무실 인테리어 비용, 국내은행 계좌 입출금 내역서 등)', 'Proof of how the capital was used (purchase receipts, office fit-out costs, Korean bank statements, etc.)', 'applicant', None),
    d7ab_premises_d8=('사업장 존재 입증 서류 (사무실 임대차 계약서, 사업장 전경·사무공간·간판 사진 등 자료)', 'Proof the business premises exist (office lease, photos of the premises, office space and sign, etc.)', 'business_entity', None),
    d7ab_home_business_experience=('해당 업종 또는 분야의 사업 경험 관련 국적국 서류 (필요시 징구)', 'Documents from your home country on business experience in the field (when requested)', 'applicant', None),
    d7ab_partner_funds=('공동사업자인 국민의 사업자금(사용 내역) 입증서류', 'Proof of the Korean co-owner\'s business funds (and their use)', 'business_entity', None),
    d7ab_joint_bizreg=('공동사업자가 표시된 사업자등록증 사본, 공동사업자약정서 원본', 'Copy of the business registration showing the co-owners, and the original co-ownership agreement', 'business_entity', None),
    d7ab_rnd_facility_docs=('연구개발시설 지정서 및 근무인력 명단 (성명, 직책, 학력, 연구경력, 근무분야 등)', 'R&D facility designation and staff list (name, position, education, research career, field)', 'business_entity', None),
    d7ab_corp_reg_bizreg=('법인등기사항전부증명서 및 사업자등록증 사본', 'Corporate register and copy of the business registration', 'business_entity', None),
    d7ab_degree_or_rec=('학위증명서 사본 또는 관계 중앙행정기관의 장의 추천서', 'Copy of your degree certificate, or a recommendation from the head of the competent central agency', 'applicant', None),
    d7ab_d84_points_docs=('점수제 해당 항목(및 점수) 입증 서류 (지식재산권 등록증 사본, 출원사실증명서, OASIS 이수 증서·입상확인서·선정공문 등)', 'Proof of the points items (copies of IP registrations, filing certificates, OASIS certificates, award or selection letters, etc.)', 'applicant', None),
    d7ab_startup_korea_rec=('스타트업 코리아 특별비자 추천서 (중소벤처기업부 발급)', 'Startup Korea special-visa recommendation (issued by the Ministry of SMEs and Startups)', 'other_third_party', None),
    d7ab_industrial_property=('산업재산권, 그 밖에 이에 준하는 기술과 그 사용에 관한 권리 등을 보유하고 있음을 입증하는 서류', 'Proof you hold industrial-property or equivalent technology rights', 'applicant', None),
    d7ab_office_lease=('사무실 임대차계약서', 'Office lease', 'business_entity', None),
    d7ab_d84_points_stay=('점수제 해당 항목 입증서류 (특허증·실용신안등록증·디자인등록증 사본, OECD 국가 지식재산권 입증서류, 출원사실증명서, OASIS 이수 증서 등)', 'Proof of the points items (copies of patent/utility/design registrations, OECD IP proof, filing certificates, OASIS certificates, etc.)', 'applicant', None),
    d7ab_kstartup_docs=('중기부 발행 K-startup 그랜드챌린지 참여 확인서, 중기부장관 추천 공문', 'K-Startup Grand Challenge participation confirmation and the minister\'s recommendation letter (Ministry of SMEs and Startups)', 'other_third_party', None),
    d7ab_mss_rec=('중기부장관 추천서', 'Recommendation from the Minister of SMEs and Startups', 'other_third_party', None),
    d7ab_ip_cert_copies=('특허증, 실용신안등록증, 디자인등록증, 상표등록증 등 사본', 'Copies of patent, utility-model, design or trademark registrations', 'applicant', None),
    d7ab_business_operation_proof=('사업운영 관련 입증서류', 'Proof of business operations', 'business_entity', None),
    # ---- D-9
    d7ab_equipment_contract=('설비도입계약서 또는 산업설비도입 입증서류', 'Equipment purchase contract or proof of the industrial-equipment import', 'business_entity', None),
    d7ab_inviter_bizreg=('초청회사의 사업자등록증 사본 또는 법인등기사항전부증명서', 'Copy of the inviting company\'s business registration or its corporate register', 'business_entity', None),
    d7ab_order_contract=('수주계약서 사본', 'Copy of the order (shipbuilding/plant) contract', 'business_entity', None),
    d7ab_d9_bizreg=('사업자등록증 사본, 영업허가증 사본 (해당자), 투자기업등록증 (소지자)', 'Copy of the business registration, business licence copy (if any) and investment company registration (if held)', 'applicant', None),
    d7ab_joint_agreement=('공동사업약정서 원본 및 사본 (해당자)', 'Co-business agreement, original and copy (if applicable)', 'applicant', None),
    d7ab_business_funds=('사업자금 도입관련 입증서류 (송금확인증, 외국환 매입증명서, 세관신고서, 해당국세관 반출신고서 등)', 'Proof of the business-fund inflow (remittance confirmation, foreign-exchange purchase certificate, customs declarations, etc.)', 'applicant', None),
    d7ab_sales_proof=('영업실적 입증서류 (수출입면장, 부가세예정 또는 확정 신고서 등)', 'Proof of sales (import/export licences, provisional or final VAT returns, etc.)', 'applicant', None),
    d7ab_premises_d9=('사업장 존재 입증서류 (임대차계약서, 사업장·사무공간·간판 사진 등 자료)', 'Proof the business premises exist (lease, photos of the premises, office space and sign, etc.)', 'applicant', None),
    d7ab_hire_pledge=('국민고용예정서약서 (해당자만 제출)', 'Pledge to hire Korean nationals (only if applicable)', 'applicant', None),
    d7ab_trade_number=('무역업 고유번호부여증 (한국무역협회 발행) 사본', 'Copy of the trade business number certificate (issued by KITA)', 'applicant', None),
    d7ab_joint_agreement_partners=('공동사업약정서 원본 및 사본 (공동 사업자인 경우)', 'Co-business agreement, original and copy (for joint owners)', 'applicant', None),
    d7ab_premises_lease=('사업장 존재 입증서류 (임대차계약서 등)', 'Proof the business premises exist (lease, etc.)', 'applicant', None),
    d7ab_d9_points_cvi=('점수제 해당 점수 입증서류 (수출입실적증명서, 경력증명서·학위증·교육이수증, 자본금 입증서류, TOPIK 점수표, 사회통합프로그램 이수증 등)', 'Proof of the points (import/export certificate, career/degree/training certificates, capital proof, TOPIK score, KIIP certificate, etc.)', 'applicant', None),
    d7ab_d9_points_stay=('점수제 해당 입증서류', 'Proof of the points items', 'applicant', None),
    d7ab_status_change_reason=('체류자격변경 사유서', 'Statement of reasons for the status change', 'applicant', None),
    d7ab_dispatch_or_employment_hq=('파견명령서 또는 재직증명서 (본사 발급)', 'Dispatch order or certificate of employment (issued by the head office)', 'employer', None),
    d7ab_ship_or_equipment_contract=('선박수주계약서 또는 설비도입계약서', 'Shipbuilding order contract or equipment purchase contract', 'business_entity', None),
    d7ab_tax_proof_company=('납세사실증명 (외국인 개인납세내역이 없는 경우 회사 것으로 접수)', 'Proof of tax payment (the company\'s, if you have no personal tax record)', 'applicant', None),
    d7ab_partner_income=('공동사업자의 연간 소득 입증 서류 (해당자)', 'Proof of the co-owner\'s annual income (if applicable)', 'applicant', None),
    d7ab_oasis_cert=('OASIS 교육 이수증 (해당자)', 'OASIS course completion certificate (if applicable)', 'applicant', None),
    d7ab_personal_tax_cert=('개인 납세사실증명원 (해당외국인) (예: 납세조합 발행 을종근로소득원천징수영수증, 세무서 발행 소득금액증명원)', 'Personal tax-payment certificate (e.g. the tax association\'s withholding receipt or the tax office\'s income certificate)', 'applicant', None),
    d7ab_business_ok_proof=('정상적으로 사업을 영위하고 있음을 입증하는 서류 (소득금액증명원, 납세증명서, 납세사실증명원 등)', 'Proof the business is operating normally (income certificate, tax clearance, tax-payment certificate, etc.)', 'applicant', None),
    d7ab_korean_employment_proof=('국민 고용 입증서류 (원천징수․고용보험 등 6개월 이상 계속 입증서류)', 'Proof of employing Korean nationals (withholding or employment-insurance records for 6+ continuous months)', 'applicant', None),
    d7ab_bizreg_residence=('사업자등록증, 임대차계약서 등 주거지 입증서류', 'Business registration, and proof of residence such as a lease', 'applicant', None),
    # ---- D-10
    d7ab_degree_d10=('학위증 (졸업증명서, 학위취득증명서도 인정)', 'Degree certificate (graduation or degree-conferral certificates also accepted)', 'applicant', None),
    d7ab_univ_rank_proof=('대학 순위 소명자료 (세계 대학순위 적용 대상자)', 'Evidence of the university\'s ranking (if the world-ranking criterion applies)', 'applicant', None),
    d7ab_career_proof=('근무경력 증빙서류 (근무기간, 장소, 직종 등이 포함된 경력증명서 또는 재직증명서)', 'Proof of work experience (career or employment certificate showing period, place and occupation)', 'applicant', None),
    d7ab_training_proof=('국내 연수 활동 증빙서류 (연구·연수기관의 수료증명서, 교환학생 경력 확인 증명 등)', 'Proof of training in Korea (completion certificate from the research/training institution, exchange-student confirmation, etc.)', 'applicant', None),
    d7ab_korean_proof=('한국어능력 입증서류', 'Proof of Korean ability', 'applicant', None),
    d7ab_recommendation_visa=('추천서 (관계 중앙행정기관장 고용추천서 또는 재외공관장 추천 문서)', 'Recommendation (employment recommendation from a central agency, or a mission\'s internal recommendation)', 'other_third_party', None),
    d7ab_recommendation_stay=('고용추천서 (관계 중앙행정기관장 추천 또는 재외공관장 추천)', 'Employment recommendation (from a central agency or an overseas mission)', 'other_third_party', None),
    d7ab_high_income_proof=('고소득 전문가 입증서류 (자국 공공기관이 발행한 전년도 근로소득 입증서류)', 'Proof of high income (last year\'s earned income issued by a public body at home)', 'applicant', None),
    d7ab_kr_degree=('국내 정규 대학 전문학사 이상 학위증 (또는 졸업증명서)', 'Associate degree or higher from a Korean university (or graduation certificate)', 'applicant', None),
    d7ab_korean_proof_level4=('한국어능력 입증서류 (사회통합프로그램 중간평가 합격증 또는 사전평가 점수표(81점 이상), 한국어능력시험(TOPIK) 4급 이상 유효 성적표)', 'Korean-ability proof (KIIP mid-term pass or placement score of 81+, or a valid TOPIK level 4+ result)', 'applicant', None),
    d7ab_rank200_proof=('최근 3년 이내 THE 또는 QS 세계 대학순위 200위 이내 대학 소명자료 (해당자)', 'Evidence the university ranked within THE or QS top 200 in the last 3 years (if applicable)', 'applicant', None),
    d7ab_topik6=('한국어능력시험(TOPIK) 6급 유효 성적표 (해당자)', 'Valid TOPIK level 6 result (if applicable)', 'applicant', None),
    d7ab_intern_contract=('인턴계약서', 'Internship contract', 'employer', None),
    d7ab_ambassador_rec=('양국 공관 대사 추천서', 'Recommendation from the ambassadors of both countries', 'other_third_party', None),
    d7ab_degree_bachelor=('학사(국내 전문학사) 학위 이상 학력증명서', 'Proof of a bachelor\'s degree or higher (Korean associate degree)', 'applicant', None),
    d7ab_startup_plan=('기술창업계획서', 'Technology start-up plan', 'applicant', None),
    d7ab_ip_or_filing=('특허증·실용신안등록증·디자인등록증 사본 또는 특허 등 출원사실증명서 (해당자)', 'Copy of a patent/utility/design registration, or a patent filing certificate (if applicable)', 'applicant', None),
    d7ab_oasis_proof=('창업이민종합지원시스템 교육과정 이수증 또는 교육참여 확인서 (해당자)', 'OASIS course completion or participation certificate (if applicable)', 'applicant', None),
    d7ab_oecd_ip=('OECD 국가 지식재산권 보유 사실을 확인할 수 있는 공적 서류 (해당자)', 'Official proof you hold intellectual property in an OECD country (if applicable)', 'applicant', None),
    d7ab_top_univ_grad=('해외 우수대학(본교) 졸업(예정)증명서', 'Graduation (or expected graduation) certificate from the top overseas university (main campus)', 'applicant', None),
    d7ab_top_univ_grad_stay=('국내·외 우수대학(본교) 졸업(예정)증명서', 'Graduation (or expected graduation) certificate from the top Korean or overseas university (main campus)', 'applicant', None),
    d7ab_intern_plan=('인턴활동 계획서', 'Internship activity plan', 'applicant', None),
    d7ab_intern_univ_proof=('최근 3년 이내 세계 대학순위 THE 200위, QS 500위 이내 소명자료 및 학위과정(첨단기술분야만 해당) 재학증명서 또는 졸업증명서(학위증)', 'Evidence of a THE top-200 / QS top-500 ranking in the last 3 years, and an enrollment or graduation certificate for the (high-tech) degree programme', 'applicant', None),
    d7ab_intern_labor_contract=('인턴근로계약서 (인턴 기업, 인턴활동 분야, 인턴 기간 필수 명시)', 'Internship employment contract (must state the company, the high-tech field and the period)', 'employer', None),
    d7ab_intern_company_docs=('초청 기업(기관) 사업자등록증(또는 고유번호증), 법인등기부등본, 고용보험가입자 명부, 연구시설 현황자료', 'Inviting company\'s business registration (or unique number), corporate register, employment-insurance roster and research-facility data', 'employer', None),
    d7ab_intern_company_eligibility=('첨단기술인턴 초청이 가능한 기업(기관)임을 입증할 수 있는 서류 (택1: 상장기업 연구시설 입증서류, 기업부설연구소인정서 또는 연구개발전담부서인정서, 첨단기술기업지정서, 벤처기업확인서)', 'Proof the company may invite high-tech interns (one of: listed-company research-facility proof, corporate R&D centre or R&D department recognition, high-tech company designation, venture confirmation)', 'employer', None),
    d7ab_school_grad=('국내 초·중·고교 졸업증명서 또는 동등한 학력 소지 입증 서류', 'Graduation certificates from Korean primary, middle and high school, or proof of equivalent education', 'applicant', None),
    d7ab_youth_checklist=('국내 성장 기반 외국인 청소년 자격변경 체크리스트 (붙임7)', 'Status-change checklist for foreign youth raised in Korea (annex 7)', 'applicant', None),
    d7ab_kiip_cert=('사회통합프로그램 이수증 (해당자)', 'KIIP completion certificate (if applicable)', 'applicant', None),
    d7ab_abroad_reason=('중도 해외 장기 체류 사유서 및 소명자료 (해당자, 붙임8)', 'Statement and evidence on long stays abroad in between (if applicable, annex 8)', 'applicant', None),
    d7ab_korean_proof_level3=('한국어능력 입증서류 (사회통합프로그램 3단계 이수증(사전평가 61점 이상 성적증명서 포함) 또는 한국어능력시험(TOPIK) 3급 이상 유효 성적표)', 'Korean-ability proof (KIIP level 3 certificate incl. placement score 61+, or a valid TOPIK level 3+ result)', 'applicant', None),
    d7ab_caregiver_cert=('한국보건복지인재원 발급 요양보호사 교육수료증명서', 'Care-worker training completion certificate issued by the Korea Health and Welfare Human Resources Development Institute', 'applicant', None),
    d7ab_new_contract_possible=('국내에서 출국하지 않고 새로운 근로계약 체결이 가능함을 입증하는 서류 (이적동의서: 이전 근무처에서 잔여 근로계약 기간이 1개월 이상 있는 경우)', 'Proof you may sign a new employment contract without leaving Korea (a release consent if over a month remains on the previous contract)', 'employer', None),
    d7ab_degree_cert=('학위증', 'Degree certificate', 'applicant', None),
    d7ab_korean_proof_pt=('한국어능력 입증자료 (한국어능력시험(TOPIK) 성적표 등)', 'Proof of Korean ability (TOPIK result, etc.)', 'applicant', None),
    d7ab_d10_pt_confirm=('구직 시간제 취업 확인서', 'Job-seeker part-time work confirmation', 'employer', None),
)

NOTES = dict(notes_ko=[OFFICER_NOTE_KO], notes_en=[OFFICER_NOTE_EN])
VISA_FORM = '사증발급신청서 (별지 제17호 서식), 여권, 표준규격사진 1매, 수수료'
VISA_FORM_COPY = '사증발급신청서 (별지 제17호 서식), 여권사본, 표준규격사진 1매, 수수료'
CVI_FORM = '사증발급인정신청서 (별지 제21호 서식), 여권, 표준규격사진 1매'
CVI_FORM_COPY = '사증발급인정신청서 (별지 제21호 서식), 여권사본, 표준규격사진 1매'
PROXY = '대리인 신청시 : 위임장, 대리인 재직증명서, 대리인 신분증 추가 제출'


def visa_form(copy=False):
    a = VISA_FORM_COPY if copy else VISA_FORM
    return [item('d7ab_visa_app', anchor=a), item('passport_copy' if copy else 'passport', anchor=a), item('photo', anchor=a), item('fee', anchor=a)]


def cvi_form(copy=False):
    a = CVI_FORM_COPY if copy else CVI_FORM
    return [item('d7ab_cvi_app', anchor=a), item('passport_copy' if copy else 'passport', anchor=a), item('photo', anchor=a)]


def proxy():
    return item('d7ab_proxy_docs', 'ADDITIONAL_IF_APPLICABLE', anchor=PROXY, applies_when_ko='대리인이 신청하는 경우', applies_when_en='If an agent applies')


# ==========================================================================
# A-1 외교 · A-2 공무 · A-3 협정 — 사증 (visa manual pp. 7-13)
# ==========================================================================
guidance('A-1', 'visa_issuance', manual=VISA, section='외교(A-1) 공관장 재량으로 발급할 수 있는 사증 — 1. 외교(A-1) 체류자격 사증발급', anchor='외교(A-1) 자격 해당자에 대한 단수 또는 복수사증',
         summary_ko='외교(A-1) 사증은 사증발급신청서·여권·사진·수수료와 파견·재직 증명서류 또는 해당국 외교부장관의 협조공한을 냅니다. 외교사절단·영사기관 구성원의 동반가족은 본국 발급 가족관계 입증서류를 더합니다.',
         summary_en='An A-1 visa needs the visa form, passport, photo and fee plus proof of dispatch/employment or a cooperation letter from your foreign minister. Accompanying family of mission or consular members add family-relationship proof issued at home.',
         docs=visa_form() + [
             item('d7ab_a1_dispatch_or_mofa', anchor='파견, 재직을 증명하는 서류 또는 해당국 외교부장관의 협조공한'),
             item('d7ab_a1_family_proof', 'CONDITIONAL_REQUIRED', anchor='본국에서 발급한 가족관계증명서, 출생증명서 등 가족관계 입증서류',
                  applies_when_ko='외국정부의 외교사절단이나 영사기관 구성원의 동반가족', applies_when_en='Accompanying family of a foreign diplomatic mission or consular post member'),
         ],
         conditions_ko=['신분증명서의 제시 등으로 해당 신분임이 확인되면 협조공한은 구술서로 갈음할 수 있습니다.', '외교관 여권을 소지하고 체류목적이 외교활동이어야 하며, 입국목적이 외교활동이 아니면 그 목적에 맞는 체류자격의 사증을 받아야 합니다.'],
         conditions_en=['If your status is confirmed (e.g. by showing your ID), a note verbale can replace the cooperation letter.', 'You must hold a diplomatic passport and come for diplomatic activity; for any other purpose, get the visa for that purpose.'],
         **NOTES)

guidance('A-2', 'visa_issuance', manual=VISA, section='공무(A-2) 공관장 재량으로 발급할 수 있는 사증 — 1. 공무(A-2) 체류자격 사증발급', anchor='공무(A-2)의 체류자격에 해당하는 자에 대한 단수사증',
         summary_ko='공무(A-2) 사증은 사증발급신청서·여권·사진·수수료와 파견·재직 증명서류 또는 해당국 외교부장관이나 소속부처 장관의 공한(공무수행임을 명시)을 냅니다.',
         summary_en='An A-2 visa needs the visa form, passport, photo and fee plus proof of dispatch/employment or a letter from your foreign minister or ministry stating the official duty.',
         docs=visa_form() + [item('d7ab_a2_dispatch_or_letter', anchor='파견, 재직을 증명하는 서류 또는 해당국 외교부장관이나 소속부처 장관의 공한')],
         conditions_ko=['관용여권 또는 신분증명서 소지 여부를 확인하며, 일반여권 소지자는 공무수행자 또는 국제기구 근무자와 그 가족에 한합니다.'],
         conditions_en=['An official passport or ID is checked; ordinary-passport holders qualify only as officials on duty or staff of international organisations and their families.'],
         **NOTES)

guidance('A-3', 'visa_issuance', manual=VISA, section='협정(A-3) 공관장 재량으로 발급할 수 있는 사증 — 1. 협정(A-3) 체류자격 사증발급', anchor='협정(A-3)의 체류자격에 해당하는 자에 대한 단수사증',
         summary_ko='협정(A-3) 사증은 사증발급신청서·여권·사진·수수료와 파견·재직 증명서류 또는 해당국 외교부장관이나 소속부처 장관의 공한을 냅니다. Fulbright 협정대상자(A-3-99)는 한미교류재단 협조공한상의 장학금 수혜기간으로 복수사증을 받습니다.',
         summary_en='An A-3 visa needs the visa form, passport, photo and fee plus proof of dispatch/employment or a letter from your foreign minister or ministry. Fulbright grantees (A-3-99) get a multiple visa for the scholarship period in the Fulbright Commission\'s letter.',
         docs=visa_form() + [item('d7ab_a2_dispatch_or_letter', anchor='파견, 재직을 증명하는 서류 또는 해당국 외교부장관이나 소속부처 장관의 공한')],
         **NOTES)

guidance('A-3', 'visa_issuance_confirmation', manual=VISA, state='NOT_APPLICABLE', completeness='SOURCE_ONLY',
         section='협정(A-3) 사증발급인정서 발급대상', anchor='사증발급인정서 발급 제외 대상임',
         summary_ko='협정(A-3)은 사증발급인정서 발급 제외 대상입니다.', summary_en='A-3 is excluded from the confirmation of visa issuance.')

# ==========================================================================
# B-1 사증면제 · B-2 관광통과 — 사증 (visa manual pp. 14-22)
# ==========================================================================
guidance('B-1', 'visa_issuance', manual=VISA, state='NOT_APPLICABLE', completeness='SOURCE_ONLY',
         section='사증면제(B-1) 공관장 재량으로 발급할 수 있는 사증', anchor='해당사항 없음',
         summary_ko='사증면제(B-1)는 공관장 재량으로 발급할 수 있는 사증이 "해당사항 없음"입니다. 대한민국과 사증면제협정을 체결한 국가의 국민이 그 협정에 의한 활동을 하려는 경우의 자격입니다.',
         summary_en='For B-1 the manual lists no visa a mission may issue at its discretion ("not applicable"). B-1 is for nationals of countries with a visa-waiver agreement doing what that agreement allows.',
         conditions_ko=['사증면제협정 체결국가 국민도 체류기간이 협정기간(통상 3월)을 초과하거나 단기취업 등 영리 또는 유급행위에 종사하려면 반드시 해당 사증을 받아 입국해야 합니다.'],
         conditions_en=['Even nationals of visa-waiver countries must enter on the proper visa to stay longer than the agreement period (usually 3 months) or to do paid work such as short-term employment.'])
guidance('B-1', 'visa_issuance_confirmation', manual=VISA, state='NOT_APPLICABLE', completeness='SOURCE_ONLY',
         section='사증면제(B-1) 사증발급인정서 발급대상', anchor='사증면제(B-1), 관광통과(B-2) 자격은 사증발급인정서 발급 제외대상임',
         summary_ko='사증면제(B-1)와 관광통과(B-2) 자격은 사증발급인정서 발급 제외대상입니다.', summary_en='B-1 and B-2 are excluded from the confirmation of visa issuance.')
guidance('B-2', 'visa_issuance', manual=VISA, state='NOT_APPLICABLE', completeness='SOURCE_ONLY',
         section='관광통과(B-2) 공관장 재량으로 발급할 수 있는 사증', anchor='해당사항 없음',
         summary_ko='관광통과(B-2)는 공관장 재량으로 발급할 수 있는 사증이 "해당사항 없음"입니다. 관광·통과 등의 목적으로 사증 없이 입국하려는 사람의 자격입니다.',
         summary_en='For B-2 the manual lists no visa a mission may issue at its discretion ("not applicable"). B-2 is for people entering without a visa for tourism or transit.',
         conditions_ko=['사증면제협정 또는 관광통과 목적으로 입국한 사람은 원칙적으로 체류기간 연장이나 체류자격 변경허가를 받을 수 없으므로, 체류기간이 협정기간 또는 법무부장관이 따로 정하는 기간을 초과하면 반드시 사증을 받아 입국해야 합니다.'],
         conditions_en=['People entering under a visa-waiver agreement or for tourism/transit are in principle not granted extensions or status changes, so a stay beyond the agreement period or the period the Minister sets requires entering on a visa.'])
guidance('B-2', 'visa_issuance_confirmation', manual=VISA, state='NOT_APPLICABLE', completeness='SOURCE_ONLY',
         section='관광통과(B-2) 사증발급인정서 발급대상', anchor='사증면제(B-1), 관광통과(B-2) 자격은 사증발급인정서 발급 제외대상임',
         summary_ko='사증면제(B-1)와 관광통과(B-2) 자격은 사증발급인정서 발급 제외대상입니다.', summary_en='B-1 and B-2 are excluded from the confirmation of visa issuance.')

# ==========================================================================
# A-1 외교 · A-2 공무 · A-3 협정 — 체류 (stay manual pp. 14-21)
# ==========================================================================
A_FAMILY_SCOPE_KO = '동반가족 범위: 법적 혼인관계의 배우자(복수 배우자는 1명만), 미성년인 미혼 동거 자녀, 「초·중등교육법」상 학교에 정규 학생으로 등록된 20세 이하 미혼 동거자녀, 대학 이상에서 정규 과정 교육·연구를 하려는 26세 이하 미혼 동거자녀, 소득활동에 종사하지 않는 조건으로 입국한 본인 또는 배우자의 60세 이상 부모, 별도 생계유지가 불가능한 성년 미혼 동거 장애인 자녀.'
A_FAMILY_SCOPE_EN = 'Accompanying family: legal spouse (only one), minor unmarried children living together, unmarried children aged 20 or under enrolled in a primary/secondary school, unmarried children aged 26 or under in regular university education or research, parents (of you or your spouse) aged 60+ entering on condition of not earning income, and adult unmarried disabled children who cannot support themselves.'


def a_activities(code, label):
    guidance(code, 'activities_outside_status', section=f'{label} 체류자격외 활동 — 1. 주한외국공관원 가족의 국내취업', anchor=f'{label} 자격을 소지한“주한외국공관원 가족”의 국내취업은 상호주의에 따라',
             summary_ko=f'{label} 자격을 가진 주한외국공관원 가족은 상호주의에 따라 외교부장관(외교사절담당관)의 추천을 받은 경우에만 국내취업을 위한 체류자격외 활동허가를 받습니다. 여권, 통합신청서, 수수료, 외교부 고용추천서(필수)와 해당 체류자격별 필요서류를 냅니다.',
             summary_en=f'Family members of foreign mission staff holding {label} may work only with a recommendation from the Ministry of Foreign Affairs, under reciprocity. Submit the passport, integrated form, fee, the ministry\'s employment recommendation (mandatory) and the documents for the target status.',
             period_ko='근로계약 범위 내에서 최장 2년 (주한미국대사관 공관원가족은 재임기간 및 고용계약 기간 범위 내 최장 3년)', period_en='Up to 2 years within the employment contract (US embassy staff families: up to 3 years within the term and contract)',
             fee_ko='자격외 활동 12만원 (주한 미국 공관원의 동반가족은 상호주의에 따라 면제)', fee_en='KRW 120,000 (waived for accompanying family of US embassy staff, by reciprocity)',
             docs=[item('passport', anchor='여권, 통합신청서'), item('app_form_34', anchor='여권, 통합신청서'), item('fee', anchor='수수료(자격외 활동 12만원)'),
                   item('d7ab_mofa_employment_rec', anchor='외교부(외교사절담당관)에서 받은 고용추천서(필수)'),
                   item('d7ab_target_status_docs', anchor='해당 체류자격별 체류자격외 활동 필요서류(자격요건 등 구비)')],
             conditions_ko=['취업허용 국가는 ’24. 1월 현재 29개국이며, 허용 범위는 D-1, D-6, E-1~E-5, E-6(E-6-2 제외), E-7(E-7-4 제외)입니다. 주한캐나다·미국대사관 공관원가족은 허용 범위가 더 넓습니다.',
                            '신청절차: 주한외국공관이 외교부에 고용추천서 발급 공한을 요청하고, 외교부가 관할 출입국·외국인관서에 공문을 보내면, 동반가족 또는 대리인이 신청서류와 고용추천서를 제출합니다.',
                            '주한미국대사관 공관원가족은 취업사실을 확인할 수 있는 서류(사업자등록증, 고용계약서 등) 이외의 업체 요건·학력·경력·범죄경력 등 서류 제출이 불요합니다.'],
             conditions_en=['Work is allowed for nationals of 29 countries (as of Jan 2024) in D-1, D-6, E-1~E-5, E-6 (not E-6-2) and E-7 (not E-7-4); families of Canadian and US embassy staff have a wider scope.',
                            'Procedure: the mission asks the ministry for the recommendation, the ministry sends it to the immigration office, then the family member or an agent files the application with it.',
                            'US embassy families need only proof of the job (business registration, employment contract, etc.), not the other company, education, career or criminal-record documents.'],
             **NOTES)
    guidance(code, 'activities_outside_status', scenario='intl-org-family', section=f'{label} 체류자격외 활동 — 2. 국제기구 직원의 동반가족', anchor=f'{label} 자격을 소지한 국제기구 직원의 동반가족에 대한 체류자격외 활동 허가',
             summary_ko=f'대한민국과 협정을 맺고 국내에 주소지를 둔 국제기구에서 {label} 자격으로 근무하는 직원의 배우자와 미성년 자녀는 상호주의와 관계없이, 단순노무 분야를 제외한 모든 체류자격의 활동에 대해 체류자격외 활동허가를 받을 수 있습니다. 외교부 고용추천서는 필요 없습니다.',
             summary_en=f'Spouses and minor children of {label} staff at an international organisation based in Korea under an agreement can get permission for any status\'s activity except simple labour, regardless of reciprocity. No ministry recommendation is needed.',
             period_ko='1년 (체류자격외 활동허가 일반원칙에 따름)', period_en='1 year (general rule for activity permits)',
             fee_ko='자격외 활동 12만원', fee_en='KRW 120,000',
             docs=[item('passport', anchor='여권, 통합신청서'), item('app_form_34', anchor='여권, 통합신청서'), item('fee', anchor='수수료(자격외 활동 12만원)'),
                   item('d7ab_target_status_docs', anchor='해당 체류자격별 체류자격외 활동 필요서류(자격요건 등 구비)')],
             conditions_ko=['녹색기후기금(GCF) 사무국 직원은 배우자·미성년 자녀 외에 직원이 경제적으로 부양하는 가계 구성원인 자녀도 허용됩니다.', '허용되지 않는 활동: D-3, E-9, E-10, H-2 등 단순노무 분야.'],
             conditions_en=['For GCF secretariat staff, children who are economically dependent household members are also covered.', 'Not allowed: simple-labour statuses such as D-3, E-9, E-10, H-2.'],
             **NOTES)


a_activities('A-1', '외교(A-1)')
a_activities('A-2', '공무(A-2)')

guidance('A-1', 'status_grant', section='외교(A-1) 체류자격 부여', anchor='①신청서(별지 제34호 서식), 여권 ②출생증명서 사본 ③대사관 협조공한 ④부양자의 외국공관원 신분증',
         summary_ko='국내에서 출생한 외교(A-1) 가족은 출생일부터 90일 이내에 신청서·여권과 출생증명서 사본, 대사관 협조공한, 부양자의 외국공관원 신분증으로 체류자격 부여를 신청합니다.',
         summary_en='A child of an A-1 family born in Korea applies for a status grant within 90 days of birth with the form, passport, a copy of the birth certificate, the embassy\'s cooperation letter and the supporting parent\'s mission ID.',
         timing_ko='출생일부터 90일 이내 신청', timing_en='Apply within 90 days of birth',
         docs=[item('app_form_34', anchor='①신청서(별지 제34호 서식), 여권 ②출생증명서 사본'), item('passport', anchor='①신청서(별지 제34호 서식), 여권 ②출생증명서 사본'),
               item('d7ab_birth_cert_copy', anchor='출생증명서 사본 ③대사관 협조공한'), item('d7ab_embassy_letter', anchor='③대사관 협조공한 ④부양자의 외국공관원 신분증'),
               item('d7ab_supporter_mission_id', anchor='부양자의 외국공관원 신분증')],
         **NOTES)

guidance('A-1', 'status_change', section='외교(A-1) 체류자격 변경허가', anchor='외교(A-1) 자격 이외의 자격으로 입국 시 외교(A-1) 자격으로 체류자격 변경 허가',
         summary_ko='외교사절단·영사기관 구성원, 외교사절과 동등한 특권·면제를 받는 사람, 그 동반가족이 외교(A-1) 이외의 자격으로 입국했다면 외교(A-1)로 변경할 수 있습니다. 신청서·여권과 파견·재직 증명서류를 내고, 구성원은 자국 대사관 협조 공문을, 동반가족은 가족관계 입증서류와 주체류자의 신분증을 더합니다.',
         summary_en='Mission or consular members, people with equivalent privileges and immunities, and their accompanying family who entered on another status can change to A-1. Submit the form, passport and proof of dispatch/employment; members add their embassy\'s letter, family members add family-relationship proof and the principal\'s ID.',
         period_ko='재직기간 내', period_en='Within the term of service',
         docs=[item('d7ab_app_form', anchor='신청서, 여권, 자국 대사관의 협조 공문, 파견·재직을 증명하는 서류'), item('passport', anchor='신청서, 여권, 자국 대사관의 협조 공문'),
               item('d7ab_home_embassy_letter', 'CONDITIONAL_REQUIRED', anchor='자국 대사관의 협조 공문, 파견·재직을 증명하는 서류',
                    applies_when_ko='대한민국 정부가 접수한 외국정부의 외교사절단이나 영사기관의 구성원', applies_when_en='Members of a foreign diplomatic mission or consular post accepted by Korea'),
               item('d7ab_dispatch_employment', anchor='파견·재직을 증명하는 서류', notes_ko='동반가족은 주체류자(① 또는 ②에 해당하는 사람)의 파견·재직 증명서류를 냅니다.', notes_en='Accompanying family submit the principal\'s proof of dispatch/employment.'),
               item('d7ab_family_birth_proof', 'CONDITIONAL_REQUIRED', anchor='출생증명서, 가족관계증명서 등 가족관계 입증서류', applies_when_ko='동반가족', applies_when_en='Accompanying family'),
               item('d7ab_principal_id', 'CONDITIONAL_REQUIRED', anchor='①또는②에 해당하는 사람의 신분증 및 파견·재직을 증명하는 서류', applies_when_ko='동반가족', applies_when_en='Accompanying family')],
         conditions_ko=[A_FAMILY_SCOPE_KO], conditions_en=[A_FAMILY_SCOPE_EN],
         **NOTES)

A2_SELF_FAMILY = [
    item('app_form_34', anchor='① 신청서(별지 제34호 서식), 여권'), item('passport', anchor='① 신청서(별지 제34호 서식), 여권'),
    item('d7ab_a2_dispatch_or_ministry', 'CONDITIONAL_REQUIRED', anchor='파견․재직을 입증하는 서류 또는 자국 소속부처의 장의 협조공문', applies_when_ko='본인', applies_when_en='The official'),
    item('d7ab_status_relation_proof', 'CONDITIONAL_REQUIRED', anchor='출생증명서 등 신분관계 입증서류', applies_when_ko='부양가족', applies_when_en='Dependent family'),
    item('d7ab_supporter_duty_id', 'CONDITIONAL_REQUIRED', anchor='부양자의 공무수행을 증명하는 신분증', applies_when_ko='부양가족', applies_when_en='Dependent family'),
]
guidance('A-2', 'status_grant', section='공무(A-2) 체류자격 부여', anchor='출생일부터 90일 이내 신청',
         summary_ko='공무(A-2) 체류자격 부여는 출생일부터 90일 이내에 신청합니다. 본인은 신청서·여권과 파견·재직 입증서류 또는 자국 소속부처의 장의 협조공문을, 부양가족은 신청서·여권과 출생증명서 등 신분관계 입증서류, 부양자의 공무수행 신분증을 냅니다.',
         summary_en='Apply for an A-2 status grant within 90 days of birth. The official submits the form, passport and proof of dispatch/employment or the home ministry\'s letter; dependants submit the form, passport, a birth certificate or other relationship proof and the supporting official\'s ID.',
         timing_ko='출생일부터 90일 이내 신청', timing_en='Apply within 90 days of birth',
         docs=A2_SELF_FAMILY, **NOTES)
guidance('A-2', 'status_change', section='공무(A-2) 체류자격 변경허가', anchor='주한 외국공관 등에 주재근무하는 자 중 공무자격(A-2)의 동반가족 범위',
         summary_ko='공무(A-2)로의 체류자격 변경은 본인이 신청서·여권과 파견·재직 입증서류 또는 자국 소속부처의 장의 협조공문을, 부양가족이 신청서·여권과 출생증명서 등 신분관계 입증서류, 부양자의 공무수행 신분증을 냅니다.',
         summary_en='To change to A-2, the official submits the form, passport and proof of dispatch/employment or the home ministry\'s letter; dependants submit the form, passport, a birth certificate or other relationship proof and the supporting official\'s ID.',
         docs=A2_SELF_FAMILY, doc_page_window=1,
         conditions_ko=[A_FAMILY_SCOPE_KO], conditions_en=[A_FAMILY_SCOPE_EN],
         **NOTES)

guidance('A-3', 'activities_outside_status', section='협정(A-3) 체류자격외 활동 — 1. 협정(A-3)자격 소지자의 체류자격외 활동 범위', anchor='협정(A-3)자격 소지자의 체류자격외 활동 범위',
         summary_ko='협정(A-3) 자격 소지자는 교수(E-1)부터 특정활동(E-7)까지의 활동에 대해 체류자격외 활동허가를 받을 수 있으며, 입국 후 A-3로 자격변경을 받은 경우에도 허용됩니다. 신청서·여권·수수료, 복무확인서, SOFA ID 카드, 해당 자격 관련 서류를 내고 SPONSOR는 소속 기관장(고용주)의 동의서를 더합니다.',
         summary_en='A-3 holders can get permission for E-1 to E-7 activities, also when they changed to A-3 after entry. Submit the form, passport, fee, certificate of service, SOFA ID card and the target status\'s documents; SPONSORs add their unit head\'s (employer\'s) consent.',
         docs=[item('app_form_34', anchor='①신청서(별지34호), 여권, 수수료 ②복무확인서'), item('passport', anchor='①신청서(별지34호), 여권, 수수료 ②복무확인서'), item('fee', anchor='①신청서(별지34호), 여권, 수수료 ②복무확인서'),
               item('d7ab_service_cert', anchor='②복무확인서 ③ S.O.F.A  ID 카드'), item('d7ab_sofa_id', anchor='S.O.F.A  ID 카드 ④해당 자격 관련 서류'),
               item('d7ab_target_status_papers', anchor='④해당 자격 관련 서류'),
               item('d7ab_sponsor_consent', 'CONDITIONAL_REQUIRED', anchor='⑤SPONSOR인 경우 소속 기관장(고용주)의 동의서', applies_when_ko='SPONSOR인 경우', applies_when_en='If you are the SPONSOR')],
         conditions_ko=['자격외 활동 중인 근무처를 변경하려면 새로운 근무처로 자격외 활동을 다시 신청합니다.'],
         conditions_en=['To change the workplace of the permitted activity, apply again for the new workplace.'],
         **NOTES)

guidance('A-3', 'status_grant', section='협정(A-3) 체류자격 부여 — 1. 국내 출생자', anchor='초청계약자 등이 발급한 복무확인서․재직증명서 또는 초청계약서',
         summary_ko='국내에서 출생한 협정(A-3) 가족은 출생일로부터 90일 이내에 신청서·여권, 출생증명서 등 가족관계 입증서류, 부양자의 신분증명서, 초청계약자 등이 발급한 복무확인서·재직증명서 또는 초청계약서로 신청합니다. 90일 이내 출국하면 별도허가가 필요 없습니다.',
         summary_en='A child of an A-3 family born in Korea applies within 90 days of birth with the form, passport, a birth certificate or other family proof, the supporting parent\'s ID and the certificate of service/employment or invitation contract. No permit is needed if the child leaves within 90 days.',
         timing_ko='출생일로부터 90일 이내 신청 (90일 이내 출국하는 경우 별도허가 불필요)', timing_en='Apply within 90 days of birth (not needed if leaving within 90 days)',
         docs=[item('app_form_34', anchor='① 신청서(별지 제34호 서식), 여권'), item('passport', anchor='① 신청서(별지 제34호 서식), 여권'),
               item('d7ab_a3_family_proof', anchor='출생증명서 등 가족관계 입증서류'), item('d7ab_supporter_id', anchor='부양자의 신분증명서'),
               item('d7ab_invitation_contractor_docs', anchor='초청계약자 등이 발급한 복무확인서․재직증명서 또는 초청계약서')],
         **NOTES)

guidance('A-3', 'status_change', section='협정(A-3) 체류자격 변경허가 — 1. SOFA 해당자', anchor='SOFA 해당자 신청서류',
         summary_ko='SOFA 해당자는 다른 체류자격(등록외국인 포함)에서 협정(A-3)으로 변경할 수 있습니다. 본인은 신청서·여권, SPONSOR 복무확인서(현역) 또는 재직증명서(군속), 초청계약자는 초청계약서를 내고, 피부양가족은 가족관계 입증서류, 부양자의 신분증명서, 복무확인서·재직증명서 또는 초청계약서, 11세 미만은 부·모의 SOFA ID 카드를 냅니다.',
         summary_en='SOFA personnel can change to A-3 from any other status (including registered foreigners). The member submits the form, passport and the SPONSOR certificate of service (active duty) or employment (civilian), contractors add the invitation contract; dependants submit family proof, the sponsor\'s ID, the certificate of service/employment or invitation contract and, under 11, a parent\'s SOFA ID card.',
         docs=[item('app_form_34', anchor='① 신청서(별지34호), 여권'), item('passport', anchor='① 신청서(별지34호), 여권'),
               item('d7ab_sponsor_service_cert', 'CONDITIONAL_REQUIRED', anchor='SPONSOR 복무확인서(현역) 또는 재직증명서(군속)', applies_when_ko='본인', applies_when_en='The SOFA member'),
               item('d7ab_invitation_contract', 'CONDITIONAL_REQUIRED', anchor='③ 초청계약서(초청계약자)', applies_when_ko='초청계약자 본인', applies_when_en='Invited contractors'),
               item('d7ab_a3_family_proof', 'CONDITIONAL_REQUIRED', anchor='출생증명서 등 가족관계 입증서류', applies_when_ko='피부양가족', applies_when_en='Dependants'),
               item('d7ab_supporter_id', 'CONDITIONAL_REQUIRED', anchor='부양자의 신분증명서', applies_when_ko='피부양가족', applies_when_en='Dependants'),
               item('d7ab_invitation_contractor_docs', 'CONDITIONAL_REQUIRED', anchor='초청계약자 등이 발급한 복무확인서․재직증명서 또는 초청계약서', applies_when_ko='피부양가족', applies_when_en='Dependants'),
               item('d7ab_parent_sofa_id', 'CONDITIONAL_REQUIRED', anchor='11세 미만자는 부․모의 SOFA ID 카드', applies_when_ko='피부양가족', applies_when_en='Dependants')],
         conditions_ko=['A-3 소지자가 퇴직 등으로 자격을 잃은 뒤 국내에서 변경 가능한 다른 체류자격으로 계속 체류하려면 신분상실일로부터 30일 이내에 자격변경을 신청합니다(30일 이내 출국하면 별도 허가 불필요).'],
         conditions_en=['An A-3 holder who loses the status (e.g. on retirement) and wants to stay on another status that allows an in-country change must apply within 30 days of losing it (no permit needed if leaving within 30 days).'],
         **NOTES)
guidance('A-3', 'status_change', scenario='fulbright', section='협정(A-3) 체류자격 변경허가 — 2. Fulbright 협정 대상자', anchor='Fulbright 협정 대상자 체류자격 변경허가',
         summary_ko='A-3-99 사증을 받지 못하고 무비자로 입국한 Fulbright 협정 대상자는 신청서·여권, Fulbright I/D 카드, 한미교육위원단 협조공한으로 변경을 신청하며, 협조공한상의 장학금 수혜기간이 부여됩니다.',
         summary_en='Fulbright grantees who entered visa-free without an A-3-99 visa apply with the form, passport, Fulbright ID card and the Korean-American Educational Commission\'s letter; the scholarship period in the letter is granted.',
         period_ko='협조공한상의 장학금 수혜기간', period_en='The scholarship period stated in the letter',
         docs=[item('app_form_34', anchor='신청서(별지34호), 여권, Fulbright I/D 카드, 한미교육위원단 협조공한'), item('passport', anchor='신청서(별지34호), 여권, Fulbright I/D 카드, 한미교육위원단 협조공한'),
               item('d7ab_fulbright_id', anchor='Fulbright I/D 카드, 한미교육위원단 협조공한'), item('d7ab_kaec_letter', anchor='Fulbright I/D 카드, 한미교육위원단 협조공한')],
         **NOTES)

# 외국인등록 / 재입국허가: the sections list documents — replace the earlier summary-only rules.
A_REG_SUMMARY_KO = '외국인등록 면제 대상이지만 본인이 원하면 외국인등록증을 발급받을 수 있으며, 이 경우에도 등록사항변경 신고·체류지 변경 신고 등 등록외국인의 의무는 면제됩니다. 신청서, 여권원본, 반명함판 천연색 사진, 주한외국공관원 신분증 등 신분 입증서류를 냅니다.'
A_REG_SUMMARY_EN = 'You are exempt from registration but can get a residence card on request; the usual duties of registered foreigners (reporting changes, address changes, etc.) still do not apply. Submit the form, original passport, a colour photo and your mission ID or other proof of status.'
A_REENTRY_KO = '출국한 날로부터 1년 이내에 재입국하면 재입국허가가 면제됩니다. 단수사증을 가진 사람이 재임기간(공무수행기간, 신분존속기간 또는 협정상의 체류기간) 내에 재입국하려고 요청하면 재입국허가(단수·복수)를 받을 수 있으며, 재임기간 중 유효한 복수사증이 있으면 필요 없습니다.'
A_REENTRY_EN = 'Re-entry within one year of departure is exempt. Holders of a single-entry visa may, on request, get a single or multiple re-entry permit within their term (duty, status or agreement period); not needed if you hold a valid multiple visa for the term.'
for code in ('A-1', 'A-2', 'A-3'):
    drop(code, 'registration')
    drop(code, 'reentry')
    guidance(code, 'registration', state='CONDITIONAL', section=f'{code} 외국인등록', anchor='외국인등록 면제 대상이나 본인이 원할 경우 외국인등록증 발급',
             summary_ko=A_REG_SUMMARY_KO, summary_en=A_REG_SUMMARY_EN,
             docs=[item('app_form_34', anchor='신청서(별지 제34호), 여권원본, 반명함판 천연색 사진'), item('passport_original', anchor='여권원본, 반명함판 천연색 사진'),
                   item('d7ab_photo_half', anchor='반명함판 천연색 사진(3.5×4.5㎝)'), item('d7ab_mission_id_proof', anchor='주한외국공관원 신분증 등 신분 입증서류')],
             **NOTES)
for code in ('A-1', 'A-2'):
    guidance(code, 'reentry', state='CONDITIONAL', section=f'{code} 재입국허가', anchor='출국한 날로부터 1년 이내 재입국하려는 경우 면제',
             summary_ko=A_REENTRY_KO, summary_en=A_REENTRY_EN, period_ko='국내 재임기간 내 (공항만에서도 복수 가능)', period_en='Within your term in Korea (multiple permits also at ports)',
             docs=[item('app_form_34', anchor='신청서(별지34호),여권, 외교관 신분증, 대사관 협조 공한, 재직 증명 서류'), item('passport', anchor='신청서(별지34호),여권, 외교관 신분증'),
                   item('d7ab_diplomat_id', anchor='외교관 신분증, 대사관 협조 공한'), item('d7ab_embassy_letter', anchor='대사관 협조 공한, 재직 증명 서류'), item('d7ab_employment_proof', anchor='대사관 협조 공한, 재직 증명 서류')],
             **NOTES)
guidance('A-3', 'reentry', state='CONDITIONAL', section='A-3 재입국허가', anchor='출국한 날로부터 1년 이내 재입국하려는 경우 면제',
         summary_ko=A_REENTRY_KO, summary_en=A_REENTRY_EN, period_ko='국내 재임기간 내 (공항만에서도 복수 가능)', period_en='Within your term in Korea (multiple permits also at ports)',
         docs=[item('app_form_34', anchor='①신청서(별지34호), 여권, SOFA ID카드'), item('passport', anchor='①신청서(별지34호), 여권, SOFA ID카드'),
               item('d7ab_sofa_id_both', anchor='SOFA ID카드(SPONSOR와 Dependent 모두 필요)'), item('d7ab_service_cert_departure', anchor='②복무확인서(재직증명서: 출국일과 동반 가족기재된 것)')],
         **NOTES)

# ==========================================================================
# D-7 / D-8 / D-9 — 대학 강연활동 (C-4-5) 체류자격외 활동 (same text in each chapter)
# ==========================================================================
LECTURE_ANCHOR = '①신청서(별지 34호 서식), 여권 및 외국인등록증, 수수료 ②총(학)장의 추천서'


def lecture_rule(code, label):
    return guidance(code, 'activities_outside_status', section=f'{label} 체류자격외 활동 — 외국인투자기업 CEO 등 우수전문인력의 대학 강연활동', anchor='대학에서 90일 이내 강의활동을 하려는 자에 대한 단기취업(C-4-5)자격으로의 자격외 활동',
                    summary_ko='투자자 등(D-7, D-8, D-9) 중 국내기업(투자기업 포함)에서 상근이사 이상으로 근무하는 사람이 대학에서 90일 이내 강의를 하려면 단기취업(C-4-5) 체류자격외 활동허가를 받습니다. 신청서·여권·외국인등록증·수수료, 총(학)장의 추천서, 고유번호증(사업자등록증) 사본, 고용계약서 원본·사본, 원근무처장의 동의서를 냅니다.',
                    summary_en='D-7, D-8 or D-9 holders working as full-time directors or above at a Korean company (incl. investment companies) who want to lecture at a university for up to 90 days get a C-4-5 activity permit. Submit the form, passport, residence card, fee, the president\'s/dean\'s recommendation, the university\'s unique-number (business registration) copy, the employment contract (original and copy) and the current employer\'s consent.',
                    docs=[item('app_form_34', anchor=LECTURE_ANCHOR), item('passport', anchor=LECTURE_ANCHOR), item('arc', anchor=LECTURE_ANCHOR), item('fee', anchor=LECTURE_ANCHOR),
                          item('d7ab_dean_rec', anchor='②총(학)장의 추천서'), item('d7ab_unique_no_copy', anchor='③고유번호증(사업자등록증)사본'),
                          item('contract_original_copy', anchor='④고용계약서원본 및 사본', role='educational_institution'), item('d7ab_origin_employer_consent', anchor='⑤원근무처장의 동의서')],
                    conditions_ko=['원래의 체류목적을 침해하지 않는 범위에서 정규교육기관(초·중·고 및 대학)의 교육을 받는 것은 체류기간 범위 내에서 별도 허가가 필요 없습니다.'],
                    conditions_en=['Attending a regular school or university without undermining your original purpose needs no permit within your period of stay.'],
                    **NOTES)


def not_workplace(code, label, anchor):
    guidance(code, 'workplace_change', state='NOT_APPLICABLE', completeness='SOURCE_ONLY', section=f'{label} 근무처의 변경․추가', anchor=anchor,
             summary_ko=f'{label}은(는) 근무처 변경·추가 허가(신고) 대상이 아니며, 소속기관 변경은 외국인등록사항 변경신고로 처리합니다. 같은 계열회사 내 이동도 외국인등록사항 변경(변동)신고로 처리합니다.',
             summary_en=f'{label} is not subject to the workplace change/addition permit or report; a change of affiliated organisation is filed as a change of registration details, including moves within the same group.')


def no_grant(code, label, anchor='해당사항 없음'):
    guidance(code, 'status_grant', state='NOT_APPLICABLE', completeness='SOURCE_ONLY', section=f'{label} 체류자격 부여', anchor=anchor,
             summary_ko=f'{label}의 체류자격 부여는 "해당사항 없음"입니다.', summary_en=f'Status grant is "not applicable" for {label}.')


# ==========================================================================
# D-7 주재
# ==========================================================================
guidance('D-7', 'visa_issuance', manual=VISA, section='주재(D-7) 공관장 재량으로 발급할 수 있는 사증 — 1. 외국기업 국내지사 주재', anchor='중국인 국내주재지사 등의 주재원',
         summary_ko='공관장 재량으로 발급하는 주재(D-7) 사증은 중국인 국내주재지사 등의 주재원(공기업 또는 사기업에 1년 이상 고용된 직원)과 그 동반가족(F-3)에게 유효기간 2년 이내 복수사증으로 발급하며, 그 밖의 경우는 사증발급인정서로 신청합니다. 외국기업 국내지사 주재 사증은 신청서·여권·사진·수수료와 외국 소재 회사 재직증명서, 파견명령서, 국내지점 설치 입증서류(설치허가서 사본), 지사·연락사무소 정상 운영 입증서류, 필수전문인력 입증서류를 냅니다.',
         summary_en='The D-7 visa a mission may issue at its discretion is for Chinese staff of a Korean branch (employed 1+ year by a public or private company) and their F-3 family, as a multiple-entry visa valid up to 2 years; other cases apply through a confirmation of visa issuance. A D-7 visa for a foreign company\'s Korean branch needs the form, passport, photo and fee plus the certificate of employment abroad, the dispatch order, proof of the Korean branch (permit copy), proof the branch/liaison office operates normally and proof you are essential professional staff.',
         docs=visa_form() + [
             item('d7ab_foreign_company_employment', anchor='② 외국 소재 회사 등 재직증명서'), item('d7ab_dispatch_order', anchor='③ 파견명령서'),
             item('d7ab_branch_permit', anchor='지사 또는 연락사무소 설치허가서 사본'),
             item('d7ab_branch_operation_proof', anchor='지사 또는 연락사무소가 정상적으로 운영되고 있음을 입증하는 서류'),
             item('d7ab_essential_staff_proof', anchor='필수전문인력임을 입증하는 서류(이력서, 경력증명서 등)')],
         conditions_ko=['국내 납세의무가 없는 비영리 연락사무소는 연락사무소 운영자금 도입실적 등으로 납세실적을 대체합니다.', '중국인 국내주재지사 등의 주재원(1년 이상 고용된 직원)과 동반가족(F-3)에게는 유효기간 2년 이내의 복수사증이 발급됩니다.'],
         conditions_en=['A non-profit liaison office with no Korean tax liability may replace tax records with records of its operating-fund inflows.', 'Chinese staff (employed 1+ year) posted to Korean branches and their families (F-3) receive multiple visas valid up to 2 years.'],
         **NOTES)
guidance('D-7', 'visa_issuance', scenario='overseas-hq', manual=VISA, section='주재(D-7) 공관장 재량으로 발급할 수 있는 사증 — 2. 해외진출 기업 근무 외국인력 국내 본사 주재', anchor='해외진출 기업 근무 외국인력 국내 본사 주재활동 해당자에 대한 1년 이하의 단․복수 사증발급',
         summary_ko='상장법인·공공기관의 해외지사에서 국내 본사로 파견되는 사람은 1년 이하 단·복수 사증을 받으며, 필수전문인력 입증서류, 본사 등기사항전부증명서, 해외직접투자(해외지점설치) 신고수리서, 해외 송금 입증서류, 해외지사 등기·사업자등록, 해외지사 재직·납세 증명, 파견기간이 명시된 인사명령서를 냅니다.',
         summary_en='Staff of an overseas branch of a listed company or public institution posted to the Korean head office get a single/multiple visa of up to 1 year; submit proof of essential staff, the head office register, the overseas investment (branch) report acceptance, remittance proof, the overseas branch\'s register or business registration, its employment and tax proof, and a personnel order stating the period.',
         docs=visa_form(copy=True) + [
             item('d7ab_essential_staff_proof', anchor='② 필수전문인력임을 입증하는 서류(이력서, 경력증명서 등)'),
             item('d7ab_hq_register_optional', anchor='본사의 등기사항전부증명서(본사가 공공기업인 경우 생략 가능)'),
             item('d7ab_odi_report', anchor='해외직접투자신고수리서 또는 해외지점설치신고수리서'), item('d7ab_remittance_proof', anchor='해외 송금확인 입증서류'),
             item('d7ab_overseas_branch_reg', anchor='해외지사의 법인등기사항전부증명서 또는 사업자등록증'),
             item('d7ab_overseas_employment_tax', anchor='해외지사에서의 재직증명서 및 납세사실증명'),
             item('d7ab_personnel_order', anchor='인사명령서(파견명령서) : 파견기간이 명시된 명령서일 것')],
         **NOTES)

D7_CVI = '주재(D-7) 사증발급인정서 발급대상'
guidance('D-7', 'visa_issuance_confirmation', manual=VISA, section=f'{D7_CVI} — 1. 외국기업 국내지사 등에서 주재활동', anchor='① 사증발급인정신청서 (별지 제21호 서식), 여권, 표준규격사진 1매 ② 초청사유서 ③ 필수전문인력임을 입증하는 서류(이력서, 경력증명서 등) ④ 외국 소재 회사 등 재직증명서',
         summary_ko='외국기업 국내지사 주재(D-7) 사증발급인정서는 신청서·여권·사진, 초청사유서, 필수전문인력 입증서류, 외국 소재 회사 재직증명서, 파견명령서, 국내지점 설치 입증서류, 지사·연락사무소 정상 운영 입증서류를 냅니다.',
         summary_en='A D-7 confirmation for a foreign company\'s Korean branch needs the form, passport and photo, the invitation statement, proof of essential staff, the certificate of employment abroad, the dispatch order, proof of the Korean branch and proof it operates normally.',
         docs=cvi_form() + [
             item('d7ab_invitation_reason', anchor='② 초청사유서 ③ 필수전문인력임을 입증하는 서류'), item('d7ab_essential_staff_proof', anchor='③ 필수전문인력임을 입증하는 서류(이력서, 경력증명서 등) ④ 외국 소재 회사'),
             item('d7ab_foreign_company_employment', anchor='④ 외국 소재 회사 등 재직증명서 ⑤ 파견명령서'), item('d7ab_dispatch_order', anchor='⑤ 파견명령서 ⑥ 국내지점 등 설치 입증서류'),
             item('d7ab_branch_permit_cvi', anchor='지사나 연락사무소 설치허가서 사본 또는 신고수리서 사본'),
             item('d7ab_branch_operation_proof', anchor='영업자금 또는 연락사무소 운영자금 도입실적'), proxy()],
         **NOTES)
guidance('D-7', 'visa_issuance_confirmation', scenario='overseas-hq', manual=VISA, section=f'{D7_CVI} — 2. 해외진출 기업 근무 외국인력 국내 본사 주재활동', anchor='④ 본사의 등기사항전부증명서 ⑤ 해외직접투자신고수리서 또는 해외지점설치신고수리서',
         summary_ko='해외진출 기업 국내 본사 주재 사증발급인정서는 신청서·여권 사본·사진, 초청사유서, 필수전문인력 입증서류, 본사 등기사항전부증명서, 해외직접투자(해외지점설치) 신고수리서, 해외 송금 입증서류, 해외지사 등기·사업자등록, 본사 납세사실증명, 파견기간이 명시된 인사명령서를 냅니다.',
         summary_en='The confirmation for a posting to the Korean head office needs the form, passport copy and photo, the invitation statement, proof of essential staff, the head office register, the overseas investment (branch) report acceptance, remittance proof, the overseas branch\'s register or business registration, the head office\'s tax proof and a personnel order stating the period.',
         docs=cvi_form(copy=True) + [
             item('d7ab_invitation_reason', anchor='② 초청사유서'), item('d7ab_essential_staff_proof', anchor='③ 필수전문인력임을 입증하는 서류(이력서, 경력증명서 등) ④ 본사의'),
             item('d7ab_hq_register', anchor='④ 본사의 등기사항전부증명서 ⑤'), item('d7ab_odi_report', anchor='⑤ 해외직접투자신고수리서 또는 해외지점설치신고수리서'),
             item('d7ab_remittance_proof', anchor='⑥ 해외 송금확인 입증서류'), item('d7ab_overseas_branch_reg', anchor='⑦ 해외지사의 법인등기사항전부증명서 또는 사업자등록증'),
             item('d7ab_hq_tax', anchor='⑧ 본사의 납세사실증명'), item('d7ab_personnel_order', anchor='⑨ 인사명령서(파견명령서) : 파견기간이 명시된 명령서일 것'), proxy()],
         **NOTES)
for scen, title, anc in (('russia', '3. 한․러 한시적 근로활동에 관한 협정 대상자', '한․러 한시적 근로활동에 관한 협정 대상자'),
                         ('uzbekistan', '4. 한․우즈벡 한시적 근로활동에 관한 협정 대상자', '한․우즈벡 한시적 근로활동에 관한 협정 대상자')):
    who_ko = '러시아 국민(대표사무소 직원, 회사집단 직원)' if scen == 'russia' else '우즈베키스탄 회사 집단과 근로계약을 맺고 국내 동일 회사 집단에서 근무하는 사람'
    who_en = 'Russian nationals (representative-office or company-group staff)' if scen == 'russia' else 'People employed by an Uzbek company group working at a Korean company of the same group'
    guidance('D-7', 'visa_issuance_confirmation', scenario=scen, manual=VISA, section=f'{D7_CVI} — {title}', anchor=anc,
             summary_ko=f'{who_ko}의 주재(D-7) 사증발급인정서는 신청서·여권·사진, 본사 발생 파견명령서, 영업자금 도입실적 입증서류, 납세사실증명, 국내지점 설치 입증서류, 부가가치세법에 따른 사업자등록증을 냅니다.',
             summary_en=f'The D-7 confirmation for {who_en} needs the form, passport and photo, the head-office dispatch order, proof of operating-fund inflows, tax-payment proof, proof of the Korean branch and the VAT business registration.',
             docs=cvi_form() + [
                 item('d7ab_hq_dispatch_order', anchor='② 본사발생 파견명령서'), item('d7ab_fx_funds_proof', anchor='③ 외국환매입증명서 등 영업자금 도입실적 입증서류'),
                 item('d7ab_tax_payment_proof', anchor='④ 납세사실증명'), item('d7ab_branch_permit_cvi', anchor='지사나 연락사무소 설치허가서 사본 또는 신고수리서 사본'),
                 item('d7ab_vat_biz_reg', anchor='‘부가가치세법’에 따른 사업자등록증'), proxy()],
             **NOTES)
for scen, title, anc, last in (('flc-member', '6-가. 외국법자문법률사무소에 파견되는 구성원 또는 소속 외국법자문사', '외국법자문법률사무소에 파견되는 구성원*또는 소속 외국법자문사**', 'member'),
                               ('flc-staff', '6-나. 외국법자문법률사무소에 파견되는 사무직원', '외국법자문법률사무소에 파견되는 사무직원', 'staff')):
    extra = (item('d7ab_flc_consultant_reg', anchor='⑥ 외국법자문사 등록증 (대한변호사협회 발행, 법 10조)') if last == 'member'
             else item('d7ab_career_cert_hq', anchor='⑥ 경력증명서 (본사1년 이상 근무요건 충족 여부 확인)'))
    guidance('D-7', 'visa_issuance_confirmation', scenario=scen, manual=VISA, section=f'{D7_CVI} — {title}', anchor=anc,
             summary_ko=('외국법자문법률사무소에 파견되는 구성원·소속 외국법자문사는' if last == 'member' else '외국법자문법률사무소에 파견되는 사무직원은')
             + ' 신청서·여권·사진, 외국법자문법률사무소 등록증, 국내지점 설치 신고서 및 사업자등록증, 영업자금 도입실적 입증서류, 본사 발행 파견명령서(파견기간 명시)와 '
             + ('외국법자문사 등록증을 냅니다. 1년 이상 본사 근무요건이 면제되어 경력증명서는 필요 없습니다.' if last == 'member' else '본사 1년 이상 근무를 확인하는 경력증명서를 냅니다.'),
             summary_en=('Members and foreign legal consultants posted to a foreign legal consultant office' if last == 'member' else 'Office staff posted to a foreign legal consultant office')
             + ' submit the form, passport and photo, the office registration, the branch report and business registration, proof of operating-fund inflows, the head-office dispatch order stating the period and '
             + ('the consultant registration; the one-year head-office requirement is waived, so no career certificate is needed.' if last == 'member' else 'a career certificate showing one year or more at the head office.'),
             docs=cvi_form() + [
                 item('d7ab_flc_office_reg', anchor='② 외국법자문법률사무소 등록증 (대한변호사협회 발행, 법 제18조)'),
                 item('d7ab_branch_report_bizreg', anchor='③ 국내지점 등 설치 신고서 (외국환은행 발행) 및 사업자등록증'),
                 item('d7ab_fx_funds_proof', anchor='④ 외국환매입증명서 등 영업자금 도입실적 입증서류'),
                 item('d7ab_dispatch_order_period', anchor='⑤ 파견명령서 (본사발행, 파견기간 명시)'), extra, proxy()],
             **NOTES)

no_grant('D-7', '주재(D-7)')
not_workplace('D-7', '주재(D-7)', '근무처 변경․추가 허가(신고) 대상 아님 : 외국인등록사항 변경신고')
lecture_rule('D-7', '주재(D-7)')

D7_CHANGE_FORM = '① 신청서(별지34호 서식), 여권 및 외국인등록증, 표준규격사진1장,수수료'
guidance('D-7', 'status_change', section='주재(D-7) 체류자격 변경허가 — 2. 기업투자(D-8) 자격 소지자의 동일계열 외국기업 주재(D-7)로의 변경', anchor='기업투자(D-8)자격 소지자의 동일계열 외국기업의 주재(D-7)자격으로의 자격변경 허가',
         summary_ko='기업투자(D-8)로 외국인투자기업에서 필수전문인력으로 일하다 동일계열 외국기업의 국내지사·자회사 등으로 파견(전근)되는 합법체류자는 주재(D-7)로 변경할 수 있습니다. 신청사유서, 파견명령서 원본 또는 재직예정증명서, 지사·연락사무소 설치허가서 사본, 동일계열 입증서류, 영업자금 도입실적 증명, 사무실 임대차 계약서 원본, 근무 중인 외국인 현황을 냅니다.',
         summary_en='Lawful D-8 residents working as essential staff of a foreign-invested company who are transferred to a Korean branch or subsidiary of the same foreign group can change to D-7. Submit a statement of reasons, the original dispatch order or a certificate of prospective employment, the branch/liaison permit copy, proof of the same group, proof of operating funds, the original office lease and a list of foreign employees.',
         docs=[item('app_form_34', anchor=D7_CHANGE_FORM), item('passport', anchor=D7_CHANGE_FORM), item('arc', anchor=D7_CHANGE_FORM), item('photo1', anchor=D7_CHANGE_FORM), item('fee', anchor=D7_CHANGE_FORM),
               item('d7ab_change_reason', anchor='② 신청사유서'), item('d7ab_dispatch_or_prospective', anchor='③ 파견명령서(외국본사 발행) 원본 또는 재직예정증명서'),
               item('d7ab_foreign_branch_permit', anchor='④ 외국기업의 국내지사 설치허가서 사본 또는 연락사무소 설치허가서 사본(외국환은행 발행)'),
               item('d7ab_same_group_proof', anchor='⑤ 동일계열 외국기업 입증 서류(법인등기사항전부증명서 등)'),
               item('d7ab_target_company_funds', anchor='⑥ 근무하려는 기업의 연간납세증명서 또는 외국환매입증명서 등 영업자금 도입실적 증명서류'),
               item('d7ab_office_lease_original', anchor='⑦ 사무실 임대차 계약서 원본'), item('d7ab_foreign_staff_list', anchor='⑧ 근무 중인 외국인 현황'),
               item('d7ab_personal_tax_original', 'MAY_BE_REQUESTED_BY_OFFICER', anchor='개인 납세사실증명원 원본(근로소득원천징수영수증(작년) 또는 소득금액증명원(최근 기록)', applies_when_ko='필요 시 추가 서류', applies_when_en='Additional document when needed')],
         conditions_ko=['신설지사와 과거 출입국관리법 위반 신청자는 반드시 실태조사를 합니다.'], conditions_en=['New branches and applicants with past immigration violations are always subject to an on-site check.'],
         **NOTES)
guidance('D-7', 'status_change', scenario='chile', section='주재(D-7) 체류자격 변경허가 — 3. 단기방문(C-3-4) 사증을 소지한 칠레국민', anchor='단기방문(C-3-4)사증을 소지한 칠레국민에 대한 주재(D-7), 기업투자(D-8), 무역경영(D-9)자격으로 체류자격 변경허가',
         summary_ko='단기방문(C-3-4) 사증을 가진 칠레국민으로 관리자·임원 또는 전문지식 관련 자격으로 일방당사국 기업에 고용되어 그 기업·자회사·계열사에서 근무하려는 사람은 주재(D-7) 등으로 변경할 수 있습니다. 재직증명서, 파견명령서, 국내 지점 설치 입증서류, 영업자금 도입실적, 이력서 또는 경력증명서, 사업자등록증 사본, 연간 납세사실증명서를 냅니다.',
         summary_en='Chilean nationals on a C-3-4 visa employed as managers, executives or specialists who will work at that company, its subsidiary or affiliate can change to D-7 etc. Submit the certificate of employment, dispatch order, proof of the Korean branch, proof of operating funds, a CV or career certificate, the business registration copy and the annual tax certificate.',
         docs=[item('app_form_34', anchor='① 신청서(별지34호 서식), 여권, 표준규격사진1장, 수수료 ② 외국소재 회사 등 재직증명서'), item('passport', anchor='① 신청서(별지34호 서식), 여권, 표준규격사진1장, 수수료 ② 외국소재'),
               item('photo1', anchor='표준규격사진1장, 수수료 ② 외국소재'), item('fee', anchor='수수료 ② 외국소재 회사 등 재직증명서'),
               item('d7ab_foreign_company_employment', anchor='② 외국소재 회사 등 재직증명서'), item('d7ab_hq_dispatch_order_stay', anchor='③ 파견명령서(본사 발행) ④ 국내 지점'),
               item('d7ab_branch_proof_stay', anchor='④ 국내 지점 등 설치 입증서류(지사 또는 연락사무소 설치허가서 등)'),
               item('d7ab_fx_funds_proof', anchor='⑤ 외국환매입증명서 등 영업자금 도입실적 입증서류 ⑥'), item('d7ab_cv_or_career', anchor='⑥ 이력서 또는 경력증명서'),
               item('business_reg_copy', anchor='⑦ 사업자등록증 사본 ⑧ 연간 납세사실증명서'), item('d7ab_annual_tax', anchor='⑧ 연간 납세사실증명서')],
         **NOTES)

# ==========================================================================
# D-8 기업투자
# ==========================================================================
no_grant('D-8', '기업투자(D-8)')
not_workplace('D-8', '기업투자(D-8)', '기업투자(D-8) 자격은 ‘근무처 변경․추가 허가(신고)’ 대상 아님 : 외국인등록사항 변경신고')
lecture_rule('D-8', '기업투자(D-8)')
D8_D7_FORM = '①신청서(별지34호 서식) 여권 및 외국인등록증, 표준규격사진1장, 수수료 ②파견명령서(본사 발행)'
guidance('D-8', 'activities_outside_status', scenario='d7-same-group', section='주재(D-7) 체류자격외 활동 — 3. 기업투자(D-8) 자격 소지자에 대한 동일계열 회사 내의 주재(D-7) 활동', anchor='기업투자(D-8) 자격 소지자에 대한 동일계열 회사 내의 주재(D-7)자격의 체류자격외 활동',
         summary_ko='기업투자(D-8) 자격 소지자가 동일계열 회사에서 주재(D-7) 활동을 하려면 체류자격외 활동허가를 받습니다. 본사 발행 파견명령서, 원근무처와 동일계열사 입증서류, 사업자등록증 사본, 국내지사 설치 신고(허가) 서류, 원근무처장의 동의서, 영업실적 증명서류를 냅니다.',
         summary_en='D-8 holders who will do D-7 work at a company of the same group get an activity permit. Submit the head-office dispatch order, proof of the same group, the business registration copy, the branch report/permit documents, the current employer\'s consent and proof of business performance.',
         docs=[item('app_form_34', anchor=D8_D7_FORM), item('passport', anchor=D8_D7_FORM), item('arc', anchor=D8_D7_FORM), item('photo1', anchor=D8_D7_FORM), item('fee', anchor=D8_D7_FORM),
               item('d7ab_hq_dispatch_order_stay', anchor='②파견명령서(본사 발행) ③원근무처와'), item('d7ab_same_group_original', anchor='③원근무처와 동일계열사 입증서류(법인등기사항전부증명서 원본 등)'),
               item('business_reg_copy', anchor='④사업자등록증 사본 ⑤외국기업의'), item('d7ab_branch_report_docs', anchor='⑤외국기업의 국내지사설치 신고(허가)관련 서류(지사 설치허가서 등)'),
               item('d7ab_origin_employer_consent', anchor='⑥원근무처장의 동의서 ⑦영업실적증명'), item('d7ab_sales_record_corp', anchor='⑦영업실적증명 서류 -법인 납세사실증명원 등')],
         **NOTES)

D8_CHANGE_EXCEPT_KO = '허가의 예외(자격변경 불가, 출국 후 사증을 받아 입국): 기술연수(D-3), 비전문취업(E-9), 선원취업(E-10), 방문취업(H-2), 기타(G-1) 자격 소지자, 관광취업(H-1)으로 입국한 아일랜드·프랑스·영국 국민(협정에 자격변경을 허용하지 않는 국가), 그리고 투자자가 아닌 사람을 임원으로 등재한 뒤 신청하는 경우(특정활동(E-7) 대상). 기업투자(D-8)로 변경이 허용되지 않는 자격도 투자의 진정성이 인정되는 등 특별한 사유가 있으면 정밀심사 후 변경이 허용될 수 있습니다.'
D8_CHANGE_EXCEPT_EN = 'Exceptions (no change; leave and enter on a visa): holders of D-3, E-9, E-10, H-2 or G-1, nationals of Ireland, France and the UK who entered on H-1 (their agreements do not allow a change), and cases where a non-investor is registered as an officer (that is E-7). Statuses that normally cannot change to D-8 may be allowed after close review for special reasons such as a genuine investment.'
D8_FORM = '① 신청서(별지34호 서식), 여권 및 외국인등록증, 표준규격사진1장'
D8_FORM_ARC = '① 신청서(별지34호 서식), 여권, 외국인등록증(해당자), 표준규격사진1장'


def d8_form(arc_optional=False):
    a = D8_FORM_ARC if arc_optional else D8_FORM
    arc = item('arc', 'ADDITIONAL_IF_APPLICABLE', anchor='외국인등록증(해당자)', applies_when_ko='해당자', applies_when_en='If applicable') if arc_optional else item('arc', anchor=a)
    return [item('app_form_34', anchor=a), item('passport', anchor=a), arc, item('photo1', anchor='표준규격사진1장')]


def small_investor(prefix=''):
    w = dict(applies_when_ko='투자금액 3억원 미만 개인투자자', applies_when_en='Individual investors of less than KRW 300 million')
    return [item('d7ab_capital_use', 'CONDITIONAL_REQUIRED', anchor='자본금 사용내역 입증서류', **w),
            item('d7ab_home_business_experience', 'MAY_BE_REQUESTED_BY_OFFICER', anchor='해당 업종 또는 분야의 사업 경험 관련 국적국 서류 (필요시 징구)', **w)]


guidance('D-8-1', 'status_change', section='기업투자(D-8) 체류자격 변경허가 — 1. 법인에 투자(D-8-1)한 외국인', anchor='1. 법인에 투자(D-8-1)한 외국인에 대한 체류자격 변경허가',
         summary_ko='법인 투자자(D-8-1)는 1억원 이상을 투자해 의결권 있는 주식의 10% 이상을 소유하거나 임원 파견 등 계약을 맺어야 합니다. 사업자등록증·법인등기·주주변동상황명세서, 투자기업등록증 사본, 투자자금 도입 입증서류, 영업실적 증명서, 체류지·사업장 입증서류를 내고, 3억원 미만 개인투자자는 자본금 사용내역 등을 더합니다.',
         summary_en='Corporate investors (D-8-1) must invest KRW 100 million or more and hold 10%+ of voting shares or have an officer-dispatch or similar contract. Submit the business registration, corporate register and shareholder-change statement, the investment company registration copy, proof of the investment inflow, business performance, proof of residence and of premises; individual investors under KRW 300 million add capital-use records.',
         docs=d8_form() + [
             item('corp_docs_d8', anchor='② 사업자등록증 사본, 법인등기사항전부증명서, 주주변동상황명세서 원본', role='business_entity'),
             item('fdi_company_reg_copy', anchor='③ 투자기업등록증 사본', role='business_entity'),
             item('dispatch_and_employment_d8', 'CONDITIONAL_REQUIRED', anchor='주재활동의 경우 파견명령서(파견기간이 명시된 해외 본사 및 해외 본사의 제3국 소재 지사 발행) 및 재직증명서', applies_when_ko='주재활동(파견)인 경우', applies_when_en='Intra-company transferees', role='business_entity'),
             item('d7ab_investment_funds', anchor='⑤ 투자자금 도입관련 입증서류'),
             item('business_performance', anchor='⑥ 영업실적(수출입실적 등) 증명서', role='business_entity'),
             residence(anchor='⑦ 체류지 입증서류(부동산 임대차계약서 등)'),
             item('d7ab_premises_d8', anchor='⑧ 사업장 존재 입증 서류 (사무실 임대차 계약서'),
         ] + small_investor(),
         conditions_ko=['투자자금은 본인 명의가 원칙이며, 배우자·미성년 자녀 명의 반입과 대리송금은 예외적으로 인정됩니다(3억원 이상 투자자는 부모·배우자 부모 명의도 추가 인정 가능).',
                        '외국인투자기업등록지위를 갖춘 금융지주회사가 100% 출자한 자회사의 필수전문인력은 금융지주회사의 인가서·외국인투자기업등록증, 자회사 등기·주주명부, 해외본사 파견명령서, 사업자등록증 사본을 냅니다.',
                        D8_CHANGE_EXCEPT_KO],
         conditions_en=['Funds should be in your own name; transfers in the name of a spouse or minor child, or by proxy, are accepted exceptionally (for KRW 300 million+, also parents and parents-in-law).',
                        'Essential staff of a 100% subsidiary of a financial holding company registered as foreign-invested submit the holding company\'s licence and registration, the subsidiary\'s register and shareholder list, the head-office dispatch order and business registrations.',
                        D8_CHANGE_EXCEPT_EN],
         **NOTES)
guidance('D-8-2', 'status_change', section='기업투자(D-8) 체류자격 변경허가 — 2. 벤처 투자(D-8-2) 외국인', anchor='2. 벤처 투자(D-8-2) 외국인에 체류자격 변경허가',
         summary_ko='벤처 투자자(D-8-2)는 사업자등록증·법인등기, 벤처기업(예비벤처기업)확인서, 지식재산권 등 우수 기술력 입증서류, 체류지 입증서류, 사무실 임대차계약서, 영업실적 증명서로 변경합니다.',
         summary_en='Venture investors (D-8-2) change with the business registration and corporate register, the (pre-)venture confirmation, proof of technology/IP, proof of residence, the office lease and business performance.',
         docs=d8_form(arc_optional=True) + [
             item('business_reg_corp_reg', anchor='② 사업자등록증 사본, 법인등기사항전부증명서', role='business_entity'),
             item('venture_docs', anchor='벤처기업확인서 또는 예비벤처기업확인서', role='business_entity'),
             item('ip_proof', anchor='지식재산권을 보유하는 등 우수한 기술력을 가지고 있음을 입증하는 서류', role='business_entity'),
             residence(anchor='⑤ 체류지 입증서류(부동산 등 임재차계약서 등)'),
             item('d7ab_office_lease', anchor='⑥ 사무실 임대차계약서'), item('business_performance', anchor='⑦ 영업실적(수출입실적 등) 증명서', role='business_entity')],
         conditions_ko=[D8_CHANGE_EXCEPT_KO], conditions_en=[D8_CHANGE_EXCEPT_EN],
         **NOTES)
guidance('D-8-3', 'status_change', section='기업투자(D-8) 체류자격 변경허가 — 3. 개인기업 투자(D-8-3)', anchor='3. 개인기업 투자(D-8-3)에 대한 체류자격 변경허가',
         summary_ko='국민이 경영하는 기업에 투자한 외국인(D-8-3)은 1억원 이상 투자해 출자총액의 10% 이상을 소유하고 사업자등록증에 한국인과 공동대표로 등재되어야 합니다. 공동사업자 표시 사업자등록증·공동사업자약정서, 투자기업등록증, 공동사업자인 국민의 사업자금 입증서류, 투자자금 도입 입증서류, 영업실적, 체류지·사업장 입증서류를 냅니다.',
         summary_en='Investors in a business run by a Korean national (D-8-3) must invest KRW 100 million+, own 10%+ of the capital and be listed as co-representative. Submit the business registration showing the co-owners and the co-ownership agreement, the investment company registration, proof of the Korean partner\'s funds, proof of the investment inflow, business performance and proof of residence and premises.',
         docs=d8_form(arc_optional=True) + [
             item('d7ab_joint_bizreg', anchor='② 공동사업자가 표시된 사업자등록증 사본, 공동사업자약정서 원본'),
             item('fdi_company_reg_copy', anchor='③ 투자기업등록증 사본', role='business_entity'),
             item('d7ab_partner_funds', anchor='④ 공동사업자인 국민의 사업자금(사용 내역) 입증서류'),
             item('dispatch_and_employment_d8', 'CONDITIONAL_REQUIRED', anchor='⑤ 주재활동의 경우 파견명령서', applies_when_ko='주재활동(파견)인 경우', applies_when_en='Intra-company transferees', role='business_entity'),
             item('d7ab_investment_funds', anchor='⑥ 투자자금 도입관련 입증서류'),
             item('business_performance', anchor='⑥ 영업실적(수출입실적 등) 증명서', role='business_entity'),
             residence(anchor='⑦ 체류지 입증서류(부동산 임대차계약서 등)'),
             item('d7ab_premises_d8', anchor='⑧ 사업장 존재 입증 서류 (사무실 임대차 계약서'),
         ] + small_investor(),
         conditions_ko=['공동사업자인 국민의 사업자금이 1억원 이상이어야 합니다.', D8_CHANGE_EXCEPT_KO], conditions_en=['The Korean co-owner\'s business funds must be KRW 100 million or more.', D8_CHANGE_EXCEPT_EN],
         **NOTES)
guidance('D-8-4', 'status_change', covers=['D-8-4S'], section='기업투자(D-8) 체류자격 변경허가 — 4. 기술창업(D-8-4) 외국인', anchor='4. 기술창업(D-8-4) 외국인에 대한 체류자격 변경허가',
         summary_ko='기술창업(D-8-4)은 신청서·여권·사진, 체류지 입증서류, 법인등기사항전부증명서·사업자등록증 사본, 학위증명서 사본 또는 관계 중앙행정기관의 장의 추천서를 기본으로 냅니다. 점수제 적용대상자는 지식재산권·OASIS 이수 등 점수 항목 입증서류를, 점수제 면제자(K-Startup 그랜드챌린지 참여자, 정부 창업지원사업 수혜자, 스타트업코리아 특별비자)는 중기부 확인서·추천서를 더합니다.',
         summary_en='Technology start-ups (D-8-4) submit the form, passport, photo, proof of residence, the corporate register and business registration, and a degree certificate copy or a central agency\'s recommendation. Points applicants add proof of the points items (IP, OASIS, etc.); points-exempt applicants (K-Startup Grand Challenge, government start-up programmes, Startup Korea special visa) add the ministry\'s confirmation or recommendation.',
         docs=[item('d7ab_app_form', anchor='신청서, 여권, 표준규격 사진, 체류지 입증서류(부동산 임대차 계약서 등)'), item('passport', anchor='신청서, 여권, 표준규격 사진, 체류지 입증서류'),
               item('photo', anchor='신청서, 여권, 표준규격 사진, 체류지 입증서류'), residence(anchor='체류지 입증서류(부동산 임대차 계약서 등)'),
               item('d7ab_corp_reg_bizreg', anchor='법인등기사항전부증명서 및 사업자등록증 사본'),
               item('d7ab_degree_or_rec', anchor='학위증명서 사본 또는 관계 중앙행정기관의 장의 추천서'),
               item('d7ab_d84_points_stay', 'CONDITIONAL_REQUIRED', anchor='점수제 적용대상자 제출서류', applies_when_ko='점수제 적용대상자', applies_when_en='Points-system applicants'),
               item('d7ab_kstartup_docs', 'CONDITIONAL_REQUIRED', anchor='중기부 발행 K-startup 그랜드챌린지 참여 확인서, 중기부장관 추천 공문',
                    applies_when_ko='K-Startup 그랜드 챌린지 참여자 (확인서 및 추천서는 최초 체류자격변경허가 시에만 징구)', applies_when_en='K-Startup Grand Challenge participants (only at the first status change)'),
               item('d7ab_mss_rec', 'CONDITIONAL_REQUIRED', anchor='(스타트업코리아 특별비자) 기본 제출서류 + 중기부장관 추천서', applies_when_ko='정부 창업지원사업 수혜자 또는 스타트업코리아 특별비자 대상자', applies_when_en='Government start-up programme beneficiaries or Startup Korea special-visa applicants')],
         conditions_ko=['점수제 적용대상자는 총 300점 중 60점 이상(필수항목 1개 이상 충족)이어야 하고, 대한민국 법인을 설립하고 법인등기·사업자등록을 마쳐야 합니다.',
                        '법인 설립이 완료되지 않은 경우 법인등기사항전부증명서·사업자등록증 사본 제출을 생략할 수 있으며, 6개월 이내에 제출하고 체류기간을 연장해야 합니다(점수제 적용 대상자 및 스타트업코리아 특별비자 대상자).',
                        D8_CHANGE_EXCEPT_KO],
         conditions_en=['Points applicants need 60 of 300 points (at least one mandatory item) and must have set up and registered a Korean corporation.',
                        'If the corporation is not yet set up, the register and business registration may be omitted but must be submitted within 6 months with an extension (points applicants and Startup Korea special-visa applicants).',
                        D8_CHANGE_EXCEPT_EN],
         **NOTES)

D8_EXT_RES = '체류지 입증서류(임대차계약서, 숙소제공 확인서, 체류기간 만료예고 통지우편물, 공공요금 납부영수증, 기숙사비 영수증 등)'
guidance('D-8-3', 'extension', section='기업투자(D-8) — 3. 개인기업 투자(D-8-3)에 대한 체류기간 연장허가', anchor='3. 개인기업 투자(D-8-3)에 대한 체류기간 연장허가',
         summary_ko='개인기업 투자자(D-8-3)는 공동사업자 표시 사업자등록증·공동사업자약정서, 투자기업등록증, 공동사업자인 국민의 사업자금 입증서류, 투자자금 도입 입증서류, 납세사실 또는 부가가치세 과세표준 증명, 영업실적, 사업장·체류지 입증서류로 연장하며, 3억원 미만 투자자는 자본금 사용내역 등을 더합니다.',
         summary_en='D-8-3 investors extend with the business registration showing the co-owners and the agreement, the investment company registration, proof of the Korean partner\'s funds, proof of the investment inflow, tax or VAT base proof, business performance and proof of premises and residence; investors under KRW 300 million add capital-use records.',
         docs=d8_form(arc_optional=True) + [
             item('d7ab_joint_bizreg', anchor='② 공동사업자가 표시된 사업자등록증 사본, 공동사업자약정서 원본'),
             item('fdi_company_reg_copy', anchor='③ 투자기업등록증 사본', role='business_entity'),
             item('d7ab_partner_funds', anchor='④ 공동사업자인 국민의 사업자금(사용 내역) 입증서류'),
             item('dispatch_and_employment_d8', 'CONDITIONAL_REQUIRED', anchor='⑤ 주재활동의 경우 파견명령서', applies_when_ko='주재활동(파견)인 경우', applies_when_en='Intra-company transferees', role='business_entity'),
             item('investment_funds_proof', anchor='⑥ 투자자금 도입관련 입증서류'),
             item('vat_tax_docs', anchor='⑦ 개인 납세사실 증명서류 또는 부가가치세 과세표준 확인증명 관련서류'),
             item('business_performance', anchor='⑧ 영업실적(수출입실적 등) 증명서', role='business_entity'),
             item('d7ab_premises_d8', anchor='⑨ 사업장 존재 입증 서류 (사무실 임대차 계약서'),
             residence(anchor='⑩ ' + D8_EXT_RES),
         ] + small_investor(),
         **NOTES)
guidance('D-8-4', 'extension', covers=['D-8-4S'], section='기업투자(D-8) — 4. 기술창업(D-8-4(S)) 외국인에 대한 체류기간 연장허가', anchor='4. 기술창업(D-8-4(S)) 외국인에 대한 체류기간 연장허가',
         summary_ko='기술창업(D-8-4, D-8-4S)은 법인등기사항전부증명서·사업자등록증 사본, 사업운영 관련 입증서류, 납세증명서, 체류지 입증서류로 연장하며, 지식재산권 출원으로 자격변경을 받은 사람은 특허증 등 등록증 사본을 더합니다.',
         summary_en='Technology start-ups (D-8-4, D-8-4S) extend with the corporate register and business registration, proof of business operations, a tax clearance certificate and proof of residence; those whose change was based on an IP filing add copies of the registrations.',
         docs=d8_form(arc_optional=True) + [
             item('d7ab_corp_reg_bizreg', anchor='② 법인등기사항전부증명서 및 사업자등록증 사본'),
             item('d7ab_ip_cert_copies', 'CONDITIONAL_REQUIRED', anchor='③ 특허증(특허청), 실용신안등록증(특허청), 디자인등록증(특허청), 상표등록증(특허청) 등 사본',
                  applies_when_ko='지식재산권 출원으로 자격변경 허가를 받은 사람', applies_when_en='If your status change was granted on an IP filing'),
             item('d7ab_business_operation_proof', anchor='④ 사업운영 관련 입증서류'), item('tax_clearance', anchor='⑤ 납세증명서', role='business_entity'),
             residence(anchor='⑥ ' + D8_EXT_RES)],
         **NOTES)

D8_VISA = '기업투자(D-8) 공관장 재량으로 발급할 수 있는 사증'
INVEST_ANCHOR = '⑤ 투자자금 도입관련 입증서류'
guidance('D-8-1', 'visa_issuance', manual=VISA, section=f'{D8_VISA} — 1. 외국인 투자기업에서의 주재활동 (D-8-1)', anchor='해당자에 대한 기업투자(D-8-1) 사증발급 (특정국가 제외)',
         summary_ko='법인 투자(D-8-1) 사증은 원칙적으로 본국 소재 공관에 신청하며, 신청서·여권·사진·수수료와 주재활동 시 파견명령서·재직증명서, 외국인투자기업등록증 사본, 사업자등록증·법인등기·주주변동상황명세서, 투자자금 도입 입증서류를 냅니다. 3억원 미만 개인투자자는 자본금 사용내역, 사업장 존재 입증서류 등을 더합니다.',
         summary_en='A D-8-1 visa is normally applied for at the mission in your home country with the form, passport, photo and fee, the dispatch order and employment certificate for transferees, the foreign-invested company registration, the business registration, corporate register and shareholder-change statement, and proof of the investment inflow. Individual investors under KRW 300 million add capital-use and premises proof.',
         docs=visa_form() + [
             item('d7ab_dispatch_employment_period', 'CONDITIONAL_REQUIRED', anchor='② 주재활동의 경우 파견명령서(파견기간 명시) 및 재직증명서', applies_when_ko='주재활동(파견)인 경우', applies_when_en='Intra-company transferees'),
             item('d7ab_fdi_reg_copy', anchor='③ 외국인투자기업등록증 사본'),
             item('corp_docs_d8', anchor='④ 사업자등록증 사본, 법인등기사항전부증명서, 주주변동상황명세서 원본', role='business_entity'),
             item('d7ab_investment_funds', anchor=INVEST_ANCHOR),
             item('d7ab_premises_d8', 'CONDITIONAL_REQUIRED', anchor='사업장 존재 입증 서류 (사무실 임대차 계약서', applies_when_ko='투자금액 3억원 미만 개인투자자', applies_when_en='Individual investors of less than KRW 300 million'),
         ] + small_investor(),
         conditions_ko=['특정국가 국민은 이 공관장 재량 사증(D-8-1)의 대상에서 제외됩니다.', '신청인이 해외에 주재하며 사업체를 운영(영주권 등 장기거주자 포함)하면 주재하는 국가 소재 재외공관에서도 신청할 수 있습니다.'],
         conditions_en=['Nationals of the designated countries are excluded from this discretionary D-8-1 visa.', 'If you live and run a business abroad (incl. long-term residents), you may apply at the mission in that country.'],
         **NOTES)
guidance('D-8-2', 'visa_issuance', manual=VISA, section=f'{D8_VISA} — 2. 벤처기업을 설립한 자 등 (D-8-2)', anchor='벤처기업 육성에 관한 특별조치법에 따라 벤처기업을 설립한 자 등에 대한 기업투자(D-8-2) 사증발급',
         summary_ko='벤처 투자(D-8-2) 사증은 신청서·여권 사본·사진·수수료와 사업자등록증·법인등기, 벤처기업(예비벤처기업)확인서, 지식재산권 등 우수 기술력 입증서류를 냅니다.',
         summary_en='A D-8-2 visa needs the form, passport copy, photo and fee plus the business registration and corporate register, the (pre-)venture confirmation and proof of technology/IP.',
         conditions_ko=['중국 및 특정국가 국민은 이 공관장 재량 사증(D-8-2)의 대상에서 제외됩니다.'], conditions_en=['Nationals of China and the designated countries are excluded from this discretionary D-8-2 visa.'],
         docs=visa_form(copy=True) + [
             item('business_reg_corp_reg', anchor='② 사업자등록증 사본, 법인등기사항전부증명서', role='business_entity'),
             item('venture_docs', anchor='③ 벤처기업확인서 또는 예비벤처기업확인서', role='business_entity'),
             item('ip_proof', anchor='④ 지식재산권을 보유하는 등 우수한 기술력을 가지고 있음을 입증하는 서류', role='business_entity')],
         **NOTES)
guidance('D-8-3', 'visa_issuance', manual=VISA, section=f'{D8_VISA} — 3. 국민이 경영하는 기업에 투자하는 외국인 (D-8-3)', anchor='국민이 경영하는 기업에 투자하는 외국인에 대한 기업투자(D-8-3) 자격 사증발급',
         summary_ko='개인기업 투자(D-8-3) 사증은 신청서·여권·사진·수수료와 외국인투자기업등록증 사본, 공동사업자인 국민의 사업자금 입증서류, 공동사업자 표시 사업자등록증·공동사업자약정서, 투자자금 도입 입증서류를 내고, 3억원 미만 투자자는 자본금 사용내역 등을 더합니다.',
         summary_en='A D-8-3 visa needs the form, passport, photo and fee plus the foreign-invested company registration, proof of the Korean partner\'s funds, the business registration showing the co-owners and the agreement, and proof of the investment inflow; investors under KRW 300 million add capital-use proof.',
         docs=visa_form() + [
             item('d7ab_fdi_reg_copy', anchor='② 외국인투자기업등록증 사본'),
             item('d7ab_partner_funds', anchor='③ 공동사업자인 국민의 사업자금(사용 내역) 입증서류'),
             item('d7ab_joint_bizreg', anchor='④ 공동사업자가 표시된 사업자등록증 사본, 공동사업자약정서 원본'),
             item('d7ab_investment_funds', anchor=INVEST_ANCHOR),
             item('d7ab_premises_d8', 'CONDITIONAL_REQUIRED', anchor='사업장 존재 입증 서류 (사무실 임대차 계약서', applies_when_ko='투자금액 3억원 미만 신청자', applies_when_en='Applicants investing less than KRW 300 million'),
         ] + small_investor(),
         conditions_ko=['3억원 미만 소액투자자로서 사업 경험이 없는 사람은 정밀심사합니다.'], conditions_en=['Small investors (under KRW 300 million) without business experience are closely reviewed.'],
         **NOTES)
guidance('D-8-4', 'visa_issuance', manual=VISA, section=f'{D8_VISA} — 4. 기술창업자 (D-8-4)', anchor='지식재산권을 보유하거나 이에 준하는 기술력 등을 가진 기술창업자에 대한 기업투자(D-8-4) 사증발급',
         summary_ko='기술창업(D-8-4) 사증은 신청서·여권·사진·수수료와 법인등기사항전부증명서·사업자등록증 사본, 학위증명서 사본 또는 관계 중앙행정기관의 장의 추천서, 점수제 해당 항목 입증서류를 냅니다.',
         summary_en='A D-8-4 visa needs the form, passport, photo and fee plus the corporate register and business registration, a degree certificate copy or a central agency\'s recommendation, and proof of the points items.',
         docs=visa_form() + [
             item('d7ab_corp_reg_bizreg', anchor='② 법인등기사항전부증명서 및 사업자등록증 사본'),
             item('d7ab_degree_or_rec', anchor='③ 학위증명서 사본 또는 관계 중앙행정기관의 장의 추천서'),
             item('d7ab_d84_points_docs', anchor='④ 점수제 해당 항목( 및 점수) 입증 서류')],
         conditions_ko=['학위는 이미 취득한 경우만 인정하고 취득 예정자는 제외합니다.', '대한민국 법인을 설립하고 법인등기 및 사업자등록을 완료해야 합니다.'],
         conditions_en=['Only degrees already obtained count.', 'You must have set up a Korean corporation and completed its registration and business registration.'],
         **NOTES)
guidance('D-8-4S', 'visa_issuance', manual=VISA, section=f'{D8_VISA} — 4-1. 스타트업 코리아 특별비자 기술창업자 (D-8-4S)', anchor='중소벤처기업부 장관의 추천을 받은 기술창업자에 대한 기업투자(D-8-4S) 사증발급',
         summary_ko='스타트업 코리아 특별비자(D-8-4S)는 민간평가위원회 심사 승인과 중소벤처기업부장관의 추천을 받은 사람이 신청서·여권·사진, 법인등기사항전부증명서·사업자등록증 사본(제출 가능 시), 스타트업 코리아 특별비자 추천서를 냅니다.',
         summary_en='The Startup Korea special visa (D-8-4S) is for people approved by the private evaluation committee and recommended by the Minister of SMEs and Startups; submit the form, passport and photo, the corporate register and business registration (if available) and the recommendation.',
         docs=[item('d7ab_visa_app', anchor='① 사증발급신청서 (별지 제17호 서식), 여권, 표준규격사진 1매 ② 법인등기사항전부증명서 및 사업자등록증 사본 (제출 가능 시)'),
               item('passport', anchor='① 사증발급신청서 (별지 제17호 서식), 여권, 표준규격사진 1매 ② 법인등기'), item('photo', anchor='표준규격사진 1매 ② 법인등기사항전부증명서'),
               item('d7ab_corp_reg_bizreg', 'ADDITIONAL_IF_APPLICABLE', anchor='② 법인등기사항전부증명서 및 사업자등록증 사본 (제출 가능 시)', applies_when_ko='제출 가능 시', applies_when_en='If available'),
               item('d7ab_startup_korea_rec', anchor='③ 스타트업 코리아 특별비자 추천서 (중소벤처기업부 발급)')],
         conditions_ko=['법인설립이 완료되지 않은 경우 법인등기사항전부증명서·사업자등록증 사본 제출을 생략할 수 있으며, 입국 후 체류기간(6개월) 이내에 제출하여 체류기간을 연장해야 합니다.'],
         conditions_en=['If the corporation is not yet set up, these may be omitted but must be submitted within the 6-month stay after entry, with an extension.'],
         **NOTES)

D8_CVI = '기업투자(D-8) 사증발급인정서 발급대상'
guidance('D-8-1', 'visa_issuance_confirmation', manual=VISA, section=f'{D8_CVI} — 1. 대한민국 법인에 투자한 외국인 (D-8-1)', anchor='대한민국 법인에 투자한 외국인 기업투자(D-8-1) 자격',
         summary_ko='법인 투자(D-8-1) 사증발급인정서는 관할 출입국·외국인관서에 신청서·여권·사진과 주재활동 시 파견명령서·재직증명서, 외국인투자기업등록증 사본, 사업자등록증·법인등기·주주변동상황명세서, 투자자금 도입 입증서류를 내고, 3억원 미만 개인투자자는 자본금 사용내역 등을 더합니다.',
         summary_en='A D-8-1 confirmation is filed at the immigration office with the form, passport and photo, the dispatch order and employment certificate for transferees, the foreign-invested company registration, the business registration, corporate register and shareholder-change statement, and proof of the investment inflow; individual investors under KRW 300 million add capital-use proof.',
         docs=cvi_form() + [
             item('d7ab_dispatch_employment_period', 'CONDITIONAL_REQUIRED', anchor='② 주재활동의 경우 파견명령서(파견기간 명시) 및 재직증명서', applies_when_ko='주재활동(파견)인 경우', applies_when_en='Intra-company transferees'),
             item('d7ab_fdi_reg_copy', anchor='③ 외국인투자기업등록증 사본'),
             item('corp_docs_d8', anchor='④ 사업자등록증 사본, 법인등기사항전부증명서, 주주변동상황명세서 원본', role='business_entity'),
             item('d7ab_investment_funds', anchor=INVEST_ANCHOR),
             item('d7ab_premises_d8', 'CONDITIONAL_REQUIRED', anchor='사업장 존재 입증 서류 (사무실 임대차 계약서', applies_when_ko='투자금액 3억원 미만 개인투자자', applies_when_en='Individual investors of less than KRW 300 million'),
         ] + small_investor() + [proxy()],
         **NOTES)
guidance('D-8-2', 'visa_issuance_confirmation', manual=VISA, section=f'{D8_CVI} — 2. 벤처기업 설립자 및 예비벤처기업 확인을 받은 자 (D-8-2)', anchor='벤처기업 육성에 관한 특별조치법에 따라 벤처기업을 설립한 자 및 예비벤처기업 확인을 받은 자',
         summary_ko='벤처 투자(D-8-2) 사증발급인정서는 신청서·여권 사본·사진, 초청사유서, 사업자등록증·법인등기, 산업재산권 등 기술 보유 입증서류를 냅니다.',
         summary_en='A D-8-2 confirmation needs the form, passport copy and photo, the invitation statement, the business registration and corporate register, and proof of industrial-property or equivalent technology rights.',
         docs=cvi_form(copy=True) + [
             item('d7ab_invitation_reason', anchor='② 초청사유서'),
             item('business_reg_corp_reg', anchor='③ 사업자등록증 사본, 법인등기사항전부증명서', role='business_entity'),
             item('d7ab_industrial_property', anchor='산업재산권, 그 밖에 이에 준하는 기술과 그 사용에 관한 권리 등을 보유하고 있음을 입증하는 서류'), proxy()],
         **NOTES)
guidance('D-8-3', 'visa_issuance_confirmation', manual=VISA, section=f'{D8_CVI} — 3. 국민이 경영하는 개인기업에 투자한 외국인 (D-8-3)', anchor='국민이 경영하는 개인기업에 투자한 외국인 기업투자(D-8-3) 자격',
         summary_ko='개인기업 투자(D-8-3)는 관할 출입국·외국인관서에 신청하며, 투자금액·업종 등을 고려해 체류기간 1년 이하 단수사증이 발급됩니다. 매뉴얼은 사증발급신청서·여권·사진·수수료, 외국인투자기업등록증 사본, 공동사업자인 국민의 사업자금 입증서류, 공동사업자 표시 사업자등록증·공동사업자약정서, 투자자금 도입 입증서류를 적고 있습니다.',
         summary_en='D-8-3 is filed at the immigration office and a single visa of up to 1 year is issued depending on the amount and sector. The manual lists the visa form, passport, photo and fee, the foreign-invested company registration, proof of the Korean partner\'s funds, the business registration showing the co-owners and the agreement, and proof of the investment inflow.',
         docs=visa_form() + [
             item('d7ab_fdi_reg_copy', anchor='② 외국인투자기업등록증 사본'),
             item('d7ab_partner_funds', anchor='③ 공동사업자인 국민의 사업자금(사용 내역) 입증서류'),
             item('d7ab_joint_bizreg', anchor='④ 공동사업자가 표시된 사업자등록증 사본, 공동사업자약정서 원본'),
             item('d7ab_dispatch_employment_period', 'CONDITIONAL_REQUIRED', anchor='주재활동의 경우 파견명령서(파견기간 명시) 및 재직증명서', applies_when_ko='주재활동(파견)인 경우', applies_when_en='Intra-company transferees'),
             item('d7ab_rnd_facility_docs', 'CONDITIONAL_REQUIRED', anchor='산업통상자원부장관이 지정한 ｢연구개발시설｣은 지정서 및 근무인력 명단', applies_when_ko='산업통상자원부장관이 지정한 연구개발시설', applies_when_en='Designated R&D facilities'),
             item('d7ab_investment_funds', anchor=INVEST_ANCHOR),
             item('d7ab_premises_d8', 'CONDITIONAL_REQUIRED', anchor='사업장 존재 입증 서류 (사무실 임대차 계약서', applies_when_ko='투자금액 3억원 미만 신청자', applies_when_en='Applicants investing less than KRW 300 million'),
         ] + small_investor(),
         conditions_ko=['연구개발시설은 출자총액의 100분의 30 이상이어야 하며, 학사학위 소지자로서 3년 이상 연구경력 또는 석사학위 이상 소지한 연구 전담인력이 5명 이상이어야 합니다.', '3억원 미만 소액투자자로서 사업 경험이 없는 사람은 정밀심사합니다.'],
         conditions_en=['For designated R&D facilities the share must be 30%+ and there must be 5+ dedicated researchers (bachelor\'s with 3+ years\' research, or master\'s or higher).', 'Small investors without business experience are closely reviewed.'],
         **NOTES)
guidance('D-8-4', 'visa_issuance_confirmation', manual=VISA, section=f'{D8_CVI} — 4. 기술창업자 (D-8-4)', anchor='4.  국내에서 전문학사 이상의 학위를 취득한 사람 또는 외국에서 학사 이상의 학위를 취득한 사람, 또는 관계 중앙행정기관의 장이 추천한 사람으로서',
         summary_ko='기술창업(D-8-4) 사증발급인정서는 관할 출입국·외국인관서에 신청서·여권·사진, 법인등기사항전부증명서·사업자등록증 사본, 학위증명서 사본 또는 관계 중앙행정기관의 장의 추천서, 점수제 해당 항목 입증서류를 냅니다.',
         summary_en='A D-8-4 confirmation is filed at the immigration office with the form, passport and photo, the corporate register and business registration, a degree certificate copy or a central agency\'s recommendation, and proof of the points items.',
         docs=cvi_form() + [
             item('d7ab_corp_reg_bizreg', anchor='② 법인등기사항전부증명서 및 사업자등록증 사본'),
             item('d7ab_degree_or_rec', anchor='③ 학위증명서 사본 또는 관계 중앙행정기관의 장의 추천서'),
             item('d7ab_d84_points_docs', anchor='④ 점수제 해당 항목( 및 점수) 입증 서류')],
         **NOTES)
guidance('D-8-4S', 'visa_issuance_confirmation', manual=VISA, section=f'{D8_CVI} — 4-1. 스타트업 코리아 특별비자 기술창업자 (D-8-4S)', anchor='일부를 가감할 수 있음 4-1. 스타트업 코리아 특별비자',
         summary_ko='스타트업 코리아 특별비자(D-8-4S) 사증발급인정서는 신청서·여권·사진, 법인등기사항전부증명서·사업자등록증 사본(제출 가능 시), 스타트업 코리아 특별비자 추천서를 냅니다.',
         summary_en='A D-8-4S confirmation needs the form, passport and photo, the corporate register and business registration (if available) and the Startup Korea special-visa recommendation.',
         docs=cvi_form() + [
             item('d7ab_corp_reg_bizreg', 'ADDITIONAL_IF_APPLICABLE', anchor='② 법인등기사항전부증명서 및 사업자등록증 사본 (제출 가능 시)', applies_when_ko='제출 가능 시', applies_when_en='If available'),
             item('d7ab_startup_korea_rec', anchor='③ 스타트업 코리아 특별비자 추천서 (중소벤처기업부 발급)')],
         **NOTES)

# ==========================================================================
# D-9 무역경영
# ==========================================================================
no_grant('D-9', '무역경영(D-9)', anchor='“해당사항 없음”')
not_workplace('D-9', '무역경영(D-9)', '근무처 변경․추가 허가(신고) 대상 아님 : 외국인등록사항 변경신고')
lecture_rule('D-9', '무역경영(D-9)')

guidance('D-9', 'registration', section='무역경영(D-9) 외국인등록', anchor='1. 제출서류 (외국인 개인사업자는 “2”번 참조)',
         summary_ko='무역경영(D-9) 외국인등록은 신청서·여권원본·사진·수수료와 사업자등록증, 임대차계약서 등 주거지 입증서류를 냅니다. 외국인 개인사업자 중 해당자는 국민고용예정서약서를 더합니다.',
         summary_en='D-9 registration needs the form, original passport, photo and fee plus the business registration and proof of residence such as a lease; individual business owners add a pledge to hire Korean nationals where applicable.',
         docs=[item('app_form_34', anchor='① 신청서(별지34호 서식), 여권원본, 표준규격사진1장, 수수료'), item('passport_original', anchor='여권원본, 표준규격사진1장, 수수료'),
               item('photo1', anchor='표준규격사진1장, 수수료'), item('fee', anchor='여권원본, 표준규격사진1장, 수수료'),
               item('d7ab_bizreg_residence', anchor='② 사업자등록증, 임대차계약서 등 주거지 입증서류'),
               item('d7ab_hire_pledge', 'ADDITIONAL_IF_APPLICABLE', anchor='③ 국민고용예정서약서 (해당자만 제출)', applies_when_ko='외국인 개인사업자 중 해당자', applies_when_en='Individual business owners, where applicable')],
         **NOTES)

guidance('D-9-1', 'status_change', section='무역경영(D-9) 체류자격 변경허가 — 1. 무역비자 점수제 요건을 충족하는 자 (D-9-1)', anchor='무역비자 점수제 요건을 충족하는 자에 대한 무역업(D-9-1) 체류자격 변경허가',
         summary_ko='무역비자 점수제 요건(총 160점 중 60점 이상, 필수항목 10점 이상)을 충족하면 무역업(D-9-1)으로 변경할 수 있습니다. 신청서·여권·사진·수수료, 사업자등록증 사본, 무역업 고유번호부여증 사본, 공동사업자는 공동사업 약정서, 사업장 존재 입증서류, 점수제 입증서류를 냅니다.',
         summary_en='Meeting the trade-visa points test (60 of 160 points, 10+ on mandatory items) allows a change to D-9-1. Submit the form, passport, photo and fee, the business registration copy, the trade business number certificate, the co-business agreement for joint owners, proof of premises and the points evidence.',
         docs=[item('app_form_34', anchor='①신청서(별지34호 서식), 여권, 표준규격사진 1장, 수수료  ②사업자등록증 사본 ③무역업'), item('passport', anchor='①신청서(별지34호 서식), 여권, 표준규격사진 1장, 수수료  ②사업자등록증 사본 ③무역업'),
               item('photo1', anchor='표준규격사진 1장, 수수료  ②사업자등록증 사본 ③무역업'), item('fee', anchor='수수료  ②사업자등록증 사본 ③무역업'),
               item('business_reg_copy', anchor='②사업자등록증 사본 ③무역업 고유번호부여증'), item('d7ab_trade_number', anchor='③무역업 고유번호부여증(한국무역협회 발행) 사본'),
               item('d7ab_joint_agreement_partners', 'CONDITIONAL_REQUIRED', anchor='④공동사업 약정서 원본 및 사본(공동사업자인 경우)', applies_when_ko='공동사업자인 경우', applies_when_en='Joint owners'),
               item('d7ab_premises_lease', anchor='⑤사업장 존재 입증서류(임대차계약서 등) ⑥점수제'), item('d7ab_d9_points_stay', anchor='⑥점수제 해당 입증서류 등')],
         period_ko='최초 허가 시 체류기간은 1년만 부여', period_en='Only 1 year is granted the first time',
         conditions_ko=['범칙금 처분을 받은 사람 등 체류허가 제한 통합기준에 해당하는 사람은 결격입니다.'], conditions_en=['People caught by the consolidated stay-restriction criteria (e.g. after fines) are ineligible.'],
         **NOTES)
guidance('D-9', 'status_change', scenario='equipment-ship', section='무역경영(D-9) 체류자격 변경허가 — 2. 수출설비 설치·운영·보수 또는 선박건조·산업설비 제작 파견자', anchor='부득이한 사유로 사증면제(B-1) 또는 단기사증을 소지하고 입국한 외국인 중 아래 해당자에 대한 체류자격 변경허가',
         summary_ko='부득이한 사유로 사증면제(B-1)나 단기사증으로 입국한 사람 중 산업설비(기계) 도입회사에 파견·초청되어 설치·운영·보수 기술을 제공하거나 선박건조·산업설비 제작 과정에 파견된 필수전문인력은 무역경영(D-9)으로 변경할 수 있습니다. 체류자격변경 사유서, 본사 발급 파견명령서 또는 재직증명서, 선박수주계약서 또는 설비도입계약서, 사업자등록증 사본, 납세사실증명을 냅니다.',
         summary_en='People who unavoidably entered visa-free (B-1) or on a short-term visa and who provide installation/operation/maintenance for an equipment-importing company, or are essential staff posted to shipbuilding or plant manufacturing, can change to D-9. Submit a statement of reasons, the head-office dispatch order or employment certificate, the shipbuilding or equipment contract, the business registration copy and tax-payment proof.',
         docs=[item('app_form_34', anchor='①신청서(별지34호 서식), 여권, 표준규격사진 1장, 수수료  ②체류자격변경 사유서'), item('passport', anchor='①신청서(별지34호 서식), 여권, 표준규격사진 1장, 수수료  ②체류자격변경 사유서'),
               item('photo1', anchor='표준규격사진 1장, 수수료  ②체류자격변경 사유서'), item('fee', anchor='수수료  ②체류자격변경 사유서'),
               item('d7ab_status_change_reason', anchor='②체류자격변경 사유서'), item('d7ab_dispatch_or_employment_hq', anchor='③파견명령서 또는 재직증명서(본사 발급)'),
               item('d7ab_ship_or_equipment_contract', anchor='④선박수주계약서 또는 설비도입계약서'), item('business_reg_copy', anchor='⑤사업자등록증 사본 ⑥납세사실증명'),
               item('d7ab_tax_proof_company', anchor='⑥납세사실증명(외국인개인납세내역이 없는 경우 회사 것으로 접수)')],
         **NOTES)
D9_IND_RES_ALTS = [{'ko': '임대차계약서', 'en': 'Lease contract'}, {'ko': '월세 지급 입증서류', 'en': 'Proof of rent payments'}]
guidance('D-9-4', 'status_change', covers=['D-9-5'], section='무역경영(D-9) 체류자격 변경허가 — 3. 외국인 개인사업자 (유학생 무역경영자 포함)', anchor='외국인 개인사업자에 대한 체류자격 변경허가 (2012.10.29. 시행)',
         summary_ko='3억원 이상의 외자를 도입해 사업자등록을 한 외국인 개인사업자(국내 대학 석사 이상 유학·구직 자격자는 1억원 이상 등)는 무역경영(D-9)으로 변경할 수 있습니다. 사업자등록증·영업허가증·투자기업등록증, 공동사업약정서와 공동사업자 소득 입증(해당자), 사업자금 도입 입증서류, 자본금 사용내역, OASIS 이수증(해당자), 영업실적(해당자), 주거지·사업장 입증서류를 냅니다.',
         summary_en='Individual business owners who brought in KRW 300 million+ of foreign capital and registered a business (or D-2/D-10 holders with a Korean master\'s degree investing KRW 100 million+, etc.) can change to D-9. Submit the business registration, licence and investment company registration, the co-business agreement and partner income proof (if any), proof of fund inflow, capital-use proof, OASIS certificate (if any), sales proof (if any) and proof of residence and premises.',
         docs=[item('app_form_34', anchor='① 신청서 (시행규칙 별지 제34호 서식), 여권, 수수료'), item('passport', anchor='① 신청서 (시행규칙 별지 제34호 서식), 여권, 수수료'), item('fee', anchor='① 신청서 (시행규칙 별지 제34호 서식), 여권, 수수료'),
               item('d7ab_d9_bizreg', anchor='② 사업자등록증 사본, 영업허가증 (해당자), 투자기업등록증 (소지자)'),
               item('d7ab_joint_agreement', 'CONDITIONAL_REQUIRED', anchor='③ 공동사업약정서 원본 및 사본 (해당자)', applies_when_ko='해당자', applies_when_en='If applicable'),
               item('d7ab_partner_income', 'CONDITIONAL_REQUIRED', anchor='④ 공동사업자의 연간 소득 입증 서류 (해당자)', applies_when_ko='해당자', applies_when_en='If applicable'),
               item('d7ab_business_funds', anchor='⑤ 사업자금 도입관련 입증서류 (송금확인증, 외국환 매입증명서, 세관신고서, 해당국세관 반출신고서 등)'),
               item('d7ab_capital_use', anchor='⑥ 자본금 사용내역 입증서류 (물품구매 영수증, 사무실 인테리어 비용, 국내은행 계좌 입출금내역서 등)'),
               item('d7ab_oasis_cert', 'ADDITIONAL_IF_APPLICABLE', anchor='⑦ OASIS 교육 이수증(해당자)', applies_when_ko='해당자', applies_when_en='If applicable'),
               item('d7ab_sales_proof', 'CONDITIONAL_REQUIRED', anchor='⑧ 영업실적 입증서류 (수출입면장, 부가세예정 또는 확정 신고서 등)', applies_when_ko='체류자격 변경 전 단기사증(C-3-4) 등을 소지하고 영업행위를 한 경우', applies_when_en='If you did business before the change on a short-term visa such as C-3-4'),
               residence(anchor='⑨ 주거지 입증 서류 (임대차계약서, 월세 지급 입증서류 등)', alts=D9_IND_RES_ALTS),
               item('d7ab_premises_d9', anchor='⑩ 사업장 존재 입증 서류 (임대차계약서, 사업장‧사무공간‧간판사진 등 자료)')],
         conditions_ko=['자격변경 제외 체류자격: D-3, E-9, E-10, G-1, C-3-2, C-3-3, H-1(협정상 자격변경을 허용하지 않는 프랑스·아일랜드·영국 국민만 불허), H-2.',
                        '국내 대학 석사 이상(예정자 포함) 유학(D-2)·구직(D-10) 자격자는 1억원 이상 투자(최대 5,000만원까지 국내 조성 자금 인정, 나머지는 외자) 후 사업자등록을 하면 대상이 되며, 국내 대학 학사(예정자 포함)로 OASIS에서 30점 이상 취득한 경우도 허용됩니다. 유학생 무역경영자(D-9-5)의 국내 형성 자금은 본인 잔고증명 또는 자본금 사용 내역 등으로 합산합니다.',
                        '단기임차(6개월 미만), 주거전용 임차, 온라인 사업장은 원칙적으로 사업장으로 인정하지 않습니다(사업특성상 부득이한 경우 예외).'],
         conditions_en=['Statuses that cannot change: D-3, E-9, E-10, G-1, C-3-2, C-3-3, H-1 (refused only for French, Irish and British nationals whose agreements bar changes), H-2.',
                        'D-2 or D-10 holders with (or about to receive) a Korean master\'s degree qualify after investing KRW 100 million+ (up to KRW 50 million may be raised in Korea, the rest must be foreign capital) and registering a business; Korean bachelor\'s graduates with 30+ OASIS points also qualify. For student traders (D-9-5), funds formed in Korea are counted from your own balance certificate or capital-use records.',
                        'Short leases (under 6 months), residential-only leases and online premises are in principle not accepted (exceptions where unavoidable for the business).'],
         **NOTES)

D9_EXT2 = '① 신청서(별지34호 서식), 여권 및 외국인등록증, 수수료\n   ② 파견명령서 또는 재직증명서(본사 발행)'
guidance('D-9', 'extension', scenario='equipment-ship', section='무역경영(D-9) 체류기간 연장허가 — 2. 선박건조·설비제작 감독 또는 수출설비 설치·운영·보수', anchor='선박건조‧설비제작 감독 또는 수출설비(기계)의 설치‧운영‧보수 업무를 하려는 경우',
         summary_ko='선박건조·설비제작 감독 또는 수출설비 설치·운영·보수 업무자는 본사 발행 파견명령서 또는 재직증명서, 선박수주계약서 또는 설비도입계약서, 사업자등록증 사본, 해당 외국인의 개인 납세사실증명원, 체류지 입증서류로 연장합니다.',
         summary_en='Shipbuilding/plant supervisors and equipment installation, operation or maintenance staff extend with the head-office dispatch order or employment certificate, the shipbuilding or equipment contract, the business registration copy, their personal tax-payment certificate and proof of residence.',
         docs=[item('app_form_34', anchor='① 신청서(별지34호 서식), 여권 및 외국인등록증, 수수료 ② 파견명령서 또는 재직증명서(본사 발행)'), item('passport', anchor='① 신청서(별지34호 서식), 여권 및 외국인등록증, 수수료 ② 파견명령서'),
               item('arc', anchor='여권 및 외국인등록증, 수수료 ② 파견명령서'), item('fee', anchor='수수료 ② 파견명령서 또는 재직증명서(본사 발행)'),
               item('d7ab_dispatch_or_employment_hq', anchor='② 파견명령서 또는 재직증명서(본사 발행)'), item('d7ab_ship_or_equipment_contract', anchor='③ 선박수주계약서 또는 설비도입계약서'),
               item('business_reg_copy', anchor='④ 사업자등록증 사본 ⑤ 개인 납세사실증명원'), item('d7ab_personal_tax_cert', anchor='⑤ 개인 납세사실증명원 (해당외국인)'),
               residence(anchor='⑥ 체류지 입증서류(임대차계약서, 숙소제공 확인서')],
         **NOTES)
guidance('D-9-4', 'extension', covers=['D-9-5'], section='무역경영(D-9) 체류기간 연장허가 — 3. 외국인 개인사업자, 유학생 출신 무역경영자', anchor='3. 외국인 개인사업자, 유학생 출신 무역경영자',
         summary_ko='외국인 개인사업자와 유학생 출신 무역경영자는 사업자등록증·영업허가증·투자기업등록증, 정상적으로 사업을 영위하고 있음을 입증하는 서류(소득금액증명원, 납세증명서 등), 체류지·사업장 입증서류로 연장하며, 해당자는 국민 고용 입증서류를 냅니다.',
         summary_en='Individual business owners and former-student traders extend with the business registration, licence and investment company registration, proof the business operates normally (income certificate, tax clearance, etc.) and proof of residence and premises; where applicable, proof of employing Korean nationals.',
         docs=[item('app_form_34', anchor='① 신청서(별지34호 서식), 여권 및 외국인등록증, 수수료\n ② 사업자등록증 사본, 영업허가증 (해당자)'), item('passport', anchor='① 신청서(별지34호 서식), 여권 및 외국인등록증, 수수료 ② 사업자등록증 사본, 영업허가증'),
               item('arc', anchor='여권 및 외국인등록증, 수수료 ② 사업자등록증 사본, 영업허가증'), item('fee', anchor='수수료 ② 사업자등록증 사본, 영업허가증 (해당자)'),
               item('d7ab_d9_bizreg', anchor='② 사업자등록증 사본, 영업허가증 (해당자), 투자기업등록증 (소지자)'),
               item('d7ab_business_ok_proof', anchor='③ 정상적으로 사업을 영위하고 있음을 입증하는 서류'),
               residence(anchor='④ 체류지 입증서류(임대차계약서, 숙소제공 확인서'),
               item('d7ab_premises_d9', anchor='⑤ 사업장 존재 입증서류(임대차계약서, 사업장 전경․사무공간 간판사진 등 자료)'),
               item('d7ab_korean_employment_proof', 'ADDITIONAL_IF_APPLICABLE', anchor='⑥ 국민 고용 입증서류(원천징수․고용보험 등 6개월 이상 계속 입증서류)', applies_when_ko='해당자만 제출', applies_when_en='Only if applicable')],
         conditions_ko=['납세증명서 등은 발급한 날부터 30일 이내인 것이어야 하며, 납세실적이 저조하거나 없으면 추가 서류를 요구할 수 있습니다.'],
         conditions_en=['Tax certificates must be issued within the last 30 days; additional documents may be requested if tax records are low or absent.'],
         **NOTES)

D9_VISA = '무역경영(D-9) 공관장 재량으로 발급할 수 있는 사증'
guidance('D-9', 'visa_issuance', scenario='equipment', manual=VISA, section=f'{D9_VISA} — 1. 산업설비(기계) 도입회사 파견·초청 기술 제공자', anchor='1. 산업설비(기계) 도입회사에 파견 또는 초청되어 그 장비의 설치',
         summary_ko='산업설비(기계) 도입회사에 파견·초청되어 설치·운영·보수 기술을 제공하는 사람은 체류기간 1년 이하 단수사증을 받으며, 신청서·여권·사진·수수료, 설비도입계약서 또는 산업설비도입 입증서류, 파견명령서, 초청회사의 사업자등록증 사본 또는 법인등기, 연간 납세사실증명서를 냅니다.',
         summary_en='People posted or invited to an equipment-importing company to install, operate or maintain it get a single visa of up to 1 year; submit the form, passport, photo and fee, the equipment contract or import proof, the dispatch order, the inviting company\'s business registration or register and the annual tax certificate.',
         docs=visa_form() + [
             item('d7ab_equipment_contract', anchor='② 설비도입계약서 또는 산업설비도입 입증서류'), item('d7ab_dispatch_order', anchor='③ 파견명령서 ④ 초청회사의'),
             item('d7ab_inviter_bizreg', anchor='④ 초청회사의 사업자등록증 사본 또는 법인등기사항전부증명서'), item('d7ab_annual_tax', anchor='⑤ 연간 납세사실증명서')],
         **NOTES)
guidance('D-9', 'visa_issuance', scenario='ship', manual=VISA, section=f'{D9_VISA} — 2. 선박건조 및 산업설비 제작·감독 파견자', anchor='2. 선박건조 및 산업설비 제작·감독을 위하여 파견되는 자(발주자 또는',
         summary_ko='선박건조·산업설비 제작·감독을 위해 발주자 또는 그 지정 전문용역 회사에서 파견되는 사람은 체류기간 1년 이하 단수사증을 받으며, 신청서·여권 사본·사진·수수료, 수주계약서 사본, 파견명령서, 초청회사의 사업자등록증 사본 또는 법인등기, 연간 납세사실증명서를 냅니다.',
         summary_en='People posted by the ordering company (or its designated service firm) to supervise shipbuilding or plant manufacturing get a single visa of up to 1 year; submit the form, passport copy, photo and fee, the order contract copy, the dispatch order, the inviting company\'s business registration or register and the annual tax certificate.',
         docs=visa_form(copy=True) + [
             item('d7ab_order_contract', anchor='② 수주계약서 사본'), item('d7ab_dispatch_order', anchor='③ 파견명령서 ④ 초청회사의'),
             item('d7ab_inviter_bizreg', anchor='④ 초청회사의 사업자등록증 사본 또는 법인등기사항전부증명서'), item('d7ab_annual_tax', anchor='⑤ 연간 납세사실증명서')],
         **NOTES)
guidance('D-9', 'visa_issuance', scenario='individual-business', manual=VISA, section=f'{D9_VISA} — 4. 외국인 개인사업자', anchor='외국인 개인사업자에 대한 무역경영(D-9) 자격 체류기간 1년 이하의 단수사증 발급',
         summary_ko='3억원 이상 외자를 도입해 사업자등록을 마친 사람 또는 투자기업등록증을 받은 자본금 3억원 이상 개인사업자는 원칙적으로 본국 공관에서 1년 이하 단수사증을 받습니다. 사업자등록증·영업허가증·투자기업등록증, 공동사업약정서(해당자), 사업자금 도입 입증서류, 자본금 사용내역, 영업실적(해당자), 사업장 존재 입증서류, 국민고용예정서약서(해당자)를 냅니다.',
         summary_en='Individual business owners who brought in KRW 300 million+ and registered a business, or hold an investment company registration with KRW 300 million+ capital, normally get a single visa of up to 1 year at the home-country mission. Submit the business registration, licence and investment registration, the co-business agreement (if any), proof of fund inflow, capital-use proof, sales proof (if any), proof of premises and a pledge to hire Koreans (if applicable).',
         docs=visa_form(copy=True) + [
             item('d7ab_d9_bizreg', anchor='② 사업자등록증 사본, 영업허가증 사본 (해당자), 투자기업등록증 (소지자)'),
             item('d7ab_joint_agreement', 'CONDITIONAL_REQUIRED', anchor='③ 공동사업약정서 원본 및 사본 (해당자)', applies_when_ko='해당자 (총 자본금, 지분 및 수익금 분배방법 등 포함)', applies_when_en='If applicable (must state total capital, shares and profit split)'),
             item('d7ab_business_funds', anchor='④ 사업자금 도입관련 입증서류'), item('d7ab_capital_use', anchor='⑤ 자본금 사용내역 입증서류'),
             item('d7ab_sales_proof', 'CONDITIONAL_REQUIRED', anchor='⑥ 영업실적 입증서류', applies_when_ko='사증신청 전 단기사증(C-3-4) 등을 소지하고 영업행위를 한 경우', applies_when_en='If you did business before applying on a short-term visa such as C-3-4'),
             item('d7ab_premises_d9', anchor='⑦ 사업장 존재 입증서류'),
             item('d7ab_hire_pledge', 'ADDITIONAL_IF_APPLICABLE', anchor='⑧ 국민고용예정서약서(해당자만 제출)', applies_when_ko='해당자', applies_when_en='If applicable')],
         **NOTES)

D9_CVI = '무역경영(D-9) 사증발급인정서 발급대상'
guidance('D-9', 'visa_issuance_confirmation', scenario='trade-points', manual=VISA, section=f'{D9_CVI} — 1. 무역비자 점수제 해당자', anchor='무역비자 점수제의 총160점 중 60점 이상 득점자로서, 필수항목 점수가 10점 이상인 자',
         summary_ko='무역비자 점수제(총 160점 중 60점 이상, 필수항목 10점 이상) 해당자는 본인 명의 사업자등록을 마치고 최근 3년 이내 출입국관리법 위반이 없어야 합니다. 공통제출 서류, 사업자등록증 사본, 무역업 고유번호부여증 사본, 공동사업약정서(공동사업자), 사업장 존재 입증서류, 점수제 입증서류를 냅니다.',
         summary_en='Trade-visa points applicants (60 of 160, 10+ on mandatory items) must have registered a business in their own name and have no immigration violation in the last 3 years. Submit the common documents, the business registration copy, the trade business number certificate, the co-business agreement (joint owners), proof of premises and the points evidence.',
         docs=[item('d7ab_cvi_common', anchor='사증발급인정신청서, 여권사본 등 공통제출 서류'), item('business_reg_copy', anchor='◦ 사업자등록증 사본 ◦ 무역업 고유번호부여증'),
               item('d7ab_trade_number', anchor='무역업 고유번호부여증(한국무역협회 발행) 사본'),
               item('d7ab_joint_agreement_partners', 'CONDITIONAL_REQUIRED', anchor='공동사업약정서 원본 및 사본 (공동 사업자인 경우)', applies_when_ko='공동 사업자인 경우', applies_when_en='Joint owners'),
               item('d7ab_premises_lease', anchor='사업장 존재 입증서류(임대차계약서 등)'), item('d7ab_d9_points_cvi', anchor='◦ 점수제 해당 점수 입증서류')],
         **NOTES)
for scen, title, anc, contract in (('equipment', '2. 산업설비(기계) 도입회사 파견·초청 기술 제공자', '③ 설비도입계약서 또는 산업설비도입 입증서류 ④ 파견명령서', ('d7ab_equipment_contract', '③ 설비도입계약서 또는 산업설비도입 입증서류')),
                                   ('ship', '3. 선박건조 및 산업설비 제작·감독 파견자', '③ 수주계약서 사본', ('d7ab_order_contract', '③ 수주계약서 사본'))):
    guidance('D-9', 'visa_issuance_confirmation', scenario=scen, manual=VISA, section=f'{D9_CVI} — {title}', anchor=anc,
             summary_ko=('산업설비(기계) 도입회사에 파견·초청되는 기술 제공자' if scen == 'equipment' else '선박건조·산업설비 제작·감독 파견자') + '의 사증발급인정서는 신청서·여권 사본·사진, 초청사유서, ' + ('설비도입계약서 또는 산업설비도입 입증서류' if scen == 'equipment' else '수주계약서 사본') + ', 파견명령서, 초청회사의 사업자등록증 사본 또는 법인등기, 연간 납세사실증명서를 냅니다.',
             summary_en='The confirmation for ' + ('equipment installation/maintenance staff' if scen == 'equipment' else 'shipbuilding/plant supervisors') + ' needs the form, passport copy and photo, the invitation statement, ' + ('the equipment contract or import proof' if scen == 'equipment' else 'the order contract copy') + ', the dispatch order, the inviting company\'s business registration or register and the annual tax certificate.',
             docs=cvi_form(copy=True) + [item('d7ab_invitation_reason', anchor='② 초청사유서'), item(contract[0], anchor=contract[1]), item('d7ab_dispatch_order', anchor='④ 파견명령서 ⑤ 초청회사의'),
                                         item('d7ab_inviter_bizreg', anchor='⑤ 초청회사의 사업자등록증 사본 또는 법인등기사항전부증명서'), item('d7ab_annual_tax', anchor='⑥ 연간 납세사실증명서'), proxy()],
             **NOTES)

# ==========================================================================
# D-10 구직
# ==========================================================================
no_grant('D-10', '구직(D-10)')
guidance('D-10', 'workplace_change', state='NOT_APPLICABLE', completeness='SOURCE_ONLY', section='구직(D-10) 근무처의 변경․추가', anchor='해당사항 없음',
         summary_ko='구직(D-10)의 근무처 변경·추가는 "해당사항 없음"입니다.', summary_en='Workplace change/addition is "not applicable" for D-10.')

D10_COMMON_A = '공통서류(신청서, 사진, 여권사본, 수수료, 신분증사본)'
D10_COMMON_B = '공통서류(신청서, 사진, 여권 사본, 수수료, 신분증 사본)'


def d10_common(a=D10_COMMON_B):
    return [item('d7ab_app_form', anchor=a), item('photo', anchor=a), item('passport_copy', anchor=a), item('fee', anchor=a), item('arc_copy', anchor=a)]


def d10_common_t():
    a = '공통서류(신청서, 표준규격 사진, 여권 사본, 수수료)'
    return [item('d7ab_app_form', anchor=a), item('photo', anchor=a), item('passport_copy', anchor=a), item('fee', anchor=a)]


STAY_COST = '연도별 1인 가구 주거급여 기준액 × 체류개월 수'
NO_COST_KO, NO_COST_EN = '체재비 입증서류 제출은 면제됩니다.', 'No proof of living funds is required.'


def d10_points_docs(manual):
    rec = item('d7ab_recommendation_visa', 'ADDITIONAL_IF_APPLICABLE', anchor='❍ 추천서(해당자)', applies_when_ko='해당자', applies_when_en='If applicable') if manual == VISA else \
        item('d7ab_recommendation_stay', 'ADDITIONAL_IF_APPLICABLE', anchor='❍ 고용추천서(해당자)', applies_when_ko='해당자', applies_when_en='If applicable')
    w = dict(applies_when_ko='해당자', applies_when_en='If applicable')
    return [item('job_plan', anchor='❍ 구직활동 계획서'),
            item('d7ab_degree_d10', anchor='❍ 학위증(졸업증명서, 학위취득증명서도 인정)', notes_ko='출입국관리정보시스템(유학생정보시스템)으로 확인되는 경우 제출 면제', notes_en='Not needed if it can be checked in the immigration (student) information system'),
            item('d7ab_univ_rank_proof', 'CONDITIONAL_REQUIRED', anchor='❍ 대학 순위 소명자료(세계 대학순위 적용 대상자)', applies_when_ko='세계 대학순위 적용 대상자', applies_when_en='If the world-ranking criterion applies'),
            item('d7ab_career_proof', 'ADDITIONAL_IF_APPLICABLE', anchor='❍ 근무경력 증빙서류(해당자)', **w),
            item('d7ab_training_proof', 'ADDITIONAL_IF_APPLICABLE', anchor='❍ 국내 연수 활동 증빙서류(해당자)', **w),
            item('d7ab_korean_proof', 'ADDITIONAL_IF_APPLICABLE', anchor='❍ 한국어능력 입증서류(해당자)', **w), rec,
            item('d7ab_high_income_proof', 'ADDITIONAL_IF_APPLICABLE', anchor='❍ 고소득 전문가 입증서류(해당자)', **w),
            item('stay_cost_proof_d10', anchor=STAY_COST),
            item('points_docs', 'ADDITIONAL_IF_APPLICABLE', anchor='❍ 기타 점수제 평가에 필요하다고 인정되는 서류', applies_when_ko='점수제 평가에 필요한 경우', applies_when_en='If needed for the points assessment')]


D10_BLOCK_KO = '공통 제한대상: 신청일로부터 5년 이내 금고 이상의 형 또는 강제퇴거·출국명령, 3년 이내 300만원 이상 벌금형, 체류허가 제한 통합기준에 해당하는 범칙금(초범 500만원 이상, 재범 3년 내 합산 700만원 이상)을 받은 사람.'
D10_BLOCK_EN = 'Common bars: within 5 years a prison sentence or deportation/departure order, within 3 years a fine of KRW 3 million+, or immigration fines meeting the restriction criteria (first KRW 5 million+, or KRW 7 million+ combined within 3 years).'
D10_VISA = '구직(D-10) 공관장 재량으로 발급할 수 있는 사증'
D10_VISA_COND_KO = ['해외에서 발급한 서류는 반드시 한글 또는 영어로 번역 후 아포스티유 인증 또는 자국정부(OECD 지재권 입증 서류는 발행국)의 공증을 거쳐 재외공관에 제출합니다.',
                    '자국 또는 거주 중인 국가(출생·취업 등으로 장기 체류 중인 국가)에 소재한 한국공관에 신청합니다.', D10_BLOCK_KO]
D10_VISA_COND_EN = ['Documents issued abroad must be translated into Korean or English and apostilled or notarised by your government (for OECD IP proof, by the issuing country).',
                    'Apply at the Korean mission in your country or your country of long-term residence.', D10_BLOCK_EN]
D10_VISA_PERIOD = dict(period_ko='체류기간 6개월 단수사증 (구직사증 복수사증발급협정 체결국 국민은 유효기간 2년, 체류기간 6월의 복수사증)', period_en='Single visa for 6 months (nationals of countries with a job-seeker multiple-visa agreement: multiple visa valid 2 years, 6-month stays)')

guidance('D-10-1', 'visa_issuance', manual=VISA, section=f'{D10_VISA} — 1-1) 일반구직(D-10-1) : 점수제 적용 대상자', anchor='1-1) 일반구직(D-10-1) : 점수제 적용 대상자',
         summary_ko='점수제 적용 일반구직(D-10-1) 사증은 구직 점수표 총 190점 중 기본항목 20점 이상, 총 60점 이상이어야 합니다. 공통서류와 구직활동 계획서, 학위증, 체재비 입증서류를 내고 해당자는 대학 순위 소명자료, 경력·연수·한국어능력·추천서·고소득 입증서류를 더합니다.',
         summary_en='A points-based D-10-1 visa needs 60+ of 190 points with 20+ on the basic items. Submit the common documents, a job-seeking plan, the degree certificate and proof of living funds, plus ranking, career, training, Korean-ability, recommendation or high-income proof where applicable.',
         docs=d10_common() + d10_points_docs(VISA), conditions_ko=D10_VISA_COND_KO, conditions_en=D10_VISA_COND_EN, **D10_VISA_PERIOD, **NOTES)
for scen, title, anc, extra, sko, sen in (
        ('first-change', 'ⅰ) 국내 대학 졸업 후 최초 구직자격 변경', '국내 대학 졸업 후 최초 구직자격 변경자로 사증발급은 졸업일로부터 1년 이내만 인정',
         [item('job_plan', anchor='❍ 구직활동 계획서'), item('d7ab_kr_degree', anchor='❍ 국내 정규 대학* 전문학사 이상 학위증(또는 졸업증명서)')],
         '국내 대학 졸업 후 최초 구직자격 변경자(점수제 면제)는 졸업일로부터 1년 이내에만 사증을 받을 수 있으며, 공통서류, 구직활동 계획서, 국내 정규 대학 전문학사 이상 학위증을 냅니다.',
         'First-time job seekers after graduating from a Korean university (points-exempt) can get the visa only within 1 year of graduation; submit the common documents, a job-seeking plan and the Korean associate-or-higher degree.'),
        ('korean-graduate', 'ⅱ) 국내 대학 졸업 한국어능력 우수자', '국내 대학 졸업 한국어능력 우수자(토픽 4급 상당 이상)',
         [item('job_plan', anchor='❍ 구직활동 계획서'), item('d7ab_kr_degree', anchor='❍ 국내 정규 대학* 전문학사 이상 학위증(또는 졸업증명서)'),
          item('d7ab_korean_proof_level4', anchor='사회통합프로그램 중간평가 합격증 또는 사전평가 점수표(81점 이상), 한국어능력시험(TOPIK) 4급 이상 유효 성적표')],
         '국내 대학 졸업 한국어능력 우수자(점수제 면제)는 졸업일(학위수여일)로부터 3년 이내인 경우에만 특례가 적용되며, 공통서류, 구직활동 계획서, 국내 정규 대학 학위증, 한국어능력 입증서류를 냅니다.',
         'Korean-university graduates with strong Korean (points-exempt) qualify only within 3 years of graduation; submit the common documents, a job-seeking plan, the Korean degree and Korean-ability proof.'),
        ('promising-talent', 'ⅲ) 유망인재', '29세 이하 해외 대학 졸업자로서 ❶THE 또는 QS 세계 대학순위 200위 이내 대학 졸업',
         [item('job_plan', anchor='❍ 구직활동 계획서'), item('d7ab_degree_d10', anchor='❍ 학위증(졸업증명서, 학위취득증명서도 인정)'),
          item('d7ab_rank200_proof', 'ADDITIONAL_IF_APPLICABLE', anchor='최근 3년 이내 THE 또는 QS 세계 대학순위 200위 이내 대학 소명자료(해당자)', applies_when_ko='해당자', applies_when_en='If applicable'),
          item('d7ab_topik6', 'ADDITIONAL_IF_APPLICABLE', anchor='한국어능력시험(TOPIK) 6급 유효 성적표(해당자)', applies_when_ko='해당자', applies_when_en='If applicable')],
         '유망인재(29세 이하 해외 대학 졸업자로 THE·QS 200위 이내 대학 졸업 또는 한국학 전공 TOPIK 6급)는 공통서류, 구직활동 계획서, 학위증과 해당자별 대학순위 소명자료 또는 TOPIK 6급 성적표를 냅니다.',
         'Promising talent (overseas graduates aged 29 or under from a THE/QS top-200 university, or Korean-studies majors with TOPIK 6) submit the common documents, a job-seeking plan, the degree and the ranking evidence or TOPIK 6 result as applicable.'),
        ('embassy-intern', 'ⅳ) 주한 공관 근무 인턴 직원', 'ⅳ) 주한 공관 근무 인턴 직원',
         [item('d7ab_intern_contract', anchor='❍ 인턴계약서'), item('d7ab_ambassador_rec', anchor='❍ 양국 공관 대사 추천서')],
         '주한 외국공관에서 근무하려는 인턴 직원은 공통서류, 인턴계약서, 양국 공관 대사 추천서를 냅니다.',
         'Interns who will work at a foreign mission in Korea submit the common documents, the internship contract and recommendations from both countries\' ambassadors.')):
    guidance('D-10-1', 'visa_issuance', scenario=scen, manual=VISA, section=f'{D10_VISA} — 1-2) 일반구직(D-10-1) 점수제 면제 대상자 {title}', anchor=anc,
             summary_ko=sko, summary_en=sen, docs=d10_common() + extra, conditions_ko=[NO_COST_KO] + D10_VISA_COND_KO, conditions_en=[NO_COST_EN] + D10_VISA_COND_EN, **D10_VISA_PERIOD, **NOTES)
D10_STARTUP = [item('d7ab_degree_bachelor', anchor='❍ 학사(국내 전문학사) 학위 이상 학력증명서'), item('d7ab_startup_plan', anchor='❍ 기술창업계획서'),
               item('d7ab_ip_or_filing', 'ADDITIONAL_IF_APPLICABLE', anchor='특허증·실용신안등록증·디자인등록증 사본 또는 특허 등 출원사실증명서(해당자)', applies_when_ko='해당자', applies_when_en='If applicable'),
               item('d7ab_oasis_proof', 'ADDITIONAL_IF_APPLICABLE', anchor='창업이민종합지원시스템 교육과정 이수증 또는 교육참여 확인서(해당자)', applies_when_ko='해당자', applies_when_en='If applicable'),
               item('d7ab_oecd_ip', 'ADDITIONAL_IF_APPLICABLE', anchor='OECD 국가 지식재산권 보유 사실을 확인할 수 있는 공적 서류(해당자)', applies_when_ko='해당자', applies_when_en='If applicable'),
               item('stay_cost_proof_d10', anchor=STAY_COST)]
D10_STARTUP_KO = '기술창업준비(D-10-2)는 학사(국내 전문학사) 이상 학위를 가진 사람으로 국내 특허권 등 보유·출원, OASIS 참여·이수(최근 3년 이내), K-Startup 그랜드챌린지 추천, 해외(OECD) 지식재산권 보유 중 하나에 해당해야 합니다. 공통서류, 학력증명서, 기술창업계획서, 체재비 입증서류를 내고 해당자는 특허 등 증명, OASIS 이수증, OECD 지식재산권 서류를 더합니다.'
D10_STARTUP_EN = 'D-10-2 needs a bachelor\'s degree (Korean associate degree) and one of: a Korean patent/utility/design right held or filed, OASIS participation or completion in the last 3 years, a K-Startup Grand Challenge recommendation, or OECD-country IP. Submit the common documents, proof of education, a start-up plan and proof of living funds, plus patent, OASIS or OECD IP proof as applicable.'
guidance('D-10-2', 'visa_issuance', manual=VISA, section=f'{D10_VISA} — 2) 기술창업준비(D-10-2)', anchor='2) 기술창업준비(D-10-2)\n   ❍ 공통서류(신청서, 사진, 여권사본, 수수료, 신분증사본)',
         summary_ko=D10_STARTUP_KO, summary_en=D10_STARTUP_EN, docs=d10_common(D10_COMMON_A) + D10_STARTUP,
         conditions_ko=D10_VISA_COND_KO, conditions_en=D10_VISA_COND_EN, **D10_VISA_PERIOD, **NOTES)
guidance('D-10-T', 'visa_issuance', manual=VISA, section=f'{D10_VISA} — 3) 최우수인재(D-10-T)', anchor='3) 최우수인재(D-10-T)',
         summary_ko='최우수인재 구직(D-10-T)은 최근 5년 이내 세계 대학 순위 100위 이내 대학의 석사 이상 학위를 취득한 사람이 대상이며(부처추천 불요), 공통서류(신청서, 표준규격 사진, 여권 사본, 수수료), 구직활동 계획서, 해외 우수대학(본교) 졸업(예정)증명서를 냅니다.',
         summary_en='D-10-T is for people with a master\'s or higher from a world top-100 university obtained in the last 5 years (no ministry recommendation needed); submit the common documents (form, photo, passport copy, fee), a job-seeking plan and the graduation (or expected graduation) certificate from that university (main campus).',
         docs=d10_common_t() + [item('job_plan', anchor='❍ 구직활동 계획서'), item('d7ab_top_univ_grad', anchor='해외 우수대학(본교) 졸업(예정)증명서')],
         conditions_ko=D10_VISA_COND_KO, conditions_en=D10_VISA_COND_EN, **D10_VISA_PERIOD, **NOTES)

D10_INTERN = [item('d7ab_intern_plan', anchor='❍ 인턴활동 계획서'),
              item('d7ab_intern_univ_proof', anchor='최근 3년 이내 세계 대학순위 THE 200위, QS 500위 이내 소명자료'),
              item('d7ab_intern_labor_contract', anchor='❍ 인턴근로계약서'),
              item('d7ab_intern_company_docs', anchor='법인등기부등본, 고용보험가입자 명부, 연구시설 현황자료'),
              item('d7ab_intern_company_eligibility', anchor='첨단기술인턴 초청이 가능한 기업(기관)임을 입증할 수 있는 서류(택1)'),
              item('stay_cost_proof_d10', anchor=STAY_COST, does_not_apply_when_ko='인턴계약서에 인턴기간 동안 같은 수준의 국내 체재비 지급 내용이 확인되는 경우', does_not_apply_when_en='If the internship contract shows living support at that level for the internship period')]
D10_INTERN_COND_KO = ['휴학증명서도 인정하되 휴학일로부터 1년이 지나면 인정하지 않으며, 학력증명서는 유학(D-2) 지침의 국가별 공증절차대로 공적 확인을 받은 경우에만 인정합니다.']
D10_INTERN_COND_EN = ['A leave-of-absence certificate is accepted unless the leave began over a year ago; education documents count only if legalised under the D-2 country-specific procedure.']
guidance('D-10-3', 'visa_issuance_confirmation', manual=VISA, section='구직(D-10) 사증발급인정서 발급대상 — 첨단기술인턴(D-10-3)', anchor='첨단기술인턴(D-10-3)에 대해서는 사증발급인정서를 통한 사증발급만 허용하며',
         summary_ko='첨단기술인턴(D-10-3)은 사증발급인정서를 통한 사증발급만 허용되며 최대 1년(계약서상 인턴기간 이내)이 부여될 수 있습니다. 공통서류, 인턴활동 계획서, 대학순위 소명자료와 재학·졸업증명서, 인턴근로계약서, 초청 기업 서류와 초청 가능 기업 입증서류, 체재비 입증서류를 냅니다.',
         summary_en='High-tech interns (D-10-3) get the visa only through a confirmation of visa issuance, for up to 1 year (not beyond the contract). Submit the common documents, an internship plan, the university-ranking evidence and enrollment/graduation certificate, the internship contract, the inviting company\'s documents and proof it may invite interns, and proof of living funds.',
         period_ko='최대 1년 (계약서에 명시된 인턴기간 초과 불가)', period_en='Up to 1 year (not beyond the internship period in the contract)',
         docs=d10_common(D10_COMMON_A) + D10_INTERN, conditions_ko=D10_INTERN_COND_KO + [D10_BLOCK_KO], conditions_en=D10_INTERN_COND_EN + [D10_BLOCK_EN], **NOTES)

D10_CHANGE = '구직(D-10) 체류자격 변경허가 — 다. 제출서류'
guidance('D-10-1', 'status_change', section=f'{D10_CHANGE} 1-1) 일반구직(D-10-1) : 점수제 적용', anchor='1-1) 일반구직(D-10-1) : 점수제 적용',
         summary_ko='점수제 적용 일반구직(D-10-1)은 학사(국내 전문학사 포함) 이상 국내 합법 체류자로 구직 점수표 총 190점 중 기본항목 20점 이상, 총 60점 이상이어야 합니다. 공통서류, 구직활동 계획서, 학위증, 체재비 입증서류를 내고 해당자는 대학 순위·경력·연수·한국어능력·고용추천서·고소득 입증서류를 더합니다.',
         summary_en='Points-based D-10-1 is for lawful residents with a bachelor\'s (incl. Korean associate) degree scoring 60+ of 190 with 20+ on basic items. Submit the common documents, a job-seeking plan, the degree and proof of living funds, plus ranking, career, training, Korean-ability, recommendation or high-income proof where applicable.',
         docs=d10_common(D10_COMMON_A) + d10_points_docs(STAY),
         conditions_ko=['법무부장관 고시국가 국민 중 B-1, B-2, C-1, C-3, C-4, D-3, E-9, E-10, G-1 자격자는 총 80점 이상이어야 변경이 허용됩니다.',
                        '이전 근무처와의 근로계약 기간이 남아 새로운 근로계약 체결이 제한되는 사람은 제한되며, 고용주의 이적동의서가 있으면 예외로 인정됩니다.', D10_BLOCK_KO],
         conditions_en=['Nationals of countries designated by the Minister holding B-1, B-2, C-1, C-3, C-4, D-3, E-9, E-10 or G-1 need 80+ points.',
                        'Anyone still bound by a previous employment contract is barred unless the employer gives a release consent.', D10_BLOCK_EN],
         **NOTES)
D10_EXEMPT = [
    ('first-change', 'ⅰ) 유학생 졸업 후 최초 구직변경', 'ⅰ) 유학생 졸업 후 최초 구직변경',
     [item('job_plan', anchor='❍ 구직활동 계획서'), item('d7ab_kr_degree', anchor='❍ 국내 정규 대학* 전문학사 이상 학위증(또는 졸업증명서)'), residence(anchor='❍ 체류지 입증서류')],
     '국내 대학에서 전문학사 이상 학위과정 유학생(D-2)으로 졸업한 뒤 최초로 구직(D-10-1)으로 변경하면 점수제가 적용되지 않으며, 공통서류, 구직활동 계획서, 국내 정규 대학 학위증, 체류지 입증서류를 냅니다. 최초 1년이 부여되고 연장 시에는 점수제가 적용됩니다.',
     'Graduates of a Korean associate-or-higher programme (D-2) changing to D-10-1 for the first time are points-exempt; submit the common documents, a job-seeking plan, the Korean degree and proof of residence. One year is granted first; extensions use the points system.', [NO_COST_KO], [NO_COST_EN]),
    ('korean-graduate', 'ⅱ) 국내 대학 출신 한국어 성적 우수자', 'ⅱ) 국내 대학 출신 한국어 성적 우수자',
     [item('job_plan', anchor='❍ 구직활동 계획서'), item('d7ab_kr_degree', anchor='❍ 국내 정규 대학* 전문학사 이상 학위증(또는 졸업증명서)'),
      item('d7ab_korean_proof_level4', anchor='사회통합프로그램 중간평가 합격증 또는 사전평가 점수표(81점 이상), 한국어능력시험(TOPIK) 4급 이상 유효 성적표'), residence(anchor='❍ 체류지 입증서류')],
     '국내 정규 대학 전문학사 이상 학위 취득 후 3년이 지나지 않은 한국어능력 우수자(사회통합프로그램 4단계 중간평가 합격 또는 TOPIK 4급 이상)는 점수제 면제로, 공통서류, 구직활동 계획서, 학위증, 한국어능력 입증서류, 체류지 입증서류를 냅니다.',
     'Korean-university graduates within 3 years of graduation with strong Korean (KIIP level-4 mid-term pass or TOPIK 4+) are points-exempt; submit the common documents, a job-seeking plan, the degree, Korean-ability proof and proof of residence.', [NO_COST_KO], [NO_COST_EN]),
    ('domestic-youth', 'ⅲ) 국내 성장 기반 외국인 청소년', 'ⅲ) 국내 성장 기반 외국인 청소년',
     [item('job_plan', anchor='❍ 구직활동 계획서'), residence(anchor='❍ 체류지* 입증서류', notes_ko='근무처가 아닌 실제 거주지 입증서류 제출이 원칙입니다.', notes_en='Proof of your actual home, not the workplace, is required.'),
      item('d7ab_school_grad', anchor='국내 초·중·고교 졸업증명서 또는 동등한 학력 소지 입증 서류'), item('d7ab_youth_checklist', anchor='국내 성장 기반 외국인 청소년 자격변경 체크리스트(붙임7)'),
      item('d7ab_kiip_cert', 'ADDITIONAL_IF_APPLICABLE', anchor='❍ 사회통합프로그램 이수증(해당자)', applies_when_ko='해당자', applies_when_en='If applicable'),
      item('d7ab_abroad_reason', 'ADDITIONAL_IF_APPLICABLE', anchor='중도 해외 장기 체류 사유서 및 소명자료(해당자, 붙임8)', applies_when_ko='해당자', applies_when_en='If applicable'),
      item('overseas_criminal_record', 'CONDITIONAL_REQUIRED', anchor='❍ 해외범죄경력증명서(면제자* 제외)', applies_when_ko='면제자 제외', applies_when_en='Unless exempt',
           does_not_apply_when_ko='대한민국 출생 또는 14세 미만에 입국하여 14세 이후 해외에서 6개월 이상 연속 체류하지 않은 사람, 과거 해외범죄경력증명서를 내고 국내 체류 중이며 해외에서 6개월 이상 연속 체류하지 않은 사람',
           does_not_apply_when_en='Born in Korea or entered before 14 without a 6-month continuous stay abroad after 14; or already submitted one and have not stayed abroad 6 months continuously since')],
     '18세 이상 24세 이하의 합법체류자로 국내 초·중·고교를 모두 졸업했거나 동등한 학력을 갖춘 사람은 점수제 면제로, 공통서류, 구직활동 계획서, 체류지 입증서류, 졸업증명서, 자격변경 체크리스트, 해외범죄경력증명서(면제자 제외)를 내고 해당자는 사회통합프로그램 이수증, 해외 장기 체류 사유서를 더합니다.',
     'Lawful residents aged 18-24 who completed Korean primary, middle and high school (or equivalent) are points-exempt; submit the common documents, a job-seeking plan, proof of residence, graduation certificates, the checklist and an overseas criminal record (unless exempt), plus a KIIP certificate or an explanation of long stays abroad where applicable.', [NO_COST_KO], [NO_COST_EN]),
    ('promising-talent', 'ⅳ) 유망인재', 'ⅳ) 유망인재',
     [item('job_plan', anchor='❍ 구직활동 계획서'), item('d7ab_degree_d10', anchor='❍ 학위증(졸업증명서, 학위취득증명서도 인정)'),
      item('d7ab_rank200_proof', 'ADDITIONAL_IF_APPLICABLE', anchor='최근 3년 이내 THE 또는 QS 세계 대학순위 200위 이내 대학 소명자료(해당자)', applies_when_ko='해당자', applies_when_en='If applicable'),
      item('d7ab_topik6', 'ADDITIONAL_IF_APPLICABLE', anchor='한국어능력시험(TOPIK) 6급 유효한 성적표(해당자)', applies_when_ko='해당자', applies_when_en='If applicable'), residence(anchor='❍ 체류지 입증서류')],
     '유망인재(29세 이하 해외 대학 졸업자로 최근 3년 이내 THE·QS 200위 이내 대학 학사 이상 또는 한국학 전공 TOPIK 6급)는 공통서류, 구직활동 계획서, 학위증, 해당자별 대학순위 소명자료 또는 TOPIK 6급 성적표, 체류지 입증서류를 냅니다.',
     'Promising talent (overseas graduates aged 29 or under from a THE/QS top-200 university in the last 3 years, or Korean-studies majors with TOPIK 6) submit the common documents, a job-seeking plan, the degree, the ranking evidence or TOPIK 6 result as applicable and proof of residence.', [NO_COST_KO], [NO_COST_EN]),
    ('caregiver-trainee', 'ⅴ) 요양보호사 전문연수 과정 수료자', 'ⅴ) 요양보호사 전문연수 과정 수료자',
     [item('d7ab_intern_contract', anchor='❍ 인턴계약서'), item('d7ab_korean_proof_level3', anchor='사회통합프로그램 3단계 이수증(사전평가 61점 이상 성적증명서 포함) 또는 한국어능력시험(TOPIK) 3급 이상 유효 성적표'),
      item('d7ab_caregiver_cert', anchor='한국보건복지인재원 발급 요양보호사 교육수료증명서'), residence(anchor='❍ 체류지 입증서류')],
     '한국보건복지인재원 주관 요양보호사 전문연수 과정을 수료하고 노인의료복지시설에서 인턴 근로계약을 체결하려는 사람은 공통서류, 인턴계약서, 한국어능력 입증서류(사회통합프로그램 3단계 또는 TOPIK 3급 이상), 요양보호사 교육수료증명서, 체류지 입증서류를 냅니다.',
     'Graduates of the care-worker training course who will sign an internship contract with an elderly-care facility submit the common documents, the internship contract, Korean-ability proof (KIIP level 3 or TOPIK 3+), the training completion certificate and proof of residence.', [NO_COST_KO], [NO_COST_EN]),
    ('professional-experience', 'ⅵ) 전문직종(E-1~E-7) 근무 경력자', 'ⅵ) 전문직종(E-1~E-7) 근무 경력자',
     [item('job_plan', anchor='❍ 구직활동 계획서'), item('d7ab_new_contract_possible', 'CONDITIONAL_REQUIRED', anchor='국내에서 출국하지 않고 새로운 근로계약 체결이 가능함을 입증하는 서류',
                                                                 applies_when_ko='이전 근무처에서 잔여 근로계약 기간이 1개월 이상 있는 경우 (이적동의서)', applies_when_en='If over a month remains on the previous contract (release consent)'),
      residence(anchor='❍ 체류지 입증서류'),
      item('stay_cost_proof_d10', anchor=STAY_COST,
           does_not_apply_when_ko='전문직종(E-1~E-7) 자격에서 구직(D-10) 자격으로 최초 자격변경하는 사람', does_not_apply_when_en='Your first change from E-1~E-7 to D-10')],
     '교수(E-1)~특정활동(E-7, E-6-2 제외) 자격으로 근로계약이 끝나거나 정당한 사유로 취업이 종료되었으나 체류기간 만료 전에 새 근무처를 구하지 못한 사람은 공통서류, 구직활동 계획서, 새 근로계약 체결 가능 입증서류(이적동의서), 체류지 입증서류, 체재비 입증서류를 냅니다. E-1~E-7에서 최초로 변경하면 체재비 입증은 면제됩니다.',
     'E-1~E-7 holders (not E-6-2) whose contract ended or who stopped working for a valid reason and found no new job before expiry submit the common documents, a job-seeking plan, proof they may sign a new contract (release consent), proof of residence and proof of living funds; the living-funds proof is waived for a first change from E-1~E-7.', [], []),
    ('embassy-intern', 'ⅶ) 주한 공관 근무 인턴 직원', 'ⅶ) 주한 공관 근무 인턴 직원',
     [item('d7ab_intern_contract', anchor='❍ 인턴계약서'), item('d7ab_ambassador_rec', anchor='❍ 양국 공관 대사 추천서'), residence(anchor='❍ 체류지 입증서류')],
     '주한 외국공관에서 근무하려는 인턴 직원은 공통서류, 인턴계약서, 양국 공관 대사 추천서, 체류지 입증서류를 냅니다.',
     'Interns who will work at a foreign mission in Korea submit the common documents, the internship contract, the ambassadors\' recommendations and proof of residence.', [NO_COST_KO], [NO_COST_EN]),
]
for scen, title, anc, extra, sko, sen, cko, cen in D10_EXEMPT:
    guidance('D-10-1', 'status_change', scenario=scen, section=f'{D10_CHANGE} 1-2) 일반구직(D-10-1) 점수제 면제 특례자 — {title}', anchor=anc,
             summary_ko=sko, summary_en=sen, docs=d10_common() + extra, conditions_ko=cko + [D10_BLOCK_KO], conditions_en=cen + [D10_BLOCK_EN], **NOTES)
guidance('D-10-2', 'status_change', section=f'{D10_CHANGE} 2) 기술창업준비(D-10-2)', anchor='2) 기술창업준비(D-10-2)\n    ❍ 공통서류(신청서, 사진, 여권사본, 수수료, 신분증사본)',
         summary_ko=D10_STARTUP_KO, summary_en=D10_STARTUP_EN, docs=d10_common(D10_COMMON_A) + D10_STARTUP,
         conditions_ko=['OASIS 교육 이수일로부터 3년이 지난 뒤 신청하는 사람은 제한됩니다(교육 재이수 중인 사람 제외).', D10_BLOCK_KO],
         conditions_en=['Applications more than 3 years after completing OASIS are barred (unless retaking it).', D10_BLOCK_EN], **NOTES)
guidance('D-10-3', 'status_change', section=f'{D10_CHANGE} 3) 첨단기술인턴(D-10-3)', anchor='3) 첨단기술인턴(D-10-3)\n    ❍ 공통서류(신청서, 사진, 여권사본, 수수료, 신분증사본)',
         summary_ko='첨단기술인턴(D-10-3)은 세계 우수 대학 첨단기술 분야 재학생 또는 졸업 3년 이내 졸업생(만 30세 미만, 석사 이상 만 35세 미만)이 요건을 갖춘 기업(기관)과 인턴계약을 맺은 경우입니다. 공통서류, 인턴활동 계획서, 대학순위 소명자료와 재학·졸업증명서, 인턴근로계약서, 초청 기업 서류와 초청 가능 기업 입증서류, 체재비 입증서류를 냅니다.',
         summary_en='D-10-3 is for high-tech students or recent graduates (within 3 years; under 30, or under 35 with a master\'s) of top universities with an internship contract at a qualifying company. Submit the common documents, an internship plan, the ranking evidence and enrollment/graduation certificate, the internship contract, the company\'s documents and proof it may invite interns, and proof of living funds.',
         docs=d10_common(D10_COMMON_A) + D10_INTERN,
         conditions_ko=D10_INTERN_COND_KO + ['초청기업이 D-10-1 인턴 채용이나 E계열 외국인 고용이 제한되는 경우, 요건을 갖추지 못한 기업과 계약한 경우, 초청인원이 국민고용인원의 20%를 넘는 경우는 제한됩니다.', D10_BLOCK_KO],
         conditions_en=D10_INTERN_COND_EN + ['Barred if the company may not hire D-10-1 interns or E-series foreigners, does not meet the requirements, or the interns would exceed 20% of its Korean staff.', D10_BLOCK_EN], **NOTES)
guidance('D-10-T', 'status_change', section=f'{D10_CHANGE} 4) 최우수인재(D-10-T)', anchor='4) 최우수인재(D-10-T)\n    ❍ 공통서류(신청서, 표준규격 사진, 여권 사본, 수수료)',
         summary_ko='최우수인재 구직(D-10-T)은 최근 5년 이내 세계 대학 순위 100위 이내 대학의 석사 이상 학위를 취득하고 국내 취업을 위해 구직하려는 사람(부처추천 불요)으로, 공통서류(신청서, 표준규격 사진, 여권 사본, 수수료), 구직활동 계획서, 국내·외 우수대학(본교) 졸업(예정)증명서를 냅니다.',
         summary_en='D-10-T is for people with a master\'s or higher from a world top-100 university in the last 5 years seeking work in Korea (no ministry recommendation); submit the common documents (form, photo, passport copy, fee), a job-seeking plan and the graduation (or expected graduation) certificate from that university (main campus).',
         docs=d10_common_t() + [item('job_plan', anchor='❍ 구직활동 계획서'), item('d7ab_top_univ_grad_stay', anchor='국내·외 우수대학(본교) 졸업(예정)증명서')],
         conditions_ko=['입국금지 사유, 특정강력범죄 형 선고, 금고 이상 형 집행 종료 후 5년 미경과, 300만원 이상 벌금 납부 후 3년 미경과, 최근 5년간 출입국관리법 3회 이상 위반 등 결격사유가 있으면 제한됩니다.'],
         conditions_en=['Barred for grounds such as an entry ban, a conviction for a specified violent crime, less than 5 years since a prison sentence ended, less than 3 years since paying a KRW 3 million+ fine, or 3+ immigration violations in 5 years.'], **NOTES)

D10_PT = '공통서류(신청서, 사진, 여권사본, 수수료, 신분증사본), 학위증, 근로계약서, 사업자등록증'
for proc in ('activities_outside_status', 'part_time_work'):
    guidance('D-10-1', proc, section='구직(D-10) 체류자격외 활동 — 1. 시간제 취업활동 허가 특례', anchor='1. 시간제 취업활동 허가 특례',
             summary_ko='일반구직(D-10-1) 중 국내 대학 전문학사 이상 학위 취득 후 3년 미만이고 사회통합프로그램 4단계 이상 또는 TOPIK 4급 이상이며 E-1~E-7 체류 이력이 없는 사람은 제조업(사회통합프로그램 4단계 이상) 또는 농업 분야 시간제 취업을 체류자격외 활동허가로 받을 수 있습니다. D-10-2, D-10-3은 제외됩니다.',
             summary_en='D-10-1 holders within 3 years of a Korean associate-or-higher degree, with KIIP level 4+ or TOPIK 4+ and no prior E-1~E-7 stay, can get an activity permit for part-time work in manufacturing (KIIP level 4+ only) or agriculture. D-10-2 and D-10-3 are excluded.',
             fee_ko='12만원 (시간제취업허가는 유학생이 아니므로 체류자격외활동허가로 처리)', fee_en='KRW 120,000 (handled as an activity permit, not a student work permit)',
             docs=[item('d7ab_app_form', anchor=D10_PT), item('photo', anchor=D10_PT), item('passport_copy', anchor=D10_PT), item('fee', anchor=D10_PT), item('arc_copy', anchor=D10_PT),
                   item('d7ab_degree_cert', anchor='신분증사본), 학위증, 근로계약서'), item('labor_contract', anchor='학위증, 근로계약서, 사업자등록증', role='employer'),
                   item('business_reg', anchor='근로계약서, 사업자등록증, 한국어능력 입증자료', role='employer'),
                   item('d7ab_korean_proof_pt', anchor='한국어능력 입증자료(한국어능력시험(TOPIK) 성적표 등)'), item('d7ab_d10_pt_confirm', anchor='구직 시간제 취업 확인서')],
             conditions_ko=['허용 시간: 주중 25시간, 주말·공휴일 제한 없음(사회통합프로그램 5단계 이상 이수자는 주중 30시간).',
                            '제조업 시간제 취업은 TOPIK 소지자는 제외되고 사회통합프로그램 4단계 이상 이수자에 한합니다. 농업 분야는 어학 요건이 없습니다.',
                            '요건을 갖추었더라도 출입국관리법 및 관련 지침 위반으로 신청이 제한되는 사람은 제외됩니다.'],
             conditions_en=['Hours: 25 per week on weekdays, unlimited on weekends and holidays (30 on weekdays with KIIP level 5+).',
                            'Manufacturing is open only to KIIP level 4+ completers, not TOPIK holders; agriculture has no language requirement.',
                            'People restricted for violating immigration law or guidelines are excluded even if they meet the requirements.'],
             **NOTES)

# ==========================================================================
# Families: let the subtype question cover the procedures whose rules now differ by subtype.
# (Only this group's families are touched; existing options and their targets are unchanged.)
# ==========================================================================
for _fam, _procs in (('D-8', ('status_change', 'visa_issuance', 'visa_issuance_confirmation')), ('D-10', ('status_change', 'visa_issuance'))):
    _d = [d for d in FAMILIES[_fam]['dimensions'] if d['id'] == 'subtype'][0]
    _d['procedures'] = list(_d['procedures']) + [p for p in _procs if p not in _d['procedures']]
FAMILIES['D-9'] = {'dimensions': [
    dim('subtype', '어떤 무역경영(D-9) 활동인가요?', 'Which D-9 activity is yours?', [
        opt('trade', '무역거래자 (무역업 고유번호, 점수제 무역비자 D-9-1)', 'Trader with a trade business number (points-based trade visa, D-9-1)', ['D-9-1', 'D-9#trade-points'], ['무역', '점수제']),
        opt('equipment', '수출설비(기계)의 설치·운영·보수', 'Installing, operating or maintaining exported equipment', ['D-9#equipment', 'D-9#equipment-ship'], ['설비', '기계']),
        opt('ship', '선박건조 및 산업설비 제작·감독', 'Shipbuilding or plant manufacturing supervision', ['D-9#ship', 'D-9#equipment-ship'], ['선박', '조선']),
        opt('business', '외국인 개인사업자 · 유학생 출신 무역경영자', 'Individual business owner or former-student trader', ['D-9-4', 'D-9#individual-business'], ['개인사업자', '회사경영']),
    ], procedures=['status_change', 'extension', 'visa_issuance', 'visa_issuance_confirmation'],
        unsure_ko='외국인등록증의 체류자격란이나 사증에 적힌 세부 약호와 활동 내용을 확인하세요. 모르면 관할 출입국·외국인관서(1345)에 확인하세요.',
        unsure_en='Check the detailed code on your residence card or visa and what you do. If unsure, ask the immigration office (1345).'),
]}
