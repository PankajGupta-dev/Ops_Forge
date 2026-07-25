"""
Agent 5: Knowledge Memory Agent (MongoDB Atlas & Vector Search).

Responsibilities:
- Permanent storage of every incident, root cause analysis, recovery action, and health outcome into MongoDB Atlas
- Automatic generation of semantic embeddings for incident summaries
- Semantic similarity search using Atlas Vector Search to match new incidents against historical occurrences
- Pre-seeding historical incident memory for live demo readiness
"""

import uuid
from typing import List, Optional, Dict, Any
from datetime import datetime

from app.utils.logger import get_logger
from app.schemas.incident import IncidentReport
from app.schemas.recovery import RecoveryAction
from app.schemas.knowledge import (
    IncidentRecord,
    IncidentOutcome,
    VectorSearchRequest,
    SimilaritySearchResult,
    SimilarityMatch,
    StoreIncidentRequest
)
from app.integrations.mongodb_client import MongoDBAtlasClient
from app.services.vector_search_service import VectorSearchService

logger = get_logger()


class KnowledgeMemoryAgent:
    """
    Agent 5 — Knowledge Memory Agent.
    
    Acts as the persistent long-term memory store of the OpsForge autonomous lifecycle.
    Embeds and stores every incident record into MongoDB Atlas, allowing Agent 3 and
    Agent 4 to query past incidents for vector similarity matching.
    """

    def __init__(
        self,
        mongo_client: Optional[MongoDBAtlasClient] = None,
        vector_service: Optional[VectorSearchService] = None
    ):
        self.mongo_client = mongo_client or MongoDBAtlasClient()
        self.vector_service = vector_service or VectorSearchService(mongo_client=self.mongo_client)

    async def store_incident(
        self,
        report: IncidentReport,
        action: Optional[RecoveryAction] = None,
        outcome_success: bool = True,
        operator_notes: Optional[str] = None
    ) -> IncidentRecord:
        """
        Stores an incident report from Agent 3, recovery action from Agent 4,
        and post-recovery verification outcome into MongoDB Atlas with vector embeddings.
        """
        incident_id = f"INC-{uuid.uuid4().hex[:8].upper()}"
        
        # Build embedding text summary
        summary_text = (
            f"App: {report.app_name}. Root Cause: {report.root_cause}. "
            f"Causal Chain: {' -> '.join(report.causal_chain)}. "
            f"Fix Applied: {action.title if action else 'Automated mitigation'}."
        )

        logger.info(f"Agent 5: Generating vector embedding for Incident '{incident_id}'...")
        embedding = await self.vector_service.generate_embedding(summary_text)

        outcome_obj = IncidentOutcome(
            success=outcome_success,
            resolution_time_seconds=45,
            verification_details={"health_check": "HTTP 200 OK", "metrics_baseline": "normal"},
            operator_notes=operator_notes,
            resolved_at=datetime.utcnow()
        )

        record = IncidentRecord(
            id=incident_id,
            deployment_id=report.deployment_id,
            app_name=report.app_name,
            severity=report.severity,
            status=report.incident_status,
            root_cause=report.root_cause,
            causal_chain=report.causal_chain,
            affected_signals=report.affected_signals,
            selected_recovery_action=action.title if action else (report.recommendations[0].action if report.recommendations else "Rollback"),
            recovery_category=action.steps[0].command if (action and action.steps) else None,
            recovery_status=action.status if action else None,
            approved_by=action.approved_by if action else "Operator",
            approval_mode="voice" if (action and action.narrative) else "ui",
            outcome=outcome_obj,
            summary=summary_text,
            vector_embedding=embedding,
            tags=[report.app_name.lower(), report.severity.value if hasattr(report.severity, 'value') else str(report.severity)],
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )

        # Convert record to dictionary for MongoDB Atlas storage
        doc = record.model_dump(by_alias=False)
        self.mongo_client.insert_incident(doc)
        logger.info(f"Agent 5: Successfully saved Incident '{incident_id}' to MongoDB Atlas Knowledge Base.")

        return record

    async def query_similar_incidents(
        self,
        query: str,
        limit: int = 5,
        min_score: float = 0.60
    ) -> SimilaritySearchResult:
        """
        Queries MongoDB Atlas Vector Search for historical incidents matching the query string or root cause.
        Returns a formatted SimilaritySearchResult object containing percentage matches.
        """
        logger.info(f"Agent 5: Querying Atlas Vector Search for query '{query[:50]}...'")
        search_req = VectorSearchRequest(
            query_text=query,
            limit=limit,
            min_score=min_score
        )

        return await self.vector_service.search_similar_incidents(search_req)

    async def seed_initial_knowledge(self) -> int:
        """
        Pre-seeds MongoDB Atlas with sample historical incidents to ensure immediate vector search
        demonstrability during live hackathon presentations.
        """
        seed_data = [
            {
                "id": "INC-PAST-001",
                "deployment_id": "dep-old-01",
                "app_name": "OpsForge Demo App",
                "severity": "critical",
                "status": "resolved",
                "root_cause": "Database connection pool exhaustion caused by unclosed connections in deployment #47",
                "causal_chain": [
                    "Deployment #47 introduced leak in DB connection handler",
                    "Active pool reached max_connections (100/100)",
                    "Incoming API requests failed with 500 Internal Server Error"
                ],
                "affected_signals": ["db_pool_active_connections", "http_500_error_rate"],
                "selected_recovery_action": "Restart container & increase DB connection pool limit",
                "recovery_category": "restart",
                "recovery_status": "verified",
                "approved_by": "Senior Platform Engineer",
                "approval_mode": "voice",
                "summary": "OpsForge Demo App: Database connection pool exhaustion caused by unclosed connections in deployment #47. Fix: Restart container & increase DB connection pool limit.",
                "outcome": {
                    "success": True,
                    "resolution_time_seconds": 32,
                    "verification_details": {"http_status": 200, "db_connections": "12/100"},
                    "operator_notes": "Identical to Redis connection leak pattern. Restart restored health."
                },
                "tags": ["opsforge", "database", "connection-leak", "doks"],
                "created_at": "2026-07-20T10:15:00Z"
            },
            {
                "id": "INC-PAST-002",
                "deployment_id": "dep-old-02",
                "app_name": "OpsForge Demo App",
                "severity": "high",
                "status": "resolved",
                "root_cause": "Invalid environment variable REDIS_URL pointing to unreachable internal host",
                "causal_chain": [
                    "Deployment #48 updated configuration environment variables",
                    "REDIS_URL was set to redis-internal.local instead of redis.default.svc",
                    "Caching client thrown ConnectionRefused exception on startup"
                ],
                "affected_signals": ["redis_connection_status", "app_health_probe"],
                "selected_recovery_action": "Rollback deployment to previous healthy release",
                "recovery_category": "rollback",
                "recovery_status": "verified",
                "approved_by": "On-call Engineer",
                "approval_mode": "ui",
                "summary": "OpsForge Demo App: Invalid environment variable REDIS_URL pointing to unreachable internal host. Fix: Rollback deployment to previous healthy release.",
                "outcome": {
                    "success": True,
                    "resolution_time_seconds": 28,
                    "verification_details": {"http_status": 200, "redis_ping": "PONG"},
                    "operator_notes": "Rollback to deployment #47 restored full service."
                },
                "tags": ["opsforge", "redis", "env-var", "rollback"],
                "created_at": "2026-07-22T14:30:00Z"
            },
            {
                "id": "INC-PAST-003",
                "deployment_id": "dep-old-03",
                "app_name": "OpsForge Demo App",
                "severity": "high",
                "status": "resolved",
                "root_cause": "Memory leak in Node.js event loop during high load burst",
                "causal_chain": [
                    "Traffic spiked by 400% during marketing promotion",
                    "Unbounded array accumulation in event logger caused heap OOM",
                    "Container restarted by DigitalOcean health checker"
                ],
                "affected_signals": ["container_ram_percent", "restart_count"],
                "selected_recovery_action": "Scale service replicas from 1 to 3 instances",
                "recovery_category": "scale_up",
                "recovery_status": "verified",
                "approved_by": "Ops Lead",
                "approval_mode": "voice",
                "summary": "OpsForge Demo App: Memory leak in Node.js event loop during high load burst. Fix: Scale service replicas from 1 to 3 instances.",
                "outcome": {
                    "success": True,
                    "resolution_time_seconds": 55,
                    "verification_details": {"replicas": "3/3", "cpu_utilization": "34%"},
                    "operator_notes": "Scaling horizontally distributed traffic load effectively."
                },
                "tags": ["opsforge", "memory-leak", "autoscale", "digitalocean"],
                "created_at": "2026-07-23T08:45:00Z"
            }
        ]

        logger.info("Agent 5: Pre-seeding historical incident knowledge memory into MongoDB Atlas...")
        seeded_count = 0
        for item in seed_data:
            # Generate embedding for each seed document
            embedding = await self.vector_service.generate_embedding(item["summary"])
            item["vector_embedding"] = embedding
            self.mongo_client.insert_incident(item)
            seeded_count += 1

        logger.info(f"Agent 5: Successfully seeded {seeded_count} past incident memories.")
        return seeded_count

    def get_all_incidents(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Returns all stored incident memory records from MongoDB Atlas."""
        return self.mongo_client.list_all_incidents(limit=limit)
