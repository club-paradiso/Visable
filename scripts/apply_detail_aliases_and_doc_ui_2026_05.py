#!/usr/bin/env python3
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(".")
VISA_DATA = ROOT / "visa_data.json"
INDEX_HTML = ROOT / "index.html"
SCENARIO_HELP = ROOT / "data/scenario_help_records.json"
LAW_AUDIT_DOC = ROOT / "docs/integrations/PUBLIC_DATA_AND_LAW_GROUNDING_AUDIT.md"

OUT_MD = ROOT / "docs/data/DETAIL_CODE_ALIAS_AND_DOCS_UI_FIX_2026_05.md"
OUT_JSON = ROOT / "docs/data/detail_code_alias_and_docs_ui_fix_2026_05.json"
OUT_UI = ROOT / "docs/audits/SEARCH_DETAIL_CODE_AND_DOCS_UI_FIX.md"

MANUAL_PATHS = [
    "docs/source-manuals/2026-05/stay_manual_2026_05.pdf",
    "docs/source-manuals/2026-05/visa_manual_2026_05.pdf",
    "docs/source-manuals/2026-05/체류민원 안내매뉴얼_260521.pdf",
    "docs/source-manuals/2026-05/사증발급 안내매뉴얼_260521.pdf",
]

DETAIL_CODE_RE = re.compile(r"\b[A-Z]-\d{1,2}(?:-[A-Z0-9]+)+\b")
WATCHED_CODES = ["F-1-6", "E-7-4", "F-2-7", "D-10-T", "F-2-R", "F-4-R", "F-5-T"]

def norm(value: Any) -> str:
    return str(value or "").strip().upper()

def compact_text(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True)

def load_json(path: Path, fallback: Any) -> Any:
    if not path.exists():
        return fallback
    return json.loads(path.read_text(encoding="utf-8"))

def write_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

