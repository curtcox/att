"""Deploy API schemas."""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel


class DeployRunRequest(BaseModel):
    """Deploy run payload."""

    config_path: Path
