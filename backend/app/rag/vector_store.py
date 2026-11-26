import uuid

from qdrant_client import QdrantClient, models
from qdrant_client.models import Distance, VectorParams

from backend.app.config import QDRANT_PATH


# Connect to local Qdrant storage
client = QdrantClient(path=str(QDRANT_PATH))

VECTOR_SIZE = 384

COLLECTIONS = [
    "general",
    "contracts",
    "litigation",
    "compliance",
    "ip"
]


def create_collection(collection_name: str):
    existing = list_collections()

    if collection_name not in existing:
        client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(
                size=VECTOR_SIZE,
                distance=Distance.COSINE
            )
        )

    return collection_name


def create_all_collections():
    for collection_name in COLLECTIONS:
        create_collection(collection_name)

    return list_collections()


def list_collections():
    return [
        collection.name
        for collection in client.get_collections().collections
    ]


def prepare_payload(chunk: dict) -> dict:
    return {
        "chunk_id": chunk["chunk_id"],
        "text": chunk["text"],
        "doc_id": chunk["doc_id"],
        "source_document": chunk["source_document"],
        "source_path": chunk["source_path"],
        "collection": chunk["collection"],
        "access_roles": chunk["access_roles"],
        "matter_id": chunk["matter_id"],
        "format": chunk["format"],
        "chunk_type": chunk["chunk_type"],
        "section_heading": chunk["section_heading"],
        "heading_path": chunk["heading_path"],
        "page_numbers": chunk["page_numbers"],
        "page_number": chunk["page_number"],
        "document_notices": chunk["document_notices"]
    }


def store_chunks(collection_name: str, chunks: list, vectors: list):
    if collection_name not in COLLECTIONS:
        raise ValueError("Unknown collection")

    if len(chunks) != len(vectors):
        raise ValueError("Each chunk must have one embedding")

    if not chunks:
        return 0

    create_collection(collection_name)

    points = []

    for chunk, vector in zip(chunks, vectors):

        if chunk["collection"] != collection_name:
            raise ValueError("Chunk collection does not match target")

        if len(vector) != VECTOR_SIZE:
            raise ValueError("Embedding has an incorrect dimension")

        # Convert readable chunk ID into a deterministic UUID
        point_id = str(
            uuid.uuid5(
                uuid.NAMESPACE_URL,
                chunk["chunk_id"]
            )
        )

        points.append(
            models.PointStruct(
                id=point_id,
                vector=vector,
                payload=prepare_payload(chunk)
            )
        )

    client.upsert(
        collection_name=collection_name,
        points=points,
        wait=True
    )

    return len(points)