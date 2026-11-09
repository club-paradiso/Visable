// @ts-nocheck
/**
 * Boot of index.html (structure map C28–C30 + C32): theme and editorial-theme toggles, finder-region labels, initUI,
 * command chips, local data injection, category counts, the document-composer tags, the visa-data / issuance /
 * evidence loaders, the DOMContentLoaded bootstrap with the data-action dispatcher, and the landing journey tracks.
 * The DOMContentLoaded *registration* stays inline in index.html as a one-liner that calls `Visable.boot.onDomReady()`:
 * three parse-time shims register their own DOMContentLoaded handlers while the document is parsed, and the inline
 * registration keeps the main bootstrap ahead of them exactly as before (a module-time registration would run after
 * them). Everything else is verbatim. The `let INTEGRATED_FORM_META` and `let _currentInKoreaAction` are module-private;
 * `DOC_MODAL_ACTION_MAP` moved with its only reader. Uses the inline state owners (VISA_DATA, dataReady, currentLanguage,
 * …) by bare name and the Visable.* stubs at call time (compatibility surface, ADR-009). assets/js/visable-theme.js calls
 * `window.toggleTheme`, assets/js/civic-search.js calls startPreEntryTrack/startInKoreaTrack, so those keep inline stubs.
 * Covered by every golden spec (boot, search, language, tools, legacy card).
 * Moved verbatim from index.html lines 16852-17947 (1096 lines; kept inline: none).
 * Exposed on window.Visable.boot; 12 inline stubs with the same names delegate here.
 */
function toggleTheme(){
    const newTheme = document.body.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
    document.body.setAttribute('data-theme', newTheme);
    // Persist the brightness choice so it survives reloads and carries across
    // the other Visable pages (shared key). Brightness is independent of the
    // editorial style theme (paradiso:editorial-theme).
    Visable.state.write(Visable.state.KEYS.brightness, newTheme);
    updateThemeLabel();
    updateThemeColorMeta();
}

/* Administrative region display names for the agency/medical finders. The data
   (and the finder filters) stay keyed on the Korean canonical name; only the
   visible label is localized so a non-Korean UI never shows a Korean region
   chip. Both the full (서울특별시) and short (서울) forms map to one label.
   Kept outside the i18n-scan window above on purpose: the keys are Korean by
   design, not stray UI text. */
const REGION_I18N = {
    '전체': { en: 'All', 'zh-CN': '全部' },
    '서울': { en: 'Seoul', 'zh-CN': '首尔' }, '서울특별시': { en: 'Seoul', 'zh-CN': '首尔' },
    '부산': { en: 'Busan', 'zh-CN': '釜山' }, '부산광역시': { en: 'Busan', 'zh-CN': '釜山' },
    '대구': { en: 'Daegu', 'zh-CN': '大邱' }, '대구광역시': { en: 'Daegu', 'zh-CN': '大邱' },
    '인천': { en: 'Incheon', 'zh-CN': '仁川' }, '인천광역시': { en: 'Incheon', 'zh-CN': '仁川' },
    '광주': { en: 'Gwangju', 'zh-CN': '光州' }, '광주광역시': { en: 'Gwangju', 'zh-CN': '光州' },
    '대전': { en: 'Daejeon', 'zh-CN': '大田' }, '대전광역시': { en: 'Daejeon', 'zh-CN': '大田' },
    '울산': { en: 'Ulsan', 'zh-CN': '蔚山' }, '울산광역시': { en: 'Ulsan', 'zh-CN': '蔚山' },
    '세종': { en: 'Sejong', 'zh-CN': '世宗' }, '세종특별자치시': { en: 'Sejong', 'zh-CN': '世宗' },
    '경기': { en: 'Gyeonggi', 'zh-CN': '京畿道' }, '경기도': { en: 'Gyeonggi', 'zh-CN': '京畿道' },
    '강원': { en: 'Gangwon', 'zh-CN': '江原道' }, '강원특별자치도': { en: 'Gangwon', 'zh-CN': '江原道' },
    '충북': { en: 'Chungbuk', 'zh-CN': '忠清北道' }, '충청북도': { en: 'Chungbuk', 'zh-CN': '忠清北道' },
    '충남': { en: 'Chungnam', 'zh-CN': '忠清南道' }, '충청남도': { en: 'Chungnam', 'zh-CN': '忠清南道' },
    '전북': { en: 'Jeonbuk', 'zh-CN': '全北' }, '전북특별자치도': { en: 'Jeonbuk', 'zh-CN': '全北' },
    '전남': { en: 'Jeonnam', 'zh-CN': '全南' }, '전라남도': { en: 'Jeonnam', 'zh-CN': '全南' },
    '경북': { en: 'Gyeongbuk', 'zh-CN': '庆北' }, '경상북도': { en: 'Gyeongbuk', 'zh-CN': '庆北' },
    '경남': { en: 'Gyeongnam', 'zh-CN': '庆南' }, '경상남도': { en: 'Gyeongnam', 'zh-CN': '庆南' },
    '제주': { en: 'Jeju', 'zh-CN': '济州' }, '제주특별자치도': { en: 'Jeju', 'zh-CN': '济州' }
};
function localizeRegion(koName) {
    const name = (koName == null ? '' : String(koName)).trim();
    const code = normalizeLocaleCode(currentLanguage);
    if (!name) return code === 'ko' ? '전체' : (REGION_I18N['전체'][code] || 'All');
    if (code === 'ko') return name;
    const entry = REGION_I18N[name];
    return (entry && entry[code]) || name;
}
function localizeFinderRegions() {
    document.querySelectorAll('#jejuRegionFilter .jeju-region-pill').forEach((p) => {
        p.textContent = localizeRegion(p.dataset.region || '전체');
    });
    document.querySelectorAll('#medFinderChips .p-med-finder__chip').forEach((c) => {
        if (c.dataset.medRegion) c.textContent = localizeRegion(c.dataset.medRegion);
    });
    const agentSel = document.getElementById('agentFinderRegion');
    if (agentSel) agentSel.querySelectorAll('option').forEach((o) => {
        if (o.value) o.textContent = localizeRegion(o.value);
    });
}

/* ── Editorial style theme (civic_editorial / archive_diary) ──────────────
   Lives on the root <html data-theme> element, independent of the body-level
   light/dark brightness toggle. Persisted in localStorage; default civic. */
const EDITORIAL_THEME_STORAGE_KEY = 'paradiso:editorial-theme';
const EDITORIAL_THEMES = ['civic_editorial', 'archive_diary'];
// Theme toggle labels live in the locale packs (editorialThemeCivic /
// editorialThemeKitsch / editorialThemeAria) — no inline dictionaries here.

function getStoredEditorialTheme() {
    try {
        const stored = Visable.state.read(EDITORIAL_THEME_STORAGE_KEY);
        return EDITORIAL_THEMES.includes(stored) ? stored : 'civic_editorial';
    } catch (e) { return 'civic_editorial'; }
}

function currentEditorialTheme() {
    const t = document.documentElement.getAttribute('data-theme');
    return EDITORIAL_THEMES.includes(t) ? t : 'civic_editorial';
}

function updateEditorialThemeLabel() {
    const theme = currentEditorialTheme();
    const textEl = document.querySelector('.editorial-theme-btn-text');
    if (textEl) textEl.textContent = tx(theme === 'archive_diary' ? 'editorialThemeKitsch' : 'editorialThemeCivic');
    const aria = tx('editorialThemeAria');
    setAttr('#editorialThemeBtn', 'aria-label', aria);
    setAttr('#editorialThemeBtn', 'title', aria);
}

function applyEditorialTheme(theme, { persist = true } = {}) {
    if (!EDITORIAL_THEMES.includes(theme)) theme = 'civic_editorial';
    document.documentElement.setAttribute('data-theme', theme);
    if (persist) Visable.state.write(EDITORIAL_THEME_STORAGE_KEY, theme);
    updateEditorialThemeLabel();
    updateThemeColorMeta();
}

function toggleEditorialTheme() {
    const next = currentEditorialTheme() === 'civic_editorial' ? 'archive_diary' : 'civic_editorial';
    applyEditorialTheme(next);
}

function toggleAccordions(c){document.querySelectorAll('.vc,.su').forEach(el=>{if(c)el.classList.remove('open');else el.classList.add('open');});}

