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
const backendOrigin = fs.readFileSync(path.join(root, 'assets/js/backend-origin.js'), 'utf8');
const vercelExtract = fs.readFileSync(path.join(root, 'api/enforcement/extract.js'), 'utf8');
const vercelAnalyze = fs.readFileSync(path.join(root, 'api/enforcement/analyze.js'), 'utf8');
const vercelConfirm = fs.readFileSync(path.join(root, 'api/enforcement/confirm.js'), 'utf8');
const lawProbe = fs.readFileSync(path.join(root, 'api/enforcement/law-probe.js'), 'utf8');
const fallbackRuntime = fs.readFileSync(path.join(root, 'lib/enforcement-fallback.js'), 'utf8');
const groundedRuntime = fs.readFileSync(path.join(root, 'lib/enforcement-grounded-ai.js'), 'utf8');
const lawRuntime = fs.readFileSync(path.join(root, 'lib/enforcement-law-grounding.js'), 'utf8');
const precedentRuntime = fs.readFileSync(path.join(root, 'lib/enforcement-precedent-grounding.js'), 'utf8');
const credentialRuntime = fs.readFileSync(path.join(root, 'lib/law-credential.js'), 'utf8');
const legalRules = JSON.parse(fs.readFileSync(path.join(root, 'backend/data/enforcement/legal_rules.json'), 'utf8'));
const { extractStructuredCaseV2, publicRuntimeConfig } = require('../lib/enforcement-grounded-ai.js');
const { resolveLawCredential } = require('../lib/law-credential.js');

const backendResolverIndex = html.indexOf('assets/js/backend-origin.js');
const enforcementModuleIndex = html.indexOf('scripts/enforcement-ui.mjs');

