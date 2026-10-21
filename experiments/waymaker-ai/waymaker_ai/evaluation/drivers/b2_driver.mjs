// B2 baseline driver: the search page / quick answer JS resolver, one question per line.
//
// Runs under Node as a child of the evaluation runner. Reads JSON lines
// {"id", "question"} on stdin, writes one JSON line per item on stdout.
// Recipe (docs/ai/waymaker-genesis/research-notes/status-classifier.md §9):
// VisableStatusGuidance.interpret(q, bundle) -> route -> nextStep(state, bundle).
// The driver only reports what the resolver returned plus the bundle's own
// kind/parent for every code it mentions; deriving parent vs subcode happens in
// the runner (python), where it is unit-tested.
//
// No network: the scripts are evaluated from local files and the driver never
// imports an HTTP module.
import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { createInterface } from 'node:readline';

const ROOT = process.argv[2];
const bundle = JSON.parse(readFileSync(join(ROOT, 'data/status-guidance-202609.json'), 'utf8'));
bundle.local_practice = JSON.parse(readFileSync(join(ROOT, 'data/local-practice-202609.json'), 'utf8'));
for (const name of ['status-guidance', 'search-router']) {
  // The scripts are browser globals (IIFEs that attach to globalThis).
  new Function(readFileSync(join(ROOT, 'assets/js', name + '.js'), 'utf8'))();
}
const SG = globalThis.VisableStatusGuidance;

function kindOf(code) {
  const rec = code && bundle.codes[code];
  return rec ? { kind: rec.kind || null, parent: rec.parent || null } : null;
}

function codeIndex(codes) {
  const out = {};
  const queue = codes.filter(Boolean);
  while (queue.length) {
    const code = queue.shift();
    if (out[code] !== undefined) continue;
    const info = kindOf(code);
    out[code] = info;
    if (info && info.parent) queue.push(info.parent);
  }
  return out;
}

const rl = createInterface({ input: process.stdin, crlfDelay: Infinity });
let peakHeap = 0;
for await (const line of rl) {
  if (!line.trim()) continue;
  const record = JSON.parse(line);
  const q = record.question;
  const t0 = process.hrtime.bigint();
  try {
    const interp = SG.interpret(q, bundle);
    const route = interp.route || {};
    const state = { interp, answers: {}, procedure: null, status: null, history: [], lang: /[가-힣]/.test(q) ? 'ko' : 'en', query: q };
    const step = SG.nextStep(state, bundle) || {};
    const latency = Number(process.hrtime.bigint() - t0) / 1e6;
    const heap = process.memoryUsage().heapUsed;
    peakHeap = Math.max(peakHeap, heap);
    const codes = (interp.codes || []).map((c) => ({ code: c.code, exact: !!c.exact, role: c.role || null, fromUnknown: c.fromUnknown || null, fromAlias: c.fromAlias || null }));
    const raw = {
      codes,
      unknownCodes: interp.unknownCodes || [],
      transitionFrom: interp.transitionFrom || null,
      procedure: interp.procedure || null,
      procedureCandidates: interp.procedureCandidates || [],
      confidence: interp.confidence || null,
      routeIntent: route.intent || null,
      routeProcedure: route.procedure || null,
      routeStatus: route.status || null,
      routeSubstatus: route.substatus || null,
      stepKind: step.kind || null,
      stepStatus: step.status || null,
      stepProcedure: step.procedure || null,
      target: step.target || null,
      displayCode: step.displayCode || null,
      inherited: !!step.inherited,
      dimension: step.dimension || null,
    };
    const mentioned = [raw.displayCode, raw.transitionFrom, raw.stepStatus, ...codes.map((c) => c.code)];
    if (typeof raw.target === 'string') mentioned.push(raw.target.split('~')[0]);
    process.stdout.write(JSON.stringify({ id: record.id, ok: true, raw, code_index: codeIndex(mentioned), latency_ms: Math.round(latency * 1000) / 1000, js_heap_used_bytes: heap, upstream_calls: 0 }) + '\n');
  } catch (err) {
    process.stdout.write(JSON.stringify({ id: record.id, ok: false, error: String(err && err.message || err).slice(0, 500) }) + '\n');
  }
}
process.stdout.write(JSON.stringify({ _meta: true, node: process.version, js_heap_used_peak_bytes: peakHeap }) + '\n');
