/* ============================================================================
 * Visable — post-search status guidance (September 2026 manuals)
 * ----------------------------------------------------------------------------
 * ANSWER FIRST · CLARIFY WHEN NECESSARY · ACTION SECOND · DOCUMENTS CLEARLY ·
 * EVIDENCE ALWAYS AVAILABLE.
 *
 * Reads the compiled bundle data/status-guidance-202609.json (built from the
 * authored rules by scripts/build_status_coverage_manifest.py; every document
 * item and condition in it is anchored to a page of the 2026-09 manuals) and
 * renders, above the raw manual search results:
 *
 *   1. what Visable understood (status · procedure, editable)
 *   2. one clarifying question at a time — only when the answer changes the
 *      guidance — with "잘 모르겠어요" and back
 *   3. the structured answer for the resolved status/subtype + procedure
 *   4. the document checklist grouped by requirement level
 *   5. next actions and the official evidence (page-level, opens the same
 *      excerpt dialog the manual search uses)
 *
 * Pure functions (interpret / nextStep / compose / renderModel) are exposed on
 * globalThis.VisableStatusGuidance BEFORE the DOM guard so they run in plain
 * Node for scripts/check_status_resolver.mjs and check_document_guidance.mjs.
 *
 * Fail-closed: no guidance entry → SOURCE_ONLY evidence, never a guessed list.
 * ========================================================================== */
