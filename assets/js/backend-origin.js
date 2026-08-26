/**
 * The one place Visable's backend origin is defined.
 *
 * Why this file exists
 * --------------------
 * The production backend URL was written out five separate times — twice in
 * index.html, twice in ai.html, and once each in three feature scripts — as a
 * `DEFAULT_API_BASE` literal, each with its own copy of the localhost-detection
 * logic. Moving the backend meant finding all five, and missing one produced a
 * page that silently talked to the wrong host.
 *
 * Now there is exactly one literal. Every call site resolves through
 * `window.VisableBackend.origin()`.
 *
 * Deliberately not a build step: this site ships as static files with no
 * bundler, and introducing one purely to inline a constant would cost far more
 * than it saves. A plain script loaded before its consumers is the simplest
 * mechanism that actually fits how this project deploys.
 *
 * Resolution order
 * ----------------
 *   1. `window.PARADISO_BACKEND_URL`, if a deploy set it. This is the override
 *      hook that already existed; it keeps working unchanged.
 *   2. Same-origin (empty string) on localhost / 127.0.0.1 / file:, so local
 *      development talks to a local backend rather than production.
 *   3. The committed production origin.
 *
 * No credential ever appears here. The browser calls Visable's own backend and
 * nothing else; provider keys stay server-side.
 */
(function (global) {
  'use strict';

  // The single source of truth. Changing the backend host is this one edit.
  var PRODUCTION_ORIGIN = 'https://web-production-14f9a.up.railway.app';

  var LOCAL_HOSTNAMES = ['localhost', '127.0.0.1', '[::1]', '::1'];

  function isLocalContext() {
    try {
      if (global.location && global.location.protocol === 'file:') return true;
      var host = (global.location && global.location.hostname) || '';
      return LOCAL_HOSTNAMES.indexOf(host) >= 0;
    } catch (e) {
      // A context without `location` (a worker, a test harness) is not
      // local development; fall through to the production origin.
      return false;
    }
  }

  function origin() {
    try {
      var override = global.PARADISO_BACKEND_URL;
      if (override && String(override).trim()) {
        return String(override).trim().replace(/\/+$/, '');
      }
    } catch (e) { /* an unreadable override is simply not an override */ }

    // Same-origin locally: a dev server proxies /api itself, and pointing a
    // local page at production would send development traffic to real users'
    // backend.
    return isLocalContext() ? '' : PRODUCTION_ORIGIN;
  }

  function url(path) {
    var base = origin();
    var suffix = String(path || '');
    if (suffix && suffix.charAt(0) !== '/') suffix = '/' + suffix;
    return base + suffix;
  }

  global.VisableBackend = {
    origin: origin,
    url: url,
    productionOrigin: PRODUCTION_ORIGIN,
    isLocalContext: isLocalContext
  };

  // Back-compat: several call sites read this global directly. Publishing the
  // resolved value keeps them working without each re-deriving it.
  if (!global.PARADISO_BACKEND_URL) {
    try {
      global.PARADISO_BACKEND_URL = global.PARADISO_BACKEND_URL || '';
    } catch (e) { /* non-writable global: the resolver above still works */ }
  }
})(typeof window !== 'undefined' ? window : this);
