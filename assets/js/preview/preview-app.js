/**
 * PreView by Paradiso — standalone pre-arrival pre-check app.
 *
 * Pure browser JS, no dependencies, no LLM calls, no eval.
 * - Deterministic helpers are separated from DOM rendering and exposed on
 *   globalThis.PreViewApp so Node smoke tests can exercise them headlessly.
 * - The backend proxy (GET /api/preview/mission) is attempted first; on any
 *   failure the labeled local MVP sample data from preview-data.js renders,
 *   with a visible fallback notice.
 * - Every dynamic value reaches the DOM via textContent (never innerHTML),
 *   and external links must match a strict official-host allowlist.
 */
(function () {
  'use strict';

  var DEFAULT_API_BASE = 'https://web-production-14f9a.up.railway.app';
  var API_TIMEOUT_MS = 6000;

  var ALLOWED_LINK_PREFIXES = [
    'https://overseas.mofa.go.kr/',
    'https://www.mofa.go.kr/',
    'https://www.data.go.kr/'
  ];

  var PURPOSES = {
    study: { ko: '유학·학업', en: 'Study', manualCodes: ['D-2', 'D-4'] },
    exchange: { ko: '교환·공공외교 프로그램', en: 'Exchange / public diplomacy', manualCodes: ['D-2'] },
    business: { ko: '비즈니스·상용', en: 'Business', manualCodes: ['C-4', 'C-3'] },
    family: { ko: '가족·장기 체류 준비', en: 'Family / long stay', manualCodes: [] },
    short: { ko: '단기 방문', en: 'Short visit', manualCodes: ['C-3'] },
    notsure: { ko: '아직 잘 모름', en: 'Not sure', manualCodes: [] }
  };

  /* ------------------------------------------------------ pure helpers -- */

  function escapeHtml(value) {
    return String(value == null ? '' : value)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function getData() {
    if (typeof globalThis !== 'undefined' && globalThis.PREVIEW_FALLBACK_DATA) {
      return globalThis.PREVIEW_FALLBACK_DATA;
    }
    return null;
  }

  function isAllowedLink(url) {
    if (typeof url !== 'string') return false;
    for (var i = 0; i < ALLOWED_LINK_PREFIXES.length; i += 1) {
      if (url.indexOf(ALLOWED_LINK_PREFIXES[i]) === 0) return true;
    }
    return false;
  }

  function findBundle(data, countryId) {
    if (!data || !data.bundles || !countryId) return null;
    var wanted = String(countryId).toLowerCase();
    for (var i = 0; i < data.bundles.length; i += 1) {
      var bundle = data.bundles[i];
      if (bundle.id === wanted || (bundle.iso2 || '').toLowerCase() === wanted) return bundle;
    }
    return null;
  }

  function purposeLabel(purposeKey, lang) {
    var entry = PURPOSES[purposeKey] || PURPOSES.notsure;
    return lang === 'en' ? entry.en : entry.ko;
  }

  function manualRefsForPurpose(data, purposeKey) {
    if (!data || !data.manual || !Array.isArray(data.manual.records)) return [];
    var codes = (PURPOSES[purposeKey] || PURPOSES.notsure).manualCodes;
    var out = [];
    for (var i = 0; i < codes.length; i += 1) {
      for (var j = 0; j < data.manual.records.length; j += 1) {
        if (data.manual.records[j].code === codes[i]) out.push(data.manual.records[j]);
      }
    }
    return out;
  }

  function buildChecklist(purposeKey, bundle) {
    var countryKo = bundle ? bundle.countryKo : '현재 체류국';
    var items = [
      { ko: '여권 유효기간과 상태를 확인하세요 (기본 준비).', en: 'Check your passport validity and condition.' },
      {
        ko: countryKo + ' 기준 관할 재외공관을 확인하세요 (공관 카드 참고).',
        en: 'Confirm the Korean mission with jurisdiction over your current country.'
      },
      {
        ko: '사증 필요 여부를 확인하세요 — 사증 면제협정·무사증 해당 여부는 공식 원문 확인 필요.',
        en: 'Confirm whether you need a visa; waiver status must be checked against official sources.'
      },
      {
        ko: '공관 공식 안내 확인 — 공지·사증 게시판에서 최신 안내를 확인하세요.',
        en: 'Read the mission’s latest official notices and visa board.'
      },
      {
        ko: '접수 방식(방문·대행·온라인 여부)은 공관마다 다릅니다. 관할 공관에 최종 확인하세요.',
        en: 'Application intake methods differ by mission — confirm with the mission itself.'
      }
    ];
    if (purposeKey === 'study' || purposeKey === 'exchange') {
      items.push({
        ko: '교육기관·프로그램 주관기관이 안내하는 절차와 공관 안내를 함께 확인하세요.',
        en: 'Cross-check guidance from your school/program with the mission’s guidance.'
      });
    } else if (purposeKey === 'business') {
      items.push({
        ko: '초청·일정 관련 안내가 공관 공지에 있는지 확인하세요.',
        en: 'Check the mission notices for invitation/schedule-related guidance.'
      });
    } else if (purposeKey === 'family') {
      items.push({
        ko: '가족·장기 체류 목적은 유형이 다양합니다. 어떤 절차가 해당되는지 관할 공관에 최종 확인하세요.',
        en: 'Family/long-stay cases vary — confirm the applicable procedure with the mission.'
      });
    } else if (purposeKey === 'notsure') {
      items.push({
        ko: '방문 목적이 정해지면 해당 목적 기준으로 다시 확인하세요. 목적에 따라 절차가 달라집니다.',
        en: 'Once your purpose is decided, re-check — procedures depend on purpose.'
      });
    }
    return items;
  }

  function buildContactScript(options) {
    var opts = options || {};
    var nationality = String(opts.nationality || '').trim() || '외국';
    var purposeKo = purposeLabel(opts.purpose, 'ko');
    var purposeEn = purposeLabel(opts.purpose, 'en');
    var ko =
      '안녕하세요. 저는 ' + nationality + ' 국적자이며, ' + purposeKo +
      ' 목적으로 한국 방문을 준비하고 있습니다. 제 경우 사증 신청이 필요한지, ' +
      '필요하다면 접수 방법과 공식 안내 페이지를 알려주실 수 있을까요? ' +
      '공관 공식 안내에 따라 준비하겠습니다. 감사합니다.';
    var en =
      'Hello, I am a national of ' + nationality + ' preparing to visit Korea for ' +
      purposeEn.toLowerCase() + ' purposes. Could you let me know whether I need to apply for a visa, ' +
      'and if so, how applications are accepted and where the official guidance is posted? Thank you.';
    return { ko: ko, en: en };
  }

  function apiFallbackMessage(data) {
    return (data && data.apiFallbackMessageKo) ||
      '현재 공공데이터 API 응답을 불러오지 못해 MVP 샘플 데이터를 표시합니다. 최종 정보는 관할 재외공관 공식 원문을 확인해야 합니다.';
  }

  function unsupportedMessage(data) {
    return (data && data.unsupportedCountryMessageKo) ||
      '선택한 국가는 아직 MVP 샘플 범위에 없습니다. 관할 재외공관 공식 안내를 확인해 주세요.';
  }

  function apiBase() {
    try {
      if (typeof window !== 'undefined' && window.PARADISO_BACKEND_URL && String(window.PARADISO_BACKEND_URL).trim()) {
        return String(window.PARADISO_BACKEND_URL).trim();
      }
    } catch (e) { /* ignore */ }
    try {
      var host = (typeof location !== 'undefined' && location.hostname) || '';
      if (host === 'localhost' || host === '127.0.0.1' ||
          (typeof location !== 'undefined' && location.protocol === 'file:')) {
        return '';
      }
    } catch (e2) { /* ignore */ }
    return DEFAULT_API_BASE;
  }

  var PreViewApp = {
    escapeHtml: escapeHtml,
    getData: getData,
    isAllowedLink: isAllowedLink,
    findBundle: findBundle,
    purposeLabel: purposeLabel,
    manualRefsForPurpose: manualRefsForPurpose,
    buildChecklist: buildChecklist,
    buildContactScript: buildContactScript,
    apiFallbackMessage: apiFallbackMessage,
    unsupportedMessage: unsupportedMessage,
    apiBase: apiBase,
    PURPOSES: PURPOSES,
    ALLOWED_LINK_PREFIXES: ALLOWED_LINK_PREFIXES
  };
  if (typeof globalThis !== 'undefined') globalThis.PreViewApp = PreViewApp;
  if (typeof window !== 'undefined') window.PreViewApp = PreViewApp;

  /* ------------------------------------------------- DOM below this line -- */
  if (typeof document === 'undefined') return;

  function el(tag, className, text) {
    var node = document.createElement(tag);
    if (className) node.className = className;
    if (text != null) node.textContent = text;
    return node;
  }

  function officialLink(url, label) {
    if (!isAllowedLink(url)) return el('span', 'pv-link-blocked', label);
    var anchor = el('a', 'pv-link', label + ' ↗');
    anchor.href = url;
    anchor.target = '_blank';
    anchor.rel = 'noopener noreferrer';
    return anchor;
  }

  function badge(text, variant) {
    return el('span', 'pv-badge' + (variant ? ' pv-badge-' + variant : ''), text);
  }

  function card(titleKo, titleEn, badgeText, badgeVariant) {
    var section = el('section', 'pv-card');
    var head = el('div', 'pv-card-head');
    var title = el('h3', 'pv-card-title', titleKo);
    title.appendChild(el('span', 'pv-card-title-en', titleEn));
    head.appendChild(title);
    if (badgeText) head.appendChild(badge(badgeText, badgeVariant));
    section.appendChild(head);
    return section;
  }

  function setStatus(state, message) {
    var node = document.getElementById('pvStatus');
    if (!node) return;
    node.className = 'pv-status pv-status-' + state;
    node.textContent = message;
  }

  function renderMissionCard(container, bundle, apiResult, data) {
    var isLive = !!(apiResult && apiResult.ok && apiResult.mode === 'live_api' &&
      Array.isArray(apiResult.items) && apiResult.items.length > 0);
    var c = card('공관', 'Mission', isLive ? '공공데이터 API 기반' : data.sampleBadgeKo, isLive ? 'live' : 'sample');

    if (isLive) {
      apiResult.items.slice(0, 4).forEach(function (item) {
        var row = el('div', 'pv-mission');
        row.appendChild(el('p', 'pv-mission-name', item.missionNameKo || '공관명 확인 필요'));
        var metaBits = [];
        if (item.missionTypeKo) metaBits.push(item.missionTypeKo);
        if (item.countryNameKo) metaBits.push(item.countryNameKo);
        if (item.countryIso2) metaBits.push(item.countryIso2);
        if (metaBits.length) row.appendChild(el('p', 'pv-mission-meta', metaBits.join(' · ')));
        if (item.addressKo) row.appendChild(el('p', 'pv-mission-line', '주소: ' + item.addressKo));
        if (item.phone) row.appendChild(el('p', 'pv-mission-line', '대표전화: ' + item.phone));
        if (item.emergencyPhone) row.appendChild(el('p', 'pv-mission-line', '긴급전화: ' + item.emergencyPhone));
        if (item.consularCallCenter) row.appendChild(el('p', 'pv-mission-line', '영사콜센터: ' + item.consularCallCenter));
        c.appendChild(row);
      });
      if (apiResult.source) {
        c.appendChild(el('p', 'pv-card-note',
          '출처: ' + (apiResult.source.provider || '') + ' · ' + (apiResult.source.datasetName || '') +
          ' (조회일 ' + (apiResult.source.fetchedAt || '') + ')'));
      }
    } else if (bundle) {
      bundle.posts.forEach(function (post) {
        var row = el('div', 'pv-mission');
        row.appendChild(el('p', 'pv-mission-name', post.nameKo));
        row.appendChild(el('p', 'pv-mission-meta', post.typeKo + ' · ' + post.cityKo));
        row.appendChild(el('p', 'pv-mission-line', post.contactNoteKo));
        var linkLine = el('p', 'pv-mission-link');
        linkLine.appendChild(officialLink(post.officialSiteUrl, '공관 공식 홈페이지'));
        row.appendChild(linkLine);
        c.appendChild(row);
      });
    } else {
      c.appendChild(el('p', 'pv-card-note',
        '관할 재외공관은 외교부 재외공관 정보(공공데이터)와 외교부 안내에서 확인할 수 있습니다. 공식 원문 확인 필요.'));
    }
    container.appendChild(c);
  }

  function renderEntryPrecheckCard(container, bundle, data) {
    var c = card('입국 전 확인', 'Entry pre-check', '공식 공개자료 기반', 'official');
    if (bundle && bundle.entryPrecheck) {
      c.appendChild(el('p', 'pv-pill-line', '상태: ' + bundle.entryPrecheck.statusKo));
      c.appendChild(el('p', 'pv-card-body', bundle.entryPrecheck.summaryKo));
      var list = el('ul', 'pv-list');
      (bundle.entryPrecheck.checkPointsKo || []).forEach(function (point) {
        list.appendChild(el('li', null, point));
      });
      c.appendChild(list);
    } else {
      c.appendChild(el('p', 'pv-card-body',
        '사증 면제협정·무사증 해당 여부는 국가별로 다르며, 이 MVP 샘플 범위 밖입니다. 공식 원문 확인 필요.'));
    }
    var refLine = el('p', 'pv-card-note');
    refLine.appendChild(document.createTextNode('참고 자료: '));
    refLine.appendChild(officialLink('https://www.data.go.kr/data/15099235/fileData.do', '외교부_국가별 사증 면제협정 체결현황'));
    c.appendChild(refLine);
    c.appendChild(el('p', 'pv-card-caution',
      '이 카드는 입국 전 확인 맥락 참고용입니다. 무사증 입국 가능 여부를 보증하지 않으며, 관할 공관에 최종 확인하세요.'));
    container.appendChild(c);
  }

  function renderNoticeCard(container, bundle, data) {
    var c = card('공관 공개 안내', 'Mission notice', '공식 공개자료 기반', 'official');
    var notices = (bundle && bundle.missionNotices) || [];
    if (!notices.length) {
      c.appendChild(el('p', 'pv-card-body',
        '이 국가의 공관 공개 안내 참조는 아직 샘플에 없습니다. 공관 공식 홈페이지의 공지·사증 게시판을 확인하세요.'));
    }
    notices.forEach(function (notice) {
      var row = el('div', 'pv-notice');
      row.appendChild(el('p', 'pv-notice-title', notice.title));
      row.appendChild(el('p', 'pv-notice-meta', notice.post + ' · ' + (notice.fetchedAt ? '수집일 ' + notice.fetchedAt : '본문 미수집')));
      row.appendChild(el('p', 'pv-notice-snippet', notice.textSnippet));
      var linkLine = el('p', 'pv-mission-link');
      linkLine.appendChild(officialLink(notice.url, '공식 게시판/게시글 열기'));
      row.appendChild(linkLine);
      c.appendChild(row);
    });
    c.appendChild(el('p', 'pv-card-caution',
      '발췌는 완전한 공식 체크리스트가 아닙니다. 반드시 공관 공식 안내 확인 후 준비하세요.'));
    container.appendChild(c);
  }

  function renderManualCard(container, purposeKey, data) {
    var c = card('매뉴얼 기준 참고', 'Manual reference', '매뉴얼 기준 참고', 'manual');
    var records = manualRefsForPurpose(data, purposeKey);
    if (!records.length) {
      c.appendChild(el('p', 'pv-card-body',
        '이 목적에 대응하는 매뉴얼 참고 항목이 아직 없습니다. 해당 절차 유형은 관할 재외공관 공식 안내에서 확인해 주세요. 공식 원문 확인 필요.'));
    }
    records.forEach(function (record) {
      var row = el('div', 'pv-manual');
      row.appendChild(el('p', 'pv-manual-code', record.headingKo));
      row.appendChild(el('p', 'pv-manual-summary', record.issuanceRouteSummaryKo));
      var pointer = record.sourcePointer || {};
      row.appendChild(el('p', 'pv-manual-meta',
        '출전: ' + (data.manual.sourceLabelKo || '사증발급 안내매뉴얼') +
        (pointer.page ? ' · p.' + pointer.page : '')));
      c.appendChild(row);
    });
    c.appendChild(el('p', 'pv-card-caution', data.manual ? data.manual.usageBoundaryKo :
      '매뉴얼 기준 참고는 참고 레이어이며, 최종 확인은 관할 재외공관 공식 안내를 따릅니다.'));
    container.appendChild(c);
  }

  function renderSafetyCard(container, bundle) {
    var c = card('안전 참고', 'Safety note', 'MVP 샘플 데이터', 'sample');
    if (bundle && bundle.safety) {
      c.appendChild(el('p', 'pv-pill-line', '상태: ' + bundle.safety.statusKo));
      c.appendChild(el('p', 'pv-card-body', bundle.safety.summaryKo));
    } else {
      c.appendChild(el('p', 'pv-card-body',
        '국가별 안전정보는 외교부 공공데이터로 제공됩니다. 이 MVP 샘플에는 수록되어 있지 않습니다. 공식 원문 확인 필요.'));
    }
    container.appendChild(c);
  }

  function renderChecklistCard(container, purposeKey, bundle, langPref) {
    var c = card('준비 체크리스트', 'Checklist', '입국 전 확인사항', 'official');
    var list = el('ol', 'pv-checklist');
    buildChecklist(purposeKey, bundle).forEach(function (item) {
      var li = el('li', null, item.ko);
      if (langPref === 'en' && item.en) li.appendChild(el('span', 'pv-check-en', item.en));
      list.appendChild(li);
    });
    c.appendChild(list);
    c.appendChild(el('p', 'pv-card-caution',
      '이 체크리스트는 확인 절차 안내이며, 요구서류 목록이 아닙니다. 서류는 공관 공식 안내에서 확인하세요.'));
    container.appendChild(c);
  }

  function renderContactCard(container, purposeKey, nationality, langPref) {
    var c = card('문의 문장', 'Contact script', null, null);
    var script = buildContactScript({ purpose: purposeKey, nationality: nationality });
    c.appendChild(el('p', 'pv-script-label', '한국어 문의 예시'));
    c.appendChild(el('p', 'pv-script', script.ko));
    if (langPref !== 'ko') {
      c.appendChild(el('p', 'pv-script-label', 'English example'));
      c.appendChild(el('p', 'pv-script', script.en));
    }
    c.appendChild(el('p', 'pv-card-note',
      '공관마다 문의 채널(이메일·게시판·전화)이 다릅니다. 공식 홈페이지의 안내 채널을 이용하세요.'));
    container.appendChild(c);
  }

  function renderSourcesCard(container, bundle, apiResult) {
    var c = card('출처', 'Sources', 'Source-grounded', 'official');
    var list = el('ul', 'pv-sources');
    if (apiResult && apiResult.ok && apiResult.source) {
      var liveItem = el('li', 'pv-source-row');
      liveItem.appendChild(el('span', 'pv-source-state pv-source-live', 'LIVE API'));
      liveItem.appendChild(el('span', 'pv-source-title',
        (apiResult.source.datasetName || '') + ' — ' + (apiResult.source.provider || '')));
      list.appendChild(liveItem);
    }
    var sources = (bundle && bundle.sources) || [];
    sources.forEach(function (source) {
      var item = el('li', 'pv-source-row');
      item.appendChild(el('span', 'pv-source-state', source.evidenceLevel || ''));
      item.appendChild(el('span', 'pv-source-title', source.titleKo));
      if (source.url && isAllowedLink(source.url)) {
        item.appendChild(officialLink(source.url, '원문'));
      }
      list.appendChild(item);
    });
    c.appendChild(list);
    container.appendChild(c);
  }

  function renderResults(formValues, apiResult) {
    var data = getData();
    var container = document.getElementById('pvResults');
    if (!container || !data) return;
    container.textContent = '';

    var bundle = findBundle(data, formValues.country);
    var summary = el('div', 'pv-result-summary');
    var headline = bundle
      ? bundle.countryKo + ' (' + bundle.countryEn + ') 체류자 기준 입국 전 확인사항'
      : '입국 전 확인사항';
    summary.appendChild(el('h2', 'pv-result-title', headline));
    summary.appendChild(el('p', 'pv-result-meta',
      '방문 목적: ' + purposeLabel(formValues.purpose, 'ko') +
      (formValues.nationality ? ' · 국적: ' + formValues.nationality : '')));
    container.appendChild(summary);

    if (!bundle) {
      var warn = el('div', 'pv-callout pv-callout-warn');
      warn.setAttribute('role', 'note');
      warn.appendChild(el('p', null, unsupportedMessage(data)));
      container.appendChild(warn);
    }

    if (data.isSample && !(apiResult && apiResult.ok)) {
      var sampleNote = el('div', 'pv-callout');
      sampleNote.setAttribute('role', 'note');
      sampleNote.appendChild(el('p', null, data.sampleNoticeKo));
      container.appendChild(sampleNote);
    }

    var grid = el('div', 'pv-grid');
    renderMissionCard(grid, bundle, apiResult, data);
    renderEntryPrecheckCard(grid, bundle, data);
    renderNoticeCard(grid, bundle, data);
    renderManualCard(grid, formValues.purpose, data);
    renderSafetyCard(grid, bundle);
    renderChecklistCard(grid, formValues.purpose, bundle, formValues.language);
    renderContactCard(grid, formValues.purpose, formValues.nationality, formValues.language);
    renderSourcesCard(grid, bundle, apiResult);
    container.appendChild(grid);

    var disclaimer = el('div', 'pv-callout pv-callout-strong');
    disclaimer.setAttribute('role', 'note');
    disclaimer.appendChild(el('p', null, data.disclaimerKo));
    container.appendChild(disclaimer);

    container.hidden = false;
    try {
      container.scrollIntoView({ behavior: 'smooth', block: 'start' });
    } catch (e) { /* ignore */ }
  }

  function fetchMissionFromApi(iso2) {
    var base = apiBase();
    if (typeof fetch !== 'function') return Promise.resolve(null);
    var controller = typeof AbortController === 'function' ? new AbortController() : null;
    var timer = controller ? setTimeout(function () { controller.abort(); }, API_TIMEOUT_MS) : null;
    var url = base + '/api/preview/mission?country=' + encodeURIComponent(iso2);
    return fetch(url, { signal: controller ? controller.signal : undefined })
      .then(function (response) {
        if (!response.ok && response.status !== 200) return null;
        return response.json();
      })
      .catch(function () { return null; })
      .then(function (payload) {
        if (timer) clearTimeout(timer);
        return payload;
      });
  }

  function readForm() {
    var country = document.getElementById('pvCountry');
    var nationalitySelect = document.getElementById('pvNationality');
    var nationalityOther = document.getElementById('pvNationalityOther');
    var purpose = document.getElementById('pvPurpose');
    var language = document.getElementById('pvLanguage');
    var nationality = nationalitySelect ? nationalitySelect.value : '';
    if (nationality === 'other' && nationalityOther) {
      nationality = String(nationalityOther.value || '').trim().slice(0, 40);
    } else if (nationalitySelect) {
      var selected = nationalitySelect.options[nationalitySelect.selectedIndex];
      nationality = selected && selected.value !== 'other' ? selected.textContent : '';
    }
    return {
      country: country ? country.value : '',
      nationality: nationality,
      purpose: purpose ? purpose.value : 'notsure',
      language: language ? language.value : 'ko'
    };
  }

  function onSubmit(event) {
    event.preventDefault();
    var values = readForm();
    var data = getData();
    var bundle = findBundle(data, values.country);

    if (!bundle) {
      setStatus('fallback', apiFallbackMessage(data));
      renderResults(values, null);
      return;
    }

    setStatus('checking', '공공데이터 API 확인 중…');
    fetchMissionFromApi(bundle.iso2).then(function (payload) {
      var live = payload && payload.ok === true && payload.mode === 'live_api' &&
        Array.isArray(payload.items) && payload.items.length > 0;
      if (live) {
        setStatus('live', (data && data.apiLiveMessageKo) || '공공데이터 API 기반');
        renderResults(values, payload);
      } else {
        setStatus('fallback', apiFallbackMessage(data));
        renderResults(values, null);
      }
    });
  }

  function initThemeToggle() {
    var button = document.getElementById('pvBrightToggle');
    if (!button) return;
    button.addEventListener('click', function () {
      var body = document.body;
      var isDark = body.getAttribute('data-theme') === 'dark';
      if (isDark) {
        body.removeAttribute('data-theme');
      } else {
        body.setAttribute('data-theme', 'dark');
      }
      try {
        localStorage.setItem('paradiso:brightness', isDark ? 'light' : 'dark');
      } catch (e) { /* ignore */ }
    });
  }

  function toggleNationalityOther() {
    var select = document.getElementById('pvNationality');
    var wrap = document.getElementById('pvNationalityOtherWrap');
    if (!select || !wrap) return;
    wrap.hidden = select.value !== 'other';
  }

  function applyPersistedBrightness() {
    try {
      if (localStorage.getItem('paradiso:brightness') === 'dark') {
        document.body.setAttribute('data-theme', 'dark');
      }
    } catch (e) { /* ignore */ }
  }

  function init() {
    applyPersistedBrightness();
    var form = document.getElementById('pvForm');
    if (form) form.addEventListener('submit', onSubmit);
    var nationality = document.getElementById('pvNationality');
    if (nationality) nationality.addEventListener('change', toggleNationalityOther);
    initThemeToggle();
    setStatus('idle', '입력 후 "입국 전 확인사항 보기"를 누르면 공공데이터 API를 먼저 시도하고, 실패 시 MVP 샘플 데이터로 안내합니다.');
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
