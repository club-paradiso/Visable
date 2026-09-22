'use strict';

/**
 * Waymaker Quick Answer — optional wording enhancement (server side).
 *
 * The client sends a VALIDATED, deterministic Quick Answer model. The model
 * may only rephrase the summary; it may not add or change facts. Its output is
 * accepted only when the same validator the client uses (validateEnhancement in
 * assets/js/waymaker-quick-answer.js) finds no number, amount, document, form,
 * office or fee that the model does not already contain. Anything else returns
 * ok:false and the client keeps the deterministic sentence.
 *
 * No personal data: the payload is the structured model (status code, procedure,
 * document names, fee lines) plus the user's typed query. Nothing is stored.
 */
const QA = require('../assets/js/waymaker-quick-answer.js');

const DEFAULT_MODELS = ['google/gemma-4-31b-it:free', 'openai/gpt-oss-120b:free', 'meta-llama/llama-3.3-70b-instruct:free'];
const RANDOM_MODEL_IDS = new Set(['openrouter/auto', 'openrouter/free', 'auto', 'free']);

function runtimeConfig() {
  const modelsRaw = String(process.env.WAYMAKER_QA_OPENROUTER_MODEL_CANDIDATES || process.env.OPENROUTER_MODEL_CANDIDATES || '').trim();
  const primary = String(process.env.WAYMAKER_QA_OPENROUTER_MODEL || process.env.OPENROUTER_MODEL || DEFAULT_MODELS[0]).trim();
  const configured = modelsRaw ? modelsRaw.split(',').map((m) => m.trim()) : DEFAULT_MODELS;
  const models = [...new Set([primary, ...configured])].filter(Boolean).filter((m) => !RANDOM_MODEL_IDS.has(m.toLowerCase()) && !m.toLowerCase().endsWith('/auto'));
  return {
    key: String(process.env.OPENROUTER_API_KEY || '').trim(),
    models,
    siteUrl: String(process.env.SITE_URL || 'https://visable-mu.vercel.app').trim(),
    siteTitle: String(process.env.SITE_TITLE || 'Visable Waymaker Quick Answer').trim(),
    timeoutMs: Math.min(Math.max(Number(process.env.WAYMAKER_QA_TIMEOUT_SECONDS || 7) * 1000, 2000), 20000),
  };
}

function publicRuntimeConfig() {
  const cfg = runtimeConfig();
  return { openrouterConfigured: Boolean(cfg.key), modelCandidates: cfg.models, timeoutMs: cfg.timeoutMs };
}

const MODES = new Set(['answer', 'fee', 'clarify', 'fallback']);
function cleanText(v, limit) { return String(v == null ? '' : v).replace(/\s+/g, ' ').trim().slice(0, limit); }
function cleanList(list, limit, itemLimit) { return Array.isArray(list) ? list.slice(0, limit).map((x) => (typeof x === 'string' ? cleanText(x, itemLimit) : x)) : []; }

