"""Source evidence view for reviewers: the text around a cited location.

Evidence is resolved by REFERENCE at view time, never copied into every fact:

1. the parsed page text of the cited edition in ``data/manual-corpus/<edition>.json``
   (already produced by scripts/build_current_manual_corpus.py) — the window
   around the fact's wording on the cited page(s) is returned; or
2. the verbatim excerpt recorded with the legacy verified grounding
   (``source_excerpt``) for editions without a parsed corpus; or
3. the citation's own stored excerpt (e.g. an AI extraction's evidence).

If none exists the view says so plainly instead of inventing context.
"""
from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional

from .paths import repo_data_path

# Deploy-context aware (Railway Root Directory = backend): services/knowledge/paths.py.
_CORPUS_DIR = repo_data_path("data/manual-corpus", "knowledge_deploy/manual-corpus")
_WINDOW = 360


@lru_cache(maxsize=8)
def _corpus(edition_ref: str) -> Optional[Dict[int, str]]:
    path = _CORPUS_DIR / f"{edition_ref}.json"
    if not re.match(r"^[a-z0-9_]+$", edition_ref or "") or not path.is_file():
        return None
    try:
        return {int(p.get("page") or 0): str(p.get("text") or "") for p in json.loads(path.read_text(encoding="utf-8"))}
    except (OSError, ValueError, TypeError):
        return None


def _window(text: str, needle: str) -> Optional[str]:
    compact_needle = re.sub(r"\s+", "", needle)
    if not compact_needle:
        return None
    # Map positions in a whitespace-free copy back to the original text.
    index, positions = [], []
    for i, ch in enumerate(text):
        if not ch.isspace():
            index.append(ch)
            positions.append(i)
    flat = "".join(index)
    for length in (len(compact_needle), 12, 8):
        probe = compact_needle[:length]
        at = flat.find(probe)
        if at >= 0:
            start = positions[at]
            return text[max(0, start - _WINDOW // 2): start + _WINDOW].strip()
    return None


def evidence_for_fact(repo, fact_id: str) -> Dict[str, Any]:
    fact = repo.get_fact(fact_id)
    items: List[Dict[str, Any]] = []
    legacy = ((repo.get_variant(fact["variant_id"]).get("attributes") or {}).get("legacy_grounding") or {})
    label = re.split(r"[(（]", fact["value_text"])[0]
    for cit in fact["citations"]:
        entry = {"source": f"{cit['source_title']} {cit['version_label']}", "pages": _pages(cit),
                 "section": cit.get("section_title") or "", "locator": cit.get("locator") or "",
                 "kind": "none", "text": "", "match_found": False}
        corpus = _corpus(cit.get("edition_ref") or "")
        if corpus and cit.get("page_start"):
            for page in range(int(cit["page_start"]), int(cit.get("page_end") or cit["page_start"]) + 1):
                window = _window(corpus.get(page, ""), label)
                if window:
                    entry.update(kind="parsed_page_text", text=window, match_found=True, page=page)
                    break
            if entry["kind"] == "none":
                page_text = corpus.get(int(cit["page_start"]), "")
                entry.update(kind="parsed_page_text", text=page_text[:_WINDOW * 2], match_found=False,
                             page=int(cit["page_start"]))
        elif legacy.get("source_excerpt"):
            excerpt = str(legacy["source_excerpt"])
            window = _window(excerpt, label)
            entry.update(kind="legacy_verified_excerpt", text=window or excerpt[:_WINDOW * 2],
                         match_found=bool(window))
        elif cit.get("evidence_excerpt"):
            entry.update(kind="citation_excerpt", text=cit["evidence_excerpt"],
                         match_found=bool(_window(cit["evidence_excerpt"], label)))
        items.append(entry)
    return {"fact_id": fact_id, "value_text": fact["value_text"], "evidence": items}


def _pages(cit: Dict[str, Any]) -> str:
    if not cit.get("page_start"):
        return ""
    end = cit.get("page_end") or cit["page_start"]
    return str(cit["page_start"]) if end == cit["page_start"] else f"{cit['page_start']}-{end}"
