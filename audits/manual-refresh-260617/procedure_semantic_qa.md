# Procedure semantic QA — 2026-06-17 manual refresh follow-up

_Generated 2026-06-19._

## Scope

Semantic quality pass over procedure `summary` text and document arrays (`commonDocs`/`requiredDocs`/`additionalDocs`/`conditionalDocs`) across all 42 status authoring JSONs under `backend/data/visa_authoring/statuses/`.

**Bug class:** the prior auto-extraction from the 2026.6 stay manual concatenated adjacent section headings and rule/eligibility prose into procedure summaries and document arrays, so explanatory sentences and section headers (e.g. `재입국허가1`) rendered as document chips.

**Source of truth:** 2026.6 stay/residence manual `docs/source-manuals/2026-06-17/extracted/full_text/stay_manual_260617.txt` (and visa issuance manual for issuance procedures). No documents were invented; where the manual lists no submitted documents for a procedure, the document list is left empty with a precise note.

## Summary

- Statuses scanned: **42**
- Statuses changed: **19**
- Total change items: **71**

| status | procedure | field | action | cause |
|---|---|---|---|---|
| C-3 | extension | requiredDocs.requiredDocs | removed (prose/heading) → notes/summary | auto-extracted non-document prose / adjacent section heading rendered as a document chip |
| C-3 | extension | requiredDocs.requiredDocs | removed (prose/heading) → notes/summary | auto-extracted non-document prose / adjacent section heading rendered as a document chip |
| C-3 | extension | notes | added note | explanatory rule/restriction relocated from a document array to notes |
| D-1 | reentry | requiredDocs.conditionalDocs | removed (prose/heading) → notes/summary | auto-extracted non-document prose / adjacent section heading rendered as a document chip |
| D-1 | reentry | notes | added note | explanatory rule/restriction relocated from a document array to notes |
| D-2 | reentry | requiredDocs.conditionalDocs | removed (prose/heading) → notes/summary | auto-extracted non-document prose / adjacent section heading rendered as a document chip |
| D-2 | reentry | requiredDocs.conditionalDocs | removed (prose/heading) → notes/summary | auto-extracted non-document prose / adjacent section heading rendered as a document chip |
| D-2 | reentry | notes | added note | explanatory rule/restriction relocated from a document array to notes |
| D-2 | reentry | notes | added note | explanatory rule/restriction relocated from a document array to notes |
| D-2 | extension | requiredDocs.conditionalDocs | removed (prose/heading) → notes/summary | auto-extracted non-document prose / adjacent section heading rendered as a document chip |
| D-2 | extension | requiredDocs.conditionalDocs | removed (prose/heading) → notes/summary | auto-extracted non-document prose / adjacent section heading rendered as a document chip |
| D-2 | extension | notes | added note | explanatory rule/restriction relocated from a document array to notes |
| D-2 | extension | notes | added note | explanatory rule/restriction relocated from a document array to notes |
| D-3 | extension | requiredDocs.requiredDocs | truncated appended bleed | valid document with adjacent section-heading or rule text concatenated by PDF extraction |
| D-3 | extension | notes | added note | explanatory rule/restriction relocated from a document array to notes |
| D-4 | extension | requiredDocs.requiredDocs | truncated appended bleed | valid document with adjacent section-heading or rule text concatenated by PDF extraction |
| D-4 | extension | requiredDocs.requiredDocs | truncated appended bleed | valid document with adjacent section-heading or rule text concatenated by PDF extraction |
| D-4 | extension | notes | added note | explanatory rule/restriction relocated from a document array to notes |
| D-4 | reentry | requiredDocs.conditionalDocs | removed (prose/heading) → notes/summary | auto-extracted non-document prose / adjacent section heading rendered as a document chip |
| D-4 | reentry | notes | added note | explanatory rule/restriction relocated from a document array to notes |
| D-6 | reentry | requiredDocs.conditionalDocs | removed (prose/heading) → notes/summary | auto-extracted non-document prose / adjacent section heading rendered as a document chip |
| D-6 | reentry | notes | added note | explanatory rule/restriction relocated from a document array to notes |
| D-7 | extension | requiredDocs.requiredDocs | removed (prose/heading) → notes/summary | auto-extracted non-document prose / adjacent section heading rendered as a document chip |
| D-7 | extension | requiredDocs.requiredDocs | truncated appended bleed | valid document with adjacent section-heading or rule text concatenated by PDF extraction |
| D-7 | extension | requiredDocs.requiredDocs | truncated appended bleed | valid document with adjacent section-heading or rule text concatenated by PDF extraction |
| D-7 | extension | notes | added note | explanatory rule/restriction relocated from a document array to notes |
| D-7 | reentry | requiredDocs.conditionalDocs | removed (prose/heading) → notes/summary | auto-extracted non-document prose / adjacent section heading rendered as a document chip |
| D-7 | reentry | notes | added note | explanatory rule/restriction relocated from a document array to notes |
| D-8 | extension | requiredDocs.requiredDocs | removed (prose/heading) → notes/summary | auto-extracted non-document prose / adjacent section heading rendered as a document chip |
| D-8 | extension | notes | added note | explanatory rule/restriction relocated from a document array to notes |
| D-8 | reentry | requiredDocs.conditionalDocs | removed (prose/heading) → notes/summary | auto-extracted non-document prose / adjacent section heading rendered as a document chip |
| D-8 | reentry | notes | added note | explanatory rule/restriction relocated from a document array to notes |
| D-9 | extension | requiredDocs.requiredDocs | removed (prose/heading) → notes/summary | auto-extracted non-document prose / adjacent section heading rendered as a document chip |
| D-9 | extension | requiredDocs.requiredDocs | truncated appended bleed | valid document with adjacent section-heading or rule text concatenated by PDF extraction |
| D-9 | extension | notes | added note | explanatory rule/restriction relocated from a document array to notes |
| D-9 | reentry | requiredDocs.conditionalDocs | removed (prose/heading) → notes/summary | auto-extracted non-document prose / adjacent section heading rendered as a document chip |
| D-9 | reentry | notes | added note | explanatory rule/restriction relocated from a document array to notes |
| E-2 | reentry | requiredDocs.conditionalDocs | removed (prose/heading) → notes/summary | auto-extracted non-document prose / adjacent section heading rendered as a document chip |
| E-2 | reentry | notes | added note | explanatory rule/restriction relocated from a document array to notes |
| E-3 | reentry | requiredDocs.conditionalDocs | removed (prose/heading) → notes/summary | auto-extracted non-document prose / adjacent section heading rendered as a document chip |
| E-3 | reentry | notes | added note | explanatory rule/restriction relocated from a document array to notes |
| E-4 | reentry | requiredDocs.conditionalDocs | removed (prose/heading) → notes/summary | auto-extracted non-document prose / adjacent section heading rendered as a document chip |
| E-4 | reentry | notes | added note | explanatory rule/restriction relocated from a document array to notes |
| E-5 | reentry | requiredDocs.conditionalDocs | removed (prose/heading) → notes/summary | auto-extracted non-document prose / adjacent section heading rendered as a document chip |
| E-5 | reentry | notes | added note | explanatory rule/restriction relocated from a document array to notes |
| E-6 | reentry | requiredDocs.conditionalDocs | removed (prose/heading) → notes/summary | auto-extracted non-document prose / adjacent section heading rendered as a document chip |
| E-6 | reentry | notes | added note | explanatory rule/restriction relocated from a document array to notes |
| E-6 | extension | requiredDocs.requiredDocs | truncated appended bleed | valid document with adjacent section-heading or rule text concatenated by PDF extraction |
| E-6 | extension | requiredDocs.requiredDocs | removed (prose/heading) → notes/summary | auto-extracted non-document prose / adjacent section heading rendered as a document chip |
| E-6 | extension | requiredDocs.requiredDocs | removed (prose/heading) → notes/summary | auto-extracted non-document prose / adjacent section heading rendered as a document chip |
| E-6 | extension | notes | added note | explanatory rule/restriction relocated from a document array to notes |
| E-7 | extension | requiredDocs.requiredDocs | truncated appended bleed | valid document with adjacent section-heading or rule text concatenated by PDF extraction |
| E-7 | extension | requiredDocs.requiredDocs | removed (prose/heading) → notes/summary | auto-extracted non-document prose / adjacent section heading rendered as a document chip |
| E-7 | extension | requiredDocs.requiredDocs | removed (prose/heading) → notes/summary | auto-extracted non-document prose / adjacent section heading rendered as a document chip |
| E-7 | extension | requiredDocs.requiredDocs | removed (prose/heading) → notes/summary | auto-extracted non-document prose / adjacent section heading rendered as a document chip |
| E-7 | extension | notes | added note | explanatory rule/restriction relocated from a document array to notes |
| E-8 | extension | requiredDocs.requiredDocs | removed (prose/heading) → notes/summary | auto-extracted non-document prose / adjacent section heading rendered as a document chip |
| E-8 | extension | requiredDocs.requiredDocs | truncated appended bleed | valid document with adjacent section-heading or rule text concatenated by PDF extraction |
| E-8 | extension | requiredDocs.requiredDocs | removed (prose/heading) → notes/summary | auto-extracted non-document prose / adjacent section heading rendered as a document chip |
| E-8 | extension | requiredDocs.requiredDocs | removed (prose/heading) → notes/summary | auto-extracted non-document prose / adjacent section heading rendered as a document chip |
| E-8 | extension | notes | added note | explanatory rule/restriction relocated from a document array to notes |
| E-8 | extension | notes | added note | explanatory rule/restriction relocated from a document array to notes |
| E-8 | extension | notes | added note | explanatory rule/restriction relocated from a document array to notes |
| F-3 | reentry | requiredDocs.conditionalDocs | removed (prose/heading) → notes/summary | auto-extracted non-document prose / adjacent section heading rendered as a document chip |
| F-3 | reentry | notes | added note | explanatory rule/restriction relocated from a document array to notes |
| G-1 | extension | requiredDocs.requiredDocs | removed (prose/heading) → notes/summary | auto-extracted non-document prose / adjacent section heading rendered as a document chip |
| G-1 | extension | notes | added note | explanatory rule/restriction relocated from a document array to notes |
| H-1 | extension | summary | rewrote summary (removed bleed) | procedure summary contained adjacent section heading (cross-procedure bleed) |
| H-1 | extension | requiredDocs.requiredDocs | removed (prose/heading) → notes/summary | auto-extracted non-document prose / adjacent section heading rendered as a document chip |
| H-1 | extension | requiredDocs.requiredDocs | removed (prose/heading) → notes/summary | auto-extracted non-document prose / adjacent section heading rendered as a document chip |
| H-1 | extension | notes | added note | explanatory rule/restriction relocated from a document array to notes |

