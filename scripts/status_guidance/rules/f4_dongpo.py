# F-4 재외동포 — 알기쉬운 외국국적동포 업무 매뉴얼 (embedded in both 2026.10 manuals).
# Transcribed from "4. 재외동포(F-4) 자격부여 제도 세부절차" (visa manual pp. 393–394).
# Runs inside author_rules.py (guidance, item, docdefs, drop, VISA, STAY …).

docdefs(
    overseas_crime_record=('해외 범죄경력증명서', 'Overseas criminal record certificate', 'applicant', None),
    dongpo_identity_proof=('외국국적동포임을 증명하는 서류 (가족관계기록사항에 관한 증명서, 제적등본, 호구부, 거민증, 출생증명서 등)', 'Proof of being an ethnic Korean of foreign nationality (family-relation record, removed register, hukou, resident ID, birth certificate, etc.)', 'applicant', None),
    former_national_proof=('본인이 대한민국의 국민이었던 사실을 증명하는 서류 (가족관계기록사항에 관한 증명서, 제적등본 또는 폐쇄등록부 등)', 'Proof that you were a Korean national (family-relation record, removed or closed register, etc.)', 'applicant', None),
    foreign_nationality_acquisition_proof=('외국국적을 취득한 원인 및 연월일을 증명하는 서류', 'Proof of how and when you acquired foreign nationality', 'applicant', None),
    ancestor_former_national_proof=('직계존속이 대한민국의 국민이었던 사실을 증명하는 서류 (가족관계기록사항에 관한 증명서, 제적등본 또는 폐쇄등록부 등)', 'Proof that your parent or grandparent was a Korean national (family-relation record, removed or closed register, etc.)', 'applicant', None),
    lineage_nationality_acquisition_proof=('여권 등 본인과 직계존속의 외국국적 취득원인 및 연월일을 증명하는 서류', 'Passport or other proof of how and when you and your ascendant acquired foreign nationality', 'applicant', None),
    lineal_relation_proof=('직계존비속의 관계임을 증명하는 서류 (출생증명서 등)', 'Proof of the lineal relationship (birth certificate, etc.)', 'applicant', None),
)

F4_VISA_SECTION = '알기쉬운 외국국적동포 업무 매뉴얼 — 4. 재외동포(F-4) 자격부여 제도 세부절차 나. 재외동포(F-4) 자격 사증발급 등 절차'
F4_COMMON_ANCHOR = '공통 제출서류 (사증발급·체류자격변경)'


def f4_common_docs():
    return [
        item('korean_proof_dongpo', anchor='한국어능력 입증서류 제출기준 참조'),
        item('overseas_crime_record', anchor='해외 범죄경력증명서 제출기준 참조'),
        item('dongpo_identity_proof', anchor='제적등본, 호구부, 거민증 및 출생증명서 등으로 외국국적동포임을 증명하는 서류'),
    ]


guidance('F-4', 'visa_issuance', manual=VISA, section=F4_VISA_SECTION, anchor='나. 재외동포(F-4) 자격 사증발급 등 절차',
         covers=['F-4-41', 'F-4-42'],
         summary_ko='재외동포(F-4) 사증은 공통 서류(한국어능력 입증서류, 해외 범죄경력증명서, 외국국적동포임을 증명하는 서류)에 더해, 본인이 국민이었던 사람(F-4-41)인지 그 직계비속(F-4-42)인지에 따라 추가 서류를 냅니다.',
         summary_en='An F-4 visa needs the common documents (Korean-ability proof, overseas criminal record, proof of Korean ethnicity) plus extra documents depending on whether you were a Korean national yourself (F-4-41) or are a descendant of one (F-4-42).',
         docs=f4_common_docs() + [
             item('former_national_proof', 'CONDITIONAL_REQUIRED', anchor='본인이 대한민국의 국민이었던 사실을 증명하는 서류',
                  applies_when_ko='출생으로 대한민국 국적을 가졌다가 외국국적을 취득한 사람 (F-4-41)', applies_when_en='You held Korean nationality by birth and acquired a foreign nationality (F-4-41)'),
             item('foreign_nationality_acquisition_proof', 'CONDITIONAL_REQUIRED', anchor='외국국적을 취득한 원인 및 연월일을 증명하는 서류',
                  applies_when_ko='F-4-41 대상자', applies_when_en='F-4-41 applicants'),
             item('ancestor_former_national_proof', 'CONDITIONAL_REQUIRED', anchor='직계존속이 대한민국의 국민이었던 사실을 증명하는 서류',
                  applies_when_ko='F-4-41 대상자의 직계비속으로 외국국적을 취득한 사람 (F-4-42)', applies_when_en='Descendant of an F-4-41 person who acquired a foreign nationality (F-4-42)'),
             item('lineage_nationality_acquisition_proof', 'CONDITIONAL_REQUIRED', anchor='여권 등 본인과 직계존속의 외국국적 취득원인 및 연월일을 증명하는 서류',
                  applies_when_ko='F-4-42 대상자', applies_when_en='F-4-42 applicants'),
             item('lineal_relation_proof', 'CONDITIONAL_REQUIRED', anchor='직계존비속의 관계임을 증명하는 서류(출생증명서 등)',
                  applies_when_ko='F-4-42 대상자', applies_when_en='F-4-42 applicants'),
         ],
         conditions_ko=["'18.5.1. 이후 처음으로 대한민국 국적을 이탈했거나 상실한 남성은 병역을 마치거나 면제처분을 받지 않았다면 40세가 되는 해의 12월 31일까지 재외동포(F-4) 체류자격을 받을 수 없습니다."], conditions_en=["Men who first renounced or lost Korean nationality on or after 1 May 2018 cannot receive F-4 until 31 December of the year they turn 40 unless they completed or were exempted from military service."],
         notes_ko=['한국어능력 입증서류와 해외 범죄경력증명서는 매뉴얼의 별첨 제출기준에 따라 대상과 면제 여부가 정해집니다.', OFFICER_NOTE_KO],
         notes_en=['Who must submit Korean-ability proof and an overseas criminal record, and who is exempt, follows the annexed criteria in the manual.', OFFICER_NOTE_EN])

