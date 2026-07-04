/* ============================================================================
 * Paradiso — Complex-Status Guide for additional statuses (F-6/G-1/E-7/F-5/D-2/D-4)
 * ----------------------------------------------------------------------------
 * Brings the F-4 "recommended starting point → one dominant CTA → full-screen
 * guided flow → checklist-first result" pattern to six more complex statuses,
 * WITHOUT touching the F-4 reference implementation (assets/js/f4-route-guide.js)
 * and WITHOUT inventing any legal/document content.
 *
 * Source-safety contract:
 *  - Subcode options come verbatim from visa_data.json via the TESTED adapter
 *    window.ParadisoRoute.buildGuidanceModel() (never re-derived here).
 *  - Procedure options are only the ones the adapter reports as "available".
 *  - Manual-review / reference-only subcodes (placeholders) are NOT offered.
 *  - The result NEVER re-renders protected document data. It narrows the user to
 *    a subcode + procedure, then hands off to the EXISTING source-backed detail
 *    (window.ParadisoRoute.goToResult / openVisaDrawer) for the real documents
 *    and source references. Anything not source-backed here is shown as
 *    "공식근거 확인 필요" (Official source needs confirmation).
 *  - No eligibility/approval claims. Cautious language only.
 *
 * Reuse: the F-4 engine (ParadisoComplexGuide) is intentionally NOT forked into;
 * it is data/f4-coupled and must not regress. This engine shares the same UX,
 * CSS tokens, copy, and a11y pattern, and delegates the actual legal content to
 * ParadisoRoute, so the six statuses feel consistent with F-4 while staying safe.
 * ========================================================================== */
