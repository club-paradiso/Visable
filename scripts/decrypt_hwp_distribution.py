#!/usr/bin/env python3
"""Decrypt HWP 5.x 배포용(distribution) documents and extract their body text.

Why this exists
---------------
The HiKorea 사증/체류 안내매뉴얼 ship as *배포용* HWP (FileHeader flag 0x4).
In that mode ``BodyText`` is a ~300-byte stub and the real content lives in
``ViewText/Section{N}``, AES-128-ECB encrypted. Until now this repository
recorded that as an absolute blocker — ``scripts/convert_manual_hwp.py`` still
classifies such files ``blocked_distribution_hwp``, and every open-source
backend it benchmarks returns 0 characters, because they all read ``BodyText``.

That was true of those backends but not of the format. The 배포용 scheme is
documented in Hancom's published *한글 문서 파일 형식 5.0* specification, and
the decryption key is carried **inside the file**: each ViewText section opens
with a ``HWPTAG_DISTRIBUTE_DOC_DATA`` record whose 256-byte payload yields the
key. It marks a document as view-only; it is not an access control over a
secret, and these manuals are public documents published for reading.

So this is a format reader, not a bypass: it reads a public document in a
documented public format.

What it does NOT do
-------------------
It does not decide that an extraction is authoritative. Promotion of any
edition to ``approved`` in ``data/manual_approval_index.json`` remains a human
action — see the notes in that file and ``docs/hikorea_manual_sync.md``.

Usage
-----
    python3 scripts/decrypt_hwp_distribution.py INPUT.hwp [-o OUT.txt]
    python3 scripts/decrypt_hwp_distribution.py INPUT.hwp --stats

Requires ``olefile``; AES comes from ``pycryptodome`` when present, otherwise a
small pure-Python AES-128-ECB decryptor built in below keeps the script usable
with no third-party crypto dependency.
"""
from __future__ import annotations

import argparse
import struct
import sys
import zlib
from pathlib import Path

TAG_DISTRIBUTE_DOC_DATA = 0x01C   # HWPTAG_BEGIN (0x10) + 12
TAG_PARA_TEXT = 67                # HWPTAG_BEGIN (0x10) + 51

# Control characters inside HWPTAG_PARA_TEXT. Both kinds occupy 8 WCHARs
# (the marker plus 7 more); plain "char" controls occupy 1.
CTRL_INLINE = frozenset({4, 5, 6, 7, 8, 9, 19, 20})
CTRL_EXTENDED = frozenset({1, 2, 3, 11, 12, 14, 15, 16, 17, 18, 21, 22, 23})
CTRL_WIDE = CTRL_INLINE | CTRL_EXTENDED


# --------------------------------------------------------------- AES fallback
# Only ECB decryption of a single 128-bit key is needed. pycryptodome is used
# when installed; this keeps the script working on a bare interpreter.

_SBOX = bytes.fromhex(
    "637c777bf26b6fc53001672bfed7ab76ca82c97dfa5947f0add4a2af9ca472c0"
    "b7fd9326363ff7cc34a5e5f171d8311504c723c31896059a071280e2eb27b275"
    "09832c1a1b6e5aa0523bd6b329e32f8453d100ed20fcb15b6acbbe394a4c58cf"
    "d0efaafb434d338545f9027f503c9fa851a3408f929d38f5bcb6da2110fff3d2"
    "cd0c13ec5f974417c4a77e3d645d197360814fdc222a908846eeb814de5e0bdb"
    "e0323a0a4906245cc2d3ac629195e479e7c8376d8dd54ea96c56f4ea657aae08"
    "ba78252e1ca6b4c6e8dd741f4bbd8b8a703eb5664803f60e613557b986c11d9e"
    "e1f8981169d98e949b1e87e9ce5528df8ca1890dbfe6426841992d0fb054bb16"
)
_INV_SBOX = bytes(256)
_tmp = bytearray(256)
for _i, _v in enumerate(_SBOX):
    _tmp[_v] = _i
_INV_SBOX = bytes(_tmp)
_RCON = (0x01, 0x02, 0x04, 0x08, 0x10, 0x20, 0x40, 0x80, 0x1B, 0x36)


