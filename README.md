# KOML Escalation Engine

`kee` decides whether supplied task facts require human intervention under an explicit deterministic policy. CPU only, standard library only, local files only. It makes no network requests or model calls.

Hypothesis: a pure, tested policy engine can reliably identify planted intervention cases and explain every decision. Acceptance requires exact agreement on 200 synthetic records, no false positives, reconciled counts, and a fixture report in under five seconds. Synthetic agreement supports implementation correctness, not policy suitability for real work.

## Quickstart

Python 3.10 or later. From the repository, install using locally available setuptools:

```powershell
python -m pip install --no-deps --no-build-isolation -e .
kee fixtures --out demo
kee run --input demo
kee report --format md
python -m pytest -q
```

On Windows, if pip reports that its Scripts directory is outside PATH, add the reported directory to PATH or use the module invocation below. Installation can be kept offline by adding `--no-index` when setuptools is already available.

The equivalent without installation is `python -m koml_escalation_engine.cli` in place of `kee`. Run and report use `.kee/results.json` by default. No current clock is used in decisions. There is no random generator or seed: the fixtures use fixed enumerated groups.

## Input reference

An input directory contains JSON documents with the following exact schema. JSON is the only accepted input format. CSV and YAML are rejected with a named parse error. `expectations.json` is reserved fixture metadata and is never used by the engine. Empty directories are valid zero-record inputs. Other files are rejected instead of silently skipped.

This five-record example is illustrative synthetic input, not a real trial:

```json
{
  "synthetic": true,
  "entered_by": "fixture-generator",
  "as_of": "2026-09-30",
  "policy": {"retry_limit": 3, "amount_limit_minor": 1000},
  "records": [
    {"id":"a","description":"SYNTHETIC routine","created_on":"2026-09-01","due_on":null,"status":"active","approval_required":false,"retries":0,"amount_minor":100},
    {"id":"b","description":"SYNTHETIC approval","created_on":"2026-09-01","due_on":null,"status":"active","approval_required":true,"retries":0,"amount_minor":100},
    {"id":"c","description":"SYNTHETIC blocked","created_on":"2026-09-01","due_on":null,"status":"blocked","approval_required":false,"retries":0,"amount_minor":100},
    {"id":"d","description":"SYNTHETIC overdue","created_on":"2026-09-01","due_on":"2026-09-29","status":"active","approval_required":false,"retries":0,"amount_minor":100},
    {"id":"e","description":"SYNTHETIC completed","created_on":"2026-09-01","due_on":null,"status":"completed","approval_required":true,"retries":9,"amount_minor":2000}
  ]
}
```

Save as `small/records.json`, then run `kee run --input small`. A separate five-record synthetic example ships at `examples/small/records.json`; run it with `kee run --input examples/small`. This example computes three escalations and 2400 total minor units. These are illustrative input calculations, not measured real-world results.

Real input must declare `synthetic: false` and `entered_by: "Henry"`. Henry enters his own task facts by hand. This declaration is not independently verified. Each report names real and synthetic source files separately. Keep real trial inputs and reports outside the tracked repository.

All fields shown are mandatory, except optional boolean `expected_escalation` for hand-labelled ground truth. Unknown fields are schema errors. IDs must be nonempty strings up to 256 characters and globally unique across files. Descriptions allow Unicode and Windows paths, up to 100000 characters. Booleans must be actual JSON booleans. Amounts and retries must be integers from zero through 10^12; negative, fractional, boolean, and extreme values are rejected. Amounts are minor units in one operator-chosen denomination per run; do not combine currencies. Dates must be valid ISO YYYY-MM-DD. Creation dates after `as_of` are rejected. Future due dates are allowed; due dates before creation are rejected. Retry limit must be positive.

Completed tasks never escalate. Other tasks escalate if any rule matches:

| Reason | Rule |
| --- | --- |
| approval_required | Explicit approval flag is true |
| blocked | Status is blocked |
| overdue | Due date strictly precedes supplied as_of date |
| retry_limit | Retries are at or above policy retry_limit |
| amount_limit | Amount strictly exceeds policy amount_limit_minor |

