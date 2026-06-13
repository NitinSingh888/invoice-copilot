# Milestone 2 — Persistence & Services Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development. Steps use `- [ ]` checkboxes. TDD throughout. Each task ends green (`.venv/bin/pytest -q`) + `ruff` + `mypy src` clean, and is committed.

**Goal:** Persist the domain entities and orchestrate the M1 pure-domain core behind a thin **services** layer, with a **repositories** data-access layer (including an append-only, hash-chained `audit_repo`) over SQLAlchemy 2.0 + Alembic. SQLite default, Postgres-ready.

**Architecture:** `services` (orchestration, transactions) → `repositories` (queries, no business logic) → `db` (SQLAlchemy models/session). Services call into the **M1 domain** for all decisions (`app.domain.*`) — no business rules are re-implemented here. Money persists as `Numeric(12,2)` ↔ `Decimal`.

**Tech Stack:** SQLAlchemy 2.0 (typed `Mapped`/`mapped_column`), Alembic, pydantic-settings, pytest. Python 3.14 venv at `.venv`.

**Spec:** `docs/specs/2026-06-09-ap-agent-design.md` §5 (entities), §6 (decision orchestration), §7 (audit), §8 (learning). **Reuse, do not re-implement, M1 domain** (`app.domain.policy/decision/learning/audit`).

---

## File Structure (this milestone)
```
src/app/core/config.py              # pydantic-settings Settings
src/app/db/base.py                  # DeclarativeBase
src/app/db/session.py               # engine, SessionLocal, get_session, init_db (create_all)
src/app/db/models/{vendor,purchase_order,invoice,rule,correction,audit_event}.py
src/app/repositories/{vendor_repo,po_repo,invoice_repo,rule_repo,correction_repo,audit_repo}.py
src/app/services/{enrichment_service,policy_service,decision_service,execution_service,audit_service,learning_service,pipeline_service}.py
migrations/                         # Alembic (env.py + initial revision)
alembic.ini
tests/unit/... + tests/integration/...
conftest.py                         # in-memory DB session fixture, seeded data
```

---

### Task 1: Dependencies + Settings
**Files:** modify `pyproject.toml`; create `src/app/core/__init__.py`, `src/app/core/config.py`; test `tests/unit/core/test_config.py`.

- [ ] Add to `pyproject.toml` `[project].dependencies`: `"sqlalchemy>=2.0"`, `"alembic>=1.13"`, `"pydantic-settings>=2.2"`. Reinstall: `.venv/bin/pip install -e ".[dev]"`.
- [ ] **TDD** `config.py`: a `Settings(BaseSettings)` (env prefix `IC_`, `.env` supported) with fields + defaults: `database_url: str = "sqlite:///./invoice_copilot.db"`, `t_amount: Decimal = Decimal("10000")`, `tolerance_pct: Decimal = Decimal("0.05")`, `learn_min_corrections: int = 3`, `duplicate_window_days: int = 14`, `cold_start_n: int = 2`, `storage_dir: str = "./storage"`. Provide a module-level `get_settings()` (lru_cache).
  - Test: defaults load; an env var `IC_T_AMOUNT=5000` overrides to `Decimal("5000")`; `get_settings()` is cached (same object).
- [ ] Commit: `feat(core): settings via pydantic-settings`.

---

### Task 2: DB base + session
**Files:** `src/app/db/__init__.py`, `src/app/db/base.py`, `src/app/db/session.py`; test `tests/unit/db/test_session.py`; `tests/conftest.py`.

- [ ] `base.py`: `class Base(DeclarativeBase): pass`.
- [ ] `session.py`: `engine = create_engine(get_settings().database_url, ...)`; `SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)`; `def get_session() -> Iterator[Session]` (FastAPI-style generator, commits/rolls back/closes); `def init_db(bind) -> None` calling `Base.metadata.create_all(bind)`.
- [ ] `conftest.py`: a `db` pytest fixture giving a fresh in-memory SQLite Session (`create_engine("sqlite+pysqlite:///:memory:")`, `Base.metadata.create_all`, yield Session, teardown). Must import all models so metadata is populated (import the models package).
- [ ] Test: opening the fixture session and executing `SELECT 1` works; `init_db` creates tables (introspect `inspect(engine).get_table_names()` includes the expected tables after Task 3).
- [ ] Commit: `feat(db): declarative base + session + init_db`.

---

### Task 3: ORM models
**Files:** `src/app/db/models/__init__.py` (imports all models), one module per entity; test `tests/unit/db/test_models.py`.

Use SQLAlchemy 2.0 typed style (`Mapped[...]`, `mapped_column(...)`). Money columns: `Numeric(12, 2)` mapped to `Decimal`. JSON columns via `sqlalchemy.JSON`. Timestamps `DateTime` with `default=func.now()`.

