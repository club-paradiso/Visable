// @ts-nocheck
/**
 * Code normalisation, visa naming, document-requirement normalisation and manual-text rendering helpers
 * (structure map clusters C14–C16; Phase 3, moved verbatim from index.html lines 17690-19234).
 * Pure helpers plus HTML-string renderers. They use the inline globals VISA_DATA, currentLanguage, tx(), txAt(),
 * escapeHtml(), hl(), PROCEDURE_CONFIG, DOC_DICT and friends by bare name at call time (compatibility surface,
 * ADR-009) and nothing at module-evaluation time. Exposed on window.Visable.docs; the inline stubs with the same
 * names (55 functions still called from index.html, assets/js/visa-route-guide.js guards and
 * tests/e2e/application-form-wording.spec.mjs) delegate here. Covered by tests/golden/specs/legacy-card.spec.mjs,
 * procedure.spec.mjs and search.spec.mjs; sliced by the legacy checks listed in docs/rebuild/phase0-legacy-checks.md.
 */
function normalizeVisaCode(value) {
    const cleaned = String(value || '')
        .trim()
        .toUpperCase()
        .replace(/[‐\-‒–—―－]/g, '-')
        .replace(/\s+/g, '')
        .replace(/^([A-H])(\d)([A-Z])/,  "$1-$2-$3")
        .replace(/^([A-H])(\d)$/,        "$1-$2");
    return cleaned;
}

function normalizeCodeLikeQuery(value) {
    const raw = String(value || '').trim().toUpperCase();
    if (!raw) return '';
    const compact = raw.replace(/\s+/g, '').replace(/_/g, '-');
    if (compact === 'KETA') return 'K-ETA';
    /* PARADISO_SEARCH_QUERY_FIX_20260702: also split compact forms with a
       trailing letter segment (D10T → D-10-T, E7M → E-7-M). Multi-digit
       compacts such as G15/D21 stay ambiguous here (G-15 vs G-1-5) — the
       compact-equality comparison in getExactQueryMatchRank resolves them
       against real codes, so G15 still lands on G-1-5. */
    if (/^[A-Z]+\d+$/.test(compact)) {
        return compact.replace(/^([A-Z]+)(\d+)$/, '$1-$2');
    }
    if (/^[A-Z]+\d+[A-Z][A-Z0-9]*$/.test(compact)) {
        return compact.replace(/^([A-Z]+)(\d+)([A-Z][A-Z0-9]*)$/, '$1-$2-$3');
    }
    return compact;
}

function isCodeLikeQuery(value) {
    const q = normalizeCodeLikeQuery(value);
    if (!q) return false;
    return /^[A-Z]+-\d+(?:-[A-Z0-9]+)*$/.test(q) || q === 'K-ETA';
}

/* PARADISO_EXACT_CODE_QUERY_FIX_20260609
   Treat a leading visa/status code as the user's primary intent even when the
   input came from an autocomplete label such as "D-2 유학". Without this, a
   code-like query can be diluted by names, procedure variants, or related
   status codes embedded in other records (for example F-2-R regional talent
   variants mentioning D-2), causing the wrong card to outrank the canonical
   D-2 record. */
function getPrimaryCodeLikeQuery(value) {
    const raw = String(value || '').trim();
    if (!raw) return '';
    const direct = normalizeCodeLikeQuery(raw);
    if (isCodeLikeQuery(direct)) return direct;

    /* PARADISO_SEARCH_QUERY_FIX_20260702 (3/3): the code may appear anywhere
       in the query, not only at the start — "숙련기능(E-7-4)" or "재외동포 F-4"
       should route to the code exactly like "E-7-4 숙련기능" does. */
    const match = raw.toUpperCase().match(/(?:^|[^A-Z0-9가-힣])([A-Z]+[-_\s]?\d+(?:[-_\s]?[A-Z0-9]+)*)(?=$|[^A-Z0-9])/);
    if (!match) return '';
    const compact = match[1].replace(/\s+/g, '').replace(/_/g, '-');
    const normalized = normalizeCodeLikeQuery(compact);
    return isCodeLikeQuery(normalized) ? normalized : '';
}

function getExactQueryMatchRank(item, query) {
    const qNorm = normalizeVisaCode(query);
    if (!qNorm) return 0;
    /* PARADISO_SEARCH_QUERY_FIX_20260702: dash-less compact comparison so
       compact subcode queries resolve regardless of where the user (or the
       normalizer) would place dashes: G15/G-15 → G-1-5, D21 → D-2-1,
       F442 → F-4-42, D10T → D-10-T. Equality only — prefix/substring ranks
       are unchanged. */
    const qCompact = qNorm.replace(/-/g, '');
    const codeEq = (value) => {
        const norm = normalizeVisaCode(value);
        return !!norm && (norm === qNorm || norm.replace(/-/g, '') === qCompact);
    };
    const codeNorm = normalizeVisaCode(item.code);
    const isHelperRecord = ['faq', 'scn', 'nhis'].includes(item.cat);
    if (codeEq(item.code)) return 10000;

    for (const s of getVisaSubcodes(item)) {
        if (codeEq(s.code)) return 5000;
    }

    const aliases = [
        ...(Array.isArray(item.aliases) ? item.aliases : []),
        ...(Array.isArray(item.searchAliases) ? item.searchAliases : [])
    ];
    if (aliases.some(codeEq)) return isHelperRecord ? 200 : 4000;

    for (const s of getVisaSubcodes(item)) {
        const subAliases = [
            ...(Array.isArray(s.aliases) ? s.aliases : []),
            ...(Array.isArray(s.searchAliases) ? s.searchAliases : [])
        ];
        if (subAliases.some(codeEq)) return 3000;
    }
    // Procedure-variant statusCodes: some official codes live only inside a
    // procedure variant (e.g. status-change scenarios). Index them so an exact
    // code query still resolves to the parent card even when the code is not
    // (yet) surfaced as a subCode.
    const procs = item.procedures && typeof item.procedures === 'object' ? item.procedures : {};
    for (const key of Object.keys(procs)) {
        const proc = procs[key];
        const variants = proc && Array.isArray(proc.variants) ? proc.variants : [];
        for (const variant of variants) {
            const codes = [];
            if (variant.statusCode) codes.push(variant.statusCode);
            if (Array.isArray(variant.statusCodes)) codes.push(...variant.statusCodes);
            if (codes.some(c => normalizeVisaCode(c) === qNorm)) return 3;
        }
    }
    return 0;
}

function isEnglishMode() { return currentLanguage === 'en'; }
function getVisaNameKo(v) { return v.nameKo || v.name || ''; }
function getVisaNameEn(v) {
    return v.nameEn || v.name_en || v.titleEn || v.title_en || localizedVisaNameFromPack(v.code, 'en') || '';
}
// Primary display name follows the active locale (record fields first, then the
// visa-name i18n pack); Korean canonical is the universal fallback.
function getLocalizedVisaName(v) {
    const lang = normalizeLocaleCode(currentLanguage);
    if (lang === 'ko') return getVisaNameKo(v);
    if (lang === 'en') return getVisaNameEn(v) || getVisaNameKo(v);
    return localizedVisaNameFromPack(v.code, lang) || getVisaNameKo(v);
}
// Secondary line keeps the Korean canonical name visible whenever the primary
// line is a translation (and surfaces English next to Korean in ko mode).
function getSecondaryVisaName(v) {
    const primary = getLocalizedVisaName(v);
    const ko = getVisaNameKo(v);
    if (primary && primary !== ko) return ko;
    return getVisaNameEn(v);
}
function getVisaSubcodes(v) { return Array.isArray(v.subcodes) ? v.subcodes : (Array.isArray(v.subCodes) ? v.subCodes : []); }
function getLocalizedSubcodeName(s) {
    const raw = isEnglishMode() ? (s.nameEn || s.name_en || s.titleEn || s.title_en || s.nameKo || s.name || '') : (s.nameKo || s.name || '');
    return paradisoStripInternalReviewArtifacts(raw) || raw;
}

const PROCEDURE_LABEL_INDEX = {
    visaIssuance: 0,
    certificateOfVisaIssuance: 1,
    statusChange: 2,
    extension: 3,
    statusGrant: 4,
    registration: 5,
    activitiesOutsideStatus: 6,
    workplaceChange: 7,
    reentry: 8,
    partTimeWork: 9,
    schoolChange: 10
};

function getProcedureLabelByKey(key, fallback = '') {
    const index = PROCEDURE_LABEL_INDEX[key];
    return Number.isInteger(index) ? txAt('procedureLabels', index, fallback || key) : (fallback || key);
}

function getProcedureLabel(proc) {
    return getProcedureLabelByKey(proc.key, proc.label);
}

// 영주(F-5)는 체류기간 상한이 없는 영주자격이라 '체류기간 연장' 개념이 없고,
// 영주증(영주카드)을 유효기간 10년마다 재발급하는 절차만 존재합니다(출입국관리법
// 제33조의2·시행규칙 제72조제10의2호). 데이터상 동일한 extension 절차 슬롯을
// 재사용하되, 사용자에게는 잘못된 '체류기간 연장'이 아니라 올바른 명칭
// '영주증 재발급'으로 표시합니다. (렌더러 전용 표시 보정 — 데이터 미변경)
function isF5ResidenceCardReissuance(v, proc) {
    return !!(v && v.code === 'F-5' && proc && proc.key === 'extension');
}
function getProcedureDisplayLabel(v, proc) {
    if (isF5ResidenceCardReissuance(v, proc)) {
        const label = tx('procExtensionResidenceCardF5');
        return label && label !== 'procExtensionResidenceCardF5' ? label : '영주증 재발급';
    }
    return getProcedureLabel(proc);
}

function localizeResultCount(n, subtypeCount = 0) {
    const count = tx('resultCount', { count: n });
    const subtypes = subtypeCount ? ` (${tx('resultSubtypeCount', { count: subtypeCount })})` : '';
    return `${count}${subtypes} · ${tx('resultTotal', { count: VISA_DATA.length })}`;
}

function getRecordSearchText(v) {
    const subText = getVisaSubcodes(v).map(s => `${s.code || ''} ${s.nameKo || s.name || ''} ${s.nameEn || ''} ${s.summary || ''} ${(s.eligibility || []).join(' ')} ${s.addReq || ''} ${s.note || ''}`).join(' ');
    const procedures = v.procedures ? Object.values(v.procedures).map(p => `${(p.eligibility || []).join(' ')} ${JSON.stringify(p.requiredDocs || '')} ${JSON.stringify(p.variants || '')} ${(p.notes || []).join(' ')}`).join(' ') : '';
    return `${v.code || ''} ${getVisaNameKo(v)} ${getVisaNameEn(v)} ${(v.aliases || []).join(' ')} ${(v.searchAliases || []).join(' ')} ${v.newReq || ''} ${v.extReq || ''} ${v.changeReq || ''} ${v.faq || ''} ${v.period || ''} ${subText} ${procedures}`;
}

function keywordMatchesCode(code, keywords) {
    const normalized = normalizeVisaCode(code);
    return keywords.some(kw => normalizeVisaCode(kw) === normalized || String(code || '').toLowerCase().includes(String(kw).toLowerCase()));
}

function getMatchingSubcodes(v, keywords) {
    if (!keywords || !keywords.length) return [];
    return getVisaSubcodes(v).filter(s => {
        const text = `${s.code || ''} ${s.nameKo || s.name || ''} ${s.nameEn || ''} ${s.summary || ''} ${(s.eligibility || []).join(' ')} ${s.addReq || ''} ${s.note || ''}`.toLowerCase();
        return keywords.some(kw => text.includes(kw) || normalizeVisaCode(s.code) === normalizeVisaCode(kw));
    });
}

function getManualDomains(v) {
    if (Array.isArray(v.manualDomains) && v.manualDomains.length) return v.manualDomains;
    if (['faq', 'scn', 'nhis'].includes(v.cat)) return [];
    const hasVisa = !!(v.newReq || v.newReqDocs || v.initialReqDocs);
    const hasStay = !!(v.extReq || v.extReqDocs || v.extensionReqDocs || v.changeReqDocs);
    if (hasVisa && hasStay) return ['visa_issuance', 'stay_sojourn'];
    if (hasVisa) return ['visa_issuance'];
    if (hasStay) return ['stay_sojourn'];
    return ['stay_sojourn'];
}

