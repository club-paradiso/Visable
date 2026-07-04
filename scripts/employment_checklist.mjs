/*
 * employment_checklist.mjs
 * ----------------------------------------------------------------------------
 * Builds the guided checklist state for the 취업정보 신고용 직종·업종 찾기 feature
 * from a (PR #442) analyzer result + the user's current selections. Pure ES
 * module: runs in Node (tests) and in the browser (bridged onto
 * window.EmploymentChecklist by index.html). It performs NO I/O.
 *
 * Why this exists: the old UI showed a STATIC 3-item legend that never reflected
 * the analyzer result, selections, clarifications, or the "공식 코드 확인 필요"
 * state — so it could imply progress that wasn't real. This module is the single
 * source of truth for checklist state, with explicit, testable status rules.
 *
 * Hard rules (do not weaken):
 *   - "candidate found" is NOT "confirmed".
 *   - "공식 코드 확인 필요" (needs_confirmation) is NOT complete.
 *   - a pending clarification keeps 직종/업종 out of complete.
 *   - income stays pending until a user-selected bracket exists.
 *   - the HiKorea final check is NEVER complete inside Paradiso.
 *   - this feature never asserts a visa permits the work (no eligibility step).
 * ----------------------------------------------------------------------------
 */

export const CHECKLIST_SCHEMA = '2026-06-employment-checklist';

/**
 * Guided-flow state machine for the employment finder. Drives PROGRESSIVE
 * disclosure so only one major action shows at a time: after a search the user
 * sees the interpretation first; when a fork question is pending AND there are
 * candidates to gate, the candidate list is held behind the question until the
 * user answers, picks "잘 모르겠어요", or explicitly reveals it. Weak inputs (no
 * candidates) are never gated — their guided examples are the action.
 *
 * Returns: 'idle' | 'analyzing' | 'needs_clarification' | 'showing_candidates'.
 */
export function employmentFlowState(opts = {}) {
  if (opts.analyzing) return 'analyzing';
  const r = opts.analyzerResult;
  if (!r) return 'idle';
  const needsClar = !!r.clarificationRequired && !opts.clarificationAnswered;
  if (needsClar && opts.hasCandidates && !opts.candidatesRevealed) return 'needs_clarification';
  return 'showing_candidates';
}

// Status vocabulary. `text` is shown next to the icon so status is never
// conveyed by colour alone (accessibility).
export const STATUS = {
  pending: { ko: '아직 필요해요', en: 'Not yet', 'zh-CN': '还需要', ja: 'まだ必要です', vi: 'Chưa hoàn tất', tl: 'Hindi pa', id: 'Belum', ru: 'Ещё нужно', fr: 'Pas encore', es: 'Aún falta', ar: 'لا يزال مطلوبًا', de: 'Noch nicht', icon: '⬜', tr: "Henüz değil", uk: "Ще потрібно" },
  ready: { ko: '후보를 찾았어요', en: 'Candidate found', 'zh-CN': '已找到候选', ja: '候補が見つかりました', vi: 'Đã tìm thấy ứng viên', tl: 'May nahanap na kandidato', id: 'Kandidat ditemukan', ru: 'Найден кандидат', fr: 'Candidat trouvé', es: 'Candidato encontrado', ar: 'تم العثور على مرشح', de: 'Kandidat gefunden', icon: '🔵', tr: "Aday bulundu", uk: "Кандидата знайдено" },
  needs_confirmation: { ko: '확인이 필요해요', en: 'Quick check needed', 'zh-CN': '需要确认', ja: '確認が必要です', vi: 'Cần kiểm tra', tl: 'Kailangan ng mabilis na pagtsek', id: 'Perlu konfirmasi', ru: 'Нужна проверка', fr: 'Vérification requise', es: 'Requiere comprobación', ar: 'يلزم التحقق', de: 'Prüfung nötig', icon: '⚠️', tr: "Hızlı kontrol gerekli", uk: "Потрібна швидка перевірка" },
  complete: { ko: '선택했어요', en: 'Selected', 'zh-CN': '已选择', ja: '選択しました', vi: 'Đã chọn', tl: 'Napili na', id: 'Sudah dipilih', ru: 'Выбрано', fr: 'Sélectionné', es: 'Seleccionado', ar: 'تم الاختيار', de: 'Ausgewählt', icon: '✅', tr: "Seçildi", uk: "Вибрано" },
  blocked: { ko: '조금 더 알려주세요', en: 'Add a detail', 'zh-CN': '请再补充一点', ja: 'もう少し教えてください', vi: 'Cho thêm chi tiết', tl: 'Magdagdag ng detalye', id: 'Tambahkan detail', ru: 'Добавьте детали', fr: 'Ajoutez un détail', es: 'Añada un detalle', ar: 'أضف تفصيلًا', de: 'Detail ergänzen', icon: '✏️', tr: "Bir ayrıntı ekleyin", uk: "Додайте деталь" }
};

