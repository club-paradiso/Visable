// @ts-nocheck
/**
 * Document tabs, the source-evidence panel, the caution block, easy mode and the card view modes of the legacy
 * per-status card (structure map C24–C25). Kept inline in index.html: `DOCUMENT_TAB_CONFIG` (read at run time by
 * tests/e2e/bilingual-doc-names.spec.mjs and the inline code), `EASY_MODE_VIEW_MODES`, `EASY_MODE_CARD_STATE`,
 * `EASY_MODE_PREF_KEY`, `EASY_MODE_CAUTION_ROW_RE` (read by inline code at call time) and `let globalEasyMode`
 * (assigned by the inline code and initialised from localStorage at parse time, ADR-009 correction). This module reads
 * those by bare name (global lexical scope) and uses tx(), escapeHtml(), hl(), showToast(), Visable.state and the
 * Visable.docs stubs at call time only. Covered by tests/golden/specs/legacy-card.spec.mjs (card modes, document tabs).
 * Moved verbatim from index.html lines 17798-18326 (517 lines; kept inline: ['DOCUMENT_TAB_CONFIG', 'EASY_MODE_CARD_STATE', 'EASY_MODE_CAUTION_ROW_RE', 'EASY_MODE_PREF_KEY', 'EASY_MODE_VIEW_MODES', 'globalEasyMode']).
 * Exposed on window.Visable.cards; 12 inline stubs with the same names delegate here.
 */
function renderCautionBlock() {
    return `<div class="vc-caution">${escapeHtml(tx('cautionText'))}</div>`;
}

// Localized document-tab stage label (falls back to the Korean default in the
// config). Official Korean *document item* text is never translated here.
function getDocumentTabLabel(cfg) {
    return txAt('documentTabLabels', cfg.labelIndex, cfg.label);
}

const DOCUMENT_DATA_MISSING_NOTICE = '구조화 서류 데이터 없음: 이 절차의 구비서류는 아직 Visable 구조화 데이터에 충분히 정리되어 있지 않습니다. 최신 체류·사증 민원 안내매뉴얼 또는 관할 출입국·외국인관서를 확인하세요.';
const DOCUMENT_REGISTRATION_MISSING_NOTICE = '구조화 서류 데이터 없음: 이 절차의 구비서류는 아직 Visable 구조화 데이터에 충분히 정리되어 있지 않습니다. 최신 체류·사증 민원 안내매뉴얼 또는 관할 출입국·외국인관서를 확인하세요.';

function isDocFieldMissing(field) {
    if (field === 'DATA_MISSING' || field == null) return true;
    if (Array.isArray(field) && field.length === 0) return true;
    return false;
}

function formatDocumentTabRefNote(refs) {
    if (!Array.isArray(refs) || !refs.length) return '';
    const bits = refs.map(ref => {
        const sourceDate = ref.sourceDate || ref.sourceRevisionDate || ref.revisionDate || '';
        const versionLabel = sourceDate ? `${ref.manualVersion || ref.version || '2026.9'} (${sourceDate})` : (ref.manualVersion || ref.version || '2026.9');
        return [ref.manualName || ref.manual || '체류민원', versionLabel, ref.pageRange || '페이지 확인 필요'].filter(Boolean).join(' · ');
    });
    return `${txAt('issuanceUiLabels', 9, '출처')}: ${bits.join(' / ')}`;
}

// Note: label map not used here — doc_* IDs in item.name or item.label would render as raw strings
function normalizeDocumentTabItems(field) {
    // items are pre-resolved Korean labels, DOC_DICT not needed
    if (isDocFieldMissing(field) || !Array.isArray(field)) return [];
    return field.map(item => {
        let name, note;
        if (typeof item === 'string') { name = item; note = ''; }
        else if (!item || typeof item !== 'object') return null;
        else { name = item.name || item.label || item.title || 'DATA_MISSING'; note = item.note || item.description || ''; }
        // Keep prose / over-long example text out of the document name; relocate
        // it into the note so the row reads as one concrete document.
        if (name && name !== 'DATA_MISSING') {
            const split = paradisoSplitDocItem(name);
            if (split.kind === 'prose') {
                // No concrete document name — render as a note-only row.
                const merged = [split.note, note].filter(Boolean).join(' / ');
                return { name: '', note: merged, isNote: true };
            }
            if (split.label) {
                name = split.label;
                if (split.note) note = [split.note, note].filter(Boolean).join(' / ');
            }
        }
        return { name, note };
    }).filter(item => item && ((item.name && !isDocPlaceholder(item.name)) || (item.isNote && item.note)));
}

