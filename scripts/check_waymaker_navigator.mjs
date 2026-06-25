#!/usr/bin/env node
/**
 * check_waymaker_navigator.mjs — validation for the Waymaker procedure navigator
 * core (assets/js/waymaker-navigator.js).
 *
 * Offline, Node-only. Loads the module's REAL pure functions (UMD CommonJS export)
 * and exercises them against the real visa_data.json. Asserts the all-status safe
 * behavior the refactor promises:
 *  - every canonical status appears in the catalog and has >=1 safe procedure state;
 *  - the UI procedure adapter does NOT introduce a second taxonomy (it mirrors the
 *    backend PACKET_TYPE_BY_PROCEDURE_KEY exactly);
 *  - materially-ambiguous statuses (F-6) ask a sub-status clarification;
 *  - coverage-limited detection never treats an empty packet as complete;
 *  - the AI-follow-up context carries ONLY safe categorical identifiers (no
 *    checklist, no free text, no personal identifiers);
 *  - KO/EN navigator strings are at parity.
 *
 * Run: node scripts/check_waymaker_navigator.mjs
 */
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { createRequire } from 'node:module';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..');
const require = createRequire(import.meta.url);
const WM = require(join(ROOT, 'assets/js/waymaker-navigator.js'));
const records = JSON.parse(readFileSync(join(ROOT, 'visa_data.json'), 'utf8'));

let failures = 0, checks = 0;
function ok(cond, msg) {
  checks++;
  if (!cond) { failures++; console.error('  ✗ ' + msg); }
}
function section(name) { console.log('\n• ' + name); }

// ---------------------------------------------------------------------------
section('Status catalog covers all canonical statuses');
const catalog = WM.buildStatusCatalog(records);
ok(catalog.length === records.length, `catalog has ${records.length} entries (got ${catalog.length})`);
const byCode = Object.fromEntries(catalog.map((s) => [s.code, s]));
['D-2', 'F-4', 'F-6', 'E-7', 'F-5', 'G-1', 'A-1', 'H-2', 'B-1', 'YOUTH-STAY', 'REGION-S', 'K-STAR'].forEach((c) => {
  ok(byCode[c], `catalog contains ${c}`);
});
ok(byCode['K-STAR'] && byCode['K-STAR'].isProgram, 'K-STAR flagged as program');
ok(byCode['REGION-S'] && byCode['REGION-S'].isProgram, 'REGION-S flagged as program');
ok(byCode['D-2'] && !byCode['D-2'].isProgram, 'D-2 not flagged as program');

// ---------------------------------------------------------------------------
section('Adapter mirrors backend (no second taxonomy)');
const EXPECTED = {
  registration: 'foreigner_registration', extension: 'extension', statusChange: 'status_change',
  activitiesOutsideStatus: 'activities_outside_status', workplaceChange: 'workplace_change',
  reentry: 'reentry_permit', statusGrant: 'status_grant', visaIssuance: 'visa_issuance'
};
Object.keys(EXPECTED).forEach((k) => {
  ok(WM.PACKET_TYPE_BY_PROCEDURE_KEY[k] === EXPECTED[k], `procedure ${k} -> ${EXPECTED[k]}`);
  ok(WM.packetTypeForProcedureKey(k) === EXPECTED[k], `packetTypeForProcedureKey(${k})`);
});
ok(WM.packetTypeForProcedureKey('foreigner_registration') === 'foreigner_registration', 'public packet type passes through');
ok(WM.packetTypeForProcedureKey('totally_made_up') === null, 'unknown procedure -> null');
ok(Object.keys(WM.PACKET_TYPE_BY_PROCEDURE_KEY).length === Object.keys(EXPECTED).length, 'no extra procedure keys introduced');

// ---------------------------------------------------------------------------
section('Every canonical status has >=1 safe procedure state');
let zeroProc = [];
catalog.forEach((s) => {
  const procs = WM.proceduresForStatus(s);
  // A status with zero procedures would render a coverage-limited "no procedures"
  // state (still safe), but canonical data should never be empty.
  if (procs.length === 0 && !s.isProgram) zeroProc.push(s.code);
  procs.forEach((p) => ok(p.packetType, `${s.code}/${p.procedureKey} maps to a packet type`));
});
ok(zeroProc.length === 0, `no canonical status has zero procedures (offenders: ${zeroProc.join(',') || 'none'})`);