// All user-facing copy, keyed so tests can assert ko+en presence and so the
// renderer never hardcodes strings inline. (Dynamic analyzer copy in this feature
// follows the ko/en convention established in PR #442; every additional locale —
// zh-CN, ja, vi, tl, id, ru, fr, es, ar, de — falls back to ko when missing.)
export const CHECKLIST_COPY = {
  'step.occupation.label': { ko: '1단계 · 내가 하는 일 (직종)', en: 'Step 1 · Your work (occupation)', 'zh-CN': '第 1 步 · 我所做的工作（职业）', ja: 'ステップ1 · 私がする仕事（職種）', vi: 'Bước 1 · Công việc của bạn (nghề nghiệp)', tl: 'Hakbang 1 · Ang trabaho mo (occupation)', id: 'Langkah 1 · Pekerjaan Anda (jenis pekerjaan)', ru: 'Шаг 1 · Ваша работа (профессия)', fr: 'Étape 1 · Votre travail (profession)', es: 'Paso 1 · Su trabajo (ocupación)', ar: 'الخطوة 1 · العمل الذي تؤديه (المهنة)', de: 'Schritt 1 · Ihre Tätigkeit (Beruf)', tr: "1. adım · İşiniz (meslek)", uk: "Крок 1 · Ваша робота (професія)" },
  'step.occupation.plain': { ko: '내가 실제로 하는 일', en: 'What you actually do', 'zh-CN': '我实际所做的工作', ja: '実際に行う仕事', vi: 'Việc bạn thực sự làm', tl: 'Ang aktwal mong ginagawa', id: 'Apa yang sebenarnya Anda lakukan', ru: 'Что вы фактически делаете', fr: 'Ce que vous faites réellement', es: 'Lo que realmente hace', ar: 'ما تقوم به فعليًا', de: 'Was Sie tatsächlich tun', tr: "Gerçekte ne yaptığınız", uk: "Що ви фактично робите" },
  'step.industry.label': { ko: '2단계 · 회사/사업장이 하는 일 (업종)', en: 'Step 2 · Employer / business activity (industry)', 'zh-CN': '第 2 步 · 公司/营业场所所做的业务（行业）', ja: 'ステップ2 · 会社・事業所が行う事業（業種）', vi: 'Bước 2 · Hoạt động của công ty/cơ sở kinh doanh (ngành)', tl: 'Hakbang 2 · Aktibidad ng employer / negosyo (industriya)', id: 'Langkah 2 · Aktivitas perusahaan/tempat usaha (industri)', ru: 'Шаг 2 · Деятельность работодателя/предприятия (отрасль)', fr: 'Étape 2 · Activité de l\'employeur / de l\'établissement (secteur)', es: 'Paso 2 · Actividad del empleador / del negocio (sector)', ar: 'الخطوة 2 · نشاط الشركة/مكان العمل (القطاع)', de: 'Schritt 2 · Tätigkeit des Arbeitgebers / Betriebs (Branche)', tr: "2. adım · İşveren / işletme faaliyeti (sektör)", uk: "Крок 2 · Діяльність роботодавця / підприємства (галузь)" },
  'step.industry.plain': { ko: '회사·사업장이 하는 일', en: 'What your employer/business does', 'zh-CN': '公司·营业场所所做的业务', ja: '会社・事業所が行う事業', vi: 'Việc công ty/cơ sở kinh doanh làm', tl: 'Ang ginagawa ng employer/negosyo', id: 'Apa yang dilakukan perusahaan/tempat usaha', ru: 'Чем занимается работодатель/предприятие', fr: 'Ce que fait votre employeur/établissement', es: 'Lo que hace su empleador/negocio', ar: 'ما تقوم به الشركة/مكان العمل', de: 'Was Ihr Arbeitgeber/Betrieb tut', tr: "İşvereninizin/işletmenizin ne yaptığı", uk: "Чим займається ваш роботодавець/підприємство" },
  'step.income.label': { ko: '3단계 · 연간소득 구간', en: 'Step 3 · Annual income bracket', 'zh-CN': '第 3 步 · 年收入区间', ja: 'ステップ3 · 年間所得区分', vi: 'Bước 3 · Khoảng thu nhập hằng năm', tl: 'Hakbang 3 · Bracket ng taunang kita', id: 'Langkah 3 · Rentang penghasilan tahunan', ru: 'Шаг 3 · Диапазон годового дохода', fr: 'Étape 3 · Tranche de revenu annuel', es: 'Paso 3 · Tramo de ingresos anuales', ar: 'الخطوة 3 · شريحة الدخل السنوي', de: 'Schritt 3 · Jahreseinkommensstufe', tr: "3. adım · Yıllık gelir dilimi", uk: "Крок 3 · Діапазон річного доходу" },
  'step.income.plain': { ko: '하이코리아에서 선택할 소득 구간', en: 'Income bracket to pick on HiKorea', 'zh-CN': '在 HiKorea 选择的收入区间', ja: 'HiKoreaで選択する所得区分', vi: 'Khoảng thu nhập cần chọn trên HiKorea', tl: 'Income bracket na pipiliin sa HiKorea', id: 'Rentang penghasilan yang dipilih di HiKorea', ru: 'Диапазон дохода, выбираемый на HiKorea', fr: 'Tranche de revenu à choisir sur HiKorea', es: 'Tramo de ingresos a elegir en HiKorea', ar: 'شريحة الدخل التي تختارها في HiKorea', de: 'Auf HiKorea zu wählende Einkommensstufe', tr: "HiKorea'da seçilecek gelir dilimi", uk: "Діапазон доходу, який слід вибрати на HiKorea" },
  'step.hikorea.label': { ko: '4단계 · 하이코리아 최종 확인', en: 'Step 4 · Final HiKorea check', 'zh-CN': '第 4 步 · HiKorea 最终确认', ja: 'ステップ4 · HiKoreaでの最終確認', vi: 'Bước 4 · Xác nhận cuối cùng trên HiKorea', tl: 'Hakbang 4 · Huling pagtsek sa HiKorea', id: 'Langkah 4 · Konfirmasi akhir di HiKorea', ru: 'Шаг 4 · Финальная проверка на HiKorea', fr: 'Étape 4 · Vérification finale sur HiKorea', es: 'Paso 4 · Comprobación final en HiKorea', ar: 'الخطوة 4 · التحقق النهائي عبر HiKorea', de: 'Schritt 4 · Abschließende Prüfung auf HiKorea', tr: "4. adım · Son HiKorea kontrolü", uk: "Крок 4 · Фінальна перевірка на HiKorea" },
  'step.hikorea.plain': { ko: '최종 신고 전 확인할 것', en: 'Confirm before final submission', 'zh-CN': '最终申报前需确认的事项', ja: '最終申告の前に確認すること', vi: 'Cần xác nhận trước khi khai báo cuối cùng', tl: 'Tiyakin bago ang huling pagsumite', id: 'Periksa sebelum pelaporan akhir', ru: 'Проверьте перед окончательной подачей', fr: 'À confirmer avant la déclaration finale', es: 'Confirmar antes de la declaración final', ar: 'تأكّد قبل الإبلاغ النهائي', de: 'Vor der endgültigen Meldung bestätigen', tr: "Son gönderimden önce onaylayın", uk: "Підтвердьте перед остаточною подачею" },

  'reason.occupation.pending': { ko: '검색하면 ‘내가 하는 일’에 가까운 직종 후보를 찾아드려요.', en: 'Search and we\'ll find occupation candidates close to your work.', 'zh-CN': '搜索后，我们会为您找出与“我所做的工作”相近的职业候选。', ja: '検索すると、「私がする仕事」に近い職種候補をお探しします。', vi: 'Khi bạn tìm kiếm, chúng tôi sẽ tìm các ứng viên nghề nghiệp gần với công việc của bạn.', tl: 'Kapag naghanap ka, hahanapin namin ang mga kandidatong occupation na malapit sa trabaho mo.', id: 'Setelah Anda mencari, kami akan menemukan kandidat pekerjaan yang dekat dengan pekerjaan Anda.', ru: 'После поиска мы подберём кандидатов профессий, близких к вашей работе.', fr: 'Après votre recherche, nous trouverons des professions proches de votre travail.', es: 'Tras buscar, encontraremos ocupaciones cercanas a su trabajo.', ar: 'عند البحث سنجد لك مرشّحي مهن قريبة من عملك.', de: 'Nach der Suche finden wir Berufskandidaten, die Ihrer Tätigkeit nahekommen.', tr: "Arayın, işinize yakın meslek adayları bulalım.", uk: "Виконайте пошук — і ми підберемо кандидатів професій, близьких до вашої роботи." },
  'reason.occupation.ready': { ko: '직종 후보를 찾았어요. 내가 하는 일에 가까운 항목을 선택하세요.', en: 'Found occupation candidates — pick the one closest to your work.', 'zh-CN': '已找到职业候选。请选择与您所做工作最接近的项目。', ja: '職種候補が見つかりました。あなたの仕事に最も近い項目を選んでください。', vi: 'Đã tìm thấy ứng viên nghề nghiệp — hãy chọn mục gần nhất với công việc của bạn.', tl: 'May nahanap na kandidatong occupation — piliin ang pinakamalapit sa trabaho mo.', id: 'Kandidat pekerjaan ditemukan — pilih yang paling dekat dengan pekerjaan Anda.', ru: 'Найдены кандидаты профессий — выберите ближайший к вашей работе.', fr: 'Professions trouvées — choisissez celle qui correspond le mieux à votre travail.', es: 'Ocupaciones encontradas — elija la más cercana a su trabajo.', ar: 'تم العثور على مرشّحي مهن — اختر الأقرب إلى عملك.', de: 'Berufskandidaten gefunden — wählen Sie den, der Ihrer Tätigkeit am nächsten kommt.', tr: "Meslek adayları bulundu — işinize en yakın olanı seçin.", uk: "Знайдено кандидатів професій — виберіть найближчого до вашої роботи." },
  'reason.occupation.needs_confirmation': { ko: '한 가지만 더 확인하면 직종이 정확해져요. 아래 질문에 답해 주세요.', en: 'One more detail will pin down the occupation — answer the question below.', 'zh-CN': '再确认一点，职业就能更准确。请回答下面的问题。', ja: 'もう一つ確認すれば職種がより正確になります。下の質問にお答えください。', vi: 'Chỉ cần xác nhận thêm một điểm là nghề nghiệp sẽ chính xác hơn. Hãy trả lời câu hỏi bên dưới.', tl: 'Isa pang detalye ang magpapatumpak sa occupation — sagutin ang tanong sa ibaba.', id: 'Satu detail lagi akan memastikan pekerjaannya — jawab pertanyaan di bawah.', ru: 'Ещё одна деталь уточнит профессию — ответьте на вопрос ниже.', fr: 'Un détail de plus précisera la profession — répondez à la question ci-dessous.', es: 'Un detalle más precisará la ocupación — responda la pregunta de abajo.', ar: 'تفصيل إضافي واحد يحدّد المهنة بدقة — أجب عن السؤال أدناه.', de: 'Ein weiteres Detail bestimmt den Beruf — beantworten Sie die Frage unten.', tr: "Bir ayrıntı daha mesleği kesinleştirecek — aşağıdaki soruyu yanıtlayın.", uk: "Ще одна деталь уточнить професію — дайте відповідь на запитання нижче." },
  'reason.occupation.needs_code': { ko: '입력은 이해했지만 공식 직종 코드는 확인이 필요해요 (공식 코드 확인 필요).', en: 'Understood, but the official occupation code needs confirmation.', 'zh-CN': '已理解您的输入，但官方职业代码仍需确认（需确认官方代码）。', ja: '入力は理解しましたが、公式の職種コードは確認が必要です（公式コードの確認が必要）。', vi: 'Đã hiểu nội dung nhập, nhưng mã nghề nghiệp chính thức cần được xác nhận (cần xác nhận mã chính thức).', tl: 'Naintindihan ang input, ngunit kailangan pang kumpirmahin ang opisyal na occupation code (kailangan ng kumpirmasyon sa opisyal na code).', id: 'Masukan Anda dipahami, tetapi kode pekerjaan resmi masih perlu dikonfirmasi (perlu konfirmasi kode resmi).', ru: 'Ввод понят, но официальный код профессии требует подтверждения (требуется подтверждение официального кода).', fr: 'Entrée comprise, mais le code professionnel officiel doit être confirmé (confirmation du code officiel requise).', es: 'Entendimos su entrada, pero el código oficial de la ocupación necesita confirmación (se requiere confirmar el código oficial).', ar: 'فُهم الإدخال، لكن رمز المهنة الرسمي يحتاج إلى تأكيد (يلزم تأكيد الرمز الرسمي).', de: 'Eingabe verstanden, aber der offizielle Berufscode muss bestätigt werden (Bestätigung des offiziellen Codes erforderlich).', tr: "Girdiğiniz anlaşıldı, ancak resmi meslek kodunun onaylanması gerekiyor.", uk: "Ваш ввід зрозуміли, але офіційний код професії потребує підтвердження (потрібне підтвердження офіційного коду)." },
  'reason.occupation.complete': { ko: '직종 후보를 선택했어요. 최종값은 하이코리아에서 확인하세요.', en: 'Occupation selected — confirm the final value on HiKorea.', 'zh-CN': '已选择职业候选。最终值请在 HiKorea 确认。', ja: '職種候補を選択しました。最終的な値はHiKoreaで確認してください。', vi: 'Đã chọn ứng viên nghề nghiệp. Hãy xác nhận giá trị cuối cùng trên HiKorea.', tl: 'Napili na ang occupation — kumpirmahin ang huling halaga sa HiKorea.', id: 'Pekerjaan dipilih — konfirmasi nilai akhirnya di HiKorea.', ru: 'Профессия выбрана — подтвердите итоговое значение на HiKorea.', fr: 'Profession sélectionnée — confirmez la valeur finale sur HiKorea.', es: 'Ocupación seleccionada — confirme el valor final en HiKorea.', ar: 'تم اختيار المهنة — أكّد القيمة النهائية في HiKorea.', de: 'Beruf ausgewählt — bestätigen Sie den endgültigen Wert auf HiKorea.', tr: "Meslek seçildi — nihai değeri HiKorea'da onaylayın.", uk: "Професію вибрано — підтвердьте остаточне значення на HiKorea." },
  'reason.occupation.blocked': { ko: '조금 더 구체적으로 입력하면 직종 후보를 찾을 수 있어요 (하는 일/장소).', en: 'Add a bit more detail (task / place) to find occupation candidates.', 'zh-CN': '再输入得具体一些（工作内容/地点），即可找到职业候选。', ja: 'もう少し具体的に入力すると職種候補が見つかります（仕事内容・場所）。', vi: 'Hãy nhập cụ thể hơn một chút (công việc / địa điểm) để tìm ứng viên nghề nghiệp.', tl: 'Magdagdag ng kaunting detalye (gawain / lugar) para makahanap ng kandidatong occupation.', id: 'Tambahkan sedikit detail (tugas / tempat) untuk menemukan kandidat pekerjaan.', ru: 'Добавьте немного деталей (задача / место), чтобы найти кандидатов профессий.', fr: 'Ajoutez un peu de détail (tâche / lieu) pour trouver des professions.', es: 'Añada un poco más de detalle (tarea / lugar) para encontrar ocupaciones.', ar: 'أضف مزيدًا من التفاصيل (المهمة / المكان) للعثور على مرشّحي المهن.', de: 'Ergänzen Sie etwas Detail (Tätigkeit / Ort), um Berufskandidaten zu finden.', tr: "Meslek adaylarını bulmak için biraz daha ayrıntı ekleyin (görev / yer).", uk: "Додайте трохи більше деталей (завдання / місце), щоб знайти кандидатів професій." },

  'reason.industry.pending': { ko: '검색하면 회사·사업장이 하는 일에 가까운 업종 후보를 찾아드려요.', en: 'Search and we\'ll find industry candidates close to your employer\'s business.', 'zh-CN': '搜索后，我们会为您找出与公司·营业场所业务相近的行业候选。', ja: '検索すると、会社・事業所が行う事業に近い業種候補をお探しします。', vi: 'Khi bạn tìm kiếm, chúng tôi sẽ tìm các ứng viên ngành gần với hoạt động của công ty/cơ sở kinh doanh.', tl: 'Kapag naghanap ka, hahanapin namin ang mga kandidatong industriya na malapit sa negosyo ng employer mo.', id: 'Setelah Anda mencari, kami akan menemukan kandidat industri yang dekat dengan usaha perusahaan Anda.', ru: 'После поиска мы подберём кандидатов отраслей, близких к деятельности вашего работодателя.', fr: 'Après votre recherche, nous trouverons des secteurs proches de l\'activité de votre employeur.', es: 'Tras buscar, encontraremos sectores cercanos a la actividad de su empleador.', ar: 'عند البحث سنجد لك مرشّحي قطاعات قريبة من نشاط الشركة/مكان العمل.', de: 'Nach der Suche finden wir Branchenkandidaten, die der Tätigkeit Ihres Arbeitgebers nahekommen.', tr: "Arayın, işvereninizin faaliyetine yakın sektör adayları bulalım.", uk: "Виконайте пошук — і ми підберемо кандидатів галузей, близьких до діяльності вашого роботодавця." },
  'reason.industry.ready': { ko: '업종 후보를 찾았어요. 회사/사업장이 하는 일에 가까운 항목을 선택하세요.', en: 'Found industry candidates — pick the one closest to your employer\'s business.', 'zh-CN': '已找到行业候选。请选择与公司/营业场所业务最接近的项目。', ja: '業種候補が見つかりました。会社・事業所が行う事業に最も近い項目を選んでください。', vi: 'Đã tìm thấy ứng viên ngành — hãy chọn mục gần nhất với hoạt động của công ty/cơ sở kinh doanh.', tl: 'May nahanap na kandidatong industriya — piliin ang pinakamalapit sa negosyo ng employer mo.', id: 'Kandidat industri ditemukan — pilih yang paling dekat dengan usaha perusahaan Anda.', ru: 'Найдены кандидаты отраслей — выберите ближайший к деятельности работодателя.', fr: 'Secteurs trouvés — choisissez celui qui correspond le mieux à l\'activité de votre employeur.', es: 'Sectores encontrados — elija el más cercano a la actividad de su empleador.', ar: 'تم العثور على مرشّحي قطاعات — اختر الأقرب إلى نشاط الشركة/مكان العمل.', de: 'Branchenkandidaten gefunden — wählen Sie den, der der Tätigkeit Ihres Arbeitgebers am nächsten kommt.', tr: "Sektör adayları bulundu — işvereninizin faaliyetine en yakın olanı seçin.", uk: "Знайдено кандидатів галузей — виберіть найближчого до діяльності вашого роботодавця." },
  'reason.industry.needs_confirmation': { ko: '고용 형태(직접 고용/파견 등)에 따라 업종이 달라져요. 아래 질문에 답해 주세요.', en: 'Industry depends on the employment relationship — answer the question below.', 'zh-CN': '行业会因雇佣形态（直接雇佣/派遣等）而不同。请回答下面的问题。', ja: '雇用形態（直接雇用・派遣など）によって業種が変わります。下の質問にお答えください。', vi: 'Ngành thay đổi tùy theo hình thức tuyển dụng (thuê trực tiếp / phái cử, v.v.). Hãy trả lời câu hỏi bên dưới.', tl: 'Nag-iiba ang industriya depende sa relasyon ng pagtatrabaho (direktang pagkuha / dispatch, atbp.) — sagutin ang tanong sa ibaba.', id: 'Industri berbeda tergantung bentuk hubungan kerja (perekrutan langsung / penyaluran, dll.). Jawab pertanyaan di bawah.', ru: 'Отрасль зависит от формы занятости (прямой наём / аутстаффинг и т. п.) — ответьте на вопрос ниже.', fr: 'Le secteur dépend de la relation d\'emploi (emploi direct / intérim, etc.) — répondez à la question ci-dessous.', es: 'El sector depende de la relación laboral (contratación directa / cesión, etc.) — responda la pregunta de abajo.', ar: 'يختلف القطاع حسب شكل التوظيف (توظيف مباشر / إعارة، إلخ) — أجب عن السؤال أدناه.', de: 'Die Branche hängt vom Beschäftigungsverhältnis ab (Direktanstellung / Entsendung usw.) — beantworten Sie die Frage unten.', tr: "Sektör, istihdam ilişkisine bağlıdır — aşağıdaki soruyu yanıtlayın.", uk: "Галузь залежить від форми зайнятості (прямий найм / аутстафінг тощо) — дайте відповідь на запитання нижче." },
  'reason.industry.needs_code': { ko: '입력은 이해했지만 공식 업종 코드는 확인이 필요해요 (공식 코드 확인 필요).', en: 'Understood, but the official industry code needs confirmation.', 'zh-CN': '已理解您的输入，但官方行业代码仍需确认（需确认官方代码）。', ja: '入力は理解しましたが、公式の業種コードは確認が必要です（公式コードの確認が必要）。', vi: 'Đã hiểu nội dung nhập, nhưng mã ngành chính thức cần được xác nhận (cần xác nhận mã chính thức).', tl: 'Naintindihan ang input, ngunit kailangan pang kumpirmahin ang opisyal na industry code (kailangan ng kumpirmasyon sa opisyal na code).', id: 'Masukan Anda dipahami, tetapi kode industri resmi masih perlu dikonfirmasi (perlu konfirmasi kode resmi).', ru: 'Ввод понят, но официальный код отрасли требует подтверждения (требуется подтверждение официального кода).', fr: 'Entrée comprise, mais le code de secteur officiel doit être confirmé (confirmation du code officiel requise).', es: 'Entendimos su entrada, pero el código oficial del sector necesita confirmación (se requiere confirmar el código oficial).', ar: 'فُهم الإدخال، لكن رمز القطاع الرسمي يحتاج إلى تأكيد (يلزم تأكيد الرمز الرسمي).', de: 'Eingabe verstanden, aber der offizielle Branchencode muss bestätigt werden (Bestätigung des offiziellen Codes erforderlich).', tr: "Girdiğiniz anlaşıldı, ancak resmi sektör kodunun onaylanması gerekiyor.", uk: "Ваш ввід зрозуміли, але офіційний код галузі потребує підтвердження (потрібне підтвердження офіційного коду)." },
  'reason.industry.complete': { ko: '업종 후보를 선택했어요. 최종값은 하이코리아에서 확인하세요.', en: 'Industry selected — confirm the final value on HiKorea.', 'zh-CN': '已选择行业候选。最终值请在 HiKorea 确认。', ja: '業種候補を選択しました。最終的な値はHiKoreaで確認してください。', vi: 'Đã chọn ứng viên ngành. Hãy xác nhận giá trị cuối cùng trên HiKorea.', tl: 'Napili na ang industriya — kumpirmahin ang huling halaga sa HiKorea.', id: 'Industri dipilih — konfirmasi nilai akhirnya di HiKorea.', ru: 'Отрасль выбрана — подтвердите итоговое значение на HiKorea.', fr: 'Secteur sélectionné — confirmez la valeur finale sur HiKorea.', es: 'Sector seleccionado — confirme el valor final en HiKorea.', ar: 'تم اختيار القطاع — أكّد القيمة النهائية في HiKorea.', de: 'Branche ausgewählt — bestätigen Sie den endgültigen Wert auf HiKorea.', tr: "Sektör seçildi — nihai değeri HiKorea'da onaylayın.", uk: "Галузь вибрано — підтвердьте остаточне значення на HiKorea." },
  'reason.industry.blocked': { ko: '회사/사업장이 무슨 일을 하는지 적으면 업종 후보를 찾을 수 있어요.', en: 'Tell us what your employer/business does to find industry candidates.', 'zh-CN': '写明公司/营业场所做什么业务，即可找到行业候选。', ja: '会社・事業所が何をしているかを書くと業種候補が見つかります。', vi: 'Hãy ghi rõ công ty/cơ sở kinh doanh làm gì để tìm ứng viên ngành.', tl: 'Sabihin kung ano ang ginagawa ng employer/negosyo mo para makahanap ng kandidatong industriya.', id: 'Tuliskan apa yang dilakukan perusahaan/tempat usaha untuk menemukan kandidat industri.', ru: 'Укажите, чем занимается ваш работодатель/предприятие, чтобы найти кандидатов отраслей.', fr: 'Indiquez ce que fait votre employeur/établissement pour trouver des secteurs.', es: 'Indique qué hace su empleador/negocio para encontrar sectores.', ar: 'اكتب ما تقوم به الشركة/مكان العمل للعثور على مرشّحي القطاعات.', de: 'Geben Sie an, was Ihr Arbeitgeber/Betrieb tut, um Branchenkandidaten zu finden.', tr: "Sektör adaylarını bulmak için işvereninizin/işletmenizin ne yaptığını bize bildirin.", uk: "Напишіть, чим займається ваш роботодавець/підприємство, щоб знайти кандидатів галузей." },

  'reason.income.pending': { ko: '하이코리아에서 실제 연간소득 구간을 선택해야 합니다 (과세 전 기준).', en: 'Select your actual annual income bracket on HiKorea (pre-tax).', 'zh-CN': '须在 HiKorea 选择实际年收入区间（以税前为准）。', ja: 'HiKoreaで実際の年間所得区分を選択する必要があります（税引き前を基準）。', vi: 'Bạn phải chọn khoảng thu nhập hằng năm thực tế trên HiKorea (theo mức trước thuế).', tl: 'Kailangan mong piliin ang aktwal na taunang income bracket sa HiKorea (bago ang buwis).', id: 'Anda harus memilih rentang penghasilan tahunan yang sebenarnya di HiKorea (sebelum pajak).', ru: 'Выберите фактический диапазон годового дохода на HiKorea (до уплаты налогов).', fr: 'Sélectionnez votre tranche de revenu annuel réelle sur HiKorea (avant impôt).', es: 'Seleccione su tramo de ingresos anuales real en HiKorea (antes de impuestos).', ar: 'يجب اختيار شريحة الدخل السنوي الفعلية في HiKorea (قبل الضريبة).', de: 'Wählen Sie Ihre tatsächliche Jahreseinkommensstufe auf HiKorea (vor Steuern).', tr: "HiKorea'da gerçek yıllık gelir diliminizi seçin (vergi öncesi).", uk: "Виберіть свій фактичний діапазон річного доходу на HiKorea (до вирахування податків)." },
  'reason.income.complete': { ko: '소득 구간을 임시로 골랐어요. 최종 선택은 하이코리아에서 확인하세요.', en: 'Income bracket drafted — confirm the final choice on HiKorea.', 'zh-CN': '已暂选收入区间。最终选择请在 HiKorea 确认。', ja: '所得区分を仮に選びました。最終的な選択はHiKoreaで確認してください。', vi: 'Đã chọn tạm khoảng thu nhập. Hãy xác nhận lựa chọn cuối cùng trên HiKorea.', tl: 'Pansamantalang napili ang income bracket — kumpirmahin ang huling pagpili sa HiKorea.', id: 'Rentang penghasilan dipilih sementara — konfirmasi pilihan akhir di HiKorea.', ru: 'Диапазон дохода выбран предварительно — подтвердите окончательный выбор на HiKorea.', fr: 'Tranche de revenu provisoire — confirmez le choix final sur HiKorea.', es: 'Tramo de ingresos provisional — confirme la elección final en HiKorea.', ar: 'تم اختيار شريحة الدخل مؤقتًا — أكّد الاختيار النهائي في HiKorea.', de: 'Einkommensstufe vorläufig gewählt — bestätigen Sie die endgültige Wahl auf HiKorea.', tr: "Gelir dilimi taslak olarak seçildi — nihai seçimi HiKorea'da onaylayın.", uk: "Діапазон доходу вибрано попередньо — підтвердьте остаточний вибір на HiKorea." },

  'reason.hikorea.pending': { ko: '검색을 마치면 하이코리아에서 최종 확인할 항목을 정리해 드려요.', en: 'After searching, we\'ll list what to confirm on HiKorea.', 'zh-CN': '搜索结束后，我们会为您整理出需在 HiKorea 最终确认的事项。', ja: '検索を終えると、HiKoreaで最終確認すべき項目を整理してお見せします。', vi: 'Sau khi tìm kiếm xong, chúng tôi sẽ tổng hợp những mục cần xác nhận cuối cùng trên HiKorea.', tl: 'Pagkatapos maghanap, ililista namin kung ano ang kumpirmahin sa HiKorea.', id: 'Setelah pencarian selesai, kami akan merangkum hal yang perlu dikonfirmasi di HiKorea.', ru: 'После поиска мы перечислим, что нужно подтвердить на HiKorea.', fr: 'Après votre recherche, nous listerons ce qu\'il faut confirmer sur HiKorea.', es: 'Tras buscar, enumeraremos lo que debe confirmar en HiKorea.', ar: 'بعد انتهاء البحث سنرتّب لك العناصر التي يلزم تأكيدها نهائيًا في HiKorea.', de: 'Nach der Suche listen wir auf, was Sie auf HiKorea bestätigen müssen.', tr: "Arama tamamlandığında HiKorea'da neyi onaylamanız gerektiğini listeleriz.", uk: "Після пошуку ми складемо перелік того, що потрібно підтвердити на HiKorea." },
  'reason.hikorea.needs_confirmation': { ko: '최종 신고는 하이코리아 화면에서 직접 확인·선택해야 합니다. Visable은 후보만 찾아드려요.', en: 'Final reporting is done on HiKorea itself — Visable only finds candidates.', 'zh-CN': '最终申报须在 HiKorea 界面亲自确认·选择。Visable 仅为您查找候选。', ja: '最終申告はHiKoreaの画面でご自身が確認・選択する必要があります。Visableは候補をお探しするだけです。', vi: 'Việc khai báo cuối cùng phải do bạn tự xác nhận và chọn trên màn hình HiKorea. Visable chỉ tìm ứng viên.', tl: 'Ang huling pag-uulat ay sa HiKorea mismo gagawin — si Visable ay naghahanap lang ng mga kandidato.', id: 'Pelaporan akhir harus Anda konfirmasi dan pilih sendiri di layar HiKorea. Visable hanya menemukan kandidat.', ru: 'Окончательная подача выполняется на самом HiKorea — Visable только подбирает кандидатов.', fr: 'La déclaration finale se fait sur HiKorea même — Visable ne fait que trouver des candidats.', es: 'La declaración final se realiza en la propia HiKorea — Visable solo busca candidatos.', ar: 'الإبلاغ النهائي يتم على شاشة HiKorea نفسها — أما Visable فيكتفي بإيجاد المرشّحين.', de: 'Die endgültige Meldung erfolgt auf HiKorea selbst — Visable findet nur Kandidaten.', tr: "Nihai bildirim HiKorea'nın kendisinde yapılır — Visable yalnızca aday bulur.", uk: "Остаточна подача виконується безпосередньо на HiKorea — Visable лише підбирає кандидатів." },

  'section.occupation': { ko: '직종 후보: 내가 하는 일에 가까운 항목', en: 'Occupation candidates: closest to what you do', 'zh-CN': '职业候选：与您所做工作最接近的项目', ja: '職種候補：あなたの仕事に最も近い項目', vi: 'Ứng viên nghề nghiệp: mục gần nhất với việc bạn làm', tl: 'Mga kandidatong occupation: pinakamalapit sa ginagawa mo', id: 'Kandidat pekerjaan: paling dekat dengan yang Anda lakukan', ru: 'Кандидаты профессий: ближайшие к тому, что вы делаете', fr: 'Professions candidates : les plus proches de votre travail', es: 'Ocupaciones candidatas: las más cercanas a lo que hace', ar: 'مرشّحو المهن: الأقرب إلى ما تقوم به', de: 'Berufskandidaten: am nächsten zu Ihrer Tätigkeit', tr: "Meslek adayları: yaptığınız işe en yakın olanlar", uk: "Кандидати професій: найближчі до того, що ви робите" },
  'section.industry': { ko: '업종 후보: 회사/사업장이 하는 일에 가까운 항목', en: 'Industry candidates: closest to your employer\'s business', 'zh-CN': '行业候选：与公司/营业场所业务最接近的项目', ja: '業種候補：会社・事業所が行う事業に最も近い項目', vi: 'Ứng viên ngành: mục gần nhất với hoạt động của công ty/cơ sở kinh doanh', tl: 'Mga kandidatong industriya: pinakamalapit sa negosyo ng employer mo', id: 'Kandidat industri: paling dekat dengan usaha perusahaan Anda', ru: 'Кандидаты отраслей: ближайшие к деятельности вашего работодателя', fr: 'Secteurs candidats : les plus proches de l\'activité de votre employeur', es: 'Sectores candidatos: los más cercanos a la actividad de su empleador', ar: 'مرشّحو القطاعات: الأقرب إلى نشاط الشركة/مكان العمل', de: 'Branchenkandidaten: am nächsten zur Tätigkeit Ihres Arbeitgebers', tr: "Sektör adayları: işvereninizin faaliyetine en yakın olanlar", uk: "Кандидати галузей: найближчі до діяльності вашого роботодавця" },
  'caution.main': { ko: 'Visable은 신고용 직종·업종 후보를 찾는 도구예요. 실제 신고 시에는 하이코리아 화면에서 최종 선택값을 확인하세요. (해당 체류자격에서 취업이 가능한지는 판단하지 않아요.)', en: 'Visable finds occupation/industry candidates for reporting. Always confirm the final values on HiKorea. (It does not decide whether your visa permits the work.)', 'zh-CN': 'Visable 是用于查找申报用职业·行业候选的工具。实际申报时，请在 HiKorea 界面确认最终选择值。（不判断该居留资格是否允许就业。）', ja: 'Visableは申告用の職種・業種候補を探すツールです。実際の申告時には、HiKoreaの画面で最終的な選択値を確認してください。（当該の在留資格で就業が可能かどうかは判断しません。）', vi: 'Visable là công cụ tìm ứng viên nghề nghiệp·ngành để khai báo. Khi khai báo thực tế, hãy xác nhận giá trị lựa chọn cuối cùng trên màn hình HiKorea. (Công cụ không phán định liệu tư cách lưu trú đó có cho phép làm việc hay không.)', tl: 'Ang Visable ay kasangkapan para maghanap ng mga kandidatong occupation·industriya para sa pag-uulat. Sa aktwal na pag-uulat, kumpirmahin ang mga huling halaga sa screen ng HiKorea. (Hindi nito tinutukoy kung pinapayagan ng iyong visa ang trabaho.)', id: 'Visable adalah alat untuk menemukan kandidat pekerjaan·industri untuk pelaporan. Saat pelaporan sebenarnya, konfirmasi nilai pilihan akhir di layar HiKorea. (Alat ini tidak menilai apakah status tinggal tersebut mengizinkan bekerja.)', ru: 'Visable — это инструмент для поиска кандидатов профессий·отраслей для отчётности. При фактической подаче подтверждайте итоговые значения на экране HiKorea. (Он не определяет, разрешает ли ваш статус пребывания эту работу.)', fr: 'Visable est un outil pour trouver des professions·secteurs candidats à des fins de déclaration. Lors de la déclaration réelle, confirmez les valeurs finales sur l\'écran HiKorea. (Il ne décide pas si votre statut de séjour autorise ce travail.)', es: 'Visable es una herramienta para buscar ocupaciones·sectores candidatos para la declaración. En la declaración real, confirme los valores finales en la pantalla de HiKorea. (No determina si su estatus de estancia permite el trabajo.)', ar: 'Visable أداة للبحث عن مرشّحي المهن·القطاعات لأغراض الإبلاغ. عند الإبلاغ الفعلي، أكّد القيم النهائية على شاشة HiKorea. (لا يحدّد ما إذا كان وضع الإقامة المعني يسمح بالعمل.)', de: 'Visable ist ein Werkzeug, um Berufs-·Branchenkandidaten für die Meldung zu finden. Bestätigen Sie bei der tatsächlichen Meldung die endgültigen Werte auf dem HiKorea-Bildschirm. (Es entscheidet nicht, ob Ihr Aufenthaltstitel die Arbeit erlaubt.)', tr: "Visable, bildirim için meslek/sektör adayları bulan bir araçtır. Nihai değerleri her zaman HiKorea'da onaylayın. (Vizenizin bu işe izin verip vermediğine karar vermez.)", uk: "Visable — це інструмент для пошуку кандидатів професій·галузей для звітності. Під час фактичної подачі підтверджуйте остаточні значення на екрані HiKorea. (Він не визначає, чи дозволяє ваш статус перебування цю роботу.)" },
  'weak.title': { ko: '입력하신 내용만으로는 직종과 업종을 나누기 어려워요.', en: 'This input alone is hard to split into occupation and industry.', 'zh-CN': '仅凭您输入的内容，难以区分职业和行业。', ja: 'ご入力の内容だけでは、職種と業種を分けるのが難しいです。', vi: 'Chỉ với nội dung bạn nhập, khó tách thành nghề nghiệp và ngành.', tl: 'Sa input na ito lang, mahirap hatiin sa occupation at industriya.', id: 'Hanya dengan masukan ini, sulit memisahkan pekerjaan dan industri.', ru: 'Только по этому вводу трудно разделить профессию и отрасль.', fr: 'Avec cette seule saisie, il est difficile de distinguer profession et secteur.', es: 'Solo con esta entrada es difícil separar ocupación y sector.', ar: 'يصعب فصل المهنة عن القطاع بالاعتماد على ما أدخلته فقط.', de: 'Allein mit dieser Eingabe lässt sich Beruf und Branche schwer trennen.', tr: "Yalnızca bu girdiyle mesleği ve sektörü ayırmak zordur.", uk: "Лише за цим вводом важко розділити професію та галузь." },
  'weak.hint': { ko: '아래처럼 입력하면 더 정확해져요.', en: 'Try inputs like these for a better match.', 'zh-CN': '像下面这样输入会更准确。', ja: '下のように入力するとより正確になります。', vi: 'Hãy nhập như bên dưới để kết quả chính xác hơn.', tl: 'Subukan ang mga input na tulad nito para mas tumpak.', id: 'Coba masukan seperti ini agar lebih akurat.', ru: 'Попробуйте такой ввод для более точного совпадения.', fr: 'Essayez des saisies comme celles-ci pour un meilleur résultat.', es: 'Pruebe entradas como estas para una mejor coincidencia.', ar: 'جرّب إدخالات مثل هذه للحصول على نتيجة أدق.', de: 'Versuchen Sie Eingaben wie diese für eine bessere Übereinstimmung.', tr: "Daha iyi bir eşleşme için şöyle girdiler deneyin.", uk: "Спробуйте такий ввід для точнішого збігу." },
  'weak.detail.place': { ko: '일하는 장소', en: 'Where you work', 'zh-CN': '工作地点', ja: '働く場所', vi: 'Nơi bạn làm việc', tl: 'Kung saan ka nagtatrabaho', id: 'Tempat Anda bekerja', ru: 'Где вы работаете', fr: 'Où vous travaillez', es: 'Dónde trabaja', ar: 'مكان عملك', de: 'Wo Sie arbeiten', tr: "Çalıştığınız yer", uk: "Де ви працюєте" },
  'weak.detail.task': { ko: '하는 일', en: 'What you do', 'zh-CN': '所做的工作', ja: '行う仕事', vi: 'Việc bạn làm', tl: 'Ang ginagawa mo', id: 'Apa yang Anda lakukan', ru: 'Что вы делаете', fr: 'Ce que vous faites', es: 'Lo que hace', ar: 'ما تقوم به', de: 'Was Sie tun', tr: "Yaptığınız iş", uk: "Що ви робите" },
  'weak.detail.business': { ko: '회사/사업장이 하는 일', en: 'What the employer/business does', 'zh-CN': '公司/营业场所所做的业务', ja: '会社・事業所が行う事業', vi: 'Việc công ty/cơ sở kinh doanh làm', tl: 'Ang ginagawa ng employer/negosyo', id: 'Apa yang dilakukan perusahaan/tempat usaha', ru: 'Чем занимается работодатель/предприятие', fr: 'Ce que fait l\'employeur/l\'établissement', es: 'Lo que hace el empleador/negocio', ar: 'ما تقوم به الشركة/مكان العمل', de: 'Was der Arbeitgeber/Betrieb tut', tr: "İşverenin/işletmenin ne yaptığı", uk: "Чим займається роботодавець/підприємство" },
  'clarify.lead': { ko: '정확도를 높이려면 이것만 확인해 주세요.', en: 'One more detail will improve the match.', 'zh-CN': '为提高准确度，只需确认这一点。', ja: '正確さを高めるために、これだけ確認してください。', vi: 'Để tăng độ chính xác, chỉ cần xác nhận điều này.', tl: 'Para mas tumpak, kumpirmahin lang ito.', id: 'Untuk meningkatkan akurasi, cukup konfirmasi ini.', ru: 'Чтобы повысить точность, подтвердите только это.', fr: 'Pour améliorer la précision, confirmez seulement ceci.', es: 'Para mayor precisión, solo confirme esto.', ar: 'لزيادة الدقة، أكّد هذا فقط.', de: 'Für mehr Genauigkeit bestätigen Sie nur dies.', tr: "Bir ayrıntı daha eşleşmeyi iyileştirecek.", uk: "Щоб підвищити точність, підтвердьте лише це." },
  'card.fit': { ko: '이 항목이 맞을 수 있는 경우', en: 'This may fit when', 'zh-CN': '该项目可能合适的情况', ja: 'この項目が当てはまる場合', vi: 'Mục này có thể phù hợp khi', tl: 'Maaaring bagay ito kapag', id: 'Item ini mungkin cocok jika', ru: 'Этот вариант может подойти, когда', fr: 'Cet élément peut convenir lorsque', es: 'Esta opción puede encajar cuando', ar: 'قد يناسب هذا العنصر عندما', de: 'Dies könnte passen, wenn', tr: "Bu, şu durumda uygun olabilir", uk: "Цей варіант може підійти, коли" },
  'card.other': { ko: '다른 항목이 맞을 수 있는 경우', en: 'Another may fit when', 'zh-CN': '其他项目可能更合适的情况', ja: '別の項目が当てはまる場合', vi: 'Mục khác có thể phù hợp khi', tl: 'Maaaring bagay ang iba kapag', id: 'Item lain mungkin cocok jika', ru: 'Другой вариант может подойти, когда', fr: 'Un autre élément peut convenir lorsque', es: 'Otra opción puede encajar cuando', ar: 'قد يناسب عنصر آخر عندما', de: 'Ein anderes könnte passen, wenn', tr: "Başka bir seçenek şu durumda uygun olabilir", uk: "Інший варіант може підійти, коли" },
  'card.needsCode': { ko: '공식 코드 확인 필요', en: 'Official code needs confirmation', 'zh-CN': '需确认官方代码', ja: '公式コードの確認が必要', vi: 'Cần xác nhận mã chính thức', tl: 'Kailangan ng kumpirmasyon sa opisyal na code', id: 'Perlu konfirmasi kode resmi', ru: 'Требуется подтверждение официального кода', fr: 'Code officiel à confirmer', es: 'El código oficial necesita confirmación', ar: 'يلزم تأكيد الرمز الرسمي', de: 'Offizieller Code muss bestätigt werden', tr: "Resmi kodun onaylanması gerekiyor", uk: "Потрібне підтвердження офіційного коду" },
  // HiKorea final step shows an action label, never a "complete" one.
  'status.hikorea': { ko: '하이코리아에서 확인해 주세요', en: 'Confirm in HiKorea', 'zh-CN': '请在 HiKorea 确认', ja: 'HiKoreaで確認してください', vi: 'Hãy xác nhận trên HiKorea', tl: 'Kumpirmahin sa HiKorea', id: 'Konfirmasi di HiKorea', ru: 'Подтвердите на HiKorea', fr: 'Confirmez sur HiKorea', es: 'Confirme en HiKorea', ar: 'أكّد عبر HiKorea', de: 'Auf HiKorea bestätigen', tr: "HiKorea'da onaylayın", uk: "Підтвердьте на HiKorea" },

  // Toss-inspired guided UI copy (keyed for every locale; rendered by index.html).
  'interpret.title': { ko: '이렇게 이해했어요', en: 'Here’s how Visable understood your input', 'zh-CN': 'Visable 是这样理解您输入的', ja: 'Visableはこう理解しました', vi: 'Visable đã hiểu nội dung bạn nhập như thế này', tl: 'Ganito naintindihan ng Visable ang input mo', id: 'Beginilah Visable memahami masukan Anda', ru: 'Вот как Visable понял ваш ввод', fr: 'Voici comment Visable a compris votre saisie', es: 'Así entendió Visable su entrada', ar: 'هكذا فهم Visable ما أدخلته', de: 'So hat Visable Ihre Eingabe verstanden', tr: "Visable, girdinizi şöyle anladı", uk: "Ось як Visable зрозумів ваш ввід" },
  'interpret.place': { ko: '일하는 곳', en: 'Where you work', 'zh-CN': '工作地点', ja: '働く場所', vi: 'Nơi làm việc', tl: 'Lugar ng trabaho', id: 'Tempat bekerja', ru: 'Место работы', fr: 'Lieu de travail', es: 'Lugar de trabajo', ar: 'مكان العمل', de: 'Arbeitsort', tr: "Çalıştığınız yer", uk: "Місце роботи" },
  'interpret.object': { ko: '대상', en: 'What you handle', 'zh-CN': '处理的对象', ja: '対象', vi: 'Đối tượng xử lý', tl: 'Ang hinahawakan', id: 'Objek yang ditangani', ru: 'С чем работаете', fr: 'Ce que vous traitez', es: 'Lo que maneja', ar: 'ما تتعامل معه', de: 'Womit Sie arbeiten', tr: "Ne ile çalıştığınız", uk: "З чим працюєте" },
  'interpret.action': { ko: '하는 일', en: 'What you do', 'zh-CN': '所做的工作', ja: '行う仕事', vi: 'Việc làm', tl: 'Ang ginagawa', id: 'Yang dilakukan', ru: 'Что вы делаете', fr: 'Ce que vous faites', es: 'Lo que hace', ar: 'ما تقوم به', de: 'Was Sie tun', tr: "Yaptığınız iş", uk: "Що ви робите" },
  'interpret.check': { ko: '더 확인할 점', en: 'Still to confirm', 'zh-CN': '仍需确认的点', ja: 'さらに確認する点', vi: 'Điểm cần xác nhận thêm', tl: 'Dapat pang tiyakin', id: 'Yang masih perlu dipastikan', ru: 'Ещё нужно подтвердить', fr: 'Encore à confirmer', es: 'Aún por confirmar', ar: 'ما يلزم تأكيده أيضًا', de: 'Noch zu bestätigen', tr: "Hâlâ onaylanması gerekenler", uk: "Ще потрібно підтвердити" },
  'clarify.dunno': { ko: '잘 모르겠어요', en: 'Not sure', 'zh-CN': '不太清楚', ja: 'よくわかりません', vi: 'Không chắc', tl: 'Hindi sigurado', id: 'Tidak yakin', ru: 'Не уверен(а)', fr: 'Je ne sais pas', es: 'No estoy seguro', ar: 'لست متأكدًا', de: 'Nicht sicher', tr: "Emin değilim", uk: "Не впевнений(а)" },
  'conf.high': { ko: '가장 가까움', en: 'Closest', 'zh-CN': '最接近', ja: '最も近い', vi: 'Gần nhất', tl: 'Pinakamalapit', id: 'Paling dekat', ru: 'Ближайший', fr: 'Le plus proche', es: 'El más cercano', ar: 'الأقرب', de: 'Am nächsten', tr: "En yakın", uk: "Найближчий" },
  'conf.mid': { ko: '비슷함', en: 'Similar', 'zh-CN': '相似', ja: '類似', vi: 'Tương tự', tl: 'Magkatulad', id: 'Mirip', ru: 'Похожий', fr: 'Similaire', es: 'Similar', ar: 'مشابه', de: 'Ähnlich', tr: "Benzer", uk: "Схожий" },
  'conf.low': { ko: '가능성 있음', en: 'Possible', 'zh-CN': '有可能', ja: '可能性あり', vi: 'Có thể', tl: 'Posible', id: 'Mungkin', ru: 'Возможно', fr: 'Possible', es: 'Posible', ar: 'محتمل', de: 'Möglich', tr: "Olası", uk: "Можливо" },
  'group.top': { ko: '가장 가까운 후보', en: 'Closest candidate', 'zh-CN': '最接近的候选', ja: '最も近い候補', vi: 'Ứng viên gần nhất', tl: 'Pinakamalapit na kandidato', id: 'Kandidat paling dekat', ru: 'Ближайший кандидат', fr: 'Candidat le plus proche', es: 'Candidato más cercano', ar: 'المرشّح الأقرب', de: 'Nächster Kandidat', tr: "En yakın aday", uk: "Найближчий кандидат" },
  'group.others': { ko: '다른 가능성', en: 'Other possibilities', 'zh-CN': '其他可能', ja: 'その他の可能性', vi: 'Khả năng khác', tl: 'Iba pang posibilidad', id: 'Kemungkinan lain', ru: 'Другие варианты', fr: 'Autres possibilités', es: 'Otras posibilidades', ar: 'احتمالات أخرى', de: 'Weitere Möglichkeiten', tr: "Diğer olasılıklar", uk: "Інші варіанти" },
  'group.several': { ko: '몇 가지 가능성이 있어요', en: 'A few possibilities', 'zh-CN': '有几种可能', ja: 'いくつかの可能性があります', vi: 'Có một vài khả năng', tl: 'May ilang posibilidad', id: 'Ada beberapa kemungkinan', ru: 'Есть несколько вариантов', fr: 'Quelques possibilités', es: 'Hay varias posibilidades', ar: 'هناك عدة احتمالات', de: 'Mehrere Möglichkeiten', tr: "Birkaç olasılık var", uk: "Є кілька варіантів" },
  'card.source': { ko: '공식 분류 코드', en: 'Official classification code', 'zh-CN': '官方分类代码', ja: '公式分類コード', vi: 'Mã phân loại chính thức', tl: 'Opisyal na classification code', id: 'Kode klasifikasi resmi', ru: 'Официальный код классификации', fr: 'Code de classification officiel', es: 'Código de clasificación oficial', ar: 'رمز التصنيف الرسمي', de: 'Offizieller Klassifikationscode', tr: "Resmi sınıflandırma kodu", uk: "Офіційний код класифікації" },
  'card.detail': { ko: '자세히 보기', en: 'See details', 'zh-CN': '查看详情', ja: '詳細を見る', vi: 'Xem chi tiết', tl: 'Tingnan ang detalye', id: 'Lihat detail', ru: 'Подробнее', fr: 'Voir les détails', es: 'Ver detalles', ar: 'عرض التفاصيل', de: 'Details anzeigen', tr: "Ayrıntıları gör", uk: "Переглянути деталі" },
  'more.show': { ko: '더 보기', en: 'Show more', 'zh-CN': '查看更多', ja: 'もっと見る', vi: 'Xem thêm', tl: 'Magpakita pa', id: 'Tampilkan lainnya', ru: 'Показать ещё', fr: 'Afficher plus', es: 'Mostrar más', ar: 'عرض المزيد', de: 'Mehr anzeigen', tr: "Daha fazla göster", uk: "Показати більше" },
  'more.hide': { ko: '접기', en: 'Show less', 'zh-CN': '收起', ja: '閉じる', vi: 'Thu gọn', tl: 'Magpakita ng mas kaunti', id: 'Sembunyikan', ru: 'Свернуть', fr: 'Afficher moins', es: 'Mostrar menos', ar: 'عرض أقل', de: 'Weniger anzeigen', tr: "Daha az göster", uk: "Показати менше" },
  'needcode.title': { ko: '공식 코드 확인 필요', en: 'Official code needs confirmation', 'zh-CN': '需确认官方代码', ja: '公式コードの確認が必要', vi: 'Cần xác nhận mã chính thức', tl: 'Kailangan ng kumpirmasyon sa opisyal na code', id: 'Perlu konfirmasi kode resmi', ru: 'Требуется подтверждение официального кода', fr: 'Code officiel à confirmer', es: 'El código oficial necesita confirmación', ar: 'يلزم تأكيد الرمز الرسمي', de: 'Offizieller Code muss bestätigt werden', tr: "Resmi kodun onaylanması gerekiyor", uk: "Потрібне підтвердження офіційного коду" },
  'needcode.body': { ko: '입력하신 업무는 해석할 수 있지만, 하이코리아에서 실제 선택할 공식 코드까지는 최종 확인이 필요해요.', en: 'Visable can read your work, but the exact official code to pick in HiKorea still needs a final check.', 'zh-CN': '您输入的工作可以被解读，但在 HiKorea 实际选择的官方代码仍需最终确认。', ja: '入力された業務は解釈できますが、HiKoreaで実際に選択する公式コードまでは最終確認が必要です。', vi: 'Có thể đọc hiểu công việc bạn nhập, nhưng mã chính thức thực tế cần chọn trên HiKorea vẫn cần kiểm tra cuối cùng.', tl: 'Mababasa ng Visable ang trabaho mo, ngunit kailangan pa ng huling pagtsek ang eksaktong opisyal na code na pipiliin sa HiKorea.', id: 'Pekerjaan yang Anda masukkan dapat dipahami, tetapi kode resmi yang benar-benar dipilih di HiKorea masih perlu pemeriksaan akhir.', ru: 'Visable понимает вашу работу, но точный официальный код для выбора на HiKorea всё ещё требует финальной проверки.', fr: 'Visable peut interpréter votre travail, mais le code officiel exact à choisir sur HiKorea nécessite encore une vérification finale.', es: 'Visable puede interpretar su trabajo, pero el código oficial exacto a elegir en HiKorea aún necesita una comprobación final.', ar: 'يمكن لـ Visable تفسير عملك، لكن الرمز الرسمي الدقيق الذي ستختاره في HiKorea لا يزال بحاجة إلى تحقق نهائي.', de: 'Visable kann Ihre Tätigkeit deuten, doch der genaue offizielle Code zur Auswahl auf HiKorea braucht noch eine abschließende Prüfung.', tr: "Visable işinizi yorumlayabilir, ancak HiKorea'da seçilecek tam resmi kodun yine de son bir kontrole ihtiyacı var.", uk: "Visable може розпізнати вашу роботу, але точний офіційний код для вибору на HiKorea все ще потребує остаточної перевірки." },
  'needcode.research': { ko: '다른 표현으로 다시 검색', en: 'Search with different words', 'zh-CN': '换种表述重新搜索', ja: '別の表現で再検索', vi: 'Tìm lại bằng cách diễn đạt khác', tl: 'Maghanap gamit ang ibang salita', id: 'Cari lagi dengan kata lain', ru: 'Искать другими словами', fr: 'Rechercher avec d\'autres mots', es: 'Buscar con otras palabras', ar: 'ابحث بصياغة أخرى', de: 'Mit anderen Worten suchen', tr: "Farklı kelimelerle ara", uk: "Шукати іншими словами" },
  'needcode.portal': { ko: '통계분류포털에서 확인', en: 'Check the classification portal', 'zh-CN': '在统计分类门户确认', ja: '統計分類ポータルで確認', vi: 'Kiểm tra trên cổng phân loại thống kê', tl: 'Tingnan sa classification portal', id: 'Periksa di portal klasifikasi', ru: 'Проверить на портале классификации', fr: 'Vérifier sur le portail de classification', es: 'Consultar en el portal de clasificación', ar: 'تحقّق من بوابة التصنيف', de: 'Im Klassifikationsportal prüfen', tr: "Sınıflandırma portalında kontrol edin", uk: "Перевірити на порталі класифікації" },
  // Guided-flow gate (candidates held behind the clarification question)
  'flow.gateTitle': { ko: '후보는 잠시 후에 보여드릴게요', en: 'Candidates in just a moment', 'zh-CN': '候选稍后即可显示', ja: '候補は少し後でお見せします', vi: 'Ứng viên sẽ hiển thị trong giây lát', tl: 'Ipapakita ang mga kandidato sa ilang sandali', id: 'Kandidat akan ditampilkan sebentar lagi', ru: 'Кандидаты появятся через мгновение', fr: 'Les candidats dans un instant', es: 'Los candidatos en un momento', ar: 'سنعرض المرشّحين بعد لحظات', de: 'Kandidaten gleich', tr: "Adaylar birazdan", uk: "Кандидати з'являться за мить" },
  'flow.gateBody': { ko: '위 질문에 답하면 더 정확한 직종·업종 후보를 보여드려요.', en: 'Answer the question above and we’ll show more accurate occupation/industry candidates.', 'zh-CN': '回答上面的问题，即可显示更准确的职业·行业候选。', ja: '上の質問に答えると、より正確な職種・業種候補をお見せします。', vi: 'Trả lời câu hỏi ở trên để chúng tôi hiển thị ứng viên nghề nghiệp·ngành chính xác hơn.', tl: 'Sagutin ang tanong sa itaas at magpapakita kami ng mas tumpak na mga kandidatong occupation·industriya.', id: 'Jawab pertanyaan di atas, dan kami akan menampilkan kandidat pekerjaan·industri yang lebih akurat.', ru: 'Ответьте на вопрос выше — и мы покажем более точных кандидатов профессий·отраслей.', fr: 'Répondez à la question ci-dessus et nous afficherons des professions·secteurs candidats plus précis.', es: 'Responda la pregunta de arriba y le mostraremos ocupaciones·sectores candidatos más precisos.', ar: 'أجب عن السؤال أعلاه لنعرض مرشّحي مهن·قطاعات أكثر دقة.', de: 'Beantworten Sie die Frage oben, und wir zeigen genauere Berufs-·Branchenkandidaten.', tr: "Yukarıdaki soruyu yanıtlayın, daha doğru meslek/sektör adayları gösterelim.", uk: "Дайте відповідь на запитання вище — і ми покажемо точніших кандидатів професій·галузей." },
  'flow.reveal': { ko: '그냥 후보 보기', en: 'Show candidates anyway', 'zh-CN': '直接查看候选', ja: 'そのまま候補を見る', vi: 'Cứ xem ứng viên', tl: 'Ipakita pa rin ang mga kandidato', id: 'Tetap tampilkan kandidat', ru: 'Всё равно показать кандидатов', fr: 'Afficher quand même les candidats', es: 'Mostrar candidatos de todos modos', ar: 'اعرض المرشّحين على أي حال', de: 'Kandidaten trotzdem anzeigen', tr: "Adayları yine de göster", uk: "Все одно показати кандидатів" }
};

