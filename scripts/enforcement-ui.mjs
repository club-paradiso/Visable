const $ = (selector, root = document) => root.querySelector(selector);
const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];

let structuredCase = null;
let currentStep = 1;
let analysisSequence = 0;
let sessionNarrative = '';
let sessionLocale = 'ko-KR';
const skippedClarifications = new Set();
const analysisCache = new Map();

const violationLabels = {
  STATUS_OUTSIDE_ACTIVITY_ART20: '체류자격에서 허용된 범위를 벗어난 활동을 필요한 허가 없이 한 상황',
  UNAUTHORIZED_STAY_OR_WORK_ART18_1: '취업할 수 있는 체류자격 없이 일을 한 상황',
  UNAUTHORIZED_EMPLOYMENT_ART18_2: '허가된 근무처가 아닌 곳에서 일을 한 상황',
  UNAUTHORIZED_WORKPLACE_CHANGE_ART21_1: '필요한 근무처 변경·추가 허가 없이 다른 근무처에서 일을 한 상황',
  OVERSTAY_ART25: '허가된 체류기간이 지난 뒤에도 계속 체류한 상황',
};

function resolveApiBase() {
  const configured = document.querySelector('meta[name="api-base"]')?.content?.trim();
  if (configured) return configured.replace(/\/+$/, '');

  if (window.VisableBackend && typeof window.VisableBackend.origin === 'function') {
    return window.VisableBackend.origin();
  }

  const override = window.PARADISO_BACKEND_URL?.trim();
  if (override) return override.replace(/\/+$/, '');

  const local = location.hostname === 'localhost'
    || location.hostname === '127.0.0.1'
    || location.protocol === 'file:';
  return local ? '' : null;
}

const apiBase = resolveApiBase();

function escapeHtml(value) {
  return String(value ?? '').replace(/[&<>'"]/g, (character) => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;'
  })[character]);
}

function localTodayIso() {
  const now = new Date();
  const local = new Date(now.getTime() - now.getTimezoneOffset() * 60000);
  return local.toISOString().slice(0, 10);
}

function setAssessmentDateToday({ force = false } = {}) {
  const input = $('#assessment-date');
  if (!input) return;
  input.max = localTodayIso();
  if (force || !input.value) input.value = localTodayIso();
}

function resolveAssessmentDate() {
  const input = $('#assessment-date');
  const today = localTodayIso();
  const value = input?.value || '';
  if (!/^\d{4}-\d{2}-\d{2}$/.test(value)) return today;
  if (value > today) return today;
  return value;
}

function showStep(number, { scroll = true } = {}) {
  currentStep = number;
  document.body.dataset.enforcementStep = String(number);
  let activeSection = null;
  $$('[data-step]').forEach((section) => {
    const active = Number(section.dataset.step) === number;
    section.hidden = !active;
    if (active) activeSection = section;
  });
  $$('[data-step-nav]').forEach((button) => {
    const value = Number(button.dataset.stepNav);
    button.disabled = value > number;
    button.classList.toggle('is-active', value === number);
    if (value === number) button.setAttribute('aria-current', 'step');
    else button.removeAttribute('aria-current');
  });
  if (scroll && activeSection) {
    requestAnimationFrame(() => {
      activeSection.scrollIntoView({ block: 'start', behavior: 'auto' });
      activeSection.querySelector('h2')?.focus({ preventScroll: true });
    });
  }
}

function setLoading(active, title = '사례를 정리하고 있어요.', detail = '필요한 사실을 빠르게 구조화하고 있습니다.') {
  const loading = $('#loading');
  loading.hidden = !active;
  $('#loading-title').textContent = title;
  $('#loading-detail').textContent = detail;
  document.body.setAttribute('aria-busy', String(active));
}

function setBusy(form, active) {
  if (!form) return;
  const submit = form.querySelector('button[type="submit"]');
  if (submit) submit.disabled = active;
}

function setError(target, message = '') {
  target.textContent = message;
  target.hidden = !message;
}

async function request(path, payload, { timeoutMs = 30000 } = {}) {
  if (apiBase == null) {
    throw new Error('Visable 분석 서버 주소를 확인하지 못했습니다. 페이지를 새로고침해 주세요.');
  }

  const url = `${apiBase}${path}`;
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const response = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
      body: JSON.stringify(payload), cache: 'no-store', signal: controller.signal,
    });
    // Keep the abort active through the body, not just until response headers.
    if (!(response.headers.get('content-type') || '').includes('application/json')) {
      throw new Error(`분석 서버 응답 형식을 확인하지 못했습니다. (${response.status})`);
    }
    const data = await response.json();
    if (!response.ok) {
      const friendly = {
        'case text is required': '사례 설명을 입력해 주세요.',
        'invalid assessmentDate': '분석 기준일 형식을 확인해 주세요.',
        'invalid structured enforcement case': '확인한 사실 중 형식이 맞지 않는 항목이 있습니다. 입력값을 다시 확인해 주세요.',
      }[data.detail];
      throw new Error(friendly || `분석 서버 요청에 실패했습니다. (${response.status})`);
    }
    if (!data || typeof data !== 'object') throw new Error('분석 서버의 응답을 확인하지 못했습니다. 다시 시도해 주세요.');
    return data;
  } catch (error) {
    if (error?.name === 'AbortError') throw new Error('분석 시간이 길어져 요청을 멈췄습니다. 잠시 후 다시 시도해 주세요.');
    if (error instanceof TypeError || error instanceof SyntaxError) throw new Error('Visable 분석 서버에 연결하지 못했습니다. 잠시 후 다시 시도해 주세요.');
    throw error;
  } finally {
    clearTimeout(timer);
  }
}

function detectLocale(text) {
  const value = String(text || '');
  if (/[가-힣]/.test(value)) return 'ko-KR';
  if (/[ぁ-んァ-ン]/.test(value)) return 'ja-JP';
  if (/[一-鿿]/.test(value)) return 'zh-CN';
  if (/[Ѐ-ӿ]/.test(value)) return 'ru-RU';
  if (/[؀-ۿ]/.test(value)) return 'ar';
  if (/[฀-๿]/.test(value)) return 'th-TH';
  const browserLocale = String(navigator.language || 'en-US');
  return browserLocale.startsWith('ko') ? 'en-US' : browserLocale;
}

function isKoreanLocale() {
  return sessionLocale.toLowerCase().startsWith('ko');
}

function normalizeStatus(value) {
  const clean = String(value || '').trim().toUpperCase();
  const match = clean.match(/^([A-HM])\s*-?\s*(\d{1,2})(?:\s*-?\s*(\d{1,2}))?$/);
  if (!match) return clean.slice(0, 20);
  return `${match[1]}-${Number(match[2])}${match[3] ? `-${Number(match[3])}` : ''}`;
}

function removeUnknownFacts(caseData, labels) {
  const blocked = new Set(labels);
  caseData.unknownFacts = (caseData.unknownFacts || []).filter((item) => !blocked.has(item));
}

function deriveViolationAfterStatus(caseData) {
  if (caseData.violationCode) return;
  const status = String(caseData.statusOfStay || '').toUpperCase();
  const candidates = new Set(caseData.violationCandidates || []);
  if (/^D-(?:2|4)(?:-|$)/.test(status) && candidates.has('STATUS_OUTSIDE_ACTIVITY_ART20')) {
    caseData.violationCode = 'STATUS_OUTSIDE_ACTIVITY_ART20';
  } else if (/^(?:B-1|B-2|C-1|C-3)(?:-|$)/.test(status) && candidates.has('UNAUTHORIZED_STAY_OR_WORK_ART18_1')) {
    caseData.violationCode = 'UNAUTHORIZED_STAY_OR_WORK_ART18_1';
  }
  if (caseData.violationCode) {
    caseData.violationCandidates = [caseData.violationCode];
    removeUnknownFacts(caseData, ['구체적인 위반 유형', '취업 가능 체류자격인지 및 지정 근무처·근무처 변경 관계']);
  }
}

