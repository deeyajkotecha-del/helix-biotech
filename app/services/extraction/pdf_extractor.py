"""
PDF Text Extractor using PyMuPDF (fitz).

Extracts text from PDFs with page number markers for citation tracking.
"""

import logging
from pathlib import Path
from typing import Union

import fitz  # PyMuPDF

logger = logging.getLogger(__name__)


def extract_text_from_pdf(pdf_path: Union[str, Path]) -> str:
    """
    Extract all text from a PDF file.

    Args:
        pdf_path: Path to the PDF file

    Returns:
        Full text content of the PDF
    """
    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    logger.info(f"Extracting text from {pdf_path.name}")

    doc = fitz.open(str(pdf_path))
    text_parts = []

    for page_num in range(len(doc)):
        page = doc[page_num]
        text = page.get_text()
        text_parts.append(text)

    doc.close()

    return "\n".join(text_parts)


def extract_text_by_page(pdf_path: Union[str, Path]) -> list[dict]:
    """
    Extract text from PDF with page numbers for citations.

    Args:
        pdf_path: Path to the PDF file

    Returns:
        List of dicts with keys: page_number, text
    """
    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    logger.info(f"Extracting text by page from {pdf_path.name}")

    doc = fitz.open(str(pdf_path))
    pages = []

    for page_num in range(len(doc)):
        page = doc[page_num]
        text = page.get_text()
        pages.append({
            "page_number": page_num + 1,  # 1-indexed
            "text": text
        })

    doc.close()

    return pages


def extract_text_with_markers(pdf_path: Union[str, Path]) -> str:
    """
    Extract text from PDF with [PAGE X] markers for AI extraction.

    This format allows the AI to cite specific pages when extracting data.

    Args:
        pdf_path: Path to the PDF file

    Returns:
        Text with [PAGE X] markers before each page's content
    """
    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    logger.info(f"Extracting text with markers from {pdf_path.name}")

    doc = fitz.open(str(pdf_path))
    text_parts = []

    for page_num in range(len(doc)):
        page = doc[page_num]
        text = page.get_text().strip()

        if text:  # Only include non-empty pages
            text_parts.append(f"\n[PAGE {page_num + 1}]\n{text}")

    doc.close()

    return "\n".join(text_parts)


def get_pdf_metadata(pdf_path: Union[str, Path]) -> dict:
    """
    Get metadata from a PDF file.

    Args:
        pdf_path: Path to the PDF file

    Returns:
        Dict with metadata: page_count, title, author, creation_date, etc.
    """
    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    doc = fitz.open(str(pdf_path))

    metadata = {
        "page_count": len(doc),
        "title": doc.metadata.get("title", ""),
        "author": doc.metadata.get("author", ""),
        "subject": doc.metadata.get("subject", ""),
        "creator": doc.metadata.get("creator", ""),
        "creation_date": doc.metadata.get("creationDate", ""),
        "modification_date": doc.metadata.get("modDate", ""),
        "file_size_kb": pdf_path.stat().st_size // 1024
    }

    doc.close()

    return metadata


def extract_images_info(pdf_path: Union[str, Path]) -> list[dict]:
    """
    Get information about images in the PDF (for identifying charts/graphs).

    Args:
        pdf_path: Path to the PDF file

    Returns:
        List of dicts with image info: page, bbox, size
    """
    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    doc = fitz.open(str(pdf_path))
    images = []

    for page_num in range(len(doc)):
        page = doc[page_num]
        image_list = page.get_images()

        for img_index, img in enumerate(image_list):
            xref = img[0]
            images.append({
                "page": page_num + 1,
                "image_index": img_index,
                "xref": xref,
                "width": img[2],
                "height": img[3]
            })

    doc.close()

    return images


def extract_text_chunks(
    pdf_path: Union[str, Path],
    chunk_size: int = 10000,
    overlap: int = 500
) -> list[dict]:
    """
    Extract text in chunks suitable for LLM processing.

    Useful for very large PDFs that exceed context limits.

    Args:
        pdf_path: Path to the PDF file
        chunk_size: Target size of each chunk in characters
        overlap: Character overlap between chunks

    Returns:
        List of dicts with keys: chunk_index, start_page, end_page, text
    """
    pages = extract_text_by_page(pdf_path)

    chunks = []
    current_chunk = ""
    current_pages = []

    for page_data in pages:
        page_text = f"\n[PAGE {page_data['page_number']}]\n{page_data['text']}"

        if len(current_chunk) + len(page_text) > chunk_size and current_chunk:
            # Save current chunk
            chunks.append({
                "chunk_index": len(chunks),
                "start_page": current_pages[0] if current_pages else 1,
                "end_page": current_pages[-1] if current_pages else 1,
                "text": current_chunk,
                "char_count": len(current_chunk)
            })

            # Start new chunk with overlap
            overlap_text = current_chunk[-overlap:] if len(current_chunk) > overlap else current_chunk
            current_chunk = overlap_text + page_text
            current_pages = [page_data['page_number']]
        else:
            current_chunk += page_text
            current_pages.append(page_data['page_number'])

    # Don't forget the last chunk
    if current_chunk:
        chunks.append({
            "chunk_index": len(chunks),
            "start_page": current_pages[0] if current_pages else 1,
            "end_page": current_pages[-1] if current_pages else 1,
            "text": current_chunk,
            "char_count": len(current_chunk)
        })

    return chunks


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def quick_extract(pdf_path: Union[str, Path]) -> tuple[str, dict]:
    """
    Quick extraction returning text with markers and metadata.

    Args:
        pdf_path: Path to the PDF file

    Returns:
        Tuple of (text_with_markers, metadata_dict)
    """
    text = extract_text_with_markers(pdf_path)
    metadata = get_pdf_metadata(pdf_path)
    return text, metadata