// Every locale Paradiso ships UI copy in. `ko` is the source/fallback; any locale
// missing a string (or an unknown code) resolves to `ko`. zh-CN keeps its hyphen
// key, which is why we look up by the raw code rather than a stripped form.
export const CHECKLIST_LANGS = ['ko', 'en', 'zh-CN', 'ja', 'vi', 'tl', 'id', 'ru', 'fr', 'es', 'ar', 'de', 'tr', 'uk'];
// Locales rendered right-to-left (no bidi control characters are injected — the UI
// sets direction via dir="rtl"; this list only flags which codes are RTL).
export const CHECKLIST_RTL_LANGS = ['ar'];

/** Normalize an arbitrary lang code to a supported one, falling back to ko. */
export function resolveChecklistLang(lang) {
  return CHECKLIST_LANGS.includes(lang) ? lang : 'ko';
}

/** Resolve a copy key to a language (ko default; any missing locale falls back to ko). */
export function checklistCopy(key, lang) {
  const e = CHECKLIST_COPY[key];
  if (!e) return key;
  const l = resolveChecklistLang(lang);
  return e[l] || e.ko;
}
function statusLabel(status, lang) {
  const s = STATUS[status] || STATUS.pending;
  const l = resolveChecklistLang(lang);
  return s[l] || s.ko;
}

