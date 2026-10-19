/* ============================================================================
 * Visable — home search suggestions (deterministic, local, no network per key)
 * ----------------------------------------------------------------------------
 * suggest(query, index) turns what the user is typing into a short ranked list
 * of things the existing search already resolves:
 *
 *   status        a 체류자격 code (E-7)                 → searches the code
 *   substatus     a subcode, always shown under its parent (E-7-1 under E-7)
 *   status_procedure  code × procedure (F-6 체류기간 연장)
 *   procedure     a procedure on its own (체류지 변경 신고)
 *   tool          an existing page or dialog (Form Helper, visit reservations…)
 *
 * The interpretation is VisableStatusGuidance.interpret() — the same reader the
 * results page uses — over data/search-suggest-index.json, which is derived from
 * the canonical guidance bundle (scripts/build_search_suggest_index.mjs). Nothing
 * here invents a code, a name or a procedure: rows are built from index entries
 * only, and every row that searches is re-interpreted before it is offered, so a
 * suggestion can never lead to a different reading than its label promises.
 *
 * Ranking is a plain score with stable tie-breaks (insertion order follows the
 * natural code order):
 *   1000 the whole query is a status code        950 a code typed in a longer query
 *    990 the whole query is a subcode             900 code × procedure both typed
 *    860 a tool named outright (no status/procedure in the query)
 *    800/750 a procedure on its own (status-independent / status needed)
 *    650 a status reached through an alias         600 code × likely procedure
 *    500 subcodes / codes continuing the typed prefix
 *    450 alias candidates       400 name matches       300 tools alongside
 *
 * Pure: no DOM. Exposed on globalThis.VisableSearchSuggest for Node tests.
 * ========================================================================== */