def _xtime(a: int) -> int:
    a <<= 1
    return (a ^ 0x1B) & 0xFF if a & 0x100 else a


def _mul(a: int, b: int) -> int:
    r = 0
    while b:
        if b & 1:
            r ^= a
        a = _xtime(a)
        b >>= 1
    return r


def _expand_key(key: bytes) -> list[list[int]]:
    w = [list(key[i * 4:i * 4 + 4]) for i in range(4)]
    for i in range(4, 44):
        t = list(w[i - 1])
        if i % 4 == 0:
            t = t[1:] + t[:1]
            t = [_SBOX[b] for b in t]
            t[0] ^= _RCON[i // 4 - 1]
        w.append([w[i - 4][j] ^ t[j] for j in range(4)])
    return [sum(w[r * 4:r * 4 + 4], []) for r in range(11)]


def _aes128_ecb_decrypt(key: bytes, data: bytes) -> bytes:
    try:
        from Crypto.Cipher import AES  # type: ignore
        return AES.new(key, AES.MODE_ECB).decrypt(data)
    except Exception:
        pass
    rk = _expand_key(key)
    out = bytearray(len(data))
    for off in range(0, len(data), 16):
        s = bytearray(data[off:off + 16])
        for j in range(16):
            s[j] ^= rk[10][j]
        for rnd in range(9, -1, -1):
            # InvShiftRows
            t = bytearray(s)
            for r in range(1, 4):
                for c in range(4):
                    t[((c + r) % 4) * 4 + r] = s[c * 4 + r]
            # InvSubBytes
            s = bytearray(_INV_SBOX[b] for b in t)
            # AddRoundKey
            for j in range(16):
                s[j] ^= rk[rnd][j]
            if rnd:
                # InvMixColumns
                for c in range(4):
                    a = s[c * 4:c * 4 + 4]
                    s[c * 4 + 0] = _mul(a[0], 14) ^ _mul(a[1], 11) ^ _mul(a[2], 13) ^ _mul(a[3], 9)
                    s[c * 4 + 1] = _mul(a[0], 9) ^ _mul(a[1], 14) ^ _mul(a[2], 11) ^ _mul(a[3], 13)
                    s[c * 4 + 2] = _mul(a[0], 13) ^ _mul(a[1], 9) ^ _mul(a[2], 14) ^ _mul(a[3], 11)
                    s[c * 4 + 3] = _mul(a[0], 11) ^ _mul(a[1], 13) ^ _mul(a[2], 9) ^ _mul(a[3], 14)
        out[off:off + 16] = s
    return bytes(out)


# ------------------------------------------------------------ key derivation

def _msvc_rand(seed: int):
    """The MSVC ``rand()`` LCG the format's key schedule is defined against."""
    n = seed
    while True:
        n = (n * 214013 + 2531011) & 0xFFFFFFFF
        yield (n >> 16) & 0x7FFF


def derive_key(record: bytes) -> bytes:
    """Recover the AES-128 key from a 256-byte HWPTAG_DISTRIBUTE_DOC_DATA payload.

    The record is XOR-masked with a run-length keystream: each reload draws
    *two* values from the LCG — one for the mask byte, one for how many bytes
    it covers. The key is then a 16-byte window whose offset the seed selects.
    """
    seed = struct.unpack_from("<I", record, 0)[0]
    rnd = _msvc_rand(seed)
    buf = bytearray(record)
    remaining = 0
    mask = 0
    for i in range(256):
        if remaining == 0:
            mask = next(rnd) & 0xFF
            remaining = (next(rnd) & 0x0F) + 1
        buf[i] ^= mask
        remaining -= 1
    offset = 4 + (seed & 0x0F)
    return bytes(buf[offset:offset + 16])


def decrypt_section(raw: bytes) -> bytes:
    """Decrypt one ``ViewText/Section{N}`` stream into raw HWP body records."""
    header = struct.unpack_from("<I", raw, 0)[0]
    tag = header & 0x3FF
    size = (header >> 20) & 0xFFF
    if tag != TAG_DISTRIBUTE_DOC_DATA:
        raise ValueError(
            f"not a distribution section: leading tag is 0x{tag:03X}, "
            f"expected 0x{TAG_DISTRIBUTE_DOC_DATA:03X}")
    pos = 4
    if size == 0xFFF:
        size = struct.unpack_from("<I", raw, 4)[0]
        pos = 8
    key = derive_key(raw[pos:pos + size])
    body = raw[pos + size:]
    body = body[:len(body) - (len(body) % 16)]
    return zlib.decompressobj(-15).decompress(_aes128_ecb_decrypt(key, body))


# ------------------------------------------------------------ record walking

def iter_records(buf: bytes):
    """Yield ``(tag, level, payload)`` for each HWP record in a decoded section."""
    pos = 0
    end = len(buf)
    while pos + 4 <= end:
        header = struct.unpack_from("<I", buf, pos)[0]
        tag = header & 0x3FF
        level = (header >> 10) & 0x3FF
        size = (header >> 20) & 0xFFF
        pos += 4
        if size == 0xFFF:
            if pos + 4 > end:
                break
            size = struct.unpack_from("<I", buf, pos)[0]
            pos += 4
        yield tag, level, buf[pos:pos + size]
        pos += size


def para_text(payload: bytes) -> str:
    """Decode one HWPTAG_PARA_TEXT payload.

    Runs of ordinary characters are decoded as UTF-16LE in one go rather than
    per ``chr()``: decoding character by character splits a surrogate pair into
    two lone surrogates, which then cannot be encoded back out to UTF-8.
    """
    out: list[str] = []
    run = bytearray()
    i = 0
    n = len(payload) // 2
    while i < n:
        pair = payload[i * 2:i * 2 + 2]
        code = struct.unpack("<H", pair)[0]
        if code >= 32:
            run += pair
            i += 1
            continue
        if run:
            out.append(run.decode("utf-16-le", "replace"))
            run = bytearray()
        if code in CTRL_WIDE:
            i += 8
            continue
        if code in (10, 13):
            out.append("\n")
        i += 1
    if run:
        out.append(run.decode("utf-16-le", "replace"))
    return "".join(out)


def is_distribution(path: Path) -> bool:
    import olefile
    ole = olefile.OleFileIO(str(path))
    try:
        flags = struct.unpack_from("<I", ole.openstream("FileHeader").read(), 36)[0]
        return bool(flags & 0x4)
    finally:
        ole.close()


def extract(path: Path) -> str:
    """Extract the full body text of a 배포용 HWP."""
    import olefile
    ole = olefile.OleFileIO(str(path))
    try:
        sections = sorted(
            (s for s in ("/".join(e) for e in ole.listdir())
             if s.startswith("ViewText/Section")),
            key=lambda s: int(s.rsplit("Section", 1)[1]))
        if not sections:
            raise ValueError("no ViewText sections — not a distribution HWP?")
        chunks = []
        for name in sections:
            decoded = decrypt_section(ole.openstream(name).read())
            chunks.append("".join(
                para_text(payload) for tag, _, payload in iter_records(decoded)
                if tag == TAG_PARA_TEXT))
        return "\n".join(chunks)
    finally:
        ole.close()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("input", type=Path)
    ap.add_argument("-o", "--out", type=Path, help="write text here (default: stdout)")
    ap.add_argument("--stats", action="store_true",
                    help="print extraction statistics instead of the text")
    args = ap.parse_args()

    if not args.input.exists():
        print(f"ERROR: {args.input} not found", file=sys.stderr)
        return 1
    try:
        text = extract(args.input)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    if args.stats:
        import re
        lines = [ln for ln in text.split("\n") if ln.strip()]
        codes = re.findall(r"\b[A-H]-\d{1,2}(?:-\d{1,2})?\b", text)
        korean = sum(1 for ch in text if "가" <= ch <= "힣")
        print(f"characters      : {len(text):,}")
        print(f"non-empty lines : {len(lines):,}")
        print(f"korean ratio    : {korean / max(len(text), 1):.3f}")
        print(f"visa codes      : {len(codes):,} occurrences, "
              f"{len(set(codes))} distinct")
        print(f"U+FFFD          : {text.count(chr(0xFFFD))}")
        return 0

    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text, encoding="utf-8")
        print(f"wrote {len(text):,} characters to {args.out}")
    else:
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
