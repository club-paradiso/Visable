/*
 * employment_code_analyzer.mjs
 * ----------------------------------------------------------------------------
 * Deterministic retrieval pipeline that turns a plain Korean/English job or
 * business description into candidate 직종(occupation, KSCO8) and 업종(industry,
 * KSIC11) codes for HiKorea 취업정보(employment information) reporting.
 *
 * IMPORTANT DESIGN CONSTRAINTS (see CLAUDE.md + task spec):
 *  - This module NEVER invents classification codes. Every candidate it returns
 *    is retrieved from the canonical dataset (data/jobcode_master.json). If a
 *    term has no match in the official table, no candidate is produced.
 *  - Occupation (what the person does) and industry (what the employer's
 *    business is) are classified on two completely separate tracks. They are
 *    never mixed.
 *  - This is NOT a legal-permission checker. It only helps find candidate
 *    classification codes for reporting. Final confirmation must come from
 *    HiKorea / 1345 / the 국가데이터처 통계분류포털.
 *
 * The module is environment-neutral: it is a pure ES module that takes its data
 * as injected dependencies, so the SAME code runs in Node (CLI + regression
 * tests) and in the browser (bridged onto window.EmploymentCodeAnalyzer by
 * index.html). It performs no file or network I/O itself.
 * ----------------------------------------------------------------------------
 */

/* --------------------------------------------------------------------------
 * 1. Input normalization
 * ------------------------------------------------------------------------ */

const PUNCT_RE = /[(){}\[\],.\/|·•∙:;!?'"`~_+\-=*&^%$#@<>"'「」『』【】]/g;

/** Lowercase, strip punctuation, collapse whitespace. Korean is preserved. */
export function normalize(value) {
  return String(value == null ? '' : value)
    .toLowerCase()
    .replace(PUNCT_RE, ' ')
    .replace(/\s+/g, ' ')
    .trim();
}

// Korean grammatical particles / verb endings that we strip from a token tail so
// "카페에서" -> "카페", "바리스타로" -> "바리스타", "일해요" -> "일".
const KO_SUFFIX_RE = /(입니다|이에요|예요|이예요|해요|하는|하던|하고|했어요|에서|에게|으로|로서|로써|로|은|는|이|가|을|를|와|과|의|도|만|님|중|쪽)$/;

const STOP_TERMS = new Set([
  '일', '일함', '일하는', '하는', '사람', '직원', '업무', '관련', '분야', '직무',
  '해요', '하고', '있어요', '예요', '이에요', '거', '것', '좀', '제',
  'job', 'work', 'works', 'working', 'worker', 'staff', 'person', 'people',
  'employee', 'the', 'and', 'for', 'with', 'that', 'this', 'into', 'from',
  'who', 'where', 'what', 'are', 'is', 'at', 'in', 'on', 'of', 'to', 'do', 'doing'
]);

/** Detect dominant language of the raw input (rough heuristic, good enough). */
export function detectLanguage(text) {
  const hasHangul = /[가-힣]/.test(text || '');
  const hasLatin = /[a-z]/i.test(text || '');
  if (hasHangul && hasLatin) return 'mixed';
  if (hasHangul) return 'ko';
  if (hasLatin) return 'en';
  return 'unknown';
}

/** Strip a trailing Korean particle from a token (single pass). */
function stripKoSuffix(token) {
  const m = token.match(KO_SUFFIX_RE);
  if (m && token.length - m[0].length >= 2) return token.slice(0, token.length - m[0].length);
  return token;
}

/** Turn raw text into a de-duplicated list of useful query tokens. */
export function tokenize(text) {
  const norm = normalize(text);
  const out = new Set();
  if (norm) out.add(norm);
  norm.split(' ').forEach((raw) => {
    const t = raw.trim();
    if (!t) return;
    [t, stripKoSuffix(t)].forEach((cand) => {
      if (cand && cand.length >= 2 && !STOP_TERMS.has(cand)) out.add(cand);
    });
  });
  return [...out];
}

