"""
MongoDB Atlas Client for Agent 5 (Knowledge Memory Agent).

Provides robust connection management to MongoDB Atlas with:
- Incident memory document storage in MongoDB Atlas
- Support for MongoDB Atlas Vector Search ($vectorSearch aggregation pipeline)
- Resilient local fallback vector similarity calculations when Atlas Vector Search index is pending or offline
- Outcome updates and incident record querying
"""

import math
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from app.utils.config import settings
from app.utils.logger import get_logger

logger = get_logger()

# Optional PyMongo import handling for local fallback operation
try:
    import pymongo
    from pymongo import MongoClient
    PYMONGO_AVAILABLE = True
except ImportError:
    PYMONGO_AVAILABLE = False
    logger.warning("pymongo is not installed. MongoDBAtlasClient will operate in in-memory simulation mode.")


class MongoDBAtlasClient:
    """
    Production-grade client boundary for MongoDB Atlas and Atlas Vector Search.
    
    Supports both live MongoDB Atlas database connections and an in-memory
    simulated storage fallback for offline demo resilience.
    """

    def __init__(self, uri: Optional[str] = None, db_name: str = "OpsForge", collection_name: str = "incidents"):
        self.uri = uri or getattr(settings, "MONGODB_ATLAS_URI", "")
        self.db_name = db_name
        self.collection_name = collection_name
        
        self.client = None
        self.db = None
        self.collection = None
        
        # In-memory storage for offline / simulation mode fallback
        self._in_memory_store: Dict[str, Dict[str, Any]] = {}
        self.is_connected = False
        
        self._initialize_connection()

    def _initialize_connection(self):
        """Attempts connection to MongoDB Atlas if URI is configured and pymongo is available."""
        if not PYMONGO_AVAILABLE:
            logger.info("MongoDB client operating in in-memory simulation mode (pymongo absent).")
            return

        if not self.uri or "username:password" in self.uri or "your_mongodb" in self.uri:
            logger.info("MONGODB_ATLAS_URI not fully configured. Operating in resilient simulation mode.")
            return

        try:
            self.client = MongoClient(self.uri, serverSelectionTimeoutMS=5000)
            # Trigger server selection check
            self.client.admin.command('ping')
            self.db = self.client[self.db_name]
            self.collection = self.db[self.collection_name]
            self.is_connected = True
            logger.info(f"Successfully connected to MongoDB Atlas database '{self.db_name}' collection '{self.collection_name}'")
        except Exception as e:
            logger.warning(f"Could not connect to live MongoDB Atlas ({e}). Falling back to simulation mode.")
            self.is_connected = False
            self.client = None
            self.db = None
            self.collection = None

    def ensure_connected(self) -> bool:
        """Re-attempts MongoDB connection if not currently connected. Returns True if connected."""
        if self.is_connected and self.collection is not None:
            return True
        # Only retry if we have a valid URI and pymongo is available
        if PYMONGO_AVAILABLE and self.uri and "username:password" not in self.uri and "your_mongodb" not in self.uri:
            logger.info(f"Attempting MongoDB reconnection to '{self.db_name}'...")
            self._initialize_connection()
        return self.is_connected

    def insert_incident(self, document: Dict[str, Any]) -> str:
        """
        Inserts a complete incident record document into MongoDB Atlas or memory store.
        Returns the inserted document ID.
        """
        doc_id = document.get("id") or str(document.get("_id", f"inc-{int(datetime.utcnow().timestamp())}"))
        document["id"] = doc_id
        document["updated_at"] = datetime.utcnow().isoformat()
        if "created_at" not in document:
            document["created_at"] = datetime.utcnow().isoformat()

        # Always maintain local memory store as instant fallback
        self._in_memory_store[doc_id] = document

        self.ensure_connected()
        if self.is_connected and self.collection is not None:
            try:
                # Upsert into Atlas
                self.collection.replace_one({"id": doc_id}, document, upsert=True)
                logger.info(f"Inserted/updated document '{doc_id}' in MongoDB Atlas database '{self.db_name}'.")
            except Exception as e:
                logger.error(f"Failed inserting document into MongoDB Atlas: {e}. Stored in memory fallback.")
        else:
            logger.info(f"Stored document '{doc_id}' in local memory simulation store.")

        return doc_id

    def get_incident_by_id(self, incident_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves a single incident document by ID."""
        self.ensure_connected()
        if self.is_connected and self.collection is not None:
            try:
                doc = self.collection.find_one({"id": incident_id}, {"_id": 0})
                if doc:
                    return doc
            except Exception as e:
                logger.error(f"Error querying MongoDB Atlas for ID {incident_id}: {e}")

        return self._in_memory_store.get(incident_id)

    def update_incident_outcome(self, incident_id: str, outcome_data: Dict[str, Any]) -> bool:
        """Updates the recovery outcome of an existing incident record."""
        update_fields = {
            "outcome": outcome_data,
            "status": "resolved" if outcome_data.get("success") else "investigating",
            "updated_at": datetime.utcnow().isoformat()
        }

        if self.is_connected and self.collection is not None:
            try:
                res = self.collection.update_one({"id": incident_id}, {"$set": update_fields})
                if res.modified_count > 0 or res.matched_count > 0:
                    logger.info(f"Updated outcome for incident '{incident_id}' in MongoDB Atlas.")
                    return True
            except Exception as e:
                logger.error(f"Failed updating outcome in MongoDB Atlas: {e}")

        if incident_id in self._in_memory_store:
            self._in_memory_store[incident_id].update(update_fields)
            logger.info(f"Updated outcome for incident '{incident_id}' in local memory store.")
            return True

        return False

    def vector_search(
        self,
        query_vector: List[float],
        index_name: str = "vector_index",
        path: str = "vector_embedding",
        limit: int = 5,
        num_candidates: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Executes MongoDB Atlas Vector Search using the $vectorSearch aggregation pipeline stage.
        Falls back to local cosine similarity calculation if Atlas Vector Search is unconfigured.
        """
        results: List[Dict[str, Any]] = []

        if self.is_connected and self.collection is not None:
            try:
                pipeline = [
                    {
                        "$vectorSearch": {
                            "index": index_name,
                            "path": path,
                            "queryVector": query_vector,
                            "numCandidates": num_candidates,
                            "limit": limit
                        }
                    },
                    {
                        "$project": {
                            "_id": 0,
                            "id": 1,
                            "app_name": 1,
                            "root_cause": 1,
                            "selected_recovery_action": 1,
                            "recovery_category": 1,
                            "outcome": 1,
                            "created_at": 1,
                            "score": {"$meta": "vectorSearchScore"}
                        }
                    }
                ]
                cursor = self.collection.aggregate(pipeline)
                for doc in cursor:
                    results.append(doc)
                if results:
                    logger.info(f"Atlas Vector Search returned {len(results)} matches via MongoDB pipeline.")
                    return results
            except Exception as e:
                logger.warning(f"Atlas Vector Search pipeline execution skipped/failed ({e}). Utilizing fallback vector matching.")

        # Fallback local cosine similarity search
        return self._fallback_cosine_vector_search(query_vector, limit=limit)

    def _fallback_cosine_vector_search(
        self,
        query_vector: List[float],
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """Calculates cosine similarity over stored documents for offline / fallback search."""
        all_docs: List[Dict[str, Any]] = []

        # Gather documents from live DB or in-memory store
        if self.is_connected and self.collection is not None:
            try:
                all_docs = list(self.collection.find({}, {"_id": 0}))
            except Exception as e:
                logger.error(f"Error fetching docs for fallback search: {e}")
                all_docs = list(self. _in_memory_store.values())
        else:
            all_docs = list(self._in_memory_store.values())

        scored_docs = []
        for doc in all_docs:
            doc_vector = doc.get("vector_embedding") or doc.get("vectorEmbedding")
            if not doc_vector or len(doc_vector) != len(query_vector):
                continue
            
            similarity = self._cosine_similarity(query_vector, doc_vector)
            doc_copy = dict(doc)
            doc_copy["score"] = round(similarity, 4)
            scored_docs.append(doc_copy)

        # Sort descending by score
        scored_docs.sort(key=lambda x: x["score"], reverse=True)
        return scored_docs[:limit]

    @staticmethod
    def _cosine_similarity(vec_a: List[float], vec_b: List[float]) -> float:
        """Computes cosine similarity between two numeric vectors."""
        dot_product = sum(a * b for a, b in zip(vec_a, vec_b))
        norm_a = math.sqrt(sum(a * a for a in vec_a))
        norm_b = math.sqrt(sum(b * b for b in vec_b))
        
        if norm_a == 0.0 or norm_b == 0.0:
            return 0.0
        return max(0.0, min(1.0, dot_product / (norm_a * norm_b)))

    def list_all_incidents(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Returns all stored incident records ordered by creation timestamp."""
        if self.is_connected and self.collection is not None:
            try:
                cursor = self.collection.find({}, {"_id": 0}).sort("created_at", -1).limit(limit)
                return list(cursor)
            except Exception as e:
                logger.error(f"Error listing incidents from MongoDB Atlas: {e}")

        docs = list(self._in_memory_store.values())
        docs.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        return docs[:limit]
