
from qdrant_client import models

from backend.app.rag.embeddings import generate_embedding
from backend.app.rag.vector_store import client
from backend.app.security.access_control import can_access_collection


def search_dense(
    question: str,
    user: dict,
    collection_name: str,
    limit: int = 5
) -> list:

    if not question or not question.strip():
        raise ValueError("Question cannot be empty")

    role = user.get("role", "")
    allowed_matters = user.get("matters", [])

    if not can_access_collection(role, collection_name):
        return []

    if limit < 1:
        raise ValueError("Limit must be at least 1")

    if not isinstance(allowed_matters, list):
        raise ValueError("User matters must be a list")

    if not all(isinstance(matter, str) for matter in allowed_matters):
        raise ValueError("Matter IDs must be strings")

    query_vector = generate_embedding(question)

    matter_conditions = [
        models.FieldCondition(
            key="matter_id",
            match=models.MatchValue(value="NONE")
        )
    ]

    if "*" not in allowed_matters:
        for matter_id in allowed_matters:
            matter_conditions.append(
                models.FieldCondition(
                    key="matter_id",
                    match=models.MatchValue(value=matter_id)
                )
            )

    normalised_role = (
        role.strip().lower().replace(" ", "_")
    )

    must_conditions = [
        models.FieldCondition(
            key="access_roles",
            match=models.MatchValue(value=normalised_role)
        )
    ]

    if "*" not in allowed_matters:
        must_conditions.append(
            models.Filter(should=matter_conditions)
        )

    access_filter = models.Filter(
        must=must_conditions
    )

    results = client.query_points(
        collection_name=collection_name,
        query=query_vector,
        query_filter=access_filter,
        limit=limit,
        with_payload=True
    ).points

    return [
        {
            "chunk_id": point.payload["chunk_id"],
            "text": point.payload["text"],
            "source_document": point.payload["source_document"],
            "doc_id": point.payload["doc_id"],
            "collection": point.payload["collection"],
            "matter_id": point.payload["matter_id"],
            "access_roles": point.payload["access_roles"],
            "section_heading": point.payload.get("section_heading"),
            "heading_path": point.payload.get("heading_path", []),
            "chunk_type": point.payload.get("chunk_type"),
            "page_numbers": point.payload["page_numbers"],
            "score": point.score
        }
        for point in results
    ]