# 체류자격 변경: the section lists the full document set (replaces the earlier summary-only rule).
drop('F-4', 'status_change')
guidance('F-4', 'status_change', manual=STAY, section='알기쉬운 외국국적동포 업무 매뉴얼 — 다. 재외동포(F-4) 자격 변경 절차', anchor='대상별 제출서류가 국내에서 발급되거나 출입국정보시스템으로 확인이 가',
         summary_ko='국내에서 재외동포(F-4)로 바꾸려면 대상별 서류가 국내에서 발급되거나 출입국정보시스템으로 확인될 수 있어야 합니다. 통합신청서와 기본 서류에 동포 입증서류, 해외 범죄경력증명서, 한국어능력 입증서류를 함께 내고, 조기적응프로그램을 먼저 이수해야 합니다.',
         summary_en='You can change to F-4 inside Korea only if the documents for your category are issued in Korea or can be checked in the immigration system. Submit the integrated form and basic documents with proof of Korean ethnicity, an overseas criminal record and Korean-ability proof, after completing the early-adaptation program.',
         docs=[
             item('app_form_dongpo', anchor='재외동포 통합신청서(별지 제1호서식), 여권 및 사본, 표준규격사진 1매, 체류지 입증서류, 결핵진단서'),
             item('passport_and_copy', anchor='여권 및 사본, 표준규격사진 1매, 체류지 입증서류, 결핵진단서'),
             item('photo', anchor='표준규격사진 1매, 체류지 입증서류, 결핵진단서'),
             residence(anchor='체류지 입증서류, 결핵진단서'),
             item('tb_cert', anchor='결핵진단서, 조기적응프로그램'),
             item('early_adaptation_cert', anchor='조기적응프로그램* 이수증, 수수료'),
             item('fee', anchor='이수증, 수수료'),
             item('dongpo_identity_proof', anchor='동포임을 입증할 수 있는 서류, 해외 범죄경력증명서'),
             item('overseas_crime_record', anchor='해외 범죄경력증명서(별첨 1)'),
             item('korean_proof_dongpo', anchor='한국어 능력 입증서류(별첨 2)'),
         ],
         conditions_ko=['조기적응프로그램은 자격변경 신청 전에 의무적으로 이수해야 합니다. 국내 초·중·고교 재학·졸업자, 만 6세 이하 또는 만 65세 이상, 장기체류 자격으로 3년 이상 체류한 사람, 이전 이수자, 사회통합프로그램 1단계 이상 이수(중)자, 중증장애인은 면제됩니다.',
                        'CIS 지역 동포가 과거 동포 사증(C-3-8, H-2, F-4)을 받은 적이 있으면 동포 입증자료를 내고 국내에서 변경할 수 있습니다.',
                        "'18.5.1. 이후 처음으로 대한민국 국적을 이탈했거나 상실한 남성은 병역을 마치거나 면제처분을 받지 않았다면 40세가 되는 해의 12월 31일까지 재외동포(F-4) 체류자격을 받을 수 없습니다."],
         conditions_en=['The early-adaptation program must be completed before applying. Exempt: students or graduates of Korean primary/secondary schools, age 6 or under or 65 or over, 3+ years of long-term stay, earlier completers, those in or past level 1 of the social integration program, and people with severe disabilities.',
                        'Compatriots from CIS countries who previously held a compatriot visa (C-3-8, H-2, F-4) can change in Korea by submitting proof of Korean ethnicity.',
                        'Men who first renounced or lost Korean nationality on or after 1 May 2018 cannot receive F-4 until 31 December of the year they turn 40 unless they completed or were exempted from military service.'],
         notes_ko=[OFFICER_NOTE_KO], notes_en=[OFFICER_NOTE_EN])
