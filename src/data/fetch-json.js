// @ts-check
/**
 * Data loading layer (Phase 3). Behaviour mirrors the inline helpers it replaces:
 *  - every request uses `cache: 'no-store'` unless told otherwise (the inline code did);
 *  - `fetchJson` throws on a non-2xx response with the same message shape the caller used;
 *  - `fetchOptionalJson` never throws: it warns and resolves to null;
 *  - `fetchJsonWithTimeout` aborts the request (and a stalled body) after `timeoutMs`.
 * Nothing here interprets legal content; it only moves bytes.
 *
 * Plain ES module + JSDoc on purpose (ADR-010): the source tree is still served without a
 * build by the legacy e2e jobs, so modules must run natively in the browser.
 */

/**
 * @typedef {Object} FetchJsonOptions
 * @property {RequestCache} [cache] Passed straight to fetch(); defaults to 'no-store' like the legacy inline code.
 * @property {string} [errorMessage] Message of the Error thrown on a non-2xx status. Default: `HTTP <status>`.
 * @property {AbortSignal} [signal]
 * @property {Record<string, string>} [headers]
 */

/**
 * @template T
 * @param {string} url
 * @param {FetchJsonOptions} [options]
 * @returns {Promise<T>}
 */
export async function fetchJson(url, options = {}) {
  const res = await fetch(url, { cache: options.cache ?? 'no-store', signal: options.signal });
  if (!res.ok) throw new Error(options.errorMessage ?? `HTTP ${res.status}`);
  return /** @type {T} */ (await res.json());
}

/**
 * Optional data: a missing or broken file is logged and yields null (legacy `fetchOptionalJson`).
 * @template T
 * @param {string} path
 * @returns {Promise<T | null>}
 */
export async function fetchOptionalJson(path) {
  try {
    return await fetchJson(path);
  } catch (e) {
    console.warn(`Optional Visable data not loaded: ${path}`, e);
    return null;
  }
}

/**
 * Fetch JSON with a hard ceiling. The timer also covers a stalled response body, exactly
 * like the legacy visa-data loader (a cold backend must never keep search locked).
 * @template T
 * @param {string} url
 * @param {number} timeoutMs
 * @param {FetchJsonOptions} [options]
 * @returns {Promise<T>}
 */
export async function fetchJsonWithTimeout(url, timeoutMs, options = {}) {
  const ctl = new AbortController();
  const timer = setTimeout(() => ctl.abort(), timeoutMs);
  try {
    return await fetchJson(url, { ...options, signal: ctl.signal });
  } finally {
    clearTimeout(timer);
  }
}

/**
 * POST a JSON body and parse a JSON response; throws on a non-2xx status.
 * @template T
 * @param {string} url
 * @param {unknown} body
 * @param {FetchJsonOptions} [options]
 * @returns {Promise<T>}
 */
export async function postJson(url, body, options = {}) {
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
    body: JSON.stringify(body),
    cache: options.cache ?? 'no-store',
    signal: options.signal
  });
  if (!res.ok) throw new Error(options.errorMessage ?? `HTTP ${res.status}`);
  return /** @type {T} */ (await res.json());
}
