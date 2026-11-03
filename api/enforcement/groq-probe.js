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
  if (!(request.query && request.query.diagnose === '1')) return response.status(200).json({ ...base, status: 'configured' });

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
        body: JSON.stringify({ model, messages: [{ role: 'user', content: 'Return this JSON object exactly: {"ok":true}' }], max_tokens: 64, response_format: { type: 'json_object' } }),
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
