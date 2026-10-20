/* ============================================================================
 * VISABLE Unified Internationalization Layer (visable-i18n.js)
 * ----------------------------------------------------------------------------
 * Shared, robust, accessible localization controller for all VISABLE surfaces.
 *
 * Supported Locales (15 total):
 *   Tier 1: ko (canonical), en, zh-CN, vi, id
 *   Tier 2: ja, tl, ru, ar (RTL), zh-TW (Traditional script conversion)
 *   Tier 3: fr, es, de, tr, uk
 *
 * Precedence:
 *   1. Explicit URL parameter: ?lang=...
 *   2. Stored preference: localStorage.getItem('paradiso:language')
 *   3. Browser navigator language (where supported)
 *   4. Canonical fallback: 'ko'
 * ============================================================================
 */
(function (global) {
  'use strict';

  var STORAGE_KEY = 'paradiso:language';
  var DEFAULT_LOCALE = 'ko';

  var LOCALE_CONFIG = {
    'ko':    { name: '한국어',           local: '한국어',           short: 'KO', html: 'ko', dir: 'ltr', tier: 1 },
    'en':    { name: 'English',          local: 'English',          short: 'EN', html: 'en', dir: 'ltr', tier: 1 },
    'zh-CN': { name: '简体中文',         local: '简体中文',         short: '简', html: 'zh-CN', dir: 'ltr', tier: 1 },
    'zh-TW': { name: '繁體中文',         local: '繁體中文',         short: '繁', html: 'zh-TW', dir: 'ltr', tier: 2 },
    'vi':    { name: 'Tiếng Việt',       local: 'Tiếng Việt',       short: 'VI', html: 'vi', dir: 'ltr', tier: 1 },
    'id':    { name: 'Bahasa Indonesia', local: 'Bahasa Indonesia', short: 'ID', html: 'id', dir: 'ltr', tier: 1 },
    'ja':    { name: '日本語',           local: '日本語',           short: 'JA', html: 'ja', dir: 'ltr', tier: 2 },
    'tl':    { name: 'Tagalog',          local: 'Tagalog',          short: 'TL', html: 'tl', dir: 'ltr', tier: 2 },
    'ru':    { name: 'Русский',          local: 'Русский',          short: 'RU', html: 'ru', dir: 'ltr', tier: 2 },
    'ar':    { name: 'العربية',          local: 'العربية',          short: 'ع',  html: 'ar', dir: 'rtl', tier: 2 },
    'fr':    { name: 'Français',         local: 'Français',         short: 'FR', html: 'fr', dir: 'ltr', tier: 3 },
    'es':    { name: 'Español',          local: 'Español',          short: 'ES', html: 'es', dir: 'ltr', tier: 3 },
    'de':    { name: 'Deutsch',          local: 'Deutsch',          short: 'DE', html: 'de', dir: 'ltr', tier: 3 },
    'tr':    { name: 'Türkçe',           local: 'Türkçe',           short: 'TR', html: 'tr', dir: 'ltr', tier: 3 },
    'uk':    { name: 'Українська',       local: 'Українська',       short: 'UK', html: 'uk', dir: 'ltr', tier: 3 }
  };

  var LOCALE_ALIASES = {
    'zh': 'zh-CN',
    'zh-cn': 'zh-CN',
    'zh-hans': 'zh-CN',
    'zh-sg': 'zh-CN',
    'zh-tw': 'zh-TW',
    'zh-hant': 'zh-TW',
    'zh-hk': 'zh-TW',
    'fil': 'tl',
    'in': 'id',
    'ja-jp': 'ja',
    'vi-vn': 'vi',
    'id-id': 'id',
    'ru-ru': 'ru',
    'ar-sa': 'ar',
    'ar-ae': 'ar',
    'ar-eg': 'ar',
    'ko-kr': 'ko',
    'en-us': 'en',
    'en-gb': 'en'
  };

  // Dedicated checklist translations across Tier 1, Tier 2, and Tier 3
  var CHECKLIST_STRINGS = {
    // Header & Navigation
    navGuided: {
      ko: '맞춤 안내',
      en: 'Guided Steps',
      'zh-CN': '精准向导',
      'zh-TW': '精準嚮導',
      vi: 'Hướng dẫn cụ thể',
      id: 'Panduan Khusus',
      ja: 'カスタム案内',
      tl: 'Gabay sa Hakbang',
      ru: 'Индивидуальный гид',
      ar: 'إرشادات مخصصة'
    },
    navSearch: {
      ko: '전체 검색',
      en: 'Full Search',
      'zh-CN': '全量搜索',
      'zh-TW': '全量搜尋',
      vi: 'Tìm kiếm tất cả',
      id: 'Pencarian Lengkap',
      ja: '全体検索',
      tl: 'Buong Paghahanap',
      ru: 'Общий поиск',
      ar: 'البحث الشامل'
    },
    navFormHelper: {
      ko: '서식 작성',
      en: 'Form Helper',
      'zh-CN': '表格填写',
      'zh-TW': '表格填寫',
      vi: 'Khai báo biểu mẫu',
      id: 'Bantuan Formulir',
      ja: '書式作成',
      tl: 'Tulong sa Form',
      ru: 'Помощник по анкетам',
      ar: 'مساعد تعبئة النماذج'
    },
    operatorMode: {
      ko: '운영자 모드',
      en: 'Operator Mode',
      'zh-CN': '运营人员模式',
      'zh-TW': '運營人員模式',
      vi: 'Chế độ quản trị',
      id: 'Mode Operator',
      ja: '管理者モード',
      tl: 'Operator Mode',
      ru: 'Режим оператора',
      ar: 'وضع المشرف'
    },
    languageSelectLabel: {
      ko: '언어 선택',
      en: 'Select Language',
      'zh-CN': '选择语言',
      'zh-TW': '選擇語言',
      vi: 'Chọn ngôn ngữ',
      id: 'Pilih Bahasa',
      ja: '言語を選択',
      tl: 'Pumili ng Wika',
      ru: 'Выбор языка',
      ar: 'اختيار اللغة'
    },

    // Hero Section
    heroEyebrow: {
      ko: '대한민국 출입국 행정 서류 안내 / 2026.09 공식 매뉴얼',
      en: 'KOREA IMMIGRATION DOCUMENTS / 2026.09 OFFICIAL MANUAL',
      'zh-CN': '韩国出入境行政材料指南 / 2026.09 官方手册',
      'zh-TW': '韓國出入境行政材料指南 / 2026.09 官方手冊',
      vi: 'HỒ SƠ HÀNH CHÍNH XUẤT NHẬP CẢNH HÀN QUỐC / CẨM NANG 2026.09',
      id: 'PANDUAN DOKUMEN IMIGRASI KOREA / MANUAL RESMI 2026.09',
      ja: '韓国出入国行政書類案内 / 2026.09 公式マニュアル',
      tl: 'MGA DOKUMENTO SA IMIGRASISYON SA KOREA / OPISYAL NA MANWAL 2026.09',
      ru: 'ДОКУМЕНТЫ ДЛЯ ИММИГРАЦИИ В КОРЕЮ / ОФИЦИАЛЬНЫЙ РУКОВОДСТВО 2026.09',
      ar: 'وثائق الهجرة إلى كوريا / الدليل الرسمي 2026.09'
    },
    pageTitleMain: {
      ko: '내 상황에 맞는 서류,',
      en: 'Immigration Documents,',
      'zh-CN': '符合您具体情形的材料，',
      'zh-TW': '符合您具體情形的材料，',
      vi: 'Hồ sơ phù hợp với hoàn cảnh của bạn,',
      id: 'Dokumen Sesuai Situasi Anda,',
      ja: 'あなたの状況に合った書類、',
      tl: 'Mga dokumentong akma sa iyong sitwasyon,',
      ru: 'Документы под вашу ситуацию,',
      ar: 'وثائق الهجرة الخاصة بوضعك،'
    },
    pageTitleSub: {
      ko: '필요한 것부터 쉽고 확실하게.',
      en: 'Simplified, Transparent and Reliable.',
      'zh-CN': '按需梳理，清晰确切。',
      'zh-TW': '按需梳理，清晰確切。',
      vi: 'Rõ ràng, đơn giản và đáng tin cậy.',
      id: 'Mudah, Jelas, dan Terpercaya.',
      ja: '必要なものから分かりやすく確実に。',
      tl: 'Mula sa kailangan nang madali at sigurado.',
      ru: 'Просто, прозрачно и надежно.',
      ar: 'بكل وضوح وسهولة وموثوقية.'
    },
    heroCopy: {
      ko: '체류자격과 신청 업무를 선택하면 필요한 준비사항을 확인할 수 있어요. 같은 자격이어도 신청 상황에 따라 서류가 달라질 수 있습니다.',
      en: 'Select your visa status and procedure to see your required documents. Even with the same status, requirements vary by individual scenario.',
      'zh-CN': '选择滞留资格和申请业务，即可查看所需准备材料。即使持有相同签证，具体申请情形不同所需材料也有所差异。',
      'zh-TW': '選擇滯留資格和申請業務，即可查看所需準備材料。即使持有相同簽證，具體申請情形不同所需材料也有所差異。',
      vi: 'Chọn tư cách cư trú và thủ tục bạn cần để kiểm tra hồ sơ. Cùng một loại visa nhưng tùy trường hợp cụ thể mà hồ sơ có thể khác nhau.',
      id: 'Pilih status tinggal dan prosedur Anda untuk melihat dokumen yang diperlukan. Meskipun status visanya sama, persyaratannya berbeda tergantung skenario.',
      ja: '滞在資格と申請手続きを選択すると、必要な準備書類を確認できます。同じ資格でも申請状況によって書類が異なる場合があります。',
      tl: 'Piliin ang iyong visa status at pamamaraan upang makita ang mga kinakailangang dokumento. Maaaring mag-iba ang mga ito ayon sa sitwasyon.',
      ru: 'Выберите ваш визовый статус и процедуру, чтобы увидеть список необходимых документов. Требования могут различаться в зависимости от ситуации.',
      ar: 'حدد وضع إقامتك والإجراء المطلوب لعرض المستندات اللازمة. حتى مع نفس نوع التأشيرة، تختلف المتطلبات بحسب تفاصيل حالتك.'
    },

    // Stepper Labels
    step1Tab: {
      ko: '1단계: 업무 선택',
      en: 'Step 1: Task',
      'zh-CN': '第1步：选择业务',
      'zh-TW': '第1步：選擇業務',
      vi: 'Bước 1: Chọn thủ tục',
      id: 'Langkah 1: Prosedur',
      ja: 'ステップ1: 手続き選択',
      tl: 'Hakbang 1: Pamamaraan',
      ru: 'Шаг 1: Процедура',
      ar: 'الخطوة 1: الإجراء'
    },
    step1TabDesc: {
      ko: '어떤 업무를 신청하시나요?',
      en: 'What procedure do you need?',
      'zh-CN': '您需要办理哪项业务？',
      'zh-TW': '您需要辦理哪項業務？',
      vi: 'Bạn cần làm thủ tục gì?',
      id: 'Prosedur apa yang Anda butuhkan?',
      ja: 'どの手続きを申請しますか？',
      tl: 'Anong pamamaraan ang kailangan mo?',
      ru: 'Какая процедура вам требуется?',
      ar: 'ما هو الإجراء الذي تحتاجه؟'
    },
    step2Tab: {
      ko: '2단계: 체류자격',
      en: 'Step 2: Visa Status',
      'zh-CN': '第2步：滞留资格',
      'zh-TW': '第2步：滯留資格',
      vi: 'Bước 2: Tư cách cư trú',
      id: 'Langkah 2: Status Visa',
      ja: 'ステップ2: 滞在資格',
      tl: 'Hakbang 2: Visa Status',
      ru: 'Шаг 2: Визовый статус',
      ar: 'الخطوة 2: وضع الإقامة'
    },
    step2TabDesc: {
      ko: '현재/목표 체류자격',
      en: 'Current or target visa code',
      'zh-CN': '当前或目标签证代码',
      'zh-TW': '當前或目標簽證代碼',
      vi: 'Mã visa hiện tại hoặc mục tiêu',
      id: 'Kode visa saat ini atau tujuan',
      ja: '現在または変更希望の資格',
      tl: 'Kasalukuyan o target na visa code',
      ru: 'Текущий или целевой статус',
      ar: 'رمز التأشيرة الحالي أو المستهدف'
    },
    step3Tab: {
      ko: '3단계: 세부 상황',
      en: 'Step 3: Scenario',
      'zh-CN': '第3步：细分情形',
      'zh-TW': '第3步：細分情形',
      vi: 'Bước 3: Tình huống cụ thể',
      id: 'Langkah 3: Skenario',
      ja: 'ステップ3: 詳細状況',
      tl: 'Hakbang 3: Sitwasyon',
      ru: 'Шаг 3: Сценарий',
      ar: 'الخطوة 3: تفاصيل الحالة'
    },
    step3TabDesc: {
      ko: '구체적인 신청 사유',
      en: 'Specific application reason',
      'zh-CN': '具体申请事由',
      'zh-TW': '具體申請事由',
      vi: 'Lý do nộp đơn cụ thể',
      id: 'Alasan permohonan spesifik',
      ja: '具体的な申請理由',
      tl: 'Tiyak na dahilan ng aplikasyon',
      ru: 'Конкретное основание подачи',
      ar: 'سبب التقديم المحدد'
    },
    step4Tab: {
      ko: '4단계: 서류 목록',
      en: 'Step 4: Checklist',
      'zh-CN': '第4步：材料清单',
      'zh-TW': '第4步：材料清單',
      vi: 'Bước 4: Danh mục hồ sơ',
      id: 'Langkah 4: Daftar Dokumen',
      ja: 'ステップ4: 書類リスト',
      tl: 'Hakbang 4: Checklist',
      ru: 'Шаг 4: Чек-лист документов',
      ar: 'الخطوة 4: قائمة المستندات'
    },
    step4TabDesc: {
      ko: '필요 서류 체크리스트',
      en: 'Document checklist and notes',
      'zh-CN': '所需材料清单与须知',
      'zh-TW': '所需材料清單與須知',
      vi: 'Danh mục kiểm tra và lưu ý',
      id: 'Daftar periksa dan catatan',
      ja: '必要書類チェックと注意事項',
      tl: 'Checklist ng mga dokumento',
      ru: 'Список документов и примечания',
      ar: 'قائمة المستندات والملاحظات'
    },
    stepperStep1: {
      ko: '업무 선택',
      en: 'Procedure',
      'zh-CN': '业务选择',
      'zh-TW': '業務選擇',
      vi: 'Chọn thủ tục',
      id: 'Pilih Prosedur',
      ja: '手続き選択',
      tl: 'Pamamaraan',
      ru: 'Процедура',
      ar: 'الإجراء'
    },
    stepperStep2: {
      ko: '체류자격',
      en: 'Visa Status',
      'zh-CN': '滞留资格',
      'zh-TW': '滯留資格',
      vi: 'Tư cách cư trú',
      id: 'Status Visa',
      ja: '滞在資格',
      tl: 'Visa Status',
      ru: 'Визовый статус',
      ar: 'وضع الإقامة'
    },
    stepperStep3: {
      ko: '세부 상황',
      en: 'Scenario',
      'zh-CN': '细分情形',
      'zh-TW': '細分情形',
      vi: 'Trường hợp',
      id: 'Skenario',
      ja: '詳細状況',
      tl: 'Sitwasyon',
      ru: 'Сценарий',
      ar: 'تفاصيل الحالة'
    },
    stepperStep4: {
      ko: '서류 체크리스트',
      en: 'Checklist',
      'zh-CN': '材料清单',
      'zh-TW': '材料清單',
      vi: 'Checklist hồ sơ',
      id: 'Checklist Dokumen',
      ja: '書類リスト',
      tl: 'Checklist',
      ru: 'Чек-лист',
      ar: 'قائمة المستندات'
    },
    step4Title: {
      ko: '맞춤 서류 준비 체크리스트',
      en: 'Personalized Document Checklist',
      'zh-CN': '个性化材料准备清单',
      'zh-TW': '個人化材料準備清單',
      vi: 'Danh mục hồ sơ chuẩn bị phù hợp',
      id: 'Daftar Periksa Dokumen Khusus',
      ja: 'カスタム書類準備チェックリスト',
      tl: 'Naiangkop na Checklist ng mga Dokumento',
      ru: 'Индивидуальный чек-лист документов',
      ar: 'قائمة مخصصة للمستندات المطلوبة'
    },

    // Step 1: Tasks
    step1Title: {
      ko: '1단계: 어떤 출입국 업무를 준비하시나요?',
      en: 'Step 1: What immigration procedure are you preparing for?',
      'zh-CN': '第1步：您正在准备办理哪项出入境业务？',
      'zh-TW': '第1步：您正在準備辦理哪項出入境業務？',
      vi: 'Bước 1: Bạn đang chuẩn bị làm thủ tục xuất nhập cảnh nào?',
      id: 'Langkah 1: Prosedur imigrasi apa yang sedang Anda persiapkan?',
      ja: 'ステップ1: どの出入国手続きを準備していますか？',
      tl: 'Hakbang 1: Anong proseso sa imigrasyon ang iyong inihahanda?',
      ru: 'Шаг 1: Какую иммиграционную процедуру вы готовите?',
      ar: 'الخطوة 1: ما هو إجراء الهجرة الذي تستعد له؟'
    },
    step1Subtitle: {
      ko: '신청하고자 하는 행정 업무를 선택하세요. 세부 상황에 맞는 정확한 서류 목록으로 안내합니다.',
      en: 'Select the administrative procedure you need. We will guide you to the exact document checklist for your scenario.',
      'zh-CN': '请选择您要办理的业务类型。我们将为您提供符合具体情形的准确材料清单。',
      'zh-TW': '請選擇您要辦理的業務類型。我們將為您提供符合具體情形的準確材料清單。',
      vi: 'Vui lòng chọn thủ tục hành chính bạn cần. Chúng tôi sẽ hướng dẫn danh mục hồ sơ chính xác cho bạn.',
      id: 'Pilih prosedur administratif yang Anda butuhkan. Kami akan memandu Anda ke daftar dokumen yang tepat.',
      ja: '申請する手続きを選択してください。具体的な状況に応じた正確な書類リストをご案内します。',
      tl: 'Piliin ang pamamaraang kailangan mo. Gagabayan ka namin sa eksaktong checklist ng dokumento.',
      ru: 'Выберите нужную процедуру. Мы покажем точный список документов под вашу ситуацию.',
      ar: 'اختر الإجراء الإداري المطلوب. سنرشدك إلى قائمة المستندات الدقيقة الخاصة بوضعك.'
    },
    taskExtensionTitle: {
      ko: '체류기간 연장 (Extension)',
      en: 'Extension of Stay (Extension)',
      'zh-CN': '延长居留期限 (Extension)',
      'zh-TW': '延長居留期限 (Extension)',
      vi: 'Gia hạn thời gian cư trú (Extension)',
      id: 'Perpanjangan Masa Tinggal (Extension)',
      ja: '滞在期間の延長 (Extension)',
      tl: 'Pagpapalawig ng Pananatili (Extension)',
      ru: 'Продление срока пребывания (Extension)',
      ar: 'تمديد مدة الإقامة (Extension)'
    },
    taskExtensionDesc: {
      ko: '한국 체류 기간을 더 연장하고 싶어요',
      en: 'I want to stay in Korea longer under my current status',
      'zh-CN': '我想延长目前在韩国的滞留期限',
      'zh-TW': '我想延長目前在韓國的滯留期限',
      vi: 'Tôi muốn tiếp tục ở lại Hàn Quốc với visa hiện tại',
      id: 'Saya ingin memperpanjang masa tinggal saya di Korea',
      ja: '現在の資格のまま韓国での滞在期間を延ばしたい',
      tl: 'Nais kong manatili nang mas matagal sa Korea gamit ang aking visa',
      ru: 'Я хочу продлить срок пребывания в Корее по текущей визе',
      ar: 'أرغب في تمديد فترة إقامتي الحالية في كوريا'
    },
    taskChangeTitle: {
      ko: '체류자격 변경 (Change of Status)',
      en: 'Change of Status (Change)',
      'zh-CN': '变更滞留资格 (Change of Status)',
      'zh-TW': '變更滯留資格 (Change of Status)',
      vi: 'Thay đổi tư cách cư trú (Change of Status)',
      id: 'Perubahan Status Tinggal (Change of Status)',
      ja: '滞在資格の変更 (Change of Status)',
      tl: 'Pagpapalit ng Status (Change of Status)',
      ru: 'Смена статуса пребывания (Change of Status)',
      ar: 'تغيير وضع الإقامة (Change of Status)'
    },
    taskChangeDesc: {
      ko: '다른 비자나 새로운 활동으로 자격을 바꾸고 싶어요',
      en: 'I want to switch to a different visa or start a new permitted activity',
      'zh-CN': '我想变更为其他签证或从事新的在留活动',
      'zh-TW': '我想變更為其他簽證或從事新的在留活動',
      vi: 'Tôi muốn chuyển sang visa khác hoặc bắt đầu công việc/hoạt động mới',
      id: 'Saya ingin beralih ke visa lain atau memulai kegiatan baru',
      ja: '別のビザや新しい活動のために資格を切り替えたい',
      tl: 'Gusto kong lumipat sa ibang visa o magsimula ng bagong aktibidad',
      ru: 'Я хочу сменить категорию визы или начать новую деятельность',
      ar: 'أرغب في الانتقال إلى تأشيرة أخرى أو بدء نشاط مصرح به جديد'
    },
    taskRegistrationTitle: {
      ko: '외국인등록·거소신고 (Registration)',
      en: 'Foreigner Registration / Residence Report',
      'zh-CN': '外国人登录·居所申报 (Registration)',
      'zh-TW': '外國人登錄·居所申報 (Registration)',
      vi: 'Đăng ký cư trú / Báo cáo nơi ở (Registration)',
      id: 'Pendaftaran WNA / Lapor Tempat Tinggal',
      ja: '外国人登録・国内居所申告 (Registration)',
      tl: 'Pagpaparehistro ng Dayuhan / Pag-ulat ng Tirahan',
      ru: 'Регистрация иностранца / Декларация проживания',
      ar: 'تسجيل الأجانب / الإبلاغ عن محل الإقامة'
    },
    taskRegistrationDesc: {
      ko: '한국에 입국하여 외국인등록증을 발급받거나 거소신고를 해요',
      en: 'I entered Korea and need an Alien Registration Card (ARC) or residence report',
      'zh-CN': '入境韩国后，申领外国人登录证或办理居所申报',
      'zh-TW': '入境韓國後，申領外國人登錄證或辦理居所申報',
      vi: 'Tôi vừa nhập cảnh Hàn Quốc và cần làm thẻ cư trú (ARC) hoặc báo cáo cư sở',
      id: 'Saya telah masuk ke Korea dan perlu membuat Kartu Tinggal (ARC) atau lapor tinggal',
      ja: '入国後に外国人登録証（カード）の発行や居所申告を行う',
      tl: 'Pumasok ako sa Korea at kailangan ko ng Alien Registration Card (ARC) o ulat ng tirahan',
      ru: 'Я въехал в Корею и мне нужно оформить регистрационную карту (ARC) или заявить адрес',
      ar: 'دخلت إلى كوريا وأحتاج إلى إصدار بطاقة تسجيل الأجنبي (ARC) أو الإبلاغ عن الإقامة'
    },
    taskUnsure: {
      ko: '어떤 절차가 필요한지 잘 모르겠어요',
      en: 'I’m not sure what procedure I need',
      'zh-CN': '我不确定自己需要办理哪项手续',
      'zh-TW': '我不確定自己需要辦理哪項手續',
      vi: 'Tôi chưa rõ mình cần làm thủ tục gì',
      id: 'Saya tidak yakin prosedur apa yang saya perlukan',
      ja: 'どの手続きが必要かよく分かりません',
      tl: 'Hindi ako sigurado kung anong pamamaraan ang kailangan ko',
      ru: 'Я не уверен, какая процедура мне нужна',
      ar: 'لست متأكداً من الإجراء الذي أحتاجه'
    },

    // Step 2: Visa Status
    step2TitleCurrent: {
      ko: '현재 어떤 체류자격으로 머무르고 있나요?',
      en: 'What is your current visa status?',
      'zh-CN': '您目前持有哪种滞留资格？',
      'zh-TW': '您目前持有哪種滯留資格？',
      vi: 'Hiện tại bạn đang ở Hàn Quốc với visa nào?',
      id: 'Apa status visa Anda saat ini di Korea?',
      ja: '現在どの滞在資格で滞在していますか？',
      tl: 'Ano ang iyong kasalukuyang visa status?',
      ru: 'По какому визовому статусу вы сейчас находитесь?',
      ar: 'ما هو وضع إقامتك الحالي في كوريا؟'
    },
    step2TitleTarget: {
      ko: '어떤 체류자격으로 변경하고자 하나요?',
      en: 'Which visa status do you want to change to?',
      'zh-CN': '您希望变更为哪种滞留资格？',
      'zh-TW': '您希望變更為哪種滯留資格？',
      vi: 'Bạn muốn chuyển sang tư cách cư trú nào?',
      id: 'Status visa mana yang ingin Anda ubah?',
      ja: 'どの滞在資格に変更を希望しますか？',
      tl: 'Sa anong visa status mo gustong lumipat?',
      ru: 'На какой визовый статус вы хотите перейти?',
      ar: 'ما هو وضع الإقامة الذي ترغب في التغيير إليه؟'
    },
    step2TitleRegister: {
      ko: '등록 또는 거소신고할 체류자격을 선택하세요',
      en: 'Select the visa status to register or report',
      'zh-CN': '请选择要办理登录或居所申报的签证资格',
      'zh-TW': '請選擇要辦理登錄或居所申報的簽證資格',
      vi: 'Chọn tư cách cư trú cần đăng ký hoặc báo cáo',
      id: 'Pilih status visa untuk pendaftaran atau lapor tinggal',
      ja: '登録または居所申告を行う滞在資格を選択してください',
      tl: 'Piliin ang visa status na irerehistro o iuulat',
      ru: 'Выберите статус для регистрации или подачи декларации',
      ar: 'اختر وضع الإقامة المراد تسجيله أو الإبلاغ عنه'
    },
    step2SearchPlaceholder: {
      ko: '체류자격 검색 (예: D-2, E-7, 유학, 취업, 동포)',
      en: 'Search status code or name (e.g. D-2, E-7, student, worker)',
      'zh-CN': '搜索签证代码或名称 (如: D-2, E-7, 留学, 职业, 同胞)',
      'zh-TW': '搜尋簽證代碼或名稱 (如: D-2, E-7, 留學, 職業, 同胞)',
      vi: 'Tìm mã hoặc tên visa (VD: D-2, E-7, du học, việc làm)',
      id: 'Cari kode atau nama visa (mis: D-2, E-7, pelajar, kerja)',
      ja: '資格コードまたは名称で検索 (例: D-2, E-7, 留学, 就労)',
      tl: 'Maghanap ng visa code o pangalan (hal. D-2, E-7, mag-aaral)',
      ru: 'Поиск по коду или названию (напр. D-2, E-7, учеба, работа)',
      ar: 'ابحث برمز التأشيرة أو اسمها (مثل D-2, E-7, دراسة, عمل)'
    },
    candidateCountLabel: {
      ko: '{count}개 체류자격 선택 가능',
      en: '{count} visa statuses available',
      'zh-CN': '共有 {count} 种滞留资格可选',
      'zh-TW': '共有 {count} 種滯留資格可選',
      vi: 'Có {count} tư cách cư trú phù hợp',
      id: '{count} status visa tersedia',
      ja: '{count}件の滞在資格が選択可能',
      tl: '{count} mga visa status ang available',
      ru: 'Доступно статусов: {count}',
      ar: 'يتوفر {count} من أوضاع الإقامة'
    },
    candidateEmptyTitle: {
      ko: '일치하는 체류자격을 찾지 못했어요.',
      en: 'No matching visa status found.',
      'zh-CN': '未找到匹配的滞留资格。',
      'zh-TW': '未找到匹配的滯留資格。',
      vi: 'Không tìm thấy tư cách cư trú phù hợp.',
      id: 'Tidak ada status visa yang cocok ditemukan.',
      ja: '一致する滞在資格が見つかりませんでした。',
      tl: 'Walang nahanap na tugmang visa status.',
      ru: 'Подходящий статус не найден.',
      ar: 'لم يتم العثور على وضع إقامة مطابق.'
    },
    candidateEmptyDesc: {
      ko: '코드(예: D-2, E-7-1) 또는 명칭(예: 유학, 특정활동)으로 검색하거나 인기 체류자격을 눌러보세요.',
      en: 'Try searching by code (e.g. D-2, E-7-1), English name, or click one of the quick chips above.',
      'zh-CN': '请尝试输入代码 (如: D-2, E-7-1) 或名称搜索，也可以点击上方的常用快捷标签。',
      'zh-TW': '請嘗試輸入代碼 (如: D-2, E-7-1) 或名稱搜尋，也可以點擊上方的常用快捷標籤。',
      vi: 'Hãy thử tìm theo mã (VD: D-2, E-7-1) hoặc nhấp vào các phím tắt phổ biến phía trên.',
      id: 'Coba cari dengan kode (mis: D-2, E-7-1) atau klik salah satu pilihan cepat di atas.',
      ja: 'コード（例: D-2, E-7-1）や名称で検索するか、上記のクイックタグを押してみてください。',
      tl: 'Subukang maghanap gamit ang code (hal. D-2, E-7-1) o i-click ang mga mabilisang opsyon sa itaas.',
      ru: 'Попробуйте ввести код (напр. D-2, E-7-1) или выберите одну из популярных категорий выше.',
      ar: 'جرب البحث بالرمز (مثل D-2, E-7-1) أو انقر على أحد الخيارات السريعة أعلاه.'
    },

    // Step 3: Scenarios
    step3TitlePattern: {
      ko: '{code} ({name}) 세부 신청 상황 선택',
      en: 'Select Specific Scenario for {code} ({name})',
      'zh-CN': '选择 {code} ({name}) 具体申请情形',
      'zh-TW': '選擇 {code} ({name}) 具體申請情形',
      vi: 'Chọn tình huống cụ thể cho {code} ({name})',
      id: 'Pilih Skenario Spesifik untuk {code} ({name})',
      ja: '{code}（{name}）の詳細申請状況を選択',
      tl: 'Pumili ng Tiyak na Sitwasyon para sa {code} ({name})',
      ru: 'Выберите конкретный сценарий для {code} ({name})',
      ar: 'اختر الحالة المحددة لتأشيرة {code} ({name})'
    },
    step3Subtitle: {
      ko: '같은 체류자격이라도 세부 사유와 신청 조건에 따라 제출 서류가 달라집니다.',
      en: 'Even under the same status, required documents depend on your specific reason and conditions.',
      'zh-CN': '即使持有相同签证，具体事由和申请条件不同，所需提交的材料也有所差异。',
      'zh-TW': '即使持有相同簽證，具體事由和申請條件不同，所需提交的材料也有所差異。',
      vi: 'Cùng một loại visa nhưng tùy theo lý do và điều kiện nộp đơn mà hồ sơ sẽ khác nhau.',
      id: 'Meskipun visanya sama, dokumen yang diserahkan bergantung pada alasan dan kondisi Anda.',
      ja: '同じ滞在資格であっても、詳細な事由や申請条件によって提出書類が異なります。',
      tl: 'Kahit parehong status, ang mga dokumento ay nakadepende sa iyong dahilan at kondisyon.',
      ru: 'Даже при одинаковом статусе список документов зависит от конкретных обстоятельств.',
      ar: 'حتى ضمن نفس فئة التأشيرة، تعتمد المستندات المطلوبة على أسبابك وشروط تقديمك الخاصة.'
    },
    basicDocsPreviewLabel: {
      ko: '기본 서류: ',
      en: 'Basic documents: ',
      'zh-CN': '基本材料：',
      'zh-TW': '基本材料：',
      vi: 'Hồ sơ cơ bản: ',
      id: 'Dokumen dasar: ',
      ja: '基本書類: ',
      tl: 'Pangunahing dokumento: ',
      ru: 'Основные документы: ',
      ar: 'المستندات الأساسية: '
    },

    // Step 4: Checklist
    checklistTitle: {
      ko: '맞춤형 구비서류 체크리스트',
      en: 'Customized Document Checklist',
      'zh-CN': '定制化必备材料清单',
      'zh-TW': '定製化必備材料清單',
      vi: 'Danh mục kiểm tra hồ sơ được tùy chỉnh',
      id: 'Daftar Periksa Dokumen Khusus Anda',
      ja: 'オーダーメイド準備書類チェックリスト',
      tl: 'Naiangkop na Checklist ng mga Dokumento',
      ru: 'Персональный чек-лист документов',
      ar: 'قائمة تحقق المستندات المخصصة لك'
    },
    copyBtn: {
      ko: '체크리스트 복사',
      en: 'Copy Checklist',
      'zh-CN': '复制清单',
      'zh-TW': '複製清單',
      vi: 'Sao chép danh mục',
      id: 'Salin Daftar',
      ja: 'リストをコピー',
      tl: 'Kopyahin ang Checklist',
      ru: 'Скопировать чек-лист',
      ar: 'نسخ القائمة'
    },
    printBtn: {
      ko: '인쇄',
      en: 'Print View',
      'zh-CN': '打印视图',
      'zh-TW': '列印檢視',
      vi: 'In danh sách',
      id: 'Cetak Tampilan',
      ja: '印刷',
      tl: 'I-print',
      ru: 'Распечатать',
      ar: 'طباعة'
    },
    startOverBtn: {
      ko: '처음부터 다시 선택',
      en: 'Start Over',
      'zh-CN': '重新选择',
      'zh-TW': '重新選擇',
      vi: 'Bắt đầu lại',
      id: 'Mulai Ulang',
      ja: '最初から選び直す',
      tl: 'Magsimula Muli',
      ru: 'Начать заново',
      ar: 'البدء من جديد'
    },
    tabBasicDocs: {
      ko: '기본 제출 서류',
      en: 'Required Documents',
      'zh-CN': '基本必备材料',
      'zh-TW': '基本必備材料',
      vi: 'Hồ sơ bắt buộc',
      id: 'Dokumen Wajib',
      ja: '基本提出書類',
      tl: 'Mga Kailangang Dokumento',
      ru: 'Обязательные документы',
      ar: 'المستندات الإلزامية'
    },
    tabCondDocs: {
      ko: '조건부·대체 서류',
      en: 'Conditional & Alternatives',
      'zh-CN': '条件·替代材料',
      'zh-TW': '條件·替代材料',
      vi: 'Hồ sơ có điều kiện / thay thế',
      id: 'Dokumen Bersyarat & Alternatif',
      ja: '条件付き・代替書類',
      tl: 'May Kondisyon at Alternatibo',
      ru: 'Условные и альтернативные',
      ar: 'المستندات المشروطة والبديلة'
    },
    tabAppGuidance: {
      ko: '본인 출석 및 대리 신청',
      en: 'In-Person & Proxy Rules',
      'zh-CN': '本人出席与代办规定',
      'zh-TW': '本人出席與代辦規定',
      vi: 'Quy định có mặt trực tiếp / nộp thay',
      id: 'Ketentuan Kehadiran & Kuasa',
      ja: '本人出頭および代理申請',
      tl: 'Personal na Pagpunta at Pag-proxy',
      ru: 'Личное присутствие и подача по доверенности',
      ar: 'قواعد الحضور الشخصي والتوكيل'
    },
    tabOfficeDiff: {
      ko: '관서별 특이사항',
      en: 'Office Specifics',
      'zh-CN': '管辖机构特别要求',
      'zh-TW': '管轄機構特別要求',
      vi: 'Lưu ý riêng theo từng văn phòng',
      id: 'Ketentuan Khusus Kantor Imigrasi',
      ja: '管轄官署別の特記事項',
      tl: 'Mga Partikular na Opisina',
      ru: 'Особенности отделений',
      ar: 'متطلبات المكاتب الإقليمية'
    },
    progressPattern: {
      ko: '{checked} / {total}개 준비 완료 ({percent}%)',
      en: '{checked} of {total} documents ready ({percent}%)',
      'zh-CN': '已准备 {checked} / {total} 项 ({percent}%)',
      'zh-TW': '已準備 {checked} / {total} 項 ({percent}%)',
      vi: 'Đã chuẩn bị {checked} / {total} hồ sơ ({percent}%)',
      id: '{checked} dari {total} dokumen siap ({percent}%)',
      ja: '{checked} / {total}件 準備完了（{percent}%）',
      tl: '{checked} sa {total} dokumento ay handa na ({percent}%)',
      ru: 'Подготовлено {checked} из {total} документов ({percent}%)',
      ar: 'تم تجهيز {checked} من أصل {total} مستند ({percent}%)'
    },
    formHelperLinkText: {
      ko: 'VISABLE 서식 도우미에서 바로 작성하기 ↗',
      en: 'Fill out with VISABLE Form Helper ↗',
      'zh-CN': '在 VISABLE 表格助手中直接填写 ↗',
      'zh-TW': '在 VISABLE 表格助手中直接填寫 ↗',
      vi: 'Điền đơn trực tiếp trên VISABLE Form Helper ↗',
      id: 'Isi langsung di VISABLE Form Helper ↗',
      ja: 'VISABLE 書式作成ヘルパーで今すぐ作成 ↗',
      tl: 'Punan agad sa VISABLE Form Helper ↗',
      ru: 'Заполнить в Помощнике по анкетам VISABLE ↗',
      ar: 'تعبئة النموذج مباشرة عبر مساعد VISABLE ↗'
    },
    badgeAlternative: {
      ko: '택 1 제출 (대체 가능)',
      en: 'Submit 1 (Alternative)',
      'zh-CN': '选1项提交 (可替代)',
      'zh-TW': '選1項提交 (可替代)',
      vi: 'Nộp 1 trong các mục (Thay thế được)',
      id: 'Pilih 1 (Bisa Diganti)',
      ja: 'いずれか1つ提出（代替可）',
      tl: 'Pumili ng 1 (Maaaring ipalit)',
      ru: 'Выберите 1 (Альтернатива)',
      ar: 'تقديم خيار واحد (بديل)'
    },
    badgeConditional: {
      ko: '해당자 제출',
      en: 'If applicable',
      'zh-CN': '符合条件者提交',
      'zh-TW': '符合條件者提交',
      vi: 'Nộp nếu thuộc diện',
      id: 'Jika berlaku',
      ja: '該当者のみ提出',
      tl: 'Kung naaangkop',
      ru: 'При наличии оснований',
      ar: 'إذا كان ينطبق'
    },
    legalWarningNote: {
      ko: '공식 문서명은 법무부 출입국 매뉴얼 원문 및 법령과 일치하도록 한국어로 보존됩니다. 본 안내는 공식 고시 및 체류관리 지침을 바탕으로 제작된 참고용 도구이며, 개별 심사관 재량에 따라 추가 소명 자료가 요구될 수 있습니다.',
      en: 'Official Korean document names remain the authoritative standard to match official immigration manuals and statutes. This checklist is an informational preparation aid; immigration officers may request additional supporting evidence at their administrative discretion.',
      'zh-CN': '为与出入境官方手册和法规完全一致，正式文件名称保留韩文原称。本指南为参考工具，出入境审查官可能会根据个案裁量权要求补充说明材料。',
      'zh-TW': '為與出入境官方手冊和法規完全一致，正式文件名稱保留韓文原稱。本指南為參考工具，出入境審查官可能會根據個案裁量權要求補充說明材料。',
      vi: 'Tên văn bản chính thức được giữ nguyên bằng tiếng Hàn để đối chiếu chính xác với văn bản pháp luật và cẩm nang xuất nhập cảnh. Đây là công cụ hỗ trợ tham khảo; thẩm tra viên có quyền yêu cầu nộp thêm tài liệu giải trình bổ sung.',
      id: 'Nama dokumen resmi tetap dalam bahasa Korea agar sesuai dengan manual dan undang-undang resmi. Panduan ini adalah alat bantu referensi; petugas imigrasi dapat meminta bukti tambahan atas diskresi mereka.',
      ja: '公式文書名は出入国マニュアルおよび法令と一致させるため韓国語原文を併記・保持しています。本案内は参考用ツールであり、審査官の裁量により追加の疎明資料が求められる場合があります。',
      tl: 'Ang mga opisyal na pangalan ng dokumento ay pinanatili sa Korean upang tumugma sa opisyal na manwal. Ang checklist na ito ay gabay lamang; maaaring humingi ng karagdagang ebidensya ang opisyal ng imigrasyon.',
      ru: 'Официальные наименования документов приводятся на корейском языке для сверки с законодательством. Данный чек-лист носит информационный характер; инспектор может запросить дополнительные подтверждающие документы.',
      ar: 'يتم الاحتفاظ بأسماء المستندات الرسمية باللغة الكورية لمطابقتها مع الدليل واللوائح الرسمية. هذه القائمة هي أداة إرشادية فقط؛ ويحق لمسؤول الهجرة طلب مستندات توضيحية إضافية وفقاً لتقديره.'
    },

    // Meta & badges
    metaCasesLabel: {
      ko: '{count}개 세부 상황',
      en: '{count} Scenarios',
      'zh-CN': '{count}项细分情形',
      'zh-TW': '{count}項細分情形',
      vi: '{count} trường hợp cụ thể',
      id: '{count} skenario spesifik',
      ja: '{count}件の詳細状況',
      tl: '{count} mga sitwasyon',
      ru: '{count} конкретных сценариев',
      ar: '{count} حالة تفصيلية'
    },
    metaOfficesLabel: {
      ko: '{count}개 관할관서 대응',
      en: '{count} Local Offices',
      'zh-CN': '{count}个管辖机构',
      'zh-TW': '{count}個管轄機構',
      vi: '{count} văn phòng xuất nhập cảnh',
      id: '{count} kantor imigrasi',
      ja: '{count}件の管轄官署対応',
      tl: '{count} mga tanggapan',
      ru: '{count} региональных отделений',
      ar: '{count} مكتب إقليمي'
    },
    metaManualSource: {
      ko: '법무부 매뉴얼 편집본',
      en: 'MOJ Manual Source',
      'zh-CN': '法务部官方手册汇编',
      'zh-TW': '法務部官方手冊彙編',
      vi: 'Bản biên tập Cẩm nang Bộ Tư pháp',
      id: 'Kompilasi Manual Resmi Kementerian Kehakiman',
      ja: '法務省公式マニュアル編集版',
      tl: 'Opisyal na Manwal ng Ministry of Justice',
      ru: 'Редакция официального руководства Минюста',
      ar: 'مقتطفات من دليل وزارة العدل الرسمي'
    },

    // Step 2 & 3 back buttons & controls
    step2BackBtn: {
      ko: '← 이전: 업무 선택으로',
      en: '← Back: Select Task',
      'zh-CN': '← 返回：选择业务',
      'zh-TW': '← 返回：選擇業務',
      vi: '← Quay lại: Chọn thủ tục',
      id: '← Kembali: Pilih Prosedur',
      ja: '← 戻る: 手続き選択へ',
      tl: '← Bumalik: Pumili ng Pamamaraan',
      ru: '← Назад: Выбор процедуры',
      ar: '← العودة: اختيار الإجراء'
    },
    step3BackBtn: {
      ko: '← 이전: 체류자격 변경',
      en: '← Back: Change Visa Status',
      'zh-CN': '← 返回：更换滞留资格',
      'zh-TW': '← 返回：更換滯留資格',
      vi: '← Quay lại: Đổi tư cách cư trú',
      id: '← Kembali: Ganti Status Visa',
      ja: '← 戻る: 滞在資格を変更',
      tl: '← Bumalik: Palitan ang Visa Status',
      ru: '← Назад: Сменить статус',
      ar: '← العودة: تغيير وضع الإقامة'
    },
    step4BackBtn: {
      ko: '← 이전: 세부 상황 변경',
      en: '← Back: Change Scenario',
      'zh-CN': '← 返回：更换申请情形',
      'zh-TW': '← 返回：更換申請情形',
      vi: '← Quay lại: Đổi tình huống',
      id: '← Kembali: Ganti Skenario',
      ja: '← 戻る: 詳細状況を変更',
      tl: '← Bumalik: Palitan ang Sitwasyon',
      ru: '← Назад: Сменить сценарий',
      ar: '← العودة: تغيير الحالة'
    },
    subtabKnow: {
      ko: '체류자격을 알고 있어요',
      en: 'I know my visa status',
      'zh-CN': '我知道我的签证资格',
      'zh-TW': '我知道我的簽證資格',
      vi: 'Tôi đã biết tư cách cư trú',
      id: 'Saya tahu status visa saya',
      ja: '滞在資格を知っています',
      tl: 'Alam ko ang aking visa status',
      ru: 'Я знаю свой визовый статус',
      ar: 'أعرف وضع إقامتي'
    },
    subtabDontKnow: {
      ko: '체류자격을 확인하고 싶어요 (등록증 보는 법)',
      en: 'How to find visa status (ARC guide)',
      'zh-CN': '如何确认签证资格 (查看外国人登录证)',
      'zh-TW': '如何確認簽證資格 (查看外國人登錄證)',
      vi: 'Cách kiểm tra visa (xem thẻ cư trú ARC)',
      id: 'Cara cek status visa (panduan ARC)',
      ja: '滞在資格を確認したい（登録証の見方）',
      tl: 'Paano malalaman ang visa status (gabay sa ARC)',
      ru: 'Как узнать свой статус (по карте ARC)',
      ar: 'كيفية معرفة وضع الإقامة (دليل بطاقة ARC)'
    },
    popularChipsLabel: {
      ko: '자주 찾는 체류자격:',
      en: 'Popular Visas:',
      'zh-CN': '常用签证：',
      'zh-TW': '常用簽證：',
      vi: 'Visa phổ biến:',
      id: 'Visa Populer:',
      ja: 'よく検索される資格:',
      tl: 'Mga Madalas Hanaping Visa:',
      ru: 'Популярные статусы:',
      ar: 'تأشيرات شائعة:'
    },

    // ARC Guide
    arcGuideTitle: {
      ko: '외국인등록증(ARC)에서 체류자격 확인하기',
      en: 'How to find your visa status on your Alien Registration Card (ARC)',
      'zh-CN': '在外国人登录证(ARC)上确认滞留资格',
      'zh-TW': '在外國人登錄證(ARC)上確認滯留資格',
      vi: 'Cách kiểm tra tư cách cư trú trên thẻ ngoại kiều (ARC)',
      id: 'Cara menemukan status visa pada Kartu Registrasi Orang Asing (ARC)',
      ja: '外国人登録証（カード）で滞在資格を確認する方法',
      tl: 'Paano malalaman ang visa status sa iyong Alien Registration Card (ARC)',
      ru: 'Как найти визовый статус на регистрационной карте (ARC)',
      ar: 'كيف تجد وضع إقامتك على بطاقة تسجيل الأجنبي (ARC)'
    },
    arcGuideDesc: {
      ko: '가지고 계신 등록증의 앞면 가운데에 체류자격(SOJOURN STATUS)과 체류기간(PERIOD OF SOJOURN)이 표시되어 있습니다.',
      en: 'On the front center of your card, you will find your SOJOURN STATUS and PERIOD OF SOJOURN.',
      'zh-CN': '在您持有的登录证正面中央，标有滞留资格(SOJOURN STATUS)和滞留期限(PERIOD OF SOJOURN)。',
      'zh-TW': '在您持有的登錄證正面中央，標有滯留資格(SOJOURN STATUS)和滯留期限(PERIOD OF SOJOURN)。',
      vi: 'Ở mặt trước chính giữa thẻ cư trú có ghi TƯ CÁCH CƯ TRÚ (SOJOURN STATUS) và THỜI HẠN CƯ TRÚ (PERIOD OF SOJOURN).',
      id: 'Di bagian depan tengah kartu Anda, tertera SOJOURN STATUS dan PERIOD OF SOJOURN.',
      ja: 'お手元の登録証の表面中央に「滞在資格（SOJOURN STATUS）」と「滞在期間（PERIOD OF SOJOURN）」が記載されています。',
      tl: 'Sa harap at gitna ng iyong card, makikita ang SOJOURN STATUS at PERIOD OF SOJOURN.',
      ru: 'На лицевой стороне карты по центру указаны SOJOURN STATUS (статус) и PERIOD OF SOJOURN (срок).',
      ar: 'في منتصف الواجهة الأمامية لبطاقتك، ستجد SOJOURN STATUS (وضع الإقامة) و PERIOD OF SOJOURN (مدة الإقامة).'
    },
    arcStep1: {
      ko: '외국인등록증 앞면 중앙의 \'체류자격(SOJOURN STATUS)\' 란을 확인하세요.',
      en: 'Locate the \'SOJOURN STATUS\' field in the center of the card front.',
      'zh-CN': '查看登录证正面中央的“滞留资格(SOJOURN STATUS)”一栏。',
      'zh-TW': '查看登錄證正面中央的“滯留資格(SOJOURN STATUS)”一欄。',
      vi: 'Tìm mục \'SOJOURN STATUS\' ở chính giữa mặt trước thẻ.',
      id: 'Lihat kolom \'SOJOURN STATUS\' di bagian tengah depan kartu.',
      ja: '登録証表面中央の「滞在資格（SOJOURN STATUS）」欄を確認してください。',
      tl: 'Tingnan ang \'SOJOURN STATUS\' sa gitnang bahagi ng harap ng card.',
      ru: 'Найдите поле \'SOJOURN STATUS\' в центре лицевой стороны карты.',
      ar: 'ابحث عن خانة \'SOJOURN STATUS\' في منتصف واجهة البطاقة.'
    },
    arcStep2: {
      ko: '알파벳 대문자와 숫자 조합(예: E-7-1, D-2-2, F-4-11)이 적혀 있습니다.',
      en: 'You will see a combination of letters and numbers (e.g. E-7-1, D-2-2, F-4-11).',
      'zh-CN': '上面印有大写字母和数字组合的代码 (如: E-7-1, D-2-2, F-4-11)。',
      'zh-TW': '上面印有大寫字母和數字組合的代碼 (如: E-7-1, D-2-2, F-4-11)。',
      vi: 'Bạn sẽ thấy tổ hợp chữ cái in hoa và số (VD: E-7-1, D-2-2, F-4-11).',
      id: 'Anda akan melihat kombinasi huruf besar dan angka (mis: E-7-1, D-2-2, F-4-11).',
      ja: '英大文字と数字の組み合わせ（例: E-7-1, D-2-2, F-4-11）が記載されています。',
      tl: 'Makakakita ka ng kombinasyon ng mga letra at numero (hal. E-7-1, D-2-2, F-4-11).',
      ru: 'Там указана комбинация букв и цифр (напр. E-7-1, D-2-2, F-4-11).',
      ar: 'ستجد مجموعة من الحروف الكبيرة والأرقام (مثل E-7-1, D-2-2, F-4-11).'
    },
    arcStep3: {
      ko: '아래 예시 카드의 강조된 위치를 확인하신 후, \'체류자격을 알고 있어요\' 탭에서 해당 코드를 선택해 주세요.',
      en: 'Check the highlighted spot on the example card below, then select that code in the "I know my visa status" tab.',
      'zh-CN': '确认下方示例卡片中高亮的位置后，在“我知道我的签证资格”选项卡中选择该代码。',
      'zh-TW': '確認下方範例卡片中醒目提示的位置後，在“我知道我的簽證資格”標籤頁中選擇該代碼。',
      vi: 'Xem vị trí được đánh dấu trên thẻ mẫu bên dưới, sau đó chọn mã đó trong tab "Tôi đã biết tư cách cư trú".',
      id: 'Periksa posisi yang disorot pada contoh kartu di bawah, lalu pilih kode tersebut di tab "Saya tahu status visa saya".',
      ja: '以下の見本カードの強調箇所を確認し、「滞在資格を知っています」タブでそのコードを選択してください。',
      tl: 'Tingnan ang naka-highlight na bahagi sa halimbawang card sa ibaba, at piliin ang code sa "Alam ko ang aking visa status" tab.',
      ru: 'Посмотрите на выделенную область на образце карты ниже, затем выберите этот код на вкладке "Я знаю свой визовый статус".',
      ar: 'تحقق من الموضع المحدد على نموذج البطاقة أدناه، ثم اختر ذلك الرمز من تبويب "أعرف وضع إقامتي".'
    },
    arcExtRouteTitle: {
      ko: '등록증이 없거나 확인이 어려우신가요?',
      en: 'Don’t have your card yet or cannot find the status?',
      'zh-CN': '还没有登录证或难以确认？',
      'zh-TW': '還沒有登錄證或難以確認？',
      vi: 'Chưa có thẻ cư trú hoặc khó xác định?',
      id: 'Belum memiliki kartu atau kesulitan menemukan status?',
      ja: 'カードをお持ちでないか、確認が難しいですか？',
      tl: 'Wala ka pa bang card o nahihirapang kumpirmahin?',
      ru: 'У вас еще нет карты или трудно определить статус?',
      ar: 'ليس لديك بطاقة بعد أو يصعب التحقق؟'
    },
    arcHikoreaLink: {
      ko: '하이코리아 체류만료일 및 자격 조회 바로가기 ↗',
      en: 'Check expiry date and status on HiKorea ↗',
      'zh-CN': '前往 HiKorea 查询滞留到期日与资格 ↗',
      'zh-TW': '前往 HiKorea 查詢滯留到期日與資格 ↗',
      vi: 'Tra cứu hạn visa và tư cách trên HiKorea ↗',
      id: 'Cek masa berlaku dan status tinggal di HiKorea ↗',
      ja: 'HiKorea で滞在満了日および資格を照会 ↗',
      tl: 'Suriin ang petsa ng pag-expire at status sa HiKorea ↗',
      ru: 'Проверить срок и статус на портале HiKorea ↗',
      ar: 'الاستعلام عن تاريخ انتهاء الإقامة ووضعها عبر HiKorea ↗'
    },
    arcCall1345Note: {
      ko: '또는 법무부 출입국종합안내센터 국번 없이 1345 (20개 국어 무료 상담)',
      en: 'Or call Korea Immigration Contact Center at 1345 (toll-free, 20 languages)',
      'zh-CN': '或拨打出入境外国人综合咨询中心 1345 (免区号，20种语言免费咨询)',
      'zh-TW': '或撥打出入境外國人綜合諮詢中心 1345 (免區號，20種語言免費諮詢)',
      vi: 'Hoặc gọi Tổng đài Xuất nhập cảnh 1345 (miễn phí, hỗ trợ 20 thứ tiếng)',
      id: 'Atau hubungi Pusat Layanan Imigrasi Korea di 1345 (bebas pulsa, 20 bahasa)',
      ja: 'または法務省出入国在留総合インフォメーションセンター 1345（局番なし・20言語対応無料相談）',
      tl: 'O tumawag sa Immigration Contact Center sa 1345 (libre, 20 wika)',
      ru: 'Или позвоните в Справочный центр иммиграции по номеру 1345 (бесплатно, 20 языков)',
      ar: 'أو اتصل بمركز استعلامات الهجرة الكورية على الرقم 1345 (مجاناً، متاح بـ 20 لغة)'
    },
    arcSwitchBtn: {
      ko: '체류자격 코드를 확인했어요 → 목록에서 선택하기',
      en: 'I found my visa code → Select from list',
      'zh-CN': '已确认签证代码 → 前往列表选择',
      'zh-TW': '已確認簽證代碼 → 前往列表選擇',
      vi: 'Tôi đã tìm thấy mã visa → Chọn từ danh sách',
      id: 'Saya sudah tahu kode visa saya → Pilih dari daftar',
      ja: '資格コードを確認しました → リストから選択する',
      tl: 'Nahanap ko na ang aking visa code → Pumili sa listahan',
      ru: 'Я нашел код своего статуса → Выбрать из списка',
      ar: 'لقد تأكدت من رمز إقامتي → الانتقال للاختيار من القائمة'
    },

    // Step 4 Doc Groups
    groupBaselineTitle: {
      ko: '기본 제출서류',
      en: 'Mandatory Baseline Documents',
      'zh-CN': '基本必备提交材料',
      'zh-TW': '基本必備提交材料',
      vi: 'Hồ sơ cơ bản bắt buộc',
      id: 'Dokumen Dasar Wajib',
      ja: '基本提出書類',
      tl: 'Mga Pangunahing Dokumento',
      ru: 'Базовые обязательные документы',
      ar: 'المستندات الأساسية الإلزامية'
    },
    groupBaselineBadge: {
      ko: '반드시 준비',
      en: 'Mandatory',
      'zh-CN': '必须准备',
      'zh-TW': '必須準備',
      vi: 'Bắt buộc',
      id: 'Wajib',
      ja: '必須準備',
      tl: 'Kailangan',
      ru: 'Обязательно',
      ar: 'إلزامي'
    },
    groupBaselineDesc: {
      ko: '해당 신청 업무와 상황에서 공통적으로 제출하도록 명시된 서류입니다.',
      en: 'Documents explicitly mandated for this procedure and specific scenario.',
      'zh-CN': '该业务和申请情形下明确要求提交的通用必备材料。',
      'zh-TW': '該業務和申請情形下明確要求提交的通用必備材料。',
      vi: 'Các tài liệu bắt buộc chung cho thủ tục và trường hợp nộp đơn này.',
      id: 'Dokumen yang secara eksplisit diwajibkan untuk prosedur dan situasi ini.',
      ja: '該当の手続きおよび状況において共通して提出が明記されている書類です。',
      tl: 'Mga dokumentong tahasang kinakailangan para sa pamamaraan at sitwasyong ito.',
      ru: 'Документы, прямо предусмотренные для данной процедуры и сценария.',
      ar: 'المستندات المنصوص عليها صراحة لهذا الإجراء وتفاصيل هذه الحالة.'
    },
    groupConditionalTitle: {
      ko: '상황에 따라 필요한 서류 (해당자 제출)',
      en: 'Conditional Supporting Documents (If Applicable)',
      'zh-CN': '视具体情形提交材料 (符合条件者)',
      'zh-TW': '視具體情形提交材料 (符合條件者)',
      vi: 'Hồ sơ bổ sung tùy theo tình huống (Người thuộc diện)',
      id: 'Dokumen Tambahan Sesuai Kondisi (Jika Berlaku)',
      ja: '状況に応じて必要な書類（該当者提出）',
      tl: 'Mga Karagdagang Dokumento (Kung Naaangkop)',
      ru: 'Документы по обстоятельствам (при наличии оснований)',
      ar: 'مستندات مشروطة بحسب الحالة (إذا كان ينطبق)'
    },
    groupConditionalBadge: {
      ko: '조건부 확인',
      en: 'Conditional',
      'zh-CN': '按需确认',
      'zh-TW': '按需確認',
      vi: 'Có điều kiện',
      id: 'Bersyarat',
      ja: '条件付き確認',
      tl: 'Kondisyonal',
      ru: 'При условиях',
      ar: 'مشروط'
    },
    groupConditionalDesc: {
      ko: '개별 체류조건, 소득 증명, 가족 동반, 고위험국 결핵검진 등 특정 요건이 충족될 때 제출합니다.',
      en: 'Submitted when specific conditions apply, such as income verification, dependent family, or health/TB screening.',
      'zh-CN': '当下述特定条件满足时提交，例如收入证明、家属随行、指定国家结核筛查等。',
      'zh-TW': '當下述特定條件滿足時提交，例如收入證明、家屬隨行、指定國家結核篩查等。',
      vi: 'Nộp khi thỏa mãn các điều kiện cụ thể như chứng minh thu nhập, bảo lãnh gia đình, khám lao theo danh sách chỉ định.',
      id: 'Diserahkan jika memenuhi kondisi tertentu seperti bukti penghasilan, keluarga yang mendampingi, atau skrining TB.',
      ja: '個別滞在条件、所得証明、家族同伴、高リスク国結核検診など特定の要件に該当する場合に提出します。',
      tl: 'Isumite kapag may partikular na kondisyon tulad ng patunay ng kita, kasamang pamilya, o pagsusuri sa TB.',
      ru: 'Подаются при наличии особых условий: подтверждение дохода, сопровождение семьи, справка о туберкулезе и т.д.',
      ar: 'تُقدم عند انطباق شروط معينة، مثل إثبات الدخل، مرافقة العائلة، أو فحص السل للدول المحددة.'
    },
    groupApplicationTitle: {
      ko: '방문 및 대리 신청 안내',
      en: 'In-Person Appearance & Proxy Application',
      'zh-CN': '到场及委托代办须知',
      'zh-TW': '到場及委託代辦須知',
      vi: 'Quy định có mặt trực tiếp và ủy quyền nộp thay',
      id: 'Panduan Kehadiran Langsung & Pengajuan Kuasa',
      ja: '出頭および代理申請のご案内',
      tl: 'Gabay sa Personal na Pagpunta at Pag-proxy',
      ru: 'Порядок личной явки и подачи по доверенности',
      ar: 'إرشادات الحضور الشخصي والتقديم بالتوكيل'
    },
    groupApplicationBadge: {
      ko: '출석·대리 절차',
      en: 'Attendance Rules',
      'zh-CN': '到场·代办规定',
      'zh-TW': '到場·代辦規定',
      vi: 'Quy trình có mặt/đại diện',
      id: 'Aturan Kehadiran',
      ja: '出頭・代理規定',
      tl: 'Panuntunan sa Pagpunta',
      ru: 'Правила явки',
      ar: 'قواعد الحضور'
    },
    groupApplicationDesc: {
      ko: '서류 접수 대리와 본인 출석(지문·생체정보 등록, 인터뷰, 실물 등록증 수령)은 별개의 절차입니다.',
      en: 'Document submission by proxy and mandatory personal attendance (biometrics, fingerprinting, interview) are distinct legal requirements.',
      'zh-CN': '递交材料委托代办与本人必须亲自到场 (录入指纹与生物识别信息、面谈、领取实体证件) 是不同的法定程序。',
      'zh-TW': '遞交材料委託代辦與本人必須親自到場 (錄入指紋與生物識別資訊、面談、領取實體證件) 是不同的法定程序。',
      vi: 'Nộp hồ sơ qua người đại diện và việc phải đích thân có mặt (lấy dấu vân tay, chụp ảnh sinh trắc, phỏng vấn) là hai thủ tục riêng biệt.',
      id: 'Pengajuan dokumen melalui perwakilan dan kehadiran langsung wajib (biometrik, sidik jari, wawancara) adalah prosedur yang berbeda.',
      ja: '書類提出の代理と本人出頭（指紋等の生体認証登録、面接、実物カード受領）は別の手続きです。',
      tl: 'Ang pagsumite ng dokumento gamit ang kinatawan at ang personal na pagpunta (biometrics, panayam) ay magkahiwalay na proseso.',
      ru: 'Подача документов представителем и обязательное личное присутствие (сдача биометрии, дактилоскопия, собеседование) являются отдельными требованиями.',
      ar: 'تقديم المستندات بالتوكيل والحضور الشخصي الإلزامي (تسجيل البصمات، المقابلة، استلام البطاقة) هما إجراءان منفصلان قانوناً.'
    },
    groupOfficeTitle: {
      ko: '관할 출입국관서별 안내',
      en: 'Local Immigration Office Guidance',
      'zh-CN': '管辖出入境机构特别须知',
      'zh-TW': '管轄出入境機構特別須知',
      vi: 'Hướng dẫn riêng theo từng cơ quan quản hạt',
      id: 'Panduan Khusus Kantor Imigrasi Setempat',
      ja: '管轄出入国官署別のご案内',
      tl: 'Gabay ng Lokal na Tanggapan ng Imigrasyon',
      ru: 'Особенности региональных иммиграционных отделений',
      ar: 'إرشادات مكاتب الهجرة الإقليمية'
    },
    groupOfficeBadge: {
      ko: '지역별 안내',
      en: 'Local Practice',
      'zh-CN': '地区指引',
      'zh-TW': '地區指引',
      vi: 'Theo địa phương',
      id: 'Praktik Lokal',
      ja: '地域別案内',
      tl: 'Lokal na Gabay',
      ru: 'Региональная практика',
      ar: 'الممارسات المحلية'
    },
    groupCautionsTitle: {
      ko: '방문 전 확인사항 및 법적 한계',
      en: 'Pre-Visit Notices & Legal Limitations',
      'zh-CN': '到访前须知与法律说明',
      'zh-TW': '到訪前須知與法律說明',
      vi: 'Lưu ý trước khi đến và giới hạn pháp lý',
      id: 'Catatan Sebelum Berkunjung & Batasan Hukum',
      ja: '訪問前のご確認事項および法的留意事項',
      tl: 'Mga Paalala Bago Bumisita at Limitasyon sa Batas',
      ru: 'Информация перед визитом и правовые ограничения',
      ar: 'تنبيهات ما قبل الزيارة والحدود القانونية'
    },
    groupCautionsBadge: {
      ko: '유의사항',
      en: 'Legal Notice',
      'zh-CN': '注意事项',
      'zh-TW': '注意事項',
      vi: 'Lưu ý pháp lý',
      id: 'Peringatan',
      ja: '注意事項',
      tl: 'Mahalagang Paalala',
      ru: 'Важное уведомление',
      ar: 'إشعار قانوني'
    },
    cautionApprovalTitle: {
      ko: '체류허가 보장 여부',
      en: 'No Guarantee of Permit',
      'zh-CN': '居留许可非必然保证',
      'zh-TW': '居留許可非必然保證',
      vi: 'Không đảm bảo chắc chắn được cấp phép',
      id: 'Tidak Ada Jaminan Izin Diberikan',
      ja: '在留許可の保証について',
      tl: 'Walang Garantisadong Permiso',
      ru: 'Отсутствие гарантии получения разрешения',
      ar: 'عدم ضمان منح التصريح'
    },
    cautionApprovalDesc: {
      ko: '체류서류를 모두 준비했다고 해서 법적으로 체류기간 연장이나 자격변경 허가가 보장되는 것은 아닙니다. 심사 과정에서 관할 청 심사관의 판단에 따라 추가 소명자료 제출을 요구받을 수 있습니다.',
      en: 'Preparing all listed documents does not legally guarantee approval of extension or status change. The immigration examiner has discretionary authority to request supplementary evidence during examination.',
      'zh-CN': '备齐所有材料并不代表法律上必然准予延期或变更。审查过程中，出入境审查官有权根据个案裁量要求提交补充说明材料。',
      'zh-TW': '備齊所有材料並不代表法律上必然准予延期或變更。審查過程中，出入境審查官有權根據個案裁量要求提交補充說明材料。',
      vi: 'Chuẩn bị đầy đủ tất cả hồ sơ không đồng nghĩa với việc chắc chắn được phê duyệt. Thẩm tra viên có quyền yêu cầu nộp thêm tài liệu giải trình trong quá trình xét duyệt.',
      id: 'Menyiapkan seluruh dokumen tidak menjamin secara hukum bahwa perpanjangan atau perubahan status akan disetujui. Petugas imigrasi berwenang meminta bukti tambahan.',
      ja: 'すべての書類を揃えても、在留期間の延長や資格変更が法的に保証されるわけではありません。審査官の裁量により、追加疎明資料の提出を求められる場合があります。',
      tl: 'Ang paghahanda ng lahat ng dokumento ay hindi garantisadong maaprubahan. May awtoridad ang immigration officer na humingi ng karagdagang katibayan.',
      ru: 'Сбор всех указанных документов не гарантирует автоматического одобрения. Инспектор вправе запросить дополнительные разъясняющие материалы.',
      ar: 'تجهيز جميع المستندات لا يضمن قانوناً الحصول على تمديد الإقامة أو تغيير وضعها. يحق لمسؤول الهجرة طلب مستندات توضيحية إضافية أثناء الفحص.'
    },
    cautionVersionTitle: {
      ko: '자료 기준 시점 및 검증 상태',
      en: 'Source Date & Verification Status',
      'zh-CN': '资料基准时间与核查状态',
      'zh-TW': '資料基準時間與核查狀態',
      vi: 'Thời điểm căn cứ dữ liệu và trạng thái kiểm tra',
      id: 'Tanggal Rujukan Data & Status Verifikasi',
      ja: '資料の基準時点および検証状況',
      tl: 'Petsa ng Batayan at Katayuan ng Pagsusuri',
      ru: 'Дата актуальности данных и статус верификации',
      ar: 'تاريخ البيانات وحالة التدقيق'
    },
    cautionVersionDesc: {
      ko: '본 체크리스트는 2026년 9월 출입국 매뉴얼을 기반으로 정리된 이관 편집자료(COMPILED_NEEDS_REVIEW)입니다. 최신 지침 고시나 관할관서 공지가 우선하므로, 중요한 신청 전에는 하이코리아 공지사항을 반드시 대조하세요.',
      en: 'This checklist is compiled from the September 2026 official Immigration Manual (COMPILED_NEEDS_REVIEW). Recent ministry notices and official local announcements supersede this guide. Always cross-check with HiKorea announcements prior to major applications.',
      'zh-CN': '本清单基于2026年9月出入境官方业务手册整理汇编 (COMPILED_NEEDS_REVIEW)。最新的官方公告或机构通知具有优先效力，重大申请前请务必核对 HiKorea 最新公告。',
      'zh-TW': '本清單基於2026年9月出入境官方業務手冊整理彙編 (COMPILED_NEEDS_REVIEW)。最新的官方公告或機構通知具有優先效力，重大申請前請務必核對 HiKorea 最新公告。',
      vi: 'Danh mục này được biên soạn dựa trên Cẩm nang Xuất nhập cảnh tháng 9/2026 (COMPILED_NEEDS_REVIEW). Các thông báo mới nhất của cơ quan chức năng luôn được ưu tiên áp dụng, vui lòng đối chiếu trên HiKorea trước khi nộp đơn.',
      id: 'Daftar periksa ini disusun berdasarkan Manual Imigrasi September 2026 (COMPILED_NEEDS_REVIEW). Pengumuman kementerian terbaru tetap berlaku prioritas. Selalu periksa pengumuman di HiKorea sebelum mengajukan.',
      ja: '本チェックリストは2026年9月の出入国管理マニュアルに基づき整理された編集資料（COMPILED_NEEDS_REVIEW）です。最新の告示や管轄官署の公式告知が優先されるため、重要な申請の前に必ずHiKoreaのお知らせをご確認ください。',
      tl: 'Ang checklist na ito ay batay sa opisyal na Manwal ng Imigrasyon ng Setyembre 2026 (COMPILED_NEEDS_REVIEW). Ang pinakabagong opisyal na anunsyo ang laging mangingibabaw. Tiyaking mag-cross-check sa HiKorea bago magsumite.',
      ru: 'Данный перечень составлен на основе официального Руководства по иммиграции от сентября 2026 года (COMPILED_NEEDS_REVIEW). Официальные ведомственные объявления имеют приоритет. Обязательно сверяйтесь с HiKorea перед подачей.',
      ar: 'تم إعداد هذه القائمة بناءً على دليل الهجرة الرسمي لشهر سبتمبر 2026 (COMPILED_NEEDS_REVIEW). الإعلانات الرسمية الحديثة الصادرة عن الوزارة والمكاتب لها الأولوية دائماً. يرجى مراجعة إعلانات HiKorea قبل التقديم.'
    },
    hikoreaBtn: {
      ko: '하이코리아 바로가기 (온라인 방문예약·전자민원) ↗',
      en: 'Go to HiKorea (Visit Reservation & e-Applications) ↗',
      'zh-CN': '前往 HiKorea 官网 (在线预约·电子民愿) ↗',
      'zh-TW': '前往 HiKorea 官網 (線上預約·電子民願) ↗',
      vi: 'Đến trang HiKorea (Đặt lịch hẹn & nộp đơn trực tuyến) ↗',
      id: 'Buka HiKorea (Reservasi Kunjungan & Layanan Elektronik) ↗',
      ja: 'HiKorea 公式サイト（訪問予約・電子申請）↗',
      tl: 'Pumunta sa HiKorea (Online Reservation at e-Application) ↗',
      ru: 'Перейти на портал HiKorea (онлайн-запись и услуги) ↗',
      ar: 'الانتقال إلى موقع HiKorea (حجز المواعيد والمعاملات الإلكترونية) ↗'
    },
    sourceSnapshotBtn: {
      ko: '이관 원문표 대조 확인 ↗',
      en: 'Cross-check Source Baseline Table ↗',
      'zh-CN': '对照查看原始移交数据表 ↗',
      'zh-TW': '對照查看原始移交數據表 ↗',
      vi: 'Đối chiếu bảng dữ liệu gốc chuyển giao ↗',
      id: 'Cek silang tabel sumber asli ↗',
      ja: '移管原本対照テーブルを確認 ↗',
      tl: 'Suriin ang orihinal na talahanayan ng pinagmulan ↗',
      ru: 'Сверить с исходной таблицей данных ↗',
      ar: 'مقارنة جدول المصدر الأصلي ↗'
    },
    checklistPrintBtn: {
      ko: '체크리스트 인쇄 / PDF 저장',
      en: 'Print Checklist / Save as PDF',
      'zh-CN': '打印清单 / 另存为 PDF',
      'zh-TW': '列印清單 / 另存為 PDF',
      vi: 'In danh mục / Lưu PDF',
      id: 'Cetak Daftar / Simpan PDF',
      ja: 'チェックリスト印刷 / PDF保存',
      tl: 'I-print ang Checklist / I-save bilang PDF',
      ru: 'Печать чек-листа / Сохранить в PDF',
      ar: 'طباعة القائمة / حفظ كملف PDF'
    },
    checklistCopyLinkBtn: {
      ko: '결과 링크 복사',
      en: 'Copy Result Link',
      'zh-CN': '复制结果链接',
      'zh-TW': '複製結果連結',
      vi: 'Sao chép liên kết kết quả',
      id: 'Salin Tautan Hasil',
      ja: '結果リンクをコピー',
      tl: 'Kopyahin ang Link ng Resulta',
      ru: 'Копировать ссылку на результат',
      ar: 'نسخ رابط النتيجة'
    },
    checklistClearBtn: {
      ko: '체크 상태 초기화',
      en: 'Clear Checks',
      'zh-CN': '重置勾选状态',
      'zh-TW': '重設勾選狀態',
      vi: 'Đặt lại trạng thái chọn',
      id: 'Hapus Centang',
      ja: 'チェック状態をリセット',
      tl: 'I-clear ang mga Tsek',
      ru: 'Сбросить отметки',
      ar: 'إلغاء تحديد الاختيارات'
    },
    linkCopiedAlert: {
      ko: '맞춤 서류 체크리스트 링크가 복사되었습니다!',
      en: 'Customized document checklist link copied to clipboard!',
      'zh-CN': '个性化材料清单链接已复制到剪贴板！',
      'zh-TW': '個人化材料清單連結已複製到剪貼簿！',
      vi: 'Đã sao chép liên kết danh mục hồ sơ vào bộ nhớ tạm!',
      id: 'Tautan daftar periksa dokumen Anda telah disalin!',
      ja: 'カスタム書類チェックリストのリンクをコピーしました！',
      tl: 'Nakopya ang link ng iyong checklist sa clipboard!',
      ru: 'Ссылка на персональный чек-лист скопирована в буфер обмена!',
      ar: 'تم نسخ رابط قائمة المستندات المخصصة إلى الحافظة!'
    }
  };

  var cache = {};

  function normalizeLocale(raw) {
    if (!raw) return DEFAULT_LOCALE;
    var trimmed = String(raw).trim();
    if (LOCALE_CONFIG[trimmed]) return trimmed;
    var lower = trimmed.toLowerCase();
    if (LOCALE_ALIASES[lower]) return LOCALE_ALIASES[lower];
    var prefix = lower.split('-')[0].split('_')[0];
    if (LOCALE_ALIASES[prefix]) return LOCALE_ALIASES[prefix];
    if (LOCALE_CONFIG[prefix]) return prefix;
    return DEFAULT_LOCALE;
  }

  function getStoredLocale() {
    try {
      var s = global.localStorage ? global.localStorage.getItem(STORAGE_KEY) : null;
      return s ? normalizeLocale(s) : null;
    } catch (e) {
      return null;
    }
  }

  function getUrlLocale() {
    try {
      if (typeof window !== 'undefined' && window.location) {
        var param = new URLSearchParams(window.location.search).get('lang');
        return param ? normalizeLocale(param) : null;
      }
    } catch (e) {}
    return null;
  }

  function getBrowserLocale() {
    try {
      if (typeof navigator !== 'undefined' && navigator.language) {
        return normalizeLocale(navigator.language);
      }
    } catch (e) {}
    return null;
  }

  function resolveInitialLocale() {
    return getUrlLocale() || getStoredLocale() || DEFAULT_LOCALE;
  }

  var currentLocale = resolveInitialLocale();

  function isRTL(locale) {
    var loc = locale || currentLocale;
    return loc === 'ar';
  }

  function loadPack(locale) {
    var loc = normalizeLocale(locale);
    var fileLoc = loc === 'zh-TW' ? 'zh-CN' : loc;
    if (cache[fileLoc]) return Promise.resolve(cache[fileLoc]);

    var path = 'data/i18n/' + fileLoc + '.json';
    return fetch(path)
      .then(function (res) {
        if (!res.ok) throw new Error('Failed to load locale pack: ' + path);
        return res.json();
      })
      .then(function (data) {
        cache[fileLoc] = data;
        return data;
      })
      .catch(function (err) {
        console.warn('[VisableI18n] Failed to fetch pack for', fileLoc, err);
        return cache[DEFAULT_LOCALE] || {};
      });
  }

  function loadBaseline() {
    return loadPack(DEFAULT_LOCALE).then(function () {
      if (currentLocale !== DEFAULT_LOCALE) {
        return loadPack(currentLocale);
      }
    });
  }

  function interpolate(str, vars) {
    if (typeof str !== 'string') return str;
    if (!vars || typeof vars !== 'object') return str;
    return str.replace(/\{([a-zA-Z0-9_-]+)\}/g, function (match, key) {
      return vars[key] !== undefined && vars[key] !== null ? String(vars[key]) : match;
    });
  }

  function t(key, vars, fallback) {
    // 1. Check checklist dedicated strings
    if (CHECKLIST_STRINGS[key]) {
      var entry = CHECKLIST_STRINGS[key];
      var val = entry[currentLocale] || entry['en'] || entry['ko'] || fallback || key;
      return interpolate(val, vars);
    }

    // 2. Check loaded locale pack
    var activePack = cache[currentLocale === 'zh-TW' ? 'zh-CN' : currentLocale];
    var basePack = cache[DEFAULT_LOCALE];

    var text = (activePack && activePack[key]) || (basePack && basePack[key]) || fallback || key;
    return interpolate(text, vars);
  }

  function tArray(key) {
    var activePack = cache[currentLocale === 'zh-TW' ? 'zh-CN' : currentLocale];
    var basePack = cache[DEFAULT_LOCALE];
    var arr = (activePack && activePack[key]) || (basePack && basePack[key]);
    return Array.isArray(arr) ? arr : [];
  }

  function applyTraditionalMode(on) {
    if (typeof window !== 'undefined' && window.ParadisoZhT) {
      if (on) {
        if (!window.ParadisoZhT.isActive()) window.ParadisoZhT.start();
      } else {
        if (window.ParadisoZhT.isActive()) window.ParadisoZhT.stop();
      }
    }
  }

  function setLocale(newLocale, opts) {
    opts = opts || {};
    var normalized = normalizeLocale(newLocale);
    currentLocale = normalized;

    try {
      if (global.localStorage) {
        global.localStorage.setItem(STORAGE_KEY, normalized);
      }
    } catch (e) {}

    var cfg = LOCALE_CONFIG[normalized] || LOCALE_CONFIG[DEFAULT_LOCALE];
    if (typeof document !== 'undefined') {
      document.documentElement.lang = cfg.html;
      document.documentElement.dir = cfg.dir;
      document.body.setAttribute('data-locale', normalized);
      if (cfg.dir === 'rtl') {
        document.body.classList.add('rtl-layout');
      } else {
        document.body.classList.remove('rtl-layout');
      }
    }

    applyTraditionalMode(normalized === 'zh-TW');

    return loadPack(normalized).then(function () {
      // Dispatch events for all listeners
      if (typeof window !== 'undefined' && window.dispatchEvent) {
        var eventData = {
          detail: {
            locale: normalized,
            dir: cfg.dir,
            lang: cfg.html,
            isRTL: cfg.dir === 'rtl'
          }
        };
        window.dispatchEvent(new CustomEvent('visable-language-changed', eventData));
        window.dispatchEvent(new CustomEvent('paradiso-language-applied', eventData));
      }
      return normalized;
    });
  }

  function getAvailableLocales() {
    return Object.keys(LOCALE_CONFIG).map(function (code) {
      return Object.assign({ code: code }, LOCALE_CONFIG[code]);
    });
  }

  function getProcedureName(proc, locale) {
    var loc = locale || currentLocale;
    var map = {
      extension: CHECKLIST_STRINGS.taskExtensionTitle[loc] || CHECKLIST_STRINGS.taskExtensionTitle['ko'],
      change: CHECKLIST_STRINGS.taskChangeTitle[loc] || CHECKLIST_STRINGS.taskChangeTitle['ko'],
      registration: CHECKLIST_STRINGS.taskRegistrationTitle[loc] || CHECKLIST_STRINGS.taskRegistrationTitle['ko']
    };
    return map[proc] || proc;
  }

  // Self bootstrap
  if (typeof document !== 'undefined') {
    var cfg = LOCALE_CONFIG[currentLocale] || LOCALE_CONFIG[DEFAULT_LOCALE];
    document.documentElement.lang = cfg.html;
    document.documentElement.dir = cfg.dir;
    if (cfg.dir === 'rtl') document.body.classList.add('rtl-layout');
    applyTraditionalMode(currentLocale === 'zh-TW');
    loadBaseline();
  }

  var api = {
    getLocale: function () { return currentLocale; },
    setLocale: setLocale,
    normalizeLocale: normalizeLocale,
    isRTL: isRTL,
    t: t,
    tArray: tArray,
    getProcedureName: getProcedureName,
    getAvailableLocales: getAvailableLocales,
    loadPack: loadPack,
    loadBaseline: loadBaseline,
    CHECKLIST_STRINGS: CHECKLIST_STRINGS,
    LOCALE_CONFIG: LOCALE_CONFIG
  };

  global.VisableI18n = api;

})(typeof window !== 'undefined' ? window : this);
