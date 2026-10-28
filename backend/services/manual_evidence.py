"""Approved manual excerpts for /api/ask questions without verified knowledge facts.

The Waymaker knowledge platform publishes verified document facts for a handful
of status/procedure pairs only (D-2 / D-4 / E-7 extension). Every other question
(E-7 workplace change, F-6 extension, G-1-5 activities, E-9 visa issuance, ...)
used to reach the model with no source at all, and the model filled the gap from
memory — e.g. it named a "체류자격 증명서" that no manual lists (Waymaker QA
2026-10-16). The approved 2026.9 manuals are already in the FTS index built by
``scripts/build_manual_search_index.py``; this module retrieves excerpts from it
for the answer prompt and the source panel.

Rules (CLAUDE.md), enforced here rather than left to callers:

* Only ``approval_state = 'approved'`` chunks with ``direct_evidence = 1``.
  Superseded and review-pending editions never reach the prompt.
* One procedure scope per block, never mixed: stay procedures (체류자격 변경 /
  체류기간 연장 / 외국인등록 / 재입국 / 체류자격외 활동 / 근무처 변경·추가) read the
  외국인체류 안내매뉴얼 only; visa issuance (사증발급 / 사증발급인정서 / 공관 사증)
  reads the 사증발급 안내매뉴얼 only. A question naming both gets two separate,
  labelled blocks.
* Sub-codes are not flattened. With an exact sub-code (G-1-5) a chunk tagged
  only with a sibling sub-code (G-1-6) is dropped; a parent-level chunk is kept
  and labelled as parent-level. With only a parent (F-6), a chunk tagged only
  with F-6-1 is kept but labelled as F-6-1-only, so the prompt can tell the
  model not to present it as an F-6-wide rule.
* Nothing is rewritten. Excerpts are the indexed source text (OCR / extracted
  PDF text), trimmed to a budget. They are retrieved automatically: no person
  chose them for this question, and every consumer says so.

Read-only, stdlib only, no network. Never raises: any failure degrades to a
status the caller reports (``index_unavailable`` / ``no_results``), never to a
silent empty answer basis.
"""
from __future__ import annotations

import os
import re
import sqlite3
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from . import manual_locator as _locator
from . import manual_registry as _registry
from . import manual_search as _search
from . import procedure_location as _procedure_location

MANUAL_EVIDENCE_VERSION = "2026-10-manual-evidence-v1"

SCOPE_STAY = "stay"
SCOPE_VISA = "visa_issuance"

STATUS_USED = "approved_excerpts"
STATUS_NO_RESULTS = "no_results"
STATUS_INDEX_UNAVAILABLE = "index_unavailable"
STATUS_NOT_ATTEMPTED = "not_attempted"

# Manual family (services/manual_registry.derive_family) per procedure scope.
_SCOPE_FAMILY = {SCOPE_STAY: "stay_guide_manual", SCOPE_VISA: "visa_issuance_manual"}
_SCOPE_TITLE = {SCOPE_STAY: "외국인체류 안내매뉴얼", SCOPE_VISA: "사증발급 안내매뉴얼"}
_SCOPE_TITLE_EN = {SCOPE_STAY: "Stay Manual for Foreign Residents", SCOPE_VISA: "Visa Issuance Manual"}
_SCOPE_LABEL = {SCOPE_STAY: "체류 절차", SCOPE_VISA: "사증발급 절차"}
ISSUING_BODY = "법무부 출입국·외국인정책본부"


def _env_int(name: str, default: int) -> int:
    try:
        return max(1, int(float(os.environ.get(name, "") or default)))
    except (TypeError, ValueError):
        return default


#: Budget. The final /api/ask prompt already carries the answer-quality
#: contract, law/legal-analysis context and the visa_data block; ~4.2k chars of
#: Korean excerpts (about 3k tokens) keeps the whole prompt well inside the free
#: models' context while leaving room for the answer.
MAX_EXCERPTS = _env_int("PARADISO_ASK_MANUAL_EVIDENCE_MAX_EXCERPTS", 5)
MAX_TOTAL_CHARS = _env_int("PARADISO_ASK_MANUAL_EVIDENCE_MAX_CHARS", 4200)
MAX_EXCERPT_CHARS = _env_int("PARADISO_ASK_MANUAL_EVIDENCE_EXCERPT_CHARS", 1100)
_POOL = 40
_MIN_EXCERPT_CHARS = 80

# ---------------------------------------------------------------------------
# Procedure scope
# ---------------------------------------------------------------------------
# Backend task type (paradiso_backend._detect_task_type) -> (scope, Korean label).
TASK_SCOPE: Dict[str, Tuple[str, str]] = {
    "extension": (SCOPE_STAY, "체류기간 연장허가"),
    "status_change": (SCOPE_STAY, "체류자격 변경허가"),
    "workplace_change": (SCOPE_STAY, "근무처 변경·추가"),
    "activities_outside_status": (SCOPE_STAY, "체류자격외 활동허가"),
    "foreigner_registration": (SCOPE_STAY, "외국인등록"),
    "address_report": (SCOPE_STAY, "체류지 변경신고"),
    "passport_info_report": (SCOPE_STAY, "외국인등록사항 변경신고"),
    "family_status_change": (SCOPE_STAY, "체류자격 부여"),
    "marriage_divorce_status_change": (SCOPE_STAY, "체류기간 연장·체류자격 변경"),
    "academic_status_change": (SCOPE_STAY, "체류 관리"),
}

