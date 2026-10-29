#!/usr/bin/env python3
"""Verify the handoff against the saved artifact and its immutable case files."""
import hashlib
import json
import zipfile
from pathlib import Path

root = Path(__file__).resolve().parent
index = json.loads((root / 'handoff-index.json').read_text(encoding='utf-8'))
with zipfile.ZipFile(root / 'Artemis-label-review-backup-20261027.zip') as archive:
    assert archive.testzip() is None
    sheet = json.loads(archive.read('cases.json'))
records = index['records']
assert len(records) == len(sheet['cases']) == 140
assert len({r['record_id'] for r in records}) == 140
assert [r['record_id'] for r in records] == [c['id'] for c in sheet['cases']]
changed = []
for info in sheet['sets']:
    path = root / 'originals' / info['file']
    assert hashlib.sha256(path.read_bytes()).hexdigest() == info['sha256'], info['file']
    original = json.loads(path.read_text(encoding='utf-8'))['cases']
    candidate = root / 'partial-v2' / info['file'].replace('_cases.json', '_cases.v2-partial.json')
    revised = json.loads(candidate.read_text(encoding='utf-8'))['cases'] if candidate.exists() else original
    assert [x['id'] for x in original] == [x['id'] for x in revised]
    for old, new in zip(original, revised):
        if old != new:
            changed.append(old['id'])
assert changed == [c['record_id'] for c in index['changes']]
print(f'PASS: {len(records)} IDs and order, original SHA-256, {len(changed)} changed case IDs')
print('Scope: file integrity only; this is not a legal validation or live-storage check.')
