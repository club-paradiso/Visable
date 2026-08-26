'use strict';

const { resolveLawCredential } = require('./law-credential');

const DEFAULT_BASE_URL = 'https://www.law.go.kr';
const QUERY_BY_VIOLATION = {
  STATUS_OUTSIDE_ACTIVITY_ART20: '체류자격외활동허가 출입국관리법',
  UNAUTHORIZED_STAY_OR_WORK_ART18_1: '취업활동 체류자격 출입국관리법',
  UNAUTHORIZED_EMPLOYMENT_ART18_2: '지정된 근무처 출입국관리법',
  UNAUTHORIZED_WORKPLACE_CHANGE_ART21_1: '근무처 변경 추가 출입국관리법',
  OVERSTAY_ART25: '체류기간 연장허가 출입국관리법',
};

function config() {
  const resolved = resolveLawCredential();
  const base = String(process.env.LAW_API_BASE_URL || DEFAULT_BASE_URL).trim();
  return {
    credential: resolved.credential,
    credentialSource: resolved.credentialSource,
    baseUrl: /^https:\/\/([a-z0-9-]+\.)*law\.go\.kr(?::\d+)?$/i.test(base) ? base.replace(/\/+$/, '') : DEFAULT_BASE_URL,
  };
}

function timeoutMs() {
  const seconds = Number(process.env.LAW_GROUNDING_TIMEOUT_SECONDS || 6.5);
  return Number.isFinite(seconds) && seconds > 0 ? Math.min(seconds * 1000, 12000) : 6500;
}

async function fetchJson(url) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs());
  try {
    const response = await fetch(url, { headers: { Accept: 'application/json' }, signal: controller.signal });
    if (!response.ok) return null;
    const text = await response.text();
    try { return JSON.parse(text); } catch { return null; }
  } catch {
    return null;
  } finally {
    clearTimeout(timer);
  }
}

function objects(root) {
  const out = [];
  const visit = (value) => {
    if (Array.isArray(value)) return value.forEach(visit);
    if (!value || typeof value !== 'object') return;
    out.push(value);
    Object.values(value).forEach(visit);
  };
  visit(root);
  return out;
}

function pick(object, keys) {
  for (const key of keys) {
    const value = object && object[key];
    if (value !== undefined && value !== null && value !== '' && typeof value !== 'object') return String(value).trim();
  }
  return '';
}

function clean(value, limit = 700) {
  return String(value || '').replace(/<[^>]*>/g, ' ').replace(/\s+/g, ' ').trim().slice(0, limit);
}

function listCandidates(data) {
  const out = [];
  const seen = new Set();
  for (const object of objects(data)) {
    const id = pick(object, ['판례일련번호', '판례정보일련번호', 'ID', 'id']);
    if (!id || seen.has(id)) continue;
    const title = pick(object, ['사건명', '판례명', 'title']);
    if (!title) continue;
    seen.add(id);
    out.push({ id, title });
  }
  return out.slice(0, 3);
}

function normalizeBody(data, sourceId, caseData) {
  const all = objects(data);
  const object = all.find((item) => pick(item, ['판례정보일련번호', '판례일련번호', 'ID', 'id']) === String(sourceId))
    || all.find((item) => pick(item, ['사건명', '판례명', 'title']))
    || {};
  const title = clean(pick(object, ['사건명', '판례명', 'title']), 240);
  const caseNumber = clean(pick(object, ['사건번호', 'caseNumber']), 90);
  const court = clean(pick(object, ['법원명', 'court']), 120);
  const dateRaw = clean(pick(object, ['선고일자', 'decisionDate']), 20).replace(/\D/g, '');
  const issue = clean(pick(object, ['판시사항', 'issue']), 420);
  const holding = clean(pick(object, ['판결요지', 'holdingSummary']), 620);
  const body = clean(pick(object, ['판례내용', '본문', 'text']), 900);
  const reference = clean(pick(object, ['참조조문', 'referenceStatutes']), 500);
  const combined = `${reference} ${issue} ${holding} ${body}`;
  if (!title || !combined || !/출입국관리법|체류자격|출입국/.test(combined)) return null;
  const excerpt = clean([issue, holding].filter(Boolean).join(' / ') || body, 700);
  if (!excerpt) return null;
  const date = dateRaw.length === 8 ? `${dateRaw.slice(0, 4)}-${dateRaw.slice(4, 6)}-${dateRaw.slice(6, 8)}` : null;
  const url = `https://www.law.go.kr/precInfoP.do?precSeq=${encodeURIComponent(sourceId)}`;
  const evidenceId = `precedent:${sourceId}`;
  const matchingFactors = ['위반 유형'];
  if (caseData.statusOfStay && combined.toUpperCase().includes(String(caseData.statusOfStay).toUpperCase())) matchingFactors.push('체류자격');
  return {
    evidence: {
      id: evidenceId,
      sourceType: 'COURT',
      title: caseNumber ? `${title} (${caseNumber})` : title,
      authority: court || '대한민국 법원',
      sourceDate: date,
      sourceUrl: url,
      excerpt,
      citationGrade: 'DIRECT',
      resultKind: 'BODY_RESULT',
      applicable: true,
    },
    similarCase: {
      id: `similar:${sourceId}`,
      sourceType: 'COURT',
      matchingFactors,
      differingFactors: ['공개 판결문만으로 사실관계와 행정청 내부 재량요소의 동일성은 확인할 수 없음'],
      outcomeSummary: excerpt,
      sourceTitle: caseNumber ? `${title} (${caseNumber})` : title,
      sourceDate: date,
      sourceUrl: url,
      evidenceId,
    },
  };
}

async function retrieveOfficialPrecedents(caseData, baseline) {
  const cfg = config();
  const base = { status: 'UNAVAILABLE', evidence: [], similarCases: [], limitations: [] };
  if (!cfg.credential) {
    base.limitations.push('법령 API 인증값이 없어 공식 판례 본문 검색을 실행하지 않았습니다.');
    return base;
  }
  if (!baseline || baseline.status !== 'AVAILABLE') return base;
  const query = QUERY_BY_VIOLATION[caseData && caseData.violationCode];
  if (!query) return base;

  const params = new URLSearchParams({
    OC: cfg.credential,
    target: 'prec',
    type: 'JSON',
    search: '2',
    query,
    display: '3',
    sort: 'ddes',
  });
  const list = await fetchJson(`${cfg.baseUrl}/DRF/lawSearch.do?${params.toString()}`);
  if (!list) {
    base.limitations.push('국가법령정보센터 판례 목록 조회를 완료하지 못했습니다.');
    return base;
  }

  const candidates = listCandidates(list);
  for (const candidate of candidates) {
    const detailParams = new URLSearchParams({ OC: cfg.credential, target: 'prec', type: 'JSON', ID: candidate.id });
    const detail = await fetchJson(`${cfg.baseUrl}/DRF/lawService.do?${detailParams.toString()}`);
    if (!detail) continue;
    const normalized = normalizeBody(detail, candidate.id, caseData);
    if (!normalized) continue;
    base.evidence.push(normalized.evidence);
    base.similarCases.push(normalized.similarCase);
  }

  if (base.similarCases.length) base.status = 'AVAILABLE';
  else {
    base.status = 'LIMITED';
    base.limitations.push('현재 질의로 직접 인용 가능한 공개 판례 본문을 찾지 못했습니다.');
  }
  return base;
}

module.exports = { retrieveOfficialPrecedents };