## Detail (before → after)

### C-3
- **extension.requiredDocs.requiredDocs** — removed (prose/heading) → notes/summary
    - before: `단체관광(C-3-2)은 출국 항공기 부재, 영주·귀화신청 등 부득이한 사유가 있는 경우에 한해 제한적으로 검토`
- **extension.requiredDocs.requiredDocs** — removed (prose/heading) → notes/summary
    - before: `단기방문(C-3)은 입국일로부터 체류기간 90일 범위 내에서만 연장 가능`
- **extension.notes** — added note
    - after: `단체관광(C-3-2)은 출국 항공기 부재, 영주·귀화 신청 등 부득이한 사유가 있는 경우에 한해 제한적으로 연장이 검토됩니다.`

### D-1
- **reentry.requiredDocs.conditionalDocs** — removed (prose/heading) → notes/summary
    - before: `사우디아라비아·이란·리비아 국적자는 복수재입국허가가 제한됩니다(단, 결혼이민(F-6)·유학(D-2)·일반연수(D-4) 국민은 가능).`
- **reentry.notes** — added note
    - after: `사우디아라비아·이란·리비아 국적자는 복수재입국허가가 제한됩니다(단, 결혼이민(F-6)·유학(D-2)·일반연수(D-4) 국민은 가능).`

