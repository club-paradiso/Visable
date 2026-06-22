/* ============================================================================
 * Paradiso — Complex-Status Guide for additional statuses (F-6/G-1/E-7/F-5/D-2/D-4)
 * ----------------------------------------------------------------------------
 * Brings the F-4 "recommended starting point → one dominant CTA → full-screen
 * guided flow → checklist-first result" pattern to six more complex statuses,
 * WITHOUT touching the F-4 reference implementation (assets/js/f4-route-guide.js)
 * and WITHOUT inventing any legal/document content.
 *
 * Source-safety contract:
 *  - Subcode options come verbatim from visa_data.json via the TESTED adapter
 *    window.ParadisoRoute.buildGuidanceModel() (never re-derived here).
 *  - Procedure options are only the ones the adapter reports as "available".
 *  - Manual-review / reference-only subcodes (placeholders) are NOT offered.
 *  - The result NEVER re-renders protected document data. It narrows the user to
 *    a subcode + procedure, then hands off to the EXISTING source-backed detail
 *    (window.ParadisoRoute.goToResult / openVisaDrawer) for the real documents
 *    and source references. Anything not source-backed here is shown as
 *    "공식근거 확인 필요" (Official source needs confirmation).
 *  - No eligibility/approval claims. Cautious language only.
 *
 * Reuse: the F-4 engine (ParadisoComplexGuide) is intentionally NOT forked into;
 * it is data/f4-coupled and must not regress. This engine shares the same UX,
 * CSS tokens, copy, and a11y pattern, and delegates the actual legal content to
 * ParadisoRoute, so the six statuses feel consistent with F-4 while staying safe.
 * ========================================================================== */
