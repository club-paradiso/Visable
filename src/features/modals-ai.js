// @ts-nocheck
/**
 * Modal core, visa drawer, AI modal + Waymaker handoff, document/subcode/FAQ modals, the /api/ask call, the grounding
 * source panel, document help and document guide (structure map C05–C08 and C11–C12). The nine AI/document-help `let`
 * state variables are module-private (every reader and writer moved with them); `let docGuideData` stays inline because
 * src/render/cards' fee box reads it through a `typeof` guard. Module-evaluation side effects kept as they were:
 * `document.addEventListener('DOMContentLoaded', setupAiModeSelector)` and `window.verifyFaqWithAi = …` (both ran at
 * parse time before; the module evaluates before DOMContentLoaded, so the listener still fires). Uses the inline globals
 * VISA_DATA, currentLanguage, tx(), txAt(), escapeHtml(), showToast(), API_BASE, Visable.data/state and the Visable.docs /
 * Visable.cards stubs at call time (compatibility surface, ADR-009). assets/js (visa-route-guide, short-stay-checker,
 * legal-source-search) call openModal/closeModal/openVisaDrawer/openAiModal/buildWaymakerHandoffUrl by bare name, so
 * those keep inline stubs. Covered by tests/golden/specs/fail-closed.spec.mjs (AI endpoint aborted / 503) and
 * legacy-card.spec.mjs (drawer/doc actions present); backend static tests slice the /api/ask body from the corpus.
 * Moved verbatim from index.html lines 16467-17516 (1027 lines; kept inline: ['docGuideData']).
 * Exposed on window.Visable.modals; 21 inline stubs with the same names delegate here.
 */
function openModal(id) {
    const modal = document.getElementById(id);
    if (!modal || modal.classList.contains('active')) return;
    lastFocusedElement = document.activeElement;
    if(modal) {
        modal.classList.add('active');
        modal.setAttribute('aria-hidden', 'false');
        activeModal = modal;
        document.addEventListener('keydown', trapModalFocus);
        syncModalScrollLock();
        const focusable = modalFocusables(modal)[0];
        if(focusable) focusable.focus({ preventScroll: true });
    }
}
function closeModal(id) {
    const modal = document.getElementById(id);
    const wasActive = activeModal === modal;
    if(modal) {
        modal.classList.remove('active');
        modal.setAttribute('aria-hidden', 'true');
    }
    if (activeModal && modal === activeModal) {
        activeModal = null;
        document.removeEventListener('keydown', trapModalFocus);
    }
    syncModalScrollLock();
    if(wasActive && lastFocusedElement) {
        if (lastFocusedElement.isConnected) lastFocusedElement.focus({ preventScroll: true });
        lastFocusedElement = null;
    }
}

// --- Visa Detail Drawer ---
// Clones the existing detailed `.vc[data-code]` card into a side drawer
// (desktop) / bottom sheet (mobile). Reuses all existing render output so
// warnings, source panels, document tabs, and next actions remain intact.
function openVisaDrawer(code) {
    if (!code) return false;
    const overlay = document.getElementById('visaDrawerOverlay');
    const body = document.getElementById('visaDrawerBody');
    if (!overlay || !body) return false;
    const source = document.querySelector(`#rlist .vc[data-code="${CSS.escape(code)}"]`);
    if (!source) return false;

    const titleEl = document.getElementById('visaDrawerTitle');
    const eyebrowEl = document.getElementById('visaDrawerEyebrow');
    const disclaimerEl = document.getElementById('visaDrawerDisclaimer');
    if (eyebrowEl) eyebrowEl.textContent = tx('drawerEyebrow');
    if (disclaimerEl) disclaimerEl.textContent = tx('drawerDisclaimer');
    const visa = (typeof VISA_DATA !== 'undefined') ? VISA_DATA.find(v => v.code === code) : null;
    const name = visa ? (getLocalizedVisaName(visa) || '') : '';
    if (titleEl) titleEl.textContent = name ? `${code} · ${name}` : code;

    const clone = source.cloneNode(true);
    clone.classList.add('open');
    clone.removeAttribute('data-code'); // avoid duplicate query matches
    if (clone.id) clone.removeAttribute('id');
    // Strip the top-level toggle so users can't collapse the entire drawer body
    const topHeader = clone.querySelector(':scope > .vc-h');
    if (topHeader) topHeader.removeAttribute('data-action');
    // Sanitize duplicate IDs that would collide with the main #rlist clone
    clone.querySelectorAll('[id]').forEach(el => el.removeAttribute('id'));

    body.innerHTML = '';
    body.appendChild(clone);
    hydrateScenarioChecklistState(clone);
    body.scrollTop = 0;

    lastFocusedElement = document.activeElement;
    overlay.classList.add('active');
    overlay.setAttribute('aria-hidden', 'false');
    activeModal = overlay;
    document.addEventListener('keydown', trapModalFocus);
    document.body.classList.add('drawer-open');
    syncModalScrollLock();
    const closeBtn = overlay.querySelector('.visa-drawer-close');
    if (closeBtn) closeBtn.focus();
    return true;
}

function closeVisaDrawer() {
    const overlay = document.getElementById('visaDrawerOverlay');
    if (!overlay || !overlay.classList.contains('active')) return;
    overlay.classList.remove('active');
    overlay.setAttribute('aria-hidden', 'true');
    if (activeModal === overlay) {
        activeModal = null;
        document.removeEventListener('keydown', trapModalFocus);
    }
    document.body.classList.remove('drawer-open');
    syncModalScrollLock();
    // Defer body clear until after the transition so it doesn't flash
    setTimeout(() => {
        const body = document.getElementById('visaDrawerBody');
        if (body && !overlay.classList.contains('active')) body.innerHTML = '';
    }, 320);
    if (!activeModal && lastFocusedElement) {
        try { lastFocusedElement.focus(); } catch (e) {}
        lastFocusedElement = null;
    } else if (!activeModal) {
        lastFocusedElement = null;
    }
}

// --- AI Modal ---
let currentAiVisaCode = null;
let currentAiController = null;
let currentAiSelectedProcedureKey = null;
let currentAiSelectedProcedureVariantId = null;
// Waymaker answer-speed tier: 'fast' | 'basic' | 'pro' (pro is coming-soon).
let currentAiAnswerMode = 'basic';
function setupAiModeSelector() {
    const selector = document.getElementById('aiModeSelector');
    if (!selector || selector.dataset.wired) return;
    selector.dataset.wired = '1';
    selector.querySelectorAll('.ai-mode-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const mode = btn.dataset.mode;
            if (btn.classList.contains('is-disabled')) return;
            currentAiAnswerMode = mode;
            selector.querySelectorAll('.ai-mode-btn').forEach(b => {
                const active = b === btn;
                b.classList.toggle('is-active', active);
                b.setAttribute('aria-checked', active ? 'true' : 'false');
            });
        });
    });
}
document.addEventListener('DOMContentLoaded', setupAiModeSelector);
function findProcedureVariant(visa, procedureKey, variantId) {
    const variants = visa?.procedures?.[procedureKey]?.variants;
    if (!Array.isArray(variants)) return null;
    return variants.find(variant => variant && variant.id === variantId) || null;
}
function openAiModal(visaCode, selectedProcedureKey = '', selectedProcedureVariantId = '', selectedVariantLabel = '', promptKey = 'selectedScenarioAiPrompt') {
    const visa = VISA_DATA.find(v => v.code === visaCode);
    if (!visa) return false;
    const selectedVariant = findProcedureVariant(visa, selectedProcedureKey, selectedProcedureVariantId);
    currentAiVisaCode = visaCode;
    currentAiSelectedProcedureKey = selectedVariant ? selectedProcedureKey : null;
    currentAiSelectedProcedureVariantId = selectedVariant ? selectedProcedureVariantId : null;
    document.getElementById('aiModalTitleText').innerHTML = `${escapeHtml(visa.code)} (${escapeHtml(visa.name)})`;

    const descEl = document.querySelector('#aiModalOverlay .modal-body p');
    // Localized through tx() for all four main languages (was ko/en-only, which
    // left Chinese modes showing Korean copy).
    descEl.innerHTML = ['faq', 'scn', 'nhis'].includes(visa.cat) ? tx('aiDescSpecial') : tx('aiDescGeneral');

    const jobCodeBtn = document.getElementById('btnJobCode');
    if (jobCodeBtn) {
        const isJobCodeTarget = Visable.features.jobcode.JOBCODE_TARGET_VISAS.some(prefix => visa.code === prefix || visa.code.startsWith(prefix + '-') || visa.code.startsWith(prefix));
        jobCodeBtn.style.display = isJobCodeTarget ? '' : 'none';
    }
    const aiInput = document.getElementById('aiInput');
    const contextEl = document.getElementById('aiModalContext');
    if (selectedVariant) {
        const label = selectedVariantLabel || selectedVariant.labelKo || selectedVariant.label || selectedVariant.id;
        aiInput.value = tx(promptKey || 'selectedScenarioAiPrompt', { visaCode: visa.code, label });
        // Show the user (and only as safe labels) which scenario context the AI
        // will receive. Only identifiers are sent — never checklist/reminder state.
        if (contextEl) {
            const procedureLabel = getProcedureLabelByKey(selectedProcedureKey, selectedProcedureKey);
            const bits = [visa.code, procedureLabel, label].filter(Boolean).map(escapeHtml).join(' · ');
            contextEl.innerHTML = `<span class="ai-modal-context-label">${escapeHtml(tx('aiModalContextLabel'))}</span> <span class="ai-modal-context-value">${bits}</span><span class="ai-modal-context-note">${escapeHtml(tx('aiModalContextNote'))}</span>`;
            contextEl.hidden = false;
        }
    } else {
        aiInput.value = '';
        if (contextEl) { contextEl.innerHTML = ''; contextEl.hidden = true; }
    }
    document.getElementById('aiResult').style.display = 'none';
    document.getElementById('aiResult').innerHTML = '';
    openModal('aiModalOverlay');
    return true;
}

