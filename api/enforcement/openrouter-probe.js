'use strict';

module.exports = async function handler(request, response) {
  if (request.method !== 'GET') {
    response.setHeader('Allow', 'GET');
    return response.status(405).json({ detail: 'method not allowed' });
  }

  const key = String(process.env.OPENROUTER_API_KEY || '').trim();
  if (!key) {
    return response.status(200).json({
      service: 'visable-enforcement-openrouter-probe',
      configured: false,
      reachable: false,
      authorized: false,
      status: 'not_configured',
    });
  }

  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 8000);
  try {
    const upstream = await fetch('https://openrouter.ai/api/v1/key', {
      method: 'GET',
      headers: {
        Authorization: `Bearer ${key}`,
        Accept: 'application/json',
      },
      signal: controller.signal,
    });
    if (!upstream.ok) {
      return response.status(200).json({
        service: 'visable-enforcement-openrouter-probe',
        configured: true,
        reachable: true,
        authorized: false,
        status: `upstream_http_${upstream.status}`,
      });
    }
    await upstream.text();
    let generation = null;
    if (request.query && request.query.diagnose === '1') {
      // Fixed synthetic probe only. Never accepts a user's case, prompt or key.
      const { modelCandidates, classifyProviderError } = require('../../lib/enforcement-grounded-ai');
      const models = modelCandidates().slice(0, 3);
      generation = await Promise.all(models.map(async (model) => {
      try {
      const probe = await fetch('https://openrouter.ai/api/v1/chat/completions', {
        method: 'POST',
        headers: { Authorization: `Bearer ${key}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({ model, messages: [{ role: 'user', content: 'Reply with the word OK.' }], max_tokens: 16 }),
        signal: controller.signal,
      });
      let result = {};
      try { result = await probe.json(); } catch {}
      const message = String(result.error?.metadata?.raw || result.error?.message || result.message || result.detail || '').split(key).join('[redacted]').slice(0, 500)
        .replace(/(?:sk-|Bearer\s+)[A-Za-z0-9_-]+/gi, '[redacted]');
      return { model, status: probe.status, reason: probe.ok ? null : classifyProviderError(probe.status, message) };
      } catch (error) {
        return { model, status: null, reason: error?.name === 'AbortError' ? 'timeout' : 'network_error' };
      }
      }));
    }

    return response.status(200).json({
      service: 'visable-enforcement-openrouter-probe',
      configured: true,
      reachable: true,
      authorized: true,
      status: 'ok',
      ...(generation ? { generation } : {}),
    });
  } catch (error) {
    return response.status(200).json({
      service: 'visable-enforcement-openrouter-probe',
      configured: true,
      reachable: false,
      authorized: false,
      status: error && error.name === 'AbortError' ? 'timeout' : 'network_error',
    });
  } finally {
    clearTimeout(timer);
  }
};
