from collections import defaultdict

from backend.app.security.manifest_loader import load_manifest
from backend.app.rag.ingestion import ingest_document
from backend.app.rag.embeddings import generate_embeddings
from backend.app.rag.vector_store import (
    store_chunks,
    create_all_collections,
    client
)


def index_all_documents():

    grouped_chunks = defaultdict(list)

    try:
        # Ensure all five collections exist
        create_all_collections()

        documents = load_manifest()

        print("Documents to process:", len(documents))

        # Step 1: Read and chunk every document
        for number, entry in enumerate(documents, start=1):

            doc_id = entry["doc_id"]

            print(
                f"\n[{number}/{len(documents)}] "
                f"Processing: {entry['source_document']}"
            )

            chunks = ingest_document(doc_id)

            grouped_chunks[entry["collection"]].extend(chunks)

            print("Chunks created:", len(chunks))

        total_indexed = 0

        # Step 2: Generate embeddings and store by collection
        for collection_name, chunks in grouped_chunks.items():

            print(
                f"\nIndexing collection: {collection_name}"
            )

            texts = [
                chunk["text"]
                for chunk in chunks
            ]

            vectors = generate_embeddings(texts)

            stored = store_chunks(
                collection_name=collection_name,
                chunks=chunks,
                vectors=vectors
            )

            total_indexed += stored

            print("Chunks stored:", stored)

        print("\n" + "=" * 50)
        print("INDEXING COMPLETE")
        print("=" * 50)
        print("Total chunks indexed:", total_indexed)

        for collection_name in sorted(grouped_chunks):
            print(
                collection_name,
                ":",
                len(grouped_chunks[collection_name])
            )

        return total_indexed

    finally:
        client.close()


if __name__ == "__main__":
    index_all_documents()