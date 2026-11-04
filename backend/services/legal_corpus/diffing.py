"""Article-level diff between two versions of the same law."""

from __future__ import annotations

from typing import Any, Dict, List


def diff_articles(old: List[Dict[str, Any]], new: List[Dict[str, Any]]) -> Dict[str, Any]:
    old_by_id = {a["articleId"]: a for a in old}
    new_by_id = {a["articleId"]: a for a in new}
    added = sorted(set(new_by_id) - set(old_by_id))
    removed = sorted(set(old_by_id) - set(new_by_id))
    modified: List[Dict[str, Any]] = []
    unchanged = 0
    for art_id in sorted(set(old_by_id) & set(new_by_id)):
        o, n = old_by_id[art_id], new_by_id[art_id]
        if o.get("textSha256") != n.get("textSha256") or o.get("titleKo") != n.get("titleKo") or o.get("deleted") != n.get("deleted"):
            modified.append(
                {
                    "articleId": art_id,
                    "titleKo": n.get("titleKo"),
                    "oldSha256": o.get("textSha256"),
                    "newSha256": n.get("textSha256"),
                    "oldDeleted": bool(o.get("deleted")),
                    "newDeleted": bool(n.get("deleted")),
                }
            )
        else:
            unchanged += 1
    return {
        "addedArticles": added,
        "removedArticles": removed,
        "modifiedArticles": modified,
        "unchangedCount": unchanged,
    }
