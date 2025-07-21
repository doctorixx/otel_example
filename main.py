from random import randint

from flask import Flask, jsonify
from opentelemetry import trace
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.instrumentation.flask import FlaskInstrumentor
import uuid

app = Flask(__name__)

# Configure OpenTelemetry
resource = Resource.create({"service.name": "my-flask-app"})
tracer_provider = TracerProvider(resource=resource)
trace.set_tracer_provider(tracer_provider)

# Configure Jaeger Exporter
jaeger_exporter = JaegerExporter(
    agent_host_name="localhost",  # Replace with your Jaeger agent host if different
    agent_port=6831,              # Replace with your Jaeger agent port if different
)

# Configure the trace processor
span_processor = BatchSpanProcessor(jaeger_exporter)
tracer_provider.add_span_processor(span_processor)

# Instrument Flask
FlaskInstrumentor().instrument_app(app)

tracer = trace.get_tracer("diceroller.tracer")

def roll():
    # This creates a new span that's the child of the current one
    with tracer.start_as_current_span("roll") as rollspan:
        res = randint(1, 6)
        rollspan.set_attribute("roll.value", res)
        return res

@app.route("/")
def hello():
    with trace.get_tracer(__name__).start_as_current_span("hello-endpoint"):
        tracking_id = str(uuid.uuid4())
        # Add attributes to the span
        current_span = trace.get_current_span()
        rand = roll()
        current_span.set_attribute("tracking.id", tracking_id)
        return jsonify({"message": "Hello from Flask!", "tracking_id": tracking_id, "rand": rand})

if __name__ == "__main__":
    app.run(debug=True)