### D-2
- **reentry.requiredDocs.conditionalDocs** — removed (prose/heading) → notes/summary
    - before: `입국규제 등의 사유로 재입국허가를 받아야 하는 경우 체류지 관할 출입국·외국인관서에서 재입국허가 필요`
- **reentry.requiredDocs.conditionalDocs** — removed (prose/heading) → notes/summary
    - before: `체류기간 만료일이 2년 미만인 경우 잔여 체류기간 범위 내에서 복수재입국허가 부여`
- **reentry.notes** — added note
    - after: `입국규제 등의 사유로 재입국허가를 받아야 하는 경우에는 체류지 관할 출입국·외국인관서에서 재입국허가를 받아야 합니다.`
- **reentry.notes** — added note
    - after: `체류기간 만료일이 2년 미만인 경우 잔여 체류기간 범위 내에서 복수재입국허가가 부여됩니다.`
- **extension.requiredDocs.conditionalDocs** — removed (prose/heading) → notes/summary
    - before: `우수인증대학 및 인증대학 학위과정 재학생으로 전체 평균학점 C학점 이상인 사람은 일부 재정능력 입증서류가 생략될 수 있으나, 장관 고시국가 및 중점관리국가 국민은 예외가 있습니다.`
- **extension.requiredDocs.conditionalDocs** — removed (prose/heading) → notes/summary
    - before: `비자심사강화대학 학위과정 재학생으로 전체 평균 이수학점이 D학점 이하인 경우 심사가 강화될 수 있습니다.`
- **extension.notes** — added note
    - after: `우수인증대학·인증대학 학위과정 재학생으로 전체 평균학점이 C학점 이상인 경우 일부 재정능력 입증서류가 생략될 수 있으나, 장관 고시국가 및 중점관리국가 국민은 예외가 있습니다.`
