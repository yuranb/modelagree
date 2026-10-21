# Configuration

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
| `prompt` | Required UTF-8 file; its loaded text is reused for every model and item. Write the output field/label instructions here. |
| `run_dir` | Output directory; defaults to `runs/<config-stem>` relative to the config. |
| `retry_attempts` | Positive integer, default 3; maximum attempts per item per invocation after infrastructure failures. |
| `label_schema` | Required mapping of field names to task definitions. |
| `type` | `categorical`, `ordinal`, or `multi_label`. |
| `labels` | Distinct nonempty strings for categorical and multi-label tasks. |
| `levels` | Distinct strings, ordered lowest to highest, for ordinal tasks. |
| `models` | Nonempty list of model definitions. |
| `id` | Unique local evaluation ID; all comparisons and storage use it, never list positions. |
| `provider` | `mock`, `openai` (Responses API), `gemini` (generateContent API), or `anthropic` (Messages API). |
| `model` | Provider model ID; separate from the local evaluation ID. |
| `parameters` | Provider options; the mock provider accepts an empty mapping. |
| `responses` | Mock-only JSON file mapping item IDs to response strings or objects with `text`, optional `input_tokens`, `output_tokens`, `total_tokens`. |

`timeout_seconds` is an optional positive model-level request timeout (default
60). Supported options in `parameters` are:

| Provider | Parameters |
| --- | --- |
| `openai` | `temperature`, `top_p`, `max_output_tokens`, `reasoning_effort` |
| `gemini` | `temperature`, `top_p`, `top_k`, `max_output_tokens`, `seed` |
| `anthropic` | `max_output_tokens` (required), `effort` |

Omitted optional parameters use provider defaults; model-specific support still applies.
Anthropic requires a positive integer `max_output_tokens` and accepts only
`effort: low|medium|high|xhigh|max` as an additional parameter.
`reasoning_effort` accepts `none`, `minimal`, `low`, `medium`, `high`, or `xhigh`;
choose a value supported by your model. Temperature must be in [0, 2], top-p in
[0, 1], seed a nonnegative integer, and token/top-k limits positive integers.
Unknown provider options are rejected. Each schema definition accepts only
`type` and its task's `labels` or `levels`; extra options are rejected there too.
Authentication has no YAML option. These checks do not detect arbitrary secrets
pasted into allowed text values.

Dataset example:

```json
{"id":"item-1","text":"Invented scenario asking for water.","labels":{"relevance":"relevant","severity":"none","needs":["water"]}}
```

Item IDs must be distinct nonempty strings. Text is required. Reference fields
may be missing or null; an unknown or invalid reference is counted and excluded
for that field. Empty multi-label lists are valid. Duplicate labels in a set,
unknown labels, wrong types, and missing fields are invalid predictions; there
are no default labels or coercions.

An item may also have `"image":"images/example.jpg"`, resolved relative to the
dataset file (not the YAML). Local JPEG, PNG, and WebP images up to 10 MiB are
supported. Each selected image is fingerprinted, snapshotted under the run's
`images/` directory when requested, and sent inline. Image bytes are checked
against their fingerprint before sending. Keep the original inputs available
when resuming; scoring and reporting only need the run directory.

`modelagree run CONFIG --limit N` selects the first N nonblank JSONL records
before image loading. The limit is part of the frozen run definition: resume
with the same limit, and use a new `run_dir` for a different limit or an unlimited
run. No labels are used for selection and item order is not randomized.
