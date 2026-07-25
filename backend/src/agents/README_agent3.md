# Agent 3: Telemetry & Root Cause Agent

Agent 3 is a strictly analytical component of the OpsForge Platform. Its primary responsibility is to ingest raw deployment telemetry (logs, metrics, events), deterministically detect if an incident occurred, build a chronological timeline, and leverage Gemini 2.5 Flash to diagnose the root cause and propose ranked recovery actions.

**Agent 3 NEVER executes recovery actions.** Its output is purely analytical and forms the data contract (`IncidentReport`) that downstream agents (like Agent 4: Recovery & Voice) consume.

---

## 🏗️ Architecture & Pipeline

The Agent 3 pipeline is fully synchronous for the caller and is composed of three sequential stages:

1.  **Incident Detection (Deterministic Stage 1):**
    Evaluates incoming telemetry against hard thresholds (e.g., CPU > 90%, P99 Latency > 2000ms, >5 ERROR logs, specific crash keywords). This ensures the LLM is guided by hard math, not hallucination.
2.  **Correlation Layer (Deterministic Stage 2):**
    Merges disjointed logs, anomalous metrics, and lifecycle events into a single, chronologically sorted `CorrelatedTimelineEntry` list.
3.  **Root Cause Analysis (LLM Stage 3):**
    Constructs a concise prompt containing the detected incident reasons, peak metric summary, and the unified timeline. Gemini evaluates this to produce the final `IncidentReport`.

```
Frontend / Monitoring Webhook
       │
       ▼
[ POST /incident/analyze ]
       │
       ├─► 1. detect_incident() (telemetry_service.py)
       │      • Scans logs for ERROR thresholds & crash keywords
       │      • Scans metrics for CPU/RAM/Latency peaks
       │
       ├─► 2. correlate() (telemetry_service.py)
       │      • Builds unified chronological timeline
       │
       └─► 3. RCAService.analyse() (rca_service.py)
              • Gemini 2.5 Flash Prompting
              • Pydantic Schema Validation
              • Automatic Retry (1 max) on JSON malformation
```

---

## 📁 Files & Modules Involved

All Agent 3 code resides in the Python FastAPI backend (`backend/app/`).

| File | Path | Description |
| :--- | :--- | :--- |
| **Pydantic Schemas** | `schemas/incident.py` | Defines `LogEntry`, `MetricPoint`, `DeploymentEvent`, `IncidentAnalysisRequest`, and the final `IncidentReport` and `RecoveryRecommendation`. |
| **Telemetry Service** | `services/telemetry_service.py` | Contains `detect_incident()` and `correlate()` functions. Handles all deterministic data wrangling before LLM invocation. |
| **RCA Service** | `services/rca_service.py` | Contains `RCAService`. Builds the prompt, calls `GeminiClient`, strips markdown, validates JSON, and manages the retry loop. |
| **System Prompt** | `prompts/rca.txt` | The strict system instruction file ensuring Gemini outputs raw JSON matching the `IncidentReport` schema. |
| **Agent Interface** | `agents/root_cause.py` | The thin orchestration class (`RootCauseAgent`) that exposes the async `run()` method, wiring the three stages together. |
| **API Route** | `routes/incidents.py` | Exposes `POST /incident/analyze`. Handles basic HTTP payload validation. |
| **Unit Tests** | `../tests/test_root_cause_agent.py` | 18 unit tests validating detection rules, timeline sorting, Gemini mocking, and FastAPI route responses. |

---

## 🛠️ Key Functions

*   `detect_incident(request: IncidentAnalysisRequest) -> tuple[bool, List[str]]`: Scans the raw payload for anomalies based on predefined constants (e.g., `CPU_CRITICAL_THRESHOLD`).
*   `correlate(request: IncidentAnalysisRequest, detection_reasons: List[str]) -> CorrelatedIncident`: Sorts logs, anomalous metrics, and events by timestamp into a single list. Limits context size by filtering out "normal" metric readings.
*   `RCAService.build_prompt(incident: CorrelatedIncident, retry_error: Optional[str]) -> str`: Formats the timeline and detection flags into text. If `retry_error` is provided, it appends the previous Pydantic validation error to self-correct the LLM.
*   `RCAService.analyse(incident: CorrelatedIncident) -> IncidentReport`: Executes the Gemini API call and handles JSON serialization/validation.

---

## 🚀 Usage

To trigger Agent 3, send a `POST` request to `/incident/analyze` with the telemetry payload:

```json
POST /incident/analyze
{
  "deployment_id": "dep-xyz-123",
  "app_name": "user-auth-service",
  "logs": [
    {
      "timestamp": "2024-06-01T12:00:00Z",
      "level": "ERROR",
      "message": "Process killed: out of memory",
      "source": "app"
    }
  ],
  "metrics": [
    {
      "timestamp": "2024-06-01T11:59:55Z",
      "name": "ram_percent",
      "value": 98.5,
      "unit": "%"
    }
  ],
  "events": []
}
```

**Output:** A fully typed `IncidentReport` containing the `root_cause`, `causal_chain`, and a ranked list of `recommendations`.
