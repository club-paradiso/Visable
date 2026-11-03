// @ts-nocheck
/**
 * Deadline reminders (Phase 3, moved verbatim from index.html lines 25978-26288).
 * Legacy IIFE kept as-is; it uses the inline globals tx() and getLanguageOption() (compatibility
 * surface, ADR-009) and the shared localStorage keys paradisoReminders / paradisoReminderBannerDismiss.
 * It used to run at parse time; as a module it runs after parsing, before DOMContentLoaded and before
 * the i18n packs load — the same state it saw before (Korean fallbacks until paradiso-language-applied).
 * Covered by tests/golden/specs/reminders.spec.mjs.
 */

/* === Deadline reminder feature ===
 * Stores user-entered deadlines in localStorage (key: paradisoReminders).
 * On every visit, shows a banner if any deadline is within 30 days.
 * Each saved item can be exported to the user's calendar via .ics download
 * or Google Calendar deep link — those native calendars fire the actual
 * push notifications (we have no notification server).
 */
(function () {
  'use strict';
  var STORAGE_KEY = 'paradisoReminders';
  var DISMISS_KEY = 'paradisoReminderBannerDismiss';
  /* Korean fallbacks keep first paint sane if this runs before i18n packs load;
     the paradiso-language-applied listener re-renders with pack text after. */
  var TYPE_LABELS = {
    visa: '체류기간 만료일',
    arc: '외국인등록증 갱신일',
    appointment: '방문 예약 날짜'
  };
  var TYPE_INDEX = { visa: 0, arc: 1, appointment: 2 };
  function rtx(key, fallback) {
    try { var v = tx(key); return v === key ? fallback : v; } catch (e) { return fallback; }
  }
  function typeLabel(type) {
    var idx = TYPE_INDEX[type];
    try {
      var arr = tx('reminderTypeLabels');
      if (idx !== undefined && Array.isArray(arr) && arr[idx]) return arr[idx];
    } catch (e) {}
    return TYPE_LABELS[type] || rtx('reminderTypeShort', '기한');
  }

  var form = document.getElementById('reminderForm');
  if (!form) return;
  var typeEl = document.getElementById('reminderType');
  var dateEl = document.getElementById('reminderDate');
  var memoEl = document.getElementById('reminderMemo');
  var errorEl = document.getElementById('reminderFormError');
  var successEl = document.getElementById('reminderSaveStatus');
  var listEl = document.getElementById('reminderItems');
  var emptyEl = document.getElementById('reminderEmpty');
  var banner = document.getElementById('reminderBanner');
  var bannerText = document.getElementById('reminderBannerText');
  var bannerClose = document.getElementById('reminderBannerClose');
  var submitEl = form.querySelector('[type="submit"]');
  var cancelEditEl = document.getElementById('reminderCancelEdit');
  var editingId = null;

  function resetEditState() {
    editingId = null;
    form.reset();
    if (submitEl) submitEl.textContent = rtx('reminderSubmit', 'Save reminder');
    if (cancelEditEl) cancelEditEl.hidden = true;
  }

  function load() {
    try {
      var raw = localStorage.getItem(STORAGE_KEY);
      var arr = raw ? JSON.parse(raw) : [];
      return Array.isArray(arr) ? arr : [];
    } catch (e) { return []; }
  }
  function save(items) {
    try { localStorage.setItem(STORAGE_KEY, JSON.stringify(items)); return true; } catch (e) { return false; }
  }
  function uid() { return 'r_' + Date.now().toString(36) + Math.random().toString(36).slice(2, 7); }

  function daysUntil(isoDate) {
    var today = new Date();
    today.setHours(0, 0, 0, 0);
    var target = new Date(isoDate + 'T00:00:00');
    return Math.round((target - today) / 86400000);
  }
  function formatReminderDate(isoDate) {
    var d = new Date(isoDate + 'T00:00:00');
    try {
      var langOpt = (typeof getLanguageOption === 'function') ? getLanguageOption() : null;
      return d.toLocaleDateString(langOpt ? langOpt.html : 'ko', { year: 'numeric', month: 'long', day: 'numeric' });
    } catch (e) {
      return d.getFullYear() + '년 ' + (d.getMonth() + 1) + '월 ' + d.getDate() + '일';
    }
  }
  function ddayLabel(n) {
    if (n === 0) return 'D-DAY';
    if (n > 0) return 'D-' + n;
    return 'D+' + Math.abs(n);
  }
  function urgency(n) {
    if (n < 0) return 'past';
    if (n <= 7) return 'urgent';
    if (n <= 30) return 'soon';
    return 'ok';
  }

  function buildIcs(item) {
    var d = item.date.replace(/-/g, '');
    var nextDay = new Date(item.date + 'T00:00:00');
    nextDay.setDate(nextDay.getDate() + 1);
    var dEnd = nextDay.toISOString().slice(0, 10).replace(/-/g, '');
    var stamp = new Date().toISOString().replace(/[-:]/g, '').split('.')[0] + 'Z';
    var summary = (typeLabel(item.type) || rtx('reminderFallbackLabel', '기한 알림')) + (item.memo ? ' - ' + item.memo : '');
    summary = summary.replace(/([,;\\])/g, '\\$1');
    var lines = [
      'BEGIN:VCALENDAR',
      'VERSION:2.0',
      'PRODID:-//Paradiso//Deadline Reminder//KO',
      'CALSCALE:GREGORIAN',
      'METHOD:PUBLISH',
      'BEGIN:VEVENT',
      'UID:' + item.id + '@paradiso',
      'DTSTAMP:' + stamp,
      'DTSTART;VALUE=DATE:' + d,
      'DTEND;VALUE=DATE:' + dEnd,
      'SUMMARY:' + summary,
      'DESCRIPTION:' + rtx('reminderCalendarDesc', 'Visable 기한 알림'),
      'BEGIN:VALARM',
      'TRIGGER:-P7D',
      'ACTION:DISPLAY',
      'DESCRIPTION:' + summary + ' ' + rtx('reminderBefore7', '(7일 전)'),
      'END:VALARM',
      'BEGIN:VALARM',
      'TRIGGER:-P1D',
      'ACTION:DISPLAY',
      'DESCRIPTION:' + summary + ' ' + rtx('reminderBefore1', '(1일 전)'),
      'END:VALARM',
      'END:VEVENT',
      'END:VCALENDAR'
    ];
    return lines.join('\r\n');
  }
  function downloadIcs(item) {
    var blob = new Blob([buildIcs(item)], { type: 'text/calendar;charset=utf-8' });
    var url = URL.createObjectURL(blob);
    var a = document.createElement('a');
    a.href = url;
    a.download = 'paradiso-reminder-' + item.date + '.ics';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    setTimeout(function () { URL.revokeObjectURL(url); }, 1000);
  }
  function googleCalUrl(item) {
    var d = item.date.replace(/-/g, '');
    var nextDay = new Date(item.date + 'T00:00:00');
    nextDay.setDate(nextDay.getDate() + 1);
    var dEnd = nextDay.toISOString().slice(0, 10).replace(/-/g, '');
    var title = (typeLabel(item.type) || rtx('reminderFallbackLabel', '기한 알림')) + (item.memo ? ' - ' + item.memo : '');
    return 'https://calendar.google.com/calendar/render?action=TEMPLATE'
      + '&text=' + encodeURIComponent(title)
      + '&dates=' + d + '/' + dEnd
      + '&details=' + encodeURIComponent(rtx('reminderCalendarDesc', 'Visable 기한 알림'));
  }

  function render() {
    var items = load().slice().sort(function (a, b) {
      return a.date < b.date ? -1 : a.date > b.date ? 1 : 0;
    });
    listEl.innerHTML = '';
    if (items.length === 0) {
      emptyEl.hidden = false;
    } else {
      emptyEl.hidden = true;
      items.forEach(function (item) {
        var n = daysUntil(item.date);
        var li = document.createElement('li');
        li.className = 'p-reminder-item';

        var info = document.createElement('div');
        var head = document.createElement('div');
        head.className = 'p-reminder-item__head';
        var typeSpan = document.createElement('span');
        typeSpan.className = 'p-reminder-item__type';
        typeSpan.textContent = typeLabel(item.type);
        head.appendChild(typeSpan);
        if (item.memo) {
          var memoSpan = document.createElement('span');
          memoSpan.className = 'p-reminder-item__memo';
          memoSpan.textContent = item.memo;
          head.appendChild(memoSpan);
        }
        info.appendChild(head);
        var dateP = document.createElement('div');
        dateP.className = 'p-reminder-item__date';
        dateP.textContent = formatReminderDate(item.date);
        info.appendChild(dateP);
        li.appendChild(info);

        var dday = document.createElement('span');
        dday.className = 'p-reminder-item__dday';
        dday.dataset.urgency = urgency(n);
        dday.textContent = ddayLabel(n);
        li.appendChild(dday);

        var actions = document.createElement('div');
        actions.className = 'p-reminder-item__actions';

        var icsBtn = document.createElement('button');
        icsBtn.type = 'button';
        icsBtn.className = 'p-reminder-item__btn p-reminder-item__btn--primary';
        icsBtn.textContent = rtx('reminderIcsBtn', '내 캘린더에 저장');
        icsBtn.addEventListener('click', function () { downloadIcs(item); });
        actions.appendChild(icsBtn);

        var gBtn = document.createElement('a');
        gBtn.className = 'p-reminder-item__btn';
        gBtn.href = googleCalUrl(item);
        gBtn.target = '_blank';
        gBtn.rel = 'noopener';
        gBtn.textContent = rtx('reminderGcalBtn', 'Google 캘린더에 추가');
        actions.appendChild(gBtn);

        var editBtn = document.createElement('button');
        editBtn.type = 'button';
        editBtn.className = 'p-reminder-item__btn';
        editBtn.textContent = rtx('reminderEditBtn', 'Edit');
        editBtn.addEventListener('click', function () {
          editingId = item.id;
          typeEl.value = item.type;
          dateEl.value = item.date;
          memoEl.value = item.memo || '';
          if (submitEl) submitEl.textContent = rtx('reminderUpdateBtn', 'Save changes');
          if (cancelEditEl) cancelEditEl.hidden = false;
          form.scrollIntoView({ behavior: 'smooth', block: 'center' });
          typeEl.focus();
        });
        actions.appendChild(editBtn);

        var delBtn = document.createElement('button');
        delBtn.type = 'button';
        delBtn.className = 'p-reminder-item__btn p-reminder-item__btn--danger';
        delBtn.textContent = rtx('reminderDeleteBtn', '삭제');
        delBtn.addEventListener('click', function () {
          if (!confirm(rtx('reminderDeleteConfirm', '이 기한을 삭제하시겠습니까?'))) return;
          save(load().filter(function (it) { return it.id !== item.id; }));
          if (editingId === item.id) resetEditState();
          render();
          showBanner();
        });
        actions.appendChild(delBtn);

        li.appendChild(actions);
        listEl.appendChild(li);
      });
    }
    showBanner();
  }

  function showBanner() {
    if (!banner) return;
    var today = new Date().toISOString().slice(0, 10);
    var dismissed = null;
    try { dismissed = localStorage.getItem(DISMISS_KEY); } catch (e) { dismissed = null; }
    if (dismissed === today) { banner.hidden = true; return; }
    var items = load().map(function (it) {
      return { it: it, n: daysUntil(it.date) };
    }).filter(function (x) { return x.n >= 0 && x.n <= 30; })
      .sort(function (a, b) { return a.n - b.n; });
    if (items.length === 0) { banner.hidden = true; return; }
    var first = items[0];
    var label = typeLabel(first.it.type);
    var memo = first.it.memo ? ' (' + first.it.memo + ')' : '';
    var dleft = first.n === 0 ? rtx('reminderBannerToday', '오늘이에요') : rtx('reminderBannerDaysLeft', '{days}일 남았어요').replace('{days}', first.n);
    bannerText.textContent = label + memo + ' — ' + dleft + '.';
    banner.hidden = false;
  }

  if (bannerClose) {
    bannerClose.addEventListener('click', function () {
      var today = new Date().toISOString().slice(0, 10);
      try { localStorage.setItem(DISMISS_KEY, today); } catch (e) {}
      banner.hidden = true;
    });
  }

  if (cancelEditEl) cancelEditEl.addEventListener('click', resetEditState);

  form.addEventListener('submit', function (e) {
    e.preventDefault();
    errorEl.hidden = true;
    var type = typeEl.value;
    var date = dateEl.value;
    var memo = (memoEl.value || '').trim();
    if (!type) { errorEl.textContent = rtx('reminderErrType', '기한 종류를 선택해 주세요.'); errorEl.hidden = false; typeEl.focus(); return; }
    if (!date || !/^\d{4}-\d{2}-\d{2}$/.test(date)) { errorEl.textContent = rtx('reminderErrDate', '날짜를 입력해 주세요.'); errorEl.hidden = false; dateEl.focus(); return; }
    var items = load();
    if (editingId) {
      items = items.map(function (item) {
        return item.id === editingId
          ? Object.assign({}, item, { type: type, date: date, memo: memo, updatedAt: Date.now() })
          : item;
      });
    } else {
      items.push({ id: uid(), type: type, date: date, memo: memo, createdAt: Date.now() });
    }
    if (!save(items)) {
      errorEl.textContent = rtx('reminderErrSave', '저장하지 못했습니다. 브라우저 저장소가 차단되어 있을 수 있습니다.');
      errorEl.hidden = false;
      return;
    }
    resetEditState();
    render();
    successEl.hidden = false;
    setTimeout(function () { successEl.hidden = true; }, 3500);
  });

  window.addEventListener('paradiso-language-applied', function () {
    if (submitEl) submitEl.textContent = editingId ? rtx('reminderUpdateBtn', 'Save changes') : rtx('reminderSubmit', 'Save reminder');
    if (cancelEditEl) cancelEditEl.textContent = rtx('reminderCancelEdit', 'Cancel edit');
    render();
  });
  render();
})();
