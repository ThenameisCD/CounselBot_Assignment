
# Convert role names into a consistent format
def normalise_role(role: str) -> str:
    return role.strip().lower().replace(" ", "_")


# Role-based collection permissions
ROLE_COLLECTION_ACCESS = {
    "general_counsel": [
        "general",
        "contracts",
        "litigation",
        "compliance",
        "ip"
    ],
    "corporate_counsel": [
        "general",
        "contracts",
        "ip"
    ],
    "litigation_counsel": [
        "general",
        "litigation",
        "ip"
    ],
    "compliance_officer": [
        "general",
        "compliance"
    ],
    "paralegal": [
        "general",
        "contracts"
    ]
}


# Check whether a role can access a collection
def can_access_collection(role: str, collection: str) -> bool:

    normalised_role = normalise_role(role)

    allowed_collections = ROLE_COLLECTION_ACCESS.get(
        normalised_role, []
    )

    return collection in allowed_collections


# Check whether a role can access a particular document
def can_access_document_role(
    role: str,
    access_roles: list
) -> bool:

    normalised_role = normalise_role(role)

    normalised_access_roles = [
        normalise_role(allowed_role)
        for allowed_role in access_roles
    ]

    return normalised_role in normalised_access_roles


# Check whether a user is assigned to a matter
def can_access_matter(
    user_matters: list,
    matter_id: str
) -> bool:

    # General Counsel has access to all matters
    if "*" in user_matters:
        return True

    # Documents without a matter restriction are accessible
    if matter_id is None or matter_id == "NONE":
        return True

    return matter_id in user_matters


# Combined access-control decision
def can_access_document(
    user: dict,
    document: dict
) -> bool:

    role = user.get("role")
    user_matters = user.get("matters", [])

    collection = document.get("collection")
    access_roles = document.get("access_roles", [])
    matter_id = document.get("matter_id")

    # Check 1: Collection permission
    if not can_access_collection(role, collection):
        return False

    # Check 2: Document-level role permission
    if not can_access_document_role(role, access_roles):
        return False

    # Check 3: Matter assignment
    if not can_access_matter(user_matters, matter_id):
        return False

    return True
