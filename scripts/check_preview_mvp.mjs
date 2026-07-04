#!/usr/bin/env node
/**
 * PreView by Paradiso — dependency-free smoke test.
 *
 * Validates the standalone PreView MVP surface:
 *   - route + asset wiring, required copy, forbidden copy
 *   - independence (no Visable CTA, no HiKorea CTA)
 *   - fallback data shape via the real preview-data.js / preview-app.js
 *     pure helpers executed in a Node vm sandbox (no DOM required)
 *   - source registry / snapshot hygiene (hosts, evidence levels, no dumps)
 *   - no public-data service key material in frontend files
 *
 * Run: node scripts/check_preview_mvp.mjs   (alias: npm run test:preview)
 */

import { readFileSync, existsSync } from 'node:fs';
import path from 'node:path';
import vm from 'node:vm';
import { fileURLToPath } from 'node:url';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const failures = [];
let checks = 0;

function ok(condition, label) {
  checks += 1;
  if (condition) {
    console.log(`  ok  ${label}`);
  } else {
    failures.push(label);
    console.error(`FAIL  ${label}`);
  }
}

function read(rel) {
  return readFileSync(path.join(ROOT, rel), 'utf8');
}

/* ------------------------------------------------------------ files ---- */
const FRONTEND_FILES = [
  'preview.html',
  'assets/css/preview.css',
  'assets/js/preview/preview-data.js',
  'assets/js/preview/preview-app.js',
];
const DATA_FILES = [
  'data/preview/preview-source-registry.json',
  'data/preview/mission-notices.snapshot.json',
  'data/preview/visa-waiver.snapshot.json',
];

console.log('[check_preview_mvp] file presence');
for (const rel of [...FRONTEND_FILES, ...DATA_FILES]) {
  ok(existsSync(path.join(ROOT, rel)), `${rel} exists`);
}
if (failures.length) {
  console.error(`\n[check_preview_mvp] aborting: ${failures.length} missing file(s).`);
  process.exit(1);
}

const html = read('preview.html');
const css = read('assets/css/preview.css');
const dataJs = read('assets/js/preview/preview-data.js');
const appJs = read('assets/js/preview/preview-app.js');
const frontendBlob = html + '\n' + css + '\n' + dataJs + '\n' + appJs;

/* ------------------------------------------------- route + wiring ------ */
console.log('[check_preview_mvp] route wiring');
ok(html.includes('assets/js/preview/preview-data.js'), 'preview.html references preview-data.js');
ok(html.includes('assets/js/preview/preview-app.js'), 'preview.html references preview-app.js');
ok(html.includes('assets/css/preview.css'), 'preview.html references preview.css');
ok(html.includes('PreView') && html.includes('by Paradiso'), 'preview.html shows "PreView by Paradiso" branding');
ok(html.includes('Before Korea, PreView your first official step.'), 'hero headline present');
ok(html.includes('한국 입국 전, 첫 공식 절차를 미리 확인하세요.'), 'Korean hero headline present');

/* -------------------------------------------------- independence ------- */
console.log('[check_preview_mvp] independence (no Visable / HiKorea CTA)');
ok(!/visable/i.test(frontendBlob), 'preview frontend contains no Visable reference');
ok(!/hikorea/i.test(frontendBlob), 'preview frontend contains no HiKorea reference');
const internalLinks = [...html.matchAll(/href="([^"]+)"/g)]
  .map((m) => m[1])
  .filter((href) => !href.startsWith('https://') && !href.startsWith('#') && !href.startsWith('assets/'));
ok(internalLinks.length === 0, `no internal page links out of PreView (found: ${internalLinks.join(', ') || 'none'})`);

/* ------------------------------------------------- required copy ------- */
console.log('[check_preview_mvp] required user-facing copy');
const REQUIRED_COPY = [
  '입국 전 확인사항',
  '공관 공식 안내 확인',
  '공식 원문 확인 필요',
  '관할 공관에 최종 확인하세요',
  '공공데이터 API 기반',
  '공식 공개자료 기반',
  '매뉴얼 기준 참고',
  'MVP 샘플 데이터',
];
for (const phrase of REQUIRED_COPY) {
  ok(frontendBlob.includes(phrase), `required copy present: "${phrase}"`);
}
ok(
  html.includes('PreView는 외교 공공데이터와 공식 공개자료를 바탕으로 입국 전 확인사항을 정리하는 서비스입니다.'),
  'visible disclaimer sentence present in preview.html',
);
ok(
  frontendBlob.includes('현재 공공데이터 API 응답을 불러오지 못해 MVP 샘플 데이터를 표시합니다.'),
  'API fallback copy present',
);
const HERO_BADGES = ['MOFA public data', 'Korean missions', 'Pre-arrival checklist', 'Source-grounded', 'Official web materials', 'Manual reference'];
for (const badgeText of HERO_BADGES) {
  ok(html.includes(badgeText), `hero badge present: "${badgeText}"`);
}
const CARD_TITLES = [
  ['공관', 'Mission'], ['입국 전 확인', 'Entry pre-check'], ['공관 공개 안내', 'Mission notice'],
  ['매뉴얼 기준 참고', 'Manual reference'], ['안전 참고', 'Safety note'], ['준비 체크리스트', 'Checklist'],
  ['문의 문장', 'Contact script'], ['출처', 'Sources'],
];
for (const [ko, en] of CARD_TITLES) {
  ok(appJs.includes(`card('${ko}', '${en}'`), `result card wired: ${ko} / ${en}`);
}