- **extension.notes** — added note
    - after: `비자심사강화대학 학위과정 재학생으로 전체 평균 이수학점이 D학점 이하인 경우 심사가 강화될 수 있습니다.`

### D-3
- **extension.requiredDocs.requiredDocs** — truncated appended bleed
    - before: `연수기간 연장신청 사유서(별도서식) ‣해외투자기업 기술연수생 등에 대한 사증발급인정서 발급 및 관리에 관한 지침 (제5조) 기술연수생의 연수기간은 원칙적으로 입국한 날로부터 6개월을 초과할 수 없다. 다만, 청(사무소·출장소)장이 추가로 연수가 필요하다고 인정하는 경우 입국한 날부터 2년을 초과하지 않는 한도 내에서 그 연수기간을 연장할 수 있다.`
    - after: `연수기간 연장신청 사유서(별도서식)`
- **extension.notes** — added note
    - after: `연수기간은 「해외투자기업 기술연수생 등에 대한 사증발급인정서 발급 및 관리에 관한 지침」 제5조에 따라 원칙적으로 입국일부터 6개월을 초과할 수 없으나, 청(사무소·출장소)장이 추가 연수가 필요하다고 인정하는 경우 입국일부터 2년을 초과하지 않는 범위에서 연장할 수 있습니다.`

### D-4
- **extension.requiredDocs.requiredDocs** — truncated appended bleed
    - before: `체류지 입증서류(예: 임대차계약서, 거주/숙소 제공 확인서, 체류기간 만료예고 통지우편물, 공공요금 납부영수증, 기숙사비 영수증 또는 기숙사 거주확인서 등. 가족·배우자·지인·고용주 등 타인이 제공하는 주소지에 거주하거나 신청자 명의의 임대차계약서·기숙사 자료만으로 체류지를 입증하기 어려운 경우에는 거주/숙소 제공 확인서와 임대차계약서 또는 부동산등기사항전부증명서(등기부등본) 등 제공자의 주거지 사용권한 입증자료를 준비)2. 기업 맞춤형 인턴십(K-Trainee, D 2K)의 체류기간 연장 제출서류 ※ 인턴기간은 원칙적으로 6개월을`
    - after: `체류지 입증서류(예: 임대차계약서, 거주/숙소 제공 확인서, 체류기간 만료예고 통지우편물, 공공요금 납부영수증, 기숙사비 영수증 또는 기숙사 거주확인서 등. 가족·배우자·지인·고용주 등 타인이 제공하는 주소지에 거주하거나 신청자 명의의 임대차계약서·기숙사 자료만으로 체류지를 입증하기 어려운 경우에는 거주/숙소 제공 확인서와 임대차계약서 또는 부동산등기사항전부증명서(등기부등본) 등 제공자의 주거지 사용권한 입증자료를 준비)`
- **extension.requiredDocs.requiredDocs** — truncated appended bleed
    - before: `기간연장 사유서 및 인턴·연수 활동 계획서3. 고등학교 이하 교육기관 외국인유학생(D-4-3)의 체류기간 연장 제출서류`
    - after: `기간연장 사유서 및 인턴·연수 활동 계획서`
- **extension.notes** — added note
    - after: `기업 맞춤형 인턴십(K-Trainee, D-4-2K)의 인턴기간은 원칙적으로 6개월을 초과할 수 없으나, 추가로 필요하다고 인정되는 경우 입국일부터 1년을 초과하지 않는 범위에서 연장할 수 있습니다.`
- **reentry.requiredDocs.conditionalDocs** — removed (prose/heading) → notes/summary
    - before: `사우디아라비아·이란·리비아 국적자는 복수재입국허가가 제한됩니다(단, 결혼이민(F-6)·유학(D-2)·일반연수(D-4) 국민은 가능).`
- **reentry.notes** — added note
    - after: `사우디아라비아·이란·리비아 국적자는 복수재입국허가가 제한됩니다(단, 결혼이민(F-6)·유학(D-2)·일반연수(D-4) 국민은 가능).`

### D-6
- **reentry.requiredDocs.conditionalDocs** — removed (prose/heading) → notes/summary
    - before: `사우디아라비아·이란·리비아 국적자는 복수재입국허가가 제한됩니다(단, 결혼이민(F-6)·유학(D-2)·일반연수(D-4) 국민은 가능).`
- **reentry.notes** — added note
    - after: `사우디아라비아·이란·리비아 국적자는 복수재입국허가가 제한됩니다(단, 결혼이민(F-6)·유학(D-2)·일반연수(D-4) 국민은 가능).`

