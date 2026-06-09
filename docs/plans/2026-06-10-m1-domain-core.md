# Milestone 1 — Domain Core Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the pure, deterministic safety core of Invoice Copilot — policy findings, PO matching, tolerance/duplicate/vendor checks, the decision-guard verdict pipeline, learned-rule evaluation, correction-pattern detection, and the tamper-evident audit hash-chain — fully test-driven, with zero I/O.

**Architecture:** Everything in this milestone lives under `src/app/domain/` and is **pure** (functions over dataclasses, no DB, no network, no LLM). This is the "code decides and guards" half of the spec's core principle (LLM proposes, code decides). Money is `Decimal`. Later milestones (persistence, API, agents, frontend) call into this core; keeping it pure makes it exhaustively unit-testable and is the strongest code-quality signal.

**Tech Stack:** Python 3.11+, `pytest`, `Decimal`, `dataclasses`, `enum`; tooling `ruff` + `mypy`. Package layout `src/app/...` with `pyproject.toml` (setuptools, src layout).

**Spec reference:** `docs/specs/2026-06-09-zamp-ap-agent-design.md` — §5 (domain model), §6 (guard), §7 (audit chain), §8 (learning), §14 (tests).

---

## File Structure (created in this milestone)

```
invoice-copilot/
├── pyproject.toml                       # package + tooling + pytest config
├── src/app/__init__.py
├── src/app/domain/__init__.py
├── src/app/domain/money.py              # Decimal parsing/formatting helpers
├── src/app/domain/policy/__init__.py
├── src/app/domain/policy/findings.py    # Severity, Finding, max_severity
├── src/app/domain/policy/matching.py    # InvoiceData, PurchaseOrder, POMatch, match_po
├── src/app/domain/policy/checks.py      # per-check functions + run_policy
├── src/app/domain/decision/__init__.py
├── src/app/domain/decision/thresholds.py# ConfidenceBand, Verdict, Thresholds
├── src/app/domain/decision/guard.py     # Decision, decide() — the verdict pipeline
├── src/app/domain/learning/__init__.py
├── src/app/domain/learning/rule_model.py# LearnedRule, RuleContext, RuleOutcome, apply_rules
├── src/app/domain/learning/patterns.py  # Correction, PatternCandidate, detect_pattern
└── src/app/domain/audit/__init__.py
    src/app/domain/audit/chain.py        # hash_event, chain, verify_chain
tests/unit/domain/...                    # mirrors the above
```

---

### Task 1: Project scaffold

**Files:**
- Create: `pyproject.toml`
- Create: `src/app/__init__.py`, `src/app/domain/__init__.py`
- Create: `tests/__init__.py`, `tests/unit/__init__.py`, `tests/unit/domain/__init__.py`
- Create: `tests/unit/test_smoke.py`

- [ ] **Step 1: Write `pyproject.toml`**

```toml
[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[project]
name = "invoice-copilot"
version = "0.1.0"
description = "A conversational AI accounts-payable agent"
requires-python = ">=3.11"
dependencies = []

[project.optional-dependencies]
dev = ["pytest>=8", "ruff>=0.5", "mypy>=1.10"]

[tool.setuptools.packages.find]
where = ["src"]

[tool.pytest.ini_options]
pythonpath = ["src"]
testpaths = ["tests"]
addopts = "-q"

[tool.ruff]
line-length = 100
src = ["src", "tests"]

[tool.mypy]
python_version = "3.11"
mypy_path = "src"
strict = true
```

- [ ] **Step 2: Create the empty package + test `__init__.py` files**

Create each of these as an empty file: `src/app/__init__.py`, `src/app/domain/__init__.py`, `tests/__init__.py`, `tests/unit/__init__.py`, `tests/unit/domain/__init__.py`.

- [ ] **Step 3: Write a smoke test**

`tests/unit/test_smoke.py`:
```python
def test_app_package_imports():
    import app
    assert app is not None
```

- [ ] **Step 4: Install dev deps and run the smoke test**

Run: `pip install -e ".[dev]" && pytest tests/unit/test_smoke.py -v`
Expected: PASS (1 passed).

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml src tests
git commit -m "chore: scaffold src-layout package, pytest, tooling"
```

---

### Task 2: Money helpers

**Files:**
- Create: `src/app/domain/money.py`
- Test: `tests/unit/domain/test_money.py`

- [ ] **Step 1: Write the failing test**

```python
from decimal import Decimal
from app.domain.money import to_money, fmt_usd

def test_to_money_parses_int_and_str():
    assert to_money(12400) == Decimal("12400")
    assert to_money("12400.50") == Decimal("12400.50")

def test_to_money_quantizes_to_cents():
    assert to_money("10.005") == Decimal("10.01")  # round half-up to cents

