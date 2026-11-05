// @ts-nocheck
/**
 * HiKorea 취업정보 신고용 직종(KSCO8)·업종(KSIC11) 참고 검색 — the job-code finder modal (Phase 3, moved
 * verbatim from index.html lines 16904-18154 plus its DOMContentLoaded wiring, lines 24277-24292).
 * Uses the inline globals currentLanguage, tx(), escapeHtml(), hl(), escapeRegExp(), showToast(), openModal(),
 * closeModal(), fallbackCopy(), API_BASE and window.EmploymentCodeAnalyzer / window.EmploymentChecklist
 * (compatibility surface, ADR-009), and Visable.data.fetchJson at event time. Exposed on
 * window.Visable.features.jobcode; the inline stubs with the same names delegate here. One change from the
 * inline text: the lazy import of scripts/employment_interpret_client.mjs is resolved against the document
 * (document.baseURI) instead of the module file so the URL stays /scripts/employment_interpret_client.mjs
 * (ADR-009 addendum). Exercised by scripts/check_employment_reporting_helper.mjs and
 * scripts/check_employment_checklist.mjs (vm sandbox) and tests/golden/specs/tools.spec.mjs.
 */
// --- Job Code Modal · HiKorea 취업정보 신고용 직종(KSCO8)·업종(KSIC11) 참고 검색 ---
// Monochrome pictogram from the modal's SVG sprite (#jc-i-*). Replaces emoji,
// which render differently on every platform and ignore the theme colour.
function jcIcon(name, cls) {
    return `<svg class="jc-ic${cls ? ' ' + cls : ''}" viewBox="0 0 24 24" aria-hidden="true" focusable="false"><use href="#jc-i-${name}"/></svg>`;
}
// The inline copy in this helper exists in Korean, Chinese and English. Every
// other UI language (vi, th, ru, ja, …) reads the English copy rather than
// silently falling back to Korean.
function jcEnLike() { return currentLanguage !== 'ko' && currentLanguage !== 'zh-CN'; }
// Name of a language in the current UI language ("vi" → "베트남어"/"Vietnamese").
function jcLanguageName(code) {
    try {
        const ui = currentLanguage === 'zh-CN' ? 'zh-Hans' : (currentLanguage || 'ko');
        return new Intl.DisplayNames([ui], { type: 'language' }).of(code) || code;
    } catch (_) { return code; }
}
const JOBCODE_TARGET_VISAS = ['E-1','E-2','E-3','E-4','E-5','E-6','E-7','E-8','E-9','E-10','H-1','H-2','D-8','D-9','D-10','F-2','F-4','F-5','F-6'];
let _jobcodeData = null; let _jobcodeLoadPromise = null; let _jcSearchDebounce = null; let _jcAutoAnalyzeDebounce = null;
let _jcFilter = 'all';
let _jcLevel = 'all'; // 'all' | 'leaf' (가장 구체적인 단계 = 세세분류/세분류 leaf 코드만)
let _jcSelected = { occupation: null, industry: null };
let _jcIncome = '';
// Last natural-language analysis + rendered card counts — the source for the
// guided checklist, so selection/income changes can rebuild it without re-running.
let _jcAnalysis = null;
let _jcAnalysisRequest = 0;
let _jcResultCounts = { occupation: null, industry: null };
let _jcClarificationAnswered = false;
// Guided-flow state: idle | analyzing | needs_clarification | showing_candidates.
let _jcFlow = { state: 'idle', revealed: false };
// Canonical job-code dataset (docs/rebuild/phase0-data-canon.md). The former fallbacks
// ./data/output.json, ./jobcode_master.json and ./output.json no longer exist in the repo.
const JOBCODE_JSON_PATHS = ['./data/jobcode_master.json'];
const JOBCODE_STOP_TERMS = new Set(['일','일함','일하는','하는','사람','직원','알바','파트타임','업무','관련','분야','직무','job','work','worker','staff','person','employee','part','time']);
// Terms that legitimately match BOTH a 직종(person's job) and 업종(employer activity).
const JC_AMBIGUOUS_TERMS = new Set(['카페','커피','음식점','식당','레스토랑','학원','호텔','병원','미용실','농장','공장','마트','편의점','술집','주점']);
const JC_TYPE_LABEL = { occupation: '직종', industry: '업종' };
const JC_TYPE_LABEL_EN = { occupation: 'Occupation', industry: 'Industry' };
const JC_TYPE_LABEL_ZH = { occupation: '职业', industry: '行业' };
const JOBCODE_QUERY_EXPANSIONS = [
    { needles: ['개발자','소프트웨어','프로그래머','코딩','웹개발','앱개발','it개발','developer','software','programmer','coding'], terms: ['개발자','소프트웨어','프로그래머','정보 통신','컴퓨터','it','개발','응용 소프트웨어','시스템 소프트웨어','웹'] },
    { needles: ['영어학원','어학원강사','학원강사','영어강사','영어선생','외국어강사','english teacher','language teacher'], terms: ['영어','영어강사','강사','교사','선생','학원','어학원','교육','회화','외국어','어학','외국어학원'] },
    { needles: ['영어','어학원','학원','선생','선생님','교사','강사','가르치','english','teacher','instructor','academy','language','education'], terms: ['강사','교사','선생','학원','어학원','교육','외국어','어학'] },
    { needles: ['식당','음식점','주방','서빙','요리','조리','홀서빙','카페','바리스타','restaurant','kitchen','cook','server','food','cafe','barista','요리사','주방장','셰프','chef'], terms: ['음식','조리','주방','서빙','음식점','웨이터','요리사','식음료','외식','카페','바리스타','커피','조리사','주방장'] },
    // 요리 계열별 업종(KSIC11 세세분류)이 정확히 뜨도록 하는 확장 —
    // "중식당"처럼 요리 계열이 명시된 입력이 한식 등 다른 계열과 동률로 묶이지 않게 한다.
    { needles: ['한식당','한식','한정식','백반','국밥','고깃집','삼겹살','갈비집','korean restaurant','korean bbq'], terms: ['한식','음식점','식당'] },
    { needles: ['중식당','중국집','중식','중화요리','중국음식','짜장면','마라탕','chinese restaurant','chinese food'], terms: ['중식','외국식','음식점','식당'] },
    { needles: ['일식당','일식','일본음식','초밥','스시','돈까스','japanese restaurant','sushi'], terms: ['일식','외국식','음식점','식당'] },
    { needles: ['양식당','양식','이탈리안','파스타','스테이크','western food','italian restaurant','steakhouse'], terms: ['서양식','양식','외국식','음식점','식당'] },
    { needles: ['베트남','태국','인도 음식','인도식당','쌀국수','아시안','vietnamese','thai restaurant','indian restaurant'], terms: ['기타 외국식','외국식','음식점','식당'] },
    { needles: ['분식','김밥','떡볶이','snack bar'], terms: ['김밥','간이 음식점','음식점','식당'] },
    { needles: ['치킨','통닭','chicken'], terms: ['치킨','치킨 전문점','음식점'] },
    { needles: ['피자','햄버거','버거','샌드위치','패스트푸드','pizza','burger','fast food'], terms: ['피자','햄버거','샌드위치','음식점'] },
    { needles: ['빵집','베이커리','제과점','제빵','파티시에','bakery','baker'], terms: ['제과점','제빵사','제과','제빵','음식점'] },
    { needles: ['술집','주점','호프','이자카야','포차','pub','bartender'], terms: ['주점','주점업','음식점'] },
    { needles: ['공장','제조','생산','조립','작업자','라인','factory','manufacturing','production','assembly','operator'], terms: ['제조','생산','조립','기계','공장','제조업','생산직','작업원','조작원'] },
    { needles: ['청소','미화','cleaner','cleaning','housekeeping','환경미화'], terms: ['청소','미화','환경미화','가사','청소부','청소원'] },
    { needles: ['호텔','숙박','객실','리조트','hotel','hospitality','lodging','resort'], terms: ['호텔','숙박','객실','접객','서비스','프런트','리조트','여관','민박'] },
    { needles: ['돌봄','간병','요양','요양보호','요양원','care','caregiver','nursing home'], terms: ['간병','요양','돌봄','요양보호사','사회복지','노인복지','복지시설'] },
    { needles: ['농장','농업','작물','원예','비닐하우스','farm','agriculture','horticulture'], terms: ['농업','농장','작물','재배','축산','원예','농업종사자'] },
    { needles: ['배달','배송','택배','퀵','delivery','courier','logistics'], terms: ['배달','배송','택배','운송','물류','배달원','택배기사'] },
    { needles: ['택시','버스','화물차','트럭','운전기사','driver','taxi','bus'], terms: ['운전','택시','버스','운전기사','자동차','육상운송','화물','운수'] },
    { needles: ['연구원','연구','박사','연구소','researcher','research'], terms: ['연구원','연구','연구사','전문가','기술연구','학술연구'] },
    { needles: ['통번역','번역','통역','번역가','translator','interpreter'], terms: ['번역','통역','번역가','통역사','통번역','외국어','언어'] },
    { needles: ['자영업','자영업자','사장님','상점','가게','점주','소상공인','self-employed'], terms: ['자영업','소매','판매','경영','상점','소규모'] },
    { needles: ['편의점','마트','슈퍼','소매','retail','convenience store'], terms: ['편의점','소매','마트','판매원','소매업','슈퍼마켓'] },
    { needles: ['미용','헤어','네일','뷰티','미용사','헤어디자이너','beauty','hair','nail'], terms: ['미용','헤어','네일','미용사','뷰티','헤어디자이너','미용실'] },
    { needles: ['경비','보안','경호','security','guard','watchman'], terms: ['경비','보안','경호','시설경비','청원경찰','경비원'] },
    { needles: ['간호','간호사','간호조무','nurse','nursing'], terms: ['간호','간호사','간호조무사','병원','의료','보건'] },
    { needles: ['회계','세무','경리','재무','accountant','accounting'], terms: ['회계','세무','경리','재무','회계담당','회계사'] },
    { needles: ['건설','건축','시공','현장','인테리어','construction','builder'], terms: ['건설','건축','시공','인테리어','토목','건설공사','현장'] },
    { needles: ['디자이너','디자인','그래픽','designer','graphic','ux','ui'], terms: ['디자이너','디자인','그래픽','시각','영상','콘텐츠'] }
];
async function loadJobcodeData() {
    if (_jobcodeData) return _jobcodeData;
    if (_jobcodeLoadPromise) return _jobcodeLoadPromise;
    _jobcodeLoadPromise = (async () => {
        const errors = [];
        if (window.location.protocol === 'data:' || window.location.protocol === 'about:') throw new Error("현재 샌드박스 환경에서는 파일 접근 불가");
        for (const path of JOBCODE_JSON_PATHS) {
            try {
                // Data layer (src/data/fetch-json.js): a non-2xx status throws `HTTP <status>`,
                // which the catch below records exactly as before.
                const json = await Visable.data.fetchJson(path, { cache: 'default' });
                if (!json.data || !Array.isArray(json.data)) { errors.push(`${path}: 데이터 형식 오류`); continue; }
                _jobcodeData = json; return json;
            } catch (err) { errors.push(`${path}: ${err.message}`); }
        }
        _jobcodeLoadPromise = null; throw new Error(`로드 실패:\n${errors.join('\n')}`);
    })();
    return _jobcodeLoadPromise;
}
function updateJobcodeNaturalSearchLabel() {
    const label = document.getElementById('jcNaturalSearchLabel');
    if (!label) return;
    label.textContent = API_BASE ? tx('jobCodeNaturalSearchApi') : tx('jobCodeNaturalSearchLocal');
}
function normalizeJobcodeText(value) {
    return String(value || '')
        .toLowerCase()
        .replace(/[(){}\[\],.\/|·•∙:;!?'"`~_+\-=]/g, ' ')
        .replace(/\s+/g, ' ')
        .trim();
}
function addJobcodeTerm(set, term) {
    const normalized = normalizeJobcodeText(term);
    if (!normalized || normalized.length < 2 || JOBCODE_STOP_TERMS.has(normalized)) return;
    set.add(normalized);
}
function getJobcodeSearchTerms(query, extraTerms = []) {
    const q = normalizeJobcodeText(query);
    const terms = new Set();
    addJobcodeTerm(terms, q);
    q.split(/\s+/).forEach(t => addJobcodeTerm(terms, t.replace(/(입니다|이에요|예요|하는|하던|하고|에서|으로|로|은|는|이|가|을|를|의|님)$/g, '')));
    JOBCODE_QUERY_EXPANSIONS.forEach(group => {
        if (group.needles.some(n => q.includes(normalizeJobcodeText(n)))) group.terms.forEach(t => addJobcodeTerm(terms, t));
    });
    extraTerms.forEach(t => addJobcodeTerm(terms, t));
    return [...terms];
}
// new-schema field accessors (type/code/name_ko/search_terms_ko)
function jcName(r) { return r.name_ko || r.상세설명 || ''; }
// Display-only name: prefer the dataset's verified English label (name_en) in
// English mode, falling back to the Korean canonical when no English exists
// (KSCO8/KSIC11 taxonomy is only partially translated upstream). Search/matching
// and the HiKorea memo keep using jcName() so behaviour is unchanged.
function jcDisplayName(r) {
    if (jcEnLike() && r && typeof r.name_en === 'string' && r.name_en.trim()) return r.name_en.trim();
    return jcName(r);
}
function jcCode(r) { return r.code || r.코드값 || ''; }
function jcType(r) { return r.type || (r.분류 === '산업' ? 'industry' : 'occupation'); }
function jcTerms(r) { return Array.isArray(r.search_terms_ko) ? r.search_terms_ko : []; }
function jcLevel(r) { return r.level || ''; }
// 분류 단계 깊이: 대분류(1) → 중분류(2) → 소분류(3) → 세분류(4) → 세세분류(5).
// 숫자가 클수록 더 구체적인 단계 → 검색 시 먼저 인식되도록 가중치/정렬에 사용.
const JC_LEVEL_RANK = { major: 1, middle: 2, minor: 3, unit: 4, detailed_unit: 5 };
function jcLevelRank(r) {
    const lv = jcLevel(r);
    if (JC_LEVEL_RANK[lv]) return JC_LEVEL_RANK[lv];
    return Math.min(jcCode(r).length, 5); // level 필드가 없으면 코드 길이로 깊이 추정
}
// leaf(말단) = 하위 자식이 없는 가장 구체적인 코드. 직종은 세분류, 업종은 세세분류가 말단.
// HiKorea 신고에 실제로 쓰는 코드이므로 '세부코드만' 필터와 강조 표시에 사용.
// ⚠ KSCO8(직종)과 KSIC11(업종)은 같은 숫자 코드를 공유한다(예: 2641 = 직종 '외국어 강사' / 업종 '유선 통신장비 제조업').
//   따라서 부모 집합을 전역으로 모으면 한쪽의 부모 코드가 다른 쪽의 말단 코드를 오판한다.
//   반드시 직종/업종 타입별로 분리해서 부모 집합을 구한다.
function jcLeafParentSets() {
    if (!_jobcodeData) return { occupation: new Set(), industry: new Set() };
    if (_jobcodeData._leafParentSets) return _jobcodeData._leafParentSets;
    const sets = { occupation: new Set(), industry: new Set() };
    _jobcodeData.data.forEach(r => {
        if (!r.parent_code) return;
        const t = jcType(r);
        (sets[t] || (sets[t] = new Set())).add(r.parent_code);
    });
    _jobcodeData._leafParentSets = sets;
    return sets;
}
function jcIsLeaf(r) {
    const set = jcLeafParentSets()[jcType(r)];
    return set ? !set.has(jcCode(r)) : true;
}
// 공식 명칭 조각이 너무 일반적이어서 쿼리 토큰 안에 들어 있어도 관련성 근거가 안 되는 단어들
// (아래 scoreJobcodeRow의 복합어 포함 매칭에서 제외).
const JC_GENERIC_NAME_WORDS = new Set(['및','기타','관련','일반','유사','전문','서비스','종사자','종사원']);
// 행(row) 하나당 정규화된 명칭/코드/동의어/명칭단어를 1회만 계산해 원본 데이터셋 객체에
// 캐싱한다. 검색은 키 입력마다 전체 풀(~1,400건/타입)을 다시 스코어링하므로, 매번
// 동일한 정규식 정규화를 반복하던 부분을 없애 타이핑 반응성을 높인다.
function jcNormalizedRow(row) {
    if (row._jcNorm) return row._jcNorm;
    const name = normalizeJobcodeText(jcName(row));
    const cache = {
        name,
        code: normalizeJobcodeText(jcCode(row)),
        synonyms: jcTerms(row).map(normalizeJobcodeText),
        nameWords: name.split(' ').filter(w => w.length >= 2 && !JC_GENERIC_NAME_WORDS.has(w))
    };
    row._jcNorm = cache;
    return cache;
}
function jcNameWords(row) { return jcNormalizedRow(row).nameWords; }
// normalizedQuery: getScoredJobcodeRows already normalizes the query ONCE for the
// whole pool; pass it through so this per-row function doesn't re-run the same
// regex-heavy normalization for every row (previously O(pool size) redundant work
// per keystroke). Falls back to normalizing `query` itself for any other caller.
function scoreJobcodeRow(row, query, terms, normalizedQuery) {
    const { name, code, synonyms } = jcNormalizedRow(row);
    const q = normalizedQuery !== undefined ? normalizedQuery : normalizeJobcodeText(query);
    let score = 0;
    if (q && code === q) score += 1200;
    else if (q && code.startsWith(q)) score += 220;
    if (q && name === q) score += 520;
    else if (q.length >= 2 && name.includes(q)) score += 180 + Math.min(q.length, 20);
    if (q && synonyms.includes(q)) score += 360;
    const nameWords = jcNameWords(row);
    terms.forEach(term => {
        if (code === term) score += 900;
        else if (/^[0-9]+$/.test(term) && code.startsWith(term)) score += 160;
        if (name === term) score += 260;
        else if (name.includes(term)) score += 50 + Math.min(term.length * 4, 36);
        if (synonyms.includes(term)) score += 120;
        // 복합어 포함 매칭: "중식당" ⊃ "중식", "일식집" ⊃ "일식"처럼 교착어 토큰이
        // 공식 명칭 단어를 품고 있으면 가점 (토큰당 1회, 한글 3자 이상만).
        // 조사가 붙은 토큰("학원에서")은 제외 — 조사 제거형("학원")이 이미 참여하고,
        // 원형을 넣으면 명칭에 그 단어가 홀로 남은 행만 불공평하게 가점받는다.
        if (term.length >= 3 && /[가-힣]/.test(term) && !/(입니다|이에요|예요|하는|하던|하고|에서|으로|로|은|는|이|가|을|를|의|님)$/.test(term)) {
            for (const w of nameWords) {
                if (w !== term && term.includes(w)) { score += 70; break; }
            }
        }
    });
    // 관련성이 있을 때만, 더 구체적인 단계(세세분류 > 세분류 > … > 대분류)를 위로 끌어올린다.
    if (score > 0) {
        score += jcLevelRank(row) * 28;
        if (jcIsLeaf(row)) score += 90; // 실제 신고에 쓰는 말단 코드를 최우선으로 노출
    }
    return score;
}
function getScoredJobcodeRows(type, query, terms, limit = 60) {
    if (!_jobcodeData) return [];
    const q = normalizeJobcodeText(query);
    let pool = _jobcodeData.data.filter(r => jcType(r) === type);
    // '세부코드만' 단계 필터: 말단(가장 구체적인) 코드만 남긴다.
    if (_jcLevel === 'leaf') pool = pool.filter(jcIsLeaf);
    if (!q && (!terms || !terms.length)) {
        if (_jcLevel === 'leaf') {
            // 검색어 없이 세부코드만 볼 때: 코드순으로 일부만 둘러보기
            return pool.slice().sort((a, b) => jcCode(a).localeCompare(jcCode(b))).slice(0, limit);
        }
        // default browse: show top-level (대분류) categories
        return pool.filter(r => (r.level ? r.level === 'major' : jcCode(r).length === 1))
            .sort((a, b) => jcCode(a).localeCompare(jcCode(b)));
    }
    return pool
        .map(r => ({ row: r, score: scoreJobcodeRow(r, query, terms || [], q) }))
        .filter(x => x.score > 0)
        // 점수 동률이면 더 구체적인 단계(세세분류)를 먼저 노출.
        .sort((a, b) => b.score - a.score || jcLevelRank(b.row) - jcLevelRank(a.row) || jcCode(a.row).localeCompare(jcCode(b.row)))
        .slice(0, limit)
        .map(x => Object.assign({}, x.row, { _score: x.score }));
}
function jcMatchReason(row, query, terms) {
    const q = normalizeJobcodeText(query);
    const name = normalizeJobcodeText(jcName(row));
    const code = normalizeJobcodeText(jcCode(row));
    if (q && (code === q || code.startsWith(q)) && /[0-9a-z]/.test(q)) return `코드 ‘${escapeHtml(query.trim())}’ 일치`;
    if (q && name.includes(q)) return '';
    const syn = jcTerms(row).find(t => terms.includes(normalizeJobcodeText(t)) && !name.includes(normalizeJobcodeText(t)));
    if (syn) return `‘${escapeHtml(syn)}’ 관련`;
    return '';
}
function jcSelectedCode(type) { return _jcSelected[type] ? _jcSelected[type].code : null; }
// Friendly confidence label relative to the best candidate in the pane.
function jcConfLabel(row, top) {
    if (row._confidence) return { key: `conf.${row._confidence === 'medium' ? 'mid' : row._confidence}`, cls: `is-${row._confidence === 'medium' ? 'mid' : row._confidence}` };
    const s = row._score || 0;
    const r = top > 0 ? s / top : 0;
    if (r >= 0.8) return { key: 'conf.high', cls: 'is-high' };
    if (r >= 0.45) return { key: 'conf.mid', cls: 'is-mid' };
    return { key: 'conf.low', cls: 'is-low' };
}
// Plain-language "this may fit when / another may fit when" parts for a card.
function jcCardHelp(type, isLeaf) {
    const en = jcEnLike();
    const zh = currentLanguage === 'zh-CN';
    return {
        fitLabel: jcChecklistCopy('card.fit'),
        fitText: type === 'occupation'
            ? (zh ? '与你实际所做的工作相近时' : en ? 'this is close to what you actually do' : '내가 실제로 하는 일과 비슷할 때')
            : (zh ? '与公司·营业场所所做的业务相近时' : en ? 'this is close to your employer/business activity' : '회사·사업장이 하는 일과 비슷할 때'),
        otherLabel: jcChecklistCopy('card.other'),
        otherText: isLeaf
            ? (zh ? '若下方相似项目更合适，请比较后选择' : en ? 'a similar item fits better — compare them' : '아래 비슷한 항목이 더 맞으면 비교해서 고르기')
            : (zh ? '若有更具体的细分代码，请选择那个' : en ? 'a more specific (detailed) code exists — pick that' : '더 구체적인 세부코드가 있으면 그걸 고르기')
    };
}
// opts.conf = { key, cls } confidence band computed by renderJobcodeList.
function renderJobcodeCard(row, query, terms, opts = {}) {
    const en = jcEnLike();
    const zh = currentLanguage === 'zh-CN';
    const type = jcType(row);
    const code = jcCode(row);
    const name = jcDisplayName(row);
    const lvLabel = (zh
        ? ({ major:'大分类', middle:'中分类', minor:'小分类', unit:'细分类', detailed_unit:'细细分类' })[row.level]
        : (en ? row.level_label_en : row.level_label_ko) || (en
            ? ({ major:'Major group', middle:'Sub-major group', minor:'Minor group', unit:'Unit group', detailed_unit:'Detailed unit' })[row.level]
            : ({ major:'대분류', middle:'중분류', minor:'소분류', unit:'세분류', detailed_unit:'세세분류' })[row.level])) || '';
    const badge = type === 'occupation'
        ? `<span class="jc2-tb jc2-tb--occ">${zh ? '职业' : en ? 'Occupation' : '직종'}</span>`
        : `<span class="jc2-tb jc2-tb--ind">${zh ? '行业' : en ? 'Industry' : '업종'}</span>`;
    const isLeaf = jcIsLeaf(row);
    const conf = opts.conf || jcConfLabel(row, row._score || 1);
    const confChip = `<span class="jc2-conf ${conf.cls}">${escapeHtml(jcChecklistCopy(conf.key))}</span>`;
    const leafTag = isLeaf ? `<span class="jc2-lvl jc2-lvl--report" title="${zh ? '最具体的层级 — HiKorea 申报时实际使用的代码' : en ? 'Most specific level — the code actually used for HiKorea reporting' : '가장 구체적인 단계 — HiKorea 신고에 실제로 쓰는 코드입니다'}">${jcIcon('target')}${zh ? '申报用细分代码' : en ? 'Reporting sub-code' : '신고용 세부코드'}</span>` : '';
    const srcChip = `<span class="jc2-src">${jcIcon('check')}${escapeHtml(jcChecklistCopy('card.source'))}</span>`;
    const reason = jcMatchReason(row, query, terms);
    const why = reason ? `<div class="jc2-card-why">${reason}</div>` : '';
    const h = jcCardHelp(type, isLeaf);
    const fit = `<div class="jc2-card-fit">${jcIcon('check-circle')}<span><b>${escapeHtml(h.fitLabel)}</b>: ${escapeHtml(h.fitText)}</span></div>`;
    const path = row.path_ko ? `<div class="jc2-card-path">${escapeHtml(row.path_ko)}</div>` : '';
    // Progressive disclosure: the longer caveat + path hide behind "자세히 보기".
    const meta = `<div class="jc2-card-meta">${escapeHtml(lvLabel)} · ${srcChip}${leafTag ? ' ' + leafTag : ''}</div>`;
    const details = `<details class="jc2-card-more"><summary>${escapeHtml(jcChecklistCopy('card.detail'))}</summary>`
        + meta + fit
        + `<div class="jc2-card-other">${jcIcon('swap')}<span><b>${escapeHtml(h.otherLabel)}</b>: ${escapeHtml(h.otherText)}</span></div>${path}</details>`;
    const isSel = jcSelectedCode(type) === code;
    // Non-Korean UI shows the translated name first; the Korean official name
    // stays underneath because that is what the HiKorea screen lists.
    const koName = jcName(row);
    const koLine = name !== koName ? `<div class="jc2-card-name-ko" lang="ko">${escapeHtml(koName)}</div>` : '';
    return `<div class="jc2-card${isLeaf ? ' jc2-card--leaf' : ''}" role="listitem" data-type="${type}" data-code="${escapeHtml(code)}">
        <div class="jc2-card-top"><span class="jc2-code">${escapeHtml(code)}</span>${badge}${confChip}</div>
        <div class="jc2-card-name">${hl(name, terms || [])}</div>${koLine}
        ${why}${details}
        <button type="button" class="jc2-select${isSel ? ' is-sel' : ''}" data-action="select-jobcode" data-type="${type}" data-code="${escapeHtml(code)}" aria-pressed="${isSel}">${jcSelectLabel(isSel)}</button>
    </div>`;
}
function jcSelectLabel(selected) {
    const zh = currentLanguage === 'zh-CN', en = jcEnLike();
    return selected
        ? jcIcon('check') + escapeHtml(zh ? '已选择' : en ? 'Selected' : '선택됨')
        : escapeHtml(zh ? '选这个' : en ? 'Choose this' : '이걸로 선택');
}
function jobcodeEmptyHtml(type) {
    const en = jcEnLike();
    const zh = currentLanguage === 'zh-CN';
    return `<div class="jc2-empty"><b>${escapeHtml(tx('jobCodeEmptyTitle'))}</b>${escapeHtml(tx('jobCodeEmptyHint'))}
        <ul>
            <li>${escapeHtml(type === 'occupation' ? (zh ? '按职务名称搜索（例：讲师、厨师、开发）' : en ? 'Search by job title (e.g. instructor, cook, developer)' : '직무명으로 검색 (예: 강사, 요리사, 개발)') : (zh ? '按公司行业搜索（例：教育、餐饮、制造）' : en ? 'Search by company industry (e.g. education, restaurant, manufacturing)' : '회사 업종으로 검색 (예: 교육, 음식점, 제조)'))}</li>
            <li>${zh ? '用更短的词搜索' : en ? 'Search with shorter words' : '더 짧은 단어로 검색'}</li>
            <li>${zh ? '点击推荐标签试试' : en ? 'Try the suggested chips' : '추천 칩을 눌러보기'}</li>
        </ul></div>`;
}
// opts: true (legacy) or { collapse, ambiguous }. collapse → guided AI layout
// (top recommendation vs alternatives, top 2 visible, rest behind "더 보기").
function renderJobcodeList(rows, box, type, query, terms, opts = {}) {
    if (!box) return;
    if (typeof opts === 'boolean') opts = { collapse: opts };
    // Guided results show two cards plus "더 보기", so they flow with the page;
    // only the long browse list keeps its own scroll area.
    box.classList.toggle('is-guided', !!opts.collapse);
    if (!rows.length) { box.innerHTML = jobcodeEmptyHtml(type); return; }
    const MAX = 60;
    const top = rows[0] ? (rows[0]._score || 0) : 0;
    const card = (r) => renderJobcodeCard(r, query, terms, { conf: jcConfLabel(r, top) });
    const groupHead = (label) => `<div class="jc2-group-head">${escapeHtml(label)}</div>`;

    if (opts.collapse) {
        // Reporting-level (leaf) codes first; show top 2, hide the rest under "더 보기".
        const ordered = [...rows.filter(jcIsLeaf), ...rows.filter(r => !jcIsLeaf(r))].slice(0, MAX);
        const ambiguous = !!opts.ambiguous;
        // One recommendation when the reading is clear; two when it genuinely isn't.
        const nVisible = ambiguous ? 2 : 1;
        const visible = ordered.slice(0, nVisible);
        const hidden = ordered.slice(nVisible);
        let html = '', othersShown = false;
        if (ambiguous) {
            // Avoid false certainty: don't single out a "closest" candidate.
            html += groupHead(jcChecklistCopy('group.several'));
            html += visible.map(card).join('');
        } else {
            html += groupHead(jcChecklistCopy('group.top'));
            html += card(visible[0]);
            if (visible[1]) { html += groupHead(jcChecklistCopy('group.others')); othersShown = true; html += card(visible[1]); }
        }
        if (hidden.length) {
            html += `<button type="button" class="jc2-more-btn" aria-expanded="false">${escapeHtml(jcChecklistCopy('more.show'))}</button>`;
            html += `<div class="jc2-more" hidden>` + ((!ambiguous && !othersShown) ? groupHead(jcChecklistCopy('group.others')) : '') + hidden.map(card).join('') + `</div>`;
        }
        box.innerHTML = html;
        const moreBtn = box.querySelector('.jc2-more-btn');
        if (moreBtn) moreBtn.onclick = () => {
            const more = box.querySelector('.jc2-more');
            const show = more.hidden; more.hidden = !show;
            moreBtn.setAttribute('aria-expanded', String(show));
            moreBtn.textContent = show ? jcChecklistCopy('more.hide') : jcChecklistCopy('more.show');
        };
        return;
    }
    // Browse mode (direct keyword filter): flat list, capped.
    const html = rows.slice(0, MAX).map(card).join('');
    box.innerHTML = html + (rows.length > MAX ? `<div class="jc2-empty" style="padding:0.7rem;">${currentLanguage === 'zh-CN' ? `※ 仅显示前 ${MAX} 项。请输入更具体的搜索词。` : jcEnLike() ? `※ Showing top ${MAX} only. Enter a more specific search term.` : `※ 상위 ${MAX}건만 표시. 검색어를 더 구체적으로 입력하세요.`}</div>` : '');
}
function setJobcodeFilter(filter) {
    _jcFilter = ['all', 'occupation', 'industry'].includes(filter) ? filter : 'all';
    const root = document.querySelector('#jobCodeModalOverlay .jc2');
    if (root) {
        root.classList.toggle('jc-filter-occupation', _jcFilter === 'occupation');
        root.classList.toggle('jc-filter-industry', _jcFilter === 'industry');
    }
    [['all','jcFilterAll'],['occupation','jcFilterOcc'],['industry','jcFilterInd']].forEach(([f,id]) => {
        const b = document.getElementById(id);
        if (b) { const on = f === _jcFilter; b.classList.toggle('is-on', on); b.setAttribute('aria-selected', String(on)); }
    });
    const input = document.getElementById('jcSearchInput');
    renderJobcodeResults(input ? input.value : '');
}
function setJobcodeLevel(level) {
    _jcLevel = level === 'leaf' ? 'leaf' : 'all';
    [['all','jcLevelAll'],['leaf','jcLevelLeaf']].forEach(([f,id]) => {
        const b = document.getElementById(id);
        if (b) { const on = f === _jcLevel; b.classList.toggle('is-on', on); b.setAttribute('aria-selected', String(on)); }
    });
    const input = document.getElementById('jcSearchInput');
    renderJobcodeResults(input ? input.value : '');
}
// 자연어 입력 판정: 여러 단어이거나 한글 4자 이상이면 키워드 필터보다 자연어 분석기가
// 더 잘 처리하므로, 입력이 멈추면 버튼을 누르지 않아도 자동으로 분석을 실행한다.
function jcLooksNaturalQuery(q) {
    const t = (q || '').trim();
    if (t.length < 4) return false;
    return /\s/.test(t) || /[가-힣]{4,}/.test(t);
}
function searchJobcodeChip(term) {
    const input = document.getElementById('jcSearchInput');
    if (!input) return;
    // Cancel any debounced render/auto-analyze still pending from prior typing —
    // setting .value here doesn't fire an 'input' event, so a stale timer from
    // before this click could otherwise fire afterward and clobber this chip's
    // results with an outdated (or empty-query browse) render.
    clearTimeout(_jcSearchDebounce); clearTimeout(_jcAutoAnalyzeDebounce);
    input.value = term;
    input.focus();
    // Multi-word / natural-language chips (e.g. "택배 상하차 해요", "카페 바리스타")
    // run the full analyzer so interpretation + decomposition + cautions show;
    // single keyword chips keep the instant filter.
    if (/\s/.test(term.trim()) || term.trim().length >= 3) searchJobcodeWithAI();
    else renderJobcodeResults(term);
}
async function openJobCodeModal() {
    openModal('jobCodeModalOverlay');
    updateJobcodeNaturalSearchLabel();
    _jcFilter = 'all'; _jcLevel = 'all'; _jcSelected = { occupation: null, industry: null }; _jcIncome = '';
    _jcAnalysis = null; _jcResultCounts = { occupation: null, industry: null }; _jcClarificationAnswered = false;
    _jcFlow = { state: 'idle', revealed: false };
    jcResetAnswered();
    jcSetStep('ask');
    setJobcodeFilter('all');
    setJobcodeLevel('all');
    const input = document.getElementById('jcSearchInput');
    if (input) { input.value = ''; setTimeout(() => input.focus(), 100); }
    const incomeSel = document.getElementById('jcIncome'); if (incomeSel) incomeSel.value = '';
    renderJobcodeSelectedSummary();
    clearEmploymentAnalysisUI();
    renderEmploymentChecklist();   // initial state: 4 steps, all pending
    jcApplyFlow();                 // idle: hide gate / candidates-onward sections
    const jobBox = document.getElementById('jcJobResults'), indBox = document.getElementById('jcIndResults');
    if (jobBox) jobBox.innerHTML = `<div class="jc2-loading">${escapeHtml(tx('jobCodeLoading'))}</div>`;
    if (indBox) indBox.innerHTML = `<div class="jc2-loading">${escapeHtml(tx('jobCodeLoading'))}</div>`;
    try {
        await loadJobcodeData();
        const coverageEl = document.getElementById('jcCoverageNote');
        if (coverageEl && _jobcodeData) {
            const en = jcEnLike();
            const zh = currentLanguage === 'zh-CN';
            const occ = (_jobcodeData.categories || {})['직종'] || 0;
            const ind = (_jobcodeData.categories || {})['업종'] || 0;
            const occFull = _jobcodeData.occupation_source && _jobcodeData.occupation_source.full_table_loaded;
            const occNote = zh
                ? (occFull ? '职业完整表' : '职业大·中分类')
                : en
                ? (occFull ? 'occupation full table' : 'occupation major/sub groups')
                : (occFull ? '직종 전체표' : '직종 대·중분류');
            coverageEl.textContent = zh
                ? `依据 KSCO8·KSIC11 · ${occNote} ${occ} 项 · 行业 ${ind} 项 · 最终代码务必在 HiKorea/1345 确认`
                : en
                ? `Based on KSCO8·KSIC11 · ${occNote} ${occ} · industry ${ind} · always confirm the final code with HiKorea/1345`
                : `기준 KSCO8·KSIC11 · ${occNote} ${occ}건 · 업종 ${ind}건 · 최종 코드는 HiKorea/1345 확인 필수`;
        }
        renderJobcodeResults('');
    } catch (err) {
        const errorHtml = `<div class="jc2-empty" style="color:var(--color-error);">${jcIcon('alert')} <b>${currentLanguage === 'zh-CN' ? '数据加载失败' : jcEnLike() ? 'Data load failed' : '데이터 로드 실패'}</b><br><small>${escapeHtml(err.message)}</small></div>`;
        if (jobBox) jobBox.innerHTML = errorHtml; if (indBox) indBox.innerHTML = errorHtml;
    }
}
function renderJobcodeGuidance(query, jobRows, indRows) {
    const q = (query || '').trim();
    const ambEl = document.getElementById('jcAmbiguity');
    const warnEl = document.getElementById('jcBoundaryWarn');
    // E-7 / visa boundary warning
    const looksVisa = /\be-?\d/i.test(q) || /[a-z]-\d/i.test(q) || /비자|사증|visa/i.test(q);
    if (warnEl) {
        if (looksVisa) { warnEl.hidden = false; warnEl.innerHTML = tx('jobCodeBoundaryWarn'); }
        else warnEl.hidden = true;
    }
    // ambiguity guidance
    if (ambEl) {
        const nq = normalizeJobcodeText(q);
        const isAmbiguousTerm = [...JC_AMBIGUOUS_TERMS].some(t => nq && (nq === normalizeJobcodeText(t) || nq.includes(normalizeJobcodeText(t))));
        const matchesBoth = q && jobRows.length > 0 && indRows.length > 0;
        if (q && (isAmbiguousTerm || matchesBoth)) {
            ambEl.hidden = false;
            ambEl.innerHTML = tx('jobCodeAmbiguity');
        } else ambEl.hidden = true;
    }
}
// After a search, the starter helpers (examples, explainer) have done their job:
// fold them away and bring the answer into view. On a phone the first result
// otherwise sits below several screens of help text.
function jcRevealAnswer() {
    const root = document.querySelector('#jobCodeModalOverlay .jc2');
    if (!root) return;
    root.classList.add('jc2--answered', 'jc2--has-query');
    jcSetStep('result');
}
// Two screens. 'ask' = the question and the input, nothing else. 'result' =
// what Visable understood, one recommendation per side, the memo. The input
// is hidden on 'result' so a slow typist never sees the screen change under
// them; "다시 적기" is the one way back.
function jcSetStep(step) {
    const root = document.querySelector('#jobCodeModalOverlay .jc2');
    if (!root) return;
    root.dataset.jcStep = step === 'result' ? 'result' : 'ask';
    if (step !== 'result') root.classList.remove('jc2--answered');
    const bar = document.getElementById('jcStepbar');
    if (bar) bar.hidden = step !== 'result';
    const said = document.getElementById('jcYouSaid');
    const input = document.getElementById('jcSearchInput');
    if (said) said.textContent = input ? input.value.trim() : '';
    const body = root.closest('.modal-body') || root;
    if (body && typeof body.scrollTo === 'function') { try { body.scrollTo({ top: 0 }); } catch (_) { body.scrollTop = 0; } }
}
function jcGoBackToAsk() {
    jcSetStep('ask');
    const input = document.getElementById('jcSearchInput');
    if (input) { input.focus(); if (typeof input.select === 'function') input.select(); }
}
function jcResetAnswered() {
    const root = document.querySelector('#jobCodeModalOverlay .jc2');
    if (root) root.classList.remove('jc2--answered');
}
function jcSetHasQuery(on) {
    const root = document.querySelector('#jobCodeModalOverlay .jc2');
    if (root) root.classList.toggle('jc2--has-query', !!on);
}
function renderJobcodeResults(query) {
    if (!(query || '').trim()) jcResetAnswered();
    jcSetHasQuery((query || '').trim());
    const jobBox = document.getElementById('jcJobResults'), indBox = document.getElementById('jcIndResults'), badge = document.getElementById('jcCountBadge');
    if (!jobBox || !indBox || !_jobcodeData) return;
    const q = (query || '').trim();
    const terms = getJobcodeSearchTerms(q);
    const jobRows = getScoredJobcodeRows('occupation', q, terms);
    const indRows = getScoredJobcodeRows('industry', q, terms);
    renderJobcodeList(jobRows, jobBox, 'occupation', q, terms);
    renderJobcodeList(indRows, indBox, 'industry', q, terms);
    renderJobcodeGuidance(q, jobRows, indRows);
    if (typeof clearEmploymentAnalysisUI === 'function') clearEmploymentAnalysisUI();
    if (badge) {
        const en = jcEnLike();
        const zh = currentLanguage === 'zh-CN';
        const occL = zh ? '职业' : en ? 'Occupation' : '직종', indL = zh ? '行业' : en ? 'Industry' : '업종';
        if (_jcFilter === 'occupation') badge.textContent = `${occL} ${jobRows.length}`;
        else if (_jcFilter === 'industry') badge.textContent = `${indL} ${indRows.length}`;
        else badge.textContent = q ? `${occL} ${jobRows.length} · ${indL} ${indRows.length}` : (zh ? '查看全部' : en ? 'View all' : '전체 보기');
        badge.hidden = !q;
    }
    const hintEl = document.getElementById('jcAiHint');
    if (hintEl) {
        const total = jobRows.length + indRows.length;
        const leafTotal = jobRows.filter(r => jcIsLeaf(r)).length + indRows.filter(r => jcIsLeaf(r)).length;
        if (q && q.length >= 2 && (total < 5 || leafTotal === 0)) {
            hintEl.hidden = false;
            hintEl.innerHTML = currentLanguage === 'zh-CN'
                ? `${jcIcon('bulb')} 找不到<b>申报用细分代码</b>？把所做的工作写成一句话再按 <b>Enter</b>，就能找得更准确。（点这里也可以）`
                : jcEnLike()
                ? `${jcIcon('bulb')} Can't find the <b>reporting sub-code</b>? Describe your work in a sentence and press <b>Enter</b> for a more accurate match. (Or tap here.)`
                : `${jcIcon('bulb')} <b>신고용 세부코드</b>를 못 찾으셨나요? 하는 일을 문장으로 적고 <b>Enter</b>를 누르면 더 정확하게 찾아드려요. (여기를 눌러도 돼요)`;
            hintEl.onclick = () => searchJobcodeWithAI();
        } else {
            hintEl.hidden = true;
        }
    }
}
function selectJobcode(type, code) {
    if (!_jobcodeData || !['occupation', 'industry'].includes(type)) return;
    const row = _jobcodeData.data.find(r => jcType(r) === type && jcCode(r) === code);
    if (!row) return;
    _jcSelected[type] = { code, name: jcName(row) };
    renderJobcodeSelectedSummary();
    renderEmploymentChecklist();   // candidate confirmed → step turns complete
    // refresh select-button states in the relevant pane
    const boxId = type === 'occupation' ? 'jcJobResults' : 'jcIndResults';
    const box = document.getElementById(boxId);
    if (box) box.querySelectorAll('.jc2-select').forEach(btn => {
        const on = btn.dataset.code === code;
        btn.classList.toggle('is-sel', on);
        btn.setAttribute('aria-pressed', String(on));
        btn.innerHTML = jcSelectLabel(on);
    });
    const bothPicked = _jcSelected.occupation && _jcSelected.industry;
    // No toast — on a phone it covered the income select and the copy button.
    // The pressed button reads "✓ 선택됨", the summary row (role=status) updates,
    // and the screen moves to the next thing to pick.
    // 한쪽만 골랐으면 나머지(직종↔업종) 후보로 바로 이동 — 휴대폰에서 스크롤로 찾지 않아도 된다.
    if (!bothPicked && _jcFilter === 'all') {
        const otherType = type === 'occupation' ? 'industry' : 'occupation';
        const pane = document.querySelector(`#jobCodeModalOverlay .jc2-pane[data-pane="${otherType}"]`);
        const results = document.getElementById('jcResults');
        if (pane && results && !results.hidden && typeof pane.scrollIntoView === 'function') {
            const reduce = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
            try { pane.scrollIntoView({ behavior: reduce ? 'auto' : 'smooth', block: 'start' }); } catch (_) {}
        }
    }
    // 둘 다 골랐으면 다음 행동(요약 확인 → 메모 복사)으로 부드럽게 안내
    if (bothPicked) {
        const sum = document.getElementById('jcSummary');
        if (sum) {
            if (typeof sum.scrollIntoView === 'function') sum.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
            sum.classList.add('jc2-summary--pulse');
            setTimeout(() => sum.classList.remove('jc2-summary--pulse'), 1400);
        }
    }
}
function renderJobcodeSelectedSummary() {
    const occEl = document.getElementById('jcSelOcc'), indEl = document.getElementById('jcSelInd');
    const setCell = (el, sel) => {
        if (!el) return;
        if (sel) { el.textContent = `${sel.code} · ${sel.name}`; el.classList.add('is-set'); }
        else { el.textContent = currentLanguage === 'zh-CN' ? '尚未选择' : jcEnLike() ? 'Not selected yet' : '아직 선택 안 함'; el.classList.remove('is-set'); }
    };
    setCell(occEl, _jcSelected.occupation);
    setCell(indEl, _jcSelected.industry);
    // Slim sticky bar only once something is picked; before that it sits at the
    // end of the content instead of covering the candidates.
    const sum = document.getElementById('jcSummary');
    if (sum) sum.classList.toggle('is-active', !!(_jcSelected.occupation || _jcSelected.industry));
}
function buildJobcodeMemo() {
    const occ = _jcSelected.occupation, ind = _jcSelected.industry;
    const income = (document.getElementById('jcIncome') || {}).value || '';
    return [
        `직종: ${occ ? occ.code + ' ' + occ.name : '(미선택)'}`,
        `업종: ${ind ? ind.code + ' ' + ind.name : '(미선택)'}`,
        `연간소득: ${income || '(미입력)'}`,
        `주의: 최종 신고 전 HiKorea 화면에서 재확인 필요`
    ].join('\n');
}
function copyJobcodeMemo() {
    const btn = document.getElementById('jcCopyBtn');
    const label = document.getElementById('jcCopyLabel') || btn;
    const text = buildJobcodeMemo();
    const done = () => {
        if (!btn || !label) return;
        const original = label.textContent;
        btn.classList.add('copied');
        label.textContent = currentLanguage === 'zh-CN' ? '已复制' : jcEnLike() ? 'Copied' : '복사됨';
        setTimeout(() => { btn.classList.remove('copied'); label.textContent = original; }, 1600);
    };
    if (navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText(text).then(done).catch(() => { fallbackCopy(text); done(); });
    else { fallbackCopy(text); done(); }
}
// --- Deterministic natural-language analyzer bridge (scripts/employment_code_analyzer.mjs) ---
// The analyzer module attaches window.EmploymentCodeAnalyzer when loaded. We lazily
// fetch the alias lexicon + source metadata and bind an analyzer to the already
// loaded jobcode dataset. It powers the entity interpretation, ambiguity chips and
// HiKorea tips; it also feeds entity-aware terms into the existing scorer.
let _empLex = null, _empSources = null, _empAnalyzer = null, _empLoadPromise = null;
async function ensureEmploymentAnalyzer() {
    if (_empAnalyzer) return _empAnalyzer;
    if (!window.EmploymentCodeAnalyzer || !window.EmploymentCodeAnalyzer.createEmploymentAnalyzer) return null;
    if (_empLoadPromise) return _empLoadPromise;
    _empLoadPromise = (async () => {
        if (!_jobcodeData) { try { await loadJobcodeData(); } catch (_) { _empLoadPromise = null; return null; } }
        const grab = (p) => Visable.data.fetchJson(p, { cache: 'default' }).catch(() => null);
        // Base aliases + entertainment + tattoo alias packs + umbrella/ambiguous
        // inputs + field-labor place/object/action lexicon + fork disambiguation
        // rules + income reminder + source/legal metadata, merged the same way the
        // Node loader (scripts/employment_data_loader.mjs) does.
        const [koBase, enBase, zhBase, koEnt, enEnt, koTat, enTat, amb, src, fieldKo, fieldEn, disamb, income, pivot] = await Promise.all([
            grab('./data/employment/synonyms.ko.json'),
            grab('./data/employment/synonyms.en.json'),
            grab('./data/employment/synonyms.zh.json'),
            grab('./data/employment/aliases.entertainment.ko.json'),
            grab('./data/employment/aliases.entertainment.en.json'),
            grab('./data/employment/aliases.tattoo.ko.json'),
            grab('./data/employment/aliases.tattoo.en.json'),
            grab('./data/employment/ambiguous_inputs.json'),
            grab('./data/employment/classification_sources.json'),
            grab('./data/employment/colloquial_field_terms_ko.json'),
            grab('./data/employment/colloquial_field_terms_en.json'),
            grab('./data/employment/disambiguation_rules.json'),
            grab('./data/employment/income_brackets.json'),
            // Foreign-language work phrases → Korean retrieval words (no codes).
            grab('./data/employment/multilingual_pivot.json')
        ]);
        const cc = (o) => (o && Array.isArray(o.concepts) ? o.concepts : []);
        _empLex = {
            ko: { concepts: [...cc(koBase), ...cc(koEnt), ...cc(koTat)] },
            en: { concepts: [...cc(enBase), ...cc(enEnt), ...cc(enTat)] },
            // Chinese pool — without it, Chinese descriptions matched nothing at all.
            zh: { concepts: [...cc(zhBase)] }
        };
        _empSources = src;
        _empAnalyzer = window.EmploymentCodeAnalyzer.createEmploymentAnalyzer({
            data: _jobcodeData, lexicon: _empLex, sources: src,
            ambiguous: amb || { entries: [] },
            legalSources: (src && src.legal_sources) || [],
            context: _jobcodeData && _jobcodeData.employment_reporting_context,
            fieldTerms: { ko: fieldKo || { signals: [] }, en: fieldEn || { signals: [] } },
            disambiguation: disamb || { rules: [] },
            incomeBrackets: income || null,
            pivot: pivot || null
        });
        return _empAnalyzer;
    })();
    return _empLoadPromise;
}
const JC_CONF_LABEL = { high: '높음', medium: '보통', low: '낮음' };
const JC_MODE_LABEL = {
    field_labor_mode: '현장·작업 기준 분석',
    professional_mode: '전문·사무직 분석',
    service_mode: '서비스·접객 분석',
    arts_entertainment_mode: '예술·공연 분석',
    ambiguous_mode: '추가 정보 필요'
};
const JC_MODE_LABEL_EN = {
    field_labor_mode: 'Field/manual-work analysis',
    professional_mode: 'Professional/office analysis',
    service_mode: 'Service/hospitality analysis',
    arts_entertainment_mode: 'Arts/performance analysis',
    ambiguous_mode: 'More information needed'
};
const JC_MODE_LABEL_ZH = {
    field_labor_mode: '现场·作业类分析',
    professional_mode: '专业·办公职分析',
    service_mode: '服务·接待类分析',
    arts_entertainment_mode: '艺术·演出类分析',
    ambiguous_mode: '需要补充信息'
};
function renderEmploymentInterpretation(analysis) {
    const el = document.getElementById('jcInterpret');
    if (!el) return;
    if (!analysis) { el.hidden = true; el.innerHTML = ''; return; }
    const e = analysis.extracted || {};
    const ps = analysis.parsedSignals || {};
    const en = jcEnLike();
    const zh = currentLanguage === 'zh-CN';
    const SENS_LABEL = zh
        ? { tattoo: '纹身·刺青（法律敏感）', entertainment: '演艺·演出（需另行审查）' }
        : en
        ? { tattoo: 'Tattoo work (legally sensitive)', entertainment: 'Entertainment/performance (separate review)' }
        : { tattoo: '문신·타투(법적 민감)', entertainment: '연예·공연(별도 검토)' };
    const sens = (e.legalSensitivity || []).map(s => SENS_LABEL[s] || s).join(', ');
    const sigLine = (arr) => (Array.isArray(arr) ? arr.map(x => x && (x.label || x)).filter(Boolean).join(', ') : '');
    const isField = analysis.mode === 'field_labor_mode';
    // field-labor: lead with the place + object + action signals (the way the
    // input was actually decoded), with plain-language labels.
    // Rows are [pictogram, label, value].
    const fieldRows = isField ? [
        ['pin', jcChecklistCopy('interpret.place'), sigLine(ps.places)],
        ['package', jcChecklistCopy('interpret.object'), sigLine(ps.objects)],
        ['wrench', jcChecklistCopy('interpret.action'), sigLine(ps.actions)]
    ].filter(([, , v]) => v) : [];
    // Words the multilingual pivot translated ("nhà hàng → 식당"), so the person
    // can see exactly how their own-language sentence was read.
    const translated = Array.isArray(analysis.translatedTerms) ? analysis.translatedTerms.filter((h) => h && h.surface && h.ko) : [];
    const transRows = translated.length
        ? [['languages', jcChecklistCopy('interpret.translated'), translated.map((h) => `${h.surface} → ${h.ko}`).join(' · ')]]
        : [];
    const rows = [
        ['user', (zh ? '所做工作（职业）' : en ? 'Your work' : '하는 일(직종)'), e.jobRole],
        ['building', (zh ? '工作单位' : en ? 'Workplace' : '근무처'), e.workplaceType],
        ['factory', (zh ? '经营活动（行业）' : en ? 'Business activity' : '사업 활동(업종)'), e.businessActivity],
        ['file', (zh ? '雇佣形态' : en ? 'Employment type' : '고용형태'), e.employmentTypeLabel || e.employmentType],
        ['mic', (zh ? '活动类型' : en ? 'Activity type' : '활동 유형'), e.performanceType],
        ['scale', (zh ? '法律敏感度' : en ? 'Sensitive area' : '법적 민감도'), sens || null],
        ['id-card', (zh ? '居留资格' : en ? 'Status' : '체류자격'), e.visaStatus]
    ].filter(([, , v]) => v);
    // "더 확인할 점" — built from the top clarification's answer options so the
    // uncertainty is shown gently and concretely (not a scary warning).
    const topQ = Array.isArray(analysis.ambiguityQuestions) ? analysis.ambiguityQuestions[0] : null;
    const checkOpts = topQ && Array.isArray(topQ.chips)
        ? topQ.chips.filter(c => !/모르|not sure/i.test(c)).slice(0, 3).map(c => c.replace(/\([^)]*\)/g, '').trim()) : [];
    if (checkOpts.length) rows.push(['help', jcChecklistCopy('interpret.check'), checkOpts.join(en ? ' / ' : ' · ')]);
    const allRows = [...transRows, ...fieldRows, ...rows];
    if (!allRows.length && !analysis.parsedInterpretation) { el.hidden = true; el.innerHTML = ''; return; }
    el.hidden = false;
    const modeLabel = (currentLanguage === 'zh-CN' ? JC_MODE_LABEL_ZH[analysis.mode] : jcEnLike() ? JC_MODE_LABEL_EN[analysis.mode] : JC_MODE_LABEL[analysis.mode]) || '';
    const interp = analysis.parsedInterpretation
        ? `<div class="jc2-interpret-sum">${jcIcon('search')}<span>${escapeHtml(analysis.parsedInterpretation)}</span></div>` : '';
    const needConfirm = analysis.sourceStatus === 'needs_confirmation'
        ? `<div class="jc2-interpret-pending">${jcIcon('alert')}<span>${escapeHtml(jcChecklistCopy('needcode.body'))}</span></div>`
        : '';
    // "Written in Vietnamese" — only when the typed language differs from the UI.
    const typed = analysis.inputLanguage;
    const uiBase = String(currentLanguage || 'ko').split('-')[0];
    const langChip = typed && translated.length && !['ko', 'mixed', 'unknown', uiBase].includes(typed)
        ? ` <span class="jc2-interpret-lang">${jcIcon('globe')}${escapeHtml(jcChecklistCopy('interpret.inputLang').replace('{lang}', jcLanguageName(typed)))}</span>` : '';
    const grid = allRows.length
        ? `<div class="jc2-interpret-grid">`
            + allRows.map(([ic, k, v]) => `<span class="jc2-interpret-k">${jcIcon(ic)}<span>${escapeHtml(k)}</span></span><span class="jc2-interpret-v">${escapeHtml(String(v))}</span>`).join('')
            + `</div>`
        : '';
    // The one-line reading already tells the person what was understood; the
    // field-by-field breakdown folds away so the question and candidates sit
    // closer to the search box. Pending-source notice stays outside the fold.
    const fold = interp && grid
        ? `<details class="jc2-interpret-more"><summary>${escapeHtml(jcChecklistCopy('card.detail'))}</summary>${grid}</details>`
        : grid;
    el.innerHTML = `<div class="jc2-interpret-h">${jcIcon('message')}<span>${escapeHtml(jcChecklistCopy('interpret.title'))}</span>${modeLabel ? ` <span class="jc2-interpret-mode">${escapeHtml(modeLabel)}</span>` : ''}${langChip}</div>`
        + interp
        + fold
        + needConfirm;
}
function renderEmploymentFollowupChips(analysis) {
    const el = document.getElementById('jcFollowup');
    if (!el) return;
    const chips = analysis && Array.isArray(analysis.followUpChips) ? analysis.followUpChips : [];
    // Generic refine chips ("직원이에요", "연습생이에요") only help when the input
    // was not understood well, or touches entertainment/tattoo work where the
    // role genuinely needs pinning down. For a clear "미용실 헤어디자이너" they
    // just push the candidates further down the screen.
    const weakRead = analysis && (analysis.mode === 'ambiguous_mode'
        || ((analysis.extracted || {}).legalSensitivity || []).length > 0
        || (!(analysis.occupationCandidates || []).length && !(analysis.industryCandidates || []).length));
    if (!chips.length || !weakRead) { el.hidden = true; el.innerHTML = ''; return; }
    el.hidden = false;
    el.innerHTML = `<div class="jc2-refine-h">${jcIcon('plus')}<span>${currentLanguage === 'zh-CN' ? '后续选择 — 点击以进一步细化' : jcEnLike() ? 'Follow-up — tap to narrow further' : '후속 선택 — 눌러서 더 구체화'}</span></div>`
        + `<div class="jc2-refine-chips">`
        + chips.slice(0, 14).map((c) => `<button type="button" class="jc2-refine-chip" data-jc-refine="${escapeHtml(c)}">${escapeHtml(c)}</button>`).join('')
        + `</div>`;
    el.querySelectorAll('.jc2-refine-chip').forEach((btn) => {
        btn.onclick = () => {
            const inp = document.getElementById('jcSearchInput');
            if (!inp) return;
            clearTimeout(_jcSearchDebounce); clearTimeout(_jcAutoAnalyzeDebounce);
            const cleaned = (btn.dataset.jcRefine || '').replace(/\([^)]*\)/g, '').trim();
            inp.value = (inp.value.trim() + ' ' + cleaned).trim();
            searchJobcodeWithAI();
        };
    });
}
// User chose "잘 모르겠어요" — keep BOTH possibilities, reveal candidates, stop
// blocking the checklist, but never mark the fork resolved/complete. No re-search.
function jcDismissClarification() {
    _jcClarificationAnswered = true;
    _jcFlow.revealed = true;
    const el = document.getElementById('jcRefine');
    if (el) { el.hidden = true; el.innerHTML = ''; }
    renderEmploymentSpecialStates(_jcAnalysis);
    jcApplyFlow();
    renderEmploymentChecklist();
}
// --- Guided-flow controller: progressive disclosure (one action at a time) ---
function jcShow(id, show) { const el = document.getElementById(id); if (el) el.hidden = !show; }
function jcApplyFlow() {
    const C = window.EmploymentChecklist;
    const hasCandidates = (_jcResultCounts.occupation || 0) > 0 || (_jcResultCounts.industry || 0) > 0;
    const state = (C && C.employmentFlowState)
        ? C.employmentFlowState({ analyzerResult: _jcAnalysis, clarificationAnswered: _jcClarificationAnswered, candidatesRevealed: _jcFlow.revealed, hasCandidates })
        : (_jcAnalysis ? 'showing_candidates' : 'idle');
    _jcFlow.state = state;
    const gated = state === 'needs_clarification';
    const shown = state === 'showing_candidates';
    // Candidates are hidden ONLY while a fork question is pending (gated). In idle
    // they stay visible for the keyword-browse path; the income reminder + final
    // checklist appear once the guided flow reaches candidates.
    jcShow('jcResults', !gated);
    // 연간소득 안내는 신고 준비 단계(3단계)와 요약의 소득 선택칸이 이미 보여주므로 별도 카드는 숨긴다.
    jcShow('jcIncomeReminder', false);
    jcShow('jcFinalCheck', shown);
    jcShow('jcResultsGate', gated);
    if (gated) {
        const gate = document.getElementById('jcResultsGate');
        if (gate) {
            gate.innerHTML = `<div class="jc2-gate-h">${jcIcon('lock')}<span>${escapeHtml(jcChecklistCopy('flow.gateTitle'))}</span></div>`
                + `<p class="jc2-gate-b">${escapeHtml(jcChecklistCopy('flow.gateBody'))}</p>`
                + `<button type="button" class="jc2-gate-btn" id="jcRevealBtn">${escapeHtml(jcChecklistCopy('flow.reveal'))}</button>`;
            const rb = gate.querySelector('#jcRevealBtn');
            if (rb) rb.onclick = () => { _jcFlow.revealed = true; jcApplyFlow(); };
        }
    }
}
/* UX-08 `Emp / Special States` (node 442:39).
   Renders the states buildSpecialStates() derived, each with the one next
   action the design specifies. Ordered by the design; all applicable states
   show, because they are independent facts about the same input (a trainee in
   an entertainment role is genuinely both).

   The sensitive-occupation copy states that a permit or licence MAY apply and
   points at the competent office. It never says an activity is legal or
   illegal — 가치판단·합법성 단정 금지 (442:99). */
// Pictogram names in the modal's SVG sprite (#jc-i-*).
const JC_SPECIAL_ICON = {
    no_official_code: 'search', broad_indirect_match: 'compass', freelancer: 'file',
    self_employed: 'building', trainee: 'cap', arts_entertainment: 'mic',
    legally_sensitive: 'scale', mixed_language: 'languages', low_confidence: 'help',
    source_unverifiable: 'link'
};
const JC_SPECIAL_I18N = {
    no_official_code: 'NoOfficialCode', broad_indirect_match: 'BroadMatch',
    freelancer: 'Freelancer', self_employed: 'SelfEmployed', trainee: 'Trainee',
    arts_entertainment: 'Arts', legally_sensitive: 'Sensitive',
    mixed_language: 'MixedLang', low_confidence: 'LowConfidence',
    source_unverifiable: 'SourceUnverifiable'
};
const JC_SPECIAL_POINTS_AT_QUESTION = new Set(['pick_main_task', 'answer_followup']);
function renderEmploymentSpecialStates(analysis) {
    const el = document.getElementById('jcSpecialStates');
    if (!el) return;
    const refineEl = document.getElementById('jcRefine');
    const questionOnScreen = !!(refineEl && !refineEl.hidden);
    // While the clarification question is visible, a second card whose only
    // action is "답하러 가기" points at the same thing — skip it. Every other
    // state (sensitive work, trainee, freelancer …) still shows.
    const states = ((analysis && Array.isArray(analysis.specialStates)) ? analysis.specialStates : [])
        .filter((st) => !(questionOnScreen && JC_SPECIAL_POINTS_AT_QUESTION.has(st.action)));
    if (!states.length) { el.hidden = true; el.innerHTML = ''; return; }
    const items = states.map((st) => {
        const key = JC_SPECIAL_I18N[st.id];
        if (!key) return '';
        return `<li class="jc2-special-item" data-jc-special="${escapeHtml(st.id)}">`
            + `<span class="jc2-special-ic" aria-hidden="true">${jcIcon(JC_SPECIAL_ICON[st.id] || 'info')}</span>`
            + `<span class="jc2-special-tx">`
            + `<span class="jc2-special-title">${escapeHtml(tx('empSt' + key + 'Title'))}</span>`
            + `<span class="jc2-special-body">${escapeHtml(tx('empSt' + key + 'Body'))}</span>`
            + `</span>`
            + `<button type="button" class="jc2-special-cta" data-jc-special-action="${escapeHtml(st.action)}">`
            + `${escapeHtml(tx('empSt' + key + 'Cta'))}${jcIcon('arrow-right')}</button>`
            + `</li>`;
    }).filter(Boolean).join('');
    if (!items) { el.hidden = true; el.innerHTML = ''; return; }
    el.innerHTML = `<p class="jc2-special-h">${escapeHtml(tx('empSpecialStatesLabel'))}</p>`
        + `<ul class="jc2-special-list">${items}</ul>`;
    el.hidden = false;
    el.querySelectorAll('[data-jc-special-action]').forEach((btn) => {
        btn.onclick = () => runEmploymentSpecialAction(btn.getAttribute('data-jc-special-action'));
    });
}

/* Every state's next action does something concrete. None of them assert a
   determination — they move the user toward the input or the office that can
   settle the question. */
function runEmploymentSpecialAction(action) {
    const input = document.getElementById('jcSearchInput');
    const focusInput = (select) => {
        if (!input) return;
        jcSetStep('ask');
        input.focus();
        if (select && typeof input.select === 'function') input.select();
    };
    switch (action) {
        case 'show_nearest':
        case 'verify_by_code':
            // Candidates are the nearest thing we have; reveal and scroll to them.
            _jcFlow.revealed = true; jcApplyFlow();
            { const r = document.getElementById('jcResults'); if (r) r.scrollIntoView({ block: 'nearest' }); }
            return;
        case 'pick_main_task':
        case 'answer_followup':
            // Both are answered by the clarification question already on screen.
            { const r = document.getElementById('jcRefine');
              if (r && !r.hidden) { r.scrollIntoView({ block: 'nearest' }); return; } }
            focusInput(true);
            return;
        case 'check_contract':
        case 'check_business_registration':
            // These turn on facts only the user has; put them back in the box with
            // the follow-up chips visible so they can add the missing detail.
            { const c = document.getElementById('jcRefine');
              if (c && !c.hidden) c.scrollIntoView({ block: 'nearest' }); }
            focusInput(false);
            return;
        case 'show_e6':
            // E-6 is a real status in visa_data.json — route through normal search.
            closeModal('jobCodeModalOverlay');
            { const q = document.getElementById('q');
              if (q) { q.value = 'E-6'; const f = document.getElementById('searchForm');
                if (f) { try { f.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true })); } catch (e) {} } } }
            return;
        case 'confirm_with_office':
            { const fc = document.getElementById('jcFinalCheck');
              if (fc) { fc.hidden = false; fc.scrollIntoView({ block: 'nearest' }); } }
            return;
        case 'rewrite_in_korean':
            focusInput(true);
            return;
        default:
            focusInput(false);
    }
}

