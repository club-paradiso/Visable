'use strict';

// Operator check for the Groq provider. GET only, fixed synthetic prompt: it never
// accepts a case, prompt or key from the caller and never returns the key.
// ?diagnose=1 spends one tiny request per configured model.
module.exports = async function handler(request, response) {
  if (request.method !== 'GET') {
    response.setHeader('Allow', 'GET');
    return response.status(405).json({ detail: 'method not allowed' });
  }

  const { groqModelCandidates } = require('../../lib/enforcement-grounded-ai').publicRuntimeConfig();
  const key = String(process.env.GROQ_API_KEY || '').trim();
  const base = { service: 'visable-enforcement-groq-probe', configured: Boolean(key), models: groqModelCandidates };
  if (!key) return response.status(200).json({ ...base, status: 'not_configured' });
  const mode = request.query && request.query.diagnose;

  // Full pipeline on ONE fixed synthetic case (never caller input): legal baseline ->
  // Groq -> server validation. Returns only statuses, never the model's text.
  if (mode === 'analysis' || mode === 'raw') {
    const { analyzeGroundedCase } = require('../../lib/enforcement-grounded-ai');
    const started = Date.now();
    // 'raw' also returns the model's unvalidated text for THIS synthetic case only,
    // so an operator can see which fields the validator dropped and why.
    const result = await analyzeGroundedCase({
      schemaVersion: '1', statusOfStay: 'D-2', violationCode: 'STATUS_OUTSIDE_ACTIVITY_ART20',
      durationDays: 18, authorizationObtained: false, priorViolations: 0,
      assessmentDate: new Date().toISOString().slice(0, 10),
    }, { debug: mode === 'raw' });
    const prediction = result.prediction || {};
    return response.status(200).json({
      ...base,
      status: 'analysis',
      elapsedMs: Date.now() - started,
      baselineStatus: result.legalBaseline?.status || null,
      predictionStatus: prediction.status || null,
      modelId: prediction.modelId || null,
      failureCategory: prediction.failureCategory || null,
      hasMonetaryRange: Boolean(prediction.monetaryPrediction?.predictedLikelyRange),
      primaryDisposition: prediction.primaryDisposition?.type || null,
      stayImpactCount: (prediction.stayImpact || []).length,
      moneyRationaleCount: (prediction.monetaryPrediction?.rationale || []).length,
      validationNotes: prediction.validationNotes || [],
      ...(mode === 'raw' ? { rawModelText: result.debug?.rawModelText || null } : {}),
    });
  }

  // Official precedent search health, per violation query (no case data involved).
  if (mode === 'precedent') {
    const { diagnosePrecedentSearch } = require('../../lib/enforcement-precedent-grounding');
    const started = Date.now();
    const report = await diagnosePrecedentSearch();
    return response.status(200).json({ ...base, status: 'precedent', elapsedMs: Date.now() - started, ...report });
  }

  // Several fixed synthetic cases, one per violation type, run in parallel. Shows how
  // often each result section (money, disposition, stay impact) survives validation.
  if (mode === 'matrix') {
    const { analyzeGroundedCase } = require('../../lib/enforcement-grounded-ai');
    const today = new Date().toISOString().slice(0, 10);
    const cases = [
      { id: 'D2_ART20_18D_FIRST', statusOfStay: 'D-2', violationCode: 'STATUS_OUTSIDE_ACTIVITY_ART20', durationDays: 18, authorizationObtained: false, priorViolations: 0 },
      { id: 'E74_ART21_63D', statusOfStay: 'E-7-4', violationCode: 'UNAUTHORIZED_WORKPLACE_CHANGE_ART21_1', durationDays: 63, authorizationObtained: false, workplaceChangeAuthorized: false },
      { id: 'D10_OVERSTAY_6D_VOLUNTARY', statusOfStay: 'D-10', violationCode: 'OVERSTAY_ART25', durationDays: 6, priorViolations: 0, voluntaryDisclosure: true },
      { id: 'C3_ART18_1_90D_DETECTED', statusOfStay: 'C-3', violationCode: 'UNAUTHORIZED_STAY_OR_WORK_ART18_1', durationDays: 90, authorizationObtained: false, investigationStarted: true },
      { id: 'E9_ART18_2_150D_PRIOR1', statusOfStay: 'E-9', violationCode: 'UNAUTHORIZED_EMPLOYMENT_ART18_2', durationDays: 150, authorizationObtained: false, priorViolations: 1 },
    ];
    const started = Date.now();
    const rows = await Promise.all(cases.map(async ({ id, ...facts }) => {
      try {
        const result = await analyzeGroundedCase({ schemaVersion: '1', assessmentDate: today, ...facts }, { timeoutMs: 22000, debug: true });
        const prediction = result.prediction || {};
        return {
          id,
          baselineStatus: result.legalBaseline?.status || null,
          allowedDispositions: result.legalBaseline?.legallyAvailableDispositions || [],
          predictionStatus: prediction.status || null,
          failureCategory: prediction.failureCategory || null,
          modelId: prediction.modelId || null,
          primaryDisposition: prediction.primaryDisposition ? `${prediction.primaryDisposition.type}:${prediction.primaryDisposition.likelihood}` : null,
          alternatives: (prediction.alternativeDispositions || []).length,
          hasMoney: Boolean(prediction.monetaryPrediction),
          stayImpact: (prediction.stayImpact || []).length,
          validationNotes: prediction.validationNotes || [],
          lawGrounding: result.lawGrounding?.status || null,
          precedentStatus: result.precedentGrounding?.status || null,
          precedentsFound: result.precedentGrounding?.retrievedCases ?? null,
          precedentLimitations: (result.precedentGrounding?.limitations || []).slice(0, 2),
          confidence: prediction.confidence?.level || null,
          ...(!prediction.primaryDisposition && result.debug?.rawModelText ? { rawHead: result.debug.rawModelText.slice(0, 240) } : {}),
        };
      } catch (error) {
        return { id, error: String(error?.message || error).slice(0, 120) };
      }
    }));
    return response.status(200).json({ ...base, status: 'matrix', elapsedMs: Date.now() - started, rows });
  }

  if (mode !== '1') return response.status(200).json({ ...base, status: 'configured' });

  const { classifyProviderError } = require('../../lib/enforcement-grounded-ai');
  const redact = (value) => String(value || '').split(key).join('[redacted]').replace(/gsk_[A-Za-z0-9]+/g, '[redacted]').slice(0, 300);

  // Which chat models this key can actually use, so a decommissioned default is visible.
  let available = null;
  try {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 8000);
    const list = await fetch('https://api.groq.com/openai/v1/models', { headers: { Authorization: `Bearer ${key}` }, signal: controller.signal });
    clearTimeout(timer);
    const body = await list.json();
    available = list.ok ? (body.data || []).map((item) => String(item.id)).filter((id) => !/whisper|tts|guard|distil/i.test(id)).sort() : `http_${list.status}`;
  } catch (error) {
    available = error?.name === 'AbortError' ? 'timeout' : 'network_error';
  }

  const generation = await Promise.all(groqModelCandidates.slice(0, 3).map(async (model) => {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 8000);
    try {
      const probe = await fetch('https://api.groq.com/openai/v1/chat/completions', {
        method: 'POST',
        headers: { Authorization: `Bearer ${key}`, 'Content-Type': 'application/json' },
        // Same shape as the real call: gpt-oss reasons first, so give it room and low effort.
        body: JSON.stringify({
          model,
          messages: [{ role: 'user', content: 'Return this JSON object exactly: {"ok":true}' }],
          max_tokens: 400,
          response_format: { type: 'json_object' },
          ...(/gpt-oss/i.test(model) ? { reasoning_effort: 'low' } : {}),
        }),
        signal: controller.signal,
      });
      let result = {};
      try { result = await probe.json(); } catch {}
      const message = redact(result.error?.message);
      return { model, status: probe.status, reason: probe.ok ? null : classifyProviderError(probe.status, message), message: probe.ok ? null : message };
    } catch (error) {
      return { model, status: null, reason: error?.name === 'AbortError' ? 'timeout' : 'network_error' };
    } finally {
      clearTimeout(timer);
    }
  }));
  return response.status(200).json({ ...base, status: 'ok', available, generation });
};
