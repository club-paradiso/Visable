#!/usr/bin/env node

const fs = require('fs');
const path = require('path');

const ROOT = path.resolve(__dirname, '..', '..');
const visaDataPath = path.join(ROOT, 'visa_data.json');
const docMasterPath = path.join(ROOT, 'doc_master.json');
const records = JSON.parse(fs.readFileSync(visaDataPath, 'utf8'));
const docMaster = JSON.parse(fs.readFileSync(docMasterPath, 'utf8'));
const DOC_DICT = Object.fromEntries(docMaster.map(doc => [doc.id, doc.ko_name || doc.name || doc.id]).filter(([id]) => id));

const DOC_PLACEHOLDER_TOKENS = new Set([
  '매뉴얼 확인 필요', '페이지 확인 필요', 'Manual review needed', 'Page review needed',
  '문서명 미상', '비고 정보 없음', 'DATA_MISSING', 'Document name unknown', 'No note available'
]);

const DOC_FIELD_KEYS = new Set([
  'commonDocs', 'common_documents', 'common',
  'requiredDocs', 'required_documents', 'required_documents_ko', 'reqDocs', 'documents', 'document', 'docs', 'required',
  'additionalDocs', 'additional_documents', 'addReqDocs', 'addReq', 'additional',
  'conditionalDocs', 'conditional_documents', 'conditional',
  'initialReqDocs', 'newReqDocs', 'cviReqDocs', 'changeReqDocs', 'chgReqDocs', 'extensionReqDocs', 'extReqDocs',
  'statusGrantReqDocs', 'registrationReqDocs', 'activitiesOutsideStatusReqDocs', 'workplaceChangeReqDocs', 'reentryReqDocs',
  'documents_initial', 'documents_registration', 'documents_extension'
]);

const NESTED_DOC_GROUP_KEYS = new Set([
  'commonDocs', 'common_documents', 'common',
  'requiredDocs', 'required_documents', 'reqDocs', 'documents', 'document', 'docs', 'required',
  'additionalDocs', 'additional_documents', 'addReqDocs', 'addReq', 'additional',
  'conditionalDocs', 'conditional_documents', 'conditional'
]);

function isDocPlaceholder(value) {
  return DOC_PLACEHOLDER_TOKENS.has(String(value || '').trim());
}

function normalizeText(value) {
  return String(value == null ? '' : value).normalize('NFKC').replace(/\u00a0/g, ' ').replace(/\s+/g, ' ').trim();
}

function getDocumentRequirementLabel(doc) {
  if (doc && typeof doc === 'object' && !Array.isArray(doc)) {
    const label = normalizeText(doc.name || doc.label || doc.title || doc.textKo || doc.text || doc.description || '');
    return DOC_DICT[label] || label;
  }
  const label = normalizeText(doc);
  return DOC_DICT[label] || label;
}

function paradisoDocFamilyProbe(label) {
  let probe = normalizeText(label);
  if (!probe) return '';
  probe = probe.replace(/^\s*[①-⑳0-9]+[.)]?\s*/g, '');
  probe = probe.replace(/[(（][^()（）]*[)）]/g, '').replace(/[(（][^()（）]*[)）]/g, '');
  return probe
    .replace(/\s+/g, '')
    .replace(/[ㆍ·•]/g, '')
    .replace(/별지제?\d+호서식?/g, '')
    .replace(/원본및사본1부|원본및사본/g, '')
    .replace(/원본|사본/g, '')
    .replace(/각?1부|1매|1통/g, '')
    .replace(/[()（）［\]\[\]{}.,:：]/g, '')
    .trim();
}

const FAMILY_RULES = [
  { family: '신청서', re: /^(통합신청서|신청서)/ },
  { family: '여권', re: /^여권/ },
  { family: '수수료', re: /^(수수료|정부수입인지|수입인지|인지대|인지)/ },
  { family: '외국인등록증', re: /^(외국인등록증|등록증|거소증)/ },
  { family: '체류지입증서류', re: /^(체류지입증서류|임대차계약서|숙소제공확인서|거주숙소제공확인서|공공요금납부영수증|공과금|기숙사비영수증|기숙사거주확인)/ },
  { family: '재정입증서류', re: /^(재정입증서류|재정능력입증서류|잔고증명서?|은행잔고증명서?|소득증명서?|통장)/ },
  { family: '학업수행입증서류', re: /^(학업정상수행입증서류|학업을정상적으로수행하고있음을입증하는서류|재학증명서|성적증명서|출석확인서)/ },
  { family: '수료증명서·지도교수확인서', re: /^(수료증명서|지도교수|유학담당자)/ },
  { family: '표준규격사진', re: /^(표준규격사진|여권용사진|반명함판(천연색)?사진|증명사진|사진)/ },
  { family: '사업자등록증', re: /^(교육기관)?(사업자등록증|고유번호증)(또는교육기관고유번호증|또는고유번호증)?$/ },
  { family: '가족관계입증서류', re: /^가족관계(입증서류|증명서)/ },
  { family: '혼인관계증명서', re: /^혼인관계증명서/ },
  { family: '기본증명서', re: /^기본증명서/ },
  { family: '결핵진단서', re: /^(결핵건강진단서|결핵진단서)/ }
];

