"""OpenTelemetry setup for Langfuse integration with non-OpenAI providers."""

from __future__ import annotations

import base64
import logging

from castor.config.settings import settings

logger = logging.getLogger(__name__)

_otel_initialized = False


def setup_otel_langfuse() -> None:
    """Configure OpenTelemetry to send traces to Langfuse.

    This enables automatic tracing for Anthropic and Gemini clients
    via their respective OpenTelemetry instrumentors.
    """
    global _otel_initialized

    if _otel_initialized:
        return

    if not settings.langfuse_enabled:
        logger.debug("Langfuse not enabled, skipping OTel setup")
        return

    try:
        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import SimpleSpanProcessor
    except ImportError:
        logger.warning("OpenTelemetry packages not installed, skipping OTel setup")
        return

    # Create auth header
    auth_string = f"{settings.langfuse_public_key}:{settings.langfuse_secret_key}"
    auth_bytes = base64.b64encode(auth_string.encode()).decode()

    # Configure exporter to send to Langfuse
    exporter = OTLPSpanExporter(
        endpoint=f"{settings.langfuse_base_url}/api/public/otel/v1/traces",
        headers={"Authorization": f"Basic {auth_bytes}"},
    )

    # Set up tracer provider
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    trace.set_tracer_provider(provider)

    # Instrument Anthropic if available
    try:
        from openinference.instrumentation.anthropic import AnthropicInstrumentor
        AnthropicInstrumentor().instrument()
        logger.debug("Anthropic instrumentation enabled")
    except ImportError:
        pass

    # Instrument Google GenAI if available
    try:
        from openinference.instrumentation.google_genai import GoogleGenAIInstrumentor
        GoogleGenAIInstrumentor().instrument()
        logger.debug("Google GenAI instrumentation enabled")
    except ImportError:
        pass

    _otel_initialized = True
    logger.info("OpenTelemetry Langfuse integration initialized")
