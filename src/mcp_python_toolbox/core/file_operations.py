"""Module for file operations scoped to a workspace directory."""

import os
from pathlib import Path
from typing import Union, List, Dict, Optional, Any


def validate_workspace_path(workspace_root: Union[str, Path], path: Union[str, Path]) -> Path:
    """Resolve a path and reject it if it falls outside the workspace root.

    ``workspace_root`` is resolved first. ``path`` is joined to that root
    (absolute ``path`` values replace the root, per ``pathlib``) and then
    resolved, which follows symlinks. Containment is ``resolved == root`` or
    ``root in resolved.parents``, not a string-prefix check (so ``/tmp/ws``
    does not accept ``/tmp/ws-evil``).

    Args:
        workspace_root: Workspace root directory (resolved inside this helper).
        path: Path to validate, relative to the workspace root or absolute.

    Returns:
        Path: The resolved absolute path.

    Raises:
        ValueError: If the path resolves to a location outside the workspace root.
    """
    root = Path(workspace_root).resolve()
    resolved_path = (root / Path(path)).resolve()
    if resolved_path != root and root not in resolved_path.parents:
        raise ValueError(f"Path {path} is outside workspace root")
    return resolved_path


class FileOperations:
    """Manages file operations within a workspace directory.

    Paths are resolved and rejected if they fall outside the workspace root.
    That check applies only to these file helpers; it is not a sandbox.
    Includes:
    - Reading and writing files
    - Creating directories and deleting files
    - Listing directory contents
    - Path validation

    Attributes:
        workspace_root (Path): The root directory of the workspace
    """

    def __init__(self, workspace_root: Union[str, Path]):
        """Initialize the FileOperations manager.

        Args:
            workspace_root: Path to the workspace root directory

        Raises:
            ValueError: If the workspace root does not exist
        """
        self.workspace_root = Path(workspace_root).resolve()
        if not self.workspace_root.exists():
            raise ValueError(f"Workspace root does not exist: {self.workspace_root}")

    def _validate_path(self, path: Union[str, Path]) -> Path:
        """Validate and resolve a path within the workspace.

        Ensures that the given path resolves to a location within the workspace root
        directory. Paths outside the workspace raise ``ValueError``.

        Args:
            path: The path to validate, relative to workspace root

        Returns:
            Path: The resolved absolute path

        Raises:
            ValueError: If the path resolves to a location outside the workspace root
        """
        return validate_workspace_path(self.workspace_root, path)

    def read_file(
        self,
        path: Union[str, Path],
        start_line: Optional[int] = None,
        end_line: Optional[int] = None,
    ) -> str:
        """Read contents of a file, optionally between specific lines.

        Args:
            path: Path to the file to read, relative to workspace root
            start_line: Optional line number to start reading from (1-based)
            end_line: Optional line number to end reading at (inclusive)

        Returns:
            str: The contents of the file or specified lines

        Raises:
            FileNotFoundError: If the file does not exist
            ValueError: If the path is outside workspace root
            IndexError: If line numbers are out of range
        """
        file_path = self._validate_path(path)
        if not file_path.is_file():
            raise FileNotFoundError(f"File not found: {path}")

        with open(file_path, "r", encoding="utf-8") as f:
            if start_line is None and end_line is None:
                return f.read()

            lines = f.readlines()
            start_idx = (start_line - 1) if start_line else 0
            end_idx = end_line if end_line else len(lines)
            return "".join(lines[start_idx:end_idx])

    def write_file(self, path: Union[str, Path], content: str, mode: str = "w") -> None:
        """Write content to a file.

        Creates parent directories if they don't exist. The file will be created
        if it doesn't exist or overwritten if it does (unless append mode is used).

        Args:
            path: Path to the file to write, relative to workspace root
            content: The content to write to the file
            mode: The file opening mode ('w' for write, 'a' for append)

        Raises:
            ValueError: If the path is outside workspace root
            IOError: If unable to write to the file
        """
        file_path = self._validate_path(path)
        os.makedirs(file_path.parent, exist_ok=True)

        with open(file_path, mode, encoding="utf-8") as f:
            f.write(content)

    def delete_file(self, path: Union[str, Path]) -> None:
        """Delete a file.

        Args:
            path: Path to the file to delete, relative to workspace root

        Raises:
            FileNotFoundError: If the file does not exist
            ValueError: If the path is outside workspace root
            OSError: If unable to delete the file
        """
        file_path = self._validate_path(path)
        if file_path.is_file():
            os.remove(file_path)
        else:
            raise FileNotFoundError(f"File not found: {path}")

    def list_directory(self, path: Union[str, Path] = ".") -> List[Dict[str, Any]]:
        """List contents of a directory with metadata.

        Args:
            path: Path to the directory to list, relative to workspace root.
                 Defaults to workspace root.

        Returns:
            List of dictionaries containing:
                - name: Name of the item
                - type: 'file' or 'directory'
                - size: Size in bytes
                - modified: Modification timestamp
                - path: Path relative to workspace root

        Raises:
            NotADirectoryError: If the path is not a directory
            ValueError: If the path is outside workspace root
        """
        dir_path = self._validate_path(path)
        if not dir_path.is_dir():
            raise NotADirectoryError(f"Not a directory: {path}")

        contents = []
        for item in dir_path.iterdir():
            stat = item.stat()
            contents.append(
                {
                    "name": item.name,
                    "type": "file" if item.is_file() else "directory",
                    "size": stat.st_size,
                    "modified": stat.st_mtime,
                    "path": str(item.relative_to(self.workspace_root)),
                }
            )
        return contents

    def create_directory(self, path: Union[str, Path]) -> None:
        """Create a directory and any necessary parent directories.

        Args:
            path: Path to the directory to create, relative to workspace root

        Raises:
            ValueError: If the path is outside workspace root
            OSError: If unable to create the directory
        """
        dir_path = self._validate_path(path)
        os.makedirs(dir_path, exist_ok=True)