// --- Waymaker (ai.html) selected-scenario handoff -------------------------
// The floating Waymaker CTA (.ai-fab) is a global entry point. When the user
// has selected a scenario, we carry ONLY safe identifiers + the public scenario
// label to ai.html so Waymaker opens with the same context as the in-page modal.
// Checklist/checkbox/reminder/localStorage state is NEVER included. Reflects the
// most recently selected scenario; cleared when the selection is reset.
let selectedScenarioHandoff = null;
function buildWaymakerHandoffUrl(visaCode, procedureKey, variantId, label, lang) {
    const params = new URLSearchParams();
    if (visaCode) params.set('visa_code', visaCode);
    if (procedureKey) params.set('selected_procedure_key', procedureKey);
    if (variantId) params.set('selected_procedure_variant_id', variantId);
    if (label) params.set('scenario_label', label);
    params.set('lang', lang || currentLanguage || 'ko');
    return 'ai.html?' + params.toString();
}
function syncWaymakerFab() {
    const fab = document.querySelector('.ai-fab');
    if (!fab) return;
    if (selectedScenarioHandoff) {
        const h = selectedScenarioHandoff;
        fab.setAttribute('href', buildWaymakerHandoffUrl(h.visaCode, h.procedureKey, h.variantId, h.label));
    } else {
        fab.setAttribute('href', 'ai.html');
    }
}
function setSelectedScenarioHandoff(visaCode, procedureKey, variantId, label) {
    selectedScenarioHandoff = { visaCode, procedureKey, variantId, label };
    syncWaymakerFab();
}
function clearSelectedScenarioHandoff() {
    selectedScenarioHandoff = null;
    syncWaymakerFab();
}
// Shared entry for the in-card scenario AI CTAs so a failed open never becomes a
// silent no-op — the user always gets visible feedback.
function handleScenarioAiHandoff(btn, promptKey = 'selectedScenarioAiPrompt') {
    if (!btn) return false;
    const opened = openAiModal(btn.dataset.visaCode, btn.dataset.procedureKey, btn.dataset.variantId, btn.dataset.variantLabel, promptKey);
    if (!opened && typeof showToast === 'function') showToast(tx('scenarioAiOpenError'));
    return opened;
}

// --- Doc Modal ---
function openDocModal(visaCode, type, subIdx) {
    const visa = VISA_DATA.find(v => v.code === visaCode);
    if (!visa) return;
    let title = '', docs = [];
    let stageNote = '';
    let targetCode = visa.code;
    const isFaq = ['faq', 'scn', 'nhis'].includes(visa.cat);

    if (type === 'new') {
        title = tx('docModalTitleNew');
        docs = flattenDocGroups(getProcedure(visa, PROCEDURE_CONFIG.find(p => p.key === 'visaIssuance')).docs);
    } else if (type === 'ext') {
        title = tx('docModalTitleExt');
        docs = flattenDocGroups(getProcedure(visa, PROCEDURE_CONFIG.find(p => p.key === 'extension')).docs);
    } else if (type === 'change') {
        title = tx('docModalTitleChange');
        docs = flattenDocGroups(getProcedure(visa, PROCEDURE_CONFIG.find(p => p.key === 'statusChange')).docs);
        if (!docs.length) {
            docs = [
                ...flattenDocGroups(getProcedure(visa, PROCEDURE_CONFIG.find(p => p.key === 'extension')).docs),
                ...flattenDocGroups(getProcedure(visa, PROCEDURE_CONFIG.find(p => p.key === 'visaIssuance')).docs)
            ];
            docs = dedupeDocs(docs);
            if (docs.length) stageNote = tx('docModalTitleChangeNote');
        }
    } else if (type === 'sub' && subIdx != null) {
        const sIdx = parseInt(subIdx, 10);
        const subcodes = getVisaSubcodes(visa);
        if (!isNaN(sIdx) && subcodes[sIdx]) {
            const sub = subcodes[sIdx];
            title = tx('docModalTitleSub', { name: sub.name || tx('docModalTitleSubFallbackName') }); docs = flattenDocGroups(normalizeDocGroups(null, sub, { additionalDocs: ['addReqDocs', 'addReq'] })); targetCode = sub.code;
        } else { title = tx('docModalTitleSubGeneric'); }
    }
    document.getElementById('docModalTitle').innerHTML = `${escapeHtml(visa.code)} - ${escapeHtml(title)}${stageNote ? ` <span style="font-size:0.8em;color:var(--color-warning);">(${escapeHtml(tx('docStageReference'))})</span>` : ''}`;
    const descEl = document.getElementById('docModalDesc');
    const docDisclaimer = currentLanguage === 'zh-CN'
        ? `🚨 <strong>实务注意事项</strong>：本清单为法令中明示的基本通用材料。审查官可依裁量判断，在出入境实务现场要求补充额外的证明材料。<br><div style="margin-top:0.6rem; padding-top:0.6rem; border-top:1px dashed var(--bd); color:var(--t2);">🤝 <strong>代理人（家属、雇主等）代为访问申请须知</strong><br>• <strong>代理资格：</strong>仅限因疾病、未满 17 周岁等不得已事由者，或配偶/直系亲属、邀请人/雇主（含所属员工）。（※ 永住（F-5）等必须本人出席的民愿除外）<br>• <strong>必备携带：</strong>除上述基本材料外，须务必携带 <strong>① 委托书（指定格式）② 代理人身份证（核对原件及复印件）③ 关系证明材料（家庭关系证明书、在职证明书等）</strong>，且综合申请书下方须有代理人签名。</div>`
        : currentLanguage === 'en'
        ? `<strong>Practice note</strong>: This checklist covers basic common documents stated in laws and manuals. Immigration reviewers may request additional supporting materials in practice.<br><div style="margin-top:0.6rem; padding-top:0.6rem; border-top:1px dashed var(--bd); color:var(--t2);"><strong>Proxy visit note</strong><br>Proxy filing is limited to permitted cases such as unavoidable illness, minors under 17, spouse/direct relatives, inviter/employer, or employees of the employer. Bring the required base documents plus a power of attorney, proxy ID, and relationship proof where applicable.</div>`
        : `🚨 <strong>실무 주의사항</strong>: 본 체크리스트는 법령에 명시된 기본 공통 서류입니다. 심사관의 재량적 판단에 따라 출입국 실무 현장에서 추가 소명 자료가 징구될 수 있습니다.<br><div style="margin-top:0.6rem; padding-top:0.6rem; border-top:1px dashed var(--bd); color:var(--t2);">🤝 <strong>대리인(가족, 고용주 등) 방문 대리 신청 안내</strong><br>• <strong>대리 자격:</strong> 질병, 만 17세 미만 등 부득이한 사유가 있거나, 배우자/직계친족, 초청자/고용주(소속 직원 포함)에 한함. (※ 영주(F-5) 등 본인 출석 필수 민원은 예외)<br>• <strong>필수 지참:</strong> 위 기본 서류 외에 <strong>① 위임장(소정 양식) ② 대리인 신분증(원본 대조 및 사본) ③ 관계 입증 서류(가족관계증명서, 재직증명서 등)</strong>를 반드시 지참해야 하며, 통합신청서 하단에 대리인 서명이 필수입니다.</div>`;
    descEl.innerHTML = `${stageNote ? `<div class="text-desc" style="margin-bottom:0.6rem;">${stageNote}</div>` : ''}${renderModalFeeBox(visa, type)}${docDisclaimer}`;
    descEl.style.display = 'block';
    document.getElementById('docModalChecklist').innerHTML = docs.length
        ? renderDocTags(docs, [], type === 'sub', targetCode) + renderDocGroupingSourceNote()
        : `<div class="text-desc">${escapeHtml(tx('docReviewFallback'))}</div>`;
    openModal('docModalOverlay');
}

// --- Subcode Detail Modal ---
// Structured, data-driven detail view for a single 세부코드. Everything is
// sourced from the parent record's existing subCodes[] entry and
// procedures[].variants[] — nothing is invented (CLAUDE.md). Empty sections are
// omitted; honest source-gap copy is shown when subcode-specific data is thin.
function renderSubcodeProcedureVariants(visa, sub) {
    const procs = (visa && visa.procedures) || {};
    const target = normalizeVisaCode(sub.code);
    const blocks = [];
    Object.keys(procs).forEach(procKey => {
        const proc = procs[procKey];
        const variants = proc && Array.isArray(proc.variants) ? proc.variants : [];
        variants.forEach(variant => {
            if (!variant || normalizeVisaCode(variant.statusCode) !== target) return;
            const procLabel = getProcedureLabelByKey(procKey, procKey);
            const scenarioLabel = paradisoStripInternalReviewArtifacts(variant.labelKo || variant.label || '');
            const scenario = stripManualArtifacts(variant.scenarioKo || variant.scenario || '');
            const vDocs = flattenDocGroups(normalizeDocGroups(variant.requiredDocs || null, variant));
            const docsHtml = vDocs.length ? renderDocTags(vDocs, [], true, sub.code) : '';
            const notes = Array.isArray(variant.notes) ? variant.notes.map(n => stripManualArtifacts(n)).filter(Boolean) : [];
            const notesHtml = notes.length ? `<ul class="subcode-modal-vnotes">${notes.map(n => `<li>${escapeHtml(n)}</li>`).join('')}</ul>` : '';
            blocks.push(`<div class="subcode-modal-variant"><div class="subcode-modal-variant-head"><span class="subcode-modal-variant-proc">${escapeHtml(procLabel)}</span>${scenarioLabel ? `<span class="subcode-modal-variant-label">${escapeHtml(scenarioLabel)}</span>` : ''}</div>${scenario ? `<p class="subcode-modal-text">${escapeHtml(scenario)}</p>` : ''}${docsHtml}${notesHtml}</div>`);
        });
    });
    return blocks.join('');
}