function deterministicSummary(caseData) {
  const status = caseData.statusOfStay;
  const days = Number.isFinite(Number(caseData.durationDays)) ? Number(caseData.durationDays) : null;
  const workplace = caseData.workplaceType;
  const activity = caseData.activity;

  if (!isKoreanLocale()) {
    const parts = [];
    if (status) parts.push(`your current status of stay is ${status}`);
    if (caseData.violationCode === 'OVERSTAY_ART25') {
      parts.push(days != null ? `you stayed ${days} days beyond the permitted period` : 'you stayed beyond the permitted period');
    } else if (activity || workplace || caseData.authorizationObtained === false) {
      let work = workplace ? `you worked at a ${workplace}` : 'you carried out work-related activity';
      if (caseData.authorizationObtained === false) work += ' without the required permission';
      if (days != null) work += ` for ${days} days`;
      parts.push(work);
    } else if (caseData.violationCode) {
      parts.push(violationLabels[caseData.violationCode] || 'a possible immigration-related violation was described');
    }
    if (caseData.priorViolations === 0) parts.push('this is your first violation');
    else if (Number(caseData.priorViolations) > 0) parts.push(`you reported ${Number(caseData.priorViolations)} previous violation(s)`);
    if (caseData.voluntaryDisclosure === true) parts.push('you reported or visited the immigration office voluntarily');
    if (caseData.investigationStarted === true && caseData.voluntaryDisclosure !== true) parts.push('an investigation or enforcement contact has already started');
    return parts.length ? `${parts.join(', ')}.` : 'I could only identify part of the situation you described.';
  }

  // Short, complete Korean sentences. The previous comma-joined fragments read as
  // "음식점에서 필요한 허가 없이 취업활동 그 기간은 30일" and users could not parse them.
  const sentences = [];
  const subject = status ? `${status} 체류자격으로 ` : '';
  if (caseData.violationCode === 'OVERSTAY_ART25') {
    sentences.push(days != null
      ? `${subject}허가된 체류기간이 지난 뒤 ${days}일 동안 더 머문 상황이에요.`
      : `${subject}허가된 체류기간이 지난 뒤에도 계속 머문 상황이에요.`);
  } else if (activity || workplace || caseData.authorizationObtained === false) {
    const place = workplace ? `${workplace}에서 ` : '';
    const permission = caseData.authorizationObtained === false ? (/^E-[1-7](?:-|$)/i.test(status || '') ? '사전허가를 받지 않고 ' : '필요한 허가 없이 ') : '';
    const period = days != null ? `${days}일 동안 ` : '';
    sentences.push(`${subject}${place}${permission}${period}일한 상황이에요.`);
  } else if (caseData.violationCode) {
    sentences.push(`${subject}${violationLabels[caseData.violationCode] || '출입국 관련 위반 상황'}이에요.`);
  } else if (status) {
    sentences.push(`현재 체류자격은 ${status}예요.`);
  }

  if (caseData.priorViolations === 0) sentences.push('이번이 첫 위반이에요.');
  else if (Number(caseData.priorViolations) > 0) sentences.push(`과거 위반 전력이 ${Number(caseData.priorViolations)}회 있어요.`);
  if (caseData.voluntaryDisclosure === true) sentences.push('본인이 먼저 신고하거나 출입국관서에 자진 방문했어요.');
  if (caseData.investigationStarted === true && caseData.voluntaryDisclosure !== true) sentences.push('이미 적발되었거나 조사가 시작됐어요.');

  if (!sentences.length) return '입력한 내용 중 일부 사실만 확인할 수 있었어요. 아래 질문에 답해 주세요.';
  return sentences.join(' ');
}

function displayValue(value, fallback = '확인되지 않음') {
  if (value === null || value === undefined || value === '') return fallback;
  if (value === true) return '예';
  if (value === false) return '아니요';
  return String(value);
}

function renderFactList(caseData) {
  const facts = [
    ['체류자격', displayValue(caseData.statusOfStay)],
    ['상황', caseData.violationCode ? (violationLabels[caseData.violationCode] || caseData.violationCode) : '정확한 유형을 더 확인해야 함'],
    ['기간', caseData.durationDays == null ? '확인되지 않음' : `${Number(caseData.durationDays)}일`],
    ['허가 여부', /^E-[1-7](?:-|$)/i.test(caseData.statusOfStay || '') && ['UNAUTHORIZED_EMPLOYMENT_ART18_2', 'UNAUTHORIZED_WORKPLACE_CHANGE_ART21_1'].includes(caseData.violationCode) && caseData.workplaceRegime !== 'PERMIT' ? '사전허가 의무가 적용되는지 추가 확인 필요' : caseData.authorizationObtained == null ? '확인되지 않음' : (caseData.authorizationObtained ? '허가를 받았다고 입력함' : '허가를 받지 않았다고 입력함')],
    ...(caseData.workplaceRegime ? [['근무처 절차', caseData.workplaceRegime === 'PERMIT' ? '사전허가 대상(사용자 확인)' : '사후신고 대상(사용자 확인)']] : []),
    ['과거 위반', caseData.priorViolations == null ? '확인되지 않음' : (Number(caseData.priorViolations) === 0 ? '첫 위반으로 입력됨' : `${Number(caseData.priorViolations)}회${Number(caseData.priorViolations) >= 2 ? ' 이상' : ''}`)],
    ['자진신고·자진방문', caseData.voluntaryDisclosure == null ? '확인되지 않음' : (caseData.voluntaryDisclosure ? '예' : '아니요')],
    ['적발·사범조사 시작', caseData.investigationStarted == null ? '확인되지 않음' : (caseData.investigationStarted ? '예' : '아니요')],
  ];
  $('#confirmed-facts').innerHTML = facts.map(([label, value]) => `<div><dt>${escapeHtml(label)}</dt><dd>${escapeHtml(value)}</dd></div>`).join('');
}

function renderConfirmationNotes(caseData) {
  const warnings = caseData.extractionWarnings || [];
  const unknown = caseData.unknownFacts || [];
  const notes = [];
  if (warnings.length) notes.push(`<strong>확인이 필요한 해석</strong><ul>${warnings.map((item) => `<li>${escapeHtml(item)}</li>`).join('')}</ul>`);
  if (unknown.length) notes.push(`<strong>아직 확인되지 않은 정보</strong><ul>${unknown.map((item) => `<li>${escapeHtml(item)}</li>`).join('')}</ul>`);
  const target = $('#confirmation-notes');
  target.innerHTML = notes.join('');
  target.hidden = notes.length === 0;
}

