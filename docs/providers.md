# Real providers

## Credentials and response handling

No real API calls are made by the tests or the demo. Authentication reads
`GEMINI_API_KEY`, `OPENAI_API_KEY`, and `ANTHROPIC_API_KEY` only from the process environment.
Config, model, provider-parameter, and schema definitions reject unsupported
options, including credential options. `.env` is ignored by Git and is not
loaded by the program.

Authentication values are sent in HTTP headers to fixed provider endpoints;
those headers are not persisted in run artifacts, and redirects are rejected.
Provider error records contain fixed codes rather than HTTP error bodies or
exception details.

Successful HTTP bodies are decoded as UTF-8; invalid byte sequences are replaced.
Literal current environment API-key values are replaced with
`[REDACTED_API_KEY]` before JSON decoding. For a parseable JSON envelope, decoded
strings and keys are checked too, including strings in nested lists and a scalar
root. Every object member is checked before duplicate keys can overwrite it.
If decoded redaction finds an additional match, the saved HTTP envelope is
reserialized from its redacted representation. Reserialization can change
whitespace, escapes, number representations, and duplicate members; redacted
keys can collide. Otherwise the decoded HTTP text, with any literal redactions,
is retained.

Malformed, truncated, or excessively nested JSON receives only literal-text
redaction. This targeted check does not detect other encodings or secrets absent
from the current environment. Decoding and redaction can both change retained
text; exact HTTP-envelope fidelity is sacrificed when redaction requires it.

Only timeouts, connection failures, HTTP 408/429, and HTTP 5xx are retried.
TLS verification failures and other HTTP errors are permanent. Once successfully
saved, HTTP 200 responses with unusable, missing, refused, or malformed model
output are retained and scored as invalid where applicable. The transport uses
normal TLS verification and supports the standard `SSL_CERT_FILE` mechanism if
your system needs a custom trust store. It never disables certificate checks.

Gemini's `output_tokens` records `candidatesTokenCount`; `total_tokens` records
`totalTokenCount`, which can include thinking tokens, so input plus output need
not equal total. Usage metadata remains in the saved HTTP body, subject to
credential redaction.
The adapters follow the official [OpenAI Responses reference](https://developers.openai.com/api/reference/cli/resources/responses/methods/create),
[OpenAI image-input guide](https://developers.openai.com/api/docs/guides/images-vision),
and [Gemini generateContent reference](https://ai.google.dev/api/generate-content).

### Anthropic / Claude Haiku 5.5

Use `provider: anthropic` with `ANTHROPIC_API_KEY` set in the environment.
The adapter sends text followed by any image to the fixed Messages endpoint,
with the frozen prompt as `system` and API version `2023-06-01`. It does not
send thinking overrides, fallback options, or cache controls.

The target model is `claude-haiku-5-5`. For prompts up to 100,000 tokens,
its price is $0.10 per million input tokens and $0.50 per million output tokens.
Adaptive thinking is on by default and effort defaults to `medium`; thinking
tokens count toward `max_tokens` and output charges. For classification, start
with `effort: low` and `max_output_tokens: 2048`. The output limit is required;
there is no implicit default. `temperature`, `top_p`, and `top_k` are rejected
by local configuration validation because Haiku 5.5 rejects non-default
sampling settings with HTTP 400. See the official
[Haiku 5.5 overview](https://platform.claude.com/docs/en/models/haiku-5-5/overview)
and [migration guide](https://platform.claude.com/docs/en/models/haiku-5-5/migration-guide).

All text blocks are concatenated; thinking and other block types are skipped.
Input and output usage are recorded directly, while `total_tokens` stays null
because the API does not supply it. The saved HTTP envelope retains
`stop_reason`. A `refusal` or `max_tokens` stop is saved as `completed` and
scored as invalid for every field, even if its text is parseable JSON. These
failures contribute to failure-as-wrong bounds and are not retried. Haiku 5.5
has no server-side refusal fallback. For `max_tokens`, increase
`max_output_tokens` and use a new `run_dir`; completed records stay immutable.

After preparing your local CrisisMMD dataset, run
`modelagree run examples/crisismmd-claude.yaml`. This example uses only Haiku
with a 60-second timeout. Tests use mocked HTTP and do not establish live API
compatibility.

## Troubleshooting

On macOS with the python.org installer, missing trusted root certificates can
cause every request to fail immediately with `tls_error`. Run
`Install Certificates.command` in the matching `/Applications/Python 3.x/`
folder; see the [Python installation instructions](https://docs.python.org/3/using/mac.html#installation-steps).
Alternatively, activate your environment and point `SSL_CERT_FILE` at a certifi
CA bundle:

```sh
python -m pip install certifi
export SSL_CERT_FILE="$(python -m certifi)"
```

Certifi is an optional local certificate setup aid, not a modelagree runtime
dependency. Keep this variable set in the shell used to run modelagree.
After fixing certificate trust, set a new `run_dir` in your config and rerun
with the same `--limit`, if any: `tls_error` records are permanent errors and
are not retried when resuming the old directory. Keep TLS verification enabled.
