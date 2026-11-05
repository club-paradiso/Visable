import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
const require = createRequire(import.meta.url);
const { assessTemporalLawEvidence, dateIso } = require('../lib/enforcement-law-validity.js');

assert.equal(dateIso('20260123'), '2026-01-23');
assert.equal(dateIso('2026-2-3'), '2026-02-03');
assert.equal(dateIso('2026-02-30'), null);
assert.equal(dateIso('bogus'), null);

const dateCase = { violationStartDate: '2026-02-01', violationEndDate: '2026-02-20' };
assert.equal(assessTemporalLawEvidence(dateCase, '2026-01-01', '2026-01-23').verified, true);
assert.equal(assessTemporalLawEvidence(dateCase, '2026-01-01', '2026-02-15').code, 'historical_version_required');
assert.equal(assessTemporalLawEvidence(dateCase, '2026-01-01', '').code, 'effective_dates_unavailable');
assert.equal(assessTemporalLawEvidence({ durationDays: 18, assessmentDate: '2026-10-21' },
  '2026-01-01', '2026-01-23').code, 'violation_dates_required');
assert.equal(assessTemporalLawEvidence({ violationStartDate: '2026-02-20', violationEndDate: '2026-02-01' },
  '2026-01-01', '2026-01-23').verified, false);

const source = require('../lib/enforcement-law-grounding.js');
assert.equal(typeof source.groundOfficialLaw, 'function');