function clarificationFor(caseData) {
  if (!caseData.statusOfStay && !skippedClarifications.has('statusOfStay')) {
    return {
      kind: 'statusOfStay',
      type: 'text',
      question: '위반 당시 체류자격이 무엇인가요?',
      hint: '예: D-2, E-7-4, F-2',
      // Common codes only as shortcuts; the user still picks, nothing is inferred.
      quickPicks: [
        ['D-2', '유학 D-2'], ['D-4', '어학연수 D-4'], ['D-10', '구직 D-10'], ['E-9', '비전문취업 E-9'],
        ['E-7', '특정활동 E-7'], ['H-2', '방문취업 H-2'], ['B-1', '무비자 B-1'], ['B-2', '관광통과 B-2'], ['C-3', '단기방문 C-3'],
      ],
    };
  }

  if (!caseData.violationCode && !skippedClarifications.has('violationCode')) {
    const candidates = new Set(caseData.violationCandidates || []);
    const options = [];
    const add = (value, label) => { if (!candidates.size || candidates.has(value)) options.push({ value, label }); };
    const professionalStatus = /^E-[1-7](?:-|$)/i.test(caseData.statusOfStay || '');
    add('STATUS_OUTSIDE_ACTIVITY_ART20', professionalStatus ? '현재 체류자격에서 허용하는 활동과 다른 종류의 일을 했어요' : '학생 등의 체류자격으로, 필요한 활동 허가 없이 일을 했어요');
    if (!professionalStatus) add('UNAUTHORIZED_STAY_OR_WORK_ART18_1', '애초에 취업할 수 없는 체류자격인데 일을 했어요');
    add('UNAUTHORIZED_EMPLOYMENT_ART18_2', '허가된 회사는 그대로이고, 지정된 근무처가 아닌 곳에서도 일했어요');
    add('UNAUTHORIZED_WORKPLACE_CHANGE_ART21_1', '다른 회사·사업장으로 옮기거나 추가했어요 (허가·신고 구분은 별도로 확인)');
    add('OVERSTAY_ART25', '체류기간이 지난 뒤에도 계속 체류했어요');
    return {
      kind: 'violationCode',
      type: 'choice',
      question: candidates.has('UNAUTHORIZED_EMPLOYMENT_ART18_2') && candidates.has('UNAUTHORIZED_WORKPLACE_CHANGE_ART21_1')
        ? '다른 곳에서 일했다는 게 정확히 어떤 상황이었나요?'
        : '아래 중 실제 상황에 가장 가까운 것은 무엇인가요?',
      options,
    };
  }

  // E-1~E-7 can fall under a 15-day report obligation rather than a
  // prior-permission obligation. Only the user can confirm the applicable
  // regime; we must not infer it from the E visa code or from "no permit".
  const workplaceCodes = ['UNAUTHORIZED_EMPLOYMENT_ART18_2', 'UNAUTHORIZED_WORKPLACE_CHANGE_ART21_1'];
  if (/^E-[1-7](?:-|$)/i.test(caseData.statusOfStay || '')
      && workplaceCodes.includes(caseData.violationCode)
      && !caseData.workplaceRegime && !skippedClarifications.has('workplaceRegime')) {
    return {
      kind: 'workplaceRegime',
      type: 'choice',
      question: '근무처 변경·추가가 사전허가 대상인지 사후신고 대상인지 확인하셨나요?',
      options: [
        { value: 'PERMIT', label: '관할 출입국관서에서 사전허가 대상이라고 확인했어요' },
        { value: 'REPORT', label: '관할 출입국관서에서 사후신고 대상이라고 확인했어요' },
      ],
    };
  }

  if (caseData.durationDays == null && !skippedClarifications.has('durationDays')) {
    return {
      kind: 'durationDays',
      type: 'number',
      question: '그 상황은 대략 며칠 동안 이어졌나요?',
      hint: '예: 21',
    };
  }

  return null;
}

function renderClarification(caseData) {
  const card = $('#clarification-card');
  const answers = $('#clarification-answers');
  const question = clarificationFor(caseData);
  const primary = $('#confirm-primary');
  card.hidden = !question;
  primary.disabled = Boolean(question);
  answers.innerHTML = '';

  if (!question) return;
  $('#clarification-question').textContent = question.question;

  if (question.type === 'choice') {
    answers.innerHTML = `${question.options.map((option) => `<button type="button" class="clarification-option" data-clarify-value="${escapeHtml(option.value)}">${escapeHtml(option.label)}</button>`).join('')}
      <button type="button" class="clarification-option clarification-option--muted" data-clarify-skip="${escapeHtml(question.kind)}">잘 모르겠어요</button>`;
  } else {
    const type = question.type === 'number' ? 'number' : 'text';
    const attrs = type === 'number' ? 'min="0" max="36500" inputmode="numeric"' : 'maxlength="20" autocomplete="off"';
    const picks = (question.quickPicks || []).map(([value, label]) => `<button type="button" class="clarification-chip" data-clarify-value="${escapeHtml(value)}">${escapeHtml(label)}</button>`).join('');
    answers.innerHTML = `${picks ? `<div class="clarification-chips" role="group" aria-label="자주 쓰는 체류자격">${picks}</div><p class="field-hint">목록에 없으면 직접 입력하세요. 관광으로 들어왔다면 여권·사증에 적힌 코드(B-1, B-2, C-3 등)를 확인해 주세요.</p>` : ''}<div class="clarification-input-row"><input id="clarification-input" type="${type}" ${attrs} placeholder="${escapeHtml(question.hint || '')}" aria-label="${escapeHtml(question.question)}"><button type="button" class="primary-button secondary-button--small" id="clarification-apply">확인</button></div>
      <button type="button" class="clarification-option clarification-option--muted" data-clarify-skip="${escapeHtml(question.kind)}">잘 모르겠어요</button>`;
  }

  $$('[data-clarify-value]', answers).forEach((button) => button.addEventListener('click', () => {
    applyClarification(question.kind, button.dataset.clarifyValue || '');
  }));
  $$('[data-clarify-skip]', answers).forEach((button) => button.addEventListener('click', () => {
    skippedClarifications.add(button.dataset.clarifySkip || question.kind);
    setError($('#confirm-error'));
    renderConfirmation(structuredCase);
  }));

  const apply = $('#clarification-apply', answers);
  if (apply) {
    const input = $('#clarification-input', answers);
    const commit = () => applyClarification(question.kind, input.value);
    apply.addEventListener('click', commit);
    input.addEventListener('keydown', (event) => {
      if (event.key === 'Enter') {
        event.preventDefault();
        commit();
      }
    });
    input.focus({ preventScroll: true });
  }
}

function applyClarification(kind, rawValue) {
  const value = String(rawValue || '').trim();
  setError($('#confirm-error'));

  if (kind === 'statusOfStay') {
    if (!value) return setError($('#confirm-error'), '체류자격을 입력하거나 잘 모르겠어요를 선택해 주세요.');
    structuredCase.statusOfStay = normalizeStatus(value);
    removeUnknownFacts(structuredCase, ['체류자격']);
    deriveViolationAfterStatus(structuredCase);
  } else if (kind === 'workplaceRegime') {
    if (!['PERMIT', 'REPORT'].includes(value)) return setError($('#confirm-error'), '해당하는 확인 결과를 선택해 주세요.');
    structuredCase.workplaceRegime = value;
  } else if (kind === 'durationDays') {
    const days = Number(value);
    if (!Number.isInteger(days) || days < 0 || days > 36500) return setError($('#confirm-error'), '기간을 일수로 입력해 주세요.');
    structuredCase.durationDays = days;
    removeUnknownFacts(structuredCase, ['위반기간', '위반 시작일']);
  } else if (kind === 'violationCode') {
    if (!violationLabels[value]) return setError($('#confirm-error'), '실제 상황과 가장 가까운 항목을 선택해 주세요.');
    structuredCase.violationCode = value;
    structuredCase.violationCandidates = [value];
    if (value === 'STATUS_OUTSIDE_ACTIVITY_ART20' || value === 'UNAUTHORIZED_STAY_OR_WORK_ART18_1') {
      if (structuredCase.authorizationObtained == null) structuredCase.authorizationObtained = false;
    }
    if (value === 'UNAUTHORIZED_WORKPLACE_CHANGE_ART21_1') {
      structuredCase.workplaceChangeAuthorized = false;
      if (structuredCase.authorizationObtained == null) structuredCase.authorizationObtained = false;
    }
    removeUnknownFacts(structuredCase, ['구체적인 위반 유형', '취업 가능 체류자격인지 및 지정 근무처·근무처 변경 관계']);
  }

  skippedClarifications.delete(kind);
  renderConfirmation(structuredCase);
}

