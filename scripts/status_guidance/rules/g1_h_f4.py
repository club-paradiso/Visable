# G-1 기타 · H-1 관광취업 · H-2 방문취업 · F-4 재외동포 (remaining cells).
# Transcribed from the 2026-10-19 manuals:
#   stay manual — 기타(G-1) chapter (체류자격외 활동 / 근무처의 변경․추가 / 체류자격 부여 / 체류자격 변경허가 / 재입국허가),
#                 관광취업(H-1) chapter, 알기쉬운 외국국적동포 업무 매뉴얼 (H-2 체류관리, F-4 체류자격 외 활동허가);
#   visa manual — 기타(G-1) 사증발급인정서 (외국인환자 G-1-10), 전자사증 발급대상, 관광취업(H-1) 공관장 재량 사증,
#                 동포 매뉴얼 (H-2 사증 신규 발급 중단).
# Runs inside author_rules.py (guidance, item, docdefs, drop, residence, RESIDENCE_ALTS, VISA, STAY …).

docdefs(
    # G-1 체류 (stay manual)
    g1h_accident_claim=('산재보상심사청구서 또는 재심청구서', 'Industrial-accident compensation review claim or re-examination claim', 'applicant', None),
    g1h_family_guardian_accident=('가족관계 기타 보호자 입증 서류(가족에 한함)', 'Proof of family or guardian relationship (family members only)', 'applicant', None),
    g1h_livelihood_form=('생계유지능력 심사확인서', 'Livelihood-capacity review confirmation', 'applicant', None),
    g1h_self_treatment_need=('의료기관에서 발행한 소견서 등 자기치료의 필요성을 입증하는 서류', 'Medical opinion or other proof from a medical institution of the need for treatment', 'applicant', 'hospital'),
    g1h_labor_petition_copy=('노동부 제출 진정서 사본', 'Copy of the petition filed with the Ministry of Labor', 'applicant', None),
    g1h_wage_arrears_confirm=('노동부 발급 체불금품 확인원 등', 'Wage-arrears confirmation issued by the Ministry of Labor, etc.', 'applicant', 'labor_office'),
    g1h_refugee_status_proof=('난민인정신청 접수증 등 난민신청자 또는 인도적 체류허가자임을 입증할 수 있는 서류', 'Refugee-application receipt or other proof that you are a refugee applicant or humanitarian-stay holder', 'applicant', None),
    g1h_refugee_receipt=('난민인정신청 접수증', 'Refugee-status application receipt', 'applicant', None),
    g1h_reason_diag=('진단서 등 사유를 증명할 수 있는 서류', 'Medical certificate or other proof of the reason', 'applicant', 'hospital'),
    g1h_long_treatment_opinion=('의료기관에서 발행한 소견서 등 장기 치료의 필요성을 입증할 수 있는 서류', 'Medical opinion or other proof from a medical institution of the need for long-term treatment', 'medical_institution', 'hospital'),
    g1h_spouse_marriage_proof=('가족관계증명서, 결혼증명서 등 혼인관계를 입증할 수 있는 서류', 'Family-relation certificate, marriage certificate or other proof of the marriage', 'applicant', None),
    g1h_qualification_proof=('해당자격 입증서류 등', 'Proof of the relevant qualification, etc.', 'applicant', None),
    g1h_workplace_docs=('사업자등록증 사본 등 사업장 관련 서류', 'Business registration copy or other workplace documents', 'employer', None),
    # G-1-10 사증발급인정서 (visa manual)
    g1h_cvi_form=('사증발급인정신청서 (별지 제21호 서식)', 'Application for a confirmation of visa issuance (Form 21)', 'inviter', None),
    g1h_medical_purpose_proof=('의료기관에서 발급한 의료목적 입증서류', 'Proof of the medical purpose issued by the medical institution', 'medical_institution', 'hospital'),
    g1h_agency_registration=('사업자등록증 사본 및 유치기관 등록증 사본', 'Copies of the business registration and the patient-attraction institution registration', 'agency', None),
    g1h_family_caregiver_cvi=('동반가족 입증서류 및 간병인 입증서류', 'Proof of accompanying family and of caregiver status', 'applicant', None),
    # H-1 공관장 재량 사증 (visa manual)
    g1h_visa_form=('사증발급신청서', 'Visa application form', 'applicant', None),
    g1h_photo=('사진', 'Photo', 'applicant', None),
    g1h_return_ticket=('왕복항공권', 'Return air ticket', 'applicant', None),
    g1h_funds_3m=('예금잔고증명서 등 일정기간(3개월) 체류할 수 있는 경비 입증서류', 'Bank balance certificate or other proof of funds for a stay of a set period (3 months)', 'applicant', None),
    g1h_criminal_health=('범죄경력증명서, 건강진단서', 'Criminal record certificate, health certificate', 'applicant', None),
    g1h_insurance_cert=('보험증서', 'Insurance certificate', 'applicant', None),
    g1h_school_cert=('재학증명서 또는 최종학력증명서', 'Certificate of enrollment or of highest education', 'applicant', None),
    g1h_wh_plan=('관광취업 활동계획서', 'Working-holiday activity plan', 'applicant', None),
    g1h_mission_other=('기타 재외공관장이 필요하다고 인정하는 서류', 'Other documents the head of the mission considers necessary', 'applicant', None),
    # H-2 취업개시·근무처변경 신고 (stay manual, 동포 매뉴얼)
    g1h_special_employment_copy=('특례고용가능확인서 사본', 'Copy of the special employment permit confirmation', 'employer', None),
    g1h_h2_report_fax=('방문취업 동포 취업개시 등 신고서 및 외국인등록증 사본', 'H-2 employment-start report form and a copy of the residence card', 'applicant', None),
    # F-4 체류자격 외 활동허가 (stay manual, 동포 매뉴얼)
    g1h_geoso_card=('거소신고증', 'Domestic residence report card', 'applicant', None),
    g1h_simple_labor_proof=('단순노무 업종 취업사실을 입증할 수 있는 공적서류(건강보험 가입내역, 소득금액증명원 등)', 'Official proof of employment in a simple-labor industry (health-insurance enrollment record, income certificate, etc.)', 'applicant', None),
)

G1_CHG = '기타(G-1) 체류자격 변경허가'
G1_GRANT = '기타(G-1) 체류자격 부여'
G1_AOS = '기타(G-1) 체류자격외 활동'
G1_UNHCR_ALTS = RESIDENCE_ALTS + [{'ko': '교회·난민지원시설·인권단체·UNHCR 등의 주거확인서', 'en': 'Housing confirmation from a church, refugee shelter, human-rights group or UNHCR'}]
G1_CHG_BASE_ANCHOR = '신청서(별지 제34호 서식), 여권, 표준규격사진 1매, 수수료'


def g1_photo_base(anchor=G1_CHG_BASE_ANCHOR):
    """신청서(별지 제34호 서식), 여권, 표준규격사진 1매, 수수료"""
    return [item('app_form_34', anchor=anchor), item('passport', anchor=anchor), item('photo', anchor=anchor), item('fee', anchor=anchor)]


def g1_refugee_birth_docs():
    """G-1-99: 신청서, 여권(없으면 사유서), 사진, 수수료, 출생증명서 등."""
    return [item('app_form_34', anchor='신청서(별지 제34호 서식), 여권*, 표준규격사진 1매, 수수료'),
            item('passport', anchor='난민 신청의 특수성으로 여권이 없을 경우 그 사유서로 갈음', substitution_allowed=True, substitute_documents=['사유서 (여권이 없는 경우)']),
            item('photo', anchor='여권*, 표준규격사진 1매, 수수료'), item('fee', anchor='여권*, 표준규격사진 1매, 수수료'),
            item('birth_cert_age_proof', anchor='출생증명서 등 부모와의 관계를 입증할 수 있는 서류 및 미성년 자녀의 나이를 확인할 수 있는 서류')]


