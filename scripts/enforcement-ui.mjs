const $ = (selector, root = document) => root.querySelector(selector);
const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];

let structuredCase = null;

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

function showStep(number) {
  $$('[data-step]').forEach((section) => { section.hidden = Number(section.dataset.step) !== number; });
  $$('[data-step-nav]').forEach((button) => {
    const value = Number(button.dataset.stepNav);
    button.disabled = value > number;
    button.classList.toggle('is-active', value === number);
    if (value === number) button.setAttribute('aria-current', 'step');
    else button.removeAttribute('aria-current');
  });
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

function setLoading(active) { $('#loading').hidden = !active; }
function setError(target, message = '') { target.textContent = message; target.hidden = !message; }

async function request(path, payload) {
  if (apiBase == null) {
    throw new Error('Visable 분석 서버 주소를 확인하지 못했습니다. 페이지를 새로고침해 주세요.');
  }

  const url = `${apiBase}${path}`;
  let response;
  try {
    response = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
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
    throw new Error(
      typeof data.detail === 'string'
        ? data.detail
        : `분석 서버 요청에 실패했습니다. (${response.status})`
    );
  }
  return data;
}

function assignValue(form, name, value) {
  const input = form.elements.namedItem(name);
  if (!input) return;
  if (typeof value === 'boolean') input.value = String(value);
  else input.value = value ?? '';
}

function populateConfirmation(caseData) {
  const form = $('#confirm-form');
  ['statusOfStay', 'violationCode', 'durationDays', 'priorViolations', 'authorizationObtained',
    'voluntaryDisclosure', 'violationStartDate', 'violationEndDate'].forEach((name) => assignValue(form, name, caseData[name]));
  const unknown = caseData.unknownFacts || [];
  $('#unknown-facts').innerHTML = unknown.length
    ? `<strong>정확도에 영향을 줄 수 있는 미확인 정보</strong><ul>${unknown.map((item) => `<li>${escapeHtml(item)}</li>`).join('')}</ul>`
    : '<strong>주요 입력 사실이 모두 확인되었습니다.</strong>';
}

function nullableBoolean(value) {
  if (value === '') return null;
  return value === 'true';
}

function readConfirmedCase() {
  const form = $('#confirm-form');
  const value = (name) => form.elements.namedItem(name).value.trim();
  const numberOrNull = (name) => value(name) === '' ? null : Number(value(name));
  return {
    ...structuredCase,
    statusOfStay: value('statusOfStay') || null,
    violationCode: value('violationCode') || null,
    violationCandidates: value('violationCode') ? [value('violationCode')] : [],
    durationDays: numberOrNull('durationDays'),
    priorViolations: numberOrNull('priorViolations'),
    authorizationObtained: nullableBoolean(value('authorizationObtained')),
    voluntaryDisclosure: nullableBoolean(value('voluntaryDisclosure')),
    violationStartDate: value('violationStartDate') || null,
    violationEndDate: value('violationEndDate') || null,
  };
}

const won = (value) => value == null ? '산출 불가' : `${Number(value).toLocaleString('ko-KR')}원`;
const range = (value) => !value ? '예상 범위 산출 불가' : `${won(value.minimumKrw)} – ${won(value.maximumKrw)}`;
const confidenceLabels = { VERY_HIGH: '매우 높음', HIGH: '높음', MEDIUM: '중간', LOW: '낮음', VERY_LOW: '매우 낮음', INSUFFICIENT: '근거 부족' };
const likelihoodLabels = { VERY_HIGH: '매우 높음', HIGH: '높음', MODERATE: '중간', LOW: '낮음', VERY_LOW: '매우 낮음', UNKNOWN: '특정 어려움' };
const groundingLabels = { VERIFIED: '실시간 법령 API 검증 완료', AUDIT_ONLY: '법령 API 감사 모드', LIMITED: '법령 API 부분 검증', UNAVAILABLE: '정적 법령 스냅샷 사용' };
const dispositionLabels = {
  NO_IMMEDIATE_DEPARTURE_MEASURE: '즉시 출국조치 없음',
  STAY_PERMISSION_DISADVANTAGE: '체류허가상 불이익',
  DEPARTURE_RECOMMENDATION: '출국권고',
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
    <div class="result-grid">
      <article class="result-card baseline">
        <p class="card-kicker">1 · DETERMINISTIC LEGAL BASELINE</p>
        <h3>법령 기준</h3>
        <p class="subtle">법령상 기준 범칙금</p>
        <p class="amount">${won(baseline.baselineAmountKrw)}</p>
        <p>통상 가감 범위(시행규칙 제86조제2항): <strong>${range(baseline.legallyAdjustableRange)}</strong></p>
        <p><span class="tag">${escapeHtml(groundingLabel)}</span></p>
        <p class="subtle">${escapeHtml((baseline.appliedRules || []).join(' · '))}</p>
      </article>
      <article class="result-card prediction">
        <p class="card-kicker">2 · VISABLE AI PREDICTION</p>
        <h3>Visable AI 예상</h3>
        <p class="subtle">예상 범칙금</p>
        <p class="amount">${monetary ? range(monetary.predictedLikelyRange) : '생성하지 못함'}</p>
        <p>${monetary?.pointEstimateKrw != null ? `대표 추정액: <strong>${won(monetary.pointEstimateKrw)}</strong>` : '근거가 충분하지 않아 대표 추정액을 표시하지 않습니다.'}</p>
        <p class="subtle">${escapeHtml(modelLabel)} · AI 금액 예측은 위 통상 가감 범위 안으로 제한됩니다.</p>
      </article>
      <article class="result-card span-2">
        <p class="card-kicker">3 · DISPOSITION</p>
        <h3>예상 행정처분</h3>
        ${disposition(prediction.primaryDisposition, true)}
        ${(prediction.alternativeDispositions || []).map((item) => disposition(item)).join('')}
      </article>
      <article class="result-card">
        <p class="card-kicker">4 · CONFIDENCE</p>
        <h3>예측 신뢰도 · ${escapeHtml(confidenceLabels[confidence.level] || confidence.level)}</h3>
        ${factors((confidence.reasons || []).map((label, index) => ({ label, basis: index ? 'INFERRED' : 'SUPPORTED' })))}
      </article>
      <article class="result-card">
        <p class="card-kicker">5 · SIMILAR CASES</p>
        <h3>유사사례</h3>
        ${similar.length ? similar.map((item) => `<a class="evidence-item" href="${escapeHtml(item.sourceUrl)}" target="_blank" rel="noopener noreferrer"><strong>${escapeHtml(item.sourceTitle || item.id)}</strong><br><span class="subtle">${escapeHtml(item.outcomeSummary)}</span></a>`).join('') : '<p class="subtle">현재 확인 가능한 유사 공개사례가 충분하지 않습니다.</p>'}
      </article>
      <article class="result-card span-2">
        <p class="card-kicker">6 · WHY THIS PREDICTION?</p>
        <h3>예상 근거</h3>
        <div class="result-grid">
          <div><strong>가중 방향 요인</strong>${factors(prediction.aggravatingFactors)}</div>
          <div><strong>감경 방향 요인</strong>${factors(prediction.mitigatingFactors)}</div>
          <div><strong>미확인 요인</strong>${factors(prediction.unresolvedFactors)}</div>
          <div><strong>한계</strong>${limitations.length ? `<ul>${limitations.map((item) => `<li>${escapeHtml(item)}</li>`).join('')}</ul>` : '<p class="subtle">추가 한계 없음</p>'}</div>
        </div>
      </article>
      <article class="result-card span-2">
        <p class="card-kicker">OFFICIAL SOURCES</p><h3>법적 근거</h3>
        <p class="subtle">${escapeHtml(groundingLabel)}${grounding.credentialSource ? ` · ${escapeHtml(grounding.credentialSource)}` : ''}</p>
        <div class="evidence-list">${sources.length ? sources.map((source) => `<a class="evidence-item" href="${escapeHtml(source.sourceUrl)}" target="_blank" rel="noopener noreferrer"><strong>${escapeHtml(source.title)}</strong><br><span class="subtle">${escapeHtml(source.authority)} · ${escapeHtml(source.excerpt || '')}</span></a>`).join('') : '<p class="subtle">검증된 공개 근거를 불러오지 못했습니다.</p>'}</div>
      </article>
    </div>
    <p class="subtle">${escapeHtml(data.disclaimer || '')}</p>`;
}

$('#case-form').addEventListener('submit', async (event) => {
  event.preventDefault();
  setError($('#input-error'));
  setLoading(true);
  try {
    const text = $('#case-text').value.trim();
    if (!text) throw new Error('사례 설명을 입력해 주세요.');
    const response = await request('/api/enforcement/extract', {
      text,
      assessmentDate: $('#assessment-date').value || null,
    });
    structuredCase = response.case;
    populateConfirmation(structuredCase);
    // Discard the raw narrative from live UI state after extraction.
    $('#case-text').value = '';
    showStep(2);
  } catch (error) { setError($('#input-error'), error.message); }
  finally { setLoading(false); }
});

$('#confirm-form').addEventListener('submit', async (event) => {
  event.preventDefault();
  setError($('#confirm-error'));
  setLoading(true);
  try {
    structuredCase = readConfirmedCase();
    const response = await request('/api/enforcement/analyze', { caseData: structuredCase });
    renderResult(response);
    showStep(3);
  } catch (error) { setError($('#confirm-error'), error.message); }
  finally { setLoading(false); }
});

$$('[data-back]').forEach((button) => button.addEventListener('click', () => showStep(Number(button.dataset.back))));
$('#restart').addEventListener('click', () => {
  structuredCase = null;
  $('#case-form').reset();
  $('#confirm-form').reset();
  $('#result-root').replaceChildren();
  showStep(1);
});
