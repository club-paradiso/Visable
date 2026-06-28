/* =========================================================================
 * visa-route-guide.js — Paradiso unified visa/status route-guidance layer
 * -------------------------------------------------------------------------
 * Turns the existing search → result-card experience into a guided journey
 * that works the SAME way for every 체류자격:
 *
 *   search → (subcode / 상황 선택) → (절차 선택) → result drawer opens with
 *   the chosen subcode + procedure already active, scrolled into view.
 *
 * Design notes
 *  - Self-contained IIFE, loaded with <script defer>. Mirrors the established
 *    module pattern (assets/js/f4-route-guide.js, short-stay-checker.js):
 *    own strings, own styles, exposes a window.* namespace, reuses the page's
 *    global helpers (openModal/closeModal/openVisaDrawer/renderResults/...).
 *  - It NEVER invents legal content. Availability + documents come straight
 *    from the page's own renderer (the live .procedure-tab buttons that
 *    getProcedure() produced) and from visa_data.json. Procedures with no
 *    source-backed data are shown honestly as "공식 출처 확인 필요", never faked.
 *  - Pure, DOM-free functions (buildGuidanceModel, procedureStatusForRecord,
 *    parseRouteState, serializeRouteState, validateRouteState, resolveCode,
 *    routeFinderNext) are exported for Node validation
 *    (scripts/check_visa_route_guide.mjs). All DOM access is guarded behind
 *    `typeof document !== 'undefined'`.
 *  - Strings are fully localized in-module (ko/en/zh-CN/ja/vi/tl/id/ru/fr/es/
 *    ar/de — all 12 UI locales), so this new surface does not touch the central
 *    i18n packs (no parity-check risk) and does not regress any language. ko is
 *    the universal fallback for any locale/key gap. Official procedure labels
 *    still come from the page's own txAt('procedureLabels', …) so they match
 *    everywhere. Arabic is rendered without bidi control characters.
 * ========================================================================= */
