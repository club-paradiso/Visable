// @ts-nocheck
/**
 * Search scoring and the result list of the legacy per-status card (structure map C26: keyword scoring, expansion,
 * suggestions, direct-search mode, renderResults and the compact list). Kept inline in index.html: `ALIAS_MAP` and
 * `PREDEF_KEYWORDS` (read at run time by tests/e2e/search-smoke.spec.mjs through page.evaluate and by legacy scripts
 * that regex-parse index.html). The `let dt` debounce handle is module-private. Uses the inline globals VISA_DATA,
 * dataReady, currentLanguage, currentSearchMode, qEl, tx(), txArray(), escapeHtml(), hl(), CC and the Visable.docs /
 * Visable.cards stubs at call time only (compatibility surface, ADR-009); assets/js/civic-search.js, status-guidance.js
 * and the e2e specs call executeSearch/renderResults/resetToLanding by bare name, so those keep inline stubs. Covered by
 * tests/golden/specs/search.spec.mjs, procedure.spec.mjs, fail-closed.spec.mjs and legacy-card.spec.mjs.
 * Moved verbatim from index.html lines 17694-18171 (465 lines; kept inline: ['ALIAS_MAP', 'PREDEF_KEYWORDS']).
 * Exposed on window.Visable.search; 10 inline stubs with the same names delegate here.
 */
function calculateScore(item,keywords){
    if(!keywords || !keywords.length) return 1;
    let score=0; const cL=(item.code||'').toLowerCase(), nL=getVisaNameKo(item).toLowerCase(), codeNorm=normalizeVisaCode(item.code);
    /* PARADISO_SEARCH_ALIAS_FIX_20260702: searchAliases (the curated Korean
       alias field on records/subcodes) previously counted only for exact
       code-like queries — keyword scoring scanned the legacy `aliases` field
       alone, so curated terms like "산재"/"고용사유서" were invisible to word
       search. Include them here and in the subcode text below. */
    const aliasL=[...(item.aliases||[]),...(item.searchAliases||[])].map(x=>String(x).toLowerCase());
    const content=getRecordSearchText(item).toLowerCase();
    let isAnd=true;
    for(const kw of keywords){
        let m=false; const kwNorm = normalizeVisaCode(kw);
        if(cL===kw||nL===kw||(kwNorm && codeNorm===kwNorm)){score+=220; m=true;} else if(cL.includes(kw)||nL.includes(kw)||(kwNorm && codeNorm.includes(kwNorm))){score+=120; m=true;}
        aliasL.forEach(a=>{ if(a===kw){score+=180; m=true;} else if(a.includes(kw)||kw.includes(a)){score+=90; m=true;} });
        const subs = getVisaSubcodes(item);
        if(subs.length){
            for(const s of subs){
                const sCode=(s.code||'').toLowerCase(), sName=(s.name||'').toLowerCase(), sAliases=[...(s.aliases||[]),...(s.searchAliases||[])].join(' ').toLowerCase();
                const sNorm = normalizeVisaCode(s.code);
                if(sCode===kw||sName===kw||(kwNorm && sNorm===kwNorm)){score+=130; m=true;} else if(sCode.includes(kw)||sName.includes(kw)||(kwNorm && sNorm.includes(kwNorm))){score+=80; m=true;}
                const sc=`${s.nameKo||''} ${s.nameEn||''} ${s.summary||''} ${(s.eligibility||[]).join(' ')} ${s.addReq||''} ${s.note||''} ${sAliases}`.toLowerCase();
                const n=(sc.match(new RegExp(escapeRegExp(kw),'g'))||[]).length;
                if(n>0){score+=n*16; m=true;}
            }
        }
        const cn=(content.match(new RegExp(escapeRegExp(kw),'g'))||[]).length;
        if(cn>0){score+=cn*12; m=true;}
        if(!m) isAnd=false;
    }
    return currentSearchMode==='and' ? (isAnd?score:0) : score;
}

