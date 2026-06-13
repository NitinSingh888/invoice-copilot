"""Filesystem path resolution that works across source and installed layouts.

The bundled ``data/`` directory (seed corpus, sample invoice documents, uploads)
lives next to the project root. But the *code* runs from different places:

* source checkout / docker-compose: ``__file__`` is ``<root>/src/app/core/paths.py``,
  so the data dir is ``<root>/data``.
* production image (``pip install .``): the package is installed under
  ``site-packages`` while the Dockerfile copies ``data/`` to the WORKDIR
  (``/app/data``).

A fixed ``Path(__file__).parents[N]`` guess is therefore wrong in one of the two
environments. We instead probe candidate locations and return the first that
actually exists, so the same code is correct whether run from source or installed.
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path


@lru_cache
def project_data_dir() -> Path:
    """Return the bundled ``data/`` directory, resolved for the current layout."""
    candidates: list[Path] = []
    env = os.environ.get("IC_DATA_DIR")
    if env:
        candidates.append(Path(env))
    # Source layout: this file is <root>/src/app/core/paths.py -> parents[3] = <root>.
    candidates.append(Path(__file__).resolve().parents[3] / "data")
    # Container WORKDIR (e.g. /app) where the Dockerfile copies data/.
    candidates.append(Path.cwd() / "data")

    for c in candidates:
        if c.is_dir():
            return c
    # Nothing found — return the most likely production path; callers log/warn.
    return Path.cwd() / "data"
