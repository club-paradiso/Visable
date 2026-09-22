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
  function search(index, query, options) {
    options = options || {};
    var parts = queryParts(index, query);
    if (!parts.length) return [];
    var isCode = function (part) { return /^[a-h]-\d{1,2}(?:-[a-z0-9]+)*$/.test(part) || /^(k-star|region-s|youth-stay)$/.test(part); };
    var matchesCode = function (codes, part) {
      return codes.includes(part) || (/^[a-h]-\d{1,2}$/.test(part) && codes.some(function (code) { return code.startsWith(part + '-'); }));
    };
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
  root.VisableManualSearch = { normalize: normalize, prepare: prepare, search: search, excerpt: excerpt };
})(typeof globalThis !== 'undefined' ? globalThis : this);
