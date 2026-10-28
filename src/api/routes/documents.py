"""Document Library endpoints for VeriAI."""

import shutil
import uuid
from pathlib import Path
from typing import Any, Dict, List
from fastapi import APIRouter, File, HTTPException, UploadFile

from src.api.database import (
    delete_document_record,
    get_all_documents,
    get_document_by_id,
    save_document_record,
)
from src.api.schemas import DocumentResponse
from src.config import get_config, PROJECT_ROOT
from src.rag.document_loader import (
    chunk_processed_document,
    process_document,
    sanitize_filename,
    validate_file_safety,
)
from src.rag.vectorstore import delete_document_chunks, index_document_chunks

router = APIRouter(prefix="/documents", tags=["Document Library"])


def get_uploads_dir() -> Path:
    cfg = get_config()
    rel = cfg.get("paths", {}).get("uploads_dir", "data/uploads")
    dir_path = PROJECT_ROOT / rel
    dir_path.mkdir(parents=True, exist_ok=True)
    return dir_path


@router.post("/upload", response_model=DocumentResponse)
async def upload_document(file: UploadFile = File(...)):
    """Uploads, validates, parses, chunks, and indexes a PDF or TXT document."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="Uploaded file missing filename.")

    sanitized_name = sanitize_filename(file.filename)
    ext = Path(sanitized_name).suffix.lower()
    allowed_exts = get_config().get("documents", {}).get("supported_extensions", [".pdf", ".txt"])
    if ext not in allowed_exts:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported format '{ext}'. Allowed extensions: {', '.join(allowed_exts)}.",
        )

    doc_id = f"doc-{uuid.uuid4().hex[:10]}"
    target_path = get_uploads_dir() / f"{doc_id}_{sanitized_name}"

    # Write file safely
    try:
        with open(target_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")

    # Validate size & security
    max_mb = get_config().get("documents", {}).get("max_upload_size_mb", 25)
    is_safe, safety_err = validate_file_safety(target_path, max_size_mb=max_mb)
    if not is_safe:
        target_path.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail=safety_err)

    # Process and extract text (via PyMuPDF for PDF, plain for TXT)
    processed = process_document(doc_id, target_path, sanitized_name)

    # Chunk with page attribution
    chunks = chunk_processed_document(processed)

    # Index in vector store
    indexed_count = index_document_chunks(chunks)

    # Persist in SQLite
    save_document_record(
        doc_id=doc_id,
        filename=sanitized_name,
        file_type=processed.file_type,
        file_size_bytes=processed.file_size_bytes,
        page_count=processed.page_count,
        chunk_count=indexed_count,
        is_scanned_warning=processed.is_scanned_warning,
        warning_message=processed.warning_message,
        storage_path=str(target_path.relative_to(PROJECT_ROOT)),
    )

    doc = get_document_by_id(doc_id)
    if not doc:
        raise HTTPException(status_code=500, detail="Failed to retrieve saved document.")
    return doc


@router.get("", response_model=List[DocumentResponse])
def list_documents():
    """Lists all uploaded documents with indexing status and metadata."""
    return get_all_documents()


@router.get("/{doc_id}/preview")
def get_document_preview(doc_id: str):
    """Retrieves document pages preview safely without exposing system paths."""
    doc = get_document_by_id(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail=f"Document '{doc_id}' not found.")

    storage_rel = doc.get("storage_path")
    if not storage_rel:
        raise HTTPException(status_code=404, detail="Document file path missing.")

    file_path = PROJECT_ROOT / storage_rel
    # Verify path is within uploads dir to prevent path traversal
    if not file_path.resolve().is_relative_to(get_uploads_dir().resolve()):
        raise HTTPException(status_code=403, detail="Access denied: invalid file path.")

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Underlying file not found on disk.")

    processed = process_document(doc_id, file_path, doc["filename"])
    pages_data = [
        {"page_number": p.page_number, "text": p.text[:1500], "char_count": p.char_count}
        for p in processed.pages[:10]  # First 10 pages for preview
    ]

    return {
        "id": doc_id,
        "filename": doc["filename"],
        "file_type": doc["file_type"],
        "page_count": doc["page_count"],
        "chunk_count": doc["chunk_count"],
        "is_scanned_warning": doc["is_scanned_warning"],
        "warning_message": doc["warning_message"],
        "pages_preview": pages_data,
    }


@router.delete("/{doc_id}")
def delete_document(doc_id: str):
    """Deletes document record, removes its chunks from vectorstore, and deletes local file."""
    doc = get_document_by_id(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail=f"Document '{doc_id}' not found.")

    # 1. Remove vector chunks
    delete_document_chunks(doc_id)

    # 2. Remove file on disk safely
    storage_rel = doc.get("storage_path")
    if storage_rel:
        p = PROJECT_ROOT / storage_rel
        if p.exists() and p.resolve().is_relative_to(get_uploads_dir().resolve()):
            p.unlink(missing_ok=True)

    # 3. Remove DB record
    delete_document_record(doc_id)
    return {"status": "deleted", "id": doc_id}


@router.post("/{doc_id}/reindex")
def reindex_document(doc_id: str):
    """Re-chunks and re-indexes an existing document."""
    doc = get_document_by_id(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail=f"Document '{doc_id}' not found.")

    storage_rel = doc.get("storage_path")
    if not storage_rel:
        raise HTTPException(status_code=404, detail="Document file path missing.")

    file_path = PROJECT_ROOT / storage_rel
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Document file not found on disk.")

    # Remove old vector chunks
    delete_document_chunks(doc_id)

    # Re-process and re-index
    processed = process_document(doc_id, file_path, doc["filename"])
    chunks = chunk_processed_document(processed)
    count = index_document_chunks(chunks)

    # Update DB chunk count
    save_document_record(
        doc_id=doc_id,
        filename=doc["filename"],
        file_type=doc["file_type"],
        file_size_bytes=doc["file_size_bytes"],
        page_count=processed.page_count,
        chunk_count=count,
        is_scanned_warning=processed.is_scanned_warning,
        warning_message=processed.warning_message,
        storage_path=storage_rel,
    )

    return {"status": "reindexed", "id": doc_id, "chunk_count": count}