/* --------------------------------------------------------------------------
 * 2. Concept lexicon + entity extraction
 *
 * A "concept" (from data/employment/synonyms.{ko,en}.json) maps everyday
 * surface phrases to:
 *   - a human-readable label,
 *   - which track(s) it informs (occupation / industry),
 *   - occupation_terms / industry_terms that are fed into the search,
 *   - and, for workplaces, the typical ambiguous roles (used to ask follow-ups).
 * The lexicon contains NO official codes — only retrieval hints.
 * ------------------------------------------------------------------------ */

function conceptSurfaces(concept) {
  const surfaces = Array.isArray(concept.surface) ? concept.surface : [];
  return surfaces.map(normalize).filter(Boolean);
}

/** Find every concept whose surface phrase appears in the normalized text. */
function matchConcepts(normalizedText, tokenSet, concepts) {
  const matched = [];
  for (const concept of concepts) {
    const surfaces = conceptSurfaces(concept);
    let hit = null;
    for (const s of surfaces) {
      if (!s) continue;
      // Multi-word surfaces: substring match. Single tokens: exact token match
      // OR substring (so "카페에서" still matches surface "카페").
      if (s.includes(' ')) {
        if (normalizedText.includes(s)) { hit = s; break; }
      } else if (tokenSet.has(s) || normalizedText.includes(s)) {
        hit = s; break;
      }
    }
    if (hit) matched.push({ concept, matchedSurface: hit });
  }
  return matched;
}

/**
 * Extract structured entities from the input.
 * Returns job_role / workplace_type / business_activity / employment_type /
 * visa_status plus the per-track search-term sets and ambiguity flags.
 */
export function extractEntities(input, lex) {
  const text = input.text || '';
  const normalizedText = normalize(text);
  const tokens = tokenize(text);
  const tokenSet = new Set(tokens);
  const language = input.locale || detectLanguage(text);

  const concepts = [
    ...(lex.ko && Array.isArray(lex.ko.concepts) ? lex.ko.concepts : []),
    ...(lex.en && Array.isArray(lex.en.concepts) ? lex.en.concepts : [])
  ];
  const matches = matchConcepts(normalizedText, tokenSet, concepts);

  const roleMatches = matches.filter((m) => m.concept.type === 'role');
  const workplaceMatches = matches.filter((m) => m.concept.type === 'workplace');
  const empMatches = matches.filter((m) => m.concept.type === 'employment_type');
  const visaMatches = matches.filter((m) => m.concept.type === 'visa');

  // Per-track search terms: raw tokens always participate (so we still retrieve
  // even for concepts not in the lexicon); concept terms are added on top.
  const occupationTerms = new Set(tokens);
  const industryTerms = new Set(tokens);
  roleMatches.forEach((m) => (m.concept.occupation_terms || []).forEach((t) => occupationTerms.add(normalize(t))));
  // A role can weakly hint an industry (e.g. barista -> beverage place) only if
  // it carries industry_terms explicitly.
  roleMatches.forEach((m) => (m.concept.industry_terms || []).forEach((t) => industryTerms.add(normalize(t))));
  workplaceMatches.forEach((m) => (m.concept.industry_terms || []).forEach((t) => industryTerms.add(normalize(t))));
  workplaceMatches.forEach((m) => (m.concept.occupation_terms || []).forEach((t) => occupationTerms.add(normalize(t))));

  // Explicit visa status overrides anything detected in free text.
  let visaStatus = (input.visaStatus || '').trim().toUpperCase() || null;
  if (!visaStatus && visaMatches.length) visaStatus = (visaMatches[0].concept.visa_code || '').toUpperCase() || null;

  // Employment type: explicit input wins, then a detected modifier.
  let employmentType = (input.employmentType || '').trim() || null;
  let employmentTypeLabel = null;
  if (!employmentType && empMatches.length) {
    employmentType = empMatches[0].concept.employment_type || null;
    employmentTypeLabel = empMatches[0].concept.label_ko || null;
  }

  const uniq = (arr) => [...new Set(arr.filter(Boolean))];
  const jobRole = roleMatches.length ? uniq(roleMatches.map((m) => m.concept.label_ko)).join(' / ') : null;
  const workplaceType = workplaceMatches.length
    ? uniq(workplaceMatches.map((m) => m.concept.label_ko)).join(' / ')
    : null;
  const businessActivity = workplaceMatches.length
    ? uniq(workplaceMatches.map((m) => m.concept.business_label_ko || m.concept.label_ko)).join(' / ')
    : null;

  // Ambiguity flags drive the follow-up questions later.
  const ambiguityFlags = [];
  if (workplaceMatches.length && !roleMatches.length) ambiguityFlags.push('workplace_without_role');
  if (roleMatches.length && !workplaceMatches.length) ambiguityFlags.push('role_without_workplace');
  if (!roleMatches.length && !workplaceMatches.length) ambiguityFlags.push('underspecified');
  if (empMatches.some((m) => m.concept.owner)) ambiguityFlags.push('owner_or_self_employed');

  return {
    normalizedInput: normalizedText,
    language,
    jobRole,
    workplaceType,
    businessActivity,
    employmentType,
    employmentTypeLabel,
    visaStatus,
    occupationTerms: [...occupationTerms].filter(Boolean),
    industryTerms: [...industryTerms].filter(Boolean),
    matchedConcepts: matches.map((m) => ({ id: m.concept.id, type: m.concept.type, surface: m.matchedSurface })),
    roleMatches,
    workplaceMatches,
    empMatches,
    ambiguityFlags
  };
}

