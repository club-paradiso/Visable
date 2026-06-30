#!/usr/bin/env node
/**
 * check_hikorea_reservation_helper.mjs
 * Validation for the redesigned 하이코리아 예약 도우미 / HiKorea Reservation Helper
 * (assets/js/hikorea-reservation-helper.js).
 *
 * Offline, no deps. It:
 *   1. extracts the REAL pure logic (computeReservationPath) from the module and
 *      exercises the spec scenarios deterministically;
 *   2. asserts the status-specific suggestion lists (incl. the F-5 specific-label
 *      rule) and the friendly one-question-per-step flow copy + section labels;
 *   3. asserts the cautious-wording / disclaimer / same-day guarantees and that
 *      the flow is LLM-free;
 *   4. asserts the index.html wiring (deferred script, modal shell reuse) and
 *      KO/EN chrome-pack parity (also enforced by check_popup_i18n.mjs).
 *
 * Run: node scripts/check_hikorea_reservation_helper.mjs
 */
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..');
const read = (p) => readFileSync(join(ROOT, p), 'utf8');

let failures = 0;
let checks = 0;
function ok(cond, label, extra) {
  checks++;
  if (cond) console.log(`  PASS  ${label}`);
  else { failures++; console.log(`  FAIL  ${label}${extra ? ' — ' + extra : ''}`); }
}
function section(t) { console.log(`\n== ${t}`); }

const src = read('assets/js/hikorea-reservation-helper.js');
const indexHtml = read('index.html');

/* ------------------------------------------------ extract the pure function */
// Brace-balanced extraction (indentation-independent). The function contains no
// braces inside string literals, so a plain counter is correct here.
function extractFn(source, name) {
  const sig = 'function ' + name + '(';
  const start = source.indexOf(sig);
  if (start === -1) return null;
  let i = source.indexOf('{', start);
  let depth = 0;
  for (; i < source.length; i++) {
    const c = source[i];
    if (c === '{') depth++;
    else if (c === '}') { depth--; if (depth === 0) { i++; break; } }
  }
  return source.slice(start, i);
}

section('Pure deterministic logic (computeReservationPath)');
let compute = null;
try {
  const fnSrc = extractFn(src, 'computeReservationPath');
  // eslint-disable-next-line no-new-func
  compute = new Function(`${fnSrc}; return computeReservationPath;`)();
} catch (e) { /* asserted below */ }
ok(typeof compute === 'function', 'computeReservationPath extracted + callable', compute ? '' : 'extraction failed');

