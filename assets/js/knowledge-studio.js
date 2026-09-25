/**
 * Waymaker Knowledge Studio (operator UI).
 *
 * Talks only to the operator-authenticated API under /api/knowledge/studio.
 * Every value from the API is rendered with textContent (never innerHTML), so
 * sanitized user queries, source excerpts and operator notes cannot inject
 * markup. The operator token is kept in this tab's sessionStorage only.
 */
(function (global) {
  'use strict';

  var doc = global.document;
  var TOKEN_KEY = 'waymaker.ks.token';
  var API = '/api/knowledge/studio';
  var state = { token: '', view: 'overview', sources: null, selectedTask: null };

  // ------------------------------------------------------------------ utils
  function h(tag, attrs, children) {
    var el = doc.createElement(tag);
    Object.keys(attrs || {}).forEach(function (k) {
      var v = attrs[k];
      if (v === null || v === undefined || v === false) return;
      if (k === 'text') el.textContent = String(v);
      else if (k === 'on') Object.keys(v).forEach(function (ev) { el.addEventListener(ev, v[ev]); });
      else if (k === 'className') el.className = v;
      else el.setAttribute(k, v === true ? '' : String(v));
    });
    (children || []).forEach(function (c) {
      if (c === null || c === undefined || c === false) return;
      el.appendChild(typeof c === 'string' || typeof c === 'number' ? doc.createTextNode(String(c)) : c);
    });
    return el;
  }
  function $(id) { return doc.getElementById(id); }
  function clear(el) { while (el.firstChild) el.removeChild(el.firstChild); return el; }
  function status(msg) { $('ks-status').textContent = msg || ''; }
  function store(key, value) {
    try { if (value === undefined) return global.sessionStorage.getItem(key); if (value === null) global.sessionStorage.removeItem(key); else global.sessionStorage.setItem(key, value); } catch (e) { /* storage unavailable: token lives in memory */ }
    return null;
  }
  function url(path) {
    return (global.VisableBackend && global.VisableBackend.url) ? global.VisableBackend.url(path) : path;
  }
  function api(path, opts) {
    opts = opts || {};
    var init = { method: opts.method || 'GET', headers: { Authorization: 'Bearer ' + state.token } };
    if (opts.body !== undefined) { init.headers['Content-Type'] = 'application/json'; init.body = JSON.stringify(opts.body); }
    return global.fetch(url(API + path), init).then(function (res) {
      return res.json().catch(function () { return {}; }).then(function (data) {
        if (!res.ok) {
          var detail = (data && data.detail) || {};
          var err = new Error(detail.message || detail.error || ('HTTP ' + res.status));
          err.status = res.status; err.detail = detail;
          throw err;
        }
        return data;
      });
    });
  }
  function fail(err) {
    if (err && err.status === 401) { signOut('토큰이 유효하지 않습니다.'); return; }
    status('오류: ' + ((err && err.message) || err));
  }

  var STATE_TONE = { PUBLISHED: 'ok', VERIFIED: 'ok', HUMAN_REVIEWED: 'ok', HUMAN_REVIEW_REQUIRED: 'warn',
    AI_EXTRACTED: 'warn', DRAFT: 'warn', REJECTED: 'bad', SUPERSEDED: '', WITHDRAWN: 'bad',
    open: 'warn', needs_evidence: 'warn', resolved: 'ok', rejected: 'bad', investigating: 'warn', wont_fix: '',
    ADDED: 'warn', REMOVED: 'bad', CHANGED: 'warn', UNCHANGED: 'ok', pass: 'ok', fail: 'bad',
    active: 'ok', staged: 'warn', superseded: '', withdrawn: 'bad', approved: 'ok', needs_review: 'warn',
    draft: 'warn', retired: '', current: 'ok', refresh_due: 'warn', unavailable: 'bad' };
  // Short operator labels; the stable code stays available as the title.
  var STATE_LABEL = { PUBLISHED: '게시', VERIFIED: '검증됨', HUMAN_REVIEWED: '검토 완료', HUMAN_REVIEW_REQUIRED: '검토 필요',
    AI_EXTRACTED: 'AI 추출', DRAFT: '초안', REJECTED: '반려', SUPERSEDED: '대체됨', WITHDRAWN: '철회',
    ADDED: '추가', REMOVED: '삭제', CHANGED: '변경', UNCHANGED: '동일' };
  function badge(text) {
    return h('span', { className: 'ks-badge', 'data-tone': STATE_TONE[text] || '', title: text || '',
      text: STATE_LABEL[text] || text || '—' });
  }

  function table(caption, columns, rows, onRow) {
    if (!rows.length) return h('p', { className: 'ks-empty', text: caption + ': 항목이 없습니다.' });
    var head = h('tr', {}, columns.map(function (c) { return h('th', { scope: 'col', text: c[0] }); }));
    var body = rows.map(function (row) {
      var tr = h('tr', onRow ? { className: 'ks-row-clickable', tabindex: '0' } : {},
        columns.map(function (c) {
          var v = c[1](row);
          return h('td', { className: c[2] || '' }, [v instanceof global.Node ? v : String(v === null || v === undefined ? '—' : v)]);
        }));
      if (onRow) {
        tr.addEventListener('click', function () { onRow(row, tr); });
        tr.addEventListener('keydown', function (e) { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); onRow(row, tr); } });
      }
      return tr;
    });
    return h('div', { className: 'ks-table-wrap' }, [h('table', {}, [h('caption', { text: caption }), h('thead', {}, [head]), h('tbody', {}, body)])]);
  }
  function kv(pairs) {
    var dl = h('dl', { className: 'ks-kv' });
    pairs.forEach(function (p) {
      if (p[1] === undefined) return;
      dl.appendChild(h('dt', { text: p[0] }));
      dl.appendChild(h('dd', {}, [p[1] instanceof global.Node ? p[1] : String(p[1] === null || p[1] === '' ? '—' : p[1])]));
    });
    return dl;
  }
  function pages(c) { if (!c || !c.page_start) return ''; return c.page_end && c.page_end !== c.page_start ? c.page_start + '-' + c.page_end : String(c.page_start); }
  function citeText(c) { return c ? (c.source_title + ' ' + c.version_label + (pages(c) ? ', p. ' + pages(c) : '') + (c.section_title ? ' — ' + c.section_title : '')) : '—'; }
  function field(label, input) { return h('div', { className: 'ks-field' }, [h('label', { 'for': input.id, text: label }), input]); }
  function select(id, options, value) {
    var s = h('select', { id: id });
    options.forEach(function (o) { var opt = h('option', { value: o[0], text: o[1] }); if (o[0] === value) opt.selected = true; s.appendChild(opt); });
    return s;
  }

  // --------------------------------------------------------------- dialog
  function confirmDialog(title, bodyNodes, confirmLabel) {
    var dlg = $('ks-dialog');
    $('ks-dialog-title').textContent = title;
    var body = clear($('ks-dialog-body'));
    bodyNodes.forEach(function (n) { body.appendChild(n); });
    $('ks-dialog-confirm').textContent = confirmLabel || '확인';
    return new Promise(function (resolve) {
      function done(ok) {
        $('ks-dialog-cancel').removeEventListener('click', onCancel);
        dlg.removeEventListener('close', onClose);
        resolve(ok);
      }
      function onCancel() { dlg.close('cancel'); }
      function onClose() { done(dlg.returnValue === 'confirm'); }
      $('ks-dialog-cancel').addEventListener('click', onCancel);
      dlg.addEventListener('close', onClose);
      if (dlg.showModal) dlg.showModal(); else dlg.setAttribute('open', '');
      var first = body.querySelector('input, textarea, select');
      (first || $('ks-dialog-confirm')).focus();
    });
  }

  // --------------------------------------------------------------- views
  var views = {};

  views.overview = function (root) {
    return api('/overview').then(function (o) {
      var m = o.metrics || {};
      root.appendChild(h('h1', { text: '개요' }));
      if (!o.storage.durable) {
        root.appendChild(h('p', { className: 'ks-banner ks-banner-danger', role: 'note',
          text: '저장소가 영구적이지 않습니다(인메모리). 재배포 시 운영자 변경이 사라집니다. WAYMAKER_KNOWLEDGE_DB를 영구 볼륨으로 설정하세요.' }));
      }
      var metrics = [['검토 대기 지식', m.pending_review], ['열린 검토 작업', m.open_review_tasks], ['열린 충돌', m.open_conflicts],
        ['미해결 커버리지 공백', m.unresolved_gaps], ['신규 미지 클러스터(7일)', m.new_unknown_clusters_7d],
        ['게시된 지식', m.published_facts], ['대체된 지식', m.superseded_facts],
        ['실패한 평가', m.failing_eval_cases === null ? '실행 전' : m.failing_eval_cases],
        ['갱신 필요 출처', m.sources_needing_refresh], ['사용자 피드백(7일)', m.feedback_7d]];
      root.appendChild(h('dl', { className: 'ks-metrics' }, metrics.map(function (x) {
        return h('div', { className: 'ks-metric' }, [h('dt', { text: x[0] }), h('dd', { text: x[1] === undefined ? '—' : x[1] })]);
      })));
      (o.sources_needing_refresh || []).forEach(function (s) {
        root.appendChild(h('p', { className: 'ks-banner', role: 'note' }, [
          '출처 갱신 필요: ' + s.title + ' — 게시된 지식이 대체된 판(' + s.stale_editions.join(', ') + ')을 인용합니다. 현재 승인된 판: ' +
          (s.current_editions.join(', ') || '없음') + '. 새 판 기준으로 재확인하세요.']));
      });
      root.appendChild(h('h2', { text: '다음에 검토할 항목' }));
      return api('/review-queue?limit=5').then(function (q) {
        root.appendChild(table('우선순위 상위 5건 (점수 근거는 검토 화면에 표시)', [
          ['우선순위', function (t) { return t.priority_score; }, 'ks-num'],
          ['종류', function (t) { return taskKind(t.task_kind); }],
          ['대상', function (t) { return t.variant_key; }, 'ks-mono'],
          ['제안 값', function (t) { return t.value_text; }, 'ks-ko']
        ], q.tasks, function (t) { go('queue', { task: t.task_id }); }));
      });
    });
  };

  function taskKind(k) {
    return { new_fact: '신규', update_fact: '변경(새 판)', conflict: '충돌', source_refresh: '새 판 재확인', gap_resolution: '공백 해결' }[k] || k;
  }

  views.queue = function (root, params) {
    root.appendChild(h('h1', { text: '검토 대기열' }));
    var filterStatus = select('ks-q-status', [['open', '열림'], ['needs_evidence', '근거 필요'], ['resolved', '해결'], ['rejected', '반려'], ['all', '전체']], params.status || 'open');
    var filterCode = h('input', { id: 'ks-q-code', placeholder: '예: D-2', value: params.status_code || '' });
    var apply = h('button', { type: 'button', className: 'ks-btn', text: '적용' });
    root.appendChild(h('div', { className: 'ks-filters' }, [field('상태', filterStatus), field('체류자격', filterCode), apply]));
    apply.addEventListener('click', function () { go('queue', { status: filterStatus.value, status_code: filterCode.value.trim() }); });
    var split = h('div', { className: 'ks-split' });
    var list = h('div'); var detail = h('div', { className: 'ks-panel', id: 'ks-task-detail' }, [h('p', { className: 'ks-muted', text: '항목을 선택하면 제안·현재 값, 출처, 근거, 영향이 표시됩니다.' })]);
    split.appendChild(list); split.appendChild(detail); root.appendChild(split);
    var qs = '?status=' + encodeURIComponent(filterStatus.value) + (filterCode.value.trim() ? '&status_code=' + encodeURIComponent(filterCode.value.trim()) : '');
    return api('/review-queue' + qs).then(function (q) {
      list.appendChild(table('검토 작업 ' + q.tasks.length + '건', [
        ['점수', function (t) { return t.priority_score; }, 'ks-num'],
        ['종류', function (t) { return taskKind(t.task_kind); }],
        ['자격·절차', function (t) { return (t.subcode || t.status_code) + ' · ' + t.procedure; }],
        ['제안 값', function (t) { return t.value_text; }, 'ks-ko'],
        ['상태', function (t) { return badge(t.lifecycle_state); }]
      ], q.tasks, function (t, tr) {
        Array.prototype.forEach.call(tr.parentNode.children, function (r) { r.removeAttribute('aria-selected'); });
        tr.setAttribute('aria-selected', 'true');
        renderTask(detail, t.task_id).then(function () {
          // On phones the detail sits below the list: bring it into view and
          // move focus to its heading so keyboard / screen-reader users follow.
          var heading = detail.querySelector('h2');
          if (heading) { heading.tabIndex = -1; heading.focus({ preventScroll: true }); }
          if (global.matchMedia && global.matchMedia('(max-width: 860px)').matches && detail.scrollIntoView) detail.scrollIntoView();
        });
      }));
      if (params.task) renderTask(detail, params.task);
    });
  };

  function renderTask(panel, taskId) {
    clear(panel).appendChild(h('p', { className: 'ks-muted', text: '불러오는 중…' }));
    return api('/review-queue/' + encodeURIComponent(taskId)).then(function (d) {
      clear(panel);
      var f = d.proposed; var cur = d.current_published; var cit = (f.citations || [])[0];
      panel.appendChild(h('h2', { text: '검토: ' + f.value_text }));
      panel.appendChild(kv([
        ['상태', badge(f.lifecycle_state)], ['대상', f.variant_key], ['속성', f.property],
        ['출처(판·쪽)', citeText(cit)], ['출처 판 검토 상태', cit ? cit.content_review_state : '—'],
        ['출처 판 상태', cit ? cit.version_status : '—'], ['위치', cit ? cit.locator : '—'],
        ['생성 경로', f.origin + ' (' + f.created_by_kind + ')'], ['추출 경고', (f.extraction_warnings || []).join(' / ') || '없음']
      ]));
      if ((d.conflicts || []).length) {
        panel.appendChild(h('p', { className: 'ks-banner ks-banner-danger', role: 'alert',
          text: '충돌 ' + d.conflicts.length + '건: 해결 전에는 승인·게시할 수 없습니다. [충돌] 탭에서 두 출처를 비교해 해결하세요.' }));
      }
      panel.appendChild(h('h2', { text: '현재 게시 값과 비교' }));
      if (d.diff && d.diff.current) {
        var rows = [['값', 'value_text'], ['요건 수준', 'requirement_level'], ['조건', 'condition_kind'], ['조건 설명', 'condition_text'], ['효력 시작', 'effective_from'], ['출처', 'source'], ['쪽', 'pages']];
        var changed = d.diff.changed_fields || [];
        panel.appendChild(h('div', { className: 'ks-table-wrap' }, [h('table', { className: 'ks-diff' }, [
          h('caption', { text: '변경된 항목은 강조 표시 + "변경" 표기' }),
          h('thead', {}, [h('tr', {}, [h('th', { scope: 'col', text: '항목' }), h('th', { scope: 'col', text: '현재 게시' }), h('th', { scope: 'col', text: '제안' })])]),
          h('tbody', {}, rows.map(function (r) {
            var isChanged = changed.indexOf(r[1]) >= 0;
            return h('tr', {}, [h('th', { scope: 'row', text: r[0] + (isChanged ? ' (변경)' : '') }),
              h('td', { className: isChanged ? 'ks-changed ks-ko' : 'ks-ko', text: d.diff.current[r[1]] || '—' }),
              h('td', { className: isChanged ? 'ks-changed ks-ko' : 'ks-ko', text: d.diff.proposed[r[1]] || '—' })]);
          }))
        ])]));
      } else {
        panel.appendChild(h('p', { className: 'ks-muted', text: '같은 항목의 게시된 값이 없습니다(신규 지식).' }));
      }
      var im = d.impact || {};
      panel.appendChild(h('h2', { text: '영향' }));
      panel.appendChild(kv([['영향받는 평가', (im.affected_eval_count || 0) + '건' + (im.affected_eval_cases && im.affected_eval_cases.length ? ' — ' + im.affected_eval_cases.map(function (c) { return c.case_key; }).join(', ') : '')],
        ['게시 시 대체', (im.would_supersede || []).length + '건'], ['회귀 평가 재실행 필요', im.requires_regression_rerun ? '예' : '아니오']]));
      var pf = d.task.priority_factors || {};
      panel.appendChild(h('p', { className: 'ks-muted', text: '우선순위 ' + d.task.priority_score + ' = 공백 빈도 ' + (pf.gap_frequency || 0) + ', 피드백 ' + (pf.user_feedback || 0) +
        ', 절차 위험 ' + (pf.procedure_risk || 0) + ', 출처 권위 순위 ' + (pf.source_authority_rank || '—') + ', 영향 평가 ' + (pf.affected_evals || 0) + ', 충돌 ' + (pf.open_conflicts || 0) + ', 경과일 ' + (pf.age_days || 0) }));
      var evidence = h('div', {}, [h('p', { className: 'ks-muted', text: '근거 불러오는 중…' })]);
      panel.appendChild(h('h2', { text: '출처 근거' }));
      panel.appendChild(evidence);
      api('/evidence/' + encodeURIComponent(f.fact_id)).then(function (ev) {
        clear(evidence);
        (ev.evidence || []).forEach(function (e) {
          evidence.appendChild(h('p', { className: 'ks-muted', text: e.source + (e.pages ? ' · p. ' + e.pages : '') + ' · ' +
            ({ parsed_page_text: '파싱된 원문 페이지', legacy_verified_excerpt: '검증된 발췌(기존)', citation_excerpt: '인용 발췌', none: '근거 텍스트 없음' }[e.kind] || e.kind) +
            (e.kind !== 'none' ? (e.match_found ? ' · 문구 일치 확인' : ' · 문구 불일치 — 직접 확인 필요') : '') }));
          if (e.text) evidence.appendChild(h('pre', { className: 'ks-evidence', lang: 'ko', text: e.text }));
        });
      }).catch(function () { clear(evidence).appendChild(h('p', { className: 'ks-error', text: '근거를 불러오지 못했습니다.' })); });
      panel.appendChild(actionBar(f, d.task));
      panel.appendChild(h('h2', { text: '감사 기록' }));
      panel.appendChild(table('이 지식의 변경 이력', [
        ['시각', function (a) { return a.at; }, 'ks-mono'], ['행위자', function (a) { return a.actor + ' (' + a.actor_kind + ')'; }],
        ['동작', function (a) { return a.action; }], ['사유', function (a) { return a.reason; }, 'ks-ko']], d.audit || []));
    }).catch(function (err) { clear(panel); fail(err); });
  }

  function actionBar(f, task) {
    var bar = h('div', { className: 'ks-actions', role: 'group', 'aria-label': '검토 동작' });
    function btn(label, action, cls, needsReason) {
      var b = h('button', { type: 'button', className: 'ks-btn ' + (cls || ''), text: label });
      b.addEventListener('click', function () { runAction(f, action, label, needsReason); });
      bar.appendChild(b);
    }
    var s = f.lifecycle_state;
    if (s === 'AI_EXTRACTED' || s === 'DRAFT') btn('검토 시작', 'start_review');
    if (s === 'HUMAN_REVIEW_REQUIRED') btn('승인(검토 완료)', 'approve', 'ks-btn-primary');
    if (s === 'HUMAN_REVIEWED') btn('검증', 'verify', 'ks-btn-primary');
    if (s === 'VERIFIED') btn('게시', 'publish', 'ks-btn-primary');
    if (['DRAFT', 'AI_EXTRACTED', 'HUMAN_REVIEW_REQUIRED', 'HUMAN_REVIEWED', 'VERIFIED'].indexOf(s) >= 0) {
      btn('근거 더 필요', 'needs_evidence', '', true);
      btn('수정(새 버전)', 'edit');
      btn('반려', 'reject', 'ks-btn-danger', true);
    }
    return bar;
  }

  function runAction(f, action, label, needsReason) {
    var reason = h('textarea', { id: 'ks-action-reason', required: needsReason || action === 'publish' ? true : null });
    var nodes = [h('p', { className: 'ks-ko', text: f.value_text })];
    var value = null;
    if (action === 'edit') {
      value = h('textarea', { id: 'ks-edit-value' }); value.value = f.value_text;
      nodes.push(field('새 값(원문 표기 유지)', value));
    }
    if (action === 'publish') nodes.push(h('p', { className: 'ks-banner', text: '게시하면 같은 항목의 현재 게시 값이 대체되고 Waymaker 답변에 즉시 반영됩니다.' }));
    nodes.push(field(needsReason || action === 'publish' ? '사유 (필수)' : '사유', reason));
    return confirmDialog(label, nodes, label).then(function (ok) {
      if (!ok) return;
      if ((needsReason || action === 'publish') && !reason.value.trim()) { status('사유를 입력해야 합니다.'); return; }
      var body = { action: action, reason: reason.value.trim() };
      if (value) body.value_text = value.value.trim();
      status(label + ' 처리 중…');
      return api('/facts/' + encodeURIComponent(f.fact_id) + '/actions', { method: 'POST', body: body }).then(function (res) {
        status(label + ' 완료: ' + res.fact.lifecycle_state);
        return render();
      });
    }).catch(fail);
  }

  views.facts = function (root, params) {
    root.appendChild(h('h1', { text: '지식' }));
    var st = select('ks-f-state', [['PUBLISHED', '게시'], ['SUPERSEDED', '대체됨'], ['HUMAN_REVIEW_REQUIRED', '검토 필요'], ['AI_EXTRACTED', 'AI 추출'], ['REJECTED', '반려'], ['all', '전체']], params.state || 'PUBLISHED');
    var code = h('input', { id: 'ks-f-code', placeholder: '예: D-2', value: params.status_code || '' });
    var apply = h('button', { type: 'button', className: 'ks-btn', text: '적용' });
    var add = h('button', { type: 'button', className: 'ks-btn ks-btn-primary', text: '지식 직접 추가' });
    root.appendChild(h('div', { className: 'ks-filters' }, [field('상태', st), field('체류자격', code), apply, add]));
    apply.addEventListener('click', function () { go('facts', { state: st.value, status_code: code.value.trim() }); });
    add.addEventListener('click', function () { manualFactDialog(); });
    var qs = '?state=' + encodeURIComponent(st.value) + (code.value.trim() ? '&status_code=' + encodeURIComponent(code.value.trim()) : '');
    return api('/facts' + qs).then(function (res) {
      root.appendChild(table('지식 ' + res.facts.length + '건', [
        ['대상', function (f) { return f.variant_key; }, 'ks-mono'],
        ['속성', function (f) { return f.property; }],
        ['값(원문)', function (f) { return f.value_text; }, 'ks-ko'],
        ['조건', function (f) { return f.condition_kind === 'always' ? '항상' : (f.condition_text || f.condition_kind); }, 'ks-ko'],
        ['출처', function (f) { return citeText((f.citations || [])[0]); }, 'ks-ko'],
        ['검토자', function (f) { return f.verified_by ? f.verified_by + ' (' + (f.reviewer_kind === 'legacy_repository_verification' ? '기존 저장소 검증' : '운영자') + ')' : '—'; }],
        ['상태', function (f) { return badge(f.lifecycle_state); }]
      ], res.facts));
    });
  };

  function manualFactDialog() {
    return loadSources().then(function (sources) {
      var editions = [];
      sources.forEach(function (s) { s.versions.forEach(function (v) { editions.push([v.source_version_id, s.title_ko + ' ' + v.version_label + ' (' + v.edition_ref + ', ' + v.status + ')']); }); });
      var f = {
        status: h('input', { id: 'ks-m-status', placeholder: 'H-2', required: true }),
        subcode: h('input', { id: 'ks-m-sub', placeholder: '(선택) H-2-5' }),
        procedure: select('ks-m-proc', [['extension', '체류기간 연장'], ['status_change', '체류자격 변경'], ['registration', '외국인등록'], ['workplace_change', '근무처 변경·추가'], ['activities_outside_status', '체류자격외 활동'], ['reentry', '재입국'], ['visa_issuance', '사증발급']], 'extension'),
        property: select('ks-m-prop', [['required_document', '제출서류'], ['eligibility_rule', '요건'], ['fee', '수수료'], ['deadline', '기한'], ['online_service', '전자민원'], ['reporting_duty', '신고의무'], ['exception', '예외'], ['procedural_note', '유의사항']], 'required_document'),
        value: h('textarea', { id: 'ks-m-value', required: true }),
        level: select('ks-m-level', [['common', '기본'], ['required', '증빙'], ['conditional', '해당 시'], ['additional', '추가 요청 가능']], 'required'),
        condition: h('input', { id: 'ks-m-cond', placeholder: '해당 시 조건(원문)' }),
        edition: select('ks-m-edition', editions, editions.length ? editions[0][0] : ''),
        page: h('input', { id: 'ks-m-page', type: 'number', min: '1', required: true }),
        section: h('input', { id: 'ks-m-section', placeholder: '매뉴얼 절 제목' }),
        locator: h('input', { id: 'ks-m-loc', placeholder: '예: 다. 제출서류' })
      };
      var nodes = [h('p', { className: 'ks-muted', text: '직접 추가한 지식도 검토 → 검증 → 게시를 거칩니다. 출처 판과 쪽수는 필수입니다.' }),
        h('div', { className: 'ks-grid' }, [field('체류자격', f.status), field('세부약호', f.subcode), field('절차', f.procedure), field('속성', f.property)]),
        field('값(출처 원문 그대로)', f.value), h('div', { className: 'ks-grid' }, [field('요건 수준', f.level), field('조건', f.condition)]),
        field('출처 판', f.edition), h('div', { className: 'ks-grid' }, [field('쪽', f.page), field('절', f.section), field('위치', f.locator)])];
      return confirmDialog('지식 직접 추가', nodes, '검토 대기열에 추가').then(function (ok) {
        if (!ok) return;
        var level = f.level.value;
        var body = { status_code: f.status.value.trim().toUpperCase(), subcode: f.subcode.value.trim().toUpperCase() || null,
          procedure: f.procedure.value, property: f.property.value, value_text: f.value.value.trim(),
          requirement_level: f.property.value === 'required_document' ? level : null,
          condition_kind: level === 'conditional' ? 'conditional' : 'always', condition_text: f.condition.value.trim(),
          section_title: f.section.value.trim(),
          location: { source_version_id: f.edition.value, page_start: Number(f.page.value) || null, section_title: f.section.value.trim(), locator: f.locator.value.trim() } };
        return api('/facts', { method: 'POST', body: body }).then(function (res) {
          status('추가됨: ' + res.result.action + ' — 검토 대기열에서 확인하세요.');
          go('queue', {});
        }).catch(function (err) {
          var errs = (err.detail && err.detail.errors) || [];
          status('검증 실패: ' + (errs.map(function (e) { return e.code + ' ' + e.message; }).join('; ') || err.message));
        });
      });
    }).catch(fail);
  }

  views.conflicts = function (root) {
    root.appendChild(h('h1', { text: '충돌' }));
    root.appendChild(h('p', { className: 'ks-muted', text: '같은 항목에 대해 서로 다른 값이 제안·게시된 경우입니다. 먼저 조회된 쪽을 고르지 않습니다. 해결 전에는 양쪽 모두 승인·게시할 수 없습니다.' }));
    return api('/conflicts').then(function (res) {
      if (!res.conflicts.length) { root.appendChild(h('p', { className: 'ks-empty', text: '열린 충돌이 없습니다.' })); return; }
      res.conflicts.forEach(function (c) {
        var panel = h('section', { className: 'ks-panel', 'aria-label': '충돌 ' + c.slot_key });
        panel.appendChild(h('h2', {}, [c.conflict_kind + ' ', badge(c.status)]));
        panel.appendChild(h('p', { className: 'ks-mono', text: c.slot_key }));
        var sides = [['A', c.fact_a], ['B', c.fact_b]];
        panel.appendChild(table('두 값 비교', [['쪽', function (x) { return x[0]; }], ['값', function (x) { return x[1].value_text; }, 'ks-ko'],
          ['조건', function (x) { return x[1].condition_kind; }], ['출처', function (x) { return (x[1].source.title || '') + ' ' + (x[1].source.version || '') + (x[1].source.pages ? ', p. ' + x[1].source.pages : ''); }, 'ks-ko'],
          ['권위', function (x) { return x[1].authority_type; }], ['상태', function (x) { return badge(x[1].lifecycle_state); }]], sides));
        var bar = h('div', { className: 'ks-actions', role: 'group', 'aria-label': '충돌 해결' });
        [['A 유지', c.fact_a_id], ['B 유지', c.fact_b_id], ['충돌 아님(기각)', null]].forEach(function (opt) {
          var b = h('button', { type: 'button', className: 'ks-btn', text: opt[0] });
          b.addEventListener('click', function () {
            var reason = h('textarea', { id: 'ks-c-reason', required: true });
            confirmDialog(opt[0], [h('p', { className: 'ks-muted', text: opt[1] ? '다른 쪽이 검토 전이면 반려됩니다. 게시된 값은 그대로 남습니다.' : '두 값이 서로 모순되지 않는 경우에만 기각하세요.' }), field('근거 (필수)', reason)], opt[0]).then(function (ok) {
              if (!ok) return;
              if (!reason.value.trim()) { status('근거를 입력해야 합니다.'); return; }
              return api('/conflicts/' + encodeURIComponent(c.conflict_id) + '/resolve', { method: 'POST', body: { keep_fact_id: opt[1], reason: reason.value.trim() } })
                .then(function () { status('충돌 처리 완료'); return render(); });
            }).catch(fail);
          });
          bar.appendChild(b);
        });
        panel.appendChild(bar);
        root.appendChild(panel);
      });
    });
  };

  function loadSources() {
    if (state.sources) return Promise.resolve(state.sources);
    return api('/sources').then(function (r) { state.sources = r.sources; return r.sources; });
  }

  views.sources = function (root) {
    root.appendChild(h('h1', { text: '출처·버전' }));
    state.sources = null;
    return loadSources().then(function (sources) {
      sources.forEach(function (s) {
        root.appendChild(h('h2', {}, [s.title_ko + ' ', badge(s.refresh_state)]));
        root.appendChild(table(s.source_key + ' — 판별 상태', [
          ['판', function (v) { return v.version_label; }], ['식별자', function (v) { return v.edition_ref; }, 'ks-mono'],
          ['상태', function (v) { return badge(v.status); }], ['내용 검토', function (v) { return badge(v.content_review_state); }],
          ['효력 시작', function (v) { return v.effective_from || '미상'; }], ['게시 지식', function (v) { return v.published_fact_count; }, 'ks-num'],
          ['검토 대기', function (v) { return v.pending_fact_count; }, 'ks-num']], s.versions));
      });
      var stay = sources.filter(function (s) { return s.source_key === 'stay_guide_manual'; })[0] || sources[0];
      if (!stay) return;
      var opts = stay.versions.map(function (v) { return [v.source_version_id, v.version_label + ' · ' + v.edition_ref]; });
      var from = select('ks-d-from', opts, (stay.versions.filter(function (v) { return v.published_fact_count; })[0] || {}).source_version_id);
      var to = select('ks-d-to', opts, (stay.versions.filter(function (v) { return v.pending_fact_count; })[0] || stay.versions[0]).source_version_id);
      var code = h('input', { id: 'ks-d-code', value: 'D-2' });
      var run = h('button', { type: 'button', className: 'ks-btn ks-btn-primary', text: '비교' });
      var out = h('div', { id: 'ks-diff-out' });
      root.appendChild(h('h2', { text: '판 비교 (결정적 비교: 추가 · 삭제 · 변경 · 동일)' }));
      root.appendChild(h('div', { className: 'ks-filters' }, [field('이전 판', from), field('새 판', to), field('체류자격', code), run]));
      root.appendChild(out);
      run.addEventListener('click', function () {
        clear(out);
        api('/diff?from_version=' + encodeURIComponent(from.value) + '&to_version=' + encodeURIComponent(to.value) + '&status_code=' + encodeURIComponent(code.value.trim()))
          .then(function (d) {
            var sm = d.summary;
            out.appendChild(h('p', { text: d.from.version + ' → ' + d.to.version + ': 추가 ' + sm.ADDED + ' · 삭제 ' + sm.REMOVED + ' · 변경 ' + sm.CHANGED + ' · 동일 ' + sm.UNCHANGED }));
            out.appendChild(table('변경 기록', [
              ['변경', function (r) { return badge(r.change); }],
              ['대상', function (r) { return (r.subcode || r.status_code) + ' · ' + r.procedure; }],
              ['이전', function (r) { return r.from ? r.from.value_text + ' [' + (r.from.requirement_level || '') + ']' : '—'; }, 'ks-ko'],
              ['새 판', function (r) { return r.to ? r.to.value_text + ' [' + (r.to.requirement_level || '') + ']' : '—'; }, 'ks-ko'],
              ['변경 필드', function (r) { return (r.changed_fields || []).join(', ') || '—'; }],
              ['영향 평가', function (r) { return (r.affected_eval_cases || []).length; }, 'ks-num']], d.records));
          }).catch(fail);
      });
      var statuses = h('input', { id: 'ks-i-status', value: 'D-2', placeholder: 'D-2, E-7' });
      var mode = select('ks-i-mode', [['dry_run', '미리보기(dry-run)'], ['apply', '적용(검토 대기열에 추가)']], 'dry_run');
      var ingest = h('button', { type: 'button', className: 'ks-btn', text: '가져오기 실행' });
      var report = h('div');
      root.appendChild(h('h2', { text: '새 판 가져오기 (2026.9 체류 안내 — 검토 전 원본)' }));
      root.appendChild(h('p', { className: 'ks-muted', text: '가져온 항목은 자동 게시되지 않습니다. 모두 검토 대기열로 들어갑니다. 같은 판을 다시 가져와도 중복이 생기지 않습니다.' }));
      root.appendChild(h('div', { className: 'ks-filters' }, [field('체류자격(쉼표 구분)', statuses), field('모드', mode), ingest]));
      root.appendChild(report);
      ingest.addEventListener('click', function () {
        clear(report);
        var list = statuses.value.split(',').map(function (x) { return x.trim().toUpperCase(); }).filter(Boolean);
        api('/ingest', { method: 'POST', body: { adapter: 'status_guidance', mode: mode.value, statuses: list } }).then(function (rep) {
          var sm = rep.summary;
          report.appendChild(h('p', { text: '결과 (' + rep.mode + '): ' + Object.keys(sm).map(function (k) { return k + ' ' + sm[k]; }).join(' · ') }));
          report.appendChild(table('항목별 분류', [['#', function (i) { return i.index; }, 'ks-num'], ['분류', function (i) { return badge(i.action); }],
            ['값', function (i) { return i.value_text; }, 'ks-ko'], ['경고·오류', function (i) { return (i.errors || []).map(function (e) { return e.code; }).concat(i.warnings || []).join(' / '); }, 'ks-ko']], rep.items));
          state.sources = null;
        }).catch(fail);
      });
    });
  };

  function gapsView(root, kind, title) {
    root.appendChild(h('h1', { text: title }));
    root.appendChild(h('p', { className: 'ks-muted', text: kind === 'unknown'
      ? '검증된 지식이 없어 제한 안내로 답한 질문 묶음입니다. 사용자 정보가 빠진 질문(예: 체류자격 미기재)은 지식 공백이 아니므로 여기에 들어오지 않습니다.'
      : '답변 품질 신호(지식 없음·충돌·사용자 신고 등)를 체류자격·절차·의도·사유별로 묶었습니다. 질문 원문은 저장하지 않고 개인정보를 가린 발췌만 보관합니다.' }));
    return api('/gaps?kind=' + kind + '&status=all').then(function (res) {
      root.appendChild(table('공백 ' + res.gaps.length + '건 (빈도·피드백 순)', [
        ['사유', function (g) { return g.reason_code; }, 'ks-mono'],
        ['자격·절차·의도', function (g) { return [g.subcode || g.status_code || '—', g.procedure || '—', g.intent || '—'].join(' · '); }],
        ['발생', function (g) { return g.occurrence_count; }, 'ks-num'], ['피드백', function (g) { return g.feedback_count; }, 'ks-num'],
        ['최근', function (g) { return (g.last_seen || '').slice(0, 10); }],
        ['예시(가림 처리)', function (g) { return g.example_query || '(보관 안 함)'; }, 'ks-ko'],
        ['상태', function (g) { return badge(g.resolution_status); }]
      ], res.gaps, function (g) { gapDialog(g); }));
    });
  }
  views.gaps = function (root) { return gapsView(root, 'all', '커버리지 공백'); };
  views.unknown = function (root) { return gapsView(root, 'unknown', '미지 질문'); };

  function gapDialog(g) {
    var st = select('ks-g-status', [['open', '열림'], ['investigating', '조사 중'], ['resolved', '해결'], ['wont_fix', '대응 안 함']], g.resolution_status);
    var note = h('textarea', { id: 'ks-g-note' }); note.value = g.resolution_note || '';
    var promote = h('input', { id: 'ks-g-promote', type: 'checkbox' });
    var key = h('input', { id: 'ks-g-key', value: ('gap.' + (g.status_code || 'x') + '.' + (g.procedure || 'x') + '.' + (g.intent || 'x')).toLowerCase().replace(/[^a-z0-9_.:-]/g, '_') });
    var query = h('input', { id: 'ks-g-query', value: g.example_query || '' });
    var nodes = [kv([['사유', g.reason_code], ['대상', [g.status_code, g.subcode, g.procedure, g.intent].filter(Boolean).join(' · ')], ['발생 / 피드백', g.occurrence_count + ' / ' + g.feedback_count]]),
      field('처리 상태', st), field('메모', note),
      h('div', { className: 'ks-field' }, [h('label', { 'for': 'ks-g-promote' }, [promote, ' 회귀 평가 케이스로 승격(초안 — 별도 승인 필요)'])]),
      field('케이스 키', key), field('평가 질문(가림 처리된 예시 기반)', query)];
    return confirmDialog('커버리지 공백', nodes, '저장').then(function (ok) {
      if (!ok) return;
      return api('/gaps/' + encodeURIComponent(g.gap_id), { method: 'POST', body: { resolution_status: st.value, note: note.value.trim() } }).then(function () {
        if (!promote.checked) return null;
        return api('/gaps/' + encodeURIComponent(g.gap_id) + '/promote', { method: 'POST', body: {
          case_key: key.value.trim(), query: query.value.trim() || g.example_query || (g.status_code + ' ' + g.procedure), language: 'ko',
          tags: ['promoted_gap'], assertions: [{ type: 'EXPECTED_STATUS', value: g.status_code }, { type: 'MUST_NOT_LEAK_INTERNAL_METADATA' }] } });
      }).then(function (c) { status(c ? '저장·승격 완료: ' + c.case_key + ' (초안)' : '저장 완료'); return render(); });
    }).catch(fail);
  }

  views.evals = function (root) {
    root.appendChild(h('h1', { text: '평가' }));
    var sel = h('input', { id: 'ks-e-selector', value: 'all', 'aria-describedby': 'ks-e-help' });
    var run = h('button', { type: 'button', className: 'ks-btn ks-btn-primary', text: '평가 실행(오프라인·결정적)' });
    var out = h('div', { id: 'ks-e-out' });
    root.appendChild(h('div', { className: 'ks-filters' }, [field('선택자', sel), run]));
    root.appendChild(h('p', { className: 'ks-muted', id: 'ks-e-help', text: 'all · tag:ci · tag:golden_questions_v1 · 케이스 키. 승인된 케이스만 실행됩니다. 문장 표현이 아니라 사실·출처·커버리지를 검사합니다.' }));
    root.appendChild(out);
    run.addEventListener('click', function () {
      status('평가 실행 중…');
      api('/evals/run', { method: 'POST', body: { selector: sel.value.trim() || 'all' } }).then(function (r) {
        status('평가 완료: ' + r.passed + '/' + r.total + ' 통과');
        clear(out).appendChild(table('실패 ' + r.failed + '건', [['케이스', function (x) { return x.case_key; }, 'ks-mono'],
          ['실패 내용', function (x) { return x.failures.join(' / '); }, 'ks-ko']], r.results.filter(function (x) { return !x.passed; })));
        return render();
      }).catch(fail);
    });
    return api('/evals').then(function (res) {
      root.appendChild(table('평가 케이스 ' + res.cases.length + '건', [
        ['케이스', function (c) { return c.case_key; }, 'ks-mono'], ['질문', function (c) { return c.query; }, 'ks-ko'],
        ['출처', function (c) { return c.origin; }], ['상태', function (c) { return badge(c.state); }],
        ['최근 결과', function (c) { return c.last_result ? badge(c.last_result.passed ? 'pass' : 'fail') : '—'; }],
        ['동작', function (c) {
          if (c.state !== 'draft') return '—';
          var b = h('button', { type: 'button', className: 'ks-btn', text: '승인' });
          b.addEventListener('click', function (e) {
            e.stopPropagation();
            api('/evals/' + encodeURIComponent(c.case_id) + '/state', { method: 'POST', body: { state: 'approved' } }).then(function () { status('승인됨: ' + c.case_key); return render(); }).catch(fail);
          });
          return b;
        }]], res.cases));
    });
  };

  views.audit = function (root) {
    root.appendChild(h('h1', { text: '감사 기록' }));
    return api('/audit?limit=200').then(function (res) {
      root.appendChild(table('최근 변경 ' + res.audit.length + '건 (추가 전용, 수정·삭제 불가)', [
        ['시각', function (a) { return a.at; }, 'ks-mono'], ['행위자', function (a) { return a.actor; }], ['종류', function (a) { return a.actor_kind; }],
        ['대상', function (a) { return a.entity_type + ' ' + a.entity_id; }, 'ks-mono'], ['동작', function (a) { return a.action; }],
        ['사유', function (a) { return a.reason; }, 'ks-ko']], res.audit));
    });
  };

  // --------------------------------------------------------------- router
  var params = {};
  function go(view, p) { state.view = view; params = p || {}; render(); }
  function render() {
    Array.prototype.forEach.call(doc.querySelectorAll('#ks-tabs [role="tab"]'), function (t) {
      t.setAttribute('aria-selected', t.getAttribute('data-view') === state.view ? 'true' : 'false');
      t.tabIndex = t.getAttribute('data-view') === state.view ? 0 : -1;
    });
    var root = clear($('ks-view'));
    root.setAttribute('aria-busy', 'true');
    var p = (views[state.view] || views.overview)(root, params) || Promise.resolve();
    return p.catch(fail).then(function () { root.removeAttribute('aria-busy'); });
  }

  function signOut(message) {
    state.token = ''; store(TOKEN_KEY, null);
    $('ks-app').hidden = true; $('ks-session').hidden = true; $('ks-login').hidden = false;
    var e = $('ks-login-error'); e.hidden = !message; e.textContent = message || '';
  }
  function signIn(token) {
    state.token = token;
    return api('/overview').then(function (o) {
      store(TOKEN_KEY, token);
      $('ks-login').hidden = true; $('ks-app').hidden = false; $('ks-session').hidden = false;
      $('ks-operator').textContent = '운영자: ' + o.operator;
      return render();
    }).catch(function (err) {
      signOut(err.status === 503 ? '이 서버에서는 Knowledge Studio가 꺼져 있습니다(운영자 토큰 미설정).'
        : err.status === 401 ? '토큰이 유효하지 않습니다.' : '서버에 연결하지 못했습니다.');
    });
  }

  function init() {
    $('ks-login-form').addEventListener('submit', function (e) { e.preventDefault(); signIn($('ks-token').value.trim()); });
    $('ks-signout').addEventListener('click', function () { signOut(''); });
    var tabs = doc.querySelectorAll('#ks-tabs [role="tab"]');
    Array.prototype.forEach.call(tabs, function (t, i) {
      t.addEventListener('click', function () { go(t.getAttribute('data-view'), {}); });
      t.addEventListener('keydown', function (e) {
        var next = e.key === 'ArrowDown' || e.key === 'ArrowRight' ? i + 1 : e.key === 'ArrowUp' || e.key === 'ArrowLeft' ? i - 1 : null;
        if (next === null) return;
        e.preventDefault();
        var target = tabs[(next + tabs.length) % tabs.length];
        target.focus(); target.click();
      });
    });
    var saved = store(TOKEN_KEY);
    if (saved) signIn(saved);
  }

  global.WaymakerKnowledgeStudio = { init: init, _h: h };
  if (doc.readyState === 'loading') doc.addEventListener('DOMContentLoaded', init); else init();
})(window);
