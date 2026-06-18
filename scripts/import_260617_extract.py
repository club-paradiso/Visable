#!/usr/bin/env python3
from pathlib import Path
import shutil
import sys
import zipfile

SRC_PREFIX = 'manual_extract_260617/'
DEST = Path('docs/source-manuals/2026-06-17/extracted')

if len(sys.argv) != 2:
    print('usage: python3 scripts/import_260617_extract.py /path/to/manual_extract_260617.zip')
    raise SystemExit(2)

zip_path = Path(sys.argv[1]).expanduser()
if not zip_path.exists():
    print(f'not found: {zip_path}', file=sys.stderr)
    raise SystemExit(1)

if DEST.exists():
    shutil.rmtree(DEST)
DEST.mkdir(parents=True, exist_ok=True)

count = 0
with zipfile.ZipFile(zip_path) as zf:
    for info in zf.infolist():
        if info.is_dir() or not info.filename.startswith(SRC_PREFIX):
            continue
        rel = info.filename[len(SRC_PREFIX):]
        if not rel:
            continue
        out = DEST / rel
        out.parent.mkdir(parents=True, exist_ok=True)
        with zf.open(info) as src, out.open('wb') as dst:
            shutil.copyfileobj(src, dst)
        count += 1

print(f'imported {count} files into {DEST}')
