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
    return response.status(200).json({
      service: 'visable-enforcement-openrouter-probe',
      configured: true,
      reachable: true,
      authorized: true,
      status: 'ok',
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
