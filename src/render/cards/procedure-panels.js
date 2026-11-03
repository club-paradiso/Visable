// @ts-nocheck
/**
 * Procedure panels of the legacy result card: procedure variants, the scenario picker, the scenario checklist
 * (localStorage via Visable.state), the procedure panel/tab renderers and the route-wizard config (structure map
 * C16 tail + C17–C19; Phase 3, moved verbatim from index.html lines 17749-18384). The two `let` picker-state
 * variables are module-private (nothing outside the cluster read them). Uses the inline globals tx(), txAt(),
 * escapeHtml(), hl(), showToast(), PROCEDURE_CONFIG, Visable.docs.* (via the inline stubs) and friends at call time
 * only (compatibility surface, ADR-009). Exposed on window.Visable.cards; the inline stubs with the same names
 * (12 functions) delegate here. Covered by tests/golden/specs/legacy-card.spec.mjs and
 * procedure.spec.mjs; sliced by the legacy checks listed in scripts/frontend_modules.json consumers.
 */
function renderProcedureVariant(visaCode, procedureKey, variant, keywords, selectedByDefault = false, alreadyShownDocs = null) {
    const effectiveDocs = alreadyShownDocs
        ? subtractDocGroupsForRender(variant.docs, alreadyShownDocs)
        : variant.docs;
    const docsHtml = renderProcedureDocGroups(effectiveDocs, keywords, visaCode, procedureKey);
    const docCount = countRenderableDocs(effectiveDocs);
    const checklistVariant = { ...variant, docs: effectiveDocs };
    const statusCode = variant.statusCode ? `<span class="manual-subcode-code">${escapeHtml(variant.statusCode)}</span>` : '';
    const scenarioText = stripManualArtifacts(variant.scenario);
    const scenario = scenarioText ? `<div class="manual-subcode-desc">${escapeHtml(scenarioText)}</div>` : '';
    const cleanNotes = variant.notes.map(n => stripManualArtifacts(n)).filter(Boolean);
    const notes = cleanNotes.length ? `<div class="manual-subcode-desc">${cleanNotes.map(escapeHtml).join('<br>')}</div>` : '';
    const refs = variant.manualRefs.map(ref => [ref.manualName, ref.manualVersion, ref.pageRange].filter(Boolean).map(escapeHtml).join(' · ')).filter(Boolean);
    const citations = refs.length ? `<div class="manual-subcode-desc" style="margin-top:0.5rem; opacity:0.85;">${refs.join('<br>')}</div>` : '';
    return `<div class="manual-subcode-card${selectedByDefault ? ' is-selected' : ''}" data-procedure-variant="${escapeHtml(variant.id)}" data-procedure-variant-card="${escapeHtml(variant.id)}">
        <div class="scenario-selected-badge">${escapeHtml(tx('scenarioSelectedBadge'))}</div>
        <div class="manual-subcode-top">${statusCode}<span class="manual-subcode-name">${escapeHtml(variant.label)}</span></div>
        ${scenario}
        <div class="procedure-doc-count">${escapeHtml(tx('documentCountLabel', { count: docCount }))}</div>
        ${docsHtml ? `<div class="doc-group-grid">${docsHtml}</div>` : `<div class="doc-group-empty">${escapeHtml(tx('docReviewFallback'))}</div>`}
        ${(cleanNotes.length || refs.length) ? `<details class="source-limitation-detail" style="margin-top:0.5rem;"><summary>${escapeHtml(tx('procNotesToggle') || '세부 안내')}</summary><div class="source-limitation-body">${notes}${citations}</div></details>` : ''}
        <div class="scenario-selected-actions">
            ${renderScenarioSelectedContextBanner(visaCode, procedureKey, variant.label)}
            ${renderScenarioChecklist(visaCode, procedureKey, checklistVariant)}
            <div class="scenario-selected-note">${escapeHtml(tx('scenarioSelectedReferenceNote'))}</div>
            <button type="button" class="scenario-ai-handoff-btn" data-action="ask-selected-procedure-variant" data-visa-code="${escapeHtml(visaCode)}" data-procedure-key="${escapeHtml(procedureKey)}" data-variant-id="${escapeHtml(variant.id)}" data-variant-label="${escapeHtml(variant.label)}">${escapeHtml(tx('scenarioAskAi'))}</button>
        </div>
    </div>`;
}

// --- In-screen scenario picker popup -------------------------------------
// The scenario choices live in a modal dialog (#scenarioPickerOverlay) populated
// on demand from the originating selector's hidden variant cards. Picking a
// scenario reveals only that card; everything else stays hidden.
let scenarioPickerActiveSelector = null;
let scenarioPickerActivePanel = null;

function closeScenarioPicker() {
    const panel = scenarioPickerActivePanel;
    if (panel) {
        if (panel._escHandler) { document.removeEventListener('keydown', panel._escHandler); panel._escHandler = null; }
        if (panel._outsideHandler) { document.removeEventListener('pointerdown', panel._outsideHandler, true); panel._outsideHandler = null; }
        panel.hidden = true;
    }
    if (scenarioPickerActiveSelector) {
        const trigger = scenarioPickerActiveSelector.querySelector('.scenario-picker-trigger');
        if (trigger) trigger.setAttribute('aria-expanded', 'false');
    }
    const bd = document.getElementById('scenarioPickerBackdrop');
    if (bd) bd.classList.remove('is-active');
    scenarioPickerActivePanel = null;
    scenarioPickerActiveSelector = null;
}

