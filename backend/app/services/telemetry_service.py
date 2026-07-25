"""
Telemetry Service — Agent 3 (Telemetry & Root Cause Agent)

Responsibility:
  Aggregate raw deployment telemetry (logs, metrics, events) into a
  normalized CorrelatedIncident for Gemini analysis.

  This module contains two sequential stages:
    1. Incident Detection  — rule-based, deterministic
    2. Correlation Layer   — unifies and sorts all signals into a timeline
"""

from typing import List, Dict, Optional
from datetime import datetime, timezone

from app.schemas.incident import (
    IncidentAnalysisRequest,
    CorrelatedIncident,
    CorrelatedTimelineEntry,
    LogEntry,
    MetricPoint,
    DeploymentEvent,
    Severity,
)
from app.utils.logger import get_logger

logger = get_logger()


# ---------------------------------------------------------------------------
# Detection thresholds (tunable constants — never hardcoded inside logic)
# ---------------------------------------------------------------------------

CPU_CRITICAL_THRESHOLD     = 90.0   # %
RAM_CRITICAL_THRESHOLD     = 90.0   # %
ERROR_RATE_THRESHOLD       = 0.05   # 5% error ratio
LATENCY_CRITICAL_MS        = 2000   # 2 000 ms P99
ERROR_LOG_LIMIT            = 5      # ≥N ERROR logs triggers detection
CRASH_KEYWORDS             = {"oom", "killed", "segfault", "panic", "out of memory", "exit code 1", "exit code 137"}
FAILURE_EVENT_TYPES        = {"DEPLOY_FAILED", "HEALTH_CHECK_FAILED", "CONTAINER_CRASH", "OOM_KILL", "ROLLBACK_TRIGGERED"}


# ---------------------------------------------------------------------------
# Stage 1: Rule-based Incident Detection
# ---------------------------------------------------------------------------

def _detect_log_errors(logs: List[LogEntry]) -> Optional[str]:
    error_count = sum(1 for l in logs if l.level.upper() in {"ERROR", "FATAL", "CRITICAL"})
    if error_count >= ERROR_LOG_LIMIT:
        return f"{error_count} ERROR/FATAL log lines detected (threshold: {ERROR_LOG_LIMIT})"
    return None


def _detect_crash_keywords(logs: List[LogEntry]) -> Optional[str]:
    for entry in logs:
        msg_lower = entry.message.lower()
        for kw in CRASH_KEYWORDS:
            if kw in msg_lower:
                return f"Crash keyword '{kw}' found in logs at {entry.timestamp.isoformat()}"
    return None


def _detect_metric_anomalies(metrics: List[MetricPoint]) -> List[str]:
    reasons: List[str] = []
    cpu_peaks   = [m.value for m in metrics if m.name == "cpu_percent"]
    ram_peaks   = [m.value for m in metrics if m.name == "ram_percent"]
    error_rates = [m.value for m in metrics if m.name == "error_rate"]
    latencies   = [m.value for m in metrics if m.name == "p99_latency_ms"]

    if cpu_peaks and max(cpu_peaks) >= CPU_CRITICAL_THRESHOLD:
        reasons.append(f"CPU peaked at {max(cpu_peaks):.1f}% (threshold: {CPU_CRITICAL_THRESHOLD}%)")
    if ram_peaks and max(ram_peaks) >= RAM_CRITICAL_THRESHOLD:
        reasons.append(f"RAM peaked at {max(ram_peaks):.1f}% (threshold: {RAM_CRITICAL_THRESHOLD}%)")
    if error_rates and max(error_rates) >= ERROR_RATE_THRESHOLD:
        reasons.append(f"Error rate peaked at {max(error_rates)*100:.1f}% (threshold: {ERROR_RATE_THRESHOLD*100:.1f}%)")
    if latencies and max(latencies) >= LATENCY_CRITICAL_MS:
        reasons.append(f"P99 latency peaked at {max(latencies):.0f}ms (threshold: {LATENCY_CRITICAL_MS}ms)")

    return reasons