### D-7
- **extension.requiredDocs.requiredDocs** — removed (prose/heading) → notes/summary
    - before: `영 별표 1의 16. 주재(D-7)란의 “가”목 해당자`
- **extension.requiredDocs.requiredDocs** — truncated appended bleed
    - before: `체류지 입증서류(예: 임대차계약서, 거주/숙소 제공 확인서, 체류기간 만료예고 통지우편물, 공공요금 납부영수증, 기숙사비 영수증 또는 기숙사 거주확인서 등. 가족·배우자·지인·고용주 등 타인이 제공하는 주소지에 거주하거나 신청자 명의의 임대차계약서·기숙사 자료만으로 체류지를 입증하기 어려운 경우에는 거주/숙소 제공 확인서와 임대차계약서 또는 부동산등기사항전부증명서(등기부등본) 등 제공자의 주거지 사용권한 입증자료를 준비)영 별표 1의 16. 주재(D-7)란의 “나”목 해당자`
    - after: `체류지 입증서류(예: 임대차계약서, 거주/숙소 제공 확인서, 체류기간 만료예고 통지우편물, 공공요금 납부영수증, 기숙사비 영수증 또는 기숙사 거주확인서 등. 가족·배우자·지인·고용주 등 타인이 제공하는 주소지에 거주하거나 신청자 명의의 임대차계약서·기숙사 자료만으로 체류지를 입증하기 어려운 경우에는 거주/숙소 제공 확인서와 임대차계약서 또는 부동산등기사항전부증명서(등기부등본) 등 제공자의 주거지 사용권한 입증자료를 준비)`
- **extension.requiredDocs.requiredDocs** — truncated appended bleed
    - before: `체류지 입증서류(예: 임대차계약서, 거주/숙소 제공 확인서, 체류기간 만료예고 통지우편물, 공공요금 납부영수증, 기숙사비 영수증 또는 기숙사 거주확인서 등. 가족·배우자·지인·고용주 등 타인이 제공하는 주소지에 거주하거나 신청자 명의의 임대차계약서·기숙사 자료만으로 체류지를 입증하기 어려운 경우에는 거주/숙소 제공 확인서와 임대차계약서 또는 부동산등기사항전부증명서(등기부등본) 등 제공자의 주거지 사용권한 입증자료를 준비)외국법자문법률사무소의 구성원, 소속 자문사, 사무직원`
    - after: `체류지 입증서류(예: 임대차계약서, 거주/숙소 제공 확인서, 체류기간 만료예고 통지우편물, 공공요금 납부영수증, 기숙사비 영수증 또는 기숙사 거주확인서 등. 가족·배우자·지인·고용주 등 타인이 제공하는 주소지에 거주하거나 신청자 명의의 임대차계약서·기숙사 자료만으로 체류지를 입증하기 어려운 경우에는 거주/숙소 제공 확인서와 임대차계약서 또는 부동산등기사항전부증명서(등기부등본) 등 제공자의 주거지 사용권한 입증자료를 준비)`
- **extension.notes** — added note
    - after: `주재(D-7)는 외국기업 주재(가목), 내국기업 해외주재(나목), 외국법자문법률사무소 구성원·소속 자문사·사무직원 등 세부 유형별로 제출서류가 구분되며, 유형에 따라 적용 서류가 달라집니다.`
- **reentry.requiredDocs.conditionalDocs** — removed (prose/heading) → notes/summary
    - before: `사우디아라비아·이란·리비아 국적자는 복수재입국허가가 제한됩니다(단, 결혼이민(F-6)·유학(D-2)·일반연수(D-4) 국민은 가능).`
- **reentry.notes** — added note
    - after: `사우디아라비아·이란·리비아 국적자는 복수재입국허가가 제한됩니다(단, 결혼이민(F-6)·유학(D-2)·일반연수(D-4) 국민은 가능).`

### D-8
- **extension.requiredDocs.requiredDocs** — removed (prose/heading) → notes/summary
    - before: `※ 외국인투자기업등록지위를 갖춘 금융지주회사에서 100%출자한 자회사의 필수전문인력인 경우 제출서류`
- **extension.notes** — added note
    - after: `외국인투자기업등록 지위를 갖춘 금융지주회사가 100% 출자한 자회사의 필수전문인력인 경우의 제출서류가 포함되어 있으며, 세부 유형에 따라 적용 서류가 달라질 수 있습니다.`
- **reentry.requiredDocs.conditionalDocs** — removed (prose/heading) → notes/summary
    - before: `사우디아라비아·이란·리비아 국적자는 복수재입국허가가 제한됩니다(단, 결혼이민(F-6)·유학(D-2)·일반연수(D-4) 국민은 가능).`
