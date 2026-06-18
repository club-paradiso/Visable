#!/usr/bin/env python3
from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SOURCE_FILES = {
    "stay": ROOT / "docs/source-manuals/2026-06-17/extracted/full_text/stay_manual_260617.txt",
    "visa": ROOT / "docs/source-manuals/2026-06-17/extracted/full_text/visa_issue_manual_260617.txt",
}
STATUSES_DIR = ROOT / "backend/data/visa_authoring/statuses"
OUTPUT = ROOT / "docs/data/2026_06_17_manual_code_inventory.json"

CODE_RE = re.compile(r"\b[A-H]-\d{1,2}(?:-[0-9A-Z]+)?\b|\bK-STAR\b")
PAGE_RE = re.compile(r"^===== (?P<title>.*?) / PDF page (?P<page>\d+) of (?P<total>\d+) =====$")
REFERENCE_WORDS = ("참조", "해당", "배우자", "동반", "예시", "예)", "등)")
ABOLISHED_WORDS = ("폐지", "폐지된", "발급되지 않습니다", "abolished")
DEPRECATED_WORDS = ("한시", "정상화", "deprecated")
MULTIPLE_ENTRY_WORDS = ("복수사증", "복수비자", "multiple")
SPECIAL_SUFFIX_RE = re.compile(r"-(?:T|S\d*|R|H|Y|[0-9]+[A-Z]+)$")
TOP_TIER_CODES = {"D-10-T", "E-7-T", "F-2-T", "F-5-T"}
POLICY_OR_MULTIPLE_ENTRY_CODES = {"C-3-91"}


