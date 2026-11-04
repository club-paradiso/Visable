"""Annex 7 (범칙금의 양정기준) extraction and calculator-rule comparison.

Annex 7 of the Enforcement Rule of the Immigration Act is served by
law.go.kr only as a file (HWP/PDF). The official PDF is preserved
verbatim in the corpus; its text layer is extracted with ``pdftotext``
(poppler-utils — the same tool the HiKorea manual workflow installs)
and parsed into structured rows.

Parsing discipline:

* Period-based rows (위반기간) are converted to month tiers.
* Count-based (위반인원) and recurrence-based (위반횟수) rows are kept as
  labelled criteria — they are never mixed into period tiers.
* A row the parser cannot interpret completely is flagged
  ``needsManualReview`` instead of being silently approximated.
* Nothing in this module ever *writes* calculator rules. It only
  produces a comparison report against
  ``backend/data/enforcement/legal_rules.json``; changing a calculator
  amount always requires human approval (see INTEGRATION_PLAN.md).
"""

from __future__ import annotations

import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# File format sniffing (page labels on law.go.kr are unreliable — the same
# flSeq is linked under several format labels; magic bytes do not lie).
# ---------------------------------------------------------------------------


def sniff_format(data: bytes) -> str:
    if data.startswith(b"%PDF"):
        return "pdf"
    if data.startswith(b"\xd0\xcf\x11\xe0"):
        return "hwp"
    if data.startswith(b"PK\x03\x04"):
        return "hwpx-or-zip"
    return "unknown"


def extract_pdf_text(pdf_path: Path) -> str:
    exe = shutil.which("pdftotext")
    if not exe:
        raise RuntimeError("pdftotext (poppler-utils) is required to extract Annex 7 text")
    with tempfile.NamedTemporaryFile("w+", suffix=".txt", delete=False) as tmp:
        tmp_path = tmp.name
    try:
        subprocess.run([exe, "-layout", str(pdf_path), tmp_path], check=True, capture_output=True, timeout=120)
        return Path(tmp_path).read_text(encoding="utf-8", errors="replace")
    finally:
        Path(tmp_path).unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# Structured parsing of the extracted text
# ---------------------------------------------------------------------------

_MOK = re.compile(r"^([가-힣])\.\s*(?:법\s*제(\d+)조(?:제(\d+)항)?(?:제(\d+)호)?|법인)", re.M)
_AMOUNT = re.compile(r"(\d[\d,]*)\s*만원")
_PERIOD_TOKEN = re.compile(r"(\d+)\s*(개월|년)\s*(이상|미만)")
_COUNT_TOKEN = re.compile(r"(\d+)\s*명\s*(이상|이하)?")
_COUNT_RANGE = re.compile(r"(\d+)\s*명\s*이상\s*(\d+)\s*명\s*이하")


def _months(value: int, unit: str) -> int:
    return value * 12 if unit == "년" else value


def parse_period_tiers(segment: str) -> List[Dict[str, Any]]:
    """Parse period tiers from the Annex 7 PDF text layer.

    The official PDF's table layout interleaves columns, so the token
    stream inside one item looks like::

        1개월 미만 200만원  1개월 이상 300만원  3개월 미만
        3개월 이상 400만원  6개월 미만  6개월 이상 700만원 …

    i.e. a tier's upper bound may be printed *after* its amount, just
    before the next tier's lower bound. The state machine below assigns
    a ``미만`` token to the most recent amount's tier when that tier
    still lacks an upper bound, and to the upcoming tier otherwise
    (the first tier's ``1개월 미만`` precedes its amount).
    """
    events: List[tuple] = []
    for tok in _PERIOD_TOKEN.finditer(segment):
        events.append((tok.start(), "period", tok))
    for amt in _AMOUNT.finditer(segment):
        events.append((amt.start(), "amount", amt))
    events.sort(key=lambda e: e[0])

    tiers: List[Dict[str, Any]] = []
    current: Dict[str, Any] = {}
    for _, kind, m in events:
        if kind == "period":
            value = _months(int(m.group(1)), m.group(2))
            if m.group(3) == "이상":
                if "minimumMonths" not in current:
                    current["minimumMonths"] = value
            else:  # 미만
                if not current and tiers and tiers[-1]["maximumMonths"] is None:
                    tiers[-1]["maximumMonths"] = value
                elif "maximumMonths" not in current:
                    current["maximumMonths"] = value
        else:
            if not current:
                continue
            tiers.append(
                {
                    "minimumMonths": current.get("minimumMonths", 0),
                    "maximumMonths": current.get("maximumMonths"),
                    "amountKrw": int(m.group(1).replace(",", "")) * 10000,
                }
            )
            current = {}
    return tiers


