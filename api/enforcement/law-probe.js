'use strict';

const LAW_HOST = 'https://www.law.go.kr';

function exactLawFound(data, lawName) {
  const wanted = String(lawName || '').replace(/[\s·]/g, '');
  const stack = [data];
  while (stack.length) {
    const value = stack.pop();
    if (Array.isArray(value)) {
      stack.push(...value);
      continue;
    }
    if (!value || typeof value !== 'object') continue;
    const name = value['법령명한글'] || value['법령명'] || value['법령명_한글'] || value.lawName;
    if (name && String(name).replace(/[\s·]/g, '') === wanted) return true;
    stack.push(...Object.values(value));
  }
  return false;
}

module.exports = async function handler(request, response) {
  if (request.method !== 'GET') {
    response.setHeader('Allow', 'GET');
    return response.status(405).json({ detail: 'method not allowed' });
  }

  const preferred = String(process.env.LAW_API_OC || '').trim();
  const legacy = String(process.env.LAW_API_KEY || '').trim();
  const credential = preferred || legacy;
  const credentialSource = preferred ? 'LAW_API_OC' : (legacy ? 'LAW_API_KEY' : null);
  const mode = String(process.env.LAW_GROUNDING_MODE || 'enabled').trim().toLowerCase();

  if (!credential) {
    return response.status(200).json({
      service: 'visable-enforcement-law-probe',
      configured: false,
      credentialSource: null,
      mode,
      reachable: false,
      exactLawFound: false,
      status: 'not_configured',
    });
  }

  const params = new URLSearchParams({
    OC: credential,
    target: 'law',
    type: 'JSON',
    query: '출입국관리법',
    display: '5',
  });
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 8000);

  try {
    const upstream = await fetch(`${LAW_HOST}/DRF/lawSearch.do?${params.toString()}`, {
      method: 'GET',
      headers: { Accept: 'application/json' },
      signal: controller.signal,
    });
    if (!upstream.ok) {
      return response.status(200).json({
        service: 'visable-enforcement-law-probe',
        configured: true,
        credentialSource,
        mode,
        reachable: true,
        exactLawFound: false,
        status: `upstream_http_${upstream.status}`,
      });
    }
    const text = await upstream.text();
    let data;
    try { data = JSON.parse(text); }
    catch {
      return response.status(200).json({
        service: 'visable-enforcement-law-probe',
        configured: true,
        credentialSource,
        mode,
        reachable: true,
        exactLawFound: false,
        status: 'unexpected_non_json_response',
      });
    }
    const found = exactLawFound(data, '출입국관리법');
    return response.status(200).json({
      service: 'visable-enforcement-law-probe',
      configured: true,
      credentialSource,
      mode,
      reachable: true,
      exactLawFound: found,
      status: found ? 'ok' : 'no_exact_law_match',
    });
  } catch (error) {
    return response.status(200).json({
      service: 'visable-enforcement-law-probe',
      configured: true,
      credentialSource,
      mode,
      reachable: false,
      exactLawFound: false,
      status: error && error.name === 'AbortError' ? 'timeout' : 'network_error',
    });
  } finally {
    clearTimeout(timer);
  }
};