G1_LIVELIHOOD_NOTE_KO = '매뉴얼에 ‘체류기간 연장’ 심사 시 활용한다고 적혀 있습니다.'
G1_LIVELIHOOD_NOTE_EN = 'The manual notes it is used when the extension is examined.'
G1_99_CONDITIONS_KO = ['부 또는 모가 난민신청자(G-1-5)로 합법체류 중이어야 합니다. 난민신청자가 출국기한 유예자이면 대상이 아닙니다.',
                       '국내 출생 자녀가 난민신청을 하지 않은 상태로 17세 미만이어야 합니다.']
G1_99_CONDITIONS_EN = ['A parent must be staying lawfully as a refugee applicant (G-1-5); not if that parent is under a deferred departure deadline.',
                       'The child born in Korea must be under 17 and must not have applied for refugee status.']

# ==========================================================================
# G-1 체류자격 부여 (국내 출생)
# ==========================================================================
guidance('G-1-5', 'status_grant', section=G1_GRANT + ' — 1. 국내출생 난민신청자(G-1-5)', anchor='1. 국내출생 난민신청자(G-1-5)',
         summary_ko='국내에서 출생한 난민신청자(G-1-5)는 1년 이내로 체류자격을 부여받으며, 특별한 사정이 없으면 가족의 체류기간과 같게 부여됩니다. 신청서·여권·사진·수수료와 난민인정신청 접수증, 체류지 입증 서류를 냅니다.',
         summary_en='A refugee applicant born in Korea (G-1-5) is granted status for up to one year, normally matching the family\'s period of stay. Submit the form, passport, photo and fee with the refugee-application receipt and proof of residence.',
         period_ko='1년 이내 (특별한 사정이 없는 한 가족의 체류기간과 동일)', period_en='Up to 1 year (normally the same as the family\'s period of stay)',
         docs=g1_photo_base('신청서(별지 제34호 서식), 여권 , 표준규격사진 1매, 수수료') + [
             item('g1h_refugee_receipt', anchor='난민인정신청 접수증'),
             residence(anchor='교회·난민지원시설· 인권단체·UNHCR 등의 주거확인서', alts=G1_UNHCR_ALTS)],
         notes_ko=['수수료는 일반 체류외국인과 같습니다.', OFFICER_NOTE_KO], notes_en=['The fee is the same as for other foreign residents.', OFFICER_NOTE_EN])

guidance('G-1-12', 'status_grant', section=G1_GRANT + ' — 2. 인도적 체류허가자의 국내 출생 미성년 자녀 (G-1-12)', anchor='2. 인도적 체류허가자의 국내 출생 미성년 자녀 (G-1-12)',
         summary_ko='인도적 체류허가자의 국내 출생 미성년 자녀(G-1-12)는 인도적 체류허가자의 체류기간 범위에서 체류자격을 부여받습니다. 신청서·여권·사진·수수료와 출생증명서 등 관계·나이 입증 서류, 체류지 입증 서류를 냅니다.',
         summary_en='A minor child born in Korea to a humanitarian-stay holder (G-1-12) is granted status within the holder\'s period of stay. Submit the form, passport, photo and fee with a birth certificate or other proof of parentage and age, and proof of residence.',
         period_ko='인도적 체류허가자의 체류기간 범위 내', period_en='Within the humanitarian-stay holder\'s period of stay',
         docs=g1_photo_base() + [
             item('birth_cert_age_proof', anchor='출생증명서 등 부모와의 관계를 입증할 수 있는 서류 및 미성년 자녀의 나이를 확인할 수 있는 서류'),
             residence(anchor='교회·난민지원시설·인권단체·UNHCR 등의 주거확인서', alts=G1_UNHCR_ALTS)],
         notes_ko=['수수료는 일반 체류외국인과 같습니다.', OFFICER_NOTE_KO], notes_en=['The fee is the same as for other foreign residents.', OFFICER_NOTE_EN])

guidance('G-1-99', 'status_grant', section=G1_GRANT + ' — 3. 난민 신청자(G-1-5)의 국내 출생 미성년 자녀 (G-1-99)', anchor='3. 난민 신청자(G-1-5)의 국내 출생 미성년 자녀 (G-1-99)',
         summary_ko='난민신청자(G-1-5)의 국내 출생 미성년 자녀(G-1-99)는 해당 난민신청자의 체류기간 만료일까지 체류자격을 부여받습니다. 신청서·여권(없으면 사유서)·사진·수수료와 출생증명서 등 관계·나이 입증 서류를 냅니다.',
         summary_en='A minor child born in Korea to a refugee applicant (G-1-5) is granted G-1-99 status until that applicant\'s stay expires. Submit the form, passport (or a statement if there is none), photo and fee with a birth certificate or other proof of parentage and age.',
         period_ko='해당 난민신청자(G-1-5)의 체류기간 만료일까지', period_en='Until the refugee applicant\'s (G-1-5) stay expires',
         conditions_ko=G1_99_CONDITIONS_KO + ['자녀가 난민신청을 한 경우에는 G-1-5 자격 정정이 안내됩니다.'],
         conditions_en=G1_99_CONDITIONS_EN + ['If the child has applied for refugee status, a correction to G-1-5 is advised.'],
         docs=g1_refugee_birth_docs(),
         notes_ko=['수수료는 일반 체류외국인과 같습니다.', OFFICER_NOTE_KO], notes_en=['The fee is the same as for other foreign residents.', OFFICER_NOTE_EN])

# ==========================================================================
# G-1 체류자격 변경허가 (사유별)
# ==========================================================================
guidance('G-1-1', 'status_change', section=G1_CHG + ' — 1. 산업재해 청구 및 치료 중인 사람과 그 가족(G-1-1)', anchor='1. 산업재해 청구 및 치료 중인 사람과 그 가족(G-1-1)',
         summary_ko='산재보상심사 청구·재심청구 중이거나 산재로 치료·요양 중인 사람과 그 가족(배우자·직계가족)은 G-1-1로 변경할 수 있으며, 체류기간 1년 범위(입원치료 및 산재보상 완료 시까지)로 허가됩니다.',
         summary_en='People claiming or appealing industrial-accident compensation or being treated for an industrial accident, and their spouse or direct family, can change to G-1-1 for up to one year (until treatment and compensation are completed).',
         period_ko='체류기간 1년 범위 내 (입원치료 및 산재보상 완료시까지)', period_en='Within 1 year (until hospital treatment and compensation are completed)',
         docs=g1_photo_base() + [
             item('g1h_accident_claim', anchor='산재보상심사청구서 또는 재심청구서'),
             item('industrial_accident_diag', anchor='산재로 인한 병원진단서 등'),
             item('g1h_family_guardian_accident', 'CONDITIONAL_REQUIRED', anchor='가족관계 기타 보호자 입증 서류(가족에 한함)', applies_when_ko='가족이 신청하는 경우', applies_when_en='Family members applying'),
             item('g1h_livelihood_form', anchor='생계유지능력 심사확인서')],
         notes_ko=[OFFICER_NOTE_KO], notes_en=[OFFICER_NOTE_EN])

