#!/usr/bin/env python3
"""Invoice Copilot — terminal walkthrough.

Drives the live API through the Observe → Decide → Audit story.
Run `make walkthrough` (server must already be running via `make run`).

Usage:
    DEMO_BASE_URL=http://localhost:8123 python scripts/demo.py
"""

from __future__ import annotations

import os
import sys

try:
    import httpx
except ImportError:
    sys.exit("httpx is required: pip install httpx  (or: make install)")

BASE_URL = os.environ.get("DEMO_BASE_URL", "http://localhost:8123").rstrip("/")

W = "\033[0m"   # reset
B = "\033[1m"   # bold
C = "\033[96m"  # cyan
G = "\033[92m"  # green
Y = "\033[93m"  # yellow
D = "\033[90m"  # dim


def sep(label: str = "") -> None:
    line = "─" * 60
    if label:
        pad = (60 - len(label) - 2) // 2
        print(f"\n{D}{line[:pad]} {B}{label}{W}{D} {line[:60 - pad - len(label) - 2]}{W}")
    else:
        print(f"{D}{line}{W}")


def step(n: int, title: str) -> None:
    print(f"\n{C}{B}[{n}/3] {title}{W}")


def check_server(client: httpx.Client) -> None:
    try:
        r = client.get(f"{BASE_URL}/api/v1/health", timeout=4)
        r.raise_for_status()
    except (httpx.ConnectError, httpx.TimeoutException):
        print(
            f"\n{Y}{B}Server not reachable at {BASE_URL}{W}\n"
            "Start the server first:  make run\n"
            "Then re-run:             make walkthrough\n"
        )
        sys.exit(1)


def main() -> None:
    sep("Invoice Copilot — Observe → Decide → Audit")
    print(f"{D}Base URL: {BASE_URL}{W}\n")

    with httpx.Client() as client:
        check_server(client)

        # ── Step 1: Reset / seed ──────────────────────────────────────────
        step(1, "OBSERVE  — fresh batch of today's invoices")
        print(
            "  The agent receives a new batch of invoices every morning.\n"
            "  We reset the database to a clean demo state:\n"
        )
        r = client.post(f"{BASE_URL}/api/v1/demo/reset", timeout=15)
        r.raise_for_status()
        data = r.json()
        count = data.get("received", "?")
        print(f"  {G}✓{W}  Batch seeded — {B}{count} invoices{W} loaded into the queue.")

        # ── Step 2: Process batch ─────────────────────────────────────────
        step(2, "DECIDE   — process today's invoices")
        print(
            "  The AP agent reads every invoice, matches POs, applies policy,\n"
            "  and decides: auto-clear, escalate, or block.\n"
        )
        r = client.post(
            f"{BASE_URL}/api/v1/chat",
            json={"message": "process today's invoices", "history": []},
            timeout=30,
        )
        r.raise_for_status()
        chat_data = r.json()
        reply = chat_data.get("reply", "")
        result = chat_data.get("result") or {}

        queued = result.get("queued", 0)
        needs = result.get("needs", 0)
        blocked = result.get("blocked", 0)

        print(f"  Agent reply:\n  {D}{reply}{W}\n")
        print(f"  {G}✓{W}  Batch processed:")
        print(f"       {B}{queued:>3}{W}  queued for payment run  (auto-cleared)")
        print(f"       {B}{needs:>3}{W}  need your review        (escalated)")
        print(f"       {B}{blocked:>3}{W}  blocked                 (hard stop — duplicate)")

        # ── Step 3: Audit trail ───────────────────────────────────────────
        step(3, "AUDIT    — verify the decision chain for INV-4471")
        print(
            "  Every decision is written to an append-only, hash-chained audit\n"
            "  log. Tamper with any event and the chain verification fails.\n"
        )
        r = client.get(f"{BASE_URL}/api/v1/audit/INV-4471", timeout=15)
        r.raise_for_status()
        audit_data = r.json()

        events = audit_data.get("events", [])
        verified = audit_data.get("chain_verified", False)
        n_events = len(events)

        status = f"{G}VERIFIED{W}" if verified else f"{Y}BROKEN{W}"
        print(f"  {G}✓{W}  Audit trail for INV-4471:")
        print(f"       Chain integrity : {B}{status}{W}")
        print(f"       Events recorded : {B}{n_events}{W}")

        if events:
            print(f"\n  {D}Event log:{W}")
            for ev in events:
                actor = ev.get("actor", "—")
                action = ev.get("action", "—")
                module = ev.get("module", "—")
                print(f"    {D}·{W}  [{module:12s}]  {actor:20s}  {action}")

        # ── Summary ───────────────────────────────────────────────────────
        sep("Summary")
        print(
            f"\n  {G}{B}Done.{W}  The full Observe → Decide → Audit loop ran in seconds.\n"
            "\n"
            "  Next steps:\n"
            f"    • Open {C}http://localhost:8123{W} — try the chat UI (Demo + Live modes).\n"
            "    • Run `make reset` then ask: 'explain INV-4471' or 'show me the rules'.\n"
            "    • Deploy to Render in one push — see render.yaml.\n"
        )
        sep()


if __name__ == "__main__":
    main()
