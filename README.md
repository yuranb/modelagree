# modelagree

Run several models with one frozen prompt, preserve their raw responses, and
compare structured labels with a reference dataset. Python 3.10 or later.

Install with `python -m pip install -e .`. The commands are
`modelagree run CONFIG`, `modelagree score RUN_DIR`, and
`modelagree report RUN_DIR`. This first milestone supports the offline mock
provider; more complete examples and metrics follow in subsequent milestones.
