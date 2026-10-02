"""Credentials are environment-only and excluded from serialized artifacts."""
import json
import os

KEY_VARIABLES = ('OPENAI_API_KEY', 'GEMINI_API_KEY')


def redact(text):
    for name in KEY_VARIABLES:
        secret = os.environ.get(name)
        if secret:
            text = text.replace(secret, '[REDACTED_API_KEY]')
    return text


def decode_redacted_json(text):
    """Scrub literal and JSON-escaped credentials, retaining text when possible."""
    raw = redact(text)
    changed = False

    def scrub(value):
        nonlocal changed
        if isinstance(value, str):
            clean = redact(value)
            changed |= clean != value
            return clean
        if isinstance(value, list):
            return [scrub(item) for item in value]
        # Object hooks already scrubbed nested dictionaries, bottom-up.
        return value

    def object_pairs(pairs):
        # Check every member before duplicate keys can overwrite a secret.
        return {scrub(key): scrub(value) for key, value in pairs}

    try:
        data = scrub(json.loads(raw, object_pairs_hook=object_pairs))
    except (ValueError, RecursionError):
        return {}, raw
    if changed:
        raw = json.dumps(data, ensure_ascii=True)
    return data, raw


def require_key(name):
    value = os.environ.get(name)
    if not value:
        raise ValueError(f'Set {name} in the environment before starting this provider')
    if any(character.isspace() for character in value):
        raise ValueError(f'{name} must not contain whitespace')
    return value
