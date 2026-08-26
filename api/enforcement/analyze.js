'use strict';

const { analyzeGroundedCase, publicRuntimeConfig } = require('../../lib/enforcement-grounded-ai');
const { retrieveOfficialPrecedents } = require('../../lib/enforcement-precedent-grounding');

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
    const analysis = await analyzeGroundedCase(payload.caseData);
    const precedent = await retrieveOfficialPrecedents(payload.caseData || {}, analysis.legalBaseline);
    const prediction = analysis.prediction || {};
    const knownEvidence = new Set((prediction.evidence || []).map((item) => item && item.id).filter(Boolean));
    const appendedEvidence = [...(prediction.evidence || [])];
    for (const item of precedent.evidence || []) {
      if (item && item.id && !knownEvidence.has(item.id)) {
        knownEvidence.add(item.id);
        appendedEvidence.push(item);
      }
    }
    analysis.prediction = {
      ...prediction,
      evidence: appendedEvidence,
      similarCases: precedent.similarCases || [],
      limitations: [...new Set([...(prediction.limitations || []), ...(precedent.limitations || [])])],
    };
    analysis.precedentGrounding = {
      status: precedent.status,
      retrievedCases: (precedent.similarCases || []).length,
    };
    return response.status(200).json(analysis);
  } catch (error) {
    console.error('Enforcement analysis rejected', { name: error && error.name, message: error && error.message });
    return response.status(422).json({ detail: 'invalid structured enforcement case' });
  }
};
