# Agent 5 – Knowledge Memory Agent

## 1. Overview
The **Knowledge Memory Agent** (Agent 5) serves as the persistent long-term memory engine for the OpsForge autonomous AI platform engineer. Powered by **MongoDB Atlas** and **Atlas Vector Search**, Agent 5 captures every incident record, root cause analysis, selected recovery action, and verification outcome across the deployment lifecycle. It converts text summaries into semantic vector embeddings (768 dimensions) to allow upstream agents to query historical incidents and calculate similarity match percentages (e.g., *"87% similar to Incident #3 — same fix worked"*).

## 2. Purpose
Agent 5 prevents redundant diagnostic effort by ensuring that system failures, root causes, and verified mitigations are remembered permanently. By embedding root cause descriptions and executing vector similarity searches against MongoDB Atlas, OpsForge leverages historical telemetry and past outcomes to accelerate decision-making during future incidents.

## 3. Responsibilities
- **Persistent Incident Ingestion**: Store complete incident records combining root cause reports from Agent 3 and recovery actions from Agent 4 into MongoDB Atlas.
- **Vector Embedding Generation**: Generate 768-dimensional semantic embeddings for incident summaries using the Gemini Embedding API (`text-embedding-004`) with deterministic L2-normalized ngram feature vector fallbacks.
- **Atlas Vector Search Execution**: Perform `$vectorSearch` pipeline queries against MongoDB Atlas indexes to retrieve structurally and semantically similar past incidents.
- **Cosine Similarity Fallback**: Provide an in-memory vector similarity ranking mechanism for local fallback operation if Atlas Vector Search indexes are building or offline.
- **Outcome Tracking & Updates**: Record post-recovery health verification status, resolution duration, and operator notes.
- **Knowledge Base Seeding**: Pre-populate MongoDB Atlas with realistic historical incident records for zero-cold-start demonstrability during live testing.

## 4. Architecture
Agent 5 is constructed with a modular, layered architecture separating REST API contracts, agent orchestration, vector generation services, and database integration boundaries:

```
┌────────────────────────────────────────────────────────┐
│                   FastAPI Router                       │
│              (app/routes/memory.py)                    │
└──────────────────────────┬─────────────────────────────┘
                           │
┌──────────────────────────▼─────────────────────────────┐
│                KnowledgeMemoryAgent                    │
│             (app/agents/knowledge_memory.py)           │
└──────────────┬───────────────────────────┬─────────────┘
               │                           │
┌──────────────▼─────────────┐   ┌─────────▼─────────────┐
│    VectorSearchService     │   │  MongoDBAtlasClient   │
│(app/services/vector_search)│   │(app/integrations/mongo)│
└──────────────┬─────────────┘   └─────────┬─────────────┘
               │                           │
               └─────────────┬─────────────┘
                             │
               ┌─────────────▼─────────────┐
               │    MongoDB Atlas Store    │
               │ (incidents collection &   │
               │   $vectorSearch Index)    │
               └───────────────────────────┘
```

## 5. Folder & File Structure
```
opsforge/backend/
├── app/
│   ├── agents/
│   │   └── knowledge_memory.py       # Agent 5 core orchestrator logic
│   ├── integrations/
│   │   └── mongodb_client.py         # MongoDB Atlas & Vector Search client boundary
│   ├── routes/
│   │   └── memory.py                 # FastAPI REST endpoints (/memory/*)
│   ├── schemas/
│   │   └── knowledge.py              # Pydantic data schemas and camelCase contracts
│   └── services/
│       └── vector_search_service.py  # Text embedding & similarity ranking service
└── src/
    └── agents/
        └── README_Agent5.md          # Comprehensive Agent 5 documentation
```

## 6. Workflow (step-by-step)
1. **Incident Resolution Ingestion**: Upstream agents (or API clients) submit an incident summary, root cause, and recovery details via `POST /memory/store`.
2. **Summary Construction**: `KnowledgeMemoryAgent` synthesizes a structured string combining app name, root cause, causal chain, and applied recovery strategy.
3. **Vector Generation**: `VectorSearchService` submits the text to Gemini `text-embedding-004` (or fallback feature generator) to compute a 768-dimensional float vector.
4. **Atlas Database Insertion**: `MongoDBAtlasClient` inserts or upserts the document into the `opsforge.incidents` collection in MongoDB Atlas (or in-memory fallback store).
5. **Similarity Match Request**: When Agent 3 or an operator requests historical context (`POST /memory/similar`), the input query is vectorized.
6. **Vector Search Query**: `MongoDBAtlasClient` executes a `$vectorSearch` pipeline query matching the embedding against stored documents.
7. **Similarity Ranking**: Results are ranked, similarity scores are formatted as percentages (0–100%), and human-readable explanation strings are generated.
8. **Outcome Verification Update**: Post-mitigation verification results update the stored document via `update_incident_outcome`.

