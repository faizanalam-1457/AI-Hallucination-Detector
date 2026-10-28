"""Document ingestion, validation, and PyMuPDF text extraction for VeriAI.

Extracts text from PDF and TXT documents, preserving page-level attribution
for auditability in hallucination verification. Validates file integrity,
sanitizes filenames, and detects scanned/empty documents requiring OCR.
"""

import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Tuple

import fitz  # PyMuPDF

from src.config import get_config, PROJECT_ROOT


@dataclass
class DocumentPage:
    page_number: int  # 1-indexed
    text: str
    char_count: int


@dataclass
class ProcessedDocument:
    doc_id: str
    filename: str
    file_type: str
    file_size_bytes: int
    page_count: int
    total_characters: int
    is_scanned_warning: bool
    warning_message: Optional[str]
    pages: List[DocumentPage] = field(default_factory=list)


@dataclass
class DocumentChunk:
    chunk_id: str
    doc_id: str
    doc_title: str
    page_number: Optional[int]
    text: str
    chunk_index: int


def sanitize_filename(filename: str) -> str:
    """Sanitizes filename to prevent directory traversal or script injection."""
    clean = os.path.basename(filename)
    # Remove null bytes and non-alphanumeric/period/dash/underscore characters
    clean = re.sub(r"[^\w\.\-\_ ]", "_", clean)
    return clean.strip(" .") or "document"


def validate_file_safety(file_path: Path, max_size_mb: int = 25) -> Tuple[bool, Optional[str]]:
    """Checks that a file exists, is within size limits, and is not a dangerous type."""
    if not file_path.exists():
        return False, "File does not exist."

    size_mb = file_path.stat().st_size / (1024 * 1024)
    if size_mb > max_size_mb:
        return False, f"File exceeds maximum allowed size of {max_size_mb} MB (actual: {size_mb:.1f} MB)."

    ext = file_path.suffix.lower()
    allowed_exts = get_config().get("documents", {}).get("supported_extensions", [".pdf", ".txt"])
    if ext not in allowed_exts:
        return False, f"Unsupported file type '{ext}'. Supported extensions: {', '.join(allowed_exts)}."

    return True, None


def extract_text_from_pdf(file_path: Path) -> Tuple[List[DocumentPage], bool, Optional[str]]:
    """Extracts text per page from a PDF using PyMuPDF.

    Returns:
        (pages, is_scanned_warning, warning_message)
    """
    pages: List[DocumentPage] = []
    total_chars = 0

    try:
        doc = fitz.open(file_path)
    except Exception as e:
        return [], True, f"Failed to parse PDF document: {str(e)}"

    with doc:
        for page_idx in range(len(doc)):
            page = doc[page_idx]
            text = page.get_text("text").strip()
            total_chars += len(text)
            pages.append(
                DocumentPage(
                    page_number=page_idx + 1,
                    text=text,
                    char_count=len(text),
                )
            )

    is_scanned = len(pages) > 0 and total_chars < 50
    warning = (
        "Document contains minimal or zero extractable text. This PDF appears to be a scanned image. "
        "Optical Character Recognition (OCR) is required to extract and index image-only PDFs."
        if is_scanned
        else None
    )

    return pages, is_scanned, warning


def extract_text_from_txt(file_path: Path) -> Tuple[List[DocumentPage], bool, Optional[str]]:
    """Reads a plain text file, treating it as a single page."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read().strip()
    except UnicodeDecodeError:
        try:
            with open(file_path, "r", encoding="latin-1") as f:
                content = f.read().strip()
        except Exception as e:
            return [], True, f"Failed to decode text file: {str(e)}"

    pages = [DocumentPage(page_number=1, text=content, char_count=len(content))]
    return pages, False, None


def process_document(doc_id: str, file_path: Path, original_filename: str) -> ProcessedDocument:
    """Processes an uploaded file into a ProcessedDocument representation."""
    ext = file_path.suffix.lower()
    clean_name = sanitize_filename(original_filename)

    if ext == ".pdf":
        pages, is_scanned, warning = extract_text_from_pdf(file_path)
    elif ext == ".txt":
        pages, is_scanned, warning = extract_text_from_txt(file_path)
    else:
        pages, is_scanned, warning = [], True, f"Unsupported format: {ext}"

    total_chars = sum(p.char_count for p in pages)
    return ProcessedDocument(
        doc_id=doc_id,
        filename=clean_name,
        file_type=ext.lstrip("."),
        file_size_bytes=file_path.stat().st_size if file_path.exists() else 0,
        page_count=len(pages),
        total_characters=total_chars,
        is_scanned_warning=is_scanned,
        warning_message=warning,
        pages=pages,
    )


def chunk_processed_document(
    doc: ProcessedDocument,
    chunk_size_words: Optional[int] = None,
    chunk_overlap_words: Optional[int] = None,
) -> List[DocumentChunk]:
    """Generates overlapping word-window chunks while preserving page numbers.

    For PDFs, chunks are created on a per-page basis to ensure page citations
    remain strictly accurate.
    """
    cfg = get_config().get("documents", {})
    size = chunk_size_words or cfg.get("chunk_size_words", 150)
    overlap = chunk_overlap_words or cfg.get("chunk_overlap_words", 30)
    step = max(size - overlap, 1)

    all_chunks: List[DocumentChunk] = []
    chunk_counter = 0

    for page in doc.pages:
        words = page.text.split()
        if not words:
            continue

        start = 0
        while start < len(words):
            window = words[start : start + size]
            all_chunks.append(
                DocumentChunk(
                    chunk_id=f"{doc.doc_id}-p{page.page_number}-{chunk_counter}",
                    doc_id=doc.doc_id,
                    doc_title=doc.filename,
                    page_number=page.page_number,
                    text=" ".join(window),
                    chunk_index=chunk_counter,
                )
            )
            chunk_counter += 1
            start += step

    return all_chunks
