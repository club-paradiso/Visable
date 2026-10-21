"""A readable scanner for Korean statute citations.

Why a scanner and not one regular expression: a citation is a small grammar.
It has an optional law title, then 제N조[의M], then an optional (heading),
제N항 or ①, 제N호[의M] or "N.", and 가목. Annex, form and addendum references
(별표 N의M, 별지 제N호서식, 부칙) have their own shapes. Written as one pattern,
this becomes unreadable and fails silently on the next variant. The scanner
reads one component at a time, so every accepted form is a small named
function that a test exercises.

Title rules (no substitution, spec 07 §2 invariant 3):

* The title before a reference is the LONGEST exact (``compact()``) match
  against ``known_titles``, and it must start at a word boundary. There is no
  generic "anything ending in 법" rule. An unknown title before 제N조 gives
  ``law_title_as_written=None``, so "신가상체류관리법 제3조" never becomes
  "가상체류관리법 제3조".
* A title written inside 「」 is taken as written, because the brackets
  delimit it explicitly. Verification then resolves it exactly or not at all.
* Short forms are resolved relative to ``context_title``: 법 → the Act, 영 → its
  decree, 규칙 → its rule. 같은 법 (동법) / 같은 영 / 같은 규칙 resolve to the most
  recent cited title of that kind, falling back to the context.
* A reference with no title of its own that follows another citation, separated
  only by connectors (",", "및", "또는", "부터", ...), inherits that citation's
  title. "같은 조 제2항" inherits the previous article as well, and so does a
  bare 제N항 / 제N호 after a connector ("제5조제1항 및 제2항" is two citations of
  제5조).

A reference starts at a word boundary, so 부칙 inside "가상부칙장애법" and 제5조
inside "경제5조원" are not references. The one exception is 제N조 written
straight after a title ("가상체류관리법제5조").

``parse_citation_string`` is for a citation that stands alone (an entry of
``ClaimInput.citations``). There, the text before the first reference can only
be the title, so it is taken as written even when it is not a known title.
``parse_citation_strings`` parses several such strings with one title context,
so "같은 법" in the second string refers to the title cited in the first.

Spans index into the NFC-normalized text. For the usual (already NFC) input
they are indexes into the input itself.
"""
from __future__ import annotations

import unicodedata
from dataclasses import dataclass, field, replace
from typing import Iterable, List, Optional, Sequence, Tuple

from waymaker_ai.contracts import Citation, ProvisionRef, compact, normalize_text
from waymaker_ai.legal.identity import act_title_of, decree_title_of, rule_title_of, title_kind

#: ① … ⑳ → 1 … 20
CIRCLED_NUMBERS = {chr(0x2460 + offset): offset + 1 for offset in range(20)}
SUBITEM_LETTERS = "가나다라마바사아자차카타파하"
INTERPUNCTS = "·ㆍ・‧"
INLINE_SPACES = " \t 　"
MAX_NUMBER_DIGITS = 6
#: The printed "N." item form is accepted only for small N, so "① 2026. 9. 15." is not item 2026.
MAX_DOTTED_ITEM = 99

TITLE_OPEN, TITLE_CLOSE = "「", "」"
MAX_BRACKETED_TITLE_CHARS = 80
HEADING_OPEN, HEADING_CLOSE = "(（", ")）"
MAX_HEADING_CHARS = 60
#: Parenthesized text after an article that is not a heading: amendment notes,
#: drafting phrases, and promulgation tags such as "(법률 제123호)".
NOT_HEADING_PREFIXES = (
    "개정", "신설", "삭제", "전문개정", "본조신설", "시행일", "종전", "이하", "단서", "다만",
    "법률 제", "법률제", "대통령령", "총리령", "부령", "법무부령",
)
#: A parenthesis made only of these characters is a cross-reference such as "(제2항)".
REFERENCE_CHARS = frozenset("제조항호의목0123456789①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳")
PROMULGATION_OPEN, PROMULGATION_CLOSE = "<〈(（", ">〉)）"
MAX_PROMULGATION_TAG_CHARS = 60