guidance('G-1-2', 'status_change', section=G1_CHG + ' — 2. 질병, 사고로 치료 중인 사람과 그 가족(G-1-2)', anchor='2. 질병, 사고로 치료 중인 사람과 그 가족(G-1-2)',
         summary_ko='체류 중 질병·사고로 장기치료가 필요해 기존 체류자격을 유지할 수 없는 등록외국인, 단기사증 입국 후 사고로 장기치료가 불가피한 사람과 그 가족은 G-1-2로 변경할 수 있으며 체류기간 1년 범위로 허가됩니다.',
         summary_en='Registered foreigners who need long-term treatment for illness or accident and cannot keep their status, short-term-visa entrants who need long-term treatment after an accident, and their families can change to G-1-2 for up to one year.',
         period_ko='체류기간 1년 범위 내', period_en='Within 1 year',
         conditions_ko=['건강검진·질병치료 등을 위해 단기사증(B-1, B-2, C-3)으로 입국한 뒤 장기치료·요양이 필요하다고 인정된 사람은 외국인환자(G-1-10) 변경 대상입니다.'],
         conditions_en=['People who entered on a short-term visa (B-1, B-2, C-3) for a health check or treatment and are found to need long-term treatment change to foreign patient status (G-1-10) instead.'],
         docs=[item('g1h_self_treatment_need', anchor='의료기관에서 발행한 소견서 등 자기치료의 필요성을 입증하는 서류'),
               item('treatment_cost_proof', anchor='치료 및 체류 비용 조달 능력을 입증하는 서류'),
               item('guarantor', anchor='치료 및 체류 비용 조달 능력을 입증하는 서류 신원보증서'),
               item('family_relation_accompany', 'CONDITIONAL_REQUIRED', anchor='가족관계 입증서류 (배우자 또는 직계가족 동반시만 해당)', applies_when_ko='배우자 또는 직계가족이 동반하는 경우', applies_when_en='If a spouse or direct family member accompanies you'),
               item('g1h_livelihood_form', anchor='생계유지능력 심사확인서 (‘체류기간 연장’ 심사 시 활용)', notes_ko=G1_LIVELIHOOD_NOTE_KO, notes_en=G1_LIVELIHOOD_NOTE_EN)],
         notes_ko=[OFFICER_NOTE_KO], notes_en=[OFFICER_NOTE_EN])

guidance('G-1-3', 'status_change', section=G1_CHG + ' — 3. 각종 소송 진행 중인 사람(G-1-3)', anchor='3. 각종 소송 진행 중인 사람(G-1-3)',
         summary_ko='손해배상·전세금반환 등 민사소송, 형사소송(불구속 공판, 보석, 구속적부심 석방, 집행유예 후 항소·상고 등), 가사·행정소송을 진행 중인 사람은 G-1-3으로 변경할 수 있으며 체류기간 6월 범위로 허가됩니다. 원칙적으로 체류지 관할 관서에서 접수합니다.',
         summary_en='People pursuing civil suits (damages, deposit return), criminal proceedings (trial without detention, bail, release on review, appeal after a suspended sentence) or family/administrative suits can change to G-1-3 for up to 6 months, filed in principle at the office for their address.',
         period_ko='체류기간 6월 범위 이내', period_en='Within 6 months',
         channel_ko='원칙적으로 외국인의 체류지 관할 청(사무소·출장소)에서 접수', channel_en='In principle, the immigration office for your address',
         docs=g1_photo_base() + [
             item('lawsuit_docs', anchor='소장 사본, 소송제기 증명원, 법률구조결정서 사본, 기타 청구권의 존재를 확인할 수 있는 서류'),
             item('guarantor', anchor='기타 청구권의 존재를 확인할 수 있는 서류 신원보증서'),
             item('family_or_guardian_proof', 'CONDITIONAL_REQUIRED', anchor='가족관계 또는 보호자 입증서류 (보호자․가족에 한함)', applies_when_ko='보호자·가족이 신청하는 경우', applies_when_en='Guardians or family members applying'),
             item('g1h_livelihood_form', anchor='생계유지능력 심사확인서 (‘체류기간 연장’ 심사 시 활용)', notes_ko=G1_LIVELIHOOD_NOTE_KO, notes_en=G1_LIVELIHOOD_NOTE_EN)],
         notes_ko=[OFFICER_NOTE_KO], notes_en=[OFFICER_NOTE_EN])

guidance('G-1-4', 'status_change', section=G1_CHG + ' — 4. 임금체불로 노동관서에서 중재 중인 사람(G-1-4)', anchor='4. 임금체불로 노동관서에서 중재 중인 사람(G-1-4)',
         summary_ko='고용노동부에 체불임금 진정을 접수해 중재 중이거나, 진정이 해결되지 않아 민사소송 중인 사람은 G-1-4로 변경할 수 있으며 체류기간 6월 범위로 허가됩니다.',
         summary_en='People whose unpaid-wage petition is under mediation at the Ministry of Employment and Labor, or who are suing after it went unresolved, can change to G-1-4 for up to 6 months.',
         period_ko='체류기간 6월 범위 내', period_en='Within 6 months',
         docs=g1_photo_base() + [
             item('g1h_labor_petition_copy', anchor='노동부 제출 진정서 사본'),
             item('g1h_wage_arrears_confirm', anchor='노동부 발급 체불금품 확인원 등'),
             item('guarantor', anchor='노동부 발급 체불금품 확인원 등 신원보증서'),
             item('g1h_livelihood_form', anchor='생계유지능력 심사확인서 (‘체류기간 연장’ 심사 시 활용)', notes_ko=G1_LIVELIHOOD_NOTE_KO, notes_en=G1_LIVELIHOOD_NOTE_EN)],
         notes_ko=[OFFICER_NOTE_KO], notes_en=[OFFICER_NOTE_EN])


def g1_refugee_change_docs():
    a = '신청서(별지 제34호 서식), 여권 및 외국인등록증, 표준규격사진 1매, 수수료'
    return [item('app_form_34', anchor=a), item('passport', anchor=a), item('arc', anchor=a), item('photo', anchor=a), item('fee', anchor=a),
            item('g1h_refugee_status_proof', anchor='난민인정신청 접수증 등 난민신청자 또는 인도적 체류허가자임을 입증할 수 있는 서류'),
            residence(anchor='교회·난민지원시설· 인권단체·UNHCR 등의 주거확인서', alts=G1_UNHCR_ALTS)]


G1_REFUGEE_CHG_SECTION = G1_CHG + ' — 5. 난민신청자(G-1-5) 및 난민불인정자 중 인도적 체류허가자(G-1-6)'
G1_REFUGEE_CHG_ANCHOR = '5. 난민신청자(G-1-5) 및 난민불인정자 중 인도적 체류허가자(G-1-6)'
guidance('G-1-5', 'status_change', section=G1_REFUGEE_CHG_SECTION, anchor=G1_REFUGEE_CHG_ANCHOR,
         summary_ko='대한민국 안에서 난민인정을 신청한 외국인은 난민신청자(G-1-5)로 변경할 수 있으며 6개월 내지 1년 범위로 허가됩니다. 신청서·여권·외국인등록증·사진·수수료와 난민인정신청 접수증 등 입증서류, 체류지 입증 서류를 냅니다.',
         summary_en='A foreigner in Korea who has applied for refugee status can change to G-1-5 for 6 months to 1 year. Submit the form, passport, residence card, photo and fee with the refugee-application receipt or similar proof and proof of residence.',
         period_ko='6개월 내지 1년 범위 내 (소송 등 수행 예정기간, 인도적 사유 등을 고려해 법정기한 1년 내에서 탄력적으로 부여 가능)', period_en='6 months to 1 year (may be set flexibly within the 1-year legal limit for lawsuits or humanitarian reasons)',
         docs=g1_refugee_change_docs(),
         notes_ko=['수수료는 일반 체류외국인과 같습니다.', OFFICER_NOTE_KO], notes_en=['The fee is the same as for other foreign residents.', OFFICER_NOTE_EN])
