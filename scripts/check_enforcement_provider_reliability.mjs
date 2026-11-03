import assert from 'node:assert/strict';
import { createRequire } from 'node:module';

const require = createRequire(import.meta.url);
const { callOpenRouter, classifyProviderError } = require('../lib/enforcement-grounded-ai.js');
const originalFetch = globalThis.fetch;
const names = ['OPENROUTER_API_KEY', 'ENFORCEMENT_OPENROUTER_MODEL', 'ENFORCEMENT_OPENROUTER_MODEL_CANDIDATES'];
const saved = Object.fromEntries(names.map((name) => [name, process.env[name]]));

try {
  process.env.OPENROUTER_API_KEY = 'synthetic-test-only';
  process.env.ENFORCEMENT_OPENROUTER_MODEL = 'test/mock-one:free';
  process.env.ENFORCEMENT_OPENROUTER_MODEL_CANDIDATES = 'test/mock-one:free,test/mock-two:free';
  let calls = 0;
  globalThis.fetch = async () => {
    calls++;
    return { ok: false, status: 429, json: async () => ({
      error: { message: 'free-models-per-min rate limit exceeded' },
    }) };
  };

  assert.equal(classifyProviderError(429, 'free-models-per-min rate limit exceeded'), 'provider_rate_limit');
  const first = await callOpenRouter([{ role: 'user', content: 'synthetic test only' }], { budgetMs: 1000 });
  assert.equal(first.ok, false);
  assert.equal(first.error, 'provider_rate_limit');
  assert.equal(first.retryable, true);
  assert.equal(calls, 1, 'shared free-tier quota must stop further free candidates');

  const second = await callOpenRouter([{ role: 'user', content: 'synthetic test only' }], { budgetMs: 1000 });
  assert.equal(second.ok, false);
  assert.equal(second.error, 'provider_rate_limit');
  assert.equal(calls, 1, 'warm-instance cooldown must avoid another upstream request');

  // A removed model route (HTTP 404) must not be retried on every request; the next
  // candidate must answer instead. Production saw this on 2026-11-02.
  process.env.ENFORCEMENT_OPENROUTER_MODEL = 'test/removed-model';
  process.env.ENFORCEMENT_OPENROUTER_MODEL_CANDIDATES = 'test/removed-model,test/working-model';
  const seen = [];
  globalThis.fetch = async (_url, init) => {
    const { model } = JSON.parse(init.body);
    seen.push(model);
    if (model === 'test/removed-model') {
      return { ok: false, status: 404, json: async () => ({ error: { message: 'No endpoints found for test/removed-model' } }) };
    }
    return { ok: true, status: 200, json: async () => ({ model, choices: [{ message: { content: '{"ok":true}' } }] }) };
  };
  const recovered = await callOpenRouter([{ role: 'user', content: 'synthetic test only' }], { budgetMs: 1000 });
  assert.equal(recovered.ok, true);
  assert.equal(recovered.model, 'test/working-model');
  assert.deepEqual(seen, ['test/removed-model', 'test/working-model']);
  const again = await callOpenRouter([{ role: 'user', content: 'synthetic test only' }], { budgetMs: 1000 });
  assert.equal(again.ok, true);
  assert.deepEqual(seen.slice(2), ['test/working-model'], 'a 404 model must be skipped on the next request');

  console.log('enforcement provider rate-limit and removed-model checks passed');
} finally {
  globalThis.fetch = originalFetch;
  for (const name of names) {
    if (saved[name] === undefined) delete process.env[name];
    else process.env[name] = saved[name];
  }
}
