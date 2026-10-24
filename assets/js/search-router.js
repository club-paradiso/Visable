/* ============================================================================
 * Visable — search intent router (procedure-first)
 * ----------------------------------------------------------------------------
 * A query is not "a visa code plus a keyword". This layer extracts, separately:
 *
 *   status / substatus      (codes, aliases — via VisableStatusGuidance.interpret)
 *   procedure               (object × action composition, then keyword fallback)
 *   object                  (card, passport, address, school, name, residence proof)
 *   office                  (관할 관서 lexicon from data/local-practice-202609.json)
 *   program                 (special status programs; user programs such as GKS)
 *   user conditions         (reissue reason, kind of change)
 *   natural-language intent (question form + facet: documents / fee / how / …)
 *
 * and classifies the query into one of
 *
 *   STATUS_ONLY · STATUS_PROCEDURE · PROCEDURE_ONLY · ADMINISTRATIVE_TASK ·
 *   NATURAL_LANGUAGE_QUESTION · SPECIAL_PROGRAM · AMBIGUOUS · UNKNOWN
 *
 * The procedure registry in the guidance bundle (procedure_registry) says what
 * context each procedure needs (STATUS_INDEPENDENT … CONTEXT_DEPENDENT). The
 * router turns that into `needs` so the resolver can serve a status-independent
 * baseline (card reissue, address report) instead of asking for a code that
 * would not change the answer.
 *
 * Pure: exposed on globalThis.VisableSearchRouter for Node tests. No DOM.
 * ========================================================================== */
