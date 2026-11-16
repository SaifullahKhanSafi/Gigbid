"""PII-safe spans exported to Phoenix via OTLP when configured."""

import os
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from core.security import mask

provider = TracerProvider(resource=Resource.create({"service.name": os.getenv("OTEL_SERVICE_NAME", "gigbid")}))
if os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT"):
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

    provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
trace.set_tracer_provider(provider)
tracer = trace.get_tracer("gigbid")


def span(name, trace_id, **attrs):
    return tracer.start_as_current_span(
        name, attributes={"gigbid.trace_id": trace_id, **{k: str(v) for k, v in mask(attrs).items()}}
    )