/* --------------------------------------------------------------------------
 * 3. Search index + hybrid scoring (per track)
 * ------------------------------------------------------------------------ */

const LEVEL_RANK = { major: 1, middle: 2, minor: 3, unit: 4, detailed_unit: 5 };

/**
 * Build a reusable search index from the canonical dataset. Precomputes
 * normalized name/terms and the TYPE-SEGREGATED set of parent codes (KSCO8 and
 * KSIC11 share numeric codes, so a global parent set would mislabel leaves).
 */
export function buildIndex(dataset) {
  const rows = Array.isArray(dataset) ? dataset : (dataset && dataset.data) || [];
  const parentByType = { occupation: new Set(), industry: new Set() };
  rows.forEach((r) => {
    if (r.parent_code != null && parentByType[r.type]) parentByType[r.type].add(String(r.parent_code));
  });
  const indexed = rows.map((r) => ({
    row: r,
    type: r.type,
    code: String(r.code || ''),
    normName: normalize(r.name_ko || r.name_en || ''),
    normTerms: (Array.isArray(r.search_terms_ko) ? r.search_terms_ko : []).map(normalize),
    level: r.level || '',
    levelRank: LEVEL_RANK[r.level] || 0,
    isLeaf: !parentByType[r.type] || !parentByType[r.type].has(String(r.code || ''))
  }));
  return { indexed, parentByType, meta: dataset && !Array.isArray(dataset) ? dataset : null };
}

/**
 * Score one indexed row against the raw query + expanded terms.
 * Returns { score, matchedTerms } where matchedTerms explains the hit.
 */
