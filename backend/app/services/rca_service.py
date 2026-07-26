"""
Root Cause Analysis Service — Agent 3 (Telemetry & Root Cause Agent)

Responsibility:
  Orchestrate the full RCA pipeline:
    CorrelatedIncident
      → prompt construction
      → Gemini generation
      → Pydantic validation (with single retry)
      → IncidentReport

  One retry is attempted on validation failure, feeding back the exact
  error text so Gemini can correct its output.
"""

import json
import os
from typing import Optional

from fastapi import HTTPException

from app.schemas.incident import (
    CorrelatedIncident,
    CorrelatedTimelineEntry,
    IncidentReport,
    IncidentStatus,
    Severity,
)
from app.integrations.gemini_client import GeminiClient, GeminiAPIError
from app.utils.logger import get_logger

logger = get_logger()

PROMPT_FILE_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "prompts", "rca.txt"
)

# Maximum timeline entries forwarded to Gemini (keeps token count bounded).
MAX_TIMELINE_ENTRIES = 80


class RCAService:
    def __init__(self, gemini_client: Optional[GeminiClient] = None) -> None:
        self.gemini_client  = gemini_client or GeminiClient()
        self._system_prompt = self._load_system_prompt()

    # ------------------------------------------------------------------
    # Prompt Construction
    # ------------------------------------------------------------------

    def _load_system_prompt(self) -> str:
        if os.path.exists(PROMPT_FILE_PATH):
            with open(PROMPT_FILE_PATH, "r", encoding="utf-8") as f:
                return f.read()
        return (
            "You are OpsForge Agent 3. Analyse the incident evidence and return "
            "a strict JSON IncidentReport object. No markdown. No code fences."
        )

    def build_prompt(
        self,
        incident: CorrelatedIncident,
        historical_matches: Optional[list] = None,
        retry_error: Optional[str] = None,
    ) -> str:
        """Construct the user-turn prompt from correlated incident data and Agent 5 historical memory."""

        # Trim timeline to MAX_TIMELINE_ENTRIES (most recent anomalous first).
        timeline_slice = incident.timeline[-MAX_TIMELINE_ENTRIES:]

        timeline_text_parts: list[str] = []
        for entry in timeline_slice:
            sev = f" [{entry.severity.value.upper()}]" if entry.severity else ""
            timeline_text_parts.append(
                f"  {entry.timestamp.isoformat()}{sev} {entry.label}: {entry.detail}"
            )
        timeline_text = "\n".join(timeline_text_parts) or "  (no timeline entries)"

        metric_text = "\n".join(
            f"  {name}: peak={value}" for name, value in incident.metric_summary.items()
        ) or "  (no metric data)"

        detection_text = "\n".join(
            f"  - {r}" for r in incident.detection_reasons
        ) or "  (no detection rules triggered)"

        # Format historical incident matches from Agent 5
        if historical_matches:
            hist_parts = []
            for idx, match in enumerate(historical_matches, 1):
                match_dict = match if isinstance(match, dict) else (match.model_dump() if hasattr(match, 'model_dump') else dict(match))
                score_pct = match_dict.get("similarity_percentage", int(match_dict.get("similarity_score", 0) * 100))
                inc_id = match_dict.get("incident_id", "INC-UNKNOWN")
                root_c = match_dict.get("root_cause", "Unknown")
                rec_act = match_dict.get("recovery_action", "N/A")
                success = match_dict.get("outcome_success", True)
                hist_parts.append(
                    f"  Match {idx}: [{score_pct}% Similar] Incident '{inc_id}' ({match_dict.get('app_name', 'App')})\n"
                    f"    - Historical Root Cause: {root_c}\n"
                    f"    - Past Recovery Action: {rec_act}\n"
                    f"    - Outcome: {'SUCCESS (Resolved)' if success else 'FAILED'}"
                )
            historical_text = "\n".join(hist_parts)
        else:
            historical_text = "  No prior similar incidents found in Agent 5 Knowledge Base."

        prompt_parts = [
            "=== INCIDENT CONTEXT ===",
            f"Deployment ID : {incident.deployment_id}",
            f"Application   : {incident.app_name}",
            f"Incident Flag : {'YES' if incident.incident_detected else 'NO — analyse for anomalies anyway'}",
            "",
            "=== DETECTION RULES TRIGGERED ===",
            detection_text,
            "",
            "=== PEAK METRIC SUMMARY ===",
            metric_text,
            "",
            "=== UNIFIED TIMELINE (chronological) ===",
            timeline_text,
            "",
            "=== HISTORICAL SIMILAR INCIDENTS (AGENT 5 KNOWLEDGE MEMORY) ===",
            historical_text,
            "",
            "=== TASK ===",
            "Produce a complete IncidentReport JSON object. Required fields:",
            "  deployment_id (string), app_name (string), incident_status ('open'|'investigating'|'resolved'),",
            "  severity ('critical'|'high'|'medium'|'low'|'info'), root_cause (string),",
            "  causal_chain (list of strings), affected_signals (list of strings), contributing_factors (list of strings),",
            "  recommendations (list of objects with fields: rank (int), category ('rollback'|'restart'|'scale_up'|'config_patch'|'manual'), action (string), rationale (string), risk (string)),",
            "  confidence (float 0.0-1.0), summary (string), warnings (list of strings).",
            "Incorporate insights from Agent 5 historical matches if relevant to recommend proven recovery actions.",
        ]

        if retry_error:
            prompt_parts.extend([
                "",
                "=== PREVIOUS ATTEMPT FAILED SCHEMA VALIDATION ===",
                f"Error: {retry_error}",
                "Correct your JSON to strictly match the required schema types and values.",
            ])

        return "\n".join(prompt_parts)

    # ------------------------------------------------------------------
    # JSON Cleaning
    # ------------------------------------------------------------------

    @staticmethod
    def _clean_json(text: str) -> str:
        """Strip markdown fences that Gemini may include despite instructions."""
        cleaned = text.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        elif cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        return cleaned.strip()

    # ------------------------------------------------------------------
    # Pipeline Orchestration
    # ------------------------------------------------------------------

    async def analyse(
        self,
        incident: CorrelatedIncident,
        historical_matches: Optional[list] = None
    ) -> IncidentReport:
        """
        Run the full RCA pipeline.
        Raises HTTPException on unrecoverable failure.
        """
        logger.info(
            f"Starting RCA for deployment '{incident.deployment_id}'. "
            f"Timeline entries: {len(incident.timeline)}. "
            f"Incident detected: {incident.incident_detected}. "
            f"Historical matches: {len(historical_matches) if historical_matches else 0}."
        )

        prompt = self.build_prompt(incident, historical_matches=historical_matches)

        # Convert historical_matches to serializable dicts for IncidentReport
        matches_serialized = []
        if historical_matches:
            for m in historical_matches:
                if isinstance(m, dict):
                    matches_serialized.append(m)
                elif hasattr(m, 'model_dump'):
                    matches_serialized.append(m.model_dump(by_alias=True))
                elif hasattr(m, 'dict'):
                    matches_serialized.append(m.dict())

        from datetime import datetime, timezone

        def _enrich_and_audit(rpt: IncidentReport) -> IncidentReport:
            if not rpt.trace_id and incident.trace_id:
                rpt.trace_id = incident.trace_id
            if not rpt.app_id and incident.app_id:
                rpt.app_id = incident.app_id
            rpt.similar_incidents = matches_serialized
            
            logger.info(
                f"[AUDIT LOG] trace_id='{rpt.trace_id}' | app_id='{rpt.app_id}' | deployment_id='{rpt.deployment_id}' | "
                f"agent_name='Agent 3 (Root Cause)' | action='INCIDENT_ANALYSIS_COMPLETED' | "
                f"timestamp='{datetime.now(timezone.utc).isoformat()}' | status='SUCCESS'"
            )
            return rpt

        # --- Attempt 1 ---
        try:
            raw = await self.gemini_client.generate_json(
                prompt=prompt,
                system_instruction=self._system_prompt,
            )
        except GeminiAPIError as exc:
            logger.error(
                f"[AUDIT LOG] trace_id='{incident.trace_id}' | app_id='{incident.app_id}' | deployment_id='{incident.deployment_id}' | "
                f"agent_name='Agent 3 (Root Cause)' | action='INCIDENT_ANALYSIS_FAILED' | "
                f"timestamp='{datetime.now(timezone.utc).isoformat()}' | status='FAILED'"
            )
            logger.error(f"Gemini API error on first attempt: {exc}")
            raise HTTPException(status_code=502, detail=f"Gemini API failure: {str(exc)}")

        cleaned = self._clean_json(raw)

        first_err_msg: str = ""
        try:
            report = IncidentReport.model_validate(json.loads(cleaned))
            logger.info("IncidentReport validated on first attempt.")
            return _enrich_and_audit(report)
        except Exception as exc:
            first_err_msg = str(exc)
            logger.warning(f"Validation failed on first attempt: {first_err_msg}")

        # --- Attempt 2 (single retry with error feedback) ---
        logger.info("Initiating single retry with validation feedback.")
        retry_prompt = self.build_prompt(incident, historical_matches=historical_matches, retry_error=first_err_msg)

        try:
            retry_raw = await self.gemini_client.generate_json(
                prompt=retry_prompt,
                system_instruction=self._system_prompt,
            )
            retry_cleaned = self._clean_json(retry_raw)
            report = IncidentReport.model_validate(json.loads(retry_cleaned))
            logger.info("IncidentReport validated on retry attempt.")
            return _enrich_and_audit(report)
        except Exception as retry_err:
            logger.error(
                f"[AUDIT LOG] trace_id='{incident.trace_id}' | app_id='{incident.app_id}' | deployment_id='{incident.deployment_id}' | "
                f"agent_name='Agent 3 (Root Cause)' | action='INCIDENT_ANALYSIS_FAILED' | "
                f"timestamp='{datetime.now(timezone.utc).isoformat()}' | status='FAILED'"
            )
            logger.error(f"RCA validation failed after retry: {retry_err}")
            raise HTTPException(
                status_code=422,
                detail={
                    "error": "Failed to parse or validate Gemini RCA response.",
                    "details": str(retry_err),
                },
            )

