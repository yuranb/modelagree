# CrisisMMD conversion

Run the commands below from the repository root. For provider setup, see
[Providers](providers.md).

Obtain and extract [CrisisMMD v2.0](https://crisisnlp.qcri.org/crisismmd) yourself.
The converter only reads your local copy; it never downloads data. Put the
extracted `CrisisMMD_v2.0/` directory under `data/crisismmd/` or keep it outside
this repository. The shipped Git rules ignore those conventional data paths
and directories named `runs`; arbitrary custom output directories are not
automatically ignored.

```sh
python scripts/prepare_crisismmd.py /absolute/path/to/CrisisMMD_v2.0
# Edit examples/crisismmd.yaml: replace both provider model placeholders.
# Set the two API-key environment variables using your preferred secret manager.
modelagree run examples/crisismmd.yaml --limit 12
modelagree report runs/crisismmd
```

The conversion writes `data/crisismmd/items.jsonl` by default; override it with
`--output PATH`. It reads the original `annotations/*.tsv` tables, resolves
local images under the dataset's `data_image/` directory, and emits one item per
image ID with both tasks:

- `informativeness`: `informative` or `not_informative`, using `image_info` by
  default, matching the supplied image-focused prompt.
- `damage_severity`: `little_or_no_damage` < `mild_damage` < `severe_damage`,
  from `image_damage`. Unannotated damage remains unknown, not “no damage.”

Use `--informativeness-source text` for `text_info`, or `agreed` to require equal,
known text/image labels. Adapt your prompt if you change the reference policy.
The selected policy and original annotation values are saved in item metadata.
These are image-level observations, so text references can repeat when a tweet
has multiple images. The converter combines event annotation files; it does not
claim to reconstruct an official train/dev/test split.

Unknown labels are retained as null references and counted. Exact duplicate IDs
are collapsed; conflicting duplicates are errors. Missing local images fail by
default; `--skip-missing-images` explicitly skips them and prints a count. This
option changes the evaluation population. The converter prints conversion and
unknown-reference counts and writes output atomically. No real CrisisMMD rows or
images are included in this repository; converter tests use invented TSV rows.

On 2026-10-21, the maintainer ran the converter on a real CrisisMMD v2.0 archive
with annotations and one event's images, using `--skip-missing-images`.
The subsequent [partial live provider check](providers.md#partial-live-check)
covered that event's first 50 records; full-archive compatibility remains
unverified.