guidance('G-1-6', 'status_change', section=G1_REFUGEE_CHG_SECTION, anchor=G1_REFUGEE_CHG_ANCHOR,
         summary_ko='난민불인정자 중 인도적 체류허가를 받은 사람은 G-1-6으로 변경하며, 통보를 받은 날부터 체류기간 1년이 부여됩니다. 신청서·여권·외국인등록증·사진·수수료와 인도적 체류허가자임을 입증하는 서류, 체류지 입증 서류를 냅니다.',
         summary_en='A rejected refugee applicant granted humanitarian stay changes to G-1-6 and receives one year from the date of notification. Submit the form, passport, residence card, photo and fee with proof of humanitarian-stay status and proof of residence.',
         period_ko='통보를 받은 날부터 체류기간 1년', period_en='1 year from the date of notification',
         docs=g1_refugee_change_docs(),
         notes_ko=['수수료는 일반 체류외국인과 같습니다.', OFFICER_NOTE_KO], notes_en=['The fee is the same as for other foreign residents.', OFFICER_NOTE_EN])

guidance('G-1-9', 'status_change', section=G1_CHG + ' — 6. 임신․출산 등 인도적 배려가 불가피한 사람 (G-1-9)', anchor='6. 임신․출산 등 인도적 배려가 불가피한 사람 (G-1-9)',
         summary_ko='임신·출산 등으로 즉시 출국이 곤란한 사람은 G-1-9로 변경할 수 있으며 체류기간 1년이 부여됩니다. 신청서·여권·사진·수수료와 진단서 등 사유 증명서류, 신원보증서를 냅니다.',
         summary_en='People who cannot leave immediately because of pregnancy, childbirth or similar reasons can change to G-1-9 and receive one year. Submit the form, passport, photo and fee with a medical certificate or other proof of the reason and a letter of guarantee.',
         period_ko='체류기간 1년', period_en='1 year',
         docs=g1_photo_base() + [item('g1h_reason_diag', anchor='진단서 등 사유를 증명할 수 있는 서류'),
                                 item('guarantor', anchor='진단서 등 사유를 증명할 수 있는 서류 신원보증서')],
         notes_ko=[OFFICER_NOTE_KO], notes_en=[OFFICER_NOTE_EN])

guidance('G-1-10', 'status_change', section=G1_CHG + ' — 7. 외국인환자 (G-1-10)', anchor='7. 외국인환자 (G-1-10)',
         summary_ko='B-1, B-2, C-3(C-3-3 포함)으로 입국한 뒤 의료기관 검진 등으로 장기치료·요양이 필요하다고 인정된 사람과 동반이 필요한 배우자 등 가족·간병인은 외국인환자(G-1-10)로 변경하며 1년 이내로 허가됩니다.',
         summary_en='People who entered on B-1, B-2 or C-3 (including C-3-3) and are found by a medical institution to need long-term treatment, plus the spouse, family or caregiver who must accompany them, change to G-1-10 for up to one year.',
         period_ko='1년 이내 범위', period_en='Up to 1 year',
         docs=[item('app_form_34', anchor='① 신청서(별지 제34호 서식), 여권, 표준규격사진 1매, 수수료'), item('passport', anchor='① 신청서(별지 제34호 서식), 여권, 표준규격사진 1매, 수수료'),
               item('photo', anchor='① 신청서(별지 제34호 서식), 여권, 표준규격사진 1매, 수수료'), item('fee', anchor='① 신청서(별지 제34호 서식), 여권, 표준규격사진 1매, 수수료'),
               item('g1h_long_treatment_opinion', anchor='의료기관에서 발행한 소견서 등 장기 치료의 필요성을 입증할 수 있는 서류'),
               item('treatment_cost_proof', anchor='치료 및 체류 비용 조달 능력을 입증할 수 있는 서류', does_not_apply_when_ko='유치 기관 또는 신원보증인이 신원을 보증하는 경우 제출 생략', does_not_apply_when_en='Omitted if the attracting institution or a guarantor vouches for you'),
               item('family_caregiver_proof', 'CONDITIONAL_REQUIRED', anchor='④ 가족관계 및 간병인 입증서류', applies_when_ko='동반가족 또는 간병인이 신청하는 경우', applies_when_en='When an accompanying family member or caregiver applies'),
               residence(anchor='체류지입증서류(임대차계약서, 숙소제공 확인서, 숙박료 납입 영수증 등)', alts=[{'ko': '임대차계약서', 'en': 'Lease contract'}, {'ko': '숙소제공 확인서', 'en': 'Accommodation provision confirmation'}, {'ko': '숙박료 납입 영수증 등', 'en': 'Lodging payment receipt, etc.'}])],
         notes_ko=[OFFICER_NOTE_KO], notes_en=[OFFICER_NOTE_EN])

guidance('G-1-11', 'status_change', section=G1_CHG + ' — 8. 성폭력피해자 등 인도적 고려가 필요한 사람 (G-1-11)', anchor='8. 성폭력피해자 등 인도적 고려가 필요한 사람 (G-1-11)',
         summary_ko='성폭력범죄, 성매매 강요, 상습폭행·학대, 심각한 범죄 피해 등을 이유로 재판·수사 또는 민·형사상 권리구제 절차가 진행 중인 체류외국인은 G-1-11로 변경할 수 있으며 체류기간 1년이 부여됩니다.',
         summary_en='Foreign residents whose trial, investigation or civil/criminal remedy is under way because of sexual violence, forced prostitution, habitual assault or abuse, or other serious crime can change to G-1-11 and receive one year.',
         period_ko='체류기간 1년', period_en='1 year',
         docs=g1_photo_base() + [item('rights_relief_proof', anchor='소송관련 서류 등 권리구제 입증서류'),
                                 item('guarantor', anchor='소송관련 서류 등 권리구제 입증서류 신원보증서')],
         notes_ko=[OFFICER_NOTE_KO], notes_en=[OFFICER_NOTE_EN])

guidance('G-1-99', 'status_change', section=G1_CHG + ' — 9. 기타 사유에 해당되는 사람 (G-1-99)', anchor='9. 기타 사유에 해당되는 사람 (G-1-99)',
         summary_ko='매뉴얼의 G-1-99 변경 대상은 요건을 모두 갖춘 난민신청자(G-1-5)의 국내 출생 자녀이며, 해당 난민신청자의 체류기간 만료일까지 허가됩니다. 신청서·여권(없으면 사유서)·사진·수수료와 출생증명서 등 관계·나이 입증 서류를 냅니다.',
         summary_en='The manual\'s G-1-99 change covers a child born in Korea to a refugee applicant (G-1-5) who meets all the conditions; it runs until that applicant\'s stay expires. Submit the form, passport (or a statement if there is none), photo and fee with proof of parentage and age.',
         period_ko='해당 난민신청자(G-1-5)의 체류기간 만료일까지', period_en='Until the refugee applicant\'s (G-1-5) stay expires',
         conditions_ko=G1_99_CONDITIONS_KO + ['국내 출생 자녀가 난민 신청을 한 경우에는 대상이 아닙니다.'],
         conditions_en=G1_99_CONDITIONS_EN + ['Not eligible if the child has applied for refugee status.'],
         docs=g1_refugee_birth_docs(),
         notes_ko=[OFFICER_NOTE_KO], notes_en=[OFFICER_NOTE_EN])