def _detect_failure_events(events: List[DeploymentEvent]) -> List[str]:
    reasons: List[str] = []
    for event in events:
        if event.event_type.upper() in FAILURE_EVENT_TYPES:
            reasons.append(f"Failure event: {event.event_type} at {event.timestamp.isoformat()}")
    return reasons


def detect_incident(request: IncidentAnalysisRequest) -> tuple[bool, List[str]]:
    """
    Run all detection rules against the telemetry payload.
    Returns (incident_detected: bool, detection_reasons: List[str]).
    """
    reasons: List[str] = []

    log_error_reason = _detect_log_errors(request.logs)
    if log_error_reason:
        reasons.append(log_error_reason)

    crash_reason = _detect_crash_keywords(request.logs)
    if crash_reason:
        reasons.append(crash_reason)

    reasons.extend(_detect_metric_anomalies(request.metrics))
    reasons.extend(_detect_failure_events(request.events))

    return bool(reasons), reasons


# ---------------------------------------------------------------------------
# Stage 2: Correlation Layer
# ---------------------------------------------------------------------------

def _severity_from_log_level(level: str) -> Optional[Severity]:
    mapping = {
        "CRITICAL": Severity.CRITICAL,
        "FATAL":    Severity.CRITICAL,
        "ERROR":    Severity.HIGH,
        "WARN":     Severity.MEDIUM,
        "WARNING":  Severity.MEDIUM,
        "INFO":     Severity.INFO,
        "DEBUG":    Severity.INFO,
    }
    return mapping.get(level.upper())


def _build_metric_summary(metrics: List[MetricPoint]) -> Dict[str, float]:
    """Compute peak values per metric name for the Gemini context block."""
    peaks: Dict[str, float] = {}
    for m in metrics:
        current_peak = peaks.get(m.name, float("-inf"))
        if m.value > current_peak:
            peaks[m.name] = round(m.value, 4)
    return peaks


def correlate(request: IncidentAnalysisRequest, detection_reasons: List[str]) -> CorrelatedIncident:
    """
    Normalize all telemetry signals into a unified chronological timeline.
    Deduplicates overlapping timestamps by preserving insertion order.
    """
    entries: List[CorrelatedTimelineEntry] = []

    # Map log entries
    for log in request.logs:
        entries.append(CorrelatedTimelineEntry(
            timestamp=log.timestamp,
            source_type="log",
            label=f"[{log.level.upper()}] {log.source}",
            detail=log.message,
            severity=_severity_from_log_level(log.level),
        ))

    # Map metric observations (only anomalous readings to keep context concise)
    for metric in request.metrics:
        is_anomalous = (
            (metric.name == "cpu_percent"     and metric.value >= CPU_CRITICAL_THRESHOLD) or
            (metric.name == "ram_percent"     and metric.value >= RAM_CRITICAL_THRESHOLD) or
            (metric.name == "error_rate"      and metric.value >= ERROR_RATE_THRESHOLD)   or
            (metric.name == "p99_latency_ms"  and metric.value >= LATENCY_CRITICAL_MS)
        )
        if is_anomalous:
            entries.append(CorrelatedTimelineEntry(
                timestamp=metric.timestamp,
                source_type="metric",
                label=f"[METRIC] {metric.name}",
                detail=f"{metric.value}{metric.unit}",
                severity=Severity.HIGH,
            ))

    # Map deployment events
    for event in request.events:
        severity = Severity.HIGH if event.event_type.upper() in FAILURE_EVENT_TYPES else Severity.INFO
        entries.append(CorrelatedTimelineEntry(
            timestamp=event.timestamp,
            source_type="event",
            label=f"[EVENT] {event.event_type}",
            detail=event.description or str(event.metadata),
            severity=severity,
        ))

    # Sort unified timeline chronologically
    entries.sort(key=lambda e: e.timestamp)

    incident_detected = bool(detection_reasons)

    logger.info(
        f"Correlator produced {len(entries)} timeline entries for deployment '{request.deployment_id}'. "
        f"Incident detected: {incident_detected}."
    )

    return CorrelatedIncident(
        deployment_id=request.deployment_id,
        app_name=request.app_name,
        incident_detected=incident_detected,
        detection_reasons=detection_reasons,
        timeline=entries,
        metric_summary=_build_metric_summary(request.metrics),
    )
