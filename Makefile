# Invoice Copilot — developer entry points
# Run `make help` to see all targets (the default).

.PHONY: help install db db-down run test lint typecheck check seed reset demo walkthrough docker-build

help:  ## Show this help message
	@echo ""
	@echo "  Invoice Copilot — make targets"
	@echo ""
	@echo "  Setup"
	@echo "    make install       Install the package + dev deps into .venv"
	@echo "    make db            Start Postgres container (docker compose)"
	@echo "    make db-down       Stop and remove Postgres container"
	@echo ""
	@echo "  Development"
	@echo "    make run           Start the API server on :8123 (requires make db first)"
	@echo "    make test          Run the test suite (requires make db first)"
	@echo "    make lint          Ruff lint check on src + tests"
	@echo "    make typecheck     Mypy type check on src"
	@echo "    make check         lint + typecheck + test"
	@echo ""
	@echo "  Demo"
	@echo "    make seed          Force-reseed the running API server"
	@echo "    make reset         Alias for seed"
	@echo "    make demo          Print demo instructions"
	@echo "    make walkthrough   Run the terminal walkthrough against a running server"
	@echo ""
	@echo "  Docker"
	@echo "    make docker-build  Build the production Docker image (invoice-copilot)"
	@echo ""

# ── Setup ────────────────────────────────────────────────────────────────────

install:  ## Create .venv if missing, then install package + dev deps
	@if [ ! -d .venv ]; then python3 -m venv .venv; fi
	.venv/bin/pip install -e ".[dev]"

# ── Database ─────────────────────────────────────────────────────────────────

db:  ## Start Postgres container and wait until healthy
	docker compose up -d postgres
	@echo "Waiting for Postgres to be healthy..."
	@until docker compose exec -T postgres pg_isready -U copilot -q; do sleep 1; done
	@echo "Postgres is ready."

db-down:  ## Stop and remove the Postgres container
	docker compose down

# ── Run ──────────────────────────────────────────────────────────────────────

run: db  ## Start the API server (hot-reload, port 8123)
	PYTHONPATH=src .venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8123 --reload

# ── Quality ──────────────────────────────────────────────────────────────────

# NOTE: `make test` requires `make db` to be run first (Postgres must be up).
test:  ## Run the test suite with pytest (requires make db)
	.venv/bin/pytest -q

lint:  ## Ruff lint check
	.venv/bin/ruff check src tests

typecheck:  ## Mypy type check
	.venv/bin/mypy src

check: lint typecheck test  ## Run lint + typecheck + test

# ── Demo ─────────────────────────────────────────────────────────────────────

seed:  ## Force-reseed via the running API (shortcut)
	curl -s -X POST http://localhost:8123/api/v1/demo/reset

reset: seed  ## Alias for seed

demo: db  ## Print demo instructions
	@echo ""
	@echo "  ══════════════════════════════════════════════════════════════"
	@echo "   Invoice Copilot — Demo"
	@echo "  ══════════════════════════════════════════════════════════════"
	@echo ""
	@echo "  1. In one terminal:    make run"
	@echo "     Then open:          http://localhost:8123"
	@echo "     (Click the 'Demo' / 'Live' toggle to switch between modes)"
	@echo ""
	@echo "  2. For a terminal walkthrough:"
	@echo "     In another terminal:  make walkthrough"
	@echo "     (Drives the API through the Observe → Decide → Audit story)"
	@echo ""
	@echo "  ══════════════════════════════════════════════════════════════"
	@echo ""

walkthrough:  ## Run the terminal demo walkthrough against the running server
	.venv/bin/python scripts/demo.py

# ── Docker ───────────────────────────────────────────────────────────────────

docker-build:  ## Build the production Docker image
	docker build -t invoice-copilot .
