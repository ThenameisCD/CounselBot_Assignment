
import re

from rank_bm25 import BM25Okapi
from qdrant_client import models

from backend.app.rag.vector_store import client
from backend.app.security.access_control import can_access_collection


def tokenize(text: str) -> list:
    return re.findall(r"\b[a-z0-9]+\b", text.lower())


def search_bm25(
    question: str,
    user: dict,
    collection_name: str,
    limit: int = 5
) -> list:

    if not question or not question.strip():
        raise ValueError("Question cannot be empty")

    if limit < 1:
        raise ValueError("Limit must be at least 1")

    if not can_access_collection(
        user.get("role", ""),
        collection_name
    ):
        return []

    allowed_matters = user.get("matters", [])

    if not isinstance(allowed_matters, list):
        raise ValueError("User matters must be a list")

    if not all(isinstance(matter, str) for matter in allowed_matters):
        raise ValueError("Matter IDs must be strings")

    normalised_role = (
        user["role"].strip().lower().replace(" ", "_")
    )

    must_conditions = [
        models.FieldCondition(
            key="access_roles",
            match=models.MatchValue(value=normalised_role)
        )
    ]

    if "*" not in allowed_matters:

        matter_conditions = [
            models.FieldCondition(
                key="matter_id",
                match=models.MatchValue(value="NONE")
            )
        ]

        for matter_id in allowed_matters:
            matter_conditions.append(
                models.FieldCondition(
                    key="matter_id",
                    match=models.MatchValue(value=matter_id)
                )
            )

        must_conditions.append(
            models.Filter(should=matter_conditions)
        )

    access_filter = models.Filter(
        must=must_conditions
    )

    accessible_points = []
    offset = None

    while True:

        points, next_offset = client.scroll(
            collection_name=collection_name,
            scroll_filter=access_filter,
            limit=256,
            offset=offset,
            with_payload=True,
            with_vectors=False
        )

        accessible_points.extend(points)

        if next_offset is None:
            break

        offset = next_offset

    if not accessible_points:
        return []

    tokenized_corpus = [
        tokenize(point.payload["text"])
        for point in accessible_points
    ]

    query_tokens = tokenize(question)

    if not query_tokens:
        raise ValueError("Question contains no searchable words")

    bm25 = BM25Okapi(tokenized_corpus)
    scores = bm25.get_scores(query_tokens)

    ranked_results = []

    for point, score in zip(accessible_points, scores):

        if score <= 0:
            continue

        payload = point.payload

        ranked_results.append({
            "chunk_id": payload["chunk_id"],
            "text": payload["text"],
            "source_document": payload["source_document"],
            "doc_id": payload["doc_id"],
            "collection": payload["collection"],
            "matter_id": payload["matter_id"],
            "access_roles": payload["access_roles"],
            "section_heading": payload.get("section_heading"),
            "heading_path": payload.get("heading_path", []),
            "chunk_type": payload.get("chunk_type"),
            "page_numbers": payload["page_numbers"],
            "score": float(score)
        })

    ranked_results.sort(
        key=lambda result: result["score"],
        reverse=True
    )

    return ranked_results[:limit]
