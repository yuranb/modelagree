import time
from dataclasses import asdict

from .config import digest, load_config
from .providers import create_provider
from .providers.base import ProviderError
from .schema import parse_response
from .storage import read_json, response_path, run_lock, utc_now, write_json


def run(config_path):
    frozen, run_dir = load_config(config_path)
    with run_lock(run_dir):
        manifest_path = run_dir / "manifest.json"
        fingerprint = digest(frozen)
        if manifest_path.exists():
            manifest = read_json(manifest_path)
            if manifest["fingerprint"] != fingerprint:
                raise ValueError("Frozen run inputs changed; use a new run_dir")
        else:
            write_json(manifest_path, {**frozen, "fingerprint": fingerprint, "created_at": utc_now()})
        for model_id, model in frozen["models"].items():
            provider = create_provider(model)
            for item in frozen["items"]:
                path = response_path(run_dir, model_id, item["id"])
                previous = read_json(path) if path.exists() else {}
                if previous.get("status") in {"completed", "permanent_error"}:
                    continue
                request = {"model_id": model_id, "provider": model["provider"], "model": model["model"],
                           "parameters": model["parameters"], "prompt": frozen["prompt"],
                           "item_id": item["id"], "text": item["text"], "label_schema": frozen["label_schema"]}
                record = {"model_id": model_id, "item_id": item["id"], "request": request,
                          "attempts": previous.get("attempts", []), "raw_response": None,
                          "parsed": None, "usage": None, "latency_seconds": None}
                for attempt in range(frozen["retry_attempts"]):
                    started_at = utc_now()
                    start = time.perf_counter()
                    try:
                        response = provider.generate(request)
                    except ProviderError as exc:
                        record.update(status="retryable_error" if exc.retryable else "permanent_error")
                        record["attempts"].append({"started_at": started_at, "finished_at": utc_now(),
                                                    "latency_seconds": time.perf_counter() - start,
                                                    "error": exc.code, "retryable": exc.retryable})
                        write_json(path, record)
                        if not exc.retryable:
                            break
                        if attempt + 1 < frozen["retry_attempts"]:
                            time.sleep(min(2 ** attempt, 8))
                        continue
                    elapsed = time.perf_counter() - start
                    finished_at = utc_now()
                    values = asdict(response)
                    record.update(status="completed", raw_response=response.text,
                                  started_at=started_at, finished_at=finished_at,
                                  latency_seconds=response.latency_seconds if response.latency_seconds is not None else elapsed,
                                  usage={k: values[k] for k in ("input_tokens", "output_tokens", "total_tokens")},
                                  parsed=parse_response(response.text, frozen["label_schema"]))
                    record["attempts"].append({"started_at": started_at, "finished_at": finished_at,
                                                "latency_seconds": elapsed, "error": None})
                    write_json(path, record)
                    break
    return run_dir
