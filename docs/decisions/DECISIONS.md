# Architecture Decision Record

Short, dated notes on the choices that shaped Invoice Copilot and the trade-offs behind them.

## 1. The LLM proposes; deterministic code decides and guards
**Decision:** the model only reads documents, converses, and drafts rules. Every money-moving verdict is computed by pure, tested code (`domain/decision/guard.py`).
**Why:** end-to-end financial workflows fail on reliability/safety, not reasoning. Prompt injection is unsolved industry-wide, and LLM tool-use is inconsistent across runs. Gating money on model judgment is unacceptable; gating it on a deterministic predicate is testable and injection-proof.
**Trade-off:** the agent is less "magic" — it can't freely take novel actions. That's the point.

## 2. Postgres everywhere (no SQLite)
**Decision:** local dev, tests, and production all run on Postgres. Local/test via a Docker container; production via Neon (free, no expiry).
**Why:** test against the same engine you ship on — catches engine-specific issues an in-memory SQLite shortcut hides. Chosen over Render's own free Postgres (deleted after 30 days) and Supabase (pauses after 7 days idle), both bad for a persistent demo link.
**Trade-off:** running `pytest` now requires Docker. Mitigated by `make db` and a CI Postgres service. Tests use a separate `copilot_test` DB with TRUNCATE-based isolation.

## 3. Mock-first LLM client
**Decision:** a provider-agnostic `LLMClient` protocol with a **deterministic `MockClient`** as the default, plus real Anthropic (primary) and OpenAI (secondary) adapters behind a failover.
**Why:** the whole app must run **key-free** so a reviewer just opens it; deterministic mocks also make tests reproducible (no network, no flakiness). The real adapters prove the integration without being required.
**Trade-off:** the mock's "intelligence" is rule-based, not a real model — fine for the demo; flip `IC_LLM_PROVIDER` for the real thing.

## 4. Append-only, hash-chained audit
**Decision:** every pipeline step appends an immutable event whose hash chains to the previous one; `verify()` recomputes the chain.
**Why:** mirrors a regulated-finance (SOX) audit trail and makes tampering detectable. Cheap to build, high narrative payoff, and doubles as the debugger.
**Trade-off:** app-enforced (no DB triggers); a production system would add storage-level immutability. Documented as such.

## 5. Learning that generalizes, with mandatory human confirmation
**Decision:** ≥N consistent corrections induce a *structured, threshold-generalized* rule, surfaced as an **editable card** the user must approve before it ever applies. Approved rules are evaluated by deterministic code, and may only *tighten* the verdict.
**Why:** examples are ambiguous (Gulwani) — a literal echo isn't learning and silent learning is unsafe. Generalization + human-in-the-loop is the honest design.
**Trade-off:** needs a few corrections before it helps (cold start) — acceptable and realistic.

## 6. Request/response chat (no streaming)
**Decision:** the conversational endpoint is request/response; an escalation simply ends the turn with an approval card; the user's click is a new request.
**Why:** streaming + mid-turn human-approval pausing is the riskiest integration and most likely demo-breaker. Request/response is simpler and equally demoable.
**Trade-off:** less "typing" feel. Listed as future work.

## 7. `create_all` + seed-on-boot instead of Alembic (for now)
**Decision:** the app creates tables and seeds the demo batch on startup if the DB is empty.
**Why:** ideal for an ephemeral demo and a fresh Neon DB — zero migration steps. The schema is fully ORM-defined and migration-ready; Alembic is the documented production path.
**Trade-off:** no incremental migrations yet — fine for a prototype, called out explicitly.

## 8. Layered structure (api → services → domain + repositories)
**Decision:** thin HTTP handlers call orchestration services, which compose a **pure domain core** and data-access repositories. The domain has no I/O.
**Why:** the pure core is exhaustively unit-testable (it holds the safety logic) and the boundaries keep files small and reasoning local. Strong code-quality signal.
**Trade-off:** more files/indirection than a flat app — justified by testability and clarity.
