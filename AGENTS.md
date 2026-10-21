# Agent instructions for modelagree

These rules apply to every automated change in this repository. The task list
lives in `docs/codex-plan.md`; work on exactly one task per change unless told
otherwise.

## Commands

```sh
python -m pip install -e '.[test]'
python -m pytest                      # sockets are disabled; must pass
modelagree run examples/demo.yaml     # offline demo; must still work
modelagree score runs/demo > /dev/null && modelagree report runs/demo
```

Run all of the above before declaring a task done. Delete `runs/` afterwards; it
is Git-ignored and must never be committed.

## Invariants (never break these)

1. **Runtime dependencies stay `PyYAML` only.** No numpy, scipy, pandas,
   requests, httpx, or vendor SDKs at runtime. Test-only extras may be added to
   `[project.optional-dependencies].test` when a task says so.
2. **No network in tests.** `pytest-socket` blocks sockets; provider tests mock
   `modelagree.providers.http.open_request` like `tests/test_providers.py` does.
3. **Completed response records are immutable.** Never rewrite, re-request, or
   "repair" a record whose status is `completed` or `permanent_error`.
4. **No label coercion.** Invalid, unknown, duplicate, or missing values are
   invalid; never map them to a default label, lowercase them, or deduplicate.
5. **Explicit denominators.** Every new rate is built with `metrics.ratio()`
   (or has `value`, `numerator`, `denominator`), plus `sample_size` when the
   arithmetic denominator is not an item count. Undefined values are `None`
   with an `undefined_reason` string, never 0 or 1 by convention.
6. **Fingerprint compatibility.** A new config/manifest key must be omitted
   from the frozen dict when it has its default value (see how `limit` is
   handled in `config.load_config`). Existing run directories created by
   0.1.0 must still resume, score, and report.
7. **`scores.json` is additive.** Do not rename, remove, or change the meaning
   of existing keys. New keys are fine. `tests/golden/` (once added) enforces
   this.
8. **Credentials are environment-only.** No API keys in YAML, URLs, logs, error
   messages, or run artifacts. Every new key variable must be added to
   `security.KEY_VARIABLES` so it is redacted.
9. **Report stays a single self-contained HTML file**: no JavaScript, no
   external assets, every dynamic value passed through `report.esc`.
10. **Evaluation purity.** Providers must not enable server-side fallbacks,
    retries on a different model, response caching across items, or anything
    else that could make a different model answer than the one configured.

## Style

- Match the surrounding code: compact functions, few comments, standard
  library only. Do not reformat files you are not otherwise changing.
- Every new metric gets a hand-computed test whose comment shows the
  arithmetic, in the style of `tests/test_metrics.py`. Do not import
  scikit-learn, statsmodels, or krippendorff in tests; hard-code expected
  values you have verified by hand or from a cited published example.
- Code, docs, commit messages, and comments are in English.
- When behaviour or design changes, update `README.md` (or the relevant file
  under `docs/`), `DESIGN.md`, and `CHANGELOG.md` in the same change.
- Do not make claims about other tools in documentation that you cannot cite.
