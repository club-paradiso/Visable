'use strict';

// Waymaker Quick Answer — optional AI wording for an already-validated structured
// answer. GET reports the runtime state (no secrets). POST returns
// { ok: true, summary } only when the rewritten sentence passes the shared
// validator; every other outcome is { ok: false, status } and the client keeps
// its deterministic sentence. Nothing is stored.
const { enhanceQuickAnswer, publicRuntimeConfig } = require('../../lib/waymaker-quick-answer-ai');

module.exports = async function handler(request, response) {
  response.setHeader('Cache-Control', 'no-store');
  if (request.method === 'GET') {
    const runtime = publicRuntimeConfig();
    return response.status(200).json({ service: 'visable-waymaker-quick-answer', status: runtime.openrouterConfigured ? 'ok' : 'NOT_CONFIGURED', mode: runtime.openrouterConfigured ? 'wording-enhancement' : 'deterministic-only', runtime });
  }
  if (request.method !== 'POST') {
    response.setHeader('Allow', 'GET, POST');
    return response.status(405).json({ ok: false, status: 'METHOD_NOT_ALLOWED' });
  }
  let payload = request.body || {};
  if (typeof payload === 'string') {
    try { payload = JSON.parse(payload); } catch { return response.status(400).json({ ok: false, status: 'INVALID_JSON' }); }
  }
  try {
    const result = await enhanceQuickAnswer(payload);
    if (result.status === 'NOT_CONFIGURED') return response.status(503).json({ ok: false, status: 'NOT_CONFIGURED' });
    if (result.status === 'REJECTED_INPUT') return response.status(422).json({ ok: false, status: 'REJECTED_INPUT' });
    return response.status(200).json(result);
  } catch (error) {
    console.error('Quick Answer enhancement failed', { name: error && error.name, message: error && error.message });
    return response.status(200).json({ ok: false, status: 'PROVIDER_FAILED' });
  }
};
