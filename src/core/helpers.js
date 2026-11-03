// @ts-nocheck
/**
 * Small inline helpers that survived the cluster moves (Phase 3): the toast, the result-card tab labels
 * (`getLabels`, reads the inline `CL` table) and the search debug panel (reads the parse-time const
 * `SEARCH_DEBUG_ENABLED`, `qEl`, `dataReady`, `VISA_DATA` by bare name). Moved verbatim from index.html; exposed on
 * window.Visable.core, inline stubs with the same names delegate here. `escapeHtml`/`escapeRegExp`/`hl` are not
 * here: their inline copies became stubs to the identical implementations in src/render/escape.js.
 */
function showToast(message, type = 'warning') {
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.setAttribute('role', 'status');
    toast.setAttribute('aria-live', 'polite');
    toast.textContent = message;
    document.body.appendChild(toast);
    setTimeout(() => toast.classList.add('show'), 10);
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}

function getSearchDebugSnapshot(label){
    const sf = document.getElementById('searchForm');
    const stb = document.getElementById('searchToggleBtn');
    const xb = document.getElementById('xb');
    const activeEl = document.activeElement;
    return {
        label,
        bodyClassName: document.body.className,
        searchFormComputedDisplay: sf ? getComputedStyle(sf).display : '(missing)',
        searchFormInlineDisplay: sf ? sf.style.display : '(missing)',
        searchToggleAriaExpanded: stb ? stb.getAttribute('aria-expanded') : '(missing)',
        searchToggleText: stb ? stb.textContent.replace(/\s+/g, ' ').trim() : '(missing)',
        searchToggleClassName: stb ? stb.className : '(missing)',
        xbComputedDisplay: xb ? getComputedStyle(xb).display : '(missing)',
        xbClassName: xb ? xb.className : '(missing)',
        qValue: qEl ? qEl.value : '(missing)',
        activeElement: activeEl ? `${activeEl.tagName.toLowerCase()}#${activeEl.id || ''}.${activeEl.className || ''}` : '(none)'
    };
}

function ensureSearchDebugPanel(){
    if (!SEARCH_DEBUG_ENABLED || document.getElementById('searchDebugPanel')) return;
    const panel = document.createElement('aside');
    panel.id = 'searchDebugPanel';
    panel.style.cssText = 'position:fixed;right:12px;bottom:12px;z-index:99999;max-width:min(90vw,360px);background:rgba(0,0,0,.86);color:#9fffb0;font:12px/1.4 ui-monospace,SFMono-Regular,Menlo,monospace;padding:10px 12px;border:1px solid rgba(159,255,176,.5);border-radius:10px;box-shadow:0 10px 24px rgba(0,0,0,.45);white-space:pre-wrap;word-break:break-word;pointer-events:none;';
    panel.textContent = 'search debug panel';
    document.body.appendChild(panel);
}

function debugSearchState(label){
    const snapshot = getSearchDebugSnapshot(label);
    window.__PARADISO_SEARCH_DEBUG__ = snapshot;
    if (!SEARCH_DEBUG_ENABLED) return snapshot;
    ensureSearchDebugPanel();
    console.table(snapshot);
    const panel = document.getElementById('searchDebugPanel');
    if (panel) {
        panel.textContent = [
            `label: ${snapshot.label}`,
            `body: ${snapshot.bodyClassName}`,
            `searchForm(display): ${snapshot.searchFormComputedDisplay} / inline=${snapshot.searchFormInlineDisplay || '(empty)'}`,
            `toggle(aria-expanded): ${snapshot.searchToggleAriaExpanded}`,
            `toggle(text): ${snapshot.searchToggleText}`,
            `xb(display): ${snapshot.xbComputedDisplay}`,
            `input(length): ${typeof snapshot.qValue === 'string' ? snapshot.qValue.length : 0}`
        ].join('\n');
    }
    return snapshot;
}

function getLabels(v){return v.labels||CL[v.cat]||['개요','상세','FAQ'];}

export { showToast, getSearchDebugSnapshot, ensureSearchDebugPanel, debugSearchState, getLabels };