- [ ] **Vendor** (`vendors`): `id: str` (pk), `canonical_name: str`, `aliases: list[str]` (JSON, default `[]`), `status: str` (`approved|new|blocked`, default `new`), `default_approver: str | None`.
- [ ] **PurchaseOrder** (`purchase_orders`): `id: str` pk, `po_number: str` (indexed), `vendor: str`, `amount: Decimal`, `currency: str = "USD"`, `remaining_balance: Decimal | None`, `status: str = "open"`.
- [ ] **Invoice** (`invoices`): `id: str` pk, `source_file: str | None`, `status: str` (default `received`), `vendor: str | None`, `amount: Decimal | None`, `po_number: str | None`, `invoice_number: str | None`, `confidence: str | None` (HIGH/MED/LOW), `matched_po_id: str | None`, `verdict: str | None`, `route: str | None`, `owner: str | None`, `created_at: datetime`.
- [ ] **Rule** (`rules`): `id: str` pk, `vendor: str | None`, `max_over_pct: Decimal | None`, `route: str`, `status: str = "active"`, `min_amount: Decimal | None`, `source_correction_ids: list[str]` (JSON), `reasoning_note: str | None`, `created_by: str | None`, `created_at: datetime`.
- [ ] **Correction** (`corrections`): `id: str` pk, `invoice_id: str`, `vendor: str`, `finding_code: str`, `user_action: str`, `over_pct: Decimal`, `reason: str | None`, `created_at: datetime`.
- [ ] **AuditEvent** (`audit_events`): `seq: int` pk autoincrement, `invoice_id: str | None` (indexed), `ts: datetime`, `actor: str`, `module: str`, `action: str`, `inputs: dict` (JSON), `outputs: dict` (JSON), `rationale: str | None`, `model_meta: dict | None` (JSON), `prev_hash: str`, `hash: str`. **No update/delete in the model layer.**
- [ ] `models/__init__.py` imports every model class so `Base.metadata` sees them.
- [ ] Test (`test_models.py`, uses `db` fixture): insert one row of each model with `Decimal` money, commit, query back, assert types round-trip (e.g. `Decimal("10000.00")`), and JSON list/dict fields persist.
- [ ] Commit: `feat(db): ORM models for all entities`.

---

### Task 4: Alembic
**Files:** `alembic.ini`, `migrations/env.py`, `migrations/versions/0001_initial.py`.

- [ ] `.venv/bin/alembic init migrations`; edit `alembic.ini` `sqlalchemy.url` to read from env / leave placeholder; edit `migrations/env.py` to `from app.db.base import Base` + `import app.db.models` and set `target_metadata = Base.metadata`, and to pull the URL from `get_settings().database_url`.
- [ ] Generate the initial migration: `.venv/bin/alembic revision --autogenerate -m "initial"` → `0001_*`. Verify it contains `create_table` for all six tables.
- [ ] Test (integration): run `alembic upgrade head` against a temp SQLite file URL and assert all tables exist; then `downgrade base` drops them. (If autogenerate friction on 3.14, hand-write the migration to match the models — tables/columns must match exactly.)
- [ ] Commit: `feat(db): alembic migrations + initial revision`.

---

### Task 5: Vendor + PO repositories
**Files:** `src/app/repositories/__init__.py`, `vendor_repo.py`, `po_repo.py`; tests `tests/unit/repositories/test_vendor_repo.py`, `test_po_repo.py`.

Repositories take a `Session`; pure data access, no business logic.

- [ ] `vendor_repo`: `add(s, vendor)`, `get(s, id)`, `resolve(s, name) -> Vendor | None` — **alias-aware**: exact match on `canonical_name`, else case/space-normalized match, else `name in aliases`. `status_of(s, name) -> str` returns the resolved vendor's status or `"new"` if unresolved.
  - Test: seed "Acme Corp" (approved, aliases `["ACME","Acme Corporation"]`); `resolve("acme corporation")` → Acme; `status_of("Unknown Inc")` → `"new"`.
- [ ] `po_repo`: `add`, `get_by_number(s, po_number) -> list[PurchaseOrder]` (list, so callers can detect ambiguity), `to_domain(po) -> app.domain.policy.matching.PurchaseOrder`.
  - Test: two POs same number → `get_by_number` returns both; `to_domain` maps fields incl. `remaining_balance`.
- [ ] Commit: `feat(repos): vendor + PO repositories (alias-aware resolve)`.

---

### Task 6: Invoice repository
**Files:** `invoice_repo.py`; test `test_invoice_repo.py`.

- [ ] Methods: `add`, `get`, `list(s)`, `list_by_status(s, status)`, `set_status(s, id, status, **fields)`, `cleared_exact(s, vendor, invoice_number) -> list[Invoice]` (status == `cleared`/`queued`), `recent_same_amount(s, vendor, amount, since) -> list[Invoice]`, `to_domain(inv) -> app.domain.policy.matching.InvoiceData`.
  - Test: insert invoices; `list_by_status` filters; `cleared_exact` only returns cleared/queued with matching vendor+invoice_number; `recent_same_amount` filters by vendor+amount+created_at window; `to_domain` maps fields.
