from typing import Optional
from opentelemetry import trace
from opentelemetry import __version__ as otel_version
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor, ConsoleSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor


def init_tracing(app, service_name: str, enable: bool = False) -> None:
    """Initialize OpenTelemetry tracing for the FastAPI app.

    This is a lightweight, production-friendly default that writes traces
    to the console. In production, replace ConsoleSpanExporter with an OTLP
    exporter to send traces to a collector.
    """
    if not enable:
        return
    provider = TracerProvider()
    trace.set_tracer_provider(provider)
    # Simple console exporter for development; switch to OTLP in prod
    span_processor = SimpleSpanProcessor(ConsoleSpanExporter())
    provider.add_span_processor(span_processor)
    # Instrument FastAPI to automatically create spans for incoming requests
    try:
        FastAPIInstrumentor.instrument_app(app, tracer_provider=provider)
    except Exception:
        # If instrumentation fails for any reason, fail closed gracefully
        pass
