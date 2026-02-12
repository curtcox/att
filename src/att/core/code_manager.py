"""Code and file operations for a project."""

from __future__ import annotations

import difflib
from pathlib import Path


class CodeManager:
    """Constrained file operations within project boundaries."""

    def list_files(self, project_path: Path) -> list[Path]:
        return sorted(path for path in project_path.rglob("*") if path.is_file())

    def read_file(self, project_path: Path, rel_path: str) -> str:
        path = self._resolve(project_path, rel_path)
        return path.read_text(encoding="utf-8")

    def write_file(self, project_path: Path, rel_path: str, content: str) -> None:
        path = self._resolve(project_path, rel_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def search(self, project_path: Path, pattern: str) -> list[Path]:
        matches: list[Path] = []
        for file_path in self.list_files(project_path):
            try:
                if pattern in file_path.read_text(encoding="utf-8"):
                    matches.append(file_path)
            except UnicodeDecodeError:
                continue
        return matches

    def diff(self, original: str, updated: str, *, from_name: str, to_name: str) -> str:
        return "\n".join(
            difflib.unified_diff(
                original.splitlines(),
                updated.splitlines(),
                fromfile=from_name,
                tofile=to_name,
                lineterm="",
            )
        )

    @staticmethod
    def _resolve(project_path: Path, rel_path: str) -> Path:
        root = project_path.resolve()
        candidate = (root / rel_path).resolve()
        if root not in candidate.parents and candidate != root:
            msg = f"Path escapes project root: {rel_path}"
            raise ValueError(msg)
        return candidate
