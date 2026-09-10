from __future__ import annotations

import json
import sys
import unittest
from copy import deepcopy
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = REPO_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from services.enforcement_ontology import (  # noqa: E402
    EnforcementOntologyError,
    deterministic_violation_codes,
    load_enforcement_ontology,
    ontology_statute_reference,
    validate_legal_rule_database,
    validate_ontology_data,
    violation_map,
)
from services.enforcement_rules import RULES_PATH, load_rule_database  # noqa: E402


class EnforcementOntologyTests(unittest.TestCase):
    def setUp(self):
        self.ontology = load_enforcement_ontology()
        self.rules = json.loads(RULES_PATH.read_text(encoding="utf-8"))

    def test_checked_in_ontology_matches_deterministic_rules(self):
        loaded_rules = load_rule_database()
        observed = {
            rule["violationCode"]
            for snapshot in loaded_rules["snapshots"]
            for rule in snapshot["rules"]
        }
        self.assertEqual(observed, deterministic_violation_codes(self.ontology))
        self.assertEqual(len(observed), 5)

    def test_public_labels_and_primary_articles_do_not_drift(self):
        definitions = violation_map(self.ontology)
        for snapshot in self.rules["snapshots"]:
            for rule in snapshot["rules"]:
                definition = definitions[rule["violationCode"]]
                self.assertEqual(rule["label"], definition["labelKo"])
                self.assertEqual(rule["statuteArticle"], ontology_statute_reference(definition))

    def test_duplicate_violation_codes_are_rejected(self):
        broken = deepcopy(self.ontology)
        broken["violations"].append(deepcopy(broken["violations"][0]))
        with self.assertRaisesRegex(EnforcementOntologyError, "duplicate violation code"):
            validate_ontology_data(broken)

    def test_unknown_material_fact_dimension_is_rejected(self):
        broken = deepcopy(self.ontology)
        broken["violations"][0]["materialFactDimensions"].append("inventedDimension")
        with self.assertRaisesRegex(EnforcementOntologyError, "unknown material fact dimension"):
            validate_ontology_data(broken)

    def test_rule_outside_ontology_is_rejected(self):
        broken = deepcopy(self.rules)
        invented = deepcopy(broken["snapshots"][0]["rules"][0])
        invented["violationCode"] = "TEST_ONLY_UNKNOWN_RULE"
        broken["snapshots"][0]["rules"].append(invented)
        with self.assertRaisesRegex(EnforcementOntologyError, "missing from ontology"):
            validate_legal_rule_database(broken, ontology=self.ontology)

    def test_rule_label_drift_is_rejected(self):
        broken = deepcopy(self.rules)
        broken["snapshots"][0]["rules"][0]["label"] = "drifted label"
        with self.assertRaisesRegex(EnforcementOntologyError, "rule label drift"):
            validate_legal_rule_database(broken, ontology=self.ontology)

    def test_rule_statute_drift_is_rejected(self):
        broken = deepcopy(self.rules)
        broken["snapshots"][0]["rules"][0]["statuteArticle"] = "출입국관리법 제999조"
        with self.assertRaisesRegex(EnforcementOntologyError, "rule statute drift"):
            validate_legal_rule_database(broken, ontology=self.ontology)

    def test_planned_non_deterministic_concept_does_not_require_money_rule(self):
        extended = deepcopy(self.ontology)
        extended["violations"].append({
            "code": "TEST_ONLY_PLANNED_CONCEPT",
            "labelKo": "테스트 전용 계획 개념",
            "category": "TEST_ONLY",
            "legalBasis": {"lawName": "TEST_ONLY", "article": "TEST_ONLY"},
            "materialFactDimensions": ["violationType"],
            "lifecycle": "PLANNED",
            "supportedByDeterministicRules": False,
        })
        validate_legal_rule_database(self.rules, ontology=extended)
        self.assertNotIn("TEST_ONLY_PLANNED_CONCEPT", deterministic_violation_codes(extended))


if __name__ == "__main__":
    unittest.main()
