/*
 * Paradiso form-helper — Korean → Chinese display layer.
 *
 * form-helper.html fills official Korean PDF forms; its wizard renderer was
 * built Korean-only ("language toggle is cosmetic in MVP"). Rather than
 * refactor every render call, this layer translates the *displayed* Korean UI
 * text to Chinese at the DOM level, keyed by exact (trimmed) text — the same
 * efficient, single-source pattern used elsewhere (no per-call hardcoding).
 *
 * - zh-CN: replace Korean text nodes via the KO2ZH dictionary.
 * - zh-TW: replace via KO2ZH, then convert the Simplified result to Traditional
 *   through window.ParadisoZhT (zh-traditional.js).
 * Strings not in the dictionary stay Korean (graceful, extensible — the deep
 * official-form field labels can be added incrementally). The generated PDF is
 * unaffected (it remains the official Korean form / its 중문 병기본 variant).
 *
 * Skips SCRIPT/STYLE/TEXTAREA/INPUT and any [data-s2t="off"] subtree, and never
 * touches user-typed input values.
 */
(function (global) {
  'use strict';

  // Exact-match (trimmed) Korean → Simplified Chinese. Covers the entry/landing,
  // privacy notice, step navigation, instructions, form names and primary
  // actions. Extend this map to deepen coverage of the form-field wizard.
  var KO2ZH = {
    '한국어 · EN': '简体中文',
    '필수서류 작성 도우미': '必备材料填写助手',
    '출입국·외국인청 제출용 정본 서식을 단계별로 채워, 입력값이 정본 레이아웃 위에 배치된 PDF로 내려받습니다.': '分步填写用于向出入境·外国人厅提交的正本表格，并将您的输入排布在正本版式上，下载为 PDF。',
    '개인정보 안내': '个人信息须知',
    '개인정보 안내 — 입력하신 정보는 이 페이지(브라우저 메모리) 안에서만 사용됩니다. 서버로 전송되거나 저장되지 않으며, localStorage에도 저장하지 않습니다. PDF는 브라우저 안에서 빈 정본 서식 위에 직접 작성됩니다. 제출 전 최신 공식 서식과 관할 출입국·외국인청 안내를 확인하세요.': '个人信息须知 —— 您输入的信息仅在本页面（浏览器内存）中使用，不会发送或保存到服务器，也不会存入 localStorage。PDF 在浏览器内直接填写在空白正本表格上。提交前请确认最新官方表格和管辖出入境·外国人厅的指引。',
    '어떤 서류를 작성하시나요?': '您要填写哪种材料？',
    '작성할 서류를 선택하세요. 서류별로 근거 법령과 작성 흐름이 다릅니다.': '请选择要填写的材料。不同材料的依据法令和填写流程各不相同。',
    '단계 진행': '步骤进度',
    '신청/신고 유형 선택': '选择申请/申报类型',
    '어떤 신청 또는 신고를 하려 하십니까? 통합신청서에서 체크할 항목이 결정됩니다.': '您要进行哪种申请或申报？这将决定综合申请书上需勾选的项目。',
    '체류자격 및 목적': '居留资格及目的',
    '현재 체류자격과 신청 목적을 입력하세요. 해당 항목만 표시됩니다.': '请输入当前居留资格和申请目的。仅显示相关项目。',
    '기본 인적사항': '基本个人信息',
    '신청서 공통 기재 항목입니다. 민감한 정보는 이 페이지 안에서만 사용되며 외부로 전송되지 않습니다.': '这是申请书的通用填写项目。敏感信息仅在本页面中使用，不会向外部发送。',
    '절차별 추가정보': '各程序的补充信息',
    '선택하신 신청 유형에 따라 추가 입력 항목이 표시됩니다.': '将根据您所选的申请类型显示补充输入项目。',
    '누락 및 확인 필요 항목': '遗漏及需确认项目',
    '입력하신 내용을 바탕으로 확인이 필요한 사항을 정리합니다.': '根据您输入的内容，整理出需确认的事项。',
    '작성 가이드': '填写指南',
    '아래 내용을 참고하여 통합신청서를 작성하세요. 복사 또는 인쇄 후 출입국·외국인청 방문 시 활용하세요.': '请参考以下内容填写综合申请书。复制或打印后，可在访问出入境·外国人厅时使用。',
    '문서 미리보기 (A4)': '文档预览（A4）',
    '⬇ 정본 PDF 다운로드': '⬇ 下载正本 PDF',
    '⬇ 중문 병기본 PDF 다운로드': '⬇ 下载中文对照版 PDF',
    '신청서 미리보기': '申请书预览',
    '신청 유형을 선택하면\n미리보기가 업데이트됩니다.': '选择申请类型后\n预览会随之更新。',
    '신청 유형을 선택하면': '选择申请类型后',
    '미리보기가 업데이트됩니다.': '预览会随之更新。',
    '이전 단계': '上一步',
    '다음 단계': '下一步',
    '처음으로': '返回开始',
    '초기화': '重置',
    '복사': '复制',
    '인쇄': '打印',
    '기본 질문': '基本问题',
    '거주자 정보': '居住者信息',
    '제공자 정보': '提供者信息',
    '누락 확인': '遗漏确认',
    '작성 안내': '填写指引',
    '피보증외국인': '被保证外国人',
    '신원보증인': '身份保证人',
    '통합신청서(신고서)': '综合申请书（申报书）',
    '재외동포(F-4) 통합신청서 · 국내거소신고서': '在外同胞（F-4）综合申请书·国内居所申报书',
    '거주/숙소제공확인서': '居住/住所提供确认书',
    '신원보증서': '身份保证书',
    '통합신청서 / 국내거소신고서': '综合申请书 / 国内居所申报书',
    '외국인등록·체류기간 연장·체류자격 변경·재입국·체류지 변경 등. F-4 여부에 따라 서식이 갈립니다.': '外国人登录·居留期限延长·居留资格变更·再入境·居留地变更等。表格依是否为 F-4 而不同。',
    '체류지 입증용. 질문 2개로 작성 주체와 칸을 안내하고 정본 위에 채워 드립니다.': '用于居留地证明。通过 2 个问题指引填写主体和栏位，并填写在正本上。',
    '특정 체류자격에서만 요구. 보증인/피보증인 분기로 작성 칸을 안내하고 정본 위에 채워 드립니다.': '仅特定居留资格要求。按保证人/被保证人分支指引填写栏位，并填写在正本上。',
    '선택하신 신청 유형에 해당하는 추가 입력 항목이 없습니다. 다음 단계로 진행하세요.': '所选申请类型没有需要补充的输入项目。请进入下一步。',
    '입력값은 브라우저 메모리에만 저장되며 서버로 전송되지 않습니다(localStorage 미사용). 최신 공식 서식은 HiKorea 또는 1345에서 확인하세요.': '输入值仅保存在浏览器内存中，不会发送到服务器（不使用 localStorage）。最新官方表格请在 HiKorea 或 1345 确认。'
  };

  var RUN = /[一-鿿][·一-鿿]*/g; // for chaining S->T
  var SKIP_TAG = { SCRIPT: 1, STYLE: 1, TEXTAREA: 1, INPUT: 1, NOSCRIPT: 1 };
  function skip(el) { return !!(el && el.closest && el.closest('[data-s2t="off"]')); }

  var mode = 'ko';     // 'ko' | 'zh-CN' | 'zh-TW'
  function toTrad(s) {
    var zt = global.ParadisoZhT;
    return (zt && typeof zt.convert === 'function') ? zt.convert(s) : s;
  }
  function translate(text) {
    var key = text.replace(/\s+$/,'').replace(/^\s+/,'');
    var zh = KO2ZH.hasOwnProperty(key) ? KO2ZH[key] : null;
    if (zh == null) return null;
    return mode === 'zh-TW' ? toTrad(zh) : zh;
  }
  function processText(node) {
    var p = node.parentNode; if (!p) return;
    if (SKIP_TAG[p.nodeName] || skip(p)) return;
    var v = node.nodeValue; if (!v || !/[가-힣]/.test(v)) return;
    var zh = translate(v);
    if (zh != null && zh !== v) node.nodeValue = zh;
  }
  function walk(root) {
    if (!root) return;
    if (root.nodeType === 3) { processText(root); return; }
    if (root.nodeType !== 1 || SKIP_TAG[root.nodeName] || skip(root)) return;
    var tw = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, null);
    var n; while ((n = tw.nextNode())) processText(n);
  }

  var observer = null;
  function start() {
    if (observer) return;
    try { walk(document.body); } catch (e) {}
    if (typeof MutationObserver !== 'function') return;
    observer = new MutationObserver(function (muts) {
      for (var i = 0; i < muts.length; i++) {
        var m = muts[i];
        if (m.type === 'characterData') { if (m.target && m.target.nodeType === 3) processText(m.target); }
        else { for (var j = 0; j < m.addedNodes.length; j++) { var an = m.addedNodes[j]; if (an.nodeType === 3) processText(an); else if (an.nodeType === 1) walk(an); } }
      }
    });
    try { observer.observe(document.body, { subtree: true, childList: true, characterData: true }); } catch (e) {}
  }
  function stop() { if (observer) { try { observer.disconnect(); } catch (e) {} observer = null; } }

  function setMode(m) {
    mode = (m === 'zh-CN' || m === 'zh-TW') ? m : 'ko';
    if (mode === 'ko') { stop(); }
    else { start(); }
  }
  global.ParadisoFormI18n = { setMode: setMode, KO2ZH: KO2ZH };
})(typeof window !== 'undefined' ? window : this);