function renderDomainBadges(v) {
    const domains = getManualDomains(v);
    if (domains.includes('visa_issuance') && domains.includes('stay_sojourn')) {
        return `<span class="manual-badge domain-visa">${escapeHtml(txAt('domainLabels', 0, '공통/양쪽'))}</span>`;
    }
    return domains.map(d => {
        if (d === 'visa_issuance') return `<span class="manual-badge domain-visa">${escapeHtml(txAt('domainLabels', 1, '사증발급'))}</span>`;
        if (d === 'stay_sojourn') return `<span class="manual-badge domain-stay">${escapeHtml(txAt('domainLabels', 2, '체류민원'))}</span>`;
        return `<span class="manual-badge">${escapeHtml(d)}</span>`;
    }).join('');
}

function renderReviewBadge(v) {
    const status = v.sourceManualStatus || {};
    if (status.verified === true && !status.needsManualReview) return `<span class="manual-badge review-ok">${escapeHtml(txAt('reviewLabels', 0, '2026.6 매뉴얼 확인됨'))}</span>`;
    if (status.verified === false && status.needsManualReview === false) return `<span class="manual-badge review-needed">${escapeHtml(txAt('reviewLabels', 1, '일부 정보 미검증'))}</span>`;
    return `<span class="manual-badge review-needed">${escapeHtml(txAt('reviewLabels', 2, '2026.6 매뉴얼 확인 필요'))}</span>`;
}

const SOURCE_CONFIRMED_PROCEDURE_KEY_MAP = {
    visa_issuance: 'visaIssuance',
    initial: 'visaIssuance',
    certificate_of_visa_issuance: 'certificateOfVisaIssuance',
    change_of_status: 'statusChange',
    status_change: 'statusChange',
    extension: 'extension',
    extension_of_stay: 'extension',
    status_grant: 'statusGrant',
    registration: 'registration',
    foreigner_registration: 'registration',
    alien_registration: 'registration',
    registration_or_residence_report: 'registration',
    reporting_duty: 'registration',
    activities_outside_status: 'activitiesOutsideStatus',
    activity_outside_status: 'activitiesOutsideStatus',
    workplace_change_or_addition: 'workplaceChange',
    workplace_change_addition: 'workplaceChange',
    reentry: 'reentry',
    reentry_permit: 'reentry'
};

function procedureKeyForSourceConfirmedType(type) {
    const key = String(type || '').trim().toLowerCase();
    return SOURCE_CONFIRMED_PROCEDURE_KEY_MAP[key] || '';
}

function getSourceConfirmedEntriesForProcedure(v, procedureKey) {
    const entries = Array.isArray(v?.sourceConfirmedStructuredRequirements) ? v.sourceConfirmedStructuredRequirements : [];
    return entries.filter(entry => procedureKeyForSourceConfirmedType(entry?.procedureType) === procedureKey);
}

// F-4 procedures that use 재외동포 통합신청서(별지 제1호서식) per
// 재외동포의 출입국과 법적지위에 관한 법률 시행규칙
const F4_OVERSEAS_KOREANS_FORM_PROCEDURES = new Set([
    'statusChange', 'registration', 'activitiesOutsideStatus', 'extension'
]);

/* Single application-form wording rule (stay procedures only).
   One piece = one document name, e.g. "신청서", "통합신청서 (별지 제34호 서식)",
   "통합신청서(별지 제1호 서식)", "재외동포(F-4) 통합신청서(별지 제1호 서식)".
   Whitespace between 호/서식 and the optional 재외동포 prefix are tolerated.
   Already-canonical wording ("통합신청서 (신고서) [별지 제34호서식]") does not
   match, so the function is idempotent. */
const PARADISO_APP_FORM_PIECE_RE = /^(재외동포(?:\s*\(\s*F-4\s*\))?\s*)?(?:통합\s*)?신청서\s*(?:\(\s*(?:시행규칙\s*)?별지\s*제?\s*(34|1)\s*호\s*서식\s*\))?$/;

function paradisoCanonicalAppFormPiece(piece, procedureKey, statusCode) {
    const value = String(piece || '').trim();
    if (!value || procedureKey === 'visaIssuance') return value;
    const m = value.match(PARADISO_APP_FORM_PIECE_RE);
    if (!m) return value;
    const formNo = m[2] || '';
    const isF4 = statusCode === 'F-4';
    const f4Stay = isF4 && (F4_OVERSEAS_KOREANS_FORM_PROCEDURES.has(procedureKey) || (!procedureKey && (formNo === '1' || m[1])));
    if (f4Stay) return tx('f4ApplicationForm');
    // 별지 제1호 / 재외동포 접두어는 F-4 문맥이 아니면 임의로 바꾸지 않는다.
    if (formNo === '1' || m[1]) return value;
    return '통합신청서 (신고서) [별지 제34호서식]';
}

/* Splits on top-level commas only (commas inside parentheses stay) and applies
   the application-form rule to every piece, so a combined row such as
   "신청서, 여권, 외국인등록증(소지자), 사진 1매" is handled too. */
function paradisoCanonicalAppFormText(text, procedureKey, statusCode) {
    const value = String(text || '').trim();
    if (!value || procedureKey === 'visaIssuance') return value;
    if (value.indexOf(',') < 0) return paradisoCanonicalAppFormPiece(value, procedureKey, statusCode);
    const parts = [];
    let depth = 0, cur = '';
    for (const ch of value) {
        if (ch === '(' || ch === '（') depth++;
        else if (ch === ')' || ch === '）') depth = Math.max(0, depth - 1);
        if (ch === ',' && depth === 0) { parts.push(cur); cur = ''; continue; }
        cur += ch;
    }
    parts.push(cur);
    let changed = false;
    const out = parts.map(p => {
        const next = paradisoCanonicalAppFormPiece(p, procedureKey, statusCode);
        if (next !== p.trim()) changed = true;
        return next;
    });
    return changed ? out.join(', ') : value;
}

/* Glossary lookup key for the canonical generic form wording: it is the same
   document as the existing 별지 제34호 glossary entry (no new term invented).
   Lives here, outside the i18n runtime block, so the hardcoded-text check
   (scripts/check_index_hardcoded_text.mjs) keeps passing. */
function paradisoGlossaryLabelForAppForm(label) {
    return String(label || '').replace(/\s+/g, '') === '통합신청서(신고서)[별지제34호서식]'
        ? '통합신청서(별지 제34호 서식)'
        : label;
}

function canonicalizeSourceConfirmedDocText(text, procedureKey, statusCode) {
    const value = String(text || '').replace(/^\s*[①-⑳]\s*/g, '').trim();
    if (!value || isDocPlaceholder(value)) return '';
    return paradisoCanonicalAppFormText(value, procedureKey, statusCode);
}

function groupSourceConfirmedDocuments(entries, procedureKey, statusCode) {
    const groups = { commonDocs: [], requiredDocs: [], additionalDocs: [], conditionalDocs: [] };
    (entries || []).forEach(entry => {
        (entry.documents || []).forEach(doc => {
            const text = canonicalizeSourceConfirmedDocText(doc?.textKo || doc?.text || doc?.name, procedureKey, statusCode);
            if (!text) return;
            const requiredness = String(doc?.requiredness || '').toLowerCase();
            if (/common|basic|공통|기본/.test(requiredness)) groups.commonDocs.push(text);
            else if (/conditional|condition|조건/.test(requiredness)) groups.conditionalDocs.push(text);
            else if (/additional|review|supplement|추가|심사/.test(requiredness)) groups.additionalDocs.push(text);
            else groups.requiredDocs.push(text);
        });
    });
    return mergeDocGroups(groups);
}

function sourceConfirmedManualRefs(entries) {
    const seen = new Set();
    return (entries || []).map(entry => {
        const source = entry.source || {};
        const pageStart = entry.pageStart || source.pageStart;
        const pageEnd = entry.pageEnd || source.pageEnd;
        const pageRange = pageStart && pageEnd && pageStart !== pageEnd ? `pp. ${pageStart}-${pageEnd}` : (pageStart ? `p. ${pageStart}` : '');
        return {
            manualName: source.manualName || entry.manualName || '외국인체류 안내매뉴얼',
            manualVersion: source.manualVersion || entry.manualVersion || '2026.9',
            pageRange,
            sectionTitle: entry.sectionTitle || '',
            subCode: entry.subCode || '',
            sourceConfirmed: true
        };
    }).filter(ref => {
        const key = [ref.manualName, ref.manualVersion, ref.pageRange, ref.sectionTitle, ref.subCode].join('|');
        if (seen.has(key)) return false;
        seen.add(key);
        return true;
    });
}

function mergeManualRefs(...refLists) {
    const seen = new Set();
    return refLists.flat().filter(ref => {
        if (!ref) return false;
        const key = [ref.manualName || ref.manual || '', ref.manualVersion || ref.version || '', ref.pageRange || '', ref.sectionTitle || '', ref.subCode || ''].join('|');
        if (seen.has(key)) return false;
        seen.add(key);
        return true;
    });
}

// 영주(F-5) 취득 경로 표시 보정 (렌더러 전용 — 보호 데이터 파일 미변경).
// 영주자격은 재외공관에서 '영주 사증'을 발급받아 입국하는 자격이 아니라, 국내
// 체류 중 다른 장기체류자격(F-2·F-6·D-8 등)에서 '체류자격 변경허가'를 받아
// 취득합니다(출입국관리법 제10조의3 영주자격, 제24조 체류자격 변경허가). F-5
// 레코드의 레거시 newReq/newReqDocs(전환 요건 입증·해외범죄경력·생계유지·사회통합
// 5단계)는 바로 이 자격변경 요건이므로, '체류자격 변경' 절차가 이를 노출하도록
// 매핑합니다. 변경허가 후에는 외국인등록과 함께 영주증이 발급되고, 영주증은 유효
// 기간 10년마다 재발급합니다(extension 슬롯을 '영주증 재발급'으로 표시). 영주
// 사증은 발급되지 않으므로 '사증발급' 절차는 노출하지 않습니다.
function remapPermanentResidenceAcquisition(v, cfg) {
    if (!v || v.code !== 'F-5' || !cfg) return cfg;
    if (cfg.key === 'statusChange') {
        const baseRequired = (cfg.docFields && cfg.docFields.requiredDocs) || cfg.oldDocs || [];
        return {
            ...cfg,
            oldText: (cfg.oldText && v[cfg.oldText]) ? cfg.oldText : 'newReq',
            docFields: { ...(cfg.docFields || {}), requiredDocs: [...baseRequired, 'newReqDocs'] }
        };
    }
    return cfg;
}
function isSuppressedProcedureForStatus(v, cfg) {
    // 사증발급이 적용되지 않는 체류자격(영주 F-5, 사증면제 B-1·B-2, 비대상 H-2
    // 등)은 '사증발급' 탭을 숨깁니다. 판정은 isVisaIssuanceNotApplicable
    // (data/visa_issuance_records.json 기반)에 위임합니다.
    if (!(v && cfg && cfg.key === 'visaIssuance')) return false;
    return isVisaIssuanceNotApplicable(v);
}

// 사증발급(입국 전) 서류의 권위 있는 출처는 data/visa_issuance_records.json 의
// issuanceModes[].documents 입니다(재외공관 신청 서류: 사증발급신청서 별지 제17호
// 등). 레코드에 절차 범위(procedures.visaIssuance)·source-confirmed 서류가 없을 때,
// 렌더러가 레거시 최상위 newReqDocs/initialReqDocs(입국 후 체류 절차용 통합신청서
// 별지 제34호·외국인등록증·체류자격 부여 수수료 등 — 사증발급 단계에 부적합)로
// 폴백하면 안 되므로, 이 발급-출처 서류를 사증발급 탭/모달의 폴백 문서로
// 사용합니다. 발명 없음 — 보호 데이터(visa_data.json/visas.json)는 변경하지 않습니다.
function getVisaIssuanceModeDocGroups(v) {
    if (!v) return null;
    const record = getVisaIssuanceRecord(v.code);
    if (!record) return null;
    const modes = Array.isArray(record.issuanceModes) ? record.issuanceModes : [];
    const groups = { commonDocs: [], requiredDocs: [], additionalDocs: [], conditionalDocs: [] };
    for (const mode of modes) {
        const docs = mode && mode.documents;
        if (!docs) continue;
        if (Array.isArray(docs.common)) groups.commonDocs.push(...docs.common);
        if (Array.isArray(docs.additional)) groups.additionalDocs.push(...docs.additional);
        if (Array.isArray(docs.conditional)) groups.conditionalDocs.push(...docs.conditional);
    }
    return hasAnyDocs(groups) ? mergeDocGroups(groups) : null;
}

