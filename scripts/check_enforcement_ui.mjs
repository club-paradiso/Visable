import fs from 'node:fs';
import path from 'node:path';
import assert from 'node:assert/strict';

const root = path.resolve(import.meta.dirname, '..');
const html = fs.readFileSync(path.join(root, 'enforcement.html'), 'utf8');
const css = fs.readFileSync(path.join(root, 'assets/css/enforcement.css'), 'utf8');
const js = fs.readFileSync(path.join(root, 'scripts/enforcement-ui.mjs'), 'utf8');
const index = fs.readFileSync(path.join(root, 'index.html'), 'utf8');
const vercelExtract = fs.readFileSync(path.join(root, 'api/enforcement/extract.js'), 'utf8');
const vercelAnalyze = fs.readFileSync(path.join(root, 'api/enforcement/analyze.js'), 'utf8');
const fallbackRuntime = fs.readFileSync(path.join(root, 'lib/enforcement-fallback.js'), 'utf8');

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
  ['Vercel extract fallback exists', vercelExtract.includes('extractStructuredCase') && vercelExtract.includes('deterministic-fallback')],
  ['Vercel analyze fallback exists', vercelAnalyze.includes('analyzeCase') && vercelAnalyze.includes('deterministic-fallback')],
  ['fallback runtime uses canonical rule snapshot', fallbackRuntime.includes("require('../backend/data/enforcement/legal_rules.json')")],
  ['fallback prediction stays unavailable without provider', fallbackRuntime.includes("status: 'UNAVAILABLE'") && fallbackRuntime.includes('예측 모델의 유효한 구조화 결과가 없습니다.')],
  ['fallback preserves no-precedent limitation', fallbackRuntime.includes('현재 확인 가능한 유사 공개사례가 충분하지 않습니다.')],
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
console.log(`Enforcement UI contract passed (${checks.length} checks).`);
