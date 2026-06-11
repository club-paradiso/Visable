#!/usr/bin/env node

const fs = require('fs');
const path = require('path');

const repoRoot = path.resolve(__dirname, '..', '..');
const visaData = JSON.parse(fs.readFileSync(path.join(repoRoot, 'visa_data.json'), 'utf8'));
const docMasterRaw = JSON.parse(fs.readFileSync(path.join(repoRoot, 'doc_master.json'), 'utf8'));

const DOC_DICT = {};
Object.values(docMasterRaw || {}).forEach(entry => {
  if (entry && typeof entry === 'object' && entry.id) DOC_DICT[entry.id] = entry.ko_name || entry.name || entry.label || entry.id;
});

const PROCEDURE_CONFIG = [
  { key: 'visaIssuance', label: '사증발급', oldDocs: ['initialReqDocs', 'newReqDocs'], oldText: 'newReq', docFields: { requiredDocs: ['initialReqDocs', 'newReqDocs', 'reqDocs', 'documents', 'requiredDocs', 'required_documents'], additionalDocs: ['addReqDocs'] } },
  { key: 'certificateOfVisaIssuance', label: '사증발급인정서', oldDocs: ['cviReqDocs'] },
  { key: 'statusChange', label: '체류자격 변경', oldDocs: ['changeReqDocs'], oldText: 'changeReq', docFields: { requiredDocs: ['changeReqDocs', 'chgReqDocs'] } },
  { key: 'extension', label: '체류기간 연장', oldDocs: ['extensionReqDocs', 'extReqDocs'], oldText: 'extReq', docFields: { requiredDocs: ['extensionReqDocs', 'extReqDocs'] } },
  { key: 'statusGrant', label: '체류자격 부여', oldDocs: ['statusGrantReqDocs'] },
  { key: 'registration', label: '외국인등록', oldDocs: ['registrationReqDocs'] },
  { key: 'activitiesOutsideStatus', label: '자격외활동', oldDocs: ['activitiesOutsideStatusReqDocs'] },
  { key: 'workplaceChange', label: '근무처 변경·추가', oldDocs: ['workplaceChangeReqDocs'] },
  { key: 'reentry', label: '재입국', oldDocs: ['reentryReqDocs'] }
];

const DOC_GROUP_ALIASES = {
  commonDocs: ['commonDocs', 'common_documents', 'common'],
  requiredDocs: ['requiredDocs', 'required_documents', 'reqDocs', 'documents', 'document', 'docs', 'required'],
  additionalDocs: ['additionalDocs', 'additional_documents', 'addReqDocs', 'addReq', 'additional'],
  conditionalDocs: ['conditionalDocs', 'conditional_documents', 'conditional']
};

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

const DOC_PLACEHOLDER_TOKENS = new Set([
  '매뉴얼 확인 필요',
  '페이지 확인 필요',
  'Manual review needed',
  'Page review needed',
  '문서명 미상',
  '비고 정보 없음',
  'DATA_MISSING',
  'Document name unknown',
  'No note available'
]);

const DISCRETIONARY_RE = /((기타|그\s*밖에)\s*심사에\s*필요(하다고|한)?\s*(인정)?(하는|되는)?\s*(서류|자료)|심사\s*과정에서\s*추가\s*서류|추가\s*서류\s*제출을\s*요구할?\s*수|서류(는|를)?\s*[^,，]{0,10}가감될\s*수|출입국[·\s]*외국인(청|관서|사무소)?(\(.*?\))?장?이?\s*[^,，]{0,20}인정하는\s*서류)/;
const HIGH_CONFIDENCE_BASIC_RE = /(별거|이혼|실종|사망|혼인단절|해당\s*시|사안별\s*해당|필요\s*시|요청\s*시|입증서류\s*추가|별도\s*제출)/;
const REVIEW_BASIC_RE = /(경우|자녀|초청인|피부양|기타|사안|심사에\s*필요하다고\s*인정되는|추가서류|수동\s*검토|자동\s*추출|세부약호|대상자|해당자)/;
const ALLOWED_COMMON_RE = /^(체류지\s*입증서류|체류지입증서류|가족관계증명서|가족관계\s*입증서류|사업자등록증|고유번호증|수수료|여권|외국인등록증|통합신청서|신청서|표준규격사진|사진|혼인관계증명서|기본증명서|소득금액증명원|재정|잔고증명서|구직활동계획서|학력\s*입증서류|체류비\s*입증서류|한국어능력\s*입증서류)/;

