'use strict';

// Local-practice report intake (honest by design).
//
// Visable has no datastore for user reports. This function validates a report
// against data/schemas/local_practice_report.schema.json (shape + privacy
// guard) and, when an operator has configured LOCAL_PRACTICE_REPORTS_WEBHOOK_URL,
// forwards it there with moderation state SUBMITTED. Without that configuration
// it returns 503 NOT_CONFIGURED so the client can tell the user the truth
// instead of pretending the report was received. Reports never change guidance;
// moderation happens outside this function.
const PROCEDURES = new Set(['extension', 'status_change', 'registration', 'card_reissue', 'residence_report', 'registration_info_report', 'reentry', 'part_time_work', 'activities_outside_status', 'workplace_change', 'workplace_report', 'status_grant', 'other']);
const FORBIDDEN = [/\b[A-Z]{1,2}\d{7,8}\b/, /\b\d{6}-?[1-8]\d{6}\b/, /\b\d{4}-?\d{4}-?\d{4}\b/];

function text(v, max) { return typeof v === 'string' ? v.replace(/\s+/g, ' ').trim().slice(0, max) : ''; }
function list(v, n, max) { return Array.isArray(v) ? v.slice(0, n).map((x) => text(x, max)).filter(Boolean) : []; }

function validateReport(input) {
  const errors = [];
  if (!input || typeof input !== 'object') return { ok: false, errors: ['body'] };
  const r = {
    schema_version: 1,
    office: text(input.office, 80),
    visit_month: text(input.visit_month, 7),
    procedure: text(input.procedure, 40),
    status: /^[A-H]-\d{1,2}(-[0-9A-Z]{1,6})?$/.test(String(input.status || '')) ? input.status : null,
    status_unknown: Boolean(input.status_unknown),
    outcome: {
      document_expected_not_requested: list(input.outcome && input.outcome.document_expected_not_requested, 12, 120),
      document_requested_not_expected: list(input.outcome && input.outcome.document_requested_not_expected, 12, 120),
      fee_difference: text(input.outcome && input.outcome.fee_difference, 300) || null,
      process_difference: text(input.outcome && input.outcome.process_difference, 300) || null,
    },
    notes: text(input.notes, 800) || null,
    evidence_available: Boolean(input.evidence_available),
    language: text(input.language, 8) || 'ko',
    consent: input.consent === true,
    client_submitted_at: text(input.client_submitted_at, 40) || new Date().toISOString(),
  };
  if (r.office.length < 2) errors.push('office');
  if (!/^20[2-3][0-9]-(0[1-9]|1[0-2])$/.test(r.visit_month)) errors.push('visit_month');
  if (!PROCEDURES.has(r.procedure)) errors.push('procedure');
  if (!r.consent) errors.push('consent');
  const hasOutcome = r.outcome.document_expected_not_requested.length || r.outcome.document_requested_not_expected.length || r.outcome.fee_difference || r.outcome.process_difference || r.notes;
  if (!hasOutcome) errors.push('outcome');
  const free = [r.notes, r.outcome.fee_difference, r.outcome.process_difference, ...r.outcome.document_expected_not_requested, ...r.outcome.document_requested_not_expected].filter(Boolean).join('\n');
  if (FORBIDDEN.some((re) => re.test(free))) errors.push('identifier_pattern');
  return { ok: !errors.length, errors, report: r };
}

module.exports = async function handler(request, response) {
  response.setHeader('Cache-Control', 'no-store');
  if (request.method === 'GET') {
    const configured = Boolean(String(process.env.LOCAL_PRACTICE_REPORTS_WEBHOOK_URL || '').trim());
    return response.status(200).json({ service: 'visable-local-practice-report', status: configured ? 'ok' : 'NOT_CONFIGURED', persistence: configured ? 'webhook' : 'none' });
  }
  if (request.method !== 'POST') {
    response.setHeader('Allow', 'GET, POST');
    return response.status(405).json({ ok: false, status: 'METHOD_NOT_ALLOWED' });
  }
  let payload = request.body || {};
  if (typeof payload === 'string') {
    try { payload = JSON.parse(payload); } catch { return response.status(400).json({ ok: false, status: 'INVALID_JSON' }); }
  }
  const v = validateReport(payload);
  if (!v.ok) return response.status(422).json({ ok: false, status: 'REJECTED', errors: v.errors });
  const webhook = String(process.env.LOCAL_PRACTICE_REPORTS_WEBHOOK_URL || '').trim();
  if (!webhook) return response.status(503).json({ ok: false, status: 'NOT_CONFIGURED' });
  try {
    const res = await fetch(webhook, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ kind: 'visable.local_practice_report', moderation: 'SUBMITTED', received_at: new Date().toISOString(), report: v.report }) });
    if (!res.ok) return response.status(502).json({ ok: false, status: 'UPSTREAM_FAILED' });
    return response.status(200).json({ ok: true, status: 'SUBMITTED', moderation: 'SUBMITTED' });
  } catch (error) {
    console.error('Local-practice report forward failed', { name: error && error.name });
    return response.status(502).json({ ok: false, status: 'UPSTREAM_FAILED' });
  }
};
module.exports.validateReport = validateReport;