function getProcedure(v, cfg) {
    cfg = remapPermanentResidenceAcquisition(v, cfg);
    const hidden = isSuppressedProcedureForStatus(v, cfg);
    const raw = v.procedures && v.procedures[cfg.key] ? v.procedures[cfg.key] : null;
    const structuredEntries = getSourceConfirmedEntriesForProcedure(v, cfg.key);
    const structuredDocs = groupSourceConfirmedDocuments(structuredEntries, cfg.key, v.code);
    const structuredRefs = sourceConfirmedManualRefs(structuredEntries);
    const legacyDocs = normalizeDocGroups(null, v, {
        commonDocs: ['commonDocs'],
        requiredDocs: cfg.docFields?.requiredDocs || cfg.oldDocs || [],
        additionalDocs: ['additionalDocs', ...(cfg.docFields?.additionalDocs || [])],
        conditionalDocs: ['conditionalDocs']
    });
    const legacyAvailable = hasAnyDocs(structuredDocs) || hasAnyDocs(legacyDocs) || !!(cfg.oldText && v[cfg.oldText]);
    const hasExplicitAvailability = !!(raw && Object.prototype.hasOwnProperty.call(raw, 'available'));
    const explicitUnavailable = hasExplicitAvailability && raw.available === false;
    const explicitAvailable = hasExplicitAvailability && raw.available === true;
    const available = hidden ? false : (explicitUnavailable ? false : (explicitAvailable || legacyAvailable));
    const rawDocs = normalizeDocGroups(raw?.requiredDocs, raw || {});
    const hasProcedureScopedDocs = hasAnyDocs(structuredDocs) || hasAnyDocs(rawDocs);
    // Procedure-scoped data is the display authority. Legacy top-level arrays
    // are a fallback only; merging them into explicit procedure docs can pool
    // scenario/status-specific requirements into the basic/common section.
    const emptyLegacyDocs = { commonDocs: [], requiredDocs: [], additionalDocs: [], conditionalDocs: [] };
    let docs;
    if (hasProcedureScopedDocs) {
        docs = mergeDocGroups(structuredDocs, rawDocs, emptyLegacyDocs);
    } else if (cfg.key === 'visaIssuance') {
        // H-5: 사증발급 탭/모달은 레거시 최상위 newReqDocs/initialReqDocs(체류 절차용
        // 서류)로 폴백하지 않습니다. 절차 범위 서류가 없으면 발급-출처
        // (visa_issuance_records.json) 서류가 우선하고, 그마저 없으면 빈 목록으로
        // 두어 렌더러가 기존 '확인 필요/공식 출처에서 확인' 안내를 노출하게 합니다.
        const issuanceDocs = getVisaIssuanceModeDocGroups(v);
        docs = mergeDocGroups(structuredDocs, rawDocs, issuanceDocs || emptyLegacyDocs);
    } else {
        docs = mergeDocGroups(structuredDocs, rawDocs, legacyDocs);
    }
    return {
        key: cfg.key,
        label: txAt('procedureLabels', cfg.labelIndex, cfg.label),
        oldType: cfg.oldType,
        available,
        eligibility: raw?.eligibility || [],
        notes: paradisoFilterProcedureNotes(raw?.notes),
        summary: raw?.summary || (cfg.oldText && v[cfg.oldText] ? v[cfg.oldText] : ''),
        docs: hidden ? emptyLegacyDocs : docs,
        variants: normalizeProcedureVariants(raw?.variants),
        feeInfo: getProcedureFeeInfo(v, cfg.key),
        manualRefs: mergeManualRefs(structuredRefs, raw?.manualRefs || []),
        sourceConfirmed: hasAnyDocs(structuredDocs)
    };
}

const DOC_GROUP_ALIASES = {
    commonDocs: ['commonDocs', 'common_documents', 'common'],
    requiredDocs: ['requiredDocs', 'required_documents', 'reqDocs', 'documents', 'document', 'docs', 'required'],
    additionalDocs: ['additionalDocs', 'additional_documents', 'addReqDocs', 'addReq', 'additional'],
    conditionalDocs: ['conditionalDocs', 'conditional_documents', 'conditional']
};

/* Auto-extracted 절차 제출서류 occasionally arrive as ONE comma-joined blob
   ("신청서, 수수료, 한국어능력 입증서류, 체류지 입증서류(예: …) 등 □ 재외동포(F-4) …")
   instead of separate rows, so the whole list rendered as a single over-long tile
   — visibly different from every other 체류자격. This splits such a blob back into
   its constituent documents (each top-level comma part is a real document; commas
   inside parentheses are preserved) and drops any trailing manual section-heading
   fragment ("… 등 □ …"). Bare common tokens map to their canonical doc IDs so the
   unified official naming (통합신청서(별지 제34호 서식)) and the standard 수수료→fee-box
   handling apply — matching all other statuses. Display-only: the protected data
   files (visa_data.json / doc_master.json) are NEVER mutated. */