// Which track(s) the TOP clarification question actually forks. Keeps the two
// checklist tracks independent: "software developer" clarifies the employer
// (industry) while the occupation is already clear; "골프장 청소" clarifies the
// employer (industry) while "cleaner" is clear; a vessel/factory fork changes both.
const CLARIFY_TRACKS_BY_TOPIC = {
  direct_employer_vs_contractor: ['industry'],
  restaurant_employee_vs_outsourced: ['industry'],
  employer_product_unknown: ['industry'],
  hospitality_role_unknown: ['occupation'],
  construction_labor_vs_technical_install: ['occupation'],
  vessel_crew_vs_land_processing: ['occupation', 'industry'],
  aquaculture_vs_processing: ['occupation', 'industry'],
  farm_harvest_vs_food_factory: ['occupation', 'industry'],
  manufacturing_vs_logistics: ['occupation', 'industry']
};
const CLARIFY_TRACKS_BY_FLAG = {
  workplace: ['industry'],
  role: ['occupation'],
  freelancer: ['occupation', 'industry'],
  owner: ['occupation', 'industry'],
  underspecified: ['occupation', 'industry']
};
function clarificationTracks(result) {
  const q = result && Array.isArray(result.ambiguityQuestions) ? result.ambiguityQuestions[0] : null;
  if (!q) return { occupation: false, industry: false };
  const list = (q.topic && CLARIFY_TRACKS_BY_TOPIC[q.topic]) || (q.flag && CLARIFY_TRACKS_BY_FLAG[q.flag]) || ['occupation', 'industry'];
  return { occupation: list.includes('occupation'), industry: list.includes('industry') };
}