def ordered_unique(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        x = norm(item)
        if x and x not in seen:
            seen.add(x)
            out.append(x)
    return out

def derive_parents(detail_code: str) -> list[str]:
    parts = norm(detail_code).split("-")
    out: list[str] = []
    while len(parts) > 2:
        parts = parts[:-1]
        out.append("-".join(parts))
    return out

def add_alias(record: dict[str, Any], alias: str, reason: str, audit: dict[str, Any]) -> bool:
    alias = norm(alias)
    if not alias:
        return False

    current = ordered_unique([str(x) for x in record.get("searchAliases", []) or []])
    if alias in current:
        return False

    current.append(alias)
    record["searchAliases"] = current

    alias_audit = record.get("_searchAliasAudit")
    if not isinstance(alias_audit, dict):
        alias_audit = {}

    generated = alias_audit.get("generatedAliases")
    if not isinstance(generated, list):
        generated = []

    generated.append({
        "alias": alias,
        "reason": reason,
        "source": "existing_repo_json_and_2026_05_manual_audit",
        "sourceManualVersion": "2026.5",
        "legalContentCreated": False,
        "verified": False,
        "needsManualReview": True,
        "updatedAt": "2026-05-26",
    })

    alias_audit["generatedAliases"] = generated
    alias_audit["method"] = "detail_code_alias_extraction_without_new_legal_content"
    alias_audit["verified"] = False
    alias_audit["needsManualReview"] = True
    record["_searchAliasAudit"] = alias_audit

    audit["added_aliases"].append({
        "record_code": record.get("code"),
        "record_name": record.get("name"),
        "alias": alias,
        "reason": reason,
    })
    return True

def collect_scenario_records() -> list[dict[str, Any]]:
    store = load_json(SCENARIO_HELP, {})
    if not isinstance(store, dict):
        return []
    out = []
    for item in store.get("records", []) or []:
        if isinstance(item, dict) and isinstance(item.get("record"), dict):
            out.append(item)
    return out

def patch_visa_data() -> dict[str, Any]:
    data = load_json(VISA_DATA, None)
    if not isinstance(data, list):
        raise SystemExit("visa_data.json must be a list")

    manual_files = {path: Path(path).exists() for path in MANUAL_PATHS}

    law_audit_text = LAW_AUDIT_DOC.read_text(encoding="utf-8") if LAW_AUDIT_DOC.exists() else ""
    law_runtime_active = not (
        "declared only" in law_audit_text
        or "runtime inactive" in law_audit_text
        or "does not call public-data APIs" in law_audit_text
        or "does not call National Law Information" in law_audit_text
    )

    audit: dict[str, Any] = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "scope": "detail-code search metadata and index.html UI/search resolver patch",
        "manual_files_present": manual_files,
        "law_public_data_runtime_active_detected": law_runtime_active,
        "law_public_data_note": (
            "Repository audit suggests law/public-data API integration is active; this patch still avoids external legal-content mutation."
            if law_runtime_active
            else "Repository audit indicates law/public-data API integration is declared-only or runtime-inactive, so this patch does not fetch or generate external legal content."
        ),
        "added_aliases": [],
        "guardrails": {
            "created_new_records": False,
            "deleted_records": False,
            "modified_legal_requirement_text": False,
            "promoted_verified_true": False,
            "external_law_api_called": False,
            "backend_changed": False,
            "search_metadata_changed": True,
            "index_html_changed": True,
        },
    }

    by_code: dict[str, dict[str, Any]] = {}
    for record in data:
        if isinstance(record, dict) and record.get("code"):
            by_code[norm(record.get("code"))] = record

    detail_tokens_by_source: dict[str, set[str]] = {}

    # 1. Add aliases from existing live visa_data content.
    for record in data:
        if not isinstance(record, dict) or not record.get("code"):
            continue

        parent_code = norm(record.get("code"))

        for sub in record.get("subCodes", []) or []:
            if isinstance(sub, dict):
                sub_code = norm(sub.get("code"))
                if DETAIL_CODE_RE.fullmatch(sub_code):
                    add_alias(record, sub_code, "existing_subCodes_code", audit)
                    detail_tokens_by_source.setdefault(sub_code, set()).add(parent_code)

        for token in sorted(set(DETAIL_CODE_RE.findall(compact_text(record)))):
            if token != parent_code:
                add_alias(record, token, "existing_record_text_code_token", audit)
                detail_tokens_by_source.setdefault(token, set()).add(parent_code)

    # 2. Add aliases from scenario/help migration copies, attached only to existing live records.
    for item in collect_scenario_records():
        source_code = norm(item.get("sourceVisaDataCode"))
        rec = item.get("record") or {}
        record_code = norm(rec.get("code"))
        preferred_source = source_code or record_code or "scenario_help"

        for token in sorted(set(DETAIL_CODE_RE.findall(compact_text(rec)))):
            detail_tokens_by_source.setdefault(token, set()).add(preferred_source)

            if record_code in by_code:
                add_alias(by_code[record_code], token, "scenario_help_record_text_code_token", audit)

            if source_code in by_code:
                add_alias(by_code[source_code], token, "scenario_help_source_record_text_code_token", audit)

            for parent in derive_parents(token):
                if parent in by_code:
                    add_alias(by_code[parent], token, f"scenario_help_detail_code_parent_fallback:{preferred_source}", audit)
                    break

    # 3. Parent fallback for all collected detail tokens.
    for token, sources in sorted(detail_tokens_by_source.items()):
        for parent in derive_parents(token):
            if parent in by_code:
                add_alias(by_code[parent], token, f"detail_code_parent_fallback_from:{','.join(sorted(sources))}", audit)
                break

    # 4. Watch specific codes, but do not fabricate aliases if they were never found.
    watched = {}
    for code in WATCHED_CODES:
        holders = []
        for record in data:
            if not isinstance(record, dict):
                continue
            aliases = [norm(x) for x in record.get("searchAliases", []) or []]
            if code in aliases or code == norm(record.get("code")):
                holders.append(norm(record.get("code")))
        watched[code] = {
            "found_as_detail_token": code in detail_tokens_by_source,
            "source_records": sorted(detail_tokens_by_source.get(code, [])),
            "records_with_alias_or_code": sorted(set(holders)),
        }

    audit["watched_code_diagnostics"] = watched
    audit["added_alias_count"] = len(audit["added_aliases"])
    audit["records_touched"] = sorted(set(str(x["record_code"]) for x in audit["added_aliases"]))

    write_json(VISA_DATA, data)
    return audit

