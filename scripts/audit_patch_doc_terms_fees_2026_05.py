#!/usr/bin/env python3
from __future__ import annotations

import json
import re
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(".")
VISA_DATA = ROOT / "visa_data.json"
BACKEND_VISAS = ROOT / "backend/data/visas.json"
SCENARIO_HELP = ROOT / "data/scenario_help_records.json"
INDEX_HTML = ROOT / "index.html"

OUT_MD = ROOT / "docs/data/DOC_TERM_FEE_NORMALIZATION_AUDIT_2026_05.md"
OUT_JSON = ROOT / "docs/data/doc_term_fee_normalization_audit_2026_05.json"
UI_AUDIT = ROOT / "docs/audits/DOC_TERM_FEE_DISPLAY_FIX_2026_05.md"

MANUAL_PATHS = [
    "docs/source-manuals/2026-05/stay_manual_2026_05.pdf",
    "docs/source-manuals/2026-05/visa_manual_2026_05.pdf",
    "docs/source-manuals/2026-05/체류민원 안내매뉴얼_260521.pdf",
    "docs/source-manuals/2026-05/사증발급 안내매뉴얼_260521.pdf",
]

LAW_AUDIT_DOC = ROOT / "docs/integrations/PUBLIC_DATA_AND_LAW_GROUNDING_AUDIT.md"

DOC_LABEL_KEYS = {
    "name", "title", "label", "text", "doc", "document", "item", "requirement",
    "ko", "koName", "displayName", "desc", "description", "note"
}

DOC_PATH_HINTS = (
    "doc", "docs", "document", "documents", "req", "required",
    "addreq", "requiredocs", "requirements", "checklist",
    "서류", "구비", "필수", "추가"
)

FEE_BASELINES = {
    "foreignRegistration": {
        "labelKo": "외국인등록",
        "items": [
            {"name": "외국인등록증 발급 수수료", "amountKRW": 35000, "display": "외국인등록증 발급 수수료 35,000원"}
        ],
    },
    "extension": {
        "labelKo": "체류기간 연장",
        "items": [
            {"name": "체류기간 연장허가 수수료", "amountKRW": 60000, "display": "체류기간 연장허가 정부수입인지 60,000원"}
        ],
    },
    "statusChange": {
        "labelKo": "체류자격 변경",
        "items": [
            {"name": "체류자격 변경허가 수수료", "amountKRW": 100000, "display": "체류자격 변경허가 정부수입인지 100,000원"},
            {"name": "외국인등록증 재발급/교체 수수료", "amountKRW": 35000, "display": "등록증 발급이 필요한 경우 35,000원 별도 가능"}
        ],
    },
    "grantStatus": {
        "labelKo": "체류자격 부여",
        "items": [
            {"name": "체류자격 부여 수수료", "amountKRW": 80000, "display": "체류자격 부여 정부수입인지 80,000원"},
            {"name": "외국인등록증 발급 수수료", "amountKRW": 35000, "display": "외국인등록 대상자는 등록증 발급 수수료 35,000원 별도"}
        ],
    },
    "visaIssuance": {
        "labelKo": "사증 발급",
        "items": [
            {"name": "재외공관 사증발급 수수료", "amountKRW": None, "display": "재외공관 사증발급 수수료는 국적, 사증 종류, 공관 기준에 따라 달라짐"}
        ],
    },
}

CANONICAL_REPLACEMENTS = [
    (re.compile(r"^신청서\s*\(?별지\s*제?34호\s*서식\)?$"), "통합신청서(별지 제34호 서식)"),
    (re.compile(r"^통합신청서\s*\(?별지\s*제?34호\s*서식\)?$"), "통합신청서(별지 제34호 서식)"),
    (re.compile(r"^통합신청서$"), "통합신청서(별지 제34호 서식)"),
    (re.compile(r"^신청서$"), "통합신청서(별지 제34호 서식)"),
    (re.compile(r"^여권$"), "여권 원본 및 인적사항면 사본"),
    (re.compile(r"^여권\s*원본\s*및\s*사본$"), "여권 원본 및 인적사항면 사본"),
    (re.compile(r"^외국인등록증$"), "외국인등록증 원본 및 사본"),
    (re.compile(r"^외국인등록증\s*\(또는\s*거소증\)\s*원본\s*및\s*사본$"), "외국인등록증 원본 및 사본(거소증 해당자 포함)"),
    (re.compile(r"^표준규격사진\s*1매$"), "표준규격사진 1매(3.5×4.5cm, 최근 6개월)"),
    (re.compile(r"^수수료$"), "수수료(절차별 정부수입인지/카드 발급 수수료 확인)"),
    (re.compile(r"^혼인관계증명서$"), "혼인관계증명서(상세)"),
    (re.compile(r"^기본증명서$"), "기본증명서(상세)"),
    (re.compile(r"^가족관계증명서$"), "가족관계증명서(상세)"),
]

