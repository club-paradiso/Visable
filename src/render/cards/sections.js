// @ts-nocheck
/**
 * Result-card sections of the legacy per-status card: the F-4 route wizard (C20), the source-confirmed requirements,
 * subcode groups, HiKorea guide, manual actions, next-action area and card summary (C22), and the visa-issuance
 * section with its scenario guide (C23). The three `let` picker/guide state variables are module-private (nothing
 * outside these clusters read them). Uses the inline globals tx(), txAt(), escapeHtml(), hl(), openModal(),
 * showToast(), VISA_DATA, PROCEDURE_CONFIG and the Visable.docs/Visable.cards stubs at call time only
 * (compatibility surface, ADR-009). assets/js/visa-route-guide.js guards `typeof openHikoreaGuide === 'function'`,
 * so that name keeps an inline stub. Covered by tests/golden/specs/legacy-card.spec.mjs; sliced by the legacy checks
 * that read scripts/frontend_modules.json.
 * Moved verbatim from index.html lines 17766-18649 (882 lines; kept inline: none).
 * Exposed on window.Visable.cards; 20 inline stubs with the same names delegate here.
 */
function isF4RouteWizardTarget(v) {
    return !!getRouteWizardConfig(v);
}
function renderF4RouteChooser(v) {
    const cfg = getRouteWizardConfig(v);
    if (!cfg) return '';
    // Statuses migrated to a dedicated full-screen ComplexStatusGuide entry get
    // their single recommended-start CTA from those modules instead of this
    // in-card route-picker, so suppress the legacy wizard for them to avoid
    // competing guide buttons. F-4 → assets/js/f4-route-guide.js; F-6/G-1/E-7/
    // F-5/D-2/D-4 → assets/js/complex-status-guide.js. Remaining configured
    // statuses keep the route wizard until migrated.
    const COMPLEX_GUIDE_MIGRATED = ['F-4', 'F-6', 'G-1', 'E-7', 'F-5', 'D-2', 'D-4'];
    if (typeof v.code === 'string' && COMPLEX_GUIDE_MIGRATED.indexOf(v.code.toUpperCase()) !== -1) return '';
    // Route selection happens in an in-screen popup (#routePickerOverlay). Nothing
    // is pre-selected: the trigger shows a neutral label and the explanation area
    // stays hidden until the user picks a route.
    return `<section class="f4-route-wizard manual-section" data-f4-route-wizard data-route-wizard-code="${escapeHtml(v.code)}" aria-label="${escapeHtml(tx(cfg.ariaKey))}">
        <h4 class="manual-section-title">${escapeHtml(tx(cfg.titleKey))}</h4>
        <p class="f4-route-intro">${escapeHtml(tx(cfg.introKey))}</p>
        <div class="f4-route-bar">
            <button type="button" class="f4-route-trigger" data-action="open-route-picker" aria-haspopup="dialog">
                <span class="f4-route-trigger-label">${escapeHtml(tx('routePickerTrigger'))}</span>
                <span class="f4-route-trigger-caret" aria-hidden="true">▾</span>
            </button>
            <button type="button" class="f4-route-showall" data-action="show-all-f4-routes" hidden>${escapeHtml(tx('routeShowAll'))}</button>
        </div>
        <div class="f4-route-explain" data-f4-route-explain role="status" aria-live="polite" hidden></div>
    </section>`;
}
function selectF4Route(btn) {
    // Back-compat shim: resolve the wizard/card from the clicked control and
    // delegate to the shared apply helper (the popup path uses chooseRoute).
    const wizard = btn.closest('[data-f4-route-wizard]');
    if (!wizard) return;
    applyRouteSelection(wizard, btn.closest('.manual-result'), {
        routeId: btn.dataset.routeId || '',
        procKey: btn.dataset.procedureKey,
        variantId: btn.dataset.variantId || '',
        labelKey: btn.dataset.labelKey,
        descKey: btn.dataset.descKey
    });
}
function applyRouteSelection(wizard, card, route) {
    if (!wizard) return;
    const { routeId, procKey, variantId, labelKey, descKey } = route;
    wizard.setAttribute('data-selected-route', routeId || '');
    const explain = wizard.querySelector('[data-f4-route-explain]');
    const tab = card ? card.querySelector(`.procedure-tab[data-procedure="${procKey}"]:not([disabled])`) : null;
    // Make the selected route obvious in text (not color alone): echo it in the
    // trigger label and a labelled banner above the cautious detail.
    const routeLabel = labelKey ? tx(labelKey) : '';
    const triggerLabel = wizard.querySelector('.f4-route-trigger-label');
    if (triggerLabel) triggerLabel.textContent = routeLabel ? `✓ ${routeLabel}` : tx('routePickerTrigger');
    let html = `<p class="f4-route-selected"><span class="f4-route-selected-prefix">${escapeHtml(tx('f4RouteSelectedPrefix'))}</span> <strong>${escapeHtml(routeLabel)}</strong></p>`;
    html += `<p class="f4-route-desc">${escapeHtml(descKey ? tx(descKey) : '')}</p>`;
    if (tab && card) {
        // De-emphasize (not hide) the other procedure tabs and activate the
        // route's procedure tab + panel, reusing the select-procedure model.
        card.querySelectorAll('.procedure-tab').forEach(t => {
            t.classList.toggle('active', t === tab);
            t.classList.toggle('is-route-muted', t !== tab);
        });
        card.querySelectorAll('.procedure-panel').forEach(p => p.classList.toggle('active', p.dataset.procedurePanel === procKey));
        // Route maps to a specific source-backed scenario variant → bring it
        // forward (revealing only that card) via the in-screen picker model.
        // Broad routes (no variantId) reset the picker to its empty state so a
        // previously selected subtype cannot leak stale checklist/AI context.
        const panel = card.querySelector(`.procedure-panel[data-procedure-panel="${procKey}"]`);
        const selector = panel ? panel.querySelector('[data-procedure-variant-selector].scenario-needs-pick') : null;
        if (selector) {
            // A broad route (no specific variantId) that lands on a procedure with
            // exactly one scenario auto-reveals it, so popup-gating single scenarios
            // doesn't leave the route showing an empty state. Multi-scenario broad
            // routes still reset to the empty picker so the user chooses.
            const variantCards = selector.querySelectorAll('[data-procedure-variant-card]');
            const autoId = (!variantId && variantCards.length === 1)
                ? (variantCards[0].dataset.procedureVariantCard || '')
                : '';
            applyScenarioSelection(selector, variantId || autoId);
        }
        html += `<p class="f4-route-source-note">${escapeHtml(tx('f4RouteSourceNote'))}</p>`;
    } else {
        // No source-backed procedure data for this route: explain it and send
        // the user to HiKorea / 1345 / competent office instead of guessing.
        html += `<p class="f4-route-source-note">${escapeHtml(tx('f4RouteNoDocsNote'))}</p>`;
    }
    if (explain) { explain.innerHTML = html; explain.hidden = false; }
    const showAll = wizard.querySelector('.f4-route-showall');
    if (showAll) showAll.hidden = false;
}
// --- In-screen route picker popup ----------------------------------------
// The route choices live in a modal dialog (#routePickerOverlay), built on
// demand from ROUTE_WIZARD_CONFIG for the originating wizard's status code.
let routePickerActiveWizard = null;
let routePickerActiveCard = null;