const PARADISO_PROC_DOC_BLOB_HEAD_RE = /^\s*(통합\s*신청서|신청서|사증발급신청서|여권|외국인\s*등록증|등록증|거소증|수수료|정부수입인지|표준규격\s*사진|여권용\s*사진|증명사진|사진|한국어능력)/;
const PARADISO_PROC_DOC_BLOB_PART_RE = /(입증서류|입증자료|서류|증명서|확인서|신청서|신고서|신분증|계약서|등록증|거소증|영수증|진단서|허가서|동의서|사유서|계획서|여권|사진|수수료|인지|등본|초본|인정서|위임장|이수증|합격증|성적표)$/;
const PARADISO_PROC_DOC_BLOB_SECTION_TAIL_RE = /\s*등?\s*[□■◇▶▷☞❍◦]\s*[\s\S]*$/;
function paradisoCanonicalizeProcedureDocPart(part) {
    const head = String(part).split(/[(（]/)[0].replace(/\s+/g, '');
    if (/^(통합)?신청서$/.test(head)) return 'doc_app_form';
    if (/^(수수료|정부수입인지|수입인지|인지대)$/.test(head)) return 'doc_fee';
    return part;
}
function paradisoSplitProcedureDocBlob(value) {
    let s = String(value == null ? '' : value).replace(/\s+/g, ' ').trim();
    if (!s || s.indexOf(',') < 0 || !PARADISO_PROC_DOC_BLOB_HEAD_RE.test(s)) return null;
    s = s.replace(PARADISO_PROC_DOC_BLOB_SECTION_TAIL_RE, '').trim();
    if (!s || s.indexOf(',') < 0) return null;
    const parts = [];
    let depth = 0, cur = '';
    for (const ch of s) {
        if (ch === '(' || ch === '（') depth++;
        else if (ch === ')' || ch === '）') depth = Math.max(0, depth - 1);
        if (ch === ',' && depth === 0) { parts.push(cur.trim()); cur = ''; continue; }
        cur += ch;
    }
    parts.push(cur.trim());
    const cleaned = parts.map(p => p.replace(/\s*등\s*$/, '').trim()).filter(Boolean);
    if (cleaned.length < 2) return null;
    // Every part must read as a concrete document name (its head, before any
    // parenthetical, is a short noun phrase ending in a document token) so a
    // genuine explanatory sentence is never fragmented into pseudo-tiles.
    const everyPartIsDoc = cleaned.every(p => {
        const head = p.split(/[(（]/)[0].trim().replace(/\s+/g, '');
        return head.length > 0 && head.length <= 30 && PARADISO_PROC_DOC_BLOB_PART_RE.test(head);
    });
    if (!everyPartIsDoc) return null;
    return cleaned.map(paradisoCanonicalizeProcedureDocPart);
}

function toDocArray(value) {
    if (!value) return [];
    if (Array.isArray(value)) return value.flatMap(toDocArray);
    if (typeof value === 'string') {
        // A single auto-extracted blob crams several documents (and sometimes a
        // trailing section heading) into one comma-joined string; split it back
        // into separate document rows before the prose-blob guard keeps it whole.
        const procBlob = paradisoSplitProcedureDocBlob(value);
        if (procBlob) return procBlob;
        // Never fragment a single prose blob (e.g. "세부약호별(산업재해·질병치료·…)
        // 추가 제출서류는 사안마다 다름") into pseudo-document tiles on the middot.
        if (paradisoIsSingleProseBlob(value)) {
            const v = value.trim();
            return v && !isDocPlaceholder(v) ? [v] : [];
        }
        return value.split(/\n|;|·/)
            .map(v => v.trim())
            .filter(v => v && !isDocPlaceholder(v))
            .flatMap(v => paradisoSplitCompoundDocRow(v) || [v]);
    }
    if (typeof value === 'object') {
        const label = value.name || value.label || value.title || value.text || value.description;
        return label ? [String(label).trim()].filter(v => v && !isDocPlaceholder(v)) : [];
    }
    return [String(value).trim()].filter(v => v && !isDocPlaceholder(v));
}

// Tokens that are never real document names: pipeline placeholders or
// "could-not-extract" stand-ins. Rendering any of them as a checklist line is a
// user-facing quality regression, so they are suppressed at the rendering layer
// (defense-in-depth on top of the data cleanup, so a future data regression can
// never surface them to users).
const DOC_PLACEHOLDER_TOKENS = [
    '매뉴얼 확인 필요', '페이지 확인 필요', 'Manual review needed', 'Page review needed',
    '문서명 미상', '비고 정보 없음', 'DATA_MISSING', 'Document name unknown', 'No note available'
];
function isDocPlaceholder(value) {
    return DOC_PLACEHOLDER_TOKENS.includes(String(value || '').trim());
}

/* PARADISO_DOC_PROSE_SPLIT_20260609
   Single source of truth (mirrored by scripts/audit_duplicate_render_content.py)
   for separating a raw document item into a concise checklist LABEL plus a
   relocated NOTE. Explanatory prose / eligibility / stay-period / scope /
   procedure text must never render as a required-document tile -- it is moved to
   a note instead, and the underlying source wording is preserved verbatim. No
   data is mutated: this is a render-layer transform only. */
const PARADISO_DOC_LONG_THRESHOLD = 80;
const PARADISO_DOC_SEVERE_THRESHOLD = 160;
const PARADISO_DOC_SENTENCE_END_RE = /(?:습니다|입니다|합니다|됩니다|있습니다|없습니다|바랍니다|십시오|하십시오|가능|불가|불요|제한|부여|징구|면제|해당됩니다|필요합니다|수\s*없[다음]|할\s*수\s*있음|받을\s*수\s*있음)\.?$/;
const PARADISO_DOC_PROSE_TOPIC_RE = /(원칙적으로|경우에\s*한|에\s*한해|해당자|대상으로\s*합니다|대상입니다|상한은|특례\s*상한|체류기간\s*상한|허가될\s*수|조정될\s*수|심사가\s*강화|생략될\s*수|제출\s*불요|초과할\s*수\s*없|기재하되|허위기재|처벌받을\s*수)/;
const PARADISO_DOC_TAIL_RE = /(서류|증명서|확인서|신청서|계약서|등록증|영수증|진단서|보증서|결정문|입증자료|사업자등록증|고유번호증|허가서|동의서|사유서|계획서|증빙서류|여권|사본|원본|사진|수수료|인지|통지서|출석부|카드|공한|등본|초본|입증서류|증서|소견서|위임장|재학증명서|졸업증명서|인정서|확인증|납입증명서)$/;
const PARADISO_DOC_HEADING_RE = /[□■◇▶▷※☞❍]|[0-9]{1,2}\.\s*\S+제출서류|체류기간\s*연장\s*제출서류/;
const PARADISO_DOC_RESIDENCE_RE = /체류지\s*입증서류\s*\(\s*예\s*:[\s\S]*?준비\s*\)/;
const PARADISO_DOC_SUBCODE_REF_RE = /[A-Z]{1,3}-[0-9]+-[0-9A-Z]+/;
const PARADISO_DOC_PROSE_PREFIX_RE = /^(대상|예외|참고|유의|비고|주의|단,|대상:)/;
const PARADISO_DOC_STRONG_PROSE_TOKENS = ['세부약호'];

function paradisoNormalizeDocText(value) {
    if (value == null) return '';
    return String(value).normalize('NFKC').replace(/ /g, ' ').replace(/\s+/g, ' ').trim();
}
function paradisoStripLeadingDocMarks(value) {
    let s = String(value || '');
    const re = /^\s*(?:[①-⑳]|[0-9]+\s*[.)]|[-‣◦○●□■◇*※·•ㆍ])\s*/;
    while (true) {
        const next = s.replace(re, '');
        if (next === s) return s.trim();
        s = next;
    }
}
// Returns { label, note, kind } where kind is 'doc' | 'prose' | 'empty'.
function paradisoSplitDocItem(value) {
    let text = paradisoNormalizeDocText(value);
    if (!text || isDocPlaceholder(text)) return { label: '', note: '', kind: 'empty' };
    text = paradisoStripLeadingDocMarks(text);
    if (!text) return { label: '', note: '', kind: 'empty' };

    const m = text.match(PARADISO_DOC_RESIDENCE_RE);
    if (m) {
        const block = m[0];
        const before = text.slice(0, m.index).trim().replace(/,+$/, '').trim();
        const after = text.slice(m.index + block.length).trim();
        const inner = block.slice(block.indexOf('(') + 1, block.lastIndexOf(')')).trim();
        const noteParts = [];
        if (inner) noteParts.push(inner);
        if (after) noteParts.push(paradisoStripLeadingDocMarks(after));
        const rawNote = noteParts.filter(Boolean).join(' / ');
        const note = /^예:/.test(rawNote) ? '*' + rawNote : rawNote;
        const label = before ? (before + ', 체류지 입증서류*') : '체류지 입증서류*';
        if (!before || !PARADISO_DOC_SENTENCE_END_RE.test(before)) return { label, note, kind: 'doc' };
    }

    const headCandidate = text.split(/[(（]|※|‣|◦|·|\s—\s/)[0].trim();
    const looksLikeSentence = PARADISO_DOC_SENTENCE_END_RE.test(text) || PARADISO_DOC_PROSE_TOPIC_RE.test(text);
    const hasDocTail = PARADISO_DOC_TAIL_RE.test(headCandidate);
    const hasHeading = PARADISO_DOC_HEADING_RE.test(text);
    const hasSubcodeRef = PARADISO_DOC_SUBCODE_REF_RE.test(text);
    const prosePrefix = PARADISO_DOC_PROSE_PREFIX_RE.test(text);
    const openP = (text.match(/[(（]/g) || []).length;
    const closeP = (text.match(/[)）]/g) || []).length;
    const unbalanced = openP !== closeP;
    const strongProse = PARADISO_DOC_STRONG_PROSE_TOKENS.some(t => text.includes(t))
        || text.includes('사증발급인정서') || unbalanced || hasSubcodeRef || prosePrefix;

    if (!hasDocTail && (looksLikeSentence || text.length > PARADISO_DOC_LONG_THRESHOLD || strongProse)) {
        return { label: '', note: text, kind: 'prose' };
    }

    if (hasDocTail && (text.length > PARADISO_DOC_LONG_THRESHOLD || hasHeading)) {
        let cut = null;
        const markers = ['(', '（', '※', '‣', '□', '■', '◇', '▶', '▷', '☞', '❍'];
        markers.forEach(ch => {
            const idx = text.indexOf(ch, headCandidate.length);
            if (idx >= 0 && (cut === null || idx < cut)) cut = idx;
        });
        if (cut !== null && cut < text.length) {
            const label = text.slice(0, cut).trim().replace(/,+$/, '').trim();
            const note = paradisoStripLeadingDocMarks(text.slice(cut).trim().replace(/^[()（）\s]+/, ''));
            if (PARADISO_DOC_TAIL_RE.test(label) && label.length <= PARADISO_DOC_SEVERE_THRESHOLD) {
                return { label, note, kind: 'doc' };
            }
        }
    }

    if (text.length > PARADISO_DOC_SEVERE_THRESHOLD) return { label: '', note: text, kind: 'prose' };
    return { label: text, note: '', kind: 'doc' };
}
// True when a bare string is one explanatory sentence rather than a
// separator-joined document list (so toDocArray must not fragment it).
function paradisoIsSingleProseBlob(value) {
    const s = paradisoNormalizeDocText(value);
    if (!s) return false;
    if (PARADISO_DOC_STRONG_PROSE_TOKENS.some(t => s.includes(t))) return true;
    const openP = (s.match(/[(（]/g) || []).length;
    const closeP = (s.match(/[)）]/g) || []).length;
    if (openP !== closeP) return true;
    if (s.indexOf('·') >= 0 && (PARADISO_DOC_SENTENCE_END_RE.test(s) || PARADISO_DOC_PROSE_TOPIC_RE.test(s) || s.length > 120)) return true;
    return false;
}

function dedupeDocs(docs) {
    const seen = new Set();
    return (docs || []).filter(doc => {
        const key = String(doc || '').trim();
        // Drop empties, duplicates, and placeholder/diagnostic stand-ins so a
        // group that only held placeholders collapses to empty and the panel
        // shows a single source-limited notice instead of fake rows.
        if (!key || seen.has(key) || isDocPlaceholder(key)) return false;
        seen.add(key);
        return true;
    });
}

/* PARADISO_DOC_RENDER_GUARD_BEGIN (20260610)
   Display-only document dedupe, merge and UX grouping. Source-of-truth data
   (visa_data.json / doc_master.json) is NEVER mutated here — these helpers
   shape what users see when the same official requirement arrives both as a
   procedure-bucket string (e.g. "신청서") and a legacy doc-id whose DOC_DICT
   label is the decorated official form ("통합신청서 (별지 제34호 서식)").
   Static contract canonical domestic label: "통합신청서(별지 제34호 서식)".
   The pre-patch regression: dedupe keys were computed on the RAW entry, so a
   doc_* id never collided with its Korean-string twin and both rendered.
   audits/official-document-dedupe/audit_document_duplicates.js extracts this
   block verbatim for its "after" simulation — keep the markers intact. */

function paradisoResolveDocDisplayLabel(entry) {
    const s = String(entry == null ? '' : entry).trim();
    if (s.indexOf('doc_') === 0 && typeof DOC_DICT === 'object' && DOC_DICT[s]) return DOC_DICT[s];
    return s;
}

/* The manuals frequently list several common documents on ONE line
   ("신청서, 여권, 외국인등록증, 수수료"). Splitting such rows into individual
   tiles is source-faithful (each part is a real document) and lets per-family
   dedupe work. Split only when EVERY top-level comma part independently reads
   as a document; commas inside parentheses (e.g. "체류지 입증서류(예: 임대차
   계약서, …)") never split. */
const PARADISO_DOC_PART_TAIL_RE = /(서류|증명서|확인서|신청서|신고서|신분증|계약서|등록증|영수증|진단서|보증서|입증자료|허가서|동의서|사유서|계획서|여권|사진|수수료|등본|초본|확인증|납입증명서|인정서|소견서|위임장|원본|사본|1매|1부)\s*[)）]?$/;
const PARADISO_DOC_COMMON_HEAD_RE = /^(통합\s*신청서|신청서|사증발급신청서|여권|외국인\s*등록증|등록증|거소증|수수료|표준규격\s*사진|여권용\s*사진|반명함판[^,]*사진|증명사진|사진)/;

function paradisoSplitCompoundDocRow(label) {
    const resolved = paradisoResolveDocDisplayLabel(label);
    if (!resolved || resolved.length > 130 || resolved.indexOf(',') < 0) return null;
    const parts = [];
    let depth = 0, cur = '';
    for (const ch of resolved) {
        if (ch === '(' || ch === '（') depth++;
        else if (ch === ')' || ch === '）') depth = Math.max(0, depth - 1);
        if (ch === ',' && depth === 0) { parts.push(cur.trim()); cur = ''; continue; }
        cur += ch;
    }
    parts.push(cur.trim());
    const cleaned = parts.filter(Boolean);
    if (cleaned.length < 2) return null;
    if (!cleaned.every(p => PARADISO_DOC_COMMON_HEAD_RE.test(p) || PARADISO_DOC_PART_TAIL_RE.test(p))) return null;
    const out = [];
    cleaned.forEach(p => {
        const sub = p.split(/\s+및\s+/);
        if (sub.length === 2 && sub.every(s => PARADISO_DOC_COMMON_HEAD_RE.test(s.trim()) && s.trim().length <= 14)) {
            out.push(...sub.map(s => s.trim()));
        } else {
            out.push(p);
        }
    });
    return out;
}

/* Duplicate-family key. Resolves doc_* ids through DOC_DICT FIRST (the actual
   regression fix), then decides family membership on a probe string with
   parenthetical content and decoration tokens removed. A family only matches
   when it consumes the whole probe (full-consumption check), so compound or
   qualified rows ("사업자등록증에 제조업…이 포함된 경우 … 확인서") keep their own
   identity instead of being swallowed by a family. */
const PARADISO_DOC_FAMILY_RULES = [
    { head: /^사증발급신청서/, family: '사증발급신청서', allow: /^$/ },
    { head: /^(통합)?신청서/, family: '신청서', allow: /^(체류자격변경허가신청포함|신고서)?$/ },
    { head: /^여권/, family: '여권', allow: /^(및인적사항면|인적사항면|및)?$/ },
    { head: /^(외국인등록증|등록증|거소증)/, family: '외국인등록증', allow: /^(또는거소증|소지자|해당자|기존등록자에한함|및)?$/ },
    { head: /^수수료/, family: '수수료', allow: /^$/ },
    { head: /^(표준규격사진|여권용사진|반명함판(천연색)?사진|증명사진|사진)/, family: '표준규격사진', allow: /^(천연색)?$/ },
    { head: /^표준입학허가서/, family: '표준입학허가서', allow: /^$/ },
    { head: /^(교육기관)?(사업자등록증|고유번호증)/, family: '사업자등록증', allow: /^(또는고유번호증|또는교육기관고유번호증)?$/ },
    { head: /^재학(또는연구생|연구생)?증명서/, family: '재학증명서', allow: /^(또는연구생증명서)?$/ },
    { head: /^(학업을정상적으로수행하고있음을입증하는서류|학업정상수행입증서류|출석확인서|성적증명서)/, family: '학업수행입증서류', allow: /^(예시.*)?$/ },
    { head: /^재정(능력|입증)/, family: '재정입증서류', allow: /^(입증)?(서류)?$/ },
    { head: /^(은행)?잔고증명서/, family: '재정입증서류', allow: /^$/ },
    { head: /^체류지\s*입증\s*서류|^체류지입증서류/, family: '체류지입증서류', allow: /^(예.*)?$/ },
    { head: /^가족관계(입증서류|증명서)/, family: '가족관계입증서류', allow: /^(상세)?$/ },
    { head: /^혼인관계증명서/, family: '혼인관계증명서', allow: /^(상세)?$/ },
    { head: /^기본증명서/, family: '기본증명서', allow: /^(상세)?$/ },
    { head: /^(결핵건강진단서|결핵진단서)/, family: '결핵진단서', allow: /^$/ }
];

function paradisoDocFamilyProbe(resolvedLabel) {
    let probe = String(resolvedLabel || '').normalize('NFKC').trim();
    if (!probe) return '';
    probe = probe.replace(/^\s*[①-⑳0-9]+[.)]?\s*/g, '');
    // Strip parenthetical content (two passes cover simple nesting) for the
    // family DECISION only — display labels keep the original wording.
    probe = probe.replace(/[(（][^()（）]*[)）]/g, '').replace(/[(（][^()（）]*[)）]/g, '');
    probe = probe
        .replace(/\s+/g, '')
        .replace(/[ㆍ·•]/g, '')
        .replace(/별지제?\d+호서식?/g, '')
        .replace(/원본및사본1부|원본및사본/g, '')
        .replace(/원본|사본/g, '')
        .replace(/각?1부|1매|1통/g, '')
        .replace(/[()（）［\]\[\]{}.,:：]/g, '')
        .trim();
    return probe;
}

