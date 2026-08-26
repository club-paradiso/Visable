import fs from 'node:fs';
import path from 'node:path';
import assert from 'node:assert/strict';
import { createRequire } from 'node:module';

const root = path.resolve(import.meta.dirname, '..');
const require = createRequire(import.meta.url);
const html = fs.readFileSync(path.join(root, 'enforcement.html'), 'utf8');
const css = fs.readFileSync(path.join(root, 'assets/css/enforcement.css'), 'utf8');
const js = fs.readFileSync(path.join(root, 'scripts/enforcement-ui.mjs'), 'utf8');
const index = fs.readFileSync(path.join(root, 'index.html'), 'utf8');
const vercelExtract = fs.readFileSync(path.join(root, 'api/enforcement/extract.js'), 'utf8');
const vercelAnalyze = fs.readFileSync(path.join(root, 'api/enforcement/analyze.js'), 'utf8');
const lawProbe = fs.readFileSync(path.join(root, 'api/enforcement/law-probe.js'), 'utf8');
const fallbackRuntime = fs.readFileSync(path.join(root, 'lib/enforcement-fallback.js'), 'utf8');
const groundedRuntime = fs.readFileSync(path.join(root, 'lib/enforcement-grounded-ai.js'), 'utf8');
const outcomeRuntime = fs.readFileSync(path.join(root, 'lib/enforcement-outcome-policy.js'), 'utf8');
const lawRuntime = fs.readFileSync(path.join(root, 'lib/enforcement-law-grounding.js'), 'utf8');
const precedentRuntime = fs.readFileSync(path.join(root, 'lib/enforcement-precedent-grounding.js'), 'utf8');
const credentialRuntime = fs.readFileSync(path.join(root, 'lib/law-credential.js'), 'utf8');
const legalRules = JSON.parse(fs.readFileSync(path.join(root, 'backend/data/enforcement/legal_rules.json'), 'utf8'));
const { extractStructuredCaseV2, publicRuntimeConfig } = require('../lib/enforcement-grounded-ai.js');
const { applyOutcomePolicy } = require('../lib/enforcement-outcome-policy.js');
const { resolveLawCredential } = require('../lib/law-credential.js');

const backendResolverIndex = html.indexOf('assets/js/backend-origin.js');
const enforcementModuleIndex = html.indexOf('scripts/enforcement-ui.mjs');

