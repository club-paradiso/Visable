/* Shared decorative pictograms. Source labels stay intact for existing renderers. */
(function () {
  'use strict';
  var catalog = {
  "paths": {
    "clock": "<circle cx=\"12\" cy=\"12\" r=\"9\"/><path d=\"M12 7v5l3 2\"/>",
    "change": "<path d=\"M4 7h16m-4-4 4 4-4 4M20 17H4m4-4-4 4 4 4\"/>",
    "id-card": "<rect x=\"3\" y=\"5\" width=\"18\" height=\"14\" rx=\"2\"/><circle cx=\"8\" cy=\"10\" r=\"2\"/><path d=\"M5 16a3 3 0 0 1 6 0m3-7h4m-4 4h4\"/>",
    "globe": "<circle cx=\"12\" cy=\"12\" r=\"9\"/><path d=\"M3 12h18M12 3a17 17 0 0 1 0 18 17 17 0 0 1 0-18\"/>",
    "lightbulb": "<path d=\"M9 18h6m-5 3h4M8 14a6 6 0 1 1 8 0c-1 1-1 2-1 4H9c0-2 0-3-1-4Z\"/>",
    "user": "<circle cx=\"12\" cy=\"8\" r=\"4\"/><path d=\"M4 21v-2a8 8 0 0 1 16 0v2\"/>",
    "arrow-left": "<path d=\"M20 12H4m6-6-6 6 6 6\"/>",
    "clipboard": "<rect x=\"7\" y=\"3\" width=\"10\" height=\"4\" rx=\"1\"/><path d=\"M7 5H5a2 2 0 0 0-2 2v13a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V7a2 2 0 0 0-2-2h-2M8 12h8m-8 5h8\"/>",
    "search": "<circle cx=\"10.5\" cy=\"10.5\" r=\"7.5\"/><path d=\"m16 16 5 5\"/>",
    "landmark": "<path d=\"m3 9 9-6 9 6H3Zm2 1v8m5-8v8m4-8v8m5-8v8M3 21h18M3 18h18\"/>",
    "warning": "<path d=\"m10.3 3.9-8 14a2 2 0 0 0 1.7 3h16a2 2 0 0 0 1.7-3l-8-14a2 2 0 0 0-3.4 0ZM12 9v4m0 4h.01\"/>",
    "printer": "<path d=\"M6 8V3h12v5M6 17H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2M6 14h12v7H6Zm12-3h.01\"/>",
    "link": "<path d=\"m10 13 4-4m-6 6-2 2a3.5 3.5 0 0 1-5-5l4-4a3.5 3.5 0 0 1 5 0m4 2 2-2a3.5 3.5 0 0 1 5 5l-4 4a3.5 3.5 0 0 1-5 0\"/>",
    "ban": "<circle cx=\"12\" cy=\"12\" r=\"9\"/><path d=\"m6 6 12 12\"/>",
    "info": "<circle cx=\"12\" cy=\"12\" r=\"9\"/><path d=\"M12 11v6m0-10h.01\"/>",
    "scale": "<path d=\"M12 3v18m-5 0h10M4 7l8-2 8 2M4 7l-3 7h6L4 7Zm16 0-3 7h6l-3-7Z\"/>",
    "file-text": "<path d=\"M6 22a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h8a2.4 2.4 0 0 1 1.704.706l3.588 3.588A2.4 2.4 0 0 1 20 8v12a2 2 0 0 1-2 2z\" />\n  <path d=\"M14 2v5a1 1 0 0 0 1 1h5\" />\n  <path d=\"M10 9H8\" />\n  <path d=\"M16 13H8\" />\n  <path d=\"M16 17H8\" />",
    "calendar-days": "<path d=\"M8 2v3\" />\n  <path d=\"M16 2v3\" />\n  <rect x=\"3\" y=\"3\" width=\"18\" height=\"18\" rx=\"2\" />\n  <path d=\"M3 9h18\" />\n  <path d=\"M8 13h.01\" />\n  <path d=\"M12 13h.01\" />\n  <path d=\"M16 13h.01\" />\n  <path d=\"M8 17h.01\" />\n  <path d=\"M12 17h.01\" />\n  <path d=\"M16 17h.01\" />",
    "book-open": "<path d=\"M12 5v16\" />\n  <path d=\"M20.001 19A2 2 0 0022 17V5a2 2 0 00-1.999-2L16 3.002A5 5 0 0012 5a5 5 0 00-4-2H4a2 2 0 00-2 2v12a2 2 0 001.999 2H8a5 5 0 014 2 5 5 0 014-2z\" />",
    "house": "<path d=\"M15 21v-8a1 1 0 0 0-1-1h-4a1 1 0 0 0-1 1v8\" />\n  <path d=\"M3 10a2 2 0 0 1 .709-1.528l7-5.999a2 2 0 0 1 2.582 0l7 5.999A2 2 0 0 1 21 10v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z\" />",
    "compass": "<path d=\"m16.24 7.76-1.804 5.411a2 2 0 0 1-1.265 1.265L7.76 16.24l1.804-5.411a2 2 0 0 1 1.265-1.265z\" />\n  <circle cx=\"12\" cy=\"12\" r=\"10\" />",
    "plane": "<path d=\"M17.8 19.2 16 11l3.5-3.5C21 6 21.5 4 21 3c-1-.5-3 0-4.5 1.5L13 8 4.8 6.2c-.5-.1-.9.1-1.1.5l-.3.5c-.2.5-.1 1 .3 1.3L9 12l-2 3H4l-1 1 3 2 2 3 1-1v-3l3-2 3.5 5.3c.3.4.8.5 1.3.3l.5-.2c.4-.3.6-.7.5-1.2z\" />",
    "external-link": "<path d=\"M15 3h6v6\" />\n  <path d=\"M10 14 21 3\" />\n  <path d=\"M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6\" />",
    "check": "<path d=\"m5 12 4 4L19 6\"/>",
    "check-square": "<rect x=\"3\" y=\"3\" width=\"18\" height=\"18\" rx=\"3\"/><path d=\"m7 12 3 3 7-7\"/>",
    "x": "<path d=\"m6 6 12 12M6 18 18 6\"/>",
    "briefcase": "<rect x=\"3\" y=\"7\" width=\"18\" height=\"14\" rx=\"2\"/><path d=\"M8 7V3h8v4M3 12a20 20 0 0 0 18 0M12 11v4\"/>",
    "hospital": "<path d=\"M5 21V3h14v18M3 21h18M9 7h6m-3-3v6M9 21v-6h6v6\"/>",
    "graduation": "<path d=\"m2 9 10-5 10 5-10 5-10-5Zm4 2v6c4 3 8 3 12 0v-6M22 9v7\"/>",
    "wrench": "<path d=\"M14 6a6 6 0 0 0-7 7L3 17a3 3 0 0 0 4 4l4-4a6 6 0 0 0 7-7l-4 4-4-4 4-4Z\"/>",
    "target": "<circle cx=\"12\" cy=\"12\" r=\"9\"/><circle cx=\"12\" cy=\"12\" r=\"5\"/><circle cx=\"12\" cy=\"12\" r=\"1\"/>",
    "users": "<circle cx=\"9\" cy=\"7\" r=\"3\"/><path d=\"M2 21v-2a7 7 0 0 1 14 0v2M16 4a3 3 0 0 1 0 6m3 4a6 6 0 0 1 3 5v2\"/>",
    "factory": "<path d=\"M3 21V10l6 3V7l6 4V3h4l2 18H3ZM7 17h1m4 0h1m4 0h1\"/>",
    "coins": "<ellipse cx=\"9\" cy=\"6\" rx=\"6\" ry=\"3\"/><path d=\"M3 6v6c0 4 12 4 12 0V6M3 10c0 4 12 4 12 0m0-1c8-1 8 5 0 6m-6 1v3c0 4 12 4 12 0v-7\"/>",
    "flag": "<path d=\"M4 22V3m0 0c5-4 11 4 16 0v10c-5 4-11-4-16 0\"/>",
    "pin": "<path d=\"m9 3 9 3-3 5 3 4-6 1-4 5 1-6-5-4 5-2V3Z\"/>",
    "phone": "<path d=\"M6 3H3v4c0 8 6 14 14 14h4v-4l-5-2-2 2a14 14 0 0 1-7-7l2-2-3-5Z\"/>",
    "map-pin": "<path d=\"M20 10c0 6-8 12-8 12S4 16 4 10a8 8 0 1 1 16 0Z\"/><circle cx=\"12\" cy=\"10\" r=\"3\"/>",
    "handshake": "<path d=\"m2 8 5-4 5 2 5-2 5 4-3 9-6 4-6-3-5-10Zm5-4 5 2-4 5 3 2 5-4m-3 12 2-3m-6 1 2-3m4 2 2-3\"/>",
    "bot": "<rect x=\"3\" y=\"7\" width=\"18\" height=\"14\" rx=\"3\"/><path d=\"M12 7V3m-2 12h4M7 11h.01M17 11h.01\"/>",
    "package": "<path d=\"m3 7 9-4 9 4v10l-9 4-9-4V7Zm0 0 9 5 9-5M12 12v9M7 5l10 5\"/>",
    "building": "<rect x=\"5\" y=\"3\" width=\"14\" height=\"18\" rx=\"1\"/><path d=\"M9 7h1m4 0h1M9 11h1m4 0h1M9 21v-5h6v5\"/>",
    "drama": "<path d=\"M3 3c4 2 6 2 10 0v7c0 4-5 6-5 6S3 14 3 10V3Zm5 16c2 3 5 3 5 3s7-2 7-7V7l-5 1M6 7h.01M10 7h.01M6 11h4m7 2h.01\"/>",
    "eye": "<path d=\"M2 12s4-7 10-7 10 7 10 7-4 7-10 7S2 12 2 12Z\"/><circle cx=\"12\" cy=\"12\" r=\"3\"/>",
    "smile": "<circle cx=\"12\" cy=\"12\" r=\"9\"/><path d=\"M8 14c2 3 6 3 8 0M8 9h.01M16 9h.01\"/>",
    "plus": "<path d=\"M12 4v16M4 12h16\"/>",
    "lock": "<rect x=\"4\" y=\"10\" width=\"16\" height=\"12\" rx=\"2\"/><path d=\"M8 10V6a4 4 0 0 1 8 0v4m-4 5v3\"/>",
    "help": "<circle cx=\"12\" cy=\"12\" r=\"9\"/><path d=\"M9 9a3 3 0 1 1 5 2l-2 2m0 4h.01\"/>",
    "square": "<rect x=\"3\" y=\"3\" width=\"18\" height=\"18\" rx=\"3\"/>",
    "speech": "<path d=\"M21 11a9 9 0 0 1-9 9H3l2-5a9 9 0 1 1 16-4Z\"/><path d=\"M8 9h8m-8 4h5\"/>",
    "pen": "<path d=\"m16 3 5 5-12 12-6 1 1-6L16 3Zm-1 1 5 5\"/>",
    "hourglass": "<path d=\"M5 3h14M5 21h14M7 3v4l5 5-5 5v4M17 3v4l-5 5 5 5v4\"/>",
    "image": "<rect x=\"3\" y=\"3\" width=\"18\" height=\"18\" rx=\"2\"/><circle cx=\"8\" cy=\"8\" r=\"2\"/><path d=\"m3 18 6-6 4 4 3-3 5 5\"/>",
    "mouse": "<rect x=\"6\" y=\"2\" width=\"12\" height=\"20\" rx=\"6\"/><path d=\"M12 2v7\"/>",
    "backpack": "<rect x=\"5\" y=\"6\" width=\"14\" height=\"16\" rx=\"3\"/><path d=\"M9 6V3h6v3M8 16h8v4H8Zm1-6h6\"/>",
    "life-buoy": "<circle cx=\"12\" cy=\"12\" r=\"9\"/><circle cx=\"12\" cy=\"12\" r=\"4\"/><path d=\"m5.5 5.5 3.7 3.7m5.6 5.6 3.7 3.7m0-13-3.7 3.7m-5.6 5.6-3.7 3.7\"/>",
    "inbox": "<path d=\"m3 4-1 12v5h20v-5L21 4H3Zm-1 12h6l2 3h4l2-3h6\"/>",
    "flask": "<path d=\"M9 3h6M10 3v7L4 20h16l-6-10V3M7 15h10\"/>",
    "chart": "<path d=\"M3 3v18h18M7 17v-5m5 5V7m5 10V4\"/>",
    "rocket": "<path d=\"m7 14 3 3c7-2 11-7 11-14-7 0-12 4-14 11Zm0 0-4 1 1-6 5-2m1 10-1 4 6-1 2-5M3 21l3-3\"/><circle cx=\"16\" cy=\"8\" r=\"2\"/>",
    "bolt": "<path d=\"m13 2-9 12h7l-1 8 10-12h-7l0-8Z\"/>",
    "sparkles": "<path d=\"m12 3 2.5 6.5L21 12l-6.5 2.5L12 21l-2.5-6.5L3 12l6.5-2.5L12 3ZM3 3v4M1 5h4m15 14v4m-2-2h4\"/>",
    "dice": "<rect x=\"3\" y=\"3\" width=\"18\" height=\"18\" rx=\"3\"/><path d=\"M7 7h.01M17 7h.01M12 12h.01M7 17h.01M17 17h.01\"/>",
    "refresh": "<path d=\"M4 7h16m-4-4 4 4-4 4M20 17H4m4-4-4 4 4 4\"/>"
  },
  "mapping": {
    "🕓": "clock",
    "⏰": "clock",
    "⏱": "clock",
    "🌐": "globe",
    "🌏": "globe",
    "🌍": "globe",
    "🌎": "globe",
    "🏛": "landmark",
    "🧭": "compass",
    "⚖": "scale",
    "🏡": "house",
    "🏠": "house",
    "💼": "briefcase",
    "👔": "briefcase",
    "🏥": "hospital",
    "🛂": "plane",
    "✈": "plane",
    "🛫": "plane",
    "🛬": "plane",
    "🎓": "graduation",
    "✅": "check",
    "☑": "check-square",
    "⚠": "warning",
    "🚨": "warning",
    "💡": "lightbulb",
    "🔧": "wrench",
    "🛠": "wrench",
    "🎯": "target",
    "🙋": "user",
    "👥": "users",
    "👨‍👩‍👧‍👦": "users",
    "🏭": "factory",
    "💰": "coins",
    "🏁": "flag",
    "📌": "pin",
    "📚": "book-open",
    "📖": "book-open",
    "📋": "clipboard",
    "🔍": "search",
    "🔎": "search",
    "📞": "phone",
    "☎": "phone",
    "📅": "calendar-days",
    "🗓": "calendar-days",
    "📍": "map-pin",
    "🤝": "handshake",
    "🤖": "bot",
    "📦": "package",
    "🏢": "building",
    "📄": "file-text",
    "📑": "file-text",
    "🎭": "drama",
    "🪪": "id-card",
    "🧐": "eye",
    "🙂": "smile",
    "➕": "plus",
    "🔒": "lock",
    "❓": "help",
    "🔗": "link",
    "ℹ": "info",
    "⬜": "square",
    "🔄": "refresh",
    "🗣": "speech",
    "📝": "pen",
    "⏳": "hourglass",
    "🖼": "image",
    "🖱": "mouse",
    "🎒": "backpack",
    "🛟": "life-buoy",
    "📭": "inbox",
    "🔬": "flask",
    "📊": "chart",
    "🚀": "rocket",
    "❌": "x",
    "⚡": "bolt",
    "✨": "sparkles",
    "🎲": "dice"
  }
};
  var token = /\p{Regional_Indicator}{2}|\p{Extended_Pictographic}(?:\uFE0F|\p{Emoji_Modifier})?(?:\u200D\p{Extended_Pictographic}(?:\uFE0F|\p{Emoji_Modifier})?)*/gu;
  var plainSymbols = new Set(['©', '®', '™', '↔', '↕', '↖', '↗', '↘', '↙', '↩', '↪', '⤴', '⤵', '▶', '◀']);
  var excluded = 'script,style,noscript,textarea,input,svg,pre,code,[contenteditable="true"],[data-vs-pictogram],[data-original-source],#secs';
  function nameFor(value) {
    var clean = value.replace(/\uFE0F|\p{Emoji_Modifier}/gu, '');
    if (plainSymbols.has(clean)) return null;
    if (/^\p{Regional_Indicator}{2}$/u.test(clean)) return 'globe';
    return catalog.mapping[clean] || 'info';
  }
  function icon(name) {
    var svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    svg.setAttribute('viewBox', '0 0 24 24');
    svg.setAttribute('aria-hidden', 'true');
    svg.setAttribute('focusable', 'false');
    svg.innerHTML = catalog.paths[name] || catalog.paths.info;
    return svg;
  }
  function decorate(node) {
    var parent = node.parentElement;
    if (!parent || parent.closest(excluded)) return;
    var value = node.nodeValue;
    token.lastIndex = 0;
    var matches = Array.from(value.matchAll(token)).filter(function (m) { return nameFor(m[0]); });
    if (!matches.length) return;
    var control = parent.closest('button,a,[role="button"]');
    if (control && !control.hasAttribute('aria-label') && !control.hasAttribute('aria-labelledby') && !control.title) {
      token.lastIndex = 0;
      if (!control.textContent.replace(token, '').trim()) control.setAttribute('aria-label', control.textContent.trim());
    }
    // Native option menus cannot render SVG. Keep their text label and value.
    if (parent.closest('option')) {
      token.lastIndex = 0;
      node.nodeValue = value.replace(token, function (m) { return nameFor(m) ? '' : m; }).trim();
      return;
    }
    var fragment = document.createDocumentFragment(), cursor = 0;
    matches.forEach(function (match) {
      fragment.appendChild(document.createTextNode(value.slice(cursor, match.index)));
      var svg = icon(nameFor(match[0]));
      svg.setAttribute('class', 'vs-pictogram');
      svg.dataset.vsPictogram = nameFor(match[0]);
      var source = document.createElementNS('http://www.w3.org/2000/svg', 'desc');
      source.setAttribute('class', 'vs-pictogram-source');
      source.textContent = match[0];
      svg.prepend(source);
      fragment.appendChild(svg);
      cursor = match.index + match[0].length;
    });
    fragment.appendChild(document.createTextNode(value.slice(cursor)));
    node.replaceWith(fragment);
  }
  function refresh(root) {
    if (!root || !root.isConnected) return;
    if (root.nodeType === 3) { decorate(root); return; }
    if (root.nodeType !== 1 || root.closest(excluded)) return;
    var walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
    var nodes = [], node;
    while ((node = walker.nextNode())) nodes.push(node);
    nodes.forEach(decorate);
  }
  function boot() {
    refresh(document.body);
    new MutationObserver(function (changes) {
      var roots = new Set();
      changes.forEach(function (change) {
        if (change.type === 'characterData') roots.add(change.target);
        else change.addedNodes.forEach(function (node) { roots.add(node); });
      });
      roots.forEach(refresh);
    }).observe(document.body, { childList: true, subtree: true, characterData: true });
  }
  window.VisablePictograms = { refresh: refresh, nameFor: nameFor };
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot);
  else boot();
})();