function openRoutePicker(trigger) {
    const wizard = trigger.closest('[data-f4-route-wizard]');
    if (!wizard) return;
    routePickerActiveWizard = wizard;
    routePickerActiveCard = trigger.closest('.manual-result');
    const code = wizard.getAttribute('data-route-wizard-code') || '';
    const v = (typeof VISA_DATA !== 'undefined') ? VISA_DATA.find(x => x.code === code) : null;
    const cfg = v ? getRouteWizardConfig(v) : null;
    const host = document.getElementById('routePickerChoices');
    if (!cfg || !host) return;
    const selectedId = wizard.getAttribute('data-selected-route') || '';
    host.innerHTML = cfg.routes.map((r, i) => {
        const label = tx(r.labelKey);
        const desc = r.descKey ? tx(r.descKey) : '';
        const pressed = r.id === selectedId ? 'true' : 'false';
        return `<button type="button" class="scenario-choice route-picker-choice" role="listitem" data-action="choose-route" data-route-id="${escapeHtml(r.id)}" data-procedure-key="${escapeHtml(r.procedureKey)}" data-variant-id="${escapeHtml(r.variantId || '')}" data-label-key="${escapeHtml(r.labelKey)}" data-desc-key="${escapeHtml(r.descKey)}" aria-pressed="${pressed}">
            <span class="scenario-choice-marker" aria-hidden="true"><span class="scenario-choice-num">${i + 1}</span></span>
            <span class="scenario-choice-body">
                <span class="scenario-choice-main"><span>${escapeHtml(label)}</span></span>
                ${desc ? `<span class="scenario-choice-preview">${escapeHtml(makeManualPreview(desc, 110))}</span>` : ''}
            </span>
            <span class="scenario-choice-go" aria-hidden="true">→</span>
        </button>`;
    }).join('');
    const heading = document.getElementById('routePickerTitle');
    if (heading) heading.textContent = tx(cfg.titleKey);
    const copy = document.getElementById('routePickerModalCopy');
    if (copy) copy.textContent = tx(cfg.introKey);
    openModal('routePickerOverlay');
}

function chooseRoute(button) {
    if (routePickerActiveWizard) {
        applyRouteSelection(routePickerActiveWizard, routePickerActiveCard, {
            routeId: button.dataset.routeId || '',
            procKey: button.dataset.procedureKey,
            variantId: button.dataset.variantId || '',
            labelKey: button.dataset.labelKey,
            descKey: button.dataset.descKey
        });
    }
    closeModal('routePickerOverlay');
    routePickerActiveWizard = null;
    routePickerActiveCard = null;
}
function resetF4Route(btn) {
    const wizard = btn.closest('[data-f4-route-wizard]');
    const card = btn.closest('.manual-result');
    if (!wizard) return;
    wizard.removeAttribute('data-selected-route');
    const triggerLabel = wizard.querySelector('.f4-route-trigger-label');
    if (triggerLabel) triggerLabel.textContent = tx('routePickerTrigger');
    const explain = wizard.querySelector('[data-f4-route-explain]');
    if (explain) { explain.innerHTML = ''; explain.hidden = true; }
    if (card) card.querySelectorAll('.procedure-tab').forEach(t => t.classList.remove('is-route-muted'));
    const showAll = wizard.querySelector('.f4-route-showall');
    if (showAll) showAll.hidden = true;
}


function renderSourceConfirmedRequirements(v) {
    // Renders ONLY source-confirmed (HIGH / STRUCTURED_EVIDENCE_READY) entries
    // supplied by the backend on the visa record. Candidate / needs-review
    // evidence is never present in this field, so there is nothing unverified
    // to hide here. Returns '' when the field is absent (most statuses).
    const entries = Array.isArray(v.sourceConfirmedStructuredRequirements)
        ? v.sourceConfirmedStructuredRequirements : [];
    if (!entries.length) return '';
    const en = currentLanguage === 'en';
    const zh = currentLanguage === 'zh-CN';
    const PROC_KO = {
        extension: '체류기간 연장', registration: '외국인등록', visa_issuance: '사증발급',
        change_of_status: '체류자격 변경', status_grant: '체류자격 부여',
        reentry: '재입국', workplace_change_or_addition: '근무처 변경·추가',
        activity_outside_status: '체류자격외 활동', reporting_duty: '신고 의무', other: ''
    };
    const PROC_EN = {
        extension: 'Extension of stay', registration: 'Foreigner registration', visa_issuance: 'Visa issuance',
        change_of_status: 'Change of status', status_grant: 'Grant of status',
        reentry: 'Re-entry', workplace_change_or_addition: 'Change/add workplace',
        activity_outside_status: 'Activities outside status', reporting_duty: 'Reporting duty', other: ''
    };
    const PROC_ZH = {
        extension: '居留期限延长', registration: '外国人登录', visa_issuance: '签证签发',
        change_of_status: '居留资格变更', status_grant: '居留资格赋予',
        reentry: '再入境', workplace_change_or_addition: '工作单位变更·追加',
        activity_outside_status: '居留资格外活动', reporting_duty: '申报义务', other: ''
    };
    const cards = entries.map(e => {
        const proc = (zh ? PROC_ZH[e.procedureType] : en ? PROC_EN[e.procedureType] : PROC_KO[e.procedureType]) || e.procedureType || '';
        const cov = Array.isArray(e.subCodesCovered) && e.subCodesCovered.length
            ? e.subCodesCovered.join(', ') : (e.subCode || '');
        const scope = cov ? ` <span class="manual-subcode-code">${escapeHtml(cov)}</span>` : '';
        const page = (e.pageStart && e.pageEnd && e.pageStart !== e.pageEnd)
            ? `pp. ${e.pageStart}-${e.pageEnd}` : (e.pageStart ? `p. ${e.pageStart}` : '');
        const src = e.source || {};
        const cite = [src.manualName, src.manualVersion, page].filter(Boolean).map(escapeHtml).join(' · ');
        const docs = Array.isArray(e.documents) ? e.documents : [];
        const docItems = docs.map(d => `<li>${escapeHtml(d.textKo || '')}</li>`).join('');
        return `<div class="manual-subcode-card">
            <div class="manual-subcode-top"><span class="manual-subcode-name">${escapeHtml(proc)}</span>${scope}</div>
            <div class="manual-subcode-desc">${escapeHtml(e.sectionTitle || '')}</div>
            ${docItems ? `<ul style="margin:0.5rem 0 0; padding-left:1.1rem; font-size:0.85rem; line-height:1.6;">${docItems}</ul>` : ''}
            <div class="manual-subcode-desc" style="margin-top:0.5rem; opacity:0.85;">${cite}</div>
        </div>`;
    }).join('');
    return `<div class="manual-section">
        <h4 class="manual-section-title">${zh ? '已核实出处的手册要件' : en ? 'Source-confirmed manual requirements' : '출처 확인된 매뉴얼 요건 (Source-confirmed manual requirements)'}</h4>
        <p class="manual-subcode-desc">${zh ? '已对照 2026.6 官方手册相关页面直接核实的项目。仅限于所显示的细分约号·程序范围。' : en ? 'Items verified directly against the relevant pages of the official 2026.6 manual. Limited to the sub-codes and procedure scope shown.' : '2026.6 공식 매뉴얼에서 해당 페이지를 직접 확인한 항목입니다. 표시된 세부약호·절차 범위에 한합니다.'}</p>
        <div class="manual-subcode-grid">${cards}</div>
    </div>`;
}

// Source/status chip for a subcode. Distinguishes official-confirmed vs.
// manual-review vs. auto-extracted vs. deprecated/inactive, per the source
// transparency requirement (never hide uncertainty).
function subcodeSourceChip(s) {
    const st = s.status || 'active';
    if (st !== 'active') return `<span class="subcode-chip chip-deprecated">${escapeHtml(tx('sourceChipDeprecated'))}</span>`;
    const conf = (Array.isArray(s.manualRefs) && s.manualRefs[0] && s.manualRefs[0].confidence) || '';
    if (s.needsManualReview === false) return `<span class="subcode-chip chip-official">${escapeHtml(tx('sourceChipOfficial'))}</span>`;
    if (/auto/i.test(conf)) return `<span class="subcode-chip chip-auto">${escapeHtml(tx('sourceChipAuto'))}</span>`;
    return `<span class="subcode-chip chip-review">${escapeHtml(tx('sourceChipReview'))}</span>`;
}

/* ---- Generic parent/subcode grouping helpers (search-result density) -------
   Broad parent-code searches (C-3, B-2, F-2, F-6, D-2, D-10, E-7, G-1, F-4 …)
   must not flood the card with every subcode as a full card. These helpers are
   data-driven and generic — nothing is hardcoded per status. */
