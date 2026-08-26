'use strict';

const { publicLawCredentialConfig, resolveLawCredential } = require('./law-credential');

const DEFAULT_BASE_URL = 'https://www.law.go.kr';
const SEARCH_PATH = '/DRF/lawSearch.do';
const SERVICE_PATH = '/DRF/lawService.do';
const DEFAULT_TIMEOUT_MS = 6500;

const ARTICLE_BY_VIOLATION = {
  UNAUTHORIZED_STAY_OR_WORK_ART18_1: '18',
  UNAUTHORIZED_EMPLOYMENT_ART18_2: '18',
  STATUS_OUTSIDE_ACTIVITY_ART20: '20',
  UNAUTHORIZED_WORKPLACE_CHANGE_ART21_1: '21',
  OVERSTAY_ART25: '25',
};

function lawConfig() {
  const resolved = resolveLawCredential();
  const modeRaw = String(process.env.LAW_GROUNDING_MODE || 'enabled').trim().toLowerCase();
  const mode = ['disabled', 'audit', 'enabled'].includes(modeRaw) ? modeRaw : 'disabled';
  const rawBase = String(process.env.LAW_API_BASE_URL || DEFAULT_BASE_URL).trim();
  const baseUrl = /^https:\/\/([a-z0-9-]+\.)*law\.go\.kr(?::\d+)?$/i.test(rawBase)
    ? rawBase.replace(/\/+$/, '')
    : DEFAULT_BASE_URL;
  return {
    credential: resolved.credential,
    credentialSource: resolved.credentialSource,
    mode,
    baseUrl,
  };
}

function publicLawConfig() {
  const cfg = lawConfig();
  return {
    ...publicLawCredentialConfig(),
    lawGroundingMode: cfg.mode,
    endpointHost: new URL(cfg.baseUrl).hostname,
  };
}

function timeoutMs() {
  const seconds = Number(process.env.LAW_GROUNDING_TIMEOUT_SECONDS || 6.5);
  return Number.isFinite(seconds) && seconds > 0 ? Math.min(seconds * 1000, 12000) : DEFAULT_TIMEOUT_MS;
}

async function fetchJson(url) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs());
  try {
    const response = await fetch(url, {
      method: 'GET',
      headers: {
        Accept: 'application/json, application/xml;q=0.2, text/plain;q=0.1',
        'User-Agent': 'Visable-Enforcement-Law-Grounding/2',
      },
      signal: controller.signal,
    });
    if (!response.ok) return { ok: false, status: `http_${response.status}` };
    const text = await response.text();
    try {
      return { ok: true, data: JSON.parse(text) };
    } catch {
      return { ok: false, status: 'non_json_response' };
    }
  } catch (error) {
    return { ok: false, status: error && error.name === 'AbortError' ? 'timeout' : 'network_error' };
  } finally {
    clearTimeout(timer);
  }
}

function allObjects(root) {
  const out = [];
  const visit = (value) => {
    if (Array.isArray(value)) {
      value.forEach(visit);
      return;
    }
    if (!value || typeof value !== 'object') return;
    out.push(value);
    Object.values(value).forEach(visit);
  };
  visit(root);
  return out;
}

function firstText(object, keys) {
  for (const key of keys) {
    const value = object && object[key];
    if (value !== undefined && value !== null && value !== '' && typeof value !== 'object') {
      return String(value).trim();
    }
  }
  return '';
}

function normalizeLawName(value) {
  return String(value || '').replace(/[\s·]/g, '').trim();
}

function exactLawCandidate(data, lawName) {
  const wanted = normalizeLawName(lawName);
  const objects = allObjects(data);
  const candidates = objects.filter((object) => {
    const name = firstText(object, ['법령명한글', '법령명', '법령명_한글', 'lawName', '법령명한글보기']);
    return normalizeLawName(name) === wanted;
  });
  const candidate = candidates.find((object) => firstText(object, ['법령일련번호', 'MST', 'mst', '법령ID', 'ID', 'lawId'])) || candidates[0];
  if (!candidate) return null;
  return {
    mst: firstText(candidate, ['법령일련번호', 'MST', 'mst']),
    id: firstText(candidate, ['법령ID', 'ID', 'lawId']),
    name: firstText(candidate, ['법령명한글', '법령명', '법령명_한글', 'lawName']) || lawName,
    effectiveDate: firstText(candidate, ['시행일자', '공포일자', '시행일', 'effectiveDate']),
  };
}