def test_fmt_usd():
    assert fmt_usd(Decimal("12400")) == "$12,400.00"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/domain/test_money.py -v`
Expected: FAIL with `ModuleNotFoundError: app.domain.money`.

- [ ] **Step 3: Write minimal implementation**

`src/app/domain/money.py`:
```python
from __future__ import annotations
from decimal import Decimal, ROUND_HALF_UP

CENTS = Decimal("0.01")

def to_money(value: int | str | Decimal) -> Decimal:
    """Coerce a value to a 2-dp Decimal (USD, single currency for the prototype)."""
    return Decimal(str(value)).quantize(CENTS, rounding=ROUND_HALF_UP)

def fmt_usd(amount: Decimal) -> str:
    return f"${amount:,.2f}"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/domain/test_money.py -v`
Expected: PASS (3 passed).

- [ ] **Step 5: Commit**

```bash
git add src/app/domain/money.py tests/unit/domain/test_money.py
git commit -m "feat(domain): money Decimal helpers"
```

---

### Task 3: Policy findings

**Files:**
- Create: `src/app/domain/policy/__init__.py` (empty)
- Create: `src/app/domain/policy/findings.py`
- Test: `tests/unit/domain/policy/__init__.py` (empty), `tests/unit/domain/policy/test_findings.py`

- [ ] **Step 1: Write the failing test**

```python
from app.domain.policy.findings import Severity, Finding, max_severity

def test_finding_is_frozen_value():
    f = Finding("PO_MATCH_OK", Severity.INFO, "Matched PO-1")
    assert (f.code, f.severity, f.detail) == ("PO_MATCH_OK", Severity.INFO, "Matched PO-1")

def test_max_severity_empty_is_info():
    assert max_severity([]) is Severity.INFO

def test_max_severity_picks_highest():
    findings = [
        Finding("A", Severity.INFO, ""),
        Finding("B", Severity.WARN, ""),
        Finding("C", Severity.INFO, ""),
    ]
    assert max_severity(findings) is Severity.WARN

def test_hard_stop_dominates():
    findings = [Finding("B", Severity.WARN, ""), Finding("D", Severity.HARD_STOP, "")]
    assert max_severity(findings) is Severity.HARD_STOP
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/domain/policy/test_findings.py -v`
Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Write minimal implementation**

`src/app/domain/policy/findings.py`:
```python
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from collections.abc import Iterable

class Severity(str, Enum):
    INFO = "info"
    WARN = "warn"
    HARD_STOP = "hard_stop"

_ORDER = {Severity.INFO: 0, Severity.WARN: 1, Severity.HARD_STOP: 2}

@dataclass(frozen=True)
class Finding:
    code: str
    severity: Severity
    detail: str = ""

def max_severity(findings: Iterable[Finding]) -> Severity:
    items = list(findings)
    if not items:
        return Severity.INFO
    return max((f.severity for f in items), key=lambda s: _ORDER[s])
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/domain/policy/test_findings.py -v`
Expected: PASS (4 passed).

- [ ] **Step 5: Commit**

```bash
git add src/app/domain/policy/__init__.py src/app/domain/policy/findings.py tests/unit/domain/policy
git commit -m "feat(domain): policy Finding + Severity + max_severity"
```

---

### Task 4: PO matching

**Files:**
- Create: `src/app/domain/policy/matching.py`
- Test: `tests/unit/domain/policy/test_matching.py`

- [ ] **Step 1: Write the failing test**

```python
from decimal import Decimal
from app.domain.policy.matching import InvoiceData, PurchaseOrder, match_po

def _inv(po_number):
    return InvoiceData(invoice_id="INV-1", vendor="Acme", amount=Decimal("100"),
                       po_number=po_number, invoice_number="A-1")

def test_match_single_po():
    pos = [PurchaseOrder("PO-1", "Acme", Decimal("100"))]
    m = match_po(_inv("PO-1"), pos)
    assert m.po is pos[0] and m.ambiguous is False

def test_no_po_number_returns_none():
    m = match_po(_inv(None), [PurchaseOrder("PO-1", "Acme", Decimal("100"))])
    assert m.po is None and m.ambiguous is False

def test_unmatched_po_number_returns_none():
    m = match_po(_inv("PO-9"), [PurchaseOrder("PO-1", "Acme", Decimal("100"))])
    assert m.po is None and m.ambiguous is False

def test_multiple_matches_is_ambiguous():
    pos = [PurchaseOrder("PO-1", "Acme", Decimal("100")),
           PurchaseOrder("PO-1", "Acme", Decimal("200"))]
    m = match_po(_inv("PO-1"), pos)
    assert m.po is None and m.ambiguous is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/domain/policy/test_matching.py -v`
Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Write minimal implementation**

`src/app/domain/policy/matching.py`:
```python
from __future__ import annotations
from dataclasses import dataclass
from decimal import Decimal
from collections.abc import Sequence