def patch_index_html() -> dict[str, Any]:
    path = INDEX_HTML
    text = path.read_text(encoding="utf-8")
    changed = False

    css_marker = "DOC_SECTION_UNIFICATION_CSS_2026_05"
    css = r'''
/* DOC_SECTION_UNIFICATION_CSS_2026_05
   Duplicate required-document summary is hidden when the detailed 구비서류/procedure section exists.
   This is UI unification only; underlying data remains intact.
*/
.doc-summary-duplicate-collapsed {
  display: none !important;
}
'''

    if css_marker not in text:
        if "</style>" not in text:
            raise SystemExit("Could not find </style> in index.html")
        text = text.replace("</style>", css + "\n</style>", 1)
        changed = True

    resolver_marker = "DETAIL_CODE_RESOLVER_SHIM_2026_05"
    resolver = r'''
<script id="DETAIL_CODE_RESOLVER_SHIM_2026_05">
(function () {
  "use strict";

  const DETAIL_CODE_EXACT = /^[A-Z]-\d{1,2}(?:-[A-Z0-9]+)+$/;

  function norm(value) {
    return String(value || "").trim().toUpperCase();
  }

  function deriveParents(code) {
    const parts = norm(code).split("-");
    const out = [];
    while (parts.length > 2) {
      parts.pop();
      out.push(parts.join("-"));
    }
    return out;
  }

  async function loadVisaDataForDetailResolver() {
    if (window.__paradisoDetailAliasData) return window.__paradisoDetailAliasData;
    try {
      const res = await fetch("visa_data.json", { cache: "no-store" });
      if (!res.ok) throw new Error("visa_data.json fetch failed: " + res.status);
      const data = await res.json();
      window.__paradisoDetailAliasData = Array.isArray(data) ? data : [];
      return window.__paradisoDetailAliasData;
    } catch (err) {
      console.warn("[Paradiso] detail-code resolver unavailable:", err);
      window.__paradisoDetailAliasData = [];
      return window.__paradisoDetailAliasData;
    }
  }

  function buildAliasMap(records) {
    const top = new Map();
    const alias = new Map();

    for (const record of records) {
      if (!record || !record.code) continue;
      const code = norm(record.code);
      top.set(code, code);

      const aliases = Array.isArray(record.searchAliases) ? record.searchAliases : [];
      for (const item of aliases) {
        const a = norm(item);
        if (a && !top.has(a) && !alias.has(a)) alias.set(a, code);
      }

      const subcodes = Array.isArray(record.subCodes) ? record.subCodes : [];
      for (const sub of subcodes) {
        const sc = norm(sub && sub.code);
        if (sc && !top.has(sc) && !alias.has(sc)) alias.set(sc, code);
      }
    }

    return { top, alias };
  }

  async function resolveDetailCodeQuery(query) {
    const q = norm(query);
    if (!DETAIL_CODE_EXACT.test(q)) return null;

    const records = await loadVisaDataForDetailResolver();
    const maps = buildAliasMap(records);

    if (maps.top.has(q)) return null;
    if (maps.alias.has(q)) return maps.alias.get(q);

    for (const parent of deriveParents(q)) {
      if (maps.top.has(parent)) return parent;
    }

    return null;
  }

  function installDetailResolver() {
    const form = document.getElementById("searchForm");
    const input = document.getElementById("q");
    if (!form || !input || form.dataset.detailCodeResolverInstalled === "1") return;

    form.dataset.detailCodeResolverInstalled = "1";

    form.addEventListener("submit", async function (event) {
      if (form.dataset.detailCodeResolving === "1") return;

      const original = input.value;
      const resolved = await resolveDetailCodeQuery(original);

      if (!resolved || norm(resolved) === norm(original)) return;

      event.preventDefault();
      event.stopImmediatePropagation();

      form.dataset.detailCodeResolving = "1";
      form.dataset.originalDetailCodeQuery = original;
      input.value = resolved;

      try {
        form.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
      } finally {
        window.setTimeout(function () {
          form.dataset.detailCodeResolving = "0";
          input.value = original;
        }, 280);
      }
    }, true);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", installDetailResolver);
  } else {
    installDetailResolver();
  }
})();
</script>
'''

    if resolver_marker not in text:
        if "</body>" not in text:
            raise SystemExit("Could not find </body> in index.html")
        text = text.replace("</body>", resolver + "\n</body>", 1)
        changed = True

    doc_marker = "DOC_SECTION_UNIFICATION_SHIM_2026_05"
    doc_shim = r'''
<script id="DOC_SECTION_UNIFICATION_SHIM_2026_05">
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

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", installDocSectionUnifier);
  } else {
    installDocSectionUnifier();
  }
})();
</script>
'''

    if doc_marker not in text:
        if "</body>" not in text:
            raise SystemExit("Could not find </body> in index.html")
        text = text.replace("</body>", doc_shim + "\n</body>", 1)
        changed = True

    if changed:
        path.write_text(text, encoding="utf-8")

    return {
        "index_html_changed": changed,
        "detail_resolver_installed": resolver_marker in path.read_text(encoding="utf-8"),
        "doc_unification_installed": doc_marker in path.read_text(encoding="utf-8"),
    }

