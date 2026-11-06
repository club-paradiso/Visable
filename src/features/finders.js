// @ts-nocheck
/**
 * Registered-agent finder and designated-hospital finder (Phase 3, moved verbatim from
 * index.html lines 25572-25775 and 25574-25773).
 * Legacy IIFEs kept as-is: they fetch data/agent_registry_2026-04-30.json and
 * data/designated_medical_institutions_2026_11_02.json with cache:'no-cache', use the inline globals
 * tx(), localizeRegion() and the paradiso-language-applied event, and expose window.updateAgentFinderLanguage /
 * window.updateMedFinderLanguage for applyLanguage() (compatibility surface, ADR-009).
 * They used to run at parse time; as a module they run after parsing, so the two fetches start a few
 * milliseconds later — both render into modals that are closed at that point. Covered by
 * tests/golden/specs/finders.spec.mjs.
 */

// ── Registered immigration agent finder ──
(function initAgentFinder() {
  const root = document.getElementById('agentFinder');
  if (!root) return;
  const regionSel = document.getElementById('agentFinderRegion');
  const keywordIn = document.getElementById('agentFinderKeyword');
  const countEl = document.getElementById('agentFinderCount');
  const listEl = document.getElementById('agentFinderList');
  const emptyEl = document.getElementById('agentFinderEmpty');
  const errorEl = document.getElementById('agentFinderError');
  const retryBtn = document.getElementById('agentFinderRetry');
  const promptEl = document.getElementById('agentFinderPrompt');
  const loadingEl = document.getElementById('agentFinderLoading');
  const moreEl = document.getElementById('agentFinderMore');
  const showMoreBtn = document.getElementById('agentFinderShowMore');
  let dataset = { agencies: [], regions: [], meta: {} };
  const PAGE_SIZE = 12;
  let filteredAgencies = [];
  let visibleCount = 0;
  let selectedJejuCity = '';

  function escapeText(s) {
    return String(s == null ? '' : s)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
  }
  function copyToClipboard(text) {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      return navigator.clipboard.writeText(text);
    }
    return new Promise(function (resolve, reject) {
      try {
        const ta = document.createElement('textarea');
        ta.value = text;
        ta.setAttribute('readonly', '');
        ta.style.position = 'absolute';
        ta.style.left = '-9999px';
        document.body.appendChild(ta);
        ta.select();
        const ok = document.execCommand && document.execCommand('copy');
        document.body.removeChild(ta);
        ok ? resolve() : reject(new Error('copy command failed'));
      } catch (err) { reject(err); }
    });
  }
  function buildCard(a) {
    const name = escapeText(a.name);
    const region = escapeText([a.province_short || a.region1 || a.province, a.region2 || a.city_or_district].filter(Boolean).join(' · '));
    const address = a.address ? escapeText(a.address) : '';
    const phone = (a.phone || '').trim();
    const displayPhone = (a.display_phone || phone).trim();
    const phoneSafe = phone.replace(/[^0-9+\-]/g, '');
    const q = encodeURIComponent(a.map_query || a.address || a.name || '');
    const naverHref = 'https://map.naver.com/p/search/' + q;
    const kakaoHref = 'https://map.kakao.com/link/search/' + q;
    const phoneBtn = phone
      ? '<a href="tel:' + escapeText(phoneSafe) + '" rel="nofollow">' + escapeText(tx('agentPhone', { phone: displayPhone })) + '</a>'
      : '';
    const copyBtn = address
      ? '<button type="button" data-agent-copy="' + escapeText(a.address) + '">' + escapeText(tx('agentCopyAddress')) + '</button>'
      : '';
    return ''
      + '<li class="p-agent-finder__card">'
      +   '<span class="p-agent-finder__region">' + region + '</span>'
      +   '<h3>' + name + '</h3>'
      +   (address ? '<address>' + address + '</address>' : '')
      +   '<div class="p-agent-finder__actions">'
      +     '<a href="' + naverHref + '" target="_blank" rel="noopener noreferrer">' + escapeText(tx('agentNaver')) + '</a>'
      +     '<a href="' + kakaoHref + '" target="_blank" rel="noopener noreferrer">' + escapeText(tx('agentKakao')) + '</a>'
      +     copyBtn
      +     phoneBtn
      +   '</div>'
      + '</li>';
  }
  function renderSlice() {
    const slice = filteredAgencies.slice(0, visibleCount);
    if (filteredAgencies.length === 0) {
      listEl.innerHTML = '';
      emptyEl.hidden = false;
      countEl.textContent = '';
      moreEl.hidden = true;
    } else {
      emptyEl.hidden = true;
      listEl.innerHTML = slice.map(buildCard).join('');
      if (visibleCount >= filteredAgencies.length) {
        countEl.textContent = tx('agentCountAll', { count: filteredAgencies.length });
        moreEl.hidden = true;
      } else {
        countEl.textContent = tx('agentCountShowing', { showing: slice.length, total: filteredAgencies.length });
        moreEl.hidden = false;
      }
    }
  }
  function applyFilter() {
    const region = regionSel.value;
    const kw = (keywordIn.value || '').trim().toLowerCase();
    const hasSearch = !!(region || kw || selectedJejuCity);
    if (!hasSearch) {
      promptEl.hidden = false;
      listEl.innerHTML = '';
      countEl.textContent = tx('agentTotalCount', { count: dataset.agencies.length }) || `총 ${dataset.agencies.length}개 기관`;
      emptyEl.hidden = true;
      moreEl.hidden = true;
      return;
    }
    promptEl.hidden = true;
    filteredAgencies = dataset.agencies.filter(function (a) {
      if (region && (a.region1 || a.province) !== region) return false;
      if (selectedJejuCity && (a.region2 || a.city_or_district) !== selectedJejuCity) return false;
      if (!kw) return true;
      const hay = (a.normalized_search_text || ((a.name || '') + ' ' + (a.address || '') + ' ' + (a.phone || '') + ' ' + (a.display_phone || '') + ' ' + (a.region1 || '') + ' ' + (a.region2 || ''))).toLowerCase();
      return hay.indexOf(kw) !== -1;
    });
    visibleCount = PAGE_SIZE;
    renderSlice();
  }
  function populateRegions(regions) {
    regionSel.querySelectorAll('option:not([value=""])').forEach(function (opt) { opt.remove(); });
    const localize = (typeof localizeRegion === 'function') ? localizeRegion : function (r) { return r; };
    const opts = regions.map(function (r) {
      // Value stays the Korean canonical (filtering keys on it); only the label localizes.
      return '<option value="' + escapeText(r) + '">' + escapeText(localize(r)) + '</option>';
    }).join('');
    regionSel.insertAdjacentHTML('beforeend', opts);
  }
  window.updateAgentFinderLanguage = function () {
    if (regionSel) {
      const allOption = regionSel.querySelector('option[value=""]');
      if (allOption) allOption.textContent = tx('agentRegionAll');
    }
    if (typeof localizeFinderRegions === 'function') localizeFinderRegions();
    if (dataset.agencies.length) applyFilter();
  };
  function showError() {
    errorEl.hidden = false;
    listEl.innerHTML = '';
    countEl.textContent = '';
    emptyEl.hidden = true;
    promptEl.hidden = true;
    loadingEl.hidden = true;
    moreEl.hidden = true;
  }
  listEl.addEventListener('click', function (ev) {
    const btn = ev.target.closest('button[data-agent-copy]');
    if (!btn) return;
    ev.preventDefault();
    const addr = btn.getAttribute('data-agent-copy') || '';
    if (!addr) return;
    copyToClipboard(addr).then(function () {
      if (typeof showToast === 'function') showToast(tx('agentCopied'), 'success');
    }).catch(function () {
      if (typeof showToast === 'function') showToast(tx('agentCopyFailed'), 'warning');
    });
  });
  showMoreBtn.addEventListener('click', function () {
    visibleCount += PAGE_SIZE;
    renderSlice();
  });
  regionSel.addEventListener('change', applyFilter);
  keywordIn.addEventListener('input', applyFilter);
  window.addEventListener('paradiso-language-applied', applyFilter);
  const jejuFilterEl = document.getElementById('jejuRegionFilter');
  if (jejuFilterEl) {
    jejuFilterEl.addEventListener('click', function (ev) {
      const pill = ev.target.closest('.jeju-region-pill');
      if (!pill) return;
      const province = pill.dataset.region || '';
      selectedJejuCity = '';
      regionSel.value = province;
      jejuFilterEl.querySelectorAll('.jeju-region-pill').forEach(function (p) {
        p.classList.toggle('jeju-pill-active', p === pill);
        p.setAttribute('aria-pressed', p === pill ? 'true' : 'false');
      });
      applyFilter();
    });
  }

  function loadDataset() {
    loadingEl.hidden = false;
    promptEl.hidden = true;
    errorEl.hidden = true;
    // Parse-time IIFE: runs before the module entry, so it cannot use window.Visable (ADR-009 note).
    fetch('data/agent_registry_2026-04-30.json', { cache: 'no-cache' })
      .then(function (res) {
        if (!res.ok) throw new Error('HTTP ' + res.status);
        return res.json();
      })
      .then(function (json) {
        loadingEl.hidden = true;
        dataset.meta = json && json._meta ? json._meta : {};
        dataset.regions = Array.isArray(json && json.regions) ? json.regions : [];
        dataset.agencies = Array.isArray(json && json.agencies) ? json.agencies : [];
        populateRegions(dataset.regions);
        window.updateAgentFinderLanguage();
        applyFilter();
      })
      .catch(function () {
        loadingEl.hidden = true;
        showError();
      });
  }
  if (retryBtn) retryBtn.addEventListener('click', loadDataset);
  loadDataset();
})();