function scoreRow(entry, rawQuery, terms) {
  const q = normalize(rawQuery);
  const matched = new Set();
  let score = 0;

  // Direct query vs. code / name.
  if (q) {
    if (entry.code === q) { score += 1200; matched.add(q); }
    else if (q.length >= 2 && entry.code.startsWith(q) && /^[0-9a-z]+$/i.test(q)) { score += 200; matched.add(q); }
    if (entry.normName === q) { score += 520; matched.add(q); }
    else if (q.length >= 2 && entry.normName.includes(q)) { score += 150 + Math.min(q.length, 20); matched.add(q); }
    if (entry.normTerms.includes(q)) { score += 320; matched.add(q); }
  }

  // Expanded terms vs. code / name / synonyms. Name and synonym hits are
  // ADDITIVE (not exclusive): a term that appears in the candidate's own name
  // is more relevant than one that only appears in its alias list, so an
  // on-name match outranks an alias-only match even when alias counts tie.
  for (const term of terms) {
    if (!term || term === q) continue;
    if (entry.code === term) { score += 700; matched.add(term); continue; }
    if (/^[0-9]+$/.test(term) && term.length >= 2 && entry.code.startsWith(term)) { score += 120; matched.add(term); }
    if (entry.normName === term) { score += 240; matched.add(term); }
    else if (term.length >= 2 && entry.normName.includes(term)) { score += 60 + Math.min(term.length * 4, 32); matched.add(term); }
    if (entry.normTerms.includes(term)) { score += 110; matched.add(term); }
  }

  if (score > 0) {
    // Prefer deeper, more specific levels and actual leaf (reporting) codes.
    score += entry.levelRank * 24;
    if (entry.isLeaf) score += 80;
  }
  return { score, matchedTerms: [...matched] };
}

/* --------------------------------------------------------------------------
 * 4. Candidate building + confidence
 * ------------------------------------------------------------------------ */

const LEVEL_LABEL = {
  major: '대분류', middle: '중분류', minor: '소분류', unit: '세분류', detailed_unit: '세세분류'
};

function confidenceLabel(score, topScore) {
  // Confidence is relative to the best candidate so a strong match band still
  // reads as "high" even when absolute scores vary by query length.
  if (topScore <= 0) return 'low';
  const ratio = score / topScore;
  if (score >= 360 && ratio >= 0.6) return 'high';
  if (score >= 160 && ratio >= 0.35) return 'medium';
  return 'low';
}

function buildReason(entry, matchedTerms, classificationLabel) {
  const lvl = LEVEL_LABEL[entry.level] || entry.level || '';
  const leafTag = entry.isLeaf ? '신고용 세부코드' : '상위 분류';
  const terms = matchedTerms.filter((t) => t && t !== entry.code).slice(0, 4);
  const termPart = terms.length ? `‘${terms.join('’, ‘')}’ 키워드와 일치` : '코드/명칭 일치';
  return `${classificationLabel} ${lvl} · ${leafTag} — ${termPart}`;
}

function toCandidate(entry, scored, classificationType, sourceMeta, topScore) {
  const r = entry.row;
  const classificationLabel = classificationType === 'occupation' ? '직종(KSCO8)' : '업종(KSIC11)';
  const confidence = confidenceLabel(scored.score, topScore);
  const candidate = {
    code: entry.code,
    name: r.name_ko || r.name_en || '',
    nameEn: r.name_en || null,
    classification: classificationType, // 'occupation' | 'industry'
    level: entry.level,
    levelLabel: LEVEL_LABEL[entry.level] || entry.level,
    isReportingLeaf: entry.isLeaf,
    path: r.path_ko || '',
    score: scored.score,
    confidence,
    matchedTerms: scored.matchedTerms,
    reason: buildReason(entry, scored.matchedTerms, classificationType === 'occupation' ? '직종' : '업종'),
    source: {
      classification: r.source_classification || (sourceMeta && sourceMeta.classification) || null,
      version: r.source_version || (sourceMeta && sourceMeta.short_name) || null,
      effectiveDate: r.source_effective_date || (sourceMeta && sourceMeta.effective_date) || null
    }
  };
  if (confidence === 'low') {
    candidate.warning = '신뢰도가 낮습니다. 실제 업무/사업 내용을 더 구체적으로 입력하거나 HiKorea 조회로 확인하세요.';
  }
  return candidate;
}