function initUI(){
    // Bootstrap from ?q= URL parameter — skip landing animation, go straight to results.
    try {
        const qParam = new URLSearchParams(window.location.search).get('q');
        if (qParam && qEl) {
            const normalized = isCodeLikeQuery(qParam) ? normalizeCodeLikeQuery(qParam) : qParam.trim();
            if (normalized) {
                qEl.value = normalized;
                document.body.classList.remove('landing', 'launching', 'anagram-run', 'searching');
                document.body.setAttribute('data-scene', 'searched');
                document.body.classList.add('searched');
                renderResults(normalized);
            }
        }
    } catch (e) {}
    const lf=getLandingHintItems();
    const lc=document.getElementById('landingHints');
    if(lc) {
        lc.innerHTML='';
        lf.forEach(x=>{const b=document.createElement('button');b.className='lh';b.textContent=x.l;b.onclick=()=>{qEl.value=x.q;executeSearch();};lc.appendChild(b);});
    }

    const rf=getQuickFilterItems();
    const qc=document.getElementById('qf');
    if(qc) {
        qc.innerHTML='';
        rf.forEach(x=>{const b=document.createElement('button');b.className='qb';b.textContent=x.l;b.onclick=()=>{qEl.value=x.q;qEl.focus();document.getElementById('xb').classList.add('v');renderResults(x.q);};qc.appendChild(b);});
    }
    renderCmdChips();
}

function renderCmdChips(){
    const host = document.getElementById('pCmdChips');
    if (!host) return;
    const items = getLandingHintItems().slice(0, 10);
    host.innerHTML = '';
    items.forEach(x => {
        const b = document.createElement('button');
        b.type = 'button';
        b.className = 'p-cmd-chip';
        b.setAttribute('role', 'listitem');
        b.textContent = x.l;
        b.dataset.query = x.q;
        b.onclick = () => { if (qEl) { qEl.value = x.q; } executeSearch(); };
        host.appendChild(b);
    });
}

function injectLocalData(arr) {
    if (!arr.some(v => v.code === "FAQ-0")) arr.unshift({
        code: "FAQ-0",
        name: "방문 예약 없이 가능한 업무 안내",
        cat: "faq",
        newReq: "체류지 변경 신고, 여권 정보 변경 신고 등 일부 업무는 방문예약 없이 처리할 수 있는 경우가 있습니다. 업무별 가능 여부와 필요한 서류는 외국인종합안내센터 1345 또는 관할 출입국·외국인관서에서 확인하세요."
    });
    return arr;
}
function setSearchEnabled(enabled) {
    if (!qEl) return;
    qEl.disabled = !enabled;
    const goBtn = document.querySelector('.sbar-go');
    if (goBtn) goBtn.disabled = !enabled;
    qEl.style.opacity = enabled ? '1' : '0.6';
    if (enabled) {
        qEl.placeholder = tx('qPlaceholder');
        if (rcEl) rcEl.textContent = '';
    } else {
        qEl.placeholder = tx('dataLoading');
    }
}


// Coverage-hero purpose bucket for one status record. Presentation-layer
// classification only — the canonical `cat` field in visa_data.json is never
// mutated. The four buckets are mutually exclusive. Helper/FAQ records
// (cat 'faq'/'scn'/'nhis') route to a null bucket and are left out of the
// card totals; the three pilot tracks (cat 'etc': K-STAR/REGION-S/YOUTH-STAY)
// are grouped into 방문·외교·기타 (stat-visit). Card totals therefore reflect
// every non-helper coverage entry — the 39 formal 체류자격 plus the 3 pilots
// (42) — not the canonical 39 alone.
function coverageBucket(v) {
    const code = v && v.code, cat = v && v.cat;
    if (!code || !cat) return null;
    if (['faq', 'scn', 'nhis'].includes(cat)) return null;
    if (cat === 'study') return 'stat-study';
    if (cat === 'family') return 'stat-residence';
    if (cat === 'work' || cat === 'invest') return 'stat-work';
    // 'other'/'short' members whose activity is employment in nature are grouped
    // with 취업·전문직: 취재(D-5)·관광취업(H-1)·방문취업(H-2)·단기취업(C-4).
    if (['D-5', 'H-1', 'H-2', 'C-4'].includes(code)) return 'stat-work';
    // Remaining short-stay, diplomatic (A-1~A-3), religious (D-6),
    // misc/humanitarian (G-1) and special pilot tracks (cat 'etc') →
    // 방문·외교·기타.
    return 'stat-visit';
}
// Sort coverage chips in the familiar A→K family order, numerically within a family.
function coverageCodeSortKey(code) {
    const m = String(code || '').match(/^([A-Z]+)-?(\d+)?/);
    return [m ? m[1] : String(code || ''), m && m[2] ? parseInt(m[2], 10) : 999, String(code || '')];
}
function updateCategoryCounts() {
    if (!Array.isArray(VISA_DATA) || !VISA_DATA.length) return;
    const buckets = { 'stat-work': new Set(), 'stat-study': new Set(), 'stat-residence': new Set(), 'stat-visit': new Set() };
    VISA_DATA.forEach(v => {
        const id = coverageBucket(v);
        if (id && buckets[id]) buckets[id].add(v.code);
    });
    Object.keys(buckets).forEach(id => {
        const el = document.getElementById(id);
        if (!el) return;
        const n = String(buckets[id].size);
        el.dataset.count = n;
        const card = el.closest('.stat-card');
        // Keep the landing metrics correct even before the reveal animation runs.
        el.textContent = n;
        // Every code in the bucket becomes a visible, searchable chip (the static
        // markup only carries a representative few as a pre-data fallback).
        const chipBox = card && card.querySelector('.stat-codes');
        if (chipBox) {
            const codes = [...buckets[id]].sort((a, b) => {
                const ka = coverageCodeSortKey(a), kb = coverageCodeSortKey(b);
                return ka[0].localeCompare(kb[0]) || (ka[1] - kb[1]) || ka[2].localeCompare(kb[2]);
            });
            chipBox.removeAttribute('aria-hidden');
            chipBox.setAttribute('role', 'list');
            chipBox.innerHTML = codes.map(code =>
                `<button type="button" role="listitem" class="stat-code-chip" data-action="search-hint" data-query="${escapeHtml(code)}" aria-label="${escapeHtml(code)}">${escapeHtml(code)}</button>`
            ).join('');
        }
    });
}

/* ── Essential form composer (#docComposer) ─────────────────────────────────
   Metadata comes from data/integrated_form_metadata.json (the same source the
   form-helper editor is built on); the chips preview which 민원 checkboxes the
   통합신청서 covers. */
let INTEGRATED_FORM_META = null;

function renderDocComposerTags() {
    const host = document.getElementById('docComposerTags');
    if (!host) return;
    const types = INTEGRATED_FORM_META && Array.isArray(INTEGRATED_FORM_META.applicationTypes)
        ? INTEGRATED_FORM_META.applicationTypes : [];
    if (!types.length) { host.innerHTML = ''; return; }
    const shown = types.slice(0, 6);
    const rest = types.length - shown.length;
    host.innerHTML = shown.map(t => {
        const label = pickLocalizedManualText({ ko: t.formCheckboxKo, en: t.formCheckboxEn });
        return label ? `<span class="doc-composer-tag">☑ ${escapeHtml(label)}</span>` : '';
    }).filter(Boolean).join('') + (rest > 0 ? `<span class="doc-composer-tag more">+${rest}</span>` : '');
}

async function loadDocComposerMeta() {
    INTEGRATED_FORM_META = await fetchOptionalJson('./data/integrated_form_metadata.json');
    renderDocComposerTags();
}

function buildProcedureEvidenceIndex(records) {
    const map = new Map();
    (Array.isArray(records) ? records : []).forEach(record => {
        if (!record || !record.code || !record.procedureType) return;
        map.set(`${normalizeVisaCode(record.code)}:${record.procedureType}`, record);
    });
    return map;
}

function fetchOptionalJson(path) {
    // Data layer (src/data/fetch-json.js) — same warn-and-null semantics.
    return Visable.data.fetchOptionalJson(path);
}

async function loadVisaIssuanceData() {
    const [issuance, evidence, overlays] = await Promise.all([
        fetchOptionalJson('./data/visa_issuance_records.json'),
        fetchOptionalJson('./data/procedure_evidence_bindings.json'),
        fetchOptionalJson('./data/official_web_overlays.json')
    ]);
    VISA_ISSUANCE_RECORDS = Array.isArray(issuance?.records) ? issuance.records : [];
    VISA_ISSUANCE_BY_CODE = new Map(VISA_ISSUANCE_RECORDS.map(record => [normalizeVisaCode(record.code), record]));
    PROCEDURE_EVIDENCE_BINDINGS = Array.isArray(evidence?.records) ? evidence.records : [];
    PROCEDURE_EVIDENCE_BY_KEY = buildProcedureEvidenceIndex(PROCEDURE_EVIDENCE_BINDINGS);
    OFFICIAL_WEB_OVERLAYS = Array.isArray(overlays?.records) ? overlays.records : [];
    OFFICIAL_WEB_OVERLAY_POLICY = overlays?.policy && typeof overlays.policy === 'object' ? overlays.policy : {};
}

