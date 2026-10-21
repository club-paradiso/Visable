"""Canonical status-of-stay code inventory, read-only from ``visa_data.json``.

Why: a label that names a code Waymaker does not know (a typo such as "E-7-04",
an invented subcode) silently teaches a model a status that does not exist. The
validator therefore checks every status and subcode code in ``expected`` and in
``source_refs`` against the codes the product itself serves.

``visa_data.json`` is a protected file. This module only reads it and never
writes or reformats it.

Shape of the file as observed on 2026-10-19 (42 top-level records, 261 codes):

* Each top-level record has a ``code``. Subcodes sit in ``subCodes`` and again
  in ``subcodes`` (identical lists kept for UI compatibility); both are read.
* Two 3-segment codes (D-4-1, D-4-2K) are top-level records *and* subcodes of
  D-4. The repository rule is that 3+ segments make a subcode, so they count as
  subcodes of D-4 here, not as parents.
* The ``*-T`` variants (D-10-T, E-7-T, F-2-T, F-5-T, plus F-2-T1 and F-5-T1)
  exist only as subcodes.
* Program records (K-STAR, REGION-S, YOUTH-STAY: ``isProgram`` true or
  ``cat`` "etc") are not statuses of stay. Their subcode lists name codes that
  also sit under a status parent (F-2-7S under F-2 and K-STAR) or only under
  the program (F-3-3R under REGION-S).
* C-3 lists the 2-segment code C-2 among its subcodes, and C-2 has no record
  of its own. The repository rule says a 2-segment code is a parent, the file
  says C-2 sits under C-3. The inventory keeps both facts
  (``irregular_placements``) instead of choosing one, and the validator turns
  any label that depends on the choice into a review warning.

Hierarchy decisions follow the repository rule (segments), placements follow
the file. Where the two disagree, neither silently wins.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, FrozenSet, Iterable, List, Mapping, Optional, Set

REPO_ROOT = Path(__file__).resolve().parents[4]
DEFAULT_INVENTORY_PATH = REPO_ROOT / "visa_data.json"

SUBCODE_LIST_KEYS = ("subCodes", "subcodes")


class InventoryError(Exception):
    """The inventory file is missing or does not have the expected shape."""


@dataclass(frozen=True)
class CodeInventory:
    top_level: FrozenSet[str]
    programs: FrozenSet[str]
    #: subcode -> top-level records that list it
    placements: Mapping[str, FrozenSet[str]]
    source: str = ""

    @property
    def all_codes(self) -> FrozenSet[str]:
        return self.top_level | frozenset(self.placements)

    def contains(self, code: str) -> bool:
        return code in self.top_level or code in self.placements

    def is_program(self, code: str) -> bool:
        return code in self.programs

    def parents_of(self, code: str) -> FrozenSet[str]:
        return self.placements.get(code, frozenset())

    def status_parents_of(self, code: str) -> FrozenSet[str]:
        """Placements under a status of stay (programs excluded)."""
        return frozenset(p for p in self.parents_of(code) if p not in self.programs)

    def program_parents_of(self, code: str) -> FrozenSet[str]:
        return frozenset(p for p in self.parents_of(code) if p in self.programs)

    def is_subcode(self, code: str) -> bool:
        """A known code with 3+ segments (the repository hierarchy rule).

        D-4-1 is a top-level record in the file and still a subcode; the
        ``*-T`` variants are subcodes; C-2 (2 segments, listed under C-3) is not.
        """
        return self.contains(code) and segment_count(code) >= 3

    def is_parent_code(self, code: str) -> bool:
        """A known 2-segment code, which may stand as ``status_code`` (programs included)."""
        return self.contains(code) and segment_count(code) <= 2

    def irregular_placements(self, code: str) -> FrozenSet[str]:
        """Status records that list a 2-segment (parent-shaped) code as their subcode, e.g. C-2 under C-3."""
        if segment_count(code) > 2:
            return frozenset()
        return self.status_parents_of(code)

    def structural_parent(self, code: str) -> Optional[str]:
        """First two segments (E-7-4R -> E-7) when that is a top-level status code."""
        if segment_count(code) < 3:
            return None
        candidate = "-".join(code.split("-")[:2])
        if candidate in self.top_level and candidate not in self.programs:
            return candidate
        return None


def segment_count(code: str) -> int:
    return len([part for part in code.split("-") if part])


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------
_CACHE: Dict[str, CodeInventory] = {}


def load_inventory(path: Optional[Path] = None) -> CodeInventory:
    """Load (and cache per path) the inventory. Raises InventoryError on a bad file."""
    inventory_path = Path(path) if path else DEFAULT_INVENTORY_PATH
    key = str(inventory_path.resolve())
    if key not in _CACHE:
        try:
            with open(inventory_path, "r", encoding="utf-8") as handle:
                records = json.load(handle)
        except FileNotFoundError as exc:
            raise InventoryError(f"inventory file not found: {inventory_path}") from exc
        except json.JSONDecodeError as exc:
            raise InventoryError(f"inventory file is not valid JSON: {inventory_path}: {exc}") from exc
        _CACHE[key] = build_inventory(records, source=str(inventory_path))
    return _CACHE[key]


def build_inventory(records: Any, source: str = "") -> CodeInventory:
    if not isinstance(records, list):
        raise InventoryError("inventory must be a JSON array of status records")
    top_level: Set[str] = set()
    programs: Set[str] = set()
    placements: Dict[str, Set[str]] = {}
    for position, record in enumerate(records):
        code = record.get("code") if isinstance(record, dict) else None
        if not isinstance(code, str) or not code:
            raise InventoryError(f"inventory record {position} has no code")
        top_level.add(code)
        if _is_program(record):
            programs.add(code)
        for subcode in _subcodes_of(record):
            placements.setdefault(subcode, set()).add(code)
    return CodeInventory(
        top_level=frozenset(top_level),
        programs=frozenset(programs),
        placements={code: frozenset(parents) for code, parents in placements.items()},
        source=source,
    )


def _is_program(record: Mapping[str, Any]) -> bool:
    return record.get("isProgram") is True or record.get("cat") == "etc"


def _subcodes_of(record: Mapping[str, Any]) -> List[str]:
    codes: List[str] = []
    for key in SUBCODE_LIST_KEYS:
        codes.extend(_codes_in(record.get(key) or []))
    return sorted(set(codes))


def _codes_in(entries: Iterable[Any]) -> List[str]:
    codes: List[str] = []
    for entry in entries:
        if isinstance(entry, dict) and isinstance(entry.get("code"), str) and entry["code"]:
            codes.append(entry["code"])
        elif isinstance(entry, str) and entry:
            codes.append(entry)
    return codes