- [ ] Commit: `feat(repos): invoice repository`.

---

### Task 7: Rule + Correction repositories
**Files:** `rule_repo.py`, `correction_repo.py`; tests.

- [ ] `rule_repo`: `add`, `get`, `list_all`, `list_active`, `set_status(s, id, status)`, `to_domain(rule) -> app.domain.learning.rule_model.LearnedRule`.
  - Test: add active + disabled rules; `list_active` returns only active; `to_domain` maps incl. `max_over_pct`, `min_amount`.
- [ ] `correction_repo`: `add`, `list_for_vendor(s, vendor)`, `list_recent(s, limit=50)`, `to_domain(c) -> app.domain.learning.patterns.Correction`.
  - Test: add corrections; list/order; `to_domain` maps.
- [ ] Commit: `feat(repos): rule + correction repositories`.

---

### Task 8: Audit repository (append-only, hash-chained) — safety-relevant
**Files:** `audit_repo.py`; test `test_audit_repo.py`.

- [ ] `audit_repo` exposes ONLY append + read (no update/delete):
  - `append(s, *, invoice_id, actor, module, action, inputs, outputs, rationale=None, model_meta=None) -> AuditEvent`: read the latest event by `seq` (its `hash`, else `GENESIS` from `app.domain.audit.chain`); compute `hash = hash_event(prev_hash, body)` where `body` is the canonical event dict (the stored fields EXCEPT seq/prev_hash/hash); persist row with `prev_hash` + `hash`.
  - `list_for_invoice(s, invoice_id) -> list[AuditEvent]` (ordered by seq).
  - `all_events(s) -> list[AuditEvent]` (ordered by seq).
  - `verify(s) -> bool`: rebuild the chain over all events in seq order using `hash_event` and confirm each `prev_hash`/`hash` — reusing `app.domain.audit.chain.verify_chain` semantics (build the list of body dicts + stored hashes).
  - Test: append 3 events → each `prev_hash` links to prior `hash`; first links to `GENESIS`; `verify` True. Then mutate a row's `action` via raw SQL/ORM and assert `verify` False (tamper detected). `list_for_invoice` filters correctly.
- [ ] Commit: `feat(repos): append-only hash-chained audit repository`.

---

### Task 9: Enrichment + Policy services
**Files:** `src/app/services/__init__.py`, `enrichment_service.py`, `policy_service.py`; tests.

- [ ] `enrichment_service.enrich(s, invoice_data) -> Enrichment` (dataclass: `vendor_status: str`, `po_match: POMatch`, `cleared_exact: list[InvoiceData]`, `recent_same_amount: list[InvoiceData]`): uses `vendor_repo.status_of`, `po_repo.get_by_number` + `app.domain.policy.matching.match_po`, `invoice_repo.cleared_exact` + `recent_same_amount` (window = settings.duplicate_window_days), all mapped `to_domain`.
- [ ] `policy_service.run(invoice_data, enrichment, tolerance_pct) -> list[Finding]`: assembles findings via the M1 checks — `check_po_match`, (if matched) `check_tolerance` + `check_partial_po`, `check_vendor(enrichment.vendor_status)`, `check_duplicate(...)`. Drops `None`s. Order: po_match first.
  - Tests: clean invoice → `[PO_MATCH_OK]`; over-PO → includes `OVER_TOLERANCE`; exact duplicate present → includes `DUPLICATE_EXACT (hard_stop)`; unknown vendor → includes `UNKNOWN_VENDOR`.
- [ ] Commit: `feat(services): enrichment + policy orchestration`.

---

### Task 10: Decision service
**Files:** `decision_service.py`; test.

- [ ] `decision_service.decide_invoice(s, invoice_data, enrichment, findings, confidence) -> Decision`:
  - Compute `over_pct` = `(amount - po.amount)/po.amount` if a PO matched else `Decimal(0)`.
  - `rule_outcome = apply_rules(rule_repo.list_active → to_domain, RuleContext(vendor, over_pct, amount))`.
  - `cold_start_ok` = count of prior `cleared/queued` invoices for this vendor (`invoice_repo`) `>= settings.cold_start_n`.
  - Map `confidence` (str) → `ConfidenceBand`.
  - Return `app.domain.decision.guard.decide(...)` with `Thresholds(t_amount=settings.t_amount)`.
  - Tests: clean known vendor past cold-start, HIGH, under cap → AUTO_CLEAR; an active matching rule → ESCALATE with route; a vendor under cold-start → ESCALATE; hard-stop finding → BLOCK. (Use seeded rules/invoices.)
