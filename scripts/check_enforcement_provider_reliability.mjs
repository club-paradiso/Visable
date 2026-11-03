import assert from 'node:assert/strict';
import { createRequire } from 'node:module';

const require = createRequire(import.meta.url);
const { callOpenRouter, callPredictionProviders, classifyProviderError, publicRuntimeConfig } = require('../lib/enforcement-grounded-ai.js');
const originalFetch = globalThis.fetch;
const names = ['OPENROUTER_API_KEY', 'ENFORCEMENT_OPENROUTER_MODEL', 'ENFORCEMENT_OPENROUTER_MODEL_CANDIDATES', 'GROQ_API_KEY', 'ENFORCEMENT_GROQ_MODELS'];
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

  // ---- Groq first, OpenRouter second -------------------------------------------
  const msgs = [{ role: 'user', content: 'synthetic test only' }];
  const ok = (model) => ({ ok: true, status: 200, json: async () => ({ model, choices: [{ message: { content: '{"ok":true}' } }] }) });
  const fail = (status, message = '') => ({ ok: false, status, json: async () => ({ error: { message } }) });
  process.env.ENFORCEMENT_OPENROUTER_MODEL = 'test/or-model';
  process.env.ENFORCEMENT_OPENROUTER_MODEL_CANDIDATES = 'test/or-model';

  // No Groq key: behaviour is exactly the OpenRouter path, and Groq is never called.
  delete process.env.GROQ_API_KEY;
  let hosts = [];
  globalThis.fetch = async (url, init) => { hosts.push(new URL(url).host); return ok(JSON.parse(init.body).model); };
  let out = await callPredictionProviders(msgs, { budgetMs: 1000 });
  assert.equal(out.ok, true);
  assert.deepEqual(hosts, ['openrouter.ai'], 'without GROQ_API_KEY only OpenRouter is called');
  assert.equal(publicRuntimeConfig().groqConfigured, false);

  // Groq answers: OpenRouter is not called, gpt-oss gets low reasoning, no OpenRouter-only params leak.
  process.env.GROQ_API_KEY = 'synthetic-groq-test-only';
  process.env.ENFORCEMENT_GROQ_MODELS = 'openai/gpt-oss-120b,llama-3.3-70b-versatile';
  hosts = []; const bodies = [];
  globalThis.fetch = async (url, init) => { hosts.push(new URL(url).host); const b = JSON.parse(init.body); bodies.push(b); return ok(b.model); };
  out = await callPredictionProviders(msgs, { budgetMs: 1000 });
  assert.equal(out.ok, true);
  assert.equal(out.model, 'groq/openai/gpt-oss-120b');
  assert.deepEqual(hosts, ['api.groq.com']);
  assert.equal(bodies[0].reasoning_effort, 'low');
  assert.equal(Object.hasOwn(bodies[0], 'reasoning'), false, 'OpenRouter-only reasoning object must not be sent to Groq');
  assert.deepEqual(bodies[0].response_format, { type: 'json_object' });
  assert.deepEqual(publicRuntimeConfig().providerOrder, ['groq', 'openrouter']);
  assert.equal(JSON.stringify(publicRuntimeConfig()).includes('synthetic-groq-test-only'), false, 'runtime config must never expose the key');

  // Every Groq model rate-limited: OpenRouter answers instead.
  process.env.ENFORCEMENT_GROQ_MODELS = 'groq/limited-a,groq/limited-b';
  hosts = [];
  globalThis.fetch = async (url, init) => {
    hosts.push(new URL(url).host);
    return new URL(url).host === 'api.groq.com' ? fail(429, 'Rate limit reached') : ok(JSON.parse(init.body).model);
  };
  out = await callPredictionProviders(msgs, { budgetMs: 1000 });
  assert.equal(out.ok, true);
  assert.equal(out.model, 'test/or-model');
  assert.deepEqual(hosts, ['api.groq.com', 'api.groq.com', 'openrouter.ai']);

  // Groq only, and it fails: report Groq's real reason, not "openrouter not configured".
  delete process.env.OPENROUTER_API_KEY;
  process.env.ENFORCEMENT_GROQ_MODELS = 'groq/down-a';
  globalThis.fetch = async () => fail(503, 'over capacity');
  out = await callPredictionProviders(msgs, { budgetMs: 1000 });
  assert.equal(out.ok, false);
  assert.equal(out.error, 'http_503');

  // Bad Groq key: stop trying Groq models at once and fall through to OpenRouter.
  process.env.OPENROUTER_API_KEY = 'synthetic-test-only';
  process.env.ENFORCEMENT_GROQ_MODELS = 'groq/auth-a,groq/auth-b';
  hosts = [];
  globalThis.fetch = async (url, init) => {
    hosts.push(new URL(url).host);
    return new URL(url).host === 'api.groq.com' ? fail(401, 'Invalid API Key') : ok(JSON.parse(init.body).model);
  };
  out = await callPredictionProviders(msgs, { budgetMs: 1000 });
  assert.equal(out.ok, true);
  assert.deepEqual(hosts, ['api.groq.com', 'openrouter.ai'], 'a 401 must not be retried on the next Groq model');

  console.log('enforcement Groq-first provider checks passed');
} finally {
  globalThis.fetch = originalFetch;
  for (const name of names) {
    if (saved[name] === undefined) delete process.env[name];
    else process.env[name] = saved[name];
  }
}
