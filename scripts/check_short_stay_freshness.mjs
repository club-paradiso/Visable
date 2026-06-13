#!/usr/bin/env node
/*
 * check_short_stay_freshness.mjs
 * -----------------------------------------------------------------------------
 * Date-based freshness watch for the short-stay entry checker data.
 *
 * The official sources (law.go.kr, k-eta.go.kr, MOJ Jeju notice) cannot be
 * crawled from CI (HTTP 403), so this is a *date-based* monitor, not a content
 * diff. It flags:
 *   - any source whose `sourceDate` is older than STALE_DAYS (default 365)
 *   - the K-ETA temporary-exemption window (`ketaTemporaryExemption
 *     .lastVerifiedThrough`) when it is expired or within EXPIRY_WARN_DAYS
 *
 * Usage:
 *   node scripts/check_short_stay_freshness.mjs               # report to stdout
 *   node scripts/check_short_stay_freshness.mjs --report f.md # also write markdown
 *   node scripts/check_short_stay_freshness.mjs --json f.json # also write machine JSON
 *
 * Exit code: 0 = fresh, 1 = stale (so a scheduled workflow can branch on it).
 * The last stdout line is always `FRESHNESS: OK` or `FRESHNESS: STALE`.
 */
import { readFileSync, writeFileSync } from 'node:fs';
import { dirname, isAbsolute, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..');
const STALE_DAYS = Number(process.env.SHORT_STAY_STALE_DAYS || 365);
const EXPIRY_WARN_DAYS = Number(process.env.SHORT_STAY_EXPIRY_WARN_DAYS || 60);

const argReport = argValue('--report');
const argJson = argValue('--json');
function argValue(flag) {
  const i = process.argv.indexOf(flag);
  return i !== -1 && process.argv[i + 1] ? process.argv[i + 1] : null;
}

const readJson = (p) => JSON.parse(readFileSync(join(ROOT, p), 'utf8'));
const today = new Date();
const todayStr = today.toISOString().slice(0, 10);
const daysBetween = (a, b) => Math.floor((a.getTime() - b.getTime()) / 86400000);
const parseDate = (s) => (s && /^\d{4}-\d{2}-\d{2}$/.test(s) ? new Date(s + 'T00:00:00Z') : null);

const sources = readJson('data/short-stay/sources.json');
const rules = readJson('data/short-stay/rules.json');

const findings = [];

// 1. Per-source age.
for (const s of sources.sources || []) {
  const d = parseDate(s.sourceDate);
  if (!d) continue;
  const age = daysBetween(today, d);
  if (age > STALE_DAYS) {
    findings.push({
      kind: 'stale_source',
      id: s.id,
      title: s.title,
      sourceDate: s.sourceDate,
      ageDays: age,
      detail: `출처 기준일 ${s.sourceDate} (${age}일 경과, 임계값 ${STALE_DAYS}일) — 공식 원문 재확인 필요`
    });
  }
}

// 2. K-ETA temporary-exemption window.
const keta = (rules.rules && rules.rules.b21GeneralVisaFreeKeta && rules.rules.b21GeneralVisaFreeKeta.ketaTemporaryExemption) || {};
const through = parseDate(keta.lastVerifiedThrough);
if (through) {
  const daysLeft = daysBetween(through, today);
  if (daysLeft < 0) {
    findings.push({
      kind: 'keta_exemption_expired',
      detail: `K-ETA 한시 면제 종료일(${keta.lastVerifiedThrough})이 지났습니다 (${-daysLeft}일 경과). 연장·종료 여부를 공식 확인하고 데이터를 갱신하세요.`
    });
  } else if (daysLeft <= EXPIRY_WARN_DAYS) {
    findings.push({
      kind: 'keta_exemption_expiring',
      detail: `K-ETA 한시 면제 종료일(${keta.lastVerifiedThrough})까지 ${daysLeft}일 남았습니다. 연장 여부를 미리 공식 확인하세요.`
    });
  }
}

const stale = findings.length > 0;

// --- report -----------------------------------------------------------------
const lines = [];
lines.push('# Short-stay data freshness report');
lines.push('');
lines.push(`- 검사일: ${todayStr}`);
lines.push(`- sourceStatus: ${sources.sourceStatus}`);
lines.push(`- 임계값: 출처 ${STALE_DAYS}일 / 만료 경고 ${EXPIRY_WARN_DAYS}일`);
lines.push(`- 결과: ${stale ? '⚠️ STALE — 재확인 필요 항목 있음' : '✅ OK'}`);
lines.push('');
if (stale) {
  lines.push('| 종류 | 항목 | 상세 |');
  lines.push('| --- | --- | --- |');
  for (const f of findings) {
    lines.push(`| ${f.kind} | ${f.id || f.title || '—'} | ${f.detail} |`);
  }
  lines.push('');
  lines.push('갱신 방법: `audits/short-stay-country-checker/UPDATE_WORKFLOW.md` 참고.');
}
const report = lines.join('\n') + '\n';

const outPath = (p) => (isAbsolute(p) ? p : join(ROOT, p));
process.stdout.write(report);
if (argReport) writeFileSync(outPath(argReport), report);
if (argJson) writeFileSync(outPath(argJson), JSON.stringify({ checkedAt: todayStr, stale, findings }, null, 2) + '\n');

console.log(stale ? 'FRESHNESS: STALE' : 'FRESHNESS: OK');
process.exit(stale ? 1 : 0);
