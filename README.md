# modelagree

[![CI](https://github.com/yuranb/modelagree/actions/workflows/tests.yml/badge.svg?branch=main)](https://github.com/yuranb/modelagree/actions/workflows/tests.yml)

An agreement evaluation tool for researchers using LLMs as annotators, with
explicit statistical denominators and auditable records. MIT licensed; Python 3.10+.

## What questions does it answer?

- How closely do model labels agree with reference labels and with each other?
- How many items have unknown references, invalid predictions, or provider failures?
- How does agreement change when failures count as wrong?
- Which frozen inputs and saved responses produced the results?

## Five-line quickstart

Run these commands from the repository root; the offline demo needs no API key:

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[test]'
modelagree run examples/demo.yaml
modelagree score runs/demo && modelagree report runs/demo
```

## What the report shows

Open `runs/demo/report.html` in a browser. The self-contained HTML report has
no external assets or JavaScript; `runs/demo/scores.json` holds the metrics.
See reference and pairwise agreement, confusion matrices, invalid-output and
response-status counts, and latency/token totals with measurement counts.
The demo's 12 scenarios and both models' responses are synthetic.

<!-- TODO (T4.2): Add the report screenshot at docs/images/report.png.
![Example modelagree report](docs/images/report.png)
-->

## Features

- Categorical, ordinal, and multi-label fields, validated independently.
- Conditional agreement and conservative failure-as-wrong bounds.
- A frozen prompt and manifest, immutable completed records, and resumable runs.
- Offline mock, OpenAI, Gemini, and Anthropic providers; text and local images.
- Local CrisisMMD conversion and `--limit N` for small trials.

## Focus alongside general evaluation frameworks

modelagree focuses on structured annotation agreement: explicit denominators,
visible unknown and invalid counts, failure-as-wrong bounds, and saved evidence
for auditing each evaluation. It uses local files, a synchronous CLI, and a
single HTML report. See [DESIGN.md](DESIGN.md) for implementation choices.

## Documentation

- [Configuration](docs/configuration.md): YAML, dataset records, images, and limits.
- [Run artifacts and resumption](docs/run-artifacts.md): commands, records, development, Docker, and compatibility tests.
- [Metrics and denominators](docs/metrics.md): agreement, bounds, pairwise comparisons, and resource totals.
- [Providers](docs/providers.md): credentials, decoding/redaction, retries, Claude, and macOS TLS troubleshooting.
- [CrisisMMD](docs/crisismmd.md): local conversion and reference-label policies.
- [Changelog](CHANGELOG.md) and [design decisions](DESIGN.md).

## Known limitations

- The manifest fingerprint detects changes to freshly loaded run inputs during
  resumption. Scoring does not recompute it from the current manifest contents,
  so it does not detect manual edits to saved references or other manifest data.
- The shipped Git rules cover conventional data and run directory names. Check
  custom `run_dir` and converter `--output` paths before staging files. Run
  artifacts contain original input data and are not anonymized. Git-ignore
  rules do not protect files that have already been tracked.
- Provider tests use mocked HTTP. They check request construction and response
  handling, not live API or model compatibility.
- Converter tests use synthetic TSV rows and local test images. On 2026-10-21,
  the maintainer ran the CrisisMMD v2.0 converter on a real archive with
  annotations and one event's images, using `--skip-missing-images`.
- In that live check, the `anthropic` provider completed 12/12 and 50/50 requests
  with `claude-haiku-5-5`, with zero format violations in both runs. This was a
  partial check covering one event and its first 50 records. Full-archive
  compatibility and other providers remain unverified.

These examples show which output paths the shipped Git rules ignore:

| Example output | Ignored by shipped Git rules? |
| --- | --- |
| `runs/demo/report.html` | yes |
| `custom-output/report.html` | no |

## License

[MIT](LICENSE).
