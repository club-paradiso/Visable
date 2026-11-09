/*
 * manual-updates.js — shared helper for the "새 매뉴얼 개정 후보" notices.
 *
 * Data: data/manual-updates/pending_revisions.json (built by scripts/build_manual_update_notices.py from the
 * reviewed paragraph diffs). Each revision names the status code(s), the manual (visa | stay) and optionally the
 * procedure(s) it belongs to, and carries the changed manual lines verbatim.
 *
 * Rules this module keeps (CLAUDE.md):
 *  - visa revisions only for visa procedures, stay revisions only for stay procedures (never mixed);
 *  - a revision written for a subcode (D-4-3) is shown for that subcode only, never as a parent-code (D-4) rule;
 *  - the notice always says the new edition is not reviewed and the guidance still follows the earlier edition.
 * Used by status-guidance.js (search result page) and manual-reader.js (manual.html); checked by
 * scripts/check_manual_updates.mjs.
 */
(function (root) {
  'use strict';
  var STR = {
    ko: {
      title: '새 매뉴얼에서 바뀐 곳 (검토 전)', body: '법무부 매뉴얼이 새로 올라와 이 자격과 관련된 부분이 바뀐 것으로 보여요. 아직 사람이 검토하지 않았고, 이 화면의 안내는 이전 판을 따릅니다. 신청 전에 새 원문을 확인하세요.',
      bodyReader: '이 자격에서 새 매뉴얼로 바뀐 곳이에요. 아래 원문에는 이미 반영돼 있어요. 사람이 검토하기 전이라 Visable의 자격별 안내와 AI 답변은 아직 이전 판을 따릅니다.',
      bodyAll: '새로 올라온 법무부 매뉴얼에서 바뀐 곳이에요. 사람이 검토하기 전이라 Visable의 자격별 안내와 AI 답변은 아직 이전 판을 따릅니다. 신청 전에 새 원문을 확인하세요.',
      manualVisa: '사증발급 안내매뉴얼', manualStay: '외국인체류 안내매뉴얼', edition: '{date}판', open: '원문에서 바뀐 곳 보기', lines: '바뀐 원문', tag: '검토 전'
    },
    en: {
      title: 'Changed in the newer manual (not reviewed yet)', body: 'The Ministry of Justice posted a newer manual and part of it related to this status appears to have changed. It has not been reviewed yet, and the guidance on this page still follows the earlier edition. Check the new source before you apply.',
      bodyReader: 'These are the passages that changed for this status in the newer manual. The source text below already includes them. They have not been reviewed yet, so Visable\'s status guidance and AI answers still follow the earlier edition.',
      bodyAll: 'These are the passages that changed in the newly posted Ministry of Justice manuals. They have not been reviewed yet, so Visable\'s status guidance and AI answers still follow the earlier edition. Check the new source before you apply.',
      manualVisa: 'Visa Issuance Guide Manual', manualStay: 'Foreigner Stay/Residence Guide Manual', edition: '{date} edition', open: 'See the changed passage in the manual', lines: 'Changed source text', tag: 'Not reviewed'
    }
  };
  function esc(v) { return String(v == null ? '' : v).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; }); }
  function t(lang, key, vars) { var s = (STR[lang] || STR.ko)[key]; return vars ? s.replace(/\{(\w+)\}/g, function (_, k) { return vars[k] == null ? '' : vars[k]; }) : s; }

  // domain: 'visa' | 'stay'; codes: candidate status codes (e.g. [model.status, model.target]); procedure: procedure id or null.
  function forStatus(data, domain, codes, procedure) {
    if (!data || !Array.isArray(data.revisions)) return [];
    var want = (codes || []).map(function (c) { return String(c || '').split('#')[0]; }).filter(Boolean);
    return data.revisions.filter(function (r) {
      if (r.role !== domain) return false;
      if (!r.codes.some(function (c) { return want.indexOf(c) >= 0; })) return false;
      return !r.procedures || !r.procedures.length || (procedure && r.procedures.indexOf(procedure) >= 0);
    });
  }
  function manualOf(data, r) { return data && data.editions && data.editions[r.role] || null; }
  function href(r, base) { return (base == null ? 'manual.html' : base) + '#' + r.reader_hash; }

  function noticeHtml(data, items, lang, opts) {
    if (!items || !items.length) return '';
    lang = lang === 'en' ? 'en' : 'ko'; opts = opts || {};
    var rows = items.map(function (r) {
      var ed = manualOf(data, r);
      var manual = t(lang, r.role === 'visa' ? 'manualVisa' : 'manualStay') + (ed ? ' · ' + t(lang, 'edition', { date: ed.source_date }) : '');
      var lines = (r.manual_lines || []).map(function (l) { return '<li>' + esc(l) + '</li>'; }).join('');
      return '<li class="mu-item"><p class="mu-item-title">' + esc(lang === 'en' ? (r.title_en || r.title_ko) : r.title_ko) + '</p>'
        + '<p class="mu-item-sum">' + esc(lang === 'en' ? (r.summary_en || r.summary_ko) : r.summary_ko) + '</p>'
        + '<details class="mu-lines"><summary>' + esc(t(lang, 'lines')) + '</summary><ul lang="ko">' + lines + '</ul></details>'
        + '<p class="mu-item-src">' + esc(manual) + ' · <a href="' + esc(href(r, opts.base)) + '">' + esc(t(lang, 'open')) + '</a></p></li>';
    }).join('');
    return '<aside class="mu-notice" role="note" aria-labelledby="muTitle' + esc(opts.idSuffix || '') + '"><p class="mu-title" id="muTitle' + esc(opts.idSuffix || '') + '"><span class="mu-tag">' + esc(t(lang, 'tag')) + '</span> ' + esc(t(lang, 'title')) + '</p>'
      + '<p class="mu-body">' + esc(t(lang, opts.variant === 'reader' ? 'bodyReader' : opts.variant === 'all' ? 'bodyAll' : 'body')) + '</p><ul class="mu-list">' + rows + '</ul></aside>';
  }

  var api = { forStatus: forStatus, noticeHtml: noticeHtml, href: href, STR: STR };
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.VisableManualUpdates = api;
})(typeof window !== 'undefined' ? window : this);
