"""Offline tests with fictional values only; never treat fixtures as real cases."""
import copy
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from services.enforcement_case_registry import (
    CaseRegistryError, reviewed_observations, validate_case_registry,
)


def token(prefix, digit):
    return prefix + "_" + digit * 24


def fixture():
    source = token("src", "a")
    return {
        "schemaVersion": "1.0.0",
        "datasetVersion": "synthetic-test-only",
        "jurisdiction": "KR",
        "sources": [{
            "sourceId": source, "sourceType": "OFFICIAL_ADMINISTRATIVE_DECISION",
            "authority": "Official test authority",
            "publicUrl": "https://www.law.go.kr/LSW/deccInfoP.do?deccSeq=123",
            "publicationDate": "2026-10-21", "reviewStatus": "SOURCE_VERIFIED",
        }],
        "cases": [{
            "caseId": token("case", "b"),
            "sourceIds": [source],
            "subjects": [
                {"subjectId": token("subject", "c"), "role": "EMPLOYER", "statusOfStay": None,
                 "violationCode": "EMPLOYMENT_VIOLATION_TEST", "violationArticle": "제18조제3항",
                 "observations": [{
                     "observationId": token("obs", "d"), "type": "PENALTY_NOTICE",
                     "stage": "NOTIFIED", "amountKrw": 9000000,
                     "decisionDate": "2026-10-21", "sourceIds": [source],
                     "sourcePage": 2, "reviewStatus": "INDEPENDENTLY_REVIEWED",
                     "independentFromPrediction": True,
                 }]},
                {"subjectId": token("subject", "e"), "role": "FOREIGN_NATIONAL",
                 "statusOfStay": "UNKNOWN", "violationCode": None,
                 "violationArticle": None, "observations": []},
            ],
        }],
    }


class CaseRegistryTests(unittest.TestCase):
    def test_multi_subject_stores_only_documented_employer_notice(self):
        case = fixture()
        valid = validate_case_registry(case)
        self.assertEqual(len(valid["cases"][0]["subjects"]), 2)
        employer = reviewed_observations(valid, role="EMPLOYER", observation_type="PENALTY_NOTICE")
        foreigner = reviewed_observations(valid, role="FOREIGN_NATIONAL", observation_type="PENALTY_NOTICE")
        self.assertEqual(employer[0]["observedAmountKrw"], 9000000)
        self.assertEqual(foreigner, [], "employer amount is NOT a foreigner's assessed fine")
        self.assertEqual(len(employer), 1)

    def test_duplicate_source_and_subject_fail(self):
        data = fixture()
        data["sources"].append(copy.deepcopy(data["sources"][0]))
        with self.assertRaises(CaseRegistryError):
            validate_case_registry(data)
        data = fixture()
        data["cases"][0]["subjects"][1]["subjectId"] = token("subject", "c")
        with self.assertRaises(CaseRegistryError):
            validate_case_registry(data)

    def test_money_type_is_not_interchangeable(self):
        data = fixture()
        data["cases"][0]["subjects"][0]["observations"][0]["type"] = "DEPORTATION"
        with self.assertRaises(CaseRegistryError):
            validate_case_registry(data)
        data = fixture()
        data["cases"][0]["subjects"][0]["observations"][0]["stage"] = "PAID"
        with self.assertRaises(CaseRegistryError):
            validate_case_registry(data)

    def test_no_fabricated_payment_or_foreigner_outcomes(self):
        data = fixture()
        data["cases"][0]["subjects"][0]["observations"][0]["reviewStatus"] = "STAGED"
        self.assertEqual(reviewed_observations(data, role="EMPLOYER", observation_type="PENALTY_NOTICE"), [])
        self.assertEqual(reviewed_observations(fixture(), role="EMPLOYER", observation_type="PENALTY_PAYMENT_CONFIRMED"), [])

    def test_source_and_reviewer_protection(self):
        data = fixture()
        data["sources"][0]["reviewStatus"] = "STAGED"
        with self.assertRaises(CaseRegistryError):
            validate_case_registry(data)
        data = fixture()
        data["cases"][0]["subjects"][0]["observations"][0]["independentFromPrediction"] = False
        with self.assertRaises(CaseRegistryError):
            validate_case_registry(data)

    def test_identifier_and_unapproved_field_rejected(self):
        data = fixture()
        data["cases"][0]["subjects"][0]["name"] = "NO_PERSONAL_DATA"
        with self.assertRaises(CaseRegistryError):
            validate_case_registry(data)
        data = fixture()
        data["cases"][0]["subjects"][0]["nationality"] = "TEST"
        with self.assertRaises(CaseRegistryError):
            validate_case_registry(data)

    def test_source_host_and_credentials_rejected(self):
        for url in (
            "https://law.go.kr.evil.example/LSW",
            "http://www.law.go.kr/LSW",
            "https://127.0.0.1/LSW",
            "https://www.law.go.kr/LSW?OC=SECRET",
            "https://www.law.go.kr/LSW#fragment",
        ):
            data = fixture()
            data["sources"][0]["publicUrl"] = url
            with self.subTest(url=url), self.assertRaises(CaseRegistryError):
                validate_case_registry(data)

    def test_unreviewed_no_candidate_and_no_unknown_role(self):
        data = fixture()
        data["cases"][0]["subjects"][0]["observations"][0]["reviewStatus"] = "STAGED"
        self.assertEqual(reviewed_observations(data, role="EMPLOYER", observation_type="PENALTY_NOTICE"), [])
        with self.assertRaises(CaseRegistryError):
            reviewed_observations(data, role="UNKNOWN", observation_type="COURT_FINE")


if __name__ == "__main__":
    unittest.main()
