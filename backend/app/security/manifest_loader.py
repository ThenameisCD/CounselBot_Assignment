
import json

from backend.app.config import DATASET_DIR


# Load all document records from the manifest
def load_manifest() -> list:

    manifest_file = DATASET_DIR / "manifest.json"

    with open(manifest_file, "r", encoding="utf-8") as file:
        manifest = json.load(file)

    return manifest


# Find one document using its document ID
def get_document_by_id(doc_id: str):

    documents = load_manifest()

    for document in documents:
        if document["doc_id"] == doc_id:
            return document

    return None