function getExactCodeMatchRank(item, keywords) {
    if (!keywords || !keywords.length) return 0;
    const normalizedKeywords = keywords.map(kw => normalizeVisaCode(kw)).filter(Boolean);
    if (!normalizedKeywords.length) return 0;
    const codeNorm = normalizeVisaCode(item.code);
    if (codeNorm && normalizedKeywords.some(kw => codeNorm === kw)) return 10000;
    const subcodeNorms = getVisaSubcodes(item).map(s => normalizeVisaCode(s.code)).filter(Boolean);
    if (subcodeNorms.some(sCode => normalizedKeywords.some(kw => sCode === kw))) return 5000;
    if (codeNorm && normalizedKeywords.some(kw => codeNorm.startsWith(kw))) return 200;
    if (codeNorm && normalizedKeywords.some(kw => codeNorm.includes(kw))) return 100;
    return 0;
}

/* PARADISO_SEARCH_QUERY_FIX_20260702: alias targets must be codes that exist
   in the loaded data. The old RF-1/OVS-1 targets were removed records, which
   made "난민"/"불법체류" searches return zero results in AND mode. 난민* now
   routes to the real refugee-applicant subcode G-1-5; the 불법체류 aliases are
   dropped so those words fall through to normal keyword search over record
   text. FAQ-0 is injected at runtime by injectLocalData(). */

function expandKeywords(keywords){
    const expanded = new Set(keywords.map(k=>k.toLowerCase()));
    const joined = keywords.join('').toLowerCase();
    const joinedNoSpace = joined.replace(/\s+/g,'');
    if(ALIAS_MAP[joined]) expanded.add(ALIAS_MAP[joined].toLowerCase());
    if(ALIAS_MAP[joinedNoSpace]) expanded.add(ALIAS_MAP[joinedNoSpace].toLowerCase());
    keywords.forEach(k=>{
        const nk = k.replace(/\s+/g,'').toLowerCase();
        const codeNorm = normalizeVisaCode(nk);
        if(codeNorm) expanded.add(codeNorm.toLowerCase());
        VISA_DATA.forEach(v => {
            if (normalizeVisaCode(v.code) === codeNorm) expanded.add(String(v.code || '').toLowerCase());
            getVisaSubcodes(v).forEach(s => {
                if (normalizeVisaCode(s.code) === codeNorm) {
                    expanded.add(String(s.code || '').toLowerCase());
                    expanded.add(String(v.code || '').toLowerCase());
                }
            });
        });
        if(ALIAS_MAP[nk]) expanded.add(ALIAS_MAP[nk].toLowerCase());
        if(nk==='제주') expanded.add('b-2-2');
        if(nk==='협정') expanded.add('b-1');
    });
    return [...expanded];
}

/* PARADISO_SEARCH_QUERY_FIX_20260702: every suggestion below must actually
   resolve to at least one result when searched verbatim (covered by
   scripts/check_exact_code_search_coverage.py). The old parenthetical/slash
   phrasings ("체류지 변경(주민센터)", "만료 당일/임산부 등", "오버스테이") returned
   zero results when clicked. */

// A predefined keyword that names a real 체류자격 code is a status suggestion,
// not a procedure one. The code has to resolve against VISA_DATA — a
// code-shaped substring alone never promotes a keyword.
function suggestionTypeForKeyword(keyword) {
    const match = String(keyword || '').match(/([A-Za-z]-\d+(?:-\d+)?)/);
    if (!match) return 'procedure';
    const norm = normalizeVisaCode(match[1]);
    const known = VISA_DATA.some(v => normalizeVisaCode(v.code) === norm ||
        getVisaSubcodes(v).some(s => normalizeVisaCode(s.code) === norm));
    return known ? 'visa_code' : 'procedure';
}