(function (root) {
  'use strict';

  var STR = {
    ko: {
      understood: '{status} · {procedure}(으)로 이해했어요', understoodStatusOnly: '{status}(으)로 이해했어요', understoodProcOnly: '{procedure}(으)로 이해했어요',
      edit: '수정', done: '완료', changeStatus: '체류자격 바꾸기', changeProcedure: '절차 바꾸기', searchCode: '코드로 검색',
      askProcedure: '{status}에서 무엇을 하려고 하세요?', askProcedureHint: '절차에 따라 필요한 서류와 조건이 달라요.',
      manyTypes: '{status}에는 여러 체류 유형이 있어요. 정확한 안내를 위해 현재 상황을 조금만 확인할게요.',
      twoTypes: '두 가지 유형이 가능해요. 한 가지만 더 확인할게요.',
      unsure: '잘 모르겠어요', back: '이전 질문', answered: '확인한 내용', change: '변경',
      closest: '현재 정보로는 {target} 안내와 가장 가까워 보여요.', exact: '{target} 기준으로 안내해요.', inherited: '{parent} 공통 기준이 적용돼요. 세부유형별 차이는 없어요.',
      unresolvedTitle: '정확한 세부유형을 아직 확인하지 못했어요',
      unresolvedBody: '아래 유형 중 하나에 해당할 수 있어요. 각 유형의 원문을 확인하거나, 외국인등록증의 체류자격란(예: F-1-5)으로 다시 검색해 보세요.',
      candidates: '가능한 유형', sourceOnlyTitle: '구조화된 안내가 아직 없어요', sourceOnlyBody: '이 항목은 매뉴얼 원문으로만 확인할 수 있어요. 아래 근거 페이지를 열어 확인하세요.',
      notApplicable: '이 절차는 {status}에 해당하지 않아요.', notPermitted: '{status}에서는 이 절차가 원칙적으로 허용되지 않아요.', exceptionOnly: '{status}에서는 예외적인 경우에만 허가돼요.', conditional: '조건에 따라 달라져요.',
      answerTitle: '안내', period: '체류기간', fee: '수수료', timing: '신청 시기', channel: '신청 방법', filer: '신청 주체', conditions: '확인할 조건',
      docsTitle: '준비할 서류', docsPartial: '현재 확인된 기본 서류', docsClarify: '세부유형을 확인하면 정확한 서류 목록을 보여드릴 수 있어요.', docsSourceOnly: '서류 목록은 원문 페이지에서 확인하세요.',
      grpRequired: '필수서류', grpConditional: '상황에 따라 필요한 서류', grpApplicable: '해당자만 제출', grpAlternative: '아래 서류 중 하나', grpOfficer: '심사 과정에서 추가 요청될 수 있음', grpAdmin: '행정정보 공동이용 동의 시 제출 생략 가능', grpPrev: '이미 제출한 경우 생략될 수 있음', grpSource: '원문에 언급되어 있으나 구조화되지 않음', grpNA: '해당 없음', grpLegacy: '기존 소지자만',
      oneOf: '다음 중 하나', role: '준비하는 사람', where: '발급처', validity: '유효기간', origCopy: '원본/사본', apostille: '아포스티유·영사확인 필요', translation: '번역 필요', applies: '적용 조건', notApplies: '생략 조건', notes: '참고', source: '근거', page: '쪽',
      roles: { applicant: '신청인', inviter: '초청인', employer: '고용주', educational_institution: '학교·연수기관', korean_spouse: '한국인 배우자', principal_holder: '주체류자', local_government: '지방자치단체', sponsor: '신원보증인', business_entity: '사업체', ship_owner: '선주·선박회사', agency: '대행기관', medical_institution: '의료기관·유치기관', other_third_party: '제3자' },
      where_labels: { hikorea: '하이코리아·출입국관서 서식', community_center: '주민센터·정부24', bank: '은행', hospital: '의료기관', school: '학교', tax_office: '세무서·홈택스', court: '법원', employment_center: '고용센터', labor_office: '노동관서', kcomwel: '근로복지공단', designated_hospital: '법무부 지정 병원', local_government: '지방자치단체' },
      overlays: '공통으로 확인할 것', officer: '심사 과정에서 추가 서류가 요청되거나 일부 서류가 생략될 수 있습니다.',
      nextTitle: '다음 할 일', nextReserve: '방문예약 안내', nextForms: '통합신청서 작성', nextCall: '1345 외국인종합안내센터', nextAi: '상황이 복잡한가요? Waymaker로 추가 분석', nextLegacy: '기존 체류자격 카드 보기',
      evidenceTitle: '공식 매뉴얼 근거', evidenceCount: '관련 근거 {n}건', open: '본문 펼치기', original: '원문 보기', reviewState: '2026.09 원문 · 검토 전', moreManual: '매뉴얼 원문 검색 결과 더 보기',
      stayManual: '외국인체류 안내매뉴얼', visaManual: '사증발급 안내매뉴얼',
      relatedTitle: '이 체류자격의 다른 절차', programTitle: '특별 제도', transitionTitle: '체류자격 변경 경로', currentStatus: '현재 체류자격', from: '현재', to: '목표',
      legacyStop: '이 체류자격은 {date}부터 신규 발급이 중단되었어요. 기존 소지자에게만 적용돼요.', abolished: '이 세부약호는 폐지되었어요({date}). {superseded}로 정정된 기준을 확인하세요.',
      loading: '체류자격 안내를 불러오는 중이에요.', failed: '체류자격 안내를 불러오지 못했어요. 아래 매뉴얼 원문 검색은 그대로 사용할 수 있어요.', retry: '다시 시도',
      unknownCode: '{code}은(는) 2026년 9월 매뉴얼에서 확인되지 않는 코드예요. 오타가 아닌지 확인하거나 상위 코드로 검색해 보세요.',
      noStatus: '체류자격을 찾지 못했어요', noStatusBody: '체류자격 코드(예: F-6, D-2-1)나 상황(예: 배우자 비자 연장)으로 검색해 보세요. 아래 매뉴얼 원문 검색 결과도 확인할 수 있어요.',
      confidenceLow: '해석이 확실하지 않아요. 맞지 않으면 수정해 주세요.', disclaimer: '2026년 9월 판 매뉴얼 원문을 구조화한 참고 정보이며 법적 효력이 없습니다. 최종 확인은 관할 출입국·외국인관서, 하이코리아, 1345에서 하세요.',
      sourceOnlyEvidence: '원문 확인', stateLabel: { SUPPORTED: '안내 가능', CONDITIONAL: '조건부', NOT_APPLICABLE: '해당 없음', GENERALLY_NOT_PERMITTED: '원칙적 불가', EXCEPTION_ONLY: '예외적 허용', LEGACY_ONLY: '기존 소지자', SOURCE_ONLY: '원문 확인', UNVERIFIED: '미확인' },
      exclusions: '변경이 제한되는 경우', exceptions: '예외', transitionDocs: '제출서류',
      programNote: '일반 코드만으로는 판단할 수 없어요. 아래 조건이 추가로 적용돼요.', dims: '확인 항목', variantsTitle: '특례·예외 상황', relatedPrograms: '일부 대상자에게 적용되는 별도 제도:', understoodProgram: '{program}(으)로 이해했어요',
    },
    en: {
      understood: 'We read this as {status} · {procedure}', understoodStatusOnly: 'We read this as {status}', understoodProcOnly: 'We read this as {procedure}',
      edit: 'Edit', done: 'Done', changeStatus: 'Change status', changeProcedure: 'Change procedure', searchCode: 'Search by code',
      askProcedure: 'What do you want to do with {status}?', askProcedureHint: 'Documents and conditions depend on the procedure.',
      manyTypes: '{status} covers several types of stay. A quick check will make the guidance exact.',
      twoTypes: 'Two types are possible. One more question.',
      unsure: "I'm not sure", back: 'Previous question', answered: 'What you told us', change: 'Change',
      closest: 'Your situation looks closest to the {target} guidance.', exact: 'Guidance for {target}.', inherited: 'The common {parent} rule applies; subtypes are not treated differently.',
      unresolvedTitle: 'We could not pin down the exact subtype yet',
      unresolvedBody: 'One of the types below may apply. Open the original text for each, or search again with the status shown on your residence card (e.g. F-1-5).',
      candidates: 'Possible types', sourceOnlyTitle: 'No structured guidance yet', sourceOnlyBody: 'This item is only available as original manual text. Open the evidence pages below.',
      notApplicable: 'This procedure does not apply to {status}.', notPermitted: 'This procedure is generally not permitted for {status}.', exceptionOnly: 'For {status} this is granted only in exceptional cases.', conditional: 'It depends on conditions.',
      answerTitle: 'Guidance', period: 'Period of stay', fee: 'Fee', timing: 'When to apply', channel: 'How to apply', filer: 'Who files', conditions: 'Conditions to check',
      docsTitle: 'Documents to prepare', docsPartial: 'Basic documents confirmed so far', docsClarify: 'Confirm the subtype to see the exact document list.', docsSourceOnly: 'See the original page for the document list.',
      grpRequired: 'Required', grpConditional: 'Depending on your situation', grpApplicable: 'Only if it applies to you', grpAlternative: 'One of the following', grpOfficer: 'May be requested during review', grpAdmin: 'Can be skipped with consent to administrative data sharing', grpPrev: 'May be skipped if already submitted', grpSource: 'Mentioned in the source but not structured', grpNA: 'Not applicable', grpLegacy: 'Existing holders only',
      oneOf: 'One of', role: 'Prepared by', where: 'Where to get it', validity: 'Validity', origCopy: 'Original / copy', apostille: 'Apostille or consular confirmation required', translation: 'Translation required', applies: 'Applies when', notApplies: 'May be omitted when', notes: 'Notes', source: 'Source', page: 'p.',
      roles: { applicant: 'Applicant', inviter: 'Inviter', employer: 'Employer', educational_institution: 'School / institution', korean_spouse: 'Korean spouse', principal_holder: 'Principal holder', local_government: 'Local government', sponsor: 'Guarantor', business_entity: 'Business', ship_owner: 'Ship owner', agency: 'Agency', medical_institution: 'Hospital / facilitator', other_third_party: 'Third party' },
      where_labels: { hikorea: 'HiKorea / immigration office form', community_center: 'Community center / Gov24', bank: 'Bank', hospital: 'Hospital', school: 'School', tax_office: 'Tax office / Hometax', court: 'Court', employment_center: 'Employment center', labor_office: 'Labour office', kcomwel: 'KCOMWEL', designated_hospital: 'Designated hospital', local_government: 'Local government' },
      overlays: 'Common rules to check', officer: 'The examining officer may request additional documents or waive some of them.',
      nextTitle: 'Next steps', nextReserve: 'Visit reservation guide', nextForms: 'Fill in the application form', nextCall: 'Call 1345 (Immigration Contact Center)', nextAi: 'Complicated situation? Analyse it with Waymaker', nextLegacy: 'Open the existing status card',
      evidenceTitle: 'Official manual evidence', evidenceCount: '{n} related passages', open: 'Read page text', original: 'Open original', reviewState: '2026.09 original · not yet reviewed', moreManual: 'More manual search results',
      stayManual: 'Residence manual', visaManual: 'Visa issuance manual',
      relatedTitle: 'Other procedures for this status', programTitle: 'Special program', transitionTitle: 'Change-of-status path', currentStatus: 'Current status', from: 'From', to: 'To',
      legacyStop: 'New issuance of this status stopped on {date}. It applies to existing holders only.', abolished: 'This subcode was abolished ({date}). See the rule now filed under {superseded}.',
      loading: 'Loading status guidance…', failed: 'Status guidance could not be loaded. The manual search below still works.', retry: 'Try again',
      unknownCode: '{code} is not a code found in the September 2026 manuals. Check for a typo or search the parent code.',
      noStatus: 'No status recognised', noStatusBody: 'Search with a status code (e.g. F-6, D-2-1) or a situation (e.g. spouse visa extension). The manual search results below are still available.',
      confidenceLow: 'This reading is uncertain. Edit it if it is wrong.', disclaimer: 'Structured from the September 2026 manuals for reference only; no legal effect. Confirm with your immigration office, HiKorea or 1345.',
      sourceOnlyEvidence: 'Source only', stateLabel: { SUPPORTED: 'Guidance available', CONDITIONAL: 'Conditional', NOT_APPLICABLE: 'Not applicable', GENERALLY_NOT_PERMITTED: 'Generally not permitted', EXCEPTION_ONLY: 'Exception only', LEGACY_ONLY: 'Existing holders', SOURCE_ONLY: 'Source only', UNVERIFIED: 'Unverified' },
      exclusions: 'When the change is restricted', exceptions: 'Exceptions', transitionDocs: 'Documents',
      programNote: 'The ordinary code alone is not enough. These extra conditions apply.', dims: 'What is checked', variantsTitle: 'Special cases', relatedPrograms: 'Separate schemes that apply to some holders:', understoodProgram: 'We read this as {program}',
    }
  };

  function esc(v) { return String(v == null ? '' : v).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; }); }
  function fmt(s, vars) { return String(s || '').replace(/\{(\w+)\}/g, function (_, k) { return vars && vars[k] != null ? vars[k] : ''; }); }
  function tr(lang, key, vars) { var p = STR[lang] || STR.ko; var v = p[key] != null ? p[key] : STR.ko[key]; return typeof v === 'string' ? fmt(v, vars) : v; }
  function L(lang, obj, k) { return lang === 'en' && obj[k + '_en'] ? obj[k + '_en'] : (obj[k + '_ko'] || obj[k + '_en'] || ''); }
  function LL(lang, obj) { return lang === 'en' && obj.en ? obj.en : (obj.ko || obj.en || ''); }

  var PROCEDURE_ORDER = ['extension', 'status_change', 'registration', 'part_time_work', 'activities_outside_status', 'workplace_change', 'reentry', 'registration_info_report', 'residence_report', 'card_reissue', 'status_grant', 'visa_issuance', 'visa_issuance_confirmation', 'electronic_visa', 'workplace_report', 'program_condition_change'];
  var SHORT_STAY = ['B-1', 'B-2', 'C-1', 'C-3', 'C-4'];

  /* --------------------------------------------------------------- codes --- */
  function normalizeCode(raw, codes) {
    var s = String(raw || '').toUpperCase().replace(/[‐‑‒–—−－]/g, '-').replace(/\s+/g, '');
    var m = s.match(/^([A-H])-?(\d{1,2})(?:-?([0-9A-Z]{1,6}))?$/);
    if (!m) return null;
    var parent = m[1] + '-' + m[2];
    if (!m[3]) {
      if (codes[parent]) return parent;
      if (m[2].length === 2) { var split = m[1] + '-' + m[2][0] + '-' + m[2][1]; if (codes[split]) return split; if (codes[m[1] + '-' + m[2][0]]) return { unknownSub: split, parent: m[1] + '-' + m[2][0] }; }
      return null;
    }
    var sub = parent + '-' + m[3];
    if (codes[sub]) return sub;
    // compact forms: F27 → F-2-7, E74 → E-7-4, D10T, F442 → F-4-42, G15 → G-1-5
    var digits = m[2] + m[3];
    for (var i = 1; i < digits.length; i++) {
      var cand = m[1] + '-' + digits.slice(0, i) + '-' + digits.slice(i);
      if (codes[cand]) return cand;
    }
    return codes[parent] ? { unknownSub: sub, parent: parent } : null;
  }
  function parentOf(code) { var p = String(code).split('-'); return p.slice(0, 2).join('-'); }
  function baseTarget(t) { return String(t).split('#')[0]; }
  function isSubcode(code) { return /^[A-H]-\d{1,2}-/.test(code) || code.indexOf('~') > 0; }

  /* ----------------------------------------------------------- interpret --- */
  function interpret(query, bundle) {
    var q = String(query || '').trim();
    var lower = q.toLowerCase();
    var codes = bundle.codes;
    var out = { query: q, codes: [], unknownCodes: [], aliasCandidates: [], aliasQuestion: null, procedure: null, procedureCandidates: [], preAnswers: {}, confidence: 'LOW', program: null, keywords: [] };
    var codeRe = /([A-Ha-h])\s?-?\s?(\d{1,2})(?:\s?-?\s?([0-9A-Za-z]{1,6}))?(?![A-Za-z0-9])/g;
    var m;
    while ((m = codeRe.exec(q))) {
      var token = m[0].replace(/\s/g, '');
      // a bare letter+digit inside a word (e.g. "e2" in "e2e") is guarded by the lookahead; also skip obvious non-codes
      var n = normalizeCode(token, codes);
      if (!n) continue;
      if (typeof n === 'object') { out.unknownCodes.push(n.unknownSub); if (out.codes.every(function (c) { return c.code !== n.parent; })) out.codes.push({ code: n.parent, exact: false, fromUnknown: n.unknownSub }); continue; }
      if (out.codes.every(function (c) { return c.code !== n; })) out.codes.push({ code: n, exact: isSubcode(n) });
    }
    // aliases (longest term first); only when no explicit code
    if (!out.codes.length) {
      var best = null;
      bundle.aliases.forEach(function (a) {
        a.terms.forEach(function (t) {
          var tl = t.toLowerCase();
          if (lower.indexOf(tl) >= 0 && (!best || tl.length > best.term.length)) best = { term: tl, alias: a };
        });
      });
      if (best) {
        var cands = best.alias.candidates;
        if (cands.length === 1 && cands[0].indexOf('PROGRAM:') === 0) { out.program = cands[0].slice(8); }
        else if (cands.length === 1) { out.codes.push({ code: cands[0], exact: isSubcode(cands[0]), fromAlias: best.term }); }
        else { out.aliasCandidates = cands; out.aliasQuestion = best.alias; }
        out.keywords.push(best.term);
      }
    }
    // procedure keywords: longest matching keyword wins; ties → catalog order
    var procHit = null;
    bundle.procedures.forEach(function (p) {
      p.keywords.forEach(function (k) {
        var kl = k.toLowerCase();
        if (lower.indexOf(kl) >= 0 && (!procHit || kl.length > procHit.len)) procHit = { id: p.id, len: kl.length, kw: k };
      });
    });
    if (procHit) { out.procedure = procHit.id; out.keywords.push(procHit.kw); }
    // pre-answers from family option aliases (e.g. "호텔" → E-9 industry service)
    out.codes.forEach(function (c) {
      var fam = bundle.families[parentOf(c.code)];
      if (!fam) return;
      fam.dimensions.forEach(function (d) {
        d.options.forEach(function (o) {
          (o.aliases || []).forEach(function (a) {
            var al = a.toLowerCase();
            if (al.length >= 2 && lower.indexOf(al) >= 0 && !out.preAnswers[d.id]) { out.preAnswers[d.id] = o.id; out.keywords.push(a); }
          });
        });
      });
    });
    var primary = out.codes[0];
    if (primary && out.procedure) out.confidence = primary.exact ? 'HIGH' : 'HIGH';
    else if (primary) out.confidence = 'MEDIUM';
    else if (out.aliasCandidates.length || out.program) out.confidence = 'MEDIUM';
    if (primary && !out.procedure) {
      var entry = codes[primary.code] || {};
      out.procedureCandidates = PROCEDURE_ORDER.filter(function (pid) { var st = entry.procedures && entry.procedures[pid]; return st && st.s !== 'UNVERIFIED'; });
    }
    return out;
  }

  /* --------------------------------------------------------------- lookup --- */
  function guidanceFor(bundle, target, procedure) {
    return bundle.guidance.filter(function (g) { return g.target === target && g.procedure === procedure; });
  }
  function targetKey(g) { return g.scenario ? g.target + '#' + g.scenario : g.target; }
  function candidateEntries(bundle, code, procedure) {
    // all guidance entries under a parent (or an exact code) for this procedure
    var parent = parentOf(code);
    return bundle.guidance.filter(function (g) {
      if (g.procedure !== procedure) return false;
      var base = baseTarget(g.target).split('~')[0];
      if (isSubcode(code)) return base === code || (g.covers || []).indexOf(code) >= 0;
      return base === parent || parentOf(base) === parent;
    });
  }
  function codeState(bundle, code, procedure) {
    var c = bundle.codes[code];
    return c && c.procedures && c.procedures[procedure] ? c.procedures[procedure] : null;
  }
  function transitionFor(bundle, target, procedure) {
    var hits = bundle.transitions.filter(function (t) { return t.procedure === procedure && (t.to === target || parentOf(t.to) === target); });
    return hits.length ? hits[0] : null;
  }

  /* ----------------------------------------------------------- resolver ---- */
  // state = { interp, answers: {dimId: optionId | 'unsure'}, procedure (override), status (override), skipped: [] }
  function effectiveProcedure(state) { return state.procedure || (state.interp && state.interp.procedure) || null; }
  function effectiveStatus(state) {
    if (state.status) return state.status;
    if (state.interp.codes.length) return state.interp.codes[0].code;
    var a = state.answers.__alias;
    if (a && state.interp.aliasQuestion) {
      var o = state.interp.aliasQuestion.options.filter(function (x) { return x.id === a; })[0];
      if (o) return o.targets[0];
    }
    return null;
  }

  function nextStep(state, bundle) {
    var interp = state.interp;
    var answers = state.answers || {};
    var lang = state.lang || 'ko';
    if (interp.program && !interp.codes.length && !state.status) {
      return { kind: 'program', program: bundle.programs.filter(function (p) { return p.id === interp.program; })[0] };
    }
    // 0. alias ambiguity → which status?
    if (!interp.codes.length && !state.status && interp.aliasQuestion && !answers.__alias) {
      var aq = interp.aliasQuestion;
      return { kind: 'question', dimension: '__alias', question_ko: aq.question_ko, question_en: aq.question_en, options: aq.options, allowUnsure: true, unsure_ko: null, unsure_en: null, why: 'status' };
    }
    if (!interp.codes.length && !state.status && interp.aliasQuestion && answers.__alias === 'unsure') {
      return { kind: 'unresolved', reason: 'status', candidates: interp.aliasCandidates.map(function (c) { return { target: c }; }) };
    }
    var status = effectiveStatus(state);
    if (!status) return { kind: 'no-status' };
    var procedure = effectiveProcedure(state);
    var codeInfo = bundle.codes[status] || {};
    // 1. procedure unknown → ask (options = procedures with a known state)
    if (!procedure) {
      var opts = PROCEDURE_ORDER.filter(function (pid) { var st = codeInfo.procedures && codeInfo.procedures[pid]; return st && st.s !== 'UNVERIFIED' && st.s !== 'NOT_APPLICABLE'; });
      if (!opts.length) opts = ['extension', 'status_change', 'registration'];
      return { kind: 'question', dimension: '__procedure', question_ko: tr('ko', 'askProcedure', { status: status }), question_en: tr('en', 'askProcedure', { status: status }), hint_ko: tr('ko', 'askProcedureHint'), hint_en: tr('en', 'askProcedureHint'),
        options: opts.map(function (pid) { var p = bundle.procedures.filter(function (x) { return x.id === pid; })[0]; var st = codeInfo.procedures[pid]; return { id: pid, ko: p.ko, en: p.en, targets: [pid], state: st ? st.s : null }; }), allowUnsure: false, why: 'procedure' };
    }
    // 2. status change into a target with a transition rule → current status matters
    var transition = procedure === 'status_change' ? transitionFor(bundle, status, procedure) : null;
    if (transition && transition.exclusions && transition.exclusions.length && !answers.current_status) {
      var cq = bundle.current_status_question;
      return { kind: 'question', dimension: 'current_status', question_ko: cq.question_ko, question_en: cq.question_en, options: cq.options, allowUnsure: true, unsure_ko: cq.unsure_ko, unsure_en: cq.unsure_en, why: 'transition' };
    }
    // 3. candidates for the resolved code + procedure
    var exact = isSubcode(status);
    var candidates = candidateEntries(bundle, status, procedure);
    var parent = parentOf(status);
    var fam = bundle.families[parent];
    var dims = fam ? fam.dimensions.filter(function (d) { return !d.procedures || d.procedures.indexOf(procedure) >= 0; }) : [];
    // exact subcode with no own entries: the parent's common rule applies when the manifest says the state is inherited
    var inherited = false;
    if (exact && !candidates.length && inherits(bundle, status, procedure)) {
      candidates = bundle.guidance.filter(function (g) { return g.procedure === procedure && g.target === parent; });
      inherited = !!candidates.length;
    }
    var remaining = candidates.slice();
    var answeredDims = [];
    var chosenCode = null;
    var unsureCount = 0;
    function dimCoverage(d, pool) {
      // how many of the pool entries at least one option of this dimension leads to
      return pool.filter(function (g) { return d.options.some(function (o) { return optionMatches(bundle, d, o, g, procedure); }); }).length;
    }
    dims.forEach(function (d) {
      var a = answers[d.id];
      if (!a) return;
      if (a === 'unsure') { unsureCount += 1; return; }
      var opt = d.options.filter(function (o) { return o.id === a; })[0];
      if (!opt) return;
      // an answer to a dimension that no longer applies to the remaining candidates (e.g. an F-1-5 phase after the
      // stay reason was answered as "student parent") is stale and must not empty the result: ignore it
      if (!dimCoverage(d, remaining)) return;
      answeredDims.push({ dimension: d, option: opt });
      remaining = remaining.filter(function (g) { return optionMatches(bundle, d, opt, g, procedure); });
      if (opt.targets.length === 1 && opt.targets[0].indexOf('#') < 0 && opt.targets[0].indexOf('~') < 0) chosenCode = opt.targets[0];
    });
    if (state.variant) {
      var v = remaining.filter(function (g) { return targetKey(g) === state.variant; });
      if (v.length) remaining = v;
    }
    // 4. ask the next dimension that still splits the remaining candidates
    var distinct = {};
    remaining.forEach(function (g) { distinct[targetKey(g)] = true; });
    var distinctCount = Object.keys(distinct).length;
    if (distinctCount > 1) {
      for (var i = 0; i < dims.length; i++) {
        var d = dims[i];
        if (answers[d.id]) continue;
        if (interp.preAnswers && interp.preAnswers[d.id]) { answers[d.id] = interp.preAnswers[d.id]; return nextStep(state, bundle); }
        // after a "잘 모르겠어요" answer only a dimension that applies to every remaining candidate may still be asked;
        // a refinement question that presupposes the unsure answer would fake certainty
        if (unsureCount && dimCoverage(d, remaining) < remaining.length) continue;
        var buckets = {};
        d.options.forEach(function (o) {
          var hits = remaining.filter(function (g) { return optionMatches(bundle, d, o, g, procedure); });
          if (hits.length) buckets[o.id] = hits.map(targetKey).sort().join('|');
        });
        var keys = Object.keys(buckets);
        var outcomes = {};
        keys.forEach(function (k) { outcomes[buckets[k]] = true; });
        var splits = Object.keys(outcomes).length >= 2 || (keys.length >= 1 && keys.some(function (k) { return buckets[k].split('|').length < distinctCount; }));
        if (splits) {
          return { kind: 'question', dimension: d.id, question_ko: d.question_ko, question_en: d.question_en, options: d.options, allowUnsure: true, unsure_ko: d.unsure_ko, unsure_en: d.unsure_en, why: 'subtype', remaining: distinctCount, answered: answeredDims };
        }
      }
    }
    if (!remaining.length) {
      var st = codeState(bundle, chosenCode || status, procedure) || codeState(bundle, status, procedure) || codeState(bundle, parent, procedure);
      return { kind: 'source-only', status: chosenCode || status, procedure: procedure, state: st ? st.s : 'UNVERIFIED', page: st ? st.p : null, manual: st ? st.m : null, candidates: candidates, answered: answeredDims, transition: transition };
    }
    var uniq = []; var seen = {};
    remaining.forEach(function (g) { var k = targetKey(g); if (!seen[k]) { seen[k] = true; uniq.push(g); } });
    var baseEntries = uniq.filter(function (g) { return !g.scenario; });
    if (uniq.length > 1 && baseEntries.length === 1 && uniq.every(function (g) { return g.target === baseEntries[0].target; })) {
      // one main rule plus special-case variants that no question distinguishes: answer with the main rule, offer the variants
      var main = baseEntries[0];
      return { kind: 'resolved', status: status, procedure: procedure, entries: [main], target: main.target, scenario: null, inherited: inherited || (chosenCode && chosenCode !== main.target), displayCode: chosenCode || (inherited ? status : main.target.split('~')[0]), exact: exact, answered: answeredDims, transition: transition, variants: uniq.filter(function (g) { return g !== main; }), confidence: exact || chosenCode ? 'HIGH' : 'MEDIUM' };
    }
    if (uniq.length > 1) {
      return { kind: 'unresolved', reason: 'subtype', status: status, procedure: procedure, candidates: uniq, answered: answeredDims, transition: transition };
    }
    var entry = uniq[0];
    var covered = exact && entry.target.split('~')[0] !== status && (entry.covers || []).indexOf(status) >= 0;
    var displayCode = chosenCode && chosenCode !== entry.target.split('~')[0] ? chosenCode : (inherited || covered ? status : entry.target.split('~')[0]);
    return { kind: 'resolved', status: status, procedure: procedure, entries: [entry], target: entry.target, scenario: entry.scenario, inherited: inherited || covered || (!!chosenCode && chosenCode !== entry.target.split('~')[0]), displayCode: displayCode, exact: exact, answered: answeredDims, transition: transition, variants: [], confidence: (exact || !dims.length || chosenCode) ? 'HIGH' : (answeredDims.length ? 'MEDIUM' : 'MEDIUM') };
  }

  function inherits(bundle, code, procedure) {
    var c = bundle.codes[code]; var st = c && c.procedures && c.procedures[procedure];
    return !!(st && st.i);
  }
  function scenarioBases(dim) {
    if (dim.__sb) return dim.__sb;
    var s = {};
    dim.options.forEach(function (o) { o.targets.forEach(function (t) { if (t.indexOf('#') > 0) s[baseTarget(t)] = true; }); });
    dim.__sb = s;
    return s;
  }
  // Does an answer option lead to guidance entry g? Targets: 'F-1-5#scenario' (exact scenario), 'F-1~relative-visit'
  // (scenario record), 'F-1-5' (all scenarios of that code unless the dimension itself splits its scenarios), or a
  // code whose procedure inherits the parent rule (E-9-5 → E-9).
  function optionMatches(bundle, dim, option, g, procedure) {
    var bases = scenarioBases(dim);
    var key = targetKey(g);
    return option.targets.some(function (t) {
      if (t.indexOf('#') > 0) return key === t;
      if (t === key) return true;
      if (t === g.target) return !(g.scenario && bases[t]);
      if (parentOf(t) === g.target && inherits(bundle, t, procedure)) return true;
      return false;
    });
  }

  /* --------------------------------------------------------------- compose -- */
  var GROUP_OF = { REQUIRED_BASELINE: 'required', CONDITIONAL_REQUIRED: 'conditional', ADDITIONAL_IF_APPLICABLE: 'applicable', ALTERNATIVE_DOCUMENT: 'applicable', MAY_BE_REQUESTED_BY_OFFICER: 'officer', ADMIN_INFO_CHECKABLE: 'admin', PREVIOUSLY_SUBMITTED_MAY_BE_OMITTED: 'prev', SOURCE_MENTIONS_BUT_NOT_STRUCTURED: 'source', NOT_APPLICABLE: 'na', LEGACY_ONLY: 'legacy' };
  var GROUP_ORDER = ['required', 'conditional', 'applicable', 'admin', 'prev', 'officer', 'source', 'legacy', 'na'];
  var GROUP_LABEL = { required: 'grpRequired', conditional: 'grpConditional', applicable: 'grpApplicable', admin: 'grpAdmin', prev: 'grpPrev', officer: 'grpOfficer', source: 'grpSource', legacy: 'grpLegacy', na: 'grpNA' };

  function groupDocuments(entry) {
    var groups = {};
    var alternatives = {};
    (entry.documents || []).forEach(function (d) {
      var g = GROUP_OF[d.requirement_level] || 'source';
      if (d.administrative_information_exemption && g === 'required') d.adminNote = true;
      if (d.alternatives_group && d.alternatives && d.alternatives.length) { alternatives[d.alternatives_group] = d.alternatives; }
      (groups[g] = groups[g] || []).push(d);
    });
    return GROUP_ORDER.filter(function (g) { return groups[g]; }).map(function (g) { return { key: g, labelKey: GROUP_LABEL[g], items: groups[g] }; });
  }
  function applicableOverlays(bundle, status, procedure, entry) {
    var parent = parentOf(status);
    var docRefs = {};
    (entry && entry.documents || []).forEach(function (d) { docRefs[d.ref] = true; });
    var domain = ['visa_issuance', 'visa_issuance_confirmation', 'electronic_visa'].indexOf(procedure) >= 0 ? 'visa' : 'stay';
    return bundle.overlays.filter(function (o) {
      var s = o.scope || {};
      if (s.domains && s.domains.indexOf(domain) < 0) return false;
      if (s.procedures && s.procedures.indexOf(procedure) < 0) return false;
      if (s.exclude_codes && (s.exclude_codes.indexOf(status) >= 0 || s.exclude_codes.indexOf(parent) >= 0)) return false;
      if (s.include_parents && s.include_parents.indexOf(parent) < 0) return false;
      if (s.requires_doc && !docRefs[s.requires_doc]) return false;
      if (o.kind === 'discretion') return false; // rendered once as the persistent officer note
      if (o.id === 'fee_table') return false;    // the procedure fee is shown in the key facts instead
      return true;
    });
  }
  function feeFor(bundle, procedure, status) {
    var table = bundle.overlays.filter(function (o) { return o.id === 'fee_table'; })[0];
    if (!table) return null;
    var row = table.table.filter(function (r) { return r.procedure === procedure; })[0];
    return row || null;
  }
  function evidenceFor(bundle, step, entries) {
    var list = [];
    var seen = {};
    function push(manual, page, section, kind) {
      if (!page) return;
      var k = manual + ':' + page;
      if (seen[k]) return; seen[k] = true;
      list.push({ manual: manual, page: page, section: section, kind: kind });
    }
    (entries || []).forEach(function (e) { push(e.source.manual, e.source.pdf_page, e.source.section, 'guidance'); });
    if (step.transition) { push(step.transition.manual, step.transition.pdf_page, step.transition.from_allowed_ko ? tr('ko', 'transitionTitle') : '', 'transition'); (step.transition.exclusions || []).forEach(function (ex) { push(step.transition.manual, ex.pdf_page, ex.ko, 'exclusion'); }); }
    if (step.page) push(step.manual === 'visa' ? 'visa_manual_2026_09_01' : 'stay_manual_2026_09_18', step.page, '', 'state');
    (step.candidates || []).forEach(function (c) { if (c.source) push(c.source.manual, c.source.pdf_page, c.source.section, 'candidate'); });
    return list;
  }
  function manualMeta(bundle, manualId) {
    var meta = bundle.sources[manualId] || {};
    return { id: manualId, title_ko: meta.title_ko, title_en: meta.title_en, date: meta.date, edition: meta.edition, file: meta.pdf, corpusId: meta.corpus_source_id };
  }

  function compose(step, state, bundle) {
    var lang = state.lang || 'ko';
    var status = step.status || effectiveStatus(state);
    var procedure = step.procedure || effectiveProcedure(state);
    var codeInfo = status ? (bundle.codes[status] || {}) : {};
    var proc = bundle.procedures.filter(function (p) { return p.id === procedure; })[0] || null;
    var model = { kind: step.kind, lang: lang, status: status, statusName: codeInfo.name_ko, statusNameEn: codeInfo.name_en, procedure: procedure, procedureLabel: proc ? (lang === 'en' ? proc.en : proc.ko) : '', lifecycle: codeInfo.lifecycle, temporal: codeInfo.temporal || {}, programs: [], relatedPrograms: [], step: step };
    var programCode = step.displayCode || (step.entries && step.entries[0] ? step.entries[0].target.split('~')[0] : status);
    var programInfo = bundle.codes[programCode] || codeInfo;
    function byId(id) { return bundle.programs.filter(function (p) { return p.id === id; })[0]; }
    model.programs = (programInfo.programs || []).map(byId).filter(Boolean);
    model.relatedPrograms = (programInfo.related_programs || (programCode !== status ? codeInfo.related_programs : []) || []).map(byId).filter(Boolean);
    var entries = step.entries || [];
    var entry = entries[0] || null;
    model.entry = entry;
    model.target = entry ? entry.target.split('~')[0] : status;
    model.targetInfo = entry ? bundle.codes[entry.target] || bundle.codes[model.target] || {} : codeInfo;
    model.state = entry ? entry.state : (step.state || null);
    model.completeness = entry ? entry.completeness : (step.kind === 'unresolved' ? 'REQUIRES_CLARIFICATION' : 'SOURCE_ONLY');
    model.documentGroups = entry ? groupDocuments(entry) : [];
    model.overlays = status && procedure ? applicableOverlays(bundle, status, procedure, entry) : [];
    model.fee = entry && entry.fee_ko ? { ko: entry.fee_ko, en: entry.fee_en } : (procedure ? feeFor(bundle, procedure, status) : null);
    model.evidence = evidenceFor(bundle, step, entries).map(function (e) { return Object.assign({}, e, manualMeta(bundle, e.manual)); });
    model.transition = step.transition || null;
    model.currentStatus = state.answers && state.answers.current_status || null;
    if (model.transition && model.currentStatus) {
      var cq = bundle.current_status_question || { options: [] };
      var copt = cq.options.filter(function (o) { return o.id === model.currentStatus; })[0];
      var cls = copt && copt.targets && copt.targets.length ? copt.targets[0] : model.currentStatus;
      var ex = model.currentStatus === 'unsure' ? null : model.transition.exclusions.filter(function (x) { return x.class === cls || (x.from || []).indexOf(cls) >= 0; })[0];
      model.transitionOutcome = ex ? { state: ex.state, ko: ex.ko, en: ex.en, exceptions: ex.exceptions || [] } : { state: 'SUPPORTED' };
    }
    model.related = procedure && codeInfo.procedures ? PROCEDURE_ORDER.filter(function (pid) { var st = codeInfo.procedures[pid]; return pid !== procedure && st && ['SUPPORTED', 'CONDITIONAL', 'EXCEPTION_ONLY'].indexOf(st.s) >= 0; }).slice(0, 6) : [];
    model.officerNote = tr(lang, 'officer');
    return model;
  }

  /* ---------------------------------------------------------------- render -- */
  function pageLink(bundle, ev, lang) {
    var file = ev.file || '';
    return '<a class="sg-page" href="' + esc(file) + '#page=' + ev.page + '" target="_blank" rel="noopener">' + esc(lang === 'en' ? ev.title_en : ev.title_ko) + ' · ' + esc(ev.date || '') + ' · ' + ev.page + tr(lang, 'page') + '</a>';
  }
  function stateBadge(lang, st) { if (!st) return ''; var lab = tr(lang, 'stateLabel')[st] || st; return '<span class="sg-state sg-state-' + esc(st.toLowerCase()) + '">' + esc(lab) + '</span>'; }
  function statusLabel(model, code) {
    var lang = model.lang; var info = code === model.status ? { name_ko: model.statusName, name_en: model.statusNameEn } : {};
    var name = lang === 'en' ? (info.name_en || info.name_ko) : info.name_ko;
    return '<span class="sg-code">' + esc(code) + '</span>' + (name ? ' <span class="sg-name">' + esc(name) + '</span>' : '');
  }

  function renderInterpretation(model, state, bundle) {
    var lang = model.lang; var interp = state.interp;
    var status = model.status; var procLabel = model.procedureLabel;
    var text;
    if (model.kind === 'program' && model.step.program) text = tr(lang, 'understoodProgram', { program: LL(lang, { ko: model.step.program.name_ko, en: model.step.program.name_en }) });
    else if (status && procLabel) text = tr(lang, 'understood', { status: status, procedure: procLabel });
    else if (status) text = tr(lang, 'understoodStatusOnly', { status: status });
    else if (procLabel) text = tr(lang, 'understoodProcOnly', { procedure: procLabel });
    else text = tr(lang, 'noStatus');
    var name = status ? (lang === 'en' ? (model.statusNameEn || model.statusName) : model.statusName) : '';
    var html = '<div class="sg-interp" role="status" aria-live="polite"><p class="sg-interp-text">' + esc(text) + (name ? ' <span class="sg-interp-name">' + esc(name) + '</span>' : '') + '</p>';
    if (status || procLabel) html += '<button type="button" class="sg-link" data-sg-action="edit" aria-expanded="' + (state.editing ? 'true' : 'false') + '" aria-controls="sgEditor">' + esc(tr(lang, state.editing ? 'done' : 'edit')) + '</button>';
    html += '</div>';
    if (interp.confidence === 'LOW' && (status || procLabel)) html += '<p class="sg-muted">' + esc(tr(lang, 'confidenceLow')) + '</p>';
    (interp.unknownCodes || []).forEach(function (c) { html += '<p class="sg-warn">' + esc(tr(lang, 'unknownCode', { code: c })) + '</p>'; });
    if (state.editing) {
      var opts = PROCEDURE_ORDER.filter(function (pid) { var c = bundle.codes[status]; var st = c && c.procedures && c.procedures[pid]; return st && st.s !== 'UNVERIFIED'; });
      if (!opts.length) opts = PROCEDURE_ORDER.slice(0, 8);
      html += '<div id="sgEditor" class="sg-editor"><p class="sg-editor-label">' + esc(tr(lang, 'changeProcedure')) + '</p><div class="sg-chips" role="group" aria-label="' + esc(tr(lang, 'changeProcedure')) + '">' +
        opts.map(function (pid) { var p = bundle.procedures.filter(function (x) { return x.id === pid; })[0]; return '<button type="button" class="sg-chip" data-sg-action="set-procedure" data-sg-value="' + esc(pid) + '" aria-pressed="' + (pid === model.procedure) + '">' + esc(lang === 'en' ? p.en : p.ko) + '</button>'; }).join('') + '</div>' +
        '<p class="sg-editor-label">' + esc(tr(lang, 'changeStatus')) + '</p><form class="sg-code-form" data-sg-form="code"><label class="sg-sr" for="sgCodeInput">' + esc(tr(lang, 'searchCode')) + '</label><input id="sgCodeInput" type="text" inputmode="text" autocomplete="off" placeholder="F-1-5" maxlength="12"><button type="submit" class="sg-btn">' + esc(tr(lang, 'searchCode')) + '</button></form></div>';
    }
    return html;
  }

  function renderAnswered(model, step, lang) {
    var list = (step.answered || []).slice();
    if (model.currentStatus) list.push({ dimension: { id: 'current_status' }, option: { ko: tr('ko', 'currentStatus') + ': ' + model.currentStatus, en: tr('en', 'currentStatus') + ': ' + model.currentStatus } });
    if (!list.length) return '';
    return '<div class="sg-answered"><span class="sg-answered-label">' + esc(tr(lang, 'answered')) + '</span>' + list.map(function (a) {
      return '<span class="sg-answered-item">' + esc(LL(lang, a.option)) + ' <button type="button" class="sg-link" data-sg-action="reopen" data-sg-dim="' + esc(a.dimension.id) + '">' + esc(tr(lang, 'change')) + '</button></span>';
    }).join('') + '</div>';
  }

  function renderQuestion(step, model, state) {
    var lang = model.lang;
    var intro = '';
    if (step.why === 'subtype') intro = step.remaining === 2 ? tr(lang, 'twoTypes') : tr(lang, 'manyTypes', { status: model.status });
    var html = '<section class="sg-question" aria-labelledby="sgQuestionTitle" data-sg-dim="' + esc(step.dimension) + '">' + renderAnswered(model, step, lang) +
      (intro ? '<p class="sg-question-intro">' + esc(intro) + '</p>' : '') +
      '<h3 id="sgQuestionTitle" class="sg-question-title" tabindex="-1">' + esc(L(lang, step, 'question')) + '</h3>' + (step.hint_ko ? '<p class="sg-muted">' + esc(L(lang, step, 'hint')) + '</p>' : '') +
      '<div class="sg-options" role="group" aria-labelledby="sgQuestionTitle">' +
      step.options.map(function (o) { return '<button type="button" class="sg-option" data-sg-action="answer" data-sg-dim="' + esc(step.dimension) + '" data-sg-value="' + esc(o.id) + '" aria-pressed="false">' + esc(LL(lang, o)) + (o.state && o.state !== 'SUPPORTED' ? ' ' + stateBadge(lang, o.state) : '') + (o.hint_ko ? '<small>' + esc(L(lang, o, 'hint')) + '</small>' : '') + '</button>'; }).join('') +
      '</div><div class="sg-question-foot">' + (step.allowUnsure ? '<button type="button" class="sg-option sg-option-unsure" data-sg-action="answer" data-sg-dim="' + esc(step.dimension) + '" data-sg-value="unsure">' + esc(tr(lang, 'unsure')) + '</button>' : '') +
      (state.history && state.history.length ? '<button type="button" class="sg-link" data-sg-action="back">' + esc(tr(lang, 'back')) + '</button>' : '') + '</div>' +
      (step.unsure_ko && state.answers[step.dimension] === 'unsure' ? '<p class="sg-muted">' + esc(L(lang, step, 'unsure')) + '</p>' : '') + '</section>';
    return html;
  }

  function renderDocItem(d, lang, bundle, entry) {
    var role = tr(lang, 'roles')[d.applicant_role] || d.applicant_role;
    var where = d.where_to_obtain ? (tr(lang, 'where_labels')[d.where_to_obtain] || d.where_to_obtain) : '';
    var name = lang === 'en' ? d.name_en : d.name_ko;
    var sub = lang === 'en' && d.name_ko ? '<span class="sg-doc-ko" lang="ko">' + esc(d.name_ko) + '</span>' : '';
    var cond = d.applies_when_ko ? '<div class="sg-doc-cond">' + esc(L(lang, d, 'applies_when')) + '</div>' : '';
    var alts = d.alternatives && d.alternatives.length ? '<div class="sg-doc-alts"><span>' + esc(tr(lang, 'oneOf')) + '</span><ul>' + d.alternatives.map(function (a) { return '<li>' + esc(LL(lang, a)) + '</li>'; }).join('') + '</ul></div>' : '';
    var details = [];
    if (role && d.applicant_role !== 'applicant') details.push([tr(lang, 'role'), role]);
    if (where) details.push([tr(lang, 'where'), where]);
    if (d.validity_period) details.push([tr(lang, 'validity'), d.validity_period]);
    if (d.original_or_copy) details.push([tr(lang, 'origCopy'), d.original_or_copy]);
    if (d.does_not_apply_when_ko) details.push([tr(lang, 'notApplies'), L(lang, d, 'does_not_apply_when')]);
    if (d.notes_ko) details.push([tr(lang, 'notes'), L(lang, d, 'notes')]);
    if (d.apostille_required) details.push([tr(lang, 'apostille'), '']);
    if (d.substitute_documents && d.substitute_documents.length) details.push([tr(lang, 'oneOf'), d.substitute_documents.join(', ')]);
    var src = d.source && d.source.pdf_page ? [tr(lang, 'source'), (lang === 'en' ? bundle.sources[entry.source.manual].title_en : bundle.sources[entry.source.manual].title_ko) + ' · ' + d.source.pdf_page + tr(lang, 'page')] : null;
    if (src) details.push(src);
    var body = details.length ? '<dl class="sg-doc-meta">' + details.map(function (p) { return '<div><dt>' + esc(p[0]) + '</dt><dd>' + esc(p[1]) + '</dd></div>'; }).join('') + '</dl>' : '';
    var inner = '<span class="sg-doc-name">' + esc(name) + '</span>' + sub + (d.adminNote ? '<span class="sg-doc-tag">' + esc(tr(lang, 'grpAdmin')) + '</span>' : '');
    if (!body && !cond && !alts) return '<li class="sg-doc"><div class="sg-doc-row">' + inner + '</div></li>';
    return '<li class="sg-doc"><details class="sg-doc-details"><summary class="sg-doc-row">' + inner + '</summary>' + cond + alts + body + '</details></li>';
  }

  function renderDocuments(model, bundle) {
    var lang = model.lang; var entry = model.entry;
    if (!entry) return '';
    var full = entry.completeness === 'FULLY_STRUCTURED';
    var title = full ? tr(lang, 'docsTitle') : tr(lang, 'docsPartial');
    var html = '<section class="sg-docs" aria-labelledby="sgDocsTitle"><h3 id="sgDocsTitle">' + esc(title) + '</h3>';
    if (!model.documentGroups.length) {
      html += '<p class="sg-muted">' + esc(tr(lang, entry.completeness === 'SOURCE_ONLY' ? 'docsSourceOnly' : 'docsClarify')) + '</p></section>';
      return html;
    }
    model.documentGroups.forEach(function (g) {
      html += '<div class="sg-doc-group sg-doc-group-' + g.key + '"><h4>' + esc(tr(lang, g.labelKey)) + '</h4><ul class="sg-doc-list">' + g.items.map(function (d) { return renderDocItem(d, lang, bundle, entry); }).join('') + '</ul></div>';
    });
    if (!full) html += '<p class="sg-muted">' + esc(tr(lang, 'docsClarify')) + '</p>';
    html += '<p class="sg-officer">' + esc(model.officerNote) + '</p></section>';
    return html;
  }

  function renderFacts(model) {
    var lang = model.lang; var e = model.entry; var rows = [];
    if (e && e.period_ko) rows.push([tr(lang, 'period'), L(lang, e, 'period')]);
    if (e && e.timing_ko) rows.push([tr(lang, 'timing'), L(lang, e, 'timing')]);
    if (model.fee) rows.push([tr(lang, 'fee'), LL(lang, model.fee)]);
    if (e && e.channel_ko) rows.push([tr(lang, 'channel'), L(lang, e, 'channel')]);
    if (e && e.filer) rows.push([tr(lang, 'filer'), tr(lang, 'roles')[e.filer] || e.filer]);
    if (!rows.length) return '';
    return '<dl class="sg-facts">' + rows.map(function (r) { return '<div><dt>' + esc(r[0]) + '</dt><dd>' + esc(r[1]) + '</dd></div>'; }).join('') + '</dl>';
  }

  function renderConditions(model) {
    var lang = model.lang; var e = model.entry;
    var conds = e ? (lang === 'en' && e.conditions_en && e.conditions_en.length ? e.conditions_en : e.conditions_ko) : [];
    if (!conds || !conds.length) return '';
    return '<div class="sg-conditions"><h4>' + esc(tr(lang, 'conditions')) + '</h4><ul>' + conds.map(function (c) { return '<li>' + esc(c) + '</li>'; }).join('') + '</ul></div>';
  }

  function renderOverlays(model) {
    var lang = model.lang;
    if (!model.overlays.length) return '';
    return '<section class="sg-overlays" aria-labelledby="sgOverlayTitle"><h3 id="sgOverlayTitle">' + esc(tr(lang, 'overlays')) + '</h3><ul>' + model.overlays.map(function (o) {
      return '<li><details><summary>' + esc(LL(lang, o).split(/[.。]\s/)[0]) + '</summary><p>' + esc(LL(lang, o)) + '</p>' + (o.table && o.kind === 'fee' && !model.fee ? '' : '') + '<p class="sg-muted">' + esc(lang === 'en' ? 'Residence manual' : '외국인체류 안내매뉴얼') + ' · ' + o.pdf_page + tr(lang, 'page') + '</p></details></li>';
    }).join('') + '</ul></section>';
  }

  function renderTransition(model) {
    var lang = model.lang; var t = model.transition;
    if (!t) return '';
    var html = '<section class="sg-transition" aria-labelledby="sgTransitionTitle"><h3 id="sgTransitionTitle">' + esc(tr(lang, 'transitionTitle')) + '</h3>';
    html += '<p><span class="sg-muted">' + esc(tr(lang, 'from')) + '</span> ' + esc(model.currentStatus ? model.currentStatus : (lang === 'en' ? t.from_allowed_en : t.from_allowed_ko)) + ' <span aria-hidden="true">→</span> <span class="sg-muted">' + esc(tr(lang, 'to')) + '</span> <span class="sg-code">' + esc(t.to) + '</span></p>';
    if (model.transitionOutcome && model.transitionOutcome.state !== 'SUPPORTED') {
      html += '<p class="sg-warn">' + stateBadge(lang, model.transitionOutcome.state) + ' ' + esc(LL(lang, model.transitionOutcome)) + '</p>';
      if (model.transitionOutcome.exceptions.length) html += '<h4>' + esc(tr(lang, 'exceptions')) + '</h4><ul>' + model.transitionOutcome.exceptions.map(function (x) { return '<li>' + esc(LL(lang, x)) + '</li>'; }).join('') + '</ul>';
    } else if (t.exclusions && t.exclusions.length) {
      html += '<h4>' + esc(tr(lang, 'exclusions')) + '</h4><ul>' + t.exclusions.map(function (x) { return '<li>' + esc(LL(lang, x)) + '</li>'; }).join('') + '</ul>';
    }
    if (t.conditions_ko && t.conditions_ko.length) html += '<ul>' + (lang === 'en' ? t.conditions_en : t.conditions_ko).map(function (c) { return '<li>' + esc(c) + '</li>'; }).join('') + '</ul>';
    if (t.documents_note_ko) html += '<p class="sg-muted">' + esc(L(lang, t, 'documents_note')) + '</p>';
    if (t.period_ko) html += '<dl class="sg-facts"><div><dt>' + esc(tr(lang, 'period')) + '</dt><dd>' + esc(L(lang, t, 'period')) + '</dd></div></dl>';
    return html + '</section>';
  }

  function renderPrograms(model) {
    var lang = model.lang;
    var related = model.relatedPrograms.length ? '<p class="sg-muted sg-related-programs">' + esc(tr(lang, 'relatedPrograms')) + ' ' + model.relatedPrograms.map(function (p) { return '<button type="button" class="sg-link sg-link-inline" data-sg-action="search" data-sg-value="' + esc(lang === 'en' ? p.name_en : p.name_ko) + '">' + esc(LL(lang, { ko: p.name_ko, en: p.name_en })) + '</button>'; }).join(', ') + '</p>' : '';
    if (!model.programs.length) return related;
    return related + model.programs.map(function (p) {
      return '<section class="sg-program" aria-label="' + esc(tr(lang, 'programTitle')) + '"><p class="sg-kicker">' + esc(tr(lang, 'programTitle')) + '</p><h3>' + esc(LL(lang, { ko: p.name_ko, en: p.name_en })) + '</h3><p>' + esc(tr(lang, 'programNote')) + '</p><p>' + esc(L(lang, p, 'summary')) + '</p><p class="sg-muted">' + esc(tr(lang, 'dims')) + ': ' + esc((lang === 'en' ? p.dimensions_en : p.dimensions_ko).join(' · ')) + ' · ' + (lang === 'en' ? 'Residence manual' : '외국인체류 안내매뉴얼') + ' ' + esc(p.pdf_page) + tr(lang, 'page') + '</p></section>';
    }).join('');
  }

  function renderNext(model) {
    var lang = model.lang;
    var ai = 'ai.html?' + (model.status ? 'visa_code=' + encodeURIComponent(model.status) + '&' : '') + (model.procedure ? 'selected_procedure_key=' + encodeURIComponent(model.procedure) + '&' : '') + 'lang=' + lang;
    return '<section class="sg-next" aria-labelledby="sgNextTitle"><h3 id="sgNextTitle">' + esc(tr(lang, 'nextTitle')) + '</h3><ul>' +
      '<li><button type="button" class="sg-link" data-action="open-hikorea-guide" data-vcode="' + esc(model.status || '') + '">' + esc(tr(lang, 'nextReserve')) + '</button></li>' +
      '<li><a href="form-helper.html">' + esc(tr(lang, 'nextForms')) + '</a></li>' +
      '<li><a href="tel:1345">' + esc(tr(lang, 'nextCall')) + '</a></li>' +
      (model.status ? '<li><button type="button" class="sg-link" data-sg-action="legacy-card">' + esc(tr(lang, 'nextLegacy')) + '</button></li>' : '') +
      '<li class="sg-next-ai"><a href="' + esc(ai) + '">' + esc(tr(lang, 'nextAi')) + '</a></li></ul></section>';
  }

  function renderEvidence(model, bundle) {
    var lang = model.lang;
    if (!model.evidence.length) return '';
    return '<section class="sg-evidence" aria-labelledby="sgEvidenceTitle"><h3 id="sgEvidenceTitle">' + esc(tr(lang, 'evidenceTitle')) + '</h3><p class="sg-muted">' + esc(tr(lang, 'evidenceCount', { n: model.evidence.length })) + ' · ' + esc(tr(lang, 'reviewState')) + '</p><ol class="sg-evidence-list">' +
      model.evidence.map(function (ev, i) {
        return '<li><div class="sg-evidence-meta">' + esc(lang === 'en' ? ev.title_en : ev.title_ko) + ' · ' + esc(ev.date || '') + ' · ' + ev.page + esc(tr(lang, 'page')) + '</div>' + (ev.section ? '<div class="sg-evidence-section">' + esc(ev.section) + '</div>' : '') +
          '<div class="sg-evidence-actions"><button type="button" class="sg-link" data-sg-action="open-page" data-sg-source="' + esc(ev.corpusId) + '" data-sg-page="' + ev.page + '">' + esc(tr(lang, 'open')) + '</button><a href="' + esc(ev.file) + '#page=' + ev.page + '" target="_blank" rel="noopener">' + esc(tr(lang, 'original')) + '</a></div></li>';
      }).join('') + '</ol><button type="button" class="sg-link" data-sg-action="manual-tab">' + esc(tr(lang, 'moreManual')) + '</button></section>';
  }

  function renderRelated(model, bundle) {
    var lang = model.lang;
    if (!model.related.length) return '';
    return '<section class="sg-related" aria-labelledby="sgRelatedTitle"><h3 id="sgRelatedTitle">' + esc(tr(lang, 'relatedTitle')) + '</h3><div class="sg-chips">' + model.related.map(function (pid) { var p = bundle.procedures.filter(function (x) { return x.id === pid; })[0]; return '<button type="button" class="sg-chip" data-sg-action="set-procedure" data-sg-value="' + esc(pid) + '">' + esc(lang === 'en' ? p.en : p.ko) + '</button>'; }).join('') + '</div></section>';
  }

  function renderLifecycle(model) {
    var lang = model.lang; var t = model.temporal || {}; var info = model.targetInfo || {};
    var tt = info.temporal || t;
    if (model.lifecycle === 'legacy_holders_only' || (info.lifecycle === 'legacy_holders_only')) return '<p class="sg-warn">' + esc(tr(lang, 'legacyStop', { date: tt.effective_to || t.effective_to || '' })) + '</p>';
    if (info.lifecycle === 'abolished') return '<p class="sg-warn">' + esc(tr(lang, 'abolished', { date: tt.effective_to || '', superseded: tt.superseded_by || '' })) + '</p>';
    return '';
  }

  function renderAnswer(model, step, bundle, state) {
    var lang = model.lang; var e = model.entry;
    var targetCode = step.displayCode || (e ? e.target.split('~')[0] : model.status);
    var tInfo = bundle.codes[targetCode] || model.targetInfo || {};
    var targetName = lang === 'en' ? (tInfo.name_en || tInfo.name_ko) : tInfo.name_ko;
    var ruleCode = e ? e.target.split('~')[0] : targetCode;
    var lead = step.inherited ? tr(lang, 'inherited', { parent: ruleCode }) : (step.exact || step.confidence === 'HIGH' ? tr(lang, 'exact', { target: targetCode }) : tr(lang, 'closest', { target: targetCode }));
    var html = '<section class="sg-answer" aria-labelledby="sgAnswerTitle">' + renderAnswered(model, step, lang) +
      '<p class="sg-kicker">' + esc(model.procedureLabel) + '</p><h2 id="sgAnswerTitle" class="sg-answer-title" tabindex="-1"><span class="sg-code">' + esc(targetCode) + '</span>' + (targetName ? ' <span class="sg-name">' + esc(targetName) + '</span>' : '') + (e && e.scenario && e.source ? ' <span class="sg-scenario">' + esc(e.source.section.split(' — ').pop().replace(/^[가-하]\.\s*/, '')) + '</span>' : '') + '</h2>' +
      '<p class="sg-lead">' + esc(lead) + '</p>' + renderLifecycle(model);
    if (model.state && model.state !== 'SUPPORTED') {
      var key = model.state === 'NOT_APPLICABLE' ? 'notApplicable' : model.state === 'GENERALLY_NOT_PERMITTED' ? 'notPermitted' : model.state === 'EXCEPTION_ONLY' ? 'exceptionOnly' : model.state === 'CONDITIONAL' ? 'conditional' : null;
      if (key) html += '<p class="sg-warn">' + stateBadge(lang, model.state) + ' ' + esc(tr(lang, key, { status: targetCode })) + '</p>';
    }
    if (e) html += '<p class="sg-summary">' + esc(L(lang, e, 'summary')) + '</p>';
    html += renderFacts(model) + renderConditions(model);
    if (step.variants && step.variants.length) {
      html += '<div class="sg-variants"><h4>' + esc(tr(lang, 'variantsTitle')) + '</h4><ul class="sg-candidates">' + step.variants.map(function (g) { return '<li><button type="button" class="sg-candidate" data-sg-action="pick-variant" data-sg-target="' + esc(targetKey(g)) + '"><span>' + esc(g.source.section.split(' — ').pop()) + '</span><small>' + esc(L(lang, g, 'summary').slice(0, 120)) + '</small></button></li>'; }).join('') + '</ul></div>';
    }
    html += '</section>';
    html += renderTransition(model) + renderPrograms(model) + renderDocuments(model, bundle) + renderOverlays(model) + renderNext(model) + renderEvidence(model, bundle) + renderRelated(model, bundle);
    return html;
  }

  function renderUnresolved(model, step, bundle, state) {
    var lang = model.lang;
    var html = '<section class="sg-answer sg-unresolved" aria-labelledby="sgAnswerTitle">' + renderAnswered(model, step, lang) + '<p class="sg-kicker">' + esc(model.procedureLabel) + '</p><h2 id="sgAnswerTitle" class="sg-answer-title" tabindex="-1">' + esc(tr(lang, 'unresolvedTitle')) + '</h2><p class="sg-lead">' + esc(tr(lang, 'unresolvedBody')) + '</p>' + renderLifecycle(model);
    html += '<h3>' + esc(tr(lang, 'candidates')) + '</h3><ul class="sg-candidates">' + (step.candidates || []).map(function (g) {
      var code = g.target ? g.target.split('~')[0] : ''; var info = bundle.codes[g.target] || bundle.codes[code] || {};
      var name = lang === 'en' ? (info.name_en || info.name_ko) : info.name_ko;
      var sec = g.source ? g.source.section : '';
      return '<li><button type="button" class="sg-candidate" data-sg-action="pick-target" data-sg-target="' + esc(targetKey(g)) + '"><span class="sg-code">' + esc(code) + '</span> ' + esc(name || '') + (sec ? '<small>' + esc(sec) + '</small>' : '') + '</button>' + (g.state ? stateBadge(lang, g.state) : '') + '</li>';
    }).join('') + '</ul></section>';
    html += renderTransition(model) + renderPrograms(model) + renderNext(model) + renderEvidence(model, bundle) + renderRelated(model, bundle);
    return html;
  }

  function renderSourceOnly(model, step, bundle, state) {
    var lang = model.lang;
    var key = step.state === 'NOT_APPLICABLE' ? 'notApplicable' : step.state === 'GENERALLY_NOT_PERMITTED' ? 'notPermitted' : step.state === 'EXCEPTION_ONLY' ? 'exceptionOnly' : null;
    var html = '<section class="sg-answer sg-source-only" aria-labelledby="sgAnswerTitle">' + renderAnswered(model, step, lang) + '<p class="sg-kicker">' + esc(model.procedureLabel) + '</p><h2 id="sgAnswerTitle" class="sg-answer-title" tabindex="-1"><span class="sg-code">' + esc(model.status) + '</span>' + (model.statusName ? ' <span class="sg-name">' + esc(lang === 'en' ? (model.statusNameEn || model.statusName) : model.statusName) + '</span>' : '') + '</h2>' + renderLifecycle(model);
    if (key) html += '<p class="sg-warn">' + stateBadge(lang, step.state) + ' ' + esc(tr(lang, key, { status: model.status })) + '</p>';
    else html += '<p class="sg-lead">' + stateBadge(lang, step.state || 'SOURCE_ONLY') + ' ' + esc(tr(lang, 'sourceOnlyTitle')) + '</p><p>' + esc(tr(lang, 'sourceOnlyBody')) + '</p>';
    html += '</section>' + renderTransition(model) + renderPrograms(model) + renderNext(model) + renderEvidence(model, bundle) + renderRelated(model, bundle);
    return html;
  }

  function renderProgram(step, state, bundle) {
    var lang = state.lang || 'ko'; var p = step.program;
    if (!p) return '';
    return '<section class="sg-answer" aria-labelledby="sgAnswerTitle"><p class="sg-kicker">' + esc(tr(lang, 'programTitle')) + '</p><h2 id="sgAnswerTitle" class="sg-answer-title" tabindex="-1">' + esc(LL(lang, { ko: p.name_ko, en: p.name_en })) + '</h2><p class="sg-lead">' + esc(L(lang, p, 'summary')) + '</p><p class="sg-muted">' + esc(tr(lang, 'dims')) + ': ' + esc((lang === 'en' ? p.dimensions_en : p.dimensions_ko).join(' · ')) + '</p><div class="sg-chips">' + p.codes.map(function (c) { return '<button type="button" class="sg-chip" data-sg-action="search" data-sg-value="' + esc(c) + '">' + esc(c) + '</button>'; }).join('') + '</div></section>' +
      '<section class="sg-evidence" aria-labelledby="sgEvidenceTitle"><h3 id="sgEvidenceTitle">' + esc(tr(lang, 'evidenceTitle')) + '</h3><ol class="sg-evidence-list"><li><div class="sg-evidence-meta">' + esc(lang === 'en' ? 'Residence manual' : '외국인체류 안내매뉴얼') + ' · ' + esc(p.pdf_page) + tr(lang, 'page') + '</div><div class="sg-evidence-actions"><button type="button" class="sg-link" data-sg-action="open-page" data-sg-source="stay_manual_2026_09_18_pdf" data-sg-page="' + esc(p.pdf_page) + '">' + esc(tr(lang, 'open')) + '</button><a href="' + esc(p.file) + '#page=' + esc(p.pdf_page) + '" target="_blank" rel="noopener">' + esc(tr(lang, 'original')) + '</a></div></li></ol></section>';
  }

  function renderModel(step, state, bundle) {
    var lang = state.lang || 'ko';
    var model = compose(step, state, bundle);
    var html = renderInterpretation(model, state, bundle);
    if (step.kind === 'question') html += renderQuestion(step, model, state);
    else if (step.kind === 'resolved') html += renderAnswer(model, step, bundle, state);
    else if (step.kind === 'unresolved') html += renderUnresolved(model, step, bundle, state);
    else if (step.kind === 'source-only') html += renderSourceOnly(model, step, bundle, state);
    else if (step.kind === 'program') html += renderProgram(step, state, bundle);
    else if (step.kind === 'no-status') html += '<section class="sg-answer"><h2 class="sg-answer-title" tabindex="-1">' + esc(tr(lang, 'noStatus')) + '</h2><p class="sg-lead">' + esc(tr(lang, 'noStatusBody')) + '</p></section>';
    html += '<p class="sg-disclaimer">' + esc(tr(lang, 'disclaimer')) + '</p>';
    return { html: html, model: model };
  }

  var api = { STR: STR, normalizeCode: normalizeCode, interpret: interpret, nextStep: nextStep, compose: compose, renderModel: renderModel, groupDocuments: groupDocuments, applicableOverlays: applicableOverlays, candidateEntries: candidateEntries, PROCEDURE_ORDER: PROCEDURE_ORDER, esc: esc, parentOf: parentOf };
  root.VisableStatusGuidance = api;

  /* ------------------------------------------------------------------ DOM -- */
  if (typeof document === 'undefined') return;

  var bundle = null, loadPromise = null, host = null, state = null, lastQuery = '';
  function lang() { return document.documentElement.lang === 'en' ? 'en' : 'ko'; }
  function load() {
    if (bundle) return Promise.resolve(bundle);
    if (loadPromise) return loadPromise;
    loadPromise = fetch('data/status-guidance-202609.json').then(function (r) { if (!r.ok) throw new Error('HTTP ' + r.status); return r.json(); }).then(function (b) { bundle = b; return b; }).catch(function (e) { loadPromise = null; throw e; });
    return loadPromise;
  }
  function ensureHost() {
    if (host && host.isConnected) return host;
    host = document.getElementById('statusGuidance');
    if (!host) {
      host = document.createElement('section');
      host.id = 'statusGuidance'; host.className = 'sg'; host.setAttribute('aria-labelledby', 'sgHeading');
      var main = document.getElementById('mainContent');
      var tabs = document.getElementById('civicResultTabs');
      if (tabs && tabs.parentNode === main) main.insertBefore(host, tabs); else if (main) main.prepend(host);
    }
    return host;
  }
  function storageKey(q) { return 'visable.sg.' + q; }
  function saveState() { try { sessionStorage.setItem(storageKey(state.query), JSON.stringify({ answers: state.answers, procedure: state.procedure, status: state.status, history: state.history, variant: state.variant || null })); } catch (e) { /* ignore */ } }
  function restoreState(q) { try { var raw = sessionStorage.getItem(storageKey(q)); return raw ? JSON.parse(raw) : null; } catch (e) { return null; } }

  function render(focusTarget) {
    var h = ensureHost();
    if (!state) { h.innerHTML = ''; return; }
    state.lang = lang();
    var step = nextStep(state, bundle);
    var out = renderModel(step, state, bundle);
    h.innerHTML = '<h2 id="sgHeading" class="sg-sr">' + esc(tr(state.lang, 'answerTitle')) + '</h2>' + out.html;
    h.setAttribute('data-sg-kind', step.kind);
    document.body.setAttribute('data-sg-kind', step.kind);
    saveState();
    if (focusTarget) {
      var f = h.querySelector('#sgQuestionTitle, #sgAnswerTitle');
      if (f) { try { f.focus({ preventScroll: false }); } catch (e) { f.focus(); } }
    }
    document.dispatchEvent(new CustomEvent('visable:guidance-rendered', { detail: { query: state.query, kind: step.kind, target: step.target || null, procedure: step.procedure || null } }));
  }
  function start(query) {
    query = String(query || '').trim();
    if (!query) { state = null; if (host) host.innerHTML = ''; return; }
    var h = ensureHost();
    lastQuery = query;
    h.innerHTML = '<p class="sg-load" role="status">' + esc(tr(lang(), 'loading')) + '</p>';
    load().then(function () {
      if (lastQuery !== query) return;
      var interp = interpret(query, bundle);
      var saved = restoreState(query);
      state = { query: query, interp: interp, answers: saved ? saved.answers : {}, procedure: saved ? saved.procedure : null, status: saved ? saved.status : null, history: saved ? (saved.history || []) : [], variant: saved ? saved.variant : null, editing: false, lang: lang() };
      render(false);
    }).catch(function () {
      if (lastQuery !== query) return;
      h.innerHTML = '<div class="sg-failed" role="status"><p>' + esc(tr(lang(), 'failed')) + '</p><button type="button" class="sg-btn" data-sg-action="retry">' + esc(tr(lang(), 'retry')) + '</button></div>';
    });
  }
  function submitSearch(value) {
    var input = document.getElementById('civicQuery') || document.getElementById('q');
    var q = document.getElementById('q');
    if (q) q.value = value;
    if (typeof executeSearch === 'function' && q) { executeSearch(); }
    else if (input) { input.value = value; var form = input.closest('form'); if (form) form.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true })); }
  }
  document.addEventListener('click', function (event) {
    var btn = event.target.closest('[data-sg-action]');
    if (!btn || !host || !host.contains(btn)) return;
    var action = btn.getAttribute('data-sg-action');
    if (action === 'retry') { start(lastQuery); return; }
    if (!state) return;
    if (action === 'answer') {
      var dim = btn.getAttribute('data-sg-dim'); var val = btn.getAttribute('data-sg-value');
      state.history.push({ answers: JSON.parse(JSON.stringify(state.answers)), procedure: state.procedure, status: state.status });
      state.variant = null;
      if (dim === '__procedure') state.procedure = val;
      else if (dim === '__alias') { state.answers.__alias = val; if (val !== 'unsure') { var o = state.interp.aliasQuestion.options.filter(function (x) { return x.id === val; })[0]; if (o) state.status = o.targets[0]; } }
      else state.answers[dim] = val;
      render(true); return;
    }
    if (action === 'back') { var prev = state.history.pop(); if (prev) { state.answers = prev.answers; state.procedure = prev.procedure; state.status = prev.status; state.variant = prev.variant || null; } render(true); return; }
    if (action === 'reopen') { var d = btn.getAttribute('data-sg-dim'); state.history.push({ answers: JSON.parse(JSON.stringify(state.answers)), procedure: state.procedure, status: state.status }); delete state.answers[d]; if (d === 'current_status') delete state.answers.current_status; render(true); return; }
    if (action === 'edit') { state.editing = !state.editing; render(false); if (state.editing) { var inp = host.querySelector('#sgCodeInput'); if (inp) inp.focus(); } return; }
    if (action === 'set-procedure') { state.history.push({ answers: JSON.parse(JSON.stringify(state.answers)), procedure: state.procedure, status: state.status }); state.procedure = btn.getAttribute('data-sg-value'); state.editing = false; render(true); return; }
    if (action === 'pick-target') {
      var t = btn.getAttribute('data-sg-target'); var base = baseTarget(t);
      // choose the family option that leads to this target so the answered chips stay truthful
      var fam = bundle.families[parentOf(base.split('~')[0])];
      state.history.push({ answers: JSON.parse(JSON.stringify(state.answers)), procedure: state.procedure, status: state.status });
      if (fam) fam.dimensions.forEach(function (dm) { dm.options.forEach(function (o) { if (o.targets.indexOf(t) >= 0 || o.targets.indexOf(base) >= 0) state.answers[dm.id] = o.id; }); });
      if (isSubcode(base) && base.indexOf('~') < 0) state.status = base;
      render(true); return;
    }
    if (action === 'pick-variant') { state.history.push({ answers: JSON.parse(JSON.stringify(state.answers)), procedure: state.procedure, status: state.status, variant: state.variant }); state.variant = btn.getAttribute('data-sg-target'); render(true); return; }
    if (action === 'search') { submitSearch(btn.getAttribute('data-sg-value')); return; }
    if (action === 'open-page') {
      var src = btn.getAttribute('data-sg-source'); var pg = Number(btn.getAttribute('data-sg-page'));
      if (window.VisableCivicSearch && typeof window.VisableCivicSearch.openPage === 'function') window.VisableCivicSearch.openPage(src, pg, btn);
      return;
    }
    if (action === 'manual-tab') { var tab = document.querySelector('[data-cs-tab="manual"]'); if (tab) { tab.click(); tab.focus(); } return; }
    if (action === 'legacy-card') { var card = document.querySelector('#rlist article.vc'); var tabAll = document.querySelector('[data-cs-tab="guide"]'); if (tabAll) tabAll.click(); if (card) { card.scrollIntoView({ block: 'start', behavior: 'smooth' }); var hd = card.querySelector('.vc-h'); if (hd) hd.setAttribute('tabindex', '-1'), hd.focus(); } return; }
  });
  document.addEventListener('submit', function (event) {
    var form = event.target.closest && event.target.closest('[data-sg-form="code"]');
    if (!form || !state) return;
    event.preventDefault();
    var val = form.querySelector('input').value.trim();
    var n = normalizeCode(val, bundle.codes);
    if (typeof n === 'string') { state.history.push({ answers: JSON.parse(JSON.stringify(state.answers)), procedure: state.procedure, status: state.status }); state.status = n; state.answers = {}; state.editing = false; render(true); }
    else { form.querySelector('input').setAttribute('aria-invalid', 'true'); }
  });
  document.addEventListener('paradiso:results-rendered', function (event) { start(event.detail && event.detail.query); });
  document.addEventListener('paradiso:landing-reset', function () { state = null; lastQuery = ''; if (host) host.innerHTML = ''; document.body.removeAttribute('data-sg-kind'); });
  window.addEventListener('paradiso-language-applied', function () { if (state && bundle) render(false); });
  if (document.body.classList.contains('searched')) { var q0 = document.getElementById('q'); if (q0 && q0.value) start(q0.value); }
})(typeof globalThis !== 'undefined' ? globalThis : this);
