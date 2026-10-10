"""Tests for CodeExecutor timeout, workspace checks, and temp-file cleanup."""

import os
import time
from pathlib import Path
from typing import List

import pytest

from mcp_python_toolbox.core.code_executor import (
    DEFAULT_TIMEOUT_SECONDS,
    MAX_TIMEOUT_SECONDS,
    TIMEOUT_ENV_VAR,
    CodeExecutor,
    resolve_timeout,
)
from mcp_python_toolbox.core.file_operations import FileOperations
from tests.conftest import make_venv_workspace

SLEEP_WITH_GRANDCHILD = """
import os
import subprocess
import sys
import time
from pathlib import Path

grandchild = subprocess.Popen(
    [sys.executable, "-c", "import time; time.sleep(120)"],
)
Path("pids.txt").write_text(
    "{0}\\n{1}\\n".format(os.getpid(), grandchild.pid)
)
print("CHILD_PID={0}".format(os.getpid()), flush=True)
print("GRANDCHILD_PID={0}".format(grandchild.pid), flush=True)
time.sleep(120)
"""


def _pid_is_running(pid: int) -> bool:
    """Return True if ``pid`` is still a live process."""
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def _wait_until_not_running(pid: int, timeout: float = 3.0) -> bool:
    """Wait until ``pid`` is gone, or until ``timeout`` elapses."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        if not _pid_is_running(pid):
            return True
        time.sleep(0.05)
    return not _pid_is_running(pid)


def _assert_temp_files_removed(paths: List[str]) -> None:
    assert paths, "expected CodeExecutor to create a temporary snippet file"
    leftover = [path for path in paths if os.path.exists(path)]
    assert leftover == [], "temporary snippet file was not removed: {}".format(leftover)


def test_default_timeout_is_thirty_seconds() -> None:
    assert DEFAULT_TIMEOUT_SECONDS == 30
    assert resolve_timeout() == 30


def test_per_call_timeout_is_capped() -> None:
    assert resolve_timeout(10_000) == MAX_TIMEOUT_SECONDS


def test_env_var_sets_default_timeout(monkeypatch: pytest.MonkeyPatch, workspace: Path) -> None:
    monkeypatch.setenv(TIMEOUT_ENV_VAR, "12")
    executor = CodeExecutor(workspace)
    assert executor.default_timeout == 12.0


def test_normal_run_returns_output(executor: CodeExecutor) -> None:
    result = executor.execute_code("print('hello-from-executor')")
    assert result["exit_code"] == 0
    assert "hello-from-executor" in result["stdout"]
    assert result.get("timed_out") is not True


def test_timeout_kills_child_and_grandchild(workspace: Path, executor: CodeExecutor) -> None:
    result = executor.execute_code(SLEEP_WITH_GRANDCHILD, timeout=2)
    assert result.get("timed_out") is True
    assert "timed out" in result["error"].lower()
    assert "2 second" in result["error"]

    pids_file = workspace / "pids.txt"
    assert pids_file.exists(), "partial work should be visible: {}".format(result)
    child_pid, grandchild_pid = [
        int(line) for line in pids_file.read_text().splitlines() if line.strip()
    ]
    assert _wait_until_not_running(child_pid), "child {} still running".format(child_pid)
    assert _wait_until_not_running(grandchild_pid), "grandchild {} still running".format(
        grandchild_pid
    )


def test_working_dir_outside_workspace_rejected(executor: CodeExecutor) -> None:
    with pytest.raises(ValueError, match="outside workspace"):
        executor.execute_code("print(1)", working_dir="..")


def test_symlink_escape_rejected(workspace: Path, executor: CodeExecutor) -> None:
    outside = workspace.parent / "outside_target"
    outside.mkdir()
    link = workspace / "link_out"
    link.symlink_to(outside)
    with pytest.raises(ValueError, match="outside workspace"):
        executor.execute_code("print(1)", working_dir="link_out")


def test_sibling_prefix_dir_rejected(tmp_path: Path) -> None:
    """``ws`` must not treat sibling ``ws-evil`` as inside the workspace."""
    ws = make_venv_workspace(tmp_path / "ws")
    evil = tmp_path / "ws-evil"
    evil.mkdir()
    (evil / "secret.txt").write_text("stolen")

    executor = CodeExecutor(ws)
    with pytest.raises(ValueError, match="outside workspace"):
        executor.execute_code("print(1)", working_dir="../ws-evil")
    with pytest.raises(ValueError, match="outside workspace"):
        executor.execute_code("print(1)", working_dir=str(evil))

    file_ops = FileOperations(ws)
    with pytest.raises(ValueError, match="outside workspace"):
        file_ops.read_file("../ws-evil/secret.txt")
    with pytest.raises(ValueError, match="outside workspace"):
        file_ops.read_file(str(evil / "secret.txt"))


def test_absolute_path_inside_workspace_accepted(workspace: Path, executor: CodeExecutor) -> None:
    inner = workspace / "inner"
    inner.mkdir()
    note = inner / "note.txt"
    note.write_text("inside")

    file_ops = FileOperations(workspace)
    assert file_ops.read_file(str(note)) == "inside"

    result = executor.execute_code("import os; print(os.getcwd())", working_dir=str(inner))
    assert result["exit_code"] == 0
    assert str(inner.resolve()) in result["stdout"]


def test_temp_file_removed_on_success(
    executor: CodeExecutor, recorded_temp_files: List[str]
) -> None:
    result = executor.execute_code("print('cleanup-ok')")
    assert result["exit_code"] == 0
    _assert_temp_files_removed(recorded_temp_files)


def test_temp_file_removed_on_timeout(
    executor: CodeExecutor, recorded_temp_files: List[str]
) -> None:
    result = executor.execute_code("import time; time.sleep(120)", timeout=1)
    assert result.get("timed_out") is True
    _assert_temp_files_removed(recorded_temp_files)


def test_temp_file_removed_on_invalid_working_dir(
    executor: CodeExecutor, recorded_temp_files: List[str]
) -> None:
    with pytest.raises(ValueError, match="outside workspace"):
        executor.execute_code("print(1)", working_dir="..")
    _assert_temp_files_removed(recorded_temp_files)


def test_temp_file_removed_when_venv_missing(
    tmp_path: Path, recorded_temp_files: List[str]
) -> None:
    bare = tmp_path / "bare_workspace"
    bare.mkdir()
    executor = CodeExecutor(bare)
    with pytest.raises(FileNotFoundError):
        executor.execute_code("print(1)")
    _assert_temp_files_removed(recorded_temp_files)
