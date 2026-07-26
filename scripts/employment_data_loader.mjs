/*
 * employment_data_loader.mjs — Node-side loader that assembles every input the
 * employment-code analyzer needs from the data/employment/* files, so the CLI
 * and the regression tests build the analyzer the exact same way.
 *
 * The browser builds the equivalent bundle via fetch() in index.html.
 */
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');
const readJson = (p) => JSON.parse(readFileSync(join(root, p), 'utf8'));
const concepts = (obj) => (obj && Array.isArray(obj.concepts) ? obj.concepts : []);

/** Returns deps ready for createEmploymentAnalyzer({ ...deps }). */
export function loadEmploymentAnalyzerDeps() {
  const data = readJson('data/jobcode_master.json');

  // Base aliases + entertainment + tattoo, merged per locale.
  const ko = {
    concepts: [
      ...concepts(readJson('data/employment/synonyms.ko.json')),
      ...concepts(readJson('data/employment/aliases.entertainment.ko.json')),
      ...concepts(readJson('data/employment/aliases.tattoo.ko.json'))
    ]
  };
  const en = {
    concepts: [
      ...concepts(readJson('data/employment/synonyms.en.json')),
      ...concepts(readJson('data/employment/aliases.entertainment.en.json')),
      ...concepts(readJson('data/employment/aliases.tattoo.en.json'))
    ]
  };
  // Chinese pool: Chinese-speaking residents describe their work in Chinese, and
  // without this the analyzer returned nothing at all for those inputs. It adds
  // retrieval surfaces only — the codes still come from jobcode_master.json.
  const zh = { concepts: concepts(readJson('data/employment/synonyms.zh.json')) };

  const ambiguous = readJson('data/employment/ambiguous_inputs.json');
  const sources = readJson('data/employment/classification_sources.json');

  // Field-labor place/object/action/tool lexicon (장소 + 대상 + 작업) + fork
  // disambiguation rules + income-bracket reminder. Optional, but loaded by
  // default so the CLI and tests build the analyzer exactly like the browser.
  const fieldTerms = {
    ko: readJson('data/employment/colloquial_field_terms_ko.json'),
    en: readJson('data/employment/colloquial_field_terms_en.json')
  };
  const disambiguation = readJson('data/employment/disambiguation_rules.json');
  const incomeBrackets = readJson('data/employment/income_brackets.json');

  return {
    data,
    lexicon: { ko, en, zh },
    ambiguous,
    sources,
    legalSources: sources.legal_sources || [],
    context: data.employment_reporting_context,
    fieldTerms,
    disambiguation,
    incomeBrackets
  };
}
