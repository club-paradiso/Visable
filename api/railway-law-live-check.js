'use strict';

const RAILWAY_ORIGIN = 'https://web-production-14f9a.up.railway.app';

async function readJson(path) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 15000);
  try {
    const response = await fetch(`${RAILWAY_ORIGIN}${path}`, {
      headers: {
        Accept: 'application/json',
        'User-Agent': 'Visable-Temporary-Railway-Law-Check/1',
      },
      signal: controller.signal,
    });
    const payload = await response.json().catch(() => ({}));
    return { status: response.status, payload };
  } finally {
    clearTimeout(timer);
  }
}

module.exports = async function handler(req, res) {
  if (req.method !== 'GET') {
    res.setHeader('Allow', 'GET');
    return res.status(405).json({ ok: false, error: 'method_not_allowed' });
  }

  try {
    const [health, law] = await Promise.all([
      readJson('/health'),
      readJson(`/api/legal/laws/search?q=${encodeURIComponent('출입국관리법')}`),
    ]);

    const results = Array.isArray(law.payload && law.payload.results) ? law.payload.results : [];
    const first = results[0] || {};
    return res.status(200).json({
      service: 'temporary-railway-law-live-check',
      railwayHealthHttpStatus: health.status,
      railwayHealthOk: health.status === 200 && health.payload && health.payload.status === 'ok',
      openrouterConfigured: Boolean(health.payload && health.payload.providers && health.payload.providers.openrouter),
      lawApiConfigured: Boolean(health.payload && health.payload.law_api && health.payload.law_api.law_api_configured),
      lawGroundingActive: Boolean(health.payload && health.payload.law_grounding_active),
      lawSearchHttpStatus: law.status,
      lawSearchOk: Boolean(law.payload && law.payload.ok === true),
      lawSearchCount: Number((law.payload && law.payload.count) || 0),
      firstLawName: String(first.lawName || first.law_name || first.title || ''),
      verified: Boolean(
        health.status === 200 &&
        health.payload && health.payload.status === 'ok' &&
        law.status === 200 &&
        law.payload && law.payload.ok === true &&
        Number(law.payload.count || 0) > 0
      ),
    });
  } catch (error) {
    return res.status(502).json({
      service: 'temporary-railway-law-live-check',
      verified: false,
      error: error && error.name ? error.name : 'upstream_unavailable',
    });
  }
};
