#!/usr/bin/env node
/*
 * build_employment_test_cases.mjs
 * ----------------------------------------------------------------------------
 * Deterministically generates the employment-analyzer mode test suites from
 * compact template tables so the 450+ fixtures stay maintainable and cannot
 * drift into hand-edited hallucinated codes. Every case asserts BEHAVIOUR
 * (mode / parsed signals / candidate clusters), never a hard-coded official code.
 *
 *   node scripts/build_employment_test_cases.mjs
 *
 * Emits, under data/employment/:
 *   field_labor_test_cases.json        (>=150)
 *   professional_test_cases.json       (>=100)
 *   service_test_cases.json            (>=80)
 *   arts_entertainment_test_cases.json (>=60)
 *   ambiguous_test_cases.json          (>=60)
 *
 * The runner is scripts/check_employment_analyzer_modes.mjs.
 * ----------------------------------------------------------------------------
 */
import { writeFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');
const out = (name, obj) => {
  writeFileSync(join(root, 'data/employment', name), JSON.stringify(obj, null, 2) + '\n', 'utf8');
  console.log(`  wrote data/employment/${name} (${obj.cases.length} cases)`);
};

const slug = (s) => s.toLowerCase().replace(/[^a-z0-9가-힣]+/g, '_').replace(/^_+|_+$/g, '').slice(0, 40);
let counter = 0;
const mk = (o) => ({ id: `${o.prefix}_${String(++counter).padStart(4, '0')}_${slug(o.input)}`, ...o.body });

/* ===========================================================================
 * FIELD LABOR — place × object × action combinations per sector (the critical mode)
 * ========================================================================= */
const FIELD = [
  { sector: 'fishery_vessel', places: ['배', '어선', '고깃배', '오징어배'], objects: ['한치', '오징어', '갈치', '고등어', '생선'], actions: ['잡아요', '잡습니다', '어획해요', '조업해요'], occ: '어', ind: '어업', topic: 'vessel_crew_vs_land_processing' },
  { sector: 'agriculture', places: ['과수원', '감귤 농장', '사과밭'], objects: ['귤', '감귤', '사과', '배', '포도'], actions: ['따요', '땁니다', '수확해요'], occ: '재배', ind: '재배', topic: 'farm_harvest_vs_food_factory' },
  { sector: 'agriculture', places: ['밭', '농장', '하우스'], objects: ['마늘', '양파', '배추', '고추', '감자'], actions: ['뽑아요', '캐요', '수확해요', '심어요'], occ: '재배', ind: '재배', topic: 'farm_harvest_vs_food_factory' },
  { sector: 'agriculture', places: ['하우스', '비닐하우스', '딸기 농장'], objects: ['딸기', '토마토', '오이', '파프리카'], actions: ['따요', '수확해요', '포장해요'], occ: '재배', ind: '재배', topic: 'farm_harvest_vs_food_factory' },
  { sector: 'aquaculture', places: ['양식장', '가두리'], objects: ['전복', '물고기', '새우', '굴'], actions: ['밥 줘요', '먹이 줘요', '키워요', '양식해요'], occ: '양식', ind: '양식', topic: 'aquaculture_vs_processing' },
  { sector: 'seafood_processing', places: ['수산물 공장', '가공공장', '선별장'], objects: ['생선', '오징어', '수산물'], actions: ['손질해요', '가공해요', '다듬어요'], occ: '가공', ind: '수산물 가공', topic: 'vessel_crew_vs_land_processing' },
  { sector: 'manufacturing', places: ['공장', '제조공장', '생산라인'], objects: ['박스', '부품', '제품', '자재'], actions: ['포장해요', '조립해요', '검사해요'], occ: '단순', ind: '제조', topic: 'manufacturing_vs_logistics' },
  { sector: 'logistics', places: ['창고', '물류센터', '택배 터미널'], objects: ['박스', '택배', '상자', '화물'], actions: ['나릅니다', '상하차해요', '분류해요', '적재해요'], occ: '하역', ind: '창고', topic: 'manufacturing_vs_logistics' },
  { sector: 'grounds', places: ['골프장', '컨트리클럽'], objects: ['잔디', '그린', '쓰레기'], actions: ['청소해요', '관리해요', '깎아요'], occ: '청소', ind: '골프장', topic: 'direct_employer_vs_contractor' },
  { sector: 'hospitality', places: ['리조트', '호텔', '펜션'], objects: ['객실', '침대', '침구'], actions: ['청소해요', '정리해요'], occ: '청소', ind: '숙박', topic: 'hospitality_role_unknown' },
  { sector: 'construction', places: ['건설현장', '공사장', '현장'], objects: ['자재', '벽돌', '철근'], actions: ['나릅니다', '용접해요', '칠해요', '설치해요'], occ: '건설', ind: '건설', topic: 'construction_labor_vs_technical_install' },
  { sector: 'kitchen_labor', places: ['식당', '주방', '급식실'], objects: ['접시', '그릇'], actions: ['설거지해요', '주방보조해요'], occ: '조리', ind: '음식점', topic: 'restaurant_employee_vs_outsourced' },
  { sector: 'cleaning', places: ['건물', '사무실', '빌딩'], objects: ['쓰레기', '바닥', '유리창'], actions: ['청소해요', '치워요', '닦아요'], occ: '청소', ind: '청소', topic: null },
  { sector: 'livestock', places: ['축산농가', '목장', '양계장'], objects: ['소', '돼지', '닭', '가축'], actions: ['키워요', '먹이 줘요', '사육해요'], occ: '사육', ind: '축산', topic: null }
];

function buildFieldCases() {
  const cases = [];
  for (const t of FIELD) {
    // place+object+action, plus object+action, plus place+action — realistic phrasings.
    const combos = [];
    for (const p of t.places) for (const o of t.objects) for (const a of t.actions) combos.push(`${p}에서 ${o} ${a}`);
    for (const o of t.objects) for (const a of t.actions) combos.push(`${o} ${a}`);
    for (const p of t.places) for (const a of t.actions) combos.push(`${p}에서 ${a}`);
    // sample ~12 per sector deterministically (stride) for variety without bloat.
    const stride = Math.max(1, Math.floor(combos.length / 12));
    const picked = combos.filter((_, i) => i % stride === 0).slice(0, 12);
    for (const input of picked) {
      cases.push(mk({
        prefix: 'field', input,
        body: {
          input, language: 'ko', expectMode: 'field_labor_mode',
          expectSignals: ['places', 'objects', 'actions'],
          expectOccupationCluster: t.occ, expectIndustryCluster: t.ind,
          clarificationTopic: t.topic || undefined,
          withholdCodeIfUnverified: false, noHallucinatedCode: true
        }
      }));
    }
  }
  // explicit required examples from the task spec (guaranteed present)
  const required = [
    ['한치잡이 배에서 한치잡아요', '어', '어업', 'vessel_crew_vs_land_processing'],
    ['배 타고 고기 잡아요', '어', '어업', 'vessel_crew_vs_land_processing'],
    ['수산물 공장에서 생선 손질해요', '가공', '수산물 가공', null],
    ['양식장에서 물고기 밥 줘요', '양식', '양식', 'aquaculture_vs_processing'],
    ['귤 따요', '재배', '재배', 'farm_harvest_vs_food_factory'],
    ['감귤 농장에서 일해요', null, '재배', null],
    ['마늘 뽑아요', '재배', '재배', null],
    ['농장에서 채소 포장해요', '재배', '재배', null],
    ['공장에서 박스 포장해요', null, '제조', 'manufacturing_vs_logistics'],
    ['공장에서 부품 조립해요', '조립', '제조', null],
    ['창고에서 택배 상자 나릅니다', '하역', '창고', 'manufacturing_vs_logistics'],
    ['골프장 청소해요', '청소', null, 'direct_employer_vs_contractor'],
    ['골프장 잔디 관리해요', '조경', '골프장', 'direct_employer_vs_contractor'],
    ['리조트 객실 청소해요', '청소', null, 'hospitality_role_unknown'],
    ['호텔에서 침대 정리해요', '청소', null, null],
    ['식당에서 설거지해요', '조리', null, 'restaurant_employee_vs_outsourced'],
    ['주방 보조해요', '조리', null, null],
    ['건설현장에서 자재 나릅니다', null, '건설', null],
    ['용접 보조합니다', '용접', null, null]
  ];
  for (const [input, occ, ind, topic] of required) {
    cases.push(mk({ prefix: 'field_req', input, body: {
      input, language: 'ko', expectMode: 'field_labor_mode', expectSignals: ['places', 'objects', 'actions'],
      expectOccupationCluster: occ || undefined, expectIndustryCluster: ind || undefined,
      clarificationTopic: topic || undefined, withholdCodeIfUnverified: false, noHallucinatedCode: true
    } }));
  }
  // a few English field-labor cases
  const en = [
    ['I catch squid on a fishing boat', '어', '어업', 'en'],
    ['I pick tangerines at an orchard', '재배', '재배', 'en'],
    ['I pack boxes at a factory', null, '제조', 'en'],
    ['I clean the golf course', '청소', null, 'en'],
    ['I feed fish at an aquaculture farm', '양식', '양식', 'en'],
    ['I carry boxes at a warehouse', '하역', '창고', 'en']
  ];
  for (const [input, occ, ind] of en) {
    cases.push(mk({ prefix: 'field_en', input, body: {
      input, language: 'en', expectMode: 'field_labor_mode', expectSignals: ['actions'],
      expectOccupationCluster: occ || undefined, expectIndustryCluster: ind || undefined,
      withholdCodeIfUnverified: false, noHallucinatedCode: true
    } }));
  }
  return cases;
}

/* ===========================================================================
 * PROFESSIONAL / OFFICE
 * ========================================================================= */
const PRO = [
  ['소프트웨어 개발자', 'ko', '소프트웨어'], ['software developer', 'en', '소프트웨어'],
  ['AI 엔지니어', 'ko', '소프트웨어'], ['AI engineer', 'en', '소프트웨어'],
  ['데이터 분석가', 'ko', '분석'], ['data analyst', 'en', '분석'],
  ['웹 디자이너', 'ko', '디자이너'], ['web designer', 'en', '디자이너'],
  ['UX 디자이너', 'ko', '디자이너'], ['UX designer', 'en', '디자이너'],
  ['연구원', 'ko', '연구'], ['researcher', 'en', '연구'],
  ['실험실 보조', 'ko', '시험원'], ['lab assistant', 'en', '시험원'],
  ['대학교수', 'ko', '교수'], ['professor', 'en', '교수'],
  ['영어 강사', 'ko', '강사'], ['English teacher', 'en', '강사'],
  ['학원 강사', 'ko', '강사'], ['hagwon instructor', 'en', '강사'],
  ['번역가', 'ko', '번역'], ['translator', 'en', '번역'],
  ['통역사', 'ko', '통역'], ['interpreter', 'en', '통역'],
  ['회계사', 'ko', '회계'], ['accountant', 'en', '회계'],
  ['컨설턴트', 'ko', '진단'], ['consultant', 'en', '진단'],
  ['마케터', 'ko', '마케팅'], ['marketer', 'en', '마케팅'],
  ['사무직', 'ko', '사무'], ['office administrator', 'en', '사무'],
  ['무역회사 직원', 'ko', null], ['trade company employee', 'en', null],
  ['해외 영업', 'ko', '영업'], ['overseas sales', 'en', '영업'],
  ['수출입 관리', 'ko', null], ['import export manager', 'en', '영업'],
  ['엔지니어', 'ko', '기술자'], ['engineer', 'en', '기술자'],
  ['정비공', 'ko', '정비'], ['mechanic', 'en', '정비'],
  ['건축가', 'ko', '건축'], ['architect', 'en', '건축'],
  ['변호사', 'ko', '변호사'], ['lawyer', 'en', '변호사'],
  ['의사', 'ko', '의사'], ['doctor', 'en', '의사'],
  ['간호사', 'ko', '간호'], ['nurse', 'en', '간호'],
  ['수의사', 'ko', '수의사'], ['veterinarian', 'en', '수의사'],
  ['약사', 'ko', '약사'], ['pharmacist', 'en', '약사']
];
const PRO_WORKPLACES = [
  ['IT 스타트업에서 개발해요', 'ko', '소프트웨어', '소프트웨어'],
  ['software engineer at a startup', 'en', '소프트웨어', null],
  ['대학교에서 연구해요', 'ko', '연구', '대학'],
  ['영어학원에서 강의해요', 'ko', '강사', '교육'],
  ['I teach English at a hagwon', 'en', '강사', '교습'],
  ['무역회사에서 해외영업 합니다', 'ko', '영업', null],
  ['회계법인에서 회계 업무', 'ko', '회계', null],
  ['병원에서 간호사로 일해요', 'ko', '간호', '병원'],
  ['startup founder', 'en', null, null],
  ['스타트업 대표예요', 'ko', null, null]
];
// Extra professional roles to comfortably exceed 100 cases.
const PRO_EXTRA = [
  ['백엔드 개발자', 'ko', '소프트웨어'], ['backend developer', 'en', '소프트웨어'],
  ['프론트엔드 개발자', 'ko', '소프트웨어'], ['frontend developer', 'en', '소프트웨어'],
  ['앱 개발자', 'ko', '소프트웨어'], ['mobile app developer', 'en', '소프트웨어'],
  ['그래픽 디자이너', 'ko', '디자이너'], ['graphic designer', 'en', '디자이너'],
  ['제품 디자이너', 'ko', '디자이너'], ['product designer', 'en', '디자이너'],
  ['세무사', 'ko', '세무'], ['tax accountant', 'en', '세무'],
  ['연구개발', 'ko', '연구'], ['R&D researcher', 'en', '연구'],
  ['한의사', 'ko', '한의사'], ['oriental medicine doctor', 'en', '한의사'],
  ['치과의사', 'ko', '치과'], ['dentist', 'en', '치과'],
  ['기계 엔지니어', 'ko', '기계'], ['mechanical engineer', 'en', '기계'],
  ['전기 엔지니어', 'ko', '기술자'], ['electrical engineer', 'en', '기술자'],
  ['자동차 정비사', 'ko', '정비'], ['auto mechanic', 'en', '정비'],
  ['사진작가', 'ko', '사진'], ['photographer', 'en', '사진'],
  ['카피라이터', 'ko', null], ['copywriter', 'en', null],
  ['경영 컨설턴트', 'ko', '진단'], ['management consultant', 'en', '진단'],
  ['상품 기획자', 'ko', '기획'], ['product planner', 'en', '기획'],
  ['홍보 담당', 'ko', '홍보'], ['PR specialist', 'en', '홍보'],
  ['데이터 엔지니어', 'ko', '분석'], ['data engineer', 'en', '분석'],
  ['UI 디자이너', 'ko', '디자이너'], ['UI designer', 'en', '디자이너'],
  ['통번역사', 'ko', '번역'], ['translator interpreter', 'en', '번역']
];
function buildProCases() {
  const cases = [];
  for (const [input, language, occ] of [...PRO, ...PRO_EXTRA]) {
    cases.push(mk({ prefix: 'pro', input, body: {
      input, language, expectMode: 'professional_mode',
      expectOccupationCluster: occ || undefined,
      withholdCodeIfUnverified: false, noHallucinatedCode: true
    } }));
  }
  for (const [input, language, occ, ind] of PRO_WORKPLACES) {
    cases.push(mk({ prefix: 'pro_wp', input, body: {
      input, language, expectMode: 'professional_mode',
      expectOccupationCluster: occ || undefined, expectIndustryCluster: ind || undefined,
      withholdCodeIfUnverified: false, noHallucinatedCode: true
    } }));
  }
  return cases;
}

/* ===========================================================================
 * SERVICE / HOSPITALITY / RETAIL / LOGISTICS-CS / BEAUTY
 * ========================================================================= */
const SERVICE = [
  ['카페에서 바리스타로 일해요', 'ko', '음료', '음료'], ['barista at a cafe', 'en', '음료', null],
  ['식당 홀서빙', 'ko', '서비스', '음식점'], ['restaurant server', 'en', '서비스', null],
  ['호텔 프론트', 'ko', null, '숙박'], ['hotel front desk', 'en', null, null],
  ['미용실에서 머리해요', 'ko', '미용', '미용'], ['hair designer', 'en', '미용', '미용'],
  ['네일샵에서 네일아트', 'ko', '네일', '미용'], ['nail artist', 'en', '네일', null],
  ['메이크업 아티스트', 'ko', '메이크업', null], ['makeup artist', 'en', '메이크업', null],
  ['편의점 알바', 'ko', null, '소매'], ['convenience store clerk', 'en', null, null],
  ['옷가게 판매원', 'ko', '판매', '소매'], ['retail sales clerk', 'en', '판매', null],
  ['백화점 매장 직원', 'ko', '판매', '소매'], ['department store staff', 'en', '판매', null],
  ['콜센터 상담원', 'ko', '상담', null], ['call center agent', 'en', '상담', null],
  ['고객센터 CS', 'ko', '상담', null], ['customer service rep', 'en', '상담', null],
  ['온라인 쇼핑몰 CS', 'ko', null, '소매'], ['online shop customer service', 'en', null, null],
  ['택배 배송기사', 'ko', '운송', '운송'], ['delivery driver', 'en', '운송', null],
  ['주차 관리원', 'ko', '주차', null], ['parking attendant', 'en', '주차', null],
  ['빌딩 경비원', 'ko', '경비', '경비'], ['building security guard', 'en', '경비', null],
  ['마트 캐셔', 'ko', '계산', '소매'], ['supermarket cashier', 'en', '계산', null],
  ['카페 매니저', 'ko', '관리', '음료'], ['cafe manager', 'en', '관리', null],
  ['헤어 디자이너', 'ko', '미용', '미용'], ['hairstylist', 'en', '미용', null],
  ['피부관리사', 'ko', '미용', '미용'], ['esthetician', 'en', '미용', null],
  ['세탁소 직원', 'ko', '세탁', null], ['laundry worker', 'en', '세탁', null]
];
function buildServiceCases() {
  const cases = [];
  for (const [input, language, occ, ind] of SERVICE) {
    cases.push(mk({ prefix: 'svc', input, body: {
      input, language, expectMode: 'service_mode',
      expectOccupationCluster: occ || undefined, expectIndustryCluster: ind || undefined,
      withholdCodeIfUnverified: false, noHallucinatedCode: true
    } }));
  }
  // workplace-only service phrasings (ambiguity expected, still service business)
  const wp = [
    ['카페에서 일해요', 'ko', '음료'], ['식당에서 일해요', 'ko', '음식점'],
    ['호텔에서 일해요', 'ko', '숙박'], ['미용실에서 일해요', 'ko', '미용'],
    ['편의점에서 일해요', 'ko', '소매'], ['마트에서 일해요', 'ko', '소매'],
    ['I work at a cafe', 'en', '음료'], ['I work at a hotel', 'en', '숙박'],
    ['I work at a restaurant', 'en', '음식점'], ['I work at a beauty salon', 'en', '미용']
  ];
  for (const [input, language, ind] of wp) {
    cases.push(mk({ prefix: 'svc_wp', input, body: {
      input, language, expectMode: 'service_mode',
      expectIndustryCluster: ind || undefined,
      withholdCodeIfUnverified: false, noHallucinatedCode: true
    } }));
  }
  // additional service roles to comfortably exceed 80
  const more = [
    ['중식당 주방장', 'ko', '조리', '음식점'], ['한식당 요리사', 'ko', '조리', '음식점'],
    ['치킨집 알바', 'ko', null, '음식점'], ['피자집 직원', 'ko', null, '음식점'],
    ['커피숍 직원', 'ko', '음료', '음료'], ['베이커리 판매', 'ko', '판매', null],
    ['리조트 식음료', 'ko', null, '숙박'], ['게스트하우스 운영', 'ko', null, '숙박'],
    ['모텔 카운터 직원', 'ko', null, '숙박'], ['스파 관리사', 'ko', '미용', null],
    ['속눈썹 연장', 'ko', '미용', '미용'], ['왁싱샵 직원', 'ko', '미용', '미용'],
    ['반려동물 미용', 'ko', '미용', null], ['세차장 직원', 'ko', null, null],
    ['주유소 알바', 'ko', null, '소매'], ['편의점 야간 알바', 'ko', null, '소매'],
    ['옷가게 점원', 'ko', '판매', '소매'], ['화장품 매장 판매', 'ko', '판매', '소매'],
    ['핸드폰 매장 판매', 'ko', '판매', null], ['프랜차이즈 매장 매니저', 'ko', '관리', null],
    ['waiter at a restaurant', 'en', '서비스', null], ['hotel housekeeping', 'en', '청소', null],
    ['barista', 'en', '음료', null], ['cashier', 'en', '계산', null],
    ['store clerk', 'en', '판매', null], ['call center agent', 'en', '상담', null],
    ['security guard', 'en', '경비', null], ['delivery rider', 'en', '운송', null],
    ['hair stylist', 'en', '미용', null], ['esthetician', 'en', '미용', null],
    ['nail technician', 'en', '네일', null], ['pet groomer', 'en', '미용', null]
  ];
  for (const [input, language, occ, ind] of more) {
    cases.push(mk({ prefix: 'svc2', input, body: {
      input, language, expectMode: 'service_mode',
      expectOccupationCluster: occ || undefined, expectIndustryCluster: ind || undefined,
      withholdCodeIfUnverified: false, noHallucinatedCode: true
    } }));
  }
  return cases;
}

/* ===========================================================================
 * ARTS / ENTERTAINMENT / CREATOR / BEAUTY (legally sensitive)
 * ========================================================================= */
const ARTS = [
  ['댄서', 'ko', 'entertainment', '무용', true],
  ['무용수', 'ko', 'entertainment', '무용', true],
  ['안무가', 'ko', 'entertainment', '안무', false],
  ['백댄서', 'ko', 'entertainment', '무용', false],
  ['아이돌', 'ko', 'entertainment', null, true],
  ['아이돌 연습생', 'ko', 'entertainment', null, true],
  ['케이팝 아이돌', 'ko', 'entertainment', null, true],
  ['가수', 'ko', 'entertainment', '가수', false],
  ['래퍼', 'ko', 'entertainment', '가수', false],
  ['뮤지컬 배우', 'ko', 'entertainment', '배우', false],
  ['배우', 'ko', 'entertainment', '배우', false],
  ['모델', 'ko', 'entertainment', '모델', false],
  ['연주가', 'ko', 'entertainment', '연주', false],
  ['공연 예술가', 'ko', 'entertainment', null, false],
  ['보컬 트레이너', 'ko', 'entertainment', '강사', false],
  ['댄스 강사', 'ko', 'entertainment', '강사', false],
  ['dancer', 'en', 'entertainment', '무용', true],
  ['choreographer', 'en', 'entertainment', '안무', false],
  ['backup dancer', 'en', 'entertainment', '무용', false],
  ['idol', 'en', 'entertainment', null, true],
  ['K-pop trainee', 'en', 'entertainment', null, true],
  ['singer', 'en', 'entertainment', '가수', false],
  ['actor', 'en', 'entertainment', '배우', false],
  ['model', 'en', 'entertainment', '모델', false],
  ['musical actor', 'en', 'entertainment', '배우', false],
  ['dance instructor', 'en', 'entertainment', '강사', false]
];
const CREATOR = [
  ['유튜버', 'ko', '콘텐츠'], ['youtuber', 'en', '콘텐츠'],
  ['영상 편집하고 유튜브 콘텐츠 만들어요', 'ko', '콘텐츠'], ['video editor', 'en', '콘텐츠'],
  ['스트리머', 'ko', '콘텐츠'], ['streamer', 'en', '콘텐츠'],
  ['인플루언서', 'ko', null], ['influencer', 'en', null],
  ['콘텐츠 크리에이터', 'ko', '콘텐츠'], ['content creator', 'en', '콘텐츠']
];
const ARTS2 = [
  ['발레리나', 'ko', 'entertainment', '무용', false],
  ['한국무용가', 'ko', 'entertainment', '무용', false],
  ['현대무용수', 'ko', 'entertainment', '무용', false],
  ['연습생이에요', 'ko', 'entertainment', null, true],
  ['걸그룹 멤버', 'ko', 'entertainment', null, true],
  ['보이그룹 연습생', 'ko', 'entertainment', null, true],
  ['트로트 가수', 'ko', 'entertainment', '가수', false],
  ['세션 연주자', 'ko', 'entertainment', '연주', false],
  ['오케스트라 단원', 'ko', 'entertainment', '연주', false],
  ['공연단체 무용수', 'ko', 'entertainment', '무용', false],
  ['뮤지컬 배우 지망생', 'ko', 'entertainment', '배우', false],
  ['패션 모델', 'ko', 'entertainment', '모델', false],
  ['ballerina', 'en', 'entertainment', '무용', false],
  ['contemporary dancer', 'en', 'entertainment', '무용', false],
  ['session musician', 'en', 'entertainment', '연주', false],
  ['girl group member', 'en', 'entertainment', null, true],
  ['fashion model', 'en', 'entertainment', '모델', false],
  ['stage performer', 'en', 'entertainment', null, false]
];
const TATTOO = [
  ['타투이스트', 'ko'], ['문신사', 'ko'], ['반영구화장', 'ko'], ['눈썹문신', 'ko'],
  ['타투샵 운영', 'ko'], ['반영구 화장사', 'ko'], ['문신아티스트', 'ko'],
  ['tattoo artist', 'en'], ['cosmetic tattoo artist', 'en'], ['permanent makeup artist', 'en'],
  ['tattooist', 'en']
];
function buildArtsCases() {
  const cases = [];
  for (const [input, language, sens, occ, clarify] of [...ARTS, ...ARTS2]) {
    cases.push(mk({ prefix: 'arts', input, body: {
      input, language, expectMode: 'arts_entertainment_mode',
      expectLegalSensitivity: sens, expectOccupationCluster: occ || undefined,
      clarificationRequired: clarify === true ? true : undefined,
      withholdCodeIfUnverified: occ ? false : true, noHallucinatedCode: true
    } }));
  }
  for (const [input, language, occ] of CREATOR) {
    cases.push(mk({ prefix: 'creator', input, body: {
      input, language, expectMode: 'professional_mode',
      expectOccupationCluster: occ || undefined,
      withholdCodeIfUnverified: false, noHallucinatedCode: true
    } }));
  }
  for (const [input, language] of TATTOO) {
    cases.push(mk({ prefix: 'tattoo', input, body: {
      input, language, expectMode: 'service_mode',
      expectLegalSensitivity: 'tattoo', expectMaxConfidence: 'low',
      expectWarningIncludes: '문신', withholdCodeIfUnverified: false, noHallucinatedCode: true
    } }));
  }
  return cases;
}

/* ===========================================================================
 * AMBIGUOUS / FUZZY / MISSPELLED / MULTILINGUAL
 * ========================================================================= */
const AMBIG = [
  ['프리랜서', 'ko'], ['freelancer', 'en'], ['알바', 'ko'], ['아르바이트', 'ko'],
  ['회사원', 'ko'], ['직장인', 'ko'], ['일해요', 'ko'], ['돈 벌어요', 'ko'],
  ['취업했어요', 'ko'], ['회사 다녀요', 'ko'], ['job', 'en'], ['work', 'en'],
  ['I have a job', 'en'], ['part time worker', 'en'], ['자영업해요', 'ko'],
  ['사업해요', 'ko'], ['장사해요', 'ko'], ['뭐든 해요', 'ko'], ['이것저것 해요', 'ko'],
  ['그냥 일함', 'ko'], ['바리스타아', 'ko'], ['개발', 'ko'], ['디자인 일', 'ko'],
  ['cafe에서 알바해요', 'mixed'], ['공장 다녀요', 'ko'], ['현장 일해요', 'ko'],
  ['배달해요', 'ko'], ['청소 일', 'ko'], ['서비스직', 'ko'], ['생산직', 'ko'],
  ['ilhaeyo', 'en'], ['알바생', 'ko'], ['투잡 해요', 'ko'], ['부업해요', 'ko'],
  ['인턴이에요', 'ko'], ['수습이에요', 'ko'], ['파견 나가요', 'ko'], ['용역 일해요', 'ko'],
  ['일용직', 'ko'], ['막노동', 'ko'], ['노가다', 'ko'], ['손님 응대', 'ko'],
  ['가게 봐요', 'ko'], ['매장 일해요', 'ko'], ['사무 봐요', 'ko'], ['관리 일', 'ko'],
  ['contractor', 'en'], ['gig worker', 'en'], ['odd jobs', 'en'], ['self employed', 'en'],
  ['I run a small business', 'en'], ['打工', 'zh'], ['工作', 'zh'], ['会社員', 'ko'],
  ['뭔가 만들어요', 'ko'], ['포장 일', 'ko'], ['상하차', 'ko'], ['새벽 알바', 'ko'],
  ['주말 알바', 'ko'], ['단기 알바', 'ko']
];
function buildAmbigCases() {
  const cases = [];
  for (const [input, language] of AMBIG) {
    cases.push(mk({ prefix: 'ambig', input, body: {
      input, language, neverSilentDeadEnd: true,
      // mode is intentionally NOT asserted strictly here; many of these are
      // legitimately ambiguous OR resolve to a field/service cluster. The runner
      // only requires: understood-or-clarified, no hallucinated code.
      noHallucinatedCode: true
    } }));
  }
  return cases;
}

/* ===========================================================================
 * Emit
 * ========================================================================= */
const META = {
  schema_version: '2026-06-employment-analyzer-mode-test-cases',
  generated_by: 'scripts/build_employment_test_cases.mjs',
  contract: {
    noHallucinatedCode: 'always: every returned candidate code exists in jobcode_master.json with the matching type',
    tracksSeparated: 'always: occupation candidates type occupation, industry candidates type industry',
    sourceMetadataPresent: 'always: sourceNotes non-empty',
    expectMode: 'res.mode must equal this (when present)',
    expectSignals: 'parsedSignals must contain >=1 of these kinds (field cases)',
    expectOccupationCluster: 'SOFT: keyword should appear in some occupation candidate, OR the code is withheld and clarification is required. Aggregate hit-rate is gated.',
    expectIndustryCluster: 'SOFT: same for industry',
    expectLegalSensitivity: 'extracted.legalSensitivity includes this',
    expectMaxConfidence: 'no candidate exceeds this confidence',
    expectWarningIncludes: 'some warning contains this string',
    clarificationRequired: 'res.clarificationRequired must be true',
    withholdCodeIfUnverified: 'documentation: code may be withheld for unverified mapping',
    neverSilentDeadEnd: 'must return candidates OR an interpretation + clarification'
  }
};

console.log('Generating employment-analyzer mode test suites…');
out('field_labor_test_cases.json', { ...META, mode: 'field_labor_mode', cases: buildFieldCases() });
out('professional_test_cases.json', { ...META, mode: 'professional_mode', cases: buildProCases() });
out('service_test_cases.json', { ...META, mode: 'service_mode', cases: buildServiceCases() });
out('arts_entertainment_test_cases.json', { ...META, mode: 'arts_entertainment_mode', cases: buildArtsCases() });
out('ambiguous_test_cases.json', { ...META, mode: 'ambiguous_mode', cases: buildAmbigCases() });
console.log('Done.');
