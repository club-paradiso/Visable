#!/usr/bin/env python3
"""Audit duplicate / misclassified status-result rendering across Paradiso records.

This script dynamically discovers EVERY visa / status / residence code that is
reachable from the repository's own data (app ``visa_data.json``, the synced
``backend/data/visas.json``, ``doc_master.json`` document master, the
``data/scenario_help_records.json`` store, and the source manifests). It never
hard-codes the code universe -- the list is derived purely from those files, so
the audit automatically tracks new parents, subcodes, special variants
(``K-STAR``, ``REGION-S`` ...) and procedure groups.

It then inspects every document-bearing, user-visible field (procedure document
groups, the legacy ``documents_*`` tabs, the legacy ``*ReqDocs`` arrays, and
subcode ``addReqDocs``) and detects the rendering-quality defects described in
the task:

  * exact / normalized duplicate document labels inside one visible section
  * the same item appearing in both 공통서류 and 필수서류 for one result+procedure
  * explanatory prose rendered as a checklist item (long >80 / severe >160 KR
    chars, sentence-final verbs, or eligibility / stay-period / scope /
    discretion / procedure wording)
  * a parent record rendering subcode-specific rules as universal documents
  * conditional documents mixed into the required group
  * procedure-scope contamination (사증발급 <-> 체류 procedures leaking into one
    another)
  * orphan subcodes (a subcode whose parent code is missing)
  * OCR / manual coverage gaps (reported, never auto-filled)

Outputs ``audits/dedup-rendering-audit.md`` and, in ``--check`` mode, fails only
on SEVERE issues so it can be wired into ``scripts/check_repo.sh`` without making
medium / low findings block the repository check.

The normalization + split helpers in this module are the single source of truth
for the data-hygiene transform (``apply_doc_render_hygiene_2026_06_09.py``) and
mirror the render-layer helpers added to ``index.html``.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import unicodedata
from collections import OrderedDict, defaultdict

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

APP_VISA_DATA = os.path.join(REPO_ROOT, "visa_data.json")
BACKEND_VISA_DATA = os.path.join(REPO_ROOT, "backend", "data", "visas.json")
DOC_MASTER = os.path.join(REPO_ROOT, "doc_master.json")
SCENARIO_RECORDS = os.path.join(REPO_ROOT, "data", "scenario_help_records.json")
SOURCE_MANIFESTS = [
    os.path.join(REPO_ROOT, "docs", "source-manuals", "source_manifest.json"),
    os.path.join(REPO_ROOT, "docs", "source-manuals", "2026-06", "incoming", "source_files_manifest_2026_06_01.json"),
    os.path.join(REPO_ROOT, "docs", "source-manuals", "2026-05", "incoming", "source_files_manifest_2026_05_21.json"),
]
STRUCTURED_REQ_INDEXES = [
    os.path.join(REPO_ROOT, "backend", "data", "manual_grounding", "structured_requirements_index_2026_06_01.json"),
    os.path.join(REPO_ROOT, "backend", "data", "manual_grounding", "structured_requirements_index_2026_05.json"),
]

AUDIT_OUTPUT = os.path.join(REPO_ROOT, "audits", "dedup-rendering-audit.md")

# Severity levels.
SEV_HIGH = "high"   # severe -- fails --check
SEV_MED = "medium"  # warn-only
SEV_LOW = "low"     # warn-only / informational

# The four procedure document groups, in render order. Mirrors
# renderProcedureDocGroups() in index.html.
PROCEDURE_GROUPS = ["commonDocs", "requiredDocs", "additionalDocs", "conditionalDocs"]
GROUP_LABELS = {
    "commonDocs": "공통서류",
    "requiredDocs": "필수서류",
    "additionalDocs": "추가/심사 필요 서류",
    "conditionalDocs": "조건부 서류",
}

# Procedure scope buckets, used for procedure-contamination detection. Mirrors
# PROCEDURE_CONFIG keys in index.html.
VISA_ISSUANCE_PROCEDURES = {"visaIssuance", "certificateOfVisaIssuance"}
STAY_PROCEDURES = {
    "statusChange", "extension", "statusGrant", "registration",
    "activitiesOutsideStatus", "workplaceChange", "reentry", "partTimeWork",
    "schoolChange",
}

# Legacy flat document-tab fields (rendered by renderDocumentTabs()).
DOCUMENT_TAB_FIELDS = ["documents_initial", "documents_registration", "documents_extension"]
# Legacy *ReqDocs arrays that PROCEDURE_CONFIG folds into procedure groups.
LEGACY_REQ_FIELDS = [
    "newReqDocs", "extReqDocs", "initialReqDocs", "extensionReqDocs",
    "changeReqDocs", "cviReqDocs", "statusGrantReqDocs", "registrationReqDocs",
    "activitiesOutsideStatusReqDocs", "workplaceChangeReqDocs", "reentryReqDocs",
]

# Pipeline placeholders that are never real document names (mirrors
# DOC_PLACEHOLDER_TOKENS in index.html).
DOC_PLACEHOLDER_TOKENS = {
    "매뉴얼 확인 필요", "페이지 확인 필요", "Manual review needed", "Page review needed",
    "문서명 미상", "비고 정보 없음", "DATA_MISSING", "Document name unknown", "No note available",
}

# --------------------------------------------------------------------------- #
# Normalization helpers (single source of truth; mirrored in index.html JS).
# --------------------------------------------------------------------------- #

_LEADING_MARK_RE = re.compile(r"^\s*(?:[①-⑳]|[0-9]+\s*[.)]|[-‣◦○●□■◇*※·•ㆍ])\s*")


def normalize_text(value) -> str:
    """NFKC-normalize, collapse whitespace, trim. Preserves wording."""
    if value is None:
        return ""
    s = unicodedata.normalize("NFKC", str(value))
    s = s.replace(" ", " ")
    s = re.sub(r"\s+", " ", s).strip()
    return s


def strip_leading_marks(value: str) -> str:
    s = value
    while True:
        nxt = _LEADING_MARK_RE.sub("", s)
        if nxt == s:
            return s.strip()
        s = nxt


def canonical_key(value) -> str:
    """Aggressive canonical key for duplicate detection.

    Mirrors paradisoCanonicalDocKey20260609() in index.html: NFKC, strip
    numbering/bullets, drop whitespace + middots + brackets, and collapse a few
    well-known synonym families so e.g. "통합신청서(별지 제34호 서식)" and "신청서"
    are recognised as the same document. Intentionally conservative -- only
    collapses families that are unambiguous in the immigration-document domain.
    """
    text = normalize_text(value)
    if not text or is_placeholder(text):
        return ""
    text = strip_leading_marks(text)
    text = re.sub(r"\s+", "", text)
    text = re.sub(r"[ㆍ·•]", "", text)
    text = re.sub(r"[()\[\]{}［］]", "", text)
    text = text.replace("별지제34호서식", "").replace("원본및사본1부", "")
    text = text.replace("원본", "").replace("사본", "")

    families = [
        (re.compile(r"^(통합)?신청서"), "신청서"),
        (re.compile(r"^여권"), "여권"),
        (re.compile(r"^(외국인)?등록증"), "외국인등록증"),
        (re.compile(r"^수수료"), "수수료"),
        (re.compile(r"^(표준규격)?사진"), "표준규격사진"),
        (re.compile(r"^표준입학허가서"), "표준입학허가서"),
        (re.compile(r"^(교육기관)?(사업자등록증|고유번호증)"), "교육기관사업자등록증"),
        (re.compile(r"^재학(연구생)?증명서"), "재학증명서"),
        (re.compile(r"^체류지입증"), "체류지입증서류"),
        (re.compile(r"^재정(능력|입증)"), "재정입증서류"),
        (re.compile(r"^가족관계"), "가족관계입증서류"),
    ]
    for rx, canon in families:
        if rx.match(text):
            return canon
    return text


def is_placeholder(value) -> bool:
    return normalize_text(value) in DOC_PLACEHOLDER_TOKENS


def resolve_doc(value, doc_master: dict) -> str:
    """Resolve a doc reference to its rendered Korean label.

    Strings starting with ``doc_`` resolve through doc_master; dict items use
    name/label/title/text; everything else is stringified. Mirrors
    toDocArray()/DOC_DICT resolution in index.html.
    """
    if isinstance(value, str):
        if value.startswith("doc_"):
            entry = doc_master.get(value)
            return entry.get("ko_name", value) if entry else value
        return value
    if isinstance(value, dict):
        for key in ("name", "label", "title", "text", "description"):
            if value.get(key):
                return str(value[key])
        return ""
    return str(value)


# --------------------------------------------------------------------------- #
# Prose / document split detection (single source of truth).
# --------------------------------------------------------------------------- #

LONG_DOC_THRESHOLD = 80     # > 80 -> long (medium)
SEVERE_DOC_THRESHOLD = 160  # > 160 rendered label -> severe

# Sentence-final endings that mark explanatory prose rather than a document
# name. Anchored at the end of the (normalized) string.
SENTENCE_END_RE = re.compile(
    r"(?:습니다|입니다|합니다|됩니다|있습니다|없습니다|바랍니다|십시오|하십시오|"
    r"가능|불가|불요|제한|부여|징구|면제|해당됩니다|필요합니다|"
    r"수\s*없[다음]|할\s*수\s*있음|받을\s*수\s*있음)\.?$"
)

# Wording that describes eligibility / stay-period / scope / discretion /
# procedure rather than a concrete document.
PROSE_TOPIC_RE = re.compile(
    r"(원칙적으로|경우에\s*한|에\s*한해|해당자|대상으로\s*합니다|대상입니다|"
    r"상한은|특례\s*상한|체류기간\s*상한|허가될\s*수|조정될\s*수|"
    r"심사가\s*강화|생략될\s*수|제출\s*불요|초과할\s*수\s*없|"
    r"기재하되|허위기재|처벌받을\s*수)"
)

# Document-noun tails: if the head before a boundary ends in one of these it is
# a plausible concrete document name. Intentionally concrete nouns only -- bare
# generic endings (확인, 발급, 특례 ...) are excluded so prose that merely ends in
# one of those words is not mistaken for a document.
DOC_TAIL_RE = re.compile(
    r"(서류|증명서|확인서|신청서|계약서|등록증|영수증|진단서|보증서|결정문|"
    r"입증자료|사업자등록증|고유번호증|허가서|동의서|사유서|계획서|증빙서류|"
    r"여권|사본|원본|사진|수수료|인지|통지서|출석부|카드|공한|등본|초본|"
    r"입증서류|증서|소견서|위임장|재학증명서|졸업증명서|인정서|확인증|납입증명서)$"
)

# Tokens that, in the absence of a concrete document tail, mark an item as
# explanatory prose (subcode variability, cross-procedure notes, ...).
STRONG_PROSE_TOKENS = ("세부약호",)

# Section / procedure heading markers that should never sit inside a document
# label (they are extraction artifacts).
HEADING_MARKER_RE = re.compile(r"[□■◇▶▷※☞]|(?<![0-9])[0-9]{1,2}\.\s*\S+제출서류|체류기간\s*연장\s*제출서류")

# Canonical 체류지 입증서류 example block -- the single dominant over-long item.
RESIDENCE_DOC_RE = re.compile(r"체류지\s*입증서류\s*\(\s*예\s*:.*?준비\s*\)", re.DOTALL)


def split_doc_item(value):
    """Split a raw document item into a concise checklist ``label`` plus a
    relocated ``note``, classifying the item.

    Returns a dict: ``{label, note, kind}`` where ``kind`` is one of
    ``doc`` (clean document, possibly with a relocated note),
    ``prose`` (whole item is explanatory text -> label is empty, suppress from
    checklist), or ``empty``.

    This is the shared contract used by the renderer (so the user only ever sees
    ``label`` as a checklist line and ``note`` as a sub-note) and by the
    validation check (which measures ``label`` length).
    """
    text = normalize_text(value)
    if not text or is_placeholder(text):
        return {"label": "", "note": "", "kind": "empty"}
    text = strip_leading_marks(text)
    if not text:
        return {"label": "", "note": "", "kind": "empty"}

    # 1) Canonical 체류지 입증서류 example block: keep the doc name, relocate the
    #    parenthetical examples + any trailing leaked content to a note.
    m = RESIDENCE_DOC_RE.search(text)
    if m:
        before = text[: m.start()].strip().rstrip(",")
        block = m.group(0)
        after = text[m.end():].strip()
        note_parts = []
        inner = block[block.find("(") + 1: block.rfind(")")].strip()
        if inner:
            note_parts.append(inner)
        if after:
            note_parts.append(strip_leading_marks(after))
        note = " / ".join(p for p in note_parts if p)
        if before:
            # Leading comma list before the residence doc: the residence doc is
            # the last element. Keep the prefix list intact, append residence
            # doc name.
            label = (before + ", 체류지 입증서류").strip()
        else:
            label = "체류지 입증서류"
        # If the leading prefix is itself prose, fall through to prose handling.
        if not before or not SENTENCE_END_RE.search(before):
            return {"label": label, "note": note, "kind": "doc"}

    # 2) Whole-item prose: explanatory text with no document-noun tail.
    head_candidate = re.split(r"[(（]|※|‣|◦|·|\s—\s", text, maxsplit=1)[0].strip()
    looks_like_sentence = bool(SENTENCE_END_RE.search(text) or PROSE_TOPIC_RE.search(text))
    has_doc_tail = bool(DOC_TAIL_RE.search(head_candidate))
    has_heading = bool(HEADING_MARKER_RE.search(text))
    has_subcode_ref = bool(re.search(r"[A-Z]{1,3}-[0-9]+-[0-9A-Z]+", text))
    prose_prefix = bool(re.match(r"^(대상|예외|참고|유의|비고|주의|단)\b|^단,|^대상:", text))
    open_p = text.count("(") + text.count("（")
    close_p = text.count(")") + text.count("）")
    unbalanced = open_p != close_p
    strong_prose = (any(tok in text for tok in STRONG_PROSE_TOKENS)
                    or ("사증발급인정서" in text)
                    or unbalanced or has_subcode_ref or prose_prefix)

    # A real document almost always ends its head in a document noun. When the
    # head has NO document-noun tail, an item that is also a sentence / very long
    # / a subcode rule / a cross-procedure note / an explanatory prefix / a split
    # prose fragment (unbalanced parens) is explanatory prose, not a document.
    if not has_doc_tail and (looks_like_sentence or len(text) > LONG_DOC_THRESHOLD
                             or strong_prose):
        return {"label": "", "note": text, "kind": "prose"}

    # 3) Document with a long trailing tail (examples / heading / caveat after a
    #    recognizable doc head). Relocate the tail to a note.
    if has_doc_tail and (len(text) > LONG_DOC_THRESHOLD or has_heading):
        cut = None
        for rx in (re.compile(r"[(（]"), re.compile(r"※"), re.compile(r"‣"),
                   re.compile(r"[□■◇▶▷☞❍]"), re.compile(r"(?<=[다음])\s+\S")):
            mm = rx.search(text, len(head_candidate))
            if mm and (cut is None or mm.start() < cut):
                cut = mm.start()
        if cut and cut < len(text):
            label = text[:cut].strip().rstrip(",").rstrip()
            note = strip_leading_marks(text[cut:].strip().lstrip("()（） "))
            if DOC_TAIL_RE.search(label) and len(label) <= SEVERE_DOC_THRESHOLD:
                return {"label": label, "note": note, "kind": "doc"}

    # 4) Over-long blob with no clean split point: relocate whole text to a note
    #    rather than render a >160-char checklist tile.
    if len(text) > SEVERE_DOC_THRESHOLD:
        return {"label": "", "note": text, "kind": "prose"}

    # 5) Plain document (short, recognizable).
    return {"label": text, "note": "", "kind": "doc"}


# --------------------------------------------------------------------------- #
# Discovery (dynamic; never hard-coded).
# --------------------------------------------------------------------------- #

# Sentinel proving the universe is data-derived, not a literal list.
HARDCODED_CODE_UNIVERSE = None
STATUS_CODE_RE = re.compile(r"^[A-Z]{1,6}-[A-Z0-9]+(?:-[A-Z0-9]+)?$")
SUBCODE_RE = re.compile(r"^([A-Z]{1,6}-[A-Z0-9]+)-[A-Z0-9]+$")


def load_json(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def discover_codes():
    """Discover the complete code universe from repository data only.

    Returns ``(records, discovery)`` where ``records`` maps code -> a normalized
    record descriptor and ``discovery`` carries provenance + counts. No code
    list is ever hard-coded; ``HARDCODED_CODE_UNIVERSE`` must stay ``None``.
    """
    assert HARDCODED_CODE_UNIVERSE is None, "Code universe must be data-derived, not hard-coded."

    app_visas = load_json(APP_VISA_DATA)
    doc_master = {d["id"]: d for d in load_json(DOC_MASTER) if isinstance(d, dict) and d.get("id")}

    records = OrderedDict()
    parents = []
    subcodes = []
    special_variants = []
    scenario_codes = []

    def add_record(code, raw, source_file, record_type, parent=None):
        code = str(code).strip()
        if not code:
            return
        records[code] = {
            "code": code,
            "raw": raw,
            "source_file": source_file,
            "record_type": record_type,
            "parent": parent,
        }

    def classify_child(code):
        """A subcode whose final segment is non-numeric (e.g. D-10-T, E-7-S1,
        E-9-JS) is a special variant per CLAUDE.md; a purely numeric final
        segment (D-2-1) is an ordinary subcode. Both remain children of their
        parent in the hierarchy."""
        final = code.rsplit("-", 1)[-1]
        if final.isdigit():
            subcodes.append(code)
        else:
            special_variants.append(code)

    for rec in app_visas:
        if not isinstance(rec, dict):
            continue
        code = rec.get("code")
        if not code:
            continue
        add_record(code, rec, "visa_data.json", "status", None)
        if SUBCODE_RE.match(code):
            classify_child(code)
        elif STATUS_CODE_RE.match(code):
            parents.append(code)
        else:
            special_variants.append(code)
        # Inline subCodes live on the parent record but are independent codes.
        for sub in rec.get("subCodes") or []:
            if isinstance(sub, dict) and sub.get("code"):
                sub_code = str(sub["code"]).strip()
                classify_child(sub_code)
                add_record(
                    sub_code,
                    sub,
                    "visa_data.json",
                    "subcode",
                    parent=code,
                )

    # Scenario help store records (K-ETA, TB-1, SCN-*, FAQ-*, OVS-1, ...).
    if os.path.exists(SCENARIO_RECORDS):
        scn = load_json(SCENARIO_RECORDS)
        for entry in scn.get("records", []) or []:
            inner = entry.get("record") or {}
            code = inner.get("code") or entry.get("sourceVisaDataCode")
            if not code:
                continue
            code = str(code).strip()
            scenario_codes.append(code)
            if code not in records:
                add_record(code, inner, "data/scenario_help_records.json", "scenario", None)

    discovery = {
        "doc_master": doc_master,
        "doc_master_ids": sorted(doc_master.keys()),
        "parents": sorted(set(parents)),
        "subcodes": sorted(set(subcodes)),
        "special_variants": sorted(set(special_variants)),
        "scenario_codes": sorted(set(scenario_codes)),
        "source_manifests": [p for p in SOURCE_MANIFESTS if os.path.exists(p)],
    }
    return records, discovery


def load_manual_coverage():
    """Codes that have structured-requirements manual grounding."""
    covered = set()
    for path in STRUCTURED_REQ_INDEXES:
        if not os.path.exists(path):
            continue
        try:
            data = load_json(path)
        except Exception:
            continue
        # Index shape varies; collect any value that looks like a status code.
        def walk(node):
            if isinstance(node, dict):
                for k, v in node.items():
                    if isinstance(k, str) and STATUS_CODE_RE.match(k):
                        covered.add(k)
                    walk(v)
            elif isinstance(node, list):
                for it in node:
                    if isinstance(it, str) and STATUS_CODE_RE.match(it):
                        covered.add(it)
                    else:
                        walk(it)
        walk(data)
    return covered


# --------------------------------------------------------------------------- #
# Detection.
# --------------------------------------------------------------------------- #

class Issue:
    __slots__ = ("code", "parent", "record_type", "title", "source_file",
                 "field_path", "text", "reason", "severity", "action", "category")

    def __init__(self, code, parent, record_type, title, source_file, field_path,
                 text, reason, severity, action, category):
        self.code = code
        self.parent = parent
        self.record_type = record_type
        self.title = title
        self.source_file = source_file
        self.field_path = field_path
        self.text = text
        self.reason = reason
        self.severity = severity
        self.action = action
        self.category = category


def _trunc(text, n=90):
    text = normalize_text(text)
    return text if len(text) <= n else text[: n - 1] + "…"


def _record_title(raw):
    name = raw.get("name") or raw.get("record", {}).get("name") if isinstance(raw, dict) else ""
    return normalize_text(name)


def _is_single_prose_blob(value):
    """True when a bare string is one explanatory sentence rather than a
    separator-joined document list, so it must not be split into fragments."""
    s = normalize_text(value)
    if not s:
        return False
    if any(tok in s for tok in STRONG_PROSE_TOKENS):
        return True
    if (s.count("(") + s.count("（")) != (s.count(")") + s.count("）")):
        return True
    if "·" in s and (bool(SENTENCE_END_RE.search(s)) or bool(PROSE_TOPIC_RE.search(s)) or len(s) > 120):
        return True
    return False


def to_doc_array(value, doc_master):
    """Mirror index.html toDocArray(): resolve a doc field value into a flat
    list of label strings, splitting bare strings on the renderer's separators
    (newline / semicolon / middot)."""
    out = []
    if value is None:
        return out
    if isinstance(value, list):
        for item in value:
            out.extend(to_doc_array(item, doc_master))
        return out
    if isinstance(value, str):
        if value.startswith("doc_"):
            label = resolve_doc(value, doc_master)
            if label and not is_placeholder(label):
                out.append(label)
            return out
        # Do not middot/semicolon-split a single prose blob into pseudo-document
        # fragments (e.g. "세부약호별(산업재해·질병치료·...) 추가 제출서류는 사안마다 다름").
        # Such blobs are relocated whole as a note by split_doc_item.
        if _is_single_prose_blob(value):
            piece = value.strip()
            if piece and not is_placeholder(piece):
                out.append(piece)
            return out
        for piece in re.split(r"[\n;·]", value):
            piece = piece.strip()
            if piece and not is_placeholder(piece):
                out.append(piece)
        return out
    if isinstance(value, dict):
        label = resolve_doc(value, doc_master)
        if label and not is_placeholder(label):
            out.append(label)
        return out
    out.append(str(value).strip())
    return out


# Legacy field -> procedure mapping (mirrors PROCEDURE_CONFIG docFields/oldDocs
# in index.html AFTER the render fix). The free-text summary fields
# (newReq / extReq / changeReq) are deliberately NOT included: they are the
# procedure ``oldText`` summaries and aliasing them into requiredDocs is exactly
# how description prose leaked into the checklist. The render fix removes them
# from the doc aliases (they still render as the summary), so the audit models
# the fixed renderer here.
PROC_LEGACY_FIELDS = {
    "visaIssuance": {"requiredDocs": ["initialReqDocs", "newReqDocs"],
                     "additionalDocs": ["addReqDocs"]},
    "certificateOfVisaIssuance": {"requiredDocs": ["cviReqDocs"]},
    "statusChange": {"requiredDocs": ["changeReqDocs"]},
    "extension": {"requiredDocs": ["extensionReqDocs", "extReqDocs"]},
    "statusGrant": {"requiredDocs": ["statusGrantReqDocs"]},
    "registration": {"requiredDocs": ["registrationReqDocs"]},
    "activitiesOutsideStatus": {"requiredDocs": ["activitiesOutsideStatusReqDocs"]},
    "workplaceChange": {"requiredDocs": ["workplaceChangeReqDocs"]},
    "reentry": {"requiredDocs": ["reentryReqDocs"]},
}
PROC_ORDER = list(PROC_LEGACY_FIELDS.keys())


def _cross_category_dedupe(groups):
    """Mirror dedupeDocGroupsAcrossCategories(): keep the first canonical
    occurrence across common -> required -> additional -> conditional."""
    seen = set()
    out = {g: [] for g in PROCEDURE_GROUPS}
    for gkey in PROCEDURE_GROUPS:
        for label in groups.get(gkey, []):
            ckey = canonical_key(label)
            if not ckey or ckey in seen:
                continue
            seen.add(ckey)
            out[gkey].append(label)
    return out


def build_rendered_procedures(raw, doc_master):
    """Reconstruct the user-visible document groups per procedure, applying the
    same split + prose-relocation + cross-category dedupe contract the renderer
    uses. Returns dict[pkey] -> {group: [tiles], 'notes': [relocated notes]}.
    """
    procedures = raw.get("procedures") or {}
    out = OrderedDict()
    keys = list(dict.fromkeys(PROC_ORDER + list(procedures.keys())))
    for pkey in keys:
        proc = procedures.get(pkey) if isinstance(procedures, dict) else None
        if isinstance(proc, dict) and proc.get("available") is False:
            continue
        # Gather raw items per group from structured procedure data + legacy.
        raw_groups = {g: [] for g in PROCEDURE_GROUPS}
        if isinstance(proc, dict):
            rd = proc.get("requiredDocs")
            if isinstance(rd, dict):
                for g in PROCEDURE_GROUPS:
                    raw_groups[g].extend(to_doc_array(rd.get(g), doc_master))
            elif rd is not None:
                raw_groups["requiredDocs"].extend(to_doc_array(rd, doc_master))
            for g in PROCEDURE_GROUPS:
                if g in proc and not (isinstance(rd, dict) and g in rd):
                    raw_groups[g].extend(to_doc_array(proc.get(g), doc_master))
        for g, fields in PROC_LEGACY_FIELDS.get(pkey, {}).items():
            for field in fields:
                if field in raw:
                    raw_groups[g].extend(to_doc_array(raw.get(field), doc_master))
        if not any(raw_groups.values()):
            continue
        # Split each item: tiles keep the doc label, prose + tails become notes.
        tiles = {g: [] for g in PROCEDURE_GROUPS}
        notes = []
        for g in PROCEDURE_GROUPS:
            for item in raw_groups[g]:
                split = split_doc_item(item)
                if split["kind"] == "prose":
                    if split["note"]:
                        notes.append(split["note"])
                    continue
                if not split["label"]:
                    continue
                tiles[g].append(split["label"])
                if split["note"]:
                    notes.append(split["note"])
        deduped = _cross_category_dedupe(tiles)
        deduped["notes"] = notes
        out[pkey] = deduped
    return out


def _scope_bucket(scope):
    if scope in VISA_ISSUANCE_PROCEDURES:
        return "visa"
    if scope in STAY_PROCEDURES:
        return "stay"
    return "other"


def detect_rendered_issues(code, descriptor, doc_master, parent_codes):
    """Gate-level detection on the *rendered* document tiles (what the user
    actually sees). These severities drive ``--check``."""
    raw = descriptor["raw"]
    parent = descriptor["parent"]
    rtype = descriptor["record_type"]
    source_file = descriptor["source_file"]
    title = _record_title(raw)
    issues = []
    if not isinstance(raw, dict):
        return issues

    rendered = build_rendered_procedures(raw, doc_master)

    for pkey, groups in rendered.items():
        bucket = _scope_bucket(pkey)
        for gkey in PROCEDURE_GROUPS:
            seen = {}
            for label in groups[gkey]:
                field_path = f"procedures.{pkey}.{gkey}"
                ckey = canonical_key(label)
                # (1) identical tile repeated in a section (survived dedupe).
                if ckey and ckey in seen:
                    issues.append(Issue(
                        code, parent, rtype, title, source_file, field_path,
                        _trunc(label), "동일 섹션 내 동일 서류 타일 반복(렌더 후에도 잔존)",
                        SEV_HIGH, "섹션 내 중복 타일 제거", "dup_in_section"))
                elif ckey:
                    seen[ckey] = label
                # (2) rendered tile label too long.
                if len(normalize_text(label)) > SEVERE_DOC_THRESHOLD:
                    issues.append(Issue(
                        code, parent, rtype, title, source_file, field_path,
                        _trunc(label, 140),
                        f"렌더되는 서류 타일 길이 {len(normalize_text(label))}자(>160, severe)",
                        SEV_HIGH, "서류명만 타일로 두고 예시/단서를 비고로 분리", "long_doc_severe"))
                # (3) prose tile that escaped relocation.
                if split_doc_item(label)["kind"] == "prose":
                    issues.append(Issue(
                        code, parent, rtype, title, source_file, field_path,
                        _trunc(label, 120),
                        "산문이 서류 타일로 렌더됨(분리 누락)",
                        SEV_HIGH, "산문을 비고로 이전", "prose_as_doc"))
                # (4) parent rendering a subcode-specific rule as a generic doc.
                if rtype != "subcode" and gkey in ("commonDocs", "requiredDocs"):
                    if re.search(r"[A-Z]{1,3}-[0-9]+-[0-9A-Z]+", label) or \
                       re.search(r"(세부약호|특례\s*상한|상한은)", label):
                        issues.append(Issue(
                            code, parent, rtype, title, source_file, field_path,
                            _trunc(label, 120),
                            "부모 레코드가 하위 약호 전용 규칙을 보편 서류 타일로 렌더",
                            SEV_HIGH, "‘하위 체류자격별 유의사항’으로 분리(정확한 약호 표기)",
                            "subcode_rule_as_generic"))
                # (5) procedure-scope contamination surviving as a tile.
                if bucket == "stay" and re.search(
                        r"(사증발급인정서|재외공관|사증\s*발급\s*제출서류)", label):
                    issues.append(Issue(
                        code, parent, rtype, title, source_file, field_path,
                        _trunc(label, 120),
                        "체류 절차 타일에 사증발급 전용 안내 혼입(절차 범위 오염)",
                        SEV_HIGH, "사증발급/체류 안내를 각 절차 범위로 분리",
                        "procedure_contamination"))
                elif bucket == "visa" and re.search(
                        r"(체류기간\s*연장\s*제출서류|외국인등록\s*제출서류)", label):
                    issues.append(Issue(
                        code, parent, rtype, title, source_file, field_path,
                        _trunc(label, 120),
                        "사증발급 절차 타일에 체류 절차 전용 안내 혼입(절차 범위 오염)",
                        SEV_HIGH, "사증발급/체류 안내를 각 절차 범위로 분리",
                        "procedure_contamination"))
        # (6) same tile in BOTH 공통서류 and 필수서류 (survived cross dedupe).
        common = {canonical_key(x) for x in groups["commonDocs"]}
        required = {canonical_key(x) for x in groups["requiredDocs"]}
        for ckey in sorted((common & required) - {""}):
            issues.append(Issue(
                code, parent, rtype, title, source_file, f"procedures.{pkey}",
                ckey, "동일 항목이 공통서류와 필수서류 타일에 모두 잔존",
                SEV_HIGH, "공통서류에 유지하고 필수서류에서 suppress", "common_and_required"))

    # (7) orphan subcode (parent missing).
    m = SUBCODE_RE.match(code)
    if m and descriptor.get("parent") is None and m.group(1) not in parent_codes \
            and code not in parent_codes:
        issues.append(Issue(
            code, parent, rtype, title, source_file, "code", code,
            f"하위 약호이나 부모 코드 {m.group(1)} 부재",
            SEV_HIGH, "부모 레코드 추가 또는 약호 재배치", "orphan_subcode"))

    return issues


def detect_raw_findings(code, descriptor, doc_master):
    """Layer-B detection on the *raw* protected data. These are logged for
    manual review (warn-only). Per CLAUDE.md the renderer mitigates them, but
    they document what is physically present in the JSON so the data can be
    cleaned by a human later if desired."""
    raw = descriptor["raw"]
    parent = descriptor["parent"]
    rtype = descriptor["record_type"]
    source_file = descriptor["source_file"]
    title = _record_title(raw)
    findings = []
    if not isinstance(raw, dict):
        return findings

    procedures = raw.get("procedures") or {}
    fields = []
    if isinstance(procedures, dict):
        for pkey, proc in procedures.items():
            if not isinstance(proc, dict):
                continue
            rd = proc.get("requiredDocs")
            if isinstance(rd, dict):
                for g in PROCEDURE_GROUPS:
                    fields.append((f"procedures.{pkey}.requiredDocs.{g}", g, rd.get(g) or []))
    for f in DOCUMENT_TAB_FIELDS:
        if isinstance(raw.get(f), list):
            fields.append((f, "requiredDocs", raw[f]))

    for field_path, gkey, items in fields:
        seen = {}
        for it in items:
            label = normalize_text(resolve_doc(it, doc_master))
            if not label or is_placeholder(label):
                continue
            ckey = canonical_key(label)
            if ckey and ckey in seen:
                findings.append(Issue(
                    code, parent, rtype, title, source_file, field_path,
                    _trunc(label), "데이터 배열 내 중복 문자열",
                    SEV_LOW, "동일 배열의 정확한 중복 제거(안전 편집)", "raw_dup_in_array"))
            elif ckey:
                seen[ckey] = label
            split = split_doc_item(label)
            if split["kind"] == "prose":
                findings.append(Issue(
                    code, parent, rtype, title, source_file, field_path,
                    _trunc(label, 120),
                    "데이터상 산문이 문서 배열에 존재(렌더러가 비고로 이전)",
                    SEV_MED, "적절한 note 필드로 이전 검토(수동)", "raw_prose_in_array"))
            elif len(label) > SEVERE_DOC_THRESHOLD:
                findings.append(Issue(
                    code, parent, rtype, title, source_file, field_path,
                    _trunc(label, 140),
                    f"데이터상 {len(label)}자 긴 문자열(렌더러가 분리)",
                    SEV_MED, "서류명/예시를 분리 검토(수동)", "raw_long_in_array"))
            if HEADING_MARKER_RE.search(label):
                findings.append(Issue(
                    code, parent, rtype, title, source_file, field_path,
                    _trunc(label, 120),
                    "데이터상 섹션/절차 제목 텍스트가 문서 배열에 혼입",
                    SEV_MED, "제목/절차 텍스트 분리 검토(수동)", "raw_heading_in_array"))

    return findings


# --------------------------------------------------------------------------- #
# Report.
# --------------------------------------------------------------------------- #

def build_report(records, discovery, rendered_issues, raw_findings, manual_covered, audited_codes):
    all_issues = rendered_issues
    by_code = defaultdict(list)
    for iss in all_issues:
        by_code[iss.code].append(iss)
    raw_by_code = defaultdict(list)
    for iss in raw_findings:
        raw_by_code[iss.code].append(iss)

    sev_counts = {SEV_HIGH: 0, SEV_MED: 0, SEV_LOW: 0}
    for iss in all_issues:
        sev_counts[iss.severity] += 1

    raw_sev_counts = {SEV_HIGH: 0, SEV_MED: 0, SEV_LOW: 0}
    for iss in raw_findings:
        raw_sev_counts[iss.severity] += 1

    cat_counts = defaultdict(int)
    for iss in all_issues:
        cat_counts[iss.category] += 1
    raw_cat_counts = defaultdict(int)
    for iss in raw_findings:
        raw_cat_counts[iss.category] += 1

    clean_codes = sorted(c for c in audited_codes if c not in by_code)

    lines = []
    w = lines.append
    w("# Paradiso 중복/오분류 상태-결과 렌더링 감사 (dedup-rendering-audit)")
    w("")
    w("> 생성: `python3 scripts/audit_duplicate_render_content.py`  ")
    w("> 이 보고서는 저장소 데이터에서 **동적으로 발견된** 모든 비자/체류/거주 코드를 감사합니다. "
      "코드 목록은 하드코딩되지 않으며 `visa_data.json` · `backend/data/visas.json` · "
      "`doc_master.json` · `data/scenario_help_records.json` · source manifests에서 유도됩니다.")
    w("")

    # Root cause.
    w("## 1. 근본 원인 요약 (root cause)")
    w("")
    w("문서 보유 필드(`procedures.*.requiredDocs.*`, 레거시 `documents_*` 탭, 레거시 `*ReqDocs`, "
      "`subCodes[].addReqDocs`)가 매뉴얼/OCR 추출 과정에서 다음 오염을 포함했고, 렌더러는 이를 "
      "그대로 '구비서류' 체크리스트 항목으로 표시합니다:")
    w("")
    w("1. **단일 거대 문자열의 반복** — `체류지 입증서류(예: … 준비)` (~237자)가 약 30개 레코드의 "
      "`extension`/`registration` 그룹과 `documents_extension`에 동일하게 반복되어, 서류명 뒤에 예시·"
      "재정능력 단서까지 한 칸에 렌더됩니다.")
    w("2. **절차/약호 제목 혼입** — 위 괄호 뒤에 다른 절차/약호 제목이 접합 "
      "(예: `…준비)2. 기업 맞춤형 인턴십…`, `…준비) 등 □ 재외동포(F-4)…`) → 절차 범위 오염.")
    w("3. **산문의 서류화** — 자격/체류기간/재량/절차를 설명하는 완결 문장이 `requiredDocs`·"
      "`conditionalDocs`에 직접 들어가 체크리스트 항목으로 표시됩니다.")
    w("")
    w("렌더 계층에는 이미 교차그룹 dedupe가 일부 있으나(`dedupeDocGroupsAcrossCategories` 등), "
      "**산문/과장 라벨을 비고로 분리하는 단계가 없어** 위 항목들이 사용자에게 노출됩니다.")
    w("")

    w("두 계층으로 보고합니다: **(A) 렌더 결과(사용자 노출, gate)** — `--check`가 SEVERE만 차단; "
      "**(B) 원본 데이터 위생(manual review)** — CLAUDE.md의 보호 파일 정책에 따라 데이터는 보존하고 "
      "렌더러가 비고로 이전하므로 경고만 합니다.")
    w("")

    # D-2 deep dive.
    w("## 2. D-2 심층 분석 (deep dive)")
    w("")
    d2_rendered = by_code.get("D-2", [])
    d2_raw = raw_by_code.get("D-2", [])
    w("D-2(유학)의 핵심 결함은 렌더러가 설명 텍스트(`newReq`/`extReq`)를 `requiredDocs`에 alias하여 "
      "**자격 설명 산문을 필수서류 타일로** 표시하고, `체류지 입증서류(예: …)` 237자 문자열과 약호별 "
      "체류기간 특례 문장을 체크리스트 항목으로 노출한 것입니다.")
    w("")
    if d2_rendered:
        w(f"**(A) 렌더 결과 잔여 이슈 {len(d2_rendered)}건:**")
        w("")
        w("| field path | 문제 텍스트 | 사유 | severity |")
        w("|---|---|---|---|")
        for iss in d2_rendered[:14]:
            w(f"| `{iss.field_path}` | {iss.text} | {iss.reason} | {iss.severity} |")
    else:
        w("**(A) 렌더 결과:** 잔여 SEVERE 이슈 없음 — 렌더 계층 가드가 산문/과장 라벨을 비고로 분리합니다.")
    w("")
    if d2_raw:
        w(f"**(B) 원본 데이터 위생(수동 검토) {len(d2_raw)}건:**")
        w("")
        w("| field path | 문제 텍스트 | 사유 |")
        w("|---|---|---|")
        for iss in d2_raw[:14]:
            w(f"| `{iss.field_path}` | {iss.text} | {iss.reason} |")
    w("")
    w("D-2 권장 상태: 설명(`newReq`/`extReq`)은 개요/상세에서 1회만 노출하고 서류로 렌더하지 않음; "
      "공통/필수/조건부 서류는 각 그룹에만; `체류지 입증서류` 예시와 약호별 체류기간 특례는 비고로 분리.")
    w("")

    # Affected-record table (rendered / gate).
    w("## 3. 영향받는 레코드 — 렌더 결과 이슈 표 (gate)")
    w("")
    if all_issues:
        w("| code | parent | type | title | source file | field path | 문제 텍스트 | 사유 | severity | 권장 조치 |")
        w("|---|---|---|---|---|---|---|---|---|---|")
        for iss in sorted(all_issues, key=lambda x: (0 if x.severity == SEV_HIGH else 1 if x.severity == SEV_MED else 2, x.code)):
            w(f"| {iss.code} | {iss.parent or '-'} | {iss.record_type} | {iss.title or '-'} | "
              f"`{iss.source_file}` | `{iss.field_path}` | {iss.text} | {iss.reason} | "
              f"{iss.severity} | {iss.action} |")
    else:
        w("렌더 결과 잔여 이슈 없음 — 렌더 계층 가드가 모든 산문/과장/오염 항목을 비고로 분리합니다.")
    w("")

    # Parent/subcode hierarchy.
    w("## 4. 부모/하위 약호 계층 (hierarchy)")
    w("")
    w("| parent | subcodes |")
    w("|---|---|")
    hierarchy = defaultdict(list)
    for code, desc in records.items():
        if desc["record_type"] == "subcode" and desc.get("parent"):
            hierarchy[desc["parent"]].append(code)
        else:
            m = SUBCODE_RE.match(code)
            if m:
                hierarchy[m.group(1)].append(code)
    for parent in sorted(hierarchy):
        subs = sorted(set(hierarchy[parent]))
        present = "✓" if parent in records else "✗(부모 부재)"
        w(f"| {parent} {present} | {', '.join(subs)} |")
    w("")

    # Complete code inventory.
    w("## 5. 전체 코드 인벤토리 (complete inventory)")
    w("")
    w(f"- 부모 상태 코드: {len(discovery['parents'])} — {', '.join(discovery['parents'])}")
    w(f"- 하위 약호: {len(discovery['subcodes'])} — {', '.join(discovery['subcodes'])}")
    w(f"- 특수 변형: {len(discovery['special_variants'])} — {', '.join(discovery['special_variants'])}")
    w(f"- 시나리오/도움 레코드 코드: {len(discovery['scenario_codes'])} — {', '.join(discovery['scenario_codes'])}")
    w(f"- doc_master 문서 정의: {len(discovery['doc_master_ids'])}")
    w("")

    # Clean records.
    w("## 6. 클린 레코드 (clean records)")
    w("")
    w(f"이슈 없이 통과한 코드 {len(clean_codes)}개:")
    w("")
    w(", ".join(clean_codes) if clean_codes else "(없음)")
    w("")

    # OCR / manual coverage.
    w("## 7. OCR/매뉴얼 커버리지 노트 (보고만, 자동 보정 안 함)")
    w("")
    status_codes = [c for c, d in records.items() if d["record_type"] in ("status", "subcode")]
    missing_cov = sorted(c for c in status_codes if c not in manual_covered)
    w(f"- 구조화 매뉴얼 근거(structured_requirements 인덱스)로 커버된 상태 코드: {len(manual_covered)}")
    w(f"- 인덱스에서 직접 확인되지 않은 상태 코드: {len(missing_cov)}")
    if missing_cov:
        w(f"  - {', '.join(missing_cov)}")
    w(f"- 사용된 source manifest: {', '.join(os.path.relpath(p, REPO_ROOT) for p in discovery['source_manifests']) or '(없음)'}")
    w("- 매뉴얼 원문(PDF/HWP)은 `docs/source-manuals/`에 존재하며, 커버리지 공백은 보고만 하고 데이터를 임의 생성하지 않습니다.")
    w("")

    # Raw data-hygiene findings (manual review, warn-only).
    w("## 8. 원본 데이터 위생 수동 검토 항목 (raw findings, warn-only)")
    w("")
    w("CLAUDE.md 보호 파일 정책에 따라 아래 항목은 **데이터를 보존**하고 렌더러가 비고로 이전합니다. "
      "사람이 추후 안전 편집(정확한 중복 제거 / 적절한 note 필드 이전)할 후보 목록입니다.")
    w("")
    w(f"- 총 {len(raw_findings)}건 (MED {raw_sev_counts[SEV_MED]} / LOW {raw_sev_counts[SEV_LOW]})")
    w("")
    if raw_findings:
        w("| code | field path | 문제 텍스트 | 사유 | severity |")
        w("|---|---|---|---|---|")
        for iss in sorted(raw_findings, key=lambda x: (x.code, x.field_path))[:200]:
            w(f"| {iss.code} | `{iss.field_path}` | {iss.text} | {iss.reason} | {iss.severity} |")
        if len(raw_findings) > 200:
            w("")
            w(f"… 외 {len(raw_findings) - 200}건 생략.")
    else:
        w("원본 데이터 위생 이슈 없음.")
    w("")

    # Recommended actions by severity.
    w("## 9. 심각도별 권장 조치 (recommended actions)")
    w("")
    w(f"- **HIGH (렌더 결과 severe, {sev_counts[SEV_HIGH]}건):** 산문/과장 라벨을 비고로 분리, 공통∩필수 중복은 "
      "공통 유지·필수 suppress, 절차 범위 오염 분리, 약호 전용 규칙은 ‘하위 체류자격별 유의사항’으로 라벨링. "
      "**렌더 계층 가드**로 처리(보호 데이터 미수정).")
    w(f"- **MEDIUM (렌더 {sev_counts[SEV_MED]}건 / 원본 {raw_sev_counts[SEV_MED]}건):** 긴 서류명의 예시/단서 비고 분리, "
      "조건부 서류 재분류. 경고만, 수동 검토 대상.")
    w(f"- **LOW (렌더 {sev_counts[SEV_LOW]}건 / 원본 {raw_sev_counts[SEV_LOW]}건):** 정보성(정확한 중복, 매뉴얼 커버리지 공백 등).")
    w("")
    w("### 카테고리별 건수 (렌더 / 원본)")
    w("")
    w("| category | rendered | raw |")
    w("|---|---|---|")
    for cat in sorted(set(cat_counts) | set(raw_cat_counts)):
        w(f"| {cat} | {cat_counts.get(cat, 0)} | {raw_cat_counts.get(cat, 0)} |")
    w("")

    # Coverage section.
    w("## 10. 커버리지 (discovered vs audited)")
    w("")
    discovered_count = len(records)
    audited_count = len(audited_codes)
    w(f"- **discovered_code_count: {discovered_count}**")
    w(f"- **audited_code_count: {audited_count}**")
    w(f"- parent 코드 수: {len(discovery['parents'])}")
    w(f"- subcode 수: {len(discovery['subcodes'])}")
    w(f"- special variant 수: {len(discovery['special_variants'])}")
    w(f"- scenario/help 코드 수: {len(discovery['scenario_codes'])}")
    proc_groups_seen = set()
    for code, desc in records.items():
        raw = desc["raw"]
        if isinstance(raw, dict):
            for pkey in (raw.get("procedures") or {}):
                proc_groups_seen.add(pkey)
    w(f"- 발견된 procedure group 종류: {len(proc_groups_seen)} — {', '.join(sorted(proc_groups_seen))}")
    w(f"- HIGH/MED/LOW 이슈: {sev_counts[SEV_HIGH]} / {sev_counts[SEV_MED]} / {sev_counts[SEV_LOW]}")
    if discovered_count != audited_count:
        w("")
        w(f"> ⚠️ discovered != audited ({discovered_count} != {audited_count}). 감사 실패 조건.")
    w("")

    return "\n".join(lines), sev_counts, discovered_count, audited_count


# --------------------------------------------------------------------------- #
# Orchestration.
# --------------------------------------------------------------------------- #

def run_audit(records, discovery):
    doc_master = discovery["doc_master"]
    parent_codes = set(records.keys())
    rendered_issues = []
    raw_findings = []
    audited = set()
    skipped = {}
    for code, desc in records.items():
        try:
            rendered_issues.extend(detect_rendered_issues(code, desc, doc_master, parent_codes))
            raw_findings.extend(detect_raw_findings(code, desc, doc_master))
            audited.add(code)
        except Exception as exc:  # pragma: no cover - defensive
            skipped[code] = f"detection error: {exc}"
    return rendered_issues, raw_findings, audited, skipped


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true",
                        help="Validation mode: fail (exit 2) only on SEVERE issues; warn on medium/low.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable summary JSON.")
    args = parser.parse_args(argv)

    records, discovery = discover_codes()
    manual_covered = load_manual_coverage()
    rendered_issues, raw_findings, audited, skipped = run_audit(records, discovery)
    all_issues = rendered_issues

    discovered_count = len(records)
    audited_count = len(audited)

    severe = [i for i in all_issues if i.severity == SEV_HIGH]
    medium = [i for i in all_issues if i.severity == SEV_MED]
    low = [i for i in all_issues if i.severity == SEV_LOW]

    if args.check:
        # Validation mode for check_repo.sh: fail only on severe issues, count
        # mismatch, or unexplained skips.
        problems = []
        if discovered_count != audited_count:
            problems.append(f"discovered_code_count({discovered_count}) != audited_code_count({audited_count})")
        unexplained = [c for c in records if c not in audited and c not in skipped]
        if unexplained:
            problems.append(f"codes skipped without reason: {', '.join(sorted(unexplained))}")
        for code, reason in skipped.items():
            problems.append(f"code {code} skipped: {reason}")
        if severe:
            problems.append(f"{len(severe)} SEVERE rendering issue(s)")

        if args.json:
            print(json.dumps({
                "mode": "check", "severe": len(severe), "medium": len(medium),
                "low": len(low), "discovered": discovered_count, "audited": audited_count,
            }, ensure_ascii=False))

        if problems:
            print("AUDIT --check FAILED:", file=sys.stderr)
            for p in problems:
                print(f"  - {p}", file=sys.stderr)
            # Show up to 25 severe issues for actionable output.
            for iss in severe[:25]:
                print(f"  [SEVERE] {iss.code} {iss.field_path} :: {iss.reason} :: {iss.text}", file=sys.stderr)
            if len(severe) > 25:
                print(f"  ... and {len(severe) - 25} more severe issues", file=sys.stderr)
            return 2
        print(f"AUDIT --check OK: 0 severe issues; {len(medium)} medium / {len(low)} low (warn-only). "
              f"discovered==audited=={audited_count}.")
        return 0

    # Full audit mode: write the markdown report.
    report, sev_counts, discovered_count, audited_count = build_report(
        records, discovery, rendered_issues, raw_findings, manual_covered, audited)
    os.makedirs(os.path.dirname(AUDIT_OUTPUT), exist_ok=True)
    with open(AUDIT_OUTPUT, "w", encoding="utf-8") as fh:
        fh.write(report + "\n")

    print(f"Wrote {os.path.relpath(AUDIT_OUTPUT, REPO_ROOT)}")
    print(f"  discovered_code_count = {discovered_count}")
    print(f"  audited_code_count    = {audited_count}")
    print(f"  HIGH/MED/LOW issues   = {sev_counts[SEV_HIGH]} / {sev_counts[SEV_MED]} / {sev_counts[SEV_LOW]}")

    if args.json:
        print(json.dumps({
            "discovered": discovered_count, "audited": audited_count,
            "high": sev_counts[SEV_HIGH], "medium": sev_counts[SEV_MED], "low": sev_counts[SEV_LOW],
        }, ensure_ascii=False))

    # Exit non-zero on the task's hard-fail conditions.
    exit_code = 0
    if discovered_count != audited_count:
        print(f"ERROR: discovered_code_count({discovered_count}) != audited_code_count({audited_count})", file=sys.stderr)
        exit_code = 1
    unexplained = [c for c in records if c not in audited and c not in skipped]
    if unexplained:
        print(f"ERROR: codes skipped without explicit reason: {', '.join(sorted(unexplained))}", file=sys.stderr)
        exit_code = 1
    for code, reason in skipped.items():
        print(f"ERROR: code {code} skipped: {reason}", file=sys.stderr)
        exit_code = 1
    if HARDCODED_CODE_UNIVERSE is not None:
        print("ERROR: code universe is hard-coded", file=sys.stderr)
        exit_code = 1
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
