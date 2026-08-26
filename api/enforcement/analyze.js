'use strict';

// Keep Enforcement on currently active default fallbacks even if the shared
// runtime's historical defaults still contain deprecated free endpoints.
// A deployment-specific ENFORCEMENT_OPENROUTER_MODEL_CANDIDATES value always
// wins, so operators can opt into premium or newer models without a code edit.
if (!String(process.env.ENFORCEMENT_OPENROUTER_MODEL_CANDIDATES || '').trim()) {
  process.env.ENFORCEMENT_OPENROUTER_MODEL_CANDIDATES = [
    'openai/gpt-oss-120b:free',
    'google/gemma-4-31b-it:free',
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
