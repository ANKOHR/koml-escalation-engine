"""Reports preserve provenance and never invent measured savings."""

import json


def safe_text(value):
    return str(value).replace(chr(0x2014), "-")


def json_text(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2).replace(chr(0x2014), "\\u2014") + "\n"


def banner(result):
    synthetic = [i["file"] for i in result["inputs"] if i["synthetic"]]
    real = [i["file"] for i in result["inputs"] if not i["synthetic"]]
    return safe_text(f"Data provenance: SYNTHETIC fixtures: {', '.join(synthetic) or 'none'}. Real inputs declared hand-entered by Henry: {', '.join(real) or 'none'}. Declarations are not independently verified. Ground-truth agreement measures supplied labels, not real-world accuracy.")


def render(result, format):
    if format == "json":
        return json_text({"provenance_banner": banner(result), **result})
    lines = ["# KOML Escalation Engine report", "", banner(result), "", result["savings"], "", "## Computed counts", ""]
    for field, value in result["summary"].items():
        lines.append(f"- {field}: {json.dumps(value, sort_keys=True)}")
    lines += ["", "Reason counts can overlap. Amounts are input minor units, not savings or a currency conversion.", "", "## Decision trace", ""]
    for decision in result["decisions"]:
        lines.append("- " + json.dumps(decision, ensure_ascii=False, sort_keys=True))
    return safe_text("\n".join(lines)) + "\n"
