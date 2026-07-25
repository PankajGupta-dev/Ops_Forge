# OpsForge Deployment Planner Agent (Agent 1) Documentation

# Overview

The **Deployment Planner Agent (Agent 1)** is the reasoning engine of the OpsForge platform. It is responsible for parsing application files (such as Dockerfiles) alongside user deployment intents (e.g., requests for databases, autoscaling, or specific regional bounds) and translating them into a strict, validated, machine-readable **DeploymentPlan JSON**.

Agent 1 acts purely as a plan-generation and topology-reasoning pipeline. It **does not deploy any infrastructure**. The resulting output plan is designed to be consumed directly by the **Infra & Deploy Agent (Agent 2)** for execution.

---

# Flow Architecture

The execution pipeline inside the FastAPI backend runs as follows:

```
[POST /plan] ──► [FastAPI Route] ──► [Planner Service]
                                            │
                                            ├──► [Dockerfile Parser] (Deterministic)
                                            ├──► [Prompt Builder]
                                            ├──► [Gemini API Client] (JSON Mode)
                                            └──► [Pydantic Validation] (With Single Retry)
                                                        │
                                                        └──► Returns DeploymentPlan JSON
```

1. **Ingress Validation**: Route receives user intent and raw Dockerfile content.
2. **Dockerfile Analysis**: Extracts metadata deterministically using Python code (never using LLM for base facts).
3. **Prompt Construction**: Compiles the parsed Dockerfile, user intent, Pydantic schemas, and safety instructions.
4. **LLM Ingress**: Calls the Google Gemini API with JSON response format enabled.
5. **Schema Validation**: Validates output against strict Pydantic models. On fail, retry once with error context.
6. **Egress Plan Delivery**: Returns a validated, structural plan.

---

# Involved Files

All Python modules reside within the `backend/app/` structure:

```
backend/
├── app/
│   ├── main.py                   # FastAPI initialization and route mounting
│   ├── agents/
│   │   └── deployment_planner.py # Agent 1 coordinator class orchestrating execution
│   ├── config/
│   │   └── env.py / utils/config.py # Environment configurations loader
│   ├── integrations/
│   │   └── gemini_client.py      # Async client for Google Gemini API integration
│   ├── prompts/
│   │   └── deployment.txt        # System instruction guidelines for Gemini
│   ├── routes/
│   │   └── deploy.py             # FastAPI routing defining POST endpoints
│   ├── schemas/
│   │   └── deployment.py         # Strict Pydantic schemas for payload validation
│   ├── services/
│   │   └── planner_service.py    # Orchestration service handling pipeline steps
│   └── utils/
│       ├── docker_parser.py      # Deterministic regex-based Dockerfile parsing
│       └── logger.py             # Operational event logging utility
└── tests/
    └── test_deployment_planner.py # Unit tests for parser and schema routing validation
```

---

# Key Components & Functionality

### 1. `docker_parser.py`
Parses Dockerfiles line-by-line using Python regular expressions.
* **Function**: `parse_dockerfile(dockerfile_content: str) -> DockerfileAnalysis`
* **Extracted Fields**:
  * `runtime`: Inferred runtime environment (e.g. `python`, `node`, `go`, `rust`, `php`, `java`).
  * `base_image`: The target base image string (e.g., `python:3.11-slim`).
  * `language`: Associated programming language.
  * `framework`: Detects frameworks like `fastapi`, `django`, `flask`, `express`, `nextjs`, `nestjs`.
  * `working_dir`: Extracted from the `WORKDIR` instruction.
  * `exposed_ports`: Integer port array collected from `EXPOSE` lines.
  * `entry_command` / `entrypoint`: Captured from `CMD` and `ENTRYPOINT` (supports JSON array or shell format).
  * `package_manager`: Inferred dependency tools (`pip`, `poetry`, `npm`, `yarn`, `cargo`, etc.).
  * `healthcheck`: Extracted raw healthcheck configuration string.
  * `env_vars`: Dict containing static key-value pairs declared using `ENV`.
* *Note: Unspecified parameters default strictly to `None` to prevent hallucinating application configurations.*

