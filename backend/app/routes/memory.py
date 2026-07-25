"""
FastAPI Route Handlers for Agent 5: Knowledge Memory Agent (MongoDB Atlas & Vector Search).

Exposes REST endpoints for:
- Storing incidents, recovery actions, and outcomes into MongoDB Atlas
- Performing semantic vector similarity searches for past incidents
- Pre-seeding historical incident memory for live demo readiness
- Fetching historical incident audit trails and memory documents
"""

from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, status, Query

from app.schemas.knowledge import (
    StoreIncidentRequest,
    IncidentRecord,
    VectorSearchRequest,
    SimilaritySearchResult,
    SeedMemoryResponse
)
from app.schemas.incident import IncidentReport
from app.agents.knowledge_memory import KnowledgeMemoryAgent
from app.utils.logger import get_logger

logger = get_logger()
router = APIRouter(prefix="/memory", tags=["Knowledge Memory (Agent 5)"])

# Initialize Agent 5 instance
knowledge_agent = KnowledgeMemoryAgent()


@router.post(
    "/store",
    response_model=Dict[str, Any],
    status_code=status.HTTP_201_CREATED,
    summary="Store incident and outcome into MongoDB Atlas memory"
)
async def store_incident(payload: StoreIncidentRequest):
    """
    Stores a complete incident record, selected recovery action, and verification outcome
    into MongoDB Atlas. Automatically computes and indexes a semantic vector embedding.
    """
    try:
        logger.info(f"API POST /memory/store: Storing incident for app '{payload.app_name}'")
        
        # Construct synthetic IncidentReport for the agent method
        from app.schemas.incident import IncidentStatus, Severity
        report = IncidentReport(
            deployment_id=payload.deployment_id,
            app_name=payload.app_name,
            incident_status=IncidentStatus.RESOLVED if payload.outcome_success else IncidentStatus.INVESTIGATING,
            severity=payload.severity,
            root_cause=payload.root_cause,
            causal_chain=payload.causal_chain or [payload.root_cause],
            affected_signals=payload.affected_signals,
            recommendations=[],
            confidence=0.92,
            summary=payload.summary
        )

        record = await knowledge_agent.store_incident(
            report=report,
            outcome_success=payload.outcome_success
        )

        return {
            "success": True,
            "message": f"Incident record '{record.id}' successfully stored in MongoDB Atlas memory.",
            "incident_id": record.id,
            "deployment_id": record.deployment_id
        }
    except Exception as e:
        logger.error(f"Error in POST /memory/store: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to store incident into MongoDB Atlas memory: {str(e)}"
        )


@router.post(
    "/similar",
    response_model=SimilaritySearchResult,
    summary="Search for similar past incidents using Atlas Vector Search"
)
async def search_similar_incidents(payload: VectorSearchRequest):
    """
    Queries MongoDB Atlas Vector Search using semantic vector embeddings.
    Returns ranked historical incident matches with percentage similarity scores
    (e.g., '87% similar to Incident #3 — same fix worked').
    """
    try:
        query_text = payload.query_text or ""
        if not query_text.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="query_text parameter cannot be empty."
            )

        logger.info(f"API POST /memory/similar: Querying vector search for '{query_text[:50]}'")
        result = await knowledge_agent.query_similar_incidents(
            query=query_text,
            limit=payload.limit,
            min_score=payload.min_score
        )
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in POST /memory/similar: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Vector search failed: {str(e)}"
        )


@router.post(
    "/seed",
    response_model=SeedMemoryResponse,
    status_code=status.HTTP_200_OK,
    summary="Seed historical incident memory into MongoDB Atlas for live demo"
)
async def seed_memory():
    """
    Pre-populates MongoDB Atlas with historical incident records and vector embeddings
    to enable instant similarity search demonstrability in live hackathon demos.
    """
    try:
        logger.info("API POST /memory/seed: Initializing demo knowledge memory seeding")
        count = await knowledge_agent.seed_initial_knowledge()
        return SeedMemoryResponse(
            seeded_count=count,
            message=f"Successfully seeded {count} past incident memories into MongoDB Atlas."
        )
    except Exception as e:
        logger.error(f"Error in POST /memory/seed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to seed memory database: {str(e)}"
        )


@router.get(
    "/incidents",
    response_model=List[Dict[str, Any]],
    summary="List all stored incident memory records"
)
async def list_incidents(limit: int = Query(default=20, ge=1, le=100)):
    """Retrieves all historical incident memory documents from MongoDB Atlas."""
    try:
        return knowledge_agent.get_all_incidents(limit=limit)
    except Exception as e:
        logger.error(f"Error in GET /memory/incidents: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed listing incidents: {str(e)}"
        )


@router.get(
    "/incidents/{incident_id}",
    response_model=Dict[str, Any],
    summary="Get details of a specific historical incident record"
)
async def get_incident(incident_id: str):
    """Fetches a single incident memory record document by ID."""
    doc = knowledge_agent.mongo_client.get_incident_by_id(incident_id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Incident memory record '{incident_id}' not found."
        )
    return doc