const VISA_DATA_API_TIMEOUT_MS = 4000;
async function loadVisaData() {
    const parse = (raw) => injectLocalData(Array.isArray(raw) ? raw : (Array.isArray(raw?.data) ? raw.data : (Array.isArray(raw?.visas) ? raw.visas : [])));
    const applySuccess = async (arr, label) => {
        await loadVisaIssuanceData();
        VISA_DATA = arr; dataReady = true; if(rcEl) rcEl.textContent = tx('dataReady', { count: VISA_DATA.length, source: label });
        setSearchEnabled(true); initUI(); updateCategoryCounts();
        document.dispatchEvent(new CustomEvent('paradiso:data-ready'));
    };
    try {
        if (!API_BASE) throw new Error("Local");
        // Hard ceiling: a cold or hung backend must never keep search locked.
        // On timeout we fall through to the committed ./visa_data.json below.
        // Data layer: the timer also covers a stalled response body.
        const apiJson = await Visable.data.fetchJsonWithTimeout(`${API_BASE}${Visable.data.API_ROUTES.visas}`, VISA_DATA_API_TIMEOUT_MS, { errorMessage: 'API Fail' });
        await applySuccess(parse(apiJson), tx('sourceApi')); return;
    } catch (e) {
        try {
            await applySuccess(parse(await Visable.data.fetchJson(Visable.data.DATA_PATHS.visaData, { errorMessage: 'JSON Fail' })), tx('sourceStatic'));
        } catch (err) {
            dataReady = false;
            if (rcEl) rcEl.textContent = tx('visaDataLoadError');
            setSearchEnabled(false);
            document.dispatchEvent(new CustomEvent('paradiso:data-failed'));
        }
    }
}

