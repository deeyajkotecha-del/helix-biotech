"""
PDF Vision Analyzer

Uses Claude Vision API to extract structured data from investor presentations.
Converts PDFs to images and analyzes each slide.
"""

import os
import asyncio
import aiohttp
import base64
import json
import tempfile
from pathlib import Path
from typing import List, Optional
from datetime import datetime, timezone

# Try to import PDF libraries
try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False

try:
    from pdf2image import convert_from_path
    PDF2IMAGE_AVAILABLE = True
except ImportError:
    PDF2IMAGE_AVAILABLE = False


# Slide analysis prompt
SLIDE_ANALYSIS_PROMPT = """Analyze this investor presentation slide and extract ALL data in structured JSON format.

Return ONLY valid JSON (no markdown, no explanation) with this structure:
{
  "slide_number": <int>,
  "slide_title": "<title from slide>",
  "slide_type": "<one of: title, pipeline, clinical_data, mechanism, financials, timeline, competitive, team, other>",
  "key_data_points": [
    {"label": "<metric name>", "value": "<value>", "unit": "<unit if any>", "context": "<any qualifier>"}
  ],
  "tables": [
    {"title": "<table title>", "headers": ["col1", "col2"], "rows": [["val1", "val2"]]}
  ],
  "charts": [
    {"type": "<bar|line|pie|waterfall|kaplan_meier>", "title": "<title>", "data_summary": "<key findings>"}
  ],
  "pipeline_assets": [
    {"name": "<drug name>", "target": "<target>", "indication": "<indication>", "stage": "<phase>", "partner": "<if any>"}
  ],
  "clinical_results": [
    {"trial": "<trial name>", "endpoint": "<endpoint>", "result": "<result>", "p_value": "<if shown>", "comparator": "<if shown>"}
  ],
  "catalysts": [
    {"event": "<event>", "timing": "<date or period>", "asset": "<drug name>"}
  ],
  "citations": ["<any sources or references mentioned>"],
  "raw_text": "<key text content if not captured above>"
}

If a section has no data, use empty array []. Extract EVERY number and data point visible."""


