"""Korean–English article alignment for the legal corpus.

Alignment is established on structured identifiers (lawId + MST +
article number/branch + effective date), never on title similarity.
An English article is only marked as corresponding to a Korean article
when both belong to versions of the *same promulgation* (same
promulgation number / effective date). Matching by article number alone
across different versions is reported as UNVERIFIED, not ALIGNED.

Status vocabulary (corpus-wide):

* ``ALIGNED`` — translation and Korean text are the same version and the
  article exists on both sides.
* ``OLDER_TRANSLATION`` — the newest official translation is older than
  the current Korean version.
* ``PARTIAL`` — a translation of the corresponding version exists but
  covers only some articles.
* ``UNVERIFIED`` — correspondence has not been established.
* ``NOT_AVAILABLE`` — no official translation body is served at all.
"""

from __future__ import annotations

from typing import Any, Dict, List


def align_version(
    *,
    ko_articles: List[Dict[str, Any]],
    en_index: Dict[str, Any],
    ko_promulgation_no: str | None,
    ko_effective_from: str,
) -> Dict[str, Any]:
    """Align one Korean version against one English index.

    ``en_index`` is the output of ``parser.parse_english_law_html`` plus
    provenance fields (``mst``, ``promulgationNo``, ``effectiveFrom``,
    ``sourceUrl``) attached by the caller.
    """
    if not en_index.get("hasContent"):
        return {
            "status": "NOT_AVAILABLE",
            "englishMst": en_index.get("mst"),
            "englishPromulgationNo": en_index.get("promulgationNo"),
            "englishEffectiveFrom": en_index.get("effectiveFrom"),
            "reason": "공식 영문 본문이 제공되지 않음 (헤더만 반환되거나 번역 자체가 없음)",
            "pairs": [],
            "koreanArticleCount": len(ko_articles),
            "englishArticleCount": 0,
        }

    same_version = (
        en_index.get("promulgationNo") is not None
        and ko_promulgation_no is not None
        and str(en_index["promulgationNo"]) == str(ko_promulgation_no)
    )
    en_by_id = {a["articleId"]: a for a in en_index["articles"]}
    ko_ids = {a["articleId"] for a in ko_articles}
    pairs: List[Dict[str, Any]] = []
    for art in ko_articles:
        en = en_by_id.get(art["articleId"])
        if en is None:
            pairs.append(
                {
                    "articleId": art["articleId"],
                    "status": "UNVERIFIED" if not same_version else "PARTIAL",
                    "titleKo": art.get("titleKo"),
                    "titleEn": None,
                    "englishTextSha256": None,
                }
            )
        else:
            pairs.append(
                {
                    "articleId": art["articleId"],
                    "status": "ALIGNED" if same_version else "UNVERIFIED",
                    "titleKo": art.get("titleKo"),
                    "titleEn": en.get("titleEn"),
                    "englishTextSha256": en.get("textSha256"),
                }
            )
    extra_en = sorted(set(en_by_id) - ko_ids)

    if not same_version:
        status = "OLDER_TRANSLATION" if (en_index.get("effectiveFrom") or "") < ko_effective_from else "UNVERIFIED"
    elif len(en_by_id) < len(ko_ids):
        status = "PARTIAL"
    else:
        status = "ALIGNED"

    return {
        "status": status,
        "englishMst": en_index.get("mst"),
        "englishPromulgationNo": en_index.get("promulgationNo"),
        "englishEffectiveFrom": en_index.get("effectiveFrom"),
        "englishSourceUrl": en_index.get("sourceUrl"),
        "samePromulgation": same_version,
        "koreanArticleCount": len(ko_articles),
        "englishArticleCount": len(en_by_id),
        "englishOnlyArticles": extra_en,
        "pairs": pairs,
    }
