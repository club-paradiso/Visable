"""The engineering gate must not pass on missing or inferior measurements."""
import copy
import importlib.util
from pathlib import Path

path = Path(__file__).resolve().parents[3] / "scripts/check_bfixed_metrics.py"
spec = importlib.util.spec_from_file_location("bfixed_metrics_gate", path)
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)


def inputs():
    keys = ["procedure_fine_accuracy","status_exact_accuracy","subcode_accuracy_subcode_expected",
            "current_status_accuracy","target_status_accuracy"]
    headline = {s:{"classification."+k:{"numerator":4,"denominator":5} for k in keys} for s in ("dev","test")}
    current={"benchmark":{"digest":"fixed"},"headline":{"b_fixed":copy.deepcopy(headline),"b2_js":copy.deepcopy(headline)},
             "baselines":{n:{"available":True} for n in ("b_fixed","b2_js")},
             "items":{n:[{"id":"one","task":"status_procedure_classification","status":"ok"}] for n in ("b_fixed","b2_js")}}
    previous={"benchmark_digest":"fixed","systems":{"B_fixed_before":{"headline":headline}}}
    return current,previous


def test_equal_measurements_pass_engineering_gate_only():
    assert not gate.failures(*inputs())


def test_missing_denominator_or_process_is_not_a_pass():
    current,previous=inputs()
    current["headline"]["b_fixed"]["test"]["classification.procedure_fine_accuracy"]["denominator"]=0
    current["baselines"]["b_fixed"]["available"]=False
    current["items"]["b_fixed"]=[]
    errors=gate.failures(current,previous)
    assert any("denominator" in e for e in errors)
    assert any("unavailable" in e for e in errors)
    assert any("no classification" in e for e in errors)


def test_regression_in_either_procedure_or_direction_fails():
    for key in ("procedure_fine_accuracy","target_status_accuracy","subcode_accuracy_subcode_expected"):
        current,previous=inputs()
        current["headline"]["b_fixed"]["test"]["classification."+key]["numerator"]=3
        assert any("regression" in e for e in gate.failures(current,previous))