/** True when the analyzer understood the input (signals/concepts/interpretation). */
function hasUnderstanding(r) {
  if (!r) return false;
  const ps = r.parsedSignals || {};
  const sig = (ps.places || []).length + (ps.objects || []).length + (ps.actions || []).length + (ps.tools || []).length;
  return sig > 0 || (r.matchedConcepts || []).length > 0 || !!r.parsedInterpretation ||
    !!(r.extracted && (r.extracted.jobRole || r.extracted.workplaceType || r.extracted.businessActivity));
}

/**
 * buildEmploymentChecklistState(opts) → { schema, lang, concepts, steps }.
 *
 * opts:
 *   analyzerResult           PR #442 analyze() output, or null (initial state)
 *   selectedOccupation       { code, name } | null  (user confirmed)
 *   selectedIndustry         { code, name } | null
 *   clarificationState       { answered:boolean } | null   (override)
 *   incomeState              { selected:boolean, value? } | null
 *   sourceStatus             override string (else analyzerResult.sourceStatus)
 *   occupationResultCount    number of occupation cards actually shown (UI truth)
 *   industryResultCount      number of industry cards actually shown
 *   lang                     any of CHECKLIST_LANGS (default 'ko'; unknown → 'ko')
 */
export function buildEmploymentChecklistState(opts = {}) {
  const r = opts.analyzerResult || null;
  const lang = resolveChecklistLang(opts.lang);
  const hasResult = !!r;

  const occCount = opts.occupationResultCount != null
    ? opts.occupationResultCount : (r && r.occupationCandidates ? r.occupationCandidates.length : 0);
  const indCount = opts.industryResultCount != null
    ? opts.industryResultCount : (r && r.industryCandidates ? r.industryCandidates.length : 0);

  const understood = hasUnderstanding(r);
  const answered = !!(opts.clarificationState && opts.clarificationState.answered);
  const clarificationPending = !!(r && r.clarificationRequired) && !answered;
  // Per-track: only the track(s) the top question actually forks are held back.
  const forks = clarificationPending ? clarificationTracks(r) : { occupation: false, industry: false };
  const noOfficialCodeFound = !!(r && r.noOfficialCodeFound);
  const needsCode = hasResult && (opts.sourceStatus === 'needs_confirmation' || r.sourceStatus === 'needs_confirmation' ||
    (noOfficialCodeFound && understood));

  const occupationConfirmed = !!opts.selectedOccupation;
  const industryConfirmed = !!opts.selectedIndustry;
  const occupationCandidateFound = occCount > 0;
  const industryCandidateFound = indCount > 0;
  const incomeSelected = !!(opts.incomeState && opts.incomeState.selected);

  // Per-track status: confirmed > (this track's) clarification > candidate >
  // needs-code > weak. Clarification only blocks the track it actually forks.
  function trackStatus(confirmed, candidateFound, forked) {
    if (!hasResult) return 'pending';
    if (confirmed) return 'complete';
    if (forked) return 'needs_confirmation';
    if (candidateFound) return 'ready';
    if (needsCode) return 'needs_confirmation';
    if (understood) return 'needs_confirmation'; // understood but no card → confirm officially
    return 'blocked';                            // weak input → ask for more detail
  }
  const occStatus = trackStatus(occupationConfirmed, occupationCandidateFound, forks.occupation);
  const indStatus = trackStatus(industryConfirmed, industryCandidateFound, forks.industry);

  function reasonKey(track, status, forked) {
    if (status === 'complete') return `reason.${track}.complete`;
    if (status === 'blocked') return `reason.${track}.blocked`;
    if (status === 'ready') return `reason.${track}.ready`;
    if (status === 'pending') return `reason.${track}.pending`;
    // needs_confirmation: this track's clarification first, else official-code.
    if (forked) return `reason.${track}.needs_confirmation`;
    return `reason.${track}.needs_code`;
  }

  const mkStep = (id, labelKey, plainKey, status, reasonKeyStr, extra = {}) => ({
    id,
    label: checklistCopy(labelKey, lang),
    labelKey,
    plainLanguageLabel: checklistCopy(plainKey, lang),
    status,
    // statusLabelKey lets a step show an action-style label (e.g. the HiKorea
    // step always says "하이코리아에서 확인해 주세요", never a "complete" label).
    statusLabel: extra.statusLabelKey ? checklistCopy(extra.statusLabelKey, lang) : statusLabel(status, lang),
    reason: checklistCopy(reasonKeyStr, lang),
    reasonKey: reasonKeyStr,
    i18nKey: labelKey,
    sourceStatus: extra.sourceStatus || (status === 'needs_confirmation' && extra.code ? 'needs_confirmation' : (status === 'ready' || status === 'complete' ? 'official_list' : 'pending')),
    ...(extra.actionLabel ? { actionLabel: extra.actionLabel } : {})
  });

  const incomeStatus = !hasResult ? 'pending' : (incomeSelected ? 'complete' : 'pending');
  const incomeReasonKey = incomeStatus === 'complete' ? 'reason.income.complete' : 'reason.income.pending';
  // HiKorea final check is NEVER complete inside Paradiso.
  const hikoreaStatus = hasResult ? 'needs_confirmation' : 'pending';
  const hikoreaReasonKey = hasResult ? 'reason.hikorea.needs_confirmation' : 'reason.hikorea.pending';

  const steps = [
    mkStep('occupation', 'step.occupation.label', 'step.occupation.plain', occStatus,
      reasonKey('occupation', occStatus, forks.occupation), { code: true }),
    mkStep('industry', 'step.industry.label', 'step.industry.plain', indStatus,
      reasonKey('industry', indStatus, forks.industry), { code: true }),
    mkStep('income', 'step.income.label', 'step.income.plain', incomeStatus, incomeReasonKey),
    mkStep('hikorea', 'step.hikorea.label', 'step.hikorea.plain', hikoreaStatus, hikoreaReasonKey,
      { sourceStatus: 'needs_confirmation', statusLabelKey: 'status.hikorea' })
  ];

  return {
    schema: CHECKLIST_SCHEMA,
    lang,
    concepts: {
      occupationCandidateFound,
      occupationConfirmed,
      industryCandidateFound,
      industryConfirmed,
      incomeReminderShown: hasResult,
      incomeSelected,
      officialCodeVerified: (occupationCandidateFound || industryCandidateFound) && !noOfficialCodeFound,
      officialCodeNeedsConfirmation: needsCode,
      clarificationPending,
      hikoreaFinalCheckRequired: true
    },
    steps
  };
}

export default { CHECKLIST_SCHEMA, STATUS, CHECKLIST_COPY, CHECKLIST_LANGS, CHECKLIST_RTL_LANGS, resolveChecklistLang, checklistCopy, buildEmploymentChecklistState, employmentFlowState };

// Browser bridge for the inline UI in index.html (no build step).
if (typeof window !== 'undefined') {
  window.EmploymentChecklist = { CHECKLIST_SCHEMA, STATUS, CHECKLIST_COPY, CHECKLIST_LANGS, CHECKLIST_RTL_LANGS, resolveChecklistLang, checklistCopy, buildEmploymentChecklistState, employmentFlowState };
}
