// Node-side loaders. Every expected value in the golden suite comes from a
// committed data file (data/i18n/*.json, visa_data.json,
// data/status-guidance-202609.json, ...) or from fixtures/guidance-strings.mjs,
// which records the strings the current site renders with their source lines.
// Nothing here invents content.
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..', '..', '..');
const cache = new Map();
export function readJson(rel) {
  if (!cache.has(rel)) cache.set(rel, JSON.parse(fs.readFileSync(path.join(ROOT, rel), 'utf8')));
  return cache.get(rel);
}

export const MANIFEST = readJson('data/i18n/manifest.json');
// 14 packs + zh-TW, which renders the zh-CN pack through assets/js/zh-traditional.js
// (data/i18n/manifest.json "policy"). The language dialog lists all 15.
export const LOCALES = [...MANIFEST.supportedLocales, 'zh-TW'];
export const RTL = new Set(['ar']);
export function pack(locale) {
  const file = locale === 'zh-TW' ? 'zh-CN' : locale;
  return readJson(`data/i18n/${MANIFEST.files?.[file] || file + '.json'}`);
}
export const stripTags = (s) => String(s || '').replace(/<[^>]+>/g, '');
export const localeLabel = (locale) => MANIFEST.localeLabels[locale];

export const VISA_DATA = readJson('visa_data.json');
export const visaRecord = (code) => VISA_DATA.find((v) => v && v.code === code) || null;
export function subcodeRecord(code) {
  for (const v of VISA_DATA) for (const s of v.subCodes || []) if (s.code === code) return { parent: v, sub: s };
  return null;
}
export const VISA_NAMES = readJson('data/i18n/visa-names.json').names;

export const GUIDANCE = readJson('data/status-guidance-202609.json');
export const STAY_EDITION = GUIDANCE.sources.stay_manual_2026_11_02; // { edition: '2026.11', date: '2026-11-02', ... }
export const guidanceEntry = (target, procedure) => GUIDANCE.guidance.find((e) => e.target === target && e.procedure === procedure) || null;
export const commonProcedure = (procedure) => GUIDANCE.guidance.find((e) => e.procedure === procedure && (e.target == null || e.target === 'COMMON')) || null;
export const fee = (id) => GUIDANCE.fees.find((f) => f.id === id) || null;
// Renderer rule (assets/js/status-guidance.js:600): a document with ref === 'fee' is
// not rendered in the document list; it feeds the fee section instead.
export const renderedDocs = (entry) => (entry?.documents || []).filter((d) => d.ref !== 'fee');
export const docsByLevel = (entry, level) => renderedDocs(entry).filter((d) => d.requirement_level === level);
export const won = (n) => '₩' + Number(n).toLocaleString('en-US');

export const FORMS = readJson('data/form_definitions.json');
export const MANUAL_CATALOG = readJson('data/manual-reader/catalog.json');
export const CHECKLIST_EXTENSION = readJson('data/immigration-checklists/extension-202609.json');
export const NATIONALITY_CONTENT = readJson('data/nationality_content.json');
