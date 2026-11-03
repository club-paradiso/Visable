// @ts-check
/**
 * State layer (Phase 3): the single owner of every localStorage key the index page uses.
 * Key strings are exactly the legacy ones — returning users keep their language, theme,
 * reminders and checklists (no renames, no migration needed; a `migrate()` hook exists for
 * the day a key has to change). Every access is guarded like the inline code was: storage
 * can throw in private windows or when blocked, and the page must keep working.
 *
 * Keys and their legacy owners: docs/rebuild/phase3-structure-map.md §5 and
 * phase0-inventory.md §B. Shared with other pages/scripts: language, brightness,
 * editorial-theme, easyMode (civic-search.js, ai.html, new-home.html, visable-theme.js).
 */

export const KEYS = Object.freeze({
  language: 'paradiso:language',
  brightness: 'paradiso:brightness',
  editorialTheme: 'paradiso:editorial-theme',
  easyMode: 'paradiso:easyMode',
  i18nDebug: 'paradiso:i18n-debug',
  city: 'paradiso_city',
  devDiagnostics: 'paradisoDevDiagnostics',
  reminders: 'paradisoReminders',
  reminderBannerDismiss: 'paradisoReminderBannerDismiss',
  hikoreaStepsDone: 'paradiso_hikorea_steps_done',
  scenarioChecklistPrefix: 'paradiso:scenario-checklist:'
});

/** @param {string} key @returns {string | null} */
export function read(key) {
  try { return localStorage.getItem(key); } catch (_) { return null; }
}

/** @param {string} key @param {string} value @returns {boolean} true when stored */
export function write(key, value) {
  try { localStorage.setItem(key, value); return true; } catch (_) { return false; }
}

/** @param {string} key @returns {boolean} */
export function remove(key) {
  try { localStorage.removeItem(key); return true; } catch (_) { return false; }
}

/**
 * Parse a JSON value; a missing or corrupt entry yields `fallback` (never throws).
 * @template T
 * @param {string} key
 * @param {T} fallback
 * @returns {T}
 */
export function readJson(key, fallback) {
  const raw = read(key);
  if (raw == null) return fallback;
  try { return /** @type {T} */ (JSON.parse(raw)); } catch (_) { return fallback; }
}

/** @param {string} key @param {unknown} value */
export function writeJson(key, value) {
  return write(key, JSON.stringify(value));
}

/**
 * All stored keys that start with a prefix (used by the scenario-checklist reset).
 * @param {string} prefix
 * @returns {string[]}
 */
export function keysWithPrefix(prefix) {
  const out = [];
  try {
    for (let i = 0; i < localStorage.length; i += 1) {
      const k = localStorage.key(i);
      if (k && k.startsWith(prefix)) out.push(k);
    }
  } catch (_) { /* storage blocked: nothing to list */ }
  return out;
}

/**
 * Key migrations for returning users. Nothing is renamed today; this is the one place a
 * rename would be implemented (copy old → new, keep the old value until a later release).
 */
export function migrate() {
  return { migrated: [] };
}
