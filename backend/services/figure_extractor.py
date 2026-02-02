"""
PDF Figure Extraction Service

Extracts images and figures from investor presentation PDFs.
Uses pdf2image (poppler) for high-quality image extraction.
"""

import os
import re
import json
import hashlib
import tempfile
import requests
from pathlib import Path
from typing import Optional
from datetime import datetime

# Try to import pdf2image (requires poppler)
try:
    from pdf2image import convert_from_path, convert_from_bytes
    PDF2IMAGE_AVAILABLE = True
except ImportError:
    PDF2IMAGE_AVAILABLE = False
    print("Warning: pdf2image not available. Install with: pip install pdf2image")

# Try to import PyMuPDF as fallback
try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False


# Directories
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data" / "figures"
PUBLIC_DIR = BASE_DIR.parent / "app" / "public" / "figures"

DATA_DIR.mkdir(parents=True, exist_ok=True)
PUBLIC_DIR.mkdir(parents=True, exist_ok=True)


def sanitize_filename(name: str) -> str:
    """Convert string to safe filename."""
    name = name.lower()
    name = re.sub(r'[^\w\s-]', '', name)
    name = re.sub(r'[\s_]+', '-', name)
    return name[:50]


def download_pdf(url: str, dest_path: Path) -> bool:
    """Download PDF from URL."""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers, timeout=60)
        response.raise_for_status()

        with open(dest_path, 'wb') as f:
            f.write(response.content)
        return True
    except Exception as e:
        print(f"Error downloading PDF: {e}")
        return False


def extract_figures_pdf2image(pdf_path: Path, output_dir: Path, dpi: int = 200) -> list:
    """Extract slides as images using pdf2image (poppler)."""
    if not PDF2IMAGE_AVAILABLE:
        raise ImportError("pdf2image not available")

    figures = []
    images = convert_from_path(str(pdf_path), dpi=dpi)

    for i, image in enumerate(images, 1):
        filename = f"slide-{i:02d}.png"
        filepath = output_dir / filename
        image.save(str(filepath), "PNG")

        figures.append({
            "slide_number": i,
            "filename": filename,
            "path": str(filepath),
            "width": image.width,
            "height": image.height
        })

    return figures


def extract_figures_pymupdf(pdf_path: Path, output_dir: Path, dpi: int = 200) -> list:
    """Extract slides as images using PyMuPDF."""
    if not PYMUPDF_AVAILABLE:
        raise ImportError("PyMuPDF not available")

    figures = []
    doc = fitz.open(str(pdf_path))

    for i, page in enumerate(doc, 1):
        # Render page to image
        mat = fitz.Matrix(dpi / 72, dpi / 72)
        pix = page.get_pixmap(matrix=mat)

        filename = f"slide-{i:02d}.png"
        filepath = output_dir / filename
        pix.save(str(filepath))

        figures.append({
            "slide_number": i,
            "filename": filename,
            "path": str(filepath),
            "width": pix.width,
            "height": pix.height
        })

    doc.close()
    return figures


def extract_embedded_images_pymupdf(pdf_path: Path, output_dir: Path) -> list:
    """Extract embedded images from PDF using PyMuPDF."""
    if not PYMUPDF_AVAILABLE:
        return []

    images = []
    doc = fitz.open(str(pdf_path))

    for page_num, page in enumerate(doc, 1):
        image_list = page.get_images()

        for img_idx, img in enumerate(image_list, 1):
            xref = img[0]

            try:
                base_image = doc.extract_image(xref)
                image_bytes = base_image["image"]
                image_ext = base_image["ext"]

                filename = f"slide-{page_num:02d}-img-{img_idx:02d}.{image_ext}"
                filepath = output_dir / filename

                with open(filepath, "wb") as f:
                    f.write(image_bytes)

                images.append({
                    "slide_number": page_num,
                    "image_index": img_idx,
                    "filename": filename,
                    "path": str(filepath),
                    "format": image_ext
                })
            except Exception as e:
                print(f"Error extracting image {img_idx} from page {page_num}: {e}")

    doc.close()
    return images