function openScenarioPicker(trigger) {
    const selector = trigger.closest('[data-procedure-variant-selector]');
    if (!selector) return;
    const panel = selector.querySelector('.scenario-picker-panel');
    // 토글: 이미 열린 패널 클릭 시 닫기
    if (panel && !panel.hidden) { closeScenarioPicker(); return; }
    // 다른 열린 패널 먼저 닫기
    closeScenarioPicker();
    if (!panel) return;
    const choicesHost = panel.querySelector('.scenario-picker-panel-choices');
    if (!choicesHost) return;
    // Track as active up-front so any failure path below routes through
    // closeScenarioPicker(), which always clears the (mobile) backdrop and the
    // trigger's expanded state — never leaving a dark overlay with no dialog.
    scenarioPickerActiveSelector = selector;
    scenarioPickerActivePanel = panel;
    try {
        const selectedId = selector.getAttribute('data-selected-variant') || '';
        const cards = Array.from(selector.querySelectorAll('[data-procedure-variant-card]'));
        // Build the dialog content FIRST. Only reveal the panel (and, on mobile,
        // the backdrop) once content exists — so the dark overlay never precedes
        // a rendered dialog.
        choicesHost.innerHTML = cards.map((card, i) => {
            const id = card.getAttribute('data-procedure-variant-card') || '';
            const label = (card.querySelector('.manual-subcode-name')?.textContent || '').trim();
            const code = (card.querySelector('.manual-subcode-code')?.textContent || '').trim();
            const preview = (card.querySelector('.manual-subcode-desc')?.textContent || '').trim();
            const pressed = id === selectedId ? 'true' : 'false';
            return `<button type="button" class="scenario-choice scenario-picker-choice" role="listitem" data-action="choose-scenario-variant" data-variant-id="${escapeHtml(id)}" aria-pressed="${pressed}">
                <span class="scenario-choice-marker" aria-hidden="true"><span class="scenario-choice-num">${i + 1}</span></span>
                <span class="scenario-choice-body">
                    <span class="scenario-choice-main"><span class="scenario-picker-choice-label">${escapeHtml(label)}</span>${code ? `<span class="manual-subcode-code">${escapeHtml(code)}</span>` : ''}</span>
                    ${preview ? `<span class="scenario-choice-preview">${escapeHtml(makeManualPreview(preview, 110))}</span>` : ''}
                </span>
                <span class="scenario-choice-go" aria-hidden="true">→</span>
            </button>`;
        }).join('');
        const firstBtn = choicesHost.querySelector('button');
        if (!firstBtn) throw new Error('no scenario choices to render');
        panel.hidden = false;
        // Guard against a stranded dark overlay: if the panel has no layout box
        // (e.g. its procedure tab is not the active/visible one), close instead
        // of darkening the page behind an invisible dialog.
        const rect = panel.getBoundingClientRect();
        if (rect.width === 0 && rect.height === 0) throw new Error('scenario picker panel is not visible');
        trigger.setAttribute('aria-expanded', 'true');
        // 모바일 백드롭 표시 (CSS gates display to ≤540px; harmless on desktop).
        const bd = document.getElementById('scenarioPickerBackdrop');
        if (bd) bd.classList.add('is-active');
        // 첫 번째 선택지로 포커스
        requestAnimationFrame(() => firstBtn.focus());
        // Escape 키로 닫기
        const escHandler = e => { if (e.key === 'Escape') { closeScenarioPicker(); trigger.focus(); } };
        panel._escHandler = escHandler;
        document.addEventListener('keydown', escHandler);
        // 외부 클릭 시 닫기 (약간 지연해 현재 클릭 이벤트 제외)
        const outsideHandler = e => {
            if (!panel.contains(e.target) && e.target !== trigger && !trigger.contains(e.target)) {
                closeScenarioPicker();
            }
        };
        panel._outsideHandler = outsideHandler;
        setTimeout(() => document.addEventListener('pointerdown', outsideHandler, true), 100);
    } catch (err) {
        if (typeof console !== 'undefined' && console.warn) console.warn('[scenario-picker] open failed:', err && err.message);
        // Reset all open/backdrop state so the page is never left dark.
        closeScenarioPicker();
        if (typeof showToast === 'function') showToast(tx('scenarioPickerOpenError'));
    }
}

function chooseScenarioVariant(button) {
    const id = button.dataset.variantId || '';
    const selector = scenarioPickerActiveSelector;
    closeScenarioPicker();
    if (selector) applyScenarioSelection(selector, id);
}

function clearScenarioSelection(button) {
    const selector = button.closest('[data-procedure-variant-selector]');
    if (selector) applyScenarioSelection(selector, '');
}

function applyScenarioSelection(selector, selectedId) {
    if (!selector) return;
    if (selectedId) selector.setAttribute('data-selected-variant', selectedId);
    else selector.removeAttribute('data-selected-variant');
    selector.classList.toggle('has-selection', !!selectedId);
    let selectedCard = null;
    selector.querySelectorAll('[data-procedure-variant-card]').forEach(card => {
        const isSelected = !!selectedId && card.dataset.procedureVariantCard === selectedId;
        card.classList.toggle('is-selected', isSelected);
        card.classList.toggle('is-muted', !!selectedId && !isSelected);
        if (isSelected) selectedCard = card;
    });
    const labelEl = selector.querySelector('.scenario-picker-trigger-label');
    const clearBtn = selector.querySelector('.scenario-picker-clear');
    const picked = selectedCard ? (selectedCard.querySelector('.manual-subcode-name')?.textContent || '').trim() : '';
    if (labelEl) {
        labelEl.textContent = picked ? `✓ ${picked}` : tx('scenarioPickerTrigger');
    }
    if (clearBtn) clearBtn.hidden = !selectedId;
    // Carry the same safe context to the floating Waymaker (ai.html) CTA.
    if (selectedId && selectedCard) {
        const visaCode = selector.getAttribute('data-visa-code') || '';
        const procedureKey = selector.getAttribute('data-procedure-variant-selector') || '';
        setSelectedScenarioHandoff(visaCode, procedureKey, selectedId, picked);
    } else {
        clearSelectedScenarioHandoff();
    }
}

