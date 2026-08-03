#!/usr/bin/env node
/**
 * UI + behavior tests for the HiKorea employment-reporting helper in index.html.
 *
 * Part A — static structure & microcopy assertions on index.html / i18n.
 * Part B — loads the REAL helper functions from index.html into a vm sandbox
 *          (with a tiny DOM stub) and exercises search/scoring/guidance/memo.
 *
 * No browser or npm deps. Run: node scripts/check_employment_reporting_helper.mjs
 */
import fs from 'node:fs';
import path from 'node:path';
import vm from 'node:vm';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const repo = path.resolve(__dirname, '..');
const html = fs.readFileSync(path.join(repo, 'index.html'), 'utf8');
const data = JSON.parse(fs.readFileSync(path.join(repo, 'data', 'jobcode_master.json'), 'utf8'));
const ko = JSON.parse(fs.readFileSync(path.join(repo, 'data', 'i18n', 'ko.json'), 'utf8'));

const failures = [];
const ok = (cond, msg) => { if (!cond) failures.push(msg); };
const has = (needle, msg) => ok(html.includes(needle), msg || `missing in index.html: ${needle}`);

// ── Part A · static structure & microcopy ───────────────────────────────────
has('취업정보 신고용 직종·업종 찾기', 'header title microcopy missing');
has('HiKorea 신고 전에 내 일과 사업장 분야를 미리 정리', 'hero subtitle missing');
has('기준: KSCO8 · KSIC11', 'trust badge missing');
has('최종 신고 전 HiKorea에서 재확인', 'caution badge missing');
// UX-08 (442:99) "신고 대상 ≠ 취업 가능 — AMBER 경고 필수". A reporting code is
// not a work permission; conflating the two is the most consequential
// misreading this tool can produce, so the warning is asserted structurally and
// must be present for EVERY input, not only legally sensitive ones.
has('id="jcScopeWarn"', 'reportable-is-not-permitted warning element missing');
has('jobCodeScopeWarning', 'scope warning is not i18n-bound');
ok(!/id="jcScopeWarn"[^>]*\shidden/.test(html),
  'the scope warning must not be hidden by default');
ok(/class="jc2-scope-warn"/.test(html), 'scope warning missing its amber styling hook');
// UX-08 Emp / Special States (442:39): ten states, each with one next action.
has('id="jcSpecialStates"', 'special-states container missing');
has('renderEmploymentSpecialStates', 'special-states renderer not wired');
has('runEmploymentSpecialAction', 'special-state actions not wired');
{
  const ids = ['no_official_code', 'broad_indirect_match', 'freelancer', 'self_employed',
    'trainee', 'arts_entertainment', 'legally_sensitive', 'mixed_language',
    'low_confidence', 'source_unverifiable'];
  const i18nMap = html.slice(html.indexOf('const JC_SPECIAL_I18N'), html.indexOf('function renderEmploymentSpecialStates'));
  for (const id of ids) {
    ok(i18nMap.includes(id), `special state ${id} has no i18n mapping`);
  }
  // Every state needs Title/Body/Cta in both packs — a state without a next
  // action would break the design's one rule for this screen.
  const suffixes = ['NoOfficialCode', 'BroadMatch', 'Freelancer', 'SelfEmployed', 'Trainee',
    'Arts', 'Sensitive', 'MixedLang', 'LowConfidence', 'SourceUnverifiable'];
  for (const suf of suffixes) {
    for (const part of ['Title', 'Body', 'Cta']) {
      ok(typeof ko[`empSt${suf}${part}`] === 'string' && ko[`empSt${suf}${part}`].length > 0,
        `KO copy missing empSt${suf}${part}`);
    }
  }
  // 가치판단·합법성 단정 금지: the sensitive-occupation copy must hedge and point
  // at the office, never assert legality either way.
  const sens = ko.empStSensitiveBody || '';
  ok(/필요할 수 있|관할/.test(sens), 'sensitive-occupation copy does not hedge or point at the office');
  ok(!/합법|불법|가능합니다|할 수 있습니다$/.test(sens),
    'sensitive-occupation copy asserts legality');
}
const koScope = ko.jobCodeScopeWarning || '';
ok(koScope.includes('신고 대상') || koScope.includes('취업이 허용'),
  'KO scope warning does not actually distinguish reporting from permission');
ok(/1345|하이코리아|출입국/.test(koScope),
  'KO scope warning does not point at an official channel');