if (typeof compute === 'function') {
  // 1. D-2 + no card + in Korea -> alien registration
  const s1 = compute({ statusCode: 'D-2', hasRegistrationCard: 'no', currentLocation: 'in_korea' });
  ok(s1.recommendedPurpose === 'registration', 'D-2 + no card + in Korea → registration', s1.recommendedPurpose);

  // 2. D-2 + has card + extension purpose -> extension
  const s2 = compute({ statusCode: 'D-2', hasRegistrationCard: 'yes', reservationPurpose: 'extension' });
  ok(s2.recommendedPurpose === 'extension', 'D-2 + has card + extension → extension', s2.recommendedPurpose);
  ok(s2.warnings.includes('extensionWindow'), 'extension flow surfaces the application-window caution');

  // 3. F-4 + no card -> domestic residence report (거소) path, not 외국인등록
  const s3 = compute({ statusCode: 'F-4', hasRegistrationCard: 'no' });
  ok(s3.recommendedPurpose === 'residence_report', 'F-4 + no card → residence_report (국내거소신고)', s3.recommendedPurpose);
  const s3b = compute({ statusCode: 'F-4', hasRegistrationCard: 'no', reservationPurpose: 'registration' });
  ok(s3b.recommendedPurpose === 'residence_report' && s3b.warnings.includes('f4ResidenceReport'),
    'F-4 routes a registration choice to residence_report with an explanatory note', s3b.recommendedPurpose);

  // 4. E-7 + workplace change -> workplace
  const s4 = compute({ statusCode: 'E-7', reservationPurpose: 'workplace' });
  ok(s4.recommendedPurpose === 'workplace', 'E-7 + workplace → workplace', s4.recommendedPurpose);

  // 6. unsure -> low-confidence fallback that points to 1345
  const s6 = compute({ reservationPurpose: 'unsure' });
  ok(s6.recommendedPurpose === 'unsure' && s6.confidence === 'low', 'unsure → unsure + low confidence', s6.recommendedPurpose + '/' + s6.confidence);
  ok(s6.warnings.includes('unsureGuidance'), 'unsure → 1345/office fallback guidance warning');

  // 7. same-day + real-name cautions ALWAYS present
  ok(s1.warnings.includes('sameDay') && s2.warnings.includes('sameDay') && s6.warnings.includes('sameDay'),
    'same-day caution present on every result');
  ok(s1.warnings.includes('realName'), 'real-name caution present');

  // Overseas notice + fixed 9-step click path + 5 blocked tips
  const sOver = compute({ currentLocation: 'overseas', reservationPurpose: 'extension' });
  ok(sOver.warnings.includes('overseasNotice'), 'overseas selection surfaces the in-Korea notice');
  ok(Array.isArray(s1.hikoreaClickSteps) && s1.hikoreaClickSteps.length === 9, 'HiKorea click path has 9 steps');
  ok(Array.isArray(s1.blockedCaseTips) && s1.blockedCaseTips.length === 5, 'five blocked-case tips returned');

  // Expiry handling
  ok(compute({ reservationPurpose: 'extension', expiryDate: '2000-01-01' }).warnings.includes('expired'),
    'past expiry date → expired warning');
  ok(compute({ reservationPurpose: 'extension', expiryDate: '2999-01-01' }).expiryStatus === 'ok',
    'far-future expiry date → ok status');

  // Determinism: identical input → identical output
  ok(JSON.stringify(compute({ statusCode: 'D-2', hasRegistrationCard: 'no', currentLocation: 'in_korea' })) === JSON.stringify(s1),
    'deterministic: identical input → identical output');
}

/* ------------------------------------ whole-module load (regression guard) */
// The pure-function extraction above never evaluates the rest of the module, so
// a load-time ReferenceError (e.g. STR_PACKS pointing at an undefined STR_*
// pack) would sail past every other check while breaking the live feature: the
// IIFE throws before `window.ParadisoReservationHelper = …`, so the card opens
// an empty modal. Execute the full module against minimal DOM/window stubs and
// assert the public API is actually published.
section('Whole-module load publishes window.ParadisoReservationHelper');
{
  const noop = () => {};
  const win = { addEventListener: noop };
  const doc = { addEventListener: noop, getElementById: () => null, querySelector: () => null, querySelectorAll: () => [] };
  const storage = { getItem: () => null, setItem: noop, removeItem: noop };
  let threw = null;
  try {
    // eslint-disable-next-line no-new-func
    new Function('window', 'document', 'localStorage', 'navigator', 'Proxy', src)(
      win, doc, storage, { language: 'ko' }, Proxy
    );
  } catch (e) { threw = e; }
  ok(!threw, 'full module evaluates without throwing at load time', threw ? String(threw.message || threw) : '');
  ok(win.ParadisoReservationHelper && typeof win.ParadisoReservationHelper.open === 'function',
    'window.ParadisoReservationHelper.open published after load');
}

/* --------------------------------------------- status-specific suggestions */
section('Visa/status integration — common reservation purposes');
function suggestionIds(code) {
  const block = src.split('STATUS_SUGGESTIONS', 2)[1] || '';
  const re = new RegExp("'" + code.replace('-', '\\-') + "'\\s*:\\s*\\[([^\\]]*)\\]");
  const m = block.match(re);
  if (!m) return [];
  return m[1].split(',').map((x) => x.trim().replace(/^'|'$/g, '')).filter(Boolean);
}
const SUGG = {
  'D-2': ['registration', 'extension', 'address', 'activity'],
  'F-4': ['residence_report', 'extension', 'residence_reissue', 'address'],
  'E-7': ['registration', 'change_status', 'workplace', 'extension'],
  'F-6': ['registration', 'extension', 'address', 'reissue'],
  'F-5': ['address', 'reissue', 'reg_change', 'consult_f5'],
  'G-1': ['registration', 'extension', 'address', 'consult']
};
for (const [code, expected] of Object.entries(SUGG)) {
  ok(JSON.stringify(suggestionIds(code)) === JSON.stringify(expected), `${code} common-purpose suggestions match spec`, suggestionIds(code).join(','));
}