COMBINED_CORE_DOC_RE = re.compile(
    r"(신청서|통합신청서).*(여권).*(표준규격사진|사진).*(수수료)"
)

def load_json(path: Path, fallback: Any = None) -> Any:
    if not path.exists():
        return fallback
    return json.loads(path.read_text(encoding="utf-8"))

def write_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

def clean_spaces(value: str) -> str:
    return re.sub(r"\s+", " ", str(value)).strip()

def normalize_doc_label(value: str) -> str:
    original = clean_spaces(value)
    if not original:
        return original

    text = original
    for pattern, replacement in CANONICAL_REPLACEMENTS:
        if pattern.search(text):
            return replacement

    text = re.sub(r"신청서\s*\(?별지\s*제?34호\s*서식\)?", "통합신청서(별지 제34호 서식)", text)
    text = text.replace("정부수입인지, 절차별 금액은 수수료 안내 확인", "절차별 정부수입인지 금액은 수수료 안내 확인")
    text = text.replace("표준규격사진 1매", "표준규격사진 1매(3.5×4.5cm, 최근 6개월)")
    return clean_spaces(text)

def split_combined_core_docs(value: str) -> list[str] | None:
    text = clean_spaces(value)
    if not COMBINED_CORE_DOC_RE.search(text):
        return None

    return [
        "통합신청서(별지 제34호 서식)",
        "여권 원본 및 인적사항면 사본",
        "표준규격사진 1매(3.5×4.5cm, 최근 6개월)",
        "수수료(절차별 정부수입인지/카드 발급 수수료 확인)",
    ]

def path_is_doc_like(path: list[str]) -> bool:
    joined = ".".join(str(x).lower() for x in path)
    return any(h in joined for h in DOC_PATH_HINTS)

def normalize_doc_tree(obj: Any, path: list[str], audit: dict[str, Any], record_code: str) -> Any:
    if isinstance(obj, list):
        new_items = []
        changed = False
        doc_like = path_is_doc_like(path)

        for item in obj:
            if doc_like and isinstance(item, str):
                split = split_combined_core_docs(item)
                if split:
                    new_items.extend(split)
                    audit["split_combined_doc_items"].append({
                        "code": record_code,
                        "path": ".".join(path),
                        "before": item,
                        "after": split,
                    })
                    changed = True
                    continue

                normalized = normalize_doc_label(item)
                if normalized != item:
                    audit["normalized_doc_terms"].append({
                        "code": record_code,
                        "path": ".".join(path),
                        "before": item,
                        "after": normalized,
                    })
                    changed = True
                new_items.append(normalized)
            else:
                new_items.append(normalize_doc_tree(item, path, audit, record_code))

        return new_items if changed else new_items

    if isinstance(obj, dict):
        out = {}
        for key, value in obj.items():
            key_path = path + [str(key)]
            if path_is_doc_like(key_path) and isinstance(value, str) and str(key) in DOC_LABEL_KEYS:
                normalized = normalize_doc_label(value)
                if normalized != value:
                    audit["normalized_doc_terms"].append({
                        "code": record_code,
                        "path": ".".join(key_path),
                        "before": value,
                        "after": normalized,
                    })
                out[key] = normalized
            else:
                out[key] = normalize_doc_tree(value, key_path, audit, record_code)
        return out

    return obj

def add_fee_metadata(record: dict[str, Any], audit: dict[str, Any]) -> None:
    code = str(record.get("code") or "")
    current = record.get("feeInfo")
    if not isinstance(current, dict):
        current = {}

    existing_patch = current.get("paradisoDefault202605")
    baseline = {
        "sourceBasis": "2026.5 체류민원/사증 매뉴얼 및 출입국관리법 시행규칙 수수료표 기준의 표시용 기본 수수료 메타데이터",
        "verified": False,
        "needsManualReview": True,
        "displayCaution": "수수료는 면제, 감면, 온라인 신청, 관할기관 안내, 등록증 발급 필요 여부에 따라 달라질 수 있으므로 최종 금액은 HiKorea, 1345, 관할 출입국·외국인관서에서 확인해야 함.",
        "procedures": FEE_BASELINES,
    }

    if existing_patch != baseline:
        current["paradisoDefault202605"] = baseline
        record["feeInfo"] = current
        audit["fee_metadata_added_or_updated"].append(code)

