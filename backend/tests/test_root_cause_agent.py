"""
Unit Tests — Agent 3: Telemetry & Root Cause Agent

Tests cover:
  - Rule-based incident detection (positive & negative cases)
  - Correlation layer (timeline sorting, metric filtering)
  - RCA Service (Gemini mocked)
  - Route contract (via FastAPI TestClient)
"""

import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch, MagicMock

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.schemas.incident import (
    IncidentAnalysisRequest,
    LogEntry,
    MetricPoint,
    DeploymentEvent,
    Severity,
    IncidentStatus,
    RecoveryCategory,
    RecoveryRecommendation,
    IncidentReport,
    CorrelatedIncident,
)
from app.services.telemetry_service import (
    detect_incident,
    correlate,
    CPU_CRITICAL_THRESHOLD,
    ERROR_LOG_LIMIT,
)

client = TestClient(app)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

NOW = datetime(2024, 6, 1, 12, 0, 0, tzinfo=timezone.utc)


def _log(level: str, msg: str, offset_seconds: int = 0) -> LogEntry:
    ts = datetime(2024, 6, 1, 12, 0, offset_seconds, tzinfo=timezone.utc)
    return LogEntry(timestamp=ts, level=level, message=msg, source="app")


def _metric(name: str, value: float, offset_seconds: int = 0) -> MetricPoint:
    ts = datetime(2024, 6, 1, 12, 0, offset_seconds, tzinfo=timezone.utc)
    return MetricPoint(timestamp=ts, name=name, value=value, unit="%")


def _event(event_type: str, desc: str = "", offset_seconds: int = 0) -> DeploymentEvent:
    ts = datetime(2024, 6, 1, 12, 0, offset_seconds, tzinfo=timezone.utc)
    return DeploymentEvent(timestamp=ts, event_type=event_type, description=desc)


