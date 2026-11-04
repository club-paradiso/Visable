// Compatibility surface of the legacy inline script in index.html (Phase 3, ADR-009).
// Top-level `let`/`const` bindings of a classic script live in the global lexical scope, so
// module code can read and assign them by bare name (they are NOT window properties).
// Top-level `function` declarations are window properties. Both are listed here so that
// `checkJs` can type-check modules that still reach into the inline code during the
// transition. Source of truth: docs/rebuild/phase3-structure-map.md §3. Trim entries as the
// owners move into modules.
declare let VISA_DATA: any[];
declare let dataReady: boolean;
declare let currentLanguage: string;
declare let selectedLocale: string;
declare let I18N_MANIFEST: any;
declare const UI_TRANSLATIONS: Record<string, any>;
declare const LANGUAGE_OPTIONS: Array<{ code: string; html: string; short: string; name: string; local: string; dir?: string }>;
declare const API_BASE: string;
declare const BOOTSTRAP_KO_FALLBACK: Record<string, any>;
declare function tx(key: string, vars?: Record<string, unknown>): string;
declare function txAt(locale: string, key: string, vars?: Record<string, unknown>): string;
declare function escapeHtml(s: unknown): string;
declare function showToast(message: string, type?: string): void;
declare function renderResults(query: string): void;
declare function executeSearch(...args: any[]): void;
declare function applyLanguage(code: string, options?: { silent?: boolean }): void;
declare function openVisaDrawer(code: string, ...rest: any[]): void;
declare function closeVisaDrawer(): void;
declare function openModal(id: string, ...rest: any[]): void;
declare function closeModal(id: string): void;
declare function initUI(): void;
declare function updateCategoryCounts(): void;
declare function setSearchEnabled(on: boolean): void;
declare function injectLocalData(records: any[]): any[];
declare function normalizeVisaCode(code: string): string;

interface Window {
  Visable: any;
  VisableBackend?: { origin(): string; url(path: string): string; productionOrigin?: string };
  PARADISO_BACKEND_URL?: string;
  ParadisoDocumentHelp?: any;
  ParadisoRoute?: any;
  ParadisoShortStay?: any;
  VisableReminderDialog?: any;
  VisableCivicSearch?: any;
  ParadisoUnifiedSearch?: any;
  ParadisoIndexFallback?: any;
  ParadisoReservationHelper?: any;
  ParadisoZhT?: any;
  EmploymentCodeAnalyzer?: any;
  EmploymentChecklist?: any;
  __paradisoDetailAliasData?: any[];
}
