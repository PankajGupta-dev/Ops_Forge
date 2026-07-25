"""
Pydantic schemas for Agent 5: Knowledge Memory Agent (MongoDB Atlas & Vector Search).

Defines output and input data structures for:
- Incident memory records stored in MongoDB Atlas
- Recovery action and outcome tracking
- Vector similarity search requests and match results
- Knowledge base seeding endpoints
"""

from typing import List, Optional, Dict, Any
from enum import Enum
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict
from pydantic.alias_generators import to_camel

from app.schemas.incident import Severity, IncidentStatus, RecoveryCategory
from app.schemas.recovery import RecoveryStatus


class CamelBaseModel(BaseModel):
    """Base schema enforcing camelCase aliases for clean frontend integration."""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        use_enum_values=True
    )


class IncidentOutcome(CamelBaseModel):
    """Record of the final recovery outcome and health verification."""
    success: bool = Field(..., description="Whether the recovery action successfully restored system health")
    resolution_time_seconds: Optional[int] = Field(None, description="Time taken from incident detection to health verification")
    verification_details: Dict[str, Any] = Field(default_factory=dict, description="Metrics and health probe check results")
    operator_notes: Optional[str] = Field(None, description="Optional notes or feedback provided by the operator")
    resolved_at: Optional[datetime] = Field(default_factory=datetime.utcnow, description="UTC timestamp of resolution")


class IncidentRecord(CamelBaseModel):
    """
    Complete incident document stored in MongoDB Atlas.
    Combines root cause analysis from Agent 3, recovery execution from Agent 4,
    and outcome status with Atlas Vector Search embeddings.
    """
    id: str = Field(..., description="Unique incident record identifier (UUID or Mongo ObjectId)")
    deployment_id: str = Field(..., description="Target deployment identifier")
    app_name: str = Field(..., description="Application name")
    severity: Severity = Field(..., description="Incident severity level")
    status: IncidentStatus = Field(IncidentStatus.RESOLVED, description="Overall incident lifecycle status")
    root_cause: str = Field(..., description="Concise root cause statement from Agent 3")
    causal_chain: List[str] = Field(default_factory=list, description="Chronological causal steps leading to failure")
    affected_signals: List[str] = Field(default_factory=list, description="Telemetry signals/metrics exhibiting anomalies")
    selected_recovery_action: Optional[str] = Field(None, description="Title of the executed recovery recommendation")
    recovery_category: Optional[RecoveryCategory] = Field(None, description="Category of recovery action applied")
    recovery_status: Optional[RecoveryStatus] = Field(None, description="Status of recovery action execution")
    approved_by: Optional[str] = Field(None, description="Identity of operator who approved recovery")
    approval_mode: Optional[str] = Field(None, description="Approval medium (ui or voice)")
    outcome: Optional[IncidentOutcome] = Field(None, description="Post-recovery health outcome")
    summary: str = Field(..., description="Executive summary used for semantic vector embedding")
    vector_embedding: Optional[List[float]] = Field(default=None, description="Atlas Vector Search embedding vector")
    tags: List[str] = Field(default_factory=list, description="Search and categorization tags")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Record creation timestamp")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Record last updated timestamp")


class VectorSearchRequest(CamelBaseModel):
    """Request payload to perform semantic vector search for past incidents."""
    query_text: Optional[str] = Field(None, description="Free text summary or root cause string to match against history")
    deployment_id: Optional[str] = Field(None, description="Optional deployment filter")
    app_name: Optional[str] = Field(None, description="Optional application filter")
    limit: int = Field(default=5, ge=1, le=20, description="Maximum number of historical matches to return")
    min_score: float = Field(default=0.65, ge=0.0, le=1.0, description="Minimum similarity score threshold (0.0 - 1.0)")


class SimilarityMatch(CamelBaseModel):
    """Single matched historical incident record with vector similarity percentage score."""
    incident_id: str = Field(..., description="Historical incident identifier")
    app_name: str = Field(..., description="Application name of historical incident")
    root_cause: str = Field(..., description="Historical root cause summary")
    recovery_action: Optional[str] = Field(None, description="Recovery action that was executed")
    recovery_category: Optional[RecoveryCategory] = Field(None, description="Category of successful recovery action")
    outcome_success: bool = Field(..., description="Whether the past recovery action succeeded")
    similarity_score: float = Field(..., ge=0.0, le=1.0, description="Vector cosine similarity score (0.0 to 1.0)")
    similarity_percentage: int = Field(..., ge=0, le=100, description="Formatted similarity score percentage (0 - 100%)")
    explanation: str = Field(..., description="Formatted string e.g., '87% similar to Incident #3 — same fix worked.'")
    created_at: datetime = Field(..., description="Timestamp when historical incident occurred")


class SimilaritySearchResult(CamelBaseModel):
    """Result object returned when querying Knowledge Memory for past incidents."""
    query: str = Field(..., description="Input query summary or root cause text used for vector search")
    total_matches: int = Field(..., description="Number of past incidents meeting similarity threshold")
    top_match: Optional[SimilarityMatch] = Field(None, description="Highest scoring historical incident match")
    matches: List[SimilarityMatch] = Field(default_factory=list, description="Ranked list of similar historical incidents")


class StoreIncidentRequest(CamelBaseModel):
    """Payload to store an incident report and recovery outcome into MongoDB Atlas memory."""
    deployment_id: str = Field(..., description="Unique deployment identifier")
    app_name: str = Field(..., description="Application name")
    severity: Severity = Field(..., description="Severity level")
    root_cause: str = Field(..., description="Root cause description")
    causal_chain: List[str] = Field(default_factory=list, description="Causal chain items")
    affected_signals: List[str] = Field(default_factory=list, description="Anomalous metric or log signals")
    selected_recovery_action: Optional[str] = Field(None, description="Executed action description")
    recovery_category: Optional[RecoveryCategory] = Field(None, description="Applied recovery category")
    recovery_status: Optional[RecoveryStatus] = Field(None, description="Recovery status")
    approved_by: Optional[str] = Field("Operator", description="Approver identity")
    approval_mode: Optional[str] = Field("ui", description="Approval mode")
    outcome_success: bool = Field(True, description="Whether recovery succeeded")
    summary: str = Field(..., description="Executive summary for embedding")
    tags: List[str] = Field(default_factory=list, description="Category tags")


class SeedMemoryResponse(CamelBaseModel):
    """Response returned after seeding initial past incidents into MongoDB Atlas."""
    seeded_count: int = Field(..., description="Number of sample historical incidents inserted")
    message: str = Field(..., description="Status summary message")
