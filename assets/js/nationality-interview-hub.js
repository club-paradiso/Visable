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
      'footer.note': 'New Home by Paradiso는 공식 기관과 제휴 또는 소속 관계가 없습니다. 모든 안내는 학습 참고용이며, 최종 확인은 법무부·출입국외국인관서·하이코리아·1345를 통해 진행하세요.',
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
      'footer.note': 'New Home by Paradiso is not affiliated with or part of any official body. All guidance is for study reference; confirm with the Ministry of Justice, immigration office, HiKorea, or 1345.',
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
    },
    'zh-CN': {
      'hero.kicker': '国籍民愿·归化面试准备',
      'hero.title': '国籍民愿与归化面试准备，集于一处',
      'hero.lead': '从归化、国籍恢复、国籍丧失·脱离、复数国籍、国民宣誓到归化面试准备 —— 以官方法令和指引为基础，查看与您情况相近的流程，并通过练习题和模拟面试进行准备。',
      'hero.ctaPrimary': '开始归化面试学习', 'hero.ctaSecondary': '浏览国籍民愿',
      'global.disclaimer': '本功能是帮助确认国籍民愿、准备归化面试及基本素养的学习工具，不保证实际审查结果。官方指引和个别通知请优先确认法务部·出入境外国人机关的指引。',
      'about.title': '了解国籍民愿',
      'about.intro': '选择您感兴趣的国籍民愿类型，确认它是什么民愿、面向谁、一般流程、材料注意事项、相关法令与官方出处。个别情形可能有所不同。',
      'laws.title': '相关法令·指针',
      'laws.intro': '请按类别查看作为国籍业务依据的官方出处。地区公告或辅助说明资料会另行标示。可通过外部链接直接查看原文。',
      'flow.title': '程序·材料流程',
      'flow.intro': '选择类型后可查看一般流程和材料相关注意事项。准确的顺序·材料·标准以管辖出入境外国人机关的指引为准，并可能因个别情形而不同。',
      'interview.title': '归化面试备考学习室',
      'interview.intro': '从理解程序、学习核心主题、预想问题卡片、模拟面试练习到参考视频，分阶段进行准备。所有问题均为学习用练习题，并非实际面试题或官方历年真题。',
      'kiip.title': '事前评价/综合评价学习流程',
      'kiip.intro': '社会融合项目（KIIP）通过事前评价分配阶段，经过分阶段学习后进入综合评价（含归化用）。修完·评价结果并不等同于获得归化许可。',
      'videos.title': '参考视频/资料',
      'videos.intro': '已将用户提供的播放列表·频道整理为参考。不保存视频字幕·脚本，且非官方资料。',
      'waymaker.title': 'Waymaker 国籍民愿教练',
      'waymaker.heading': '提问并练习',
      'waymaker.desc': '国籍民愿指引教练会区分法令·指引进行说明；归化面试教练会检查您输入的答复，并建议更自然的示例和后续问题。全程以文字进行，无语音。',
      'waymaker.note': '不预测是否合格，个别通知和出入境外国人机关的指引始终优先。',
      'waymaker.ctaGuide': '打开国籍民愿指引教练', 'waymaker.ctaInterview': '用归化面试教练模拟面试',
      'badge.official': '基于官方资料', 'badge.notOfficial': '非官方真题', 'badge.unofficialVideo': '非官方参考资料',
      'footer.note': 'New Home by Paradiso 与官方机关无合作或隶属关系。所有指引仅供学习参考，最终确认请通过法务部·出入境外国人机关·HiKorea·1345 进行。',
      'footer.back': '← 返回国籍·归化主页',
      'filter.all': '全部', 'who': '适合这些人', 'flowLabel': '一般流程', 'docNote': '材料相关注意事项',
      'relatedLaws': '相关法令', 'relatedSources': '官方出处', 'caution': '注意', 'confirmNeeded': '需确认',
      'caseVaries': '可能因个别情形而不同', 'viewFlow': '查看答复流程', 'guidance': '答复指南',
      'goodStructure': '良好的答复结构', 'riskyPatterns': '应避免的答复', 'practiceWaymaker': '用 Waymaker 练习',
      'rooms.understand': '理解程序', 'rooms.topics': '核心主题学习', 'rooms.questions': '预想问题卡片',
      'rooms.mock': '模拟面试练习', 'rooms.videos': '参考视频/资料',
      'randomQ': '随机问题', 'searchQ': '搜索问题', 'allCats': '全部主题', 'allDiffs': '全部难度',
      'mock.todayQ': '今日练习题', 'mock.next': '下一题', 'mock.placeholder': '请在此用韩语输入答复。一并写上理由和经历会更好。',
      'mock.checkLocal': '检查我的答复', 'mock.startWaymaker': '开始 Waymaker 模拟面试', 'mock.retry': '重新作答',
      'mock.strengths': '做得好的地方', 'mock.improvements': '需补充的地方', 'mock.risky': '需注意的表述',
      'mock.revised': '更自然的答复示例', 'mock.followup': '下一道练习题', 'mock.tip': '学习提示',
      'mock.loading': 'Waymaker 正在审阅答复…',
      'mock.aiFail': '无法加载 AI 反馈。请先查看基本检查结果。',
      'mock.localTitle': '基本检查结果（离线）', 'mock.noAnswer': '请先输入答复。',
      'understand.heading': '归化面试·基本素养的准备是怎样衔接的？',
      'understand.body': '归化准备通常衔接社会融合项目（KIIP）学习与事前评价·综合评价，以及归化适格审查过程中的面试。面试并非背诵标准答案的场合，而更接近确认基本素养与沟通能力的场合。',
      'understand.warn': '面试对象·内容·是否免除会因个别情形和通知而不同。此处内容仅供学习参考，个别通知和管辖出入境外国人机关的指引始终优先。',
      'understand.steps': '准备流程示例',
      'sourceLabel.official_kiip': 'KIIP 学习衔接', 'sourceLabel.official_socinet': '评价指引衔接',
      'sourceLabel.practice': '练习题', 'sourceLabel.internal_guidance': '面试态度指南',
      'sourceLabel.official_law': '法令参考', 'sourceLabel.official_notice': '官方指引参考', 'sourceLabel.video_reference_topic': '视频参考主题',
      'studyFocus': '学习要点', 'noResults': '没有符合条件的结果。',
      'videoDisclaimer': '视频资料为非官方参考资料，并不代表实际面试题或法务部官方历年真题。',
      'openLink': '前往', 'difficulty.easy': '简单', 'difficulty.medium': '中等', 'difficulty.hard': '困难',
      'localCheck.tooShort': '答复太短。请逐句补充理由和具体经历。',
      'localCheck.direct': '先给出对问题的直接答复会更稳妥。',
      'localCheck.vague': '内容略显笼统。请再补充一个具体的例子或经历。',
      'localCheck.structure': '有理由和示例，答复结构很好。',
      'localCheck.length': '篇幅适当。请清晰地传达要点。',
      'localCheck.specific': '包含具体的经历·示例，很有说服力。',
      'localCheck.risky': '只强调福利·金钱·逃避义务的表述，最好避免以策安全。',
      'localCheck.okStart': '已明确给出对问题的答复。',
      'rubric.title': '答复检查项目', 'rubric.direct': '直接答复', 'rubric.specific': '具体经历·示例',
      'rubric.structure': '理由·结构', 'rubric.length': '适当篇幅', 'rubric.attitude': '安全的表述',
      'rubric.ok': '充分', 'rubric.improve': '补充',
      'cautionCoach': '此反馈仅供练习，不保证实际审查结果。'
    },
    ja: {
      'hero.kicker': '国籍民願・帰化面接の準備',
      'hero.title': '国籍民願と帰化面接の準備を、一つの場所で',
      'hero.lead': '帰化、国籍回復、国籍喪失・離脱、複数国籍、国民宣誓、そして帰化面接の準備まで — 公式の法令と案内をもとに、ご自身の状況に近い流れを確認し、練習問題と模擬面接で準備できます。',
      'hero.ctaPrimary': '帰化面接の学習を始める', 'hero.ctaSecondary': '国籍民願を見てみる',
      'global.disclaimer': 'この機能は、国籍民願の確認と帰化面接および基本素養の準備を助けるための学習ツールであり、実際の審査結果を保証するものではありません。公式案内と個別通知は、法務部・出入国外国人官署の案内を優先してご確認ください。',
      'about.title': '国籍民願について知る',
      'about.intro': '関心のある国籍民願の種類を選び、どんな民願か・誰のためのものか・一般的な流れ・書類の留意事項・関連法令と公式出典を確認しましょう。個別の事案によって異なる場合があります。',
      'laws.title': '関連法令・指針',
      'laws.intro': '国籍業務の根拠となる公式出典を種類別に確認しましょう。地域の告知や補助説明資料は別途表示されます。外部リンクから原文を直接確認できます。',
      'flow.title': '手続き・書類の流れ',
      'flow.intro': '種類を選ぶと一般的な流れと書類に関する留意事項を確認できます。正確な順序・書類・基準は管轄の出入国外国人官署の案内が優先され、個別の事案によって異なる場合があります。',
      'interview.title': '帰化面接対策の学習室',
      'interview.intro': '手続きの理解から、重要テーマの学習、予想質問カード、模擬面接の練習、参考映像まで段階的に準備しましょう。すべての質問は学習用の練習問題であり、実際の面接質問や公式の過去問ではありません。',
      'kiip.title': '事前評価/総合評価の学習の流れ',
      'kiip.intro': '社会統合プログラム（KIIP）は事前評価で段階が割り当てられ、段階別の学習を経て総合評価（帰化用を含む）へと続きます。修了・評価の結果がそのまま帰化許可を意味するわけではありません。',
      'videos.title': '参考映像/資料',
      'videos.intro': 'ユーザーが提供した再生リスト・チャンネルを参考用に整理しました。映像の字幕・台本は保存せず、公式資料ではありません。',
      'waymaker.title': 'Waymaker 国籍民願コーチ',
      'waymaker.heading': '質問して、練習しましょう',
      'waymaker.desc': '国籍民願案内コーチは法令・案内を区別して説明し、帰化面接コーチは入力した回答を点検して、より自然な例文と追加の質問を提案します。音声なしのテキストで進みます。',
      'waymaker.note': '合否を予測することはなく、個別通知と出入国外国人官署の案内が常に優先されます。',
      'waymaker.ctaGuide': '国籍民願案内コーチを開く', 'waymaker.ctaInterview': '帰化面接コーチで模擬面接',
      'badge.official': '公式資料に基づく', 'badge.notOfficial': '公式の過去問ではありません', 'badge.unofficialVideo': '非公式の参考資料',
      'footer.note': 'New Home by Paradiso は公式機関と提携または所属の関係はありません。すべての案内は学習の参考用であり、最終確認は法務部・出入国外国人官署・HiKorea・1345 を通じて行ってください。',
      'footer.back': '← 国籍・帰化ホームへ',
      'filter.all': 'すべて', 'who': 'こんな方へ', 'flowLabel': '一般的な流れ', 'docNote': '書類に関する留意事項',
      'relatedLaws': '関連法令', 'relatedSources': '公式出典', 'caution': '注意', 'confirmNeeded': '確認が必要',
      'caseVaries': '個別の事案によって異なる場合があります', 'viewFlow': '回答の流れを見る', 'guidance': '回答ガイド',
      'goodStructure': '良い回答の構成', 'riskyPatterns': '避けるべき回答', 'practiceWaymaker': 'Waymaker で練習する',
      'rooms.understand': '手続きの理解', 'rooms.topics': '重要テーマの学習', 'rooms.questions': '予想質問カード',
      'rooms.mock': '模擬面接の練習', 'rooms.videos': '参考映像/資料',
      'randomQ': 'ランダム質問', 'searchQ': '質問を検索', 'allCats': 'すべてのテーマ', 'allDiffs': 'すべての難易度',
      'mock.todayQ': '今日の練習問題', 'mock.next': '次の質問', 'mock.placeholder': 'ここに韓国語で回答を入力してみましょう。理由と経験を一緒に書くと良いです。',
      'mock.checkLocal': '回答を点検する', 'mock.startWaymaker': 'Waymaker 模擬面接を始める', 'mock.retry': '回答を書き直す',
      'mock.strengths': '良かった点', 'mock.improvements': '補うべき点', 'mock.risky': '注意すべき表現',
      'mock.revised': 'より自然な回答例', 'mock.followup': '次の練習問題', 'mock.tip': '学習のヒント',
      'mock.loading': 'Waymaker が回答を検討中…',
      'mock.aiFail': 'AI フィードバックを読み込めませんでした。まず基本点検の結果をご確認ください。',
      'mock.localTitle': '基本点検の結果（オフライン）', 'mock.noAnswer': 'まず回答を入力してください。',
      'understand.heading': '帰化面接・基本素養の準備は、どのようにつながりますか？',
      'understand.body': '帰化の準備は通常、社会統合プログラム（KIIP）の学習と事前評価・総合評価、そして帰化適格審査の過程での面接へとつながります。面接は正解を暗記する場ではなく、基本素養と意思疎通を確認する場に近いものです。',
      'understand.warn': '面接の対象・内容・免除の可否は、個別の事案と通知によって異なります。ここの内容は学習の参考用であり、常に個別通知と管轄の出入国外国人官署の案内が優先されます。',
      'understand.steps': '準備の流れの例',
      'sourceLabel.official_kiip': 'KIIP 学習連携', 'sourceLabel.official_socinet': '評価案内連携',
      'sourceLabel.practice': '練習問題', 'sourceLabel.internal_guidance': '面接態度ガイド',
      'sourceLabel.official_law': '法令参考', 'sourceLabel.official_notice': '公式案内参考', 'sourceLabel.video_reference_topic': '映像参考テーマ',
      'studyFocus': '学習ポイント', 'noResults': '条件に合う結果がありません。',
      'videoDisclaimer': '映像資料は非公式の参考資料であり、実際の面接質問や法務部の公式過去問を意味するものではありません。',
      'openLink': '移動', 'difficulty.easy': 'やさしい', 'difficulty.medium': 'ふつう', 'difficulty.hard': 'むずかしい',
      'localCheck.tooShort': '回答が短すぎます。理由と具体的な経験を一文ずつ加えてみましょう。',
      'localCheck.direct': '質問への直接の回答を先に述べると、より安定します。',
      'localCheck.vague': '内容がやや漠然としています。具体的な例や経験をもう一つ加えてみましょう。',
      'localCheck.structure': '理由と例があり、回答の構成が良いです。',
      'localCheck.length': '分量が適切です。要点をはっきりと伝えましょう。',
      'localCheck.specific': '具体的な経験・例が含まれており、説得力があります。',
      'localCheck.risky': '恩恵・金銭・義務回避だけを強調する表現は避けるほうが安全です。',
      'localCheck.okStart': '質問への回答をはっきりと示しました。',
      'rubric.title': '回答の点検項目', 'rubric.direct': '直接の回答', 'rubric.specific': '具体的な経験・例',
      'rubric.structure': '理由・構成', 'rubric.length': '適切な分量', 'rubric.attitude': '安全な表現',
      'rubric.ok': '十分', 'rubric.improve': '補う',
      'cautionCoach': 'このフィードバックは練習用であり、実際の審査結果を保証するものではありません。'
    },
    vi: {
      'hero.kicker': 'Dịch vụ quốc tịch & chuẩn bị phỏng vấn',
      'hero.title': 'Dịch vụ quốc tịch và chuẩn bị phỏng vấn nhập tịch, tại một nơi',
      'hero.lead': 'Nhập tịch, phục hồi quốc tịch, mất/từ bỏ quốc tịch, đa quốc tịch, lời tuyên thệ công dân và chuẩn bị phỏng vấn — xem quy trình gần với hoàn cảnh của bạn dựa trên luật và hướng dẫn chính thức, rồi luyện tập bằng câu hỏi và phỏng vấn thử.',
      'hero.ctaPrimary': 'Bắt đầu chuẩn bị phỏng vấn', 'hero.ctaSecondary': 'Xem các dịch vụ quốc tịch',
      'global.disclaimer': 'Đây là công cụ học tập giúp bạn kiểm tra các dịch vụ quốc tịch và chuẩn bị cho phỏng vấn nhập tịch cùng phần đánh giá kiến thức cơ bản. Công cụ không bảo đảm bất kỳ kết quả thẩm tra nào. Hãy luôn xác nhận hướng dẫn chính thức và các thông báo cá nhân với Bộ Tư pháp · cơ quan xuất nhập cảnh và người nước ngoài.',
      'about.title': 'Tìm hiểu các dịch vụ quốc tịch',
      'about.intro': 'Chọn một loại dịch vụ để xem đó là gì, thường dành cho ai, quy trình thông thường, lưu ý về giấy tờ, luật liên quan và nguồn chính thức. Từng trường hợp cá nhân có thể khác nhau.',
      'laws.title': 'Luật & hướng dẫn liên quan',
      'laws.intro': 'Xem các nguồn chính thức làm cơ sở cho công việc quốc tịch theo từng loại. Thông báo địa phương và tài liệu giải thích bổ trợ được đánh dấu riêng. Mở liên kết ngoài để đọc bản gốc.',
      'flow.title': 'Quy trình & dòng giấy tờ',
      'flow.intro': 'Chọn một loại để xem quy trình chung và lưu ý về giấy tờ. Trình tự, giấy tờ và tiêu chí chính xác tuân theo cơ quan xuất nhập cảnh có thẩm quyền và có thể khác nhau theo từng trường hợp.',
      'interview.title': 'Phòng học chuẩn bị phỏng vấn nhập tịch',
      'interview.intro': 'Chuẩn bị từng bước: hiểu quy trình, học các chủ đề cốt lõi, xem câu hỏi luyện tập, làm phỏng vấn thử và xem video tham khảo. Mọi câu hỏi đều là tài liệu luyện tập, không phải câu hỏi thật hay đề thi chính thức trước đây.',
      'kiip.title': 'Quy trình học đánh giá sơ bộ / đánh giá tổng hợp',
      'kiip.intro': 'KIIP phân cấp độ qua đánh giá sơ bộ, rồi dẫn đến đánh giá tổng hợp (bao gồm bản dành cho nhập tịch). Hoàn thành chương trình tự nó không có nghĩa là được chấp thuận nhập tịch.',
      'videos.title': 'Video / tài liệu tham khảo',
      'videos.intro': 'Danh sách phát và kênh do người dùng cung cấp, được sắp xếp chỉ để tham khảo. Không lưu trữ phụ đề hay lời thoại, và đây không phải tài liệu chính thức.',
      'waymaker.title': 'Huấn luyện viên quốc tịch Waymaker',
      'waymaker.heading': 'Hãy hỏi và luyện tập',
      'waymaker.desc': 'Huấn luyện viên hướng dẫn quốc tịch giải thích trong khi phân biệt luật với hướng dẫn; huấn luyện viên phỏng vấn xem câu trả lời bạn nhập và gợi ý ví dụ tự nhiên hơn cùng một câu hỏi tiếp theo. Ưu tiên văn bản, không cần giọng nói.',
      'waymaker.note': 'Công cụ không bao giờ dự đoán đậu/rớt; các thông báo cá nhân và cơ quan xuất nhập cảnh luôn được ưu tiên.',
      'waymaker.ctaGuide': 'Mở huấn luyện viên hướng dẫn quốc tịch', 'waymaker.ctaInterview': 'Phỏng vấn thử với huấn luyện viên',
      'badge.official': 'Dựa trên nguồn chính thức', 'badge.notOfficial': 'Không phải đề thi chính thức trước đây', 'badge.unofficialVideo': 'Tham khảo không chính thức',
      'footer.note': 'New Home by Paradiso không liên kết hay trực thuộc bất kỳ cơ quan chính thức nào. Mọi hướng dẫn chỉ để tham khảo học tập; hãy xác nhận với Bộ Tư pháp, cơ quan xuất nhập cảnh, HiKorea hoặc 1345.',
      'footer.back': '← Quay lại trang chủ quốc tịch',
      'filter.all': 'Tất cả', 'who': 'Dành cho ai', 'flowLabel': 'Quy trình chung', 'docNote': 'Lưu ý về giấy tờ',
      'relatedLaws': 'Luật liên quan', 'relatedSources': 'Nguồn chính thức', 'caution': 'Lưu ý', 'confirmNeeded': 'Cần xác nhận',
      'caseVaries': 'Có thể khác nhau theo từng trường hợp', 'viewFlow': 'Xem quy trình trả lời', 'guidance': 'Hướng dẫn trả lời',
      'goodStructure': 'Cấu trúc trả lời tốt', 'riskyPatterns': 'Cách trả lời nên tránh', 'practiceWaymaker': 'Luyện tập với Waymaker',
      'rooms.understand': 'Hiểu quy trình', 'rooms.topics': 'Chủ đề cốt lõi', 'rooms.questions': 'Câu hỏi luyện tập',
      'rooms.mock': 'Phỏng vấn thử', 'rooms.videos': 'Video tham khảo',
      'randomQ': 'Câu hỏi ngẫu nhiên', 'searchQ': 'Tìm câu hỏi', 'allCats': 'Tất cả chủ đề', 'allDiffs': 'Tất cả mức độ',
      'mock.todayQ': 'Câu hỏi luyện tập hôm nay', 'mock.next': 'Câu hỏi tiếp theo', 'mock.placeholder': 'Nhập câu trả lời của bạn vào đây bằng tiếng Hàn. Nên ghi kèm lý do và trải nghiệm.',
      'mock.checkLocal': 'Kiểm tra câu trả lời của tôi', 'mock.startWaymaker': 'Bắt đầu phỏng vấn thử Waymaker', 'mock.retry': 'Viết lại câu trả lời',
      'mock.strengths': 'Điểm tốt', 'mock.improvements': 'Cần cải thiện', 'mock.risky': 'Cách diễn đạt cần lưu ý',
      'mock.revised': 'Ví dụ tự nhiên hơn', 'mock.followup': 'Câu hỏi luyện tập tiếp theo', 'mock.tip': 'Mẹo học tập',
      'mock.loading': 'Waymaker đang xem xét câu trả lời…',
      'mock.aiFail': 'Không tải được phản hồi AI. Vui lòng xem kết quả kiểm tra cơ bản trước.',
      'mock.localTitle': 'Kiểm tra cơ bản (ngoại tuyến)', 'mock.noAnswer': 'Vui lòng nhập câu trả lời trước.',
      'understand.heading': 'Chuẩn bị phỏng vấn & kiến thức cơ bản gắn kết với nhau như thế nào?',
      'understand.body': 'Việc chuẩn bị nhập tịch thường kết nối việc học KIIP, các kỳ đánh giá sơ bộ/tổng hợp và buổi phỏng vấn trong quá trình thẩm tra nhập tịch. Phỏng vấn kiểm tra kiến thức cơ bản và khả năng giao tiếp hơn là các câu trả lời học thuộc lòng.',
      'understand.warn': 'Ai được phỏng vấn, nội dung và việc miễn trừ tùy thuộc vào từng trường hợp và thông báo. Đây chỉ là tài liệu tham khảo học tập; thông báo cá nhân của bạn và cơ quan xuất nhập cảnh có thẩm quyền luôn được ưu tiên.',
      'understand.steps': 'Ví dụ quy trình chuẩn bị',
      'sourceLabel.official_kiip': 'Liên kết KIIP', 'sourceLabel.official_socinet': 'Liên kết đánh giá',
      'sourceLabel.practice': 'Luyện tập', 'sourceLabel.internal_guidance': 'Hướng dẫn thái độ',
      'sourceLabel.official_law': 'Tham khảo luật', 'sourceLabel.official_notice': 'Tham khảo thông báo chính thức', 'sourceLabel.video_reference_topic': 'Chủ đề video',
      'studyFocus': 'Trọng tâm học tập', 'noResults': 'Không có kết quả phù hợp.',
      'videoDisclaimer': 'Tài liệu video là tham khảo không chính thức và không đại diện cho câu hỏi phỏng vấn thật hay đề thi chính thức trước đây của Bộ Tư pháp.',
      'openLink': 'Mở', 'difficulty.easy': 'Dễ', 'difficulty.medium': 'Trung bình', 'difficulty.hard': 'Khó',
      'localCheck.tooShort': 'Câu trả lời của bạn rất ngắn. Hãy thử thêm mỗi câu một lý do và một trải nghiệm cụ thể.',
      'localCheck.direct': 'Sẽ vững vàng hơn khi câu trả lời trực tiếp cho câu hỏi xuất hiện trước.',
      'localCheck.vague': 'Nội dung hơi mơ hồ. Hãy thêm một ví dụ hoặc trải nghiệm cụ thể.',
      'localCheck.structure': 'Có lý do và ví dụ giúp câu trả lời của bạn có cấu trúc tốt.',
      'localCheck.length': 'Độ dài phù hợp. Hãy truyền đạt ý chính một cách rõ ràng.',
      'localCheck.specific': 'Có trải nghiệm hoặc ví dụ cụ thể, rất thuyết phục.',
      'localCheck.risky': 'An toàn hơn nếu tránh chỉ nhấn mạnh quyền lợi, tiền bạc hay việc né tránh nghĩa vụ.',
      'localCheck.okStart': 'Bạn đã nêu một câu trả lời rõ ràng cho câu hỏi.',
      'rubric.title': 'Tiêu chí câu trả lời', 'rubric.direct': 'Trả lời trực tiếp', 'rubric.specific': 'Ví dụ cụ thể',
      'rubric.structure': 'Lý do & cấu trúc', 'rubric.length': 'Độ dài hợp lý', 'rubric.attitude': 'Diễn đạt an toàn',
      'rubric.ok': 'Tốt', 'rubric.improve': 'Cải thiện',
      'cautionCoach': 'Phản hồi này chỉ để luyện tập và không bảo đảm bất kỳ kết quả thẩm tra nào.'
    },
    tl: {
      'hero.kicker': 'Mga serbisyo sa nasyonalidad at paghahanda sa interbyu',
      'hero.title': 'Mga serbisyo sa nasyonalidad at paghahanda sa interbyu para sa naturalisasyon, sa isang lugar',
      'hero.lead': 'Naturalisasyon, pagbawi ng nasyonalidad, pagkawala/pagtalikod, maramihang nasyonalidad, ang panunumpa ng mamamayan at paghahanda sa interbyu — tingnan ang daloy na malapit sa iyong sitwasyon batay sa opisyal na batas at gabay, pagkatapos ay magsanay gamit ang mga tanong at mock interview.',
      'hero.ctaPrimary': 'Simulan ang paghahanda sa interbyu', 'hero.ctaSecondary': 'Tingnan ang mga serbisyo sa nasyonalidad',
      'global.disclaimer': 'Ito ay isang kasangkapan sa pag-aaral upang tulungan kang tingnan ang mga serbisyo sa nasyonalidad at maghanda para sa interbyu ng naturalisasyon at pagtatasa ng pangunahing kaalaman. Hindi nito ginagarantiya ang anumang resulta ng pagsusuri. Palaging kumpirmahin ang opisyal na gabay at mga personal na abiso sa Ministri ng Hustisya · tanggapan ng imigrasyon at dayuhan.',
      'about.title': 'Tuklasin ang mga serbisyo sa nasyonalidad',
      'about.intro': 'Pumili ng uri ng serbisyo upang makita kung ano ito, para kanino ito kadalasan, ang karaniwang daloy, mga babala sa dokumento, mga kaugnay na batas at opisyal na pinagmulan. Maaaring magkaiba ang bawat kaso.',
      'laws.title': 'Mga kaugnay na batas at alituntunin',
      'laws.intro': 'Tingnan ang mga opisyal na pinagmulan sa likod ng gawaing nasyonalidad ayon sa uri. Ang mga lokal na abiso at pangalawang paliwanag ay tinatakan nang hiwalay. Buksan ang mga panlabas na link upang basahin ang orihinal.',
      'flow.title': 'Daloy ng proseso at dokumento',
      'flow.intro': 'Pumili ng uri upang makita ang pangkalahatang daloy at mga babala sa dokumento. Ang eksaktong pagkakasunod-sunod, mga dokumento at pamantayan ay sumusunod sa may kapangyarihang tanggapan ng imigrasyon at maaaring magkaiba ayon sa kaso.',
      'interview.title': 'Silid-aralan para sa interbyu ng naturalisasyon',
      'interview.intro': 'Maghanda nang pahakbang: unawain ang proseso, pag-aralan ang mga pangunahing paksa, tingnan ang mga tanong sa pagsasanay, magsagawa ng mock interview, at suriin ang mga sangguniang video. Bawat tanong ay materyal sa pagsasanay, hindi tunay o opisyal na nakaraang tanong.',
      'kiip.title': 'Daloy ng pag-aaral ng paunang pagtatasa / komprehensibong pagtatasa',
      'kiip.intro': 'Nagtatakda ang KIIP ng antas sa pamamagitan ng paunang pagtatasa, pagkatapos ay umaakay sa komprehensibong pagtatasa (kabilang ang bersyon para sa naturalisasyon). Ang pagkumpleto nito mismo ay hindi nangangahulugang aprubado na ang naturalisasyon.',
      'videos.title': 'Mga sangguniang video / materyales',
      'videos.intro': 'Mga playlist at channel na ibinigay ng user, inayos para sa sanggunian lamang. Walang iniimbak na caption o transcript, at hindi ito opisyal na materyales.',
      'waymaker.title': 'Waymaker na coach sa nasyonalidad',
      'waymaker.heading': 'Magtanong, at magsanay',
      'waymaker.desc': 'Ipinaliliwanag ng coach sa gabay sa nasyonalidad habang pinaghihiwalay ang batas sa gabay; sinusuri ng coach sa interbyu ang iyong na-type na sagot at nagmumungkahi ng mas natural na halimbawa at isang follow-up na tanong. Text muna, hindi kailangan ng boses.',
      'waymaker.note': 'Hindi nito kailanman hinuhulaan kung pasado o bagsak; ang mga personal na abiso at ang tanggapan ng imigrasyon ay laging nangunguna.',
      'waymaker.ctaGuide': 'Buksan ang coach sa gabay sa nasyonalidad', 'waymaker.ctaInterview': 'Mock interview kasama ang coach',
      'badge.official': 'Batay sa opisyal na pinagmulan', 'badge.notOfficial': 'Hindi opisyal na nakaraang tanong', 'badge.unofficialVideo': 'Hindi opisyal na sanggunian',
      'footer.note': 'Ang New Home by Paradiso ay hindi kaugnay o bahagi ng anumang opisyal na ahensya. Lahat ng gabay ay para sa sanggunian sa pag-aaral; kumpirmahin sa Ministri ng Hustisya, tanggapan ng imigrasyon, HiKorea, o 1345.',
      'footer.back': '← Bumalik sa home ng nasyonalidad',
      'filter.all': 'Lahat', 'who': 'Para kanino ito', 'flowLabel': 'Pangkalahatang daloy', 'docNote': 'Mga babala sa dokumento',
      'relatedLaws': 'Mga kaugnay na batas', 'relatedSources': 'Mga opisyal na pinagmulan', 'caution': 'Babala', 'confirmNeeded': 'Kailangang kumpirmahin',
      'caseVaries': 'Maaaring magkaiba ayon sa indibidwal na kaso', 'viewFlow': 'Tingnan ang daloy ng sagot', 'guidance': 'Gabay sa sagot',
      'goodStructure': 'Magandang istruktura ng sagot', 'riskyPatterns': 'Mga dapat iwasan', 'practiceWaymaker': 'Magsanay gamit ang Waymaker',
      'rooms.understand': 'Unawain ang proseso', 'rooms.topics': 'Mga pangunahing paksa', 'rooms.questions': 'Mga tanong sa pagsasanay',
      'rooms.mock': 'Mock interview', 'rooms.videos': 'Mga sangguniang video',
      'randomQ': 'Random na tanong', 'searchQ': 'Maghanap ng tanong', 'allCats': 'Lahat ng paksa', 'allDiffs': 'Lahat ng antas',
      'mock.todayQ': 'Tanong sa pagsasanay ngayon', 'mock.next': 'Susunod na tanong', 'mock.placeholder': 'I-type ang iyong sagot dito sa Korean. Makatutulong na magdagdag ng dahilan at karanasan.',
      'mock.checkLocal': 'Suriin ang aking sagot', 'mock.startWaymaker': 'Simulan ang Waymaker mock interview', 'mock.retry': 'Muling isulat ang sagot',
      'mock.strengths': 'Mga lakas', 'mock.improvements': 'Dapat pagbutihin', 'mock.risky': 'Mga pananalitang dapat bantayan',
      'mock.revised': 'Mas natural na halimbawa', 'mock.followup': 'Susunod na tanong sa pagsasanay', 'mock.tip': 'Tip sa pag-aaral',
      'mock.loading': 'Sinusuri ng Waymaker ang iyong sagot…',
      'mock.aiFail': 'Hindi ma-load ang AI feedback. Pakitingnan muna ang mga pangunahing resulta.',
      'mock.localTitle': 'Pangunahing pagsusuri (offline)', 'mock.noAnswer': 'Mangyaring mag-type muna ng sagot.',
      'understand.heading': 'Paano nagkakaugnay ang paghahanda sa interbyu at pangunahing kaalaman?',
      'understand.body': 'Ang paghahanda sa naturalisasyon ay karaniwang nag-uugnay sa pag-aaral ng KIIP, ang mga paunang/komprehensibong pagtatasa, at ang interbyu sa loob ng pagsusuri ng naturalisasyon. Sinusuri ng interbyu ang pangunahing kaalaman at komunikasyon, hindi mga sagot na isinaulo.',
      'understand.warn': 'Kung sino ang ininterbyu, ang nilalaman, at anumang exemption ay nakadepende sa indibidwal na kaso at abiso. Para lamang itong sanggunian sa pag-aaral; ang iyong personal na abiso at ang may kapangyarihang tanggapan ng imigrasyon ay laging nangunguna.',
      'understand.steps': 'Halimbawa ng daloy ng paghahanda',
      'sourceLabel.official_kiip': 'Nakaugnay sa KIIP', 'sourceLabel.official_socinet': 'Nakaugnay sa pagtatasa',
      'sourceLabel.practice': 'Pagsasanay', 'sourceLabel.internal_guidance': 'Gabay sa saloobin',
      'sourceLabel.official_law': 'Sanggunian sa batas', 'sourceLabel.official_notice': 'Sanggunian sa opisyal na abiso', 'sourceLabel.video_reference_topic': 'Paksa ng video',
      'studyFocus': 'Pokus sa pag-aaral', 'noResults': 'Walang tumutugmang resulta.',
      'videoDisclaimer': 'Ang mga materyales na video ay hindi opisyal na sanggunian at hindi kumakatawan sa tunay na tanong sa interbyu o opisyal na nakaraang tanong mula sa Ministri ng Hustisya.',
      'openLink': 'Buksan', 'difficulty.easy': 'Madali', 'difficulty.medium': 'Katamtaman', 'difficulty.hard': 'Mahirap',
      'localCheck.tooShort': 'Napakaikli ng iyong sagot. Subukang magdagdag ng tig-isang pangungusap para sa dahilan at konkretong karanasan.',
      'localCheck.direct': 'Mas matatag kapag nauuna ang tuwirang sagot sa tanong.',
      'localCheck.vague': 'Medyo malabo ang nilalaman. Magdagdag ng isang konkretong halimbawa o karanasan.',
      'localCheck.structure': 'May dahilan at halimbawa na nagbibigay ng magandang istruktura sa iyong sagot.',
      'localCheck.length': 'Tama ang haba. Ipahatid nang malinaw ang pangunahing punto.',
      'localCheck.specific': 'May kasamang konkretong karanasan o halimbawa, na nakakukumbinsi.',
      'localCheck.risky': 'Mas ligtas na iwasan ang pagbibigay-diin lamang sa benepisyo, pera, o pag-iwas sa tungkulin.',
      'localCheck.okStart': 'Nagbigay ka ng malinaw na sagot sa tanong.',
      'rubric.title': 'Pamantayan ng sagot', 'rubric.direct': 'Tuwirang sagot', 'rubric.specific': 'Konkretong halimbawa',
      'rubric.structure': 'Dahilan at istruktura', 'rubric.length': 'Sapat na haba', 'rubric.attitude': 'Ligtas na pananalita',
      'rubric.ok': 'Mabuti', 'rubric.improve': 'Pagbutihin',
      'cautionCoach': 'Ang feedback na ito ay para sa pagsasanay at hindi ginagarantiya ang anumang resulta ng pagsusuri.'
    },
    id: {
      'hero.kicker': 'Layanan kewarganegaraan & persiapan wawancara',
      'hero.title': 'Layanan kewarganegaraan dan persiapan wawancara naturalisasi, dalam satu tempat',
      'hero.lead': 'Naturalisasi, pemulihan kewarganegaraan, kehilangan/pelepasan, kewarganegaraan ganda, sumpah warga negara, dan persiapan wawancara — tinjau alur yang dekat dengan situasi Anda berdasarkan hukum dan panduan resmi, lalu berlatih dengan pertanyaan dan wawancara simulasi.',
      'hero.ctaPrimary': 'Mulai persiapan wawancara', 'hero.ctaSecondary': 'Jelajahi layanan kewarganegaraan',
      'global.disclaimer': 'Ini adalah alat belajar untuk membantu Anda memeriksa layanan kewarganegaraan dan mempersiapkan wawancara naturalisasi serta penilaian pengetahuan dasar. Alat ini tidak menjamin hasil pemeriksaan apa pun. Selalu konfirmasikan panduan resmi dan pemberitahuan pribadi dengan Kementerian Hukum · kantor imigrasi dan orang asing.',
      'about.title': 'Jelajahi layanan kewarganegaraan',
      'about.intro': 'Pilih jenis layanan untuk melihat apa itu, umumnya untuk siapa, alur biasa, peringatan dokumen, hukum terkait, dan sumber resmi. Setiap kasus dapat berbeda.',
      'laws.title': 'Hukum & pedoman terkait',
      'laws.intro': 'Telusuri sumber resmi yang menjadi dasar urusan kewarganegaraan menurut jenisnya. Pemberitahuan lokal dan penjelasan tambahan ditandai secara terpisah. Buka tautan eksternal untuk membaca aslinya.',
      'flow.title': 'Alur prosedur & dokumen',
      'flow.intro': 'Pilih jenis untuk melihat alur umum dan peringatan dokumen. Urutan, dokumen, dan kriteria yang tepat mengikuti kantor imigrasi yang berwenang dan dapat berbeda menurut kasus.',
      'interview.title': 'Ruang belajar wawancara naturalisasi',
      'interview.intro': 'Bersiaplah langkah demi langkah: pahami prosesnya, pelajari topik inti, telusuri pertanyaan latihan, jalankan wawancara simulasi, dan tinjau video referensi. Setiap pertanyaan adalah bahan latihan, bukan pertanyaan nyata atau soal resmi terdahulu.',
      'kiip.title': 'Alur belajar pra-evaluasi / evaluasi komprehensif',
      'kiip.intro': 'KIIP menetapkan tingkat melalui pra-evaluasi, lalu menuju evaluasi komprehensif (termasuk versi naturalisasi). Menyelesaikannya saja tidak berarti persetujuan naturalisasi.',
      'videos.title': 'Video / materi referensi',
      'videos.intro': 'Daftar putar dan kanal yang disediakan pengguna, ditata hanya untuk referensi. Tidak ada teks atau transkrip yang disimpan, dan ini bukan materi resmi.',
      'waymaker.title': 'Pelatih kewarganegaraan Waymaker',
      'waymaker.heading': 'Bertanya, dan berlatih',
      'waymaker.desc': 'Pelatih panduan kewarganegaraan menjelaskan sambil membedakan hukum dari panduan; pelatih wawancara meninjau jawaban yang Anda ketik dan menyarankan contoh yang lebih alami serta pertanyaan lanjutan. Berbasis teks, tanpa perlu suara.',
      'waymaker.note': 'Alat ini tidak pernah memprediksi lulus/gagal; pemberitahuan pribadi dan kantor imigrasi selalu diutamakan.',
      'waymaker.ctaGuide': 'Buka pelatih panduan kewarganegaraan', 'waymaker.ctaInterview': 'Wawancara simulasi dengan pelatih',
      'badge.official': 'Berdasarkan sumber resmi', 'badge.notOfficial': 'Bukan soal resmi terdahulu', 'badge.unofficialVideo': 'Referensi tidak resmi',
      'footer.note': 'New Home by Paradiso tidak berafiliasi atau menjadi bagian dari badan resmi mana pun. Semua panduan untuk referensi belajar; konfirmasikan dengan Kementerian Hukum, kantor imigrasi, HiKorea, atau 1345.',
      'footer.back': '← Kembali ke beranda kewarganegaraan',
      'filter.all': 'Semua', 'who': 'Untuk siapa ini', 'flowLabel': 'Alur umum', 'docNote': 'Peringatan dokumen',
      'relatedLaws': 'Hukum terkait', 'relatedSources': 'Sumber resmi', 'caution': 'Peringatan', 'confirmNeeded': 'Perlu konfirmasi',
      'caseVaries': 'Dapat berbeda menurut kasus masing-masing', 'viewFlow': 'Lihat alur jawaban', 'guidance': 'Panduan jawaban',
      'goodStructure': 'Struktur jawaban yang baik', 'riskyPatterns': 'Pola yang harus dihindari', 'practiceWaymaker': 'Berlatih dengan Waymaker',
      'rooms.understand': 'Pahami prosesnya', 'rooms.topics': 'Topik inti', 'rooms.questions': 'Pertanyaan latihan',
      'rooms.mock': 'Wawancara simulasi', 'rooms.videos': 'Video referensi',
      'randomQ': 'Pertanyaan acak', 'searchQ': 'Cari pertanyaan', 'allCats': 'Semua topik', 'allDiffs': 'Semua tingkat',
      'mock.todayQ': 'Pertanyaan latihan hari ini', 'mock.next': 'Pertanyaan berikutnya', 'mock.placeholder': 'Ketik jawaban Anda di sini dalam bahasa Korea. Menambahkan alasan dan pengalaman akan membantu.',
      'mock.checkLocal': 'Periksa jawaban saya', 'mock.startWaymaker': 'Mulai wawancara simulasi Waymaker', 'mock.retry': 'Tulis ulang jawaban',
      'mock.strengths': 'Kelebihan', 'mock.improvements': 'Perlu diperbaiki', 'mock.risky': 'Ungkapan yang perlu diperhatikan',
      'mock.revised': 'Contoh yang lebih alami', 'mock.followup': 'Pertanyaan latihan berikutnya', 'mock.tip': 'Tips belajar',
      'mock.loading': 'Waymaker sedang meninjau jawaban Anda…',
      'mock.aiFail': 'Tidak dapat memuat umpan balik AI. Silakan periksa hasil dasar terlebih dahulu.',
      'mock.localTitle': 'Pemeriksaan dasar (offline)', 'mock.noAnswer': 'Silakan ketik jawaban terlebih dahulu.',
      'understand.heading': 'Bagaimana persiapan wawancara & pengetahuan dasar saling berkaitan?',
      'understand.body': 'Persiapan naturalisasi biasanya menghubungkan pembelajaran KIIP, pra/evaluasi komprehensif, dan wawancara dalam pemeriksaan naturalisasi. Wawancara memeriksa pengetahuan dasar dan komunikasi, bukan jawaban yang dihafal.',
      'understand.warn': 'Siapa yang diwawancarai, isinya, dan pengecualian apa pun bergantung pada kasus masing-masing dan pemberitahuan. Ini hanya referensi belajar; pemberitahuan pribadi Anda dan kantor imigrasi yang berwenang selalu diutamakan.',
      'understand.steps': 'Contoh alur persiapan',
      'sourceLabel.official_kiip': 'Terkait KIIP', 'sourceLabel.official_socinet': 'Terkait evaluasi',
      'sourceLabel.practice': 'Latihan', 'sourceLabel.internal_guidance': 'Panduan sikap',
      'sourceLabel.official_law': 'Referensi hukum', 'sourceLabel.official_notice': 'Referensi pemberitahuan resmi', 'sourceLabel.video_reference_topic': 'Topik video',
      'studyFocus': 'Fokus belajar', 'noResults': 'Tidak ada hasil yang cocok.',
      'videoDisclaimer': 'Materi video adalah referensi tidak resmi dan tidak mewakili pertanyaan wawancara nyata atau soal resmi terdahulu dari Kementerian Hukum.',
      'openLink': 'Buka', 'difficulty.easy': 'Mudah', 'difficulty.medium': 'Sedang', 'difficulty.hard': 'Sulit',
      'localCheck.tooShort': 'Jawaban Anda sangat singkat. Coba tambahkan masing-masing satu kalimat untuk alasan dan pengalaman konkret.',
      'localCheck.direct': 'Lebih mantap jika jawaban langsung atas pertanyaan muncul lebih dulu.',
      'localCheck.vague': 'Terbaca agak kabur. Tambahkan satu contoh atau pengalaman konkret.',
      'localCheck.structure': 'Adanya alasan dan contoh memberi struktur yang baik pada jawaban Anda.',
      'localCheck.length': 'Panjangnya sesuai. Sampaikan poin utama dengan jelas.',
      'localCheck.specific': 'Memuat pengalaman atau contoh konkret, sehingga meyakinkan.',
      'localCheck.risky': 'Lebih aman menghindari penekanan hanya pada manfaat, uang, atau menghindari kewajiban.',
      'localCheck.okStart': 'Anda menyatakan jawaban yang jelas atas pertanyaan.',
      'rubric.title': 'Rubrik jawaban', 'rubric.direct': 'Jawaban langsung', 'rubric.specific': 'Contoh konkret',
      'rubric.structure': 'Alasan & struktur', 'rubric.length': 'Panjang memadai', 'rubric.attitude': 'Ungkapan aman',
      'rubric.ok': 'Baik', 'rubric.improve': 'Perbaiki',
      'cautionCoach': 'Umpan balik ini untuk latihan dan tidak menjamin hasil pemeriksaan apa pun.'
    },
    ru: {
      'hero.kicker': 'Услуги по гражданству и подготовка к собеседованию',
      'hero.title': 'Услуги по гражданству и подготовка к собеседованию по натурализации — в одном месте',
      'hero.lead': 'Натурализация, восстановление гражданства, утрата/отказ, множественное гражданство, присяга гражданина и подготовка к собеседованию — изучите процесс, близкий к вашей ситуации, на основе официальных законов и руководств, затем тренируйтесь с вопросами и пробным собеседованием.',
      'hero.ctaPrimary': 'Начать подготовку к собеседованию', 'hero.ctaSecondary': 'Обзор услуг по гражданству',
      'global.disclaimer': 'Это учебный инструмент, помогающий проверить услуги по гражданству и подготовиться к собеседованию по натурализации и оценке базовых знаний. Он не гарантирует какой-либо результат рассмотрения. Всегда уточняйте официальные указания и индивидуальные уведомления в Министерстве юстиции · миграционном органе по делам иностранцев.',
      'about.title': 'Изучить услуги по гражданству',
      'about.intro': 'Выберите тип услуги, чтобы увидеть, что это, для кого обычно предназначено, типичный процесс, предостережения по документам, связанные законы и официальные источники. Отдельные случаи могут отличаться.',
      'laws.title': 'Связанные законы и руководства',
      'laws.intro': 'Просмотрите официальные источники, лежащие в основе работы по гражданству, по типам. Местные уведомления и вспомогательные пояснения отмечаются отдельно. Откройте внешние ссылки, чтобы прочитать оригиналы.',
      'flow.title': 'Процедура и порядок документов',
      'flow.intro': 'Выберите тип, чтобы увидеть общий процесс и предостережения по документам. Точный порядок, документы и критерии определяются компетентным миграционным органом и могут отличаться в зависимости от случая.',
      'interview.title': 'Учебная комната подготовки к собеседованию по натурализации',
      'interview.intro': 'Готовьтесь шаг за шагом: поймите процесс, изучите ключевые темы, просмотрите тренировочные вопросы, проведите пробное собеседование и посмотрите справочные видео. Каждый вопрос — это учебный материал, а не реальный или официальный вопрос прошлых лет.',
      'kiip.title': 'Учебный поток предварительной / комплексной оценки',
      'kiip.intro': 'KIIP назначает уровень по предварительной оценке, затем ведёт к комплексной оценке (включая версию для натурализации). Её завершение само по себе не означает одобрения натурализации.',
      'videos.title': 'Справочные видео / материалы',
      'videos.intro': 'Предоставленные пользователем плейлисты и каналы, упорядоченные только для справки. Субтитры и расшифровки не хранятся, и это не официальные материалы.',
      'waymaker.title': 'Коуч по гражданству Waymaker',
      'waymaker.heading': 'Спрашивайте и тренируйтесь',
      'waymaker.desc': 'Коуч-гид по гражданству объясняет, разграничивая закон и руководство; коуч по собеседованию проверяет введённый вами ответ и предлагает более естественный пример и уточняющий вопрос. Прежде всего текст, голос не нужен.',
      'waymaker.note': 'Он никогда не предсказывает сдачу/провал; индивидуальные уведомления и миграционный орган всегда имеют приоритет.',
      'waymaker.ctaGuide': 'Открыть коуча-гида по гражданству', 'waymaker.ctaInterview': 'Пробное собеседование с коучем',
      'badge.official': 'На основе официальных источников', 'badge.notOfficial': 'Не официальный вопрос прошлых лет', 'badge.unofficialVideo': 'Неофициальный справочный материал',
      'footer.note': 'New Home by Paradiso не связана и не входит в состав какого-либо официального органа. Все указания предназначены для учебной справки; уточняйте в Министерстве юстиции, миграционном органе, HiKorea или по 1345.',
      'footer.back': '← Назад на главную по гражданству',
      'filter.all': 'Все', 'who': 'Для кого это', 'flowLabel': 'Общий процесс', 'docNote': 'Предостережения по документам',
      'relatedLaws': 'Связанные законы', 'relatedSources': 'Официальные источники', 'caution': 'Внимание', 'confirmNeeded': 'Требует подтверждения',
      'caseVaries': 'Может различаться в зависимости от случая', 'viewFlow': 'Посмотреть структуру ответа', 'guidance': 'Руководство по ответу',
      'goodStructure': 'Хорошая структура ответа', 'riskyPatterns': 'Чего следует избегать', 'practiceWaymaker': 'Тренироваться с Waymaker',
      'rooms.understand': 'Понять процесс', 'rooms.topics': 'Ключевые темы', 'rooms.questions': 'Тренировочные вопросы',
      'rooms.mock': 'Пробное собеседование', 'rooms.videos': 'Справочные видео',
      'randomQ': 'Случайный вопрос', 'searchQ': 'Поиск вопросов', 'allCats': 'Все темы', 'allDiffs': 'Все уровни',
      'mock.todayQ': 'Сегодняшний тренировочный вопрос', 'mock.next': 'Следующий вопрос', 'mock.placeholder': 'Введите свой ответ здесь на корейском. Добавление причины и примера помогает.',
      'mock.checkLocal': 'Проверить мой ответ', 'mock.startWaymaker': 'Начать пробное собеседование Waymaker', 'mock.retry': 'Переписать ответ',
      'mock.strengths': 'Сильные стороны', 'mock.improvements': 'Что улучшить', 'mock.risky': 'Выражения, на которые стоит обратить внимание',
      'mock.revised': 'Более естественный пример', 'mock.followup': 'Следующий тренировочный вопрос', 'mock.tip': 'Совет для учёбы',
      'mock.loading': 'Waymaker проверяет ваш ответ…',
      'mock.aiFail': 'Не удалось загрузить отзыв ИИ. Пожалуйста, сначала проверьте базовые результаты.',
      'mock.localTitle': 'Базовая проверка (офлайн)', 'mock.noAnswer': 'Пожалуйста, сначала введите ответ.',
      'understand.heading': 'Как сочетаются подготовка к собеседованию и базовые знания?',
      'understand.body': 'Подготовка к натурализации обычно связывает обучение по KIIP, предварительную/комплексную оценки и собеседование в рамках рассмотрения натурализации. Собеседование проверяет базовые знания и общение, а не заученные ответы.',
      'understand.warn': 'Кого приглашают на собеседование, его содержание и любые освобождения зависят от отдельного случая и уведомления. Это только учебная справка; ваше индивидуальное уведомление и компетентный миграционный орган всегда имеют приоритет.',
      'understand.steps': 'Пример процесса подготовки',
      'sourceLabel.official_kiip': 'Связано с KIIP', 'sourceLabel.official_socinet': 'Связано с оценкой',
      'sourceLabel.practice': 'Практика', 'sourceLabel.internal_guidance': 'Руководство по поведению',
      'sourceLabel.official_law': 'Ссылка на закон', 'sourceLabel.official_notice': 'Ссылка на официальное уведомление', 'sourceLabel.video_reference_topic': 'Тема видео',
      'studyFocus': 'Фокус обучения', 'noResults': 'Нет подходящих результатов.',
      'videoDisclaimer': 'Видеоматериалы являются неофициальными справочными материалами и не представляют реальные вопросы собеседования или официальные вопросы прошлых лет Министерства юстиции.',
      'openLink': 'Открыть', 'difficulty.easy': 'Легко', 'difficulty.medium': 'Средне', 'difficulty.hard': 'Трудно',
      'localCheck.tooShort': 'Ваш ответ очень короткий. Попробуйте добавить по одному предложению для причины и конкретного опыта.',
      'localCheck.direct': 'Надёжнее, когда прямой ответ на вопрос идёт первым.',
      'localCheck.vague': 'Звучит немного расплывчато. Добавьте один конкретный пример или опыт.',
      'localCheck.structure': 'Причина и пример придают вашему ответу хорошую структуру.',
      'localCheck.length': 'Объём подходящий. Чётко донесите ключевую мысль.',
      'localCheck.specific': 'Содержит конкретный опыт или пример, что убедительно.',
      'localCheck.risky': 'Безопаснее не подчёркивать только льготы, деньги или уклонение от обязанностей.',
      'localCheck.okStart': 'Вы дали чёткий ответ на вопрос.',
      'rubric.title': 'Критерии ответа', 'rubric.direct': 'Прямой ответ', 'rubric.specific': 'Конкретный пример',
      'rubric.structure': 'Причина и структура', 'rubric.length': 'Достаточный объём', 'rubric.attitude': 'Безопасные формулировки',
      'rubric.ok': 'Достаточно', 'rubric.improve': 'Улучшить',
      'cautionCoach': 'Этот отзыв предназначен для тренировки и не гарантирует какой-либо результат рассмотрения.'
    },
    fr: {
      'hero.kicker': 'Services de nationalité et préparation à l’entretien',
      'hero.title': 'Services de nationalité et préparation à l’entretien de naturalisation, au même endroit',
      'hero.lead': 'Naturalisation, recouvrement de la nationalité, perte/renonciation, multiple nationalité, serment du citoyen et préparation à l’entretien — consultez un parcours proche de votre situation à partir des lois et directives officielles, puis entraînez-vous avec des questions et un entretien simulé.',
      'hero.ctaPrimary': 'Commencer la préparation à l’entretien', 'hero.ctaSecondary': 'Parcourir les services de nationalité',
      'global.disclaimer': 'Ceci est un outil d’étude pour vous aider à vérifier les services de nationalité et à préparer l’entretien de naturalisation et l’évaluation des connaissances de base. Il ne garantit aucun résultat d’examen. Confirmez toujours les directives officielles et les avis individuels auprès du ministère de la Justice · bureau de l’immigration et des étrangers.',
      'about.title': 'Explorer les services de nationalité',
      'about.intro': 'Choisissez un type de service pour voir ce dont il s’agit, à qui il s’adresse généralement, le parcours habituel, les avertissements relatifs aux documents, les lois connexes et les sources officielles. Chaque cas peut différer.',
      'laws.title': 'Lois et directives connexes',
      'laws.intro': 'Parcourez par type les sources officielles qui fondent le travail sur la nationalité. Les avis locaux et les explications secondaires sont signalés séparément. Ouvrez les liens externes pour lire les originaux.',
      'flow.title': 'Parcours de procédure et de documents',
      'flow.intro': 'Choisissez un type pour voir un parcours général et les avertissements relatifs aux documents. L’ordre exact, les documents et les critères relèvent du bureau d’immigration compétent et peuvent différer selon le cas.',
      'interview.title': 'Salle d’étude pour l’entretien de naturalisation',
      'interview.intro': 'Préparez-vous étape par étape : comprenez le processus, étudiez les thèmes essentiels, parcourez les questions d’entraînement, faites un entretien simulé et consultez des vidéos de référence. Chaque question est un support d’entraînement, et non une question réelle ou officielle d’examens passés.',
      'kiip.title': 'Parcours d’étude pré-évaluation / évaluation complète',
      'kiip.intro': 'Le KIIP attribue un niveau via la pré-évaluation, puis mène à l’évaluation complète (y compris la version naturalisation). Le terminer ne signifie pas en soi l’approbation de la naturalisation.',
      'videos.title': 'Vidéos / supports de référence',
      'videos.intro': 'Listes de lecture et chaînes fournies par les utilisateurs, organisées à titre de référence uniquement. Aucun sous-titre ni transcription n’est conservé, et ce ne sont pas des supports officiels.',
      'waymaker.title': 'Coach nationalité Waymaker',
      'waymaker.heading': 'Posez des questions et entraînez-vous',
      'waymaker.desc': 'Le coach guide nationalité explique en distinguant la loi de la directive ; le coach d’entretien examine votre réponse saisie et propose un exemple plus naturel et une question de suivi. Tout se fait par texte, sans voix.',
      'waymaker.note': 'Il ne prédit jamais la réussite ou l’échec ; les avis individuels et le bureau d’immigration ont toujours la priorité.',
      'waymaker.ctaGuide': 'Ouvrir le coach guide nationalité', 'waymaker.ctaInterview': 'Entretien simulé avec le coach',
      'badge.official': 'Basé sur des sources officielles', 'badge.notOfficial': 'Pas une question officielle d’examen passé', 'badge.unofficialVideo': 'Référence non officielle',
      'footer.note': 'New Home by Paradiso n’est ni affilié ni rattaché à un organisme officiel. Toutes les directives sont fournies à titre d’étude ; confirmez auprès du ministère de la Justice, du bureau d’immigration, de HiKorea ou du 1345.',
      'footer.back': '← Retour à l’accueil nationalité',
      'filter.all': 'Tout', 'who': 'À qui cela s’adresse', 'flowLabel': 'Parcours général', 'docNote': 'Avertissements sur les documents',
      'relatedLaws': 'Lois connexes', 'relatedSources': 'Sources officielles', 'caution': 'Attention', 'confirmNeeded': 'À confirmer',
      'caseVaries': 'Peut varier selon le cas individuel', 'viewFlow': 'Voir le déroulé de la réponse', 'guidance': 'Guide de réponse',
      'goodStructure': 'Bonne structure de réponse', 'riskyPatterns': 'Schémas à éviter', 'practiceWaymaker': 'S’entraîner avec Waymaker',
      'rooms.understand': 'Comprendre le processus', 'rooms.topics': 'Thèmes essentiels', 'rooms.questions': 'Questions d’entraînement',
      'rooms.mock': 'Entretien simulé', 'rooms.videos': 'Vidéos de référence',
      'randomQ': 'Question aléatoire', 'searchQ': 'Rechercher des questions', 'allCats': 'Tous les thèmes', 'allDiffs': 'Tous les niveaux',
      'mock.todayQ': 'Question d’entraînement du jour', 'mock.next': 'Question suivante', 'mock.placeholder': 'Saisissez votre réponse ici en coréen. Ajouter une raison et un exemple aide.',
      'mock.checkLocal': 'Vérifier ma réponse', 'mock.startWaymaker': 'Démarrer l’entretien simulé Waymaker', 'mock.retry': 'Réécrire la réponse',
      'mock.strengths': 'Points forts', 'mock.improvements': 'À améliorer', 'mock.risky': 'Expressions à surveiller',
      'mock.revised': 'Exemple plus naturel', 'mock.followup': 'Question d’entraînement suivante', 'mock.tip': 'Conseil d’étude',
      'mock.loading': 'Waymaker examine votre réponse…',
      'mock.aiFail': 'Impossible de charger le retour de l’IA. Veuillez d’abord consulter les résultats de base.',
      'mock.localTitle': 'Vérification de base (hors ligne)', 'mock.noAnswer': 'Veuillez d’abord saisir une réponse.',
      'understand.heading': 'Comment la préparation à l’entretien et aux connaissances de base s’articule-t-elle ?',
      'understand.body': 'La préparation à la naturalisation relie généralement l’étude du KIIP, les évaluations préalable/complète et l’entretien dans le cadre de l’examen de naturalisation. L’entretien vérifie les connaissances de base et la communication plutôt que des réponses mémorisées.',
      'understand.warn': 'Qui est entretenu, le contenu et toute dispense dépendent du cas individuel et de l’avis. Ceci n’est qu’une référence d’étude ; votre avis individuel et le bureau d’immigration compétent ont toujours la priorité.',
      'understand.steps': 'Exemple de parcours de préparation',
      'sourceLabel.official_kiip': 'Lié au KIIP', 'sourceLabel.official_socinet': 'Lié à l’évaluation',
      'sourceLabel.practice': 'Entraînement', 'sourceLabel.internal_guidance': 'Guide de comportement',
      'sourceLabel.official_law': 'Référence légale', 'sourceLabel.official_notice': 'Référence d’avis officiel', 'sourceLabel.video_reference_topic': 'Thème vidéo',
      'studyFocus': 'Axe d’étude', 'noResults': 'Aucun résultat correspondant.',
      'videoDisclaimer': 'Les supports vidéo sont des références non officielles et ne représentent pas de vraies questions d’entretien ni des questions officielles d’examens passés du ministère de la Justice.',
      'openLink': 'Ouvrir', 'difficulty.easy': 'Facile', 'difficulty.medium': 'Moyen', 'difficulty.hard': 'Difficile',
      'localCheck.tooShort': 'Votre réponse est très courte. Essayez d’ajouter une phrase pour une raison et une pour une expérience concrète.',
      'localCheck.direct': 'C’est plus solide quand une réponse directe à la question vient en premier.',
      'localCheck.vague': 'Cela paraît un peu vague. Ajoutez un exemple ou une expérience concrète.',
      'localCheck.structure': 'Une raison et un exemple donnent une bonne structure à votre réponse.',
      'localCheck.length': 'La longueur est appropriée. Transmettez clairement le point clé.',
      'localCheck.specific': 'Elle comprend une expérience ou un exemple concret, ce qui est convaincant.',
      'localCheck.risky': 'Il est plus prudent d’éviter de ne mettre en avant que les avantages, l’argent ou le fait d’éviter des obligations.',
      'localCheck.okStart': 'Vous avez donné une réponse claire à la question.',
      'rubric.title': 'Grille de réponse', 'rubric.direct': 'Réponse directe', 'rubric.specific': 'Exemple concret',
      'rubric.structure': 'Raison et structure', 'rubric.length': 'Longueur adéquate', 'rubric.attitude': 'Formulation sûre',
      'rubric.ok': 'Bien', 'rubric.improve': 'À améliorer',
      'cautionCoach': 'Ce retour est destiné à l’entraînement et ne garantit aucun résultat d’examen.'
    },
    es: {
      'hero.kicker': 'Servicios de nacionalidad y preparación de la entrevista',
      'hero.title': 'Servicios de nacionalidad y preparación de la entrevista de naturalización, en un solo lugar',
      'hero.lead': 'Naturalización, recuperación de la nacionalidad, pérdida/renuncia, nacionalidad múltiple, el juramento del ciudadano y la preparación de la entrevista: revise un proceso cercano a su situación según la ley y las directrices oficiales, y luego practique con preguntas y una entrevista simulada.',
      'hero.ctaPrimary': 'Comenzar la preparación de la entrevista', 'hero.ctaSecondary': 'Explorar los servicios de nacionalidad',
      'global.disclaimer': 'Esta es una herramienta de estudio para ayudarle a consultar los servicios de nacionalidad y a prepararse para la entrevista de naturalización y la evaluación de conocimientos básicos. No garantiza ningún resultado de la revisión. Confirme siempre las directrices oficiales y los avisos individuales con el Ministerio de Justicia · oficina de inmigración y extranjería.',
      'about.title': 'Explorar los servicios de nacionalidad',
      'about.intro': 'Elija un tipo de servicio para ver qué es, a quién se dirige en general, el proceso habitual, las advertencias sobre documentos, las leyes relacionadas y las fuentes oficiales. Cada caso puede diferir.',
      'laws.title': 'Leyes y directrices relacionadas',
      'laws.intro': 'Explore por tipo las fuentes oficiales que sustentan el trabajo de nacionalidad. Los avisos locales y las explicaciones secundarias se marcan por separado. Abra los enlaces externos para leer los originales.',
      'flow.title': 'Proceso y flujo de documentos',
      'flow.intro': 'Elija un tipo para ver un proceso general y las advertencias sobre documentos. El orden, los documentos y los criterios exactos dependen de la oficina de inmigración competente y pueden diferir según el caso.',
      'interview.title': 'Sala de estudio para la entrevista de naturalización',
      'interview.intro': 'Prepárese paso a paso: comprenda el proceso, estudie los temas clave, revise preguntas de práctica, haga una entrevista simulada y consulte vídeos de referencia. Cada pregunta es material de práctica, no una pregunta real ni oficial de exámenes pasados.',
      'kiip.title': 'Flujo de estudio de preevaluación / evaluación integral',
      'kiip.intro': 'El KIIP asigna un nivel mediante la preevaluación y luego conduce a la evaluación integral (incluida la versión de naturalización). Completarlo no significa por sí mismo la aprobación de la naturalización.',
      'videos.title': 'Vídeos / materiales de referencia',
      'videos.intro': 'Listas de reproducción y canales proporcionados por los usuarios, organizados solo como referencia. No se almacenan subtítulos ni transcripciones, y no son materiales oficiales.',
      'waymaker.title': 'Coach de nacionalidad Waymaker',
      'waymaker.heading': 'Pregunte y practique',
      'waymaker.desc': 'El coach de orientación de nacionalidad explica distinguiendo la ley de la directriz; el coach de entrevista revisa la respuesta que escribe y sugiere un ejemplo más natural y una pregunta de seguimiento. Es principalmente por texto, sin voz.',
      'waymaker.note': 'Nunca predice aprobado o suspenso; los avisos individuales y la oficina de inmigración siempre tienen prioridad.',
      'waymaker.ctaGuide': 'Abrir el coach de orientación de nacionalidad', 'waymaker.ctaInterview': 'Entrevista simulada con el coach',
      'badge.official': 'Basado en fuentes oficiales', 'badge.notOfficial': 'No es una pregunta oficial de exámenes pasados', 'badge.unofficialVideo': 'Referencia no oficial',
      'footer.note': 'New Home by Paradiso no está afiliado ni forma parte de ningún organismo oficial. Toda la orientación es de referencia para el estudio; confirme con el Ministerio de Justicia, la oficina de inmigración, HiKorea o el 1345.',
      'footer.back': '← Volver al inicio de nacionalidad',
      'filter.all': 'Todo', 'who': 'A quién va dirigido', 'flowLabel': 'Proceso general', 'docNote': 'Advertencias sobre documentos',
      'relatedLaws': 'Leyes relacionadas', 'relatedSources': 'Fuentes oficiales', 'caution': 'Atención', 'confirmNeeded': 'Necesita confirmación',
      'caseVaries': 'Puede variar según el caso individual', 'viewFlow': 'Ver el flujo de la respuesta', 'guidance': 'Guía de respuesta',
      'goodStructure': 'Buena estructura de respuesta', 'riskyPatterns': 'Patrones que evitar', 'practiceWaymaker': 'Practicar con Waymaker',
      'rooms.understand': 'Comprender el proceso', 'rooms.topics': 'Temas clave', 'rooms.questions': 'Preguntas de práctica',
      'rooms.mock': 'Entrevista simulada', 'rooms.videos': 'Vídeos de referencia',
      'randomQ': 'Pregunta aleatoria', 'searchQ': 'Buscar preguntas', 'allCats': 'Todos los temas', 'allDiffs': 'Todos los niveles',
      'mock.todayQ': 'Pregunta de práctica de hoy', 'mock.next': 'Siguiente pregunta', 'mock.placeholder': 'Escriba aquí su respuesta en coreano. Añadir un motivo y un ejemplo ayuda.',
      'mock.checkLocal': 'Comprobar mi respuesta', 'mock.startWaymaker': 'Iniciar la entrevista simulada de Waymaker', 'mock.retry': 'Reescribir la respuesta',
      'mock.strengths': 'Puntos fuertes', 'mock.improvements': 'Por mejorar', 'mock.risky': 'Expresiones que vigilar',
      'mock.revised': 'Ejemplo más natural', 'mock.followup': 'Siguiente pregunta de práctica', 'mock.tip': 'Consejo de estudio',
      'mock.loading': 'Waymaker está revisando su respuesta…',
      'mock.aiFail': 'No se pudo cargar la respuesta de la IA. Consulte primero los resultados básicos.',
      'mock.localTitle': 'Comprobación básica (sin conexión)', 'mock.noAnswer': 'Escriba primero una respuesta.',
      'understand.heading': '¿Cómo encajan la preparación de la entrevista y los conocimientos básicos?',
      'understand.body': 'La preparación para la naturalización suele conectar el estudio del KIIP, las evaluaciones previa/integral y la entrevista dentro de la revisión de naturalización. La entrevista comprueba los conocimientos básicos y la comunicación, no respuestas memorizadas.',
      'understand.warn': 'A quién se entrevista, el contenido y cualquier exención dependen del caso individual y del aviso. Esto es solo referencia de estudio; su aviso individual y la oficina de inmigración competente siempre tienen prioridad.',
      'understand.steps': 'Ejemplo de proceso de preparación',
      'sourceLabel.official_kiip': 'Vinculado al KIIP', 'sourceLabel.official_socinet': 'Vinculado a la evaluación',
      'sourceLabel.practice': 'Práctica', 'sourceLabel.internal_guidance': 'Guía de actitud',
      'sourceLabel.official_law': 'Referencia legal', 'sourceLabel.official_notice': 'Referencia de aviso oficial', 'sourceLabel.video_reference_topic': 'Tema del vídeo',
      'studyFocus': 'Enfoque de estudio', 'noResults': 'No hay resultados coincidentes.',
      'videoDisclaimer': 'Los materiales de vídeo son referencias no oficiales y no representan preguntas reales de la entrevista ni preguntas oficiales de exámenes pasados del Ministerio de Justicia.',
      'openLink': 'Abrir', 'difficulty.easy': 'Fácil', 'difficulty.medium': 'Medio', 'difficulty.hard': 'Difícil',
      'localCheck.tooShort': 'Su respuesta es muy corta. Intente añadir una frase para un motivo y otra para una experiencia concreta.',
      'localCheck.direct': 'Es más sólido cuando una respuesta directa a la pregunta aparece primero.',
      'localCheck.vague': 'Se lee algo vago. Añada un ejemplo o experiencia concreta.',
      'localCheck.structure': 'Un motivo y un ejemplo dan a su respuesta una buena estructura.',
      'localCheck.length': 'La longitud es adecuada. Transmita el punto clave con claridad.',
      'localCheck.specific': 'Incluye una experiencia o un ejemplo concreto, lo cual es convincente.',
      'localCheck.risky': 'Es más seguro evitar destacar solo los beneficios, el dinero o la evasión de deberes.',
      'localCheck.okStart': 'Ha dado una respuesta clara a la pregunta.',
      'rubric.title': 'Rúbrica de la respuesta', 'rubric.direct': 'Respuesta directa', 'rubric.specific': 'Ejemplo concreto',
      'rubric.structure': 'Motivo y estructura', 'rubric.length': 'Longitud adecuada', 'rubric.attitude': 'Expresión segura',
      'rubric.ok': 'Suficiente', 'rubric.improve': 'Mejorar',
      'cautionCoach': 'Este comentario es para práctica y no garantiza ningún resultado de la revisión.'
    },
    ar: {
      'hero.kicker': 'خدمات الجنسية والتحضير للمقابلة',
      'hero.title': 'خدمات الجنسية والتحضير لمقابلة التجنّس، في مكان واحد',
      'hero.lead': 'التجنّس واستعادة الجنسية وفقدانها أو التخلي عنها وتعدّد الجنسية ويمين المواطن والتحضير للمقابلة — راجع مساراً قريباً من حالتك بناءً على القوانين والإرشادات الرسمية، ثم تدرّب بالأسئلة وبمقابلة تجريبية.',
      'hero.ctaPrimary': 'ابدأ التحضير للمقابلة', 'hero.ctaSecondary': 'تصفّح خدمات الجنسية',
      'global.disclaimer': 'هذه أداة تعليمية تساعدك على الاطلاع على خدمات الجنسية والتحضير لمقابلة التجنّس وتقييم المعارف الأساسية. وهي لا تضمن أي نتيجة للمراجعة. تأكّد دائماً من الإرشادات الرسمية والإشعارات الفردية لدى وزارة العدل · مكتب الهجرة والأجانب.',
      'about.title': 'استكشاف خدمات الجنسية',
      'about.intro': 'اختر نوع الخدمة لترى ماهيتها ولمن تُوجّه عادةً، والمسار المعتاد، وتنبيهات المستندات، والقوانين ذات الصلة والمصادر الرسمية. وقد تختلف كل حالة على حدة.',
      'laws.title': 'القوانين والإرشادات ذات الصلة',
      'laws.intro': 'تصفّح حسب النوع المصادر الرسمية التي يستند إليها عمل الجنسية. تُميَّز الإشعارات المحلية والشروحات الثانوية على حدة. افتح الروابط الخارجية لقراءة النصوص الأصلية.',
      'flow.title': 'مسار الإجراء والمستندات',
      'flow.intro': 'اختر نوعاً لترى مساراً عاماً وتنبيهات المستندات. الترتيب والمستندات والمعايير الدقيقة تتبع مكتب الهجرة المختص وقد تختلف حسب الحالة.',
      'interview.title': 'غرفة دراسة مقابلة التجنّس',
      'interview.intro': 'تحضّر خطوة بخطوة: افهم الإجراء، وادرس المواضيع الأساسية، وتصفّح أسئلة التدريب، وأجرِ مقابلة تجريبية، وراجع مقاطع الفيديو المرجعية. كل سؤال هو مادة تدريب، وليس سؤالاً حقيقياً أو سؤالاً رسمياً سابقاً.',
      'kiip.title': 'مسار دراسة التقييم المسبق / التقييم الشامل',
      'kiip.intro': 'يحدّد برنامج KIIP المستوى عبر التقييم المسبق، ثم يقود إلى التقييم الشامل (بما في ذلك نسخة التجنّس). وإكماله بذاته لا يعني الموافقة على التجنّس.',
      'videos.title': 'مقاطع فيديو / مواد مرجعية',
      'videos.intro': 'قوائم تشغيل وقنوات قدّمها المستخدمون، منظّمة للمرجعية فقط. لا تُخزَّن أي ترجمات أو نصوص، وهي ليست مواد رسمية.',
      'waymaker.title': 'مدرّب الجنسية Waymaker',
      'waymaker.heading': 'اسأل وتدرّب',
      'waymaker.desc': 'يشرح مدرّب إرشاد الجنسية مع التمييز بين القانون والإرشاد؛ ويراجع مدرّب المقابلة إجابتك المكتوبة ويقترح مثالاً أكثر طبيعية وسؤالاً للمتابعة. يعتمد على النص أولاً، دون حاجة إلى الصوت.',
      'waymaker.note': 'لا يتنبّأ أبداً بالنجاح أو الرسوب؛ وتبقى الإشعارات الفردية ومكتب الهجرة لهما الأولوية دائماً.',
      'waymaker.ctaGuide': 'افتح مدرّب إرشاد الجنسية', 'waymaker.ctaInterview': 'مقابلة تجريبية مع المدرّب',
      'badge.official': 'استناداً إلى مصادر رسمية', 'badge.notOfficial': 'ليس سؤالاً رسمياً سابقاً', 'badge.unofficialVideo': 'مرجع غير رسمي',
      'footer.note': 'New Home by Paradiso ليست منتسبة إلى أي جهة رسمية ولا جزءاً منها. كل الإرشادات للمرجعية الدراسية؛ تأكّد لدى وزارة العدل أو مكتب الهجرة أو HiKorea أو 1345.',
      'footer.back': '→ العودة إلى صفحة الجنسية الرئيسية',
      'filter.all': 'الكل', 'who': 'لمن هذا', 'flowLabel': 'المسار العام', 'docNote': 'تنبيهات المستندات',
      'relatedLaws': 'القوانين ذات الصلة', 'relatedSources': 'المصادر الرسمية', 'caution': 'تنبيه', 'confirmNeeded': 'يلزم التأكيد',
      'caseVaries': 'قد يختلف حسب الحالة الفردية', 'viewFlow': 'عرض مسار الإجابة', 'guidance': 'دليل الإجابة',
      'goodStructure': 'بنية إجابة جيدة', 'riskyPatterns': 'أنماط ينبغي تجنّبها', 'practiceWaymaker': 'تدرّب مع Waymaker',
      'rooms.understand': 'فهم الإجراء', 'rooms.topics': 'المواضيع الأساسية', 'rooms.questions': 'أسئلة التدريب',
      'rooms.mock': 'مقابلة تجريبية', 'rooms.videos': 'مقاطع فيديو مرجعية',
      'randomQ': 'سؤال عشوائي', 'searchQ': 'بحث في الأسئلة', 'allCats': 'كل المواضيع', 'allDiffs': 'كل المستويات',
      'mock.todayQ': 'سؤال تدريب اليوم', 'mock.next': 'السؤال التالي', 'mock.placeholder': 'اكتب إجابتك هنا بالكورية. إضافة سبب وتجربة ملموسة تساعد.',
      'mock.checkLocal': 'تحقّق من إجابتي', 'mock.startWaymaker': 'ابدأ مقابلة Waymaker التجريبية', 'mock.retry': 'أعد كتابة الإجابة',
      'mock.strengths': 'نقاط القوة', 'mock.improvements': 'ما ينبغي تحسينه', 'mock.risky': 'عبارات يُنتبه إليها',
      'mock.revised': 'مثال أكثر طبيعية', 'mock.followup': 'سؤال التدريب التالي', 'mock.tip': 'نصيحة دراسية',
      'mock.loading': 'يراجع Waymaker إجابتك…',
      'mock.aiFail': 'تعذّر تحميل ملاحظات الذكاء الاصطناعي. يرجى الاطلاع أولاً على النتائج الأساسية.',
      'mock.localTitle': 'فحص أساسي (دون اتصال)', 'mock.noAnswer': 'يرجى كتابة إجابة أولاً.',
      'understand.heading': 'كيف يتكامل التحضير للمقابلة والمعارف الأساسية؟',
      'understand.body': 'عادةً ما يربط التحضير للتجنّس بين دراسة KIIP وتقييمَي ما قبل التقييم والتقييم الشامل، والمقابلة ضمن مراجعة التجنّس. تتحقّق المقابلة من المعارف الأساسية والتواصل أكثر من الإجابات المحفوظة.',
      'understand.warn': 'مَن تُجرى معه المقابلة ومحتواها وأي إعفاء يعتمد على الحالة الفردية والإشعار. هذا للمرجعية الدراسية فقط؛ ويبقى إشعارك الفردي ومكتب الهجرة المختص لهما الأولوية دائماً.',
      'understand.steps': 'مثال على مسار التحضير',
      'sourceLabel.official_kiip': 'مرتبط بـ KIIP', 'sourceLabel.official_socinet': 'مرتبط بالتقييم',
      'sourceLabel.practice': 'تدريب', 'sourceLabel.internal_guidance': 'دليل السلوك',
      'sourceLabel.official_law': 'مرجع قانوني', 'sourceLabel.official_notice': 'مرجع إشعار رسمي', 'sourceLabel.video_reference_topic': 'موضوع الفيديو',
      'studyFocus': 'محور الدراسة', 'noResults': 'لا توجد نتائج مطابقة.',
      'videoDisclaimer': 'مواد الفيديو مراجع غير رسمية ولا تمثّل أسئلة مقابلة حقيقية أو أسئلة رسمية سابقة من وزارة العدل.',
      'openLink': 'فتح', 'difficulty.easy': 'سهل', 'difficulty.medium': 'متوسط', 'difficulty.hard': 'صعب',
      'localCheck.tooShort': 'إجابتك قصيرة جداً. حاول إضافة جملة للسبب وأخرى لتجربة ملموسة.',
      'localCheck.direct': 'يكون أكثر ثباتاً عندما تأتي الإجابة المباشرة على السؤال أولاً.',
      'localCheck.vague': 'تبدو غامضة بعض الشيء. أضف مثالاً أو تجربة ملموسة واحدة.',
      'localCheck.structure': 'وجود سبب ومثال يمنح إجابتك بنية جيدة.',
      'localCheck.length': 'الطول مناسب. أوصل الفكرة الأساسية بوضوح.',
      'localCheck.specific': 'تتضمّن تجربة أو مثالاً ملموساً، وهذا مقنع.',
      'localCheck.risky': 'من الأأمن تجنّب التركيز فقط على المزايا أو المال أو التهرّب من الواجبات.',
      'localCheck.okStart': 'لقد قدّمت إجابة واضحة على السؤال.',
      'rubric.title': 'معايير الإجابة', 'rubric.direct': 'إجابة مباشرة', 'rubric.specific': 'مثال ملموس',
      'rubric.structure': 'السبب والبنية', 'rubric.length': 'طول مناسب', 'rubric.attitude': 'صياغة آمنة',
      'rubric.ok': 'كافٍ', 'rubric.improve': 'تحسين',
      'cautionCoach': 'هذه الملاحظات للتدريب ولا تضمن أي نتيجة للمراجعة.'
    },
    de: {
      'hero.kicker': 'Staatsangehörigkeitsdienste & Vorbereitung auf das Interview',
      'hero.title': 'Staatsangehörigkeitsdienste und Vorbereitung auf das Einbürgerungsinterview an einem Ort',
      'hero.lead': 'Einbürgerung, Wiedererlangung der Staatsangehörigkeit, Verlust/Aufgabe, mehrfache Staatsangehörigkeit, der Bürgereid und die Interviewvorbereitung — sehen Sie sich anhand offizieller Gesetze und Hinweise einen Ablauf an, der Ihrer Situation nahekommt, und üben Sie dann mit Fragen und einem Probeinterview.',
      'hero.ctaPrimary': 'Interviewvorbereitung starten', 'hero.ctaSecondary': 'Staatsangehörigkeitsdienste durchsehen',
      'global.disclaimer': 'Dies ist ein Lernwerkzeug, das Ihnen hilft, Staatsangehörigkeitsdienste zu prüfen und sich auf das Einbürgerungsinterview und die Prüfung der Grundkenntnisse vorzubereiten. Es garantiert kein Prüfungsergebnis. Bestätigen Sie offizielle Hinweise und individuelle Bescheide stets beim Justizministerium · der Einwanderungs- und Ausländerbehörde.',
      'about.title': 'Staatsangehörigkeitsdienste erkunden',
      'about.intro': 'Wählen Sie einen Diensttyp, um zu sehen, worum es geht, für wen er in der Regel gedacht ist, den typischen Ablauf, Dokumentenhinweise, zugehörige Gesetze und offizielle Quellen. Einzelfälle können abweichen.',
      'laws.title': 'Zugehörige Gesetze & Richtlinien',
      'laws.intro': 'Durchsuchen Sie nach Typ die offiziellen Quellen, die der Staatsangehörigkeitsarbeit zugrunde liegen. Lokale Bekanntmachungen und ergänzende Erläuterungen sind gesondert gekennzeichnet. Öffnen Sie externe Links, um die Originale zu lesen.',
      'flow.title': 'Verfahrens- und Dokumentenablauf',
      'flow.intro': 'Wählen Sie einen Typ, um einen allgemeinen Ablauf und Dokumentenhinweise zu sehen. Die genaue Reihenfolge, Dokumente und Kriterien richten sich nach der zuständigen Einwanderungsbehörde und können je nach Fall abweichen.',
      'interview.title': 'Lernraum für das Einbürgerungsinterview',
      'interview.intro': 'Bereiten Sie sich Schritt für Schritt vor: Verstehen Sie den Prozess, lernen Sie Kernthemen, sehen Sie sich Übungsfragen an, führen Sie ein Probeinterview durch und sehen Sie sich Referenzvideos an. Jede Frage ist Übungsmaterial, keine echte oder offizielle frühere Prüfungsfrage.',
      'kiip.title': 'Lernablauf Vorabbewertung / Gesamtbewertung',
      'kiip.intro': 'Das KIIP weist über die Vorabbewertung eine Stufe zu und führt dann zur Gesamtbewertung (einschließlich der Einbürgerungsversion). Der Abschluss bedeutet für sich genommen keine Einbürgerungsgenehmigung.',
      'videos.title': 'Referenzvideos / -materialien',
      'videos.intro': 'Von Nutzern bereitgestellte Wiedergabelisten und Kanäle, ausschließlich zur Referenz geordnet. Es werden keine Untertitel oder Transkripte gespeichert, und dies sind keine offiziellen Materialien.',
      'waymaker.title': 'Waymaker-Coach für Staatsangehörigkeit',
      'waymaker.heading': 'Fragen Sie und üben Sie',
      'waymaker.desc': 'Der Staatsangehörigkeits-Leitfaden-Coach erklärt und unterscheidet dabei Gesetz von Hinweis; der Interview-Coach prüft Ihre eingegebene Antwort und schlägt ein natürlicheres Beispiel sowie eine Anschlussfrage vor. Es funktioniert primär per Text, ohne Stimme.',
      'waymaker.note': 'Er sagt nie Bestehen/Nichtbestehen voraus; individuelle Bescheide und die Einwanderungsbehörde haben immer Vorrang.',
      'waymaker.ctaGuide': 'Staatsangehörigkeits-Leitfaden-Coach öffnen', 'waymaker.ctaInterview': 'Probeinterview mit dem Coach',
      'badge.official': 'Auf Basis offizieller Quellen', 'badge.notOfficial': 'Keine offizielle frühere Prüfungsfrage', 'badge.unofficialVideo': 'Inoffizielle Referenz',
      'footer.note': 'New Home by Paradiso ist mit keiner offiziellen Stelle verbunden oder Teil davon. Alle Hinweise dienen der Lernreferenz; bestätigen Sie beim Justizministerium, der Einwanderungsbehörde, HiKorea oder 1345.',
      'footer.back': '← Zurück zur Staatsangehörigkeits-Startseite',
      'filter.all': 'Alle', 'who': 'Für wen das ist', 'flowLabel': 'Allgemeiner Ablauf', 'docNote': 'Dokumentenhinweise',
      'relatedLaws': 'Zugehörige Gesetze', 'relatedSources': 'Offizielle Quellen', 'caution': 'Achtung', 'confirmNeeded': 'Bestätigung erforderlich',
      'caseVaries': 'Kann je nach Einzelfall variieren', 'viewFlow': 'Antwortablauf ansehen', 'guidance': 'Antwortleitfaden',
      'goodStructure': 'Gute Antwortstruktur', 'riskyPatterns': 'Zu vermeidende Muster', 'practiceWaymaker': 'Mit Waymaker üben',
      'rooms.understand': 'Den Prozess verstehen', 'rooms.topics': 'Kernthemen', 'rooms.questions': 'Übungsfragen',
      'rooms.mock': 'Probeinterview', 'rooms.videos': 'Referenzvideos',
      'randomQ': 'Zufallsfrage', 'searchQ': 'Fragen suchen', 'allCats': 'Alle Themen', 'allDiffs': 'Alle Stufen',
      'mock.todayQ': 'Heutige Übungsfrage', 'mock.next': 'Nächste Frage', 'mock.placeholder': 'Geben Sie Ihre Antwort hier auf Koreanisch ein. Ein Grund und ein Beispiel helfen.',
      'mock.checkLocal': 'Meine Antwort prüfen', 'mock.startWaymaker': 'Waymaker-Probeinterview starten', 'mock.retry': 'Antwort neu schreiben',
      'mock.strengths': 'Stärken', 'mock.improvements': 'Zu verbessern', 'mock.risky': 'Zu beachtende Ausdrücke',
      'mock.revised': 'Natürlicheres Beispiel', 'mock.followup': 'Nächste Übungsfrage', 'mock.tip': 'Lerntipp',
      'mock.loading': 'Waymaker prüft Ihre Antwort…',
      'mock.aiFail': 'KI-Feedback konnte nicht geladen werden. Bitte prüfen Sie zuerst die Basisergebnisse.',
      'mock.localTitle': 'Basisprüfung (offline)', 'mock.noAnswer': 'Bitte geben Sie zuerst eine Antwort ein.',
      'understand.heading': 'Wie greifen Interview- und Grundkenntnisvorbereitung ineinander?',
      'understand.body': 'Die Einbürgerungsvorbereitung verbindet in der Regel das KIIP-Lernen, die Vorab-/Gesamtbewertungen und das Interview im Rahmen der Einbürgerungsprüfung. Das Interview prüft Grundkenntnisse und Kommunikation eher als auswendig gelernte Antworten.',
      'understand.warn': 'Wer interviewt wird, der Inhalt und etwaige Befreiungen hängen vom Einzelfall und vom Bescheid ab. Dies ist nur eine Lernreferenz; Ihr individueller Bescheid und die zuständige Einwanderungsbehörde haben immer Vorrang.',
      'understand.steps': 'Beispiel für einen Vorbereitungsablauf',
      'sourceLabel.official_kiip': 'Mit KIIP verknüpft', 'sourceLabel.official_socinet': 'Mit Bewertung verknüpft',
      'sourceLabel.practice': 'Übung', 'sourceLabel.internal_guidance': 'Verhaltensleitfaden',
      'sourceLabel.official_law': 'Gesetzesreferenz', 'sourceLabel.official_notice': 'Referenz offizieller Hinweis', 'sourceLabel.video_reference_topic': 'Videothema',
      'studyFocus': 'Lernschwerpunkt', 'noResults': 'Keine passenden Ergebnisse.',
      'videoDisclaimer': 'Videomaterialien sind inoffizielle Referenzen und stellen keine echten Interviewfragen oder offiziellen früheren Prüfungsfragen des Justizministeriums dar.',
      'openLink': 'Öffnen', 'difficulty.easy': 'Leicht', 'difficulty.medium': 'Mittel', 'difficulty.hard': 'Schwer',
      'localCheck.tooShort': 'Ihre Antwort ist sehr kurz. Versuchen Sie, je einen Satz für einen Grund und eine konkrete Erfahrung hinzuzufügen.',
      'localCheck.direct': 'Es ist sicherer, wenn eine direkte Antwort auf die Frage zuerst kommt.',
      'localCheck.vague': 'Es liest sich etwas vage. Fügen Sie ein konkretes Beispiel oder eine Erfahrung hinzu.',
      'localCheck.structure': 'Ein Grund und ein Beispiel geben Ihrer Antwort eine gute Struktur.',
      'localCheck.length': 'Die Länge ist angemessen. Vermitteln Sie den Kernpunkt klar.',
      'localCheck.specific': 'Sie enthält eine konkrete Erfahrung oder ein Beispiel, was überzeugend ist.',
      'localCheck.risky': 'Es ist sicherer, nicht nur Vorteile, Geld oder das Vermeiden von Pflichten zu betonen.',
      'localCheck.okStart': 'Sie haben eine klare Antwort auf die Frage gegeben.',
      'rubric.title': 'Antwortraster', 'rubric.direct': 'Direkte Antwort', 'rubric.specific': 'Konkretes Beispiel',
      'rubric.structure': 'Grund & Struktur', 'rubric.length': 'Angemessene Länge', 'rubric.attitude': 'Sichere Formulierung',
      'rubric.ok': 'Ausreichend', 'rubric.improve': 'Verbessern',
      'cautionCoach': 'Dieses Feedback dient der Übung und garantiert kein Prüfungsergebnis.'
    }
  };

  // Traditional Chinese is a display layer over zh-CN (assets/js/zh-traditional.js).
  // `lang` is the content locale; `langTrad` activates the converter.
  var langTrad = false;
  // Locales the module ships content for. ko is the canonical fallback.
  var SUPPORTED_LANGS = ['ko', 'en', 'zh-CN', 'ja', 'vi', 'tl', 'id', 'ru', 'fr', 'es', 'ar', 'de'];
  var RTL_LANGS = { ar: true };
  // Map a stored/navigator code (e.g. "pt-BR", "ZH-cn") to a supported pack, ko otherwise.
  function resolveLang(raw) {
    var s = String(raw || '');
    if (s === 'zh-TW' || s === 'zh-Hant') { langTrad = true; return 'zh-CN'; }
    if (s === 'zh-CN' || s === 'zh-Hans' || s.toLowerCase() === 'zh') return 'zh-CN';
    var low = s.toLowerCase();
    var base = low.split(/[-_]/)[0];
    for (var i = 0; i < SUPPORTED_LANGS.length; i++) {
      var code = SUPPORTED_LANGS[i];
      if (code === 'zh-CN') continue; // handled above
      if (low === code || base === code) return code;
    }
    return '';
  }
  var lang = (function () {
    try {
      var resolved = resolveLang(localStorage.getItem('paradiso:language') || '');
      if (resolved) return resolved;
    } catch (e) {}
    return resolveLang(navigator.language || '') || 'ko';
  })();
  function applyTradLayer(on) {
    try { var zt = window.ParadisoZhT; if (!zt) return; if (on) { if (!zt.isActive()) zt.start(); } else if (zt.isActive()) { zt.stop(); } } catch (e) {}
  }
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
    korean_language: { ko: '한국어 의사소통', en: 'Korean communication', 'zh-CN': '韩语沟通', ja: '韓国語コミュニケーション', vi: 'Giao tiếp tiếng Hàn', tl: 'Komunikasyon sa Korean', id: 'Komunikasi bahasa Korea', ru: 'Общение на корейском', fr: 'Communication en coréen', es: 'Comunicación en coreano', ar: 'التواصل بالكورية', de: 'Koreanische Kommunikation' },
    reason_for_naturalization: { ko: '귀화 동기', en: 'Reason for naturalization', 'zh-CN': '归化动机', ja: '帰化の動機', vi: 'Lý do nhập tịch', tl: 'Dahilan ng naturalisasyon', id: 'Alasan naturalisasi', ru: 'Причина натурализации', fr: 'Motif de la naturalisation', es: 'Motivo de la naturalización', ar: 'دافع التجنّس', de: 'Grund der Einbürgerung' },
    life_in_korea: { ko: '한국 생활 경험', en: 'Life in Korea', 'zh-CN': '韩国生活经历', ja: '韓国での生活経験', vi: 'Cuộc sống ở Hàn Quốc', tl: 'Buhay sa Korea', id: 'Kehidupan di Korea', ru: 'Жизнь в Корее', fr: 'Vie en Corée', es: 'Vida en Corea', ar: 'الحياة في كوريا', de: 'Leben in Korea' },
    korean_society: { ko: '대한민국 사회 기본 이해', en: 'Korean society', 'zh-CN': '韩国社会基本了解', ja: '韓国社会の基本理解', vi: 'Xã hội Hàn Quốc', tl: 'Lipunang Korean', id: 'Masyarakat Korea', ru: 'Корейское общество', fr: 'Société coréenne', es: 'Sociedad coreana', ar: 'المجتمع الكوري', de: 'Koreanische Gesellschaft' },
    democratic_order: { ko: '자유민주적 기본질서', en: 'Democratic order', 'zh-CN': '自由民主基本秩序', ja: '自由民主的基本秩序', vi: 'Trật tự dân chủ tự do', tl: 'Demokratikong kaayusan', id: 'Tatanan demokratis', ru: 'Демократический порядок', fr: 'Ordre démocratique', es: 'Orden democrático', ar: 'النظام الديمقراطي الأساسي', de: 'Demokratische Grundordnung' },
    rights_and_duties: { ko: '권리와 의무', en: 'Rights & duties', 'zh-CN': '权利与义务', ja: '権利と義務', vi: 'Quyền và nghĩa vụ', tl: 'Mga karapatan at tungkulin', id: 'Hak dan kewajiban', ru: 'Права и обязанности', fr: 'Droits et devoirs', es: 'Derechos y deberes', ar: 'الحقوق والواجبات', de: 'Rechte und Pflichten' },
    interview_attitude: { ko: '면접 태도', en: 'Interview attitude', 'zh-CN': '面试态度', ja: '面接の態度', vi: 'Thái độ phỏng vấn', tl: 'Saloobin sa interbyu', id: 'Sikap wawancara', ru: 'Поведение на собеседовании', fr: 'Attitude en entretien', es: 'Actitud en la entrevista', ar: 'سلوك المقابلة', de: 'Verhalten im Interview' },
    pre_evaluation_study: { ko: '사전평가/종합평가', en: 'Pre/comprehensive evaluation', 'zh-CN': '事前评价/综合评价', ja: '事前評価/総合評価', vi: 'Đánh giá sơ bộ/tổng hợp', tl: 'Paunang/komprehensibong pagtatasa', id: 'Pra/evaluasi komprehensif', ru: 'Предварительная/комплексная оценка', fr: 'Évaluation préalable/complète', es: 'Evaluación previa/integral', ar: 'التقييم المسبق/الشامل', de: 'Vorab-/Gesamtbewertung' }
  };
  function catLabel(c) { return (CATEGORY_LABELS[c] && (CATEGORY_LABELS[c][lang] || CATEGORY_LABELS[c].ko)) || c; }

  var DATA = { guides: [], sources: [], questions: [], videos: [], topics: [] };
  var sourceById = {};

  /* ----------------------------------------------------------- i18n apply */
  var LANG_TOGGLE_NEXT = { ko: 'en', en: 'zh-CN', 'zh-CN': 'zh-TW', 'zh-TW': 'ko' };
  var LANG_TOGGLE_LABEL = { ko: 'EN', en: '简', 'zh-CN': '繁', 'zh-TW': '한국어' };
  function applyStatic() {
    document.documentElement.lang = langTrad ? 'zh-TW' : lang;
    applyTradLayer(langTrad);
    var nodes = document.querySelectorAll('[data-i18n]');
    for (var i = 0; i < nodes.length; i++) {
      var key = nodes[i].getAttribute('data-i18n');
      var val = t(key);
      if (val != null) nodes[i].textContent = val;
    }
    var cur = langTrad ? 'zh-TW' : lang;
    var lt = el('langToggle'); if (lt) { lt.textContent = LANG_TOGGLE_LABEL[cur] || 'EN'; lt.setAttribute('data-s2t', 'off'); }
  }

  /* --------------------------------------------------- 1. guide browsing */
  var guideFilter = 'all';
  var GUIDE_GROUPS = [
    { id: 'all', ko: '전체', en: 'All', 'zh-CN': '全部' },
    { id: 'naturalization', ko: '귀화', en: 'Naturalization', 'zh-CN': '归化', cats: ['naturalization_general', 'naturalization_simplified', 'naturalization_special', 'naturalization_marriage'] },
    { id: 'restoration', ko: '국적회복', en: 'Restoration', 'zh-CN': '国籍恢复', cats: ['nationality_restoration'] },
    { id: 'lossleave', ko: '국적상실/이탈', en: 'Loss / renunciation', 'zh-CN': '国籍丧失/脱离', cats: ['nationality_loss_report', 'nationality_renunciation', 'nationality_acquisition_report', 'nationality_retention'] },
    { id: 'multiple', ko: '복수국적', en: 'Multiple nationality', 'zh-CN': '复数国籍', cats: ['multiple_nationality', 'foreign_nationality_non_exercise_pledge'] },
    { id: 'oath', ko: '국민선서', en: 'Oath', 'zh-CN': '国民宣誓', cats: ['oath_and_certificate'] },
    { id: 'interview', ko: '면접/평가', en: 'Interview / evaluation', 'zh-CN': '面试/评价', cats: ['interview_review', 'kiip_evaluation', 'review_period_status'] }
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
    var steps = lang === 'zh-CN'
      ? ['社会融合项目（KIIP）·自主学习', '事前评价分配阶段', '分阶段学习', '综合评价（含归化用）', '归化适格审查过程中的面试', '作为整体审查的一部分反映结果']
      : lang === 'en'
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
      var cur = langTrad ? 'zh-TW' : lang;
      var nextSel = LANG_TOGGLE_NEXT[cur] || 'en';
      langTrad = (nextSel === 'zh-TW');
      lang = (nextSel === 'zh-TW' || nextSel === 'zh-CN') ? 'zh-CN' : nextSel;
      try { localStorage.setItem('paradiso:language', nextSel); } catch (e) {}
      applyTradLayer(langTrad);
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
