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
  // CJK ideographs with no Hangul → treat as Chinese (한자 단독 입력).
  const hasHan = /[一-鿿]/.test(text || '');
  if (hasHangul && hasLatin) return 'mixed';
  if (hasHangul) return 'ko';
  if (hasHan && !hasLatin) return 'zh';
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

/**
 * Surface-match rule shared by concepts, ambiguous entries and field signals.
 *  - Multi-word surfaces: substring (phrase) match.
 *  - Latin single words: EXACT token only — so "actor" never matches inside
 *    "factory", "model" never inside "modeling", "vet" never inside "veteran".
 *  - Korean single words: token match, or substring for length>=3 (handles
 *    agglutination like "카페에서" → "카페"); short 2-char surfaces (모델, 배우,
 *    가수, 타투) must hit a real token, not a substring of a longer word.
 */
function surfaceHits(surface, normalizedText, tokenSet) {
  const s = normalize(surface);
  if (!s) return false;
  if (s.includes(' ')) return normalizedText.includes(s);
  if (/^[a-z0-9]+$/.test(s)) return tokenSet.has(s);
  // Han (Chinese) is written without spaces, so a whole sentence normalizes to a
  // single token and token matching never fires. Han characters are also dense —
  // a 2-character word (酒店, 客房) is as specific as a 3-syllable Hangul word — so
  // substring matching starts at length 2 instead of 3.
  if (/^[一-鿿]+$/.test(s)) return s.length >= 2 && normalizedText.includes(s);
  return tokenSet.has(s) || (s.length >= 3 && normalizedText.includes(s));
}

/** Find every concept whose surface phrase appears in the normalized text. */
function matchConcepts(normalizedText, tokenSet, concepts) {
  const matched = [];
  for (const concept of concepts) {
    const surfaces = conceptSurfaces(concept);
    let hit = null;
    for (const s of surfaces) {
      if (s && surfaceHits(s, normalizedText, tokenSet)) { hit = s; break; }
    }
    if (hit) matched.push({ concept, matchedSurface: hit });
  }
  return matched;
}

/**
 * Match umbrella / ambiguous inputs (data/employment/ambiguous_inputs.json).
 * These are vague or non-existent-as-a-single-code terms (아이돌, 댄서, 연습생,
 * 타투이스트, 반영구화장, 알바, 회사원, 프리랜서, …) that must be DECOMPOSED into
 * real sub-roles rather than mapped to one invented code.
 */