function renderProcedureVariants(v, proc, keywords, alreadyShownDocs = null) {
    if (!proc.variants.length) return '';
    const title = tx('scenarioSelectorTitle');
    const notice = tx('scenarioSelectorCopy');
    const officialLabelsNote = currentLanguage === 'ko' ? '' : `<p class="scenario-official-labels-note">${escapeHtml(tx('scenarioOfficialLabelsKoNote'))}</p>`;
    // Every scenario — even a lone one (e.g. F-4 외국인등록 → 국내거소신고) — is
    // presented behind the in-screen popup, so clicking a procedure never dumps
    // scenario docs inline. The user opens the popup, picks their situation, and
    // only that scenario's 절차·서류 render. Cards therefore start unselected
    // (selectedByDefault = false) and stay hidden until a pick.
    const cardsHtml = proc.variants.map(variant => renderProcedureVariant(v.code, proc.key, variant, keywords, false, alreadyShownDocs)).join('');
    const head = `<div><h5 class="scenario-selector-heading">${escapeHtml(title)}</h5><p class="scenario-selector-copy">${escapeHtml(notice)}</p>${officialLabelsNote}</div>`;
    // The choice happens in an in-screen popup. Until the user picks their
    // situation, NONE of the scenario cards are shown — only the selected one
    // renders afterwards — so the result stays uncluttered. A single-scenario
    // procedure uses the same popup path for a consistent experience.
    const variantCount = proc.variants.length;
    return `<div class="procedure-variant-list scenario-needs-pick" data-procedure-variant-selector="${escapeHtml(proc.key)}" data-visa-code="${escapeHtml(v.code)}">
        ${head}
        <div class="scenario-picker-bar">
            <button type="button" class="scenario-picker-trigger" data-action="open-scenario-picker" data-procedure-key="${escapeHtml(proc.key)}" data-visa-code="${escapeHtml(v.code)}" aria-haspopup="dialog" aria-expanded="false">
                <span class="scenario-picker-trigger-label">${escapeHtml(tx('scenarioPickerTrigger'))}</span>
                <span class="scenario-picker-trigger-count" aria-hidden="true">${variantCount}</span>
                <span class="scenario-picker-trigger-caret" aria-hidden="true">▾</span>
            </button>
            <button type="button" class="scenario-picker-clear" data-action="clear-procedure-variant" hidden>${escapeHtml(tx('scenarioPickerClear'))}</button>
            <div class="scenario-picker-panel" hidden role="dialog" aria-label="${escapeHtml(title)}">
                <div class="scenario-picker-panel-inner">
                    <div class="scenario-picker-panel-head">
                        <span class="scenario-picker-panel-title">${escapeHtml(title)}</span>
                        <button type="button" class="scenario-picker-panel-x" data-action="close-scenario-picker" aria-label="${escapeHtml(tx('closeModal'))}"><span class="pg pg-x pg-solo" aria-hidden="true"></span></button>
                    </div>
                    <div class="scenario-picker-panel-choices" role="list"></div>
                </div>
            </div>
        </div>
        <p class="scenario-picker-empty-hint">${escapeHtml(tx('scenarioPickerEmptyHint'))}</p>
        <div class="manual-subcode-grid manual-subcode-grid--docs">${cardsHtml}</div>
    </div>`;
}

// --- Selected scenario action checklist ---------------------------------
// Personal preparation aid only. Checkbox state lives in localStorage scoped
// to the selected visa/procedure/variant; it is NEVER sent to the backend or
// AI, and never stores personal information. See
// docs/data/SELECTED_SCENARIO_ACTION_CHECKLIST_2026_05.md.
const SCENARIO_CHECKLIST_STORAGE_PREFIX = 'paradiso:scenario-checklist:';
// Display groups follow the user-facing Visable classification (the four
// internal buckets remain the data model; see paradisoBuildDocDisplayGroups).
const SCENARIO_CHECKLIST_GROUPS = [
    { key: 'basic', labelIndex: 0, fallback: '항상 확인할 서류' },
    { key: 'situational', labelIndex: 1, fallback: '상황별 추가 서류' }
];

function hashScenarioChecklistItem(text) {
    // Stable djb2-style hash so a document item maps to the same storage key
    // across renders without persisting the (Korean) item text in the key.
    let h = 5381;
    const s = String(text || '');
    for (let i = 0; i < s.length; i++) h = (((h << 5) + h) + s.charCodeAt(i)) | 0;
    return (h >>> 0).toString(36);
}

function scenarioChecklistScopePrefix(visaCode, procedureKey, variantId) {
    // Storage key is scoped by visa/status code, procedure key and variant id.
    return SCENARIO_CHECKLIST_STORAGE_PREFIX
        + [visaCode, procedureKey, variantId].map(part => encodeURIComponent(String(part || ''))).join(':')
        + ':';
}

function scenarioChecklistItemStorageKey(visaCode, procedureKey, variantId, group, itemText) {
    // ...further scoped by document group and a stable hash of the item text.
    return scenarioChecklistScopePrefix(visaCode, procedureKey, variantId) + group + ':' + hashScenarioChecklistItem(itemText);
}

function scenarioChecklistStoreGet(key) { return Visable.state.read(key); }
function scenarioChecklistStoreSet(key, value) { return Visable.state.write(key, value); }
function scenarioChecklistStoreRemove(key) { Visable.state.remove(key); }