#: What may separate two references that share one title.
CONNECTORS: Tuple[str, ...] = (
    "그리고", "내지", "또는", "부터", "까지", "및", "와", "과", ",", "、", "·", "~", "∼", "[", "]", "［", "］",
)
#: Skipped when looking backwards from a reference for its title ("[별표 1]").
OPENING_BRACKETS = "[［"
#: Characters a law title can end with (법, 법률, 시행령, 시행규칙, 규정, 고시, 예규,
#: 지침, 조례, 조약). A 제N조 written straight after one of them is still a
#: reference ("가상체류관리법제5조"); after any other letter it is part of a word.
TITLE_FINAL_CHARS = frozenset("법률령칙정시규침례약")

#: (written form, resolution kind). Matched longest first. 동법 is the older
#: spelling of 같은 법 that manuals still print ("동법 시행령 제12조").
SHORT_FORMS: Tuple[Tuple[str, str], ...] = (
    ("같은 법 시행규칙", "same_act_rule"),
    ("같은 법 시행령", "same_act_decree"),
    ("동법 시행규칙", "same_act_rule"),
    ("동법 시행령", "same_act_decree"),
    ("같은 규칙", "same_rule"),
    ("같은 법", "same_act"),
    ("같은 영", "same_decree"),
    ("동법", "same_act"),
    ("규칙", "context_rule"),
    ("법", "context_act"),
    ("영", "context_decree"),
)
SAME_ARTICLE_FORMS = ("같은 조", "같은조")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def parse_citations(
    text: str, *, known_titles: Iterable[str] = (), context_title: Optional[str] = None
) -> List[Citation]:
    """Every citation in free text, in order, with spans."""
    return _scan(text, index=_TitleIndex(known_titles), context=_new_context(context_title), standalone=False)


def parse_citation_string(
    raw: str, *, known_titles: Iterable[str] = (), context_title: Optional[str] = None
) -> List[Citation]:
    """Citations in one standalone citation string, e.g. "가상체류관리법 제5조제1항".

    A string with a title but no provision ("가상체류관리법") yields one citation
    with an empty ``ProvisionRef``. An empty string yields nothing.
    """
    return _parse_standalone(raw, _TitleIndex(known_titles), _new_context(context_title))


def parse_citation_strings(
    raws: Sequence[str], *, known_titles: Iterable[str] = (), context_title: Optional[str] = None
) -> List[Citation]:
    """Several standalone citation strings, sharing one title context, in order."""
    index = _TitleIndex(known_titles)
    context = _new_context(context_title)
    citations: List[Citation] = []
    for raw in raws:
        citations.extend(_parse_standalone(raw, index, context))
    return citations


def provision_ref_from_key(key: Optional[str]) -> Optional[ProvisionRef]:
    """The ProvisionRef a provision key denotes ("제4조제4항", "별표1", "부칙제1조").

    Keys are written without a title, so the scanner reads them as references
    only. Anything that is not exactly one reference gives None.
    """
    if not key:
        return None
    found = _scan(key, index=_TitleIndex(()), context=_new_context(None), standalone=False)
    if len(found) != 1 or found[0].span != (0, len(unicodedata.normalize("NFC", key))):
        return None
    return found[0].provision


def article_key_of(key: Optional[str]) -> Optional[str]:
    """'제4조제4항' → '제4조'. Keys the scanner cannot read are returned without spaces."""
    if not key:
        return None
    ref = provision_ref_from_key(key)
    return ref.article_key() if ref is not None else normalize_text(key).replace(" ", "")


def _parse_standalone(raw: str, index: "_TitleIndex", context: "_TitleContext") -> List[Citation]:
    found = _scan(raw, index=index, context=context, standalone=True)
    if found:
        return found
    title = _clean_title(unicodedata.normalize("NFC", raw or ""))
    if not title:
        return []
    source = unicodedata.normalize("NFC", raw)
    context.seen.append(title)
    return [Citation(raw=normalize_text(source), law_title_as_written=title, provision=ProvisionRef(), span=(0, len(source)))]


# ---------------------------------------------------------------------------
# Scanner
# ---------------------------------------------------------------------------
class _Cursor:
    """A position in the text plus the few primitive reads the grammar needs."""

    def __init__(self, text: str, pos: int) -> None:
        self.text = text
        self.pos = pos

    def peek(self) -> str:
        return self.text[self.pos] if self.pos < len(self.text) else ""

    def skip_spaces(self) -> None:
        while self.pos < len(self.text) and self.text[self.pos] in INLINE_SPACES:
            self.pos += 1

    def take(self, literal: str) -> bool:
        if self.text.startswith(literal, self.pos):
            self.pos += len(literal)
            return True
        return False

    def take_number(self) -> Optional[int]:
        start = self.pos
        while self.pos < len(self.text) and self.text[self.pos].isdecimal():
            self.pos += 1
        digits = self.text[start:self.pos]
        if not digits or len(digits) > MAX_NUMBER_DIGITS:
            self.pos = start
            return None
        return int(digits)


