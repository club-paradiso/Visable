#!/usr/bin/env node
// Reuse the existing B2 vocabulary, not benchmark questions or labels.
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const root = path.resolve(__dirname, '..');
const router = require(path.join(root, 'assets/js/search-router.js'));
const bundle = JSON.parse(fs.readFileSync(path.join(root, 'data/status-guidance-202609.json'), 'utf8'));
const sources = {
  'assets/js/search-router.js': fs.readFileSync(path.join(root,'assets/js/search-router.js')),
  'data/status-guidance-202609.json#procedures': JSON.stringify(bundle.procedures),
};
const result = {
  schema_version: 'procedure-vocabulary/1',
  provenance: 'Repository B2 procedure catalog and object/action lexicons; no evaluation labels.',
  sources: Object.fromEntries(Object.entries(sources).map(([p,content]) => [p, crypto.createHash('sha256').update(content).digest('hex')])),
  procedures: bundle.procedures.map(p => ({id:p.id, keywords:p.keywords})),
  objects: router.OBJECTS,
  actions: router.ACTIONS,
};
const output = JSON.stringify(result, null, 2) + '\n';
const target = path.join(root,'backend/data/procedure_classifier_lexicon.json');
if (process.argv.includes('--check')) {
  if (fs.readFileSync(target,'utf8') !== output) throw new Error('procedure vocabulary is stale; run builder');
} else fs.writeFileSync(target,output);