async function searchLaw(lawName, cfg) {
  const params = new URLSearchParams({
    OC: cfg.credential,
    target: 'law',
    type: 'JSON',
    query: lawName,
    display: '10',
  });
  const result = await fetchJson(`${cfg.baseUrl}${SEARCH_PATH}?${params.toString()}`);
  if (!result.ok) return { ok: false, status: result.status };
  const candidate = exactLawCandidate(result.data, lawName);
  return candidate ? { ok: true, candidate } : { ok: false, status: 'no_exact_law_match' };
}

async function lawDetail(candidate, cfg, extra = {}) {
  const params = new URLSearchParams({ OC: cfg.credential, target: 'law', type: 'JSON' });
  if (candidate.mst) params.set('MST', candidate.mst);
  else if (candidate.id) params.set('ID', candidate.id);
  else return { ok: false, status: 'missing_law_identifier' };
  for (const [key, value] of Object.entries(extra)) {
    if (value !== undefined && value !== null && value !== '') params.set(key, String(value));
  }
  return fetchJson(`${cfg.baseUrl}${SERVICE_PATH}?${params.toString()}`);
}

function normalizeArticleNumber(value) {
  const raw = String(value || '').replace(/\s/g, '');
  const match = raw.match(/(?:제)?0*(\d+)조/);
  return match ? String(Number(match[1])) : raw.replace(/\D/g, '');
}

function cleanExcerpt(value, limit = 850) {
  return String(value || '').replace(/<[^>]*>/g, ' ').replace(/\s+/g, ' ').trim().slice(0, limit);
}

function findArticle(data, articleNumber) {
  const wanted = String(Number(articleNumber));
  for (const object of allObjects(data)) {
    const number = firstText(object, ['조문번호', '조문번호문자열', '조문키', 'articleNo', 'article']);
    if (!number || normalizeArticleNumber(number) !== wanted) continue;
    const title = firstText(object, ['조문제목', '조문제목명', 'articleTitle']);
    const body = firstText(object, ['조문내용', '조문본문', '내용', 'articleText', 'text']);
    const excerpt = cleanExcerpt([number, title, body].filter(Boolean).join(' '));
    if (excerpt) return excerpt;
  }
  return '';
}

function findAppendix7(data) {
  const objects = allObjects(data);
  for (const object of objects) {
    const blob = cleanExcerpt(Object.entries(object)
      .filter(([, value]) => typeof value !== 'object')
      .map(([key, value]) => `${key} ${value}`)
      .join(' '), 1200);
    if ((/별표\s*7/.test(blob) || /별표제?7/.test(blob)) && /범칙금/.test(blob)) {
      return blob.slice(0, 850);
    }
  }
  return '';
}

function evidenceItem({ id, title, article, excerpt, sourceUrl, effectiveDate, grade }) {
  return {
    id,
    sourceType: title.includes('시행규칙') ? 'REGULATION' : 'STATUTE',
    title,
    authority: '국가법령정보센터',
    sourceDate: /^\d{8}$/.test(String(effectiveDate || ''))
      ? `${effectiveDate.slice(0, 4)}-${effectiveDate.slice(4, 6)}-${effectiveDate.slice(6, 8)}`
      : null,
    sourceUrl,
    excerpt: cleanExcerpt(excerpt || article, 850),
    citationGrade: grade,
    resultKind: 'LEGAL_RULE',
    applicable: true,
  };
}

async function fetchNamedLaw(lawName, cfg) {
  const search = await searchLaw(lawName, cfg);
  if (!search.ok) return { ok: false, status: search.status };
  const detail = await lawDetail(search.candidate, cfg);
  if (!detail.ok) return { ok: false, status: detail.status, candidate: search.candidate };
  return { ok: true, candidate: search.candidate, data: detail.data };
}

async function fetchAppendix7(candidate, cfg) {
  const detail = await lawDetail(candidate, cfg, { BD: 'ON', BT: '1', BN: '7' });
  if (!detail.ok) return '';
  return findAppendix7(detail.data);
}