def _read_branch(cur: _Cursor) -> int:
    """'의M' after an article or item number; 0 when absent ('제5조의 규정' is not a branch)."""
    start = cur.pos
    if cur.take("의"):
        number = cur.take_number()
        if number is not None:
            return number
    cur.pos = start
    return 0


def _read_numbered(cur: _Cursor, unit: str, *, branch: bool) -> Optional[Tuple[int, int]]:
    """'제N<unit>' (spaces allowed inside), optionally followed by '의M'."""
    start = cur.pos
    if not cur.take("제"):
        return None
    cur.skip_spaces()
    number = cur.take_number()
    if number is None:
        cur.pos = start
        return None
    cur.skip_spaces()
    if not cur.take(unit):
        cur.pos = start
        return None
    return number, (_read_branch(cur) if branch else 0)


def _looks_like_heading(content: str) -> bool:
    if not content or len(content) > MAX_HEADING_CHARS:
        return False
    if content.startswith(NOT_HEADING_PREFIXES):
        return False
    return not set(compact(content)) <= REFERENCE_CHARS


def _read_heading(cur: _Cursor) -> Optional[str]:
    """'(수수료의 납부방법)' right after an article."""
    start = cur.pos
    cur.skip_spaces()
    opener = cur.peek()
    if not opener or opener not in HEADING_OPEN:
        cur.pos = start
        return None
    close = -1
    for index in range(cur.pos + 1, min(len(cur.text), cur.pos + 2 + MAX_HEADING_CHARS)):
        if cur.text[index] == "\n":
            break
        if cur.text[index] in HEADING_CLOSE:
            close = index
            break
    content = cur.text[cur.pos + 1:close].strip() if close != -1 else ""
    if not _looks_like_heading(content):
        cur.pos = start
        return None
    cur.pos = close + 1
    return normalize_text(content)


def _read_paragraph(cur: _Cursor) -> Optional[int]:
    """'제N항' or a circled number."""
    start = cur.pos
    cur.skip_spaces()
    circled = cur.peek()
    if circled and circled in CIRCLED_NUMBERS:
        cur.pos += 1
        return CIRCLED_NUMBERS[circled]
    numbered = _read_numbered(cur, "항", branch=False)
    if numbered is not None:
        return numbered[0]
    cur.pos = start
    return None


def _read_item(cur: _Cursor, *, after_paragraph: bool) -> Tuple[Optional[int], int]:
    """'제N호[의M]', or the printed 'N.' form directly after a paragraph."""
    start = cur.pos
    cur.skip_spaces()
    numbered = _read_numbered(cur, "호", branch=True)
    if numbered is not None:
        if cur.text.startswith("서식", cur.pos):   # 별지 제N호서식 is a form, not an item
            cur.pos = start
            return None, 0
        return numbered
    if after_paragraph:
        number = cur.take_number()
        if number is not None and number <= MAX_DOTTED_ITEM and cur.take("."):
            following = cur.peek()
            if not following.isdecimal():
                return number, 0
    cur.pos = start
    return None, 0


def _read_subitem(cur: _Cursor) -> Optional[str]:
    """'가목' … '하목'."""
    start = cur.pos
    cur.skip_spaces()
    letter = cur.peek()
    if letter and letter in SUBITEM_LETTERS and cur.text.startswith("목", cur.pos + 1):
        cur.pos += 2
        return letter
    cur.pos = start
    return None


def _read_subdivisions(cur: _Cursor) -> Tuple[Optional[int], Optional[int], int, Optional[str]]:
    paragraph = _read_paragraph(cur)
    item, item_branch = _read_item(cur, after_paragraph=paragraph is not None)
    subitem = _read_subitem(cur) if item is not None else None
    return paragraph, item, item_branch, subitem


def _read_article_chain(cur: _Cursor) -> Optional[Tuple[ProvisionRef, Optional[str]]]:
    """제N조[의M][(heading)][제N항|①][제N호[의M]|N.][가목]."""
    article = _read_numbered(cur, "조", branch=True)
    if article is None:
        return None
    heading = _read_heading(cur)
    paragraph, item, item_branch, subitem = _read_subdivisions(cur)
    ref = ProvisionRef(
        article=article[0], article_branch=article[1], paragraph=paragraph,
        item=item, item_branch=item_branch, subitem=subitem,
    )
    return ref, heading