function isDocPlaceholder(value) {
  return DOC_PLACEHOLDER_TOKENS.has(String(value || '').trim());
}

function resolveDocLabel(entry) {
  if (entry && typeof entry === 'object') {
    return String(entry.name || entry.label || entry.title || entry.textKo || entry.text || entry.description || '').trim();
  }
  const raw = String(entry == null ? '' : entry).trim();
  return DOC_DICT[raw] || raw;
}

function toDocArray(value) {
  if (!value) return [];
  if (Array.isArray(value)) return value.flatMap(toDocArray);
  if (typeof value === 'object') {
    const nested = extractNestedDocGroups(value);
    if (hasAnyDocs(nested)) return flattenDocGroups(nested);
    return [resolveDocLabel(value)].filter(v => v && !isDocPlaceholder(v));
  }
  return String(value)
    .split(/\n|;/)
    .map(v => v.trim())
    .filter(v => v && !isDocPlaceholder(v))
    .flatMap(splitCompoundDocRow);
}

function splitCompoundDocRow(value) {
  const label = resolveDocLabel(value);
  if (!label || label.length > 130 || !label.includes(',')) return [label];
  const parts = [];
  let depth = 0;
  let current = '';
  for (const ch of label) {
    if (ch === '(' || ch === '（') depth += 1;
    else if (ch === ')' || ch === '）') depth = Math.max(0, depth - 1);
    if (ch === ',' && depth === 0) {
      parts.push(current.trim());
      current = '';
    } else {
      current += ch;
    }
  }
  parts.push(current.trim());
  const cleaned = parts.filter(Boolean);
  if (cleaned.length < 2) return [label];
  const docLike = /^(통합\s*신청서|신청서|여권|외국인\s*등록증|등록증|거소증|수수료|표준규격\s*사진|사진)|(?:서류|증명서|확인서|신청서|신고서|계약서|등록증|영수증|진단서|보증서|입증자료|여권|사진|수수료|등본|초본|사본|원본)\s*$/;
  return cleaned.every(part => docLike.test(part)) ? cleaned : [label];
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
  const groups = emptyGroups();
  if (!value || typeof value !== 'object' || Array.isArray(value)) return groups;
  Object.entries(DOC_GROUP_ALIASES).forEach(([groupKey, aliases]) => {
    aliases.forEach(alias => {
      if (Object.prototype.hasOwnProperty.call(value, alias)) addDocField(groups, groupKey, value[alias]);
    });
  });
  return mergeDocGroups(groups);
}

function normalizeDocGroups(docValue, raw = {}, fieldAliases = {}) {
  const groups = emptyGroups();
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

function emptyGroups() {
  return { commonDocs: [], requiredDocs: [], additionalDocs: [], conditionalDocs: [] };
}

function hasAnyDocs(groups) {
  return !!(groups && (groups.commonDocs?.length || groups.requiredDocs?.length || groups.additionalDocs?.length || groups.conditionalDocs?.length));
}

function flattenDocGroups(groups) {
  return [
    ...(groups?.commonDocs || []),
    ...(groups?.requiredDocs || []),
    ...(groups?.additionalDocs || []),
    ...(groups?.conditionalDocs || [])
  ];
}

function docProbe(label) {
  return resolveDocLabel(label)
    .normalize('NFKC')
    .replace(/[(（][^()（）]*[)）]/g, '')
    .replace(/\s+/g, '')
    .replace(/[ㆍ·•]/g, '')
    .replace(/별지제?\d+호서식?/g, '')
    .replace(/원본및사본1부|원본및사본|원본|사본|각?1부|1매|1통/g, '')
    .replace(/[()（）［\]\[\]{}.,:：]/g, '')
    .trim();
}

