#!/usr/bin/env node
/*
 * Form Helper 2.0 guard (offline, runs in `bash scripts/check_repo.sh`).
 *
 *  1. inventory / coverage: data/forms_inventory.json and the coverage doc are byte-fresh
 *     (python3 scripts/forms/build_forms_inventory.py --check), every 출국기한유예 and 난민
 *     annex is EXCLUDED and never mapped, no SUPPORTED form lacks a QA pass.
 *  2. template drift: each template PDF's sha256, page count and page size match the
 *     recorded template block (a replaced PDF fails here instead of being filled blindly).
 *  3. schema ↔ definitions: every field map and derived target resolves to an overlay key
 *     of the form's (edition) template; every overlay key is reachable from a field or a
 *     documented exception; sample fixtures cover every form.
 *  4. engine: fit / wrap / overflow / font / digits / conditions / derived / search.
 *  5. export: for every fillable form the Node export (pdf-lib + fontkit, the same vendor
 *     files the browser loads) is verified against the engine ops with PyMuPDF
 *     (scripts/forms/verify_export.py) — skipped with INFO when PyMuPDF is unavailable.
 *
 *  --record-qa  writes support.qa = PASS/FAIL (+ qaDate) into data/form_schemas.json.
 */
import fs from 'node:fs';
import path from 'node:path';
import { createRequire } from 'node:module';
import { execFileSync, spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const require = createRequire(import.meta.url);
const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const rd = (p) => fs.readFileSync(path.join(ROOT, p), 'utf8');
const E = require(path.join(ROOT, 'assets/js/form-engine.js'));
const schemas = JSON.parse(rd('data/form_schemas.json'));
const defs = JSON.parse(rd('data/form_definitions.json'));
const inventory = JSON.parse(rd('data/forms_inventory.json'));
const charset = JSON.parse(rd('assets/forms/fonts/NanumGothic-Regular.charset.json'));
const samples = JSON.parse(rd('tests/fixtures/form_field_samples.json'));
const overlaySamples = JSON.parse(rd('tests/fixtures/form_overlay_samples.json'));
const RECORD = process.argv.includes('--record-qa');

let checks = 0, failures = 0;
function ok(cond, msg) { checks++; if (!cond) { failures++; console.error('  FAIL ' + msg); } }
function info(msg) { console.log('  INFO ' + msg); }

/* ── 1. inventory / coverage ───────────────────────────────────────────── */
{
  const r = spawnSync('python3', [path.join(ROOT, 'scripts/forms/build_forms_inventory.py'), '--check'], { encoding: 'utf8' });
  ok(r.status === 0, 'inventory + coverage doc are fresh (build_forms_inventory.py --check): ' + (r.stdout || '').trim().split('\n').slice(-2).join(' | ') + (r.stderr || '').trim().slice(-300));
  const excludedNumbers = new Set();
  for (const it of inventory.inventory) {
    if (it.class === 'excluded_departure' || it.class === 'excluded_refugee') {
      excludedNumbers.add(it.number);
      ok(it.status === 'EXCLUDED', `${it.number} ${it.class} is EXCLUDED (got ${it.status})`);
      ok(!(it.visable_forms || []).length, `${it.number} has no Visable field map`);
    }
  }
  ok(excludedNumbers.has('44') && excludedNumbers.has('44의2'), '출국기한유예 annexes 44 / 44의2 are excluded');
  ok(['30의3', '30의4', '30의5'].every((n) => excludedNumbers.has(n)), '난민 annexes 30의3–30의5 are excluded');
  for (const [fid, spec] of Object.entries(schemas.forms)) {
    ok(!excludedNumbers.has(spec.support.annex), `${fid} does not map an excluded annex`);
    ok(!/난민|출국기한|출국기한유예|refugee/i.test(spec.nameKo + spec.nameEn), `${fid} is not a refugee / departure-deadline form`);
    if (spec.support.status === 'SUPPORTED') ok(spec.support.qa === 'PASS', `${fid} SUPPORTED requires qa PASS (got ${spec.support.qa})`);
    ok(['SUPPORTED', 'PARTIAL', 'BLOCKED'].includes(spec.support.status), `${fid} status is a known value`);
  }
  ok(inventory.supported_now.every((f) => schemas.forms[f] && schemas.forms[f].support.status === 'SUPPORTED'), 'inventory supported_now matches schema statuses');
  const doc = rd('docs/forms_official/FORM_HELPER_COVERAGE_20260923.md');
  for (const h of ['SUPPORTED BEFORE', 'NEWLY SUPPORTED', "FULLY QA'D", 'PARTIAL', 'BLOCKED', 'EXCLUDED — DEPARTURE DEADLINE', 'EXCLUDED — REFUGEE', 'STALE', 'UNKNOWN']) ok(doc.includes(h), `coverage doc has the ${h} row`);
}

/* ── 2. template drift ─────────────────────────────────────────────────── */
const PDFLib = require(path.join(ROOT, 'assets/forms/vendor/pdf-lib.min.js'));
const fontkit = require(path.join(ROOT, 'assets/forms/vendor/fontkit.umd.min.js'));
const crypto = await import('node:crypto');
for (const [fid, spec] of Object.entries(schemas.forms)) {
  const bytes = fs.readFileSync(path.join(ROOT, spec.pdf));
  const sha = crypto.createHash('sha256').update(bytes).digest('hex');
  ok(sha === spec.template.sha256, `${fid} template sha256 matches (${sha.slice(0, 12)} vs ${String(spec.template.sha256).slice(0, 12)})`);
  ok(bytes.length === spec.template.bytes, `${fid} template byte size matches`);
  const doc = await PDFLib.PDFDocument.load(bytes, { updateMetadata: false });
  ok(doc.getPageCount() === spec.template.pages && spec.pages === spec.template.pages, `${fid} page count ${doc.getPageCount()} matches template (${spec.template.pages})`);
  const p0 = doc.getPage(0).getSize();
  ok(Math.round(p0.width) === spec.pageWidth && Math.round(p0.height) === spec.pageHeight, `${fid} page size ${p0.width}x${p0.height} matches`);
  for (const o of Object.values(spec.overlay)) {
    ok((o.page || 0) < spec.pages, `${fid} overlay page index in range`);
    if (o.check) ok(o.cx > 0 && o.cx < spec.pageWidth && o.cy > 0 && o.cy < spec.pageHeight, `${fid} check inside page`);
    else ok(o.x >= 0 && o.x + (o.maxWidth || 0) <= spec.pageWidth + 0.01 && o.y > 0 && o.y < spec.pageHeight, `${fid} text cell inside page`);
  }
  ok(spec.template.verification && spec.template.fieldMapVersion && spec.template.revisionOnForm, `${fid} template block is complete`);
}

/* ── 3. schema ↔ definitions ───────────────────────────────────────────── */
const KNOWN_UNDRIVEN = { F07: ['app_hanja', 'g_hanja'] }; // 漢字 cells: no CJK glyphs in the embedded font
for (const [fid, f] of Object.entries(defs.forms)) {
  const editions = (f.editions || [{ v: f.schema }]).map((e) => e.v);
  ok(editions.every((e) => schemas.forms[e]), `${fid} editions exist in schemas`);
  const keys = new Set(); for (const e of editions) Object.keys(schemas.forms[e].overlay).forEach((k) => keys.add(k));
  const used = new Set();
  const useMap = (m) => { if (!m) return; if (typeof m === 'string') used.add(m); else { if (m.dot) used.add(m.dot); if (m.digits) used.add(m.digits); (m.ymd || []).forEach((k) => used.add(k)); } };
  for (const fl of f.fields) { useMap(fl.map); (fl.options || []).forEach((o) => { if (o.map) used.add(o.map); }); }
  for (const d of f.derived || []) used.add(d.target);
  for (const u of used) ok(keys.has(u), `${fid} map target ${u} exists in overlay`);
  const undriven = [...keys].filter((k) => !used.has(k) && !(KNOWN_UNDRIVEN[fid] || []).includes(k));
  ok(!undriven.length, `${fid} every overlay key is driven by a field (${undriven.join(',')})`);
  ok(f.steps.length >= 2 && f.fields.length >= 5, `${fid} has steps and fields`);
  ok(f.name && f.name.ko && f.name.en && f.summary && f.who && f.where && f.attachments, `${fid} has KO/EN explain copy`);
  ok(Array.isArray(f.search.ko) && f.search.ko.length >= 3 && Array.isArray(f.search.en) && f.search.en.length >= 2, `${fid} has search terms`);
  ok(samples[fid], `${fid} has a field-level sample fixture`);
  const stepIds = new Set(f.steps.map((s) => s.id));
  for (const fl of f.fields) ok(stepIds.has(fl.step), `${fid}.${fl.key} step ${fl.step} exists`);
  const keysSeen = new Set(); for (const fl of f.fields) { ok(!keysSeen.has(fl.key), `${fid} duplicate field key ${fl.key}`); keysSeen.add(fl.key); }
}
for (const fid of Object.keys(schemas.forms)) {
  const fillable = Object.values(defs.forms).some((f) => f.schema === fid || (f.editions || []).some((e) => e.v === fid));
  ok(fillable || schemas.forms[fid].support.status === 'BLOCKED', `${fid} schema is used by a definition (or BLOCKED)`);
}
// i18n packs carry the fh chrome
for (const loc of ['ko', 'en', 'zh-CN', 'ja', 'vi', 'tl', 'id', 'ru', 'fr', 'es', 'ar', 'de', 'tr', 'uk']) {
  const p = JSON.parse(rd(`data/i18n/${loc}.json`));
  ok(p.fh && p.fh.title && p.fh.handoffTitle && p.fh.fitOverflow, `${loc} pack has fh chrome strings`);
}

/* ── 4. engine unit tests ──────────────────────────────────────────────── */
const font = fontkit.create(fs.readFileSync(path.join(ROOT, 'assets/forms/fonts/NanumGothic-Regular.ttf')));
const measure = (t, s) => font.layout(t).advanceWidth * s / font.unitsPerEm;
const glyphs = E.makeGlyphChecker(charset);
{
  const fit = E.fitSingle('REPUBLIC OF THE PHILIPPINES', 9, 60, measure);
  ok(fit.size === E.MIN_SIZE && fit.overflow && fit.lines[0].length < 'REPUBLIC OF THE PHILIPPINES'.length, 'single-line text shrinks to the 6.5pt floor then clips + flags overflow');
  ok(measure(fit.lines[0], fit.size) <= 60, 'clipped text never exceeds the cell');
  const short = E.fitSingle('KIM', 9, 60, measure); ok(short.size === 9 && !short.overflow, 'short text keeps its size');
  const wrapped = E.fitMulti('경기도 수원시 영통구 광교로 145, 광교아파트 102동 1502호 (이의동)', 9, 200, 3, measure);
  ok(!wrapped.overflow && wrapped.lines.length >= 2 && wrapped.lines.every((l) => measure(l, wrapped.size) <= 200), 'multi-line text wraps within the cell');
  const over = E.fitMulti('가'.repeat(400), 9, 200, 3, measure); ok(over.overflow && over.lines.length === 3, 'multi-line overflow keeps the allowed lines and flags');
  ok(glyphs('ⓐ③').length === 2 && glyphs('한글 ABC 123').length === 0, 'glyph checker flags circled glyphs and accepts Hangul/Latin');
  const lay = E.layout(schemas.forms.F08, { name: 'NGUYEN VAN ANH', arc_no: '980123-1234567', sex_f: true, new_address: '경기도 수원시 영통구 광교로 145' }, measure, glyphs, {});
  ok(lay.ops.filter((o) => o.key === 'arc_no').length === 13, 'a 13-digit registration number lands in 13 cells');
  ok(lay.ops.some((o) => o.type === 'check' && o.key === 'sex_f'), 'a boolean value becomes a tick op');
  ok(lay.issues.length === 0, 'well-formed values raise no fit issues');
  const lay2 = E.layout(schemas.forms.F14, { w1_sub: '③' }, measure, glyphs, {});
  ok(lay2.ops.length === 0 && lay2.issues[0].kind === 'FONT', 'a glyph outside the font is left blank and flagged FONT');
  const f01 = defs.forms.F01; const v = E.initialValues(f01);
  ok(E.visibleSteps(f01, v).map((s) => s.id).join(',') === 'type,person,contact,sign', 'F01 conditional steps hidden until a type is chosen');
  v.app_type = 'address_change'; v.new_address = 'A'; v.korean_address = 'B';
  ok(E.overlayValues(f01, v).addr_korea === 'A', 'address change maps the NEW address into the official address cell');
  ok(E.visibleFields(f01, v, 'contact').some((x) => x.key === 'new_address') && !E.visibleFields(f01, v, 'contact').some((x) => x.key === 'korean_address'), 'address-change shows the new-address field only');
  v.app_type = 'status_change'; v.desired_status = 'E-7-1';
  ok(E.overlayValues(f01, v).change_status === 'E-7-1' && !E.overlayValues(f01, v).grant_status, 'desired status goes to the change cell only');
  v.edition = 'F03'; ok(E.editionOf(f01, v) === 'F03', 'edition switch selects the Chinese template'); v.edition = 'F01';
  const val = E.validate(f01, v, 'ko', (k, vars) => k + ':' + (vars && vars.label));
  ok(val.some((i) => i.code === 'required' && i.key === 'surname'), 'required fields are reported');
  const f08 = defs.forms.F08; const v8 = E.initialValues(f08); Object.assign(v8, { name: 'A', sex: 'F', nationality: 'X', arc_no: '980123-1234567', new_address: 'Y', res_type: 'rent' });
  ok(E.validate(f08, v8, 'ko', (k) => k).length === 0, 'fields of a hidden step (위임장) are neither validated nor required');
  ok(!('poa_y' in E.overlayValues(f08, v8)), 'fields of a hidden step are not printed');
  v8.use_poa = 'yes';
  ok(E.validate(f08, v8, 'ko', (k) => k).some((i) => i.key === 'agent_name'), 'once the step is shown its required fields are enforced');
  const idx = E.buildSearchIndex(defs, inventory, 'ko');
  const top = (q) => (E.search(idx, q, 3)[0] || {}).entry?.id;
  ok(top('통합신청서') === 'F01' && top('주소 변경') === 'F08' && top('숙소 제공') === 'F06' && top('신원보증') === 'F07' && top('F-4 거소신고') === 'F04', 'search examples from the brief resolve to the intended forms');
  const ref = E.search(idx, '난민', 8).map((r) => r.entry);
  ok(ref.length && ref.every((e) => e.kind === 'catalog') && ref.some((e) => e.status === 'EXCLUDED') && !ref.some((e) => e.status === 'FILLABLE'), 'refugee forms are never fillable: only catalog entries (excluded / official-use) match');
  const dep = E.search(idx, '출국기한유예', 8).map((r) => r.entry);
  ok(dep.length && dep.every((e) => e.kind === 'catalog') && dep.some((e) => e.status === 'EXCLUDED') && !dep.some((e) => e.status === 'FILLABLE'), 'departure-deadline forms are never fillable: only catalog entries match');
  ok(E.normalizeValue({ type: 'arc' }, '980123 1234567') === '980123-1234567' && E.normalizeValue({ type: 'upper', maxLen: 4 }, 'abcdef') === 'ABCD', 'value normalisation (arc hyphen, upper-case, maxLen)');
  ok(E.filename(defs.forms.F08, { name: 'NGUYEN VAN ANH' }, 'F08', 'ko') === 'NGUYEN VAN ANH_체류지변경신고서.pdf', 'download filename');
}

/* ── 5. Node export + PyMuPDF verification for every fillable form ─────── */
const OUT = path.join(ROOT, 'artifacts/form-helper-qa/node-export');
fs.mkdirSync(OUT, { recursive: true });
const fontBytes = fs.readFileSync(path.join(ROOT, 'assets/forms/fonts/NanumGothic-Regular.ttf'));
const py = spawnSync('python3', ['-c', 'import pymupdf'], { encoding: 'utf8' });
const HAVE_PYMUPDF = py.status === 0;
const qaResult = {};
async function exportForm(fid, sampleKey) {
  const f = defs.forms[fid]; const values = E.initialValues(f);
  for (const [k, val] of Object.entries(samples[sampleKey])) { const fd = f.fields.find((x) => x.key === k); values[k] = fd ? E.normalizeValue(fd, val) : val; }
  const ed = E.editionOf(f, values); const spec = schemas.forms[ed];
  const issues = E.validate(f, values, 'ko', (k) => k).filter((i) => i.level === 'error');
  ok(!issues.length, `${sampleKey}: sample fills every required field (${issues.map((i) => i.key).join(',')})`);
  const lay = E.layout(spec, E.overlayValues(f, values), measure, glyphs, {});
  ok(!lay.issues.some((i) => i.kind === 'OVERFLOW' || i.kind === 'FONT'), `${sampleKey}: sample values fit their cells (${lay.issues.map((i) => i.kind + ':' + i.key).join(',')})`);
  const doc = await PDFLib.PDFDocument.load(fs.readFileSync(path.join(ROOT, spec.pdf)));
  doc.registerFontkit(fontkit);
  const pfont = await doc.embedFont(fontBytes);
  const pages = doc.getPages(); const H = spec.pageHeight;
  const ink = PDFLib.rgb(spec.ink[0] / 255, spec.ink[1] / 255, spec.ink[2] / 255);
  for (const op of lay.ops) {
    const page = pages[op.page];
    if (op.type === 'rect') page.drawRectangle({ x: op.x0, y: H - op.y1, width: op.x1 - op.x0, height: op.y1 - op.y0, color: PDFLib.rgb(1, 1, 1) });
    else if (op.type === 'check') {
      const cx = op.cx, cy = H - op.cy, s = op.s;
      page.drawLine({ start: { x: cx - 0.45 * s, y: cy + 0.02 * s }, end: { x: cx - 0.12 * s, y: cy - 0.38 * s }, thickness: 1.1, color: ink });
      page.drawLine({ start: { x: cx - 0.12 * s, y: cy - 0.38 * s }, end: { x: cx + 0.55 * s, y: cy + 0.5 * s }, thickness: 1.1, color: ink });
    } else page.drawText(op.text, { x: op.x, y: H - op.y, size: op.size, font: pfont, color: ink });
  }
  const bytes = await doc.save();
  const pdfPath = path.join(OUT, `${sampleKey}.pdf`); const opsPath = path.join(OUT, `${sampleKey}-ops.json`);
  fs.writeFileSync(pdfPath, bytes); fs.writeFileSync(opsPath, JSON.stringify({ form: fid, edition: ed, ops: lay.ops }));
  ok(lay.ops.length >= 8, `${sampleKey}: export draws ${lay.ops.length} ops`);
  if (HAVE_PYMUPDF) {
    const r = spawnSync('python3', [path.join(ROOT, 'scripts/forms/verify_export.py'), pdfPath, opsPath], { encoding: 'utf8' });
    const pass = r.status === 0;
    ok(pass, `${sampleKey}: PyMuPDF verification of the export (${(r.stdout || '').trim().split('\n').slice(-3).join(' | ')})`);
    qaResult[ed] = (qaResult[ed] === false) ? false : pass; if (ed !== fid) qaResult[fid] = (qaResult[fid] === false) ? false : pass;
  }
  return lay;
}
for (const sampleKey of Object.keys(samples).filter((k) => !k.startsWith('_'))) {
  const fid = sampleKey.split('_')[0];
  ok(!!defs.forms[fid], `sample ${sampleKey} refers to a defined form`);
  if (defs.forms[fid]) await exportForm(fid, sampleKey);
}
// the overlay-level samples (authoring fixture) must also fit
for (const [fid, vals] of Object.entries(overlaySamples)) {
  if (fid.startsWith('_')) continue;
  const lay = E.layout(schemas.forms[fid], vals, measure, glyphs, {});
  const bad = lay.issues.filter((i) => i.kind === 'FONT');
  ok(!bad.length, `${fid} overlay sample has no FONT issues (${bad.map((b) => b.key).join(',')})`);
}
if (!HAVE_PYMUPDF) info('PyMuPDF not importable — export geometry verification skipped (run locally: pip install pymupdf)');

if (RECORD && HAVE_PYMUPDF) {
  const today = new Date().toISOString().slice(0, 10);
  for (const [fid, spec] of Object.entries(schemas.forms)) {
    if (qaResult[fid] === undefined) continue;
    spec.support.qa = qaResult[fid] ? 'PASS' : 'FAIL'; spec.support.qaDate = today; spec.support.qaMethod = 'node export (pdf-lib + fontkit) verified with PyMuPDF against engine ops; browser E2E on F08/F01';
  }
  fs.writeFileSync(path.join(ROOT, 'data/form_schemas.json'), JSON.stringify(schemas, null, 2) + '\n');
  info('recorded qa results into data/form_schemas.json: ' + JSON.stringify(qaResult));
}

if (failures) { console.error(`[check_form_helper] ${failures} of ${checks} checks failed`); process.exit(1); }
console.log(`[check_form_helper] OK — ${checks} checks passed (${Object.keys(samples).filter((k) => !k.startsWith('_')).length} sample exports, PyMuPDF ${HAVE_PYMUPDF ? 'verified' : 'skipped'})`);