/** Accept only the shape the client produces; strip anything else. Returns null when unusable. */
function sanitizeModel(input) {
  if (!input || typeof input !== 'object') return null;
  const m = input;
  if (!MODES.has(m.mode)) return null;
  const docs = m.documents && typeof m.documents === 'object' ? m.documents : {};
  const doc = (d) => (d && typeof d === 'object' ? { name: cleanText(d.name, 160), form: cleanText(d.form, 40) || 'SOURCE_DOES_NOT_SPECIFY', appliesWhen: d.appliesWhen ? cleanText(d.appliesWhen, 200) : null } : null);
  const out = {
    version: 1,
    query: cleanText(m.query, 300),
    mode: m.mode,
    interpretation: {
      status: m.interpretation && /^[A-H]-\d{1,2}(-[0-9A-Z]{1,6})?$/.test(String(m.interpretation.status || '')) ? m.interpretation.status : null,
      procedure: m.interpretation ? cleanText(m.interpretation.procedure, 40) || null : null,
      procedureLabel: m.interpretation ? cleanText(m.interpretation.procedureLabel, 80) : '',
      office: m.interpretation ? cleanText(m.interpretation.office, 40) || null : null,
      program: m.interpretation ? cleanText(m.interpretation.program, 20) || null : null,
      facet: m.interpretation ? cleanText(m.interpretation.facet, 20) || null : null,
      confidence: ['HIGH', 'MEDIUM', 'LOW'].includes(m.interpretation && m.interpretation.confidence) ? m.interpretation.confidence : 'LOW',
    },
    title: cleanText(m.title, 160),
    summary: cleanText(m.summary, 900),
    documents: {
      required: (docs.required || []).slice(0, 20).map(doc).filter(Boolean),
      conditional: (docs.conditional || []).slice(0, 20).map(doc).filter(Boolean),
      applicableOnly: (docs.applicableOnly || []).slice(0, 20).map(doc).filter(Boolean),
      alternatives: (docs.alternatives || []).slice(0, 10).map((a) => (a && typeof a === 'object' ? { ref: cleanText(a.ref, 60), name: cleanText(a.name, 160), options: cleanList(a.options, 10, 120) } : null)).filter(Boolean),
      omittable: (docs.omittable || []).slice(0, 20).map(doc).filter(Boolean),
    },
    fees: (Array.isArray(m.fees) ? m.fees : []).slice(0, 6).map((f) => ({
      id: cleanText(f.id, 60), label: cleanText(f.label, 120), amount: Number.isFinite(Number(f.amount)) ? Number(f.amount) : 0, amountState: cleanText(f.amountState, 20), currency: 'KRW',
      instruments: cleanList(f.instruments, 6, 40), onlineReduction: Number.isFinite(Number(f.onlineReduction)) ? Number(f.onlineReduction) : null, review: cleanText(f.review, 40),
      exemptions: (Array.isArray(f.exemptions) ? f.exemptions : []).slice(0, 8).map((e) => ({ id: cleanText(e.id, 60), condition: cleanText(e.condition, 400), review: cleanText(e.review, 40), program: e.program ? cleanText(e.program, 20) : null })),
      notExempt: cleanList(f.notExempt, 4, 300), conflicts: (Array.isArray(f.conflicts) ? f.conflicts : []).slice(0, 3).map((c) => ({ regulation: cleanText(c.regulation, 200), manual: cleanText(c.manual, 200), interim: cleanText(c.interim, 200) })),
    })),
    localPractice: { office: m.localPractice && m.localPractice.office ? { id: cleanText(m.localPractice.office.id, 40), name: cleanText(m.localPractice.office.name, 80) } : null, variations: (m.localPractice && Array.isArray(m.localPractice.variations) ? m.localPractice.variations : []).slice(0, 6).map((v) => ({ id: cleanText(v.id, 80), layer: cleanText(v.layer, 40), summary: cleanText(v.summary, 300) })) },
    sources: (Array.isArray(m.sources) ? m.sources : []).slice(0, 20).map((s) => ({ type: cleanText(s.type, 20), title: cleanText(s.title, 120), article: s.article ? cleanText(s.article, 40) : null, page: Number.isFinite(Number(s.page)) ? Number(s.page) : null })),
    uncertainties: (Array.isArray(m.uncertainties) ? m.uncertainties : []).slice(0, 8).map((u) => ({ id: cleanText(u.id, 40), text: cleanText(u.text, 300) })),
  };
  return QA.validateModel(out).ok ? out : null;
}

function systemPrompt(lang) {
  const ko = lang !== 'en';
  return ko
    ? [
      '당신은 Visable의 문장 정리 도우미입니다. 출입국 사실을 만들어 내는 역할이 아닙니다.',
      '입력으로 이미 검증된 구조화 안내(절차, 서류, 원본/사본 표기, 수수료, 면제 조건, 관서 정보, 근거, 불확실한 점)가 주어집니다.',
      '할 일: 주어진 summary를 사용자에게 읽기 쉬운 한국어 2~3문장(총 120~320자)으로 다시 씁니다.',
      '금지: 입력에 없는 서류·원본/사본 요건·수수료·금액·면제·기한·관서별 관행·자격 요건·숫자를 추가하거나 바꾸는 것. 허가를 보장하거나 단정하는 표현. 인사말, 목록, 마크다운, 링크.',
      '입력에 conflicts나 uncertainties가 있으면 그 취지를 한 문장으로 유지합니다.',
      '출력은 JSON 객체 하나: {"summary": "..."}',
    ].join('\n')
    : [
      'You are Visable\'s wording assistant. You do not originate immigration facts.',
      'You receive an already-validated structured answer (procedure, documents, original/copy markings, fees, exemption conditions, office information, sources, uncertainties).',
      'Task: rewrite the given summary into 2–3 plain English sentences (120–320 characters) that are easy to read.',
      'Forbidden: adding or changing any document, original/copy requirement, fee, amount, exemption, deadline, office practice, eligibility rule or number that is not in the input; guaranteeing or asserting approval; greetings, lists, markdown, links.',
      'If the input has conflicts or uncertainties, keep their gist in one sentence.',
      'Output exactly one JSON object: {"summary": "..."}',
    ].join('\n');
}

