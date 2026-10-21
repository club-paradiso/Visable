"""The read-only status code inventory (waymaker_ai.dataset.inventory).

These tests read the real visa_data.json, because the point of the inventory is
to mirror it. They assert structure the repository rules depend on, not counts
that change whenever a subcode is added.
"""
from __future__ import annotations

import pytest

from waymaker_ai.dataset.inventory import InventoryError, build_inventory, load_inventory


@pytest.fixture(scope="module")
def inventory():
    return load_inventory()


def test_parents_and_subcodes_are_present(inventory):
    for code in ("D-2", "E-7", "F-2", "G-1", "D-10"):
        assert inventory.is_parent_code(code), code
    for code in ("D-2-1", "E-7-4", "G-1-5", "E-7-1"):
        assert inventory.is_subcode(code), code
        assert not inventory.is_parent_code(code), code


def test_g_1_5_is_a_subcode_of_g_1_never_a_family(inventory):
    assert inventory.parents_of("G-1-5") == frozenset({"G-1"})
    assert "G-1-5" not in inventory.top_level


def test_t_variants_exist_only_as_subcodes(inventory):
    for code, parent in (("D-10-T", "D-10"), ("E-7-T", "E-7"), ("F-2-T", "F-2"), ("F-5-T", "F-5")):
        assert inventory.contains(code)
        assert code not in inventory.top_level
        assert parent in inventory.parents_of(code)


def test_three_segment_top_level_records_still_count_as_subcodes(inventory):
    # D-4-1 is a top-level record in visa_data.json and also listed under D-4.
    assert "D-4-1" in inventory.top_level
    assert inventory.is_subcode("D-4-1")
    assert inventory.parents_of("D-4-1") == frozenset({"D-4"})


def test_programs_and_program_placed_subcodes(inventory):
    assert {"K-STAR", "REGION-S", "YOUTH-STAY"} <= inventory.programs
    assert inventory.parents_of("F-2-7S") == frozenset({"F-2", "K-STAR"})
    assert inventory.status_parents_of("F-3-3R") == frozenset()
    assert inventory.program_parents_of("F-3-3R") == frozenset({"REGION-S"})
    assert inventory.structural_parent("F-3-3R") == "F-3"
    assert inventory.structural_parent("REGIONAL-D-2") is None


def test_unknown_codes_are_not_contained(inventory):
    for code in ("E-7-04", "e-7", "G-1-55", "Z-9"):
        assert not inventory.contains(code), code


def test_build_inventory_reads_both_subcode_keys():
    inventory = build_inventory([
        {"code": "X-1", "subCodes": [{"code": "X-1-1"}], "subcodes": [{"code": "X-1-2"}]},
        {"code": "PROG", "cat": "etc", "subcodes": [{"code": "X-1-1"}]},
    ])
    assert inventory.parents_of("X-1-1") == frozenset({"X-1", "PROG"})
    assert inventory.contains("X-1-2")
    assert inventory.is_program("PROG")


def test_bad_inventory_shapes_raise():
    with pytest.raises(InventoryError):
        build_inventory({"code": "X-1"})
    with pytest.raises(InventoryError):
        build_inventory([{"name": "no code"}])


def test_two_segment_code_listed_under_another_status_is_irregular_not_a_subcode(inventory):
    # visa_data.json lists C-2 under C-3 and gives it no record of its own.
    assert "C-2" not in inventory.top_level
    assert inventory.contains("C-2")
    assert inventory.is_parent_code("C-2") and not inventory.is_subcode("C-2")
    assert inventory.irregular_placements("C-2") == frozenset({"C-3"})
    assert inventory.irregular_placements("E-7") == frozenset()
    assert inventory.irregular_placements("E-7-4") == frozenset()


def test_program_only_subcodes(inventory):
    assert inventory.is_subcode("REGIONAL-D-2")
    assert inventory.status_parents_of("REGIONAL-D-2") == frozenset()
    assert inventory.structural_parent("REGIONAL-D-2") is None
    assert inventory.is_parent_code("K-STAR") and inventory.is_program("K-STAR")


def test_inventory_is_read_only():
    import hashlib

    from waymaker_ai.dataset.inventory import DEFAULT_INVENTORY_PATH

    before = hashlib.sha256(DEFAULT_INVENTORY_PATH.read_bytes()).hexdigest()
    load_inventory()
    assert hashlib.sha256(DEFAULT_INVENTORY_PATH.read_bytes()).hexdigest() == before