function renderScenarioChecklist(visaCode, procedureKey, variant) {
    if (!variant) return '';
    const docs = variant.docs || {};
    const variantId = variant.id || '';
    const displayGroups = paradisoBuildDocDisplayGroups(docs);
    const groupsHtml = SCENARIO_CHECKLIST_GROUPS.map(group => {
        const items = Array.isArray(displayGroups[group.key]) ? displayGroups[group.key] : [];
        if (!items.length) return '';
        const groupTitle = txAt('docUxGroupLabels', group.labelIndex, group.fallback);
        const rows = items.map(item => {
            const rawText = String(item || '').trim();
            if (!rawText) return '';
            const isDocId = rawText.startsWith('doc_');
            const textBase = isDocId ? (DOC_DICT[rawText] || tx('docDefinitionNeeded')) : rawText;
            const text = paradisoCanonicalAppFormText(textBase, procedureKey, normalizeVisaCode(visaCode));
            const storageKey = scenarioChecklistItemStorageKey(visaCode, procedureKey, variantId, group.key, rawText);
            const checked = scenarioChecklistStoreGet(storageKey) === '1' ? ' checked' : '';
            const helpButton = renderDocumentHelpButton(rawText, text);
            return `<li class="scenario-checklist-row">
                <label class="scenario-checklist-label">
                    <input type="checkbox" class="scenario-checklist-checkbox" data-scenario-checklist-item data-storage-key="${escapeHtml(storageKey)}"${checked}>
                    <span class="scenario-checklist-itemtext">${escapeHtml(text)}</span>
                </label>
                ${helpButton}
            </li>`;
        }).filter(Boolean).join('');
        if (!rows) return '';
        return `<fieldset class="scenario-checklist-group" data-group="${group.key}">
            <legend class="scenario-checklist-group-title">${escapeHtml(groupTitle)}</legend>
            <ul class="scenario-checklist-list">${rows}</ul>
        </fieldset>`;
    }).filter(Boolean).join('');
    if (!groupsHtml) return '';
    const sourcePages = (variant.manualRefs || []).map(ref => ref && ref.pageRange).filter(Boolean).join(' · ');
    const procedureLabel = getProcedureLabelByKey(procedureKey, procedureKey);
    const title = tx('scenarioChecklistTitle');
    const dataAttrs = `data-visa-code="${escapeHtml(visaCode)}" data-procedure-key="${escapeHtml(procedureKey)}" data-variant-id="${escapeHtml(variantId)}" data-variant-label="${escapeHtml(variant.label || '')}" data-status-code="${escapeHtml(variant.statusCode || '')}" data-procedure-label="${escapeHtml(procedureLabel)}" data-source-pages="${escapeHtml(sourcePages)}"`;
    return `<section class="scenario-checklist" data-scenario-checklist ${dataAttrs} aria-label="${escapeHtml(title)}">
        <h6 class="scenario-checklist-title">${escapeHtml(title)}</h6>
        <div class="scenario-checklist-groups">${groupsHtml}</div>
        <div class="scenario-checklist-actions">
            <button type="button" class="scenario-checklist-btn" data-action="copy-scenario-checklist">${escapeHtml(tx('scenarioChecklistCopy'))}</button>
            <button type="button" class="scenario-checklist-btn" data-action="print-scenario-checklist">${escapeHtml(tx('scenarioChecklistPrint'))}</button>
            <button type="button" class="scenario-checklist-btn" data-action="reset-scenario-checklist">${escapeHtml(tx('scenarioChecklistReset'))}</button>
        </div>
        <p class="scenario-checklist-safety">${escapeHtml(tx('scenarioChecklistSafetyNote'))}</p>
        <p class="scenario-checklist-guidance">${escapeHtml(tx('scenarioChecklistConfirmGuidance'))}</p>
        <button type="button" class="scenario-ai-handoff-btn scenario-checklist-ai-btn" data-action="ask-checklist-missing" data-visa-code="${escapeHtml(visaCode)}" data-procedure-key="${escapeHtml(procedureKey)}" data-variant-id="${escapeHtml(variantId)}" data-variant-label="${escapeHtml(variant.label || '')}">${escapeHtml(tx('scenarioChecklistMissingAsk'))}</button>
        <div class="scenario-checklist-status" role="status" aria-live="polite"></div>
    </section>`;
}

function persistScenarioChecklistItem(checkbox) {
    const key = checkbox.getAttribute('data-storage-key');
    if (!key) return;
    if (checkbox.checked) scenarioChecklistStoreSet(key, '1');
    else scenarioChecklistStoreRemove(key);
    // Keep any other mounted checkbox sharing the same scoped key in sync — e.g.
    // the search-result card and its cloned detail-drawer copy.
    syncScenarioChecklistCheckboxes(key, checkbox.checked, checkbox);
}

function syncScenarioChecklistCheckboxes(key, checked, origin) {
    if (!key) return;
    document.querySelectorAll('input[type="checkbox"][data-scenario-checklist-item]').forEach(cb => {
        if (cb !== origin && cb.getAttribute('data-storage-key') === key && cb.checked !== checked) {
            cb.checked = checked;
        }
    });
}

// Cloned cards (e.g. the detail drawer) carry render-time checkbox markup that
// can be stale relative to localStorage. Re-hydrate every checklist checkbox in
// a container from its scoped storage key so localStorage stays authoritative.
function hydrateScenarioChecklistState(container) {
    if (!container) return;
    container.querySelectorAll('input[type="checkbox"][data-scenario-checklist-item]').forEach(cb => {
        const key = cb.getAttribute('data-storage-key');
        if (key) cb.checked = scenarioChecklistStoreGet(key) === '1';
    });
}

function collectScenarioChecklistData(root) {
    const groups = [];
    root.querySelectorAll('.scenario-checklist-group').forEach(fs => {
        const title = (fs.querySelector('.scenario-checklist-group-title')?.textContent || '').trim();
        const items = [];
        fs.querySelectorAll('.scenario-checklist-row').forEach(row => {
            const cb = row.querySelector('input[type="checkbox"]');
            const text = (row.querySelector('.scenario-checklist-itemtext')?.textContent || '').trim();
            if (text) items.push({ text, checked: !!(cb && cb.checked) });
        });
        if (items.length) groups.push({ title, items });
    });
    return {
        visaCode: root.getAttribute('data-visa-code') || '',
        statusCode: root.getAttribute('data-status-code') || '',
        variantLabel: root.getAttribute('data-variant-label') || '',
        procedureLabel: root.getAttribute('data-procedure-label') || '',
        sourcePages: root.getAttribute('data-source-pages') || '',
        groups
    };
}

