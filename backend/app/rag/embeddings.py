from sentence_transformers import SentenceTransformer

from backend.app.config import EMBEDDING_MODEL


# Load the embedding model once and reuse it
embedding_model = SentenceTransformer(EMBEDDING_MODEL)


def generate_embedding(text: str) -> list:
    """
    Convert text into a numerical vector.
    """

    if not text or not text.strip():
        raise ValueError("Text cannot be empty")

    vector = embedding_model.encode(
        text,
        normalize_embeddings=True
    )

    return vector.tolist()


def generate_embeddings(texts: list) -> list:
    """
    Convert multiple text chunks into numerical vectors.
    """

    if not texts:
        return []

    if any(not text or not text.strip() for text in texts):
        raise ValueError("Text list contains empty content")

    vectors = embedding_model.encode(
        texts,
        normalize_embeddings=True,
        show_progress_bar=True
    )

    return vectors.tolist()