# Design decisions

**Small Python package.** Python 3.10+, a `src/` layout, setuptools, and one runtime
dependency (PyYAML) keep installation straightforward and prevent accidentally
importing a repository copy instead of the installed package. Providers, parsing,
storage, metrics, reporting, and the CLI are separate small modules.

**One frozen run config.** YAML names the dataset, prompt, schema, models,
parameters, and retry settings. Paths resolve relative to the config so invocation
location does not change inputs. The manifest records input content and a canonical
SHA-256 fingerprint. Resumption compares freshly loaded inputs with that recorded
fingerprint; scoring does not verify the current manifest contents. The same loaded
prompt text is reused for every request, and reference labels are withheld from
providers.

**Stable identities.** Model definitions become an ID-keyed mapping and dataset
IDs must be unique. Provider model names are separate from evaluation IDs, so
parameter variants can coexist. Scoring joins item IDs and enumerates model IDs,
never positions; ID hashes make filesystem paths safe.

**Three independent task types.** Categorical and ordinal values are strings;
ordinal `levels` explicitly define order. Multi-label values are lists of distinct
known strings, with an empty list valid. Schema definitions accept only `type` and
the appropriate `labels` or `levels` option. Each output field is validated
separately so one bad answer does not discard another field's valid answer.

**Provider protocol and offline mock.** A provider accepts one request and returns
text plus optional usage/latency. A file of canned responses implements this same
protocol without networking, making the entire evaluation reproducible without
keys or costs. Missing canned responses are permanent failures, not guesses.

**Auditable records.** One JSON record per model/item stores the request, raw
response text, UTC timestamps, available usage, and attempt history. The runner
saves each completed provider return before label parsing and leaves `parsed` as
a null compatibility placeholder. Scoring derives validity from the saved text.
Unknown usage is null rather than zero. Once durably saved, completed records are
not rewritten or requested again, so invalid output cannot trigger an
accuracy-improving retry. JSON escaping allows otherwise unwritable Unicode
values to be retained in the source text.

**Resumption and concurrency.** A run lock prevents concurrent requests for the
same run. Atomic replacement and file fsync avoid partially written records.
Completed/permanent records are skipped; only retryable infrastructure failures
can be attempted again. A hard crash may leave a lock requiring manual removal;
a crash before a received response is saved cannot guarantee exactly-once remote
execution without server support.

**Restricted retries.** Infrastructure failures such as timeouts, rate limiting,
and server errors receive a bounded number of attempts with capped exponential
backoff. Other errors and invalid model output do not. Attempt histories retain
failures so latency and operational problems remain visible.

**Parsing with format accounting.** A directly supplied JSON object, a fenced
object, or a recoverable object surrounded by prose can provide labels. Fences
and surrounding prose are format violations. Ambiguous multiple objects,
duplicate JSON keys, and nonstandard `NaN`/`Infinity` constants are rejected;
extra fields are flagged. Numeric label values, including exponent overflow
such as `1e999`, remain invalid fields. Invalid parsed values are represented as
null with `valid: false` and an error, while their original spelling remains in
the saved raw response. No missing or invalid field receives a default label or
becomes valid through coercion or deduplication.

Object extraction starts at the first `{` or `[` marker, which must decode as
an object. Thus prefixed arrays, including arrays missing a closing bracket,
cannot supply an inner label object; bracketed prose before an object is also
rejected. The remaining suffix must contain no `{` or `}`. Other suffix text,
including `[]` or `true`, is accepted with the `surrounding_text` flag.

**Explicit denominators.** Primary metrics require valid predictions and known
references for the field. Counts report unknown references, invalid predictions,
and their overlap. Missing responses and provider errors are invalid predictions.
Failure-as-wrong bounds include known-reference failures with zero agreement,
preventing selective model failure from making accuracy look better.

**Categorical and ordinal agreement.** Exact agreement, unweighted Cohen's kappa,
and a reference-by-prediction confusion matrix describe different aspects of
agreement. Kappa exposes chance agreement and its denominator; degenerate cases
are undefined, not assigned 1. Ordinal tasks add counts and rates above, below,
and two or more levels away, preserving the direction and size of errors.

**Multi-label conventions.** Set equality, any overlap, mean Jaccard, and micro-F1
capture strict correctness, partial agreement, and pooled label performance.
Empty/empty Jaccard is 1; any-overlap is 0. Zero-denominator micro-F1 is undefined.
Its failure bound adds one error per vocabulary label per invalid item, equivalent
to the worst-case complement prediction; no default empty prediction is invented.

**Bounds have limits.** Failure-as-wrong agreement rates are separate from
conditional metrics. Kappa and directional errors have no claimed bound because
there is no canonical way to assign their failure labels. Pairwise failure bounds
penalize either side's failure; they are operational scores, not imputed labels.

