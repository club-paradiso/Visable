// @ts-nocheck
/**
 * Legacy shim `DOC_SECTION_UNIFICATION_SHIM_2026_05` (Phase 3, moved verbatim from the inline <script> block in index.html).
 * Its install function used to be registered for DOMContentLoaded while the document was parsed; index.html
 * keeps that registration as a one-liner calling `Visable.shims.installDocSectionUnifier()`, so it still runs in the same
 * order relative to the main bootstrap and the other shims (ADR-009 addendum 4). Everything else is the
 * original IIFE; it reads the inline globals it always read (VISA_DATA, selectedLocale, LANGUAGE_OPTIONS, …) lazily.
 */
let __install;
(function () {
  "use strict";

  function cleanText(value) {
    return String(value || "").replace(/\s+/g, " ").trim();
  }

  function isRequiredSummaryTitle(text) {
    const t = cleanText(text);
    return t === "필수서류" || /^required documents$/i.test(t) || /^required docs$/i.test(t);
  }

  function isDetailedDocsTitle(text) {
    const t = cleanText(text);
    return t === "구비서류" || /document checklist/i.test(t) || /documents by procedure/i.test(t);
  }

  function findSectionForTitle(titleEl, card) {
    return titleEl.closest(".manual-section")
      || titleEl.closest(".vs")
      || titleEl.closest("section")
      || titleEl.parentElement;
  }

  function cardHasDetailedDocumentSection(card) {
    if (!card) return false;
    if (card.querySelector(".procedure-tabs, .doc-group-grid, .procedure-docs, .doc-tabs")) return true;

    const titles = Array.from(card.querySelectorAll(".manual-section-title, h2, h3, h4, h5"));
    return titles.some(el => isDetailedDocsTitle(el.textContent));
  }

  function collapseDuplicateRequiredDocSummary(root) {
    const scope = root && root.querySelectorAll ? root : document;
    const cards = Array.from(scope.querySelectorAll(".manual-result, .vc"));

    for (const card of cards) {
      if (!cardHasDetailedDocumentSection(card)) continue;

      const titles = Array.from(card.querySelectorAll(".manual-section-title, h2, h3, h4, h5"));
      for (const title of titles) {
        if (!isRequiredSummaryTitle(title.textContent)) continue;
        if (title.closest(".procedure-panel, .procedure-variant-list, .doc-group-grid, .docs-section")) continue;

        const section = findSectionForTitle(title, card);
        if (!section || section === card) continue;

        section.classList.add("doc-summary-duplicate-collapsed");
        section.setAttribute("aria-hidden", "true");
        section.setAttribute("data-paradiso-doc-summary-unified", "true");
      }
    }
  }

  function installDocSectionUnifier() {
    collapseDuplicateRequiredDocSummary(document);

    const target = document.getElementById("rlist") || document.body;
    if (!target || target.dataset.docSectionUnifierInstalled === "1") return;
    target.dataset.docSectionUnifierInstalled = "1";

    const observer = new MutationObserver(function () {
      collapseDuplicateRequiredDocSummary(target);
    });

    observer.observe(target, { childList: true, subtree: true });

    let ticks = 0;
    const timer = window.setInterval(function () {
      collapseDuplicateRequiredDocSummary(target);
      ticks += 1;
      if (ticks > 12) window.clearInterval(timer);
    }, 400);
  }

  // Registration moved to index.html (a parse-time one-liner that calls this export), see module header.
  __install = installDocSectionUnifier;
})();

export { __install as installDocSectionUnifier };
