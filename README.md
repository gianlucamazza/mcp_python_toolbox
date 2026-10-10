# MCP Python Toolbox

A local [Model Context Protocol](https://modelcontextprotocol.io) (stdio) server that exposes Python workspace tools to an MCP client such as Claude Desktop: read/write files, analyze/format/lint Python, manage a project `.venv`, and run code.

It is not published to PyPI. It does not sandbox execution. See [Security](#security).

## Overview

Start the server against a workspace directory. A connected MCP client can then:

- Read, write, and delete files, and list directories, inside that workspace
- Analyze, format, and lint Python code
- Create a virtual environment and install dependencies
- Execute Python snippets on the host

## Features

### File Operations (`FileOperations`)
- File tools scoped to a workspace directory
- Paths are resolved and rejected if they fall outside the workspace root
- Read and write files with line-specific operations (`write_file` creates parent directories)
- Delete files (`delete_file` does not remove directories)
- List directory contents with metadata (size, type, modification time)
- `create_directory` exists on the class but is not registered as an MCP tool

### Code Analysis (`CodeAnalyzer`)
- Parse and analyze Python code structure using AST
- Extract detailed information about:
  - Import statements and their aliases
  - Function definitions with arguments and decorators
  - Class definitions with base classes and methods
  - Global variable assignments
- Format code using:
  - Black (default)
  - PEP8 (using autopep8)
- Lint with Pylint (JSON output, 30s subprocess timeout)

### Project Management (`ProjectManager`)
- Create a workspace `.venv` (`venv.create`, with pip)
- Install dependencies into that `.venv` via `pip`:
  - From `requirements.txt`
  - From `pyproject.toml` `[project.dependencies]`
- `update_package` / `create_requirements_file` on the class use the `.venv` interpreter (`pip install --upgrade` / `pip freeze`)
- `list_packages` and `check_conflicts` inspect packages visible to the **running server interpreter** (`importlib.metadata`), not the workspace `.venv`

### Code Execution (`CodeExecutor`)
- Write the snippet to a temp file and run it with `subprocess`
- Uses the workspace `.venv` Python if that interpreter exists
- Capture stdout, stderr, and exit codes
- Optional working directory (not checked against the workspace root)
- No timeout, resource limits, or isolation

## Security

There is no sandbox. The server and every tool run with the same OS user and permissions as the process that started it. There are no containers, seccomp filters, resource limits, import allowlists, or network restrictions. Use this only with MCP clients and workspaces you trust.

What the code actually enforces:

- `read_file`, `write_file`, `delete_file`, and `list_directory` resolve paths and reject those outside the workspace root. Analyze/lint/format do not use that check.
- `execute_python` is unsandboxed host execution: a temp `.py` file plus `subprocess.run` on the workspace `.venv` interpreter. The snippet can read or write anywhere that user can, start processes, and use the network. The optional `working_dir` is not workspace-checked.
- `create_venv` and `install_dependencies` can create `.venv` and install packages into it with pip.

Do not expose the server to untrusted clients, and do not point `--workspace` at a tree you are unwilling to let an assistant modify or execute code from.

## Installation

1. Clone the repository:
```bash
git clone https://github.com/gianlucamazza/mcp_python_toolbox.git
cd mcp_python_toolbox
```

2. Create and activate a virtual environment:
```bash
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# or
.venv\Scripts\activate  # Windows
```

3. Install the package in development mode:
```bash
pip install -e ".[dev]"
```

## Usage

### Running as a CLI Tool

The simplest way to start the server is using the CLI:

```bash
# Start with current directory as workspace
python -m mcp_python_toolbox

# Or specify a workspace directory
python -m mcp_python_toolbox --workspace /path/to/your/project
```

### Setting Up with Claude Desktop

Claude Desktop can automatically launch and manage the MCP Python Toolbox server. Here's how to configure it:

1. Install and set up the MCP Python Toolbox as described above
2. Add a configuration entry for the Python Toolbox in Claude Desktop's MCP tools configuration:

```json
"python-toolbox": {
  "command": "/Users/username/path/to/mcp_python_toolbox/.venv/bin/python",
  "args": [
    "-m",
    "mcp_python_toolbox",
    "--workspace",
    "/Users/username/path/to/workspace"
  ],
  "env": {
    "PYTHONPATH": "/Users/username/path/to/mcp_python_toolbox/src",
    "PATH": "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin",
    "VIRTUAL_ENV": "/Users/username/path/to/mcp_python_toolbox/.venv",
    "PYTHONHOME": ""
  }
}
```

3. Customize the paths to match your environment
4. Claude Desktop will automatically start the MCP server when needed
5. Claude will now have access to Python development tools through the MCP interface

### Programmatic Usage

```python
from mcp_python_toolbox import PythonToolboxServer

server = PythonToolboxServer(workspace_root="/path/to/your/project")
server.setup()
server.run()
```

### Core Module Examples

#### File Operations
```python
from mcp_python_toolbox.core import FileOperations

file_ops = FileOperations(workspace_root="/path/to/project")

# Read file contents
content = file_ops.read_file("src/example.py")
# Read specific lines
lines = file_ops.read_file("src/example.py", start_line=10, end_line=20)

# Write to file
file_ops.write_file("output.txt", "Hello, World!")
# Append to file
file_ops.write_file("log.txt", "New entry\n", mode='a')

# List directory contents
contents = file_ops.list_directory("src")
for item in contents:
    print(f"{item['name']} - {item['type']} - {item['size']} bytes")
```

#### Code Analysis
```python
from mcp_python_toolbox.core import CodeAnalyzer

analyzer = CodeAnalyzer(workspace_root="/path/to/project")

# Analyze Python file structure
analysis = analyzer.parse_python_file("src/example.py")
print(f"Found {len(analysis['functions'])} functions")
print(f"Found {len(analysis['classes'])} classes")

# Format code
formatted = analyzer.format_code(code, style='black')

# Lint code
issues = analyzer.lint_code("src/example.py")
for issue in issues:
    print(f"Line {issue['line']}: {issue['message']}")
```

#### Project Management
```python
from mcp_python_toolbox.core import ProjectManager

pm = ProjectManager(workspace_root="/path/to/project")

# Create virtual environment
pm.create_virtual_environment()

# Install dependencies
pm.install_dependencies()  # from requirements.txt or pyproject.toml
pm.install_dependencies("requirements-dev.txt")  # from specific file

# Check for conflicts
conflicts = pm.check_dependency_conflicts()
if conflicts:
    print("Found dependency conflicts:")
    for conflict in conflicts:
        print(f"{conflict['package']} requires {conflict['requires']}")

# Update packages
pm.update_package("requests")  # to latest
pm.update_package("flask", version="2.0.0")  # to specific version
```

#### Code Execution
```python
from mcp_python_toolbox.core.code_executor import CodeExecutor

executor = CodeExecutor(workspace_root="/path/to/project")

code = '''
def greet(name):
    return f"Hello, {name}!"

print(greet("World"))
'''

result = executor.execute_code(code)
print(f"Output: {result['stdout']}")
print(f"Errors: {result['stderr']}")
print(f"Exit code: {result['exit_code']}")
```

## Development

### Tests

This repository does not currently ship a `tests/` suite. `pyproject.toml` is configured for pytest if you add one:

```bash
pytest
```

### Type Checking

```bash
mypy src/mcp_python_toolbox
```

### Linting

```bash
pylint src/mcp_python_toolbox
```

### Formatting

```bash
black src/mcp_python_toolbox
```

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- MCP server built with the [Python SDK](https://github.com/modelcontextprotocol/python-sdk) (`FastMCP`)
- Formatting via Black; linting via Pylint (run in a subprocess)
