"""Build a corpus of ~100 real-style invoice documents for the demo.

Pulls invoice images from the open Voxel51 high-quality-invoice-images-for-ocr
dataset (varied templates), runs the REAL extractor (vision) on each, and caches
the extracted fields. Run ONCE at build time:

    PYTHONPATH=src .venv/bin/python scripts/build_corpus.py

Outputs:
    data/invoices_corpus/<file>.jpg        the document images
    data/invoices_corpus/extracted.json    [{file, vendor, amount, po_number,
                                             invoice_number, confidence}]
"""

from __future__ import annotations

import json
import urllib.request
from pathlib import Path

from app.agents import extraction_agent
from app.clients.llm.factory import build_llm_client
from app.core.config import get_settings

TARGET = 100
PAGE = 100  # datasets-server caps a single request at length=100
PAGES = 2  # fetch up to 200 rows to absorb failures
DATASET = "Voxel51%2Fhigh-quality-invoice-images-for-ocr"
OUT = Path(__file__).resolve().parent.parent / "data" / "invoices_corpus"


def _fetch_rows() -> list[dict]:
    out: list[dict] = []
    for p in range(PAGES):
        url = (
            "https://datasets-server.huggingface.co/rows"
            f"?dataset={DATASET}&config=default&split=train&offset={p * PAGE}&length={PAGE}"
        )
        with urllib.request.urlopen(url, timeout=60) as resp:  # noqa: S310
            out.extend(json.loads(resp.read())["rows"])
    return out


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    settings = get_settings()
    client = build_llm_client(settings)
    print(f"provider={settings.llm_provider} model={settings.anthropic_model}")

    rows = _fetch_rows()
    print(f"fetched {len(rows)} rows")

    results: list[dict[str, object]] = []
    for i, r in enumerate(rows):
        if len(results) >= TARGET:
            break
        img = r["row"].get("image")
        if not isinstance(img, dict) or "src" not in img:
            continue
        fname = f"inv-c{i:03d}.jpg"
        fpath = OUT / fname
        try:
            with urllib.request.urlopen(img["src"], timeout=60) as ir:  # noqa: S310
                data = ir.read()
            fpath.write_bytes(data)
            ext = extraction_agent.extract(
                client, file_bytes=data, filename=fname, content_type="image/jpeg"
            )
            row = {
                "file": fname,
                "vendor": ext.vendor,
                "amount": str(ext.amount) if ext.amount is not None else None,
                "po_number": ext.po_number,
                "invoice_number": ext.invoice_number,
                "confidence": ext.overall_confidence,
            }
            results.append(row)
            print(
                f"[{len(results):3}/{TARGET}] {fname} | {str(ext.vendor)[:26]:26} | "
                f"amt={row['amount']!s:>10} | inv={ext.invoice_number!s:>12} | "
                f"conf={ext.overall_confidence}"
            )
            # incremental save so a crash keeps progress
            (OUT / "extracted.json").write_text(json.dumps(results, indent=2))
        except Exception as e:  # noqa: BLE001
            print(f"  skip {fname}: {type(e).__name__}: {e}")
            if fpath.exists():
                fpath.unlink()

    print(f"\nDONE — {len(results)} invoices in {OUT}")


if __name__ == "__main__":
    main()
