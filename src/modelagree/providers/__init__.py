from .mock import MockProvider


def create_provider(model):
    if model["provider"] == "mock":
        return MockProvider(model)
    if model["provider"] == "openai":
        from .openai import OpenAIProvider
        return OpenAIProvider(model)
    if model["provider"] == "gemini":
        from .gemini import GeminiProvider
        return GeminiProvider(model)
    raise ValueError("Unsupported provider")