const checks = [
  ['three-step flow', /data-step="1"[\s\S]*data-step="2"[\s\S]*data-step="3"/.test(html)],
  ['fact-only confirmation copy', html.includes('입력한 사실이 맞는지만 확인해 주세요.') && html.includes('맞아요 · 분석하기') && html.includes('법률 판단이 아니라 사실 확인 단계입니다.')],
  ['confirmation replaces bureaucratic edit grid', !html.includes('name="violationCode"') && !html.includes('name="durationDays"') && html.includes('id="confirmed-facts"')],
  ['single-question clarification UI', html.includes('id="clarification-card"') && js.includes('function clarificationFor(') && html.includes('한 가지만 더 확인할게요')],
  ['critical clarification can be skipped honestly', js.includes('잘 모르겠어요') && js.includes('skippedClarifications')],
  ['confirmation always precedes analysis', !js.includes('caseNeedsConfirmation') && js.includes('showStep(2);') && js.includes('renderConfirmation(structuredCase)')],
  ['confirmation copy is immediate and deterministic', js.includes('function deterministicSummary(') && !js.includes('/api/enforcement/confirm')],
  ['Gemma receives structured facts, not raw narrative', vercelConfirm.includes('payload.caseData') && !vercelConfirm.includes('payload.text') && vercelConfirm.includes('SAFE_FIELDS')],
  ['Gemma is copy-only and cannot drive legal output', vercelConfirm.includes('copy-only-no-legal-judgment') && vercelConfirm.includes('Never perform legal analysis') && vercelConfirm.includes('summaryIsSafe')],
  ['Gemma 4 preferred for confirmation copy', vercelConfirm.includes('google/gemma-4-31b-it:free')],
  ['legal baseline card', html.includes('법령상 기준') && js.includes('법령 기준')],
  ['prediction card naming', js.includes('<h3>처분 전망</h3>') && js.includes('예상 범칙금 범위') && !js.includes('<h3>Visable AI 예상</h3>')],
  ['degraded prediction is explained without a DOM observer', js.includes('AI 추정 보류') && js.includes('법령 기준 산출에 필요한 사실 부족') && js.includes('일시적으로 분석을 불러오지 못했습니다') && !js.includes('MutationObserver')],
  ['determination card never exposes internal review jargon', !js.includes('사람의 검토') && !js.includes('사람 검토') && !js.includes('humanReviewReason')],
  ['failure copy never exposes internal ops state', !js.includes('운영자가') && !js.includes('API 키') && !js.includes('인증 설정을 확인해야 합니다') && !js.includes('서버의 AI 제공자') && js.includes('법령 기준 결과는 그대로 확인할 수 있습니다')],
  ['internal process terms stay out of user copy', !js.includes('정적 법령 스냅샷 사용') && !js.includes('AI의 응답이 법적 근거 또는 데이터 형식 검증') && !js.includes('AI 응답이 근거·형식 검증을 통과하지 못해') && !fallbackRuntime.includes('검증된 법령 스냅샷') && !groundedRuntime.includes('저장된 법령 스냅샷') && !lawRuntime.includes('정적 검증 스냅샷') && !lawRuntime.includes('버전 고정 스냅샷')],
  ['confidence reasons never confess internal verification state', !groundedRuntime.includes('VERIFIED 상태가 아닙니다') && !groundedRuntime.includes('실시간 법령 API 검증이 완전한') && !groundedRuntime.includes('서버에서 검증') && !groundedRuntime.includes('서버에서 제한') && groundedRuntime.includes('법령 기준 금액과 예상 범위를 나눠서 보여드립니다') && groundedRuntime.includes('법령 기준은 공식 법령 자료를 바탕으로 정했습니다')],
  ['basis tags use plain user language, never inference-speak', js.includes("SUPPORTED: '확인된 사실'") && js.includes("INFERRED: '입력 내용에서 파악'") && js.includes("UNKNOWN: '아직 확인 안 됨'") && !js.includes("'추론'")],
  ['duration note credits the period the user entered', fallbackRuntime.includes('입력한 기간(') && fallbackRuntime.includes('으로 계산했습니다') && !fallbackRuntime.includes('1개월로 환산')],
  ['30-day month-boundary warning is reliable', js.includes('durationDays === 30') && js.includes('30일은 월 단위 경계에 걸릴 수 있습니다') && !js.includes('hasExactDates')],
  ['result UX styles ship in the primary stylesheet', !html.includes('assets/css/enforcement-result-ux.css') && css.includes('.prediction-degraded-note') && css.includes('.baseline-boundary-note')],
  ['result UX runs in the primary module', !html.includes('scripts/enforcement-result-ux.js') && js.includes('function resultNotice(')],
  ['analysis shows an immediate inline progress state', js.includes('function renderAnalysisLoading(') && js.indexOf('showStep(3);') < js.indexOf("request('/api/enforcement/analyze'")],
  ['step changes focus the active work area', js.includes("activeSection.scrollIntoView({ block: 'start', behavior: 'auto' })") && js.includes("activeSection.querySelector('h2')?.focus")],
  ['disposition section', js.includes('행정처분 전망')],
  ['empty disposition explains why and shows the legal range, not a blank', js.includes('function emptyDispositionHtml(') && js.includes('legallyAvailableDispositions') && js.includes('가능성 순위가 아니라')],
  ['unusable model answers get one retry on another model', groundedRuntime.includes('RETRY_REJECTED') && groundedRuntime.includes('exclude: tried') && groundedRuntime.includes('function unwrapPredictionPayload(')],
  ['result opens with a plain-language verdict built from validated values only', js.includes('function verdictSentence(') && js.includes('class="verdict-card"')],
  ['stay impact from the validated prediction is rendered', js.includes('prediction.stayImpact') && js.includes('stay-impact')],
  ['money rationale and direction are rendered', js.includes('monetary?.rationale') && js.includes('directionLabels')],
  ['outcome-relevant facts can be answered in step 2 and on the result', html.includes('id="accuracy-card"') && js.includes('function accuracyBoostCard(') && js.includes('analyzeCase(applyAccuracyAnswer(')],
  ['unknown facts stay unknown unless the user answers', js.includes("caseData?.[item.key] === null || caseData?.[item.key] === undefined") && !js.includes('priorViolations = 0;')],
  ['prompt carries the exact output shape and the unknown-is-not-no rule', groundedRuntime.includes('Return exactly this shape') && groundedRuntime.includes('Never describe an unknown fact as absent or negative')],
  ['blocked baseline offers an exact-date next step instead of a dead end', js.includes('function nextStepCard(') && js.includes('id="date-range-form"') && js.includes('violationStartDate: start, violationEndDate: end')],
  ['unverified rule periods stop honestly without a guessed amount', js.includes("baseline.status === 'HISTORICAL_RULE_UNAVAILABLE'") && js.includes('검증된 법령 기준이 없어 금액을 계산하지 않았어요')],
  ['no AI wait when the legal baseline is missing', js.includes("baselineResponse.legalBaseline.status !== 'AVAILABLE'")],
  ['evidence basis codes are shown in Korean', js.includes("SUPPORTED: '확인된 사실'") && !js.includes('${escapeHtml(item.basis)}</span>')],
  ['operator limitations are translated, not dropped', js.includes('function plainLimitation(') && js.includes('limitations.map(plainLimitation)')],
  ['status clarification has one-tap choices', js.includes('quickPicks') && css.includes('.clarification-chip')],
  ['showcase example is not a calendar-month boundary case', !html.includes('음식점에서 한 달 동안')],
  ['confidence section', js.includes('예측 신뢰도')],
  ['similar cases section shown only when cases exist', js.includes('similar.length ? `<details>')],
  ['workplace cases ask plain-language facts, not the legal regime first', js.includes("kind: 'workplaceChangeType'") && js.includes("kind: 'previousEmploymentEndReason'") && js.includes("kind: 'procedureStatus'") && js.includes('근무처가 어떻게 바뀐 건가요?') && !js.includes('사전허가 대상인지 사후신고 대상인지 확인하셨나요?')],
  ['authority-confirmed regime remains only as a last-resort question', js.includes("kind: 'workplaceRegime'") && js.includes('이미 관할 출입국관서에서') && js.includes("workplaceRegimeSource = 'USER_CONFIRMED'")],
  ['selecting the workplace-change code never auto-sets unauthorized facts', !js.includes("if (value === 'UNAUTHORIZED_WORKPLACE_CHANGE_ART21_1') {\n      structuredCase.workplaceChangeAuthorized = false;") && js.includes('does not prove the change was unpermitted or unreported')],
  ['determination result is explainable', js.includes('function determinationCard(') && js.includes('판별에 쓰인 사실') && js.includes('아직 확인할 사항')],
  ['administrative-fine track is rendered separately from the fine table', js.includes("baseline.status === 'ADMINISTRATIVE_FINE_TRACK'") && js.includes('법정 상한일 뿐이며')],
  ['not-applicable determination stops calculation honestly', js.includes("baseline.status === 'NOT_APPLICABLE'")],
  ['user copy hides law API error codes', js.includes('function plainLimitation') && js.includes('실시간 법령 원문 대조가 완료되지 않았습니다.') && !js.includes('grounding.credentialSource ?')],
  ['why panel', js.includes('<summary>예상 근거</summary>') && js.includes('예상 근거')],
  ['official source links', js.includes('공식 출처') && js.includes('sourceUrl')],
  ['privacy copy', html.includes('원문 서술은 저장하지 않습니다')],
  ['raw narrative discarded from textarea after extraction', js.includes("$('#case-text').value = ''")],
  ['extract endpoint wired', js.includes('/api/enforcement/extract')],
  ['analyze endpoint wired', js.includes('/api/enforcement/analyze')],
  ['enforcement uses the deployed same-origin API', html.includes('<meta name="api-base" content=".">') && js.includes('const configured =')],
  ['Vercel extract v2 exists', vercelExtract.includes('extractStructuredCaseV2') && vercelExtract.includes('legal-aware-extraction-v2')],
  ['Vercel grounded analyzer exists', vercelAnalyze.includes('analyzeGroundedCase') && vercelAnalyze.includes('grounded-ai-v2')],
  ['runtime reads OpenRouter only server-side', groundedRuntime.includes('process.env.OPENROUTER_API_KEY') && !html.includes('OPENROUTER_API_KEY')],
  ['runtime rejects numeric probabilities', groundedRuntime.includes('numeric_probability_prohibited')],
  ['runtime bounds monetary prediction', groundedRuntime.includes('sanitizeMoneyRange') && groundedRuntime.includes('legallyAdjustableRange')],
  ['runtime forbids random OpenRouter routing', groundedRuntime.includes('RANDOM_MODEL_IDS')],
  ['Groq is tried first and goes through the same validation', groundedRuntime.includes('async function callPredictionProviders(') && groundedRuntime.includes('await callPredictionProviders(messages,') && groundedRuntime.includes("process.env.GROQ_API_KEY")],
  ['Groq probe is GET-only and never echoes the key', fs.readFileSync(new URL('../api/enforcement/groq-probe.js', import.meta.url), 'utf8').includes("request.method !== 'GET'") && fs.readFileSync(new URL('../api/enforcement/groq-probe.js', import.meta.url), 'utf8').includes("split(key).join('[redacted]')")],
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
  ['Article 18(1) label remains legally corrected', groundedRuntime.includes('취업활동이 허용되는 체류자격 없이 취업')],
  ['Article 18(2) label remains legally corrected', groundedRuntime.includes('취업활동 자격 보유자가 지정된 근무처가 아닌 곳에서 근무')],
  ['shared backend resolver loaded', backendResolverIndex >= 0],
  ['shared backend resolver loads before enforcement module', backendResolverIndex >= 0 && backendResolverIndex < enforcementModuleIndex],
  ['shared backend resolver remains available as operator override infrastructure', js.includes('window.VisableBackend') && js.includes('window.VisableBackend.origin')],
  ['production does not silently fall back to same-origin without explicit config', js.includes("return local ? '' : null")],
  ['network failure has explicit user message', js.includes('Visable 분석 서버에 연결하지 못했습니다.')],
  ['HTTP failure preserves status', js.includes('분석 서버 요청에 실패했습니다. (${response.status})')],
  ['mobile breakpoint', css.includes('@media (max-width: 680px)')],
  ['mobile one-column results', /@media \(max-width: 680px\)[\s\S]*\.fact-grid, \.result-grid \{ grid-template-columns: 1fr; \}/.test(css)],
  ['mobile confirmation input stacks', /@media \(max-width: 680px\)[\s\S]*\.clarification-input-row \{ grid-template-columns: 1fr; \}/.test(css)],
  ['mobile confirmation actions stack', /@media \(max-width: 640px\)[\s\S]*\.confirmation-actions[\s\S]*grid-template-columns: 1fr/.test(css)],
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

const runtime = publicRuntimeConfig();
assert.equal(Object.hasOwn(runtime, 'openrouterConfigured'), true);
assert.equal(Object.hasOwn(runtime, 'lawApiConfigured'), true);
assert.equal(Object.hasOwn(runtime, 'lawApiCredentialSource'), true);
assert.ok(Array.isArray(runtime.supportedCredentialEnvNames));
assert.equal(Object.hasOwn(runtime, 'key'), false);
assert.equal(Object.hasOwn(runtime, 'credential'), false);

console.log(`Enforcement UI/runtime contract passed (${checks.length} static checks + legal extraction/credential assertions).`);