// --- Global Event Delegation ---
// The DOMContentLoaded bootstrap. index.html registers it inline (`document.addEventListener('DOMContentLoaded',
// () => Visable.boot.onDomReady())`) so it keeps running before the parse-time shims' own handlers.
async function onDomReady() {
    ensureSearchDebugPanel();
    applyEditorialTheme(getStoredEditorialTheme(), { persist: false });
    await loadI18nTranslations();
    renderLanguageMenu();
    applyLanguage(getInitialLanguage(), { silent: true });
    loadDocumentHelp();
    loadDocGuide();
    loadDocComposerMeta();
    loadVisaData();
    if(qEl) {
        qEl.addEventListener('input', handleInput);
        qEl.addEventListener('keydown', handleAutocompleteKeydown);
    }
    document.querySelectorAll('[data-action="toggle-search"]').forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.preventDefault();
            e.stopPropagation();
            handleDirectSearchToggle();
        }, true);
    });

    const searchForm = document.getElementById('searchForm');
    searchForm?.addEventListener('submit', (e) => {
        e.preventDefault(); executeSearch();
    });

    const citySearch = document.getElementById('citySearch');
    if (citySearch) citySearch.addEventListener('input', (e) => renderCityList(e.target.value));

    const jurSido = document.getElementById('jurSido');
    if (jurSido) jurSido.addEventListener('change', updateSigungu);
    const jurSigungu = document.getElementById('jurSigungu');
    if (jurSigungu) jurSigungu.addEventListener('change', showJurisdiction);

    Visable.features.jobcode.wireJobcodeInputs(); // #jcSearchInput / #jcIncome wiring, moved to src/features/jobcode.js

    debugSearchState('DOMContentLoaded:init');

    // Persist scenario-checklist checkbox state locally on change. Document-level
    // delegation survives result-card re-renders and avoids duplicate listeners.
    document.addEventListener('change', (e) => {
        const checklistItem = e.target.closest('[data-scenario-checklist-item]');
        if (checklistItem) persistScenarioChecklistItem(checklistItem);
    });

    document.addEventListener('click', (e) => {
        const documentHelpTrigger = e.target.closest('.document-help-trigger');
        if (documentHelpTrigger) {
            e.preventDefault();
            e.stopPropagation();
            openDocumentHelp(documentHelpTrigger.dataset.documentHelpId, documentHelpTrigger);
            return;
        }
        const documentHelpClose = e.target.closest('[data-action="close-document-help"]');
        if (documentHelpClose) {
            e.preventDefault();
            e.stopPropagation();
            closeDocumentHelp();
            return;
        }
        // Document-guide toggle lives inside the .vc-h[data-action="toggle-su"]
        // wrapper, so it must be handled BEFORE the toggle-su branch — otherwise
        // the bubbled click collapses the result card and hides the drawer the
        // user just opened. stopPropagation keeps the card from toggling.
        const guideToggle = e.target.closest('.doc-guide-toggle');
        if (guideToggle) { e.stopPropagation(); toggleDocGuide(guideToggle); return; }
        // Reading/clicking inside an open drawer must not bubble up and collapse
        // the surrounding result card.
        if (e.target.closest('.doc-guide-drawer')) { e.stopPropagation(); return; }

        // Toggle su wrapper inside results
        const toggleSu = e.target.closest('[data-action="toggle-su"]');
        if (toggleSu) { toggleSu.parentElement.classList.toggle('open'); return; }

        // Subcode detail modal: clicking the dimmed backdrop (not the box) closes it.
        if (e.target.classList.contains('subcode-modal-overlay')) { closeModal('subcodeDetailOverlay'); return; }

        const actionBtn = e.target.closest('[data-action]');
        if (actionBtn) {
            const action = actionBtn.dataset.action;
            const handlers = {
                'clear-search': clearSearch,
                'close-ai-modal': () => closeModal('aiModalOverlay'),
                'close-short-stay-modal': () => closeModal('shortStayModalOverlay'),
                'close-jobcode-modal': () => closeModal('jobCodeModalOverlay'),
                'close-jurisdiction-modal': () => closeModal('jurisdictionModalOverlay'),
                'close-agent-finder': () => closeModal('agentFinderModalOverlay'),
                'close-med-finder': () => closeModal('medFinderModalOverlay'),
                'close-doc-modal': () => closeModal('docModalOverlay'),
                'open-subcode-detail': () => openSubcodeModal(actionBtn.dataset.parent, actionBtn.dataset.subcode),
                'close-subcode-modal': () => closeModal('subcodeDetailOverlay'),
                'close-faq-modal': () => closeModal('faqModalOverlay'),
                'close-hikorea-guide': () => closeModal('hikoreaGuideOverlay'),
                'open-ai-modal': () => openAiModal(actionBtn.dataset.visaCode),
                'open-hikorea-guide': () => openHikoreaGuide(actionBtn.dataset.vcode),
                'open-doc-modal': () => openDocModal(actionBtn.dataset.vcode, actionBtn.dataset.type, actionBtn.dataset.subidx),
                'open-faq-modal': () => openFaqModal(actionBtn.dataset.vcode),
                'select-procedure': () => {
                    const card = actionBtn.closest('.manual-result');
                    if (!card || actionBtn.disabled) return;
                    card.querySelectorAll('.procedure-tab').forEach(btn => btn.classList.toggle('active', btn === actionBtn));
                    card.querySelectorAll('.procedure-panel').forEach(panel => panel.classList.toggle('active', panel.dataset.procedurePanel === actionBtn.dataset.procedure));
                },
                'select-f4-route': () => selectF4Route(actionBtn),
                'open-route-picker': () => openRoutePicker(actionBtn),
                'choose-route': () => chooseRoute(actionBtn),
                'close-route-picker': () => closeModal('routePickerOverlay'),
                'show-all-f4-routes': () => resetF4Route(actionBtn),
                'open-issuance-guide': () => openIssuanceGuide(actionBtn),
                'choose-issuance-mode': () => chooseIssuanceMode(actionBtn),
                'close-issuance-guide': () => closeModal('issuanceGuideOverlay'),
                'clear-issuance-guide': () => clearIssuanceGuide(actionBtn),
                'toggle-subcode-group': () => {
                    const body = document.getElementById(actionBtn.getAttribute('aria-controls'));
                    if (!body) return;
                    const expand = actionBtn.getAttribute('aria-expanded') !== 'true';
                    actionBtn.setAttribute('aria-expanded', String(expand));
                    body.hidden = !expand;
                },
                'open-scenario-picker': () => openScenarioPicker(actionBtn),
                'choose-scenario-variant': () => chooseScenarioVariant(actionBtn),
                'clear-procedure-variant': () => clearScenarioSelection(actionBtn),
                'close-scenario-picker': () => closeScenarioPicker(),
                'ask-selected-procedure-variant': () => handleScenarioAiHandoff(actionBtn, 'selectedScenarioAiPrompt'),
                'copy-scenario-checklist': () => copyScenarioChecklist(actionBtn),
                'print-scenario-checklist': () => printScenarioChecklist(actionBtn),
                'reset-scenario-checklist': () => resetScenarioChecklist(actionBtn),
                'ask-checklist-missing': () => handleScenarioAiHandoff(actionBtn, 'scenarioChecklistMissingPrompt'),
                'select-docs-tab': () => {
                    const section = actionBtn.closest('.docs-section');
                    if (!section || actionBtn.disabled) return;
                    activateDocsTab(section, actionBtn.dataset.docsTab);
                },
                'set-card-mode': () => {
                    setCardMode(actionBtn.closest('.manual-result'), actionBtn.dataset.cardMode);
                },
                'toggle-easy-mode': () => toggleGlobalEasyMode(),
                'search-hint': () => { document.getElementById('q').value = actionBtn.dataset.query; executeSearch(); },
                'quick-filter': () => { document.getElementById('q').value = actionBtn.dataset.query; document.getElementById('xb').classList.add('v'); renderResults(actionBtn.dataset.query); },
                'set-search-mode': () => setSearchMode(actionBtn.dataset.mode),
                'toggle-accordions': () => toggleAccordions(actionBtn.dataset.fold === 'true'),
                'toggle-search': handleDirectSearchToggle,
                'close-cmd-palette': () => {
                    if (document.body.classList.contains('searching') && !document.body.classList.contains('searched')) closeDirectSearchMode();
                },
                'show-detail': () => {
                    const code = actionBtn.dataset.code;
                    if (!code) return;
                    // Unified route guidance: parent-with-subcodes opens a 세부코드/상황
                    // selector, others open a 절차 selector, before landing on the
                    // result drawer with the chosen subcode + procedure active. Falls
                    // through to the plain drawer when the layer is absent or declines.
                    if (window.ParadisoRoute && typeof window.ParadisoRoute.start === 'function'
                        && window.ParadisoRoute.start(code, { source: 'search-result' })) return;
                    if (typeof openVisaDrawer === 'function' && openVisaDrawer(code)) return;
                    // Fallback: existing scroll-to-detail behaviour
                    const target = document.querySelector(`.vc[data-code="${CSS.escape(code)}"]`);
                    if (!target) return;
                    target.classList.add('open', 'rc-target-flash');
                    setTimeout(() => target.classList.remove('rc-target-flash'), 1600);
                    target.scrollIntoView({ behavior: 'smooth', block: 'start' });
                },
                'close-visa-drawer': () => closeVisaDrawer(),
                'open-jobcode-modal': () => openJobCodeModal(),
                'open-jurisdiction-modal': () => openJurisdictionModal(),
                'open-agent-finder': () => openModal('agentFinderModalOverlay'),
                'open-med-finder': () => openModal('medFinderModalOverlay'),
                'open-short-stay': () => { if (window.ParadisoShortStay && typeof window.ParadisoShortStay.open === 'function') window.ParadisoShortStay.open(); },
                'reveal-home-section': () => {
                    const targetId = actionBtn.dataset.target || '';
                    const target = document.getElementById(targetId);
                    if (!target) return;
                    if (targetId === 'reminderSection' && window.VisableReminderDialog) {
                        window.VisableReminderDialog.open(actionBtn);
                        return;
                    }
                    // The civic landing owns the pre-entry / post-entry journey as a real
                    // state machine (CLOSED | PRE_ENTRY_OPEN | POST_ENTRY_OPEN); every entry
                    // that targets the journey section routes through it so ARIA and the
                    // visible state cannot diverge.
                    const journey = window.VisableCivicSearch && window.VisableCivicSearch.journey;
                    if (targetId === 'visaManualSection' && journey && document.body.classList.contains('civic-refresh')) {
                        const track = actionBtn.dataset.journeyTrack === 'in' ? 'post' : (actionBtn.dataset.journeyTrack === 'pre' ? 'pre' : null);
                        if (track) journey.open(track); else journey.open(journey.state() === 'POST_ENTRY_OPEN' ? 'post' : 'pre');
                        actionBtn.setAttribute('aria-expanded', journey.state() === 'CLOSED' ? 'false' : 'true');
                        return;
                    }
                    // Other landing sections (pathways, reminders) are plain disclosures: a
                    // second activation collapses them again.
                    const open = !target.classList.contains('is-home-revealed');
                    target.classList.toggle('is-home-revealed', open);
                    actionBtn.setAttribute('aria-expanded', open ? 'true' : 'false');
                    if (!open) return;
                    if (actionBtn.dataset.journeyTrack === 'pre' && typeof startPreEntryTrack === 'function') startPreEntryTrack();
                    if (actionBtn.dataset.journeyTrack === 'in' && typeof startInKoreaTrack === 'function') startInKoreaTrack();
                    target.scrollIntoView({ behavior: 'smooth', block: 'start' });
                },
                'search-jobcode-ai': () => searchJobcodeWithAI(),
                'jobcode-back': () => jcGoBackToAsk(),
                'set-jobcode-filter': () => setJobcodeFilter(actionBtn.dataset.jcFilter),
                'set-jobcode-level': () => setJobcodeLevel(actionBtn.dataset.jcLevel),
                'search-jobcode-chip': () => searchJobcodeChip(actionBtn.dataset.jcChip),
                'select-jobcode': () => selectJobcode(actionBtn.dataset.type, actionBtn.dataset.code),
                'copy-jobcode-memo': () => copyJobcodeMemo(),
                'copy-visa-result': () => copyVisaResult(actionBtn, actionBtn.dataset.vcode),
                'verify-faq': () => verifyFaqWithAi(actionBtn.dataset.vcode, actionBtn.dataset.q),
                'reset-to-landing': () => { if(document.body.classList.contains('searched')) resetToLanding(); },
                'toggle-city': () => toggleCityMenu(),
                'apply-city': () => { applyCity(JSON.parse(actionBtn.dataset.city)); toggleCityMenu(false); },
                'toggle-language-menu': () => toggleLanguageMenu(),
                'apply-language': () => { applyLanguage(actionBtn.dataset.lang); toggleLanguageMenu(false); },
                'toggle-theme': () => toggleTheme(),
                'toggle-editorial-theme': () => toggleEditorialTheme(),
                'open-global-settings': () => window.openGlobalSettings && window.openGlobalSettings(),
                'close-global-settings': () => window.closeGlobalSettings && window.closeGlobalSettings(),
                'open-city-from-settings': () => {
                    if (window.closeGlobalSettings) window.closeGlobalSettings();
                    toggleCityMenu(true);
                    document.getElementById('citySearch')?.focus();
                },
                'set-brightness': () => window.setGlobalBrightness && window.setGlobalBrightness(actionBtn.dataset.brightness),
                'scroll-to-brand': () => document.getElementById('brandHero')?.scrollIntoView({ behavior: 'smooth' })
            };
            if (handlers[action]) {
                if (actionBtn.tagName !== 'A') e.preventDefault();
                handlers[action]();
            }
            return;
        }

        const aiBtn = e.target.closest('.ai-action-btn');
        if (aiBtn) { e.preventDefault(); submitAiAnalysis(aiBtn.dataset.type, aiBtn); return; }

        ['shortStayModalOverlay', 'jobCodeModalOverlay', 'jurisdictionModalOverlay', 'agentFinderModalOverlay', 'medFinderModalOverlay', 'aiModalOverlay', 'docModalOverlay', 'faqModalOverlay', 'hikoreaGuideOverlay', 'scenarioPickerOverlay', 'routePickerOverlay', 'issuanceGuideOverlay'].forEach(id => {
            const el = document.getElementById(id); if (el && e.target === el) closeModal(id);
        });

        const wrap = document.getElementById('cityWrap'), menu = document.getElementById('cityMenu');
        if (wrap && !wrap.contains(e.target) && menu && menu.style.display !== 'none') menu.style.display = 'none';

        const langWrap = document.getElementById('languageWrap'), langMenu = document.getElementById('languageMenu');
        if (langWrap && !langWrap.contains(e.target) && langMenu?.classList.contains('open')) toggleLanguageMenu(false);

        const sWrap = document.getElementById('searchForm'), al = document.getElementById('auto-list');
        if (sWrap && !sWrap.contains(e.target) && al) al.classList.remove('active');
    });

    // The listener above is the sole owner of every [data-action] on the page,
    // and this callback only reaches it after `await loadI18nTranslations()`.
    // Deferred scripts render the interactive landing inside that window, so
    // the utility directory is clickable before its owner exists and an early
    // tap has nothing to retry it. assets/js/backend-origin.js records one such
    // tap; announcing the owner is live lets it replay that tap instead of
    // dropping it. Dispatched here, not at the end of the callback, so the
    // replay happens the moment the delegation can serve it.
    document.dispatchEvent(new CustomEvent('visable:landing-actions-ready'));

    // Keyboard activation (Enter/Space) for role="button" subcode cards. Real
    // <button> preview chips handle this natively, so they are skipped here.
    document.addEventListener('keydown', (e) => {
        if (e.key !== 'Enter' && e.key !== ' ' && e.key !== 'Spacebar') return;
        const card = e.target && e.target.closest && e.target.closest('[data-action="open-subcode-detail"]');
        if (!card || card.tagName === 'BUTTON') return;
        e.preventDefault();
        openSubcodeModal(card.dataset.parent, card.dataset.subcode);
    });

    document.addEventListener('keydown', e => {
        if (e.key === 'Enter' && e.target.classList.contains('logo-area')) {
            if (document.body.classList.contains('searched')) resetToLanding();
        }
        if (e.key === 'Tab') {
            const helpOverlay = document.getElementById('documentHelpOverlay');
            if (helpOverlay?.classList.contains('is-open')) {
                const focusable = Array.from(helpOverlay.querySelectorAll('button:not([disabled]):not([tabindex="-1"]), a[href]'))
                    .filter(el => !el.hidden && el.getClientRects().length > 0);
                if (focusable.length) {
                    const first = focusable[0];
                    const last = focusable[focusable.length - 1];
                    if (e.shiftKey && (document.activeElement === first || !focusable.includes(document.activeElement))) {
                        e.preventDefault();
                        last.focus();
                    } else if (!e.shiftKey && (document.activeElement === last || !helpOverlay.contains(document.activeElement))) {
                        e.preventDefault();
                        first.focus();
                    }
                }
                return;
            }
        }
        if (e.key === 'Escape') {
            if (document.getElementById('documentHelpOverlay')?.classList.contains('is-open')) {
                e.preventDefault();
                closeDocumentHelp();
                return;
            }
            const langMenu = document.getElementById('languageMenu');
            if (langMenu?.classList.contains('open')) {
                toggleLanguageMenu(false);
                return;
            }
            const anyModalOpen = ['routeGuideOverlay', 'shortStayModalOverlay', 'jobCodeModalOverlay', 'jurisdictionModalOverlay', 'agentFinderModalOverlay', 'medFinderModalOverlay', 'aiModalOverlay', 'docModalOverlay', 'subcodeDetailOverlay', 'faqModalOverlay', 'hikoreaGuideOverlay', 'scenarioPickerOverlay', 'routePickerOverlay', 'issuanceGuideOverlay'].some(id => {
                const el = document.getElementById(id);
                if (el?.classList.contains('active')) { closeModal(id); return true; }
                return false;
            });
            if (anyModalOpen) return;
            const drawer = document.getElementById('visaDrawerOverlay');
            if (drawer?.classList.contains('active')) {
                closeVisaDrawer();
                return;
            }
            if (document.body.classList.contains('searching') && !document.body.classList.contains('searched')) {
                closeDirectSearchMode();
            }
        }
    });

    document.addEventListener('toggle', (e) => {
        const details = e.target;
        if (!(details instanceof HTMLDetailsElement)) return;
        if (!details.classList.contains('manual-subcode-more') || !details.open) return;
        const summary = details.querySelector('summary');
        if (!(summary instanceof HTMLElement)) return;
        requestAnimationFrame(() => {
            summary.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        });
    }, true);

    initScrollReveal();

    // Kitsch masthead: live date + IP-resolved city (archive_diary only)
    if (document.documentElement.dataset.theme === 'archive_diary') {
        const _kd = new Date();
        const _kMonths = ['JAN','FEB','MAR','APR','MAY','JUN','JUL','AUG','SEP','OCT','NOV','DEC'];
        const _kDateStr = `${_kMonths[_kd.getMonth()]} ${_kd.getDate()} ${_kd.getFullYear()}`;
        const _kStampEl = document.querySelector('.k-stamp-date');
        if (_kStampEl) _kStampEl.textContent = `${_kd.getDate()} ${_kMonths[_kd.getMonth()]} ${_kd.getFullYear()}`;
        const _kCalEl = document.querySelector('.k-obj.k-cal');
        if (_kCalEl) {
            const _kCalB = _kCalEl.querySelector('b');
            const _kCalI = _kCalEl.querySelector('i');
            if (_kCalB) _kCalB.textContent = _kd.getDate();
            if (_kCalI) _kCalI.textContent = _kMonths[_kd.getMonth()];
        }
        // Masthead city was previously IP-resolved via external geolocation APIs;
        // replaced with a static label to avoid unconsented external network calls.
        const el = document.getElementById('k-masthead-meta');
        if (el) el.textContent = `VISABLE · ${_kDateStr} · REPUBLIC OF KOREA`;

        // --- Random country passport stamp (archive_diary only) ---
        (async () => {
            const flagFromCca2 = (cca2) => [...cca2.toUpperCase()]
                .map((c) => String.fromCodePoint(0x1F1E6 + c.charCodeAt(0) - 65)).join('');
            function countryInkColor(cca2) {
                let h = 0;
                for (const c of cca2) h = (h * 31 + c.charCodeAt(0)) % 360;
                h = 180 + (h % 160);
                return `hsl(${h}, 65%, 28%)`;
            }
            function buildCountryStamp(country, day, month, year) {
                const ink = countryInkColor(country.cca2);
                const rawName = country.name.common.toUpperCase();
                const name = rawName.length > 14 ? rawName.slice(0, 13) + '.' : rawName;
                const nameSize = name.length > 10 ? 9 : 11;
                const serial = `NO.${(country.cca2.charCodeAt(0) * 97 + country.cca2.charCodeAt(1) * 13) % 9000 + 1000}`;
                let ticks = '';
                for (let a = 0; a < 360; a += 15) {
                    const rad = a * Math.PI / 180;
                    const x1 = 80 + 66 * Math.cos(rad), y1 = 80 + 66 * Math.sin(rad);
                    const x2 = 80 + 71 * Math.cos(rad), y2 = 80 + 71 * Math.sin(rad);
                    ticks += `<line x1="${x1.toFixed(1)}" y1="${y1.toFixed(1)}" x2="${x2.toFixed(1)}" y2="${y2.toFixed(1)}" stroke="${ink}" stroke-width="1.6"/>`;
                }
                return `<svg id="k-stamp-country" viewBox="0 0 160 160" width="140" height="140" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
<defs>
<path id="kcs-arc-top" d="M 80,80 m -52,0 a 52,52 0 1,1 104,0" fill="none"/>
<path id="kcs-arc-bot" d="M 80,80 m -52,0 a 52,52 0 1,0 104,0" fill="none"/>
<mask id="kcs-grunge"><rect width="160" height="160" fill="#fff"/><circle cx="46" cy="38" r="9" fill="#000" opacity="0.35"/><circle cx="122" cy="104" r="11" fill="#000" opacity="0.3"/><circle cx="98" cy="30" r="5" fill="#000" opacity="0.4"/><circle cx="34" cy="112" r="7" fill="#000" opacity="0.3"/><circle cx="128" cy="58" r="4" fill="#000" opacity="0.45"/></mask>
</defs>
<g mask="url(#kcs-grunge)">
<circle cx="80" cy="80" r="74" fill="none" stroke="${ink}" stroke-width="2"/>
<circle cx="80" cy="80" r="70" fill="none" stroke="${ink}" stroke-width="3.4"/>
${ticks}
<circle cx="80" cy="80" r="62" fill="none" stroke="${ink}" stroke-width="1.2" stroke-dasharray="3 2.4"/>
<text font-size="7.5" letter-spacing="2.6" fill="${ink}" font-family="'Space Mono', 'Pretendard', 'Pretendard Variable', sans-serif" font-weight="700"><textPath href="#kcs-arc-top" startOffset="50%" text-anchor="middle">★ IMMIGRATION ★ ADMITTED ★</textPath></text>
<text font-size="7" letter-spacing="2.2" fill="${ink}" opacity="0.85" font-family="'Space Mono', 'Pretendard', 'Pretendard Variable', sans-serif"><textPath href="#kcs-arc-bot" startOffset="50%" text-anchor="middle">VISABLE · ${serial}</textPath></text>
<text x="80" y="70" text-anchor="middle" font-size="26">${country.flag}</text>
<text x="80" y="92" text-anchor="middle" font-size="${nameSize}" letter-spacing="1.6" fill="${ink}" font-family="'Space Mono', 'Pretendard', 'Pretendard Variable', sans-serif" font-weight="700">${name}</text>
<line x1="48" y1="99" x2="112" y2="99" stroke="${ink}" stroke-width="1" opacity="0.6"/>
<text x="80" y="112" text-anchor="middle" font-size="9" letter-spacing="1.4" fill="${ink}" font-family="'Space Mono', 'Pretendard', 'Pretendard Variable', sans-serif" font-weight="700">${day} ${month} ${year}</text>
<text x="80" y="124" text-anchor="middle" font-size="7" letter-spacing="3" fill="${ink}" opacity="0.7" font-family="'Space Mono', 'Pretendard', 'Pretendard Variable', sans-serif">— ENTRY —</text>
</g>
</svg>`;
            }
            // Country pool was previously fetched from external country/flag APIs;
            // replaced with a static local list to avoid external network calls.
            const KS_COUNTRIES = [
                {name:{common:'NEPAL'},cca2:'NP',flag:'🇳🇵'},{name:{common:'VIETNAM'},cca2:'VN',flag:'🇻🇳'},
                {name:{common:'PHILIPPINES'},cca2:'PH',flag:'🇵🇭'},{name:{common:'INDONESIA'},cca2:'ID',flag:'🇮🇩'},
                {name:{common:'THAILAND'},cca2:'TH',flag:'🇹🇭'},{name:{common:'CAMBODIA'},cca2:'KH',flag:'🇰🇭'},
                {name:{common:'MONGOLIA'},cca2:'MN',flag:'🇲🇳'},{name:{common:'UZBEKISTAN'},cca2:'UZ',flag:'🇺🇿'},
                {name:{common:'CHINA'},cca2:'CN',flag:'🇨🇳'},{name:{common:'USA'},cca2:'US',flag:'🇺🇸'},
                {name:{common:'JAPAN'},cca2:'JP',flag:'🇯🇵'},{name:{common:'INDIA'},cca2:'IN',flag:'🇮🇳'},
            ];
            const country = KS_COUNTRIES[Math.floor(Math.random() * KS_COUNTRIES.length)];
            if (!country.flag) country.flag = flagFromCca2(country.cca2);
            const searchWrapper = document.querySelector('.k-gw-search, .p-gw-search, [class*="gw-search"]');
            if (!searchWrapper) return;
            searchWrapper.style.position = 'relative';
            searchWrapper.insertAdjacentHTML('beforeend', buildCountryStamp(country, _kd.getDate(), _kMonths[_kd.getMonth()], _kd.getFullYear()));
            if (!document.getElementById('k-stamp-country-style')) {
                const style = document.createElement('style');
                style.id = 'k-stamp-country-style';
                /* z-index 를 음수로 두는 이유: 검색 알약은 backdrop-filter 때문에
                   자체 쌓임 맥락을 만든다. 음수 자식은 알약의 배경 위, 내용물
                   아래에 칠해진다 — 도장이 유리 위에 찍힌 것처럼 보이면서
                   '확인하기' 버튼이나 입력 문구를 절대 덮지 않는다.
                   양수였을 때는 도장 원호가 CTA 버튼을 가로질렀다. */
                style.textContent = ':root[data-theme="archive_diary"] #k-stamp-country{position:absolute;bottom:-104px;right:-96px;transform:rotate(18deg);opacity:0.85;pointer-events:none;z-index:-1;filter:drop-shadow(0 1px 0 rgba(0,0,0,0.06));}'
                    /* 좁은 폭에서는 140px 도장이 알약보다 커서 뷰포트 밖으로
                       빠져나간다 — 크기와 위치를 같이 줄인다. */
                    + '@media (max-width:720px){:root[data-theme="archive_diary"] #k-stamp-country{width:104px;height:104px;bottom:-30px;right:4px;}}'
                    /* The stamp is injected only while archive_diary is active, but the element
                       survives a runtime toggle to civic — keep it kitsch-only. */
                    + ':root:not([data-theme="archive_diary"]) #k-stamp-country{display:none !important;}';
                document.head.appendChild(style);
            }
        })();
    }

}

