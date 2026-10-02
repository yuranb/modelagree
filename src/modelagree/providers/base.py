from dataclasses import dataclass
from typing import Protocol


@dataclass
class Response:
    text: str
    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None
    latency_seconds: float | None = None
    raw_http_response: str | None = None
    api_request: dict | None = None


class ProviderError(Exception):
    """Only safe, fixed error codes are persisted, never exception bodies."""

    def __init__(self, code, retryable=False):
        super().__init__(code)
        self.code = code
        self.retryable = retryable


class Provider(Protocol):
    def generate(self, request: dict) -> Response: ...
