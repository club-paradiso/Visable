#!/usr/bin/env python3
"""Tests for the 배포용 HWP decryptor.

Runnable standalone (`python3 scripts/tests/test_decrypt_hwp_distribution.py`)
or via pytest. No network, no manual files required: the AES core is checked
against the FIPS-197 vector, the key schedule against a synthetic record, and
the record/text walkers against hand-built payloads.

The AES fallback matters more than it looks. When pycryptodome is absent the
script decrypts with its own implementation, and a subtly wrong one does not
raise — it yields plausible-length garbage that then fails somewhere far away
in the pipeline. So it is pinned to the published vector here.
"""
from __future__ import annotations

import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import decrypt_hwp_distribution as D  # noqa: E402

FAILURES: list[str] = []


def check(name, fn):
    try:
        fn()
        print(f"  PASS  {name}")
    except AssertionError as exc:
        FAILURES.append(f"{name}: {exc}")
        print(f"  FAIL  {name}: {exc}")
    except Exception as exc:  # noqa: BLE001
        FAILURES.append(f"{name}: {type(exc).__name__}: {exc}")
        print(f"  ERROR {name}: {type(exc).__name__}: {exc}")


def _without_pycryptodome(fn):
    """Run fn with `Crypto` imports blocked, forcing the pure-Python path."""
    import builtins
    real = builtins.__import__

    def blocked(name, *a, **k):
        if name.startswith("Crypto"):
            raise ImportError("blocked for test")
        return real(name, *a, **k)

    builtins.__import__ = blocked
    try:
        return fn()
    finally:
        builtins.__import__ = real


def test_aes_fips197_vector():
    """The published AES-128 vector, through the pure-Python path."""
    key = bytes.fromhex("000102030405060708090a0b0c0d0e0f")
    ciphertext = bytes.fromhex("69c4e0d86a7b0430d8cdb78070b4c55a")
    expected = bytes.fromhex("00112233445566778899aabbccddeeff")
    got = _without_pycryptodome(lambda: D._aes128_ecb_decrypt(key, ciphertext))
    assert got == expected, f"got {got.hex()}, want {expected.hex()}"


def test_aes_fallback_matches_reference():
    """Pure-Python and pycryptodome must agree over multiple blocks."""
    try:
        from Crypto.Cipher import AES
    except Exception:
        print("       (skipped: pycryptodome not installed)")
        return
    import os
    key = os.urandom(16)
    data = os.urandom(16 * 40)
    reference = AES.new(key, AES.MODE_ECB).decrypt(data)
    mine = _without_pycryptodome(lambda: D._aes128_ecb_decrypt(key, data))
    assert mine == reference, "pure-Python AES diverges from pycryptodome"


def test_key_derivation_is_deterministic_and_seed_dependent():
    record = bytes(range(256))
    k1 = D.derive_key(record)
    k2 = D.derive_key(record)
    assert k1 == k2, "key derivation is not deterministic"
    assert len(k1) == 16, f"key must be 16 bytes, got {len(k1)}"
    other = bytes([0xFF, 0, 0, 0]) + record[4:]
    assert D.derive_key(other) != k1, "different seed produced the same key"


def test_key_offset_follows_seed_low_nibble():
    """Offset is 4 + (seed & 0x0F); a seed change inside the nibble moves it."""
    base = bytearray(256)
    base[0:4] = struct.pack("<I", 0x00000000)
    a = D.derive_key(bytes(base))
    base[0:4] = struct.pack("<I", 0x00000007)
    b = D.derive_key(bytes(base))
    assert a != b, "seed low nibble did not affect the key window"


def test_rejects_non_distribution_section():
    """A section that does not open with the distribute record must not be
    silently decrypted into garbage."""
    header = struct.pack("<I", (67) | (0 << 10) | (8 << 20))
    raw = header + b"\x00" * 8
    try:
        D.decrypt_section(raw)
    except ValueError as exc:
        assert "not a distribution section" in str(exc)
        return
    raise AssertionError("expected ValueError for a non-distribution section")


def test_iter_records_walks_headers():
    def rec(tag, level, payload):
        return struct.pack("<I", tag | (level << 10) | (len(payload) << 20)) + payload

    buf = rec(67, 0, b"abcd") + rec(66, 1, b"xy")
    got = [(t, lv, p) for t, lv, p in D.iter_records(buf)]
    assert got == [(67, 0, b"abcd"), (66, 1, b"xy")], got


def test_iter_records_handles_extended_size():
    payload = b"z" * 5000
    header = struct.pack("<I", 67 | (0 << 10) | (0xFFF << 20))
    buf = header + struct.pack("<I", len(payload)) + payload
    got = list(D.iter_records(buf))
    assert len(got) == 1 and got[0][2] == payload, "extended size not handled"


def test_para_text_keeps_surrogate_pairs_intact():
    """Decoding WCHAR-by-WCHAR splits astral characters into lone surrogates,
    which then cannot be encoded to UTF-8 at write time."""
    astral = "\U0001F600"          # outside the BMP -> a surrogate pair
    payload = ("가나" + astral + "다").encode("utf-16-le")
    out = D.para_text(payload)
    assert out == "가나" + astral + "다", repr(out)
    out.encode("utf-8")            # must not raise


def test_para_text_skips_control_runs():
    """Inline/extended controls occupy 8 WCHARs; a naive skip of 1 would leak
    binary padding into the text."""
    payload = (struct.pack("<H", 4) + b"\x00" * 14          # 8 WCHARs total
               + "본문".encode("utf-16-le"))
    assert D.para_text(payload) == "본문", repr(D.para_text(payload))


def test_para_text_maps_breaks_to_newlines():
    payload = ("가".encode("utf-16-le") + struct.pack("<H", 13)
               + "나".encode("utf-16-le"))
    assert D.para_text(payload) == "가\n나"


def test_production_data_untouched():
    """This script only ever reads. Guard the protected files by hash."""
    import hashlib
    protected = ["visa_data.json", "doc_master.json", "backend/data/visas.json"]
    before = {}
    for rel in protected:
        p = ROOT / rel
        if p.exists():
            before[rel] = hashlib.sha256(p.read_bytes()).hexdigest()
    # Exercise the module's pure paths.
    D.derive_key(bytes(256))
    D.para_text("확인".encode("utf-16-le"))
    for rel, digest in before.items():
        now = hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()
        assert now == digest, f"{rel} was modified"


def main() -> int:
    print("decrypt_hwp_distribution:")
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            check(name[5:].replace("_", " "), fn)
    if FAILURES:
        print(f"\nFAIL — {len(FAILURES)} failure(s)")
        return 1
    print("\nOK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
