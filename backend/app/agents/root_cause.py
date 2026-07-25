import asyncio
from typing import Optional, List, Dict, Any, Tuple
from fastapi import HTTPException

from app.schemas.incident import IncidentAnalysisRequest, IncidentReport
from app.schemas.recovery import RecoveryAction
from app.services.telemetry_service import detect_incident, correlate
from app.services.rca_service import RCAService
from app.agents.knowledge_memory import KnowledgeMemoryAgent
from app.agents.recovery_voice import RecoveryVoiceAgent
from app.integrations.gemini_client import GeminiClient
from app.utils.logger import get_logger

logger = get_logger()


class RootCauseAgent:
    """
    Agent 3 entry point (Integrated with Agent 4 Recovery & Agent 5 Knowledge Memory).

    Accepts an IncidentAnalysisRequest, runs the full pipeline:
      1. Rule-based incident detection
      2. Signal correlation
      3. Agent 5 Atlas Vector Search lookup for similar historical incidents
      4. Gemini RCA analysis incorporating historical memory
      5. Asynchronous handoff to Agent 4 (Recovery & Voice Approval)
    Returns a validated IncidentReport or performs full handoff to Agent 4.
    """

    def __init__(
        self,
        gemini_client: Optional[GeminiClient] = None,
        knowledge_agent: Optional[KnowledgeMemoryAgent] = None,
        recovery_agent: Optional[RecoveryVoiceAgent] = None
    ) -> None:
        self._rca_service = RCAService(gemini_client=gemini_client)
        self.knowledge_agent = knowledge_agent or KnowledgeMemoryAgent()
        self.recovery_agent = recovery_agent or RecoveryVoiceAgent()

    async def run(self, request: IncidentAnalysisRequest) -> IncidentReport:
        """
        Execute the full RCA pipeline with Agent 5 Knowledge Memory vector search.
        """
        logger.info(
            f"Agent 3 invoked for deployment_id='{request.deployment_id}', "
            f"app='{request.app_name}'. "
            f"Logs: {len(request.logs)}, Metrics: {len(request.metrics)}, "
            f"Events: {len(request.events)}."
        )

        # Stage 1: Rule-based Incident Detection
        incident_detected, detection_reasons = detect_incident(request)
        logger.info(
            f"Incident detection result: detected={incident_detected}, "
            f"reasons={len(detection_reasons)}."
        )

        # Stage 2: Correlation — normalize all signals into a unified timeline
        correlated = correlate(request, detection_reasons)

        # Stage 2.5: Agent 5 Atlas Vector Search Query for Similar Historical Incidents
        historical_matches: List[Dict[str, Any]] = []
        error_snippets = [l.message for l in request.logs if l.level.upper() in ("ERROR", "FATAL", "CRITICAL")][:3]
        query_text = (
            f"App: {request.app_name}. "
            f"Detection: {', '.join(detection_reasons) if detection_reasons else 'General anomaly'}. "
            f"Errors: {' '.join(error_snippets)}"
        ).strip()

        logger.info(f"Agent 3: Querying Agent 5 Knowledge Memory for vector similarity match on '{query_text[:60]}...'")
        try:
            search_result = await asyncio.wait_for(
                self.knowledge_agent.query_similar_incidents(
                    query=query_text,
                    limit=3,
                    min_score=0.50
                ),
                timeout=5.0
            )

            if search_result and search_result.matches:
                historical_matches = [m.model_dump(by_alias=False) for m in search_result.matches]
                top_pct = search_result.top_match.similarity_percentage if search_result.top_match else 0
                logger.info(
                    f"Agent 3 -> Agent 5 Integration: Found {len(historical_matches)} similar historical incidents "
                    f"(Top match: {top_pct}% similarity)."
                )
            else:
                logger.info("Agent 3 -> Agent 5 Integration: No similar historical incidents found in Knowledge Memory above threshold.")
        except asyncio.TimeoutError:
            logger.warning("Agent 3 -> Agent 5 Integration: Vector search query timed out (5s). Proceeding with RCA without historical context.")
        except Exception as exc:
            logger.warning(f"Agent 3 -> Agent 5 Integration error (non-fatal): {exc}. Proceeding with standard RCA.")

        # Stage 3: Gemini RCA — generate and validate IncidentReport combining current telemetry & historical memory
        report = await self._rca_service.analyse(correlated, historical_matches=historical_matches)

        logger.info(
            f"Agent 3 complete for '{request.deployment_id}'. "
            f"Severity: {report.severity}, Recommendations: {len(report.recommendations)}, "
            f"Historical Matches Included: {len(report.similar_incidents)}."
        )

        return report

    async def hand_off_to_recovery(
        self,
        report: IncidentReport,
        timeout_seconds: float = 10.0
    ) -> RecoveryAction:
        """
        Agent 3 -> Agent 4 Integration.

        Asynchronously transfers the completed incident analysis payload to Agent 4 (Recovery & Voice Approval).
        Transfers:
          - Root cause (`report.root_cause`)
          - Incident summary (`report.summary`)
          - Severity (`report.severity`)
          - Confidence score (`report.confidence`)
          - Risk level & options (`report.recommendations`)
          - Supporting evidence (`report.causal_chain`, `report.affected_signals`, `report.contributing_factors`, `report.warnings`)

        Handles communication timeouts and validation failures gracefully.
        """
        if not report or not report.recommendations:
            logger.error("Agent 3 -> Agent 4 Handoff Failed: IncidentReport contains no valid recovery recommendations.")
            raise HTTPException(status_code=400, detail="Cannot hand off incident report without recovery recommendations.")

        top_rec = min(report.recommendations, key=lambda r: r.rank)

        logger.info(
            f"[AUDIT LOG] trace_id='{report.trace_id}' | app_id='{report.app_id}' | deployment_id='{report.deployment_id}' | "
            f"agent_name='Agent 3 (Telemetry & RCA)' | action='TRANSMIT_INCIDENT_REPORT_TO_AGENT4' | "
            f"severity='{report.severity}' | confidence='{report.confidence}' | "
            f"top_risk='{top_rec.risk}' | recommendations_count={len(report.recommendations)}"
        )

        try:
            action = await asyncio.wait_for(
                self.recovery_agent.create_recovery_plan(report),
                timeout=timeout_seconds
            )
            logger.info(
                f"Agent 3 -> Agent 4 Integration Success: Transferred incident analysis for deployment '{report.deployment_id}'. "
                f"Generated RecoveryAction ID: '{action.id}' (Status: '{action.status}')."
            )
            return action
        except asyncio.TimeoutError:
            logger.error(f"Agent 3 -> Agent 4 Integration Error: Communication timed out after {timeout_seconds}s while creating recovery plan.")
            raise HTTPException(
                status_code=504,
                detail=f"Communication timeout during Agent 3 to Agent 4 recovery handoff ({timeout_seconds}s limit)."
            )
        except HTTPException as exc:
            raise exc
        except Exception as exc:
            logger.error(f"Agent 3 -> Agent 4 Integration Error: Handoff failed due to unexpected exception: {exc}")
            raise HTTPException(
                status_code=502,
                detail=f"Agent 3 to Agent 4 integration communication failure: {str(exc)}"
            )

    async def run_with_recovery_handoff(
        self,
        request: IncidentAnalysisRequest,
        timeout_seconds: float = 10.0
    ) -> Tuple[IncidentReport, RecoveryAction]:
        """
        End-to-end Agent 3 -> Agent 4 Pipeline Execution.

        1. Executes root cause analysis (Agent 3).
        2. Automatically transfers the structured report to Agent 4.
        3. Returns both the IncidentReport and the generated RecoveryAction.
        """
        report = await self.run(request)
        action = await self.hand_off_to_recovery(report, timeout_seconds=timeout_seconds)
        return report, action