function renderEmploymentRefine(analysis) {
    const el = document.getElementById('jcRefine');
    if (!el) return;
    const qs = analysis && Array.isArray(analysis.ambiguityQuestions) ? analysis.ambiguityQuestions : [];
    if (!qs.length || _jcClarificationAnswered) { el.hidden = true; el.innerHTML = ''; return; }
    el.hidden = false;
    const en = jcEnLike();
    const zh = currentLanguage === 'zh-CN';
    // ONE question at a time: the single most relevant fork. Answering it re-runs
    // the analyzer, which surfaces the next question only if still needed.
    const q = qs[0];
    const lead = jcChecklistCopy('clarify.lead');
    const remaining = qs.length > 1
        ? `<span class="jc2-refine-more">${escapeHtml(zh ? `回答后还可再确认 ${qs.length - 1} 项` : en ? `+${qs.length - 1} more after this` : `답하면 ${qs.length - 1}개 더 확인할 수 있어요`)}</span>` : '';
    // Large, tap-friendly answer buttons; the analyzer chips are the real options.
    const answers = (q.chips || []).map((c) =>
        `<button type="button" class="jc2-answer" data-jc-refine="${escapeHtml(c)}">${escapeHtml(c.replace(/\([^)]*\)/g, '').trim())}</button>`).join('');
    const dunno = `<button type="button" class="jc2-answer jc2-answer--dunno" data-jc-dunno="1">${escapeHtml(jcChecklistCopy('clarify.dunno'))}</button>`;
    el.innerHTML = `<div class="jc2-refine-h">${jcIcon('target')}<span>${escapeHtml(lead)}</span>${remaining}</div>`
        + `<div class="jc2-refine-q"><p class="jc2-refine-qt">${escapeHtml(q.question)}</p>`
        + `<div class="jc2-answers">${answers}${dunno}</div></div>`;
    // An answer appends the clarifier to the query and re-runs the analyzer.
    el.querySelectorAll('.jc2-answer[data-jc-refine]').forEach((btn) => {
        btn.onclick = () => {
            const inp = document.getElementById('jcSearchInput');
            if (!inp) return;
            clearTimeout(_jcSearchDebounce); clearTimeout(_jcAutoAnalyzeDebounce);
            const cleaned = (btn.dataset.jcRefine || '').replace(/\([^)]*\)/g, '').trim();
            inp.value = (inp.value.trim() + ' ' + cleaned).trim();
            searchJobcodeWithAI();
        };
    });
    const dunnoBtn = el.querySelector('[data-jc-dunno]');
    if (dunnoBtn) dunnoBtn.onclick = () => jcDismissClarification();
}
function renderEmploymentTips(analysis) {
    const el = document.getElementById('jcTips');
    if (!el) return;
    const warns = analysis && Array.isArray(analysis.warnings) ? analysis.warnings : [];
    if (!warns.length) { el.hidden = true; el.innerHTML = ''; return; }
    const sens = (analysis.extracted && analysis.extracted.legalSensitivity) || [];
    // Legal cautions (문신사법 / 연예·공연 / 별도 검토) are pulled to the top as a
    // prominent banner so warnings are never buried in tiny text.
    const isLegal = (w) => /문신|타투|연예|공연|별도 검토|별도 확인|허용되는 것은 아닙/.test(w);
    const legal = warns.filter(isLegal);
    const rest = warns.filter((w) => !isLegal(w));
    const en = jcEnLike();
    const zh = currentLanguage === 'zh-CN';
    let html = '';
    if (sens.length && legal.length) {
        html += `<div class="jc2-legal-banner"><div class="jc2-legal-h">${jcIcon('alert')}<span>${zh ? '注意 — 有代码并不代表该工作·施术被许可' : en ? 'Caution — having a code does not mean the job/procedure is permitted' : '주의사항 — 코드가 있다고 취업·시술이 허용되는 것은 아닙니다'}</span></div>`
            + `<ul class="jc2-tips-list">` + legal.map((w) => `<li>${escapeHtml(w)}</li>`).join('') + `</ul></div>`;
    }
    const tipItems = (sens.length && legal.length ? rest : warns);
    if (tipItems.length) {
        html += `<details class="jc2-tips-fold"><summary class="jc2-tips-h">${jcIcon('pin')}<span>${zh ? 'HiKorea 录入提示 · 官方标准' : en ? 'HiKorea input tips · official standards' : '하이코리아 입력 팁 · 공식 기준'}</span></summary>`
            + `<ul class="jc2-tips-list">` + tipItems.map((w) => `<li>${escapeHtml(w)}</li>`).join('') + `</ul></details>`;
    }
    el.hidden = false;
    el.innerHTML = html;
}
// --- Guided checklist (직종 → 업종 → 연간소득 → 하이코리아 최종 확인) -------------
// The checklist module carries copy for all 14 UI languages (falls back to ko).
function jcLang() { return currentLanguage || 'ko'; }
function jcChecklistCopy(key) {
    const C = window.EmploymentChecklist;
    return C && C.checklistCopy ? C.checklistCopy(key, jcLang()) : '';
}
// Build the checklist state from the last analysis + current selections/income.
function jcBuildChecklistState() {
    const C = window.EmploymentChecklist;
    if (!C || !C.buildEmploymentChecklistState) return null;
    const incomeVal = (document.getElementById('jcIncome') || {}).value || '';
    return C.buildEmploymentChecklistState({
        analyzerResult: _jcAnalysis,
        selectedOccupation: _jcSelected.occupation,
        selectedIndustry: _jcSelected.industry,
        clarificationState: { answered: _jcClarificationAnswered },
        incomeState: { selected: !!incomeVal, value: incomeVal },
        occupationResultCount: _jcResultCounts.occupation,
        industryResultCount: _jcResultCounts.industry,
        sourceStatus: _jcAnalysis ? _jcAnalysis.sourceStatus : undefined,
        lang: jcLang()
    });
}
const JC_STATUS_CLASS = { pending: 'is-pending', ready: 'is-ready', needs_confirmation: 'is-warn', complete: 'is-done', blocked: 'is-blocked' };
// Status pictograms; the text status label beside them stays the primary signal.
const JC_STATUS_ICON = { pending: 'circle', ready: 'circle-dot', needs_confirmation: 'alert', complete: 'check-circle', blocked: 'pencil' };
function renderEmploymentChecklist() {
    const el = document.getElementById('jcChecklist');
    if (!el) return;
    const st = jcBuildChecklistState();
    if (!st) { el.hidden = true; el.innerHTML = ''; return; }
    el.hidden = false;
    el.innerHTML = st.steps.map((s) => {
        const cls = JC_STATUS_CLASS[s.status] || 'is-pending';
        return `<li class="jc2-cl-item ${cls}">`
            + `<span class="jc2-cl-ic" aria-hidden="true">${jcIcon(JC_STATUS_ICON[s.status] || 'circle')}</span>`
            + `<span class="jc2-cl-tx">`
            + `<span class="jc2-cl-top"><b class="jc2-cl-label">${escapeHtml(s.label)}</b>`
            + `<span class="jc2-cl-status" data-status="${s.status}">${escapeHtml(s.statusLabel)}</span></span>`
            + `<span class="jc2-cl-plain">${escapeHtml(s.plainLanguageLabel)}</span>`
            + `<span class="jc2-cl-reason">${escapeHtml(s.reason)}</span>`
            + `</span></li>`;
    }).join('');
}
// Guided examples for weak/dead-end inputs — never a bare "검색 결과 없음".
// [search value, i18n key for the visible label] — the label follows the UI
// language while the value stays the Korean sentence the analyzer knows best.
const JC_WEAK_EXAMPLES = [['카페에서 음료 만들어요', 'jobCodeChip6'], ['공장에서 박스 포장해요', 'jobCodeChip3'], ['골프장 청소해요', 'jobCodeChip1'], ['학원에서 영어 가르쳐요', 'jobCodeChip4']];
function renderEmploymentWeakHelp(analysis, occCount, indCount) {
    const el = document.getElementById('jcWeakHelp');
    if (!el) return;
    // "weak" = no candidates AND no CONCRETE splitter (place/object/action/role/
    // workplace) to separate 직종 vs 업종. Employment-type modifiers ("알바") or
    // umbrella terms alone are NOT concrete. Legally-sensitive (연예/문신) inputs
    // get their own tailored guidance, so they are excluded here.
    const ps = (analysis && analysis.parsedSignals) || {};
    const ex = (analysis && analysis.extracted) || {};
    const concrete = (ps.places || []).length + (ps.objects || []).length + (ps.actions || []).length
        + (ex.jobRole ? 1 : 0) + (ex.workplaceType ? 1 : 0) + (ex.businessActivity ? 1 : 0);
    const sensitive = ((ex.legalSensitivity || []).length) > 0;
    const weak = analysis && occCount === 0 && indCount === 0 && concrete === 0 && !sensitive;
    if (!weak) { el.hidden = true; el.innerHTML = ''; return; }
    el.hidden = false;
    const detail = [jcChecklistCopy('weak.detail.task'), jcChecklistCopy('weak.detail.place'), jcChecklistCopy('weak.detail.business')];
    el.innerHTML = `<div class="jc2-weak-h">${jcIcon('bulb')}<span>${escapeHtml(jcChecklistCopy('weak.title'))}</span></div>`
        + `<p class="jc2-weak-sub">${escapeHtml(jcChecklistCopy('weak.hint'))} · ${detail.map(escapeHtml).join(' · ')}</p>`
        + `<div class="jc2-weak-chips">` + JC_WEAK_EXAMPLES.map(([value, key]) => {
            const label = tx(key);
            return `<button type="button" class="jc2-weak-chip" data-jc-example="${escapeHtml(value)}">${escapeHtml(label && label !== key ? label : value)}</button>`;
        }).join('') + `</div>`;
    el.querySelectorAll('.jc2-weak-chip').forEach((b) => {
        b.onclick = () => { const inp = document.getElementById('jcSearchInput'); if (!inp) return; clearTimeout(_jcSearchDebounce); clearTimeout(_jcAutoAnalyzeDebounce); inp.value = b.dataset.jcExample || ''; searchJobcodeWithAI(); };
    });
}
function clearEmploymentAnalysisUI() {
    ['jcInterpret', 'jcRefine', 'jcFollowup', 'jcTips', 'jcWeakHelp'].forEach((id) => {
        const el = document.getElementById(id);
        if (el) { el.hidden = true; el.innerHTML = ''; }
    });
}
// 분석기 후보(순서 보존)를 데이터셋 행으로 되돌리고, 인라인 스코어러 결과를 뒤에 붙인다.
// 보충 행의 점수는 분석기 마지막 후보 점수를 넘지 않게 눌러서(스케일이 서로 달라)
// 신뢰도 라벨이 분석기 1위 기준으로 유지되게 한다.
function jcRowsFromAnalysis(candidates, fallbackRows, limit = 60) {
    if (!Array.isArray(candidates) || !candidates.length || !_jobcodeData) return fallbackRows;
    const rows = []; const seen = new Set();
    candidates.forEach(c => {
        const row = _jobcodeData.data.find(r => jcType(r) === c.classification && jcCode(r) === String(c.code));
        if (!row) return;
        seen.add(String(c.code));
        rows.push(Object.assign({}, row, { _score: c.score, _confidence: c.confidence }));
    });
    if (!rows.length) return fallbackRows;
    const floor = rows[rows.length - 1]._score || 0;
    fallbackRows.forEach(r => {
        if (seen.has(jcCode(r))) return;
        rows.push(Object.assign({}, r, { _score: Math.min(r._score || 0, floor) }));
    });
    return rows.slice(0, limit);
}
async function searchJobcodeWithAI() {
    const inputEl = document.getElementById('jcSearchInput');
    const input = inputEl ? inputEl.value.trim() : '';
    if (!input) { showToast(currentLanguage === 'zh-CN' ? '请在搜索框中填写您的工作或营业场所（例：中餐厅厨师长）。' : jcEnLike() ? 'Please describe your job or workplace in the search box (e.g. Chinese-restaurant head chef).' : "검색창에 본인의 일이나 사업장을 적어주세요 (예: 중식당 주방장)."); return; }
    jcSetStep('result');
    const requestId = ++_jcAnalysisRequest;
    const isCurrentRequest = () => requestId === _jcAnalysisRequest && inputEl.value.trim() === input;
    const jobBox = document.getElementById('jcJobResults'), indBox = document.getElementById('jcIndResults'), spinner = document.getElementById('jcAiSpinner');
    const btn = spinner ? spinner.parentElement : null;
    if (btn) btn.disabled = true; if (spinner) spinner.style.display = 'inline-block';
    // 분석이 실제로 실행되면 'AI 검색을 눌러보세요' 힌트는 더 이상 유효하지 않다.
    const aiHint = document.getElementById('jcAiHint'); if (aiHint) { aiHint.hidden = true; }
    if (jobBox) jobBox.innerHTML = `<div class="jc2-loading">${escapeHtml(tx('jobCodeLoadingNatural'))}</div>`;
    if (indBox) indBox.innerHTML = `<div class="jc2-loading">${escapeHtml(tx('jobCodeLoadingNatural'))}</div>`;
    try {
        if (!_jobcodeData) { try { await loadJobcodeData(); } catch (_) {
            const msg = currentLanguage === 'zh-CN' ? '当前无法使用分析功能。请填写得更具体一些，或稍后再试。' : jcEnLike() ? 'The lookup tool is unavailable right now. Try a more specific description or try again later.' : '지금은 분석 기능을 사용할 수 없어요. 더 구체적으로 적거나 잠시 후 다시 시도해 주세요.';
            const html = `<div class="jc2-empty">${escapeHtml(msg)}</div>`;
            if (jobBox) jobBox.innerHTML = html; if (indBox) indBox.innerHTML = html; return;
        } }
        // Deterministic analyzer: entity extraction → interpretation, ambiguity
        // chips, tips, AND entity-aware terms fed into the existing scorer.
        let analysis = null;
        try {
            const az = await ensureEmploymentAnalyzer();
            const { interpretEmploymentInput } = await import(/* @vite-ignore */ new URL('scripts/employment_interpret_client.mjs', document.baseURI).href);
            const facts = await interpretEmploymentInput({ text: input, lang: jcEnLike() ? 'en' : 'ko', apiBase: API_BASE });
            if (!isCurrentRequest()) return;
            // Analyzer questions exist in Korean and English; any UI language
            // other than Korean/Chinese gets the English wording.
            if (az) analysis = az.analyze({ text: input, locale: jcEnLike() ? 'en' : currentLanguage, facts });
        } catch (_) { analysis = null; }
        if (!isCurrentRequest()) return;
        // Fresh search → store analysis, clear stale selections/clarification so the
        // checklist never inherits a previous query's progress.
        _jcAnalysis = analysis;
        _jcSelected = { occupation: null, industry: null };
        _jcClarificationAnswered = false;
        _jcFlow = { state: 'analyzing', revealed: false };
        renderJobcodeSelectedSummary();
        renderEmploymentInterpretation(analysis);
        renderEmploymentRefine(analysis);
        renderEmploymentSpecialStates(analysis);
        renderEmploymentFollowupChips(analysis);
        renderEmploymentTips(analysis);
        const searchText = analysis ? analysis.searchText : input;
        // If the sentence names employees as task targets, their profession is
        // explicitly NOT an occupation/industry search keyword for this user.
        const scopedRelation = !!(analysis && analysis.managedStaff);
        let jobKw = scopedRelation ? (analysis.occupationTerms || []) : getJobcodeSearchTerms(searchText, analysis ? analysis.occupationTerms : []);
        let indKw = scopedRelation ? (analysis.industryTerms || []) : getJobcodeSearchTerms(searchText, analysis ? analysis.industryTerms : []);
        let fallbackNote = null;
        // 분석기(회귀테스트로 순위까지 검증됨)가 낸 후보를 최상단에 그대로 두고,
        // 인라인 키워드 스코어러 결과는 그 아래를 채우는 보충으로만 쓴다 —
        // 두 스코어러의 가중치 차이로 1위가 뒤바뀌는 문제(예: 서빙인데 조리사가 1위)를 막는다.
        // Do not reintroduce the teacher/childcare false positives through the
        // legacy keyword fallback after the analyzer has recognized that the
        // person's actual job is administering teacher staffing.
        const occupationFallback = scopedRelation
            ? [] : getScoredJobcodeRows('occupation', '', jobKw, 60);
        const jobRows = jcRowsFromAnalysis(analysis && analysis.occupationCandidates, occupationFallback);
        const indRows = jcRowsFromAnalysis(analysis && analysis.industryCandidates,
            scopedRelation ? [] : getScoredJobcodeRows('industry', '', indKw, 60));
        // Guided AI layout: top recommendation vs alternatives. When the analyzer
        // is still clarifying, show "몇 가지 가능성이 있어요" (no false "closest").
        const ambiguous = !!(analysis && analysis.clarificationRequired && !_jcClarificationAnswered);
        renderJobcodeList(jobRows, jobBox, 'occupation', input, jobKw, { collapse: true, ambiguous });
        renderJobcodeList(indRows, indBox, 'industry', input, indKw, { collapse: true, ambiguous });
        renderJobcodeGuidance(input, jobRows, indRows);
        if (analysis) { const amb = document.getElementById('jcAmbiguity'); if (amb) amb.hidden = true; }
        // Never a bare "검색 결과 없음" when the input WAS understood (place/object/
        // action or concept signals present): explain that the official mapping
        // needs confirmation instead, so field-worker inputs don't dead-end.
        const ps = analysis && analysis.parsedSignals;
        const hasSignals = !!(ps && ((ps.places||[]).length || (ps.objects||[]).length || (ps.actions||[]).length))
            || !!(analysis && (analysis.parsedInterpretation || (analysis.matchedConcepts||[]).length));
        if (hasSignals) {
            // Reassuring "공식 코드 확인 필요" card (not a scary dead-end), with two
            // gentle next actions: re-word the search, or check the official portal.
            const pendHtml = `<div class="jc2-needcode">`
                + `<div class="jc2-needcode-h">${jcIcon('search')}<span>${escapeHtml(jcChecklistCopy('needcode.title'))}</span></div>`
                + `<p class="jc2-needcode-b">${escapeHtml(jcChecklistCopy('needcode.body'))}</p>`
                + `<div class="jc2-needcode-acts">`
                + `<button type="button" class="jc2-needcode-btn" data-jc-research="1">${escapeHtml(jcChecklistCopy('needcode.research'))}</button>`
                + `<a class="jc2-needcode-btn jc2-needcode-link" href="https://kssc.mods.go.kr" target="_blank" rel="noopener">${escapeHtml(jcChecklistCopy('needcode.portal'))}${jcIcon('external')}</a>`
                + `</div></div>`;
            if (jobBox && !jobRows.length) jobBox.innerHTML = pendHtml;
            if (indBox && !indRows.length) indBox.innerHTML = pendHtml;
            document.querySelectorAll('.jc2-needcode-btn[data-jc-research]').forEach((b) => {
                b.onclick = () => { jcSetStep('ask'); const inp = document.getElementById('jcSearchInput'); if (inp) { inp.value = ''; inp.focus(); } };
            });
        }
        // Update the guided checklist + weak-input help from what's actually shown.
        _jcResultCounts = { occupation: jobRows.length, industry: indRows.length };
        renderEmploymentChecklist();
        renderEmploymentWeakHelp(analysis, jobRows.length, indRows.length);
        // Progressive flow: gate candidates behind a pending fork question.
        jcApplyFlow();
        jcRevealAnswer();
        const badge = document.getElementById('jcCountBadge');
        if (badge) badge.hidden = true;
        if (badge) badge.textContent = currentLanguage === 'zh-CN' ? `职业 ${jobRows.length} · 行业 ${indRows.length}` : jcEnLike() ? `Occupation ${jobRows.length} · Industry ${indRows.length}` : `직종 ${jobRows.length} · 업종 ${indRows.length}`;
        if (fallbackNote) {
            const noteHtml = `<div class="jc2-empty" style="color:var(--color-warning);padding:0.6rem;">${escapeHtml(fallbackNote)}</div>`;
            if (jobBox) jobBox.insertAdjacentHTML('afterbegin', noteHtml);
        }
    } catch (e) {
        const errorHtml = `<div class="jc2-empty" style="color:var(--color-error);">${currentLanguage === 'zh-CN' ? '自然语言搜索出错' : jcEnLike() ? 'Natural-language search error' : '자연어 검색 오류'}: ${escapeHtml(e.message)}</div>`;
        if (jobBox) jobBox.innerHTML = errorHtml; if (indBox) indBox.innerHTML = errorHtml;
    } finally { if (requestId === _jcAnalysisRequest) { if (btn) btn.disabled = false; if (spinner) spinner.style.display = 'none'; } }
}
// DOMContentLoaded wiring for the search field and the income bracket select (moved from the inline
// DOMContentLoaded handler; called from there at the same point).
function wireJobcodeInputs() {
    const jcSearchInput = document.getElementById('jcSearchInput');
    if (jcSearchInput) {
        jcSearchInput.addEventListener('input', (e) => {
            clearTimeout(_jcSearchDebounce); clearTimeout(_jcAutoAnalyzeDebounce);
            const v = e.target.value;
            _jcSearchDebounce = setTimeout(() => renderJobcodeResults(v), 200);
            // 타이핑이 멈췄다고 자동 분석하지 않는다 — 결과 화면으로 넘어가 버리면
            // 천천히 입력하는 사람은 쓰던 문장을 잃는다. Enter 또는 버튼으로만 찾는다.
        });
        jcSearchInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') { clearTimeout(_jcSearchDebounce); clearTimeout(_jcAutoAnalyzeDebounce); searchJobcodeWithAI(); }
        });
    }
    // Income bracket choice → checklist step 3 reflects a (draft) user selection.
    const jcIncomeSel = document.getElementById('jcIncome');
    if (jcIncomeSel) jcIncomeSel.addEventListener('change', () => { _jcIncome = jcIncomeSel.value || ''; renderEmploymentChecklist(); });
}

export {
    JOBCODE_TARGET_VISAS, jcIcon, updateJobcodeNaturalSearchLabel, openJobCodeModal, renderJobcodeResults,
    searchJobcodeWithAI, selectJobcode, copyJobcodeMemo, setJobcodeFilter, setJobcodeLevel, searchJobcodeChip,
    jcGoBackToAsk, renderEmploymentChecklist, wireJobcodeInputs
};