function getRegistrationProcedureTabItems(v) {
    const registrationCfg = PROCEDURE_CONFIG.find(p => p.key === 'registration');
    if (!registrationCfg) return [];
    const proc = getProcedure(v, registrationCfg);
    const docs = flattenDocGroups(proc.docs).filter(doc => !isDocPlaceholder(doc));
    if (!docs.length) return [];
    const refNote = formatDocumentTabRefNote(proc.manualRefs);
    // Unresolved doc_* IDs fall back to a safe generic label (tx('docDefinitionNeeded'))
    // instead of surfacing the raw ID to users.
    return docs.map(doc => ({
        name: DOC_DICT[doc] || tx('docDefinitionNeeded'),
        note: refNote || proc.summary || ''
    }));
}

function getDocumentTabItems(v, cfg) {
    const directItems = normalizeDocumentTabItems(v[cfg.field]);
    if (directItems.length) return paradisoMergeDocumentTabItemsForDisplay(directItems);
    if (cfg.key === 'registration') return paradisoMergeDocumentTabItemsForDisplay(getRegistrationProcedureTabItems(v));
    return [];
}

function getDocumentMissingNotice(panelKey) {
    // Localized for the four main languages; falls back to the Korean constant.
    return tx('docTabMissingNotice') || (panelKey === 'registration' ? DOCUMENT_REGISTRATION_MISSING_NOTICE : DOCUMENT_DATA_MISSING_NOTICE);
}

function renderDocumentTabPanel(v, cfg, isActive) {
    const items = getDocumentTabItems(v, cfg);
    // Procedure-scoped, source-honest limitation note (NEVER show repeated
    // generic missing-data tiles such as "문서명 미상" / "비고 정보 없음" as
    // user-facing content — the static visa result rendering contract treats
    // those as quality regressions).
    const bodyHtml = !items.length
        ? `<div class="docs-missing-notice" role="note">${escapeHtml(getDocumentMissingNotice(cfg.key))}</div>`
        : `<ol class="docs-list">${items.map(item => {
            const rawName = paradisoCanonicalAppFormText((item && item.name) || '',
                cfg.key === 'initial' ? 'visaIssuance' : cfg.key, normalizeVisaCode(v && v.code));
            const rawNote = (item && item.note) || '';
            const nameIsMissing = !rawName || rawName === 'DATA_MISSING';
            // Prose that carried no concrete document name is rendered as a
            // note-only row instead of a fake checklist line.
            if (nameIsMissing && item && item.isNote && rawNote && rawNote !== 'DATA_MISSING') {
                return `<li class="docs-list-row docs-list-row--note"><div class="docs-list-note">${renderManualDetailBlock(rawNote, [], 120)}</div></li>`;
            }
            // Skip rows whose document name is missing — rendering "문서명 미상"
            // as if it were a checklist line is misleading.
            if (nameIsMissing) return '';
            // A pure caution marker (e.g. "체류민원 기준 주의") is not a
            // submittable document; showing it with a checkmark bullet next to
            // real documents misrepresents it as one regardless of view. Easy
            // Mode already excludes these (isEasyModeNonDocRow) — apply the
            // same caution-row check here so Standard view doesn't show it as
            // a fake checklist tile either. Fee rows are untouched: Standard
            // view intentionally keeps those visible with their own note.
            if (EASY_MODE_CAUTION_ROW_RE.test(rawName)) {
                return rawNote && rawNote !== 'DATA_MISSING'
                    ? `<li class="docs-list-row docs-list-row--note"><div class="docs-list-note">${renderManualDetailBlock(rawNote, [], 120)}</div></li>`
                    : '';
            }
            const noteIsMissing = !rawNote || rawNote === 'DATA_MISSING';
            const helpButton = renderDocumentHelpButton(rawName, rawName);
            // helpButton keeps the pure Korean rawName for its own lookup;
            // only the visible label gets the glossary-verified translation.
            const nameHtml = `<div class="docs-list-name-row"><div class="docs-list-name">${renderAnnotatedDocLabel(rawName)}</div>${helpButton}</div>`;
            // Drop the empty "비고 정보 없음" placeholder entirely; rendering
            // an explicit "no note" row buries the actual document name.
            const noteHtml = noteIsMissing
                ? ''
                : `<div class="docs-list-note">${renderManualDetailBlock(rawNote, [], 120)}</div>`;
            return `<li class="docs-list-row">${nameHtml}${noteHtml}</li>`;
        }).filter(Boolean).join('')}</ol>`;
    return `<div class="docs-panel${isActive ? ' active' : ''}" data-docs-panel="${cfg.key}" role="tabpanel">${bodyHtml}</div>`;
}