function buildScenarioChecklistText(data) {
    const lines = [];
    lines.push(tx('scenarioChecklistTitle'));
    const headerBits = [data.visaCode, data.statusCode, data.procedureLabel, data.variantLabel].filter(Boolean);
    if (headerBits.length) lines.push(headerBits.join(' · '));
    lines.push('');
    data.groups.forEach(group => {
        if (group.title) lines.push('# ' + group.title);
        group.items.forEach(item => { lines.push((item.checked ? '[x] ' : '[ ] ') + item.text); });
        lines.push('');
    });
    if (data.sourcePages) lines.push(tx('scenarioChecklistSourceLabel') + ': ' + data.sourcePages);
    lines.push(tx('scenarioChecklistSafetyNote'));
    lines.push(tx('scenarioChecklistConfirmGuidance'));
    return lines.join('\n').replace(/\n{3,}/g, '\n\n').trim() + '\n';
}

function buildScenarioChecklistPrintHtml(data) {
    const headerBits = [data.visaCode, data.statusCode, data.procedureLabel, data.variantLabel].filter(Boolean).map(escapeHtml);
    const groups = data.groups.map(group => {
        const items = group.items.map(item => `<li>${item.checked ? '☑' : '☐'} ${escapeHtml(item.text)}</li>`).join('');
        return `<section class="scl-print-group"><h2>${escapeHtml(group.title)}</h2><ul>${items}</ul></section>`;
    }).join('');
    const source = data.sourcePages ? `<p class="scl-print-source">${escapeHtml(tx('scenarioChecklistSourceLabel'))}: ${escapeHtml(data.sourcePages)}</p>` : '';
    return `<div class="scl-print-doc">
        <h1>${escapeHtml(tx('scenarioChecklistTitle'))}</h1>
        ${headerBits.length ? `<p class="scl-print-meta">${headerBits.join(' · ')}</p>` : ''}
        ${groups}
        ${source}
        <p class="scl-print-note">${escapeHtml(tx('scenarioChecklistSafetyNote'))}</p>
        <p class="scl-print-note">${escapeHtml(tx('scenarioChecklistConfirmGuidance'))}</p>
    </div>`;
}

function setScenarioChecklistStatus(root, message, isError) {
    const el = root.querySelector('.scenario-checklist-status');
    if (!el) return;
    el.textContent = message;
    el.classList.toggle('is-error', !!isError);
    clearTimeout(el._scTimer);
    el._scTimer = setTimeout(() => { el.textContent = ''; el.classList.remove('is-error'); }, 4000);
}

async function scenarioChecklistCopyText(text) {
    try {
        if (navigator.clipboard && navigator.clipboard.writeText) {
            await navigator.clipboard.writeText(text);
            return true;
        }
    } catch (e) { /* fall through to legacy copy path */ }
    try {
        const ta = document.createElement('textarea');
        ta.value = text; ta.setAttribute('readonly', ''); ta.style.position = 'fixed'; ta.style.opacity = '0';
        document.body.appendChild(ta); ta.select();
        const ok = document.execCommand && document.execCommand('copy');
        document.body.removeChild(ta);
        return !!ok;
    } catch (e) { return false; }
}

async function copyScenarioChecklist(button) {
    const root = button.closest('[data-scenario-checklist]');
    if (!root) return;
    const text = buildScenarioChecklistText(collectScenarioChecklistData(root));
    const ok = await scenarioChecklistCopyText(text);
    setScenarioChecklistStatus(root, ok ? tx('scenarioChecklistCopied') : tx('scenarioChecklistCopyFailed'), !ok);
}

function printScenarioChecklist(button) {
    const root = button.closest('[data-scenario-checklist]');
    if (!root) return;
    const data = collectScenarioChecklistData(root);
    let host = document.getElementById('scenarioChecklistPrintHost');
    if (!host) { host = document.createElement('div'); host.id = 'scenarioChecklistPrintHost'; document.body.appendChild(host); }
    host.innerHTML = buildScenarioChecklistPrintHtml(data);
    document.body.classList.add('printing-scenario-checklist');
    const cleanup = () => {
        document.body.classList.remove('printing-scenario-checklist');
        host.innerHTML = '';
        window.removeEventListener('afterprint', cleanup);
    };
    window.addEventListener('afterprint', cleanup);
    try { window.print(); } catch (e) { cleanup(); return; }
    // Safari does not always fire afterprint; clean up defensively.
    setTimeout(cleanup, 2000);
}

function resetScenarioChecklist(button) {
    const root = button.closest('[data-scenario-checklist]');
    if (!root) return;
    const scope = scenarioChecklistScopePrefix(root.getAttribute('data-visa-code') || '', root.getAttribute('data-procedure-key') || '', root.getAttribute('data-variant-id') || '');
    try {
        const toRemove = Visable.state.keysWithPrefix(scope);
        toRemove.forEach(scenarioChecklistStoreRemove);
    } catch (e) { /* localStorage unavailable — visible boxes are still cleared below */ }
    root.querySelectorAll('input[type="checkbox"][data-scenario-checklist-item]').forEach(cb => {
        cb.checked = false;
        const key = cb.getAttribute('data-storage-key');
        scenarioChecklistStoreRemove(key);
        syncScenarioChecklistCheckboxes(key, false, cb);
    });
}

