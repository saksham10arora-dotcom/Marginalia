"""Provider registry for OpenAI-compatible chat-completion APIs.

Data only, no logic -- `openai_compatible.py` does the actual calling. The
point is that adding a provider is a dict entry here, not a new client module
plus another `if NOTE_ENGINE == "..."` branch in main.py, which is how the
first two engines (haiku via local CLI, gemini via its own bespoke API) grew.

Those two stay special-cased: the Claude CLI isn't an HTTP API at all, and
Gemini's `generateContent` shape predates this registry. Everything else the
world ships speaks OpenAI's /chat/completions, so it goes here.
"""
from dataclasses import dataclass, field


@dataclass(frozen=True)
class ProviderSpec:
    base_url: str
    default_model: str
    # Env var names to read from ~/.config/keys.env, in priority order.
    # Empty list = a local server that needs no auth (ollama, lmstudio).
    key_names: list[str] = field(default_factory=list)
    # Whether this provider's default model accepts image parts. Frame capture
    # is skipped entirely for text-only providers rather than being sent and
    # silently ignored (or 400'd) -- see openai_compatible.build_messages.
    supports_vision: bool = False
    # Providers that want extra headers (OpenRouter uses these for attribution
    # on its public leaderboards; harmless to send, and it asks for them).
    extra_headers: dict[str, str] = field(default_factory=dict)


PROVIDERS: dict[str, ProviderSpec] = {
    "openrouter": ProviderSpec(
        base_url="https://openrouter.ai/api/v1",
        # Routes to whichever upstream is cheapest/healthiest; swap via
        # MARGIN_MODEL for a specific one (e.g. "openai/gpt-4o-mini").
        default_model="anthropic/claude-3.5-haiku",
        key_names=["OPENROUTER_API_KEY"],
        supports_vision=True,
        extra_headers={
            "HTTP-Referer": "https://github.com/saksham10arora-dotcom/Margin",
            "X-Title": "Margin",
        },
    ),
    "groq": ProviderSpec(
        base_url="https://api.groq.com/openai/v1",
        default_model="llama-3.3-70b-versatile",
        key_names=["GROQ_API_KEY"],
        # Groq does host vision models, but the default text model above is
        # not one -- flip this only alongside a vision-capable default.
        supports_vision=False,
    ),
    "fireworks": ProviderSpec(
        base_url="https://api.fireworks.ai/inference/v1",
        default_model="accounts/fireworks/models/llama-v3p3-70b-instruct",
        key_names=["FIREWORKS_API_KEY"],
        supports_vision=False,
    ),
    "cerebras": ProviderSpec(
        base_url="https://api.cerebras.ai/v1",
        default_model="llama-3.3-70b",
        key_names=["CEREBRAS_API_KEY"],
        supports_vision=False,
    ),
    "together": ProviderSpec(
        base_url="https://api.together.xyz/v1",
        default_model="meta-llama/Llama-3.3-70B-Instruct-Turbo",
        key_names=["TOGETHER_API_KEY"],
        supports_vision=False,
    ),
    "openai": ProviderSpec(
        base_url="https://api.openai.com/v1",
        default_model="gpt-4o-mini",
        key_names=["OPENAI_API_KEY"],
        supports_vision=True,
    ),
    # Local servers: no key, no cost, no quota. Whatever model you have
    # pulled -- override with MARGIN_MODEL.
    "ollama": ProviderSpec(
        base_url="http://localhost:11434/v1",
        default_model="llama3.2",
        key_names=[],
        supports_vision=False,
    ),
    "lmstudio": ProviderSpec(
        base_url="http://localhost:1234/v1",
        default_model="local-model",
        key_names=[],
        supports_vision=False,
    ),
}

# Engines that predate this registry and have their own client modules.
NATIVE_ENGINES = ("haiku", "gemini")


def is_openai_compatible(engine: str) -> bool:
    return engine in PROVIDERS


def get_provider(engine: str) -> ProviderSpec:
    try:
        return PROVIDERS[engine]
    except KeyError:
        known = ", ".join(sorted(PROVIDERS) + list(NATIVE_ENGINES))
        raise ValueError(f"Unknown engine {engine!r}. Known engines: {known}") from None
