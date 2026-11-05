"""Credential-free public transport for law.go.kr statute text.

This is the fallback transport for the DRF Open API used by ``law_tools``.
The DRF API requires the OC credential to be registered for the caller's IP /
domain; that registration is not possible from every deployment's egress
addresses (the Vercel serverless path hit exactly this and was fixed in
``lib/enforcement-law-public.js``).  The public law.go.kr web endpoints need
no credential:

  1. discovery — ``GET /법령/<법령명>`` frames the *current* version; the
     framed ``lsInfoP.do`` URL carries its ``lsiSeq`` (MST) and ``efYd``.
  2. body — ``GET /LSW/lsInfoR.do?lsiSeq=<MST>&efYd=<YYYYMMDD>`` serves the
     full official text, parsed with the legal-corpus parser rules already
     used by the corpus sync pipeline (``legal_corpus.parser``).

DRF stays primary wherever it answers.  This module is only consulted after
a DRF infrastructure failure (official/auth error, HTTP error, timeout, bad
response, parse error) or an authoritative-looking empty result, so a broken
registration can no longer zero out Q&A law grounding.  Nothing here invents
content: a law is only returned when its official body was actually fetched
and parsed, and only successful lookups are cached (1 h, in-process).

Scope: current-version statutes / decrees / rules by exact law name.  There
is no public keyword search equivalent, so free-text queries are resolved to
candidate law names first (see ``law_name_candidates``).
"""

from __future__ import annotations

import re
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Callable, Dict, List, Optional, Tuple

BASE = "https://www.law.go.kr"
USER_AGENT = "VisableLawPublic/1.0 (+https://github.com/club-paradiso/Visable)"

# Same discovery pattern as services.legal_corpus.client and the JS public
# transport (lib/enforcement-law-public.js): the current-version iframe URL.
_DISCOVERY_RE = re.compile(r"lsInfoP\.do\?lsiSeq=(\d+)&[^\"']*efYd=(\d{8})")

_CACHE_TTL_SECONDS = 3600.0
_cache: Dict[str, Tuple[float, Any]] = {}

# (url, timeout_seconds) -> (http_status, body_text).  Status 0 means the
# request never completed (network/timeout); callers treat it as failure.
PublicFetch = Callable[[str, float], Tuple[int, str]]


def _default_fetch(url: str, timeout: float) -> Tuple[int, str]:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return int(resp.status), resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as exc:
        try:
            return int(exc.code), exc.read().decode("utf-8", "replace")
        except Exception:
            return int(exc.code), ""
    except Exception:
        return 0, ""


def _cache_get(key: str) -> Optional[Any]:
    entry = _cache.get(key)
    if entry is None:
        return None
    stored_at, value = entry
    if time.time() - stored_at > _CACHE_TTL_SECONDS:
        _cache.pop(key, None)
        return None
    return value


def _cache_put(key: str, value: Any) -> None:
    _cache[key] = (time.time(), value)


def reset_public_cache_for_tests() -> None:
    _cache.clear()


def public_law_url(law_name: str) -> str:
    """Secret-free public page URL for a law (safe to expose as source_url)."""
    return f"{BASE}/" + urllib.parse.quote(f"법령/{law_name}")


def fetch_public_page(
    url: str,
    *,
    fetch: Optional[PublicFetch] = None,
    timeout: float = 20.0,
) -> Tuple[int, str]:
    """Fetch one public law.go.kr page through the shared public seam.

    Used by the precedent detail fallback (``precInfoR.do``) so every public
    request shares the same user agent, error contract and test seam.
    """
    send = fetch or _default_fetch
    return send(url, timeout)


def discover_current(
    law_name: str,
    *,
    fetch: Optional[PublicFetch] = None,
    timeout: float = 20.0,
) -> Optional[Tuple[str, str]]:
    """Return ``(lsi_seq, ef_yd)`` for the current version of ``law_name``.

    ``None`` on any failure (unknown name, HTTP error, changed page shape) —
    a failed discovery is never cached.
    """
    name = (law_name or "").strip()
    if not name:
        return None
    cache_key = f"discover:{name}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached
    send = fetch or _default_fetch
    status, text = send(public_law_url(name), timeout)
    if status != 200 or not text:
        return None
    match = _DISCOVERY_RE.search(text)
    if not match:
        return None
    found = (match.group(1), match.group(2))
    _cache_put(cache_key, found)
    return found


def _article_label(article_number: Any, branch_number: Any) -> str:
    try:
        number = int(article_number)
    except (TypeError, ValueError):
        return str(article_number or "")
    try:
        branch = int(branch_number or 0)
    except (TypeError, ValueError):
        branch = 0
    return f"제{number}조" + (f"의{branch}" if branch else "")


