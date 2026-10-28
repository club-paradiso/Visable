/* Shared anchoring for header popovers (language selector, theme picker).
 *
 * Why this exists: each overlay used to set its own `top` + `right` from the
 * trigger's rect. A modal <dialog> also carries the UA rule
 * `inset-inline-start: 0`, so with a fixed width the box was over-constrained
 * and the browser dropped `right` — the language panel opened at the left edge
 * of the screen instead of under the KO button. Placement now always writes
 * every inset explicitly (left/top set, right/bottom auto), measures the panel
 * after it is displayed, and keeps it inside the viewport.
 *
 *   VisableOverlay.place(panel, trigger, opts) -> { side, left, top } | null
 *   VisableOverlay.track(panel, trigger, opts) -> stop()
 *
 * opts.gap (8)     space between trigger and panel
 * opts.margin (12) minimum distance from every viewport edge
 * opts.when()      false = let the stylesheet place it (e.g. a mobile bottom
 *                  sheet); inline insets are cleared
 *
 * Alignment is the trigger's inline end: right edges line up in LTR, left
 * edges in RTL (the mirrored header puts the button on the left). The panel
 * opens below the trigger; when it does not fit and there is more room above,
 * it opens above. Whichever side is used, a panel taller than the room gets a
 * max-height and scrolls inside. track() re-places on resize and on any
 * scroll (page or ancestor) so the panel stays attached to its trigger. */
(function () {
  'use strict';
  var INSETS = ['left', 'top', 'right', 'bottom', 'maxHeight'];

  function clear(panel) {
    INSETS.forEach(function (k) { panel.style[k] = ''; });
    delete panel.dataset.placement;
  }
  function active(opts) { return !opts || typeof opts.when !== 'function' || opts.when(); }

  function place(panel, trigger, opts) {
    opts = opts || {};
    if (!panel) return null;
    if (!trigger || !trigger.isConnected || !active(opts)) { clear(panel); return null; }
    var gap = opts.gap == null ? 8 : opts.gap;
    var margin = opts.margin == null ? 12 : opts.margin;
    var de = document.documentElement;
    var vw = de.clientWidth || window.innerWidth;
    var vh = de.clientHeight || window.innerHeight;
    // Reset to the stylesheet's size before measuring; offset* ignores the open animation's transform.
    panel.style.maxHeight = '';
    panel.style.right = 'auto';
    panel.style.bottom = 'auto';
    var r = trigger.getBoundingClientRect();
    var pw = panel.offsetWidth, ph = panel.offsetHeight;
    var rtl = getComputedStyle(trigger).direction === 'rtl';

    var left = rtl ? r.left : r.right - pw;
    left = Math.min(left, vw - margin - pw);
    left = Math.max(margin, left);

    var below = vh - r.bottom - gap - margin;
    var above = r.top - gap - margin;
    var side = ph <= below || below >= above ? 'bottom' : 'top';
    var room = Math.max(0, side === 'bottom' ? below : above);
    if (ph > room) { panel.style.maxHeight = Math.floor(room) + 'px'; ph = Math.min(ph, panel.offsetHeight); }
    var top = side === 'bottom' ? r.bottom + gap : r.top - gap - ph;

    panel.style.left = Math.round(left) + 'px';
    panel.style.top = Math.round(top) + 'px';
    panel.dataset.placement = side;
    return { side: side, left: Math.round(left), top: Math.round(top) };
  }

  function track(panel, trigger, opts) {
    var frame = 0;
    function update() { frame = 0; place(panel, trigger, opts); }
    function schedule() { if (!frame) frame = requestAnimationFrame(update); }
    place(panel, trigger, opts);
    window.addEventListener('resize', schedule);
    window.addEventListener('scroll', schedule, { capture: true, passive: true });
    var vv = window.visualViewport;
    if (vv) vv.addEventListener('resize', schedule);
    return function stop() {
      if (frame) cancelAnimationFrame(frame);
      window.removeEventListener('resize', schedule);
      window.removeEventListener('scroll', schedule, { capture: true });
      if (vv) vv.removeEventListener('resize', schedule);
    };
  }

  window.VisableOverlay = { place: place, track: track, clear: clear };
})();
