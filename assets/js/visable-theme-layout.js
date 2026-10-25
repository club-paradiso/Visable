/*
 * Visable theme layouts — result page arrangement per visual theme.
 *
 * The approved Claude Design canvas ("Visable Rebrand — Clear Passage")
 * arranges the same answer differently per theme:
 *   Visable · Chrome → answer band on top, then a reading column and a side
 *                      column (next steps, fee, local office)
 *   Stamp            → an open passport booklet: left page (answer, overview,
 *                      conditions, local), right page (documents, fee, next)
 *   Neon             → one centred conversation column (CSS only, no regroup)
 *
 * status-guidance.js re-renders #statusGuidance with innerHTML. After each
 * render this script MOVES the existing blocks into column wrappers. Nothing
 * is cloned, added or reworded: copy, data, disclaimers and the reading
 * order inside each column stay exactly as rendered. Below 1024px, without a
 * structured answer, or with no visual theme (legacy looks), the blocks stay
 * in one column in their original order.
 */
(function () {
  'use strict';
  var root = document.documentElement;
  var MIN = 1024;
  var host = null;
  var busy = false;

  // Which column each block goes to, per theme. Anything not listed stays in
  // the main (left-page) column, in rendered order.
  var PLANS = {
    default: { kind: 'aside', head: ['sg-interp', 'sg-editor', 'sg-answered', 'sg-answer'], side: ['sg-next', 'sg-fee', 'sg-local'], tail: ['sg-related', 'sg-disclaimer'] },
    chrome: { kind: 'aside', head: ['sg-interp', 'sg-editor', 'sg-answered', 'sg-answer'], side: ['sg-fee', 'sg-next', 'sg-local'], tail: ['sg-related', 'sg-disclaimer'] },
    stamp: { kind: 'spread', head: ['sg-interp', 'sg-editor', 'sg-answered'], side: ['sg-docs', 'sg-fee', 'sg-next'], tail: ['sg-evidence', 'sg-related', 'sg-disclaimer'] }
  };

  function wide() { return window.matchMedia ? window.matchMedia('(min-width: ' + MIN + 'px)').matches : window.innerWidth >= MIN; }
  function hasClass(el, list) { for (var i = 0; i < list.length; i++) if (el.classList.contains(list[i])) return true; return false; }
  function direct(h) { return Array.prototype.slice.call(h.children); }
  function isCol(el) { return el.classList.contains('vl-col'); }

  function unwrap(h) {
    if (!direct(h).some(isCol)) { h.removeAttribute('data-vl'); return; }
    var moved = Array.prototype.slice.call(h.querySelectorAll('[data-vl-i]'));
    moved.sort(function (a, b) { return (+a.getAttribute('data-vl-i')) - (+b.getAttribute('data-vl-i')); });
    var first = direct(h).filter(isCol)[0];
    moved.forEach(function (el) { h.insertBefore(el, first); el.removeAttribute('data-vl-i'); });
    direct(h).filter(isCol).forEach(function (c) { c.remove(); });
    h.removeAttribute('data-vl');
  }

  function want() {
    var vt = root.getAttribute('data-vt');
    var plan = PLANS[vt];
    if (!plan || !wide() || !document.body.classList.contains('searched')) return null;
    return { vt: vt, plan: plan };
  }

  function apply() {
    if (busy) return;
    var h = host || (host = document.getElementById('statusGuidance'));
    if (!h) return;
    var w = want();
    var sig = w ? w.vt : '';
    var wrapped = direct(h).some(isCol);
    // Already in the wanted state with no new loose blocks: nothing to do.
    if (wrapped && h.getAttribute('data-vl-vt') === sig && !direct(h).some(function (el) { return !isCol(el); })) return;
    if (!wrapped && !w) return;
    busy = true;
    try {
      unwrap(h);
      h.removeAttribute('data-vl-vt');
      if (!w || !h.querySelector(':scope > .sg-answer')) return;
      var plan = w.plan;
      var head = [], main = [], side = [], tail = [];
      direct(h).forEach(function (el, i) {
        el.setAttribute('data-vl-i', String(i));
        if (el.id === 'sgHeading' || hasClass(el, plan.head)) head.push(el);
        else if (hasClass(el, plan.tail)) tail.push(el);
        else if (hasClass(el, plan.side)) side.push(el);
        else main.push(el);
      });
      if (!side.length || !main.length) { direct(h).forEach(function (el) { el.removeAttribute('data-vl-i'); }); return; }
      var col = function (name, items) {
        var d = document.createElement('div');
        d.className = 'vl-col vl-' + name;
        items.forEach(function (el) { d.appendChild(el); });
        return d;
      };
      var grid = col('grid', []);
      grid.appendChild(col('main', main));
      grid.appendChild(col('side', side));
      // Head → grid(main, side) → tail: the same order assistive technology
      // and the single-column layout read.
      h.appendChild(col('head', head));
      h.appendChild(grid);
      h.appendChild(col('tail', tail));
      h.setAttribute('data-vl', plan.kind);
      h.setAttribute('data-vl-vt', sig);
    } finally { busy = false; }
  }

  function schedule() { if (!busy) (window.requestAnimationFrame || setTimeout)(apply); }

  function boot() {
    host = document.getElementById('statusGuidance');
    document.addEventListener('visable:guidance-rendered', schedule);
    document.addEventListener('paradiso:landing-reset', schedule);
    if (window.MutationObserver) {
      new MutationObserver(schedule).observe(root, { attributes: true, attributeFilter: ['data-vt'] });
      if (host) new MutationObserver(schedule).observe(host, { childList: true });
    }
    var t = null;
    window.addEventListener('resize', function () { clearTimeout(t); t = setTimeout(apply, 120); });
    apply();
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot); else boot();
  window.VisableThemeLayout = { apply: apply };
})();
