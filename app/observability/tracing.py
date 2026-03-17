from typing import Optional

# OpenTelemetry is optional; allow tests to run without it installed.
try:
    from opentelemetry import trace
    from opentelemetry import __version__ as otel_version
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import SimpleSpanProcessor, ConsoleSpanExporter
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

    _OTEL_AVAILABLE = True
except Exception:
    trace = None
    otel_version = None
    TracerProvider = None
    SimpleSpanProcessor = None
    ConsoleSpanExporter = None
    FastAPIInstrumentor = None
    _OTEL_AVAILABLE = False


def init_tracing(app, service_name: str, enable: bool = False) -> None:
    """Initialize OpenTelemetry tracing for the FastAPI app.

    This is a lightweight, production-friendly default that writes traces
    to the console. In production, replace ConsoleSpanExporter with an OTLP export.
    If OpenTelemetry is not available, this is a no-op.
    """
    if not enable or not _OTEL_AVAILABLE:
        return
    provider = TracerProvider()
    trace.set_tracer_provider(provider)  # type: ignore[attr-defined]
    # Simple console exporter for development; switch to OTLP in prod
    span_processor = SimpleSpanProcessor(ConsoleSpanExporter())  # type: ignore[attr-defined]
    provider.add_span_processor(span_processor)
    # Instrument FastAPI to automatically create spans for incoming requests
    try:
        if FastAPIInstrumentor is not None:
            FastAPIInstrumentor.instrument_app(app, tracer_provider=provider)  # type: ignore[attr-defined]
    except Exception:
        # If instrumentation fails, fail gracefully
        pass
