"""Approved-facts ledger, pilot (APPROVED-FACTS-DESIGN.ko.md).

A fact is (subject, role, value) for one amount or period on one page of the
2026-10-19 manuals, tied to an exact quote of that page and the page's approval
hash. This module does the two mechanical ends of the pilot; a person does the
middle, in the review sheet's "사실" tab:

* ``extract`` proposes candidates from the pilot pages (the evidence pages of
  the 140 real-manual cases) with the post-check's own value and role readers,
  plus the nearest status code above the value. Candidates are never used by
  the post-check. Fields the rules cannot settle are left empty.
* ``export`` takes the reviewer's decisions (an ArtifactData export of the
  ``facts_review`` collection) and appends the approved facts to the ledger,
  but only after re-checking that the quote is still on the page, that the
  page text still has the ledger's approval hash, and that the value appears in
  the quote. Anything that fails is reported and not written.

Nothing here is a legal verification: an approved fact says "the manual's page
says this", not that it is right in law.

Usage, from experiments/waymaker-ai/artemis_bootstrap::

    python approved_facts.py extract           # writes the candidate file
    python approved_facts.py check             # exit 1 if the candidate file is stale
    python approved_facts.py export <dir>      # <dir>/facts_review/*.json from ArtifactData
    python approved_facts.py bundle --out <f>  # facts.json for the review sheet's "사실" tab
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import label_v2  # noqa: E402
import manual_ledger  # noqa: E402
import trust_gate  # noqa: E402

CANDIDATES = HERE / "ledgers" / "manual_2026_10_19_fact_candidates.jsonl"
FACTS = HERE / "ledgers" / "manual_2026_10_19_facts.jsonl"

#: The roles a reviewer may choose (design §3). Candidates start from the post-check's
#: role reader; the reviewer refines it.
ROLES: Dict[str, str] = {
    "issue_deadline": "발급 기한", "processing_time": "처리 기간", "filing_deadline": "신청·제출 기한",
    "report_deadline": "신고 기한", "entry_deadline": "입국 기한", "exit_deadline": "출국 기한",
    "pickup_deadline": "수령 기한", "waiting_period": "경과 대기", "validity": "유효기간",
    "stay_per_grant": "1회 체류기간", "stay_cap_total": "총 체류기간 상한", "extension_period": "연장 기간",
    "fee": "수수료", "income_threshold": "소득 기준", "deposit": "예치금·잔고", "insurance": "보험",
    "fine": "과태료", "count_limit": "횟수 상한", "other": "기타(메모에 적기)",
}
#: Post-check role → the reviewer role it most likely is (a starting point only).
_FROM_CHECK = {"issue": "issue_deadline", "process": "processing_time", "apply": "filing_deadline",
               "submit": "filing_deadline", "report": "report_deadline", "entry": "entry_deadline",
               "wait": "waiting_period", "validity": "validity", "stay": "stay_per_grant",
               "extend": "extension_period", "fee": "fee", "income": "income_threshold",
               "deposit": "deposit", "fine": "fine"}
_CODE_RE = re.compile(r"(?<![A-Za-z0-9-])([A-H]-\d{1,2}(?:-[0-9A-Z]{1,2})?)(?![0-9])")
_COMPARATOR_RE = re.compile(r"^\s*(?:원|개월|년|일|주|달)?\s*(이상|이하|이내|미만|초과|까지|동안|간)")
_HOUSEHOLD_RE = re.compile(r"(\d+)\s*인\s*(?:가구|이상)?")
_PER_RE = re.compile(r"1\s*(?:명|인)\s*당|(?<![가-힣])명당|매년|연간|월\s*평균")


def pilot_pages() -> Dict[str, Dict[str, Any]]:
    """Evidence pages of the 140 real-manual cases (label v2), resolved from the page ledger."""
    pages: Dict[str, Dict[str, Any]] = {}
    for set_name in label_v2.SETS:
        cases = json.loads((label_v2.OUT / f"{set_name}_cases.v2.json").read_text(encoding="utf-8"))["cases"]
        for case in manual_ledger.resolve_cases(cases):
            for e in case["evidence"]:
                pages.setdefault(e["id"], e)
    return dict(sorted(pages.items()))


def _quote_and_labels(text: str, clause: str) -> Dict[str, Any]:
    """The exact page substring for a clause. Table clauses are built as "row header cell":
    quote the row line and keep the row and column names as labels."""
    if clause.strip() in text:
        return {"quote": clause.strip(), "row_label": None, "column_label": None}
    row, head, *_ = clause.split(" ", 2) + ["", ""]
    for line in text.splitlines():
        if line.strip().startswith("|") and row and row in line:
            return {"quote": line.strip(), "row_label": row, "column_label": head or None}
    return {"quote": None, "row_label": None, "column_label": None}


def _value(key: tuple) -> Optional[Dict[str, Any]]:
    kind, unit, amount = key
    if kind == "period" and unit == "year" and amount >= 100:   # "2025년 기준" is a calendar year
        return None
    if kind == "money":
        return {"kind": "money", "amount": amount, "unit": unit}
    return {"kind": "period", "amount": amount, "unit": unit}


def _candidate_id(page_id: str, quote: str, value: Mapping[str, Any]) -> str:
    raw = f"{page_id}|{quote}|{value['kind']}|{value['unit']}|{value['amount']}"
    return "fc-" + hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def extract() -> List[Dict[str, Any]]:
    """Candidates for every amount and period on the pilot pages that has a role word,
    and every amount (a fee or threshold without one is still worth a look)."""
    ledger = manual_ledger.load_ledger()
    out: List[Dict[str, Any]] = []
    seen = set()
    for page_id, page in pilot_pages().items():
        text = unicodedata.normalize("NFC", page["text"])
        for key, roles, clause in trust_gate._role_pairs(text):
            value = _value(key)
            if value is None or (not roles and value["kind"] != "money"):
                continue
            where = _quote_and_labels(text, clause)
            if not where["quote"]:
                continue
            cid = _candidate_id(page_id, where["quote"], value)
            if cid in seen:
                continue
            seen.add(cid)
            at = text.find(where["quote"])
            codes = _CODE_RE.findall(text[:max(at, 0)] + where["quote"])
            after = clause[clause.find(str(int(value["amount"]))):] if value["kind"] == "period" else clause
            comparator = _COMPARATOR_RE.search(after[len(str(int(value["amount"]))):]) if value["kind"] == "period" else None
            household = _HOUSEHOLD_RE.search(clause)
            per = _PER_RE.search(clause)
            code = codes[-1] if codes else None
            out.append({
                "candidate_id": cid,
                "status": "candidate",
                "subject": {
                    "status_code": "-".join(code.split("-")[:2]) if code else None,
                    "sub_code": code if code and code.count("-") >= 2 else None,
                    "procedure": "visa" if page["source"]["domain"] == "visa_issuance" else "stay",
                    "qualifiers": {
                        "applicant": "동반가족" if "동반" in clause else "본인" if "본인" in clause else None,
                        "household_size": int(household.group(1)) if household else None,
                        "per": per.group(0) if per else None,
                        "nationality": None,
                        "row_label": where["row_label"], "column_label": where["column_label"],
                    },
                },
                "role": _FROM_CHECK.get(roles[0]) if roles else None,
                "role_from_check": roles[0] if roles else None,
                "value": {**value, "comparator": comparator.group(1) if comparator else None},
                "source": {
                    "page_id": page_id,
                    "page_approval_hash": ledger[page_id]["approved_sha256"],
                    "quote": where["quote"],
                    "quote_sha256": trust_gate.approval_hash(where["quote"]),
                },
                "note": "규칙이 뽑은 후보. 사람이 승인하기 전에는 사후 확인에 쓰지 않는다.",
            })
    return out


def _write_jsonl(path: Path, rows: List[Mapping[str, Any]], header: Mapping[str, Any]) -> None:
    lines = [json.dumps(header, ensure_ascii=False)] + [json.dumps(r, ensure_ascii=False) for r in rows]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def candidate_header(count: int) -> Dict[str, Any]:
    return {"kind": "artemis_fact_candidates", "edition": "2026.10", "pages": "evidence pages of the 140 label-v2 cases",
            "count": count, "meaning": "rule-made candidates; not used by the post-check until a person approves them",
            "roles": ROLES}


def load_candidates(path: Path = CANDIDATES) -> List[Dict[str, Any]]:
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    return [r for r in rows if r.get("candidate_id")]


def check() -> bool:
    """True when the committed candidate file equals a fresh extraction."""
    return CANDIDATES.exists() and load_candidates() == extract()


def _verify(fact: Mapping[str, Any], pages: Mapping[str, Mapping[str, Any]], ledger: Mapping[str, Mapping[str, Any]]) -> List[str]:
    src = fact.get("source") or {}
    page = pages.get(src.get("page_id"))
    problems = []
    if page is None:
        return [f"page {src.get('page_id')} is not a pilot page"]
    text = unicodedata.normalize("NFC", page["text"])
    if trust_gate.approval_hash(page["text"]) != ledger[src["page_id"]]["approved_sha256"]:
        problems.append("page text no longer has the ledger's approval hash")
    if src.get("page_approval_hash") != ledger[src["page_id"]]["approved_sha256"]:
        problems.append("fact names a different page hash than the ledger")
    quote = unicodedata.normalize("NFC", src.get("quote") or "")
    if not quote or quote not in text:
        problems.append("quote is not on the page")
    value = fact.get("value") or {}
    found = trust_gate.extract_claims(quote) + [trust_gate.Claim("money", n, ("money", "krw", v))
                                               for n, v in ((m.group(0), trust_gate._number(m.group("n")))
                                                            for m in trust_gate._BARE_AMOUNT_RE.finditer(quote))]
    if not any(c.key[0] == value.get("kind") and c.key[1] == value.get("unit") and c.key[2] == value.get("amount") for c in found):
        problems.append("value is not in the quote")
    if fact.get("role") not in ROLES:
        problems.append(f"role {fact.get('role')!r} is not in the role list")
    subject = fact.get("subject") or {}
    if subject.get("procedure") not in ("visa", "stay"):
        problems.append("subject.procedure must be visa or stay")
    return problems


def export(review_dir: Path) -> Dict[str, Any]:
    """Append approved reviews to the facts ledger after re-checking each one."""
    pages = pilot_pages()
    ledger = manual_ledger.load_ledger()
    existing = {}
    if FACTS.exists():
        for line in FACTS.read_text(encoding="utf-8").splitlines()[1:]:
            if line.strip():
                row = json.loads(line)
                existing[row["fact_id"]] = row
    written, rejected = [], []
    for path in sorted((review_dir / "facts_review").glob("*.json")):
        doc = json.loads(path.read_text(encoding="utf-8"))
        data = doc.get("data", doc)
        if data.get("decision") not in ("approved", "approved_edited"):
            continue
        fact = {
            "fact_id": data["candidate_id"].replace("fc-", "f-"),
            "status": "approved",
            "subject": data["subject"], "role": data["role"], "value": data["value"], "source": data["source"],
            "review": {"by": data.get("reviewer"), "at": data.get("updated_at"), "edition": "2026.10",
                       "decision": data["decision"], "notes": data.get("note") or ""},
            "supersedes": existing[data["candidate_id"].replace("fc-", "f-")]["fact_id"] if data["candidate_id"].replace("fc-", "f-") in existing else None,
        }
        problems = _verify(fact, pages, ledger)
        if problems:
            rejected.append({"candidate_id": data["candidate_id"], "problems": problems})
            continue
        before = existing.get(fact["fact_id"])
        if before is not None and {k: v for k, v in before.items() if k != "supersedes"} == {k: v for k, v in fact.items() if k != "supersedes"}:
            continue   # same decision exported again
        written.append(fact)
    if written:
        rows = list(existing.values())
        replaced = {f["fact_id"] for f in written}
        rows = [r for r in rows if r["fact_id"] not in replaced] + written
        header = {"kind": "artemis_approved_facts", "edition": "2026.10",
                  "meaning": "facts a person approved against the 2026-10-19 manual page text; not a legal verification",
                  "exported_utc": datetime.now(timezone.utc).isoformat(timespec="seconds")}
        _write_jsonl(FACTS, rows, header)
    return {"written": len(written), "rejected": rejected}


def bundle() -> Dict[str, Any]:
    """What the review sheet's "사실" tab loads: candidates, the role list, and the text of
    every page a candidate quotes."""
    pages = pilot_pages()
    rows = load_candidates()
    used = {r["source"]["page_id"] for r in rows}
    return {"version": "artemis-facts-pilot-1", "edition": "2026.10", "roles": ROLES, "candidates": rows,
            "pages": {pid: {"title": pages[pid]["title"], "text": pages[pid]["text"],
                            "domain": pages[pid]["source"]["domain"]} for pid in sorted(used)}}


def main(argv: Optional[List[str]] = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("command", choices=("extract", "check", "export", "bundle"))
    p.add_argument("review_dir", nargs="?")
    p.add_argument("--out")
    args = p.parse_args(argv)
    if args.command == "extract":
        rows = extract()
        _write_jsonl(CANDIDATES, rows, candidate_header(len(rows)))
        print(json.dumps({"candidates": len(rows)}))
    elif args.command == "bundle":
        if not args.out:
            p.error("bundle needs --out")
        out = Path(args.out)
        out.write_text(json.dumps(bundle(), ensure_ascii=False), encoding="utf-8")
        print(json.dumps({"candidates": len(load_candidates()), "bytes": out.stat().st_size}))
    elif args.command == "check":
        fresh = check()
        print(json.dumps({"fresh": fresh}))
        return 0 if fresh else 1
    else:
        if not args.review_dir:
            p.error("export needs the directory ArtifactData wrote")
        result = export(Path(args.review_dir))
        print(json.dumps(result, ensure_ascii=False, indent=1))
        return 1 if result["rejected"] else 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
