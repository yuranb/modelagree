"""Basic field-level accounting; full agreement statistics arrive in M2."""

from pathlib import Path

from .schema import validate_value
from .storage import read_json, response_path, write_json


def score(run_dir):
    run_dir = Path(run_dir)
    manifest = read_json(run_dir / "manifest.json")
    models = {}
    for mid in manifest["models"]:
        fields = {}
        for field, spec in manifest["label_schema"].items():
            valid = correct = unknown = invalid = 0
            for item in manifest["items"]:
                path = response_path(run_dir, mid, item["id"])
                rec = read_json(path) if path.exists() else {}
                ref = item.get("labels", {}).get(field)
                pred = (rec.get("parsed") or {}).get("fields", {}).get(field, {})
                if validate_value(ref, spec):
                    unknown += 1
                elif not pred.get("valid", False):
                    invalid += 1
                else:
                    valid += 1
                    value = pred["value"]
                    correct += (set(value) == set(ref)) if spec["type"] == "multi_label" else value == ref
            fields[field] = {"eligible": valid, "unknown_reference": unknown,
                             "invalid_prediction_known_reference": invalid,
                             "exact_agreement": {"numerator": correct, "denominator": valid,
                                                 "value": correct / valid if valid else None}}
        models[mid] = fields
    result = {"models": models}
    write_json(run_dir / "scores.json", result)
    return result
