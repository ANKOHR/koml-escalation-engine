import json

from koml_escalation_engine.cli import main
from koml_escalation_engine.core import evaluate
from koml_escalation_engine.fixtures import expectations, fixture_document


def test_fixtures_labelled_synthetic(tmp_path):
    assert main(["fixtures", "--out", str(tmp_path)]) == 0
    for path in tmp_path.iterdir():
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["synthetic"] is True
    assert len(fixture_document()["records"]) == 200


def test_fixture_ground_truth_matches_hand_computed():
    result = evaluate([("records.json", fixture_document())])
    assert result["summary"] == expectations()["summary"]
    assert {d["id"] for d in result["decisions"] if d["escalate"]} == {f"g{g}-{i:02}" for g in range(1, 7) for i in range(20)}