// Pure builder (no DOM): returns the modal's header + body HTML for one subcode.
// Kept side-effect-free so it can be unit-tested headlessly (scripts/check_subcode_modal.mjs).
function buildSubcodeModalView(visa, sub) {
    const name = getLocalizedSubcodeName(sub) || '';
    const parentName = getLocalizedVisaName(visa) || '';
    const title = name ? `${escapeHtml(sub.code)} · ${escapeHtml(name)}` : escapeHtml(sub.code);
    /* UX-03 `Result / Subcode Card` (node 473:96): "상위 코드 D-10 — 공통 요건은
       상위 코드 카드에서 확인하세요". Naming the parent is not enough — this view
       shows only what is SPECIFIC to the sub-code, so a reader who takes it as
       complete would miss the parent's common requirements entirely. This is
       the reciprocal of renderParentScopeNotice, which scopes the parent card
       when a sub-code was searched. */
    const parentScope = `<span class="subcode-modal-parent-scope">${escapeHtml(tx('subcodeModalParentScope', { code: visa.code }))}</span>`;
    const parentHtml = `<span class="subcode-modal-parent-text">${escapeHtml(tx('subcodeModalParentLabel'))}: ${escapeHtml(visa.code)}${parentName ? ` (${escapeHtml(parentName)})` : ''}</span>${subcodeSourceChip(sub)}${parentScope}`;

    const sections = [];

    // 1) When does it apply (only when source text exists — never filler).
    const about = stripManualArtifacts(sub.summary)
        || (Array.isArray(sub.eligibility) && sub.eligibility[0])
        || stripManualArtifacts(sub.note)
        || stripManualArtifacts(sub.addReq);
    if (about) {
        sections.push(`<section class="subcode-modal-section"><h3 class="subcode-modal-h">${escapeHtml(tx('subcodeModalAbout'))}</h3><p class="subcode-modal-text">${escapeHtml(about)}</p></section>`);
    }

    // 2) Subcode-specific additional documents (cautious label — not "필수").
    const docs = flattenDocGroups(normalizeDocGroups(null, sub, { additionalDocs: ['addReqDocs', 'addReq'] }));
    const docsHtml = docs.length
        ? renderDocTags(docs, [], true, sub.code) + renderDocGroupingSourceNote()
        : `<p class="subcode-modal-gap">${escapeHtml(tx('subcodeModalNoDocs'))}</p>`;
    sections.push(`<section class="subcode-modal-section"><h3 class="subcode-modal-h">${escapeHtml(tx('subcodeModalDocsTitle'))}</h3>${docsHtml}</section>`);

    // 3) Subcode-specific procedure variants (omit section if none).
    const variantHtml = renderSubcodeProcedureVariants(visa, sub);
    if (variantHtml) {
        sections.push(`<section class="subcode-modal-section"><h3 class="subcode-modal-h">${escapeHtml(tx('subcodeModalProcTitle'))}</h3>${variantHtml}</section>`);
    }

    // 4) Cautions (deprecated/inactive status note; omit if none).
    const warnings = [];
    if (sub.status && sub.status !== 'active') {
        const sn = paradisoStripInternalReviewArtifacts(sub.statusNote);
        if (sn) warnings.push(sn);
    }
    if (warnings.length) {
        sections.push(`<section class="subcode-modal-section"><h3 class="subcode-modal-h">${escapeHtml(tx('subcodeModalWarnTitle'))}</h3><ul class="subcode-modal-warn">${warnings.map(w => `<li>${escapeHtml(w)}</li>`).join('')}</ul></section>`);
    }

    // 5) Official basis (subcode manualRefs, else honest source-gap copy).
    const refs = Array.isArray(sub.manualRefs) ? sub.manualRefs : [];
    const sourceHtml = refs.length
        ? `<ul class="subcode-modal-source">${refs.map(ref => {
            const bits = [ref.manualName || tx('sourceManualFallback'), ref.manualVersion || ref.version || '2026.9', ref.pageRange || tx('pageNeedsReview'), `${tx('confidenceLabel')}: ${ref.confidence || tx('confidenceNeedsReview')}`];
            return `<li>${bits.map(escapeHtml).join(' · ')}</li>`;
        }).join('')}</ul>`
        : `<p class="subcode-modal-gap">${escapeHtml(tx('subcodeModalSourceGap'))}</p>`;
    sections.push(`<section class="subcode-modal-section"><h3 class="subcode-modal-h">${escapeHtml(tx('subcodeModalSourceTitle'))}</h3>${sourceHtml}</section>`);

    // CTA → parent status full guidance (avoids duplicating parent docs here).
    sections.push(`<div class="subcode-modal-cta"><button type="button" class="subcode-modal-cta-btn" data-action="search-hint" data-query="${escapeHtml(visa.code)}">${escapeHtml(tx('subcodeModalParentCta', { code: visa.code }))}</button></div>`);

    return { eyebrow: tx('subcodeModalEyebrow'), title, parentHtml, body: sections.join('') };
}

function openSubcodeModal(parentCode, subCode) {
    const visa = VISA_DATA.find(v => v.code === parentCode);
    if (!visa) return;
    const subs = getVisaSubcodes(visa);
    const sub = subs.find(s => normalizeVisaCode(s.code) === normalizeVisaCode(subCode));
    if (!sub) return;

    const view = buildSubcodeModalView(visa, sub);
    const eyebrowEl = document.getElementById('subcodeModalEyebrow');
    const titleEl = document.getElementById('subcodeModalTitle');
    const parentEl = document.getElementById('subcodeModalParent');
    const bodyEl = document.getElementById('subcodeModalBody');
    const backEl = document.getElementById('subcodeModalBackLabel');
    if (eyebrowEl) eyebrowEl.textContent = view.eyebrow;
    if (titleEl) titleEl.innerHTML = view.title;
    if (parentEl) parentEl.innerHTML = view.parentHtml;
    if (bodyEl) { bodyEl.innerHTML = view.body; bodyEl.scrollTop = 0; }
    if (backEl) backEl.textContent = tx('subcodeModalBack');
    openModal('subcodeDetailOverlay');
    // This is a page-level detail view, so move focus to its heading (rather than
    // the first control) for an accessible "you are now reading X" entry point.
    if (titleEl) titleEl.focus();
}

function renderModalFeeBox(visa, type) {
    const procedureKeyByType = { ext: 'extension', change: 'statusChange' };
    const key = procedureKeyByType[type];
    if (key) return renderProcedureFeeBox(getProcedureFeeInfo(visa, key));
    if (type === 'new') {
        return renderProcedureFeeBox({
            label: currentLanguage === 'zh-CN' ? '新申请居留资格相关手续费' : currentLanguage === 'en' ? 'New status-related fees' : '신규 체류자격 관련 수수료',
            revenueStamp: null,
            cardIssueFee: 35000,
            notes: currentLanguage === 'zh-CN' ? [
                '在韩国境内申请赋予居留资格时，政府收入印花 80,000 韩元为基本标准。',
                '入境后属于外国人登录对象者，另需缴纳外国人登录证发放手续费 35,000 韩元。',
                '驻外公馆的签证签发手续费可能因国籍·签证种类·公馆标准而有所不同。'
            ] : currentLanguage === 'en' ? [
                'When applying for grant of status in Korea, a KRW 80,000 revenue stamp is the usual baseline.',
                'People subject to foreigner registration after entry have a separate KRW 35,000 registration card fee.',
                'Consular visa issuance fees may vary by nationality, visa type, and mission.'
            ] : [
                '국내에서 체류자격 부여를 신청하는 경우 정부수입인지 80,000원이 기본입니다.',
                '입국 후 외국인등록 대상자는 외국인등록증 발급 수수료 35,000원이 별도입니다.',
                '재외공관 사증발급 수수료는 국적·사증 종류·공관 기준에 따라 달라질 수 있습니다.'
            ],
            sourceNote: STAY_FEE_SOURCE_NOTE
        });
    }
    return '';
}

