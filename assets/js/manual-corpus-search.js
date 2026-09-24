/* Page-level retrieval of the pinned September originals. No generated advice. */
(function (root) {
  'use strict';
  var dash = /[‐‑‒–—−－]/g;
  function normalize(value) {
    return String(value || '').normalize('NFKC').replace(dash, '-').toLowerCase().replace(/\s+/g, ' ').trim();
  }
  function prepare(sources, pages) {
    var codes = new Map();
    var byId = new Map(sources.map(function (source) { return [source.id, source]; }));
    var rows = pages.map(function (page) {
      (page.status_codes_detected || []).forEach(function (code) { codes.set(code.replace(/-/g, '').toLowerCase(), code.toLowerCase()); });
      return { page: page, source: byId.get(page.source_id), text: normalize(page.text), heading: normalize(page.heading),
        codes: (page.status_codes_detected || []).map(normalize) };
    }).filter(function (row) { return row.source; });
    return { rows: rows, codes: codes };
  }
  function queryParts(index, query) {
    var parts = normalize(query).split(' ').filter(Boolean).slice(0, 12);
    return parts.map(function (part) { return index.codes.get(part.replace(/-/g, '')) || part; });
  }
  /* Evidence vocabulary per procedure: the phrases the manuals use in their own
   * section headings. Used only to rank pages (never to state a requirement). */
  var PROCEDURE_TERMS = {
    extension: ['체류기간 연장허가', '체류기간연장허가', '체류기간 연장', '연장허가'],
    status_change: ['체류자격 변경허가', '체류자격변경허가', '자격으로의 변경', '자격변경', '변경허가'],
    status_grant: ['체류자격 부여', '체류자격부여', '자격부여'],
    registration: ['외국인등록'],
    card_reissue: ['등록증 재발급', '재발급'],
    reentry: ['재입국허가', '재입국'],
    activities_outside_status: ['체류자격외 활동', '체류자격외활동', '자격외 활동', '자격외활동'],
    part_time_work: ['시간제 취업', '시간제취업'],
    workplace_change: ['근무처 변경', '근무처의 변경', '근무처 추가', '근무처변경'],
    workplace_report: ['고용변동', '취업개시 신고', '신고의무'],
    residence_report: ['체류지 변경', '체류지변경'],
    registration_info_report: ['등록사항 변경', '등록사항변경'],
    visa_issuance: ['사증발급', '사증 발급'],
    visa_issuance_confirmation: ['사증발급인정서', '사증발급인정'],
    electronic_visa: ['전자사증']
  };
  function count(text, term) { return term ? text.split(term).length - 1 : 0; }
  function inRange(ranges, row) {
    var r = ranges && ranges[row.source.id];
    return !!(r && row.page.page >= r[0] && row.page.page <= r[1]);
  }
  /* Intent-aware score. `intent` comes from the resolved guidance, not from raw
   * words: { status, procedure, chapters: {sourceId: [start, end]},
   * anchors: [{source, page}], domain: 'stay' | 'visa_issuance' }. */
  function intentScore(row, intent) {
    var score = 0;
    var status = intent.status ? normalize(intent.status) : '';
    var parent = status ? status.split('-').slice(0, 2).join('-') : '';
    if (inRange(intent.chapters, row)) score += 30;
    (intent.anchors || []).forEach(function (a) {
      if (a.source !== row.source.id) return;
      var d = Math.abs(a.page - row.page.page);
      if (d === 0) score += 60; else if (d === 1) score += 12;
    });
    var own = intent.procedure ? (PROCEDURE_TERMS[intent.procedure] || []) : [];
    if (own.length) {
      var hits = 0;
      own.forEach(function (term, i) { var n = count(row.text, term); if (n) hits += n * (i === 0 ? 3 : 1); if (row.heading.includes(term)) score += 18; });
      score += Math.min(hits * 4, 32);
      // A page written for another procedure outranks nothing: penalise the
      // strongest foreign procedure when it dominates the page.
      var foreign = 0;
      Object.keys(PROCEDURE_TERMS).forEach(function (pid) {
        if (pid === intent.procedure) return;
        var n = 0; PROCEDURE_TERMS[pid].forEach(function (term) { n += count(row.text, term) + (row.heading.includes(term) ? 3 : 0); });
        if (n > foreign) foreign = n;
      });
      if (foreign > hits) score -= Math.min((foreign - hits) * 5, 30);
      // "A ➠ B" pages describe a change between two statuses.
      if (intent.procedure !== 'status_change' && /➠|→/.test(row.heading + ' ' + row.text.slice(0, 160))) score -= 25;
    } else if (status) {
      // status only: the chapter opening (definition, activity range) first, transitions last
      var r = intent.chapters && intent.chapters[row.source.id];
      if (r && row.page.page === r[0]) score += 25;
      if (/➠|→/.test(row.heading)) score -= 20;
    }
    if (status && status !== parent) {
      // a subcode (E-7-4, D-2-5): pages naming the exact subcode beat the family's general pages
      if (row.codes.includes(status)) score += 25;
      if (row.heading.includes(status)) score += 15;
    }
    if (parent) {
      // headings that name a different status family are about that status
      var others = (row.heading.match(/[a-h]-\d{1,2}/g) || []).filter(function (c) { return c !== parent; });
      if (others.length && !row.heading.includes(parent)) score -= 15;
      else if (others.length) score -= Math.min(others.length * 5, 15);
    }
    if (intent.domain && row.source.domain !== intent.domain) score -= 25;
    return score;
  }
  function search(index, query, options) {
    options = options || {};
    var intent = options.intent || null;
    var parts = queryParts(index, query);
    if (!parts.length) return [];
    var isCode = function (part) { return /^[a-h]-\d{1,2}(?:-[a-z0-9]+)*$/.test(part) || /^(k-star|region-s|youth-stay)$/.test(part); };
    var matchesCode = function (codes, part) {
      return codes.includes(part) || (/^[a-h]-\d{1,2}$/.test(part) && codes.some(function (code) { return code.startsWith(part + '-'); }));
    };
    if (intent && (intent.status || intent.procedure)) {
      // Evidence query: the interpreted status and procedure, not the raw words.
      // A page qualifies when it belongs to the status (code on the page or the
      // status chapter) and, for a procedure, uses that procedure's vocabulary
      // or is a cited anchor page.
      var st = intent.status ? normalize(intent.status) : '';
      var terms = intent.procedure ? (PROCEDURE_TERMS[intent.procedure] || []) : [];
      var anchored = function (row) { return (intent.anchors || []).some(function (a) { return a.source === row.source.id && Math.abs(a.page - row.page.page) <= 1; }); };
      return index.rows.filter(function (row) {
        if (options.domain && row.source.domain !== options.domain) return false;
        if (row.page.page <= 2) return false;
        var statusOk = !st || matchesCode(row.codes, st) || matchesCode(row.codes, st.split('-').slice(0, 2).join('-')) || inRange(intent.chapters, row);
        var procOk = !terms.length || terms.some(function (t) { return row.text.includes(t); }) || anchored(row);
        return (statusOk && procOk) || anchored(row);
      }).map(function (row) {
        return { page: row.page, source: row.source, score: intentScore(row, intent) };
      }).sort(function (a, b) { return b.score - a.score || b.source.date.localeCompare(a.source.date) || a.page.page - b.page.page; });
    }
    return index.rows.filter(function (row) {
      return (!options.domain || row.source.domain === options.domain) && parts.every(function (part) {
        return isCode(part) ? matchesCode(row.codes, part) : row.text.includes(part);
      });
    }).map(function (row) {
      var score = row.page.page <= 2 ? -100 : 0;
      parts.forEach(function (part) {
        if (row.heading.includes(part)) score += 20;
        if (!isCode(part)) score += Math.min(row.text.split(part).length - 1, 12);
      });
      if (row.text.includes(parts.join(' '))) score += 8;
      if (row.source.domain === 'stay' && parts.some(function (part) { return /^(연장|변경|등록|재입국)$/.test(part); })) score += 6;
      return { page: row.page, source: row.source, score: score };
    }).sort(function (a, b) { return b.score - a.score || b.source.date.localeCompare(a.source.date) || a.page.page - b.page.page; });
  }
  function excerpt(text, query, index, size) {
    var plain = String(text || '').replace(/\s+/g, ' ').trim();
    var terms = queryParts(index, query).sort(function (a, b) { return b.length - a.length; });
    var lower = normalize(plain);
    var found = terms.map(function (term) { return lower.indexOf(term); }).filter(function (n) { return n >= 0; });
    var start = Math.max(0, (found[0] || 0) - 65);
    return (start ? '…' : '') + plain.slice(start, start + (size || 220)) + (plain.length > start + (size || 220) ? '…' : '');
  }
  root.VisableManualSearch = { normalize: normalize, prepare: prepare, search: search, excerpt: excerpt, intentScore: intentScore, PROCEDURE_TERMS: PROCEDURE_TERMS };
})(typeof globalThis !== 'undefined' ? globalThis : this);