function displayKey(doc) {
  const probe = docProbe(doc);
  if (!probe) return '';
  const families = [
    [/^(통합)?신청서/, '신청서'],
    [/^여권/, '여권'],
    [/^(수수료|정부수입인지|수입인지|인지대|인지)/, '수수료'],
    [/^(외국인등록증|등록증|거소증)/, '외국인등록증'],
    [/^(체류지입증서류|임대차계약서|숙소제공확인서|거주숙소제공확인서|공공요금납부영수증|공과금|기숙사비영수증|기숙사거주확인)/, '체류지입증서류'],
    [/^(재정입증서류|재정능력입증서류|잔고증명서?|은행잔고증명서?|소득증명서?|통장)/, '재정입증서류'],
    [/^(학업정상수행입증서류|학업을정상적으로수행하고있음을입증하는서류|재학증명서|성적증명서|출석확인서)/, '학업수행입증서류'],
    [/^혼인관계증명서/, '혼인관계증명서'],
    [/^가족관계(입증서류|증명서)/, '가족관계입증서류'],
    [/^기본증명서/, '기본증명서']
  ];
  for (const [re, family] of families) {
    if (re.test(probe)) return family;
  }
  return probe;
}

function mergeDocGroups(...groupList) {
  const groups = emptyGroups();
  groupList.forEach(src => {
    if (!src) return;
    Object.keys(groups).forEach(key => groups[key].push(...toDocArray(src[key])));
  });
  Object.keys(groups).forEach(key => {
    const seen = new Set();
    groups[key] = groups[key].filter(doc => {
      const label = resolveDocLabel(doc);
      if (!label || isDocPlaceholder(label)) return false;
      const rawKey = String(label);
      if (seen.has(rawKey)) return false;
      seen.add(rawKey);
      return true;
    });
  });
  return dedupeAcrossSections(groups);
}

function dedupeAcrossSections(groups) {
  const seen = new Set();
  ['commonDocs', 'requiredDocs', 'additionalDocs', 'conditionalDocs'].forEach(groupKey => {
    groups[groupKey] = (groups[groupKey] || []).filter(doc => {
      const key = displayKey(doc);
      if (!key || seen.has(key)) return false;
      seen.add(key);
      return true;
    });
  });
  return groups;
}

function procedureKeyForSourceConfirmedType(type) {
  return SOURCE_CONFIRMED_PROCEDURE_KEY_MAP[String(type || '').trim().toLowerCase()] || '';
}

function groupSourceConfirmedDocuments(record, procedureKey) {
  const groups = emptyGroups();
  const entries = Array.isArray(record.sourceConfirmedStructuredRequirements) ? record.sourceConfirmedStructuredRequirements : [];
  entries
    .filter(entry => procedureKeyForSourceConfirmedType(entry?.procedureType) === procedureKey)
    .forEach(entry => {
      (entry.documents || []).forEach(doc => {
        const text = resolveDocLabel(doc?.textKo || doc?.text || doc?.name);
        if (!text || isDocPlaceholder(text)) return;
        const requiredness = String(doc?.requiredness || '').toLowerCase();
        if (/common|basic|공통|기본/.test(requiredness)) groups.commonDocs.push(text);
        else if (/conditional|condition|조건/.test(requiredness)) groups.conditionalDocs.push(text);
        else if (/additional|review|supplement|추가|심사/.test(requiredness)) groups.additionalDocs.push(text);
        else groups.requiredDocs.push(text);
      });
    });
  return mergeDocGroups(groups);
}

