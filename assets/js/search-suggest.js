/* ============================================================================
 * Visable — home search suggestions (deterministic, local, no network per key)
 * ----------------------------------------------------------------------------
 * suggest(query, index) turns what the user is typing into a short ranked list
 * of things the existing search already resolves:
 *
 *   status        a 체류자격 code (E-7)                 → searches the code
 *   substatus     a subcode, always shown under its parent (E-7-1 under E-7)
 *   status_procedure  code × procedure (F-6 체류기간 연장)
 *   procedure     a procedure on its own (체류지 변경 신고)
 *   tool          an existing page or dialog (Form Helper, visit reservations…)
 *
 * The interpretation is VisableStatusGuidance.interpret() — the same reader the
 * results page uses — over data/search-suggest-index.json, which is derived from
 * the canonical guidance bundle (scripts/build_search_suggest_index.mjs). Nothing
 * here invents a code, a name or a procedure: rows are built from index entries
 * only, and every row that searches is re-interpreted before it is offered, so a
 * suggestion can never lead to a different reading than its label promises.
 *
 * Ranking is a plain score with stable tie-breaks (insertion order follows the
 * natural code order):
 *   1000 the whole query is a status code        950 a code typed in a longer query
 *    990 the whole query is a subcode             900 code × procedure both typed
 *    860+ a tool named outright (no status/procedure in the query; +strength of the match)
 *    760+ a tool next to a procedure typed without a code ("체류기간 만료 알림")
 *    800/750 a procedure on its own (status-independent / status needed)
 *    650 a status reached through an alias         600 code × likely procedure
 *    500 subcodes / codes continuing the typed prefix
 *    450 alias candidates       400 name matches       300+ tools alongside a code
 *
 * Pure: no DOM. Exposed on globalThis.VisableSearchSuggest for Node tests.
 * ========================================================================== */