_VISA_SCOPE_RE = re.compile(
    r"사증\s*발급|사증발급인정서|발급인정서|비자\s*발급|사증\s*신청|비자\s*신청|재외\s*공관|공관|영사관|대사관"
    r"|visa issuance|issuance certificate|certificate (?:of|for) (?:confirmation of )?visa|apply for a visa|visa application",
    re.IGNORECASE,
)
_REENTRY_RE = re.compile(r"재입국|re-?entry", re.IGNORECASE)
# Work wording without a detected procedure. For a status held in Korea this is
# an activity-scope (stay) question; it never routes to visa issuance.
_WORK_RE = re.compile(r"취업|일하|일을|일할|근무|아르바이트|알바|단순노무|고용|\bwork\b|\bjob\b|employ", re.IGNORECASE)

# Procedure keywords searched alongside the question's own words.
_PROCEDURE_TERMS: Dict[str, Tuple[str, ...]] = {
    "체류기간 연장허가": ("체류기간", "연장허가", "연장"),
    "체류자격 변경허가": ("체류자격", "변경허가", "변경"),
    "근무처 변경·추가": ("근무처", "변경", "추가"),
    "체류자격외 활동허가": ("체류자격외", "활동허가", "취업"),
    "외국인등록": ("외국인등록", "등록"),
    "체류지 변경신고": ("체류지", "변경신고"),
    "외국인등록사항 변경신고": ("등록사항", "변경신고"),
    "체류자격 부여": ("체류자격", "부여"),
    "체류기간 연장·체류자격 변경": ("연장", "변경", "이혼"),
    "체류 관리": ("체류", "변경"),
    "재입국허가": ("재입국",),
    "활동범위": ("활동범위", "취업", "취업활동"),
    "사증발급": ("사증발급인정서", "사증발급", "사증", "첨부서류", "제출서류"),
}


def procedure_scopes(question: str, task_type: Optional[str], has_code: bool) -> List[Tuple[str, str]]:
    """``[(scope, procedure_label), ...]`` for the question; empty when unknown.

    Visa issuance wording wins over a generic "연장" only when no stay task was
    detected; a question naming both procedures gets both scopes, as separate
    blocks. Without a detected procedure and without a status code there is no
    scope, and no excerpt is retrieved (the caller keeps the honest "no manual
    basis" state rather than guessing a manual).
    """
    text = str(question or "")
    scopes: List[Tuple[str, str]] = []
    visa = bool(_VISA_SCOPE_RE.search(text))
    stay = TASK_SCOPE.get(str(task_type or ""))
    if stay:
        scopes.append(stay)
    elif _REENTRY_RE.search(text):
        scopes.append((SCOPE_STAY, "재입국허가"))
    if visa:
        scopes.append((SCOPE_VISA, "사증발급"))
    if not scopes and has_code and _WORK_RE.search(text):
        scopes.append((SCOPE_STAY, "활동범위"))
    # A stay task detected only from the word "연장"/"변경" next to explicit visa
    # issuance wording ("사증발급인정서 연장") is still a visa question.
    if visa and stay and stay[0] == SCOPE_STAY and not _stay_procedure_named(text):
        scopes = [s for s in scopes if s[0] == SCOPE_VISA]
    return _apply_location(text, scopes)


def _location_cues_enabled() -> bool:
    return os.environ.get("VISABLE_MANUAL_LOCATION_CUES", "1").strip().lower() not in ("0", "false", "off", "no")


def _apply_location(text: str, scopes: List[Tuple[str, str]]) -> List[Tuple[str, str]]:
    """Where the foreigner is (services/procedure_location.py) settles what the
    procedure words leave open. A question with no procedure gets the manual for
    where they are; a stay scope resting only on "체류기간" or on a status code plus a
    work word ("D-4로 가면 체류기간은", "F-1-D … work") is a visa question for
    someone abroad. A stay procedure named outright (연장허가, 외국인등록, 근무처 …)
    is never overridden. ``VISABLE_MANUAL_LOCATION_CUES=0`` turns this off."""
    if not _location_cues_enabled():
        return scopes
    where = _procedure_location.location(text)
    if not where:
        return scopes
    if not scopes:
        return [(SCOPE_VISA, "사증발급")] if where == "abroad" else [(SCOPE_STAY, "체류 관리")]
    named = {m.group(0) for m in _STAY_NAMED_RE.finditer(text)}
    weak_stay = all(scope == SCOPE_STAY for scope, _ in scopes) and all(
        re.fullmatch(r"체류\s*기간", n) for n in named) and not _procedure_location.IN_KOREA_TASK_RE.search(text)
    if where == "abroad" and weak_stay:
        return [(SCOPE_VISA, "사증발급")]
    return scopes


