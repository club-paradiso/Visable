// @ts-nocheck
/**
 * Legacy shim `DETAIL_CODE_RESOLVER_SHIM_2026_05` (Phase 3, moved verbatim from the inline <script> block in index.html).
 * Its install function used to be registered for DOMContentLoaded while the document was parsed; index.html
 * keeps that registration as a one-liner calling `Visable.shims.installDetailResolver()`, so it still runs in the same
 * order relative to the main bootstrap and the other shims (ADR-009 addendum 4). Everything else is the
 * original IIFE; it reads the inline globals it always read (VISA_DATA, selectedLocale, LANGUAGE_OPTIONS, …) lazily.
 */
let __install;
(function () {
  "use strict";

  const DETAIL_CODE_EXACT = /^[A-Z]-\d{1,2}(?:-[A-Z0-9]+)+$/;

  function norm(value) {
    return String(value || "").trim().toUpperCase();
  }

  function deriveParents(code) {
    const parts = norm(code).split("-");
    const out = [];
    while (parts.length > 2) {
      parts.pop();
      out.push(parts.join("-"));
    }
    return out;
  }

  function compact(value) {
    return norm(value).replace(/-/g, "");
  }

  // Warm a background copy of visa_data.json only as a fallback for the rare
  // case where the in-page dataset (VISA_DATA) is not reachable from this
  // script; the resolver prefers the already-loaded in-page records.
  function warmFallbackRecords() {
    if (window.__paradisoDetailAliasData) return;
    try {
      Visable.data.fetchJson("visa_data.json", { errorMessage: function (status) { return "visa_data.json fetch failed: " + status; } })
        .then(function (data) {
          window.__paradisoDetailAliasData = Array.isArray(data) ? data : [];
        })
        .catch(function (err) {
          console.warn("[Visable] detail-code resolver fallback unavailable:", err);
          window.__paradisoDetailAliasData = [];
        });
    } catch (err) {
      window.__paradisoDetailAliasData = [];
    }
  }

  // The loaded dataset the primary search pipeline itself searches. Preferring
  // it (over a second fetch) keeps the resolver in lock-step with what the user
  // can actually reach, and lets resolution run synchronously.
  function getResolverRecords() {
    try {
      if (typeof VISA_DATA !== "undefined" && Array.isArray(VISA_DATA) && VISA_DATA.length) {
        return VISA_DATA;
      }
    } catch (err) { /* VISA_DATA not in scope — fall through to the fetched copy */ }
    return Array.isArray(window.__paradisoDetailAliasData) ? window.__paradisoDetailAliasData : null;
  }

  // Build the set of dash-less code forms the PRIMARY pipeline already resolves
  // exactly (record codes, subcodes, aliases, subcode aliases and procedure
  // variant status codes — i.e. everything getExactQueryMatchRank ranks > 0),
  // plus a compact→canonical map of valid top-level reroute targets. The
  // resolver must never demote any query the primary pipeline can resolve on
  // its own, so those codes are excluded from rerouting.
  function buildAliasMap(records) {
    const resolvable = new Set();
    const topByCompact = new Map();
    const addResolvable = function (value) {
      const c = compact(value);
      if (c) resolvable.add(c);
    };

    for (const record of records) {
      if (!record || !record.code) continue;
      const code = norm(record.code);
      topByCompact.set(compact(code), code);
      addResolvable(code);

      if (Array.isArray(record.aliases)) for (const a of record.aliases) addResolvable(a);
      if (Array.isArray(record.searchAliases)) for (const a of record.searchAliases) addResolvable(a);

      // Prefer canonical `subcodes`, but also include any legacy compat
      // `subCodes` entries so no exact-search code is dropped during the
      // compatibility phase (the two may diverge until subCodes is removed).
      const subcodes = [
        ...(Array.isArray(record.subcodes) ? record.subcodes : []),
        ...(Array.isArray(record.subCodes) ? record.subCodes : []),
      ];
      for (const sub of subcodes) {
        if (!sub) continue;
        addResolvable(sub.code);
        if (Array.isArray(sub.aliases)) for (const a of sub.aliases) addResolvable(a);
        if (Array.isArray(sub.searchAliases)) for (const a of sub.searchAliases) addResolvable(a);
      }

      // Procedure-variant status codes also resolve to the parent card in the
      // primary pipeline (getExactQueryMatchRank rank 3), so never reroute them.
      const procs = record.procedures && typeof record.procedures === "object" ? record.procedures : {};
      for (const key of Object.keys(procs)) {
        const proc = procs[key];
        const variants = proc && Array.isArray(proc.variants) ? proc.variants : [];
        for (const variant of variants) {
          if (!variant) continue;
          if (variant.statusCode) addResolvable(variant.statusCode);
          if (Array.isArray(variant.statusCodes)) for (const c of variant.statusCodes) addResolvable(c);
        }
      }
    }

    return { resolvable, topByCompact };
  }

  // Returns a parent code ONLY for detail-shaped queries the primary pipeline
  // cannot resolve at all (unknown / mistyped subcodes whose parent card does
  // exist). Any query already resolvable in the loaded data returns null so the
  // primary pipeline renders its exact record/subcode view untouched.
  function resolveDetailCodeQuery(query) {
    const q = norm(query);
    if (!DETAIL_CODE_EXACT.test(q)) return null;

    const records = getResolverRecords();
    if (!records || !records.length) return null;

    const maps = buildAliasMap(records);
    if (maps.resolvable.has(compact(q))) return null;

    for (const parent of deriveParents(q)) {
      const pc = compact(parent);
      if (maps.topByCompact.has(pc)) return maps.topByCompact.get(pc);
    }

    return null;
  }

  function installDetailResolver() {
    const form = document.getElementById("searchForm");
    const input = document.getElementById("q");
    if (!form || !input || form.dataset.detailCodeResolverInstalled === "1") return;

    form.dataset.detailCodeResolverInstalled = "1";
    warmFallbackRecords();

    // Capture phase on the form fires before the primary bubble-phase submit
    // handler on the same element, so we can rewrite the query in place and let
    // the existing search pipeline run EXACTLY ONCE with the parent code. No
    // preventDefault / re-dispatch (which previously double-submitted and
    // briefly flashed the correct subcode view before the parent overview).
    form.addEventListener("submit", function () {
      const original = input.value;
      const resolved = resolveDetailCodeQuery(original);
      if (!resolved || compact(resolved) === compact(original)) return;

      input.value = resolved;
      // Restore the text the user typed once the primary handler (which reads
      // qEl.value synchronously during this same dispatch) has consumed it.
      window.setTimeout(function () {
        if (input.value === resolved) input.value = original;
      }, 0);
    }, true);
  }

  // Registration moved to index.html (a parse-time one-liner that calls this export), see module header.
  __install = installDetailResolver;
})();

export { __install as installDetailResolver };
