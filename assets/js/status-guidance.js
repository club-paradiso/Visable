/* ============================================================================
 * Visable — post-search guidance (procedure-first, September 2026 baseline)
 * ----------------------------------------------------------------------------
 * ANSWER FIRST · CLARIFY ONLY WHEN IT CHANGES THE ANSWER · WHAT TO PREPARE ·
 * COST · WHAT TO DO NEXT · LOCAL DIFFERENCES · OFFICIAL EVIDENCE.
 *
 * Reads data/status-guidance-202609.json (built by scripts/build_status_coverage_manifest.py
 * from scripts/status_guidance/author_rules.py; every document item is anchored
 * to a manual page or to a quoted regulation article) plus
 * data/local-practice-202609.json, and renders above the raw source search:
 *
 *   1. what Visable understood (status · procedure · office, editable)
 *   2. one clarification at a time — only when the answer depends on it
 *   3. Waymaker Quick Answer for question-shaped queries (assets/js/waymaker-quick-answer.js)
 *   4. the procedure answer (status-specific, or the status-independent common rule)
 *   5. documents grouped by requirement level, with the source-backed physical form
 *   6. 비용 / 납부 from the fee registry (never inside the document list)
 *   7. local-office information, layered and labelled, never merged into the baseline
 *   8. next actions, then official evidence (collapsed until requested)
 *
 * Routing: assets/js/search-router.js (VisableSearchRouter) extracts status /
 * procedure / object / office / conditions separately; the procedure registry
 * in the bundle says whether a procedure needs a status at all. A known
 * procedure is never discarded because the query lacks a code.
 *
 * Pure functions (interpret / nextStep / compose / renderModel) are exposed on
 * globalThis.VisableStatusGuidance BEFORE the DOM guard for the Node checks.
 * Fail-closed: no rule → source-only evidence, never a guessed list.
 * ========================================================================== */