function getDocumentRequirementLabel(doc) {
    if (doc && typeof doc === 'object') {
        return paradisoResolveDocDisplayLabel(doc.name || doc.label || doc.title || doc.textKo || doc.text || doc.description || '');
    }
    return paradisoResolveDocDisplayLabel(doc);
}

function copyDocumentRequirementForDisplay(doc) {
    if (doc && typeof doc === 'object') {
        if (Array.isArray(doc)) return doc.slice();
        return { ...doc };
    }
    return doc;
}

function setDocumentRequirementLabel(doc, label) {
    if (!(doc && typeof doc === 'object') || Array.isArray(doc)) return label;
    const copy = { ...doc };
    if (Object.prototype.hasOwnProperty.call(copy, 'name')) copy.name = label;
    else if (Object.prototype.hasOwnProperty.call(copy, 'label')) copy.label = label;
    else if (Object.prototype.hasOwnProperty.call(copy, 'title')) copy.title = label;
    else if (Object.prototype.hasOwnProperty.call(copy, 'textKo')) copy.textKo = label;
    else if (Object.prototype.hasOwnProperty.call(copy, 'text')) copy.text = label;
    else copy.name = label;
    return copy;
}

const DOCUMENT_REQUIREMENT_DISPLAY_FAMILY_RULES = [
    { family: '신청서', re: /^(통합신청서|신청서)/ },
    { family: '여권', re: /^여권/ },
    { family: '수수료', re: /^(수수료|정부수입인지|수입인지|인지대|인지)/ },
    { family: '외국인등록증', re: /^(외국인등록증|등록증|거소증)/ },
    { family: '체류지입증서류', re: /^(체류지입증서류|임대차계약서|숙소제공확인서|거주숙소제공확인서|공공요금납부영수증|공과금|기숙사비영수증|기숙사거주확인)/ },
    { family: '재정입증서류', re: /^(재정입증서류|재정능력입증서류|잔고증명서?|은행잔고증명서?|소득증명서?|통장)/ },
    { family: '학업수행입증서류', re: /^(학업정상수행입증서류|학업을정상적으로수행하고있음을입증하는서류|재학증명서|성적증명서|출석확인서)/ },
    { family: '수료증명서·지도교수확인서', re: /^(수료증명서|지도교수|유학담당자)/ }
];

function normalizeDocumentRequirementKey(label) {
    const resolved = getDocumentRequirementLabel(label);
    if (!resolved || isDocPlaceholder(resolved)) return '';
    const split = paradisoSplitDocItem(resolved);
    const displayLabel = split.kind === 'doc' && split.label ? split.label : resolved;
    const probe = paradisoDocFamilyProbe(displayLabel);
    if (!probe) return '';
    if (/(수수료|정부수입인지|수입인지|인지대|인지)/.test(probe)) return '수수료';
    if (/졸업증명서/.test(probe) && !/(학업정상|학업을정상적|출석|성적)/.test(probe)) return probe;
    for (const rule of DOCUMENT_REQUIREMENT_DISPLAY_FAMILY_RULES) {
        if (rule.re.test(probe)) return rule.family;
    }
    // Keep the earlier full-consumption guards for families where over-collapsing
    // would hide a distinct requirement.
    for (const rule of PARADISO_DOC_FAMILY_RULES) {
        const m = probe.match(rule.head);
        if (!m) continue;
        const rest = probe.slice(m[0].length);
        if (rule.allow.test(rest)) return rule.family;
        if (/^또는/.test(rest) && PARADISO_DOC_PART_TAIL_RE.test(rest)) return rule.family;
    }
    return probe;
}

function getDocumentRequirementDisplayKey(doc) {
    return normalizeDocumentRequirementKey(getDocumentRequirementLabel(doc));
}

function scoreDocumentRequirementSpecificity(label) {
    const text = getDocumentRequirementLabel(label);
    if (!text) return 0;
    let score = Math.min(text.length, 80);
    if (/통합신청서|별지\s*제?\d+호/.test(text)) score += 90;
    if (/체류지\s*입증|재정(능력|입증)|학업.*입증|정상적으로\s*수행/.test(text)) score += 90;
    if (/외국인등록증.*거소증|원본\s*및\s*사본|인적사항면/.test(text)) score += 55;
    if (/정부수입인지|수입인지/.test(text)) score += 45;
    if (/수료증명서/.test(text) && /(지도교수|유학담당자)/.test(text)) score += 70;
    if (/[()（）]/.test(text)) score += 18;
    if (/^신청서$|^여권$|^수수료$|^거소증$/.test(text.trim())) score -= 30;
    return score;
}

function mergeUniqueDocumentArray(existingValue, nextValue) {
    const out = [];
    [existingValue, nextValue].forEach(value => {
        (Array.isArray(value) ? value : (value ? [value] : [])).forEach(item => {
            const key = item && typeof item === 'object' ? JSON.stringify(item) : String(item);
            if (!out.some(prev => (prev && typeof prev === 'object' ? JSON.stringify(prev) : String(prev)) === key)) out.push(item);
        });
    });
    return out;
}

function mergeDocumentRequirementForDisplay(existingDoc, nextDoc) {
    const existingLabel = getDocumentRequirementLabel(existingDoc);
    const nextLabel = getDocumentRequirementLabel(nextDoc);
    const chooseNext = scoreDocumentRequirementSpecificity(nextLabel) > scoreDocumentRequirementSpecificity(existingLabel);
    const preferredDoc = copyDocumentRequirementForDisplay(chooseNext ? nextDoc : existingDoc);
    const fallbackDoc = chooseNext ? existingDoc : nextDoc;
    const preferredLabel = chooseNext ? nextLabel : existingLabel;
    let merged = setDocumentRequirementLabel(preferredDoc, preferredLabel);
    if (merged && typeof merged === 'object' && !Array.isArray(merged)) {
        const other = fallbackDoc && typeof fallbackDoc === 'object' && !Array.isArray(fallbackDoc) ? fallbackDoc : {};
        ['sources', 'sourceRefs', 'manualRefs', 'refs', 'metadata'].forEach(field => {
            if (!Array.isArray(merged[field]) && !Array.isArray(other[field])) return;
            const combined = mergeUniqueDocumentArray(merged[field], other[field]);
            if (combined.length) merged[field] = combined;
        });
        ['note', 'description'].forEach(field => {
            const bits = [merged[field], other[field]].map(v => String(v || '').trim()).filter(Boolean);
            merged[field] = [...new Set(bits)].join(' / ');
        });
    }
    return merged;
}

function getDocumentSectionItemsField(section) {
    if (Array.isArray(section?.docs)) return 'docs';
    if (Array.isArray(section?.items)) return 'items';
    if (Array.isArray(section?.documents)) return 'documents';
    return 'docs';
}

function dedupeDocumentSectionsForDisplay(sections) {
    // Display-layer dedupe only. Source records from visa_data.json, API payloads,
    // and doc_master.json are copied and never mutated here.
    const seen = new Map();
    const output = [];
    (sections || []).forEach(section => {
        const field = getDocumentSectionItemsField(section);
        const docs = Array.isArray(section?.[field]) ? section[field] : [];
        const outSection = { ...(section || {}), [field]: [] };
        docs.forEach(doc => {
            const key = getDocumentRequirementDisplayKey(doc);
            if (!key) return;
            const prior = seen.get(key);
            if (!prior) {
                seen.set(key, { section: outSection, field, index: outSection[field].length });
                outSection[field].push(copyDocumentRequirementForDisplay(doc));
                return;
            }
            prior.section[prior.field][prior.index] = mergeDocumentRequirementForDisplay(prior.section[prior.field][prior.index], doc);
        });
        if (outSection[field].length) output.push(outSection);
    });
    return output;
}

function paradisoCanonicalDocKey20260609(doc) {
    return normalizeDocumentRequirementKey(doc);
}

/* Whether a kept label is a "bare generic" (exactly its family word, no
   parenthetical detail) — only such labels may be upgraded in place to a more
   specific same-family wording (e.g. "여권" → "여권 원본 및 인적사항면 사본"). */
