from backend.app.rag.dense_retrieval import search_dense
from backend.app.rag.bm25_retrieval import search_bm25


def reciprocal_rank_fusion(
    result_lists: list,
    k: int = 60
) -> list:
    """
    Combine ranked result lists using Reciprocal Rank Fusion.
    """

    if k < 1:
        raise ValueError("RRF k must be at least 1")

    combined = {}

    for results in result_lists:

        for rank, result in enumerate(results, start=1):

            chunk_id = result["chunk_id"]

            if chunk_id not in combined:
                combined[chunk_id] = {
                    **result,
                    "rrf_score": 0.0
                }

            combined[chunk_id]["rrf_score"] += (
                1.0 / (k + rank)
            )

    ranked_results = sorted(
        combined.values(),
        key=lambda item: item["rrf_score"],
        reverse=True
    )

    return ranked_results


def hybrid_search(
    question: str,
    user: dict,
    collection_name: str,
    dense_limit: int = 10,
    bm25_limit: int = 10,
    final_limit: int = 5
) -> list:
    """
    Combine dense and BM25 retrieval using RRF.
    """

    if final_limit < 1:
        raise ValueError("Final limit must be at least 1")

    dense_results = search_dense(
        question=question,
        user=user,
        collection_name=collection_name,
        limit=dense_limit
    )

    bm25_results = search_bm25(
        question=question,
        user=user,
        collection_name=collection_name,
        limit=bm25_limit
    )

    fused_results = reciprocal_rank_fusion([
        dense_results,
        bm25_results
    ])

    return fused_results[:final_limit]