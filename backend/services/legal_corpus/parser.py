"""Parsers for law.go.kr body pages (``lsInfoR.do`` / ``engLsInfoR.do``).

The parsers are deliberately conservative: they only recognise the markup
patterns the National Law Information Center actually serves, and they
preserve the provider's wording verbatim. The single transformation
applied is *whitespace normalisation* — the provider's HTML splits
statute tokens around hyperlinks (``제3조 <a>제1항</a> 을``), which would
otherwise produce text that differs from the official printed statute
(``제3조제1항을``). Only the spacing around Korean particles and
article/paragraph references is re-joined; no word is ever added,
removed or reordered. This is documented in SOURCE_POLICY.md.
"""

from __future__ import annotations

import hashlib
import re
from html.parser import HTMLParser
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# Text normalisation
# ---------------------------------------------------------------------------

_WS = re.compile(r"\s+")
_PARTICLE1 = "을를은는이가의와과로"
_PARTICLE2 = ("으로", "에서", "에게", "부터", "까지", "마다", "조차", "마저", "이나", "라도")


def normalize_statute_text(text: str) -> str:
    """Collapse whitespace and re-join link-split Korean statute tokens."""
    t = _WS.sub(" ", text).strip()
    # "( 제70조" -> "(제70조", "경우 )" -> "경우)"
    t = re.sub(r"\(\s+", "(", t)
    t = re.sub(r"\s+\)", ")", t)
    # "제3조 제1항" -> "제3조제1항", "제1항 및 제2항 에서" handled below.
    t = re.sub(r"(제\d+조(?:의\d+)?)\s+(제?\d+항)", r"\1\2", t)
    t = re.sub(r"(\d+항)\s+(제?\d+호)", r"\1\2", t)
    # Single-character particles split off by link boundaries.
    t = re.sub(rf"([가-힣0-9」』\)])\s+([{_PARTICLE1}])(?=[\s\.,\)]|$)", r"\1\2", t)
    for p in _PARTICLE2:
        t = re.sub(rf"([가-힣0-9」』\)])\s+({p})(?=[\s\.,\)]|$)", r"\1\2", t)
    t = re.sub(r"\s+([,\.])", r"\1", t)
    return t.strip()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Title block
# ---------------------------------------------------------------------------

_TITLE_BLOCK = re.compile(
    r"\[\s*시행\s*(\d{4})\.\s*(\d{1,2})\.\s*(\d{1,2})\.\s*\]\s*"
    r"\[\s*(법률|대통령령|총리령|법무부령|부령|행정안전부령|법무부고시|대통령훈령)\s*제\s*([\d,]+)\s*호,\s*"
    r"(\d{4})\.\s*(\d{1,2})\.\s*(\d{1,2})\.\s*,\s*([^\]]+?)\s*\]"
)


def _iso(y: str, m: str, d: str) -> str:
    return f"{int(y):04d}-{int(m):02d}-{int(d):02d}"


def parse_title_block(text: str) -> Optional[Dict[str, Any]]:
    """Extract promulgation/effective data from ``[시행 ...] [법률 제...호, ...]``."""
    m = _TITLE_BLOCK.search(text)
    if not m:
        return None
    return {
        "effectiveFrom": _iso(m.group(1), m.group(2), m.group(3)),
        "lawKindKo": m.group(4),
        "promulgationNo": m.group(5).replace(",", ""),
        "promulgationDate": _iso(m.group(6), m.group(7), m.group(8)),
        "revisionTypeKo": m.group(9).strip(),
    }


# ---------------------------------------------------------------------------
# Paragraph collector
# ---------------------------------------------------------------------------