- **reentry.notes** — added note
    - after: `사우디아라비아·이란·리비아 국적자는 복수재입국허가가 제한됩니다(단, 결혼이민(F-6)·유학(D-2)·일반연수(D-4) 국민은 가능).`

### D-9
- **extension.requiredDocs.requiredDocs** — removed (prose/heading) → notes/summary
    - before: `한국무역협회장 또는 한국무역통계진흥원장44)이 발행하는 “수출입실적증명서”`
- **extension.requiredDocs.requiredDocs** — truncated appended bleed
    - before: `납세실적은 국세청 발급 “소득세 납세사실증명” 제출2. 선박건조·설비제작 감독 또는 수출설비(기계)의 설치·운영·보수 업무를 하려는 경우`
    - after: `납세실적은 국세청 발급 “소득세 납세사실증명” 제출`
- **extension.notes** — added note
    - after: `선박건조·설비제작 감독 또는 수출설비(기계)의 설치·운영·보수 업무를 하려는 경우 등 세부 유형에 따라 제출서류가 달라질 수 있습니다.`
- **reentry.requiredDocs.conditionalDocs** — removed (prose/heading) → notes/summary
    - before: `사우디아라비아·이란·리비아 국적자는 복수재입국허가가 제한됩니다(단, 결혼이민(F-6)·유학(D-2)·일반연수(D-4) 국민은 가능).`
- **reentry.notes** — added note
    - after: `사우디아라비아·이란·리비아 국적자는 복수재입국허가가 제한됩니다(단, 결혼이민(F-6)·유학(D-2)·일반연수(D-4) 국민은 가능).`

### E-2
- **reentry.requiredDocs.conditionalDocs** — removed (prose/heading) → notes/summary
    - before: `사우디아라비아·이란·리비아 국적자는 복수재입국허가가 제한됩니다(단, 결혼이민(F-6)·유학(D-2)·일반연수(D-4) 국민은 가능).`
- **reentry.notes** — added note
    - after: `사우디아라비아·이란·리비아 국적자는 복수재입국허가가 제한됩니다(단, 결혼이민(F-6)·유학(D-2)·일반연수(D-4) 국민은 가능).`

### E-3
- **reentry.requiredDocs.conditionalDocs** — removed (prose/heading) → notes/summary
    - before: `사우디아라비아·이란·리비아 국적자는 복수재입국허가가 제한됩니다(단, 결혼이민(F-6)·유학(D-2)·일반연수(D-4) 국민은 가능).`
- **reentry.notes** — added note
    - after: `사우디아라비아·이란·리비아 국적자는 복수재입국허가가 제한됩니다(단, 결혼이민(F-6)·유학(D-2)·일반연수(D-4) 국민은 가능).`

### E-4
- **reentry.requiredDocs.conditionalDocs** — removed (prose/heading) → notes/summary
    - before: `사우디아라비아·이란·리비아 국적자는 복수재입국허가가 제한됩니다(단, 결혼이민(F-6)·유학(D-2)·일반연수(D-4) 국민은 가능).`
- **reentry.notes** — added note
    - after: `사우디아라비아·이란·리비아 국적자는 복수재입국허가가 제한됩니다(단, 결혼이민(F-6)·유학(D-2)·일반연수(D-4) 국민은 가능).`

### E-5
- **reentry.requiredDocs.conditionalDocs** — removed (prose/heading) → notes/summary
    - before: `사우디아라비아·이란·리비아 국적자는 복수재입국허가가 제한됩니다(단, 결혼이민(F-6)·유학(D-2)·일반연수(D-4) 국민은 가능).`
- **reentry.notes** — added note
    - after: `사우디아라비아·이란·리비아 국적자는 복수재입국허가가 제한됩니다(단, 결혼이민(F-6)·유학(D-2)·일반연수(D-4) 국민은 가능).`

### E-6
- **reentry.requiredDocs.conditionalDocs** — removed (prose/heading) → notes/summary
    - before: `사우디아라비아·이란·리비아 국적자는 복수재입국허가가 제한됩니다(단, 결혼이민(F-6)·유학(D-2)·일반연수(D-4) 국민은 가능).`
- **reentry.notes** — added note
    - after: `사우디아라비아·이란·리비아 국적자는 복수재입국허가가 제한됩니다(단, 결혼이민(F-6)·유학(D-2)·일반연수(D-4) 국민은 가능).`
- **extension.requiredDocs.requiredDocs** — truncated appended bleed
    - before: `고용추천서 또는 공연추천서 ※ 추천서 발행기관: 영상물등급위원회, 문화체육관광부, 방송통신위원회 등`
    - after: `고용추천서 또는 공연추천서`