// 5. F-5 uses specific labels, never vague ones.
ok(src.includes("pAddress: '체류지 변경'") && src.includes("pReissue: '등록증 재발급'") && src.includes("pRegChange: '등록사항 변경'"),
  'F-5-relevant labels are concrete (체류지 변경 · 등록증 재발급 · 등록사항 변경)');
ok(!src.includes('영주 관련 후속 민원') && !src.includes('외국인등록 관련 업무'),
  'no vague F-5 labels (영주 관련 후속 민원 / 외국인등록 관련 업무)');

/* --------------------------------------------------- friendly flow + copy */
section('Friendly one-question-per-step flow + result sections');
const FLOW_Q_KO = [
  '무엇 때문에 출입국에 가시나요?',
  '외국인등록증이나 거소증이 있나요?',
  '지금 한국에 있나요?',
  '현재 체류자격을 알고 있나요?',
  '체류기간 만료일이 언제인가요?'
];
for (const q of FLOW_Q_KO) ok(src.includes(q), `flow question present: ${q}`);
const FLOW_Q_EN = [
  'Why are you visiting immigration?',
  'Do you have an Alien Registration Card or residence card?',
  'Are you currently in Korea?',
  'Do you know your current visa/status type?',
  'When does your current stay expire?'
];
for (const q of FLOW_Q_EN) ok(src.includes(q), `EN flow question present: ${q}`);

const SECTIONS = [
  ['하이코리아에서 누를 것', 'What to click on HiKorea'],
  ['예약 전에 준비할 것', 'What to prepare before booking'],
  ['예약 후 확인할 것', 'What to check after booking'],
  ['예약이 안 될 때', 'If booking does not work']
];
for (const [ko, en] of SECTIONS) ok(src.includes(ko) && src.includes(en), `result section present: ${ko} / ${en}`);

// Header + CTAs
ok(src.includes('하이코리아 예약 도우미') && src.includes('HiKorea Reservation Helper'), 'feature title present (KO + EN)');
ok(src.includes('예약 경로 찾기') && src.includes('Find my reservation path'), 'primary CTA present');
ok(src.includes('하이코리아 바로가기') && src.includes('Go to HiKorea'), 'secondary CTA present');
ok(src.includes('구비서류 체크리스트 보기') && src.includes('View document checklist'), 'document-checklist CTA present');
ok(src.includes('결과 저장') && src.includes('Save result'), 'save-result CTA present');

// Click-path steps (KO)
const CLICKS = ['하이코리아 접속', '민원신청 선택', '방문예약 선택', '방문예약 신청 선택', '회원 로그인 또는 비회원 인증', '관할 출입국관서 선택', '방문 목적 선택', '날짜와 시간 선택', '예약 완료 후 접수증 저장'];
for (const c of CLICKS) ok(src.includes(c), `click-path step present: ${c}`);

// Blocked-case cards (5)
const BLOCKED = ['날짜가 안 보여요', '오늘 방문하고 싶어요', '어느 출입국을 골라야 할지 모르겠어요', '로그인이나 인증이 안 돼요', '어떤 업무를 골라야 할지 모르겠어요'];
for (const b of BLOCKED) ok(src.includes(b), `blocked-case card present: ${b}`);

/* ------------------------------------------------ cautious wording / safety */
section('Cautious wording, disclaimer, and LLM-free guarantee');
ok(src.includes('하이코리아에서 이 업무로 예약할 가능성이 높습니다.'), 'cautious "likely" result lead present (KO)');
ok(src.includes('당일 예약은 되지 않을 수 있'), 'same-day caution copy present');
ok(src.includes('예약은 실제 방문하는 사람 이름으로 해야 합니다.'), 'real-name caution copy present');
ok(src.includes('이 도우미는 예약 전에 필요한 정보를 정리해 주는 안내입니다.') &&
   src.includes('This helper organizes information before booking.'),
  'official-source disclaimer present (KO + EN)');