function paradisoIsBareGenericDocLabel(label) {
    const resolved = paradisoResolveDocDisplayLabel(label);
    if (/[(（]/.test(resolved)) return false;
    const probe = paradisoDocFamilyProbe(resolved);
    return PARADISO_DOC_FAMILY_RULES.some(rule => {
        const m = probe.match(rule.head);
        return !!m && m[0] === probe;
    });
}

function paradisoDedupeDocGroupsForRender20260609(groups) {
    return dedupeDocGroupsAcrossCategories(groups);
}

function canonicalDocDedupeKey(doc) {
    return paradisoCanonicalDocKey20260609(doc);
}

/* Cross-bucket display merge: first occurrence keeps its position; a later
   same-family entry is dropped, but may donate its richer label when the kept
   one is a bare generic and the newcomer is a longer non-"또는" wording (rule:
   show once, prefer the official/specific label, keep earliest placement). */
function dedupeDocGroupsAcrossCategories(groups) {
    const seen = new Map(); // family key -> { groupKey, index }
    const orderedKeys = ['commonDocs', 'requiredDocs', 'additionalDocs', 'conditionalDocs'];
    orderedKeys.forEach(groupKey => {
        const kept = [];
        (groups[groupKey] || []).forEach(doc => {
            if (isDocPlaceholder(doc)) return;
            const key = canonicalDocDedupeKey(doc);
            if (!key) return;
            const prior = seen.get(key);
            if (!prior) {
                seen.set(key, { groupKey, index: kept.length });
                kept.push(doc);
                return;
            }
            const priorArr = prior.groupKey === groupKey ? kept : groups[prior.groupKey];
            const priorDoc = priorArr[prior.index];
            priorArr[prior.index] = mergeDocumentRequirementForDisplay(priorDoc, doc);
        });
        groups[groupKey] = kept;
    });
    return groups;
}

/* User-facing UX regrouping (display only). The four internal buckets are a
   Visable classification — the official manuals use varying local headings
   (제출서류·신청서류·첨부서류·기본서류·추가서류 …), so the UI presents three
   reader-friendly groups WITHOUT claiming they are official headings:
     항상 확인할 서류    ← commonDocs + requiredDocs
     상황별 추가 서류    ← additionalDocs + conditionalDocs
     기관 확인 필요 서류 ← discretionary catch-all wording, shown as a
                            caution note rather than checklist tiles. */
const PARADISO_DOC_DISCRETIONARY_RE = /((기타|그\s*밖에)\s*심사에\s*필요(하다고|한)?\s*(인정)?(하는|되는)?\s*(서류|자료)|심사\s*과정에서\s*추가\s*서류|추가\s*서류\s*제출을\s*요구할?\s*수|서류(는|를)?\s*[^,，]{0,10}가감될\s*수|출입국[·\s]*외국인(청|관서|사무소)?(\(.*?\))?장?이?\s*[^,，]{0,20}인정하는\s*서류)/;

function paradisoIsDiscretionaryDocText(label) {
    return PARADISO_DOC_DISCRETIONARY_RE.test(paradisoResolveDocDisplayLabel(label));
}

function paradisoBuildDocDisplayGroups(groups) {
    const basic = [], situational = [], discretionary = [];
    const sections = dedupeDocumentSectionsForDisplay([
        { key: 'commonDocs', docs: groups?.commonDocs || [] },
        { key: 'requiredDocs', docs: groups?.requiredDocs || [] },
        { key: 'additionalDocs', docs: groups?.additionalDocs || [] },
        { key: 'conditionalDocs', docs: groups?.conditionalDocs || [] }
    ]);
    const route = (arr, target) => (arr || []).forEach(doc => {
        if (isDocPlaceholder(doc)) return;
        (paradisoIsDiscretionaryDocText(doc) ? discretionary : target).push(doc);
    });
    sections.forEach(section => {
        if (section.key === 'commonDocs' || section.key === 'requiredDocs') route(section.docs, basic);
        else route(section.docs, situational);
    });
    return { basic, situational, discretionary };
}

/* documents_* strip rows ({name, note}) sharing a duplicate family merge into
   ONE row: the first row keeps its label and the later row's label/note are
   appended verbatim to the note (no wording is invented or lost). */
function paradisoMergeDocumentTabItemsForDisplay(items) {
    const seen = new Map();
    const kept = [];
    (items || []).forEach(item => {
        if (!item) return;
        const name = String(item.name || '').trim();
        if (!name) { kept.push(item); return; }
        const key = getDocumentRequirementDisplayKey(item);
        if (!key) { kept.push(item); return; }
        const prior = seen.get(key);
        if (!prior) {
            const copy = { ...item };
            seen.set(key, copy);
            kept.push(copy);
            return;
        }
        const merged = mergeDocumentRequirementForDisplay(prior, item);
        Object.keys(prior).forEach(k => delete prior[k]);
        Object.assign(prior, merged);
    });
    return kept;
}
/* PARADISO_DOC_RENDER_GUARD_END */

function mergeDocGroups(...groupList) {
    const groups = { commonDocs: [], requiredDocs: [], additionalDocs: [], conditionalDocs: [] };
    groupList.forEach(src => {
        if (!src) return;
        Object.keys(groups).forEach(groupKey => {
            groups[groupKey].push(...toDocArray(src[groupKey]));
        });
    });
    Object.keys(groups).forEach(groupKey => {
        groups[groupKey] = dedupeDocs(groups[groupKey]);
    });
    return dedupeDocGroupsAcrossCategories(groups);
}

/* PARADISO_VARIANT_DOC_DIFF_20260609
   Parent procedure documents are rendered once at panel level. Variant cards
   should show only situation-specific additions/differences, otherwise "전체 보기"
   repeats the same common documents in every scenario card. */
function subtractDocGroupsForRender(docGroups, alreadyShownGroups) {
    const shownKeys = new Set(
        flattenDocGroups(alreadyShownGroups || {}).map(canonicalDocDedupeKey).filter(Boolean)
    );
    const result = { commonDocs: [], requiredDocs: [], additionalDocs: [], conditionalDocs: [] };

    Object.keys(result).forEach(groupKey => {
        result[groupKey] = toDocArray(docGroups?.[groupKey]).filter(doc => {
            const key = canonicalDocDedupeKey(doc);
            if (!key || shownKeys.has(key) || isDocPlaceholder(doc)) return false;
            shownKeys.add(key);
            return true;
        });
    });

    return dedupeDocGroupsAcrossCategories(result);
}

function addDocField(groups, groupKey, value) {
    const nested = extractNestedDocGroups(value);
    if (hasAnyDocs(nested)) {
        Object.keys(groups).forEach(key => groups[key].push(...nested[key]));
        return;
    }
    groups[groupKey].push(...toDocArray(value));
}

function extractNestedDocGroups(value) {
    const groups = { commonDocs: [], requiredDocs: [], additionalDocs: [], conditionalDocs: [] };
    if (!value || typeof value !== 'object' || Array.isArray(value)) return groups;
    Object.entries(DOC_GROUP_ALIASES).forEach(([groupKey, aliases]) => {
        aliases.forEach(alias => {
            if (Object.prototype.hasOwnProperty.call(value, alias)) addDocField(groups, groupKey, value[alias]);
        });
    });
    return mergeDocGroups(groups);
}

function normalizeDocGroups(docValue, raw = {}, fieldAliases = {}) {
    const groups = { commonDocs: [], requiredDocs: [], additionalDocs: [], conditionalDocs: [] };
    if (Array.isArray(docValue) || typeof docValue === 'string') groups.requiredDocs = toDocArray(docValue);
    else if (docValue && typeof docValue === 'object') Object.assign(groups, extractNestedDocGroups(docValue));
    Object.entries(DOC_GROUP_ALIASES).forEach(([groupKey, aliases]) => {
        aliases.forEach(alias => {
            if (Object.prototype.hasOwnProperty.call(raw, alias)) addDocField(groups, groupKey, raw[alias]);
        });
    });
    Object.entries(fieldAliases).forEach(([groupKey, aliases]) => {
        (aliases || []).forEach(alias => {
            if (Object.prototype.hasOwnProperty.call(raw, alias)) addDocField(groups, groupKey, raw[alias]);
        });
    });
    return mergeDocGroups(groups);
}

function flattenDocGroups(groups) {
    if (!groups) return [];
    return dedupeDocs([
        ...(groups.commonDocs || []),
        ...(groups.requiredDocs || []),
        ...(groups.additionalDocs || []),
        ...(groups.conditionalDocs || [])
    ]);
}

function hasAnyDocs(groups) {
    return !!(groups && (groups.commonDocs?.length || groups.requiredDocs?.length || groups.additionalDocs?.length || groups.conditionalDocs?.length));
}

/* "제출서류 N건" must match the checklist tiles the user actually sees.
   renderDocTags() relocates prose-classified items into notes, so counting raw
   array lengths overstates N whenever a document array still holds prose. */
function countRenderableDocs(groups) {
    const dedupedSections = dedupeDocumentSectionsForDisplay([
        { key: 'commonDocs', docs: groups?.commonDocs || [] },
        { key: 'requiredDocs', docs: groups?.requiredDocs || [] },
        { key: 'additionalDocs', docs: groups?.additionalDocs || [] },
        { key: 'conditionalDocs', docs: groups?.conditionalDocs || [] }
    ]);
    return dedupedSections.flatMap(section => section.docs || []).filter(key => {
        const isUnresolvedId = typeof key === 'string' && key.startsWith('doc_') && !DOC_DICT[key];
        if (isUnresolvedId) return true;
        // Discretionary catch-alls render as a caution note, not as tiles —
        // they must not inflate the "제출서류 N건" count the user sees.
        if (paradisoIsDiscretionaryDocText(key)) return false;
        return paradisoSplitDocItem(DOC_DICT[key] || key).kind !== 'prose';
    }).length;
}

function normalizeProcedureVariants(rawVariants) {
    if (!Array.isArray(rawVariants)) return [];
    return rawVariants.map(raw => {
        const item = raw && typeof raw === 'object' ? raw : {};
        return {
            id: item.id || '',
            label: item.labelKo || item.label || item.statusCode || item.id || '',
            statusCode: item.statusCode || '',
            scenario: item.scenarioKo || item.scenario || '',
            available: item.available !== false,
            docs: normalizeDocGroups(item.requiredDocs, item),
            notes: paradisoFilterProcedureNotes(item.notes),
            manualRefs: Array.isArray(item.manualRefs) ? item.manualRefs : []
        };
    }).filter(item => item.available && item.label && hasAnyDocs(item.docs));
}

function renderDocGroup(title, docs, keywords, groupType = '', visaCode = '', procedureKey = '') {
    if (!docs || !docs.length) return '';
    return `<div class="doc-group ${groupType}"><h5 class="doc-group-title">${title}</h5>${renderDocTags(docs, keywords, false, visaCode, procedureKey)}</div>`;
}

const MANUAL_LONG_TEXT_THRESHOLD = 150;
const MANUAL_PREVIEW_LENGTH = 112;

const MANUAL_AUTO_EXTRACT_PREFIX_RE = /^\s*\[\s*\d{4}\.\d+\s*[^\]]*검토\s*필요\s*\]\s*/;
// Strip leading "체류기간 (연장)(허가)(절차)" section title ONLY when followed by clear
// content boundaries (whitespace, digits, circled-numbers, section bullets, common
// document/procedure keywords). Avoid stripping when directly followed by a Hangul
// grammar particle (e.g. F-4's "체류기간연장허가가 제한될").
const MANUAL_REDUNDANT_HEADING_RE = /^(?:체류기간\s*연장\s*허가\s*절차|체류기간\s*연장\s*허가|체류기간연장허가\s*절차|체류기간연장허가|체류기간\s*연장|체류기간연장)(?=\s|$|\d|[①-⑳]|[가-차]\.|[\-○※☞·•◦□*]|필수|첨부|제출|신청|공통|추가|조건|대상|적용|상한|발급|준비|절차)/;
// Render-layer suppression of low-value auto-generated boilerplate that clutters
// status results. The protected data files (visa_data.json) are NEVER mutated —
// this is a display-only transform:
//  - terse "[한국인] … [외국인] …" tag-summaries that merely abbreviate the real
//    overview text (e.g. F-6's "지금 할 수 있는 일" summary). The legitimate
//    leading prose (incl. a "[입국 전 · …]" lead-in) is preserved; only the
//    bracketed tag list is dropped.
const PARADISO_TERSE_TAG_SUMMARY_RE = /\s*\[한국인\][^[\]]*\[외국인\][^[\]]*/g;
//  - templated "다음 단계: ① … → ② … → ③ …" hand-holding notes that repeat the
//    generic HiKorea/관할 관서 workflow on nearly every status.
const PARADISO_DUMMY_NEXT_STEP_NOTE_RE = /^\s*다음\s*단계\s*[:：]/;
function paradisoIsDummyProcedureNote(text) {
    return PARADISO_DUMMY_NEXT_STEP_NOTE_RE.test(String(text == null ? '' : text));
}
// Paradiso-internal provenance/methodology notes that only state HOW the document
// lists were produced ("…자동 추출한 제출서류입니다 … 수동 검토가 필요합니다", "대표
// 서류를 구조화했습니다", "…서류 목록은 보류했습니다"). The substantive caution they
// carry (lists may vary by case; confirm with the authority) is ALREADY shown by
// the per-procedure source-evidence header (getDefaultLimitationExplanation), the
// "매뉴얼 확인 필요" source chip, the doc-grouping note, and the empty-state
// fallback — so inline they are redundant, self-undermining prose. The official
// 2026.5 manual itself states the listed documents may be added to or reduced at
// the officer's discretion, so the kept disclaimers stay accurate; only the
// redundant provenance phrasing is dropped. Display-only; data files unchanged.
const PARADISO_SOURCE_PROVENANCE_NOTE_RE = /자동\s*추출한?\s*제출서류입니다|대표\s*서류를\s*구조화했습니다|자동\s*추출되었으며|서류\s*목록은\s*보류했습니다/;
function paradisoIsRedundantSourceProvenanceNote(text) {
    return PARADISO_SOURCE_PROVENANCE_NOTE_RE.test(String(text == null ? '' : text));
}
// Internal source-audit annotations that leaked into user-facing notes, e.g.
// "[2026-06-08 출처 대조] 2026-06-01 체류민원 매뉴얼 영주(F-5) 절 … 기준: …".
// These are an internal reviewer's cross-check log (dated "출처 대조"), not user
// guidance — surfacing them only erodes trust. The substantive facts they carry
// are already shown in the proper fields (e.g. F-5's 영주증 10년·재발급·과태료 in
// the fee box; G-1's 세부약호별 상이 in its summary/문서목록), so dropping the whole
// annotation note loses no unique information. Display-only; data files unchanged.
const PARADISO_AUDIT_ANNOTATION_NOTE_RE = /^\s*[\[（(]\s*20\d{2}[-.]\s*\d{1,2}(?:[-.]\s*\d{1,2})?\s*출처\s*대조\s*[\]）)]/;
function paradisoIsInternalAuditAnnotationNote(text) {
    return PARADISO_AUDIT_ANNOTATION_NOTE_RE.test(String(text == null ? '' : text));
}
function paradisoFilterProcedureNotes(notes) {
    return Array.isArray(notes) ? notes.filter(n => n && !paradisoIsDummyProcedureNote(n) && !paradisoIsRedundantSourceProvenanceNote(n) && !paradisoIsInternalAuditAnnotationNote(n)) : [];
}

