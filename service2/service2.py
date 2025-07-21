from random import choice
import time

import requests
from flask import Flask, jsonify, request
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
import uuid
import atexit

app = Flask(__name__)

# Configure OpenTelemetry
resource = Resource.create({
    "service.name": "user-service",
    "service.version": "1.0.0",
    "service.port": "5001",
})
tracer_provider = TracerProvider(resource=resource)
trace.set_tracer_provider(tracer_provider)

# Configure exporters
otlp_exporter = OTLPSpanExporter(
    endpoint="http://jaeger:4318/v1/traces",
)
console_exporter = ConsoleSpanExporter()

# Add processors
span_processor_otlp = BatchSpanProcessor(otlp_exporter)
span_processor_console = BatchSpanProcessor(console_exporter)

tracer_provider.add_span_processor(span_processor_otlp)
tracer_provider.add_span_processor(span_processor_console)

# Instrument Flask and Requests
FlaskInstrumentor().instrument_app(app)
RequestsInstrumentor().instrument()  # This will trace HTTP requests

tracer = trace.get_tracer("user-service.tracer")

# Mock user database
USERS = [
    {"id": 1, "name": "Alice", "email": "alice@example.com"},
    {"id": 2, "name": "Bob", "email": "bob@example.com"},
    {"id": 3, "name": "Charlie", "email": "charlie@example.com"},
]


def get_random_user():
    with tracer.start_as_current_span("get_random_user") as span:
        # Simulate some processing time
        time.sleep(0.1)
        user = choice(USERS)
        span.set_attribute("user.id", user["id"])
        span.set_attribute("user.name", user["name"])
        return user


def validate_request():
    with tracer.start_as_current_span("validate_request") as span:
        # Simulate validation logic
        time.sleep(0.05)
        request_id = request.headers.get('X-Request-ID')
        if request_id:
            span.set_attribute("request.id", request_id)
        span.set_attribute("request.valid", True)
        return True


@app.route("/health")
def health():
    with tracer.start_as_current_span("health-check"):

        requests.get("http://localhost:5003")

        return jsonify({"status": "healthy", "service": "user-service"})


@app.route("/users/random")
def random_user():
    with tracer.start_as_current_span("random_user_endpoint") as span:
        # Add some metadata to the span
        span.set_attribute("endpoint", "/users/random")
        span.set_attribute("http.method", request.method)

        # Validate the request
        if not validate_request():
            return jsonify({"error": "Invalid request"}), 400

        # Get a random user
        user = get_random_user()

        # Add response metadata
        span.set_attribute("response.user_count", len(USERS))
        span.set_attribute("response.selected_user_id", user["id"])

        return jsonify({
            "user": user,
            "timestamp": time.time(),
            "service": "user-service"
        })


@app.route("/users/<int:user_id>")
def get_user(user_id):
    with tracer.start_as_current_span("get_user_endpoint") as span:
        span.set_attribute("endpoint", f"/users/{user_id}")
        span.set_attribute("user.requested_id", user_id)

        # Simulate database lookup
        with tracer.start_as_current_span("database_lookup") as db_span:
            time.sleep(0.05)  # Simulate DB query time
            user = next((u for u in USERS if u["id"] == user_id), None)
            db_span.set_attribute("db.query", f"SELECT * FROM users WHERE id = {user_id}")
            db_span.set_attribute("db.result_found", user is not None)

        if not user:
            span.set_attribute("response.status", "not_found")
            return jsonify({"error": "User not found"}), 404

        span.set_attribute("response.status", "success")
        return jsonify({"user": user, "service": "user-service"})


# Ensure spans are flushed before shutdown
def shutdown():
    tracer_provider.force_flush(timeout_millis=5000)
    tracer_provider.shutdown()


atexit.register(shutdown)

if __name__ == "__main__":
    try:
        print("Starting User Service on port 5001...")
        app.run(debug=True, port=5001, host="0.0.0.0")
    finally:
        shutdown()