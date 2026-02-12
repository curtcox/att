"""Runtime API schemas."""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel


class RuntimeStartRequest(BaseModel):
    """Start runtime payload."""

    config_path: Path