guidance('G-1-12', 'status_change', section=G1_CHG + ' — 10. 인도적 체류허가자의 가족 (G-1-12)', anchor='10. 인도적 체류허가자의 가족 (G-1-12)',
         summary_ko='인도적 체류허가자의 배우자와 미성년 자녀(배우자가 있는 미성년자 제외)는 G-1-12로 변경하며, 인도적 체류허가자의 체류기간 범위에서 허가됩니다. 배우자는 혼인관계 입증서류, 자녀는 출생증명서 등 관계·나이 입증 서류를 냅니다.',
         summary_en='The spouse and minor children (not married minors) of a humanitarian-stay holder change to G-1-12 within the holder\'s period of stay. A spouse submits proof of the marriage; a child submits a birth certificate or other proof of parentage and age.',
         period_ko='인도적 체류허가자의 체류기간 범위 내', period_en='Within the humanitarian-stay holder\'s period of stay',
         docs=[item('app_form_34', anchor='신청서(별지 제34호 서식), 여권 및 외국인등록증, 표준규격사진 1매, 수수료'), item('passport', anchor='신청서(별지 제34호 서식), 여권 및 외국인등록증, 표준규격사진 1매, 수수료'),
               item('arc', anchor='신청서(별지 제34호 서식), 여권 및 외국인등록증, 표준규격사진 1매, 수수료'), item('photo', anchor='신청서(별지 제34호 서식), 여권 및 외국인등록증, 표준규격사진 1매, 수수료'),
               item('fee', anchor='신청서(별지 제34호 서식), 여권 및 외국인등록증, 표준규격사진 1매, 수수료'),
               item('g1h_spouse_marriage_proof', 'CONDITIONAL_REQUIRED', anchor='(배우자) 가족관계증명서, 결혼증명서 등 혼인관계를 입증할 수 있는 서류', applies_when_ko='배우자', applies_when_en='Spouse'),
               item('birth_cert_age_proof', 'CONDITIONAL_REQUIRED', anchor='(미성년 자녀) 출생증명서 등 부모와의 관계를 입증할 수 있는 서류', applies_when_ko='미성년 자녀', applies_when_en='Minor child'),
               residence(anchor='교회·난민지원시설·인권단체·UNHCR 등의 주거확인서', alts=G1_UNHCR_ALTS)],
         notes_ko=[OFFICER_NOTE_KO], notes_en=[OFFICER_NOTE_EN])

# ==========================================================================
# G-1 체류자격외 활동
# ==========================================================================
G1_AOS1_ANCHOR = '신청서(별지 제34호 서식), 여권, 외국인등록증, 수수료 고용계약서, 사업자등록증 사본, 해당자격 입증서류 등'
for _code in ('G-1-7', 'G-1-11', 'G-1-99'):
    guidance(_code, 'activities_outside_status', section=G1_AOS + ' — 1. 성폭력 피해자 등에 대한 체류자격외 활동허가', anchor='1. 성폭력 피해자 등에 대한 체류자격외 활동허가',
             summary_ko='사고 등으로 사망한 사람의 가족(G-1-7), 성폭력피해자 등(G-1-11), 기타 사유(G-1-99) 해당자는 취업제한 분야를 제외한 단순노무 분야에서 일하려면 체류자격외 활동허가를 받습니다. 전문분야 취업은 관련 법령이 정한 자격을 갖춰야 하며, 허가기간은 체류기간 범위에서 최대 1년입니다.',
             summary_en='Family of a deceased accident victim (G-1-7), sexual-violence victims and similar (G-1-11) and other-reason holders (G-1-99) need permission for activities outside status to work in simple-labor jobs outside the restricted fields. Professional jobs require the qualifications set by law; permission lasts up to one year within the period of stay.',
             period_ko='체류기간 범위 내에서 최대 1년', period_en='Up to 1 year within the period of stay',
             conditions_ko=['취업제한 분야가 아니어야 합니다.', '취업 예정지 고용주가 「외국인 불법 고용주 등에 대한 사증발급인정서 발급 등 제한기준」에 따른 제한 대상자가 아니어야 합니다.',
                            '연장 시 취업 변동 여부를 확인하며, 취업이 바뀌면 다시 사전에 체류자격외 활동허가를 받아야 합니다.'],
             conditions_en=['The job must not be in a restricted field.', 'The prospective employer must not be restricted under the criteria limiting confirmations of visa issuance for illegal employers.',
                            'Changes in employment are checked at extension; if your job changes you must get permission again in advance.'],
             docs=[item('app_form_34', anchor=G1_AOS1_ANCHOR), item('passport', anchor=G1_AOS1_ANCHOR), item('arc', anchor=G1_AOS1_ANCHOR), item('fee', anchor=G1_AOS1_ANCHOR),
                   item('employment_contract', anchor=G1_AOS1_ANCHOR, role='employer'),
                   item('business_reg_copy', anchor=G1_AOS1_ANCHOR),
                   item('g1h_qualification_proof', anchor=G1_AOS1_ANCHOR)],
             notes_ko=[OFFICER_NOTE_KO], notes_en=[OFFICER_NOTE_EN])

G1_AOS2_BASE = '신청서(별지 제34호 서식), 여권, 외국인등록증 고용계약서 사업자등록증 사본 등 사업장 관련 서류'


def g1_refugee_aos_docs():
    return [item('app_form_34', anchor=G1_AOS2_BASE), item('passport', anchor=G1_AOS2_BASE), item('arc', anchor=G1_AOS2_BASE),
            item('employment_contract', anchor=G1_AOS2_BASE, role='employer'), item('g1h_workplace_docs', anchor=G1_AOS2_BASE),
            item('fee', anchor='사업장 관련 서류 수수료는 일반 체류외국인과 동일')]


guidance('G-1-5', 'activities_outside_status', section=G1_AOS + ' — 2. 난민신청자에 대한 체류자격외 취업활동 허가', anchor='2. 난민신청자에 대한 체류자격외 취업활동 허가',
         summary_ko='난민인정 신청 후 6개월이 지난 난민신청자(또는 근로능력 없는 피부양자 부양 등으로 청장 등이 특히 필요하다고 인정한 사람)는 건설업 등 취업제한 업종을 제외한 단순노무 업무에 대해 체류자격외 활동허가를 받을 수 있으며, 체류기간 범위에서 체류허가기간까지 허가됩니다.',
         summary_en='Refugee applicants six months after applying (or those the office head finds it especially necessary for, such as supporting a dependant unable to work) can get permission for simple-labor work outside the restricted industries, including construction, up to the end of their permitted stay.',
         period_ko='체류기간 범위 내에서 체류허가기간까지', period_en='Up to the end of the permitted stay, within the period of stay',
         conditions_ko=['입증자료 제출 지연, 소재 불명, 보호 등 신청자의 귀책 사유로 인한 기간은 6개월에 산입하지 않습니다.',
                        '외국어 회화강사(E-2) 등 전문분야에 취업하려면 일반 체류외국인과 같은 서류와 절차를 거칩니다.',
                        '취업제한 업종에 불법취업하면 일반 체류외국인에 준해 사범처리됩니다.'],
         conditions_en=['Time caused by the applicant (late evidence, unknown whereabouts, detention) does not count toward the six months.',
                        'Professional work such as foreign-language instruction (E-2) follows the same documents and procedure as for other foreign residents.',
                        'Illegal work in a restricted industry is handled as an offence, as for other foreign residents.'],
         docs=g1_refugee_aos_docs(),
         notes_ko=[OFFICER_NOTE_KO], notes_en=[OFFICER_NOTE_EN])

