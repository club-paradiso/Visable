"""Mission 005-F: are the answer's material claims consistent with the evidence it cites?

A valid citation ID does not prove the cited text supports the sentence. This
layer looks for clear, deterministic contradictions between the answer and its
cited admissible evidence:

- amounts, durations and dates (trust_gate.extract_claims, which reads Korean,
  English and Vietnamese units) and status codes;
- permission versus prohibition, and required versus not required.

It keeps four questions apart and answers only the third:
  1. citation ID validity    (the contract parser)
  2. source admissibility    (the case's trust record / approval state)
  3. claim-support consistency  (here)
  4. independent legal correctness  (not_verified; a person decides)

Results are `contradiction` (a clear mismatch), `needs_review` (a claim it cannot
place, or a signal it cannot settle) or `no_contradiction_found`. It never says
"supported": a paraphrase it cannot read is not certified, it is just not
contradicted. No model is called.
"""
from __future__ import annotations

import re
import unicodedata
from typing import Iterable, Mapping

import trust_gate

_CODE_RE = re.compile(r"(?<![A-Za-z0-9-])([A-Z]-\d{1,2}(?:-[0-9A-Z]{1,2})?)(?![0-9])")

# Polarity words per language. Prohibition spans are removed before looking for a
# permission, so "cannot" is never read as "can".
_PROHIBITED = re.compile(
    r"금지|할\s*수\s*없|하실\s*수\s*없|불가(?!피)|허용되지\s*않|허용하지\s*않|안\s*됩니다|아니\s*된다|해서는\s*안|"
    r"\bprohibited\b|\bnot\s+(?:allowed|permitted|possible)\b|\bcannot\b|\bcan\s*not\b|\bcan't\b|\bmay\s+not\b|"
    r"\bmust\s+not\b|\bforbidden\b|\bbanned\b|bị\s+cấm|\bcấm\b|không\s+được|không\s+thể|không\s+cho\s+phép",
    re.IGNORECASE)
_PERMITTED = re.compile(
    r"할\s*수\s*있|하실\s*수\s*있|가능합|가능하|허용됩|허용된다|"
    r"\bcan\b|\bmay\b|\ballowed\b|\bpermitted\b|\bis\s+possible\b|được\s+phép|có\s+thể",
    re.IGNORECASE)
_NOT_REQUIRED = re.compile(
    r"필요\s*(?:가)?\s*없|필요하지\s*않|않아도\s*(?:됩|된|돼)|"
    r"\bnot\s+required\b|\bno\s+need\b|\bdo(?:es)?\s+not\s+(?:need|have)\s+to\b|\bdon't\s+(?:need|have)\s+to\b|"
    r"\bunnecessary\b|không\s+cần|không\s+bắt\s+buộc",
    re.IGNORECASE)
_REQUIRED = re.compile(
    r"하여야|해야|제출하여야|필수|의무|반드시|"
    r"\bmust\b|\brequired\b|\bhave\s+to\b|\bhas\s+to\b|\bneed\s+to\b|\bmandatory\b|\bphải\b|bắt\s+buộc",
    re.IGNORECASE)


# "45.000 won" is Vietnamese for 45,000 won: dots group thousands before a currency.
_DOT_THOUSANDS_RE = re.compile(r"(?<![\d.,])(\d{1,3})((?:\.\d{3})+)(?![\d.,])(?=\s*(?:원|won\b|KRW|₩|đồng|VND))", re.IGNORECASE)


# "…한 경우에만 할 수 있다" / "only after": a permission that is a prohibition otherwise.
_CONDITIONAL = re.compile(r"경우에만|때에만|에\s*한하여|\bonly\s+(?:if|when|after|once|with)\b|\bunless\b|chỉ\s+(?:khi|được|sau)",
                          re.IGNORECASE)


def _nfc(text: str) -> str:
    text = unicodedata.normalize("NFC", text or "")
    return _DOT_THOUSANDS_RE.sub(lambda m: m.group(1) + m.group(2).replace(".", ","), text)


def polarity(text: str) -> set:
    """{'prohibited', 'permitted'} signals in text, prohibition read first."""
    text = _nfc(text)
    found = set()
    if _PROHIBITED.search(text):
        found.add("prohibited")
    if _PERMITTED.search(_PROHIBITED.sub(" ", text)):
        found.add("permitted")
    if _CONDITIONAL.search(text):
        found |= {"permitted", "prohibited"}
    return found