async function groundOfficialLaw(caseData, baseline) {
  const cfg = lawConfig();
  const base = {
    status: 'UNAVAILABLE',
    mode: cfg.mode,
    configured: Boolean(cfg.credential),
    credentialSource: cfg.credentialSource || null,
    evidence: [],
    limitations: [],
    checkedAt: new Date().toISOString(),
  };

  if (cfg.mode === 'disabled') {
    base.limitations.push('실시간 법령 grounding이 disabled 상태입니다.');
    return base;
  }
  if (!cfg.credential) {
    base.limitations.push('Vercel에 지원되는 법령 API 인증 환경변수가 없어 정적 검증 스냅샷을 사용합니다.');
    return base;
  }
  if (!baseline || baseline.status !== 'AVAILABLE') {
    base.limitations.push('법령상 기준을 먼저 확정할 수 없어 실시간 조문 교차검증을 생략했습니다.');
    return base;
  }

  const article = ARTICLE_BY_VIOLATION[caseData && caseData.violationCode];
  if (!article) {
    base.limitations.push('현재 위반유형에 대응하는 실시간 법령 조문 매핑이 없습니다.');
    return base;
  }

  const [act, rule] = await Promise.all([
    fetchNamedLaw('출입국관리법', cfg),
    fetchNamedLaw('출입국관리법 시행규칙', cfg),
  ]);

  const grade = cfg.mode === 'enabled' ? 'DIRECT' : 'CONTEXTUAL';
  let actArticle = '';
  let rule86 = '';
  let appendix7 = '';

  if (act.ok) {
    actArticle = findArticle(act.data, article);
    if (actArticle) {
      base.evidence.push(evidenceItem({
        id: `live-law:immigration-act:${article}`,
        title: '출입국관리법',
        article: `제${article}조`,
        excerpt: actArticle,
        sourceUrl: 'https://www.law.go.kr/법령/출입국관리법',
        effectiveDate: act.candidate.effectiveDate,
        grade,
      }));
    }
  } else {
    base.limitations.push(`출입국관리법 API 조회 실패: ${act.status}`);
  }

  if (rule.ok) {
    rule86 = findArticle(rule.data, '86');
    appendix7 = findAppendix7(rule.data) || await fetchAppendix7(rule.candidate, cfg);
    if (rule86) {
      base.evidence.push(evidenceItem({
        id: 'live-law:immigration-rule:86',
        title: '출입국관리법 시행규칙',
        article: '제86조',
        excerpt: rule86,
        sourceUrl: 'https://www.law.go.kr/법령/출입국관리법시행규칙',
        effectiveDate: rule.candidate.effectiveDate,
        grade,
      }));
    }
    if (appendix7) {
      base.evidence.push(evidenceItem({
        id: 'live-law:immigration-rule:appendix7',
        title: '출입국관리법 시행규칙 별표 7',
        article: '범칙금의 양정기준',
        excerpt: appendix7,
        sourceUrl: 'https://www.law.go.kr/법령별표서식/(출입국관리법시행규칙,별표7)',
        effectiveDate: rule.candidate.effectiveDate,
        grade,
      }));
    }
  } else {
    base.limitations.push(`출입국관리법 시행규칙 API 조회 실패: ${rule.status}`);
  }

  const coreVerified = Boolean(actArticle && rule86);
  if (cfg.mode === 'audit') {
    base.status = coreVerified ? 'AUDIT_ONLY' : 'LIMITED';
    base.limitations.push('LAW_GROUNDING_MODE=audit이므로 조회 결과는 진단용이며 실시간 검증 완료로 표시하지 않습니다.');
  } else if (coreVerified && appendix7) {
    base.status = 'VERIFIED';
  } else if (coreVerified || base.evidence.length) {
    base.status = 'LIMITED';
    if (!appendix7) base.limitations.push('별표 7 본문을 API 응답에서 직접 식별하지 못해 금액표는 버전 고정 스냅샷과 교차 사용합니다.');
  }

  if (!base.evidence.length) {
    base.limitations.push('실시간 법령 API에서 인용 가능한 조문 본문을 확보하지 못했습니다.');
  }
  return base;
}

module.exports = {
  ARTICLE_BY_VIOLATION,
  groundOfficialLaw,
  publicLawConfig,
};