function getParentVisaCode(code) {
    const norm = String(code || '').trim().toUpperCase();
    const m = /^([A-Z]+-\d+)(?:-.+)?$/.exec(norm);
    return m ? m[1] : norm;
}
function isSubcodeOf(parentCode, childCode) {
    const p = normalizeVisaCode(parentCode), c = normalizeVisaCode(childCode);
    return !!p && !!c && p !== c && normalizeVisaCode(getParentVisaCode(childCode)) === p;
}
function groupSearchResultsByParent(results) {
    const groups = new Map();
    (results || []).forEach(r => {
        const parent = getParentVisaCode(r && r.code);
        if (!groups.has(parent)) groups.set(parent, []);
        groups.get(parent).push(r);
    });
    return groups;
}
function shouldAutoExpandSubcodeGroup(query, group) {
    const qNorm = normalizeVisaCode(query);
    if (!qNorm) return false;
    return (group || []).some(s => normalizeVisaCode(s && s.code) === qNorm);
}
function renderSubcodePreview(group, query, parentCode) {
    const active = (group || []).filter(s => !s.status || s.status === 'active');
    const preview = (active.length ? active : group).slice(0, 4);
    if (!preview.length) return '';
    const chips = preview.map(s =>
        `<button type="button" class="subcode-preview-chip" role="listitem" data-action="open-subcode-detail" data-parent="${escapeHtml(parentCode || getParentVisaCode(s.code))}" data-subcode="${escapeHtml(s.code)}" aria-label="${escapeHtml(tx('subcodeModalOpenAria', { code: s.code }))}"><span class="subcode-preview-code">${hl(s.code, query ? [query] : [])}</span><span class="subcode-preview-name">${escapeHtml(getLocalizedSubcodeName(s))}</span></button>`
    ).join('');
    return `<div class="subcode-preview-chips" role="list" aria-label="${escapeHtml(tx('subcodePreviewAria'))}">${chips}</div>`;
}
function renderExpandableSubcodeGroup(v, group, innerHtml, query, idSuffix) {
    const groupId = `subgroup-${normalizeVisaCode(v.code)}${idSuffix ? `-${idSuffix}` : ''}`;
    const expanded = shouldAutoExpandSubcodeGroup(query, group);
    return `<div class="subcode-expand-wrap">
        <button type="button" class="subcode-expand-btn" data-action="toggle-subcode-group" aria-expanded="${expanded ? 'true' : 'false'}" aria-controls="${groupId}">
            <span class="subcode-expand-show">${escapeHtml(tx('subcodeGroupShowCount', { count: group.length }))}</span>
            <span class="subcode-expand-hide">${escapeHtml(tx('subcodeGroupHide'))}</span>
            <span class="subcode-expand-caret" aria-hidden="true">▾</span>
        </button>
        <div id="${groupId}" class="subcode-expand-body" ${expanded ? '' : 'hidden'}>${innerHtml}</div>
    </div>`;
}

function renderSubcodes(v, keywords, matchingSubcodes, opts) {
    const subs = getVisaSubcodes(v);
    if (!subs.length) return '';
    opts = opts || {};
    const en = currentLanguage === 'en';
    const zh = currentLanguage === 'zh-CN';
    const matchSet = new Set((matchingSubcodes || []).map(s => s.code));
    const visaCode = v.code || '';
    const cardId = (s) => `subcode-${normalizeVisaCode(visaCode)}-${normalizeVisaCode(s.code)}`;

    const renderCard = (s) => {
        const label = paradisoStripInternalReviewArtifacts(s.nameKo || s.name || '');
        const cleanSummary = stripManualArtifacts(s.summary);
        const cleanNote = stripManualArtifacts(s.note);
        const desc = cleanSummary || (Array.isArray(s.eligibility) && s.eligibility[0]) || cleanNote || s.addReq || tx('manualNeedsReview');
        const inactive = s.status && s.status !== 'active';
        const cleanStatusNote = paradisoStripInternalReviewArtifacts(s.statusNote);
        const statusNote = inactive && cleanStatusNote ? `<div class="manual-subcode-status">${escapeHtml(cleanStatusNote)}</div>` : '';
        const matchBadge = matchSet.has(s.code) ? `<span class="subcode-match-badge" aria-label="${zh ? '可能与您情况相关的细分代码' : en ? 'Sub-code possibly relevant to your situation' : '내 상황과 관련 가능성 있는 세부코드'}">${zh ? '可能相关' : en ? 'May apply' : '관련 가능'}</span>` : '';
        return `<div id="${cardId(s)}" class="manual-subcode-card manual-subcode-card--interactive${matchSet.has(s.code) ? ' match' : ''}${inactive ? ' is-inactive' : ''}" role="button" tabindex="0" data-action="open-subcode-detail" data-parent="${escapeHtml(visaCode)}" data-subcode="${escapeHtml(s.code)}" aria-label="${escapeHtml(tx('subcodeModalOpenAria', { code: s.code }))}">
            <div class="manual-subcode-top"><span class="manual-subcode-code">${hl(s.code, keywords)}</span><span class="manual-subcode-name">${hl(label, keywords)}</span>${subcodeSourceChip(s)}${matchBadge}<span class="manual-subcode-go" aria-hidden="true">›</span></div>
            <div class="manual-subcode-desc">${hl(desc, keywords)}</div>${statusNote}
        </div>`;
    };

    // Category-grouped HTML for an arbitrary subset (group order follows first
    // appearance in the FULL list so lifting cards out never reshuffles it).
    const buildGroupedHtml = (list) => {
        const gm = new Map();
        subs.forEach(s => { const g = s.group || '기타'; if (!gm.has(g)) gm.set(g, []); });
        list.forEach(s => gm.get(s.group || '기타').push(s));
        const hasG = list.some(s => s.group);
        return [...gm.keys()].filter(g => gm.get(g).length).map(g => {
            const cards = gm.get(g).map(renderCard).join('');
            const groupTitle = hasG ? `<div class="manual-subcode-group-title">${escapeHtml(g)}</div>` : '';
            return `<div class="manual-subcode-group">${groupTitle}<div class="manual-subcode-grid">${cards}</div></div>`;
        }).join('');
    };

    // Retired/inactive sub-codes (status !== active) collapse into ONE compact
    // chip cluster with a single shared note, instead of repeating the same
    // boilerplate card per code. Each chip still opens the per-code detail modal
    // (which keeps the full uncertainty notice), so nothing is hidden — only
    // de-cluttered. Active codes stay as full cards.
    const splitByActivity = (list) => ({
        active: list.filter(s => !s.status || s.status === 'active'),
        inactive: list.filter(s => s.status && s.status !== 'active')
    });
    const renderInactiveCluster = (list) => {
        if (!list.length) return '';
        const chips = list.map(s => {
            const rawLabel = paradisoStripInternalReviewArtifacts(s.nameKo || s.name || '');
            const meaningful = rawLabel && !/매뉴얼\s*참조\s*코드|manual\s*review\s*code/i.test(rawLabel);
            const nameHtml = meaningful ? `<span class="subcode-mini-name">${hl(rawLabel, keywords)}</span>` : '';
            return `<button type="button" class="subcode-mini-chip${matchSet.has(s.code) ? ' match' : ''}" data-action="open-subcode-detail" data-parent="${escapeHtml(visaCode)}" data-subcode="${escapeHtml(s.code)}" aria-label="${escapeHtml(tx('subcodeModalOpenAria', { code: s.code }))}"><span class="subcode-mini-code">${hl(s.code, keywords)}</span>${nameHtml}</button>`;
        }).join('');
        const heading = zh ? `已废止·非活跃细分代码 ${list.length}个` : en ? `Retired / inactive sub-codes (${list.length})` : `폐지·비활성 세부코드 ${list.length}개`;
        const note = zh ? '出现在手册提取本中，但尚未核实为活跃细分代码。点击任一代码可查看其详情与注意事项。'
            : en ? 'Present in the manual extract but not yet verified as active sub-codes. Tap any code for its detail and cautions.'
            : '매뉴얼 추출본에는 있으나 아직 활성 세부코드로 검증되지 않았습니다. 각 코드를 누르면 상세·주의사항을 확인할 수 있습니다.';
        const groupId = `subinactive-${normalizeVisaCode(visaCode)}`;
        return `<div class="subcode-inactive-cluster">
            <button type="button" class="subcode-inactive-toggle" data-action="toggle-subcode-group" aria-expanded="false" aria-controls="${groupId}">
                <span class="subcode-inactive-caret" aria-hidden="true">▾</span><span>${escapeHtml(heading)}</span>
            </button>
            <div id="${groupId}" class="subcode-inactive-body" hidden>
                <p class="subcode-inactive-note">${escapeHtml(note)}</p>
                <div class="subcode-mini-grid">${chips}</div>
            </div>
        </div>`;
    };

    const title = `<h4 class="manual-section-title">${escapeHtml(tx('subcodesTitle'))}</h4>`;

    // A) Broad parent-code query (e.g. "C-3" on the C-3 card): parent-first.
    //    Compact one-line summary + 3–4 preview chips + a keyboard-accessible
    //    expand/collapse group instead of a wall of full subcode cards.
    if (opts.broadParentQuery && subs.length > 5) {
        const activeSubs = subs.filter(s => !s.status || s.status === 'active');
        const summarySubs = activeSubs.length ? activeSubs : subs;
        const summaryNames = summarySubs
            .map(s => getLocalizedSubcodeName(s))
            .filter(name => name && !/매뉴얼\s*참조\s*코드|manual\s*review\s*code/i.test(name));
        const names = summaryNames.slice(0, 4).join(', ')
            || summarySubs.slice(0, 4).map(s => s.code).filter(Boolean).join(', ');
        // Count + expandable group cover the ACTIVE sub-codes (the meaningful set);
        // deprecated placeholders move to the compact cluster below so the summary,
        // the preview chips, and the expand toggle all line up on the same number.
        const inactiveSubs = subs.filter(s => s.status && s.status !== 'active');
        const groupSubs = activeSubs.length ? activeSubs : subs;
        const summary = `<p class="subcode-group-summary">${escapeHtml(tx('subcodeGroupSummary', { count: groupSubs.length, names }))}</p>`;
        const hint = `<p class="subcode-group-hint">${escapeHtml(tx('subcodeGroupHint', { example: (activeSubs[0] && activeSubs[0].code) || `${visaCode}-1` }))}</p>`;
        const inactiveCluster = activeSubs.length ? renderInactiveCluster(inactiveSubs) : '';
        return `<div class="manual-section" data-subcode-section="broad">${title}${summary}${renderSubcodePreview(subs, opts.queryCode, v.code)}${renderExpandableSubcodeGroup(v, groupSubs, buildGroupedHtml(groupSubs), opts.queryCode)}${inactiveCluster}${hint}</div>`;
    }

    // B) Matched subcodes are lifted into their own labeled group up top
    //    (original code order preserved). PR-K1 #8: the matched group and the
    //    remainder both default to the accessible collapse toggle so keyword
    //    searches never open with walls of full subcode cards. Exact subcode
    //    searches stay prominent via shouldAutoExpandSubcodeGroup().
    const matched = subs.filter(s => matchSet.has(s.code));
    const rest = matched.length ? subs.filter(s => !matchSet.has(s.code)) : subs;
    let matchedHtml = '';
    if (matched.length) {
        matchedHtml = `<div class="manual-subcode-group"><div class="manual-subcode-group-title">${zh ? '与您情况相关' : en ? 'Related to your situation' : '내 상황과 관련'}</div>${renderExpandableSubcodeGroup(v, matched, `<div class="manual-subcode-grid">${matched.map(renderCard).join('')}</div>`, opts.queryCode, 'match')}</div>`;
        if (rest.length) matchedHtml += `<hr class="subcode-match-divider"><div class="manual-subcode-group-title">${zh ? '全部细分代码' : en ? 'All sub-codes' : '전체 세부코드'}</div>`;
    }
    // Active rest → full grouped cards; inactive rest → compact chip cluster.
    const { active: restActive, inactive: restInactive } = splitByActivity(rest);
    const restGroup = restActive.length ? restActive : rest;
    const restHtml = restGroup.length
        ? renderExpandableSubcodeGroup(v, restGroup, buildGroupedHtml(restGroup), opts.queryCode)
        : '';
    const restInactiveHtml = restActive.length ? renderInactiveCluster(restInactive) : '';
    return `<div class="manual-section" data-subcode-section>${title}${matchedHtml}${restHtml}${restInactiveHtml}</div>`;
}