async function callOpenRouter(messages, cfg) {
  if (!cfg.key) return { ok: false, error: 'openrouter_not_configured' };
  let lastError = 'no_model_succeeded';
  for (const model of cfg.models) {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), cfg.timeoutMs);
    try {
      const response = await fetch('https://openrouter.ai/api/v1/chat/completions', {
        method: 'POST',
        headers: { Authorization: `Bearer ${cfg.key}`, 'Content-Type': 'application/json', 'HTTP-Referer': cfg.siteUrl, 'X-Title': cfg.siteTitle },
        body: JSON.stringify({ model, messages, temperature: 0.2, max_tokens: 400, response_format: { type: 'json_object' } }),
        signal: controller.signal,
      });
      if (!response.ok) { lastError = `http_${response.status}`; if ([401, 402, 403].includes(response.status)) break; continue; }
      const payload = await response.json();
      const content = payload && payload.choices && payload.choices[0] && payload.choices[0].message ? payload.choices[0].message.content : null;
      const text = Array.isArray(content) ? content.map((c) => (typeof c === 'string' ? c : (c && c.text) || '')).join('') : String(content || '');
      if (!text.trim()) { lastError = 'empty_response'; continue; }
      return { ok: true, model: payload.model || model, text };
    } catch (error) {
      lastError = error && error.name === 'AbortError' ? 'timeout' : 'network_error';
    } finally {
      clearTimeout(timer);
    }
  }
  return { ok: false, error: lastError };
}

function parseSummary(text) {
  const stripped = String(text || '').trim().replace(/^```(?:json)?\s*/i, '').replace(/\s*```$/, '').trim();
  try { const obj = JSON.parse(stripped); if (obj && typeof obj.summary === 'string') return obj.summary; } catch (e) { /* fall through */ }
  const m = stripped.match(/"summary"\s*:\s*"([\s\S]*?)"\s*}?\s*$/);
  return m ? m[1] : null;
}

/**
 * @returns {{ok:boolean, summary?:string, model?:string, error?:string, status?:string, reasons?:string[]}}
 */
async function enhanceQuickAnswer(payload, deps = {}) {
  const lang = payload && payload.lang === 'en' ? 'en' : 'ko';
  const model = sanitizeModel(payload && payload.model);
  if (!model) return { ok: false, error: 'invalid_model', status: 'REJECTED_INPUT' };
  if (model.mode !== 'answer') return { ok: false, error: 'deterministic_mode', status: 'NOT_NEEDED' };
  const cfg = deps.config || runtimeConfig();
  if (!cfg.key) return { ok: false, error: 'openrouter_not_configured', status: 'NOT_CONFIGURED' };
  const call = deps.callOpenRouter || callOpenRouter;
  const messages = [
    { role: 'system', content: systemPrompt(lang) },
    { role: 'user', content: JSON.stringify({ lang, structured_answer: model }) },
  ];
  const result = await call(messages, cfg);
  if (!result.ok) return { ok: false, error: result.error, status: 'PROVIDER_FAILED' };
  const summary = parseSummary(result.text);
  if (!summary) return { ok: false, error: 'unparseable', status: 'REJECTED_OUTPUT' };
  const verdict = QA.validateEnhancement(model, summary);
  if (!verdict.ok) return { ok: false, error: 'validation_failed', status: 'REJECTED_OUTPUT', reasons: verdict.reasons };
  return { ok: true, summary: verdict.text, model: result.model, status: 'OK' };
}

module.exports = { enhanceQuickAnswer, sanitizeModel, systemPrompt, parseSummary, runtimeConfig, publicRuntimeConfig, callOpenRouter };
