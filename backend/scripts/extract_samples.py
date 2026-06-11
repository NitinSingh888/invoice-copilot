"""One-off: run the REAL extractor over the downloaded sample invoice PDFs and
print the extracted fields, so we can design the demo seed around real data.

Usage (from backend/, with .env providing IC_ANTHROPIC_API_KEY):
    .venv/bin/python scripts/extract_samples.py
"""

from __future__ import annotations

import json
from pathlib import Path

from app.agents import extraction_agent
from app.clients.llm.factory import build_llm_client
from app.core.config import get_settings

SAMPLES = Path(__file__).resolve().parent.parent / "data" / "sample_invoices"


def main() -> None:
    settings = get_settings()
    client = build_llm_client(settings)
    print(f"provider={settings.llm_provider} model={settings.anthropic_model}\n")

    rows = []
    for pdf in sorted(SAMPLES.glob("*.pdf")):
        data = pdf.read_bytes()
        ext = extraction_agent.extract(
            client, file_bytes=data, filename=pdf.name, content_type="application/pdf"
        )
        row = {
            "file": pdf.name,
            "vendor": ext.vendor,
            "amount": str(ext.amount) if ext.amount is not None else None,
            "po_number": ext.po_number,
            "invoice_number": ext.invoice_number,
            "confidence": ext.overall_confidence,
        }
        rows.append(row)
        print(
            f"{pdf.name:24} | {str(ext.vendor)[:28]:28} | "
            f"amt={row['amount']!s:>12} | po={ext.po_number!s:>10} | "
            f"inv={ext.invoice_number!s:>14} | conf={ext.overall_confidence}"
        )

    out = SAMPLES.parent / "extracted_samples.json"
    out.write_text(json.dumps(rows, indent=2))
    print(f"\nwrote {out}")


if __name__ == "__main__":
    main()
