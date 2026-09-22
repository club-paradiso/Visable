/* ============================================================================
 * Visable — local-practice report flow ("실제 방문 내용이 달랐나요?")
 * ----------------------------------------------------------------------------
 * A short structured report for users whose office visit differed from the
 * guidance. Opens from the guidance layer (event `visable:local-report`) as an
 * accessible dialog: focus is trapped, Escape closes, focus returns.
 *
 * Privacy: no passport number, ARC number, resident registration number, case
 * number or full name is asked for; free text is checked client-side for such
 * patterns and the user must confirm the text carries none. Nothing is uploaded.
 *
 * Honesty: the report is POSTed to /api/local-practice/report. That function
 * forwards to an operator-configured intake or answers 503 NOT_CONFIGURED. The
 * UI shows exactly which of these happened; it never claims a report was
 * received when it was not. A report never becomes guidance by itself
 * (see data/local-practice-202609.json → promotion_rule).
 * ========================================================================== */
(function (root) {
  'use strict';
  var COPY = {
    ko: {
      title: '실제 방문 내용이 달랐나요?', intro: '관할 관서에서 실제로 요구한 내용을 알려주시면 검토 후 다른 이용자에게 "관서별 차이"로 안내할 수 있어요. 제보 하나로 안내가 바뀌지는 않으며, 검토 전에는 표시되지 않아요.',
      office: '방문한 관서', officeOther: '직접 입력', month: '방문 시기 (월)', procedure: '어떤 업무였나요?', status: '체류자격 (알면 입력)', statusUnknown: '잘 모르겠어요',
      expected: '안내에는 있었는데 요구하지 않은 서류', requested: '안내에는 없었는데 추가로 요구한 서류', feeDiff: '수수료·납부 방식이 달랐다면', processDiff: '예약·절차가 달랐다면', notes: '그 밖의 메모', evidence: '영수증·안내문 등 확인 자료를 보여줄 수 있어요 (업로드하지 않음)',
      privacy: '여권번호, 외국인등록번호, 주민등록번호, 접수번호, 실명은 적지 마세요.', consent: '위 개인정보를 적지 않았음을 확인해요.', submit: '제보 보내기', cancel: '닫기', placeholderList: '한 줄에 하나씩',
      sent: '제보가 접수됐어요 (검토 대기). 검토 후 관서별 차이 정보에 반영될 수 있어요.', notConfigured: '아직 제보를 받는 서버가 준비되지 않았어요. 작성한 내용은 이 기기에만 임시 저장했고, 어디에도 전송되지 않았어요.', rejected: '보낼 수 없는 내용이 있어요: {errors}', failed: '전송에 실패했어요. 잠시 후 다시 시도해 주세요. 작성한 내용은 이 기기에 임시 저장했어요.',
      errOffice: '관서를 선택하거나 입력해 주세요.', errMonth: '방문 시기를 선택해 주세요.', errOutcome: '달랐던 내용을 한 가지 이상 적어 주세요.', errConsent: '개인정보 미기재 확인이 필요해요.', errIdentifier: '여권번호·등록번호·접수번호로 보이는 숫자가 있어요. 지워 주세요.',
      procedures: { extension: '체류기간 연장', status_change: '체류자격 변경', registration: '외국인등록', card_reissue: '외국인등록증 재발급', residence_report: '체류지 변경신고', registration_info_report: '등록사항 변경신고', reentry: '재입국허가', part_time_work: '시간제 취업', activities_outside_status: '체류자격외 활동', workplace_change: '근무처 변경·추가', workplace_report: '근무처 신고', status_grant: '체류자격 부여', other: '기타' },
    },
    en: {
      title: 'Was your visit different?', intro: 'Tell us what the office actually asked for. After review it can be shown to others as an office-level difference. A single report never changes the guidance and is not shown before review.',
      office: 'Office visited', officeOther: 'Type it', month: 'Month of visit', procedure: 'What was the procedure?', status: 'Status (if you know it)', statusUnknown: 'Not sure',
      expected: 'Documents in the guidance that were NOT requested', requested: 'Documents requested that were NOT in the guidance', feeDiff: 'If the fee or payment differed', processDiff: 'If the appointment or process differed', notes: 'Other notes', evidence: 'I could show a receipt or notice if asked (nothing is uploaded)',
      privacy: 'Do not write passport numbers, residence card numbers, resident registration numbers, case numbers or full names.', consent: 'I confirm none of the above identifiers are included.', submit: 'Send report', cancel: 'Close', placeholderList: 'One per line',
      sent: 'Report received (awaiting review). After review it may appear as an office-level difference.', notConfigured: 'The intake server is not set up yet. Your text was kept only on this device and was not sent anywhere.', rejected: 'Some content cannot be sent: {errors}', failed: 'Sending failed. Try again later. Your text was kept on this device.',
      errOffice: 'Choose or type the office.', errMonth: 'Choose the month of the visit.', errOutcome: 'Describe at least one difference.', errConsent: 'Please confirm no identifiers are included.', errIdentifier: 'Something looks like a passport, card or case number. Please remove it.',
      procedures: { extension: 'Extension of stay', status_change: 'Change of status', registration: 'Foreign resident registration', card_reissue: 'Residence card reissue', residence_report: 'Change-of-address report', registration_info_report: 'Registration-information report', reentry: 'Re-entry permit', part_time_work: 'Part-time work', activities_outside_status: 'Activities outside status', workplace_change: 'Workplace change / addition', workplace_report: 'Workplace report', status_grant: 'Status grant', other: 'Other' },
    }
  };
  var FORBIDDEN = [/\b[A-Z]{1,2}\d{7,8}\b/, /\b\d{6}-?[1-8]\d{6}\b/, /\b\d{4}-?\d{4}-?\d{4}\b/];
  var ENDPOINT = '/api/local-practice/report';
  var DRAFT_KEY = 'visable.local-report.draft';
  function esc(v) { return String(v == null ? '' : v).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; }); }
  function fmt(s, vars) { return String(s || '').replace(/\{(\w+)\}/g, function (_, k) { return vars && vars[k] != null ? vars[k] : ''; }); }
  function t(lang, key, vars) { var p = COPY[lang] || COPY.ko; var v = p[key] != null ? p[key] : COPY.ko[key]; return typeof v === 'string' ? fmt(v, vars) : v; }
  function lines(v) { return String(v || '').split(/\n+/).map(function (s) { return s.trim(); }).filter(Boolean).slice(0, 12); }

  function collect(form, lang) {
    var officeSel = form.querySelector('[name="office"]').value;
    var officeText = form.querySelector('[name="office_other"]').value.trim();
    return {
      schema_version: 1,
      office: officeSel === '__other' ? officeText : officeSel,
      visit_month: form.querySelector('[name="visit_month"]').value,
      procedure: form.querySelector('[name="procedure"]').value,
      status: form.querySelector('[name="status"]').value.trim().toUpperCase() || null,
      status_unknown: form.querySelector('[name="status_unknown"]').checked,
      outcome: {
        document_expected_not_requested: lines(form.querySelector('[name="expected"]').value),
        document_requested_not_expected: lines(form.querySelector('[name="requested"]').value),
        fee_difference: form.querySelector('[name="fee"]').value.trim() || null,
        process_difference: form.querySelector('[name="process"]').value.trim() || null,
      },
      notes: form.querySelector('[name="notes"]').value.trim() || null,
      evidence_available: form.querySelector('[name="evidence"]').checked,
      language: lang,
      consent: form.querySelector('[name="consent"]').checked,
      client_submitted_at: new Date().toISOString(),
    };
  }
  function validate(r, lang) {
    var errors = [];
    if (!r.office || r.office.length < 2) errors.push(t(lang, 'errOffice'));
    if (!/^20[2-3][0-9]-(0[1-9]|1[0-2])$/.test(r.visit_month || '')) errors.push(t(lang, 'errMonth'));
    var o = r.outcome;
    if (!(o.document_expected_not_requested.length || o.document_requested_not_expected.length || o.fee_difference || o.process_difference || r.notes)) errors.push(t(lang, 'errOutcome'));
    if (!r.consent) errors.push(t(lang, 'errConsent'));
    var free = [r.notes, o.fee_difference, o.process_difference].concat(o.document_expected_not_requested, o.document_requested_not_expected).filter(Boolean).join('\n');
    if (FORBIDDEN.some(function (re) { return re.test(free); })) errors.push(t(lang, 'errIdentifier'));
    return errors;
  }

  var api = { COPY: COPY, validate: validate, FORBIDDEN: FORBIDDEN, ENDPOINT: ENDPOINT };
  root.VisableLocalPracticeReport = api;
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  if (typeof document === 'undefined') return;

  var dialog = null, opener = null;
  function offices() { var b = root.VisableStatusGuidance && root.__visableBundle; return b && b.local_practice ? b.local_practice.offices : []; }
  function loadOffices() {
    return fetch('data/local-practice-202609.json').then(function (r) { return r.ok ? r.json() : null; }).then(function (lp) { return lp ? lp.offices : []; }).catch(function () { return []; });
  }
  function monthOptions(lang) {
    var out = ''; var d = new Date();
    for (var i = 0; i < 18; i++) { var y = d.getFullYear(), m = d.getMonth() + 1; var v = y + '-' + (m < 10 ? '0' : '') + m; out += '<option value="' + v + '">' + v + '</option>'; d.setMonth(d.getMonth() - 1); }
    return out;
  }
  function open(detail) {
    var lang = detail.lang === 'en' ? 'en' : 'ko';
    opener = document.activeElement;
    loadOffices().then(function (list) {
      if (!dialog) { dialog = document.createElement('dialog'); dialog.id = 'sgReportDialog'; dialog.className = 'sg-report'; dialog.setAttribute('aria-labelledby', 'sgReportTitle'); document.body.append(dialog); dialog.addEventListener('close', function () { if (opener && opener.isConnected) opener.focus(); }); dialog.addEventListener('keydown', function (e) { if (e.key === 'Escape' || e.key === 'Esc') { e.preventDefault(); e.stopPropagation(); dialog.close(); } }); }
      var procs = t(lang, 'procedures');
      dialog.innerHTML = '<form method="dialog" class="sg-report-form" novalidate>' +
        '<div class="sg-report-head"><h2 id="sgReportTitle">' + esc(t(lang, 'title')) + '</h2><button type="button" class="sg-report-close" data-report-close aria-label="' + esc(t(lang, 'cancel')) + '">✕</button></div>' +
        '<p class="sg-report-intro">' + esc(t(lang, 'intro')) + '</p>' +
        '<label>' + esc(t(lang, 'office')) + '<select name="office" required><option value="">—</option>' + list.map(function (o) { return '<option value="' + esc(o.id) + '"' + (detail.office === o.id ? ' selected' : '') + '>' + esc(lang === 'en' ? o.name_en : o.name_ko) + '</option>'; }).join('') + '<option value="__other">' + esc(t(lang, 'officeOther')) + '</option></select></label>' +
        '<label class="sg-report-other" hidden>' + esc(t(lang, 'officeOther')) + '<input name="office_other" type="text" maxlength="80" autocomplete="off"></label>' +
        '<label>' + esc(t(lang, 'month')) + '<select name="visit_month" required><option value="">—</option>' + monthOptions(lang) + '</select></label>' +
        '<label>' + esc(t(lang, 'procedure')) + '<select name="procedure">' + Object.keys(procs).map(function (k) { return '<option value="' + k + '"' + (detail.procedure === k ? ' selected' : '') + '>' + esc(procs[k]) + '</option>'; }).join('') + '</select></label>' +
        '<div class="sg-report-row"><label>' + esc(t(lang, 'status')) + '<input name="status" type="text" maxlength="12" placeholder="F-6-1" value="' + esc(detail.status || '') + '" autocomplete="off"></label><label class="sg-report-check"><input name="status_unknown" type="checkbox"' + (detail.status ? '' : ' checked') + '> ' + esc(t(lang, 'statusUnknown')) + '</label></div>' +
        '<label>' + esc(t(lang, 'expected')) + '<textarea name="expected" rows="2" placeholder="' + esc(t(lang, 'placeholderList')) + '"></textarea></label>' +
        '<label>' + esc(t(lang, 'requested')) + '<textarea name="requested" rows="2" placeholder="' + esc(t(lang, 'placeholderList')) + '"></textarea></label>' +
        '<label>' + esc(t(lang, 'feeDiff')) + '<input name="fee" type="text" maxlength="300"></label>' +
        '<label>' + esc(t(lang, 'processDiff')) + '<input name="process" type="text" maxlength="300"></label>' +
        '<label>' + esc(t(lang, 'notes')) + '<textarea name="notes" rows="3" maxlength="800"></textarea></label>' +
        '<label class="sg-report-check"><input name="evidence" type="checkbox"> ' + esc(t(lang, 'evidence')) + '</label>' +
        '<p class="sg-report-privacy">' + esc(t(lang, 'privacy')) + '</p>' +
        '<label class="sg-report-check"><input name="consent" type="checkbox" required> ' + esc(t(lang, 'consent')) + '</label>' +
        '<p class="sg-report-status" role="status" aria-live="polite"></p>' +
        '<div class="sg-report-actions"><button type="button" class="sg-btn" data-report-close>' + esc(t(lang, 'cancel')) + '</button><button type="submit" class="sg-btn sg-btn-primary">' + esc(t(lang, 'submit')) + '</button></div></form>';
      var form = dialog.querySelector('form');
      form.querySelector('[name="office"]').addEventListener('change', function (e) { form.querySelector('.sg-report-other').hidden = e.target.value !== '__other'; });
      dialog.querySelectorAll('[data-report-close]').forEach(function (b) { b.addEventListener('click', function () { dialog.close(); }); });
      form.addEventListener('submit', function (e) {
        e.preventDefault();
        var status = form.querySelector('.sg-report-status');
        var report = collect(form, lang);
        var errors = validate(report, lang);
        if (errors.length) { status.textContent = errors.join(' '); status.className = 'sg-report-status sg-report-error'; return; }
        try { localStorage.setItem(DRAFT_KEY, JSON.stringify(report)); } catch (err) { /* ignore */ }
        var submitBtn = form.querySelector('button[type="submit"]'); submitBtn.disabled = true;
        fetch(ENDPOINT, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(report) })
          .then(function (res) { return res.json().catch(function () { return {}; }).then(function (d) { return { status: res.status, data: d }; }); })
          .then(function (r) {
            submitBtn.disabled = false;
            if (r.data && r.data.ok) { status.textContent = t(lang, 'sent'); status.className = 'sg-report-status sg-report-ok'; try { localStorage.removeItem(DRAFT_KEY); } catch (err) { /* ignore */ } return; }
            if (r.status === 503 || r.status === 404 || r.status === 405 || (r.data && r.data.status === 'NOT_CONFIGURED')) { status.textContent = t(lang, 'notConfigured'); status.className = 'sg-report-status sg-report-warn'; return; }
            if (r.status === 422) { status.textContent = t(lang, 'rejected', { errors: (r.data.errors || []).join(', ') }); status.className = 'sg-report-status sg-report-error'; return; }
            status.textContent = t(lang, 'failed'); status.className = 'sg-report-status sg-report-warn';
          })
          .catch(function () { submitBtn.disabled = false; status.textContent = t(lang, 'failed'); status.className = 'sg-report-status sg-report-warn'; });
      });
      if (typeof dialog.showModal === 'function') dialog.showModal(); else dialog.setAttribute('open', '');
      var first = dialog.querySelector('select, input, button'); if (first) first.focus();
    });
  }
  document.addEventListener('visable:local-report', function (e) { open(e.detail || {}); });
})(typeof globalThis !== 'undefined' ? globalThis : this);