/** Rank the dataset for one track and return the top N candidates. */
export function searchTrack(index, classificationType, rawQuery, terms, options = {}) {
  const limit = options.limit || 5;
  const sourceMeta = options.sourceMeta || null;
  const scoredRows = [];
  for (const entry of index.indexed) {
    if (entry.type !== classificationType) continue;
    const scored = scoreRow(entry, rawQuery, terms);
    if (scored.score > 0) scoredRows.push({ entry, scored });
  }
  scoredRows.sort((a, b) => {
    if (b.scored.score !== a.scored.score) return b.scored.score - a.scored.score;
    // Tie-break: prefer leaf, then deeper level, then shorter (more general) code.
    if (a.entry.isLeaf !== b.entry.isLeaf) return a.entry.isLeaf ? -1 : 1;
    if (b.entry.levelRank !== a.entry.levelRank) return b.entry.levelRank - a.entry.levelRank;
    return a.entry.code.length - b.entry.code.length;
  });
  const topScore = scoredRows.length ? scoredRows[0].scored.score : 0;
  return scoredRows.slice(0, limit).map((s) => toCandidate(s.entry, s.scored, classificationType, sourceMeta, topScore));
}

/* --------------------------------------------------------------------------
 * 5. Ambiguity follow-up questions
 * ------------------------------------------------------------------------ */

function buildAmbiguity(entities, occCandidates, indCandidates, lex) {
  const questions = [];

  // Workplace given but no concrete role -> ask what they actually do there.
  entities.workplaceMatches.forEach((m) => {
    const roles = m.concept.ambiguous_roles;
    if (Array.isArray(roles) && roles.length && !entities.roleMatches.length) {
      questions.push({
        flag: 'role',
        question: `${m.concept.label_ko || m.matchedSurface}에서 실제로 어떤 일을 하시나요? (직종 후보를 좁히기 위함)`,
        chips: roles
      });
    }
  });

  // Role given but no employer business -> ask where they work.
  if (entities.roleMatches.length && !entities.workplaceMatches.length && entities.ambiguityFlags.includes('role_without_workplace')) {
    questions.push({
      flag: 'workplace',
      question: '근무처(고용주)의 주된 사업이 무엇인가요? 업종 후보를 찾으려면 사업 종류가 필요합니다.',
      chips: ['식당/카페', '학원/교육', 'IT/소프트웨어', '제조/공장', '도소매/쇼핑몰', '병원/복지', '직접 입력']
    });
  }

  // Freelancer / unclear -> need both service and client.
  const freelancer = entities.empMatches.some((m) => m.concept.freelancer) ||
    /프리랜서|freelanc/i.test(entities.normalizedInput);
  if (freelancer) {
    questions.push({
      flag: 'freelancer',
      question: '프리랜서라면 (1) 어떤 서비스를 제공하는지와 (2) 누구(어떤 사업체)에게 제공하는지를 알려주세요. 직종은 서비스 내용, 업종은 거래처/본인 사업 기준입니다.',
      chips: ['번역/통역', '디자인', '개발/IT', '콘텐츠 제작', '강의/교육', '직접 입력']
    });
  }

  // Owner / 자영업 -> occupation likely 관리자, remind business registration angle.
  if (entities.ambiguityFlags.includes('owner_or_self_employed')) {
    questions.push({
      flag: 'owner',
      question: '본인이 사업주(자영업)인가요? 그렇다면 직종은 보통 관리자/경영, 업종은 사업자등록상 업태·종목 기준으로 골라야 합니다.',
      chips: ['네, 사업주예요', '아니요, 고용된 직원입니다']
    });
  }

  // Underspecified input with no usable candidates.
  if (!occCandidates.length && !indCandidates.length && entities.ambiguityFlags.includes('underspecified')) {
    questions.push({
      flag: 'underspecified',
      question: '입력이 너무 짧습니다. 어떤 일을 하는지(직종)와 근무처가 무슨 사업을 하는지(업종)를 함께 적어주세요. 예: “카페에서 바리스타로 일해요”.',
      chips: []
    });
  }

  return questions;
}