@dataclass(frozen=True)
class PurchaseOrder:
    po_number: str
    vendor: str
    amount: Decimal
    remaining_balance: Decimal | None = None

@dataclass(frozen=True)
class InvoiceData:
    invoice_id: str
    vendor: str
    amount: Decimal
    po_number: str | None
    invoice_number: str

@dataclass(frozen=True)
class POMatch:
    po: PurchaseOrder | None
    ambiguous: bool = False

def match_po(invoice: InvoiceData, pos: Sequence[PurchaseOrder]) -> POMatch:
    if not invoice.po_number:
        return POMatch(po=None)
    candidates = [p for p in pos if p.po_number == invoice.po_number]
    if len(candidates) == 0:
        return POMatch(po=None)
    if len(candidates) > 1:
        return POMatch(po=None, ambiguous=True)
    return POMatch(po=candidates[0])
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/domain/policy/test_matching.py -v`
Expected: PASS (4 passed).

- [ ] **Step 5: Commit**

```bash
git add src/app/domain/policy/matching.py tests/unit/domain/policy/test_matching.py
git commit -m "feat(domain): PO matching (single/none/ambiguous)"
```

---

### Task 5: Policy checks (PO, tolerance, partial, vendor)

**Files:**
- Create: `src/app/domain/policy/checks.py`
- Test: `tests/unit/domain/policy/test_checks.py`

- [ ] **Step 1: Write the failing test**

```python
from decimal import Decimal
from app.domain.policy.findings import Severity
from app.domain.policy.matching import InvoiceData, PurchaseOrder, POMatch
from app.domain.policy.checks import (
    check_po_match, check_tolerance, check_partial_po, check_vendor,
)

def _inv(amount, po_number="PO-1"):
    return InvoiceData("INV-1", "Acme", Decimal(amount), po_number, "A-1")

def test_check_po_match_ok():
    po = PurchaseOrder("PO-1", "Acme", Decimal("100"))
    f = check_po_match(_inv("100"), POMatch(po=po))
    assert f.code == "PO_MATCH_OK" and f.severity is Severity.INFO

def test_check_po_match_ambiguous():
    f = check_po_match(_inv("100"), POMatch(po=None, ambiguous=True))
    assert f.code == "MULTI_PO_MATCH" and f.severity is Severity.WARN

def test_check_po_missing_vs_unmatched():
    assert check_po_match(_inv("100", None), POMatch(None)).code == "MISSING_PO"
    assert check_po_match(_inv("100", "PO-X"), POMatch(None)).code == "NO_PO_MATCH"

def test_tolerance_within_returns_none():
    po = PurchaseOrder("PO-1", "Acme", Decimal("100"))
    assert check_tolerance(_inv("104"), po, Decimal("0.05")) is None  # 4% <= 5%

def test_tolerance_over():
    po = PurchaseOrder("PO-1", "Acme", Decimal("100"))
    f = check_tolerance(_inv("113"), po, Decimal("0.05"))
    assert f.code == "OVER_TOLERANCE" and f.severity is Severity.WARN

def test_tolerance_under():
    po = PurchaseOrder("PO-1", "Acme", Decimal("100"))
    f = check_tolerance(_inv("80"), po, Decimal("0.05"))
    assert f.code == "UNDER_TOLERANCE"

def test_partial_po_flags_when_po_partly_fulfilled():
    po = PurchaseOrder("PO-1", "Acme", Decimal("100"), remaining_balance=Decimal("40"))
    f = check_partial_po(_inv("30"), po)  # 30 <= remaining 40, but PO partly used
    assert f.code == "PARTIAL_PO" and f.severity is Severity.WARN

def test_vendor_status():
    assert check_vendor("approved") is None
    assert check_vendor("new").code == "UNKNOWN_VENDOR"
    assert check_vendor("blocked").severity is Severity.HARD_STOP
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/domain/policy/test_checks.py -v`
Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Write minimal implementation**

`src/app/domain/policy/checks.py`:
```python
from __future__ import annotations
from decimal import Decimal
from .findings import Finding, Severity
from .matching import InvoiceData, PurchaseOrder, POMatch

def check_po_match(invoice: InvoiceData, match: POMatch) -> Finding:
    if match.ambiguous:
        return Finding("MULTI_PO_MATCH", Severity.WARN, "Multiple POs match this number")
    if match.po is None:
        if invoice.po_number:
            return Finding("NO_PO_MATCH", Severity.WARN, f"No PO {invoice.po_number}")
        return Finding("MISSING_PO", Severity.WARN, "No PO referenced")
    return Finding("PO_MATCH_OK", Severity.INFO, f"Matched {match.po.po_number}")