// Facts that move the outcome inside the legal range. Optional: the user can always
// leave them unknown, and an unknown fact is never treated as a "no".
const accuracyQuestions = [
  { key: 'priorViolations', unknown: '과거 위반 전력', question: '예전에 출입국 관련 위반으로 처분받은 적이 있나요?', options: [[0, '처음이에요'], [1, '1번 있어요'], [2, '2번 이상']] },
  { key: 'voluntaryDisclosure', unknown: '자진신고 여부', question: '적발되기 전에 스스로 출입국관서에 알리거나 찾아갔나요?', options: [[true, '네, 스스로 했어요'], [false, '아니요']] },
  { key: 'investigationStarted', unknown: '사범조사 시작 여부', question: '이미 단속되거나 조사 연락을 받았나요?', options: [[true, '네, 받았어요'], [false, '아직 아니에요']] },
];

function openAccuracyQuestions(caseData) {
  return accuracyQuestions.filter((item) => caseData?.[item.key] === null || caseData?.[item.key] === undefined);
}

function accuracyQuestionsHtml(caseData) {
  return openAccuracyQuestions(caseData).map((item) => `
    <div class="accuracy-question" role="group" aria-label="${escapeHtml(item.question)}">
      <p>${escapeHtml(item.question)}</p>
      <div class="clarification-chips">${item.options.map(([value, label]) => `<button type="button" class="clarification-chip" data-accuracy-key="${item.key}" data-accuracy-value="${escapeHtml(JSON.stringify(value))}">${escapeHtml(label)}</button>`).join('')}</div>
    </div>`).join('');
}

function applyAccuracyAnswer(caseData, key, rawValue) {
  const question = accuracyQuestions.find((item) => item.key === key);
  if (!question) return caseData;
  let value;
  try { value = JSON.parse(rawValue); } catch { return caseData; }
  if (!question.options.some(([allowed]) => allowed === value)) return caseData;
  const next = { ...caseData, [key]: value };
  next.unknownFacts = (next.unknownFacts || []).filter((item) => item !== question.unknown);
  return next;
}

function wireAccuracyButtons(root, onAnswer) {
  $$('[data-accuracy-key]', root).forEach((button) => button.addEventListener('click', () => {
    onAnswer(button.dataset.accuracyKey, button.dataset.accuracyValue);
  }));
}

function renderAccuracyCard(caseData) {
  const card = $('#accuracy-card');
  if (!card) return;
  const html = accuracyQuestionsHtml(caseData);
  card.hidden = !html;
  $('#accuracy-questions').innerHTML = html;
  wireAccuracyButtons(card, (key, value) => {
    structuredCase = applyAccuracyAnswer(structuredCase, key, value);
    renderConfirmation(structuredCase);
  });
}

function renderConfirmation(caseData) {
  $('#confirmation-summary').textContent = deterministicSummary(caseData);
  renderFactList(caseData);
  renderConfirmationNotes(caseData);
  renderClarification(caseData);
  renderAccuracyCard(caseData);
}

function analysisFingerprint(caseData) {
  const keys = [
    'statusOfStay', 'violationCode', 'durationDays', 'priorViolations',
    'authorizationObtained', 'workplaceChangeAuthorized', 'workplaceRegime', 'voluntaryDisclosure',
    'investigationStarted', 'falseRepresentation', 'violationStartDate',
    'violationEndDate', 'assessmentDate'
  ];
  return JSON.stringify(keys.map((key) => caseData?.[key] ?? null));
}

const won = (value) => value == null ? '산출 불가' : `${Number(value).toLocaleString('ko-KR')}원`;
const range = (value) => !value ? '예상 범위 산출 불가' : `${won(value.minimumKrw)} – ${won(value.maximumKrw)}`;
const confidenceLabels = { VERY_HIGH: '매우 높음', HIGH: '높음', MEDIUM: '중간', LOW: '낮음', VERY_LOW: '매우 낮음', INSUFFICIENT: '근거 부족' };
const likelihoodLabels = { VERY_HIGH: '매우 높음', HIGH: '높음', MODERATE: '중간', LOW: '낮음', VERY_LOW: '매우 낮음', UNKNOWN: '특정 어려움' };
const groundingLabels = { VERIFIED: '실시간 법령 API 검증 완료', AUDIT_ONLY: '법령 API 감사 모드', LIMITED: '법령 API 부분 검증', UNAVAILABLE: '정적 법령 스냅샷 사용' };
const dispositionLabels = {
  STAY_PERMISSION_DISADVANTAGE: '체류허가상 불이익',
  DEPARTURE_ORDER: '출국명령',
  DEPORTATION: '강제퇴거',
  CRIMINAL_REFERRAL: '형사절차 회부'
};

const basisLabels = { SUPPORTED: '근거 확인', INFERRED: '추론', UNKNOWN: '미확인' };

function factors(items = []) {
  if (!items.length) return '<p class="subtle">확인된 요인이 없습니다.</p>';
  return `<ul>${items.map((item) => `<li>${escapeHtml(item.label)} <span class="tag" data-basis="${escapeHtml(item.basis)}">${escapeHtml(basisLabels[item.basis] || item.basis)}</span></li>`).join('')}</ul>`;
}

// Server limitations are written for operators ("OpenRouter prediction unavailable:
// http_404", "Vercel에 ... 환경변수"). Keep every notice, but say it in plain Korean.
const providerReasonLabels = {
  provider_rate_limit: '무료 AI 호출 한도 도달', timeout: '응답 시간 초과', network_error: '네트워크 오류',
  no_compatible_endpoint: '사용할 수 있는 AI 모델 없음', http_404: '사용할 수 있는 AI 모델 없음',
  empty_response: 'AI가 빈 응답을 보냄', openrouter_not_configured: 'AI 서버 설정 필요', provider_auth_error: 'AI 서버 인증 오류',
};
function plainLimitation(text) {
  const value = String(text || '').trim();
  if (/법령.*API 조회 실패|no_exact_law_match|실시간 법령 API에서 인용 가능한 조문|law_api|LAW_API_OC/i.test(value)) {
    return '실시간 법령 원문 대조가 완료되지 않았습니다. 저장된 기준과 최신 공식 법령을 비교해 주세요.';
  }
  if (/정확한 위반 시작일·종료일|사건 당시 법령과 현재/.test(value)) {
    return '정확한 위반 날짜가 없어 사건 당시 적용 법령을 확정하지 못했습니다.';
  }
  if (/직접 인용 가능한 공개 판례|유사사례가 충분하지|유사 공개사례가 충분하지/.test(value)) {
    return '직접 비교할 수 있는 공개 사례가 충분하지 않아 개별 처분을 단정할 수 없습니다.';
  }
  if (/본 분석은 현재 제공된 법령 및 사례에 한정/.test(value)) {
    return '공개된 법령과 사례로 분석했으며, 실제 처분에는 개별 사정과 추가 기준이 반영될 수 있습니다.';
  }
  if (/공개 유사사례가 충분하지 않으면/.test(value)) {
    return '비교할 공개 사례가 부족하면 처분 전망의 신뢰도가 낮아집니다.';
  }
  const provider = value.match(/^OpenRouter prediction unavailable:\s*(\S+)/i);
  if (provider) return `AI 예상을 받지 못했습니다 (${providerReasonLabels[provider[1]] || '일시적 오류'}). 법령 기준은 그대로 유효합니다.`;
  if (/^OpenRouter prediction rejected/i.test(value)) return 'AI 응답이 근거·형식 검증을 통과하지 못해 표시하지 않았습니다.';
  if (/Vercel에 지원되는 법령 API 인증/.test(value)) return '실시간 법령 조회를 쓸 수 없어, 저장된 법령 기준(검증 스냅샷)으로 계산했습니다.';
  if (/법령 API 인증값이 없어/.test(value)) return '실시간 판례 조회를 쓸 수 없어 공식 판례 본문은 검색하지 않았습니다.';
  return value;
}

function needsExactDates(baseline) {
  return (baseline.missingFacts || []).some((item) => /시작일|종료일|위반기간/.test(item));
}