function matchAmbiguous(normalizedText, tokenSet, entries) {
  const matched = [];
  for (const entry of entries || []) {
    const surfaces = (Array.isArray(entry.surface) ? entry.surface : []).map(normalize).filter(Boolean);
    let hit = null;
    for (const s of surfaces) {
      if (s && surfaceHits(s, normalizedText, tokenSet)) { hit = s; break; }
    }
    if (hit) matched.push({ entry, matchedSurface: hit });
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

  // Every locale pool is merged unconditionally: mixed-language input
  // ("카페에서 barista로 일해요") must match concepts from more than one pool.
  const concepts = [
    ...(lex.ko && Array.isArray(lex.ko.concepts) ? lex.ko.concepts : []),
    ...(lex.en && Array.isArray(lex.en.concepts) ? lex.en.concepts : []),
    ...(lex.zh && Array.isArray(lex.zh.concepts) ? lex.zh.concepts : [])
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

  // --- richer entities (entertainment / tattoo / self-employment aware) ---
  // employer_type from a matched workplace (or its explicit employer_type field).
  const employerType = workplaceMatches.length
    ? uniq(workplaceMatches.map((m) => m.concept.employer_type || m.concept.id)).join(' / ')
    : (empMatches.some((m) => m.concept.owner) ? 'self-employed' : null);

  // income_status: detected from explicit unpaid/paid cues in the text.
  let incomeStatus = 'unknown';
  if (/무급|무보수|소득\s*없|돈\s*안|unpaid|no\s*pay|volunteer|봉사/.test(normalizedText)) incomeStatus = 'unpaid';
  else if (/유급|월급|급여|페이|시급|일당|보수|소득\s*있|paid|salary|wage/.test(normalizedText)) incomeStatus = 'paid';

  // performance_type / role_status / legal_sensitivity from concept metadata.
  const performanceType = uniq(matches.map((m) => m.concept.performance_type)).join(' / ') || null;
  const roleStatusFromConcept = uniq([
    ...empMatches.map((m) => m.concept.role_status),
    ...matches.map((m) => m.concept.role_status)
  ]);
  let roleStatus = roleStatusFromConcept[0] || null;
  if (!roleStatus) {
    if (empMatches.some((m) => m.concept.owner)) roleStatus = 'owner';
    else if (empMatches.some((m) => m.concept.freelancer)) roleStatus = 'freelancer';
    else if (empMatches.some((m) => m.concept.trainee)) roleStatus = 'trainee';
  }
  const legalSensitivity = uniq(matches.map((m) => m.concept.legal_sensitivity));

  // Confidence cap (broad/indirect mappings, e.g. tattoo, idol umbrella) and
  // per-track candidate caveats carried by the matched concepts.
  const caps = uniq(matches.map((m) => m.concept.confidence_cap));
  const confidenceCap = caps.includes('low') ? 'low' : (caps.includes('medium') ? 'medium' : null);
  const candidateCaveats = { occupation: [], industry: [] };
  matches.forEach((m) => {
    const cav = m.concept.candidate_caveat;
    if (!cav) return;
    const tracks = m.concept.type === 'workplace' ? ['industry'] : (m.concept.type === 'role' ? ['occupation'] : ['occupation', 'industry']);
    tracks.forEach((t) => candidateCaveats[t].push(cav));
  });
  candidateCaveats.occupation = uniq(candidateCaveats.occupation);
  candidateCaveats.industry = uniq(candidateCaveats.industry);

  // Ambiguity flags drive the follow-up questions later.
  const ambiguityFlags = [];
  if (workplaceMatches.length && !roleMatches.length) ambiguityFlags.push('workplace_without_role');
  if (roleMatches.length && !workplaceMatches.length) ambiguityFlags.push('role_without_workplace');
  if (!roleMatches.length && !workplaceMatches.length) ambiguityFlags.push('underspecified');
  if (empMatches.some((m) => m.concept.owner)) ambiguityFlags.push('owner_or_self_employed');
  if (roleStatus === 'trainee' || empMatches.some((m) => m.concept.trainee)) ambiguityFlags.push('trainee_status_unclear');

  return {
    normalizedInput: normalizedText,
    language,
    jobRole,
    workplaceType,
    businessActivity,
    employmentType,
    employmentTypeLabel,
    employerType,
    incomeStatus,
    performanceType,
    roleStatus,
    legalSensitivity,
    visaStatus,
    confidenceCap,
    candidateCaveats,
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
 * 2b. Field-labor signal extraction + analyzer modes
 *
 * Field-worker descriptions ("한치잡이 배에서 한치잡아요", "귤 따요",
 * "골프장 청소해요", "공장에서 박스 포장해요") rarely contain a formal job title.
 * They are best decoded as PLACE + OBJECT + ACTION (+ TOOL). The
 * colloquial_field_terms.{ko,en}.json lexicons carry these signals together with
 * VERIFIED retrieval keywords (every term exists in jobcode_master.json) and a
 * sector tag. No official codes live in those files.
 * ------------------------------------------------------------------------ */

// Sectors that mean site-based / field labor (E-8/E-9/E-10/H-2 style work).
const FIELD_LABOR_SECTORS = new Set([
  'fishery_vessel', 'fishery', 'aquaculture', 'seafood_processing', 'agriculture',
  'livestock', 'manufacturing', 'logistics', 'grounds', 'construction',
  'cleaning', 'kitchen_labor'
  // NOTE: 'hospitality' deliberately excluded — a bare 호텔/리조트 PLACE is a
  // service workplace; the field-labor angle (객실 청소·정비) comes from the
  // cleaning ACTION/OBJECT, which is what flips those inputs to field mode.
]);

// Concept-id → coarse mode bucket, used only to pick service vs professional mode
// when there is no field-labor signal. Field labor and arts are detected from
// signals / legal sensitivity, so they are not listed here.
const SERVICE_CONCEPT_IDS = new Set([
  // Korean concept ids
  'barista', 'server', 'cook', 'cook_assistant', 'baker', 'food_prep', 'sales_clerk', 'customer_service',
  'hotel_front', 'cleaner', 'driver', 'delivery', 'cafe', 'restaurant', 'convenience_store',
  'retail_store', 'online_shopping', 'hotel', 'beauty_shop',
  // cuisine-specific eateries (all classify as service workplaces)
  'korean_restaurant', 'chinese_restaurant', 'japanese_restaurant', 'western_restaurant',
  'other_foreign_restaurant', 'snack_bar', 'chicken_shop', 'pizza_burger_shop', 'bakery', 'pub',
  'korean_restaurant_en', 'chinese_restaurant_en', 'japanese_restaurant_en', 'western_restaurant_en',
  'other_foreign_restaurant_en', 'pizza_burger_shop_en', 'chicken_shop_en', 'bakery_en', 'pub_en',
  // English concept ids (synonyms.en.json)
  'barista_en', 'server_en', 'cook_en', 'cook_assistant_en', 'sales_clerk_en',
  'customer_service_en', 'front_desk_en', 'cleaner_en', 'delivery_en', 'cafe_en',
  'restaurant_en', 'online_shop_en', 'retail_en', 'convenience_en', 'hotel_en',
  // beauty / personal service
  'nail_artist', 'makeup_artist', 'nail_artist_en', 'makeup_artist_en', 'hair_designer_en'
]);
const PROFESSIONAL_CONCEPT_IDS = new Set([
  // Korean concept ids
  'developer', 'designer', 'marketer', 'translator', 'researcher', 'professor',
  'english_instructor', 'instructor', 'ta', 'manager', 'office_worker',
  'content_creator', 'nurse', 'caregiver', 'childcare_teacher', 'it_company',
  'university', 'school', 'language_academy', 'media_company', 'hospital',
  'care_facility', 'daycare',
  // newly added Korean professional concepts
  'accountant', 'lawyer', 'doctor', 'veterinarian', 'pharmacist', 'architect',
  'engineer_general', 'mechanic', 'data_analyst', 'consultant', 'sales_trade',
  'photographer', 'lab_assistant',
  // English concept ids (synonyms.en.json)
  'developer_en', 'designer_en', 'marketer_en', 'translator_en', 'researcher_en',
  'professor_en', 'teacher_en', 'content_creator_en', 'nurse_en', 'caregiver_en',
  'manager_en', 'academy_en', 'university_en', 'startup_en', 'hospital_en', 'daycare_en',
  'accountant_en', 'lawyer_en', 'doctor_en', 'veterinarian_en', 'pharmacist_en',
  'architect_en', 'engineer_en', 'mechanic_en', 'data_analyst_en', 'consultant_en',
  'sales_trade_en', 'photographer_en', 'lab_assistant_en'
]);

/**
 * Scan the input for field-labor place/object/action/tool signals.
 * Returns the per-kind matches plus merged retrieval terms (occupation/industry),
 * the union of sectors, and the disambiguation rule ids the signals point at.
 */
export function extractFieldSignals(text, fieldLex) {
  const normalizedText = normalize(text);
  const tokenSet = new Set(tokenize(text));
  const signals = [
    ...((fieldLex && fieldLex.ko && fieldLex.ko.signals) || []),
    ...((fieldLex && fieldLex.en && fieldLex.en.signals) || [])
  ];
  const matched = [];
  for (const sig of signals) {
    const surfaces = Array.isArray(sig.surface) ? sig.surface : [];
    let hit = null;
    for (const sf of surfaces) { if (surfaceHits(sf, normalizedText, tokenSet)) { hit = normalize(sf); break; } }
    if (hit) matched.push({ ...sig, matchedSurface: hit });
  }
  const byKind = { places: [], objects: [], actions: [], tools: [] };
  const kindKey = { place: 'places', object: 'objects', action: 'actions', tool: 'tools' };
  const occupationTerms = new Set();
  const industryTerms = new Set();
  const sectors = new Set();
  const disambiguationIds = new Set();
  // How many matched signals point at each fork rule — used to rank which single
  // question is most relevant (3 signals agreeing on "vessel?" beats 1 stray ref).
  const disambiguationRefs = Object.create(null);
  for (const m of matched) {
    const k = kindKey[m.signal];
    if (k) byKind[k].push({ id: m.id, label: m.label_ko || m.label_en || m.id, sector: m.sector, surface: m.matchedSurface });
    (m.occupation_terms || []).forEach((t) => occupationTerms.add(normalize(t)));
    (m.industry_terms || []).forEach((t) => industryTerms.add(normalize(t)));
    if (m.sector) sectors.add(m.sector);
    (m.disambiguation || []).forEach((d) => { disambiguationIds.add(d); disambiguationRefs[d] = (disambiguationRefs[d] || 0) + 1; });
  }
  return {
    matched,
    places: byKind.places,
    objects: byKind.objects,
    actions: byKind.actions,
    tools: byKind.tools,
    sectors,
    placeIds: new Set(byKind.places.map((p) => p.id)),
    disambiguationIds,
    disambiguationRefs,
    occupationTerms: [...occupationTerms].filter(Boolean),
    industryTerms: [...industryTerms].filter(Boolean)
  };
}

/**
 * Decide the analyzer mode. Order of precedence:
 *   arts_entertainment → field_labor → service → professional → ambiguous.
 * Field labor wins whenever a real place/object/action site-signal is present,
 * even at a service-ish place (식당 설거지, 골프장 청소) — matching how those
 * inputs should be read.
 */
export function detectMode(entities, fieldSig) {
  const sens = entities.legalSensitivity || [];
  if (sens.includes('entertainment')) return 'arts_entertainment_mode';
  const inField = (arr) => (arr || []).some((m) => FIELD_LABOR_SECTORS.has(m.sector));
  const hasFieldAction = inField(fieldSig.actions);
  const hasFieldObjOrPlace = inField(fieldSig.objects) || inField(fieldSig.places) || inField(fieldSig.tools);
  const ids = new Set((entities.matchedConcepts || []).map((c) => c.id));
  const hasService = (fieldSig.matched || []).some((m) => m.sector === 'food_service') ||
    [...ids].some((id) => SERVICE_CONCEPT_IDS.has(id));
  const hasProfessional = [...ids].some((id) => PROFESSIONAL_CONCEPT_IDS.has(id));
  // A field ACTION (잡다/따다/포장/청소/설거지/용접…) is decisive — it means
  // hands-on site work even at a service-ish place (식당 설거지, 골프장 청소).
  if (hasFieldAction) return 'field_labor_mode';
  // A field place/object with no competing professional/service role is field too.
  if (hasFieldObjOrPlace && !hasProfessional && !hasService) return 'field_labor_mode';
  if (sens.includes('tattoo')) return 'service_mode';
  if (hasProfessional) return 'professional_mode';
  if (hasService) return 'service_mode';
  if (hasFieldObjOrPlace) return 'field_labor_mode';
  return 'ambiguous_mode';
}

/**
 * Field-labor / fork disambiguation questions, driven by the matched signals.
 * A rule fires only when (a) a matched signal references it AND (b) its trigger
 * sector/place is actually present — so a stray fish token can't drag a vessel
 * question into a clearly aquaculture/factory input. Ranked by how many signals
 * agree on the fork, then by static priority.
 */
export function evaluateDisambiguation(fieldSig, rules) {
  const fired = [];
  for (const rule of rules || []) {
    if (!fieldSig.disambiguationIds.has(rule.id)) continue;
    const trig = rule.trigger || {};
    if (trig.sectors && trig.sectors.length && !trig.sectors.some((s) => fieldSig.sectors.has(s))) continue;
    if (trig.places && trig.places.length && !trig.places.some((p) => fieldSig.placeIds && fieldSig.placeIds.has(p))) continue;
    fired.push({ rule, refs: (fieldSig.disambiguationRefs && fieldSig.disambiguationRefs[rule.id]) || 0 });
  }
  fired.sort((a, b) => (b.refs - a.refs) || ((b.rule.priority || 0) - (a.rule.priority || 0)));
  return fired.map((f) => f.rule);
}

/** Human-readable "장소 + 작업" interpretation line. */
function buildParsedInterpretation(entities, fieldSig, mode, locale) {
  const en = locale === 'en';
  if (mode === 'field_labor_mode') {
    const parts = [];
    fieldSig.places.forEach((p) => parts.push(p.label));
    fieldSig.objects.forEach((o) => parts.push(o.label));
    fieldSig.actions.forEach((a) => parts.push(a.label));
    const uniq = [...new Set(parts)].slice(0, 4);
    if (uniq.length) return en
      ? `Read as: ${uniq.join(' + ')} (place + task)`
      : `${uniq.join(' + ')} 기준으로 분석됨`;
  }
  const bits = [entities.jobRole, entities.businessActivity].filter(Boolean);
  if (bits.length) return en ? `Read as: ${bits.join(' / ')}` : `${bits.join(' / ')}(으)로 분석됨`;
  return null;
}

/* --------------------------------------------------------------------------
 * 3. Search index + hybrid scoring (per track)
 * ------------------------------------------------------------------------ */

const LEVEL_RANK = { major: 1, middle: 2, minor: 3, unit: 4, detailed_unit: 5 };

// Name fragments too generic to prove relevance when found INSIDE a query token
// (see the compound-containment rule in scoreRow).
const GENERIC_NAME_WORDS = new Set(['및', '기타', '관련', '일반', '유사', '전문', '서비스', '종사자', '종사원']);

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
  const indexed = rows.map((r) => {
    const normName = normalize(r.name_ko || r.name_en || '');
    return {
      row: r,
      type: r.type,
      code: String(r.code || ''),
      normName,
      // Distinctive words of the official name ("중식 음식점업" → ["중식",
      // "음식점업"]), used by the compound-containment rule in scoreRow.
      nameWords: normName.split(' ').filter((w) => w.length >= 2 && !GENERIC_NAME_WORDS.has(w)),
      normTerms: (Array.isArray(r.search_terms_ko) ? r.search_terms_ko : []).map(normalize),
      level: r.level || '',
      levelRank: LEVEL_RANK[r.level] || 0,
      isLeaf: !parentByType[r.type] || !parentByType[r.type].has(String(r.code || ''))
    };
  });
  return { indexed, parentByType, meta: dataset && !Array.isArray(dataset) ? dataset : null };
}

/**
 * Score one indexed row against the raw query + expanded terms.
 * Returns { score, matchedTerms } where matchedTerms explains the hit.
 */
// normalizedQuery: searchTrack normalizes rawQuery ONCE per call and passes it
// through here, since this function runs once per dataset entry (up to ~1,400
// per track) — re-normalizing the same query string on every entry was pure
// redundant regex work. Falls back to normalizing rawQuery for any other caller.
function scoreRow(entry, rawQuery, terms, normalizedQuery) {
  const q = normalizedQuery !== undefined ? normalizedQuery : normalize(rawQuery);
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
    // Compound-word containment: agglutinated Korean tokens often EMBED an
    // official name word — "중식당" ⊃ "중식", "일식집" ⊃ "일식", "요리사" ⊃
    // "요리". The includes() checks above only look for name ⊇ term, so give
    // credit for term ⊇ name-word too (Hangul only; capped at one hit per term
    // so generic fragments can't stack). Particle-suffixed tokens ("학원에서")
    // are excluded — their stripped twin ("학원") already participates, and the
    // raw form would unevenly reward rows whose name happens to keep the word
    // standalone.
    if (term.length >= 3 && /[가-힣]/.test(term) && !KO_SUFFIX_RE.test(term)) {
      for (const w of entry.nameWords) {
        if (w !== term && term.includes(w)) { score += 70; matched.add(w); break; }
      }
    }
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

const CONF_ORDER = { low: 0, medium: 1, high: 2 };
/** Never let a candidate read higher than the cap imposed by a broad/indirect concept. */
function applyCap(confidence, cap) {
  if (!cap) return confidence;
  return CONF_ORDER[confidence] <= CONF_ORDER[cap] ? confidence : cap;
}

function buildReason(entry, matchedTerms, classificationLabel) {
  const lvl = LEVEL_LABEL[entry.level] || entry.level || '';
  const leafTag = entry.isLeaf ? '신고용 세부코드' : '상위 분류';
  const terms = matchedTerms.filter((t) => t && t !== entry.code).slice(0, 4);
  const termPart = terms.length ? `‘${terms.join('’, ‘')}’ 키워드와 일치` : '코드/명칭 일치';
  return `${classificationLabel} ${lvl} · ${leafTag} — ${termPart}`;
}

function buildReasonEn(entry, matchedTerms, classificationLabel) {
  const lvl = entry.level || '';
  const leafTag = entry.isLeaf ? 'reporting-level code' : 'parent category';
  const terms = matchedTerms.filter((t) => t && t !== entry.code).slice(0, 4);
  const termPart = terms.length ? `matched terms: ${terms.join(', ')}` : 'code/name match';
  return `${classificationLabel} ${lvl} · ${leafTag} — ${termPart}`;
}

function toCandidate(entry, scored, classificationType, sourceMeta, topScore, opts = {}) {
  const r = entry.row;
  const officialName = r.name_ko || r.name_en || '';
  let confidence = applyCap(confidenceLabel(scored.score, topScore), opts.confidenceCap);
  const caveats = [...(opts.caveats || [])];
  const reasonKo = buildReason(entry, scored.matchedTerms, classificationType === 'occupation' ? '직종' : '업종');
  const candidate = {
    code: entry.code,
    name: officialName,
    officialName, // spec alias
    nameEn: r.name_en || null,
    classification: classificationType, // 'occupation' | 'industry'
    classificationType, // spec alias
    level: entry.level,
    levelLabel: LEVEL_LABEL[entry.level] || entry.level,
    isReportingLeaf: entry.isLeaf,
    path: r.path_ko || '',
    score: scored.score,
    confidence,
    matchedTerms: scored.matchedTerms,
    reason: reasonKo,
    reasonKo,
    reasonEn: buildReasonEn(entry, scored.matchedTerms, classificationType === 'occupation' ? 'Occupation(KSCO8)' : 'Industry(KSIC11)'),
    caveats,
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
  const normalizedQuery = normalize(rawQuery);
  const scoredRows = [];
  for (const entry of index.indexed) {
    if (entry.type !== classificationType) continue;
    const scored = scoreRow(entry, rawQuery, terms, normalizedQuery);
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
  return scoredRows.slice(0, limit).map((s) => toCandidate(s.entry, s.scored, classificationType, sourceMeta, topScore, {
    confidenceCap: options.confidenceCap || null,
    caveats: options.caveats || []
  }));
}

/* --------------------------------------------------------------------------
 * 5. Ambiguity follow-up questions
 * ------------------------------------------------------------------------ */

function buildAmbiguity(entities, occCandidates, indCandidates, lex, ambiguousMatches) {
  const questions = [];

  // Umbrella / decomposition terms (아이돌, 댄서, 타투이스트, 반영구화장, 알바, ...):
  // their question + chips come straight from data/employment/ambiguous_inputs.json.
  (ambiguousMatches || []).forEach((m) => {
    const e = m.entry;
    if (e.question_ko) questions.push({ flag: e.id, question: e.question_ko, chips: e.chips || [] });
  });

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

// Follow-up chips help the user refine without typing. General chips always apply;
// domain chips appear when the input touches entertainment or tattoo work.
const GENERAL_CHIPS = [
  '직접 하는 일을 선택할게요', '근무 장소를 선택할게요', '회사/가게가 하는 일을 선택할게요',
  '직원이에요', '프리랜서예요', '사업주예요', '연습생이에요', '소득이 있어요', '소득이 없어요'
];
const ENTERTAINMENT_CHIPS = [
  '공연자로 활동해요', '노래를 해요', '춤을 춰요', '안무를 만들어요', '댄스를 가르쳐요',
  '백댄서예요', '연습생이에요', '소속사 아티스트예요', '소속사 직원이에요', '공연단체 소속이에요'
];
const TATTOO_CHIPS = [
  '타투 시술을 해요', '반영구화장을 해요', '눈썹문신을 해요', '디자인만 해요',
  '타투샵 직원이에요', '타투샵을 운영해요', '강의/교육을 해요'
];
function buildFollowUpChips(entities, ambiguousMatches) {
  const out = [];
  const sens = entities.legalSensitivity || [];
  // Chips explicitly attached to the matched umbrella entries come first.
  (ambiguousMatches || []).forEach((m) => (m.entry.chips || []).forEach((c) => out.push(c)));
  if (sens.includes('entertainment')) ENTERTAINMENT_CHIPS.forEach((c) => out.push(c));
  if (sens.includes('tattoo')) TATTOO_CHIPS.forEach((c) => out.push(c));
  GENERAL_CHIPS.forEach((c) => out.push(c));
  return [...new Set(out)];
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

  const sens = entities.legalSensitivity || [];
  // Entertainment / performance caution.
  if (sens.includes('entertainment')) {
    warnings.push('연예·공연 활동은 소속기관, 계약형태, 보수 발생 여부, 실제 활동내용, 체류자격별 활동범위에 따라 별도 검토가 필요합니다. 직종·업종 후보는 취업 가능 여부 판단이 아닙니다.');
    warnings.push('‘아이돌’ 등은 공식 표준분류에 단일 항목이 없어 실제 활동(가수/무용/연기/방송 등)으로 나눠 후보를 제시합니다. 연습생·훈련 과정은 유급 취업 여부 자체가 별도 확인 대상입니다.');
  }
  // Tattoo caution — legally sensitive (문신사법: 2025-09-25 국회 통과, 2027-10-29 시행 예정).
  if (sens.includes('tattoo')) {
    warnings.push('문신 관련 활동은 문신사법 시행일, 면허 요건, 체류자격, 고용형태, 실제 시술 여부에 따라 별도 검토가 필요합니다. 코드가 있다고 해서 해당 활동이 곧바로 허용되는 것은 아닙니다.');
    warnings.push('참고: 문신사법은 2025-09-25 국회 본회의를 통과했고 2027-10-29 시행 예정입니다(문신·반영구화장 포함, 국가자격 면허 필요). 시행 전·후 요건과 외국인 가능 여부는 국가법령정보센터(law.go.kr)·관할 출입국에서 반드시 확인하세요.');
    warnings.push('현재 표준직업/표준산업분류에는 ‘문신/타투’ 전용 항목이 없어 미용·개인서비스 등 넓은 분류로 간접 매칭됩니다(신뢰도 낮음). 실제 신고 코드는 HiKorea에서 확인하세요.');
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

// Legal source notes appended only when the input is legally sensitive (tattoo /
// entertainment), so users see the governing-law provenance, not just the
// classification provenance.
function buildLegalNotes(legalSources, sensitivity) {
  const out = [];
  (legalSources || []).forEach((ls) => {
    if (!ls.applies_to || ls.applies_to.some((s) => (sensitivity || []).includes(s))) {
      out.push({
        track: 'legal',
        classification: ls.source_name,
        version: ls.status || null,
        effectiveDate: ls.effective_date || null,
        sourceName: ls.source_name,
        sourceRef: ls.source_reference || ls.source_url || null,
        verified: ls.verified === true,
        notes: ls.notes || null
      });
    }
  });
  return out;
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
  const ambiguousEntries = (deps.ambiguous && Array.isArray(deps.ambiguous.entries)) ? deps.ambiguous.entries : [];
  const legalSources = deps.legalSources || (sources && sources.legal_sources) || [];
  // Field-labor place/object/action lexicon + fork disambiguation rules + income
  // reminder. All optional, so the analyzer degrades gracefully without them.
  const fieldLex = deps.fieldTerms || { ko: { signals: [] }, en: { signals: [] } };
  const disambiguationRules = (deps.disambiguation && Array.isArray(deps.disambiguation.rules)) ? deps.disambiguation.rules : [];
  const incomeBrackets = deps.incomeBrackets || null;
  const index = buildIndex(dataset);
  const occMeta = dataset && dataset.occupation_source;
  const indMeta = dataset && dataset.industry_source;

  const uniq = (arr) => [...new Set(arr.filter(Boolean))];

  function analyze(input) {
    const safeInput = typeof input === 'string' ? { text: input } : (input || { text: '' });
    const entities = extractEntities(safeInput, lexicon);

    // Umbrella / ambiguous inputs (아이돌, 댄서, 타투이스트, 반영구화장, 알바, ...):
    // decompose into real sub-role terms, never a single invented code, and carry
    // their legal sensitivity + confidence cap into retrieval.
    const tokenSet = new Set(tokenize(safeInput.text));
    const ambiguousMatches = matchAmbiguous(entities.normalizedInput, tokenSet, ambiguousEntries);

    // Field-labor place/object/action/tool signals (장소 + 대상 + 작업).
    const fieldSig = extractFieldSignals(safeInput.text, fieldLex);

    let occTerms = entities.occupationTerms.slice();
    let indTerms = entities.industryTerms.slice();
    ambiguousMatches.forEach((m) => {
      const dec = m.entry.decompose || {};
      (dec.occupation_terms || []).forEach((t) => occTerms.push(normalize(t)));
      (dec.industry_terms || []).forEach((t) => indTerms.push(normalize(t)));
    });
    // Field signals contribute VERIFIED retrieval keywords on both tracks.
    fieldSig.occupationTerms.forEach((t) => occTerms.push(t));
    fieldSig.industryTerms.forEach((t) => indTerms.push(t));
    occTerms = uniq(occTerms);
    indTerms = uniq(indTerms);

    // Merge sensitivity + confidence cap from concepts AND ambiguous entries.
    const legalSensitivity = uniq([
      ...(entities.legalSensitivity || []),
      ...ambiguousMatches.map((m) => m.entry.legal_sensitivity)
    ]);
    entities.legalSensitivity = legalSensitivity;
    const caps = uniq([entities.confidenceCap, ...ambiguousMatches.map((m) => m.entry.confidence_cap)]);
    const confidenceCap = caps.includes('low') ? 'low' : (caps.includes('medium') ? 'medium' : null);
    const occCaveats = uniq([
      ...entities.candidateCaveats.occupation,
      ...ambiguousMatches.map((m) => m.entry.candidate_caveat_occupation || m.entry.candidate_caveat)
    ]);
    const indCaveats = uniq([
      ...entities.candidateCaveats.industry,
      ...ambiguousMatches.map((m) => m.entry.candidate_caveat_industry || m.entry.candidate_caveat)
    ]);

    const occupationCandidates = searchTrack(index, 'occupation', safeInput.text, occTerms, {
      limit: 5, sourceMeta: occMeta, confidenceCap, caveats: occCaveats
    });
    const industryCandidates = searchTrack(index, 'industry', safeInput.text, indTerms, {
      limit: 5, sourceMeta: indMeta, confidenceCap, caveats: indCaveats
    });

    // Analyzer mode (field_labor / arts_entertainment / service / professional /
    // ambiguous) decides the banner, which forks to ask, and how empty results are
    // explained.
    const mode = detectMode(entities, fieldSig);
    const locale = entities.language === 'en' ? 'en' : 'ko';

    // Field-labor fork questions come first (one targeted question at a time), then
    // the concept-driven ambiguity follow-ups.
    const firedRules = evaluateDisambiguation(fieldSig, disambiguationRules);
    const fieldQuestions = firedRules.map((r) => ({
      flag: r.id,
      topic: r.topic,
      question: (locale === 'en' && r.question_en) ? r.question_en : r.question_ko,
      chips: r.chips || []
    }));
    const conceptQuestions = buildAmbiguity(entities, occupationCandidates, industryCandidates, lexicon, ambiguousMatches);
    // Show the single most relevant field fork up front; keep concept follow-ups too,
    // but never flood the user — cap the whole list.
    const ambiguityQuestions = [...fieldQuestions.slice(0, 1), ...conceptQuestions, ...fieldQuestions.slice(1)].slice(0, 3);

    const followUpChips = buildFollowUpChips(entities, ambiguousMatches);
    const warnings = buildWarnings(safeInput, entities, occupationCandidates, industryCandidates, context);
    const sourceNotes = [
      ...buildSourceNotes(sources || { occupation: occMeta, industry: indMeta }, context),
      ...buildLegalNotes(legalSources, legalSensitivity)
    ];

    // No official code found, but the input was understood (signals/concepts present)
    // → drive the "공식 코드 확인 필요" state instead of a bare "검색 결과 없음".
    const hasSignals = fieldSig.matched.length > 0 || (entities.matchedConcepts || []).length > 0 ||
      !!entities.jobRole || !!entities.workplaceType;
    const noOfficialCodeFound = occupationCandidates.length === 0 && industryCandidates.length === 0;
    const sourceStatus = noOfficialCodeFound
      ? (hasSignals ? 'needs_confirmation' : 'no_match')
      : 'official_list';

    const parsedInterpretation = buildParsedInterpretation(entities, fieldSig, mode, locale);
    const clarificationRequired = ambiguityQuestions.length > 0;
    const clarificationQuestion = clarificationRequired ? ambiguityQuestions[0].question : null;

    const incomeReportingNote = incomeBrackets
      ? (locale === 'en' ? incomeBrackets.reminder_en : incomeBrackets.reminder_ko)
      : (locale === 'en'
        ? 'HiKorea employment reporting also requires an annual income bracket alongside occupation and industry (pre-tax). Report a change only when the bracket changes.'
        : 'HiKorea 취업정보 신고는 직종·업종과 함께 연간소득 구간도 신고합니다(과세 전 기준). 구간이 바뀐 경우에만 변경 신고하세요.');

    // cautionNotes mirrors warnings (spec field name); warnings kept for back-compat.
    const cautionNotes = warnings.slice();

    return {
      input: safeInput.text,
      normalizedInput: entities.normalizedInput,
      detectedLanguage: entities.language,
      mode,
      parsedInterpretation: parsedInterpretation || undefined,
      // Structured field-labor signals (spec: parsedSignals).
      parsedSignals: {
        places: fieldSig.places,
        objects: fieldSig.objects,
        actions: fieldSig.actions,
        tools: fieldSig.tools,
        sectors: [...fieldSig.sectors],
        employerHints: entities.businessActivity ? [entities.businessActivity] : [],
        workSettingHints: entities.workplaceType ? [entities.workplaceType] : [],
        visaContextHints: entities.visaStatus ? [entities.visaStatus] : []
      },
      extracted: {
        language: entities.language,
        jobRole: entities.jobRole || undefined,
        workplaceType: entities.workplaceType || undefined,
        businessActivity: entities.businessActivity || undefined,
        employmentType: entities.employmentType || undefined,
        employmentTypeLabel: entities.employmentTypeLabel || undefined,
        employerType: entities.employerType || undefined,
        incomeStatus: entities.incomeStatus || undefined,
        performanceType: entities.performanceType || undefined,
        roleStatus: entities.roleStatus || undefined,
        legalSensitivity: legalSensitivity.length ? legalSensitivity : undefined,
        visaStatus: entities.visaStatus || undefined
      },
      occupationCandidates,
      industryCandidates,
      incomeReportingNote,
      clarificationRequired,
      clarificationQuestion,
      ambiguityQuestions,
      followUpChips,
      ambiguityFlags: entities.ambiguityFlags,
      matchedConcepts: entities.matchedConcepts,
      // Per-track expanded search terms — exposed so a host UI can feed them into
      // its own scorer (entity-aware retrieval) instead of re-deriving them.
      occupationTerms: occTerms,
      industryTerms: indTerms,
      cautionNotes,
      warnings,
      sourceStatus,
      noOfficialCodeFound,
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
    extractFieldSignals,
    detectMode,
    evaluateDisambiguation,
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
  extractFieldSignals,
  detectMode,
  evaluateDisambiguation,
  buildIndex,
  searchTrack,
  createEmploymentAnalyzer,
  analyzeEmploymentText
};
