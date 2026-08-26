'use strict';

const { analyzeCase } = require('../../lib/enforcement-fallback');

module.exports = async function handler(request, response) {
  if (request.method === 'GET') {
    return response.status(200).json({
      service: 'visable-enforcement-analyze',
      status: 'ok',
      mode: 'deterministic-fallback',
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
    return response.status(200).json(analyzeCase(payload.caseData));
  } catch {
    return response.status(422).json({ detail: 'invalid structured enforcement case' });
  }
};