def _make_report(**overrides) -> dict:
    base = {
        "deployment_id":    "dep-001",
        "app_name":         "test-app",
        "incident_status":  "open",
        "severity":         "high",
        "root_cause":       "OOM kill due to memory leak",
        "causal_chain":     ["Memory leak in worker", "OOM killer triggered"],
        "affected_signals": ["ram_percent"],
        "contributing_factors": ["No autoscaling"],
        "recommendations":  [{
            "rank": 1,
            "category": "restart",
            "action": "Restart the application container",
            "rationale": "Clears leaked memory state",
            "risk": "Brief downtime",
            "estimated_ttm_minutes": 2,
        }],
        "confidence": 0.87,
        "summary": "Memory exhaustion caused an OOM kill.",
        "warnings": [],
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# Detection Tests
# ---------------------------------------------------------------------------

class TestIncidentDetection:
    def _request(self, logs=None, metrics=None, events=None) -> IncidentAnalysisRequest:
        return IncidentAnalysisRequest(
            deployment_id="dep-001",
            app_name="test-app",
            logs=logs or [],
            metrics=metrics or [],
            events=events or [],
        )

    def test_no_signals_no_incident(self):
        req = self._request()
        detected, reasons = detect_incident(req)
        assert detected is False
        assert reasons == []

    def test_error_log_threshold_triggers(self):
        logs = [_log("ERROR", f"err {i}", i) for i in range(ERROR_LOG_LIMIT)]
        req = self._request(logs=logs)
        detected, reasons = detect_incident(req)
        assert detected is True
        assert any("ERROR" in r for r in reasons)

    def test_below_error_log_threshold_no_trigger(self):
        logs = [_log("ERROR", f"err {i}", i) for i in range(ERROR_LOG_LIMIT - 1)]
        req = self._request(logs=logs)
        detected, _ = detect_incident(req)
        assert detected is False

    def test_crash_keyword_triggers(self):
        logs = [_log("ERROR", "Process killed: out of memory")]
        req = self._request(logs=logs)
        detected, reasons = detect_incident(req)
        assert detected is True
        # A crash keyword matched — the reason contains "Crash keyword" header text.
        assert any("Crash keyword" in r for r in reasons)

    def test_cpu_spike_triggers(self):
        metrics = [_metric("cpu_percent", CPU_CRITICAL_THRESHOLD + 1)]
        req = self._request(metrics=metrics)
        detected, reasons = detect_incident(req)
        assert detected is True
        assert any("CPU" in r for r in reasons)

    def test_failure_event_triggers(self):
        events = [_event("DEPLOY_FAILED", "Container exit 1")]
        req = self._request(events=events)
        detected, reasons = detect_incident(req)
        assert detected is True
        assert any("DEPLOY_FAILED" in r for r in reasons)

    def test_only_info_logs_no_incident(self):
        logs = [_log("INFO", "App started", i) for i in range(20)]
        req = self._request(logs=logs)
        detected, _ = detect_incident(req)
        assert detected is False


# ---------------------------------------------------------------------------
# Correlation Tests
# ---------------------------------------------------------------------------

class TestCorrelation:
    def _request(self, logs=None, metrics=None, events=None) -> IncidentAnalysisRequest:
        return IncidentAnalysisRequest(
            deployment_id="dep-002",
            app_name="test-app",
            logs=logs or [],
            metrics=metrics or [],
            events=events or [],
        )

    def test_timeline_is_chronologically_sorted(self):
        logs = [
            _log("ERROR", "late error", offset_seconds=30),
            _log("INFO",  "early info", offset_seconds=0),
        ]
        req = self._request(logs=logs)
        correlated = correlate(req, [])
        timestamps = [e.timestamp for e in correlated.timeline]
        assert timestamps == sorted(timestamps)

    def test_anomalous_metrics_included_normal_excluded(self):
        metrics = [
            _metric("cpu_percent", 50.0),          # normal — excluded
            _metric("cpu_percent", 95.0, offset_seconds=10),  # anomalous — included
        ]
        req = self._request(metrics=metrics)
        correlated = correlate(req, [])
        metric_entries = [e for e in correlated.timeline if e.source_type == "metric"]
        assert len(metric_entries) == 1
        assert "95.0" in metric_entries[0].detail

    def test_metric_summary_tracks_peaks(self):
        metrics = [
            _metric("cpu_percent", 40.0),
            _metric("cpu_percent", 88.0, offset_seconds=5),
            _metric("cpu_percent", 70.0, offset_seconds=10),
        ]
        req = self._request(metrics=metrics)
        correlated = correlate(req, [])
        assert correlated.metric_summary["cpu_percent"] == 88.0

    def test_empty_input_produces_empty_timeline(self):
        req = self._request()
        correlated = correlate(req, [])
        assert correlated.timeline == []
        assert correlated.incident_detected is False


# ---------------------------------------------------------------------------
# RCA Service Tests (Gemini mocked)
# ---------------------------------------------------------------------------

class TestRCAService:
    @pytest.mark.asyncio
    async def test_successful_rca_on_first_attempt(self):
        from app.services.rca_service import RCAService
        report_dict = _make_report()

        mock_client = MagicMock()
        mock_client.generate_json = AsyncMock(return_value=json.dumps(report_dict))

        service = RCAService(gemini_client=mock_client)
        correlated = CorrelatedIncident(
            deployment_id="dep-001",
            app_name="test-app",
            incident_detected=True,
            detection_reasons=["OOM detected"],
            timeline=[],
            metric_summary={"ram_percent": 95.0},
        )
        result = await service.analyse(correlated)
        assert isinstance(result, IncidentReport)
        assert result.severity == Severity.HIGH
        assert result.confidence == 0.87

    @pytest.mark.asyncio
    async def test_retry_on_first_validation_failure(self):
        from app.services.rca_service import RCAService
        report_dict = _make_report()

        mock_client = MagicMock()
        # First call returns invalid JSON; second returns valid.
        mock_client.generate_json = AsyncMock(
            side_effect=["not valid json", json.dumps(report_dict)]
        )

        service = RCAService(gemini_client=mock_client)
        correlated = CorrelatedIncident(
            deployment_id="dep-001",
            app_name="test-app",
            incident_detected=True,
            detection_reasons=[],
            timeline=[],
            metric_summary={},
        )
        result = await service.analyse(correlated)
        assert isinstance(result, IncidentReport)
        assert mock_client.generate_json.call_count == 2

    @pytest.mark.asyncio
    async def test_raises_422_after_double_failure(self):
        from app.services.rca_service import RCAService
        from fastapi import HTTPException

        mock_client = MagicMock()
        mock_client.generate_json = AsyncMock(return_value="invalid json always")

        service = RCAService(gemini_client=mock_client)
        correlated = CorrelatedIncident(
            deployment_id="dep-001",
            app_name="test-app",
            incident_detected=False,
            detection_reasons=[],
            timeline=[],
            metric_summary={},
        )
        with pytest.raises(HTTPException) as exc_info:
            await service.analyse(correlated)
        assert exc_info.value.status_code == 422


# ---------------------------------------------------------------------------
# Route Contract Tests
# ---------------------------------------------------------------------------

class TestIncidentRoute:
    def _payload(self, **overrides) -> dict:
        base = {
            "deployment_id": "dep-test",
            "app_name": "test-app",
            "logs": [{"timestamp": "2024-06-01T12:00:00Z", "level": "ERROR", "message": "oom kill", "source": "app"}],
            "metrics": [],
            "events": [],
        }
        base.update(overrides)
        return base

    def test_missing_deployment_id_returns_400(self):
        payload = self._payload(deployment_id="")
        resp = client.post("/incident/analyze", json=payload)
        assert resp.status_code == 400

    def test_missing_app_name_returns_400(self):
        payload = self._payload(app_name="")
        resp = client.post("/incident/analyze", json=payload)
        assert resp.status_code == 400

    def test_empty_telemetry_returns_400(self):
        payload = self._payload(logs=[], metrics=[], events=[])
        resp = client.post("/incident/analyze", json=payload)
        assert resp.status_code == 400

    def test_valid_payload_calls_agent(self):
        report_dict = _make_report()
        with patch(
            "app.routes.incidents._agent.run",
            new_callable=AsyncMock,
            return_value=IncidentReport(**report_dict),
        ):
            resp = client.post("/incident/analyze", json=self._payload())
        assert resp.status_code == 200
        body = resp.json()
        assert body["deployment_id"] == "dep-001"
        assert body["severity"] == "high"
        assert len(body["recommendations"]) == 1
