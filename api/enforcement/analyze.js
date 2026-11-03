'use strict';

// 2026-11-02 production probe (/api/enforcement/openrouter-probe?diagnose=1):
// minimax/minimax-m3.1-flash:free -> HTTP 404 (route removed), gemma-4-31b -> 200,
// gemma-4-26b -> 429. The removed route was first in line, so every analysis spent
// a round-trip on a dead model. Keep explicit operator overrides and strict output
// validation; no paid fallback.
if (!String(process.env.ENFORCEMENT_OPENROUTER_MODEL || '').trim()) {
  process.env.ENFORCEMENT_OPENROUTER_MODEL = 'google/gemma-4-31b-it:free';
}
if (!String(process.env.ENFORCEMENT_OPENROUTER_MODEL_CANDIDATES || '').trim()) {
  process.env.ENFORCEMENT_OPENROUTER_MODEL_CANDIDATES = [
    'google/gemma-4-31b-it:free',
    'google/gemma-4-26b-a4b-it:free',
  ].join(',');
}

const { analyzeGroundedCase, analyzeBaselineCase, publicRuntimeConfig } = require('../../lib/enforcement-grounded-ai');

module.exports = async function handler(request, response) {
  if (request.method === 'GET') {
    const runtime = publicRuntimeConfig();
    return response.status(200).json({
      service: 'visable-enforcement-analyze',
      status: 'ok',
      mode: runtime.openrouterConfigured || runtime.groqConfigured ? 'grounded-ai-v2' : 'deterministic-fallback',
      runtime,
    });
  }

  if (request.method !== 'POST') {
    response.setHeader('Allow', 'GET, POST');
    return response.status(405).json({ detail: 'method not allowed' });
  }

  let payload = request.body || {};
  if (typeof payload === 'string') {
    try { payload = JSON.parse(payload); }
    catch { return response.status(400).json({ detail: 'invalid JSON body' }); }
  }

  try {
    return response.status(200).json(payload.baselineOnly === true ? analyzeBaselineCase(payload.caseData) : await analyzeGroundedCase(payload.caseData));
  } catch (error) {
    console.error('Enforcement analysis rejected', { name: error && error.name, message: error && error.message });
    return response.status(422).json({ detail: 'invalid structured enforcement case' });
  }
};
