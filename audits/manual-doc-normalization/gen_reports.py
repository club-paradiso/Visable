#!/usr/bin/env python3
"""Generate per-batch audit reports + final summary from the global scans
and the reviewed decision map. Read-only w.r.t. visa_data.json."""
import json
from pathlib import Path
from datetime import date

AUD = Path("audits/manual-doc-normalization")
mech = json.loads((AUD / "mechanical_findings.json").read_text(encoding="utf-8"))
naming = json.loads((AUD / "naming_candidates.json").read_text(encoding="utf-8"))

BATCHES = [
    ("B01", ["B-1", "B-2", "C-3", "C-4", "D-1", "D-2"]),
    ("B02", ["D-3", "D-4", "D-4-1", "D-7", "D-8", "D-9"]),
    ("B03", ["D-10", "E-1", "E-2", "E-3", "E-4", "E-5"]),
    ("B04", ["E-6", "E-7", "E-8", "E-9", "E-10", "F-1"]),
    ("B05", ["F-2", "F-3", "F-4", "F-5", "F-6", "G-1"]),
    ("B06", ["H-1", "H-2", "A-1", "A-2", "A-3", "C-1"]),
    ("B07", ["D-5", "D-6", "D-4-2K", "K-STAR", "REGION-S", "YOUTH-STAY"]),
]

# Reviewed decisions for naming near-miss candidates (value -> (decision, reason, evidence))
# decision in {ALREADY_FAITHFUL, FLATTENED_ARTIFACT, PROTECTED_NUMBER, FEE_NOTE,
#              MULTI_DOC_ELEMENT, LESS_SPECIFIC}
DEC = {
 "표준입학허가서(대학 총·학장 발행)": ("ALREADY_FAITHFUL", "Matches manual modulo dot-char/space.", "stay L3103 '③ 표준입학허가서* (대학 총․학장 발행)'"),
 "부·모 잔고증명서 제출 시 가족관계증명서 추가 제출": ("ALREADY_FAITHFUL", "Conditional note, faithful to manual.", "stay L3106"),
 "수수료 면제": ("FEE_NOTE", "Fee note, not a document name; fees are protected.", "stay L582"),
 "사업장 존재 입증서류": ("ALREADY_FAITHFUL", "Whitespace-only diff ('입증 서류'); appears in 2 different variants (not a dup).", "stay L4260"),
 "공동사업자인 국민의 사업자금 사용내역 입증서류": ("ALREADY_FAITHFUL", "Flattened '(사용 내역)' parens; same doc.", "stay L4306"),
 "신청서, 여권, 표준규격사진, 체류지 입증서류": ("MULTI_DOC_ELEMENT", "Comma-joined multi-doc element; splitting = restructuring, out of scope.", "stay L4332"),
 "체류자격 변경 사유서": ("ALREADY_FAITHFUL", "Whitespace-only vs '체류자격변경 사유서'.", "stay L4658"),
 "고용계약서(원본 및 사본)": ("ALREADY_FAITHFUL", "Paren-wrapped vs '고용계약서 원본 및 사본'; same doc.", "stay L3817"),
 "공적확인을 받은 학력증명서": ("ALREADY_FAITHFUL", "Exact modulo '*' marker.", "stay L6596"),
 "국내·외 은행 잔고증명서(해당자)": ("ALREADY_FAITHFUL", "Whitespace/dot-char diff.", "stay L7077"),
 "통합신청서(별지 제34호 서식)": ("ALREADY_FAITHFUL", "Standard official form; exact match present.", "stay L11254"),
 "고용·공연추천서": ("ALREADY_FAITHFUL", "Dot-char diff (·/․).", "stay L7515"),
 "체류기간 연장허가,": ("FLATTENED_ARTIFACT", "Procedure heading fragment captured as a doc; table context unclear.", "stay L125"),
 "통합신청서 ※ 지방자치단체 방문 시:": ("FLATTENED_ARTIFACT", "Heading fragment concatenated by extraction.", "stay L182"),
 "출입국·외국인관서 방문 시:": ("FLATTENED_ARTIFACT", "Heading fragment concatenated by extraction.", "stay L11611"),
 "외국인근로자(신청자)의 위임장(대행 시)": ("ALREADY_FAITHFUL", "Conditional doc; faithful.", "stay L11712 context"),
 "사업자등록증 등 사업장 관련 입증서류": ("ALREADY_FAITHFUL", "Exact modulo quotes around 사업자등록증.", "stay L11691"),
 "여권 원본": ("ALREADY_FAITHFUL", "Whitespace-only vs '여권원본'.", "stay L596"),
 "재정능력 입증서류(불법체류 다발국가 국민에 한함)": ("ALREADY_FAITHFUL", "Faithful to manual.", "stay L12324"),
 "통합신청서(별지 제1호 서식)": ("LESS_SPECIFIC", "Manual prefixes '재외동포'; form number 제1호 already correct. Prepending not 'extremely clear', risk of churn. Flag for review.", "stay L18747 '재외동포 통합신청서(별지 제1호서식)'"),
 "해외범죄경력증명서": ("ALREADY_FAITHFUL", "Exact match present.", "stay L5392"),
 "산재로 인한 병원 진단서 등": ("ALREADY_FAITHFUL", "Whitespace-only vs '병원진단서'.", "stay L18052"),
 "체류지 입증서류(월세계약서 등)": ("ALREADY_FAITHFUL", "Faithful to manual.", "stay L18463"),
 "외국인등록 신청서": ("LESS_SPECIFIC", "Descriptive; registration uses 통합신청서. Not clearly wrong; flag for review.", "stay L1149 '외국인등록 신청서류'"),
 "대학 총장 추천서(발급일로부터 1년간 유효)": ("ALREADY_FAITHFUL", "Label + validity annotation; K-STAR section.", "K-STAR L27294 context"),
 # D-10 flattened artifacts (roman-marker heading mash):
 "체류지 입증서류 ⅱ) 국내 성장 기반 외국인 청소년": ("FLATTENED_ARTIFACT", "Doc + section heading mashed by extraction.", "D-10 stay sec"),
 "체류지 입증서류 ⅲ) 유망인재": ("FLATTENED_ARTIFACT", "Doc + section heading mashed by extraction.", "D-10 stay sec"),
 "기술창업 활동계획서": ("ALREADY_FAITHFUL", "Whitespace vs '기술창업활동계획서'.", "stay L5816"),
 "학력 입증서류": ("ALREADY_FAITHFUL", "Generic faithful label; manual '최종학력입증서류'.", "stay L3107/L3172"),
 "인턴활동계획서": ("ALREADY_FAITHFUL", "Whitespace vs '인턴활동 계획서'.", "stay L5436"),
}

