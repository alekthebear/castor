# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Castor is an AI-powered forecasting bot for Metaculus. It uses LLMs (OpenAI, Anthropic, Gemini) to predict outcomes for various question types (binary, numeric, discrete, multiple choice) and optionally submits predictions to Metaculus.

## Commands

```bash
# Install dependencies
uv sync

# Run forecaster
uv run castor --tournament <id> --submit --num-samples 5
uv run castor --post <id> --submit
uv run castor --post <id> --provider anthropic  # Override LLM provider
uv run castor --post <id> --agent baseline --no-record

# Database migrations (uses DATABASE_URL)
uv run alembic upgrade head
uv run alembic revision --autogenerate -m "<change>"

# Tests
uv run pytest

# Linting and type checking
uv run ruff check castor
uv run mypy castor
```

## Architecture

### Multi-Provider LLM System (`castor/clients/llm/`)
- **Protocol-based abstraction**: `LLMClient` Protocol in `base.py`
- **Factory pattern**: `create_llm_client()` in `__init__.py`
- **Providers**: OpenAI, Anthropic, Gemini with per-provider instrumentation
- **Configuration**: `LLM_PROVIDER` env var ("openai" | "anthropic" | "gemini")

### Agents (`castor/agents/`)
- An Agent turns a Question into a Forecast (`Agent` protocol in `base.py`); register new ones in `AGENTS` in `__init__.py` and select with `--agent`
- `baseline/`: research once, draw N Samples from one prompt, aggregate (median/mean); type-specific logic in `binary.py`, `numeric.py`, `multiple_choice.py`

### Runner (`castor/runner.py`)
- Fetches the Question, runs the Agent, submits, and records the Forecast Run (also when it fails)

### Tracing and storage (`castor/tracing/`, `castor/storage/`)
- Wrap units of work in `with step("name", **metadata):` and attach content with `artifact(kind, content, role=...)`; Steps nest and are mirrored to Langfuse
- `TracedLLMClient` records every LLM call's prompt and response as a Step
- Forecast Runs are written once at the end to the database at `DATABASE_URL` (Supabase Postgres in prod, sqlite works locally); schema in `storage/models.py`, migrations in `migrations/`

### Research Integration (`castor/research/`)
- Auto-selects best available provider: AskNews > Exa > Perplexity > None
- Falls back gracefully if no research providers configured

### Observability (`castor/utils/telemetry.py`)
- Langfuse integration with OpenTelemetry; spans come from `step()` and the LLM SDK instrumentors

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

## Docs (`.agent/docs/`)

All design docs live flat in `.agent/docs/`:

- `CONTEXT.md`: domain glossary (Question, Agent, Forecast Run, Step, ...). Use these terms in code, docs, and conversation; update it when a term is added or changes meaning. Definitions only, no implementation details.
- `backlog.md`: deferred ideas and open design questions, one bullet each.
- `YYYYMMDD_<topic>.md`: one doc per body of work (plan, design decisions and why, status), dated when the work started. Update its status as work progresses rather than creating a new doc.

## Code Style

- **Comments**: Keep them short and succinct. Describe the general rule or intent, not the specific bug or example that prompted the code.
