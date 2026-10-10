"""
Main entry point for the MCP Python Toolbox server.
"""

import os
import argparse
from pathlib import Path
from .core.code_executor import (
    DEFAULT_TIMEOUT_SECONDS,
    MAX_TIMEOUT_SECONDS,
    TIMEOUT_ENV_VAR,
)
from .server import PythonToolboxServer


def main() -> None:
    """Run the MCP Python Toolbox server."""
    parser = argparse.ArgumentParser(description="MCP Python Toolbox Server")
    parser.add_argument(
        "--workspace",
        type=str,
        default=os.getcwd(),
        help="Path to the workspace root directory (default: current directory)",
    )
    parser.add_argument(
        "--execute-timeout",
        type=float,
        default=None,
        help=(
            "Default timeout in seconds for execute_python "
            f"(default: {DEFAULT_TIMEOUT_SECONDS}, env: {TIMEOUT_ENV_VAR}, "
            f"max: {MAX_TIMEOUT_SECONDS})"
        ),
    )

    args = parser.parse_args()
    workspace_root = Path(args.workspace).resolve()

    server = PythonToolboxServer(workspace_root, execute_timeout=args.execute_timeout)
    server.setup()
    server.run()


if __name__ == "__main__":
    main()