def parse_count_tiers(segment: str) -> List[Dict[str, Any]]:
    tiers: List[Dict[str, Any]] = []
    amounts = list(_AMOUNT.finditer(segment))
    cursor = 0
    for amt in amounts:
        window_text = segment[cursor:amt.start()]
        cursor = amt.end()
        m = _COUNT_RANGE.search(window_text)
        c = _COUNT_TOKEN.search(window_text)
        if m:
            criterion = {"minimumPersons": int(m.group(1)), "maximumPersons": int(m.group(2))}
        elif c:
            criterion = {
                "minimumPersons": int(c.group(1)) if c.group(2) != "이하" else None,
                "maximumPersons": int(c.group(1)) if c.group(2) == "이하" else None,
                "label": window_text.strip().split()[-2] if len(window_text.strip().split()) >= 2 else window_text.strip(),
            }
            if c.group(2) is None and int(c.group(1)):
                criterion = {"persons": int(c.group(1))}
        else:
            continue
        tiers.append({**criterion, "amountKrw": int(amt.group(1).replace(",", "")) * 10000})
    return tiers


def parse_recurrence_tiers(segment: str) -> List[Dict[str, Any]]:
    tiers: List[Dict[str, Any]] = []
    for m in re.finditer(r"(\d+)\s*회\s*(이상)?\s*(\d[\d,]*)\s*만원", segment):
        tiers.append(
            {
                "occurrence": int(m.group(1)),
                "orMore": bool(m.group(2)),
                "amountKrw": int(m.group(3).replace(",", "")) * 10000,
            }
        )
    return tiers


# Mok items that the enforcement calculator depends on. Mapping from the
# Annex 7 item to the existing violationCode in legal_rules.json.
CALCULATOR_ITEMS: Dict[str, Dict[str, str]] = {
    "너": {"violationCode": "UNAUTHORIZED_STAY_OR_WORK_ART18_1", "statute": "제18조제1항"},
    "어": {"violationCode": "STATUS_OUTSIDE_ACTIVITY_ART20", "statute": "제20조"},
    "더": {"violationCode": "UNAUTHORIZED_EMPLOYMENT_ART18_2", "statute": "제18조제2항"},
    "저": {"violationCode": "UNAUTHORIZED_WORKPLACE_CHANGE_ART21_1", "statute": "제21조제1항"},
    "고": {"violationCode": "OVERSTAY_ART25", "statute": "제25조"},
}