def _convert_articles(parsed: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Map corpus-parser articles to the ``law_tools._extract_articles`` shape."""
    articles: List[Dict[str, Any]] = []
    for art in parsed.get("articles") or []:
        if not isinstance(art, dict) or art.get("deleted"):
            continue
        number = art.get("articleNumber")
        branch = art.get("branchNumber") or 0
        text = " ".join(str(art.get("text") or "").split())
        if not text:
            continue
        articles.append({
            "article_no": str(number),
            "article_label": _article_label(number, branch),
            "article_title": str(art.get("titleKo") or "")[:200],
            "text": text[:600],
        })
    return articles


def fetch_law_document(
    law_name: str,
    *,
    fetch: Optional[PublicFetch] = None,
    timeout: float = 30.0,
) -> Optional[Dict[str, Any]]:
    """Fetch + parse the current official body for ``law_name``.

    Returns ``{law_name, law_serial_no, enforcement_date, articles,
    source_url}`` or ``None`` when the law cannot be discovered or its body
    does not parse into at least one article.  Only successes are cached.
    """
    name = (law_name or "").strip()
    if not name:
        return None
    cache_key = f"doc:{name}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached
    discovered = discover_current(name, fetch=fetch, timeout=min(timeout, 20.0))
    if discovered is None:
        return None
    lsi_seq, ef_yd = discovered
    send = fetch or _default_fetch
    body_url = f"{BASE}/LSW/lsInfoR.do?lsiSeq={lsi_seq}&efYd={ef_yd}&ancYnChk=0"
    status, html = send(body_url, timeout)
    if status != 200 or not html:
        return None
    from .legal_corpus.parser import parse_korean_law_html

    try:
        parsed = parse_korean_law_html(html)
    except Exception:
        return None
    articles = _convert_articles(parsed)
    if not articles:
        return None
    # Discovery succeeded by exact official name, so the requested name is
    # the official one; the body parse confirms content, not the name.
    document = {
        "law_name": name,
        "law_serial_no": lsi_seq,
        "enforcement_date": ef_yd,
        "articles": articles,
        "source_url": public_law_url(name),
    }
    _cache_put(cache_key, document)
    return document


_LAW_NAME_SUFFIXES = ("법률", "법", "시행령", "시행규칙", "규칙", "고시", "훈령", "예규", "조례")


def law_name_candidates(query: str, *, max_candidates: int = 4) -> List[str]:
    """Resolve a search query to candidate exact law names, best first.

    Planner queries are shaped ``"<법령명> <주제어...>"``, so token prefixes
    are tried longest-first (``출입국관리법 시행령`` before ``출입국관리법``);
    a bare query that already looks like a law name is tried as-is.
    """
    q = " ".join(str(query or "").split())
    if not q:
        return []
    candidates: List[str] = []

    def add(value: str) -> None:
        value = value.strip()
        if value and value not in candidates and len(value) <= 60:
            candidates.append(value)

    tokens = q.split(" ")
    if len(tokens) == 1:
        add(q)
    else:
        for k in range(min(3, len(tokens) - 1), 0, -1):
            prefix = " ".join(tokens[:k])
            if prefix.endswith(_LAW_NAME_SUFFIXES) or k == 1:
                add(prefix)
        add(q)
    return candidates[:max_candidates]


def _row_from_document(document: Dict[str, Any], *, query: str) -> Dict[str, Any]:
    articles = document.get("articles") or []
    first = articles[0] if articles else {}
    summary = ""
    if first:
        head = first.get("article_label") or ""
        title = first.get("article_title") or ""
        head = f"{head}({title})" if title else head
        summary = f"{head} {first.get('text') or ''}".strip()[:700]
    name = document["law_name"]
    return {
        "source_type": "law",
        "title": name,
        "law_name": name,
        "law_id": document["law_serial_no"],
        "law_serial_no": document["law_serial_no"],
        "reference": document["law_serial_no"],
        "article": "",
        "case_name": "",
        "case_number": "",
        "decision_date": "",
        "summary": summary,
        "law_division": "",
        "promulgation_date": "",
        "enforcement_date": document.get("enforcement_date") or "",
        # Discovery resolves through the official current-version pointer,
        # so the returned version is the in-force one.
        "law_status_code": "현행",
        "department": "",
        "retrieval_status": "ok",
        "relevance": "primary",
        "source_url": document["source_url"],
        "query": query,
        "transport": "public",
    }


def search_law_rows(
    query: str,
    *,
    limit: int = 5,
    fetch: Optional[PublicFetch] = None,
    timeout: float = 30.0,
) -> List[Dict[str, Any]]:
    """Public-transport statute search: at most one law, resolved by name.

    The public site offers no keyword search, so this returns the single law
    whose exact name the query resolves to (with its body actually fetched),
    or an empty list.  Rows use the ``law_tools`` normalized-candidate shape.
    """
    for candidate in law_name_candidates(query):
        document = fetch_law_document(candidate, fetch=fetch, timeout=timeout)
        if document is not None:
            return [_row_from_document(document, query=query)][: max(1, limit)]
    return []


def _article_matches(article: Dict[str, Any], article_filter: str) -> bool:
    wanted = " ".join(str(article_filter or "").split())
    if not wanted:
        return True
    label = str(article.get("article_label") or "")
    if wanted == label:
        return True
    wanted_match = re.search(r"(\d+)\s*조(?:\s*의\s*(\d+))?", wanted)
    if not wanted_match:
        return False
    wanted_label = f"제{int(wanted_match.group(1))}조" + (
        f"의{int(wanted_match.group(2))}" if wanted_match.group(2) else ""
    )
    return wanted_label == label


def detail_for_law(
    law_name: str,
    article: str = "",
    *,
    fetch: Optional[PublicFetch] = None,
    timeout: float = 30.0,
) -> Optional[Dict[str, Any]]:
    """Public-transport law detail: ``{detail, articles}`` or ``None``.

    ``articles`` follows the same filter/cap semantics as
    ``law_tools._extract_articles`` (only the requested article when a filter
    is given, at most 10 entries).
    """
    document = fetch_law_document(law_name, fetch=fetch, timeout=timeout)
    if document is None:
        return None
    row = _row_from_document(document, query=law_name)
    articles = [
        art for art in (document.get("articles") or [])
        if _article_matches(art, article)
    ][:10]
    return {"detail": row, "articles": articles}