G1_AOS3_ANCHOR = '난민인정을 받지 못한 자 중 인도적 체류허가를 받은 자, 인도적체류 허가자의 가족(G-1-12)'
for _code, _who_ko, _who_en in (('G-1-6', '인도적 체류허가자(G-1-6)', 'Humanitarian-stay holders (G-1-6)'), ('G-1-12', '인도적 체류허가자의 가족(G-1-12)', 'Family of a humanitarian-stay holder (G-1-12)')):
    guidance(_code, 'activities_outside_status', section=G1_AOS + ' — 3. 인도적체류자에 대한 체류자격외 취업활동 허가', anchor=G1_AOS3_ANCHOR,
             summary_ko=f'{_who_ko}는 난민신청자와 같은 범위에서 체류자격외 취업활동 허가를 받을 수 있으며, 건설업 취업도 가능합니다. 허가기간은 체류기간 범위에서 최대 1년이고 제출서류는 난민신청자와 같습니다.',
             summary_en=f'{_who_en} can get permission to work outside status in the same range as refugee applicants, construction included. Permission lasts up to one year within the period of stay; the documents are the same as for refugee applicants.',
             period_ko='체류기간 범위 내에서 최대 1년', period_en='Up to 1 year within the period of stay',
             conditions_ko=['건설업에 취업할 때는 체류자격외 활동허가서를 받아 ‘외국인노동자 건설업 기초안전 보건교육’을 이수해야 합니다.',
                            '외국어 회화강사(E-2) 등 전문분야에 취업하려면 일반 체류외국인과 같은 서류와 절차를 거칩니다.'],
             conditions_en=['For construction work, receive the permission document and complete the basic construction safety and health training for foreign workers.',
                            'Professional work such as foreign-language instruction (E-2) follows the same documents and procedure as for other foreign residents.'],
             docs=g1_refugee_aos_docs(),
             notes_ko=[OFFICER_NOTE_KO], notes_en=[OFFICER_NOTE_EN])

# ==========================================================================
# G-1 근무처의 변경․추가 / 재입국허가 (chapter-wide)
# ==========================================================================
guidance('G-1', 'workplace_change', state='CONDITIONAL', completeness='PARTIALLY_STRUCTURED', section='기타(G-1) 근무처의 변경․추가', anchor='근무처(고용주)가 변경되는 경우 새로운 체류자격외 활동허가 필요',
         summary_ko='기타(G-1) 자격자의 취업허가는 사전 허가 사항이며(난민신청자, 인도적체류자 등 동일), 근무처(고용주)가 바뀌면 새로운 체류자격외 활동허가를 받아야 합니다. 수수료는 일반 체류외국인과 같습니다.',
         summary_en='For G-1 holders (refugee applicants and humanitarian-stay holders alike), permission to work must be obtained in advance, and a change of workplace (employer) needs a new permission for activities outside status. The fee is the same as for other foreign residents.',
         notes_ko=['서류는 해당 체류자격외 활동허가 안내를 따릅니다.'], notes_en=['Documents follow the activities-outside-status guidance.'])

G1_REENTRY_DOCS = '신청서 (별지 34호 서식), 여권, 외국인등록증, 수수료'
REENTRY_COND_KO = ['등록을 마친 외국인이 출국한 날로부터 1년 이내에 재입국하려는 경우 재입국허가가 면제됩니다.',
                   '체류기간이 1년보다 적게 남아 있으면 체류기간 범위 내에서 면제됩니다.',
                   '입국규제 및 사증발급규제자는 체류지 관할 청(사무소·출장소)에 방문하여 재입국허가를 받아야 합니다.']
REENTRY_COND_EN = ['Registered foreigners re-entering within one year of departure are exempt from the re-entry permit.',
                   'If less than a year of stay remains, the exemption runs within the remaining stay.',
                   'People under an entry ban or visa-issuance restriction must visit the office for their address to get a re-entry permit.']
guidance('G-1', 'reentry', section='기타(G-1) 재입국허가', anchor='재입국허가 면제 제도 시행',
         summary_ko='등록외국인은 출국한 날로부터 1년 이내(남은 체류기간이 1년보다 짧으면 그 범위) 재입국하면 재입국허가가 면제됩니다. 입국규제·사증발급규제자는 체류지 관할 관서를 방문해 신청서, 여권, 외국인등록증, 수수료로 재입국허가를 받습니다.',
         summary_en='Registered foreigners re-entering within one year of departure (or within the remaining stay if shorter) are exempt. People under an entry ban or visa restriction visit the office for their address with the form, passport, residence card and fee.',
         conditions_ko=REENTRY_COND_KO, conditions_en=REENTRY_COND_EN,
         docs=[item('app_form_34', anchor=G1_REENTRY_DOCS), item('passport', anchor=G1_REENTRY_DOCS), item('arc', anchor=G1_REENTRY_DOCS), item('fee', anchor=G1_REENTRY_DOCS)],
         notes_ko=[OFFICER_NOTE_KO], notes_en=[OFFICER_NOTE_EN])

# ==========================================================================
# G-1-10 외국인환자 — 사증발급인정서 / 전자사증 (visa manual)
# ==========================================================================
guidance('G-1-10', 'visa_issuance_confirmation', manual=VISA, section='기타(G-1) 사증발급인정서 발급대상 — 1. 외국인환자(C-3-3, G-1-10)에 대한 사증발급인정서 발급',
         anchor='1. 외국인환자(C-3-3, G-1-10)에 대한 사증발급인정서 발급',
         summary_ko='외국인 환자 유치기관의 초청으로 국내 의료기관에서 진료·요양하려는 외국인 환자와 간병 등을 위해 동반입국이 필요한 가족·간병인은, 「의료법」상 유치의료기관 또는 유치업자로 등록한 초청자가 대한민국 비자포털 온라인으로만 사증발급인정서를 신청할 수 있습니다.',
         summary_en='Foreign patients invited by a registered patient-attraction institution for treatment in Korea, and family or caregivers who must accompany them, are sponsored only online through the Korea Visa Portal by an inviter registered under the Medical Service Act.',
         channel_ko='초청자가 대한민국 비자포털 온라인 신청 (초청자의 사업장 소재지 관할 출입국·외국인청)', channel_en='Inviter applies online via the Korea Visa Portal (office for the inviter\'s place of business)',
         filer='inviter',
         docs=[item('g1h_cvi_form', anchor='사증발급인정신청서 (별지 제21호 서식), 여권사본, 표준규격사진 1매'),
               item('passport_copy', anchor='사증발급인정신청서 (별지 제21호 서식), 여권사본, 표준규격사진 1매'),
               item('photo', anchor='사증발급인정신청서 (별지 제21호 서식), 여권사본, 표준규격사진 1매'),
               item('g1h_medical_purpose_proof', anchor='의료기관에서 발급한 의료목적 입증서류'),
               item('treatment_cost_proof', anchor='치료 및 체류 비용 조달 능력을 입증할 수 있는 서류',
                    does_not_apply_when_ko='유치 기관이 피초청인에 대하여 신원보증을 하는 경우 제출 생략 (유치기관이 최초 초청하거나 불법체류자가 다수 발생한 유치기관은 징구 가능)',
                    does_not_apply_when_en='Omitted if the institution guarantees the invitee (may still be required for a first-time inviter or one with many overstayers)'),
               item('g1h_agency_registration', anchor='사업자등록증 사본 및 유치기관 등록증 사본', does_not_apply_when_ko='대한민국비자포털을 통해 유치기관으로 등록한 경우 생략', does_not_apply_when_en='Omitted if registered as an institution through the Korea Visa Portal'),
               item('g1h_family_caregiver_cvi', 'CONDITIONAL_REQUIRED', anchor='동반가족 입증서류 및 간병인 입증서류', applies_when_ko='동반가족 또는 간병인', applies_when_en='Accompanying family or caregiver',
                    notes_ko='인정서류: 본국 또는 국내 소재 본국대사관에서 발행한 가족관계 확인서류(결혼증명서·가족관계기록사항에 관한 증명서 또는 출생증명서 등)', notes_en='Accepted: family-relation documents issued by the home country or its embassy in Korea (marriage certificate, family-relation record or birth certificate, etc.)')],
         notes_ko=['출입국·외국인청(사무소·출장소)장은 심사를 위해 첨부서류의 일부를 가감할 수 있습니다.'], notes_en=['The immigration office head may add or waive some documents for the examination.'])

