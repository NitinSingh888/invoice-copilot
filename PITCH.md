# Invoice Copilot — the one-page pitch

> An AI teammate for the person who pays the bills. You brief it once; it clears the routine invoices itself, asks you about the risky ones, learns your judgment, and logs every move for audit.

---

## The problem

Every company that receives supplier invoices has someone in **Accounts Payable (AP)** clearing a daily queue by hand. For each invoice they: open the document, read off vendor / amount / PO number, match it to the purchase order, check policy (duplicate? over budget? unknown vendor? over the PO?), and then **approve, route for sign-off, or hold** it.

It's **~3 hours a day** of repetitive work — and it's unforgiving: **duplicate and over-payments are among the costliest, most common finance leaks.** Generic automation (RPA) is brittle and breaks the moment a vendor changes their invoice layout; a chatbot can answer questions but can't actually *do* the work.

## Who it's for

The **AP clerk / finance-ops associate** (and the manager who signs off escalations). Persona: *Maya* clears the queue; *Priya* approves what Maya routes up.

## What it does

You talk to it. *"Process today's invoices."* It then, for every invoice:

1. **Reads** the document (vision/LLM) → structured fields + a confidence score.
2. **Matches** the purchase order and **checks policy** (tolerance, duplicates, budget, vendor).
3. **Decides** — and this is the important part — with **deterministic, auditable code, not the LLM**:
   - clean + low-risk → **auto-clears** it into the payment run;
   - over-tolerance / unknown vendor / low confidence → **escalates** to you as an **Approve / Hold / Edit** card *in the conversation*;
   - exact duplicate / blocked vendor → **blocks** it.
4. **Learns** — when you correct it the same way a few times, it proposes a *generalizing, editable rule* ("Acme over-PO by < ~8% → route to Priya") that you approve, and applies it next time.
5. **Logs** every step to a **tamper-evident (hash-chained) audit trail** you can replay.

So a 60-invoice morning becomes: *the agent cleared 40, you made 5 quick calls, 1 was blocked* — minutes instead of hours.

## Why it fits Zamp

Zamp builds **"AI employees" (Pace)** that run finance/ops processes end-to-end — and **invoice / accounts-payable automation is their flagship use case.** Invoice Copilot is a working miniature of exactly that, built the way Zamp has to build it:

- **The act-vs-ask boundary** (auto-clear the safe, escalate the rest) = Zamp's "monitor, act, escalate."
- **The LLM never moves money** — a deterministic guard decides; the model only proposes. (Prompt injection is unsolved; you can't gate payments on model judgment.)
- **A tamper-evident audit trail** — Zamp sells to banks; SOX/audit is the wedge.
- **Learns from corrections** — Zamp's "brief it once, it learns your process."

## The ROI

- **Time:** clears the routine 60-70% automatically → hours back per clerk per day.
- **Money:** catches duplicate/over-billing before payment (the expensive errors).
- **Trust:** every decision is explainable and replayable — audit-ready by construction.
- **It compounds:** the more you use it, the more of your judgment it absorbs.

## What it is — and isn't

**It is:** a vertical, action-taking conversational agent for one real workflow (AP invoice clearing), done deeply and safely, with a real backend (FastAPI + PostgreSQL), a deterministic safety core (259 tests), a real LLM layer (mock-by-default, swappable to Anthropic/OpenAI), and a production-grade React UI.

**It is *not* (deliberate scope):** a general chatbot, a full ERP, or connected to real bank rails (it queues into a simulated payment run). No multi-currency, no real auth/multi-tenancy. These are cut on purpose — the point is to do **one thing end-to-end and trustworthy**, not everything halfway.

---

*The thesis in one line: in finance automation, the hard part isn't reasoning — it's reliability, safety, and proof. So the LLM proposes; deterministic code decides and guards; and every action leaves an auditable trail.*
