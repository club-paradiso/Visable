#!/usr/bin/env node
/**
 * UI + behavior tests for the HiKorea employment-reporting helper (markup in index.html,
 * logic in src/features/jobcode.js since Phase 3 of the frontend rebuild).
 *
 * Part A — static structure & microcopy assertions on index.html / the module / i18n.
 * Part B — loads the REAL helper functions from src/features/jobcode.js into a vm sandbox
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
// Frontend source corpus (scripts/frontend_modules.json modules first, then index.html): the data-action dispatcher
// that wires the helper's actions lives in src/boot.js since Phase 3 of the rebuild; the markup stays in index.html.
const html = [...JSON.parse(fs.readFileSync(path.join(repo, 'scripts', 'frontend_modules.json'), 'utf8')).sources.map((rel) => fs.readFileSync(path.join(repo, rel), 'utf8')), fs.readFileSync(path.join(repo, 'index.html'), 'utf8')].join('\n');
const js = fs.readFileSync(path.join(repo, 'src', 'features', 'jobcode.js'), 'utf8');
const data = JSON.parse(fs.readFileSync(path.join(repo, 'data', 'jobcode_master.json'), 'utf8'));
const ko = JSON.parse(fs.readFileSync(path.join(repo, 'data', 'i18n', 'ko.json'), 'utf8'));
const polish = fs.readFileSync(path.join(repo, 'assets', 'css', 'jobcode-refinement.css'), 'utf8');

const failures = [];
const ok = (cond, msg) => { if (!cond) failures.push(msg); };
const has = (needle, msg) => ok(html.includes(needle), msg || `missing in index.html: ${needle}`);
const hasJs = (needle, msg) => ok(js.includes(needle), msg || `missing in src/features/jobcode.js: ${needle}`);

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
hasJs('renderEmploymentSpecialStates', 'special-states renderer not wired');
hasJs('runEmploymentSpecialAction', 'special-state actions not wired');
{
  const ids = ['no_official_code', 'broad_indirect_match', 'freelancer', 'self_employed',
    'trainee', 'arts_entertainment', 'legally_sensitive', 'mixed_language',
    'low_confidence', 'source_unverifiable'];
  const i18nMap = js.slice(js.indexOf('const JC_SPECIAL_I18N'), js.indexOf('function renderEmploymentSpecialStates'));
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
// Visual refinement must remain compatible with the existing functional markup.
// Result progress is an announcement, NOT a new mandatory step or code verdict.
has('id="jcChoiceProgress"', 'selection progress indicator missing');
has('class="jc2-lead-index"', 'search-stage visual hierarchy missing');
has('class="jc2-result-index"', 'result-stage visual hierarchy missing');
has('assets/css/jobcode-refinement.css', 'scoped UI polish stylesheet not loaded');
hasJs('progress.classList.toggle', 'selection progress not updated by the existing summary renderer');
ok(polish.includes('#jobCodeModalOverlay .jc2-modal') && polish.includes('max-width: 940px'),
  'finder must have a usable desktop width for two-pane comparisons');
ok(polish.includes('@media (max-width: 680px)') && polish.includes('.jc2-summary.is-active { position: static; }'),
  'mobile selection summary must not cover result cards');
ok(polish.includes('@media (prefers-reduced-motion: reduce)'),
  'reduced-motion support missing from finder polish');
ok(polish.includes(':focus-visible') && polish.includes('min-height: 43px'),
  'finder candidate actions need visible focus and mobile-sized tap targets');
ok(!polish.includes('display: none; /* scope warning */'),
  'finder must never hide permission/reporting warning');
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
// Keep the initial search focused: examples appear only as contextual weak-result help.
ok(!/id="jcExamplesLabel"|id="jcChips"|data-jc-chip=/.test(html), 'default-view example prompts must be absent');
ok(ko.jobCodePlaceholder === '직종명, 업종명 또는 하는 일을 검색하세요', 'KO search placeholder should guide without a sample list');
// separate panes + badges
has('data-pane="occupation"', 'occupation pane missing');
has('data-pane="industry"', 'industry pane missing');
has('이건 직종이에요', 'occupation badge missing');
has('이건 업종이에요', 'industry badge missing');
// selected summary + copy
['jcSelOcc', 'jcSelInd', 'jcIncome', 'jcCopyBtn'].forEach(id => has(`id="${id}"`, `summary element #${id} missing`));
has('data-action="copy-jobcode-memo"', 'copy-memo action missing');
has('HiKorea 입력용 메모 복사', 'copy button label missing');
// required warnings (Phase 5 boundary + final-check copy)
has('취업정보 신고용 분류 참고', 'required reference-only warning missing');
has('자격외활동 허가 여부를 판단하지 않습니다', 'required boundary warning missing');
has('HiKorea 신고 화면 또는 1345', 'required final-confirmation warning missing');
// wiring: action handlers present
['set-jobcode-filter', 'select-jobcode', 'copy-jobcode-memo'].forEach(a =>
  has(`'${a}'`, `action handler '${a}' not wired`));
// risky label replaced: AI button must not say "공식 직종·업종"
ok(!ko.jobCodeNaturalSearchLocal.includes('공식'), 'jobCodeNaturalSearchLocal still uses risky "공식" wording');
// keyboard: interactive controls are native focusable elements
has('type="search" id="jcSearchInput"', 'search input must be a native <input type=search>');
ok(/<button type="button"[^>]*class="jc2-seg/.test(html), 'filter tabs must be native <button> (keyboard focusable)');
hasJs('class="jc2-weak-chip"', 'contextual weak-result example buttons must remain available');
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
// The module is plain script apart from its trailing `export {…}` block, so the slice up
// to that block evaluates as a classic script in the sandbox.
const startMark = '// --- Job Code Modal · HiKorea';
const start = js.indexOf(startMark);
const endMark = '\nexport {';
const end = js.indexOf(endMark, start);
ok(start !== -1 && end !== -1, 'could not locate helper JS region in src/features/jobcode.js');

if (start !== -1 && end !== -1) {
  const region = js.slice(start, end);
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
  getScoredJobcodeRows, jobcodeEmptyHtml, buildJobcodeMemo, renderJobcodeGuidance, renderJobcodeSelectedSummary,
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
    // 7) Result-header progress follows existing selections (no extra gate).
    JC.renderJobcodeSelectedSummary();
    ok(dom._els['jcChoiceProgress'].textContent === '2/2 선택 완료',
      'both selections must mark the result header as complete');
    JC.setSelected({ occupation: { code: '22', name: '정보 통신 전문가 및 기술직' }, industry: null });
    JC.renderJobcodeSelectedSummary();
    ok(dom._els['jcChoiceProgress'].textContent === '1/2 선택',
      'one classification must remain visibly incomplete');
    JC.setSelected({ occupation: null, industry: null });
    JC.renderJobcodeSelectedSummary();
    ok(dom._els['jcChoiceProgress'].textContent === '0/2 선택',
      'resetting the finder must reset selection progress');
  }
}

if (failures.length) {
  console.error('[check_employment_reporting_helper] FAIL');
  failures.forEach(m => console.error('  - ' + m));
  process.exit(1);
}
console.log('[check_employment_reporting_helper] OK — static structure, microcopy, search behavior, ambiguity, boundary, empty state, and memo all verified');
