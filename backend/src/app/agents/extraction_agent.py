from __future__ import annotations

import base64
from io import BytesIO

from pypdf import PdfReader

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

    Routes to the appropriate path based on content type:
    - PDF: extract embedded text via pypdf (text path, image_b64=None)
    - Image: encode as base64, pass as image_b64 with empty text
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
        )
        image_b64 = None
    elif is_image:
        image_b64 = base64.b64encode(file_bytes).decode()
        text = ""
    else:
        text = file_bytes.decode("utf-8", "ignore")

    return client.extract_invoice(text=text, image_b64=image_b64)
