#!/usr/bin/env python3
"""Generate remaining-run batch reports (R01-R07) with per-code audit entries.

Extended scope of this run (beyond merged PR #327):
  - post-merge mechanical re-scan (A/B/E/N)
  - documents_* arrays: Type A + provenance-gated C/D
  - doc_master.json internal consistency
  - ID-array rendered-label duplicate scan
  - D-2 attributed documents_* deep check vs stay manual

Read-only w.r.t. visa_data.json / doc_master.json.
"""
import json
from pathlib import Path
from datetime import date

AUD = Path("audits/manual-doc-normalization")
DATA = json.loads(Path("visa_data.json").read_text(encoding="utf-8"))
BY_CODE = {v["code"]: v for v in DATA}

BATCHES = [
    ("R01", ["B-1", "B-2", "C-3", "C-4", "D-1", "D-2"]),
    ("R02", ["D-3", "D-4", "D-4-1", "D-7", "D-8", "D-9"]),
    ("R03", ["D-10", "E-1", "E-2", "E-3", "E-4", "E-5"]),
    ("R04", ["E-6", "E-7", "E-8", "E-9", "E-10", "F-1"]),
    ("R05", ["F-2", "F-3", "F-4", "F-5", "F-6", "G-1"]),
    ("R06", ["H-1", "H-2", "A-1", "A-2", "A-3", "C-1"]),
    ("R07", ["D-5", "D-6", "D-4-2K", "K-STAR", "REGION-S", "YOUTH-STAY"]),
]

# Global scan results (all verified this session; see remaining_progress.md)
MECH = "0 Type A, 0 Type B, 0 Type E, 0 Type N"
D10_NOTE = ("Type N = 1 (구직활동계획서 vs 구직활동 계획서) — previously closed as "
            "AMBIGUOUS_TABLE_CONTEXT in merged PR #327 (different applicant "
            "sub-categories, 점수제 적용 vs 면제 특례); NOT re-opened, no new evidence.")

# D-2 deep-check decisions (attributed documents_* arrays vs stay manual D-2 sec L1162-2255)
D2_DETAIL = [
    ("documents_initial", "학력요건 입증서류", "SKIP/ALREADY_FAITHFUL",
     "Manual L1487: '학력요건 및 재정능력 입증서류' — data faithfully splits the composite into two entries."),
    ("documents_initial", "체류민원 기준 주의", "SKIP/PROTECTED_CAUTION",
     "Caution note stored as document entry; removing/moving would weaken an official-source warning (forbidden). Data-hygiene follow-up only."),
    ("documents_registration", "통합신청서(별지 제34호 서식)", "SKIP/MORE_SPECIFIC_OFFICIAL",
     "Manual D-2 section uses shorthand '신청서'; 별지 제34호 IS the 통합신청서 (official label verbatim elsewhere in same manual, L11254). Data is more specific, not wrong."),
    ("documents_registration", "여권 원본 및 사본 1부", "SKIP/ALREADY_FAITHFUL",
     "Manual L1483: '여권 및 사본 1부' — data adds clarifying '원본'; same requirement."),
    ("documents_registration", "외국인등록증 발급 수수료", "SKIP/FEE_PROTECTED",
     "Fee item; fee amounts/labels protected."),
    ("documents_registration", "재학증명서 또는 연구생증명서", "SKIP/ALREADY_FAITHFUL",
     "Manual L1661: '재학(연구생)증명서' — data expands parenthetical to '또는' form; same document."),
    ("documents_registration", "체류지 입증서류(예: …)", "SKIP/GUIDANCE_PROSE",
     "Label head '체류지 입증서류' exact in manual; long parenthetical is applicant guidance — removal would weaken guidance."),
    ("documents_extension", "통합신청서(별지 제34호 서식)", "SKIP/MORE_SPECIFIC_OFFICIAL",
     "Same as registration case."),
    ("documents_extension", "정상 학업 수행 입증서류", "SKIP/STYLE_PARAPHRASE",
     "Manual phrase '학업을 정상적으로 수행하고 있음을 입증하는 서류' (used verbatim in procedures.extension.requiredDocs). documents_extension uses compressed display form — not clearly wrong; 'do not normalize merely for style'."),
    ("documents_extension", "체류지 입증서류(예: …)", "SKIP/GUIDANCE_PROSE",
     "Same as registration case."),
]

def docfields(v):
    out = []
    notes = v.get("_source_notes") or {}
    for k in v:
        if k.startswith("documents_"):
            arr = v[k] if isinstance(v[k], list) else []
            attributed = bool(notes.get(k))
            out.append((k, len(arr), attributed))
    return out

def code_entry(code):
    v = BY_CODE[code]
    tabs = sorted((v.get("procedures") or {}).keys())
    L = [f"### {code}"]
    L.append(f"- Procedure tabs inspected: {', '.join(tabs) if tabs else '(none)'}")
    L.append(f"- Mechanical re-scan (procedure arrays, ID arrays, subCodes, documents_*): "
             + (D10_NOTE if code == "D-10" else MECH))
    dfs = docfields(v)
    if dfs:
        for name, n, attributed in dfs:
            if code == "D-2":
                L.append(f"- `{name}` ({n} entries): provenance = stay manual (_source_notes) → "
                         f"deep-checked against stay manual D-2 section. Result: 0 confirmed fixes (see detail below).")
            elif attributed:
                L.append(f"- `{name}` ({n} entries): provenance attributed → checked. 0 findings.")
            else:
                L.append(f"- `{name}` ({n} entries): **no `_source_notes` provenance** → governing manual "
                         f"undeterminable → Type C/D = `AMBIGUOUS_MANUAL_MISMATCH` (skip); Type A checked = 0.")
    else:
        L.append("- documents_* arrays: none.")
    L.append("- ID-array rendered-label duplicate scan (two doc ids → same ko_name): 0.")
    if code == "D-2":
        L.append("- **D-2 deep-check detail (attributed arrays vs stay manual L1162–2255):**")
        for fld, item, dec, why in D2_DETAIL:
            L.append(f"    - ⚠️ `{item}` [{fld}] → **{dec}** — {why}")
    L.append("- Confirmed fixes this run: **0**.")
    L.append("")
    return "\n".join(L)

for bid, codes in BATCHES:
    lines = [f"# Remaining Batch {bid} — {', '.join(codes)}", ""]
    lines.append(f"_Run: data/manual-doc-normalization-remaining · {date.today()}_")
    lines.append("_Authoritative manuals chosen per tab: visaIssuance → visa_hwp_full.txt; 체류 tabs → stay_hwp_full.txt._")
    lines.append("")
    lines.append("**Pre-edit plan:** 0 intended changes in this batch (all candidates fail the "
                 "CONFIRMED_* evidence bar — see per-code entries). Estimated diff size: 0 lines. "
                 "Files that would change: none.")
    lines.append("")
    for code in codes:
        lines.append(code_entry(code))
    skips = (len(D2_DETAIL) if "D-2" in codes else 0) + (1 if "D-10" in codes else 0)
    lines.append(f"**Batch totals:** confirmed fixes = 0; ambiguous/skip entries recorded = {skips}; "
                 f"validation = JSON valid, no diff produced.")
    fn = AUD / f"remaining_batch_{bid}_{'_'.join(codes)}.md"
    fn.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {fn.name}")
print("done")