def sync_backend_copy() -> None:
    BACKEND_VISAS.parent.mkdir(parents=True, exist_ok=True)
    BACKEND_VISAS.write_text(VISA_DATA.read_text(encoding="utf-8"), encoding="utf-8")

def sync_scenario_shadows(live_data: list[dict[str, Any]], audit: dict[str, Any]) -> None:
    if not SCENARIO_HELP.exists():
        return

    store = load_json(SCENARIO_HELP, {})
    if not isinstance(store, dict) or not isinstance(store.get("records"), list):
        return

    by_index_code = {}
    by_code = {}
    for idx, record in enumerate(live_data):
        code = str(record.get("code") or "")
        by_index_code[(idx, code)] = record
        by_code.setdefault(code, record)

    synced = []
    for envelope in store["records"]:
        if not isinstance(envelope, dict):
            continue

        idx = envelope.get("sourceVisaDataIndex")
        code = envelope.get("sourceVisaDataCode")
        live = by_index_code.get((idx, code)) or by_code.get(code)

        if isinstance(live, dict):
            if envelope.get("record") != live:
                envelope["record"] = deepcopy(live)
                synced.append(code)

    store["_docTermFeeShadowSync"] = {
        "updatedAt": "2026-05-26",
        "method": "copy_live_record_after_doc_term_fee_metadata_patch_for_e4_parity",
        "syncedCodes": sorted(set(str(x) for x in synced if x)),
        "legalContentCreated": False,
        "verifiedPromotion": False,
    }

    write_json(SCENARIO_HELP, store)
    audit["scenario_shadow_synced_codes"] = sorted(set(str(x) for x in synced if x))

def patch_index_html(audit: dict[str, Any]) -> None:
    text = INDEX_HTML.read_text(encoding="utf-8")
    changed = False

    css_marker = "DOC_TERM_FEE_UI_CSS_2026_05"
    css = r'''
/* DOC_TERM_FEE_UI_CSS_2026_05 */
.paradiso-fee-notice {
  margin: 0.75rem 0;
  padding: 0.85rem 0.95rem;
  border: 1px solid rgba(14, 163, 123, 0.28);
  border-left: 4px solid var(--p-emerald, #0EA37B);
  border-radius: 14px;
  background: color-mix(in srgb, var(--p-emerald, #0EA37B) 7%, #fff);
  color: var(--p-ink, #152823);
}
.paradiso-fee-notice strong {
  display: block;
  margin-bottom: 0.25rem;
  color: var(--p-emerald-deep, #085E48);
}
.paradiso-fee-notice small {
  display: block;
  margin-top: 0.35rem;
  color: var(--p-ink-mute, #5f6763);
  line-height: 1.5;
}
'''
    if css_marker not in text:
        text = text.replace("</style>", css + "\n</style>", 1)
        changed = True

    shim_marker = "DOC_TERM_FEE_UI_SHIM_2026_05"
    shim = r'''
<script id="DOC_TERM_FEE_UI_SHIM_2026_05">
(function () {
  "use strict";

  const FEE_BY_LABEL = [
    { test: /외국인등록/, title: "수수료 안내", body: "외국인등록증 발급 수수료 35,000원" },
    { test: /체류기간\s*연장|연장/, title: "수수료 안내", body: "체류기간 연장허가 정부수입인지 60,000원" },
    { test: /체류자격\s*변경|변경/, title: "수수료 안내", body: "체류자격 변경허가 정부수입인지 100,000원. 등록증 발급이 필요한 경우 35,000원 별도 가능" },
    { test: /최초\s*신청|입국\s*전|신규|사증/, title: "수수료 안내", body: "사증발급 수수료는 국적, 사증 종류, 재외공관 기준에 따라 달라짐. 국내 체류자격 부여는 정부수입인지 80,000원, 외국인등록 대상자는 등록증 발급 수수료 35,000원 별도 가능" }
  ];

  const TERM_REPLACEMENTS = [
    [/^신청서$/, "통합신청서(별지 제34호 서식)"],
    [/^통합신청서$/, "통합신청서(별지 제34호 서식)"],
    [/^신청서\s*\(?별지\s*제?34호\s*서식\)?$/, "통합신청서(별지 제34호 서식)"],
    [/^여권$/, "여권 원본 및 인적사항면 사본"],
    [/^표준규격사진\s*1매$/, "표준규격사진 1매(3.5×4.5cm, 최근 6개월)"],
    [/^수수료$/, "수수료(절차별 금액 아래 수수료 안내 확인)"],
    [/^혼인관계증명서$/, "혼인관계증명서(상세)"],
    [/^기본증명서$/, "기본증명서(상세)"],
    [/^가족관계증명서$/, "가족관계증명서(상세)"]
  ];

  function clean(value) {
    return String(value || "").replace(/\s+/g, " ").trim();
  }

  function normalizeTerm(value) {
    let text = clean(value);
    for (const pair of TERM_REPLACEMENTS) {
      if (pair[0].test(text)) return pair[1];
    }
    text = text.replace(/신청서\s*\(?별지\s*제?34호\s*서식\)?/g, "통합신청서(별지 제34호 서식)");
    text = text.replace(/표준규격사진\s*1매/g, "표준규격사진 1매(3.5×4.5cm, 최근 6개월)");
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
    const candidates = Array.from(card.querySelectorAll(".doc-item, .doc-card, .docs-list li, .manual-doc-item, .doc-group li, .doc-group-card"));
    for (const el of candidates) {
      if (el.dataset.paradisoDocTermNormalized === "1") continue;
      const text = clean(el.textContent);
      if (!text || text.length > 90) continue;

      const normalized = normalizeTerm(text);
      if (normalized && normalized !== text) {
        el.textContent = normalized;
        el.dataset.paradisoDocTermNormalized = "1";
      }
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

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", install);
  } else {
    install();
  }
})();
</script>
'''
    if shim_marker not in text:
        text = text.replace("</body>", shim + "\n</body>", 1)
        changed = True

    if changed:
        INDEX_HTML.write_text(text, encoding="utf-8")

    audit["index_html_doc_term_fee_shim_added"] = changed