function getProcedureGroups(record, cfg) {
  const raw = record.procedures && record.procedures[cfg.key] ? record.procedures[cfg.key] : null;
  const structuredDocs = groupSourceConfirmedDocuments(record, cfg.key);
  const rawDocs = normalizeDocGroups(raw?.requiredDocs, raw || {});
  const legacyDocs = normalizeDocGroups(null, record, {
    commonDocs: ['commonDocs'],
    requiredDocs: cfg.docFields?.requiredDocs || cfg.oldDocs || [],
    additionalDocs: ['additionalDocs', ...(cfg.docFields?.additionalDocs || [])],
    conditionalDocs: ['conditionalDocs']
  });
  return hasAnyDocs(structuredDocs) || hasAnyDocs(rawDocs)
    ? mergeDocGroups(structuredDocs, rawDocs)
    : mergeDocGroups(legacyDocs);
}

function getVariantGroups(variant) {
  return normalizeDocGroups(variant?.requiredDocs, variant || {});
}

function buildDisplayGroups(groups) {
  const display = { basic: [], situational: [], discretionary: [] };
  const deduped = dedupeAcrossSections({
    commonDocs: [...(groups.commonDocs || [])],
    requiredDocs: [...(groups.requiredDocs || [])],
    additionalDocs: [...(groups.additionalDocs || [])],
    conditionalDocs: [...(groups.conditionalDocs || [])]
  });
  const route = (docs, target) => {
    (docs || []).forEach(doc => {
      const label = resolveDocLabel(doc);
      if (!label || isDocPlaceholder(label)) return;
      if (DISCRETIONARY_RE.test(label)) display.discretionary.push(label);
      else display[target].push(label);
    });
  };
  route(deduped.commonDocs, 'basic');
  route(deduped.requiredDocs, 'basic');
  route(deduped.additionalDocs, 'situational');
  route(deduped.conditionalDocs, 'situational');
  return display;
}

function classifyBasicLabel(label, scope) {
  const text = resolveDocLabel(label);
  const context = `${scope.title || ''} ${scope.procedureKey || ''} ${scope.variantLabel || ''} ${scope.statusCode || ''}`;
  if (!text) return 'OK_COMMON';
  if (ALLOWED_COMMON_RE.test(text)) return 'OK_COMMON';
  if (HIGH_CONFIDENCE_BASIC_RE.test(text)) {
    if (scope.kind === 'procedureVariant' && sharesScenarioContext(text, context)) return 'OK_COMMON';
    return scope.kind === 'procedureVariant' ? 'REVIEW_NEEDED' : 'HIGH_CONFIDENCE_VIOLATION';
  }
  if (REVIEW_BASIC_RE.test(text) || text.length > 120 || /[□■◇▶▷※☞❍]|[0-9]-[0-9]?\)|ⅰ|ⅱ|ⅲ|ⅳ/.test(text)) return 'REVIEW_NEEDED';
  return 'OK_COMMON';
}

function sharesScenarioContext(label, context) {
  return ['이혼', '별거', '실종', '사망', '혼인단절', '자녀', '초청인', '피부양'].some(term => label.includes(term) && context.includes(term));
}

function scanScope(scope, groups) {
  const display = buildDisplayGroups(groups);
  const findings = [];
  if (!display.basic.length && !display.situational.length && !display.discretionary.length) {
    findings.push({ level: 'NO_DOCUMENTS', group: 'all', label: '', reason: 'No rendered document groups discovered' });
    return findings;
  }
  if (display.basic.length > 18) {
    findings.push({ level: 'REVIEW_NEEDED', group: 'basic', label: `${display.basic.length} items`, reason: 'Large basic/common group' });
  }
  const seen = new Map();
  ['basic', 'situational', 'discretionary'].forEach(group => {
    display[group].forEach(label => {
      const key = displayKey(label);
      if (!key) return;
      if (seen.has(key)) findings.push({ level: 'HIGH_CONFIDENCE_VIOLATION', group, label, reason: `Duplicate display family also in ${seen.get(key)}` });
      else seen.set(key, group);
    });
  });
  display.basic.forEach(label => {
    const level = classifyBasicLabel(label, scope);
    if (level !== 'OK_COMMON') {
      findings.push({ level, group: 'basic', label, reason: level === 'HIGH_CONFIDENCE_VIOLATION' ? 'Conditional/scenario wording in basic/common group' : 'Suspicious basic/common wording needs manual source review' });
    }
  });
  return findings;
}

