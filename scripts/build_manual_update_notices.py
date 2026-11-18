#!/usr/bin/env python3
"""Build data/manual-updates/pending_revisions.json: the per-status "새 매뉴얼 개정 후보" notices the UI shows.

Input
  audits/manual-refresh-*/<pair>.json     paragraph-level edition diffs (scripts/diff_manual_paragraph_editions.py);
                                          each pair compares the edition the guidance follows with the newest staged one
                                          (visa 2026-10-19 → 2026-11-06, stay 2026-11-02 → 2026-11-16)
  data/manual-updates/hunk_mapping.json   hand-written status/procedure mapping for every changed hunk
  docs/source-manuals/source_manifest.json   pending_review_editions (hash-pinned editions)

Output
  data/manual-updates/pending_revisions.json

Rules (CLAUDE.md): never rewrites visa_data.json / doc_master.json, never adds a requirement. The notice quotes the
changed manual lines verbatim and says plainly that the edition is not reviewed yet. A changed hunk with no mapping
fails the build, so a new revision cannot be dropped silently. A mapping entry may list `line_prefixes` to quote only
some lines of a multi-line hunk (e.g. to leave out a line whose only change is a bullet mark). After a human review promotes the edition
(and the guidance data is updated), regenerate with an empty diff set or remove the entries.

Usage:  python3 scripts/build_manual_update_notices.py [--check]
"""
import argparse, json, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAPPING = ROOT / 'data/manual-updates/hunk_mapping.json'
OUT = ROOT / 'data/manual-updates/pending_revisions.json'
MANIFEST = ROOT / 'docs/source-manuals/source_manifest.json'
AUDITS = ROOT / 'audits'
COVER = re.compile(r'^\d{4}\. \d{1,2}\.$')


def load(p):
    return json.loads(Path(p).read_text(encoding='utf-8'))


def build():
    mapping = load(MAPPING)
    manifest = load(MANIFEST)
    pending = {}
    for e in manifest['pending_review_editions']:
        if e.get('derived_reader_markdown') and e['source_date'] > pending.get(e['role'], {}).get('source_date', ''):
            pending[e['role']] = e  # newest staged edition per role (the one the manual reader shows)
    role_key = {'visa': 'visa_issuance_manual', 'stay': 'stay_residence_manual'}
    revisions, problems, used = [], [], set()
    editions = {}
    for pair in sorted({e['pair'] for e in mapping['entries']}):
        found = sorted(AUDITS.glob(f'manual-refresh-*/{pair}.json'))
        if len(found) != 1:
            problems.append(f'{pair}: expected exactly one audits/manual-refresh-*/{pair}.json, found {len(found)}')
            continue
        d = load(found[0])
        role = 'visa' if pair.startswith('visa') else 'stay'
        pe = pending.get(role_key[role])
        if not pe:
            problems.append(f'{role}: no pending_review edition with reader Markdown in the manifest')
            continue
        new_label = d['meta'].get('new_label', '')
        if pe['source_date'] not in new_label and pe['source_date'][2:].replace('-', '') not in new_label:
            problems.append(f'{pair}: diff ends at {new_label}, but the newest staged {role} edition is {pe["source_date"]}')
            continue
        editions[role] = {'source_date': pe['source_date'], 'version': pe['version'], 'status': 'pending_review',
                          'hwp_sha256': pe['original_hwp_sha256'], 'diff': found[0].with_suffix('.md').relative_to(ROOT).as_posix(),
                          'reader_markdown': pe['derived_reader_markdown']['file'],
                          'compared_with': d['meta'].get('old_label') or d['meta'].get('old', '')}
        for h in d['hunks']:
            new = h.get('new_lines') or []
            if not new:
                continue
            if mapping.get('ignore_cover_month_change') and all(COVER.match(x.strip()) for x in new + (h.get('old_lines') or [])):
                continue
            hit = [m for m in mapping['entries'] if m['pair'] == pair and any(x.strip().startswith(m['match_new_line_prefix']) for x in new)]
            if not hit:
                problems.append(f'{pair}: hunk at new line {h["new_start"]} has no mapping in hunk_mapping.json: {new[0][:60]}')
                continue
            for m in hit:
                used.add(m['id'])
                if m.get('line_prefixes'):
                    lines = [x.strip() for x in new if any(x.strip().startswith(p) for p in m['line_prefixes'])]
                else:
                    lines = [x.strip() for x in new if x.strip().startswith(m['match_new_line_prefix']) or len(hit) == 1]
                revisions.append({
                    'id': m['id'], 'role': role, 'kind': h['kind'], 'codes': m['codes'], 'procedures': m['procedures'],
                    'reader_hash': m['reader_hash'], 'title_ko': m['title_ko'], 'title_en': m['title_en'],
                    'summary_ko': m['summary_ko'], 'summary_en': m['summary_en'],
                    'manual_lines': lines, 'manual_line_no': h['new_start'], 'state': 'pending_review'})
    for m in mapping['entries']:
        if m['id'] not in used:
            problems.append(f'mapping {m["id"]} matched no changed hunk (stale mapping)')
    order = {m['id']: i for i, m in enumerate(mapping['entries'])}
    revisions.sort(key=lambda r: order[r['id']])
    out = {
        'schema_version': 1, 'generated_by': 'scripts/build_manual_update_notices.py',
        'state': 'pending_review',
        'note': '새로 반입된 매뉴얼(사증 ' + editions.get('visa', {}).get('source_date', '-') + ', 체류 ' + editions.get('stay', {}).get('source_date', '-') + ')에서 바뀐 곳입니다. 아직 사람이 검토하지 않았고, Visable의 자격별 안내·AI 답변은 이전 판을 따릅니다. 신청 전에 원문을 확인하세요.',
        'editions': editions, 'revisions': revisions}
    return out, problems


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    args = ap.parse_args()
    out, problems = build()
    text = json.dumps(out, ensure_ascii=False, indent=1) + '\n'
    if problems:
        print('\n'.join('PROBLEM: ' + p for p in problems), file=sys.stderr)
        return 1
    if args.check:
        if not OUT.exists() or OUT.read_text(encoding='utf-8') != text:
            print('pending_revisions.json is stale: run python3 scripts/build_manual_update_notices.py', file=sys.stderr)
            return 1
        print(f'manual update notices up to date ({len(out["revisions"])} revisions)')
        return 0
    OUT.write_text(text, encoding='utf-8')
    print(f'wrote {OUT.relative_to(ROOT)}: {len(out["revisions"])} revisions')
    return 0


if __name__ == '__main__':
    sys.exit(main())