// ---------------------------------------------------------------------------
section('Materially-ambiguous statuses ask sub-status clarification');
ok(WM.needsSubStatusClarification(byCode['F-6'], 'statusChange') === true, 'F-6 statusChange asks clarification');
ok(WM.needsSubStatusClarification(byCode['F-6'], 'extension') === true, 'F-6 extension asks clarification');
ok(WM.needsSubStatusClarification(byCode['D-2'], 'extension') === true, 'D-2 extension asks clarification (8 subcodes)');
ok(WM.needsSubStatusClarification(byCode['A-1'], 'extension') === false, 'A-1 (no subcodes) does not ask clarification');
ok(WM.needsSubStatusClarification(byCode['E-1'], 'extension') === false, 'E-1 (no subcodes) does not ask clarification');

// ---------------------------------------------------------------------------
section('Coverage detection never treats empty packet as complete');
const fullPacket = { coverageSummary: { level: 'full', isLimited: false, hasDocuments: true }, documents: { commonDocs: [{ nameKo: 'x' }] }, sourceLens: { overallLevel: 'source_confirmed' } };
const limitedPacket = { coverageSummary: { level: 'unavailable', isLimited: true, hasDocuments: false }, documents: {}, sourceLens: { overallLevel: 'unavailable' } };
const derivedOnly = { documents: { requiredDocs: [] }, sourceLens: { overallLevel: 'limited' } }; // no coverageSummary
ok(WM.deriveCoverage(fullPacket).isLimited === false, 'full packet not limited');
ok(WM.deriveCoverage(limitedPacket).isLimited === true, 'unavailable packet is limited');
ok(WM.deriveCoverage(derivedOnly).isLimited === true, 'no-doc packet derived as limited even without coverageSummary');
ok(WM.deriveCoverage(null).isLimited === true, 'null packet is limited (safe default)');

// ---------------------------------------------------------------------------
section('Checklist grouping uses requiredness buckets, no fabrication');
const docPacket = {
  documents: {
    commonDocs: [{ nameKo: '여권', sourceBacked: true, sourceRefs: [{ evidenceLevel: 'source_confirmed' }] }],
    requiredDocs: [{ nameKo: '재정입증 서류', sourceBacked: true, sourceRefs: [{ evidenceLevel: 'source_confirmed' }] }],
    conditionalDocs: [{ nameKo: '수료증명서 (해당자)', sourceBacked: true, conditionKo: '해당자', sourceRefs: [] }],
    additionalDocs: []
  }
};
const items = WM.groupChecklistItems(docPacket);
ok(items.length === 3, `3 checklist items (got ${items.length})`);
ok(items.find((i) => i.group === 'common'), 'has common item');
ok(items.find((i) => i.group === 'conditional' && i.conditionKo === '해당자'), 'conditional item keeps conditionKo');
ok(WM.groupChecklistItems({ documents: {} }).length === 0, 'empty documents -> empty checklist (no fabrication)');

// ---------------------------------------------------------------------------
section('AI follow-up context carries only safe categorical identifiers');
const state = {
  locale: 'en', location: 'in_korea', statusCode: 'D-2', exactStatusCode: 'D-2-1',
  procedureKey: 'extension', subStatusKnown: true,
  // these must NOT leak:
  checklist: { x: true }, freeText: 'my passport number is 12345', name: 'Jane'
};
const aiCtx = WM.buildAiFollowupContext(state, fullPacket);
const allowed = new Set(['domain', 'locale', 'location', 'statusCode', 'exactStatusCode', 'subStatusKnown', 'procedureKey', 'packetType', 'packetId', 'coverageLevel', 'coverageLimited']);
ok(Object.keys(aiCtx).every((k) => allowed.has(k)), `context keys are all safe (got ${Object.keys(aiCtx).join(',')})`);
ok(aiCtx.statusCode === 'D-2' && aiCtx.exactStatusCode === 'D-2-1' && aiCtx.procedureKey === 'extension', 'context carries status+procedure');
ok(!('checklist' in aiCtx) && !('freeText' in aiCtx) && !('name' in aiCtx), 'context never carries checklist / free text / name');
ok(JSON.stringify(aiCtx).indexOf('passport') === -1 && JSON.stringify(aiCtx).indexOf('12345') === -1, 'no personal identifiers leak into context');