- **extension.requiredDocs.requiredDocs** — removed (prose/heading) → notes/summary
    - before: `기타 심사에 필요한 자료* (필요 시 1`
- **extension.requiredDocs.requiredDocs** — removed (prose/heading) → notes/summary
    - before: `2종 제출) * 재직증명서, 외국인 고용현황, 근로소득원천징수부 등`
- **extension.notes** — added note
    - after: `고용추천서·공연추천서 발행기관: 영상물등급위원회, 문화체육관광부, 방송통신위원회 등.`

### E-7
- **extension.requiredDocs.requiredDocs** — truncated appended bleed
    - before: `고용주 납부내역증명, 납세증명서, 지방세 납세증명서(정상영업 및 세금체납여부확인)2. 협정상 사증·체류허가 특례적용대상자에 대한 특례사항 규정 가. 한·인도 포괄적경제동반자협정(CEPA): 독립전문가(IP) 적용대상`
    - after: `고용주 납부내역증명, 납세증명서, 지방세 납세증명서(정상영업 및 세금체납여부확인)`
- **extension.requiredDocs.requiredDocs** — removed (prose/heading) → notes/summary
    - before: `국내법인 또는 개인사업자와 서비스공급계약을 체결한 전문가로서의 자격요건을 갖추고 해당 분야에서 1년 이상 경력이 있는 자* * 협정상 양허직종(162개)에서 서비스를 제공하기 위해 ‘서비스공급계약’을 체결한 독립전문가에게만 적용 (고용계약을 체결하고 E-7 허용직종에서 취업하는 전문인력에 대해서는 E-7지침 일반 적용) 사증특례`
- **extension.requiredDocs.requiredDocs** — removed (prose/heading) → notes/summary
    - before: `최대 1년의 범위 내에서 계약기간을 체류기간으로 하는 단수사증발급인정서 발급 (계약기간이 1년이 초과하는 경우에는 1년 부여) 체류특례`
- **extension.requiredDocs.requiredDocs** — removed (prose/heading) → notes/summary
    - before: `체류기간 연장허가,`
- **extension.notes** — added note
    - after: `한·인도 포괄적경제동반자협정(CEPA) 등 협정상 사증·체류 특례 적용대상(독립전문가 등)은 별도 기준이 적용되며, 사증발급·체류 특례 사항은 해당 협정 및 E-7 지침에 따라 별도로 확인해야 합니다.`

### E-8
- **extension.requiredDocs.requiredDocs** — removed (prose/heading) → notes/summary
    - before: `(수수료 면제)`
- **extension.requiredDocs.requiredDocs** — truncated appended bleed
    - before: `거주/숙소 제공 확인서 ※ 고용주의 등기부등본, 임대차계약서 등 추가서류 불요`
    - after: `거주/숙소 제공 확인서`
- **extension.requiredDocs.requiredDocs** — removed (prose/heading) → notes/summary
    - before: `통합신청서 ※ 지방자치단체 방문 시:`
- **extension.requiredDocs.requiredDocs** — removed (prose/heading) → notes/summary
    - before: `출입국·외국인관서 방문 시:`
- **extension.notes** — added note
    - after: `체류기간 연장 추천 단계의 수수료는 면제됩니다.`
- **extension.notes** — added note
    - after: `거주/숙소 제공 확인서 제출 시 고용주의 등기부등본·임대차계약서 등 추가서류는 불요합니다.`
- **extension.notes** — added note
    - after: `계절근로(E-8) 연장은 지방자치단체 방문 절차와 출입국·외국인관서 방문 절차로 구분됩니다.`

### F-3
- **reentry.requiredDocs.conditionalDocs** — removed (prose/heading) → notes/summary
    - before: `사우디아라비아·이란·리비아 국적자는 복수재입국허가가 제한됩니다(단, 결혼이민(F-6)·유학(D-2)·일반연수(D-4) 국민은 가능).`
- **reentry.notes** — added note
    - after: `사우디아라비아·이란·리비아 국적자는 복수재입국허가가 제한됩니다(단, 결혼이민(F-6)·유학(D-2)·일반연수(D-4) 국민은 가능).`

### G-1
- **extension.requiredDocs.requiredDocs** — removed (prose/heading) → notes/summary
    - before: `세부약호별(산업재해·질병치료·소송·임금체불·난민신청 관련 등) 추가 제출서류 및 허가기간은 사안마다 달라 관할 출입국·외국인관서 또는 체류민원 매뉴얼에서 확인 (G-1은 세부약호별로 요건이 상이)`
