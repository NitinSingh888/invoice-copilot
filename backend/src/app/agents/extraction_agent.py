from __future__ import annotations

import base64

from app.clients.llm.base import LLMClient
from app.clients.llm.types import ExtractedInvoice


def extract(
    client: LLMClient,
    *,
    file_bytes: bytes,
    filename: str,
    content_type: str,
) -> ExtractedInvoice:
    """Extract invoice fields from uploaded file bytes.

    PDFs and images are sent directly to Claude's vision/document API.
    Claude reads the visual layout — more accurate than text extraction.
    """
    is_image = content_type.startswith("image/")

    # Everything goes through vision/document — Claude handles PDFs natively
    image_b64 = base64.b64encode(file_bytes).decode()
    text = ""

    # For plain text files (rare), fall back to text mode
    if not is_image and not content_type == "application/pdf" and not filename.lower().endswith(".pdf"):
        text = file_bytes.decode("utf-8", "ignore")
        image_b64 = None  # type: ignore[assignment]

    return client.extract_invoice(text=text, image_b64=image_b64)
