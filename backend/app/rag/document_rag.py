from backend.app.rag.hybrid_retrieval import hybrid_search
from backend.app.rag.reranking import rerank_results


def document_rag_search(
    question: str,
    user: dict,
    collection_name: str,
    candidate_limit: int = 10,
    final_limit: int = 5
) -> list:
    """
    Complete document retrieval pipeline:
    Dense + BM25 -> RRF -> Cross-encoder reranking.
    """

    if not question or not question.strip():
        raise ValueError("Question cannot be empty")

    if final_limit < 1:
        raise ValueError("Final limit must be at least 1")

    if candidate_limit < final_limit:
        raise ValueError(
            "Candidate limit must be greater than or equal to final limit"
        )

    # Stage 1 and 2: Hybrid retrieval
    candidates = hybrid_search(
        question=question,
        user=user,
        collection_name=collection_name,
        dense_limit=candidate_limit,
        bm25_limit=candidate_limit,
        final_limit=candidate_limit
    )

    if not candidates:
        return []

    # Stage 3: Cross-encoder reranking
    final_results = rerank_results(
        question=question,
        results=candidates,
        top_k=final_limit
    )

    return final_results