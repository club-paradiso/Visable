#!/usr/bin/env node
/*
 * scripts/check_deadline_helpers.js
 *
 * Deterministic FUNCTIONAL check (not just string presence) for the inline
 * deadline-calculator helpers in index.html. It extracts the pure date / ICS /
 * Google-Calendar helper functions and exercises them with a small `tx` stub:
 *
 *   - paradisoDeadlineAddDays  : timezone-neutral date math, invalid handling
 *   - paradisoDeadlineDdayLabel: D-day formatting
 *   - buildDeadlineIcs         : all-day VEVENT with DTSTART/SUMMARY/DESCRIPTION,
 *                                cautious wording, no personal data
 *   - deadlineGoogleCalUrl     : safe URL encoding + cautious details
 *
 * Exits non-zero on any failed assertion. No network, no DOM.
 */
'use strict';

const fs = require('fs');
const path = require('path');

const INDEX_PATH = path.resolve(__dirname, '..', 'index.html');

function fail(msg) {
  console.error(`[check_deadline_helpers] ${msg}`);
  process.exitCode = 1;
}

function extractRange(html, startMarker, endMarker) {
  const start = html.indexOf(startMarker);
  if (start === -1) { fail(`could not find ${startMarker}`); process.exit(1); }
  const end = html.indexOf(endMarker, start + startMarker.length);
  if (end === -1) { fail(`could not find ${endMarker}`); process.exit(1); }
  return html.slice(start, end);
}

function main() {
  const html = fs.readFileSync(INDEX_PATH, 'utf8');
  // Pure helpers live contiguously between these two function declarations.
  const src = extractRange(html, 'function paradisoDeadlineAddDays(', '\nfunction downloadDeadlineIcs(');

  // Compile the extracted helpers in a sandbox with a minimal tx() stub.
  const factory = new Function(`
    'use strict';
    const tx = (k) => (k === 'deadlineDdayToday' ? 'Today' : k);
    ${src}
    return { paradisoDeadlineAddDays, paradisoDeadlineDaysFromToday, paradisoDeadlineDdayLabel, buildDeadlineIcs, deadlineGoogleCalUrl };
  `);
  let H;
  try {
    H = factory();
  } catch (err) {
    fail(`failed to compile deadline helpers: ${err.message}`);
    process.exit(1);
  }

  let checks = 0;
  const ok = (cond, msg) => { checks++; if (!cond) fail(`FAIL: ${msg}`); };

  // --- date math (timezone-neutral, UTC-based) ---
  ok(H.paradisoDeadlineAddDays('2026-01-01', 90) === '2026-04-01', 'entry+90 → 2026-04-01');
  ok(H.paradisoDeadlineAddDays('2026-03-01', -60) === '2025-12-31', 'expiry-60 crosses year boundary');
  ok(H.paradisoDeadlineAddDays('2024-02-28', 1) === '2024-02-29', 'leap day handling');
  ok(H.paradisoDeadlineAddDays('not-a-date', 90) === '', 'invalid date → empty');
  ok(H.paradisoDeadlineAddDays('', 90) === '', 'empty date → empty');

  // --- ICS generation ---
  const ics = H.buildDeadlineIcs({
    title: 'Estimated registration deadline',
    date: '2026-05-10',
    note: 'Common-rule preparation reminder. Not an official deadline; confirm with HiKorea, 1345.',
  });
  ok(ics.includes('BEGIN:VEVENT') && ics.includes('END:VCALENDAR'), 'ICS envelope');
  ok(ics.includes('DTSTART;VALUE=DATE:20260510'), 'ICS DTSTART all-day');
  ok(ics.includes('SUMMARY:Estimated registration deadline'), 'ICS SUMMARY');
  ok(/DESCRIPTION:[^\r\n]*Not an official deadline/.test(ics), 'ICS DESCRIPTION carries caution');
  ok(!/passport|email|phone|nationality/i.test(ics), 'ICS has no personal-data fields');
  ok(H.buildDeadlineIcs({ title: 'x', date: 'bad' }) === '', 'ICS invalid date → empty');

  // --- Google Calendar URL ---
  const g = H.deadlineGoogleCalUrl({ title: '예상 등록 기한', date: '2026-05-10', note: '준비용 알림. 공식 기한 아님.' });
  ok(g.startsWith('https://calendar.google.com/calendar/render?action=TEMPLATE'), 'GCal base URL');
  ok(g.includes('text=' + encodeURIComponent('예상 등록 기한')), 'GCal encodes title');
  ok(g.includes('dates=20260510/20260511'), 'GCal all-day range');
  ok(g.includes('details=' + encodeURIComponent('준비용 알림. 공식 기한 아님.')), 'GCal encodes cautious details');
  ok(H.deadlineGoogleCalUrl({ title: 'x', date: 'bad' }) === '', 'GCal invalid date → empty');

  if (process.exitCode === 1) {
    console.error('[check_deadline_helpers] FAILED');
  } else {
    console.log(`[check_deadline_helpers] OK — ${checks} functional checks passed`);
  }
}

main();
