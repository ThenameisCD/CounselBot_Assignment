
from backend.app.security.access_control import can_access_document
from backend.app.security.manifest_loader import get_document_by_id


# Check whether a user can access a document
def check_document_access(user: dict, doc_id: str) -> bool:

    # Find document metadata in the manifest
    document = get_document_by_id(doc_id)

    # Deny access if the document does not exist
    if document is None:
        return False

    # Apply all access-control rules
    return can_access_document(user, document)
