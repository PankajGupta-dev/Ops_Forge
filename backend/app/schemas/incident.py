"""
Pydantic schemas for Agent 3: Telemetry & Root Cause Analysis.

All data contracts between the telemetry collector, correlator,
Gemini analysis, and downstream Agent 4 are defined here.
"""

from typing import List, Optional, Dict, Any
from enum import Enum
from datetime import datetime
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class Severity(str, Enum):
    CRITICAL = "critical"
    HIGH     = "high"
    MEDIUM   = "medium"
    LOW      = "low"
    INFO     = "info"


class IncidentStatus(str, Enum):
    OPEN        = "open"
    INVESTIGATING = "investigating"
    RESOLVED    = "resolved"


class RecoveryCategory(str, Enum):
    ROLLBACK      = "rollback"
    RESTART       = "restart"
    SCALE_UP      = "scale_up"
    CONFIG_PATCH  = "config_patch"
    MANUAL        = "manual"


# ---------------------------------------------------------------------------
# Input: Telemetry Data Structures
# ---------------------------------------------------------------------------

class LogEntry(BaseModel):
    """A single structured log line from a deployment or service."""
    timestamp: datetime = Field(..., description="UTC timestamp of the log event")
    level:     str      = Field(..., description="Log level: ERROR, WARN, INFO, DEBUG")
    message:   str      = Field(..., description="Raw log message content")
    source:    str      = Field(default="app", description="Origin source (app, platform, infra)")


class MetricPoint(BaseModel):
    """A single time-series metric observation."""
    timestamp: datetime = Field(..., description="UTC timestamp of the metric sample")
    name:      str      = Field(..., description="Metric name (cpu_percent, ram_percent, error_rate, p99_latency_ms)")
    value:     float    = Field(..., description="Numeric metric value")
    unit:      str      = Field(default="", description="Unit label (%, ms, req/s)")


class DeploymentEvent(BaseModel):
    """A discrete event from the deployment lifecycle."""
    timestamp:   datetime         = Field(..., description="UTC timestamp of the event")
    event_type:  str              = Field(..., description="Event type: DEPLOY_STARTED, DEPLOY_FAILED, HEALTH_CHECK_FAILED, etc.")
    description: str              = Field(default="", description="Human-readable event summary")
    metadata:    Dict[str, Any]   = Field(default_factory=dict, description="Structured event metadata")


# ---------------------------------------------------------------------------
# Input: Analysis Request (API surface for POST /incident/analyze)
# ---------------------------------------------------------------------------

class IncidentAnalysisRequest(BaseModel):
    """Request body submitted by the caller to trigger root cause analysis."""
    trace_id:      Optional[str] = Field(None, description="Globally unique trace identifier")
    app_id:        Optional[str] = Field(None, description="Cloud application platform identifier")
    deployment_id: str           = Field(..., description="Unique deployment identifier (from Agent 2)")
    app_name:      str           = Field(..., description="Human-readable application name")
    deployment_status: Optional[str] = Field(None, description="Status of the deployment")
    infrastructure_metadata: Dict[str, Any] = Field(default_factory=dict, description="Metadata from infrastructure provider")
    logs:          List[LogEntry]        = Field(default_factory=list, description="Structured log entries")
    metrics:       List[MetricPoint]     = Field(default_factory=list, description="Time-series metric observations")
    events:        List[DeploymentEvent] = Field(default_factory=list, description="Deployment lifecycle events")


# ---------------------------------------------------------------------------
# Internal: Correlation Layer
# ---------------------------------------------------------------------------

class CorrelatedTimelineEntry(BaseModel):
    """A single normalized entry in the unified incident timeline."""
    timestamp:   datetime         = Field(..., description="UTC timestamp")
    source_type: str              = Field(..., description="Origin: log | metric | event")
    label:       str              = Field(..., description="Short label describing this entry")
    detail:      str              = Field(default="", description="Full content or reading")
    severity:    Optional[Severity] = Field(None, description="Assigned severity tier (if applicable)")


class CorrelatedIncident(BaseModel):
    """Normalized, chronologically-sorted incident timeline ready for Gemini."""
    trace_id:          Optional[str]            = Field(None, description="Trace identifier")
    app_id:            Optional[str]            = Field(None, description="Cloud application identifier")
    deployment_id:     str                      = Field(..., description="Deployment identifier")
    app_name:          str                      = Field(..., description="Application name")
    incident_detected: bool                     = Field(..., description="True if rule-based detection fired")
    detection_reasons: List[str]                = Field(default_factory=list, description="Triggered detection rules")
    timeline:          List[CorrelatedTimelineEntry] = Field(default_factory=list, description="Unified chronological event timeline")
    metric_summary:    Dict[str, float]         = Field(default_factory=dict, description="Peak metric readings (cpu, ram, error_rate)")


# ---------------------------------------------------------------------------
# Output: Recovery Recommendation (consumed by Agent 4)
# ---------------------------------------------------------------------------

class RecoveryRecommendation(BaseModel):
    """A single ranked recovery action recommended by Gemini."""
    rank:        int              = Field(..., ge=1, description="Priority rank (1 = highest)")
    category:    RecoveryCategory = Field(..., description="Recovery action category")
    action:      str              = Field(..., description="Precise recovery action description")
    rationale:   str              = Field(..., description="Why this action addresses the root cause")
    risk:        str              = Field(..., description="Potential risks or side-effects")
    estimated_ttm_minutes: Optional[int] = Field(None, description="Estimated time-to-mitigate in minutes")
    target_deployment_id: Optional[str] = Field(None, description="Target deployment run identifier for rollback operations")


# ---------------------------------------------------------------------------
# Output: Incident Report (final contract, consumed by Agent 4)
# ---------------------------------------------------------------------------

class IncidentReport(BaseModel):
    """
    Fully validated root cause analysis report produced by Agent 3.
    This is the output contract consumed by Agent 4 (Recovery & Voice).
    """
    trace_id:         Optional[str]             = Field(None, description="Globally unique trace identifier")
    app_id:           Optional[str]             = Field(None, description="Cloud application platform identifier")
    deployment_id:    str                       = Field(..., description="Deployment under analysis")
    app_name:         str                       = Field(..., description="Application name")
    incident_status:  IncidentStatus            = Field(..., description="Current incident status")
    severity:         Severity                  = Field(..., description="Overall incident severity")
    root_cause:       str                       = Field(..., description="Concise root cause statement")
    causal_chain:     List[str]                 = Field(..., min_length=1, description="Ordered causal chain of events leading to failure")
    affected_signals: List[str]                 = Field(default_factory=list, description="Metrics or services exhibiting anomalies")
    contributing_factors: List[str]             = Field(default_factory=list, description="Secondary factors that amplified the incident")
    recommendations:  List[RecoveryRecommendation] = Field(..., min_length=1, description="Ranked recovery recommendations")
    confidence:       float                     = Field(..., ge=0.0, le=1.0, description="Gemini confidence score for root cause (0.0–1.0)")
    summary:          str                       = Field(..., description="Single-paragraph executive summary for the operator")
    warnings:         List[str]                 = Field(default_factory=list, description="Any analysis caveats or data quality warnings")
    similar_incidents: List[Dict[str, Any]]     = Field(default_factory=list, description="Historical incidents retrieved from Agent 5 Vector Search")

