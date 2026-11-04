// Moved verbatim from the inline <script> block of ai.html (lines 3076-3291 before the move; Phase 5 of the frontend rebuild, 2026-11-04).
// Classic script loaded at the same document position, so it still runs synchronously at parse time in the same order.
    (function () {
        'use strict';
        if (!window.WaymakerNavigator) return;

        // The unified chat workspace is the public default. The deterministic
        // navigator is an explicit guided mode opened with ?nav=1.
        var params = new URLSearchParams(location.search);
        var legacy = params.get('legacyChat') === '1';
        try { if (localStorage.getItem('paradisoDevDiagnostics') === '1' && params.get('nav') !== '1') legacy = true; } catch (e) {}
        // Nationality-platform deep links (new-home.html / nationality-interview-hub.html
        // → ai.html?domain=nationality[&mode=naturalization_interview_prep]) advertise
        // the CHAT coach surface: applyNationalityDomainHint() seeds the chat subtitle,
        // composer placeholder, and starter chips. Mounting the navigator would hide
        // that chat behind body.wm-active and strand the user on an unrelated surface,
        // so these links keep the chat visible. ?nav=1 still forces the navigator.
        if ((params.get('domain') || '').toLowerCase() === 'nationality' && params.get('nav') !== '1') legacy = true;
        var navigatorRequested = params.get('nav') === '1';
        if (legacy || !navigatorRequested) return; // keep the unified chat workspace visible

        // Optional handoff from index.html's floating Waymaker CTA
        // (buildWaymakerHandoffUrl()): visa_code + selected_procedure_key +
        // scenario_label. Unlike AI_SCENARIO above (used for the legacy chat's
        // free-text AI context), the navigator only needs a status code to be
        // useful, so this does not require selected_procedure_variant_id. When
        // absent, the navigator behaves exactly as before (starts at "intro").
        var navInitialScenario = (function () {
            var visaCode = (params.get('visa_code') || '').trim();
            if (!visaCode) return null;
            var procedureKey = (params.get('selected_procedure_key') || '').trim();
            var label = (params.get('scenario_label') || '').trim();
            return { visaCode: visaCode, procedureKey: procedureKey || null, label: label || null };
        })();

        // Mirror ai.html's API base resolution (the const is module-scoped above).
        var apiBase = (window.VisableBackend && window.VisableBackend.origin())
            || ((window.PARADISO_BACKEND_URL && window.PARADISO_BACKEND_URL.trim())
                || ((location.hostname === 'localhost' || location.hostname === '127.0.0.1' || location.protocol === 'file:')
                    ? "" : "https://web-production-14f9a.up.railway.app"));

        function getRecords() {
            // Reuse the same source ai.html uses: live /api/visas, else local file.
            return fetch(apiBase + '/api/visas', { cache: 'no-store' })
                .then(function (r) { if (!r.ok) throw new Error('api'); return r.json(); })
                .then(function (d) { return (d && d.visas) ? d.visas : (Array.isArray(d) ? d : []); })
                .catch(function () {
                    return fetch('./visa_data.json', { cache: 'no-store' })
                        .then(function (r) { return r.json(); })
                        .then(function (d) { return Array.isArray(d) ? d : (d.visas || []); })
                        .catch(function () { return []; });
                });
        }

        // Consent state mirrors the legacy chat: the user must accept the
        // 개인정보·면책 modal before any free-text question is sent to /api/ask.
        function isWaymakerConsentGranted() {
            try {
                var p = JSON.parse(localStorage.getItem('paradiso_ai_consent') || 'null');
                return !!(p && p.agreed && (Date.now() - (p.at || 0)) < 24 * 60 * 60 * 1000);
            } catch (e) { return false; }
        }

        // Follow-up request coordination (M-6). Rapid taps on the packet's "Ask"
        // button must not race each other:
        //   * abort any earlier in-flight request (re-entry guard),
        //   * a 75s timeout budget (mirrors the main sendAi path) so a hung server
        //     never leaves the "…" spinner spinning forever,
        //   * a monotonic sequence token so ONLY the latest request renders — a
        //     superseded request adopts a never-settling promise so the navigator
        //     never clears a newer answer with a stale earlier one.
        var _followupController = null;
        var _followupSeq = 0;
        var FOLLOWUP_TIMEOUT_MS = 75000; // same budget as sendAi's AI_REQUEST_TIMEOUT_MS

        // AI follow-up — SECONDARY support. Sends ONLY safe categorical identifiers
        // + the user's typed question. No checklist, no personal identifiers, and
        // ALWAYS stream:false so the buffered, fully-gated path runs (Phase 10).
        function onAskFollowup(context, question) {
            // Gate on the existing consent modal — never post the user's question
            // to /api/ask before they have accepted the privacy/disclaimer notice.
            if (!isWaymakerConsentGranted()) {
                try { if (typeof showConsent === 'function') showConsent(); } catch (e) {}
                return Promise.resolve({
                    ok: false,
                    message: context && context.locale === 'en'
                        ? 'Please accept the privacy & disclaimer notice, then tap “Ask” again.'
                        : '개인정보·면책 동의 후 ‘질문하기’를 다시 눌러 주세요.'
                });
            }
            var body = {
                question: question,
                consent: true,
                stream: false,                              // force buffered/gated path
                answer_mode: 'basic',
                lang: context.locale === 'en' ? 'en' : 'ko',
                visa_code: context.exactStatusCode || context.statusCode || undefined,
                selected_procedure_key: context.procedureKey || undefined,
                context: 'Waymaker procedure-packet follow-up (' + (context.packetType || '') +
                         '). Explain the already-generated deterministic packet only; do not invent ' +
                         'documents, fees, deadlines, citations, or HiKorea tasks; recommend official confirmation.'
            };
            // Abort any earlier in-flight follow-up so a slow earlier response can
            // never overwrite a newer one, then claim the next sequence token.
            if (_followupController) { try { _followupController.abort(); } catch (e) {} }
            var controller = new AbortController();
            _followupController = controller;
            var mySeq = ++_followupSeq;
            var didTimeout = false;
            var timeoutId = setTimeout(function () {
                didTimeout = true;
                try { controller.abort(); } catch (e) {}
            }, FOLLOWUP_TIMEOUT_MS);
            var localeEn = !!(context && context.locale === 'en');
            // A superseded request must not render at all: its late resolution would
            // clear the newer answer (the navigator clears `out` before rendering).
            // Adopt a never-settling promise so the navigator's .then never fires.
            var stale = function () { return new Promise(function () {}); };
            var isStale = function () { return mySeq !== _followupSeq; };
            // Returns a structured result so the navigator can render the same
            // trust/safety card the legacy chat shows (renderSafetyResponse) and
            // a visible failure notice instead of silently swallowing errors —
            // a plain string collapses safety_blocked/safety_alternatives and
            // a nested {detail:{...}} error body (e.g. 503 no-provider-configured)
            // into an empty string with no user-visible feedback.
            return fetch(apiBase + '/api/ask', {
                method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body),
                signal: controller.signal
            }).then(function (r) {
                var status = r.status;
                return r.json().catch(function () { return {}; }).then(function (b) { return { status: status, body: b }; });
            }).then(function (payload) {
                  clearTimeout(timeoutId);
                  if (isStale()) return stale();
                  var status = payload.status;
                  var res = payload.body || {};
                  // Rate limited (backend rate_limited envelope, HTTP 429): a calm,
                  // localized notice — never a hard failure.
                  if (status === 429) {
                      return { ok: false, message: localeEn
                          ? 'Too many requests right now. Please wait a moment and try again.'
                          : '요청이 많아 잠시 제한되었습니다. 잠시 후 다시 시도해 주세요.' };
                  }
                  if (!res || (res.detail && typeof res.detail === 'object')) return { ok: false };
                  var answer = res.copy_safe_answer || res.answer || (res.safety_notice || '');
                  var safetyBlocked = !!res.safety_blocked;
                  var safetyAlternatives = Array.isArray(res.safety_alternatives) ? res.safety_alternatives : [];
                  // The backend's blocked answer is "<refusal paragraph>\n\n<alt heading>\n- ...".
                  // Keep only the refusal paragraph here — safetyAlternatives is rendered as its
                  // own structured list, mirroring renderSafetyResponse()'s split above so the
                  // two never duplicate the same content.
                  if (safetyBlocked && answer) answer = answer.split('\n\n')[0] || answer;
                  return {
                      ok: !!answer,
                      answer: answer,
                      safetyBlocked: safetyBlocked,
                      safetyAlternatives: safetyAlternatives
                  };
              }).catch(function () {
                  clearTimeout(timeoutId);
                  if (isStale()) return stale();
                  // Hard timeout: surface a localized "took too long" note (matching
                  // the main path's timeout card intent) instead of a silent blank.
                  if (didTimeout) {
                      return { ok: false, message: localeEn
                          ? 'The response is taking too long, so the request was stopped. Please try again shortly; for urgent matters, confirm via HiKorea (hikorea.go.kr) or 1345.'
                          : 'AI 응답이 지연되어 요청을 중단했습니다. 잠시 후 다시 시도해 주세요. 급한 경우 HiKorea(hikorea.go.kr) 또는 1345로 확인하세요.' };
                  }
                  return { ok: false };
              });
        }

        // HiKorea handoff — reuse the deterministic helper's pure logic if present;
        // always preserve the official HiKorea link + 1345 fallback. Never automate
        // login/booking/payment, never fabricate a reservation category.
        function openHiKorea(statusCode, procedureKey, packetType, isLimited) {
            try {
                if (window.ParadisoReservationHelper && typeof window.ParadisoReservationHelper.open === 'function'
                    && document.getElementById('hikoreaGuideOverlay')) {
                    window.ParadisoReservationHelper.open({ visaCode: statusCode });
                    return;
                }
            } catch (e) {}
            window.open('https://www.hikorea.go.kr', '_blank', 'noopener');
        }

        function analytics(event, props) {
            // Privacy-safe sink: forward to a global analytics layer if present,
            // else no-op. (The module already strips to categorical props.)
            try { if (window.PARADISO_ANALYTICS && window.PARADISO_ANALYTICS.track) window.PARADISO_ANALYTICS.track(event, props); } catch (e) {}
        }

        var root = document.getElementById('waymakerNavigatorRoot');
        if (!root) return;
        document.body.classList.add('wm-active');
        try {
            window.__waymakerNav = window.WaymakerNavigator.createNavigator({
                root: root, apiBase: apiBase, getRecords: getRecords,
                onAskFollowup: onAskFollowup, openHiKorea: openHiKorea, analytics: analytics,
                initialScenario: navInitialScenario
            }).mount();
        } catch (e) {
            // If the navigator fails to mount, fall back to the legacy chat surface
            // rather than showing a blank page.
            document.body.classList.remove('wm-active');
            if (window.console && console.error) console.error('Waymaker navigator failed to mount:', e);
        }
        // Deep link ai.html#legalSourceSearchRoot → scroll to the research panel
        // once the navigator surface (which makes it visible) has mounted.
        try {
            if (location.hash === '#legalSourceSearchRoot') {
                var lr = document.getElementById('legalSourceSearchRoot');
                if (lr) setTimeout(function () { lr.scrollIntoView({ behavior: 'smooth', block: 'start' }); }, 250);
            }
        } catch (e) {}
    })();
