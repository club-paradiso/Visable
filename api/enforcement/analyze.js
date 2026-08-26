'use strict';

// Enforcement has a Korean-first output surface. Prefer the current multilingual
// Gemma 4 free endpoint, then fall back to gpt-oss-120b. Deployment-specific
// ENFORCEMENT_OPENROUTER_MODEL / *_CANDIDATES values always win, so operators
// can opt into a premium verifier (for example Gemini 3 Flash) without code edits.
if (!String(process.env.ENFORCEMENT_OPENROUTER_MODEL || '').trim()) {
  process.env.ENFORCEMENT_OPENROUTER_MODEL = 'google/gemma-4-31b-it:free';
}
if (!String(process.env.ENFORCEMENT_OPENROUTER_MODEL_CANDIDATES || '').trim()) {
  process.env.ENFORCEMENT_OPENROUTER_MODEL_CANDIDATES = [
    'google/gemma-4-31b-it:free',
    'openai/gpt-oss-120b:free',
  ].join(',');
}

const { analyzeGroundedCase, publicRuntimeConfig } = require('../../lib/enforcement-grounded-ai');

module.exports = async function handler(request, response) {
  if (request.method === 'GET') {
    const runtime = publicRuntimeConfig();
    return response.status(200).json({
      service: 'visable-enforcement-analyze',
      status: 'ok',
      mode: runtime.openrouterConfigured ? 'grounded-ai-v2' : 'deterministic-fallback',
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
    return response.status(200).json(await analyzeGroundedCase(payload.caseData));
  } catch (error) {
    console.error('Enforcement analysis rejected', { name: error && error.name, message: error && error.message });
    return response.status(422).json({ detail: 'invalid structured enforcement case' });
  }
};