// ---------------------------------------------------------------------------
section('Source coverage labels (KO/EN) and class mapping');
ok(WM.sourceCoverageLabel('source_confirmed', 'ko') === '공식 원문 확인', 'KO confirmed label');
ok(WM.sourceCoverageLabel('source_confirmed', 'en') === 'Confirmed in official source', 'EN confirmed label');
ok(WM.sourceCoverageLabel('unavailable', 'en') === 'No current source coverage', 'EN none label');
ok(WM.sourceCoverageLabel('limited', 'ko') === '관할기관 확인 필요', 'KO verify label');
// no raw developer codes ever surface as a user label
['BASIS', 'SOURCE', 'DISABLED', 'needs_review', 'bad_response', 'limited', 'unavailable'].forEach((raw) => {
  ['ko', 'en'].forEach((loc) => {
    const label = WM.sourceCoverageLabel('source_confirmed', loc);
    ok(label.indexOf(raw) === -1, `confirmed label does not leak raw code ${raw}`);
  });
});

// ---------------------------------------------------------------------------
section('KO/EN navigator string parity');
const koKeys = Object.keys(WM.STRINGS.ko).sort();
const enKeys = Object.keys(WM.STRINGS.en).sort();
ok(koKeys.length === enKeys.length, `same number of KO (${koKeys.length}) and EN (${enKeys.length}) keys`);
koKeys.forEach((k) => ok(WM.STRINGS.en[k] != null && String(WM.STRINGS.en[k]).length > 0, `EN string exists for key '${k}'`));
enKeys.forEach((k) => ok(WM.STRINGS.ko[k] != null && String(WM.STRINGS.ko[k]).length > 0, `KO string exists for key '${k}'`));
// exact product copy spot-checks
ok(WM.STRINGS.ko.coverageLimited.indexOf('공식 근거가 충분히 구조화되어 있지 않습니다') !== -1, 'KO coverage-limited exact copy');
ok(WM.STRINGS.en.coverageLimited.indexOf('does not yet have enough structured official-source coverage') !== -1, 'EN coverage-limited exact copy');
ok(WM.STRINGS.ko.hikoreaCta === 'HiKorea 예약 경로 확인', 'KO HiKorea CTA exact copy');
ok(WM.STRINGS.en.hikoreaCta === 'Check my HiKorea booking path', 'EN HiKorea CTA exact copy');
ok(WM.STRINGS.ko.aiFollowupCta === '이 패킷에서 헷갈리는 점 묻기', 'KO AI follow-up CTA exact copy');
ok(WM.STRINGS.en.aiFollowupCta === 'Ask about this packet', 'EN AI follow-up CTA exact copy');

// ---------------------------------------------------------------------------
section('Procedure labels exist KO/EN for every adapter key');
Object.keys(WM.PACKET_TYPE_BY_PROCEDURE_KEY).forEach((k) => {
  ok(WM.procedureLabel(k, 'ko') && WM.procedureLabel(k, 'ko') !== k, `KO label for ${k}`);
  ok(WM.procedureLabel(k, 'en') && WM.procedureLabel(k, 'en') !== k, `EN label for ${k}`);
});

// ---------------------------------------------------------------------------
section('Analytics wrapper is categorical-only (no free text / prompts)');
let captured = [];
const track = WM.makeAnalytics((e, p) => captured.push([e, p]));
track('waymaker_status_selected', { locale: 'ko', statusFamily: 'D-2', freeText: 'leak', name: 'Jane', count: 5 });
track('not_an_allowed_event', { locale: 'ko' });
ok(captured.length === 1, 'only allowed events pass through');
ok(captured[0][1].statusFamily === 'D-2' && captured[0][1].locale === 'ko', 'categorical props kept');
ok(!('freeText' in captured[0][1]) && !('name' in captured[0][1]) && !('count' in captured[0][1]), 'free text / name / non-categorical stripped');

// ---------------------------------------------------------------------------
console.log('\n' + (failures === 0
  ? `✓ Waymaker navigator: all ${checks} checks passed.`
  : `✗ Waymaker navigator: ${failures}/${checks} checks FAILED.`));
process.exit(failures === 0 ? 0 : 1);
