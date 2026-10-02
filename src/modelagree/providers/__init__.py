from .mock import MockProvider


def create_provider(model):
    if model["provider"] == "mock":
        return MockProvider(model)
    raise ValueError("Unsupported provider")
