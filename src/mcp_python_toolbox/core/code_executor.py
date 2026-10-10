"""Module for executing Python code via subprocess using the workspace virtual environment."""

import os
import signal
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, Optional, Union

from .file_operations import validate_workspace_path

DEFAULT_TIMEOUT_SECONDS = 30
MAX_TIMEOUT_SECONDS = 300
TIMEOUT_ENV_VAR = "MCP_PYTHON_EXECUTE_TIMEOUT"


def resolve_timeout(timeout: Optional[float] = None, default: Optional[float] = None) -> float:
    """Resolve an execution timeout and cap it at ``MAX_TIMEOUT_SECONDS``.

    Precedence when ``timeout`` is omitted: ``default``, then the
    ``MCP_PYTHON_EXECUTE_TIMEOUT`` environment variable, then 30 seconds.

    Args:
        timeout: Explicit timeout in seconds.
        default: Already-resolved fallback used when ``timeout`` is None.

    Returns:
        The timeout in seconds, never greater than ``MAX_TIMEOUT_SECONDS``.

    Raises:
        ValueError: If the provided timeout is non-numeric or not positive.
    """
    if timeout is not None:
        value = _parse_timeout(timeout)
    elif default is not None:
        value = _parse_timeout(default)
    else:
        env_value = os.environ.get(TIMEOUT_ENV_VAR)
        if env_value:
            value = _parse_timeout(env_value)
        else:
            return float(DEFAULT_TIMEOUT_SECONDS)
    return min(value, float(MAX_TIMEOUT_SECONDS))


def _parse_timeout(value: Union[str, int, float]) -> float:
    """Parse a positive timeout in seconds."""
    try:
        parsed = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("timeout must be a positive number of seconds") from exc
    if parsed <= 0:
        raise ValueError("timeout must be a positive number of seconds")
    return parsed


def _output_text(value: Any) -> str:
    """Normalize captured subprocess output to text."""
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)


def _kill_process_group(process: subprocess.Popen) -> None:
    """Kill a process and its descendants.

    POSIX children are started with ``start_new_session=True``, so the child
    PID is the process-group ID and ``os.killpg`` terminates the group.
    Windows has no ``killpg``; fall back to ``taskkill /T`` and then
    ``process.kill``.
    """
    if process.poll() is not None:
        return
    if os.name == "nt":
        try:
            subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(process.pid)],
                capture_output=True,
                check=False,
            )
        except OSError:
            try:
                process.kill()
            except OSError:
                pass
        return
    try:
        os.killpg(os.getpgid(process.pid), signal.SIGKILL)
    except (ProcessLookupError, PermissionError, OSError):
        try:
            process.kill()
        except OSError:
            pass


