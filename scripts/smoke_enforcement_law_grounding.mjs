// Live smoke for enforcement law grounding (network-dependent — NOT part
// of the blocking CI suite). Hits the real law.go.kr endpoints with a
// synthetic non-secret credential so the DRF path fails registration and
// the public-endpoint transport must carry the verification.
//
//   node scripts/smoke_enforcement_law_grounding.mjs
//
// Expected: a current-version case with exact violation dates reaches
// lawGrounding status VERIFIED (act article + rule Art. 86 + Annex 7 with
// the live PDF hash matching the stored official snapshot).
import { createRequire } from 'node:module';
const require = createRequire(import.meta.url);

process.env.LAW_API_OC = process.env.LAW_API_OC || 'SYNTHETIC_NON_SECRET_SMOKE';
process.env.LAW_GROUNDING_MODE = 'enabled';
const { groundOfficialLaw } = require('../lib/enforcement-law-grounding.js');

const result = await groundOfficialLaw({
  violationCode: 'UNAUTHORIZED_WORKPLACE_CHANGE_ART21_1',
  violationStartDate: '2026-10-24',
  violationEndDate: '2026-11-03',
}, { status: 'AVAILABLE' });

console.log('status:', result.status);
console.log('temporal:', JSON.stringify(result.temporalVerification));
console.log('evidence:', result.evidence.map((item) => item.id));
console.log('limitations:', result.limitations);
if (result.status !== 'VERIFIED') {
  console.error('SMOKE FAILED: expected VERIFIED for a current-version case');
  process.exit(1);
}
console.log('Live law grounding smoke passed');