guidance('G-1-10', 'electronic_visa', manual=VISA, completeness='PARTIALLY_STRUCTURED', section='전자사증 — 1. 발급대상',
         anchor='우수 유치기관에서 초청한 의료관광객 및 동반가족․ 간병인(C-3-3, G-1-10)',
         summary_ko='법무부장관이 ‘의료관광 우수 유치기관’으로 지정한 우수 유치기관에서 초청한 의료관광객과 동반가족·간병인(C-3-3, G-1-10)은 전자사증 발급대상입니다. 제출서류는 사증발급인정서 발급대상자와 같습니다.',
         summary_en='Medical tourists and their accompanying family or caregivers (C-3-3, G-1-10) invited by an institution the Minister of Justice has designated as an excellent medical-tourism institution can get an electronic visa. The documents are the same as for the confirmation of visa issuance.',
         notes_ko=['제출서류는 G-1-10 사증발급인정서 안내를 따릅니다.'], notes_en=['Documents follow the G-1-10 confirmation-of-visa-issuance guidance.'])

# ==========================================================================
# H-1 관광취업
# ==========================================================================
H1_VISA_ANCHOR = '사증발급신청서, 사진, 여권, 왕복항공권'
H1_RECIP_ANCHOR = '상호주의에 따라 제출 여부 결정'
guidance('H-1', 'visa_issuance', manual=VISA, section='관광취업(H-1) 공관장 재량으로 발급할 수 있는 사증 — 4. 제출서류', anchor='협정체결국을 관할하는 재외공관',
         summary_ko='관광취업(H-1) 사증은 협정체결국을 관할하는 재외공관에 신청합니다. 사증발급신청서·사진·여권·왕복항공권과 체류경비 입증서류, 관광취업 활동계획서를 내고, 범죄경력증명서·건강진단서, 보험증서, 재학·최종학력증명서는 상호주의에 따라 제출 여부가 정해집니다.',
         summary_en='Apply for an H-1 working-holiday visa at the Korean mission covering the agreement country. Submit the form, photo, passport, return ticket, proof of funds and an activity plan; whether a criminal record and health certificate, insurance certificate and school certificate are needed is decided by reciprocity.',
         channel_ko='협정체결국을 관할하는 재외공관 (오스트리아 국민은 협정에 따라 주일본 대사관 등에서도 신청 가능)', channel_en='The Korean mission covering the agreement country (Austrians may also apply at the embassy in Japan and other listed missions)',
         fee_ko='상대 국가가 우리 국민에게 워킹홀리데이 사증 수수료를 징수하면 상호주의에 따라 징수', fee_en='Charged by reciprocity if the other country charges Korean nationals a working-holiday visa fee',
         docs=[item('g1h_visa_form', anchor=H1_VISA_ANCHOR), item('g1h_photo', anchor=H1_VISA_ANCHOR), item('passport', anchor=H1_VISA_ANCHOR),
               item('g1h_return_ticket', anchor=H1_VISA_ANCHOR, substitution_allowed=True, substitute_documents=['상당금액 예치서류 (왕복항공권이 없는 경우)']),
               item('g1h_funds_3m', anchor='예금잔고증명서 등 일정기간(3개월)'),
               item('g1h_criminal_health', 'CONDITIONAL_REQUIRED', anchor='범죄경력증명서, 건강진단서', applies_when_ko='상호주의에 따라 제출 여부 결정 (미국은 한-미 WEST 프로그램 양해각서에 따름)', applies_when_en='Required or not by reciprocity (for the US, per the Korea-US WEST MOU)'),
               item('g1h_insurance_cert', 'CONDITIONAL_REQUIRED', anchor='보험증서', applies_when_ko='상호주의에 따라 제출 여부 결정', applies_when_en='Required or not by reciprocity'),
               item('g1h_school_cert', 'CONDITIONAL_REQUIRED', anchor='재학증명서 또는 최종학력증명서', applies_when_ko='상호주의에 따라 제출 여부 결정', applies_when_en='Required or not by reciprocity'),
               item('g1h_wh_plan', anchor='관광취업 활동계획서', notes_ko='대략적인 내용도 가능하며 인터뷰 등으로 확인된 경우 제출 생략 가능', notes_en='A rough outline is acceptable; may be omitted if confirmed at interview'),
               item('g1h_mission_other', 'MAY_BE_REQUESTED_BY_OFFICER', anchor='기타 재외공관장이 필요하다고 인정하는 서류')],
         notes_ko=[OFFICER_NOTE_KO], notes_en=[OFFICER_NOTE_EN])

guidance('H-1', 'visa_issuance_confirmation', manual=VISA, state='NOT_APPLICABLE', completeness='SOURCE_ONLY', section='관광취업(H-1) 사증발급인정서 발급대상', anchor='사증발급인정서 발급대상 아님',
         summary_ko='관광취업(H-1)은 사증발급인정서 발급대상이 아닙니다.', summary_en='H-1 is not eligible for a confirmation of visa issuance.')

guidance('H-1', 'workplace_change', state='CONDITIONAL', completeness='PARTIALLY_STRUCTURED', section='관광취업(H-1) 근무처의 변경․추가', anchor='별도의 근무처 추가 또는 변경없이 취업 활동 가능',
         summary_ko='관광취업(H-1)은 별도의 근무처 추가 또는 변경 없이 취업 활동을 할 수 있습니다. 다만 일정한 자격요건·자격증이 필요하거나 E-7(특정활동) 직종에 해당하는 직종에 취업하려는 경우에는 제한됩니다.',
         summary_en='H-1 holders may work without a separate workplace addition or change. This does not apply to jobs that require specific qualifications or licences or fall under E-7 (specific activities) occupations.')

H1_REENTRY_DOCS = '(제출서류 : 신청서 (별지 34호 서식), 여권, 외국인등록증, 수수료)'
guidance('H-1', 'reentry', section='관광취업(H-1) 재입국허가', anchor='재입국허가 면제 제도 시행',
         summary_ko='등록외국인은 출국한 날로부터 1년 이내(남은 체류기간이 1년보다 짧으면 그 범위) 재입국하면 재입국허가가 면제됩니다. 입국규제·사증발급규제자는 체류지 관할 관서를 방문해 신청서, 여권, 외국인등록증, 수수료로 재입국허가를 받습니다.',
         summary_en='Registered foreigners re-entering within one year of departure (or within the remaining stay if shorter) are exempt. People under an entry ban or visa restriction visit the office for their address with the form, passport, residence card and fee.',
         conditions_ko=REENTRY_COND_KO, conditions_en=REENTRY_COND_EN,
         docs=[item('app_form_34', anchor=H1_REENTRY_DOCS), item('passport', anchor=H1_REENTRY_DOCS), item('arc', anchor=H1_REENTRY_DOCS), item('fee', anchor=H1_REENTRY_DOCS)],
         notes_ko=[OFFICER_NOTE_KO], notes_en=[OFFICER_NOTE_EN])

