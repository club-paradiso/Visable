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

  /*
   * Root-index landing compatibility shims.
   *
   * The shared Figma skin currently hides the historical .p-gw-utility row
   * with display:none!important even though the actions still exist. The main
   * HTML is a very large single-file application, so keep the narrowly scoped
   * restoration in its own stylesheet and load it only for the root landing.
   *
   * The short-stay module is deferred and can finish after a fast mobile user
   * taps the restored button. The delegated action intentionally calls
   * window.ParadisoShortStay.open(), so install a tiny readiness bridge before
   * that module loads. If the user taps early, the bridge records the intent;
   * when the real module assigns window.ParadisoShortStay, the setter replays
   * exactly one open. This is UI readiness only and does not touch entry rules.
   *
   * Neither shim participates in backend-origin resolution.
   */
  try {
    var doc = global.document;
    var pathname = (global.location && global.location.pathname) || '';
    var isRootLanding = pathname === '/' || pathname === '/index.html';

    if (doc && doc.head && isRootLanding &&
        !doc.getElementById('visable-landing-utility-restoration')) {
      var utilityStyles = doc.createElement('link');
      utilityStyles.id = 'visable-landing-utility-restoration';
      utilityStyles.rel = 'stylesheet';
      utilityStyles.href = 'assets/css/landing-utility-restoration-20260908.css';
      doc.head.appendChild(utilityStyles);
    }

    if (isRootLanding && (!global.ParadisoShortStay || typeof global.ParadisoShortStay.open !== 'function')) {
      var pendingShortStayOpen = false;
      var shortStayBootstrap = {
        __visableBootstrap: true,
        open: function () {
          pendingShortStayOpen = true;
        }
      };

      Object.defineProperty(global, 'ParadisoShortStay', {
        configurable: true,
        enumerable: true,
        get: function () {
          return shortStayBootstrap;
        },
        set: function (realApi) {
          Object.defineProperty(global, 'ParadisoShortStay', {
            configurable: true,
            enumerable: true,
            writable: true,
            value: realApi
          });

          if (pendingShortStayOpen && realApi && typeof realApi.open === 'function') {
            pendingShortStayOpen = false;
            global.setTimeout(function () {
              try { realApi.open(); } catch (e) { /* keep page usable if popup setup fails */ }
            }, 0);
          }
        }
      });
    }
  } catch (e) {
    // Landing compatibility must never interfere with backend resolution.
  }
})(typeof window !== 'undefined' ? window : this);