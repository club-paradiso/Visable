/* ============================================================================
 * Waymaker Quick Answer — a structured answer composer, not an oracle.
 * ----------------------------------------------------------------------------
 * For question-shaped queries the guidance layer (status-guidance.js) asks this
 * module to compose a brief, validated answer model from the SAME resolver
 * output it renders in full:
 *
 *   query → deterministic extraction (search-router) → resolver (nextStep)
 *         → structured lookup (guidance bundle) → document rules + physical
 *         form → fee registry + exemptions → local-office layer → source
 *         binding → validated Quick Answer model → optional AI wording →
 *         rendered Quick Answer
 *
 * Facts (documents, forms, fees, exemptions, deadlines, offices, eligibility)
 * come only from the bundle. The optional AI step may rephrase the summary
 * sentence; its output is accepted only when validateEnhancement() proves it
 * introduces no number, amount, document, office or form that the model does
 * not already contain. Failure of the AI step never changes the answer.
 *
 * Modes: answer (HIGH) · fee (deterministic fee question) · clarify (MEDIUM:
 * one question) · fallback (LOW: structured evidence only).
 *
 * UMD: globalThis.VisableQuickAnswer in the browser and in Node; module.exports
 * for the Vercel function (api/waymaker/quick-answer.js) which reuses the
 * validator so the server can never return what the client would reject.
 * ========================================================================== */
