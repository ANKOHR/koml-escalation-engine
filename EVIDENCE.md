# Local build evidence

Measured on 1 October 2026 with Python 3.12 on this Windows CPU host.

- pytest: 32 passed in 1.04 seconds.
- Installed kee executable: fixtures, run, report completed in 0.592691 seconds total, below the five-second acceptance limit.
- 200 synthetic records: 120 escalations, 80 no-intervention decisions.
- Each of five reasons: 40 cases. Reasons overlap.
- Supplied label agreement: 120 true positives, zero false positives, zero false negatives.
- Amount total: 92060 input minor units, reconciled against the independent hand-computed oracle.
- Regression tests change task facts and supplied labels, proving outputs are computed.
- Repeated results and reports are byte-identical. Empty, malformed, Unicode, long and adversarial inputs are covered.
- Saved report inconsistencies and unsupported savings claims are rejected.

These measurements concern synthetic implementation correctness and local runtime. Real accuracy, time saved, money saved and commercial demand remain unmeasured. No real-use trial has occurred.

Build verdict: maintain as portfolio evidence. Record the final evidence-based verdict after fourteen days of actual use, as specified in README.md.