def check_tolerance(invoice: InvoiceData, po: PurchaseOrder, tolerance_pct: Decimal) -> Finding | None:
    diff = invoice.amount - po.amount
    if po.amount == 0 or diff == 0:
        return None
    pct = diff / po.amount
    if pct > tolerance_pct:
        return Finding("OVER_TOLERANCE", Severity.WARN, f"{pct:.0%} over PO")
    if pct < -tolerance_pct:
        return Finding("UNDER_TOLERANCE", Severity.WARN, f"{abs(pct):.0%} under PO")
    return None

def check_partial_po(invoice: InvoiceData, po: PurchaseOrder) -> Finding | None:
    if po.remaining_balance is None:
        return None
    if po.remaining_balance < po.amount and invoice.amount <= po.remaining_balance:
        return Finding("PARTIAL_PO", Severity.WARN, "PO is only partly fulfilled")
    return None

def check_vendor(vendor_status: str) -> Finding | None:
    if vendor_status == "approved":
        return None
    if vendor_status == "blocked":
        return Finding("VENDOR_BLOCKED", Severity.HARD_STOP, "Vendor is blocked")
    return Finding("UNKNOWN_VENDOR", Severity.WARN, "Vendor not yet approved")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/domain/policy/test_checks.py -v`
Expected: PASS (8 passed).

- [ ] **Step 5: Commit**

```bash
git add src/app/domain/policy/checks.py tests/unit/domain/policy/test_checks.py
git commit -m "feat(domain): policy checks (po, tolerance, partial, vendor)"
```

---

### Task 6: Duplicate detection

**Files:**
- Modify: `src/app/domain/policy/checks.py` (add `check_duplicate`)
- Test: `tests/unit/domain/policy/test_duplicate.py`

- [ ] **Step 1: Write the failing test**

```python
from decimal import Decimal
from app.domain.policy.findings import Severity
from app.domain.policy.matching import InvoiceData
from app.domain.policy.checks import check_duplicate

def _inv(inv_no, amount="100"):
    return InvoiceData("INV-NEW", "Acme", Decimal(amount), "PO-1", inv_no)

def test_exact_duplicate_is_hard_stop():
    cleared = [InvoiceData("INV-OLD", "Acme", Decimal("100"), "PO-1", "A-1")]
    f = check_duplicate(_inv("A-1"), cleared_exact=cleared, recent_same_amount=[])
    assert f.code == "DUPLICATE_EXACT" and f.severity is Severity.HARD_STOP
    assert "INV-OLD" in f.detail

def test_suspected_duplicate_is_warn():
    recent = [InvoiceData("INV-OLD", "Acme", Decimal("100"), "PO-1", "A-2")]
    f = check_duplicate(_inv("A-1"), cleared_exact=[], recent_same_amount=recent)
    assert f.code == "DUPLICATE_SUSPECT" and f.severity is Severity.WARN

def test_no_duplicate_returns_none():
    assert check_duplicate(_inv("A-1"), cleared_exact=[], recent_same_amount=[]) is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/domain/policy/test_duplicate.py -v`
Expected: FAIL with `ImportError: cannot import name 'check_duplicate'`.

- [ ] **Step 3: Append implementation to `checks.py`**

Add to `src/app/domain/policy/checks.py`:
```python
from collections.abc import Sequence

def check_duplicate(
    invoice: InvoiceData,
    cleared_exact: Sequence[InvoiceData],
    recent_same_amount: Sequence[InvoiceData],
) -> Finding | None:
    """Exact = same (vendor, invoice_number) already cleared → hard stop.
    Suspect = same (vendor, amount) recently, different/missing invoice number → warn.
    Caller is responsible for pre-filtering the two candidate lists by vendor/window."""
    for c in cleared_exact:
        if c.vendor == invoice.vendor and c.invoice_number == invoice.invoice_number:
            return Finding("DUPLICATE_EXACT", Severity.HARD_STOP, f"Already cleared as {c.invoice_id}")
    for c in recent_same_amount:
        if (c.vendor == invoice.vendor and c.amount == invoice.amount
                and c.invoice_number != invoice.invoice_number):
            return Finding("DUPLICATE_SUSPECT", Severity.WARN, "Same vendor + amount seen recently")
    return None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/domain/policy/test_duplicate.py -v`
Expected: PASS (3 passed).

- [ ] **Step 5: Commit**

```bash
git add src/app/domain/policy/checks.py tests/unit/domain/policy/test_duplicate.py
git commit -m "feat(domain): explicit duplicate detection (exact=hard-stop, suspect=warn)"
```

---

### Task 7: Decision guard — the verdict pipeline

**Files:**
- Create: `src/app/domain/decision/__init__.py` (empty)
- Create: `src/app/domain/decision/thresholds.py`
- Create: `src/app/domain/decision/guard.py`
- Test: `tests/unit/domain/decision/__init__.py` (empty), `tests/unit/domain/decision/test_guard.py`

- [ ] **Step 1: Write the failing test (covers all precedence branches)**

```python
from decimal import Decimal
from app.domain.policy.findings import Finding, Severity
from app.domain.decision.thresholds import ConfidenceBand, Verdict, Thresholds
from app.domain.decision.guard import decide, RuleOutcome