(function (root) {
  'use strict';

  var STR = {
    ko: {
      understood: '{status} · {procedure}(으)로 이해했어요', understoodStatusOnly: '{status}(으)로 이해했어요', understoodProcOnly: '{procedure}(으)로 이해했어요',
      understoodOffice: '{office} 기준', edit: '수정', done: '완료', changeStatus: '체류자격 바꾸기', changeProcedure: '절차 바꾸기', searchCode: '코드로 검색',
      askProcedure: '{status}에서 무엇을 하려고 하세요?', askProcedureHint: '절차에 따라 필요한 서류와 조건이 달라요.',
      askWhich: '어떤 일을 하려고 하세요?', askWhichHint: '가장 가까운 것을 골라 주세요.',
      manyTypes: '{status}에는 여러 체류 유형이 있어요. 정확한 안내를 위해 현재 상황을 조금만 확인할게요.',
      twoTypes: '두 가지 유형이 가능해요. 한 가지만 더 확인할게요.',
      unsure: '잘 모르겠어요', back: '이전 질문', answered: '확인한 내용', change: '변경',
      closest: '현재 정보로는 {target} 안내와 가장 가까워 보여요.', exact: '{target} 기준으로 안내해요.', inherited: '{parent} 공통 기준이 적용돼요. 세부유형별 차이는 없어요.',
      commonLead: '체류자격과 관계없이 같은 기준이 적용돼요.', commonLeadWithStatus: '{status}도 같은 공통 기준이 적용돼요.', commonKicker: '공통 절차',
      optionalStatus: '체류자격을 알려주기 (선택)', optionalStatusWhy: '체류자격을 알려주시면 해당되는 추가 서류와 조건을 함께 보여드려요.',
      needStatusTitle: '{procedure}은(는) 체류자격에 따라 서류가 달라요', needStatusLead: '한 가지만 확인할게요.', pickCloser: '조금 더 구체적으로 골라 주세요.',
      unresolvedTitle: '정확한 세부유형을 아직 확인하지 못했어요',
      unresolvedBody: '아래 유형 중 하나에 해당할 수 있어요. 각 유형의 근거를 확인하거나, 외국인등록증의 체류자격란(예: F-1-5)으로 다시 검색해 보세요.',
      candidates: '가능한 유형', sourceOnlyTitle: '구조화된 안내가 아직 없어요', sourceOnlyBody: '이 항목은 공식 원문으로만 확인할 수 있어요. 아래 근거를 열어 확인하세요.',
      notApplicable: '이 절차는 {status}에 해당하지 않아요.', notPermitted: '{status}에서는 이 절차가 원칙적으로 허용되지 않아요.', exceptionOnly: '{status}에서는 예외적인 경우에만 허가돼요.', conditional: '조건에 따라 달라져요.',
      answerTitle: '안내', period: '체류기간', timing: '신청 시기', channel: '신청 방법', filer: '신청 주체', conditions: '확인할 조건',
      docsTitle: '준비할 서류', docsPartial: '현재 확인된 기본 서류', docsClarify: '세부유형을 확인하면 정확한 서류 목록을 보여드릴 수 있어요.', docsSourceOnly: '서류 목록은 원문에서 확인하세요.',
      docsCount: '필수 {n}개', docsCountCond: '조건부 {n}개',
      grpRequired: '필수', grpConditional: '조건부', grpApplicable: '해당자만', grpAlternative: '대체 가능', grpOfficer: '추가 요청 가능', grpAdmin: '생략 가능 · 행정정보 공동이용 동의 시', grpPrev: '생략 가능 · 이미 제출한 경우', grpSource: '원문 언급 · 구조화 전', grpNA: '이번에는 해당 없음', grpLegacy: '기존 소지자만',
      oneOf: '다음 중 하나', role: '준비하는 사람', where: '발급처', validity: '유효기간', apostille: '아포스티유·영사확인 필요', translation: '번역 필요', applies: '적용 조건', notApplies: '생략 조건', notes: '참고', source: '근거', page: '쪽',
      formTitle: '제출 형태', formCopies: '사본 {n}부', formReturned: '돌려받음', formKept: '반환되지 않음',
      formOriginalShown: '원본 제시 · 돌려받음', formOriginalKept: '원본 제출 · 반환되지 않음',
      formReturnUnknown: '원본을 제시만 하는지 제출하는지는 원문에 적혀 있지 않아요. 계속 필요한 원본이면 돌려받는지 창구에서 확인하세요.',
      prepBring: '원본 지참 권장', prepKeep: '원본 지참 · 사본 준비',
      prepBasis: '준비 권장 · 공식 표기 없음',
      prepSection: '제출 형태가 공식 안내에 적힌 서류는 그 표기를 그대로 보여 드려요. 점선으로 표시한 「원본 지참」은 공식 표기가 없는 서류에 대한 준비 권장이에요. 여권·계약서처럼 계속 필요한 원본은 사본도 함께 준비해 두세요.',
      forms: { ORIGINAL_ONLY: '원본', COPY_ONLY: '사본', ORIGINAL_AND_COPY: '원본 + 사본', ORIGINAL_PRESENT_COPY_SUBMIT: '원본 지참 · 사본 제출', CERTIFIED_COPY: '원본대조필 사본', ONE_OF_ORIGINAL_OR_COPY: '원본 또는 사본', ELECTRONIC_DOCUMENT_ACCEPTED: '전자문서 가능', VARIES_BY_ITEM: '항목별로 다름', SOURCE_DOES_NOT_SPECIFY: '원본·사본 표기 없음', NOT_APPLICABLE: '' },
      formBasis: { SOURCE_PHRASE: '원문 표기', REGULATION: '법령 규정', NONE: '' },
      roles: { applicant: '신청인', inviter: '초청인', employer: '고용주', educational_institution: '학교·연수기관', korean_spouse: '한국인 배우자', principal_holder: '주체류자', local_government: '지방자치단체', sponsor: '신원보증인', business_entity: '사업체', ship_owner: '선주·선박회사', agency: '대행기관', medical_institution: '의료기관·유치기관', other_third_party: '제3자' },
      where_labels: { hikorea: '하이코리아·출입국관서 서식', community_center: '주민센터·정부24', bank: '은행', hospital: '의료기관', school: '학교', tax_office: '세무서·홈택스', court: '법원', employment_center: '고용센터', labor_office: '노동관서', kcomwel: '근로복지공단', designated_hospital: '법무부 지정 병원', local_government: '지방자치단체' },
      overlays: '공통 규칙', overlaysMore: '그 밖의 공통 규칙 {n}개', condTitle: '조건과 예외', officer: '심사 과정에서 추가 서류가 요청되거나 일부 서류가 생략될 수 있습니다.',
      feeTitle: '비용 / 납부', feeNone: '수수료 없음', feeNotListed: '수수료 항목이 규정에 없어요', feeConflict: '근거마다 달라요 · 확인 필요', feeFor: '{label}', feeOnline: '온라인 신청 시 {pct}% 감경', feeInstrument: '납부 방식', feeExemptTitle: '면제·감경 조건', feeNotExempt: '면제되지 않는 경우',
      feeVariants: '다른 경우', feeEntryNote: '절차 안내 원문의 수수료 문구', feeNonRefundable: '심사수수료이므로 접수 후 반환되지 않아요.', feeCheck: '확인 필요', feeGks: 'GKS 장학생', feeInvestigated: '확인 결과',
      instruments: { REVENUE_STAMP: '정부수입인지', CASH_OR_CASH_RECEIPT: '현금 또는 현금 납입 증표', CARD: '신용·직불카드', ELECTRONIC_PAYMENT: '전자결제', REVENUE_CERTIFICATE_STAMP: '수입증지' },
      feeReview: { VERIFIED_REGULATION: '시행규칙 기준', MANUAL_EXPLICIT: '공식 안내 명시', CONDITIONAL_NEEDS_REVIEW: '조건부 · 확인 필요', CONFLICT: '근거 불일치 · 확인 필요', NEEDS_REVIEW: '확인 필요', NOT_FOUND: '근거 확인되지 않음' },
      localTitle: '관할 관서 정보', localNational: '전국 기준', localNationalBody: '위 안내는 법령과 법무부 공식 안내를 기준으로 한 전국 공통 기준이에요.', localDiffer: '관할 관서별로 실제 요구 서류나 절차가 조금 다를 수 있어요.', localPick: '내 관서 선택', localNone: '{office}에 대해 확인된 차이 정보가 없어요. 전국 기준을 따르세요.', localHas: '{office} · 최근 확인된 차이 있음',
      localKind: '정보 성격', localChecked: '최근 확인일', localUnchecked: '아직 확인되지 않음', localReports: '제보 {n}건', localBaseline: '전국 기준', localDetail: '자세히', localReport: '실제 방문 내용이 달랐나요?', localNotPolicy: '전국 기준을 바꾸는 정보가 아니에요. 서류는 전국 기준대로 준비하세요.',
      layers: { NATIONAL_OFFICIAL_BASELINE: '전국 공식 기준', OFFICIAL_LOCAL_GUIDANCE: '관서 공식 안내', VERIFIED_LOCAL_PRACTICE: '검토된 실무 정보', REVIEWED_USER_REPORT: '검토된 이용자 제보', UNVERIFIED_USER_REPORT: '확인되지 않은 이용자 제보', CONFLICTING_REPORTS: '제보 간 불일치', STALE_REPORT: '오래된 제보', UNKNOWN: '정보 없음' },
      nextTitle: '다음 할 일', nextDocs: '준비 서류 {n}개 보기', nextReserve: '방문예약 안내', nextForms: '통합신청서 작성', nextCall: '1345 외국인종합안내센터', nextAi: '이어서 질문하기', nextLegacy: '기존 체류자격 카드 보기', nextFull: '전체 안내', nextEvidence: '근거 보기',
      evidenceTitle: '공식 근거', evidenceShow: '근거 보기', evidenceReview: '2026년 9월판 원문은 아직 사람이 한 줄씩 대조 검토하지 않았어요.', evidenceCount: '{n}건', evidenceBasis: '최신 기준일 {date}', evidenceRegulation: '법령', evidenceManual: '공식 안내', open: '본문 펼치기', original: '원문 보기', reviewState: '검토 전 원문', moreManual: '관련 원문 더 보기', lawChecked: '{date} 확인',
      stayManual: '외국인체류 안내매뉴얼', visaManual: '사증발급 안내매뉴얼',
      relatedTitle: '관련 절차', programTitle: '특별 제도', transitionTitle: '체류자격 변경 경로', currentStatus: '현재 체류자격', from: '현재', to: '목표',
      legacyStop: '이 체류자격은 {date}부터 신규 발급이 중단되었어요. 기존 소지자에게만 적용돼요.', abolished: '이 세부약호는 폐지되었어요({date}). {superseded}로 정정된 기준을 확인하세요.',
      loading: '안내를 불러오는 중이에요.', failed: '안내를 불러오지 못했어요. 아래 원문 검색은 그대로 사용할 수 있어요.', retry: '다시 시도',
      unknownCode: '{code}은(는) 2026년 9월 기준 자료에서 확인되지 않는 코드예요. 오타가 아닌지 확인하거나 상위 코드로 검색해 보세요.',
      noStatus: '무엇을 찾으시는지 조금 더 알려주세요', noStatusBody: '하려는 일(예: 외국인등록증 재발급, 주소 변경 신고), 체류자격 코드(예: F-6, D-2-1), 또는 상황(예: 배우자 비자 연장)으로 검색해 보세요.', noStatusTry: '자주 찾는 업무', passportHint: '여권 재발급은 자국 대사관·영사관 업무예요. 새 여권을 받은 뒤에는 15일 이내에 등록사항 변경신고를 해야 해요.',
      confidenceLow: '해석이 확실하지 않아요. 맞지 않으면 수정해 주세요.',
      disclaimer: '공식 자료를 바탕으로 정리한 참고 안내예요. 법률 상담이나 민원 대행이 아니며, 최종 판단은 관할 기관에서 이루어집니다.', disclaimerMore: '안내 기준 보기',
      interpLabel: '검색 해석', wmTitle: '내 상황이 조금 다르다면', wmBody: 'Waymaker에 지금 상황을 설명하면 필요한 절차와 근거를 단계별로 정리해 드려요.', wmCta: 'Waymaker로 이어서 보기',
      disclaimerDetail: ['이 안내는 법무부 출입국·외국인정책본부의 공식 안내자료(사증발급 안내매뉴얼 2026-09-01판, 외국인체류 안내매뉴얼 2026-09-18판)와 출입국관리법·시행령·시행규칙(2026-09-22 확인)을 구조화한 참고 정보이며 법적 효력이 없습니다.', '출입국·외국인청(사무소·출장소)장은 심사를 위해 필요하면 제출서류를 가감할 수 있고, 허가 여부는 심사로 결정됩니다.', '2026년 9월판 안내자료의 원문은 아직 사람이 한 줄씩 대조 검토하지 않았어요. 각 근거의 검토 상태를 함께 표시합니다.', '최종 확인은 관할 출입국·외국인관서, 하이코리아(hikorea.go.kr), 1345 외국인종합안내센터에서 하세요. Visable은 공식 정부 서비스가 아닙니다.'],
      sourceOnlyEvidence: '원문 확인', stateLabel: { SUPPORTED: '안내 가능', CONDITIONAL: '조건부', NOT_APPLICABLE: '해당 없음', GENERALLY_NOT_PERMITTED: '원칙적 불가', EXCEPTION_ONLY: '예외적 허용', LEGACY_ONLY: '기존 소지자', SOURCE_ONLY: '원문 확인', UNVERIFIED: '미확인' },
      exclusions: '변경이 제한되는 경우', exceptions: '예외', transitionDocs: '제출서류',
      programNote: '일반 코드만으로는 판단할 수 없어요. 아래 조건이 추가로 적용돼요.', dims: '확인 항목', variantsTitle: '특례·예외 상황', relatedPrograms: '일부 대상자에게 적용되는 별도 제도:', understoodProgram: '{program}(으)로 이해했어요',
      reasonTitle: '재발급 사유 (선택)', reasonWhy: '사유에 따라 기존 등록증을 함께 내는지가 달라져요.',
      formVaries: '원본·사본 여부는 서류 이름이 아니라 절차별 원문 표기에 따라 달라요. 확인된 예시:', formVariesAsk: '어떤 절차인지 알려주시면 그 절차의 표기를 보여드려요.', formNoMark: '표기 없음',
      localPremise: '관할 관서별 실무 정보는 전국 기준을 바꾸지 않아요. 서류는 전국 기준대로 준비하고, 아래 정보는 참고만 하세요.', localPremiseNone: '{office}에 대해 확인된 차이 정보가 없어요.',
      gksFeeNote: 'GKS(정부초청장학생) 수수료 면제는 절차마다 달라요. {exempt} 반면 {notExempt}',
      gksExemptPart: '체류자격 변경·체류기간 연장·재입국허가는 초청 조건(정부·정부출연기관의 체재비 부담)에 해당할 때만 면제될 수 있어요(시행규칙 제74조 제1항 제2호, 조건부·확인 필요).', gksNotExemptPart: '외국인등록증 발급·재발급 수수료는 면제 대상자도 납부해요.',
    },
    en: {
      understood: 'We read this as {status} · {procedure}', understoodStatusOnly: 'We read this as {status}', understoodProcOnly: 'We read this as {procedure}',
      understoodOffice: 'for {office}', edit: 'Edit', done: 'Done', changeStatus: 'Change status', changeProcedure: 'Change procedure', searchCode: 'Search by code',
      askProcedure: 'What do you want to do with {status}?', askProcedureHint: 'Documents and conditions depend on the procedure.',
      askWhich: 'What do you want to do?', askWhichHint: 'Pick the closest one.',
      manyTypes: '{status} covers several types of stay. A quick check will make the guidance exact.',
      twoTypes: 'Two types are possible. One more question.',
      unsure: "I'm not sure", back: 'Previous question', answered: 'What you told us', change: 'Change',
      closest: 'Your situation looks closest to the {target} guidance.', exact: 'Guidance for {target}.', inherited: 'The common {parent} rule applies; subtypes are not treated differently.',
      commonLead: 'The same rule applies regardless of your status.', commonLeadWithStatus: 'The same common rule applies to {status}.', commonKicker: 'Common procedure',
      optionalStatus: 'Tell us your status (optional)', optionalStatusWhy: 'With your status we can add the documents and conditions that apply to you.',
      needStatusTitle: 'Documents for {procedure} depend on your status', needStatusLead: 'One quick question.', pickCloser: 'Pick the closest one.',
      unresolvedTitle: 'We could not pin down the exact subtype yet',
      unresolvedBody: 'One of the types below may apply. Open the evidence for each, or search again with the status shown on your residence card (e.g. F-1-5).',
      candidates: 'Possible types', sourceOnlyTitle: 'No structured guidance yet', sourceOnlyBody: 'This item is only available as official source text. Open the evidence below.',
      notApplicable: 'This procedure does not apply to {status}.', notPermitted: 'This procedure is generally not permitted for {status}.', exceptionOnly: 'For {status} this is granted only in exceptional cases.', conditional: 'It depends on conditions.',
      answerTitle: 'Guidance', period: 'Period of stay', timing: 'When to apply', channel: 'How to apply', filer: 'Who files', conditions: 'Conditions to check',
      docsTitle: 'Documents to prepare', docsPartial: 'Basic documents confirmed so far', docsClarify: 'Confirm the subtype to see the exact document list.', docsSourceOnly: 'See the source for the document list.',
      docsCount: '{n} required', docsCountCond: '{n} conditional',
      grpRequired: 'Required', grpConditional: 'Conditional', grpApplicable: 'Only if it applies to you', grpAlternative: 'Alternatives accepted', grpOfficer: 'May be requested', grpAdmin: 'May be skipped · with consent to administrative data sharing', grpPrev: 'May be skipped · if already submitted', grpSource: 'Mentioned in the source · not structured yet', grpNA: 'Not needed in your case', grpLegacy: 'Existing holders only',
      oneOf: 'One of', role: 'Prepared by', where: 'Where to get it', validity: 'Validity', apostille: 'Apostille or consular confirmation required', translation: 'Translation required', applies: 'Applies when', notApplies: 'May be omitted when', notes: 'Notes', source: 'Source', page: 'p.',
      formTitle: 'How to submit', formCopies: '{n} copy', formReturned: 'returned to you', formKept: 'not returned',
      formOriginalShown: 'Original shown · returned to you', formOriginalKept: 'Original submitted · not returned',
      formReturnUnknown: 'The source does not say whether the original is only shown or handed in. If you still need it, ask at the counter whether it is returned.',
      prepBring: 'Bring the original', prepKeep: 'Bring the original · prepare a copy',
      prepBasis: 'preparation advice · not stated in the source',
      prepSection: 'Where the official guidance states a submission form, it is shown as written. A dashed “Bring the original” is preparation advice for documents the guidance is silent on. For originals you keep needing — a passport, a contract — prepare a copy as well.',
      forms: { ORIGINAL_ONLY: 'Original', COPY_ONLY: 'Copy', ORIGINAL_AND_COPY: 'Original + copy', ORIGINAL_PRESENT_COPY_SUBMIT: 'Show original · submit copy', CERTIFIED_COPY: 'Certified copy', ONE_OF_ORIGINAL_OR_COPY: 'Original or copy', ELECTRONIC_DOCUMENT_ACCEPTED: 'Electronic document accepted', VARIES_BY_ITEM: 'Varies by item', SOURCE_DOES_NOT_SPECIFY: 'Not specified in the source', NOT_APPLICABLE: '' },
      formBasis: { SOURCE_PHRASE: 'source wording', REGULATION: 'regulation', NONE: '' },
      roles: { applicant: 'Applicant', inviter: 'Inviter', employer: 'Employer', educational_institution: 'School / institution', korean_spouse: 'Korean spouse', principal_holder: 'Principal holder', local_government: 'Local government', sponsor: 'Guarantor', business_entity: 'Business', ship_owner: 'Ship owner', agency: 'Agency', medical_institution: 'Hospital / facilitator', other_third_party: 'Third party' },
      where_labels: { hikorea: 'HiKorea / immigration office form', community_center: 'Community center / Gov24', bank: 'Bank', hospital: 'Hospital', school: 'School', tax_office: 'Tax office / Hometax', court: 'Court', employment_center: 'Employment center', labor_office: 'Labour office', kcomwel: 'KCOMWEL', designated_hospital: 'Designated hospital', local_government: 'Local government' },
      overlays: 'Common rules', overlaysMore: '{n} more common rules', condTitle: 'Conditions and exceptions', officer: 'The examining officer may request additional documents or waive some of them.',
      feeTitle: 'Cost / payment', feeNone: 'No fee', feeNotListed: 'No fee item in the regulation', feeConflict: 'Sources disagree · confirm', feeFor: '{label}', feeOnline: '{pct}% reduction when filed online', feeInstrument: 'How to pay', feeExemptTitle: 'Exemptions and reductions', feeNotExempt: 'Not exempt',
      feeVariants: 'Other cases', feeEntryNote: 'Fee wording in the procedure source', feeNonRefundable: 'An examination fee: not refunded once accepted.', feeCheck: 'Confirm', feeGks: 'GKS scholar', feeInvestigated: 'What we checked',
      instruments: { REVENUE_STAMP: 'Government revenue stamp', CASH_OR_CASH_RECEIPT: 'Cash or cash-payment receipt', CARD: 'Credit / debit card', ELECTRONIC_PAYMENT: 'Electronic payment', REVENUE_CERTIFICATE_STAMP: 'Local revenue stamp' },
      feeReview: { VERIFIED_REGULATION: 'Per the Enforcement Rule', MANUAL_EXPLICIT: 'Stated in official guidance', CONDITIONAL_NEEDS_REVIEW: 'Conditional · confirm', CONFLICT: 'Sources disagree · confirm', NEEDS_REVIEW: 'Confirm', NOT_FOUND: 'No basis found' },
      localTitle: 'Your immigration office', localNational: 'National baseline', localNationalBody: 'The guidance above is the nationwide baseline from the law and official Ministry of Justice guidance.', localDiffer: 'Individual offices may ask for slightly different documents or steps.', localPick: 'Choose your office', localNone: 'No confirmed differences are on record for {office}. Follow the national baseline.', localHas: '{office} · a recently reported difference',
      localKind: 'Type of information', localChecked: 'Last checked', localUnchecked: 'Not yet checked', localReports: '{n} report(s)', localBaseline: 'National baseline', localDetail: 'Details', localReport: 'Was your visit different?', localNotPolicy: 'This does not change the national baseline. Prepare documents per the baseline.',
      layers: { NATIONAL_OFFICIAL_BASELINE: 'National official baseline', OFFICIAL_LOCAL_GUIDANCE: 'Official local guidance', VERIFIED_LOCAL_PRACTICE: 'Verified local practice', REVIEWED_USER_REPORT: 'Reviewed user report', UNVERIFIED_USER_REPORT: 'Unverified user report', CONFLICTING_REPORTS: 'Conflicting reports', STALE_REPORT: 'Stale report', UNKNOWN: 'Unknown' },
      nextTitle: 'Next steps', nextDocs: 'See the {n} documents', nextReserve: 'Visit reservation guide', nextForms: 'Fill in the application form', nextCall: 'Call 1345 (Immigration Contact Center)', nextAi: 'Ask a follow-up', nextLegacy: 'Open the existing status card', nextFull: 'Full guidance', nextEvidence: 'See evidence',
      evidenceTitle: 'Official evidence', evidenceShow: 'Show evidence', evidenceReview: 'The September 2026 guides have not yet been reviewed line by line by a person.', evidenceCount: '{n} sources', evidenceBasis: 'Latest basis {date}', evidenceRegulation: 'Regulation', evidenceManual: 'Official guidance', open: 'Read page text', original: 'Open original', reviewState: 'original text, not yet reviewed', moreManual: 'More source passages', lawChecked: 'checked {date}',
      stayManual: 'Residence manual', visaManual: 'Visa issuance manual',
      relatedTitle: 'Related procedures', programTitle: 'Special program', transitionTitle: 'Change-of-status path', currentStatus: 'Current status', from: 'From', to: 'To',
      legacyStop: 'New issuance of this status stopped on {date}. It applies to existing holders only.', abolished: 'This subcode was abolished ({date}). See the rule now filed under {superseded}.',
      loading: 'Loading guidance…', failed: 'Guidance could not be loaded. The source search below still works.', retry: 'Try again',
      unknownCode: '{code} is not a code found in the September 2026 sources. Check for a typo or search the parent code.',
      noStatus: 'Tell us a little more about what you are looking for', noStatusBody: 'Search with a task (e.g. residence card reissue, address change report), a status code (e.g. F-6, D-2-1) or a situation (e.g. spouse visa extension).', noStatusTry: 'Common tasks', passportHint: 'Passport renewal is done by your own embassy or consulate. After receiving the new passport, report the change within 15 days.',
      confidenceLow: 'This reading is uncertain. Edit it if it is wrong.',
      disclaimer: 'Reference guidance compiled from official sources — not legal advice and not an application agency. The final decision is made by the competent office.', disclaimerMore: 'How this guidance is compiled',
      interpLabel: 'Search interpreted as', wmTitle: 'If your situation is different', wmBody: 'Describe it to Waymaker and it lays out the procedure and the sources step by step.', wmCta: 'Continue in Waymaker',
      disclaimerDetail: ['Compiled from the Ministry of Justice official guides (visa issuance guide 2026-09-01, residence guide 2026-09-18) and the Immigration Act, its Decree and its Rule (read 2026-09-22). It has no legal effect.', 'The head of the immigration office may add or waive documents for examination, and outcomes are decided by examination.', 'The September 2026 guides have not yet been reviewed line by line by a person; each source shows its review state.', 'Confirm with your immigration office, HiKorea (hikorea.go.kr) or the 1345 Immigration Contact Center. Visable is not a government service.'],
      sourceOnlyEvidence: 'Source only', stateLabel: { SUPPORTED: 'Guidance available', CONDITIONAL: 'Conditional', NOT_APPLICABLE: 'Not applicable', GENERALLY_NOT_PERMITTED: 'Generally not permitted', EXCEPTION_ONLY: 'Exception only', LEGACY_ONLY: 'Existing holders', SOURCE_ONLY: 'Source only', UNVERIFIED: 'Unverified' },
      exclusions: 'When the change is restricted', exceptions: 'Exceptions', transitionDocs: 'Documents',
      programNote: 'The ordinary code alone is not enough. These extra conditions apply.', dims: 'What is checked', variantsTitle: 'Special cases', relatedPrograms: 'Separate schemes that apply to some holders:', understoodProgram: 'We read this as {program}',
      reasonTitle: 'Reason for reissue (optional)', reasonWhy: 'The reason decides whether you hand in the existing card.',
      formVaries: 'Whether an original or a copy is needed depends on the procedure\'s own source wording, not on the document name. Confirmed examples:', formVariesAsk: 'Tell us the procedure to see its exact wording.', formNoMark: 'not specified',
      localPremise: 'Office-level practice never changes the national baseline. Prepare documents per the baseline and treat the information below as reference only.', localPremiseNone: 'No confirmed differences are on record for {office}.',
      gksFeeNote: 'GKS (government scholarship) fee exemptions differ by procedure. {exempt} However, {notExempt}',
      gksExemptPart: 'Status change, extension and re-entry permits may be exempt only when the invitation terms apply (Government or a government-funded institute bears living costs; Rule Art. 74(1)(2), conditional and to be confirmed).', gksNotExemptPart: 'the residence card issue and reissue fee is payable even by exempt applicants.',
    }
  };

  function esc(v) { return String(v == null ? '' : v).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; }); }
  function fmt(s, vars) { return String(s || '').replace(/\{(\w+)\}/g, function (_, k) { return vars && vars[k] != null ? vars[k] : ''; }); }
  function tr(lang, key, vars) { var p = STR[lang] || STR.ko; var v = p[key] != null ? p[key] : STR.ko[key]; return typeof v === 'string' ? fmt(v, vars) : v; }
  function L(lang, obj, k) { return lang === 'en' && obj[k + '_en'] ? obj[k + '_en'] : (obj[k + '_ko'] || obj[k + '_en'] || ''); }
  function LL(lang, obj) { return lang === 'en' && obj.en ? obj.en : (obj.ko || obj.en || ''); }
  // Verbatim Korean (source headings, Korean-only data fields) inside English guidance is marked as Korean.
  function koIf(lang, text) { return lang !== 'ko' && /[가-힣]/.test(String(text || '')) ? ' lang="ko"' : ''; }
  function won(n) { return '₩' + String(n).replace(/\B(?=(\d{3})+(?!\d))/g, ','); }

  var PROCEDURE_ORDER = ['extension', 'status_change', 'registration', 'part_time_work', 'activities_outside_status', 'workplace_change', 'reentry', 'registration_info_report', 'residence_report', 'card_reissue', 'status_grant', 'visa_issuance', 'visa_issuance_confirmation', 'electronic_visa', 'workplace_report', 'program_condition_change'];
  var SHORT_STAY = ['B-1', 'B-2', 'C-1', 'C-3', 'C-4'];
  var COMMON_TASKS = [['외국인등록증 재발급', 'Residence card reissue'], ['주소 변경 신고', 'Address change report'], ['체류기간 연장', 'Extension of stay'], ['체류자격 변경', 'Change of status'], ['외국인등록', 'Foreign resident registration']];

  /* --------------------------------------------------------------- codes --- */
  function normalizeCode(raw, codes) {
    var s = String(raw || '').toUpperCase().replace(/[‐‑‒–—−－]/g, '-').replace(/\s+/g, '');
    var m = s.match(/^([A-H])-?(\d{1,2})(?:-?([0-9A-Z]{1,6}))?$/);
    if (!m) return null;
    var parent = m[1] + '-' + m[2];
    if (!m[3]) {
      if (codes[parent]) return parent;
      if (m[2].length === 2) { var split = m[1] + '-' + m[2][0] + '-' + m[2][1]; if (codes[split]) return split; if (codes[m[1] + '-' + m[2][0]]) return { unknownSub: split, parent: m[1] + '-' + m[2][0] }; }
      return null;
    }
    var sub = parent + '-' + m[3];
    if (codes[sub]) return sub;
    var digits = m[2] + m[3];
    for (var i = 1; i < digits.length; i++) {
      var cand = m[1] + '-' + digits.slice(0, i) + '-' + digits.slice(i);
      if (codes[cand]) return cand;
    }
    return codes[parent] ? { unknownSub: sub, parent: parent } : null;
  }
  function parentOf(code) { var p = String(code).split('-'); return p.slice(0, 2).join('-'); }
  function baseTarget(t) { return String(t).split('#')[0]; }
  function isSubcode(code) { return /^[A-H]-\d{1,2}-/.test(code) || code.indexOf('~') > 0; }

  /* ----------------------------------------------------------- interpret --- */
  function interpret(query, bundle, opts) {
    opts = opts || {};
    var q = String(query || '').trim();
    var lower = q.toLowerCase();
    var codes = bundle.codes;
    var out = { query: q, codes: [], unknownCodes: [], aliasCandidates: [], aliasQuestion: null, procedure: null, procedureCandidates: [], preAnswers: {}, confidence: 'LOW', program: null, keywords: [], route: null, office: null, conditions: {}, isQuestion: false, facet: null };
    var codeRe = /([A-Ha-h])\s?-?\s?(\d{1,2})(?:\s?-?\s?([0-9A-Za-z]{1,6}))?(?![A-Za-z0-9])/g;
    var m;
    while ((m = codeRe.exec(q))) {
      var token = m[0].replace(/\s/g, '');
      var n = normalizeCode(token, codes);
      if (!n) continue;
      if (typeof n === 'object') { out.unknownCodes.push(n.unknownSub); if (out.codes.every(function (c) { return c.code !== n.parent; })) out.codes.push({ code: n.parent, exact: false, fromUnknown: n.unknownSub }); continue; }
      if (out.codes.every(function (c) { return c.code !== n; })) out.codes.push({ code: n, exact: isSubcode(n) });
    }
    if (!out.codes.length) {
      var best = null;
      bundle.aliases.forEach(function (a) {
        a.terms.forEach(function (t) {
          var tl = t.toLowerCase();
          if (lower.indexOf(tl) >= 0 && (!best || tl.length > best.term.length)) best = { term: tl, alias: a };
        });
      });
      if (best) {
        var cands = best.alias.candidates;
        if (cands.length === 1 && cands[0].indexOf('PROGRAM:') === 0) { out.program = cands[0].slice(8); }
        else if (cands.length === 1) { out.codes.push({ code: cands[0], exact: isSubcode(cands[0]), fromAlias: best.term }); }
        else { out.aliasCandidates = cands; out.aliasQuestion = best.alias; }
        out.keywords.push(best.term);
      }
    }
    var procHit = null;
    bundle.procedures.forEach(function (p) {
      p.keywords.forEach(function (k) {
        var kl = k.toLowerCase();
        if (lower.indexOf(kl) >= 0 && (!procHit || kl.length > procHit.len)) procHit = { id: p.id, len: kl.length, kw: k };
      });
    });
    if (procHit) { out.procedure = procHit.id; out.keywords.push(procHit.kw); }
    out.codes.forEach(function (c) {
      var fam = bundle.families[parentOf(c.code)];
      if (!fam) return;
      fam.dimensions.forEach(function (d) {
        d.options.forEach(function (o) {
          (o.aliases || []).forEach(function (a) {
            var al = a.toLowerCase();
            if (al.length >= 2 && lower.indexOf(al) >= 0 && !out.preAnswers[d.id]) { out.preAnswers[d.id] = o.id; out.keywords.push(a); }
          });
        });
      });
    });
    // Procedure-first routing: object × action composition, office, conditions and question form.
    if (!opts.noRouter && root.VisableSearchRouter && typeof root.VisableSearchRouter.route === 'function') {
      var r = root.VisableSearchRouter.route(q, bundle, { localPractice: bundle.local_practice || null });
      out.route = r;
      if (r.procedureAmbiguous) { out.procedure = null; out.procedureCandidates = r.procedureCandidates.slice(); }
      else if (r.procedure) out.procedure = r.procedure;
      else if (r.hint === 'passport_reissue') { out.procedure = null; }
      out.hint = r.hint || null; out.hintObject = r.hintObject || null;
      if (!out.codes.length && !out.aliasQuestion && r.aliasQuestion) { out.aliasQuestion = r.aliasQuestion; out.aliasCandidates = r.statusCandidates || r.aliasQuestion.candidates; }
      out.office = r.office; out.conditions = r.conditions || {}; out.isQuestion = r.isQuestion; out.facet = r.facet; out.userProgram = r.userProgram;
    }
    var primary = out.codes[0];
    if (primary && out.procedure) out.confidence = 'HIGH';
    else if (primary) out.confidence = 'MEDIUM';
    else if (out.procedure) { var reg = registryFor(bundle, out.procedure); out.confidence = reg && (reg.context_requirement === 'STATUS_INDEPENDENT' || reg.context_requirement === 'STATUS_OPTIONAL') ? 'HIGH' : 'MEDIUM'; }
    else if (out.aliasCandidates.length || out.program) out.confidence = 'MEDIUM';
    if (primary && !out.procedure) {
      var entry = codes[primary.code] || {};
      out.procedureCandidates = PROCEDURE_ORDER.filter(function (pid) { var st = entry.procedures && entry.procedures[pid]; return st && st.s !== 'UNVERIFIED'; });
    }
    return out;
  }

  /* --------------------------------------------------------------- lookup --- */
  function guidanceFor(bundle, target, procedure) { return bundle.guidance.filter(function (g) { return g.target === target && g.procedure === procedure; }); }
  function targetKey(g) { return g.scenario ? g.target + '#' + g.scenario : g.target; }
  function candidateEntries(bundle, code, procedure) {
    var parent = parentOf(code);
    return bundle.guidance.filter(function (g) {
      if (g.procedure !== procedure || g.target === 'COMMON') return false;
      var base = baseTarget(g.target).split('~')[0];
      if (isSubcode(code)) return base === code || (g.covers || []).indexOf(code) >= 0;
      return base === parent || parentOf(base) === parent;
    });
  }
  function codeState(bundle, code, procedure) { var c = bundle.codes[code]; return c && c.procedures && c.procedures[procedure] ? c.procedures[procedure] : null; }
  function transitionFor(bundle, target, procedure) { var hits = bundle.transitions.filter(function (t) { return t.procedure === procedure && (t.to === target || parentOf(t.to) === target); }); return hits.length ? hits[0] : null; }
  function registryFor(bundle, procedure) { var reg = bundle.procedure_registry || []; for (var i = 0; i < reg.length; i++) if (reg[i].procedure === procedure) return reg[i]; return null; }
  function commonEntry(bundle, procedure) { return bundle.guidance.filter(function (g) { return g.target === 'COMMON' && g.procedure === procedure; })[0] || null; }
  function procedureMeta(bundle, pid) { return bundle.procedures.filter(function (p) { return p.id === pid; })[0] || null; }

  /* ----------------------------------------------------------- resolver ---- */
  function effectiveProcedure(state) { return state.procedure || (state.interp && state.interp.procedure) || null; }
  function effectiveStatus(state) {
    if (state.status) return state.status;
    if (state.interp.codes.length) return state.interp.codes[0].code;
    var a = state.answers.__alias;
    if (a && state.interp.aliasQuestion) {
      var o = state.interp.aliasQuestion.options.filter(function (x) { return x.id === a; })[0];
      if (o) return o.targets[0];
    }
    return null;
  }
  function statusQuestion(bundle, lang, state) {
    var prompt = bundle.status_prompt;
    var picked = state.answers.__status;
    if (picked && picked !== 'unsure') {
      var opt = prompt.options.filter(function (o) { return o.id === picked; })[0];
      if (opt && opt.targets.length > 1) {
        return { kind: 'question', dimension: '__status2', question_ko: tr('ko', 'pickCloser'), question_en: tr('en', 'pickCloser'),
          options: opt.targets.map(function (c) { var info = bundle.codes[c] || {}; return { id: c, ko: c + ' ' + (info.name_ko || ''), en: c + ' ' + (info.name_en || info.name_ko || ''), targets: [c] }; }), allowUnsure: true, why: 'status' };
      }
    }
    return { kind: 'question', dimension: '__status', question_ko: prompt.question_ko, question_en: prompt.question_en, hint_ko: prompt.hint_ko, hint_en: prompt.hint_en, options: prompt.options, allowUnsure: true, why: 'status', showCodeForm: true };
  }
  function procedureStep(bundle, state, procedure, status, reg, entry) {
    var interp = state.interp;
    var reason = state.answers.reissue_reason || (interp.conditions && interp.conditions.reissue_reason) || null;
    return { kind: 'procedure', status: status, procedure: procedure, entries: [entry], target: 'COMMON', common: true, contextRequirement: reg.context_requirement,
      optionalStatus: reg.context_requirement === 'STATUS_OPTIONAL' && !status, reasonDim: procedure === 'card_reissue' ? bundle.reissue_reason : null, reason: reason, confidence: 'HIGH', answered: [], variants: [] };
  }

  function nextStep(state, bundle) {
    var interp = state.interp;
    var answers = state.answers || {};
    if (interp.program && !interp.codes.length && !state.status) {
      return { kind: 'program', program: bundle.programs.filter(function (p) { return p.id === interp.program; })[0] };
    }
    var procedure = effectiveProcedure(state);
    var reg = procedure ? registryFor(bundle, procedure) : null;
    var statusFree = reg && (reg.context_requirement === 'STATUS_INDEPENDENT' || reg.context_requirement === 'STATUS_OPTIONAL');
    // 0. alias ambiguity → which status? (skipped for status-independent procedures unless the user asked to refine)
    if (!interp.codes.length && !state.status && interp.aliasQuestion && !answers.__alias && !(statusFree && !state.askStatus)) {
      var aq = interp.aliasQuestion;
      return { kind: 'question', dimension: '__alias', question_ko: aq.question_ko, question_en: aq.question_en, options: aq.options, allowUnsure: true, unsure_ko: null, unsure_en: null, why: 'status' };
    }
    if (!interp.codes.length && !state.status && interp.aliasQuestion && answers.__alias === 'unsure' && !statusFree) {
      return { kind: 'unresolved', reason: 'status', candidates: interp.aliasCandidates.map(function (c) { return { target: c }; }) };
    }
    var status = effectiveStatus(state);
    if (!status) {
      // Procedure-first: a known procedure is served from its context requirement, never discarded.
      if (procedure && statusFree && !state.askStatus) {
        var common = commonEntry(bundle, procedure);
        if (common) return procedureStep(bundle, state, procedure, null, reg, common);
      }
      if (procedure && reg) {
        if (answers.__status === 'unsure' && statusFree) { var c2 = commonEntry(bundle, procedure); if (c2) return procedureStep(bundle, state, procedure, null, reg, c2); }
        var sq = statusQuestion(bundle, state.lang, state);
        sq.kind = 'need-status'; sq.procedure = procedure; sq.optional = !!statusFree; sq.registry = reg;
        return sq;
      }
      if (!procedure && interp.procedureCandidates && interp.procedureCandidates.length > 1 && !interp.codes.length) {
        return { kind: 'question', dimension: '__procedure', question_ko: tr('ko', 'askWhich'), question_en: tr('en', 'askWhich'), hint_ko: tr('ko', 'askWhichHint'), hint_en: tr('en', 'askWhichHint'),
          options: interp.procedureCandidates.map(function (pid) { var p = procedureMeta(bundle, pid); return { id: pid, ko: p.ko, en: p.en, targets: [pid] }; }), allowUnsure: false, why: 'procedure' };
      }
      return { kind: 'no-status', hint: interp.hint || null, hintObject: interp.hintObject || null, office: interp.office || null };
    }
    var codeInfo = bundle.codes[status] || {};
    // 1. procedure unknown → ask (options = procedures with a known state)
    if (!procedure) {
      var opts = PROCEDURE_ORDER.filter(function (pid) { var st = codeInfo.procedures && codeInfo.procedures[pid]; return st && st.s !== 'UNVERIFIED' && st.s !== 'NOT_APPLICABLE'; });
      if (!opts.length) opts = ['extension', 'status_change', 'registration'];
      return { kind: 'question', dimension: '__procedure', question_ko: tr('ko', 'askProcedure', { status: status }), question_en: tr('en', 'askProcedure', { status: status }), hint_ko: tr('ko', 'askProcedureHint'), hint_en: tr('en', 'askProcedureHint'),
        options: opts.map(function (pid) { var p = procedureMeta(bundle, pid); var st = codeInfo.procedures ? codeInfo.procedures[pid] : null; return { id: pid, ko: p.ko, en: p.en, targets: [pid], state: st ? st.s : null }; }), allowUnsure: false, why: 'procedure' };
    }
    // 2. status change into a target with a transition rule → current status matters
    var transition = procedure === 'status_change' ? transitionFor(bundle, status, procedure) : null;
    if (transition && transition.exclusions && transition.exclusions.length && !answers.current_status) {
      var cq = bundle.current_status_question;
      return { kind: 'question', dimension: 'current_status', question_ko: cq.question_ko, question_en: cq.question_en, options: cq.options, allowUnsure: true, unsure_ko: cq.unsure_ko, unsure_en: cq.unsure_en, why: 'transition' };
    }
    // 3. candidates for the resolved code + procedure
    var exact = isSubcode(status);
    var candidates = candidateEntries(bundle, status, procedure);
    var parent = parentOf(status);
    var fam = bundle.families[parent];
    var dims = fam ? fam.dimensions.filter(function (d) { return !d.procedures || d.procedures.indexOf(procedure) >= 0; }) : [];
    var inherited = false;
    if (exact && !candidates.length && inherits(bundle, status, procedure)) {
      candidates = bundle.guidance.filter(function (g) { return g.procedure === procedure && g.target === parent; });
      inherited = !!candidates.length;
    }
    // 3b. no status-specific rule but a common rule exists → the common rule applies to this status too
    if (!candidates.length && reg && reg.common_target) {
      var ce = commonEntry(bundle, procedure);
      var st0 = codeState(bundle, status, procedure) || codeState(bundle, parent, procedure);
      if (ce && !(st0 && (st0.s === 'NOT_APPLICABLE' || st0.s === 'GENERALLY_NOT_PERMITTED'))) return procedureStep(bundle, state, procedure, status, reg, ce);
    }
    var remaining = candidates.slice();
    var answeredDims = [];
    var chosenCode = null;
    var unsureCount = 0;
    function dimCoverage(d, pool) { return pool.filter(function (g) { return d.options.some(function (o) { return optionMatches(bundle, d, o, g, procedure); }); }).length; }
    dims.forEach(function (d) {
      var a = answers[d.id];
      if (!a) return;
      if (a === 'unsure') { unsureCount += 1; return; }
      var opt = d.options.filter(function (o) { return o.id === a; })[0];
      if (!opt) return;
      if (!dimCoverage(d, remaining)) return;
      answeredDims.push({ dimension: d, option: opt });
      remaining = remaining.filter(function (g) { return optionMatches(bundle, d, opt, g, procedure); });
      if (opt.targets.length === 1 && opt.targets[0].indexOf('#') < 0 && opt.targets[0].indexOf('~') < 0) chosenCode = opt.targets[0];
    });
    if (state.variant) { var v = remaining.filter(function (g) { return targetKey(g) === state.variant; }); if (v.length) remaining = v; }
    var distinct = {};
    remaining.forEach(function (g) { distinct[targetKey(g)] = true; });
    var distinctCount = Object.keys(distinct).length;
    if (distinctCount > 1) {
      for (var i = 0; i < dims.length; i++) {
        var d = dims[i];
        if (answers[d.id]) continue;
        if (interp.preAnswers && interp.preAnswers[d.id]) { answers[d.id] = interp.preAnswers[d.id]; return nextStep(state, bundle); }
        if (unsureCount && dimCoverage(d, remaining) < remaining.length) continue;
        var buckets = {};
        d.options.forEach(function (o) { var hits = remaining.filter(function (g) { return optionMatches(bundle, d, o, g, procedure); }); if (hits.length) buckets[o.id] = hits.map(targetKey).sort().join('|'); });
        var keys = Object.keys(buckets);
        var outcomes = {};
        keys.forEach(function (k) { outcomes[buckets[k]] = true; });
        var splits = Object.keys(outcomes).length >= 2 || (keys.length >= 1 && keys.some(function (k) { return buckets[k].split('|').length < distinctCount; }));
        if (splits) {
          return { kind: 'question', dimension: d.id, question_ko: d.question_ko, question_en: d.question_en, options: d.options, allowUnsure: true, unsure_ko: d.unsure_ko, unsure_en: d.unsure_en, why: 'subtype', remaining: distinctCount, answered: answeredDims };
        }
      }
    }
    if (!remaining.length) {
      var st = codeState(bundle, chosenCode || status, procedure) || codeState(bundle, status, procedure) || codeState(bundle, parent, procedure);
      return { kind: 'source-only', status: chosenCode || status, procedure: procedure, state: st ? st.s : 'UNVERIFIED', page: st ? st.p : null, manual: st ? st.m : null, candidates: candidates, answered: answeredDims, transition: transition };
    }
    var uniq = []; var seen = {};
    remaining.forEach(function (g) { var k = targetKey(g); if (!seen[k]) { seen[k] = true; uniq.push(g); } });
    var baseEntries = uniq.filter(function (g) { return !g.scenario; });
    if (uniq.length > 1 && baseEntries.length === 1 && uniq.every(function (g) { return g.target === baseEntries[0].target; })) {
      var main = baseEntries[0];
      return { kind: 'resolved', status: status, procedure: procedure, entries: [main], target: main.target, scenario: null, inherited: inherited || (chosenCode && chosenCode !== main.target), displayCode: chosenCode || (inherited ? status : main.target.split('~')[0]), exact: exact, answered: answeredDims, transition: transition, variants: uniq.filter(function (g) { return g !== main; }), confidence: exact || chosenCode ? 'HIGH' : 'MEDIUM' };
    }
    if (uniq.length > 1) return { kind: 'unresolved', reason: 'subtype', status: status, procedure: procedure, candidates: uniq, answered: answeredDims, transition: transition };
    var entry = uniq[0];
    var covered = exact && entry.target.split('~')[0] !== status && (entry.covers || []).indexOf(status) >= 0;
    var displayCode = chosenCode && chosenCode !== entry.target.split('~')[0] ? chosenCode : (inherited || covered ? status : entry.target.split('~')[0]);
    return { kind: 'resolved', status: status, procedure: procedure, entries: [entry], target: entry.target, scenario: entry.scenario, inherited: inherited || covered || (!!chosenCode && chosenCode !== entry.target.split('~')[0]), displayCode: displayCode, exact: exact, answered: answeredDims, transition: transition, variants: [], confidence: (exact || !dims.length || chosenCode) ? 'HIGH' : 'MEDIUM' };
  }

  function inherits(bundle, code, procedure) { var c = bundle.codes[code]; var st = c && c.procedures && c.procedures[procedure]; return !!(st && st.i); }
  function scenarioBases(dim) {
    if (dim.__sb) return dim.__sb;
    var s = {};
    dim.options.forEach(function (o) { o.targets.forEach(function (t) { if (t.indexOf('#') > 0) s[baseTarget(t)] = true; }); });
    dim.__sb = s;
    return s;
  }
  function optionMatches(bundle, dim, option, g, procedure) {
    var bases = scenarioBases(dim);
    var key = targetKey(g);
    return option.targets.some(function (t) {
      if (t.indexOf('#') > 0) return key === t;
      if (t === key) return true;
      if (t === g.target) return !(g.scenario && bases[t]);
      if (parentOf(t) === g.target && inherits(bundle, t, procedure)) return true;
      return false;
    });
  }

  /* --------------------------------------------------------------- compose -- */
  // Requirement groups, in reading order: 필수 · 조건부 · 해당자만 · 대체 가능 · 생략 가능 · 추가 요청 가능.
  var GROUP_OF = { REQUIRED_BASELINE: 'required', CONDITIONAL_REQUIRED: 'conditional', ADDITIONAL_IF_APPLICABLE: 'applicable', ALTERNATIVE_DOCUMENT: 'alternative', MAY_BE_REQUESTED_BY_OFFICER: 'officer', ADMIN_INFO_CHECKABLE: 'admin', PREVIOUSLY_SUBMITTED_MAY_BE_OMITTED: 'prev', SOURCE_MENTIONS_BUT_NOT_STRUCTURED: 'source', NOT_APPLICABLE: 'na', LEGACY_ONLY: 'legacy' };
  var GROUP_ORDER = ['required', 'conditional', 'applicable', 'alternative', 'admin', 'prev', 'officer', 'source', 'legacy', 'na'];
  var GROUP_LABEL = { required: 'grpRequired', conditional: 'grpConditional', applicable: 'grpApplicable', alternative: 'grpAlternative', admin: 'grpAdmin', prev: 'grpPrev', officer: 'grpOfficer', source: 'grpSource', legacy: 'grpLegacy', na: 'grpNA' };

  // Fees are never documents: `fee` items are lifted out of the list and kept as fee evidence.
  function groupDocuments(entry, context) {
    var groups = {};
    var reason = context && context.reason;
    (entry.documents || []).forEach(function (d) {
      if (d.ref === 'fee') return;
      var g = GROUP_OF[d.requirement_level] || 'source';
      if (d.administrative_information_exemption && g === 'required') d.adminNote = true;
      // Card-reissue reason: the existing card is required unless the card was lost (시행령 제42조 제2항).
      if (reason && d.ref === 'arc_existing_original') g = reason === 'lost' ? 'na' : 'required';
      (groups[g] = groups[g] || []).push(d);
    });
    return GROUP_ORDER.filter(function (g) { return groups[g]; }).map(function (g) { return { key: g, labelKey: GROUP_LABEL[g], items: groups[g] }; });
  }
  function feeEvidence(entry) { return (entry && entry.documents || []).filter(function (d) { return d.ref === 'fee'; }).map(function (d) { return d.source; }); }
  /* Common rules are useful but must not bury a procedure answer. Each applicable
   * overlay is placed in one tier:
   *   critical   — changes the outcome of this procedure now (presence in Korea,
   *                the passport caps the period, a rule tied to a document on the list);
   *   contextual — triggered by a document on this list or scoped to this status family;
   *   reference  — true in general, not triggered here: kept behind a disclosure.
   * The triggers only read the composed document list; no rule text is changed. */
  var OVERLAY_TRIGGERS = {
    sealed_medical_docs: function (docs) { return docs.some(function (d) { return /건강진단|마약|신체검사|진단서/.test(d.name_ko || '') || /medical (?:certificate|examination|check)|health (?:check|certificate|examination)|drug test/i.test(d.name_en || ''); }); },
    foreign_doc_apostille: function (docs) { return docs.some(function (d) { return d.apostille_required || d.translation_required; }); },
    admin_info_sharing: function (docs) { return docs.some(function (d) { return d.administrative_information_exemption || d.requirement_level === 'ADMIN_INFO_CHECKABLE'; }); },
    previously_submitted_omitted: function (docs) { return docs.some(function (d) { return d.requirement_level === 'PREVIOUSLY_SUBMITTED_MAY_BE_OMITTED'; }); },
    domestic_doc_validity_3m: function (docs) { return docs.some(function (d) { return ['community_center', 'tax_office', 'court', 'bank', 'local_government'].indexOf(d.where_to_obtain) >= 0; }); }
  };
  function overlayTier(o, docs) {
    var s = o.scope || {};
    if (s.requires_doc || o.kind === 'presence' || o.kind === 'period') return 'critical';
    if (OVERLAY_TRIGGERS[o.id]) return OVERLAY_TRIGGERS[o.id](docs) ? 'contextual' : 'reference';
    // scoped to this status family (e.g. the job / income report for work statuses)
    if (s.include_parents) return 'contextual';
    return 'reference';
  }
  function tierOverlays(overlays, entry) {
    var docs = (entry && entry.documents) || [];
    var out = { critical: [], contextual: [], reference: [] };
    (overlays || []).forEach(function (o) { out[overlayTier(o, docs)].push(o); });
    return out;
  }
  /* Two notes that say the same thing in different registers (합니다체 / 해요체,
   * trailing punctuation, spacing) are one note. */
  function noteKey(text) {
    return String(text || '').toLowerCase().replace(/[\s.,·:;!?"'“”‘’()\[\]\-–—]/g, '')
      .replace(/(습니다|합니다|됩니다|입니다|어요|아요|해요|돼요|에요|예요|이에요|요|다)$/, '');
  }
  function words(text) { return String(text || '').toLowerCase().replace(/[^a-z0-9가-힣\s]/g, ' ').split(/\s+/).filter(function (w) { return w.length > 1; }); }
  function bigrams(key) { var out = {}; for (var i = 0; i < key.length - 1; i++) out[key.slice(i, i + 2)] = true; return out; }
  function sameNote(a, b) {
    var ka = noteKey(a), kb = noteKey(b);
    if (!ka || !kb) return false;
    if (ka === kb) return true;
    // one sentence restating the other with a few extra words ("once accepted" / "once the application is accepted")
    var wa = words(a), wb = words(b);
    var small = wa.length <= wb.length ? wa : wb, big = wa.length <= wb.length ? wb : wa;
    if (small.length >= 4 && small.every(function (w) { return big.indexOf(w) >= 0; })) return true;
    var ba = bigrams(ka), bb = bigrams(kb), na = Object.keys(ba).length, nb = Object.keys(bb).length, shared = 0;
    Object.keys(ba).forEach(function (g) { if (bb[g]) shared += 1; });
    return na + nb > 0 && (2 * shared) / (na + nb) >= 0.85;
  }
  function uniqueNotes(list) {
    var out = [];
    (list || []).forEach(function (n) { if (n && !out.some(function (m) { return sameNote(m, n); })) out.push(n); });
    return out;
  }
  function applicableOverlays(bundle, status, procedure, entry) {
    var parent = status ? parentOf(status) : null;
    var docRefs = {};
    (entry && entry.documents || []).forEach(function (d) { docRefs[d.ref] = true; });
    var domain = ['visa_issuance', 'visa_issuance_confirmation', 'electronic_visa'].indexOf(procedure) >= 0 ? 'visa' : 'stay';
    return bundle.overlays.filter(function (o) {
      var s = o.scope || {};
      if (s.domains && s.domains.indexOf(domain) < 0) return false;
      if (s.procedures && s.procedures.indexOf(procedure) < 0) return false;
      if (s.exclude_codes && status && (s.exclude_codes.indexOf(status) >= 0 || s.exclude_codes.indexOf(parent) >= 0)) return false;
      if (s.include_parents && (!parent || s.include_parents.indexOf(parent) < 0)) return false;
      if (s.requires_doc && !docRefs[s.requires_doc]) return false;
      if (o.kind === 'discretion') return false;  // rendered once as the persistent officer note
      if (o.id === 'fee_table' || o.id === 'fees_non_refundable') return false; // fees live in the fee section
      return true;
    });
  }
  // Fee registry lookup: the most specific row for (procedure, status, target); others are shown as "other cases".
  function feesFor(bundle, procedure, status, targetStatus) {
    var rows = (bundle.fees || []).filter(function (f) { return f.procedure === procedure; });
    if (!rows.length) return null;
    var parent = status ? parentOf(status) : null;
    var tparent = targetStatus ? parentOf(targetStatus) : null;
    function match(f) {
      var s = f.scope;
      if (!s) return 'general';
      if (s.parents && parent) return s.parents.indexOf(parent) >= 0 ? 'scoped' : 'no';
      if (s.target_parents && tparent) return s.target_parents.indexOf(tparent) >= 0 ? 'scoped' : 'no';
      return 'unknown';
    }
    var scoped = rows.filter(function (f) { return match(f) === 'scoped'; });
    var general = rows.filter(function (f) { return !f.scope; });
    var primary = scoped.length ? scoped : (general.length ? general : rows);
    var variants = rows.filter(function (f) { return primary.indexOf(f) < 0 && match(f) !== 'no'; });
    return { primary: primary, variants: variants, resolvedByStatus: !!scoped.length, all: rows };
  }
  function exemptionApplies(ex, status, targetStatus, userProgram) {
    var s = ex.scope || {};
    if (s.parents && status && s.parents.indexOf(parentOf(status)) < 0) return false;
    if (s.target_parents && targetStatus && s.target_parents.indexOf(parentOf(targetStatus)) < 0) return false;
    return true;
  }
  function evidenceFor(bundle, step, entries, fees) {
    var list = [];
    var seen = {};
    function pushManual(manual, page, section, kind) {
      if (!page || !manual) return;
      var k = manual + ':' + page;
      if (seen[k]) return; seen[k] = true;
      list.push({ type: 'manual', manual: manual, page: page, section: section, kind: kind });
    }
    function pushLaw(id, claim) {
      if (!id || !bundle.law_sources || !bundle.law_sources[id]) return;
      var k = 'law:' + id;
      if (seen[k]) { if (claim) seen[k].claims.push(claim); return; }
      var ls = bundle.law_sources[id];
      var ev = { type: 'regulation', id: id, law: ls, claims: claim ? [claim] : [] };
      seen[k] = ev; list.push(ev);
    }
    (entries || []).forEach(function (e) {
      pushManual(e.source.manual, e.source.pdf_page, e.source.section, 'guidance');
      (e.law_sources || []).forEach(function (id) { pushLaw(id, e.source.section); });
      (e.documents || []).forEach(function (d) { if (d.source && d.source.law) pushLaw(d.source.law, d.name_ko); if (d.source && d.source.type === 'manual' && d.source.pdf_page) pushManual(e.source.manual, d.source.pdf_page, e.source.section, 'document'); });
    });
    if (step.transition) { pushManual(step.transition.manual, step.transition.pdf_page, step.transition.from_allowed_ko ? tr('ko', 'transitionTitle') : '', 'transition'); (step.transition.exclusions || []).forEach(function (ex) { pushManual(step.transition.manual, ex.pdf_page, ex.ko, 'exclusion'); }); }
    if (step.page) pushManual(step.manual === 'visa' ? 'visa_manual_2026_09_01' : 'stay_manual_2026_09_18', step.page, '', 'state');
    (step.candidates || []).forEach(function (c) { if (c.source) pushManual(c.source.manual, c.source.pdf_page, c.source.section, 'candidate'); });
    if (fees) {
      fees.primary.concat(fees.variants).forEach(function (f) {
        pushLaw(f.law, f.label_ko); if (f.payment_law) pushLaw(f.payment_law, tr('ko', 'feeInstrument'));
        if (f.pdf_page) pushManual(f.manual, f.pdf_page, f.label_ko, 'fee');
        (f.exemptions || []).forEach(function (ex) { if (ex.law) pushLaw(ex.law, ex.condition_ko); if (ex.pdf_page) pushManual(ex.manual || f.manual, ex.pdf_page, ex.condition_ko, 'fee'); });
        if (f.online_reduction && f.online_reduction.law) pushLaw(f.online_reduction.law, f.online_reduction.quote_ko);
      });
    }
    return list;
  }
  function manualMeta(bundle, manualId) {
    var meta = bundle.sources[manualId] || {};
    return { id: manualId, title_ko: meta.title_ko, title_en: meta.title_en, date: meta.date, edition: meta.edition, file: meta.pdf, corpusId: meta.corpus_source_id, review: meta.review_state };
  }
  function latestBasisDate(evidence) {
    var dates = evidence.map(function (e) { return e.type === 'regulation' ? (e.law.effective || '') : (e.date || ''); }).filter(Boolean).sort();
    return dates.length ? dates[dates.length - 1] : '';
  }
  function localPracticeFor(bundle, state, procedure, status) {
    var lp = bundle.local_practice;
    var officeId = state.office || (state.interp.office && state.interp.office.id) || null;
    if (!lp) return { available: false, office: null, officeId: officeId, variations: [], offices: [] };
    var office = officeId ? (lp.offices || []).filter(function (o) { return o.id === officeId; })[0] || null : null;
    var parent = status ? parentOf(status) : null;
    var variations = (lp.variations || []).filter(function (v) {
      if (officeId && v.office !== officeId) return false;
      if (procedure && v.procedure !== procedure) return false;
      if (v.status && status && !(v.status === status || parentOf(v.status) === status || v.status === parent)) return false;
      if (v.status && !status) return false;
      return true;
    }).map(function (v) {
      var stale = v.last_checked && lp.stale_after_days ? ((Date.now() - Date.parse(v.last_checked)) / 86400000 > lp.stale_after_days) : false;
      return Object.assign({}, v, { effectiveLayer: stale ? 'STALE_REPORT' : v.layer, office_name_ko: ((lp.offices || []).filter(function (o) { return o.id === v.office; })[0] || {}).name_ko });
    });
    return { available: true, office: office, officeId: officeId, variations: officeId ? variations : [], anyForProcedure: variations.length, offices: lp.offices || [], layers: lp.truth_layers || [] };
  }

  function compose(step, state, bundle) {
    var lang = state.lang || 'ko';
    var status = step.status || effectiveStatus(state);
    var procedure = step.procedure || effectiveProcedure(state);
    var codeInfo = status ? (bundle.codes[status] || {}) : {};
    var proc = procedure ? procedureMeta(bundle, procedure) : null;
    var model = { kind: step.kind, lang: lang, status: status, statusName: codeInfo.name_ko, statusNameEn: codeInfo.name_en, procedure: procedure, procedureLabel: proc ? (lang === 'en' ? proc.en : proc.ko) : '', lifecycle: codeInfo.lifecycle, temporal: codeInfo.temporal || {}, programs: [], relatedPrograms: [], step: step, common: !!step.common, route: state.interp.route || null };
    var programCode = step.displayCode || (step.entries && step.entries[0] && step.entries[0].target !== 'COMMON' ? step.entries[0].target.split('~')[0] : status);
    var programInfo = (programCode && bundle.codes[programCode]) || codeInfo;
    function byId(id) { return bundle.programs.filter(function (p) { return p.id === id; })[0]; }
    model.programs = (programInfo.programs || []).map(byId).filter(Boolean);
    model.relatedPrograms = (programInfo.related_programs || (programCode !== status ? codeInfo.related_programs : []) || []).map(byId).filter(Boolean);
    var entries = step.entries || [];
    var entry = entries[0] || null;
    model.entry = entry;
    model.target = entry && entry.target !== 'COMMON' ? entry.target.split('~')[0] : status;
    model.targetInfo = entry && entry.target !== 'COMMON' ? bundle.codes[entry.target] || bundle.codes[model.target] || {} : codeInfo;
    model.state = entry ? entry.state : (step.state || null);
    model.completeness = entry ? entry.completeness : (step.kind === 'unresolved' ? 'REQUIRES_CLARIFICATION' : 'SOURCE_ONLY');
    model.reason = step.reason || null;
    model.documentGroups = entry ? groupDocuments(entry, { reason: model.reason }) : [];
    model.docCounts = { required: 0, conditional: 0 };
    model.documentGroups.forEach(function (g) { if (g.key === 'required') model.docCounts.required += g.items.length; else if (g.key === 'conditional' || g.key === 'applicable' || g.key === 'alternative') model.docCounts.conditional += g.items.length; });
    model.overlays = procedure && (status || step.common) ? applicableOverlays(bundle, status, procedure, entry) : [];
    model.overlayTiers = tierOverlays(model.overlays, entry);
    var targetStatus = procedure === 'status_change' ? (model.target || status) : null;
    model.fees = procedure && step.kind !== 'question' && step.kind !== 'need-status' ? feesFor(bundle, procedure, status, targetStatus) : null;
    model.feeEvidence = feeEvidence(entry);
    model.entryFeeNote = entry && entry.fee_ko ? { ko: entry.fee_ko, en: entry.fee_en } : null;
    model.userProgram = state.interp.userProgram || null;
    model.evidence = evidenceFor(bundle, step, entries, model.fees).map(function (e) { return e.type === 'manual' ? Object.assign({}, e, manualMeta(bundle, e.manual)) : e; });
    model.basisDate = latestBasisDate(model.evidence);
    model.transition = step.transition || null;
    model.currentStatus = state.answers && state.answers.current_status || null;
    if (model.transition && model.currentStatus) {
      var cq = bundle.current_status_question || { options: [] };
      var copt = cq.options.filter(function (o) { return o.id === model.currentStatus; })[0];
      var cls = copt && copt.targets && copt.targets.length ? copt.targets[0] : model.currentStatus;
      var ex = model.currentStatus === 'unsure' ? null : model.transition.exclusions.filter(function (x) { return x.class === cls || (x.from || []).indexOf(cls) >= 0; })[0];
      model.transitionOutcome = ex ? { state: ex.state, ko: ex.ko, en: ex.en, exceptions: ex.exceptions || [] } : { state: 'SUPPORTED' };
    }
    model.related = procedure && codeInfo.procedures ? PROCEDURE_ORDER.filter(function (pid) { var st = codeInfo.procedures[pid]; return pid !== procedure && st && ['SUPPORTED', 'CONDITIONAL', 'EXCEPTION_ONLY'].indexOf(st.s) >= 0; }).slice(0, 6) : [];
    model.officerNote = tr(lang, 'officer');
    model.localPractice = procedure ? localPracticeFor(bundle, state, procedure, status) : { available: false, variations: [], offices: [] };
    model.registry = procedure ? registryFor(bundle, procedure) : null;
    Object.defineProperty(model, 'bundle', { value: bundle, enumerable: false });
    return model;
  }

  /* ---------------------------------------------------------------- render -- */
  function stateBadge(lang, st) { if (!st) return ''; var lab = tr(lang, 'stateLabel')[st] || st; return '<span class="sg-state sg-state-' + esc(st.toLowerCase()) + '">' + esc(lab) + '</span>'; }
  function layerBadge(lang, layer) { var lab = tr(lang, 'layers')[layer] || layer; return '<span class="sg-layer sg-layer-' + esc(String(layer).toLowerCase()) + '">' + esc(lab) + '</span>'; }

  /* How the reading was reached decides how it is worded:
   *   EXACT_CODE       the query carries the status code itself        → definitive
   *   CONFIRMED        the user picked the status / procedure          → definitive
   *   EXACT_PROCEDURE  a procedure keyword and no status needed        → definitive
   *   NATURAL_HIGH     inferred from words with a single reading       → "…(으)로 이해했어요"
   *   AMBIGUOUS        alias, partial or low-confidence reading         → "…이해했어요" + edit prompt */
  // The query is the procedure's own name (or one of its registered keywords), not a sentence about it.
  function isProcedureName(query, model) {
    var q = String(query || '').toLowerCase().replace(/\s+/g, '');
    if (!q || !model.bundle) return false;
    var p = procedureMeta(model.bundle, model.procedure);
    if (!p) return false;
    return [p.ko, p.en].concat(p.keywords || []).some(function (k) { return String(k || '').toLowerCase().replace(/\s+/g, '') === q; });
  }
  function matchKind(state, model) {
    var interp = state.interp || { codes: [] };
    var status = model.status;
    if (status && (interp.codes || []).some(function (c) { return c.code === status && !c.fromAlias && !c.fromUnknown; })) return 'EXACT_CODE';
    if (state.status && state.status === status) return 'CONFIRMED';
    if (!status && model.procedure && interp.procedure === model.procedure && !interp.isQuestion && !(interp.codes || []).length && isProcedureName(state.query || interp.query, model)) return 'EXACT_PROCEDURE';
    if (!status && model.procedure && state.procedure === model.procedure) return 'CONFIRMED';
    if (interp.confidence === 'HIGH') return 'NATURAL_HIGH';
    return 'AMBIGUOUS';
  }
  function renderInterpretation(model, state, bundle) {
    var lang = model.lang; var interp = state.interp;
    var status = model.status; var procLabel = model.procedureLabel;
    var mk = matchKind(state, model);
    var definitive = (mk === 'EXACT_CODE' || mk === 'CONFIRMED' || mk === 'EXACT_PROCEDURE') && model.kind !== 'program';
    var text;
    if (model.kind === 'program' && model.step.program) text = tr(lang, 'understoodProgram', { program: LL(lang, { ko: model.step.program.name_ko, en: model.step.program.name_en }) });
    else if (status && procLabel) text = tr(lang, 'understood', { status: status, procedure: procLabel });
    else if (status) text = tr(lang, 'understoodStatusOnly', { status: status });
    else if (procLabel) text = tr(lang, 'understoodProcOnly', { procedure: procLabel });
    else text = tr(lang, 'noStatus');
    var name = status ? (lang === 'en' ? (model.statusNameEn || model.statusName) : model.statusName) : '';
    var office = model.localPractice && model.localPractice.office;
    var officeHtml = office ? ' <span class="sg-interp-office">· ' + esc(tr(lang, 'understoodOffice', { office: lang === 'en' ? office.name_en : office.name_ko })) + '</span>' : '';
    if (definitive && (status || procLabel)) {
      var out = '<div class="sg-interp" role="status" aria-live="polite" data-sg-match="' + mk + '"><p class="sg-interp-text"><span class="sg-sr">' + esc(tr(lang, 'interpLabel')) + ': </span>' +
        (status ? '<span class="sg-interp-code">' + esc(status) + '</span>' + (name ? ' <span class="sg-interp-name">' + esc(name) + '</span>' : '') : '') +
        (procLabel ? (status ? ' <span class="sg-interp-sep" aria-hidden="true">·</span> ' : '') + '<span class="sg-interp-proc">' + esc(procLabel) + '</span>' : '') + officeHtml + '</p>';
      out += '<button type="button" class="sg-link" data-sg-action="edit" aria-expanded="' + (state.editing ? 'true' : 'false') + '" aria-controls="sgEditor">' + esc(tr(lang, state.editing ? 'done' : 'edit')) + '</button></div>';
      return out + interpEditor(model, state, bundle);
    }
    var html = '<div class="sg-interp" role="status" aria-live="polite" data-sg-match="' + mk + '"><p class="sg-interp-text">' + esc(text) + (name ? ' <span class="sg-interp-name">' + esc(name) + '</span>' : '') + officeHtml + '</p>';
    if (status || procLabel) html += '<button type="button" class="sg-link" data-sg-action="edit" aria-expanded="' + (state.editing ? 'true' : 'false') + '" aria-controls="sgEditor">' + esc(tr(lang, state.editing ? 'done' : 'edit')) + '</button>';
    html += '</div>';
    if (interp.confidence === 'LOW' && (status || procLabel)) html += '<p class="sg-muted">' + esc(tr(lang, 'confidenceLow')) + '</p>';
    return html + interpEditor(model, state, bundle);
  }
  function interpEditor(model, state, bundle) {
    var lang = model.lang; var interp = state.interp; var status = model.status; var html = '';
    (interp.unknownCodes || []).forEach(function (c) { html += '<p class="sg-warn">' + esc(tr(lang, 'unknownCode', { code: c })) + '</p>'; });
    if (state.editing) {
      var opts = PROCEDURE_ORDER.filter(function (pid) { var c = bundle.codes[status]; var st = c && c.procedures && c.procedures[pid]; return st && st.s !== 'UNVERIFIED'; });
      if (!opts.length) opts = PROCEDURE_ORDER.slice(0, 10);
      html += '<div id="sgEditor" class="sg-editor"><p class="sg-editor-label">' + esc(tr(lang, 'changeProcedure')) + '</p><div class="sg-chips" role="group" aria-label="' + esc(tr(lang, 'changeProcedure')) + '">' +
        opts.map(function (pid) { var p = procedureMeta(bundle, pid); return '<button type="button" class="sg-chip" data-sg-action="set-procedure" data-sg-value="' + esc(pid) + '" aria-pressed="' + (pid === model.procedure) + '">' + esc(lang === 'en' ? p.en : p.ko) + '</button>'; }).join('') + '</div>' +
        '<p class="sg-editor-label">' + esc(tr(lang, 'changeStatus')) + '</p><form class="sg-code-form" data-sg-form="code"><label class="sg-sr" for="sgCodeInput">' + esc(tr(lang, 'searchCode')) + '</label><input id="sgCodeInput" type="text" inputmode="text" autocomplete="off" placeholder="F-1-5" maxlength="12"><button type="submit" class="sg-btn">' + esc(tr(lang, 'searchCode')) + '</button></form></div>';
    }
    return html;
  }

  function renderAnswered(model, step, lang) {
    var list = (step.answered || []).slice();
    if (model.currentStatus) list.push({ dimension: { id: 'current_status' }, option: { ko: tr('ko', 'currentStatus') + ': ' + model.currentStatus, en: tr('en', 'currentStatus') + ': ' + model.currentStatus } });
    if (!list.length) return '';
    return '<div class="sg-answered"><span class="sg-answered-label">' + esc(tr(lang, 'answered')) + '</span>' + list.map(function (a) {
      return '<span class="sg-answered-item">' + esc(LL(lang, a.option)) + ' <button type="button" class="sg-link" data-sg-action="reopen" data-sg-dim="' + esc(a.dimension.id) + '">' + esc(tr(lang, 'change')) + '</button></span>';
    }).join('') + '</div>';
  }

  function renderQuestion(step, model, state) {
    var lang = model.lang;
    var intro = '';
    if (step.why === 'subtype') intro = step.remaining === 2 ? tr(lang, 'twoTypes') : tr(lang, 'manyTypes', { status: model.status });
    var gks = state.interp && state.interp.userProgram === 'gks' && state.interp.facet === 'fee' && model.bundle ? '<p class="sg-warn">' + esc(gksFeeNote(model.bundle, lang)) + '</p>' : '';
    var html = '<section class="sg-question" aria-labelledby="sgQuestionTitle" data-sg-dim="' + esc(step.dimension) + '">' + renderAnswered(model, step, lang) + gks +
      (intro ? '<p class="sg-question-intro">' + esc(intro) + '</p>' : '') +
      '<h3 id="sgQuestionTitle" class="sg-question-title" tabindex="-1">' + esc(L(lang, step, 'question')) + '</h3>' + (step.hint_ko ? '<p class="sg-muted">' + esc(L(lang, step, 'hint')) + '</p>' : '') +
      '<div class="sg-options' + (step.why === 'procedure' ? ' sg-options-grid' : '') + '" role="group" aria-labelledby="sgQuestionTitle">' +
      step.options.map(function (o) { return '<button type="button" class="sg-option" data-sg-action="answer" data-sg-dim="' + esc(step.dimension) + '" data-sg-value="' + esc(o.id) + '" aria-pressed="false">' + esc(LL(lang, o)) + (o.state && o.state !== 'SUPPORTED' ? ' ' + stateBadge(lang, o.state) : '') + (o.hint_ko ? '<small>' + esc(L(lang, o, 'hint')) + '</small>' : '') + '</button>'; }).join('') +
      '</div><div class="sg-question-foot">' + (step.allowUnsure ? '<button type="button" class="sg-option sg-option-unsure" data-sg-action="answer" data-sg-dim="' + esc(step.dimension) + '" data-sg-value="unsure">' + esc(tr(lang, 'unsure')) + '</button>' : '') +
      (state.history && state.history.length ? '<button type="button" class="sg-link" data-sg-action="back">' + esc(tr(lang, 'back')) + '</button>' : '') + '</div>' +
      (step.showCodeForm ? '<form class="sg-code-form" data-sg-form="code"><label class="sg-sr" for="sgCodeInput">' + esc(tr(lang, 'searchCode')) + '</label><input id="sgCodeInput" type="text" inputmode="text" autocomplete="off" placeholder="F-6-1" maxlength="12"><button type="submit" class="sg-btn">' + esc(tr(lang, 'searchCode')) + '</button></form>' : '') +
      (step.unsure_ko && state.answers[step.dimension] === 'unsure' ? '<p class="sg-muted">' + esc(L(lang, step, 'unsure')) + '</p>' : '') + '</section>';
    return html;
  }

  function renderNeedStatus(step, model, state, bundle) {
    var lang = model.lang;
    var head = '<section class="sg-answer sg-need-status" aria-labelledby="sgAnswerTitle"><p class="sg-kicker">' + esc(model.procedureLabel) + '</p><h2 id="sgAnswerTitle" class="sg-answer-title" tabindex="-1">' + esc(tr(lang, 'needStatusTitle', { procedure: model.procedureLabel })) + '</h2>' +
      '<p class="sg-lead">' + esc(step.registry ? L(lang, step.registry, 'basis') : tr(lang, 'needStatusLead')) + '</p></section>';
    return head + renderQuestion(step, model, state) + renderWaymaker(model, step);
  }

  function formLabel(lang, d) {
    var f = d.submission_form;
    if (!f || f === 'NOT_APPLICABLE' || f === 'SOURCE_DOES_NOT_SPECIFY') return '';
    var label = tr(lang, 'forms')[f] || '';
    if (f === 'ORIGINAL_AND_COPY' && d.copy_count) label = (lang === 'en' ? 'Original + ' : '원본 + ') + tr(lang, 'formCopies', { n: d.copy_count });
    else if (f === 'COPY_ONLY' && d.copy_count) label = tr(lang, 'formCopies', { n: d.copy_count });
    // "원본" alone never says whether it is only shown or handed in. Only a source-backed
    // return statement distinguishes presentation from surrender; otherwise the label stays bare.
    if (f === 'ORIGINAL_ONLY' && d.original_returned === true) label = tr(lang, 'formOriginalShown');
    else if (f === 'ORIGINAL_ONLY' && d.original_returned === false) label = tr(lang, 'formOriginalKept');
    else if (d.original_returned === true) label += ' · ' + tr(lang, 'formReturned');
    return label;
  }

  /* Physical-form preparation policy.
   * Two different questions are kept apart: whether a document is required
   * (requirement_level) and what physical form to prepare (this layer).
   *   OFFICIAL_EXPLICIT          the rule's own source phrase / regulation states original or copy;
   *   PREPARATION_RECOMMENDATION the source is silent — a preparation default, never a rule:
   *                                BRING_ORIGINAL   bring the original, a copy may be prepared;
   *                                KEEP_ORIGINAL    possession-sensitive originals (passport,
   *                                                 ID cards, contracts, diplomas, licences):
   *                                                 bring the original to be checked, prepare a
   *                                                 copy for submission — never "submit original";
   *   NOT_APPLICABLE             the item is a form you fill in, a fee or a photo.
   * Source beats heuristic: an explicit form is shown as written even for a contract. */
  var POSSESSION_REF = /passport|^arc|_id$|_id_|contract|diploma|degree|licen[cs]e|ip_proof|patent|biz_reg|business_reg|registration_cert|corp_reg/i;
  var POSSESSION_NAME = /여권|등록증|신분증|계약서|약정서|학위|졸업증|자격증|면허|특허|여행증명서|거소신고증|영주증|고유번호증|허가증/;
  var FORM_REF = /^app_form|_form_\d+|_form$|^form_/;
  var FORM_NAME = /^(?:재외동포\s*)?(?:통합)?신청서|^신고서|\(별지 제\d+호/;
  function docClass(d) {
    var ref = String(d.ref || ''), name = String(d.name_ko || '');
    if (ref === 'fee' || /수수료/.test(name)) return 'fee';
    if (/photo/.test(ref) || /^사진/.test(name)) return 'photo';
    if (FORM_REF.test(ref) || FORM_NAME.test(name)) return 'form';
    if (POSSESSION_REF.test(ref) || POSSESSION_NAME.test(name)) return 'possession';
    return 'general';
  }
  function preparation(d) {
    var f = d.submission_form || 'SOURCE_DOES_NOT_SPECIFY';
    var cls = docClass(d);
    if (f !== 'SOURCE_DOES_NOT_SPECIFY' && f !== 'NOT_APPLICABLE') return { kind: 'OFFICIAL_EXPLICIT', form: f, basis: d.form_basis || 'SOURCE_PHRASE', docClass: cls, returnKnown: d.original_returned === true || d.original_returned === false };
    if (cls === 'form' || cls === 'fee' || cls === 'photo' || f === 'NOT_APPLICABLE') return { kind: 'NOT_APPLICABLE', form: 'NOT_APPLICABLE', docClass: cls };
    return { kind: 'PREPARATION_RECOMMENDATION', form: 'SOURCE_DOES_NOT_SPECIFY', policy: cls === 'possession' ? 'KEEP_ORIGINAL' : 'BRING_ORIGINAL', docClass: cls };
  }
  function preparationLabel(lang, d) {
    var p = preparation(d);
    if (p.kind === 'OFFICIAL_EXPLICIT') return formLabel(lang, d) || tr(lang, 'forms')[p.form] || '';
    if (p.kind === 'PREPARATION_RECOMMENDATION') return tr(lang, p.policy === 'KEEP_ORIGINAL' ? 'prepKeep' : 'prepBring');
    return '';
  }

  /* One document row, in the order a person scans it: name · requirement (the
   * group heading) · submission form · who prepares it · issuer · condition.
   * Source, validity and the other particulars sit behind the row's disclosure.
   * A silent-source preparation label is a short dashed tag; the one explanation
   * of that tag is the section note, never repeated per row. */
  function renderDocItem(d, lang, bundle, entry) {
    var role = tr(lang, 'roles')[d.applicant_role] || d.applicant_role;
    var where = d.where_to_obtain ? (tr(lang, 'where_labels')[d.where_to_obtain] || d.where_to_obtain) : '';
    var name = lang === 'en' ? d.name_en : d.name_ko;
    var sub = lang === 'en' && d.name_ko ? '<span class="sg-doc-ko" lang="ko">' + esc(d.name_ko) + '</span>' : '';
    var prep = preparation(d);
    var form = preparationLabel(lang, d);
    var who = [];
    if (role && d.applicant_role !== 'applicant') who.push('<span class="sg-doc-who"><span class="sg-sr">' + esc(tr(lang, 'role')) + ': </span>' + esc(role) + '</span>');
    if (where) who.push('<span class="sg-doc-where"><span class="sg-sr">' + esc(tr(lang, 'where')) + ': </span>' + esc(where) + '</span>');
    var cond = d.applies_when_ko ? '<span class="sg-doc-cond">' + esc(L(lang, d, 'applies_when')) + '</span>' : '';
    var alts = d.alternatives && d.alternatives.length ? '<div class="sg-doc-alts"><span>' + esc(tr(lang, 'oneOf')) + '</span><ul>' + d.alternatives.map(function (a) { return '<li>' + esc(LL(lang, a)) + '</li>'; }).join('') + '</ul></div>' : '';
    var details = [];
    if (prep.kind === 'OFFICIAL_EXPLICIT') {
      var ftxt = form || tr(lang, 'forms')[d.submission_form] || d.submission_form;
      if (d.copy_count && d.submission_form !== 'ORIGINAL_AND_COPY' && d.submission_form !== 'COPY_ONLY') ftxt += ' · ' + tr(lang, 'formCopies', { n: d.copy_count });
      if (d.form_note_ko) ftxt += ' — ' + L(lang, d, 'form_note');
      var basis = tr(lang, 'formBasis')[d.form_basis] || '';
      if (basis) ftxt += ' (' + basis + ')';
      if (d.submission_form === 'ORIGINAL_ONLY' && !prep.returnKnown && prep.docClass === 'possession') ftxt += ' — ' + tr(lang, 'formReturnUnknown');
      details.push([tr(lang, 'formTitle'), ftxt]);
    } else if (prep.kind === 'PREPARATION_RECOMMENDATION') {
      details.push([tr(lang, 'formTitle'), form + ' · ' + tr(lang, 'prepBasis')]);
    }
    if (d.validity_period) details.push([tr(lang, 'validity'), d.validity_period]);
    if (d.does_not_apply_when_ko) details.push([tr(lang, 'notApplies'), L(lang, d, 'does_not_apply_when')]);
    if (d.notes_ko) details.push([tr(lang, 'notes'), L(lang, d, 'notes')]);
    if (d.apostille_required) details.push([tr(lang, 'apostille'), '']);
    if (d.substitute_documents && d.substitute_documents.length) details.push([tr(lang, 'oneOf'), d.substitute_documents.join(', ')]);
    var src = null;
    if (d.source && d.source.type === 'regulation' && bundle.law_sources && bundle.law_sources[d.source.law]) { var ls = bundle.law_sources[d.source.law]; src = [tr(lang, 'source'), (lang === 'en' ? ls.title_en : ls.title_ko) + ' ' + ls.article + (d.source.quote ? ' — “' + d.source.quote + '”' : '')]; }
    else if (d.source && d.source.pdf_page && entry && entry.source && bundle.sources[entry.source.manual]) { src = [tr(lang, 'source'), (lang === 'en' ? bundle.sources[entry.source.manual].title_en : bundle.sources[entry.source.manual].title_ko) + ' · ' + d.source.pdf_page + tr(lang, 'page') + (d.source.law && bundle.law_sources[d.source.law] ? ' · ' + bundle.law_sources[d.source.law].title_ko + ' ' + bundle.law_sources[d.source.law].article : '')]; }
    if (src) details.push(src);
    var body = details.length ? '<dl class="sg-doc-meta">' + details.map(function (p) { return '<div><dt>' + esc(p[0]) + '</dt><dd' + koIf(lang, p[1]) + '>' + esc(p[1]) + '</dd></div>'; }).join('') + '</dl>' : '';
    var head = '<span class="sg-doc-main"><span class="sg-doc-name">' + esc(name) + '</span>' + sub + (form ? '<span class="sg-doc-form' + (prep.kind === 'PREPARATION_RECOMMENDATION' ? ' sg-doc-form-rec' : '') + '" data-sg-form-kind="' + prep.kind + '">' + esc(form) + '</span>' : '') + (d.adminNote ? '<span class="sg-doc-tag">' + esc(tr(lang, 'grpAdmin')) + '</span>' : '') + '</span>';
    var line = who.length || cond ? '<span class="sg-doc-line">' + cond + who.join('') + '</span>' : '';
    if (!body && !alts) return '<li class="sg-doc"><div class="sg-doc-row">' + head + line + '</div></li>';
    return '<li class="sg-doc"><details class="sg-doc-details"><summary class="sg-doc-row">' + head + line + '</summary>' + alts + body + '</details></li>';
  }

  function renderDocuments(model, bundle) {
    var lang = model.lang; var entry = model.entry;
    if (!entry) return '';
    var full = entry.completeness === 'FULLY_STRUCTURED';
    var title = full ? tr(lang, 'docsTitle') : tr(lang, 'docsPartial');
    var counts = model.docCounts.required ? '<span class="sg-docs-count">' + esc(tr(lang, 'docsCount', { n: model.docCounts.required })) + (model.docCounts.conditional ? ' · ' + esc(tr(lang, 'docsCountCond', { n: model.docCounts.conditional })) : '') + '</span>' : '';
    var html = '<section class="sg-docs" id="sgDocs" aria-labelledby="sgDocsTitle"><div class="sg-section-head"><h3 id="sgDocsTitle" tabindex="-1">' + esc(title) + '</h3>' + counts + '</div>';
    if (!model.documentGroups.length) { html += '<p class="sg-muted">' + esc(tr(lang, entry.completeness === 'SOURCE_ONLY' ? 'docsSourceOnly' : 'docsClarify')) + '</p></section>'; return html; }
    var recommended = false;
    model.documentGroups.forEach(function (g) {
      g.items.forEach(function (d) { if (preparation(d).kind === 'PREPARATION_RECOMMENDATION') recommended = true; });
      html += '<div class="sg-doc-group sg-doc-group-' + g.key + '"><h4>' + esc(tr(lang, g.labelKey)) + ' <span class="sg-doc-group-n">' + g.items.length + '</span></h4><ul class="sg-doc-list">' + g.items.map(function (d) { return renderDocItem(d, lang, bundle, entry); }).join('') + '</ul></div>';
    });
    if (recommended) html += '<p class="sg-doc-prep-note">' + esc(tr(lang, 'prepSection')) + '</p>';
    if (!full) html += '<p class="sg-muted">' + esc(tr(lang, 'docsClarify')) + '</p>';
    html += '<p class="sg-officer">' + esc(model.officerNote) + '</p></section>';
    return html;
  }

  function renderFacts(model) {
    var lang = model.lang; var e = model.entry; var rows = [];
    if (e && e.period_ko) rows.push([tr(lang, 'period'), L(lang, e, 'period')]);
    if (e && e.timing_ko) rows.push([tr(lang, 'timing'), L(lang, e, 'timing')]);
    if (e && e.channel_ko) rows.push([tr(lang, 'channel'), L(lang, e, 'channel')]);
    if (e && e.filer) rows.push([tr(lang, 'filer'), tr(lang, 'roles')[e.filer] || e.filer]);
    if (!rows.length) return '';
    return '<dl class="sg-facts">' + rows.map(function (r) { return '<div><dt>' + esc(r[0]) + '</dt><dd>' + esc(r[1]) + '</dd></div>'; }).join('') + '</dl>';
  }

  function feeAmountLine(lang, f) {
    if (f.amount_state === 'NO_FEE') return tr(lang, 'feeNone');
    if (f.amount_state === 'NOT_LISTED') return tr(lang, 'feeNotListed');
    var line = won(f.amount);
    if (f.amount_state === 'CONFLICT') line += ' · ' + tr(lang, 'feeConflict');
    return line;
  }
  function feeSummary(lang, model) {
    var fees = model.fees;
    if (!fees) return null;
    var f = fees.primary[0];
    if (!f) return null;
    if (fees.primary.length > 1 && fees.primary.every(function (x) { return x.amount_state === 'FIXED'; })) return fees.primary.map(function (x) { return (lang === 'en' ? x.label_en : x.label_ko).replace(/ (수수료|fee)$/i, '') + ' ' + won(x.amount); }).join(' · ');
    return feeAmountLine(lang, f);
  }
  function renderFees(model, bundle) {
    var lang = model.lang; var fees = model.fees;
    if (!fees) return '';
    var html = '<section class="sg-fee" aria-labelledby="sgFeeTitle"><h3 id="sgFeeTitle">' + esc(tr(lang, 'feeTitle')) + '</h3>';
    // Every note line in this section goes through one list, so a data note and a
    // renderer note that say the same thing (합니다체 / 해요체) are printed once.
    var shown = [];
    function note(text, cls, prefix) {
      if (!text || shown.some(function (m) { return sameNote(m, text); })) return '';
      shown.push(text);
      return '<p class="sg-fee-line ' + (cls || 'sg-muted') + '">' + (prefix ? esc(prefix) + ': ' : '') + esc(text) + '</p>';
    }
    fees.primary.forEach(function (f) {
      var review = tr(lang, 'feeReview')[f.review_state] || f.review_state;
      html += '<div class="sg-fee-row"><div class="sg-fee-amount">' + esc(feeAmountLine(lang, f)) + '</div><div class="sg-fee-label">' + esc(lang === 'en' ? f.label_en : f.label_ko) + ' <span class="sg-fee-review sg-fee-review-' + esc(f.review_state.toLowerCase()) + '">' + esc(review) + '</span></div>';
      if (f.payment_instruments && f.payment_instruments.length) html += '<div class="sg-fee-line"><span class="sg-fee-k">' + esc(tr(lang, 'feeInstrument')) + '</span> ' + esc(f.payment_instruments.map(function (i) { return tr(lang, 'instruments')[i] || i; }).join(' · ')) + '</div>';
      if (f.online_reduction) html += '<div class="sg-fee-line">' + esc(tr(lang, 'feeOnline', { pct: Math.round(f.online_reduction.rate * 100) })) + '</div>';
      (f.conflicts || []).forEach(function (c) { html += '<p class="sg-warn"><span>' + esc(L(lang, c, 'regulation')) + ' · ' + esc(L(lang, c, 'manual')) + '<br>' + esc(L(lang, c, 'interim')) + '</span></p>'; });
      var ex = (f.exemptions || []).filter(function (e) { return exemptionApplies(e, model.status, model.target, model.userProgram); });
      if (ex.length) {
        html += '<details class="sg-fee-details"' + (model.userProgram && ex.some(function (e) { return e.program === model.userProgram; }) ? ' open' : '') + '><summary>' + esc(tr(lang, 'feeExemptTitle')) + ' · ' + ex.length + '</summary><ul>' + ex.map(function (e) {
          var hi = model.userProgram && e.program === model.userProgram;
          return '<li' + (hi ? ' class="sg-fee-hi"' : '') + '>' + (hi ? '<strong>' + esc(tr(lang, 'feeGks')) + '</strong> · ' : '') + esc(L(lang, e, 'condition')) + ' <span class="sg-fee-review sg-fee-review-' + esc(e.review_state.toLowerCase()) + '">' + esc(tr(lang, 'feeReview')[e.review_state] || e.review_state) + '</span>' + (e.evidence_required_ko ? '<br><span class="sg-muted">' + esc(L(lang, e, 'evidence_required')) + '</span>' : '') + '</li>';
        }).join('') + '</ul></details>';
      }
      if (f.not_exempt && f.not_exempt.length) html += '<p class="sg-fee-line sg-fee-not"><span class="sg-fee-k">' + esc(tr(lang, 'feeNotExempt')) + '</span> ' + f.not_exempt.map(function (n) { return esc(LL(lang, n)); }).join(' ') + '</p>';
      (f.investigations || []).forEach(function (inv) { if (model.userProgram || (model.status && parentOf(model.status) === 'G-1')) html += '<p class="sg-fee-line"><span class="sg-fee-k">' + esc(tr(lang, 'feeInvestigated')) + '</span> ' + esc(LL(lang, inv)) + '</p>'; });
      ((lang === 'en' ? f.notes_en : f.notes_ko) || []).forEach(function (n) { html += note(n); });
      html += '</div>';
    });
    if (fees.variants.length) html += '<p class="sg-fee-variants"><span class="sg-fee-k">' + esc(tr(lang, 'feeVariants')) + '</span> ' + fees.variants.map(function (v) { return esc((lang === 'en' ? v.label_en : v.label_ko) + ': ' + feeAmountLine(lang, v)); }).join(' · ') + '</p>';
    if (model.entryFeeNote && !fees.primary.some(function (f) { return f.amount_state === 'NO_FEE'; })) html += note(LL(lang, model.entryFeeNote), 'sg-muted', tr(lang, 'feeEntryNote'));
    if (fees.primary.some(function (f) { return f.amount > 0; })) html += note(tr(lang, 'feeNonRefundable'));
    return html + '</section>';
  }

  function renderConditions(model) {
    var lang = model.lang; var e = model.entry;
    var conds = e ? (lang === 'en' && e.conditions_en && e.conditions_en.length ? e.conditions_en : e.conditions_ko) : [];
    if (!conds || !conds.length) return '';
    return '<div class="sg-conditions"><h4>' + esc(tr(lang, 'conditions')) + '</h4><ul>' + conds.map(function (c) { return '<li>' + esc(c) + '</li>'; }).join('') + '</ul></div>';
  }
  function renderNotes(model) {
    var lang = model.lang; var e = model.entry;
    var notes = e ? (lang === 'en' && e.notes_en && e.notes_en.length ? e.notes_en : e.notes_ko) : [];
    if (!notes || !notes.length) return '';
    return '<ul class="sg-notes">' + notes.map(function (c) { return '<li>' + esc(c) + '</li>'; }).join('') + '</ul>';
  }

  function overlayItem(lang, o) {
    return '<li><details><summary>' + esc(LL(lang, o).split(/[.。]\s/)[0]) + '</summary><p>' + esc(LL(lang, o)) + '</p><p class="sg-muted">' + esc(tr(lang, 'evidenceManual')) + ' · ' + esc(tr(lang, 'stayManual')) + ' · ' + o.pdf_page + tr(lang, 'page') + '</p></details></li>';
  }
  /* F · conditions and exceptions: the rule's own conditions and notes, the
   * special-case variants, then the common rules this procedure actually
   * triggers; untriggered common rules stay behind one disclosure. */
  function renderConditionsSection(model, step) {
    var lang = model.lang;
    var body = renderConditions(model) + renderNotes(model);
    if (step && step.variants && step.variants.length) {
      body += '<div class="sg-variants"><h4>' + esc(tr(lang, 'variantsTitle')) + '</h4><ul class="sg-candidates">' + step.variants.map(function (g) { return '<li><button type="button" class="sg-candidate" data-sg-action="pick-variant" data-sg-target="' + esc(targetKey(g)) + '"><span>' + esc(g.source.section.split(' — ').pop()) + '</span><small>' + esc(L(lang, g, 'summary').slice(0, 120)) + '</small></button></li>'; }).join('') + '</ul></div>';
    }
    var tiers = model.overlayTiers || { critical: [], contextual: [], reference: [] };
    var shown = tiers.critical.concat(tiers.contextual);
    var rules = '';
    if (shown.length) rules += '<h4 id="sgOverlayTitle">' + esc(tr(lang, 'overlays')) + '</h4><ul class="sg-rules">' + shown.map(function (o) { return overlayItem(lang, o); }).join('') + '</ul>';
    if (tiers.reference.length) rules += '<details class="sg-rules-more"><summary>' + esc(tr(lang, 'overlaysMore', { n: tiers.reference.length })) + '</summary><ul class="sg-rules">' + tiers.reference.map(function (o) { return overlayItem(lang, o); }).join('') + '</ul></details>';
    if (rules) body += '<div class="sg-overlays">' + rules + '</div>';
    if (!body) return '';
    return '<section class="sg-cond-section" aria-labelledby="sgCondTitle"><h3 id="sgCondTitle">' + esc(tr(lang, 'condTitle')) + '</h3>' + body + '</section>';
  }

  function renderTransition(model) {
    var lang = model.lang; var t = model.transition;
    if (!t) return '';
    var html = '<section class="sg-transition" aria-labelledby="sgTransitionTitle"><h3 id="sgTransitionTitle">' + esc(tr(lang, 'transitionTitle')) + '</h3>';
    html += '<p><span class="sg-muted">' + esc(tr(lang, 'from')) + '</span> ' + esc(model.currentStatus ? model.currentStatus : (lang === 'en' ? t.from_allowed_en : t.from_allowed_ko)) + ' <span aria-hidden="true">→</span> <span class="sg-muted">' + esc(tr(lang, 'to')) + '</span> <span class="sg-code">' + esc(t.to) + '</span></p>';
    if (model.transitionOutcome && model.transitionOutcome.state !== 'SUPPORTED') {
      html += '<p class="sg-warn">' + stateBadge(lang, model.transitionOutcome.state) + ' ' + esc(LL(lang, model.transitionOutcome)) + '</p>';
      if (model.transitionOutcome.exceptions.length) html += '<h4>' + esc(tr(lang, 'exceptions')) + '</h4><ul>' + model.transitionOutcome.exceptions.map(function (x) { return '<li>' + esc(LL(lang, x)) + '</li>'; }).join('') + '</ul>';
    } else if (t.exclusions && t.exclusions.length) {
      html += '<h4>' + esc(tr(lang, 'exclusions')) + '</h4><ul>' + t.exclusions.map(function (x) { return '<li>' + esc(LL(lang, x)) + '</li>'; }).join('') + '</ul>';
    }
    if (t.conditions_ko && t.conditions_ko.length) html += '<ul>' + (lang === 'en' ? t.conditions_en : t.conditions_ko).map(function (c) { return '<li>' + esc(c) + '</li>'; }).join('') + '</ul>';
    if (t.documents_note_ko) html += '<p class="sg-muted">' + esc(L(lang, t, 'documents_note')) + '</p>';
    if (t.period_ko) html += '<dl class="sg-facts"><div><dt>' + esc(tr(lang, 'period')) + '</dt><dd>' + esc(L(lang, t, 'period')) + '</dd></div></dl>';
    return html + '</section>';
  }

  function renderPrograms(model) {
    var lang = model.lang;
    var related = model.relatedPrograms.length ? '<p class="sg-muted sg-related-programs">' + esc(tr(lang, 'relatedPrograms')) + ' ' + model.relatedPrograms.map(function (p) { return '<button type="button" class="sg-link sg-link-inline" data-sg-action="search" data-sg-value="' + esc(lang === 'en' ? p.name_en : p.name_ko) + '">' + esc(LL(lang, { ko: p.name_ko, en: p.name_en })) + '</button>'; }).join(', ') + '</p>' : '';
    if (!model.programs.length) return related;
    return related + model.programs.map(function (p) {
      return '<section class="sg-program" aria-label="' + esc(tr(lang, 'programTitle')) + '"><p class="sg-kicker">' + esc(tr(lang, 'programTitle')) + '</p><h3>' + esc(LL(lang, { ko: p.name_ko, en: p.name_en })) + '</h3><p>' + esc(tr(lang, 'programNote')) + '</p><p>' + esc(L(lang, p, 'summary')) + '</p><p class="sg-muted">' + esc(tr(lang, 'dims')) + ': ' + esc((lang === 'en' ? p.dimensions_en : p.dimensions_ko).join(' · ')) + ' · ' + esc(tr(lang, 'evidenceManual')) + ' ' + esc(p.pdf_page) + tr(lang, 'page') + '</p></section>';
    }).join('');
  }

  function renderLocal(model, bundle) {
    var lang = model.lang; var lp = model.localPractice;
    if (!lp || !lp.available || !model.procedure) return '';
    var html = '<section class="sg-local" aria-labelledby="sgLocalTitle"><details class="sg-local-details"' + (lp.officeId ? ' open' : '') + '><summary><h3 id="sgLocalTitle">' + esc(tr(lang, 'localTitle')) + '</h3><span class="sg-muted">' + esc(lp.office ? (lang === 'en' ? lp.office.name_en : lp.office.name_ko) : tr(lang, 'localNational')) + '</span></summary>';
    html += '<p class="sg-local-national"><span class="sg-layer sg-layer-national_official_baseline">' + esc(tr(lang, 'localNational')) + '</span> ' + esc(tr(lang, 'localNationalBody')) + '</p>';
    var officeName = lp.office ? (lang === 'en' ? lp.office.name_en : lp.office.name_ko) : '';
    html += '<div class="sg-local-pick"><label for="sgOffice">' + esc(tr(lang, 'localPick')) + '</label><select id="sgOffice" data-sg-office><option value="">—</option>' + lp.offices.map(function (o) { return '<option value="' + esc(o.id) + '"' + (lp.officeId === o.id ? ' selected' : '') + '>' + esc(lang === 'en' ? o.name_en : o.name_ko) + '</option>'; }).join('') + '</select></div>';
    if (lp.office) {
      if (lp.variations.length) {
        html += '<p class="sg-local-has">' + esc(tr(lang, 'localHas', { office: officeName })) + '</p><ul class="sg-local-list">' + lp.variations.map(function (v) {
          return '<li class="sg-local-item"><details><summary>' + layerBadge(lang, v.effectiveLayer) + ' <span>' + esc(L(lang, v, 'summary')) + '</span></summary>' +
            '<p>' + esc(L(lang, v, 'detail')) + '</p>' +
            '<dl class="sg-doc-meta"><div><dt>' + esc(tr(lang, 'localKind')) + '</dt><dd>' + esc(tr(lang, 'layers')[v.effectiveLayer] || v.effectiveLayer) + ' · ' + esc(tr(lang, 'localReports', { n: v.report_count || 0 })) + '</dd></div>' +
            '<div><dt>' + esc(tr(lang, 'localChecked')) + '</dt><dd>' + esc(v.last_checked || tr(lang, 'localUnchecked')) + '</dd></div>' +
            '<div><dt>' + esc(tr(lang, 'localBaseline')) + '</dt><dd>' + esc(L(lang, v, 'national_baseline')) + '</dd></div></dl>' +
            '<p class="sg-warn">' + esc(tr(lang, 'localNotPolicy')) + '</p></details></li>';
        }).join('') + '</ul>';
      } else {
        html += '<p class="sg-muted">' + esc(tr(lang, 'localNone', { office: officeName })) + '</p>';
      }
    } else {
      html += '<p class="sg-muted">' + esc(tr(lang, 'localDiffer')) + '</p>';
    }
    html += '<button type="button" class="sg-link" data-sg-action="report">' + esc(tr(lang, 'localReport')) + '</button></details></section>';
    return html;
  }

  function aiHref(model) {
    return 'ai.html?' + (model.status ? 'visa_code=' + encodeURIComponent(model.status) + '&' : '') + (model.procedure ? 'selected_procedure_key=' + encodeURIComponent(model.procedure) + '&' : '') + 'lang=' + model.lang;
  }
  function renderNext(model) {
    var lang = model.lang;
    return '<section class="sg-next" aria-labelledby="sgNextTitle"><h3 id="sgNextTitle">' + esc(tr(lang, 'nextTitle')) + '</h3><ul>' +
      '<li><button type="button" class="sg-link" data-action="open-hikorea-guide" data-vcode="' + esc(model.status || '') + '">' + esc(tr(lang, 'nextReserve')) + '</button></li>' +
      '<li><a href="form-helper.html">' + esc(tr(lang, 'nextForms')) + '</a></li>' +
      '<li><a href="tel:1345">' + esc(tr(lang, 'nextCall')) + '</a></li>' +
      (model.status ? '<li><button type="button" class="sg-link" data-sg-action="legacy-card">' + esc(tr(lang, 'nextLegacy')) + '</button></li>' : '') +
      '<li class="sg-next-ai"><a href="' + esc(aiHref(model)) + '" data-sg-action="followup">' + esc(tr(lang, 'nextAi')) + '</a></li></ul></section>';
  }
  /* Waymaker's place on a result page: the structured answer owns the page.
   * Exact results carry only the compact follow-up link in 다음 할 일; when the
   * answer depends on more context (a question, an unresolved subtype, a
   * procedure that needs a status, nothing matched) Waymaker is offered as the
   * resolver, once, right after the answer. The full navigator lives on ai.html. */
  var WAYMAKER_RESOLVER_KINDS = { unresolved: true, 'need-status': true, 'no-status': true, 'source-only': true };
  function renderWaymaker(model, step) {
    if (!step || !WAYMAKER_RESOLVER_KINDS[step.kind]) return '';
    var lang = model.lang;
    return '<aside class="sg-wm" aria-labelledby="sgWmTitle"><p class="sg-wm-title" id="sgWmTitle">' + esc(tr(lang, 'wmTitle')) + '</p><p class="sg-wm-body">' + esc(tr(lang, 'wmBody')) + '</p><a class="sg-btn" href="' + esc(aiHref(model)) + '" data-sg-action="followup">' + esc(tr(lang, 'wmCta')) + '</a></aside>';
  }

  function manualTitle(lang, ev) {
    var t = lang === 'en' ? ev.title_en : ev.title_ko;
    if (t) return t;
    // never fall back to the internal id: name the manual by its domain
    return tr(lang, /visa/.test(String(ev.manual || ev.id || '')) ? 'visaManual' : 'stayManual');
  }
  function renderEvidence(model, bundle, opts) {
    var lang = model.lang;
    if (!model.evidence.length) return '';
    var open = opts && opts.open;
    var items = model.evidence.map(function (ev) {
      if (ev.type === 'regulation') {
        var ls = ev.law;
        var claims = ev.claims.filter(function (c, i, a) { return c && a.indexOf(c) === i; }).slice(0, 4).join(' · ');
        var lawTitle = (lang === 'en' ? ls.title_en : ls.title_ko) + ' ' + ls.article;
        return '<li class="sg-ev sg-ev-law"><div class="sg-evidence-meta">' + esc(tr(lang, 'evidenceRegulation')) + ' · <span' + koIf(lang, lawTitle) + '>' + esc(lawTitle) + '</span> · ' + esc(tr(lang, 'lawChecked', { date: ls.checked_on })) + '</div>' +
          '<div class="sg-evidence-section">' + esc(lang === 'en' ? ls.label_en : ls.label_ko) + '</div>' + (claims ? '<div class="sg-evidence-claims"' + koIf(lang, claims) + '>' + esc(claims) + '</div>' : '') +
          '<div class="sg-evidence-actions"><a href="' + esc(ls.url) + '" target="_blank" rel="noopener">' + esc(tr(lang, 'original')) + '</a></div></li>';
      }
      return '<li class="sg-ev sg-ev-manual"><div class="sg-evidence-meta">' + esc(manualTitle(lang, ev)) + ' · ' + esc(ev.date || '') + ' · ' + ev.page + esc(tr(lang, 'page')) + '</div>' + (ev.section ? '<div class="sg-evidence-section"' + koIf(lang, ev.section) + '>' + esc(ev.section) + '</div>' : '') +
        '<div class="sg-evidence-actions"><button type="button" class="sg-link" data-sg-action="open-page" data-sg-source="' + esc(ev.corpusId) + '" data-sg-page="' + ev.page + '">' + esc(tr(lang, 'open')) + '</button><a href="' + esc(ev.file) + '#page=' + ev.page + '" target="_blank" rel="noopener">' + esc(tr(lang, 'original')) + '</a></div></li>';
    }).join('');
    var hasManual = model.evidence.some(function (e) { return e.type === 'manual'; });
    return '<section class="sg-evidence" aria-labelledby="sgEvidenceTitle"><details class="sg-evidence-details" id="sgEvidence"' + (open ? ' open' : '') + '><summary><h3 id="sgEvidenceTitle">' + esc(tr(lang, 'evidenceTitle')) + ' <span class="sg-ev-count">' + esc(tr(lang, 'evidenceCount', { n: model.evidence.length })) + '</span></h3><span class="sg-ev-show">' + esc(tr(lang, 'evidenceShow')) + '</span></summary>' +
      (model.basisDate ? '<p class="sg-muted sg-ev-basis">' + esc(tr(lang, 'evidenceBasis', { date: model.basisDate })) + '</p>' : '') +
      (hasManual ? '<p class="sg-muted sg-ev-review">' + esc(tr(lang, 'evidenceReview')) + '</p>' : '') +
      '<ol class="sg-evidence-list">' + items + '</ol><div class="sg-raw-slot" id="sgRawSlot"></div></details></section>';
  }

  function renderRelated(model, bundle) {
    var lang = model.lang;
    if (!model.related.length) return '';
    return '<section class="sg-related" aria-labelledby="sgRelatedTitle"><h3 id="sgRelatedTitle">' + esc(tr(lang, 'relatedTitle')) + '</h3><div class="sg-chips">' + model.related.map(function (pid) { var p = procedureMeta(bundle, pid); return '<button type="button" class="sg-chip" data-sg-action="set-procedure" data-sg-value="' + esc(pid) + '">' + esc(lang === 'en' ? p.en : p.ko) + '</button>'; }).join('') + '</div></section>';
  }

  function renderLifecycle(model) {
    var lang = model.lang; var t = model.temporal || {}; var info = model.targetInfo || {};
    var tt = info.temporal || t;
    if (model.lifecycle === 'legacy_holders_only' || (info.lifecycle === 'legacy_holders_only')) return '<p class="sg-warn">' + esc(tr(lang, 'legacyStop', { date: tt.effective_to || t.effective_to || '' })) + '</p>';
    if (info.lifecycle === 'abolished') return '<p class="sg-warn">' + esc(tr(lang, 'abolished', { date: tt.effective_to || '', superseded: tt.superseded_by || '' })) + '</p>';
    return '';
  }

  function renderReason(model, step, bundle) {
    var lang = model.lang; var dim = step.reasonDim;
    if (!dim) return '';
    return '<div class="sg-reason"><p class="sg-editor-label">' + esc(tr(lang, 'reasonTitle')) + '</p><p class="sg-muted">' + esc(tr(lang, 'reasonWhy')) + '</p><div class="sg-chips" role="group" aria-label="' + esc(tr(lang, 'reasonTitle')) + '">' + dim.options.map(function (o) {
      return '<button type="button" class="sg-chip" data-sg-action="answer" data-sg-dim="reissue_reason" data-sg-value="' + esc(o.id) + '" aria-pressed="' + (model.reason === o.id) + '">' + esc(LL(lang, o)) + '</button>';
    }).join('') + '</div></div>';
  }

  // C core guidance (above) · D documents · E fees · F conditions / exceptions ·
  // G local office · H next actions · I Waymaker (resolver only) · J evidence · K related.
  function detailSections(model, step, bundle, state) {
    return renderTransition(model) + renderPrograms(model) + renderDocuments(model, bundle) + renderFees(model, bundle) + renderConditionsSection(model, step) + renderLocal(model, bundle) + renderNext(model) + renderWaymaker(model, step) + renderEvidence(model, bundle, { open: !!state.evidenceOpen }) + renderRelated(model, bundle);
  }
  // One immediate next action inside the first screen.
  function answerActions(model) {
    var lang = model.lang; var n = model.docCounts.required + model.docCounts.conditional;
    var docs = n ? '<a class="sg-btn sg-btn-primary" href="#sgDocs" data-sg-action="jump-docs">' + esc(tr(lang, 'nextDocs', { n: n })) + '</a>' : '';
    return '<div class="sg-answer-actions">' + docs + '<button type="button" class="sg-btn" data-action="open-hikorea-guide" data-vcode="' + esc(model.status || '') + '">' + esc(tr(lang, 'nextReserve')) + '</button></div>';
  }

  function renderAnswer(model, step, bundle, state) {
    var lang = model.lang; var e = model.entry;
    var targetCode = step.displayCode || (e ? e.target.split('~')[0] : model.status);
    var tInfo = bundle.codes[targetCode] || model.targetInfo || {};
    var targetName = lang === 'en' ? (tInfo.name_en || tInfo.name_ko) : tInfo.name_ko;
    var ruleCode = e ? e.target.split('~')[0] : targetCode;
    // Certainty follows the match, not a blanket hedge: a code the user typed (or
    // picked) is answered definitively; only a reading inferred from words says "closest".
    var mk = matchKind(state, model);
    var definitive = step.exact || step.confidence === 'HIGH' || mk === 'EXACT_CODE' || mk === 'CONFIRMED';
    var lead = step.inherited ? tr(lang, 'inherited', { parent: ruleCode }) : (definitive ? tr(lang, 'exact', { target: targetCode }) : tr(lang, 'closest', { target: targetCode }));
    var html = '<section class="sg-answer" aria-labelledby="sgAnswerTitle">' + renderAnswered(model, step, lang) +
      '<p class="sg-kicker">' + esc(model.procedureLabel) + '</p><h2 id="sgAnswerTitle" class="sg-answer-title" tabindex="-1"><span class="sg-code">' + esc(targetCode) + '</span>' + (targetName ? ' <span class="sg-name">' + esc(targetName) + '</span>' : '') + (e && e.scenario && e.source ? ' <span class="sg-scenario">' + esc(e.source.section.split(' — ').pop().replace(/^[가-하]\.\s*/, '')) + '</span>' : '') + '</h2>' +
      '<p class="sg-lead">' + esc(lead) + '</p>' + renderLifecycle(model);
    if (model.state && model.state !== 'SUPPORTED') {
      var key = model.state === 'NOT_APPLICABLE' ? 'notApplicable' : model.state === 'GENERALLY_NOT_PERMITTED' ? 'notPermitted' : model.state === 'EXCEPTION_ONLY' ? 'exceptionOnly' : model.state === 'CONDITIONAL' ? 'conditional' : null;
      if (key) html += '<p class="sg-warn">' + stateBadge(lang, model.state) + ' ' + esc(tr(lang, key, { status: targetCode })) + '</p>';
    }
    if (e) html += '<p class="sg-summary">' + esc(L(lang, e, 'summary')) + '</p>';
    html += renderFacts(model) + answerActions(model);
    html += '</section>' + detailSections(model, step, bundle, state);
    return html;
  }

  function renderProcedure(model, step, bundle, state) {
    var lang = model.lang; var e = model.entry;
    var lead = model.status ? tr(lang, 'commonLeadWithStatus', { status: model.status }) : tr(lang, 'commonLead');
    var html = '<section class="sg-answer sg-common" aria-labelledby="sgAnswerTitle"><p class="sg-kicker">' + esc(tr(lang, 'commonKicker')) + '</p><h2 id="sgAnswerTitle" class="sg-answer-title" tabindex="-1">' + esc(model.procedureLabel) + '</h2><p class="sg-lead">' + esc(lead) + '</p>';
    if (e) html += '<p class="sg-summary">' + esc(L(lang, e, 'summary')) + '</p>';
    html += renderFacts(model) + renderReason(model, step, bundle);
    if (step.optionalStatus && model.registry) html += '<div class="sg-optional"><button type="button" class="sg-link" data-sg-action="ask-status">' + esc(tr(lang, 'optionalStatus')) + '</button><span class="sg-muted">' + esc(L(lang, model.registry, 'status_optional_note') || tr(lang, 'optionalStatusWhy')) + '</span></div>';
    html += answerActions(model);
    html += '</section>' + detailSections(model, step, bundle, state);
    return html;
  }

  function renderUnresolved(model, step, bundle, state) {
    var lang = model.lang;
    var html = '<section class="sg-answer sg-unresolved" aria-labelledby="sgAnswerTitle">' + renderAnswered(model, step, lang) + '<p class="sg-kicker">' + esc(model.procedureLabel) + '</p><h2 id="sgAnswerTitle" class="sg-answer-title" tabindex="-1">' + esc(tr(lang, 'unresolvedTitle')) + '</h2><p class="sg-lead">' + esc(tr(lang, 'unresolvedBody')) + '</p>' + renderLifecycle(model);
    html += '<h3>' + esc(tr(lang, 'candidates')) + '</h3><ul class="sg-candidates">' + (step.candidates || []).map(function (g) {
      var code = g.target ? g.target.split('~')[0] : ''; var info = bundle.codes[g.target] || bundle.codes[code] || {};
      var name = lang === 'en' ? (info.name_en || info.name_ko) : info.name_ko;
      var sec = g.source ? g.source.section : '';
      return '<li><button type="button" class="sg-candidate" data-sg-action="pick-target" data-sg-target="' + esc(targetKey(g)) + '"><span class="sg-code">' + esc(code) + '</span> ' + esc(name || '') + (sec ? '<small>' + esc(sec) + '</small>' : '') + '</button>' + (g.state ? stateBadge(lang, g.state) : '') + '</li>';
    }).join('') + '</ul></section>';
    html += renderTransition(model) + renderPrograms(model) + renderFees(model, bundle) + renderNext(model) + renderWaymaker(model, step) + renderEvidence(model, bundle, { open: true }) + renderRelated(model, bundle);
    return html;
  }

  function renderSourceOnly(model, step, bundle, state) {
    var lang = model.lang;
    var key = step.state === 'NOT_APPLICABLE' ? 'notApplicable' : step.state === 'GENERALLY_NOT_PERMITTED' ? 'notPermitted' : step.state === 'EXCEPTION_ONLY' ? 'exceptionOnly' : null;
    var html = '<section class="sg-answer sg-source-only" aria-labelledby="sgAnswerTitle">' + renderAnswered(model, step, lang) + '<p class="sg-kicker">' + esc(model.procedureLabel) + '</p><h2 id="sgAnswerTitle" class="sg-answer-title" tabindex="-1"><span class="sg-code">' + esc(model.status) + '</span>' + (model.statusName ? ' <span class="sg-name">' + esc(lang === 'en' ? (model.statusNameEn || model.statusName) : model.statusName) + '</span>' : '') + '</h2>' + renderLifecycle(model);
    if (key) html += '<p class="sg-warn">' + stateBadge(lang, step.state) + ' ' + esc(tr(lang, key, { status: model.status })) + '</p>';
    else html += '<p class="sg-lead">' + stateBadge(lang, step.state || 'SOURCE_ONLY') + ' ' + esc(tr(lang, 'sourceOnlyTitle')) + '</p><p>' + esc(tr(lang, 'sourceOnlyBody')) + '</p>';
    html += '</section>' + renderTransition(model) + renderPrograms(model) + (key ? '' : renderFees(model, bundle)) + renderNext(model) + renderWaymaker(model, step) + renderEvidence(model, bundle, { open: true }) + renderRelated(model, bundle);
    return html;
  }

  function renderProgram(step, state, bundle) {
    var lang = state.lang || 'ko'; var p = step.program;
    if (!p) return '';
    return '<section class="sg-answer" aria-labelledby="sgAnswerTitle"><p class="sg-kicker">' + esc(tr(lang, 'programTitle')) + '</p><h2 id="sgAnswerTitle" class="sg-answer-title" tabindex="-1">' + esc(LL(lang, { ko: p.name_ko, en: p.name_en })) + '</h2><p class="sg-lead">' + esc(L(lang, p, 'summary')) + '</p><p class="sg-muted">' + esc(tr(lang, 'dims')) + ': ' + esc((lang === 'en' ? p.dimensions_en : p.dimensions_ko).join(' · ')) + '</p><div class="sg-chips">' + p.codes.map(function (c) { return '<button type="button" class="sg-chip" data-sg-action="search" data-sg-value="' + esc(c) + '">' + esc(c) + '</button>'; }).join('') + '</div></section>' +
      '<section class="sg-evidence" aria-labelledby="sgEvidenceTitle"><details class="sg-evidence-details" id="sgEvidence" open><summary><h3 id="sgEvidenceTitle">' + esc(tr(lang, 'evidenceTitle')) + '</h3><span class="sg-muted">' + esc(tr(lang, 'evidenceCount', { n: 1 })) + '</span></summary><ol class="sg-evidence-list"><li class="sg-ev sg-ev-manual"><div class="sg-evidence-meta">' + esc(tr(lang, 'evidenceManual')) + ' · ' + esc(lang === 'en' ? 'Residence guide' : '외국인체류 안내매뉴얼') + ' · ' + esc(p.pdf_page) + tr(lang, 'page') + '</div><div class="sg-evidence-actions"><button type="button" class="sg-link" data-sg-action="open-page" data-sg-source="stay_manual_2026_09_18_pdf" data-sg-page="' + esc(p.pdf_page) + '">' + esc(tr(lang, 'open')) + '</button><a href="' + esc(p.file) + '#page=' + esc(p.pdf_page) + '" target="_blank" rel="noopener">' + esc(tr(lang, 'original')) + '</a></div></li></ol></details></section>';
  }

  // Source-backed examples of one document family across procedures (never a global default).
  function formExamples(bundle, family, lang) {
    var match = { passport: /^passport/, residence_proof: /residence|lease/, card: /^arc/ }[family] || /$^/;
    var seen = {}; var out = [];
    bundle.guidance.forEach(function (g) {
      (g.documents || []).forEach(function (d) {
        if (!match.test(d.ref) || d.ref === 'fee') return;
        var form = d.submission_form || 'SOURCE_DOES_NOT_SPECIFY';
        if (seen[form]) return; seen[form] = true;
        var proc = procedureMeta(bundle, g.procedure);
        out.push({ target: g.target === 'COMMON' ? (lang === 'en' ? 'common' : '공통') : g.target.split('~')[0], procedure: proc ? (lang === 'en' ? proc.en : proc.ko) : g.procedure, form: form === 'SOURCE_DOES_NOT_SPECIFY' ? tr(lang, 'formNoMark') : (formLabel(lang, d) || tr(lang, 'forms')[form]), name: lang === 'en' ? d.name_en : d.name_ko });
      });
    });
    return out.slice(0, 4);
  }
  function gksFeeNote(bundle, lang) {
    var ext = (bundle.fees || []).filter(function (f) { return f.id === 'extension_general'; })[0];
    var card = (bundle.fees || []).filter(function (f) { return f.id === 'card_reissue'; })[0];
    if (!ext || !card) return '';
    return tr(lang, 'gksFeeNote', { exempt: tr(lang, 'gksExemptPart'), notExempt: tr(lang, 'gksNotExemptPart') });
  }
  function renderNoStatus(step, state, lang, bundle) {
    var html = '<section class="sg-answer sg-no-status" aria-labelledby="sgAnswerTitle"><h2 id="sgAnswerTitle" class="sg-answer-title" tabindex="-1">' + esc(tr(lang, 'noStatus')) + '</h2><p class="sg-lead">' + esc(tr(lang, 'noStatusBody')) + '</p>';
    if (step.hint === 'passport_reissue') html += '<p class="sg-warn">' + esc(tr(lang, 'passportHint')) + '</p>';
    if (step.hint === 'form_varies' && bundle) {
      var ex = formExamples(bundle, step.hintObject, lang);
      html += '<div class="sg-premise"><p class="sg-warn">' + esc(tr(lang, 'formVaries')) + '</p>' + (ex.length ? '<ul class="sg-notes">' + ex.map(function (e) { return '<li><span class="sg-code">' + esc(e.target) + '</span> ' + esc(e.procedure) + ' — ' + esc(e.name) + ': <strong>' + esc(e.form) + '</strong></li>'; }).join('') + '</ul>' : '') + '<p class="sg-muted">' + esc(tr(lang, 'formVariesAsk')) + '</p></div>';
    }
    if (step.office && bundle && bundle.local_practice) {
      var lp = bundle.local_practice; var officeName = lang === 'en' ? step.office.name_en : step.office.name_ko;
      var vars = (lp.variations || []).filter(function (v) { return v.office === step.office.id; });
      html += '<div class="sg-premise"><p class="sg-warn">' + esc(tr(lang, 'localPremise')) + '</p>' + (vars.length ? '<ul class="sg-local-list">' + vars.map(function (v) { return '<li class="sg-local-item"><details><summary>' + layerBadge(lang, v.layer) + ' <span>' + esc(L(lang, v, 'summary')) + '</span></summary><p>' + esc(L(lang, v, 'detail')) + '</p><p class="sg-muted">' + esc(tr(lang, 'localBaseline')) + ': ' + esc(L(lang, v, 'national_baseline')) + '</p></details></li>'; }).join('') + '</ul>' : '<p class="sg-muted">' + esc(tr(lang, 'localPremiseNone', { office: officeName })) + '</p>') + '</div>';
    }
    if (state.interp && state.interp.userProgram === 'gks' && state.interp.facet === 'fee' && bundle) html += '<p class="sg-warn">' + esc(gksFeeNote(bundle, lang)) + '</p>';
    html += '<p class="sg-editor-label">' + esc(tr(lang, 'noStatusTry')) + '</p><div class="sg-chips">' + COMMON_TASKS.map(function (t) { return '<button type="button" class="sg-chip" data-sg-action="search" data-sg-value="' + esc(t[0]) + '">' + esc(lang === 'en' ? t[1] : t[0]) + '</button>'; }).join('') + '</div>';
    html += '<form class="sg-code-form" data-sg-form="code"><label class="sg-sr" for="sgCodeInput">' + esc(tr(lang, 'searchCode')) + '</label><input id="sgCodeInput" type="text" inputmode="text" autocomplete="off" placeholder="F-6-1" maxlength="12"><button type="submit" class="sg-btn">' + esc(tr(lang, 'searchCode')) + '</button></form></section>';
    html += renderWaymaker({ lang: lang, status: null, procedure: null }, step);
    return html;
  }

  function renderDisclaimer(lang) {
    return '<div class="sg-disclaimer"><p>' + esc(tr(lang, 'disclaimer')) + ' <details class="sg-disclaimer-more"><summary>' + esc(tr(lang, 'disclaimerMore')) + '</summary><ul>' + tr(lang, 'disclaimerDetail').map(function (t) { return '<li>' + esc(t) + '</li>'; }).join('') + '</ul></details></p></div>';
  }

  function renderModel(step, state, bundle) {
    var lang = state.lang || 'ko';
    var model = compose(step, state, bundle);
    var html = renderInterpretation(model, state, bundle);
    var quick = null;
    var QA = root.VisableQuickAnswer;
    var wantQuick = !!(state.interp && state.interp.isQuestion) || !!state.quick;
    if (QA && typeof QA.build === 'function' && wantQuick && step.kind !== 'program' && step.kind !== 'no-status') {
      try { quick = QA.build({ step: step, model: model, state: state, bundle: bundle, lang: lang, helpers: { tr: tr, esc: esc, won: won, feeSummary: feeSummary, formLabel: formLabel, parentOf: parentOf } }); } catch (e) { quick = null; }
    }
    if (quick && quick.html) html += quick.html;
    var body = '';
    if (step.kind === 'question') body = renderQuestion(step, model, state);
    else if (step.kind === 'need-status') body = renderNeedStatus(step, model, state, bundle);
    else if (step.kind === 'resolved') body = renderAnswer(model, step, bundle, state);
    else if (step.kind === 'procedure') body = renderProcedure(model, step, bundle, state);
    else if (step.kind === 'unresolved') body = renderUnresolved(model, step, bundle, state);
    else if (step.kind === 'source-only') body = renderSourceOnly(model, step, bundle, state);
    else if (step.kind === 'program') body = renderProgram(step, state, bundle);
    else if (step.kind === 'no-status') body = renderNoStatus(step, state, lang, bundle);
    if (quick && quick.collapsesDetail) {
      var open = !!state.fullOpen;
      html += '<div class="sg-full" id="sgFull"' + (open ? '' : ' hidden') + '>' + body + '</div>';
    } else html += body;
    html += renderDisclaimer(lang);
    model.quick = quick ? quick.model : null;
    return { html: html, model: model };
  }

  var api = { STR: STR, normalizeCode: normalizeCode, interpret: interpret, nextStep: nextStep, compose: compose, renderModel: renderModel, groupDocuments: groupDocuments, applicableOverlays: applicableOverlays, candidateEntries: candidateEntries, feesFor: feesFor, exemptionApplies: exemptionApplies, evidenceFor: evidenceFor, localPracticeFor: localPracticeFor, registryFor: registryFor, commonEntry: commonEntry, formLabel: formLabel, preparation: preparation, preparationLabel: preparationLabel, feeSummary: feeSummary, uniqueNotes: uniqueNotes, sameNote: sameNote, tierOverlays: tierOverlays, manualTitle: manualTitle, PROCEDURE_ORDER: PROCEDURE_ORDER, esc: esc, parentOf: parentOf, tr: tr, won: won };
  root.VisableStatusGuidance = api;

  /* ------------------------------------------------------------------ DOM -- */
  if (typeof document === 'undefined') return;

  var bundle = null, loadPromise = null, host = null, state = null, lastQuery = '';
  // The structured guidance exists in Korean and English. Korean readers get
  // Korean; every other locale gets English rather than untranslated Korean.
  function lang() { var l = String(document.documentElement.lang || 'ko').toLowerCase(); return l === 'ko' || l.indexOf('ko-') === 0 ? 'ko' : 'en'; }
  function track(event, props) { try { if (root.PARADISO_ANALYTICS && typeof root.PARADISO_ANALYTICS.track === 'function') root.PARADISO_ANALYTICS.track(event, props || {}); } catch (e) { /* analytics never breaks guidance */ } }
  function load() {
    if (bundle) return Promise.resolve(bundle);
    if (loadPromise) return loadPromise;
    loadPromise = fetch('data/status-guidance-202609.json').then(function (r) { if (!r.ok) throw new Error('HTTP ' + r.status); return r.json(); }).then(function (b) {
      bundle = b;
      // Local practice is optional: the national baseline never waits for it.
      return fetch('data/local-practice-202609.json').then(function (r) { return r.ok ? r.json() : null; }).catch(function () { return null; }).then(function (lp) { if (lp) bundle.local_practice = lp; return bundle; });
    }).catch(function (e) { loadPromise = null; throw e; });
    return loadPromise;
  }
  function ensureHost() {
    if (host && host.isConnected) return host;
    host = document.getElementById('statusGuidance');
    if (!host) {
      host = document.createElement('section');
      host.id = 'statusGuidance'; host.className = 'sg'; host.setAttribute('aria-labelledby', 'sgHeading');
      // The one primary result renderer: always first in the result area.
      var main = document.getElementById('mainContent');
      if (main) main.prepend(host);
    }
    return host;
  }
  function storageKey(q) { return 'visable.sg.' + q; }
  function saveState() { try { sessionStorage.setItem(storageKey(state.query), JSON.stringify({ answers: state.answers, procedure: state.procedure, status: state.status, history: state.history, variant: state.variant || null, office: state.office || null, fullOpen: !!state.fullOpen, askStatus: !!state.askStatus })); } catch (e) { /* ignore */ } }
  function restoreState(q) { try { var raw = sessionStorage.getItem(storageKey(q)); return raw ? JSON.parse(raw) : null; } catch (e) { return null; } }
  function snapshot() { return { answers: JSON.parse(JSON.stringify(state.answers)), procedure: state.procedure, status: state.status, variant: state.variant || null, askStatus: !!state.askStatus }; }

  var lastKind = null;
  // Procedure-first results and the legacy per-status list below them.
  // The legacy renderer auto-expands every matching card, which is fine for a
  // status query (one card) but not for a status-independent procedure or a
  // status prompt: "체류기간 연장" matches all 40 statuses and 40 expanded cards
  // are ~100k px on a phone (WebKit refuses to even screenshot it). For those two
  // kinds the cards are context, not the answer, so they start collapsed; every
  // header stays tappable and the compact summary above them is untouched.
  var legacyDirty = true;
  function collapseLegacyList(kind) {
    var cards = document.querySelectorAll('#rlist article.vc');
    if ((kind !== 'procedure' && kind !== 'need-status') || cards.length < 2) { document.body.removeAttribute('data-sg-legacy'); return; }
    // Snap closed without the card's open/close transition: the list was just
    // rendered expanded, and animating 15–40 cards shut is a visible jump on a
    // phone (and a 40k px page for the duration of the transition).
    var list = cards[0].parentElement;
    if (list) list.classList.add('sg-legacy-snap');
    cards.forEach(function (c) { c.classList.remove('open'); });
    document.body.setAttribute('data-sg-legacy', 'collapsed');
    if (list) { void list.offsetHeight; requestAnimationFrame(function () { requestAnimationFrame(function () { list.classList.remove('sg-legacy-snap'); }); }); }
  }

  function render(focusTarget) {
    var h = ensureHost();
    if (!state) { h.innerHTML = ''; return; }
    state.lang = lang();
    var step = nextStep(state, bundle);
    var out = renderModel(step, state, bundle);
    h.innerHTML = '<h2 id="sgHeading" class="sg-sr">' + esc(tr(state.lang, 'answerTitle')) + '</h2>' + out.html;
    // Content language of the block; on an RTL page the Korean/English guidance keeps LTR order.
    h.setAttribute('lang', state.lang);
    if (document.documentElement.dir === 'rtl') h.setAttribute('dir', 'ltr'); else h.removeAttribute('dir');
    document.body.setAttribute('data-sg-state', 'ready');
    h.setAttribute('data-sg-kind', step.kind);
    h.setAttribute('data-sg-quick', out.model.quick ? out.model.quick.mode : 'none');
    document.body.setAttribute('data-sg-kind', step.kind);
    if (legacyDirty || lastKind !== step.kind) { collapseLegacyList(step.kind); legacyDirty = false; }
    saveState();
    if (focusTarget) {
      var f = h.querySelector('#sgQuickTitle, #sgQuestionTitle, #sgAnswerTitle');
      if (f) { try { f.focus({ preventScroll: false }); } catch (e) { f.focus(); } }
    }
    if (lastKind !== step.kind) {
      if (step.kind === 'procedure' && !state.status) track('procedure_only_result', { procedure: step.procedure });
      if (out.model.quick) track(out.model.quick.mode === 'clarify' ? 'waymaker_clarification_shown' : 'waymaker_quick_answer_shown', { procedure: step.procedure || null, kind: step.kind });
      if (step.kind === 'source-only' || step.kind === 'unresolved') track('structured_fallback_used', { kind: step.kind });
    }
    lastKind = step.kind;
    if (root.VisableQuickAnswer && typeof root.VisableQuickAnswer.afterRender === 'function' && out.model.quick) root.VisableQuickAnswer.afterRender(h, out.model, state, bundle);
    document.dispatchEvent(new CustomEvent('visable:guidance-rendered', { detail: { query: state.query, kind: step.kind, target: step.target || null, procedure: step.procedure || null, quick: out.model.quick ? out.model.quick.mode : null, evidenceIntent: evidenceIntent(out.model, bundle) } }));
  }
  /* Evidence query, separate from the answer query: the raw-source search ranks
   * pages by the interpreted status + procedure, the status chapter and the pages
   * the structured answer cites — not by the words the user typed. */
  function evidenceIntent(model, bundle) {
    if (!model || (!model.status && !model.procedure)) return null;
    var parent = model.status ? parentOf(model.status) : null;
    var chapters = {};
    if (parent) Object.keys(bundle.chapters || {}).forEach(function (mid) { var c = bundle.chapters[mid][parent]; var src = bundle.sources[mid]; if (c && src && src.corpus_source_id) chapters[src.corpus_source_id] = [c.pdf_start, c.pdf_end]; });
    var anchors = (model.evidence || []).filter(function (e) { return e.type === 'manual' && e.corpusId && e.kind !== 'fee'; }).map(function (e) { return { source: e.corpusId, page: Number(e.page) }; });
    var proc = model.procedure ? procedureMeta(bundle, model.procedure) : null;
    return { status: model.status || null, procedure: model.procedure || null, chapters: chapters, anchors: anchors, domain: proc ? (proc.domain === 'visa' ? 'visa_issuance' : 'stay') : null };
  }
  function start(query) {
    query = String(query || '').trim();
    if (!query) { state = null; if (host) host.innerHTML = ''; return; }
    var h = ensureHost();
    lastQuery = query;
    h.innerHTML = '<p class="sg-load" role="status">' + esc(tr(lang(), 'loading')) + '</p>';
    document.body.setAttribute('data-sg-state', 'loading');
    load().then(function () {
      if (lastQuery !== query) return;
      var interp = interpret(query, bundle);
      var saved = restoreState(query);
      state = { query: query, interp: interp, answers: saved ? saved.answers : {}, procedure: saved ? saved.procedure : null, status: saved ? saved.status : null, history: saved ? (saved.history || []) : [], variant: saved ? saved.variant : null, office: saved ? saved.office : null, fullOpen: saved ? !!saved.fullOpen : false, askStatus: saved ? !!saved.askStatus : false, editing: false, lang: lang() };
      if (!state.office && interp.office) state.office = interp.office.id;
      lastKind = null;
      render(false);
    }).catch(function () {
      if (lastQuery !== query) return;
      h.innerHTML = '<div class="sg-failed" role="status"><p>' + esc(tr(lang(), 'failed')) + '</p><button type="button" class="sg-btn" data-sg-action="retry">' + esc(tr(lang(), 'retry')) + '</button></div>';
      // Only when the structured layer cannot load does the legacy list come back as the fallback.
      document.body.setAttribute('data-sg-state', 'failed');
    });
  }
  function submitSearch(value) {
    var input = document.getElementById('civicQuery') || document.getElementById('q');
    var q = document.getElementById('q');
    if (q) q.value = value;
    if (typeof executeSearch === 'function' && q) { executeSearch(); }
    else if (input) { input.value = value; var form = input.closest('form'); if (form) form.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true })); }
  }
  function currentModel() { if (!state || !bundle) return null; var step = nextStep(state, bundle); return { step: step, model: compose(step, state, bundle) }; }
  document.addEventListener('click', function (event) {
    var btn = event.target.closest('[data-sg-action]');
    if (!btn || !host || !host.contains(btn)) return;
    var action = btn.getAttribute('data-sg-action');
    if (action === 'retry') { start(lastQuery); return; }
    if (!state) return;
    if (action === 'answer') {
      var dim = btn.getAttribute('data-sg-dim'); var val = btn.getAttribute('data-sg-value');
      state.history.push(snapshot());
      state.variant = null;
      if (dim === '__procedure') state.procedure = val;
      else if (dim === '__alias') { state.answers.__alias = val; if (val !== 'unsure') { var o = state.interp.aliasQuestion.options.filter(function (x) { return x.id === val; })[0]; if (o) state.status = o.targets[0]; } }
      else if (dim === '__status') { state.answers.__status = val; if (val !== 'unsure') { var so = bundle.status_prompt.options.filter(function (x) { return x.id === val; })[0]; if (so && so.targets.length === 1) state.status = so.targets[0]; } }
      else if (dim === '__status2') { if (val !== 'unsure') state.status = val; else state.answers.__status = 'unsure'; }
      else state.answers[dim] = val;
      render(true); return;
    }
    if (action === 'back') { var prev = state.history.pop(); if (prev) { state.answers = prev.answers; state.procedure = prev.procedure; state.status = prev.status; state.variant = prev.variant || null; state.askStatus = !!prev.askStatus; } render(true); return; }
    if (action === 'reopen') { var d = btn.getAttribute('data-sg-dim'); state.history.push(snapshot()); delete state.answers[d]; if (d === 'current_status') delete state.answers.current_status; render(true); return; }
    if (action === 'edit') { state.editing = !state.editing; render(false); if (state.editing) { var inp = host.querySelector('#sgCodeInput'); if (inp) inp.focus(); } return; }
    if (action === 'set-procedure') { state.history.push(snapshot()); state.procedure = btn.getAttribute('data-sg-value'); state.editing = false; render(true); return; }
    if (action === 'ask-status') { state.history.push(snapshot()); state.askStatus = true; delete state.answers.__status; render(true); return; }
    if (action === 'pick-target') {
      var t = btn.getAttribute('data-sg-target'); var base = baseTarget(t);
      var fam = bundle.families[parentOf(base.split('~')[0])];
      state.history.push(snapshot());
      if (fam) fam.dimensions.forEach(function (dm) { dm.options.forEach(function (o) { if (o.targets.indexOf(t) >= 0 || o.targets.indexOf(base) >= 0) state.answers[dm.id] = o.id; }); });
      if (isSubcode(base) && base.indexOf('~') < 0) state.status = base;
      render(true); return;
    }
    if (action === 'pick-variant') { state.history.push(snapshot()); state.variant = btn.getAttribute('data-sg-target'); render(true); return; }
    if (action === 'search') { submitSearch(btn.getAttribute('data-sg-value')); return; }
    if (action === 'open-page') {
      var src = btn.getAttribute('data-sg-source'); var pg = Number(btn.getAttribute('data-sg-page'));
      if (window.VisableCivicSearch && typeof window.VisableCivicSearch.openPage === 'function') window.VisableCivicSearch.openPage(src, pg, btn);
      return;
    }
    if (action === 'manual-tab') { var raw = document.getElementById('civicRawSources'); if (raw) { raw.open = true; var rs = raw.querySelector('summary'); if (rs) { raw.scrollIntoView({ block: 'start', behavior: 'smooth' }); rs.focus(); } } return; }
    if (action === 'jump-docs') { event.preventDefault(); var dt = host.querySelector('#sgDocsTitle'); if (dt) { dt.scrollIntoView({ block: 'start', behavior: 'smooth' }); try { dt.focus({ preventScroll: true }); } catch (e) { dt.focus(); } } return; }
    // The legacy per-status card is not part of the normal result; it opens only on this explicit request.
    if (action === 'legacy-card') { document.body.setAttribute('data-legacy-card', 'open'); var card = document.querySelector('#rlist article.vc'); if (card) { card.classList.add('open'); card.scrollIntoView({ block: 'start', behavior: 'smooth' }); var hd = card.querySelector('.vc-h'); if (hd) hd.setAttribute('tabindex', '-1'), hd.focus(); } return; }
    if (action === 'toggle-full') { state.fullOpen = !state.fullOpen; render(false); track('quick_answer_full_detail', { open: state.fullOpen }); var full = host.querySelector('#sgFull'); if (state.fullOpen && full) { var ft = full.querySelector('#sgAnswerTitle, #sgQuestionTitle'); if (ft) { try { ft.focus({ preventScroll: false }); } catch (e) { ft.focus(); } } } return; }
    if (action === 'show-evidence') { state.fullOpen = true; state.evidenceOpen = true; render(false); var ev = host.querySelector('#sgEvidence'); if (ev) { ev.open = true; ev.scrollIntoView({ block: 'start', behavior: 'smooth' }); var s = ev.querySelector('summary'); if (s) { s.setAttribute('tabindex', '-1'); s.focus(); } } return; }
    if (action === 'report') { event.preventDefault(); var cm = currentModel(); track('local_report_started', { procedure: cm && cm.model.procedure }); document.dispatchEvent(new CustomEvent('visable:local-report', { detail: { query: state.query, procedure: cm ? cm.model.procedure : null, status: cm ? cm.model.status : null, office: state.office || null, lang: lang() } })); return; }
    if (action === 'followup') {
      var cm2 = currentModel();
      track('ai_followup_started', { procedure: cm2 && cm2.model.procedure });
      if (root.VisableQuickAnswer && typeof root.VisableQuickAnswer.handoff === 'function' && cm2) { try { if (root.VisableQuickAnswer.handoff(cm2.model, state, bundle) === false) return; event.preventDefault(); return; } catch (e) { /* fall through to the plain link */ } }
      return;
    }
  });
  document.addEventListener('change', function (event) {
    var sel = event.target.closest && event.target.closest('[data-sg-office]');
    if (!sel || !state || !host || !host.contains(sel)) return;
    state.office = sel.value || null;
    track('office_variation_opened', { office: state.office });
    render(false);
    var pick = host.querySelector('#sgOffice'); if (pick) pick.focus();
  });
  document.addEventListener('toggle', function (event) {
    var el = event.target;
    if (!state || !host || !el || !host.contains(el)) return;
    if (el.matches && el.matches('.sg-fee-details') && el.open) track('fee_opened', {});
    if (el.matches && el.matches('.sg-doc-details') && el.open) track('document_form_detail_opened', {});
    if (el.matches && el.matches('.sg-evidence-details')) state.evidenceOpen = el.open;
  }, true);
  document.addEventListener('submit', function (event) {
    var form = event.target.closest && event.target.closest('[data-sg-form="code"]');
    if (!form || !state) return;
    event.preventDefault();
    var val = form.querySelector('input').value.trim();
    var n = normalizeCode(val, bundle.codes);
    if (typeof n === 'string') { state.history.push(snapshot()); state.status = n; state.answers = {}; state.editing = false; state.askStatus = false; render(true); }
    else { form.querySelector('input').setAttribute('aria-invalid', 'true'); }
  });
  document.addEventListener('paradiso:results-rendered', function (event) { legacyDirty = true; document.body.removeAttribute('data-legacy-card'); var q = event.detail && event.detail.query; if (state && bundle && String(q || '').trim() === state.query && lastQuery === state.query) { render(false); return; } start(q); });
  document.addEventListener('paradiso:landing-reset', function () { state = null; lastQuery = ''; if (host) host.innerHTML = ''; document.body.removeAttribute('data-sg-kind'); document.body.removeAttribute('data-sg-legacy'); document.body.removeAttribute('data-sg-state'); document.body.removeAttribute('data-legacy-card'); });
  window.addEventListener('paradiso-language-applied', function () { if (state && bundle) render(false); });
  if (document.body.classList.contains('searched')) { var q0 = document.getElementById('q'); if (q0 && q0.value) start(q0.value); }
})(typeof globalThis !== 'undefined' ? globalThis : this);
