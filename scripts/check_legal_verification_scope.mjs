// The visible evidence panel must distinguish version identity from body review.
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
const bundle = JSON.parse(readFileSync('data/status-guidance-202609.json','utf8'));
for (const file of ['status-guidance.js','search-router.js','waymaker-quick-answer.js'])
  new Function(readFileSync('assets/js/'+file,'utf8'))();
for (const lang of ['ko','en']) {
  const SG = globalThis.VisableStatusGuidance;
  const query = lang === 'ko' ? '체류지 변경 신고' : 'address change report';
  const state = {query,interp:SG.interpret(query,bundle),answers:{},history:[],lang};
  const step = SG.nextStep(state,bundle);
  const out = SG.renderModel(step,state,bundle);
  assert(out.html.includes('sg-law-review-scope'), 'body review scope must be visible');
  assert(out.html.includes('2026-10-26') && out.html.includes('2026-09-22'));
  assert(out.html.includes(lang === 'ko' ? '재검토 필요' : 'needs revalidation'));
  const qa = globalThis.VisableQuickAnswer.build({model:out.model,step,state,bundle,lang});
  assert(qa.model.uncertainties.some(u=>u.id==='law_body_review'));
}
assert.equal(bundle.law_sources.rule_73.review_state,'ARTICLE_TEXT_AT_REFERENCE_DATE_READ');
assert.equal(bundle.law_sources.rule_form_34.body_review_state,'PREVIOUS_VERSION_SUMMARY_ONLY');
console.log('Legal verification scope: visible in KO/EN evidence and quick answer; article-only exception preserved.');
