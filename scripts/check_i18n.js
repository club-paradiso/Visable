#!/usr/bin/env node
'use strict';

const { spawnSync } = require('child_process');
const path = require('path');

const scripts = [
  'check_i18n_coverage.mjs',
  'check_index_hardcoded_text.mjs',
];

for (const script of scripts) {
  const result = spawnSync(process.execPath, [path.join(__dirname, script)], {
    stdio: 'inherit',
    env: process.env,
  });
  if (result.status !== 0) process.exit(result.status || 1);
}

console.log('[check_i18n] OK — static i18n coverage and index hardcoded-text scan passed');
