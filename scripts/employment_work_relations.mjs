/**
 * Structured employment relationship detection (KSCO/KSIC are NOT defined here).
 *
 * Read the sentence's grammatical roles before looking up codes:
 *   "I recruit nurses"  → nurses are task targets, not the user's profession.
 *   "I work as a nurse" → nurse is the user's profession.
 * Rules only create grounded retrieval hints. All codes come from the
 * canonical dataset in employment_code_analyzer.mjs.
 */
const KO_STAFF_TARGETS = [
  '직원', '인력', '근로자', '종사자', '팀원', '교사', '교원', '강사',
  '간호사', '의사', '개발자', '디자이너', '요리사', '청소원', '청소부',
  '기사', '보조교사', '관리사', '상담사', '사회복지사', '연구원'
];
const EN_STAFF_TARGETS = [
  'staff', 'employees', 'workers', 'teachers', 'nurses', 'doctors',
  'developers', 'designers', 'engineers', 'drivers', 'cleaners',
  'instructors', 'contractors', 'chefs', 'cooks', 'interpreters'
];
const KO_MANAGING = '관리|채용|선발|배치|감독|총괄|조율|운영|근태|인사|급여|연수|훈련|교육|스케줄|일정|코디네이|지원';
const EN_MANAGING = '(?:manag(?:e|es|ing|ement)?|supervis(?:e|es|ing|ion)?|hir(?:e|es|ing)?|recruit(?:s|ing|ment)?|schedul(?:e|es|ing)?|coordinat(?:e|es|ing|ion)?|oversee|overseeing|train(?:s|ing)?|staffing)';
const escapeRx = (s) => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');

function usableRoleSurface(surface) {
  const s = String(surface || '').trim().toLowerCase();
  if (s.length < 2 || s.length > 32) return false;
  // Exclude generic activities ("개발", "연구", "운영", "영어 수업") that could
  // refer to objects or processes, rather than a human occupation.
  if (/[가-힣]/.test(s)) return /(?:교사|교원|강사|교수|조교|의사|간호사|기사|직원|인력|종사자|개발자|디자이너|기술자|엔지니어|연구원|상담사|관리사|요리사|조리사|청소원|청소부|관리자|매니저|바리스타|변호사|회계사|약사|사회복지사|가수|배우|모델|댄서|작가|프로그래머)$/.test(s);
  return /(?:teacher|nurse|doctor|developer|designer|driver|worker|staff|employee|engineer|translator|interpreter|chef|cook|instructor|assistant|technician|manager|researcher|consultant|analyst|accountant|lawyer|artist|actor)$/.test(s);
}