// guided checklist (dynamic; copy lives in scripts/employment_checklist.mjs) +
// plain-language pane labels before the official classification terms
has('id="jcChecklist"', 'guided checklist container missing');
has('내가 하는 일에 가까운 항목', 'occupation pane plain-language label missing');
has('회사나 사업장이 하는 일에 가까운 항목', 'industry pane plain-language label missing');
// guided-flow: candidate gate + Step-5 final HiKorea checklist
has('id="jcResultsGate"', 'candidate gate element missing');
has('id="jcFinalCheck"', 'final HiKorea checklist card missing');
has('하이코리아에서 마지막으로 확인할 것', 'final-check title missing');
has('연간소득 구간', 'income step copy missing');
// segmented filter
has('data-jc-filter="all"', 'filter: all missing');
has('data-jc-filter="occupation"', 'filter: occupation missing');
has('data-jc-filter="industry"', 'filter: industry missing');
['전체', '직종만', '업종만'].forEach(t => has(`>${t}<`, `filter label ${t} missing`));
// friendly natural-language example chips (field + service + professional +
// retail + logistics coverage), each runs the analyzer. Entertainment/tattoo
// (아이돌 연습생/타투이스트) are intentionally NOT featured as main-screen chips —
// they're legally-sensitive umbrella terms; the decomposition + caution logic
// is still fully covered by scripts/check_employment_code_analyzer.mjs fixtures.
['골프장 청소해요', '한치잡이 배에서 일해요', '학원에서 영어 가르쳐요', '카페에서 음료 만들어요', '편의점에서 계산해요', '택배 상하차 해요'].forEach(c =>
  has(`data-jc-chip="${c}"`, `example chip ${c} missing`));
// separate panes + badges
has('data-pane="occupation"', 'occupation pane missing');
has('data-pane="industry"', 'industry pane missing');
has('이건 직종입니다', 'occupation badge missing');
has('이건 업종입니다', 'industry badge missing');
// selected summary + copy
['jcSelOcc', 'jcSelInd', 'jcIncome', 'jcCopyBtn'].forEach(id => has(`id="${id}"`, `summary element #${id} missing`));
has('data-action="copy-jobcode-memo"', 'copy-memo action missing');
has('HiKorea 입력용 메모 복사', 'copy button label missing');
// required warnings (Phase 5 boundary + final-check copy)
has('취업정보 신고용 분류 참고', 'required reference-only warning missing');
has('자격외활동 허가 여부를 판단하지 않습니다', 'required boundary warning missing');
has('HiKorea 신고 화면 또는 1345', 'required final-confirmation warning missing');
// wiring: action handlers present
['set-jobcode-filter', 'search-jobcode-chip', 'select-jobcode', 'copy-jobcode-memo'].forEach(a =>
  has(`'${a}'`, `action handler '${a}' not wired`));
