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
            self.assertIn(hit['source_id'], ('visa_manual_2026_09_01_pdf', 'stay_manual_2026_09_18_pdf'))
        # Superseded editions are never offered as direct evidence.
        for bucket in ('needs_review', 'superseded'):
            for hit in result.get(bucket) or []:
                self.assertFalse(hit['usable_as_direct_evidence'])

    def test_domain_and_no_results_remain_distinct_from_unavailable(self):
        result = manual_search.search_manuals('F-6', domain='stay')
        self.assertTrue(result['approved'])
        self.assertTrue(all(h['domain'] == 'stay' for h in result['approved']))
        self.assertEqual(manual_search.search_manuals('zzzzmissingword')['status'], 'no_results')
        self.assertEqual(manual_search.search_manuals('F-6', path='/no/manual/index')['status'], 'index_unavailable')

if __name__ == '__main__':
    unittest.main()
