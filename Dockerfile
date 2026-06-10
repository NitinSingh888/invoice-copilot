# Invoice Copilot — production image
#
# Single-stage build on python:3.12-slim.
# psycopg[binary] ships its own libpq, so no extra OS packages are needed.
#
# The app binds to $PORT (Render injects this automatically; default 8000).
# The src-layout package ("app") is installed as a proper package via
# `pip install .` so `import app` works without PYTHONPATH tricks.

FROM python:3.12-slim

# Reduce noise and keep the layer cache clean.
ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Copy only the files needed to install the package first (better layer caching).
COPY pyproject.toml ./

# Copy source tree, static web assets and the demo script.
COPY src/ ./src/
COPY web/ ./web/
COPY scripts/ ./scripts/

# Install the package (non-editable, no dev extras).
# pip finds packages via [tool.setuptools.packages.find] where = ["src"].
RUN pip install .

# Expose the default Render port.
EXPOSE 8000

# Use sh -c so $PORT is expanded at runtime (Render sets it; default 8000).
# `web/` is served as static files relative to the CWD (/app), matching
# the StaticFiles(directory="web") mount in app.main.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
