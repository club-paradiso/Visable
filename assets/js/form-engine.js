/*
 * Visable Form Helper 2.0 — form engine (no DOM, runs in the browser and in Node).
 *
 * One data model drives the editor, the preview and the PDF export:
 *   data/form_definitions.json  → steps, fields, conditions, mapping, validation, search
 *   data/form_schemas.json      → official template (sha256, pages, size) + overlay coordinates
 *
 * The engine turns field values into overlay values (overlayValues), and overlay
 * values into drawing operations (layout). Both the canvas preview and the pdf-lib
 * export consume the same operations, so what the user sees is what is exported.
 *
 * Text fitting policy (§36 of the sprint brief): a value is drawn at the declared
 * size; when it does not fit the printed cell it is reduced in 0.5 pt steps down
 * to MIN_SIZE (6.5 pt, still legible when printed); cells declared with lines > 1
 * wrap instead; anything that still does not fit is CLIPPED to the cell and flagged
 * as OVERFLOW so the user is warned before export. Nothing is ever drawn outside
 * its cell. Characters missing from the embedded font are never drawn silently:
 * the whole value is left blank and flagged as FONT.
 */
(function (root, factory) {
  if (typeof module === 'object' && module.exports) module.exports = factory();
  else root.VisableFormEngine = factory();
}(typeof self !== 'undefined' ? self : this, function () {
  'use strict';

  var MIN_SIZE = 6.5;
  var SHRINK_STEP = 0.5;
  var SAFETY = 0.985; // canvas vs. pdf font metrics differ by a hair; keep text inside the cell

  /* ── small helpers ─────────────────────────────────────────────────────── */
  function isEmpty(v) { return v === undefined || v === null || v === '' || v === false || (Array.isArray(v) && !v.length); }
  function todayIso() { var d = new Date(); var p = function (n) { return (n < 10 ? '0' : '') + n; }; return d.getFullYear() + '-' + p(d.getMonth() + 1) + '-' + p(d.getDate()); }
  function splitDate(iso) { var m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(String(iso || '')); return m ? { y: m[1], m: m[2], d: m[3] } : { y: '', m: '', d: '' }; }
  function dateDot(iso) { var d = splitDate(iso); return d.y ? d.y + '.' + d.m + '.' + d.d : String(iso || ''); }
  function digitsOnly(v) { return String(v == null ? '' : v).replace(/\D+/g, ''); }
  function pick(obj, lang) {
    if (obj == null) return '';
    if (typeof obj !== 'object') return String(obj);
    return obj[lang] || obj.en || obj.ko || '';
  }

  /* ── condition DSL: {field, eq|in|gte|empty|truthy} | {any:[]} | {all:[]} | {not:{}} ── */
  function evalCond(cond, values) {
    if (!cond) return true;
    if (cond.any) return cond.any.some(function (c) { return evalCond(c, values); });
    if (cond.all) return cond.all.every(function (c) { return evalCond(c, values); });
    if (cond.not) return !evalCond(cond.not, values);
    var v = values[cond.field];
    if (Object.prototype.hasOwnProperty.call(cond, 'eq')) return v === cond.eq || String(v) === String(cond.eq);
    if (cond['in']) return cond['in'].some(function (x) { return v === x || String(v) === String(x); });
    if (Object.prototype.hasOwnProperty.call(cond, 'gte')) return Number(v) >= Number(cond.gte);
    if (Object.prototype.hasOwnProperty.call(cond, 'empty')) return isEmpty(v) === !!cond.empty;
    if (Object.prototype.hasOwnProperty.call(cond, 'truthy')) return !!v === !!cond.truthy;
    return true;
  }

  /* ── model ──────────────────────────────────────────────────────────────── */
  function initialValues(form) {
    var values = {};
    form.fields.forEach(function (f) {
      if (f.type === 'note') return;
      var d = f['default'];
      if (d === 'today') values[f.key] = todayIso();
      else if (d !== undefined) values[f.key] = d;
      else if (f.type === 'yesno') values[f.key] = false;
      else values[f.key] = '';
    });
    return values;
  }
  // a field is live only when its own condition AND its step's condition hold (a hidden
  // step never validates, prints or counts its fields)
  function stepCondOk(form, stepId, values) {
    if (!form) return true;
    var step = form.steps.filter(function (s) { return s.id === stepId; })[0];
    return step ? evalCond(step.showIf, values) : true;
  }
  function fieldVisible(f, values, form) { return evalCond(f.showIf, values) && stepCondOk(form, f.step, values); }
  function stepVisible(form, step, values) {
    if (!evalCond(step.showIf, values)) return false;
    return form.fields.some(function (f) { return f.step === step.id && evalCond(f.showIf, values); });
  }
  function visibleSteps(form, values) { return form.steps.filter(function (s) { return stepVisible(form, s, values); }); }
  function visibleFields(form, values, stepId) {
    return form.fields.filter(function (f) { return (!stepId || f.step === stepId) && fieldVisible(f, values, form); });
  }
  function isRequired(f, values) { return f.reqIf ? evalCond(f.reqIf, values) : !!f.req; }
  function editionOf(form, values) {
    var ef = form.fields.filter(function (f) { return f.role === 'edition'; })[0];
    var v = ef ? values[ef.key] : null;
    if (v && form.editions && form.editions.some(function (e) { return e.v === v; })) return v;
    return form.editions && form.editions.length ? form.editions[0].v : form.schema;
  }

  /* ── normalisation of typed values ────────────────────────────────────── */
  function normalizeValue(f, raw) {
    if (raw == null) return '';
    if (f.type === 'yesno') return !!raw;
    if (f.type === 'choice') return raw;
    var s = String(raw);
    if (f.type === 'upper') s = s.toUpperCase();
    if (f.type === 'arc') { s = digitsOnly(s).slice(0, 13); if (s.length === 13) s = s.slice(0, 6) + '-' + s.slice(6); }
    if (f.type === 'number') s = s.replace(/[^\d]/g, '');
    if (f.type === 'phone') s = s.replace(/[^\d+\-() ]/g, '');
    if (f.maxLen && f.type !== 'textarea') s = s.slice(0, f.maxLen);
    if (f.maxLen && f.type === 'textarea') s = s.slice(0, f.maxLen);
    return s;
  }

  /* ── validation ──────────────────────────────────────────────────────── */
  function validate(form, values, lang, tr) {
    tr = tr || function (k, vars) { return k + (vars ? ' ' + JSON.stringify(vars) : ''); };
    var issues = [];
    form.fields.forEach(function (f) {
      if (f.type === 'note' || !fieldVisible(f, values, form)) return;
      var v = values[f.key];
      if (isRequired(f, values) && isEmpty(v)) {
        issues.push({ level: 'error', key: f.key, step: f.step, code: 'required', msg: tr('validationRequired', { label: pick(f.label, lang) }) });
        return;
      }
      if (isEmpty(v)) return;
      if (f.type === 'arc' && digitsOnly(v).length !== 13) issues.push({ level: 'warn', key: f.key, step: f.step, code: 'arc', msg: tr('validationArc', { label: pick(f.label, lang) }) });
      if (f.type === 'email' && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(String(v))) issues.push({ level: 'warn', key: f.key, step: f.step, code: 'email', msg: tr('validationEmail', { label: pick(f.label, lang) }) });
      if (f.type === 'date' && !/^\d{4}-\d{2}-\d{2}$/.test(String(v))) issues.push({ level: 'error', key: f.key, step: f.step, code: 'date', msg: tr('validationDate', { label: pick(f.label, lang) }) });
    });
    (form.validation || []).forEach(function (rule) {
      if (rule.kind === 'dateOrder') {
        var a = values[rule.before], b = values[rule.after];
        if (a && b && /^\d{4}-\d{2}-\d{2}$/.test(a) && /^\d{4}-\d{2}-\d{2}$/.test(b) && b < a) issues.push({ level: rule.level || 'warn', key: rule.after, step: fieldStep(form, rule.after), code: 'dateOrder', msg: pick(rule.msg, lang) });
      } else if (rule.kind === 'anyOf') {
        if (!rule.fields.some(function (k) { return !isEmpty(values[k]); })) issues.push({ level: rule.level || 'error', key: rule.fields[0], step: fieldStep(form, rule.fields[0]), code: 'anyOf', msg: pick(rule.msg, lang) });
      }
    });
    return issues;
  }
  function fieldStep(form, key) { var f = form.fields.filter(function (x) { return x.key === key; })[0]; return f ? f.step : null; }

  /* ── field values → overlay values ───────────────────────────────────── */
  function overlayValues(form, values) {
    var out = {};
    var byKey = {};
    form.fields.forEach(function (f) { byKey[f.key] = f; });
    form.fields.forEach(function (f) {
      if (f.type === 'note' || !fieldVisible(f, values, form)) return;
      var v = values[f.key];
      if (f.type === 'choice') {
        (f.options || []).forEach(function (o) {
          if (isEmpty(v) || !(o.v === v || String(o.v) === String(v))) return;
          if (o.map) out[o.map] = true;
          if (o.text != null && f.map) writeMap(out, f.map, o.text);
        });
        return;
      }
      if (f.type === 'yesno') { if (v && typeof f.map === 'string') out[f.map] = true; return; }
      if (isEmpty(v) || !f.map) return;
      writeMap(out, f.map, v);
    });
    (form.derived || []).forEach(function (rule) {
      var apply = rule.when ? evalCond(rule.when, values) : true;
      var val;
      if (apply) {
        if (rule.fromOverlay) val = out[rule.fromOverlay];
        else if (rule.from) val = values[rule.from];
        else if (rule.const !== undefined) val = rule.const;
      } else if (rule['else']) val = values[rule['else']];
      else if (rule.elseMap) val = rule.elseMap.values[values[rule.elseMap.field]];
      if (val === undefined || val === null || val === '' || val === false) { if (!apply && rule.fromOverlay) delete out[rule.target]; return; }
      var src = rule.from ? byKey[rule.from] : null;
      out[rule.target] = (src && src.type === 'date') ? dateDot(val) : val;
    });
    return out;
  }
  function writeMap(out, map, v) {
    if (typeof map === 'string') { out[map] = String(v); return; }
    if (map.dot) { out[map.dot] = dateDot(v); return; }
    if (map.ymd) { var d = splitDate(v); out[map.ymd[0]] = d.y; out[map.ymd[1]] = d.m; out[map.ymd[2]] = d.d; return; }
    if (map.digits) { out[map.digits] = String(v); return; }
  }

  /* ── glyph coverage ───────────────────────────────────────────────────── */
  function makeGlyphChecker(charset) {
    var ranges = (charset && charset.ranges) || [];
    return function (text) {
      var bad = [];
      for (var i = 0; i < text.length; i++) {
        var cp = text.codePointAt(i);
        if (cp > 0xffff) i++;
        if (cp === 10 || cp === 13 || cp === 9) continue;
        var ok = false;
        for (var r = 0; r < ranges.length; r++) { if (cp >= ranges[r][0] && cp <= ranges[r][1]) { ok = true; break; } }
        if (!ok) { var ch = String.fromCodePoint(cp); if (bad.indexOf(ch) < 0) bad.push(ch); }
      }
      return bad;
    };
  }

  /* ── text fitting ────────────────────────────────────────────────────── */
  function fitSingle(text, size, maxWidth, measure) {
    var s = size;
    while (s > MIN_SIZE && measure(text, s) > maxWidth) s = Math.round((s - SHRINK_STEP) * 100) / 100;
    if (s < MIN_SIZE) s = MIN_SIZE;
    if (measure(text, s) <= maxWidth) return { size: s, lines: [text], overflow: false };
    var kept = text;
    while (kept.length && measure(kept, s) > maxWidth) kept = kept.slice(0, -1);
    return { size: s, lines: [kept], overflow: true, dropped: text.slice(kept.length) };
  }
  function wrapAt(text, size, maxWidth, measure) {
    var lines = [], words = text.split(/(\s+)/), cur = '';
    function pushWord(w) {
      if (!w) return;
      if (measure(cur + w, size) <= maxWidth) { cur += w; return; }
      if (/^\s+$/.test(w)) { return; }
      if (cur) { lines.push(cur.replace(/\s+$/, '')); cur = ''; }
      if (measure(w, size) <= maxWidth) { cur = w; return; }
      // a single word longer than the cell: break by character
      for (var i = 0; i < w.length; i++) {
        var ch = w[i];
        if (measure(cur + ch, size) > maxWidth && cur) { lines.push(cur); cur = ch; } else cur += ch;
      }
    }
    for (var i = 0; i < words.length; i++) pushWord(words[i]);
    if (cur) lines.push(cur.replace(/\s+$/, ''));
    return lines;
  }
  function fitMulti(text, size, maxWidth, maxLines, measure) {
    var s = size;
    for (;;) {
      var lines = wrapAt(text, s, maxWidth, measure);
      if (lines.length <= maxLines) return { size: s, lines: lines, overflow: false };
      if (s - SHRINK_STEP < MIN_SIZE) {
        var kept = lines.slice(0, maxLines);
        return { size: s, lines: kept, overflow: true, dropped: lines.slice(maxLines).join(' ') };
      }
      s = Math.round((s - SHRINK_STEP) * 100) / 100;
    }
  }

  /* ── overlay values → drawing ops ──────────────────────────────────────
   * spec: form_schemas.json entry; values: overlay key → value; measure(text,size) → width (pt);
   * glyphs(text) → [missing chars]. Returns { ops, issues } where
   *   ops: [{type:'text', page, key, x, y, size, text, w, h, align}, {type:'check', page, key, cx, cy, s}, {type:'rect', page, key, x0,y0,x1,y1}]
   *   issues: [{kind:'OVERFLOW'|'FONT'|'SHRUNK', key, chars?, dropped?, size?}]
   */
  function layout(spec, values, measure, glyphs, labels) {
    var ops = [], issues = [];
    var overlay = spec.overlay || {};
    Object.keys(values).forEach(function (key) {
      var o = overlay[key], val = values[key];
      if (!o || val === '' || val == null || val === false) return;
      var page = o.page || 0;
      if (o.check) { ops.push({ type: 'check', page: page, key: key, cx: o.cx, cy: o.cy, s: o.s || 5 }); return; }
      var text = String(val).replace(/\r?\n+/g, ' ').trim();
      if (!text) return;
      if (o.wbox) ops.push({ type: 'rect', page: page, key: key, x0: o.wbox[0], y0: o.wbox[1], x1: o.wbox[2], y1: o.wbox[3] });
      var missing = glyphs ? glyphs(text) : [];
      if (missing.length) { issues.push({ kind: 'FONT', key: key, chars: missing, label: labels ? labels[key] : key }); return; }
      if (o.digits && Array.isArray(o.digits.cells)) {
        var ds = digitsOnly(text);
        if (ds.length === o.digits.cells.length) {
          var dsize = o.digits.size || 10;
          for (var i = 0; i < ds.length; i++) {
            var w = measure(ds[i], dsize);
            ops.push({ type: 'text', page: page, key: key, x: o.digits.cells[i] - w / 2, y: o.digits.y, size: dsize, text: ds[i], w: w, h: dsize, cell: i });
          }
          return;
        }
      }
      var size = o.size || 9;
      var maxWidth = (o.maxWidth || (spec.pageWidth - o.x - 6)) * SAFETY;
      var lines = o.lines || 1;
      var fit = lines > 1 ? fitMulti(text, size, maxWidth, lines, measure) : fitSingle(text, size, maxWidth, measure);
      var lh = o.lineHeight || fit.size * 1.2;
      fit.lines.forEach(function (ln, idx) {
        var w = measure(ln, fit.size);
        var x = o.align === 'center' ? o.x - w / 2 : o.x;
        ops.push({ type: 'text', page: page, key: key, x: x, y: o.y + idx * lh, size: fit.size, text: ln, w: w, h: fit.size, line: idx, maxWidth: o.maxWidth || null, overflow: !!fit.overflow });
      });
      if (fit.overflow) issues.push({ kind: 'OVERFLOW', key: key, dropped: fit.dropped || '', size: fit.size, label: labels ? labels[key] : key });
      else if (fit.size <= 7 && fit.size < size) issues.push({ kind: 'SHRUNK', key: key, size: fit.size, label: labels ? labels[key] : key });
    });
    return { ops: ops, issues: issues };
  }

  /* map overlay key → the editor field that produced it (for issue links / highlights) */
  function overlayToField(form) {
    var m = {};
    form.fields.forEach(function (f) {
      var add = function (k) { if (k && !m[k]) m[k] = f.key; };
      if (typeof f.map === 'string') add(f.map);
      else if (f.map) { add(f.map.dot); add(f.map.digits); (f.map.ymd || []).forEach(add); }
      (f.options || []).forEach(function (o) { add(o.map); });
    });
    (form.derived || []).forEach(function (r) { if (r.from && !m[r.target]) m[r.target] = r.from; else if (r.fromOverlay && m[r.fromOverlay] && !m[r.target]) m[r.target] = m[r.fromOverlay]; });
    return m;
  }

  /* ── search ───────────────────────────────────────────────────────────── */
  function norm(s) {
    return String(s || '').toLowerCase().replace(/[\s\-_·ㆍ.,()/]+/g, '').replace(/제(\d+)호(의\d+)?서식/g, '$1$2').replace(/별지/g, '');
  }
  function buildSearchIndex(definitions, inventory, lang) {
    var entries = [];
    Object.keys(definitions.forms).forEach(function (fid) {
      var f = definitions.forms[fid];
      var terms = [].concat(pick(f.name, 'ko'), pick(f.name, 'en'), pick(f.short, 'ko'), pick(f.short, 'en'), pick(f.number, 'ko'), pick(f.number, 'en'), (f.search && f.search.ko) || [], (f.search && f.search.en) || [], f.procedures || [], fid);
      if (f.editions) f.editions.forEach(function (e) { terms.push(e.v); terms.push(pick(e.label, 'ko')); });
      var primary = ((f.search && f.search.primary) || []).map(norm);
      entries.push({ kind: 'form', id: fid, form: f, status: 'FILLABLE', terms: terms.map(norm).filter(Boolean), primary: primary, title: pick(f.name, lang), sub: pick(f.number, lang) });
    });
    var covered = {};
    Object.keys(definitions.forms).forEach(function (fid) { var f = definitions.forms[fid]; covered[f.schema] = true; (f.editions || []).forEach(function (e) { covered[e.v] = true; }); });
    ((inventory && inventory.inventory) || []).forEach(function (it) {
      if (it['class'] === 'deleted') return;
      var fillable = (it.visable_forms || []).some(function (v) { return covered[v]; });
      if (fillable) return;
      var terms = [it.title, it.number, '별지 제' + it.number + '호서식', it['class'], it.status].map(norm).filter(Boolean);
      entries.push({ kind: 'catalog', id: it.source + ':' + it.number, item: it, status: it.status || it['class'], terms: terms, title: it.title, sub: '별지 제' + it.number + '호서식' + (it.revision ? ' · ' + it.revision : '') });
    });
    return entries;
  }
  function search(index, query, limit) {
    var q = norm(query);
    if (!q) return [];
    var alt = q.replace(/^f(\d)/, 'f-$1');
    var scored = [];
    index.forEach(function (e) {
      var best = 0;
      e.terms.forEach(function (t) {
        var s = 0;
        if (t === q || t === alt) s = 100;
        else if (t.indexOf(q) === 0) s = 80;
        else if (t.indexOf(q) >= 0) s = 60;
        else if (q.length >= 2 && q.indexOf(t) >= 0 && t.length >= 2) s = 40;
        if (s && e.primary && e.primary.indexOf(t) >= 0) s += 10; // the form's own primary tasks outrank aliases shared with other forms
        if (s > best) best = s;
      });
      if (best) scored.push({ score: best + (e.kind === 'form' ? 5 : 0) + (e.form && e.form.featured ? 2 : 0), entry: e });
    });
    scored.sort(function (a, b) { return b.score - a.score; });
    return scored.slice(0, limit || 12);
  }

  /* ── output naming ────────────────────────────────────────────────────── */
  function filename(form, values, editionId, lang) {
    var nm = (form.output && form.output.filenameFrom || []).map(function (k) { return String(values[k] || '').trim(); }).filter(Boolean).join(' ');
    var safe = (nm || 'draft').replace(/[\\/:*?"<>|]+/g, '').replace(/\s+/g, ' ').trim().slice(0, 40);
    var noun = pick(form.output && form.output.noun, lang) || form.schema;
    return safe + '_' + noun + (editionId && editionId !== form.schema ? '_' + editionId : '') + '.pdf';
  }

  /* ── summary for the review screen ────────────────────────────────────── */
  function completeness(form, values) {
    var req = 0, filled = 0;
    form.fields.forEach(function (f) {
      if (f.type === 'note' || !fieldVisible(f, values, form)) return;
      if (!isRequired(f, values)) return;
      req++; if (!isEmpty(values[f.key])) filled++;
    });
    return { required: req, filled: filled };
  }

  return {
    MIN_SIZE: MIN_SIZE, evalCond: evalCond, initialValues: initialValues, fieldVisible: fieldVisible, stepVisible: stepVisible, visibleSteps: visibleSteps,
    visibleFields: visibleFields, isRequired: isRequired, editionOf: editionOf, normalizeValue: normalizeValue, validate: validate, overlayValues: overlayValues,
    makeGlyphChecker: makeGlyphChecker, layout: layout, overlayToField: overlayToField, buildSearchIndex: buildSearchIndex, search: search, filename: filename,
    completeness: completeness, dateDot: dateDot, splitDate: splitDate, digitsOnly: digitsOnly, pick: pick, todayIso: todayIso, isEmpty: isEmpty, fitSingle: fitSingle, fitMulti: fitMulti, wrapAt: wrapAt, norm: norm
  };
}));