function normalizeDocumentRequirementKey(label) {
  const resolved = getDocumentRequirementLabel(label);
  if (!resolved || isDocPlaceholder(resolved)) return '';
  const probe = paradisoDocFamilyProbe(resolved);
  if (!probe) return '';
  if (/(수수료|정부수입인지|수입인지|인지대|인지)/.test(probe)) return '수수료';
  if (/졸업증명서/.test(probe) && !/(학업정상|학업을정상적|출석|성적)/.test(probe)) return probe;
  const rule = FAMILY_RULES.find(item => item.re.test(probe));
  return rule ? rule.family : probe;
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

function copyDocumentRequirementForDisplay(doc) {
  if (doc && typeof doc === 'object' && !Array.isArray(doc)) return { ...doc };
  if (Array.isArray(doc)) return doc.slice();
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

function mergeDocumentRequirementForDisplay(existingDoc, nextDoc) {
  const existingLabel = getDocumentRequirementLabel(existingDoc);
  const nextLabel = getDocumentRequirementLabel(nextDoc);
  const chooseNext = scoreDocumentRequirementSpecificity(nextLabel) > scoreDocumentRequirementSpecificity(existingLabel);
  return setDocumentRequirementLabel(copyDocumentRequirementForDisplay(chooseNext ? nextDoc : existingDoc), chooseNext ? nextLabel : existingLabel);
}

function dedupeDocumentSectionsForDisplay(sections) {
  const seen = new Map();
  const output = [];
  for (const section of sections || []) {
    const docs = Array.isArray(section.docs) ? section.docs : [];
    const outSection = { ...section, docs: [] };
    for (const doc of docs) {
      const key = getDocumentRequirementDisplayKey(doc);
      if (!key) continue;
      const prior = seen.get(key);
      if (!prior) {
        seen.set(key, { section: outSection, index: outSection.docs.length });
        outSection.docs.push(copyDocumentRequirementForDisplay(doc));
      } else {
        prior.section.docs[prior.index] = mergeDocumentRequirementForDisplay(prior.section.docs[prior.index], doc);
      }
    }
    if (outSection.docs.length) output.push(outSection);
  }
  return output;
}

function toDocArray(value) {
  if (!value) return [];
  if (Array.isArray(value)) return value.flatMap(toDocArray);
  if (typeof value === 'string') {
    return value.split(/\n|;|·/)
      .map(item => item.trim())
      .filter(item => item && !isDocPlaceholder(item));
  }
  if (typeof value === 'object') {
    const label = getDocumentRequirementLabel(value);
    return label && !isDocPlaceholder(label) ? [value] : [];
  }
  const text = String(value).trim();
  return text && !isDocPlaceholder(text) ? [text] : [];
}

function hasNestedDocGroups(value) {
  return !!(value && typeof value === 'object' && !Array.isArray(value)
    && Object.keys(value).some(key => NESTED_DOC_GROUP_KEYS.has(key)));
}

function sectionsFromField(key, value, basePath) {
  if (!DOC_FIELD_KEYS.has(key)) return [];
  if (hasNestedDocGroups(value)) {
    return Object.entries(value)
      .filter(([childKey]) => NESTED_DOC_GROUP_KEYS.has(childKey))
      .flatMap(([childKey, childValue]) => sectionsFromField(childKey, childValue, `${basePath}.${key}`));
  }
  const docs = toDocArray(value);
  return docs.length ? [{ key, path: `${basePath}.${key}`, docs }] : [];
}

function discoverScopes(value, basePath, scopes) {
  if (!value || typeof value !== 'object') return;
  if (Array.isArray(value)) {
    value.forEach((item, index) => discoverScopes(item, `${basePath}[${index}]`, scopes));
    return;
  }
  const sections = Object.entries(value).flatMap(([key, child]) => sectionsFromField(key, child, basePath));
  if (sections.length) scopes.push({ path: basePath, sections });
  Object.entries(value).forEach(([key, child]) => {
    if (DOC_FIELD_KEYS.has(key) && !hasNestedDocGroups(child)) return;
    discoverScopes(child, `${basePath}.${key}`, scopes);
  });
}

function duplicateFamilies(sections) {
  const seen = new Map();
  for (const section of sections || []) {
    for (const doc of section.docs || []) {
      const key = getDocumentRequirementDisplayKey(doc);
      if (!key) continue;
      if (!seen.has(key)) seen.set(key, []);
      seen.get(key).push({ section: section.key, path: section.path, label: getDocumentRequirementLabel(doc) });
    }
  }
  return [...seen.entries()]
    .filter(([, items]) => items.length > 1)
    .map(([family, items]) => ({ family, items }));
}

function formatRecord(record, index) {
  const code = record && record.code ? record.code : `record-${index + 1}`;
  const name = record && (record.nameKo || record.name || record.nameEn || record.title || '');
  return name ? `${code} ${name}` : code;
}

const allScopes = [];
const noDocumentRecords = [];
records.forEach((record, index) => {
  const recordLabel = formatRecord(record, index);
  const scopes = [];
  discoverScopes(record, recordLabel, scopes);
  if (!scopes.length) noDocumentRecords.push(recordLabel);
  scopes.forEach(scope => allScopes.push({ recordLabel, ...scope }));
});

const resolvedDuplicates = [];
const unresolvedDuplicates = [];

for (const scope of allScopes) {
  const before = duplicateFamilies(scope.sections);
  const afterSections = dedupeDocumentSectionsForDisplay(scope.sections);
  const after = duplicateFamilies(afterSections);
  if (before.length) resolvedDuplicates.push({ ...scope, before, afterSections });
  if (after.length) unresolvedDuplicates.push({ ...scope, after });
}

const d2Scopes = allScopes.filter(scope => /^D-2(?:\s|$)/.test(scope.recordLabel));
const d2Resolved = resolvedDuplicates.filter(scope => /^D-2(?:\s|$)/.test(scope.recordLabel));
const d2AfterRows = d2Scopes
  .flatMap(scope => dedupeDocumentSectionsForDisplay(scope.sections).map(section => ({
    scope: scope.path,
    section: section.key,
    labels: section.docs.map(getDocumentRequirementLabel)
  })))
  .filter(row => row.labels.length);

console.log('# Rendered document duplicate check');
console.log(`visa_data records: ${records.length}`);
console.log(`document scopes discovered: ${allScopes.length}`);
console.log(`records with no document arrays: ${noDocumentRecords.length}`);
noDocumentRecords.forEach(record => console.log(`- NO_DOC_ARRAY: ${record}`));
console.log('');
console.log(`resolved duplicate display families before render dedupe: ${resolvedDuplicates.length}`);
resolvedDuplicates.slice(0, 80).forEach(scope => {
  console.log(`- RESOLVED: ${scope.path}`);
  scope.before.forEach(dup => {
    const labels = dup.items.map(item => `${item.section}:${item.label}`).join(' | ');
    console.log(`  ${dup.family}: ${labels}`);
  });
});
if (resolvedDuplicates.length > 80) console.log(`- ... ${resolvedDuplicates.length - 80} more resolved scopes omitted`);
console.log('');
console.log('D-2 proof case:');
if (!d2Scopes.length) {
  console.log('- D-2 record not found');
} else if (!d2Resolved.length) {
  console.log('- D-2 has no duplicate display families after current discovery');
} else {
  d2Resolved.forEach(scope => {
    console.log(`- D-2 resolved scope: ${scope.path}`);
    scope.before.forEach(dup => console.log(`  ${dup.family}: ${dup.items.map(item => item.label).join(' | ')}`));
  });
}
d2AfterRows.slice(0, 12).forEach(row => console.log(`  AFTER ${row.scope} ${row.section}: ${row.labels.join(' | ')}`));
console.log('');
console.log(`unresolved duplicate display families after render dedupe: ${unresolvedDuplicates.length}`);
unresolvedDuplicates.forEach(scope => {
  console.log(`- UNRESOLVED: ${scope.path}`);
  scope.after.forEach(dup => {
    const labels = dup.items.map(item => `${item.section}:${item.label}`).join(' | ');
    console.log(`  ${dup.family}: ${labels}`);
  });
});

if (unresolvedDuplicates.length) {
  process.exitCode = 1;
}
