'use strict';

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
