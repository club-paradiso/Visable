/*
 * manual-reader-route.js — one place that turns (status code, procedure id) into a
 * manual.html deep link. Used by manual.html itself and by the civic search
 * "관련 원문" panel, and checked by scripts/check_manual_reader.mjs.
 *
 * Hash format: manual.html#c-<chapter>.<v|s>[.<section>]
 *   chapter  = parent status (F-6), or a program chapter (dongpo, regional, youth, toptier, kstar, metro, common)
 *   v / s    = 사증발급 안내매뉴얼 / 외국인체류 안내매뉴얼 (never mixed)
 *   section  = a section key (extend, change, reg, …) or a block index
 * Subcodes link to the parent chapter; the reader never presents a parent chapter
 * as a subcode-specific rule.
 */
(function (root) {
  'use strict';
  var PROCEDURE_SECTION = {
    visa_issuance: ['v', 'consul'],
    visa_issuance_confirmation: ['v', 'cert'],
    electronic_visa: ['v', 'evisa'],
    status_grant: ['s', 'grant'],
    status_change: ['s', 'change'],
    extension: ['s', 'extend'],
    registration: ['s', 'reg'],
    card_reissue: ['s', 'reg'],
    activities_outside_status: ['s', 'extra'],
    part_time_work: ['s', 'parttime'],
    workplace_change: ['s', 'work'],
    workplace_report: ['s', 'work'],
    reentry: ['s', 'reentry']
  };
  var STAY_ONLY = { residence_report: 1, registration_info_report: 1, program_condition_change: 1 };

  function normCode(code) {
    return String(code || '').trim().toUpperCase().replace(/[‐‑‒–—−－]/g, '-').replace(/\s+/g, '');
  }
  var PROGRAMS = { 'DONGPO': 'dongpo', 'REGIONAL': 'regional', 'YOUTH': 'youth', 'TOP-TIER': 'toptier', 'METRO': 'metro', 'K-STAR': 'kstar' };
  function chapterFor(code) {
    var c = normCode(code);
    if (!c) return null;
    if (c.indexOf('PROGRAM:') === 0) return PROGRAMS[c.slice(8)] || null;
    if (c.indexOf('~') > 0) { if (/~DONGPO$/.test(c)) return 'dongpo'; c = c.split('~')[0]; }
    if (c === 'K-STAR' || /^(F-2-7S|F-5-S\d*|F-2-71)$/.test(c)) return 'kstar';
    if (/^[A-H]-\d{1,2}-T\d*$/.test(c) || c === 'F-1-15' || c === 'F-1-24') return 'toptier';
    if (/^E-7-Y$/.test(c)) return 'youth';
    if (/^[A-H]-\d{1,2}-\d*R$|^REGION-S$/.test(c)) return 'regional';
    if (/^F-4(-|$)|^H-2(-|$)|^C-3-8$/.test(c)) return 'dongpo';
    var m = /^([A-H])-(\d{1,2})/.exec(c);
    return m ? m[1] + '-' + m[2] : null;
  }
  /* Returns 'manual.html#c-…' or null when the code is unknown to the manuals. */
  function href(code, procedure, opts) {
    opts = opts || {};
    var chapter = opts.chapter || chapterFor(code);
    if (!chapter) return null;
    var sec = PROCEDURE_SECTION[procedure] || null;
    var tab = sec ? sec[0] : (STAY_ONLY[procedure] ? 's' : (opts.domain === 'visa_issuance' ? 'v' : opts.domain === 'stay' ? 's' : ''));
    var base = opts.base == null ? 'manual.html' : opts.base;
    return base + '#c-' + chapter + (tab ? '.' + tab + (sec ? '.' + sec[1] : '') : '');
  }
  var api = { href: href, chapterFor: chapterFor, PROCEDURE_SECTION: PROCEDURE_SECTION };
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.VisableManualReaderRoute = api;
})(typeof window !== 'undefined' ? window : this);
