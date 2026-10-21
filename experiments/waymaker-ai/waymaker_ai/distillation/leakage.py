"""Train/eval leakage guard: exact duplicates and word 3-gram overlap.

Why this exists: a training example that is a near copy of an evaluation item
turns the benchmark into a memory test. The existing fine-tune scaffold merged
its eval rows into training before re-splitting
(research-notes/knowledge-platform.md §4, defect 2), and training-distill.md
§4.6 asks for dedupe by exact hash *and* n-gram overlap, applied to questions.

Why word 3-grams and not character n-grams: benchmark questions are templated
("D-2 … 체류기간 연장 서류" vs "D-4 … 체류기간 연장 서류"). Two template siblings
share most word 3-grams, while two unrelated questions about the same
procedure share few. Character 3-grams of Korean text overlap heavily for any
two questions on the same topic, which would block every training set.
Status codes stay whole tokens ("E-7-4"), because a hyphen is kept inside a
token.

The guard is deliberately strict: an overlap above the threshold is a refusal,
not a warning. The fix is to re-split by case template (training-distill.md
§4.6), never to raise the threshold.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, FrozenSet, Iterable, List, Mapping, Sequence, Set, Tuple

from waymaker_ai.contracts import compact, normalize_text

#: The evaluation splits a training example must never resemble.
EVAL_SPLITS: Tuple[str, ...] = ("dev", "test", "adversarial_holdout")

DEFAULT_NGRAM = 3
#: Jaccard similarity of word 3-gram sets above which a pair is a leak. Two
#: template siblings that differ in one token typically score 0.5-0.7
#: (INFERRED from the shape of templated questions), so 0.5 catches them.
DEFAULT_MAX_OVERLAP = 0.5

Gram = Tuple[str, ...]


@dataclass(frozen=True)
class TextItem:
    """One text to compare, with the example it came from."""

    example_id: str
    split: str
    text: str


@dataclass(frozen=True)
class Overlap:
    train_id: str
    eval_id: str
    eval_split: str
    score: float           # Jaccard similarity of the gram sets, 1.0 for exact duplicates
    exact: bool            # identical after normalisation

    def describe(self) -> str:
        kind = "exact duplicate" if self.exact else f"3-gram overlap {self.score:.2f}"
        return f"train {self.train_id} ~ {self.eval_split} {self.eval_id}: {kind}"


def tokenize(text: str) -> List[str]:
    """Lower-cased word tokens. Letters, digits and hyphens stay; everything else splits."""
    cleaned: List[str] = []
    for char in normalize_text(text).lower():
        cleaned.append(char if char.isalnum() or char == "-" else " ")
    return [token.strip("-") for token in "".join(cleaned).split() if token.strip("-")]


def word_ngrams(text: str, n: int = DEFAULT_NGRAM) -> FrozenSet[Gram]:
    """Word n-grams of ``text``. A text shorter than n tokens is one gram of all its tokens."""
    tokens = tokenize(text)
    if not tokens:
        return frozenset()
    if len(tokens) < n:
        return frozenset({tuple(tokens)})
    return frozenset(tuple(tokens[i:i + n]) for i in range(len(tokens) - n + 1))


def jaccard(left: FrozenSet[Gram], right: FrozenSet[Gram]) -> float:
    if not left or not right:
        return 0.0
    return len(left & right) / len(left | right)


def example_text(example: Mapping[str, object]) -> str:
    """The text of a benchmark example that a model sees: question plus any claim text."""
    raw_input = example.get("input")
    if not isinstance(raw_input, Mapping):
        return ""
    parts: List[str] = []
    question = raw_input.get("question")
    if isinstance(question, str):
        parts.append(question)
    claim = raw_input.get("claim")
    if isinstance(claim, Mapping):
        for key in ("text", "quoted_text"):
            value = claim.get(key)
            if isinstance(value, str):
                parts.append(value)
    return "\n".join(parts)


def items_from_examples(examples: Iterable[Mapping[str, object]]) -> List[TextItem]:
    return [
        TextItem(example_id=str(example.get("id")), split=str(example.get("split")), text=example_text(example))
        for example in examples
    ]


def find_overlaps(
    train: Sequence[TextItem],
    evaluation: Sequence[TextItem],
    *,
    n: int = DEFAULT_NGRAM,
    max_overlap: float = DEFAULT_MAX_OVERLAP,
) -> List[Overlap]:
    """Every (train, eval) pair that is an exact duplicate or overlaps above ``max_overlap``.

    An inverted index over eval grams keeps this linear in practice: only eval
    items that share at least one gram with a train item are scored.
    """
    eval_grams: List[FrozenSet[Gram]] = [word_ngrams(item.text, n) for item in evaluation]
    eval_exact: Dict[str, List[int]] = defaultdict(list)
    index: Dict[Gram, Set[int]] = defaultdict(set)
    for position, (item, grams) in enumerate(zip(evaluation, eval_grams)):
        eval_exact[compact(item.text).lower()].append(position)
        for gram in grams:
            index[gram].add(position)

    overlaps: List[Overlap] = []
    for item in train:
        grams = word_ngrams(item.text, n)
        key = compact(item.text).lower()
        exact_hits = set(eval_exact.get(key, ())) if key else set()
        candidates: Set[int] = set(exact_hits)
        for gram in grams:
            candidates |= index.get(gram, set())
        for position in sorted(candidates):
            target = evaluation[position]
            exact = position in exact_hits
            score = 1.0 if exact else jaccard(grams, eval_grams[position])
            if exact or score > max_overlap:
                overlaps.append(Overlap(item.example_id, target.example_id, target.split, round(score, 4), exact))
    return overlaps


def duplicate_texts(items: Sequence[TextItem]) -> List[Tuple[str, str]]:
    """Pairs of example ids inside one collection whose texts are identical after normalisation."""
    first_seen: Dict[str, str] = {}
    duplicates: List[Tuple[str, str]] = []
    for item in items:
        key = compact(item.text).lower()
        if not key:
            continue
        if key in first_seen:
            duplicates.append((first_seen[key], item.example_id))
        else:
            first_seen[key] = item.example_id
    return duplicates
