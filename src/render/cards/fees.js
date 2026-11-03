// @ts-nocheck
/**
 * Procedure fee helpers of the legacy result card (structure map C13: fee-info lookup and the fee box renderer).
 * Kept inline in index.html: `PROCEDURE_CONFIG` (read by bare name from src/docs/normalize.js, src/render/cards/*.js and
 * assets/js/visa-route-guide.js) and `STAY_FEE_SOURCE_NOTE` (read by inline code). This module reads them by bare name
 * (global lexical scope) and uses tx(), escapeHtml(), docGuideData (inline `let`, typeof-guarded) and Visable.docs stubs
 * at call time only (compatibility surface, ADR-009). Covered by tests/golden/specs/legacy-card.spec.mjs (fee tile).
 * Moved verbatim from index.html lines 17513-17692 (145 lines; kept inline: ['COMMON_MANUAL_WARNINGS', 'PROCEDURE_CONFIG', 'STAY_FEE_SOURCE_NOTE']).
 * Exposed on window.Visable.cards; 2 inline stubs with the same names delegate here.
 */


// 외국인등록증·영주증 등 실물 신분증은 방문 수령 시 발급/재발급 수수료(35,000원,
// 시행규칙 제72조제10·10의2호)만 들지만, 등기우편으로 수령할 경우 우편요금이
// 추가됩니다(총 39,000원 = 35,000원 + 4,000원). 카드 수수료가 표시되는 모든
// 체류자격 절차에 공통 적용되도록 렌더링 단계에서 일괄 반영합니다.
const CARD_DELIVERY_SURCHARGE = 4000;
const DEFAULT_PROCEDURE_FEES = {
    activitiesOutsideStatus: {
        label: '체류자격 외 활동허가',
        revenueStamp: 120000,
        notes: ['정부수입인지 120,000원']
    },
    workplaceChange: {
        label: '근무처 변경·추가',
        revenueStamp: 120000,
        notes: ['정부수입인지 120,000원', '신고 민원 또는 개별 특례는 면제될 수 있어 관할 관서 확인이 필요합니다.']
    },
    statusGrant: {
        label: '체류자격 부여',
        revenueStamp: 80000,
        notes: ['정부수입인지 80,000원']
    },
    statusChange: {
        label: '체류자격 변경허가',
        revenueStamp: 100000,
        notes: ['정부수입인지 100,000원']
    },
    extension: {
        label: '체류기간 연장허가',
        revenueStamp: 60000,
        notes: ['정부수입인지 60,000원']
    },
    registration: {
        label: '외국인등록',
        revenueStamp: 0,
        cardIssueFee: 35000,
        notes: ['외국인등록증 발급 및 재발급 수수료 35,000원']
    },
    reentry: {
        label: '재입국허가',
        revenueStamp: null,
        notes: ['단수 재입국허가 30,000원', '복수 재입국허가 50,000원']
    }
};

function formatWon(amount) {
    if (typeof amount !== 'number') return '';
    return currentLanguage === 'zh-CN' ? `${amount.toLocaleString('en-US')} 韩元` : currentLanguage === 'en' ? `KRW ${amount.toLocaleString('en-US')}` : `${amount.toLocaleString('ko-KR')}원`;
}

function getProcedureFeeInfo(v, procedureKey) {
    const raw = v.procedures && v.procedures[procedureKey] ? v.procedures[procedureKey] : {};
    if (raw && raw.feeInfo) return raw.feeInfo;
    const base = DEFAULT_PROCEDURE_FEES[procedureKey];
    if (!base) return null;
    const fee = { ...base, commonReference: true, notes: [...(base.notes || [])] };
    if (procedureKey === 'statusChange' && v.code === 'F-5') {
        fee.revenueStamp = 200000;
        fee.notes = ['영주(F-5) 자격 변경허가 정부수입인지 200,000원'];
        fee.commonReference = false;
    }
    // 출입국관리법 시행규칙 제72조: 결혼이민(F-6) 4만원 예외는 제4호 '체류자격 부여'에만 있음.
    // 변경허가는 제5호(10만원, 예외는 영주 F-5뿐)이므로 F-6 예외를 부여(statusGrant)로 정정.
    if (procedureKey === 'statusGrant' && v.code === 'F-6') {
        fee.revenueStamp = 40000;
        fee.notes = ['결혼이민(F-6) 체류자격 부여 정부수입인지 40,000원 (시행규칙 제72조제4호)'];
        fee.commonReference = false;
    }
    if (procedureKey === 'extension' && v.code === 'F-6') {
        fee.revenueStamp = 30000;
        fee.notes = ['결혼이민(F-6) 체류기간 연장허가 정부수입인지 30,000원'];
        fee.commonReference = false;
    }
    // 영주(F-5)는 체류기간 상한이 없어 '체류기간 연장(시행규칙 제72조제6호, 6만원)'
    // 대상이 아닙니다. 기본 연장 수수료가 오인되지 않도록, 영주증(영주카드) 재발급
    // 수수료(시행규칙 제72조제10의2호, 35,000원)로 정정합니다.
    if (procedureKey === 'extension' && v.code === 'F-5') {
        fee.label = currentLanguage === 'zh-CN' ? '永住证补发' : currentLanguage === 'en' ? 'Permanent residence card reissuance' : '영주증 재발급';
        fee.revenueStamp = 0;
        fee.cardIssueFee = 35000;
        fee.notes = currentLanguage === 'zh-CN'
            ? [
                '永住（F-5）没有居留期限上限，因此不属于“居留期限延长”对象。',
                '永住证（永住卡）有效期为 10 年，须在到期前补发（逾期可能被处以罚款）。',
                '永住证补发手续费 35,000 韩元（出入境管理法施行规则第 72 条第 10 之 2 号）。'
            ]
            : currentLanguage === 'en'
            ? [
                'Permanent residence (F-5) has no stay-period limit, so it is not subject to "extension of stay".',
                'The permanent residence card is valid for 10 years and must be reissued before it expires (a late reissuance may incur a fine).',
                'Permanent residence card reissuance fee: KRW 35,000 (Enforcement Rule Art. 72, item 10-2).'
            ]
            : [
                '영주(F-5)는 체류기간 상한이 없어 ‘체류기간 연장’ 대상이 아닙니다.',
                '영주증(영주카드) 유효기간은 10년이며 만료 전 재발급해야 합니다(기간 도과 시 과태료).',
                '영주증 재발급 수수료 35,000원 (출입국관리법 시행규칙 제72조제10의2호)'
            ];
        fee.commonReference = false;
    }
    return fee;
}

