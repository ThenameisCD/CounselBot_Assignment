
from pydantic import BaseModel, Field
from typing import Literal


class LoginRequest(BaseModel):
    username: str
    password: str


class ChatRequest(BaseModel):
    question: str
    collection_name: str = "general"
    query_type: Literal["document", "sql"] = "document"


class Citation(BaseModel):
    source_document: str
    doc_id: str
    chunk_id: str
    page_numbers: list[int] = Field(default_factory=list)
    section_heading: str | None = None
    heading_path: list[str] = Field(default_factory=list)


class ChatResponse(BaseModel):
    answer: str
    status: str
    citations: list[Citation] = Field(default_factory=list)
