// Strings the post-search guidance renders today. Source of truth:
// assets/js/status-guidance.js `STR` table (ko: lines 34-102, en: 103-170 at
// commit 5082d9d). STR has ko and en only; `lang()` (line 1595) maps every
// non-Korean document language to en, so the 13 other UI languages see the
// English guidance. Verified against the rendered page on 2026-11-03
// (docs/rebuild/phase0-inventory.md). Templates keep their {placeholders}.
export const GUIDANCE_STR = {
  ko: {
    answerTitle: '안내',
    interpLabel: '검색 해석',
    edit: '수정',
    askProcedure: '{status}에서 무엇을 하려고 하세요?',
    askProcedureHint: '절차에 따라 필요한 서류와 조건이 달라요.',
    exact: '{target} 기준으로 안내해요.',
    commonKicker: '공통 절차',
    commonLead: '체류자격과 관계없이 같은 기준이 적용돼요.',
    understoodProcOnly: '{procedure}(으)로 이해했어요',
    docsTitle: '준비할 서류',
    docsCount: '필수 {n}개',
    docsCountCond: '조건부 {n}개',
    grpRequired: '필수',
    grpConditional: '조건부',
    officer: '심사 과정에서 추가 서류가 요청되거나 일부 서류가 생략될 수 있습니다.',
    feeTitle: '비용 / 납부',
    feeNonRefundable: '심사수수료이므로 접수 후 반환되지 않아요.',
    instruments: { REVENUE_STAMP: '정부수입인지', CASH_OR_CASH_RECEIPT: '현금 또는 현금 납입 증표', CARD: '신용·직불카드', ELECTRONIC_PAYMENT: '전자결제', REVENUE_CERTIFICATE_STAMP: '수입증지' },
    feeReview: { VERIFIED_REGULATION: '시행규칙 기준' },
    overviewTitle: '한눈에 보기',
    ovFee: '수수료 {amount} · {review}',
    ovDocs: '필수 서류 {n}개',
    ovReview: '참고용 안내예요 · 신청 전 공식 원문을 확인하세요',
    ovBasis: '기준일 {date} · 공식 근거 {n}건',
    evidenceTitle: '공식 근거',
    evidenceShow: '근거 보기',
    nextTitle: '다음 할 일',
    nextDocs: '준비 서류 {n}개 보기',
    unknownCode: '{code}은(는) 현재 기준 자료({edition}판)에서 확인되지 않는 코드예요. 오타가 아닌지 확인하거나 상위 코드로 검색해 보세요.',
    noStatus: '무엇을 찾으시는지 조금 더 알려주세요',
    failed: '안내를 불러오지 못했어요. 아래 원문 검색은 그대로 사용할 수 있어요.',
    retry: '다시 시도',
    disclaimer: '공식 자료를 바탕으로 정리한 참고 안내예요. 법률 상담이나 민원 대행이 아니며, 최종 판단은 관할 기관에서 이루어집니다.',
    disclaimerMore: '안내 기준 보기',
    chipLegend: '원문 확인 표시는 아직 정리된 안내가 없어 공식 원문 해당 쪽으로 안내한다는 뜻이에요.',
    wmTitle: '내 상황이 조금 다르다면',
    wmCta: 'Waymaker로 이어서 보기'
  },
  en: {
    answerTitle: 'Guidance',
    interpLabel: 'Search interpreted as',
    edit: 'Edit',
    askProcedure: 'What do you want to do with {status}?',
    askProcedureHint: 'Documents and conditions depend on the procedure.',
    docsTitle: 'Documents to prepare',
    docsCount: '{n} required',
    docsCountCond: '{n} conditional',
    feeTitle: 'Fee / payment',
    disclaimer: 'Reference guidance compiled from official sources — not legal advice and not an application agency. The final decision is made by the competent office.',
    disclaimerMore: 'How this guidance is compiled',
    wmTitle: 'If your situation is different',
    wmCta: 'Continue in Waymaker'
  }
};
export const fill = (tpl, vars) => String(tpl).replace(/\{(\w+)\}/g, (m, k) => (vars[k] == null ? m : String(vars[k])));
// '2026.11' → '2026년 11월' as rendered in the unknown-code notice ("2026년 11월판").
export const editionKo = (edition) => { const [y, m] = String(edition).split('.'); return `${y}년 ${Number(m)}월`; };

// Strings the legacy per-status result card (index.html `renderResults` and the
// procedure renderers) hard-codes in source rather than reading from the i18n packs.
// Recorded from index.html at commit 1c7fb16 (line numbers in comments) and verified
// against the rendered card on 2026-11-03 (tests/golden/specs/legacy-card.spec.mjs).
export const LEGACY_CARD_STR = {
  // paradisoCanonicalAppFormText(): every "통합신청서 …" document row is rewritten to this (index.html:17979).
  canonicalAppForm: '통합신청서 (신고서) [별지 제34호서식]',
  // Fee tile heading inside a procedure panel (index.html:17680; ko / en / zh-CN literals).
  feeTile: { ko: '공통 수수료 참고', en: 'Common fee reference' },
  // Status-guidance "Next steps" row that opens this card (assets/js/status-guidance.js `nextLegacy`, lines 73 / 142).
  openLegacy: { ko: '기존 체류자격 카드 보기', en: 'Open the existing status card' }
};
