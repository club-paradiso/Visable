#!/usr/bin/env node

import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const readJson = rel => JSON.parse(fs.readFileSync(path.join(ROOT, rel), 'utf8'));
const readText = rel => fs.readFileSync(path.join(ROOT, rel), 'utf8');

const nationalitySources = readJson('data/nationality_sources.json');
const nationalityContent = readJson('data/nationality_content.json');
const nationalityPaths = readJson('data/nationality_paths.json');
const overlays = readJson('data/official_web_overlays.json');
const newHomeHtml = readText('new-home.html');
const indexHtml = readText('index.html');

const failures = [];
const passes = [];
const check = (label, condition, detail = '') => {
  if (condition) passes.push(label);
  else failures.push(`${label}${detail ? `: ${detail}` : ''}`);
};

const OFFICIAL_HOSTS = new Set([
  'immigration.go.kr', 'mojminwon.moj.go.kr', 'hikorea.go.kr',
  'socinet.go.kr', 'kiiptest.org', 'moj.go.kr', 'law.go.kr',
  'gwanbo.go.kr', 'easylaw.go.kr', 'overseas.mofa.go.kr',
  'visa.go.kr'
]);
const hostOf = raw => {
  try { return new URL(raw).hostname.replace(/^www\./, ''); }
  catch { return ''; }
};
const collectSourceIds = (value, out = []) => {
  if (!value || typeof value !== 'object') return out;
  if (Array.isArray(value)) {
    value.forEach(item => collectSourceIds(item, out));
    return out;
  }
  if (Array.isArray(value.sourceIds)) out.push(...value.sourceIds);
  Object.values(value).forEach(item => collectSourceIds(item, out));
  return out;
};

const sources = Array.isArray(nationalitySources.sources) ? nationalitySources.sources : [];
const sourceIds = sources.map(source => source.sourceId);
const sourceIdSet = new Set(sourceIds);
check('nationality source registry has unique IDs', sourceIds.length === sourceIdSet.size);
check('nationality source registry has an explicit hierarchy', String(nationalitySources._meta?.sourceHierarchy || '').includes('Tier 1'));

for (const source of sources) {
  const label = source.sourceId || '(missing sourceId)';
  check(`${label} has identity metadata`, !!(source.sourceId && source.title && source.titleEn && source.publisher));
  check(`${label} has tier/type/class metadata`, [1, 2, 3, 4].includes(source.sourceTier) && !!source.sourceType && !!source.sourceClass);
  check(`${label} has scope metadata`, !!(source.scopeKo && source.scopeEn && source.jurisdictionKo && source.jurisdictionEn));
  check(`${label} has review metadata`, !!(source.accessedAt && source.verificationStatus && source.reflection));
  check(`${label} uses an approved official host`, OFFICIAL_HOSTS.has(hostOf(source.url)), source.url);
}

const references = [...collectSourceIds(nationalityContent), ...collectSourceIds(nationalityPaths)];
for (const sourceId of new Set(references)) {
  check(`source reference resolves: ${sourceId}`, sourceIdSet.has(sourceId));
}

for (const requiredPath of ['general', 'marriage', 'family', 'special', 'restoration', 'determination', 'dual', 'loss', 'renunciation', 'after']) {
  check(`nationality path exists: ${requiredPath}`, nationalityPaths.paths.some(pathItem => pathItem.id === requiredPath));
}

const futureAmendment = sources.find(source => source.sourceId === 'law-nationality-act-2026-amendment');
check('future Nationality Act amendment is a correction signal only', futureAmendment?.reflection === 'correction_signal_only');
check('future Nationality Act amendment keeps its future effective date', futureAmendment?.effectiveDate === '2026-12-03');
check('future amendment is not silently presented as current law', String(futureAmendment?.notes || '').includes('must not be treated as the current rule before'));

const missionRecords = Array.isArray(overlays.records) ? overlays.records : [];
const requiredCountries = ['United States', 'China', 'Japan', 'Vietnam', 'Philippines', 'Thailand', 'Mongolia', 'Uzbekistan', 'Canada', 'Australia'];
for (const country of requiredCountries) {
  check(`mission source recorded: ${country}`, missionRecords.some(record => record.country === country));
}
for (const record of missionRecords) {
  const label = record.id || record.country || '(mission source)';
  check(`${label} cannot become a global rule`, record.globalRuleEligible === false && record.sourceTier === 3);
  check(`${label} has scope and access metadata`, !!(record.localOnlySummaryKo && record.localOnlySummaryEn && record.accessedAt));
  check(`${label} has a mission URL`, hostOf(record.sourceUrl) === 'overseas.mofa.go.kr');
  check(`${label} has explicit reflection handling`, ['country_or_mission_specific_note', 'official_handoff_link'].includes(record.reflection));
}
check('manual override is prohibited by overlay policy', overlays.policy?.manualRecordOverrideAllowed === false);
check('global promotion requires central authority', overlays.policy?.globalPromotionRequiresCentralAuthority === true);

for (const riskyPhrase of ['귀화 가능성 진단', '2분 귀화 진단']) {
  check(`New Home avoids eligibility-engine phrase: ${riskyPhrase}`, !readText('data/nationality_content.json').includes(riskyPhrase));
}
check('New Home renders source scope', newHomeHtml.includes('nh-source-scope') && newHomeHtml.includes('sourceScopeLabel'));
check('New Home renders source dates/access dates', newHomeHtml.includes('sourceAccessedLabel') && newHomeHtml.includes('sourceEffectiveLabel'));
check('New Home carries a non-affiliation disclaimer', String(nationalityContent.sourcesPanel?.disclaimer?.ko || '').includes('제휴 또는 소속 관계가 없습니다'));
check('New Home marks future-effective sources', newHomeHtml.includes('futureEffectiveBadge') && newHomeHtml.includes('correction_signal_only'));
check('New Home no longer uses a verified checkmark badge', !newHomeHtml.includes('.nh-official-badge::before'));

check('Visa UI matches overlays by covered status codes', indexHtml.includes('record.coveredCodes.some'));
check('Visa UI renders mission links instead of an inert selector', indexHtml.includes('issuance-mission-link') && !indexHtml.includes('<select>${options}</select>'));
check('Visa UI includes the required consular caution', indexHtml.includes('재외공관별 추가서류와 접수 방식은 공관마다 다를 수 있으므로'));
check('Homepage links to Visa Portal', indexHtml.includes('href="https://www.visa.go.kr/"'));
check('Homepage links to the official 1345 page', indexHtml.includes('href="https://www.immigration.go.kr/moj/196/subview.do"'));

console.log(`Official external-source validation: ${passes.length} checks passed`);
if (failures.length) {
  console.error(`Official external-source validation failed (${failures.length}):`);
  failures.forEach(failure => console.error(`- ${failure}`));
  process.exit(1);
}