function nextStepCard(baseline) {
  if (baseline.status === 'AVAILABLE') return '';
  if ((baseline.missingFacts || []).some((item) => /사전허가 대상인지 사후신고 대상인지/.test(item))) {
    return `<section class="next-step-card" aria-labelledby="next-step-title">
      <p class="card-kicker">추가 확인 필요 · 처분 전망 보류</p>
      <h3 id="next-step-title">근무처 변경·추가가 허가 대상인지 신고 대상인지 먼저 확인해야 해요.</h3>
      <p>E-1~E-7 체류자격에서는 요건에 따라 사후신고가 적용될 수 있어요. 이 구분에 따라 범칙금과 과태료가 달라지므로 금액을 추측하지 않습니다.</p>
      <button type="button" class="primary-button" data-next-step-back>허가·신고 구분 확인하기</button>
    </section>`;
  }
  if (structuredCase?.workplaceRegime === 'REPORT' && baseline.status === 'UNSUPPORTED') {
    return `<section class="next-step-card next-step-card--stop" aria-labelledby="next-step-title">
      <p class="card-kicker">범칙금 계산 대상 아님</p>
      <h3 id="next-step-title">사후신고 대상이라면 별도의 과태료 기준을 확인해야 해요.</h3>
      <p>신고 의무 위반은 출입국관리법 제100조제1항제3호에 따라 과태료 검토 대상입니다. 범칙금 계산식을 대신 적용하지 않으며, 실제 신고의무 위반 여부는 별도 확인이 필요합니다.</p>
      <button type="button" class="primary-button" data-next-step-back data-reset-workplace-regime>허가·신고 구분 수정하기</button>
    </section>`;
  }
  if (needsExactDates(baseline)) {
    const today = localTodayIso();
    const start = structuredCase?.violationStartDate || '';
    const end = structuredCase?.violationEndDate || '';
    return `<section class="next-step-card" aria-labelledby="next-step-title">
      <p class="card-kicker">다음 단계 · 날짜만 알려 주세요</p>
      <h3 id="next-step-title">정확한 기간이 있어야 범칙금 기준을 계산할 수 있어요.</h3>
      <p>범칙금은 “개월” 단위로 구간이 나뉩니다. 30일처럼 경계에 걸리면 날짜에 따라 금액 구간이 달라져서, 추측하지 않고 계산을 멈췄습니다.</p>
      <form class="date-range-form" id="date-range-form" novalidate>
        <label>시작한 날<input type="date" id="violation-start" max="${today}" value="${escapeHtml(start)}" required></label>
        <label>끝난 날 (계속 중이면 오늘)<input type="date" id="violation-end" max="${today}" value="${escapeHtml(end)}" required></label>
        <button type="submit" class="primary-button">이 날짜로 다시 계산</button>
      </form>
      <p class="form-error" id="date-range-error" role="alert" hidden></p>
    </section>`;
  }
  if (baseline.status === 'HISTORICAL_RULE_UNAVAILABLE' || baseline.status === 'UNSUPPORTED') {
    return `<section class="next-step-card next-step-card--stop" aria-labelledby="next-step-title">
      <p class="card-kicker">계산하지 않음</p>
      <h3 id="next-step-title">이 경우는 검증된 법령 기준이 없어 금액을 계산하지 않았어요.</h3>
      <p>${baseline.status === 'UNSUPPORTED' ? '이 위반 유형은 아직 Visable 계산 규칙에 없습니다.' : '입력한 기간에 적용되는 법령 기준을 Visable이 검증해 두지 않았습니다.'} 추측한 금액 대신, 외국인종합안내센터(☎1345)나 관할 출입국·외국인관서에 확인해 주세요.</p>
    </section>`;
  }
  return `<section class="next-step-card" aria-labelledby="next-step-title">
      <p class="card-kicker">다음 단계</p>
      <h3 id="next-step-title">어떤 상황인지 하나만 더 골라 주세요.</h3>
      <p>위반 유형이 정해져야 법령 기준을 계산할 수 있습니다.${(baseline.missingFacts || []).length ? ` 부족한 정보: ${escapeHtml(baseline.missingFacts.join(', '))}` : ''}</p>
      <button type="button" class="primary-button" data-next-step-back>상황 다시 고르기</button>
    </section>`;
}

function wireNextStep() {
  const form = $('#date-range-form');
  if (form) {
    form.addEventListener('submit', (event) => {
      event.preventDefault();
      const start = $('#violation-start').value;
      const end = $('#violation-end').value;
      const error = $('#date-range-error');
      if (!/^\d{4}-\d{2}-\d{2}$/.test(start) || !/^\d{4}-\d{2}-\d{2}$/.test(end)) return setError(error, '시작한 날과 끝난 날을 모두 골라 주세요.');
      if (end < start) return setError(error, '끝난 날이 시작한 날보다 빠릅니다.');
      if (end > localTodayIso()) return setError(error, '미래 날짜는 쓸 수 없어요.');
      setError(error);
      const next = { ...structuredCase, violationStartDate: start, violationEndDate: end };
      next.durationDays = Math.round((Date.parse(`${end}T00:00:00Z`) - Date.parse(`${start}T00:00:00Z`)) / 86400000) + 1;
      next.unknownFacts = (next.unknownFacts || []).filter((item) => item !== '위반기간' && item !== '위반 시작일');
      analyzeCase(next);
    });
  }
  $('[data-next-step-back]')?.addEventListener('click', (event) => {
    if (event.currentTarget.hasAttribute('data-reset-workplace-regime') && structuredCase) structuredCase.workplaceRegime = null;
    analysisSequence++;
    skippedClarifications.delete('violationCode');
    skippedClarifications.delete('workplaceRegime');
    renderConfirmation(structuredCase);
    showStep(2);
  });
}

const likelihoodSteps = { VERY_LOW: 1, LOW: 2, MODERATE: 3, HIGH: 4, VERY_HIGH: 5 };
const directionLabels = { MITIGATED: '기준보다 낮은 쪽', BASELINE: '기준 금액 근처', AGGRAVATED: '기준보다 높은 쪽', UNCERTAIN: '방향 불확실' };
const dispositionHelp = {
  STAY_PERMISSION_DISADVANTAGE: '범칙금 납부 후 체류는 이어가지만, 다음 연장·변경 심사에서 불리하게 볼 수 있다는 뜻이에요.',
  DEPARTURE_ORDER: '정해진 기한 안에 스스로 출국하라는 명령이에요.',
  DEPORTATION: '강제로 출국시키는 처분이에요.',
  CRIMINAL_REFERRAL: '범칙금이 아니라 형사절차(고발 등)로 넘어갈 수 있다는 뜻이에요.',
};

function likelihoodMeter(level) {
  const step = likelihoodSteps[level] || 0;
  return `<span class="likelihood-meter" role="img" aria-label="가능성 ${escapeHtml(likelihoodLabels[level] || '특정 어려움')}">${[1, 2, 3, 4, 5].map((index) => `<i class="${index <= step ? 'is-on' : ''}"></i>`).join('')}</span>`;
}

function disposition(item, primary = false) {
  if (!item) return '<p class="subtle">현재 공개된 근거만으로 가장 유력한 처분을 특정하기 어렵습니다.</p>';
  return dispositionHtml(item, primary);
}

