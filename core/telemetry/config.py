"""OpenTelemetry configuration for BHNBot tracing."""

import os
from typing import Optional

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

_tracer_provider: Optional[TracerProvider] = None
_initialized: bool = False


def configure_telemetry(
    service_name: str = "bhnbot",
    otlp_endpoint: Optional[str] = None,
    enable_console: bool = False,
) -> TracerProvider:
    """Configure OpenTelemetry TracerProvider with OTLP exporter.
    
    Args:
        service_name: Name of the service for traces.
        otlp_endpoint: OTLP gRPC endpoint (e.g., "http://localhost:4317").
                      Falls back to OTEL_EXPORTER_OTLP_ENDPOINT env var.
        enable_console: If True, also export spans to console (for debugging).
    
    Returns:
        Configured TracerProvider instance.
    """
    global _tracer_provider, _initialized
    
    if _initialized:
        return _tracer_provider
    
    endpoint = otlp_endpoint or os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
    
    resource = Resource.create({
        "service.name": service_name,
        "service.version": os.getenv("BOT_VERSION", "dev"),
        "deployment.environment": os.getenv("ENVIRONMENT", "development"),
    })
    
    _tracer_provider = TracerProvider(resource=resource)
    
    if endpoint:
        otlp_exporter = OTLPSpanExporter(endpoint=endpoint, insecure=True)
        _tracer_provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
    
    if enable_console or os.getenv("OTEL_CONSOLE_EXPORT", "").lower() == "true":
        _tracer_provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))
    
    trace.set_tracer_provider(_tracer_provider)
    _initialized = True
    
    return _tracer_provider


def get_tracer(name: str = "bhnbot") -> trace.Tracer:
    """Get a tracer instance for creating spans.
    
    Args:
        name: Tracer name, typically module or component name.
    
    Returns:
        Tracer instance.
    """
    if not _initialized:
        configure_telemetry()
    return trace.get_tracer(name)


def shutdown_telemetry() -> None:
    """Shutdown the tracer provider, flushing pending spans."""
    global _tracer_provider, _initialized
    if _tracer_provider:
        _tracer_provider.shutdown()
        _tracer_provider = None
        _initialized = False
