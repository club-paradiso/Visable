#!/usr/bin/env node
/**
 * update_short_stay_rules.mjs
 *
 * Rebuilds data/short-stay/rules.json + data/short-stay/sources.json from the
 * official-source fixtures under data/short-stay/fixtures/ so that future
 * official-list refreshes never require editing index.html.
 *
 * Modes:
 *   node scripts/update_short_stay_rules.mjs                 # try live fetch, fall back to fixtures
 *   node scripts/update_short_stay_rules.mjs --from-fixtures # fixtures only (no network)
 *
 * Live fetch is best-effort: when the official K-ETA / MOJ pages cannot be
 * reached (offline CI, blocked network), the script seeds from fixtures and
 * marks sourceStatus = "needs_refresh" so the UI shows the official-refresh
 * warning. Network availability is NEVER required for normal validation.
 *
 * Outputs:
 *   data/short-stay/rules.json
 *   data/short-stay/sources.json
 *   audits/short-stay-country-checker/update_report.md
 *   audits/short-stay-country-checker/source_diff.json
 */
import { readFileSync, writeFileSync, existsSync, mkdirSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..');
const FIXTURE_DIR = join(ROOT, 'data', 'short-stay', 'fixtures');
const OUT_RULES = join(ROOT, 'data', 'short-stay', 'rules.json');
const OUT_SOURCES = join(ROOT, 'data', 'short-stay', 'sources.json');
const AUDIT_DIR = join(ROOT, 'audits', 'short-stay-country-checker');

const FROM_FIXTURES = process.argv.includes('--from-fixtures');

const readJson = (p) => JSON.parse(readFileSync(p, 'utf8'));
const sha256 = (p) => createHash('sha256').update(readFileSync(p)).digest('hex').slice(0, 16);

// --- 1. Optional live fetch (best effort; never blocks) ---------------------
async function tryLiveFetch() {
  if (FROM_FIXTURES) return { ok: false, reason: '--from-fixtures flag' };
  try {
    const ctrl = new AbortController();
    const t = setTimeout(() => ctrl.abort(), 8000);
    const res = await fetch('https://www.k-eta.go.kr/portal/apply/index.do', { signal: ctrl.signal });
    clearTimeout(t);
    if (!res.ok) return { ok: false, reason: `K-ETA portal HTTP ${res.status}` };
    // A real parser for the official page would go here. Until the page
    // structure is verified by a maintainer, a reachable page alone is NOT
    // treated as a verified source refresh.
    return { ok: false, reason: 'live page reachable but parser not yet certified — keeping fixture seed' };
  } catch (e) {
    return { ok: false, reason: `network unavailable (${e.name || 'error'})` };
  }
}

// --- 2. Load fixtures --------------------------------------------------------
const idx = readJson(join(FIXTURE_DIR, 'country_index.json')).countries;
const fxB1 = readJson(join(FIXTURE_DIR, 'b1_visa_waiver.json'));
const fxB21 = readJson(join(FIXTURE_DIR, 'b21_general_visa_free.json'));
const fxJeju = readJson(join(FIXTURE_DIR, 'jeju_b22_notice.json'));
const fxKeta = readJson(join(FIXTURE_DIR, 'keta_program.json'));
const fxC3 = readJson(join(FIXTURE_DIR, 'c3_fallback.json'));

const fail = (msg) => { console.error(`[update_short_stay_rules] ERROR: ${msg}`); process.exit(1); };

function isoOf(nameKo) {
  const hit = idx[nameKo];
  if (!hit) fail(`country_index.json is missing "${nameKo}" — add it before regenerating`);
  return hit.iso2;
}

// --- 3. Assemble per-country records ----------------------------------------
const countries = {};
function ensureCountry(nameKo) {
  const iso2 = isoOf(nameKo);
  if (!countries[iso2]) {
    const meta = idx[nameKo];
    countries[iso2] = {
      iso2,
      iso3: meta.iso3 || null,
      nameKo,
      nameEn: meta.nameEn,
      aliasesKo: [nameKo, ...(meta.aliases || []).filter(a => /[가-힣]/.test(a))],
      aliasesEn: [meta.nameEn, ...(meta.aliases || []).filter(a => !/[가-힣]/.test(a))],
      ordinaryPassport: true,
      diplomaticPassport: 'unknown',
      officialPassport: 'unknown',
      servicePassport: 'unknown',
      specialPassport: 'unknown',
      b1: { ordinaryEligible: false },
      b21: { listed: false },
      b22Jeju: {
        jejuEntryDenied: false,
        jejuStayDays: fxJeju.jejuStayDays,
        mainlandMovement: 'unknown',
        stayAreaExpansionPermitRequired: false,
        passportScope: 'unknown',
        sourceRefs: ['moj_jeju_notice_2022_189', 'mofa_jeju_notice_copy_2023_09_18']
      },
      c3Fallback: true,
      keta: null,
      sourceRefs: [],
      notes: []
    };
  }
  return countries[iso2];
}

// B-1 ordinary
for (const row of fxB1.ordinaryPassportCountries) {
  const c = ensureCountry(row.nameKo);
  c.b1 = { ordinaryEligible: true, stay: row.stay, stayNote: row.stayNote || null, suspended: false };
  c.sourceRefs.push('visa_manual_2026_05_b1_b2_c3');
}
// B-1 suspended
for (const row of fxB1.suspendedOrdinaryCountries) {
  const c = ensureCountry(row.nameKo);
  c.b1 = { ordinaryEligible: false, stay: row.stay, suspended: true, suspensionNote: row.suspensionNote };
  c.sourceRefs.push('visa_manual_2026_05_b1_b2_c3');
  c.notes.push(`B-1 협정은 유효하나 일반여권 적용 일시정지: ${row.suspensionNote}`);
}
// B-1 diplomatic/official-only examples
for (const row of fxB1.diplomaticOfficialOnlyExamples) {
  const c = ensureCountry(row.nameKo);
  if (!c.b1.ordinaryEligible) {
    c.b1.diplomaticOfficialOnly = true;
    c.b1.diplomaticOfficialScope = row.passportScope;
    c.b1.diplomaticOfficialStay = row.stay;
    c.diplomaticPassport = true;
    if (/관용/.test(row.passportScope)) c.officialPassport = true;
  }
  c.sourceRefs.push('visa_manual_2026_05_b1_b2_c3');
}
// B-2-1 general visa-free
for (const group of fxB21.stayGroups) {
  for (const nameKo of group.countriesKo) {
    const c = ensureCountry(nameKo);
    c.b21 = { listed: true, stay: group.stay };
    c.sourceRefs.push('visa_manual_2026_05_b1_b2_c3');
  }
}
for (const row of fxB21.revokedCountries) {
  const c = ensureCountry(row.nameKo);
  c.b21 = { listed: false, revoked: true, revokedDate: row.revokedDate };
  c.notes.push(`일반 무사증(B-2) 지정취소: ${row.revokedDate}`);
}
for (const row of fxB21.conflicts || []) {
  const c = ensureCountry(row.nameKo);
  c.notes.push(`B-2-1 체류기간 출처 불일치: ${row.manualValue} vs ${row.storedValue} → ${row.adopted} 채택, 공식 재확인 필요`);
}

// Jeju entry-denied
for (const nameKo of fxJeju.entryDeniedCountriesKo) {
  const c = ensureCountry(nameKo);
  c.b22Jeju.jejuEntryDenied = true;
  c.b22Jeju.mainlandMovement = 'not_allowed_by_default';
}
for (const row of fxJeju.entryDeniedConflicts || []) {
  const c = ensureCountry(row.nameKo);
  c.b22Jeju.jejuEntryDenied = true;
  c.b22Jeju.mainlandMovement = 'not_allowed_by_default';
  c.b22Jeju.conflictNote = row.reason;
  c.b22Jeju.sourceRefs = [...c.b22Jeju.sourceRefs, row.conflictSourceId];
  c.notes.push(`제주 무사증 입국불허 목록 출처 불일치 — ${row.reason}`);
}
// Jeju stay-area expansion permit groups
const exp = fxJeju.stayAreaExpansionPermit;
const applyExpansion = (names, scope) => {
  for (const nameKo of names) {
    const c = ensureCountry(nameKo);
    if (c.b22Jeju.jejuEntryDenied) continue; // denial wins
    c.b22Jeju.stayAreaExpansionPermitRequired = true;
    c.b22Jeju.mainlandMovement = 'requires_stay_area_expansion_permit';
    c.b22Jeju.passportScope = scope;
  }
};
applyExpansion(exp.allPassports, 'all');
applyExpansion(exp.officialOrdinaryPassports, 'official_ordinary');
applyExpansion(exp.ordinaryPassports, 'ordinary');

// K-ETA derivation: eligible = has a visa-free path (B-1 ordinary or B-2-1)
const ketaExempt = new Set(fxKeta.temporaryExemption.countriesKo.map(isoOf));
for (const c of Object.values(countries)) {
  const visaFree = c.b1.ordinaryEligible || c.b21.listed;
  c.keta = {
    eligible: visaFree,
    allowedStay: c.b21.listed ? c.b21.stay : (c.b1.ordinaryEligible ? c.b1.stay : null),
    applicationRequiredUnlessExempt: visaFree,
    temporaryExemption: ketaExempt.has(c.iso2),
    feeKRW: fxKeta.program.feeKRW,
    notVisa: true,
    entryNotGuaranteed: true
  };
  if (!c.b22Jeju.jejuEntryDenied && !c.b22Jeju.stayAreaExpansionPermitRequired) {
    c.b22Jeju.mainlandMovement = visaFree ? 'general_visa_free_path_available' : 'unknown';
  }
  c.sourceRefs = [...new Set(c.sourceRefs)];
}

// --- 4. Alias map -------------------------------------------------------------
const normalizeAlias = (s) => String(s).toLowerCase().normalize('NFC').replace(/[\s\-–—'’.()]/g, '');
const aliases = {};
for (const c of Object.values(countries)) {
  for (const a of [...c.aliasesKo, ...c.aliasesEn, c.iso2]) {
    const key = normalizeAlias(a);
    if (!key) continue;
    if (aliases[key] && aliases[key] !== c.iso2) fail(`alias collision: "${a}" → ${aliases[key]} vs ${c.iso2}`);
    aliases[key] = c.iso2;
  }
}

// --- 5. Top-level rules block --------------------------------------------------
const fetchResult = await tryLiveFetch();
const sourceStatus = fetchResult.ok ? 'verified' : 'needs_refresh';
const today = new Date().toISOString().slice(0, 10);

const rules = {
  schemaVersion: 1,
  lastUpdated: today,
  generatedAt: new Date().toISOString().replace(/\.\d{3}Z$/, 'Z'),
  sourceStatus,
  sourceStatusReason: fetchResult.ok ? 'official pages fetched' : `seeded from stored fixtures — ${fetchResult.reason}`,
  countries,
  aliases,
  rules: {
    b1VisaWaiverAgreement: {
      basis: '출입국관리법 제7조 제2항 제2호 · 시행령 별표1 사증면제(B-1)',
      tableBasisDate: fxB1.tableBasisDate,
      storedListDate: fxB1.sourceDate,
      activityNote: fxB1.activityNote,
      ordinaryCount: fxB1.ordinaryPassportCountries.length,
      suspendedCount: fxB1.suspendedOrdinaryCountries.length,
      sourceRefs: ['law_immigration_enforcement_decree_table_1', 'visa_manual_2026_05_b1_b2_c3']
    },
    b21GeneralVisaFreeKeta: {
      basis: '출입국관리법 제7조 제2항 제3호 · 시행령 별표1 관광·통과(B-2) — 법무부장관 지정 무사증입국 허가대상',
      tableBasisDate: fxB21.tableBasisDate,
      storedListDate: fxB21.sourceDate,
      separateFromJeju: true,
      ketaProgram: fxKeta.program,
      ketaTemporaryExemption: {
        lastVerifiedThrough: fxKeta.temporaryExemption.lastVerifiedThrough,
        extensionUnverified: fxKeta.temporaryExemption.extensionUnverified,
        countriesIso2: [...ketaExempt].sort()
      },
      sourceRefs: ['law_immigration_enforcement_decree_table_1', 'visa_manual_2026_05_b1_b2_c3', 'k_eta_eligible_countries']
    },
    b22JejuVisaFree: {
      basis: '제주특별자치도 무사증입국 (법무부고시 제2022-189호 사본 기준)',
      noticeNo: fxJeju.noticeNo,
      effectiveDate: fxJeju.effectiveDate,
      copyDate: fxJeju.copyDate,
      jejuStayDays: fxJeju.jejuStayDays,
      separateFromGeneralVisaFree: true,
      entryDeniedCount: fxJeju.entryDeniedCountriesKo.length,
      entryDeniedConflictCount: (fxJeju.entryDeniedConflicts || []).length,
      expansionPermitCounts: {
        all: exp.allPassports.length,
        officialOrdinary: exp.officialOrdinaryPassports.length,
        ordinary: exp.ordinaryPassports.length
      },
      sourceRefs: ['moj_jeju_notice_2022_189', 'mofa_jeju_notice_copy_2023_09_18']
    },
    c3Fallback: {
      basis: '출입국관리법 시행령 별표1 단기방문(C-3) — 90일 이내, 영리활동 불가',
      purposeMap: fxC3.purposeMap,
      sourceRefs: ['law_immigration_enforcement_decree_table_1', 'visa_manual_2026_05_b1_b2_c3']
    },
    stayExtensionWarning: {
      basis: '2026.5 사증발급/체류 안내매뉴얼 — B-1·B-2 공통',
      text: '사증면제(B-1)·관광통과(B-2)로 입국한 경우 원칙적으로 체류기간 연장이나 체류자격 변경이 허용되지 않습니다. 허용 기간을 초과해 체류하려면 사증을 발급받아 입국해야 합니다.',
      sourceRefs: ['stay_manual_2026_05_b1_b2_extension_change', 'visa_manual_2026_05_b1_b2_c3']
    }
  }
};

// --- 6. sources.json ------------------------------------------------------------
const fixtureHash = (f) => sha256(join(FIXTURE_DIR, f));
const sources = {
  schemaVersion: 1,
  generatedAt: rules.generatedAt,
  sourceStatus,
  sources: [
    {
      id: 'law_immigration_enforcement_decree_table_1',
      type: 'law',
      title: '출입국관리법 시행령 별표1 (사증면제 B-1 · 관광통과 B-2 · 단기방문 C-3)',
      url: 'https://www.law.go.kr/법령/출입국관리법시행령',
      localPath: null,
      retrievedAt: null,
      effectiveDate: null,
      sourceDate: '2026-05-21',
      hash: null,
      scope: 'B-1/B-2/C-3 법적 분류 근거',
      confidence: 'high',
      notes: '법령 본문은 매뉴얼 인용으로 확인(visa_hwp_full.txt 내 출입국관리법 제7조 인용). 실시간 법령 조회는 이 세션에서 불가.'
    },
    {
      id: 'visa_manual_2026_05_b1_b2_c3',
      type: 'official_manual',
      title: '2026.5 사증발급 안내매뉴얼 (B-1 협정 일람표 2022-09-22 기준 · B-2 무사증 일람표 · C-3 세부약호)',
      url: null,
      localPath: 'docs/data/claude_opus_manual_extraction_2026_05/visa_hwp_full.txt',
      retrievedAt: today,
      effectiveDate: '2026-05-21',
      sourceDate: '2026-05-21',
      hash: fixtureHash('b1_visa_waiver.json'),
      scope: 'B-1 협정국·B-2-1 무사증국·C-3 분류',
      confidence: 'high',
      notes: 'B-1 일반여권 67개국 목록은 저장 데이터 기준일 2024-12-04, B-2-1 목록은 2022-11-01. 아르헨티나 체류기간 출처 불일치(30일 vs 90일) 기록됨.'
    },
    {
      id: 'stay_manual_2026_05_b1_b2_extension_change',
      type: 'official_manual',
      title: '2026.6.1 외국인체류 안내매뉴얼 — B-1/B-2 체류기간 연장·자격변경 원칙 불허 경고',
      url: null,
      localPath: 'docs/data/claude_opus_manual_extraction_2026_05/stay_hwp_full.txt',
      retrievedAt: today,
      effectiveDate: '2026-06-01',
      sourceDate: '2026-06-01',
      hash: null,
      scope: 'B-1/B-2 입국 후 연장·변경 제한 경고',
      confidence: 'high',
      notes: '단기 체류자격 연장/변경 원칙 불허 문구의 근거.'
    },
    {
      id: 'k_eta_eligible_countries',
      type: 'official_web',
      title: 'K-ETA 공식 누리집 — 적용 대상 국가·수수료·면제 안내',
      url: 'https://www.k-eta.go.kr',
      localPath: 'data/short-stay/fixtures/keta_program.json',
      retrievedAt: null,
      effectiveDate: null,
      sourceDate: fxKeta.lastVerified,
      hash: fixtureHash('keta_program.json'),
      scope: 'K-ETA 제도(비자 아님)·수수료·한시 면제국',
      confidence: 'medium',
      notes: '제도 세부(수수료·유효기간)는 실시간 조회 불가로 저장 사본 기준(medium). K-ETA 한시 면제 2026-12-31 연장은 2026-06-13 외부 공식 출처(법무부·재외공관 K-ETA 면제 연장 공지)로 교차확인됨.',
      crossCheckedAt: '2026-06-13',
      crossCheckUrls: [
        'https://www.mofa.go.kr/ca-en/brd/m_5231/view.do?seq=761797',
        'https://english.visitkorea.or.kr/svc/contents/contentsView.do?vcontsId=251923'
      ]
    },
    {
      id: 'moj_jeju_notice_2022_189',
      type: 'official_notice',
      title: '법무부고시 제2022-189호 — 제주특별자치도 무사증입국 불허국가 및 체류지역 확대허가 국가',
      url: null,
      localPath: 'data/short-stay/fixtures/jeju_b22_notice.json',
      retrievedAt: null,
      effectiveDate: fxJeju.effectiveDate,
      sourceDate: fxJeju.effectiveDate,
      hash: fixtureHash('jeju_b22_notice.json'),
      scope: 'B-2-2 제주 무사증 입국불허·체류지역 확대허가 국가군',
      confidence: 'medium',
      notes: '고시 원문 실시간 확인 불가 — 저장 사본 기준. 이란 포함 여부 출처 간 불일치 기록됨.'
    },
    {
      id: 'mofa_jeju_notice_copy_2023_09_18',
      type: 'official_mission_copy',
      title: '외교부/재외공관 게시 제주 무사증 고시 사본 (2023-09-18)',
      url: null,
      localPath: 'data/short-stay/fixtures/jeju_b22_notice.json',
      retrievedAt: null,
      effectiveDate: fxJeju.effectiveDate,
      sourceDate: fxJeju.copyDate,
      hash: fixtureHash('jeju_b22_notice.json'),
      scope: 'B-2-2 고시 사본(국가군 3그룹 34/1/29)',
      confidence: 'medium',
      notes: '재외공관 게시 사본 기준일 2023-09-18.'
    },
    {
      id: 'paradiso_visa_data_b22_subcode_2026_05',
      type: 'internal_stored_copy',
      title: 'Paradiso visa_data.json B-2-2 서브코드 저장 사본 (제외국 23개국 — 이란 포함)',
      url: null,
      localPath: 'visa_data.json',
      retrievedAt: today,
      effectiveDate: null,
      sourceDate: '2026-05-21',
      hash: null,
      scope: '이란 입국불허 충돌 기록 전용',
      confidence: 'medium',
      notes: '고시 사본(22개국)과 불일치 — 안전 우선으로 이란을 입국불허로 유지. 공식 재확인 필요.'
    }
  ]
};

// --- 7. Diff + write -------------------------------------------------------------
let diff = { previous: null, changes: ['initial generation'] };
if (existsSync(OUT_RULES)) {
  try {
    const prev = readJson(OUT_RULES);
    const prevIso = new Set(Object.keys(prev.countries || {}));
    const nowIso = new Set(Object.keys(countries));
    const added = [...nowIso].filter(k => !prevIso.has(k));
    const removed = [...prevIso].filter(k => !nowIso.has(k));
    const changed = [...nowIso].filter(k => prevIso.has(k) &&
      JSON.stringify(prev.countries[k]) !== JSON.stringify(countries[k]));
    diff = {
      previous: { lastUpdated: prev.lastUpdated, sourceStatus: prev.sourceStatus, countryCount: prevIso.size },
      changes: { addedCountries: added, removedCountries: removed, changedCountries: changed }
    };
  } catch { /* keep initial diff */ }
}

// Compact source catalogue so the UI can show readable per-answer citations
// (제목 + 기준일 + 신뢰도) without a second fetch of sources.json.
rules.sourceCatalog = sources.sources.map(function (s) {
  return { id: s.id, title: s.title, sourceDate: s.sourceDate, confidence: s.confidence };
});

mkdirSync(AUDIT_DIR, { recursive: true });
writeFileSync(OUT_RULES, JSON.stringify(rules, null, 2) + '\n');
writeFileSync(OUT_SOURCES, JSON.stringify(sources, null, 2) + '\n');
writeFileSync(join(AUDIT_DIR, 'source_diff.json'), JSON.stringify(diff, null, 2) + '\n');

const report = `# Short-stay rules update report

- Generated: ${rules.generatedAt}
- Mode: ${FROM_FIXTURES ? '--from-fixtures' : 'auto (live fetch attempted)'}
- Live fetch result: ${fetchResult.ok ? 'OK' : `not used — ${fetchResult.reason}`}
- sourceStatus: **${sourceStatus}**
- Countries in rules.json: ${Object.keys(countries).length}
- Aliases indexed: ${Object.keys(aliases).length}
- B-1 ordinary: ${rules.rules.b1VisaWaiverAgreement.ordinaryCount} (+${rules.rules.b1VisaWaiverAgreement.suspendedCount} suspended)
- B-2-1 listed: ${Object.values(countries).filter(c => c.b21.listed).length}
- Jeju entry-denied: ${rules.rules.b22JejuVisaFree.entryDeniedCount} (+${rules.rules.b22JejuVisaFree.entryDeniedConflictCount} conflict-flagged)
- Stay-area expansion permit: all=${exp.allPassports.length}, official/ordinary=${exp.officialOrdinaryPassports.length}, ordinary=${exp.ordinaryPassports.length}
- Vietnam (VN): b1.ordinaryEligible=${countries.VN.b1.ordinaryEligible}, b21.listed=${countries.VN.b21.listed}, jejuEntryDenied=${countries.VN.b22Jeju.jejuEntryDenied}, expansionPermit=${countries.VN.b22Jeju.stayAreaExpansionPermitRequired}

Diff vs previous: see source_diff.json
`;
writeFileSync(join(AUDIT_DIR, 'update_report.md'), report);
console.log(report);
console.log(`Wrote ${OUT_RULES}`);
console.log(`Wrote ${OUT_SOURCES}`);
