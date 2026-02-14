from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def _script_path() -> Path:
    return Path(__file__).resolve().parents[2] / "scripts" / "handoff_helper.py"


def test_quickview_prints_expected_sections(tmp_path: Path) -> None:
    handoff = tmp_path / "NEXT_MACHINE_HANDOFF.md"
    handoff.write_text(
        "\n".join(
            (
                "# Next Machine Handoff",
                "",
                "## Snapshot",
                "- Date: `2026-02-14`",
                "",
                "## Active Next Slice (Recommended)",
                "1. Do something",
                "",
                "## Resume Checklist",
                "1. Validate things",
                "",
                "## Working Agreement",
                "- Keep edits small.",
            )
        ),
        encoding="utf-8",
    )

    completed = subprocess.run(
        [
            sys.executable,
            str(_script_path()),
            "quickview",
            "--file",
            str(handoff),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    stdout = completed.stdout
    assert "## Snapshot" in stdout
    assert "## Active Next Slice (Recommended)" in stdout
    assert "## Resume Checklist" in stdout
    assert "## Working Agreement" in stdout


def test_prepend_recent_delivered_inserts_block_after_archive_pointer(tmp_path: Path) -> None:
    handoff = tmp_path / "NEXT_MACHINE_HANDOFF.md"
    handoff.write_text(
        "\n".join(
            (
                "# Next Machine Handoff",
                "",
                "## Recent Delivered Work",
                "- See done for older completed slices:",
                "  - `/tmp/archive.md`",
                "",
                "- Existing bullet:",
                "  - existing detail",
                "",
                "## Active Next Slice (Recommended)",
                "1. Keep going",
            )
        ),
        encoding="utf-8",
    )

    subprocess.run(
        [
            sys.executable,
            str(_script_path()),
            "prepend-recent",
            "--file",
            str(handoff),
            "--summary",
            "Completed helper automation:",
            "--detail",
            "added command A",
            "--detail",
            "added command B",
        ],
        check=True,
    )

    content = handoff.read_text(encoding="utf-8")
    assert "- Completed helper automation:" in content
    assert "  - added command A" in content
    assert "  - added command B" in content

    expected_order = [
        "- See done for older completed slices:",
        "  - `/tmp/archive.md`",
        "",
        "- Completed helper automation:",
        "  - added command A",
        "  - added command B",
        "",
        "- Existing bullet:",
    ]
    cursor = -1
    for token in expected_order:
        next_cursor = content.find(token, cursor + 1)
        assert next_cursor > cursor
        cursor = next_cursor