class PDFVisionAnalyzer:
    """Analyze PDFs using Claude Vision API."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY required")

        self.api_url = "https://api.anthropic.com/v1/messages"

    async def analyze_presentation(
        self,
        pdf_source: str,
        max_slides: int = 50,
        skip_slides: List[int] = None
    ) -> dict:
        """
        Analyze a presentation PDF.

        Args:
            pdf_source: URL or local path to PDF
            max_slides: Maximum slides to analyze
            skip_slides: Slide numbers to skip (e.g., [1, 2] for title slides)

        Returns:
            dict with presentation data and extracted information
        """
        skip_slides = skip_slides or []

        result = {
            "source_url": pdf_source if pdf_source.startswith("http") else None,
            "analyzed_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "total_slides": 0,
            "analyzed_slides": 0,
            "slides": [],
            "extracted_data": {
                "pipeline": [],
                "clinical_results": [],
                "catalysts": [],
                "financials": [],
                "key_metrics": []
            },
            "errors": []
        }

        # Download PDF if URL
        if pdf_source.startswith("http"):
            pdf_path = await self._download_pdf(pdf_source)
            if not pdf_path:
                result["errors"].append(f"Failed to download PDF: {pdf_source}")
                return result
        else:
            pdf_path = pdf_source

        # Convert PDF to images
        images = await self._pdf_to_images(pdf_path)
        if not images:
            result["errors"].append("Failed to convert PDF to images")
            return result

        result["total_slides"] = len(images)

        # Analyze each slide
        for i, (img_data, img_format) in enumerate(images[:max_slides]):
            slide_num = i + 1

            if slide_num in skip_slides:
                continue

            print(f"  Analyzing slide {slide_num}/{len(images)}...")

            try:
                slide_analysis = await self._analyze_slide(img_data, img_format, slide_num)
                if slide_analysis:
                    result["slides"].append(slide_analysis)
                    result["analyzed_slides"] += 1

                    # Merge extracted data
                    self._merge_extracted_data(result["extracted_data"], slide_analysis)

            except Exception as e:
                result["errors"].append(f"Slide {slide_num}: {str(e)}")

            # Rate limiting
            await asyncio.sleep(0.5)

        # Clean up temp file
        if pdf_source.startswith("http") and pdf_path:
            try:
                os.remove(pdf_path)
            except:
                pass

        return result

    async def _download_pdf(self, url: str) -> Optional[str]:
        """Download PDF to temp file."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=60)) as response:
                    if response.status != 200:
                        return None

                    # Save to temp file
                    fd, path = tempfile.mkstemp(suffix=".pdf")
                    with os.fdopen(fd, "wb") as f:
                        f.write(await response.read())
                    return path

        except Exception as e:
            print(f"Download error: {e}")
            return None

    async def _pdf_to_images(self, pdf_path: str) -> List[tuple]:
        """Convert PDF to list of (image_data, format) tuples."""
        images = []

        if PYMUPDF_AVAILABLE:
            try:
                doc = fitz.open(pdf_path)
                for page_num in range(len(doc)):
                    page = doc[page_num]
                    # Render at 2x for better quality
                    pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
                    img_data = pix.tobytes("png")
                    images.append((base64.b64encode(img_data).decode(), "image/png"))
                doc.close()
                return images
            except Exception as e:
                print(f"PyMuPDF error: {e}")

        if PDF2IMAGE_AVAILABLE:
            try:
                pil_images = convert_from_path(pdf_path, dpi=150)
                for img in pil_images:
                    import io
                    buffer = io.BytesIO()
                    img.save(buffer, format="PNG")
                    img_data = base64.b64encode(buffer.getvalue()).decode()
                    images.append((img_data, "image/png"))
                return images
            except Exception as e:
                print(f"pdf2image error: {e}")

        return images

    async def _analyze_slide(self, img_data: str, img_format: str, slide_num: int) -> Optional[dict]:
        """Analyze a single slide with Claude Vision."""
        headers = {
            "x-api-key": self.api_key,
            "content-type": "application/json",
            "anthropic-version": "2023-06-01"
        }

        payload = {
            "model": "claude-sonnet-4-20250514",
            "max_tokens": 4000,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": img_format,
                                "data": img_data
                            }
                        },
                        {
                            "type": "text",
                            "text": f"Slide {slide_num}. {SLIDE_ANALYSIS_PROMPT}"
                        }
                    ]
                }
            ]
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(self.api_url, headers=headers, json=payload) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        print(f"API error: {error_text}")
                        return None

                    data = await response.json()
                    content = data["content"][0]["text"]

                    # Parse JSON from response
                    return self._parse_slide_json(content, slide_num)

        except Exception as e:
            print(f"Analysis error: {e}")
            return None

    def _parse_slide_json(self, content: str, slide_num: int) -> dict:
        """Parse JSON from Claude response."""
        # Try to find JSON in response
        content = content.strip()

        # Remove markdown code blocks if present
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]

        # Find JSON boundaries
        start = content.find("{")
        end = content.rfind("}") + 1

        if start >= 0 and end > start:
            try:
                data = json.loads(content[start:end])
                data["slide_number"] = slide_num
                return data
            except json.JSONDecodeError as e:
                print(f"JSON parse error: {e}")
                return {
                    "slide_number": slide_num,
                    "slide_type": "parse_error",
                    "raw_text": content[:500]
                }

        return {
            "slide_number": slide_num,
            "slide_type": "no_json",
            "raw_text": content[:500]
        }

    def _merge_extracted_data(self, target: dict, slide: dict):
        """Merge slide data into target extracted_data."""
        # Pipeline assets
        for asset in slide.get("pipeline_assets", []):
            if asset.get("name"):
                # Check for duplicates
                existing = [a for a in target["pipeline"] if a.get("name") == asset["name"]]
                if not existing:
                    target["pipeline"].append(asset)

        # Clinical results
        for result in slide.get("clinical_results", []):
            if result.get("trial") or result.get("endpoint"):
                target["clinical_results"].append(result)

        # Catalysts
        for catalyst in slide.get("catalysts", []):
            if catalyst.get("event"):
                target["catalysts"].append(catalyst)

        # Key metrics from data points
        for point in slide.get("key_data_points", []):
            if point.get("label") and point.get("value"):
                target["key_metrics"].append(point)


async def analyze_presentation(pdf_url: str) -> dict:
    """Convenience function to analyze a presentation."""
    analyzer = PDFVisionAnalyzer()
    return await analyzer.analyze_presentation(pdf_url)


async def main():
    """Test PDF analyzer."""
    # Test with a sample PDF (you'd need a real URL)
    print("=" * 70)
    print("PDF Vision Analyzer")
    print("=" * 70)

    if not os.getenv("ANTHROPIC_API_KEY"):
        print("\nANTHROPIC_API_KEY not set. Set it to test PDF analysis.")
        return

    # Check PDF library availability
    print(f"\nPyMuPDF available: {PYMUPDF_AVAILABLE}")
    print(f"pdf2image available: {PDF2IMAGE_AVAILABLE}")

    if not PYMUPDF_AVAILABLE and not PDF2IMAGE_AVAILABLE:
        print("\nNo PDF library available. Install pymupdf or pdf2image.")
        return

    print("\nAnalyzer ready. Use analyze_presentation(pdf_url) to analyze PDFs.")


if __name__ == "__main__":
    asyncio.run(main())
