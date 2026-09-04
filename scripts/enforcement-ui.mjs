const $ = (selector, root = document) => root.querySelector(selector);
const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];

let structuredCase = null;
let currentStep = 1;
let sessionNarrative = '';
let sessionLocale = 'ko-KR';
let confirmationRequestToken = 0;
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
  $$('[data-step]').forEach((section) => {
    section.hidden = Number(section.dataset.step) !== number;
  });
  $$('[data-step-nav]').forEach((button) => {
    const value = Number(button.dataset.stepNav);
    button.disabled = value > number;
    button.classList.toggle('is-active', value === number);
    if (value === number) button.setAttribute('aria-current', 'step');
    else button.removeAttribute('aria-current');
  });
  if (scroll) window.scrollTo({ top: 0, behavior: 'smooth' });
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

async function request(path, payload) {
  if (apiBase == null) {
    throw new Error('Visable 분석 서버 주소를 확인하지 못했습니다. 페이지를 새로고침해 주세요.');
  }

  const url = `${apiBase}${path}`;
  let response;
  try {
    response = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
      body: JSON.stringify(payload),
    });
  } catch (error) {
    console.error('Enforcement API connection failure', { url, error });
    throw new Error('Visable 분석 서버에 연결하지 못했습니다. 잠시 후 다시 시도해 주세요.');
  }

  const contentType = response.headers.get('content-type') || '';
  const data = contentType.includes('application/json')
    ? await response.json().catch(() => ({}))
    : {};

  if (!response.ok) {
    console.error('Enforcement API request failure', { url, status: response.status });
    const detail = typeof data.detail === 'string' ? data.detail : '';
    const friendly = {
      'case text is required': '사례 설명을 입력해 주세요.',
      'invalid assessmentDate': '분석 기준일 형식을 확인해 주세요.',
      'invalid structured enforcement case': '확인한 사실 중 형식이 맞지 않는 항목이 있습니다. 입력값을 다시 확인해 주세요.',
    }[detail];
    throw new Error(friendly || detail || `분석 서버 요청에 실패했습니다. (${response.status})`);
  }
  return data;
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

  const clauses = [];
  if (status) clauses.push(`현재 ${status} 체류자격`);

  if (caseData.violationCode === 'OVERSTAY_ART25') {
    clauses.push(days != null ? `허가된 체류기간이 지난 뒤 ${days}일 동안 더 체류한 상황` : '허가된 체류기간이 지난 뒤에도 계속 체류한 상황');
  } else if (activity || workplace || caseData.authorizationObtained === false) {
    let work = workplace ? `${workplace}에서 ` : '';
    if (caseData.authorizationObtained === false) work += '필요한 허가 없이 ';
    work += activity || '일을 했고';
    if (days != null) work += ` 그 기간은 ${days}일`;
    clauses.push(work.replace(/했고 그 기간은/, '했으며 그 기간은'));
  } else if (caseData.violationCode) {
    clauses.push(violationLabels[caseData.violationCode] || '출입국 관련 위반 상황');
  }

  if (caseData.priorViolations === 0) clauses.push('이번이 첫 위반');
  else if (Number(caseData.priorViolations) > 0) clauses.push(`과거 위반 전력이 ${Number(caseData.priorViolations)}회`);
  if (caseData.voluntaryDisclosure === true) clauses.push('본인이 먼저 신고하거나 출입국관서에 자진 방문');
  if (caseData.investigationStarted === true && caseData.voluntaryDisclosure !== true) clauses.push('이미 적발되었거나 조사가 시작된 상태');

  if (!clauses.length) return '입력한 내용 중 일부 사실만 확인할 수 있었어요.';
  return `${clauses.join(', ')}인 것으로 이해했어요.`;
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
    ['허가 여부', caseData.authorizationObtained == null ? '확인되지 않음' : (caseData.authorizationObtained ? '필요한 허가를 받은 것으로 입력됨' : '필요한 허가를 받지 않은 것으로 입력됨')],
    ['과거 위반', caseData.priorViolations == null ? '확인되지 않음' : (Number(caseData.priorViolations) === 0 ? '첫 위반으로 입력됨' : `${Number(caseData.priorViolations)}회`)],
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
      question: '현재 체류자격이 무엇인가요?',
      hint: '예: D-2, E-7-4, F-2',
    };
  }

  if (!caseData.violationCode && !skippedClarifications.has('violationCode')) {
    const candidates = new Set(caseData.violationCandidates || []);
    const options = [];
    const add = (value, label) => { if (!candidates.size || candidates.has(value)) options.push({ value, label }); };
    add('STATUS_OUTSIDE_ACTIVITY_ART20', '학생 등의 체류자격으로, 필요한 활동 허가 없이 일을 했어요');
    add('UNAUTHORIZED_STAY_OR_WORK_ART18_1', '애초에 취업할 수 없는 체류자격인데 일을 했어요');
    add('UNAUTHORIZED_EMPLOYMENT_ART18_2', '허가된 회사는 그대로이고, 지정된 근무처가 아닌 곳에서도 일했어요');
    add('UNAUTHORIZED_WORKPLACE_CHANGE_ART21_1', '다른 회사·사업장으로 옮기거나 추가했는데 필요한 변경·추가 허가를 받지 않았어요');
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
    answers.innerHTML = `<div class="clarification-input-row"><input id="clarification-input" type="${type}" ${attrs} placeholder="${escapeHtml(question.hint || '')}" aria-label="${escapeHtml(question.question)}"><button type="button" class="primary-button secondary-button--small" id="clarification-apply">확인</button></div>
      <button type="button" class="clarification-option clarification-option--muted" data-clarify-skip="${escapeHtml(question.kind)}">잘 모르겠어요</button>`;
  }

  $$('[data-clarify-value]', answers).forEach((button) => button.addEventListener('click', () => {
    applyClarification(question.kind, button.dataset.clarifyValue || '');
  }));
  $$('[data-clarify-skip]', answers).forEach((button) => button.addEventListener('click', () => {
    skippedClarifications.add(button.dataset.clarifySkip || question.kind);
    setError($('#confirm-error'));
    renderConfirmation(structuredCase);
    void humanizeConfirmation(structuredCase);
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
  void humanizeConfirmation(structuredCase);
}

function confirmationFingerprint(caseData) {
  const keys = [
    'statusOfStay', 'violationCode', 'activity', 'workplaceType', 'authorizationObtained',
    'workplaceChangeAuthorized', 'durationDays', 'priorViolations', 'voluntaryDisclosure',
    'investigationStarted', 'violationStartDate', 'violationEndDate'
  ];
  return JSON.stringify(keys.map((key) => caseData?.[key] ?? null));
}

function renderConfirmation(caseData) {
  $('#confirmation-summary').textContent = deterministicSummary(caseData);
  $('#confirmation-source').hidden = true;
  renderFactList(caseData);
  renderConfirmationNotes(caseData);
  renderClarification(caseData);
}

async function humanizeConfirmation(caseData) {
  if (!caseData || location.protocol === 'file:') return;
  const fingerprint = confirmationFingerprint(caseData);
  const requestToken = ++confirmationRequestToken;
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 9000);
  try {
    const response = await fetch(new URL('/api/enforcement/confirm', window.location.origin), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
      body: JSON.stringify({ caseData, locale: sessionLocale }),
      signal: controller.signal,
    });
    if (!response.ok) return;
    const data = await response.json().catch(() => ({}));
    if (requestToken !== confirmationRequestToken || currentStep !== 2) return;
    if (confirmationFingerprint(structuredCase) !== fingerprint) return;
    if (data.mode !== 'gemma' || typeof data.summary !== 'string' || !data.summary.trim()) return;
    $('#confirmation-summary').textContent = data.summary.trim();
    $('#confirmation-source').hidden = false;
  } catch {
    // The deterministic confirmation is already visible; model polishing is best-effort only.
  } finally {
    clearTimeout(timer);
  }
}