def _read_annex(cur: _Cursor) -> Optional[ProvisionRef]:
    """'별표 N' / '별표 N의M'."""
    start = cur.pos
    if not cur.take("별표"):
        return None
    cur.skip_spaces()
    number = cur.take_number()
    if number is None:
        cur.pos = start
        return None
    branch = _read_branch(cur)
    return ProvisionRef(annex=f"별표 {number}" + (f"의{branch}" if branch else ""))


def _read_form(cur: _Cursor) -> Optional[ProvisionRef]:
    """'별지 제N호서식' / '별지 제N호의M서식' ('서식' may be omitted)."""
    start = cur.pos
    if not cur.take("별지"):
        return None
    cur.skip_spaces()
    numbered = _read_numbered(cur, "호", branch=True)
    if numbered is None:
        cur.pos = start
        return None
    after_number = cur.pos
    cur.skip_spaces()
    if not cur.take("서식"):
        cur.pos = after_number
    number, branch = numbered
    return ProvisionRef(form=f"별지 제{number}호" + (f"의{branch}" if branch else "") + "서식")


def _skip_promulgation_tag(cur: _Cursor) -> None:
    """'부칙 <법률 제123호, 2020. 1. 1.>' — the tag names the amending act, not a provision."""
    start = cur.pos
    cur.skip_spaces()
    opener = cur.peek()
    if not opener or opener not in PROMULGATION_OPEN:
        cur.pos = start
        return
    limit = min(len(cur.text), cur.pos + 2 + MAX_PROMULGATION_TAG_CHARS)
    for index in range(cur.pos + 1, limit):
        if cur.text[index] in PROMULGATION_CLOSE:
            content = cur.text[cur.pos + 1:index]
            if any(ch.isdecimal() for ch in content):
                cur.pos = index + 1
                return
            break
    cur.pos = start


def _read_addendum(cur: _Cursor) -> Optional[Tuple[ProvisionRef, Optional[str]]]:
    """'부칙', '부칙 제2조', '부칙 <…> 제1조제1항'."""
    if not cur.take("부칙"):
        return None
    _skip_promulgation_tag(cur)
    before_article = cur.pos
    cur.skip_spaces()
    chain = _read_article_chain(cur)
    if chain is None:
        cur.pos = before_article
        return ProvisionRef(addendum=True), None
    ref, heading = chain
    return replace(ref, addendum=True), heading


def _may_start_reference(text: str, pos: int) -> bool:
    """A reference starts at a word boundary, or (제N조 only) right after a title's last letter.

    Without this, "가상부칙장애법" would contain a 부칙 reference and "경제5조원"
    a 제5조 one. "가상체류관리법제5조" is still read, because 법 can end a title.
    """
    if _is_word_boundary(text, pos):
        return True
    return text.startswith("제", pos) and text[pos - 1] in TITLE_FINAL_CHARS


def _read_reference(text: str, pos: int) -> Optional[Tuple[ProvisionRef, Optional[str], int]]:
    """A reference starting exactly at ``pos``: (provision, claimed heading, end)."""
    if not _may_start_reference(text, pos):
        return None
    cur = _Cursor(text, pos)
    heading: Optional[str] = None
    if text.startswith("제", pos):
        chain = _read_article_chain(cur)
        if chain is None:
            return None
        ref, heading = chain
    elif text.startswith("별표", pos):
        annex = _read_annex(cur)
        if annex is None:
            return None
        ref = annex
        closing = cur.peek()
        if pos > 0 and text[pos - 1] in OPENING_BRACKETS and closing and closing in "]］":
            cur.pos += 1   # keep "[별표 1]" whole in the raw text
    elif text.startswith("별지", pos):
        form = _read_form(cur)
        if form is None:
            return None
        ref = form
    elif text.startswith("부칙", pos):
        addendum = _read_addendum(cur)
        if addendum is None:
            return None
        ref, heading = addendum
    else:
        return None
    return ref, heading, cur.pos