def write_audits(alias_audit: dict[str, Any], index_audit: dict[str, Any]) -> None:
    audit = {
        **alias_audit,
        "index_html_patch": index_audit,
    }
    write_json(OUT_JSON, audit)

    lines: list[str] = []
    lines.append("# Detail-Code Alias and Document UI Fix - 2026.5")
    lines.append("")
    lines.append("## Scope")
    lines.append("")
    lines.append("This patch fixes two related runtime UX/data issues:")
    lines.append("")
    lines.append("1. Detail-code searches such as `F-1-6` should resolve to existing parent/scenario records instead of failing as missing top-level records.")
    lines.append("2. Result cards should not show a duplicate top-level `필수서류` summary when the detailed `구비서류` section is already rendered.")
    lines.append("")
    lines.append("## Source/API status")
    lines.append("")
    lines.append(alias_audit["law_public_data_note"])
    lines.append("")
    lines.append("## Manual files checked in repository")
    lines.append("")
    for path, exists in alias_audit["manual_files_present"].items():
        lines.append(f"- `{path}`: {'present' if exists else 'not found'}")
    lines.append("")
    lines.append("## Search alias changes")
    lines.append("")
    lines.append(f"- Added alias entries: {alias_audit['added_alias_count']}")
    lines.append(f"- Records touched: {len(alias_audit['records_touched'])}")
    lines.append("")
    lines.append("### Watched-code diagnostics")
    lines.append("")
    for code, info in alias_audit["watched_code_diagnostics"].items():
        holders = ", ".join(info["records_with_alias_or_code"]) if info["records_with_alias_or_code"] else "none"
        sources = ", ".join(info["source_records"]) if info["source_records"] else "none"
        lines.append(f"- `{code}`")
        lines.append(f"  - found_as_detail_token: `{info['found_as_detail_token']}`")
        lines.append(f"  - source_records: {sources}")
        lines.append(f"  - records_with_alias_or_code: {holders}")
    lines.append("")
    lines.append("## Index/UI changes")
    lines.append("")
    lines.append("- Added a detail-code resolver shim to `index.html`.")
    lines.append("- Added a document-section unification shim to hide duplicate `필수서류` summary sections when `구비서류` is present.")
    lines.append("- Added CSS for `.doc-summary-duplicate-collapsed`.")
    lines.append("")
    lines.append("## Guardrails")
    lines.append("")
    lines.append("- No new visa/status records.")
    lines.append("- No record deletion.")
    lines.append("- No legal requirement text changes.")
    lines.append("- No `verified=true` promotion.")
    lines.append("- No backend changes.")
    lines.append("- No external legal API call.")
    lines.append("")
    lines.append("## Manual QA")
    lines.append("")
    lines.append("- [ ] Search `F-1-6`.")
    lines.append("- [ ] Search `f-1-6`.")
    lines.append("- [ ] Search `F-1`.")
    lines.append("- [ ] Search `E-7-4`.")
    lines.append("- [ ] Search `F-2-7`.")
    lines.append("- [ ] Search `제주 무사증`.")
    lines.append("- [ ] Confirm autocomplete click and Enter search produce a result.")
    lines.append("- [ ] Open a result card with document sections.")
    lines.append("- [ ] Confirm duplicate top-level `필수서류` summary is hidden when `구비서류` exists.")
    lines.append("- [ ] Confirm `구비서류` tabs still render.")
    lines.append("")
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")

    OUT_UI.write_text("""# Search Detail-Code and Document UI Fix

## Issue

- Exact detail-code queries such as `F-1-6` can fail because they are not always top-level `visa_data.json[].code` records.
- Result cards can show a duplicate top-level `필수서류` summary above the detailed `구비서류` tabbed section.

## Change

- Adds conservative `searchAliases` metadata to existing `visa_data.json` records.
- Adds a detail-code resolver shim in `index.html`.
- Adds a document-section unification shim in `index.html`.
- Keeps underlying document data intact while hiding the duplicate summary in the UI.

## Guardrails

- No backend changes.
- No new visa/status records.
- No record deletion.
- No legal requirement text changes.
- No `verified=true` promotion.
- No external legal API call.

## Manual QA

- [ ] Search `F-1-6`.
- [ ] Search `f-1-6`.
- [ ] Search `F-1`.
- [ ] Search `E-7-4`.
- [ ] Search `F-2-7`.
- [ ] Search `제주 무사증`.
- [ ] Open a result card with document sections.
- [ ] Confirm duplicate top-level `필수서류` summary is hidden when `구비서류` exists.
- [ ] Confirm `구비서류` tabs still render.
""", encoding="utf-8")

def main() -> None:
    alias_audit = patch_visa_data()
    index_audit = patch_index_html()
    write_audits(alias_audit, index_audit)

    print(json.dumps({
        "added_alias_count": alias_audit["added_alias_count"],
        "records_touched": len(alias_audit["records_touched"]),
        "watched_code_diagnostics": alias_audit["watched_code_diagnostics"],
        "index_html_patch": index_audit,
        "audit_md": str(OUT_MD),
        "audit_json": str(OUT_JSON),
        "audit_ui": str(OUT_UI),
    }, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