// --- FAQ Modal ---
window.verifyFaqWithAi = function(visaCode, question) {
    closeModal('faqModalOverlay');
    openAiModal(visaCode);
    document.getElementById('aiInput').value = currentLanguage === 'zh-CN'
        ? `[法令真伪核验请求]\n请就以下情况/问题，确认 2026 年《出入境管理法》及签证/居留手册中准确的法律依据和原文规定。\n\n核验对象：${question}`
        : currentLanguage === 'en'
        ? `[Legal fact-check request]\nPlease confirm the exact legal basis and original provisions in the 2026 Immigration Act and the visa/residence manuals for the situation/question below.\n\nItem to verify: ${question}`
        : `[법령 진위여부 검증 요청]\n다음 상황/질문에 대한 2026년 출입국관리법 및 사증/체류 매뉴얼의 정확한 법적 근거와 원문 규정을 확인해 주십시오.\n\n검증 대상: ${question}`;
    setTimeout(() => { const btn = document.querySelector('.ai-action-btn[data-type="analyze"]'); if(btn) btn.click(); }, 150);
};
function openFaqModal(visaCode) {
    const visa = VISA_DATA.find(v => v.code === visaCode);
    if (!visa || !visa.faq) return;
    document.getElementById('faqModalTitle').innerHTML = currentLanguage === 'zh-CN' ? `${escapeHtml(visa.code)} 常见问题` : currentLanguage === 'en' ? `${escapeHtml(visa.code)} FAQ` : `${escapeHtml(visa.code)} 자주 묻는 질문`;
    const pairs = visa.faq.split(/Q:\s*/).filter(Boolean);
    const html = pairs.map(p => {
        const parts = p.split(/A:\s*/); const q = parts[0].trim(); const a = (parts[1] || '').trim();
        const verifyLabel = currentLanguage === 'zh-CN' ? 'AI 事实核查（核对法令/手册依据）' : currentLanguage === 'en' ? 'AI fact-check with legal/manual sources' : 'AI 팩트체크 (법령/매뉴얼 근거 확인)';
        return `<div class="faq-item"><div class="faq-q">Q. ${escapeHtml(q)}</div><div class="faq-a">${escapeHtml(a).replace(/\n/g, '<br>')}<div style="margin-top:0.85rem; text-align:right; border-top:1px dashed var(--bd2); padding-top:0.6rem;"><button type="button" class="cb" style="color:var(--ac); border-color:var(--ac);" data-action="verify-faq" data-vcode="${escapeHtml(visa.code)}" data-q="${escapeHtml(q).replace(/'/g,"\\'").replace(/"/g,"&quot;")}">🤖 ${escapeHtml(verifyLabel)}</button></div></div></div>`;
    }).join('');
    document.getElementById('faqModalBody').innerHTML = html || `<div class="text-desc">${currentLanguage === 'zh-CN' ? '暂无已登记的常见问题。' : currentLanguage === 'en' ? 'No registered FAQ entries.' : '등록된 자주 묻는 질문이 없습니다.'}</div>`;
    openModal('faqModalOverlay');
}

function fallbackCopy(text) {
    const ta = document.createElement('textarea'); ta.value = text; ta.style.position = 'fixed'; ta.style.opacity = '0';
    document.body.appendChild(ta); ta.select();
    try { document.execCommand('copy'); } catch {}
    document.body.removeChild(ta);
}

// --- Jurisdiction Modal ---
/* Jurisdiction finder moved to src/features/jurisdiction.js (Phase 3); these stubs keep the names the
   dispatcher and the DOMContentLoaded wiring call (all event-time). */
// --- AI Analysis Processing ---
// Explicit developer-diagnostics mode (?debug=1 / ?dev=1, localStorage
// paradisoDevDiagnostics=1, or window.PARADISO_DEV_DIAGNOSTICS). Ordinary users
// never see which provider/model produced an answer; the former public
// "응답 모델: OpenRouter · <model id>" badge was removed for that reason.
function isAiDevDiagnosticsEnabled() {
    try {
        if (typeof window !== 'undefined' && window.PARADISO_DEV_DIAGNOSTICS) return true;
        if (Visable.state.read(Visable.state.KEYS.devDiagnostics) === '1') return true;
        if (typeof location !== 'undefined' && location.search && /[?&](?:debug|dev)=1(?:&|$)/.test(location.search)) return true;
    } catch (e) { return false; }
    return false;
}

