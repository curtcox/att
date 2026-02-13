from pathlib import Path

MAX_NEXT_MACHINE_HANDOFF_LINES = 250


def test_next_machine_handoff_size_guardrail() -> None:
    workspace_root = Path(__file__).resolve().parents[2]
    handoff_path = workspace_root / "todo" / "NEXT_MACHINE_HANDOFF.md"

    line_count = len(handoff_path.read_text(encoding="utf-8").splitlines())

    assert line_count <= MAX_NEXT_MACHINE_HANDOFF_LINES, (
        f"{handoff_path} has {line_count} lines; limit is "
        f"{MAX_NEXT_MACHINE_HANDOFF_LINES}. Archive older completed detail under "
        "done/ and keep only active context in NEXT_MACHINE_HANDOFF.md."
    )
