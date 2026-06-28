#!/usr/bin/env node
/*
 * Conservative validation for the visa issuance enrichment POC.
 * This script intentionally validates only the new layer plus the static UI
 * hooks that render it; it does not promote weak evidence to confirmed status.
 */
'use strict';

const fs = require('fs');
const path = require('path');

const ROOT = path.resolve(__dirname, '..');
const PRIORITY_CODES = [
  'D-2', 'D-4', 'D-10', 'E-7', 'E-8', 'E-9',
  'F-1', 'F-2', 'F-4', 'F-6', 'G-1', 'H-2',
  'C-3', 'B-1', 'B-2'
];
const ALLOWED_OVERLAY_DOMAINS = new Set([
  'visa.go.kr',
  'hikorea.go.kr',
  'immigration.go.kr',
  'mofa.go.kr',
  'overseas.mofa.go.kr',
  'law.go.kr'
]);
const BAD_PLACEHOLDERS = ['\uFFFD', 'TBD', 'DATA_MISSING', '문서명 미상', '비고 정보 없음'];
const VALID_EVIDENCE_LEVELS = new Set([
  'source_confirmed',
  'contextual',
  'limited',
  'unavailable',
  'not_applicable'
]);
const VALID_REVIEW_STATUSES = new Set([
  'complete',
  'needs_manual_extraction',
  'needs_source_review',
  'needs_official_web_overlay',
  'should_remain_limited',
  'not_applicable'
]);
const REQUIRED_MISSION_COUNTRIES = [
  'United States', 'China', 'Japan', 'Vietnam', 'Philippines',
  'Thailand', 'Mongolia', 'Uzbekistan', 'Canada', 'Australia'
];

const failures = [];
const warnings = [];
const passed = [];

function readJson(relPath) {
  const abs = path.join(ROOT, relPath);
  try {
    return JSON.parse(fs.readFileSync(abs, 'utf8'));
  } catch (err) {
    failures.push(`${relPath}: invalid JSON (${err.message})`);
    return null;
  }
}

function readText(relPath) {
  return fs.readFileSync(path.join(ROOT, relPath), 'utf8');
}

function check(name, cond, detail) {
  if (cond) passed.push(name);
  else failures.push(detail ? `${name}: ${detail}` : name);
}

function warn(name, cond, detail) {
  if (!cond) warnings.push(detail ? `${name}: ${detail}` : name);
}

function collectStrings(value, out = []) {
  if (value == null) return out;
  if (typeof value === 'string') out.push(value);
  else if (Array.isArray(value)) value.forEach(item => collectStrings(item, out));
  else if (typeof value === 'object') Object.values(value).forEach(item => collectStrings(item, out));
  return out;
}

function hasDuplicate(values) {
  const seen = new Set();
  for (const value of values) {
    if (seen.has(value)) return true;
    seen.add(value);
  }
  return false;
}

function sourceHasPageOrUrl(source) {
  if (!source || typeof source !== 'object') return false;
  if (source.sourceUrl || source.url) return true;
  return Number.isInteger(source.pageStart) && Number.isInteger(source.pageEnd);
}

const visaData = readJson('visa_data.json') || [];
const issuance = readJson('data/visa_issuance_records.json') || {};
const evidence = readJson('data/procedure_evidence_bindings.json') || {};
const overlays = readJson('data/official_web_overlays.json') || {};
const indexHtml = readText('index.html');

const canonicalCodes = visaData
  .filter(v => v && !['faq', 'scn', 'nhis'].includes(v.cat))
  .map(v => v.code)
  .filter(Boolean);

const issuanceRecords = Array.isArray(issuance.records) ? issuance.records : [];
const evidenceRecords = Array.isArray(evidence.records) ? evidence.records : [];
const overlayRecords = Array.isArray(overlays.records) ? overlays.records : [];
const issuanceByCode = new Map(issuanceRecords.map(record => [record.code, record]));
const visaIssuanceBindings = evidenceRecords.filter(record => record.procedureType === 'visa_issuance');
const bindingByCode = new Map(visaIssuanceBindings.map(record => [record.code, record]));

check('valid issuance records array', Array.isArray(issuance.records));
check('valid evidence bindings array', Array.isArray(evidence.records));
check('valid overlay records array', Array.isArray(overlays.records));
check('no duplicate issuance record codes', !hasDuplicate(issuanceRecords.map(record => record.code)));
check('no duplicate visa_issuance evidence binding codes', !hasDuplicate(visaIssuanceBindings.map(record => record.code)));
check('priority code coverage count', PRIORITY_CODES.every(code => issuanceByCode.has(code)), 'missing priority issuance record');

