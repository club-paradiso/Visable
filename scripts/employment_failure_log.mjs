/*
 * employment_failure_log.mjs
 * ----------------------------------------------------------------------------
 * Lightweight, dependency-free logging CONTRACT for no-result / low-confidence
 * employment-analyzer queries. Used to find coverage gaps and aliases to add.
 *
 * Paradiso is a static site, so there is no server to persist to by default.
 * This module therefore:
 *   - defines the record shape (one source of truth for app + backend),
 *   - provides createFailureLogger() that buffers in memory and, in a browser,
 *     mirrors to localStorage (dev-safe, bounded), and
 *   - documents the single seam where a real backend can later persist records
 *     (POST them as JSONL to an endpoint / table) without changing callers.
 *
 * A record is appended on a search when noOfficialCodeFound is true OR the best
 * candidate is low confidence OR the user selected "none of these".
 * ----------------------------------------------------------------------------
 */

export const FAILURE_LOG_SCHEMA = '2026-06-employment-failure-log';

/** Build a log record from an analyzer result (+ optional user selection). */
export function buildFailureRecord(result, opts = {}) {
  const occ = result.occupationCandidates || [];
  const ind = result.industryCandidates || [];
  const best = [...occ, ...ind].sort((a, b) => (b.score || 0) - (a.score || 0))[0] || null;
  const lowConfidence = !!best && best.confidence === 'low';
  const noResult = !!result.noOfficialCodeFound;
  return {
    schema: FAILURE_LOG_SCHEMA,
    query: result.input != null ? result.input : (opts.query || ''),
    normalizedQuery: result.normalizedInput || '',
    detectedLanguage: result.detectedLanguage || (result.extracted && result.extracted.language) || 'unknown',
    mode: result.mode || 'unknown',
    returnedOccupation: occ.map((c) => ({ code: c.code, name: c.officialName, confidence: c.confidence })),
    returnedIndustry: ind.map((c) => ({ code: c.code, name: c.officialName, confidence: c.confidence })),
    userSelected: opts.userSelected || null,        // {track, code, name} | 'none' | null
    noResultFlag: noResult,
    lowConfidenceFlag: lowConfidence,
    clarificationFlag: !!result.clarificationRequired,
    parsedSignals: result.parsedSignals
      ? {
          places: (result.parsedSignals.places || []).map((p) => p.label),
          objects: (result.parsedSignals.objects || []).map((o) => o.label),
          actions: (result.parsedSignals.actions || []).map((a) => a.label)
        }
      : null,
    timestamp: opts.timestamp || new Date().toISOString()
  };
}

/** Should this result be logged at all? (only failures / low-confidence) */
export function shouldLog(result, opts = {}) {
  if (opts.userSelected === 'none') return true;
  if (result.noOfficialCodeFound) return true;
  const all = [...(result.occupationCandidates || []), ...(result.industryCandidates || [])];
  return all.length === 0 || all.every((c) => c.confidence === 'low');
}

/**
 * createFailureLogger({ persist }) → { log(result, opts), all(), clear() }.
 *  - In a browser, records mirror to localStorage under 'paradiso.empFailLog'
 *    (bounded to `max`), so a developer can inspect real misses.
 *  - `persist` is the backend seam: if provided, it is called with each record
 *    (e.g. to POST to /api/employment-log). Errors are swallowed (never block UX).
 */
export function createFailureLogger(options = {}) {
  const max = options.max || 500;
  const key = options.storageKey || 'paradiso.empFailLog';
  const hasLS = typeof localStorage !== 'undefined';
  let buf = [];
  if (hasLS) { try { buf = JSON.parse(localStorage.getItem(key) || '[]'); } catch { buf = []; } }

  function persistAll() {
    if (!hasLS) return;
    try { localStorage.setItem(key, JSON.stringify(buf.slice(-max))); } catch { /* quota: ignore */ }
  }
  return {
    log(result, opts = {}) {
      if (!shouldLog(result, opts)) return null;
      const rec = buildFailureRecord(result, opts);
      buf.push(rec);
      if (buf.length > max) buf = buf.slice(-max);
      persistAll();
      if (typeof options.persist === 'function') { try { options.persist(rec); } catch { /* never block */ } }
      return rec;
    },
    all() { return buf.slice(); },
    clear() { buf = []; persistAll(); }
  };
}

export default { FAILURE_LOG_SCHEMA, buildFailureRecord, shouldLog, createFailureLogger };

// Browser bridge so the inline UI can attach a logger without a build step.
if (typeof window !== 'undefined') {
  window.EmploymentFailureLog = { FAILURE_LOG_SCHEMA, buildFailureRecord, shouldLog, createFailureLogger };
}
