"""Tests for the CodeAnalyzer linting behaviour."""

from pathlib import Path

import pytest

from mcp_python_toolbox.core.code_analyzer import CodeAnalyzer


@pytest.fixture
def analyzer(tmp_path: Path) -> CodeAnalyzer:
    """Return a CodeAnalyzer rooted at a temporary workspace."""
    return CodeAnalyzer(tmp_path)


def test_lint_missing_file(analyzer: CodeAnalyzer, tmp_path: Path) -> None:
    """Linting a non-existent file reports an error instead of raising."""
    issues = analyzer.lint_code(tmp_path / "does_not_exist.py")
    assert len(issues) == 1
    assert "File not found" in issues[0]["message"]
    assert issues[0]["type"] == "error"


def test_lint_clean_file(analyzer: CodeAnalyzer, tmp_path: Path) -> None:
    """A well-formed module produces no lint issues."""
    module = tmp_path / "clean.py"
    module.write_text(
        '"""A clean module."""\n\n\n'
        "def add(first: int, second: int) -> int:\n"
        '    """Return the sum of two integers."""\n'
        "    return first + second\n"
    )
    issues = analyzer.lint_code(module)
    assert issues == []


def test_lint_reflects_file_changes(analyzer: CodeAnalyzer, tmp_path: Path) -> None:
    """Re-linting after a fix must return fresh results (regression: issue #2).

    The previous in-process pylint invocation shared an ``astroid`` module
    cache across calls, so a file that was linted, then fixed, then linted
    again could return stale results. Running pylint in a subprocess gives
    each call a clean cache; this test guards that behaviour.
    """
    module = tmp_path / "sample.py"

    # First version has an unused import, which pylint flags as W0611.
    module.write_text(
        '"""Sample module."""\n'
        "import os\n\n\n"
        "def greet() -> str:\n"
        '    """Return a greeting."""\n'
        '    return "hello"\n'
    )
    first = analyzer.lint_code(module)
    assert any("W0611" in issue["message"] for issue in first), first

    # Fix the file by removing the unused import.
    module.write_text(
        '"""Sample module."""\n\n\n'
        "def greet() -> str:\n"
        '    """Return a greeting."""\n'
        '    return "hello"\n'
    )
    second = analyzer.lint_code(module)
    assert not any("W0611" in issue["message"] for issue in second), second


def test_lint_issue_schema(analyzer: CodeAnalyzer, tmp_path: Path) -> None:
    """Each issue exposes the documented keys with string values."""
    module = tmp_path / "bad.py"
    module.write_text("import os\n")  # unused import + missing docstring
    issues = analyzer.lint_code(module)
    assert issues
    for issue in issues:
        assert set(issue) == {"path", "line", "type", "message"}
        assert isinstance(issue["line"], str)
        assert isinstance(issue["type"], str)
