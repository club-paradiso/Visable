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

function getProcedureTitle(proc, optLang) {
  var lang = optLang || state.lang || (window.VisableI18n ? window.VisableI18n.getLocale() : 'ko');
  if (window.VisableI18n && window.VisableI18n.getProcedureName) {
    return window.VisableI18n.getProcedureName(proc, lang);
  }
  if (proc === 'extension') return '체류기간 연장';
  if (proc === 'change') return '체류자격 변경';
  if (proc === 'registration') return '외국인등록·국내거소신고';
  return proc;
}

function getVisaInfo(rawCode, optLang) {
  var lang = optLang || state.lang || (window.VisableI18n ? window.VisableI18n.getLocale() : 'ko');
  if (!rawCode) {
    return { name: '알 수 없음', en: 'Unknown', desc: '체류자격 정보', name_ko: '알 수 없음', localized_name: 'Unknown' };
  }
  var clean = String(rawCode).trim();
  var code = clean.split(' ')[0].split('·')[0].split('(')[0].trim();

  var rawEntry = VISA_DESCRIPTIONS[clean] || VISA_DESCRIPTIONS[code];
  if (!rawEntry) {
    var parts = code.split('-');
    if (parts.length >= 3) {
      rawEntry = VISA_DESCRIPTIONS[parts.slice(0, 3).join('-')] || VISA_DESCRIPTIONS[parts.slice(0, 2).join('-')];
    } else if (parts.length === 2) {
      rawEntry = VISA_DESCRIPTIONS[parts[0]];
    }
  }

  if (!rawEntry) {
    return {
      code: code,
      name: code,
      name_ko: code,
      en: code,
      localized_name: code,
      desc: (lang === 'en' ? 'Visa status ' : lang === 'zh-CN' ? '滞留资格 ' : lang === 'vi' ? 'Tư cách lưu trú ' : lang === 'id' ? 'Status visa ' : '체류자격 ') + code
    };
  }

  var nameKo = rawEntry.name;
  var nameEn = rawEntry.en || rawEntry.name;
  var localizedName = nameKo;
  var desc = rawEntry.desc;

  if (lang === 'en') {
    localizedName = nameEn;
    desc = rawEntry.desc_en || rawEntry.desc;
  } else if (lang === 'zh-CN') {
    localizedName = rawEntry['zh-CN'] || nameEn;
    desc = rawEntry.desc_zh || rawEntry.desc_en || rawEntry.desc;
  } else if (lang === 'zh-TW') {
    var zhName = rawEntry['zh-CN'] || nameEn;
    localizedName = (window.ParadisoZhT && window.ParadisoZhT.convert) ? window.ParadisoZhT.convert(zhName) : zhName;
    var zhDesc = rawEntry.desc_zh || rawEntry.desc_en || rawEntry.desc;
    desc = (window.ParadisoZhT && window.ParadisoZhT.convert) ? window.ParadisoZhT.convert(zhDesc) : zhDesc;
  } else if (lang === 'vi') {
    localizedName = rawEntry.vi || nameEn;
    desc = rawEntry.desc_vi || rawEntry.desc_en || rawEntry.desc;
  } else if (lang === 'id') {
    localizedName = rawEntry.id || nameEn;
    desc = rawEntry.desc_id || rawEntry.desc_en || rawEntry.desc;
  } else if (lang === 'ja') {
    localizedName = rawEntry.ja || rawEntry['zh-CN'] || nameEn;
    desc = rawEntry.desc_ja || rawEntry.desc_en || rawEntry.desc;
  } else if (lang === 'tl') {
    localizedName = rawEntry.tl || nameEn;
    desc = rawEntry.desc_tl || rawEntry.desc_en || rawEntry.desc;
  } else if (lang === 'ru') {
    localizedName = rawEntry.ru || nameEn;
    desc = rawEntry.desc_ru || rawEntry.desc_en || rawEntry.desc;
  } else if (lang === 'ar') {
    localizedName = rawEntry.ar || nameEn;
    desc = rawEntry.desc_ar || rawEntry.desc_en || rawEntry.desc;
  }

  return {
    code: code,
    name: (lang === 'ko' || !localizedName || localizedName === nameKo) ? nameKo : (nameKo + ' (' + localizedName + ')'),
    name_ko: nameKo,
    en: nameEn,
    localized_name: localizedName,
    desc: desc
  };
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

function getNoteTitle(key) {
  var lang = state.lang || 'ko';
  var map = {
    required: { ko: '기본·명시 서류', en: 'Mandatory Baseline Documents', 'zh-CN': '基本必备材料', 'zh-TW': '基本必備材料', vi: 'Hồ sơ cơ bản bắt buộc', id: 'Dokumen Dasar Wajib' },
    conditional: { ko: '해당자·대체·생략 조건', en: 'Conditional / Alternative Requirements', 'zh-CN': '条件·替代·免除要求', 'zh-TW': '條件·替代·免除要求', vi: 'Hồ sơ có điều kiện / thay thế', id: 'Dokumen Bersyarat & Alternatif' },
    application: { ko: '본인·대리 신청', en: 'In-Person / Proxy Rules', 'zh-CN': '本人·代办申请须知', 'zh-TW': '本人·代辦申請須知', vi: 'Quy định có mặt / nộp thay', id: 'Ketentuan Kehadiran / Kuasa' },
    notes: { ko: '비고 및 원문 주의', en: 'Notes & Official Remarks', 'zh-CN': '备注与特别说明', 'zh-TW': '備註與特別說明', vi: 'Ghi chú & lưu ý chính thức', id: 'Catatan & Keterangan Resmi' }
  };
  return (map[key] && (map[key][lang] || map[key].en)) || map[key].ko;
}

/* ------------------------------------------------------------------------- */
/* CARD RENDERING (Results Section in Direct Search)                         */
/* ------------------------------------------------------------------------- */
function card(original) {
  var item = activeRow(original);
  var cardEl = element('article', 'doc-card');
  var lang = state.lang || 'ko';

  var head = element('div', 'card-head');
  var left = element('div');
  var code = element('span', 'code-pill', item.status_code);
  append(left, [code, element('h3', '', item.scenario)]);

  var right = element('div', 'card-head-actions');
  var chipText = state.nationalDrafts[item.id]
    ? (lang === 'en' ? 'Local Draft' : lang === 'zh-CN' ? '本地草案' : '로컬 문구 초안')
    : (lang === 'en' ? 'Source Edition' : lang === 'zh-CN' ? '官方汇编版' : '원문 편집본');
  append(right, [element('span', 'chip', chipText)]);

  // Maintainer button: Accessible name contains "문구 편집" for E2E tests and maintainers
  var btn = element('button', 'outline-button', lang === 'en' ? 'Edit Copy' : '워딩 수정');
  btn.type = 'button';
  btn.setAttribute('aria-label', item.status_code + ' ' + item.scenario + ' 문구 편집');
  btn.addEventListener('click', function () { openEditor(original); });
  right.appendChild(btn);

  append(head, [left, right]);
  cardEl.appendChild(head);

  var body = element('div', 'card-body');
  note(body, getNoteTitle('required'), item.required_text);
  note(body, getNoteTitle('conditional'), item.conditional_text, 'conditional');
  var defaultAppText = state.procedure === 'registration'
    ? (lang === 'en'
      ? 'First-time Alien Registration and Residence Reporting require personal attendance for biometric registration. Verify in-person requirements separately.'
      : '신규 외국인등록 및 국내거소신고는 등록대상자의 연령·생체정보 등록 여부에 따라 본인 출석이 필요할 수 있습니다. 대리 접수 가능 여부와 생체정보 제공 절차는 별도로 확인해야 합니다.')
    : '';
  note(body, getNoteTitle('application'), item.application_text || defaultAppText);
  note(body, getNoteTitle('notes'), item.note_text);
  cardEl.appendChild(body);

  if (state.office) {
    localNotes(item).forEach(function (o) { cardEl.appendChild(officeCallout(o)); });
  }

  var tail = element('div', 'card-tail');
  var prov = element('div', 'card-provenance');
  var provLine = (lang === 'en') ? ('Source Edition Line ' + item.source_line) : ('원문 편집본 ' + item.source_line + '행');
  var provReview = (lang === 'en') ? 'Needs Verification' : '검토 필요';
  append(prov, [
    element('span', '', provLine),
    element('span', '', '·'),
    element('span', '', item.source_section || ''),
    element('span', '', '·'),
    element('span', '', provReview)
  ]);

  var quickBtnText = (window.VisableI18n && window.VisableI18n.t)
    ? window.VisableI18n.t('quickOpenChecklistBtn', null, '맞춤 체크리스트로 열기 →')
    : '맞춤 체크리스트로 열기 →';
  var quickBtn = element('button', 'card-quick-cta', quickBtnText);
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
  if (!q) return data.items;
  return data.items.filter(function (i) {
    var rawEntry = VISA_DESCRIPTIONS[i.status_code] || {};
    var extra = ' ' + (rawEntry.en || '') + ' ' + (rawEntry['zh-CN'] || '') + ' ' + (rawEntry.vi || '') + ' ' + (rawEntry.id || '');
    return normalize(meta(activeRow(i)) + extra).includes(q);
  });
}

function render() {
  var results = filtered();
  var target = $('cards');
  var dataset = getDataset();
  if (!dataset) return;
  var lang = state.lang || 'ko';

  target.setAttribute('aria-busy', 'true');
  var frag = document.createDocumentFragment();

  if (!results.length) {
    var empty = element('div', 'empty');
    var emptyTitle = lang === 'en' ? 'No results found.' : lang === 'zh-CN' ? '未找到相关结果。' : lang === 'vi' ? 'Không tìm thấy kết quả.' : lang === 'id' ? 'Tidak ada hasil yang ditemukan.' : '결과를 찾지 못했어요.';
    var emptyDesc = lang === 'en' ? 'Try shortening your keyword (e.g. D-2, student) or clear filters.' : lang === 'zh-CN' ? '请尝试输入简短的签证代码或材料名称，或重置搜索条件。' : lang === 'vi' ? 'Hãy thử rút ngắn từ khóa (VD: D-2) hoặc đặt lại bộ lọc.' : lang === 'id' ? 'Coba perpendek kata kunci atau setel ulang filter.' : '체류자격 코드나 서류명을 짧게 입력하거나 검색을 초기화해 보세요.';
    append(empty, [
      element('strong', '', emptyTitle),
      element('p', '', emptyDesc)
    ]);
    frag.appendChild(empty);
  } else {
    results.slice(0, state.limit).forEach(function (i) {
      frag.appendChild(card(i));
    });
  }

  target.replaceChildren(frag);
  target.setAttribute('aria-busy', 'false');

  if (lang === 'en') {
    $('count').textContent = results.length + ' scenario items' + (state.query ? ' found' : '') + (state.office ? ' · ' + officeName(state.office) + ' selected (local variances only)' : '');
  } else if (lang === 'zh-CN') {
    $('count').textContent = results.length + '项情形' + (state.query ? ' 已检索到' : '') + (state.office ? ' · 已选 ' + officeName(state.office) : '');
  } else if (lang === 'vi') {
    $('count').textContent = results.length + ' trường hợp' + (state.query ? ' tìm thấy' : '') + (state.office ? ' · Đã chọn ' + officeName(state.office) : '');
  } else if (lang === 'id') {
    $('count').textContent = results.length + ' skenario' + (state.query ? ' ditemukan' : '') + (state.office ? ' · Dipilih ' + officeName(state.office) : '');
  } else {
    $('count').textContent = results.length + '건의 상황별 항목' + (state.query ? ' 검색됨' : '') + (state.office ? ' · ' + officeName(state.office) + ' 선택 (검증된 지역 차이만 표시)' : '');
  }

  var more = $('show-more');
  more.hidden = results.length <= state.limit;
  if (!more.hidden) {
    var remaining = results.length - state.limit;
    more.textContent = lang === 'en' ? ('Show more (' + remaining + ' remaining) ↓') : ('더 보기 (' + remaining + '건 남음) ↓');
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
  $('step-2-proc-badge').textContent = getProcedureTitle(state.procedure, state.lang);
  var changeNotice = $('change-target-notice');
  if (changeNotice) {
    changeNotice.hidden = (state.procedure !== 'change');
    var strong = changeNotice.querySelector('strong');
    if (strong) strong.textContent = (window.VisableI18n && window.VisableI18n.t) ? window.VisableI18n.t('changeNoticeTitle', null, '체류자격 변경 안내') : '체류자격 변경 안내';
  }

  var t = function (k, vars, fallback) {
    return (window.VisableI18n && window.VisableI18n.t) ? window.VisableI18n.t(k, vars, fallback) : (fallback || k);
  };

  if (state.procedure === 'change') {
    $('step-2-title').textContent = t('step2TitleTarget', null, '어떤 체류자격으로 변경하고자 하나요?');
    $('step-2-desc').textContent = (state.lang === 'en')
      ? 'Select the new visa status you wish to obtain. Document requirements are provided based on the target status.'
      : (state.lang === 'zh-CN')
      ? '请选择希望取得的目标签证资格。将依据目标资格的许可标准提供材料清单。'
      : (state.lang === 'vi')
      ? 'Vui lòng chọn tư cách cư trú mục tiêu bạn muốn chuyển sang. Hồ sơ sẽ được hướng dẫn theo chuẩn tư cách mới.'
      : (state.lang === 'id')
      ? 'Pilih status visa baru yang ingin Anda peroleh. Dokumen disediakan berdasarkan status target tersebut.'
      : '새로 부여받고자 하는 목표 체류자격을 선택해 주세요. 해당 자격의 변경 허가 기준 서류가 제공됩니다.';
  } else if (state.procedure === 'registration') {
    $('step-2-title').textContent = t('step2TitleRegister', null, '등록 또는 거소신고할 체류자격을 선택하세요');
    $('step-2-desc').textContent = (state.lang === 'en')
      ? 'Select the visa status indicated in your passport visa.'
      : (state.lang === 'zh-CN')
      ? '请选择护照签证页(Visa)上记载的滞留资格。'
      : (state.lang === 'vi')
      ? 'Vui lòng chọn tư cách cư trú được ghi trên thị thực (Visa) trong hộ chiếu của bạn.'
      : (state.lang === 'id')
      ? 'Pilih status tinggal yang tertera pada visa di paspor Anda.'
      : '여권의 사증(Visa)에 기재된 체류자격을 선택해 주세요.';
  } else {
    $('step-2-title').textContent = t('step2TitleCurrent', null, '현재 어떤 체류자격으로 머무르고 있나요?');
    $('step-2-desc').textContent = (state.lang === 'en')
      ? 'Select the visa status indicated on your Alien Registration Card or passport visa.'
      : (state.lang === 'zh-CN')
      ? '请选择您所持有的外国人登录证或签证(Visa)上的滞留资格。'
      : (state.lang === 'vi')
      ? 'Vui lòng chọn tư cách cư trú được ghi trên thẻ người nước ngoài hoặc thị thực (Visa) của bạn.'
      : (state.lang === 'id')
      ? 'Pilih status visa yang tertera pada Kartu Registrasi Orang Asing atau visa paspor Anda.'
      : '소지하고 계신 외국인등록증이나 사증(Visa)의 체류자격을 선택해 주세요.';
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
      var rawEntry = VISA_DESCRIPTIONS[code] || {};
      var info = getVisaInfo(code, state.lang);
      var combined = normalize(code + ' ' + info.name + ' ' + (info.name_ko || '') + ' ' + info.en + ' ' + (rawEntry['zh-CN'] || '') + ' ' + (rawEntry.vi || '') + ' ' + (rawEntry.id || '') + ' ' + (rawEntry.ja || '') + ' ' + info.desc);
      return combined.includes(query);
    });
  }

  var t = function (k, vars, fallback) {
    return (window.VisableI18n && window.VisableI18n.t) ? window.VisableI18n.t(k, vars, fallback) : (fallback || k);
  };

  $('candidate-count').textContent = t('candidateCountLabel', { count: matchingCodes.length }, matchingCodes.length + '개 체류자격 선택 가능');

  if (!matchingCodes.length) {
    var empty = element('div', 'empty');
    append(empty, [
      element('strong', '', t('candidateEmptyTitle', null, '일치하는 체류자격을 찾지 못했어요.')),
      element('p', '', t('candidateEmptyDesc', null, '코드(예: D-2, E-7-1) 또는 명칭(예: 유학, 특정활동)으로 검색하거나 인기 체류자격을 눌러보세요.'))
    ]);
    grid.appendChild(empty);
    return;
  }

  var scenarioSuffix = (state.lang === 'en')
    ? ' scenarios'
    : (state.lang === 'zh-CN')
    ? '个细分情形'
    : (state.lang === 'vi')
    ? ' trường hợp'
    : (state.lang === 'id')
    ? ' skenario'
    : '개 세부 상황';

  matchingCodes.forEach(function (code) {
    var info = getVisaInfo(code, state.lang);
    var count = codesMap.get(code).length;

    var btn = element('button', 'candidate-item-btn');
    btn.type = 'button';
    btn.setAttribute('role', 'option');

    var codeCol = element('div', 'candidate-code-col');
    codeCol.appendChild(element('span', 'code-pill', code));

    var textCol = element('div', 'candidate-text-col');
    textCol.appendChild(element('h4', '', info.name));
    textCol.appendChild(element('p', '', info.desc + ' · ' + count + scenarioSuffix));

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
  var info = getVisaInfo(code, state.lang);
  $('step-3-name-label').textContent = info.name;

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

  var info = getVisaInfo(state.status_code, state.lang);
  var t = function (k, vars, fallback) {
    return (window.VisableI18n && window.VisableI18n.t) ? window.VisableI18n.t(k, vars, fallback) : (fallback || k);
  };
  $('step-3-title').textContent = t('step3TitlePattern', { code: state.status_code, name: info.name_ko }, state.status_code + ' (' + info.name + ') 세부 상황 선택');

  matching.forEach(function (rawItem) {
    var item = activeRow(rawItem);
    var cardEl = element('button', 'scenario-choice-card');
    cardEl.type = 'button';
    cardEl.setAttribute('role', 'option');

    var radio = element('div', 'scenario-radio-circle');
    var body = element('div', 'scenario-card-body');
    body.appendChild(element('h4', '', item.scenario));

    var basicLabel = t('basicDocsPreviewLabel', null, '기본 서류: ');
    var docsPreview = item.required_text
      ? (basicLabel + item.required_text.slice(0, 95) + (item.required_text.length > 95 ? '...' : ''))
      : (state.lang === 'en' ? 'Basic documents check needed' : '기본 서류 확인 필요');
    body.appendChild(element('p', '', docsPreview));

    var metaRow = element('div', 'scenario-meta-row');
    var lineLabel = (state.lang === 'en')
      ? ('Manual line ' + item.source_line + ' (' + (item.source_section || 'General') + ')')
      : ('원문 ' + item.source_line + '행 (' + (item.source_section || '공통') + ')');
    metaRow.appendChild(element('span', '', lineLabel));
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

  var info = getVisaInfo(item.status_code, state.lang);
  $('summary-proc-tag').textContent = getProcedureTitle(state.procedure, state.lang);
  $('summary-code-tag').textContent = item.status_code + ' ' + info.name_ko;
  $('summary-scenario-title').textContent = item.scenario;
  $('summary-provenance').textContent = (state.lang === 'en')
    ? ('2026.09 Official Manual Line ' + item.source_line + ' (' + (item.source_section || 'General') + ')')
    : ('2026.09 매뉴얼 편집본 ' + item.source_line + '행 (' + (item.source_section || '') + ')');
  $('summary-review-tag').textContent = item.review_state === 'COMPILED_NEEDS_REVIEW' ? (state.lang === 'en' ? 'Needs Verification' : '검토 필요') : item.review_state;

  $('checklist-office-select').value = state.office;

  renderBaselineChecklist(item);
  renderConditionalDocs(item);
  renderApplicationGuidance(item);
  renderOfficeDifferences(item);
}

function renderBaselineChecklist(item) {
  var container = $('baseline-docs-list');
  container.replaceChildren();

  var t = function (k, vars, fallback) {
    return (window.VisableI18n && window.VisableI18n.t) ? window.VisableI18n.t(k, vars, fallback) : (fallback || k);
  };

  var structured = parseRequiredDocsStructured(item.required_text, item);

  // 1. Legal restrictions or ineligibility
  if (structured.restrictions.length) {
    var resCard = element('div', 'restriction-card');
    var resHead = element('div', 'restriction-head');
    resHead.appendChild(element('span', 'restriction-icon', '⛔'));
    resHead.appendChild(element('h4', '', t('restrictionTitle', null, '신청 불가 또는 별도 절차 대상 안내')));
    resCard.appendChild(resHead);

    var resBody = element('div', 'restriction-body');
    structured.restrictions.forEach(function (r) {
      resBody.appendChild(element('p', '', r));
    });

    if (state.procedure === 'extension' && item.status_code.includes('F-5')) {
      resBody.appendChild(element('p', 'restriction-note', t('restrictionF5Note', null, '※ 영주(F-5) 자격은 체류기간 제한이 없으므로 체류기간 연장허가 대상이 아닙니다. 10년 주기 영주증(등록증) 만료 시에는 관할 출입국관서에서 영주증 재발급·갱신을 신청해야 합니다.')));
    } else if (state.procedure === 'change') {
      resBody.appendChild(element('p', 'restriction-note', t('restrictionChangeNote', null, '※ 이 체류자격은 출입국관리법령상 국내에서 다른 자격으로(또는 다른 자격에서 이 자격으로) 변경허가를 신청할 수 없는 원칙이 적용됩니다. 출국 후 재외공관을 통한 신규 사증(Visa) 발급 대상입니다.')));
    }

    resCard.appendChild(resBody);
    container.appendChild(resCard);
  }

  // 2. Unlisted in manual
  if (structured.unlisted) {
    var unCard = element('div', 'unlisted-card');
    var unHead = element('div', 'unlisted-head');
    unHead.appendChild(element('span', 'unlisted-icon', 'ℹ️'));
    unHead.appendChild(element('h4', '', t('unlistedTitle', null, '원문 매뉴얼 상 독립 제출서류 목록 미기재')));
    unCard.appendChild(unHead);
    unCard.appendChild(element('p', '', structured.unlistedText || t('unlistedDesc', null, '2026년 9월 공식 매뉴얼에 독립된 제출서류 목록이 수록되어 있지 않습니다. 관할 출입국관서 또는 1345에 확인하세요.')));
    unCard.appendChild(element('p', 'muted', t('unlistedMuted', null, '출입국관리법령상 개별 심사관 판단에 따라 제출 서류가 정해지므로 방문 전 관할청에 문의하시기 바랍니다.')));
    container.appendChild(unCard);
  }

  // 3. Document items
  var docs = structured.items;
  if (!docs.length) {
    if (!structured.restrictions.length && !structured.unlisted) {
      container.appendChild(element('p', 'muted', (state.lang === 'en')
        ? 'No mandatory baseline documents listed in official source. Check requirements with the local office or HiKorea.'
        : '명시된 기본 제출 서류가 원문에 기재되지 않았습니다. 관할 출입국관서 또는 하이코리아에 서류 요건을 확인하세요.'));
    }
    updateProgressBar(0, 0, structured.restrictions.length > 0 ? (state.lang === 'en' ? 'Ineligible / Special Procedure' : '신청 제한 / 별도 절차 대상') : structured.unlisted ? (state.lang === 'en' ? 'Check Required with Office' : '공식 서류 목록 개별 확인 필요') : (state.lang === 'en' ? '0 / 0 Ready (0%)' : '0 / 0개 준비 완료 (0%)'));
    return;
  }

  var checkedSet = new Set(state.checked_docs[item.id] || []);
  var totalCount = docs.length;
  var checkedCount = 0;

  var altBadgeText = t('badgeAlternative', null, '택 1 제출 (대체 가능)');
  var condBadgeText = t('badgeConditional', null, '해당자 제출');
  var formHelperText = t('formHelperLinkText', null, 'VISABLE 서식 도우미에서 바로 작성하기 ↗');

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
    input.setAttribute('aria-label', docItem.label + (state.lang === 'en' ? ' marked ready' : ' 준비 완료'));
    chkWrap.appendChild(input);

    var textWrap = element('div', 'checklist-text-wrap');
    var label = document.createElement('label');
    label.htmlFor = itemId;
    label.className = 'checklist-doc-name';
    label.textContent = docItem.label;

    if (docItem.type === 'alternative') {
      var altBadge = element('span', 'item-badge alternative-badge', altBadgeText);
      label.appendChild(altBadge);
    } else if (docItem.type === 'conditional') {
      var condBadge = element('span', 'item-badge conditional-badge-inline', condBadgeText);
      label.appendChild(condBadge);
    }

    textWrap.appendChild(label);

    if (docItem.isFormHelper) {
      var link = document.createElement('a');
      link.href = 'form-helper.html' + (state.lang !== 'ko' ? ('?lang=' + encodeURIComponent(state.lang)) : '');
      link.className = 'checklist-form-helper-link';
      link.target = '_blank';
      link.rel = 'noopener noreferrer';
      link.textContent = formHelperText;
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

  // Statutory supremacy legal warning banner
  var legalNote = element('div', 'legal-warning-banner');
  legalNote.appendChild(element('span', 'legal-warning-icon', '⚖️'));
  legalNote.appendChild(element('p', '', t('legalWarningNote')));
  container.appendChild(legalNote);

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
      var t = function (k, vars, fallback) {
        return (window.VisableI18n && window.VisableI18n.t) ? window.VisableI18n.t(k, vars, fallback) : (fallback || k);
      };
      label.textContent = t('progressPattern', { checked: checked, total: total, percent: percent }, checked + ' / ' + total + '개 준비 완료 (' + percent + '%)');
    }
  }
}

function renderConditionalDocs(item) {
  var container = $('conditional-docs-content');
  container.replaceChildren();

  if (!item.conditional_text || item.conditional_text === '별도 기재 없음') {
    var emptyText = (state.lang === 'en')
      ? 'No conditional or alternative documents specified for this scenario.'
      : (state.lang === 'zh-CN')
      ? '此情形下无单独列明的条件性或替代性材料。'
      : (state.lang === 'vi')
      ? 'Trường hợp này không có yêu cầu hồ sơ có điều kiện hoặc thay thế riêng.'
      : (state.lang === 'id')
      ? 'Tidak ada dokumen bersyarat atau alternatif yang ditentukan untuk skenario ini.'
      : '이 세부 상황에는 별도로 명시된 조건부·대체 서류가 없습니다.';
    container.appendChild(element('p', 'muted', emptyText));
    return;
  }

  var cardEl = element('div', 'condition-card');
  var cardTitle = (state.lang === 'en')
    ? 'Additional or Exemptible Documents When Applicable'
    : (state.lang === 'zh-CN')
    ? '符合条件时追加提交或可免除之材料'
    : (state.lang === 'vi')
    ? 'Hồ sơ bổ sung hoặc được miễn khi thỏa mãn điều kiện'
    : (state.lang === 'id')
    ? 'Dokumen Tambahan atau yang Dapat Dikecualikan Jika Berlaku'
    : '해당 시 추가 제출 또는 생략 가능한 서류';
  cardEl.appendChild(element('h4', '', cardTitle));
  cardEl.appendChild(element('p', '', item.conditional_text));
  container.appendChild(cardEl);
}

function renderApplicationGuidance(item) {
  var container = $('application-docs-content');
  container.replaceChildren();

  var text = item.application_text;
  if (!text) {
    if (state.procedure === 'registration') {
      text = (state.lang === 'en')
        ? 'First-time Alien Registration and Residence Reporting require personal attendance for fingerprint and facial biometric registration (age 17+). In-person attendance at the jurisdiction office is mandatory regardless of whether document filing by proxy is permitted.'
        : (state.lang === 'zh-CN')
        ? '初次外国人登录及居所申报需要录入指纹和面部生物信息（17周岁以上），本人必须亲自到场。无论是否允许代交材料，生物信息采集流程均必须亲自前往管辖出入境办事处。'
        : (state.lang === 'vi')
        ? 'Đăng ký cư trú và báo cáo cư sở lần đầu yêu cầu người từ 17 tuổi trở lên phải trực tiếp có mặt để lấy sinh trắc học (vân tay và ảnh khuôn mặt). Bắt buộc phải trực tiếp đến cơ quan quản hạt bất kể có được nộp hồ sơ thay hay không.'
        : (state.lang === 'id')
        ? 'Pendaftaran orang asing dan pelaporan tinggal pertama kali mewajibkan kehadiran langsung untuk perekaman biometrik (usia 17+). Kehadiran di kantor imigrasi adalah wajib terlepas dari pengajuan berkas oleh kuasa.'
        : '신규 외국인등록 및 국내거소신고는 등록대상자의 연령(17세 이상)·생체정보(지문 및 얼굴) 등록 여부에 따라 본인 출석이 필요합니다. 대리 접수 가능 여부와 별개로 생체정보 제공 절차는 관할 청 방문이 필수입니다.';
    } else {
      text = (state.lang === 'en')
        ? 'Applications may be filed by the applicant or a legally qualified representative (family member, licensed administrative attorney). However, individual appearance may be required if personal identity verification is requested during examination.'
        : (state.lang === 'zh-CN')
        ? '可由本人或依法具备代办资格的代理人（直系亲属、注册出入境行政士等）递交。但若审查过程中需要确认本人身份，可能会被要求亲自到场。'
        : (state.lang === 'vi')
        ? 'Đơn có thể do đương đơn hoặc người đại diện hợp pháp (người thân, luật sư hành chính được cấp phép) nộp. Tuy nhiên có thể được yêu cầu có mặt trực tiếp nếu cần xác minh danh tính cá nhân.'
        : (state.lang === 'id')
        ? 'Permohonan dapat diajukan sendiri atau oleh kuasa yang sah (keluarga, kuasa hukum terdaftar). Namun, kehadiran pribadi dapat diminta jika verifikasi identitas diperlukan.'
        : '본인 또는 출입국관리법상 자격 있는 대리인(가족, 행정사 등)이 접수할 수 있습니다. 단, 개별 심사 및 본인 확인이 필요한 경우 출석을 요구받을 수 있습니다.';
    }
  }

  var cardEl = element('div', 'app-guidance-card');
  cardEl.appendChild(element('p', '', text));
  container.appendChild(cardEl);
}

function renderOfficeDifferences(item) {
  var container = $('office-docs-content');
  container.replaceChildren();

  var t = function (k, vars, fallback) {
    return (window.VisableI18n && window.VisableI18n.t) ? window.VisableI18n.t(k, vars, fallback) : (fallback || k);
  };

  if (!state.office) {
    var notice = element('div', 'office-transparent-notice');
    notice.appendChild(element('strong', '', t('officeNationalNoticeTitle', null, '전국 기준 안내가 적용 중입니다.')));
    notice.appendChild(element('p', '', t('officeNationalNoticeBody', null, '방문 예정인 관할 출입국·외국인관서를 선택하시면 해당 관서에 대해 별도로 확인된 요구서류가 있는지 안내해 드립니다.')));
    container.appendChild(notice);
    $('office-status-badge').textContent = (state.lang === 'en') ? 'National Baseline' : '전국 기준 안내';
    return;
  }

  var oName = officeName(state.office);
  var diffs = localNotes(item);

  if (diffs.length) {
    $('office-status-badge').textContent = oName + (state.lang === 'en' ? ' Local Notes' : ' 추가 확인');
    diffs.forEach(function (entry) {
      container.appendChild(officeCallout(entry));
    });
  } else {
    $('office-status-badge').textContent = oName + (state.lang === 'en' ? ' National Baseline' : ' 전국 기준 안내');
    var notice2 = element('div', 'office-transparent-notice');
    notice2.appendChild(element('strong', '', oName + (state.lang === 'en' ? ' Document Guidance' : ' 서류 안내')));
    notice2.appendChild(element('p', '', (state.lang === 'en')
      ? 'No local variances currently recorded for this office. Official national standards apply. The head of the local office may request additional evidence under administrative discretion.'
      : '이 관서에 대해 별도로 확인된 서류 차이가 아직 없습니다. 출입국관리법령상 관할 청장의 재량에 따라 추가 소명서류가 요구될 수 있으므로, 방문 전 관할청의 최신 공지를 확인해 주세요.'));
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
/* MULTILINGUAL LOCALIZATION CONTROLLER (R4)                                 */
/* ------------------------------------------------------------------------- */
function updateLanguage(locale) {
  var loc = locale || (window.VisableI18n ? window.VisableI18n.getLocale() : 'ko');
  state.lang = loc;

  var t = function (k, vars, fallback) {
    return (window.VisableI18n && window.VisableI18n.t) ? window.VisableI18n.t(k, vars, fallback) : (fallback || k);
  };

  // Sync lang select dropdown
  var sel = $('lang-select');
  if (sel && sel.value !== loc) {
    sel.value = loc;
  }

  // HTML lang & direction attributes
  if (window.VisableI18n && window.VisableI18n.applyRTL) {
    window.VisableI18n.applyRTL(loc);
  } else {
    document.documentElement.lang = loc;
    if (loc === 'ar') {
      document.documentElement.dir = 'rtl';
      document.body.classList.add('rtl-layout');
    } else {
      document.documentElement.dir = 'ltr';
      document.body.classList.remove('rtl-layout');
    }
  }

  // Document Title
  document.title = (loc === 'ko') ? '서류 안내 | VISABLE' : (t('navDocuments', null, 'Document Guide') + ' | VISABLE');

  // Skip links
  var skip1 = document.querySelector('a.skip[href="#main-content"]');
  if (skip1) skip1.textContent = t('skipToContent', null, '본문 바로가기');
  var skip2 = document.querySelector('a.skip[href="#results"]');
  if (skip2) skip2.textContent = t('skipToResults', null, '전체 검색 결과로 이동');

  // Topbar
  var barName = document.querySelector('.bar-name');
  if (barName) barName.textContent = t('navDocuments', null, '서류 안내');

  var jumpGuided = document.querySelector('#jump-guided-btn span:last-child');
  if (jumpGuided) jumpGuided.textContent = t('navGuided', null, '맞춤 안내');

  var jumpSearch = document.querySelector('#jump-search-btn span:last-child');
  if (jumpSearch) jumpSearch.textContent = t('navSearch', null, '전체 검색');

  var formHelperLink = document.querySelector('.header-link span:first-child');
  if (formHelperLink) formHelperLink.textContent = t('navFormHelper', null, '서식 작성');
  var formHelperAnchor = document.querySelector('.header-link');
  if (formHelperAnchor) {
    formHelperAnchor.href = 'form-helper.html' + (loc !== 'ko' ? ('?lang=' + encodeURIComponent(loc)) : '');
  }

  var opPillText = document.querySelector('#operator-mode-toggle .op-text');
  if (opPillText) opPillText.textContent = t('operatorMode', null, '운영자 모드');

  // Hero Section
  var heroEyebrow = $('hero-eyebrow');
  if (heroEyebrow) heroEyebrow.textContent = t('heroEyebrow', null, 'IMMIGRATION DOCUMENTS / 2026.09');

  var pageTitle = $('page-title');
  if (pageTitle) {
    pageTitle.innerHTML = t('pageTitleMain', null, '내 상황에 맞는 서류,') + '<br><span>' + t('pageTitleSub', null, '필요한 것부터 쉽고 확실하게.') + '</span>';
  }

  var heroCopy = $('hero-copy');
  if (heroCopy) heroCopy.textContent = t('heroCopy', null, '체류자격과 신청 업무를 선택하면 필요한 준비사항을 확인할 수 있어요. 같은 자격이어도 신청 상황에 따라 서류가 달라질 수 있습니다.');

  var metaCases = $('hero-meta-cases');
  if (metaCases && metaCases.parentElement) {
    metaCases.parentElement.innerHTML = '<strong>' + t('heroMetaCases', null, '647개') + '</strong> ' + (loc === 'ko' ? '세부 상황' : 'Scenarios');
  }
  var metaOffices = $('hero-meta-offices');
  if (metaOffices && metaOffices.parentElement) {
    metaOffices.parentElement.innerHTML = '<strong>' + t('heroMetaOffices', null, '26개') + '</strong> ' + (loc === 'ko' ? '관할관서 대응' : 'Offices');
  }
  var metaSource = document.querySelector('.hero-meta .meta-badge:nth-child(3)');
  if (metaSource) metaSource.textContent = t('heroMetaSource', null, '법무부 매뉴얼 편집본');

  // Stepper Header & Items
  var guidedSecTitle = $('guided-sec-title');
  if (guidedSecTitle) guidedSecTitle.textContent = t('guidedDiscoveryTitle', null, '맞춤 서류 단계별 찾기');
  var scopeNote = document.querySelector('.guided-head .scope-note');
  if (scopeNote) scopeNote.textContent = t('guidedDiscoverySubtitle', null, '초보자 추천 · 4단계 안내');

  var step1Label = document.querySelector('#stepper-btn-1 .step-label');
  if (step1Label) step1Label.textContent = t('stepperStep1', null, '업무 선택');
  var step2Label = document.querySelector('#stepper-btn-2 .step-label');
  if (step2Label) step2Label.textContent = t('stepperStep2', null, '체류자격');
  var step3Label = document.querySelector('#stepper-btn-3 .step-label');
  if (step3Label) step3Label.textContent = t('stepperStep3', null, '세부 상황');
  var step4Label = document.querySelector('#stepper-btn-4 .step-label');
  if (step4Label) step4Label.textContent = t('stepperStep4', null, '서류 체크리스트');

  // Step 1: Task Selection Cards
  var step1Title = $('step-1-title');
  if (step1Title) step1Title.textContent = t('step1Title', null, '한국에서 어떤 일을 하려고 하나요?');
  var step1Desc = document.querySelector('#guided-step-1 .step-desc');
  if (step1Desc) step1Desc.textContent = t('step1Desc', null, '원하는 업무를 선택해 주세요. 각 업무에 따라 준비해야 할 기본 법적 절차가 달라집니다.');

  var cardExt = document.querySelector('.task-card[data-procedure="extension"]');
  if (cardExt) {
    var pExt = cardExt.querySelector('.task-pill');
    if (pExt) pExt.textContent = t('stepperStep1', null, '체류기간 연장');
    var hExt = cardExt.querySelector('.task-title');
    if (hExt) hExt.textContent = t('taskExtensionTitle', null, '한국에 더 머물고 싶어요');
    var dExt = cardExt.querySelector('.task-desc');
    if (dExt) dExt.textContent = t('taskExtensionDesc', null, '현재 체류자격을 유지하면서 허가된 체류기간 만료일을 뒤로 연장하고자 할 때 신청합니다.');
    var sExt = cardExt.querySelector('.task-subtext');
    if (sExt) sExt.textContent = t('taskExtensionSub', null, '일반적으로 만료 4개월 전부터 신청 가능 (224개 상황)');
  }

  var cardChg = document.querySelector('.task-card[data-procedure="change"]');
  if (cardChg) {
    var pChg = cardChg.querySelector('.task-pill');
    if (pChg) pChg.textContent = t('stepperStep2', null, '체류자격 변경');
    var hChg = cardChg.querySelector('.task-title');
    if (hChg) hChg.textContent = t('taskChangeTitle', null, '한국에서 하는 일이 바뀌었어요');
    var dChg = cardChg.querySelector('.task-desc');
    if (dChg) dChg.textContent = t('taskChangeDesc', null, '학업에서 취업, 직장 이직, 투자, 결혼 등 다른 체류자격(비자)으로 변경하고자 할 때 신청합니다.');
    var sChg = cardChg.querySelector('.task-subtext');
    if (sChg) sChg.textContent = t('taskChangeSub', null, '새로 부여받을 목표 자격 기준 서류 확인 (251개 상황)');
  }

  var cardReg = document.querySelector('.task-card[data-procedure="registration"]:not([data-sub="residence"])');
  if (cardReg) {
    var pReg = cardReg.querySelector('.task-pill');
    if (pReg) pReg.textContent = (loc === 'ko' ? '외국인등록' : 'Alien Registration');
    var hReg = cardReg.querySelector('.task-title');
    if (hReg) hReg.textContent = t('taskRegistrationTitle', null, '외국인등록증을 처음 만들고 싶어요');
    var dReg = cardReg.querySelector('.task-desc');
    if (dReg) dReg.textContent = t('taskRegistrationDesc', null, '대한민국에 90일을 초과하여 장기 체류하기 위해 입국 후 신규 외국인등록증을 발급받을 때 신청합니다.');
    var sReg = cardReg.querySelector('.task-subtext');
    if (sReg) sReg.textContent = t('taskRegistrationSub', null, '입국일로부터 90일 이내 관할 출입국 방문 필수');
  }

  var cardRes = document.querySelector('.task-card[data-procedure="registration"][data-sub="residence"]');
  if (cardRes) {
    var pRes = cardRes.querySelector('.task-pill');
    if (pRes) pRes.textContent = (loc === 'ko' ? '국내거소신고' : 'Residence Reporting (F-4)');
    var hRes = cardRes.querySelector('.task-title');
    if (hRes) hRes.textContent = t('taskResidenceTitle', null, '재외동포로 거소신고를 하고 싶어요');
    var dRes = cardRes.querySelector('.task-desc');
    if (dRes) dRes.textContent = t('taskResidenceDesc', null, '재외동포(F-4) 자격 소지자가 대한민국 내에 거소를 정하여 국내거소신고증을 발급받을 때 신청합니다.');
    var sRes = cardRes.querySelector('.task-subtext');
    if (sRes) sRes.textContent = t('taskResidenceSub', null, '재외동포법에 따른 거소신고 및 연계 서류 확인');
  }

  var taskHelpTextStrong = document.querySelector('.task-help-text strong');
  if (taskHelpTextStrong) taskHelpTextStrong.textContent = t('taskHelpTitle', null, '어떤 절차에 해당하는지 잘 모르겠나요?');
  var taskHelpTextSpan = document.querySelector('.task-help-text span');
  if (taskHelpTextSpan) taskHelpTextSpan.textContent = t('taskHelpSubtitle', null, '상황별 차이점과 하이코리아·1345 공식 상담 번호를 확인하세요.');
  var taskHelpBtn = $('task-help-btn');
  if (taskHelpBtn) taskHelpBtn.textContent = t('taskHelpBtnText', null, '절차 구별 가이드 보기');

  // Step 2
  var step2Back = $('step-2-back');
  if (step2Back) step2Back.textContent = t('step2BackBtn', null, '← 이전: 업무 선택으로');
  var subtabKnow = $('subtab-know');
  if (subtabKnow) subtabKnow.textContent = t('subtabKnow', null, '체류자격을 알고 있어요');
  var subtabDontKnow = $('subtab-dont-know');
  if (subtabDontKnow) subtabDontKnow.textContent = t('subtabDontKnow', null, '체류자격을 확인하고 싶어요 (등록증 보는 법)');
  var searchLabelSpan = document.querySelector('.status-search-label span');
  if (searchLabelSpan) searchLabelSpan.textContent = t('statusSearchLabel', null, '체류자격 코드 또는 명칭 검색');
  var pickerInput = $('status-picker-input');
  if (pickerInput) pickerInput.placeholder = t('statusSearchPlaceholder', null, '예: D-2, E-7-1, 유학, 특정활동, 결혼이민...');
  var mutedHint = document.querySelector('.status-search-box .muted-hint');
  if (mutedHint) mutedHint.textContent = t('statusSearchHint', null, '코드(D-2, F-4, E-7), 공식명칭(유학, 재외동포), 영문명(Study, Work)으로 검색할 수 있습니다.');
  var chipsLabel = document.querySelector('.chips-label');
  if (chipsLabel) chipsLabel.textContent = t('popularChipsLabel', null, '자주 찾는 체류자격:');

  // Step 2 ARC guide
  var arcH4 = document.querySelector('.arc-guide-text h4');
  if (arcH4) arcH4.textContent = t('arcGuideTitle', null, '외국인등록증(ARC)에서 체류자격 확인하기');
  var arcP = document.querySelector('.arc-guide-text > p');
  if (arcP) arcP.textContent = t('arcGuideSubtitle', null, '가지고 계신 등록증의 앞면 가운데에 체류자격(SOJOURN STATUS)과 체류기간(PERIOD OF SOJOURN)이 표시되어 있습니다.');
  var arcLi1 = document.querySelector('.arc-steps-list li:nth-child(1)');
  if (arcLi1) arcLi1.textContent = t('arcGuideStep1', null, "외국인등록증 앞면 중앙의 '체류자격(SOJOURN STATUS)' 란을 확인하세요.");
  var arcLi2 = document.querySelector('.arc-steps-list li:nth-child(2)');
  if (arcLi2) arcLi2.textContent = t('arcGuideStep2', null, '알파벳 대문자와 숫자 조합(예: E-7-1, D-2-2, F-4-11)이 적혀 있습니다.');
  var arcLi3 = document.querySelector('.arc-steps-list li:nth-child(3)');
  if (arcLi3) arcLi3.textContent = t('arcGuideStep3', null, "아래 예시 카드의 강조된 위치를 확인하신 후, '체류자격을 알고 있어요' 탭에서 해당 코드를 선택해 주세요.");
  var arcExtRouteTitle = document.querySelector('.ext-route-title');
  if (arcExtRouteTitle) arcExtRouteTitle.textContent = t('arcGuideExtTitle', null, '등록증이 없거나 확인이 어려우신가요?');
  var arcHikoreaLink = document.querySelector('.arc-external-routes a.link-external');
  if (arcHikoreaLink) arcHikoreaLink.textContent = t('arcGuideHikoreaLink', null, '하이코리아 체류만료일 및 자격 조회 바로가기 ↗');
  var arc1345 = document.querySelector('.call-1345-note');
  if (arc1345) arc1345.textContent = t('arcGuideCall1345', null, '또는 법무부 출입국종합안내센터 국번 없이 1345 (20개 국어 무료 상담)');
  var arcTargetPin = document.querySelector('.arc-target-pin');
  if (arcTargetPin) arcTargetPin.textContent = t('arcGuidePinText', null, '👈 이 위치를 확인하세요!');
  var switchToPickerBtn = $('switch-to-picker-btn');
  if (switchToPickerBtn) switchToPickerBtn.textContent = t('arcGuideCta', null, '체류자격 코드를 확인했어요 → 목록에서 선택하기');

  // Step 3
  var step3Back = $('step-3-back');
  if (step3Back) step3Back.textContent = t('step3BackBtn', null, '← 이전: 체류자격 변경');
  var scenarioDisclaimer = document.querySelector('.scenario-disclaimer-note span');
  if (scenarioDisclaimer) scenarioDisclaimer.textContent = t('scenarioDisclaimer', null, '※ 위 상황 목록은 2026년 9월 매뉴얼 공식 편제 항목을 기준으로 분류된 정본입니다. 임의로 조건을 추가하거나 생략하지 않았습니다.');

  // Step 4
  var step4Back = $('step-4-back');
  if (step4Back) step4Back.textContent = t('step4BackBtn', null, '← 이전: 세부 상황 변경');
  var guidedResetBtn = $('guided-reset-btn');
  if (guidedResetBtn) guidedResetBtn.textContent = t('step4ResetBtn', null, '처음부터 다시 찾기 ↺');
  var step4Title = $('step-4-title');
  if (step4Title) step4Title.textContent = t('step4Title', null, '맞춤 서류 준비 체크리스트');
  var step4Desc = document.querySelector('#guided-step-4 .step-desc');
  if (step4Desc) step4Desc.textContent = t('step4Desc', null, '선택하신 조건에 맞춰 준비해야 할 서류를 정리했습니다. 준비한 서류를 체크하며 방문을 준비해 보세요.');

  var officeLbl = document.querySelector('.office-lbl');
  if (officeLbl) officeLbl.textContent = t('officeSelectLabel', null, '방문 예정 관할 출입국관서:');
  var officeNoticeText = $('checklist-office-notice-text');
  if (officeNoticeText) officeNoticeText.textContent = t('officeSelectNotice', null, '관서 정보는 검증 단계에 따라 별도로 구분 표시됩니다.');
  var checkOfficeSelect = $('checklist-office-select');
  if (checkOfficeSelect && checkOfficeSelect.options.length > 0) {
    checkOfficeSelect.options[0].textContent = t('officeSelectDefault', null, '전국 공통 기준');
  }

  var progressTitle = $('progress-title');
  if (progressTitle) progressTitle.textContent = t('progressTitle', null, '기본 서류 준비 진행 상황');
  var progressNote = document.querySelector('.progress-note');
  if (progressNote) progressNote.textContent = t('progressNote', null, '※ 숫자는 확정된 기본 제출서류만을 기준으로 계산되며, 조건부 서류는 개별 상황에 따라 별도 확인이 필요합니다.');

  var baselineGroupTitle = $('baseline-group-title');
  if (baselineGroupTitle) baselineGroupTitle.textContent = t('baselineGroupTitle', null, '기본 제출서류');
  var baselineBadge = document.querySelector('.baseline-group .group-badge');
  if (baselineBadge) baselineBadge.textContent = t('badgeRequired', null, '반드시 준비');
  var baselineGroupDesc = document.querySelector('.baseline-group .group-desc');
  if (baselineGroupDesc) baselineGroupDesc.textContent = t('baselineGroupDesc', null, '해당 신청 업무와 상황에서 공통적으로 제출하도록 명시된 서류입니다.');

  var conditionalGroupTitle = $('conditional-group-title');
  if (conditionalGroupTitle) conditionalGroupTitle.textContent = t('conditionalGroupTitle', null, '상황에 따라 필요한 서류 (해당자 제출)');
  var conditionalBadge = document.querySelector('.conditional-group .group-badge');
  if (conditionalBadge) conditionalBadge.textContent = t('badgeConditional', null, '조건부 확인');
  var conditionalGroupDesc = document.querySelector('.conditional-group .group-desc');
  if (conditionalGroupDesc) conditionalGroupDesc.textContent = t('conditionalGroupDesc', null, '개별 체류조건, 소득 증명, 가족 동반, 고위험국 결핵검진 등 특정 요건이 충족될 때 제출합니다.');

  var appGroupTitle = $('application-group-title');
  if (appGroupTitle) appGroupTitle.textContent = t('applicationGroupTitle', null, '방문 및 대리 신청 안내');
  var appBadge = document.querySelector('.application-group .group-badge');
  if (appBadge) appBadge.textContent = t('badgeApplication', null, '출석·대리 절차');
  var appGroupDesc = document.querySelector('.application-group .group-desc');
  if (appGroupDesc) appGroupDesc.textContent = t('applicationGroupDesc', null, '서류 접수 대리와 본인 출석(지문·생체정보 등록, 인터뷰, 실물 등록증 수령)은 별개의 절차입니다.');

  var officeGroupTitle = $('office-group-title');
  if (officeGroupTitle) officeGroupTitle.textContent = t('officeGroupTitle', null, '관할 출입국관서별 안내');

  var cautionsGroupTitle = $('cautions-group-title');
  if (cautionsGroupTitle) cautionsGroupTitle.textContent = t('cautionsGroupTitle', null, '방문 전 확인사항 및 법적 한계');
  var cautionsBadge = document.querySelector('.cautions-group .group-badge');
  if (cautionsBadge) cautionsBadge.textContent = t('badgeWarning', null, '유의사항');

  var caution1Strong = document.querySelector('.cautions-content .caution-item:nth-child(1) strong');
  if (caution1Strong) caution1Strong.textContent = t('cautionPermitTitle', null, '체류허가 보장 여부');
  var caution1P = document.querySelector('.cautions-content .caution-item:nth-child(1) p');
  if (caution1P) caution1P.textContent = t('cautionPermitBody', null, '체류서류를 모두 준비했다고 해서 법적으로 체류기간 연장이나 자격변경 허가가 보장되는 것은 아닙니다. 심사 과정에서 관할 청 심사관의 판단에 따라 추가 소명자료 제출을 요구받을 수 있습니다.');

  var caution2Strong = document.querySelector('.cautions-content .caution-item:nth-child(2) strong');
  if (caution2Strong) caution2Strong.textContent = t('cautionTimingTitle', null, '자료 기준 시점 및 검증 상태');
  var caution2P = document.querySelector('.cautions-content .caution-item:nth-child(2) p');
  if (caution2P) caution2P.textContent = t('cautionTimingBody', null, '본 체크리스트는 2026년 9월 출입국 매뉴얼을 기반으로 정리된 이관 편집자료(COMPILED_NEEDS_REVIEW)입니다. 최신 지침 고시나 관할관서 공지가 우선하므로, 중요한 신청 전에는 하이코리아 공지사항을 반드시 대조하세요.');

  var hikoreaBtn = document.querySelector('.official-links-row a.ext-btn:first-child');
  if (hikoreaBtn) hikoreaBtn.textContent = t('hikoreaOfficialBtn', null, '하이코리아 바로가기 (온라인 방문예약·전자민원) ↗');
  var snapshotBtn = document.querySelector('.official-links-row a.ext-btn.secondary-ext');
  if (snapshotBtn) snapshotBtn.textContent = t('snapshotCompareBtn', null, '이관 원문표 대조 확인 ↗');

  var printBtnSpan = document.querySelector('#checklist-print-btn span:last-child');
  if (printBtnSpan) printBtnSpan.textContent = t('btnPrint', null, '체크리스트 인쇄 / PDF 저장');
  var copyLinkBtnSpan = document.querySelector('#checklist-copy-link-btn span:last-child');
  if (copyLinkBtnSpan) copyLinkBtnSpan.textContent = t('btnCopyLink', null, '결과 링크 복사');
  var clearChecksBtn = $('checklist-clear-checks-btn');
  if (clearChecksBtn) clearChecksBtn.textContent = t('btnClearChecks', null, '체크 상태 초기화');

  // Direct Search Section
  var searchTitle = $('search-title');
  if (searchTitle) searchTitle.textContent = (loc === 'ko') ? '서류 찾아보기' : 'Search All Documents';
  var queryLegend = document.querySelector('.segmented legend');
  if (queryLegend) queryLegend.textContent = (loc === 'ko') ? '신청 업무 선택' : 'Select Procedure';
  var radExtSpan = document.querySelector('input[name="procedure"][value="extension"] + span');
  if (radExtSpan) radExtSpan.textContent = (loc === 'ko') ? '체류기간 연장' : (window.VisableI18n ? window.VisableI18n.getProcedureName('extension', loc) : '체류기간 연장');
  var radChgSpan = document.querySelector('input[name="procedure"][value="change"] + span');
  if (radChgSpan) radChgSpan.textContent = (loc === 'ko') ? '체류자격 변경' : (window.VisableI18n ? window.VisableI18n.getProcedureName('change', loc) : '체류자격 변경');
  var radRegSpan = document.querySelector('input[name="procedure"][value="registration"] + span');
  if (radRegSpan) radRegSpan.textContent = (loc === 'ko') ? '외국인등록·거소신고' : (window.VisableI18n ? window.VisableI18n.getProcedureName('registration', loc) : '외국인등록·거소신고');

  var querySpan = document.querySelector('.filters .field:first-child span');
  if (querySpan) querySpan.textContent = (loc === 'ko') ? '체류자격·서류 검색' : 'Search Visa / Documents';
  var queryInput = $('query');
  if (queryInput) queryInput.placeholder = (loc === 'ko') ? '예: E-7-1, D-2, 재학증명서' : 'e.g., E-7-1, D-2, Certificate of Enrollment...';
  var officeSpan = document.querySelector('.filters .field:last-child span');
  if (officeSpan) officeSpan.textContent = (loc === 'ko') ? '관할 출입국관서' : 'Jurisdiction Immigration Office';
  var officeSelect0 = document.querySelector('#office option[value=""]');
  if (officeSelect0) officeSelect0.textContent = t('officeSelectDefault', null, '전국 공통 기준');
  var resetBtn = $('reset');
  if (resetBtn) resetBtn.textContent = (loc === 'ko') ? '선택 초기화 ↺' : 'Reset Filters ↺';

  var resultsTitle = $('results-title');
  if (resultsTitle) resultsTitle.textContent = (loc === 'ko') ? '상황별 준비서류' : 'Documents by Scenario';

  // Re-render active guided step
  if (state.step === 2) {
    renderGuidedStep2();
    renderStatusCandidates();
  } else if (state.step === 3) {
    renderGuidedStep3();
  } else if (state.step === 4) {
    renderGuidedStep4();
  }
  render();
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

    // Candidate Preview & Published API integration (R3.1)
    var params = new URLSearchParams(window.location.search);
    var previewRelease = params.get('preview_release') || params.get('preview');

    if (previewRelease) {
      try {
        var previewApiUrl = (window.VisableBackend && window.VisableBackend.url)
          ? window.VisableBackend.url('/api/checklists/preview?release_id=' + encodeURIComponent(previewRelease))
          : ('/api/checklists/preview?release_id=' + encodeURIComponent(previewRelease));
        var prevRes = await fetch(previewApiUrl, { cache: 'no-cache' });
        if (prevRes.ok) {
          var prevData = await prevRes.json();
          if (prevData && prevData.extension && prevData.change && prevData.registration) {
            ['extension', 'change', 'registration'].forEach(function (t) {
              if (prevData[t] && prevData[t].items) {
                state.datasets[t] = prevData[t];
              }
            });
            renderPreviewBanner(prevData);
          }
        }
      } catch (prevErr) {
        console.warn('Candidate preview fetch failed, using baseline:', prevErr);
      }
    } else {
      try {
        var pubApiUrl = (window.VisableBackend && window.VisableBackend.url)
          ? window.VisableBackend.url('/api/checklists/published')
          : '/api/checklists/published';
        var pubRes = await fetch(pubApiUrl, { cache: 'no-cache' });
        if (pubRes.ok) {
          var pubData = await pubRes.json();
          if (pubData && pubData.extension && pubData.change && pubData.registration) {
            ['extension', 'change', 'registration'].forEach(function (t) {
              if (pubData[t] && pubData[t].items) {
                state.datasets[t] = pubData[t];
              }
            });
          }
        }
      } catch (_) {
        // Fallback to static datasets
      }
    }

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

    // Initialize & apply localization
    var currentLocale = (window.VisableI18n ? window.VisableI18n.getLocale() : 'ko');
    state.lang = currentLocale;
    updateLanguage(state.lang);
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

function renderPreviewBanner(data) {
  var existing = document.getElementById('release-preview-banner');
  if (existing) existing.remove();

  var banner = document.createElement('aside');
  banner.id = 'release-preview-banner';
  banner.className = 'release-preview-banner';
  banner.setAttribute('role', 'status');
  banner.setAttribute('aria-label', '배포 후보 릴리스 미리보기');

  var content = document.createElement('div');
  content.className = 'release-preview-content';

  var badge = document.createElement('span');
  badge.className = 'release-preview-badge';
  badge.textContent = 'CANDIDATE PREVIEW';

  var info = document.createElement('div');
  info.className = 'release-preview-info';

  var labelText = document.createElement('strong');
  labelText.textContent = '배포 후보 미리보기 모드';

  var tagSpan = document.createElement('span');
  tagSpan.className = 'release-preview-tag';
  tagSpan.textContent = data.release_tag || data.release_id || 'candidate';

  info.appendChild(labelText);
  info.appendChild(document.createTextNode(' · 릴리스: '));
  info.appendChild(tagSpan);

  if (data.checksum_sha256) {
    var checkSpan = document.createElement('span');
    checkSpan.className = 'release-preview-checksum';
    checkSpan.textContent = 'SHA: ' + data.checksum_sha256.substring(0, 10) + '...';
    info.appendChild(document.createTextNode(' · '));
    info.appendChild(checkSpan);
  }

  content.appendChild(badge);
  content.appendChild(info);

  var exitLink = document.createElement('a');
  exitLink.className = 'release-preview-exit';
  exitLink.href = 'immigration-checklists.html';
  exitLink.textContent = '미리보기 종료 ✕';

  banner.appendChild(content);
  banner.appendChild(exitLink);

  var topbar = document.querySelector('.topbar');
  if (topbar && topbar.parentNode) {
    topbar.parentNode.insertBefore(banner, topbar);
  } else {
    document.body.prepend(banner);
  }
}

function handleUrlParams() {
  var params = new URLSearchParams(window.location.search);
  var proc = params.get('procedure') || params.get('proc');
  var code = params.get('code') || params.get('status');
  var scenarioId = params.get('scenario');
  var office = params.get('office');
  var lang = params.get('lang');

  if (lang && window.VisableI18n) {
    window.VisableI18n.setLocale(lang);
    state.lang = window.VisableI18n.getLocale();
  }

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
  if (state.lang) url.searchParams.set('lang', state.lang);
  var alertMsg = (window.VisableI18n && window.VisableI18n.t)
    ? window.VisableI18n.t('linkCopiedAlert', null, '맞춤 서류 체크리스트 링크가 복사되었습니다!')
    : '맞춤 서류 체크리스트 링크가 복사되었습니다!';
  navigator.clipboard.writeText(url.toString()).then(function () {
    window.alert(alertMsg);
  }).catch(function () {
    window.prompt(alertMsg, url.toString());
  });
});
$('checklist-clear-checks-btn').addEventListener('click', function () {
  if (state.selected_item) {
    state.checked_docs[state.selected_item.id] = [];
    safeSave(C_KEY, state.checked_docs);
    renderBaselineChecklist(state.selected_item);
    var alertMsg = (window.VisableI18n && window.VisableI18n.t)
      ? window.VisableI18n.t('checksClearedAlert', null, '서류 체크 상태가 초기화되었습니다.')
      : '서류 체크 상태가 초기화되었습니다.';
    window.alert(alertMsg);
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

// Language select & synchronization (R4)
$('lang-select').addEventListener('change', function (e) {
  var newLang = e.target.value;
  if (window.VisableI18n) {
    window.VisableI18n.setLocale(newLang);
  } else {
    updateLanguage(newLang);
  }
});

window.addEventListener('visable-language-changed', function (e) {
  var newLocale = (e.detail && e.detail.locale) ? e.detail.locale : (window.VisableI18n ? window.VisableI18n.getLocale() : 'ko');
  if (newLocale !== state.lang) {
    updateLanguage(newLocale);
  }
});

window.__VISABLE_INTERNALS = {
  splitParenSafe: splitParenSafe,
  parseRequiredDocsStructured: parseRequiredDocsStructured,
  getVisaInfo: getVisaInfo,
  updateLanguage: updateLanguage,
  state: state
};

load();
})();
