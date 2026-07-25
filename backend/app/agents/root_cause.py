import asyncio
from typing import Optional, List, Dict, Any

from app.schemas.incident import IncidentAnalysisRequest, IncidentReport
from app.services.telemetry_service import detect_incident, correlate
from app.services.rca_service import RCAService
from app.agents.knowledge_memory import KnowledgeMemoryAgent
from app.integrations.gemini_client import GeminiClient
from app.utils.logger import get_logger

logger = get_logger()


class RootCauseAgent:
    """
    Agent 3 entry point (Integrated with Agent 5 Knowledge Memory).

    Accepts an IncidentAnalysisRequest, runs the full pipeline:
      1. Rule-based incident detection
      2. Signal correlation
      3. Agent 5 Atlas Vector Search lookup for similar historical incidents
      4. Gemini RCA analysis incorporating historical memory
    Returns a validated IncidentReport for consumption by Agent 4.
    """

    def __init__(
        self,
        gemini_client: Optional[GeminiClient] = None,
        knowledge_agent: Optional[KnowledgeMemoryAgent] = None
    ) -> None:
        self._rca_service = RCAService(gemini_client=gemini_client)
        self.knowledge_agent = knowledge_agent or KnowledgeMemoryAgent()

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

