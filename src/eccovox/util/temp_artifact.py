"""Temporary artifact management for engine interoperability."""

from __future__ import annotations

from contextlib import contextmanager
from collections.abc import Iterator
from pathlib import Path
import tempfile


@contextmanager
def temporary_artifact(temp_dir: Path, suffix: str = "") -> Iterator[Path]:
    """Create and clean a temporary file under the configured EccoVox temp directory."""

    temp_dir.mkdir(parents=True, exist_ok=True)
    handle = tempfile.NamedTemporaryFile(dir=temp_dir, suffix=suffix, delete=False)
    path = Path(handle.name)
    handle.close()
    try:
        yield path
    finally:
        path.unlink(missing_ok=True)
