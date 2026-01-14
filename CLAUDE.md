# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Castor is an AI-powered forecasting bot for Metaculus. It uses LLMs (OpenAI, Anthropic, Gemini) to predict outcomes for various question types (binary, numeric, discrete, multiple choice) and optionally submits predictions to Metaculus.

## Commands

```bash
# Install dependencies
uv sync

# Run forecaster
uv run castor --tournament <id> --submit --num-runs 5
uv run castor --post <id> --submit
uv run castor --post <id> --provider anthropic  # Override LLM provider

# Linting
ruff check castor
```

## Architecture

### Multi-Provider LLM System (`castor/clients/llm/`)
- **Protocol-based abstraction**: `LLMClient` Protocol in `base.py`
- **Factory pattern**: `create_llm_client()` in `__init__.py`
- **Providers**: OpenAI, Anthropic, Gemini with per-provider instrumentation
- **Configuration**: `LLM_PROVIDER` env var ("openai" | "anthropic" | "gemini")

### Forecasting Pipeline (`castor/forecasting/`)
- `forecaster.py`: Main orchestrator that determines question type and dispatches
- `binary.py`, `numeric.py`, `multiple_choice.py`: Type-specific forecasters
- Multi-run support: Runs N forecasts and returns median/aggregated result

### Research Integration (`castor/research/`)
- Auto-selects best available provider: AskNews > Exa > Perplexity > None
- Falls back gracefully if no research providers configured

### Observability (`castor/utils/telemetry.py`)
- Langfuse integration with OpenTelemetry
- Use `@observe(name="span-name")` decorator for tracing
- Span naming: "castor-run", "forecast-batch", "forecast-question", etc.

### Configuration (`castor/config/settings.py`)
- Pydantic `BaseSettings` loading from `.env` then environment variables
- All API keys and feature flags centralized here

## Key Patterns

- **Async-first**: All LLM and research calls use async/await
- **Parallel processing**: Questions in a tournament are forecasted concurrently via `asyncio.gather()`
- **Custom exceptions**: `ParseError`, `ResearchError`, `MetaculusAPIError`, `LLMError` in `exceptions.py`
- **Pydantic models**: Question data wrapped in `QuestionDetails`, distributions in `NumericDistribution`

## CI/CD

GitHub Actions runs every 30 minutes (`.github/workflows/tournament_run.yml`) to forecast tournament questions automatically.