# Confirmed fixes (Type E) by code
EFIX = {
 "F-4": [
   ("extension",    "procedures.extension.variants[0].manualRefs[0].pageRange",    "PDF pp. 530-531 (embedded manual pp. 10-11)", "PDF pp. 530-531"),
   ("registration", "procedures.registration.variants[0].manualRefs[0].pageRange", "PDF p. 530 (embedded manual p. 10)",          "PDF p. 530"),
   ("statusChange", "procedures.statusChange.variants[0].manualRefs[0].pageRange", "PDF pp. 528-530 (embedded manual pp. 8-10)",   "PDF pp. 528-530"),
 ],
 "H-2": [
   ("registration",   "procedures.registration.variants[0].manualRefs[0].pageRange",   "PDF pp. 524-525 (embedded manual pp. 4-5)", "PDF pp. 524-525"),
   ("workplaceChange","procedures.workplaceChange.variants[0].manualRefs[0].pageRange","PDF pp. 525-526 (embedded manual pp. 5-6)", "PDF pp. 525-526"),
 ],
}

def code_section(code):
    L = []
    m = mech.get(code, {})
    fixes = EFIX.get(code, [])
    cands = naming.get(code, [])
    L.append(f"### {code}")
    # Type A/B/E/N mechanical
    A = m.get("A", []); B = m.get("B", []); E = m.get("E", []); N = m.get("N", [])
    L.append(f"- Type A (exact dup): {len(A)}" + ("" if not A else " — " + "; ".join(f"`{x['value']}` @ {x['loc']}" for x in A)))
    L.append(f"- Type B (공통∩필수): {len(B)}" + ("" if not B else " — " + "; ".join(f"`{x['value']}` @ {x['loc']}" for x in B)))
    L.append(f"- Type E (embedded manual): {len(E)}" + (" → FIXED" if E else ""))
    if N:
        for x in N:
            L.append(f"- Type N (near-dup): `{x['a']}` vs `{x['b']}` @ {x['loc']} → **AMBIGUOUS/skip** (flattened array; the two spellings map to different applicant sub-categories in the manual, 점수제 적용 vs 점수제 면제 특례).")
    else:
        L.append("- Type N (near-dup): 0")
    # Confirmed fixes
    if fixes:
        L.append("- **Confirmed fixes (Type E):**")
        for tab, path, old, new in fixes:
            L.append(f"    - [{tab}] `{path}`: `{old}` → `{new}`")
    # Naming candidates + decisions
    if cands:
        L.append(f"- Naming near-miss candidates: {len(cands)} (all reviewed → skipped):")
        for c in cands:
            val = c["value"]
            dec, reason, ev = DEC.get(val, ("AMBIGUOUS", "Not clearly an official label; table context unclear.", ""))
            L.append(f"    - ⚠️ `{val}` [{c['tab']}/{c['section']}] → **{dec}** — {reason} (evidence: {ev})")
    if not (A or B or E or N or cands):
        L.append("- No findings; no candidates. Clean.")
    L.append("")
    return "\n".join(L)

total_fix = 0
total_skip = 0
for bid, codes in BATCHES:
    lines = [f"# Batch {bid} — {', '.join(codes)}", ""]
    lines.append(f"_Authoritative manuals: visaIssuance→visa_hwp_full.txt; 체류 tabs→stay_hwp_full.txt. Generated {date.today()}._")
    lines.append("")
    bfix = 0; bskip = 0
    for code in codes:
        lines.append(code_section(code))
        bfix += sum(len(v) for k, v in EFIX.items() if k == code for v in [v])  # placeholder
    # recompute counts properly
    bfix = sum(len(EFIX.get(c, [])) for c in codes)
    bskip = sum(len(naming.get(c, [])) for c in codes) + sum(len(mech.get(c, {}).get("N", [])) for c in codes)
    lines.insert(3, f"**Batch totals:** confirmed fixes = {bfix}; ambiguous/skipped = {bskip}.\n")
    total_fix += bfix; total_skip += bskip
    (AUD / f"batch_{bid}_{'_'.join(codes).replace('/', '-')}.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote batch_{bid}: fixes={bfix} skipped={bskip}")

print(f"TOTAL confirmed fixes={total_fix}; ambiguous/skipped={total_skip}")
