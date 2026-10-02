# modelagree

A small, MIT-licensed Python 3.10+ CLI for evaluating structured LLM labels.
Run multiple models on the same labeled dataset with one frozen prompt, keep
all raw response texts, validate each label field independently, and inspect
agreement with references and between models. The offline demo needs no API key.

## Five-line quickstart

Run these commands from the repository root:

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[test]'
modelagree run examples/demo.yaml
modelagree score runs/demo && modelagree report runs/demo
```

Open `runs/demo/report.html` in a browser. It is one self-contained HTML file
with no external assets or JavaScript. `runs/demo/scores.json` contains the
machine-readable metrics. All 12 scenarios and both models' responses in this
demo are synthetic. The canned outputs intentionally include disagreements,
invalid fields, fences, duplicate labels, and missing reference labels.

## Commands

```sh
modelagree run examples/demo.yaml   # also resumes an interrupted run
modelagree score runs/demo          # writes scores.json and prints it
modelagree report runs/demo         # recomputes scores, writes report.html
python -m pytest                   # sockets disabled by default
```

The run command prints its output directory. Individual provider failures are
recorded per item; they do not abort the remaining items. Inspect the report's
response-status counts even when the command exits successfully. Config and
local filesystem errors cause a nonzero exit.

## Config reference

All paths in YAML are relative to the config file. A complete offline example:

```yaml
dataset: demo.jsonl
prompt: prompt.txt
run_dir: ../runs/demo
retry_attempts: 3
label_schema:
  relevance: {type: categorical, labels: [relevant, unrelated]}
  severity: {type: ordinal, levels: [none, minor, major]}
  needs: {type: multi_label, labels: [food, water, shelter]}
models:
  - id: mock-a
    provider: mock
    model: canned-a
    parameters: {}
    responses: mock-a.json
```

| Key | Meaning |
| --- | --- |
| `dataset` | Required UTF-8 JSONL file, one item per line. |
| `prompt` | Required UTF-8 file; its exact contents are reused for every model and item. Write the output field/label instructions here. |
| `run_dir` | Output directory; defaults to `runs/<config-stem>` relative to the config. |
| `retry_attempts` | Positive integer, default 3; maximum attempts per item per invocation after infrastructure failures. |
| `label_schema` | Required mapping of field names to task definitions. |
| `type` | `categorical`, `ordinal`, or `multi_label`. |
| `labels` | Distinct nonempty strings for categorical and multi-label tasks. |
| `levels` | Distinct strings, ordered lowest to highest, for ordinal tasks. |
| `models` | Nonempty list of model definitions. |
| `id` | Unique local evaluation ID; all comparisons and storage use it, never list positions. |
| `provider` | `mock` for canned offline responses. |
| `model` | Provider model ID; separate from the local evaluation ID. |
| `parameters` | Provider options; the mock provider accepts an empty mapping. |
| `responses` | Mock-only JSON file mapping item IDs to response strings or objects with `text`, optional `input_tokens`, `output_tokens`, `total_tokens`. |

Dataset example:

```json
{"id":"item-1","text":"Invented scenario asking for water.","labels":{"relevance":"relevant","severity":"none","needs":["water"]}}
```

Item IDs must be distinct nonempty strings. Text is required. Reference fields
may be missing or null; an unknown or invalid reference is counted and excluded
for that field. Empty multi-label lists are valid. Duplicate labels in a set,
unknown labels, wrong types, and missing fields are invalid predictions; there
are no default labels or coercions.

## Output and resumption

`manifest.json` freezes the prompt, schema, items, model definitions, retry
settings, and mock responses, with a SHA-256 fingerprint. Changing frozen inputs
requires a new `run_dir`; reordering model definitions does not. Under
`responses/<model-ID-hash>/<item-ID-hash>.json`, each record includes readable
IDs, the request, raw response text, parse results, UTC timestamps, measured
latency, available token counts, and attempt history. Hashes make arbitrary
IDs safe as filenames. The request never contains reference labels.

Completed responses—including empty, malformed, or invalid model output—are
never overwritten or requested again. Permanent provider failures are also
retained. Only infrastructure failures are retried, with capped exponential
backoff; exhausted retryable errors can be retried by resuming. Scoring reparses
raw text without modifying response records. A lock prevents concurrent runners
from issuing duplicate requests. After a hard crash, remove `.run.lock` only
once the old process is gone. A crash between receiving and durably saving a
response can require another request; exactly-once remote execution is not
promised.

## Metrics and denominators

Every metric carries its numerator and arithmetic denominator. Conditional
metrics use only items with a valid prediction and known reference. Counts show
unknown references, invalid predictions, their overlap, and eligible items.
Missing responses and provider failures count as invalid predictions. A
failure-as-wrong bound includes all known references and awards failures zero
agreement. Unknown references never enter that bound.

- **Categorical:** exact agreement, unweighted Cohen's kappa, confusion matrix
  (reference rows, prediction columns). Kappa includes its item count and
  `(1 - expected agreement)` denominator; it is undefined with no eligible items
  or expected agreement 1.
- **Ordinal:** categorical metrics plus counts/rates above, below, and at least
  two levels away from the reference, using the declared level order.
- **Multi-label:** exact set agreement, any shared label, mean per-item Jaccard,
  and pooled micro-F1 (`2TP / (2TP + FP + FN)`). Two empty sets have exact/Jaccard
  agreement 1 and overlap 0; micro-F1 with a zero denominator is undefined.
- **Pairwise:** all model pairs, joined on item ID, using valid predictions from
  both models regardless of reference availability. The lexically first model
  is the reference/left side. Its bound counts any invalid side as wrong over
  all selected items; this is an operational failure-as-wrong score rather than
  an estimate of unobserved pairwise agreement.

For the multi-label micro-F1 bound, each failed item contributes as many errors
as there are allowed labels: its worst possible predicted set is the complement
of the true set. This is conservative and avoids treating an invalid response
as an empty set. Kappa and directional errors have no failure-as-wrong bound;
they are reported only on comparable items. Undefined metrics are JSON `null`.

The report includes all metrics, per-model and pairwise matrices, format
violations, status counts, latency totals, and token totals. Every resource total
states how many measurements were available. Failed-request token costs are
usually unknown; attempt latency includes those failures.

## Development and Docker

`python -m pytest` runs all tests with networking blocked by `pytest-socket`.
GitHub Actions runs them on Python 3.10, 3.12, and 3.14 for pushes and PRs.
Runtime dependencies are limited to PyYAML; metrics and reporting use the
standard library.

```sh
docker build -t modelagree .
docker run --rm -v "$PWD/runs:/app/runs" modelagree
```

The image's default command runs and reports on the offline demo. Building the
image installs Python packages; running the demo itself does not use a network.
See [DESIGN.md](DESIGN.md) for the reasoning behind the implementation.