_STAY_NAMED_RE = re.compile(
    r"체류기간|체류\s*연장|연장허가|체류자격\s*변경|변경허가|근무처|외국인등록|체류자격외|자격외\s*활동|시간제|재입국|체류지"
    r"|extension of stay|extend my stay|change of status|alien registration|workplace",
    re.IGNORECASE,
)


def _stay_procedure_named(text: str) -> bool:
    return bool(_STAY_NAMED_RE.search(text or ""))


# ---------------------------------------------------------------------------
# Codes
# ---------------------------------------------------------------------------
_CODE_RE = re.compile(r"(?<![A-Za-z0-9])([A-H])\s?-?\s?(\d{1,2})((?:-[0-9]{1,3}[A-Z]?|-[A-Z]{1,2}\b)*)", re.IGNORECASE)
_TAG_CODE_RE = re.compile(r"^[A-H]-\d{1,2}(?:-[0-9A-Z]+)*$")


def _parent(code: str) -> str:
    parts = code.split("-")
    return "-".join(parts[:2]) if len(parts) >= 2 else code


def request_codes(question: str, visa_code: Optional[str], visa_sub_code: Optional[str]) -> Tuple[str, str]:
    """``(parent, exact_subcode)`` for retrieval.

    The backend detector keeps free-text sub-codes out of DOCUMENT routing on
    purpose. Retrieval is different: an explicit "G-1-5" in the question is the
    best filter there is, and dropping it would retrieve every G-1 sub-code's
    rules — exactly the flattening the rules forbid. The sub-code is used only to
    pick and label excerpts; it never selects a verified document list.
    """
    parent = str(visa_code or "").strip().upper()
    exact = str(visa_sub_code or "").strip().upper()
    if not exact:
        for m in _CODE_RE.finditer(str(question or "")):
            code = f"{m.group(1).upper()}-{m.group(2)}{(m.group(3) or '').upper()}"
            if code.count("-") >= 2 and (not parent or _parent(code) == parent):
                exact = code
                parent = parent or _parent(code)
                break
    if exact and not parent:
        parent = _parent(exact)
    return parent, exact


# ---------------------------------------------------------------------------
# Query terms
# ---------------------------------------------------------------------------
_PARTICLE_RE = re.compile(
    r"(으로부터|에서는|에서|에게|으로|하려면|하려고|하는데|인데요|인데|이에요|예요|입니다|합니다|하나요|할까요|한가요|은|는|이|가|을|를|에|의|도|와|과|로|만)$"
)
_STOPWORDS = {
    "어떻게", "무엇", "무엇인가요", "알려주세요", "알려줘", "필요한", "필요", "궁금합니다", "궁금해요", "가능한가요",
    "있나요", "있을까요", "되나요", "해야", "하나요", "어떤", "관련", "그리고", "지금", "현재", "비자", "제가", "저는",
    "회사를", "옮기려고", "하고", "있는데", "합니다", "싶어요", "싶습니다", "수", "있는지", "방법",
}


def _question_terms(question: str, limit: int = 8) -> List[str]:
    out: List[str] = []
    for raw in re.findall(r"[가-힣]{2,}", str(question or "")):
        word = raw
        for _ in range(2):
            stripped = _PARTICLE_RE.sub("", word)
            if len(stripped) < 2 or stripped == word:
                break
            word = stripped
        if len(word) < 2 or word in _STOPWORDS or raw in _STOPWORDS:
            continue
        if word not in out:
            out.append(word)
        if len(out) >= limit:
            break
    return out


def _fts_or_query(terms: Iterable[str]) -> str:
    cleaned: List[str] = []
    for term in terms:
        t = re.sub(r'["*():^{}\[\]\-]+', " ", str(term or "")).strip()
        for part in t.split():
            if len(part) >= 2 and part not in cleaned:
                cleaned.append(part)
    return " OR ".join(f'"{t}"*' for t in cleaned[:16])


# ---------------------------------------------------------------------------
# Index access
# ---------------------------------------------------------------------------
_COLUMNS = (
    "c.chunk_id, c.source_id, c.approval_state, c.direct_evidence, c.domain, c.page,"
    " c.heading, c.status_codes, c.manual_version, f.body"
)


def _connect(path: Optional[str]) -> Optional[sqlite3.Connection]:
    resolved = _search.index_path(path)
    if not os.path.exists(resolved):
        return None
    try:
        con = sqlite3.connect(f"file:{resolved}?mode=ro", uri=True)
        con.row_factory = sqlite3.Row
        return con
    except sqlite3.Error:
        return None


def _row_dict(row: sqlite3.Row, score: float = 0.0) -> Dict[str, Any]:
    return {
        "chunk_id": int(row["chunk_id"]),
        "source_id": str(row["source_id"] or ""),
        "page": int(row["page"] or 0),
        "heading": str(row["heading"] or ""),
        "status_codes": [c for c in str(row["status_codes"] or "").split() if c],
        "manual_version": str(row["manual_version"] or ""),
        "body": str(row["body"] or ""),
        "bm25": float(score or 0.0),
    }


