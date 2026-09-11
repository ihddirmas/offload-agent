from offload.config import Settings, get_settings


def build_model(settings: Settings | None = None):
    """Return a Strands model for the configured provider (bedrock | anthropic | ollama)."""
    settings = settings or get_settings()
    if settings.model_provider == "anthropic":
        from strands.models.anthropic import AnthropicModel

        return AnthropicModel(model_id=settings.anthropic_model_id, max_tokens=2048)
    if settings.model_provider == "ollama":
        from strands.models.ollama import OllamaModel

        return OllamaModel(host=settings.ollama_host, model_id=settings.ollama_model_id)
    from strands.models.bedrock import BedrockModel

    return BedrockModel(model_id=settings.bedrock_model_id)
