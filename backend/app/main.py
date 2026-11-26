
from fastapi import FastAPI, HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware

from backend.app.auth import (
    authenticate_user,
    create_access_token,
    verify_access_token,
    get_user_by_username
)

from backend.app.models import (
    LoginRequest,
    ChatRequest,
    ChatResponse,
    Citation
)

from backend.app.rag.answer_generation import document_rag_chain
from backend.app.rag.sql_rag import sql_rag_chain
from backend.app.rag.vector_store import COLLECTIONS, client
from backend.app.security.access_control import can_access_collection


app = FastAPI(
    title="CounselBot API",
    description="Secure Legal Document Assistant",
    version="1.0.0"
)

# Allow the Next.js frontend to communicate with FastAPI.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

security = HTTPBearer(auto_error=False)


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "message": "CounselBot API is running"
    }


@app.post("/login")
def login(request: LoginRequest):

    user = authenticate_user(
        request.username,
        request.password
    )

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password"
        )

    access_token = create_access_token(user["username"])

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": user
    }


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):

    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"}
        )

    try:
        payload = verify_access_token(credentials.credentials)

    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"}
        )

    username = payload.get("sub")

    if not username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload"
        )

    user = get_user_by_username(username)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )

    return user


@app.get("/me")
def get_me(user: dict = Depends(get_current_user)):
    return {"user": user}


@app.get("/collections/{role}")
def get_collections(role: str, user: dict = Depends(get_current_user)):

    if user["role"].strip().lower() != role.strip().lower():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You cannot view another user's collections"
        )

    accessible_collections = [
        collection
        for collection in COLLECTIONS
        if can_access_collection(user["role"], collection)
    ]

    return {
        "role": user["role"],
        "collections": accessible_collections
    }


@app.post("/chat", response_model=ChatResponse)
def chat(
    request: ChatRequest,
    user: dict = Depends(get_current_user)
):

    if not request.question.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Question cannot be empty"
        )

    try:

        if request.query_type == "sql":

            result = sql_rag_chain(
                question=request.question,
                allowed_matters=user["matters"],
                role=user["role"]
            )

            return ChatResponse(
                answer=result["answer"],
                status=result["status"],
                citations=[]
            )

        if request.collection_name not in COLLECTIONS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unknown collection"
            )

        if not can_access_collection(
            user["role"],
            request.collection_name
        ):
            return ChatResponse(
                answer="Your role is not permitted to access this collection.",
                status="role_restricted",
                citations=[]
            )

        result = document_rag_chain(
            question=request.question,
            user=user,
            collection_name=request.collection_name
        )

        citations = [
            Citation(
                source_document=citation["source_document"],
                doc_id=citation["doc_id"],
                chunk_id=citation["chunk_id"],
                page_numbers=citation["page_numbers"],
                section_heading=citation.get("section_heading"),
                heading_path=citation.get("heading_path", [])
            )
            for citation in result["citations"]
        ]

        return ChatResponse(
            answer=result["answer"],
            status=result["status"],
            citations=citations
        )

    except HTTPException:
        raise

    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while processing your question"
        )


@app.on_event("shutdown")
def shutdown_event():
    client.close()