for (const relPath of [
  'data/visa_issuance_records.json',
  'data/procedure_evidence_bindings.json',
  'data/official_web_overlays.json'
]) {
  const text = readText(relPath);
  check(`${relPath} contains no U+FFFD`, !text.includes('\uFFFD'));
  for (const token of BAD_PLACEHOLDERS.filter(token => token !== '\uFFFD')) {
    check(`${relPath} contains no ${token}`, !text.includes(token));
  }
}

for (const code of canonicalCodes) {
  const binding = bindingByCode.get(code);
  const hasGuidance = issuanceByCode.has(code);
  const hasReviewState = binding && VALID_REVIEW_STATUSES.has(binding.reviewStatus);
  const isNotApplicable = binding && binding.evidenceLevel === 'not_applicable';
  check(
    `canonical status ${code} has issuance guidance/not_applicable/review state`,
    hasGuidance || isNotApplicable || hasReviewState
  );
}

for (const record of issuanceRecords) {
  const code = record.code || '(missing code)';
  check(`${code} has manual source`, !!(record.manualSource && record.manualSource.manual && record.manualSource.sectionTitle));
  check(`${code} has at least one issuance mode`, Array.isArray(record.issuanceModes) && record.issuanceModes.length > 0);
  for (const mode of record.issuanceModes || []) {
    const modeName = mode.labelKo || mode.type || `${code} mode`;
    check(`${code} ${modeName} has user label`, !!(mode.labelKo && mode.labelEn));
    check(`${code} ${modeName} has steps`, Array.isArray(mode.steps) && mode.steps.length > 0);
    check(`${code} ${modeName} has source refs`, Array.isArray(mode.sourceRefs) && mode.sourceRefs.some(sourceHasPageOrUrl));
  }
}

for (const record of visaIssuanceBindings) {
  const label = `${record.code} ${record.procedureType}`;
  check(`${label} has valid evidence level`, VALID_EVIDENCE_LEVELS.has(record.evidenceLevel));
  check(`${label} has valid review status`, VALID_REVIEW_STATUSES.has(record.reviewStatus));
  if (record.evidenceLevel === 'source_confirmed') {
    check(
      `${label} source_confirmed has page refs or URL`,
      Array.isArray(record.manualSources) && record.manualSources.some(sourceHasPageOrUrl)
    );
  }
  if (record.evidenceLevel === 'limited' || record.evidenceLevel === 'unavailable') {
    check(`${label} has user-facing limitation explanation`, !!String(record.userFacingExplanationKo || '').trim());
  }
  if (record.evidenceLevel === 'not_applicable') {
    check(`${label} explains not applicable state`, !!String(record.userFacingExplanationKo || '').trim());
  }
}

for (const record of overlayRecords) {
  const label = record.id || record.country || '(overlay)';
  const url = String(record.sourceUrl || '');
  let domain = '';
  try { domain = new URL(url).hostname.replace(/^www\./, ''); } catch (e) { domain = ''; }
  check(`${label} has a stable id`, !!record.id);
  check(`${label} is a Tier 3 mission source`, record.sourceTier === 3 && record.sourceClass === 'consular_mission_notice');
  check(`${label} has complete source identity`, !!(record.country && record.post && record.sourceTitle && record.sourceUrl));
  check(`${label} has access metadata`, /^\d{4}-\d{2}-\d{2}$/.test(String(record.accessedAt || '')));
  check(`${label} has status coverage`, Array.isArray(record.coveredCodes) && record.coveredCodes.length > 0);
  check(`${label} overlay uses allowed domain`, ALLOWED_OVERLAY_DOMAINS.has(domain), url);
  check(`${label} remains mission-specific`, record.globalRuleEligible === false && record.reflection !== 'global_rule');
  check(`${label} overlay does not conflict silently`, record.conflictsWithManual !== true || !!record.conflictNoteKo);
}

for (const source of Array.isArray(overlays.centralHandoffs) ? overlays.centralHandoffs : []) {
  let domain = '';
  try { domain = new URL(source.url).hostname.replace(/^www\./, ''); } catch (e) { domain = ''; }
  check(`${source.id || '(central handoff)'} has Tier 2 metadata`, source.sourceTier === 2 && !!source.sourceClass);
  check(`${source.id || '(central handoff)'} uses an official domain`, ALLOWED_OVERLAY_DOMAINS.has(domain), source.url);
  check(`${source.id || '(central handoff)'} has access date and scope`, !!(source.accessedAt && source.scopeKo && source.scopeEn));
}

const overlayDomains = Array.isArray(overlays.allowedDomains) ? overlays.allowedDomains : [];
check('overlay allowed domains are restricted to official list',
  overlayDomains.every(domain => ALLOWED_OVERLAY_DOMAINS.has(domain)));
