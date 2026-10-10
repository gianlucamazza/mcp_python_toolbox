"""Shared fixtures for the execute_python test suite."""

import os
import sys
import tempfile
from pathlib import Path
from typing import List

import pytest

from mcp_python_toolbox.core.code_executor import CodeExecutor


def make_venv_workspace(root: Path) -> Path:
    """Create ``root`` with a ``.venv`` interpreter pointing at this Python."""
    root.mkdir(parents=True, exist_ok=True)
    if os.name == "nt":
        python_dir = root / ".venv" / "Scripts"
        target = python_dir / "python.exe"
    else:
        python_dir = root / ".venv" / "bin"
        target = python_dir / "python"
    python_dir.mkdir(parents=True, exist_ok=True)
    if not target.exists():
        os.symlink(sys.executable, target)
    return root


@pytest.fixture
def workspace(tmp_path: Path) -> Path:
    """Temporary workspace with a ``.venv`` interpreter pointing at this Python."""
    return make_venv_workspace(tmp_path / "workspace")


@pytest.fixture
def executor(workspace: Path) -> CodeExecutor:
    """CodeExecutor bound to the temporary workspace."""
    return CodeExecutor(workspace)


@pytest.fixture
def recorded_temp_files(monkeypatch: pytest.MonkeyPatch) -> List[str]:
    """Record temp ``.py`` paths created by ``CodeExecutor.execute_code``."""
    paths: List[str] = []
    original = tempfile.NamedTemporaryFile

    def wrapper(*args: object, **kwargs: object) -> object:
        handle = original(*args, **kwargs)
        paths.append(handle.name)
        return handle

    monkeypatch.setattr(
        "mcp_python_toolbox.core.code_executor.tempfile.NamedTemporaryFile",
        wrapper,
    )
    return paths