function renderProcedurePanel(v, proc, keywords, isActive) {
    const hasVariants = !!(proc.variants && proc.variants.length);
    const totalDocCount = countRenderableDocs(proc.docs);
    let docsHtml = renderProcedureDocGroups(proc.docs, keywords, v.code, proc.key);
    const variantsHtml = renderProcedureVariants(v, proc, keywords, proc.docs);
    // 사증발급 시나리오 안내(팝업)를 쓰는 자격(E-8·E-9·E-10 등)은 팝업이 서류의
    // 단일 출처가 되도록 상단 기본 서류 그리드·서류 수·요약·검토 안내를 생략합니다
    // (위/아래 중복 노출 방지). 팝업이 시나리오별 공통+추가서류와 절차를 직접
    // 표시하므로 이 자격에서는 사증발급 탭이 깔끔하게 팝업 하나로 정리됩니다.
    const issuanceRecordForPanel = proc.key === 'visaIssuance' ? getVisaIssuanceRecord(v.code) : null;
    const issuanceOwnsPanel = !!(issuanceRecordForPanel && issuanceRecordForPanel.scenarioGuide
        && Array.isArray(issuanceRecordForPanel.issuanceModes) && issuanceRecordForPanel.issuanceModes.length >= 2
        && !isGenericVisaIssuanceExcluded(v.code) && !isVisaIssuanceNotApplicable(v));
    if (issuanceOwnsPanel) docsHtml = '';
    const reviewFallback = `<div class="doc-group-empty">${escapeHtml(tx('docReviewFallback'))}</div>`;
    const eligibilityHtml = proc.eligibility.length ? renderLabeledManualBlock(tx('eligibilityLabel'), proc.eligibility, keywords) : '';
    const notesHtml = proc.notes.length
        ? `<details class="source-limitation-detail proc-notes-detail"><summary>${escapeHtml(tx('procNotesToggle') || '세부 안내')}</summary><div class="source-limitation-body">${renderManualDetailBlock(proc.notes.filter(Boolean).join('\n'), keywords)}</div></details>`
        : '';
    const summaryHtml = issuanceOwnsPanel ? '' : (renderProcedureSummaryBlock(proc.summary, keywords) || renderProcedureFallbackSummary(proc.key));
    const feeHtml = renderProcedureFeeBox(proc.feeInfo);
    const countHtml = (totalDocCount && !issuanceOwnsPanel) ? `<div class="procedure-doc-count">${escapeHtml(tx('documentCountLabel', { count: totalDocCount }))}</div>` : '';
    const officialDocumentNamesNote = currentLanguage === 'ko' || (!docsHtml && !variantsHtml) ? '' : `<p class="official-korean-terms-note">${escapeHtml(tx('officialDocumentNamesKoNote'))}</p>`;
    // The source-backed 사증발급 issuance detail lives inside the 사증발급 tab only,
    // so it no longer trails every procedure panel. The procedure doc grid above
    // (항상 확인할 서류) already lists the basic documents, so the embedded issuance
    // card must NOT reprint the same 항상 확인할/상황별 추가/해당 시 서류 list — that duplicate
    // "위/아래 두 번 노출" was confusing users. The card keeps its unique 신청
    // 경로·절차·주의사항·출처. When the panel has no doc grid of its own, the card
    // still carries the documents so nothing is lost. Scenario-guide panels let the
    // popup own the documents (suppressModeDocuments:false).
    const issuanceHtml = proc.key === 'visaIssuance'
        ? renderVisaIssuanceSection(v, keywords, { embedded: true, suppressModeDocuments: issuanceOwnsPanel ? false : !!docsHtml })
        : '';
    return `<div class="procedure-panel${isActive ? ' active' : ''}" data-procedure-panel="${proc.key}">
        ${renderProcedureHeader(v, proc)}
        ${eligibilityHtml}${summaryHtml}${notesHtml}
        ${feeHtml}
        ${countHtml}
        ${officialDocumentNamesNote}
        ${docsHtml ? `<div class="doc-group-grid">${docsHtml}</div>${renderDocGroupingSourceNote()}` : ''}
        ${variantsHtml || ((!docsHtml && !issuanceOwnsPanel) ? reviewFallback : '')}
        ${issuanceHtml}
    </div>`;
}

function renderProcedures(v, keywords) {
    const procedures = PROCEDURE_CONFIG.map(cfg => getProcedure(v, cfg)).filter(p => p.available);
    if (!procedures.length) {
        return `<section class="manual-section" aria-label="${escapeHtml(tx('procedureSectionTitle'))}">
            <h4 class="manual-section-title">${escapeHtml(tx('procedureSectionTitle'))}</h4>
            <div class="doc-group-empty">${escapeHtml(tx('docReviewFallback'))}</div>
        </section>`;
    }
    const firstActive = procedures.find(p => p.available) || procedures[0];
    const tabs = procedures.map(p => `<button type="button" class="procedure-tab${p.key === firstActive.key ? ' active' : ''}" data-action="select-procedure" data-procedure="${p.key}" data-testid="procedure-tab" data-procedure-key="${p.key}" ${p.available ? '' : 'disabled'}>${escapeHtml(getProcedureDisplayLabel(v, p))}</button>`).join('');
    const panels = procedures.map(p => renderProcedurePanel(v, p, keywords, p.key === firstActive.key)).join('');
    return `<div class="manual-section"><h4 class="manual-section-title">${escapeHtml(tx('procedureSectionTitle'))}</h4><div class="procedure-tabs" role="tablist">${tabs}</div>${panels}</div>`;
}

// Deterministic, key-based fallback descriptions for the most common
// procedure sections (사증발급/최초 신청, 외국인등록, 체류기간 연장) when a
// record has the section available but no source-backed summary text. These
// are generic preparation guidance only — they never invent required
// documents and never overwrite an existing richer/source-backed summary.
const PROCEDURE_FALLBACK_SUMMARY_KEYS = {
    visaIssuance: 'procFallbackInitial',
    registration: 'procFallbackRegistration',
    extension: 'procFallbackExtension'
};
function renderProcedureFallbackSummary(procedureKey) {
    const key = PROCEDURE_FALLBACK_SUMMARY_KEYS[procedureKey];
    if (!key) return '';
    return `<div class="procedure-summary procedure-summary-fallback">${escapeHtml(tx(key))}</div>`;
}

