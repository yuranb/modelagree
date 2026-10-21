# Changelog

All notable changes to this project will be documented in this file.
The format follows Keep a Changelog.

## [Unreleased]

### Changed

- Recorded the maintainer's 2026-10-21 partial live check: real CrisisMMD v2.0
  conversion with annotations, one event's images, and `--skip-missing-images`;
  Anthropic `claude-haiku-5-5` completed 12/12 and 50/50 requests with zero
  format violations. Scope was limited to one event's first 50 records;
  full-archive compatibility and other providers remain unverified.

### Added

- Anthropic Messages provider with environment-only credentials, text/image
  inputs, required output limits, optional effort, and a Haiku 5.5 CrisisMMD
  example. Refusal and token-limit stops remain immutable completed responses
  but score as invalid; mocked tests cover requests, usage, retries, and redaction.

- Frozen 0.1.0 demo scores and manifest fixtures, with compatibility tests for
  existing score values, run fingerprints, and HTML report generation.
  Additional score keys are allowed; only latency totals are excluded.

## [0.1.0]

### Added

- Frozen, resumable evaluation runs with immutable completed responses,
  environment-only credentials, and redacted artifacts.
- Mock, OpenAI, and Gemini providers with text and local-image inputs.
- Categorical, ordinal, and multi-label agreement metrics with explicit
  denominators, failure-as-wrong bounds, and pairwise comparisons.
- Self-contained HTML reports, an offline synthetic demo, and a local
  CrisisMMD conversion script.
