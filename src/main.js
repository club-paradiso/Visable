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
import * as docs from './docs/normalize.js';
import * as procedurePanels from './render/cards/procedure-panels.js';
import * as boot from './boot.js';
import * as core from './core/helpers.js';
import * as detailResolver from './shims/detail-code-resolver.js';
import * as docSectionUnifier from './shims/doc-section-unification.js';
import * as docTermFeeUi from './shims/doc-term-fee-ui.js';
import './shims/global-settings.js';
import * as runtime from './i18n/runtime.js';
import * as modalsAi from './features/modals-ai.js';
import * as results from './search/results.js';
import * as fees from './render/cards/fees.js';
import * as docTabsEasyMode from './render/cards/doc-tabs-easy-mode.js';
import * as sections from './render/cards/sections.js';
import * as jurisdiction from './features/jurisdiction.js';
import * as jobcode from './features/jobcode.js';
import * as deadline from './features/deadline.js';
// Feature modules that run on load (moved legacy IIFEs); order follows their old document order.
import './features/landing-animation.js';
import './features/finders.js';
import './features/reminders.js';

const bridge = Object.freeze({
  version: 1,
  data: Object.freeze({ ...data, DATA_PATHS, API_ROUTES }),
  state: Object.freeze({ ...state }),
  render: Object.freeze({ ...render }),
  docs: Object.freeze({ ...docs }),
  // Result-card renderers, merged from one module per cluster (names are unique across the inline code).
  cards: Object.freeze({ ...procedurePanels, ...sections, ...docTabsEasyMode, ...fees }),
  search: Object.freeze({ ...results }),
  modals: Object.freeze({ ...modalsAi }),
  i18n: Object.freeze({ ...runtime }),
  boot: Object.freeze({ ...boot }),
  core: Object.freeze({ ...core }),
  // The three DOM-patching shims; index.html registers their install functions for DOMContentLoaded.
  shims: Object.freeze({ ...detailResolver, ...docSectionUnifier, ...docTermFeeUi }),
  features: Object.freeze({ jurisdiction: Object.freeze({ ...jurisdiction }), jobcode: Object.freeze({ ...jobcode }), deadline: Object.freeze({ ...deadline }) })
});

if (typeof window !== 'undefined') {
  // Defined once; later modules extend the bridge before this assignment, never after.
  Object.defineProperty(window, 'Visable', { value: bridge, writable: false, configurable: false, enumerable: false });
}

export default bridge;
