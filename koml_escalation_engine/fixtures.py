"""Synthetic fixtures with hand-computed group expectations. No randomness."""


def fixture_document():
    records = []
    for group in range(10):
        for index in range(20):
            record = {"id": f"g{group}-{index:02}", "description": "SYNTHETIC fixture task", "created_on": "2026-09-01", "due_on": "2026-10-01", "status": "active", "approval_required": False, "retries": 0, "amount_minor": 100, "expected_escalation": group in (1, 2, 3, 4, 5, 6)}
            if group in (1, 6, 7):
                record["approval_required"] = True
            if group in (2, 6, 7):
                record["status"] = "blocked"
            if group in (3, 6, 7):
                record["due_on"] = "2026-09-29"
            if group in (4, 6, 7):
                record["retries"] = 3
            if group in (5, 6, 7):
                record["amount_minor"] = 1001
            if group == 7:
                record["status"] = "completed"
            if group == 8:
                record.update(retries=2, amount_minor=1000, due_on="2026-09-30")
            records.append(record)
    return {"synthetic": True, "entered_by": "fixture-generator", "as_of": "2026-09-30", "policy": {"retry_limit": 3, "amount_limit_minor": 1000}, "records": records}


def expectations():
    # Ten groups of twenty. Groups 1..6 escalate; group 7 is completed.
    # Amount total: 6*20*100 + 3*20*1001 + 20*1000 = 92060.
    return {"synthetic": True, "label": "SYNTHETIC hand-computed ground truth", "summary": {"records": 200, "escalations": 120, "no_intervention": 80, "amount_minor_total": 92060, "reason_counts": {"approval_required": 40, "blocked": 40, "overdue": 40, "retry_limit": 40, "amount_limit": 40}, "labelled_records": 200, "true_positives": 120, "false_positives": 0, "false_negatives": 0}}
