import json
import os
from pathlib import Path
import subprocess
import sys
import time

import pytest

from koml_escalation_engine.cli import main
from koml_escalation_engine.fixtures import fixture_document


def setup_fixture(tmp_path):
    directory = tmp_path / "input"
    assert main(["fixtures", "--out", str(directory)]) == 0
    return directory


def test_run_completes_on_fixture(tmp_path, capsys):
    directory = setup_fixture(tmp_path)
    start = time.perf_counter()
    results = tmp_path / "results.json"
    assert main(["run", "--input", str(directory), "--results", str(results)]) == 0
    assert main(["report", "--results", str(results), "--format", "md"]) == 0
    assert time.perf_counter() - start < 5


def test_empty_input_renders_without_traceback(tmp_path, capsys):
    directory = tmp_path / "empty"
    directory.mkdir()
    results = tmp_path / "results.json"
    assert main(["run", "--input", str(directory), "--results", str(results)]) == 0
    assert main(["report", "--results", str(results)]) == 0
    assert "records: 0" in capsys.readouterr().out


@pytest.mark.parametrize("name,text,line", [("bad.json", '{\n"broken":\n}', 3), ("bad.csv", "a,b", 1), ("bad.yaml", "bad: [", 1)])
def test_malformed_input_named_error(tmp_path, capsys, name, text, line):
    (tmp_path / name).write_text(text, encoding="utf-8")
    assert main(["run", "--input", str(tmp_path)]) == 2
    error = capsys.readouterr().err
    assert "ParseError" in error and name in error and f"line {line}" in error
    assert "Traceback" not in error


def test_determinism_byte_identical(tmp_path):
    directory = setup_fixture(tmp_path)
    results = tmp_path / "results.json"
    output = tmp_path / "report.md"
    snapshots = []
    for _ in range(2):
        assert main(["run", "--input", str(directory), "--results", str(results)]) == 0
        assert main(["report", "--results", str(results), "--out", str(output)]) == 0
        snapshots.append((results.read_bytes(), output.read_bytes()))
    assert snapshots[0] == snapshots[1]


def test_cli_smoke_all_subcommands(tmp_path, capsys):
    directory = setup_fixture(tmp_path)
    results = tmp_path / "results.json"
    for args in [["run", "--input", str(directory), "--results", str(results)], ["report", "--format", "json", "--results", str(results)], ["triage", "--input", str(directory)], ["explain", "--input", str(directory), "--id", "g0-00"]]:
        assert main(args) == 0
    for command in ("fixtures", "run", "report", "triage", "explain"):
        with pytest.raises(SystemExit) as exit:
            main([command, "--help"])
        assert exit.value.code == 0
    assert "Example:" in capsys.readouterr().out


def test_handles_unicode_and_long_inputs(tmp_path, capsys):
    document = fixture_document()
    record = document["records"][0]
    record["id"] = "任务-é"
    record["description"] = "日本語 C:\\Users\\henry\\任务 " + "x" * 90000
    (tmp_path / "任务.json").write_text(json.dumps(document, ensure_ascii=False), encoding="utf-8")
    assert main(["explain", "--input", str(tmp_path), "--id", record["id"]]) == 0
    assert record["id"] in capsys.readouterr().out


def test_missing_input_and_failed_write(tmp_path, capsys):
    assert main(["run", "--input", str(tmp_path / "absent")]) == 2
    assert "MissingInput" in capsys.readouterr().err
    directory = setup_fixture(tmp_path)
    target = tmp_path / "directory"
    target.mkdir()
    assert main(["run", "--input", str(directory), "--results", str(target)]) == 2
    assert "WriteError" in capsys.readouterr().err
    assert not any(p.name.startswith("tmp") for p in tmp_path.iterdir())


def test_expectations_are_not_used_for_decisions(tmp_path, capsys):
    directory = setup_fixture(tmp_path)
    (directory / "expectations.json").write_text('{"synthetic":true,"summary":{"escalations":999}}', encoding="utf-8")
    assert main(["triage", "--input", str(directory)]) == 0
    output = capsys.readouterr().out
    assert '"escalations": 120' in output


def test_subprocess_demo(tmp_path):
    environment = dict(os.environ, PYTHONPATH=str(Path(__file__).resolve().parents[1]), PYTHONIOENCODING="utf-8")
    start = time.perf_counter()
    for args in (["fixtures", "--out", "demo"], ["run", "--input", "demo"], ["report", "--format", "md"]):
        result = subprocess.run([sys.executable, "-m", "koml_escalation_engine.cli", *args], cwd=tmp_path, env=environment, capture_output=True, text=True, encoding="utf-8")
        assert result.returncode == 0, result.stderr
    assert "Data provenance:" in result.stdout
    assert time.perf_counter() - start < 5


@pytest.mark.parametrize("mutation", ["inputs", "summary", "savings", "decisions"])
def test_report_rejects_corrupted_results(tmp_path, capsys, mutation):
    from koml_escalation_engine.core import evaluate
    result = evaluate([("records.json", fixture_document())])
    if mutation == "inputs":
        result["inputs"] = [None]
    elif mutation == "summary":
        result["summary"]["escalations"] = 999
    elif mutation == "savings":
        result["savings"] = "Saved 100 pounds"
    else:
        result["decisions"][0]["escalate"] = True
    path = tmp_path / "results.json"
    path.write_text(json.dumps(result), encoding="utf-8")
    assert main(["report", "--results", str(path)]) == 2
    assert "SchemaError" in capsys.readouterr().err


def test_json_preserves_external_ids_and_report_recomputes(tmp_path, capsys):
    document = fixture_document()
    document["records"][0]["id"] = "task" + chr(0x2014) + "one"
    directory = tmp_path / "input"
    directory.mkdir()
    (directory / "records.json").write_text(json.dumps(document), encoding="utf-8")
    results = tmp_path / "results.json"
    assert main(["run", "--input", str(directory), "--results", str(results)]) == 0
    assert json.loads(results.read_text(encoding="utf-8"))["decisions"][0]["id"] == document["records"][0]["id"]
    assert chr(0x2014) not in results.read_text(encoding="utf-8")
    assert main(["report", "--results", str(results), "--format", "json"]) == 0
    capsys.readouterr()