def _approved(row: sqlite3.Row, scope: str) -> bool:
    if str(row["approval_state"]) != _registry.STATE_APPROVED or not int(row["direct_evidence"] or 0):
        return False
    family, _ = _registry.derive_family(str(row["source_id"] or ""))
    return family == _SCOPE_FAMILY[scope]


def chunk_bodies(chunk_ids: Sequence[int], *, path: Optional[str] = None) -> Dict[int, str]:
    """Full body text of indexed chunks (``search_manuals`` returns ≤320-char snippets).

    Approved direct-evidence chunks only: a superseded or review-pending chunk id
    returns nothing, so a caller cannot ground an answer on it by id.
    """
    ids = [int(i) for i in chunk_ids if str(i).strip().lstrip("-").isdigit()]
    if not ids:
        return {}
    con = _connect(path)
    if con is None:
        return {}
    try:
        marks = ",".join("?" for _ in ids)
        rows = con.execute(
            f"SELECT c.chunk_id, f.body FROM chunk c JOIN chunk_fts f ON f.rowid = c.chunk_id"
            f" WHERE c.chunk_id IN ({marks}) AND c.approval_state = ? AND c.direct_evidence = 1",
            [*ids, _registry.STATE_APPROVED],
        ).fetchall()
        return {int(r["chunk_id"]): str(r["body"] or "") for r in rows}
    except sqlite3.Error:
        return {}
    finally:
        con.close()


def _search_pool(con: sqlite3.Connection, scope: str, match: str, parent: str) -> List[Dict[str, Any]]:
    if not match:
        return []
    sql = (
        f"SELECT {_COLUMNS}, bm25(chunk_fts) AS score"
        " FROM chunk_fts f JOIN chunk c ON c.chunk_id = f.rowid"
        " WHERE chunk_fts MATCH ? AND c.approval_state = ? AND c.direct_evidence = 1 AND c.page > 0"
    )
    params: List[Any] = [match, _registry.STATE_APPROVED]
    if parent:
        sql += (
            " AND (instr(' ' || c.status_codes || ' ', ?) > 0"
            " OR instr(' ' || c.status_codes || ' ', ?) > 0 OR instr(f.body, ?) > 0)"
        )
        params += [f" {parent} ", f" {parent}-", parent]
    sql += " ORDER BY score LIMIT ?"
    params.append(_POOL * 3)
    rows = con.execute(sql, params).fetchall()
    return [_row_dict(r, r["score"]) for r in rows if _approved(r, scope)][:_POOL]


def _pages(con: sqlite3.Connection, scope: str, pages: Sequence[int]) -> List[Dict[str, Any]]:
    if not pages:
        return []
    marks = ",".join("?" for _ in pages)
    rows = con.execute(
        f"SELECT {_COLUMNS} FROM chunk c JOIN chunk_fts f ON f.rowid = c.chunk_id"
        f" WHERE c.page IN ({marks}) AND c.approval_state = ? AND c.direct_evidence = 1",
        [*pages, _registry.STATE_APPROVED],
    ).fetchall()
    return [_row_dict(r) for r in rows if _approved(r, scope)]


# ---------------------------------------------------------------------------
# Applicability (sub-code aware)
# ---------------------------------------------------------------------------
def _family_codes(chunk: Dict[str, Any], parent: str) -> List[str]:
    """Codes of the requested family the chunk is tagged with (tags + body)."""
    if not parent:
        return []
    found: List[str] = []
    for code in chunk["status_codes"]:
        if _TAG_CODE_RE.match(code) and (code == parent or code.startswith(parent + "-")) and code not in found:
            found.append(code)
    return found


def applicability(chunk: Dict[str, Any], parent: str, exact: str) -> Tuple[str, List[str]]:
    """``(level, codes)``. Levels: exact_subcode / parent / subcode_specific /
    sibling_subcode (dropped) / untagged."""
    codes = _family_codes(chunk, parent)
    body = chunk.get("body") or ""
    if exact:
        if exact in codes or re.search(rf"(?<![A-Z0-9-]){re.escape(exact)}(?![0-9A-Z-])", body):
            return "exact_subcode", [exact]
        siblings = [c for c in codes if c != parent]
        if parent in codes:
            return "parent", [parent]
        if siblings:
            return "sibling_subcode", siblings
        return "untagged", []
    if not parent:
        return "untagged", []
    if parent in codes:
        return "parent", [parent]
    subs = [c for c in codes if c != parent]
    if subs:
        return "subcode_specific", subs
    return "untagged", []


_LEVEL_SCORE = {"exact_subcode": 3.0, "parent": 2.0, "subcode_specific": 1.5, "untagged": 0.0}


# ---------------------------------------------------------------------------
# Excerpt text
# ---------------------------------------------------------------------------
_PAGE_FOOTER_RE = re.compile(r"^\s*-\s*\d{1,4}\s*-\s*$")
_HEADING_CODE_RE = re.compile(r"\(([A-H]-\d{1,2}(?:-[0-9A-Z]+)*)")
_TOC_RE = re.compile(r"(?:[·….]{8,}.*){2,}", re.S)