/* Result / Status Card `MatchReason=ParentOfExactCode` — Figma UX-03 (node
   405:66). When the query names a sub-code but this card is its PARENT, every
   requirement rendered below belongs to the parent, not to the sub-code the
   user actually asked about. Saying so is a CLAUDE.md non-negotiable: a parent
   record must never read as though it carried the sub-code's specific rules.

   The notice appears only when the sub-code resolves against visa_data.json.
   A code-shaped token we do not have ("D-2-99") is never named back as if it
   were real. */
function renderParentScopeNotice(v, primaryCodeQuery) {
    const query = normalizeVisaCode(primaryCodeQuery || '');
    const parent = normalizeVisaCode(v.code || '');
    if (!query || !parent || query === parent) return '';
    const segments = query.split('-');
    if (segments.length < 3) return '';
    if (`${segments[0]}-${segments[1]}` !== parent) return '';
    const sub = getVisaSubcodes(v).find(s => normalizeVisaCode(s.code) === query);
    if (!sub) return '';

    const en = currentLanguage === 'en';
    const zh = currentLanguage === 'zh-CN';
    const label = zh ? '输入的细分代码的上级'
        : en ? 'Parent of the code you entered'
        : '입력한 세부코드의 상위';
    const body = zh
        ? `此处列出的是 ${parent} 的共同要件。${query} 的专属要件请在下方细分代码中确认。`
        : en
        ? `The requirements shown here are common to ${parent}. Requirements specific to ${query} are in the sub-code section below.`
        : `여기에 적힌 요건은 ${parent} 공통 요건이에요. ${query} 전용 요건은 아래 세부코드에서 확인하세요.`;

    return `<div class="parent-scope-notice" data-parent-scope="${escapeHtml(parent)}" data-sub-scope="${escapeHtml(query)}"><span class="parent-scope-badge">${escapeHtml(label)}</span><p class="parent-scope-body">${escapeHtml(body)}</p></div>`;
}

function renderCommonWarnings(v) {
    const warnings = Array.isArray(v.commonWarnings) && v.commonWarnings.length ? v.commonWarnings : COMMON_MANUAL_WARNINGS;
    return `<div class="manual-warning-box"><strong>${escapeHtml(tx('commonWarningsTitle'))}</strong><ul>${warnings.map(w => `<li>${escapeHtml(w)}</li>`).join('')}</ul></div>`;
}

function renderSourceReferences(v) {
    const refs = Array.isArray(v.manualRefs) ? [...v.manualRefs] : [];
    const status = v.sourceManualStatus || {};
    if (!refs.length) {
        if (getManualDomains(v).includes('visa_issuance')) refs.push({ manualName: txAt('domainLabels', 1, '사증발급'), manualVersion: status.visaManualVersion || '2026.9', pageRange: tx('manualNeedsReview'), confidence: 'needs_review' });
        if (getManualDomains(v).includes('stay_sojourn')) refs.push({ manualName: txAt('domainLabels', 2, '체류민원'), manualVersion: status.stayManualVersion || '2026.9', pageRange: tx('manualNeedsReview'), confidence: 'needs_review' });
    }
    const refItems = refs.map(ref => {
        const sourceDate = ref.sourceDate || ref.sourceRevisionDate || ref.revisionDate || '';
        const versionLabel = sourceDate ? `${ref.manualVersion || ref.version || '2026.9'} (${sourceDate})` : (ref.manualVersion || ref.version || '2026.9');
        const bits = [ref.manualName || ref.manual || tx('sourceManualFallback'), versionLabel, ref.pageRange || tx('pageNeedsReview'), ref.confidence ? `${tx('confidenceLabel')}: ${ref.confidence}` : `${tx('confidenceLabel')}: ${tx('confidenceNeedsReview')}`];
        return `<li>${bits.map(escapeHtml).join(' · ')}</li>`;
    }).join('');
    const reviewText = status.needsManualReview === false ? tx('sourceReviewDone') : tx('sourceReviewPending');
    return `<div class="manual-source-box"><div class="manual-source-title">${escapeHtml(tx('sourceTitleResult'))}</div><ul>${refItems}</ul><div style="margin-top:0.55rem;">${escapeHtml(reviewText)} ${escapeHtml(tx('sourceLegalNote'))}</div></div>`;
}

