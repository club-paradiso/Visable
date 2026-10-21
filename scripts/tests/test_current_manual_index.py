"""Regression checks on the shipped index and actual FTS/snippet behavior."""
import json
from pathlib import Path
import sqlite3
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from backend.services import manual_search
from scripts.build_current_manual_corpus import extract_page_text

class CurrentManualIndexTest(unittest.TestCase):
    def test_duplicate_paint_is_removed_only_at_identical_coordinates(self):
        class Page:
            def get_text(self, mode=None, sort=True):
                return [(10, 10, 20, 20, '동일'), (10, 10, 20, 20, '동일'),
                        (25, 10, 35, 20, '동일'), (10, 30, 40, 40, 'F-6-3')]
        text, duplicates = extract_page_text(Page())
        self.assertEqual(text, '동일 동일\nF-6-3')
        self.assertEqual(duplicates, 1)

    def test_shipped_index_contains_every_current_page_as_approved_evidence(self):
        catalog = json.loads((ROOT / 'data/manual-corpus/catalog.json').read_text())
        with sqlite3.connect(manual_search.BACKEND_INDEX_PATH) as conn:
            self.assertEqual(conn.execute('PRAGMA integrity_check').fetchone()[0], 'ok')
            for source in catalog['sources']:
                total, direct, pages = conn.execute(
                    'SELECT count(*), sum(direct_evidence), count(distinct page) FROM chunk WHERE source_id=?',
                    (source['id'],)).fetchone()
                self.assertEqual(total, source['pages'])
                self.assertEqual(pages, source['pages'])
                # Owner-approved current editions (2026-10-16): every page is
                # direct evidence, and the catalog says so.
                self.assertEqual(source['approval_state'], 'approved')
                self.assertEqual(direct, source['pages'])

    def test_exact_subcode_has_nonempty_original_snippets(self):
        result = manual_search.search_manuals('E-7-4', limit=25)
        self.assertEqual(result['status'], 'ok')
        self.assertTrue(result['approved'])
        for hit in result['approved']:
            self.assertIn('E-7-4', hit['status_codes'])
            self.assertTrue(hit['excerpt'].strip())
            self.assertTrue(hit['usable_as_direct_evidence'])
            # PDF pages, or Markdown chunks page-mapped onto those PDF pages.
            self.assertIn(hit['source_id'], ('visa_manual_2026_09_01_pdf', 'stay_manual_2026_09_18_pdf',
                                             'visa_manual_2026_09_01_md', 'stay_manual_2026_09_18_md'))
            self.assertGreater(hit['page'], 0)
        # Superseded editions are never offered as direct evidence.
        for bucket in ('needs_review', 'superseded'):
            for hit in result.get(bucket) or []:
                self.assertFalse(hit['usable_as_direct_evidence'])

    def test_markdown_chunks_cite_a_page_of_their_own_approved_edition(self):
        """Owner-supplied HWP→Markdown chunks (2026-10-19) are direct evidence
        only where they were page-mapped; everything else is needs_review with
        no page, and stay and visa chunks never share a domain."""
        manifest = json.loads((ROOT / 'docs/source-manuals/source_manifest.json').read_text())
        catalog = {s['id']: s for s in json.loads((ROOT / 'data/manual-corpus/catalog.json').read_text())['sources']}
        derived = [d for e in manifest['current'].values() for d in e.get('derived_texts') or []]
        self.assertEqual(sorted(d['id'] for d in derived),
                         ['stay_manual_2026_09_18_md', 'visa_manual_2026_09_01_md'])
        with sqlite3.connect(manual_search.BACKEND_INDEX_PATH) as conn:
            for d in derived:
                corpus = json.loads((ROOT / d['page_map']).read_text())
                parent = catalog[d['page_source_id']]
                rows = conn.execute(
                    'SELECT approval_state, direct_evidence, page, domain, manual_version, family_key'
                    ' FROM chunk WHERE source_id=?', (d['id'],)).fetchall()
                self.assertEqual(len(rows), len(corpus['sections']))
                self.assertEqual({r[3] for r in rows}, {parent['domain']})
                self.assertEqual({r[4] for r in rows}, {parent['version']})
                direct = [r for r in rows if r[1]]
                self.assertEqual(len(direct), corpus['summary']['direct_evidence_chunks'])
                for state, is_direct, page, *_ in rows:
                    if is_direct:
                        self.assertEqual(state, 'approved')
                        self.assertTrue(1 <= page <= parent['pages'])
                    else:
                        self.assertEqual(state, 'needs_review')
                        self.assertEqual(page, 0)
            # The PDF rows are untouched by the Markdown: still one row per page.
            for sid, source in catalog.items():
                self.assertEqual(conn.execute('SELECT count(*) FROM chunk WHERE source_id=?', (sid,)).fetchone()[0],
                                 source['pages'])

    def test_domain_and_no_results_remain_distinct_from_unavailable(self):
        result = manual_search.search_manuals('F-6', domain='stay')
        self.assertTrue(result['approved'])
        self.assertTrue(all(h['domain'] == 'stay' for h in result['approved']))
        self.assertEqual(manual_search.search_manuals('zzzzmissingword')['status'], 'no_results')
        self.assertEqual(manual_search.search_manuals('F-6', path='/no/manual/index')['status'], 'index_unavailable')

if __name__ == '__main__':
    unittest.main()
