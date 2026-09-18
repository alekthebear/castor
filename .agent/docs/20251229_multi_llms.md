# Multi-Provider LLM Client Architecture Plan

**Status: ✅ Implemented**

## Overview

Design a clean, extensible LLM client system supporting OpenAI, Anthropic, and Gemini with unified Langfuse observability.

## Architecture

### Factory Pattern with Provider Abstraction

```
castor/clients/
├── llm/
│   ├── __init__.py      # Exports create_llm_client() factory
│   ├── base.py          # LLMClient protocol
│   ├── openai.py        # OpenAIClient implementation
│   ├── anthropic.py     # AnthropicClient implementation
│   └── gemini.py        # GeminiClient implementation
```

### Langfuse Integration by Provider

| Provider | Integration Method |
|----------|-------------------|
| **OpenAI** | `langfuse.openai.AsyncOpenAI` wrapper |
| **Anthropic** | OpenTelemetry via `AnthropicInstrumentor` |
| **Gemini** | OpenTelemetry via `GoogleGenAIInstrumentor` |

### Key Components

1. **Protocol** (`base.py`):
   ```python
   class LLMClient(Protocol):
       async def call(
           self,
           prompt: str,
           temperature: Optional[float] = None,
           trace_name: Optional[str] = None,
           trace_metadata: Optional[dict] = None,
       ) -> str: ...
   ```

2. **Factory** (`__init__.py`):
   ```python
   def create_llm_client(provider: str | None = None) -> LLMClient:
       provider = provider or settings.llm_provider
       match provider:
           case "openai": return OpenAIClient()
           case "anthropic": return AnthropicClient()
           case "gemini": return GeminiClient()
           case _: raise ValueError(f"Unknown provider: {provider}")
   ```

3. **OTel Setup** (`castor/utils/telemetry.py`):
   - Centralized OpenTelemetry configuration
   - Initializes `AnthropicInstrumentor` and `GoogleGenAIInstrumentor`
   - Called once at startup from `main.py`

## Settings (`settings.py`)

```python
# Provider selection
llm_provider: str = "openai"  # "openai" | "anthropic" | "gemini"
llm_temperature: float = 0.3

# Per-provider API keys
openai_api_key: str | None = None
anthropic_api_key: str | None = None
gemini_api_key: str | None = None

# Per-provider model settings (with sensible defaults)
openai_model: str = "gpt-4.1"
anthropic_model: str = "claude-sonnet-4-20250514"
gemini_model: str = "gemini-2.0-flash"
```

## Files Modified/Created

| File | Status |
|------|--------|
| `castor/clients/llm.py` | ✅ Deleted (replaced with module) |
| `castor/clients/llm/__init__.py` | ✅ Created |
| `castor/clients/llm/base.py` | ✅ Created |
| `castor/clients/llm/openai.py` | ✅ Created |
| `castor/clients/llm/anthropic.py` | ✅ Created |
| `castor/clients/llm/gemini.py` | ✅ Created |
| `castor/config/settings.py` | ✅ Modified |
| `castor/utils/telemetry.py` | ✅ Created |
| `castor/main.py` | ✅ Modified |
| `castor/clients/__init__.py` | ✅ Modified |
| `pyproject.toml` | ✅ Modified |

## Dependencies Added

```toml
"anthropic>=0.40.0",
"google-genai>=0.5.0",
"opentelemetry-sdk>=1.20.0",
"opentelemetry-exporter-otlp>=1.20.0",
"openinference-instrumentation-anthropic>=0.1.0",
"openinference-instrumentation-google-genai>=0.1.0",
```

## Usage

```python
from castor.clients.llm import create_llm_client

client = create_llm_client()  # Uses settings.llm_provider
response = await client.call(prompt, trace_name="forecast")
```

## Configuration Examples

```bash
# .env for OpenAI (default)
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-...
# OPENAI_MODEL=gpt-4.1  # optional, this is the default

# .env for Anthropic
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-...
# ANTHROPIC_MODEL=claude-sonnet-4-20250514  # optional, this is the default

# .env for Gemini
LLM_PROVIDER=gemini
GEMINI_API_KEY=...
# GEMINI_MODEL=gemini-2.0-flash  # optional, this is the default
```

## Benefits

1. **Clean separation**: Each provider in its own module
2. **Easy to extend**: Add new provider by creating one file + factory case
3. **Unified interface**: All clients expose same `call()` method
4. **Native Langfuse**: Uses recommended integration for each provider
5. **Type-safe**: Protocol ensures consistent interface
6. **Testable**: Easy to mock the protocol for testing
