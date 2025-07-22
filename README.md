# OpenTelemetry Flask Example

This repository provides a multi-service example of distributed tracing using [OpenTelemetry](https://opentelemetry.io/) in Python Flask applications. The project demonstrates how to instrument Flask and HTTP requests, propagate traces across services, and export trace data to Jaeger for observability.

## Overview

- **Language:** Python
- **Main Components:**
  - `main/`: Dice Roller service (Flask) instrumented with OpenTelemetry.
  - `service2/` and `service3/`: User service mockups returning user data, also instrumented with OpenTelemetry.
  - `req_service/`: An additional traced service example.

## Features

- Distributed tracing across multiple microservices using OpenTelemetry.
- Automatic instrumentation for Flask and HTTP requests.
- Trace context propagation via HTTP headers.
- Exporting traces to Jaeger for visualization.
- Example endpoints for rolling dice, fetching user info, and health checks.

## Architecture

```
[main (Dice Roller Service)] <------HTTP------> [service2/service3 (User Services)]
         |                                             |
         |---OpenTelemetry Tracing---------------------/
         |
         |---Jaeger (Trace Collector/Visualizer)
```

- Requests handled by `main/` call user services (`service2/`, `service3/`) and propagate trace context.
- All services export traces to a Jaeger instance.

## Quick Start

Up projects
```
docker compose up
```


Go to http://localhost:16686

<img width="1920" height="847" alt="image" src="https://github.com/user-attachments/assets/7762a0c3-7f38-4ab8-8951-da352a0928f7" />