(function (root) {
  'use strict';

  var PROCEDURE_ORDER = ['extension', 'status_change', 'registration', 'workplace_change', 'part_time_work', 'activities_outside_status', 'reentry', 'registration_info_report', 'residence_report', 'card_reissue', 'status_grant', 'workplace_report', 'visa_issuance', 'visa_issuance_confirmation', 'electronic_visa', 'program_condition_change'];
  // States offered unprompted for a code the user typed alone. A procedure the user typed is
  // shown whatever its state: the guidance then explains a "not applicable" answer itself.
  var LIKELY_STATES = { SUPPORTED: 1, CONDITIONAL: 1, SOURCE_ONLY: 2 };
  var LISTABLE_KINDS = { status: true, substatus: true };

  /* Product navigation, not immigration content: each tool is an existing page or
   * an existing dialog on the home (index.html data-action handlers). */
  var TOOLS = [
    { id: 'forms', href: 'form-helper.html', label: 'paperwork', sub: 'paperworkSub', terms: ['통합신청서', '신청서', '서식', '양식', '서류 작성', 'application form', 'integrated application', 'form helper', 'forms', 'form'] },
    { id: 'reservation', action: 'open-hikorea-guide', label: 'reservation', sub: 'reservationSub', terms: ['방문예약', '방문 예약', '예약', '하이코리아', 'hikorea', 'hi korea', 'reservation', 'appointment', 'booking'] },
    { id: 'office', action: 'open-jurisdiction-modal', label: 'office', sub: 'officeSub', terms: ['관할', '출입국관서', '출입국 관서', '출입국사무소', '출입국 사무소', '외국인관서', 'immigration office', 'jurisdiction', 'which office'] },
    { id: 'reader', href: 'manual.html', label: 'reader', sub: 'readerSub', terms: ['매뉴얼', '원문 읽기', '원문읽기', '매뉴얼 원문', 'manual', 'manuals', 'read the manual'] },
    { id: 'newhome', href: 'new-home.html', label: 'newHome', sub: 'newHomeSub', terms: ['귀화', '국적취득', '국적 취득', '국적', 'naturalization', 'naturalisation', 'citizenship'] },
    { id: 'waymaker', href: 'ai.html', label: 'waymaker', sub: 'waymakerSub', terms: ['waymaker', '웨이메이커', 'ai 상담', 'ai 안내'] }
  ];

  /* ------------------------------------------------------------ normalize -- */
  // Width, dash and space variants only. Code recognition itself stays in interpret().
  function normalize(text) {
    var s = String(text == null ? '' : text);
    if (typeof s.normalize === 'function') s = s.normalize('NFKC');
    return s.replace(/[‐‑‒–—―−﹣－]/g, '-').replace(/[​-‍﻿]/g, '').replace(/\s+/g, ' ').trim().slice(0, 300);
  }
  function lower(s) { return String(s || '').toLowerCase(); }
  function escapeRe(s) { return s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'); }
  function hasTerm(text, term) {
    var t = lower(term);
    if (!/[a-z]/.test(t)) return text.indexOf(t) >= 0;
    return new RegExp('(^|[^a-z])' + escapeRe(t) + '($|[^a-z])').test(text);
  }

  /* -------------------------------------------------------------- hydrate -- */
  // Lookups computed once per index: parents in natural order, subcodes per parent.
  function codeSortKey(code) {
    var p = String(code).split('-');
    var num = function (x) { var n = parseInt(x, 10); return isNaN(n) ? 999 : n; };
    return [p[0], num(p[1]), p.length > 2 ? num(p[2]) : -1, p.slice(2).join('-')];
  }
  function compareCodes(a, b) {
    var ka = codeSortKey(a), kb = codeSortKey(b);
    for (var i = 0; i < ka.length; i++) { if (ka[i] < kb[i]) return -1; if (ka[i] > kb[i]) return 1; }
    return 0;
  }
  function hydrate(index) {
    if (!index || index.__hydrated) return index;
    var parents = [], children = {};
    Object.keys(index.codes || {}).forEach(function (code) {
      var c = index.codes[code];
      if (!LISTABLE_KINDS[c.kind]) return;
      if (c.kind === 'status') parents.push(code);
      else if (c.parent) (children[c.parent] = children[c.parent] || []).push(code);
    });
    parents.sort(compareCodes);
    Object.keys(children).forEach(function (k) { children[k].sort(compareCodes); });
    var procedures = {};
    (index.procedures || []).forEach(function (p) { procedures[p.id] = p; });
    var registry = {};
    (index.procedure_registry || []).forEach(function (r) { registry[r.procedure] = r.context_requirement; });
    Object.defineProperty(index, '__hydrated', { value: { parents: parents, children: children, procedures: procedures, registry: registry }, enumerable: false });
    return index;
  }

  /* ------------------------------------------------------------- labels --- */
  function codeName(index, code, lang) { var c = index.codes[code]; if (!c) return ''; return lang === 'ko' ? (c.name_ko || c.name_en) : (c.name_en || c.name_ko); }
  function procName(index, pid, lang) { var p = index.__hydrated.procedures[pid]; if (!p) return ''; return lang === 'ko' ? p.ko : (p.en || p.ko); }
  function statusLabel(index, code, lang) { var n = codeName(index, code, lang); return n ? code + ' ' + n : code; }
  function lifecycleNote(index, code) {
    var c = index.codes[code] || {};
    if (c.lifecycle === 'legacy_holders_only') return { key: 'lifecycleLegacy' };
    if (c.lifecycle === 'abolished') return { key: 'lifecycleAbolished' };
    if (c.lifecycle === 'unverified') return { key: 'lifecycleUnverified' };
    return null;
  }
  function domainNote(index, pid) { var p = index.__hydrated.procedures[pid]; return p ? { key: p.domain === 'visa' ? 'domainVisa' : 'domainStay' } : null; }
  function compact(list) { return list.filter(Boolean); }

  /* ------------------------------------------------------------ interpret -- */
  function interpreter(opts) {
    if (opts && typeof opts.interpret === 'function') return opts.interpret;
    var SG = root.VisableStatusGuidance;
    return SG && typeof SG.interpret === 'function' ? SG.interpret : null;
  }
  function blankInterp(q) { return { query: q, codes: [], unknownCodes: [], aliasCandidates: [], aliasQuestion: null, procedure: null, procedureCandidates: [], confidence: 'LOW', isQuestion: false }; }

  // A row that searches is offered only if searching its query reads back as the
  // same status and procedure (the guard against labels that promise more than
  // the search delivers, e.g. an English procedure name the keywords miss).
  function readsAs(interp, index, query, code, procedure) {
    var r;
    try { r = interp(query, index); } catch (e) { return false; }
    var got = r.codes && r.codes[0] ? r.codes[0].code : null;
    if ((code || null) !== got) return false;
    if (code && r.unknownCodes && r.unknownCodes.length) return false;
    return (procedure || null) === (r.procedure || null);
  }

  /* -------------------------------------------------------------- suggest -- */
  // The whole query is (the start of) a code: "E", "E-", "E-7", "e 7 1", "E-7-S". A word that merely
  // starts with A–H ("family", "english", "go") is not: the tail is only allowed after digits.
  var CODE_ONLY = /^([A-Ha-h])(?:\s?-\s?)?(?:(\d{1,2})(?:\s?-\s?|\s)?([0-9A-Za-z]{0,6}))?$/;
  // Code-shaped text the sources do not know: a dashed token anywhere ("XYZ-999 연장"), or a query that is
  // nothing but letters and numbers ("e 7 99"). Spaced forms inside a sentence ("I am 25") are not codes.
  var CODE_SHAPE = /(^|[^A-Za-z0-9])([A-Za-z]{1,3})\s?-\s?(\d{1,3})(?:\s?-\s?([0-9A-Za-z]{1,6}))?(?![A-Za-z0-9])/;
  var CODE_SHAPE_WHOLE = /^()([A-Za-z]{1,3})[\s-]+(\d{1,3})(?:[\s-]+([0-9A-Za-z]{1,6}))?$/;

  function suggest(rawQuery, index, opts) {
    opts = opts || {};
    var lang = opts.lang === 'ko' ? 'ko' : 'en';
    var limit = opts.limit || 7;
    var q = normalize(rawQuery);
    var out = { query: q, items: [], notes: [], interp: null };
    if (!q || !index || !index.codes) return out;
    hydrate(index);
    var H = index.__hydrated;
    var interp = interpreter(opts);
    var I = interp ? interp(q, index) : blankInterp(q);
    out.interp = I;
    var text = lower(q);
    var rows = [], seen = {};
    function add(row) {
      var key = row.kind + '|' + (row.query || row.href || row.action);
      if (seen[key]) { if (row.score > seen[key].score) seen[key].score = row.score; return; }
      if (row.query) {
        if (!interp || !readsAs(interp, index, row.query, row.code || null, row.procedure || null)) {
          // An English label the keywords do not read falls back to the Korean canonical label.
          if (row.queryKo && row.queryKo !== row.query && interp && readsAs(interp, index, row.queryKo, row.code || null, row.procedure || null)) row.query = row.queryKo;
          else return;
        }
      }
      delete row.queryKo;
      row.order = rows.length;
      seen[key] = row; rows.push(row);
    }
    function statusRow(code, score, match) {
      var c = index.codes[code];
      if (!c || !LISTABLE_KINDS[c.kind]) return;
      var sub = c.kind === 'substatus'
        ? { key: 'subOf', vars: { parent: statusLabel(index, c.parent, lang) } }
        : ((H.children[code] || []).length ? { key: 'statusSubs', vars: { n: (H.children[code] || []).length } } : { key: 'statusKind' });
      add({ kind: c.kind, code: code, label: statusLabel(index, code, lang), labelLang: lang, query: code, sub: compact([sub, lifecycleNote(index, code)]), match: match, score: score });
    }
    function comboRow(code, pid, score, match) {
      var c = index.codes[code];
      if (!c || !LISTABLE_KINDS[c.kind] || !H.procedures[pid]) return;
      var st = c.procedures && c.procedures[pid];
      if (!st) return;
      var subs = [domainNote(index, pid)];
      if (c.kind === 'substatus') subs.push({ key: 'subOf', vars: { parent: statusLabel(index, c.parent, lang) } });
      if (st.s === 'NOT_APPLICABLE') subs.push({ key: 'stateNotApplicable' });
      else if (st.s === 'GENERALLY_NOT_PERMITTED' || st.s === 'EXCEPTION_ONLY') subs.push({ key: 'stateRestricted' });
      add({ kind: 'status_procedure', code: code, procedure: pid, label: code + ' ' + procName(index, pid, lang), labelLang: lang, query: code + ' ' + procName(index, pid, lang), queryKo: code + ' ' + procName(index, pid, 'ko'), sub: compact(subs), match: match, score: score });
    }
    function procedureRow(pid, score, match) {
      if (!H.procedures[pid]) return;
      var req = H.registry[pid];
      var independent = req === 'STATUS_INDEPENDENT' || req === 'STATUS_OPTIONAL';
      add({ kind: 'procedure', procedure: pid, label: procName(index, pid, lang), labelLang: lang, query: procName(index, pid, lang), queryKo: procName(index, pid, 'ko'), sub: compact([domainNote(index, pid), { key: independent ? 'procAnyStatus' : 'procNeedsStatus' }]), match: match, score: score });
    }
    function likelyProcedures(code, n) {
      var c = index.codes[code];
      if (!c) return [];
      var ranked = PROCEDURE_ORDER.filter(function (pid) { var st = c.procedures && c.procedures[pid]; return st && LIKELY_STATES[st.s]; });
      ranked.sort(function (a, b) { return (LIKELY_STATES[c.procedures[a].s] - LIKELY_STATES[c.procedures[b].s]) || (PROCEDURE_ORDER.indexOf(a) - PROCEDURE_ORDER.indexOf(b)); });
      return ranked.slice(0, n);
    }

    var primary = I.codes && I.codes[0] ? I.codes[0] : null;
    var codeOnly = q.match(CODE_ONLY);
    var procedure = I.procedure || null;

    // 1. the code(s) the interpreter recognised
    if (primary && !primary.fromUnknown) {
      var whole = !!codeOnly && !procedure;
      var isSub = index.codes[primary.code] && index.codes[primary.code].kind === 'substatus';
      var score = primary.fromAlias ? 650 : (whole ? (isSub ? 990 : 1000) : 950);
      if (procedure) comboRow(primary.code, procedure, 900, 'strong');
      statusRow(primary.code, procedure ? 700 : score, primary.fromAlias ? 'alias' : (whole ? 'exact' : 'code'));
      if (!procedure) likelyProcedures(primary.code, 3).forEach(function (pid, i) { comboRow(primary.code, pid, 600 - i, 'likely'); });
    } else if (primary && primary.fromUnknown) {
      out.notes.push({ key: 'unknownCode', vars: { code: primary.fromUnknown } });
      statusRow(primary.code, 520, 'parent');
    }

    // 2. codes continuing what is typed: "E" → parents, "E-7" → its subcodes, "E-7-S" → E-7-S1, E-7-S2…
    if (codeOnly) {
      var letter = codeOnly[1].toUpperCase(), digits = codeOnly[2] || '', tail = (codeOnly[3] || '').toUpperCase();
      if (!digits) {
        H.parents.filter(function (code) { return code.charAt(0) === letter && (index.codes[code].lifecycle === 'active'); }).forEach(function (code, i) { statusRow(code, 500 - i, 'prefix'); });
      } else {
        var parent = letter + '-' + digits;
        if (index.codes[parent]) {
          (H.children[parent] || []).filter(function (code) {
            var c = index.codes[code];
            return c.lifecycle === 'active' && (!tail || code.slice(parent.length + 1).toUpperCase().indexOf(tail) === 0);
          }).forEach(function (code, i) { statusRow(code, 500 - i, 'prefix'); });
        }
        if (!tail) H.parents.filter(function (code) { return code !== parent && code.indexOf(parent) === 0 && index.codes[code].lifecycle === 'active'; }).forEach(function (code, i) { statusRow(code, 480 - i, 'prefix'); });
      }
    }

    // 3. procedures without a code
    if (!primary) {
      if (procedure) {
        var reg = H.registry[procedure];
        procedureRow(procedure, reg === 'STATUS_INDEPENDENT' || reg === 'STATUS_OPTIONAL' ? 800 : 750, 'procedure');
      }
      (I.procedureCandidates || []).forEach(function (pid, i) { if (pid !== procedure) procedureRow(pid, 700 - i, 'procedure_candidate'); });
      // alias groups (유학 → D-2 / D-4): each candidate, and with the procedure when one is typed
      (I.aliasCandidates || []).forEach(function (code, i) {
        if (procedure) comboRow(code, procedure, 550 - i, 'alias');
        statusRow(code, 450 - i, 'alias');
      });
    }

    // 4. names: "결혼이민" → F-6, "전문인력" → E-7-1 (only when the query is not just a code)
    if (!codeOnly && q.length >= 2) {
      var needle = text.replace(/[?？!.,]/g, '').trim();
      if (needle.length >= 2) {
        var hits = [];
        Object.keys(index.codes).forEach(function (code) {
          var c = index.codes[code];
          if (!LISTABLE_KINDS[c.kind] || c.lifecycle !== 'active') return;
          if (lower(c.name_ko).indexOf(needle) >= 0 || (needle.length >= 3 && lower(c.name_en).indexOf(needle) >= 0)) hits.push(code);
        });
        hits.sort(function (a, b) { var ka = index.codes[a].kind === 'status' ? 0 : 1, kb = index.codes[b].kind === 'status' ? 0 : 1; return (ka - kb) || compareCodes(a, b); });
        hits.slice(0, 4).forEach(function (code, i) { statusRow(code, 400 - i, 'name'); });
      }
    }

    // 5. tools — named outright, or alongside an interpreted query
    var interpreted = !!(primary || procedure || (I.aliasCandidates || []).length);
    TOOLS.forEach(function (tool, i) {
      if (!tool.terms.some(function (t) { return hasTerm(text, t); })) return;
      add({ kind: 'tool', tool: tool.id, href: tool.href || null, action: tool.action || null, labelKey: tool.label, sub: [{ key: tool.sub }], match: 'tool', score: (interpreted ? 300 : 860) - i });
    });
    // a question or a long description: Waymaker explains the situation step by step
    if (!seen['tool|ai.html'] && (I.isQuestion || q.length >= 24)) {
      add({ kind: 'tool', tool: 'waymaker', href: 'ai.html', action: null, labelKey: 'waymaker', sub: [{ key: 'waymakerAsk' }], match: 'tool', score: 100 });
    }

    // 6. a code-shaped token the sources do not know ("XYZ-999") is said, never matched
    if (!primary && !(I.unknownCodes || []).length) {
      var shape = q.match(CODE_SHAPE) || q.match(CODE_SHAPE_WHOLE);
      if (shape) out.notes.push({ key: 'notACode', vars: { code: (shape[2] + '-' + shape[3] + (shape[4] ? '-' + shape[4] : '')).toUpperCase() } });
    }

    rows.sort(function (a, b) { return (b.score - a.score) || (a.order - b.order); });
    out.items = rows.slice(0, limit).map(function (row, i) { row.rank = i; delete row.order; return row; });
    return out;
  }

  var api = { normalize: normalize, hydrate: hydrate, suggest: suggest, compareCodes: compareCodes, TOOLS: TOOLS, PROCEDURE_ORDER: PROCEDURE_ORDER };
  root.VisableSearchSuggest = api;
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
})(typeof globalThis !== 'undefined' ? globalThis : this);