def excerpt_text(body: str, *, limit: int = MAX_EXCERPT_CHARS, focus: Sequence[str] = ()) -> str:
    """Source text trimmed to ``limit`` on a line boundary. Never rewritten.

    Blank lines and the printed page footer ("- 498 -") are dropped. When the
    page is longer than the limit the window starts at the first line naming a
    focus term (the procedure or the code), so the relevant section survives
    the trim.
    """
    lines = [ln.rstrip() for ln in str(body or "").splitlines()]
    lines = [ln for ln in lines if ln.strip() and not _PAGE_FOOTER_RE.match(ln)]
    if not lines:
        return ""
    start = 0
    if sum(len(ln) + 1 for ln in lines) > limit and focus:
        for i, ln in enumerate(lines):
            if any(term and term in ln for term in focus):
                start = max(0, i - 1)
                break
    out: List[str] = []
    used = 0
    for ln in lines[start:]:
        if used + len(ln) + 1 > limit:
            if not out:
                out.append(ln[: max(0, limit - 1)] + "…")
            else:
                out.append("…")
            break
        out.append(ln)
        used += len(ln) + 1
    if start > 0:
        out.insert(0, "…")
    return "\n".join(out).strip()


def citation_label(scope: str, version: str, page: int) -> str:
    return f"「{_SCOPE_TITLE[scope]} {version}」 p.{page}"


# ---------------------------------------------------------------------------
# Retrieval
# ---------------------------------------------------------------------------
def _retrieve_scope(
    con: sqlite3.Connection,
    question: str,
    scope: str,
    procedure: str,
    parent: str,
    exact: str,
    task_type: Optional[str],
) -> List[Dict[str, Any]]:
    terms = list(_PROCEDURE_TERMS.get(procedure, ())) + _question_terms(question)
    pool = _search_pool(con, scope, _fts_or_query(terms), parent)
    by_key: Dict[Tuple[str, int], Dict[str, Any]] = {}
    for rank, chunk in enumerate(pool):
        chunk["score"] = max(0.0, 2.0 - rank * 0.08)
        by_key.setdefault((chunk["source_id"], chunk["page"]), chunk)

    # Stay procedures: the status guidance records where each status +
    # procedure section starts (services/manual_locator.py). That page and the
    # next one (the section usually continues there) outrank keyword hits.
    anchors: Dict[int, float] = {}
    if scope == SCOPE_STAY and parent:
        found = _locator.locate(parent, exact or None, task_type)
        for entry in (found or {}).get("entries", [])[:6]:
            page = int(entry["page"])
            anchors[page] = max(anchors.get(page, 0.0), 5.0)
            anchors[page + 1] = max(anchors.get(page + 1, 0.0), 3.5)
    for chunk in _pages(con, scope, sorted(anchors)):
        key = (chunk["source_id"], chunk["page"])
        existing = by_key.get(key)
        if existing is None:
            chunk["score"] = 0.0
            by_key[key] = existing = chunk
        existing["score"] = existing.get("score", 0.0) + anchors.get(chunk["page"], 0.0)
        existing["anchor"] = True

    focus = [t for t in (exact, parent, *(_PROCEDURE_TERMS.get(procedure, ())[:2])) if t]
    q_terms = _question_terms(question)
    ranked: List[Dict[str, Any]] = []
    for chunk in by_key.values():
        body = chunk["body"]
        if _TOC_RE.search(body) and not chunk.get("anchor"):
            continue  # table of contents / annex index: names sections, states nothing
        level, codes = applicability(chunk, parent, exact)
        if level == "sibling_subcode":
            continue  # another sub-code's rules: never shown for this sub-code
        if level == "untagged" and not chunk.get("anchor"):
            continue
        level_score = _LEVEL_SCORE[level] if level != "untagged" else 1.0
        tags = [c for c in chunk["status_codes"] if _TAG_CODE_RE.match(c)]
        if tags and level != "untagged":
            # A page tagged with many unrelated statuses (an overview or a
            # cross-status list) is weaker evidence than one about this status,
            # and one where this status is a passing mention is not evidence.
            dominance = len([c for c in tags if _parent(c) == parent]) / len(tags)
            if not chunk.get("anchor") and (
                dominance < 0.34 or (exact and level == "parent" and dominance < 0.5)
            ):
                continue
            level_score *= 0.4 + 0.6 * dominance
        if not chunk.get("anchor") and level != "exact_subcode":
            heading_codes = [c.upper() for c in _HEADING_CODE_RE.findall(chunk["heading"])]
            if heading_codes and not any(_parent(c) == parent for c in heading_codes):
                continue  # a section about another status that mentions this one
            if exact and level == "parent" and body.count(parent) < 3 and parent not in chunk["heading"]:
                continue  # a passing parent mention says nothing about the sub-code
        bonus = sum(0.4 for t in _PROCEDURE_TERMS.get(procedure, ())[:2] if t in body)
        bonus += min(2.0, sum(0.6 for t in q_terms if t in body))
        chunk["score"] = chunk.get("score", 0.0) + level_score + bonus
        chunk["level"] = level
        chunk["codes"] = codes
        chunk["scope"] = scope
        chunk["procedure"] = procedure
        chunk["text"] = excerpt_text(body, focus=focus)
        if len(chunk["text"]) >= _MIN_EXCERPT_CHARS:  # a bare annex title states nothing
            ranked.append(chunk)

    # A page chosen through its PDF row may also hold page-mapped Markdown
    # chunks the keyword pool did not surface. Bring them in so pick_per_page
    # can prefer them; among several, the one sharing most terms with the
    # question and procedure wins (ties: the longer text).
    pdf_only = sorted({c["page"] for c in ranked if not _is_markdown(c)}
                      - {c["page"] for c in ranked if _is_markdown(c)})
    if pdf_only:
        terms = list(_PROCEDURE_TERMS.get(procedure, ())) + q_terms + [t for t in (exact, parent) if t]
        by_page: Dict[int, Dict[str, Any]] = {}
        for md in _pages(con, scope, pdf_only):
            if not _is_markdown(md):
                continue
            md["text"] = excerpt_text(md["body"], focus=focus)
            if len(md["text"]) < _MIN_EXCERPT_CHARS:
                continue
            md["overlap"] = sum(1 for t in terms if t in md["body"])
            best = by_page.get(md["page"])
            if best is None or (md["overlap"], len(md["text"])) > (best["overlap"], len(best["text"])):
                by_page[md["page"]] = md
        pdf_by_page = {c["page"]: c for c in ranked if not _is_markdown(c)}
        for page, md in by_page.items():
            pdf = pdf_by_page[page]
            level, codes = applicability(md, parent, exact)
            if level == "sibling_subcode":
                continue
            if level == "untagged":  # same page as an accepted PDF row
                level, codes = pdf["level"], pdf["codes"]
            md.update(score=pdf["score"] - 0.01, level=level, codes=codes, scope=scope, procedure=procedure)
            ranked.append(md)
    return pick_per_page(ranked)


