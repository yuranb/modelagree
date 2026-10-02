"""Credentials are environment-only and excluded from serialized artifacts."""
import os

KEY_VARIABLES = ('OPENAI_API_KEY', 'GEMINI_API_KEY')


def redact(text):
    for name in KEY_VARIABLES:
        secret = os.environ.get(name)
        if secret:
            text = text.replace(secret, '[REDACTED_API_KEY]')
    return text


def require_key(name):
    value = os.environ.get(name)
    if not value:
        raise ValueError(f'Set {name} in the environment before starting this provider')
    if any(character.isspace() for character in value):
        raise ValueError(f'{name} must not contain whitespace')
    return value