function showSuggestions(val) {
    if(!dataReady) return;
    const list = document.getElementById('auto-list'); list.innerHTML = '';
    if(!val) { list.classList.remove('active'); return; }
    const lowerVal = val.toLowerCase(), valNorm = normalizeVisaCode(val);
    const matches = [];
    const seen = new Set();
    // `query` stays exactly the string the search already understood; `type`
    // and `sublabel` only add description around it.
    const pushMatch = (query, type, sublabel) => {
        if (!query || seen.has(query)) return;
        seen.add(query);
        matches.push({ type: type, query: query, label: query, sublabel: sublabel || '' });
    };
    const primaryCode = getPrimaryCodeLikeQuery(val);
    if (primaryCode) {
        VISA_DATA
            .filter(v => normalizeVisaCode(v.code) === normalizeVisaCode(primaryCode))
            .forEach(v => pushMatch(`${v.code} ${getVisaNameKo(v)}`, 'visa_code', ''));
    }
    PREDEF_KEYWORDS.filter(k => k.toLowerCase().includes(lowerVal))
        .forEach(k => pushMatch(k, suggestionTypeForKeyword(k), ''));
    VISA_DATA.forEach(v => {
        const codeMatch = (v.code||'').toLowerCase().includes(lowerVal) || (valNorm && normalizeVisaCode(v.code).includes(valNorm));
        if(codeMatch || getVisaNameKo(v).toLowerCase().includes(lowerVal)) {
            pushMatch(`${v.code} ${getVisaNameKo(v)}`, 'visa_code', '');
        }
        getVisaSubcodes(v).forEach(s => {
            const subCodeMatch = (s.code || '').toLowerCase().includes(lowerVal) || (valNorm && normalizeVisaCode(s.code).includes(valNorm));
            if (subCodeMatch || (s.nameKo || s.name || '').toLowerCase().includes(lowerVal)) {
                // A subcode always names its parent, so the row can never be
                // read as a standalone top-level 체류자격.
                pushMatch(`${s.code} ${s.nameKo || s.name || ''}`, 'visa_status',
                    `${v.code} ${getVisaNameKo(v)}`);
            }
        });
    });
    if(matches.length > 0) {
        const rows = window.ParadisoUnifiedSearch;
        matches.slice(0, 7).forEach(m => {
            const item = document.createElement('button'); item.className = 'auto-item'; item.type = 'button';
            item.setAttribute('role', 'option');
            if (rows && typeof rows.buildSuggestionRowHtml === 'function') {
                // The shared UX-03 row markup in inner mode — this element
                // already is the button, so the renderer must not add one.
                item.innerHTML = rows.buildSuggestionRowHtml(m, {
                    inner: true,
                    labelHtml: hl(m.label, [val])
                });
                item.classList.add('us-sug');
                item.setAttribute('data-us-suggest-type', m.type);
            } else {
                item.innerHTML = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><circle cx="11" cy="11" r="7"/><line x1="16.5" y1="16.5" x2="21" y2="21"/></svg> <span>${hl(m.label, [val])}</span>`;
            }
            item.setAttribute('data-action', 'search-hint'); item.setAttribute('data-query', m.query);
            list.appendChild(item);
        });
        list.classList.add('active');
    } else list.classList.remove('active');
}
function executeSearch() {
    if (!dataReady) return;
    document.getElementById('auto-list').classList.remove('active');
    const query = qEl.value.trim(); if (!query) return;
    closeSearchBlockingSurfaces();
    if(/scn/i.test(query)) showToast(tx('scenarioToastWarning'), "warning");

    if (document.body.classList.contains('landing')) {
        try {
            const letters = document.querySelectorAll('.logo-brand .al');
            const letterRects = Array.from(letters).map(l => l.getBoundingClientRect());
            if (letterRects.length === 8) {
                const slotWidth = (letterRects[7].right - letterRects[0].left) / 8;
                letters.forEach((el, i) => {
                    const tgtIdx = parseInt(el.dataset.tgt || i, 10);
                    el.style.setProperty('--ax', ((tgtIdx * slotWidth) + (slotWidth - letterRects[i].width) / 2 - (letterRects[i].left - letterRects[0].left)) + 'px');
                    el.style.transitionDelay = (Math.abs(tgtIdx - i) * 35) + 'ms';
                });
                document.body.classList.add('anagram-run');
            }
        } catch(e) {}
        document.body.classList.add('launching');
        setTimeout(() => {
            document.body.classList.remove('landing', 'launching', 'anagram-run', 'searching');
            document.body.setAttribute('data-scene', 'searched');
            document.querySelectorAll('.logo-brand .al').forEach(el => { el.style.transitionDelay = ''; el.style.removeProperty('--ax'); });
            closeSearchBlockingSurfaces();
            document.body.classList.add('searched'); renderResults(query); window.scrollTo({ top: 0, behavior: 'smooth' });
        }, document.body.classList.contains('civic-refresh') ? 0 : 1200);
    } else {
        closeSearchBlockingSurfaces();
        renderResults(query);
    }
}
function setDirectSearchToggleState(isOpen){
    const stb = document.getElementById('searchToggleBtn');
    if (!stb) return;
    const iconEl = stb.querySelector('.hero-action-icon');
    const labelEl = stb.querySelector('.hero-action-label');
    stb.setAttribute('aria-expanded', isOpen ? 'true' : 'false');
    stb.classList.toggle('active', isOpen);
    stb.setAttribute('aria-label', isOpen ? tx('searchClose') : tx('searchOpenAria'));
    stb.title = isOpen ? tx('searchClose') : tx('searchOpen');
    if (iconEl) iconEl.textContent = isOpen ? '✕' : '🔍';
    if (labelEl) labelEl.textContent = isOpen ? tx('searchClose') : tx('searchOpen');
}

function closeDirectSearchMode(){
    debugSearchState('closeDirectSearchMode:start');
    const sf = document.getElementById('searchForm');
    const vms = document.getElementById('visaManualSection');
    if (sf) sf.style.display = 'none';
    if (vms) vms.style.display = '';
    document.body.classList.remove('searching');
    setDirectSearchToggleState(false);
    debugSearchState('closeDirectSearchMode:end');
}

function closeSearchBlockingSurfaces() {
    ['shortStayModalOverlay', 'jobCodeModalOverlay', 'jurisdictionModalOverlay', 'agentFinderModalOverlay', 'medFinderModalOverlay', 'aiModalOverlay', 'docModalOverlay', 'faqModalOverlay', 'hikoreaGuideOverlay'].forEach(id => {
        const el = document.getElementById(id);
        if (el && el.classList.contains('active')) closeModal(id);
    });
    const drawer = document.getElementById('visaDrawerOverlay');
    if (drawer && drawer.classList.contains('active')) closeVisaDrawer();
    const langMenu = document.getElementById('languageMenu');
    if (langMenu && langMenu.classList.contains('open')) toggleLanguageMenu(false);
    const cityMenu = document.getElementById('cityMenu');
    if (cityMenu) cityMenu.style.display = 'none';
}

function openDirectSearchMode(){
    debugSearchState('openDirectSearchMode:start');
    closeSearchBlockingSurfaces();
    const sf = document.getElementById('searchForm');
    const vms = document.getElementById('visaManualSection');
    if (sf) sf.style.display = 'block';
    if (vms) vms.style.display = 'none';
    document.body.classList.add('searching');
    setDirectSearchToggleState(true);
    if (qEl) setTimeout(() => qEl.focus(), 30);
    debugSearchState('openDirectSearchMode:end');
}

function handleDirectSearchToggle() {
    debugSearchState('toggle-search:before');
    const stb = document.getElementById('searchToggleBtn');
    const isOpen = stb && stb.getAttribute('aria-expanded') === 'true';
    if (!isOpen) openDirectSearchMode();
    else if (!document.body.classList.contains('searched')) closeDirectSearchMode();
    else if (qEl) qEl.focus();
    debugSearchState('toggle-search:after');
}

function resetToLanding(){
    debugSearchState('resetToLanding:start');
    document.body.classList.remove('searched', 'searching'); document.body.classList.add('landing'); qEl.value='';
    document.getElementById('xb').classList.remove('v'); document.getElementById('auto-list').classList.remove('active');
    document.getElementById('rlist').innerHTML=''; const rcHost = document.getElementById('rlistCompact'); if (rcHost) { rcHost.innerHTML = ''; rcHost.hidden = true; } rcEl.textContent = dataReady ? tx('dataReady', { count: VISA_DATA.length, source: tx('sourceStatic') }) : tx('dataLoading');
    const stb = document.getElementById('searchToggleBtn');
    closeDirectSearchMode();
    if (stb) stb.style.display = '';
    document.dispatchEvent(new CustomEvent('paradiso:landing-reset'));
    window.scrollTo({ top: 0, behavior: 'smooth' });
    resetReveal();
    debugSearchState('resetToLanding:end');
}

function renderCompactResults(filtered, kw){
    const host = document.getElementById('rlistCompact');
    if (!host) return;
    if (!filtered || !filtered.length) { host.hidden = true; host.innerHTML = ''; return; }
    const catLabels = txArray('searchedCategoryLabels');
    const catMap = {short:catLabels[0]||'단기',study:catLabels[1]||'유학/연수',work:catLabels[2]||'취업',invest:catLabels[3]||'투자',family:catLabels[4]||'가족/이민',other:catLabels[5]||'기타',diplo:catLabels[6]||'외교',nhis:catLabels[7]||'건강보험',faq:catLabels[8]||'안내',scn:catLabels[9]||'시나리오'};
    const top = filtered.slice(0, 12);
    const cards = top.map(v => {
        const name = getLocalizedVisaName(v) || v.code || '';
        const period = v.period ? escapeHtml(v.period) : '';
        const catLabel = catMap[v.cat] || '';
        const subs = getVisaSubcodes(v);
        const docCount = subs.length;
        const reviewLabel = reviewStateLabel(v);
        const rawSum = normalizeManualText(getCanonicalStatusSummarySource(v));
        const sum = rawSum ? (rawSum.length > 110 ? rawSum.slice(0, 110).replace(/\s+\S*$/, '') + '…' : rawSum) : '';
        const color = (typeof CC !== 'undefined' && CC[v.cat]) ? CC[v.cat] : '#0EA37B';
        const codeHtml = hl(v.code || '', kw);
        const nameHtml = hl(name, kw);
        const sumHtml = sum ? hl(sum, kw) : '';
        const metaParts = [];
        if (catLabel) metaParts.push(`<span class="rc-badge">${escapeHtml(catLabel)}</span>`);
        if (period) metaParts.push(`<span class="rc-badge rc-badge-period">${period}</span>`);
        if (docCount) metaParts.push(`<span class="rc-badge rc-badge-docs">${tx('resultSubtypes', { count: docCount })}</span>`);
        if (reviewLabel) metaParts.push(`<span class="rc-badge rc-badge-review">${escapeHtml(reviewLabel)}</span>`);
        return `<button type="button" class="rc-card" data-action="show-detail" data-code="${escapeHtml(v.code || '')}" style="--rc-cat:${color};" aria-label="${escapeHtml(v.code || '')} ${escapeHtml(name)}">
            <span class="rc-code">${codeHtml}</span>
            <span class="rc-name">${nameHtml}</span>
            <span class="rc-meta">${metaParts.join('')}</span>
            ${sumHtml ? `<span class="rc-sum">${sumHtml}</span>` : ''}
            <span class="rc-cta"><span>${escapeHtml(tx('compactDetail'))}</span><span class="rc-cta-arrow" aria-hidden="true">→</span></span>
        </button>`;
    }).join('');
    const headSubText = filtered.length > top.length
        ? tx('compactHeadSubMore', { showing: top.length, total: filtered.length })
        : tx('compactHeadSub', { count: filtered.length });
    host.innerHTML = `<div class="rc-head"><h2 class="rc-head-title">${escapeHtml(tx('compactHeadTitle'))}</h2><span class="rc-head-sub">${escapeHtml(headSubText)}</span></div><div class="rc-grid">${cards}</div>`;
    host.hidden = false;
}

function reviewStateLabel(v){
    const status = v && v.sourceManualStatus;
    if (!status) return '';
    if (status.needsManualReview === false) return txArray('reviewLabels')[0] || '';
    if (status.needsManualReview === true) return txArray('reviewLabels')[2] || '';
    return '';
}

function renderResults(query){
    if(!dataReady) return;
    const box=document.getElementById('rlist'), rc=document.getElementById('rc');
    const rawQuery = String(query || '').trim();
    const normalizedQuery = normalizeCodeLikeQuery(rawQuery);
    /* PARADISO_SEARCH_QUERY_FIX_20260702 (1/3): only substitute the compacted
       code form when the whole query IS code-like. Previously every query was
       whitespace-stripped into one token ("체류기간 연장" → "체류기간연장"), which
       made most multi-word searches — including the app's own suggestion
       chips — return zero results. */
    const primaryQuery = (normalizedQuery && isCodeLikeQuery(rawQuery)) ? normalizedQuery : rawQuery;
    const kw=primaryQuery.split(/\s+/).filter(Boolean), kwL=expandKeywords(kw.map(k=>k.toLowerCase()));
    /* PARADISO_SEARCH_QUERY_FIX_20260702 (2/3): a whole-query ALIAS_MAP hit
       (e.g. "체류지 변경" → FAQ-0, "난민" → G-1-5) routes through the exact-code
       pipeline, so alias targets rank like a direct code search instead of
       being an extra AND-required keyword that can never co-match. */
    const wholeAliasTarget = ALIAS_MAP[rawQuery.replace(/\s+/g, '')] || '';
    const primaryCodeQuery = getPrimaryCodeLikeQuery(rawQuery)
        || (wholeAliasTarget ? normalizeCodeLikeQuery(wholeAliasTarget) : '')
        || (kw.length === 1 && isCodeLikeQuery(kw[0]) ? normalizeCodeLikeQuery(kw[0]) : '');
    const queryIsCodeLike = !!primaryCodeQuery;
    let scored=VISA_DATA.map(v=>{
        const exactRank = queryIsCodeLike ? getExactQueryMatchRank(v, primaryCodeQuery) : 0;
        const codeRank = getExactCodeMatchRank(v, queryIsCodeLike ? [primaryCodeQuery] : kw);
        return ({...v,_score:calculateScore(v,kwL),_codeRank:Math.max(codeRank, exactRank),_exactRank:exactRank});
    });

    let filtered;
    if (queryIsCodeLike) {
        const exactTopLevel = scored.filter(v => v._exactRank >= 10000);
        const exactSubcode = scored.filter(v => v._exactRank >= 5000 && v._exactRank < 10000);
        const exactOnly = exactTopLevel.length ? exactTopLevel : (exactSubcode.length ? exactSubcode : scored.filter(v => v._exactRank > 0));
        filtered = (exactOnly.length ? exactOnly : scored.filter(v=>v._score>0))
            .sort((a,b)=>b._exactRank-a._exactRank||b._codeRank-a._codeRank||b._score-a._score);
    } else {
        filtered = scored.filter(v=>v._score>0).sort((a,b)=>b._codeRank-a._codeRank||b._score-a._score);
    }
    let st=0; filtered.forEach(v=>{st += getVisaSubcodes(v).length;});
    if(!filtered.length){
        box.innerHTML=`<div class="es"><div class="es-t">${escapeHtml(tx('resultEmptyTitle'))}</div><div class="es-d">${tx('resultEmptyDesc', { query: escapeHtml(query) })}</div><button type="button" class="cb" style="margin-top:1rem;" data-action="reset-to-landing">${currentLanguage === 'zh-CN' ? '← 返回开始' : currentLanguage === 'en' ? '← Back to start' : '← 처음으로 돌아가기'}</button></div>`;
        rc.textContent=tx('resultCount', { count: 0 });
        renderCompactResults([], kw);
        document.dispatchEvent(new CustomEvent('paradiso:results-rendered', { detail: { query: rawQuery, primaryCode: primaryCodeQuery, codes: [] } }));
        return;
    }
    // Exact single-result searches should open directly into the detailed card.
    // Showing the compact card and the full card for the same visa made the
    // results page feel duplicated and crowded.
    renderCompactResults(filtered.length === 1 ? [] : filtered, kw);
    const fg=document.createDocumentFragment();
    filtered.forEach((v,idx)=>{
        const c=document.createElement('article'); c.className='vc manual-result'; c.dataset.code = v.code || ''; c.dataset.testid = 'visa-result-card'; c.dataset.visaCode = v.code || ''; c.style.setProperty('--cbc', CC[v.cat]||CC.other); c.style.setProperty('--i', Math.min(idx,10));
        const isVisaCode = !['faq', 'scn', 'nhis'].includes(v.cat), subs=getVisaSubcodes(v), hs=subs.length>0;
        if (subs.length) c.dataset.visaSubcode = subs.map(s => s.code).filter(Boolean).join(' ');
        // Broad parent-code query (e.g. "C-3" on the C-3 card): substring matching
        // would mark EVERY subcode as "내 상황과 관련" and flood the card with full
        // subcode cards. Treat it as a parent overview instead — renderSubcodes
        // gets a compact preview + expand/collapse group via opts.
        const broadParentQuery = queryIsCodeLike && normalizeVisaCode(primaryCodeQuery) === normalizeVisaCode(v.code);
        let ms=[]; if(hs&&kw.length&&!broadParentQuery) ms=getMatchingSubcodes(v, kw.map(k=>k.toLowerCase()));
        if(kw.length&&(v._score>=50||ms.length)) c.classList.add('open');
        const periodHtml = v.period ? `<span class="manual-badge">${hl(v.period,kw)}</span>` : '';
        const dataHtml = v.dataBadge ? `<span class="manual-badge">${escapeHtml(v.dataBadge)}</span>` : '';
        const ddHtml = v.dataDate ? `<div class="data-date">${escapeHtml(tx('resultDataDate'))} ${escapeHtml(v.dataDate)}</div>` : '';
        const nameEn = getVisaNameEn(v);
        const primaryName = getLocalizedVisaName(v);
        const secondaryName = getSecondaryVisaName(v);
        c.innerHTML=`
            <div class="vc-h" data-action="toggle-su">
                <div class="manual-head-main">
                    <span class="bc">${hl(v.code,kw)}</span>
                    <div class="manual-title-stack">
                        <div class="manual-title-row">
                            <span class="manual-name-ko">${hl(primaryName,kw)}</span>
                            ${hs?`<span class="bn">${tx('resultSubtypes', { count: subs.length })}</span>`:''}
                        </div>
                        ${secondaryName ? `<div class="manual-name-en">${hl(secondaryName,kw)}</div>` : ''}
                        <div class="manual-badges">${renderDomainBadges(v)}${renderReviewBadge(v)}${periodHtml}${dataHtml}</div>
                    </div>
                </div>
                <span class="tgl">▼</span>
            </div>
            <div class="vc-cw"><div class="vc-c">
                ${v.cat === 'scn' ? `<div class="ai-cta" style="flex-direction:column; align-items:center; text-align:center; padding:2.5rem 1rem; background:var(--bg0);"><h4 style="color:var(--t1); font-weight:800; font-size:1.1rem; margin-bottom:0.5rem;">${tx('specialCaseTitle')}</h4><p style="font-size:0.85rem; color:var(--t3); margin-bottom:1.5rem; word-break:keep-all; max-width:400px;">${tx('specialCaseBody')}</p><button type="button" class="ai-btn" style="width:100%; max-width:320px; justify-content:center; box-shadow:var(--shD);" data-action="open-ai-modal" data-visa-code="${escapeHtml(v.code)}">${tx('specialCaseButton')}</button></div>` : `
                <div class="manual-layout">
                    ${renderViewModeToggle(v, isVisaCode)}
                    ${renderParentScopeNotice(v, primaryCodeQuery)}
                    ${renderNextActionArea(v, isVisaCode)}
                    ${renderCardSummary(v, kw)}
                    <div class="external-guide-slot" data-guide-slot="${escapeHtml(v.code || '')}"></div>
                    ${renderSubcodes(v, kw, ms, { broadParentQuery, queryCode: primaryCodeQuery })}
                    ${renderF4RouteChooser(v)}
                    ${renderProcedures(v, kw)}
                    ${renderStandaloneVisaIssuanceSection(v, kw)}
                    ${renderDocumentTabs(v)}
                    ${renderCautionBlock()}
                    ${renderSourceEvidencePanel(v)}
                    ${renderManualActions(v, isVisaCode)}
                    ${ddHtml}
                    ${renderEasyModePanel(v)}
                </div>`}
            </div></div>`;
        fg.appendChild(c);
    });
    box.innerHTML=''; box.appendChild(fg);
    restoreCardViewModes(box);
    rc.textContent=(st ? tx('resultCountWithSub', { count: filtered.length, subcount: st }) : tx('resultCount', { count: filtered.length })) + ` · ${tx('resultTotalSuffix', { count: VISA_DATA.length })}`;
    const modeStr=currentSearchMode==='and'?'AND':'OR';
    const catLabels = txArray('searchedCategoryLabels');
    const catMap = {short:catLabels[0]||'단기',study:catLabels[1]||'유학/연수',work:catLabels[2]||'취업',invest:catLabels[3]||'투자',family:catLabels[4]||'가족/이민',other:catLabels[5]||'기타',diplo:catLabels[6]||'외교',nhis:catLabels[7]||'건강보험',faq:catLabels[8]||'안내',scn:catLabels[9]||'시나리오'};
    const topCats=[...new Set(filtered.slice(0,3).map(v=>catMap[v.cat]||v.cat))];
    document.getElementById('rh').textContent=tx('sortMeta', { mode: modeStr, categories: topCats.join(', ') });
    // Notify external deferred modules (short-stay checker, F-4 route guide).
    document.dispatchEvent(new CustomEvent('paradiso:results-rendered', { detail: { query: rawQuery, primaryCode: primaryCodeQuery, codes: filtered.map(v => v.code || '') } }));
}

let dt;
function handleInput(){
    const v=qEl.value; document.getElementById('xb').classList.toggle('v',v.length>0); showSuggestions(v);
    if(document.body.classList.contains('searched') && dataReady){ clearTimeout(dt); dt=setTimeout(()=>renderResults(v),150); }
}
function handleAutocompleteKeydown(e){
    const list = document.getElementById('auto-list');
    if (!list || !list.classList.contains('active')) return;
    const items = [...list.querySelectorAll('.auto-item')];
    if (!items.length) return;
    const idx = items.indexOf(document.activeElement);
    if (e.key === 'ArrowDown') {
        e.preventDefault();
        items[Math.min(idx + 1, items.length - 1)].focus();
    } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        if (idx <= 0) qEl.focus();
        else items[idx - 1].focus();
    }
}
function clearSearch(){
    debugSearchState('clearSearch:start');
    const hasText = qEl.value.length > 0;
    if (!hasText && document.body.classList.contains('searching') && !document.body.classList.contains('searched')) {
        closeDirectSearchMode();
        debugSearchState('clearSearch:end-empty-close');
        return;
    }
    qEl.value='';
    qEl.focus();
    document.getElementById('xb').classList.remove('v');
    document.getElementById('auto-list').classList.remove('active');
    if(document.body.classList.contains('searched') && dataReady) renderResults('');
    debugSearchState('clearSearch:end');
}
function setSearchMode(m){currentSearchMode=m;document.getElementById('ma').classList.toggle('on',m==='and');document.getElementById('mo').classList.toggle('on',m==='or');if(document.body.classList.contains('searched')&&dataReady)renderResults(qEl.value);}

export {
    calculateScore, getExactCodeMatchRank, expandKeywords, suggestionTypeForKeyword, showSuggestions, executeSearch,
    setDirectSearchToggleState, closeDirectSearchMode, closeSearchBlockingSurfaces, openDirectSearchMode, handleDirectSearchToggle, resetToLanding,
    renderCompactResults, reviewStateLabel, renderResults, handleInput, handleAutocompleteKeydown, clearSearch,
    setSearchMode
};