/* The HiKorea reservation guide was redesigned into the friendly, mobile-first
   "하이코리아 예약 도우미 / HiKorea Reservation Helper". The flow + deterministic
   logic now live in the standalone module assets/js/hikorea-reservation-helper.js
   (window.ParadisoReservationHelper). index.html keeps only these thin shims: it
   owns the modal shell (reusing openModal/closeModal focus-trap + Escape + focus
   restore), the module owns the content + logic. */
function openHikoreaGuide(vcode) {
    if (window.ParadisoReservationHelper && typeof window.ParadisoReservationHelper.open === 'function') {
        const v = (typeof VISA_DATA !== 'undefined' && Array.isArray(VISA_DATA)) ? (VISA_DATA.find(x => x.code === vcode) || {}) : {};
        window.ParadisoReservationHelper.open({ visaCode: vcode || '', taskType: v.hikorea_task_type || '' });
    }
    openModal('hikoreaGuideOverlay');
}
function renderHikoreaGuide() {
    if (window.ParadisoReservationHelper && typeof window.ParadisoReservationHelper.render === 'function') {
        window.ParadisoReservationHelper.render();
    }
}

function renderManualActions(v, isVisaCode) {
    if (!isVisaCode) return '';
    return `<div class="manual-actions">
        <button type="button" class="doc-trigger-btn" data-action="open-doc-modal" data-vcode="${escapeHtml(v.code)}" data-type="new"><span>${escapeHtml(txAt('manualActionLabels', 0, '사증/신규 서류'))}</span></button>
        <button type="button" class="doc-trigger-btn" data-action="open-doc-modal" data-vcode="${escapeHtml(v.code)}" data-type="ext"><span>${escapeHtml(txAt('manualActionLabels', 1, '연장 서류'))}</span></button>
        <button type="button" class="doc-trigger-btn" data-action="open-doc-modal" data-vcode="${escapeHtml(v.code)}" data-type="change"><span>${escapeHtml(txAt('manualActionLabels', 2, '변경 서류'))}</span></button>
        ${v.faq ? `<button type="button" class="doc-trigger-btn" data-action="open-faq-modal" data-vcode="${escapeHtml(v.code)}"><span>FAQ</span></button>` : ''}
        <button type="button" class="doc-trigger-btn" data-action="copy-visa-result" data-vcode="${escapeHtml(v.code)}"><span>${escapeHtml(tx('actionCopyResult'))}</span></button>
    </div>`;
}

function renderNextActionArea(v, isVisaCode) {
    if (!isVisaCode) return '';
    return `<section class="next-action-panel" aria-label="${escapeHtml(tx('nextActionTitle'))}">
        <h4 class="next-action-title">${escapeHtml(tx('nextActionTitle'))}</h4>
        <div class="next-action-grid">
            <button type="button" class="next-action-btn primary hikorea-guide-btn" data-action="open-hikorea-guide" data-vcode="${escapeHtml(v.code)}">
                <span class="next-action-kicker">${escapeHtml(tx('nextActionHikoreaKicker'))}</span>
                <strong>${escapeHtml(tx('nextActionHikoreaTitle'))}</strong>
                <small>${escapeHtml(tx('nextActionHikoreaDesc'))}</small>
            </button>
            <button type="button" class="next-action-btn" data-action="open-doc-modal" data-vcode="${escapeHtml(v.code)}" data-type="new">
                <span class="next-action-kicker">${escapeHtml(tx('nextActionDocsKicker'))}</span>
                <strong>${escapeHtml(tx('nextActionDocsTitle'))}</strong>
                <small>${escapeHtml(tx('nextActionDocsDesc'))}</small>
            </button>
            <button type="button" class="next-action-btn" data-action="open-ai-modal" data-visa-code="${escapeHtml(v.code)}">
                <span class="next-action-kicker">${escapeHtml(tx('nextActionAiKicker'))}</span>
                <strong>${escapeHtml(tx('actionAi'))}</strong>
                <small>${escapeHtml(tx('nextActionAiDesc'))}</small>
            </button>
        </div>
    </section>`;
}

function renderCardSummary(v, kw) {
    if (['faq', 'scn', 'nhis'].includes(v.cat)) return '';
    const raw = v.summary || '';
    if (!raw) return '';
    const normalized = normalizeManualText(raw);
    if (!normalized) return '';
    const sentences = paradisoSplitSentences(normalized);
    if (sentences.length <= 2) {
        return `<div class="vc-summary">${hl(normalized, kw)}</div>`;
    }
    const preview = sentences.slice(0, 2).join(' ');
    const rest = sentences.slice(2).join(' ');
    return `<div class="vc-summary"><span class="vc-summary-preview">${hl(preview, kw)}</span><details class="vc-summary-detail"><summary>${escapeHtml(tx('manualDetailToggle') || '더 보기')}</summary><span class="vc-summary-rest">${hl(rest, kw)}</span></details></div>`;
}

function getVisaIssuanceRecord(code) {
    return VISA_ISSUANCE_BY_CODE.get(normalizeVisaCode(code)) || null;
}

function getVisaIssuanceBinding(code) {
    return getProcedureEvidenceBinding(code, 'visaIssuance');
}

function getVisaIssuanceOverlays(code) {
    const codeNorm = normalizeVisaCode(code);
    return OFFICIAL_WEB_OVERLAYS.filter(record => {
        if (normalizeVisaCode(record.code) === codeNorm) return true;
        return Array.isArray(record.coveredCodes) && record.coveredCodes.some(item => normalizeVisaCode(item) === codeNorm);
    });
}

/* Locale-chain text picker for {ko, en, ...} objects coming from data files.
   Resolution order: active locale → manifest fallback → ko → en (no inline
   per-language branching at call sites). */
function pickLocalizedManualText(item) {
    if (!item || typeof item !== 'object') return '';
    const chain = [normalizeLocaleCode(currentLanguage), I18N_MANIFEST.fallbackLocale || 'ko', 'ko', 'en'];
    for (const key of chain) {
        const value = item[key];
        if (typeof value === 'string' && value.trim()) return value;
    }
    return '';
}

function renderIssuanceDocList(items, keywords) {
    if (!Array.isArray(items) || !items.length) return '';
    return `<ul class="issuance-doc-list">${items.map(item => {
        const label = String(item || '');
        return `<li><span>${hl(escapeHtml(label), keywords || [])}</span>${renderDocumentHelpButton(label, label)}</li>`;
    }).join('')}</ul>`;
}

function renderIssuanceDocGroups(documents, keywords) {
    const docs = documents || {};
    const groups = [
        { key: 'common', cls: 'group-basic', label: txAt('issuanceUiLabels', 1, '항상 확인할 서류') },
        { key: 'additional', cls: 'group-situational', label: txAt('issuanceUiLabels', 2, '상황별 추가 서류') },
        { key: 'conditional', cls: 'group-conditional', label: txAt('issuanceUiLabels', 3, '해당 시 서류') }
    ].map(group => {
        const listHtml = renderIssuanceDocList(docs[group.key], keywords);
        if (!listHtml) return '';
        // Reuse the shared procedure document-group vocabulary so the issuance
        // doc checklist looks identical to the other 절차별 안내 doc groups.
        return `<div class="doc-group ${group.cls}"><h5 class="doc-group-title">${escapeHtml(group.label)}</h5>${listHtml}</div>`;
    }).filter(Boolean).join('');
    if (!groups) return '';
    return `<div class="doc-group-grid">${groups}</div>`;
}

