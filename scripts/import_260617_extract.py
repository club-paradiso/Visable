#!/usr/bin/env python3
from pathlib import Path
import shutil
import sys
import zipfile

SRC_PREFIX = 'manual_extract_260617/'
DEST = Path('docs/source-manuals/2026-06-17/extracted')


def safe_output_path(dest_root: Path, rel: str) -> Path:
    rel_path = Path(rel)

    if rel_path.is_absolute():
        raise ValueError(f'absolute path is not allowed: {rel}')

    if not rel or any(part in ('', '.', '..') for part in rel.split('/')):
        raise ValueError(f'unsafe path component in archive member: {rel}')

    out = (dest_root / rel_path).resolve()
    if out != dest_root and dest_root not in out.parents:
        raise ValueError(f'archive member escapes destination: {rel}')

    return out


if len(sys.argv) != 2:
    print('usage: python3 scripts/import_260617_extract.py /path/to/manual_extract_260617.zip')
    raise SystemExit(2)

zip_path = Path(sys.argv[1]).expanduser()
if not zip_path.exists():
    print(f'not found: {zip_path}', file=sys.stderr)
    raise SystemExit(1)

dest_root = DEST.resolve()

count = 0
with zipfile.ZipFile(zip_path) as zf:
    members = []
    for info in zf.infolist():
        if info.is_dir() or not info.filename.startswith(SRC_PREFIX):
            continue
        rel = info.filename[len(SRC_PREFIX):]
        if not rel:
            continue
        try:
            out = safe_output_path(dest_root, rel)
        except ValueError as exc:
            print(f'invalid ZIP entry {info.filename!r}: {exc}', file=sys.stderr)
            raise SystemExit(1) from exc
        members.append((info, out))

    if DEST.exists():
        shutil.rmtree(DEST)
    DEST.mkdir(parents=True, exist_ok=True)

    for info, out in members:
        out.parent.mkdir(parents=True, exist_ok=True)
        with zf.open(info) as src, out.open('wb') as dst:
            shutil.copyfileobj(src, dst)
        count += 1

print(f'imported {count} files into {DEST}')