**Pairwise comparison.** Each model pair is evaluated on the intersection of valid
predictions for the same item IDs, independent of reference availability. Sorted
IDs determine left/right orientation, including ordinal direction and matrix axes.
Invalid-left, invalid-right, and overlap counts expose changing sample coverage.

**Portable report.** Plain escaped HTML and inline CSS produce a single file with
summary and detailed metrics, confusion matrices, format violations, statuses,
and resource totals. No JavaScript or external assets are needed; model-provided
text cannot inject markup. Token and latency totals carry measurement counts and
failed-attempt time remains distinct from completion time.

**Executable examples and tests.** Twelve invented scenarios avoid using real
social-media content. Canned outputs deliberately include failures and disagreements.
Hand-computed examples test every metric; parser, storage, retry, identity, CLI,
and end-to-end checks run with sockets disabled. CI tests Python 3.10, 3.12,
and 3.14 and runs the same offline demo in Docker.

**Deliberate scope.** Local files and a synchronous CLI are sufficient for small
auditable runs. Databases, accounts, web frontends, and job queues would add
operational overhead without advancing this tool's purpose.

**Real providers without SDKs.** Standard-library HTTPS implements the OpenAI
Responses and Gemini generateContent APIs. A small documented parameter allowlist
prevents accidental prompt/model overrides and invalid credential fields. Provider
payloads preserve the same prompt and item text; the label schema validates output
locally rather than silently enabling different schema-enforcement modes per model.
Saved HTTP bodies retain provider finish metadata and usage for later audits.

**Environment-only credentials.** Only `OPENAI_API_KEY` and `GEMINI_API_KEY` provide
authentication. Their values are read at request time and sent in HTTP headers;
the authentication headers are not persisted in run artifacts. Fixed HTTPS
endpoints and rejected redirects restrict where authentication is sent. Config,
model, parameter, and schema option allowlists reject credential options but do
not detect secrets pasted into allowed text values. No `.env` loader is included.

**Redaction trade-off.** HTTP text is checked before JSON decoding, then decoded
strings and object keys are checked again for current environment API-key values.
Every object member is checked before duplicate keys are collapsed. If decoded
redaction finds a match, the retained HTTP envelope is reserialized: whitespace,
escapes, number representations, and duplicate members may change, and redacted
keys can collide. Otherwise the decoded HTTP text is retained. UTF-8 decoding
replaces invalid bytes. This is targeted credential scrubbing, not a general secret
detector: malformed, truncated, or excessively nested JSON gets only literal-text
redaction, and other encodings or secrets not in the current environment are not
covered. Privacy takes precedence over exact envelope fidelity when a match is found.

**Image evidence.** Dataset-relative local image paths resolve independently of
the config location. Fingerprints and per-run image snapshots prevent a changed
file from silently altering a resumed comparison. JPEG, PNG, and WebP are sent
inline, with a conservative 10 MiB cap to bound memory and encoded request size.
Missing or changed images fail explicitly instead of degrading into text-only
evaluation. Scoring works from saved records without original images.

**Limited runs.** `--limit` freezes the first N nonblank dataset records before
loading images; the limit belongs to the run fingerprint. Different limits require
separate output directories, so a quick trial cannot silently change a completed
run's denominator. Dataset ordering remains deterministic and visible.

**CrisisMMD conversion and reference policy.** The standalone script reads a
locally extracted v2.0 copy, original event TSV annotations, and local images. It
does not download or bundle any dataset content. Image informativeness is the
default reference to align with image damage severity; explicit text/agreed modes
record their policy and preserve original labels. No missing severity annotation
is mapped to the lowest level. Per-image IDs avoid collapsing multiple images
from one tweet, and the script does not claim official split membership.

**Converter integrity and provider tests.** Conversion rejects conflicting duplicate
IDs, malformed tables, escaping image paths, and missing images unless explicitly
asked to skip and count missing files. Atomic output avoids half-converted datasets.
Mocked HTTP tests cover both providers, local-image encoding, usage, refusals,
malformed responses, transient/permanent failures, and secret redaction, with
sockets disabled throughout. These tests do not establish live API compatibility.
Converter tests use synthetic TSV rows and test images, not an actual CrisisMMD
archive.

**Known limitations.** The saved manifest is trusted during scoring; its recorded
fingerprint is not verification of its current contents. Git-ignore protection
covers conventional paths, not every configurable output directory. Mocked HTTP
and synthetic TSV tests do not establish live-provider or real-archive
compatibility. See the README's [Known limitations](README.md#known-limitations)
for these boundaries and the output-path examples.
