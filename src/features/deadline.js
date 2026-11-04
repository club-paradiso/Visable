// @ts-nocheck
/**
 * Deadline / grace-period calculator and calendar handoff (Phase 3, moved verbatim from index.html lines 20029-20172).
 * Uses the inline globals tx() and escapeHtml() (compatibility surface, ADR-009). Exposed on
 * window.Visable.features.deadline; the inline stubs computeDeadlines() and downloadDeadlineIcs() that the
 * data-action dispatcher calls delegate here. Note (recorded in docs/rebuild/STATUS.md): renderDeadlineCalculator()
 * has no caller — scripts/check_static_visa_result_cards.js forbids mounting it from renderResults() — so the
 * calculator UI is currently unreachable; the pure helpers are exercised by scripts/check_deadline_helpers.js.
 */
// ---- Deadline / grace-period calculator + calendar handoff ----------------
// Pure, timezone-neutral date helpers (UTC-based math on plain YYYY-MM-DD
// strings so results never drift with the viewer's timezone / DST). These are
// intentionally global + side-effect-free so they are easy to verify. The
// calculator is ephemeral: dates are never stored, and never sent to the
// backend or AI (no localStorage, no /api/ask payload).
function paradisoDeadlineAddDays(isoDate, days) {
    const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(String(isoDate || '').trim());
    if (!m) return '';
    const base = Date.UTC(Number(m[1]), Number(m[2]) - 1, Number(m[3]));
    const d = new Date(base + Number(days) * 86400000);
    if (Number.isNaN(d.getTime())) return '';
    return d.getUTCFullYear() + '-' + String(d.getUTCMonth() + 1).padStart(2, '0') + '-' + String(d.getUTCDate()).padStart(2, '0');
}
function paradisoDeadlineDaysFromToday(isoDate) {
    const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(String(isoDate || '').trim());
    if (!m) return null;
    const target = Date.UTC(Number(m[1]), Number(m[2]) - 1, Number(m[3]));
    const now = new Date();
    const today = Date.UTC(now.getFullYear(), now.getMonth(), now.getDate());
    return Math.round((target - today) / 86400000);
}
function paradisoDeadlineDdayLabel(isoDate) {
    const n = paradisoDeadlineDaysFromToday(isoDate);
    if (n === null) return '';
    if (n === 0) return tx('deadlineDdayToday');
    return n > 0 ? ('D-' + n) : ('D+' + Math.abs(n));
}
function buildDeadlineIcs(item) {
    const date = String((item && item.date) || '').replace(/-/g, '');
    if (!/^\d{8}$/.test(date)) return '';
    const endIso = paradisoDeadlineAddDays(item.date, 1).replace(/-/g, '');
    const stamp = new Date().toISOString().replace(/[-:]/g, '').split('.')[0] + 'Z';
    // SUMMARY carries only the user-facing reminder title; no personal data.
    const esc = function (s) { return String(s).replace(/([,;\\])/g, '\\$1').replace(/\r?\n/g, ' '); };
    const summary = esc((item && item.title) || 'Visable reminder');
    // DESCRIPTION carries cautious wording (not just the summary) so an exported
    // event never reads as an official deadline. No personal data is included.
    const note = esc((item && item.note) || 'Visable preparation reminder. Not an official deadline.');
    const uid = 'paradiso-deadline-' + date + '-' + Math.random().toString(36).slice(2, 8) + '@paradiso';
    return [
        'BEGIN:VCALENDAR', 'VERSION:2.0', 'PRODID:-//Paradiso//Deadline Calculator//EN', 'CALSCALE:GREGORIAN', 'METHOD:PUBLISH',
        'BEGIN:VEVENT', 'UID:' + uid, 'DTSTAMP:' + stamp, 'DTSTART;VALUE=DATE:' + date, 'DTEND;VALUE=DATE:' + endIso,
        'SUMMARY:' + summary,
        'DESCRIPTION:' + note,
        'BEGIN:VALARM', 'TRIGGER:-P7D', 'ACTION:DISPLAY', 'DESCRIPTION:' + summary, 'END:VALARM',
        'END:VEVENT', 'END:VCALENDAR'
    ].join('\r\n');
}
function deadlineGoogleCalUrl(item) {
    const date = String((item && item.date) || '').replace(/-/g, '');
    if (!/^\d{8}$/.test(date)) return '';
    const endIso = paradisoDeadlineAddDays(item.date, 1).replace(/-/g, '');
    const title = String((item && item.title) || 'Visable reminder');
    const note = String((item && item.note) || 'Visable preparation reminder. Not an official deadline.');
    return 'https://calendar.google.com/calendar/render?action=TEMPLATE'
        + '&text=' + encodeURIComponent(title)
        + '&dates=' + date + '/' + endIso
        + '&details=' + encodeURIComponent(note);
}
function downloadDeadlineIcs(item) {
    const ics = buildDeadlineIcs(item);
    if (!ics) return;
    const blob = new Blob([ics], { type: 'text/calendar;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'paradiso-deadline-' + (String((item && item.date) || 'reminder')) + '.ics';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    setTimeout(function () { URL.revokeObjectURL(url); }, 1000);
}
function deadlineRowHtml(label, isoDate, caution, sourceStatus) {
    if (!isoDate) return '';
    const dday = paradisoDeadlineDdayLabel(isoDate);
    // Cautious calendar wording shared by ICS + Google Calendar so an exported
    // event is never read as an official deadline.
    const note = tx('deadlineCalendarCaution');
    const gcal = deadlineGoogleCalUrl({ title: label, date: isoDate, note: note });
    const cautionHtml = caution ? `<p class="deadline-caution">${escapeHtml(caution)}</p>` : '';
    // Source-status badge: which category this computed date belongs to
    // (common-rule preparation aid / custom reminder / etc.). Never "official".
    const sourceHtml = sourceStatus ? `<span class="deadline-row-source" data-deadline-source>${escapeHtml(sourceStatus)}</span>` : '';
    return `<div class="deadline-row">
        <div class="deadline-row-head"><span class="deadline-row-label">${escapeHtml(label)}</span>${dday ? `<span class="deadline-row-dday">${escapeHtml(dday)}</span>` : ''}</div>
        <div class="deadline-row-date">${escapeHtml(isoDate)}</div>
        ${sourceHtml}
        ${cautionHtml}
        <div class="deadline-row-actions" role="group" aria-label="${escapeHtml(tx('deadlineAddToCalendar'))}">
            <button type="button" class="deadline-cal-btn" data-action="deadline-download-ics" data-deadline-title="${escapeHtml(label)}" data-deadline-date="${escapeHtml(isoDate)}" data-deadline-note="${escapeHtml(note)}">${escapeHtml(tx('deadlineDownloadIcs'))}</button>
            <a class="deadline-cal-btn" href="${escapeHtml(gcal)}" target="_blank" rel="noopener noreferrer">${escapeHtml(tx('deadlineAddGoogle'))}</a>
        </div>
    </div>`;
}
function computeDeadlines(btn) {
    const root = btn.closest('[data-deadline-calc]');
    if (!root) return;
    const entry = (root.querySelector('[data-deadline-entry]') || {}).value || '';
    const expiry = (root.querySelector('[data-deadline-expiry]') || {}).value || '';
    const customTitle = String((root.querySelector('[data-deadline-custom-title]') || {}).value || '').trim();
    const customDate = (root.querySelector('[data-deadline-custom-date]') || {}).value || '';
    const results = root.querySelector('[data-deadline-results]');
    if (!results) return;
    const blocks = [];
    // The 90-day registration figure is a COMMON-RULE preparation aid, not a
    // per-status confirmed/official deadline — labeled as such on the row.
    const regDate = entry ? paradisoDeadlineAddDays(entry, 90) : '';
    if (regDate) {
        blocks.push(deadlineRowHtml(tx('deadlineRegEstimate'), regDate, tx('deadlineRegCaution'), tx('deadlineSourceCommonRule')));
    }
    if (expiry) {
        const reminders = [60, 30, 7, 0].map(function (o) {
            const d = paradisoDeadlineAddDays(expiry, -o);
            const sub = o === 0 ? tx('deadlineOnDate') : tx('deadlineDaysBefore', { days: o });
            return deadlineRowHtml(tx('deadlineExtReminders') + ' · ' + sub, d, '', tx('deadlineSourceCommonRule'));
        }).filter(Boolean).join('');
        if (reminders) {
            blocks.push(`<div class="deadline-group"><div class="deadline-group-title">${escapeHtml(tx('deadlineExtReminders'))}</div><p class="deadline-caution">${escapeHtml(tx('deadlineExtCaution'))}</p>${reminders}</div>`);
        }
    }
    if (customDate) {
        blocks.push(deadlineRowHtml(customTitle || tx('deadlineCustomTitle'), customDate, '', tx('deadlineSourceCustom')));
    }
    results.innerHTML = blocks.length ? blocks.join('') : `<p class="deadline-empty">${escapeHtml(tx('deadlineEmpty'))}</p>`;
    results.hidden = false;
}
function renderDeadlineCalculator(v, isVisaCode) {
    if (!isVisaCode) return '';
    return `<details class="deadline-calc manual-section" data-deadline-calc>
        <summary class="deadline-calc-summary">${escapeHtml(tx('deadlineCalcTitle'))}</summary>
        <p class="deadline-intro">${escapeHtml(tx('deadlineCalcIntro'))}</p>
        <div class="deadline-inputs">
            <label class="deadline-field"><span>${escapeHtml(tx('deadlineEntryDate'))}</span><input type="date" data-deadline-entry></label>
            <label class="deadline-field"><span>${escapeHtml(tx('deadlineExpiryDate'))}</span><input type="date" data-deadline-expiry></label>
            <label class="deadline-field"><span>${escapeHtml(tx('deadlineCustomTitle'))}</span><input type="text" data-deadline-custom-title maxlength="80"></label>
            <label class="deadline-field"><span>${escapeHtml(tx('deadlineCustomDate'))}</span><input type="date" data-deadline-custom-date></label>
        </div>
        <button type="button" class="deadline-compute-btn" data-action="compute-deadlines">${escapeHtml(tx('deadlineCompute'))}</button>
        <div class="deadline-results" data-deadline-results role="status" aria-live="polite" hidden></div>
        <p class="deadline-disclaimer">${escapeHtml(tx('deadlineDisclaimer'))}</p>
        <p class="deadline-privacy">${escapeHtml(tx('deadlinePrivacyNote'))}</p>
    </details>`;
}

export {
    paradisoDeadlineAddDays, paradisoDeadlineDaysFromToday, paradisoDeadlineDdayLabel, buildDeadlineIcs,
    deadlineGoogleCalUrl, downloadDeadlineIcs, deadlineRowHtml, computeDeadlines, renderDeadlineCalculator
};