/* --------------------------------------------------------------------------
 * 6. Warnings + source notes
 * ------------------------------------------------------------------------ */

const BASE_CAVEAT =
  '이 결과는 취업정보 신고용 직종·업종 후보를 찾기 위한 참고용입니다. 해당 체류자격에서 이 활동이 허용되는지는 별도 확인이 필요하며, 코드를 골랐다고 취업이 가능해지는 것은 아닙니다.';
const FINAL_CONFIRM =
  '최종 신고 코드는 HiKorea 신고 화면 또는 1345, 국가데이터처 통계분류포털(kssc.mods.go.kr)에서 반드시 확인하세요.';

function buildWarnings(input, entities, occCandidates, indCandidates, context) {
  const warnings = [BASE_CAVEAT, FINAL_CONFIRM];

  const visa = entities.visaStatus;
  if (visa) {
    const target = (context && context.target_statuses) || [];
    const excluded = (context && context.excluded_statuses) || [];
    const baseVisa = visa.split('-').slice(0, 2).join('-');
    if (excluded.includes(visa) || excluded.includes(baseVisa)) {
      warnings.push(`입력한 체류자격(${visa})은 취업정보 신고 대상에서 제외(예: F-5 영주)일 수 있습니다. 신고 의무 여부를 출입국에 확인하세요.`);
    } else if (target.includes(visa) || target.includes(baseVisa)) {
      warnings.push(`입력한 체류자격(${visa})은 취업정보 신고 대상에 해당할 수 있습니다. 다만 이 활동이 해당 자격에서 허용되는지(자격외활동 허가 필요 여부 등)는 별도 확인이 필요합니다.`);
    } else {
      warnings.push(`입력한 체류자격(${visa})의 취업정보 신고 의무 및 활동 허용 여부는 출입국/HiKorea에서 확인하세요.`);
    }
  }

  if (occCandidates.length && occCandidates.every((c) => !c.isReportingLeaf)) {
    warnings.push('직종(KSCO8)은 현재 세세분류(5단계) 전체표 적용 전이라 상위 분류만 매칭될 수 있습니다. HiKorea 직종조회에서 세부코드를 확정하세요.');
  }
  if (entities.empMatches.some((m) => m.concept.owner) || entities.ambiguityFlags.includes('owner_or_self_employed')) {
    warnings.push('자영업/사업주는 직종을 보통 관리자·경영으로, 업종은 사업자등록상 업태·종목 기준으로 신고합니다.');
  }
  return warnings;
}

function buildSourceNotes(sources, context) {
  const notes = [];
  if (sources && sources.occupation) {
    notes.push({
      track: 'occupation',
      classification: sources.occupation.classification || sources.occupation.classification_name,
      version: sources.occupation.short_name || sources.occupation.version || null,
      announcement: sources.occupation.announcement || null,
      effectiveDate: sources.occupation.effective_date || null,
      sourceName: sources.occupation.issuing_body || sources.occupation.source_name || null,
      sourceRef: sources.occupation.portal || sources.occupation.source_url || sources.occupation.source_reference || null,
      fetchedAt: sources.occupation.fetched_at || null,
      checksum: sources.occupation.checksum || null
    });
  }
  if (sources && sources.industry) {
    notes.push({
      track: 'industry',
      classification: sources.industry.classification || sources.industry.classification_name,
      version: sources.industry.short_name || sources.industry.version || null,
      announcement: sources.industry.announcement || null,
      effectiveDate: sources.industry.effective_date || null,
      sourceName: sources.industry.issuing_body || sources.industry.source_name || null,
      sourceRef: sources.industry.portal || sources.industry.source_url || sources.industry.source_reference || null,
      fetchedAt: sources.industry.fetched_at || null,
      checksum: sources.industry.checksum || null
    });
  }
  if (context && context.classification_portal_url) {
    notes.push({ track: 'portal', sourceName: '국가데이터처 통계분류포털', sourceRef: context.classification_portal_url });
  }
  return notes;
}