## 7. Data Flow
```
[Agent 3 / Agent 4] ──(IncidentReport + RecoveryAction)──> [POST /memory/store]
                                                                 │
                                                   [KnowledgeMemoryAgent]
                                                                 │
                                            ┌────────────────────┴────────────────────┐
                                            ▼                                         ▼
                             [VectorSearchService.generate_embedding]     [MongoDBAtlasClient.insert_incident]
                                            │                                         │
                                 (768-dim float vector)                               │
                                            └────────────────────┬────────────────────┘
                                                                 ▼
                                                    [MongoDB Atlas Database]
                                                 (opsforge.incidents collection)
```

## 8. MongoDB Atlas Collections
- **Database Name**: `opsforge`
- **Collection Name**: `incidents`
- **Document Field Structure**:
  - `id` (str): Unique incident identifier (`INC-XXXXXXXX` or custom string).
  - `deployment_id` (str): Identifier of the target deployment.
  - `app_name` (str): Name of the application.
  - `severity` (str): Severity level (`critical`, `high`, `medium`, `low`, `info`).
  - `status` (str): Lifecycle status (`resolved`, `investigating`, `open`).
  - `root_cause` (str): Concise root cause diagnostic statement.
  - `causal_chain` (List[str]): Ordered causal steps leading to failure.
  - `affected_signals` (List[str]): Anomalous metric or log indicators.
  - `selected_recovery_action` (str): Title of the executed recovery action.
  - `recovery_category` (str): Applied category (`rollback`, `restart`, `scale_up`, `config_patch`, `manual`).
  - `recovery_status` (str): Status of recovery execution (`verified`, `approved`, `pending`).
  - `approved_by` (str): Approver identity.
  - `approval_mode` (str): Approval medium (`ui` or `voice`).
  - `outcome` (Dict): Post-recovery verification details (`success`, `resolution_time_seconds`, `verification_details`).
  - `summary` (str): Complete summary text used for vector search.
  - `vector_embedding` (List[float]): 768-element floating point embedding array.
  - `tags` (List[str]): Categorization and search tags.
  - `created_at` / `updated_at` (str): UTC ISO timestamps.

## 9. Atlas Vector Search Implementation
MongoDB Atlas Vector Search is queried using the `$vectorSearch` aggregation pipeline stage:
```json
[
  {
    "$vectorSearch": {
      "index": "vector_index",
      "path": "vector_embedding",
      "queryVector": [<768 float values>],
      "numCandidates": 50,
      "limit": 5
    }
  },
  {
    "$project": {
      "_id": 0,
      "id": 1,
      "app_name": 1,
      "root_cause": 1,
      "selected_recovery_action": 1,
      "recovery_category": 1,
      "outcome": 1,
      "created_at": 1,
      "score": { "$meta": "vectorSearchScore" }
    }
  }
]
```
If Atlas Vector Search is not configured or in indexing state, `MongoDBAtlasClient` automatically executes a local cosine similarity search fallback across all stored incident documents.

## 10. Embedding Generation
- **Primary Method**: Asynchronous call to Gemini Embedding API endpoint `https://generativelanguage.googleapis.com/v1beta/models/text-embedding-004:embedContent`.
- **Vector Dimension**: `768`
- **Offline / Simulation Fallback**: Deterministic n-gram feature vector generator using MD5 hashing over character 4-grams with L2 normalization:
  $$\text{norm} = \sqrt{\sum_{i=1}^{768} v_i^2}, \quad \hat{v}_i = \frac{v_i}{\text{norm}}$$

## 11. Similar Incident Retrieval
`VectorSearchService.search_similar_incidents` processes search requests:
1. Converts `query_text` into a 768-dimensional query vector.
2. Executes `$vectorSearch` or local cosine similarity calculation.
3. Filters candidates meeting the minimum similarity threshold (`min_score`, default `0.65`).
4. Converts float scores to percentage values ($0–100\%$).
5. Constructs human-readable explanation strings:
   `"{percentage}% similar to Incident #{id} — same fix worked."`
6. Returns a structured `SimilaritySearchResult` containing the top match and ranked matches list.

## 12. APIs / Functions

