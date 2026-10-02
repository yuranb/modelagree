"""Self-contained HTML, escaped at every data boundary; no remote resources."""
import html
from pathlib import Path

from .scoring import score


def esc(value):
    return html.escape(str(value), quote=True)


def number(value):
    return "undefined" if value is None else f"{value:.4g}"


def metric(value):
    sample = f"; items={value['sample_size']}" if "sample_size" in value else ""
    return f"{number(value['value'])} ({number(value['numerator'])}/{number(value['denominator'])}{sample})"


def table(headers, rows):
    return ("<div class='scroll'><table><thead><tr>" + "".join(f"<th>{esc(h)}</th>" for h in headers)
            + "</tr></thead><tbody>" + "".join("<tr>" + "".join(f"<td>{esc(v)}</td>" for v in row)
                                               + "</tr>" for row in rows) + "</tbody></table></div>")


def _detail(field, values):
    out = f"<h3>{esc(field)}</h3>"
    out += table(["Accounting", "Items"], values["counts"].items())
    out += table(["Metric", "Value (numerator/denominator)", "Failure-as-wrong bound"],
                 [(name, metric(m), metric(values["failure_as_wrong"][name])
                   if name in values["failure_as_wrong"] else "Not defined for this statistic")
                  for name, m in values["metrics"].items()])
    matrix = values.get("confusion_matrix")
    if matrix:
        out += f"<p>Confusion matrix: rows = reference (left model in pairwise); columns = prediction (right). Denominator: {matrix['denominator']} items.</p>"
        out += table(["Reference / prediction", *matrix["labels"]],
                     [[label, *row] for label, row in zip(matrix["labels"], matrix["counts"])])
    return out


def _total_text(value):
    return f"{number(value['total'])} (n={value['denominator']})"


def report(run_dir):
    result = score(run_dir)
    parts = ["<!doctype html><html lang='en'><head><meta charset='utf-8'>",
             "<meta name='viewport' content='width=device-width, initial-scale=1'>",
             "<title>modelagree report</title><style>",
             "body{font:16px system-ui,sans-serif;color:#172536;background:#f7f9fc;margin:2rem auto;max-width:1200px;padding:0 1rem}",
             "h1,h2,h3{line-height:1.2}h2{margin-top:2.5rem}table{border-collapse:collapse;background:white;width:100%;margin:1rem 0}",
             "th,td{text-align:left;padding:.6rem;border:1px solid #ced6df}th{background:#e8eef6}.scroll{overflow-x:auto}p{line-height:1.6}",
             "</style></head><body><h1>modelagree report</h1>",
             f"<p>Frozen run: <code>{esc(result['run_fingerprint'])}</code></p>",
             "<p>Primary metrics exclude unknown references and invalid or absent predictions. Invalid counts include missing responses and provider failures. Unknown and invalid counts may overlap; the overlap is listed. Bounds treat failures as wrong over known references. Pairwise comparisons use the same item IDs, require two valid predictions, and do not depend on reference availability.</p>",
             "<p>Every rate includes its arithmetic denominator. Kappa additionally lists its comparable item count; it is undefined when expected agreement is one. Micro-F1 uses 2TP/(2TP+FP+FN); a failure adds one error per allowed label to its conservative bound. Empty sets have Jaccard 1 and partial overlap 0. All-empty micro-F1 is undefined. Bounds are not defined for kappa or directional error counts.</p>",
             "<h2>Summary</h2>"]
    summary = []
    for mid, model in result["models"].items():
        for field, values in model["fields"].items():
            name = "exact_set_agreement" if values["task_type"] == "multi_label" else "exact_agreement"
            counts = values["counts"]
            summary.append([mid, field, metric(values["metrics"][name]),
                            metric(values["failure_as_wrong"][name]), counts["unknown_reference"],
                            counts["invalid_prediction_known_reference"]])
    parts.append(table(["Model ID", "Field", "Exact agreement", "Failure-as-wrong", "Unknown reference", "Invalid with known reference"], summary))
    parts.append("<h2>Resources and format</h2><p>Totals include only available measurements; n states how many measurements were available. Completion latency excludes failed attempts; attempt latency includes them. Token use of failed HTTP requests is generally unavailable.</p>")
    resources = []
    for mid, model in result["models"].items():
        res = model["resources"]
        resources.append([mid, f"{res['completed']}/{res['items']}",
                          f"{res['format_violations']['responses_with_violations']}/{res['format_violations']['denominator']}",
                          _total_text(res["latency_seconds"]), _total_text(res["attempt_latency_seconds"]),
                          *[_total_text(res["tokens"][k]) for k in ("input_tokens", "output_tokens", "total_tokens")]])
    parts.append(table(["Model ID", "Completed", "Format violations", "Completion seconds", "Attempt seconds", "Input tokens", "Output tokens", "Total tokens"], resources))
    for mid, model in result["models"].items():
        parts.append(f"<h2>Model: {esc(mid)}</h2>")
        parts.append(table(["Format violation", "Count (of completed responses)"],
                           [(k, f"{v}/{model['resources']['completed']}") for k, v in model["resources"]["format_violations"]["by_type"].items()]))
        parts.append(table(["Response status", "Items"], model["resources"]["statuses"].items()))
        parts.extend(_detail(field, values) for field, values in model["fields"].items())
    parts.append("<h2>Pairwise model agreement</h2>")
    for pair in result["pairwise"]:
        parts.append(f"<h2>{esc(pair['left_model_id'])} vs {esc(pair['right_model_id'])}</h2>")
        parts.extend(_detail(field, values) for field, values in pair["fields"].items())
    parts.append("</body></html>")
    path = Path(run_dir) / "report.html"
    path.write_text("\n".join(parts), encoding="utf-8")
    return path
