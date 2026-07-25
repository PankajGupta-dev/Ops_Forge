import sys
import os
import unittest
from unittest.mock import AsyncMock, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.schemas.incident import (
    IncidentReport,
    IncidentStatus,
    Severity,
    RecoveryCategory,
    RecoveryRecommendation,
)
from app.schemas.recovery import RecoveryApprovalRequest, RecoveryStatus
from app.schemas.knowledge import IncidentRecord
from app.agents.recovery_voice import RecoveryVoiceAgent
from app.agents.knowledge_memory import KnowledgeMemoryAgent


class TestAgent4Agent5Integration(unittest.IsolatedAsyncioTestCase):

    async def test_agent4_executes_recovery_and_stores_memory_in_agent5(self):
        # 1. Setup mock KnowledgeMemoryAgent (Agent 5)
        mock_knowledge_agent = KnowledgeMemoryAgent()
        mock_record = IncidentRecord(
            id="INC-STORED-123456",
            deployment_id="dep-recovered-01",
            app_name="OpsForge Payment Service",
            severity=Severity.HIGH,
            status=IncidentStatus.RESOLVED,
            root_cause="Database pool exhausted",
            causal_chain=["DB connections reached maximum limit"],
            affected_signals=["db_pool_connections"],
            selected_recovery_action="Restart Application",
            summary="OpsForge Payment Service: Database pool exhausted. Fix: Restart Application.",
            tags=["payment", "database"]
        )

        mock_knowledge_agent.store_incident = AsyncMock(return_value=mock_record)

        # 2. Setup mock Infra & Deploy Agent
        mock_infra_agent = MagicMock()
        mock_infra_agent.execute_recovery = AsyncMock(return_value={"status": "success"})

        # 3. Instantiate Agent 4 with mocked Agent 5 & Infra agent
        agent4 = RecoveryVoiceAgent(
            infra_agent=mock_infra_agent,
            knowledge_agent=mock_knowledge_agent
        )

        agent4.recovery_service.el_client.text_to_speech = AsyncMock(return_value=b"mock-audio-bytes")
        agent4.recovery_service.gemini_client.generate_json = AsyncMock(
            return_value='{"narration": "Restarting application to restore health."}'
        )

        # 4. Create incident report
        report = IncidentReport(
            deployment_id="dep-recovered-01",
            app_name="OpsForge Payment Service",
            incident_status=IncidentStatus.OPEN,
            severity=Severity.HIGH,
            root_cause="Database pool exhausted",
            causal_chain=["DB connections reached maximum limit"],
            affected_signals=["db_pool_connections"],
            contributing_factors=[],
            recommendations=[
                RecoveryRecommendation(
                    rank=1,
                    category=RecoveryCategory.RESTART,
                    action="Restart application instances to flush pool",
                    rationale="Flushes dead pool connections",
                    risk="low",
                    estimated_ttm_minutes=1
                )
            ],
            confidence=0.92,
            summary="Database pool connection exhaustion on payment service.",
            warnings=[]
        )

        # 5. Generate recovery plan (Agent 4)
        action = await agent4.create_recovery_plan(report)
        self.assertEqual(action.status, RecoveryStatus.PENDING)
        self.assertEqual(action.title, "Restart Application")

        # 6. Approve action (Operator)
        approval_req = RecoveryApprovalRequest(approved=True, approver="Lead DevOps", approval_mode="ui")
        approved_action = agent4.process_approval(action.id, approval_req)
        self.assertEqual(approved_action.status, RecoveryStatus.APPROVED)

        # 7. Execute action (Agent 4 triggers execution + Agent 5 long-term memory storage)
        executed_action = await agent4.execute_recovery(action.id)

        # 8. Assertions
        self.assertEqual(executed_action.status, RecoveryStatus.VERIFIED)
        self.assertEqual(executed_action.incident_record_id, "INC-STORED-123456")
        self.assertTrue(mock_knowledge_agent.store_incident.called)

        # Verify arguments passed to Agent 5 store_incident
        call_kwargs = mock_knowledge_agent.store_incident.call_args.kwargs
        self.assertEqual(call_kwargs["report"].deployment_id, "dep-recovered-01")
        self.assertEqual(call_kwargs["action"].id, action.id)
        self.assertTrue(call_kwargs["outcome_success"])


if __name__ == "__main__":
    unittest.main()