T = Thresholds(t_amount=Decimal("10000"))

def _ok_findings():
    return [Finding("PO_MATCH_OK", Severity.INFO, "")]

def test_auto_clear_happy_path():
    d = decide(findings=_ok_findings(), confidence=ConfidenceBand.HIGH,
               amount=Decimal("2000"), vendor_status="approved",
               rule_outcome=None, thresholds=T, cold_start_ok=True)
    assert d.verdict is Verdict.AUTO_CLEAR

def test_hard_stop_blocks_even_if_everything_else_ok():
    findings = [Finding("DUPLICATE_EXACT", Severity.HARD_STOP, "")]
    d = decide(findings=findings, confidence=ConfidenceBand.HIGH,
               amount=Decimal("100"), vendor_status="approved",
               rule_outcome=None, thresholds=T, cold_start_ok=True)
    assert d.verdict is Verdict.BLOCK

def test_amount_over_cap_escalates():
    d = decide(findings=_ok_findings(), confidence=ConfidenceBand.HIGH,
               amount=Decimal("12400"), vendor_status="approved",
               rule_outcome=None, thresholds=T, cold_start_ok=True)
    assert d.verdict is Verdict.ESCALATE

def test_low_confidence_escalates():
    d = decide(findings=_ok_findings(), confidence=ConfidenceBand.MED,
               amount=Decimal("100"), vendor_status="approved",
               rule_outcome=None, thresholds=T, cold_start_ok=True)
    assert d.verdict is Verdict.ESCALATE

def test_warn_finding_escalates():
    findings = [Finding("OVER_TOLERANCE", Severity.WARN, "")]
    d = decide(findings=findings, confidence=ConfidenceBand.HIGH,
               amount=Decimal("100"), vendor_status="approved",
               rule_outcome=None, thresholds=T, cold_start_ok=True)
    assert d.verdict is Verdict.ESCALATE

def test_unapproved_vendor_escalates():
    d = decide(findings=_ok_findings(), confidence=ConfidenceBand.HIGH,
               amount=Decimal("100"), vendor_status="new",
               rule_outcome=None, thresholds=T, cold_start_ok=True)
    assert d.verdict is Verdict.ESCALATE

def test_cold_start_blocks_auto_clear():
    d = decide(findings=_ok_findings(), confidence=ConfidenceBand.HIGH,
               amount=Decimal("100"), vendor_status="approved",
               rule_outcome=None, thresholds=T, cold_start_ok=False)
    assert d.verdict is Verdict.ESCALATE

def test_rule_forces_escalate_on_otherwise_auto_clearable():
    # THE precedence test: a learned rule downgrades an auto-clearable invoice.
    ro = RuleOutcome(force_escalate=True, route="Priya", rule_id="R-7")
    d = decide(findings=_ok_findings(), confidence=ConfidenceBand.HIGH,
               amount=Decimal("2000"), vendor_status="approved",
               rule_outcome=ro, thresholds=T, cold_start_ok=True)
    assert d.verdict is Verdict.ESCALATE
    assert d.route == "Priya" and "R-7" in d.reason

def test_rule_cannot_loosen_hard_stop():
    # A rule must never turn a hard-stop into anything but BLOCK.
    findings = [Finding("DUPLICATE_EXACT", Severity.HARD_STOP, "")]
    ro = RuleOutcome(force_escalate=False, route=None, rule_id="R-9")
    d = decide(findings=findings, confidence=ConfidenceBand.HIGH,
               amount=Decimal("100"), vendor_status="approved",
               rule_outcome=ro, thresholds=T, cold_start_ok=True)
    assert d.verdict is Verdict.BLOCK
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/domain/decision/test_guard.py -v`
Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Write minimal implementation**

`src/app/domain/decision/thresholds.py`:
```python
from __future__ import annotations
from dataclasses import dataclass
from decimal import Decimal
from enum import Enum

class ConfidenceBand(str, Enum):
    HIGH = "HIGH"
    MED = "MED"
    LOW = "LOW"

class Verdict(str, Enum):
    AUTO_CLEAR = "AUTO_CLEAR"
    ESCALATE = "ESCALATE"
    BLOCK = "BLOCK"

