from pathlib import Path

import pytest

from att.core.code_manager import CodeManager


def test_write_read_search_and_diff(tmp_path: Path) -> None:
    manager = CodeManager()
    manager.write_file(tmp_path, "a/test.txt", "hello")

    assert manager.read_file(tmp_path, "a/test.txt") == "hello"
    assert manager.search(tmp_path, "hello") == [tmp_path / "a/test.txt"]

    diff = manager.diff("hello", "hello world", from_name="a/test.txt", to_name="b/test.txt")
    assert "hello world" in diff


def test_reject_path_escape(tmp_path: Path) -> None:
    manager = CodeManager()
    with pytest.raises(ValueError):
        manager.write_file(tmp_path, "../escape.txt", "x")
