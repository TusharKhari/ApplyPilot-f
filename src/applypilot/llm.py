"""Model name normalization and provider detection for ApplyPilot agent runners."""
from __future__ import annotations

_MODEL_ALIASES: dict[str, str] = {
    "deepseek-v4.1-flash": "deepseek-flash",
    "deepseek-v4-flash": "deepseek-flash",
    "deepseek-v4.1": "deepseek-flash",
    "kimi-k3": "moonshotai/kimi-k3",
    "kimi": "moonshotai/kimi-k3",
    "kimi_k3": "moonshotai/kimi-k3",
    "moonshot-kimi-k3": "moonshotai/kimi-k3",
    "kimi-k2.5": "moonshotai/kimi-k2.5",
    "kimi-k2-5": "moonshotai/kimi-k2.5",
    "nemotron-3.5-lightning-30b-a3b": "nvidia/nemotron-3.5-lightning-30b-a3b",
    "nemotron-3.5-lightning": "nvidia/nemotron-3.5-lightning-30b-a3b",
    "nemotron-3.5": "nvidia/nemotron-3.5-lightning-30b-a3b",
    "nemotron": "nvidia/nemotron-3.5-lightning-30b-a3b",
    "nemotron-lightning": "nvidia/nemotron-3.5-lightning-30b-a3b",
}


def _normalize_model_name(name: str) -> str:
    """Normalize model names and aliases to their canonical API identifier."""
    if not name:
        return name
    cleaned = name.strip()
    return _MODEL_ALIASES.get(cleaned.lower(), cleaned)


def _infer_provider_from_model(model_name: str) -> str | None:
    """Infer provider name from model name prefix/family."""
    norm = _normalize_model_name(model_name).lower()
    if norm.startswith("gemini"):
        return "gemini"
    if norm.startswith("deepseek"):
        return "deepseek"
    if norm.startswith(("moonshotai/", "kimi", "nvidia/", "nemotron")):
        return "nvidia"
    if norm.startswith(("gpt", "o1", "o3", "o4")):
        return "openai"
    if norm.startswith("claude"):
        return "anthropic"
    return None
