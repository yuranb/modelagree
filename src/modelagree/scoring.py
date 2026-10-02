"""Reference and pairwise agreement, joined by stable model and item ids."""
import itertools
from collections import Counter
from pathlib import Path

from .metrics import agreement
from .schema import parse_response, validate_value
from .storage import read_json, response_path, write_json


def _prediction(record, field):
    value = (record.get("parsed") or {}).get("fields", {}).get(field, {})
    return value.get("valid", False), value.get("value")


def _total(values):
    known = [x for x in values if isinstance(x, (int, float)) and not isinstance(x, bool)]
    return {"total": sum(known) if known else None, "denominator": len(known)}


def _resources(records):
    completed = [r for r in records if r.get("status") == "completed"]
    violations = Counter(v for r in completed for v in r["parsed"]["format_violations"])
    return {"items": len(records), "completed": len(completed),
            "statuses": dict(Counter(r.get("status", "not_requested") for r in records)),
            "format_violations": {"responses_with_violations": sum(bool(r["parsed"]["format_violations"]) for r in completed),
                                  "denominator": len(completed), "by_type": dict(violations)},
            "latency_seconds": _total(r.get("latency_seconds") for r in completed),
            "attempt_latency_seconds": _total(a.get("latency_seconds") for r in records for a in r.get("attempts", [])),
            "tokens": {k: _total((r.get("usage") or {}).get(k) for r in completed)
                       for k in ("input_tokens", "output_tokens", "total_tokens")}}


def score(run_dir):
    run_dir = Path(run_dir)
    manifest = read_json(run_dir / "manifest.json")
    schema = manifest["label_schema"]
    items = manifest["items"]
    records = {}
    for mid in sorted(manifest["models"]):
        records[mid] = {}
        for item in items:
            path = response_path(run_dir, mid, item["id"])
            rec = read_json(path) if path.exists() else {}
            if rec and (rec["model_id"] != mid or rec["item_id"] != item["id"]):
                raise ValueError("Response identity does not match its storage path")
            rec["parsed"] = parse_response(rec["raw_response"], schema) if rec.get("status") == "completed" else None
            records[mid][item["id"]] = rec
    models = {}
    for mid, by_item in records.items():
        fields = {}
        for field, spec in schema.items():
            pairs = []
            unknown = invalid = invalid_known = 0
            for item in items:
                ref = item.get("labels", {}).get(field)
                known = validate_value(ref, spec) is None
                valid, value = _prediction(by_item[item["id"]], field)
                unknown += not known
                invalid += not valid
                invalid_known += known and not valid
                if known and valid:
                    pairs.append((ref, value))
            counts = {"total": len(items), "known_reference": len(items) - unknown,
                      "unknown_reference": unknown, "invalid_prediction": invalid,
                      "invalid_prediction_known_reference": invalid_known,
                      "invalid_prediction_unknown_reference": invalid - invalid_known,
                      "eligible": len(pairs)}
            fields[field] = {"task_type": spec["type"], "counts": counts,
                             **agreement(pairs, spec, failed=invalid_known)}
        models[mid] = {"fields": fields, "resources": _resources(list(by_item.values()))}
    pairwise = []
    for left, right in itertools.combinations(sorted(records), 2):
        fields = {}
        for field, spec in schema.items():
            pairs = []
            invalid_left = invalid_right = both_invalid = 0
            for item in items:
                a_valid, a = _prediction(records[left][item["id"]], field)
                b_valid, b = _prediction(records[right][item["id"]], field)
                invalid_left += not a_valid
                invalid_right += not b_valid
                both_invalid += not a_valid and not b_valid
                if a_valid and b_valid:
                    pairs.append((a, b))
            fields[field] = {"task_type": spec["type"],
                             "counts": {"total": len(items), "eligible": len(pairs),
                                        "invalid_left": invalid_left, "invalid_right": invalid_right,
                                        "both_invalid": both_invalid, "either_invalid": len(items) - len(pairs)},
                             **agreement(pairs, spec, failed=len(items) - len(pairs))}
        pairwise.append({"left_model_id": left, "right_model_id": right, "fields": fields})
    result = {"version": 1, "run_fingerprint": manifest["fingerprint"],
              "models": models, "pairwise": pairwise}
    write_json(run_dir / "scores.json", result)
    return result
