#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

DEFAULT_SECTIONS = (
    "## Snapshot",
    "## Active Next Slice (Recommended)",
    "## Resume Checklist",
    "## Working Agreement",
)


def _read_lines(path: Path) -> list[str]:
    return path.read_text(encoding="utf-8").splitlines()


def _write_lines(path: Path, lines: list[str]) -> None:
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _extract_sections(lines: list[str], section_titles: tuple[str, ...]) -> str:
    sections: list[str] = []
    line_count = len(lines)

    for title in section_titles:
        start = next((index for index, line in enumerate(lines) if line == title), None)
        if start is None:
            continue

        end = line_count
        for index in range(start + 1, line_count):
            if lines[index].startswith("## "):
                end = index
                break

        section = "\n".join(lines[start:end]).rstrip()
        if section:
            sections.append(section)

    return "\n\n".join(sections) + ("\n" if sections else "")


def _recent_delivered_insert_index(lines: list[str]) -> int:
    recent_idx = next(
        (index for index, line in enumerate(lines) if line == "## Recent Delivered Work"),
        None,
    )
    if recent_idx is None:
        raise ValueError("Missing '## Recent Delivered Work' heading")

    cursor = recent_idx + 1
    while cursor < len(lines) and lines[cursor].strip() == "":
        cursor += 1

    if cursor < len(lines) and lines[cursor] == "- See done for older completed slices:":
        cursor += 1
        while cursor < len(lines) and lines[cursor].startswith("  - "):
            cursor += 1
        while cursor < len(lines) and lines[cursor].strip() == "":
            cursor += 1

    return cursor


def _prepend_recent(path: Path, summary: str, details: tuple[str, ...]) -> None:
    lines = _read_lines(path)
    insert_at = _recent_delivered_insert_index(lines)

    summary_line = summary.strip()
    if not summary_line.startswith("- "):
        summary_line = f"- {summary_line}"

    block = [summary_line]
    for detail in details:
        detail_line = detail.strip()
        if detail_line.startswith("- "):
            detail_line = detail_line[2:].strip()
        block.append(f"  - {detail_line}")
    block.append("")

    updated = lines[:insert_at] + block + lines[insert_at:]
    _write_lines(path, updated)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Handoff productivity helper")
    subparsers = parser.add_subparsers(dest="command", required=True)

    quickview = subparsers.add_parser(
        "quickview",
        help="Print key handoff sections for quick context",
    )
    quickview.add_argument(
        "--file",
        default="todo/NEXT_MACHINE_HANDOFF.md",
        help="Handoff file path",
    )

    prepend_recent = subparsers.add_parser(
        "prepend-recent",
        help="Prepend a new delivered-work bullet under Recent Delivered Work",
    )
    prepend_recent.add_argument(
        "--file",
        default="todo/NEXT_MACHINE_HANDOFF.md",
        help="Handoff file path",
    )
    prepend_recent.add_argument("--summary", required=True, help="Top-level delivered summary")
    prepend_recent.add_argument(
        "--detail",
        action="append",
        default=[],
        help="Detail bullet line (repeat for multiple)",
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    path = Path(args.file)

    if args.command == "quickview":
        content = _extract_sections(_read_lines(path), DEFAULT_SECTIONS)
        sys.stdout.write(content)
        return 0

    if args.command == "prepend-recent":
        _prepend_recent(path, args.summary, tuple(args.detail))
        return 0

    raise ValueError(f"Unsupported command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