const savedFetch = globalThis.fetch;
const savedEnv = {
  LAW_API_OC: process.env.LAW_API_OC,
  LAW_GROUNDING_MODE: process.env.LAW_GROUNDING_MODE,
};
try {
  process.env.LAW_API_OC = 'SYNTHETIC_NON_SECRET_TEST';
  process.env.LAW_GROUNDING_MODE = 'enabled';
  globalThis.fetch = async (url) => {
    const u = new URL(url);
    const isSearch = u.pathname.includes('lawSearch');
    const isAct = isSearch ? u.searchParams.get('query') === '출입국관리법'
      : u.searchParams.get('MST') === 'TEST-ACT';
    const payload = isSearch
      ? { law: [{ 법령명한글: isAct ? '출입국관리법' : '출입국관리법 시행규칙',
                  법령일련번호: isAct ? 'TEST-ACT' : 'TEST-RULE',
                  시행일자: isAct ? '20260101' : '20260123' }] }
      : isAct
        ? { 조문: [
            { 조문번호: '20', 조문제목: '체류자격 외 활동', 조문내용: '공식 원문 모의자료' },
            { 조문번호: '18', 조문제목: '취업활동', 조문내용: '공식 원문 모의자료' },
            { 조문번호: '21', 조문제목: '근무처 변경', 조문내용: '공식 원문 모의자료' },
          ] }
        : { 조문: [{ 조문번호: '86', 조문제목: '범칙금', 조문내용: '공식 원문 모의자료' }],
            별표: [{ 별표번호: '7', 별표제목: '범칙금 양정기준', 별표내용: '범칙금 모의자료' }] };
    return { ok: true, text: async () => JSON.stringify(payload) };
  };
  const baseline = { status: 'AVAILABLE' };
  const current = await source.groundOfficialLaw({
    violationCode: 'STATUS_OUTSIDE_ACTIVITY_ART20',
    violationStartDate: '2026-02-01', violationEndDate: '2026-02-20',
  }, baseline);
  assert.equal(current.temporalVerification.status, 'CONFIRMED');
  assert.equal(current.status, 'VERIFIED');
  const sharedArticles = await source.groundOfficialLaw({
    violationCode: null,
    violationCandidates: ['UNAUTHORIZED_EMPLOYMENT_ART18_2', 'UNAUTHORIZED_WORKPLACE_CHANGE_ART21_1'],
    violationStartDate: '2026-02-01', violationEndDate: '2026-02-20',
  }, baseline);
  assert.equal(sharedArticles.status, 'VERIFIED');
  assert.ok(sharedArticles.evidence.some((item) => item.id === 'live-law:immigration-act:18'));
  assert.ok(sharedArticles.evidence.some((item) => item.id === 'live-law:immigration-act:21'));
  const historical = await source.groundOfficialLaw({
    violationCode: 'STATUS_OUTSIDE_ACTIVITY_ART20',
    violationStartDate: '2026-01-01', violationEndDate: '2026-01-20',
  }, baseline);
  assert.equal(historical.temporalVerification.code, 'historical_version_required');
  assert.equal(historical.status, 'LIMITED');
  const missingDates = await source.groundOfficialLaw({
    violationCode: 'STATUS_OUTSIDE_ACTIVITY_ART20', durationDays: 18,
  }, baseline);
  assert.equal(missingDates.temporalVerification.code, 'violation_dates_required');
  assert.equal(missingDates.status, 'LIMITED');

  // API query hits can include <b> highlighting and contain multiple historical
  // versions. Only a version active at the start can verify the incident.
  const calls = [];
  globalThis.fetch = async (url) => {
    const u = new URL(url);
    calls.push({ target: u.searchParams.get('target'), query: u.searchParams.get('query') });
    const isAct = u.searchParams.get('query') === '출입국관리법'
      || /^ACT-/.test(u.searchParams.get('MST') || '');
    const payload = u.pathname.includes('lawSearch')
      ? { LawSearch: { totalCnt: '2', law: [
          { 법령명한글: isAct ? '<b>출입국</b>관리법' : '출입국관리법 <b>시행규칙</b>',
            법령일련번호: isAct ? 'ACT-LATE' : 'RULE-LATE', 시행일자: '20260210' },
          { 법령명한글: isAct ? '<b>출입국</b>관리법' : '출입국관리법 <b>시행규칙</b>',
            법령일련번호: isAct ? 'ACT-OLD' : 'RULE-OLD', 시행일자: '20260101' },
        ] } }
      : isAct
        ? { 조문: [{ 조문번호: '20', 조문제목: '체류자격 외 활동', 조문내용: '공식 원문 모의자료' }] }
        : { 조문: [{ 조문번호: '86', 조문제목: '범칙금', 조문내용: '공식 원문 모의자료' }],
            별표: [{ 별표번호: '0007', 별표제목: '범칙금 양정기준', 별표내용: '범칙금 모의자료' }] };
    return { ok: true, text: async () => JSON.stringify(payload) };
  };
  const changedDuringViolation = await source.groundOfficialLaw({
    violationCode: 'STATUS_OUTSIDE_ACTIVITY_ART20',
    violationStartDate: '2026-02-01', violationEndDate: '2026-02-20',
  }, baseline);
  assert.equal(changedDuringViolation.status, 'LIMITED');
  assert.equal(changedDuringViolation.temporalVerification.code, 'version_changed_during_violation');
  assert.ok(calls.some((row) => row.target === 'eflaw'), 'dated cases should use official effective-date search');

  // An HTTP 200 application error must never be mislabeled as "no law exists".
  globalThis.fetch = async () => ({ ok: true, text: async () =>
    JSON.stringify({ errorMessage: 'API 인증값이 등록되지 않았습니다' }) });
  const apiRejected = await source.groundOfficialLaw({
    violationCode: 'STATUS_OUTSIDE_ACTIVITY_ART20',
    violationStartDate: '2026-02-01', violationEndDate: '2026-02-20',
  }, baseline);
  assert.ok(apiRejected.limitations.some((item) => item.includes('upstream_authorization_or_registration_error')));
  assert.notEqual(apiRejected.status, 'VERIFIED');

  // Public-endpoint fallback: when the DRF Open API rejects the caller
  // (unregistered server IP/domain for the OC — the production failure),
  // the credential-free public law.go.kr pages must still verify the
  // article texts live. The synthetic annex PDF cannot match the stored
  // official hash, so the annex stays unverified and the status is
  // LIMITED — the fallback never inflates a failed check into VERIFIED.
  const publicSource = require('../lib/enforcement-law-public.js');
  const syntheticRuleHtml = `<html><body>
    <p class="pty1_p4"><input type="hidden" name="joNoList" value="0086"/><label>제86조(범칙금의 부과)</label>① 범칙금의 양정기준은 별표 7과 같다.</p>
    <!-- 별표 서식 시작 -->
    <div onclick="bylInfoDiv('12')">[별표 7] 범칙금의 양정기준(제86조제1항 관련)
      <a href="/LSW/flDownload.do?gubun=&amp;flSeq=170813013&amp;bylClsCd=110201">PDF</a></div>
    <!-- 별표 서식 끝 -->
  </body></html>`;
  assert.deepEqual(
    publicSource.parseAnnexFiles(syntheticRuleHtml, '7'),
    [{ flSeq: '170813013', bylClsCd: '110201' }],
  );
  const syntheticActHtml = `<html><body>
    <p class="pty1_p4"><input type="hidden" name="joNoList" value="0021"/><label>제21조(근무처의 변경·추가)</label>① 외국인은 근무처를 변경하거나 추가하려면 허가를 받아야 한다.</p>
    <p>② 세부 사항은 대통령령으로 정한다.</p>
  </body></html>`;
  assert.ok(publicSource.parseArticles(syntheticActHtml).get('21').includes('근무처를 변경하거나 추가하려면'));

  globalThis.fetch = async (url) => {
    const raw = String(url);
    if (raw.includes('/DRF/')) {
      return { ok: true, text: async () => JSON.stringify({ result: '사용자 정보 검증에 실패하였습니다.', msg: '서버장비의 IP주소 및 도메인주소를 등록해 주세요.' }) };
    }
    if (raw.includes('lsInfoR.do')) {
      const isRule = raw.includes('lsiSeq=777002');
      return { ok: true, text: async () => (isRule ? syntheticRuleHtml : syntheticActHtml) };
    }
    if (raw.includes('flDownload.do')) {
      return { ok: true, arrayBuffer: async () => new TextEncoder().encode('not-the-official-pdf').buffer };
    }
    const isRulePage = decodeURIComponent(raw).includes('시행규칙');
    return { ok: true, text: async () => `<a href="lsInfoP.do?lsiSeq=${isRulePage ? '777002' : '777001'}&amp;efYd=${isRulePage ? '20261023' : '20261002'}">현재 법령</a>` };
  };
  const publicFallback = await source.groundOfficialLaw({
    violationCode: 'UNAUTHORIZED_WORKPLACE_CHANGE_ART21_1',
    violationStartDate: '2026-10-24', violationEndDate: '2026-11-03',
  }, baseline);
  assert.equal(publicFallback.temporalVerification.status, 'CONFIRMED');
  assert.ok(publicFallback.evidence.some((item) => item.id === 'live-law:immigration-act:21'
    && item.excerpt.includes('근무처를 변경하거나 추가하려면')));
  assert.ok(publicFallback.evidence.some((item) => item.id === 'live-law:immigration-rule:86'));
  assert.ok(!publicFallback.evidence.some((item) => item.id === 'live-law:immigration-rule:appendix7'),
    'annex must stay unverified when the live PDF hash does not match the stored official file');
  assert.equal(publicFallback.status, 'LIMITED');

  // Searching two short variants improves recall but never promotes an
  // unrelated immigration ruling to a "similar case".
  const { retrieveOfficialPrecedents } = require('../lib/enforcement-precedent-grounding.js');
  const precedentQueries = [];
  globalThis.fetch = async (url) => {
    const u = new URL(url);
    if (u.pathname.includes('lawSearch')) {
      precedentQueries.push(u.searchParams.get('query'));
      const isRelevant = u.searchParams.get('query') === '근무처 추가';
      return { ok: true, text: async () => JSON.stringify({
        PrecSearch: { prec: [{
          판례일련번호: isRelevant ? 'MATCH-21' : 'UNRELATED-3',
          사건명: isRelevant ? '근무처 변경 허가 사건' : '다른 출입국 사건',
        }] },
      }) };
    }
    const relevant = u.searchParams.get('ID') === 'MATCH-21';
    return { ok: true, text: async () => JSON.stringify({
      판례정보일련번호: relevant ? 'MATCH-21' : 'UNRELATED-3',
      사건명: relevant ? '근무처 변경 허가 사건' : '다른 출입국 사건',
      판시사항: relevant ? '출입국관리법 제21조 근무처 변경 허가 문제' : '출입국관리법 제3조 관련 문제',
      판결요지: relevant ? '근무처 변경 관련 판단' : '출입국 허가 외의 절차',
    }) };
  };
  const precedentResult = await retrieveOfficialPrecedents({
    violationCode: 'UNAUTHORIZED_WORKPLACE_CHANGE_ART21_1', statusOfStay: 'E-2',
  }, baseline);
  assert.equal(precedentQueries.length, 2);
  assert.equal(precedentResult.similarCases.length, 1);
  assert.equal(precedentResult.similarCases[0].id, 'similar:MATCH-21');
} finally {
  globalThis.fetch = savedFetch;
  for (const [key, value] of Object.entries(savedEnv)) {
    if (value === undefined) delete process.env[key];
    else process.env[key] = value;
  }
}
console.log('Official law temporal evidence checks passed');
