import atexit
import uuid
from random import randint

import requests
from flask import Flask, jsonify
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.propagate import inject
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter

app = Flask(__name__)

# Configure OpenTelemetry
resource = Resource.create({
    "service.name": "dice-roller-service",
    "service.version": "1.0.0",
    "service.port": "5000",
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
RequestsInstrumentor().instrument()  # This enables HTTP request tracing

tracer = trace.get_tracer("dice-roller.tracer")

USER_SERVICE_URL = "http://localhost:5001"


def roll():
    with tracer.start_as_current_span("roll") as rollspan:
        res = randint(1, 6)
        rollspan.set_attribute("roll.value", res)
        return res


def get_user_info():
    """Make HTTP request to user service"""
    with tracer.start_as_current_span("get_user_info") as span:
        try:
            # Prepare headers for distributed tracing
            headers = {}
            inject(headers)  # This injects trace context into headers

            # Add custom request ID
            request_id = str(uuid.uuid4())
            headers['X-Request-ID'] = request_id

            span.set_attribute("http.url", f"{USER_SERVICE_URL}/users/random")
            span.set_attribute("http.method", "GET")
            span.set_attribute("request.id", request_id)

            # Make the HTTP request
            response = requests.get(
                f"{USER_SERVICE_URL}/users/random",
                headers=headers,
                timeout=5
            )

            span.set_attribute("http.status_code", response.status_code)
            span.set_attribute("http.response_size", len(response.content))

            if response.status_code == 200:
                user_data = response.json()
                span.set_attribute("user.id", user_data["user"]["id"])
                span.set_attribute("user.name", user_data["user"]["name"])
                return user_data
            else:
                span.set_attribute("error", True)
                span.set_attribute("error.message", f"HTTP {response.status_code}")
                return None

        except requests.exceptions.RequestException as e:
            span.set_attribute("error", True)
            span.set_attribute("error.message", str(e))
            span.record_exception(e)
            return None


def check_user_service_health():
    """Check if user service is available"""
    with tracer.start_as_current_span("check_user_service_health") as span:
        try:
            headers = {}
            inject(headers)

            response = requests.get(
                f"{USER_SERVICE_URL}/health",
                headers=headers,
                timeout=2
            )

            healthy = response.status_code == 200
            span.set_attribute("user_service.healthy", healthy)
            span.set_attribute("http.status_code", response.status_code)
            return healthy

        except requests.exceptions.RequestException as e:
            span.set_attribute("user_service.healthy", False)
            span.set_attribute("error.message", str(e))
            return False


@app.route("/okak")
def okak():
    # time.sleep(.1)
    requests.get("http://localhost:5001/health")
    # time.sleep(.05)
    return "okak"

@app.route("/")
def hello():
    with tracer.start_as_current_span("hello-endpoint") as span:
        tracking_id = str(uuid.uuid4())
        span.set_attribute("tracking.id", tracking_id)
        span.set_attribute("endpoint.name", "hello")

        # Roll dice
        rand = roll()

        # Check if user service is healthy
        user_service_healthy = check_user_service_health()

        response_data = {
            "message": "Hello from Dice Roller Service!",
            "tracking_id": tracking_id,
            "dice_roll": rand,
            "user_service_available": user_service_healthy
        }

        # If user service is available, get user info
        if user_service_healthy:
            user_info = get_user_info()
            if user_info:
                response_data["user"] = user_info["user"]
                response_data["user_service_timestamp"] = user_info["timestamp"]

        return jsonify(response_data)


@app.route("/roll")
def roll_only():
    """Simple endpoint that just rolls dice"""
    with tracer.start_as_current_span("roll-only-endpoint") as span:
        tracking_id = str(uuid.uuid4())
        span.set_attribute("tracking.id", tracking_id)
        span.set_attribute("endpoint.name", "roll_only")

        # Multiple rolls for demonstration
        rolls = []
        for i in range(3):
            with tracer.start_as_current_span(f"roll_{i + 1}") as roll_span:
                roll_value = roll()
                rolls.append(roll_value)
                roll_span.set_attribute("roll.sequence", i + 1)

        span.set_attribute("rolls.count", len(rolls))
        span.set_attribute("rolls.sum", sum(rolls))

        return jsonify({
            "message": "Multiple dice rolls",
            "tracking_id": tracking_id,
            "rolls": rolls,
            "total": sum(rolls)
        })


@app.route("/user/<int:user_id>")
def get_specific_user(user_id):
    """Get a specific user from user service"""
    with tracer.start_as_current_span("get-specific-user-endpoint") as span:
        span.set_attribute("requested.user_id", user_id)

        try:
            headers = {}
            inject(headers)

            response = requests.get(
                f"{USER_SERVICE_URL}/users/{user_id}",
                headers=headers,
                timeout=5
            )

            span.set_attribute("http.status_code", response.status_code)

            if response.status_code == 200:
                return jsonify(response.json())
            elif response.status_code == 404:
                return jsonify({"error": "User not found"}), 404
            else:
                return jsonify({"error": "User service error"}), 500

        except requests.exceptions.RequestException as e:
            span.set_attribute("error", True)
            span.record_exception(e)
            return jsonify({"error": "Failed to connect to user service"}), 503


# Ensure spans are flushed before shutdown
def shutdown():
    tracer_provider.force_flush(timeout_millis=5000)
    tracer_provider.shutdown()


atexit.register(shutdown)

if __name__ == "__main__":
    try:
        print("Starting Dice Roller Service on port 5000...")
        app.run(debug=True, port=5000, host="0.0.0.0")
    finally:
        shutdown()