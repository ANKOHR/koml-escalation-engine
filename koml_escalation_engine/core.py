"""Pure schema validation and deterministic policy evaluation."""

from datetime import date


class SchemaError(ValueError):
    """An explicit input violates the documented schema."""


def fail(field, message):
    raise SchemaError(f"{field}: {message}")


def iso_date(value, field):
    if not isinstance(value, str):
        fail(field, "expected ISO date YYYY-MM-DD")
    try:
        result = date.fromisoformat(value)
    except ValueError:
        fail(field, "expected valid ISO date YYYY-MM-DD")
    if result.isoformat() != value:
        fail(field, "expected ISO date YYYY-MM-DD")
    return result


def integer(value, field):
    if type(value) is not int or not 0 <= value <= 10**12:
        fail(field, "expected integer from 0 to 1000000000000")


def validate(document):
    if not isinstance(document, dict):
        fail("document", "expected object")
    required = {"synthetic", "entered_by", "as_of", "policy", "records"}
    if set(document) != required:
        fail("document fields", f"missing {sorted(required - set(document))}, unknown {sorted(set(document) - required)}")
    if type(document["synthetic"]) is not bool:
        fail("synthetic", "expected boolean")
    if document["entered_by"] != ("fixture-generator" if document["synthetic"] else "Henry"):
        fail("entered_by", "must be fixture-generator for synthetic or Henry for real hand-entered data")
    as_of = iso_date(document["as_of"], "as_of")
    policy = document["policy"]
    if not isinstance(policy, dict) or set(policy) != {"retry_limit", "amount_limit_minor"}:
        fail("policy", "required fields: retry_limit, amount_limit_minor")
    for field, value in policy.items():
        integer(value, f"policy.{field}")
    if policy["retry_limit"] == 0:
        fail("policy.retry_limit", "must be positive")
    if not isinstance(document["records"], list):
        fail("records", "expected array")
    ids = set()
    fields = {"id", "description", "created_on", "due_on", "status", "approval_required", "retries", "amount_minor"}
    for index, record in enumerate(document["records"]):
        prefix = f"records[{index}]"
        if not isinstance(record, dict) or set(record) not in (fields, fields | {"expected_escalation"}):
            fail(prefix, "schema drift: required " + ", ".join(sorted(fields)) + "; only optional field expected_escalation")
        for field in ("id", "description"):
            value = record[field]
            if not isinstance(value, str) or not value.strip() or len(value) > (256 if field == "id" else 100000):
                fail(f"{prefix}.{field}", "expected nonempty string within length limit")
        if record["id"] in ids:
            fail(f"{prefix}.id", "duplicate id")
        ids.add(record["id"])
        created = iso_date(record["created_on"], f"{prefix}.created_on")
        if created > as_of:
            fail(f"{prefix}.created_on", "future creation date relative to as_of")
        due = iso_date(record["due_on"], f"{prefix}.due_on") if record["due_on"] is not None else None
        if due is not None and due < created:
            fail(f"{prefix}.due_on", "precedes created_on")
        if record["status"] not in ("active", "blocked", "completed"):
            fail(f"{prefix}.status", "expected active, blocked, or completed")
        for field in ("approval_required", "expected_escalation"):
            if field in record and type(record[field]) is not bool:
                fail(f"{prefix}.{field}", "expected boolean")
        for field in ("retries", "amount_minor"):
            integer(record[field], f"{prefix}.{field}")
    return document


def reasons(record, policy, as_of):
    if record["status"] == "completed":
        return []
    result = []
    if record["approval_required"]:
        result.append("approval_required")
    if record["status"] == "blocked":
        result.append("blocked")
    if record["due_on"] is not None and record["due_on"] < as_of:
        result.append("overdue")
    if record["retries"] >= policy["retry_limit"]:
        result.append("retry_limit")
    if record["amount_minor"] > policy["amount_limit_minor"]:
        result.append("amount_limit")
    return result


def evaluate(documents):
    decisions, inputs, seen = [], [], set()
    for filename, document in sorted(documents, key=lambda item: item[0]):
        validate(document)
        inputs.append({"file": filename, "synthetic": document["synthetic"], "entered_by": document["entered_by"], "as_of": document["as_of"], "policy": document["policy"]})
        for record in document["records"]:
            if record["id"] in seen:
                fail("id", f"duplicate across files: {record['id']}")
            seen.add(record["id"])
            why = reasons(record, document["policy"], document["as_of"])
            decisions.append({"id": record["id"], "file": filename, "escalate": bool(why), "reasons": why, "amount_minor": record["amount_minor"], "expected_escalation": record.get("expected_escalation"), "record": dict(record)})
    labelled = [d for d in decisions if d["expected_escalation"] is not None]
    counts = {reason: sum(reason in d["reasons"] for d in decisions) for reason in ("approval_required", "blocked", "overdue", "retry_limit", "amount_limit")}
    return {"inputs": inputs, "decisions": decisions, "summary": {"records": len(decisions), "escalations": sum(d["escalate"] for d in decisions), "no_intervention": sum(not d["escalate"] for d in decisions), "amount_minor_total": sum(d["amount_minor"] for d in decisions), "reason_counts": counts, "labelled_records": len(labelled), "true_positives": sum(d["escalate"] and d["expected_escalation"] for d in labelled), "false_positives": sum(d["escalate"] and not d["expected_escalation"] for d in labelled), "false_negatives": sum(not d["escalate"] and d["expected_escalation"] for d in labelled)}, "savings": "Unmeasured: no time or money savings claimed; no measured baseline supplied."}


def validate_result(result):
    """Recompute saved results from their facts; reject drift or invented figures."""
    if not isinstance(result, dict) or set(result) != {"inputs", "decisions", "summary", "savings"}:
        fail("results", "expected inputs, decisions, summary, savings; regenerate with kee run")
    if not isinstance(result["inputs"], list) or not isinstance(result["decisions"], list):
        fail("results", "inputs and decisions must be arrays")
    documents = {}
    for source in result["inputs"]:
        if not isinstance(source, dict) or set(source) != {"file", "synthetic", "entered_by", "as_of", "policy"}:
            fail("results.inputs", "invalid source fields")
        filename = source["file"]
        if not isinstance(filename, str) or filename in documents:
            fail("results.inputs.file", "expected unique filename string")
        documents[filename] = {key: value for key, value in source.items() if key != "file"}
        documents[filename]["records"] = []
    for decision in result["decisions"]:
        if not isinstance(decision, dict) or not isinstance(decision.get("file"), str) or decision["file"] not in documents or "record" not in decision:
            fail("results.decisions", "missing source or record facts; regenerate with kee run")
        documents[decision["file"]]["records"].append(decision["record"])
    computed = evaluate(list(documents.items()))
    if result != computed:
        fail("results", "saved figures or decisions disagree with supplied facts; regenerate with kee run")
    return computed
