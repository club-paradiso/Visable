#!/usr/bin/env python3
"""Targeted Type C/D candidate detector.

For each document-label string in a procedure tab, using the CORRECT manual
(visa manual for visaIssuance tab, stay manual for all stay tabs):

  - exact_in_manual: the verbatim string appears in the manual section
  - norm_in_manual:  the normalized (punct/space-stripped) string appears
  - label_like:      short, no sentence/explanatory markers

A Type D naming candidate = label_like AND norm_in_manual AND NOT exact_in_manual
  (the manual contains this document under a slightly different surface form).

Everything else that is NOT exact_in_manual and NOT a clear label is left for
manual review (likely AMBIGUOUS) — we do NOT auto-flag descriptive strings.

Read-only. Writes audits/manual-doc-normalization/naming_candidates.json
"""
import json, re, unicodedata
from pathlib import Path

DATA = json.loads(Path("visa_data.json").read_text(encoding="utf-8"))
STAY = Path("docs/data/claude_opus_manual_extraction_2026_05/stay_hwp_full.txt").read_text(encoding="utf-8").split("\n")
VISA = Path("docs/data/claude_opus_manual_extraction_2026_05/visa_hwp_full.txt").read_text(encoding="utf-8").split("\n")

# Stay-manual section line ranges (1-indexed inclusive), built from header scan.
SMAP = {
 'A-1':(483,600),'A-2':(601,733),'A-3':(734,826),'B-1':(827,851),'B-2':(852,876),
 'C-1':(877,901),'C-3':(902,980),'C-4':(981,1047),'D-1':(1048,1161),'D-2':(1162,2255),
 'D-3':(2256,3052),'D-4':(3053,3680),'D-5':(3681,3770),'D-6':(3771,3865),'D-7':(3866,4084),
 'D-8':(4085,4591),'D-9':(4592,5180),'D-10':(5181,6251),'E-1':(6252,6469),'E-2':(6470,6819),
 'E-3':(6820,7109),'E-4':(7110,7250),'E-5':(7251,7383),'E-6':(7384,7589),'E-7':(7590,11533),
 'E-8':(11534,11615),'E-9':(11616,11967),'E-10':(11968,12115),'F-1':(12116,12640),
 'F-2':(12641,14596),'F-3':(14597,14797),'F-5':(14798,16570),'F-6':(16571,17852),
 'G-1':(17853,18319),'H-1':(18320,18465),
 'F-4':(18466,20712),'H-2':(18466,20712),
 'REGION-S':(20713,23284),'YOUTH-STAY':(23285,23848),'K-STAR':(27216,28594),
 'D-4-1':(3053,3680),'D-4-2K':(3053,3680),
}
EXTRA = {
 'D-10':[(23849,24380)], 'E-7':[(23849,24380)],
 'F-2':[(23849,24380),(27216,28594),(20713,23284)],
 'F-5':[(23849,24380),(27216,28594),(18466,20712),(20713,23284)],
 'F-1':[(18466,20712)], 'F-3':[(18466,20712)], 'C-3':[(18466,20712)],
 'D-2':[(24381,27215)], 'K-STAR':[(27216,28594)],
}
STAY_TABS = {'statusChange','extension','registration','reentry','statusGrant',
             'activitiesOutsideStatus','workplaceChange','partTimeWork','schoolChange'}
SECTIONS = ['commonDocs','requiredDocs','additionalDocs','conditionalDocs']

PUNCT = r"[\s·•∙‧ㆍ,，.．()\[\]「」『』<>〈〉【】\-‐–—_/:;※*①-⑳❶-❿`‘’“”‥…]+"
def norm(s):
    s = unicodedata.normalize("NFKC", s)
    return re.sub(PUNCT, "", s).lower()

def sect_text(code, lines, smap, extra):
    rng = smap.get(code)
    if not rng:
        return None
    s, e = rng
    txt = "\n".join(lines[s-1:e])
    for xs, xe in extra.get(code, []):
        txt += "\n" + "\n".join(lines[xs-1:xe])
    return txt

NVISA = norm("\n".join(VISA))
RAWVISA = "\n".join(VISA)

# A string is "label-like" if short and free of explanatory/sentence markers.
EXPLAIN = ['있습니다','됩니다','경우','또는','제외','대상','바랍니다','하여야','수 있','등의','에 따라',
           '예:','예시','단,','다만','으로','에서','지급','조건','이내','이상','이하','미만','초과',
           '면제될','대체','준비','확인서를','우편물','영수증','권한']
def label_like(s):
    if len(s) > 28:
        return False
    if any(m in s for m in EXPLAIN):
        return False
    return True

out = {}
for v in DATA:
    code = v['code']
    procs = v.get('procedures') or {}
    stay_txt = sect_text(code, STAY, SMAP, EXTRA)
    nstay = norm(stay_txt) if stay_txt else ""
    raw_stay = stay_txt or ""
    for tab, p in procs.items():
        if not isinstance(p, dict):
            continue
        if tab == 'visaIssuance':
            ntext, raw = NVISA, RAWVISA; manual = 'visa'
        elif tab in STAY_TABS:
            ntext, raw = nstay, raw_stay; manual = 'stay'
        else:
            ntext, raw = nstay, raw_stay; manual = 'stay?'
        scopes = []
        rd = p.get('requiredDocs')
        if isinstance(rd, dict):
            scopes.append(("requiredDocs", rd))
        for vi, var in enumerate(p.get('variants') or []):
            vrd = var.get('requiredDocs')
            if isinstance(vrd, dict):
                scopes.append((f"variants[{vi}|{var.get('id','')}]", vrd))
        for scopename, scope in scopes:
            for sect in SECTIONS:
                for i, s in enumerate(scope.get(sect) or []):
                    if not isinstance(s, str):
                        continue
                    exact = s in raw
                    nrm = norm(s) in ntext if ntext else False
                    if exact:
                        continue  # fine
                    if nrm and label_like(s):
                        out.setdefault(code, []).append({
                            "tab": tab, "manual": manual, "scope": scopename,
                            "section": sect, "idx": i, "value": s,
                            "kind": "D_naming_nearmiss"})
# summary
total = sum(len(x) for x in out.values())
Path("audits/manual-doc-normalization/naming_candidates.json").write_text(
    json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"Type C/D naming near-miss candidates (label-like, normalized-in-manual, not exact): {total}")
for code, lst in out.items():
    print(f"  {code}: {len(lst)}")
    for c in lst:
        print(f"      [{c['tab']}/{c['section']}] {c['value']!r}")