// True when the procedure-first section (renderProcedures) already renders a
// checklist for this visa, so the legacy 구비서류 strip would only duplicate it.
function procedureSectionOwnsDocuments(v) {
    if (!Array.isArray(PROCEDURE_CONFIG)) return false;
    for (const cfg of PROCEDURE_CONFIG) {
        const proc = getProcedure(v, cfg);
        if (!proc || !proc.available || !proc.docs) continue;
        const total = (proc.docs.commonDocs || []).length
            + (proc.docs.requiredDocs || []).length
            + (proc.docs.additionalDocs || []).length
            + (proc.docs.conditionalDocs || []).length;
        if (total > 0) return true;
    }
    return false;
}

function renderDocumentTabs(v) {
    if (['faq', 'scn', 'nhis'].includes(v.cat)) return '';
    const hasAnyField = DOCUMENT_TAB_CONFIG.some(cfg => v[cfg.field] !== undefined);
    if (!hasAnyField) return '';
    // De-duplicate against 절차별 안내: when the procedure-first section already
    // owns the document checklists, do NOT render a parallel 구비서류 strip as
    // a second authoritative surface. The procedure-scoped 구비서류 확인 CTA
    // still deep-links into the procedure panel that owns the documents.
    if (procedureSectionOwnsDocuments(v)) return '';
    // Only render tabs whose underlying field actually yields document items —
    // skip the empty 구조화 서류 데이터 없음 panels so the section is not
    // dominated by repeated missing-data notices.
    const tabsWithItems = DOCUMENT_TAB_CONFIG.filter(cfg => getDocumentTabItems(v, cfg).length > 0);
    if (!tabsWithItems.length) {
        return `<section class="manual-section docs-section docs-section-limited" aria-label="${escapeHtml(tx('documentSectionTitle'))}">
            <h4 class="manual-section-title">${escapeHtml(tx('documentSectionTitle'))}</h4>
            <div class="docs-missing-notice" role="note">${escapeHtml(getDocumentMissingNotice(DOCUMENT_TAB_CONFIG[0].key))}</div>
        </section>`;
    }
    const firstKey = tabsWithItems[0].key;
    const tabsHtml = tabsWithItems.map(cfg => {
        const isActive = cfg.key === firstKey;
        return `<button type="button" class="docs-tab${isActive ? ' active' : ''}" data-action="select-docs-tab" data-docs-tab="${cfg.key}" role="tab" aria-selected="${isActive ? 'true' : 'false'}"><span class="docs-tab-icon" aria-hidden="true">${cfg.icon}</span><span class="docs-tab-label">${escapeHtml(getDocumentTabLabel(cfg))}</span></button>`;
    }).join('');
    const panelsHtml = tabsWithItems.map(cfg => renderDocumentTabPanel(v, cfg, cfg.key === firstKey)).join('');
    return `<section class="manual-section docs-section" aria-label="${escapeHtml(tx('documentSectionTitle'))}">
        <h4 class="manual-section-title">${escapeHtml(tx('documentSectionTitle'))}</h4>
        <div class="docs-tabs" role="tablist">${tabsHtml}</div>
        <div class="docs-panels">${panelsHtml}</div>
    </section>`;
}

function activateDocsTab(section, targetKey) {
    if (!section || !targetKey) return;
    const tabs = Array.from(section.querySelectorAll('.docs-tab'));
    const hasTarget = tabs.some(btn => btn.dataset.docsTab === targetKey);
    if (!hasTarget) return;
    tabs.forEach(btn => {
        const active = btn.dataset.docsTab === targetKey;
        btn.classList.toggle('active', active);
        btn.setAttribute('aria-selected', active ? 'true' : 'false');
    });
    section.querySelectorAll('.docs-panel').forEach(panel => {
        panel.classList.toggle('active', panel.dataset.docsPanel === targetKey);
    });
    section.dataset.activeDocsTab = targetKey;
}