@dataclass(frozen=True)
class Thresholds:
    t_amount: Decimal = Decimal("10000")
```

`src/app/domain/decision/guard.py`:
```python
from __future__ import annotations
from dataclasses import dataclass
from decimal import Decimal
from collections.abc import Sequence
from app.domain.policy.findings import Finding, Severity, max_severity
from .thresholds import ConfidenceBand, Verdict, Thresholds

@dataclass(frozen=True)
class RuleOutcome:
    """Result of evaluating learned rules. Tighten-only: may force escalation
    and set a route, but can never authorise auto-clear."""
    force_escalate: bool
    route: str | None
    rule_id: str

@dataclass(frozen=True)
class Decision:
    verdict: Verdict
    reason: str
    route: str | None = None

def decide(
    *,
    findings: Sequence[Finding],
    confidence: ConfidenceBand,
    amount: Decimal,
    vendor_status: str,
    rule_outcome: RuleOutcome | None,
    thresholds: Thresholds,
    cold_start_ok: bool,
) -> Decision:
    # 1. Hard stop — always wins, cannot be loosened by anything.
    if max_severity(findings) is Severity.HARD_STOP:
        return Decision(Verdict.BLOCK, "Hard-stop finding; never auto-paid.")

    # 2. Learned rules — tighten only (force escalate / set route).
    if rule_outcome is not None and rule_outcome.force_escalate:
        return Decision(Verdict.ESCALATE,
                        f"Learned rule {rule_outcome.rule_id} matched (rules may only tighten).",
                        route=rule_outcome.route)

    # 3. Envelope — auto-clear only if every condition holds.
    if (confidence is ConfidenceBand.HIGH
            and amount <= thresholds.t_amount
            and max_severity(findings) is Severity.INFO
            and vendor_status == "approved"
            and cold_start_ok):
        return Decision(Verdict.AUTO_CLEAR,
                        "HIGH confidence, within cap, all findings info, approved vendor → auto-clear.")

    # 4. Otherwise — hand to a human.
    return Decision(Verdict.ESCALATE, "Outside the auto-clear envelope → escalate to a human.")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/domain/decision/test_guard.py -v`
Expected: PASS (9 passed).

- [ ] **Step 5: Commit**

```bash
git add src/app/domain/decision tests/unit/domain/decision
git commit -m "feat(domain): decision guard verdict pipeline (rules tighten-only)"
```

---

### Task 8: Learned-rule model & application

**Files:**
- Create: `src/app/domain/learning/__init__.py` (empty)
- Create: `src/app/domain/learning/rule_model.py`
- Test: `tests/unit/domain/learning/__init__.py` (empty), `tests/unit/domain/learning/test_rule_model.py`

- [ ] **Step 1: Write the failing test**

```python
from decimal import Decimal
from app.domain.learning.rule_model import LearnedRule, RuleContext, apply_rules

def _rule(rid="R-7", vendor="Acme", pct="0.08", route="Priya", status="active"):
    return LearnedRule(id=rid, vendor=vendor, max_over_pct=Decimal(pct), route=route, status=status)

def test_rule_matches_vendor_and_threshold():
    ctx = RuleContext(vendor="Acme", over_pct=Decimal("0.06"))
    out = apply_rules([_rule()], ctx)
    assert out is not None and out.force_escalate and out.route == "Priya" and out.rule_id == "R-7"

def test_rule_does_not_match_above_threshold():
    ctx = RuleContext(vendor="Acme", over_pct=Decimal("0.12"))  # 12% > 8%
    assert apply_rules([_rule()], ctx) is None

def test_rule_does_not_match_other_vendor():
    ctx = RuleContext(vendor="Globex", over_pct=Decimal("0.04"))
    assert apply_rules([_rule()], ctx) is None

def test_disabled_rule_is_ignored():
    ctx = RuleContext(vendor="Acme", over_pct=Decimal("0.04"))
    assert apply_rules([_rule(status="disabled")], ctx) is None

def test_most_specific_rule_wins():
    broad = LearnedRule("R-1", vendor="Acme", max_over_pct=Decimal("0.10"), route="Priya")
    specific = LearnedRule("R-2", vendor="Acme", max_over_pct=Decimal("0.10"),
                           route="CFO", min_amount=Decimal("5000"))
    ctx = RuleContext(vendor="Acme", over_pct=Decimal("0.04"), amount=Decimal("9000"))
    out = apply_rules([broad, specific], ctx)
    assert out.rule_id == "R-2" and out.route == "CFO"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/domain/learning/test_rule_model.py -v`
Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Write minimal implementation**

`src/app/domain/learning/rule_model.py`:
```python
from __future__ import annotations
from dataclasses import dataclass
from decimal import Decimal
from collections.abc import Sequence
from app.domain.decision.guard import RuleOutcome

