// @ts-check
/**
 * Rendering helpers (Phase 3): escaping for HTML text, attributes and regex. The text
 * escaper keeps the legacy DOM-based semantics (`&`, `<`, `>` only — not quotes), so moved
 * renderers produce byte-identical markup. `escapeAttr` is the attribute-safe variant the two
 * finders already used locally (`escapeText`); the Phase 3 escaping pass switches attribute
 * contexts to it one renderer at a time (candidates: docs/rebuild/phase3-structure-map.md §6).
 */

/** @param {unknown} s */
export function escapeHtml(s) {
  const d = document.createElement('div');
  d.textContent = /** @type {string} */ (s ?? '');
  return d.innerHTML;
}

/** @param {unknown} s */
export function escapeRegExp(s) {
  return String(s).replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

/**
 * Escape, then wrap each keyword match in <mark class="h">.
 * @param {unknown} t
 * @param {string[] | undefined} k
 */
export function hl(t, k) {
  const text = String(t ?? '');
  if (!k || !k.length) return escapeHtml(text);
  return escapeHtml(text).replace(new RegExp(`(${k.map(escapeRegExp).join('|')})`, 'gi'), '<mark class="h">$1</mark>');
}

/** Attribute-safe escaper: `& < > " '` (legacy `escapeText` of the finders). @param {unknown} s */
export function escapeAttr(s) {
  return String(s == null ? '' : s)
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
}