(function (root) {
  'use strict';

  var PROCEDURE_ORDER = ['extension', 'status_change', 'registration', 'workplace_change', 'part_time_work', 'activities_outside_status', 'reentry', 'registration_info_report', 'residence_report', 'card_reissue', 'status_grant', 'workplace_report', 'visa_issuance', 'visa_issuance_confirmation', 'electronic_visa', 'program_condition_change'];
  // States offered unprompted for a code the user typed alone. A procedure the user typed is
  // shown whatever its state: the guidance then explains a "not applicable" answer itself.
  var LIKELY_STATES = { SUPPORTED: 1, CONDITIONAL: 1, SOURCE_ONLY: 2 };
  var LISTABLE_KINDS = { status: true, substatus: true };

  /* Product navigation, not immigration content: each tool is an existing page or
   * an existing dialog on the home (index.html data-action handlers, the same
   * destinations as the "전체 도구" directory in civic-search.js). `terms` are
   * discovery words only — what people type when they look for the tool
   * ("벌금 계산" → the enforcement page, "제주 무사증 국가" → the short-stay
   * checker). They never become an answer: choosing the row opens the tool,
   * which owns its own sources and cautions. Order = tie-break order. */
  var TOOLS = [
    { id: 'forms', href: 'form-helper.html', label: 'paperwork', sub: 'paperworkSub', terms: ['통합신청서', '신청서', '서식', '양식', '서류 작성', '서류작성', 'application form', 'integrated application', 'form helper', 'forms', 'form', '申请书', '申请表'] },
    { id: 'reservation', action: 'open-hikorea-guide', label: 'reservation', sub: 'reservationSub', terms: ['방문예약', '방문 예약', '예약', '하이코리아', 'hikorea', 'hi korea', 'reservation', 'appointment', 'booking', '预约'] },
    { id: 'enforcement', href: 'enforcement.html', label: 'enforcement', sub: 'enforcementSub', terms: ['범칙금', '벌금', '과태료', '통고처분', '처벌', '사범', '불법체류', '불법 체류', '불체', '오버스테이', '초과체류', '초과 체류', '체류기간 초과', '체류 기간 초과', '체류기간을 넘', '강제퇴거', '강제 퇴거', '출국명령', '출국 명령', '보호명령', '입국금지', '입국 금지', '처분', '위반', 'overstay', 'overstayed', 'over stay', 'immigration fine', 'fines', 'penalty', 'penalties', 'violation', 'deportation', 'deported', 'enforcement', '罚款', '罚金', '非法滞留', '逾期滞留', '驱逐出境'] },
    { id: 'short', action: 'open-short-stay', label: 'short', sub: 'shortSub', terms: ['무사증', '무비자', '비자 면제', '비자면제', '비자 없이', '비자없이', '사증면제', '사증 면제', '사증 없이', '단기입국', '단기 입국', '단기방문', '단기 방문', '단기체류', '단기 체류', '입국 경로', '입국경로', '입국 가능 국가', '입국가능국가', '관광비자', '관광 비자', '여행 비자', '전자여행허가', 'k-eta', 'keta', 'visa waiver', 'visa-free', 'visa free', 'visa exemption', 'without a visa', 'short stay', 'short-stay', 'short-term visit', 'tourist visa', 'travel to korea', 'entry route', '免签', '免签证', '无签证', 'miễn thị thực', 'bebas visa'] },
    { id: 'jobs', action: 'open-jobcode-modal', label: 'jobs', sub: 'jobsSub', terms: ['직종코드', '직종 코드', '직업코드', '직업 코드', '직업분류', '직업 분류', '산업분류', '산업 분류', '업종코드', '업종 코드', '직종', '업종', '취업정보 신고', '취업 정보 신고', '고용정보 신고', 'job code', 'occupation code', 'occupational code', 'industry code', 'ksco', 'ksic', '职业代码', '行业代码'] },
    { id: 'reminders', action: 'reveal-home-section', target: 'reminderSection', label: 'reminders', sub: 'remindersSub', terms: ['만료일', '만료 날짜', '만료 알림', '만료일 계산', '기한 계산', '기한계산', '날짜 계산', '날짜계산', '체류기간 계산', '며칠 남', '디데이', 'd-day', '알림', '리마인더', 'reminder', 'reminders', 'expiry date', 'expiration date', 'days left', 'deadline calculator', '到期提醒', '到期日'] },
    { id: 'office', action: 'open-jurisdiction-modal', label: 'office', sub: 'officeSub', terms: ['관할', '출입국관서', '출입국 관서', '출입국사무소', '출입국 사무소', '출입국외국인청', '출입국·외국인청', '출입국 외국인청', '외국인관서', '출입국 위치', '출입국 주소', 'immigration office', 'jurisdiction', 'which office', '出入境管理局', '出入境事务所'] },
    { id: 'agencies', action: 'open-agent-finder', label: 'agencies', sub: 'agenciesSub', terms: ['행정사', '대행기관', '대행 기관', '민원대행', '민원 대행', '신청 대행', '대행', 'agency', 'agencies', 'immigration agent', 'representative', '代办', '行政士'] },
    { id: 'hospitals', action: 'open-med-finder', label: 'hospitals', sub: 'hospitalsSub', terms: ['지정병원', '지정 병원', '병원', '의료기관', '건강진단', '건강 진단', '건강검진', '건강 검진', '신체검사', '결핵', '마약검사', '마약 검사', 'hospital', 'hospitals', 'medical check', 'health check', 'health certificate', 'tb test', 'tuberculosis', '医院', '体检'] },
    { id: 'checklists', href: 'immigration-checklists.html', label: 'checklists', sub: 'checklistsSub', terms: ['준비서류', '준비 서류', '필요서류', '필요 서류', '구비서류', '구비 서류', '제출서류', '제출 서류', '서류 목록', '체크리스트', 'checklist', 'checklists', 'required documents', 'document list', 'documents checklist', '材料清单'] },
    { id: 'pathways', action: 'reveal-home-section', target: 'pathwaySection', label: 'pathways', sub: 'pathwaysSub', terms: ['생활 경로', '생활경로', '체류 경로', '정착 경로', '진로', 'life pathway', 'pathway', 'pathways'] },
    { id: 'browse', action: 'reveal-home-section', target: 'visaManualSection', label: 'browse', sub: 'browseSub', terms: ['목적별', '둘러보기', '비자 종류', '비자종류', '체류자격 종류', '체류자격 목록', '비자 목록', '전체 비자', 'visa types', 'types of visa', 'all visas', 'browse'] },
    { id: 'reader', href: 'manual.html', label: 'reader', sub: 'readerSub', terms: ['매뉴얼', '원문 읽기', '원문읽기', '매뉴얼 원문', 'manual', 'manuals', 'read the manual'] },
    { id: 'newhome', href: 'new-home.html', label: 'newHome', sub: 'newHomeSub', terms: ['귀화', '국적취득', '국적 취득', '국적회복', '국적 회복', '국적', '귀화시험', '귀화 면접', 'naturalization', 'naturalisation', 'citizenship', '入籍', '归化'] },
    { id: 'waymaker', href: 'ai.html', label: 'waymaker', sub: 'waymakerSub', terms: ['waymaker', '웨이메이커', 'ai 상담', 'ai 안내'] }
  ];
  /* Discovery words in the other UI languages (zh-CN with common zh-TW forms, ja, vi, tl, id,
   * ru, fr, es, ar, de, tr, uk). Same rule as above: words people type to look for the tool,
   * never immigration content. Scripts without Latin letters match as substrings, Latin words
   * as whole words (so plurals are listed). Bare "nationality" words are left out on purpose:
   * they also appear in short-stay questions ("visa-free for my nationality"). */
  var TERMS_I18N = {
    forms: ['申请书', '申請書', '申请表', '申請表', '填写表格', '統合申請書', '書類作成', 'đơn đăng ký', 'mẫu đơn', 'điền đơn', 'pormularyo', 'form ng aplikasyon', 'formulir', 'formulir permohonan', 'isi formulir', 'анкета', 'бланк заявления', 'форма заявления', 'formulaire', 'formulaires', 'formulaire de demande', 'formulario', 'formularios', 'formulario de solicitud', 'استمارة', 'نموذج طلب', 'formular', 'formulare', 'antragsformular', 'başvuru formu', 'form doldurma', 'dilekçe', 'анкета', 'бланк заяви', 'форма заяви'],
    reservation: ['预约', '預約', '网上预约', '予約', '来庁予約', 'ハイコリア', 'đặt lịch', 'đặt hẹn', 'hẹn lịch', 'mag-book', 'magpa-appointment', 'reservasi', 'janji temu', 'запись на прием', 'записаться', 'бронирование', 'rendez-vous', 'réservation', 'prendre rendez-vous', 'cita', 'cita previa', 'reserva', 'حجز موعد', 'موعد', 'termin', 'terminbuchung', 'termin buchen', 'randevu', 'randevusu', 'randevu al', 'rezervasyon', 'запис на прийом', 'записатися', 'бронювання'],
    enforcement: ['罚款', '罰款', '罚金', '罰金', '非法滞留', '非法滯留', '逾期滞留', '逾期滯留', '逾期居留', '黑户', '驱逐出境', '驅逐出境', '强制出境', '強制出境', '违法', '違法', '反則金', '過料', '不法滞在', 'オーバーステイ', '超過滞在', '退去強制', '強制送還', '出国命令', '違反', 'tiền phạt', 'nộp phạt', 'bị phạt', 'phạt tiền', 'quá hạn visa', 'cư trú bất hợp pháp', 'ở lậu', 'trục xuất', 'vi phạm', 'multa', 'multas', 'deportasyon', 'paglabag', 'denda', 'tinggal ilegal', 'deportasi', 'pelanggaran', 'sanksi', 'штраф', 'нелегальн', 'просрочка визы', 'просрочил визу', 'просроченная виза', 'депортац', 'выдворен', 'нарушени', 'amende', 'amendes', 'séjour irrégulier', 'sans papiers', 'dépassement de séjour', 'expulsion', 'infraction', 'sanction', 'sanción', 'estancia irregular', 'situación irregular', 'sin papeles', 'deportación', 'expulsión', 'infracción', 'غرامة', 'مخالفة', 'إقامة غير قانونية', 'تجاوز مدة الإقامة', 'ترحيل', 'geldstrafe', 'bußgeld', 'strafe', 'illegaler aufenthalt', 'abschiebung', 'ausweisung', 'verstoß', 'ceza', 'cezası', 'cezasi', 'para cezası', 'vize cezası', 'cezalar', 'kaçak', 'vize ihlali', 'sınır dışı', 'ihlal', 'нелегальн', 'прострочена віза', 'прострочив візу', 'депортац', 'видворен', 'порушен'],
    short: ['免簽', '免簽證', '无签证', '無簽證', '济州免签', '濟州免簽', '短期访问', '短期訪問', '入境途径', '电子旅行许可', '電子旅行許可', 'ビザなし', 'ビザ免除', '査証免除', 'ノービザ', '短期滞在', '短期訪問', 'miễn visa', 'không cần visa', 'du lịch hàn quốc', 'nhập cảnh ngắn hạn', 'visa du lịch', 'walang visa', 'turista visa', 'tanpa visa', 'visa turis', 'kunjungan singkat', 'без визы', 'безвиз', 'туристическая виза', 'краткосрочн', 'электронное разрешение на въезд', 'sans visa', 'exemption de visa', 'visa touristique', 'court séjour', 'sin visa', 'sin visado', 'exención de visa', 'exención de visado', 'visa de turista', 'estancia corta', 'بدون تأشيرة', 'إعفاء من التأشيرة', 'تأشيرة سياحية', 'إقامة قصيرة', 'visumfrei', 'ohne visum', 'visumbefreiung', 'touristenvisum', 'kurzaufenthalt', 'vizesiz', 'vize muafiyeti', 'turist vizesi', 'kısa süreli', 'без візи', 'безвіз', 'туристична віза', 'короткостроков'],
    jobs: ['职业代码', '職業代碼', '行业代码', '行業代碼', '职业分类', '職業分類', '职种代码', '職業コード', '職種コード', '業種コード', 'mã nghề', 'mã ngành', 'mã nghề nghiệp', 'code ng trabaho', 'kode pekerjaan', 'kode jabatan', 'kode industri', 'код профессии', 'код отрасли', 'классификатор профессий', 'code métier', 'code profession', "code d'activité", 'código de ocupación', 'código de profesión', 'código de actividad', 'رمز المهنة', 'رمز النشاط', 'تصنيف المهن', 'berufscode', 'berufsschlüssel', 'branchencode', 'meslek kodu', 'sektör kodu', 'код професії', 'код галузі'],
    reminders: ['到期日', '到期提醒', '期限计算', '期限計算', '提醒', '倒计时', '剩几天', '満了日', 'リマインダー', '期限通知', 'あと何日', 'ngày hết hạn', 'nhắc hạn', 'nhắc nhở', 'tính ngày', 'paalala', 'petsa ng pag-expire', 'pengingat', 'tanggal kedaluwarsa', 'hitung tanggal', 'sisa hari', 'напоминание', 'срок истечения', 'дата окончания', 'сколько дней', 'rappel', "date d'expiration", 'date limite', 'compte à rebours', 'recordatorio', 'fecha de vencimiento', 'fecha de caducidad', 'cuenta regresiva', 'تذكير', 'تاريخ الانتهاء', 'تنبيه', 'erinnerung', 'ablaufdatum', 'fristrechner', 'frist berechnen', 'hatırlatıcı', 'hatırlatma', 'bitiş tarihi', 'нагадування', 'дата закінчення', 'скільки днів'],
    office: ['管辖', '管轄', '出入境办公室', '移民局', '入管', '出入国在留管理', '出入国管理事務所', 'cục xuất nhập cảnh', 'văn phòng xuất nhập cảnh', 'sở xuất nhập cảnh', 'opisina ng immigration', 'kantor imigrasi', 'иммиграционная служба', 'миграционная служба', 'иммиграционный офис', 'миграционный офис', "bureau d'immigration", "bureau de l'immigration", "service d'immigration", 'oficina de inmigración', 'oficina de migración', 'oficina de extranjería', 'extranjería', 'مكتب الهجرة', 'دائرة الهجرة', 'مكتب الجوازات', 'ausländerbehörde', 'einwanderungsbehörde', 'immigrationsbehörde', 'göç idaresi', 'göç ofisi', 'göçmenlik bürosu', 'міграційна служба', 'імміграційна служба', 'міграційний офіс'],
    agencies: ['代辦', '行政书士', '行政書士', '代理机构', '代理機構', '中介', '代行', '申請代行', 'dịch vụ làm hồ sơ', 'đại lý', 'làm giấy tờ hộ', 'ahensya', 'ahente', 'agen', 'agensi', 'biro jasa', 'jasa pengurusan', 'агентство', 'посредник', 'представитель', 'agence', 'mandataire', 'représentant', 'intermédiaire', 'agencia', 'gestor', 'gestoría', 'representante', 'tramitador', 'وكالة', 'وكيل', 'معقب', 'agentur', 'vermittler', 'bevollmächtigter', 'visaagentur', 'ajans', 'vize danışmanı', 'temsilci', 'посередник', 'представник'],
    hospitals: ['醫院', '指定医院', '指定醫院', '體檢', '健康检查', '健康檢查', '结核', '結核', '病院', '指定病院', '医療機関', '健康診断', '麻薬検査', 'bệnh viện', 'khám sức khỏe', 'giấy khám sức khỏe', 'xét nghiệm lao', 'ospital', 'pagsusuri sa kalusugan', 'rumah sakit', 'pemeriksaan kesehatan', 'cek kesehatan', 'tes tbc', 'больниц', 'медосмотр', 'медицинский осмотр', 'медицинская справка', 'туберкулез', 'hôpital', 'hôpitaux', 'examen médical', 'certificat médical', 'tuberculose', 'hospitales', 'examen médico', 'certificado médico', 'tuberculosis', 'مستشفى', 'فحص طبي', 'شهادة صحية', 'فحص السل', 'krankenhaus', 'klinik', 'gesundheitszeugnis', 'ärztliche untersuchung', 'tuberkulose', 'hastane', 'hastanesi', 'hastaneler', 'sağlık raporu', 'sağlık kontrolü', 'tüberküloz', 'лікарн', 'медогляд', 'медична довідка', 'туберкульоз'],
    checklists: ['所需材料', '材料清單', '必备材料', '准备材料', '需要什么材料', '文件清单', '必要書類', '提出書類', '書類一覧', 'チェックリスト', 'giấy tờ cần thiết', 'hồ sơ cần chuẩn bị', 'danh sách giấy tờ', 'cần những giấy tờ gì', 'mga kailangang dokumento', 'listahan ng dokumento', 'dokumen yang diperlukan', 'daftar dokumen', 'persyaratan dokumen', 'berkas yang dibutuhkan', 'необходимые документы', 'список документов', 'перечень документов', 'какие документы', 'documents nécessaires', 'pièces justificatives', 'liste des documents', 'documents requis', 'documentos necesarios', 'documentos requeridos', 'lista de documentos', 'requisitos', 'المستندات المطلوبة', 'الوثائق المطلوبة', 'قائمة المستندات', 'erforderliche unterlagen', 'benötigte unterlagen', 'checkliste', 'gerekli belgeler', 'belge listesi', 'istenen evraklar', 'необхідні документи', 'список документів', 'перелік документів', 'які документи'],
    pathways: ['生活路径', '定居路径', '生活ルート', '定住ルート', 'lộ trình cư trú', 'lộ trình định cư', 'jalur menetap', 'путь к постоянному проживанию', "parcours d'installation", 'ruta de residencia', 'مسار الإقامة', 'aufenthaltsweg', 'yerleşim yolu', 'шлях до проживання'],
    browse: ['签证种类', '簽證種類', '签证类型', '簽證類型', '全部签证', 'ビザの種類', '在留資格一覧', 'ビザ一覧', 'các loại visa', 'loại thị thực', 'danh sách visa', 'mga uri ng visa', 'jenis visa', 'daftar visa', 'виды виз', 'типы виз', 'список виз', 'types de visa', 'liste des visas', 'tipos de visa', 'tipos de visado', 'lista de visas', 'أنواع التأشيرات', 'قائمة التأشيرات', 'visaarten', 'visumarten', 'vize türleri', 'vize çeşitleri', 'види віз', 'типи віз'],
    reader: ['手册', '手冊', 'マニュアル', 'sổ tay hướng dẫn', 'manwal', 'buku panduan', 'методичка', 'manuel', 'guide officiel', 'guía oficial', 'الدليل الرسمي', 'دليل الهجرة', 'handbuch', 'leitfaden', 'el kitabı', 'kılavuz', 'посібник'],
    newhome: ['歸化', '加入韩国国籍', '加入韓國國籍', '帰化', '国籍取得', 'nhập quốc tịch', 'naturalisasyon', 'pagkamamamayan', 'naturalisasi', 'kewarganegaraan indonesia', 'гражданство', 'натурализац', 'naturalisation', 'citoyenneté', 'naturalización', 'ciudadanía', 'التجنس', 'الحصول على الجنسية', 'einbürgerung', 'staatsbürgerschaft', 'vatandaşlık', 'vatandaşlığa geçiş', 'громадянство', 'натуралізац']
  };
  // Merged once: NFKC + lower case like the query, duplicates dropped (one word, one count).
  TOOLS.forEach(function (tool) {
    var seenTerm = {};
    tool.terms = tool.terms.concat(TERMS_I18N[tool.id] || []).map(function (term) {
      var t = String(term);
      if (typeof t.normalize === 'function') t = t.normalize('NFKC');
      return t.toLowerCase();
    }).filter(function (term) { if (seenTerm[term]) return false; seenTerm[term] = true; return true; });
  });

  // The only home sections a tool row may reveal (index.html reveal-home-section).
  var TOOL_TARGETS = { reminderSection: true, pathwaySection: true, visaManualSection: true };

  /* ------------------------------------------------------------ normalize -- */
  // Width, dash and space variants only. Code recognition itself stays in interpret().
  function normalize(text) {
    var s = String(text == null ? '' : text);
    if (typeof s.normalize === 'function') s = s.normalize('NFKC');
    return s.replace(/[‐‑‒–—―−﹣－]/g, '-').replace(/[​-‍﻿]/g, '').replace(/\s+/g, ' ').trim().slice(0, 300);
  }
  function lower(s) { return String(s || '').toLowerCase(); }
  function escapeRe(s) { return s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'); }
  function hasTerm(text, term) {
    var t = lower(term);
    if (!/[a-z]/.test(t)) return text.indexOf(t) >= 0;
    return new RegExp('(^|[^a-z])' + escapeRe(t) + '($|[^a-z])').test(text);
  }

  /* -------------------------------------------------------------- hydrate -- */
  // Lookups computed once per index: parents in natural order, subcodes per parent.
  function codeSortKey(code) {
    var p = String(code).split('-');
    var num = function (x) { var n = parseInt(x, 10); return isNaN(n) ? 999 : n; };
    return [p[0], num(p[1]), p.length > 2 ? num(p[2]) : -1, p.slice(2).join('-')];
  }
  function compareCodes(a, b) {
    var ka = codeSortKey(a), kb = codeSortKey(b);
    for (var i = 0; i < ka.length; i++) { if (ka[i] < kb[i]) return -1; if (ka[i] > kb[i]) return 1; }
    return 0;
  }
  function hydrate(index) {
    if (!index || index.__hydrated) return index;
    var parents = [], children = {};
    Object.keys(index.codes || {}).forEach(function (code) {
      var c = index.codes[code];
      if (!LISTABLE_KINDS[c.kind]) return;
      if (c.kind === 'status') parents.push(code);
      else if (c.parent) (children[c.parent] = children[c.parent] || []).push(code);
    });
    parents.sort(compareCodes);
    Object.keys(children).forEach(function (k) { children[k].sort(compareCodes); });
    var procedures = {};
    (index.procedures || []).forEach(function (p) { procedures[p.id] = p; });
    var registry = {};
    (index.procedure_registry || []).forEach(function (r) { registry[r.procedure] = r.context_requirement; });
    Object.defineProperty(index, '__hydrated', { value: { parents: parents, children: children, procedures: procedures, registry: registry }, enumerable: false });
    return index;
  }

  /* --------------------------------------------------------------- tools --- */
  // Every tool whose discovery words appear in the query, strongest first. Strength is the
  // length of the longest word that matched (capped), so "제주 무사증" beats a stray "예약";
  // ties keep TOOLS order. Pure and deterministic.
  function matchTools(rawQuery) {
    var text = lower(normalize(rawQuery));
    if (!text) return [];
    var hits = [];
    TOOLS.forEach(function (tool, order) {
      var best = 0, words = [];
      tool.terms.forEach(function (term) { if (hasTerm(text, term)) { words.push(term); if (term.length > best) best = term.length; } });
      if (!best) return;
      hits.push({ tool: tool, order: order, strength: Math.min(9, best) + Math.min(3, words.length - 1), words: words });
    });
    hits.sort(function (a, b) { return (b.strength - a.strength) || (a.order - b.order); });
    return hits;
  }
  function toolRow(hit, score) {
    var tool = hit.tool;
    return { kind: 'tool', tool: tool.id, href: tool.href || null, action: tool.action || null, target: tool.target || null, labelKey: tool.label, sub: [{ key: tool.sub }], match: 'tool', score: score };
  }

  /* ------------------------------------------------------------- labels --- */
  function codeName(index, code, lang) { var c = index.codes[code]; if (!c) return ''; return lang === 'ko' ? (c.name_ko || c.name_en) : (c.name_en || c.name_ko); }
  function procName(index, pid, lang) { var p = index.__hydrated.procedures[pid]; if (!p) return ''; return lang === 'ko' ? p.ko : (p.en || p.ko); }
  function statusLabel(index, code, lang) { var n = codeName(index, code, lang); return n ? code + ' ' + n : code; }
  function lifecycleNote(index, code) {
    var c = index.codes[code] || {};
    if (c.lifecycle === 'legacy_holders_only') return { key: 'lifecycleLegacy' };
    if (c.lifecycle === 'abolished') return { key: 'lifecycleAbolished' };
    if (c.lifecycle === 'unverified') return { key: 'lifecycleUnverified' };
    return null;
  }
  function domainNote(index, pid) { var p = index.__hydrated.procedures[pid]; return p ? { key: p.domain === 'visa' ? 'domainVisa' : 'domainStay' } : null; }
  function compact(list) { return list.filter(Boolean); }

  /* ------------------------------------------------------------ interpret -- */
  function interpreter(opts) {
    if (opts && typeof opts.interpret === 'function') return opts.interpret;
    var SG = root.VisableStatusGuidance;
    return SG && typeof SG.interpret === 'function' ? SG.interpret : null;
  }
  function blankInterp(q) { return { query: q, codes: [], unknownCodes: [], aliasCandidates: [], aliasQuestion: null, procedure: null, procedureCandidates: [], confidence: 'LOW', isQuestion: false }; }

  // A row that searches is offered only if searching its query reads back as the
  // same status and procedure (the guard against labels that promise more than
  // the search delivers, e.g. an English procedure name the keywords miss).
  function readsAs(interp, index, query, code, procedure) {
    var r;
    try { r = interp(query, index); } catch (e) { return false; }
    var got = r.codes && r.codes[0] ? r.codes[0].code : null;
    if ((code || null) !== got) return false;
    if (code && r.unknownCodes && r.unknownCodes.length) return false;
    return (procedure || null) === (r.procedure || null);
  }

  /* -------------------------------------------------------------- suggest -- */
  // The whole query is (the start of) a code: "E", "E-", "E-7", "e 7 1", "E-7-S". A word that merely
  // starts with A–H ("family", "english", "go") is not: the tail is only allowed after digits.
  var CODE_ONLY = /^([A-Ha-h])(?:\s?-\s?)?(?:(\d{1,2})(?:\s?-\s?|\s)?([0-9A-Za-z]{0,6}))?$/;
  // Code-shaped text the sources do not know: a dashed token anywhere ("XYZ-999 연장"), or a query that is
  // nothing but letters and numbers ("e 7 99"). Spaced forms inside a sentence ("I am 25") are not codes.
  var CODE_SHAPE = /(^|[^A-Za-z0-9])([A-Za-z]{1,3})\s?-\s?(\d{1,3})(?:\s?-\s?([0-9A-Za-z]{1,6}))?(?![A-Za-z0-9])/;
  var CODE_SHAPE_WHOLE = /^()([A-Za-z]{1,3})[\s-]+(\d{1,3})(?:[\s-]+([0-9A-Za-z]{1,6}))?$/;

  function suggest(rawQuery, index, opts) {
    opts = opts || {};
    var lang = opts.lang === 'ko' ? 'ko' : 'en';
    var limit = opts.limit || 7;
    var q = normalize(rawQuery);
    var out = { query: q, items: [], notes: [], interp: null };
    if (!q || !index || !index.codes) return out;
    hydrate(index);
    var H = index.__hydrated;
    var interp = interpreter(opts);
    var I = interp ? interp(q, index) : blankInterp(q);
    out.interp = I;
    var text = lower(q);
    var rows = [], seen = {};
    function add(row) {
      var key = row.kind + '|' + (row.query || row.href || (row.action + (row.target ? '#' + row.target : '')));
      if (seen[key]) { if (row.score > seen[key].score) seen[key].score = row.score; return; }
      if (row.query) {
        if (!interp || !readsAs(interp, index, row.query, row.code || null, row.procedure || null)) {
          // An English label the keywords do not read falls back to the Korean canonical label.
          if (row.queryKo && row.queryKo !== row.query && interp && readsAs(interp, index, row.queryKo, row.code || null, row.procedure || null)) row.query = row.queryKo;
          else return;
        }
      }
      delete row.queryKo;
      row.order = rows.length;
      seen[key] = row; rows.push(row);
    }
    function statusRow(code, score, match) {
      var c = index.codes[code];
      if (!c || !LISTABLE_KINDS[c.kind]) return;
      var sub = c.kind === 'substatus'
        ? { key: 'subOf', vars: { parent: statusLabel(index, c.parent, lang) } }
        : ((H.children[code] || []).length ? { key: 'statusSubs', vars: { n: (H.children[code] || []).length } } : { key: 'statusKind' });
      add({ kind: c.kind, code: code, label: statusLabel(index, code, lang), labelLang: lang, query: code, sub: compact([sub, lifecycleNote(index, code)]), match: match, score: score });
    }
    function comboRow(code, pid, score, match) {
      var c = index.codes[code];
      if (!c || !LISTABLE_KINDS[c.kind] || !H.procedures[pid]) return;
      var st = c.procedures && c.procedures[pid];
      if (!st) return;
      var subs = [domainNote(index, pid)];
      if (c.kind === 'substatus') subs.push({ key: 'subOf', vars: { parent: statusLabel(index, c.parent, lang) } });
      if (st.s === 'NOT_APPLICABLE') subs.push({ key: 'stateNotApplicable' });
      else if (st.s === 'GENERALLY_NOT_PERMITTED' || st.s === 'EXCEPTION_ONLY') subs.push({ key: 'stateRestricted' });
      add({ kind: 'status_procedure', code: code, procedure: pid, label: code + ' ' + procName(index, pid, lang), labelLang: lang, query: code + ' ' + procName(index, pid, lang), queryKo: code + ' ' + procName(index, pid, 'ko'), sub: compact(subs), match: match, score: score });
    }
    function procedureRow(pid, score, match) {
      if (!H.procedures[pid]) return;
      var req = H.registry[pid];
      var independent = req === 'STATUS_INDEPENDENT' || req === 'STATUS_OPTIONAL';
      add({ kind: 'procedure', procedure: pid, label: procName(index, pid, lang), labelLang: lang, query: procName(index, pid, lang), queryKo: procName(index, pid, 'ko'), sub: compact([domainNote(index, pid), { key: independent ? 'procAnyStatus' : 'procNeedsStatus' }]), match: match, score: score });
    }
    function likelyProcedures(code, n) {
      var c = index.codes[code];
      if (!c) return [];
      var ranked = PROCEDURE_ORDER.filter(function (pid) { var st = c.procedures && c.procedures[pid]; return st && LIKELY_STATES[st.s]; });
      ranked.sort(function (a, b) { return (LIKELY_STATES[c.procedures[a].s] - LIKELY_STATES[c.procedures[b].s]) || (PROCEDURE_ORDER.indexOf(a) - PROCEDURE_ORDER.indexOf(b)); });
      return ranked.slice(0, n);
    }

    var primary = I.codes && I.codes[0] ? I.codes[0] : null;
    var codeOnly = q.match(CODE_ONLY);
    var procedure = I.procedure || null;

    // 1. the code(s) the interpreter recognised
    if (primary && !primary.fromUnknown) {
      var whole = !!codeOnly && !procedure;
      var isSub = index.codes[primary.code] && index.codes[primary.code].kind === 'substatus';
      var score = primary.fromAlias ? 650 : (whole ? (isSub ? 990 : 1000) : 950);
      if (procedure) comboRow(primary.code, procedure, 900, 'strong');
      statusRow(primary.code, procedure ? 700 : score, primary.fromAlias ? 'alias' : (whole ? 'exact' : 'code'));
      if (!procedure) likelyProcedures(primary.code, 3).forEach(function (pid, i) { comboRow(primary.code, pid, 600 - i, 'likely'); });
    } else if (primary && primary.fromUnknown) {
      out.notes.push({ key: 'unknownCode', vars: { code: primary.fromUnknown } });
      statusRow(primary.code, 520, 'parent');
    }

    // 2. codes continuing what is typed: "E" → parents, "E-7" → its subcodes, "E-7-S" → E-7-S1, E-7-S2…
    if (codeOnly) {
      var letter = codeOnly[1].toUpperCase(), digits = codeOnly[2] || '', tail = (codeOnly[3] || '').toUpperCase();
      if (!digits) {
        H.parents.filter(function (code) { return code.charAt(0) === letter && (index.codes[code].lifecycle === 'active'); }).forEach(function (code, i) { statusRow(code, 500 - i, 'prefix'); });
      } else {
        var parent = letter + '-' + digits;
        if (index.codes[parent]) {
          (H.children[parent] || []).filter(function (code) {
            var c = index.codes[code];
            return c.lifecycle === 'active' && (!tail || code.slice(parent.length + 1).toUpperCase().indexOf(tail) === 0);
          }).forEach(function (code, i) { statusRow(code, 500 - i, 'prefix'); });
        }
        if (!tail) H.parents.filter(function (code) { return code !== parent && code.indexOf(parent) === 0 && index.codes[code].lifecycle === 'active'; }).forEach(function (code, i) { statusRow(code, 480 - i, 'prefix'); });
      }
    }

    // 3. procedures without a code
    if (!primary) {
      if (procedure) {
        var reg = H.registry[procedure];
        procedureRow(procedure, reg === 'STATUS_INDEPENDENT' || reg === 'STATUS_OPTIONAL' ? 800 : 750, 'procedure');
      }
      (I.procedureCandidates || []).forEach(function (pid, i) { if (pid !== procedure) procedureRow(pid, 700 - i, 'procedure_candidate'); });
      // alias groups (유학 → D-2 / D-4): each candidate, and with the procedure when one is typed
      (I.aliasCandidates || []).forEach(function (code, i) {
        if (procedure) comboRow(code, procedure, 550 - i, 'alias');
        statusRow(code, 450 - i, 'alias');
      });
    }

    // 4. names: "결혼이민" → F-6, "전문인력" → E-7-1 (only when the query is not just a code)
    if (!codeOnly && q.length >= 2) {
      var needle = text.replace(/[?？!.,]/g, '').trim();
      if (needle.length >= 2) {
        var hits = [];
        Object.keys(index.codes).forEach(function (code) {
          var c = index.codes[code];
          if (!LISTABLE_KINDS[c.kind] || c.lifecycle !== 'active') return;
          if (lower(c.name_ko).indexOf(needle) >= 0 || (needle.length >= 3 && lower(c.name_en).indexOf(needle) >= 0)) hits.push(code);
        });
        hits.sort(function (a, b) { var ka = index.codes[a].kind === 'status' ? 0 : 1, kb = index.codes[b].kind === 'status' ? 0 : 1; return (ka - kb) || compareCodes(a, b); });
        hits.slice(0, 4).forEach(function (code, i) { statusRow(code, 400 - i, 'name'); });
      }
    }

    // 5. tools — named outright (above everything but a typed code), next to a procedure the
    //    user typed without a code, or quietly alongside a code
    var bandTool = primary ? 300 : ((procedure || (I.aliasCandidates || []).length) ? 760 : 860);
    matchTools(q).forEach(function (hit) { add(toolRow(hit, bandTool + hit.strength)); });
    // a question or a long description: Waymaker explains the situation step by step
    if (!seen['tool|ai.html'] && (I.isQuestion || q.length >= 24)) {
      add({ kind: 'tool', tool: 'waymaker', href: 'ai.html', action: null, target: null, labelKey: 'waymaker', sub: [{ key: 'waymakerAsk' }], match: 'tool', score: 100 });
    }

    // 6. a code-shaped token the sources do not know ("XYZ-999") is said, never matched
    if (!primary && (I.unknownCodes || []).length) {
      out.notes.push({ key: 'notACode', vars: { code: I.unknownCodes[0] } });
    } else if (!primary) {
      var shape = q.match(CODE_SHAPE) || q.match(CODE_SHAPE_WHOLE);
      if (shape) out.notes.push({ key: 'notACode', vars: { code: (shape[2] + '-' + shape[3] + (shape[4] ? '-' + shape[4] : '')).toUpperCase() } });
    }

    rows.sort(function (a, b) { return (b.score - a.score) || (a.order - b.order); });
    out.items = rows.slice(0, limit).map(function (row, i) { row.rank = i; delete row.order; return row; });
    return out;
  }

  var api = { normalize: normalize, hydrate: hydrate, suggest: suggest, matchTools: matchTools, compareCodes: compareCodes, TOOLS: TOOLS, TOOL_TARGETS: TOOL_TARGETS, PROCEDURE_ORDER: PROCEDURE_ORDER };
  root.VisableSearchSuggest = api;
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
})(typeof globalThis !== 'undefined' ? globalThis : this);
