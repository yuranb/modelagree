# Design decisions

**Small Python package.** Python 3.10+, a `src/` layout, setuptools, and one runtime
dependency (PyYAML) keep installation straightforward and prevent accidentally
importing a repository copy instead of the installed package. Providers, parsing,
storage, metrics, reporting, and the CLI are separate small modules.

**One frozen run config.** YAML names the dataset, prompt, schema, models,
parameters, and retry settings. Paths resolve relative to the config so invocation
location does not change inputs. The manifest stores input content and a canonical
SHA-256 fingerprint; changed inputs require another directory, preserving the
meaning of a comparison. The prompt is reused verbatim and labels are withheld
from provider requests.

**Stable identities.** Model definitions become an ID-keyed mapping and dataset
IDs must be unique. Provider model names are separate from evaluation IDs, so
parameter variants can coexist. Scoring joins item IDs and enumerates model IDs,
never positions; ID hashes make filesystem paths safe.

**Three independent task types.** Categorical and ordinal values are strings;
ordinal `levels` explicitly define order. Multi-label values are lists of distinct
known strings, with an empty list valid. Each schema field is validated separately
so one bad answer does not discard another field's valid answer.

**Provider protocol and offline mock.** A provider accepts one request and returns
text plus optional usage/latency. A file of canned responses implements this same
protocol without networking, making the entire evaluation reproducible without
keys or costs. Missing canned responses are permanent failures, not guesses.

**Auditable records.** One JSON record per model/item stores the request, raw text,
parse result, UTC timestamps, available usage, and attempt history. Unknown usage
is null rather than zero. Completed responses are immutable, including invalid
output, so retrying cannot silently improve measured accuracy.

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

**Strict parsing with format accounting.** The parser extracts one JSON object;
a fence or surrounding prose is flagged even if fields are usable. It rejects
ambiguous multiple objects, malformed JSON, duplicate keys, and non-finite
numbers. Extra fields are flagged. Missing or invalid values are never filled,
coerced, or deduplicated into valid labels.

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
and end-to-end checks run with sockets disabled. CI covers supported Python
versions and Docker runs the same offline demo.

**Deliberate scope.** Local files and a synchronous CLI are sufficient for small
auditable runs. Databases, accounts, web frontends, and job queues would add
operational overhead without advancing this tool's purpose.
