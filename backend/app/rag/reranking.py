from sentence_transformers import CrossEncoder


# Load the cross-encoder model once
reranker = CrossEncoder(
    "cross-encoder/ms-marco-MiniLM-L-6-v2"
)


def rerank_results(
    question: str,
    results: list,
    top_k: int = 5
) -> list:
    """
    Rerank retrieved passages based on relevance to the question.
    """

    if not question or not question.strip():
        raise ValueError("Question cannot be empty")

    if top_k < 1:
        raise ValueError("top_k must be at least 1")

    if not results:
        return []

    pairs = [
        (question, result["text"])
        for result in results
    ]

    scores = reranker.predict(pairs)

    reranked_results = []

    for result, score in zip(results, scores):
        reranked_result = result.copy()
        reranked_result["rerank_score"] = float(score)
        reranked_results.append(reranked_result)

    reranked_results.sort(
        key=lambda item: item["rerank_score"],
        reverse=True
    )

    return reranked_results[:top_k]