let _revealObs = null, _staggerObs = null;
function runCountUp(child) {
    const countEl = child.querySelector('[data-count]');
    if (!countEl) return;
    const target = parseInt(countEl.dataset.count, 10);
    if (isNaN(target)) return;
    let current = 0;
    const step = Math.max(1, Math.ceil(target / 20));
    const timer = setInterval(() => {
        current = Math.min(current + step, target);
        countEl.textContent = current;
        if (current >= target) clearInterval(timer);
    }, 40);
}
function initScrollReveal() {
    const prefersReduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (prefersReduced) {
        document.querySelectorAll('[data-reveal], [data-stagger] > *').forEach(el => el.classList.add('revealed'));
        document.querySelectorAll('[data-count]').forEach(el => { el.textContent = el.dataset.count; });
        return;
    }
    _revealObs = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (!entry.isIntersecting) return;
            const el = entry.target;
            const delay = parseInt(el.dataset.revealDelay || '0', 10);
            setTimeout(() => el.classList.add('revealed'), delay);
            _revealObs.unobserve(el);
        });
    }, { threshold: 0.12, rootMargin: '0px 0px -60px 0px' });
    document.querySelectorAll('[data-reveal]').forEach(el => _revealObs.observe(el));

    _staggerObs = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (!entry.isIntersecting) return;
            const children = Array.from(entry.target.children);
            const baseDelay = parseInt(entry.target.dataset.staggerDelay || '80', 10);
            children.forEach((child, i) => {
                setTimeout(() => {
                    child.classList.add('revealed');
                    runCountUp(child);
                }, i * baseDelay);
            });
            _staggerObs.unobserve(entry.target);
        });
    }, { threshold: 0.08, rootMargin: '0px 0px -40px 0px' });
    document.querySelectorAll('[data-stagger]').forEach(group => _staggerObs.observe(group));
}
function resetReveal() {
    // Never show stale zero counts after the live visa dataset has loaded.
    document.querySelectorAll('[data-count]').forEach(el => { el.textContent = el.dataset.count || '0'; });
    document.querySelectorAll('[data-reveal].revealed').forEach(el => {
        el.classList.remove('revealed');
        if (_revealObs) _revealObs.observe(el);
    });
    document.querySelectorAll('[data-stagger] > *.revealed').forEach(el => el.classList.remove('revealed'));
    document.querySelectorAll('[data-stagger]').forEach(group => { if (_staggerObs) _staggerObs.observe(group); });
}