function renderIssuanceSteps(steps, keywords) {
    if (!Array.isArray(steps) || !steps.length) return '';
    return `<ol class="issuance-steps">${steps.map(step => {
        const text = pickLocalizedManualText(step);
        return `<li>${hl(escapeHtml(text), keywords || [])}</li>`;
    }).join('')}</ol>`;
}

function renderIssuanceWarnings(warnings, keywords) {
    if (!Array.isArray(warnings) || !warnings.length) return '';
    return `<div class="issuance-warnings"><h6 class="issuance-subtitle">${escapeHtml(txAt('issuanceUiLabels', 5, '주의사항'))}</h6><ul class="issuance-warning-list">${warnings.map(w => `<li>${hl(escapeHtml(w), keywords || [])}</li>`).join('')}</ul></div>`;
}

function renderIssuanceOverlaySelector(code) {
    const overlays = getVisaIssuanceOverlays(code);
    if (!overlays.length) return '';
    const isEnglish = normalizeLocaleCode(currentLanguage) === 'en';
    const title = isEnglish ? 'Official mission-specific application guidance' : '재외공관별 공식 접수 안내';
    const caution = isEnglish
        ? OFFICIAL_WEB_OVERLAY_POLICY.consularCautionEn
        : OFFICIAL_WEB_OVERLAY_POLICY.consularCautionKo;
    const list = overlays.map(record => {
        const sourceTitle = [record.country, record.post, record.sourceTitle].filter(Boolean).join(' · ');
        const scope = isEnglish ? record.localOnlySummaryEn : record.localOnlySummaryKo;
        const appointment = isEnglish ? record.appointmentMethodEn : record.appointmentMethodKo;
        const date = record.lastUpdated || record.sourceDate || '';
        const dateLabel = date ? `${isEnglish ? 'Source date' : '자료일'} ${date}` : `${isEnglish ? 'No visible source date' : '공개된 자료일 없음'}`;
        const accessed = record.accessedAt ? ` · ${isEnglish ? 'Accessed' : '확인일'} ${record.accessedAt}` : '';
        return `<li class="issuance-mission-item">
            <a class="issuance-mission-link" href="${escapeHtml(record.sourceUrl)}" target="_blank" rel="noopener noreferrer">${escapeHtml(sourceTitle)}</a>
            ${scope ? `<p class="issuance-mission-scope">${escapeHtml(scope)}</p>` : ''}
            ${appointment ? `<p class="issuance-mission-scope">${escapeHtml(appointment)}</p>` : ''}
            <p class="issuance-mission-meta">${escapeHtml(dateLabel + accessed)} · ${isEnglish ? 'Mission-specific only' : '해당 공관 범위만 적용'}</p>
        </li>`;
    }).join('');
    return `<details class="issuance-mission-sources">
        <summary>${escapeHtml(title)} (${overlays.length})</summary>
        <ul class="issuance-mission-list">${list}</ul>
        ${caution ? `<p class="issuance-mission-caution">${escapeHtml(caution)}</p>` : ''}
    </details>`;
}

// F-4 (재외동포) is intentionally excluded from the generic 사증발급 issuance
// renderer. F-4 keeps its dedicated diaspora route guide (assets/js/f4-route-guide.js
// + data/f4/routes.json) and the in-page route chooser. This stays an explicit,
// auditable exclusion set so a future refactor cannot silently re-absorb F-4 into
// the generic issuance UI. The protected data record is left intact; the guard is
// in code only (see scripts/check_f4_route_guide.mjs for the regression assertion).
const GENERIC_VISA_ISSUANCE_EXCLUDED_CODES = new Set(['F-4']);
function isGenericVisaIssuanceExcluded(code) {
    return GENERIC_VISA_ISSUANCE_EXCLUDED_CODES.has(normalizeVisaCode(code));
}

// 사증발급(비자 발급)이 적용되지 않는 체류자격은 '사증발급' 절차 탭과 별도
// 섹션을 모두 노출하지 않습니다. 거의 모든 레코드가 레거시 newReq 텍스트를
// 가지고 있어 legacyAvailable 만으로는 사증발급 탭이 무조건 켜지므로(사증면제·
// 비대상 자격에도 '사증발급'이 떴던 원인), 보호 데이터
// data/visa_issuance_records.json 의 issuanceModes.type 으로 적용 여부를
// 판정합니다:
//   - visa_exempt    : 사증면제 입국 (예: B-1 사증면제, B-2 관광·통과)
//   - not_applicable : 사증발급 비대상 (예: H-2 방문취업 — 사증발급 절차 없음)
// 또한 영주(F-5)는 재외공관에서 '영주 사증'을 받는 자격이 아니라 국내 체류자격
// 변경으로 취득하므로(remapPermanentResidenceAcquisition 주석 참조) 동일하게
// 사증발급 절차를 숨깁니다. 렌더러 전용 판정 — 보호 데이터는 변경하지 않습니다.
const VISA_ISSUANCE_NOT_APPLICABLE_MODE_TYPES = new Set(['visa_exempt', 'not_applicable']);
const VISA_ISSUANCE_NOT_APPLICABLE_CODES = new Set(['F-5']);
function isVisaIssuanceNotApplicable(v) {
    if (!v) return false;
    if (VISA_ISSUANCE_NOT_APPLICABLE_CODES.has(normalizeVisaCode(v.code))) return true;
    const record = getVisaIssuanceRecord(v.code);
    const modes = record && Array.isArray(record.issuanceModes) ? record.issuanceModes : [];
    if (!modes.length) return false;
    // 실제 신청 경로(mixed·consular_discretion·인정서 등)가 하나라도 있으면 그대로
    // 노출하고, 모든 경로가 사증면제/비대상일 때에만 사증발급을 숨깁니다.
    return modes.every(mode => mode && VISA_ISSUANCE_NOT_APPLICABLE_MODE_TYPES.has(mode.type));
}

// Standardized 사증발급 application-route chips. Indices map to the
// issuanceRouteChipLabels i18n pack. Chips are derived ONLY from the structured
// issuanceMode fields (type / actor / whereToApply) and route facts already
// present in the record's own source text — never invented. visa_exempt /
// not_applicable routes are not application channels, so they get no route chips.
const ISSUANCE_ROUTE_CHIP_INDEX = {
    consular: 0,      // 재외공관 신청
    confirmation: 1,  // 사증발급인정서
    eVisa: 2,         // 전자사증
    visaPortal: 3,    // 비자포털 확인
    sponsor: 4,       // 초청기관·고용주 진행
    perMission: 5     // 공관별 확인 필요
};
function deriveIssuanceRouteChips(mode, record) {
    if (!mode) return [];
    const type = mode.type || '';
    const actor = mode.actor || '';
    const where = mode.whereToApply || '';
    // 사증면제·신규발급 중단 경로는 신청 채널이 아니므로 경로 칩을 만들지 않습니다.
    if (type === 'visa_exempt' || type === 'not_applicable') return [];
    const sourceText = [mode.labelKo, mode.labelEn, mode.appliesToKo, mode.appliesToEn]
        .filter(Boolean).join(' ').toLowerCase();
    const mentions = (...needles) => needles.some(n => sourceText.includes(n));
    const picked = [];
    const add = (key, isCheck = false) => {
        if (!picked.some(item => item.key === key)) picked.push({ key, isCheck });
    };
    if (where === 'overseas_mission' || type === 'mixed' || type === 'consular_discretion') add('consular');
    if (type === 'visa_issuance_confirmation' || mentions('발급인정', '인정서', 'certificate of confirmation', 'confirmation of visa')) add('confirmation');
    if (mentions('전자사증', '전자비자', 'e-visa', 'electronic visa')) add('eVisa');
    if (mentions('비자포털', 'visa.go.kr', 'visa portal')) add('visaPortal');
    if (actor === 'employer' || mentions('초청', '고용주', 'sponsor', 'employer')) add('sponsor');
    // 국가·공관별로 절차가 달라지는 경우에만 "확인 필요" 칩(점선)을 덧붙입니다.
    const overlayRequired = !!(record && record.countryVariance && record.countryVariance.officialOverlayRequired);
    if (where === 'mixed' || type === 'consular_discretion' || overlayRequired) add('perMission', true);
    // 어떤 칩도 도출되지 않으면 최소한 재외공관 신청 채널을 안내합니다.
    if (!picked.length) add('consular');
    return picked
        .map(item => ({ label: txAt('issuanceRouteChipLabels', ISSUANCE_ROUTE_CHIP_INDEX[item.key], ''), isCheck: item.isCheck }))
        .filter(item => item.label);
}
function renderIssuanceRouteChips(mode, record) {
    const chips = deriveIssuanceRouteChips(mode, record);
    if (!chips.length) return '';
    const groupLabel = tx('issuanceRouteLabel');
    const chipHtml = chips.map(chip =>
        `<span class="issuance-route-chip${chip.isCheck ? ' is-check' : ''}">${escapeHtml(chip.label)}</span>`
    ).join('');
    return `<div class="issuance-route-chips" role="group" aria-label="${escapeHtml(groupLabel)}"><span class="issuance-route-label">${escapeHtml(groupLabel)}</span>${chipHtml}</div>`;
}