def parse_annex7_text(text: str) -> Dict[str, Any]:
    """Parse the full Annex 7 text layer into structured criteria."""
    header = re.search(r"\[별표 7\]\s*<개정\s*([\d. ]+)>", text)
    revised = None
    if header:
        parts = [int(x) for x in header.group(1).replace(" ", "").rstrip(".").split(".") if x]
        if len(parts) == 3:
            revised = f"{parts[0]:04d}-{parts[1]:02d}-{parts[2]:02d}"

    general_match = re.search(r"1\.\s*일반기준(.*?)2\.\s*개별기준", text, re.S)
    general = " ".join(general_match.group(1).split()) if general_match else ""

    matches = list(_MOK.finditer(text))
    items: List[Dict[str, Any]] = []
    for idx, m in enumerate(matches):
        start = m.start()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
        segment = text[start:end]
        mok = m.group(1)
        penalty = re.search(r"법\s*제(\d+)조의?(\d*)\s*제(\d+)호", segment)
        penalty_article = None
        if penalty:
            penalty_article = f"제{penalty.group(1)}조" + (f"의{penalty.group(2)}" if penalty.group(2) else "") + f"제{penalty.group(3)}호"
        period_tiers = parse_period_tiers(segment)
        count_tiers = parse_count_tiers(segment)
        recurrence_tiers = parse_recurrence_tiers(segment)
        flat = segment.replace(" ", "").replace("\n", "")
        if ("기준액과" in flat and "같음" in flat) or "양벌규정" in flat or ("범칙금기준액" in flat and "적용" in flat):
            # 예비·음모·미수·교사·방조 (법 제99조) and 양벌규정 (법 제99조의3)
            # items: no independent amount — the criterion *is* the
            # principal offence item's amount, applied by reference.
            basis, tiers = "REFERENCE", []
        elif period_tiers:
            basis, tiers = "PERIOD", period_tiers
        elif count_tiers:
            basis, tiers = "PERSON_COUNT", count_tiers
        elif recurrence_tiers:
            basis, tiers = "RECURRENCE", recurrence_tiers
        else:
            basis, tiers = "UNKNOWN", []
        items.append(
            {
                "item": mok,
                "violatedArticle": (f"제{m.group(2)}조" + (f"제{m.group(3)}항" if m.group(3) else "")) if m.group(2) else None,
                "penaltyArticle": penalty_article,
                "basis": basis,
                "tiers": tiers,
                "rawText": " ".join(segment.split())[:1200],
                "needsManualReview": basis == "UNKNOWN" or (basis not in ("REFERENCE",) and not tiers),
            }
        )
    return {
        "annexNo": "7",
        "titleKo": "범칙금의 양정기준 (제86조제1항 관련)",
        "revisedDate": revised,
        "generalCriteriaKo": general,
        "items": items,
    }


# ---------------------------------------------------------------------------
# Comparison against the existing calculator rules (read-only)
# ---------------------------------------------------------------------------


def compare_with_legal_rules(annex: Dict[str, Any], legal_rules: Dict[str, Any]) -> Dict[str, Any]:
    """Diff Annex-7 period tiers against legal_rules.json snapshots.

    Only period-based tiers are compared with calculator tiers. Amounts
    are never auto-approved: the report is evidence for a human decision.
    """
    annex_by_item = {item["item"]: item for item in annex["items"]}
    comparisons: List[Dict[str, Any]] = []
    for snapshot in legal_rules.get("snapshots", []):
        rules_by_code = {r["violationCode"]: r for r in snapshot.get("rules", [])}
        for mok, link in CALCULATOR_ITEMS.items():
            code = link["violationCode"]
            annex_item = annex_by_item.get(mok)
            rule = rules_by_code.get(code)
            entry: Dict[str, Any] = {
                "snapshotId": snapshot.get("id"),
                "annexItem": mok,
                "violationCode": code,
                "statute": link["statute"],
            }
            if annex_item is None or rule is None:
                entry["status"] = "MISSING_ON_ONE_SIDE"
            elif annex_item["basis"] != "PERIOD":
                entry["status"] = "BASIS_MISMATCH"
            else:
                annex_tiers = [
                    {"minimumMonths": t["minimumMonths"], "maximumMonths": t["maximumMonths"], "amountKrw": t["amountKrw"]}
                    for t in annex_item["tiers"]
                ]
                rule_tiers = [
                    {"minimumMonths": t["minimumMonths"], "maximumMonths": t["maximumMonths"], "amountKrw": t["amountKrw"]}
                    for t in rule.get("tiers", [])
                ]
                entry["status"] = "MATCH" if annex_tiers == rule_tiers else "DIFFER"
                entry["annexTiers"] = annex_tiers
                entry["ruleTiers"] = rule_tiers
            comparisons.append(entry)
    matched = sum(1 for c in comparisons if c["status"] == "MATCH")
    return {
        "annexRevisedDate": annex.get("revisedDate"),
        "comparisons": comparisons,
        "summary": {"total": len(comparisons), "matched": matched, "differ": len(comparisons) - matched},
        "policy": "Differences are reported only. Calculator amounts are never auto-approved or auto-applied.",
    }