// Safe rendering of model text for the AI modal: escape first, then only
// line breaks, bold and Markdown headings (shown as bold lines, never as "###").
function formatAiModalAnswer(text) {
    return escapeHtml(String(text || ''))
        .split('\n')
        .map(function (line) { return line.replace(/^\s*#{1,6}\s+(.*?)\s*#*$/, '<strong>$1</strong>'); })
        .join('<br>')
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
}

// Build a user-friendly provider-error block. NEVER renders raw provider JSON,
// API keys, headers, or user ids — only localized copy plus a collapsed
// disclosure of sanitized technical hints (classified error + model ids +
// upstream status codes).
function buildProviderErrorHtml(detail) {
    detail = detail || {};
    const code = detail.error || '';
    // "Not configured" is a distinct, calm state with its own guidance.
    if (code === 'no_llm_provider_configured') {
        return `<b>${escapeHtml(tx('aiNoProvider'))}</b>`;
    }
    const fallbackAnswer = detail.fallback_answer || detail.copy_safe_answer || '';
    const attempted = Array.isArray(detail.attempted_models) ? detail.attempted_models : [];
    const statuses = Array.isArray(detail.upstream_statuses) ? detail.upstream_statuses : [];
    const techBits = [];
    if (detail.provider_error_type) techBits.push('type: ' + String(detail.provider_error_type));
    if (attempted.length) techBits.push('attempted: ' + attempted.map(String).join(', '));
    if (statuses.length) techBits.push('status: ' + statuses.map(String).join(', '));
    const tech = (techBits.length && isAiDevDiagnosticsEnabled())
        ? `<details class="ai-provider-error-tech" style="margin-top:.5rem;font-size:.78rem;color:var(--t3);"><summary>${escapeHtml(tx('aiShowTechnicalDetails'))}</summary><pre style="white-space:pre-wrap;">${escapeHtml(techBits.join('\n'))}</pre></details>`
        : '';
    if (fallbackAnswer) {
        const safe = escapeHtml(String(fallbackAnswer)).replace(/\n/g, '<br>');
        return `<div class="ai-provider-error"><b>${escapeHtml(tx('aiProviderTemporarilyUnavailable'))}</b><p style="margin-top:.25rem;">${escapeHtml(tx('aiTryAgainShortly'))}</p><p style="margin-top:.25rem;color:var(--t3);font-size:.82rem;">${escapeHtml(tx('aiFallbackFromMetadata'))}</p><div class="ai-fallback-answer" style="margin-top:.7rem;">${safe}</div>${tech}</div>`;
    }
    return `<div class="ai-provider-error"><b>${escapeHtml(tx('aiProviderBusy'))}</b><p style="margin-top:.4rem;">${escapeHtml(tx('aiAllCandidatesFailed'))}</p>${tech}</div>`;
}


function mapLawWarningToFriendly(code) {
    const map = {
        LAW_GROUNDING_DISABLED: tx('aiLawWarningDisabled'),
        LAW_API_KEY_MISSING: tx('aiLawWarningMissingKey'),
        SOURCE_UNAVAILABLE: tx('aiLawWarningSourceUnavailable'),
        LAW_API_TIMEOUT: tx('aiLawWarningTimeout'),
        LAW_API_BAD_RESPONSE: tx('aiLawWarningBadResponse'),
        LAW_API_PARSE_ERROR: tx('aiLawWarningBadResponse'),
        LAW_API_OFFICIAL_ERROR: tx('aiLawWarningOfficialError'),
        LAW_API_NO_RESULTS: tx('aiLawWarningNoResults'),
        CITATION_VERIFICATION_NOT_WIRED: tx('aiLawWarningNotWired')
    };
    return map[code] || tx('aiLawStatusNeedsReview');
}


function sourcePanelCopyForState(m) {
    const state = String(m.source_panel_state || '');
    const key = String(m.source_panel_label_key || '');
    const warnings = Array.isArray(m.law_grounding_warnings) ? m.law_grounding_warnings : [];
    const errorType = String(m.law_lookup_error_type || m.law_grounding_error || '').toUpperCase();
    const hasBadLawResponse = warnings.indexOf('LAW_API_BAD_RESPONSE') !== -1 || warnings.indexOf('LAW_API_PARSE_ERROR') !== -1 || errorType === 'LAW_API_BAD_RESPONSE' || errorType === 'LAW_API_PARSE_ERROR' || errorType === 'SOURCE_UNAVAILABLE';
    if (state === 'structured_fallback_available' || key === 'structured_fallback') {
        return { text: tx('sourcePanelStructuredFallbackLabel'), subtext: tx('sourcePanelStructuredFallbackSubtext'), cls: 'state-needs-review' };
    }
    if ((m.legal_analysis_exists || key === 'structured_legal_analysis_law_lookup_issue') && hasBadLawResponse) {
        return { text: tx('sourcePanelStructuredAnalysisUsedLabel'), subtext: tx('sourcePanelStructuredAnalysisUsedSubtext'), cls: 'state-partial' };
    }
    if (state === 'related_legal_context_available' || key === 'related_legal_context') {
        return { text: tx('sourcePanelRelatedContextLabel'), subtext: tx('sourcePanelRelatedContextSubtext'), cls: 'state-partial' };
    }
    return null;
}

function lawSourcePanelText(m, statusKey) {
    const normalized = sourcePanelCopyForState(m);
    if (normalized) return normalized;
    const warnings = Array.isArray(m.law_grounding_warnings) ? m.law_grounding_warnings : [];
    const errorType = String(m.law_lookup_error_type || m.law_grounding_error || '').toUpperCase();
    const legalAnalysis = m.legal_analysis || {};
    const mode = String(m.analysis_mode || legalAnalysis.analysis_mode || '');
    const directCount = Number(m.direct_evidence_count || legalAnalysis.direct_evidence_count || 0);
    const relatedCount = Number(m.related_evidence_count || legalAnalysis.related_evidence_count || 0);
    const analogicalCount = Number(m.analogical_evidence_count || legalAnalysis.analogical_evidence_count || 0);
    const missingDirect = Boolean(m.missing_direct_authority || legalAnalysis.missing_direct_authority);
    const hasEvidence = Boolean(m.law_evidence_count) || (Array.isArray(m.law_sources) && m.law_sources.length > 0);
    if ((m.legal_analysis_exists || (legalAnalysis && Object.keys(legalAnalysis).length)) && (warnings.indexOf('LAW_API_BAD_RESPONSE') !== -1 || warnings.indexOf('LAW_API_PARSE_ERROR') !== -1 || warnings.indexOf('SOURCE_UNAVAILABLE') !== -1 || errorType === 'LAW_API_BAD_RESPONSE' || errorType === 'LAW_API_PARSE_ERROR' || errorType === 'SOURCE_UNAVAILABLE')) return { text: tx('sourcePanelStructuredAnalysisUsedLabel'), subtext: tx('sourcePanelStructuredAnalysisUsedSubtext'), cls: 'state-partial' };
    if (directCount > 0 || mode === 'direct_authority') return { text: tx('lawAnalysisDirectAuthority'), cls: 'state-verified' };
    if (relatedCount > 0 || mode === 'contextual_authority') return { text: tx('sourcePanelRelatedContextLabel'), subtext: tx('sourcePanelRelatedContextSubtext'), cls: 'state-partial' };
    if (analogicalCount > 0 || mode === 'analogical_analysis') return { text: tx('lawAnalysisAnalogical'), cls: 'state-partial' };
    if (missingDirect && (hasEvidence || statusKey === 'used' || mode === 'limited_authority')) return { text: tx('lawAnalysisNoDirect'), cls: 'state-needs-review' };
    if (warnings.indexOf('LAW_API_TIMEOUT') !== -1 || errorType === 'LAW_API_TIMEOUT') return { text: tx('lawSourceTimeout'), cls: 'state-partial' };
    if (warnings.indexOf('LAW_API_OFFICIAL_ERROR') !== -1 || errorType === 'LAW_API_OFFICIAL_ERROR') return { text: tx('lawSourceOfficialError'), cls: 'state-partial' };
    if (warnings.indexOf('LAW_API_BAD_RESPONSE') !== -1 || warnings.indexOf('LAW_API_PARSE_ERROR') !== -1 || errorType === 'LAW_API_BAD_RESPONSE' || errorType === 'LAW_API_PARSE_ERROR') return { text: tx('lawAnalysisTechnicalIssue'), cls: 'state-partial' };
    if (warnings.indexOf('LAW_API_NOT_CONFIGURED') !== -1 || warnings.indexOf('LAW_API_KEY_MISSING') !== -1 || errorType === 'LAW_API_NOT_CONFIGURED' || statusKey === 'disabled') return { text: tx('lawAnalysisLookupUnavailable'), cls: 'state-disabled' };
    return { text: tx('lawAnalysisNoDirect'), cls: 'state-partial' };
}

function renderGroundingSourcePanel(metadata) {
    const m = metadata || {};
    const manual = Array.isArray(m.grounding_sources) ? m.grounding_sources.some((src) => src && (src.source_title || src.source_file || src.source_date)) : false;
    const lawAttempted = Boolean(m.law_grounding_attempted);
    const lawUsed = Boolean(m.law_grounding_used);
    // Coarse, non-secret status: not_attempted / disabled / unavailable / used.
    const lawStatus = m.law_grounding_status ? String(m.law_grounding_status) : '';
    const lawWarnings = Array.isArray(m.law_grounding_warnings) ? m.law_grounding_warnings : [];
    const hasCitation = Boolean(m.citation_verification);
    const citationStatus = m.citation_verification && m.citation_verification.status ? String(m.citation_verification.status) : '';
    const hasPublicData = Array.isArray(m.public_data_grounding) ? m.public_data_grounding.length > 0 : Boolean(m.public_data_grounding);
    const hasVariantContext = Boolean(m.procedure_variant_context_used) || (Array.isArray(m.procedure_variant_context_sources) && m.procedure_variant_context_sources.length > 0);
    const variantSources = Array.isArray(m.procedure_variant_context_sources) ? m.procedure_variant_context_sources : [];

    // Honest disclosure state classes — mirror docs/ai/CITATION_AND_UNCERTAINTY_SCHEMA.md states.
    // CSS in the STRUCTURAL RESULT-CARD HIERARCHY v2 layer styles gp-row.state-*.
    const rows = [];

    // Answer-basis row (answer-quality contract). A single compact line that
    // tells the user how strongly the answer is grounded — high/moderate/low —
    // without repeating the long disclaimers below. Distinct from per-source
    // rows: it summarizes source STATE, not an individual source.
    const qualityMode = m.answer_quality_mode ? String(m.answer_quality_mode) : '';
    const QUALITY_TEXT = {
        source_confirmed: { key: 'aiAnswerBasisConfirmed', cls: 'state-verified' },
        source_assisted: { key: 'aiAnswerBasisAssisted', cls: 'state-partial' },
        source_limited: { key: 'aiAnswerBasisLimited', cls: 'state-needs-review' },
        source_unavailable: { key: 'aiAnswerBasisUnavailable', cls: 'state-disabled' },
        generic_advisory: { key: 'aiAnswerBasisGeneric', cls: 'state-advisory' }
    };
    if (QUALITY_TEXT[qualityMode]) {
        const qd = QUALITY_TEXT[qualityMode];
        rows.push(`<div class="gp-row ${qd.cls} gp-row-answer-basis"><strong>${escapeHtml(tx('aiAnswerBasisLabel'))}</strong>: ${escapeHtml(tx(qd.key))}</div>`);
    }

    if (manual) {
        rows.push(`<div class="gp-row state-source-supported"><strong>${escapeHtml(tx('aiManualGroundingLabel'))}</strong>: ${escapeHtml(tx('aiManualGroundingStatus'))}</div>`);
    }
    // Law-grounding status — a single, short, cautious, normalized row
    // (not_attempted / disabled / unavailable / used). Falls back to deriving
    // the state from the older booleans for compatibility. Shown only when the
    // question carried legal/activity-scope intent, so plain questions stay
    // uncluttered. Never implies official legal confirmation unless real law
    // search results were actually used.
    const lawStatusKey = lawStatus || (lawUsed ? 'used' : (lawAttempted ? 'unavailable' : ''));
    // Legacy normalized status keys retained: lawGroundingStatusUsed, lawGroundingStatusDisabled, lawGroundingStatusUnavailable.
    // Verified styling rule retained: if (lawStatusKey === 'used') state-verified; unavailable/disabled are not verified.
    if (lawStatusKey === 'used' || lawStatusKey === 'unavailable' || lawStatusKey === 'disabled') {
        const sourceState = lawSourcePanelText(m, lawStatusKey);
        const lawSourceNames = Array.isArray(m.law_sources)
            ? m.law_sources.filter(function(src) { return src && src.law_name; }).slice(0, 3).map(function(src) { return String(src.law_name); })
            : [];
        const lawSourceNote = lawSourceNames.length ? `<div class="gp-subnote">${lawSourceNames.map(escapeHtml).join(' · ')}</div>` : '';
        const stateSubnote = sourceState.subtext ? `<div class="gp-subnote">${escapeHtml(sourceState.subtext)}</div>` : '';
        const reassureHtml = (!stateSubnote && (lawStatusKey === 'unavailable' || lawStatusKey === 'disabled'))
            ? `<div class="gp-subnote">${escapeHtml(tx('lawGroundingReassure'))}</div>` : '';
        rows.push(`<div class="gp-row ${sourceState.cls}"><strong>${escapeHtml(tx('lawGroundingStatusLabel'))}</strong>: ${escapeHtml(sourceState.text)}${sourceState.subtext ? stateSubnote : lawSourceNote}${reassureHtml}</div>`);
    }
    // Manual-to-law fallback — kept visibly DISTINCT from source-confirmed
    // manual grounding (state-source-supported above) and from needs-review
    // scenario context (state-needs-review below). Shows only when manual
    // document guidance was absent and the system leaned on legal grounding for
    // CONTEXT. Cautious styling; it must never read as a final official decision
    // and never implies a confirmed required-document list.
    if (m.manual_to_law_fallback_used) {
        rows.push(`<div class="gp-row state-partial gp-row-law-fallback"><strong>${escapeHtml(tx('manualToLawFallbackLabel'))}</strong>: ${escapeHtml(tx('manualToLawFallbackChecked'))}<div class="gp-subnote">${escapeHtml(tx('manualToLawFallbackNote'))}</div></div>`);
    }
    if (hasPublicData) {
        rows.push(`<div class="gp-row state-partial"><strong>${escapeHtml(tx('aiPublicDataLabel'))}</strong>: ${escapeHtml(tx('aiPublicDataStatus'))}</div>`);
    }
    if (hasVariantContext) {
        // Up to 4 safe metadata items only (visa_code · procedure_key · label/variant_id · page_range).
        // Raw requiredDocs / manualRefs / full visa_data are never surfaced here.
        const safeSources = variantSources.filter(function(src) { return src && typeof src === 'object'; });
        const shown = safeSources.slice(0, 4);
        const extra = safeSources.length > 4 ? safeSources.length - 4 : 0;
        const itemsHtml = shown.map(function(src) {
            const parts = [];
            if (src.visa_code) parts.push(escapeHtml(String(src.visa_code)));
            if (src.procedure_key) parts.push(escapeHtml(getProcedureLabelByKey(String(src.procedure_key), String(src.procedure_key))));
            const lbl = src.label || src.variant_id;
            if (lbl) parts.push(escapeHtml(String(lbl)));
            if (src.page_range) parts.push(escapeHtml(String(src.page_range)));
            return parts.length ? '<div class="gp-variant-item">' + parts.join(' · ') + '</div>' : '';
        }).join('');
        const moreHtml = extra > 0 ? `<div class="gp-variant-more">${escapeHtml(tx('aiScenarioMoreCount', { count: extra }))}</div>` : '';
        const listHtml = itemsHtml ? '<div class="gp-variant-list">' + itemsHtml + moreHtml + '</div>' : '';
        // Needs-review scenario variants are local manual context only — visibly
        // distinct from source-confirmed grounding and never a final determination.
        const noteHtml = `<div class="gp-variant-note">${escapeHtml(tx('aiScenarioMatchNote'))}</div>`;
        const selectedScenario = Boolean(currentAiSelectedProcedureVariantId && safeSources.some(function(src) { return src.variant_id === currentAiSelectedProcedureVariantId; }));
        const variantTitle = selectedScenario ? tx('aiSelectedScenarioLabel') : tx('aiScenarioGroundingLabel');
        rows.push('<div class="gp-row state-needs-review"><strong>' + escapeHtml(variantTitle) + '</strong>: ' + escapeHtml(tx('aiScenarioCandidateStatus')) + listHtml + noteHtml + '</div>');
    }
    // Related statuses to verify — rendered as DISTINCT chips, never as source
    // grounding. For an H-1 study question, D-2 / D-4 are comparison statuses
    // the user may need to check; they must not look like a manual source that
    // proves what H-1 permits (answer-quality contract, Part F).
    const relatedStatuses = Array.isArray(m.related_statuses_not_sources) ? m.related_statuses_not_sources.filter(Boolean) : [];
    if (relatedStatuses.length) {
        const chips = relatedStatuses.map(function(code) {
            return '<span class="gp-related-chip">' + escapeHtml(String(code)) + '</span>';
        }).join('');
        rows.push(
            '<div class="gp-row state-related gp-row-related"><strong>' + escapeHtml(tx('aiRelatedStatusLabel')) + '</strong>'
            + '<div class="gp-related-chips">' + chips + '</div>'
            + '<div class="gp-subnote">' + escapeHtml(tx('aiRelatedStatusNote')) + '</div></div>'
        );
    }

    // The answer-basis row already conveys the grounding state, so an extra
    // advisory row is only needed when there is no other signal at all.
    const hasSignal = rows.some(function(r) { return r.indexOf('gp-row-answer-basis') === -1 && r.indexOf('gp-row-related') === -1; });
    if (!hasSignal && !QUALITY_TEXT[qualityMode]) {
        // No strong grounding signal — still surface an advisory row so the
        // 1345 / HiKorea / immigration-office disclosure stays visible.
        rows.push(`<div class="gp-row state-advisory"><strong>${escapeHtml(tx('aiAdvisoryLabel'))}</strong>: ${escapeHtml(tx('aiAdvisoryText'))}</div>`);
    }

    // Developer diagnostics (Part G): per-family statuses first, raw codes last.
    // Public-safe contract: raw internal codes (bad_response / not_attempted /
    // statute: family dumps / LAW_API_* warnings) must NOT render for normal
    // users. This block is emitted ONLY when an explicit developer/debug mode is
    // enabled (?debug=1 / ?dev=1, localStorage paradisoDevDiagnostics=1, or
    // window.PARADISO_DEV_DIAGNOSTICS). typeof guards keep it crash-safe.
    let devDiagnosticsEnabled = false;
    try {
        if (typeof window !== 'undefined' && window.PARADISO_DEV_DIAGNOSTICS) devDiagnosticsEnabled = true;
        else if (Visable.state.read(Visable.state.KEYS.devDiagnostics) === '1') devDiagnosticsEnabled = true;
        else if (typeof location !== 'undefined' && location.search && /[?&](?:debug|dev)=1(?:&|$)/.test(location.search)) devDiagnosticsEnabled = true;
    } catch (e) { devDiagnosticsEnabled = false; }
    const familyStatuses = (m.source_family_statuses && typeof m.source_family_statuses === 'object') ? m.source_family_statuses : {};
    const familyLines = Object.keys(familyStatuses).filter(function(f) { return familyStatuses[f]; }).map(function(f) { return f + ': ' + String(familyStatuses[f]); });
    const diagLines = (familyLines.length ? familyLines.concat(['', '--- raw developer codes ---']) : []).concat(lawWarnings);
    const debug = (devDiagnosticsEnabled && (lawWarnings.length || familyLines.length)) ? `<details style="margin-top:.35rem;"><summary>${escapeHtml(tx('aiDeveloperDiagnostics'))}</summary><pre style="white-space:pre-wrap;">${escapeHtml(diagLines.join('\n'))}</pre></details>` : '';
    return `<div class="ai-grounding-panel"><div class="gp-title">${escapeHtml(tx('aiSourcePanelTitle'))}</div><p class="gp-lead">${escapeHtml(tx('aiSourcePanelLead'))}</p>${rows.join('')}${debug}<p class="gp-disclosure">${escapeHtml(tx('aiSourceDisclosure'))}</p></div>`;
}


async function submitAiAnalysis(actionType, btnEl) {
    if (actionType === 'jurisdiction') return openJurisdictionModal();
    if (actionType === 'job_code') return openJobCodeModal();
    const userInput = document.getElementById('aiInput').value.trim();
    if (!userInput) { showToast(tx('aiEmptyInput')); return; }
    const visa = VISA_DATA.find(v => v.code === currentAiVisaCode); if (!visa) return;
    const allBtns = document.querySelectorAll('.ai-action-btn'), resultBox = document.getElementById('aiResult'), spinner = btnEl.querySelector('.spinner');
    allBtns.forEach(b => b.disabled = true); if (spinner) spinner.style.display = 'block'; resultBox.style.display = 'none';

    const isSpecialCat = ['faq', 'scn', 'nhis'].includes(visa.cat);
    let actionDirective = '';
    if (actionType === 'analyze') actionDirective = isSpecialCat ? `[요청 작업] 철저한 법적 판단 및 구제 절차를 검증해 주십시오.` : `[요청 작업] 해당 체류자격을 발급, 연장 또는 변경할 가능성을 객관적으로 평가해 주십시오.`;
    else if (actionType === 'doc_guide') actionDirective = `[요청 작업] 해당 비자의 필수 서류들에 대한 '개념 풀이' 및 발급처를 안내해 주십시오.`;

    if (currentAiController) currentAiController.abort();
    currentAiController = new AbortController();
    const _aiController = currentAiController;
    // Timeout guard so the spinner can never spin forever if the backend /
    // provider hangs. `_didTimeout` distinguishes a timeout abort from a
    // user-initiated one in the catch block below.
    let _didTimeout = false;
    const _timeoutId = setTimeout(() => { _didTimeout = true; _aiController.abort(); }, AI_REQUEST_TIMEOUT_MS);
    try {
        const response = await Visable.data.postRaw(`${API_BASE}/api/ask`, {
                question: userInput,
                consent: true,
                context: actionDirective,
                lang: currentLanguage,
                answer_mode: currentAiAnswerMode,
                // Provider/model routing detail only on the explicit developer opt-in.
                diagnostics: isAiDevDiagnosticsEnabled() || undefined,
                visa_data: {
                    code: visa.code,
                    name: visa.name,
                    cat: visa.cat,
                    period: visa.period || '',
                    newReq: visa.newReq || '',
                    extReq: visa.extReq || '',
                    faq: visa.faq || '',
                    procedures: visa.procedures || null
                },
                ...(currentAiSelectedProcedureKey && currentAiSelectedProcedureVariantId ? {
                    selected_procedure_key: currentAiSelectedProcedureKey,
                    selected_procedure_variant_id: currentAiSelectedProcedureVariantId
                } : {})
            }, { signal: currentAiController.signal });
        // A 503 here is a safe provider state: either no LLM provider is
        // configured, or all OpenRouter model candidates are temporarily
        // unavailable. Show localized, user-friendly copy with sanitized
        // technical details behind a collapsed disclosure — never raw provider
        // JSON, keys, or user ids.
        if (response.status === 503) {
            let detail = {};
            try { const body = await response.json(); detail = (body && body.detail) ? body.detail : (body || {}); } catch (_) { detail = {}; }
            resultBox.innerHTML = buildProviderErrorHtml(detail); resultBox.style.display = 'block';
            return;
        }
        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
        const result = await response.json();
        let formattedText = formatAiModalAnswer(result.copy_safe_answer || result.answer || tx('aiNoResult'));
        // Which provider/model answered is infrastructure detail: it is not shown
        // here (server telemetry + explicit developer diagnostics keep it). Only
        // a limited deterministic answer gets a product-language notice.
        const fallbackNote = (result.deterministic_fallback_answer_used
                // Deterministic fallback is NOT an evidence-grounded model answer.
                // Surface it as a clear status callout (matching the prominence the
                // same state gets on the 503 path) instead of a faint footnote, so
                // the user can tell this is a temporary preparation note. Inline
                // styles reuse the existing theme variables (no new CSS/i18n keys).
                ? `<div class="ai-fallback-note ai-fallback-callout" role="status" style="margin-top:.6rem;padding:.55rem .7rem;border-radius:8px;border:1px solid color-mix(in srgb, var(--color-warning, #b45309) 45%, transparent);background:color-mix(in srgb, var(--color-warning, #b45309) 8%, var(--bg2, #fff));color:var(--t1);font-size:.84rem;line-height:1.5;"><b>${escapeHtml(tx('aiProviderTemporarilyUnavailable'))}</b><br>${escapeHtml(tx('aiFallbackFromMetadata'))}</div>`
                : '');
        const sourcePanel = renderGroundingSourcePanel(result);
        resultBox.innerHTML = formattedText + fallbackNote + sourcePanel; resultBox.style.display = 'block';
    } catch (error) {
        if (error.name === 'AbortError') {
            // Timeout-triggered abort shows a graceful message; a user-initiated
            // abort (new request) stays silent. The spinner is cleared in finally.
            if (_didTimeout) { resultBox.innerHTML = `<b>${escapeHtml(tx('aiTimeout'))}</b>`; resultBox.style.display = 'block'; }
            return;
        }
        resultBox.innerHTML = `<b>${escapeHtml(tx('aiError'))}</b>`; resultBox.style.display = 'block';
    } finally {
        clearTimeout(_timeoutId);
        allBtns.forEach(b => b.disabled = false); if (spinner) spinner.style.display = 'none'; currentAiController = null;
    }
}

// --- Render Doc Checklists ---
// ── Source-grounded document explainer (data/document_help.json) ────────────
let documentHelpData = null;
let documentHelpMatcher = null;
let documentHelpLastTrigger = null;

async function loadDocumentHelp() {
    try {
        const json = await Visable.data.fetchJson(Visable.data.DATA_PATHS.documentHelp).catch(() => null);
        if (!json) return;
        if (!Array.isArray(json) || !window.ParadisoDocumentHelp) return;
        documentHelpData = json;
        documentHelpMatcher = window.ParadisoDocumentHelp.createMatcher(json);
    } catch (e) { /* optional enrichment: requirements must still render */ }
    if (documentHelpMatcher && dataReady && qEl && qEl.value.trim() && document.body.classList.contains('searched')) {
        renderResults(qEl.value.trim());
    }
}

function findDocumentHelp(...candidates) {
    return documentHelpMatcher ? documentHelpMatcher.find(...candidates) : null;
}

function renderDocumentHelpButton(docKey, label, className = '') {
    const record = findDocumentHelp(docKey, label);
    if (!record || !window.ParadisoDocumentHelp) return '';
    const buttonLabel = window.ParadisoDocumentHelp.ui(currentLanguage).open;
    return `<button type="button" class="document-help-trigger${className ? ` ${className}` : ''}" data-action="open-document-help" data-document-help-id="${escapeHtml(record.id)}" aria-haspopup="dialog">${escapeHtml(buttonLabel)}</button>`;
}

function openDocumentHelp(recordId, trigger) {
    const record = findDocumentHelp(recordId);
    const overlay = document.getElementById('documentHelpOverlay');
    const content = document.getElementById('documentHelpContent');
    if (!record || !overlay || !content || !window.ParadisoDocumentHelp) return;
    const isEn = String(currentLanguage || '').toLowerCase().startsWith('en');
    const labels = window.ParadisoDocumentHelp.ui(currentLanguage);
    documentHelpLastTrigger = trigger || document.activeElement;
    document.getElementById('documentHelpTitle').textContent = isEn ? (record.titleEn || record.titleKo) : record.titleKo;
    document.getElementById('documentHelpTitleEn').textContent = isEn ? record.titleKo : (record.titleEn || '');
    document.getElementById('documentHelpKicker').textContent = isEn ? 'Official-source-based document guide' : '공식 출처 기반 문서 안내';
    content.innerHTML = window.ParadisoDocumentHelp.renderPanel(record, currentLanguage);
    overlay.querySelectorAll('[data-action="close-document-help"]').forEach(btn => btn.setAttribute('aria-label', labels.close));
    overlay.classList.add('is-open');
    overlay.setAttribute('aria-hidden', 'false');
    document.body.classList.add('document-help-open');
    const body = document.getElementById('documentHelpBody');
    if (body) body.scrollTop = 0;
    requestAnimationFrame(() => document.getElementById('documentHelpTitle')?.focus());
}

function closeDocumentHelp() {
    const overlay = document.getElementById('documentHelpOverlay');
    if (!overlay || !overlay.classList.contains('is-open')) return;
    overlay.classList.remove('is-open');
    overlay.setAttribute('aria-hidden', 'true');
    document.body.classList.remove('document-help-open');
    const restore = documentHelpLastTrigger;
    documentHelpLastTrigger = null;
    if (restore && typeof restore.focus === 'function' && restore.isConnected) restore.focus();
}

// ── Document preparation guide (data/doc_guide.json) ────────────────────────
// Checklist enrichment only: when the guide file is missing or fails to load,
// docGuideData stays null and checklists render exactly as before.
async function loadDocGuide() {
    try {
        const json = await Visable.data.fetchJson(Visable.data.DATA_PATHS.docGuide).catch(() => null);
        if (!json) return;
        if (json && typeof json === 'object' && !Array.isArray(json)) docGuideData = json;
    } catch (e) { /* optional enhancement — checklist must keep working without it */ }
    // The guide load runs in parallel with visa/API data and is not awaited
    // before initial render. For ?q= deep links, the visa response can win the
    // race and renderDocTags() runs while docGuideData is still null, omitting
    // the guide buttons. If results are already on screen when the guide data
    // arrives, re-render the current query so the buttons appear.
    if (docGuideData && dataReady && qEl && qEl.value.trim() && document.body.classList.contains('searched')) {
        renderResults(qEl.value.trim());
    }
}

// PR-K2 #18 skeleton — conditional-document applicability container.
// Wraps the manual-sourced conditional sentence (결핵·마약검사 등 특정 국적/
// 유형에만 요구되는 서류) together with an applicable-country list slot.
// ── S4 DATA INJECTION POINT ─────────────────────────────────────────────
// The country/eligibility list must come from doc_guide.json (field name:
// applicable_countries) once the 항목 10·17 전수조사 data PR lands. Never
// hand-author country lists here: until the field exists in data this
// renders the conditional sentence plus an empty, hidden list element.
function buildDocGuideApplicability(g, en) {
    const countries = Array.isArray(g.applicable_countries)
        ? g.applicable_countries.map(c => String(c || '').trim()).filter(Boolean)
        : [];
    const listHtml = countries.length
        ? `<ul class="doc-guide-country-list" data-doc-countries>${countries.map(c => `<li>${escapeHtml(c)}</li>`).join('')}</ul>`
        : '<ul class="doc-guide-country-list" data-doc-countries hidden></ul>';
    return `<div class="doc-guide-applicability">
        <p class="doc-guide-conditional">${escapeHtml(currentLanguage === 'zh-CN' ? '有条件提交：' : en ? 'Conditional: ' : '조건부 제출: ')}${escapeHtml(g.conditional)}</p>
        ${listHtml}
    </div>`;
}

function buildDocGuideDrawer(docId, visaCode = '') {
    const g = docGuideData && docGuideData[docId];
    if (!g) return '';
    const en = currentLanguage === 'en';
    const zh = currentLanguage === 'zh-CN';
    const chip = (txt, cls, mark) => `<span class="doc-guide-chip ${cls}"><b aria-hidden="true">${mark}</b>${escapeHtml(txt)}</span>`;
    const accepts = Array.isArray(g.accept) ? g.accept.map(a => chip(a, 'doc-guide-chip--ok', '✓')).join('') : '';
    const rejects = Array.isArray(g.reject) ? g.reject.map(r => chip(r, 'doc-guide-chip--no', '✗')).join('') : '';
    // S3-C1-01: doc_health's sample image is the E-2-only statutory form
    // (별지 제21호의3 회화지도(E-2) 자격 사증신청자 건강확인서). doc_health is a
    // shared health-document concept across 6 statuses, so this form image must
    // render only on E-2; other statuses keep the textual health guidance.
    const imageScopedOut = docId === 'doc_health' && normalizeVisaCode(visaCode) !== 'E-2';
    const img = (g.image_url && !imageScopedOut)
        ? `<figure class="doc-guide-figure"><img src="${escapeHtml(g.image_url)}" alt="${escapeHtml((zh ? '官方表格示例' : en ? 'Official form example' : '공식 서식 예시'))}" loading="lazy"><figcaption>${escapeHtml(zh ? '出入境管理法施行规则别纸表格（真本）' : en ? 'Official statutory form (Enforcement Rule annex)' : '출입국관리법 시행규칙 별지 서식 (진본)')}</figcaption></figure>`
        : '';
    // Source line renders unconditionally — a guide without provenance must
    // surface as "needs verification" rather than silently looking authoritative.
    const sourceText = g.source || (zh ? '出处待人工核实' : en ? 'Source pending manual verification' : '출처 확인 필요 (사람 검수 대상)');
    return `<div class="doc-guide-drawer" data-doc-guide="${escapeHtml(docId)}" hidden>
        ${g.spec ? `<p class="doc-guide-spec">${escapeHtml(g.spec)}</p>` : ''}
        ${(accepts || rejects) ? `<div class="doc-guide-chips">${accepts}${rejects}</div>` : ''}
        ${g.tip ? `<p class="doc-guide-tip">💡 ${escapeHtml(g.tip)}</p>` : ''}
        ${g.conditional ? buildDocGuideApplicability(g, en) : ''}
        ${img}
        <p class="doc-guide-source">${escapeHtml(zh ? '出处：' : en ? 'Source: ' : '출처: ')}${escapeHtml(sourceText)}</p>
    </div>`;
}

function toggleDocGuide(btn) {
    const tile = btn.closest('.doc-chk-item');
    const drawer = tile && tile.nextElementSibling;
    if (!drawer || !drawer.classList.contains('doc-guide-drawer')) return;
    const open = drawer.hidden;
    drawer.hidden = !open;
    btn.setAttribute('aria-expanded', String(open));
    btn.classList.toggle('is-open', open);
}

function renderDocTags(docKeys, keywords, isSubCode = false, visaCode = '', procedureKey = '') {
    // Defense-in-depth: never emit placeholder/diagnostic stand-ins as checklist
    // rows even if an upstream path bypassed dedupeDocs().
    const dedupedSections = dedupeDocumentSectionsForDisplay([{ key: 'flat', docs: docKeys || [] }]);
    const cleanKeys = (dedupedSections[0]?.docs || []).filter(key => String(key || '').trim() && !isDocPlaceholder(key));
    if (!cleanKeys.length) return `<div class="text-desc" style="color:var(--t3);">${currentLanguage === 'zh-CN' ? '无需额外材料。' : currentLanguage === 'en' ? 'No additional documents required.' : '요구되는 추가 서류가 없습니다.'}</div>`;
    // Explanatory prose that was authored inside a document array is relocated
    // here (rendered as a note) instead of being shown as a fake checklist tile.
    const relocatedNotes = [];
    const tagsHtml = cleanKeys.map(key => {
        // Resolve every doc id through DOC_DICT (kept in sync with doc_master.json).
        // Unknown ids must never surface their raw machine id to users — show a
        // friendly "문서 정의 필요" label and stash the raw id in a debug-only
        // data attribute so developers can still trace it.
        const isUnresolvedId = typeof key === 'string' && key.startsWith('doc_') && !DOC_DICT[key];
        let officialName = DOC_DICT[key] || (isUnresolvedId ? (tx('docDefinitionNeeded') || '문서 정의 필요') : key);
        // Split off prose / over-long example text so only the concise document
        // name renders as a checklist tile (source wording preserved as a note).
        if (!isUnresolvedId) {
            const split = paradisoSplitDocItem(officialName);
            if (split.kind === 'prose') {
                if (split.note) relocatedNotes.push(split.note);
                return '';
            }
            if (split.label) {
                officialName = split.label;
                if (split.note) relocatedNotes.push(split.note);
            }
        }
        // Application-form wording ("신청서" → "통합신청서 …", F-4 → 재외동포
        // 통합신청서 별지 제1호) is applied here, at the render source, using the
        // procedure the tile belongs to. Source data is never mutated.
        if (!isUnresolvedId && typeof paradisoCanonicalAppFormText === 'function') {
            officialName = paradisoCanonicalAppFormText(officialName, procedureKey, normalizeVisaCode(visaCode));
        }
        // Non-Korean locales: append a glossary translation after the
        // canonical Korean name (data/i18n/official-terms.json) — official
        // names are never invented, only reused from that glossary. By
        // product decision, this also shows fallback/needs-verification-tier
        // translations (not just confirmed ones); this plain-text path (kept
        // this way because the result flows through hl(), which re-escapes
        // any HTML) cannot show the dotted "unverified" marker the other two
        // surfaces (renderAnnotatedDocLabel) use — a known, accepted gap.
        // Tries the doc_*-id index first (exact term binding); if that finds
        // nothing, falls back to the same text/family-based lookup the
        // Standard 구비서류 tabs and Easy Mode use, so the identical document
        // reads the same bilingual way wherever it appears on the site.
        if (!isUnresolvedId) {
            const beforeGlossary = officialName;
            if (typeof key === 'string' && key.startsWith('doc_') && typeof annotateOfficialDocLabel === 'function') {
                officialName = annotateOfficialDocLabel(key, officialName);
            }
            if (officialName === beforeGlossary && typeof findOfficialTermIdForKoreanLabel === 'function') {
                const fallbackTermId = findOfficialTermIdForKoreanLabel(officialName);
                const fallbackTranslation = fallbackTermId ? officialTermTranslation(fallbackTermId) : null;
                if (fallbackTranslation && !officialName.toLowerCase().includes(fallbackTranslation.toLowerCase())) {
                    officialName = officialName + ' (' + fallbackTranslation + ')';
                }
            }
        }
        // D6 (항목 16): the foreign-resident occupation/income report moved to
        // HiKorea online filing (외국인 취업정보 온라인 신고제, 2026-01-02 시행;
        // 시범운영 ~2026.6, then online-only — 법무부 2025-12-16 보도). Surface
        // that as a checklist note wherever the 직업 신고서 tile renders.
        if (/직업\s*신고서/.test(String(officialName))) {
            relocatedNotes.push(currentLanguage === 'zh-CN'
                ? '外国人职业·年收入申报通过 HiKorea（hikorea.go.kr）线上办理（外国人就业信息线上申报制）。'
                : currentLanguage === 'en'
                ? 'The foreign-resident occupation/income report is filed online via HiKorea (hikorea.go.kr).'
                : '외국인 직업·연간소득 신고는 하이코리아(hikorea.go.kr) 온라인으로 처리합니다 (외국인 취업정보 온라인 신고제).');
        }
        const debugAttr = isUnresolvedId ? ` data-doc-id="${escapeHtml(key)}"` : '';
        const isCritical = ['doc_health', 'doc_crim', 'doc_tb'].includes(key);
        const criticalClass = isCritical ? ' critical' : '';
        // Long manual excerpts shouldn't become an oversized card squeezed into
        // one grid cell — flag them so CSS can let them span the full row.
        const blockClass = String(officialName).length > 80 ? ' doc-chk-item--block' : '';
        const iconHtml = isCritical ? `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" aria-hidden="true"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>` : `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" aria-hidden="true"><polyline points="20 6 9 17 4 12"/></svg>`;
        const documentHelpBtnHtml = !isUnresolvedId ? renderDocumentHelpButton(key, officialName) : '';
        const guideAvailable = !documentHelpBtnHtml && !isUnresolvedId && docGuideData && docGuideData[key];
        const guideBtnHtml = documentHelpBtnHtml || (guideAvailable ? `<button type="button" class="doc-guide-toggle" data-action="toggle-doc-guide" aria-expanded="false">${currentLanguage === 'zh-CN' ? '指南' : currentLanguage === 'en' ? 'Guide' : '가이드'}</button>` : '');
        const guideDrawerHtml = guideAvailable ? buildDocGuideDrawer(key, visaCode) : '';
        return `<div class="doc-chk-item${criticalClass}${blockClass}${isUnresolvedId ? ' doc-chk-item--undefined' : ''}"${debugAttr}>${iconHtml}<span>${hl(officialName, keywords)}</span>${guideBtnHtml}</div>${guideDrawerHtml}`;
    }).join('');
    const warningHtml = isSubCode ? `<div class="subcode-warning">${escapeHtml(tx('manualNeedsReview'))}: ${escapeHtml(txAt('docUxGroupLabels', 1, '상황별 추가 서류'))}</div>` : '';
    // De-duplicate relocated notes (canonicalized) and render them under the
    // checklist as supplementary guidance, never as required-document rows.
    const noteSeen = new Set();
    const noteItems = relocatedNotes.filter(n => {
        if (paradisoIsRedundantSourceProvenanceNote(n)) return false;
        const k = canonicalDocDedupeKey(n);
        if (!k || noteSeen.has(k)) return false;
        noteSeen.add(k);
        return true;
    });
    const notesHtml = noteItems.length
        ? `<ul class="doc-checklist-notes" aria-label="${escapeHtml(currentLanguage === 'zh-CN' ? '参考事项' : currentLanguage === 'en' ? 'Notes' : '참고 사항')}">${noteItems.map(n => `<li>${hl(escapeHtml(n), keywords)}</li>`).join('')}</ul>`
        : '';
    const checklistHtml = tagsHtml ? `<div class="doc-checklist">${tagsHtml}</div>` : '';
    return `<div class="doc-req-box" style="margin-top:0; padding:0; border:none; background:transparent;">${warningHtml}${checklistHtml}${notesHtml}</div>`;
}


export {
    openModal, closeModal, openVisaDrawer, closeVisaDrawer, setupAiModeSelector, findProcedureVariant,
    openAiModal, buildWaymakerHandoffUrl, syncWaymakerFab, setSelectedScenarioHandoff, clearSelectedScenarioHandoff, handleScenarioAiHandoff,
    openDocModal, renderSubcodeProcedureVariants, buildSubcodeModalView, openSubcodeModal, renderModalFeeBox, openFaqModal,
    fallbackCopy, isAiDevDiagnosticsEnabled, formatAiModalAnswer, buildProviderErrorHtml, mapLawWarningToFriendly, sourcePanelCopyForState,
    lawSourcePanelText, renderGroundingSourcePanel, submitAiAnalysis, loadDocumentHelp, findDocumentHelp, renderDocumentHelpButton,
    openDocumentHelp, closeDocumentHelp, loadDocGuide, buildDocGuideApplicability, buildDocGuideDrawer, toggleDocGuide,
    renderDocTags
};