/* ------------------------------------------------- forbidden copy ------ */
console.log('[check_preview_mvp] forbidden user-facing strings');
const FORBIDDEN = [
  { label: 'TBD', re: /\bTBD\b/ },
  { label: 'N/A', re: /\bN\/A\b/i },
  { label: 'lorem ipsum', re: /lorem ipsum/i },
  { label: 'fake phone', re: /fake phone/i },
  { label: 'fake URL', re: /fake url/i },
  { label: '실시간 전세계 공관', re: /실시간 전세계 공관/ },
  { label: '비자 발급 보장', re: /비자 발급 보장/ },
  { label: '승인 가능성 예측', re: /승인 가능성 예측/ },
  { label: '대사관 장벽', re: /대사관 장벽/ },
  { label: '진짜 비자 체크리스트', re: /진짜 비자 체크리스트/ },
  { label: '법무부 공식 대체', re: /법무부 공식 대체/ },
  { label: '내부 심사 기준', re: /내부 심사 기준/ },
];
for (const { label, re } of FORBIDDEN) {
  ok(!re.test(frontendBlob), `forbidden string absent: "${label}"`);
}

/* --------------------------------------------------- key hygiene ------- */
console.log('[check_preview_mvp] service-key hygiene in frontend files');
ok(!/SERVICE_KEY/i.test(frontendBlob), 'no SERVICE_KEY env name in frontend files');
ok(!/serviceKey\s*=\s*["'][A-Za-z0-9%+/=]{15,}/.test(frontendBlob), 'no inline serviceKey value in frontend files');
const KEY_ENVS = [
  'PUBLIC_DATA_SERVICE_KEY',
  'MOFA_EMBASSY_SERVICE_KEY',
  'MOFA_EMBASSY_HOMEPAGE_SERVICE_KEY',
  'MOFA_ENTRANCE_VISA_SERVICE_KEY',
  'MOFA_COUNTRY_SAFETY_SERVICE_KEY',
  'MOFA_TRAVEL_ALARM_SERVICE_KEY',
  'MOFA_NOTICE_SERVICE_KEY',
];
for (const envName of KEY_ENVS) {
  const value = process.env[envName];
  if (value && value.length >= 8) {
    ok(!frontendBlob.includes(value), `live ${envName} value not present in frontend files`);
  }
}

/* --------------------------------------------- data via vm sandbox ----- */
console.log('[check_preview_mvp] fallback data + pure helpers (vm sandbox)');
const sandbox = vm.createContext({ console: { log() {}, warn() {}, error() {} } });
let vmOk = true;
try {
  vm.runInContext(dataJs, sandbox, { filename: 'preview-data.js' });
  vm.runInContext(appJs, sandbox, { filename: 'preview-app.js' });
} catch (error) {
  vmOk = false;
  ok(false, `preview JS executes in Node vm (${error.message})`);
}
if (vmOk) {
  const data = vm.runInContext('globalThis.PREVIEW_FALLBACK_DATA', sandbox);
  const app = vm.runInContext('globalThis.PreViewApp', sandbox);
  ok(!!data, 'PREVIEW_FALLBACK_DATA is exposed');
  ok(!!app, 'PreViewApp namespace is exposed');
  ok(Array.isArray(data.bundles) && data.bundles.length >= 3, `>= 3 country/post bundles (found ${data.bundles?.length ?? 0})`);
  ok(data.isSample === true, 'fallback data is flagged isSample: true');
  for (const bundle of data.bundles ?? []) {
    ok(
      !!(bundle.countryKo && bundle.countryEn && bundle.iso2 && Array.isArray(bundle.posts) && bundle.posts.length > 0),
      `bundle ${bundle.id}: country ko/en + iso2 + posts present`,
    );
    ok(Array.isArray(bundle.sources) && bundle.sources.length >= 3, `bundle ${bundle.id}: source metadata array present`);
    ok(!!bundle.entryPrecheck?.summaryKo, `bundle ${bundle.id}: entry pre-check summary present`);
    ok(!!bundle.safety?.summaryKo, `bundle ${bundle.id}: safety summary present`);
  }
  ok(typeof data.unsupportedCountryMessageKo === 'string' && data.unsupportedCountryMessageKo.length > 20,
    'unsupported-country fallback copy exists');
  ok(app.findBundle(data, 'vn')?.iso2 === 'VN', 'findBundle resolves vn -> VN bundle');
  ok(app.findBundle(data, 'zz') === null, 'findBundle returns null for unsupported country');
  ok(app.buildChecklist('study', data.bundles[0]).length >= 5, 'buildChecklist(study) yields >= 5 items');
  const script = app.buildContactScript({ purpose: 'business', nationality: '몽골' });
  ok(script.ko.includes('몽골') && script.en.length > 20, 'buildContactScript includes nationality + EN variant');
  ok(app.manualRefsForPurpose(data, 'study').length >= 1, 'manualRefsForPurpose(study) returns manual records');
  ok(app.escapeHtml('<script>"x"</script>') === '&lt;script&gt;&quot;x&quot;&lt;/script&gt;', 'escapeHtml escapes HTML metacharacters');
  ok(app.isAllowedLink('https://overseas.mofa.go.kr/vn-ko/index.do') === true, 'isAllowedLink accepts official mission host');
  ok(app.isAllowedLink('https://evil.example.com/x') === false, 'isAllowedLink rejects non-official host');
}

/* ------------------------------------------------ registry checks ------ */
console.log('[check_preview_mvp] source registry');
const registry = JSON.parse(read('data/preview/preview-source-registry.json'));
ok(Array.isArray(registry.sources) && registry.sources.length >= 5, `registry has >= 5 sources (found ${registry.sources?.length ?? 0})`);
for (const source of registry.sources ?? []) {
  ok(
    !!(source.id && source.titleKo && source.provider && source.sourceFamily && source.sourceType &&
       source.evidenceLevel && source.usedFor && source.lastChecked && source.limitationsKo),
    `registry source "${source.id}": required fields (titleKo/provider/sourceType/evidenceLevel/limitationsKo/...) present`,
  );
}
const FAMILIES = ['public_data_portal_api', 'public_data_portal_file', 'official_mission_web', 'uploaded_manual_reference', 'local_mvp_sample'];
for (const family of FAMILIES) {
  ok(registry.sources.some((s) => s.sourceFamily === family), `registry covers sourceFamily "${family}"`);
}

/* -------------------------------------------- mission-notice hosts ----- */
console.log('[check_preview_mvp] mission-notice snapshot hygiene');
const notices = JSON.parse(read('data/preview/mission-notices.snapshot.json'));
const ALLOWED_HOSTS = new Set(['mofa.go.kr', 'www.mofa.go.kr', 'overseas.mofa.go.kr']);
ok(Array.isArray(notices.items) && notices.items.length > 0, 'mission-notice snapshot has items');
for (const item of notices.items ?? []) {
  let host = null;
  try { host = new URL(item.url).hostname; } catch { /* leave null */ }
  ok(host !== null && ALLOWED_HOSTS.has(host), `notice "${item.title}" host is official (${host ?? 'invalid URL'})`);
  ok(item.sourceType === 'overseas_mofa_public_web', `notice "${item.title}" sourceType is overseas_mofa_public_web`);
  ok(!!item.extractionStatus, `notice "${item.title}" carries extractionStatus`);
  ok(typeof item.textSnippet === 'string' && item.textSnippet.length <= 500, `notice "${item.title}" snippet is short`);
}

/* -------------------------------------------- manual snapshot ---------- */
console.log('[check_preview_mvp] manual snapshot (optional)');
const manualPath = path.join(ROOT, 'data/preview/visa-issuance-manual.snapshot.json');
if (existsSync(manualPath)) {
  const manual = JSON.parse(readFileSync(manualPath, 'utf8'));
  ok(Array.isArray(manual.records) && manual.records.length > 0, 'manual snapshot has records');
  for (const record of manual.records ?? []) {
    ok(record.evidenceLevel === 'manual_reference', `manual record ${record.code}: evidenceLevel manual_reference`);
    ok(record.requiresOfficialMissionCheck === true, `manual record ${record.code}: requiresOfficialMissionCheck true`);
    const longest = Math.max(...Object.values(record).map((v) => (typeof v === 'string' ? v.length : 0)));
    ok(longest <= 400, `manual record ${record.code}: no long verbatim dumps (longest field ${longest} chars)`);
  }
} else {
  console.log('  ok  manual snapshot absent — acceptable (PreView works without the manual layer)');
}

/* ------------------------------------------------------------- exit ---- */
if (failures.length) {
  console.error(`\n[check_preview_mvp] FAILED — ${failures.length}/${checks} check(s) failed.`);
  process.exit(1);
}
console.log(`\n[check_preview_mvp] PASS — ${checks} checks passed.`);
