#!/usr/bin/env node
/**
 * check_nationality_services_data.mjs
 *
 * Offline, stdlib/Node-only validator for the 국적민원·귀화면접 준비 source
 * registry + guide dataset:
 *   - data/nationality_service_sources.json
 *   - data/nationality_service_guides.json
 *
 * Enforces the source-safety contract for the nationality services hub. Exits
 * non-zero on any failure. Run: node scripts/check_nationality_services_data.mjs
 */
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const readJson = (rel) => JSON.parse(fs.readFileSync(path.join(ROOT, rel), 'utf8'));

const failures = [];
let passes = 0;
const check = (label, condition, detail = '') => {
  if (condition) passes++;
  else failures.push(`${label}${detail ? `: ${detail}` : ''}`);
};

const sourcesDoc = readJson('data/nationality_service_sources.json');
const guidesDoc = readJson('data/nationality_service_guides.json');

const SOURCE_KINDS = new Set([
  'law', 'enforcement_decree', 'enforcement_rule', 'administrative_rule',
  'official_notice', 'official_policy_page', 'civil_affairs_guide',
  'evaluation_guide', 'local_notice', 'secondary_explainer'
]);
const OFFICIAL_LEVELS = new Set(['primary', 'secondary', 'local_notice', 'reference']);
const GUIDE_CATEGORIES = new Set([
  'naturalization_general', 'naturalization_simplified', 'naturalization_special',
  'naturalization_marriage', 'nationality_restoration', 'nationality_acquisition_report',
  'nationality_loss_report', 'nationality_renunciation', 'nationality_retention',
  'multiple_nationality', 'foreign_nationality_non_exercise_pledge', 'oath_and_certificate',
  'review_period_status', 'interview_review', 'kiip_evaluation'
]);
const SOURCE_CONFIDENCE = new Set(['high', 'medium', 'needs_review']);

// Official host allowlist (mirrors check_official_external_sources.mjs).
const OFFICIAL_HOSTS = new Set([
  'immigration.go.kr', 'mojminwon.moj.go.kr', 'hikorea.go.kr', 'socinet.go.kr',
  'kiiptest.org', 'moj.go.kr', 'law.go.kr', 'gwanbo.go.kr', 'easylaw.go.kr',
  'overseas.mofa.go.kr', 'visa.go.kr'
]);
const hostOf = (raw) => {
  try { return new URL(raw).hostname.replace(/^www\./, ''); } catch { return ''; }
};

// Heuristic: a short source-aware paraphrase should never approach copied-page
// length. Conservative ceiling guards against pasted long text from a source.
const COPIED_TEXT_CEILING = 600;

/* --------------------------------------------------------------- sources */
const sources = Array.isArray(sourcesDoc.sources) ? sourcesDoc.sources : [];
check('source registry is a non-empty array', sources.length > 0);

const sourceIds = new Set();
const SOURCE_REQUIRED = [
  'id', 'title_ko', 'publisher', 'source_kind', 'url', 'official_level',
  'topic_tags', 'nationality_categories', 'checked_at', 'summary_ko', 'caution_ko', 'use_in_ui'
];
for (const s of sources) {
  const label = s.id || '(missing id)';
  for (const field of SOURCE_REQUIRED) {
    const v = s[field];
    const empty = v == null || v === '' || (Array.isArray(v) && v.length === 0);
    // use_in_ui is a boolean — "false" is a valid value, not "missing".
    if (field === 'use_in_ui') check(`${label}.use_in_ui is boolean`, typeof v === 'boolean');
    else check(`${label} has required field "${field}"`, !empty);
  }
  check(`${label}.source_kind is valid`, SOURCE_KINDS.has(s.source_kind), s.source_kind);
  check(`${label}.official_level is valid`, OFFICIAL_LEVELS.has(s.official_level), s.official_level);
  check(`${label} has checked_at`, !!s.checked_at);
  check(`${label}.id is unique`, !sourceIds.has(s.id), s.id);
  sourceIds.add(s.id);

  // #11 primary sources must sit on an official host.
  if (s.official_level === 'primary') {
    check(`${label} primary source uses an official host`, OFFICIAL_HOSTS.has(hostOf(s.url)), s.url);
  }
  // #12 summary must be a short paraphrase, not copied long text.
  check(`${label}.summary_ko is a short paraphrase (no copied long text)`,
    typeof s.summary_ko === 'string' && s.summary_ko.length <= COPIED_TEXT_CEILING,
    `${(s.summary_ko || '').length} chars`);

  // #8 a local notice must never be framed as a universal rule.
  const isLocal = s.official_level === 'local_notice' || s.source_kind === 'local_notice';
  if (isLocal) {
    const blob = `${s.summary_ko || ''} ${s.caution_ko || ''}`;
    check(`${label} local notice is scoped, not universal`,
      /(지역|예시|일반화|한정|관서)/.test(blob) && !/전국\s*공통|보편\s*규칙|모든\s*경우/.test(s.summary_ko || ''));
    check(`${label} local notice carries a non-generalization caution`,
      /일반화|예시|우선/.test(s.caution_ko || ''));
  }
}

/* ---------------------------------------------------------------- guides */
const guides = Array.isArray(guidesDoc.guides) ? guidesDoc.guides : [];
check('guide dataset is a non-empty array', guides.length > 0);

const GUIDE_REQUIRED = [
  'id', 'category', 'title_ko', 'short_summary_ko', 'who_it_is_for_ko',
  'typical_flow_ko', 'key_documents_note_ko', 'related_laws', 'related_sources',
  'caution_ko', 'source_confidence', 'last_reviewed_at'
];
const guideIds = new Set();
const LAW_KINDS = new Set(['law', 'enforcement_decree', 'enforcement_rule', 'administrative_rule']);
const lawSourceIds = new Set(sources.filter((s) => LAW_KINDS.has(s.source_kind)).map((s) => s.id));

for (const g of guides) {
  const label = g.id || '(missing id)';
  for (const field of GUIDE_REQUIRED) {
    const v = g[field];
    const empty = v == null || v === '' || (Array.isArray(v) && v.length === 0 && field !== 'related_laws');
    if (field === 'related_laws') check(`${label} has related_laws array`, Array.isArray(v));
    else check(`${label} has required field "${field}"`, !empty);
  }
  check(`${label}.category is valid`, GUIDE_CATEGORIES.has(g.category), g.category);
  check(`${label}.source_confidence is valid`, SOURCE_CONFIDENCE.has(g.source_confidence), g.source_confidence);
  check(`${label} has caution text`, typeof g.caution_ko === 'string' && g.caution_ko.trim().length > 0);
  check(`${label} has last_reviewed_at`, !!g.last_reviewed_at);
  check(`${label}.id is unique`, !guideIds.has(g.id), g.id);
  guideIds.add(g.id);

  // #6 related_sources must resolve to real registry ids.
  for (const ref of g.related_sources || []) {
    check(`${label}.related_sources resolves: ${ref}`, sourceIds.has(ref));
  }
  // #7 related_laws must resolve to real law-kind registry ids.
  for (const ref of g.related_laws || []) {
    check(`${label}.related_laws resolves to a law source: ${ref}`, lawSourceIds.has(ref), ref);
  }
}

/* --------------------------------------------------------------- summary */
if (failures.length) {
  console.error(`Nationality-services data validation FAILED (${failures.length} issue(s)):`);
  for (const f of failures) console.error(`  ✗ ${f}`);
  process.exit(1);
}
console.log(`Nationality-services data validation passed: ${passes} checks, ${sources.length} sources, ${guides.length} guides.`);
process.exit(0);
