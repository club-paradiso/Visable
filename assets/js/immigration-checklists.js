/* Visable checklists: sourced snapshots + Human-First progressive disclosure + non-publishing editing drafts. */
(function () {
'use strict';

var base = 'data/immigration-checklists/';
var N_KEY = 'visable.checklists.nationalDrafts.v1';
var O_KEY = 'visable.checklists.officeDrafts.v1';
var C_KEY = 'visable.checklists.checked.v1';

var state = {
  procedure: 'extension',
  query: '',
  office: '',
  limit: 30,
  step: 1, // 1: task, 2: status, 3: scenario, 4: checklist
  status_code: '',
  scenario_id: '',
  selected_item: null,
  lang: 'ko',
  operator_mode: false,
  datasets: {},
  offices: [],
  overrides: [],
  nationalDrafts: {},
  officeDrafts: {},
  checked_docs: {},
  notes: null
};

var $ = function (id) { return document.getElementById(id); };
var FIELDS = ['required_text', 'conditional_text', 'application_text', 'note_text'];

// Standard visa status dictionary for human-friendly plain language discovery
var VISA_DESCRIPTIONS = {
  'A-1': { name: '외교', en: 'Diplomat', desc: '주한 공관원 및 동등 외교관' },
  'A-2': { name: '공무', en: 'Official Duty', desc: '외국 정부 또는 국제기구의 공무 수행자' },
  'A-3': { name: '협정', en: 'Treaty', desc: '협정에 따른 주한미군 및 관계자' },
  'B-1': { name: '사증면제', en: 'Visa Exemption', desc: '협정에 따른 단기 무사증 체류' },
  'B-2': { name: '관광통과', en: 'Tourist/Transit', desc: '무사증 관광 및 통과 체류' },
  'C-1': { name: '일시취재', en: 'Temporary Journalism', desc: '일시적인 보도·취재 활동' },
  'C-3': { name: '단기방문', en: 'Short-term Visit', desc: '90일 이내 단기 관광·출장·친지방문' },
  'C-4': { name: '단기취업', en: 'Short-term Employment', desc: '90일 이내의 일시 공연·계절근로·취업' },
  'D-1': { name: '문화예술', en: 'Culture & Arts', desc: '학술·예술활동 및 전통문화 연구' },
  'D-2': { name: '유학', en: 'Study (Degree)', desc: '대학·대학원의 전문학사, 학사, 석사, 박사 학위과정' },
  'D-2-1': { name: '전문학사 유학', en: 'Associate Degree', desc: '전문대학 유학 학위과정' },
  'D-2-2': { name: '학사 유학', en: 'Bachelor Degree', desc: '4년제 대학교 학부과정' },
  'D-2-3': { name: '석사 유학', en: 'Master Degree', desc: '대학원 석사학위 정규과정' },
  'D-2-4': { name: '박사 유학', en: 'Doctoral Degree', desc: '대학원 박사학위 정규과정' },
  'D-2-6': { name: '교환학생', en: 'Exchange Student', desc: '국내외 대학 협정에 따른 교환학생' },
  'D-2-7': { name: '정부초청 장학생', en: 'Govt Scholarship Student', desc: '대한민국 정부초청 외국인 장학생' },
  'D-2-8': { name: '단기유학', en: 'Short-term Study', desc: '1년 이하의 학점취득 및 단기 유학 연수' },
  'D-3': { name: '기술연수', en: 'Industrial Trainee', desc: '국내 기업체 기술·기능 연수' },
  'D-4': { name: '일반연수', en: 'General Training', desc: '대학 부설 어학원 어학연수 및 초중고 연수' },
  'D-4-1': { name: '어학연수', en: 'Korean Language Trainee', desc: '대학 어학당 한국어 어학연수과정' },
  'D-4-2K': { name: '기업 맞춤형 연수(K-Trainee)', en: 'Customized Corporate Trainee', desc: '외투기업 및 해외투자 연계 맞춤형 기업 연수' },
  'D-5': { name: '취재', en: 'Journalism', desc: '외국 언론사 국내 상주 파견 기자' },
  'D-6': { name: '종교', en: 'Religion', desc: '외국 종교단체 파견 종교 활동' },
  'D-7': { name: '주재', en: 'Intra-Company Transferee', desc: '외국 본사에서 국내 지사·영업소 파견 주재원' },
  'D-8': { name: '기업투자', en: 'Foreign Investor', desc: '외국인투자촉진법에 따른 법인 투자 및 경영' },
  'D-8-1': { name: '법인투자', en: 'Incorporated Enterprise', desc: '외국인투자기업 국내 경영·관리자' },
  'D-8-4': { name: '기술창업', en: 'Tech Startup', desc: 'OASIS 기술창업 프로그램 참여 및 스타트업' },
  'D-9': { name: '무역경영', en: 'Trade & Business', desc: '외국인 무역업 영위 및 전문설비 도입·선박 감리' },
  'D-10': { name: '구직', en: 'Job Seeking', desc: '전문인력 취업 준비 및 스타트업 창업 준비' },
  'D-10-1': { name: '일반 구직', en: 'General Job Seeking', desc: '국내외 대학 졸업자 전문직 구직활동' },
  'D-10-2': { name: '기술창업 준비', en: 'Tech Startup Prep', desc: '기술창업 OASIS 프로그램 및 법인설립 준비' },
  'D-10-T': { name: '톱티어 구직', en: 'Top-Tier Job Seeking', desc: '세계 유수대학 졸업자 및 글로벌 첨단인재 국내 구직활동' },
  'E-1': { name: '교수', en: 'Professor', desc: '대학교원 및 전문대학 연구교수' },
  'E-2': { name: '회화지도', en: 'Foreign Language Instructor', desc: '외국어 학원 및 초중고 외국어 원어민 강사' },
  'E-3': { name: '연구', en: 'Research', desc: '연구기관의 자연과학·공학 등 전문 연구원' },
  'E-4': { name: '기술지도', en: 'Technology Transfer', desc: '자연과학·첨단산업 기술 도입 제공자' },
  'E-5': { name: '전문직업', en: 'Professional Employment', desc: '의사, 변호사, 회계사, 항공기 조종사 등' },
  'E-6': { name: '예술흥행', en: 'Arts & Entertainment', desc: '방송·음악·공연·호텔공연 및 프로운동선수' },
  'E-7': { name: '특정활동', en: 'Special Ability', desc: '대한민국 공·사기관 고용 전문인력 (87개 직종)' },
  'E-7-1': { name: '전문인력', en: 'Professional Personnel', desc: '관리자 및 첨단·전문가 (IT, 엔지니어, 마케팅 등)' },
  'E-7-2': { name: '준전문인력', en: 'Semi-Professional Personnel', desc: '면세점 판매원, 항공운송 사무원 등' },
  'E-7-3': { name: '일반기능인력', en: 'General Skilled Worker', desc: '조선용접공, 뿌리기업 기능인력 등' },
  'E-7-4': { name: '숙련기능인력', en: 'Skilled Technician (K-point)', desc: 'E-9/E-10 장기근무자 숙련기능 점수제 전환' },
  'E-7-4R': { name: '지역특화 숙련기능', en: 'Regional Skilled Technician', desc: '인구감소지역 장기체류 숙련기능 점수제 특례' },
  'E-7-S': { name: '혁신인재 네거티브', en: 'Innovative Talent (Negative List)', desc: '첨단 신산업·혁신분야 네거티브 규제 적용 전문인력' },
  'E-7-T': { name: '톱티어 전문인력', en: 'Top-Tier Professional', desc: 'AI·반도체 등 첨단 과학기술 분야 최고급 인재' },
  'E-7-Y': { name: '청년 우수인재', en: 'Global Youth Talent', desc: '세계 유수대학 졸업 청년 대상 전문인력' },
  'E-8': { name: '계절근로', en: 'Seasonal Worker', desc: '농번기·어번기 단기 계절근로' },
  'E-9': { name: '비전문취업', en: 'Non-Professional (EPS)', desc: '고용허가제 제조업·농축산업·어업·건설업' },
  'E-10': { name: '선원취업', en: 'Vessel Crew', desc: '연근해 어선 및 내항여객선 선원' },
  'F-1': { name: '방문동거', en: 'Visiting & Joining Family', desc: '친척 방문, 가사보조, 동반 가족의 거주' },
  'F-2': { name: '거주', en: 'Resident', desc: '점수제 우수인재, 영주자격 이전 장기 거주' },
  'F-2-7': { name: '점수제 우수인재', en: 'Points-based Resident', desc: '학력·소득·한국어 점수제 우수인재 거주' },
  'F-2-7S': { name: 'K-STAR·잠재적 우수인재', en: 'K-STAR & Potential Talent', desc: '이공계 특성화대학 졸업자 및 K-STAR 우수인재 거주' },
  'F-2-R': { name: '지역특화형 거주', en: 'Regional Specialized Resident', desc: '인구감소지역 우수인재 및 동포 정착 지원' },
  'F-2-T': { name: '톱티어 우수인재', en: 'Top-Tier Resident', desc: '글로벌 톱티어 첨단인재 대상 장기 거주' },
  'F-3': { name: '동반', en: 'Dependent Family', desc: '전문인력(D·E 계열) 및 동포(F-4·H-2) 등록자의 동반 가족' },
  'F-3-19': { name: '재외동포 동반가족', en: 'Overseas Korean Dependent', desc: '재외동포(F-4) 자격 소지자의 배우자 및 미성년 자녀' },
  'F-3-20': { name: '방문취업 동반가족', en: 'Working Visit Dependent', desc: '방문취업(H-2) 자격 소지자의 배우자 및 미성년 자녀' },
  'F-4': { name: '재외동포', en: 'Overseas Korean', desc: '대한민국 국적을 보유했던 자 및 직계비속 동포' },
  'F-4-R': { name: '지역특화 재외동포', en: 'Regional Overseas Korean', desc: '인구감소지역 거주 재외동포 특례 거소신고' },
  'F-5': { name: '영주', en: 'Permanent Resident', desc: '체류기간 제한 없는 영주자격 (10년 주기 영주증 갱신 대상)' },
  'F-5-S1': { name: 'K-STAR 영주', en: 'K-STAR Permanent Resident', desc: '이공계 첨단인재 K-STAR 트랙 영주' },
  'F-5-T': { name: '톱티어 영주', en: 'Top-Tier Permanent Resident', desc: '세계 최고급 첨단인재 톱티어 패스트트랙 영주' },
  'F-6': { name: '결혼이민', en: 'Marriage Migrant', desc: '대한민국 국민과 혼인 관계를 유지하는 배우자' },
  'F-6-1': { name: '국민의 배우자', en: 'Spouse of Korean National', desc: '한국인 배우자와 정상적인 혼인 유지' },
  'F-6-2': { name: '자녀양육', en: 'Child Rearing', desc: '국민과의 혼인관계 종료 후 미성년 자녀 양육' },
  'F-6-3': { name: '귀책사유 혼인단절', en: 'Non-Fault Divorce', desc: '배우자 사망·실종 또는 배우자 귀책사유로 인한 이혼 후 체류' },
  'G-1': { name: '기타', en: 'Miscellaneous', desc: '산재 치료, 소송 수행, 난민인정 신청 등 인도적 체류' },
  'G-1-1': { name: '산재 치료', en: 'Industrial Accident Care', desc: '업무상 재해로 인한 치료 및 요양' },
  'G-1-2': { name: '질병·사고 치료', en: 'Medical Treatment', desc: '질병 또는 사고로 인한 치료 및 간병' },
  'G-1-3': { name: '소송 수행', en: 'Lawsuit / Legal Action', desc: '임금체불 등 재판 및 소송 수행' },
  'G-1-5': { name: '난민신청자', en: 'Refugee Applicant', desc: '대한민국 난민인정 심사 진행 중 체류' },
  'G-1-6': { name: '인도적 체류자', en: 'Humanitarian Status', desc: '난민 불인정자 중 인도적 사유로 인한 체류' },
  'H-1': { name: '관광취업', en: 'Working Holiday', desc: '협정국 청년의 관광 및 단기취업' },
  'H-2': { name: '방문취업', en: 'Working Visit', desc: '외국국적동포(중국·CIS 등) 단순노무·서비스업 취업' }
};

function element(tag, cls, textContent) {
  var e = document.createElement(tag);
  if (cls) e.className = cls;
  if (textContent !== undefined && textContent !== null) e.textContent = String(textContent);
  return e;
}

function append(parent, children) {
  children.forEach(function (x) { if (x) parent.appendChild(x); });
  return parent;
}

function safeRead(key) {
  try {
    var val = JSON.parse(localStorage.getItem(key) || '{}');
    return val && typeof val === 'object' && !Array.isArray(val) ? val : {};
  } catch (e) {
    return {};
  }
}

function safeSave(key, val) {
  try {
    localStorage.setItem(key, JSON.stringify(val));
  } catch (e) {
    window.alert('이 기기에는 저장할 수 없습니다. JSON을 먼저 내려받으세요.');
  }
}

function normalize(s) {
  return String(s || '').normalize('NFKC').toLocaleLowerCase('ko').replace(/\s+/g, '');
}

function meta(item) {
  return [item.status_code, item.scenario, item.required_text, item.conditional_text, item.note_text, item.application_text].join(' ');
}

function note(parent, title, value, cls) {
  if (!value || value === '별도 기재 없음') return;
  var block = element('section', 'doc-block ' + (cls || ''));
  var h = element('h4', '', title);
  block.appendChild(h);
  if (title === '기본·명시 서류' && String(value).includes('; ')) {
    var ul = element('ul', 'doc-list');
    String(value).split(/;\s*/).map(function (v) { return v.trim(); }).filter(Boolean).forEach(function (v) {
      ul.appendChild(element('li', '', v));
    });
    block.appendChild(ul);
  } else {
    block.appendChild(element('p', '', value));
  }
  parent.appendChild(block);
}

function getDataset() {
  return state.datasets[state.procedure];
}

function activeRow(original) {
  var patch = state.nationalDrafts[original.id] || null;
  if (!patch) return original;
  var copy = Object.assign({}, original);
  FIELDS.forEach(function (k) {
    if (typeof patch[k] === 'string') copy[k] = patch[k];
  });
  return copy;
}

function approvedOverride(entry) {
  if (!entry || !entry.office_id || !entry.item_id) return false;
  if (!['OFFICIAL_LOCAL_GUIDANCE', 'VERIFIED_LOCAL_PRACTICE'].includes(entry.review_state)) return false;
  if (!entry.evidence || !Array.isArray(entry.evidence) || entry.evidence.length === 0) return false;
  if (entry.review_state === 'OFFICIAL_LOCAL_GUIDANCE' && !entry.evidence.some(function (e) { return e.type === 'office_notice' && e.url; })) return false;
  if (entry.review_state === 'VERIFIED_LOCAL_PRACTICE' && !entry.evidence.some(function (e) { return e.type === 'corroborated_reports' && Number(e.count) >= 2; })) return false;
  if (entry.expires_on && !/^\d{4}-\d{2}-\d{2}$/.test(entry.expires_on)) return false;
  if (entry.expires_on && entry.expires_on < new Date().toISOString().slice(0, 10)) return false;
  return true;
}

function officeName(id) {
  var p = state.offices.find(function (x) { return x.id === id; });
  return p ? p.name_ko : id;
}

function localNotes(item) {
  var found = state.overrides.filter(function (o) {
    return o.item_id === item.id && o.office_id === state.office && approvedOverride(o);
  });
  var draft = state.officeDrafts[item.id + '@' + state.office];
  if (draft) {
    found.push(Object.assign({ review_state: 'DRAFT', office_id: state.office }, draft));
  }
  return found;
}

function officeCallout(entry) {
  var card = element('div', 'office-specific');
  var head = element('h4', '', entry.review_state === 'DRAFT' ? '관서별 편집 초안 · 공개되지 않음' : entry.review_state === 'OFFICIAL_LOCAL_GUIDANCE' ? '관서 공식 안내 · 전국 기준과 별도' : '검증된 관서 실무 · 전국 기준과 별도');
  append(card, [head, element('p', '', officeName(entry.office_id))]);
  FIELDS.forEach(function (k) {
    if (entry.changes && typeof entry.changes[k] === 'string' && entry.changes[k].trim()) {
      note(card, ({ 'required_text': '관서별 요청 서류', 'conditional_text': '관서별 조건·생략', 'application_text': '관서별 본인·대리 안내', 'note_text': '관서별 추가 정보' })[k], entry.changes[k]);
    }
  });
  if (entry.evidence && entry.evidence.length) {
    append(card, [element('p', 'evidence', '근거: ' + entry.evidence.map(function (e) { return e.url || e.type; }).join(' · '))]);
  }
  if (entry.editor_note) {
    append(card, [element('p', 'evidence', '검토 메모: ' + entry.editor_note)]);
  }
  return card;
}

function getProcedureTitle(proc) {
  if (proc === 'extension') return '체류기간 연장';
  if (proc === 'change') return '체류자격 변경';
  if (proc === 'registration') return '외국인등록·국내거소신고';
  return proc;
}

function getVisaInfo(rawCode) {
  if (!rawCode) return { name: '알 수 없음', en: 'Unknown', desc: '체류자격 정보' };
  var clean = String(rawCode).trim();
  var code = clean.split(' ')[0].split('·')[0].split('(')[0].trim();

  if (VISA_DESCRIPTIONS[clean]) return VISA_DESCRIPTIONS[clean];
  if (VISA_DESCRIPTIONS[code]) return VISA_DESCRIPTIONS[code];

  var parts = code.split('-');
  if (parts.length >= 3) {
    var sub = parts.slice(0, 3).join('-');
    if (VISA_DESCRIPTIONS[sub]) return VISA_DESCRIPTIONS[sub];
    var sub2 = parts.slice(0, 2).join('-');
    if (VISA_DESCRIPTIONS[sub2]) return VISA_DESCRIPTIONS[sub2];
  } else if (parts.length === 2) {
    var root = parts[0];
    if (VISA_DESCRIPTIONS[root]) return VISA_DESCRIPTIONS[root];
  }
  return { name: code, en: code, desc: '체류자격 ' + code };
}

function splitParenSafe(text) {
  if (!text) return [];
  var chunks = [];
  var current = '';
  var parenDepth = 0;
  var bracketDepth = 0;

  for (var i = 0; i < text.length; i++) {
    var ch = text[i];
    if (ch === '(') parenDepth++;
    else if (ch === ')') { if (parenDepth > 0) parenDepth--; }
    else if (ch === '[') bracketDepth++;
    else if (ch === ']') { if (bracketDepth > 0) bracketDepth--; }

    var isDelimiter = (ch === ';' || ch === '\n' || ch === '、' ||
      (ch === ',' && parenDepth === 0 && bracketDepth === 0 &&
       /,\s*(?=[가-힣A-Za-z0-9]+[의·\s]*(?:서류|증명|신청서|사본|계약서|여권|사진|확인서|동의서|등록증|진술서|표|공문|영수증|소견서|통장|납세))/
       .test(text.slice(i, i + 35))));

    if (isDelimiter && parenDepth === 0 && bracketDepth === 0) {
      if (current.trim()) chunks.push(current.trim());
      current = '';
    } else {
      current += ch;
    }
  }
  if (current.trim()) chunks.push(current.trim());
  return chunks;
}

function parseRequiredDocsStructured(text, item) {
  if (!text || text === '별도 기재 없음') {
    return {
      restrictions: [],
      unlisted: true,
      unlistedText: '원문에 명시된 기본 제출 서류가 기재되지 않았습니다. 관할 출입국·외국인관서 또는 1345에 확인하세요.',
      items: []
    };
  }

  var chunks = splitParenSafe(String(text));
  var restrictions = [];
  var docs = [];
  var unlistedText = null;

  chunks.forEach(function (c, idx) {
    var trimmed = c.trim();
    if (!trimmed) return;

    // Check for ineligibility or domestic change prohibition
    if (/대상\s*아님|해당\s*없음|변경\s*불가|자격변경\s*불가|신청\s*불가/i.test(trimmed)) {
      restrictions.push(trimmed);
      return;
    }

    // Check for unlisted standalone manual requirements
    if (/확인\s*불가|원문\s*미기재|별도\s*기재\s*없음|목록\s*미기재/i.test(trimmed)) {
      unlistedText = trimmed;
      return;
    }

    var reqType = 'mandatory';
    var isAlternative = /또는|혹은|택\s*1|갈음|대체\s*가능/i.test(trimmed);
    var isConditional = /\(해당자\)|해당자에\s*한함|소지자에\s*한함|해당하는\s*경우/i.test(trimmed);

    if (isAlternative) reqType = 'alternative';
    else if (isConditional) reqType = 'conditional';

    docs.push({
      id: (item ? item.id : 'doc') + '-' + idx,
      label: trimmed,
      type: reqType,
      isFormHelper: /통합신청서|신청서/i.test(trimmed)
    });
  });

  return {
    restrictions: restrictions,
    unlisted: Boolean(unlistedText),
    unlistedText: unlistedText,
    items: docs
  };
}

function parseRequiredDocs(text) {
  var structured = parseRequiredDocsStructured(text);
  if (structured.items.length) {
    return structured.items.map(function (d) { return d.label; });
  }
  if (structured.restrictions.length || structured.unlisted) {
    return [];
  }
  return text ? [text.trim()] : [];
}

/* ------------------------------------------------------------------------- */
/* CARD RENDERING (Results Section in Direct Search)                         */
/* ------------------------------------------------------------------------- */
function card(original) {
  var item = activeRow(original);
  var cardEl = element('article', 'doc-card');

  var head = element('div', 'card-head');
  var left = element('div');
  var code = element('span', 'code-pill', item.status_code);
  append(left, [code, element('h3', '', item.scenario)]);

  var right = element('div', 'card-head-actions');
  append(right, [element('span', 'chip', state.nationalDrafts[item.id] ? '로컬 문구 초안' : '원문 편집본')]);

  // Maintainer button: Accessible name contains "문구 편집" for E2E tests and maintainers
  var btn = element('button', 'outline-button', '워딩 수정');
  btn.type = 'button';
  btn.setAttribute('aria-label', item.status_code + ' ' + item.scenario + ' 문구 편집');
  btn.addEventListener('click', function () { openEditor(original); });
  right.appendChild(btn);

  append(head, [left, right]);
  cardEl.appendChild(head);

  var body = element('div', 'card-body');
  note(body, '기본·명시 서류', item.required_text);
  note(body, '해당자·대체·생략 조건', item.conditional_text, 'conditional');
  note(body, '본인·대리 신청', item.application_text || (state.procedure === 'registration' ? '신규 외국인등록 및 국내거소신고는 등록대상자의 연령·생체정보 등록 여부에 따라 본인 출석이 필요할 수 있습니다. 대리 접수 가능 여부와 생체정보 제공 절차는 별도로 확인해야 합니다.' : ''));
  note(body, '비고 및 원문 주의', item.note_text);
  cardEl.appendChild(body);

  if (state.office) {
    localNotes(item).forEach(function (o) { cardEl.appendChild(officeCallout(o)); });
  }

  var tail = element('div', 'card-tail');
  var prov = element('div', 'card-provenance');
  append(prov, [
    element('span', '', '원문 편집본 ' + item.source_line + '행'),
    element('span', '', '·'),
    element('span', '', item.source_section || ''),
    element('span', '', '·'),
    element('span', '', '검토 필요')
  ]);

  var quickBtn = element('button', 'card-quick-cta', '맞춤 체크리스트로 열기 →');
  quickBtn.type = 'button';
  quickBtn.setAttribute('aria-label', item.status_code + ' ' + item.scenario + ' 맞춤 체크리스트 열기');
  quickBtn.addEventListener('click', function () {
    state.status_code = item.status_code;
    state.selected_item = item;
    state.scenario_id = item.id;
    setStep(4);
  });

  append(tail, [prov, quickBtn]);
  cardEl.appendChild(tail);
  return cardEl;
}

function filtered() {
  var data = getDataset();
  if (!data || !Array.isArray(data.items)) return [];
  var q = normalize(state.query);
  return q ? data.items.filter(function (i) {
    return normalize(meta(activeRow(i))).includes(q);
  }) : data.items;
}

function render() {
  var results = filtered();
  var target = $('cards');
  var dataset = getDataset();
  if (!dataset) return;

  target.setAttribute('aria-busy', 'true');
  var frag = document.createDocumentFragment();

  if (!results.length) {
    var empty = element('div', 'empty');
    append(empty, [
      element('strong', '', '결과를 찾지 못했어요.'),
      element('p', '', '체류자격 코드나 서류명을 짧게 입력하거나 검색을 초기화해 보세요.')
    ]);
    frag.appendChild(empty);
  } else {
    results.slice(0, state.limit).forEach(function (i) {
      frag.appendChild(card(i));
    });
  }

  target.replaceChildren(frag);
  target.setAttribute('aria-busy', 'false');

  $('count').textContent = results.length + '건의 상황별 항목' + (state.query ? ' 검색됨' : '') + (state.office ? ' · ' + officeName(state.office) + ' 선택 (검증된 지역 차이만 표시)' : '');
  var more = $('show-more');
  more.hidden = results.length <= state.limit;
  if (!more.hidden) {
    more.textContent = '더 보기 (' + (results.length - state.limit) + '건 남음) ↓';
  }

  $('export-drafts').hidden = !Object.keys(state.nationalDrafts).some(function (id) {
    return dataset.items.some(function (i) { return i.id === id; });
  });
  $('export-office-drafts').hidden = !Object.keys(state.officeDrafts).length;

  // Sync Guided Step 2 candidates if in guided mode
  if (state.step === 2) {
    renderStatusCandidates();
  }
}

function renderNotes() {
  var parent = $('common-notes');
  if (!parent) return;
  parent.replaceChildren();
  (state.notes && state.notes.proxy_principles || []).slice(0, 12).forEach(function (n) {
    append(parent, [element('dl', '', undefined)]);
    var dl = parent.lastElementChild;
    append(dl, [element('dt', '', n.topic), element('dd', '', n.guidance)]);
  });
}

/* ------------------------------------------------------------------------- */
/* GUIDED STEPPER & PROGRESSIVE DISCLOSURE                                   */
/* ------------------------------------------------------------------------- */
function setStep(stepNumber) {
  state.step = stepNumber;
  var items = document.querySelectorAll('.stepper-item');
  items.forEach(function (el) {
    var s = Number(el.getAttribute('data-step'));
    el.classList.toggle('active', s === stepNumber);
    el.classList.toggle('completed', s < stepNumber);
    var btn = el.querySelector('.stepper-btn');
    if (btn) btn.disabled = (s > stepNumber);
  });

  [1, 2, 3, 4].forEach(function (n) {
    var panel = $('guided-step-' + n);
    if (panel) {
      panel.hidden = (n !== stepNumber);
      panel.classList.toggle('active', n === stepNumber);
    }
  });

  if (stepNumber === 2) {
    renderGuidedStep2();
  } else if (stepNumber === 3) {
    renderGuidedStep3();
  } else if (stepNumber === 4) {
    renderGuidedStep4();
  }

  var container = $('guided-discovery');
  if (container) {
    window.scrollTo({ top: container.offsetTop - 20, behavior: 'smooth' });
  }
}

function renderGuidedStep2() {
  $('step-2-proc-badge').textContent = getProcedureTitle(state.procedure);
  $('change-target-notice').hidden = (state.procedure !== 'change');

  if (state.procedure === 'change') {
    $('step-2-title').textContent = '어떤 체류자격으로 변경하고자 하나요?';
    $('step-2-desc').textContent = '새로 부여받고자 하는 목표 체류자격을 선택해 주세요. 해당 자격의 변경 허가 기준 서류가 제공됩니다.';
  } else if (state.procedure === 'registration') {
    $('step-2-title').textContent = '등록 또는 거소신고할 체류자격을 선택하세요';
    $('step-2-desc').textContent = '여권의 사증(Visa)에 기재된 체류자격을 선택해 주세요.';
  } else {
    $('step-2-title').textContent = '현재 어떤 체류자격으로 머무르고 있나요?';
    $('step-2-desc').textContent = '소지하고 계신 외국인등록증이나 사증(Visa)의 체류자격을 선택해 주세요.';
  }

  renderStatusCandidates();
}

function renderStatusCandidates() {
  var dataset = getDataset();
  if (!dataset || !dataset.items) return;

  var grid = $('status-candidate-grid');
  grid.replaceChildren();

  var codesMap = new Map();
  dataset.items.forEach(function (item) {
    var code = item.status_code;
    if (!codesMap.has(code)) codesMap.set(code, []);
    codesMap.get(code).push(item);
  });

  var query = normalize($('status-picker-input').value);
  var matchingCodes = Array.from(codesMap.keys()).sort();

  if (query) {
    matchingCodes = matchingCodes.filter(function (code) {
      var info = getVisaInfo(code);
      var combined = normalize(code + ' ' + info.name + ' ' + info.en + ' ' + info.desc);
      return combined.includes(query);
    });
  }

  $('candidate-count').textContent = matchingCodes.length + '개 체류자격 선택 가능';

  if (!matchingCodes.length) {
    var empty = element('div', 'empty');
    append(empty, [
      element('strong', '', '일치하는 체류자격을 찾지 못했어요.'),
      element('p', '', '코드(예: D-2, E-7-1) 또는 명칭(예: 유학, 특정활동)으로 검색하거나 인기 체류자격을 눌러보세요.')
    ]);
    grid.appendChild(empty);
    return;
  }

  matchingCodes.forEach(function (code) {
    var info = getVisaInfo(code);
    var count = codesMap.get(code).length;

    var btn = element('button', 'candidate-item-btn');
    btn.type = 'button';
    btn.setAttribute('role', 'option');

    var codeCol = element('div', 'candidate-code-col');
    codeCol.appendChild(element('span', 'code-pill', code));

    var textCol = element('div', 'candidate-text-col');
    textCol.appendChild(element('h4', '', info.name));
    textCol.appendChild(element('p', '', info.desc + ' · ' + count + '개 세부 상황'));

    append(btn, [codeCol, textCol]);

    btn.addEventListener('click', function () {
      selectStatusCode(code, codesMap.get(code));
    });

    grid.appendChild(btn);
  });
}

function selectStatusCode(code, items) {
  state.status_code = code;
  $('step-3-code-pill').textContent = code;
  $('step-3-name-label').textContent = getVisaInfo(code).name;

  if (items.length === 1) {
    state.selected_item = activeRow(items[0]);
    state.scenario_id = items[0].id;
    setStep(4);
  } else {
    setStep(3);
  }
}

function renderGuidedStep3() {
  var dataset = getDataset();
  if (!dataset || !dataset.items) return;

  var grid = $('scenario-selection-grid');
  grid.replaceChildren();

  var matching = dataset.items.filter(function (i) {
    return i.status_code === state.status_code;
  });

  if (!matching.length) {
    matching = dataset.items.filter(function (i) {
      return i.status_code.startsWith(state.status_code);
    });
  }

  $('step-3-title').textContent = state.status_code + ' (' + getVisaInfo(state.status_code).name + ') 세부 상황 선택';

  matching.forEach(function (rawItem) {
    var item = activeRow(rawItem);
    var cardEl = element('button', 'scenario-choice-card');
    cardEl.type = 'button';
    cardEl.setAttribute('role', 'option');

    var radio = element('div', 'scenario-radio-circle');
    var body = element('div', 'scenario-card-body');
    body.appendChild(element('h4', '', item.scenario));

    var docsPreview = item.required_text ? '기본 서류: ' + item.required_text.slice(0, 95) + (item.required_text.length > 95 ? '...' : '') : '기본 서류 확인 필요';
    body.appendChild(element('p', '', docsPreview));

    var metaRow = element('div', 'scenario-meta-row');
    metaRow.appendChild(element('span', '', '원문 ' + item.source_line + '행 (' + (item.source_section || '공통') + ')'));
    body.appendChild(metaRow);

    append(cardEl, [radio, body]);

    cardEl.addEventListener('click', function () {
      state.selected_item = item;
      state.scenario_id = item.id;
      setStep(4);
    });

    grid.appendChild(cardEl);
  });
}

function renderGuidedStep4() {
  var item = state.selected_item;
  if (!item) return;

  $('summary-proc-tag').textContent = getProcedureTitle(state.procedure);
  $('summary-code-tag').textContent = item.status_code + ' ' + getVisaInfo(item.status_code).name;
  $('summary-scenario-title').textContent = item.scenario;
  $('summary-provenance').textContent = '2026.09 매뉴얼 편집본 ' + item.source_line + '행 (' + (item.source_section || '') + ')';
  $('summary-review-tag').textContent = item.review_state === 'COMPILED_NEEDS_REVIEW' ? '검토 필요' : item.review_state;

  $('checklist-office-select').value = state.office;

  renderBaselineChecklist(item);
  renderConditionalDocs(item);
  renderApplicationGuidance(item);
  renderOfficeDifferences(item);
}

function renderBaselineChecklist(item) {
  var container = $('baseline-docs-list');
  container.replaceChildren();

  var structured = parseRequiredDocsStructured(item.required_text, item);

  // 1. Legal restrictions or ineligibility
  if (structured.restrictions.length) {
    var resCard = element('div', 'restriction-card');
    var resHead = element('div', 'restriction-head');
    resHead.appendChild(element('span', 'restriction-icon', '⛔'));
    resHead.appendChild(element('h4', '', '신청 불가 또는 별도 절차 대상 안내'));
    resCard.appendChild(resHead);

    var resBody = element('div', 'restriction-body');
    structured.restrictions.forEach(function (r) {
      resBody.appendChild(element('p', '', r));
    });

    if (state.procedure === 'extension' && item.status_code.includes('F-5')) {
      resBody.appendChild(element('p', 'restriction-note', '※ 영주(F-5) 자격은 체류기간 제한이 없으므로 체류기간 연장허가 대상이 아닙니다. 10년 주기 영주증(등록증) 만료 시에는 관할 출입국관서에서 영주증 재발급·갱신을 신청해야 합니다.'));
    } else if (state.procedure === 'change') {
      resBody.appendChild(element('p', 'restriction-note', '※ 이 체류자격은 출입국관리법령상 국내에서 다른 자격으로(또는 다른 자격에서 이 자격으로) 변경허가를 신청할 수 없는 원칙이 적용됩니다. 출국 후 재외공관을 통한 신규 사증(Visa) 발급 대상입니다.'));
    }

    resCard.appendChild(resBody);
    container.appendChild(resCard);
  }

  // 2. Unlisted in manual
  if (structured.unlisted) {
    var unCard = element('div', 'unlisted-card');
    var unHead = element('div', 'unlisted-head');
    unHead.appendChild(element('span', 'unlisted-icon', 'ℹ️'));
    unHead.appendChild(element('h4', '', '원문 매뉴얼 상 독립 제출서류 목록 미기재'));
    unCard.appendChild(unHead);
    unCard.appendChild(element('p', '', structured.unlistedText || '2026년 9월 공식 매뉴얼에 독립된 제출서류 목록이 수록되어 있지 않습니다. 관할 출입국관서 또는 1345에 확인하세요.'));
    unCard.appendChild(element('p', 'muted', '출입국관리법령상 개별 심사관 판단에 따라 제출 서류가 정해지므로 방문 전 관할청에 문의하시기 바랍니다.'));
    container.appendChild(unCard);
  }

  // 3. Document items
  var docs = structured.items;
  if (!docs.length) {
    if (!structured.restrictions.length && !structured.unlisted) {
      container.appendChild(element('p', 'muted', '명시된 기본 제출 서류가 원문에 기재되지 않았습니다. 관할 출입국관서 또는 하이코리아에 서류 요건을 확인하세요.'));
    }
    updateProgressBar(0, 0, structured.restrictions.length > 0 ? '신청 제한 / 별도 절차 대상' : structured.unlisted ? '공식 서류 목록 개별 확인 필요' : '0 / 0개 준비 완료 (0%)');
    return;
  }

  var checkedSet = new Set(state.checked_docs[item.id] || []);
  var totalCount = docs.length;
  var checkedCount = 0;

  docs.forEach(function (docItem, idx) {
    var itemId = 'doc-chk-' + item.id + '-' + idx;
    var isChecked = checkedSet.has(docItem.label);
    if (isChecked) checkedCount++;

    var row = element('div', 'checklist-item' + (isChecked ? ' checked' : ''));
    var chkWrap = element('div', 'checklist-checkbox-wrap');

    var input = document.createElement('input');
    input.type = 'checkbox';
    input.id = itemId;
    input.checked = isChecked;
    input.setAttribute('aria-label', docItem.label + ' 준비 완료');
    chkWrap.appendChild(input);

    var textWrap = element('div', 'checklist-text-wrap');
    var label = document.createElement('label');
    label.htmlFor = itemId;
    label.className = 'checklist-doc-name';
    label.textContent = docItem.label;

    if (docItem.type === 'alternative') {
      var altBadge = element('span', 'item-badge alternative-badge', '택 1 제출 (대체 가능)');
      label.appendChild(altBadge);
    } else if (docItem.type === 'conditional') {
      var condBadge = element('span', 'item-badge conditional-badge-inline', '해당자 제출');
      label.appendChild(condBadge);
    }

    textWrap.appendChild(label);

    if (docItem.isFormHelper) {
      var link = document.createElement('a');
      link.href = 'form-helper.html';
      link.className = 'checklist-form-helper-link';
      link.target = '_blank';
      link.rel = 'noopener noreferrer';
      link.textContent = 'VISABLE 서식 도우미에서 바로 작성하기 ↗';
      textWrap.appendChild(link);
    }

    append(row, [chkWrap, textWrap]);

    input.addEventListener('change', function () {
      if (input.checked) {
        checkedSet.add(docItem.label);
        row.classList.add('checked');
      } else {
        checkedSet.delete(docItem.label);
        row.classList.remove('checked');
      }
      state.checked_docs[item.id] = Array.from(checkedSet);
      safeSave(C_KEY, state.checked_docs);
      updateProgressBar(checkedSet.size, totalCount);
    });

    container.appendChild(row);
  });

  updateProgressBar(checkedCount, totalCount);
}

function updateProgressBar(checked, total, customText) {
  var percent = total > 0 ? Math.round((checked / total) * 100) : 0;
  var fill = $('checklist-progress-fill');
  var track = $('checklist-progress-track');
  var label = $('progress-fraction');

  if (fill) fill.style.width = percent + '%';
  if (track) track.setAttribute('aria-valuenow', String(percent));
  if (label) {
    if (customText) {
      label.textContent = customText;
    } else {
      label.textContent = checked + ' / ' + total + '개 준비 완료 (' + percent + '%)';
    }
  }
}

function renderConditionalDocs(item) {
  var container = $('conditional-docs-content');
  container.replaceChildren();

  if (!item.conditional_text || item.conditional_text === '별도 기재 없음') {
    container.appendChild(element('p', 'muted', '이 세부 상황에는 별도로 명시된 조건부·대체 서류가 없습니다.'));
    return;
  }

  var cardEl = element('div', 'condition-card');
  cardEl.appendChild(element('h4', '', '해당 시 추가 제출 또는 생략 가능한 서류'));
  cardEl.appendChild(element('p', '', item.conditional_text));
  container.appendChild(cardEl);
}

function renderApplicationGuidance(item) {
  var container = $('application-docs-content');
  container.replaceChildren();

  var text = item.application_text;
  if (!text) {
    if (state.procedure === 'registration') {
      text = '신규 외국인등록 및 국내거소신고는 등록대상자의 연령(17세 이상)·생체정보(지문 및 얼굴) 등록 여부에 따라 본인 출석이 필요합니다. 대리 접수 가능 여부와 별개로 생체정보 제공 절차는 관할 청 방문이 필수입니다.';
    } else {
      text = '본인 또는 출입국관리법상 자격 있는 대리인(가족, 행정사 등)이 접수할 수 있습니다. 단, 개별 심사 및 본인 확인이 필요한 경우 출석을 요구받을 수 있습니다.';
    }
  }

  var cardEl = element('div', 'app-guidance-card');
  cardEl.appendChild(element('p', '', text));
  container.appendChild(cardEl);
}

function renderOfficeDifferences(item) {
  var container = $('office-docs-content');
  container.replaceChildren();

  if (!state.office) {
    var notice = element('div', 'office-transparent-notice');
    notice.appendChild(element('strong', '', '전국 기준 안내가 적용 중입니다.'));
    notice.appendChild(element('p', '', '방문 예정인 관할 출입국·외국인관서를 선택하시면 해당 관서에 대해 별도로 확인된 요구서류가 있는지 안내해 드립니다.'));
    container.appendChild(notice);
    $('office-status-badge').textContent = '전국 기준 안내';
    return;
  }

  var oName = officeName(state.office);
  var diffs = localNotes(item);

  if (diffs.length) {
    $('office-status-badge').textContent = oName + ' 추가 확인';
    diffs.forEach(function (entry) {
      container.appendChild(officeCallout(entry));
    });
  } else {
    $('office-status-badge').textContent = oName + ' 전국 기준 안내';
    var notice2 = element('div', 'office-transparent-notice');
    notice2.appendChild(element('strong', '', oName + ' 서류 안내'));
    notice2.appendChild(element('p', '', '이 관서에 대해 별도로 확인된 서류 차이가 아직 없습니다. 출입국관리법령상 관할 청장의 재량에 따라 추가 소명서류가 요구될 수 있으므로, 방문 전 관할청의 최신 공지를 확인해 주세요.'));
    container.appendChild(notice2);
  }
}

/* ------------------------------------------------------------------------- */
/* LOCAL DRAFT EXPORT & EDITOR                                               */
/* ------------------------------------------------------------------------- */
function exportFile(name, value) {
  var blob = new Blob([JSON.stringify(value, null, 2) + '\n'], { type: 'application/json;charset=utf-8' });
  var url = URL.createObjectURL(blob);
  var a = document.createElement('a');
  a.href = url;
  a.download = name;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(function () { URL.revokeObjectURL(url); }, 3000);
}

function exportNational() {
  var d = JSON.parse(JSON.stringify(getDataset()));
  var edited = 0;
  d.items.forEach(function (item) {
    var p = state.nationalDrafts[item.id];
    if (!p) return;
    FIELDS.forEach(function (k) {
      if (typeof p[k] === 'string') item[k] = p[k];
    });
    item.editor_note = p.editor_note || '';
    item.curation_review = 'DRAFT_NEEDS_HUMAN_VERIFICATION';
    edited++;
  });
  if (!edited) return;
  d.editor_export = {
    exported_at: new Date().toISOString(),
    changed_rows: edited,
    warning: '초안입니다. 원문 검증 및 GitHub 코드 리뷰 후 적용하세요.'
  };
  exportFile(state.procedure + '-202609.json', d);
}

function exportOffice() {
  var list = Object.keys(state.officeDrafts).sort().map(function (k) {
    var o = state.officeDrafts[k];
    return {
      id: o.id,
      office_id: o.office_id,
      item_id: o.item_id,
      procedure: o.procedure,
      review_state: 'DRAFT',
      changes: o.changes,
      evidence: o.evidence || [],
      editor_note: o.editor_note || '',
      edited_at: o.edited_at
    };
  });
  exportFile('local-overrides.draft.json', {
    schema_version: 1,
    policy: 'DRAFT entries are never rendered publicly. Verification and review state promotion required.',
    overrides: list
  });
}

function updateEditorDiff() {
  var diffBox = $('edit-diff-container');
  var diffContent = $('edit-diff-content');
  if (!diffBox || !diffContent) return;

  var item = state.selected_item;
  if (!item) {
    diffBox.hidden = true;
    return;
  }
  var row = activeRow(item);
  var form = $('edit-form');
  var changes = [];

  var fieldLabels = {
    required_text: '기본·명시 서류',
    conditional_text: '조건부·대체·생략',
    application_text: '본인·대리 신청 안내',
    note_text: '비고·근거'
  };

  FIELDS.forEach(function (k) {
    var originalVal = String(row[k] || '').trim();
    var fieldEl = form.elements.namedItem(k);
    var currentVal = String(fieldEl ? fieldEl.value : '').trim();
    if (originalVal !== currentVal) {
      changes.push({
        label: fieldLabels[k] || k,
        oldVal: originalVal || '(기존 비어있음)',
        newVal: currentVal || '(내용 삭제됨)'
      });
    }
  });

  if (!changes.length) {
    diffBox.hidden = true;
    diffContent.replaceChildren();
    return;
  }

  diffBox.hidden = false;
  diffContent.replaceChildren();
  changes.forEach(function (ch) {
    var rowEl = element('div', 'diff-row');
    rowEl.appendChild(element('span', 'diff-label', ch.label));
    rowEl.appendChild(element('span', 'diff-val diff-val-old', '- 원본: ' + ch.oldVal));
    rowEl.appendChild(element('span', 'diff-val diff-val-new', '+ 수정: ' + ch.newVal));
    diffContent.appendChild(rowEl);
  });
}

function openEditor(item) {
  state.selected_item = item;
  var row = activeRow(item);
  var dialog = $('edit-dialog');
  var form = $('edit-form');
  form.reset();

  $('edit-context').textContent = item.status_code + ' · ' + item.scenario + ' · ' + item.id;
  $('edit-scope').value = 'national';
  FIELDS.forEach(function (k) {
    form.elements.namedItem(k).value = row[k] || '';
  });
  form.elements.namedItem('editor_note').value = (state.nationalDrafts[item.id] || {}).editor_note || '';
  toggleScope();
  updateEditorDiff();

  if (typeof dialog.showModal === 'function') dialog.showModal();
  else dialog.setAttribute('open', '');
}

function toggleScope() {
  var national = $('edit-scope').value === 'national';
  var item = state.selected_item;
  var form = $('edit-form');
  $('edit-office-wrap').hidden = national;
  $('edit-evidence-wrap').hidden = national;

  if (national) {
    var row = activeRow(item);
    FIELDS.forEach(function (k) { form.elements.namedItem(k).value = row[k] || ''; });
    form.elements.namedItem('editor_note').value = (state.nationalDrafts[item.id] || {}).editor_note || '';
  } else {
    if (state.office) $('edit-office').value = state.office;
    var patch = state.officeDrafts[item.id + '@' + $('edit-office').value] || null;
    FIELDS.forEach(function (k) { form.elements.namedItem(k).value = patch && patch.changes[k] || ''; });
    form.elements.namedItem('editor_note').value = patch && patch.editor_note || '';
    $('edit-evidence').value = patch && patch.evidence?.[0]?.url || '';
  }
  updateEditorDiff();
}

function saveDraft(e) {
  e.preventDefault();
  var item = state.selected_item;
  if (!item) return;
  var form = $('edit-form');
  var values = {};
  FIELDS.forEach(function (k) {
    values[k] = String(form.elements.namedItem(k).value || '').trim();
  });
  var noteText = String(form.elements.namedItem('editor_note').value || '').trim();
  if (!noteText) {
    window.alert('수정 근거·검토 메모가 필요합니다.');
    return;
  }
  var now = new Date().toISOString();

  if ($('edit-scope').value === 'national') {
    if (!values.required_text) {
      window.alert('기본·명시 서류는 빈 값으로 저장하지 않습니다.');
      return;
    }
    state.nationalDrafts[item.id] = Object.assign(values, { editor_note: noteText, edited_at: now });
    safeSave(N_KEY, state.nationalDrafts);
  } else {
    var office = $('edit-office').value;
    if (!office) {
      window.alert('관할 출입국관서를 선택해 주세요.');
      return;
    }
    var key = item.id + '@' + office;
    var ev = $('edit-evidence').value.trim();
    if (ev && !/^https:\/\//i.test(ev)) {
      window.alert('근거 주소는 HTTPS 링크를 입력해 주세요.');
      return;
    }
    state.officeDrafts[key] = {
      id: 'draft-' + item.id + '-' + office,
      office_id: office,
      item_id: item.id,
      procedure: state.procedure,
      review_state: 'DRAFT',
      changes: values,
      evidence: ev ? [{ type: 'office_notice_candidate', url: ev }] : [],
      editor_note: noteText,
      edited_at: now
    };
    safeSave(O_KEY, state.officeDrafts);
  }

  if (typeof $('edit-dialog').close === 'function') $('edit-dialog').close();
  else $('edit-dialog').removeAttribute('open');

  render();
  if (state.step === 4 && state.selected_item) {
    renderGuidedStep4();
  }
}

function validateData(data, type) {
  if (!data || data.procedure !== type || !Array.isArray(data.items)) {
    throw Error(type + ' 데이터 구조를 확인할 수 없습니다.');
  }
  var seen = new Set();
  for (var item of data.items) {
    if (!item.id || !item.status_code || seen.has(item.id)) {
      throw Error(type + ' 데이터 ID 중복 또는 누락');
    }
    seen.add(item.id);
  }
  var count = { extension: 224, change: 251, registration: 172 }[type];
  if (data.items.length !== count) {
    throw Error(type + ' 행 수 불일치: ' + data.items.length);
  }
}

/* ------------------------------------------------------------------------- */
/* INITIALIZATION & EVENT LISTENERS                                          */
/* ------------------------------------------------------------------------- */
async function load() {
  try {
    var files = ['extension-202609.json', 'change-202609.json', 'registration-202609.json', 'reference-notes-202609.json', 'local-overrides.json'];
    var urls = files.map(function (f) { return base + f; });
    urls.push('data/local-practice-202609.json');

    var response = await Promise.all(urls.map(function (u) {
      return fetch(u, { cache: 'no-cache' }).then(function (r) {
        if (!r.ok) throw Error('HTTP ' + r.status + ': ' + u);
        return r.json();
      });
    }));

    ['extension', 'change', 'registration'].forEach(function (t, i) {
      validateData(response[i], t);
      state.datasets[t] = response[i];
    });

    state.notes = response[3];
    state.overrides = Array.isArray(response[4].overrides) ? response[4].overrides : [];
    state.offices = Array.isArray(response[5].offices) ? response[5].offices : [];

    var officeSelect = $('office');
    var editorOffice = $('edit-office');
    var checkOffice = $('checklist-office-select');

    state.offices.forEach(function (o) {
      [officeSelect, editorOffice, checkOffice].forEach(function (select) {
        if (!select) return;
        var opt = document.createElement('option');
        opt.value = o.id;
        opt.textContent = o.name_ko;
        select.appendChild(opt);
      });
    });

    state.nationalDrafts = safeRead(N_KEY);
    state.officeDrafts = safeRead(O_KEY);
    state.checked_docs = safeRead(C_KEY);

    renderNotes();
    render();
    renderGuidedStep2();

    // Check URL parameters
    handleUrlParams();
  } catch (err) {
    var cards = $('cards');
    if (cards) {
      cards.replaceChildren();
      var div = element('div', 'empty');
      append(div, [
        element('strong', '', '서류 데이터를 가져오지 못했어요.'),
        element('p', '', err.message),
        element('p', '', '연결을 확인하고 페이지를 새로고침해 주세요.')
      ]);
      cards.appendChild(div);
      cards.setAttribute('aria-busy', 'false');
    }
    if ($('count')) $('count').textContent = '불러오기 실패';
  }
}

function handleUrlParams() {
  var params = new URLSearchParams(window.location.search);
  var proc = params.get('procedure') || params.get('proc');
  var code = params.get('code') || params.get('status');
  var scenarioId = params.get('scenario');
  var office = params.get('office');

  if (proc && ['extension', 'change', 'registration'].includes(proc)) {
    state.procedure = proc;
    var radio = document.querySelector('[name="procedure"][value="' + proc + '"]');
    if (radio) radio.checked = true;
  }
  if (office) {
    state.office = office;
    if ($('office')) $('office').value = office;
    if ($('checklist-office-select')) $('checklist-office-select').value = office;
  }
  if (code) {
    state.status_code = code;
  }
  if (scenarioId && state.datasets[state.procedure]) {
    var found = state.datasets[state.procedure].items.find(function (i) { return i.id === scenarioId; });
    if (found) {
      state.selected_item = activeRow(found);
      state.scenario_id = found.id;
      state.status_code = found.status_code;
      setStep(4);
    }
  }

  if (window.location.hash === '#operator') {
    toggleOperatorMode(true);
  }
}

function toggleOperatorMode(forceState) {
  state.operator_mode = (forceState !== undefined) ? forceState : !state.operator_mode;
  document.body.setAttribute('data-operator', String(state.operator_mode));
  var pill = $('operator-mode-toggle');
  if (pill) pill.setAttribute('aria-pressed', String(state.operator_mode));
  var banner = $('operator-banner');
  if (banner) banner.hidden = !state.operator_mode;
}

// Stepper buttons
[1, 2, 3, 4].forEach(function (n) {
  var btn = $('stepper-btn-' + n);
  if (btn) {
    btn.addEventListener('click', function () {
      if (n <= state.step) setStep(n);
    });
  }
});

// Step 1: Task Selection Cards
document.querySelectorAll('.task-card').forEach(function (cardEl) {
  cardEl.addEventListener('click', function () {
    var proc = cardEl.getAttribute('data-procedure');
    state.procedure = proc;
    var radio = document.querySelector('[name="procedure"][value="' + proc + '"]');
    if (radio) radio.checked = true;
    render();
    setStep(2);
  });
});

// Task Help Modal
$('task-help-btn').addEventListener('click', function () {
  var d = $('task-help-dialog');
  if (typeof d.showModal === 'function') d.showModal();
  else d.setAttribute('open', '');
});
$('task-help-close').addEventListener('click', function () {
  var d = $('task-help-dialog');
  if (typeof d.close === 'function') d.close();
  else d.removeAttribute('open');
});

// Step 2: Back button
$('step-2-back').addEventListener('click', function () { setStep(1); });

// Step 2: Sub-tabs
$('subtab-know').addEventListener('click', function () {
  $('subtab-know').classList.add('active');
  $('subtab-know').setAttribute('aria-selected', 'true');
  $('subtab-dont-know').classList.remove('active');
  $('subtab-dont-know').setAttribute('aria-selected', 'false');
  $('subtab-panel-know').hidden = false;
  $('subtab-panel-dont-know').hidden = true;
});
$('subtab-dont-know').addEventListener('click', function () {
  $('subtab-dont-know').classList.add('active');
  $('subtab-dont-know').setAttribute('aria-selected', 'true');
  $('subtab-know').classList.remove('active');
  $('subtab-know').setAttribute('aria-selected', 'false');
  $('subtab-panel-dont-know').hidden = false;
  $('subtab-panel-know').hidden = true;
});
$('switch-to-picker-btn').addEventListener('click', function () {
  $('subtab-know').click();
  $('status-picker-input').focus();
});

// Step 2: Status Picker Search Input
$('status-picker-input').addEventListener('input', renderStatusCandidates);

// Step 2: Popular Chips
document.querySelectorAll('.popular-chip').forEach(function (btn) {
  btn.addEventListener('click', function () {
    var code = btn.getAttribute('data-code');
    $('status-picker-input').value = code;
    renderStatusCandidates();
  });
});

// Step 3: Back button
$('step-3-back').addEventListener('click', function () { setStep(2); });

// Step 4: Back button & Reset
$('step-4-back').addEventListener('click', function () { setStep(3); });
$('guided-reset-btn').addEventListener('click', function () {
  state.status_code = '';
  state.scenario_id = '';
  state.selected_item = null;
  setStep(1);
});

// Step 4: Checklist Office Select
$('checklist-office-select').addEventListener('change', function (e) {
  state.office = e.target.value;
  $('office').value = e.target.value;
  renderOfficeDifferences(state.selected_item);
  render();
});

// Step 4: Action Buttons (Print, Copy Link, Clear Checks)
$('checklist-print-btn').addEventListener('click', function () {
  window.print();
});
$('checklist-copy-link-btn').addEventListener('click', function () {
  var url = new URL(window.location.href);
  url.searchParams.set('procedure', state.procedure);
  url.searchParams.set('code', state.status_code);
  if (state.scenario_id) url.searchParams.set('scenario', state.scenario_id);
  if (state.office) url.searchParams.set('office', state.office);
  navigator.clipboard.writeText(url.toString()).then(function () {
    window.alert('맞춤 서류 체크리스트 링크가 복사되었습니다!');
  }).catch(function () {
    window.prompt('이 링크를 복사하세요:', url.toString());
  });
});
$('checklist-clear-checks-btn').addEventListener('click', function () {
  if (state.selected_item) {
    state.checked_docs[state.selected_item.id] = [];
    safeSave(C_KEY, state.checked_docs);
    renderBaselineChecklist(state.selected_item);
  }
});

// Operator Mode Toggle
$('operator-mode-toggle').addEventListener('click', function () {
  toggleOperatorMode();
});

// Legacy direct filters
document.querySelectorAll('[name="procedure"]').forEach(function (input) {
  input.addEventListener('change', function () {
    if (!input.checked) return;
    state.procedure = input.value;
    state.limit = 30;
    render();
    if (state.step > 1) {
      state.status_code = '';
      state.scenario_id = '';
      state.selected_item = null;
      setStep(1);
    }
  });
});

$('query').addEventListener('input', function (e) {
  state.query = e.target.value;
  state.limit = 30;
  render();
});

$('office').addEventListener('change', function (e) {
  state.office = e.target.value;
  state.limit = 30;
  if ($('checklist-office-select')) $('checklist-office-select').value = e.target.value;
  render();
  if (state.step === 4 && state.selected_item) {
    renderOfficeDifferences(state.selected_item);
  }
});

$('reset').addEventListener('click', function () {
  state.query = '';
  state.office = '';
  state.procedure = 'extension';
  state.limit = 30;
  $('query').value = '';
  $('office').value = '';
  if ($('checklist-office-select')) $('checklist-office-select').value = '';
  var rad = document.querySelector('[name="procedure"][value="extension"]');
  if (rad) rad.checked = true;
  render();
  $('query').focus();
});

$('show-more').addEventListener('click', function () {
  state.limit += 30;
  render();
});

$('draft-toggle').addEventListener('click', function () {
  var p = $('draft-info');
  p.hidden = !p.hidden;
  this.setAttribute('aria-expanded', String(!p.hidden));
  if (!p.hidden) p.scrollIntoView({ block: 'nearest' });
});

$('edit-scope').addEventListener('change', toggleScope);
$('edit-office').addEventListener('change', toggleScope);
$('edit-form').addEventListener('input', updateEditorDiff);
$('edit-cancel').addEventListener('click', function () {
  if (typeof $('edit-dialog').close === 'function') $('edit-dialog').close();
  else $('edit-dialog').removeAttribute('open');
});
$('edit-form').addEventListener('submit', saveDraft);
$('export-drafts').addEventListener('click', exportNational);
$('export-office-drafts').addEventListener('click', exportOffice);

// Language select
$('lang-select').addEventListener('change', function (e) {
  state.lang = e.target.value;
  if (state.lang === 'en') {
    $('hero-copy').textContent = 'Find necessary documents by selecting your visa status and application procedure. Even with the same status, required documents vary by individual scenario.';
    $('page-title').innerHTML = 'Immigration Documents,<br><span>Simplified and Reliable.</span>';
  } else {
    $('hero-copy').textContent = '체류자격과 신청 업무를 선택하면 필요한 준비사항을 확인할 수 있어요. 같은 자격이어도 신청 상황에 따라 서류가 달라질 수 있습니다.';
    $('page-title').innerHTML = '내 상황에 맞는 서류,<br><span>필요한 것부터 쉽고 확실하게.</span>';
  }
});

window.__VISABLE_INTERNALS = {
  splitParenSafe: splitParenSafe,
  parseRequiredDocsStructured: parseRequiredDocsStructured,
  getVisaInfo: getVisaInfo
};

load();
})();
