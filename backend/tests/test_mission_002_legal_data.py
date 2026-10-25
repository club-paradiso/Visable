"""Metadata repair must preserve source manuals, requirements and future dates."""
import hashlib
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

def read(path):
    return json.loads((ROOT / path).read_text())

def test_repaired_law_versions_and_unchanged_article_review_dates():
    rules = read('data/guidance-rules-202609.json')['law_sources']
    for key in ('act_35', 'act_36', 'act_87'):
        assert (rules[key]['law_id'], rules[key]['mst'], rules[key]['effective']) == ('001707', '290729', '2026-10-02')
        assert rules[key]['checked_on'] == '2026-09-22'  # not a newly verified article body
        assert rules[key]['review_state'] == 'BODY_REVALIDATION_PENDING'
        assert rules[key]['body_review_mst'] == '272921'
        assert rules[key]['identity_checked_on'] == '2026-10-26'
        assert rules[key]['checked_on_scope'] == 'listed_article_summary'
    for key in ('decree_40','decree_42','decree_44','decree_45'):
        assert (rules[key]['law_id'], rules[key]['mst'], rules[key]['effective']) == ('005256','290501','2026-10-02')
        assert rules[key]['body_review_mst'] == '289697'
        assert rules[key]['body_review_state'] == 'PREVIOUS_VERSION_SUMMARY_ONLY'
    rule = rules['rule_73']
    assert (rule['mst'], rule['effective']) == ('291289', '2026-10-23')
    assert rule['body_reference_date'] == '2026-10-26'
    assert rule['review_state'] == 'ARTICLE_TEXT_AT_REFERENCE_DATE_READ'
    assert '신용카드' not in rule['quote_ko']
    assert rule['scheduled'][0]['at'] == '2027-09-16T00:00:00+09:00'
    assert '신용카드' in rule['scheduled'][0]['set']['quote_ko']


def test_nationality_links_are_identity_verified_not_form_verified():
    registry = {s['sourceId']: s for s in read('data/nationality_sources.json')['sources']}
    services = {s['id']: s for s in read('data/nationality_service_sources.json')['sources']}
    for key, seq, date in [('law-nationality-decree','246165','2022-12-20'),('law-nationality-rule','291055','2026-10-02')]:
        row=registry[key]
        assert row['url'].endswith('lsiSeq='+seq)
        assert services[key]['url'] == row['url']
        assert row['sourceDate'] == row['effectiveDate'] == date
        assert row['contentVerified'] is False
    future=registry['law-nationality-act-2026-amendment']
    assert future['effectiveDate'] == '2026-12-03'
    assert future['reflection'] == 'correction_signal_only'


def test_manual_originals_are_unchanged_and_shipped_copies_match():
    evidence = read('docs/ai/waymaker-genesis/mission-002-phase-1/legal-evidence.json')
    for path, digest in evidence['manual_sha256'].items():
        assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest() == digest
    for a,b in [('visa_data.json','backend/data/visas.json'),('data/status-guidance-202609.json','backend/data/knowledge_deploy/status-guidance-202609.json')]:
        assert (ROOT/a).read_bytes() == (ROOT/b).read_bytes()
    d3=read('backend/data/visa_authoring/statuses/D-3.json')
    # Raw manual transcription is intentionally NOT renamed.
    raw=(ROOT/'backend/data/visa_authoring/statuses/D-3.json').read_text()
    assert '관한 지침 (제5조)' in raw
    assert any('관한 훈령」 제5조' in n for n in d3['procedures']['extension']['notes'])


def test_f4_number_conflict_is_explicit_without_rewriting_the_manual():
    evidence = read('docs/ai/waymaker-genesis/mission-002-phase-1/legal-evidence.json')['f4_notice']
    assert evidence['official_number'] == '제2026-65호'
    assert evidence['admRulId'] == '2090230'
    assert evidence['effective'] == '2026-02-12'
    script = (ROOT/'scripts/extract_dongpo_manual_2026_02.py').read_text()
    assert '원문 표기 제2026-35호 / 공식 고시 제2026-65호' in script
    assert '번호 불일치, 원문은 보존' in script
