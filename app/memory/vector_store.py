"""
Vector Store — Long-Term Semantic Memory
Stores user facts, preferences, and learned patterns using ChromaDB.
Enables the AI to remember things across conversations.
"""
import logging
from typing import Optional, List

logger = logging.getLogger(__name__)

# ChromaDB instance (lazy-loaded)
_collection = None


def _get_collection():
    """Lazy-load ChromaDB collection."""
    global _collection
    if _collection is None:
        try:
            import chromadb
            client = chromadb.PersistentClient(path="./omnia_memory")
            _collection = client.get_or_create_collection(
                name="omnia_memory",
                metadata={"hnsw:space": "cosine"},
            )
            logger.info("ChromaDB memory initialized")
        except Exception as e:
            logger.warning(f"ChromaDB unavailable: {e}. Memory will not persist.")
            return None
    return _collection


async def store_memory(
    user_id: str,
    content: str,
    memory_type: str = "fact",
    metadata: Optional[dict] = None,
) -> dict:
    """
    Store a piece of information in long-term memory.

    Args:
        user_id: User this memory belongs to
        content: The information to remember
        memory_type: "fact", "preference", "pattern", "contact"
        metadata: Additional metadata

    Returns:
        dict with storage result
    """
    collection = _get_collection()
    if collection is None:
        return {"success": False, "error": "Memory system unavailable"}

    try:
        import uuid
        doc_id = str(uuid.uuid4())

        meta = {
            "user_id": user_id,
            "type": memory_type,
            **(metadata or {}),
        }

        collection.add(
            documents=[content],
            metadatas=[meta],
            ids=[doc_id],
        )

        logger.info(f"Memory stored: [{memory_type}] {content[:50]}...")
        return {"success": True, "id": doc_id}

    except Exception as e:
        logger.error(f"Memory store error: {e}")
        return {"success": False, "error": str(e)}


async def recall_memories(
    user_id: str,
    query: str,
    n_results: int = 5,
    memory_type: Optional[str] = None,
) -> dict:
    """
    Search for relevant memories using semantic similarity.

    Args:
        user_id: User whose memories to search
        query: What to search for
        n_results: Max results to return
        memory_type: Optional filter by type

    Returns:
        dict with matching memories
    """
    collection = _get_collection()
    if collection is None:
        return {"memories": [], "error": "Memory system unavailable"}

    try:
        where_filter = {"user_id": user_id}
        if memory_type:
            where_filter["type"] = memory_type

        results = collection.query(
            query_texts=[query],
            n_results=n_results,
            where=where_filter,
        )

        memories = []
        for i, doc in enumerate(results.get("documents", [[]])[0]):
            meta = results.get("metadatas", [[]])[0][i] if results.get("metadatas") else {}
            distance = results.get("distances", [[]])[0][i] if results.get("distances") else 0
            memories.append({
                "content": doc,
                "type": meta.get("type", "unknown"),
                "relevance": round(1 - distance, 3),  # Convert distance to similarity
            })

        return {"memories": memories}

    except Exception as e:
        logger.error(f"Memory recall error: {e}")
        return {"memories": [], "error": str(e)}


async def get_user_facts(user_id: str) -> List[str]:
    """Get all stored facts about a user (for system prompt enrichment)."""
    result = await recall_memories(user_id, "user preferences and facts", n_results=20)
    return [m["content"] for m in result.get("memories", [])]