// When there is no AI disposition, say why, and show what the law allows for this
// violation (repo rule data, not a ranking) instead of an empty box.
function emptyDispositionHtml(baseline, prediction) {
  const allowed = baseline.legallyAvailableDispositions || [];
  const reason = baseline.status !== 'AVAILABLE'
    ? (needsExactDates(baseline) ? '위 “다음 단계”에서 날짜를 넣으면 처분 예상도 함께 계산해요.' : '위반 유형과 기간이 정해지면 처분 예상도 함께 계산해요.')
    : prediction.status === 'UNAVAILABLE'
      ? 'AI 예상을 이번에 받지 못해 처분 가능성 순위는 비워 두었어요. 아래 “AI 예상 다시 확인”으로 다시 시도할 수 있어요.'
      : '이 사실관계만으로는 가장 유력한 처분을 하나로 좁히기 어려웠어요.';
  return `<p class="subtle">${escapeHtml(reason)}</p>
    ${allowed.length ? `<div class="legal-dispositions">
      <strong>이 위반에 법령상 가능한 처분</strong>
      <ul>${allowed.map((type) => `<li><b>${escapeHtml(dispositionLabels[type] || type)}</b> · ${escapeHtml(dispositionHelp[type] || '')}</li>`).join('')}</ul>
      <p class="subtle">가능성 순위가 아니라, 법령상 선택될 수 있는 처분의 범위예요.</p>
    </div>` : ''}`;
}

function dispositionHtml(item, primary = false) {
  return `<div class="disposition${primary ? ' disposition--primary' : ''}">
    <strong><span>${primary ? '가장 유력 · ' : '다른 가능성 · '}${escapeHtml(dispositionLabels[item.type] || item.type)}</span><span class="disposition-likelihood">${likelihoodMeter(item.likelihood)} ${escapeHtml(likelihoodLabels[item.likelihood] || item.likelihood)}</span></strong>
    ${dispositionHelp[item.type] ? `<p class="subtle">${escapeHtml(dispositionHelp[item.type])}</p>` : ''}
    ${item.likelihoodCappedFrom ? '<p class="likelihood-cap-note">공개된 처분 사례 근거가 부족해, 가능성은 “중간”까지만 표시해요.</p>' : ''}
    ${(item.rationale || []).length ? factors(item.rationale) : ''}
  </div>`;
}

// One plain-language paragraph built only from validated values. Nothing new is inferred here.
function verdictSentence(baseline, prediction) {
  const parts = [];
  if (baseline.status === 'AVAILABLE') parts.push(`법령상 기준 범칙금은 <strong>${won(baseline.baselineAmountKrw)}</strong>이에요.`);
  const money = prediction.monetaryPrediction;
  if (money) {
    const direction = directionLabels[money.predictedDirection];
    parts.push(`AI 보조 분석에서는 <strong>${range(money.predictedLikelyRange)}</strong>${direction && money.predictedDirection !== 'UNCERTAIN' ? `(${direction})` : ''} 정도로 예상해요.`);
  }
  const primary = prediction.primaryDisposition;
  if (primary) parts.push(`가장 유력한 처분은 <strong>${escapeHtml(dispositionLabels[primary.type] || primary.type)}</strong>(가능성 ${escapeHtml(likelihoodLabels[primary.likelihood] || '특정 어려움')})이에요.`);
  if (!money && !primary) parts.push('AI 예상은 이번에 검증을 통과하지 못해, 법령 기준만 확정적으로 보여드려요.');
  return parts.join(' ');
}

function accuracyBoostCard(caseData) {
  const html = accuracyQuestionsHtml(caseData);
  if (!html) return '';
  return `<section class="accuracy-card accuracy-card--result" id="result-accuracy" aria-labelledby="result-accuracy-title">
    <p class="card-kicker">예상 정확도 올리기</p>
    <h3 id="result-accuracy-title">아래에 답하면 바로 다시 계산해요.</h3>
    <p class="subtle">모르는 사실은 “모름”으로 남겨 두고, 그만큼 신뢰도를 낮춰 계산하고 있어요.</p>
    ${html}
  </section>`;
}

function resultNotice(className, title, body) {
  return `<div class="${className}"><strong>${escapeHtml(title)}</strong><span>${escapeHtml(body)}</span></div>`;
}

function renderAnalysisLoading() {
  $('#result-root').setAttribute('aria-busy', 'true');
  $('#result-root').innerHTML = `
    <div class="analysis-loading" role="status">
      <span class="loading-spinner" aria-hidden="true"></span>
      <div>
        <strong>법령 기준과 예상 처분을 분석하고 있어요.</strong>
        <p>공식 근거와 AI 응답을 함께 검증하므로 보통 수 초가 걸립니다. 이 화면에서 결과가 바로 이어집니다.</p>
      </div>
    </div>`;
}