(function () {
  'use strict';

  var TARGETS = ['F-6', 'G-1', 'E-7', 'F-5', 'D-2', 'D-4'];

  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (ch) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[ch];
    });
  }
  // Locales with their own chrome-string pack below. Anything else (or missing
  // keys) falls back to Korean — official names are never invented.
  var SUPPORTED_LANGS = ['ko', 'en', 'zh-CN', 'ja', 'vi', 'tl', 'id', 'ru', 'fr', 'es', 'ar', 'de', 'tr', 'uk'];
  function csgLang() {
    var l = (typeof currentLanguage !== 'undefined' && currentLanguage) ? currentLanguage : 'ko';
    return SUPPORTED_LANGS.indexOf(l) !== -1 ? l : 'ko';
  }

  /* ---- chrome strings (Korean canonical; English + Simplified Chinese active.
   * Per-status data (subcode/doc names) falls back to Korean when no localized
   * value exists — official names are never invented). --------------------- */
  var STR_KO = {
    eyebrow: '공식 출처 기반 안내',
    recStartTitle: '상황에 맞는 절차 안내',
    recStartBody: '이 체류자격은 세부 유형, 신청 절차, 현재 상황에 따라 준비서류와 진행 방식이 달라질 수 있습니다. 몇 가지 질문에 답하면 내 상황에 가까운 준비서류와 절차를 확인할 수 있습니다.',
    ctaMicrocopy: '약 1분 · 세부코드를 몰라도 시작 가능',
    primaryCtaTpl: '내 상황에 맞는 {code} 준비서류 찾기',
    secondaryActionsLabel: '다른 방법으로 찾아보기',
    secViewSubcategories: '전체 세부자격 보기',
    secViewCommonDocs: '공통서류 보기',
    secViewProcedure: '신청 절차 보기',
    secViewSources: '공식 근거 보기',
    modalAria: '체류자격 준비 안내',
    close: '닫기',
    back: '← 이전',
    next: '다음',
    seeResult: '결과 보기',
    restartShort: '다시 시작',
    stepWord: '단계',
    progressAria: '진행 상황',
    optUnsure: '잘 모르겠어요',
    stepSubcodeQ: '어떤 유형에 가까우신가요?',
    stepSubcodeHelp: '아래 유형 중 가장 가까운 것을 선택하세요(공식 데이터 기준). 정확히 몰라도 "잘 모르겠어요"를 고르면 됩니다.',
    stepProcedureQ: '지금 필요한 절차는 무엇인가요?',
    stepProcedureHelp: '현재 데이터에서 안내 가능한 절차만 표시됩니다.',
    resultTitleTpl: '당신에게 가까운 {code} 준비경로',
    matchedType: '선택한 유형',
    matchedProcedure: '선택한 절차',
    unsureType: '유형 미정',
    unsureProcedure: '절차 미정',
    resFirstSteps: '먼저 해야 할 일',
    resBasicDocs: '기본 준비서류',
    resAddDocs: '내 상황에서 추가될 수 있는 서류',
    resProcedure: '신청 절차',
    resSources: '공식 근거',
    resNextActions: '다음 행동',
    officialSourceNeedsConfirm: '공식근거 확인 필요',
    firstStepConfirmType: '내 세부 유형이 맞는지 확인하기',
    firstStepConfirmOffice: '관할 출입국·외국인관서 또는 재외공관 확인하기',
    firstStepPrepareDocs: '선택한 절차에 맞는 서류 준비하기',
    docsHandoffNote: '구체적 준비서류는 공식 출처 기반 상세 화면에서 확인하세요. 아래 "전체 준비서류·절차 보기"를 눌러 해당 세부코드·절차의 서류를 확인할 수 있습니다.',
    addDocsNote: '개별 상황에 따라 추가서류가 요구될 수 있습니다. 정확한 목록은 상세 화면과 관할 기관에서 확인하세요.',
    sourcesHandoffNote: '공식 근거(매뉴얼·출처)는 상세 화면에 함께 표시됩니다. 출처가 연결되지 않은 항목은 "공식근거 확인 필요"로 표시됩니다.',
    viewFullDetail: '전체 준비서류·절차 보기',
    copyChecklist: '체크리스트 복사',
    copied: '복사되었습니다',
    copyFail: '복사하지 못했습니다',
    safetyNote: '개별 사안, 관할 출입국기관 또는 재외공관 판단에 따라 추가서류가 요구될 수 있습니다.',
    procStepPrepare: '서류 준비',
    procStepReserve: '필요 시 방문 예약',
    procStepSubmit: '신청서 제출',
    procStepReview: '심사',
    procStepResult: '결과 확인',
    procStepFollowup: '필요 시 후속 등록·증 발급',
    noSubcodesNote: '이 체류자격은 공식 데이터에 정리된 선택 가능한 세부 유형이 없어, 바로 절차 안내로 진행합니다.',
    noteE7: 'E-7은 직종·직무에 따라 요건과 서류가 다릅니다. 정확한 직종 분류 확인이 필요할 수 있으며, 결과는 단정할 수 없습니다.',
    noteG1: 'G-1은 체류 사유별로 요건과 서류가 다르며, 다수 항목이 개별 심사·확인 대상입니다. 관할 기관 확인이 필요합니다.',
    noteF5: 'F-5(영주)는 자격 기준과 절차가 까다롭고 개별 심사 비중이 큽니다. 구체적 요건은 공식 출처와 관할 기관에서 확인하세요.',
    docChecklistIntro: '아래는 공식 매뉴얼에 정리된 준비서류입니다(참고용 체크리스트). 개별 사안에 따라 달라질 수 있습니다.',
    docsInManualNote: '이 절차의 준비서류가 공식 매뉴얼에 정리되어 있습니다. "전체 준비서류·절차 보기"에서 전체 목록을 확인하세요.',
    docsMoreInDetail: '그 밖의 항목은 상세 화면에서 전체 확인하세요.',
    sourceManualLabel: '매뉴얼 근거'
  };
  var STR_EN = {
    eyebrow: 'Guidance based on official sources',
    recStartTitle: 'Guided steps for your situation',
    recStartBody: 'Documents and procedures for this status may vary depending on your subcategory, application path, and current situation. Answer a few questions to find the document checklist and procedure closest to your situation.',
    ctaMicrocopy: 'About 1 minute · No subcategory knowledge needed',
    primaryCtaTpl: 'Find My {code} Document Checklist',
    secondaryActionsLabel: 'Other ways to explore',
    secViewSubcategories: 'View All Subcategories',
    secViewCommonDocs: 'View Common Documents',
    secViewProcedure: 'View Application Procedure',
    secViewSources: 'View Official Sources',
    modalAria: 'Status preparation guide',
    close: 'Close',
    back: '← Back',
    next: 'Next',
    seeResult: 'See result',
    restartShort: 'Restart',
    stepWord: 'Step',
    progressAria: 'Progress',
    optUnsure: 'I am not sure',
    stepSubcodeQ: 'Which type is closest to yours?',
    stepSubcodeHelp: 'Pick the type closest to your situation (from official data). Not sure? Just choose "I am not sure".',
    stepProcedureQ: 'Which procedure do you need now?',
    stepProcedureHelp: 'Only procedures the current data can guide are shown.',
    resultTitleTpl: 'Your likely {code} preparation path',
    matchedType: 'Selected type',
    matchedProcedure: 'Selected procedure',
    unsureType: 'Type not decided',
    unsureProcedure: 'Procedure not decided',
    resFirstSteps: 'First steps',
    resBasicDocs: 'Basic required documents',
    resAddDocs: 'Documents that may be added for your situation',
    resProcedure: 'Procedure',
    resSources: 'Official sources',
    resNextActions: 'Next actions',
    officialSourceNeedsConfirm: 'Official source needs confirmation',
    firstStepConfirmType: 'Confirm your subcategory is correct',
    firstStepConfirmOffice: 'Confirm the competent immigration office or Korean consulate',
    firstStepPrepareDocs: 'Prepare documents for the procedure you selected',
    docsHandoffNote: 'See the official-source-based detail screen for the specific documents. Tap "View full documents & procedure" below to see the documents for that subcode/procedure.',
    addDocsNote: 'Additional documents may be requested depending on your individual case. Confirm the exact list on the detail screen and with the competent office.',
    sourcesHandoffNote: 'Official sources (manuals/references) are shown on the detail screen. Items without a connected source are marked "Official source needs confirmation".',
    viewFullDetail: 'View full documents & procedure',
    copyChecklist: 'Copy checklist',
    copied: 'Copied',
    copyFail: 'Could not copy',
    safetyNote: 'Additional documents may be requested depending on your individual case and the decision of the competent immigration office or Korean consulate.',
    procStepPrepare: 'Prepare documents',
    procStepReserve: 'Make a reservation if applicable',
    procStepSubmit: 'Submit application',
    procStepReview: 'Review / screening',
    procStepResult: 'Check result',
    procStepFollowup: 'Complete follow-up registration or card issuance if applicable',
    noSubcodesNote: 'This status has no selectable subcategories recorded in the official data, so we go straight to the procedure step.',
    noteE7: 'E-7 requirements and documents depend on the occupation/job category. Confirming the exact job classification may be required, and outcomes cannot be guaranteed.',
    noteG1: 'G-1 requirements and documents vary by reason for stay, and many items are subject to individual review. Confirmation with the competent office is required.',
    noteF5: 'F-5 (permanent residence) has strict criteria and significant individual review. Confirm specific requirements with official sources and the competent office.',
    docChecklistIntro: 'The documents below are from the official manual (reference checklist). They may vary by individual case.',
    docsInManualNote: 'This procedure’s documents are recorded in the official manual. Tap "View full documents & procedure" for the complete list.',
    docsMoreInDetail: 'See the detail screen for the remaining items.',
    sourceManualLabel: 'Manual reference'
  };
  var STR_ZH = {
    eyebrow: '基于官方依据的指引',
    recStartTitle: '符合您情况的手续指引',
    recStartBody: '该居留资格的准备材料和办理方式，会因细分类型、申请手续及当前情况而不同。回答几个问题，即可确认与您情况相近的准备材料和手续。',
    ctaMicrocopy: '约 1 分钟 · 不知道子代码也能开始',
    primaryCtaTpl: '查找符合我情况的 {code} 准备材料',
    secondaryActionsLabel: '用其他方式查找',
    secViewSubcategories: '查看全部细分资格',
    secViewCommonDocs: '查看通用材料',
    secViewProcedure: '查看申请手续',
    secViewSources: '查看官方依据',
    modalAria: '居留资格准备指引',
    close: '关闭',
    back: '← 上一步',
    next: '下一步',
    seeResult: '查看结果',
    restartShort: '重新开始',
    stepWord: '步骤',
    progressAria: '进度',
    optUnsure: '不太清楚',
    stepSubcodeQ: '您更接近哪种类型？',
    stepSubcodeHelp: '请在下列类型中选择最接近的一项（以官方数据为准）。即使不确定，也可以选择“不太清楚”。',
    stepProcedureQ: '您现在需要办理哪项手续？',
    stepProcedureHelp: '仅显示当前数据中可提供指引的手续。',
    resultTitleTpl: '与您情况相近的 {code} 准备路径',
    matchedType: '已选类型',
    matchedProcedure: '已选手续',
    unsureType: '类型未定',
    unsureProcedure: '手续未定',
    resFirstSteps: '首先要做的事',
    resBasicDocs: '基本准备材料',
    resAddDocs: '依您情况可能追加的材料',
    resProcedure: '申请手续',
    resSources: '官方依据',
    resNextActions: '下一步行动',
    officialSourceNeedsConfirm: '需确认官方依据',
    firstStepConfirmType: '确认我的细分类型是否正确',
    firstStepConfirmOffice: '向管辖出入境·外国人机关或驻外公馆确认',
    firstStepPrepareDocs: '准备符合所选手续的材料',
    docsHandoffNote: '具体准备材料请在基于官方依据的详情页确认。点击下方“查看全部准备材料·手续”，即可查看该子代码·手续的材料。',
    addDocsNote: '依个别情况可能要求追加材料。准确清单请在详情页和管辖机关确认。',
    sourcesHandoffNote: '官方依据（手册·出处）会一并显示在详情页。未连接出处的项目将标记为“需确认官方依据”。',
    viewFullDetail: '查看全部准备材料·手续',
    copyChecklist: '复制清单',
    copied: '已复制',
    copyFail: '复制失败',
    safetyNote: '依个别情形及管辖出入境机关或驻外公馆的判断，可能要求追加材料。',
    procStepPrepare: '准备材料',
    procStepReserve: '如需则预约访问',
    procStepSubmit: '提交申请书',
    procStepReview: '审查',
    procStepResult: '确认结果',
    procStepFollowup: '如需则后续登录·发证',
    noSubcodesNote: '该居留资格在官方数据中没有可选择的细分类型，因此将直接进入手续指引。',
    noteE7: 'E-7 的要件和材料会因职业·职务而不同。可能需要确认准确的职业分类，结果无法一概而定。',
    noteG1: 'G-1 的要件和材料因停留事由而异，多数项目属于个别审查·确认对象。需向管辖机关确认。',
    noteF5: 'F-5（永住）的资格标准和手续较为严格，个别审查比重大。具体要件请在官方出处和管辖机关确认。',
    docChecklistIntro: '以下是官方手册中整理的准备材料（参考用清单）。依个别情形可能有所不同。',
    docsInManualNote: '此手续的准备材料已整理在官方手册中。请在“查看全部准备材料·手续”中查看完整清单。',
    docsMoreInDetail: '其他项目请在详情页查看完整内容。',
    sourceManualLabel: '手册依据'
  };
  var STR_JA = {
    eyebrow: '公式の根拠に基づく案内',
    recStartTitle: '状況に合った手続きの案内',
    recStartBody: 'この在留資格は、詳細な類型・申請手続き・現在の状況によって、準備書類や進め方が変わることがあります。いくつかの質問に答えると、ご自身の状況に近い準備書類と手続きを確認できます。',
    ctaMicrocopy: '約1分 · 詳細コードを知らなくても開始できます',
    primaryCtaTpl: '自分の状況に合った {code} の準備書類を探す',
    secondaryActionsLabel: '別の方法で探す',
    secViewSubcategories: 'すべての詳細資格を見る',
    secViewCommonDocs: '共通書類を見る',
    secViewProcedure: '申請手続きを見る',
    secViewSources: '公式の根拠を見る',
    modalAria: '在留資格の準備案内',
    close: '閉じる',
    back: '← 戻る',
    next: '次へ',
    seeResult: '結果を見る',
    restartShort: '最初からやり直す',
    stepWord: 'ステップ',
    progressAria: '進行状況',
    optUnsure: 'よくわかりません',
    stepSubcodeQ: 'どの類型に近いですか？',
    stepSubcodeHelp: '下記の類型のうち最も近いものを選んでください（公式データに基づく）。正確にわからない場合は「よくわかりません」を選べます。',
    stepProcedureQ: '今必要な手続きは何ですか？',
    stepProcedureHelp: '現在のデータで案内できる手続きのみ表示されます。',
    resultTitleTpl: 'あなたに近い {code} の準備経路',
    matchedType: '選択した類型',
    matchedProcedure: '選択した手続き',
    unsureType: '類型未定',
    unsureProcedure: '手続き未定',
    resFirstSteps: 'まず行うこと',
    resBasicDocs: '基本の準備書類',
    resAddDocs: 'ご自身の状況で追加される可能性のある書類',
    resProcedure: '申請手続き',
    resSources: '公式の根拠',
    resNextActions: '次の行動',
    officialSourceNeedsConfirm: '公式の根拠の確認が必要',
    firstStepConfirmType: '自分の詳細類型が正しいか確認する',
    firstStepConfirmOffice: '管轄の出入国・外国人官署または在外公館を確認する',
    firstStepPrepareDocs: '選択した手続きに合わせて書類を準備する',
    docsHandoffNote: '具体的な準備書類は、公式の根拠に基づく詳細画面で確認してください。下の「準備書類・手続きをすべて見る」を押すと、その詳細コード・手続きの書類を確認できます。',
    addDocsNote: '個別の状況により追加書類が求められることがあります。正確なリストは詳細画面と管轄機関で確認してください。',
    sourcesHandoffNote: '公式の根拠（マニュアル・出典）は詳細画面に併せて表示されます。出典が結び付いていない項目は「公式の根拠の確認が必要」と表示されます。',
    viewFullDetail: '準備書類・手続きをすべて見る',
    copyChecklist: 'チェックリストをコピー',
    copied: 'コピーしました',
    copyFail: 'コピーできませんでした',
    safetyNote: '個別の事案、管轄の出入国機関または在外公館の判断により、追加書類が求められることがあります。',
    procStepPrepare: '書類の準備',
    procStepReserve: '必要に応じて訪問予約',
    procStepSubmit: '申請書の提出',
    procStepReview: '審査',
    procStepResult: '結果の確認',
    procStepFollowup: '必要に応じて後続の登録・証の発給',
    noSubcodesNote: 'この在留資格は公式データに整理された選択可能な詳細類型がないため、そのまま手続きの案内に進みます。',
    noteE7: 'E-7 は職種・職務によって要件と書類が異なります。正確な職種分類の確認が必要な場合があり、結果は断定できません。',
    noteG1: 'G-1 は滞在事由ごとに要件と書類が異なり、多くの項目が個別審査・確認の対象です。管轄機関での確認が必要です。',
    noteF5: 'F-5（永住）は資格基準と手続きが厳格で、個別審査の比重が大きいです。具体的な要件は公式の出典と管轄機関で確認してください。',
    docChecklistIntro: '以下は公式マニュアルに整理された準備書類です（参考用チェックリスト）。個別の事案により異なることがあります。',
    docsInManualNote: 'この手続きの準備書類は公式マニュアルに整理されています。「準備書類・手続きをすべて見る」で全リストを確認してください。',
    docsMoreInDetail: 'その他の項目は詳細画面ですべて確認してください。',
    sourceManualLabel: 'マニュアルの根拠'
  };
  var STR_VI = {
    eyebrow: 'Hướng dẫn dựa trên căn cứ chính thức',
    recStartTitle: 'Hướng dẫn thủ tục phù hợp với tình huống của bạn',
    recStartBody: 'Đối với tư cách lưu trú này, giấy tờ cần chuẩn bị và cách thực hiện có thể khác nhau tùy theo loại chi tiết, lộ trình nộp hồ sơ và tình huống hiện tại. Trả lời vài câu hỏi để xác nhận giấy tờ và thủ tục gần với tình huống của bạn.',
    ctaMicrocopy: 'Khoảng 1 phút · Có thể bắt đầu dù không biết mã chi tiết',
    primaryCtaTpl: 'Tìm giấy tờ chuẩn bị {code} phù hợp với tình huống của tôi',
    secondaryActionsLabel: 'Tìm bằng cách khác',
    secViewSubcategories: 'Xem tất cả tư cách chi tiết',
    secViewCommonDocs: 'Xem giấy tờ chung',
    secViewProcedure: 'Xem thủ tục nộp hồ sơ',
    secViewSources: 'Xem căn cứ chính thức',
    modalAria: 'Hướng dẫn chuẩn bị tư cách lưu trú',
    close: 'Đóng',
    back: '← Trước',
    next: 'Tiếp theo',
    seeResult: 'Xem kết quả',
    restartShort: 'Bắt đầu lại',
    stepWord: 'Bước',
    progressAria: 'Tiến độ',
    optUnsure: 'Tôi không chắc',
    stepSubcodeQ: 'Bạn gần với loại nào nhất?',
    stepSubcodeHelp: 'Hãy chọn loại gần nhất trong các loại dưới đây (theo dữ liệu chính thức). Nếu không chắc, bạn có thể chọn "Tôi không chắc".',
    stepProcedureQ: 'Thủ tục bạn cần ngay bây giờ là gì?',
    stepProcedureHelp: 'Chỉ hiển thị các thủ tục mà dữ liệu hiện tại có thể hướng dẫn.',
    resultTitleTpl: 'Lộ trình chuẩn bị {code} gần với bạn',
    matchedType: 'Loại đã chọn',
    matchedProcedure: 'Thủ tục đã chọn',
    unsureType: 'Chưa xác định loại',
    unsureProcedure: 'Chưa xác định thủ tục',
    resFirstSteps: 'Việc cần làm trước tiên',
    resBasicDocs: 'Giấy tờ chuẩn bị cơ bản',
    resAddDocs: 'Giấy tờ có thể được bổ sung theo tình huống của bạn',
    resProcedure: 'Thủ tục nộp hồ sơ',
    resSources: 'Căn cứ chính thức',
    resNextActions: 'Hành động tiếp theo',
    officialSourceNeedsConfirm: 'Cần xác nhận căn cứ chính thức',
    firstStepConfirmType: 'Xác nhận loại chi tiết của tôi có đúng không',
    firstStepConfirmOffice: 'Xác nhận cơ quan xuất nhập cảnh · quản lý người nước ngoài có thẩm quyền hoặc cơ quan đại diện ở nước ngoài',
    firstStepPrepareDocs: 'Chuẩn bị giấy tờ phù hợp với thủ tục đã chọn',
    docsHandoffNote: 'Hãy xác nhận giấy tờ chuẩn bị cụ thể trên màn hình chi tiết dựa trên căn cứ chính thức. Nhấn "Xem toàn bộ giấy tờ · thủ tục" bên dưới để xem giấy tờ của mã chi tiết · thủ tục đó.',
    addDocsNote: 'Tùy từng trường hợp riêng, có thể yêu cầu giấy tờ bổ sung. Hãy xác nhận danh sách chính xác trên màn hình chi tiết và tại cơ quan có thẩm quyền.',
    sourcesHandoffNote: 'Căn cứ chính thức (sổ tay · nguồn) được hiển thị kèm trên màn hình chi tiết. Các mục chưa được liên kết nguồn sẽ được đánh dấu "Cần xác nhận căn cứ chính thức".',
    viewFullDetail: 'Xem toàn bộ giấy tờ · thủ tục',
    copyChecklist: 'Sao chép danh sách kiểm tra',
    copied: 'Đã sao chép',
    copyFail: 'Không thể sao chép',
    safetyNote: 'Tùy từng vụ việc riêng và quyết định của cơ quan xuất nhập cảnh có thẩm quyền hoặc cơ quan đại diện ở nước ngoài, có thể yêu cầu giấy tờ bổ sung.',
    procStepPrepare: 'Chuẩn bị giấy tờ',
    procStepReserve: 'Đặt lịch hẹn nếu cần',
    procStepSubmit: 'Nộp đơn',
    procStepReview: 'Thẩm định',
    procStepResult: 'Kiểm tra kết quả',
    procStepFollowup: 'Đăng ký tiếp theo · cấp thẻ nếu cần',
    noSubcodesNote: 'Tư cách lưu trú này không có loại chi tiết nào có thể chọn được ghi nhận trong dữ liệu chính thức, nên sẽ chuyển thẳng đến bước hướng dẫn thủ tục.',
    noteE7: 'Yêu cầu và giấy tờ của E-7 khác nhau tùy theo ngành nghề · công việc. Có thể cần xác nhận phân loại ngành nghề chính xác, và kết quả không thể khẳng định chắc chắn.',
    noteG1: 'Yêu cầu và giấy tờ của G-1 khác nhau tùy theo lý do lưu trú, và nhiều mục thuộc đối tượng thẩm định · xác nhận riêng. Cần xác nhận với cơ quan có thẩm quyền.',
    noteF5: 'F-5 (thường trú) có tiêu chuẩn tư cách và thủ tục khắt khe, tỷ trọng thẩm định riêng lớn. Hãy xác nhận yêu cầu cụ thể tại nguồn chính thức và cơ quan có thẩm quyền.',
    docChecklistIntro: 'Dưới đây là giấy tờ chuẩn bị được tổng hợp trong sổ tay chính thức (danh sách kiểm tra để tham khảo). Có thể khác nhau tùy từng trường hợp riêng.',
    docsInManualNote: 'Giấy tờ chuẩn bị của thủ tục này được tổng hợp trong sổ tay chính thức. Hãy xem danh sách đầy đủ trong "Xem toàn bộ giấy tờ · thủ tục".',
    docsMoreInDetail: 'Các mục khác hãy xem đầy đủ trên màn hình chi tiết.',
    sourceManualLabel: 'Căn cứ sổ tay'
  };
  var STR_TL = {
    eyebrow: 'Gabay batay sa opisyal na pinagbatayan',
    recStartTitle: 'Gabay sa proseso na akma sa iyong sitwasyon',
    recStartBody: 'Para sa status na ito, maaaring mag-iba ang mga dokumentong ihahanda at ang paraan ng pagsasagawa depende sa detalyadong uri, ruta ng aplikasyon, at kasalukuyang sitwasyon. Sagutin ang ilang tanong para matiyak ang mga dokumento at proseso na pinakamalapit sa iyong sitwasyon.',
    ctaMicrocopy: 'Mga 1 minuto · Puwedeng simulan kahit hindi alam ang subcode',
    primaryCtaTpl: 'Hanapin ang mga {code} na dokumento na akma sa aking sitwasyon',
    secondaryActionsLabel: 'Maghanap sa ibang paraan',
    secViewSubcategories: 'Tingnan ang lahat ng detalyadong kategorya',
    secViewCommonDocs: 'Tingnan ang karaniwang mga dokumento',
    secViewProcedure: 'Tingnan ang proseso ng aplikasyon',
    secViewSources: 'Tingnan ang opisyal na pinagbatayan',
    modalAria: 'Gabay sa paghahanda ng status',
    close: 'Isara',
    back: '← Bumalik',
    next: 'Susunod',
    seeResult: 'Tingnan ang resulta',
    restartShort: 'Magsimula muli',
    stepWord: 'Hakbang',
    progressAria: 'Pagsulong',
    optUnsure: 'Hindi ako sigurado',
    stepSubcodeQ: 'Aling uri ang pinakamalapit sa iyo?',
    stepSubcodeHelp: 'Piliin ang uri na pinakamalapit sa iyong sitwasyon mula sa mga nasa ibaba (batay sa opisyal na datos). Hindi sigurado? Piliin lamang ang "Hindi ako sigurado".',
    stepProcedureQ: 'Anong proseso ang kailangan mo ngayon?',
    stepProcedureHelp: 'Ang mga proseso lamang na maaaring gabayan ng kasalukuyang datos ang ipinapakita.',
    resultTitleTpl: 'Ruta ng paghahanda ng {code} na malapit sa iyo',
    matchedType: 'Napiling uri',
    matchedProcedure: 'Napiling proseso',
    unsureType: 'Hindi pa natutukoy ang uri',
    unsureProcedure: 'Hindi pa natutukoy ang proseso',
    resFirstSteps: 'Mga unang gagawin',
    resBasicDocs: 'Mga batayang dokumentong ihahanda',
    resAddDocs: 'Mga dokumentong maaaring idagdag para sa iyong sitwasyon',
    resProcedure: 'Proseso ng aplikasyon',
    resSources: 'Opisyal na pinagbatayan',
    resNextActions: 'Mga susunod na hakbang',
    officialSourceNeedsConfirm: 'Kailangang kumpirmahin ang opisyal na pinagbatayan',
    firstStepConfirmType: 'Kumpirmahin kung tama ang iyong detalyadong uri',
    firstStepConfirmOffice: 'Kumpirmahin ang may hurisdiksyong tanggapan ng imigrasyon · dayuhan o ang embahada/konsulado ng Korea',
    firstStepPrepareDocs: 'Ihanda ang mga dokumentong akma sa napiling proseso',
    docsHandoffNote: 'Tingnan ang mga tiyak na dokumento sa detalyadong screen na batay sa opisyal na pinagbatayan. Pindutin ang "Tingnan ang lahat ng dokumento · proseso" sa ibaba para makita ang mga dokumento para sa subcode · proseso na iyon.',
    addDocsNote: 'Maaaring humingi ng karagdagang dokumento depende sa indibidwal na kaso. Kumpirmahin ang tamang listahan sa detalyadong screen at sa tanggapang may hurisdiksyon.',
    sourcesHandoffNote: 'Ang opisyal na pinagbatayan (manwal · pinagmulan) ay ipinapakita kasama sa detalyadong screen. Ang mga item na walang nakaugnay na pinagmulan ay minamarkahan ng "Kailangang kumpirmahin ang opisyal na pinagbatayan".',
    viewFullDetail: 'Tingnan ang lahat ng dokumento · proseso',
    copyChecklist: 'Kopyahin ang checklist',
    copied: 'Nakopya',
    copyFail: 'Hindi makopya',
    safetyNote: 'Depende sa indibidwal na kaso at sa pasya ng may hurisdiksyong tanggapan ng imigrasyon o embahada/konsulado ng Korea, maaaring humingi ng karagdagang dokumento.',
    procStepPrepare: 'Maghanda ng dokumento',
    procStepReserve: 'Magpa-reserba ng bisita kung kinakailangan',
    procStepSubmit: 'Isumite ang aplikasyon',
    procStepReview: 'Pagsusuri',
    procStepResult: 'Tingnan ang resulta',
    procStepFollowup: 'Kumpletuhin ang susunod na rehistro · pag-isyu ng card kung kinakailangan',
    noSubcodesNote: 'Ang status na ito ay walang mapipiling detalyadong uri na nakatala sa opisyal na datos, kaya diretso na tayo sa hakbang ng proseso.',
    noteE7: 'Ang mga kinakailangan at dokumento ng E-7 ay depende sa trabaho · tungkulin. Maaaring kailanganin ang pagkumpirma ng tamang klasipikasyon ng trabaho, at hindi matitiyak ang resulta.',
    noteG1: 'Ang mga kinakailangan at dokumento ng G-1 ay nag-iiba ayon sa dahilan ng pananatili, at maraming item ang sasailalim sa indibidwal na pagsusuri · pagkumpirma. Kailangang kumpirmahin sa tanggapang may hurisdiksyon.',
    noteF5: 'Ang F-5 (permanenteng paninirahan) ay may mahigpit na pamantayan at proseso, na may malaking bahagi ng indibidwal na pagsusuri. Kumpirmahin ang mga tiyak na kinakailangan sa opisyal na pinagmulan at sa tanggapang may hurisdiksyon.',
    docChecklistIntro: 'Nasa ibaba ang mga dokumentong ihahanda na nasa opisyal na manwal (checklist para sa sanggunian). Maaaring mag-iba ayon sa indibidwal na kaso.',
    docsInManualNote: 'Ang mga dokumento ng prosesong ito ay nakatala sa opisyal na manwal. Pindutin ang "Tingnan ang lahat ng dokumento · proseso" para sa kumpletong listahan.',
    docsMoreInDetail: 'Tingnan ang iba pang item nang buo sa detalyadong screen.',
    sourceManualLabel: 'Pinagbatayan ng manwal'
  };
  var STR_ID = {
    eyebrow: 'Panduan berdasarkan dasar resmi',
    recStartTitle: 'Panduan prosedur sesuai situasi Anda',
    recStartBody: 'Untuk status izin tinggal ini, dokumen yang perlu disiapkan dan cara pengurusannya dapat berbeda tergantung jenis rinci, jalur pengajuan, dan situasi saat ini. Jawab beberapa pertanyaan untuk mengetahui dokumen dan prosedur yang paling sesuai dengan situasi Anda.',
    ctaMicrocopy: 'Sekitar 1 menit · Bisa dimulai meski tidak tahu subkode',
    primaryCtaTpl: 'Cari dokumen persiapan {code} yang sesuai situasi saya',
    secondaryActionsLabel: 'Cari dengan cara lain',
    secViewSubcategories: 'Lihat semua jenis rinci',
    secViewCommonDocs: 'Lihat dokumen umum',
    secViewProcedure: 'Lihat prosedur pengajuan',
    secViewSources: 'Lihat dasar resmi',
    modalAria: 'Panduan persiapan status izin tinggal',
    close: 'Tutup',
    back: '← Kembali',
    next: 'Berikutnya',
    seeResult: 'Lihat hasil',
    restartShort: 'Mulai ulang',
    stepWord: 'Langkah',
    progressAria: 'Kemajuan',
    optUnsure: 'Saya tidak yakin',
    stepSubcodeQ: 'Jenis mana yang paling mendekati Anda?',
    stepSubcodeHelp: 'Pilih jenis yang paling mendekati situasi Anda dari daftar di bawah (berdasarkan data resmi). Tidak yakin? Cukup pilih "Saya tidak yakin".',
    stepProcedureQ: 'Prosedur apa yang Anda perlukan sekarang?',
    stepProcedureHelp: 'Hanya prosedur yang dapat dipandu oleh data saat ini yang ditampilkan.',
    resultTitleTpl: 'Jalur persiapan {code} yang mendekati Anda',
    matchedType: 'Jenis yang dipilih',
    matchedProcedure: 'Prosedur yang dipilih',
    unsureType: 'Jenis belum ditentukan',
    unsureProcedure: 'Prosedur belum ditentukan',
    resFirstSteps: 'Yang harus dilakukan lebih dulu',
    resBasicDocs: 'Dokumen persiapan dasar',
    resAddDocs: 'Dokumen yang mungkin ditambahkan untuk situasi Anda',
    resProcedure: 'Prosedur pengajuan',
    resSources: 'Dasar resmi',
    resNextActions: 'Tindakan berikutnya',
    officialSourceNeedsConfirm: 'Dasar resmi perlu dikonfirmasi',
    firstStepConfirmType: 'Pastikan jenis rinci saya sudah benar',
    firstStepConfirmOffice: 'Konfirmasi kantor imigrasi · orang asing yang berwenang atau perwakilan Korea di luar negeri',
    firstStepPrepareDocs: 'Siapkan dokumen sesuai prosedur yang dipilih',
    docsHandoffNote: 'Periksa dokumen persiapan yang spesifik pada layar detail berbasis dasar resmi. Tekan "Lihat seluruh dokumen · prosedur" di bawah untuk melihat dokumen subkode · prosedur tersebut.',
    addDocsNote: 'Dokumen tambahan mungkin diminta tergantung kasus masing-masing. Konfirmasi daftar yang tepat pada layar detail dan di kantor yang berwenang.',
    sourcesHandoffNote: 'Dasar resmi (manual · sumber) ditampilkan bersama pada layar detail. Item tanpa sumber yang terhubung ditandai "Dasar resmi perlu dikonfirmasi".',
    viewFullDetail: 'Lihat seluruh dokumen · prosedur',
    copyChecklist: 'Salin daftar periksa',
    copied: 'Tersalin',
    copyFail: 'Gagal menyalin',
    safetyNote: 'Tergantung kasus masing-masing dan keputusan kantor imigrasi yang berwenang atau perwakilan Korea di luar negeri, dokumen tambahan mungkin diminta.',
    procStepPrepare: 'Menyiapkan dokumen',
    procStepReserve: 'Membuat reservasi jika perlu',
    procStepSubmit: 'Mengajukan permohonan',
    procStepReview: 'Penilaian',
    procStepResult: 'Memeriksa hasil',
    procStepFollowup: 'Registrasi lanjutan · penerbitan kartu jika perlu',
    noSubcodesNote: 'Status ini tidak memiliki jenis rinci yang dapat dipilih dalam data resmi, sehingga langsung menuju langkah prosedur.',
    noteE7: 'Persyaratan dan dokumen E-7 berbeda menurut jenis pekerjaan · jabatan. Konfirmasi klasifikasi pekerjaan yang tepat mungkin diperlukan, dan hasilnya tidak dapat dipastikan.',
    noteG1: 'Persyaratan dan dokumen G-1 berbeda menurut alasan tinggal, dan banyak item merupakan objek penilaian · konfirmasi individual. Konfirmasi dengan kantor yang berwenang diperlukan.',
    noteF5: 'F-5 (izin tinggal tetap) memiliki kriteria dan prosedur yang ketat dengan porsi penilaian individual yang besar. Konfirmasi persyaratan spesifik pada sumber resmi dan kantor yang berwenang.',
    docChecklistIntro: 'Di bawah ini adalah dokumen persiapan yang dirangkum dalam manual resmi (daftar periksa untuk referensi). Dapat berbeda menurut kasus masing-masing.',
    docsInManualNote: 'Dokumen prosedur ini dirangkum dalam manual resmi. Tekan "Lihat seluruh dokumen · prosedur" untuk daftar lengkap.',
    docsMoreInDetail: 'Lihat item lainnya secara lengkap pada layar detail.',
    sourceManualLabel: 'Dasar manual'
  };
  var STR_RU = {
    eyebrow: 'Руководство на основе официальных источников',
    recStartTitle: 'Пошаговое руководство для вашей ситуации',
    recStartBody: 'Для этого статуса пребывания документы и порядок оформления могут различаться в зависимости от подтипа, пути подачи заявления и текущей ситуации. Ответьте на несколько вопросов, чтобы узнать список документов и процедуру, наиболее близкие к вашей ситуации.',
    ctaMicrocopy: 'Около 1 минуты · Можно начать, даже не зная субкод',
    primaryCtaTpl: 'Найти документы {code} для моей ситуации',
    secondaryActionsLabel: 'Искать другим способом',
    secViewSubcategories: 'Посмотреть все подкатегории',
    secViewCommonDocs: 'Посмотреть общие документы',
    secViewProcedure: 'Посмотреть процедуру подачи',
    secViewSources: 'Посмотреть официальные источники',
    modalAria: 'Руководство по подготовке к статусу пребывания',
    close: 'Закрыть',
    back: '← Назад',
    next: 'Далее',
    seeResult: 'Посмотреть результат',
    restartShort: 'Начать заново',
    stepWord: 'Шаг',
    progressAria: 'Прогресс',
    optUnsure: 'Я не уверен(а)',
    stepSubcodeQ: 'Какой тип ближе всего к вашему?',
    stepSubcodeHelp: 'Выберите наиболее близкий тип из перечисленных ниже (по официальным данным). Не уверены? Просто выберите «Я не уверен(а)».',
    stepProcedureQ: 'Какая процедура вам нужна сейчас?',
    stepProcedureHelp: 'Показаны только процедуры, по которым текущие данные могут дать руководство.',
    resultTitleTpl: 'Близкий вам путь подготовки {code}',
    matchedType: 'Выбранный тип',
    matchedProcedure: 'Выбранная процедура',
    unsureType: 'Тип не определён',
    unsureProcedure: 'Процедура не определена',
    resFirstSteps: 'Что сделать в первую очередь',
    resBasicDocs: 'Основные документы для подготовки',
    resAddDocs: 'Документы, которые могут потребоваться в вашей ситуации',
    resProcedure: 'Процедура подачи',
    resSources: 'Официальные источники',
    resNextActions: 'Дальнейшие действия',
    officialSourceNeedsConfirm: 'Требуется подтверждение официального источника',
    firstStepConfirmType: 'Проверьте, верно ли определён ваш подтип',
    firstStepConfirmOffice: 'Уточните компетентный орган иммиграции · по делам иностранцев или зарубежное представительство Кореи',
    firstStepPrepareDocs: 'Подготовьте документы для выбранной процедуры',
    docsHandoffNote: 'Конкретные документы смотрите на экране детальной информации, основанной на официальных источниках. Нажмите «Посмотреть все документы · процедуру» ниже, чтобы увидеть документы для этого субкода · процедуры.',
    addDocsNote: 'В зависимости от конкретного случая могут запросить дополнительные документы. Уточните точный список на экране детальной информации и в компетентном органе.',
    sourcesHandoffNote: 'Официальные источники (руководства · ссылки) отображаются вместе на экране детальной информации. Пункты без привязанного источника помечаются как «Требуется подтверждение официального источника».',
    viewFullDetail: 'Посмотреть все документы · процедуру',
    copyChecklist: 'Копировать чек-лист',
    copied: 'Скопировано',
    copyFail: 'Не удалось скопировать',
    safetyNote: 'В зависимости от конкретного дела и решения компетентного органа иммиграции или зарубежного представительства Кореи могут запросить дополнительные документы.',
    procStepPrepare: 'Подготовка документов',
    procStepReserve: 'При необходимости запись на визит',
    procStepSubmit: 'Подача заявления',
    procStepReview: 'Рассмотрение',
    procStepResult: 'Проверка результата',
    procStepFollowup: 'При необходимости последующая регистрация · выдача удостоверения',
    noSubcodesNote: 'Для этого статуса в официальных данных нет выбираемых подтипов, поэтому переходим сразу к шагу процедуры.',
    noteE7: 'Требования и документы для E-7 зависят от профессии · должности. Может потребоваться подтверждение точной классификации профессии, и результат нельзя гарантировать.',
    noteG1: 'Требования и документы для G-1 различаются по основанию пребывания, и многие пункты подлежат индивидуальному рассмотрению · подтверждению. Необходимо уточнение в компетентном органе.',
    noteF5: 'F-5 (постоянное проживание) имеет строгие критерии и процедуру с большой долей индивидуального рассмотрения. Уточните конкретные требования в официальных источниках и компетентном органе.',
    docChecklistIntro: 'Ниже приведены документы для подготовки из официального руководства (справочный чек-лист). Могут различаться в зависимости от конкретного случая.',
    docsInManualNote: 'Документы для этой процедуры собраны в официальном руководстве. Нажмите «Посмотреть все документы · процедуру», чтобы увидеть полный список.',
    docsMoreInDetail: 'Остальные пункты смотрите полностью на экране детальной информации.',
    sourceManualLabel: 'Основание из руководства'
  };
  var STR_FR = {
    eyebrow: 'Guide fondé sur des sources officielles',
    recStartTitle: 'Guide des démarches adapté à votre situation',
    recStartBody: 'Pour ce statut de séjour, les documents à préparer et la marche à suivre peuvent varier selon le sous-type, la voie de demande et votre situation actuelle. Répondez à quelques questions pour connaître les documents et la procédure les plus proches de votre situation.',
    ctaMicrocopy: 'Environ 1 minute · Vous pouvez commencer sans connaître le sous-code',
    primaryCtaTpl: 'Trouver les documents {code} adaptés à ma situation',
    secondaryActionsLabel: 'Chercher autrement',
    secViewSubcategories: 'Voir toutes les sous-catégories',
    secViewCommonDocs: 'Voir les documents communs',
    secViewProcedure: 'Voir la procédure de demande',
    secViewSources: 'Voir les sources officielles',
    modalAria: 'Guide de préparation du statut de séjour',
    close: 'Fermer',
    back: '← Précédent',
    next: 'Suivant',
    seeResult: 'Voir le résultat',
    restartShort: 'Recommencer',
    stepWord: 'Étape',
    progressAria: 'Progression',
    optUnsure: 'Je ne suis pas sûr(e)',
    stepSubcodeQ: 'De quel type êtes-vous le plus proche ?',
    stepSubcodeHelp: 'Choisissez le type le plus proche de votre situation parmi ceux ci-dessous (selon les données officielles). Pas sûr ? Choisissez simplement « Je ne suis pas sûr(e) ».',
    stepProcedureQ: 'De quelle procédure avez-vous besoin maintenant ?',
    stepProcedureHelp: 'Seules les procédures que les données actuelles peuvent guider sont affichées.',
    resultTitleTpl: 'Votre parcours de préparation {code} probable',
    matchedType: 'Type sélectionné',
    matchedProcedure: 'Procédure sélectionnée',
    unsureType: 'Type non déterminé',
    unsureProcedure: 'Procédure non déterminée',
    resFirstSteps: 'Premières démarches',
    resBasicDocs: 'Documents de base à préparer',
    resAddDocs: 'Documents pouvant être ajoutés selon votre situation',
    resProcedure: 'Procédure de demande',
    resSources: 'Sources officielles',
    resNextActions: 'Prochaines actions',
    officialSourceNeedsConfirm: 'Source officielle à confirmer',
    firstStepConfirmType: 'Confirmer que votre sous-type est correct',
    firstStepConfirmOffice: 'Confirmer le service d’immigration · des étrangers compétent ou la représentation coréenne à l’étranger',
    firstStepPrepareDocs: 'Préparer les documents correspondant à la procédure choisie',
    docsHandoffNote: 'Consultez les documents précis sur l’écran de détail fondé sur les sources officielles. Appuyez sur « Voir tous les documents · la procédure » ci-dessous pour voir les documents de ce sous-code · de cette procédure.',
    addDocsNote: 'Des documents supplémentaires peuvent être demandés selon votre cas individuel. Confirmez la liste exacte sur l’écran de détail et auprès du service compétent.',
    sourcesHandoffNote: 'Les sources officielles (manuels · références) sont affichées sur l’écran de détail. Les éléments sans source rattachée sont marqués « Source officielle à confirmer ».',
    viewFullDetail: 'Voir tous les documents · la procédure',
    copyChecklist: 'Copier la liste de contrôle',
    copied: 'Copié',
    copyFail: 'Impossible de copier',
    safetyNote: 'Selon votre cas individuel et la décision du service d’immigration compétent ou de la représentation coréenne à l’étranger, des documents supplémentaires peuvent être demandés.',
    procStepPrepare: 'Préparer les documents',
    procStepReserve: 'Prendre rendez-vous si nécessaire',
    procStepSubmit: 'Déposer la demande',
    procStepReview: 'Examen',
    procStepResult: 'Vérifier le résultat',
    procStepFollowup: 'Effectuer l’enregistrement · la délivrance de la carte si nécessaire',
    noSubcodesNote: 'Ce statut n’a aucun sous-type sélectionnable enregistré dans les données officielles ; nous passons donc directement à l’étape de la procédure.',
    noteE7: 'Les exigences et les documents de l’E-7 dépendent du métier · de la fonction. La confirmation de la classification professionnelle exacte peut être requise, et le résultat ne peut être garanti.',
    noteG1: 'Les exigences et les documents du G-1 varient selon le motif de séjour, et de nombreux éléments font l’objet d’un examen · d’une confirmation individuels. Une confirmation auprès du service compétent est requise.',
    noteF5: 'Le F-5 (résidence permanente) a des critères et une procédure stricts, avec une part importante d’examen individuel. Confirmez les exigences précises auprès des sources officielles et du service compétent.',
    docChecklistIntro: 'Vous trouverez ci-dessous les documents à préparer figurant dans le manuel officiel (liste de contrôle à titre indicatif). Ils peuvent varier selon votre cas individuel.',
    docsInManualNote: 'Les documents de cette procédure figurent dans le manuel officiel. Appuyez sur « Voir tous les documents · la procédure » pour la liste complète.',
    docsMoreInDetail: 'Consultez les autres éléments en entier sur l’écran de détail.',
    sourceManualLabel: 'Référence du manuel'
  };
  var STR_ES = {
    eyebrow: 'Guía basada en fuentes oficiales',
    recStartTitle: 'Guía de trámites adaptada a su situación',
    recStartBody: 'Para este estatus de estancia, los documentos a preparar y la forma de tramitarlos pueden variar según el subtipo, la vía de solicitud y su situación actual. Responda algunas preguntas para conocer los documentos y el trámite más cercanos a su situación.',
    ctaMicrocopy: 'Aprox. 1 minuto · Puede empezar aunque no conozca el subcódigo',
    primaryCtaTpl: 'Buscar los documentos {code} adecuados a mi situación',
    secondaryActionsLabel: 'Buscar de otra manera',
    secViewSubcategories: 'Ver todas las subcategorías',
    secViewCommonDocs: 'Ver documentos comunes',
    secViewProcedure: 'Ver el trámite de solicitud',
    secViewSources: 'Ver las fuentes oficiales',
    modalAria: 'Guía de preparación del estatus de estancia',
    close: 'Cerrar',
    back: '← Atrás',
    next: 'Siguiente',
    seeResult: 'Ver el resultado',
    restartShort: 'Reiniciar',
    stepWord: 'Paso',
    progressAria: 'Progreso',
    optUnsure: 'No estoy seguro/a',
    stepSubcodeQ: '¿A qué tipo se parece más?',
    stepSubcodeHelp: 'Elija el tipo más cercano a su situación entre los siguientes (según los datos oficiales). ¿No está seguro? Solo elija «No estoy seguro/a».',
    stepProcedureQ: '¿Qué trámite necesita ahora?',
    stepProcedureHelp: 'Solo se muestran los trámites que los datos actuales pueden guiar.',
    resultTitleTpl: 'Su posible ruta de preparación de {code}',
    matchedType: 'Tipo seleccionado',
    matchedProcedure: 'Trámite seleccionado',
    unsureType: 'Tipo sin determinar',
    unsureProcedure: 'Trámite sin determinar',
    resFirstSteps: 'Primeros pasos',
    resBasicDocs: 'Documentos básicos a preparar',
    resAddDocs: 'Documentos que pueden añadirse según su situación',
    resProcedure: 'Trámite de solicitud',
    resSources: 'Fuentes oficiales',
    resNextActions: 'Próximas acciones',
    officialSourceNeedsConfirm: 'Fuente oficial pendiente de confirmar',
    firstStepConfirmType: 'Confirmar que su subtipo es correcto',
    firstStepConfirmOffice: 'Confirmar la oficina de inmigración · extranjería competente o la representación coreana en el extranjero',
    firstStepPrepareDocs: 'Preparar los documentos para el trámite seleccionado',
    docsHandoffNote: 'Consulte los documentos concretos en la pantalla de detalle basada en fuentes oficiales. Pulse «Ver todos los documentos · el trámite» abajo para ver los documentos de ese subcódigo · trámite.',
    addDocsNote: 'Pueden solicitarse documentos adicionales según su caso individual. Confirme la lista exacta en la pantalla de detalle y en la oficina competente.',
    sourcesHandoffNote: 'Las fuentes oficiales (manuales · referencias) se muestran en la pantalla de detalle. Los elementos sin fuente vinculada se marcan como «Fuente oficial pendiente de confirmar».',
    viewFullDetail: 'Ver todos los documentos · el trámite',
    copyChecklist: 'Copiar la lista de verificación',
    copied: 'Copiado',
    copyFail: 'No se pudo copiar',
    safetyNote: 'Según su caso individual y la decisión de la oficina de inmigración competente o de la representación coreana en el extranjero, pueden solicitarse documentos adicionales.',
    procStepPrepare: 'Preparar los documentos',
    procStepReserve: 'Reservar una cita si corresponde',
    procStepSubmit: 'Presentar la solicitud',
    procStepReview: 'Evaluación',
    procStepResult: 'Comprobar el resultado',
    procStepFollowup: 'Completar el registro · la expedición de la tarjeta si corresponde',
    noSubcodesNote: 'Este estatus no tiene subtipos seleccionables registrados en los datos oficiales, por lo que pasamos directamente al paso del trámite.',
    noteE7: 'Los requisitos y documentos del E-7 dependen de la ocupación · función. Puede requerirse confirmar la clasificación ocupacional exacta, y el resultado no puede garantizarse.',
    noteG1: 'Los requisitos y documentos del G-1 varían según el motivo de estancia, y muchos elementos están sujetos a evaluación · confirmación individual. Es necesaria la confirmación en la oficina competente.',
    noteF5: 'El F-5 (residencia permanente) tiene criterios y un trámite estrictos, con un peso importante de la evaluación individual. Confirme los requisitos concretos en las fuentes oficiales y en la oficina competente.',
    docChecklistIntro: 'A continuación se muestran los documentos a preparar recogidos en el manual oficial (lista de verificación de referencia). Pueden variar según su caso individual.',
    docsInManualNote: 'Los documentos de este trámite están recogidos en el manual oficial. Pulse «Ver todos los documentos · el trámite» para la lista completa.',
    docsMoreInDetail: 'Consulte los demás elementos por completo en la pantalla de detalle.',
    sourceManualLabel: 'Referencia del manual'
  };
  var STR_AR = {
    eyebrow: 'إرشاد مبني على مصادر رسمية',
    recStartTitle: 'إرشاد الإجراءات المناسب لوضعك',
    recStartBody: 'بالنسبة لهذه الإقامة، قد تختلف المستندات المطلوبة وطريقة الإجراء حسب النوع التفصيلي ومسار التقديم والوضع الحالي. أجب عن بعض الأسئلة لتتعرف على المستندات والإجراءات الأقرب إلى وضعك.',
    ctaMicrocopy: 'نحو دقيقة واحدة · يمكنك البدء حتى دون معرفة الرمز الفرعي',
    primaryCtaTpl: 'البحث عن مستندات {code} المناسبة لوضعي',
    secondaryActionsLabel: 'البحث بطريقة أخرى',
    secViewSubcategories: 'عرض جميع الأنواع التفصيلية',
    secViewCommonDocs: 'عرض المستندات المشتركة',
    secViewProcedure: 'عرض إجراء التقديم',
    secViewSources: 'عرض المصادر الرسمية',
    modalAria: 'إرشاد تجهيز الإقامة',
    close: 'إغلاق',
    back: '→ رجوع',
    next: 'التالي',
    seeResult: 'عرض النتيجة',
    restartShort: 'البدء من جديد',
    stepWord: 'خطوة',
    progressAria: 'التقدم',
    optUnsure: 'لست متأكداً',
    stepSubcodeQ: 'أي نوع أقرب إلى حالتك؟',
    stepSubcodeHelp: 'اختر النوع الأقرب إلى وضعك من الأنواع أدناه (وفقاً للبيانات الرسمية). إن لم تكن متأكداً، اختر "لست متأكداً".',
    stepProcedureQ: 'ما الإجراء الذي تحتاجه الآن؟',
    stepProcedureHelp: 'تُعرض فقط الإجراءات التي يمكن للبيانات الحالية إرشادك بشأنها.',
    resultTitleTpl: 'مسار تجهيز {code} الأقرب إليك',
    matchedType: 'النوع المختار',
    matchedProcedure: 'الإجراء المختار',
    unsureType: 'النوع غير محدد',
    unsureProcedure: 'الإجراء غير محدد',
    resFirstSteps: 'ما يجب فعله أولاً',
    resBasicDocs: 'المستندات الأساسية المطلوبة',
    resAddDocs: 'مستندات قد تُضاف حسب وضعك',
    resProcedure: 'إجراء التقديم',
    resSources: 'المصادر الرسمية',
    resNextActions: 'الإجراءات التالية',
    officialSourceNeedsConfirm: 'يلزم التحقق من المصدر الرسمي',
    firstStepConfirmType: 'تحقق من صحة نوعك التفصيلي',
    firstStepConfirmOffice: 'تحقق من مكتب الهجرة · شؤون الأجانب المختص أو البعثة الكورية في الخارج',
    firstStepPrepareDocs: 'جهّز المستندات المناسبة للإجراء المختار',
    docsHandoffNote: 'تحقق من المستندات المحددة في شاشة التفاصيل المبنية على المصادر الرسمية. اضغط "عرض جميع المستندات · الإجراءات" أدناه لعرض مستندات ذلك الرمز الفرعي · الإجراء.',
    addDocsNote: 'قد تُطلب مستندات إضافية حسب كل حالة على حدة. تحقق من القائمة الدقيقة في شاشة التفاصيل ولدى الجهة المختصة.',
    sourcesHandoffNote: 'تُعرض المصادر الرسمية (الأدلة · المراجع) معاً في شاشة التفاصيل. تُوسم العناصر غير المرتبطة بمصدر بعبارة "يلزم التحقق من المصدر الرسمي".',
    viewFullDetail: 'عرض جميع المستندات · الإجراءات',
    copyChecklist: 'نسخ قائمة التحقق',
    copied: 'تم النسخ',
    copyFail: 'تعذّر النسخ',
    safetyNote: 'حسب كل حالة على حدة وقرار مكتب الهجرة المختص أو البعثة الكورية في الخارج، قد تُطلب مستندات إضافية.',
    procStepPrepare: 'تجهيز المستندات',
    procStepReserve: 'حجز زيارة عند الحاجة',
    procStepSubmit: 'تقديم الطلب',
    procStepReview: 'الفحص',
    procStepResult: 'التحقق من النتيجة',
    procStepFollowup: 'استكمال التسجيل · إصدار البطاقة عند الحاجة',
    noSubcodesNote: 'لا تتضمن هذه الإقامة أنواعاً تفصيلية قابلة للاختيار مسجلة في البيانات الرسمية، لذا ننتقل مباشرة إلى خطوة الإجراء.',
    noteE7: 'تختلف متطلبات ومستندات E-7 حسب المهنة · الوظيفة. قد يلزم التحقق من التصنيف المهني الدقيق، ولا يمكن الجزم بالنتيجة.',
    noteG1: 'تختلف متطلبات ومستندات G-1 حسب سبب الإقامة، والكثير من البنود يخضع للفحص · التحقق الفردي. يلزم التحقق لدى الجهة المختصة.',
    noteF5: 'يتميز F-5 (الإقامة الدائمة) بمعايير وإجراءات صارمة ونسبة كبيرة من الفحص الفردي. تحقق من المتطلبات المحددة من المصادر الرسمية ولدى الجهة المختصة.',
    docChecklistIntro: 'فيما يلي المستندات المطلوبة المنظمة في الدليل الرسمي (قائمة تحقق للاسترشاد). قد تختلف حسب كل حالة على حدة.',
    docsInManualNote: 'مستندات هذا الإجراء منظمة في الدليل الرسمي. اضغط "عرض جميع المستندات · الإجراءات" للحصول على القائمة الكاملة.',
    docsMoreInDetail: 'اطّلع على بقية البنود كاملةً في شاشة التفاصيل.',
    sourceManualLabel: 'مرجع الدليل'
  };
  var STR_DE = {
    eyebrow: 'Anleitung auf Basis offizieller Quellen',
    recStartTitle: 'Verfahrensanleitung passend zu Ihrer Situation',
    recStartBody: 'Bei diesem Aufenthaltstitel können die vorzubereitenden Unterlagen und der Ablauf je nach Untertyp, Antragsweg und aktueller Situation unterschiedlich sein. Beantworten Sie einige Fragen, um die Unterlagen und das Verfahren zu erfahren, die Ihrer Situation am nächsten kommen.',
    ctaMicrocopy: 'Etwa 1 Minute · Beginn auch ohne Kenntnis des Subcodes möglich',
    primaryCtaTpl: 'Passende {code}-Unterlagen für meine Situation finden',
    secondaryActionsLabel: 'Auf andere Weise suchen',
    secViewSubcategories: 'Alle Unterkategorien ansehen',
    secViewCommonDocs: 'Gemeinsame Unterlagen ansehen',
    secViewProcedure: 'Antragsverfahren ansehen',
    secViewSources: 'Offizielle Quellen ansehen',
    modalAria: 'Anleitung zur Vorbereitung des Aufenthaltstitels',
    close: 'Schließen',
    back: '← Zurück',
    next: 'Weiter',
    seeResult: 'Ergebnis ansehen',
    restartShort: 'Neu starten',
    stepWord: 'Schritt',
    progressAria: 'Fortschritt',
    optUnsure: 'Ich bin nicht sicher',
    stepSubcodeQ: 'Welchem Typ kommen Sie am nächsten?',
    stepSubcodeHelp: 'Wählen Sie den Typ, der Ihrer Situation am nächsten kommt, aus den folgenden aus (gemäß den offiziellen Daten). Nicht sicher? Wählen Sie einfach „Ich bin nicht sicher“.',
    stepProcedureQ: 'Welches Verfahren benötigen Sie jetzt?',
    stepProcedureHelp: 'Es werden nur Verfahren angezeigt, zu denen die aktuellen Daten eine Anleitung geben können.',
    resultTitleTpl: 'Ihr wahrscheinlicher {code}-Vorbereitungsweg',
    matchedType: 'Ausgewählter Typ',
    matchedProcedure: 'Ausgewähltes Verfahren',
    unsureType: 'Typ nicht festgelegt',
    unsureProcedure: 'Verfahren nicht festgelegt',
    resFirstSteps: 'Erste Schritte',
    resBasicDocs: 'Grundlegende vorzubereitende Unterlagen',
    resAddDocs: 'Unterlagen, die je nach Ihrer Situation hinzukommen können',
    resProcedure: 'Antragsverfahren',
    resSources: 'Offizielle Quellen',
    resNextActions: 'Nächste Schritte',
    officialSourceNeedsConfirm: 'Offizielle Quelle muss bestätigt werden',
    firstStepConfirmType: 'Bestätigen Sie, dass Ihr Untertyp korrekt ist',
    firstStepConfirmOffice: 'Bestätigen Sie die zuständige Einwanderungs- · Ausländerbehörde oder die koreanische Auslandsvertretung',
    firstStepPrepareDocs: 'Bereiten Sie die Unterlagen für das gewählte Verfahren vor',
    docsHandoffNote: 'Sehen Sie die konkreten Unterlagen auf dem auf offiziellen Quellen basierenden Detailbildschirm. Tippen Sie unten auf „Alle Unterlagen · das Verfahren ansehen“, um die Unterlagen für diesen Subcode · dieses Verfahren zu sehen.',
    addDocsNote: 'Je nach Ihrem Einzelfall können zusätzliche Unterlagen verlangt werden. Bestätigen Sie die genaue Liste auf dem Detailbildschirm und bei der zuständigen Behörde.',
    sourcesHandoffNote: 'Die offiziellen Quellen (Handbücher · Referenzen) werden auf dem Detailbildschirm mit angezeigt. Einträge ohne verknüpfte Quelle werden mit „Offizielle Quelle muss bestätigt werden“ gekennzeichnet.',
    viewFullDetail: 'Alle Unterlagen · das Verfahren ansehen',
    copyChecklist: 'Checkliste kopieren',
    copied: 'Kopiert',
    copyFail: 'Kopieren nicht möglich',
    safetyNote: 'Je nach Ihrem Einzelfall und der Entscheidung der zuständigen Einwanderungsbehörde oder der koreanischen Auslandsvertretung können zusätzliche Unterlagen verlangt werden.',
    procStepPrepare: 'Unterlagen vorbereiten',
    procStepReserve: 'Bei Bedarf einen Termin vereinbaren',
    procStepSubmit: 'Antrag einreichen',
    procStepReview: 'Prüfung',
    procStepResult: 'Ergebnis prüfen',
    procStepFollowup: 'Bei Bedarf Folgeregistrierung · Kartenausstellung abschließen',
    noSubcodesNote: 'Dieser Aufenthaltstitel hat in den offiziellen Daten keine auswählbaren Untertypen, daher gehen wir direkt zum Verfahrensschritt.',
    noteE7: 'Die Anforderungen und Unterlagen für E-7 hängen vom Beruf · von der Tätigkeit ab. Eine Bestätigung der genauen Berufsklassifizierung kann erforderlich sein, und das Ergebnis kann nicht garantiert werden.',
    noteG1: 'Die Anforderungen und Unterlagen für G-1 variieren je nach Aufenthaltsgrund, und viele Punkte unterliegen einer individuellen Prüfung · Bestätigung. Eine Bestätigung bei der zuständigen Behörde ist erforderlich.',
    noteF5: 'F-5 (Daueraufenthalt) hat strenge Kriterien und ein strenges Verfahren mit hohem Anteil individueller Prüfung. Bestätigen Sie die konkreten Anforderungen bei den offiziellen Quellen und der zuständigen Behörde.',
    docChecklistIntro: 'Nachstehend finden Sie die im offiziellen Handbuch aufgeführten vorzubereitenden Unterlagen (Checkliste zur Orientierung). Sie können je nach Einzelfall variieren.',
    docsInManualNote: 'Die Unterlagen dieses Verfahrens sind im offiziellen Handbuch aufgeführt. Tippen Sie auf „Alle Unterlagen · das Verfahren ansehen“ für die vollständige Liste.',
    docsMoreInDetail: 'Sehen Sie die übrigen Punkte vollständig auf dem Detailbildschirm.',
    sourceManualLabel: 'Handbuch-Referenz'
  };
  var STR_TR = {
    "eyebrow": "Resmi kaynaklara dayalı rehberlik",
    "recStartTitle": "Durumunuza uygun adım adım rehberlik",
    "recStartBody": "Bu ikamet statüsü için gerekli belgeler ve prosedürler; alt kategorinize, başvuru yolunuza ve mevcut durumunuza göre değişebilir. Birkaç soruyu yanıtlayarak durumunuza en yakın belge listesini ve prosedürü öğrenebilirsiniz.",
    "ctaMicrocopy": "Yaklaşık 1 dakika · Alt kategori bilgisi gerekmez",
    "primaryCtaTpl": "Bana uygun {code} belge listesini bul",
    "secondaryActionsLabel": "Keşfetmenin diğer yolları",
    "secViewSubcategories": "Tüm alt kategorileri görüntüle",
    "secViewCommonDocs": "Ortak belgeleri görüntüle",
    "secViewProcedure": "Başvuru prosedürünü görüntüle",
    "secViewSources": "Resmi kaynakları görüntüle",
    "modalAria": "İkamet statüsü hazırlık rehberi",
    "close": "Kapat",
    "back": "← Geri",
    "next": "İleri",
    "seeResult": "Sonucu gör",
    "restartShort": "Yeniden başlat",
    "stepWord": "Adım",
    "progressAria": "İlerleme",
    "optUnsure": "Emin değilim",
    "stepSubcodeQ": "Hangi tür sizinkine en yakın?",
    "stepSubcodeHelp": "Durumunuza en yakın türü seçin (resmi verilere göre). Emin değil misiniz? Sadece \"Emin değilim\" seçeneğini seçin.",
    "stepProcedureQ": "Şu anda hangi prosedüre ihtiyacınız var?",
    "stepProcedureHelp": "Yalnızca mevcut verilerin yönlendirebileceği prosedürler gösterilir.",
    "resultTitleTpl": "Sizin için olası {code} hazırlık yolu",
    "matchedType": "Seçilen tür",
    "matchedProcedure": "Seçilen prosedür",
    "unsureType": "Tür belirlenmedi",
    "unsureProcedure": "Prosedür belirlenmedi",
    "resFirstSteps": "İlk adımlar",
    "resBasicDocs": "Temel gerekli belgeler",
    "resAddDocs": "Durumunuza göre eklenebilecek belgeler",
    "resProcedure": "Prosedür",
    "resSources": "Resmi kaynaklar",
    "resNextActions": "Sonraki adımlar",
    "officialSourceNeedsConfirm": "Resmi kaynağın teyit edilmesi gerekir",
    "firstStepConfirmType": "Alt kategorinizin doğru olduğunu teyit edin",
    "firstStepConfirmOffice": "Yetkili göçmenlik idaresini veya Kore konsolosluğunu teyit edin",
    "firstStepPrepareDocs": "Seçtiğiniz prosedür için belgeleri hazırlayın",
    "docsHandoffNote": "Belirli belgeler için resmi kaynaklara dayalı detay ekranına bakın. İlgili alt kod/prosedüre ait belgeleri görmek için aşağıdaki \"Tüm belgeleri ve prosedürü görüntüle\" seçeneğine dokunun.",
    "addDocsNote": "Bireysel durumunuza bağlı olarak ek belgeler istenebilir. Kesin listeyi detay ekranından ve yetkili idareden teyit edin.",
    "sourcesHandoffNote": "Resmi kaynaklar (kılavuzlar/referanslar) detay ekranında gösterilir. Bağlantılı kaynağı olmayan öğeler \"Resmi kaynağın teyit edilmesi gerekir\" olarak işaretlenir.",
    "viewFullDetail": "Tüm belgeleri ve prosedürü görüntüle",
    "copyChecklist": "Kontrol listesini kopyala",
    "copied": "Kopyalandı",
    "copyFail": "Kopyalanamadı",
    "safetyNote": "Bireysel durumunuza ve yetkili göçmenlik idaresinin veya Kore konsolosluğunun kararına bağlı olarak ek belgeler istenebilir.",
    "procStepPrepare": "Belgeleri hazırla",
    "procStepReserve": "Gerekirse randevu al",
    "procStepSubmit": "Başvuruyu gönder",
    "procStepReview": "İnceleme / değerlendirme",
    "procStepResult": "Sonucu kontrol et",
    "procStepFollowup": "Gerekirse takip kaydını veya kart düzenlemesini tamamla",
    "noSubcodesNote": "Bu ikamet statüsü için resmi verilerde seçilebilir bir alt kategori kayıtlı olmadığından doğrudan prosedür adımına geçiyoruz.",
    "noteE7": "E-7 gereklilikleri ve belgeleri meslek/iş kategorisine göre değişir. Kesin iş sınıflandırmasının teyit edilmesi gerekebilir ve sonuçlar garanti edilemez.",
    "noteG1": "G-1 gereklilikleri ve belgeleri kalış nedenine göre değişir ve birçok öğe bireysel incelemeye tabidir. Yetkili idareyle teyit edilmesi gerekir.",
    "noteF5": "F-5 (kalıcı ikamet) katı kriterlere sahiptir ve önemli ölçüde bireysel incelemeye tabidir. Belirli gereklilikleri resmi kaynaklardan ve yetkili idareden teyit edin.",
    "docChecklistIntro": "Aşağıdaki belgeler resmi kılavuzdan alınmıştır (referans kontrol listesi). Bireysel duruma göre değişebilir.",
    "docsInManualNote": "Bu prosedürün belgeleri resmi kılavuzda kayıtlıdır. Tam liste için \"Tüm belgeleri ve prosedürü görüntüle\" seçeneğine dokunun.",
    "docsMoreInDetail": "Kalan öğeler için detay ekranına bakın.",
    "sourceManualLabel": "Kılavuz referansı"
  };
  var STR_UK = {
    "eyebrow": "Настанови на основі офіційних джерел",
    "recStartTitle": "Покрокові настанови для вашої ситуації",
    "recStartBody": "Необхідні документи та процедури для цього статусу перебування можуть відрізнятися залежно від вашої підкатегорії, шляху подання заяви та поточної ситуації. Дайте відповідь на кілька запитань, щоб знайти перелік документів і процедуру, найближчі до вашої ситуації.",
    "ctaMicrocopy": "Близько 1 хвилини · Знання підкатегорії не потрібне",
    "primaryCtaTpl": "Знайти мій перелік документів для {code}",
    "secondaryActionsLabel": "Інші способи ознайомлення",
    "secViewSubcategories": "Переглянути всі підкатегорії",
    "secViewCommonDocs": "Переглянути загальні документи",
    "secViewProcedure": "Переглянути процедуру подання заяви",
    "secViewSources": "Переглянути офіційні джерела",
    "modalAria": "Посібник з підготовки статусу перебування",
    "close": "Закрити",
    "back": "← Назад",
    "next": "Далі",
    "seeResult": "Переглянути результат",
    "restartShort": "Почати заново",
    "stepWord": "Крок",
    "progressAria": "Прогрес",
    "optUnsure": "Я не впевнений",
    "stepSubcodeQ": "Який тип найближчий до вашого?",
    "stepSubcodeHelp": "Виберіть тип, найближчий до вашої ситуації (за офіційними даними). Не впевнені? Просто виберіть \"Я не впевнений\".",
    "stepProcedureQ": "Яка процедура вам потрібна зараз?",
    "stepProcedureHelp": "Показано лише процедури, за якими можуть надати настанови наявні дані.",
    "resultTitleTpl": "Ваш імовірний шлях підготовки {code}",
    "matchedType": "Обраний тип",
    "matchedProcedure": "Обрана процедура",
    "unsureType": "Тип не визначено",
    "unsureProcedure": "Процедуру не визначено",
    "resFirstSteps": "Перші кроки",
    "resBasicDocs": "Основні необхідні документи",
    "resAddDocs": "Документи, які можуть додати для вашої ситуації",
    "resProcedure": "Процедура",
    "resSources": "Офіційні джерела",
    "resNextActions": "Наступні дії",
    "officialSourceNeedsConfirm": "Офіційне джерело потребує підтвердження",
    "firstStepConfirmType": "Підтвердьте, що ваша підкатегорія правильна",
    "firstStepConfirmOffice": "Підтвердьте компетентну імміграційну службу або консульство Кореї",
    "firstStepPrepareDocs": "Підготуйте документи для обраної процедури",
    "docsHandoffNote": "Перегляньте екран деталей на основі офіційних джерел для конкретних документів. Натисніть \"Переглянути повний перелік документів і процедуру\" нижче, щоб побачити документи для цього підкоду/процедури.",
    "addDocsNote": "Залежно від вашого індивідуального випадку можуть вимагати додаткові документи. Підтвердьте точний перелік на екрані деталей та в компетентній службі.",
    "sourcesHandoffNote": "Офіційні джерела (посібники/довідки) показано на екрані деталей. Елементи без пов'язаного джерела позначено як \"Офіційне джерело потребує підтвердження\".",
    "viewFullDetail": "Переглянути повний перелік документів і процедуру",
    "copyChecklist": "Копіювати контрольний список",
    "copied": "Скопійовано",
    "copyFail": "Не вдалося скопіювати",
    "safetyNote": "Залежно від вашого індивідуального випадку та рішення компетентної імміграційної служби або консульства Кореї можуть вимагати додаткові документи.",
    "procStepPrepare": "Підготувати документи",
    "procStepReserve": "За потреби записатися на прийом",
    "procStepSubmit": "Подати заяву",
    "procStepReview": "Розгляд / перевірка",
    "procStepResult": "Перевірити результат",
    "procStepFollowup": "За потреби завершити подальшу реєстрацію або оформлення картки",
    "noSubcodesNote": "Для цього статусу перебування в офіційних даних не записано жодної підкатегорії для вибору, тому переходимо одразу до кроку процедури.",
    "noteE7": "Вимоги та документи E-7 залежать від професії/категорії роботи. Може знадобитися підтвердження точної класифікації роботи, і результати не можна гарантувати.",
    "noteG1": "Вимоги та документи G-1 відрізняються залежно від причини перебування, і багато елементів підлягають індивідуальному розгляду. Потрібне підтвердження в компетентній службі.",
    "noteF5": "F-5 (постійне проживання) має суворі критерії та значний індивідуальний розгляд. Підтвердьте конкретні вимоги в офіційних джерелах та компетентній службі.",
    "docChecklistIntro": "Наведені нижче документи взято з офіційного посібника (довідковий контрольний список). Вони можуть відрізнятися залежно від індивідуального випадку.",
    "docsInManualNote": "Документи цієї процедури записано в офіційному посібнику. Натисніть \"Переглянути повний перелік документів і процедуру\", щоб побачити повний перелік.",
    "docsMoreInDetail": "Перегляньте екран деталей для решти елементів.",
    "sourceManualLabel": "Довідка з посібника"
  };
  var STR_PACKS = {
    ko: STR_KO, en: STR_EN, 'zh-CN': STR_ZH,
    ja: STR_JA, vi: STR_VI, tl: STR_TL, id: STR_ID, ru: STR_RU,
    fr: STR_FR, es: STR_ES, ar: STR_AR, de: STR_DE, tr: STR_TR, uk: STR_UK
  };
  function S(k) { var p = STR_PACKS[csgLang()] || STR_KO; return (p[k] != null) ? p[k] : STR_KO[k]; }
  function tpl(k, code) { return String(S(k)).replace('{code}', code); }

  /* ---- per-status config (data-sourced; notes are cautious framing only) --- */
  var STATUS_NOTE = { 'E-7': 'noteE7', 'G-1': 'noteG1', 'F-5': 'noteF5' };

  /* ---------------------------------------------------- data adapter (safe) */
  function getRecord(code) {
    try {
      if (typeof VISA_DATA !== 'undefined' && Array.isArray(VISA_DATA)) {
        return VISA_DATA.find(function (v) { return v && v.code === code; }) || null;
      }
    } catch (e) { /* ignore */ }
    return null;
  }
  function getModel(code) {
    var rec = getRecord(code);
    if (!rec || !window.ParadisoRoute || typeof window.ParadisoRoute.buildGuidanceModel !== 'function') return null;
    try { return window.ParadisoRoute.buildGuidanceModel(rec); } catch (e) { return null; }
  }
  // Only offer real, selectable subcodes — never manual-review/reference-only
  // placeholders (which have no meaningful title).
  function selectableSubcodes(model) {
    if (!model || !Array.isArray(model.subcodes)) return [];
    return model.subcodes.filter(function (s) { return s && s.status === 'active' && s.code; });
  }
  function subcodeLabel(s) {
    var title = (csgLang() === 'en' && s.titleEn) ? s.titleEn : (s.titleKo || s.titleEn || '');
    return title ? (s.code + ' · ' + title) : s.code;
  }
  function availableProcedures(model) {
    if (!model || !Array.isArray(model.procedures)) return [];
    return model.procedures.filter(function (p) { return p && p.status === 'available' && p.key; });
  }
  function procLabel(p) { return p.userLabel || p.officialLabel || p.key; }
  function findSub(model, code) {
    var subs = (model && model.subcodes) || [];
    for (var i = 0; i < subs.length; i++) if (subs[i].code === code) return subs[i];
    return null;
  }
  function findProc(model, key) {
    var ps = (model && model.procedures) || [];
    for (var i = 0; i < ps.length; i++) if (ps[i].key === key) return ps[i];
    return null;
  }

  /* ---------------------------------------------- source-backed documents ---
   * Document data lives at the PARENT procedure level in visa_data.json
   * (procedures.<camelKey>.requiredDocs grouped into common/required/additional/
   * conditional). Most entries are prose (manual document names), but some are
   * doc_master IDs. We render a checklist ONLY from resolvable doc_master IDs
   * (short, clean, audit-safe names); prose/empty groups fall back to the
   * existing audit-safe card renderer via the "view full detail" handoff, marked
   * as needing confirmation. Subcodes carry no own documents, so we never invent
   * subcode-specific requirements. */
  var DOC_MASTER = null;        // id -> { ko_name, en_name }
  var docMasterPromise = null;
  function buildDocMasterMap(arr) {
    var map = {};
    (Array.isArray(arr) ? arr : []).forEach(function (d) { if (d && d.id) map[d.id] = d; });
    return map;
  }
  function loadDocMaster() {
    if (DOC_MASTER) return Promise.resolve(DOC_MASTER);
    if (docMasterPromise) return docMasterPromise;
    if (typeof fetch !== 'function') return Promise.resolve(null);
    docMasterPromise = fetch('doc_master.json', { cache: 'no-cache' })
      .then(function (r) { if (!r.ok) throw new Error('HTTP ' + r.status); return r.json(); })
      .then(function (arr) { DOC_MASTER = buildDocMasterMap(arr); return DOC_MASTER; })
      .catch(function () { docMasterPromise = null; return null; }); // graceful: fall back to handoff
    return docMasterPromise;
  }
  function docName(id, docMaster) {
    var e = docMaster && docMaster[id];
    if (!e) return id;
    return (csgLang() === 'en' && e.en_name) ? e.en_name : (e.ko_name || e.en_name || id);
  }
  function camelKeyOf(snakeKey) {
    var map = (window.ParadisoRoute && window.ParadisoRoute.CAMEL_OF) || {};
    return map[snakeKey] || snakeKey;
  }
  // Partition one procedure's doc groups into resolvable doc_master IDs vs prose.
  // Pure given (groupArrays, docMaster). Returns {docs:[{id,name}], prose:Number}.
  function partitionGroup(arrays, docMaster) {
    var docs = [], prose = 0, seen = {};
    (arrays || []).forEach(function (list) {
      (Array.isArray(list) ? list : []).forEach(function (e) {
        if (typeof e === 'string' && e.indexOf('doc_') === 0 && docMaster && docMaster[e]) {
          if (!seen[e]) { seen[e] = 1; docs.push({ id: e, name: docName(e, docMaster) }); }
        } else { prose += 1; }
      });
    });
    return { docs: docs, prose: prose };
  }
  // Build source-backed doc + manual-ref info for a (code, snake procKey).
  // record + docMaster are injected (browser: VISA_DATA + DOC_MASTER; tests pass
  // them directly) so this stays unit-testable and never depends on globals.
  function buildDocInfo(code, snakeProcKey, record, docMaster) {
    var empty = { camelKey: '', basicDocs: [], basicProse: 0, sitDocs: [], sitProse: 0, docsAvailable: false, sourceRefs: [] };
    if (!snakeProcKey || !record || !record.procedures) return empty;
    var camelKey = camelKeyOf(snakeProcKey);
    var proc = record.procedures[camelKey];
    if (!proc) return empty;
    var rd = proc.requiredDocs || {};
    var basic = partitionGroup([rd.commonDocs, rd.requiredDocs], docMaster);
    var sit = partitionGroup([rd.additionalDocs, rd.conditionalDocs], docMaster);
    var sourceRefs = (Array.isArray(proc.manualRefs) ? proc.manualRefs : []).map(function (r) {
      return { name: r.manualName || '', version: r.manualVersion || '', page: r.pageRange || '' };
    }).filter(function (r) { return r.name || r.page; });
    return {
      camelKey: camelKey,
      basicDocs: basic.docs, basicProse: basic.prose,
      sitDocs: sit.docs, sitProse: sit.prose,
      docsAvailable: (basic.docs.length + basic.prose + sit.docs.length + sit.prose) > 0,
      sourceRefs: sourceRefs
    };
  }

  /* -------------------------------------------------- pure flow + result --- */
  // Steps are computed from the (source-backed) model. Pure → unit-testable.
  function buildSteps(model) {
    var steps = [];
    var subs = selectableSubcodes(model);
    if (subs.length) {
      steps.push({
        id: 'subcode', type: 'single', qKey: 'stepSubcodeQ', helpKey: 'stepSubcodeHelp',
        options: subs.map(function (s) { return { id: s.code, label: subcodeLabel(s) }; })
          .concat([{ id: 'unsure', label: S('optUnsure'), unsure: true }])
      });
    }
    var procs = availableProcedures(model);
    steps.push({
      id: 'procedure', type: 'single', qKey: 'stepProcedureQ', helpKey: 'stepProcedureHelp',
      options: procs.map(function (p) { return { id: p.key, label: procLabel(p) }; })
        .concat([{ id: 'unsure', label: S('optUnsure'), unsure: true }])
    });
    return steps;
  }

  // opts.record + opts.docMaster (optional) enable source-backed documents +
  // manual references in the result. Without them the result degrades to the
  // safe handoff (still useful, marked "공식근거 확인 필요").
  function buildResultModel(code, model, answers, opts) {
    answers = answers || {};
    opts = opts || {};
    var subCode = (answers.subcode && answers.subcode !== 'unsure') ? answers.subcode : '';
    var procKey = (answers.procedure && answers.procedure !== 'unsure') ? answers.procedure : '';
    var sub = subCode ? findSub(model, subCode) : null;
    var proc = procKey ? findProc(model, procKey) : null;
    var di = buildDocInfo(code, procKey, opts.record || null, opts.docMaster || null);
    return {
      code: code,
      subCode: subCode,
      subLabel: sub ? subcodeLabel(sub) : '',
      procKey: procKey,
      procCamelKey: di.camelKey,
      procLabel: proc ? procLabel(proc) : '',
      noteKey: STATUS_NOTE[code] || '',
      firstSteps: [S('firstStepConfirmType'), S('firstStepConfirmOffice'), S('firstStepPrepareDocs')],
      procSteps: [S('procStepPrepare'), S('procStepReserve'), S('procStepSubmit'), S('procStepReview'), S('procStepResult'), S('procStepFollowup')],
      basicDocs: di.basicDocs, basicProse: di.basicProse,
      sitDocs: di.sitDocs, sitProse: di.sitProse,
      docsAvailable: di.docsAvailable,
      sourceRefs: di.sourceRefs
    };
  }

  function sourceRefText(r) { return [r.name, r.version, r.page].filter(Boolean).join(' · '); }

  function checklistText(code, m) {
    var lines = [];
    lines.push(tpl('resultTitleTpl', code));
    lines.push(S('matchedType') + ': ' + (m.subLabel || S('unsureType')));
    lines.push(S('matchedProcedure') + ': ' + (m.procLabel || S('unsureProcedure')));
    lines.push(''); lines.push('[' + S('resFirstSteps') + ']');
    m.firstSteps.forEach(function (s) { lines.push('- ' + s); });
    lines.push(''); lines.push('[' + S('resBasicDocs') + ']');
    if (m.basicDocs && m.basicDocs.length) {
      m.basicDocs.forEach(function (d) { lines.push('[ ] ' + d.name); });
      if (m.basicProse) lines.push('- ' + S('docsMoreInDetail'));
    } else if (m.docsAvailable) { lines.push('- ' + S('docsInManualNote')); }
    else { lines.push('- ' + S('officialSourceNeedsConfirm')); }
    if (m.sitDocs && m.sitDocs.length) {
      lines.push(''); lines.push('[' + S('resAddDocs') + ']');
      m.sitDocs.forEach(function (d) { lines.push('[ ] ' + d.name); });
    }
    lines.push(''); lines.push('[' + S('resProcedure') + ']');
    m.procSteps.forEach(function (s, i) { lines.push((i + 1) + '. ' + s); });
    if (m.sourceRefs && m.sourceRefs.length) {
      lines.push(''); lines.push('[' + S('resSources') + ']');
      m.sourceRefs.forEach(function (r) { lines.push('- ' + sourceRefText(r)); });
    }
    lines.push(''); lines.push(S('safetyNote'));
    return lines.join('\n');
  }

  /* ----------------------------------------------------------- module state */
  var state = { code: null, model: null, view: 'flow', stepIndex: 0, steps: [], answers: {}, result: null,
    modal: null, lastFocus: null, keyHandler: null };

  /* --------------------------------------------------------------- styling */
  function injectStyles() {
    if (document.getElementById('csgStyles')) return;
    var css = '' +
'.csg-hero{background:var(--bg1,#fff);border:1px solid var(--bd,#d1c6b4);border-radius:var(--radius-lg,16px);box-shadow:var(--sh1,0 1px 2px rgba(0,0,0,.05));padding:1.05rem 1.1rem;}' +
'.csg-hero.csg-incard{margin:.5rem 0 .2rem;border-color:var(--ac,#2f5e67);border-left-width:4px;background:var(--bg2,#f7f3ea);}' +
'.csg-eyebrow{font-size:.7rem;letter-spacing:.12em;text-transform:uppercase;color:var(--ac,#2f5e67);font-weight:800;margin:0 0 .3rem;}' +
'.csg-rec-title{font-size:1.12rem;font-weight:800;color:var(--t1,#202221);margin:.1rem 0 .35rem;display:flex;align-items:center;gap:.45rem;word-break:keep-all;line-height:1.35;}' +
'.csg-rec-title::before{content:"";width:10px;height:10px;border-radius:50%;background:var(--ac,#2f5e67);display:inline-block;flex:0 0 auto;}' +
'.csg-rec-body{font-size:.88rem;line-height:1.65;color:var(--t2,#4f5552);margin:0 0 .85rem;word-break:keep-all;}' +
'.csg-primary-cta{font:inherit;font-weight:800;font-size:1rem;border-radius:13px;padding:.85rem 1.3rem;cursor:pointer;min-height:52px;border:1px solid var(--ac,#2f5e67);background:var(--ac,#2f5e67);color:#fff;display:inline-flex;align-items:center;gap:.5rem;width:100%;justify-content:center;box-shadow:0 2px 10px rgba(47,94,103,.18);}' +
'.csg-primary-cta:hover{filter:brightness(1.06);}' +
'.csg-primary-cta:focus-visible{outline:3px solid var(--ac,#2f5e67);outline-offset:2px;}' +
'.csg-rec-microcopy{font-size:.78rem;color:var(--t3,#757a76);margin:.5rem 0 0;text-align:center;word-break:keep-all;}' +
'.csg-secondary{margin-top:.9rem;padding-top:.75rem;border-top:1px dashed var(--bd2,#ddd3c3);}' +
'.csg-secondary-label{display:block;font-size:.72rem;font-weight:700;letter-spacing:.04em;color:var(--t3,#757a76);margin:0 0 .45rem;}' +
'.csg-secondary-row{display:flex;flex-wrap:wrap;gap:.4rem;}' +
'.csg-secondary-btn{font:inherit;font-size:.8rem;font-weight:600;border-radius:999px;padding:.4rem .8rem;min-height:38px;cursor:pointer;border:1px solid var(--bd,#d1c6b4);background:transparent;color:var(--t2,#4f5552);}' +
'.csg-secondary-btn:hover{border-color:var(--ac,#2f5e67);color:var(--ac,#2f5e67);}' +
'.csg-secondary-btn:focus-visible{outline:3px solid var(--ac,#2f5e67);outline-offset:1px;}' +
/* overlay */
'.csg-overlay{position:fixed;inset:0;z-index:9000;display:none;align-items:center;justify-content:center;padding:1.25rem;background:rgba(20,20,18,.55);}' +
'.csg-overlay.open{display:flex;}' +
'.csg-box{background:var(--bg1,#fff);border:1px solid var(--bd,#d1c6b4);border-radius:18px;box-shadow:0 18px 60px rgba(0,0,0,.3);width:min(900px,100%);height:min(720px,94vh);max-height:94vh;display:flex;flex-direction:column;overflow:hidden;}' +
'.csg-head{display:flex;align-items:flex-start;justify-content:space-between;gap:.6rem;padding:1rem 1.25rem .7rem;border-bottom:1px solid var(--bd2,#e5dccb);flex:0 0 auto;}' +
'.csg-head h2{font-size:1.08rem;font-weight:800;color:var(--t1,#202221);margin:.05rem 0 0;word-break:keep-all;}' +
'.csg-step-count{font-size:.74rem;font-weight:700;color:var(--ac,#2f5e67);margin:.25rem 0 0;letter-spacing:.04em;}' +
'.csg-close{font:inherit;font-size:1.2rem;line-height:1;border:1px solid var(--bd,#d1c6b4);background:var(--bg2,#f1ece2);color:var(--t1,#202221);border-radius:10px;min-width:42px;min-height:42px;cursor:pointer;flex:0 0 auto;}' +
'.csg-close:focus-visible{outline:3px solid var(--ac,#2f5e67);outline-offset:1px;}' +
'.csg-progress{height:6px;background:var(--bg2,#f1ece2);flex:0 0 auto;}' +
'.csg-progress-bar{height:100%;background:var(--ac,#2f5e67);transition:width .25s ease;}' +
'.csg-body{padding:1.05rem 1.25rem 1.15rem;overflow-y:auto;flex:1 1 auto;-webkit-overflow-scrolling:touch;}' +
'.csg-foot{display:flex;align-items:center;justify-content:space-between;gap:.6rem;padding:.8rem 1.25rem;border-top:1px solid var(--bd2,#e5dccb);background:var(--bg1,#fff);flex:0 0 auto;}' +
'.csg-foot-btn{font:inherit;font-weight:700;font-size:.9rem;border-radius:11px;padding:.7rem 1.15rem;cursor:pointer;min-height:48px;border:1px solid var(--bd,#d1c6b4);background:var(--bg2,#f1ece2);color:var(--t1,#202221);}' +
'.csg-foot-btn.primary{border-color:var(--ac,#2f5e67);background:var(--ac,#2f5e67);color:#fff;}' +
'.csg-foot-btn:disabled{opacity:.45;cursor:not-allowed;}' +
'.csg-foot-btn:focus-visible{outline:3px solid var(--ac,#2f5e67);outline-offset:1px;}' +
'.csg-q-title{font-size:1.1rem;font-weight:800;color:var(--t1,#202221);margin:.2rem 0 .3rem;word-break:keep-all;line-height:1.4;}' +
'.csg-q-help{font-size:.83rem;line-height:1.6;color:var(--t3,#757a76);margin:0 0 .9rem;word-break:keep-all;}' +
'.csg-opts{display:grid;gap:.5rem;max-width:640px;}' +
'.csg-opt{font:inherit;text-align:left;background:var(--bgI,#fff);border:1.5px solid var(--bd,#d1c6b4);border-radius:12px;padding:.8rem .95rem;cursor:pointer;min-height:52px;color:var(--t1,#202221);font-size:.92rem;word-break:keep-all;display:flex;align-items:center;gap:.6rem;line-height:1.45;}' +
'.csg-opt:hover{border-color:var(--ac,#2f5e67);}' +
'.csg-opt:focus-visible{outline:3px solid var(--ac,#2f5e67);outline-offset:1px;}' +
'.csg-opt[aria-checked="true"]{border-color:var(--ac,#2f5e67);background:var(--acG,rgba(47,94,103,.1));box-shadow:inset 0 0 0 1px var(--ac,#2f5e67);font-weight:700;}' +
'.csg-opt-mark{flex:0 0 auto;width:22px;height:22px;border-radius:50%;border:2px solid var(--bd,#9b9384);display:inline-flex;align-items:center;justify-content:center;font-size:.8rem;color:#fff;}' +
'.csg-opt[aria-checked="true"] .csg-opt-mark{background:var(--ac,#2f5e67);border-color:var(--ac,#2f5e67);}' +
'.csg-opt-unsure{color:var(--t2,#4f5552);font-style:italic;}' +
'.csg-result{max-width:680px;margin:0 auto;}' +
'.csg-result-title{font-size:.9rem;font-weight:800;letter-spacing:.05em;text-transform:uppercase;color:var(--t3,#757a76);margin:0 0 .4rem;}' +
'.csg-route-chip{display:inline-block;font-size:1rem;font-weight:800;color:var(--ac,#2f5e67);background:var(--acG,rgba(47,94,103,.1));border:1px solid var(--ac,#2f5e67);border-radius:12px;padding:.45rem .8rem;margin:0 0 .85rem;word-break:keep-all;}' +
'.csg-section{border:1px solid var(--bd2,#e5dccb);border-radius:14px;padding:1rem 1.05rem;margin:0 0 1rem;background:var(--bg1,#fff);}' +
'.csg-section-title{font-size:.95rem;font-weight:800;color:var(--t1,#202221);margin:0 0 .5rem;word-break:keep-all;display:flex;align-items:center;gap:.4rem;}' +
'.csg-section-title .csg-num{display:inline-flex;align-items:center;justify-content:center;width:24px;height:24px;border-radius:50%;background:var(--ac,#2f5e67);color:#fff;font-size:.78rem;font-weight:800;flex:0 0 auto;}' +
'.csg-chk{display:flex;align-items:flex-start;gap:.6rem;padding:.55rem .1rem;border:0;border-bottom:1px solid var(--bd2,#e5dccb);border-radius:0;background:transparent;font-size:.92rem;line-height:1.6;color:var(--t1,#202221);word-break:keep-all;margin:0;}' +
'.csg-checklist .csg-chk:last-child{border-bottom:0;}' +
'.csg-chk input{margin-top:.18rem;width:18px;height:18px;flex:0 0 auto;accent-color:var(--ac,#2f5e67);}' +
'.csg-ul{margin:.2rem 0;padding-left:1.15rem;}' +
'.csg-ul li{font-size:.86rem;line-height:1.6;color:var(--t1,#202221);margin:.15rem 0;word-break:keep-all;}' +
'.csg-meta{font-size:.86rem;color:var(--t2,#4f5552);margin:.1rem 0 .5rem;word-break:keep-all;}' +
'.csg-meta strong{color:var(--t1,#202221);}' +
'.csg-badge-confirm{display:inline-block;font-size:.7rem;font-weight:800;color:var(--cWk,#a85f1c);border:1px solid var(--cWk,#E68A3A);border-radius:999px;padding:.08rem .5rem;margin-left:.3rem;}' +
'.csg-note{background:var(--bg2,#f1ece2);border:1px solid var(--bd,#d1c6b4);border-radius:10px;padding:.6rem .72rem;margin:.4rem 0;font-size:.83rem;line-height:1.6;color:var(--t1,#202221);word-break:keep-all;}' +
'.csg-safety{background:var(--bg2,#f7f3ea);border:1px solid var(--bd,#d1c6b4);border-left:4px solid var(--cWk,#E68A3A);border-radius:10px;padding:.7rem .8rem;margin:.6rem 0 .2rem;font-size:.82rem;line-height:1.6;color:var(--t2,#4f5552);word-break:keep-all;}' +
'.csg-actions{display:flex;flex-wrap:wrap;gap:.45rem;margin:.3rem 0;}' +
'.csg-act-btn{display:inline-flex;align-items:center;min-height:44px;padding:.45rem .9rem;border:1px solid var(--ac,#2f5e67);border-radius:999px;font:inherit;font-size:.84rem;font-weight:700;color:var(--ac,#2f5e67);text-decoration:none;background:transparent;cursor:pointer;}' +
'.csg-act-btn.primary{background:var(--ac,#2f5e67);color:#fff;}' +
'.csg-act-btn:hover{background:var(--acG,rgba(47,94,103,.1));}' +
'.csg-act-btn:focus-visible{outline:3px solid var(--ac,#2f5e67);outline-offset:1px;}' +
'.csg-foot-note{font-size:.74rem;color:var(--t3,#757a76);margin-top:.8rem;word-break:keep-all;}' +
'body.csg-modal-open{overflow:hidden;}' +
'@media (max-width:640px){.csg-overlay{padding:0;align-items:stretch;}.csg-box{width:100%;height:100%;max-height:100%;border-radius:0;}.csg-opts{max-width:none;}.csg-foot-btn{flex:1 1 auto;text-align:center;}}';
    var style = document.createElement('style');
    style.id = 'csgStyles';
    style.textContent = css;
    document.head.appendChild(style);
  }

  /* --------------------------------------------------- recommended-start UI */
  function recStartBlockHtml(code) {
    var secBtn = function (ref, key) {
      return '<button type="button" class="csg-secondary-btn" data-csg-ref="' + ref + '">' + esc(S(key)) + '</button>';
    };
    return '<div class="csg-recstart">' +
      '<p class="csg-eyebrow">' + esc(code + ' · ' + S('eyebrow')) + '</p>' +
      '<h2 class="csg-rec-title" id="csgRecTitle-' + esc(code) + '">' + esc(S('recStartTitle')) + '</h2>' +
      '<p class="csg-rec-body">' + esc(S('recStartBody')) + '</p>' +
      '<button type="button" class="csg-primary-cta" data-csg-start>' + esc(tpl('primaryCtaTpl', code)) + '<span aria-hidden="true">→</span></button>' +
      '<p class="csg-rec-microcopy">' + esc(S('ctaMicrocopy')) + '</p>' +
      '<div class="csg-secondary">' +
        '<span class="csg-secondary-label">' + esc(S('secondaryActionsLabel')) + '</span>' +
        '<div class="csg-secondary-row">' +
          secBtn('subcategories', 'secViewSubcategories') +
          secBtn('commonDocs', 'secViewCommonDocs') +
          secBtn('procedure', 'secViewProcedure') +
          secBtn('sources', 'secViewSources') +
        '</div>' +
      '</div>' +
    '</div>';
  }

  function wireEntry(container, code) {
    var startBtn = container.querySelector('[data-csg-start]');
    if (startBtn) startBtn.addEventListener('click', function () { open(code, { view: 'flow' }); });
    container.querySelectorAll('[data-csg-ref]').forEach(function (btn) {
      btn.addEventListener('click', function () { secondaryAction(code, btn.getAttribute('data-csg-ref')); });
    });
  }

  // Secondary "browse manually" actions delegate to the EXISTING source-backed
  // UI (ParadisoRoute / the card drawer) — no protected data re-rendered here.
  function secondaryAction(code, ref) {
    var R = window.ParadisoRoute;
    try {
      if (ref === 'subcategories' && R && R.openSubcodeSelector && R.openSubcodeSelector(code)) return;
      if (ref === 'procedure' && R && R.openProcedureSelector && R.openProcedureSelector(code, '')) return;
      if ((ref === 'commonDocs' || ref === 'sources') && R && R.start && R.start(code)) return;
      if (R && R.start && R.start(code)) return;
    } catch (e) { /* fall through */ }
    if (typeof openVisaDrawer === 'function') openVisaDrawer(code);
  }

  // Inject the recommended-start block into the card's slot (rendered right after
  // the card summary, before the long subcode/procedure sections). Injected
  // whenever the slot exists — when the card is collapsed the block simply sits
  // in the (hidden) card body and appears at the top once the card is expanded,
  // matching the prior generic-CTA behavior (the six have no separate fallback
  // section, so gating on open-state would leave an expanded card with no CTA).
  function injectRecStart(code) {
    injectStyles();
    var slot = document.querySelector('.external-guide-slot[data-guide-slot="' + (window.CSS && CSS.escape ? CSS.escape(code) : code) + '"]');
    if (!slot) return false;
    slot.innerHTML = '<div class="csg-hero csg-incard">' + recStartBlockHtml(code) + '</div>';
    wireEntry(slot, code);
    return true;
  }

  /* --------------------------------------------------------------- overlay */
  function buildOverlay() {
    if (state.modal) return state.modal;
    injectStyles();
    var overlay = document.createElement('div');
    overlay.className = 'csg-overlay';
    overlay.id = 'csgOverlay';
    overlay.setAttribute('role', 'dialog');
    overlay.setAttribute('aria-modal', 'true');
    overlay.setAttribute('aria-labelledby', 'csgModalTitle');
    overlay.setAttribute('aria-hidden', 'true');
    overlay.innerHTML =
      '<div class="csg-box" role="document">' +
        '<div class="csg-head">' +
          '<div><h2 id="csgModalTitle"></h2><p class="csg-step-count" data-csg-stepcount aria-live="polite"></p></div>' +
          '<button type="button" class="csg-close" data-csg-close aria-label="' + esc(S('close')) + '">✕</button>' +
        '</div>' +
        '<div class="csg-progress" role="progressbar" aria-label="' + esc(S('progressAria')) + '" aria-valuemin="0" aria-valuemax="100" aria-valuenow="0" data-csg-progress>' +
          '<div class="csg-progress-bar" data-csg-progressbar style="width:0%"></div>' +
        '</div>' +
        '<div class="csg-body" id="csgBody"></div>' +
        '<div class="csg-foot" data-csg-foot></div>' +
      '</div>';
    document.body.appendChild(overlay);
    overlay.addEventListener('click', function (e) { if (e.target === overlay) close(); });
    overlay.querySelector('[data-csg-close]').addEventListener('click', close);
    state.modal = overlay;
    return overlay;
  }

  function focusables(container) {
    return Array.prototype.slice.call(container.querySelectorAll(
      'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
    )).filter(function (el) { return !el.disabled && (el.offsetParent !== null || el === document.activeElement); });
  }
  function onKeydown(e) {
    if (!state.modal || !state.modal.classList.contains('open')) return;
    if (e.key === 'Escape') { e.preventDefault(); e.stopPropagation(); close(); return; }
    if (e.key !== 'Tab') return;
    var f = focusables(state.modal);
    if (!f.length) return;
    var first = f[0], last = f[f.length - 1];
    if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
    else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
  }

  function open(code, opts) {
    opts = opts || {};
    if (TARGETS.indexOf(code) === -1) return false;
    var model = getModel(code);
    if (!model) {
      // Data not ready — fall back to the existing guided flow so the CTA never dead-ends.
      try { if (window.ParadisoRoute && window.ParadisoRoute.start && window.ParadisoRoute.start(code)) return true; } catch (e) {}
      if (typeof openVisaDrawer === 'function') { openVisaDrawer(code); return true; }
      return false;
    }
    buildOverlay();
    state.lastFocus = document.activeElement;
    state.code = code;
    state.model = model;
    state.steps = buildSteps(model);
    state.view = 'flow';
    state.stepIndex = 0;
    state.answers = {};
    state.result = null;
    renderGuide();
    state.modal.classList.add('open');
    state.modal.setAttribute('aria-hidden', 'false');
    document.body.classList.add('csg-modal-open');
    if (!state.keyHandler) { state.keyHandler = onKeydown; document.addEventListener('keydown', state.keyHandler, true); }
    focusFirst();
    return true;
  }

  function close() {
    if (!state.modal) return;
    state.modal.classList.remove('open');
    state.modal.setAttribute('aria-hidden', 'true');
    document.body.classList.remove('csg-modal-open');
    if (state.keyHandler) { document.removeEventListener('keydown', state.keyHandler, true); state.keyHandler = null; }
    if (state.lastFocus && typeof state.lastFocus.focus === 'function') { try { state.lastFocus.focus(); } catch (e) {} }
    state.lastFocus = null;
  }

  function focusFirst() {
    if (!state.modal) return;
    var body = state.modal.querySelector('#csgBody');
    var t = (body && body.querySelector('button, a, input, select')) || state.modal.querySelector('[data-csg-close]');
    if (t) { try { t.focus(); } catch (e) {} }
  }

  function setStepCount(txt) { var el = state.modal && state.modal.querySelector('[data-csg-stepcount]'); if (el) el.textContent = txt || ''; }
  function setProgress(pct) {
    if (!state.modal) return;
    pct = Math.max(0, Math.min(100, Math.round(pct)));
    var wrap = state.modal.querySelector('[data-csg-progress]'); var bar = state.modal.querySelector('[data-csg-progressbar]');
    if (bar) bar.style.width = pct + '%';
    if (wrap) wrap.setAttribute('aria-valuenow', String(pct));
  }
  function renderFooter(buttons) {
    var foot = state.modal && state.modal.querySelector('[data-csg-foot]');
    if (!foot) return;
    foot.innerHTML = (buttons || []).map(function (b) {
      return '<button type="button" class="csg-foot-btn' + (b.primary ? ' primary' : '') + '" data-csg-act="' + b.action + '"' + (b.disabled ? ' disabled' : '') + '>' + esc(b.label) + '</button>';
    }).join('');
    foot.querySelectorAll('[data-csg-act]').forEach(function (btn) {
      btn.addEventListener('click', function () { footAction(btn.getAttribute('data-csg-act')); });
    });
  }
  function footAction(a) {
    if (a === 'close') return close();
    if (a === 'back') return goBack();
    if (a === 'next') return goNext();
    if (a === 'restart') { state.view = 'flow'; state.stepIndex = 0; state.answers = {}; state.result = null; renderGuide(); focusFirst(); return; }
    if (a === 'detail') return handoff();
  }

  function handoff() {
    var code = state.code, m = state.result || {};
    close();
    var R = window.ParadisoRoute;
    try {
      if (R && R.goToResult && R.goToResult(code, m.subCode || '', m.procKey || '')) return;
      if (R && R.start && R.start(code)) return;
    } catch (e) {}
    if (typeof openVisaDrawer === 'function') openVisaDrawer(code);
  }

  function renderGuide() {
    if (!state.modal) return;
    if (state.view === 'result') return renderResultView();
    return renderFlow();
  }

  function renderFlow() {
    var titleEl = state.modal.querySelector('#csgModalTitle');
    var body = state.modal.querySelector('#csgBody');
    var step = state.steps[state.stepIndex];
    titleEl.textContent = state.code + ' · ' + S('recStartTitle');
    var n = state.stepIndex + 1, total = state.steps.length;
    setStepCount((csgLang() !== 'ko') ? (S('stepWord') + ' ' + n + ' / ' + total) : (n + ' / ' + total + ' ' + S('stepWord')));
    setProgress((n / total) * 100);
    body.innerHTML = renderStepHtml(step);
    body.scrollTop = 0;
    wireStep(step, body);
    var answered = !!state.answers[step.id];
    var isLast = state.stepIndex === state.steps.length - 1;
    renderFooter([
      { label: S('back'), action: 'back', disabled: state.stepIndex === 0 },
      { label: isLast ? S('seeResult') : S('next'), action: 'next', primary: true, disabled: !answered }
    ]);
  }

  function renderStepHtml(step) {
    var sel = state.answers[step.id];
    var html = '<div class="csg-step">';
    html += '<h3 class="csg-q-title">' + esc(S(step.qKey)) + '</h3>';
    if (step.helpKey) html += '<p class="csg-q-help">' + esc(S(step.helpKey)) + '</p>';
    html += '<div class="csg-opts" role="radiogroup" aria-label="' + esc(S(step.qKey)) + '">';
    html += step.options.map(function (o) {
      var on = sel === o.id;
      var cls = 'csg-opt' + (o.unsure ? ' csg-opt-unsure' : '');
      var mark = '<span class="csg-opt-mark" aria-hidden="true">' + (on ? '●' : '') + '</span>';
      return '<button type="button" class="' + cls + '" role="radio" aria-checked="' + (on ? 'true' : 'false') + '" data-csg-opt="' + esc(o.id) + '">' + mark + '<span>' + esc(o.label) + '</span></button>';
    }).join('');
    html += '</div>';
    html += '<p class="csg-foot-note">' + esc(S('safetyNote')) + '</p>';
    return html + '</div>';
  }

  function wireStep(step, body) {
    body.querySelectorAll('[data-csg-opt]').forEach(function (btn) {
      btn.addEventListener('click', function () { state.answers[step.id] = btn.getAttribute('data-csg-opt'); renderFlow(); });
    });
  }

  // Build the result model with source-backed docs/sources injected (browser:
  // VISA_DATA record + the lazily-fetched doc_master map). Kicks off doc_master
  // loading and re-renders once it arrives so the checklist upgrades in place.
  function computeResult() {
    state.result = buildResultModel(state.code, state.model, state.answers,
      { record: getRecord(state.code), docMaster: DOC_MASTER });
    if (!DOC_MASTER && typeof fetch === 'function') {
      loadDocMaster().then(function (dm) {
        if (dm && state.view === 'result' && state.modal && state.modal.classList.contains('open')) {
          state.result = buildResultModel(state.code, state.model, state.answers, { record: getRecord(state.code), docMaster: dm });
          renderResultView();
        }
      });
    }
  }

  function goNext() {
    var step = state.steps[state.stepIndex];
    if (!state.answers[step.id]) return;
    if (state.stepIndex < state.steps.length - 1) { state.stepIndex++; renderFlow(); focusFirst(); return; }
    computeResult();
    state.view = 'result';
    renderGuide();
    focusFirst();
  }
  function goBack() {
    if (state.view === 'result') { state.view = 'flow'; renderGuide(); focusFirst(); return; }
    if (state.stepIndex > 0) { state.stepIndex--; renderFlow(); focusFirst(); }
  }

  function numSection(n, titleStr, inner) {
    return '<div class="csg-section"><p class="csg-section-title"><span class="csg-num" aria-hidden="true">' + n + '</span>' + esc(titleStr) + '</p>' + inner + '</div>';
  }
  function docChecklistHtml(docs) {
    return '<div class="csg-checklist">' + docs.map(function (d) {
      return '<label class="csg-chk"><input type="checkbox"><span>' + esc(d.name) + '</span></label>';
    }).join('') + '</div>';
  }

  function renderResultView() {
    var titleEl = state.modal.querySelector('#csgModalTitle');
    var body = state.modal.querySelector('#csgBody');
    var m = state.result;
    titleEl.textContent = state.code + ' · ' + S('recStartTitle');
    setStepCount('');
    setProgress(100);

    var html = '<div class="csg-result" role="status" aria-live="polite">';
    html += '<p class="csg-result-title">' + esc(tpl('resultTitleTpl', state.code)) + '</p>';
    html += '<div class="csg-route-chip">' + esc(m.subLabel || (state.code + ' · ' + S('unsureType'))) + '</div>';
    html += '<p class="csg-meta"><strong>' + esc(S('matchedProcedure')) + ':</strong> ' + esc(m.procLabel || S('unsureProcedure')) + '</p>';
    if (m.noteKey) html += '<div class="csg-note">' + esc(S(m.noteKey)) + '</div>';

    // 1. First steps
    html += numSection('1', S('resFirstSteps'), '<ul class="csg-ul">' + m.firstSteps.map(function (s) { return '<li>' + esc(s) + '</li>'; }).join('') + '</ul>');
    // 2. Basic required documents — render a checklist from resolvable doc_master
    //    IDs; for prose/empty groups, point to the audit-safe detail (no raw
    //    prose re-rendered here) and mark needing confirmation.
    var detailBtn = '<div class="csg-actions"><button type="button" class="csg-act-btn primary" data-csg-act="detail">' + esc(S('viewFullDetail')) + '</button></div>';
    var basicInner;
    if (m.basicDocs && m.basicDocs.length) {
      basicInner = '<p class="csg-meta">' + esc(S('docChecklistIntro')) + '</p>' + docChecklistHtml(m.basicDocs) +
        (m.basicProse ? '<div class="csg-note">' + esc(S('docsMoreInDetail')) + '</div>' + detailBtn : '');
    } else if (m.docsAvailable) {
      basicInner = '<div class="csg-note">' + esc(S('docsInManualNote')) + '</div>' + detailBtn;
    } else {
      basicInner = '<p class="csg-meta"><span class="csg-badge-confirm">' + esc(S('officialSourceNeedsConfirm')) + '</span></p><div class="csg-note">' + esc(S('docsHandoffNote')) + '</div>' + detailBtn;
    }
    html += numSection('2', S('resBasicDocs'), basicInner);
    // 3. Documents that may be added for your situation
    var sitInner;
    if (m.sitDocs && m.sitDocs.length) {
      sitInner = docChecklistHtml(m.sitDocs) + (m.sitProse ? '<div class="csg-note">' + esc(S('docsMoreInDetail')) + '</div>' : '');
    } else {
      sitInner = '<div class="csg-note">' + esc(S('addDocsNote')) + '</div>';
    }
    html += numSection('3', S('resAddDocs'), sitInner);
    // 4. Procedure (generic process list)
    html += numSection('4', S('resProcedure'), '<ol class="csg-ul">' + m.procSteps.map(function (s) { return '<li>' + esc(s) + '</li>'; }).join('') + '</ol>');
    // 5. Official sources — source-backed manual references where present
    var srcInner;
    if (m.sourceRefs && m.sourceRefs.length) {
      srcInner = '<ul class="csg-ul">' + m.sourceRefs.map(function (r) {
        return '<li><strong>' + esc(S('sourceManualLabel')) + ':</strong> ' + esc(sourceRefText(r)) + '</li>';
      }).join('') + '</ul>';
    } else {
      srcInner = '<p class="csg-meta"><span class="csg-badge-confirm">' + esc(S('officialSourceNeedsConfirm')) + '</span></p>';
    }
    srcInner += '<div class="csg-note">' + esc(S('sourcesHandoffNote')) + '</div>';
    html += numSection('5', S('resSources'), srcInner);
    // 6. Next actions
    html += numSection('6', S('resNextActions'), '<div class="csg-actions">' +
      '<button type="button" class="csg-act-btn primary" data-csg-act="detail">' + esc(S('viewFullDetail')) + '</button>' +
      '<button type="button" class="csg-act-btn" data-csg-copy>' + esc(S('copyChecklist')) + '</button>' +
      '<button type="button" class="csg-act-btn" data-csg-act="restart">' + esc(S('restartShort')) + '</button>' +
    '</div>');

    html += '<div class="csg-safety">' + esc(S('safetyNote')) + '</div>';
    html += '</div>';

    body.innerHTML = html;
    body.scrollTop = 0;
    body.querySelectorAll('[data-csg-act]').forEach(function (btn) {
      btn.addEventListener('click', function () { footAction(btn.getAttribute('data-csg-act')); });
    });
    var copyBtn = body.querySelector('[data-csg-copy]');
    if (copyBtn) copyBtn.addEventListener('click', function () {
      var text = checklistText(state.code, m);
      var done = function (ok) { copyBtn.textContent = ok ? S('copied') : S('copyFail'); setTimeout(function () { copyBtn.textContent = S('copyChecklist'); }, 1800); };
      if (navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText(text).then(function () { done(true); }, function () { done(false); });
      else { try { var ta = document.createElement('textarea'); ta.value = text; ta.style.position = 'fixed'; ta.style.opacity = '0'; document.body.appendChild(ta); ta.select(); document.execCommand('copy'); document.body.removeChild(ta); done(true); } catch (e) { done(false); } }
    });

    renderFooter([
      { label: S('restartShort'), action: 'restart' },
      { label: S('close'), action: 'close', primary: true }
    ]);
  }

  /* ----------------------------------------------------- public API (tests) */
  var api = {
    TARGETS: TARGETS,
    buildSteps: buildSteps,
    buildResultModel: buildResultModel,
    recStartBlockHtml: recStartBlockHtml,
    checklistText: checklistText,
    selectableSubcodes: selectableSubcodes,
    availableProcedures: availableProcedures,
    open: open,
    close: close,
    isOpen: function () { return !!(state.modal && state.modal.classList.contains('open')); },
    // exposed for the offline contract test:
    buildDocInfo: buildDocInfo,
    buildDocMasterMap: buildDocMasterMap,
    S: S, _state: state
  };
  if (typeof globalThis !== 'undefined') globalThis.ParadisoStatusGuide = api;

  if (typeof document === 'undefined') return;

  // Warm the doc_master cache so the result checklist is ready by the time the
  // user finishes the flow (graceful: falls back to the handoff if it fails).
  try { loadDocMaster(); } catch (e) { /* non-fatal */ }

  /* ----------------------------------------------- search-result integration */
  function injectAll() {
    TARGETS.forEach(function (code) { try { injectRecStart(code); } catch (e) { /* non-fatal */ } });
  }
  document.addEventListener('paradiso:results-rendered', function () {
    // Cards render synchronously before this event; inject the recommended-start
    // block at the top of each visible (open) target card.
    injectAll();
  });
  document.addEventListener('paradiso:landing-reset', function () {
    if (state.modal && state.modal.classList.contains('open')) close();
  });
  window.addEventListener('paradiso-language-applied', function () {
    if (state.modal && state.modal.classList.contains('open')) { try { renderGuide(); } catch (e) {} }
    try { injectAll(); } catch (e) {}
  });
})();