@dataclass(frozen=True)
class LearnedRule:
    id: str
    vendor: str | None
    max_over_pct: Decimal | None
    route: str
    status: str = "active"
    min_amount: Decimal | None = None

    @property
    def specificity(self) -> int:
        return sum(c is not None for c in (self.vendor, self.max_over_pct, self.min_amount))

@dataclass(frozen=True)
class RuleContext:
    vendor: str
    over_pct: Decimal
    amount: Decimal | None = None

def _matches(rule: LearnedRule, ctx: RuleContext) -> bool:
    if rule.status != "active":
        return False
    if rule.vendor is not None and rule.vendor != ctx.vendor:
        return False
    if rule.max_over_pct is not None and ctx.over_pct >= rule.max_over_pct:
        return False
    if rule.min_amount is not None and (ctx.amount is None or ctx.amount < rule.min_amount):
        return False
    return True

def apply_rules(rules: Sequence[LearnedRule], ctx: RuleContext) -> RuleOutcome | None:
    matching = [r for r in rules if _matches(r, ctx)]
    if not matching:
        return None
    winner = max(matching, key=lambda r: r.specificity)  # most-specific wins
    return RuleOutcome(force_escalate=True, route=winner.route, rule_id=winner.id)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/domain/learning/test_rule_model.py -v`
Expected: PASS (5 passed).

- [ ] **Step 5: Commit**

```bash
git add src/app/domain/learning/__init__.py src/app/domain/learning/rule_model.py tests/unit/domain/learning
git commit -m "feat(domain): learned-rule model + tighten-only application (most-specific wins)"
```

---

### Task 9: Correction-pattern detection

**Files:**
- Create: `src/app/domain/learning/patterns.py`
- Test: `tests/unit/domain/learning/test_patterns.py`

- [ ] **Step 1: Write the failing test**

```python
from decimal import Decimal
from app.domain.learning.patterns import Correction, detect_pattern

def _c(inv, pct):
    return Correction(invoice_id=inv, vendor="Acme", finding_code="OVER_TOLERANCE",
                      user_action="route", over_pct=Decimal(pct))

def test_three_consistent_corrections_trigger_a_candidate():
    cands = detect_pattern([_c("INV-1", "0.06"), _c("INV-2", "0.04"), _c("INV-3", "0.07")], min_count=3)
    assert cands is not None
    assert cands.vendor == "Acme" and cands.action == "route"
    assert cands.example_ids == ["INV-1", "INV-2", "INV-3"]
    assert cands.max_over_pct == Decimal("0.07")  # spread upper bound, for threshold inference

def test_two_corrections_do_not_trigger():
    assert detect_pattern([_c("INV-1", "0.06"), _c("INV-2", "0.04")], min_count=3) is None

def test_inconsistent_shapes_do_not_trigger():
    mixed = [
        _c("INV-1", "0.06"),
        Correction("INV-2", "Globex", "OVER_TOLERANCE", "route", Decimal("0.04")),
        Correction("INV-3", "Acme", "OVER_TOLERANCE", "hold", Decimal("0.05")),
    ]
    assert detect_pattern(mixed, min_count=3) is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/domain/learning/test_patterns.py -v`
Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Write minimal implementation**

`src/app/domain/learning/patterns.py`:
```python
from __future__ import annotations
from dataclasses import dataclass
from decimal import Decimal
from collections import defaultdict
from collections.abc import Sequence

@dataclass(frozen=True)
class Correction:
    invoice_id: str
    vendor: str
    finding_code: str
    user_action: str
    over_pct: Decimal

@dataclass(frozen=True)
class PatternCandidate:
    vendor: str
    finding_code: str
    action: str
    example_ids: list[str]
    over_pcts: list[Decimal]

    @property
    def max_over_pct(self) -> Decimal:
        return max(self.over_pcts)

def _shape(c: Correction) -> tuple[str, str, str]:
    return (c.vendor, c.finding_code, c.user_action)

def detect_pattern(corrections: Sequence[Correction], min_count: int = 3) -> PatternCandidate | None:
    groups: dict[tuple[str, str, str], list[Correction]] = defaultdict(list)
    for c in corrections:
        groups[_shape(c)].append(c)
    for (vendor, code, action), items in groups.items():
        if len(items) >= min_count:
            return PatternCandidate(
                vendor=vendor, finding_code=code, action=action,
                example_ids=[c.invoice_id for c in items],
                over_pcts=[c.over_pct for c in items],
            )
    return None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/domain/learning/test_patterns.py -v`
Expected: PASS (3 passed).

- [ ] **Step 5: Commit**

```bash
git add src/app/domain/learning/patterns.py tests/unit/domain/learning/test_patterns.py
git commit -m "feat(domain): correction-pattern detection (same-shape, >=N)"
```

---

### Task 10: Tamper-evident audit hash-chain

**Files:**
- Create: `src/app/domain/audit/__init__.py` (empty)
- Create: `src/app/domain/audit/chain.py`
- Test: `tests/unit/domain/audit/__init__.py` (empty), `tests/unit/domain/audit/test_chain.py`

- [ ] **Step 1: Write the failing test**

```python
from app.domain.audit.chain import chain, verify_chain, GENESIS

