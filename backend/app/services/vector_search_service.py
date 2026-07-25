"""
Vector Search Service for Agent 5 (Knowledge Memory Agent).

Handles:
- Generating text embeddings using Gemini API (or deterministic fallback vectors)
- Executing semantic vector similarity searches against MongoDB Atlas
- Formatting vector search results with confidence scores and percentage explanations
"""

import math
import hashlib
import httpx
from typing import List, Optional, Dict, Any

from app.utils.config import settings
from app.utils.logger import get_logger
from app.integrations.mongodb_client import MongoDBAtlasClient
from app.schemas.knowledge import (
    VectorSearchRequest,
    SimilaritySearchResult,
    SimilarityMatch
)

logger = get_logger()

# Dimension for vector embeddings (matches standard embedding models)
EMBEDDING_DIMENSION = 768


class VectorSearchService:
    """
    Service layer providing text embedding generation and vector search orchestration
    against MongoDB Atlas Vector Search.
    """

    def __init__(self, mongo_client: Optional[MongoDBAtlasClient] = None):
        self.mongo_client = mongo_client or MongoDBAtlasClient()

    async def generate_embedding(self, text: str) -> List[float]:
        """
        Generates a 768-dimensional vector embedding for the input text using Gemini API
        or fallback deterministic feature vector generator.
        """
        if not text or not text.strip():
            return [0.0] * EMBEDDING_DIMENSION

        api_key = getattr(settings, "GEMINI_API_KEY", "")
        if api_key and "your_gemini" not in api_key:
            try:
                embedding = await self._call_gemini_embedding_api(text, api_key)
                if embedding and len(embedding) > 0:
                    return embedding
            except Exception as e:
                logger.warning(f"Gemini embedding API call failed ({e}). Utilizing fallback vector embedding generator.")

        return self._generate_fallback_vector(text)

    async def _call_gemini_embedding_api(self, text: str, api_key: str) -> List[float]:
        """Calls Gemini embedding API endpoint (text-embedding-004)."""
        url = f"https://generativelanguage.googleapis.com/v1beta/models/text-embedding-004:embedContent?key={api_key}"
        payload = {
            "model": "models/text-embedding-004",
            "content": {
                "parts": [{"text": text}]
            }
        }

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(url, json=payload)
            if response.status_code == 200:
                data = response.json()
                values = data.get("embedding", {}).get("values", [])
                if values:
                    return values

        raise ValueError(f"Gemini API returned status {response.status_code}: {response.text}")

    @staticmethod
    def _generate_fallback_vector(text: str, dimension: int = EMBEDDING_DIMENSION) -> List[float]:
        """
        Generates a deterministic normalized semantic feature vector for text when offline.
        Uses SHA-256 seed hashing over n-grams to preserve string similarity properties.
        """
        tokens = text.lower().split()
        vector = [0.0] * dimension

        for token in tokens:
            for i in range(len(token)):
                ngram = token[i:i+4]
                hash_val = int(hashlib.md5(ngram.encode("utf-8")).hexdigest(), 16)
                idx = hash_val % dimension
                weight = 1.0 + (hash_val % 10) / 10.0
                vector[idx] += weight

        # L2 Normalize
        norm = math.sqrt(sum(val * val for val in vector))
        if norm > 0:
            vector = [round(val / norm, 6) for val in vector]
        else:
            vector = [1.0 / math.sqrt(dimension)] * dimension

        return vector

    async def search_similar_incidents(
        self,
        request: VectorSearchRequest
    ) -> SimilaritySearchResult:
        """
        Executes semantic vector similarity search against stored historical incidents.
        Returns a formatted SimilaritySearchResult object.
        """
        query_text = request.query_text or ""
        if not query_text:
            return SimilaritySearchResult(
                query="",
                total_matches=0,
                top_match=None,
                matches=[]
            )

        logger.info(f"Generating vector embedding for query: '{query_text[:60]}...'")
        query_vector = await self.generate_embedding(query_text)

        raw_results = self.mongo_client.vector_search(
            query_vector=query_vector,
            limit=request.limit
        )

        matches: List[SimilarityMatch] = []
        for idx, doc in enumerate(raw_results):
            score = float(doc.get("score", doc.get("similarity_score", 0.0)))
            if score < request.min_score and len(raw_results) > 1 and idx > 0:
                continue

            pct = int(round(score * 100))
            # Bound score percentage between 0 and 100
            pct = max(0, min(100, pct))

            outcome_info = doc.get("outcome", {})
            outcome_success = outcome_info.get("success", True) if isinstance(outcome_info, dict) else True
            action_title = doc.get("selected_recovery_action") or doc.get("selectedRecoveryAction") or "Executed automated recovery"

            explanation = f"{pct}% similar to Incident #{doc.get('id', 'N/A')} — {'same fix worked' if outcome_success else 'previous mitigation attempted'}."

            match_obj = SimilarityMatch(
                incident_id=str(doc.get("id", f"INC-{idx+1}")),
                app_name=doc.get("app_name") or doc.get("appName") or "OpsForge Service",
                root_cause=doc.get("root_cause") or doc.get("rootCause") or "System failure detected",
                recovery_action=action_title,
                recovery_category=doc.get("recovery_category") or doc.get("recoveryCategory"),
                outcome_success=outcome_success,
                similarity_score=score,
                similarity_percentage=pct,
                explanation=explanation,
                created_at=doc.get("created_at") or doc.get("createdAt") or "2026-07-24T00:00:00Z"
            )
            matches.append(match_obj)

        top_match = matches[0] if matches else None

        return SimilaritySearchResult(
            query=query_text,
            total_matches=len(matches),
            top_match=top_match,
            matches=matches
        )
