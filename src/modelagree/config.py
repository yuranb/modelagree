"""Read and freeze a run's complete offline inputs."""

import hashlib
import itertools
import json
import math
from pathlib import Path

import yaml

from .schema import validate_schema
from .images import image_info
from .security import redact


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                    allow_nan=False).encode()).hexdigest()


def load_dataset(path, limit=None):
    path = Path(path).resolve()
    with path.open(encoding="utf-8") as handle:
        lines = (line for line in handle if line.strip())
        items = [json.loads(line) for line in itertools.islice(lines, limit)]
    seen = set()
    for item in items:
        if not isinstance(item, dict) or not isinstance(item.get("id"), str) or not item["id"]:
            raise ValueError("Every dataset item needs a nonempty string id")
        if item["id"] in seen:
            raise ValueError(f"Duplicate dataset item id: {item['id']}")
        seen.add(item["id"])
        if not isinstance(item.get("text"), str) or not isinstance(item.get("labels", {}), dict):
            raise ValueError("Every item needs text and an optional labels mapping")
        if item.get("image") is not None:
            if not isinstance(item["image"], str) or not item["image"]:
                raise ValueError("image must be a local file path")
            item["image"] = image_info(path.parent / item["image"])
    if not items:
        raise ValueError("Dataset is empty")
    return items


def validate_parameters(provider, parameters):
    keys = {"mock": set(), "openai": {"temperature", "top_p", "max_output_tokens", "reasoning_effort"},
            "gemini": {"temperature", "top_p", "top_k", "max_output_tokens", "seed"}}
    if not isinstance(parameters, dict) or set(parameters) - keys[provider]:
        raise ValueError("Unsupported provider parameters; credentials belong only in the environment")
    for key, value in parameters.items():
        if key == "reasoning_effort":
            if value not in ("none", "minimal", "low", "medium", "high", "xhigh"):
                raise ValueError("Unsupported reasoning_effort")
        elif key in {"max_output_tokens", "top_k", "seed"}:
            if type(value) is not int or value < (0 if key == "seed" else 1):
                raise ValueError(f"{key} must be a {'nonnegative' if key == 'seed' else 'positive'} integer")
        elif type(value) not in (float, int) or not math.isfinite(value):
            raise ValueError(f"{key} must be a finite number")
        elif not 0 <= value <= (2 if key == "temperature" else 1):
            raise ValueError(f"{key} is out of range")


def load_config(path, limit=None):
    if limit is not None and (type(limit) is not int or limit < 1):
        raise ValueError("--limit must be a positive integer")
    path = Path(path).resolve()
    try:
        cfg = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError:
        raise ValueError("Invalid YAML config") from None
    if not isinstance(cfg, dict):
        raise ValueError("Config must be a YAML mapping")
    if set(cfg) - {"dataset", "prompt", "run_dir", "retry_attempts", "label_schema", "models"}:
        raise ValueError("Unsupported config keys; credentials belong only in the environment")
    for key in ("dataset", "prompt"):
        if not isinstance(cfg.get(key), str) or not cfg[key]:
            raise ValueError(f"{key} must be a nonempty file path")
    if "run_dir" in cfg and (not isinstance(cfg["run_dir"], str) or not cfg["run_dir"]):
        raise ValueError("run_dir must be a nonempty directory path")
    base = path.parent
    schema = validate_schema(cfg["label_schema"])
    prompt = (base / cfg["prompt"]).read_text(encoding="utf-8")
    items = load_dataset(base / cfg["dataset"], limit=limit)
    models = cfg.get("models")
    if not isinstance(models, list) or not models:
        raise ValueError("models must be a nonempty list")
    seen = set()
    frozen_models = {}
    for model in models:
        if not isinstance(model, dict):
            raise ValueError("Each model must be a mapping")
        if set(model) - {"id", "provider", "model", "parameters", "responses", "timeout_seconds"}:
            raise ValueError("Unsupported model keys; credentials belong only in the environment")
        mid = model.get("id")
        if not isinstance(mid, str) or not mid or mid in seen:
            raise ValueError("Model ids must be unique nonempty strings")
        seen.add(mid)
        provider = model.get("provider")
        if not isinstance(provider, str) or provider not in {"mock", "openai", "gemini"}:
            raise ValueError("provider must be mock, openai, or gemini")
        if not isinstance(model.get("model"), str) or not model["model"]:
            raise ValueError("Each model needs a model identifier")
        if model["model"].startswith(("REPLACE_", "YOUR_", "<")):
            raise ValueError("Fill in the placeholder provider model IDs before running")
        parameters = model.get("parameters", {})
        validate_parameters(provider, parameters)
        frozen_models[mid] = {"id": mid, "provider": provider, "model": model["model"], "parameters": parameters}
        if provider == "mock":
            if not isinstance(model.get("responses"), str) or not model["responses"]:
                raise ValueError("Mock responses must name a file")
            responses = json.loads((base / model["responses"]).read_text(encoding="utf-8"))
            if not isinstance(responses, dict):
                raise ValueError("Mock responses must map item ids to responses")
            frozen_models[mid]["responses"] = responses
        elif "responses" in model:
            raise ValueError("responses is only supported by the mock provider")
        if provider != "mock" or "timeout_seconds" in model:
            timeout = model.get("timeout_seconds", 60)
            if type(timeout) not in (int, float) or not math.isfinite(timeout) or timeout <= 0:
                raise ValueError("timeout_seconds must be a positive finite number")
            frozen_models[mid]["timeout_seconds"] = timeout
    retry_attempts = cfg.get("retry_attempts", 3)
    if type(retry_attempts) is not int or retry_attempts < 1:
        raise ValueError("retry_attempts must be a positive integer")
    frozen = {"version": 1, "prompt": prompt, "label_schema": schema,
              "items": items, "models": frozen_models, "retry_attempts": retry_attempts}
    if limit is not None:
        frozen["limit"] = limit
    serialized = json.dumps(frozen, ensure_ascii=False, allow_nan=False)
    if redact(serialized) != serialized:
        raise ValueError("Run inputs contain an environment API key; remove it from the inputs")
    run_dir = (base / cfg.get("run_dir", f"runs/{path.stem}")).resolve()
    return frozen, run_dir
