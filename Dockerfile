# Invoice Copilot — multi-stage production image
#
# Stage 1: build the Vite/React frontend (node:22-slim)
# Stage 2: install the FastAPI backend on python:3.12-slim and copy in the
#           built static assets; uvicorn serves the API *and* the SPA from one
#           process via IC_STATIC_DIR.
#
# The app binds to $PORT (Render injects this; default 8000).

# ---- build frontend ----
FROM node:22-slim AS frontend
WORKDIR /fe
COPY frontend/package.json frontend/package-lock.json ./
RUN npm install
COPY frontend/ ./
RUN npm run build

# ---- backend + serve built frontend ----
FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 IC_STATIC_DIR=/app/static
WORKDIR /app
COPY backend/pyproject.toml ./
COPY backend/src ./src
COPY backend/scripts ./scripts
COPY backend/alembic.ini ./
COPY backend/migrations ./migrations
RUN pip install .
COPY --from=frontend /fe/dist /app/static
# Ship the sample invoice documents inside the image so the /file preview route
# works without a bind-mount in production (S3 migration TBD).
COPY backend/data/sample_invoices /app/data/sample_invoices
# Ship the cached extraction corpus so the demo seeds at boot (no LLM call).
# Without this the seeder finds no corpus and the app comes up with an empty demo.
COPY backend/data/corpus_unique.json /app/data/corpus_unique.json
EXPOSE 8000
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