const checks = [
  ['three-step flow', /data-step="1"[\s\S]*data-step="2"[\s\S]*data-step="3"/.test(html)],
  ['fact confirmation copy', html.includes('입력 내용을 이렇게 이해했어요.')],
  ['legal baseline card', html.includes('법령상 기준') && js.includes('법령 기준')],
  ['AI prediction card', js.includes('Visable AI 예상') && js.includes('예상 범칙금')],
  ['disposition section', js.includes('예상 행정처분')],
  ['confidence section', js.includes('예측 신뢰도')],
  ['similar cases section', js.includes('유사사례')],
  ['why panel', js.includes('WHY THIS PREDICTION?') && js.includes('예상 근거')],
  ['official source links', js.includes('OFFICIAL SOURCES') && js.includes('sourceUrl')],
  ['privacy copy', html.includes('원문 서술은 저장하지 않습니다')],
  ['raw narrative discarded', js.includes("$('#case-text').value = ''")],
  ['extract endpoint wired', js.includes('/api/enforcement/extract')],
  ['analyze endpoint wired', js.includes('/api/enforcement/analyze')],
  ['same-origin API base selected for enforcement', html.includes('<meta name="api-base" content=".">')],
  ['Vercel extract v2 exists', vercelExtract.includes('extractStructuredCaseV2') && vercelExtract.includes('legal-aware-extraction-v2')],
  ['Vercel grounded analyzer exists', vercelAnalyze.includes('analyzeGroundedCase') && vercelAnalyze.includes('grounded-ai-v2')],
  ['balanced outcome policy is applied after grounded analysis', vercelAnalyze.includes('applyOutcomePolicy') && vercelAnalyze.includes('OUTCOME_POLICY_VERSION')],
  ['outcome policy preserves no-immediate-departure option', outcomeRuntime.includes('NO_IMMEDIATE_DEPARTURE_MEASURE')],
  ['outcome policy recognizes departure recommendation', outcomeRuntime.includes('DEPARTURE_RECOMMENDATION')],
  ['unsupported high-impact departure prediction is demoted', outcomeRuntime.includes('HIGH_IMPACT_DEPARTURE_TYPES') && outcomeRuntime.includes('prediction.primaryDisposition = null')],
  ['F-5 deportation is fail-closed', outcomeRuntime.includes('제46조제2항') && outcomeRuntime.includes("type !== 'DEPORTATION'")],
  ['UI names neutral and recommendation outcomes', js.includes("NO_IMMEDIATE_DEPARTURE_MEASURE: '즉시 출국조치 없음'") && js.includes("DEPARTURE_RECOMMENDATION: '출국권고'")],
  ['UI labels the Article 86(2) range accurately', js.includes('통상 가감 범위(시행규칙 제86조제2항)')],
  ['runtime reads OpenRouter only server-side', groundedRuntime.includes('process.env.OPENROUTER_API_KEY') && !html.includes('OPENROUTER_API_KEY')],
  ['runtime rejects numeric probabilities', groundedRuntime.includes('numeric_probability_prohibited')],
  ['runtime bounds monetary prediction', groundedRuntime.includes('sanitizeMoneyRange') && groundedRuntime.includes('legallyAdjustableRange')],
  ['runtime forbids random OpenRouter routing', groundedRuntime.includes('RANDOM_MODEL_IDS')],
  ['runtime factor ids remain deterministic', groundedRuntime.includes('deterministicFactorCode') && !groundedRuntime.includes('Math.random')],
  ['precedent bodies are retrieved before prediction', groundedRuntime.includes('retrieveOfficialPrecedents') && groundedRuntime.includes('similarCases') && groundedRuntime.indexOf('retrieveOfficialPrecedents') < groundedRuntime.lastIndexOf('predictionPrompt(')],
  ['precedent runtime uses official list and body endpoints', precedentRuntime.includes("target: 'prec'") && precedentRuntime.includes('/DRF/lawSearch.do') && precedentRuntime.includes('/DRF/lawService.do')],
  ['precedent runtime exposes only body results as direct evidence', precedentRuntime.includes("resultKind: 'BODY_RESULT'") && precedentRuntime.includes("citationGrade: 'DIRECT'")],
  ['law credential helper supports canonical and MCP aliases', ['LAW_API_OC', 'LAW_OC', 'OPEN_LAW_ID', 'LAW_API_KEY'].every((name) => credentialRuntime.includes(`'${name}'`))],
  ['law runtime uses shared secret-safe credential resolver', lawRuntime.includes('resolveLawCredential') && lawRuntime.includes('publicLawCredentialConfig')],
  ['law runtime calls official DRF endpoints', lawRuntime.includes('/DRF/lawSearch.do') && lawRuntime.includes('/DRF/lawService.do')],
  ['law runtime requests appendix 7 explicitly when needed', lawRuntime.includes("BD: 'ON'") && lawRuntime.includes("BT: '1'") && lawRuntime.includes("BN: '7'")],
  ['law runtime never returns credential value', !lawRuntime.includes('credential: cfg.credential')],
  ['safe live law probe exists', lawProbe.includes("service: 'visable-enforcement-law-probe'") && lawProbe.includes("target: 'law'") && lawProbe.includes('exactLawFound')],
  ['safe live law probe never returns credential value', !lawProbe.includes('credential: credential') && !lawProbe.includes('credentialValue')],
  ['fallback runtime uses canonical rule snapshot', fallbackRuntime.includes("require('../backend/data/enforcement/legal_rules.json')")],
  ['fallback remains fail-closed without provider', fallbackRuntime.includes("status: 'UNAVAILABLE'")],
  ['fallback preserves no-precedent limitation', fallbackRuntime.includes('현재 확인 가능한 유사 공개사례가 충분하지 않습니다.')],
  ['Article 18(1) label is legally corrected', html.includes('취업활동 가능 체류자격 없이 취업')],
  ['Article 18(2) label is legally corrected', html.includes('지정된 근무처가 아닌 곳에서 근무')],
  ['shared backend resolver loaded', backendResolverIndex >= 0],
  ['shared backend resolver loads before enforcement module', backendResolverIndex >= 0 && backendResolverIndex < enforcementModuleIndex],
  ['shared backend resolver remains available as operator override infrastructure', js.includes('window.VisableBackend') && js.includes('window.VisableBackend.origin')],
  ['production does not silently fall back to same-origin without explicit config', js.includes("return local ? '' : null")],
  ['network failure has explicit user message', js.includes('Visable 분석 서버에 연결하지 못했습니다.')],
  ['HTTP failure preserves status', js.includes('분석 서버 요청에 실패했습니다. (${response.status})')],
  ['mobile breakpoint', css.includes('@media (max-width: 680px)')],
  ['mobile one-column results', /@media \(max-width: 680px\)[\s\S]*\.fact-grid, \.result-grid \{ grid-template-columns: 1fr; \}/.test(css)],
  ['reduced motion support', css.includes('prefers-reduced-motion')],
  ['homepage gateway', index.includes('enforcement.html')],
];

for (const [name, ok] of checks) assert.equal(ok, true, `enforcement UI contract failed: ${name}`);