function findManagedTarget(query, roleSurfaces) {
  const all = [...new Set([...KO_STAFF_TARGETS, ...EN_STAFF_TARGETS, ...(roleSurfaces || [])]
    .map((x) => String(x || '').trim().toLowerCase()).filter(usableRoleSurface))]
    .sort((a, b) => b.length - a.length);
  for (const surface of all) {
    const t = escapeRx(surface).replace(/\\ /g, '\\s+');
    const ko = /[가-힣]/.test(surface);
    if (ko) {
      // "영어 보조교사를 관리", "간호사들의 근태를 관리", "요리사 채용".
      const tail = '(?:들|분|님|들분)?(?:을|를|의|에게|에\\s*대한|들에\\s*대한)?';
      const qualifier = '(?:\\s*(?:근태|급여|스케줄|일정|인사|채용|배치|교육|연수|훈련|업무)(?:를|을|의)?)?';
      const pattern = new RegExp(t + tail + qualifier + '\\s*(?:' + KO_MANAGING + ')', 'u');
      const m = pattern.exec(query);
      if (m) return { target: surface, phrase: m[0], action: findKoreanAction(m[0]) };
    } else {
      const plural = surface.endsWith('s') ? '' : 's?';
      const obj = '\\b' + t + plural + '\\b';
      const prefix = new RegExp(EN_MANAGING + '\\s+(?:(?:the|our|new|junior|foreign|all|a|an|team|english-speaking)\\s+){0,4}' + obj, 'i');
      const suffix = new RegExp(obj + '\\s+(?:recruitment|staffing|management|training|schedules?|coordination|supervision)', 'i');
      const m = prefix.exec(query) || suffix.exec(query);
      if (m) return { target: surface, phrase: m[0], action: findEnglishAction(m[0]) };
    }
  }
  return null;
}
function findKoreanAction(s) {
  const m = String(s).match(new RegExp(KO_MANAGING));
  return m ? m[0] : '관리';
}
function findEnglishAction(s) {
  const m = String(s).match(new RegExp(EN_MANAGING, 'i'));
  return m ? m[0].toLowerCase() : 'management';
}
function explicitPersonalRole(text, roleSurfaces) {
  const q = String(text || '').toLowerCase();
  for (const surface of roleSurfaces || []) {
    if (!usableRoleSurface(surface)) continue;
    const term = escapeRx(String(surface).trim().toLowerCase()).replace(/\\ /g, '\\s+');
    if (/[가-힣]/.test(term)) {
      const self = new RegExp(term + '(?:으)?로(?:서)?\\s*(?:일|근무|재직|종사|활동|취업)|(?:저는|제가|나는|난)\\s*.{0,20}?' + term + '(?:입니다|이에요|예요)', 'u');
      if (self.test(q)) return surface;
    } else {
      if (new RegExp('\\b(?:i am|i.m|i work as|my job is)\\s+(?:(?:a|an|the)\\s+)?' + term + '\\b', 'i').test(q)) return surface;
    }
  }
  return '';
}
function dutyFamily(text) {
  const t = String(text || '').toLowerCase();
  if (/채용|선발|배치|인사|근태|급여|hire|recruit|staffing|payroll/.test(t)) return 'staffing';
  if (/연수|훈련|교육|train|instruct/.test(t)) return 'training';
  if (/일정|스케줄|schedule|rota|shifts?/.test(t)) return 'scheduling';
  if (/감독|총괄|팀장|과장|부서장|supervis|oversee|head of|director/.test(t)) return 'supervision';
  return 'coordination';
}
const ROLE_CANDIDATE_NAMES = {
  staffing: ['인사 및 노무 사무원', '인사 및 노사 관련 전문가', '총무 사무원 및 대학 행정조교'],
  training: ['교육 및 훈련 사무원', '인사 및 노무 사무원', '총무 사무원 및 대학 행정조교'],
  scheduling: ['총무 사무원 및 대학 행정조교', '인사 및 노무 사무원', '행정 및 경영 지원 관리자'],
  supervision: ['행정 및 경영 지원 관리자', '인사 및 노무 사무원', '총무 사무원 및 대학 행정조교'],
  coordination: ['인사 및 노무 사무원', '총무 사무원 및 대학 행정조교', '행정 및 경영 지원 관리자']
};
export function inferEmploymentRelation(text, roleSurfaces = []) {
  const query = String(text || '').toLowerCase().replace(/\\s+/g, ' ').trim();
  const hit = findManagedTarget(query, roleSurfaces);
  if (!hit) return null;
  const own = explicitPersonalRole(query, roleSurfaces);
  const duty = dutyFamily(query);
  const educationAuthority = /교육청|교육지원청|(?:office of education|education authority|education department)/i.test(query);
  const specificDuty = duty !== 'coordination' || /(?:채용|배치|인사|근태|급여|연수|훈련|일정|스케줄|행정|supervis|hire|recruit|train|schedule)/i.test(query);
  const roleNames = ROLE_CANDIDATE_NAMES[duty].slice();
  if (educationAuthority) {
    if (!roleNames.includes('기타 정부 행정 사무원')) roleNames.push('기타 정부 행정 사무원');
    if (!roleNames.includes('교육 및 훈련 사무원')) roleNames.push('교육 및 훈련 사무원');
    if (duty === 'supervision') roleNames.unshift('교육 관리자');
  }
  return {
    kind: own ? 'mixed' : 'managed_staff',
    target: hit.target, action: hit.action, duty, selfRole: own || null,
    educationAuthority, specificDuty,
    roleNames: [...new Set(roleNames)],
    requiresClarification: !specificDuty || !!own
  };
}

export function relationQuestion(relation, locale = 'ko') {
  if (!relation || !relation.requiresClarification) return null;
  if (relation.kind === 'mixed') return {
    flag: 'own_role_and_staff_management',
    question: locale === 'en'
      ? 'Is your primary occupation the professional role you mentioned, or personnel management?'
      : '직접 해당 직무를 수행하는 것이 주업무인가요, 아니면 해당 인력을 관리하는 것이 주업무인가요?',
    chips: locale === 'en'
      ? ['I work in the profession', 'I mainly manage personnel']
      : ['해당 직무를 직접 수행해요', '인력 관리가 주업무예요']
  };
  return {
    flag: 'managed_staff_duties',
    question: locale === 'en'
      ? 'What do you mainly do with the staff you mentioned?'
      : '말씀하신 인력과 관련해 주로 어떤 업무를 하시나요?',
    chips: locale === 'en'
      ? ['Recruitment and HR', 'Training and development', 'Scheduling and coordination', 'Department management']
      : ['인사·채용·배치', '교육·연수·훈련', '일정·근태·업무 조율', '부서 및 인력 총괄']
  };
}
