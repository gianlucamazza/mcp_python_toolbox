from typing import Dict, Any, Optional, List, Union
from pathlib import Path
from mcp.server.fastmcp.server import FastMCP
from .core.file_operations import FileOperations
from .core.code_analyzer import CodeAnalyzer, CodeAnalysis
from .core.project_manager import ProjectManager
from .core.code_executor import CodeExecutor


class PythonToolboxServer(FastMCP):
    def __init__(self, workspace_root: Union[str, Path], execute_timeout: Optional[float] = None):
        super().__init__()
        self.workspace_root = Path(workspace_root).resolve()
        self.file_ops = FileOperations(self.workspace_root)
        self.code_analyzer = CodeAnalyzer(self.workspace_root)
        self.project_manager = ProjectManager(self.workspace_root)
        self.code_executor = CodeExecutor(self.workspace_root, timeout=execute_timeout)

    def setup(self) -> None:
        """Register all tools with the server."""
        # File operations
        self.add_tool(self.read_file, name="read_file", description="Read the contents of a file")
        self.add_tool(self.write_file, name="write_file", description="Write content to a file")
        self.add_tool(self.delete_file, name="delete_file", description="Delete a file")
        self.add_tool(
            self.list_directory, name="list_directory", description="List contents of a directory"
        )

        # Code analysis and execution
        self.add_tool(
            self.analyze_python_file,
            name="analyze_python_file",
            description="Analyze the structure of a Python file",
        )
        self.add_tool(
            self.format_code,
            name="format_code",
            description="Format Python code according to style guidelines",
        )
        self.add_tool(self.lint_code, name="lint_code", description="Run linting on Python code")
        self.add_tool(self.execute_python, name="execute_python", description="Execute Python code")

        # Project management
        self.add_tool(
            self.create_virtual_environment,
            name="create_venv",
            description="Create a virtual environment",
        )
        self.add_tool(
            self.install_dependencies,
            name="install_dependencies",
            description="Install project dependencies",
        )
        self.add_tool(
            self.get_installed_packages, name="list_packages", description="List installed packages"
        )
        self.add_tool(
            self.check_dependency_conflicts,
            name="check_conflicts",
            description="Check for dependency conflicts",
        )

    # File operations handlers
    async def read_file(
        self, path: str, start_line: Optional[int] = None, end_line: Optional[int] = None
    ) -> str:
        return self.file_ops.read_file(path, start_line, end_line)

    async def write_file(self, path: str, content: str, mode: str = "w") -> None:
        self.file_ops.write_file(path, content, mode)

    async def delete_file(self, path: str) -> None:
        self.file_ops.delete_file(path)

    async def list_directory(self, path: str = ".") -> List[Dict[str, Any]]:
        return self.file_ops.list_directory(path)

    # Code analysis handlers
    async def analyze_python_file(self, path: str) -> CodeAnalysis:
        return self.code_analyzer.parse_python_file(path)  # CodeAnalysis is already a TypedDict

    async def format_code(self, code: str, style: str = "black") -> str:
        return self.code_analyzer.format_code(code, style)

    async def lint_code(self, path: str) -> List[Dict[str, Any]]:
        return self.code_analyzer.lint_code(path)

    # Project management handlers
    async def create_virtual_environment(self) -> None:
        self.project_manager.create_virtual_environment()

    async def install_dependencies(self, requirements_file: Optional[str] = None) -> None:
        self.project_manager.install_dependencies(requirements_file)

    async def get_installed_packages(self) -> List[Dict[str, str]]:
        return self.project_manager.get_installed_packages()

    async def check_dependency_conflicts(self) -> List[Dict[str, Any]]:
        return self.project_manager.check_dependency_conflicts()

    async def execute_python(
        self,
        code: str,
        working_dir: Optional[str] = None,
        timeout: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Execute Python code and return the result."""
        return self.code_executor.execute_code(code, working_dir, timeout)