- **extension.notes** — added note
    - after: `세부약호별(산업재해·질병치료·소송·임금체불·난민신청 관련 등) 추가 제출서류 및 허가기간은 사안마다 달라, 관할 출입국·외국인관서 또는 체류민원 매뉴얼에서 확인해야 합니다(G-1은 세부약호별로 요건이 상이).`

### H-1
- **extension.summary** — rewrote summary (removed bleed)
    - before: `체류기간 연장허가 입국한 날로부터 1년 범위 내에서 연장 - 단, 협정에 따라 미국 1년 6개월, 영국·캐나다는 2년까지 연장 가능 재입국허가1.`
    - after: `입국한 날로부터 1년 범위 내에서 체류기간을 연장하며, 협정에 따라 미국은 1년 6개월, 영국·캐나다는 2년까지 연장할 수 있습니다.`
- **extension.requiredDocs.requiredDocs** — removed (prose/heading) → notes/summary
    - before: `체류기간 연장허가 입국한 날로부터 1년 범위 내에서 연장`
- **extension.requiredDocs.requiredDocs** — removed (prose/heading) → notes/summary
    - before: `단, 협정에 따라 미국 1년 6개월, 영국·캐나다는 2년까지 연장 가능 재입국허가1.`
- **extension.notes** — added note
    - after: `2026.6 체류민원 매뉴얼 관광취업(H-1) 항목은 체류기간 연장 기간 기준만 제시하고 별도 제출서류를 열거하지 않습니다. 일반 체류기간 연장 공통서류(통합신청서·여권·외국인등록증·수수료 등)가 적용되며, 세부 제출서류는 하이코리아(HiKorea)·1345 또는 관할 출입국·외국인관서에서 확인하시기 바랍니다.`

## Reviewed but intentionally kept (legitimate conditional-document guidance)

These conditional entries name a concrete document with a condition (substitution / omission / addition) and were verified as valid document guidance, not prose:

- D-2 statusChange.conditionalDocs — `정부초청장학생은 학력증명서를 … 대체 가능`
- D-2 statusChange.conditionalDocs — `… 한국어 또는 영어 능력 요건 증빙`
- D-2 registration.conditionalDocs — `인증대학 이상은 등록금납입증명서로 대체 가능`
- D-2 partTimeWork/activitiesOutsideStatus.conditionalDocs — `… 해당 증명서 생략 가능`
- F-6 extension.conditionalDocs — `별거·이혼소송 … 해당 입증서류 추가 필요`
- D-4/D-7/E-6 requiredDocs — `체류지 입증서류(예: …)` and `신원보증서 원본(아래 직종에 한해 징구) …` (long but real document names)

## Known caveat — out of scope for this data-quality pass (separate generator/renderer follow-up)

Phase 0 surfaced a **separate, pre-existing, systemic** issue that is distinct from the H-1
source-data bug fixed here:

- **89 procedures** across the 42 statuses carry `summaryHiddenInUi: true` with
  `summaryQuality` of `generated_legacy` (79) or `ocr_blob` (10). Their authoring `summary`
  is `null`; the low-quality/legacy text lives in `_generated.removedSummaries`.
- The build (`scripts/visa/_visa_pipeline_common.py::_rebuild_procedures`) **re-injects** that
  removed text into `visa_data.json` for byte-identical runtime compatibility, and the renderer
  (`index.html`, `renderProcedureSummaryBlock` → `proc.summary`, with a `summary || v[oldText]`
  fallback chain) **does not honor `summaryHiddenInUi`** — so some of these legacy summaries
  still render (as a preview + expandable “상세 보기” block), and a few contain cross-procedure
  bleed (e.g. E-2 extension mixes 체류자격 부여 / 체류자격 변경 text).

This is a **generated-output + renderer-compatibility** matter (per stop condition 2: *“if many
fields are generated and the generation script is the real bug, fix the generator instead”*; and
stop condition 3: avoid broad renderer changes that could surface or hide other content). It is
**not** hand-edited here because:

1. It spans 89 procedures and the legacy text is generated (`_generated.removedSummaries`), not
   human-authored source — hand-editing generated outputs is explicitly discouraged.
2. The correct fix is a contained but cross-cutting change — make the build honor
   `summaryHiddenInUi` (or carry the flag and have the renderer skip hidden summaries, falling back
   to the existing clean `renderProcedureFallbackSummary`) — which should be its own reviewed change
   with its own UI QA, not bundled into this source-data semantic pass.

**Recommended follow-up:** honor `summaryHiddenInUi` end-to-end (build + renderer) so the 89
flagged-low-quality summaries are replaced by the clean key-based fallback summaries already present
in the UI. All **visible** (non-hidden) procedure summaries were verified bleed-free in this pass.
