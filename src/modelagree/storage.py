import json
import os
import tempfile
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from .config import digest
from .security import redact


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(dir=path.parent, prefix=".tmp-")
    try:
        # Escape lone surrogates as JSON Unicode escapes while preserving other text.
        with os.fdopen(fd, "w", encoding="utf-8", errors="backslashreplace") as handle:
            handle.write(redact(json.dumps(data, indent=2, ensure_ascii=False, allow_nan=False)))
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def response_path(run_dir, model_id, item_id):
    return Path(run_dir) / "responses" / digest(model_id) / f"{digest(item_id)}.json"


@contextmanager
def run_lock(run_dir):
    run_dir = Path(run_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    path = run_dir / ".run.lock"
    try:
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError:
        raise ValueError("Run is locked; remove .run.lock only after confirming no runner is active") from None
    try:
        with os.fdopen(fd, "w") as handle:
            handle.write(str(os.getpid()))
        yield
    finally:
        path.unlink()