const snapshot = legalRules.snapshots[0];
assert.equal(snapshot.verifiedAt, '2026-08-26');
assert.equal(snapshot.rules.find((rule) => rule.violationCode === 'UNAUTHORIZED_STAY_OR_WORK_ART18_1').label,
  '취업활동이 허용되는 체류자격 없이 취업');
assert.equal(snapshot.rules.find((rule) => rule.violationCode === 'UNAUTHORIZED_EMPLOYMENT_ART18_2').label,
  '취업활동 자격 보유자가 지정된 근무처가 아닌 곳에서 근무');

const d2 = extractStructuredCaseV2('D-2 유학생인데 음식점에서 허가 없이 18일 아르바이트했습니다. 처음입니다.', '2026-08-26');
assert.equal(d2.violationCode, 'STATUS_OUTSIDE_ACTIVITY_ART20');
assert.equal(d2.durationDays, 18);

const c3 = extractStructuredCaseV2('C-3 체류자격인데 음식점에서 허가 없이 12일 일했습니다.', '2026-08-26');
assert.equal(c3.violationCode, 'UNAUTHORIZED_STAY_OR_WORK_ART18_1');

const e7 = extractStructuredCaseV2('E-7인데 지정된 근무처가 아닌 다른 사업장에서 허가 없이 20일 근무했습니다.', '2026-08-26');
assert.equal(e7.violationCode, 'UNAUTHORIZED_EMPLOYMENT_ART18_2');

const ambiguous = extractStructuredCaseV2('F-2인데 다른 곳에서 허가 없이 10일 일했습니다.', '2026-08-26');
assert.equal(ambiguous.violationCode, null);
assert.ok(ambiguous.violationCandidates.length >= 2);

assert.deepEqual(resolveLawCredential({ LAW_OC: 'alias-value' }), { credential: 'alias-value', credentialSource: 'LAW_OC' });
assert.deepEqual(resolveLawCredential({ OPEN_LAW_ID: 'mcp-value' }), { credential: 'mcp-value', credentialSource: 'OPEN_LAW_ID' });
assert.equal(resolveLawCredential({ LAW_API_OC: 'canonical', LAW_OC: 'alias' }).credential, 'canonical');

const noDirectCase = applyOutcomePolicy({
  case: { statusOfStay: 'D-2' },
  legalBaseline: { status: 'AVAILABLE', legallyAvailableDispositions: ['DEPARTURE_ORDER', 'DEPORTATION'] },
  prediction: {
    evidence: [{ id: 'law:1', resultKind: 'LEGAL_RULE', citationGrade: 'DIRECT' }],
    primaryDisposition: {
      type: 'DEPORTATION', likelihood: 'HIGH', rank: 1,
      confidence: { level: 'HIGH', reasons: [] }, rationale: [], supportingEvidence: [],
    },
    alternativeDispositions: [], limitations: [],
  },
});
assert.equal(noDirectCase.prediction.primaryDisposition, null);
assert.ok(noDirectCase.prediction.alternativeDispositions.some((item) => item.type === 'NO_IMMEDIATE_DEPARTURE_MEASURE'));
assert.ok(noDirectCase.legalBaseline.legallyAvailableDispositions.includes('DEPARTURE_RECOMMENDATION'));
assert.equal(noDirectCase.outcomePolicy.departureOrderIsAutomatic, false);

const f5 = applyOutcomePolicy({
  case: { statusOfStay: 'F-5' },
  legalBaseline: { status: 'AVAILABLE', legallyAvailableDispositions: ['DEPORTATION', 'DEPARTURE_ORDER'] },
  prediction: { evidence: [], primaryDisposition: null, alternativeDispositions: [{ type: 'DEPORTATION', likelihood: 'UNKNOWN', rank: 1, confidence: { level: 'LOW', reasons: [] }, rationale: [], supportingEvidence: [] }], limitations: [] },
});
assert.ok(!f5.legalBaseline.legallyAvailableDispositions.includes('DEPORTATION'));
assert.ok(!f5.prediction.alternativeDispositions.some((item) => item.type === 'DEPORTATION'));

const runtime = publicRuntimeConfig();
assert.equal(Object.hasOwn(runtime, 'openrouterConfigured'), true);
assert.equal(Object.hasOwn(runtime, 'lawApiConfigured'), true);
assert.equal(Object.hasOwn(runtime, 'lawApiCredentialSource'), true);
assert.ok(Array.isArray(runtime.supportedCredentialEnvNames));
assert.equal(Object.hasOwn(runtime, 'key'), false);
assert.equal(Object.hasOwn(runtime, 'credential'), false);

console.log(`Enforcement UI/runtime contract passed (${checks.length} static checks + legal extraction/credential/outcome assertions).`);
