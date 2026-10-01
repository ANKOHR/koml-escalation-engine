from copy import deepcopy

import pytest

from koml_escalation_engine.core import SchemaError, evaluate
from koml_escalation_engine.fixtures import fixture_document


def test_rejects_adversarial_values():
    for field, value in [("amount_minor", -1), ("amount_minor", 1.5), ("retries", True), ("created_on", "2099-01-01"), ("description", "x" * 100001), ("status", "unknown"), ("unexpected", 1)]:
        document = fixture_document()
        document["records"][0][field] = value
        with pytest.raises(SchemaError):
            evaluate([("records.json", document)])
    document = fixture_document()
    document["records"][1]["id"] = document["records"][0]["id"]
    with pytest.raises(SchemaError, match="duplicate"):
        evaluate([("records.json", document)])


def test_ground_truth_corruption_changes_measured_agreement():
    document = fixture_document()
    before = evaluate([("records.json", document)])
    document["records"][0]["expected_escalation"] = True
    after = evaluate([("records.json", document)])
    assert after["summary"]["false_negatives"] == 1
    assert after["summary"]["escalations"] == before["summary"]["escalations"]
    document["records"][0]["approval_required"] = True
    assert evaluate([("records.json", document)])["summary"]["escalations"] == 121


def test_boundaries_and_completed_override():
    result = evaluate([("records.json", fixture_document())])
    assert all(not d["escalate"] for d in result["decisions"] if d["id"].startswith(("g7", "g8")))


def test_duplicate_across_files_and_no_mutation():
    document = fixture_document()
    original = deepcopy(document)
    evaluate([("a.json", document)])
    assert document == original
    with pytest.raises(SchemaError, match="duplicate"):
        evaluate([("a.json", document), ("b.json", document)])


@pytest.mark.parametrize("field,value", [("synthetic", 1), ("entered_by", "unknown"), ("as_of", "bad"), ("policy", {}), ("records", {})])
def test_document_schema(field, value):
    document = fixture_document()
    document[field] = value
    with pytest.raises(SchemaError):
        evaluate([("a.json", document)])
