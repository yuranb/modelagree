"""Local image fingerprinting and immutable run snapshots."""
import base64
import hashlib
import os
import tempfile
from pathlib import Path

MIMES = {'.jpg':'image/jpeg', '.jpeg':'image/jpeg', '.png':'image/png', '.webp':'image/webp'}
MAX_IMAGE_BYTES = 10 * 1024 * 1024  # Leaves room for base64 and prompt in inline requests.


def image_info(path):
    path=Path(path).resolve()
    mime=MIMES.get(path.suffix.lower())
    if mime is None:
        raise ValueError('Images must be local JPEG, PNG, or WebP files')
    if path.stat().st_size > MAX_IMAGE_BYTES:
        raise ValueError('Image exceeds the 10 MiB inline-input limit')
    data=path.read_bytes()
    if not data:
        raise ValueError('Image file is empty')
    return {'path':str(path),'sha256':hashlib.sha256(data).hexdigest(),'mime_type':mime}


def checked_bytes(info):
    data=Path(info['path']).read_bytes()
    if hashlib.sha256(data).hexdigest() != info['sha256']:
        raise ValueError('Image content changed; use a new run directory')
    return data


def snapshot_image(info, run_dir):
    suffix={v:k for k,v in MIMES.items()}[info['mime_type']]
    destination=Path(run_dir)/'images'/f"{info['sha256']}{suffix}"
    saved={**info,'path':str(destination.resolve())}
    if destination.exists():
        checked_bytes(saved)
        return saved
    data=checked_bytes(info)
    destination.parent.mkdir(parents=True,exist_ok=True)
    fd,temporary=tempfile.mkstemp(dir=destination.parent,prefix='.tmp-')
    try:
        with os.fdopen(fd,'wb') as handle:
            handle.write(data); handle.flush(); os.fsync(handle.fileno())
        os.replace(temporary,destination)
    finally:
        if os.path.exists(temporary): os.unlink(temporary)
    return saved


def encoded_image(info):
    return base64.b64encode(checked_bytes(info)).decode('ascii')