(function (root) {
  'use strict';

  var INTENTS = ['STATUS_ONLY', 'STATUS_PROCEDURE', 'PROCEDURE_ONLY', 'ADMINISTRATIVE_TASK', 'NATURAL_LANGUAGE_QUESTION', 'SPECIAL_PROGRAM', 'AMBIGUOUS', 'UNKNOWN'];

  /* ------------------------------------------------------------- lexicons -- */
  var OBJECTS = {
    card: ['외국인등록증', '등록증', '거소증', '영주증', 'arc', 'residence card', 'registration card', 'alien card', 'alien registration', 'foreigner card', 'id card', '外国人登录证', '登录证', '居留卡', '外国人居留证', 'thẻ cư trú', 'thẻ người nước ngoài', 'thẻ arc', 'kartu tinggal', 'kartu registrasi orang asing', 'kartu arc', 'بطاقة الإقامة', 'بطاقة تسجيل الأجانب', 'بطاقة أجنبي', 'بطاقة الهوية', 'بطاقة arc', '外国人登録証', '登録証', '在留カード'],
    registration_info: ['외국인등록사항', '등록사항', 'registration information', 'registered information', 'registration details', '登录事项', '外国人登录事项', 'thông tin đăng ký người nước ngoài', 'informasi registrasi', 'بيانات تسجيل الأجانب', 'معلومات التسجيل', 'تفاصيل التسجيل', '登録事項', '外国人登録事項'],
    passport: ['여권', 'passport', '护照', 'hộ chiếu', 'paspor', 'جواز السفر', 'جواز سفر', 'パスポート', '旅券'],
    address: ['주소', '체류지', '거주지', '이사', '전입', 'address', 'moved', 'moving', 'new place', 'relocat', '地址', '居住地', '搬家', '迁入', 'địa chỉ', 'chuyển nhà', 'nơi cư trú', 'alamat', 'tempat tinggal', 'pindah rumah', 'عنوان', 'مكان الإقامة', 'تغيير السكن', 'نقل سكن', '住所', '居住地', '引越し', '引っ越し'],
    school: ['학교', '전학', '소속기관', '소속 기관', 'school', 'university', 'institution', '学校', '大学', '机构', 'trường học', 'đại học', 'cơ quan', 'sekolah', 'universitas', 'lembaga', 'جامعة', 'مدرسة', 'مؤسسة تعليمية'],
    name: ['이름', '성명', '개명', '국적 변경', '국적이 바뀌', '생년월일', 'my name', 'nationality change', 'date of birth', '姓名', '改名', '国籍变更', 'họ tên', 'đổi tên', 'thay đổi quốc tịch', 'nama', 'ganti nama', 'perubahan kewarganegaraan', 'اسم', 'تغيير الاسم', 'تغيير الجنسية', 'تاريخ الميلاد', '氏名', '改名', '国籍変更'],
    residence_proof: ['체류지입증', '체류지 입증', '체류지 증명', '체류지서류', '체류지 서류', '거주 증명', '주거 증명', '임대차', '숙소제공', 'proof of residence', 'lease', 'housing proof', 'proof of address', '滞留地证明', '居住证明', '租房合同', '租赁合同', 'chứng minh nơi cư trú', 'hợp đồng thuê nhà', 'bukti tempat tinggal', 'surat sewa rumah', 'إثبات الإقامة', 'عقد إيجار', 'عقد سكن', 'إثبات السكن', '滞在地立証書類', '賃貸借契約書', '居住証明'],
  };
  var ACTIONS = {
    reissue: ['재발급', '다시 발급', '재 발급', '잃어버', '잃었', '분실', '없어졌', '훼손', '헐어', '헐었', '찢어', '깨졌', '망가', '기재란', '적는 난', 'reissue', 're-issue', 'reissuance', 'lost', 'missing', 'damaged', 'broken', 'worn', 'replace', 'replacement', 'new card', '补发', '补办', '重新补发', '遗失', '丢失', '破损', '损坏', 'cấp lại', 'làm lại', 'bị mất', 'làm mất', 'bị hỏng', 'hư hỏng', 'penerbitan ulang', 'cetak ulang', 'hilang', 'kehilangan', 'rusak', 'إعادة إصدار', 'فقدان', 'ضياع', 'مفقود', 'تالف', 'كسر', 'تلف', 'استبدال', '再交付', '再発行', '紛失', '破損'],
    register: ['외국인등록', '외국인 등록', '등록하', '등록 하', '발급받', '발급 받', '신규 발급', '처음 발급', '처음 받', 'register', 'registration', 'first card', 'get a card', 'apply for a card', '外国人登录', '新办', '首次办理', '申领', 'đăng ký cư trú', 'đăng ký người nước ngoài', 'làm thẻ lần đầu', 'cấp mới', 'pendaftaran orang asing', 'buat kartu pertama', 'bikin kartu baru', 'تسجيل الأجانب', 'تسجيل الإقامة', 'إصدار بطاقة أولى', 'تسجيل', '外国人登録', '新規登録'],
    change: ['변경', '바꾸', '바뀌', '바꿨', '바꿔', '신고', '갱신', '수정', '업데이트', 'change', 'changed', 'update', 'report', 'renewed passport', 'new passport', '变更', '更改', '换签', '修改', '申报', 'thay đổi', 'chuyển đổi', 'khai báo', 'cập nhật', 'ubah', 'mengubah', 'perubahan', 'lapor', 'pembaruan', 'تغيير', 'تعديل', 'تبديل', 'إبلاغ', 'تحديث', '在留資格変更', '資格変更', '変更', '申告'],
    extend: ['연장', '기간 연장', 'extend', 'extension', 'renew', '延期', '续签', '延长', 'gia hạn', 'kéo dài thời gian cư trú', 'perpanjang', 'perpanjangan izin tinggal', 'perpanjangan visa', 'perpanjangan', 'تجديد', 'تمديد', 'تمديد الإقامة', 'تجديد التأشيرة', '在留期間更新', '期間更新', '更新', '期間延長', '延長'],
    move: ['이사', '이사했', '이사 했', '전입', 'moved', 'move', 'relocat', '搬家', '搬迁', 'chuyển nhà', 'chuyển địa chỉ', 'pindah', 'pindah rumah', 'نقل سكن', 'تغيير السكن', 'انتقال', '引越し', '引っ越し', '転居'],
  };
  var QUESTION_RE = /\?|؟|？|어떻게|어떡|뭐\s*필요|무엇|무슨|필요해|필요한가|필요하나|필요할까|필요 ?해요|얼마|되나요|되나|될까|돼\b|돼요|할 수 있|하려면|할려면|하고 싶|알려|가능해|가능한가|맞지|맞나|맞아|아닌가|\bhow\b|\bwhat\b|\bwhich\b|\bcan i\b|\bdo i\b|\bneed\b|\bshould\b|\bis it\b|\bare\b.*\brequired\b|怎么|如何|什么|需要什么|多少钱|可以吗|行不行|能否|làm sao|thế nào|cần gì|bao nhiêu|được không|có được không|bagaimana|gimana|apa saja|berapa|bisa tidak|apakah bisa|كيف|ماذا|هل يمكن|كم|ما هي|ما هو|هل أحتاج/i;
  var FACETS = [
    ['fee', /수수료|비용|얼마|납부|수입인지|면제|감경|할인|\bfee\b|\bcost\b|\bprice\b|\bpay\b|exempt|费用|手续费|多少钱|lệ phí|chi phí|tiền|biaya|tarif|ongkos|رسوم|تكلفة|كم يكلف/i],
    ['documents', /서류|준비물|준비해|챙겨|뭐 필요|필요한 것|필요해|입증|증명서|사본|원본|documents?|papers?|\bneed\b|\bbring\b|prepare|checklist|材料|文件|材料清单|hồ sơ|giấy tờ|dokumen|berkas|syarat|أوراق|مستندات|وثائق|متطلبات/i],
    ['deadline', /기한|언제까지|며칠|일 이내|기간 안|deadline|within \d+|how long|by when|期限|截止时间|几天以内|thời hạn|hạn chót|trong vòng|tenggat|batas waktu|berapa hari|مهلة|كم يوم|خلال|موعد نهائي/i],
    ['eligibility', /가능|되나|될까|할 수 있|허용|자격이 되|해도 되|can i|allowed|eligible|possible|可以吗|具备资格|được không|có được|bisa tidak|bolehkah|هل يجوز|هل يحق|مسموح/i],
    ['how', /어떻게|어떡|절차|방법|순서|어디서|어디에|\bhow\b|\bwhere\b|process|procedure|steps|怎么|如何|流程|在哪|办理方式|thế nào|làm sao|thủ tục|ở đâu|bagaimana|cara|prosedur|di mana|كيف|طريقة|إجراءات|أين/i],
  ];
  var USER_PROGRAMS = [
    { id: 'gks', terms: ['gks', '정부초청장학', '정부 초청 장학', '정부초청 장학', 'korean government scholarship', 'government scholarship', '국비장학생', '국비 장학생'], statusCandidates: ['D-2', 'D-4'] },
  ];
  var PASSPORT_ONLY_REISSUE = /여권\s*(재발급|갱신|renew)|passport\s*(renew|reissue)|(تجديد|إعادة إصدار)\s*جواز\s*السفر/i;
  var FORM_WORDS = /원본|사본|original|copy|copies|photocop/i;
  // Everyday phrasings the procedure keywords (근무처 변경, 이직, 외국인등록) do not cover. They are
  // consulted only when nothing else matched, so an explicit procedure word always wins.
  var WORKPLACE_MOVE = /(직장|회사|일자리|근무지|일터)\s*(을|를|이|가)?\s*(바꾸|바꿨|바꿔|바뀌|바뀐|옮기|옮겼|옮겨|옮길|변경)|\b(change|changed|changing|switch|switched|switching)\s+(my\s+|of\s+)?(job|jobs|employer|company)\b|换工作|换雇主|chuyển\s+(nơi\s+làm\s+việc|công\s+việc)|pindah\s+kerja|تغيير\s+مكان\s+العمل/i;
  var FIRST_ARRIVAL = /처음|최초|입국\s*(후|하고|해서|했)|한국에\s*(와서|왔|도착)|막\s*왔|\bfirst\b|just arrived|newly arrived|after arriving/i;

  function lower(s) { return String(s || '').toLowerCase(); }
  function hasTerm(text, term) { return text.indexOf(lower(term)) >= 0; }
  function findTerms(text, list) { var hits = []; list.forEach(function (t) { if (hasTerm(text, t)) hits.push(t); }); return hits; }
  function longest(hits) { return hits.slice().sort(function (a, b) { return b.length - a.length; })[0] || null; }

  /* --------------------------------------------------------- extraction -- */
  function extractObjects(text) {
    var out = {};
    Object.keys(OBJECTS).forEach(function (k) { var h = findTerms(text, OBJECTS[k]); if (h.length) out[k] = longest(h); });
    return out;
  }
  function stripObjects(text, objects) {
    var out = text;
    Object.keys(objects).forEach(function (k) { OBJECTS[k].forEach(function (t) { out = out.split(lower(t)).join(' '); }); });
    return out;
  }
  function extractActions(text) {
    var out = {};
    Object.keys(ACTIONS).forEach(function (k) { var h = findTerms(text, ACTIONS[k]); if (h.length) out[k] = longest(h); });
    return out;
  }
  function extractOffice(text, localPractice) {
    var offices = (localPractice && localPractice.offices) || [];
    var best = null;
    offices.forEach(function (o) {
      (o.aliases || []).forEach(function (a) {
        var al = lower(a);
        if (al.length < 2) return;
        // Korean aliases match as substrings ("제주에서"); Latin aliases need word boundaries ("jeju" not "jejudo…")
        var ok = /[a-z]/.test(al) ? new RegExp('(^|[^a-z])' + al.replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + '($|[^a-z])').test(text) : text.indexOf(al) >= 0;
        if (ok && (!best || al.length > best.alias.length)) best = { id: o.id, name_ko: o.name_ko, name_en: o.name_en, alias: al };
      });
    });
    return best;
  }
  function extractUserProgram(text) {
    for (var i = 0; i < USER_PROGRAMS.length; i++) { if (findTerms(text, USER_PROGRAMS[i].terms).length) return USER_PROGRAMS[i]; }
    return null;
  }
  var REISSUE_REASON_FALLBACK = {
    lost: ['분실', '잃어버', '잃었', '없어졌', 'lost', 'missing', '遗失', '丢失', 'mất', 'bị mất', 'hilang', 'kehilangan', 'فقدان', 'مفقود', 'ضياع'],
    damaged: ['훼손', '헐', '찢어', '깨졌', '망가', 'damaged', 'broken', 'worn', '破损', '损坏', 'hỏng', 'bị hỏng', 'rusak', 'تالف', 'تلف', 'مكسور'],
    no_space: ['기재란', '적는 난', '칸이 부족', 'no space', '满页', 'hết chỗ', 'penuh', 'لا توجد مساحة'],
    status_change: ['자격 변경 후', '자격변경 후', 'after status change', '变更加签后', 'sau khi đổi visa', 'setelah ganti visa', 'بعد تغيير الإقامة'],
    info_change: ['이름 바뀌', '개명', '국적 변경', '국적이 바뀌', 'name change', '改名', 'đổi tên', 'ganti nama', 'تغيير الاسم']
  };

  function extractReissueReason(text, bundle) {
    var dim = bundle && bundle.reissue_reason;
    var best = null;
    if (dim) {
      dim.options.forEach(function (o) { (o.aliases || []).forEach(function (a) { var al = lower(a); if (hasTerm(text, al) && (!best || al.length > best.len)) best = { id: o.id, len: al.length }; }); });
    }
    Object.keys(REISSUE_REASON_FALLBACK).forEach(function (rid) {
      REISSUE_REASON_FALLBACK[rid].forEach(function (a) {
        var al = lower(a);
        if (hasTerm(text, al) && (!best || al.length > best.len)) best = { id: rid, len: al.length };
      });
    });
    return best ? best.id : null;
  }
  function facetOf(text) {
    for (var i = 0; i < FACETS.length; i++) { if (FACETS[i][1].test(text)) return FACETS[i][0]; }
    return null;
  }

  /* ------------------------------------------------- procedure composition -- */
  // Returns { procedure, candidates, why } from object × action, or null to fall back to keywords.
  function composeProcedure(text, objects, actions) {
    if (PASSPORT_ONLY_REISSUE.test(text) && !actions.change && !objects.card && !objects.registration_info) {
      return { procedure: null, candidates: [], why: 'passport_reissue_is_not_immigration', hint: 'passport_reissue' };
    }
    if (objects.registration_info) return { procedure: 'registration_info_report', candidates: ['registration_info_report'], why: 'object:registration_info' };
    if (objects.passport && (actions.change || actions.reissue) && (objects.card || actions.change)) {
      // "여권 바뀌었어", "외국인등록증에 여권번호 바꾸려면", "여권 재발급 후 신고" → registration-information report
      return { procedure: 'registration_info_report', candidates: ['registration_info_report'], why: 'object:passport+change', changeKind: 'passport' };
    }
    if (objects.card && actions.reissue) return { procedure: 'card_reissue', candidates: ['card_reissue'], why: 'object:card+reissue' };
    if (objects.card && actions.register && !actions.reissue) return { procedure: 'registration', candidates: ['registration'], why: 'object:card+register' };
    if (objects.card && !actions.register && !actions.change && !actions.extend) {
      return { procedure: null, candidates: ['card_reissue', 'registration'], why: 'object:card only', ambiguous: true };
    }
    if (actions.reissue && !objects.passport && !objects.school && !objects.address) return { procedure: 'card_reissue', candidates: ['card_reissue'], why: 'action:reissue (card assumed)', assumedObject: 'card' };
    // "체류지 입증서류" is a document about the address, not an address change: only an explicit move/change makes it a report.
    if (objects.address && !(objects.residence_proof && !actions.move && !actions.change) && (actions.change || actions.move || !actions.extend)) return { procedure: 'residence_report', candidates: ['residence_report'], why: 'object:address' };
    if (objects.school && actions.change) return { procedure: 'registration_info_report', candidates: ['registration_info_report'], why: 'object:school+change', changeKind: 'school' };
    if (objects.name && actions.change) return { procedure: 'registration_info_report', candidates: ['registration_info_report'], why: 'object:name+change', changeKind: 'name' };

    // 1. Extension: actions.extend without passport-only reissue
    if (actions.extend && !objects.passport) {
      return { procedure: 'extension', candidates: ['extension'], why: 'action:extend' };
    }

    // 2. Status change intent: requires explicit status/visa change phrase
    var STATUS_CHANGE_TERMS = /换签|换签证|chuyển\s*đổi\s*visa|chuyển\s*đổi\s*tư\s*cách|ganti\s*visa|ubah\s*status|تغيير\s*(وضع\s*الإقامة|التأشيرة|الإقامة)|체류자격\s*변경|자격\s*변경|在留資格変更|資格変更|\bstatus\s*change\b|\bchange\s*status\b|\bchange\s*visa\b|\bswitch\s*visa\b/i;
    var hasVisaOrStatusWord = /비자|체류자격|자격|visa|status|tư\s*cách|إقامة|تأشيرة|滞留资格|签证|在留資格|在留/i.test(text);
    if (STATUS_CHANGE_TERMS.test(text) || (actions.change && hasVisaOrStatusWord && !objects.card && !objects.passport && !objects.school && !objects.name && !objects.address)) {
      return { procedure: 'status_change', candidates: ['status_change'], why: 'action:change_status' };
    }

    return null;
  }

  function registryFor(bundle, procedure) {
    var reg = (bundle && bundle.procedure_registry) || [];
    for (var i = 0; i < reg.length; i++) if (reg[i].procedure === procedure) return reg[i];
    return null;
  }

  /* ----------------------------------------------------------------- route -- */
  function route(query, bundle, opts) {
    opts = opts || {};
    var SG = root.VisableStatusGuidance;
    var q = String(query || '').trim();
    var text = lower(q);
    var interp = SG && typeof SG.interpret === 'function' ? SG.interpret(q, bundle, { noRouter: true }) : { codes: [], aliasCandidates: [], aliasQuestion: null, procedure: null, program: null, preAnswers: {}, keywords: [], confidence: 'LOW', unknownCodes: [] };
    var objects = extractObjects(text);
    // Actions are matched on the text with the object words removed, so "외국인등록증" never yields the
    // action "외국인등록" and "registration card" never yields "registration".
    var actions = extractActions(stripObjects(text, objects));
    var composed = composeProcedure(text, objects, actions);
    var procedure = composed && composed.procedure ? composed.procedure : ((composed && (composed.ambiguous || composed.hint)) ? null : interp.procedure);
    var candidates = composed && composed.candidates && composed.candidates.length ? composed.candidates : (procedure ? [procedure] : []);
    // A keyword-only "registration" hit caused by an object word (arc / residence card) is not a procedure.
    if (!composed && interp.procedure === 'registration' && objects.card && !actions.register) { procedure = null; candidates = ['card_reissue', 'registration']; composed = { ambiguous: true, why: 'keyword registration from object word' }; }
    if (!procedure && !candidates.length && !composed) {
      if (WORKPLACE_MOVE.test(text)) { procedure = 'workplace_change'; candidates = [procedure]; composed = { procedure: procedure, candidates: candidates, why: 'phrase:workplace move' }; }
      else if (actions.register && FIRST_ARRIVAL.test(text) && !objects.school && !objects.passport) { procedure = 'registration'; candidates = [procedure]; composed = { procedure: procedure, candidates: candidates, why: 'phrase:first registration' }; }
    }
    var office = extractOffice(text, opts.localPractice || (bundle && bundle.local_practice) || null);
    var userProgram = extractUserProgram(text);
    var isQuestion = QUESTION_RE.test(q) || (q.length > 18 && /[가-힣]{2,}(요|죠|어|까|나)\s*$/.test(q));
    var facet = isQuestion ? facetOf(text) : facetOf(text);
    var status = interp.codes.length ? interp.codes[0].code : null;
    var statusExact = !!(interp.codes.length && interp.codes[0].exact);
    // A user program can stand in for the status family (GKS → student statuses) so the question is not a dead end.
    var aliasQuestion = interp.aliasQuestion || null;
    var statusCandidates = interp.aliasCandidates || [];
    if (!status && !aliasQuestion && userProgram && userProgram.statusCandidates && bundle && bundle.aliases) {
      var studentAlias = bundle.aliases.filter(function (a) { return a.candidates.join(',') === userProgram.statusCandidates.join(','); })[0];
      if (studentAlias) { aliasQuestion = studentAlias; statusCandidates = studentAlias.candidates; }
    }
    var conditions = {};
    if (procedure === 'card_reissue' || (candidates.indexOf('card_reissue') >= 0)) { var r = extractReissueReason(text, bundle); if (r) conditions.reissue_reason = r; }
    if (composed && composed.changeKind) conditions.change_kind = composed.changeKind;
    if (objects.residence_proof) conditions.document_focus = 'residence_proof';
    if (userProgram) conditions.program = userProgram.id;
    // False-premise questions without a procedure: never confirm a universal rule. The renderer answers with the
    // procedure-specific evidence the bundle actually holds (form varies by procedure; office ≠ baseline).
    var hint = composed && composed.hint || null;
    if (!procedure && !candidates.length && FORM_WORDS.test(text) && (objects.passport || objects.residence_proof || objects.card)) hint = 'form_varies';
    if (!procedure && office && objects.residence_proof) hint = 'local_premise';
    var registry = procedure ? registryFor(bundle, procedure) : null;
    var requirement = registry ? registry.context_requirement : null;
    var needs = [];
    if (procedure && !status && !aliasQuestion) {
      if (requirement === 'STATUS_INDEPENDENT' || requirement === 'STATUS_OPTIONAL') { /* nothing blocks */ }
      else needs.push('status');
    }
    // classification
    var structure;
    if (interp.program && !procedure && !status) structure = 'SPECIAL_PROGRAM';
    else if (procedure && (status || aliasQuestion)) structure = 'STATUS_PROCEDURE';
    else if (procedure && !status) structure = (requirement === 'STATUS_INDEPENDENT' || requirement === 'STATUS_OPTIONAL') ? 'ADMINISTRATIVE_TASK' : 'PROCEDURE_ONLY';
    else if (!procedure && candidates.length > 1) structure = 'AMBIGUOUS';
    else if (!procedure && status) structure = 'STATUS_ONLY';
    else if (!procedure && aliasQuestion) structure = 'AMBIGUOUS';
    else structure = 'UNKNOWN';
    var intent = isQuestion && structure !== 'UNKNOWN' ? 'NATURAL_LANGUAGE_QUESTION' : structure;
    if (isQuestion && structure === 'UNKNOWN') intent = 'UNKNOWN';
    var confidence = 'LOW';
    if (procedure && (status || requirement === 'STATUS_INDEPENDENT' || requirement === 'STATUS_OPTIONAL')) confidence = 'HIGH';
    else if (procedure || status || interp.program) confidence = 'MEDIUM';
    if (composed && composed.assumedObject) confidence = 'MEDIUM';
    return {
      query: q, intent: intent, structure: structure, isQuestion: isQuestion, facet: facet,
      status: status, statusExact: statusExact, statusCandidates: statusCandidates, aliasQuestion: aliasQuestion,
      substatus: statusExact ? status : null,
      procedure: procedure, procedureCandidates: candidates, procedureAmbiguous: !!(composed && composed.ambiguous),
      procedureWhy: composed ? composed.why : (interp.procedure ? 'keyword' : null), hint: hint, hintObject: hint === 'form_varies' ? (objects.passport ? 'passport' : (objects.residence_proof ? 'residence_proof' : 'card')) : null,
      object: Object.keys(objects)[0] || null, objects: objects, actions: actions,
      office: office, program: interp.program || null, userProgram: userProgram ? userProgram.id : null,
      conditions: conditions, contextRequirement: requirement, registry: registry, needs: needs,
      confidence: confidence, interp: interp,
    };
  }

  // Route on the relationships in a question, never length alone. Short factual
  // questions and one status change stay in the deterministic search.
  function assessComplexity(query) {
    var q = String(query || '').trim();
    var topics = [
      /연장|만료|extend|extension|expir/i,
      /자격\s*변경|비자\s*변경|change\s*(my\s*)?(visa|status)|switch\s*(visa|status)/i,
      /출국|재입국|돌아오|다녀|leave\s*korea|re.?entry|travel|return\s*to/i,
      /이사|주소|전입|address|moved/i,
      /취업|근무처|이직|알바|아르바이트|workplace|employer|part.time|job/i,
      /혼인|결혼|이혼|배우자|marri|divorc|spouse/i,
      /등록증|외국인등록|residen(t|ce)\s*(card|registration)|\barc\b/i
    ].filter(function (re) { return re.test(q); }).length;
    var linked = /동시에|그런데|하지만|만약|경우|중인데|하면서|하고.*(싶|해야|가능)|뒤에|전에|후에|if\b|while\b|but\b|before\b|after\b|at the same time/i.test(q);
    var questions = (q.match(/[?？]/g) || []).length;
    var codes = q.toUpperCase().match(/[A-H]\s*-\s*\d{1,2}(?:\s*-\s*(?:\d+|T))?/g) || [];
    var compare = /비교|차이|다른\s*점|어느|어떤.*(유리|낫)|중.*(유리|낫)|compare|differen|\bvs\.?(?=\s|$)|versus|which.*(better|best)/i.test(q);
    var exception = /거절|불허|위반|초과체류|불법체류|기간.*(넘|지났)|refus|denied|overstay|violation/i.test(q);
    var complex = (topics >= 2 && (linked || questions >= 2)) || (codes.length >= 2 && compare) || (exception && topics >= 2 && q.length >= 35);
    return { complex: complex, reason: complex ? (compare ? 'comparison' : exception ? 'exception' : 'multiple_procedures') : 'single_lookup', topics: topics };
  }

  var api = { route: route, assessComplexity: assessComplexity, INTENTS: INTENTS, WORKPLACE_MOVE: WORKPLACE_MOVE, FIRST_ARRIVAL: FIRST_ARRIVAL, OBJECTS: OBJECTS, ACTIONS: ACTIONS, facetOf: facetOf, extractOffice: extractOffice, composeProcedure: composeProcedure, registryFor: registryFor };
  root.VisableSearchRouter = api;
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
})(typeof globalThis !== 'undefined' ? globalThis : this);
