# Metrics and denominators

Every metric carries its numerator and arithmetic denominator. Conditional
metrics use only items with a valid prediction and known reference. Counts show
unknown references, invalid predictions, their overlap, and eligible items.
Missing responses and provider failures count as invalid predictions. A
failure-as-wrong bound includes all known references and awards failures zero
agreement. Unknown references never enter that bound.

- **Categorical:** exact agreement, unweighted Cohen's kappa, confusion matrix
  (reference rows, prediction columns). Kappa includes its item count and
  `(1 - expected agreement)` denominator; it is undefined with no eligible items
  or expected agreement 1.
- **Ordinal:** categorical metrics plus counts/rates above, below, and at least
  two levels away from the reference, using the declared level order.
- **Multi-label:** exact set agreement, any shared label, mean per-item Jaccard,
  and pooled micro-F1 (`2TP / (2TP + FP + FN)`). Two empty sets have exact/Jaccard
  agreement 1 and overlap 0; micro-F1 with a zero denominator is undefined.
- **Pairwise:** all model pairs, joined on item ID, using valid predictions from
  both models regardless of reference availability. The lexically first model
  is the reference/left side. Its bound counts any invalid side as wrong over
  all selected items; this is an operational failure-as-wrong score rather than
  an estimate of unobserved pairwise agreement.

For the multi-label micro-F1 bound, each failed item contributes as many errors
as there are allowed labels: its worst possible predicted set is the complement
of the true set. This is conservative and avoids treating an invalid response
as an empty set. Kappa and directional errors have no failure-as-wrong bound;
they are reported only on comparable items. Undefined metrics are JSON `null`.

The report includes all metrics, per-model and pairwise matrices, format
violations, status counts, latency totals, and token totals. Every resource total
states how many measurements were available. Failed-request token costs are
usually unknown; attempt latency includes those failures.
