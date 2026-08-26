import fs from 'node:fs';
import path from 'node:path';
import assert from 'node:assert/strict';

const root = path.resolve(import.meta.dirname, '..');
const html = fs.readFileSync(path.join(root, 'enforcement.html'), 'utf8');
const css = fs.readFileSync(path.join(root, 'assets/css/enforcement.css'), 'utf8');
const js = fs.readFileSync(path.join(root, 'scripts/enforcement-ui.mjs'), 'utf8');
const index = fs.readFileSync(path.join(root, 'index.html'), 'utf8');

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
  ['shared backend resolver loaded', backendResolverIndex >= 0],
  ['shared backend resolver loads before enforcement module', backendResolverIndex >= 0 && backendResolverIndex < enforcementModuleIndex],
  ['shared backend resolver used', js.includes('window.VisableBackend') && js.includes('window.VisableBackend.origin')],
  ['production does not silently fall back to same-origin', js.includes("return local ? '' : null")],
  ['network failure has explicit user message', js.includes('Visable 분석 서버에 연결하지 못했습니다.')],
  ['HTTP failure preserves status', js.includes('분석 서버 요청에 실패했습니다. (${response.status})')],
  ['mobile breakpoint', css.includes('@media (max-width: 680px)')],
  ['mobile one-column results', /@media \(max-width: 680px\)[\s\S]*\.fact-grid, \.result-grid \{ grid-template-columns: 1fr; \}/.test(css)],
  ['reduced motion support', css.includes('prefers-reduced-motion')],
  ['homepage gateway', index.includes('enforcement.html')],
];

for (const [name, ok] of checks) assert.equal(ok, true, `enforcement UI contract failed: ${name}`);
console.log(`Enforcement UI contract passed (${checks.length} checks).`);
