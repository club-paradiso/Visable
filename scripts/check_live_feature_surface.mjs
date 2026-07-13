#!/usr/bin/env node
/**
 * Regression guard for the public Visable feature surface.
 *
 * This deliberately checks both a visible entry point and its implementation
 * hook. It prevents a design or landing-page rewrite from silently dropping a
 * major service while leaving dead code elsewhere in the repository.
 */
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..');
const read = (path) => readFileSync(join(ROOT, path), 'utf8');
const index = read('index.html');
const packageJson = JSON.parse(read('package.json'));

let failures = 0;
let checks = 0;
function ok(condition, label) {
  checks++;
  if (condition) console.log(`  PASS  ${label}`);
  else { failures++; console.log(`  FAIL  ${label}`); }
}

console.log('\n== Public feature entry points + implementation hooks');
const features = [
  {
    name: 'visa/status search',
    entry: /id="searchToggleBtn"[\s\S]{0,180}data-action="toggle-search"/,
    hook: /'toggle-search'\s*:/
  },
  {
    name: 'essential form helper',
    entry: /href="form-helper\.html"/,
    hook: /<title>[\s\S]*서류|form-helper\.html/
  },
  {
    name: 'HiKorea reservation helper',
    entry: /data-action="open-hikorea-guide"/,
    hook: /assets\/js\/hikorea-reservation-helper\.js/
  },
  {
    name: 'Waymaker',
    entry: /href="ai\.html"/,
    hook: /Waymaker by Paradiso/
  },
  {
    name: 'New Home nationality/citizenship hub',
    entry: /href="new-home\.html"/,
    hook: /id="gwNewHomeLink"/
  },
  {
    name: 'short-stay country route checker',
    entry: /data-action="open-short-stay"/,
    hook: /'open-short-stay'\s*:/
  },
  {
    name: 'occupation/industry code finder',
    entry: /data-action="open-jobcode-modal"/,
    hook: /'open-jobcode-modal'\s*:/
  },
  {
    name: 'jurisdiction office finder',
    entry: /data-action="open-jurisdiction-modal"/,
    hook: /'open-jurisdiction-modal'\s*:/
  },
  {
    name: 'registered immigration agent finder',
    entry: /data-action="open-agent-finder"/,
    hook: /'open-agent-finder'\s*:/
  },
  {
    name: 'Ministry-designated hospital finder',
    entry: /data-action="open-med-finder"/,
    hook: /'open-med-finder'\s*:/
  },
  {
    name: 'pre-entry / in-Korea procedure tracks',
    entry: /data-action="reveal-home-section"\s+data-target="visaManualSection"/,
    hook: /'reveal-home-section'\s*:/
  },
  {
    name: 'eight life pathways',
    entry: /data-action="reveal-home-section"\s+data-target="pathwaySection"/,
    hook: /id="pathwaySection"/
  },
  {
    name: 'stay deadline calculator and reminders',
    entry: /data-action="reveal-home-section"\s+data-target="reminderSection"/,
    hook: /id="reminderSection"/
  }
];

for (const feature of features) {
  ok(feature.entry.test(index), `${feature.name}: visible landing entry exists`);
  ok(feature.hook.test(index), `${feature.name}: implementation hook exists`);
}

console.log('\n== Restored HiKorea account preparation');
const hiKorea = read('assets/js/hikorea-reservation-helper.js');
ok(/data-prh-account-id/.test(hiKorea) && /validateHikoreaId/.test(hiKorea), 'ID creation guide + validator are shipped');
ok(/generateHikoreaPassword/.test(hiKorea) && /data-prh-action="generate-password"/.test(hiKorea), 'secure password generator is shipped');
ok(/data-prh-action="copy-password"/.test(hiKorea), 'generated password can be copied');
ok(/accounts\.google\.com\/signup/.test(hiKorea) && /nid\.naver\.com\/user2\/join\/agree/.test(hiKorea), 'email-account preparation links are shipped');
ok(/acctVerifyItems/.test(hiKorea), 'post-sign-up email verification checklist is shipped');

ok(packageJson.scripts && packageJson.scripts['test:feature-surface'] === 'node scripts/check_live_feature_surface.mjs',
  'feature-surface guard has an npm test alias');

console.log(`\n${failures ? 'FAIL' : 'OK'} — ${checks - failures}/${checks} checks passed`);
process.exit(failures ? 1 : 0);
