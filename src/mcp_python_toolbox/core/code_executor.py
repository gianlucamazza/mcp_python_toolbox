"""Module for executing Python code via subprocess using the workspace virtual environment."""

import subprocess
from pathlib import Path
from typing import Dict, Any, Union, Optional
import tempfile
import os

class CodeExecutor:
    """Runs Python snippets with the workspace virtual environment interpreter.

    Snippets are written to a temporary file and executed with ``subprocess.run``
    using the project's ``.venv`` Python. This is not a sandbox: the child process
    has the same OS permissions as the server.

    Attributes:
        workspace_root (Path): The root directory of the workspace
        venv_path (Path): Path to the virtual environment directory
    """

    def __init__(self, workspace_root: Union[str, Path]):
        """Initialize the CodeExecutor.

        Args:
            workspace_root: Path to the workspace root directory, can be string or Path object
        """
        self.workspace_root = Path(workspace_root).resolve()
        self.venv_path = self.workspace_root / '.venv'

    def _get_python_path(self) -> Path:
        """Get the path to the Python executable in the virtual environment.

        Returns:
            Path: The path to the Python executable

        Raises:
            FileNotFoundError: If the Python executable is not found in the virtual environment
        """
        if os.name == 'nt':  # Windows
            python_path = self.venv_path / 'Scripts' / 'python.exe'
        else:  # Unix-like
            python_path = self.venv_path / 'bin' / 'python'
        
        if not python_path.exists():
            raise FileNotFoundError(f"Python executable not found in virtual environment: {python_path}")
        
        return python_path

    def execute_code(self, code: str, working_dir: Optional[str] = None) -> Dict[str, Any]:
        """Execute Python code and return the execution results.

        The code is written to a temporary file and executed with ``subprocess.run``
        using the virtual environment interpreter. The temporary file is cleaned up
        after execution. There is no sandbox, timeout, or working-directory check.

        Args:
            code: The Python code to execute as a string
            working_dir: Optional working directory for code execution. Defaults to workspace root

        Returns:
            Dict containing:
                - stdout: Standard output from the code execution
                - stderr: Standard error output from the code execution
                - exit_code: The exit code of the process (0 for success)

        Raises:
            FileNotFoundError: If the Python executable is not found
            subprocess.SubprocessError: If the code execution fails
        """
        # Create a temporary file to store the code
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as temp_file:
            temp_file.write(code)
            temp_file_path = temp_file.name

        try:
            # Get the Python executable from the virtual environment
            python_path = self._get_python_path()
            
            # Set up the working directory
            work_dir = Path(working_dir) if working_dir else self.workspace_root
            
            # Execute the code and capture output
            result = subprocess.run(
                [str(python_path), temp_file_path],
                cwd=str(work_dir),
                capture_output=True,
                text=True
            )
            
            return {
                'stdout': result.stdout,
                'stderr': result.stderr,
                'exit_code': result.returncode
            }
            
        finally:
            # Clean up the temporary file
            os.unlink(temp_file_path) 