# ---------------------------------------------------------------------------
# Titles
# ---------------------------------------------------------------------------
class _TitleIndex:
    """Known titles as compact keys, longest first, matched backwards from a reference."""

    def __init__(self, titles: Iterable[str]) -> None:
        keys = {compact(title) for title in titles if title and compact(title)}
        self.keys = sorted(keys, key=lambda key: (-len(key), key))

    def longest_match(self, text: str, end: int) -> Optional[int]:
        for key in self.keys:
            start = _match_compact_suffix(text, end, key)
            if start is not None and _is_word_boundary(text, start):
                return start
        return None


def _match_compact_suffix(text: str, end: int, key: str) -> Optional[int]:
    """Start index if ``text[:end]`` ends with ``key``, ignoring spaces and interpuncts."""
    index = end
    remaining = len(key)
    while remaining > 0:
        index -= 1
        if index < 0:
            return None
        ch = text[index]
        if ch in INLINE_SPACES or ch in INTERPUNCTS:
            continue
        if ch != key[remaining - 1]:
            return None
        remaining -= 1
    return index


def _is_word_boundary(text: str, start: int) -> bool:
    return start == 0 or not text[start - 1].isalnum()


def _skip_back(text: str, pos: int) -> int:
    while pos > 0 and (text[pos - 1].isspace() or text[pos - 1] in OPENING_BRACKETS):
        pos -= 1
    return pos


def _bracketed_title(text: str, end: int) -> Optional[Tuple[str, int]]:
    """「…」 ending at ``end``: (title as written, index of 「)."""
    if end == 0 or text[end - 1] != TITLE_CLOSE:
        return None
    opening = text.rfind(TITLE_OPEN, 0, end - 1)
    if opening == -1:
        return None
    content = text[opening + 1:end - 1]
    if TITLE_CLOSE in content or "\n" in content or len(content) > MAX_BRACKETED_TITLE_CHARS:
        return None
    title = normalize_text(content)
    return (title, opening) if title else None


def _short_form(text: str, end: int) -> Optional[Tuple[str, int]]:
    """A short form ending at ``end``: (resolution kind, start)."""
    for written, kind in sorted(SHORT_FORMS, key=lambda row: -len(compact(row[0]))):
        start = _match_compact_suffix(text, end, compact(written))
        if start is not None and _is_word_boundary(text, start):
            return kind, start
    return None


@dataclass
class _TitleContext:
    """Resolves short forms from the context title and the titles cited so far."""

    context_title: Optional[str]
    seen: List[str] = field(default_factory=list)

    def _last(self, kind: str) -> Optional[str]:
        for title in reversed(self.seen):
            if title_kind(title) == kind:
                return title
        return None

    def _same_act(self) -> Optional[str]:
        if self._last("act"):
            return self._last("act")
        if self.seen:
            return act_title_of(self.seen[-1])
        return act_title_of(self.context_title) if self.context_title else None

    def resolve(self, kind: str) -> Optional[str]:
        context = self.context_title
        if kind == "context_act":
            return act_title_of(context) if context else None
        if kind == "context_decree":
            return decree_title_of(context) if context else None
        if kind == "context_rule":
            return rule_title_of(context) if context else None
        if kind == "same_act":
            return self._same_act()
        if kind == "same_decree":
            return self._last("decree") or (decree_title_of(context) if context else None)
        if kind == "same_rule":
            return self._last("rule") or (rule_title_of(context) if context else None)
        if kind in ("same_act_decree", "same_act_rule"):
            act = self._same_act()
            if act is None:
                return None
            return decree_title_of(act) if kind == "same_act_decree" else rule_title_of(act)
        raise ValueError(f"unknown short form kind {kind!r}")


def _find_title(text: str, ref_start: int, index: _TitleIndex, context: _TitleContext) -> Tuple[Optional[str], Optional[int]]:
    """(title, start of the title text). A matched but unresolvable short form is (None, start)."""
    end = _skip_back(text, ref_start)
    bracketed = _bracketed_title(text, end)
    if bracketed is not None:
        return bracketed
    start = index.longest_match(text, end)
    if start is not None:
        return normalize_text(text[start:end]), start
    short = _short_form(text, end)
    if short is not None:
        kind, start = short
        return context.resolve(kind), start
    return None, None


def _only_connectors(between: str) -> bool:
    rest = between.strip()
    ordered = sorted(CONNECTORS, key=len, reverse=True)
    changed = True
    while rest and changed:
        changed = False
        for connector in ordered:
            if rest.startswith(connector):
                rest = rest[len(connector):].strip()
                changed = True
                break
    return rest == ""