(function (root) {
  'use strict';

  var COPY = {
    ko: {
      brand: 'Waymaker', badge: '빠른 답', clarifyTitle: '먼저 하나만 확인할게요', clarifyLead: '이 답은 여기에 따라 달라져요.',
      fallbackTitle: '확인된 안내만 보여드려요', fallbackLead: '이 조합은 아직 구조화된 답이 없어 공식 원문으로 안내해요. 아래에서 근거를 확인하세요.',
      prepare: '준비할 것', cost: '비용', office: '관할 관서', national: '전국 기준', officeHas: '{office} · 확인된 차이 있음', officeNone: '{office} · 차이 정보 없음',
      required: '필수 {n}개', conditional: '조건부 {n}개', noDocs: '원문 확인', feeNone: '수수료 없음', feeNotListed: '수수료 항목 없음(확인 필요)', feeConflict: '확인 필요', online: '온라인 −{pct}%',
      full: '전체 안내', evidence: '근거 보기', followup: '이어서 질문하기',
      aiFailed: 'AI 요약을 만들지 못했지만, 확인된 안내는 그대로 볼 수 있어요.',
      focusRequired: '{doc}: 필수예요', focusConditional: '{doc}: 상황에 따라 필요해요', focusMissing: '{doc}: 이 절차의 목록에 없어요', focusForms: '제출 형태: {form}', focusUnspecified: '원문에 원본·사본 표기는 없어요.',
      feeTitle: '{subject} 수수료', feeSentence: '{amount}이에요.', feeSentenceLabel: '{label}은(는) {amount}이에요.', feeInstrument: '납부 방식: {list}.', feeOnlineSentence: '온라인 신청 시 {pct}% 감경돼요.', feeExemptGks: '정부초청장학생(GKS) 면제는 조건부예요: {cond}', feeNoExempt: '면제 근거는 확인되지 않았어요.', feeNoneSentence: '수수료가 없어요.', feeNotListedSentence: '규정에 수수료 항목이 없어요. 별도 수수료가 없는 것으로 보이지만 관서 확인이 필요해요.', feeConflictSentence: '근거마다 달라요: {reg} / {man}. 관서 확인이 필요해요.',
      docsSentence: '필수 {n}개', docsCondSentence: '조건부 {m}개', docsLead: '준비할 서류는 {list}{more}이에요.', more: ' 등 {k}개',
      unc: { review: '2026년 9월판 공식 안내 원문은 아직 검토 전이에요.', feeReview: '수수료 근거에 확인이 필요한 항목이 있어요.', local: '관서 정보 중 확인되지 않은 제보가 있어요. 서류는 전국 기준대로 준비하세요.', forms: '원본·사본 표기가 없는 서류 {n}개는 원본을 지참하면 안전해요.', officer: '심사관이 서류를 가감할 수 있어요.' },
      commonNote: '체류자격과 관계없이 같은 기준이에요.',
    },
    en: {
      brand: 'Waymaker', badge: 'Quick answer', clarifyTitle: 'One quick check first', clarifyLead: 'The answer depends on this.',
      fallbackTitle: 'Showing only what is confirmed', fallbackLead: 'No structured answer exists for this combination yet, so we point to the official source. Check the evidence below.',
      prepare: 'To prepare', cost: 'Cost', office: 'Office', national: 'National baseline', officeHas: '{office} · a reported difference', officeNone: '{office} · no differences on record',
      required: '{n} required', conditional: '{n} conditional', noDocs: 'See source', feeNone: 'No fee', feeNotListed: 'No fee item (confirm)', feeConflict: 'confirm', online: 'online −{pct}%',
      full: 'Full guidance', evidence: 'See evidence', followup: 'Ask a follow-up',
      aiFailed: 'The AI summary could not be generated; the confirmed guidance is shown as is.',
      focusRequired: '{doc}: required', focusConditional: '{doc}: depends on your situation', focusMissing: '{doc}: not on this procedure\'s list', focusForms: 'Submission: {form}', focusUnspecified: 'The source does not say original or copy.',
      feeTitle: '{subject} fee', feeSentence: 'It is {amount}.', feeSentenceLabel: '{label} is {amount}.', feeInstrument: 'Paid by {list}.', feeOnlineSentence: '{pct}% less when filed online.', feeExemptGks: 'The GKS exemption is conditional: {cond}', feeNoExempt: 'No exemption basis was found.', feeNoneSentence: 'There is no fee.', feeNotListedSentence: 'The regulation lists no fee item; there appears to be none, but confirm with the office.', feeConflictSentence: 'Sources disagree: {reg} / {man}. Confirm with the office.',
      docsSentence: '{n} required', docsCondSentence: '{m} conditional', docsLead: 'Prepare {list}{more}.', more: ' and {k} more',
      unc: { review: 'The September 2026 official guides have not yet been reviewed line by line.', feeReview: 'Some fee items need confirmation.', local: 'Some office information is an unverified report. Prepare documents per the national baseline.', forms: '{n} document(s) have no original/copy marking in the source; bringing originals is safest.', officer: 'The officer may add or waive documents.' },
      commonNote: 'The same rule applies regardless of status.',
    }
  };
  function esc(v) { return String(v == null ? '' : v).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; }); }
  function fmt(s, vars) { return String(s || '').replace(/\{(\w+)\}/g, function (_, k) { return vars && vars[k] != null ? vars[k] : ''; }); }
  function t(lang, key, vars) { var p = COPY[lang] || COPY.ko; var v = p[key] != null ? p[key] : COPY.ko[key]; return typeof v === 'string' ? fmt(v, vars) : v; }
  function L(lang, obj, k) { return lang === 'en' && obj[k + '_en'] ? obj[k + '_en'] : (obj[k + '_ko'] || obj[k + '_en'] || ''); }
  function LL(lang, obj) { return lang === 'en' && obj.en ? obj.en : (obj.ko || obj.en || ''); }
  function won(n) { return '₩' + String(n).replace(/\B(?=(\d{3})+(?!\d))/g, ','); }
  function firstSentences(text, max) {
    var parts = String(text || '').replace(/([.。!?])\s+/g, '$1\u0000').split('\u0000');
    var out = '';
    for (var i = 0; i < parts.length; i++) { if ((out + ' ' + parts[i]).trim().length > max && out) break; out = (out + ' ' + parts[i]).trim(); }
    return out || String(text || '').slice(0, max);
  }

  /* ------------------------------------------------------------ model ------ */
  function docName(lang, d) { return lang === 'en' ? (d.name_en || d.name_ko) : d.name_ko; }
  function collectDocuments(model, lang) {
    var out = { required: [], conditional: [], applicableOnly: [], alternatives: [], omittable: [] };
    (model.documentGroups || []).forEach(function (g) {
      g.items.forEach(function (d) {
        var row = { ref: d.ref, name: docName(lang, d), form: d.submission_form || 'SOURCE_DOES_NOT_SPECIFY', copyCount: d.copy_count || null, originalReturned: d.original_returned === undefined ? null : d.original_returned, appliesWhen: L(lang, d, 'applies_when') || null };
        if (d.alternatives && d.alternatives.length) out.alternatives.push({ ref: d.ref, name: row.name, options: d.alternatives.map(function (a) { return LL(lang, a); }) });
        if (g.key === 'required') out.required.push(row);
        else if (g.key === 'conditional') out.conditional.push(row);
        else if (g.key === 'applicable') out.applicableOnly.push(row);
        else if (g.key === 'admin' || g.key === 'prev' || g.key === 'na') out.omittable.push(Object.assign(row, { why: g.key }));
      });
    });
    return out;
  }
  function collectFees(model, lang) {
    var fees = model.fees;
    if (!fees) return [];
    return fees.primary.map(function (f) {
      return { id: f.id, label: lang === 'en' ? f.label_en : f.label_ko, amount: f.amount, amountState: f.amount_state, currency: f.currency, instruments: f.payment_instruments || [], onlineReduction: f.online_reduction ? f.online_reduction.rate : null, review: f.review_state,
        exemptions: (f.exemptions || []).filter(function (e) { return root.VisableStatusGuidance ? root.VisableStatusGuidance.exemptionApplies(e, model.status, model.target, model.userProgram) : true; }).map(function (e) { return { id: e.id, condition: L(lang, e, 'condition'), review: e.review_state, program: e.program || null }; }),
        notExempt: (f.not_exempt || []).map(function (n) { return LL(lang, n); }), conflicts: (f.conflicts || []).map(function (c) { return { regulation: L(lang, c, 'regulation'), manual: L(lang, c, 'manual'), interim: L(lang, c, 'interim') }; }) };
    });
  }
  function collectLocal(model, lang) {
    var lp = model.localPractice || {};
    return { office: lp.office ? { id: lp.office.id, name: lang === 'en' ? lp.office.name_en : lp.office.name_ko } : null,
      variations: (lp.variations || []).map(function (v) { return { id: v.id, layer: v.effectiveLayer, moderation: v.moderation, summary: L(lang, v, 'summary'), lastChecked: v.last_checked || null }; }) };
  }
  function feeSources(bundle, feeModel, lang) {
    var out = []; var seen = {};
    function law(id, claim) { if (!id || !bundle.law_sources || !bundle.law_sources[id] || seen['l' + id]) return; seen['l' + id] = 1; var ls = bundle.law_sources[id]; out.push({ type: 'regulation', title: lang === 'en' ? ls.title_en : ls.title_ko, article: ls.article, url: ls.url, checkedOn: ls.checked_on, claim: claim || null }); }
    function manual(mid, page, claim) { if (!page || seen['m' + page]) return; seen['m' + page] = 1; var meta = bundle.sources[mid] || {}; out.push({ type: 'manual', title: lang === 'en' ? meta.title_en : meta.title_ko, date: meta.date, page: page, file: meta.pdf, review: meta.review_state, claim: claim || null }); }
    feeModel.primary.concat(feeModel.variants).forEach(function (f) {
      law(f.law, f.label_ko); law(f.payment_law); manual(f.manual, f.pdf_page, f.label_ko);
      (f.exemptions || []).forEach(function (e) { law(e.law, e.condition_ko); manual(e.manual || f.manual, e.pdf_page, e.condition_ko); });
      (f.not_exempt || []).forEach(function (n) { law(n.law); manual(n.manual || f.manual, n.pdf_page); });
      if (f.online_reduction) law(f.online_reduction.law);
    });
    return out;
  }
  function collectSources(model, lang) {
    return (model.evidence || []).map(function (e) {
      if (e.type === 'regulation') return { type: 'regulation', title: lang === 'en' ? e.law.title_en : e.law.title_ko, article: e.law.article, url: e.law.url, checkedOn: e.law.checked_on };
      return { type: 'manual', title: lang === 'en' ? e.title_en : e.title_ko, date: e.date, page: e.page, file: e.file, review: e.review || 'needs_review' };
    });
  }
  function collectUncertainties(model, lang, docs) {
    var u = [];
    if ((model.evidence || []).some(function (e) { return e.type === 'manual'; })) u.push({ id: 'review', text: t(lang, 'unc').review });
    if (model.fees && model.fees.primary.some(function (f) { return f.review_state !== 'VERIFIED_REGULATION' && f.review_state !== 'MANUAL_EXPLICIT'; })) u.push({ id: 'fee_review', text: t(lang, 'unc').feeReview });
    if ((model.localPractice && model.localPractice.variations || []).some(function (v) { return /UNVERIFIED|CONFLICTING|STALE/.test(v.effectiveLayer); })) u.push({ id: 'local', text: t(lang, 'unc').local });
    var unspecified = docs.required.filter(function (d) { return d.form === 'SOURCE_DOES_NOT_SPECIFY'; }).length;
    if (unspecified) u.push({ id: 'forms', text: fmt(t(lang, 'unc').forms, { n: unspecified }) });
    if (docs.required.length) u.push({ id: 'officer', text: t(lang, 'unc').officer });
    return u;
  }

  function feeLine(lang, fee) {
    if (!fee) return null;
    if (fee.amountState === 'NO_FEE') return t(lang, 'feeNone');
    if (fee.amountState === 'NOT_LISTED') return t(lang, 'feeNotListed');
    var s = won(fee.amount);
    if (fee.amountState === 'CONFLICT') s += ' · ' + t(lang, 'feeConflict');
    return s;
  }
  function feeSentences(lang, fees, model) {
    var out = [];
    fees.forEach(function (f) {
      if (f.amountState === 'NO_FEE') out.push(t(lang, 'feeNoneSentence'));
      else if (f.amountState === 'NOT_LISTED') out.push(t(lang, 'feeNotListedSentence'));
      else if (f.amountState === 'CONFLICT') out.push(t(lang, 'feeConflictSentence', { reg: f.conflicts[0] ? f.conflicts[0].regulation : won(f.amount), man: f.conflicts[0] ? f.conflicts[0].manual : '' }));
      else out.push(fees.length > 1 ? t(lang, 'feeSentenceLabel', { label: f.label, amount: won(f.amount) }) : t(lang, 'feeSentence', { amount: won(f.amount) }));
    });
    var f0 = fees[0];
    if (f0 && f0.instruments.length && f0.amountState === 'FIXED') {
      var names = root.VisableStatusGuidance ? f0.instruments.map(function (i) { return root.VisableStatusGuidance.tr(lang, 'instruments')[i] || i; }) : f0.instruments;
      out.push(t(lang, 'feeInstrument', { list: names.join(lang === 'en' ? ', ' : '·') }));
    }
    if (f0 && f0.onlineReduction) out.push(t(lang, 'feeOnlineSentence', { pct: Math.round(f0.onlineReduction * 100) }));
    if (model.userProgram === 'gks') {
      var gks = f0 && f0.exemptions.filter(function (e) { return e.program === 'gks'; })[0];
      out.push(gks ? t(lang, 'feeExemptGks', { cond: gks.condition }) : t(lang, 'feeNoExempt'));
      if (f0 && f0.notExempt.length) out.push(f0.notExempt[0]);
    }
    return out;
  }

  // Does the fee depend on the clarification still pending? If every candidate status shares the same fee rows, no.
  function feeInvariant(bundle, procedure, candidates) {
    var SG = root.VisableStatusGuidance;
    if (!SG || !candidates.length) return null;
    var sets = candidates.map(function (c) { var f = SG.feesFor(bundle, procedure, c, procedure === 'status_change' ? c : null); return f ? f.primary.map(function (x) { return x.id; }).join('|') : ''; });
    return sets.every(function (s) { return s === sets[0]; }) ? candidates[0] : null;
  }

  function build(ctx) {
    var step = ctx.step, model = ctx.model, state = ctx.state, bundle = ctx.bundle, lang = ctx.lang || 'ko';
    var route = (state.interp && state.interp.route) || {};
    var facet = route.facet || null;
    var procLabel = model.procedureLabel || '';
    var subject = (model.status ? model.status + ' ' : '') + procLabel;
    var qa = { version: 1, query: state.query, mode: 'clarify',
      interpretation: { status: model.status || null, substatus: model.status && /^[A-H]-\d{1,2}-/.test(model.status) ? model.status : null, procedure: model.procedure || null, procedureLabel: procLabel, office: model.localPractice && model.localPractice.office ? model.localPractice.office.id : null, program: model.userProgram || null, facet: facet, confidence: 'MEDIUM' },
      needsClarification: false, clarification: null, title: '', summary: '', summarySource: 'deterministic', documents: { required: [], conditional: [], applicableOnly: [], alternatives: [], omittable: [] }, fees: [], localPractice: { office: null, variations: [] }, nextActions: [], sources: [], uncertainties: [] };
    var docs, fees;
    var isQuestionStep = step.kind === 'question' || step.kind === 'need-status';
    // Deterministic fee questions are answered without a model call and, when the fee does not depend on the pending
    // clarification, without waiting for it.
    if (facet === 'fee' && model.procedure) {
      var feeStatus = model.status;
      if (!feeStatus && isQuestionStep && step.dimension === '__alias' && state.interp.aliasCandidates && state.interp.aliasCandidates.length) feeStatus = feeInvariant(bundle, model.procedure, state.interp.aliasCandidates);
      var SG = root.VisableStatusGuidance;
      var feeModel = feeStatus || !isQuestionStep ? SG.feesFor(bundle, model.procedure, feeStatus, model.procedure === 'status_change' ? model.target : null) : null;
      if (feeModel) {
        var m2 = Object.assign({}, model, { fees: feeModel, status: feeStatus || model.status });
        fees = collectFees(m2, lang);
        qa.mode = 'fee'; qa.interpretation.confidence = 'HIGH'; qa.fees = fees;
        qa.title = t(lang, 'feeTitle', { subject: ((feeStatus || '') + ' ' + procLabel).trim() });
        qa.summary = feeSentences(lang, fees, m2).join(' ');
        docs = collectDocuments(model, lang);
        qa.documents = docs; qa.sources = collectSources(m2, lang).concat(feeSources(bundle, feeModel, lang)); qa.localPractice = collectLocal(model, lang); qa.uncertainties = collectUncertainties(m2, lang, docs).filter(function (u) { return u.id !== 'forms' && u.id !== 'officer'; });
        qa.needsClarification = isQuestionStep; if (isQuestionStep) qa.clarification = { dimension: step.dimension, question: L(lang, step, 'question') };
        return finish(qa, model, state, lang, { collapsesDetail: !isQuestionStep });
      }
    }
    if (isQuestionStep) {
      qa.mode = 'clarify'; qa.needsClarification = true;
      qa.clarification = { dimension: step.dimension, question: L(lang, step, 'question'), options: (step.options || []).map(function (o) { return { id: o.id, label: LL(lang, o) }; }) };
      qa.title = t(lang, 'clarifyTitle'); qa.summary = t(lang, 'clarifyLead') + ' ' + qa.clarification.question;
      qa.sources = collectSources(model, lang);
      return finish(qa, model, state, lang, { collapsesDetail: false });
    }
    if (step.kind === 'unresolved' || step.kind === 'source-only') {
      qa.mode = 'fallback'; qa.interpretation.confidence = 'LOW';
      qa.title = t(lang, 'fallbackTitle'); qa.summary = t(lang, 'fallbackLead');
      qa.fees = collectFees(model, lang); qa.sources = collectSources(model, lang); qa.uncertainties = collectUncertainties(model, lang, qa.documents);
      return finish(qa, model, state, lang, { collapsesDetail: false });
    }
    // resolved / procedure → HIGH
    qa.mode = 'answer'; qa.interpretation.confidence = 'HIGH';
    docs = collectDocuments(model, lang); fees = collectFees(model, lang);
    qa.documents = docs; qa.fees = fees; qa.localPractice = collectLocal(model, lang); qa.sources = collectSources(model, lang); qa.uncertainties = collectUncertainties(model, lang, docs);
    var focusRef = route.conditions && route.conditions.document_focus;
    var sentences = [];
    if (focusRef) {
      var all = docs.required.map(function (d) { return Object.assign({ level: 'required' }, d); }).concat(docs.conditional.map(function (d) { return Object.assign({ level: 'conditional' }, d); }), docs.applicableOnly.map(function (d) { return Object.assign({ level: 'conditional' }, d); }));
      var focus = all.filter(function (d) { return d.ref.indexOf('residence') >= 0; })[0];
      var focusName = focus ? focus.name : (lang === 'en' ? 'Proof of residence' : '체류지 입증서류');
      qa.title = focus ? t(lang, focus.level === 'required' ? 'focusRequired' : 'focusConditional', { doc: focusName }) : t(lang, 'focusMissing', { doc: focusName });
      if (focus) {
        var formLabel = root.VisableStatusGuidance ? root.VisableStatusGuidance.formLabel(lang, { submission_form: focus.form, copy_count: focus.copyCount, original_returned: focus.originalReturned }) : '';
        sentences.push(formLabel ? t(lang, 'focusForms', { form: formLabel }) : t(lang, 'focusUnspecified'));
        var alt = docs.alternatives.filter(function (a) { return a.ref === focus.ref; })[0];
        if (alt) sentences.push((lang === 'en' ? 'One of: ' : '다음 중 하나: ') + alt.options.join(lang === 'en' ? ', ' : '·'));
        if (focus.appliesWhen) sentences.push(focus.appliesWhen);
      }
      qa.focus = focus ? { ref: focus.ref, name: focusName, level: focus.level, form: focus.form } : { ref: null, name: focusName, level: 'missing' };
    } else {
      qa.title = subject || procLabel;
      var entrySummary = model.entry ? L(lang, model.entry, 'summary') : '';
      if (entrySummary) sentences.push(firstSentences(entrySummary, lang === 'en' ? 220 : 140));
      if (docs.required.length) {
        var names = docs.required.slice(0, 4).map(function (d) { return d.name; });
        sentences.push(t(lang, 'docsLead', { list: names.join(lang === 'en' ? ', ' : '·'), more: docs.required.length > 4 ? t(lang, 'more', { k: docs.required.length - 4 }) : '' }));
      }
    }
    if (fees.length && facet !== 'documents') sentences.push(feeSentences(lang, fees, model)[0]);
    if (model.common && !focusRef) sentences.push(t(lang, 'commonNote'));
    qa.summary = sentences.filter(Boolean).join(' ');
    return finish(qa, model, state, lang, { collapsesDetail: true });
  }

  function finish(qa, model, state, lang, opts) {
    qa.nextActions = [{ id: 'full', label: t(lang, 'full') }, { id: 'evidence', label: t(lang, 'evidence') }, { id: 'followup', label: t(lang, 'followup') }];
    var v = validateModel(qa);
    if (!v.ok) { qa.mode = 'fallback'; qa.summary = t(lang, 'fallbackLead'); qa.title = t(lang, 'fallbackTitle'); qa.invalid = v.errors; }
    var collapses = !!opts.collapsesDetail && qa.mode !== 'fallback';
    return { model: qa, html: render(qa, model, lang, { collapsesDetail: collapses, fullOpen: !!(state && state.fullOpen) }), collapsesDetail: collapses };
  }

  /* --------------------------------------------------------- validation ---- */
  var MODES = ['answer', 'fee', 'clarify', 'fallback'];
  var FORMS = ['ORIGINAL_ONLY', 'COPY_ONLY', 'ORIGINAL_AND_COPY', 'ORIGINAL_PRESENT_COPY_SUBMIT', 'CERTIFIED_COPY', 'ONE_OF_ORIGINAL_OR_COPY', 'ELECTRONIC_DOCUMENT_ACCEPTED', 'VARIES_BY_ITEM', 'SOURCE_DOES_NOT_SPECIFY', 'NOT_APPLICABLE'];
  function validateModel(qa) {
    var errors = [];
    if (!qa || typeof qa !== 'object') return { ok: false, errors: ['model missing'] };
    if (MODES.indexOf(qa.mode) < 0) errors.push('mode');
    if (!qa.interpretation || ['HIGH', 'MEDIUM', 'LOW'].indexOf(qa.interpretation.confidence) < 0) errors.push('confidence');
    if (typeof qa.summary !== 'string' || !qa.summary.trim()) errors.push('summary');
    if (typeof qa.title !== 'string' || !qa.title.trim()) errors.push('title');
    if (qa.mode === 'answer' || qa.mode === 'fee') {
      if (!Array.isArray(qa.sources) || !qa.sources.length) errors.push('sources');
      ['required', 'conditional', 'applicableOnly', 'omittable'].forEach(function (k) { (qa.documents[k] || []).forEach(function (d) { if (!d.name) errors.push('document name'); if (FORMS.indexOf(d.form) < 0) errors.push('document form ' + d.form); }); });
      (qa.fees || []).forEach(function (f) { if (typeof f.amount !== 'number' || !f.amountState) errors.push('fee amount'); if (f.amountState === 'FIXED' && !(f.amount > 0)) errors.push('fee zero'); });
    }
    if (qa.mode === 'clarify' && !(qa.clarification && qa.clarification.question)) errors.push('clarification');
    if (/<|javascript:/i.test(qa.summary)) errors.push('markup in summary');
    return { ok: !errors.length, errors: errors };
  }
  // Text corpus the AI may draw from: everything the model states. Anything numeric or fact-like outside it is rejected.
  function allowedCorpus(qa) {
    var parts = [qa.title, qa.summary, qa.query];
    ['required', 'conditional', 'applicableOnly', 'omittable'].forEach(function (k) { (qa.documents[k] || []).forEach(function (d) { parts.push(d.name, d.appliesWhen || ''); }); });
    (qa.documents.alternatives || []).forEach(function (a) { parts.push(a.name); parts.push.apply(parts, a.options); });
    (qa.fees || []).forEach(function (f) {
      parts.push(f.label, String(f.amount), won(f.amount));
      (f.instruments || []).forEach(function (i) { parts.push(i); ['ko', 'en'].forEach(function (lg) { if (root.VisableStatusGuidance) parts.push(root.VisableStatusGuidance.tr(lg, 'instruments')[i] || ''); }); });
      f.exemptions.forEach(function (e) { parts.push(e.condition); }); parts.push.apply(parts, f.notExempt); f.conflicts.forEach(function (c) { parts.push(c.regulation, c.manual, c.interim); }); if (f.onlineReduction) parts.push(String(Math.round(f.onlineReduction * 100)));
    });
    (qa.localPractice.variations || []).forEach(function (v) { parts.push(v.summary); });
    if (qa.localPractice.office) parts.push(qa.localPractice.office.name);
    (qa.sources || []).forEach(function (s) { parts.push(s.title, s.article || '', s.page != null ? String(s.page) : ''); });
    (qa.uncertainties || []).forEach(function (u) { parts.push(u.text); });
    if (qa.interpretation) parts.push(qa.interpretation.status || '', qa.interpretation.procedureLabel || '');
    return parts.filter(Boolean).join('\n');
  }
  var FACT_TOKEN_RE = /₩\s?[\d,]+|\d[\d,\.]*\s?(?:만\s?원|천\s?원|원|won|krw|%|일|개월|년|부|장|매|통|days?|months?|years?|copies|copy)|\d[\d,\.]*/gi;
  var NEW_FACT_WORDS = /원본|사본|공증|아포스티유|영사확인|번역|면제|감경|무료|불필요|필요\s?없|생략|수입인지|현금|카드|기한|이내|벌금|과태료|강제퇴거|출국명령|취소|거부|불허|예약|방문예약|하이코리아|original|copy|copies|notariz|apostille|translation|exempt|waiv|free of charge|not required|no need|fine|penalty|deport|cancel|refus|reject|appointment|reservation/gi;
  var OFFICE_NAME_RE = /[가-힣]+\s?출입국(?:[·ㆍ]?외국인)?\s?(?:청|사무소|출장소|관리사무소)|[A-Z][A-Za-z]+\s+immigration\s+office/g;
  var EXEMPT_RE = /면제|무료|수수료\s?없|exempt|waiv|free of charge|no fee/i;
  var CONDITION_RE = /경우|때에?|이면|라면|한정|대상|해당|착오|잘못|\bif\b|\bwhen\b|\bonly\b|\bunless\b|\berror\b/i;
  function normalizeToken(tok) { return String(tok).replace(/[\s,]/g, '').toLowerCase(); }
  function validateEnhancement(qa, text) {
    var reasons = [];
    var s = String(text || '').replace(/\s+/g, ' ').trim();
    if (!s) return { ok: false, reasons: ['empty'] };
    if (s.length < 20 || s.length > 420) reasons.push('length');
    if (/<|>|https?:|javascript:|\[|\]|\{|\}/i.test(s)) reasons.push('markup');
    var corpus = allowedCorpus(qa);
    var corpusNorm = normalizeToken(corpus);
    var facts = s.match(FACT_TOKEN_RE) || [];
    facts.forEach(function (f) { var n = normalizeToken(f); var digits = n.replace(/[^\d]/g, ''); if (digits && corpusNorm.indexOf(digits) < 0) reasons.push('number ' + f); });
    var words = s.match(NEW_FACT_WORDS) || [];
    words.forEach(function (w) { if (corpusNorm.indexOf(normalizeToken(w)) < 0) reasons.push('fact word ' + w); });
    // Offices are never introduced by the model: every office name must already be in the answer.
    (s.match(OFFICE_NAME_RE) || []).forEach(function (o) { if (corpusNorm.indexOf(normalizeToken(o)) < 0) reasons.push('fact office ' + o); });
    // Relevance: the wording must still name the procedure or a listed document.
    var anchors = [qa.interpretation && qa.interpretation.procedureLabel].concat((qa.documents.required || []).map(function (d) { return d.name; })).filter(Boolean);
    if (anchors.length && !anchors.some(function (a) { return s.indexOf(String(a).slice(0, 4)) >= 0; })) reasons.push('off-topic');
    if (/확실|보장|반드시 허가|무조건|100%|guarantee|definitely approved|always approved/i.test(s)) reasons.push('overclaim');
    // Exemptions are conditional rules: a fixed fee may never be rewritten as an unconditional waiver.
    if ((qa.fees || []).some(function (f) { return f.amountState === 'FIXED' && f.amount > 0; })) {
      s.split(/[.!?。]\s*/).forEach(function (sentence) {
        if (!EXEMPT_RE.test(sentence)) return;
        if (!CONDITION_RE.test(sentence)) reasons.push('unconditional exemption ' + (sentence.match(EXEMPT_RE) || [''])[0]);
      });
    }
    return { ok: !reasons.length, text: s, reasons: reasons };
  }

  /* --------------------------------------------------------------- render -- */
  function render(qa, model, lang, opts) {
    var grid = '';
    if (qa.mode === 'answer' || qa.mode === 'fee') {
      var d = qa.documents;
      var prep = d.required.length ? t(lang, 'required', { n: d.required.length }) + (d.conditional.length + d.applicableOnly.length ? ' · ' + t(lang, 'conditional', { n: d.conditional.length + d.applicableOnly.length }) : '') : t(lang, 'noDocs');
      var fee = qa.fees.length ? qa.fees.map(function (f) { return feeLine(lang, f); }).join(' · ') : '—';
      var feeExtra = qa.fees.length && qa.fees[0].onlineReduction ? ' <span class="sg-muted">' + esc(t(lang, 'online', { pct: Math.round(qa.fees[0].onlineReduction * 100) })) + '</span>' : '';
      var office = qa.localPractice.office ? (qa.localPractice.variations.length ? t(lang, 'officeHas', { office: qa.localPractice.office.name }) : t(lang, 'officeNone', { office: qa.localPractice.office.name })) : t(lang, 'national');
      grid = '<dl class="sg-quick-grid"><div><dt>' + esc(t(lang, 'prepare')) + '</dt><dd>' + esc(prep) + '</dd></div>' +
        '<div><dt>' + esc(t(lang, 'cost')) + '</dt><dd>' + (qa.fees.length && qa.fees[0].amountState === 'FIXED' && qa.fees.length === 1 ? '<strong>' + esc(fee) + '</strong>' : esc(fee)) + feeExtra + '</dd></div>' +
        '<div><dt>' + esc(t(lang, 'office')) + '</dt><dd>' + esc(office) + '</dd></div></dl>';
    }
    var unc = qa.uncertainties.length && qa.mode !== 'clarify' ? '<ul class="sg-quick-uncertain">' + qa.uncertainties.slice(0, 2).map(function (u) { return '<li>' + esc(u.text) + '</li>'; }).join('') + '</ul>' : '';
    var actions = '';
    if (qa.mode !== 'clarify') {
      actions = '<div class="sg-quick-actions">' +
        (opts && opts.collapsesDetail ? '<button type="button" class="sg-btn sg-btn-primary" data-sg-action="toggle-full" aria-expanded="' + (opts.fullOpen ? 'true' : 'false') + '" aria-controls="sgFull">' + esc(t(lang, 'full')) + '</button>' : '') +
        '<button type="button" class="sg-btn" data-sg-action="show-evidence">' + esc(t(lang, 'evidence')) + '</button>' +
        '<a class="sg-btn" href="ai.html?' + (qa.interpretation.status ? 'visa_code=' + encodeURIComponent(qa.interpretation.status) + '&' : '') + (qa.interpretation.procedure ? 'selected_procedure_key=' + encodeURIComponent(qa.interpretation.procedure) + '&' : '') + 'lang=' + esc(lang) + '" data-sg-action="followup">' + esc(t(lang, 'followup')) + '</a></div>';
    }
    return '<section class="sg-quick sg-quick-' + esc(qa.mode) + '" aria-labelledby="sgQuickTitle" data-sg-quick-mode="' + esc(qa.mode) + '">' +
      '<div class="sg-quick-brand">' + esc(t(lang, 'brand')) + ' <span class="sg-state">' + esc(t(lang, 'badge')) + '</span></div>' +
      '<h2 id="sgQuickTitle" class="sg-quick-title" tabindex="-1">' + esc(qa.title) + '</h2>' +
      '<p id="sgQuickSummary" class="sg-quick-summary" data-sg-ai="deterministic" aria-live="polite">' + esc(qa.summary) + '</p>' +
      '<p id="sgQuickNote" class="sg-quick-note" role="status" hidden></p>' + grid + unc + actions + '</section>';
  }

  /* ------------------------------------------------- AI wording (optional) -- */
  var AI_ENDPOINT = '/api/waymaker/quick-answer';
  var AI_TIMEOUT_MS = 9000;
  var aiCache = {};
  function compactForAi(qa) {
    return { version: 1, query: qa.query, mode: qa.mode, interpretation: qa.interpretation, title: qa.title, summary: qa.summary,
      documents: { required: qa.documents.required.map(function (d) { return { name: d.name, form: d.form }; }), conditional: qa.documents.conditional.map(function (d) { return { name: d.name, appliesWhen: d.appliesWhen }; }), applicableOnly: qa.documents.applicableOnly.map(function (d) { return { name: d.name }; }), alternatives: qa.documents.alternatives, omittable: qa.documents.omittable.map(function (d) { return { name: d.name }; }) },
      fees: qa.fees, localPractice: qa.localPractice, sources: qa.sources.map(function (s) { return { type: s.type, title: s.title, article: s.article || null, page: s.page || null }; }), uncertainties: qa.uncertainties };
  }
  function shouldEnhance(qa, state) {
    if (typeof root.VISABLE_QUICK_ANSWER_AI !== 'undefined' && root.VISABLE_QUICK_ANSWER_AI === false) return false;
    if (qa.mode !== 'answer') return false;                 // fee / clarify / fallback are deterministic
    if (root.navigator && root.navigator.onLine === false) return false;
    return true;
  }
  function afterRender(host, model, state, bundle) {
    var qa = model.quick;
    if (!qa || !host || typeof fetch !== 'function') return;
    var summaryEl = host.querySelector('#sgQuickSummary');
    var noteEl = host.querySelector('#sgQuickNote');
    if (!summaryEl) return;
    var key = (state.lang || 'ko') + '|' + qa.query + '|' + qa.title + '|' + qa.summary;
    if (aiCache[key]) { applyCached(aiCache[key]); return; }
    if (!shouldEnhance(qa, state)) return;
    function applyCached(entry) {
      if (entry.ok) { summaryEl.textContent = entry.text; summaryEl.setAttribute('data-sg-ai', 'enhanced'); }
      else if (entry.failed && noteEl) { noteEl.textContent = t(state.lang || 'ko', 'aiFailed'); noteEl.hidden = false; }
    }
    var controller = typeof AbortController !== 'undefined' ? new AbortController() : null;
    var timer = setTimeout(function () { if (controller) controller.abort(); }, AI_TIMEOUT_MS);
    aiCache[key] = { pending: true };
    fetch(AI_ENDPOINT, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ lang: state.lang || 'ko', model: compactForAi(qa) }), signal: controller ? controller.signal : undefined })
      .then(function (res) {
        if (res.status === 404 || res.status === 501 || res.status === 405) { aiCache[key] = { ok: false, failed: false }; return null; } // not deployed here: stay silent
        return res.json().catch(function () { return { ok: false }; }).then(function (data) { return { status: res.status, data: data }; });
      })
      .then(function (r) {
        if (!r) return;
        var data = r.data || {};
        if (data && data.ok && data.summary) {
          var v = validateEnhancement(qa, data.summary);
          if (v.ok) { aiCache[key] = { ok: true, text: v.text }; applyCached(aiCache[key]); return; }
        }
        if (data && data.status === 'NOT_CONFIGURED') { aiCache[key] = { ok: false, failed: false }; return; }
        aiCache[key] = { ok: false, failed: true }; applyCached(aiCache[key]);
      })
      .catch(function () { aiCache[key] = { ok: false, failed: false }; }) // no network / aborted: the feature is simply unavailable here
      .then(function () { clearTimeout(timer); });
  }

  /* ---------------------------------------------------------- follow-up --- */
  var HANDOFF_KEY = 'visable.waymaker.handoff';
  function buildHandoff(model, state, bundle, lang) {
    lang = lang || state.lang || 'ko';
    var docs = collectDocuments(model, lang);
    var fees = collectFees(model, lang);
    var SG = root.VisableStatusGuidance;
    return { version: 1, at: new Date().toISOString(), source: 'quick-answer', query: state.query, lang: lang,
      status: model.status || null, substatus: model.status && /^[A-H]-\d{1,2}-/.test(model.status) ? model.status : null, procedure: model.procedure || null, procedureLabel: model.procedureLabel || '',
      reason: model.reason || null, office: model.localPractice && model.localPractice.office ? { id: model.localPractice.office.id, name: lang === 'en' ? model.localPractice.office.name_en : model.localPractice.office.name_ko } : null,
      documents: { required: docs.required.map(function (d) { return d.name; }), conditional: docs.conditional.concat(docs.applicableOnly).map(function (d) { return d.name + (d.appliesWhen ? ' (' + d.appliesWhen + ')' : ''); }) },
      forms: docs.required.concat(docs.conditional).map(function (d) { return { name: d.name, form: SG ? (SG.tr(lang, 'forms')[d.form] || d.form) : d.form }; }).filter(function (f) { return f.form; }),
      fees: fees.map(function (f) { return f.label + ': ' + (feeLine(lang, f) || '') + (f.onlineReduction ? ' (' + t(lang, 'online', { pct: Math.round(f.onlineReduction * 100) }) + ')' : ''); }),
      exemptions: fees.length ? fees[0].exemptions.map(function (e) { return e.condition + ' [' + e.review + ']'; }) : [],
      localPractice: collectLocal(model, lang).variations.map(function (v) { return '[' + v.layer + '] ' + v.summary; }),
      sources: collectSources(model, lang).map(function (s) { return s.type === 'regulation' ? s.title + ' ' + s.article : s.title + ' ' + (s.date || '') + ' p.' + s.page; }),
      uncertainties: collectUncertainties(model, lang, docs).map(function (u) { return u.text; }) };
  }
  function handoff(model, state, bundle) {
    if (typeof sessionStorage === 'undefined' || typeof location === 'undefined') return false;
    var packet = buildHandoff(model, state, bundle, state.lang);
    try { sessionStorage.setItem(HANDOFF_KEY, JSON.stringify(packet)); } catch (e) { return false; }
    var url = 'ai.html?handoff=quick-answer' + (packet.status ? '&visa_code=' + encodeURIComponent(packet.status) : '') + (packet.procedure ? '&selected_procedure_key=' + encodeURIComponent(packet.procedure) : '') + '&lang=' + encodeURIComponent(packet.lang);
    location.href = url;
    return true;
  }
  function readHandoff() {
    if (typeof sessionStorage === 'undefined') return null;
    try { var raw = sessionStorage.getItem(HANDOFF_KEY); if (!raw) return null; var p = JSON.parse(raw); if (!p || p.version !== 1) return null; return p; } catch (e) { return null; }
  }
  // Context text for the chatbot: facts it must not contradict or extend. Plain text, escaped by the consumer.
  function handoffContextLine(p, lang) {
    if (!p) return '';
    var ko = lang !== 'en';
    var lines = [];
    lines.push(ko ? '[Visable 확인된 안내] 사용자는 검색 결과의 빠른 답에서 이어서 질문합니다. 아래는 공식 자료에서 확인된 구조화 사실입니다. 이 사실을 설명·정리·번역만 하고, 여기에 없는 서류·원본/사본 요건·수수료·면제·기한·관서별 관행·자격 요건을 새로 만들지 마십시오. 불확실하면 관할 관서 확인을 안내하십시오.' : '[Visable confirmed guidance] The user continues from a Quick Answer. Below are structured facts confirmed from official sources. Explain, organize or translate them only; do not add documents, original/copy rules, fees, exemptions, deadlines, office practices or eligibility rules that are not listed. When unsure, recommend confirming with the office.');
    lines.push((ko ? '원래 질문: ' : 'Original question: ') + p.query);
    lines.push((ko ? '해석: ' : 'Interpretation: ') + [p.status, p.procedureLabel, p.office ? p.office.name : null, p.reason ? (ko ? '사유 ' : 'reason ') + p.reason : null].filter(Boolean).join(' · '));
    if (p.documents.required.length) lines.push((ko ? '필수서류: ' : 'Required documents: ') + p.documents.required.join(', '));
    if (p.documents.conditional.length) lines.push((ko ? '조건부 서류: ' : 'Conditional documents: ') + p.documents.conditional.join(', '));
    if (p.forms.length) lines.push((ko ? '제출 형태(원문 표기): ' : 'Submission form (per source): ') + p.forms.map(function (f) { return f.name + '=' + f.form; }).join(', '));
    if (p.fees.length) lines.push((ko ? '수수료: ' : 'Fees: ') + p.fees.join('; '));
    if (p.exemptions.length) lines.push((ko ? '면제·감경 조건: ' : 'Exemptions: ') + p.exemptions.join('; '));
    if (p.localPractice.length) lines.push((ko ? '관서 정보(전국 기준이 아님): ' : 'Office information (not the baseline): ') + p.localPractice.join('; '));
    if (p.sources.length) lines.push((ko ? '근거: ' : 'Sources: ') + p.sources.slice(0, 8).join('; '));
    if (p.uncertainties.length) lines.push((ko ? '불확실한 점: ' : 'Uncertainties: ') + p.uncertainties.join(' '));
    return lines.join('\n');
  }

  var api = { build: build, render: render, validateModel: validateModel, validateEnhancement: validateEnhancement, allowedCorpus: allowedCorpus, afterRender: afterRender, handoff: handoff, buildHandoff: buildHandoff, readHandoff: readHandoff, handoffContextLine: handoffContextLine, compactForAi: compactForAi, feeInvariant: feeInvariant, COPY: COPY, HANDOFF_KEY: HANDOFF_KEY, AI_ENDPOINT: AI_ENDPOINT };
  root.VisableQuickAnswer = api;
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
})(typeof globalThis !== 'undefined' ? globalThis : this);