check('overlay seed manifest includes all 10 required jurisdictions',
  Array.isArray(overlays.seedManifest)
    && REQUIRED_MISSION_COUNTRIES.every(country => overlays.seedManifest.some(item => item.country === country && item.status === 'inspected')));
check('overlay records include all 10 required jurisdictions',
  REQUIRED_MISSION_COUNTRIES.every(country => overlayRecords.some(item => item.country === country)));
check('overlay policy prohibits manual override and requires central authority for global promotion',
  overlays.policy?.manualRecordOverrideAllowed === false && overlays.policy?.globalPromotionRequiresCentralAuthority === true);
check('overlay policy includes the required consular caution',
  String(overlays.policy?.consularCautionKo || '').includes('재외공관별 추가서류와 접수 방식은 공관마다 다를 수 있으므로'));

check('UI renders visa issuance section', indexHtml.includes('function renderVisaIssuanceSection') && indexHtml.includes('visa-issuance-section'));
check('UI renders actionable mission-specific source links',
  indexHtml.includes('issuance-mission-sources') && indexHtml.includes('record.sourceUrl') && !indexHtml.includes('<select>${options}</select>'));
check('UI renders source limitation explanation', indexHtml.includes('function renderSourceLimitationExplanation'));
check('UI avoids stale exact-rank 6/5 filters',
  !indexHtml.includes('v._exactRank === 6') && !indexHtml.includes('v._exactRank === 5'));
check('UI uses numeric exact-code thresholds',
  indexHtml.includes('v._exactRank >= 10000') && indexHtml.includes('v._exactRank >= 5000'));

// --- Unified issuance procedure UI + F-4 exclusion (2026-06 UI unification) ---
const koI18n = readJson('data/i18n/ko.json') || {};
check('F-4 stays out of the generic issuance renderer (exclusion set present)',
  /GENERIC_VISA_ISSUANCE_EXCLUDED_CODES\s*=\s*new Set\(\[\s*'F-4'/.test(indexHtml));
check('renderVisaIssuanceSection guards excluded codes before rendering',
  /function renderVisaIssuanceSection[\s\S]*?isGenericVisaIssuanceExcluded\(\s*v\.code\s*\)/.test(indexHtml));
check('F-4 keeps its dedicated diaspora route guide wiring',
  indexHtml.includes('assets/js/f4-route-guide.js') && indexHtml.includes('id="f4RouteGuide"'));
check('F-4 issuance record still present (excluded by code, not by data deletion)',
  issuanceByCode.has('F-4'));
check('UI derives standardized application-route chips',
  indexHtml.includes('function deriveIssuanceRouteChips') && indexHtml.includes('issuance-route-chip'));
check('issuance route chip labels exist as a 6-item i18n pack',
  Array.isArray(koI18n.issuanceRouteChipLabels) && koI18n.issuanceRouteChipLabels.length === 6);
check('issuance stage label routed through i18n',
  indexHtml.includes("tx('issuanceStageLabel')") && !!koI18n.issuanceStageLabel);

// Static safety check for user-visible enum leakage in the new renderer.
const newUiRenderer = (indexHtml.match(/function renderVisaIssuanceSection[\s\S]*?function renderCautionBlock/) || [''])[0];
for (const enumName of ['source_confirmed', 'not_applicable', 'visa_issuance_confirmation', 'consular_discretion']) {
  warn('new UI renderer does not visibly print internal enum names',
    !newUiRenderer.includes(`>${enumName}<`) && !newUiRenderer.includes('`' + enumName + '`'),
    enumName);
}

const sourceCounts = visaIssuanceBindings.reduce((acc, record) => {
  acc[record.evidenceLevel] = (acc[record.evidenceLevel] || 0) + 1;
  return acc;
}, {});
const priorityCounts = PRIORITY_CODES.reduce((acc, code) => {
  const level = bindingByCode.get(code)?.evidenceLevel || 'missing';
  acc[level] = (acc[level] || 0) + 1;
  return acc;
}, {});

console.log('Visa issuance enrichment validation');
console.log(`Canonical status codes: ${canonicalCodes.length}`);
console.log(`Priority issuance records: ${issuanceRecords.filter(r => PRIORITY_CODES.includes(r.code)).length}/${PRIORITY_CODES.length}`);
console.log(`Evidence levels: ${JSON.stringify(sourceCounts)}`);
console.log(`Priority evidence levels: ${JSON.stringify(priorityCounts)}`);
console.log('');
for (const item of passed) console.log(`PASS ${item}`);
for (const item of warnings) console.log(`WARN ${item}`);
for (const item of failures) console.log(`FAIL ${item}`);
console.log('');
console.log(`${passed.length} passed, ${warnings.length} warnings, ${failures.length} failed`);

process.exit(failures.length ? 1 : 0);
