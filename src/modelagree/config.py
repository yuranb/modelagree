"""Read and freeze a run's complete offline inputs."""

import hashlib
import json
from pathlib import Path

import yaml

from .schema import validate_schema


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                    allow_nan=False).encode()).hexdigest()


def load_dataset(path):
    with path.open(encoding="utf-8") as handle:
        items = [json.loads(line) for line in handle if line.strip()]
    seen = set()
    for item in items:
        if not isinstance(item, dict) or not isinstance(item.get("id"), str) or not item["id"]:
            raise ValueError("Every dataset item needs a nonempty string id")
        if item["id"] in seen:
            raise ValueError(f"Duplicate dataset item id: {item['id']}")
        seen.add(item["id"])
        if not isinstance(item.get("text"), str) or not isinstance(item.get("labels", {}), dict):
            raise ValueError("Every item needs text and an optional labels mapping")
        if item.get("image"):
            raise ValueError("Image input is not supported by this milestone")
    if not items:
        raise ValueError("Dataset is empty")
    return items


def load_config(path):
    path = Path(path).resolve()
    cfg = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(cfg, dict):
        raise ValueError("Config must be a YAML mapping")
    base = path.parent
    schema = validate_schema(cfg["label_schema"])
    prompt = (base / cfg["prompt"]).read_text(encoding="utf-8")
    items = load_dataset(base / cfg["dataset"])
    models = cfg.get("models")
    if not isinstance(models, list) or not models:
        raise ValueError("models must be a nonempty list")
    seen = set()
    frozen_models = {}
    for model in models:
        if not isinstance(model, dict):
            raise ValueError("Each model must be a mapping")
        mid = model.get("id")
        if not isinstance(mid, str) or not mid or mid in seen:
            raise ValueError("Model ids must be unique nonempty strings")
        seen.add(mid)
        if model.get("provider") != "mock":
            raise ValueError("Only the offline mock provider is supported")
        if not isinstance(model.get("model"), str) or not model["model"]:
            raise ValueError("Each model needs a model identifier")
        parameters = model.get("parameters", {})
        if not isinstance(parameters, dict) or parameters:
            raise ValueError("Mock provider parameters must be an empty mapping")
        responses = json.loads((base / model["responses"]).read_text(encoding="utf-8"))
        if not isinstance(responses, dict):
            raise ValueError("Mock responses must map item ids to responses")
        frozen_models[mid] = {"id": mid, "provider": "mock", "model": model["model"],
                              "parameters": parameters, "responses": responses}
    retry_attempts = cfg.get("retry_attempts", 3)
    if type(retry_attempts) is not int or retry_attempts < 1:
        raise ValueError("retry_attempts must be a positive integer")
    frozen = {"version": 1, "prompt": prompt, "label_schema": schema,
              "items": items, "models": frozen_models, "retry_attempts": retry_attempts}
    run_dir = (base / cfg.get("run_dir", f"runs/{path.stem}")).resolve()
    return frozen, run_dir