(function () {
  'use strict';

  var TARGETS = ['F-6', 'G-1', 'E-7', 'F-5', 'D-2', 'D-4'];

  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (ch) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[ch];
    });
  }
  function csgLang() {
    var l = (typeof currentLanguage !== 'undefined' && currentLanguage) ? currentLanguage : 'ko';
    return l === 'en' ? 'en' : 'ko';
  }

  /* ---- chrome strings (Korean canonical; English active; zh-CN → ko fallback
   * per the repo policy — no low-quality machine Chinese in this flow). ------ */
  var STR_KO = {
    eyebrow: '공식 출처 기반 안내',
    recStartTitle: '추천 시작점',
    recStartBody: '이 체류자격은 세부 유형, 신청 절차, 현재 상황에 따라 준비서류와 진행 방식이 달라질 수 있습니다. 몇 가지 질문에 답하면 내 상황에 가까운 준비서류와 절차를 확인할 수 있습니다.',
    ctaMicrocopy: '약 1분 · 세부코드를 몰라도 시작 가능',
    primaryCtaTpl: '내 상황에 맞는 {code} 준비서류 찾기',
    secondaryActionsLabel: '다른 방식으로 보기',
    secViewSubcategories: '전체 세부자격 보기',
    secViewCommonDocs: '공통서류 보기',
    secViewProcedure: '신청 절차 보기',
    secViewSources: '공식 근거 보기',
    modalAria: '체류자격 준비 안내',
    close: '닫기',
    back: '← 이전',
    next: '다음',
    seeResult: '결과 보기',
    restartShort: '다시 시작',
    stepWord: '단계',
    progressAria: '진행 상황',
    optUnsure: '잘 모르겠어요',
    stepSubcodeQ: '어떤 유형에 가까우신가요?',
    stepSubcodeHelp: '아래는 이 체류자격의 세부 유형입니다(공식 데이터 기준). 잘 모르면 "잘 모르겠어요"를 선택해도 됩니다.',
    stepProcedureQ: '지금 필요한 절차는 무엇인가요?',
    stepProcedureHelp: '현재 데이터에서 안내 가능한 절차만 표시됩니다.',
    resultTitleTpl: '당신에게 가까운 {code} 준비경로',
    matchedType: '선택한 유형',
    matchedProcedure: '선택한 절차',
    unsureType: '유형 미정',
    unsureProcedure: '절차 미정',
    resFirstSteps: '먼저 해야 할 일',
    resBasicDocs: '기본 준비서류',
    resAddDocs: '내 상황에서 추가될 수 있는 서류',
    resProcedure: '신청 절차',
    resSources: '공식 근거',
    resNextActions: '다음 행동',
    officialSourceNeedsConfirm: '공식근거 확인 필요',
    firstStepConfirmType: '내 세부 유형이 맞는지 확인하기',
    firstStepConfirmOffice: '관할 출입국·외국인관서 또는 재외공관 확인하기',
    firstStepPrepareDocs: '선택한 절차에 맞는 서류 준비하기',
    docsHandoffNote: '구체적 준비서류는 공식 출처 기반 상세 화면에서 확인하세요. 아래 "전체 준비서류·절차 보기"를 눌러 해당 세부코드·절차의 서류를 확인할 수 있습니다.',
    addDocsNote: '개별 상황에 따라 추가서류가 요구될 수 있습니다. 정확한 목록은 상세 화면과 관할 기관에서 확인하세요.',
    sourcesHandoffNote: '공식 근거(매뉴얼·출처)는 상세 화면에 함께 표시됩니다. 출처가 연결되지 않은 항목은 "공식근거 확인 필요"로 표시됩니다.',
    viewFullDetail: '전체 준비서류·절차 보기',
    copyChecklist: '체크리스트 복사',
    copied: '복사되었습니다',
    copyFail: '복사하지 못했습니다',
    safetyNote: '개별 사안, 관할 출입국기관 또는 재외공관 판단에 따라 추가서류가 요구될 수 있습니다.',
    procStepPrepare: '서류 준비',
    procStepReserve: '필요 시 방문 예약',
    procStepSubmit: '신청서 제출',
    procStepReview: '심사',
    procStepResult: '결과 확인',
    procStepFollowup: '필요 시 후속 등록·증 발급',
    noSubcodesNote: '이 체류자격은 공식 데이터에 정리된 선택 가능한 세부 유형이 없어, 바로 절차 안내로 진행합니다.',
    noteE7: 'E-7은 직종·직무에 따라 요건과 서류가 다릅니다. 정확한 직종 분류 확인이 필요할 수 있으며, 결과는 단정할 수 없습니다.',
    noteG1: 'G-1은 체류 사유별로 요건과 서류가 다르며, 다수 항목이 개별 심사·확인 대상입니다. 관할 기관 확인이 필요합니다.',
    noteF5: 'F-5(영주)는 자격 기준과 절차가 까다롭고 개별 심사 비중이 큽니다. 구체적 요건은 공식 출처와 관할 기관에서 확인하세요.'
  };
  var STR_EN = {
    eyebrow: 'Guidance based on official sources',
    recStartTitle: 'Recommended starting point',
    recStartBody: 'Documents and procedures for this status may vary depending on your subcategory, application path, and current situation. Answer a few questions to find the document checklist and procedure closest to your situation.',
    ctaMicrocopy: 'About 1 minute · No subcategory knowledge needed',
    primaryCtaTpl: 'Find My {code} Document Checklist',
    secondaryActionsLabel: 'Other ways to view this status',
    secViewSubcategories: 'View All Subcategories',
    secViewCommonDocs: 'View Common Documents',
    secViewProcedure: 'View Application Procedure',
    secViewSources: 'View Official Sources',
    modalAria: 'Status preparation guide',
    close: 'Close',
    back: '← Back',
    next: 'Next',
    seeResult: 'See result',
    restartShort: 'Restart',
    stepWord: 'Step',
    progressAria: 'Progress',
    optUnsure: 'I am not sure',
    stepSubcodeQ: 'Which type is closest to yours?',
    stepSubcodeHelp: 'These are this status’s subcategories (from official data). If unsure, you can pick "I am not sure".',
    stepProcedureQ: 'Which procedure do you need now?',
    stepProcedureHelp: 'Only procedures the current data can guide are shown.',
    resultTitleTpl: 'Your likely {code} preparation path',
    matchedType: 'Selected type',
    matchedProcedure: 'Selected procedure',
    unsureType: 'Type not decided',
    unsureProcedure: 'Procedure not decided',
    resFirstSteps: 'First steps',
    resBasicDocs: 'Basic required documents',
    resAddDocs: 'Documents that may be added for your situation',
    resProcedure: 'Procedure',
    resSources: 'Official sources',
    resNextActions: 'Next actions',
    officialSourceNeedsConfirm: 'Official source needs confirmation',
    firstStepConfirmType: 'Confirm your subcategory is correct',
    firstStepConfirmOffice: 'Confirm the competent immigration office or Korean consulate',
    firstStepPrepareDocs: 'Prepare documents for the procedure you selected',
    docsHandoffNote: 'See the official-source-based detail screen for the specific documents. Tap "View full documents & procedure" below to see the documents for that subcode/procedure.',
    addDocsNote: 'Additional documents may be requested depending on your individual case. Confirm the exact list on the detail screen and with the competent office.',
    sourcesHandoffNote: 'Official sources (manuals/references) are shown on the detail screen. Items without a connected source are marked "Official source needs confirmation".',
    viewFullDetail: 'View full documents & procedure',
    copyChecklist: 'Copy checklist',
    copied: 'Copied',
    copyFail: 'Could not copy',
    safetyNote: 'Additional documents may be requested depending on your individual case and the decision of the competent immigration office or Korean consulate.',
    procStepPrepare: 'Prepare documents',
    procStepReserve: 'Make a reservation if applicable',
    procStepSubmit: 'Submit application',
    procStepReview: 'Review / screening',
    procStepResult: 'Check result',
    procStepFollowup: 'Complete follow-up registration or card issuance if applicable',
    noSubcodesNote: 'This status has no selectable subcategories recorded in the official data, so we go straight to the procedure step.',
    noteE7: 'E-7 requirements and documents depend on the occupation/job category. Confirming the exact job classification may be required, and outcomes cannot be guaranteed.',
    noteG1: 'G-1 requirements and documents vary by reason for stay, and many items are subject to individual review. Confirmation with the competent office is required.',
    noteF5: 'F-5 (permanent residence) has strict criteria and significant individual review. Confirm specific requirements with official sources and the competent office.'
  };
  var STR_PACKS = { ko: STR_KO, en: STR_EN };
  function S(k) { var p = STR_PACKS[csgLang()] || STR_KO; return (p[k] != null) ? p[k] : STR_KO[k]; }
  function tpl(k, code) { return String(S(k)).replace('{code}', code); }

  /* ---- per-status config (data-sourced; notes are cautious framing only) --- */
  var STATUS_NOTE = { 'E-7': 'noteE7', 'G-1': 'noteG1', 'F-5': 'noteF5' };

  /* ---------------------------------------------------- data adapter (safe) */
  function getRecord(code) {
    try {
      if (typeof VISA_DATA !== 'undefined' && Array.isArray(VISA_DATA)) {
        return VISA_DATA.find(function (v) { return v && v.code === code; }) || null;
      }
    } catch (e) { /* ignore */ }
    return null;
  }
  function getModel(code) {
    var rec = getRecord(code);
    if (!rec || !window.ParadisoRoute || typeof window.ParadisoRoute.buildGuidanceModel !== 'function') return null;
    try { return window.ParadisoRoute.buildGuidanceModel(rec); } catch (e) { return null; }
  }
  // Only offer real, selectable subcodes — never manual-review/reference-only
  // placeholders (which have no meaningful title).
  function selectableSubcodes(model) {
    if (!model || !Array.isArray(model.subcodes)) return [];
    return model.subcodes.filter(function (s) { return s && s.status === 'active' && s.code; });
  }
  function subcodeLabel(s) {
    var title = (csgLang() === 'en' && s.titleEn) ? s.titleEn : (s.titleKo || s.titleEn || '');
    return title ? (s.code + ' · ' + title) : s.code;
  }
  function availableProcedures(model) {
    if (!model || !Array.isArray(model.procedures)) return [];
    return model.procedures.filter(function (p) { return p && p.status === 'available' && p.key; });
  }
  function procLabel(p) { return p.userLabel || p.officialLabel || p.key; }
  function findSub(model, code) {
    var subs = (model && model.subcodes) || [];
    for (var i = 0; i < subs.length; i++) if (subs[i].code === code) return subs[i];
    return null;
  }
  function findProc(model, key) {
    var ps = (model && model.procedures) || [];
    for (var i = 0; i < ps.length; i++) if (ps[i].key === key) return ps[i];
    return null;
  }

  /* -------------------------------------------------- pure flow + result --- */
  // Steps are computed from the (source-backed) model. Pure → unit-testable.
  function buildSteps(model) {
    var steps = [];
    var subs = selectableSubcodes(model);
    if (subs.length) {
      steps.push({
        id: 'subcode', type: 'single', qKey: 'stepSubcodeQ', helpKey: 'stepSubcodeHelp',
        options: subs.map(function (s) { return { id: s.code, label: subcodeLabel(s) }; })
          .concat([{ id: 'unsure', label: S('optUnsure'), unsure: true }])
      });
    }
    var procs = availableProcedures(model);
    steps.push({
      id: 'procedure', type: 'single', qKey: 'stepProcedureQ', helpKey: 'stepProcedureHelp',
      options: procs.map(function (p) { return { id: p.key, label: procLabel(p) }; })
        .concat([{ id: 'unsure', label: S('optUnsure'), unsure: true }])
    });
    return steps;
  }

  function buildResultModel(code, model, answers) {
    answers = answers || {};
    var subCode = (answers.subcode && answers.subcode !== 'unsure') ? answers.subcode : '';
    var procKey = (answers.procedure && answers.procedure !== 'unsure') ? answers.procedure : '';
    var sub = subCode ? findSub(model, subCode) : null;
    var proc = procKey ? findProc(model, procKey) : null;
    return {
      code: code,
      subCode: subCode,
      subLabel: sub ? subcodeLabel(sub) : '',
      procKey: procKey,
      procLabel: proc ? procLabel(proc) : '',
      noteKey: STATUS_NOTE[code] || '',
      firstSteps: [S('firstStepConfirmType'), S('firstStepConfirmOffice'), S('firstStepPrepareDocs')],
      procSteps: [S('procStepPrepare'), S('procStepReserve'), S('procStepSubmit'), S('procStepReview'), S('procStepResult'), S('procStepFollowup')]
    };
  }

  function checklistText(code, m) {
    var lines = [];
    lines.push(tpl('resultTitleTpl', code));
    lines.push(S('matchedType') + ': ' + (m.subLabel || S('unsureType')));
    lines.push(S('matchedProcedure') + ': ' + (m.procLabel || S('unsureProcedure')));
    lines.push(''); lines.push('[' + S('resFirstSteps') + ']');
    m.firstSteps.forEach(function (s) { lines.push('- ' + s); });
    lines.push(''); lines.push('[' + S('resBasicDocs') + '] ' + S('officialSourceNeedsConfirm'));
    lines.push('- ' + S('docsHandoffNote'));
    lines.push(''); lines.push('[' + S('resProcedure') + ']');
    m.procSteps.forEach(function (s, i) { lines.push((i + 1) + '. ' + s); });
    lines.push(''); lines.push(S('safetyNote'));
    return lines.join('\n');
  }

  /* ----------------------------------------------------------- module state */
  var state = { code: null, model: null, view: 'flow', stepIndex: 0, steps: [], answers: {}, result: null,
    modal: null, lastFocus: null, keyHandler: null };

  /* --------------------------------------------------------------- styling */
  function injectStyles() {
    if (document.getElementById('csgStyles')) return;
    var css = '' +
'.csg-hero{background:var(--bg1,#fff);border:1px solid var(--bd,#d1c6b4);border-radius:var(--radius-lg,16px);box-shadow:var(--sh1,0 1px 2px rgba(0,0,0,.05));padding:1.05rem 1.1rem;}' +
'.csg-hero.csg-incard{margin:.5rem 0 .2rem;border-color:var(--ac,#2f5e67);border-left-width:4px;background:var(--bg2,#f7f3ea);}' +
'.csg-eyebrow{font-size:.7rem;letter-spacing:.12em;text-transform:uppercase;color:var(--ac,#2f5e67);font-weight:800;margin:0 0 .3rem;}' +
'.csg-rec-title{font-size:1.12rem;font-weight:800;color:var(--t1,#202221);margin:.1rem 0 .35rem;display:flex;align-items:center;gap:.45rem;word-break:keep-all;line-height:1.35;}' +
'.csg-rec-title::before{content:"";width:10px;height:10px;border-radius:50%;background:var(--ac,#2f5e67);display:inline-block;flex:0 0 auto;}' +
'.csg-rec-body{font-size:.88rem;line-height:1.65;color:var(--t2,#4f5552);margin:0 0 .85rem;word-break:keep-all;}' +
'.csg-primary-cta{font:inherit;font-weight:800;font-size:1rem;border-radius:13px;padding:.85rem 1.3rem;cursor:pointer;min-height:52px;border:1px solid var(--ac,#2f5e67);background:var(--ac,#2f5e67);color:#fff;display:inline-flex;align-items:center;gap:.5rem;width:100%;justify-content:center;box-shadow:0 2px 10px rgba(47,94,103,.18);}' +
'.csg-primary-cta:hover{filter:brightness(1.06);}' +
'.csg-primary-cta:focus-visible{outline:3px solid var(--ac,#2f5e67);outline-offset:2px;}' +
'.csg-rec-microcopy{font-size:.78rem;color:var(--t3,#757a76);margin:.5rem 0 0;text-align:center;word-break:keep-all;}' +
'.csg-secondary{margin-top:.9rem;padding-top:.75rem;border-top:1px dashed var(--bd2,#ddd3c3);}' +
'.csg-secondary-label{display:block;font-size:.72rem;font-weight:700;letter-spacing:.04em;color:var(--t3,#757a76);margin:0 0 .45rem;}' +
'.csg-secondary-row{display:flex;flex-wrap:wrap;gap:.4rem;}' +
'.csg-secondary-btn{font:inherit;font-size:.8rem;font-weight:600;border-radius:999px;padding:.4rem .8rem;min-height:38px;cursor:pointer;border:1px solid var(--bd,#d1c6b4);background:transparent;color:var(--t2,#4f5552);}' +
'.csg-secondary-btn:hover{border-color:var(--ac,#2f5e67);color:var(--ac,#2f5e67);}' +
'.csg-secondary-btn:focus-visible{outline:3px solid var(--ac,#2f5e67);outline-offset:1px;}' +
/* overlay */
'.csg-overlay{position:fixed;inset:0;z-index:9000;display:none;align-items:center;justify-content:center;padding:1.25rem;background:rgba(20,20,18,.55);}' +
'.csg-overlay.open{display:flex;}' +
'.csg-box{background:var(--bg1,#fff);border:1px solid var(--bd,#d1c6b4);border-radius:18px;box-shadow:0 18px 60px rgba(0,0,0,.3);width:min(900px,100%);height:min(720px,94vh);max-height:94vh;display:flex;flex-direction:column;overflow:hidden;}' +
'.csg-head{display:flex;align-items:flex-start;justify-content:space-between;gap:.6rem;padding:1rem 1.25rem .7rem;border-bottom:1px solid var(--bd2,#e5dccb);flex:0 0 auto;}' +
'.csg-head h2{font-size:1.08rem;font-weight:800;color:var(--t1,#202221);margin:.05rem 0 0;word-break:keep-all;}' +
'.csg-step-count{font-size:.74rem;font-weight:700;color:var(--ac,#2f5e67);margin:.25rem 0 0;letter-spacing:.04em;}' +
'.csg-close{font:inherit;font-size:1.2rem;line-height:1;border:1px solid var(--bd,#d1c6b4);background:var(--bg2,#f1ece2);color:var(--t1,#202221);border-radius:10px;min-width:42px;min-height:42px;cursor:pointer;flex:0 0 auto;}' +
'.csg-close:focus-visible{outline:3px solid var(--ac,#2f5e67);outline-offset:1px;}' +
'.csg-progress{height:6px;background:var(--bg2,#f1ece2);flex:0 0 auto;}' +
'.csg-progress-bar{height:100%;background:var(--ac,#2f5e67);transition:width .25s ease;}' +
'.csg-body{padding:1.05rem 1.25rem 1.15rem;overflow-y:auto;flex:1 1 auto;-webkit-overflow-scrolling:touch;}' +
'.csg-foot{display:flex;align-items:center;justify-content:space-between;gap:.6rem;padding:.8rem 1.25rem;border-top:1px solid var(--bd2,#e5dccb);background:var(--bg1,#fff);flex:0 0 auto;}' +
'.csg-foot-btn{font:inherit;font-weight:700;font-size:.9rem;border-radius:11px;padding:.7rem 1.15rem;cursor:pointer;min-height:48px;border:1px solid var(--bd,#d1c6b4);background:var(--bg2,#f1ece2);color:var(--t1,#202221);}' +
'.csg-foot-btn.primary{border-color:var(--ac,#2f5e67);background:var(--ac,#2f5e67);color:#fff;}' +
'.csg-foot-btn:disabled{opacity:.45;cursor:not-allowed;}' +
'.csg-foot-btn:focus-visible{outline:3px solid var(--ac,#2f5e67);outline-offset:1px;}' +
'.csg-q-title{font-size:1.1rem;font-weight:800;color:var(--t1,#202221);margin:.2rem 0 .3rem;word-break:keep-all;line-height:1.4;}' +
'.csg-q-help{font-size:.83rem;line-height:1.6;color:var(--t3,#757a76);margin:0 0 .9rem;word-break:keep-all;}' +
'.csg-opts{display:grid;gap:.5rem;max-width:640px;}' +
'.csg-opt{font:inherit;text-align:left;background:var(--bgI,#fff);border:1.5px solid var(--bd,#d1c6b4);border-radius:12px;padding:.8rem .95rem;cursor:pointer;min-height:52px;color:var(--t1,#202221);font-size:.92rem;word-break:keep-all;display:flex;align-items:center;gap:.6rem;line-height:1.45;}' +
'.csg-opt:hover{border-color:var(--ac,#2f5e67);}' +
'.csg-opt:focus-visible{outline:3px solid var(--ac,#2f5e67);outline-offset:1px;}' +
'.csg-opt[aria-checked="true"]{border-color:var(--ac,#2f5e67);background:var(--acG,rgba(47,94,103,.1));box-shadow:inset 0 0 0 1px var(--ac,#2f5e67);font-weight:700;}' +
'.csg-opt-mark{flex:0 0 auto;width:22px;height:22px;border-radius:50%;border:2px solid var(--bd,#9b9384);display:inline-flex;align-items:center;justify-content:center;font-size:.8rem;color:#fff;}' +
'.csg-opt[aria-checked="true"] .csg-opt-mark{background:var(--ac,#2f5e67);border-color:var(--ac,#2f5e67);}' +
'.csg-opt-unsure{color:var(--t2,#4f5552);font-style:italic;}' +
'.csg-result-title{font-size:.82rem;font-weight:800;letter-spacing:.05em;text-transform:uppercase;color:var(--t3,#757a76);margin:0 0 .35rem;}' +
'.csg-route-chip{display:inline-block;font-size:1rem;font-weight:800;color:var(--ac,#2f5e67);background:var(--acG,rgba(47,94,103,.1));border:1px solid var(--ac,#2f5e67);border-radius:12px;padding:.45rem .8rem;margin:0 0 .85rem;word-break:keep-all;}' +
'.csg-section{border:1px solid var(--bd2,#e5dccb);border-radius:14px;padding:.8rem .95rem;margin:0 0 .8rem;background:var(--bg1,#fff);}' +
'.csg-section-title{font-size:.95rem;font-weight:800;color:var(--t1,#202221);margin:0 0 .5rem;word-break:keep-all;display:flex;align-items:center;gap:.4rem;}' +
'.csg-section-title .csg-num{display:inline-flex;align-items:center;justify-content:center;width:24px;height:24px;border-radius:50%;background:var(--ac,#2f5e67);color:#fff;font-size:.78rem;font-weight:800;flex:0 0 auto;}' +
'.csg-chk{display:flex;align-items:flex-start;gap:.55rem;padding:.5rem .65rem;border:1px solid var(--bd,#d1c6b4);border-radius:10px;background:var(--bgI,#fff);font-size:.88rem;line-height:1.55;color:var(--t1,#202221);word-break:keep-all;margin:.3rem 0;}' +
'.csg-chk input{margin-top:.18rem;width:18px;height:18px;flex:0 0 auto;accent-color:var(--ac,#2f5e67);}' +
'.csg-ul{margin:.2rem 0;padding-left:1.15rem;}' +
'.csg-ul li{font-size:.86rem;line-height:1.6;color:var(--t1,#202221);margin:.15rem 0;word-break:keep-all;}' +
'.csg-meta{font-size:.86rem;color:var(--t2,#4f5552);margin:.1rem 0 .5rem;word-break:keep-all;}' +
'.csg-meta strong{color:var(--t1,#202221);}' +
'.csg-badge-confirm{display:inline-block;font-size:.7rem;font-weight:800;color:var(--cWk,#a85f1c);border:1px solid var(--cWk,#E68A3A);border-radius:999px;padding:.08rem .5rem;margin-left:.3rem;}' +
'.csg-note{background:var(--bg2,#f1ece2);border:1px solid var(--bd,#d1c6b4);border-radius:10px;padding:.6rem .72rem;margin:.4rem 0;font-size:.83rem;line-height:1.6;color:var(--t1,#202221);word-break:keep-all;}' +
'.csg-safety{background:var(--bg2,#f7f3ea);border:1px solid var(--bd,#d1c6b4);border-left:4px solid var(--cWk,#E68A3A);border-radius:10px;padding:.7rem .8rem;margin:.6rem 0 .2rem;font-size:.82rem;line-height:1.6;color:var(--t2,#4f5552);word-break:keep-all;}' +
'.csg-actions{display:flex;flex-wrap:wrap;gap:.45rem;margin:.3rem 0;}' +
'.csg-act-btn{display:inline-flex;align-items:center;min-height:44px;padding:.45rem .9rem;border:1px solid var(--ac,#2f5e67);border-radius:999px;font:inherit;font-size:.84rem;font-weight:700;color:var(--ac,#2f5e67);text-decoration:none;background:transparent;cursor:pointer;}' +
'.csg-act-btn.primary{background:var(--ac,#2f5e67);color:#fff;}' +
'.csg-act-btn:hover{background:var(--acG,rgba(47,94,103,.1));}' +
'.csg-act-btn:focus-visible{outline:3px solid var(--ac,#2f5e67);outline-offset:1px;}' +
'.csg-foot-note{font-size:.74rem;color:var(--t3,#757a76);margin-top:.8rem;word-break:keep-all;}' +
'body.csg-modal-open{overflow:hidden;}' +
'@media (max-width:640px){.csg-overlay{padding:0;align-items:stretch;}.csg-box{width:100%;height:100%;max-height:100%;border-radius:0;}.csg-opts{max-width:none;}.csg-foot-btn{flex:1 1 auto;text-align:center;}}';
    var style = document.createElement('style');
    style.id = 'csgStyles';
    style.textContent = css;
    document.head.appendChild(style);
  }

  /* --------------------------------------------------- recommended-start UI */
  function recStartBlockHtml(code) {
    var secBtn = function (ref, key) {
      return '<button type="button" class="csg-secondary-btn" data-csg-ref="' + ref + '">' + esc(S(key)) + '</button>';
    };
    return '<div class="csg-recstart">' +
      '<p class="csg-eyebrow">' + esc(code + ' · ' + S('eyebrow')) + '</p>' +
      '<h2 class="csg-rec-title" id="csgRecTitle-' + esc(code) + '">' + esc(S('recStartTitle')) + '</h2>' +
      '<p class="csg-rec-body">' + esc(S('recStartBody')) + '</p>' +
      '<button type="button" class="csg-primary-cta" data-csg-start>' + esc(tpl('primaryCtaTpl', code)) + '<span aria-hidden="true">→</span></button>' +
      '<p class="csg-rec-microcopy">' + esc(S('ctaMicrocopy')) + '</p>' +
      '<div class="csg-secondary">' +
        '<span class="csg-secondary-label">' + esc(S('secondaryActionsLabel')) + '</span>' +
        '<div class="csg-secondary-row">' +
          secBtn('subcategories', 'secViewSubcategories') +
          secBtn('commonDocs', 'secViewCommonDocs') +
          secBtn('procedure', 'secViewProcedure') +
          secBtn('sources', 'secViewSources') +
        '</div>' +
      '</div>' +
    '</div>';
  }

  function wireEntry(container, code) {
    var startBtn = container.querySelector('[data-csg-start]');
    if (startBtn) startBtn.addEventListener('click', function () { open(code, { view: 'flow' }); });
    container.querySelectorAll('[data-csg-ref]').forEach(function (btn) {
      btn.addEventListener('click', function () { secondaryAction(code, btn.getAttribute('data-csg-ref')); });
    });
  }

  // Secondary "browse manually" actions delegate to the EXISTING source-backed
  // UI (ParadisoRoute / the card drawer) — no protected data re-rendered here.
  function secondaryAction(code, ref) {
    var R = window.ParadisoRoute;
    try {
      if (ref === 'subcategories' && R && R.openSubcodeSelector && R.openSubcodeSelector(code)) return;
      if (ref === 'procedure' && R && R.openProcedureSelector && R.openProcedureSelector(code, '')) return;
      if ((ref === 'commonDocs' || ref === 'sources') && R && R.start && R.start(code)) return;
      if (R && R.start && R.start(code)) return;
    } catch (e) { /* fall through */ }
    if (typeof openVisaDrawer === 'function') openVisaDrawer(code);
  }

  // Inject the recommended-start block into the card's slot (rendered right after
  // the card summary, before the long subcode/procedure sections). Injected
  // whenever the slot exists — when the card is collapsed the block simply sits
  // in the (hidden) card body and appears at the top once the card is expanded,
  // matching the prior generic-CTA behavior (the six have no separate fallback
  // section, so gating on open-state would leave an expanded card with no CTA).
  function injectRecStart(code) {
    injectStyles();
    var slot = document.querySelector('.external-guide-slot[data-guide-slot="' + (window.CSS && CSS.escape ? CSS.escape(code) : code) + '"]');
    if (!slot) return false;
    slot.innerHTML = '<div class="csg-hero csg-incard">' + recStartBlockHtml(code) + '</div>';
    wireEntry(slot, code);
    return true;
  }

  /* --------------------------------------------------------------- overlay */
  function buildOverlay() {
    if (state.modal) return state.modal;
    injectStyles();
    var overlay = document.createElement('div');
    overlay.className = 'csg-overlay';
    overlay.id = 'csgOverlay';
    overlay.setAttribute('role', 'dialog');
    overlay.setAttribute('aria-modal', 'true');
    overlay.setAttribute('aria-labelledby', 'csgModalTitle');
    overlay.setAttribute('aria-hidden', 'true');
    overlay.innerHTML =
      '<div class="csg-box" role="document">' +
        '<div class="csg-head">' +
          '<div><h2 id="csgModalTitle"></h2><p class="csg-step-count" data-csg-stepcount aria-live="polite"></p></div>' +
          '<button type="button" class="csg-close" data-csg-close aria-label="' + esc(S('close')) + '">✕</button>' +
        '</div>' +
        '<div class="csg-progress" role="progressbar" aria-label="' + esc(S('progressAria')) + '" aria-valuemin="0" aria-valuemax="100" aria-valuenow="0" data-csg-progress>' +
          '<div class="csg-progress-bar" data-csg-progressbar style="width:0%"></div>' +
        '</div>' +
        '<div class="csg-body" id="csgBody"></div>' +
        '<div class="csg-foot" data-csg-foot></div>' +
      '</div>';
    document.body.appendChild(overlay);
    overlay.addEventListener('click', function (e) { if (e.target === overlay) close(); });
    overlay.querySelector('[data-csg-close]').addEventListener('click', close);
    state.modal = overlay;
    return overlay;
  }

  function focusables(container) {
    return Array.prototype.slice.call(container.querySelectorAll(
      'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
    )).filter(function (el) { return !el.disabled && (el.offsetParent !== null || el === document.activeElement); });
  }
  function onKeydown(e) {
    if (!state.modal || !state.modal.classList.contains('open')) return;
    if (e.key === 'Escape') { e.preventDefault(); e.stopPropagation(); close(); return; }
    if (e.key !== 'Tab') return;
    var f = focusables(state.modal);
    if (!f.length) return;
    var first = f[0], last = f[f.length - 1];
    if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
    else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
  }

  function open(code, opts) {
    opts = opts || {};
    if (TARGETS.indexOf(code) === -1) return false;
    var model = getModel(code);
    if (!model) {
      // Data not ready — fall back to the existing guided flow so the CTA never dead-ends.
      try { if (window.ParadisoRoute && window.ParadisoRoute.start && window.ParadisoRoute.start(code)) return true; } catch (e) {}
      if (typeof openVisaDrawer === 'function') { openVisaDrawer(code); return true; }
      return false;
    }
    buildOverlay();
    state.lastFocus = document.activeElement;
    state.code = code;
    state.model = model;
    state.steps = buildSteps(model);
    state.view = 'flow';
    state.stepIndex = 0;
    state.answers = {};
    state.result = null;
    renderGuide();
    state.modal.classList.add('open');
    state.modal.setAttribute('aria-hidden', 'false');
    document.body.classList.add('csg-modal-open');
    if (!state.keyHandler) { state.keyHandler = onKeydown; document.addEventListener('keydown', state.keyHandler, true); }
    focusFirst();
    return true;
  }

  function close() {
    if (!state.modal) return;
    state.modal.classList.remove('open');
    state.modal.setAttribute('aria-hidden', 'true');
    document.body.classList.remove('csg-modal-open');
    if (state.keyHandler) { document.removeEventListener('keydown', state.keyHandler, true); state.keyHandler = null; }
    if (state.lastFocus && typeof state.lastFocus.focus === 'function') { try { state.lastFocus.focus(); } catch (e) {} }
    state.lastFocus = null;
  }

  function focusFirst() {
    if (!state.modal) return;
    var body = state.modal.querySelector('#csgBody');
    var t = (body && body.querySelector('button, a, input, select')) || state.modal.querySelector('[data-csg-close]');
    if (t) { try { t.focus(); } catch (e) {} }
  }

  function setStepCount(txt) { var el = state.modal && state.modal.querySelector('[data-csg-stepcount]'); if (el) el.textContent = txt || ''; }
  function setProgress(pct) {
    if (!state.modal) return;
    pct = Math.max(0, Math.min(100, Math.round(pct)));
    var wrap = state.modal.querySelector('[data-csg-progress]'); var bar = state.modal.querySelector('[data-csg-progressbar]');
    if (bar) bar.style.width = pct + '%';
    if (wrap) wrap.setAttribute('aria-valuenow', String(pct));
  }
  function renderFooter(buttons) {
    var foot = state.modal && state.modal.querySelector('[data-csg-foot]');
    if (!foot) return;
    foot.innerHTML = (buttons || []).map(function (b) {
      return '<button type="button" class="csg-foot-btn' + (b.primary ? ' primary' : '') + '" data-csg-act="' + b.action + '"' + (b.disabled ? ' disabled' : '') + '>' + esc(b.label) + '</button>';
    }).join('');
    foot.querySelectorAll('[data-csg-act]').forEach(function (btn) {
      btn.addEventListener('click', function () { footAction(btn.getAttribute('data-csg-act')); });
    });
  }
  function footAction(a) {
    if (a === 'close') return close();
    if (a === 'back') return goBack();
    if (a === 'next') return goNext();
    if (a === 'restart') { state.view = 'flow'; state.stepIndex = 0; state.answers = {}; state.result = null; renderGuide(); focusFirst(); return; }
    if (a === 'detail') return handoff();
  }

  function handoff() {
    var code = state.code, m = state.result || {};
    close();
    var R = window.ParadisoRoute;
    try {
      if (R && R.goToResult && R.goToResult(code, m.subCode || '', m.procKey || '')) return;
      if (R && R.start && R.start(code)) return;
    } catch (e) {}
    if (typeof openVisaDrawer === 'function') openVisaDrawer(code);
  }

  function renderGuide() {
    if (!state.modal) return;
    if (state.view === 'result') return renderResultView();
    return renderFlow();
  }

  function renderFlow() {
    var titleEl = state.modal.querySelector('#csgModalTitle');
    var body = state.modal.querySelector('#csgBody');
    var step = state.steps[state.stepIndex];
    titleEl.textContent = state.code + ' · ' + S('recStartTitle');
    var n = state.stepIndex + 1, total = state.steps.length;
    setStepCount(csgLang() === 'en' ? (S('stepWord') + ' ' + n + ' / ' + total) : (n + ' / ' + total + ' ' + S('stepWord')));
    setProgress((n / total) * 100);
    body.innerHTML = renderStepHtml(step);
    body.scrollTop = 0;
    wireStep(step, body);
    var answered = !!state.answers[step.id];
    var isLast = state.stepIndex === state.steps.length - 1;
    renderFooter([
      { label: S('back'), action: 'back', disabled: state.stepIndex === 0 },
      { label: isLast ? S('seeResult') : S('next'), action: 'next', primary: true, disabled: !answered }
    ]);
  }

  function renderStepHtml(step) {
    var sel = state.answers[step.id];
    var html = '<div class="csg-step">';
    html += '<h3 class="csg-q-title">' + esc(S(step.qKey)) + '</h3>';
    if (step.helpKey) html += '<p class="csg-q-help">' + esc(S(step.helpKey)) + '</p>';
    html += '<div class="csg-opts" role="radiogroup" aria-label="' + esc(S(step.qKey)) + '">';
    html += step.options.map(function (o) {
      var on = sel === o.id;
      var cls = 'csg-opt' + (o.unsure ? ' csg-opt-unsure' : '');
      var mark = '<span class="csg-opt-mark" aria-hidden="true">' + (on ? '●' : '') + '</span>';
      return '<button type="button" class="' + cls + '" role="radio" aria-checked="' + (on ? 'true' : 'false') + '" data-csg-opt="' + esc(o.id) + '">' + mark + '<span>' + esc(o.label) + '</span></button>';
    }).join('');
    html += '</div>';
    html += '<p class="csg-foot-note">' + esc(S('safetyNote')) + '</p>';
    return html + '</div>';
  }

  function wireStep(step, body) {
    body.querySelectorAll('[data-csg-opt]').forEach(function (btn) {
      btn.addEventListener('click', function () { state.answers[step.id] = btn.getAttribute('data-csg-opt'); renderFlow(); });
    });
  }

  function goNext() {
    var step = state.steps[state.stepIndex];
    if (!state.answers[step.id]) return;
    if (state.stepIndex < state.steps.length - 1) { state.stepIndex++; renderFlow(); focusFirst(); return; }
    state.result = buildResultModel(state.code, state.model, state.answers);
    state.view = 'result';
    renderGuide();
    focusFirst();
  }
  function goBack() {
    if (state.view === 'result') { state.view = 'flow'; renderGuide(); focusFirst(); return; }
    if (state.stepIndex > 0) { state.stepIndex--; renderFlow(); focusFirst(); }
  }

  function numSection(n, titleStr, inner) {
    return '<div class="csg-section"><p class="csg-section-title"><span class="csg-num" aria-hidden="true">' + n + '</span>' + esc(titleStr) + '</p>' + inner + '</div>';
  }

  function renderResultView() {
    var titleEl = state.modal.querySelector('#csgModalTitle');
    var body = state.modal.querySelector('#csgBody');
    var m = state.result;
    titleEl.textContent = state.code + ' · ' + S('recStartTitle');
    setStepCount('');
    setProgress(100);

    var html = '<div class="csg-result" role="status" aria-live="polite">';
    html += '<p class="csg-result-title">' + esc(tpl('resultTitleTpl', state.code)) + '</p>';
    html += '<div class="csg-route-chip">' + esc(m.subLabel || (state.code + ' · ' + S('unsureType'))) + '</div>';
    html += '<p class="csg-meta"><strong>' + esc(S('matchedProcedure')) + ':</strong> ' + esc(m.procLabel || S('unsureProcedure')) + '</p>';
    if (m.noteKey) html += '<div class="csg-note">' + esc(S(m.noteKey)) + '</div>';

    // 1. First steps
    html += numSection('1', S('resFirstSteps'), '<ul class="csg-ul">' + m.firstSteps.map(function (s) { return '<li>' + esc(s) + '</li>'; }).join('') + '</ul>');
    // 2. Basic required documents → safe handoff (no protected data re-rendered)
    html += numSection('2', S('resBasicDocs') + ' ', '<p class="csg-meta">' + esc(S('officialSourceNeedsConfirm')) + '<span class="csg-badge-confirm">' + esc(S('officialSourceNeedsConfirm')) + '</span></p><div class="csg-note">' + esc(S('docsHandoffNote')) + '</div><div class="csg-actions"><button type="button" class="csg-act-btn primary" data-csg-act="detail">' + esc(S('viewFullDetail')) + '</button></div>');
    // 3. Documents that may be added
    html += numSection('3', S('resAddDocs'), '<div class="csg-note">' + esc(S('addDocsNote')) + '</div>');
    // 4. Procedure (generic process list)
    html += numSection('4', S('resProcedure'), '<ol class="csg-ul">' + m.procSteps.map(function (s) { return '<li>' + esc(s) + '</li>'; }).join('') + '</ol>');
    // 5. Official sources → on the detail screen / needs confirmation
    html += numSection('5', S('resSources'), '<div class="csg-note">' + esc(S('sourcesHandoffNote')) + '</div>');
    // 6. Next actions
    html += numSection('6', S('resNextActions'), '<div class="csg-actions">' +
      '<button type="button" class="csg-act-btn primary" data-csg-act="detail">' + esc(S('viewFullDetail')) + '</button>' +
      '<button type="button" class="csg-act-btn" data-csg-copy>' + esc(S('copyChecklist')) + '</button>' +
      '<button type="button" class="csg-act-btn" data-csg-act="restart">' + esc(S('restartShort')) + '</button>' +
    '</div>');

    html += '<div class="csg-safety">' + esc(S('safetyNote')) + '</div>';
    html += '</div>';

    body.innerHTML = html;
    body.scrollTop = 0;
    body.querySelectorAll('[data-csg-act]').forEach(function (btn) {
      btn.addEventListener('click', function () { footAction(btn.getAttribute('data-csg-act')); });
    });
    var copyBtn = body.querySelector('[data-csg-copy]');
    if (copyBtn) copyBtn.addEventListener('click', function () {
      var text = checklistText(state.code, m);
      var done = function (ok) { copyBtn.textContent = ok ? S('copied') : S('copyFail'); setTimeout(function () { copyBtn.textContent = S('copyChecklist'); }, 1800); };
      if (navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText(text).then(function () { done(true); }, function () { done(false); });
      else { try { var ta = document.createElement('textarea'); ta.value = text; ta.style.position = 'fixed'; ta.style.opacity = '0'; document.body.appendChild(ta); ta.select(); document.execCommand('copy'); document.body.removeChild(ta); done(true); } catch (e) { done(false); } }
    });

    renderFooter([
      { label: S('restartShort'), action: 'restart' },
      { label: S('close'), action: 'close', primary: true }
    ]);
  }

  /* ----------------------------------------------------- public API (tests) */
  var api = {
    TARGETS: TARGETS,
    buildSteps: buildSteps,
    buildResultModel: buildResultModel,
    recStartBlockHtml: recStartBlockHtml,
    checklistText: checklistText,
    selectableSubcodes: selectableSubcodes,
    availableProcedures: availableProcedures,
    open: open,
    close: close,
    isOpen: function () { return !!(state.modal && state.modal.classList.contains('open')); },
    S: S, _state: state
  };
  if (typeof globalThis !== 'undefined') globalThis.ParadisoStatusGuide = api;

  if (typeof document === 'undefined') return;

  /* ----------------------------------------------- search-result integration */
  function injectAll() {
    TARGETS.forEach(function (code) { try { injectRecStart(code); } catch (e) { /* non-fatal */ } });
  }
  document.addEventListener('paradiso:results-rendered', function () {
    // Cards render synchronously before this event; inject the recommended-start
    // block at the top of each visible (open) target card.
    injectAll();
  });
  document.addEventListener('paradiso:landing-reset', function () {
    if (state.modal && state.modal.classList.contains('open')) close();
  });
  window.addEventListener('paradiso-language-applied', function () {
    if (state.modal && state.modal.classList.contains('open')) { try { renderGuide(); } catch (e) {} }
    try { injectAll(); } catch (e) {}
  });
})();
