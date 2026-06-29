/* Visable by Paradiso · Aurora Mesh hero behavior
   Additive, landing-only, safe to load after the existing index.html bundle.
*/
(function () {
  'use strict';

  var LAYER_ID = 'visableAuroraHeroBg';
  var LINK_ID = 'visableAuroraHeroStylesheet';
  var REDUCE = false;
  try {
    REDUCE = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  } catch (e) {}

  function ensureStylesheet() {
    if (document.getElementById(LINK_ID)) return;
    var link = document.createElement('link');
    link.id = LINK_ID;
    link.rel = 'stylesheet';
    link.href = 'assets/css/visable-aurora-hero.css?v=20260629';
    document.head.appendChild(link);
  }

  function getHero() {
    return document.getElementById('hero') || document.querySelector('header[role="banner"]') || document.querySelector('header');
  }

  function createLayer() {
    var root = document.createElement('div');
    root.id = LAYER_ID;
    root.className = 'visable-aurora-hero-bg';
    root.setAttribute('aria-hidden', 'true');

    ['blue', 'mint', 'coral', 'emerald'].forEach(function (name) {
      var blob = document.createElement('span');
      blob.className = 'visable-aurora-blob visable-aurora-blob--' + name;
      root.appendChild(blob);
    });

    var mesh = document.createElement('span');
    mesh.className = 'visable-aurora-mesh';
    root.appendChild(mesh);
    return root;
  }

  function ensureLayer() {
    var hero = getHero();
    if (!hero) return null;
    var existing = document.getElementById(LAYER_ID);
    if (existing) return existing;
    var layer = createLayer();
    hero.insertBefore(layer, hero.firstChild);
    return layer;
  }

  var raf = 0;
  var lastX = 0;
  var lastY = 0;

  function setPointerVars() {
    raf = 0;
    var root = document.documentElement;
    root.style.setProperty('--visable-aurora-mx', (lastX * 18).toFixed(2) + 'px');
    root.style.setProperty('--visable-aurora-my', (lastY * 18).toFixed(2) + 'px');
  }

  function onPointerMove(event) {
    if (REDUCE) return;
    var width = Math.max(window.innerWidth || 1, 1);
    var height = Math.max(window.innerHeight || 1, 1);
    lastX = (event.clientX / width) - 0.5;
    lastY = (event.clientY / height) - 0.5;
    if (!raf) raf = window.requestAnimationFrame(setPointerVars);
  }

  var scrollRaf = 0;
  function setScrollVar() {
    scrollRaf = 0;
    var hero = getHero();
    var heroHeight = hero ? Math.max(hero.offsetHeight || 1, 1) : Math.max(window.innerHeight || 1, 1);
    var depth = Math.max(0, Math.min(1, (window.scrollY || 0) / heroHeight));
    document.documentElement.style.setProperty('--visable-aurora-scroll', depth.toFixed(3));
  }

  function onScroll() {
    if (REDUCE) return;
    if (!scrollRaf) scrollRaf = window.requestAnimationFrame(setScrollVar);
  }

  function init() {
    ensureStylesheet();
    var layer = ensureLayer();
    if (!layer) return;

    // The existing app already uses body.landing/searching/searched as a state
    // machine. We only add decorative depth to the landing state.
    document.addEventListener('pointermove', onPointerMove, { passive: true });
    window.addEventListener('scroll', onScroll, { passive: true });
    setScrollVar();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init, { once: true });
  } else {
    init();
  }
})();