// ---- Route-aware intake wizard --------------------------------------------
// Route-complex statuses (F-4, F-6, G-1, F-2, D-10, H-2, E-7, D-4, F-1) have several practical user journeys.
// Rather than dumping one generic card, offer a compact, keyboard-accessible
// route chooser that highlights the most relevant procedure tab — and, where a
// route maps to a source-backed scenario variant, brings that variant forward —
// while showing a cautious route explanation. The wizard is fully data-driven
// via ROUTE_WIZARD_CONFIG keyed by status code, so a new status is added by
// config only (no one-off code). It NEVER hides procedures/variants, never
// exposes raw manualRefs/requiredDocs, and never implies eligibility/approval.
const ROUTE_WIZARD_CONFIG = {
    'F-4': {
        titleKey: 'f4RouteTitle', introKey: 'f4RouteIntro', ariaKey: 'f4RouteChooserAria',
        routes: [
            { id: 'f4-1', labelKey: 'f4Route1Label', descKey: 'f4Route1Desc', procedureKey: 'visaIssuance' },
            { id: 'f4-2', labelKey: 'f4Route2Label', descKey: 'f4Route2Desc', procedureKey: 'statusChange' },
            { id: 'f4-3', labelKey: 'f4Route3Label', descKey: 'f4Route3Desc', procedureKey: 'statusChange' },
            { id: 'f4-4', labelKey: 'f4Route4Label', descKey: 'f4Route4Desc', procedureKey: 'registration' },
            { id: 'f4-5', labelKey: 'f4Route5Label', descKey: 'f4Route5Desc', procedureKey: 'extension' }
        ]
    },
    'F-6': {
        titleKey: 'f6RouteTitle', introKey: 'f6RouteIntro', ariaKey: 'f6RouteChooserAria',
        routes: [
            { id: 'f6-1', labelKey: 'f6Route1Label', descKey: 'f6Route1Desc', procedureKey: 'extension', variantId: 'f-6-1-marriage-maintenance-extension' },
            { id: 'f6-2', labelKey: 'f6Route2Label', descKey: 'f6Route2Desc', procedureKey: 'statusChange', variantId: 'f-6-2-child-rearing-status-change' },
            { id: 'f6-3', labelKey: 'f6Route3Label', descKey: 'f6Route3Desc', procedureKey: 'statusChange', variantId: 'f-6-3-marriage-terminated-status-change' },
            { id: 'f6-4', labelKey: 'f6Route4Label', descKey: 'f6Route4Desc', procedureKey: 'extension' },
            { id: 'f6-5', labelKey: 'f6Route5Label', descKey: 'f6Route5Desc', procedureKey: 'extension' }
        ]
    },
    'G-1': {
        titleKey: 'g1RouteTitle', introKey: 'g1RouteIntro', ariaKey: 'g1RouteChooserAria',
        routes: [
            { id: 'g1-1', labelKey: 'g1Route1Label', descKey: 'g1Route1Desc', procedureKey: 'statusChange', variantId: 'g-1-5-6-refugee-humanitarian-status-change' },
            { id: 'g1-2', labelKey: 'g1Route2Label', descKey: 'g1Route2Desc', procedureKey: 'statusChange', variantId: 'g-1-5-6-refugee-humanitarian-status-change' },
            { id: 'g1-3', labelKey: 'g1Route3Label', descKey: 'g1Route3Desc', procedureKey: 'statusChange', variantId: 'g-1-3-litigation-status-change' },
            { id: 'g1-4', labelKey: 'g1Route4Label', descKey: 'g1Route4Desc', procedureKey: 'statusChange' },
            { id: 'g1-5', labelKey: 'g1Route5Label', descKey: 'g1Route5Desc', procedureKey: 'statusChange' },
            { id: 'g1-6', labelKey: 'g1Route6Label', descKey: 'g1Route6Desc', procedureKey: 'extension' }
        ]
    },
    'F-2': {
        titleKey: 'f2RouteTitle', introKey: 'f2RouteIntro', ariaKey: 'f2RouteChooserAria',
        routes: [
            { id: 'f2-1', labelKey: 'f2Route1Label', descKey: 'f2Route1Desc', procedureKey: 'statusChange', variantId: 'f-2-2-national-minor-child-status-change' },
            { id: 'f2-2', labelKey: 'f2Route2Label', descKey: 'f2Route2Desc', procedureKey: 'statusChange', variantId: 'f-2-permanent-resident-family-status-change' },
            { id: 'f2-3', labelKey: 'f2Route3Label', descKey: 'f2Route3Desc', procedureKey: 'statusChange', variantId: 'f-2-7-point-based-talent-status-change' },
            { id: 'f2-4', labelKey: 'f2Route4Label', descKey: 'f2Route4Desc', procedureKey: 'statusChange', variantId: 'f-2-7s-potential-talent-status-change' },
            { id: 'f2-5', labelKey: 'f2Route5Label', descKey: 'f2Route5Desc', procedureKey: 'statusChange', variantId: 'f-2-8-tourism-investment-status-change' },
            { id: 'f2-6', labelKey: 'f2Route6Label', descKey: 'f2Route6Desc', procedureKey: 'statusChange', variantId: 'f-2-12-13-14-public-interest-investment-status-change' },
            { id: 'f2-7', labelKey: 'f2Route7Label', descKey: 'f2Route7Desc', procedureKey: 'extension' }
        ]
    },
    'D-10': {
        titleKey: 'd10RouteTitle', introKey: 'd10RouteIntro', ariaKey: 'd10RouteChooserAria',
        routes: [
            { id: 'd10-1', labelKey: 'd10Route1Label', descKey: 'd10Route1Desc', procedureKey: 'statusChange', variantId: 'd-10-1-points-status-change' },
            { id: 'd10-2', labelKey: 'd10Route2Label', descKey: 'd10Route2Desc', procedureKey: 'statusChange', variantId: 'd-10-1-first-graduate-status-change' },
            { id: 'd10-3', labelKey: 'd10Route3Label', descKey: 'd10Route3Desc', procedureKey: 'statusChange', variantId: 'd-10-2-tech-startup-status-change' },
            { id: 'd10-4', labelKey: 'd10Route4Label', descKey: 'd10Route4Desc', procedureKey: 'statusChange', variantId: 'd-10-3-high-tech-intern-status-change' },
            { id: 'd10-5', labelKey: 'd10Route5Label', descKey: 'd10Route5Desc', procedureKey: 'extension', variantId: 'd-10-1-points-extension' },
            { id: 'd10-6', labelKey: 'd10Route6Label', descKey: 'd10Route6Desc', procedureKey: 'extension', variantId: 'd-10-2-tech-startup-extension' },
            { id: 'd10-7', labelKey: 'd10Route7Label', descKey: 'd10Route7Desc', procedureKey: 'extension', variantId: 'd-10-3-high-tech-intern-extension' }
        ]
    },
    'H-2': {
        titleKey: 'h2RouteTitle', introKey: 'h2RouteIntro', ariaKey: 'h2RouteChooserAria',
        routes: [
            { id: 'h2-1', labelKey: 'h2Route1Label', descKey: 'h2Route1Desc', procedureKey: 'registration', variantId: 'h-2-existing-holder-registration' },
            { id: 'h2-2', labelKey: 'h2Route2Label', descKey: 'h2Route2Desc', procedureKey: 'workplaceChange', variantId: 'h-2-employment-start-workplace-change-report' },
            { id: 'h2-3', labelKey: 'h2Route3Label', descKey: 'h2Route3Desc', procedureKey: 'extension' }
        ]
    },
    'E-7': {
        titleKey: 'e7RouteTitle', introKey: 'e7RouteIntro', ariaKey: 'e7RouteChooserAria',
        routes: [
            { id: 'e7-1', labelKey: 'e7Route1Label', descKey: 'e7Route1Desc', procedureKey: 'registration' },
            { id: 'e7-2', labelKey: 'e7Route2Label', descKey: 'e7Route2Desc', procedureKey: 'workplaceChange', variantId: 'e-7-registered-workplace-change' },
            { id: 'e7-3', labelKey: 'e7Route3Label', descKey: 'e7Route3Desc', procedureKey: 'extension' }
        ]
    },
    'D-4': {
        titleKey: 'd4RouteTitle', introKey: 'd4RouteIntro', ariaKey: 'd4RouteChooserAria',
        routes: [
            { id: 'd4-1', labelKey: 'd4Route1Label', descKey: 'd4Route1Desc', procedureKey: 'statusChange', variantId: 'd-4-1-7-language-training-status-change' },
            { id: 'd4-2', labelKey: 'd4Route2Label', descKey: 'd4Route2Desc', procedureKey: 'statusChange', variantId: 'd-4-2-graduate-training-status-change' },
            { id: 'd4-3', labelKey: 'd4Route3Label', descKey: 'd4Route3Desc', procedureKey: 'statusChange', variantId: 'd-4-3-school-student-status-change' },
            { id: 'd4-4', labelKey: 'd4Route4Label', descKey: 'd4Route4Desc', procedureKey: 'extension' }
        ]
    },
    'F-1': {
        titleKey: 'f1RouteTitle', introKey: 'f1RouteIntro', ariaKey: 'f1RouteChooserAria',
        routes: [
            { id: 'f1-1', labelKey: 'f1Route1Label', descKey: 'f1Route1Desc', procedureKey: 'statusChange', variantId: 'f-1-13-status-change' },
            { id: 'f1-2', labelKey: 'f1Route2Label', descKey: 'f1Route2Desc', procedureKey: 'statusChange', variantId: 'f-1-6-marriage-cleanup-status-change' },
            { id: 'f1-3', labelKey: 'f1Route3Label', descKey: 'f1Route3Desc', procedureKey: 'statusChange', variantId: 'f-1-nationality-procedure-status-change' },
            { id: 'f1-4', labelKey: 'f1Route4Label', descKey: 'f1Route4Desc', procedureKey: 'statusChange', variantId: 'f-1-16-refugee-family-status-change' },
            { id: 'f1-5', labelKey: 'f1Route5Label', descKey: 'f1Route5Desc', procedureKey: 'statusChange', variantId: 'f-1-52-prior-marriage-child-status-change' },
            { id: 'f1-6', labelKey: 'f1Route6Label', descKey: 'f1Route6Desc', procedureKey: 'statusGrant', variantId: 'f-1-employment-parent-born-child-status-grant' },
            { id: 'f1-7', labelKey: 'f1Route7Label', descKey: 'f1Route7Desc', procedureKey: 'statusGrant', variantId: 'f-1-refugee-born-child-status-grant' },
            { id: 'f1-8', labelKey: 'f1Route8Label', descKey: 'f1Route8Desc', procedureKey: 'extension' }
        ]
    }
};
function getRouteWizardConfig(v) {
    if (!v || typeof v.code !== 'string') return null;
    return ROUTE_WIZARD_CONFIG[v.code.toUpperCase()] || null;
}

export {
    renderProcedureVariant, closeScenarioPicker, openScenarioPicker, chooseScenarioVariant, clearScenarioSelection, applyScenarioSelection,
    renderProcedureVariants, hashScenarioChecklistItem, scenarioChecklistScopePrefix, scenarioChecklistItemStorageKey, scenarioChecklistStoreGet, scenarioChecklistStoreSet,
    scenarioChecklistStoreRemove, renderScenarioChecklist, persistScenarioChecklistItem, syncScenarioChecklistCheckboxes, hydrateScenarioChecklistState, collectScenarioChecklistData,
    buildScenarioChecklistText, buildScenarioChecklistPrintHtml, setScenarioChecklistStatus, scenarioChecklistCopyText, copyScenarioChecklist, printScenarioChecklist,
    resetScenarioChecklist, renderProcedurePanel, renderProcedures, renderProcedureFallbackSummary, getRouteWizardConfig, SCENARIO_CHECKLIST_STORAGE_PREFIX,
    SCENARIO_CHECKLIST_GROUPS, PROCEDURE_FALLBACK_SUMMARY_KEYS, ROUTE_WIZARD_CONFIG
};
