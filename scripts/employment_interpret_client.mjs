/** Optional, bounded sentence interpretation. Local classification never waits
 * indefinitely and remains available when the provider is missing or busy. */
export async function interpretEmploymentInput({ text, lang = 'ko', apiBase = '', fetchImpl = fetch, timeoutMs = 5000 }) {
  if (!apiBase) return null;
  const controller = new AbortController();
  let timer;
  try {
    const request = (async () => {
      const response = await fetchImpl(`${apiBase}/api/employment/interpret`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text, lang }), signal: controller.signal,
      });
      if (!response.ok) return null;
      const body = await response.json();
      if (body.status !== 'ok' || !body.extraction || typeof body.extraction !== 'object') return null;
      const facts = {};
      for (const key of ['role', 'workplace', 'employerMainBusiness', 'clarificationQuestion']) {
        facts[key] = typeof body.extraction[key] === 'string' ? body.extraction[key].slice(0, 240) : '';
      }
      for (const key of ['tasks', 'actions', 'objects', 'tools']) {
        facts[key] = Array.isArray(body.extraction[key]) ? body.extraction[key].filter((s) => typeof s === 'string').slice(0, 12).map((s) => s.slice(0, 160)) : [];
      }
      facts.needsClarification = body.extraction.needsClarification === true;
      return facts;
    })();
    return await Promise.race([request, new Promise((resolve) => {
      timer = setTimeout(() => { controller.abort(); resolve(null); }, timeoutMs);
    })]);
  } catch (_) { return null; }
  finally { clearTimeout(timer); }
}
