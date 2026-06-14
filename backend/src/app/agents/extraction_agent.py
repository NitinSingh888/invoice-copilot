from __future__ import annotations

import base64
import logging
from io import BytesIO

from pypdf import PdfReader

from app.clients.llm.base import LLMClient
from app.clients.llm.types import ExtractedInvoice

logger = logging.getLogger(__name__)

# Minimum text length to consider PDF text extraction "good enough".
# Below this, we fall back to vision mode (render page as image).
_MIN_TEXT_LENGTH = 50


def extract(
    client: LLMClient,
    *,
    file_bytes: bytes,
    filename: str,
    content_type: str,
) -> ExtractedInvoice:
    """Extract invoice fields from uploaded file bytes.

    Routes to the appropriate path based on content type:
    - PDF: try text extraction first; fall back to vision if text is poor
    - Image: encode as base64, pass to vision
    - Text/other: decode as UTF-8 and pass as text
    """
    image_b64: str | None = None
    text: str = ""

    is_pdf = content_type == "application/pdf" or filename.lower().endswith(".pdf")
    is_image = content_type.startswith("image/")

    if is_pdf:
        reader = PdfReader(BytesIO(file_bytes))
        text = "".join(
            (page.extract_text() or "") for page in reader.pages
        ).strip()

        # If text extraction produced too little content, fall back to vision.
        # This handles scanned PDFs, complex layouts, and image-based PDFs.
        if len(text) < _MIN_TEXT_LENGTH:
            logger.info(
                "PDF text extraction too short (%d chars) for %s — falling back to vision",
                len(text),
                filename,
            )
            image_b64 = _pdf_first_page_to_image(file_bytes)
            if image_b64:
                text = ""  # let vision handle it
            # else: keep whatever text we got and hope for the best

    elif is_image:
        image_b64 = base64.b64encode(file_bytes).decode()
        text = ""
    else:
        text = file_bytes.decode("utf-8", "ignore")

    result = client.extract_invoice(text=text, image_b64=image_b64)

    # If extraction returned empty vendor/amount with text mode,
    # retry with vision as a last resort
    if is_pdf and image_b64 is None and _is_poor_extraction(result):
        logger.info("Poor extraction result for %s — retrying with vision", filename)
        fallback_image = _pdf_first_page_to_image(file_bytes)
        if fallback_image:
            result = client.extract_invoice(text="", image_b64=fallback_image)

    return result


def _is_poor_extraction(result: ExtractedInvoice) -> bool:
    """True if the extraction result looks empty/useless."""
    no_vendor = not result.vendor or result.vendor.strip() == ""
    no_amount = result.amount is None or result.amount == 0
    return no_vendor and no_amount


def _pdf_first_page_to_image(file_bytes: bytes) -> str | None:
    """Render the first page of a PDF as a PNG image and return base64.

    Uses pypdf to extract the page, then converts via a simple approach.
    Returns None if rendering fails (no dependencies for image rendering).
    """
    try:
        # Try using pdf2image if available (requires poppler)
        from pdf2image import convert_from_bytes  # type: ignore[import-not-found]

        images = convert_from_bytes(file_bytes, first_page=1, last_page=1, dpi=200)
        if images:
            buf = BytesIO()
            images[0].save(buf, format="PNG")
            return base64.b64encode(buf.getvalue()).decode()
    except ImportError:
        pass
    except Exception:
        logger.warning("pdf2image conversion failed", exc_info=True)

    # Fallback: send the raw PDF bytes as base64 — Claude can handle PDF directly
    # via its document understanding capabilities
    return base64.b64encode(file_bytes).decode()