// risky label replaced: AI button must not say "공식 직종·업종"
ok(!ko.jobCodeNaturalSearchLocal.includes('공식'), 'jobCodeNaturalSearchLocal still uses risky "공식" wording');
// keyboard: interactive controls are native focusable elements
has('type="search" id="jcSearchInput"', 'search input must be a native <input type=search>');
ok(/<button type="button"[^>]*class="jc2-seg/.test(html), 'filter tabs must be native <button> (keyboard focusable)');
ok(/<button type="button" class="jc2-chip"/.test(html), 'chips must be native <button> (keyboard focusable)');
ok(/<button type="button" class="jc2-copy"/.test(html), 'copy must be native <button> (keyboard focusable)');
has('class="sr-only">직종 또는 업종 검색', 'screen-reader label for search input missing');
has('aria-label="검색 범위 선택"', 'screen-reader label for filter group missing');
has('aria-label="선택 요약"', 'screen-reader label for selected summary missing');
// mobile-first, no horizontal overflow: single-column by default, upgraded at breakpoint
ok(/\.jc2-results\s*\{[^}]*grid-template-columns:\s*1fr;/.test(html), 'results must be single-column (mobile-first)');
ok(/@media \(min-width: 820px\) \{ \.jc2-results \{ grid-template-columns: 1fr 1fr/.test(html), 'results must upgrade to 2 columns at desktop breakpoint');
ok(!/class="jc2-[a-z-]*"[^>]*style="[^"]*width:\s*\d{3,}px/.test(html), 'jc2 elements must not hardcode wide fixed pixel widths (overflow risk)');
ok(/\.jc2-search-input\s*\{[^}]*width:\s*100%/.test(html), 'search input must be fluid width (100%)');
// microcopy keys carry the right guidance
ok(/E-7/.test(ko.jobCodeBoundaryWarn), 'jobCodeBoundaryWarn must mention E-7');
ok(ko.jobCodeAmbiguity.includes('직종') && ko.jobCodeAmbiguity.includes('업종'), 'jobCodeAmbiguity must explain 직종 vs 업종');

// ── Part B · exercise the REAL helper functions ─────────────────────────────
const startMark = '// --- Job Code Modal · HiKorea';
const start = html.indexOf(startMark);
const endMark = '\nfunction fallbackCopy(';
const end = html.indexOf(endMark, start);
ok(start !== -1 && end !== -1, 'could not locate helper JS region in index.html');

if (start !== -1 && end !== -1) {
  const region = html.slice(start, end);
  const dom = (() => {
    const els = {};
    return {
      get: (id) => (els[id] ||= { id, hidden: true, innerHTML: '', textContent: '', value: '', classList: { add() {}, remove() {}, toggle() {} }, setAttribute() {}, querySelectorAll: () => [], focus() {} }),
      reset: () => { for (const k of Object.keys(els)) delete els[k]; },
      _els: els,
    };
  })();
  const sandbox = {
    document: { getElementById: (id) => dom.get(id), querySelector: () => null },
    window: { location: { protocol: 'https:' } },
    navigator: {},
    API_BASE: '',
    currentLanguage: 'ko',
    escapeHtml: (s) => String(s == null ? '' : s),
    hl: (s) => String(s == null ? '' : s),
    escapeRegExp: (s) => String(s).replace(/[.*+?^${}()|[\]\\]/g, '\\$&'),
    tx: (k) => (ko[k] !== undefined ? ko[k] : k),
    showToast: () => {},
    openModal: () => {}, closeModal: () => {}, fallbackCopy: () => {},
    setTimeout: (fn) => { try { fn(); } catch (_) {} return 0; },
    console,
  };
  sandbox.globalThis = sandbox;
  vm.createContext(sandbox);
  const exportTail = `
;globalThis.__JC = { normalizeJobcodeText, getJobcodeSearchTerms, scoreJobcodeRow,
  getScoredJobcodeRows, jobcodeEmptyHtml, buildJobcodeMemo, renderJobcodeGuidance,
  JC_AMBIGUOUS_TERMS, setData: (d)=>{_jobcodeData=d;}, setSelected:(s)=>{_jcSelected=s;} };`;
  try {
    vm.runInContext(region + exportTail, sandbox, { filename: 'jobcode-helper.js' });
  } catch (e) {
    failures.push(`helper region failed to evaluate: ${e.message}`);
  }
  const JC = sandbox.__JC;
  if (JC) {
    JC.setData(data);

    // 1) "개발자" → occupation results include 22; industry includes software (62)
    const devOcc = JC.getScoredJobcodeRows('occupation', '개발자', JC.getJobcodeSearchTerms('개발자'));
    const devInd = JC.getScoredJobcodeRows('industry', '개발자', JC.getJobcodeSearchTerms('개발자'));
    ok(devOcc.some(r => r.code === '22'), '"개발자" should surface occupation 22 (정보 통신 전문가 및 기술직)');
    ok(devInd.some(r => r.code === '62' || r.code === 'J' || r.code.startsWith('62')),
      '"개발자" should surface a software-related industry (62/J)');
    ok(devOcc.length > 0 && devInd.length > 0, '"개발자" should fill BOTH sections separately');

    // 2) "카페" → ambiguity guidance shown
    dom.reset();
    const cafeOcc = JC.getScoredJobcodeRows('occupation', '카페', JC.getJobcodeSearchTerms('카페'));
    const cafeInd = JC.getScoredJobcodeRows('industry', '카페', JC.getJobcodeSearchTerms('카페'));
    JC.renderJobcodeGuidance('카페', cafeOcc, cafeInd);
    ok(dom._els['jcAmbiguity'] && dom._els['jcAmbiguity'].hidden === false, '"카페" should show ambiguity guidance');
    ok(JC.JC_AMBIGUOUS_TERMS.has('카페'), '카페 should be a known ambiguous term');

    // 3) "E-7" → boundary warning shown
    dom.reset();
    JC.renderJobcodeGuidance('E-7', [], []);
    ok(dom._els['jcBoundaryWarn'] && dom._els['jcBoundaryWarn'].hidden === false, '"E-7" should show boundary warning');

    // 4) empty query → top-level browse (majors only)
    const browse = JC.getScoredJobcodeRows('occupation', '', []);
    ok(browse.length === 10 && browse.every(r => r.level === 'major'),
      `empty query should browse 10 occupation majors (got ${browse.length})`);

    // 5) empty/no-match state offers recovery suggestions, not a dead end
    const emptyHtml = JC.jobcodeEmptyHtml('occupation');
    ok(/직무명으로 검색/.test(emptyHtml) && /더 짧은 단어로 검색/.test(emptyHtml),
      'empty state should offer recovery suggestions');

    // 6) memo includes BOTH selected codes + final HiKorea confirmation warning
    dom.reset();
    JC.setSelected({ occupation: { code: '22', name: '정보 통신 전문가 및 기술직' }, industry: { code: '62', name: '컴퓨터 프로그래밍, 시스템 통합 및 관리업' } });
    dom.get('jcIncome').value = '연간 1천만 원 미만';
    const memo = JC.buildJobcodeMemo();
    ok(memo.includes('22') && memo.includes('정보 통신 전문가'), 'memo missing selected occupation');
    ok(memo.includes('62') && memo.includes('컴퓨터 프로그래밍'), 'memo missing selected industry');
    ok(memo.includes('연간 1천만 원 미만'), 'memo missing income band');
    ok(memo.includes('최종 신고 전 HiKorea 화면에서 재확인'), 'memo missing final HiKorea confirmation warning');
  }
}

if (failures.length) {
  console.error('[check_employment_reporting_helper] FAIL');
  failures.forEach(m => console.error('  - ' + m));
  process.exit(1);
}
console.log('[check_employment_reporting_helper] OK — static structure, microcopy, search behavior, ambiguity, boundary, empty state, and memo all verified');
