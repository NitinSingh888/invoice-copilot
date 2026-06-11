# Invoice Copilot — developer entry points (split monorepo: backend/ + frontend/)
# Run `make help` to see all targets (the default).

.PHONY: help up down logs rebuild install db db-down backend frontend dev test lint typecheck fe-build check docker-build

help:  ## Show this help message
	@echo ""
	@echo "  Invoice Copilot — make targets"
	@echo ""
	@echo "  Run everything in Docker (recommended — no local Python/Node needed)"
	@echo "    make up             Postgres + backend + frontend (hot-reload) → http://localhost:5173"
	@echo "    make down           Stop all containers"
	@echo "    make logs           Tail logs from all services"
	@echo "    make rebuild        Rebuild images and restart (after dependency changes)"
	@echo ""
	@echo "  Run natively (optional fast path — needs local Python + Node)"
	@echo "    make install       Install backend .venv + frontend node_modules"
	@echo "    make db            Start just Postgres"
	@echo "    make backend       Start API server on :8123 with --reload"
	@echo "    make frontend      Start Vite dev server on :5173"
	@echo ""
	@echo "  Quality"
	@echo "    make test          Run pytest (requires make db)"
	@echo "    make lint          Ruff lint check on src + tests"
	@echo "    make typecheck     Mypy type check on src"
	@echo "    make fe-build      Production build of the frontend (frontend/dist)"
	@echo "    make check         lint + typecheck + test + fe-build"
	@echo ""
	@echo "  Docker"
	@echo "    make docker-build  Build the production Docker image (invoice-copilot)"
	@echo ""

# ── Run everything in Docker (recommended) ───────────────────────────────────

up:  ## Start Postgres + backend + frontend (containerised, hot-reload)
	docker compose up --build

down:  ## Stop and remove all containers
	docker compose down

logs:  ## Tail logs from all services
	docker compose logs -f

rebuild:  ## Rebuild images from scratch and restart
	docker compose up -d --build --force-recreate

# ── Native setup (optional) ──────────────────────────────────────────────────

install:  ## Create backend .venv + install deps; install frontend node_modules
	cd backend && python3 -m venv .venv && .venv/bin/pip install -e ".[dev]"
	cd frontend && npm install

# ── Database ─────────────────────────────────────────────────────────────────

db:  ## Start Postgres container and wait until healthy
	docker compose up -d postgres
	@echo "Waiting for Postgres to be healthy..."
	@until docker compose exec -T postgres pg_isready -U copilot -q; do sleep 1; done
	@echo "Postgres is ready."

db-down:  ## Stop and remove the Postgres container
	docker compose down

# ── Development servers ───────────────────────────────────────────────────────
# NOTE: reads backend/.env for IC_DATABASE_URL etc.

backend:  ## Start the FastAPI backend on :8123 with hot-reload (requires make db)
	cd backend && PYTHONPATH=src .venv/bin/uvicorn app.main:app --port 8123 --reload

frontend:  ## Start the Vite dev server on :5173 (proxies /api → http://localhost:8123)
	cd frontend && npm run dev

dev:  ## Print instructions for running the full dev stack
	@echo ""
	@echo "  ══════════════════════════════════════════════════════════════"
	@echo "   Invoice Copilot — Dev Setup"
	@echo "  ══════════════════════════════════════════════════════════════"
	@echo ""
	@echo "  Terminal 1:  make db"
	@echo "  Terminal 2:  make backend    (API on http://localhost:8123)"
	@echo "  Terminal 3:  make frontend   (UI  on http://localhost:5173)"
	@echo ""
	@echo "  Then open:   http://localhost:5173"
	@echo ""
	@echo "  ══════════════════════════════════════════════════════════════"
	@echo ""

# ── Quality ──────────────────────────────────────────────────────────────────

test:  ## Run pytest (requires make db)
	cd backend && .venv/bin/pytest -q

lint:  ## Ruff lint check on src + tests
	cd backend && .venv/bin/ruff check src tests

typecheck:  ## Mypy type check on src
	cd backend && .venv/bin/mypy src

fe-build:  ## Production build of the Vite frontend → frontend/dist
	cd frontend && npm run build

check: lint typecheck test fe-build  ## Run lint + typecheck + test + fe-build

# ── Docker ───────────────────────────────────────────────────────────────────

docker-build:  ## Build the production Docker image (multi-stage: frontend + backend)
	docker build -t invoice-copilot .
