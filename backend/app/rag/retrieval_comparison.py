
from backend.app.auth import get_user_by_username
from backend.app.rag.dense_retrieval import search_dense
from backend.app.rag.hybrid_retrieval import hybrid_search
from backend.app.rag.reranking import rerank_results
from backend.app.rag.vector_store import client


USERNAME = "adv.rao"
COLLECTION = "contracts"

QUESTION = (
    "Which customer contracts have change-of-control "
    "termination rights, and what is the recommended action?"
)

TARGET_CHUNK = "VLH-MTR-017:table:2"

CANDIDATE_LIMIT = 20
FINAL_LIMIT = 5


def display_results(method: str, results: list):

    print("\n" + "=" * 70)
    print(method)
    print("=" * 70)

    if not results:
        print("No results found.")
        return

    for rank, result in enumerate(results, start=1):

        score = result.get(
            "rerank_score",
            result.get("rrf_score", result.get("score"))
        )

        print(f"\nRank: {rank}")
        print("Document:", result.get("source_document"))
        print("Document ID:", result.get("doc_id"))
        print("Chunk ID:", result.get("chunk_id"))
        print("Chunk type:", result.get("chunk_type"))
        print("Section:", result.get("section_heading"))
        print("Heading path:", result.get("heading_path"))
        print("Pages:", result.get("page_numbers"))
        print("Score:", score)
        print("Text:", result.get("text", "")[:350])


def show_target_rank(method: str, results: list):

    rank = next(
        (
            index
            for index, result in enumerate(results, start=1)
            if result.get("chunk_id") == TARGET_CHUNK
        ),
        None
    )

    if rank is None:
        print(f"{method}: Not in candidate results")
    else:
        print(f"{method}: Rank {rank}")


def main():

    user = get_user_by_username(USERNAME)

    if user is None:
        raise ValueError("Test user was not found.")

    print("COUNSELBOT RETRIEVAL COMPARISON")
    print("=" * 70)
    print("User:", user["username"])
    print("Role:", user["role"])
    print("Matters:", user["matters"])
    print("Collection:", COLLECTION)
    print("Question:", QUESTION)

    try:

        dense_candidates = search_dense(
            question=QUESTION,
            user=user,
            collection_name=COLLECTION,
            limit=CANDIDATE_LIMIT
        )

        show_target_rank(
            "Dense-only findings-table rank",
            dense_candidates
        )

        display_results(
            "1. DENSE-ONLY SEARCH - TOP 5",
            dense_candidates[:FINAL_LIMIT]
        )

        hybrid_candidates = hybrid_search(
            question=QUESTION,
            user=user,
            collection_name=COLLECTION,
            dense_limit=CANDIDATE_LIMIT,
            bm25_limit=CANDIDATE_LIMIT,
            final_limit=CANDIDATE_LIMIT
        )

        show_target_rank(
            "Hybrid findings-table rank",
            hybrid_candidates
        )

        display_results(
            "2. HYBRID SEARCH - TOP 5",
            hybrid_candidates[:FINAL_LIMIT]
        )

        reranked_results = rerank_results(
            question=QUESTION,
            results=hybrid_candidates,
            top_k=FINAL_LIMIT
        )

        show_target_rank(
            "Reranked findings-table rank",
            reranked_results
        )

        display_results(
            "3. HYBRID + CROSS-ENCODER RERANKING - TOP 5",
            reranked_results
        )

        print("\n" + "=" * 70)
        print("COMPARISON COMPLETE")
        print("=" * 70)

    finally:
        client.close()


if __name__ == "__main__":
    main()