def _new_context(context_title: Optional[str]) -> "_TitleContext":
    return _TitleContext(context_title=normalize_text(context_title) if context_title else None)


def _clean_title(prefix: str) -> Optional[str]:
    cleaned = prefix.strip().strip("「」[]［］").strip()
    return normalize_text(cleaned) if cleaned else None


def _read_same_article(text: str, pos: int, previous: Sequence[Citation]) -> Optional[Citation]:
    """'같은 조 제2항' → the previous article with a new paragraph/item."""
    if not previous or previous[-1].provision.article is None:
        return None
    for form in SAME_ARTICLE_FORMS:
        if text.startswith(form, pos):
            cur = _Cursor(text, pos + len(form))
            paragraph, item, item_branch, subitem = _read_subdivisions(cur)
            if paragraph is None and item is None:
                return None
            last = previous[-1]
            provision = replace(last.provision, paragraph=paragraph, item=item, item_branch=item_branch, subitem=subitem)
            return Citation(
                raw=text[pos:cur.pos], law_title_as_written=last.law_title_as_written,
                provision=provision, span=(pos, cur.pos),
            )
    return None


def _read_continuation(text: str, pos: int, previous: Sequence[Citation]) -> Optional[Citation]:
    """A bare '제N항' / '제N호' right after a citation and a connector: same article.

    "제5조제1항 및 제2항" cites 제5조제2항; "제5조제1항제1호 및 제2호" keeps 제1항.
    Without a connector in between ("제5조에 따른 제2항의 기간") nothing is inherited.
    """
    if not previous or previous[-1].provision.article is None or not text.startswith("제", pos):
        return None
    last = previous[-1]
    last_end = last.span[1] if last.span else pos
    between = text[last_end:pos]
    if not between.strip() or not _only_connectors(between):
        return None
    cur = _Cursor(text, pos)
    paragraph = _read_paragraph(cur)
    if paragraph is not None:
        item, item_branch = _read_item(cur, after_paragraph=False)
        subitem = _read_subitem(cur) if item is not None else None
        provision = replace(last.provision, paragraph=paragraph, item=item, item_branch=item_branch, subitem=subitem)
    else:
        item, item_branch = _read_item(cur, after_paragraph=False)
        if item is None:
            return None
        subitem = _read_subitem(cur)
        provision = replace(last.provision, item=item, item_branch=item_branch, subitem=subitem)
    return Citation(
        raw=text[pos:cur.pos], law_title_as_written=last.law_title_as_written,
        provision=provision, span=(pos, cur.pos),
    )


def _scan(text: str, *, index: _TitleIndex, context: _TitleContext, standalone: bool) -> List[Citation]:
    source = unicodedata.normalize("NFC", text or "")
    citations: List[Citation] = []
    pos = 0
    while pos < len(source):
        inherited = _read_same_article(source, pos, citations) or _read_continuation(source, pos, citations)
        if inherited is not None:
            citations.append(inherited)
            pos = inherited.span[1] if inherited.span else pos + 1
            continue
        found = _read_reference(source, pos)
        if found is None:
            pos += 1
            continue
        provision, heading, end = found
        title, title_start = _find_title(source, pos, index, context)
        if title is None and title_start is None:
            title, title_start = _fallback_title(source, pos, citations, standalone)
        raw_start = title_start if title_start is not None else pos
        if raw_start == pos and pos > 0 and source[pos - 1] in OPENING_BRACKETS and source[end - 1] in "]］":
            raw_start -= 1   # "[별표 1]" with no title: keep both brackets
        citations.append(Citation(
            raw=source[raw_start:end], law_title_as_written=title, provision=provision,
            claimed_heading=heading, span=(raw_start, end),
        ))
        if title:
            context.seen.append(title)
        pos = end
    return citations


def _fallback_title(
    source: str, ref_start: int, previous: Sequence[Citation], standalone: bool
) -> Tuple[Optional[str], Optional[int]]:
    """Inherit across connectors, or (standalone only) take the leading text as the title."""
    if previous:
        last = previous[-1]
        last_end = last.span[1] if last.span else ref_start
        if _only_connectors(source[last_end:ref_start]):
            return last.law_title_as_written, None
        return None, None
    if standalone:
        prefix = source[:ref_start]
        title = _clean_title(prefix)
        if title:
            return title, len(prefix) - len(prefix.lstrip())
    return None, None