def main() -> None:
    data = load_json(VISA_DATA)
    if not isinstance(data, list):
        raise SystemExit("visa_data.json must be a list")

    law_audit_text = LAW_AUDIT_DOC.read_text(encoding="utf-8") if LAW_AUDIT_DOC.exists() else ""
    law_runtime_active = not (
        "declared only" in law_audit_text
        or "runtime inactive" in law_audit_text
        or "does not call public-data APIs" in law_audit_text
        or "does not call National Law Information" in law_audit_text
    )

    audit = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "scope": "all-record document terminology audit/normalization and fee display metadata",
        "manual_files_present": {path: Path(path).exists() for path in MANUAL_PATHS},
        "law_public_data_runtime_active_detected": law_runtime_active,
        "law_public_data_note": "External law/public-data runtime integration is not used by this patch; repository-local manual/data artifacts are used conservatively.",
        "records_checked": len(data),
        "normalized_doc_terms": [],
        "split_combined_doc_items": [],
        "fee_metadata_added_or_updated": [],
        "scenario_shadow_synced_codes": [],
        "index_html_doc_term_fee_shim_added": False,
        "guardrails": {
            "created_new_records": False,
            "deleted_records": False,
            "promoted_verified_true": False,
            "external_law_api_called": False,
            "backend_code_changed": False,
        },
    }

    patched = []
    for record in data:
        if not isinstance(record, dict):
            continue
        code = str(record.get("code") or "")
        before = json.dumps(record, ensure_ascii=False, sort_keys=True)

        normalized_record = normalize_doc_tree(record, [code], audit, code)
        record.clear()
        record.update(normalized_record)

        add_fee_metadata(record, audit)

        after = json.dumps(record, ensure_ascii=False, sort_keys=True)
        if before != after:
            patched.append(code)

    audit["records_touched"] = sorted(set(patched))

    write_json(VISA_DATA, data)
    sync_backend_copy()
    sync_scenario_shadows(data, audit)
    patch_index_html(audit)

    audit["normalized_doc_term_count"] = len(audit["normalized_doc_terms"])
    audit["split_combined_doc_item_count"] = len(audit["split_combined_doc_items"])
    audit["fee_metadata_record_count"] = len(set(audit["fee_metadata_added_or_updated"]))

    write_json(OUT_JSON, audit)

    lines = []
    lines.append("# Document Term and Fee Normalization Audit - 2026.5")
    lines.append("")
    lines.append("## Scope")
    lines.append("")
    lines.append("This patch audits all `visa_data.json` records and conservatively normalizes common document terms and fee-display metadata.")
    lines.append("")
    lines.append("## Source/API status")
    lines.append("")
    lines.append(audit["law_public_data_note"])
    lines.append("")
    lines.append("## Manual files checked")
    lines.append("")
    for path, exists in audit["manual_files_present"].items():
        lines.append(f"- `{path}`: {'present' if exists else 'not found'}")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Records checked: `{audit['records_checked']}`")
    lines.append(f"- Records touched: `{len(audit['records_touched'])}`")
    lines.append(f"- Normalized document terms: `{audit['normalized_doc_term_count']}`")
    lines.append(f"- Split combined document items: `{audit['split_combined_doc_item_count']}`")
    lines.append(f"- Fee metadata records updated: `{audit['fee_metadata_record_count']}`")
    lines.append(f"- Scenario/help shadow records synced: `{len(audit['scenario_shadow_synced_codes'])}`")
    lines.append("")
    lines.append("## Canonical examples")
    lines.append("")
    lines.append("- `신청서`, `통합신청서`, `신청서(별지 제34호 서식)` -> `통합신청서(별지 제34호 서식)`")
    lines.append("- `여권` -> `여권 원본 및 인적사항면 사본`")
    lines.append("- `표준규격사진 1매` -> `표준규격사진 1매(3.5×4.5cm, 최근 6개월)`")
    lines.append("- `수수료` -> `수수료(절차별 정부수입인지/카드 발급 수수료 확인)`")
    lines.append("")
    lines.append("## Fee display baseline")
    lines.append("")
    lines.append("- 외국인등록: 외국인등록증 발급 수수료 35,000원")
    lines.append("- 체류기간 연장: 정부수입인지 60,000원")
    lines.append("- 체류자격 변경: 정부수입인지 100,000원, 등록증 발급 필요 시 35,000원 별도 가능")
    lines.append("- 체류자격 부여: 정부수입인지 80,000원, 외국인등록 대상자는 등록증 발급 수수료 35,000원 별도 가능")
    lines.append("- 사증발급: 국적, 사증 종류, 재외공관 기준에 따라 달라짐")
    lines.append("")
    lines.append("## Guardrails")
    lines.append("")
    lines.append("- No new visa/status records.")
    lines.append("- No record deletion.")
    lines.append("- No `verified=true` promotion.")
    lines.append("- No backend code changes.")
    lines.append("- No external law API call.")
    lines.append("- Fee metadata is display metadata and keeps final-confirmation warning.")
    lines.append("")
    lines.append("## Manual QA")
    lines.append("")
    lines.append("- [ ] Search `F-6`.")
    lines.append("- [ ] Confirm document terms are consistent across required/common/procedure sections.")
    lines.append("- [ ] Confirm the active procedure shows a fee notice.")
    lines.append("- [ ] Check `외국인등록` fee display.")
    lines.append("- [ ] Check `체류기간 연장` fee display.")
    lines.append("- [ ] Check `체류자격 변경` fee display.")
    lines.append("- [ ] Search `F-1-6`, `E-7-4`, `F-2-7` to confirm prior alias behavior still works.")
    lines.append("")
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")

    UI_AUDIT.write_text("""# Document Term and Fee Display Fix

## Issue

Mobile visual QA on `F-6` showed inconsistent document terminology and missing fee amount display.

## Change

- Normalized common document terms in `visa_data.json`.
- Synced `backend/data/visas.json`.
- Synced scenario/help shadow copies for resolver parity.
- Added fee-display metadata under `feeInfo.paradisoDefault202605`.
- Added an `index.html` UI shim to show procedure-specific fee notices and normalize visible document labels.

## Manual QA

- [ ] Search `F-6`.
- [ ] Check `외국인등록`.
- [ ] Check `체류기간 연장`.
- [ ] Check `체류자격 변경`.
- [ ] Confirm fee amounts are visible.
- [ ] Confirm document terminology is consistent.
- [ ] Confirm prior detail-code searches still work.
""", encoding="utf-8")

    print(json.dumps({
        "records_checked": audit["records_checked"],
        "records_touched": len(audit["records_touched"]),
        "normalized_doc_term_count": audit["normalized_doc_term_count"],
        "split_combined_doc_item_count": audit["split_combined_doc_item_count"],
        "fee_metadata_record_count": audit["fee_metadata_record_count"],
        "scenario_shadow_synced_codes": len(audit["scenario_shadow_synced_codes"]),
        "index_html_doc_term_fee_shim_added": audit["index_html_doc_term_fee_shim_added"],
        "audit_md": str(OUT_MD),
        "audit_json": str(OUT_JSON),
    }, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