function renderSourceEvidencePanel(v) {
    if (['faq', 'scn', 'nhis'].includes(v.cat)) return '';
    const status = v.sourceManualStatus || {};
    const domains = getManualDomains(v);
    const issuanceBinding = getVisaIssuanceBinding(v.code);
    const hasVisa = domains.includes('visa_issuance');
    const hasStay = domains.includes('stay_sojourn');
    const isVerified = status.verified === true && !status.needsManualReview;
    const pendingReview = status.needsManualReview === true;
    const hasManualLinked = hasVisa || hasStay;
    const hasPageHint = Array.isArray(v.manualRefs) && v.manualRefs.some(ref => !!(ref && (ref.pageRange || ref.page || ref.section)));
    const isProvisional = (String(v.procedureNote || '').includes('준용') || String(v.note || '').includes('준용'));
    let badges = `<span class="sep-badge structured">${escapeHtml(tx('sourceStructuredData'))}</span>`;
    if (isVerified) badges += `<span class="sep-badge visa-manual">${escapeHtml(tx('sourceManualConfirmed'))}</span>`;
    if (pendingReview) badges += `<span class="sep-badge unverified">${escapeHtml(tx('sourceManualPending'))}</span>`;
    if (!hasManualLinked && hasPageHint) badges += `<span class="sep-badge source-linked-unverified">${escapeHtml(tx('sourceNeedLinking'))}</span>`;
    if (isProvisional) badges += `<span class="sep-badge source-linked-unverified">${escapeHtml(tx('sourceProvisional'))}</span>`;
    if (hasVisa) badges += `<span class="sep-badge visa-manual">${escapeHtml(tx('sourceVisaManual'))}</span>`;
    if (hasStay) badges += `<span class="sep-badge stay-manual">${escapeHtml(tx('sourceStayManual'))}</span>`;
    if (issuanceBinding) badges += `<span class="sep-badge ${escapeHtml(getSourceEvidenceBadgeClass(issuanceBinding.evidenceLevel))}">${escapeHtml(`${txAt('issuanceUiLabels', 0, '사증발급')}: ${getSourceEvidenceLabel(issuanceBinding.evidenceLevel)}`)}</span>`;
    if (!isVerified) badges += `<span class="sep-badge unverified">${escapeHtml(tx('sourceUnverified'))}</span>`;
    const noteKey = isVerified
        ? 'sourceVerifiedNote'
        : (pendingReview ? 'sourcePendingReviewNote' : (hasPageHint ? 'sourceNeedLinkingNote' : 'sourceUnverifiedNote'));
    const provisionalNote = isProvisional ? `<p class="sep-note">${escapeHtml(tx('sourceProvisionalNote'))}</p>` : '';
    const issuanceNote = issuanceBinding ? `<p class="sep-note">${escapeHtml((issuanceBinding.userFacingExplanationKo || issuanceBinding.limitationReasonKo || getDefaultLimitationExplanation(issuanceBinding.evidenceLevel)))}</p>` : '';
    const noteHtml = `<p class="sep-note">${escapeHtml(tx(noteKey))}</p>${issuanceNote}${provisionalNote}`;
    return `<details class="source-evidence-panel">
        <summary><span class="sep-title">${escapeHtml(tx('sourceEvidenceTitle'))}</span><span class="sep-chevron">▾</span></summary>
        <div class="sep-body"><div class="sep-badges">${badges}</div>${noteHtml}</div>
    </details>`;
}

/* ===== Easy Mode (쉬운 안내) ===============================================
   A user-facing accessibility view that re-explains the status detail in
   short, plain, action-oriented language. It sits BESIDE the Standard and
   Official Source views as a 3-way per-card toggle and never replaces official
   guidance. Every label/copy string is resolved through tx() from
   data/i18n/*.json (no hardcoded multilingual UI text here); the dynamic parts
   (summary, document names) are DERIVED from the existing status record at
   render time, so no canonical data is duplicated, invented, or mutated.
   Accuracy contract: the summary resolves through the same chain as the
   compact card (summary → newReq → extReq), and document names are grouped
   per procedure stage under the Standard view's own stage labels — stages are
   never merged into one flat list (procedure-scope rule). The
   selected view is remembered per code (EASY_MODE_CARD_STATE) and re-applied
   after renderResults() rebuilds the list — including on a language switch, so
   switching language while Easy Mode is active keeps Easy Mode and updates the
   visible copy. */
const EASY_MODE_SKIP_CATS = ['faq', 'scn', 'nhis'];