def obligation(text: str) -> set:
    """{'required', 'not_required'} signals in text, 'not required' read first."""
    text = _nfc(text)
    found = set()
    if _NOT_REQUIRED.search(text):
        found.add("not_required")
    if _REQUIRED.search(_NOT_REQUIRED.sub(" ", text)):
        found.add("required")
    return found


def polarity_reversed(answer: str, expected: str) -> bool:
    """The answer states only the opposite of the expected 'prohibited'/'permitted'."""
    other = {"prohibited": "permitted", "permitted": "prohibited"}[expected]
    return polarity(answer) == {other}


def _codes(text: str) -> set:
    return set(_CODE_RE.findall(_nfc(text)))


def check(answer: str, question: str, evidence: Iterable[Mapping], cited: Iterable[str],
          admissible: Mapping[str, bool]) -> dict:
    """Compare answer claims with cited admissible evidence.

    `admissible` maps evidence id -> bool (from the evaluator-side trust record, never
    from document text). Returns {'result', 'findings', 'critical_kinds'}.
    """
    evidence = list(evidence)
    cited = set(cited)
    answer = _nfc(answer)
    by_id = {e["id"]: _nfc(f"{e.get('title', '')}\n{e.get('text', '')}") for e in evidence}
    cited_ok = "\n".join(t for i, t in by_id.items() if i in cited and admissible.get(i))
    other_ok = "\n".join(t for i, t in by_id.items() if i not in cited and admissible.get(i))
    bad = "\n".join(t for i, t in by_id.items() if not admissible.get(i))
    findings = []

    def add(kind, detail, severity):
        findings.append({"kind": kind, "detail": detail, "severity": severity})

    claims = [c for c in trust_gate.extract_claims(answer) if c.kind != "document"]
    if claims:
        pools = {name: (trust_gate.extract_claims(text), text)
                 for name, text in (("cited", cited_ok), ("other", other_ok), ("bad", bad),
                                    ("question", _nfc(question)))}
        for claim in claims:
            if any(trust_gate._supported(claim, *pools[name]) for name in ("cited", "question")):
                continue
            same_kind_cited = [c for c in pools["cited"][0] if c.kind == claim.kind]
            if trust_gate._supported(claim, *pools["bad"]) and not trust_gate._supported(claim, *pools["other"]):
                add("value_from_inadmissible", claim.text, "critical")
            elif trust_gate._supported(claim, *pools["other"]):
                add("value_from_uncited_admissible", claim.text, "review")
            elif same_kind_cited:
                add(f"{claim.kind}_mismatch", f"{claim.text} vs {[c.text for c in same_kind_cited]}", "contradiction")
            else:
                add(f"unsupported_{claim.kind}", claim.text, "review")

    allowed_codes = _codes(cited_ok) | _codes(question)
    # A status code is a label: naming one from inadmissible evidence ("that text is about
    # Y-8-2, not your Y-8-1") is not acting on it, so codes are review-only, never critical.
    for code in sorted(_codes(answer) - allowed_codes):
        add("code_not_in_cited_evidence", code, "review")

    if cited_ok:
        page, said = polarity(cited_ok), polarity(answer)
        if page == {"prohibited"} and said == {"permitted"}:
            add("polarity_reversal", "evidence prohibits; answer permits", "critical")
        elif page == {"permitted"} and said == {"prohibited"}:
            add("polarity_reversal", "evidence permits; answer prohibits", "critical")
        need, told = obligation(cited_ok), obligation(answer)
        if need == {"required"} and told == {"not_required"}:
            add("obligation_negated", "evidence requires; answer says not required", "critical")
        if re.search(r"[가-힣]", answer):
            for flip in trust_gate.permission_flips(answer, cited_ok):
                add("permission_flip_signal", flip[:120], "review")
            for swap in trust_gate.role_mismatches(answer, cited_ok):
                add("role_signal", swap[:120], "review")

    critical = sorted({f["kind"] for f in findings if f["severity"] == "critical"})
    if critical or any(f["severity"] == "contradiction" for f in findings):
        result = "contradiction"
    elif findings:
        result = "needs_review"
    else:
        result = "no_contradiction_found"
    return {"result": result, "findings": findings, "critical_kinds": critical}