function analysisFingerprint(caseData) {
  const keys = [
    'statusOfStay', 'violationCode', 'durationDays', 'priorViolations',
    'authorizationObtained', 'workplaceChangeAuthorized', 'voluntaryDisclosure',
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

function factors(items = []) {
  if (!items.length) return '<p class="subtle">확인된 요인이 없습니다.</p>';
  return `<ul>${items.map((item) => `<li>${escapeHtml(item.label)} <span class="tag">${escapeHtml(item.basis)}</span></li>`).join('')}</ul>`;
}

function disposition(item, primary = false) {
  if (!item) return '<p class="subtle">현재 공개된 근거만으로 가장 유력한 처분을 특정하기 어렵습니다.</p>';
  return `<div class="disposition"><strong><span>${primary ? '가장 유력 · ' : ''}${escapeHtml(dispositionLabels[item.type] || item.type)}</span><span>${escapeHtml(likelihoodLabels[item.likelihood] || item.likelihood)}</span></strong>${factors(item.rationale)}</div>`;
}

function renderResult(data) {
  const baseline = data.legalBaseline || {};
  const prediction = data.prediction || {};
  const grounding = data.lawGrounding || {};
  const monetary = prediction.monetaryPrediction;
  const confidence = prediction.confidence || { level: 'INSUFFICIENT', reasons: [] };
  const sources = prediction.evidence || [];
  const similar = prediction.similarCases || [];
  const limitations = prediction.limitations || [];
  const groundingLabel = groundingLabels[grounding.status] || grounding.status || '상태 확인 불가';
  const modelLabel = prediction.modelId ? `모델: ${prediction.modelId}` : '검증된 AI 결과 없음';

  $('#result-root').innerHTML = `
    <div class="result-summary">
      <article class="result-card baseline">
        <p class="card-kicker">DETERMINISTIC LEGAL BASELINE</p>
        <h3>법령 기준</h3>
        <p class="subtle">법령상 기준 범칙금</p>
        <p class="amount">${won(baseline.baselineAmountKrw)}</p>
        <p>법정 조정 가능 범위: <strong>${range(baseline.legallyAdjustableRange)}</strong></p>
        <p><span class="tag">${escapeHtml(groundingLabel)}</span></p>
      </article>
      <article class="result-card prediction">
        <p class="card-kicker">VISABLE AI PREDICTION</p>
        <h3>Visable AI 예상</h3>
        <p class="subtle">예상 범칙금</p>
        <p class="amount">${monetary ? range(monetary.predictedLikelyRange) : '생성하지 못함'}</p>
        <p>${monetary?.pointEstimateKrw != null ? `대표 추정액: <strong>${won(monetary.pointEstimateKrw)}</strong>` : '근거가 충분하지 않아 대표 추정액을 표시하지 않습니다.'}</p>
        <p class="subtle">${escapeHtml(modelLabel)}</p>
      </article>
    </div>

    <article class="result-lead">
      <p class="card-kicker">DISPOSITION</p>
      <h3>예상 행정처분</h3>
      ${disposition(prediction.primaryDisposition, true)}
      ${(prediction.alternativeDispositions || []).map((item) => disposition(item)).join('')}
    </article>

    <div class="result-details">
      <details>
        <summary>예측 신뢰도 · ${escapeHtml(confidenceLabels[confidence.level] || confidence.level)}</summary>
        <div class="detail-body">
          <h3>예측 신뢰도</h3>
          ${factors((confidence.reasons || []).map((label, index) => ({ label, basis: index ? 'INFERRED' : 'SUPPORTED' })))}
        </div>
      </details>

      <details>
        <summary>왜 이런 예상이 나왔나요?</summary>
        <div class="detail-body">
          <p class="card-kicker">WHY THIS PREDICTION?</p>
          <h3>예상 근거</h3>
          <div class="result-grid">
            <div><strong>가중 방향 요인</strong>${factors(prediction.aggravatingFactors)}</div>
            <div><strong>감경 방향 요인</strong>${factors(prediction.mitigatingFactors)}</div>
            <div><strong>미확인 요인</strong>${factors(prediction.unresolvedFactors)}</div>
            <div><strong>한계</strong>${limitations.length ? `<ul>${limitations.map((item) => `<li>${escapeHtml(item)}</li>`).join('')}</ul>` : '<p class="subtle">추가 한계 없음</p>'}</div>
          </div>
        </div>
      </details>

      <details>
        <summary>유사사례 ${similar.length ? `(${similar.length})` : ''}</summary>
        <div class="detail-body">
          <h3>유사사례</h3>
          ${similar.length
            ? `<div class="evidence-list">${similar.map((item) => `<a class="evidence-item" href="${escapeHtml(item.sourceUrl)}" target="_blank" rel="noopener noreferrer"><strong>${escapeHtml(item.sourceTitle || item.id)}</strong><br><span class="subtle">${escapeHtml(item.outcomeSummary)}</span></a>`).join('')}</div>`
            : '<p class="subtle">현재 확인 가능한 유사 공개사례가 충분하지 않습니다.</p>'}
        </div>
      </details>

      <details>
        <summary>법적 근거와 공식 출처</summary>
        <div class="detail-body">
          <p class="card-kicker">OFFICIAL SOURCES</p>
          <h3>법적 근거</h3>
          <p class="subtle">${escapeHtml(groundingLabel)}${grounding.credentialSource ? ` · ${escapeHtml(grounding.credentialSource)}` : ''}</p>
          <p class="subtle">적용 규칙: ${escapeHtml((baseline.appliedRules || []).join(' · ') || '표시할 규칙 없음')}</p>
          <p class="subtle">분석 기준일: <strong>${escapeHtml(data.case?.assessmentDate || resolveAssessmentDate())}</strong></p>
          <div class="evidence-list">${sources.length
            ? sources.map((source) => `<a class="evidence-item" href="${escapeHtml(source.sourceUrl)}" target="_blank" rel="noopener noreferrer"><strong>${escapeHtml(source.title)}</strong><br><span class="subtle">${escapeHtml(source.authority)} · ${escapeHtml(source.excerpt || '')}</span></a>`).join('')
            : '<p class="subtle">검증된 공개 근거를 불러오지 못했습니다.</p>'}</div>
        </div>
      </details>
    </div>
    <p class="subtle">${escapeHtml(data.disclaimer || '')}</p>`;
}

async function analyzeCase(caseData, { form, errorTarget } = {}) {
  const normalizedCase = { ...caseData, assessmentDate: resolveAssessmentDate() };
  structuredCase = normalizedCase;
  const fingerprint = analysisFingerprint(normalizedCase);
  if (analysisCache.has(fingerprint)) {
    renderResult(analysisCache.get(fingerprint));
    showStep(3);
    return;
  }

  setBusy(form, true);
  setLoading(true, '법령 기준과 예상 처분을 분석하고 있어요.', '결론을 먼저 정리한 뒤 근거와 유사사례를 함께 표시합니다.');
  try {
    const response = await request('/api/enforcement/analyze', { caseData: normalizedCase });
    analysisCache.set(fingerprint, response);
    renderResult(response);
    showStep(3);
  } catch (error) {
    if (errorTarget) setError(errorTarget, error.message);
    throw error;
  } finally {
    setBusy(form, false);
    setLoading(false);
  }
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
    confirmationRequestToken += 1;

    const response = await request('/api/enforcement/extract', {
      text,
      assessmentDate: resolveAssessmentDate(),
    });
    structuredCase = response.case;
    $('#case-text').value = '';
    updateCount();
    renderConfirmation(structuredCase);
    setLoading(false);
    showStep(2);
    void humanizeConfirmation(structuredCase);
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
  const target = Number(button.dataset.back);
  confirmationRequestToken += 1;
  if (target === 1) restoreNarrativeForEditing();
  if (target === 2 && structuredCase) renderConfirmation(structuredCase);
  showStep(target);
  if (target === 2 && structuredCase) void humanizeConfirmation(structuredCase);
}));

