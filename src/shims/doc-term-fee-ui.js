// @ts-nocheck
/**
 * Legacy shim `DOC_TERM_FEE_UI_SHIM_2026_05` (Phase 3, moved verbatim from the inline <script> block in index.html).
 * Its install function used to be registered for DOMContentLoaded while the document was parsed; index.html
 * keeps that registration as a one-liner calling `Visable.shims.installDocTermFeeUi()`, so it still runs in the same
 * order relative to the main bootstrap and the other shims (ADR-009 addendum 4). Everything else is the
 * original IIFE; it reads the inline globals it always read (VISA_DATA, selectedLocale, LANGUAGE_OPTIONS, …) lazily.
 */
let __install;
(function () {
  "use strict";

  const FEE_BY_LABEL = [
    { test: /외국인등록/, title: "수수료 안내", body: "외국인등록증 발급 수수료 35,000원 (등기우편 수령 시 39,000원)" },
    { test: /체류기간\s*연장|연장/, title: "수수료 안내", body: "체류기간 연장허가 정부수입인지 60,000원" },
    { test: /체류자격\s*변경|변경/, title: "수수료 안내", body: "체류자격 변경허가 정부수입인지 100,000원. 등록증 발급이 필요한 경우 35,000원(등기우편 수령 시 39,000원) 별도 가능" },
    { test: /최초\s*신청|입국\s*전|신규|사증/, title: "수수료 안내", body: "사증발급 수수료는 국적, 사증 종류, 재외공관 기준에 따라 달라짐. 국내 체류자격 부여는 정부수입인지 80,000원, 외국인등록 대상자는 등록증 발급 수수료 35,000원(등기우편 수령 시 39,000원) 별도 가능" }
  ];

  const TERM_REPLACEMENTS = [
    // 신청서/통합신청서 wording is handled by paradisoCanonicalAppFormText (above).
    [/^여권$/, "여권 원본 및 사본"],
    [/^표준규격사진\s*1매$/, "표준규격사진 1매(3.5×4.5cm, 최근 6개월)"],
    [/^수수료$/, "수수료(절차별 금액 아래 수수료 안내 확인)"],
    [/^혼인관계증명서$/, "혼인관계증명서(상세)"],
    [/^기본증명서$/, "기본증명서(상세)"],
    [/^가족관계증명서$/, "가족관계증명서(상세)"],
    [/^체류지\s+입증서류$/, "체류지 입증서류*"]
  ];

  function clean(value) {
    return String(value || "").replace(/\s+/g, " ").trim();
  }

  // Procedures that use 재외동포 통합신청서(별지 제1호서식) for F-4
  const F4_FORM_PROCEDURE_KEYS = new Set([
    'statusChange', 'registration', 'activitiesOutsideStatus', 'extension'
  ]);

  function normalizeTerm(value, statusCode, procedureKey) {
    let text = clean(value);

    // Application-form wording (single rule shared with the source-confirmed
    // renderer): handles exact rows, F-4 별지 제1호 variants and comma-joined rows.
    if (typeof paradisoCanonicalAppFormText === 'function') {
      const formFixed = paradisoCanonicalAppFormText(text, procedureKey, statusCode);
      if (formFixed !== text) return formFixed;
    }

    for (const pair of TERM_REPLACEMENTS) {
      if (pair[0].test(text)) return pair[1];
    }
    text = text.replace(/통합통합신청서/g, "통합신청서");
    text = text.replace(/(표준규격사진 1매\(3\.5×4\.5cm, 최근 6개월\))(?:\(3\.5×4\.5cm, 최근 6개월\))+/g, "$1");

    if (!/^통합신청서/.test(text)) {
      text = text.replace(/신청서\s*\(?별지\s*제?34호\s*서식\)?/g, "통합신청서 (신고서) [별지 제34호서식]");
    }

    if (!/표준규격사진\s*1매\(3\.5×4\.5cm, 최근 6개월\)/.test(text)) {
      text = text.replace(/표준규격사진\s*1매/g, "표준규격사진 1매(3.5×4.5cm, 최근 6개월)");
    }
    return text;
  }

  function activeProcedureLabel(card) {
    const active = card.querySelector(".procedure-tab.active, .doc-tab.active, [aria-selected='true']");
    if (active) return clean(active.textContent);

    const tabs = Array.from(card.querySelectorAll(".procedure-tab, .doc-tab, button"));
    const visible = tabs.find(el => /외국인등록|체류기간|연장|변경|최초|신규|사증/.test(clean(el.textContent)));
    return visible ? clean(visible.textContent) : "";
  }

  function feeForLabel(label) {
    return FEE_BY_LABEL.find(item => item.test.test(label)) || null;
  }

  function normalizeVisibleDocTerms(card) {
    const statusCode = card.dataset.visaCode || card.dataset.code || '';
    const candidates = Array.from(card.querySelectorAll(".doc-item, .doc-card, .docs-list li, .manual-doc-item, .doc-group li, .doc-group-card"));
    for (const el of candidates) {
      if (el.dataset.paradisoDocTermNormalized === "1") continue;
      const text = clean(el.textContent);
      if (!text || text.length > 200) continue;

      const procedureKey = el.closest('[data-procedure-panel]')?.dataset?.procedurePanel
          || el.closest('[data-docs-panel]')?.dataset?.docsPanel || '';
      if (el.children.length === 0) {
        const normalized = normalizeTerm(text, statusCode, procedureKey);
        if (normalized && normalized !== text) {
          el.textContent = normalized;
          el.dataset.paradisoDocTermNormalized = "1";
        }
        continue;
      }
      // Element has child markup (e.g. bilingual spans): rewrite text nodes only.
      const walker = document.createTreeWalker(el, NodeFilter.SHOW_TEXT);
      let node, changedAny = false;
      while ((node = walker.nextNode())) {
        const raw = node.nodeValue || '';
        const t = clean(raw);
        if (!t) continue;
        const n = paradisoCanonicalAppFormText(t, procedureKey, statusCode);
        if (n && n !== t) { node.nodeValue = n; changedAny = true; }
      }
      if (changedAny) el.dataset.paradisoDocTermNormalized = "1";
    }
  }

  function updateBareFeeCards(card, fee) {
    if (!fee) return;
    const candidates = Array.from(card.querySelectorAll(".doc-item, .doc-card, .docs-list li, .manual-doc-item, .doc-group li, .doc-group-card"));
    for (const el of candidates) {
      const text = clean(el.textContent);
      if (/^수수료($|\()/.test(text) || /절차별 금액은 수수료 안내 확인/.test(text)) {
        el.textContent = "수수료: " + fee.body;
        el.dataset.paradisoFeeExpanded = "1";
      }
    }
  }

  function insertFeeNotice(card, fee) {
    // Fee guidance is rendered by renderProcedureFeeBox inside the selected
    // procedure tab. Keep this legacy shim from injecting duplicate notices.
    return;
    if (!fee || card.querySelector(".paradiso-fee-notice")) return;

    const anchor =
      card.querySelector(".procedure-tabs, .doc-tabs") ||
      card.querySelector(".doc-group-grid") ||
      card.querySelector(".manual-section-title");

    if (!anchor || !anchor.parentElement) return;

    const box = document.createElement("div");
    box.className = "paradiso-fee-notice";
    box.innerHTML = "<strong>" + fee.title + "</strong><span>" + fee.body + "</span><small>수수료는 면제, 감면, 온라인 신청, 관할기관 안내, 등록증 발급 필요 여부에 따라 달라질 수 있으므로 최종 금액은 HiKorea, 1345 또는 관할 출입국·외국인관서에서 확인하세요.</small>";

    if (anchor.nextSibling) {
      anchor.parentElement.insertBefore(box, anchor.nextSibling);
    } else {
      anchor.parentElement.appendChild(box);
    }
  }

  function patchCard(card) {
    if (!card) return;
    normalizeVisibleDocTerms(card);
    const label = activeProcedureLabel(card);
    const fee = feeForLabel(label);
    updateBareFeeCards(card, fee);
    insertFeeNotice(card, fee);
  }

  function patchAll() {
    const cards = Array.from(document.querySelectorAll(".manual-result, .vc"));
    cards.forEach(patchCard);
  }

  function install() {
    patchAll();
    const target = document.getElementById("rlist") || document.body;
    if (target.dataset.docTermFeeShimInstalled === "1") return;
    target.dataset.docTermFeeShimInstalled = "1";

    const observer = new MutationObserver(patchAll);
    observer.observe(target, { childList: true, subtree: true, attributes: true, attributeFilter: ["class", "aria-selected"] });

    let ticks = 0;
    const timer = window.setInterval(function () {
      patchAll();
      ticks += 1;
      if (ticks > 15) window.clearInterval(timer);
    }, 350);
  }

  // Registration moved to index.html (a parse-time one-liner that calls this export), see module header.
  __install = install;
})();

export { __install as installDocTermFeeUi };