# ==========================================================================
# H-2 방문취업 (알기쉬운 외국국적동포 업무 매뉴얼)
# ==========================================================================
guidance('H-2', 'visa_issuance', manual=VISA, state='GENERALLY_NOT_PERMITTED', completeness='SOURCE_ONLY',
         section='알기쉬운 외국국적동포 업무 매뉴얼 — 2. 방문취업제(H-2) □ 동포 체류자격 통합에 따라 방문취업(H-2) 사증의 신규 발급 중단',
         anchor='방문취업(H-2)과 재외동포(F-4)로 이원화된 동포 체류자격을 재외동포(F-4) 자격으로 통합하여 중국 및 CIS 지역 동포들에게도 재외동포(F-4) 사증을 발급하고, 방문취업(H-2) 사증의 신규 발급을 중단합니다',
         summary_ko='2026년 2월 12일부터 동포 체류자격을 재외동포(F-4)로 통합하여 중국 및 CIS 지역 동포에게도 재외동포(F-4) 사증을 발급하고, 방문취업(H-2) 사증의 신규 발급을 중단합니다.',
         summary_en='From 12 February 2026 the compatriot statuses are merged into F-4: compatriots from China and the CIS also receive F-4 visas, and new H-2 visas are no longer issued.')

drop('H-2', 'status_change')
guidance('H-2', 'status_change', state='GENERALLY_NOT_PERMITTED', completeness='SOURCE_ONLY', section='알기쉬운 외국국적동포 업무 매뉴얼 — 3. 방문취업제 체류관리 절차 □ 방문취업 자격으로 변경허가', anchor='다른 체류자격에서 방문취업(H-2) 자격으로 자격변경할 수 없습니다',
         summary_ko='다른 체류자격에서 방문취업(H-2) 자격으로 자격변경할 수 없습니다.', summary_en='No other status can be changed to H-2.')

H2_REPORT_SECTION = '알기쉬운 외국국적동포 업무 매뉴얼 — 3. 방문취업제 체류관리 절차 □ 방문취업 동포는 취업개시 신고를 하여야 합니다'
H2_ATTACH = '특례고용가능확인서 사본, 표준근로계약서 사본, 사업자등록증 사본'


def h2_report_docs():
    return [item('g1h_special_employment_copy', anchor=H2_ATTACH), item('standard_contract_copy', anchor=H2_ATTACH), item('business_reg_copy', anchor=H2_ATTACH),
            item('g1h_h2_report_fax', 'CONDITIONAL_REQUIRED', anchor='방문취업 동포 취업개시 등 신고서 및 외국인등록증 사본', applies_when_ko='팩스로 신고하는 경우', applies_when_en='If reporting by fax')]


H2_CHANNEL_KO = '사전예약 방문, 하이코리아 인터넷 신고(필수 기재사항 입력만으로 가능), 팩스(1577-1346), 등록 대행사를 통한 대행신고'
H2_CHANNEL_EN = 'Office visit by appointment, HiKorea online report (entering the required fields is enough), fax (1577-1346), or a registered agency'
H2_COND_KO = ['신고의무를 위반하면 출입국관리법 제100조제2항에 따라 100만원 이하 과태료 부과대상입니다.',
              '고용노동부에서 전송된 취업개시신고도 인정됩니다.']
H2_COND_EN = ['Failing to report is subject to a fine of up to KRW 1 million under Article 100(2) of the Immigration Act.',
              'An employment-start report transmitted by the Ministry of Employment and Labor is also accepted.']
guidance('H-2', 'workplace_report', section=H2_REPORT_SECTION, anchor='방문취업 허용업종에 최초 취업을 개시한 방문취업 (H-2) 자격 소지자',
         summary_ko='방문취업(H-2) 동포는 허용업종에 처음 취업하거나 근무처를 바꾸면 그날부터 15일 이내에 취업개시(근무처변경) 신고를 해야 합니다. 첨부서류는 특례고용가능확인서 사본, 표준근로계약서 사본, 사업자등록증 사본입니다.',
         summary_en='H-2 compatriots must report within 15 days of first starting work in a permitted industry or changing workplace. Attach copies of the special employment permit confirmation, the standard labor contract and the business registration.',
         timing_ko='최초 취업 개시일 또는 근무처 변경일로부터 15일 이내', timing_en='Within 15 days of starting work or changing workplace',
         channel_ko=H2_CHANNEL_KO, channel_en=H2_CHANNEL_EN, conditions_ko=H2_COND_KO, conditions_en=H2_COND_EN,
         docs=h2_report_docs(), notes_ko=[OFFICER_NOTE_KO], notes_en=[OFFICER_NOTE_EN])
guidance('H-2', 'workplace_change', section=H2_REPORT_SECTION, anchor='근무처를 변경한 경우 ⇒ 근무처를 변경한 날로부터 15일 이내',
         summary_ko='방문취업(H-2) 동포의 근무처 변경은 신고만으로 가능하며, 근무처를 변경한 날로부터 15일 이내에 근무처변경 신고를 해야 합니다. 첨부서류는 특례고용가능확인서 사본, 표준근로계약서 사본, 사업자등록증 사본입니다.',
         summary_en='H-2 compatriots change workplace by report only: file the workplace-change report within 15 days of the change, with copies of the special employment permit confirmation, the standard labor contract and the business registration.',
         timing_ko='근무처를 변경한 날로부터 15일 이내', timing_en='Within 15 days of the change',
         extra_sources=[{'manual': STAY, 'section': '알기쉬운 외국국적동포 업무 매뉴얼 — 2. 방문취업제(H-2) □ 취업절차 간소화', 'anchor': '근무처 변경도 신고만으로 가능'}],
         channel_ko=H2_CHANNEL_KO, channel_en=H2_CHANNEL_EN, conditions_ko=H2_COND_KO, conditions_en=H2_COND_EN,
         docs=h2_report_docs(), notes_ko=[OFFICER_NOTE_KO], notes_en=[OFFICER_NOTE_EN])

# ==========================================================================
# F-4 재외동포 — 체류자격 외 활동허가 (replaces the summary-only rule)
# ==========================================================================
F4_AOS_ANCHOR = '재외동포 통합신청서(별지 제1호서식), 여권 및 사본, 거소신고증, 단순노무 업종 취업사실을 입증할 수 있는 공적서류(건강보험 가입내역, 소득금액증명원 등)*, 근로계약서, 사업자등록증, 수수료'
drop('F-4', 'activities_outside_status')
guidance('F-4', 'activities_outside_status', section='알기쉬운 외국국적동포 업무 매뉴얼 — 4. 재외동포(F-4) 자격부여 제도 세부절차 마. 재외동포 자격의 체류자격 외 활동허가',
         anchor='방문취업(H-2)으로 체류하며 취업개시 신고를 한 사실이 있는 동포는',
         summary_ko='재외동포(F-4)로 바꾼 동포가 과거 방문취업(H-2)으로 취업개시 신고를 한 사업장에서 계속 일하려면 체류자격 외 활동허가를 받을 수 있습니다. 허가기간은 F-4 체류기간 범위에서 근로계약 기간에 따라 부여됩니다.',
         summary_en='Compatriots who changed to F-4 and want to keep working at the workplace they reported under H-2 can get permission for activities outside status, granted for the labor-contract period within their F-4 stay.',
         period_ko='재외동포(F-4) 체류기간 범위 내에서 근로계약 기간에 따라', period_en='Per the labor-contract period, within the F-4 period of stay',
         docs=[item('app_form_dongpo', anchor=F4_AOS_ANCHOR), item('passport_with_copy', anchor=F4_AOS_ANCHOR), item('g1h_geoso_card', anchor=F4_AOS_ANCHOR),
               item('g1h_simple_labor_proof', anchor=F4_AOS_ANCHOR, administrative_information_exemption=True,
                    notes_ko='출입국관리정보시스템(ICRM)으로 확인되는 경우 제출 면제 가능', notes_en='May be waived if it can be checked in the immigration information system (ICRM)'),
               item('labor_contract', anchor=F4_AOS_ANCHOR), item('business_reg', anchor=F4_AOS_ANCHOR), item('fee', anchor=F4_AOS_ANCHOR)],
         notes_ko=[OFFICER_NOTE_KO], notes_en=[OFFICER_NOTE_EN])