$$('[data-step-nav]').forEach((button) => button.addEventListener('click', () => {
  const target = Number(button.dataset.stepNav);
  if (target >= currentStep) return;
  confirmationRequestToken += 1;
  if (target === 1) restoreNarrativeForEditing();
  if (target === 2 && structuredCase) renderConfirmation(structuredCase);
  showStep(target);
  if (target === 2 && structuredCase) void humanizeConfirmation(structuredCase);
}));

$$('[data-example]').forEach((button) => button.addEventListener('click', () => {
  const textarea = $('#case-text');
  textarea.value = button.dataset.example || '';
  textarea.focus();
  updateCount();
}));

function updateCount() {
  const textarea = $('#case-text');
  const count = $('#case-count');
  if (!textarea || !count) return;
  count.textContent = `${textarea.value.length} / 3000`;
}

$('#case-text').addEventListener('input', updateCount);
$('#assessment-date-today').addEventListener('click', () => setAssessmentDateToday({ force: true }));

$('#restart').addEventListener('click', () => {
  structuredCase = null;
  sessionNarrative = '';
  sessionLocale = 'ko-KR';
  confirmationRequestToken += 1;
  skippedClarifications.clear();
  $('#case-form').reset();
  $('#confirm-form').reset();
  $('#result-root').innerHTML = '';
  $('#confirmation-summary').textContent = '';
  $('#confirmed-facts').innerHTML = '';
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