function easyModeApplies(v, isVisaCode) {
    return !!isVisaCode && !!v && !EASY_MODE_SKIP_CATS.includes(v.cat);
}

function renderViewModeToggle(v, isVisaCode) {
    if (!easyModeApplies(v, isVisaCode)) return '';
    // Toggle-button group, NOT tabs: the three views swap the whole card body,
    // there are no persistent tabpanels to wire aria-controls to, and the old
    // role="tablist"/role="tab" markup lacked the roving tabindex + arrow-key
    // behaviour that role obliges — screen readers announced tabs that did not
    // behave like tabs. Buttons with aria-pressed are natively keyboardable.
    const btn = (mode, key, selected) =>
        `<button type="button" class="view-mode-btn${selected ? ' active' : ''}" data-action="set-card-mode" data-card-mode="${mode}" aria-pressed="${selected ? 'true' : 'false'}">${escapeHtml(tx(key))}</button>`;
    return `<div class="view-mode-toggle">
        <span class="view-mode-label">${escapeHtml(tx('easyModeLabel'))}</span>
        <div class="view-mode-btns" role="group" aria-label="${escapeHtml(tx('easyModeToggleAria'))}">
            ${btn('standard', 'easyModeStandard', true)}${btn('easy', 'easyModeEasy', false)}${btn('official', 'easyModeOfficial', false)}
        </div>
    </div>`;
}

/* Rows the Standard document tabs carry that are NOT submittable documents —
   fee lines and caution markers. The Standard view keeps them (they render
   with their notes/context); the Easy view must not present them as
   "documents to prepare". Render-time filter only — data untouched. */
const EASY_MODE_FOOTNOTE_MARK_RE = /[\s*＊]+$/;
function isEasyModeNonDocRow(name) {
    // Fee rows reuse the same '수수료' family classifier the Standard checklist
    // dedupe already relies on, so 정부수입인지/인지대 variants are caught too
    // and the two views cannot drift on what counts as a fee.
    return normalizeDocumentRequirementKey(name) === '수수료' || EASY_MODE_CAUTION_ROW_RE.test(name);
}
// Trailing footnote markers ("체류지 입증서류*") point at footnotes the Easy
// view does not render; strip the dangling marker, keep the document name.
function cleanEasyModeDocName(raw) {
    return String(raw || '').replace(EASY_MODE_FOOTNOTE_MARK_RE, '').trim();
}

const EASY_MODE_DOCS_PER_STAGE = 5;
/* Stage-scoped document names the Standard view already surfaces for this
   status. Each group keeps the SAME localized stage label the Standard view
   uses, and stages are never merged: 사증발급/입국 전 documents must not read
   as in-Korea 체류 requirements (procedure-scope rule) — the old flat list did
   exactly that and silently dropped later stages once 8 names accumulated.
   Reuses the existing resolvers so Easy Mode never invents a document or
   asserts a requirement the source data does not already carry. */
function getEasyModeDocGroups(v) {
    const groups = [];
    // procKey: 'initial' tabs are pre-entry (사증발급) documents, so they keep
    // their own wording ('visaIssuance' is skipped by the form-wording rule).
    const addGroup = (label, rawNames, procKey = '') => {
        const seen = new Set();
        const names = [];
        for (const raw of rawNames) {
            const name = paradisoCanonicalAppFormText(cleanEasyModeDocName(raw), procKey, normalizeVisaCode(v && v.code));
            if (!name || seen.has(name) || isDocPlaceholder(name) || isEasyModeNonDocRow(name)) continue;
            seen.add(name);
            names.push(name);
        }
        if (!names.length) return;
        groups.push({
            label,
            names: names.slice(0, EASY_MODE_DOCS_PER_STAGE),
            more: Math.max(0, names.length - EASY_MODE_DOCS_PER_STAGE)
        });
    };
    for (const cfg of DOCUMENT_TAB_CONFIG) {
        addGroup(getDocumentTabLabel(cfg), getDocumentTabItems(v, cfg).map(item => item && item.name),
            cfg.key === 'initial' ? 'visaIssuance' : cfg.key);
    }
    if (!groups.length && Array.isArray(PROCEDURE_CONFIG)) {
        for (const cfg of PROCEDURE_CONFIG) {
            const proc = getProcedure(v, cfg);
            if (!proc || !proc.available) continue;
            // Procedure docs mix doc_* ids and raw Korean bucket strings
            // ("신청서"); resolve through the shared display-label resolver so
            // bucket strings render instead of vanishing, and drop only ids
            // with no DOC_DICT label (rendering a raw doc_* id is worse).
            addGroup(proc.label, flattenDocGroups(proc.docs).map(id => {
                const label = paradisoResolveDocDisplayLabel(id);
                return label.indexOf('doc_') === 0 ? '' : label;
            }), cfg.key);
        }
    }
    return groups;
}