function renderResult(data) {
  $('#result-root').setAttribute('aria-busy', String(Boolean(data.analysisPending)));
  const baseline = data.legalBaseline || {};
  const prediction = data.prediction || {};
  const grounding = data.lawGrounding || {};
  const monetary = prediction.monetaryPrediction;
  const confidence = prediction.confidence || { level: 'INSUFFICIENT', reasons: [] };
  const sources = prediction.evidence || [];
  const similar = prediction.similarCases || [];
  const limitations = prediction.limitations || [];
  const groundingLabel = groundingLabels[grounding.status] || '실시간 검증 없음 · 저장된 법령 기준';
  const baselineReady = baseline.status === 'AVAILABLE';
  const failureMessages = {
    provider_rate_limit: ['AI 서비스 요청 제한', '무료 AI 모델의 호출 한도에 도달했습니다. 잠시 후 다시 시도할 수 있습니다.'],
    timeout: ['AI 응답 시간 초과', 'AI 제공자가 제한 시간 내 응답하지 않았습니다.'],
    network_error: ['AI 네트워크 연결 실패', 'AI 제공자 연결에 문제가 발생했습니다.'],
    invalid_structured_prediction: ['AI 응답 형식 검증 실패', 'AI의 응답이 법적 근거 또는 데이터 형식 검증을 통과하지 못했습니다.'],
    openrouter_not_configured: ['AI 제공자 설정 필요', '서버의 AI 제공자 인증 설정을 확인해야 합니다.'],
    no_compatible_endpoint: ['AI 모델 일시 사용 불가', '지금 쓸 수 있는 무료 AI 모델이 없습니다. 법령 기준은 그대로 유효하며, 잠시 후 다시 시도할 수 있습니다.'],
    http_404: ['AI 모델 일시 사용 불가', '지금 쓸 수 있는 무료 AI 모델이 없습니다. 법령 기준은 그대로 유효하며, 잠시 후 다시 시도할 수 있습니다.'],
    provider_auth_error: ['AI 서버 인증 오류', 'AI 제공자 인증에 실패했습니다. 운영자가 API 키 설정을 확인해야 합니다. 법령 기준은 그대로 유효합니다.'],
    empty_response: ['AI 빈 응답', 'AI가 내용 없는 응답을 보내 표시하지 않았습니다. 잠시 후 다시 시도해 주세요.'],
  };
  const failureNotice = failureMessages[prediction.failureCategory]
    || ['AI 추정 근거 부족', '안전하게 표시할 수 있는 검증된 AI 예측이 없습니다.'];
  const modelLabel = data.analysisPending ? '처분 전망 분석 중' : prediction.status === 'UNAVAILABLE' ? '처분 전망 보류' : 'AI 보조 분석 · 최종 처분 아님';
  const durationDays = Number(data.case?.durationDays ?? structuredCase?.durationDays);
  // When the next-step card asks for dates, it already carries this explanation.
  const datesRequested = !data.analysisPending && !baselineReady && needsExactDates(baseline);
  const exactDates = Boolean((data.case || structuredCase)?.violationStartDate && (data.case || structuredCase)?.violationEndDate);
  const boundaryNotice = durationDays === 30 && !exactDates && !datesRequested
    ? resultNotice('baseline-boundary-note', '30일은 월 단위 경계에 걸릴 수 있습니다', '별표 7은 “개월” 단위 기준을 사용합니다. 정확한 시작일·종료일을 적으면 경계 판단이 더 정확해집니다.')
    : '';
  const degradedNotice = data.analysisPending
    ? resultNotice('prediction-degraded-note', '법령 기준을 먼저 확인하세요', 'AI 예상은 확인 중입니다. 검증이 끝나면 이 화면에서 이어서 표시해요.')
    : monetary
    ? ''
    : resultNotice('prediction-degraded-note',
      baselineReady ? failureNotice[0] : '법령 기준 산출에 필요한 사실 부족',
      baselineReady ? failureNotice[1] : '먼저 위반 유형과 정확한 시작·종료일을 확인해 주세요. 검증되지 않은 범칙금은 표시하지 않습니다.');

  const aiBody = !baselineReady && !data.analysisPending
    ? '법령 기준이 정해지면 AI 예상도 이어서 계산합니다. 위 “다음 단계”를 먼저 진행해 주세요.'
    : null;

  const showVerdict = !data.analysisPending && baselineReady;
  const caseForQuestions = data.case || structuredCase;
  const stayImpact = (prediction.stayImpact || []).filter(Boolean);
  const moneyReasons = monetary?.rationale || [];

  $('#result-root').innerHTML = `
    ${data.analysisPending ? '' : nextStepCard(baseline)}
    ${showVerdict ? `<section class="verdict-card" aria-labelledby="verdict-title">
      <p class="card-kicker" id="verdict-title">한눈에 보기</p>
      <p class="verdict-text">${verdictSentence(baseline, prediction)}</p>
      <p class="verdict-confidence">예측 신뢰도 <strong>${escapeHtml(confidenceLabels[confidence.level] || confidence.level)}</strong>${(prediction.unresolvedFactors || []).length ? ` · 확인 안 된 사실 ${(prediction.unresolvedFactors || []).length}개` : ''}</p>
    </section>` : ''}
    <div class="result-summary${baselineReady ? '' : ' result-summary--blocked'}">
      <article class="result-card baseline">
        <p class="card-kicker">법령 기준 · 계산식으로 산출</p>
        <h3>법령 기준</h3>
        <p class="subtle">법령상 기준 범칙금</p>
        <p class="amount">${won(baseline.baselineAmountKrw)}</p>
        <p>법정 조정 가능 범위: <strong>${range(baseline.legallyAdjustableRange)}</strong></p>
        ${baseline.violationLabel ? `<p class="subtle">적용 기준: ${escapeHtml(baseline.violationLabel)}</p>` : ''}
        <p><span class="tag">${escapeHtml(groundingLabel)}</span></p>
        ${(baseline.missingFacts || []).length && !datesRequested ? `<div class="baseline-boundary-note" role="status"><strong>추가 확인 필요</strong><ul>${baseline.missingFacts.map((item) => `<li>${escapeHtml(item)}</li>`).join('')}</ul></div>` : ''}
        ${(baseline.assumptions || []).length ? `<ul class="baseline-assumptions">${baseline.assumptions.map((item) => `<li>${escapeHtml(item)}</li>`).join('')}</ul>` : ''}
        ${boundaryNotice}
      </article>
      <article class="result-card prediction">
        <p class="card-kicker">AI 보조 분석 · 법정 범위 안에서만</p>
        <h3>처분 전망</h3>
        <p class="subtle">예상 범칙금 범위</p>
        <p class="amount">${data.analysisPending ? '확인 중' : monetary ? range(monetary.predictedLikelyRange) : aiBody ? '대기 중' : 'AI 추정 보류'}</p>
        <p>${aiBody ? aiBody : data.analysisPending ? '법령 기준은 먼저 확인할 수 있어요. AI 예상은 검증 후 표시해요.' : monetary?.pointEstimateKrw != null ? `대표 추정액: <strong>${won(monetary.pointEstimateKrw)}</strong>` : monetary ? '근거가 충분하지 않아 대표 추정액을 표시하지 않습니다.' : '유효성 검증을 통과한 구조화 예측이 없어 금액을 임의로 만들지 않았습니다.'}</p>
        ${monetary && directionLabels[monetary.predictedDirection] ? `<p><span class="tag tag--direction" data-direction="${escapeHtml(monetary.predictedDirection)}">${escapeHtml(directionLabels[monetary.predictedDirection])}</span></p>` : ''}
        ${moneyReasons.length ? `<div class="money-reasons"><strong>이 범위인 이유</strong>${factors(moneyReasons)}</div>` : ''}
        <p class="subtle">${escapeHtml(modelLabel)}</p>
        ${aiBody ? '' : degradedNotice}
      </article>
    </div>

    ${showVerdict ? accuracyBoostCard(caseForQuestions) : ''}

    <article class="result-lead">
      <p class="card-kicker">가능한 결과</p>
      <h3>행정처분 전망</h3>
      ${data.analysisPending ? '<p class="subtle">AI 예상 결과를 확인하고 있어요.</p>' : prediction.primaryDisposition ? disposition(prediction.primaryDisposition, true) : emptyDispositionHtml(baseline, prediction)}
      ${(prediction.alternativeDispositions || []).map((item) => disposition(item)).join('')}
    </article>

    ${!data.analysisPending && stayImpact.length ? `<article class="result-lead stay-impact">
      <p class="card-kicker">체류에 미치는 영향 · AI 예상</p>
      <h3>앞으로의 체류에는 이런 영향이 있을 수 있어요</h3>
      <ul>${stayImpact.map((item) => `<li>${escapeHtml(item)}</li>`).join('')}</ul>
      <p class="subtle">가능성을 설명한 것이며 확정된 결과가 아니에요. 실제 심사는 관할 출입국·외국인관서가 판단해요.</p>
    </article>` : ''}

    <div class="result-details">
      <details>
        <summary>예측 신뢰도 · ${data.analysisPending ? '분석 중' : escapeHtml(confidenceLabels[confidence.level] || confidence.level)}</summary>
        <div class="detail-body">
          <h3>예측 신뢰도</h3>
          ${factors((confidence.reasons || []).map((label, index) => ({ label, basis: index ? 'INFERRED' : 'SUPPORTED' })))}
        </div>
      </details>

      <details${showVerdict ? ' open' : ''}>
        <summary>예상 근거</summary>
        <div class="detail-body">
          <p class="card-kicker">처분 전망</p>
          <h3>예상 근거</h3>
          <div class="result-grid">
            ${(prediction.aggravatingFactors || []).length ? `<div><strong>가중 방향 요인</strong>${factors(prediction.aggravatingFactors)}</div>` : ''}
            ${(prediction.mitigatingFactors || []).length ? `<div><strong>감경 방향 요인</strong>${factors(prediction.mitigatingFactors)}</div>` : ''}
            ${(prediction.unresolvedFactors || []).length ? `<div><strong>추가 확인이 필요한 정보</strong>${factors(prediction.unresolvedFactors)}</div>` : ''}
            ${limitations.length ? `<div><strong>분석 시 참고할 사항</strong><ul>${[...new Set(limitations.map(plainLimitation).filter(Boolean))].map((item) => `<li>${escapeHtml(item)}</li>`).join('')}</ul></div>` : ''}
          </div>
        </div>
      </details>

      ${similar.length ? `<details>
        <summary>공개된 관련 사례 (${similar.length})</summary>
        <div class="detail-body">
          <h3>유사사례</h3>
          ${similar.length
            ? `<div class="evidence-list">${similar.map((item) => `<a class="evidence-item" href="${escapeHtml(item.sourceUrl)}" target="_blank" rel="noopener noreferrer"><strong>${escapeHtml(item.sourceTitle || item.id)}</strong><br><span class="subtle">${escapeHtml(item.outcomeSummary)}</span></a>`).join('')}</div>`
            : '<p class="subtle">현재 확인 가능한 유사 공개사례가 충분하지 않습니다.</p>'}
        </div>
      </details>` : ''}

      <details>
        <summary>법적 근거와 공식 출처</summary>
        <div class="detail-body">
          <p class="card-kicker">공식 출처</p>
          <h3>법적 근거</h3>
          <p class="subtle">${escapeHtml(groundingLabel)}</p>
          ${(baseline.appliedRules || []).length ? `<p class="subtle">적용 규칙: ${escapeHtml(baseline.appliedRules.join(' · '))}</p>` : ''}
          <p class="subtle">분석 기준일: <strong>${escapeHtml(data.case?.assessmentDate || resolveAssessmentDate())}</strong></p>
          <div class="evidence-list">${sources.length
            ? sources.map((source) => `<a class="evidence-item" href="${escapeHtml(source.sourceUrl)}" target="_blank" rel="noopener noreferrer"><strong>${escapeHtml(source.title)}</strong><br><span class="subtle">${escapeHtml(source.authority)} · ${escapeHtml(source.excerpt || '')}</span></a>`).join('')
            : '<p class="subtle">검증된 공개 근거를 불러오지 못했습니다.</p>'}</div>
        </div>
      </details>
    </div>
    <p class="subtle">${escapeHtml(data.disclaimer || '')}</p>`;
  if (!data.analysisPending) {
    wireNextStep();
    const boost = $('#result-accuracy');
    if (boost) wireAccuracyButtons(boost, (key, value) => {
      analyzeCase(applyAccuracyAnswer(structuredCase, key, value));
    });
  }
}