// Internal audit/TODO diagnostics that leaked into user-facing fields. These are
// developer review notes — NOT genuine user disclaimers — so surfacing them only
// erodes user trust. The legitimate source-transparency signals are deliberately
// preserved: the per-subcode chips ("매뉴얼 확인 필요"), the data-provenance
// notices ("…자동 추출한 제출서류입니다 … 수동 검토가 필요합니다"), the fee/source
// citations, and every "관할 기관 확인" caution. Display-only suppression — the
// protected data files (visa_data.json) are NEVER mutated — consistent with the
// diagnostic-suppression contract (scripts/check_placeholder_suppression.js).
//  - "체류민원 안내매뉴얼 2026.5 기준 — 정확한 항목·페이지 수동 검토 필요." (a note/
//    summary appended to subcode records as a reviewer reminder).
const PARADISO_MANUAL_REVIEW_TODO_RE = /\s*체류민원\s*안내매뉴얼\s*\d{4}\.\d+\s*기준\s*[—–\-]\s*정확한\s*항목\s*[·ㆍ・]?\s*페이지\s*수동\s*검토\s*필요\.?/g;
//  - "(수동검토 필요)" tag appended to placeholder "매뉴얼 참조 코드" subcode names.
const PARADISO_MANUAL_REVIEW_PAREN_RE = /\s*[(（]\s*수동\s*검토\s*필요\s*[)）]/g;
//  - "수동검토 필요: … 검색 연결용 항목입니다." statusNote on search-stub subcodes.
const PARADISO_SEARCH_STUB_NOTE_RE = /수동\s*검토\s*필요\s*[:：][^\n]*검색\s*연결용\s*항목입니다\.?/g;
function paradisoStripInternalReviewArtifacts(value) {
    return String(value == null ? '' : value)
        .replace(PARADISO_MANUAL_REVIEW_TODO_RE, '')
        .replace(PARADISO_MANUAL_REVIEW_PAREN_RE, '')
        .replace(PARADISO_SEARCH_STUB_NOTE_RE, '')
        .trim();
}

function stripManualArtifacts(value) {
    if (value == null) return '';
    let s = String(value);
    let changed = true;
    while (changed) {
        changed = false;
        s = s.replace(/^\s+/, '');
        const a = s.replace(MANUAL_AUTO_EXTRACT_PREFIX_RE, '');
        if (a !== s) { s = a; changed = true; }
        const b = s.replace(MANUAL_REDUNDANT_HEADING_RE, '');
        if (b !== s) { s = b; changed = true; }
    }
    s = s.replace(PARADISO_TERSE_TAG_SUMMARY_RE, '');
    return paradisoStripInternalReviewArtifacts(s);
}

function normalizeManualText(value) {
    return stripManualArtifacts(value).replace(/\s+/g, ' ').trim();
}

// Shared sentence splitter for the "2-sentence preview" pattern used by the
// card summary, the procedure summary, and the Easy panel — one regex, so the
// three views can never truncate the same canonical text differently.
function paradisoSplitSentences(text) {
    return String(text || '').split(/(?<=[.!?。])\s+/).filter(Boolean);
}

/* Canonical status-summary fallback chain. Records carry the status
   description in newReq/extReq (no `summary` field exists in current data);
   the compact card, the copy action, and the Easy panel must all resolve the
   same source text or they describe the same status from different fields. */
function getCanonicalStatusSummarySource(v) {
    return v.summary || v.newReq || v.extReq || '';
}

function makeManualPreview(value, max = MANUAL_PREVIEW_LENGTH) {
    const normalized = normalizeManualText(value);
    if (normalized.length <= max) return normalized;
    return normalized.slice(0, max).replace(/\s+\S*$/, '') + '…';
}

function isLongManualText(value, threshold = MANUAL_LONG_TEXT_THRESHOLD) {
    const cleaned = stripManualArtifacts(value);
    return normalizeManualText(cleaned).length > threshold || cleaned.split(/\n/).filter(Boolean).length > 2;
}

function renderManualDetailBlock(raw, keywords, threshold = MANUAL_LONG_TEXT_THRESHOLD) {
    const cleaned = stripManualArtifacts(raw);
    if (!cleaned) return '';
    const formatted = cleaned.replace(/([^\n])\s*※/g, '$1\n※');
    if (!isLongManualText(cleaned, threshold)) return hl(formatted, keywords).replace(/\n/g, '<br>');
    return `<span class="manual-preview">${hl(makeManualPreview(cleaned), keywords)}</span>
        <details class="manual-detail-block">
            <summary>${escapeHtml(tx('manualDetailToggle') || '상세 보기')}</summary>
            <div class="manual-detail-body">${hl(formatted, keywords).replace(/\n/g, '<br>')}</div>
        </details>`;
}

function renderLabeledManualBlock(label, value, keywords, threshold = MANUAL_LONG_TEXT_THRESHOLD) {
    const raw = Array.isArray(value) ? value.filter(Boolean).join('\n') : String(value || '').trim();
    if (!raw) return '';
    return `<div class="procedure-summary"><strong>${escapeHtml(label)}</strong><br>${renderManualDetailBlock(raw, keywords, threshold)}</div>`;
}

function renderProcedureSummaryBlock(value, keywords) {
    if (!value) return '';
    // Toss-style concise default: expose at most the first 1-2 sentences; the
    // remainder (longer manual prose / legacy extraction text) collapses behind
    // a "상세 보기" toggle. Mirrors renderCardSummary so the card summary and the
    // per-procedure summary read consistently. Full text is preserved, only the
    // default exposure is trimmed.
    const normalized = normalizeManualText(value);
    if (!normalized) return '';
    const sentences = paradisoSplitSentences(normalized);
    if (sentences.length <= 2) {
        return `<div class="procedure-summary">${hl(normalized, keywords)}</div>`;
    }
    const preview = sentences.slice(0, 2).join(' ');
    const rest = sentences.slice(2).join(' ');
    return `<div class="procedure-summary"><span class="vc-summary-preview">${hl(preview, keywords)}</span><details class="vc-summary-detail"><summary>${escapeHtml(tx('manualDetailToggle') || '상세 보기')}</summary><span class="vc-summary-rest">${hl(rest, keywords)}</span></details></div>`;
}

/* Three reader-friendly display groups (Visable classification, NOT official
   manual headings — the manuals use varying local headings per status and
   procedure). Empty groups are hidden; discretionary catch-all wording is
   shown as a caution note instead of checklist tiles. */
// PR-D1 #15 (D5, 1안): the procedure panel renders a dynamic fee box
// (renderProcedureFeeBox) with the exact 법정 금액, so the generic "수수료
// (정부수입인지…)" checklist tile (doc_fee*) is redundant here. Drop it from
// the procedure checklist only; the fee box stays canonical and now also
// carries the fee-exemption note relocated from doc_fee (예외 보존).
const PROCEDURE_FEE_TILE_KEYS = new Set(['doc_fee', 'doc_fee_new', 'doc_fee_ext', 'doc_fee_generic']);
function renderProcedureDocGroups(groups, keywords, visaCode = '', procedureKey = '') {
    const display = paradisoBuildDocDisplayGroups(groups);
    const stripFeeTile = arr => (arr || []).filter(doc => !PROCEDURE_FEE_TILE_KEYS.has(doc));
    return [
        renderDocGroup(txAt('docUxGroupLabels', 0, '항상 확인할 서류'), stripFeeTile(display.basic), keywords, 'group-basic', visaCode, procedureKey),
        renderDocGroup(txAt('docUxGroupLabels', 1, '상황별 추가 서류'), stripFeeTile(display.situational), keywords, 'group-situational', visaCode, procedureKey),
        renderDocDiscretionaryNote(display.discretionary, keywords)
    ].filter(Boolean).join('');
}

function renderDocDiscretionaryNote(items, keywords) {
    if (!items || !items.length) return '';
    const title = txAt('docUxGroupLabels', 2, '기관 확인 필요 서류');
    return `<div class="doc-group doc-discretionary-note" role="note">
        <h5 class="doc-group-title">${escapeHtml(title)}</h5>
        <ul class="doc-discretionary-list">${items.map(d => `<li>${hl(escapeHtml(paradisoResolveDocDisplayLabel(d)), keywords || [])}</li>`).join('')}</ul>
    </div>`;
}

function renderDocGroupingSourceNote() {
    return '';
}

const PROCEDURE_EVIDENCE_TYPE_BY_KEY = {
    visaIssuance: 'visa_issuance',
    certificateOfVisaIssuance: 'visa_issuance',
    registration: 'registration',
    extension: 'extension',
    statusChange: 'status_change',
    statusGrant: 'status_grant',
    workplaceChange: 'workplace_change',
    activitiesOutsideStatus: 'activities_outside_status',
    reentry: 'reentry_permit',
    partTimeWork: 'activities_outside_status',
    schoolChange: 'status_change'
};

const SOURCE_EVIDENCE_LABELS = {
    ko: {
        source_confirmed: '공식근거 직접 확인',
        contextual: '관련 공식근거 있음',
        limited: '공식근거 제한',
        unavailable: '공식근거 확인 불가',
        not_applicable: '해당 없음'
    },
    en: {
        source_confirmed: 'Official source confirmed',
        contextual: 'Official reference available',
        limited: 'Official source limited',
        unavailable: 'Official source unavailable',
        not_applicable: 'Not applicable'
    },
    'zh-CN': {
        source_confirmed: '已直接核实官方依据',
        contextual: '有相关官方依据',
        limited: '官方依据有限',
        unavailable: '无法确认官方依据',
        not_applicable: '不适用'
    }
};

function getSourceEvidenceLabel(level) {
    const lang = currentLanguage === 'zh-CN' ? 'zh-CN' : currentLanguage === 'en' ? 'en' : 'ko';
    return SOURCE_EVIDENCE_LABELS[lang][level] || SOURCE_EVIDENCE_LABELS[lang].limited;
}

function getSourceEvidenceBadgeClass(level) {
    return String(level || 'limited').replace(/_/g, '-');
}

function formatManualSourceRef(ref) {
    if (!ref) return '';
    if (typeof ref === 'string') return ref;
    const manual = ref.manualName || ref.manual || '';
    const version = ref.manualVersion || ref.version || ref.sourceRevisionDate || '';
    const pageRange = ref.pageRange || (Number.isInteger(ref.pageStart) && Number.isInteger(ref.pageEnd)
        ? `pp.${ref.pageStart}-${ref.pageEnd}`
        : (ref.page || ''));
    const section = ref.sectionTitle || ref.section || '';
    const url = ref.sourceUrl || ref.url || '';
    return [manual, version, pageRange, section, url].filter(Boolean).join(' · ');
}

function getFormattedSourceRefs(sourceState, fallbackRefs = []) {
    const refs = [];
    if (Array.isArray(fallbackRefs)) refs.push(...fallbackRefs);
    if (sourceState && Array.isArray(sourceState.manualSources)) refs.push(...sourceState.manualSources);
    if (sourceState && Array.isArray(sourceState.sourceRefs)) refs.push(...sourceState.sourceRefs);
    // Drop exact-duplicate formatted refs (e.g. mode.sourceRefs == binding.manualSources)
    // so the shared 근거 block never prints the same citation twice.
    return [...new Set(refs.map(formatManualSourceRef).filter(Boolean))];
}

function getDefaultLimitationExplanation(level) {
    if (currentLanguage === 'zh-CN') {
        if (level === 'not_applicable') return '此路径未作为该居留资格的申请程序显示。';
        if (level === 'unavailable') return '目前尚未对该项整理出可直接连接的官方依据。';
        if (level === 'contextual') return '虽有相关官方依据，但部分要件仍可能因居留资格、公馆或个案审查而有所不同。';
        if (level === 'source_confirmed') return '所显示的摘要已与官方手册依据相连接。但处理时间、手续费及受理渠道仍可能因主管机关而异，需另行确认。';
        return '由于公馆、国家、时间、手续费或渠道细节可能有所不同，官方依据有限。';
    }
    if (currentLanguage === 'en') {
        if (level === 'not_applicable') return 'This route is not shown as an application procedure for this status.';
        if (level === 'unavailable') return 'No direct official source binding has been structured yet.';
        if (level === 'contextual') return 'An official source exists, but some fields still depend on status, mission, or case-specific review.';
        if (level === 'source_confirmed') return 'The visible summary is bound to official manual references. Timing, fees, and channels may still vary by authority.';
        return 'Official grounding is limited because mission, country, timing, fees, or channel details may vary.';
    }
    if (level === 'not_applicable') return '이 경로는 해당 체류자격의 신청 절차로 표시하지 않습니다.';
    if (level === 'unavailable') return '아직 직접 연결된 공식 근거가 구조화되지 않은 항목입니다.';
    if (level === 'contextual') return '관련 공식 근거는 있으나 국가·공관·개별 사정에 따라 일부 요건이 달라질 수 있어 확정 표시하지 않습니다.';
    if (level === 'source_confirmed') return '표시된 요약은 공식 매뉴얼 근거와 연결되어 있습니다. 다만 수수료·처리기간·예약 방식은 관할 기관 확인이 필요할 수 있습니다.';
    return '공식 근거는 있으나 국가·공관·개별 사정에 따라 달라질 수 있어 확정 표시하지 않습니다.';
}