function renderIssuanceModeCard(mode, record, binding, keywords, options = {}) {
    const level = binding && binding.evidenceLevel ? binding.evidenceLevel : (mode.type === 'not_applicable' ? 'not_applicable' : 'limited');
    const sourceState = binding || {
        evidenceLevel: level,
        userFacingExplanationKo: getDefaultLimitationExplanation(level),
        manualSources: mode.sourceRefs || []
    };
    const title = pickLocalizedManualText({ ko: mode.labelKo, en: mode.labelEn });
    const applies = pickLocalizedManualText({ ko: mode.appliesToKo, en: mode.appliesToEn });
    const sourceRefs = mode.sourceRefs || (record.manualSource ? [record.manualSource] : []);
    const sourceLine = getFormattedSourceRefs({ sourceRefs }).slice(0, 2).join(' / ');
    // Optional friendly emoji icon (used by the scenario-guide cards for E-8~E-10).
    const iconHtml = mode.icon ? `<span class="issuance-card-icon" aria-hidden="true">${escapeHtml(mode.icon)}</span>` : '';
    return `<article class="issuance-scenario-card${mode.type === 'not_applicable' ? ' is-not-applicable' : ''}">
        <div class="issuance-card-head">
            <h5 class="issuance-card-title">${iconHtml}${escapeHtml(title)}</h5>
            <span class="issuance-source-badge ${escapeHtml(getSourceEvidenceBadgeClass(level))}">${escapeHtml(getSourceEvidenceLabel(level))}</span>
        </div>
        ${renderIssuanceRouteChips(mode, record)}
        ${applies ? `<p class="issuance-applies">${escapeHtml(applies)}</p>` : ''}
        <div><h6 class="issuance-subtitle">${escapeHtml(txAt('issuanceUiLabels', 4, '절차'))}</h6>${renderIssuanceSteps(mode.steps, keywords)}</div>
        ${options.suppressDocuments ? '' : renderIssuanceDocGroups(mode.documents, keywords)}
        ${renderIssuanceWarnings(mode.warnings, keywords)}
        ${renderSourceLimitationExplanation(sourceState, sourceRefs)}
    </article>`;
}

// 사증발급 시나리오 안내 팝업 — 세부코드/업종/국적 등으로 신청 경로·서류가
// 갈리는 자격(E-8·E-9·E-10 등)을 위한 단일 질문형 선택 UI. 모든 모드 카드를
// 한꺼번에 쏟지 않고, 사용자가 본인 상황을 고르면 해당 시나리오의 카드만 보여
// 인지부담을 최소화합니다. 출처 기반 issuanceModes 데이터만 사용 — 발명 없음.
function renderIssuanceScenarioPicker(v, record, modes, binding, keywords) {
    const question = pickLocalizedManualText({ ko: record.scenarioQuestionKo, en: record.scenarioQuestionEn }) || tx('issuanceGuideQuestionFallback');
    const cards = modes.map(mode => {
        const choiceTitle = pickLocalizedManualText({ ko: mode.choiceTitleKo || mode.labelKo, en: mode.choiceTitleEn || mode.labelEn });
        const card = renderIssuanceModeCard(mode, record, binding, keywords, { suppressDocuments: false });
        return `<div class="issuance-mode-card-wrap" data-issuance-mode-card="${escapeHtml(mode.id || '')}" data-issuance-choice="${escapeHtml(choiceTitle)}">${card}</div>`;
    }).join('');
    return `<div class="issuance-scenario-guide issuance-needs-pick" data-issuance-guide data-visa-code="${escapeHtml(v.code)}">
        <p class="issuance-guide-question">${escapeHtml(question)}</p>
        <div class="issuance-guide-bar">
            <button type="button" class="issuance-guide-trigger" data-action="open-issuance-guide" data-visa-code="${escapeHtml(v.code)}" aria-haspopup="dialog">
                <span class="issuance-guide-trigger-icon" aria-hidden="true">🧭</span>
                <span class="issuance-guide-trigger-label">${escapeHtml(tx('issuanceGuideTrigger'))}</span>
                <span class="issuance-guide-trigger-caret" aria-hidden="true">▾</span>
            </button>
            <button type="button" class="issuance-guide-clear" data-action="clear-issuance-guide" hidden>${escapeHtml(tx('issuanceGuideClear'))}</button>
        </div>
        <p class="issuance-guide-empty-hint">${escapeHtml(tx('issuanceGuideEmptyHint'))}</p>
        <div class="issuance-scenario-grid issuance-mode-cards">${cards}</div>
    </div>`;
}

function renderVisaIssuanceSection(v, keywords, options = {}) {
    if (['faq', 'scn', 'nhis'].includes(v.cat)) return '';
    // F-4 (재외동포) keeps its dedicated diaspora route guide; it is never absorbed
    // into the generic 사증발급 issuance renderer. See GENERIC_VISA_ISSUANCE_EXCLUDED_CODES.
    if (isGenericVisaIssuanceExcluded(v.code)) return '';
    // 사증발급이 적용되지 않는 체류자격(사증면제 B-1·B-2, 비대상 H-2, 영주 F-5)은
    // 절차 탭(embedded)·별도 섹션(standalone) 어디에서도 사증발급을 렌더링하지
    // 않습니다 — '[사증발급]이 아닌데도 사증발급이 뜨던' 오류 차단.
    if (isVisaIssuanceNotApplicable(v)) return '';
    const record = getVisaIssuanceRecord(v.code);
    if (!record) return '';
    const embedded = !!options.embedded;
    // When the host procedure panel already renders the basic-document grid, the
    // scenario cards drop their duplicate document list so the same documents are
    // not shown twice (top grid + card).
    const suppressModeDocuments = !!options.suppressModeDocuments;
    const binding = getVisaIssuanceBinding(v.code);
    const summary = pickLocalizedManualText({ ko: record.issuanceSummaryKo, en: record.issuanceSummaryEn });
    const modes = Array.isArray(record.issuanceModes) ? record.issuanceModes : [];
    // Scenario-guide records (E-8/E-9/E-10 등) carry multiple source-backed modes
    // (세부코드·업종·선박종류별). Present them behind a friendly single-question
    // popup so the user picks their situation and sees only that path's 서류·절차.
    const useScenarioGuide = !!record.scenarioGuide && modes.length >= 2;
    const cardsBlock = useScenarioGuide
        ? renderIssuanceScenarioPicker(v, record, modes, binding, keywords)
        : `<div class="issuance-scenario-grid">${modes.map(mode => renderIssuanceModeCard(mode, record, binding, keywords, { suppressDocuments: suppressModeDocuments })).join('')}</div>`;
    const variance = record.countryVariance && record.countryVariance.reasonKo ? record.countryVariance.reasonKo : '';
    const disclaimer = pickLocalizedManualText({ ko: record.disclaimerKo, en: record.disclaimerEn });
    const title = txAt('issuanceUiLabels', 0, '사증발급');
    // Small procedure-stage kicker ("입국 전 사증발급") so the user reads this as the
    // before-entry step within 절차별 안내, distinct from the after-entry stay procedures.
    const stageLabel = `<p class="issuance-stage-label">${escapeHtml(tx('issuanceStageLabel'))}</p>`;
    const body = `${stageLabel}
        ${summary ? `<p class="visa-issuance-summary">${hl(escapeHtml(summary), keywords || [])}</p>` : ''}
        ${cardsBlock}
        ${renderIssuanceOverlaySelector(v.code)}
        ${variance ? `<p class="issuance-variance-note">${escapeHtml(variance)}</p>` : ''}
        ${disclaimer ? `<p class="issuance-disclaimer">${escapeHtml(disclaimer)}</p>` : ''}`;
    if (embedded) {
        // Rendered inside the 사증발급 procedure tab — the tab already labels the
        // section, so the duplicate top-level "사증발급" heading is dropped.
        return `<div class="visa-issuance-section visa-issuance-section--embedded" aria-label="${escapeHtml(title)}">${body}</div>`;
    }
    return `<section class="manual-section visa-issuance-section" aria-label="${escapeHtml(title)}">
        <h4 class="manual-section-title">${escapeHtml(title)}</h4>
        ${body}
    </section>`;
}