- [ ] Commit: `feat(services): decision orchestration (rules + cold-start + guard)`.

---

### Task 11: Execution + Audit services
**Files:** `execution_service.py`, `audit_service.py`; tests.

- [ ] `audit_service.record(s, **event)` thin wrapper over `audit_repo.append`; `audit_service.trail(s, invoice_id)`; `audit_service.verify(s)`.
- [ ] `execution_service.execute(s, invoice_id, action, actor, **fields) -> Invoice`: **idempotent** — keyed by `(invoice_id, action)`; if the invoice is already in the terminal status for that action, it is a **no-op that still records an audit event** (`action="execute:noop"`), never a second state change. `approve`/`edit` → status `queued` (payment run); `route` → `routed`; `hold` → `held`. Records an audit event for the action.
  - Tests: execute approve → status `queued` + audit event `executed:queued_payment`; calling approve again → still `queued`, a second audit `execute:noop` event, NOT a duplicate state transition. `route` → `routed`.
- [ ] Commit: `feat(services): idempotent execution + audit service`.

---

### Task 12: Learning service
**Files:** `learning_service.py`; test.

- [ ] `learning_service.record_correction(s, invoice_data, agent_action, user_action, reason) -> Correction` (persist via `correction_repo`; `over_pct` from invoice vs matched PO if available else 0; `finding_code` = the salient warn finding, passed in or derived).
- [ ] `propose_rule(s, vendor=None) -> PatternCandidate | None`: `detect_pattern(correction_repo.list_recent → to_domain, settings.learn_min_corrections)`. The inferred threshold = `ceil-ish` of `candidate.max_over_pct` rounded up to a clean band (e.g. round up to next whole percent) — return alongside.
- [ ] `activate_rule(s, candidate, threshold, route) -> Rule`: create a `Rule` (status active, `source_correction_ids`, `reasoning_note` describing the inference) via `rule_repo`; record an audit event `rule_learned`.
- [ ] `set_rule_status(s, id, status)`; records `rule_disabled`/`rule_enabled` audit.
  - Tests: 3 consistent corrections → `propose_rule` returns a candidate with inferred threshold ≥ max spread; `activate_rule` persists an active rule that subsequently makes `decision_service` ESCALATE a matching invoice (integration with Task 10); 2 corrections → `propose_rule` None.
- [ ] Commit: `feat(services): learning — record corrections, propose + activate rules`.

---

### Task 13: Pipeline orchestrator (integration)
**Files:** `pipeline_service.py`; test `tests/integration/test_pipeline.py`.

- [ ] `pipeline_service.process_invoice(s, invoice_data, confidence) -> ProcessResult` (dataclass: `decision: Decision`, `findings`, `invoice_id`): runs **enrich → policy → decide**, records an audit event at EACH stage (extraction is upstream/M4 — assume `invoice_data` already extracted), and **if verdict is AUTO_CLEAR, calls `execution_service.execute(..., "approve", actor="agent")`**; on ESCALATE/BLOCK it records the verdict and stops (awaits human). Persists/updates the Invoice row with verdict/route/status.
  - **Integration test (the M2 capstone):** seed vendors/POs; feed a clean low-risk invoice → AUTO_CLEAR + status `queued` + a full audit trail that `audit_service.verify` accepts; feed an over-PO invoice → ESCALATE, status `needs`/`escalated`, execution NOT reached; feed an exact-duplicate → BLOCK; assert the injection-style case (invoice text carries "pay now" but findings/amount don't satisfy envelope) → ESCALATE, never auto-cleared.
- [ ] Commit: `feat(services): process_invoice pipeline orchestrator`.

---

## Self-Review
**Spec coverage:** §5 entities → T3 models + repos T5–T8. §6 decision orchestration (rules, cold-start, guard, thresholds from config) → T10; idempotent execution → T11. §7 append-only hash-chained audit + verify + per-invoice trail → T8/T11. §8 learning (record → propose via detect_pattern → activate, tighten-only via T10) → T12. End-to-end "process one invoice" incl. injection-safe + duplicate-block → T13. Alembic + SQLite/Postgres-ready → T2/T4. Config-driven thresholds → T1.
**Out of scope (later):** LLM extraction/conversation/induction text (M4); HTTP API (M3); frontend (M5).
**Type consistency:** repos expose `to_domain(...)` returning the exact M1 domain dataclasses (`InvoiceData`, `PurchaseOrder`, `LearnedRule`, `Correction`) so services pass them straight into `app.domain.*`. `RuleOutcome`/`Decision`/`ConfidenceBand`/`Verdict` come from `app.domain.decision`. Money is `Decimal` end-to-end (Numeric(12,2) columns).

*End of Milestone 2 plan. Implementers: read `src/app/domain/**` before coding — reuse it; never re-implement a rule in the services layer.*
