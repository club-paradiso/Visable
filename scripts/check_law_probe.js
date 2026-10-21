'use strict';

const assert = require('node:assert/strict');
const probe = require('../api/enforcement/law-probe');

async function run(payload, responseText) {
  const calls = [];
  global.fetch = async (url) => {
    calls.push(url);
    return { ok: true, text: async () => responseText === undefined ? JSON.stringify(payload) : responseText };
  };
  const headers = {};
  const response = {
    status(code) { this.statusCode = code; return this; },
    json(data) { this.body = data; return this; },
    setHeader(key, value) { headers[key.toLowerCase()] = value; },
  };
  await probe({ method: 'GET' }, response);
  assert.equal(response.statusCode, 200);
  assert.equal(calls.length, 1);
  assert.equal(headers['cache-control'], 'no-store');
  assert.equal(response.body.credentialSource, 'LAW_API_OC');
  assert.ok(!JSON.stringify(response.body).includes('probe-secret-value'));
  return response.body;
}

async function main() {
  const originalFetch = global.fetch;
  const originalOC = process.env.LAW_API_OC;
  const originalKey = process.env.LAW_API_KEY;
  const originalAlias = process.env.LAW_OC;
  const originalOpenLawId = process.env.OPEN_LAW_ID;
  try {
    process.env.LAW_API_OC = 'probe-secret-value';
    delete process.env.LAW_OC;
    delete process.env.OPEN_LAW_ID;
    delete process.env.LAW_API_KEY;
    const valid = await run({ LawSearch: { totalCnt: '1', law: [{ '법령명한글': '출입국관리법', '법령ID': '001707' }] } });
    assert.equal(valid.status, 'ok');
    assert.equal(valid.diagnostics.totalCount, 1);
    const highlighted = await run({ LawSearch: { totalCnt: '1', law: { '법령명한글': '<b>출입국</b>관리법', '법령ID': '001707' } } });
    assert.equal(highlighted.status, 'ok');
    const error = await run({ errorMessage: 'API 인증값이 등록되지 않았습니다' });
    assert.equal(error.status, 'upstream_authorization_or_registration_error');
    assert.equal(error.diagnostics.responseKind, 'upstream_application_error');
    const empty = await run({ LawSearch: { totalCnt: '0', law: [] } });
    assert.equal(empty.status, 'no_results');
    const mismatch = await run({ LawSearch: { totalCnt: '1', law: [{ '법령명한글': '출입국관리법 시행령' }] } });
    assert.equal(mismatch.status, 'no_exact_law_match');
    const unknown = await run({ random: 'shape' });
    assert.equal(unknown.status, 'unexpected_json_shape');
    console.log('Law API probe classification and credential redaction checks passed');
  } finally {
    global.fetch = originalFetch;
    if (originalOC === undefined) delete process.env.LAW_API_OC; else process.env.LAW_API_OC = originalOC;
    if (originalKey === undefined) delete process.env.LAW_API_KEY; else process.env.LAW_API_KEY = originalKey;
    if (originalAlias === undefined) delete process.env.LAW_OC; else process.env.LAW_OC = originalAlias;
    if (originalOpenLawId === undefined) delete process.env.OPEN_LAW_ID; else process.env.OPEN_LAW_ID = originalOpenLawId;
  }
}
main().catch((error) => { console.error(error); process.exitCode = 1; });