def _events():
    return [
        {"module": "extraction", "action": "read"},
        {"module": "guard", "action": "verdict:ESCALATE"},
        {"module": "execution", "action": "queued"},
    ]

def test_chain_links_prev_hash():
    out = chain(_events())
    assert out[0]["prev_hash"] == GENESIS
    assert out[1]["prev_hash"] == out[0]["hash"]
    assert out[2]["prev_hash"] == out[1]["hash"]

def test_verify_accepts_untampered_chain():
    assert verify_chain(chain(_events())) is True

def test_verify_detects_tampering():
    out = chain(_events())
    out[1]["action"] = "verdict:AUTO_CLEAR"  # someone edits a past event
    assert verify_chain(out) is False

def test_verify_detects_deletion():
    out = chain(_events())
    del out[1]  # drop the middle event
    assert verify_chain(out) is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/domain/audit/test_chain.py -v`
Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Write minimal implementation**

`src/app/domain/audit/chain.py`:
```python
from __future__ import annotations
import hashlib
import json
from collections.abc import Sequence

GENESIS = "0" * 64

def hash_event(prev_hash: str, event: dict) -> str:
    payload = prev_hash + json.dumps(event, sort_keys=True, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()

def chain(events: Sequence[dict]) -> list[dict]:
    prev = GENESIS
    out: list[dict] = []
    for e in events:
        body = {k: v for k, v in e.items() if k not in ("prev_hash", "hash")}
        h = hash_event(prev, body)
        out.append({**body, "prev_hash": prev, "hash": h})
        prev = h
    return out

def verify_chain(chained: Sequence[dict]) -> bool:
    prev = GENESIS
    for e in chained:
        body = {k: v for k, v in e.items() if k not in ("prev_hash", "hash")}
        if e.get("prev_hash") != prev or e.get("hash") != hash_event(prev, body):
            return False
        prev = e["hash"]
    return True
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/domain/audit/test_chain.py -v`
Expected: PASS (4 passed).

- [ ] **Step 5: Commit**

```bash
git add src/app/domain/audit tests/unit/domain/audit
git commit -m "feat(domain): tamper-evident audit hash-chain + verify"
```

---

### Task 11: Full-suite green + lint gate

**Files:** none (verification task)

- [ ] **Step 1: Run the entire unit suite**

Run: `pytest -q`
Expected: PASS — all tests from Tasks 2–10 green (≈ 40 assertions), no failures.

- [ ] **Step 2: Run ruff**

Run: `ruff check src tests`
Expected: no errors (fix any reported lint inline, re-run until clean).

- [ ] **Step 3: Commit any lint fixes**

```bash
git add -A
git commit -m "chore: lint clean for domain core" || echo "nothing to commit"
```

---

## Self-Review (completed)

**Spec coverage (M1 scope):** §5 domain model → Tasks 3,4,8,9 (Finding, PO, LearnedRule, Correction). §6 guard incl. precedence + rules-tighten-only + cold-start + confidence bands → Task 7. §5.2 duplicate detection → Task 6. §8 learning (pattern detect + rule eval + most-specific) → Tasks 8,9. §7.2 hash-chain + verify → Task 10. Partial/multi-PO + vendor aliasing inputs → Tasks 4,5. **Out of M1 scope (later milestones):** persistence/ORM (M2), services/run_policy orchestration across DB (M2), API (M3), LLM extraction + rule *induction text* + conversation (M4), frontend wiring (M5), README/seed/demo (M6).

**Placeholder scan:** none — every step has runnable test + impl code and exact commands.

**Type consistency:** `Finding`, `Severity`, `InvoiceData`, `PurchaseOrder`, `POMatch` used consistently across Tasks 3–6; `RuleOutcome` defined in `decision/guard.py` (Task 7) and imported by `learning/rule_model.py` (Task 8) — single source, no duplication; `ConfidenceBand`/`Verdict`/`Thresholds` defined once (Task 7). `Decimal` used for all money. `RuleContext.amount` is optional and only used by `min_amount` rules (Task 8 test covers it).

---

*End of Milestone 1 plan. M2–M6 will be planned as their own documents once M1 is green.*