// ── Scroll Reveal Animation ───────────────────────────────
/* scroll-reveal observer moved to src/features/landing-animation.js (Phase 3). */

// ── Diaspora → Paradiso Anagram (paradiso.html reference) ─────────
/* initFigmaAnagram moved to src/features/landing-animation.js (Phase 3). */

// ── Visa Manual Section Functions ──────────────────────────────────────────

// 입국 전 트랙: 목적 선택 UI
function startPreEntryTrack() {
  const dynamicEl = document.getElementById('visaManualDynamic');
  if (!dynamicEl) return;
  const en = currentLanguage === 'en';
  const zh = currentLanguage === 'zh-CN';

  dynamicEl.innerHTML = `
    <div class="visa-step-container">
      <div class="visa-step-header">
        <h3>${zh ? '入境前 — 驻外公馆签证申请' : en ? 'Before entry — consular visa issuance' : '입국 전 — 재외공관 사증(비자) 신청'}</h3>
        <p>${zh ? '请选择您来韩国的目的，我们会为您推荐匹配的居留资格。' : en ? 'Choose your purpose for coming to Korea. We will suggest matching residence statuses.' : '한국에 오시는 목적을 선택하세요. 맞춤형 체류자격을 추천해 드립니다.'}</p>
      </div>
      <div class="visa-purpose-grid">
        <div class="visa-purpose-card" onclick="showVisaRecommendations('study')">
          <div class="visa-purpose-icon">📚</div>
          <div>${zh ? '留学·研修' : en ? 'Study & training' : '유학·연수'}</div>
          <div class="visa-purpose-hint">${zh ? '大学、语言研修、专业教育' : en ? 'University, language study, professional training' : '대학, 어학연수, 전문교육'}</div>
        </div>
        <div class="visa-purpose-card" onclick="showVisaRecommendations('work')">
          <div class="visa-purpose-icon">💼</div>
          <div>${zh ? '就业·事业' : en ? 'Work & business' : '취업·사업'}</div>
          <div class="visa-purpose-hint">${zh ? '专业职、一般就业、投资' : en ? 'Professionals, general employment, investment' : '전문직, 일반 취업, 투자'}</div>
        </div>
        <div class="visa-purpose-card" onclick="showVisaRecommendations('family')">
          <div class="visa-purpose-icon">👨‍👩‍👧‍👦</div>
          <div>${zh ? '家庭·婚姻' : en ? 'Family & marriage' : '가족·결혼'}</div>
          <div class="visa-purpose-hint">${zh ? '随行、婚姻移民、永住' : en ? 'Accompanying family, marriage migration, permanent residence' : '동반, 결혼이민, 영주'}</div>
        </div>
        <div class="visa-purpose-card" onclick="showVisaRecommendations('visit')">
          <div class="visa-purpose-icon">✈️</div>
          <div>${zh ? '访问·旅游' : en ? 'Visit & tourism' : '방문·관광'}</div>
          <div class="visa-purpose-hint">${zh ? '短期访问、探亲' : en ? 'Short visits, visiting relatives' : '단기 방문, 친지 방문'}</div>
        </div>
      </div>
    </div>`;

  dynamicEl.scrollIntoView({ behavior: 'smooth', block: 'center' });
}