def extract_figures_from_pdf(
    pdf_url: str,
    ticker: str,
    presentation_name: str,
    extract_slides: bool = True,
    extract_embedded: bool = False,
    dpi: int = 200
) -> dict:
    """
    Main function to extract figures from a PDF presentation.

    Args:
        pdf_url: URL to the PDF file
        ticker: Company ticker (e.g., "ARWR")
        presentation_name: Name for the presentation (e.g., "ESC 2025 PALISADE")
        extract_slides: Whether to extract full slide images
        extract_embedded: Whether to extract embedded images
        dpi: Resolution for slide extraction

    Returns:
        dict with extraction results and metadata
    """
    # Create output directory
    safe_name = sanitize_filename(presentation_name)
    output_dir = PUBLIC_DIR / ticker.upper() / safe_name
    output_dir.mkdir(parents=True, exist_ok=True)

    # Generate unique ID
    url_hash = hashlib.md5(pdf_url.encode()).hexdigest()[:8]

    # Download PDF to temp file
    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
        tmp_path = Path(tmp.name)

    print(f"Downloading PDF from {pdf_url}...")
    if not download_pdf(pdf_url, tmp_path):
        return {"error": "Failed to download PDF"}

    result = {
        "id": f"{ticker.lower()}-{safe_name}-{url_hash}",
        "ticker": ticker.upper(),
        "presentation_name": presentation_name,
        "source_url": pdf_url,
        "output_dir": str(output_dir),
        "extracted_at": datetime.utcnow().isoformat(),
        "slides": [],
        "embedded_images": []
    }

    try:
        # Extract slide images
        if extract_slides:
            print(f"Extracting slides at {dpi} DPI...")

            if PDF2IMAGE_AVAILABLE:
                result["slides"] = extract_figures_pdf2image(tmp_path, output_dir, dpi)
                result["extraction_method"] = "pdf2image"
            elif PYMUPDF_AVAILABLE:
                result["slides"] = extract_figures_pymupdf(tmp_path, output_dir, dpi)
                result["extraction_method"] = "pymupdf"
            else:
                result["error"] = "No PDF extraction library available"
                return result

            print(f"Extracted {len(result['slides'])} slides")

        # Extract embedded images
        if extract_embedded and PYMUPDF_AVAILABLE:
            print("Extracting embedded images...")
            result["embedded_images"] = extract_embedded_images_pymupdf(tmp_path, output_dir)
            print(f"Extracted {len(result['embedded_images'])} embedded images")

    finally:
        # Clean up temp file
        if tmp_path.exists():
            tmp_path.unlink()

    # Convert paths to relative web paths
    for slide in result["slides"]:
        rel_path = Path(slide["path"]).relative_to(PUBLIC_DIR.parent)
        slide["web_path"] = "/" + str(rel_path).replace("\\", "/")

    for img in result["embedded_images"]:
        rel_path = Path(img["path"]).relative_to(PUBLIC_DIR.parent)
        img["web_path"] = "/" + str(rel_path).replace("\\", "/")

    return result


def get_extraction_status() -> dict:
    """Check which PDF libraries are available."""
    return {
        "pdf2image_available": PDF2IMAGE_AVAILABLE,
        "pymupdf_available": PYMUPDF_AVAILABLE,
        "ready": PDF2IMAGE_AVAILABLE or PYMUPDF_AVAILABLE
    }


if __name__ == "__main__":
    # Test extraction
    status = get_extraction_status()
    print(f"Extraction status: {status}")

    if status["ready"]:
        # Test with a sample PDF if URL provided
        import sys
        if len(sys.argv) > 1:
            url = sys.argv[1]
            result = extract_figures_from_pdf(
                pdf_url=url,
                ticker="ARWR",
                presentation_name="Test Presentation"
            )
            print(json.dumps(result, indent=2))
