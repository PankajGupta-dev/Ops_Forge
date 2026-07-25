import sys
import os
import unittest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.schemas.incident import (
    IncidentAnalysisRequest,
    IncidentReport,
    LogEntry,
    MetricPoint,
    DeploymentEvent,
    IncidentStatus,
    Severity,
    RecoveryCategory,
    RecoveryRecommendation,
)
from app.schemas.knowledge import (
    SimilaritySearchResult,
    SimilarityMatch,
    IncidentOutcome,
)
from app.agents.root_cause import RootCauseAgent
from app.agents.knowledge_memory import KnowledgeMemoryAgent


class TestAgent3Agent5Integration(unittest.IsolatedAsyncioTestCase):

    async def test_agent3_queries_agent5_vector_search(self):
        # 1. Setup mock KnowledgeMemoryAgent (Agent 5)
        mock_knowledge_agent = KnowledgeMemoryAgent()
        mock_match = SimilarityMatch(
            incident_id="INC-HISTORICAL-999",
            app_name="OpsForge Demo App",
            root_cause="Database pool exhaustion due to missing connection timeout",
            recovery_action="Restart Application and increase connection pool limit to 50",
            outcome_success=True,
            similarity_score=0.87,
            similarity_percentage=87,
            explanation="87% similar to Incident INC-HISTORICAL-999",
            created_at=datetime.now(timezone.utc)
        )
        mock_search_result = SimilaritySearchResult(
            query="App: OpsForge Demo App. Anomaly: database connection timeout",
            matches=[mock_match],
            total_matches=1,
            top_match=mock_match
        )
        mock_knowledge_agent.query_similar_incidents = AsyncMock(return_value=mock_search_result)


        # 2. Setup mock GeminiClient
        mock_gemini = MagicMock()
        mock_report_json = {
            "deployment_id": "dep-test-123",
            "app_name": "OpsForge Demo App",
            "incident_status": "open",
            "severity": "critical",
            "root_cause": "Database connection pool exhaustion (confirmed by historical pattern)",
            "causal_chain": ["Traffic spike", "Connections exhausted", "HTTP 500 errors"],
            "affected_signals": ["db_connections", "http_500_rate"],
            "contributing_factors": ["Missing timeout config"],
            "recommendations": [
                {
                    "rank": 1,
                    "category": "restart",
                    "action": "Restart Application and scale DB pool",
                    "rationale": "Matches historical incident resolution INC-HISTORICAL-999",
                    "risk": "low",
                    "estimated_ttm_minutes": 2
                }
            ],
            "confidence": 0.95,
            "summary": "Critical database pool exhaustion.",
            "warnings": []
        }

        import json
        mock_gemini.generate_json = AsyncMock(return_value=json.dumps(mock_report_json))

        # 3. Instantiate Agent 3 with injected dependencies
        agent3 = RootCauseAgent(gemini_client=mock_gemini, knowledge_agent=mock_knowledge_agent)

        # 4. Construct telemetry request
        now = datetime.now(timezone.utc)
        req = IncidentAnalysisRequest(
            deployment_id="dep-test-123",
            app_name="OpsForge Demo App",
            logs=[
                LogEntry(timestamp=now, level="ERROR", message="FATAL: connection pool exhausted", source="app")
            ],
            metrics=[
                MetricPoint(timestamp=now, name="db_connections", value=100.0, unit="cnt")
            ],
            events=[]
        )

        # 5. Execute Agent 3 pipeline
        report = await agent3.run(req)

        # 6. Assertions
        self.assertTrue(mock_knowledge_agent.query_similar_incidents.called)
        self.assertEqual(len(report.similar_incidents), 1)
        self.assertEqual(report.similar_incidents[0]["incident_id"], "INC-HISTORICAL-999")
        self.assertIn("Database connection pool exhaustion", report.root_cause)

    async def test_agent3_handles_no_historical_matches(self):
        # Setup mock KnowledgeMemoryAgent with empty search result
        mock_knowledge_agent = KnowledgeMemoryAgent()
        mock_search_result = SimilaritySearchResult(
            query="Query",
            matches=[],
            total_matches=0
        )

        mock_knowledge_agent.query_similar_incidents = AsyncMock(return_value=mock_search_result)

        mock_gemini = MagicMock()
        mock_report_json = {
            "deployment_id": "dep-new-001",
            "app_name": "New App",
            "incident_status": "open",
            "severity": "medium",
            "root_cause": "Novel memory leak in cache layer",
            "causal_chain": ["Unbounded cache insertion"],
            "affected_signals": ["ram_percent"],
            "contributing_factors": [],
            "recommendations": [
                {
                    "rank": 1,
                    "category": "restart",
                    "action": "Restart cache worker",
                    "rationale": "Flushes uncollected garbage",
                    "risk": "low",
                    "estimated_ttm_minutes": 1
                }
            ],
            "confidence": 0.80,
            "summary": "Novel cache memory leak.",
            "warnings": []
        }
        import json
        mock_gemini.generate_json = AsyncMock(return_value=json.dumps(mock_report_json))

        agent3 = RootCauseAgent(gemini_client=mock_gemini, knowledge_agent=mock_knowledge_agent)

        now = datetime.now(timezone.utc)
        req = IncidentAnalysisRequest(
            deployment_id="dep-new-001",
            app_name="New App",
            logs=[LogEntry(timestamp=now, level="ERROR", message="OOM kill worker process", source="kernel")],
            metrics=[],
            events=[]
        )

        report = await agent3.run(req)

        self.assertTrue(mock_knowledge_agent.query_similar_incidents.called)
        self.assertEqual(len(report.similar_incidents), 0)
        self.assertIn("Novel memory leak", report.root_cause)


if __name__ == "__main__":
    unittest.main()