// 입국 후 트랙: 민원 유형 선택 UI
function startInKoreaTrack() {
  const dynamicEl = document.getElementById('visaManualDynamic');
  if (!dynamicEl) return;
  const en = currentLanguage === 'en';
  const zh = currentLanguage === 'zh-CN';

  dynamicEl.innerHTML = `
    <div class="visa-step-container">
      <div class="visa-step-header">
        <h3>${zh ? '入境后 — 国内居留民愿程序' : en ? 'After entry — in-Korea residence services' : '입국 후 — 국내 체류 민원 절차'}</h3>
        <p>${zh ? '请选择您需要的程序。' : en ? 'Choose the procedure you need.' : '필요하신 절차를 선택하세요.'}</p>
      </div>
      <div class="visa-purpose-grid">
        <div class="visa-purpose-card" onclick="selectInKoreaAction('register')">
          <div class="visa-purpose-icon">📝</div>
          <div>${zh ? '外国人登录' : en ? 'Foreigner registration' : '외국인등록'}</div>
          <div class="visa-purpose-hint">${zh ? '入境后 90 天以内' : en ? 'Within 90 days of entry' : '입국 후 90일 이내'}</div>
        </div>
        <div class="visa-purpose-card" onclick="selectInKoreaAction('extend')">
          <div class="visa-purpose-icon">⏳</div>
          <div>${zh ? '居留期限延长' : en ? 'Extension of stay' : '체류기간 연장'}</div>
          <div class="visa-purpose-hint">${zh ? '到期日前申请' : en ? 'Apply before expiry' : '만료일 전 신청'}</div>
        </div>
        <div class="visa-purpose-card" onclick="selectInKoreaAction('change')">
          <div class="visa-purpose-icon">🔄</div>
          <div>${zh ? '居留资格变更' : en ? 'Change of status' : '체류자격 변경'}</div>
          <div class="visa-purpose-hint">${zh ? '转为其他资格' : en ? 'Switch to another status' : '다른 자격으로 전환'}</div>
        </div>
        <div class="visa-purpose-card" onclick="selectInKoreaAction('workplace')">
          <div class="visa-purpose-icon">🏢</div>
          <div>${zh ? '工作单位变更·追加' : en ? 'Change/add workplace' : '근무처 변경·추가'}</div>
          <div class="visa-purpose-hint">${zh ? '持就业资格者' : en ? 'For work-status holders' : '취업 자격 소지자'}</div>
        </div>
      </div>
    </div>`;

  dynamicEl.scrollIntoView({ behavior: 'smooth', block: 'center' });
}

// ── 카테고리 매핑 ──────────────────────────────────────────────────────────
const PURPOSE_TO_CAT = {
  study:  ['study'],
  work:   ['work', 'invest'],
  family: ['family'],
  visit:  ['short', 'other', 'diplo']
};
const ACTION_CAT_LABELS = {
  study:  '📚 유학·연수',
  work:   '💼 취업·전문직 / 투자·경영',
  family: '👨‍👩‍👧‍👦 가족·이민',
  visit:  '✈️ 단기 체류 / 기타'
};
const ACTION_CAT_LABELS_EN = {
  study:  '📚 Study & training',
  work:   '💼 Work & professional / investment & management',
  family: '👨‍👩‍👧‍👦 Family & migration',
  visit:  '✈️ Short stay / other'
};
const ACTION_CAT_LABELS_ZH = {
  study:  '📚 留学·研修',
  work:   '💼 就业·专业职 / 投资·经营',
  family: '👨‍👩‍👧‍👦 家庭·移民',
  visit:  '✈️ 短期居留 / 其他'
};
const DOC_MODAL_ACTION_MAP = { register: 'new', extend: 'ext' };
let _currentInKoreaAction = 'extend';

// ── 입국 전 트랙: 목적별 체류자격 추천 ────────────────────────────────────
function showVisaRecommendations(purpose) {
  const dynamicEl = document.getElementById('visaManualDynamic');
  if (!dynamicEl || !dataReady) return;

  const en = currentLanguage === 'en';
  const zh = currentLanguage === 'zh-CN';
  const targetCats  = PURPOSE_TO_CAT[purpose] || [];
  const SKIP_CATS   = ['faq', 'scn', 'nhis'];
  const matchedVisas = VISA_DATA.filter(v => targetCats.includes(v.cat) && !SKIP_CATS.includes(v.cat));

  if (!matchedVisas.length) {
    dynamicEl.innerHTML = `
      <div class="visa-step-container">
        <div class="visa-step-header">
          <h3>${zh ? '没有符合该目的的居留资格。' : en ? 'No residence status matches this purpose.' : '해당 목적에 맞는 체류자격이 없습니다.'}</h3>
          <p>${zh ? '请改用搜索框查找。' : en ? 'Try the search box instead.' : '검색창을 이용해 보세요.'}</p>
        </div>
      </div>`;
    return;
  }

  const label = (zh ? ACTION_CAT_LABELS_ZH[purpose] : en ? ACTION_CAT_LABELS_EN[purpose] : ACTION_CAT_LABELS[purpose]) || (zh ? '推荐' : en ? 'Suggested' : '추천');
  const countLabel = zh ? `${label} 居留资格（${matchedVisas.length} 项）` : en ? `${label} statuses (${matchedVisas.length})` : `${label} 체류자격 (${matchedVisas.length}건)`;
  const cardsHtml = matchedVisas.map(v => `
    <div class="visa-result-card">
      <div class="visa-result-header">
        <span class="bc">${escapeHtml(v.code)}</span>
        <span class="vt">${escapeHtml(getLocalizedVisaName(v) || v.name)}</span>
        ${v.period ? `<span class="bp">${escapeHtml(v.period)}</span>` : ''}
      </div>
      <p class="visa-result-desc">${escapeHtml(makeManualPreview(v.newReq, 100) || (zh ? '请查看详细信息。' : en ? 'Check the detailed information.' : '상세 정보를 확인하세요.'))}</p>
      <div class="visa-result-actions">
        <button class="visa-track-btn" data-pg="file" onclick="openDocModal('${escapeHtml(v.code)}', 'new')">${zh ? '新申请发放材料' : en ? 'New issuance documents' : '신규 발급 서류'}</button>
        <button class="visa-track-btn visa-track-btn-secondary" data-pg="sparkles" onclick="openAiModal('${escapeHtml(v.code)}')">${zh ? 'AI 分析' : en ? 'AI analysis' : 'AI 분석'}</button>
      </div>
    </div>`).join('');

  dynamicEl.innerHTML = `
    <div class="visa-step-container">
      <div class="visa-step-header">
        <h3>${countLabel}</h3>
        <p>${zh ? '请选择与您情况最匹配的居留资格。' : en ? 'Choose the residence status that best fits your situation.' : '본인의 상황과 가장 일치하는 체류자격을 선택하세요.'}</p>
        <button class="cb" style="margin-top:0.8rem;" onclick="startPreEntryTrack()">${zh ? '← 重新选择目的' : en ? '← Choose purpose again' : '← 목적 다시 선택'}</button>
      </div>
      <div class="visa-results-grid">${cardsHtml}</div>
    </div>`;

  dynamicEl.scrollIntoView({ behavior: 'smooth', block: 'center' });
}

