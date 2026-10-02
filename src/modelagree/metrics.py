"""Dependency-free metrics with explicit sample and arithmetic denominators."""
from .schema import allowed


def ratio(numerator, denominator, *, sample_size=None):
    result = {"value": numerator / denominator if denominator else None,
              "numerator": numerator, "denominator": denominator}
    if sample_size is not None:
        result["sample_size"] = sample_size
    return result


def agreement(pairs, spec, failed=0):
    """Compute metrics on valid pairs, plus bounds counting failures as wrong.

    For micro-F1 an invalid set contributes |vocabulary| errors, the worst
    possible set. Kappa and directional errors remain conditional on valid pairs.
    """
    n = len(pairs)
    full = n + failed
    labels = allowed(spec)
    if spec["type"] == "multi_label":
        sets = [(set(a), set(b)) for a, b in pairs]
        exact = sum(a == b for a, b in sets)
        overlap = sum(bool(a & b) for a, b in sets)
        jaccard = sum(len(a & b) / len(a | b) if a | b else 1.0 for a, b in sets)
        tp = sum(len(a & b) for a, b in sets)
        fp = sum(len(b - a) for a, b in sets)
        fn = sum(len(a - b) for a, b in sets)
        metrics = {"exact_set_agreement": ratio(exact, n),
                   "partial_overlap": ratio(overlap, n),
                   "mean_jaccard": ratio(jaccard, n),
                   "micro_f1": {**ratio(2 * tp, 2 * tp + fp + fn, sample_size=n),
                                "true_positive": tp, "false_positive": fp, "false_negative": fn}}
        lower = {"exact_set_agreement": ratio(exact, full),
                 "partial_overlap": ratio(overlap, full),
                 "mean_jaccard": ratio(jaccard, full),
                 "micro_f1": {**ratio(2 * tp, 2 * tp + fp + fn + failed * len(labels), sample_size=full),
                              "failure_error_count": failed * len(labels)}}
        return {"metrics": metrics, "failure_as_wrong": lower}
    index = {label: i for i, label in enumerate(labels)}
    matrix = [[0 for _ in labels] for _ in labels]
    for ref, pred in pairs:
        matrix[index[ref]][index[pred]] += 1
    exact = sum(matrix[i][i] for i in range(len(labels)))
    rows = [sum(row) for row in matrix]
    cols = [sum(row[i] for row in matrix) for i in range(len(labels))]
    chance = sum(a * b for a, b in zip(rows, cols)) / n ** 2 if n else None
    observed = exact / n if n else None
    denominator = 1 - chance if n else 0
    kappa = {**ratio(observed - chance if n else 0, denominator, sample_size=n),
             "observed_agreement": observed, "expected_agreement": chance,
             "undefined_reason": "no comparable items" if not n else (
                 "expected agreement is one" if not denominator else None)}
    metrics = {"exact_agreement": ratio(exact, n), "cohen_kappa": kappa}
    if spec["type"] == "ordinal":
        differences = [index[pred] - index[ref] for ref, pred in pairs]
        metrics.update(predictions_above=ratio(sum(x > 0 for x in differences), n),
                       predictions_below=ratio(sum(x < 0 for x in differences), n),
                       differences_at_least_two=ratio(sum(abs(x) >= 2 for x in differences), n))
    return {"metrics": metrics, "failure_as_wrong": {"exact_agreement": ratio(exact, full)},
            "confusion_matrix": {"labels": labels, "rows": "reference", "columns": "prediction",
                                 "counts": matrix, "denominator": n}}
