import json

from koml_escalation_engine.core import evaluate
from koml_escalation_engine.fixtures import expectations, fixture_document
from koml_escalation_engine.report import render


def test_report_matches_ground_truth_exact():
    result = evaluate([("records.json", fixture_document())])
    output = json.loads(render(result, "json"))
    assert output["summary"] == expectations()["summary"]
    for name, value in expectations()["summary"].items():
        assert f"- {name}: {json.dumps(value, sort_keys=True)}" in render(result, "md")


def test_report_zero_false_positives():
    result = evaluate([("records.json", fixture_document())])
    assert result["summary"]["false_positives"] == 0
    assert result["summary"]["false_negatives"] == 0


def test_report_carries_provenance_banner():
    synthetic = fixture_document()
    real = fixture_document()
    real.update(synthetic=False, entered_by="Henry", records=[])
    for format in ("md", "json"):
        output = render(evaluate([("synthetic.json", synthetic), ("real.json", real)]), format)
        assert "Data provenance:" in output
        assert "SYNTHETIC fixtures: synthetic.json" in output
        assert "hand-entered by Henry: real.json" in output


def test_hypothetical_figures_labelled():
    for format in ("md", "json"):
        output = render(evaluate([]), format)
        assert "Unmeasured" in output
        assert "no measured baseline supplied" in output


def test_no_em_dashes_in_outputs():
    for format in ("md", "json"):
        assert chr(0x2014) not in render(evaluate([("name" + chr(0x2014), fixture_document())]), format)