ok(/1345/.test(src), 'points users to 1345 for unclear cases');
ok(!/Waymaker|submitAiAnalysis|\/api\/ask|openai|gpt|gemini|fetch\(/i.test(src), 'flow is deterministic — no LLM / network calls');

/* -------------------------------------------------------- a11y + structure */
section('Accessibility + structure');
ok(/role="progressbar"/.test(src) && /aria-valuenow=/.test(src), 'progress indicator exposes a progressbar with aria-valuenow');
ok(src.includes("' / '") || src.includes('/ \' + total'), 'progress shows step / total');
ok(/data-prh-action="next"/.test(src) && /data-prh-action="back"/.test(src), 'visible next/back controls');
ok(/<button type="button" class="prh-opt/.test(src), 'options are real semantic buttons (keyboard-navigable)');
ok(/:focus-visible/.test(src), 'visible focus styles defined');
ok(/@media \(max-width:560px\)/.test(src), 'mobile-first responsive CSS present');
ok(/color-mix\(in srgb,var\(--ac\)/.test(src) && /var\(--bg1\)/.test(src) && /var\(--t1\)/.test(src),
  'uses theme tokens (readable in both civic_editorial + archive_diary)');

/* ----------------------------------------------------------- index wiring */
section('index.html wiring');
ok(indexHtml.includes('assets/js/hikorea-reservation-helper.js'), 'index.html loads the deferred helper module');
ok(/window\.ParadisoReservationHelper\s*=/.test(src) && /open:\s*open/.test(src) && /computeReservationPath:\s*computeReservationPath/.test(src),
  'window.ParadisoReservationHelper exposes open() + computeReservationPath()');
ok(indexHtml.includes("openModal('hikoreaGuideOverlay')"), 'reuses the modal shell (focus trap / Escape / focus restore)');
ok(indexHtml.includes('ParadisoReservationHelper'), 'index.html delegates the guide entry to the module');
ok(!/hikoreaGuideState\b/.test(indexHtml), 'old inline guide state removed from index.html');
ok(!/generateHikoreaPassword|renderHikoreaGuide\(\)\s*\{[^}]*hikoreaGuideState/.test(indexHtml), 'old password-gen / step renderer scaffold removed from index.html');

/* ------------------------------------------------------ KO/EN pack parity */
section('Chrome pack parity (KO/EN)');
function packKeys(name) {
  const decl = 'var ' + name + ' = {';
  const start = src.indexOf(decl);
  if (start === -1) return null;
  let i = src.indexOf('{', start) + 1;
  const keys = new Set();
  let depth = 0;
  let pend = '';
  while (i < src.length) {
    const ch = src[i];
    if (ch === '"' || ch === "'" || ch === '`') { const q = ch; i++; while (i < src.length) { if (src[i] === '\\') { i += 2; continue; } if (src[i] === q) { i++; break; } i++; } pend = ''; continue; }
    if (ch === '{' || ch === '[' || ch === '(') { depth++; i++; pend = ''; continue; }
    if (ch === ']' || ch === ')') { depth--; i++; pend = ''; continue; }
    if (ch === '}') { if (depth === 0) break; depth--; i++; pend = ''; continue; }
    if (depth === 0) {
      if (/[A-Za-z_$]/.test(ch)) { let j = i; let id = ''; while (j < src.length && /[\w$]/.test(src[j])) { id += src[j]; j++; } pend = id; i = j; continue; }
      if (ch === ':' && pend) { keys.add(pend); pend = ''; i++; continue; }
      if (!/\s/.test(ch)) pend = '';
    }
    i++;
  }
  return keys;
}
const ko = packKeys('STR_KO');
const en = packKeys('STR_EN');
ok(ko && en && ko.size === en.size, 'STR_KO / STR_EN have the same number of keys', ko && en ? `${ko.size} vs ${en.size}` : 'missing pack');
if (ko && en) {
  const missEn = [...ko].filter((k) => !en.has(k));
  const missKo = [...en].filter((k) => !ko.has(k));
  ok(missEn.length === 0, 'STR_EN covers every STR_KO key', missEn.join(','));
  ok(missKo.length === 0, 'STR_KO covers every STR_EN key', missKo.join(','));
}

console.log(`\n${failures ? 'FAIL' : 'OK'} — ${checks - failures}/${checks} checks passed`);
process.exit(failures ? 1 : 0);
