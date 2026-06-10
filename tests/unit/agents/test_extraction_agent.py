"""Unit tests for extraction_agent — deterministic, no network."""
from __future__ import annotations

from decimal import Decimal
from io import BytesIO
from unittest.mock import MagicMock, patch

import pytest

from app.agents import extraction_agent
from app.clients.llm.mock_client import MockClient


PLAIN_TEXT = b"vendor: Acme Corp\namount: 9800\npo: PO-1\ninvoice_number: A-1"


@pytest.fixture()
def mock_client() -> MockClient:
    return MockClient()


# ---------------------------------------------------------------------------
# text/plain path
# ---------------------------------------------------------------------------


def test_extract_text_plain_vendor_and_amount(mock_client: MockClient) -> None:
    result = extraction_agent.extract(
        mock_client,
        file_bytes=PLAIN_TEXT,
        filename="inv.txt",
        content_type="text/plain",
    )
    assert result.vendor == "Acme Corp"
    assert result.amount == Decimal("9800")
    assert result.overall_confidence == "HIGH"


def test_extract_text_plain_po_and_invoice_number(mock_client: MockClient) -> None:
    result = extraction_agent.extract(
        mock_client,
        file_bytes=PLAIN_TEXT,
        filename="inv.txt",
        content_type="text/plain",
    )
    assert result.po_number == "PO-1"
    assert result.invoice_number == "A-1"


def test_extract_text_plain_missing_amount_gives_low(mock_client: MockClient) -> None:
    text = b"vendor: Acme Corp\npo: PO-1\ninvoice_number: A-1"
    result = extraction_agent.extract(
        mock_client,
        file_bytes=text,
        filename="inv.txt",
        content_type="text/plain",
    )
    assert result.overall_confidence == "LOW"
    assert result.amount is None


# ---------------------------------------------------------------------------
# image path
# ---------------------------------------------------------------------------


def test_extract_image_passes_b64(mock_client: MockClient) -> None:
    """For an image content_type the mock receives image_b64 with text=""."""
    called_with: dict[str, object] = {}

    original_extract = mock_client.extract_invoice

    def capture(**kwargs: object) -> object:  # type: ignore[misc]
        called_with.update(kwargs)
        return original_extract(**kwargs)  # type: ignore[arg-type]

    mock_client.extract_invoice = capture  # type: ignore[method-assign]

    extraction_agent.extract(
        mock_client,
        file_bytes=b"\x89PNG",
        filename="scan.png",
        content_type="image/png",
    )
    assert called_with.get("text") == ""
    assert called_with.get("image_b64") is not None


# ---------------------------------------------------------------------------
# PDF path — monkeypatched PdfReader
# ---------------------------------------------------------------------------


def test_extract_pdf_uses_text_path(mock_client: MockClient) -> None:
    """PDF branch extracts text via PdfReader; image_b64 stays None."""
    called_with: dict[str, object] = {}

    original_extract = mock_client.extract_invoice

    def capture(**kwargs: object) -> object:  # type: ignore[misc]
        called_with.update(kwargs)
        return original_extract(**kwargs)  # type: ignore[arg-type]

    mock_client.extract_invoice = capture  # type: ignore[method-assign]

    # Build a minimal in-memory PDF (single page with text)
    fake_page = MagicMock()
    fake_page.extract_text.return_value = (
        "vendor: Acme Corp\namount: 9800\npo: PO-1\ninvoice_number: A-1"
    )
    fake_reader = MagicMock()
    fake_reader.pages = [fake_page]

    with patch("app.agents.extraction_agent.PdfReader", return_value=fake_reader):
        result = extraction_agent.extract(
            mock_client,
            file_bytes=b"%PDF-1.4 fake",
            filename="invoice.pdf",
            content_type="application/pdf",
        )

    assert called_with.get("image_b64") is None
    assert isinstance(called_with.get("text"), str)
    assert result.vendor == "Acme Corp"


def test_extract_pdf_detected_by_filename(mock_client: MockClient) -> None:
    """Filename ending .pdf triggers the PDF path even without matching content_type."""
    fake_page = MagicMock()
    fake_page.extract_text.return_value = ""
    fake_reader = MagicMock()
    fake_reader.pages = [fake_page]

    with patch("app.agents.extraction_agent.PdfReader", return_value=fake_reader):
        # Should not raise — PDF path chosen by filename extension
        extraction_agent.extract(
            mock_client,
            file_bytes=b"%PDF-1.4 fake",
            filename="doc.pdf",
            content_type="application/octet-stream",
        )
