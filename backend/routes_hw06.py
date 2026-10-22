"""HW6 document and memory API routes."""
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from .hw06_memory import (
    aggregate_view,
    chat,
    document_create,
    document_delete,
    document_get,
    document_list,
    document_update,
    memory_view,
)
from .hw06_file_memory import handle_command
from .hw06_models import ChatRequest, DocumentCreate, DocumentResponse, DocumentUpdate

router = APIRouter(prefix="/api", tags=["HW6 MongoDB and memory"])


class MemoryCommandRequest(BaseModel):
    command: str = Field(pattern=r"^/(memory|compact|dream|help)$")
    facts: list[str] = Field(default_factory=list, max_length=3)


@router.post("/documents", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
def create_document(payload: DocumentCreate):
    return document_create(payload)


@router.get("/documents", response_model=list[DocumentResponse])
def list_documents():
    return document_list()


@router.get("/documents/{identifier}", response_model=DocumentResponse)
def get_document(identifier: str):
    result = document_get(identifier)
    if result is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return result


@router.put("/documents/{identifier}", response_model=DocumentResponse)
def update_document(identifier: str, payload: DocumentUpdate):
    result = document_update(identifier, payload)
    if result is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return result


@router.delete("/documents/{identifier}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(identifier: str):
    if not document_delete(identifier):
        raise HTTPException(status_code=404, detail="Document not found")
    return None


@router.post("/chat")
def post_chat(payload: ChatRequest):
    return chat(payload)


@router.get("/memory/{user_id}")
def get_memory(user_id: str):
    return memory_view(user_id)


@router.post("/memory/command")
def memory_command(payload: MemoryCommandRequest):
    return handle_command(payload.command, payload.facts)


@router.get("/aggregate/{user_id}")
def get_aggregate(user_id: str):
    return aggregate_view(user_id)