class CodeExecutor:  # pylint: disable=too-few-public-methods
    """Runs Python snippets with the workspace virtual environment interpreter.

    Snippets are written to a temporary file and executed in a new process
    group using the project's ``.venv`` Python. A timeout kills that process
    group. ``working_dir`` is validated with the same resolve-and-reject
    helper as ``FileOperations``. This is not a sandbox: the child process
    has the same OS permissions, filesystem access, and network access as
    the server.

    Attributes:
        workspace_root (Path): The root directory of the workspace
        venv_path (Path): Path to the virtual environment directory
        default_timeout (float): Default execution timeout in seconds
    """

    def __init__(self, workspace_root: Union[str, Path], timeout: Optional[float] = None) -> None:
        """Initialize the CodeExecutor.

        Args:
            workspace_root: Path to the workspace root directory, can be string or Path object
            timeout: Default execution timeout in seconds. If omitted, uses
                ``MCP_PYTHON_EXECUTE_TIMEOUT`` or ``DEFAULT_TIMEOUT_SECONDS``.
        """
        self.workspace_root = Path(workspace_root).resolve()
        self.venv_path = self.workspace_root / ".venv"
        self.default_timeout = resolve_timeout(timeout)

    def _get_python_path(self) -> Path:
        """Get the path to the Python executable in the virtual environment.

        Returns:
            Path: The path to the Python executable

        Raises:
            FileNotFoundError: If the Python executable is not found in the virtual environment
        """
        if os.name == "nt":  # Windows
            python_path = self.venv_path / "Scripts" / "python.exe"
        else:  # Unix-like
            python_path = self.venv_path / "bin" / "python"

        if not python_path.exists():
            raise FileNotFoundError(
                f"Python executable not found in virtual environment: {python_path}"
            )

        return python_path

    def execute_code(
        self,
        code: str,
        working_dir: Optional[str] = None,
        timeout: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Execute Python code and return the execution results.

        The code is written to a temporary file and executed with the virtual
        environment interpreter. The temporary file is always removed. Execution
        is still unsandboxed: the only guards are a timeout and a workspace
        check on ``working_dir``.

        Args:
            code: The Python code to execute as a string
            working_dir: Optional working directory. Defaults to the workspace
                root. Resolved with ``validate_workspace_path``; paths (including
                symlink escapes) outside the workspace are rejected.
            timeout: Optional per-call timeout in seconds, capped at
                ``MAX_TIMEOUT_SECONDS``. Defaults to the instance timeout.

        Returns:
            Dict containing:
                - stdout: Standard output from the code execution
                - stderr: Standard error output from the code execution
                - exit_code: The exit code of the process (0 for success)
                - timed_out / error: Present when the timeout expires, along
                  with any partial stdout/stderr

        Raises:
            FileNotFoundError: If the Python executable is not found
            ValueError: If ``working_dir`` is outside the workspace or timeout is invalid
            subprocess.SubprocessError: If the code execution fails
        """
        effective_timeout = (
            resolve_timeout(timeout) if timeout is not None else self.default_timeout
        )

        temp_file_path: Optional[str] = None
        try:
            with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as temp_file:
                temp_file.write(code)
                temp_file_path = temp_file.name

            if working_dir:
                work_dir = validate_workspace_path(self.workspace_root, working_dir)
            else:
                work_dir = self.workspace_root

            python_path = self._get_python_path()
            return self._run_snippet(python_path, temp_file_path, work_dir, effective_timeout)
        finally:
            if temp_file_path is not None:
                try:
                    os.unlink(temp_file_path)
                except OSError:
                    pass

    def _run_snippet(
        self,
        python_path: Path,
        temp_file_path: str,
        work_dir: Path,
        timeout: float,
    ) -> Dict[str, Any]:
        """Run the temp snippet in a new process group and enforce the timeout."""
        popen_kwargs: Dict[str, Any] = {
            "cwd": str(work_dir),
            "stdout": subprocess.PIPE,
            "stderr": subprocess.PIPE,
            "text": True,
        }
        if os.name == "nt":
            popen_kwargs["creationflags"] = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
        else:
            popen_kwargs["start_new_session"] = True

        process = subprocess.Popen(  # pylint: disable=consider-using-with
            [str(python_path), temp_file_path],
            **popen_kwargs,
        )
        try:
            stdout, stderr = process.communicate(timeout=timeout)
            return {
                "stdout": stdout,
                "stderr": stderr,
                "exit_code": process.returncode,
            }
        except subprocess.TimeoutExpired as exc:
            _kill_process_group(process)
            extra_out = ""
            extra_err = ""
            try:
                extra_out, extra_err = process.communicate(timeout=1)
            except (subprocess.TimeoutExpired, OSError):
                try:
                    process.kill()
                except OSError:
                    pass
            timeout_display = int(timeout) if timeout == int(timeout) else timeout
            return {
                "stdout": _output_text(exc.stdout) + _output_text(extra_out),
                "stderr": _output_text(exc.stderr) + _output_text(extra_err),
                "exit_code": process.returncode,
                "timed_out": True,
                "error": f"Execution timed out after {timeout_display} seconds",
            }