### 2. `deployment.py` (Pydantic Schemas)
Defines strict serialization and validation rules.
* **`PlannerRequest`**: Payload validator for endpoint ingress containing `description` and `dockerfile` strings.
* **`DeploymentPlan`**: Main schema containing nested sub-models:
  * `application`: Basic service settings.
  * `deployment`: Platform target (`digitalocean-app-platform`), replica count, region, and rollout strategy.
  * `resources`: Hardware requests (`cpu`, `ram`, `instance_size`).
  * `autoscaling`: Autoscaling bounds and utilization targets.
  * `database`: State requirement details (`required`, `engine`, `version`, `size`).
  * `network`: Routing ports, public route exposure status, custom domain.
  * `environment`: Flat map of runtime configurations.
  * `healthcheck`: Live probing config (`path`, `port`, `initial_delay_seconds`, etc.).
  * `warnings` / `assumptions`: Arrays mapping planning warnings or reasoning assumptions.

### 3. `gemini_client.py`
Handles asynchronous HTTP calls to the Gemini REST API.
* **Function**: `generate_json(prompt: str, system_instruction: Optional[str] = None) -> str`
* **Configuration**: Sets `response_mime_type: "application/json"` under candidate generation configuration to guarantee JSON-only outputs.

### 4. `planner_service.py`
The orchestrator managing data pipelines, prompt composition, and LLM output sanity verification.
* **Function**: `generate_plan(request: PlannerRequest) -> DeploymentPlan`
* **Prompt Assembly**: Generates user context from the parsed Dockerfile object, raw contents, and description input.
* **Validation & Retry Pattern**:
  * Runs Pydantic validation on the LLM output.
  * If a `ValidationError` or `JSONDecodeError` triggers, it starts a **single retry loop**.
  * The retry prompt includes the previous validation error details, instructing Gemini to fix the schema.
  * If the second validation run fails, it raises an HTTP 422 exception.

---

# Environment Variables

Agent 1 relies on the following configurations:

| Variable | Required | Default Value | Purpose |
| :--- | :--- | :--- | :--- |
| `GEMINI_API_KEY` | **Yes** | *None* | Authentication token for calling Google Gemini APIs. |
| `GEMINI_MODEL` | No | `gemini-2.5-flash` | Target LLM model for planning (e.g. `gemini-2.5-flash`, `gemini-2.5-pro`). |

---

# Endpoints Exposed

### `POST /plan`
Generate a validated DeploymentPlan from raw inputs.

#### Payload Schema
```json
{
  "description": "Deploy with PostgreSQL and autoscaling",
  "dockerfile": "FROM python:3.11-slim\nEXPOSE 8080\nCMD [\"uvicorn\", \"main:app\"]"
}
```

#### Success Response (HTTP 200 OK)
```json
{
  "application": {
    "name": "opsforge-service",
    "runtime": "python",
    "base_image": "python:3.11-slim",
    "language": "python",
    "framework": "fastapi",
    "working_dir": "/app",
    "exposed_ports": [8080],
    "entry_command": ["uvicorn", "main:app"]
  },
  "deployment": {
    "platform": "digitalocean-app-platform",
    "region": "nyc3",
    "strategy": "rolling",
    "replicas": 1
  },
  "resources": {
    "cpu": "500m",
    "ram": "1Gi",
    "instance_size": "basic-xs"
  },
  "autoscaling": {
    "enabled": true,
    "min_instances": 1,
    "max_instances": 3,
    "target_cpu_utilization": 80
  },
  "database": {
    "required": true,
    "engine": "postgresql",
    "version": "14",
    "size": "db-s-1vcpu-1gb"
  },
  "network": {
    "ports": [8080],
    "public_http": true,
    "custom_domain": null
  },
  "environment": {},
  "healthcheck": {
    "path": "/healthz",
    "port": 8080,
    "initial_delay_seconds": 10,
    "period_seconds": 15,
    "timeout_seconds": 5
  },
  "warnings": [],
  "assumptions": [
    "Assumed default PostgreSQL version 14 based on standard platform setup",
    "Configured basic-xs resources based on low-resource python runtime characteristics"
  ]
}
```
