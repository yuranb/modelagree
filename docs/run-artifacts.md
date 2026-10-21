# Run artifacts and resumption

## Overview

A small, MIT-licensed Python 3.10+ CLI for evaluating structured LLM labels.
Run multiple models on the same labeled dataset with one frozen prompt, retain
response text, validate each label field independently, and inspect agreement
with references and between models. Retention follows the decoding and credential
redaction rules in [Providers](providers.md#credentials-and-response-handling). The offline demo needs no API key.

## Offline demo

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
modelagree --version               # prints the installed modelagree version
modelagree run examples/demo.yaml   # also resumes an interrupted run
modelagree score runs/demo          # writes scores.json and prints it
modelagree report runs/demo         # recomputes scores, writes report.html
python -m pytest                   # sockets disabled by default
```

The run command prints its output directory. Individual provider failures are
recorded per item; they do not abort the remaining items. Inspect the report's
response-status counts even when the command exits successfully. Config and
local filesystem errors cause a nonzero exit.

## Output and resumption

`manifest.json` records the prompt, schema, items, model definitions, retry
settings, and mock responses, with a SHA-256 fingerprint. Resuming compares
freshly loaded inputs with the recorded fingerprint; changing those inputs
requires a new `run_dir`, while reordering model definitions does not. This
check does not verify the current contents of the saved manifest.

Under `responses/<model-ID-hash>/<item-ID-hash>.json`, each record includes
readable IDs, the request, raw response text, UTC timestamps, measured latency,
available token counts, and attempt history. Hashes make arbitrary IDs safe as
filenames. Requests omit the item's reference labels. The `parsed` field is a
compatibility placeholder (`null`); scoring derives field validity from the
saved response text.

Real-provider records also retain the HTTP request body and decoded HTTP
response text, including refusals, truncation metadata, and responses with no
generated text. Authentication headers are not copied into saved request
records. These artifacts are not a byte-for-byte archive of the HTTP exchange;
see the [decoding and redaction rules](providers.md#credentials-and-response-handling).

The runner saves a completed provider return before label parsing. Once that
completed record is durably saved, it is neither overwritten nor requested
again, including when the text is empty, malformed, or contains invalid labels.
The provider has already decoded its HTTP envelope and applied credential
redaction before returning to the runner. Scoring and reporting parse saved
text without changing response records.

Permanent provider failures are retained. Only infrastructure failures are
retried, with capped exponential backoff; exhausted retryable errors can be
retried by resuming. A lock prevents concurrent runners from issuing duplicate
requests. After a hard crash, remove `.run.lock` only once the old process is
gone. A crash or storage failure before the completed record is durably saved
can require another request; exactly-once remote execution is not promised.

## Development

`python -m pytest` runs all tests with networking blocked by `pytest-socket`.
GitHub Actions runs them on Python 3.10, 3.12, and 3.14 for pushes and PRs.
Runtime dependencies are limited to PyYAML; metrics and reporting use the
standard library.

Install the optional development tools and run the same lint check as CI:

```sh
python -m pip install -e '.[dev]'
ruff check src tests scripts
```

Ruff enables only `E9`, `F63`, `F7`, `F82`, and `F401`; this check does not
format files. `modelagree --version` prints `modelagree 0.1.0`, sourced from
`modelagree.__version__`. A test checks it against `pyproject.toml`.

## Docker demo

```sh
docker build -t modelagree .
docker run --rm -v "$PWD/runs:/app/runs" modelagree
```

The image's default command runs and reports on the offline demo. Building the
image installs Python packages; running the demo itself does not use a network.
See [DESIGN.md](../DESIGN.md) for the reasoning behind the implementation.

## Compatibility tests

`python -m pytest` checks the offline demo against frozen 0.1.0 scores and
requires the same run fingerprint. New score keys are allowed, but existing
values and list order must remain compatible; only the two resource latency
totals are excluded. A saved 0.1.0 manifest also exercises report generation.
See [CHANGELOG.md](../CHANGELOG.md) for changes.