def _is_markdown(chunk: Dict[str, Any]) -> bool:
    return str(chunk.get("source_id") or "").endswith("_md")


def pick_per_page(ranked: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """One chunk per manual page, ordered by the page's best score.

    A page can hold the PDF page row and one or more page-mapped Markdown chunks
    (the owner's 2026.9 Markdown texts). The Markdown chunk is preferred — its
    table rows read as "열이름: 값", which matters for document lists — and the
    PDF row is the fallback. Either way the citation is the edition plus the
    chunk's PDF page. Page 0 (not page-mapped) is never evidence.
    """
    groups: Dict[Tuple[str, int], List[Dict[str, Any]]] = {}
    for chunk in ranked:
        if int(chunk.get("page") or 0) <= 0:
            continue
        key = (_registry.derive_family(chunk["source_id"])[0], int(chunk["page"]))
        groups.setdefault(key, []).append(chunk)
    picked: List[Dict[str, Any]] = []
    for chunks in groups.values():
        best_score = max(c.get("score", 0.0) for c in chunks)
        md = [c for c in chunks if _is_markdown(c)]
        pool = md or chunks
        choice = max(pool, key=lambda c: c.get("score", 0.0))
        choice = dict(choice, score=best_score)
        picked.append(choice)
    picked.sort(key=lambda c: (-c["score"], c["page"]))
    return picked


def retrieve_manual_evidence(
    question: str,
    *,
    visa_code: Optional[str] = None,
    visa_sub_code: Optional[str] = None,
    task_type: Optional[str] = None,
    path: Optional[str] = None,
    max_excerpts: int = MAX_EXCERPTS,
    max_chars: int = MAX_TOTAL_CHARS,
) -> Dict[str, Any]:
    """Approved manual excerpts for the question, split by procedure scope.

    Returns ``{"status", "scopes", "codes", "excerpts", "version"}``. ``excerpts``
    are ordered by scope (stay before visa issuance) and then by relevance, and
    each carries its manual, edition, page, applicable codes and applicability
    level. Never raises.
    """
    parent, exact = request_codes(question, visa_code, visa_sub_code)
    scopes = procedure_scopes(question, task_type, has_code=bool(parent))
    result: Dict[str, Any] = {
        "status": STATUS_NOT_ATTEMPTED,
        "scopes": [{"scope": s, "procedure": p} for s, p in scopes],
        "codes": {"parent": parent, "exact_subcode": exact},
        "excerpts": [],
        "version": MANUAL_EVIDENCE_VERSION,
    }
    if not scopes or not parent:
        return result
    con = _connect(path)
    if con is None:
        result["status"] = STATUS_INDEX_UNAVAILABLE
        return result
    try:
        per_scope = [
            _retrieve_scope(con, question, scope, procedure, parent, exact, task_type)
            for scope, procedure in scopes
        ]
    except sqlite3.Error:
        result["status"] = STATUS_INDEX_UNAVAILABLE
        return result
    finally:
        con.close()

    # A parent-code question (E-7, no sub-code asked) whose best page is
    # parent-level does not also get sub-code-only pages (E-7-H, E-7-T): the
    # model read an E-7-H page as an E-7-wide rule despite its label (QA
    # 2026-10-23). When the best page is itself sub-code specific — F-6, whose
    # extension rules exist only per F-6-1/2/3 — the ranking is kept as is.
    if not exact:
        per_scope = [
            [c for c in chunks if c["level"] != "subcode_specific"]
            if chunks and chunks[0]["level"] != "subcode_specific" else chunks
            for chunks in per_scope
        ]

    # Split the budget between scopes; a single scope gets all of it.
    share_n = max(1, max_excerpts // len(per_scope))
    share_chars = max(400, max_chars // len(per_scope))
    chosen: List[Dict[str, Any]] = []
    for chunks in per_scope:
        used = 0
        taken = 0
        for chunk in chunks:
            if taken >= share_n:
                break
            text = chunk["text"]
            if used + len(text) > share_chars:
                room = share_chars - used
                if room < 300:
                    break
                text = excerpt_text(chunk["body"], limit=room, focus=[parent, exact])
                if not text:
                    break
            used += len(text)
            taken += 1
            scope = chunk["scope"]
            version = chunk["manual_version"] or ""
            chosen.append({
                "scope": scope,
                "procedure": chunk["procedure"],
                "manual_title": _SCOPE_TITLE[scope],
                "manual_title_en": _SCOPE_TITLE_EN[scope],
                "manual_version": version,
                "page": chunk["page"],
                "citation": citation_label(scope, version, chunk["page"]),
                "applies_to": list(chunk["codes"]),
                "applicability": chunk["level"],
                "text": text,
                "chunk_id": chunk["chunk_id"],
                "source_id": chunk["source_id"],
                "text_kind": "markdown" if _is_markdown(chunk) else "pdf_text",
            })
    result["excerpts"] = chosen
    result["status"] = STATUS_USED if chosen else STATUS_NO_RESULTS
    return result


# ---------------------------------------------------------------------------
# Consumers: prompt block, source summaries, deterministic note lines
# ---------------------------------------------------------------------------
def _applicability_note(excerpt: Dict[str, Any], parent: str, exact: str) -> str:
    level = excerpt["applicability"]
    codes = ", ".join(excerpt["applies_to"])
    if level == "exact_subcode":
        return f"적용: {codes}"
    if level == "parent":
        if exact:
            return f"적용: {parent} 공통 기준 — {exact}에 그대로 적용되는지는 확인 필요"
        return f"적용: {parent}"
    if level == "subcode_specific":
        return f"적용: {codes} 전용 — {parent} 전체에 적용되는 규칙으로 쓰지 말 것"
    return "적용 자격 표시 없음 — 해당 절차 구간의 원문"


def prompt_block(evidence: Dict[str, Any]) -> str:
    """Prompt-ready excerpt block with the citation and excerpt-only rules."""
    excerpts = (evidence or {}).get("excerpts") or []
    if not excerpts:
        return ""
    codes = (evidence or {}).get("codes") or {}
    parent = codes.get("parent") or ""
    exact = codes.get("exact_subcode") or ""
    scopes = []
    for ex in excerpts:
        label = f"{_SCOPE_LABEL[ex['scope']]}({ex['manual_title']}) — {ex['procedure']}"
        if label not in scopes:
            scopes.append(label)
    lines = [
        "[공식 매뉴얼 발췌 — 승인된 현행 판 원문에서 자동 검색]",
        "- 절차 범위: " + " / ".join(scopes),
        "- 이 발췌는 승인된 매뉴얼 원문에서 질문과 관련 있어 보이는 쪽을 자동으로 고른 것입니다."
        " 사람이 이 질문에 맞춰 검토한 목록은 아닙니다.",
        "",
        "[발췌 사용 규칙 — 아래 답변 품질·문체 지침보다 우선]",
        "- 제출서류, 수수료, 기한, 허가기간, 서식 번호는 아래 발췌에 적힌 것만 쓰십시오.",
        "- 발췌에 없는 서류 이름을 만들거나 일반 지식으로 보태지 마십시오(예: '체류자격 증명서' 같은 이름)."
        " 발췌로 확인되지 않는 항목은 '매뉴얼 발췌에서 확인되지 않음'이라고 쓰고 1345·하이코리아·관할 출입국·외국인관서 확인을 안내하십시오.",
        "- 발췌가 질문과 맞지 않으면 쓰지 말고, 매뉴얼 근거를 찾지 못했다고 말하십시오.",
        "- 각 발췌의 '적용' 표시를 지키십시오. 세부자격 전용 발췌를 상위 자격 전체의 규칙처럼 쓰지 마십시오.",
        "- 사증발급(사증발급 안내매뉴얼) 요건을 체류 절차에 섞지 말고, 체류 절차 요건을 사증발급에 섞지 마십시오.",
        f"- 발췌 내용을 쓴 문단 끝에 자료명과 쪽을 한 번 적으십시오(예: {excerpts[0]['citation']})."
        " 이 인용은 '출처를 본문에 반복하지 말라'는 일반 지침의 예외입니다. 파일명·개정일은 쓰지 마십시오.",
        "- 원문은 PDF에서 추출한 글이라 단어가 겹쳐 보일 수 있습니다(예: '혼인 혼인관계 관계 증명서')."
        " 뜻이 분명할 때만 자연스럽게 옮기고, 불분명하면 인용하지 마십시오.",
        "- 자연스러운 한국어 문체 지침은 표현에만 적용됩니다. 문체를 다듬느라 발췌에 없는 내용을 더하지 마십시오.",
    ]
    current_scope = None
    for i, ex in enumerate(excerpts, 1):
        if ex["scope"] != current_scope:
            current_scope = ex["scope"]
            lines += ["", f"=== {_SCOPE_LABEL[current_scope]} 발췌 ({ex['manual_title']}) ==="]
        lines += [
            "",
            f"[발췌 {i}] {ex['citation']} · {_applicability_note(ex, parent, exact)}",
            ex["text"],
        ]
    return "\n".join(lines)


def source_summaries(evidence: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Source-panel entries, one per excerpt, in the ``grounding_sources`` item shape."""
    out: List[Dict[str, Any]] = []
    for ex in (evidence or {}).get("excerpts") or []:
        first = next((ln for ln in ex["text"].splitlines() if ln.strip() and ln.strip() != "…"), "")
        out.append({
            "source_title": ex["manual_title"],
            "source_title_en": ex["manual_title_en"],
            "source_date": ex["manual_version"],
            "issuing_body": ISSUING_BODY,
            "visa_code": ", ".join(ex["applies_to"]),
            "procedure_type": ex["procedure"],
            "section": first[:80],
            "page_range": str(ex["page"]),
            "citation": ex["citation"],
            "manual_scope": ex["scope"],
            "applies_to": list(ex["applies_to"]),
            "applicability": ex["applicability"],
            "excerpt": ex["text"][:320],
            "text_kind": ex.get("text_kind", ""),
            "source_verification_status": "approved_manual_excerpt",
            "source_confidence": "retrieved_excerpt",
            "evidence_kind": "manual_index_excerpt",
            "reviewed_for_question": False,
        })
    return out


_GATED_PHRASES = ("신고 의무는 없습니다", "반드시 신고해야 합니다", "허용됩니다", "가능합니다",
                  "더 이상 적용되지 않습니다", "no longer apply", "does not apply")


def note_lines(sources: Sequence[Dict[str, Any]], *, is_ko: bool, max_items: int = 4) -> List[str]:
    """Deterministic preparation-note lines from ``source_summaries`` items.

    Manual, edition, page, applicable codes and a short verbatim excerpt. Used
    when no model answer is available, so the note shows where the approved
    manual speaks to the question instead of only generic questions.
    """
    items = [s for s in (sources or []) if isinstance(s, dict) and s.get("page_range")][:max_items]
    if not items:
        return []
    lines: List[str] = []
    if is_ko:
        lines.append("공식 매뉴얼 발췌 (현행 판 원문에서 질문과 관련된 쪽을 자동으로 찾았어요 · 참고용, 신청 전 공식 원문 확인):")
    else:
        lines.append("Official manual excerpts (pages found automatically in the current editions · reference only, confirm with the official source before applying):")
    for src in items:
        text = str(src.get("excerpt") or "")
        snippet = " ".join(ln.strip() for ln in text.splitlines() if ln.strip() and ln.strip() != "…")
        # The preparation note's confidence gate rewrites certainty phrases
        # ("가능합니다" -> "가능 여부를 확인해야 합니다"). Inside a quotation that
        # would misquote the manual, so the snippet stops before them.
        cut = min([i for i in (snippet.find(p) for p in _GATED_PHRASES) if i >= 0] or [len(snippet)])
        if cut < len(snippet):
            snippet = snippet[:cut].rstrip() + "…"
        if len(snippet) > 160:
            snippet = snippet[:159].rstrip() + "…"
        if len(snippet.strip("… ")) < 10:
            snippet = ""
        codes = ", ".join(src.get("applies_to") or [])
        scope_tag = f" [{codes}]" if codes else ""
        if is_ko:
            label = src.get("citation") or f"「{src.get('source_title')} {src.get('source_date')}」 p.{src.get('page_range')}"
        else:
            label = f"{src.get('source_title_en') or src.get('source_title')} {src.get('source_date')}, p.{src.get('page_range')}"
        lines.append(f"* {label}{scope_tag}: {snippet}" if snippet else f"* {label}{scope_tag}")
    if is_ko:
        lines.append("발췌는 원문의 일부입니다. 본인 세부자격에 해당하는 항목인지 확인하고, 최종 제출서류는 관할 관서 안내를 따르세요.")
    else:
        lines.append("Excerpts are partial source text. Check that each applies to your own sub-status; the competent office decides the final documents.")
    return lines


__all__ = [
    "MANUAL_EVIDENCE_VERSION", "SCOPE_STAY", "SCOPE_VISA",
    "STATUS_USED", "STATUS_NO_RESULTS", "STATUS_INDEX_UNAVAILABLE", "STATUS_NOT_ATTEMPTED",
    "procedure_scopes", "request_codes", "applicability", "excerpt_text", "chunk_bodies",
    "retrieve_manual_evidence", "pick_per_page", "prompt_block", "source_summaries", "note_lines",
]
