"""Local-file CLI with atomic output and named failures."""

import argparse
import json
import os
from pathlib import Path
import sys
import tempfile

from .core import SchemaError, evaluate, validate_result
from .fixtures import expectations, fixture_document
from .report import json_text, render, safe_text


class InputError(ValueError):
    pass


def load_json(path):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError(f"duplicate JSON key {key}")
            result[key] = value
        return result
    try:
        return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=pairs)
    except json.JSONDecodeError as error:
        raise InputError(f"ParseError: {path}: line {error.lineno}: {error.msg}") from error
    except (UnicodeError, ValueError) as error:
        raise InputError(f"ParseError: {path}: line 1: {error}") from error


def read_input(directory):
    path = Path(directory)
    if not path.is_dir():
        raise InputError(f"MissingInput: {path}: use kee fixtures --out <dir> or supply an existing input directory")
    documents = []
    for file in sorted(path.iterdir()):
        if file.name == "expectations.json":
            continue
        if file.is_file():
            if file.suffix != ".json":
                raise InputError(f"ParseError: {file}: line 1: unsupported format; use JSON")
            document = load_json(file)
            try:
                evaluate([(file.name, document)])
            except SchemaError as error:
                raise SchemaError(f"{file}: line 1 (schema location): {error}") from error
            documents.append((file.name, document))
    return evaluate(documents)


def atomic_write(path, text):
    path = Path(path)
    temporary = None
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", newline="\n", dir=path.parent, delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(text)
        os.replace(temporary, path)
    except OSError as error:
        raise InputError(f"WriteError: {path}: {error}") from error
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def parser():
    root = argparse.ArgumentParser(description="Compute human intervention from explicit local inputs. No predictions or savings estimates.")
    commands = root.add_subparsers(dest="command", required=True)
    fixtures = commands.add_parser("fixtures", help="Generate 200 labelled synthetic records", epilog="Example: kee fixtures --out demo")
    fixtures.add_argument("--out", required=True)
    run = commands.add_parser("run", help="Evaluate inputs and store computed results", epilog="Example: kee run --input demo")
    run.add_argument("--input", required=True)
    run.add_argument("--results", default=".kee/results.json")
    report = commands.add_parser("report", help="Render computed results with provenance", epilog="Example: kee report --format md")
    report.add_argument("--format", choices=("md", "json"), default="md")
    report.add_argument("--results", default=".kee/results.json")
    report.add_argument("--out")
    triage = commands.add_parser("triage", help="List records requiring intervention and reasons", epilog="Example: kee triage --input demo")
    triage.add_argument("--input", required=True)
    explain = commands.add_parser("explain", help="Explain one record's policy decision", epilog="Example: kee explain --input demo --id g1-00")
    explain.add_argument("--input", required=True)
    explain.add_argument("--id", required=True)
    return root


def main(argv=None):
    args = parser().parse_args(argv)
    try:
        if args.command == "fixtures":
            atomic_write(Path(args.out) / "records.json", json_text(fixture_document()))
            atomic_write(Path(args.out) / "expectations.json", json_text(expectations()))
            print("SYNTHETIC fixtures: 200 records generated. No real data or measured savings.")
        elif args.command == "report":
            path = Path(args.results)
            if not path.is_file():
                raise InputError(f"MissingInput: {path}: first use kee run --input <dir>")
            result = load_json(path)
            result = validate_result(result)
            output = render(result, args.format)
            if args.out:
                atomic_write(args.out, output)
            else:
                sys.stdout.write(output)
        else:
            result = read_input(args.input)
            if args.command == "run":
                atomic_write(args.results, json_text(result))
                print(render(result, "json"), end="")
            elif args.command == "triage":
                result["decisions"] = [d for d in result["decisions"] if d["escalate"]]
                print(render(result, "json"), end="")
            else:
                selected = [d for d in result["decisions"] if d["id"] == args.id]
                if not selected:
                    raise InputError(f"MissingRecord: {args.id}: check --id against input records")
                result["decisions"] = selected
                print(render(result, "json"), end="")
        return 0
    except (InputError, SchemaError, OSError, KeyError, TypeError) as error:
        name = "SchemaError: " if isinstance(error, (SchemaError, KeyError, TypeError)) else ""
        print(safe_text(name + str(error)), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
