/* Paradiso — 국적민원·귀화면접 준비 hub engine.
 * Vanilla JS, no build. Loads five local JSON datasets and renders the hub.
 * Mock-interview feedback works fully offline (local heuristics); the Waymaker
 * coach is an optional enhancement that degrades gracefully when the backend
 * is unavailable. No transcripts are ever fetched or stored. */
(function () {
  'use strict';

  /* ----------------------------------------------------------------- i18n */
  var I18N = {
    ko: {
      'hero.kicker': '국적민원·귀화면접 준비',
      'hero.title': '국적민원과 귀화면접 준비를 한곳에서',
      'hero.lead': '귀화, 국적회복, 국적상실·이탈, 복수국적, 국민선서와 귀화면접 준비까지 — 공식 법령과 안내를 바탕으로 내 상황에 가까운 흐름을 살펴보고, 연습 질문과 모의면접으로 준비할 수 있습니다.',
      'hero.ctaPrimary': '귀화면접 학습 시작', 'hero.ctaSecondary': '국적민원 둘러보기',
      'global.disclaimer': '이 기능은 국적민원 확인과 귀화면접 및 기본소양 준비를 돕기 위한 학습 도구이며, 실제 심사 결과를 보장하지 않습니다. 공식 안내와 개별 통지는 법무부·출입국외국인관서 안내를 우선 확인하세요.',
      'about.title': '국적민원 알아보기',
      'about.intro': '관심 있는 국적민원 유형을 골라, 어떤 민원인지·누구를 위한 것인지·일반적 흐름·서류 유의사항·관련 법령과 공식 출처를 확인하세요. 개별 사안별로 달라질 수 있습니다.',
      'laws.title': '관련 법령·지침',
      'laws.intro': '국적 업무의 근거가 되는 공식 출처를 종류별로 살펴보세요. 지역 공지나 보조 설명자료는 별도로 표시됩니다. 외부 링크로 원문을 직접 확인할 수 있습니다.',
      'flow.title': '절차·서류 흐름',
      'flow.intro': '유형을 선택하면 일반적인 흐름과 서류 관련 유의사항을 볼 수 있습니다. 정확한 순서·서류·기준은 관할 출입국외국인관서 안내가 우선이며 개별 사안에 따라 달라질 수 있습니다.',
      'interview.title': '귀화면접 대비 학습실',
      'interview.intro': '절차 이해부터 핵심 주제 학습, 예상 질문 카드, 모의면접 연습, 참고 영상까지 단계별로 준비하세요. 모든 질문은 학습용 연습문제이며 실제 면접 질문이나 공식 기출문제가 아닙니다.',
      'kiip.title': '사전평가/종합평가 학습 흐름',
      'kiip.intro': '사회통합프로그램(KIIP)은 사전평가로 단계를 배정받고, 단계별 학습을 거쳐 종합평가(귀화용 포함)로 이어집니다. 이수·평가 결과가 곧 귀화 허가를 의미하지는 않습니다.',
      'videos.title': '참고 영상/자료',
      'videos.intro': '사용자가 제공한 재생목록·채널을 참고용으로 정리했습니다. 영상 자막·대본은 저장하지 않으며, 공식 자료가 아닙니다.',
      'waymaker.title': 'Waymaker 국적민원 코치',
      'waymaker.heading': '물어보고, 연습하세요',
      'waymaker.desc': '국적민원 안내 코치는 법령·안내를 구분해 설명하고, 귀화면접 코치는 입력한 답변을 점검해 더 자연스러운 예시와 후속 질문을 제안합니다. 음성 없이 텍스트로 진행됩니다.',
      'waymaker.note': '합격 여부를 예측하지 않으며, 개별 통지와 출입국외국인관서 안내가 항상 우선입니다.',
      'waymaker.ctaGuide': '국적민원 안내 코치 열기', 'waymaker.ctaInterview': '귀화면접 코치로 모의면접',
      'badge.official': '공식자료 기반', 'badge.notOfficial': '공식 기출 아님', 'badge.unofficialVideo': '비공식 참고자료',
      'footer.note': 'Paradiso는 공식 기관과 제휴 또는 소속 관계가 없습니다. 모든 안내는 학습 참고용이며, 최종 확인은 법무부·출입국외국인관서·하이코리아·1345를 통해 진행하세요.',
      'footer.back': '← 국적·귀화 홈으로',
      // dynamic labels
      'filter.all': '전체', 'who': '이런 분께', 'flowLabel': '일반적인 흐름', 'docNote': '서류 관련 유의사항',
      'relatedLaws': '관련 법령', 'relatedSources': '공식 출처', 'caution': '주의', 'confirmNeeded': '확인 필요',
      'caseVaries': '개별 사안별로 달라질 수 있음', 'viewFlow': '답변 흐름 보기', 'guidance': '답변 가이드',
      'goodStructure': '좋은 답변 구조', 'riskyPatterns': '피해야 할 답변', 'practiceWaymaker': 'Waymaker로 연습하기',
      'rooms.understand': '절차 이해', 'rooms.topics': '핵심 주제 학습', 'rooms.questions': '예상 질문 카드',
      'rooms.mock': '모의면접 연습', 'rooms.videos': '참고 영상/자료',
      'randomQ': '랜덤 질문', 'searchQ': '질문 검색', 'allCats': '전체 주제', 'allDiffs': '전체 난이도',
      'mock.todayQ': '오늘의 연습 질문', 'mock.next': '다음 질문', 'mock.placeholder': '여기에 답변을 한국어로 입력해 보세요. 이유와 경험을 함께 적으면 좋습니다.',
      'mock.checkLocal': '내 답변 점검하기', 'mock.startWaymaker': 'Waymaker 모의면접 시작', 'mock.retry': '답변 다시 쓰기',
      'mock.strengths': '좋았던 점', 'mock.improvements': '보완할 점', 'mock.risky': '조심할 표현',
      'mock.revised': '더 자연스러운 답변 예시', 'mock.followup': '다음 연습 질문', 'mock.tip': '학습 팁',
      'mock.loading': 'Waymaker가 답변을 검토하는 중…',
      'mock.aiFail': 'AI 피드백을 불러오지 못했습니다. 기본 점검 결과를 먼저 확인해 주세요.',
      'mock.localTitle': '기본 점검 결과 (오프라인)', 'mock.noAnswer': '먼저 답변을 입력해 주세요.',
      'understand.heading': '귀화면접·기본소양 준비, 어떻게 이어지나요?',
      'understand.body': '귀화 준비는 보통 사회통합프로그램(KIIP) 학습과 사전평가·종합평가, 그리고 귀화적격심사 과정의 면접으로 이어집니다. 면접은 정답을 외우는 자리가 아니라 기본소양과 의사소통을 확인하는 자리에 가깝습니다.',
      'understand.warn': '면접 대상·내용·면제 여부는 개별 사안과 통지에 따라 다릅니다. 여기 내용은 학습 참고용이며, 항상 개별 통지와 관할 출입국외국인관서 안내가 우선합니다.',
      'understand.steps': '준비 흐름 예시',
      'sourceLabel.official_kiip': 'KIIP 학습 연계', 'sourceLabel.official_socinet': '평가 안내 연계',
      'sourceLabel.practice': '연습문제', 'sourceLabel.internal_guidance': '면접 태도 가이드',
      'sourceLabel.official_law': '법령 참고', 'sourceLabel.official_notice': '공식 안내 참고', 'sourceLabel.video_reference_topic': '영상 참고 주제',
      'studyFocus': '학습 포인트', 'noResults': '조건에 맞는 결과가 없습니다.',
      'videoDisclaimer': '영상 자료는 비공식 참고자료이며, 실제 면접 질문 또는 법무부 공식 기출문제를 의미하지 않습니다.',
      'openLink': '바로가기', 'difficulty.easy': '쉬움', 'difficulty.medium': '보통', 'difficulty.hard': '어려움',
      'localCheck.tooShort': '답변이 너무 짧습니다. 이유와 구체적인 경험을 한 문장씩 더해보세요.',
      'localCheck.direct': '질문에 대한 직접 답변이 먼저 나오면 더 안정적입니다.',
      'localCheck.vague': '내용이 다소 막연합니다. 구체적인 예나 경험을 한 가지 더해보세요.',
      'localCheck.structure': '이유와 예시가 있어 답변 구조가 좋습니다.',
      'localCheck.length': '분량이 적절합니다. 핵심을 또박또박 전달하세요.',
      'localCheck.specific': '구체적인 경험·예시가 담겨 있어 설득력이 있습니다.',
      'localCheck.risky': '혜택·금전·의무 회피만 강조하는 표현은 피하는 편이 안전합니다.',
      'localCheck.okStart': '질문에 대한 답을 분명히 제시했습니다.',
      'rubric.title': '답변 점검 항목', 'rubric.direct': '직접 답변', 'rubric.specific': '구체적 경험·예시',
      'rubric.structure': '이유·구조', 'rubric.length': '적절한 분량', 'rubric.attitude': '안전한 표현',
      'rubric.ok': '충분', 'rubric.improve': '보완',
      'cautionCoach': '이 피드백은 연습용이며 실제 심사 결과를 보장하지 않습니다.'
    },
    en: {
      'hero.kicker': 'Nationality services & interview prep',
      'hero.title': 'Nationality services and naturalization interview prep, in one place',
      'hero.lead': 'Naturalization, nationality restoration, loss/renunciation, multiple nationality, the citizen oath and interview prep — review a flow close to your situation based on official law and guidance, then practice with questions and a mock interview.',
      'hero.ctaPrimary': 'Start interview prep', 'hero.ctaSecondary': 'Browse nationality services',
      'global.disclaimer': 'This is a study tool to help you check nationality services and prepare for the naturalization interview and basic-knowledge assessment. It does not guarantee any review outcome. Always confirm official guidance and individual notices with the Ministry of Justice / immigration office.',
      'about.title': 'Explore nationality services',
      'about.intro': 'Pick a service type to see what it is, who it is generally for, the typical flow, document cautions, related laws and official sources. Individual cases may differ.',
      'laws.title': 'Related laws & guidelines',
      'laws.intro': 'Browse the official sources behind nationality work by type. Local notices and secondary explainers are flagged separately. Open external links to read the originals.',
      'flow.title': 'Procedure & document flow',
      'flow.intro': 'Choose a type to see a general flow and document cautions. The exact order, documents and criteria follow the competent immigration office and may differ by case.',
      'interview.title': 'Naturalization interview study room',
      'interview.intro': 'Prepare step by step: understand the process, study core topics, browse practice questions, run a mock interview, and review reference videos. Every question is practice material, not a real or official past question.',
      'kiip.title': 'Pre-evaluation / comprehensive evaluation study flow',
      'kiip.intro': 'KIIP assigns a level via the pre-evaluation, then leads to the comprehensive evaluation (including the naturalization version). Completing it does not by itself mean naturalization approval.',
      'videos.title': 'Reference videos / materials',
      'videos.intro': 'User-provided playlists and channels, organized for reference only. No captions or transcripts are stored, and these are not official materials.',
      'waymaker.title': 'Waymaker nationality coach',
      'waymaker.heading': 'Ask, and practice',
      'waymaker.desc': 'The nationality guide coach explains while distinguishing law from guidance; the interview coach reviews your typed answer and suggests a more natural example and a follow-up question. It is text-first, no voice needed.',
      'waymaker.note': 'It never predicts pass/fail; individual notices and the immigration office always take priority.',
      'waymaker.ctaGuide': 'Open nationality guide coach', 'waymaker.ctaInterview': 'Mock interview with the coach',
      'badge.official': 'Based on official sources', 'badge.notOfficial': 'Not an official past question', 'badge.unofficialVideo': 'Unofficial reference',
      'footer.note': 'Paradiso is not affiliated with or part of any official body. All guidance is for study reference; confirm with the Ministry of Justice, immigration office, HiKorea, or 1345.',
      'footer.back': '← Back to nationality home',
      'filter.all': 'All', 'who': 'Who this is for', 'flowLabel': 'General flow', 'docNote': 'Document cautions',
      'relatedLaws': 'Related laws', 'relatedSources': 'Official sources', 'caution': 'Caution', 'confirmNeeded': 'Needs confirmation',
      'caseVaries': 'May vary by individual case', 'viewFlow': 'View answer flow', 'guidance': 'Answer guidance',
      'goodStructure': 'Good answer structure', 'riskyPatterns': 'Patterns to avoid', 'practiceWaymaker': 'Practice with Waymaker',
      'rooms.understand': 'Understand the process', 'rooms.topics': 'Core topics', 'rooms.questions': 'Practice questions',
      'rooms.mock': 'Mock interview', 'rooms.videos': 'Reference videos',
      'randomQ': 'Random question', 'searchQ': 'Search questions', 'allCats': 'All topics', 'allDiffs': 'All levels',
      'mock.todayQ': "Today's practice question", 'mock.next': 'Next question', 'mock.placeholder': 'Type your answer here. Adding a reason and an example helps.',
      'mock.checkLocal': 'Check my answer', 'mock.startWaymaker': 'Start Waymaker mock interview', 'mock.retry': 'Rewrite answer',
      'mock.strengths': 'Strengths', 'mock.improvements': 'To improve', 'mock.risky': 'Expressions to watch',
      'mock.revised': 'More natural example', 'mock.followup': 'Next practice question', 'mock.tip': 'Study tip',
      'mock.loading': 'Waymaker is reviewing your answer…',
      'mock.aiFail': 'Could not load AI feedback. Please check the basic results first.',
      'mock.localTitle': 'Basic check (offline)', 'mock.noAnswer': 'Please type an answer first.',
      'understand.heading': 'How does interview & basic-knowledge prep fit together?',
      'understand.body': 'Naturalization prep usually connects KIIP study, the pre/comprehensive evaluations, and the interview within the naturalization review. The interview checks basic knowledge and communication rather than memorized answers.',
      'understand.warn': 'Who is interviewed, the content, and any exemption depend on the individual case and notice. This is study reference only; your individual notice and the competent immigration office always take priority.',
      'understand.steps': 'Example prep flow',
      'sourceLabel.official_kiip': 'KIIP-linked', 'sourceLabel.official_socinet': 'Evaluation-linked',
      'sourceLabel.practice': 'Practice', 'sourceLabel.internal_guidance': 'Attitude guide',
      'sourceLabel.official_law': 'Law reference', 'sourceLabel.official_notice': 'Official notice reference', 'sourceLabel.video_reference_topic': 'Video topic',
      'studyFocus': 'Study focus', 'noResults': 'No matching results.',
      'videoDisclaimer': 'Video materials are unofficial references and do not represent real interview questions or official past questions from the Ministry of Justice.',
      'openLink': 'Open', 'difficulty.easy': 'Easy', 'difficulty.medium': 'Medium', 'difficulty.hard': 'Hard',
      'localCheck.tooShort': 'Your answer is very short. Try adding one sentence each for a reason and a concrete experience.',
      'localCheck.direct': 'It is steadier when a direct answer to the question comes first.',
      'localCheck.vague': 'It reads a little vague. Add one concrete example or experience.',
      'localCheck.structure': 'A reason and an example give your answer good structure.',
      'localCheck.length': 'The length is appropriate. Deliver the key point clearly.',
      'localCheck.specific': 'It includes a concrete experience or example, which is persuasive.',
      'localCheck.risky': 'It is safer to avoid emphasizing only benefits, money, or avoiding duties.',
      'localCheck.okStart': 'You stated a clear answer to the question.',
      'rubric.title': 'Answer rubric', 'rubric.direct': 'Direct answer', 'rubric.specific': 'Concrete example',
      'rubric.structure': 'Reason & structure', 'rubric.length': 'Adequate length', 'rubric.attitude': 'Safe wording',
      'rubric.ok': 'Good', 'rubric.improve': 'Improve',
      'cautionCoach': 'This feedback is for practice and does not guarantee any review outcome.'
    }
  };

  var lang = (function () {
    try {
      var s = (localStorage.getItem('paradiso:language') || '').toLowerCase();
      if (s.indexOf('en') === 0) return 'en';
      if (s.indexOf('ko') === 0) return 'ko';
    } catch (e) {}
    return (navigator.language || '').toLowerCase().indexOf('en') === 0 ? 'en' : 'ko';
  })();
  function t(key) { return (I18N[lang] && I18N[lang][key]) || (I18N.ko[key]) || key; }

  /* ----------------------------------------------------------- utilities */
  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }
  function el(id) { return document.getElementById(id); }
  function safeUrl(raw) {
    try { var u = new URL(raw); return (u.protocol === 'https:' || u.protocol === 'http:') ? u.href : '#'; }
    catch (e) { return '#'; }
  }
  function getJson(path) {
    return fetch(path, { cache: 'no-store' }).then(function (r) {
      if (!r.ok) throw new Error('fetch ' + path + ' ' + r.status); return r.json();
    });
  }

  // Mirror ai.html's API base resolution so the coach can reach the backend.
  var DEFAULT_API_BASE = 'https://web-production-14f9a.up.railway.app';
  var apiBase = (window.PARADISO_BACKEND_URL && window.PARADISO_BACKEND_URL.trim())
    || ((location.hostname === 'localhost' || location.hostname === '127.0.0.1' || location.protocol === 'file:') ? '' : DEFAULT_API_BASE);

  var CATEGORY_LABELS = {
    korean_language: { ko: '한국어 의사소통', en: 'Korean communication' },
    reason_for_naturalization: { ko: '귀화 동기', en: 'Reason for naturalization' },
    life_in_korea: { ko: '한국 생활 경험', en: 'Life in Korea' },
    korean_society: { ko: '대한민국 사회 기본 이해', en: 'Korean society' },
    democratic_order: { ko: '자유민주적 기본질서', en: 'Democratic order' },
    rights_and_duties: { ko: '권리와 의무', en: 'Rights & duties' },
    interview_attitude: { ko: '면접 태도', en: 'Interview attitude' },
    pre_evaluation_study: { ko: '사전평가/종합평가', en: 'Pre/comprehensive evaluation' }
  };
  function catLabel(c) { return (CATEGORY_LABELS[c] && CATEGORY_LABELS[c][lang]) || c; }

  var DATA = { guides: [], sources: [], questions: [], videos: [], topics: [] };
  var sourceById = {};

  /* ----------------------------------------------------------- i18n apply */
  function applyStatic() {
    document.documentElement.lang = lang;
    var nodes = document.querySelectorAll('[data-i18n]');
    for (var i = 0; i < nodes.length; i++) {
      var key = nodes[i].getAttribute('data-i18n');
      var val = t(key);
      if (val != null) nodes[i].textContent = val;
    }
    var lt = el('langToggle'); if (lt) { lt.textContent = lang === 'ko' ? 'EN' : '한국어'; }
  }

  /* --------------------------------------------------- 1. guide browsing */
  var guideFilter = 'all';
  var GUIDE_GROUPS = [
    { id: 'all', ko: '전체', en: 'All' },
    { id: 'naturalization', ko: '귀화', en: 'Naturalization', cats: ['naturalization_general', 'naturalization_simplified', 'naturalization_special', 'naturalization_marriage'] },
    { id: 'restoration', ko: '국적회복', en: 'Restoration', cats: ['nationality_restoration'] },
    { id: 'lossleave', ko: '국적상실/이탈', en: 'Loss / renunciation', cats: ['nationality_loss_report', 'nationality_renunciation', 'nationality_acquisition_report', 'nationality_retention'] },
    { id: 'multiple', ko: '복수국적', en: 'Multiple nationality', cats: ['multiple_nationality', 'foreign_nationality_non_exercise_pledge'] },
    { id: 'oath', ko: '국민선서', en: 'Oath', cats: ['oath_and_certificate'] },
    { id: 'interview', ko: '면접/평가', en: 'Interview / evaluation', cats: ['interview_review', 'kiip_evaluation', 'review_period_status'] }
  ];
  function groupOf(cat) {
    for (var i = 1; i < GUIDE_GROUPS.length; i++) if (GUIDE_GROUPS[i].cats.indexOf(cat) >= 0) return GUIDE_GROUPS[i].id;
    return 'other';
  }
  function renderGuideFilters() {
    var box = el('guideFilters'); box.innerHTML = '';
    GUIDE_GROUPS.forEach(function (g) {
      var b = document.createElement('button');
      b.className = 'ni-chip'; b.type = 'button';
      b.setAttribute('aria-pressed', guideFilter === g.id ? 'true' : 'false');
      b.textContent = g[lang] || g.ko;
      b.addEventListener('click', function () { guideFilter = g.id; renderGuideFilters(); renderGuides(); });
      box.appendChild(b);
    });
  }
  function renderGuides() {
    var q = (el('guideSearch').value || '').trim().toLowerCase();
    var grid = el('guideGrid'); grid.innerHTML = '';
    var list = DATA.guides.filter(function (g) {
      if (guideFilter !== 'all' && groupOf(g.category) !== guideFilter) return false;
      if (!q) return true;
      var hay = (g.title_ko + ' ' + g.short_summary_ko + ' ' + g.who_it_is_for_ko + ' ' + g.category).toLowerCase();
      return hay.indexOf(q) >= 0;
    });
    if (!list.length) { grid.innerHTML = '<p class="ni-empty">' + esc(t('noResults')) + '</p>'; return; }
    list.forEach(function (g) {
      var conf = g.source_confidence;
      var confBadge = conf === 'high'
        ? '<span class="ni-badge ni-badge-official">' + esc(t('badge.official')) + '</span>'
        : '<span class="ni-badge ni-badge-warn">' + esc(t('confirmNeeded')) + '</span>';
      var lawChips = (g.related_laws || []).concat(g.related_sources || []).map(function (id) {
        var s = sourceById[id]; if (!s) return '';
        return '<a class="ni-chip" href="' + safeUrl(s.url) + '" target="_blank" rel="noopener noreferrer">' + esc(s.title_ko) + ' ↗</a>';
      }).join('');
      var card = document.createElement('article');
      card.className = 'ni-card';
      card.innerHTML =
        '<div class="ni-card-meta">' + confBadge +
          '<span class="ni-badge ni-badge-neutral">' + esc(t('caseVaries')) + '</span></div>' +
        '<h3>' + esc(g.title_ko) + '</h3>' +
        '<p>' + esc(g.short_summary_ko) + '</p>' +
        '<p><b>' + esc(t('who')) + ':</b> ' + esc(g.who_it_is_for_ko) + '</p>' +
        '<details class="ni-disclosure"><summary>' + esc(t('viewFlow')) + '</summary><div>' +
          '<div><b>' + esc(t('flowLabel')) + '</b><ol class="ni-flow" style="margin-top:0.4rem;">' +
            (g.typical_flow_ko || []).map(function (s) { return '<li>' + esc(s) + '</li>'; }).join('') + '</ol></div>' +
          '<div class="ni-note"><b>' + esc(t('docNote')) + ':</b> ' + esc(g.key_documents_note_ko) + '</div>' +
          '<p class="ni-source-caution"><b>' + esc(t('caution')) + ':</b> ' + esc(g.caution_ko) + '</p>' +
          (lawChips ? '<div class="ni-card-foot"><span class="ni-badge ni-badge-neutral">' + esc(t('relatedSources')) + '</span>' + lawChips + '</div>' : '') +
        '</div></details>';
      grid.appendChild(card);
    });
  }

  /* --------------------------------------------------- 2. source explorer */
  var SOURCE_TABS = [
    { id: 'all', ko: '전체', en: 'All' },
    { id: 'law', ko: '법령', en: 'Law', kinds: ['law'] },
    { id: 'decree', ko: '시행령/시행규칙', en: 'Decree / Rule', kinds: ['enforcement_decree', 'enforcement_rule'] },
    { id: 'admin', ko: '행정규칙/지침', en: 'Admin rules', kinds: ['administrative_rule'] },
    { id: 'moj', ko: '법무부 안내', en: 'MOJ guidance', kinds: ['official_policy_page', 'civil_affairs_guide'] },
    { id: 'service', ko: '하이코리아/SOCINET', en: 'HiKorea / SOCINET', kinds: ['evaluation_guide'] },
    { id: 'local', ko: '지역 공지 예시', en: 'Local notices', kinds: ['local_notice'] },
    { id: 'reference', ko: '참고/보조', en: 'Reference', kinds: ['official_notice', 'secondary_explainer'] }
  ];
  var sourceTab = 'all';
  function kindLabel(kind) {
    var m = { law: '법령', enforcement_decree: '시행령', enforcement_rule: '시행규칙', administrative_rule: '행정규칙', official_notice: '공식 고시', official_policy_page: '정책 안내', civil_affairs_guide: '민원 안내', evaluation_guide: '평가 안내', local_notice: '지역 공지', secondary_explainer: '보조 설명' };
    return m[kind] || kind;
  }
  function levelBadge(level) {
    if (level === 'primary') return '<span class="ni-badge ni-badge-official">1차 공식</span>';
    if (level === 'local_notice') return '<span class="ni-badge ni-badge-warn">지역 공지 예시</span>';
    if (level === 'reference') return '<span class="ni-badge ni-badge-neutral">참고</span>';
    return '<span class="ni-badge ni-badge-neutral">2차</span>';
  }
  function renderSourceTabs() {
    var box = el('sourceTabs'); box.innerHTML = '';
    SOURCE_TABS.forEach(function (tb) {
      var b = document.createElement('button');
      b.className = 'ni-tab'; b.type = 'button'; b.setAttribute('role', 'tab');
      b.setAttribute('aria-selected', sourceTab === tb.id ? 'true' : 'false');
      b.textContent = tb[lang] || tb.ko;
      b.addEventListener('click', function () { sourceTab = tb.id; renderSourceTabs(); renderSources(); });
      box.appendChild(b);
    });
  }
  function renderSources() {
    var tab = SOURCE_TABS.filter(function (x) { return x.id === sourceTab; })[0];
    var list = DATA.sources.filter(function (s) {
      if (sourceTab === 'all') return true;
      return tab.kinds && tab.kinds.indexOf(s.source_kind) >= 0;
    });
    var box = el('sourceList');
    if (!list.length) { box.innerHTML = '<p class="ni-empty">' + esc(t('noResults')) + '</p>'; return; }
    box.innerHTML = list.map(function (s) {
      var localWarn = (s.official_level === 'local_notice' || s.source_kind === 'local_notice')
        ? '<p class="ni-source-caution">⚠ ' + esc('지역 공지 예시 — 전국 공통 규칙으로 일반화할 수 없습니다.') + '</p>' : '';
      var secWarn = (s.source_kind === 'secondary_explainer')
        ? '<p class="ni-source-caution">⚠ ' + esc('보조 설명자료 — 1차 법령이 아닙니다.') + '</p>' : '';
      return '<div class="ni-source-card">' +
        '<div class="ni-source-top">' +
          '<a class="ni-source-link" href="' + safeUrl(s.url) + '" target="_blank" rel="noopener noreferrer">' + esc(s.title_ko) + '</a>' +
          levelBadge(s.official_level) +
          '<span class="ni-badge ni-badge-neutral">' + esc(kindLabel(s.source_kind)) + '</span>' +
        '</div>' +
        '<p class="ni-source-summary">' + esc(s.summary_ko) + '</p>' +
        localWarn + secWarn +
        '<p class="ni-source-caution">' + esc(s.caution_ko) + '</p>' +
        '<div class="ni-source-meta"><span>' + esc(s.publisher) + '</span><span>확인일 ' + esc(s.checked_at) + '</span>' +
          '<span>' + esc((s.topic_tags || []).slice(0, 4).join(' · ')) + '</span></div>' +
      '</div>';
    }).join('');
  }

  /* --------------------------------------------------- 3. procedure flow */
  function renderFlowSelect() {
    var sel = el('flowSelect'); sel.innerHTML = '';
    DATA.guides.forEach(function (g) {
      var o = document.createElement('option'); o.value = g.id; o.textContent = g.title_ko; sel.appendChild(o);
    });
    sel.addEventListener('change', function () { renderFlow(sel.value); });
    if (DATA.guides.length) renderFlow(DATA.guides[0].id);
  }
  function renderFlow(id) {
    var g = DATA.guides.filter(function (x) { return x.id === id; })[0];
    var box = el('flowView'); if (!g) { box.innerHTML = ''; return; }
    var srcChips = (g.related_sources || []).map(function (sid) {
      var s = sourceById[sid]; if (!s) return '';
      return '<a class="ni-chip" href="' + safeUrl(s.url) + '" target="_blank" rel="noopener noreferrer">' + esc(s.title_ko) + ' ↗</a>';
    }).join('');
    box.innerHTML =
      '<div class="ni-card" style="gap:0.9rem;">' +
        '<div class="ni-card-meta"><span class="ni-badge ni-badge-neutral">' + esc('일반적인 흐름') + '</span>' +
          '<span class="ni-badge ni-badge-warn">' + esc('관할 출입국외국인관서 안내 우선') + '</span></div>' +
        '<h3>' + esc(g.title_ko) + '</h3>' +
        '<ol class="ni-flow">' + (g.typical_flow_ko || []).map(function (s) { return '<li>' + esc(s) + '</li>'; }).join('') + '</ol>' +
        '<div class="ni-note"><b>서류 관련 유의사항:</b> ' + esc(g.key_documents_note_ko) + '<br><span style="color:var(--cyT);">공식 안내 확인 필요 — 완전한 체크리스트가 아닙니다.</span></div>' +
        '<p class="ni-source-caution"><b>' + esc(t('caution')) + ':</b> ' + esc(g.caution_ko) + '</p>' +
        (srcChips ? '<div class="ni-card-foot"><span class="ni-badge ni-badge-neutral">' + esc(t('relatedSources')) + '</span>' + srcChips + '</div>' : '') +
      '</div>';
  }

  /* ------------------------------------------------- 4. interview room */
  var ROOM_TABS = [
    { id: 'understand', key: 'rooms.understand', panel: 'panel-understand' },
    { id: 'topics', key: 'rooms.topics', panel: 'panel-topics' },
    { id: 'questions', key: 'rooms.questions', panel: 'panel-questions' },
    { id: 'mock', key: 'rooms.mock', panel: 'panel-mock' },
    { id: 'videos', key: 'rooms.videos', panel: 'panel-videos' }
  ];
  var activeRoom = 'understand';
  function renderRoomTabs() {
    var box = el('roomTabs'); box.innerHTML = '';
    ROOM_TABS.forEach(function (tb) {
      var b = document.createElement('button');
      b.className = 'ni-roomtab'; b.type = 'button'; b.setAttribute('role', 'tab');
      b.setAttribute('aria-selected', activeRoom === tb.id ? 'true' : 'false');
      b.textContent = t(tb.key);
      b.addEventListener('click', function () { activeRoom = tb.id; selectRoom(); });
      box.appendChild(b);
    });
  }
  function selectRoom() {
    ROOM_TABS.forEach(function (tb) {
      el(tb.panel).hidden = (tb.id !== activeRoom);
    });
    renderRoomTabs();
  }

  function renderUnderstand() {
    var steps = lang === 'en'
      ? ['Study with KIIP / self-study', 'Pre-evaluation assigns a level', 'Step-by-step learning', 'Comprehensive evaluation (incl. naturalization)', 'Interview within the naturalization review', 'Result reflected as part of the whole review']
      : ['사회통합프로그램(KIIP)·자율 학습', '사전평가로 단계 배정', '단계별 학습', '종합평가(귀화용 포함)', '귀화적격심사 과정의 면접', '전체 심사의 일부로 결과 반영'];
    el('panel-understand').innerHTML =
      '<div class="ni-card" style="gap:0.8rem;max-width:760px;">' +
        '<h3>' + esc(t('understand.heading')) + '</h3>' +
        '<p>' + esc(t('understand.body')) + '</p>' +
        '<div><b>' + esc(t('understand.steps')) + '</b><ol class="ni-flow" style="margin-top:0.5rem;">' +
          steps.map(function (s) { return '<li>' + esc(s) + '</li>'; }).join('') + '</ol></div>' +
        '<div class="ni-callout" role="note"><span class="ni-callout-icon" aria-hidden="true">⚠</span><p>' + esc(t('understand.warn')) + '</p></div>' +
      '</div>';
  }

  function renderTopics() {
    var html = '<div class="ni-grid">' + DATA.topics.map(function (tp) {
      var focus = (tp.study_focus_ko || []).map(function (f) { return '<span class="ni-chip">' + esc(f) + '</span>'; }).join('');
      return '<article class="ni-card">' +
        '<div class="ni-card-meta"><span class="ni-badge ni-badge-neutral">' + esc(catLabel(tp.category)) + '</span></div>' +
        '<h3>' + esc(tp.title_ko) + '</h3>' +
        '<p>' + esc(tp.summary_ko) + '</p>' +
        (focus ? '<div class="ni-card-foot"><span class="ni-badge ni-badge-neutral">' + esc(t('studyFocus')) + '</span>' + focus + '</div>' : '') +
      '</article>';
    }).join('') + '</div>';
    el('panel-topics').innerHTML = html;
  }

  /* practice question cards */
  var qCat = 'all', qDiff = 'all';
  function diffBadge(d) { return '<span class="ni-badge ni-badge-diff ni-badge-' + d + '">' + esc(t('difficulty.' + d)) + '</span>'; }
  function questionCardHtml(q) {
    var bad = (q.bad_answer_patterns || []).map(function (b) { return esc(b); }).join(' · ');
    var labels = (q.labels || []).map(function (l) { return '<span class="ni-badge ni-badge-warn">' + esc(l) + '</span>'; }).join('');
    var enLine = (lang === 'en' && q.question_en) ? '<p class="ni-q-en">' + esc(q.question_en) + '</p>' : '';
    return '<article class="ni-q-card">' +
      '<div class="ni-q-top"><span class="ni-badge ni-badge-neutral">' + esc(catLabel(q.category)) + '</span>' + diffBadge(q.difficulty) + labels + '</div>' +
      '<p class="ni-q-text">' + esc(q.question_ko) + '</p>' + enLine +
      '<details class="ni-disclosure"><summary>' + esc(t('guidance')) + '</summary><div>' +
        '<p class="ni-q-detail"><b>' + esc(t('guidance')) + ':</b> ' + esc(q.answer_guidance_ko) + '</p>' +
        '<p class="ni-q-detail"><b>' + esc(t('goodStructure')) + ':</b> ' + esc(q.good_answer_structure_ko) + '</p>' +
        (bad ? '<p class="ni-q-bad"><b>' + esc(t('riskyPatterns')) + ':</b> ' + bad + '</p>' : '') +
      '</div></details>' +
      '<div class="ni-card-foot"><button class="ni-btn ni-btn-sm ni-btn-primary" type="button" data-practice="' + esc(q.id) + '">' + esc(t('practiceWaymaker')) + '</button></div>' +
    '</article>';
  }
  function renderQuestionsPanel() {
    var cats = Object.keys(CATEGORY_LABELS);
    var catOpts = '<option value="all">' + esc(t('allCats')) + '</option>' + cats.map(function (c) { return '<option value="' + c + '">' + esc(catLabel(c)) + '</option>'; }).join('');
    var diffOpts = '<option value="all">' + esc(t('allDiffs')) + '</option>' + ['easy', 'medium', 'hard'].map(function (d) { return '<option value="' + d + '">' + esc(t('difficulty.' + d)) + '</option>'; }).join('');
    el('panel-questions').innerHTML =
      '<div class="ni-filterbar">' +
        '<input class="ni-search" id="qSearch" type="search" placeholder="' + esc(t('searchQ')) + '" aria-label="' + esc(t('searchQ')) + '">' +
        '<label class="sr-only" for="qCat">' + esc(t('allCats')) + '</label><select class="ni-search" id="qCat" style="flex:0 1 180px;">' + catOpts + '</select>' +
        '<label class="sr-only" for="qDiff">' + esc(t('allDiffs')) + '</label><select class="ni-search" id="qDiff" style="flex:0 1 150px;">' + diffOpts + '</select>' +
        '<button class="ni-btn ni-btn-sm" id="qRandom" type="button">🎲 ' + esc(t('randomQ')) + '</button>' +
      '</div><div class="ni-grid" id="qGrid"></div>';
    el('qSearch').addEventListener('input', renderQuestionGrid);
    el('qCat').addEventListener('change', function () { qCat = this.value; renderQuestionGrid(); });
    el('qDiff').addEventListener('change', function () { qDiff = this.value; renderQuestionGrid(); });
    el('qRandom').addEventListener('click', function () {
      var pool = filteredQuestions(); if (!pool.length) return;
      var pick = pool[Math.floor(Math.random() * pool.length)];
      el('qGrid').innerHTML = questionCardHtml(pick);
    });
    renderQuestionGrid();
  }
  function filteredQuestions() {
    var s = (el('qSearch') && el('qSearch').value || '').trim().toLowerCase();
    return DATA.questions.filter(function (q) {
      if (qCat !== 'all' && q.category !== qCat) return false;
      if (qDiff !== 'all' && q.difficulty !== qDiff) return false;
      if (s && (q.question_ko + ' ' + (q.question_en || '') + ' ' + q.answer_guidance_ko).toLowerCase().indexOf(s) < 0) return false;
      return true;
    });
  }
  function renderQuestionGrid() {
    var list = filteredQuestions();
    var grid = el('qGrid');
    grid.innerHTML = list.length ? list.map(questionCardHtml).join('') : '<p class="ni-empty">' + esc(t('noResults')) + '</p>';
  }

  /* videos panel (shared markup with top-level section) */
  function videoCardsInner() {
    return DATA.videos.map(function (v) {
      var topics = (v.derived_topics || []).map(function (d) { return '<span class="ni-chip">' + esc(d) + '</span>'; }).join('');
      var kindMap = { playlist: '재생목록', channel: '채널', video: '영상' };
      return '<article class="ni-video-card">' +
        '<div class="ni-card-meta"><span class="ni-badge ni-badge-neutral">' + esc(kindMap[v.source_kind] || v.source_kind) + '</span>' +
          '<span class="ni-badge ni-badge-warn">' + esc(t('badge.unofficialVideo')) + '</span></div>' +
        '<h3>' + esc(v.title) + (v.channel ? ' · ' + esc(v.channel) : '') + '</h3>' +
        '<p>' + esc(v.notes_ko) + '</p>' +
        (topics ? '<div class="ni-card-foot">' + topics + '</div>' : '') +
        '<a class="ni-btn ni-btn-sm" href="' + safeUrl(v.url) + '" target="_blank" rel="noopener noreferrer">' + esc(t('openLink')) + ' ↗</a>' +
        '<p class="ni-video-disclaimer">' + esc(t('videoDisclaimer')) + '</p>' +
      '</article>';
    }).join('');
  }
  function renderVideos() {
    var inner = DATA.videos.length ? videoCardsInner() : '<p class="ni-empty">' + esc(t('noResults')) + '</p>';
    el('videoGrid').innerHTML = inner;
    el('panel-videos').innerHTML = '<div class="ni-grid">' + inner + '</div>';
  }

  /* ----------------------------------------------- mock interview engine */
  var mockQ = null;
  function pickMockQuestion(prev) {
    var pool = DATA.questions;
    if (prev) pool = pool.filter(function (q) { return q.id !== prev; });
    return pool[Math.floor(Math.random() * pool.length)];
  }
  function renderMockPanel() {
    el('panel-mock').innerHTML =
      '<div class="ni-mock">' +
        '<div class="ni-mock-q" id="mockQBox"></div>' +
        '<label class="sr-only" for="mockAnswer">답변 입력</label>' +
        '<textarea class="ni-textarea" id="mockAnswer" placeholder="' + esc(t('mock.placeholder')) + '"></textarea>' +
        '<div class="ni-mock-actions">' +
          '<button class="ni-btn ni-btn-primary" id="mockWaymaker" type="button">' + esc(t('mock.startWaymaker')) + '</button>' +
          '<button class="ni-btn" id="mockLocal" type="button">' + esc(t('mock.checkLocal')) + '</button>' +
          '<button class="ni-btn" id="mockNext" type="button">' + esc(t('mock.next')) + '</button>' +
          '<button class="ni-btn" id="mockRetry" type="button">' + esc(t('mock.retry')) + '</button>' +
        '</div>' +
        '<div class="ni-feedback" id="mockFeedback" aria-live="polite"></div>' +
      '</div>';
    if (!mockQ) mockQ = pickMockQuestion(null);
    drawMockQuestion();
    el('mockNext').addEventListener('click', function () { mockQ = pickMockQuestion(mockQ.id); drawMockQuestion(); el('mockAnswer').value = ''; el('mockFeedback').innerHTML = ''; });
    el('mockRetry').addEventListener('click', function () { el('mockAnswer').value = ''; el('mockFeedback').innerHTML = ''; el('mockAnswer').focus(); });
    el('mockLocal').addEventListener('click', function () { showLocalFeedback(); });
    el('mockWaymaker').addEventListener('click', function () { requestCoachFeedback(); });
  }
  function drawMockQuestion() {
    var enLine = (lang === 'en' && mockQ.question_en) ? '<p class="ni-q-en">' + esc(mockQ.question_en) + '</p>' : '';
    el('mockQBox').innerHTML =
      '<div class="ni-q-top"><span class="ni-badge ni-badge-neutral">' + esc(t('mock.todayQ')) + '</span>' +
        '<span class="ni-badge ni-badge-neutral">' + esc(catLabel(mockQ.category)) + '</span>' + diffBadge(mockQ.difficulty) +
        '<span class="ni-badge ni-badge-warn">' + esc(t('badge.notOfficial')) + '</span></div>' +
      '<p class="ni-q-text">' + esc(mockQ.question_ko) + '</p>' + enLine +
      '<p class="ni-q-detail">' + esc(mockQ.answer_guidance_ko) + '</p>';
  }

  // Conservative risky-wording detector: only benefit/money/duty-avoidance framing.
  var RISKY = ['혜택만', '돈 때문', '돈을 벌', '공짜', '복지 때문', '병역 피', '병역을 피', '세금 안', '세금을 안', '의무는 싫', '편하게 살려'];
  var STRUCTURE = ['왜냐하면', '때문', '예를 들어', '그래서', '첫째', '먼저', '예를들어'];
  // Concrete-experience markers — used by the richer rubric (구체성 dimension).
  var SPECIFIC = ['예를 들어', '예를들어', '제가', '저는', '경험', '때', '에서', '함께', '직접', '실제'];
  function analyzeAnswer(answer) {
    var a = (answer || '').trim();
    var len = a.replace(/\s/g, '').length;
    var risky = RISKY.filter(function (w) { return a.indexOf(w) >= 0; });
    var hasStructure = STRUCTURE.some(function (w) { return a.indexOf(w) >= 0; });
    var specificHits = SPECIFIC.filter(function (w) { return a.indexOf(w) >= 0; }).length;
    var hasSpecific = specificHits >= 2 || /\d/.test(a);
    var sentences = a.split(/[.!?。\n]/).filter(function (s) { return s.trim().length > 0; });
    var direct = len >= 25 && sentences.length >= 1;
    return {
      empty: len === 0, tooShort: len > 0 && len < 25, vague: len >= 25 && sentences.length < 2 && !hasStructure,
      hasStructure: hasStructure, hasSpecific: hasSpecific, direct: direct, risky: risky, len: len,
      adequateLength: len >= 40
    };
  }
  // Score-free rubric: each dimension is 충분(ok) or 보완(improve). Never pass/fail.
  function rubricRows(r) {
    return [
      { key: 'rubric.direct', ok: r.direct },
      { key: 'rubric.specific', ok: r.hasSpecific },
      { key: 'rubric.structure', ok: r.hasStructure },
      { key: 'rubric.length', ok: r.adequateLength },
      { key: 'rubric.attitude', ok: r.risky.length === 0 }
    ];
  }
  function rubricHtml(r) {
    var rows = rubricRows(r).map(function (row) {
      var mark = row.ok ? '✓' : '△';
      var tag = row.ok ? t('rubric.ok') : t('rubric.improve');
      var cls = row.ok ? 'ni-badge-easy' : 'ni-badge-medium';
      return '<li style="display:flex;justify-content:space-between;gap:0.5rem;align-items:center;">' +
        '<span>' + mark + ' ' + esc(t(row.key)) + '</span>' +
        '<span class="ni-badge ni-badge-diff ' + cls + '">' + esc(tag) + '</span></li>';
    }).join('');
    return '<div class="ni-fb-card"><h4>' + esc(t('rubric.title')) + '</h4><ul style="list-style:none;padding:0;margin:0;display:grid;gap:0.35rem;">' + rows + '</ul></div>';
  }
  function buildLocalFeedback(r) {
    var strengths = [], improvements = [], risky = [];
    if (r.adequateLength) strengths.push(t('localCheck.length')); else if (r.tooShort) improvements.push(t('localCheck.tooShort'));
    if (r.hasSpecific) strengths.push(t('localCheck.specific')); else improvements.push(t('localCheck.vague'));
    if (r.hasStructure) strengths.push(t('localCheck.structure')); else improvements.push(t('localCheck.direct'));
    if (r.risky.length) risky.push(t('localCheck.risky') + ' (' + r.risky.join(', ') + ')');
    return { strengths: strengths, improvements: improvements, risky: risky };
  }
  function showLocalFeedback() {
    var ans = el('mockAnswer').value;
    var box = el('mockFeedback');
    var r = analyzeAnswer(ans);
    if (r.empty) { box.innerHTML = '<div class="ni-fb-card ni-fb-improve">' + esc(t('mock.noAnswer')) + '</div>'; return; }
    var fb = buildLocalFeedback(r);
    box.innerHTML = localFeedbackHtml(fb.strengths, fb.improvements, fb.risky, r);
  }
  function localFeedbackHtml(strengths, improvements, risky, r) {
    var html = '<div class="ni-fb-card"><h4>' + esc(t('mock.localTitle')) + '</h4></div>';
    if (r) html += rubricHtml(r);
    if (strengths.length) html += '<div class="ni-fb-card ni-fb-good"><h4>' + esc(t('mock.strengths')) + '</h4><ul>' + strengths.map(function (s) { return '<li>' + esc(s) + '</li>'; }).join('') + '</ul></div>';
    if (improvements.length) html += '<div class="ni-fb-card ni-fb-improve"><h4>' + esc(t('mock.improvements')) + '</h4><ul>' + improvements.map(function (s) { return '<li>' + esc(s) + '</li>'; }).join('') + '</ul></div>';
    if (risky.length) html += '<div class="ni-fb-card ni-fb-risk"><h4>' + esc(t('mock.risky')) + '</h4><ul>' + risky.map(function (s) { return '<li>' + esc(s) + '</li>'; }).join('') + '</ul></div>';
    html += '<p class="ni-fb-meta">' + esc(t('cautionCoach')) + '</p>';
    return html;
  }

  // Waymaker coach: structured request with timeout + graceful fallback.
  function requestCoachFeedback() {
    var ans = el('mockAnswer').value;
    var box = el('mockFeedback');
    if (analyzeAnswer(ans).empty) { box.innerHTML = '<div class="ni-fb-card ni-fb-improve">' + esc(t('mock.noAnswer')) + '</div>'; return; }
    box.innerHTML = '<div class="ni-loading"><span class="ni-spinner" aria-hidden="true"></span>' + esc(t('mock.loading')) + '</div>';
    var controller = new AbortController();
    var timer = setTimeout(function () { controller.abort(); }, 14000);
    var payload = {
      mode: 'naturalization_interview_prep', lang: lang,
      category: mockQ.category, difficulty: mockQ.difficulty,
      question: mockQ.question_ko, answer: ans,
      is_official_past_question: false,
      disclaimer: 'practice guidance only; not official adjudication'
    };
    fetch(apiBase + '/api/nationality-coach', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload), signal: controller.signal
    }).then(function (r) { if (!r.ok) throw new Error('coach ' + r.status); return r.json(); })
      .then(function (data) { clearTimeout(timer); renderCoachFeedback(data); })
      .catch(function () { clearTimeout(timer); renderCoachFallback(); });
  }
  function listCard(cls, title, items) {
    if (!items || !items.length) return '';
    return '<div class="ni-fb-card ' + cls + '"><h4>' + esc(title) + '</h4><ul>' + items.map(function (s) { return '<li>' + esc(s) + '</li>'; }).join('') + '</ul></div>';
  }
  function renderCoachFeedback(d) {
    var box = el('mockFeedback');
    var html = '';
    html += listCard('ni-fb-good', t('mock.strengths'), d.strengths);
    html += listCard('ni-fb-improve', t('mock.improvements'), d.improvements);
    if (d.riskyExpressions && d.riskyExpressions.length) html += listCard('ni-fb-risk', t('mock.risky'), d.riskyExpressions);
    if (d.revisedAnswer) html += '<div class="ni-fb-card ni-fb-revised"><h4>' + esc(t('mock.revised')) + '</h4><p>' + esc(d.revisedAnswer) + '</p></div>';
    if (d.followUpQuestion) html += '<div class="ni-fb-card"><h4>' + esc(t('mock.followup')) + '</h4><p>' + esc(d.followUpQuestion) + '</p></div>';
    if (d.studyTip) html += '<div class="ni-fb-card"><h4>' + esc(t('mock.tip')) + '</h4><p>' + esc(d.studyTip) + '</p></div>';
    html += '<p class="ni-fb-meta">' + esc(d.caution || t('cautionCoach')) + (d.provider ? ' · ' + esc(d.provider) : '') + '</p>';
    if (!html) { renderCoachFallback(); return; }
    box.innerHTML = html;
  }
  function renderCoachFallback() {
    // Backend unavailable: never infinite-load. Show notice + local rubric feedback.
    var r = analyzeAnswer(el('mockAnswer').value);
    var fb = buildLocalFeedback(r);
    el('mockFeedback').innerHTML =
      '<div class="ni-fb-card ni-fb-improve">' + esc(t('mock.aiFail')) + '</div>' +
      localFeedbackHtml(fb.strengths, fb.improvements, fb.risky, r);
  }

  /* practice CTA from question cards -> open mock tab seeded with the question */
  function practiceWithQuestion(id) {
    var q = DATA.questions.filter(function (x) { return x.id === id; })[0];
    if (!q) return;
    mockQ = q; activeRoom = 'mock'; selectRoom(); renderMockPanel();
    var box = el('mockFeedback'); if (box) box.innerHTML = '';
    document.getElementById('interview').scrollIntoView({ behavior: 'smooth', block: 'start' });
  }

  /* ----------------------------------------------------- 5. kiip flow */
  function renderKiip() {
    var g = DATA.guides.filter(function (x) { return x.category === 'kiip_evaluation'; })[0];
    var steps = g ? g.typical_flow_ko : [];
    el('kiipFlow').innerHTML = steps.map(function (s) { return '<li>' + esc(s) + '</li>'; }).join('');
    var ids = g ? (g.related_sources || []) : ['socinet', 'kiiptest', 'moj-socinet-prog'];
    el('kiipSources').innerHTML = '<div class="ni-card-foot"><span class="ni-badge ni-badge-neutral">' + esc(t('relatedSources')) + '</span>' +
      ids.map(function (sid) { var s = sourceById[sid]; return s ? '<a class="ni-chip" href="' + safeUrl(s.url) + '" target="_blank" rel="noopener noreferrer">' + esc(s.title_ko) + ' ↗</a>' : ''; }).join('') + '</div>';
  }

  /* --------------------------------------------------------- bootstrapping */
  function wireGlobal() {
    el('langToggle').addEventListener('click', function () {
      lang = (lang === 'ko') ? 'en' : 'ko';
      try { localStorage.setItem('paradiso:language', lang); } catch (e) {}
      renderAll();
    });
    el('brightToggle').addEventListener('click', function () {
      var dark = document.body.getAttribute('data-theme') === 'dark';
      if (dark) document.body.removeAttribute('data-theme'); else document.body.setAttribute('data-theme', 'dark');
      try { localStorage.setItem('paradiso:brightness', dark ? 'light' : 'dark'); } catch (e) {}
    });
    el('guideSearch').addEventListener('input', renderGuides);
    // Delegate practice CTAs (question cards live in a dynamic grid).
    document.addEventListener('click', function (e) {
      var btn = e.target.closest('[data-practice]');
      if (btn) practiceWithQuestion(btn.getAttribute('data-practice'));
    });
  }

  function renderAll() {
    applyStatic();
    renderGuideFilters(); renderGuides();
    renderSourceTabs(); renderSources();
    renderFlow(el('flowSelect').value || (DATA.guides[0] && DATA.guides[0].id));
    renderRoomTabs(); selectRoom();
    renderUnderstand(); renderTopics(); renderQuestionsPanel(); renderMockPanel(); renderVideos();
    renderKiip();
  }

  function boot() {
    Promise.all([
      getJson('data/nationality_service_guides.json'),
      getJson('data/nationality_service_sources.json'),
      getJson('data/naturalization_interview_questions.json'),
      getJson('data/naturalization_video_sources.json'),
      getJson('data/naturalization_learning_topics.json')
    ]).then(function (res) {
      DATA.guides = res[0].guides || [];
      DATA.sources = res[1].sources || [];
      DATA.questions = res[2].questions || [];
      DATA.videos = res[3].videos || [];
      DATA.topics = res[4].topics || [];
      DATA.sources.forEach(function (s) { sourceById[s.id] = s; });
      wireGlobal();
      renderFlowSelect();
      renderAll();
    }).catch(function (err) {
      var m = document.getElementById('main');
      if (m) m.insertAdjacentHTML('afterbegin', '<div class="ni-wrap" style="padding:2rem 0;"><p class="ni-empty">데이터를 불러오지 못했습니다. 페이지를 새로고침해 주세요. / Could not load data. Please refresh.</p></div>');
      if (window.console) console.error(err);
    });
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot);
  else boot();
})();
