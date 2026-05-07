"""
OpenTelemetry setup.
Instruments FastAPI, SQLAlchemy, and httpx with distributed tracing.

Configure via env:
  OTEL_EXPORTER_OTLP_ENDPOINT=http://jaeger:4318  (or any OTLP collector)
  OTEL_SERVICE_NAME=medmind-backend               (default)
  OTEL_ENABLED=true                               (opt-in)

If OTEL_ENABLED is not set or OTEL_EXPORTER_OTLP_ENDPOINT is not set,
tracing is a no-op — the app starts normally without any telemetry.
"""

import logging
import os

logger = logging.getLogger(__name__)


def setup_telemetry(app=None) -> None:
    """Initialize OpenTelemetry tracing. Safe no-op if not configured."""
    if os.getenv("OTEL_ENABLED", "").lower() not in ("1", "true", "yes"):
        return

    endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
    if not endpoint:
        return

    try:
        from opentelemetry import trace
        from opentelemetry.sdk.resources import Resource, SERVICE_NAME
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
        from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
        from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor

        service_name = os.getenv("OTEL_SERVICE_NAME", "medmind-backend")
        resource = Resource(attributes={SERVICE_NAME: service_name})

        provider = TracerProvider(resource=resource)
        exporter = OTLPSpanExporter(
            endpoint=f"{endpoint.rstrip('/')}/v1/traces",
        )
        provider.add_span_processor(BatchSpanProcessor(exporter))
        trace.set_tracer_provider(provider)

        # Instrument FastAPI
        if app is not None:
            FastAPIInstrumentor.instrument_app(app)

        # Instrument SQLAlchemy (async-compatible)
        SQLAlchemyInstrumentor().instrument(enable_commenter=True)

        # Instrument httpx (used for Ollama, external APIs)
        HTTPXClientInstrumentor().instrument()

        logger.info(
            "OpenTelemetry tracing enabled: service=%s endpoint=%s",
            service_name, endpoint,
        )

    except ImportError:
        logger.warning("opentelemetry packages not installed — tracing disabled")
    except Exception as exc:
        logger.warning("OpenTelemetry setup failed (non-fatal): %s", exc)