/* --------------------------------------------------------------------------
 * 7. Public API
 * ------------------------------------------------------------------------ */

/**
 * createEmploymentAnalyzer({ data, lexicon, sources, context })
 *  - data: the canonical jobcode dataset (object with .data, or the array).
 *  - lexicon: { ko: {concepts:[...]}, en: {concepts:[...]} }
 *  - sources: { occupation: {...}, industry: {...} } source metadata
 *  - context: employment_reporting_context block (target/excluded statuses, etc.)
 * Returns { analyze(input), index } where index is reusable.
 */
export function createEmploymentAnalyzer(deps = {}) {
  const dataset = deps.data || { data: [] };
  const lexicon = deps.lexicon || { ko: { concepts: [] }, en: { concepts: [] } };
  const sources = deps.sources || null;
  const context = deps.context || (dataset && dataset.employment_reporting_context) || null;
  const index = buildIndex(dataset);
  const occMeta = dataset && dataset.occupation_source;
  const indMeta = dataset && dataset.industry_source;

  function analyze(input) {
    const safeInput = typeof input === 'string' ? { text: input } : (input || { text: '' });
    const entities = extractEntities(safeInput, lexicon);

    const occupationCandidates = searchTrack(index, 'occupation', safeInput.text, entities.occupationTerms, {
      limit: 5, sourceMeta: occMeta
    });
    const industryCandidates = searchTrack(index, 'industry', safeInput.text, entities.industryTerms, {
      limit: 5, sourceMeta: indMeta
    });

    const ambiguityQuestions = buildAmbiguity(entities, occupationCandidates, industryCandidates, lexicon);
    const warnings = buildWarnings(safeInput, entities, occupationCandidates, industryCandidates, context);
    const sourceNotes = buildSourceNotes(sources || { occupation: occMeta, industry: indMeta }, context);

    return {
      normalizedInput: entities.normalizedInput,
      extracted: {
        jobRole: entities.jobRole || undefined,
        workplaceType: entities.workplaceType || undefined,
        businessActivity: entities.businessActivity || undefined,
        employmentType: entities.employmentType || undefined,
        employmentTypeLabel: entities.employmentTypeLabel || undefined,
        visaStatus: entities.visaStatus || undefined,
        language: entities.language
      },
      occupationCandidates,
      industryCandidates,
      ambiguityQuestions,
      ambiguityFlags: entities.ambiguityFlags,
      matchedConcepts: entities.matchedConcepts,
      // Per-track expanded search terms — exposed so a host UI can feed them into
      // its own scorer (entity-aware retrieval) instead of re-deriving them.
      occupationTerms: entities.occupationTerms,
      industryTerms: entities.industryTerms,
      warnings,
      sourceNotes
    };
  }

  return { analyze, index };
}

/** Convenience one-shot wrapper. */
export function analyzeEmploymentText(input, deps = {}) {
  return createEmploymentAnalyzer(deps).analyze(input);
}

// Browser bridge: when loaded as a module in index.html, expose on window so the
// existing (non-module) inline UI code can call into it.
if (typeof window !== 'undefined') {
  window.EmploymentCodeAnalyzer = {
    normalize,
    tokenize,
    detectLanguage,
    extractEntities,
    buildIndex,
    searchTrack,
    createEmploymentAnalyzer,
    analyzeEmploymentText
  };
}

export default {
  normalize,
  tokenize,
  detectLanguage,
  extractEntities,
  buildIndex,
  searchTrack,
  createEmploymentAnalyzer,
  analyzeEmploymentText
};