// ── Ministry of Justice designated medical institution finder ──
(function initMedFinder() {
  const root = document.getElementById('medFinder');
  if (!root) return;
  const chipsEl = document.getElementById('medFinderChips');
  const keywordIn = document.getElementById('medFinderKeyword');
  const clearBtn = document.getElementById('medFinderClear');
  const countEl = document.getElementById('medFinderCount');
  const listEl = document.getElementById('medFinderList');
  const emptyEl = document.getElementById('medFinderEmpty');
  const errorEl = document.getElementById('medFinderError');
  const retryBtn = document.getElementById('medFinderRetry');
  const promptEl = document.getElementById('medFinderPrompt');
  const loadingEl = document.getElementById('medFinderLoading');
  const moreEl = document.getElementById('medFinderMore');
  const showMoreBtn = document.getElementById('medFinderShowMore');
  let dataset = { institutions: [], meta: {} };
  const PAGE_SIZE = 20;
  let filteredInstitutions = [];
  let visibleCount = 0;
  let activeRegion = '';

  function escapeText(s) {
    return String(s == null ? '' : s)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
  }
  function copyToClipboard(text) {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      return navigator.clipboard.writeText(text);
    }
    return new Promise(function (resolve, reject) {
      try {
        const ta = document.createElement('textarea');
        ta.value = text;
        ta.setAttribute('readonly', '');
        ta.style.position = 'absolute';
        ta.style.left = '-9999px';
        document.body.appendChild(ta);
        ta.select();
        const ok = document.execCommand && document.execCommand('copy');
        document.body.removeChild(ta);
        ok ? resolve() : reject(new Error('copy command failed'));
      } catch (err) { reject(err); }
    });
  }
  function buildCard(inst) {
    const name = escapeText(inst.institution_name);
    const region = escapeText(inst.region);
    const address = inst.address ? escapeText(inst.address) : '';
    const phone = (inst.phone || '').trim();
    const phoneSafe = phone.replace(/[^0-9+\-]/g, '');
    const mapQuery = encodeURIComponent((inst.institution_name || '') + ' ' + (inst.address || ''));
    const naverHref = 'https://map.naver.com/p/search/' + mapQuery;
    const kakaoHref = 'https://map.kakao.com/link/search/' + mapQuery;
    const phoneBtn = phoneSafe
      ? '<a href="tel:' + escapeText(phoneSafe) + '" rel="nofollow">' + escapeText(tx('medPhone', { phone: phone })) + '</a>'
      : '';
    const copyBtn = address
      ? '<button type="button" data-med-copy="' + escapeText(inst.address) + '">' + escapeText(tx('medCopyAddress')) + '</button>'
      : '';
    return ''
      + '<li class="p-med-finder__card">'
      +   '<span class="p-med-finder__region">' + region + '</span>'
      +   '<h3>' + name + '</h3>'
      +   (address ? '<address>' + address + '</address>' : '')
      +   '<div class="p-med-finder__actions">'
      +     copyBtn
      +     phoneBtn
      +     '<a href="' + naverHref + '" target="_blank" rel="noopener noreferrer">' + escapeText(tx('agentNaver')) + '</a>'
      +     '<a href="' + kakaoHref + '" target="_blank" rel="noopener noreferrer">' + escapeText(tx('agentKakao')) + '</a>'
      +   '</div>'
      +   '<p class="p-med-finder__card-source">' + escapeText(tx('medSourceNote')) + '</p>'
      + '</li>';
  }
  function renderSlice() {
    const slice = filteredInstitutions.slice(0, visibleCount);
    if (filteredInstitutions.length === 0) {
      listEl.innerHTML = '';
      emptyEl.hidden = false;
      countEl.textContent = '';
      moreEl.hidden = true;
    } else {
      emptyEl.hidden = true;
      listEl.innerHTML = slice.map(buildCard).join('');
      if (visibleCount >= filteredInstitutions.length) {
        countEl.textContent = tx('medCountAll', { count: filteredInstitutions.length });
        moreEl.hidden = true;
      } else {
        countEl.textContent = tx('medCountShowing', { showing: slice.length, total: filteredInstitutions.length });
        moreEl.hidden = false;
      }
    }
  }
  function applyFilter() {
    const kw = (keywordIn.value || '').trim().toLowerCase();
    const hasSearch = !!(activeRegion || kw.length >= 2);
    if (clearBtn) clearBtn.hidden = !(activeRegion || kw);
    if (!hasSearch) {
      promptEl.hidden = false;
      listEl.innerHTML = '';
      countEl.textContent = tx('medTotalCount', { count: dataset.institutions.length });
      emptyEl.hidden = true;
      moreEl.hidden = true;
      return;
    }
    promptEl.hidden = true;
    const regionSet = new Set(dataset.regions || []);
    const kwRaw = (keywordIn.value || '').trim();
    const kwIsRegion = kwRaw.length > 0 && regionSet.has(kwRaw);
    filteredInstitutions = dataset.institutions.filter(function (inst) {
      if (activeRegion && inst.region !== activeRegion) return false;
      if (kwIsRegion) return inst.region === kwRaw;
      if (kw.length < 2) return true;
      const hay = ((inst.institution_name || '') + ' ' + (inst.address || '') + ' ' + (inst.region || '') + ' ' + (inst.phone || '')).toLowerCase();
      return hay.indexOf(kw) !== -1;
    });
    visibleCount = PAGE_SIZE;
    renderSlice();
  }
  function setActiveChip(region) {
    activeRegion = region;
    if (chipsEl) {
      chipsEl.querySelectorAll('.p-med-finder__chip').forEach(function (btn) {
        btn.setAttribute('aria-pressed', btn.getAttribute('data-med-region') === region ? 'true' : 'false');
      });
    }
    applyFilter();
  }
  window.updateMedFinderLanguage = function () {
    if (dataset.institutions.length) applyFilter();
  };
  function showError() {
    errorEl.hidden = false;
    listEl.innerHTML = '';
    countEl.textContent = '';
    emptyEl.hidden = true;
    promptEl.hidden = true;
    loadingEl.hidden = true;
    moreEl.hidden = true;
  }
  if (chipsEl) {
    chipsEl.addEventListener('click', function (ev) {
      const chip = ev.target.closest('.p-med-finder__chip');
      if (!chip) return;
      const region = chip.getAttribute('data-med-region') || '';
      setActiveChip(activeRegion === region ? '' : region);
    });
  }
  if (clearBtn) {
    clearBtn.addEventListener('click', function () {
      keywordIn.value = '';
      setActiveChip('');
    });
  }
  listEl.addEventListener('click', function (ev) {
    const btn = ev.target.closest('button[data-med-copy]');
    if (!btn) return;
    ev.preventDefault();
    const addr = btn.getAttribute('data-med-copy') || '';
    if (!addr) return;
    copyToClipboard(addr).then(function () {
      if (typeof showToast === 'function') showToast(tx('medCopied'), 'success');
    }).catch(function () {
      if (typeof showToast === 'function') showToast(tx('medCopyFailed'), 'warning');
    });
  });
  if (showMoreBtn) {
    showMoreBtn.addEventListener('click', function () {
      visibleCount += PAGE_SIZE;
      renderSlice();
    });
  }
  keywordIn.addEventListener('input', applyFilter);
  window.addEventListener('paradiso-language-applied', applyFilter);

  function loadDataset() {
    loadingEl.hidden = false;
    promptEl.hidden = true;
    errorEl.hidden = true;
    // Parse-time IIFE: runs before the module entry, so it cannot use window.Visable (ADR-009 note).
    fetch('data/designated_medical_institutions_2026_11_02.json', { cache: 'no-cache' })
      .then(function (res) {
        if (!res.ok) throw new Error('HTTP ' + res.status);
        return res.json();
      })
      .then(function (json) {
        loadingEl.hidden = true;
        dataset.meta = json && json._meta ? json._meta : {};
        dataset.institutions = Array.isArray(json && json.institutions) ? json.institutions : [];
        applyFilter();
      })
      .catch(function () {
        loadingEl.hidden = true;
        showError();
      });
  }
  if (retryBtn) retryBtn.addEventListener('click', loadDataset);
  loadDataset();
})();
