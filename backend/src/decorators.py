from opentelemetry import trace  # pylint: disable=import-error
from opentelemetry.sdk.resources import Resource  # pylint: disable=import-error
from opentelemetry.sdk.trace import ( # pylint: disable=import-error
    TracerProvider,
) 
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
    # pylint: disable=import-error
    OTLPSpanExporter,
)
from opentelemetry.sdk.trace.export import (
    SimpleSpanProcessor,
)  # pylint: disable=import-error
from opentelemetry.trace.propagation.tracecontext import (
    TraceContextTextMapPropagator,
) # pylint: disable=import-error
from opentelemetry.trace import StatusCode, Status # pylint: disable=import-error


import functools


def span_decorator(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        print(f"IN span_decorator. name={func.__name__}")
        result = None
        if not hasattr(span_decorator, "span_context"):
            print(f"New Root Span")
            resource = Resource.create({"service.name": "stock-analyzer"})
            provider = TracerProvider(resource=resource)
            trace.set_tracer_provider(provider)

            # otlp_exporter = ConsoleSpanExporter()
            otlp_exporter = OTLPSpanExporter(
                endpoint="http://host.docker.internal:4317"
            )  # Adjust endpoint as needed
            # otlp_exporter = OTLPSpanExporter(endpoint="http://localhost:4317")
            span_processor = SimpleSpanProcessor(otlp_exporter)
            provider.add_span_processor(span_processor)
            # Set global propagators
            propagator = TraceContextTextMapPropagator()
            tracer = trace.get_tracer(__name__)
            with tracer.start_as_current_span(func.__name__) as span:
                context = {}
                propagator.inject(context)
                setattr(span_decorator, "span_context", context)
                try:
                    result = func(*args, **kwargs)
                    span.set_status(Status(StatusCode.OK))
                except Exception as e:
                    print(f"Caught an error: {str(e)}")
                    span.record_exception(e)
                    # Set the span status to ERROR
                    span.set_status(Status(StatusCode.ERROR, description=str(e)))
                delattr(span_decorator, "span_context")
        else:
            tracer = trace.get_tracer(__name__)
            context = getattr(span_decorator, "span_context")
            propagator = TraceContextTextMapPropagator()
            extracted_context = propagator.extract(
                context
            )  # Extract context from carrier
            with trace.use_span(
                trace.get_current_span(extracted_context), end_on_exit=True
            ):
                with tracer.start_as_current_span(func.__name__):
                    # This span will be a child of the parent-span from the
                    # sending service
                    result = func(*args, **kwargs)
        return result

    return wrapper