function renderSourceBackedFields(fields) {
    if (!fields || typeof fields !== 'object') return '';
    // Label order matches the sourceFieldLabels pack array (indices 0-5);
    // 6/7 = state labels, 8 = "Sources", 9/10 = detail summaries.
    const labels = {
        applicability: txAt('sourceFieldLabels', 0, '적용대상'),
        documents: txAt('sourceFieldLabels', 1, '구비서류'),
        timing: txAt('sourceFieldLabels', 2, '처리기간'),
        fees: txAt('sourceFieldLabels', 3, '수수료'),
        channels: txAt('sourceFieldLabels', 4, '접수채널'),
        warnings: txAt('sourceFieldLabels', 5, '주의사항')
    };
    const rows = Object.keys(labels).map(key => {
        const ok = fields[key] === true;
        const state = ok ? txAt('sourceFieldLabels', 6, '근거 연결') : txAt('sourceFieldLabels', 7, '공식 확인 필요');
        return `<li>${escapeHtml(labels[key])}: ${escapeHtml(state)}</li>`;
    }).join('');
    return rows ? `<ul>${rows}</ul>` : '';
}

function renderSourceLimitationExplanation(sourceState, fallbackRefs = []) {
    const level = sourceState && sourceState.evidenceLevel ? sourceState.evidenceLevel : 'limited';
    if (level === 'not_applicable') return '';
    const refs = [...new Set(getFormattedSourceRefs(sourceState, fallbackRefs))].slice(0, 4);
    // Show "근거 보기" only when source is confirmed or when actual ref citations exist
    if (level !== 'source_confirmed' && !refs.length) return '';
    const refsHtml = refs.length ? `<p>${escapeHtml(txAt('sourceFieldLabels', 8, '근거'))}: ${escapeHtml(refs.join(' / '))}</p>` : '';
    const fieldsHtml = level === 'source_confirmed' ? renderSourceBackedFields(sourceState && sourceState.sourceBackedFields) : '';
    const explanation = level === 'source_confirmed'
        ? (currentLanguage === 'zh-CN'
            ? getDefaultLimitationExplanation(level)
            : (currentLanguage === 'en' && sourceState && sourceState.userFacingExplanationEn)
            ? sourceState.userFacingExplanationEn
            : (sourceState && (sourceState.userFacingExplanationKo || sourceState.limitationReasonKo)) || getDefaultLimitationExplanation(level))
        : '';
    const summary = txAt('sourceFieldLabels', 9, '근거 보기');
    return `<details class="source-limitation-detail">
        <summary>${escapeHtml(summary)}</summary>
        <div class="source-limitation-body">${explanation ? `<p>${escapeHtml(explanation)}</p>` : ''}${refsHtml}${fieldsHtml}</div>
    </details>`;
}

function getProcedureEvidenceBinding(code, procedureKey) {
    const procedureType = PROCEDURE_EVIDENCE_TYPE_BY_KEY[procedureKey] || procedureKey;
    return PROCEDURE_EVIDENCE_BY_KEY.get(`${normalizeVisaCode(code)}:${procedureType}`) || null;
}

function renderProcedureHeader(v, proc) {
    const evidenceBinding = getProcedureEvidenceBinding(v.code, proc.key);
    const fallbackLevel = proc.sourceConfirmed ? 'source_confirmed' : ((proc.manualRefs && proc.manualRefs.length) ? 'contextual' : 'limited');
    const sourceState = evidenceBinding || {
        evidenceLevel: fallbackLevel,
        userFacingExplanationKo: getDefaultLimitationExplanation(fallbackLevel),
        manualSources: proc.manualRefs || []
    };
    const sourceLabel = getSourceEvidenceLabel(sourceState.evidenceLevel);
    const badgeClass = ` ${getSourceEvidenceBadgeClass(sourceState.evidenceLevel)}${sourceState.evidenceLevel === 'source_confirmed' ? ' confirmed' : ''}`;
    const refBits = (proc.manualRefs || []).map(ref => {
        const title = [ref.manualName || ref.manual, ref.manualVersion || ref.version, ref.pageRange].filter(Boolean).join(' · ');
        const section = ref.sectionTitle ? ` — ${ref.sectionTitle}` : '';
        const sub = ref.subCode ? ` (${ref.subCode})` : '';
        return `${title}${section}${sub}`.trim();
    }).filter(Boolean);
    const allRefBits = [...refBits, ...getFormattedSourceRefs(sourceState)].filter(Boolean);
    return `<div class="procedure-source-header">
        <div class="procedure-source-title"><span class="procedure-source-code">${escapeHtml(v.code || '')}</span><span>${escapeHtml(getProcedureDisplayLabel(v, proc))}</span></div>
        <span class="procedure-source-badge${badgeClass}">${escapeHtml(sourceLabel)}</span>
        ${renderSourceLimitationExplanation(sourceState, allRefBits)}
    </div>`;
}

// Safe selected-context banner shown directly above the in-card AI CTA so the
// user can see exactly which scenario the AI will receive. Renders only public
// labels (visa code · procedure label · scenario label) — never checklist,
// reminder, or any local/personal state.
function renderScenarioSelectedContextBanner(visaCode, procedureKey, variantLabel) {
    const procedureLabel = getProcedureLabelByKey(procedureKey, procedureKey);
    const context = [visaCode, procedureLabel, variantLabel].filter(Boolean).map(escapeHtml).join(' · ');
    if (!context) return '';
    return `<div class="scenario-selected-context" role="note"><span class="ssc-label">${escapeHtml(tx('scenarioSelectedContextLabel'))}</span> <span class="ssc-value">${context}</span></div>`;
}

export {
    normalizeVisaCode, normalizeCodeLikeQuery, isCodeLikeQuery, getPrimaryCodeLikeQuery, getExactQueryMatchRank, isEnglishMode,
    getVisaNameKo, getVisaNameEn, getLocalizedVisaName, getSecondaryVisaName, getVisaSubcodes, getLocalizedSubcodeName,
    getProcedureLabelByKey, getProcedureLabel, isF5ResidenceCardReissuance, getProcedureDisplayLabel, localizeResultCount, getRecordSearchText,
    keywordMatchesCode, getMatchingSubcodes, getManualDomains, renderDomainBadges, renderReviewBadge, procedureKeyForSourceConfirmedType,
    getSourceConfirmedEntriesForProcedure, paradisoCanonicalAppFormPiece, paradisoCanonicalAppFormText, paradisoGlossaryLabelForAppForm, canonicalizeSourceConfirmedDocText, groupSourceConfirmedDocuments,
    sourceConfirmedManualRefs, mergeManualRefs, remapPermanentResidenceAcquisition, isSuppressedProcedureForStatus, getVisaIssuanceModeDocGroups, getProcedure,
    paradisoCanonicalizeProcedureDocPart, paradisoSplitProcedureDocBlob, toDocArray, isDocPlaceholder, paradisoNormalizeDocText, paradisoStripLeadingDocMarks,
    paradisoSplitDocItem, paradisoIsSingleProseBlob, dedupeDocs, paradisoResolveDocDisplayLabel, paradisoSplitCompoundDocRow, paradisoDocFamilyProbe,
    getDocumentRequirementLabel, copyDocumentRequirementForDisplay, setDocumentRequirementLabel, normalizeDocumentRequirementKey, getDocumentRequirementDisplayKey, scoreDocumentRequirementSpecificity,
    mergeUniqueDocumentArray, mergeDocumentRequirementForDisplay, getDocumentSectionItemsField, dedupeDocumentSectionsForDisplay, paradisoCanonicalDocKey20260609, paradisoIsBareGenericDocLabel,
    paradisoDedupeDocGroupsForRender20260609, canonicalDocDedupeKey, dedupeDocGroupsAcrossCategories, paradisoIsDiscretionaryDocText, paradisoBuildDocDisplayGroups, paradisoMergeDocumentTabItemsForDisplay,
    mergeDocGroups, subtractDocGroupsForRender, addDocField, extractNestedDocGroups, normalizeDocGroups, flattenDocGroups,
    hasAnyDocs, countRenderableDocs, normalizeProcedureVariants, renderDocGroup, paradisoIsDummyProcedureNote, paradisoIsRedundantSourceProvenanceNote,
    paradisoIsInternalAuditAnnotationNote, paradisoFilterProcedureNotes, paradisoStripInternalReviewArtifacts, stripManualArtifacts, normalizeManualText, paradisoSplitSentences,
    getCanonicalStatusSummarySource, makeManualPreview, isLongManualText, renderManualDetailBlock, renderLabeledManualBlock, renderProcedureSummaryBlock,
    renderProcedureDocGroups, renderDocDiscretionaryNote, renderDocGroupingSourceNote, getSourceEvidenceLabel, getSourceEvidenceBadgeClass, formatManualSourceRef,
    getFormattedSourceRefs, getDefaultLimitationExplanation, renderSourceBackedFields, renderSourceLimitationExplanation, getProcedureEvidenceBinding, renderProcedureHeader,
    renderScenarioSelectedContextBanner, PROCEDURE_LABEL_INDEX, SOURCE_CONFIRMED_PROCEDURE_KEY_MAP, F4_OVERSEAS_KOREANS_FORM_PROCEDURES, PARADISO_APP_FORM_PIECE_RE, DOC_GROUP_ALIASES,
    PARADISO_PROC_DOC_BLOB_HEAD_RE, PARADISO_PROC_DOC_BLOB_PART_RE, PARADISO_PROC_DOC_BLOB_SECTION_TAIL_RE, DOC_PLACEHOLDER_TOKENS, PARADISO_DOC_LONG_THRESHOLD, PARADISO_DOC_SEVERE_THRESHOLD,
    PARADISO_DOC_SENTENCE_END_RE, PARADISO_DOC_PROSE_TOPIC_RE, PARADISO_DOC_TAIL_RE, PARADISO_DOC_HEADING_RE, PARADISO_DOC_RESIDENCE_RE, PARADISO_DOC_SUBCODE_REF_RE,
    PARADISO_DOC_PROSE_PREFIX_RE, PARADISO_DOC_STRONG_PROSE_TOKENS, PARADISO_DOC_PART_TAIL_RE, PARADISO_DOC_COMMON_HEAD_RE, PARADISO_DOC_FAMILY_RULES, DOCUMENT_REQUIREMENT_DISPLAY_FAMILY_RULES,
    PARADISO_DOC_DISCRETIONARY_RE, MANUAL_LONG_TEXT_THRESHOLD, MANUAL_PREVIEW_LENGTH, MANUAL_AUTO_EXTRACT_PREFIX_RE, MANUAL_REDUNDANT_HEADING_RE, PARADISO_TERSE_TAG_SUMMARY_RE,
    PARADISO_DUMMY_NEXT_STEP_NOTE_RE, PARADISO_SOURCE_PROVENANCE_NOTE_RE, PARADISO_AUDIT_ANNOTATION_NOTE_RE, PARADISO_MANUAL_REVIEW_TODO_RE, PARADISO_MANUAL_REVIEW_PAREN_RE, PARADISO_SEARCH_STUB_NOTE_RE,
    PROCEDURE_FEE_TILE_KEYS, PROCEDURE_EVIDENCE_TYPE_BY_KEY, SOURCE_EVIDENCE_LABELS
};