function topRecords() {
  return (Array.isArray(visaData) ? visaData : Object.values(visaData).flatMap(v => Array.isArray(v) ? v : [v]))
    .filter(record => record && typeof record === 'object' && record.code);
}

const records = topRecords();
const scopes = [];
records.forEach(record => {
  PROCEDURE_CONFIG.forEach(cfg => {
    const raw = record.procedures && record.procedures[cfg.key] ? record.procedures[cfg.key] : null;
    const explicitUnavailable = raw && Object.prototype.hasOwnProperty.call(raw, 'available') && raw.available === false;
    const groups = getProcedureGroups(record, cfg);
    const variants = Array.isArray(raw?.variants) ? raw.variants.filter(v => v && v.available !== false) : [];
    if (!explicitUnavailable && (hasAnyDocs(groups) || raw?.available || variants.length || (cfg.oldText && record[cfg.oldText]))) {
      scopes.push({
        kind: 'procedure',
        code: record.code,
        title: record.nameKo || record.name || '',
        procedureKey: cfg.key,
        label: cfg.label,
        groups
      });
    }
    variants.forEach(variant => {
      scopes.push({
        kind: 'procedureVariant',
        code: record.code,
        title: record.nameKo || record.name || '',
        procedureKey: cfg.key,
        label: cfg.label,
        variantId: variant.id || '',
        variantLabel: variant.labelKo || variant.label || variant.scenarioKo || '',
        statusCode: variant.statusCode || '',
        groups: getVariantGroups(variant)
      });
    });
  });
});

const allFindings = [];
scopes.forEach(scope => {
  scanScope(scope, scope.groups).forEach(finding => allFindings.push({ ...finding, scope }));
});

const high = allFindings.filter(f => f.level === 'HIGH_CONFIDENCE_VIOLATION');
const review = allFindings.filter(f => f.level === 'REVIEW_NEEDED');
const noDocs = allFindings.filter(f => f.level === 'NO_DOCUMENTS');

console.log('Document taxonomy check');
console.log(`Records scanned: ${records.length}`);
console.log(`Document scopes scanned: ${scopes.length}`);
console.log(`HIGH_CONFIDENCE_VIOLATION: ${high.length}`);
console.log(`REVIEW_NEEDED: ${review.length}`);
console.log(`NO_DOCUMENTS: ${noDocs.length}`);
console.log('');

function scopeName(scope) {
  return [scope.code, scope.procedureKey, scope.variantId || scope.variantLabel || 'parent'].filter(Boolean).join(' / ');
}

if (high.length) {
  console.log('High-confidence violations');
  high.forEach(f => {
    console.log(`- ${scopeName(f.scope)} [${f.group}] ${f.label} :: ${f.reason}`);
  });
  console.log('');
}

if (review.length) {
  console.log('Review-needed findings');
  review.slice(0, 80).forEach(f => {
    console.log(`- ${scopeName(f.scope)} [${f.group}] ${f.label} :: ${f.reason}`);
  });
  if (review.length > 80) console.log(`- ... ${review.length - 80} more review-needed findings omitted`);
  console.log('');
}

if (noDocs.length) {
  console.log('Scopes with no rendered documents');
  noDocs.slice(0, 80).forEach(f => console.log(`- ${scopeName(f.scope)}`));
  if (noDocs.length > 80) console.log(`- ... ${noDocs.length - 80} more no-document scopes omitted`);
  console.log('');
}

if (!high.length) {
  console.log('PASS: no unresolved high-confidence rendered basic/common taxonomy violations.');
}

process.exitCode = high.length ? 1 : 0;