function renderProcedureFeeBox(feeInfo) {
    if (!feeInfo) return '';
    const amountBits = [];
    if (typeof feeInfo.revenueStamp === 'number' && feeInfo.revenueStamp > 0) amountBits.push(`${currentLanguage === 'zh-CN' ? '收入印花' : currentLanguage === 'en' ? 'revenue stamp' : '수입인지'} ${formatWon(feeInfo.revenueStamp)}`);
    if (feeInfo.revenueStamp === 0) amountBits.push(currentLanguage === 'zh-CN' ? '无收入印花' : currentLanguage === 'en' ? 'no revenue stamp' : '수입인지 없음');
    const hasCardFee = typeof feeInfo.cardIssueFee === 'number' && feeInfo.cardIssueFee > 0;
    if (hasCardFee) {
        const visitFee = formatWon(feeInfo.cardIssueFee);
        const mailFee = formatWon(feeInfo.cardIssueFee + CARD_DELIVERY_SURCHARGE);
        amountBits.push(currentLanguage === 'zh-CN'
            ? `登录证 ${visitFee}（挂号邮寄领取时 ${mailFee}）`
            : currentLanguage === 'en'
            ? `card ${visitFee} (${mailFee} by registered mail)`
            : `등록증 ${visitFee} (등기우편 수령 시 ${mailFee})`);
    }
    const amountText = amountBits.length ? amountBits.join(' · ') : (currentLanguage === 'zh-CN' ? '金额需确认' : currentLanguage === 'en' ? 'Amount needs confirmation' : '금액 확인 필요');
    const baseNotes = Array.isArray(feeInfo.notes) ? feeInfo.notes : [];
    // 등기우편 수령 우편요금 안내는 카드 수수료가 있는 모든 절차/자격에 공통 부가.
    const cardDeliveryNote = hasCardFee
        ? (currentLanguage === 'zh-CN'
            ? `登录证·永住证现场领取时为 ${formatWon(feeInfo.cardIssueFee)}；若选择挂号邮寄领取，则另加邮费 ${formatWon(CARD_DELIVERY_SURCHARGE)}，合计 ${formatWon(feeInfo.cardIssueFee + CARD_DELIVERY_SURCHARGE)}。`
            : currentLanguage === 'en'
            ? `The registration/permanent-residence card costs ${formatWon(feeInfo.cardIssueFee)} for in-person pickup; choosing registered-mail delivery adds a ${formatWon(CARD_DELIVERY_SURCHARGE)} postage fee (${formatWon(feeInfo.cardIssueFee + CARD_DELIVERY_SURCHARGE)} total).`
            : `등록증·영주증은 방문 수령 시 ${formatWon(feeInfo.cardIssueFee)}이며, 등기우편 수령을 선택하면 우편요금 ${formatWon(CARD_DELIVERY_SURCHARGE)}이 추가되어 ${formatWon(feeInfo.cardIssueFee + CARD_DELIVERY_SURCHARGE)}입니다.`)
        : '';
    const notes = cardDeliveryNote ? [...baseNotes, cardDeliveryNote] : baseNotes;
    // D5 (1안): the generic 수수료 checklist tile was removed; carry its
    // fee-exemption clause here so the 면제 예외조항 is never lost. Sourced from
    // doc_guide doc_fee.conditional (시행규칙 제74조) — not invented.
    const feeExemption = (typeof docGuideData === 'object' && docGuideData && docGuideData.doc_fee && docGuideData.doc_fee.conditional) || '';
    const title = feeInfo.commonReference
        ? (currentLanguage === 'zh-CN' ? '通用手续费参考' : currentLanguage === 'en' ? 'Common fee reference' : '공통 수수료 참고')
        : (currentLanguage === 'zh-CN' ? (feeInfo.label || '手续费') : currentLanguage === 'en' ? 'Fee' : (feeInfo.label || '수수료'));
    return `<div class="procedure-fee-box">
        <div class="procedure-fee-title"><span>${escapeHtml(title)}</span><span class="procedure-fee-amount">${escapeHtml(amountText)}</span></div>
        ${notes.length ? `<ul class="procedure-fee-list">${notes.map(note => `<li>${escapeHtml(note)}</li>`).join('')}</ul>` : ''}
        ${feeExemption ? `<div class="procedure-fee-exemption">${escapeHtml((currentLanguage === 'zh-CN' ? '减免：' : currentLanguage === 'en' ? 'Exemption: ' : '면제: ') + feeExemption)}</div>` : ''}
        <div class="procedure-fee-note">${escapeHtml(feeInfo.sourceNote || STAY_FEE_SOURCE_NOTE)}</div>
    </div>`;
}

// Code normalisation, visa naming, document-requirement normalisation and manual-text helpers

export {
    formatWon, getProcedureFeeInfo, renderProcedureFeeBox, CARD_DELIVERY_SURCHARGE, DEFAULT_PROCEDURE_FEES
};