// --- 사증발급 시나리오 안내 팝업 동작 -------------------------------------
// The choices live in a modal dialog (#issuanceGuideOverlay), built on demand
// from the record's own issuanceModes. Picking a scenario reveals only that
// mode's card (가게이팅), so the result stays uncluttered for 단순노무 사용자.
// The active guide is tracked by ELEMENT (not just code) so selection always
// targets the card group the user opened, even if the same status code renders
// in more than one place (e.g. the cloned visa-detail drawer).
let issuanceGuideActiveGuide = null;

function openIssuanceGuide(trigger) {
    const guide = trigger.closest('[data-issuance-guide]');
    const code = (guide && guide.getAttribute('data-visa-code')) || trigger.dataset.visaCode || '';
    const record = getVisaIssuanceRecord(code);
    if (!record) return;
    issuanceGuideActiveGuide = guide || null;
    const modes = Array.isArray(record.issuanceModes) ? record.issuanceModes : [];
    const host = document.getElementById('issuanceGuideChoices');
    if (!host) return;
    const selectedId = guide ? (guide.getAttribute('data-selected-mode') || '') : '';
    host.innerHTML = modes.map(mode => {
        const icon = mode.icon || '';
        const title = pickLocalizedManualText({ ko: mode.choiceTitleKo || mode.labelKo, en: mode.choiceTitleEn || mode.labelEn });
        const preview = pickLocalizedManualText({ ko: mode.appliesToKo, en: mode.appliesToEn });
        const pressed = (mode.id && mode.id === selectedId) ? 'true' : 'false';
        return `<button type="button" class="scenario-choice issuance-guide-choice" role="listitem" data-action="choose-issuance-mode" data-mode-id="${escapeHtml(mode.id || '')}" aria-pressed="${pressed}">
            <span class="issuance-guide-choice-icon" aria-hidden="true">${escapeHtml(icon)}</span>
            <span class="scenario-choice-body">
                <span class="scenario-choice-main"><span class="issuance-guide-choice-label">${escapeHtml(title)}</span></span>
                ${preview ? `<span class="scenario-choice-preview">${escapeHtml(makeManualPreview(preview, 120))}</span>` : ''}
            </span>
            <span class="scenario-choice-go" aria-hidden="true">→</span>
        </button>`;
    }).join('');
    const heading = document.getElementById('issuanceGuideTitle');
    if (heading) heading.textContent = pickLocalizedManualText({ ko: record.scenarioQuestionKo, en: record.scenarioQuestionEn }) || tx('issuanceGuideModalTitle');
    const copy = document.getElementById('issuanceGuideModalCopy');
    if (copy) copy.textContent = tx('issuanceGuideModalCopy');
    openModal('issuanceGuideOverlay');
}

function chooseIssuanceMode(button) {
    const id = button.dataset.modeId || '';
    if (issuanceGuideActiveGuide) applyIssuanceModeSelection(issuanceGuideActiveGuide, id);
    closeModal('issuanceGuideOverlay');
    issuanceGuideActiveGuide = null;
}

function applyIssuanceModeSelection(guide, modeId) {
    if (!guide) return;
    if (modeId) guide.setAttribute('data-selected-mode', modeId);
    else guide.removeAttribute('data-selected-mode');
    guide.classList.toggle('has-selection', !!modeId);
    let selectedLabel = '';
    guide.querySelectorAll('[data-issuance-mode-card]').forEach(card => {
        const isSel = !!modeId && card.dataset.issuanceModeCard === modeId;
        card.classList.toggle('is-selected', isSel);
        if (isSel) selectedLabel = card.dataset.issuanceChoice || '';
    });
    const label = guide.querySelector('.issuance-guide-trigger-label');
    if (label) label.textContent = selectedLabel ? `✓ ${selectedLabel}` : tx('issuanceGuideTrigger');
    const clearBtn = guide.querySelector('.issuance-guide-clear');
    if (clearBtn) clearBtn.hidden = !modeId;
}

function clearIssuanceGuide(button) {
    const guide = button.closest('[data-issuance-guide]');
    if (guide) applyIssuanceModeSelection(guide, '');
}

function visaIssuanceProcedureAvailable(v) {
    const cfg = Array.isArray(PROCEDURE_CONFIG) ? PROCEDURE_CONFIG.find(p => p.key === 'visaIssuance') : null;
    return cfg ? getProcedure(v, cfg).available : false;
}

// The rich 사증발급 (visa-issuance) section is rendered INSIDE the 사증발급
// procedure tab (see renderProcedurePanel), so it only appears when that tab is
// active instead of permanently sitting under every procedure tab. Only when the
// status has no 사증발급 procedure tab to host it do we fall back to a standalone
// section, so the source-backed issuance content is never lost.
function renderStandaloneVisaIssuanceSection(v, keywords) {
    if (visaIssuanceProcedureAvailable(v)) return '';
    return renderVisaIssuanceSection(v, keywords);
}

export {
    isF4RouteWizardTarget, renderF4RouteChooser, selectF4Route, applyRouteSelection, openRoutePicker, chooseRoute,
    resetF4Route, renderSourceConfirmedRequirements, subcodeSourceChip, getParentVisaCode,
    isSubcodeOf, groupSearchResultsByParent, shouldAutoExpandSubcodeGroup, renderSubcodePreview, renderExpandableSubcodeGroup, renderSubcodes,
    renderParentScopeNotice, renderCommonWarnings, renderSourceReferences, openHikoreaGuide, renderHikoreaGuide, renderManualActions,
    renderNextActionArea, renderCardSummary, getVisaIssuanceRecord, getVisaIssuanceBinding, getVisaIssuanceOverlays, pickLocalizedManualText,
    renderIssuanceDocList, renderIssuanceDocGroups, renderIssuanceSteps, renderIssuanceWarnings, renderIssuanceOverlaySelector, isGenericVisaIssuanceExcluded,
    isVisaIssuanceNotApplicable, deriveIssuanceRouteChips, renderIssuanceRouteChips, renderIssuanceModeCard, renderIssuanceScenarioPicker, renderVisaIssuanceSection,
    openIssuanceGuide, chooseIssuanceMode, applyIssuanceModeSelection, clearIssuanceGuide, visaIssuanceProcedureAvailable, renderStandaloneVisaIssuanceSection,
    GENERIC_VISA_ISSUANCE_EXCLUDED_CODES, VISA_ISSUANCE_NOT_APPLICABLE_MODE_TYPES, VISA_ISSUANCE_NOT_APPLICABLE_CODES, ISSUANCE_ROUTE_CHIP_INDEX
};
