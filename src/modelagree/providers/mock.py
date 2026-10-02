from .base import ProviderError, Response


class MockProvider:
    def __init__(self, model):
        self.responses = model["responses"]

    def generate(self, request):
        value = self.responses.get(request["item_id"])
        if isinstance(value, str):
            return Response(value)
        if isinstance(value, dict) and isinstance(value.get("text"), str):
            return Response(value["text"], input_tokens=value.get("input_tokens"),
                            output_tokens=value.get("output_tokens"),
                            total_tokens=value.get("total_tokens"))
        raise ProviderError("missing_or_invalid_mock_response")