function renderEasyModePanel(v) {
    if (!easyModeApplies(v, true)) return '';
    const code = v.code || '';
    const lang = normalizeLocaleCode(currentLanguage);
    const isKo = lang === 'ko';
    // Localized status name only — never a Korean fallback name in a non-Korean
    // Easy panel. The canonical name/summary always remain in the Standard view.
    let name = '';
    if (isKo) name = getVisaNameKo(v);
    else if (lang === 'en') name = getVisaNameEn(v) || '';
    else name = localizedVisaNameFromPack(v.code, lang) || '';
    // Reading only v.summary (a field no current record carries) made EVERY
    // Easy panel claim "쉬운 안내가 아직 준비되지 않았다" and render a
    // content-free summary; resolve through the shared canonical chain instead.
    const summaryRaw = normalizeManualText(getCanonicalStatusSummarySource(v));
    const hasNativeSummary = !!summaryRaw;
    // The status summary is Korean canonical prose. Show it natively only on the
    // Korean UI; other locales keep the Easy summary in the user's language
    // (generic) and point to the Standard view for the full canonical text — so
    // Easy Mode never dumps untranslated Korean paragraphs into a non-ko panel.
    let summaryText = tx('easyModeSummaryGeneric', { code });
    if (isKo && hasNativeSummary) {
        const sentences = paradisoSplitSentences(summaryRaw);
        const two = sentences.slice(0, 2).join(' ');
        summaryText = (two.length > 240 && sentences.length > 1) ? sentences[0] : two;
    }
    const docGroups = getEasyModeDocGroups(v);
    const koAsk = (UI_TRANSLATIONS.ko && Array.isArray(UI_TRANSLATIONS.ko.easyModeAskAtOffice)) ? UI_TRANSLATIONS.ko.easyModeAskAtOffice : [];

    // The emoji icon is decorative (aria-hidden) — a language-independent
    // visual anchor that helps low-literacy readers find a section again; the
    // localized title remains the accessible name.
    const section = (icon, title, bodyHtml) =>
        `<section class="easy-card"><h4 class="easy-card-title"><span class="easy-card-icon" aria-hidden="true">${icon}</span><span>${escapeHtml(title)}</span></h4>${bodyHtml}</section>`;
    const listFrom = (key, cls) =>
        `<ul class="easy-list ${cls}">${txArray(key).map(s => `<li>${escapeHtml(s)}</li>`).join('')}</ul>`;
    // "누구를 위한 건가요" as short bullet points instead of one long sentence —
    // one idea per line reads far better at low literacy. txArray does not
    // interpolate, so substitute {code} per item here.
    const whoItems = txArray('easyModeWhoList')
        .map(s => `<li>${escapeHtml(String(s).split('{code}').join(code))}</li>`).join('');

    // Documents: grouped per procedure stage under the SAME localized stage
    // label the Standard view uses — never one merged list, so a pre-entry
    // 사증발급 document can't read as an in-Korea 체류 requirement. Only the
    // derived names are concrete; Easy Mode does not classify items as required.
    let docsBody;
    if (docGroups.length) {
        // Document names stay Korean canonical (official terminology is not
        // translated where unverified, per data/i18n policy); lang="ko" marks
        // them so screen readers and the non-ko leak guard treat them correctly.
        // renderAnnotatedDocLabel appends a glossary-verified translation in
        // parens when one exists — its own <span> carries the correct lang
        // override so it reads right even inside this lang="ko" <ul>.
        docsBody = docGroups.map(g => `<div class="easy-doc-group">
            <p class="easy-subtitle">${escapeHtml(g.label)}</p>
            <ul class="easy-list easy-list--check"${isKo ? '' : ' lang="ko"'}>${g.names.map(n => `<li>${renderAnnotatedDocLabel(n)}</li>`).join('')}</ul>
            ${g.more ? `<p class="easy-note">${escapeHtml(tx('easyModeDocsMore', { count: g.more }))}</p>` : ''}
        </div>`).join('')
            + `<p class="easy-note">${escapeHtml(tx('easyModeDocsDependsBody'))}</p>`;
    } else {
        docsBody = `<p class="easy-note">${escapeHtml(tx('easyModeDocsDependsBody'))}</p>
            <p class="easy-note">${escapeHtml(tx('easyModeDocsPointer'))}</p>`;
    }

    // Ask-at-office: show the localized phrase (so the user understands) and,
    // for non-Korean UIs, the Korean canonical line (to show the officer).
    const askItems = txArray('easyModeAskAtOffice').map((phrase, i) => {
        const koLine = (!isKo && koAsk[i] && koAsk[i] !== phrase)
            ? `<span class="easy-ask-ko" lang="ko">${escapeHtml(koAsk[i])}</span>` : '';
        return `<li><span class="easy-ask-local">${escapeHtml(phrase)}</span>${koLine}</li>`;
    }).join('');
    const askKoHint = isKo ? '' : `<p class="easy-note easy-ask-hint">${escapeHtml(tx('easyModeAskAtOfficeShowKo'))}</p>`;

    // Notices key off genuinely-missing summary data, not the non-ko generic path
    // (where the canonical summary still exists in the Standard view).
    const fallbackNotice = !hasNativeSummary ? `<p class="easy-fallback-notice" role="note">${escapeHtml(tx('easyModeFallbackNotice'))}</p>` : '';
    const noData = (!hasNativeSummary && !docGroups.length)
        ? section('ℹ️', tx('easyModeNoDataTitle'), `<p>${escapeHtml(tx('easyModeNoDataBody'))}</p>`) : '';

    // One always-visible escape hatch near the top: the 1345 immigration call
    // line as a tel: button. The site already tells users to call 1345 when
    // unsure — this only makes that advice a one-tap action.
    const callBtn = `<a class="easy-call-btn" href="tel:1345"><span class="easy-call-icon" aria-hidden="true">📞</span><span>${escapeHtml(tx('easyModeCallHelp'))}</span></a>`;

    return `<div class="easy-mode-panel" role="region" aria-label="${escapeHtml(tx('easyModeEasy'))}">
        <p class="easy-notice" role="note">${escapeHtml(tx('easyModeNotice'))}</p>
        ${fallbackNotice}
        ${callBtn}
        ${section('📌', tx('easyModeSummaryTitle'), `<p class="easy-summary"><span class="easy-code">${escapeHtml(code)}</span>${name ? ` <span class="easy-name">${escapeHtml(name)}</span>` : ''}</p><p>${escapeHtml(summaryText)}</p>`)}
        ${noData}
        ${section('🙋', tx('easyModeWhoTitle'), `<p>${escapeHtml(tx('easyModeWhoIntro'))}</p><ul class="easy-list easy-list--bullet">${whoItems}</ul>`)}
        ${section('✅', tx('easyModeNextStepsTitle'), `<ol class="easy-list easy-list--steps">${txArray('easyModeNextSteps').map(s => `<li>${escapeHtml(s)}</li>`).join('')}</ol>`)}
        ${section('📄', tx('easyModeDocumentsTitle'), docsBody)}
        ${section('⚠️', tx('easyModeWarningsTitle'), listFrom('easyModeWarnings', 'easy-list--bullet'))}
        ${section('🗣️', tx('easyModeAskAtOfficeTitle'), `${askKoHint}<ul class="easy-list easy-ask-list">${askItems}</ul>`)}
        ${section('🏛️', tx('easyModeOfficialSourceTitle'), `<p>${escapeHtml(tx('easyModeOfficialSourceBody'))}</p><p class="easy-note">${escapeHtml(tx('easyModeSourceReminder'))}</p><button type="button" class="easy-official-btn" data-action="set-card-mode" data-card-mode="official">${escapeHtml(tx('easyModeOpenOfficialSource'))}</button>`)}
    </div>`;
}

