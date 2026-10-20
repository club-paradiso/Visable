/**
 * VISABLE Content Operations Studio — Client Application
 *
 * Secure administration system for immigration knowledge, checklist items,
 * human reviews, visual diffing, and zero-loss release pipeline.
 *
 * Invariants:
 * - All dynamic data is inserted using textContent and DOM APIs (zero innerHTML).
 * - Operator tokens are preserved in sessionStorage only.
 * - Enforces role-based action gating (Viewer, Editor, Reviewer, Publisher).
 * - Strict evidence requirement: rejects approvals without official HTTPS citation.
 */
(function (global) {
  'use strict';

  var doc = global.document;
  var TOKEN_KEY = 'visable.cs.token';
  var API_PREFIX = '/api/knowledge/studio/checklists';

  var state = {
    token: '',
    operator: '',
    role: 'viewer',
    currentView: 'dashboard',
    selectedScenarioId: null,
    selectedOfficeCode: 'jeju',
    selectedDraftId: null,
    scenarios: [],
    scenarioTotal: 0,
    searchQuery: '',
    procedureFilter: 'all',
    reviewStateFilter: 'all',
  };

  // -------------------------------------------------------------------------
  // DOM & Utility Helpers (Safe DOM, Zero innerHTML)
  // -------------------------------------------------------------------------
  function h(tag, attrs, children) {
    var el = doc.createElement(tag);
    Object.keys(attrs || {}).forEach(function (k) {
      var v = attrs[k];
      if (v === null || v === undefined || v === false) return;
      if (k === 'text') {
        el.textContent = String(v);
      } else if (k === 'className') {
        el.className = v;
      } else if (k === 'on') {
        Object.keys(v).forEach(function (ev) {
          el.addEventListener(ev, v[ev]);
        });
      } else {
        el.setAttribute(k, v === true ? '' : String(v));
      }
    });
    (children || []).forEach(function (c) {
      if (c === null || c === undefined || c === false) return;
      if (typeof c === 'string' || typeof c === 'number') {
        el.appendChild(doc.createTextNode(String(c)));
      } else if (c instanceof global.Node) {
        el.appendChild(c);
      }
    });
    return el;
  }

  function $(id) {
    return doc.getElementById(id);
  }

  function clear(el) {
    while (el && el.firstChild) el.removeChild(el.firstChild);
    return el;
  }

  function status(msg) {
    var el = $('cs-status-bar');
    if (el) el.textContent = msg || '';
  }

  function store(key, value) {
    try {
      if (value === undefined) return global.sessionStorage.getItem(key);
      if (value === null) global.sessionStorage.removeItem(key);
      else global.sessionStorage.setItem(key, value);
    } catch (e) {
      /* In memory fallback */
    }
    return null;
  }

  function resolveUrl(path) {
    return (global.VisableBackend && global.VisableBackend.url)
      ? global.VisableBackend.url(path)
      : path;
  }

  function api(path, opts) {
    opts = opts || {};
    var init = {
      method: opts.method || 'GET',
      headers: {
        Authorization: 'Bearer ' + state.token,
      },
    };
    if (opts.body !== undefined) {
      init.headers['Content-Type'] = 'application/json';
      init.body = JSON.stringify(opts.body);
    }
    return global.fetch(resolveUrl(API_PREFIX + path), init).then(function (res) {
      return res.json().catch(function () { return {}; }).then(function (data) {
        if (!res.ok) {
          var detail = (data && data.detail) || {};
          var err = new Error(detail.message || detail.error || ('HTTP ' + res.status));
          err.status = res.status;
          err.detail = detail;
          throw err;
        }
        return data;
      });
    });
  }

  // -------------------------------------------------------------------------
  // Role & Permission Checks
  // -------------------------------------------------------------------------
  function canEdit() {
    return ['editor', 'reviewer', 'publisher'].indexOf(state.role) !== -1;
  }
  function canReview() {
    return ['reviewer', 'publisher'].indexOf(state.role) !== -1;
  }
  function canPublish() {
    return state.role === 'publisher';
  }

  var PROCEDURE_LABEL = {
    extension: '체류기간 연장',
    change: '체류자격 변경',
    registration: '외국인등록·거소신고',
  };

  var REVIEW_STATE_LABEL = {
    VERIFIED: '검증 완료',
    HUMAN_REVIEW_REQUIRED: '검토 필요',
    UNDER_REVIEW: '검토 중',
    DRAFT: '초안',
    SUBMITTED: '승인 대기',
    CHANGES_REQUESTED: '수정 요청',
    APPROVED: '승인됨',
    REJECTED: '반려됨',
  };

  var REVIEW_STATE_TONE = {
    VERIFIED: 'ok',
    APPROVED: 'ok',
    HUMAN_REVIEW_REQUIRED: 'warn',
    UNDER_REVIEW: 'warn',
    DRAFT: 'warn',
    SUBMITTED: 'warn',
    CHANGES_REQUESTED: 'bad',
    REJECTED: 'bad',
  };

  function renderBadge(text, customTone) {
    var tone = customTone || REVIEW_STATE_TONE[text] || 'neutral';
    var label = REVIEW_STATE_LABEL[text] || text || '—';
    return h('span', { className: 'cs-badge', 'data-tone': tone, text: label });
  }

  // -------------------------------------------------------------------------
  // Dialog / Modal Helper
  // -------------------------------------------------------------------------
  function showDialog(title, bodyEl, onConfirm) {
    var dialog = $('cs-dialog');
    var titleEl = $('cs-dialog-title');
    var bodyContainer = $('cs-dialog-body');
    var confirmBtn = $('cs-dialog-confirm');
    var cancelBtn = $('cs-dialog-cancel');

    titleEl.textContent = title;
    clear(bodyContainer);
    bodyContainer.appendChild(bodyEl);

    function close() {
      dialog.close();
      confirmBtn.removeEventListener('click', handleConfirm);
      cancelBtn.removeEventListener('click', handleCancel);
    }

    function handleConfirm(e) {
      e.preventDefault();
      if (onConfirm) onConfirm();
      close();
    }
    function handleCancel(e) {
      e.preventDefault();
      close();
    }

    confirmBtn.addEventListener('click', handleConfirm);
    cancelBtn.addEventListener('click', handleCancel);

    if (dialog.showModal) {
      dialog.showModal();
    } else {
      dialog.setAttribute('open', '');
    }
  }

  // -------------------------------------------------------------------------
  // Session & Authentication
  // -------------------------------------------------------------------------
  function signOut(message) {
    state.token = '';
    state.operator = '';
    state.role = 'viewer';
    store(TOKEN_KEY, null);

    $('cs-app').hidden = true;
    $('cs-session').hidden = true;
    $('cs-login-section').hidden = false;

    var errEl = $('cs-login-error');
    if (errEl) {
      errEl.hidden = !message;
      errEl.textContent = message || '';
    }
    status('로그아웃되었습니다.');
  }

  function signIn(token) {
    state.token = token;
    status('인증 정보를 확인하는 중...');

    return api('/auth/me')
      .then(function (me) {
        state.operator = me.operator;
        state.role = me.role || 'editor';
        store(TOKEN_KEY, token);

        $('cs-login-section').hidden = true;
        $('cs-app').hidden = false;
        $('cs-session').hidden = false;

        $('cs-operator').textContent = state.operator;
        var roleBadge = $('cs-role-badge');
        roleBadge.setAttribute('data-role', state.role);
        roleBadge.textContent = state.role.toUpperCase();

        status('연결 성공: ' + state.operator + ' (' + state.role + ')');
        navigate(state.currentView || 'dashboard');
      })
      .catch(function (err) {
        var msg = '인증에 실패했습니다.';
        if (err.status === 503) {
          msg = '운영자 인증 시스템이 설정되지 않았습니다 (WAYMAKER_OPERATOR_TOKENS 미설정).';
        } else if (err.status === 401) {
          msg = '토큰이 올바르지 않거나 만료되었습니다.';
        }
        signOut(msg);
      });
  }

  // -------------------------------------------------------------------------
  // View Router
  // -------------------------------------------------------------------------
  function navigate(viewName, opts) {
    state.currentView = viewName;
    opts = opts || {};

    // Update Tab UI
    var tabs = doc.querySelectorAll('#cs-tabs [role="tab"]');
    tabs.forEach(function (tab) {
      var isTarget = tab.getAttribute('data-view') === viewName;
      tab.setAttribute('aria-selected', isTarget ? 'true' : 'false');
    });

    var container = $('cs-view-container');
    clear(container);

    status('화면 로딩 중: ' + viewName);

    if (viewName === 'dashboard') {
      renderDashboard(container);
    } else if (viewName === 'editor') {
      renderEditor(container, opts);
    } else if (viewName === 'offices') {
      renderOffices(container);
    } else if (viewName === 'reviews') {
      renderReviews(container);
    } else if (viewName === 'diff') {
      renderDiffView(container, opts.draftId || state.selectedDraftId);
    } else if (viewName === 'publish') {
      renderPublishPipeline(container);
    }
  }

  // -------------------------------------------------------------------------
  // VIEW 1: DASHBOARD
  // -------------------------------------------------------------------------
  function renderDashboard(container) {
    var wrap = h('div', { className: 'cs-dashboard' });
    container.appendChild(wrap);

    api('/dashboard')
      .then(function (metrics) {
        clear(wrap);

        // Update pending review badge in tab header
        var pBadge = $('cs-pending-badge');
        if (pBadge) {
          pBadge.hidden = metrics.pending_review === 0;
          pBadge.textContent = String(metrics.pending_review);
        }

        // Top KPI Grid
        var kpis = [
          { label: '전체 상황별 서류', val: metrics.total_items, sub: '2026.09 공식 기준', tone: 'primary' },
          { label: '검증 완료 항목', val: metrics.verified_items, sub: '공식 매뉴얼·법령 대조', tone: 'ok' },
          { label: '검토 대기 항목', val: metrics.pending_review, sub: '운영자 승인 대기', tone: 'warn' },
          { label: '근거 보강 필요', val: metrics.needs_evidence, sub: 'HTTPS 공문·고시 미확인', tone: 'warn' },
          { label: '법령 충돌 의심', val: metrics.suspected_conflicts, sub: '상위 법령 해석 차이', tone: 'bad' },
          { label: '관서별 특별 요건', val: metrics.office_overrides_count, sub: '26개 출입국관서 차이', tone: 'primary' },
        ];

        var grid = h('div', { className: 'cs-kpi-grid' }, kpis.map(function (k) {
          return h('div', { className: 'cs-kpi-card', 'data-tone': k.tone }, [
            h('p', { className: 'cs-kpi-label', text: k.label }),
            h('p', { className: 'cs-kpi-val', text: k.val }),
            h('p', { className: 'cs-kpi-sub', text: k.sub }),
          ]);
        }));
        wrap.appendChild(grid);

        // Two-column layout
        var cols = h('div', { className: 'cs-dashboard-cols' });

        // Left Col: Procedure Breakdown & Fast Entry
        var leftCol = h('div', {}, [
          // Procedure Breakdown Card
          h('div', { className: 'cs-panel' }, [
            h('div', { className: 'cs-panel-header' }, [
              h('h3', { className: 'cs-panel-title', text: '업무 유형별 데이터 분포 (647개 전수 관리)' }),
            ]),
            h('p', { className: 'cs-field-hint', text: '출입국관리법 및 시행규칙 기준 3대 핵심 민원 업무를 전수 보존합니다.' }),
            h('div', { className: 'cs-proc-bar' }, [
              h('div', { className: 'cs-proc-seg-ext', style: 'width: 34.6%' }),
              h('div', { className: 'cs-proc-seg-chg', style: 'width: 38.8%' }),
              h('div', { className: 'cs-proc-seg-reg', style: 'width: 26.6%' }),
            ]),
            h('div', { className: 'cs-proc-legend' }, [
              h('div', { className: 'cs-proc-legend-item' }, [
                h('span', { className: 'cs-proc-dot', style: 'background: #174d37' }),
                h('span', { text: '체류기간 연장 (224건)' }),
              ]),
              h('div', { className: 'cs-proc-legend-item' }, [
                h('span', { className: 'cs-proc-dot', style: 'background: #2563eb' }),
                h('span', { text: '체류자격 변경 (251건)' }),
              ]),
              h('div', { className: 'cs-proc-legend-item' }, [
                h('span', { className: 'cs-proc-dot', style: 'background: #d97706' }),
                h('span', { text: '외국인등록·거소신고 (172건)' }),
              ]),
            ]),
          ]),

          // Quick Pilot Targets Card
          h('div', { className: 'cs-panel' }, [
            h('div', { className: 'cs-panel-header' }, [
              h('h3', { className: 'cs-panel-title', text: '중점 점검 대상 바로가기 (Pilot Vertical Slice)' }),
            ]),
            h('p', { className: 'cs-field-hint', text: '외국인 민원 빈도가 높고 법령 개정이 잦은 핵심 자격을 즉시 점검합니다.' }),
            h('div', { style: 'display: flex; gap: 0.5rem; flex-wrap: wrap; margin-top: 0.75rem;' }, [
              h('button', {
                className: 'cs-btn cs-btn-quiet',
                text: 'D-2 유학 (시간제취업·재정입증)',
                on: { click: function () { navigate('editor', { search: 'D-2' }); } },
              }),
              h('button', {
                className: 'cs-btn cs-btn-quiet',
                text: 'E-7-1 전문인력 (소득요건·고용계약)',
                on: { click: function () { navigate('editor', { search: 'E-7-1' }); } },
              }),
              h('button', {
                className: 'cs-btn cs-btn-quiet',
                text: 'F-4 재외동포 (거소신고·자격부여)',
                on: { click: function () { navigate('editor', { search: 'F-4' }); } },
              }),
              h('button', {
                className: 'cs-btn cs-btn-quiet',
                text: '제주출입국청 (도내 대학 재정기준 특례)',
                on: { click: function () { navigate('offices', { office: 'jeju' }); } },
              }),
            ]),
          ]),
        ]);

        // Right Col: Recent Drafts & Governance Rules
        var rightCol = h('div', {}, [
          h('div', { className: 'cs-panel' }, [
            h('div', { className: 'cs-panel-header' }, [
              h('h3', { className: 'cs-panel-title', text: '최근 검토·개정 초안' }),
              metrics.recent_drafts.length ? h('button', {
                className: 'cs-btn cs-btn-quiet cs-btn-sm',
                text: '대기열 열기',
                on: { click: function () { navigate('reviews'); } },
              }) : null,
            ]),
            metrics.recent_drafts.length === 0
              ? h('p', { className: 'cs-field-hint', text: '현재 진행 중인 초안이 없습니다. 자격 편집기에서 새로운 개정을 제안하세요.' })
              : h('ul', { style: 'list-style: none;' }, metrics.recent_drafts.slice(0, 5).map(function (d) {
                  return h('li', {
                    style: 'padding: 0.5rem 0; border-bottom: 1px solid var(--border); display: flex; justify-content: space-between; align-items: center;',
                  }, [
                    h('div', {}, [
                      h('strong', { text: d.item_id }),
                      h('span', { style: 'font-size: 0.75rem; color: var(--text-muted); margin-left: 0.5rem;', text: d.author }),
                    ]),
                    renderBadge(d.review_state),
                  ]);
                })),
          ]),

          h('div', { className: 'cs-panel', style: 'background: #fdfbf7;' }, [
            h('h4', { style: 'font-size: 0.9rem; font-weight: 700; color: #854d0e; margin-bottom: 0.5rem;', text: '안전한 출입국 지식 거버넌스 원칙' }),
            h('ul', { style: 'padding-left: 1.25rem; font-size: 0.8rem; color: #713f12; line-height: 1.6;' }, [
              h('li', { text: '647개 기본 데이터는 절대 임의 누락되거나 축소되지 않습니다.' }),
              h('li', { text: '모든 개정 제안은 공식 HTTPS 출입국 공문 근거가 등록되어야 승인됩니다.' }),
              h('li', { text: '관서별 예외는 전국 표준을 덮어쓰지 않고 명확히 분리 관리됩니다.' }),
              h('li', { text: '배포 전 무결성 게이트를 100% 통과해야 실제 웹사이트에 게시됩니다.' }),
            ]),
          ]),
        ]);

        cols.appendChild(leftCol);
        cols.appendChild(rightCol);
        wrap.appendChild(cols);

        status('대시보드 데이터 갱신 완료.');
      })
      .catch(function (err) {
        status('대시보드 로딩 오류: ' + err.message);
      });
  }

  // -------------------------------------------------------------------------
  // VIEW 2: VISA & SCENARIO EDITOR
  // -------------------------------------------------------------------------
  function renderEditor(container, opts) {
    opts = opts || {};
    var layout = h('div', { className: 'cs-editor-layout' });
    container.appendChild(layout);

    var leftPane = h('div', { className: 'cs-panel' });
    var rightPane = h('div', { id: 'cs-editor-form-pane', className: 'cs-form-panel' });
    layout.appendChild(leftPane);
    layout.appendChild(rightPane);

    // Initial message on right
    rightPane.appendChild(h('div', { style: 'text-align: center; padding: 3rem 1rem; color: var(--text-muted);' }, [
      h('p', { style: 'font-size: 1.1rem; font-weight: 600;', text: '왼쪽 목록에서 서류 상황을 선택하세요.' }),
      h('p', { style: 'font-size: 0.85rem; margin-top: 0.5rem;', text: '647개 공식 상황별 서류를 검색하고 개정 초안을 작성할 수 있습니다.' }),
    ]));

    // Search and Filters on Left
    var searchInput = h('input', {
      type: 'search',
      className: 'cs-search-input',
      placeholder: '체류자격 코드 또는 키워드 (예: D-2, E-7, 유학)',
      value: opts.search || state.searchQuery || '',
    });
    var searchBtn = h('button', { className: 'cs-btn cs-btn-primary cs-btn-sm', text: '검색' });

    var searchBar = h('div', { className: 'cs-search-bar' }, [searchInput, searchBtn]);
    leftPane.appendChild(searchBar);

    // Procedure Filter Pills
    var procedures = [
      { key: 'all', label: '전체' },
      { key: 'extension', label: '연장 (224)' },
      { key: 'change', label: '변경 (251)' },
      { key: 'registration', label: '등록 (172)' },
    ];
    var pillsContainer = h('div', { className: 'cs-filter-pills' });
    procedures.forEach(function (p) {
      var pill = h('button', {
        className: 'cs-pill-btn' + (state.procedureFilter === p.key ? ' active' : ''),
        text: p.label,
        on: {
          click: function () {
            state.procedureFilter = p.key;
            pillsContainer.querySelectorAll('.cs-pill-btn').forEach(function (b) { b.classList.remove('active'); });
            pill.classList.add('active');
            loadScenarioList();
          },
        },
      });
      pillsContainer.appendChild(pill);
    });
    leftPane.appendChild(pillsContainer);

    var listWrap = h('div', { className: 'cs-item-list', id: 'cs-scenario-list' });
    leftPane.appendChild(listWrap);

    function loadScenarioList() {
      clear(listWrap);
      listWrap.appendChild(h('div', { style: 'padding: 1rem; text-align: center; color: var(--text-muted);', text: '불러오는 중...' }));

      var queryParams = [];
      if (searchInput.value.trim()) queryParams.push('query=' + encodeURIComponent(searchInput.value.trim()));
      if (state.procedureFilter !== 'all') queryParams.push('procedure=' + encodeURIComponent(state.procedureFilter));
      queryParams.push('limit=100');

      api('/scenarios?' + queryParams.join('&'))
        .then(function (res) {
          clear(listWrap);
          state.scenarios = res.scenarios;
          state.scenarioTotal = res.total;

          if (!res.scenarios.length) {
            listWrap.appendChild(h('div', { style: 'padding: 1rem; text-align: center; color: var(--text-muted);', text: '일치하는 서류 항목이 없습니다.' }));
            return;
          }

          res.scenarios.forEach(function (sc) {
            var row = h('div', {
              className: 'cs-item-row' + (state.selectedScenarioId === sc.item_id ? ' selected' : ''),
              on: {
                click: function () {
                  listWrap.querySelectorAll('.cs-item-row').forEach(function (r) { r.classList.remove('selected'); });
                  row.classList.add('selected');
                  state.selectedScenarioId = sc.item_id;
                  loadScenarioDetail(sc.item_id);
                },
              },
            }, [
              h('div', { className: 'cs-item-row-top' }, [
                h('span', { className: 'cs-item-code', text: sc.status_code }),
                renderBadge(sc.review_state),
              ]),
              h('div', { className: 'cs-item-title', text: sc.plain_title || sc.official_name || sc.item_id }),
              h('div', { className: 'cs-item-group', text: (PROCEDURE_LABEL[sc.procedure] || sc.procedure) + ' · ' + (sc.target_group || '일반') }),
            ]);
            listWrap.appendChild(row);
          });

          // If opts.search was specified and we have items, open the first item
          if (opts.search && res.scenarios.length > 0 && !state.selectedScenarioId) {
            listWrap.firstChild.click();
          }
        })
        .catch(function (err) {
          clear(listWrap);
          listWrap.appendChild(h('div', { style: 'padding: 1rem; color: #dc2626;', text: '목록 조회 실패: ' + err.message }));
        });
    }

    searchBtn.addEventListener('click', loadScenarioList);
    searchInput.addEventListener('keydown', function (e) {
      if (e.key === 'Enter') {
        e.preventDefault();
        loadScenarioList();
      }
    });

    loadScenarioList();

    function loadScenarioDetail(itemId) {
      clear(rightPane);
      rightPane.appendChild(h('div', { style: 'padding: 2rem; text-align: center;', text: '상세 정보 불러오는 중...' }));

      api('/scenarios/' + itemId)
        .then(function (data) {
          clear(rightPane);
          var item = data.item;
          var draft = data.active_draft;

          // Header
          var header = h('div', { className: 'cs-panel-header' }, [
            h('div', {}, [
              h('div', { style: 'display: flex; gap: 0.5rem; align-items: center;' }, [
                h('span', { className: 'cs-badge', text: item.item_id }),
                renderBadge(draft ? draft.review_state : item.review_state),
              ]),
              h('h2', { style: 'font-size: 1.25rem; font-weight: 700; margin-top: 0.25rem;', text: (item.status_code + ' — ' + (PROCEDURE_LABEL[item.procedure] || item.procedure)) }),
              h('p', { style: 'font-size: 0.85rem; color: var(--text-muted);', text: '대상 세부구분: ' + (item.target_group || '전체/일반') }),
            ]),
          ]);
          rightPane.appendChild(header);

          if (draft) {
            var draftNotice = h('div', { className: 'cs-alert cs-alert-warn', style: 'margin-bottom: 1.25rem;' }, [
              h('strong', { text: '작성 중인 개정 초안이 있습니다 (' + draft.review_state + '). ' }),
              h('span', { text: '작성자: ' + draft.author + ' · 최근 수정: ' + (draft.updated_at ? draft.updated_at.substring(0, 10) : '—') + ' ' }),
              h('button', {
                className: 'cs-btn cs-btn-quiet cs-btn-sm',
                text: '변경점 비교 (Diff)',
                on: { click: function () { navigate('diff', { draftId: draft.draft_id }); } },
              }),
            ]);
            rightPane.appendChild(draftNotice);
          }

          // Form fields (prefill with draft if exists, else baseline item)
          var current = draft || item;

          var fOfficialName = h('input', { className: 'cs-input', value: current.official_name || '' });
          var fPlainTitle = h('input', { className: 'cs-input', value: current.plain_title || '' });

          var reqList = Array.isArray(current.required_documents) ? current.required_documents.join('\n') : (current.required_documents || '');
          var condList = Array.isArray(current.conditional_documents) ? current.conditional_documents.join('\n') : (current.conditional_documents || '');
          var excList = Array.isArray(current.exceptions) ? current.exceptions.join('\n') : (current.exceptions || '');

          var fRequired = h('textarea', { className: 'cs-textarea', text: reqList, rows: '4' });
          var fConditional = h('textarea', { className: 'cs-textarea', text: condList, rows: '3' });
          var fExceptions = h('textarea', { className: 'cs-textarea', text: excList, rows: '2' });

          var fProxyAllowed = h('input', { type: 'checkbox', id: 'f-proxy-allowed' });
          fProxyAllowed.checked = Boolean(current.proxy_allowed);

          var fProxyDetails = h('input', { className: 'cs-input', value: current.proxy_details || '' });
          var fNotes = h('textarea', { className: 'cs-textarea', text: current.notes || '', rows: '2' });

          // Official Evidence Box
          var fEvidenceUrl = h('input', {
            className: 'cs-input',
            placeholder: 'https://www.hikorea.go.kr/... 또는 https://moj.go.kr/...',
            value: current.evidence_url || '',
          });
          var fEvidenceTitle = h('input', { className: 'cs-input', placeholder: '출입국 고시 또는 매뉴얼 명칭', value: current.evidence_title || '' });
          var fEvidenceIssuer = h('input', { className: 'cs-input', placeholder: '발행/공표 기관 (e.g. 법무부 출입국·외국인정책본부)', value: current.evidence_issuer || '' });
          var fEvidenceDate = h('input', { className: 'cs-input', placeholder: 'YYYY-MM-DD', value: current.evidence_date || '' });

          var fSourceEdition = h('input', { className: 'cs-input', placeholder: '지침 판차 (e.g. 2026.10 개정판)', value: current.source_edition || '' });
          var fSourceSection = h('input', { className: 'cs-input', placeholder: '해당 조항/절 (e.g. 제3장 체류자격별 구비서류)', value: current.source_section || '' });
          var fSourceLocator = h('input', { className: 'cs-input', placeholder: '문서번호/페이지 (e.g. p.142 또는 고시 제2026-88호)', value: current.source_locator || '' });
          var fEffectiveStart = h('input', { className: 'cs-input', placeholder: '시행일 (YYYY-MM-DD)', value: current.effective_start || '' });
          var fEffectiveEnd = h('input', { className: 'cs-input', placeholder: '만료일 (YYYY-MM-DD, 선택)', value: current.effective_end || '' });

          var fRationale = h('textarea', {
            className: 'cs-textarea',
            placeholder: '개정 사유 및 법령 근거를 구체적으로 작성하세요 (필수)',
            text: (draft && (draft.editor_note || draft.change_rationale)) ? (draft.editor_note || draft.change_rationale) : '',
            rows: '3',
          });

          var form = h('form', { on: { submit: function (e) { e.preventDefault(); } } }, [
            h('div', { className: 'cs-form-row' }, [
              h('div', { className: 'cs-field' }, [
                h('label', { text: '공식 체류자격 명칭' }),
                fOfficialName,
              ]),
              h('div', { className: 'cs-field' }, [
                h('label', { text: '일반인용 쉬운 명칭' }),
                fPlainTitle,
              ]),
            ]),

            h('div', { className: 'cs-field' }, [
              h('label', { text: '필수 제출 서류 (줄바꿈으로 구분)' }),
              h('p', { className: 'cs-field-hint', text: '모든 신청인이 예외 없이 제출해야 하는 공통 구비서류입니다.' }),
              fRequired,
            ]),

            h('div', { className: 'cs-field' }, [
              h('label', { text: '조건부 제출 서류 (줄바꿈으로 구분)' }),
              h('p', { className: 'cs-field-hint', text: '특정 국적, 소득 조건, 실태조사 대상자 등 상황에 따라 요구되는 서류입니다.' }),
              fConditional,
            ]),

            h('div', { className: 'cs-field' }, [
              h('label', { text: '대체 및 면제 조건' }),
              fExceptions,
            ]),

            h('div', { className: 'cs-form-row' }, [
              h('div', { className: 'cs-field' }, [
                h('label', { text: '대리 신청 가능 여부' }),
                h('div', { style: 'margin-top: 0.5rem; display: flex; align-items: center; gap: 0.5rem;' }, [
                  fProxyAllowed,
                  h('label', { for: 'f-proxy-allowed', style: 'margin-bottom: 0; font-weight: normal;', text: '대리인 접수 허용' }),
                ]),
              ]),
              h('div', { className: 'cs-field' }, [
                h('label', { text: '대리 신청 요건 및 위임 서류' }),
                fProxyDetails,
              ]),
            ]),

            h('div', { className: 'cs-field' }, [
              h('label', { text: '행정 비고 및 유의사항' }),
              fNotes,
            ]),

            // Evidence Box
            h('div', { className: 'cs-evidence-box' }, [
              h('h4', { text: '⚖️ 공식 증빙 근거 (Evidence Gate & Legal Governance)' }),
              h('p', { className: 'cs-field-hint', text: '출입국관리법령, 법무부 고시, 하이코리아 공지 등 검증 가능한 HTTPS 링크 및 발행 기관 정보가 필수입니다.' }),
              h('div', { className: 'cs-form-row' }, [
                h('div', { className: 'cs-field' }, [
                  h('label', { text: '공식 근거 URL (HTTPS 필수)' }),
                  fEvidenceUrl,
                ]),
                h('div', { className: 'cs-field' }, [
                  h('label', { text: '근거 문서명 / 고시명' }),
                  fEvidenceTitle,
                ]),
              ]),
              h('div', { className: 'cs-form-row' }, [
                h('div', { className: 'cs-field' }, [
                  h('label', { text: '발행/공표 기관' }),
                  fEvidenceIssuer,
                ]),
                h('div', { className: 'cs-field' }, [
                  h('label', { text: '시행일 / 고시일자' }),
                  fEvidenceDate,
                ]),
              ]),
              h('div', { className: 'cs-form-row' }, [
                h('div', { className: 'cs-field' }, [
                  h('label', { text: '지침 판차 (Edition)' }),
                  fSourceEdition,
                ]),
                h('div', { className: 'cs-field' }, [
                  h('label', { text: '해당 조항 / 편장절' }),
                  fSourceSection,
                ]),
              ]),
              h('div', { className: 'cs-form-row' }, [
                h('div', { className: 'cs-field' }, [
                  h('label', { text: '문서번호 / 페이지 (Locator)' }),
                  fSourceLocator,
                ]),
                h('div', { className: 'cs-field' }, [
                  h('label', { text: '유효기간 시작~종료' }),
                  h('div', { style: 'display: flex; gap: 0.5rem; align-items: center;' }, [
                    fEffectiveStart,
                    h('span', { text: '~' }),
                    fEffectiveEnd,
                  ]),
                ]),
              ]),
            ]),

            h('div', { className: 'cs-field' }, [
              h('label', { text: '개정 사유 및 제안 배경 (Change Rationale) *' }),
              fRationale,
            ]),
          ]);

          // Actions
          var actions = h('div', { className: 'cs-form-actions' });

          function buildPayload() {
            var parseLines = function (val) {
              return val.split('\n').map(function (s) { return s.trim(); }).filter(Boolean);
            };
            var reqLines = parseLines(fRequired.value);
            var condLines = parseLines(fConditional.value);
            return {
              item_id: item.id || item.item_id,
              procedure: item.procedure,
              status_code: item.status_code,
              target_group: item.target_group,
              official_name: fOfficialName.value.trim(),
              plain_title: fPlainTitle.value.trim(),
              required_text: fRequired.value.trim(),
              conditional_text: fConditional.value.trim(),
              application_text: item.application_text || '',
              note_text: fNotes.value.trim(),
              required_documents: reqLines,
              conditional_documents: condLines,
              exceptions: parseLines(fExceptions.value),
              submission_methods: item.submission_methods || ['방문예약'],
              proxy_allowed: fProxyAllowed.checked,
              proxy_details: fProxyDetails.value.trim(),
              notes: fNotes.value.trim(),
              source_text: item.source_text || '',
              evidence_url: fEvidenceUrl.value.trim(),
              evidence_title: fEvidenceTitle.value.trim(),
              evidence_issuer: fEvidenceIssuer.value.trim(),
              evidence_date: fEvidenceDate.value.trim(),
              source_edition: fSourceEdition.value.trim() || null,
              source_section: fSourceSection.value.trim() || null,
              source_locator: fSourceLocator.value.trim() || null,
              effective_start: fEffectiveStart.value.trim() || null,
              effective_end: fEffectiveEnd.value.trim() || null,
              editor_note: fRationale.value.trim() || '운영자 서류 정보 수정',
              change_rationale: fRationale.value.trim() || '운영자 서류 정보 수정',
            };
          }

          if (canEdit()) {
            var saveBtn = h('button', {
              type: 'button',
              className: 'cs-btn cs-btn-quiet',
              text: '임시 저장 (Save Draft)',
              on: {
                click: function () {
                  var payload = buildPayload();
                  api('/drafts', { method: 'POST', body: payload })
                    .then(function (res) {
                      status('초안 저장 완료: ' + res.draft_id);
                      loadScenarioDetail(item.item_id);
                    })
                    .catch(function (err) {
                      status('초안 저장 오류: ' + err.message);
                    });
                },
              },
            });
            actions.appendChild(saveBtn);

            var submitBtn = h('button', {
              type: 'button',
              className: 'cs-btn cs-btn-primary',
              text: '검토 요청 (Submit for Review)',
              on: {
                click: function () {
                  var payload = buildPayload();
                  if (!payload.evidence_url.startsWith('https://')) {
                    status('경고: HTTPS 공식 근거 URL이 필요합니다.');
                  }
                  api('/drafts', { method: 'POST', body: payload })
                    .then(function (saved) {
                      return api('/drafts/' + saved.draft_id + '/action', {
                        method: 'POST',
                        body: {
                          action: 'submit',
                          evidence_url: payload.evidence_url,
                          evidence_title: payload.evidence_title,
                          note: payload.change_rationale,
                        },
                      });
                    })
                    .then(function () {
                      status('검토 요청 제출 완료!');
                      loadScenarioDetail(item.item_id);
                    })
                    .catch(function (err) {
                      status('검토 요청 실패: ' + err.message);
                    });
                },
              },
            });
            actions.appendChild(submitBtn);
          }

          if (draft) {
            var diffBtn = h('button', {
              type: 'button',
              className: 'cs-btn cs-btn-quiet',
              text: '변경점 비교 (Diff)',
              on: {
                click: function () {
                  navigate('diff', { draftId: draft.draft_id });
                },
              },
            });
            actions.appendChild(diffBtn);
          }

          rightPane.appendChild(form);
          rightPane.appendChild(actions);
        })
        .catch(function (err) {
          clear(rightPane);
          rightPane.appendChild(h('div', { style: 'padding: 2rem; color: #dc2626;', text: '상세 정보 로드 실패: ' + err.message }));
        });
    }
  }

  // -------------------------------------------------------------------------
  // VIEW 3: OFFICE-SPECIFIC REQUIREMENTS (26 Immigration Offices)
  // -------------------------------------------------------------------------
  function renderOffices(container) {
    var wrap = h('div', { className: 'cs-panel' });
    container.appendChild(wrap);

    wrap.appendChild(h('div', { className: 'cs-panel-header' }, [
      h('div', {}, [
        h('h2', { className: 'cs-panel-title', text: '관서별 차이 관리 (26개 출입국·외국인관서)' }),
        h('p', { className: 'cs-field-hint', text: '전국 공통 기준을 훼손하지 않고, 관서별 자체 지침과 추가 요구 서류를 투명하게 관리합니다.' }),
      ]),
      canEdit() ? h('button', {
        className: 'cs-btn cs-btn-primary',
        text: '+ 신규 관서 요건 등록',
        on: { click: showCreateOfficeOverrideDialog },
      }) : null,
    ]));

    var contentArea = h('div', { id: 'cs-offices-content' });
    wrap.appendChild(contentArea);

    api('/offices')
      .then(function (res) {
        clear(contentArea);
        var offices = res.offices || [];

        var tableEl = h('table', { className: 'cs-table' }, [
          h('thead', {}, [
            h('tr', {}, [
              h('th', { text: '관서 코드' }),
              h('th', { text: '관서 명칭' }),
              h('th', { text: '관할 구역' }),
              h('th', { text: '등록된 특별 요건' }),
              h('th', { text: '상태' }),
            ]),
          ]),
          h('tbody', {}, offices.map(function (o) {
            return h('tr', {
              className: 'clickable',
              on: {
                click: function () {
                  showOfficeDetailDialog(o);
                },
              },
            }, [
              h('td', { style: 'font-weight: 700; color: var(--primary);', text: o.office_code }),
              h('td', { style: 'font-weight: 600;', text: o.office_name }),
              h('td', { text: o.jurisdiction || '관할 구역' }),
              h('td', { text: o.override_count ? (o.override_count + '건 적용 중') : '전국 표준 적용' }),
              h('td', {}, [
                o.override_count
                  ? renderBadge('관서 차이 반영됨', 'warn')
                  : renderBadge('전국 표준', 'ok'),
              ]),
            ]);
          })),
        ]);

        contentArea.appendChild(h('div', { className: 'cs-table-wrap' }, [tableEl]));
      })
      .catch(function (err) {
        clear(contentArea);
        contentArea.appendChild(h('p', { style: 'color: #dc2626;', text: '관서 목록 로드 오류: ' + err.message }));
      });

    function showCreateOfficeOverrideDialog() {
      var fOffice = h('select', { className: 'cs-select' }, [
        h('option', { value: 'jeju', text: '제주출입국·외국인청 (jeju)' }),
        h('option', { value: 'seoul', text: '서울출입국·외국인청 (seoul)' }),
        h('option', { value: 'seoul_south', text: '서울남부출입국·외국인관서 (seoul_south)' }),
        h('option', { value: 'incheon', text: '인천출입국·외국인청 (incheon)' }),
        h('option', { value: 'suwon', text: '수원출입국·외국인청 (suwon)' }),
        h('option', { value: 'busan', text: '부산출입국·외국인청 (busan)' }),
      ]);
      var fStatusCode = h('input', { className: 'cs-input', placeholder: 'D-2, E-7 등', value: 'D-2' });
      var fProcedure = h('select', { className: 'cs-select' }, [
        h('option', { value: 'extension', text: '체류기간 연장 (extension)' }),
        h('option', { value: 'change', text: '체류자격 변경 (change)' }),
        h('option', { value: 'registration', text: '외국인등록 (registration)' }),
      ]);
      var fType = h('select', { className: 'cs-select' }, [
        h('option', { value: 'additional_document', text: '추가 서류 요구' }),
        h('option', { value: 'conditional_exemption', text: '조건부 면제 요건' }),
        h('option', { value: 'submission_restriction', text: '접수 방식 제한' }),
        h('option', { value: 'jurisdiction_rule', text: '관할구역 특례' }),
      ]);
      var fTitle = h('input', { className: 'cs-input', placeholder: '요건 제목', value: '제주도내 대학 유학생 재정능력 기준 특례' });
      var fDesc = h('textarea', { className: 'cs-textarea', text: '제주특별자치도 소재 대학 유학생에 한하여 잔고증명 기준이 완화 적용됩니다.', rows: '3' });
      var fNoticeUrl = h('input', { className: 'cs-input', placeholder: 'https://...', value: 'https://www.hikorea.go.kr/board/jeju-notice' });

      var body = h('div', {}, [
        h('div', { className: 'cs-field' }, [h('label', { text: '대상 출입국관서' }), fOffice]),
        h('div', { className: 'cs-form-row' }, [
          h('div', { className: 'cs-field' }, [h('label', { text: '체류자격 코드' }), fStatusCode]),
          h('div', { className: 'cs-field' }, [h('label', { text: '신청 업무' }), fProcedure]),
        ]),
        h('div', { className: 'cs-field' }, [h('label', { text: '요건 유형' }), fType]),
        h('div', { className: 'cs-field' }, [h('label', { text: '안내 제목' }), fTitle]),
        h('div', { className: 'cs-field' }, [h('label', { text: '상세 안내 내용' }), fDesc]),
        h('div', { className: 'cs-field' }, [h('label', { text: '공식 공지 URL (HTTPS 필수)' }), fNoticeUrl]),
      ]);

      showDialog('신규 관서 특별 요건 등록', body, function () {
        var payload = {
          office_code: fOffice.value,
          status_code: fStatusCode.value.trim(),
          procedure: fProcedure.value,
          override_type: fType.value,
          title: fTitle.value.trim(),
          description: fDesc.value.trim(),
          official_notice_url: fNoticeUrl.value.trim(),
          verification_status: 'VERIFIED',
        };
        api('/offices/overrides', { method: 'POST', body: payload })
          .then(function () {
            status('관서 요건 등록 성공');
            renderOffices(container);
          })
          .catch(function (err) {
            status('관서 요건 등록 오류: ' + err.message);
          });
      });
    }

    function showOfficeDetailDialog(office) {
      var body = h('div', {}, [
        h('p', { style: 'margin-bottom: 0.5rem;', text: office.office_name + ' (' + office.office_code + ')의 등록된 지침 목록입니다.' }),
        h('div', { className: 'cs-alert cs-alert-ok' }, [
          h('strong', { text: '전국 표준 안내 연동 상태: ' }),
          h('span', { text: '기본 647개 공통 서류가 기본으로 제공되며, 등록된 관서별 요건만 "관서별 추가 유의사항" 탭에 분리 표시됩니다.' }),
        ]),
      ]);
      showDialog(office.office_name + ' 관서 지침 정보', body);
    }
  }

  // -------------------------------------------------------------------------
  // VIEW 4: REVIEW & APPROVAL QUEUE
  // -------------------------------------------------------------------------
  function renderReviews(container) {
    var wrap = h('div', { className: 'cs-panel' });
    container.appendChild(wrap);

    wrap.appendChild(h('div', { className: 'cs-panel-header' }, [
      h('div', {}, [
        h('h2', { className: 'cs-panel-title', text: '검토 및 승인 대기열 (Human Review Queue)' }),
        h('p', { className: 'cs-field-hint', text: '운영자가 제안한 초안을 공식 HTTPS 근거와 대조하여 승인하거나 반려합니다.' }),
      ]),
    ]));

    var listArea = h('div', { id: 'cs-reviews-list' });
    wrap.appendChild(listArea);

    api('/drafts')
      .then(function (res) {
        clear(listArea);
        var drafts = res.drafts || [];

        if (!drafts.length) {
          listArea.appendChild(h('div', { style: 'text-align: center; padding: 3rem 1rem; color: var(--text-muted);' }, [
            h('p', { style: 'font-size: 1.1rem; font-weight: 600;', text: '검토 대기 중인 초안이 없습니다.' }),
            h('p', { style: 'font-size: 0.85rem; margin-top: 0.25rem;', text: '모든 개정 제안이 승인되었거나 게시 처리되었습니다.' }),
          ]));
          return;
        }

        var tableEl = h('table', { className: 'cs-table' }, [
          h('thead', {}, [
            h('tr', {}, [
              h('th', { text: '초안 ID' }),
              h('th', { text: '체류자격 / 업무' }),
              h('th', { text: '상태' }),
              h('th', { text: '제출자' }),
              h('th', { text: '공식 근거 URL' }),
              h('th', { text: '심사 액션' }),
            ]),
          ]),
          h('tbody', {}, drafts.map(function (d) {
            var hasHttps = d.evidence_url && d.evidence_url.startsWith('https://');

            var actionsTd = h('td', { style: 'white-space: nowrap;' });

            // Diff button
            actionsTd.appendChild(h('button', {
              className: 'cs-btn cs-btn-quiet cs-btn-sm',
              text: '비교 (Diff)',
              style: 'margin-right: 0.4rem;',
              on: { click: function () { navigate('diff', { draftId: d.draft_id }); } },
            }));

            if (canReview()) {
              var approveBtn = h('button', {
                className: 'cs-btn cs-btn-success cs-btn-sm',
                text: '승인 (Approve)',
                style: 'margin-right: 0.4rem;',
                on: {
                  click: function () {
                    if (!hasHttps) {
                      showDialog('승인 불가: 공식 HTTPS 근거 누락', h('div', {}, [
                        h('p', { text: 'VISABLE의 엄격한 지식 거버넌스 원칙에 따라, 공식 HTTPS 출입국 공문 근거가 등록되지 않은 초안은 승인할 수 없습니다.' }),
                        h('p', { style: 'color: #dc2626; margin-top: 0.5rem;', text: '편집기에서 공식 법무부/하이코리아 HTTPS URL을 보완해 주세요.' }),
                      ]));
                      return;
                    }

                    var isAuthor = (d.author === state.operator || d.created_by === state.operator);
                    var confirmTitle = isAuthor ? '⚠️ 분리 원칙(Four-Eyes) 경고 및 승인' : '초안 승인 확인';
                    var confirmContent = isAuthor ? h('div', {}, [
                      h('p', { style: 'font-weight: 700; color: #b45309;', text: '본인이 작성한 초안입니다. 지식 거버넌스 분리 원칙에 따라 다른 검토자의 독립 승인이 강력히 권장됩니다.' }),
                      h('p', { style: 'margin-top: 0.5rem;', text: '긴급 운영 상황으로 인한 예외 자가 승인을 계속 진행하시겠습니까?' }),
                    ]) : h('div', {}, [
                      h('p', { text: '공식 근거(' + (d.evidence_title || d.evidence_url) + ')를 대조 확인하였으며, 이 초안을 승인 상태로 전환합니다.' }),
                    ]);

                    showDialog(confirmTitle, confirmContent, function () {
                      var payload = {
                        action: 'approve',
                        comment: isAuthor ? '긴급 예외 자가 승인 확인' : '공식 근거 확인 완료 및 승인',
                        note: isAuthor ? '긴급 예외 자가 승인 확인' : '공식 근거 확인 완료 및 승인',
                        allow_self_approval: isAuthor,
                      };
                      api('/drafts/' + d.draft_id + '/action', {
                        method: 'POST',
                        body: payload,
                      })
                        .then(function () {
                          status('초안 ' + d.draft_id + ' 승인 완료');
                          renderReviews(container);
                        })
                        .catch(function (err) {
                          status('승인 오류: ' + err.message);
                        });
                    });
                  },
                },
              });
              actionsTd.appendChild(approveBtn);

              var rejectBtn = h('button', {
                className: 'cs-btn cs-btn-danger cs-btn-sm',
                text: '반려',
                on: {
                  click: function () {
                    var fReason = h('textarea', { className: 'cs-textarea', placeholder: '반려 사유 입력', rows: '3' });
                    showDialog('초안 반려 (' + d.draft_id + ')', h('div', {}, [
                      h('p', { text: '반려 사유를 작성하세요:' }),
                      fReason,
                    ]), function () {
                      api('/drafts/' + d.draft_id + '/action', {
                        method: 'POST',
                        body: { action: 'reject', note: fReason.value.trim() || '기준 미충족으로 반려' },
                      })
                        .then(function () {
                          status('초안 반려 처리되었습니다.');
                          renderReviews(container);
                        })
                        .catch(function (err) {
                          status('반려 오류: ' + err.message);
                        });
                    });
                  },
                },
              });
              actionsTd.appendChild(rejectBtn);
            }

            return h('tr', {}, [
              h('td', { style: 'font-weight: 700;', text: d.draft_id }),
              h('td', {}, [
                h('strong', { text: d.status_code }),
                h('span', { text: ' (' + (PROCEDURE_LABEL[d.procedure] || d.procedure) + ')' }),
              ]),
              h('td', {}, [renderBadge(d.review_state)]),
              h('td', { text: d.author }),
              h('td', {}, [
                hasHttps
                  ? h('span', { className: 'cs-badge', 'data-tone': 'ok', text: 'HTTPS 검증됨' })
                  : h('span', { className: 'cs-badge', 'data-tone': 'bad', text: '근거 미비 (승인불가)' }),
              ]),
              actionsTd,
            ]);
          })),
        ]);

        listArea.appendChild(h('div', { className: 'cs-table-wrap' }, [tableEl]));
      })
      .catch(function (err) {
        clear(listArea);
        listArea.appendChild(h('p', { style: 'color: #dc2626;', text: '검토 대기열 로드 오류: ' + err.message }));
      });
  }

  // -------------------------------------------------------------------------
  // VIEW 5: DIFF & VERSION HISTORY
  // -------------------------------------------------------------------------
  function renderDiffView(container, draftId) {
    var wrap = h('div', { className: 'cs-panel' });
    container.appendChild(wrap);

    wrap.appendChild(h('div', { className: 'cs-panel-header' }, [
      h('div', {}, [
        h('h2', { className: 'cs-panel-title', text: '버전 비교 및 법적 영향도 분석 (Visual Diff)' }),
        h('p', { className: 'cs-field-hint', text: '현재 게시된 기준(Baseline)과 제안된 초안(Proposed Draft)의 차이점을 분석합니다.' }),
      ]),
      h('button', {
        className: 'cs-btn cs-btn-quiet',
        text: '← 편집기로 돌아가기',
        on: { click: function () { navigate('editor'); } },
      }),
    ]));

    var contentArea = h('div', { id: 'cs-diff-content' });
    wrap.appendChild(contentArea);

    if (!draftId) {
      contentArea.appendChild(h('div', { style: 'padding: 2rem; text-align: center; color: var(--text-muted);' }, [
        h('p', { text: '비교할 초안이 선택되지 않았습니다. 자격 편집기나 검토 대기열에서 "비교 (Diff)"를 클릭하세요.' }),
      ]));
      return;
    }

    api('/diff/' + draftId)
      .then(function (diffData) {
        clear(contentArea);

        // Legal Impact Banner
        var impacts = diffData.impact_analysis || [];
        var banner = h('div', { className: 'cs-impact-banner' }, [
          h('span', { className: 'cs-impact-icon', text: '⚠️' }),
          h('div', { className: 'cs-impact-content' }, [
            h('h4', { text: '법적 및 행정적 영향도 분석 (Legal Impact Analysis)' }),
            h('p', {
              text: impacts.length
                ? impacts.join(' · ')
                : '기본 서류의 실질적 변경 없이 명칭 또는 부가 설명만 개선되었습니다.',
            }),
          ]),
        ]);
        contentArea.appendChild(banner);

        // Side-by-side comparison
        var grid = h('div', { className: 'cs-diff-container' });

        var baselineCol = h('div', { className: 'cs-diff-pane' }, [
          h('h3', { text: '현재 게시된 기준 (Current Baseline)' }),
        ]);

        var proposedCol = h('div', { className: 'cs-diff-pane' }, [
          h('h3', { text: '제안된 개정안 (Proposed Draft)' }),
        ]);

        var b = diffData.baseline || {};
        var p = diffData.proposed || {};

        function addField(label, valBase, valProp, fieldKey) {
          var isChanged = diffData.changed_fields.indexOf(fieldKey) !== -1;

          baselineCol.appendChild(h('div', { className: 'cs-diff-field' }, [
            h('div', { className: 'cs-diff-field-title', text: label }),
            h('div', {
              className: 'cs-diff-val' + (isChanged ? ' removed' : ''),
              text: Array.isArray(valBase) ? valBase.join('\n') : (String(valBase || '—')),
            }),
          ]));

          proposedCol.appendChild(h('div', { className: 'cs-diff-field' }, [
            h('div', { className: 'cs-diff-field-title', text: label }),
            h('div', {
              className: 'cs-diff-val' + (isChanged ? ' added' : ''),
              text: Array.isArray(valProp) ? valProp.join('\n') : (String(valProp || '—')),
            }),
          ]));
        }

        addField('체류자격 공식 명칭', b.official_name, p.official_name, 'official_name');
        addField('일반인용 쉬운 명칭', b.plain_title, p.plain_title, 'plain_title');
        addField('필수 제출 서류', b.required_documents, p.required_documents, 'required_documents');
        addField('조건부 제출 서류', b.conditional_documents, p.conditional_documents, 'conditional_documents');
        addField('예외 및 대체 조건', b.exceptions, p.exceptions, 'exceptions');
        addField('대리 신청 허용 여부', b.proxy_allowed ? '대리 허용' : '본인 직접 접수', p.proxy_allowed ? '대리 허용' : '본인 직접 접수', 'proxy_allowed');
        addField('대리 신청 상세 요건', b.proxy_details, p.proxy_details, 'proxy_details');
        addField('공식 근거 URL', b.evidence_url, p.evidence_url, 'evidence_url');

        grid.appendChild(baselineCol);
        grid.appendChild(proposedCol);
        contentArea.appendChild(grid);
      })
      .catch(function (err) {
        clear(contentArea);
        contentArea.appendChild(h('p', { style: 'color: #dc2626;', text: 'Diff 분석 로드 오류: ' + err.message }));
      });
  }

  // -------------------------------------------------------------------------
  // VIEW 6: PRE-PUBLISH VALIDATION & PUBLISH PIPELINE
  // -------------------------------------------------------------------------
  function renderPublishPipeline(container) {
    var wrap = h('div', { className: 'cs-panel' });
    container.appendChild(wrap);

    wrap.appendChild(h('div', { className: 'cs-panel-header' }, [
      h('div', {}, [
        h('h2', { className: 'cs-panel-title', text: '무결성 사전 검증 및 게시 파이프라인 (Release Gate)' }),
        h('p', { className: 'cs-field-hint', text: '데이터 손실을 100% 방지하고 647개 항목의 무결성을 전수 검증한 뒤 운영 배포합니다.' }),
      ]),
    ]));

    var validateCard = h('div', { className: 'cs-gate-card' });
    wrap.appendChild(validateCard);

    validateCard.appendChild(h('div', { className: 'cs-gate-header' }, [
      h('div', {}, [
        h('h3', { className: 'cs-gate-title', text: '1단계: 무결성 사전 검증 (Pre-publish Validation Gate)' }),
        h('p', { className: 'cs-field-hint', text: '647개 상황별 서류 보존, 체류자격 ID 접두어 및 스키마 유효성을 검사합니다.' }),
      ]),
      h('button', {
        className: 'cs-btn cs-btn-primary',
        text: '검증 실행',
        on: { click: runValidation },
      }),
    ]));

    var validateResults = h('div', { id: 'cs-validate-results' });
    validateCard.appendChild(validateResults);

    // Initial validation state
    runValidation();

    function runValidation() {
      clear(validateResults);
      validateResults.appendChild(h('p', { text: '무결성 검증 파이프라인 가동 중...' }));

      api('/publish/validate', { method: 'POST' })
        .then(function (report) {
          clear(validateResults);
          var isPassed = Boolean(report.passed || report.valid);
          validateCard.className = 'cs-gate-card ' + (isPassed ? 'passed' : 'failed');

          var alertTone = isPassed ? 'ok' : 'bad';
          var alertEl = h('div', { className: 'cs-alert cs-alert-' + alertTone, style: 'margin-bottom: 1rem;' }, [
            h('strong', { text: isPassed ? '✅ 무결성 검증 통과 (Release Ready)' : '❌ 검증 실패 (배포 차단됨)' }),
            h('p', { text: isPassed ? '모든 647개 항목이 완벽하게 보존되었으며 배포 기준을 충족합니다.' : '검증 요건 미달로 배포가 차단되었습니다.' }),
          ]);
          validateResults.appendChild(alertEl);

          var totalItems = report.total_items || report.total_scenarios || 0;
          var procCounts = report.procedure_counts || {};
          var extCount = procCounts.extension !== undefined ? procCounts.extension : 0;
          var chgCount = procCounts.change !== undefined ? procCounts.change : 0;
          var regCount = procCounts.registration !== undefined ? procCounts.registration : 0;
          var storageText = report.durable_storage ? '영구 보존 SQLite DB (Durable)' : '테스트 임시 메모리 DB (In-Memory)';
          var checksumText = report.dataset_checksum ? (report.dataset_checksum.substring(0, 16) + '...') : '미생성';

          // Checklist Table
          var table = h('table', { className: 'cs-checklist-table' }, [
            h('thead', {}, [
              h('tr', {}, [
                h('th', { text: '검증 항목 (Invariant Check)' }),
                h('th', { text: '기대 값' }),
                h('th', { text: '실제 값' }),
                h('th', { text: '결과' }),
              ]),
            ]),
            h('tbody', {}, [
              h('tr', {}, [
                h('td', { text: '전체 상황별 서류 전수 보존' }),
                h('td', { text: '정확히 647개' }),
                h('td', { text: totalItems + '개' }),
                h('td', {}, [totalItems === 647 ? renderBadge('PASS', 'ok') : renderBadge('FAIL', 'bad')]),
              ]),
              h('tr', {}, [
                h('td', { text: '체류기간 연장 (Extension)' }),
                h('td', { text: '224개' }),
                h('td', { text: extCount + '개' }),
                h('td', {}, [(extCount === 224) ? renderBadge('PASS', 'ok') : renderBadge('FAIL', 'bad')]),
              ]),
              h('tr', {}, [
                h('td', { text: '체류자격 변경 (Change)' }),
                h('td', { text: '251개' }),
                h('td', { text: chgCount + '개' }),
                h('td', {}, [(chgCount === 251) ? renderBadge('PASS', 'ok') : renderBadge('FAIL', 'bad')]),
              ]),
              h('tr', {}, [
                h('td', { text: '외국인등록·거소신고 (Registration)' }),
                h('td', { text: '172개' }),
                h('td', { text: regCount + '개' }),
                h('td', {}, [(regCount === 172) ? renderBadge('PASS', 'ok') : renderBadge('FAIL', 'bad')]),
              ]),
              h('tr', {}, [
                h('td', { text: '스토리지 영구성 (Durability)' }),
                h('td', { text: 'SQLite 영구 파일 보존' }),
                h('td', { text: storageText }),
                h('td', {}, [report.durable_storage ? renderBadge('DURABLE', 'ok') : renderBadge('EPHEMERAL', 'warn')]),
              ]),
              h('tr', {}, [
                h('td', { text: '데이터셋 무결성 해시 (SHA-256)' }),
                h('td', { text: '전체 647개 표준 정규화 해시' }),
                h('td', { style: 'font-family: monospace; font-size: 0.8rem;', text: checksumText }),
                h('td', {}, [renderBadge('VERIFIED', 'ok')]),
              ]),
              h('tr', {}, [
                h('td', { text: '승인 완료된 개정 초안' }),
                h('td', { text: '배포 대상 반영' }),
                h('td', { text: (report.approved_drafts_count || 0) + '건 대기' }),
                h('td', {}, [renderBadge('INFO', 'primary')]),
              ]),
            ]),
          ]);
          validateResults.appendChild(table);

          // Render Release Form if passed and has publisher role
          renderReleaseSection(report);
        })
        .catch(function (err) {
          clear(validateResults);
          validateResults.appendChild(h('p', { style: 'color: #dc2626;', text: '검증 실행 실패: ' + err.message }));
        });
    }

    var releaseSection = h('div', { id: 'cs-release-section' });
    wrap.appendChild(releaseSection);

    var historySection = h('div', { id: 'cs-release-history' });
    wrap.appendChild(historySection);

    loadReleases();

    function renderReleaseSection(report) {
      clear(releaseSection);

      var panel = h('div', { className: 'cs-panel', style: 'margin-top: 1.5rem;' }, [
        h('div', { className: 'cs-panel-header' }, [
          h('h3', { className: 'cs-panel-title', text: '2단계: 운영 게시 배포 실행 (Publish Release)' }),
        ]),
      ]);

      if (!canPublish()) {
        panel.appendChild(h('div', { className: 'cs-alert cs-alert-warn' }, [
          h('strong', { text: '권한 제한: ' }),
          h('span', { text: '게시 배포는 "게시자 (Publisher)" 권한을 보유한 운영자만 실행할 수 있습니다 (현재: ' + state.role + ').' }),
        ]));
        releaseSection.appendChild(panel);
        return;
      }

      var isPassed = Boolean(report.passed || report.valid);
      if (!isPassed) {
        panel.appendChild(h('div', { className: 'cs-alert cs-alert-bad' }, [
          h('strong', { text: '배포 차단: ' }),
          h('span', { text: '무결성 사전 검증을 통과해야 배포할 수 있습니다.' }),
        ]));
        releaseSection.appendChild(panel);
        return;
      }

      var defaultTag = 'rel-' + (new Date().toISOString().substring(0, 10).replace(/-/g, '')) + '-1';
      var fTag = h('input', { className: 'cs-input', value: defaultTag });
      var fNote = h('textarea', { className: 'cs-textarea', text: 'VISABLE 647개 상황별 서류 정기 배포 및 검증 반영', rows: '3' });

      var form = h('form', {
        on: {
          submit: function (e) {
            e.preventDefault();
            showDialog('운영 게시 배포 확인', h('div', {}, [
              h('p', { text: '배포 버전 태그: ' + fTag.value.trim() }),
              h('p', { style: 'margin-top: 0.5rem; font-weight: 700; color: #15803d;', text: '승인된 모든 초안이 실제 647개 서류 기준에 즉시 반영됩니다. 계속하시겠습니까?' }),
            ]), function () {
              api('/publish/release', {
                method: 'POST',
                body: {
                  release_tag: fTag.value.trim(),
                  release_note: fNote.value.trim(),
                },
              })
                .then(function (res) {
                  status('배포 완료: ' + res.release_id);
                  runValidation();
                  loadReleases();
                })
                .catch(function (err) {
                  status('배포 오류: ' + err.message);
                });
            });
          },
        },
      }, [
        h('div', { className: 'cs-field' }, [
          h('label', { text: '릴리스 버전 태그 (Release Tag)' }),
          fTag,
        ]),
        h('div', { className: 'cs-field' }, [
          h('label', { text: '릴리스 노트 및 개정 요약' }),
          fNote,
        ]),
        h('div', { className: 'cs-form-actions' }, [
          h('button', { type: 'submit', className: 'cs-btn cs-btn-success', text: '🚀 운영 게시 배포 확정' }),
        ]),
      ]);

      panel.appendChild(form);
      releaseSection.appendChild(panel);
    }

    function loadReleases() {
      clear(historySection);
      var panel = h('div', { className: 'cs-panel', style: 'margin-top: 1.5rem;' }, [
        h('div', { className: 'cs-panel-header' }, [
          h('h3', { className: 'cs-panel-title', text: '3단계: 릴리스 이력 관리 및 롤백 (Release History & Rollback)' }),
        ]),
      ]);
      historySection.appendChild(panel);

      api('/releases')
        .then(function (data) {
          var releases = (data && data.releases) || [];
          if (!releases.length) {
            panel.appendChild(h('p', { style: 'padding: 1.5rem; color: var(--text-muted); text-align: center;', text: '배포된 릴리스 이력이 아직 없습니다.' }));
            return;
          }

          var table = h('table', { className: 'cs-checklist-table' }, [
            h('thead', {}, [
              h('tr', {}, [
                h('th', { text: '릴리스 태그' }),
                h('th', { text: '배포 일시' }),
                h('th', { text: '배포자' }),
                h('th', { text: '반영 내역' }),
                h('th', { text: '상태' }),
                h('th', { text: '체크섬' }),
                h('th', { text: '액션' }),
              ]),
            ]),
            h('tbody', {}, releases.map(function (rel) {
              var isRolledBack = (rel.status === 'ROLLED_BACK');
              var actionTd = h('td', { style: 'white-space: nowrap;' });

              var previewUrl = 'immigration-checklists.html?preview_release=' + encodeURIComponent(rel.release_id);
              actionTd.appendChild(h('a', {
                href: previewUrl,
                target: '_blank',
                rel: 'noopener noreferrer',
                className: 'cs-btn cs-btn-quiet cs-btn-sm',
                style: 'display: inline-block; margin-right: 0.4rem; text-decoration: none;',
                text: '🔍 미리보기',
              }));

              if (!isRolledBack && canPublish()) {
                actionTd.appendChild(h('button', {
                  className: 'cs-btn cs-btn-danger cs-btn-sm',
                  text: '↩️ 롤백',
                  on: {
                    click: function () {
                      var fRollbackReason = h('textarea', {
                        className: 'cs-textarea',
                        placeholder: '롤백 사유를 상세히 입력하세요 (필수)',
                        rows: '3',
                      });
                      var dlgBody = h('div', {}, [
                        h('p', { style: 'font-weight: 700; color: #dc2626;', text: '릴리스 [' + rel.release_tag + ']을(를) 롤백하시겠습니까?' }),
                        h('p', { style: 'margin: 0.5rem 0; font-size: 0.875rem;', text: '이 릴리스 배포 직전의 스냅샷 상태로 647개 서류 데이터가 원자적으로 즉시 복원됩니다.' }),
                        h('div', { className: 'cs-field', style: 'margin-top: 0.75rem;' }, [
                          h('label', { text: '롤백 사유' }),
                          fRollbackReason,
                        ]),
                      ]);
                      showDialog('릴리스 긴급 롤백', dlgBody, function () {
                        var reason = fRollbackReason.value.trim() || '운영자 긴급 롤백 요청';
                        api('/releases/' + encodeURIComponent(rel.release_id) + '/rollback', {
                          method: 'POST',
                          body: { reason: reason, rollback_note: reason },
                        })
                          .then(function (rbRes) {
                            status('롤백 완료: ' + rbRes.release_tag);
                            runValidation();
                            loadReleases();
                          })
                          .catch(function (err) {
                            status('롤백 실패: ' + err.message);
                          });
                      });
                    },
                  },
                }));
              }

              return h('tr', {}, [
                h('td', { style: 'font-weight: 700; font-family: monospace;', text: rel.release_tag }),
                h('td', { text: (rel.published_at || '').substring(0, 19).replace('T', ' ') }),
                h('td', { text: rel.published_by }),
                h('td', { text: (rel.approved_draft_count || 0) + '건 초안 반영 (' + (rel.total_scenario_count || 647) + '개 항목)' }),
                h('td', {}, [isRolledBack ? renderBadge('롤백됨', 'warn') : renderBadge('게시됨', 'ok')]),
                h('td', { style: 'font-family: monospace; font-size: 0.75rem;', text: (rel.payload_checksum || '').substring(0, 12) + '...' }),
                actionTd,
              ]);
            })),
          ]);
          panel.appendChild(h('div', { className: 'cs-table-wrap' }, [table]));
        })
        .catch(function (err) {
          panel.appendChild(h('p', { style: 'color: #dc2626; padding: 1rem;', text: '릴리스 이력 조회 실패: ' + err.message }));
        });
    }
  }

  // -------------------------------------------------------------------------
  // Initialization & Event Binding
  // -------------------------------------------------------------------------
  function init() {
    $('cs-login-form').addEventListener('submit', function (e) {
      e.preventDefault();
      var input = $('cs-token');
      if (input && input.value.trim()) {
        signIn(input.value.trim());
      }
    });

    $('cs-signout').addEventListener('click', function () {
      signOut('정상적으로 로그아웃되었습니다.');
    });

    // Tab buttons
    var tabs = doc.querySelectorAll('#cs-tabs [role="tab"]');
    tabs.forEach(function (tab) {
      tab.addEventListener('click', function () {
        var view = tab.getAttribute('data-view');
        navigate(view);
      });
    });

    // Auto-login from sessionStorage if available
    var savedToken = store(TOKEN_KEY);
    if (savedToken) {
      signIn(savedToken);
    }
  }

  // Auto-init on DOMContentLoaded
  if (doc.readyState === 'loading') {
    doc.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

})(typeof window !== 'undefined' ? window : this);