All matching reasons are recorded. Reason counts overlap, while escalation plus no-intervention counts equal total records. Amount totals include all records, including completed ones. Missing labels do not count toward agreement metrics. False positives and negatives compare decisions with supplied labels only; zero labelled records means zero assessed cases, not proven accuracy. Sources, dates, policies, IDs and reasons appear in report traces or JSON inputs metadata. Each saved decision includes its underlying record facts for audit. Before rendering a saved report, the CLI recomputes decisions and totals from those facts and rejects inconsistent results or savings claims. This checks internal consistency, not authenticity of externally edited facts.

## Commands

| Command | Example | Purpose |
| --- | --- | --- |
| fixtures | `kee fixtures --out demo` | Write 200 synthetic records and expectations |
| run | `kee run --input demo --results .kee/results.json` | Validate and compute all records |
| report | `kee report --format json --out report.json` | Render saved results with provenance |
| triage | `kee triage --input demo` | Show only intervention decisions; summary still covers the complete input |
| explain | `kee explain --input demo --id g1-00` | Show one decision; summary still covers the complete input |

Every subcommand has `--help` with an example. Reports support md and json. Output files replace existing files atomically. CLI exits 2 for named errors: ParseError names file and parse line; SchemaError names file and field (line 1 is a schema location marker, not a parser line); MissingInput gives a usage hint; WriteError names the destination and cleans temporary files. Duplicate IDs across files are rejected. No failed run replaces existing results, so after a failed run an old report may still exist: check the exit code. Fixture generation writes its two files atomically individually, not as a directory transaction.

## Architecture

```text
Local JSON files -> cli.read_input -> core.validate -> core.evaluate
                                                   |
                                                   v
                                    atomic .kee/results.json
                                                   |
                                                   v
                                     report.render -> md / json
fixtures -> records.json + expectations.json (independent oracle)
```

## Honesty boundary and fixture labels

The tool computes only from supplied facts and policy. It does not discover need, predict failure, infer missing facts, or estimate savings. Time or money saved is unmeasured: no measured baseline is supplied, so every report explicitly refuses a savings claim. Hypothetical input examples are labelled illustrative. Runtime measurements are recorded in EVIDENCE.md and apply only to that local run.

JSON does not allow header comments. Every generated fixture JSON therefore has `synthetic: true`; records also say SYNTHETIC in their description and expectations have an explicit synthetic label. No real data ships. Reports always include a provenance banner, even for empty inputs. JSON escapes em dash characters as Unicode escapes, preserving exact input values without emitting that character. Markdown displays ordinary hyphens in their place. Unicode otherwise remains intact.

Ten fixture groups each contain twenty records: routine, approval, blocked, overdue, retry exhausted, amount above limit, all five reasons, completed with all triggers, exact boundaries, routine again. Groups 1 through 6 escalate: 120 total. Each reason appears in two active groups: 40 each. Amount total is `6*20*100 + 3*20*1001 + 20*1000 = 92060`. Expectations are literal hand-computed values, not engine-generated results. Changing task facts changes decisions; corrupting expected labels changes agreement metrics; editing the independent expectations file cannot change decisions.

## Two-week improvement hook and verdict

Start the evidence window on the first real use, not the build date. For fourteen days record run dates, number of tasks, predicted escalations, and Henry's independently hand-checked intervention decisions in a private local trial log. Primary metric is error rate `(false positives + false negatives) / checked records`; report the sample size, and leave error rate unmeasured if no records were checked. Also record days actually used. No real trial results are shipped.

If measured error rate exceeds 10 percent, fix the most frequent false-decision cause and retest, or kill with the recorded reason. If it is unused, record that finding and kill. After fourteen days record one explicit verdict and evidence in a private verdict log: expand for daily use or revenue, integrate for heavy sibling overlap, commercialise for a buyer willing to pay as-is, maintain as portfolio evidence otherwise, kill for no use or unmet acceptance criteria. Build verdict: maintain as portfolio evidence, because the synthetic acceptance criteria pass and real-use effectiveness remains unmeasured. The post-trial verdict is PENDING: the two-week real-use window has not occurred. No commercial or real-world effectiveness claim is made.