// Apply a view mode to the card DOM (no persistence). Used both for the global
// default and for an explicit per-card choice.
function applyCardMode(card, mode) {
    if (!card) return;
    if (!EASY_MODE_VIEW_MODES.includes(mode)) mode = 'standard';
    EASY_MODE_VIEW_MODES.forEach(m => card.classList.toggle('card-mode-' + m, m === mode));
    card.querySelectorAll('.view-mode-btn').forEach(btn => {
        const active = btn.dataset.cardMode === mode;
        btn.classList.toggle('active', active);
        btn.setAttribute('aria-pressed', active ? 'true' : 'false');
    });
    // The Official Source view surfaces the existing source-evidence panel; open
    // it so the official basis is visible without an extra click.
    if (mode === 'official') {
        const sep = card.querySelector('.source-evidence-panel');
        if (sep) sep.open = true;
    }
}

// Explicit per-card choice (remembered, overrides the global default).
function setCardMode(card, mode) {
    if (!card) return;
    if (!EASY_MODE_VIEW_MODES.includes(mode)) mode = 'standard';
    applyCardMode(card, mode);
    // If the control that triggered this switch got hidden by the view swap
    // (e.g. the Easy panel's "공식 근거 보기" button), keyboard/screen-reader
    // focus would silently drop to <body>; hand it to the always-visible
    // switcher button for the new mode instead.
    const active = document.activeElement;
    if (active && active !== document.body && card.contains(active) && active.getClientRects().length === 0) {
        const switcherBtn = card.querySelector(`.view-mode-btn[data-card-mode="${mode}"]`);
        if (switcherBtn) switcherBtn.focus();
    }
    const code = card.dataset.code;
    if (code) EASY_MODE_CARD_STATE.set(code, mode);
}