async function analyzeCase(caseData, { form, errorTarget } = {}) {
  const generation = ++analysisSequence;
  const normalizedCase = { ...caseData, assessmentDate: resolveAssessmentDate() };
  structuredCase = normalizedCase;
  const fingerprint = analysisFingerprint(normalizedCase);
  if (analysisCache.has(fingerprint)) {
    renderResult(analysisCache.get(fingerprint));
    showStep(3);
    return;
  }

  setBusy(form, true);
  renderAnalysisLoading();
  showStep(3);
  let baselineResponse = null;
  try {
    baselineResponse = await request('/api/enforcement/analyze', { caseData: normalizedCase, baselineOnly: true }, { timeoutMs: 10000 });
    if (generation !== analysisSequence) return;
    if (!baselineResponse.legalBaseline) throw new Error('법령 기준 응답이 비어 있습니다. 다시 시도해 주세요.');
    if (baselineResponse.legalBaseline.status !== 'AVAILABLE') {
      // The server never asks the AI without a verified legal baseline, so waiting up
      // to 28 s for the full request only delays the "what to do next" card.
      renderResult({ ...baselineResponse, analysisPending: false });
      return;
    }
    renderResult({ ...baselineResponse, analysisPending: true });
    const response = await request('/api/enforcement/analyze', { caseData: normalizedCase }, { timeoutMs: 28000 });
    if (generation !== analysisSequence) return;
    if (!response.legalBaseline) throw new Error('분석 응답이 비어 있습니다. 다시 시도해 주세요.');
    // Do not cache transient provider failures, so another attempt really retries.
    if (response.prediction?.status && response.prediction.status !== 'UNAVAILABLE') analysisCache.set(fingerprint, response);
    renderResult(response);
    if (response.legalBaseline?.status === 'AVAILABLE' && (!response.prediction?.status || response.prediction.status === 'UNAVAILABLE')) addAnalysisRetry();
  } catch (error) {
    if (generation !== analysisSequence) return;
    if (baselineResponse) {
      renderResult({
        ...baselineResponse,
        analysisPending: false,
        prediction: { ...(baselineResponse.prediction || {}), failureCategory: 'timeout', status: 'UNAVAILABLE' },
      });
      const note = document.createElement('p'); note.className = 'prediction-degraded-note'; note.setAttribute('role', 'status');
      note.textContent = error.message; $('#result-root').append(note); addAnalysisRetry();
    } else {
      if (errorTarget) setError(errorTarget, error.message);
      showStep(2);
    }
  } finally {
    setBusy(form, false);
  }
}

function addAnalysisRetry() {
  const button = document.createElement('button');
  button.type = 'button'; button.className = 'secondary-button analysis-retry'; button.textContent = 'AI 예상 다시 확인';
  button.addEventListener('click', () => { button.disabled = true; analyzeCase(structuredCase); }, { once: true });
  $('#result-root').append(button);
}

$('#case-form').addEventListener('submit', async (event) => {
  event.preventDefault();
  const form = event.currentTarget;
  setError($('#input-error'));
  setBusy(form, true);
  setLoading(true, '사례에서 핵심 사실을 찾고 있어요.', '체류자격, 상황과 기간을 정리합니다.');

  try {
    const text = $('#case-text').value.trim();
    if (!text) throw new Error('사례 설명을 입력해 주세요.');
    sessionNarrative = text;
    sessionLocale = detectLocale(text);
    skippedClarifications.clear();

    const response = await request('/api/enforcement/extract', {
      text,
      assessmentDate: resolveAssessmentDate(),
    }, { timeoutMs: 15000 });
    structuredCase = response.case;
    $('#case-text').value = '';
    updateCount();
    renderConfirmation(structuredCase);
    setLoading(false);
    showStep(2);
  } catch (error) {
    setError($('#input-error'), error.message);
  } finally {
    setBusy(form, false);
    setLoading(false);
  }
});

$('#confirm-form').addEventListener('submit', async (event) => {
  event.preventDefault();
  const form = event.currentTarget;
  setError($('#confirm-error'));
  const pending = clarificationFor(structuredCase);
  if (pending) {
    setError($('#confirm-error'), '위 질문에 답하거나 잘 모르겠어요를 선택해 주세요.');
    $('#clarification-card').scrollIntoView({ behavior: 'smooth', block: 'center' });
    return;
  }
  try {
    await analyzeCase(structuredCase, { form, errorTarget: $('#confirm-error') });
  } catch {
    // analyzeCase already surfaces the user-facing error in this step.
  }
});

function restoreNarrativeForEditing() {
  const textarea = $('#case-text');
  if (textarea && !textarea.value && sessionNarrative) {
    textarea.value = sessionNarrative;
    updateCount();
  }
}

$$('[data-back]').forEach((button) => button.addEventListener('click', () => {
  analysisSequence++;
  const target = Number(button.dataset.back);
  if (target === 1) restoreNarrativeForEditing();
  if (target === 2 && structuredCase) renderConfirmation(structuredCase);
  showStep(target);
}));

$$('[data-step-nav]').forEach((button) => button.addEventListener('click', () => {
  const target = Number(button.dataset.stepNav);
  if (target >= currentStep) return;
  analysisSequence++;
  if (target === 1) restoreNarrativeForEditing();
  if (target === 2 && structuredCase) renderConfirmation(structuredCase);
  showStep(target);
}));

$$('[data-example]').forEach((button) => button.addEventListener('click', () => {
  const textarea = $('#case-text');
  textarea.value = button.dataset.example || '';
  $$('[data-example]').forEach((item) => item.setAttribute('aria-pressed', String(item === button)));
  textarea.focus();
  updateCount();
}));

function updateCount() {
  const textarea = $('#case-text');
  const count = $('#case-count');
  if (!textarea || !count) return;
  count.textContent = `${textarea.value.length} / 3000`;
}

$('#case-text').addEventListener('input', () => {
  $$('[data-example]').forEach((button) => button.setAttribute('aria-pressed', 'false'));
  updateCount();
});
$('#assessment-date-today').addEventListener('click', () => setAssessmentDateToday({ force: true }));

$('#restart').addEventListener('click', () => {
  analysisSequence++;
  structuredCase = null;
  sessionNarrative = '';
  sessionLocale = 'ko-KR';
  skippedClarifications.clear();
  $('#case-form').reset();
  $('#confirm-form').reset();
  $('#result-root').innerHTML = '';
  $('#confirmation-summary').textContent = '';
  $('#confirmed-facts').innerHTML = '';
  $$('[data-example]').forEach((button) => button.setAttribute('aria-pressed', 'false'));
  setError($('#input-error'));
  setError($('#confirm-error'));
  setAssessmentDateToday({ force: true });
  updateCount();
  showStep(1);
  $('#case-text').focus();
});

setAssessmentDateToday();
updateCount();
showStep(1, { scroll: false });