// ── 입국 후 트랙: 민원 유형별 안내 ────────────────────────────────────────
function selectInKoreaAction(actionType) {
  const dynamicEl = document.getElementById('visaManualDynamic');
  if (!dynamicEl || !dataReady) return;
  _currentInKoreaAction = actionType;

  const en = currentLanguage === 'en';
  const zh = currentLanguage === 'zh-CN';
  const hikoreaReqBtn = `<a class="doc-trigger-btn" href="https://www.hikorea.go.kr" target="_blank" rel="noopener noreferrer">${zh ? '在 HiKorea 确认官方要件' : en ? 'Check official requirements on HiKorea' : 'HiKorea에서 공식 요건 확인'}</a>`;
  const docsVaryNote = `<p class="text-desc" style="margin-top:0.8rem;">${zh ? '具体的提交材料可能因居留资格和个人情况而异。请在 HiKorea 或管辖出入境·外国人厅确认最新指引。' : en ? 'The exact documents required can vary by residence status and personal circumstances. Check the latest guidance on HiKorea or at your competent immigration office.' : '구체적인 제출서류는 체류자격과 개인 상황에 따라 달라질 수 있습니다. HiKorea 또는 관할 출입국·외국인청에서 최신 안내를 확인하세요.'}</p>`;
  const CONFIG = {
    register: {
      title: zh ? '📝 外国人登录' : en ? '📝 Foreigner registration' : '📝 외국인등록',
      desc:   zh ? '入境后 90 天以内，须在居留地管辖的出入境·外国人厅办理外国人登录。' : en ? 'You must register as a foreigner at the immigration office for your area of residence within 90 days of entry.' : '입국 후 90일 이내에 체류지 관할 출입국·외국인청에서 외국인등록을 해야 합니다.',
      extra:  `<div class="subcode-warning" style="margin-top:0.8rem;">
                 ✅ <strong>${zh ? '提示：' : en ? 'Notice:' : '안내:'}</strong> ${zh ? '外国人登录原则上须在入境后 90 天以内申请。' : en ? 'As a rule, foreigner registration must be applied for within 90 days of entry.' : '외국인등록은 입국 후 90일 이내 신청이 원칙입니다.'}
               </div>
               ${docsVaryNote}
               ${hikoreaReqBtn}`
    },
    extend: {
      title: zh ? '⏳ 居留期限延长' : en ? '⏳ Extension of stay' : '⏳ 체류기간 연장',
      desc:   zh ? '须在居留期限到期日之前完成延长申请。' : en ? 'You must complete the extension application before your period of stay expires.' : '체류기간 만료일 전까지 연장 신청을 완료해야 합니다.',
      extra:  `<div class="subcode-warning" style="margin-top:0.8rem;">
                 ⚠️ <strong>${zh ? '注意：' : en ? 'Caution:' : '주의:'}</strong> ${zh ? '在到期当日或之后申请，可能被视为非法滞留。' : en ? 'Applying on or after the expiry date may be treated as illegal stay.' : '만료 당일·이후 신청 시 불법체류로 간주될 수 있습니다.'}
               </div>`
    },
    change: {
      title: zh ? '🔄 居留资格变更' : en ? '🔄 Change of status' : '🔄 체류자격 변경',
      desc:   zh ? '从当前居留资格变更为其他居留资格，须事先取得许可。' : en ? 'Changing from your current status of stay to a different one requires prior permission.' : '현재 체류자격에서 다른 체류자격으로 변경하려면 사전 허가가 필요합니다.',
      extra:  `<div class="subcode-warning" style="margin-top:0.8rem;">
                 ⚠️ <strong>${zh ? '注意：' : en ? 'Caution:' : '주의:'}</strong> ${zh ? '能否变更居留资格，取决于当前资格、变更目的及提交材料的审查结果。' : en ? 'Whether a change of status is possible depends on your current status, the purpose of the change, and the review of your submitted documents.' : '체류자격 변경 가능 여부는 현재 자격, 변경 목적, 제출서류 심사 결과에 따라 달라질 수 있습니다.'}
               </div>`
    },
    workplace: {
      title: zh ? '🏢 工作单位变更·追加' : en ? '🏢 Change/add workplace' : '🏢 근무처 변경·추가',
      desc:   zh ? '变更·追加工作单位，原则上须事先取得许可；持有法令所定专业知识·技术·技能者，可改以变更·追加之日起 15 日内的申报代替（出入境管理法第 21 条）。' : en ? 'In principle you must obtain prior permission to change or add a workplace; persons holding professional knowledge, skills, or expertise as prescribed by law may instead report within 15 days of the change/addition (Immigration Act Article 21).' : '근무처를 변경·추가하려면 원칙적으로 사전에 허가를 받아야 하며, 전문 지식·기술·기능 보유자로서 법령이 정하는 사람은 변경·추가한 날부터 15일 이내 신고로 갈음합니다(출입국관리법 제21조).',
      extra:  `<div class="subcode-warning" style="margin-top:0.8rem;">
                 ⚠️ <strong>${zh ? '注意：' : en ? 'Caution:' : '주의:'}</strong> ${zh ? '工作单位变更可能因居留资格不同而采取申报或许可的不同类型。' : en ? 'Workplace changes may require either a report or permission depending on the residence status.' : '근무처 변경은 체류자격별로 신고/허가 유형이 다를 수 있습니다.'}
               </div>
               ${docsVaryNote}
               ${hikoreaReqBtn}`
    }
  };

  const { title, desc, extra } = CONFIG[actionType] || { title: actionType, desc: '', extra: '' };

  dynamicEl.innerHTML = `
    <div class="visa-step-container">
      <div class="visa-step-header">
        <button class="cb" style="margin-bottom:0.8rem;" onclick="startInKoreaTrack()">${zh ? '← 重新选择程序' : en ? '← Choose procedure again' : '← 절차 다시 선택'}</button>
        <h3>${title}</h3>
        <p>${desc}</p>
      </div>
      ${extra}
      <div class="visa-search-box" style="margin-top:1.5rem;">
        <h4 style="font-size:1rem; font-weight:700; color:var(--t1); margin-bottom:0.5rem;">${zh ? '🔍 搜索您的居留资格' : en ? '🔍 Search your residence status' : '🔍 본인의 체류자격 검색'}</h4>
        <p style="font-size:0.85rem; color:var(--t3); margin-bottom:1rem;">${zh ? '请输入当前居留资格代码或名称。' : en ? 'Enter your current residence status code or name.' : '현재 체류자격 코드 또는 이름을 입력하세요.'}</p>
        <div style="display:flex; gap:0.5rem;">
          <input type="search" id="inKoreaVisaSearch" class="jc-search-input"
            style="flex:1; min-width:200px; margin-bottom:0;" placeholder="${zh ? '例：F-6, E-9, D-2' : en ? 'e.g. F-6, E-9, D-2' : '예: F-6, E-9, D-2'}"
            onkeyup="filterInKoreaVisaList(this.value)">
          <button class="visa-track-btn" style="width:auto;" onclick="searchInKoreaVisa()">${zh ? '搜索' : en ? 'Search' : '검색'}</button>
        </div>
        <div id="inKoreaVisaList" class="visa-results-grid" style="margin-top:1rem;"></div>
      </div>
    </div>`;

  dynamicEl.scrollIntoView({ behavior: 'smooth', block: 'center' });
}

// ── 보조 함수들 ────────────────────────────────────────────────────────────
function getCurrentInKoreaAction() { return _currentInKoreaAction; }

function filterInKoreaVisaList(query) {
  const listEl = document.getElementById('inKoreaVisaList');
  if (!listEl) return;
  const en = currentLanguage === 'en';
  const zh = currentLanguage === 'zh-CN';
  if (!query || !query.trim()) { listEl.innerHTML = `<p style="font-size:0.85rem;color:var(--t3);padding:0.5rem 0;">${zh ? '输入代码或名称即可显示列表。' : en ? 'Enter a code or name to see the list.' : '코드 또는 이름을 입력하면 목록이 표시됩니다.'}</p>`; return; }

  const q      = query.toLowerCase().trim();
  const SKIP   = ['faq', 'scn', 'nhis'];
  const matched = VISA_DATA
    .filter(v => !SKIP.includes(v.cat) && (v.code.toLowerCase().includes(q) || v.name.toLowerCase().includes(q)))
    .slice(0, 10);

  listEl.innerHTML = matched.map(v => `
    <div class="visa-result-card" style="cursor:pointer;" onclick="showVisaDocForAction('${escapeHtml(v.code)}')">
      <div class="visa-result-header">
        <span class="bc">${escapeHtml(v.code)}</span>
        <span class="vt">${escapeHtml(getLocalizedVisaName(v) || v.name)}</span>
        ${v.period ? `<span class="bp">${escapeHtml(v.period)}</span>` : ''}
      </div>
    </div>`).join('');
}

function searchInKoreaVisa() {
  const input = document.getElementById('inKoreaVisaSearch');
  if (input) filterInKoreaVisaList(input.value);
}

function showVisaDocForAction(visaCode) {
  const actionType = _currentInKoreaAction;
  const docMode    = DOC_MODAL_ACTION_MAP[actionType];
  if (docMode) {
    openDocModal(visaCode, docMode);
  } else {
    // change / workplace: 서류 모달 직접 지원 없음 → AI 분석으로 안내
    showToast(tx('aiDocsToast'), 'warning');
    openAiModal(visaCode);
  }
}

/* initAgentFinder moved to src/features/finders.js (Phase 3). */

/* initMedFinder moved to src/features/finders.js (Phase 3). */

/* Deadline reminders moved to src/features/reminders.js (Phase 3). */

export {
    toggleTheme, localizeRegion, localizeFinderRegions, getStoredEditorialTheme, currentEditorialTheme, updateEditorialThemeLabel,
    applyEditorialTheme, toggleEditorialTheme, toggleAccordions, initUI, renderCmdChips, injectLocalData,
    setSearchEnabled, coverageBucket, coverageCodeSortKey, updateCategoryCounts, renderDocComposerTags, loadDocComposerMeta,
    buildProcedureEvidenceIndex, fetchOptionalJson, loadVisaIssuanceData, loadVisaData, runCountUp, initScrollReveal,
    resetReveal, startPreEntryTrack, startInKoreaTrack, showVisaRecommendations, selectInKoreaAction, getCurrentInKoreaAction,
    filterInKoreaVisaList, searchInKoreaVisa, showVisaDocForAction, REGION_I18N, EDITORIAL_THEME_STORAGE_KEY, EDITORIAL_THEMES,
    VISA_DATA_API_TIMEOUT_MS, PURPOSE_TO_CAT, ACTION_CAT_LABELS, ACTION_CAT_LABELS_EN, ACTION_CAT_LABELS_ZH, DOC_MODAL_ACTION_MAP
};
export { onDomReady };
