#!/usr/bin/env node
// Validates the subcode detail modal end to end:
//   1. Static structure, event wiring, and accessibility hooks in index.html.
//   2. The pure HTML builder (buildSubcodeModalView) run headlessly against
//      EVERY subcode represented in visa_data.json — no raw value leaks, the
//      required section hierarchy is present, and honest source-gap copy is used
//      when a subcode has no confirmed documents / official references.
// Guards the "MAJOR SUBCODE UI REDESIGN" acceptance criteria against regression.
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(__dirname, '..');
const html = fs.readFileSync(path.join(repoRoot, 'index.html'), 'utf8');
const visas = JSON.parse(fs.readFileSync(path.join(repoRoot, 'visa_data.json'), 'utf8'));
const ko = JSON.parse(fs.readFileSync(path.join(repoRoot, 'data', 'i18n', 'ko.json'), 'utf8'));

const failures = [];
function check(name, cond, detail = '') { if (!cond) failures.push(`${name}${detail ? ': ' + detail : ''}`); }

// ---- 1. Static structure / wiring / a11y ----
check('modal markup #subcodeDetailOverlay present', /id="subcodeDetailOverlay"/.test(html));
check('modal is role=dialog aria-modal', /id="subcodeDetailOverlay"[^>]*role="dialog"[^>]*aria-modal="true"|id="subcodeDetailOverlay"[^>]*aria-modal="true"/.test(html) && /id="subcodeDetailOverlay"[^>]*role="dialog"/.test(html));
check('modal labelled by title', /aria-labelledby="subcodeModalTitle"/.test(html));
check('modal has close button', /data-action="close-subcode-modal"/.test(html));
check('modal body element present', /id="subcodeModalBody"/.test(html));
check('open handler wired', /'open-subcode-detail':\s*\(\)\s*=>\s*openSubcodeModal/.test(html));
check('close handler wired', /'close-subcode-modal':\s*\(\)\s*=>\s*closeModal\('subcodeDetailOverlay'\)/.test(html));
check('Escape key closes modal', /anyModalOpen = \[[^\]]*'subcodeDetailOverlay'/.test(html));
check('backdrop click closes modal', /classList\.contains\('subcode-modal-overlay'\)[\s\S]{0,80}closeModal\('subcodeDetailOverlay'\)/.test(html));
check('keyboard activation for role=button cards', /open-subcode-detail[\s\S]{0,240}openSubcodeModal\(card\.dataset\.parent/.test(html));
check('subcode cards are interactive', /data-action="open-subcode-detail" data-parent=/.test(html));
check('subcode cards expose role=button + tabindex', /manual-subcode-card--interactive[\s\S]{0,140}role="button" tabindex="0"/.test(html));
check('subcodes remain collapsed-by-default (expand group + toggle)', /renderExpandableSubcodeGroup/.test(html) && /'toggle-subcode-group'/.test(html));
check('mobile bottom-sheet styling present', /\.subcode-modal-overlay\s*\{[^}]*align-items:\s*flex-end/.test(html));

const i18nKeys = ['subcodeModalEyebrow', 'subcodeModalParentLabel', 'subcodeModalAbout', 'subcodeModalDocsTitle', 'subcodeModalProcTitle', 'subcodeModalWarnTitle', 'subcodeModalSourceTitle', 'subcodeModalNoDocs', 'subcodeModalSourceGap', 'subcodeModalParentCta', 'subcodeModalOpenAria'];
for (const loc of ['ko', 'en', 'zh-CN']) {
  const pack = JSON.parse(fs.readFileSync(path.join(repoRoot, 'data', 'i18n', loc + '.json'), 'utf8'));
  const missing = i18nKeys.filter(k => !(k in pack));
  check(`i18n keys present in ${loc}`, missing.length === 0, missing.join(','));
}

// ---- 2. Extract the pure builder + dependency and exercise every subcode ----
function extractFunction(src, name) {
  const re = new RegExp('function\\s+' + name + '\\s*\\(', 'g');
  const m = re.exec(src);
  if (!m) return '';
  const braceStart = src.indexOf('{', re.lastIndex);
  let depth = 0;
  for (let i = braceStart; i < src.length; i++) {
    if (src[i] === '{') depth++;
    else if (src[i] === '}') { depth--; if (depth === 0) return src.slice(m.index, i + 1); }
  }
  return '';
}

const buildSrc = extractFunction(html, 'buildSubcodeModalView');
const variantSrc = extractFunction(html, 'renderSubcodeProcedureVariants');
check('buildSubcodeModalView extractable', !!buildSrc);
check('renderSubcodeProcedureVariants extractable', !!variantSrc);

// Lightweight stubs for the builder's dependencies (the heavy renderers are
// covered by other checks; here we test the section-assembly logic itself).
function escapeHtml(s) { return String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#39;'); }
function tx(key, vars = {}) { let v = ko[key] != null ? ko[key] : key; if (typeof v === 'string') Object.entries(vars).forEach(([k, val]) => { v = v.split('{' + k + '}').join(val); }); return v; }
const normalizeVisaCode = c => String(c == null ? '' : c).trim().toUpperCase();
const getLocalizedSubcodeName = s => (s.nameKo || s.name || '');
const getLocalizedVisaName = v => (v.name || '');
const subcodeSourceChip = s => `<span class="subcode-chip">${s.needsManualReview === false ? 'official' : 'review'}</span>`;
const stripManualArtifacts = s => (s == null ? '' : String(s));
const paradisoStripInternalReviewArtifacts = s => (s == null ? '' : String(s));
function normalizeDocGroups(docValue, raw = {}, aliases = {}) {
  const g = { commonDocs: [], requiredDocs: [], additionalDocs: [], conditionalDocs: [] };
  if (docValue && typeof docValue === 'object' && !Array.isArray(docValue)) for (const k of Object.keys(g)) if (Array.isArray(docValue[k])) g[k] = docValue[k].slice();
  if (Array.isArray(raw.addReqDocs)) g.additionalDocs.push(...raw.addReqDocs);
  if (typeof raw.addReq === 'string' && raw.addReq.trim()) g.additionalDocs.push(raw.addReq);
  return g;
}
const flattenDocGroups = g => [...g.commonDocs, ...g.requiredDocs, ...g.additionalDocs, ...g.conditionalDocs].filter(Boolean);
const renderDocTags = (docs) => docs.length ? `<div class="doc-tags">${docs.map(d => `<span>${escapeHtml(typeof d === 'string' ? d : (d.label || d.name || ''))}</span>`).join('')}</div>` : '';
const renderDocGroupingSourceNote = () => '';
const getProcedureLabelByKey = (k) => k;

let buildSubcodeModalView, renderSubcodeProcedureVariants;
try {
  renderSubcodeProcedureVariants = eval('(' + variantSrc.replace(/^function\s+renderSubcodeProcedureVariants/, 'function') + ')');
  buildSubcodeModalView = eval('(' + buildSrc.replace(/^function\s+buildSubcodeModalView/, 'function') + ')');
} catch (e) {
  check('builder functions eval cleanly', false, e.message);
}

function getSubs(v) { return Array.isArray(v.subcodes) ? v.subcodes : (Array.isArray(v.subCodes) ? v.subCodes : []); }

if (typeof buildSubcodeModalView === 'function' && typeof renderSubcodeProcedureVariants === 'function') {
  let built = 0, leaks = 0, gapSource = 0, refSource = 0, variantRendered = 0, parentsWithSubs = 0;
  for (const v of visas) {
    const subs = getSubs(v);
    if (subs.length) parentsWithSubs++;
    for (const sub of subs) {
      if (!sub || !sub.code) continue;
      let view;
      try { view = buildSubcodeModalView(v, sub); }
      catch (e) { failures.push(`build threw for ${v.code}/${sub.code}: ${e.message}`); continue; }
      built++;
      const out = `${view.title} ${view.parentHtml} ${view.body}`;
      if (/undefined|\[object Object\]|\bNaN\b/.test(out)) { leaks++; failures.push(`raw value leak in ${v.code}/${sub.code}`); }
      // Required section hierarchy (docs + official basis always present).
      if (!view.body.includes(tx('subcodeModalDocsTitle'))) failures.push(`${v.code}/${sub.code} missing 추가서류 section`);
      if (!view.body.includes(tx('subcodeModalSourceTitle'))) failures.push(`${v.code}/${sub.code} missing 공식 근거 section`);
      // Parent CTA (links back to the parent status for shared docs/procedures).
      if (!view.body.includes(`data-query="${escapeHtml(v.code)}"`)) failures.push(`${v.code}/${sub.code} missing parent CTA`);
      // Header references the parent status code.
      if (!view.parentHtml.includes(escapeHtml(v.code))) failures.push(`${v.code}/${sub.code} header missing parent code`);
      if (view.body.includes(tx('subcodeModalSourceGap'))) gapSource++; else refSource++;
      if (renderSubcodeProcedureVariants(v, sub)) variantRendered++;
    }
  }
  check('built modal views for subcodes', built > 0, `built=${built}`);
  check('several parents carry subcodes', parentsWithSubs >= 10, `parentsWithSubs=${parentsWithSubs}`);
  check('no raw value leaks across all subcode modals', leaks === 0);
  check('honest source-gap copy used where refs are absent', gapSource > 0, `gapSource=${gapSource}`);
  check('at least one subcode renders real official references', refSource > 0, `refSource=${refSource}`);
  check('at least one subcode renders a procedure variant', variantRendered > 0, `variantRendered=${variantRendered}`);
  console.log(`[check_subcode_modal] exercised ${built} subcode modals across ${parentsWithSubs} parents (refs=${refSource}, source-gap=${gapSource}, variants=${variantRendered})`);
}

if (failures.length) {
  console.error('[check_subcode_modal] FAILED:');
  failures.forEach(f => console.error(' - ' + f));
  process.exit(1);
}
console.log('[check_subcode_modal] OK — subcode modal structure, wiring, a11y, i18n, and full-coverage builder all pass');
