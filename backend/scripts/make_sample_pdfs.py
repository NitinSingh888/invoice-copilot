#!/usr/bin/env python3
"""Generate sample invoice PDFs for testing the upload UI.

Writes three PDFs to <repo-root>/samples/.  Each PDF contains structured
Vendor / Invoice # / Amount / PO text that the extraction agent can parse.

Usage (from the backend/ directory):
    .venv/bin/python scripts/make_sample_pdfs.py

Requirements: fpdf2 (in optional dev deps), pypdf (in main deps).
"""
from __future__ import annotations

import sys
from pathlib import Path

try:
    from fpdf import FPDF
    from fpdf.enums import XPos, YPos
except ImportError:
    sys.exit(
        "fpdf2 is required: pip install fpdf2  (or: pip install -e '.[dev]')"
    )

try:
    from pypdf import PdfReader
except ImportError:
    PdfReader = None  # type: ignore[assignment,misc]


# ---------------------------------------------------------------------------
# Locate the output directory (repo-root/samples/)
# ---------------------------------------------------------------------------

_SCRIPT_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _SCRIPT_DIR.parent.parent  # backend/scripts/../../  = repo root
_OUT_DIR = _REPO_ROOT / "samples"
_OUT_DIR.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# Sample definitions
# ---------------------------------------------------------------------------

SAMPLES: list[dict[str, str]] = [
    {
        "filename": "sample_clean_autoclear.pdf",
        "description": "Clean auto-clear: known vendor, exact PO match",
        "content": (
            "INVOICE\n\n"
            "Vendor: Globex Trading\n"
            "Invoice: INV-9001\n"
            "Amount: 2480\n"
            "PO: PO-22845\n"
            "\nDate: 2025-06-01\n"
            "Due: 2025-07-01\n"
            "\nApproved vendor; amount matches PO exactly -> expected AUTO_CLEAR."
        ),
    },
    {
        "filename": "sample_over_po_escalation.pdf",
        "description": "Over-PO escalation: known vendor, ~7% over PO",
        "content": (
            "INVOICE\n\n"
            "Vendor: Acme Corp\n"
            "Invoice: INV-9002\n"
            "Amount: 8285\n"
            "PO: PO-22790\n"
            "\nDate: 2025-06-02\n"
            "Due: 2025-07-02\n"
            "\nAmount 8285 is ~7% over PO-22790 (7735) -> expected ESCALATE."
        ),
    },
    {
        "filename": "sample_unknown_vendor_no_po.pdf",
        "description": "Unknown vendor / no PO: new vendor, no purchase order",
        "content": (
            "INVOICE\n\n"
            "Vendor: Phantom Supplies Inc\n"
            "Invoice: INV-9003\n"
            "Amount: 4750\n"
            "\nDate: 2025-06-03\n"
            "Due: 2025-07-03\n"
            "\nVendor not in registry; no PO referenced -> expected ESCALATE."
        ),
    },
]


# ---------------------------------------------------------------------------
# PDF generation
# ---------------------------------------------------------------------------

def _cell(pdf: FPDF, text: str) -> None:
    """Write a single text line with a newline, compatible with fpdf2 >= 2.5."""
    pdf.cell(
        0, 7, text,
        new_x=XPos.LMARGIN, new_y=YPos.NEXT,
    )


def _make_pdf(sample: dict[str, str]) -> Path:
    pdf = FPDF()
    pdf.add_page()

    # Title banner
    pdf.set_font("Helvetica", style="B", size=16)
    _cell(pdf, "Invoice Copilot - Sample Invoice")
    pdf.ln(2)

    # Sub-title (description)
    pdf.set_font("Helvetica", style="I", size=10)
    _cell(pdf, sample["description"])
    pdf.ln(4)

    # Body text
    pdf.set_font("Courier", size=11)
    for line in sample["content"].splitlines():
        _cell(pdf, line)

    out_path = _OUT_DIR / sample["filename"]
    pdf.output(str(out_path))
    return out_path


def _verify_pdf(path: Path) -> str:
    """Return extracted text from the PDF (via pypdf)."""
    if PdfReader is None:
        return "(pypdf not available -- skipping verification)"
    reader = PdfReader(str(path))
    text = "".join(page.extract_text() or "" for page in reader.pages)
    return text


def main() -> None:
    print(f"Writing PDFs to: {_OUT_DIR}")
    for sample in SAMPLES:
        path = _make_pdf(sample)
        text = _verify_pdf(path)
        has_vendor = "Vendor:" in text or "Vendor" in text
        has_invoice = "Invoice:" in text or "INV-" in text
        has_amount = "Amount:" in text or "Amount" in text
        ok = "OK" if (has_vendor and has_invoice and has_amount) else "WARN"
        print(f"  [{ok}] {path.name}  ({path.stat().st_size} bytes)")
        if ok != "OK":
            print(f"       pypdf extracted: {text[:200]!r}")
    print("Done.")


if __name__ == "__main__":
    main()