### REST Endpoints (`app/routes/memory.py`)
- `POST /memory/store`: Store an incident report, recovery action, and outcome into MongoDB Atlas.
- `POST /memory/similar`: Execute semantic vector search to find similar historical incidents.
- `POST /memory/seed`: Pre-populate MongoDB Atlas with 3 sample historical incidents (`INC-PAST-001`, `INC-PAST-002`, `INC-PAST-003`).
- `GET /memory/incidents`: Retrieve a list of stored incident memory records.
- `GET /memory/incidents/{incident_id}`: Retrieve a specific incident record document by ID.

### Core Classes & Methods
- **`KnowledgeMemoryAgent`** (`app/agents/knowledge_memory.py`):
  - `store_incident(report, action, outcome_success, operator_notes) -> IncidentRecord`
  - `query_similar_incidents(query, limit, min_score) -> SimilaritySearchResult`
  - `seed_initial_knowledge() -> int`
  - `get_all_incidents(limit) -> List[Dict]`
- **`VectorSearchService`** (`app/services/vector_search_service.py`):
  - `generate_embedding(text) -> List[float]`
  - `search_similar_incidents(request) -> SimilaritySearchResult`
- **`MongoDBAtlasClient`** (`app/integrations/mongodb_client.py`):
  - `insert_incident(document) -> str`
  - `get_incident_by_id(incident_id) -> Optional[Dict]`
  - `update_incident_outcome(incident_id, outcome_data) -> bool`
  - `vector_search(query_vector, index_name, path, limit) -> List[Dict]`
  - `list_all_incidents(limit) -> List[Dict]`

## 13. Integration with Agent 3 & Agent 4
- **Integration with Agent 3 (Telemetry & Root Cause Agent)**:
  During root cause investigation, Agent 3 queries `POST /memory/similar` using its candidate root cause summary. The returned `top_match` similarity percentage and past resolution are attached to the `IncidentReport` to inform recommendation confidence.
- **Integration with Agent 4 (Recovery & Voice Approval Agent)**:
  When Agent 4 completes recovery execution and health verification, it calls `POST /memory/store` to write the full incident lifecycle record (root cause + chosen fix + outcome) into MongoDB Atlas memory.

## 14. Environment Variables
- `MONGODB_ATLAS_URI`: MongoDB Atlas connection string (`mongodb+srv://...`).
- `GEMINI_API_KEY`: API key used for Gemini text embeddings.
- `BACKEND_HOST`: Backend binding host (default: `127.0.0.1`).
- `BACKEND_PORT`: Backend binding port (default: `8000`).

## 15. Error Handling
- **Missing PyMongo / Connection Timeout**: Automatically degrades gracefully to in-memory simulation mode without raising unhandled runtime crashes.
- **Gemini API Network Error / Rate Limit**: Falls back to deterministic L2-normalized feature vector generation.
- **Missing Atlas Vector Index**: Aggregation pipeline failure is caught and redirected to local cosine similarity search over stored documents.
- **Invalid Payload Validation**: Pydantic schema validation returns structured HTTP 400/422 responses.

## 16. Performance Considerations
- **Index Latency**: Atlas Vector Search queries execute in sub-100ms using Hierarchical Navigable Small World (HNSW) indexing.
- **Fallback Memory Bound**: Local cosine similarity fallback limits in-memory document scans to prevent main thread blocking.
- **Async HTTP Calls**: Embedding requests to Gemini utilize non-blocking `httpx.AsyncClient` timeouts.

## 17. Security Considerations
- **Credential Protection**: Connection URIs and API keys are managed exclusively via environment variables (`Settings`).
- **No Direct Shell Input**: Storage and query parameters are parsed and sanitized via Pydantic models before database execution.
- **ReadOnly Projection**: Queries exclude MongoDB internal `_id` fields in API responses.

## 18. Current Limitations
- **In-Memory Volatility (Fallback Mode)**: When operating in simulation fallback mode (without a live MongoDB connection), stored incidents persist only for the lifespan of the backend process.
- **Static Vector Index Name**: Default vector search index name is assumed to be `vector_index`.
- **Single Tenant Scope**: Document storage does not currently partition by multi-tenant organization IDs.

## 19. Future Improvements
- **Automated Index Provisioning**: Programmatically trigger Atlas Search Index creation via MongoDB Atlas Admin API.
- **Hybrid Search**: Combine MongoDB text search (`$text`) with `$vectorSearch` for hybrid keyword-semantic scoring.
- **Multi-Tenant Partitioning**: Add `tenant_id` metadata filtering to the `$vectorSearch` aggregation pipeline.