(function () {
  'use strict';

  /* ----------------------------------------------------------- procedures */
  // Approved procedure enum (task spec). URL + model use snake_case; the
  // in-page procedure tabs use the legacy camelCase keys. CAMEL_OF maps the
  // procedures we can actually land on a rendered tab for.
  var CAMEL_OF = {
    visa_issuance: 'visaIssuance',
    certificate_of_visa_issuance: 'certificateOfVisaIssuance',
    status_change: 'statusChange',
    extension: 'extension',
    status_grant: 'statusGrant',
    alien_registration: 'registration',
    work_permission: 'activitiesOutsideStatus',
    part_time_work: 'partTimeWork',
    workplace_change: 'workplaceChange',
    reentry: 'reentry'
  };
  var SNAKE_OF = {};
  Object.keys(CAMEL_OF).forEach(function (s) { SNAKE_OF[CAMEL_OF[s]] = s; });

  // Full approved enum (includes procedures that may not map to a core tab but
  // are meaningful and handled specially, e.g. visit_reservation → HiKorea).
  var APPROVED_PROCEDURES = [
    'visa_issuance', 'certificate_of_visa_issuance', 'status_change', 'extension',
    'status_grant', 'alien_registration', 'work_permission', 'part_time_work',
    'workplace_change', 'reentry', 'residence_report', 'visit_reservation'
  ];

  // Index into the page's procedureLabels i18n array (mirrors index.html
  // PROCEDURE_LABEL_INDEX) so official labels stay identical to the tabs.
  var PROC_LABEL_INDEX = {
    visaIssuance: 0, certificateOfVisaIssuance: 1, statusChange: 2, extension: 3,
    statusGrant: 4, registration: 5, activitiesOutsideStatus: 6, workplaceChange: 7, reentry: 8
  };
  // Order procedures are offered in the selector (camelCase).
  var PROCEDURE_ORDER = [
    'visaIssuance', 'certificateOfVisaIssuance', 'statusChange', 'extension',
    'statusGrant', 'registration', 'activitiesOutsideStatus', 'workplaceChange', 'reentry'
  ];
  // Legacy top-level fields that make a procedure "available" even without a
  // procedures[key] entry — faithfully mirrors index.html PROCEDURE_CONFIG.
  var LEGACY_FIELDS = {
    visaIssuance: { text: 'newReq', docs: ['initialReqDocs', 'newReqDocs', 'reqDocs', 'documents', 'requiredDocs', 'required_documents'] },
    certificateOfVisaIssuance: { docs: ['cviReqDocs'] },
    statusChange: { text: 'changeReq', docs: ['changeReqDocs', 'chgReqDocs'] },
    extension: { text: 'extReq', docs: ['extensionReqDocs', 'extReqDocs'] },
    statusGrant: { docs: ['statusGrantReqDocs'] },
    registration: { docs: ['registrationReqDocs'] },
    activitiesOutsideStatus: { docs: ['activitiesOutsideStatusReqDocs'] },
    workplaceChange: { docs: ['workplaceChangeReqDocs'] },
    reentry: { docs: ['reentryReqDocs'] }
  };
  // 사증발급 is suppressed for these (영주 F-5). Mirrors
  // VISA_ISSUANCE_NOT_APPLICABLE_CODES; the page can override via the global
  // isVisaIssuanceNotApplicable() when present (richer, data-driven).
  var VISA_ISSUANCE_NOT_APPLICABLE_CODES = ['F-5'];

  var DEFAULT_PROC_LABELS = {
    visaIssuance: '사증발급', certificateOfVisaIssuance: '사증발급인정서', statusChange: '체류자격 변경',
    extension: '체류기간 연장', statusGrant: '체류자격 부여', registration: '외국인등록',
    activitiesOutsideStatus: '자격외활동', workplaceChange: '근무처 변경·추가', reentry: '재입국'
  };

  /* --------------------------------------------------- localized UI strings */
  /* All 12 UI locales (ko/en/zh-CN/ja/vi/tl/id/ru/fr/es/ar/de). ko is the
   * universal fallback. Verbatim across every locale: visa/status codes,
   * {placeholders}, HTML/entities, URLs, the 1345 hotline, HiKorea, and emoji.
   * Disclaimers/cautions/"verify with the official source" notices are fully
   * translated, never weakened. Arabic carries no bidi control characters. */
  var STR = {
    flowAria: { ko: '체류자격 절차 안내', en: 'Status procedure guide', 'zh-CN': '居留资格手续向导', ja: '滞在資格 手続きガイド', vi: 'Hướng dẫn thủ tục tư cách cư trú', tl: 'Gabay sa proseso ng status of stay', id: 'Panduan prosedur status tinggal', ru: 'Гид по процедурам статуса пребывания', fr: 'Guide des procédures de statut de séjour', es: 'Guía de trámites de estatus de residencia', ar: 'دليل إجراءات وضع الإقامة', de: 'Leitfaden zu Aufenthaltsverfahren' },
    close: { ko: '닫기', en: 'Close', 'zh-CN': '关闭', ja: '閉じる', vi: 'Đóng', tl: 'Isara', id: 'Tutup', ru: 'Закрыть', fr: 'Fermer', es: 'Cerrar', ar: 'إغلاق', de: 'Schließen' },
    back: { ko: '← 이전', en: '← Back', 'zh-CN': '← 上一步', ja: '← 戻る', vi: '← Quay lại', tl: '← Bumalik', id: '← Kembali', ru: '← Назад', fr: '← Retour', es: '← Atrás', ar: '← رجوع', de: '← Zurück' },
    seeResult: { ko: '결과 보기', en: 'See result', 'zh-CN': '查看结果', ja: '結果を見る', vi: 'Xem kết quả', tl: 'Tingnan ang resulta', id: 'Lihat hasil', ru: 'Посмотреть результат', fr: 'Voir le résultat', es: 'Ver el resultado', ar: 'عرض النتيجة', de: 'Ergebnis ansehen' },
    unsure: { ko: '잘 모르겠어요', en: "I'm not sure", 'zh-CN': '我不太确定', ja: 'よくわかりません', vi: 'Tôi không chắc', tl: 'Hindi ako sigurado', id: 'Saya tidak yakin', ru: 'Я не уверен(а)', fr: 'Je ne suis pas sûr(e)', es: 'No estoy seguro/a', ar: 'لست متأكدًا', de: 'Ich bin nicht sicher' },
    unsureHint: { ko: '몇 가지 질문으로 찾아보기', en: 'Find it with a few questions', 'zh-CN': '通过几个问题来查找', ja: 'いくつかの質問で探す', vi: 'Tìm bằng vài câu hỏi', tl: 'Hanapin sa ilang tanong', id: 'Temukan dengan beberapa pertanyaan', ru: 'Найти с помощью нескольких вопросов', fr: 'Trouver à l’aide de quelques questions', es: 'Encontrarlo con unas preguntas', ar: 'ابحث عنه ببضعة أسئلة', de: 'Mit einigen Fragen finden' },
    yes: { ko: '예', en: 'Yes', 'zh-CN': '是', ja: 'はい', vi: 'Có', tl: 'Oo', id: 'Ya', ru: 'Да', fr: 'Oui', es: 'Sí', ar: 'نعم', de: 'Ja' },
    no: { ko: '아니요', en: 'No', 'zh-CN': '否', ja: 'いいえ', vi: 'Không', tl: 'Hindi', id: 'Tidak', ru: 'Нет', fr: 'Non', es: 'No', ar: 'لا', de: 'Nein' },

    subcodeTitle: { ko: '{code} {name} 중 어떤 상황에 가까우신가요?', en: 'Which {code} {name} situation fits you?', 'zh-CN': '在 {code} {name} 中，哪种情况更接近您？', ja: '{code} {name} のうち、どの状況に近いですか？', vi: 'Trong {code} {name}, tình huống nào gần với bạn?', tl: 'Aling sitwasyon ng {code} {name} ang bagay sa iyo?', id: 'Di antara {code} {name}, situasi mana yang sesuai dengan Anda?', ru: 'Какая ситуация из {code} {name} вам ближе?', fr: 'Quelle situation parmi {code} {name} vous correspond ?', es: '¿Qué situación de {code} {name} se ajusta a usted?', ar: 'أي حالة من {code} {name} تنطبق عليك؟', de: 'Welche {code} {name} Situation trifft auf Sie zu?' },
    subcodeIntro: { ko: '해당하는 세부 자격(세부코드)을 고르면 그에 맞는 절차 안내로 이동합니다.', en: 'Pick the sub-status that fits you to jump to the matching procedure guidance.', 'zh-CN': '选择适合您的细分资格（子代码），即可进入对应的手续指引。', ja: '当てはまる詳細資格（詳細コード）を選ぶと、それに合った手続きガイドへ移動します。', vi: 'Chọn tư cách chi tiết (mã chi tiết) phù hợp để chuyển đến hướng dẫn thủ tục tương ứng.', tl: 'Piliin ang angkop na sub-status (subcode) upang lumipat sa katugmang gabay sa proseso.', id: 'Pilih status rinci (kode rinci) yang sesuai untuk menuju panduan prosedur yang cocok.', ru: 'Выберите подходящий подстатус (подкод), чтобы перейти к соответствующей инструкции по процедуре.', fr: 'Choisissez le sous-statut (sous-code) qui vous correspond pour accéder à la procédure adaptée.', es: 'Elija el subestatus (subcódigo) que le corresponda para ir a la guía de trámites adecuada.', ar: 'اختر الوضع التفصيلي (الرمز التفصيلي) المناسب للانتقال إلى دليل الإجراء المطابق.', de: 'Wählen Sie den passenden Unterstatus (Untercode), um zur entsprechenden Verfahrensanleitung zu gelangen.' },
    procTitle: { ko: '{label} · 어떤 절차가 필요하세요?', en: '{label} · Which procedure do you need?', 'zh-CN': '{label} · 您需要办理哪项手续？', ja: '{label} · どの手続きが必要ですか？', vi: '{label} · Bạn cần thủ tục nào?', tl: '{label} · Aling proseso ang kailangan mo?', id: '{label} · Prosedur mana yang Anda perlukan?', ru: '{label} · Какая процедура вам нужна?', fr: '{label} · De quelle procédure avez-vous besoin ?', es: '{label} · ¿Qué trámite necesita?', ar: '{label} · أي إجراء تحتاج؟', de: '{label} · Welches Verfahren benötigen Sie?' },
    procIntro: { ko: '진행하려는 절차를 선택하면 해당 안내가 바로 열립니다.', en: 'Choose a procedure to open its guidance directly.', 'zh-CN': '选择要办理的手续，将直接打开相应指引。', ja: '進めたい手続きを選ぶと、その案内がすぐに開きます。', vi: 'Chọn thủ tục bạn muốn tiến hành để mở hướng dẫn tương ứng ngay.', tl: 'Piliin ang prosesong nais mong gawin upang agad bumukas ang gabay nito.', id: 'Pilih prosedur yang ingin Anda jalankan untuk langsung membuka panduannya.', ru: 'Выберите нужную процедуру, и её инструкция откроется сразу.', fr: 'Choisissez la procédure souhaitée pour ouvrir directement son guide.', es: 'Elija el trámite que desea realizar para abrir su guía directamente.', ar: 'اختر الإجراء الذي تريد القيام به ليُفتح دليله مباشرة.', de: 'Wählen Sie das gewünschte Verfahren, um dessen Anleitung direkt zu öffnen.' },
    allProcedures: { ko: '먼저 전체 안내 보기', en: 'See the full guide first', 'zh-CN': '先查看完整指引', ja: 'まず全体の案内を見る', vi: 'Xem hướng dẫn đầy đủ trước', tl: 'Tingnan muna ang buong gabay', id: 'Lihat dulu panduan lengkap', ru: 'Сначала посмотреть полное руководство', fr: 'Voir d’abord le guide complet', es: 'Ver primero la guía completa', ar: 'اطّلع أولًا على الدليل الكامل', de: 'Zuerst den vollständigen Leitfaden ansehen' },

    badgeSubcode: { ko: '세부코드', en: 'Sub-code', 'zh-CN': '子代码', ja: '詳細コード', vi: 'Mã chi tiết', tl: 'Subcode', id: 'Kode rinci', ru: 'Подкод', fr: 'Sous-code', es: 'Subcódigo', ar: 'رمز تفصيلي', de: 'Untercode' },
    badgeSituation: { ko: '상황별 선택', en: 'By situation', 'zh-CN': '按情况选择', ja: '状況別に選択', vi: 'Theo tình huống', tl: 'Ayon sa sitwasyon', id: 'Berdasarkan situasi', ru: 'По ситуации', fr: 'Par situation', es: 'Por situación', ar: 'حسب الحالة', de: 'Nach Situation' },
    badgeSourceLimited: { ko: '공식 출처 보강 필요', en: 'Source coverage limited', 'zh-CN': '官方依据有限', ja: '公式の根拠が不十分', vi: 'Nguồn chính thức còn hạn chế', tl: 'Limitado ang opisyal na sanggunian', id: 'Sumber resmi terbatas', ru: 'Официальных источников недостаточно', fr: 'Sources officielles limitées', es: 'Cobertura de fuentes limitada', ar: 'المصادر الرسمية محدودة', de: 'Amtliche Quellenlage begrenzt' },
    badgeNeedsReview: { ko: '수동 검토 필요', en: 'Needs manual review', 'zh-CN': '需人工核对', ja: '手動での確認が必要', vi: 'Cần kiểm tra thủ công', tl: 'Kailangan ng manu-manong pagsusuri', id: 'Perlu pemeriksaan manual', ru: 'Требуется ручная проверка', fr: 'Vérification manuelle requise', es: 'Requiere revisión manual', ar: 'يتطلب مراجعة يدوية', de: 'Manuelle Prüfung erforderlich' },

    statusAvailable: { ko: '안내 있음', en: 'Guidance available', 'zh-CN': '有指引', ja: '案内あり', vi: 'Có hướng dẫn', tl: 'May gabay', id: 'Ada panduan', ru: 'Инструкция доступна', fr: 'Guide disponible', es: 'Guía disponible', ar: 'يتوفّر دليل', de: 'Anleitung verfügbar' },
    statusConditional: { ko: '조건부', en: 'Conditional', 'zh-CN': '有条件', ja: '条件付き', vi: 'Có điều kiện', tl: 'May kondisyon', id: 'Bersyarat', ru: 'С условиями', fr: 'Sous conditions', es: 'Condicional', ar: 'مشروط', de: 'Bedingt' },
    statusNotApplicable: { ko: '해당 없음', en: 'Not applicable', 'zh-CN': '不适用', ja: '該当なし', vi: 'Không áp dụng', tl: 'Hindi naaangkop', id: 'Tidak berlaku', ru: 'Не применимо', fr: 'Non applicable', es: 'No aplicable', ar: 'لا ينطبق', de: 'Nicht anwendbar' },
    statusSourceLimited: { ko: '공식 출처 확인 필요', en: 'Verify with official source', 'zh-CN': '需核对官方依据', ja: '公式の根拠を確認', vi: 'Cần xác minh nguồn chính thức', tl: 'Tiyakin sa opisyal na sanggunian', id: 'Perlu verifikasi sumber resmi', ru: 'Уточните в официальном источнике', fr: 'À vérifier auprès d’une source officielle', es: 'Verificar en la fuente oficial', ar: 'تحقّق من المصدر الرسمي', de: 'Mit amtlicher Quelle prüfen' },

    // user-facing procedure labels (generic, navigational — not legal content)
    procUser_visaIssuance: { ko: '해외에서 처음 비자 받기', en: 'Get the visa from abroad', 'zh-CN': '在海外首次申请签证', ja: '海外で初めてビザを取得する', vi: 'Nhận visa lần đầu từ nước ngoài', tl: 'Kunin ang visa mula sa ibang bansa', id: 'Memperoleh visa pertama dari luar negeri', ru: 'Получить визу за рубежом впервые', fr: 'Obtenir le visa depuis l’étranger', es: 'Obtener el visado desde el extranjero', ar: 'الحصول على التأشيرة لأول مرة من الخارج', de: 'Das Visum aus dem Ausland erhalten' },
    procUser_certificateOfVisaIssuance: { ko: '초청자가 사증발급인정서 받기', en: 'Sponsor gets a certificate for visa issuance', 'zh-CN': '邀请方申请签证发放认定书', ja: '招へい者が査証発給認定書を取得する', vi: 'Người mời nhận giấy xác nhận cấp visa', tl: 'Kukunin ng nag-imbita ang sertipiko ng kumpirmasyon sa pag-isyu ng visa', id: 'Pengundang memperoleh surat keterangan konfirmasi penerbitan visa', ru: 'Приглашающий получает сертификат подтверждения выдачи визы', fr: 'L’invitant obtient le certificat de confirmation de délivrance de visa', es: 'El invitante obtiene el certificado de confirmación de emisión de visado', ar: 'يحصل الجهة الداعية على شهادة تأكيد إصدار التأشيرة', de: 'Einladende Person erhält die Bescheinigung über die Bestätigung der Visumerteilung' },
    procUser_statusChange: { ko: '한국 안에서 이 자격으로 바꾸기', en: 'Change to this status inside Korea', 'zh-CN': '在韩国境内变更为该资格', ja: '韓国国内でこの資格に変更する', vi: 'Chuyển sang tư cách này trong Hàn Quốc', tl: 'Magpalit sa status na ito sa loob ng Korea', id: 'Mengubah ke status ini di dalam Korea', ru: 'Сменить на этот статус внутри Кореи', fr: 'Passer à ce statut depuis la Corée', es: 'Cambiar a este estatus dentro de Corea', ar: 'التغيير إلى هذا الوضع داخل كوريا', de: 'Innerhalb Koreas zu diesem Status wechseln' },
    procUser_extension: { ko: '이미 받은 자격의 기간 늘리기', en: 'Extend the period of this status', 'zh-CN': '延长已持有资格的期限', ja: 'すでに持っている資格の期間を延ばす', vi: 'Gia hạn thời gian của tư cách đã có', tl: 'Palawigin ang panahon ng status na hawak mo', id: 'Memperpanjang masa status yang sudah dimiliki', ru: 'Продлить срок имеющегося статуса', fr: 'Prolonger la durée de ce statut', es: 'Prorrogar el periodo de este estatus', ar: 'تمديد مدة الوضع الذي تملكه', de: 'Die Dauer dieses Status verlängern' },
    procUser_statusGrant: { ko: '국내 출생 등으로 체류자격 부여받기', en: 'Be granted status (e.g. birth in Korea)', 'zh-CN': '获得居留资格（如在韩出生）', ja: '国内出生などで滞在資格を付与してもらう', vi: 'Được cấp tư cách cư trú (ví dụ sinh ra tại Hàn Quốc)', tl: 'Bigyan ng status of stay (hal. ipinanganak sa Korea)', id: 'Memperoleh status tinggal (mis. lahir di Korea)', ru: 'Получить статус пребывания (например, при рождении в Корее)', fr: 'Se voir octroyer un statut (p. ex. naissance en Corée)', es: 'Recibir la concesión del estatus (p. ej. nacimiento en Corea)', ar: 'الحصول على منح وضع الإقامة (مثل الولادة في كوريا)', de: 'Aufenthaltsstatus erhalten (z. B. Geburt in Korea)' },
    procUser_registration: { ko: '입국 후 외국인등록 하기', en: 'Register as a foreign resident after entry', 'zh-CN': '入境后办理外国人登录', ja: '入国後に外国人登録をする', vi: 'Đăng ký người nước ngoài sau khi nhập cảnh', tl: 'Magparehistro bilang dayuhan pagkatapos pumasok', id: 'Melakukan registrasi orang asing setelah masuk', ru: 'Зарегистрироваться как иностранец после въезда', fr: 'S’enregistrer comme étranger après l’entrée', es: 'Registrarse como extranjero tras la entrada', ar: 'تسجيل الأجانب بعد الدخول', de: 'Nach der Einreise als Ausländer registrieren' },
    procUser_activitiesOutsideStatus: { ko: '원래 자격 외 다른 활동 허가받기', en: 'Get permission for activities outside your status', 'zh-CN': '申请从事资格外活动的许可', ja: '本来の資格以外の活動の許可を受ける', vi: 'Xin phép hoạt động ngoài tư cách', tl: 'Kumuha ng pahintulot para sa aktibidad na labas sa status', id: 'Memperoleh izin untuk kegiatan di luar status', ru: 'Получить разрешение на деятельность вне статуса', fr: 'Obtenir l’autorisation d’activités hors statut', es: 'Obtener permiso para actividades fuera del estatus', ar: 'الحصول على إذن لنشاط خارج الوضع', de: 'Erlaubnis für Tätigkeiten außerhalb des Status erhalten' },
    procUser_workplaceChange: { ko: '근무처(직장) 변경·추가 신고하기', en: 'Report a change/addition of workplace', 'zh-CN': '申报变更/增加工作单位', ja: '勤務先の変更・追加を届け出る', vi: 'Khai báo thay đổi · bổ sung nơi làm việc', tl: 'Iulat ang pagpapalit·pagdaragdag ng pinagtatrabahuhan', id: 'Melaporkan perubahan·penambahan tempat kerja', ru: 'Уведомить о смене или добавлении места работы', fr: 'Déclarer un changement ou ajout de lieu de travail', es: 'Notificar un cambio o adición de lugar de trabajo', ar: 'الإبلاغ عن تغيير جهة العمل أو إضافتها', de: 'Arbeitsplatzwechsel oder -ergänzung melden' },
    procUser_reentry: { ko: '출국 후 다시 입국하기', en: 'Re-enter after leaving Korea', 'zh-CN': '出境后再次入境', ja: '出国後に再び入国する', vi: 'Tái nhập cảnh sau khi xuất cảnh', tl: 'Muling pumasok matapos umalis ng Korea', id: 'Masuk kembali setelah keluar dari Korea', ru: 'Повторно въехать после выезда из Кореи', fr: 'Réentrer après avoir quitté la Corée', es: 'Reentrar tras salir de Corea', ar: 'إعادة الدخول بعد مغادرة كوريا', de: 'Nach der Ausreise wieder einreisen' },
    procUser_visitReservation: { ko: '방문예약·관할 관서 확인하기', en: 'Book a visit / check the competent office', 'zh-CN': '预约访问 / 确认管辖机关', ja: '訪問予約・管轄官署を確認する', vi: 'Đặt lịch hẹn / kiểm tra cơ quan quản lý', tl: 'Mag-book ng pagbisita / tingnan ang may hurisdiksyong tanggapan', id: 'Membuat reservasi kunjungan / memeriksa instansi berwenang', ru: 'Записаться на приём / проверить компетентный орган', fr: 'Prendre rendez-vous / vérifier le bureau compétent', es: 'Reservar una visita / consultar la oficina competente', ar: 'حجز موعد زيارة / التحقق من الجهة المختصة', de: 'Termin buchen / zuständige Behörde prüfen' },

    procExplain_visaIssuance: { ko: '재외공관 또는 사증발급인정서를 통한 최초 사증 발급 절차입니다.', en: 'First-time visa issuance via a consulate or a certificate for visa issuance.', 'zh-CN': '通过驻外使领馆或认定书的首次签证发放手续。', ja: '在外公館または査証発給認定書による最初の査証発給の手続きです。', vi: 'Thủ tục cấp visa lần đầu qua cơ quan đại diện ở nước ngoài hoặc giấy xác nhận cấp visa.', tl: 'Proseso ng unang pag-isyu ng visa sa pamamagitan ng konsulado o sertipiko ng kumpirmasyon sa pag-isyu ng visa.', id: 'Prosedur penerbitan visa pertama melalui perwakilan di luar negeri atau surat keterangan konfirmasi penerbitan visa.', ru: 'Процедура первичной выдачи визы через зарубежное представительство или по сертификату подтверждения выдачи визы.', fr: 'Première délivrance de visa via une mission diplomatique ou un certificat de confirmation de délivrance de visa.', es: 'Trámite de primera emisión de visado a través de una misión en el extranjero o del certificado de confirmación de emisión de visado.', ar: 'إجراء إصدار التأشيرة لأول مرة عبر بعثة في الخارج أو شهادة تأكيد إصدار التأشيرة.', de: 'Erstmalige Visumerteilung über eine Auslandsvertretung oder eine Bescheinigung über die Bestätigung der Visumerteilung.' },
    procExplain_certificateOfVisaIssuance: { ko: '국내 초청자가 출입국·외국인관서에서 인정서를 신청하는 절차입니다.', en: 'A domestic sponsor applies for the certificate at an immigration office.', 'zh-CN': '由境内邀请方在出入境机关申请认定书的手续。', ja: '国内の招へい者が出入国・外国人官署で認定書を申請する手続きです。', vi: 'Thủ tục người mời trong nước nộp đơn xin giấy xác nhận tại cơ quan xuất nhập cảnh.', tl: 'Proseso kung saan ang nag-imbita sa loob ng bansa ay nag-aaplay ng sertipiko sa immigration office.', id: 'Prosedur pengundang di dalam negeri mengajukan surat keterangan di kantor imigrasi.', ru: 'Процедура, при которой приглашающая сторона в стране подаёт заявление на сертификат в миграционном органе.', fr: 'Procédure par laquelle un invitant en Corée demande le certificat auprès d’un bureau d’immigration.', es: 'Trámite por el que un invitante en el país solicita el certificado en una oficina de inmigración.', ar: 'إجراء يتقدّم فيه الجهة الداعية داخل البلاد بطلب الشهادة لدى مكتب الهجرة.', de: 'Verfahren, bei dem eine einladende Person im Inland die Bescheinigung beim Einwanderungsamt beantragt.' },
    procExplain_statusChange: { ko: '출국하지 않고 국내에서 다른 체류자격으로 변경하는 절차입니다.', en: 'Switch to another status inside Korea without leaving.', 'zh-CN': '无需出境，在韩国境内变更为其他居留资格。', ja: '出国せずに国内で他の滞在資格に変更する手続きです。', vi: 'Thủ tục chuyển sang tư cách cư trú khác trong nước mà không xuất cảnh.', tl: 'Proseso ng pagpapalit sa ibang status of stay sa loob ng bansa nang hindi umaalis.', id: 'Prosedur mengubah ke status tinggal lain di dalam negeri tanpa keluar.', ru: 'Процедура смены на другой статус пребывания внутри страны без выезда.', fr: 'Passer à un autre statut de séjour depuis la Corée, sans sortir du pays.', es: 'Cambiar a otro estatus de residencia dentro del país sin salir.', ar: 'إجراء التغيير إلى وضع إقامة آخر داخل البلاد دون مغادرة.', de: 'Wechsel zu einem anderen Aufenthaltsstatus im Inland ohne Ausreise.' },
    procExplain_extension: { ko: '현재 체류자격의 체류기간을 연장하는 절차입니다.', en: 'Extend the stay period of your current status.', 'zh-CN': '延长当前居留资格的停留期限。', ja: '現在の滞在資格の滞在期間を延長する手続きです。', vi: 'Thủ tục gia hạn thời gian cư trú của tư cách hiện tại.', tl: 'Proseso ng pagpapahaba ng panahon ng paninirahan ng kasalukuyang status.', id: 'Prosedur memperpanjang masa tinggal status saat ini.', ru: 'Процедура продления срока пребывания текущего статуса.', fr: 'Prolonger la durée de séjour de votre statut actuel.', es: 'Prorrogar el periodo de estancia de su estatus actual.', ar: 'إجراء تمديد مدة الإقامة لوضعك الحالي.', de: 'Verlängerung der Aufenthaltsdauer Ihres aktuellen Status.' },
    procExplain_statusGrant: { ko: '국내 출생 등으로 새로 체류자격을 부여받는 절차입니다.', en: 'Be newly granted a status, e.g. for a child born in Korea.', 'zh-CN': '因在韩出生等情形新获得居留资格。', ja: '国内出生などで新たに滞在資格を付与される手続きです。', vi: 'Thủ tục được cấp mới tư cách cư trú, ví dụ con sinh ra tại Hàn Quốc.', tl: 'Proseso ng bagong pagkakaloob ng status, hal. para sa batang ipinanganak sa Korea.', id: 'Prosedur memperoleh status tinggal baru, mis. untuk anak yang lahir di Korea.', ru: 'Процедура нового предоставления статуса, например ребёнку, родившемуся в Корее.', fr: 'Octroi d’un nouveau statut, p. ex. pour un enfant né en Corée.', es: 'Concesión de un nuevo estatus, p. ej. para un hijo nacido en Corea.', ar: 'إجراء منح وضع إقامة جديد، مثلًا لطفل وُلد في كوريا.', de: 'Neuerteilung eines Status, z. B. für ein in Korea geborenes Kind.' },
    procExplain_registration: { ko: '90일 초과 체류 시 외국인등록증을 발급받는 절차입니다.', en: 'Get a registration card when staying over 90 days.', 'zh-CN': '停留超过90天时办理外国人登录证。', ja: '90日を超えて滞在する場合に外国人登録証を発給してもらう手続きです。', vi: 'Thủ tục cấp thẻ đăng ký người nước ngoài khi cư trú quá 90 ngày.', tl: 'Proseso ng pagkuha ng registration card kapag mananatili nang higit 90 araw.', id: 'Prosedur memperoleh kartu registrasi orang asing saat tinggal lebih dari 90 hari.', ru: 'Процедура получения регистрационной карты иностранца при пребывании свыше 90 дней.', fr: 'Obtention de la carte d’enregistrement en cas de séjour de plus de 90 jours.', es: 'Obtener la tarjeta de registro al permanecer más de 90 días.', ar: 'إجراء الحصول على بطاقة تسجيل الأجانب عند الإقامة أكثر من 90 يومًا.', de: 'Erhalt des Ausländerregistrierungsausweises bei einem Aufenthalt von mehr als 90 Tagen.' },
    procExplain_activitiesOutsideStatus: { ko: '현재 자격으로 허용되지 않는 활동을 허가받는 절차입니다.', en: 'Permission to do activities your status does not allow.', 'zh-CN': '申请从事当前资格不允许活动的许可。', ja: '現在の資格では認められない活動の許可を受ける手続きです。', vi: 'Thủ tục xin phép thực hiện hoạt động mà tư cách hiện tại không cho phép.', tl: 'Proseso ng pagkuha ng pahintulot para sa aktibidad na hindi pinahihintulutan ng kasalukuyang status.', id: 'Prosedur memperoleh izin untuk kegiatan yang tidak diperbolehkan oleh status saat ini.', ru: 'Процедура получения разрешения на деятельность, не допускаемую текущим статусом.', fr: 'Autorisation d’exercer des activités non permises par votre statut actuel.', es: 'Permiso para realizar actividades que su estatus actual no permite.', ar: 'إجراء الحصول على إذن لنشاط لا يسمح به وضعك الحالي.', de: 'Erlaubnis für Tätigkeiten, die Ihr aktueller Status nicht zulässt.' },
    procExplain_workplaceChange: { ko: '근무처를 변경하거나 추가할 때 신고·허가하는 절차입니다.', en: 'Report or get permission when changing/adding a workplace.', 'zh-CN': '变更或增加工作单位时的申报/许可手续。', ja: '勤務先を変更または追加する際に届け出・許可を受ける手続きです。', vi: 'Thủ tục khai báo · xin phép khi thay đổi hoặc bổ sung nơi làm việc.', tl: 'Proseso ng pag-uulat·pagkuha ng pahintulot kapag nagpapalit o nagdaragdag ng pinagtatrabahuhan.', id: 'Prosedur pelaporan·perizinan saat mengubah atau menambah tempat kerja.', ru: 'Процедура уведомления или получения разрешения при смене либо добавлении места работы.', fr: 'Déclaration ou autorisation lors du changement ou de l’ajout d’un lieu de travail.', es: 'Notificación o autorización al cambiar o añadir un lugar de trabajo.', ar: 'إجراء الإبلاغ أو الحصول على إذن عند تغيير جهة العمل أو إضافتها.', de: 'Meldung oder Genehmigung beim Wechsel oder Hinzufügen eines Arbeitsplatzes.' },
    procExplain_reentry: { ko: '체류 중 출국 후 같은 자격으로 다시 입국하기 위한 절차입니다.', en: 'Re-enter with the same status after a trip abroad.', 'zh-CN': '在停留期间出境后以同一资格再次入境。', ja: '滞在中に出国した後、同じ資格で再び入国するための手続きです。', vi: 'Thủ tục để tái nhập cảnh với cùng tư cách sau khi xuất cảnh trong thời gian cư trú.', tl: 'Proseso upang muling pumasok gamit ang parehong status pagkatapos lumabas habang naninirahan.', id: 'Prosedur untuk masuk kembali dengan status yang sama setelah keluar selama masa tinggal.', ru: 'Процедура для повторного въезда с тем же статусом после выезда во время пребывания.', fr: 'Réentrer avec le même statut après un voyage à l’étranger pendant le séjour.', es: 'Reentrar con el mismo estatus tras un viaje al extranjero durante la estancia.', ar: 'إجراء إعادة الدخول بالوضع نفسه بعد المغادرة أثناء الإقامة.', de: 'Wiedereinreise mit demselben Status nach einer Auslandsreise während des Aufenthalts.' },
    procExplain_visitReservation: { ko: '하이코리아 방문예약과 관할 출입국·외국인관서 확인을 도와드립니다.', en: 'Helps with HiKorea booking and finding the competent office.', 'zh-CN': '协助进行 HiKorea 预约并确认管辖机关。', ja: 'HiKorea の訪問予約と管轄の出入国・外国人官署の確認をお手伝いします。', vi: 'Hỗ trợ đặt lịch hẹn HiKorea và xác định cơ quan xuất nhập cảnh quản lý.', tl: 'Tumutulong sa pag-book sa HiKorea at paghahanap ng may hurisdiksyong immigration office.', id: 'Membantu reservasi HiKorea dan menemukan kantor imigrasi yang berwenang.', ru: 'Помогает записаться на приём через HiKorea и найти компетентный миграционный орган.', fr: 'Aide à la prise de rendez-vous sur HiKorea et à trouver le bureau d’immigration compétent.', es: 'Ayuda con la reserva en HiKorea y a encontrar la oficina de inmigración competente.', ar: 'يساعدك في حجز موعد عبر HiKorea وإيجاد مكتب الهجرة المختص.', de: 'Hilft bei der Terminbuchung über HiKorea und beim Finden des zuständigen Einwanderungsamts.' },

    summaryEyebrow: { ko: '선택한 안내', en: 'Your selection', 'zh-CN': '您的选择', ja: '選択した案内', vi: 'Lựa chọn của bạn', tl: 'Ang iyong pinili', id: 'Pilihan Anda', ru: 'Ваш выбор', fr: 'Votre sélection', es: 'Su selección', ar: 'اختيارك', de: 'Ihre Auswahl' },
    summaryProcedurePrefix: { ko: '현재 선택한 절차', en: 'Selected procedure', 'zh-CN': '当前选择的手续', ja: '現在選択中の手続き', vi: 'Thủ tục đã chọn', tl: 'Napiling proseso', id: 'Prosedur yang dipilih', ru: 'Выбранная процедура', fr: 'Procédure sélectionnée', es: 'Trámite seleccionado', ar: 'الإجراء المحدد', de: 'Ausgewähltes Verfahren' },
    summaryWho: { ko: '이 절차는 누구에게 해당하나요?', en: 'Who is this procedure for?', 'zh-CN': '该手续适用于谁？', ja: 'この手続きは誰が対象ですか？', vi: 'Thủ tục này dành cho ai?', tl: 'Para kanino ang prosesong ito?', id: 'Untuk siapa prosedur ini?', ru: 'Для кого эта процедура?', fr: 'À qui s’adresse cette procédure ?', es: '¿A quién corresponde este trámite?', ar: 'لمن هذا الإجراء؟', de: 'Für wen ist dieses Verfahren?' },
    summaryWhoParent: { ko: '아래에서 세부코드를 고르면 더 정확한 안내를 받을 수 있습니다.', en: 'Pick a sub-code below for more specific guidance.', 'zh-CN': '在下方选择子代码可获得更精确的指引。', ja: '下で詳細コードを選ぶと、より正確な案内を受けられます。', vi: 'Chọn mã chi tiết bên dưới để nhận hướng dẫn chính xác hơn.', tl: 'Pumili ng subcode sa ibaba para sa mas tiyak na gabay.', id: 'Pilih kode rinci di bawah untuk panduan yang lebih spesifik.', ru: 'Выберите подкод ниже для более точной инструкции.', fr: 'Choisissez un sous-code ci-dessous pour un guide plus précis.', es: 'Elija un subcódigo abajo para una guía más precisa.', ar: 'اختر رمزًا تفصيليًا أدناه للحصول على دليل أدق.', de: 'Wählen Sie unten einen Untercode für eine genauere Anleitung.' },
    changeSubcode: { ko: '세부코드 바꾸기', en: 'Change sub-code', 'zh-CN': '更改子代码', ja: '詳細コードを変更', vi: 'Đổi mã chi tiết', tl: 'Baguhin ang subcode', id: 'Ubah kode rinci', ru: 'Сменить подкод', fr: 'Changer de sous-code', es: 'Cambiar subcódigo', ar: 'تغيير الرمز التفصيلي', de: 'Untercode ändern' },
    changeProcedure: { ko: '절차 바꾸기', en: 'Change procedure', 'zh-CN': '更改手续', ja: '手続きを変更', vi: 'Đổi thủ tục', tl: 'Baguhin ang proseso', id: 'Ubah prosedur', ru: 'Сменить процедуру', fr: 'Changer de procédure', es: 'Cambiar trámite', ar: 'تغيير الإجراء', de: 'Verfahren ändern' },
    sourceBtn: { ko: '공식근거 보기', en: 'Official basis', 'zh-CN': '官方依据', ja: '公式の根拠を見る', vi: 'Căn cứ chính thức', tl: 'Opisyal na batayan', id: 'Dasar resmi', ru: 'Официальное основание', fr: 'Base officielle', es: 'Base oficial', ar: 'الأساس الرسمي', de: 'Amtliche Grundlage' },
    waymakerBtn: { ko: 'Waymaker로 질문하기', en: 'Ask Waymaker', 'zh-CN': '向 Waymaker 提问', ja: 'Waymaker に質問する', vi: 'Hỏi Waymaker', tl: 'Magtanong sa Waymaker', id: 'Tanya Waymaker', ru: 'Спросить Waymaker', fr: 'Demander à Waymaker', es: 'Preguntar a Waymaker', ar: 'اسأل Waymaker', de: 'Waymaker fragen' },
    summaryNoSubcode: { ko: '세부코드 미지정 · 대표 안내', en: 'No sub-code · general guidance', 'zh-CN': '未指定子代码 · 通用指引', ja: '詳細コード未指定 · 代表的な案内', vi: 'Chưa chọn mã chi tiết · hướng dẫn chung', tl: 'Walang subcode · pangkalahatang gabay', id: 'Tanpa kode rinci · panduan umum', ru: 'Подкод не указан · общая инструкция', fr: 'Pas de sous-code · guide général', es: 'Sin subcódigo · guía general', ar: 'بدون رمز تفصيلي · دليل عام', de: 'Kein Untercode · allgemeine Anleitung' },
    summaryProcedureMissing: { ko: '이 자격에는 ‘{label}’ 절차의 출처 기반 안내가 아직 정리되어 있지 않습니다. 하이코리아(1345)·관할 출입국·외국인관서 또는 공식 매뉴얼에서 확인하세요.', en: "Source-backed guidance for the '{label}' procedure is not yet available for this status. Please verify via HiKorea (1345), the competent immigration office, or the official manual.", 'zh-CN': '该资格的“{label}”手续暂无基于官方依据的指引。请通过 HiKorea（1345）、管辖出入境机关或官方手册核实。', ja: 'この資格には「{label}」手続きの出典に基づく案内がまだ整理されていません。HiKorea（1345）・管轄の出入国・外国人官署または公式マニュアルでご確認ください。', vi: 'Tư cách này hiện chưa có hướng dẫn dựa trên nguồn cho thủ tục “{label}”. Vui lòng xác minh qua HiKorea (1345), cơ quan xuất nhập cảnh quản lý hoặc cẩm nang chính thức.', tl: 'Wala pang gabay na nakabatay sa sanggunian para sa prosesong ‘{label}’ para sa status na ito. Mangyaring tiyakin sa HiKorea (1345), sa may hurisdiksyong immigration office, o sa opisyal na manwal.', id: 'Belum ada panduan berbasis sumber untuk prosedur “{label}” pada status ini. Mohon verifikasi melalui HiKorea (1345), kantor imigrasi yang berwenang, atau manual resmi.', ru: 'Для этого статуса пока нет инструкции по процедуре «{label}», основанной на источниках. Пожалуйста, уточните через HiKorea (1345), компетентный миграционный орган или официальное руководство.', fr: "Le guide fondé sur des sources pour la procédure « {label} » n’est pas encore disponible pour ce statut. Veuillez vérifier via HiKorea (1345), le bureau d’immigration compétent ou le manuel officiel.", es: 'Aún no hay una guía basada en fuentes para el trámite «{label}» de este estatus. Verifíquelo a través de HiKorea (1345), la oficina de inmigración competente o el manual oficial.', ar: 'لا يتوفّر بعد دليل مستند إلى المصادر لإجراء «{label}» لهذا الوضع. يرجى التحقق عبر HiKorea (1345) أو مكتب الهجرة المختص أو الدليل الرسمي.', de: 'Für diesen Status gibt es noch keine quellenbasierte Anleitung zum Verfahren „{label}". Bitte prüfen Sie dies über HiKorea (1345), das zuständige Einwanderungsamt oder das amtliche Handbuch.' },

    finderResultTitle: { ko: '이 상황에 가까워 보여요', en: 'This looks closest', 'zh-CN': '看起来最接近这种情况', ja: 'この状況に近いようです', vi: 'Có vẻ gần với tình huống này nhất', tl: 'Ito ang mukhang pinakamalapit', id: 'Ini tampaknya paling sesuai', ru: 'Похоже, это ближе всего', fr: 'Cela semble le plus proche', es: 'Esto parece lo más cercano', ar: 'يبدو أن هذا هو الأقرب', de: 'Das scheint am ehesten zuzutreffen' },
    finderResultLead: { ko: '맞다면 절차 선택으로 이동하세요. 자격·허가 여부는 보장하지 않습니다.', en: 'If correct, continue to procedure selection. This does not guarantee eligibility.', 'zh-CN': '如无误，请继续选择手续。本指引不保证资格或许可。', ja: '合っていれば手続き選択へ進んでください。資格・許可の可否は保証しません。', vi: 'Nếu đúng, hãy tiếp tục chọn thủ tục. Điều này không bảo đảm tư cách hay sự cho phép.', tl: 'Kung tama, magpatuloy sa pagpili ng proseso. Hindi nito ginagarantiyahan ang pagiging karapat-dapat o pahintulot.', id: 'Jika benar, lanjutkan ke pemilihan prosedur. Ini tidak menjamin kelayakan atau izin.', ru: 'Если верно, перейдите к выбору процедуры. Это не гарантирует право или разрешение.', fr: 'Si c’est correct, passez au choix de la procédure. Cela ne garantit ni l’éligibilité ni l’autorisation.', es: 'Si es correcto, continúe a la selección del trámite. Esto no garantiza la elegibilidad ni la autorización.', ar: 'إذا كان صحيحًا، تابع إلى اختيار الإجراء. هذا لا يضمن الأهلية أو الإذن.', de: 'Wenn das zutrifft, fahren Sie mit der Verfahrensauswahl fort. Dies garantiert weder Berechtigung noch Genehmigung.' },
    finderLowTitle: { ko: '공식기관 확인이 필요한 상황입니다', en: 'Official confirmation is recommended', 'zh-CN': '建议向官方机关确认', ja: '公式機関での確認が必要な状況です', vi: 'Nên xác nhận với cơ quan chính thức', tl: 'Inirerekomenda ang opisyal na kumpirmasyon', id: 'Disarankan konfirmasi ke instansi resmi', ru: 'Рекомендуется подтверждение в официальном органе', fr: 'Une confirmation officielle est recommandée', es: 'Se recomienda confirmación oficial', ar: 'يُنصح بالتأكد من جهة رسمية', de: 'Eine amtliche Bestätigung wird empfohlen' },
    finderLowLead: { ko: '정확히 판단하기 어려워, 아래 가까운 세부코드를 참고하시고 관할 출입국·외국인관서나 하이코리아(1345)에서 최종 확인하세요.', en: 'It is hard to determine precisely. Consider the closest sub-codes below and confirm with the competent immigration office or HiKorea (1345).', 'zh-CN': '难以精确判断。请参考下方最接近的子代码，并向管辖出入境机关或 HiKorea（1345）最终确认。', ja: '正確な判断が難しいため、下の近い詳細コードを参考にし、管轄の出入国・外国人官署または HiKorea（1345）で最終確認してください。', vi: 'Khó xác định chính xác. Hãy tham khảo các mã chi tiết gần nhất bên dưới và xác nhận cuối cùng với cơ quan xuất nhập cảnh quản lý hoặc HiKorea (1345).', tl: 'Mahirap matukoy nang tumpak. Isaalang-alang ang pinakamalapit na subcode sa ibaba at kumpirmahin sa may hurisdiksyong immigration office o sa HiKorea (1345).', id: 'Sulit ditentukan dengan tepat. Pertimbangkan kode rinci terdekat di bawah dan konfirmasi akhir ke kantor imigrasi yang berwenang atau HiKorea (1345).', ru: 'Точно определить трудно. Рассмотрите ближайшие подкоды ниже и окончательно уточните в компетентном миграционном органе или на HiKorea (1345).', fr: 'Difficile à déterminer avec précision. Examinez les sous-codes les plus proches ci-dessous et confirmez auprès du bureau d’immigration compétent ou de HiKorea (1345).', es: 'Es difícil determinarlo con precisión. Considere los subcódigos más cercanos abajo y confirme con la oficina de inmigración competente o HiKorea (1345).', ar: 'يصعب التحديد بدقة. راجع الرموز التفصيلية الأقرب أدناه وأكّد نهائيًا لدى مكتب الهجرة المختص أو HiKorea (1345).', de: 'Eine genaue Bestimmung ist schwierig. Ziehen Sie die nächstgelegenen Untercodes unten in Betracht und bestätigen Sie dies abschließend beim zuständigen Einwanderungsamt oder bei HiKorea (1345).' },
    finderPickManually: { ko: '세부코드 직접 고르기', en: 'Choose a sub-code myself', 'zh-CN': '自行选择子代码', ja: '詳細コードを自分で選ぶ', vi: 'Tự chọn mã chi tiết', tl: 'Pumili mismo ng subcode', id: 'Pilih sendiri kode rinci', ru: 'Выбрать подкод самостоятельно', fr: 'Choisir moi-même un sous-code', es: 'Elegir un subcódigo yo mismo', ar: 'اختيار الرمز التفصيلي بنفسي', de: 'Untercode selbst wählen' },

    cardCtaSubcoded: { ko: '상황·절차별로 안내받기', en: 'Guide me by situation & procedure', 'zh-CN': '按情况和手续获取指引', ja: '状況・手続き別に案内を受ける', vi: 'Hướng dẫn theo tình huống & thủ tục', tl: 'Gabayan ako ayon sa sitwasyon at proseso', id: 'Pandu saya berdasarkan situasi & prosedur', ru: 'Подсказать по ситуации и процедуре', fr: 'Me guider par situation et procédure', es: 'Guiarme por situación y trámite', ar: 'أرشدني حسب الحالة والإجراء', de: 'Nach Situation und Verfahren führen' },
    cardCtaPlain: { ko: '절차별로 안내받기', en: 'Guide me by procedure', 'zh-CN': '按手续获取指引', ja: '手続き別に案内を受ける', vi: 'Hướng dẫn theo thủ tục', tl: 'Gabayan ako ayon sa proseso', id: 'Pandu saya berdasarkan prosedur', ru: 'Подсказать по процедуре', fr: 'Me guider par procédure', es: 'Guiarme por trámite', ar: 'أرشدني حسب الإجراء', de: 'Nach Verfahren führen' },
    cardCtaHint: { ko: '세부코드와 절차를 골라 바로 안내로 이동', en: 'Pick a sub-code and procedure to jump straight to guidance', 'zh-CN': '选择子代码与手续即可直达指引', ja: '詳細コードと手続きを選んですぐ案内へ移動', vi: 'Chọn mã chi tiết và thủ tục để đến hướng dẫn ngay', tl: 'Pumili ng subcode at proseso para agad sa gabay', id: 'Pilih kode rinci dan prosedur untuk langsung ke panduan', ru: 'Выберите подкод и процедуру, чтобы сразу перейти к инструкции', fr: 'Choisissez un sous-code et une procédure pour accéder directement au guide', es: 'Elija un subcódigo y un trámite para ir directo a la guía', ar: 'اختر رمزًا تفصيليًا وإجراءً للانتقال مباشرة إلى الدليل', de: 'Untercode und Verfahren wählen, um direkt zur Anleitung zu springen' },
    invalidNotice: { ko: '요청하신 세부코드/절차를 찾을 수 없어 상위 자격 안내로 이동했습니다.', en: 'The requested sub-code/procedure was not found; showing the parent status instead.', 'zh-CN': '未找到所请求的子代码/手续，已转为显示上级资格指引。', ja: 'ご指定の詳細コード/手続きが見つからなかったため、上位資格の案内へ移動しました。', vi: 'Không tìm thấy mã chi tiết/thủ tục yêu cầu; thay vào đó hiển thị tư cách cấp trên.', tl: 'Hindi natagpuan ang hiniling na subcode/proseso; ipinakita ang pangunahing status sa halip.', id: 'Kode rinci/prosedur yang diminta tidak ditemukan; menampilkan status induk sebagai gantinya.', ru: 'Запрошенный подкод/процедура не найдены; вместо этого показан вышестоящий статус.', fr: 'Le sous-code ou la procédure demandés sont introuvables ; affichage du statut parent à la place.', es: 'No se encontró el subcódigo/trámite solicitado; se muestra el estatus principal en su lugar.', ar: 'تعذّر العثور على الرمز التفصيلي/الإجراء المطلوب؛ يُعرض الوضع الأعلى بدلًا منه.', de: 'Der angeforderte Untercode bzw. das Verfahren wurde nicht gefunden; stattdessen wird der übergeordnete Status angezeigt.' },
    errNoRecord: { ko: '해당 체류자격 정보를 찾을 수 없습니다.', en: 'Could not find this status.', 'zh-CN': '未找到该居留资格信息。', ja: 'この滞在資格の情報が見つかりません。', vi: 'Không tìm thấy thông tin tư cách cư trú này.', tl: 'Hindi matagpuan ang status na ito.', id: 'Tidak dapat menemukan status tinggal ini.', ru: 'Не удалось найти этот статус пребывания.', fr: 'Impossible de trouver ce statut.', es: 'No se pudo encontrar este estatus.', ar: 'تعذّر العثور على وضع الإقامة هذا.', de: 'Dieser Aufenthaltsstatus konnte nicht gefunden werden.' },
    sourceLimitedNote: { ko: '이 자격은 출처 기반 안내가 제한적입니다. 표시되지 않는 절차는 공식 매뉴얼·하이코리아에서 확인하세요.', en: 'Source-backed guidance is limited for this status. Verify procedures not shown via the official manual or HiKorea.', 'zh-CN': '该资格的官方依据指引有限。未显示的手续请通过官方手册或 HiKorea 核实。', ja: 'この資格は出典に基づく案内が限られています。表示されない手続きは公式マニュアルまたは HiKorea でご確認ください。', vi: 'Hướng dẫn dựa trên nguồn cho tư cách này còn hạn chế. Các thủ tục không hiển thị, vui lòng xác minh qua cẩm nang chính thức hoặc HiKorea.', tl: 'Limitado ang gabay na nakabatay sa sanggunian para sa status na ito. Tiyakin ang mga prosesong hindi ipinakita sa opisyal na manwal o sa HiKorea.', id: 'Panduan berbasis sumber untuk status ini terbatas. Verifikasi prosedur yang tidak ditampilkan melalui manual resmi atau HiKorea.', ru: 'Инструкции на основе источников для этого статуса ограничены. Не показанные процедуры уточняйте в официальном руководстве или на HiKorea.', fr: 'Le guide fondé sur des sources est limité pour ce statut. Vérifiez les procédures non affichées via le manuel officiel ou HiKorea.', es: 'La guía basada en fuentes es limitada para este estatus. Verifique los trámites no mostrados en el manual oficial o en HiKorea.', ar: 'الدليل المستند إلى المصادر محدود لهذا الوضع. تحقّق من الإجراءات غير المعروضة عبر الدليل الرسمي أو HiKorea.', de: 'Die quellenbasierte Anleitung ist für diesen Status begrenzt. Prüfen Sie nicht angezeigte Verfahren über das amtliche Handbuch oder HiKorea.' }
  };

  /* Curated, plain-language "who this is" labels. Only for sub-codes whose
   * descriptor is explicitly given by the product spec — never invented. Other
   * sub-codes fall back to their official Korean name (no fabricated content). */
  var SUBCODE_USER_LABEL = {
    'F-6-1': { ko: '한국 국민과 혼인 중인 외국인 배우자', en: 'Foreign spouse currently married to a Korean national', 'zh-CN': '与韩国国民处于婚姻关系中的外籍配偶', ja: '韓国国民と婚姻中の外国人配偶者', vi: 'Vợ/chồng người nước ngoài đang trong hôn nhân với công dân Hàn Quốc', tl: 'Dayuhang asawa na kasalukuyang kasal sa isang mamamayang Korean', id: 'Pasangan asing yang sedang menikah dengan warga negara Korea', ru: 'Иностранный супруг(а), состоящий(ая) в браке с гражданином Кореи', fr: 'Conjoint étranger actuellement marié à un ressortissant coréen', es: 'Cónyuge extranjero actualmente casado con un nacional coreano', ar: 'الزوج/الزوجة الأجنبي المتزوج حاليًا من مواطن كوري', de: 'Ausländischer Ehepartner, der derzeit mit einem koreanischen Staatsangehörigen verheiratet ist' },
    'F-6-2': { ko: '한국 국민과의 사이에서 태어난 자녀를 양육하는 경우', en: 'Raising a child born with a Korean national', 'zh-CN': '抚养与韩国国民所生子女的情形', ja: '韓国国民との間に生まれた子を養育している場合', vi: 'Trường hợp đang nuôi con sinh ra với công dân Hàn Quốc', tl: 'Kapag inaalagaan ang anak na ipinanganak kasama ang isang mamamayang Korean', id: 'Saat mengasuh anak yang lahir dari warga negara Korea', ru: 'Случай воспитания ребёнка, рождённого с гражданином Кореи', fr: 'Cas où l’on élève un enfant né avec un ressortissant coréen', es: 'Cuando se cría a un hijo nacido con un nacional coreano', ar: 'حالة تربية طفل وُلد من مواطن كوري', de: 'Wenn ein mit einem koreanischen Staatsangehörigen geborenes Kind erzogen wird' },
    'F-6-3': { ko: '배우자 사망·실종·이혼 등으로 혼인관계가 단절된 경우', en: 'Marriage ended by spouse death, disappearance, or divorce', 'zh-CN': '因配偶死亡、失踪、离婚等导致婚姻关系终止的情形', ja: '配偶者の死亡・失踪・離婚などで婚姻関係が断絶した場合', vi: 'Trường hợp quan hệ hôn nhân chấm dứt do vợ/chồng qua đời, mất tích, ly hôn, v.v.', tl: 'Kapag natapos ang pagsasama dahil sa pagkamatay, pagkawala, o diborsyo ng asawa', id: 'Saat hubungan pernikahan terputus karena pasangan meninggal, hilang, atau bercerai', ru: 'Случай прекращения брака из-за смерти, исчезновения или развода супруга(и)', fr: 'Cas où le mariage a pris fin par décès, disparition ou divorce du conjoint', es: 'Cuando el matrimonio terminó por fallecimiento, desaparición o divorcio del cónyuge', ar: 'حالة انقطاع العلاقة الزوجية بسبب وفاة الزوج أو اختفائه أو الطلاق', de: 'Wenn die Ehe durch Tod, Verschwinden oder Scheidung des Ehepartners beendet wurde' }
  };

  /* One-question-at-a-time route finder. Config-driven and reusable: a new
   * status is supported by adding an entry here. Seeded with F-6 exactly as the
   * product spec defines it. Questions narrow to a sub-code; low confidence
   * routes to an honest "official confirmation needed" screen. */
  var ROUTE_FINDER = {
    'F-6': {
      start: 'q1',
      questions: {
        q1: {
          text: { ko: '한국 국민과 현재 혼인 중이신가요?', en: 'Are you currently married to a Korean national?', 'zh-CN': '您目前与韩国国民处于婚姻关系中吗？', ja: '現在、韓国国民と婚姻中ですか？', vi: 'Bạn hiện có đang trong hôn nhân với công dân Hàn Quốc không?', tl: 'Kasalukuyan ka bang kasal sa isang mamamayang Korean?', id: 'Apakah Anda sedang menikah dengan warga negara Korea?', ru: 'Состоите ли вы сейчас в браке с гражданином Кореи?', fr: 'Êtes-vous actuellement marié(e) à un ressortissant coréen ?', es: '¿Está actualmente casado/a con un nacional coreano?', ar: 'هل أنت متزوج حاليًا من مواطن كوري؟', de: 'Sind Sie derzeit mit einem koreanischen Staatsangehörigen verheiratet?' },
          options: [
            { key: 'yes', subcode: 'F-6-1' },
            { key: 'no', next: 'q2' }
          ]
        },
        q2: {
          text: { ko: '한국 국민과의 사이에서 태어난 자녀를 양육 중이신가요?', en: 'Are you raising a child born with a Korean national?', 'zh-CN': '您是否在抚养与韩国国民所生的子女？', ja: '韓国国民との間に生まれた子を養育中ですか？', vi: 'Bạn có đang nuôi con sinh ra với công dân Hàn Quốc không?', tl: 'Inaalagaan mo ba ang isang anak na ipinanganak kasama ang isang mamamayang Korean?', id: 'Apakah Anda sedang mengasuh anak yang lahir dari warga negara Korea?', ru: 'Воспитываете ли вы ребёнка, рождённого с гражданином Кореи?', fr: 'Élevez-vous un enfant né avec un ressortissant coréen ?', es: '¿Está criando a un hijo nacido con un nacional coreano?', ar: 'هل تربّي طفلًا وُلد من مواطن كوري؟', de: 'Erziehen Sie ein mit einem koreanischen Staatsangehörigen geborenes Kind?' },
          options: [
            { key: 'yes', subcode: 'F-6-2' },
            { key: 'no', next: 'q3' }
          ]
        },
        q3: {
          text: { ko: '배우자의 사망·실종·이혼 등으로 혼인관계가 종료되었나요?', en: "Did the marriage end through the spouse's death, disappearance, or divorce?", 'zh-CN': '婚姻关系是否因配偶死亡、失踪、离婚等而终止？', ja: '配偶者の死亡・失踪・離婚などで婚姻関係が終了しましたか？', vi: 'Quan hệ hôn nhân có chấm dứt do vợ/chồng qua đời, mất tích, ly hôn, v.v. không?', tl: 'Natapos ba ang pagsasama dahil sa pagkamatay, pagkawala, o diborsyo ng asawa?', id: 'Apakah hubungan pernikahan berakhir karena pasangan meninggal, hilang, atau bercerai?', ru: 'Прекратился ли брак из-за смерти, исчезновения или развода супруга(и)?', fr: 'Le mariage a-t-il pris fin par le décès, la disparition ou le divorce du conjoint ?', es: '¿Terminó el matrimonio por fallecimiento, desaparición o divorcio del cónyuge?', ar: 'هل انتهت العلاقة الزوجية بوفاة الزوج أو اختفائه أو الطلاق؟', de: 'Endete die Ehe durch Tod, Verschwinden oder Scheidung des Ehepartners?' },
          options: [
            { key: 'yes', subcode: 'F-6-3' },
            { key: 'no', official: true }
          ]
        }
      }
    }
  };

  /* ------------------------------------------------------------- utilities */
  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (ch) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[ch];
    });
  }
  function lang() {
    var l = (typeof currentLanguage !== 'undefined' && currentLanguage) ? currentLanguage : 'ko';
    return STR.close[l] ? l : (l && l.indexOf('zh') === 0 ? 'zh-CN' : 'ko');
  }
  function interp(s, vars) {
    if (!vars) return s;
    return s.replace(/\{(\w+)\}/g, function (m, k) { return vars[k] != null ? vars[k] : m; });
  }
  function S(key, vars) {
    var e = STR[key];
    if (!e) return key;
    var l = lang();
    return interp(e[l] || e.ko || e.en || key, vars);
  }
  function pick(entry) {
    if (!entry) return '';
    if (typeof entry === 'string') return entry;
    var l = lang();
    return entry[l] || entry.ko || entry.en || '';
  }
  function normCode(code) {
    if (!code) return '';
    var c = String(code).toUpperCase().replace(/\s|_/g, '');
    // Insert the canonical hyphen between the leading letter run and the first
    // digit: D2→D-2, F6-1→F-6-1. Already-hyphenated (F-6-1) and letter-only
    // codes (K-ETA, REGION-S, K-STAR) are left untouched.
    var m = c.match(/^([A-Z]+)(\d.*)$/);
    if (m) c = m[1] + '-' + m[2];
    return c;
  }
  function cssEsc(s) {
    if (typeof CSS !== 'undefined' && CSS.escape) return CSS.escape(s);
    return String(s).replace(/["\\]/g, '\\$&');
  }

  /* ----------------------------------------------------------- data access */
  function allRecords() {
    if (typeof VISA_DATA !== 'undefined' && Array.isArray(VISA_DATA)) return VISA_DATA;
    if (typeof window !== 'undefined' && Array.isArray(window.VISA_DATA)) return window.VISA_DATA;
    return [];
  }
  function findRecord(code, records) {
    records = records || allRecords();
    var n = normCode(code);
    for (var i = 0; i < records.length; i++) {
      if (normCode(records[i].code) === n) return records[i];
    }
    return null;
  }
  function getSubcodes(rec) {
    if (!rec) return [];
    if (Array.isArray(rec.subcodes)) return rec.subcodes;
    if (Array.isArray(rec.subCodes)) return rec.subCodes;
    return [];
  }
  // Resolve a query that may be a parent code OR a direct sub-code.
  // Returns { code, subcode } where code is the parent record code.
  function resolveCode(code, records) {
    records = records || allRecords();
    var n = normCode(code);
    var direct = findRecord(n, records);
    if (direct) return { code: direct.code, subcode: '' };
    for (var i = 0; i < records.length; i++) {
      var subs = getSubcodes(records[i]);
      for (var j = 0; j < subs.length; j++) {
        if (normCode(subs[j].code) === n) return { code: records[i].code, subcode: subs[j].code };
      }
    }
    return { code: '', subcode: '' };
  }
  function visaNameKo(rec) {
    var raw = (rec && (rec.nameKo || rec.name)) || '';
    if (typeof paradisoStripInternalReviewArtifacts === 'function') {
      try { return paradisoStripInternalReviewArtifacts(raw) || raw; } catch (e) { /* noop */ }
    }
    return raw;
  }
  function visaNameEn(rec) {
    if (!rec) return '';
    if (rec.nameEn || rec.name_en) return rec.nameEn || rec.name_en;
    if (typeof getVisaNameEn === 'function') { try { return getVisaNameEn(rec) || ''; } catch (e) { /* noop */ } }
    return '';
  }
  function subcodeNameKo(s) {
    var raw = (s && (s.nameKo || s.name)) || '';
    if (typeof paradisoStripInternalReviewArtifacts === 'function') {
      try { return paradisoStripInternalReviewArtifacts(raw) || raw; } catch (e) { /* noop */ }
    }
    return raw;
  }
  function subcodeUserLabel(s) {
    var e = SUBCODE_USER_LABEL[normCode(s.code)];
    return e ? pick(e) : '';
  }
  // Display name in the active UI language (English/Chinese when available).
  function recDisplayName(rec) {
    var ko = visaNameKo(rec);
    return lang() === 'ko' ? ko : (visaNameEn(rec) || ko);
  }

  /* ------------------------------------------------------ adapter (pure) */
  function hasDocsField(rec, fields) {
    if (!fields) return false;
    for (var i = 0; i < fields.length; i++) {
      var x = rec[fields[i]];
      if (Array.isArray(x) && x.length) return true;
      if (x && typeof x === 'object' && Object.keys(x).length) return true;
      if (typeof x === 'string' && x.trim()) return true;
    }
    return false;
  }
  function procStructuredDocsPresent(raw) {
    if (!raw) return false;
    var rd = raw.requiredDocs;
    if (Array.isArray(rd)) return rd.length > 0;
    if (rd && typeof rd === 'object') {
      return Object.keys(rd).some(function (k) { return Array.isArray(rd[k]) && rd[k].length > 0; });
    }
    return false;
  }
  function visaIssuanceNotApplicable(rec) {
    if (typeof isVisaIssuanceNotApplicable === 'function') {
      try { return !!isVisaIssuanceNotApplicable(rec); } catch (e) { /* fall through */ }
    }
    return VISA_ISSUANCE_NOT_APPLICABLE_CODES.indexOf(normCode(rec.code)) !== -1;
  }
  // Faithful, DOM-free mirror of index.html getProcedure() availability.
  // Returns 'available' | 'not_applicable' | 'source_limited' | null(omit).
  function procedureStatusForRecord(rec, camelKey, opts) {
    opts = opts || {};
    var raw = rec.procedures && rec.procedures[camelKey];
    if (camelKey === 'visaIssuance') {
      var na = opts.visaIssuanceNotApplicable ? opts.visaIssuanceNotApplicable(rec) : visaIssuanceNotApplicable(rec);
      if (na) return 'not_applicable';
    }
    var explicit = (raw && Object.prototype.hasOwnProperty.call(raw, 'available')) ? raw.available : null;
    if (explicit === false) return 'not_applicable';
    var leg = LEGACY_FIELDS[camelKey] || {};
    var legacyAvailable = procStructuredDocsPresent(raw) ||
      hasDocsField(rec, leg.docs) ||
      (leg.text && rec[leg.text]) ||
      (raw && (raw.summary || (Array.isArray(raw.notes) && raw.notes.length)));
    if (explicit === true || legacyAvailable) return 'available';
    // Present-but-empty procedure stub → honest source-limited, not hidden.
    if (raw) return 'source_limited';
    return null;
  }
  function procOfficialLabel(camelKey) {
    var idx = PROC_LABEL_INDEX[camelKey];
    if (typeof txAt === 'function' && idx != null) {
      try { var v = txAt('procedureLabels', idx, ''); if (v) return v; } catch (e) { /* noop */ }
    }
    return DEFAULT_PROC_LABELS[camelKey] || camelKey;
  }
  // The normalized guidance model the UI is generated from.
  function buildGuidanceModel(rec, opts) {
    if (!rec) return null;
    opts = opts || {};
    var subs = getSubcodes(rec).map(function (s) {
      return {
        code: s.code || '',
        titleKo: subcodeNameKo(s),
        titleEn: s.nameEn || s.name_en || s.titleEn || '',
        userLabelKo: subcodeUserLabel(s),
        status: s.status || '',
        needsReview: !!s.needsManualReview
      };
    });
    var procedures = PROCEDURE_ORDER.map(function (camel) {
      var st = procedureStatusForRecord(rec, camel, opts);
      if (!st) return null;
      return {
        key: SNAKE_OF[camel],
        camelKey: camel,
        officialLabel: procOfficialLabel(camel),
        userLabel: S('procUser_' + camel),
        explanation: S('procExplain_' + camel),
        status: st
      };
    }).filter(Boolean);
    return {
      code: rec.code,
      titleKo: visaNameKo(rec),
      titleEn: visaNameEn(rec),
      hasSubcodes: subs.length > 0,
      subcodes: subs,
      procedures: procedures,
      hasRouteFinder: !!ROUTE_FINDER[normCode(rec.code)]
    };
  }

  /* --------------------------------------------------------- URL state (pure) */
  function parseRouteState(search) {
    var params;
    try { params = new URLSearchParams(search || ''); } catch (e) { return { code: '', subcode: '', procedure: '' }; }
    return {
      code: normCode(params.get('code') || ''),
      subcode: normCode(params.get('subcode') || ''),
      procedure: (params.get('procedure') || '').trim()
    };
  }
  function serializeRouteState(state) {
    state = state || {};
    var params = new URLSearchParams();
    if (state.code) params.set('code', state.code);
    if (state.subcode) params.set('subcode', state.subcode);
    if (state.procedure) params.set('procedure', state.procedure);
    var s = params.toString();
    return s ? '?' + s : '';
  }
  // Validate a parsed state against the data. Drops invalid sub-code/procedure
  // and reports what was corrected so the UI can show a non-blocking notice.
  function validateRouteState(parsed, records) {
    records = records || allRecords();
    var warnings = [];
    var out = { code: '', subcode: '', procedure: '' };
    if (!parsed || !parsed.code) return { state: out, warnings: warnings };
    var resolved = resolveCode(parsed.code, records);
    if (!resolved.code) { warnings.push('unknown-code'); return { state: out, warnings: warnings }; }
    out.code = resolved.code;
    var rec = findRecord(resolved.code, records);
    // A direct sub-code in ?code= carries its own subcode forward.
    var wantSub = parsed.subcode || resolved.subcode || '';
    if (wantSub) {
      var subs = getSubcodes(rec);
      var match = subs.some(function (s) { return normCode(s.code) === normCode(wantSub); });
      if (match) out.subcode = subs.filter(function (s) { return normCode(s.code) === normCode(wantSub); })[0].code;
      else warnings.push('invalid-subcode');
    }
    if (parsed.procedure) {
      if (APPROVED_PROCEDURES.indexOf(parsed.procedure) !== -1) out.procedure = parsed.procedure;
      else warnings.push('invalid-procedure');
    }
    return { state: out, warnings: warnings };
  }

  /* ------------------------------------------------ route-finder engine (pure) */
  // Given a finder config, a question id, and an option key, return the next
  // step: { subcode } | { official: true } | { next: questionId } | null.
  function routeFinderNext(cfg, questionId, optionKey) {
    if (!cfg || !cfg.questions || !cfg.questions[questionId]) return null;
    var opts = cfg.questions[questionId].options || [];
    for (var i = 0; i < opts.length; i++) {
      if (opts[i].key === optionKey) {
        if (opts[i].subcode) return { subcode: opts[i].subcode };
        if (opts[i].official) return { official: true };
        if (opts[i].next) return { next: opts[i].next };
        return {};
      }
    }
    return null;
  }

  /* =========================================================================
   * Everything below touches the DOM and only runs in the browser.
   * ========================================================================= */
  if (typeof document === 'undefined') {
    if (typeof module !== 'undefined' && module.exports) {
      module.exports = {
        buildGuidanceModel: buildGuidanceModel,
        procedureStatusForRecord: procedureStatusForRecord,
        parseRouteState: parseRouteState,
        serializeRouteState: serializeRouteState,
        validateRouteState: validateRouteState,
        resolveCode: resolveCode,
        routeFinderNext: routeFinderNext,
        normCode: normCode,
        CAMEL_OF: CAMEL_OF,
        SNAKE_OF: SNAKE_OF,
        APPROVED_PROCEDURES: APPROVED_PROCEDURES,
        PROCEDURE_ORDER: PROCEDURE_ORDER,
        ROUTE_FINDER: ROUTE_FINDER,
        STR: STR,
        SUBCODE_USER_LABEL: SUBCODE_USER_LABEL
      };
    }
    return;
  }

  var OVERLAY_ID = 'routeGuideOverlay';
  // Wizard navigation state for the current flow.
  var flow = null; // { code, subcode, finder } — finder: { qid, history:[] }
  var applyingPop = false;

  /* ------------------------------------------------------------- styling */
  function injectStyles() {
    if (document.getElementById('routeGuideStyles')) return;
    var css = [
      '.route-guide-overlay{position:fixed;inset:0;z-index:1200;display:none;align-items:center;justify-content:center;padding:1.1rem;background:rgba(8,12,20,.55);backdrop-filter:saturate(140%) blur(3px);}',
      '.route-guide-overlay.active{display:flex;}',
      '.route-guide-box{width:100%;max-width:560px;max-height:90vh;display:flex;flex-direction:column;background:var(--bg1,#fff);color:var(--t1,#10151f);border:1px solid var(--bd2,#d8dee8);border-radius:18px;box-shadow:0 24px 70px rgba(8,12,20,.32);overflow:hidden;}',
      '.route-guide-head{display:flex;align-items:flex-start;gap:.6rem;padding:1.05rem 1.15rem .55rem;}',
      '.route-guide-head-main{flex:1;min-width:0;}',
      '.route-guide-eyebrow{font-size:.68rem;font-weight:900;letter-spacing:.06em;text-transform:uppercase;color:var(--ac,#1f7a5a);}',
      '.route-guide-title{margin:.18rem 0 0;font-size:1.06rem;font-weight:900;line-height:1.3;}',
      '.route-guide-intro{margin:.4rem 1.15rem 0;font-size:.82rem;line-height:1.6;color:var(--t2,#56616f);}',
      '.route-guide-close{flex:0 0 auto;width:34px;height:34px;border-radius:9px;border:1px solid var(--bd2,#d8dee8);background:var(--bg2,#f4f6f9);color:var(--t2,#56616f);font-size:1.05rem;line-height:1;cursor:pointer;}',
      '.route-guide-close:hover{border-color:var(--ac,#1f7a5a);color:var(--ac,#1f7a5a);}',
      '.route-guide-body{padding:.85rem 1.15rem 1.15rem;overflow:auto;}',
      '.route-guide-list{display:flex;flex-direction:column;gap:.55rem;margin:.2rem 0 0;}',
      '.route-choice{display:flex;align-items:center;gap:.7rem;width:100%;text-align:left;padding:.8rem .85rem;border:1px solid var(--bd2,#d8dee8);border-radius:13px;background:var(--bg0,#fbfcfe);color:inherit;font:inherit;cursor:pointer;transition:border-color .15s,background .15s,transform .05s;}',
      '.route-choice:hover:not(:disabled){border-color:var(--ac,#1f7a5a);background:var(--acL,#e8f5ef);}',
      '.route-choice:active:not(:disabled){transform:translateY(1px);}',
      '.route-choice:focus-visible{outline:2px solid var(--ac,#1f7a5a);outline-offset:2px;}',
      '.route-choice:disabled{opacity:.55;cursor:not-allowed;}',
      '.route-choice-body{flex:1;min-width:0;display:flex;flex-direction:column;gap:.16rem;}',
      '.route-choice-top{display:flex;align-items:center;gap:.45rem;flex-wrap:wrap;}',
      '.route-choice-code{font-size:.95rem;font-weight:900;letter-spacing:.01em;}',
      '.route-choice-name{font-size:.92rem;font-weight:800;}',
      '.route-choice-sub{font-size:.8rem;font-weight:700;color:var(--t2,#56616f);}',
      '.route-choice-desc{font-size:.8rem;line-height:1.55;color:var(--t2,#56616f);}',
      '.route-choice-en{font-size:.76rem;color:var(--t3,#8a94a3);font-weight:600;}',
      '.route-choice-go{flex:0 0 auto;color:var(--ac,#1f7a5a);font-weight:900;font-size:1.05rem;}',
      '.route-badge{display:inline-flex;align-items:center;font-size:.64rem;font-weight:900;letter-spacing:.02em;padding:.12rem .42rem;border-radius:999px;border:1px solid var(--bd2,#d8dee8);color:var(--t2,#56616f);background:var(--bg2,#f4f6f9);}',
      '.route-badge.is-subcode{color:var(--ac,#1f7a5a);border-color:color-mix(in srgb,var(--ac,#1f7a5a) 45%,transparent);background:var(--acL,#e8f5ef);}',
      '.route-badge.is-situation{color:#7a5a1f;border-color:#e3cf9f;background:#fbf3df;}',
      '.route-badge.is-available{color:#1f7a5a;border-color:#a9dcc6;background:#e8f5ef;}',
      '.route-badge.is-conditional{color:#7a5a1f;border-color:#e3cf9f;background:#fbf3df;}',
      '.route-badge.is-limited,.route-badge.is-review{color:#9a3b2f;border-color:#e8b3aa;background:#fbe9e6;}',
      '.route-badge.is-na{color:#6b7280;border-color:#d8dee8;background:#f1f3f6;}',
      '.route-choice.is-muted{opacity:.62;}',
      '.route-finder-q{font-size:1.02rem;font-weight:850;line-height:1.45;margin:.1rem 0 .8rem;}',
      '.route-finder-actions{display:flex;gap:.5rem;margin-top:.7rem;flex-wrap:wrap;}',
      '.route-unsure{margin-top:.7rem;border-style:dashed;}',
      '.route-foot{display:flex;gap:.5rem;flex-wrap:wrap;margin-top:.95rem;padding-top:.8rem;border-top:1px dashed var(--bd2,#d8dee8);}',
      '.route-textbtn{border:1px solid var(--bd2,#d8dee8);background:var(--bg2,#f4f6f9);color:var(--t2,#56616f);font:inherit;font-size:.8rem;font-weight:800;padding:.5rem .8rem;border-radius:9px;cursor:pointer;}',
      '.route-textbtn:hover{border-color:var(--ac,#1f7a5a);color:var(--ac,#1f7a5a);}',
      '.route-note{font-size:.78rem;line-height:1.6;color:var(--t2,#56616f);background:var(--bg2,#f4f6f9);border:1px solid var(--bd2,#d8dee8);border-radius:11px;padding:.7rem .8rem;margin:.2rem 0 .4rem;}',
      // summary card injected into the result drawer
      '.route-summary-card{border:1.5px solid color-mix(in srgb,var(--ac,#1f7a5a) 55%,transparent);background:linear-gradient(180deg,var(--acL,#e8f5ef),var(--bg1,#fff));border-radius:15px;padding:.95rem 1rem;margin:0 0 1rem;box-shadow:0 6px 20px rgba(8,12,20,.07);}',
      '.route-summary-eyebrow{font-size:.66rem;font-weight:900;letter-spacing:.06em;text-transform:uppercase;color:var(--ac,#1f7a5a);}',
      '.route-summary-title{margin:.2rem 0 .05rem;font-size:1.12rem;font-weight:900;line-height:1.25;}',
      '.route-summary-en{font-size:.82rem;color:var(--t2,#56616f);font-weight:600;}',
      '.route-summary-proc{display:inline-flex;align-items:center;gap:.4rem;margin-top:.55rem;font-size:.82rem;font-weight:800;color:var(--t1,#10151f);background:var(--bg1,#fff);border:1px solid color-mix(in srgb,var(--ac,#1f7a5a) 35%,transparent);border-radius:999px;padding:.28rem .65rem;}',
      '.route-summary-proc b{color:var(--ac,#1f7a5a);}',
      'button.route-summary-proc{font:inherit;font-size:.82rem;font-weight:800;cursor:pointer;}',
      'button.route-summary-proc.is-jump:hover{border-color:var(--ac,#1f7a5a);background:var(--acL,#e8f5ef);}',
      'button.route-summary-proc:focus-visible{outline:2px solid var(--ac,#1f7a5a);outline-offset:2px;}',
      '.route-summary-who{margin:.7rem 0 0;font-size:.82rem;line-height:1.6;}',
      '.route-summary-who-h{font-weight:900;font-size:.74rem;letter-spacing:.02em;color:var(--t2,#56616f);text-transform:uppercase;}',
      '.route-summary-missing{margin:.6rem 0 0;font-size:.8rem;line-height:1.6;color:#9a3b2f;background:#fbe9e6;border:1px solid #e8b3aa;border-radius:10px;padding:.6rem .7rem;}',
      '.route-summary-actions{display:flex;flex-wrap:wrap;gap:.45rem;margin-top:.85rem;}',
      '.route-summary-btn{display:inline-flex;align-items:center;gap:.35rem;font:inherit;font-size:.78rem;font-weight:850;padding:.5rem .75rem;border-radius:9px;border:1px solid var(--bd2,#d8dee8);background:var(--bg1,#fff);color:var(--t1,#10151f);cursor:pointer;}',
      '.route-summary-btn:hover{border-color:var(--ac,#1f7a5a);color:var(--ac,#1f7a5a);}',
      '.route-summary-btn.is-primary{background:var(--ac,#1f7a5a);border-color:var(--ac,#1f7a5a);color:#fff;}',
      '.route-summary-btn.is-primary:hover{filter:brightness(1.05);color:#fff;}',
      // in-card CTA that launches the guided flow from a result card
      '.route-card-cta{display:flex;align-items:center;gap:.6rem;width:100%;text-align:left;margin:.1rem 0 .2rem;padding:.7rem .85rem;border:1.5px solid color-mix(in srgb,var(--ac,#1f7a5a) 50%,transparent);border-radius:13px;background:var(--acL,#e8f5ef);color:var(--t1,#10151f);font:inherit;cursor:pointer;transition:border-color .15s,background .15s,transform .05s;}',
      '.route-card-cta:hover{border-color:var(--ac,#1f7a5a);background:color-mix(in srgb,var(--ac,#1f7a5a) 16%,var(--bg1,#fff));}',
      '.route-card-cta:active{transform:translateY(1px);}',
      '.route-card-cta:focus-visible{outline:2px solid var(--ac,#1f7a5a);outline-offset:2px;}',
      '.route-card-cta-ico{flex:0 0 auto;width:30px;height:30px;border-radius:8px;display:flex;align-items:center;justify-content:center;background:var(--ac,#1f7a5a);color:#fff;font-size:1rem;font-weight:900;}',
      '.route-card-cta-tx{flex:1;min-width:0;display:flex;flex-direction:column;gap:.1rem;}',
      '.route-card-cta-main{font-size:.9rem;font-weight:900;}',
      '.route-card-cta-hint{font-size:.76rem;color:var(--t2,#56616f);font-weight:600;}',
      '.route-card-cta-go{flex:0 0 auto;color:var(--ac,#1f7a5a);font-weight:900;}',
      // the summary card supersedes the in-card CTA inside the drawer
      '#visaDrawerBody .route-card-cta{display:none;}',
      // mobile → bottom sheet
      '@media (max-width:640px){',
      '.route-guide-overlay{align-items:flex-end;padding:0;}',
      '.route-guide-box{max-width:none;max-height:92vh;border-radius:18px 18px 0 0;border-bottom:none;}',
      '}'
    ].join('\n');
    var style = document.createElement('style');
    style.id = 'routeGuideStyles';
    style.textContent = css;
    document.head.appendChild(style);
  }

  /* ------------------------------------------------------- overlay scaffold */
  function ensureOverlay() {
    var existing = document.getElementById(OVERLAY_ID);
    if (existing) return existing;
    injectStyles();
    var overlay = document.createElement('div');
    overlay.id = OVERLAY_ID;
    overlay.className = 'route-guide-overlay';
    overlay.setAttribute('role', 'dialog');
    overlay.setAttribute('aria-modal', 'true');
    overlay.setAttribute('aria-hidden', 'true');
    overlay.setAttribute('aria-label', S('flowAria'));
    overlay.innerHTML =
      '<div class="route-guide-box" role="document">' +
        '<div class="route-guide-head">' +
          '<div class="route-guide-head-main">' +
            '<div class="route-guide-eyebrow" data-rg="eyebrow"></div>' +
            '<h2 class="route-guide-title" id="routeGuideTitle" data-rg="title"></h2>' +
          '</div>' +
          '<button type="button" class="route-guide-close" data-rg="close" aria-label="' + esc(S('close')) + '">✕</button>' +
        '</div>' +
        '<p class="route-guide-intro" data-rg="intro"></p>' +
        '<div class="route-guide-body" data-rg="body"></div>' +
      '</div>';
    document.body.appendChild(overlay);
    overlay.setAttribute('aria-labelledby', 'routeGuideTitle');
    overlay.addEventListener('click', function (e) {
      if (e.target === overlay) closeFlow();
    });
    overlay.querySelector('[data-rg="close"]').addEventListener('click', closeFlow);
    return overlay;
  }
  function isOverlayOpen() {
    var o = document.getElementById(OVERLAY_ID);
    return !!(o && o.classList.contains('active'));
  }
  function openOverlay() {
    var o = ensureOverlay();
    if (o.classList.contains('active')) return o;
    if (typeof openModal === 'function') openModal(OVERLAY_ID);
    else { o.classList.add('active'); o.setAttribute('aria-hidden', 'false'); }
    return o;
  }
  function closeFlow() {
    flow = null;
    var o = document.getElementById(OVERLAY_ID);
    if (!o) return;
    if (typeof closeModal === 'function') closeModal(OVERLAY_ID);
    else { o.classList.remove('active'); o.setAttribute('aria-hidden', 'true'); }
  }
  function setHead(eyebrow, title, intro) {
    var o = ensureOverlay();
    o.querySelector('[data-rg="eyebrow"]').textContent = eyebrow || '';
    o.querySelector('[data-rg="title"]').textContent = title || '';
    var introEl = o.querySelector('[data-rg="intro"]');
    introEl.textContent = intro || '';
    introEl.style.display = intro ? '' : 'none';
  }
  function bodyEl() { return ensureOverlay().querySelector('[data-rg="body"]'); }
  function focusFirst() {
    var o = document.getElementById(OVERLAY_ID);
    if (!o) return;
    var f = o.querySelector('.route-guide-body button, .route-guide-body [tabindex]');
    if (f) { try { f.focus(); } catch (e) { /* noop */ } }
  }

  /* --------------------------------------------------- status badge helper */
  function statusBadge(status) {
    var map = {
      available: ['is-available', S('statusAvailable')],
      conditional: ['is-conditional', S('statusConditional')],
      not_applicable: ['is-na', S('statusNotApplicable')],
      source_limited: ['is-limited', S('statusSourceLimited')]
    };
    var m = map[status] || map.source_limited;
    return '<span class="route-badge ' + m[0] + '">' + esc(m[1]) + '</span>';
  }

  /* ------------------------------------------------------ view: sub-codes */
  function renderSubcodeSelector(code) {
    var rec = findRecord(code);
    if (!rec) return false;
    var model = buildGuidanceModel(rec);
    if (!model.hasSubcodes) return renderProcedureSelector(code, '');
    flow = { code: rec.code, subcode: '', finder: null };
    setHead(rec.code + ' · ' + S('summaryEyebrow'),
      S('subcodeTitle', { code: rec.code, name: recDisplayName(rec) }),
      S('subcodeIntro'));
    var items = model.subcodes.map(function (s) {
      var who = s.userLabelKo || s.titleEn || '';
      var badges = '<span class="route-badge is-subcode">' + esc(S('badgeSubcode')) + '</span>';
      if (s.needsReview) badges += ' <span class="route-badge is-review">' + esc(S('badgeNeedsReview')) + '</span>';
      return '<button type="button" class="route-choice" data-rg-subcode="' + esc(s.code) + '">' +
        '<span class="route-choice-body">' +
          '<span class="route-choice-top"><span class="route-choice-code">' + esc(s.code) + '</span>' +
            '<span class="route-choice-name">' + esc(s.titleKo) + '</span> ' + badges + '</span>' +
          (who ? '<span class="route-choice-desc">' + esc(who) + '</span>' : '') +
          (s.titleEn && s.titleEn !== who ? '<span class="route-choice-en">' + esc(s.titleEn) + '</span>' : '') +
        '</span><span class="route-choice-go" aria-hidden="true">→</span></button>';
    }).join('');
    var unsure = '';
    if (model.hasRouteFinder || model.subcodes.length > 1) {
      unsure = '<button type="button" class="route-choice route-unsure" data-rg-finder="1">' +
        '<span class="route-choice-body"><span class="route-choice-top"><span class="route-choice-name">' + esc(S('unsure')) + '</span></span>' +
        '<span class="route-choice-desc">' + esc(S('unsureHint')) + '</span></span>' +
        '<span class="route-choice-go" aria-hidden="true">?</span></button>';
    }
    var foot = '<div class="route-foot"><button type="button" class="route-textbtn" data-rg-all="1">' + esc(S('allProcedures')) + '</button></div>';
    bodyEl().innerHTML = '<div class="route-guide-list">' + items + unsure + '</div>' + foot;
    openOverlay();
    focusFirst();
    return true;
  }

  /* ----------------------------------------------------- view: procedures */
  // Availability shown to the user comes from the page's OWN rendered tabs
  // (the single source of truth produced by getProcedure) when we can render
  // the card; otherwise it falls back to the pure adapter model. Either way we
  // never fake content.
  function liveProcedureKeys(code) {
    ensureRendered(code);
    var card = document.querySelector('#rlist .vc[data-code="' + cssEsc(code) + '"]');
    if (!card) return null;
    var keys = {};
    card.querySelectorAll('.procedure-tab').forEach(function (t) {
      var k = t.getAttribute('data-procedure');
      if (k) keys[k] = t.disabled ? 'conditional' : 'available';
    });
    return keys;
  }
  function renderProcedureSelector(code, subcode) {
    var rec = findRecord(code);
    if (!rec) return false;
    var model = buildGuidanceModel(rec);
    flow = { code: rec.code, subcode: subcode || '', finder: null };
    var labelForTitle = subcode ? subcode : (rec.code + ' ' + recDisplayName(rec));
    setHead(rec.code + ' · ' + S('summaryEyebrow'), S('procTitle', { label: labelForTitle }), S('procIntro'));

    var live = liveProcedureKeys(code); // map camelKey → 'available'|'conditional' | null
    // Merge: live tabs are authoritative for availability; adapter supplies labels.
    var rows = PROCEDURE_ORDER.map(function (camel) {
      var liveStatus = live ? live[camel] : undefined;
      var st;
      if (live) st = liveStatus || procedureStatusForRecord(rec, camel) || null;
      else st = procedureStatusForRecord(rec, camel);
      if (!st) return null;
      if (live && liveStatus) st = liveStatus; // tab really exists
      return {
        camel: camel, snake: SNAKE_OF[camel], status: st,
        official: procOfficialLabel(camel), user: S('procUser_' + camel), explain: S('procExplain_' + camel)
      };
    }).filter(Boolean);

    // Always-meaningful: 방문예약/관할 확인 (handled via HiKorea helper).
    rows.push({ camel: 'visitReservation', snake: 'visit_reservation', status: 'available',
      official: S('procUser_visitReservation'), user: S('procUser_visitReservation'), explain: S('procExplain_visitReservation'), special: 'visit' });

    var sourceLimited = rows.filter(function (r) { return r.status === 'available'; }).length === 0;
    var items = rows.map(function (r) {
      var disabled = (r.status === 'not_applicable');
      var muted = disabled || r.status === 'source_limited' ? ' is-muted' : '';
      return '<button type="button" class="route-choice' + muted + '"' + (disabled ? ' disabled aria-disabled="true"' : '') +
        ' data-rg-proc="' + esc(r.snake) + '" data-rg-proc-camel="' + esc(r.camel) + '"' + (r.special ? ' data-rg-special="' + esc(r.special) + '"' : '') + '>' +
        '<span class="route-choice-body">' +
          '<span class="route-choice-top"><span class="route-choice-name">' + esc(r.user) + '</span> ' + statusBadge(r.status) + '</span>' +
          '<span class="route-choice-sub">' + esc(r.official) + '</span>' +
          '<span class="route-choice-desc">' + esc(r.explain) + '</span>' +
        '</span>' + (disabled ? '' : '<span class="route-choice-go" aria-hidden="true">→</span>') + '</button>';
    }).join('');
    var note = sourceLimited ? '<div class="route-note">' + esc(S('sourceLimitedNote')) + '</div>' : '';
    var foot = '<div class="route-foot">';
    if (model.hasSubcodes) foot += '<button type="button" class="route-textbtn" data-rg-back-subcode="1">' + esc(S('back')) + '</button>';
    foot += '<button type="button" class="route-textbtn" data-rg-all="1">' + esc(S('allProcedures')) + '</button></div>';
    bodyEl().innerHTML = note + '<div class="route-guide-list">' + items + '</div>' + foot;
    openOverlay();
    focusFirst();
    return true;
  }

  /* --------------------------------------------------- view: route finder */
  function renderRouteFinder(code, qid, history) {
    var rec = findRecord(code);
    var cfg = rec ? ROUTE_FINDER[normCode(rec.code)] : null;
    if (!cfg) return renderSubcodeSelector(code); // no finder → fall back
    qid = qid || cfg.start;
    history = history || [];
    flow = { code: rec.code, subcode: '', finder: { qid: qid, history: history } };
    var q = cfg.questions[qid];
    setHead(rec.code + ' · ' + S('unsure'), S('subcodeTitle', { code: rec.code, name: recDisplayName(rec) }), '');
    var opts = (q.options || []).map(function (o) {
      var label = o.key === 'yes' ? S('yes') : (o.key === 'no' ? S('no') : pick(o.label));
      return '<button type="button" class="route-choice" data-rg-answer="' + esc(o.key) + '">' +
        '<span class="route-choice-body"><span class="route-choice-top"><span class="route-choice-name">' + esc(label) + '</span></span></span>' +
        '<span class="route-choice-go" aria-hidden="true">→</span></button>';
    }).join('');
    var foot = '<div class="route-foot">';
    foot += '<button type="button" class="route-textbtn" data-rg-finder-back="1">' + esc(S('back')) + '</button>';
    foot += '<button type="button" class="route-textbtn" data-rg-back-subcode="1">' + esc(S('finderPickManually')) + '</button></div>';
    bodyEl().innerHTML = '<p class="route-finder-q">' + esc(pick(q.text)) + '</p><div class="route-guide-list">' + opts + '</div>' + foot;
    openOverlay();
    focusFirst();
    return true;
  }
  function renderFinderResult(code, subcode) {
    var rec = findRecord(code);
    var sub = getSubcodes(rec).filter(function (s) { return normCode(s.code) === normCode(subcode); })[0];
    if (!sub) return renderSubcodeSelector(code);
    setHead(rec.code + ' · ' + S('unsure'), S('finderResultTitle'), S('finderResultLead'));
    var who = subcodeUserLabel(sub) || subcodeNameKo(sub);
    var card = '<button type="button" class="route-choice" data-rg-subcode="' + esc(sub.code) + '">' +
      '<span class="route-choice-body"><span class="route-choice-top">' +
      '<span class="route-choice-code">' + esc(sub.code) + '</span><span class="route-choice-name">' + esc(subcodeNameKo(sub)) + '</span> ' +
      '<span class="route-badge is-subcode">' + esc(S('badgeSubcode')) + '</span></span>' +
      (who ? '<span class="route-choice-desc">' + esc(who) + '</span>' : '') + '</span>' +
      '<span class="route-choice-go" aria-hidden="true">' + esc(S('seeResult')) + ' →</span></button>';
    var foot = '<div class="route-foot"><button type="button" class="route-textbtn" data-rg-finder-restart="1">' + esc(S('back')) + '</button>' +
      '<button type="button" class="route-textbtn" data-rg-back-subcode="1">' + esc(S('finderPickManually')) + '</button></div>';
    bodyEl().innerHTML = '<div class="route-guide-list">' + card + '</div>' + foot;
    openOverlay();
    focusFirst();
  }
  function renderFinderLowConfidence(code) {
    var rec = findRecord(code);
    setHead(rec.code + ' · ' + S('unsure'), S('finderLowTitle'), S('finderLowLead'));
    var model = buildGuidanceModel(rec);
    var items = model.subcodes.map(function (s) {
      var who = s.userLabelKo || s.titleEn || '';
      return '<button type="button" class="route-choice" data-rg-subcode="' + esc(s.code) + '">' +
        '<span class="route-choice-body"><span class="route-choice-top">' +
        '<span class="route-choice-code">' + esc(s.code) + '</span><span class="route-choice-name">' + esc(s.titleKo) + '</span></span>' +
        (who ? '<span class="route-choice-desc">' + esc(who) + '</span>' : '') + '</span>' +
        '<span class="route-choice-go" aria-hidden="true">→</span></button>';
    }).join('');
    var foot = '<div class="route-foot"><button type="button" class="route-textbtn" data-rg-finder-restart="1">' + esc(S('back')) + '</button></div>';
    bodyEl().innerHTML = '<div class="route-guide-list">' + items + '</div>' + foot;
    openOverlay();
    focusFirst();
  }

  /* ----------------------------------------------------------- navigation */
  function ensureRendered(code) {
    var sel = '#rlist .vc[data-code="' + cssEsc(code) + '"]';
    if (document.querySelector(sel)) return true;
    if (typeof renderResults !== 'function') return false;
    var q = document.getElementById('q');
    if (q) q.value = code;
    if (document.body.classList.contains('landing')) {
      document.body.classList.remove('landing', 'launching', 'anagram-run', 'searching');
      document.body.setAttribute('data-scene', 'searched');
      document.body.classList.add('searched');
    }
    try { renderResults(code); } catch (e) { return false; }
    return !!document.querySelector(sel);
  }
  function activateProcedure(cardEl, camel) {
    var tab = cardEl.querySelector('.procedure-tab[data-procedure="' + camel + '"]');
    if (!tab) return false;
    cardEl.querySelectorAll('.procedure-tab').forEach(function (t) {
      t.classList.toggle('active', t === tab);
      t.classList.remove('is-route-muted');
    });
    cardEl.querySelectorAll('.procedure-panel').forEach(function (p) {
      p.classList.toggle('active', p.getAttribute('data-procedure-panel') === camel);
    });
    return !tab.disabled;
  }
  function injectSummaryCard(cardEl, code, subcode, camel, snake) {
    var rec = findRecord(code);
    if (!rec || !cardEl) return;
    var host = cardEl.querySelector('.manual-layout') || cardEl.querySelector('.vc-c') || cardEl;
    var prev = host.querySelector('.route-summary-card');
    if (prev) prev.parentNode.removeChild(prev);

    var sub = subcode ? getSubcodes(rec).filter(function (s) { return normCode(s.code) === normCode(subcode); })[0] : null;
    var titleCode = sub ? sub.code : rec.code;
    var titleName = sub ? subcodeNameKo(sub) : visaNameKo(rec);
    var enName = sub ? (sub.nameEn || sub.name_en || sub.titleEn || '') : visaNameEn(rec);
    var who = sub ? (subcodeUserLabel(sub) || '') : '';

    var procLabel = '';
    var missing = false;
    if (snake === 'visit_reservation') {
      procLabel = S('procUser_visitReservation');
    } else if (camel) {
      procLabel = procOfficialLabel(camel);
      missing = !cardEl.querySelector('.procedure-tab[data-procedure="' + camel + '"]');
    }

    var card = document.createElement('section');
    card.className = 'route-summary-card';
    card.setAttribute('data-route-summary', '1');
    card.setAttribute('aria-label', S('summaryEyebrow'));
    var html =
      '<div class="route-summary-eyebrow">' + esc(S('summaryEyebrow')) + '</div>' +
      '<h3 class="route-summary-title">' + esc(titleCode) + (titleName ? ' · ' + esc(titleName) : '') + '</h3>' +
      (enName ? '<div class="route-summary-en">' + esc(enName) + '</div>' : '') +
      (!sub ? '<div class="route-summary-en">' + esc(S('summaryNoSubcode')) + '</div>' : '');
    var canJump = procLabel && !missing && camel;
    if (procLabel) {
      html += canJump
        ? '<button type="button" class="route-summary-proc is-jump" data-rg-summary="jump">' + esc(S('summaryProcedurePrefix')) + ': <b>' + esc(procLabel) + '</b> <span aria-hidden="true">↓</span></button>'
        : '<div class="route-summary-proc">' + esc(S('summaryProcedurePrefix')) + ': <b>' + esc(procLabel) + '</b></div>';
    }
    if (missing) {
      html += '<div class="route-summary-missing">' + esc(S('summaryProcedureMissing', { label: procLabel })) + '</div>';
    }
    var whoText = who || (sub ? '' : S('summaryWhoParent'));
    if (whoText) {
      html += '<div class="route-summary-who"><span class="route-summary-who-h">' + esc(S('summaryWho')) + '</span><br>' + esc(whoText) + '</div>';
    }
    html += '<div class="route-summary-actions">';
    if (getSubcodes(rec).length) html += '<button type="button" class="route-summary-btn" data-rg-summary="subcode">' + esc(S('changeSubcode')) + '</button>';
    html += '<button type="button" class="route-summary-btn" data-rg-summary="procedure">' + esc(S('changeProcedure')) + '</button>';
    html += '<button type="button" class="route-summary-btn" data-rg-summary="source">' + esc(S('sourceBtn')) + '</button>';
    if (typeof openAiModal === 'function') html += '<button type="button" class="route-summary-btn is-primary" data-rg-summary="waymaker">' + esc(S('waymakerBtn')) + '</button>';
    html += '</div>';
    card.innerHTML = html;
    host.insertBefore(card, host.firstChild);

    card.addEventListener('click', function (e) {
      var btn = e.target.closest('[data-rg-summary]');
      if (!btn) return;
      var act = btn.getAttribute('data-rg-summary');
      if (act === 'subcode') { ParadisoRoute.openSubcodeSelector(code); }
      else if (act === 'procedure') { ParadisoRoute.openProcedureSelector(code, subcode); }
      else if (act === 'source') {
        var d = cardEl.querySelector('.source-evidence-panel');
        if (d) { if ('open' in d) d.open = true; d.scrollIntoView({ behavior: 'smooth', block: 'center' }); }
        else { (cardEl.querySelector('.vc-caution') || cardEl).scrollIntoView({ behavior: 'smooth', block: 'center' }); }
      } else if (act === 'waymaker') {
        if (typeof openAiModal === 'function') {
          // If the user has already picked a scenario in the active procedure
          // panel, carry that selected variant into the AI handoff so the
          // prominent summary CTA matches the in-card scenario CTA. Otherwise
          // fall back to procedure-level context (unchanged behaviour).
          var sel = cardEl.querySelector('.procedure-panel.active [data-procedure-variant-selector][data-selected-variant]')
            || cardEl.querySelector('[data-procedure-variant-selector][data-selected-variant]');
          var selVarId = sel ? sel.getAttribute('data-selected-variant') : '';
          if (selVarId) {
            var selKey = sel.getAttribute('data-procedure-variant-selector') || '';
            var nameEl = sel.querySelector('.manual-subcode-card.is-selected .manual-subcode-name');
            var selLabel = nameEl ? (nameEl.textContent || '').trim() : '';
            openAiModal(code, selKey, selVarId, selLabel);
          } else {
            openAiModal(code, camel || '', '', procLabel || '');
          }
        }
      } else if (act === 'jump') {
        var panel = cardEl.querySelector('.procedure-panel.active') || (camel && cardEl.querySelector('.procedure-tab[data-procedure="' + camel + '"]'));
        if (panel) panel.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
    });
  }
  function scrollIntoDrawer(cardEl, inDrawer) {
    var target = cardEl.querySelector('.route-summary-card') || cardEl;
    try { target.scrollIntoView({ behavior: 'smooth', block: 'start' }); } catch (e) { /* noop */ }
  }
  function goToResult(code, subcode, snake, opts) {
    opts = opts || {};
    var rec = findRecord(code);
    if (!rec) { if (typeof showToast === 'function') showToast(S('errNoRecord')); return false; }
    closeFlow();
    if (!opts.fromPop) pushUrl({ code: rec.code, subcode: subcode || '', procedure: snake || '' });
    if (!ensureRendered(rec.code)) { if (typeof showToast === 'function') showToast(S('errNoRecord')); return false; }

    var cardEl = null, inDrawer = false;
    if (typeof openVisaDrawer === 'function' && openVisaDrawer(rec.code)) {
      cardEl = document.querySelector('#visaDrawerBody .vc');
      inDrawer = true;
    }
    if (!cardEl) {
      cardEl = document.querySelector('#rlist .vc[data-code="' + cssEsc(rec.code) + '"]');
      if (cardEl) cardEl.classList.add('open');
    }
    if (!cardEl) return false;

    var camel = (snake && snake !== 'visit_reservation') ? CAMEL_OF[snake] : '';
    if (camel) activateProcedure(cardEl, camel);
    injectSummaryCard(cardEl, rec.code, subcode, camel, snake);

    if (snake === 'visit_reservation') {
      if (typeof openHikoreaGuide === 'function') { try { openHikoreaGuide(rec.code); } catch (e) { /* noop */ } }
    }
    scrollIntoDrawer(cardEl, inDrawer);
    if (opts.warnings && opts.warnings.length && typeof showToast === 'function') showToast(S('invalidNotice'));
    return true;
  }

  /* --------------------------------------------------------------- URL I/O */
  function pushUrl(state, replace) {
    if (typeof history === 'undefined' || !history.pushState) return;
    var qs = serializeRouteState(state);
    var url = location.pathname + qs + location.hash;
    try {
      if (replace) history.replaceState({ paradisoRoute: state }, '', url);
      else history.pushState({ paradisoRoute: state }, '', url);
    } catch (e) { /* noop */ }
  }
  function clearUrl(replace) {
    if (typeof history === 'undefined' || !history.replaceState) return;
    var url = location.pathname + location.hash;
    try { history.replaceState({}, '', url); } catch (e) { /* noop */ }
  }
  function applyUrlState(fromPop) {
    var parsed = parseRouteState(location.search);
    if (!parsed.code) {
      if (fromPop) { closeFlow(); if (typeof closeVisaDrawer === 'function') closeVisaDrawer(); }
      return false;
    }
    var v = validateRouteState(parsed, allRecords());
    if (!v.state.code) { return false; }
    if (v.warnings.length) {
      // Drop invalid bits but keep going (graceful fallback to parent).
      pushUrl(v.state, true);
    }
    if (v.state.procedure) {
      return goToResult(v.state.code, v.state.subcode, v.state.procedure, { fromPop: true, warnings: v.warnings });
    }
    // No procedure in URL → open the appropriate selector.
    if (v.state.subcode) return ParadisoRoute.openProcedureSelector(v.state.code, v.state.subcode);
    return ParadisoRoute.start(v.state.code, { fromUrl: true });
  }

  /* ------------------------------------------------------- overlay events */
  function wireOverlayDelegation() {
    var o = ensureOverlay();
    if (o.getAttribute('data-rg-wired')) return;
    o.setAttribute('data-rg-wired', '1');
    o.addEventListener('click', function (e) {
      if (!flow) return;
      var code = flow.code;
      var t;
      if ((t = e.target.closest('[data-rg-subcode]'))) {
        renderProcedureSelector(code, t.getAttribute('data-rg-subcode'));
      } else if (e.target.closest('[data-rg-finder]')) {
        if (ROUTE_FINDER[normCode(code)]) renderRouteFinder(code, null, []);
        else renderFinderLowConfidence(code);
      } else if (e.target.closest('[data-rg-all]')) {
        goToResult(code, flow.subcode || '', '');
      } else if ((t = e.target.closest('[data-rg-proc]'))) {
        if (t.disabled) return;
        goToResult(code, flow.subcode || '', t.getAttribute('data-rg-proc'));
      } else if (e.target.closest('[data-rg-back-subcode]')) {
        renderSubcodeSelector(code);
      } else if ((t = e.target.closest('[data-rg-answer]'))) {
        handleFinderAnswer(code, t.getAttribute('data-rg-answer'));
      } else if (e.target.closest('[data-rg-finder-back]')) {
        var f = flow.finder || { history: [] };
        if (f.history && f.history.length) {
          var prev = f.history.slice(0, -1);
          var prevQ = f.history[f.history.length - 1];
          renderRouteFinder(code, prevQ, prev);
        } else { renderSubcodeSelector(code); }
      } else if (e.target.closest('[data-rg-finder-restart]')) {
        renderRouteFinder(code, null, []);
      }
    });
  }
  function handleFinderAnswer(code, optionKey) {
    var cfg = ROUTE_FINDER[normCode(code)];
    var f = (flow && flow.finder) || { qid: cfg.start, history: [] };
    var step = routeFinderNext(cfg, f.qid, optionKey);
    if (!step) return;
    if (step.subcode) { renderFinderResult(code, step.subcode); return; }
    if (step.official) { renderFinderLowConfidence(code); return; }
    if (step.next) { renderRouteFinder(code, step.next, (f.history || []).concat([f.qid])); }
  }

  /* ---------------------------------------- in-card CTA (results-rendered) */
  // Statuses with a dedicated ComplexStatusGuide recommended-start CTA at the top
  // of their card. The generic in-card CTA is suppressed for these to avoid
  // competing guide buttons (the dedicated modules still call back into this
  // module for their "view full detail" handoff).
  var COMPLEX_GUIDE_OWNED = ['F-4', 'F-6', 'G-1', 'E-7', 'F-5', 'D-2', 'D-4'];
  // Surfaces the guided flow at the top of every guidable result card so an
  // exact-code search (which renders the full card inline, with no compact
  // show-detail card) still gets the journey. Reuses the already-wired
  // data-action="show-detail" so it routes through ParadisoRoute.start.
  function injectCardCtas(detail) {
    // If the user searched a specific sub-code, that card's CTA jumps straight
    // to the procedure selector for that sub-code (skips the parent selector).
    var query = (detail && detail.query) || '';
    var queryResolved = query ? resolveCode(query) : { code: '', subcode: '' };
    var cards = document.querySelectorAll('#rlist .vc[data-code]');
    cards.forEach(function (card) {
      var code = card.getAttribute('data-code');
      if (!code) return;
      var resolved = resolveCode(code);
      if (!resolved.code || !isGuidable(findRecord(resolved.code))) return;
      // Statuses with a dedicated full-screen ComplexStatusGuide entry own their
      // single primary CTA (F-4 → f4-route-guide.js; F-6/G-1/E-7/F-5/D-2/D-4 →
      // complex-status-guide.js). Suppress the generic in-card CTA for them so it
      // never competes with the recommended-start CTA. This module still powers
      // those guides' "view full detail" handoff via ParadisoRoute.
      if (COMPLEX_GUIDE_OWNED.indexOf(resolved.code) !== -1) return;
      var host = card.querySelector('.external-guide-slot[data-guide-slot="' + (window.CSS && CSS.escape ? CSS.escape(code) : code) + '"]')
        || card.querySelector('.external-guide-slot')
        || card.querySelector('.manual-layout') || card.querySelector('.vc-c');
      if (!host) return;
      if (host.querySelector('.route-card-cta') || card.querySelector(':scope > .vc-cw .route-card-cta')) return;
      var model = buildGuidanceModel(findRecord(resolved.code));
      // Did the search target a direct sub-code of THIS card?
      var directSub = (queryResolved.code === resolved.code && queryResolved.subcode) ? queryResolved.subcode : '';
      var startCode = directSub || resolved.code;
      var main = (directSub || !model.hasSubcodes) ? S('cardCtaPlain') : S('cardCtaSubcoded');
      var btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'route-card-cta';
      btn.setAttribute('data-action', 'show-detail');
      btn.setAttribute('data-code', startCode);
      btn.setAttribute('aria-label', main);
      btn.innerHTML = '<span class="route-card-cta-ico" aria-hidden="true">→</span>' +
        '<span class="route-card-cta-tx"><span class="route-card-cta-main">' + esc(main) + '</span>' +
        '<span class="route-card-cta-hint">' + esc(S('cardCtaHint')) + '</span></span>' +
        '<span class="route-card-cta-go" aria-hidden="true">›</span>';
      // Insert at the very top of the slot so it reads before the document wall.
      if (host.classList.contains('external-guide-slot')) host.appendChild(btn);
      else host.insertBefore(btn, host.firstChild);
    });
  }

  /* ----------------------------------------------------------- public API */
  function isGuidable(rec) {
    if (!rec) return false;
    if (['faq', 'scn', 'nhis'].indexOf(rec.cat) !== -1) return false;
    var hasProc = rec.procedures && Object.keys(rec.procedures).length > 0;
    return !!(hasProc || getSubcodes(rec).length);
  }
  var ParadisoRoute = {
    // --- pure (also used by Node tests) ---
    buildGuidanceModel: buildGuidanceModel,
    procedureStatusForRecord: procedureStatusForRecord,
    parseRouteState: parseRouteState,
    serializeRouteState: serializeRouteState,
    validateRouteState: validateRouteState,
    resolveCode: resolveCode,
    routeFinderNext: routeFinderNext,
    normCode: normCode,
    CAMEL_OF: CAMEL_OF,
    SNAKE_OF: SNAKE_OF,
    APPROVED_PROCEDURES: APPROVED_PROCEDURES,
    ROUTE_FINDER: ROUTE_FINDER,
    STR: STR,
    // --- browser flow ---
    canHandle: function (code) {
      var r = resolveCode(code);
      return !!(r.code && isGuidable(findRecord(r.code)));
    },
    start: function (code, opts) {
      opts = opts || {};
      var resolved = resolveCode(code);
      if (!resolved.code) return false;
      var rec = findRecord(resolved.code);
      if (!isGuidable(rec)) return false;
      wireOverlayDelegation();
      if (resolved.subcode) return this.openProcedureSelector(rec.code, resolved.subcode);
      var model = buildGuidanceModel(rec);
      if (model.hasSubcodes) return renderSubcodeSelector(rec.code);
      return this.openProcedureSelector(rec.code, '');
    },
    openSubcodeSelector: function (code) {
      var r = resolveCode(code);
      if (!r.code) return false;
      wireOverlayDelegation();
      return renderSubcodeSelector(r.code);
    },
    openProcedureSelector: function (code, subcode) {
      var r = resolveCode(code);
      if (!r.code) return false;
      wireOverlayDelegation();
      return renderProcedureSelector(r.code, subcode || r.subcode || '');
    },
    openRouteFinder: function (code) {
      var r = resolveCode(code);
      if (!r.code) return false;
      wireOverlayDelegation();
      if (ROUTE_FINDER[normCode(r.code)]) return renderRouteFinder(r.code, null, []);
      return renderFinderLowConfidence(r.code);
    },
    goToResult: function (code, subcode, procedure, opts) { return goToResult(code, subcode, procedure, opts); },
    close: closeFlow
  };
  window.ParadisoRoute = ParadisoRoute;

  /* ----------------------------------------------------------------- init */
  function init() {
    wireOverlayDelegation();
    // Re-render an open overlay + summary card on language change.
    document.addEventListener('paradiso-language-applied', function () {
      if (flow && isOverlayOpen()) {
        if (flow.finder) renderRouteFinder(flow.code, flow.finder.qid, flow.finder.history);
        else if (flow.subcode) renderProcedureSelector(flow.code, flow.subcode);
        else renderSubcodeSelector(flow.code);
      }
    });
    // Close the flow when the app resets to the landing scene.
    document.addEventListener('paradiso:landing-reset', function () { closeFlow(); });
    // Surface the guided-flow CTA on every guidable result card.
    document.addEventListener('paradiso:results-rendered', function (e) {
      try { injectCardCtas(e && e.detail); } catch (err) { /* non-fatal */ }
    });
    // Browser back/forward.
    window.addEventListener('popstate', function () {
      if (applyingPop) return;
      applyingPop = true;
      try { applyUrlState(true); } finally { applyingPop = false; }
    });
    // Deep link on load once data is ready.
    var parsed = parseRouteState(location.search);
    if (parsed.code) {
      var tries = 0;
      var timer = setInterval(function () {
        tries++;
        var ready = (typeof dataReady !== 'undefined' && dataReady) && allRecords().length;
        if (ready) { clearInterval(timer); applyUrlState(false); }
        else if (tries > 80) { clearInterval(timer); } // ~12s safety cap
      }, 150);
    }
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();

  if (typeof module !== 'undefined' && module.exports) {
    module.exports = ParadisoRoute;
  }
})();