class _ParagraphCollector(HTMLParser):
    """Collect ``<p>`` elements with class, text, label and JO metadata."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.paragraphs: List[Dict[str, Any]] = []
        self.region = "body"  # body | addenda | annex
        self._p: Optional[Dict[str, Any]] = None
        self._in_label = False
        self._div_stack: List[str] = []

    def handle_comment(self, data: str) -> None:
        if "별표 서식 시작" in data:
            self.region = "annex"
        elif "별표 서식 끝" in data:
            self.region = "body"

    def handle_starttag(self, tag: str, attrs_list) -> None:
        attrs = dict(attrs_list)
        if tag == "div":
            div_id = attrs.get("id", "")
            self._div_stack.append(div_id)
            if div_id == "arDivArea":
                self.region = "addenda"
        if tag == "p":
            self._p = {
                "class": attrs.get("class", ""),
                "text_parts": [],
                "label_parts": [],
                "jo_value": None,
                "deleted": False,
                "region": self.region,
            }
        elif self._p is not None:
            if tag == "input":
                if attrs.get("name") == "joNoList":
                    self._p["jo_value"] = attrs.get("value", "")
                if attrs.get("id", "").startswith("delJo"):
                    self._p["deleted"] = True
            elif tag == "label":
                self._in_label = True

    def handle_endtag(self, tag: str) -> None:
        if tag == "div" and self._div_stack:
            div_id = self._div_stack.pop()
            if div_id == "arDivArea":
                self.region = "body"
        if tag == "label":
            self._in_label = False
        if tag == "p" and self._p is not None:
            p = self._p
            p["text"] = normalize_statute_text("".join(p.pop("text_parts")))
            p["label"] = normalize_statute_text("".join(p.pop("label_parts")))
            self.paragraphs.append(p)
            self._p = None

    def handle_data(self, data: str) -> None:
        if self._p is not None:
            self._p["text_parts"].append(data)
            if self._in_label:
                self._p["label_parts"].append(data)


_ARTICLE_LABEL = re.compile(r"^제(\d+)조(?:의(\d+))?\s*(?:\(([^)]*)\))?")


def parse_korean_law_html(html: str) -> Dict[str, Any]:
    """Parse a Korean ``lsInfoR.do`` body page into structured articles."""
    collector = _ParagraphCollector()
    collector.feed(html)

    plain = normalize_statute_text(re.sub(r"<[^>]+>", " ", re.sub(r"<script.*?</script>", " ", html, flags=re.S)))
    title_block = parse_title_block(plain)

    articles: List[Dict[str, Any]] = []
    sections: List[Dict[str, Any]] = []
    addenda: List[str] = []
    current: Optional[Dict[str, Any]] = None

    for p in collector.paragraphs:
        if p["region"] == "addenda":
            if p["text"]:
                addenda.append(p["text"])
            continue
        if p["region"] == "annex":
            continue
        cls = p["class"]
        if cls == "gtit":
            heading = p["text"]
            if heading:
                sections.append({"heading": heading, "beforeArticle": current["articleId"] if current else None})
                if current is not None:
                    current.setdefault("trailingSections", []).append(heading)
            continue
        if p["jo_value"] is not None or (cls == "pty1_p4" and _ARTICLE_LABEL.match(p["label"] or p["text"])):
            label = p["label"] or p["text"]
            m = _ARTICLE_LABEL.match(label)
            if not m:
                continue
            number = m.group(1)
            branch = int(m.group(2) or 0)
            article_id = f"{number}-{branch}" if branch else number
            lead = p["text"]
            if label and lead.startswith(label):
                lead = lead[len(label):].strip()
            current = {
                "articleId": article_id,
                "articleNumber": number,
                "branchNumber": branch,
                "titleKo": (m.group(3) or "").strip() or None,
                "deleted": bool(p["deleted"]),
                "paragraphs": [],
            }
            if lead and not p["deleted"]:
                current["paragraphs"].append(lead)
            articles.append(current)
            continue
        if current is not None and p["text"]:
            if p["deleted"] and not current["paragraphs"]:
                current["deleted"] = True
                continue
            current["paragraphs"].append(p["text"])

    for art in articles:
        art["text"] = "\n".join(art["paragraphs"])
        art["textSha256"] = sha256_text(art["text"])

    return {
        "titleBlock": title_block,
        "articles": articles,
        "sections": sections,
        "addenda": addenda,
    }


# ---------------------------------------------------------------------------
# Annex list (별표·서식) extraction from the Rule body page
# ---------------------------------------------------------------------------

_ANNEX_BLOCK = re.compile(r"bylInfoDiv\('(\d+)'\)")
_ANNEX_TITLE = re.compile(r"\[(별표\s*[^\]]+|별지\s*[^\]]+)\]\s*([^<\"]*)")
_ANNEX_FILE = re.compile(r"flDownload\.do\?gubun=&(?:amp;)?(?:flExt=(hwp|hwpx|pdf)&(?:amp;)?)?flSeq=(\d+)&(?:amp;)?bylClsCd=(\d+)")


def parse_annex_list(html: str) -> List[Dict[str, Any]]:
    """Extract the annex/form list (titles + official file sequences)."""
    start = html.find("별표 서식 시작")
    end = html.find("별표 서식 끝")
    if start < 0 or end < 0 or end <= start:
        return []
    segment = html[start:end]
    blocks = _ANNEX_BLOCK.split(segment)
    annexes: List[Dict[str, Any]] = []
    # blocks: [prefix, bylId, blockHtml, bylId, blockHtml, ...]
    for i in range(1, len(blocks) - 1, 2):
        byl_id, block = blocks[i], blocks[i + 1]
        tm = _ANNEX_TITLE.search(block)
        if not tm:
            continue
        title = normalize_statute_text(f"[{tm.group(1)}] {tm.group(2)}")
        # NOTE: the page's own format labels for download anchors are not
        # reliable (the same flSeq is linked from several labels), so only
        # the file sequences are recorded here. The actual format of a
        # downloaded file is determined from its magic bytes at download
        # time (see annex7.sniff_format) — verified 2026-11-04 for Annex 7:
        # flSeq 170813011 is an HWP file and 170813013 is a PDF, although
        # the page markup associates them with several different labels.
        files = []
        seen = set()
        for fm in _ANNEX_FILE.finditer(block):
            fl_seq = fm.group(2)
            if fl_seq in seen:
                continue
            seen.add(fl_seq)
            files.append({"flSeq": fl_seq, "bylClsCd": fm.group(3)})
        annexes.append({"bylId": byl_id, "titleKo": title, "files": files})
    return annexes


# ---------------------------------------------------------------------------
# English body parsing (metadata only — body text is never stored)
# ---------------------------------------------------------------------------

_EN_ARTICLE = re.compile(r"^Article\s+(\d+)(?:-(\d+))?\s*(?:\(([^)]*)\))?", re.I)
_EN_ANCHOR = re.compile(r'<a name="EJ(\d+):(\d+)"')


class _EnglishCollector(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.paragraphs: List[Dict[str, Any]] = []
        self._p: Optional[Dict[str, Any]] = None
        self._in_bl = False
        self._div_stack: List[str] = []

    def _region(self) -> str:
        for div_id in self._div_stack:
            if div_id == "arDivArea" or div_id.startswith("engar"):
                return "addenda"
        return "body"

    def handle_starttag(self, tag: str, attrs_list) -> None:
        attrs = dict(attrs_list)
        if tag == "div":
            self._div_stack.append(attrs.get("id", ""))
        if tag == "p":
            self._p = {
                "class": attrs.get("class", ""),
                "text_parts": [],
                "bl_parts": [],
                "region": self._region(),
            }
        elif self._p is not None and tag == "span" and "bl" in (attrs.get("class") or ""):
            self._in_bl = True

    def handle_endtag(self, tag: str) -> None:
        if tag == "div" and self._div_stack:
            self._div_stack.pop()
        if tag == "span":
            self._in_bl = False
        if tag == "p" and self._p is not None:
            p = self._p
            p["text"] = normalize_statute_text("".join(p.pop("text_parts")))
            p["bl"] = normalize_statute_text("".join(p.pop("bl_parts")))
            self.paragraphs.append(p)
            self._p = None

    def handle_data(self, data: str) -> None:
        if self._p is not None:
            self._p["text_parts"].append(data)
            if self._in_bl:
                self._p["bl_parts"].append(data)


def parse_english_law_html(html: str) -> Dict[str, Any]:
    """Parse an English body page into *alignment metadata only*.

    Returns article numbers, English article titles, paragraph counts and
    per-article SHA-256 of the English text. The English body text itself
    is intentionally discarded — KLRI/ministerial translations may not be
    redistributed (see SOURCE_POLICY.md), so the corpus stores only what
    is needed to verify existence, currency and article-level alignment.
    """
    if not _EN_ANCHOR.search(html):
        return {
            "hasContent": False,
            "articles": [],
            "addendaArticleCount": 0,
            "titleBlock": None,
            "providerNoticeKo": None,
        }

    notice = None
    nm = re.search(r"ㅇ\s*이 영문법령은[^<]+", html)
    if nm:
        notice = normalize_statute_text(nm.group(0))

    plain = normalize_statute_text(re.sub(r"<[^>]+>", " ", re.sub(r"<script.*?</script>", " ", html, flags=re.S)))
    en_block = None
    em = re.search(
        r"\[\s*Enforcement Date\s*([0-9]{1,2})\.?\s*([A-Za-z]+)\.?\s*,?\s*([0-9]{4})\.?\s*\]\s*"
        r"\[\s*([^\]]*?No\.?\s*([\d,]+)[^\]]*)\]",
        plain,
    )
    if em:
        en_block = {"enforcementDateText": em.group(0), "promulgationNo": em.group(5).replace(",", "")}

    collector = _EnglishCollector()
    collector.feed(html)
    articles: List[Dict[str, Any]] = []
    addenda_article_count = 0
    current: Optional[Dict[str, Any]] = None
    for p in collector.paragraphs:
        if p.get("region") == "addenda":
            if p["class"] == "pty11" and p["bl"] and _EN_ARTICLE.match(p["bl"]):
                addenda_article_count += 1
            continue
        if p["class"] == "pty11" and p["bl"]:
            m = _EN_ARTICLE.match(p["bl"])
            if not m:
                continue
            number, branch = m.group(1), int(m.group(2) or 0)
            current = {
                "articleId": f"{number}-{branch}" if branch else number,
                "articleNumber": number,
                "branchNumber": branch,
                "titleEn": (m.group(3) or "").strip() or None,
                "paragraphs": [],
            }
            lead = p["text"]
            if lead.startswith(p["bl"]):
                lead = lead[len(p["bl"]):].strip()
            if lead:
                current["paragraphs"].append(lead)
            articles.append(current)
            continue
        if current is not None and p["text"] and p["class"].startswith("pty11"):
            current["paragraphs"].append(p["text"])

    out = []
    for art in articles:
        text = "\n".join(art["paragraphs"])
        out.append(
            {
                "articleId": art["articleId"],
                "articleNumber": art["articleNumber"],
                "branchNumber": art["branchNumber"],
                "titleEn": art["titleEn"],
                "paragraphCount": len(art["paragraphs"]),
                "textSha256": sha256_text(text),
                "charCount": len(text),
            }
        )
    return {
        "hasContent": bool(out),
        "articles": out,
        "addendaArticleCount": addenda_article_count,
        "titleBlock": en_block,
        "providerNoticeKo": notice,
    }


# ---------------------------------------------------------------------------
# Administrative-rule (고시) body
# ---------------------------------------------------------------------------


def parse_notice_html(html: str) -> Dict[str, Any]:
    """Parse an ``admRulInfoR.do`` page: title block + plain body text."""
    text = re.sub(r"<script.*?</script>", " ", html, flags=re.S)
    text = re.sub(r"<style.*?</style>", " ", text, flags=re.S)
    text = re.sub(r"<br\s*/?>", "\n", text)
    text = re.sub(r"</p>", "\n", text)
    text = re.sub(r"<[^>]+>", " ", text)
    lines = [normalize_statute_text(line) for line in text.split("\n")]
    lines = [line for line in lines if line]
    joined = "\n".join(lines)
    title_block = parse_title_block(joined)
    return {"titleBlock": title_block, "text": joined, "textSha256": sha256_text(joined)}