function restoreCardViewModes(root) {
    if (!root || !root.querySelectorAll) return;
    const fallback = globalEasyMode ? 'easy' : 'standard';
    root.querySelectorAll('.manual-result').forEach(card => {
        const override = EASY_MODE_CARD_STATE.get(card.dataset.code);
        applyCardMode(card, override || fallback);
    });
}

// Header global Easy Mode toggle: flips the preference, resets per-card overrides
// for a uniform switch, and re-renders so every open card reflects the default.
function updateEasyModeButton() {
    const btn = document.getElementById('easyModeBtn');
    if (!btn) return;
    btn.classList.toggle('is-on', globalEasyMode);
    btn.setAttribute('aria-pressed', globalEasyMode ? 'true' : 'false');
    // Every other global toggle (civic "전체 도구 보기" list, settings dialog) mirrors it.
    document.querySelectorAll('[data-action="toggle-easy-mode"]').forEach(function (el) {
        if (el !== btn) el.setAttribute('aria-pressed', globalEasyMode ? 'true' : 'false');
    });
}
function toggleGlobalEasyMode() {
    globalEasyMode = !globalEasyMode;
    Visable.state.write(EASY_MODE_PREF_KEY, globalEasyMode ? '1' : '0');
    EASY_MODE_CARD_STATE.clear();
    updateEasyModeButton();
    if (document.body.classList.contains('searched') && dataReady) renderResults(qEl ? qEl.value : '');
}

function copyVisaResult(btnEl, code) {
    const v = VISA_DATA.find(x => x.code === code);
    if (!v) return;
    const name = getLocalizedVisaName(v);
    const period = v.period || '';
    const summary = stripManualArtifacts(getCanonicalStatusSummarySource(v));
    const parts = [v.code, name, period ? `(${period})` : '', summary].filter(Boolean);
    const text = parts.join('\n');
    const done = () => {
        const span = btnEl.querySelector('span');
        if (span) { const orig = span.textContent; span.textContent = '✓'; setTimeout(() => { span.textContent = orig; }, 1500); }
        showToast(tx('copySuccess') || '복사했어요.', 'success');
    };
    if (navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText(text).then(done).catch(() => { fallbackCopy(text); done(); });
    else { fallbackCopy(text); done(); }
}

// --- Search Processing Core ---

export {
    renderCautionBlock, getDocumentTabLabel, isDocFieldMissing, formatDocumentTabRefNote, normalizeDocumentTabItems, getRegistrationProcedureTabItems,
    getDocumentTabItems, getDocumentMissingNotice, renderDocumentTabPanel, procedureSectionOwnsDocuments, renderDocumentTabs, activateDocsTab,
    renderSourceEvidencePanel, easyModeApplies, renderViewModeToggle, isEasyModeNonDocRow, cleanEasyModeDocName, getEasyModeDocGroups,
    renderEasyModePanel, applyCardMode, setCardMode, restoreCardViewModes, updateEasyModeButton, toggleGlobalEasyMode,
    copyVisaResult, DOCUMENT_DATA_MISSING_NOTICE, DOCUMENT_REGISTRATION_MISSING_NOTICE, EASY_MODE_SKIP_CATS, EASY_MODE_FOOTNOTE_MARK_RE, EASY_MODE_DOCS_PER_STAGE
};
