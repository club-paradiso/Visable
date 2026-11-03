// Module entry for index.html (Phase 3 of the frontend rebuild, ADR-009).
//
// Modules extracted from the inline script land here and are exposed through ONE
// bridge object, `window.Visable`, which the remaining inline code delegates to.
// This runs as a module (deferred, before DOMContentLoaded), which is before every
// data load, storage read and render in the inline code (they all start in the
// DOMContentLoaded handler) — so delegation is safe. No other globals are added.
// @ts-check
import * as data from './data/fetch-json.js';
import { DATA_PATHS, API_ROUTES } from './data/paths.js';
import * as state from './state/storage.js';
import * as render from './render/escape.js';

const bridge = Object.freeze({
  version: 1,
  data: Object.freeze({ ...data, DATA_PATHS, API_ROUTES }),
  state: Object.freeze({ ...state }),
  render: Object.freeze({ ...render })
});

if (typeof window !== 'undefined') {
  // Defined once; later modules extend the bridge before this assignment, never after.
  Object.defineProperty(window, 'Visable', { value: bridge, writable: false, configurable: false, enumerable: false });
}

export default bridge;
