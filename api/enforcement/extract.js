'use strict';

const { extractStructuredCase } = require('../../lib/enforcement-fallback');

module.exports = async function handler(request, response) {
  if (request.method === 'GET') {
    return response.status(200).json({
      service: 'visable-enforcement-extract',
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

  const text = String(payload.text || '').trim();
  if (!text) return response.status(422).json({ detail: 'case text is required' });

  const assessmentDate = payload.assessmentDate || null;
  if (assessmentDate && !/^\d{4}-\d{2}-\d{2}$/.test(String(assessmentDate))) {
    return response.status(422).json({ detail: 'invalid assessmentDate' });
  }

  try {
    const caseData = extractStructuredCase(text, assessmentDate);
    return response.status(200).json({ case: caseData });
  } catch (error) {
    return response.status(422).json({ detail: error.message || 'case extraction failed' });
  }
};