def load_json(path: Path) -> dict:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def normalize_ws(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def parent_code(code: str) -> str:
    if code == "K-STAR":
        return "K-STAR"
    first, second, *_ = code.split("-")
    return f"{first}-{second}"


def code_sort_key(code: str) -> tuple:
    if code == "K-STAR":
        return ("Z", 999, "", 999, "", code)
    parts = code.split("-")
    letter = parts[0]
    parsed = []
    for part in parts[1:3]:
        match = re.match(r"(\d+)(.*)", part)
        if match:
            parsed.append((int(match.group(1)), match.group(2)))
        else:
            parsed.append((999, part))
    while len(parsed) < 2:
        parsed.append((-1, ""))
    return (letter, parsed[0][0], parsed[0][1], parsed[1][0], parsed[1][1], code)


def load_authoring_index() -> tuple[dict, dict, set]:
    status_files = {}
    subcodes = {}
    searchable_codes = set()
    for path in sorted(STATUSES_DIR.glob("*.json")):
        data = load_json(path)
        code = data["code"]
        status_files[code] = {"file": str(path.relative_to(ROOT)), "data": data}
        searchable_codes.add(code)
        for subcode in data.get("subcodes") or []:
            subcode_code = subcode.get("code")
            if not subcode_code:
                continue
            subcodes.setdefault(subcode_code, []).append(
                {
                    "parentCode": code,
                    "file": str(path.relative_to(ROOT)),
                    "status": subcode.get("status", "active"),
                    "needsManualReview": subcode.get("needsManualReview", False),
                    "manualRefs": subcode.get("manualRefs") or [],
                    "nameKo": subcode.get("nameKo") or subcode.get("name") or "",
                    "searchAliases": subcode.get("searchAliases") or [],
                }
            )
            searchable_codes.add(subcode_code)
            searchable_codes.update(subcode.get("searchAliases") or [])
    return status_files, subcodes, searchable_codes


def iter_pages(manual: str, path: Path):
    if not path.exists():
        raise SystemExit(f"missing manual text file: {path}")

    current = {
        "manual": manual,
        "path": str(path.relative_to(ROOT)),
        "page": None,
        "title": "",
        "lines": [],
        "startLine": 1,
    }

    for line_no, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        marker = PAGE_RE.match(raw)
        if marker:
            if current["page"] is not None:
                yield current
            current = {
                "manual": manual,
                "path": str(path.relative_to(ROOT)),
                "page": int(marker.group("page")),
                "title": marker.group("title"),
                "lines": [raw],
                "startLine": line_no,
            }
            continue
        current["lines"].append(raw)

    if current["page"] is not None:
        yield current


def nearby_section(lines: list[str], index: int) -> str:
    for candidate in reversed(lines[max(0, index - 12) : index + 1]):
        text = normalize_ws(candidate)
        if not text or text.startswith("=====") or text in {"-", "--"}:
            continue
        if len(text) <= 120 and (
            CODE_RE.search(text)
            or text.startswith(("□", "○", "❍", "Ⅰ", "Ⅱ", "Ⅲ", "Ⅳ", "Ⅴ"))
            or re.match(r"^\d+[.)]\s*", text)
            or re.match(r"^[가-하][.)]\s*", text)
        ):
            return text
    return ""


def nearby_name(lines: list[str], index: int, code: str) -> str:
    window = lines[max(0, index - 1) : min(len(lines), index + 3)]
    for raw in window:
        text = normalize_ws(raw)
        if not text:
            continue
        cleaned = normalize_ws(CODE_RE.sub("", text))
        cleaned = cleaned.strip("()[]{}:-/·,， ")
        if cleaned and cleaned != text and len(cleaned) <= 80:
            return cleaned
    for raw in window:
        text = normalize_ws(raw)
        if text and code not in text and len(text) <= 80 and not PAGE_RE.match(text):
            return text
    return ""


def context_for(lines: list[str], index: int) -> str:
    return normalize_ws("\n".join(lines[max(0, index - 2) : min(len(lines), index + 3)]))[:700]


def has_direct_abolished_signal(code: str, refs: list[dict]) -> bool:
    for ref in refs:
        context = ref["context"]
        for match in re.finditer(re.escape(code), context):
            tail = context[match.end() : match.end() + 140]
            word_positions = [tail.find(word) for word in ABOLISHED_WORDS if word in tail]
            word_positions = [pos for pos in word_positions if pos >= 0]
            if not word_positions:
                continue
            first_word_pos = min(word_positions)
            between = tail[:first_word_pos]
            if not CODE_RE.search(between):
                return True
    return False


def collect_occurrences() -> dict[str, list[dict]]:
    occurrences = defaultdict(list)
    for manual, path in SOURCE_FILES.items():
        for page in iter_pages(manual, path):
            lines = page["lines"]
            for idx, line in enumerate(lines):
                for match in CODE_RE.finditer(line):
                    code = match.group(0)
                    occurrences[code].append(
                        {
                            "manual": manual,
                            "path": page["path"],
                            "page": page["page"],
                            "section": nearby_section(lines, idx),
                            "line": page["startLine"] + idx,
                            "context": context_for(lines, idx),
                            "nameCandidate": nearby_name(lines, idx, code),
                        }
                    )
    return occurrences


def classify(code: str, refs: list[dict], status_files: dict, subcodes: dict) -> tuple[str, str, bool, bool, str]:
    manuals = {ref["manual"] for ref in refs}
    combined_context = " ".join(ref["context"] for ref in refs[:20])
    authoring_entries = subcodes.get(code, [])
    status_values = {entry.get("status", "active") for entry in authoring_entries}

    if code in status_files and not authoring_entries and code != "K-STAR":
        return (
            "parent_status",
            "active",
            False,
            True,
            "Code matches a canonical parent status file.",
        )

    is_abolished = has_direct_abolished_signal(code, refs)

    if is_abolished:
        return (
            "abolished_subcode",
            "abolished",
            False,
            True,
            "Manual context contains abolition/폐지 language.",
        )

    if any(status in {"deprecated", "abolished"} for status in status_values):
        classification = "abolished_subcode" if "abolished" in status_values else "deprecated_subcode"
        status = "abolished" if classification == "abolished_subcode" else "deprecated"
        return (
            classification,
            status,
            False,
            True,
            "Current authoring marks this code as deprecated or abolished.",
        )

    if code in POLICY_OR_MULTIPLE_ENTRY_CODES:
        return (
            "policy_or_multiple_entry_code",
            "active",
            False,
            True,
            "Code appears in multiple-entry/policy context rather than a normal canonical subcode table.",
        )

    if code == "K-STAR" or code in TOP_TIER_CODES or SPECIAL_SUFFIX_RE.search(code):
        return (
            "special_track",
            "active" if authoring_entries or code in status_files else "unknown",
            bool(authoring_entries or code in status_files),
            True,
            "Code uses a recognized special-track suffix or K-STAR/Top-Tier naming.",
        )

    if authoring_entries:
        return (
            "active_subcode",
            "active",
            True,
            True,
            "Code is already represented in canonical authoring subcodes.",
        )

    if any(word in combined_context for word in MULTIPLE_ENTRY_WORDS):
        return (
            "policy_or_multiple_entry_code",
            "active" if authoring_entries else "unknown",
            False,
            True,
            "Code appears in multiple-entry/policy context rather than a normal canonical subcode table.",
        )

    if manuals == {"visa"}:
        return (
            "visa_only",
            "unknown",
            False,
            True,
            "Code appears only in the visa issuance manual and is not yet represented in authoring data.",
        )

    if manuals == {"stay"}:
        return (
            "stay_only",
            "unknown",
            False,
            True,
            "Code appears only in the stay/residence manual and is not yet represented in authoring data.",
        )

    if any(word in combined_context for word in REFERENCE_WORDS):
        return (
            "manual_reference_only",
            "unknown",
            False,
            True,
            "Code appears in reference/cross-reference context and is not represented as authoring subcode.",
        )

    return (
        "needs_human_review",
        "unknown",
        False,
        True,
        "Manual occurrence could not be safely classified by deterministic rules.",
    )


def main() -> int:
    status_files, subcodes, searchable_codes = load_authoring_index()
    occurrences = collect_occurrences()

    items = []
    for code in sorted(occurrences, key=code_sort_key):
        refs = occurrences[code]
        classification, status, should_be_canonical, should_be_searchable, notes = classify(
            code, refs, status_files, subcodes
        )
        source_manuals = sorted({ref["manual"] for ref in refs})
        pages_by_manual = {
            manual: sorted({ref["page"] for ref in refs if ref["manual"] == manual})
            for manual in source_manuals
        }
        source_refs = []
        seen_ref_keys = set()
        for ref in refs:
            key = (ref["manual"], ref["page"], ref["section"], ref["context"])
            if key in seen_ref_keys:
                continue
            seen_ref_keys.add(key)
            source_refs.append(
                {
                    "manual": ref["manual"],
                    "path": ref["path"],
                    "page": ref["page"],
                    "section": ref["section"],
                    "line": ref["line"],
                    "context": ref["context"],
                }
            )
            if len(source_refs) >= 12:
                break

        authoring_entries = subcodes.get(code, [])
        name_ko = ""
        if authoring_entries:
            name_ko = authoring_entries[0].get("nameKo") or ""
        if not name_ko:
            name_ko = next((ref.get("nameCandidate") or "" for ref in refs if ref.get("nameCandidate")), "")

        items.append(
            {
                "code": code,
                "parentCode": parent_code(code),
                "classification": classification,
                "status": status,
                "nameKo": name_ko,
                "sourceManuals": source_manuals,
                "sourceRefs": source_refs,
                "allPagesByManual": pages_by_manual,
                "occurrenceCount": len(refs),
                "authoringRefs": authoring_entries,
                "shouldBeInCanonicalSubcodes": should_be_canonical,
                "shouldBeSearchable": should_be_searchable,
                "searchableInCurrentData": code in searchable_codes,
                "notes": notes,
            }
        )

    summary = {
        "totalCodes": len(items),
        "byClassification": {},
        "byStatus": {},
        "activeCanonicalCandidates": 0,
        "needsHumanReview": 0,
    }
    for item in items:
        summary["byClassification"][item["classification"]] = summary["byClassification"].get(item["classification"], 0) + 1
        summary["byStatus"][item["status"]] = summary["byStatus"].get(item["status"], 0) + 1
        if item["shouldBeInCanonicalSubcodes"]:
            summary["activeCanonicalCandidates"] += 1
        if item["classification"] == "needs_human_review" or item["status"] == "unknown":
            summary["needsHumanReview"] += 1

    output = {
        "manualVersion": "2026.6",
        "sourceDate": "2026-06-17",
        "sourceFiles": {manual: str(path.relative_to(ROOT)) for manual, path in SOURCE_FILES.items()},
        "regex": CODE_RE.pattern,
        "classificationRules": {
            "parentStatusSource": "backend/data/visa_authoring/statuses/*.json",
            "canonicalSubcodeSource": "status file subcodes arrays",
            "contextSignals": {
                "abolished": list(ABOLISHED_WORDS),
                "deprecated": list(DEPRECATED_WORDS),
                "multipleEntry": list(MULTIPLE_ENTRY_WORDS),
                "specialSuffixRegex": SPECIAL_SUFFIX_RE.pattern,
            },
            "sourceRefLimitPerCode": 12,
        },
        "summary": summary,
        "items": items,
    }

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(output, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote {OUTPUT.relative_to(ROOT)} ({len(items)} codes)")
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
