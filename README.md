[![MseeP.ai Security Assessment Badge](https://mseep.net/pr/gianlucamazza-mcp-python-toolbox-badge.png)](https://mseep.ai/app/gianlucamazza-mcp-python-toolbox)

# MCP Python Toolbox

A Model Context Protocol (MCP) server that provides a comprehensive set of tools for Python development, enabling AI assistants like Claude to effectively work with Python code and projects.

## Overview

MCP Python Toolbox implements a Model Context Protocol server that gives Claude the ability to perform Python development tasks through a standardized interface. It enables Claude to:

- Read, write, and manage files within a workspace
- Analyze, format, and lint Python code
- Manage virtual environments and dependencies
- Execute Python code safely

## Features

### File Operations (`FileOperations`)
- Safe file operations within a workspace directory
- Path validation to prevent unauthorized access outside workspace
- Read and write files with line-specific operations
- Create and delete files and directories
- List directory contents with detailed metadata (size, type, modification time)
- Automatic parent directory creation when writing files

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
- Comprehensive code linting using Pylint with detailed reports

### Project Management (`ProjectManager`)
- Create and manage virtual environments with pip support
- Flexible dependency management:
  - Install from requirements.txt
  - Install from pyproject.toml
  - Support for specific package versions
- Advanced dependency handling:
  - Check for version conflicts between packages
  - List all installed packages with versions
  - Update packages to specific versions
  - Generate requirements.txt from current environment

### Code Execution (`CodeExecutor`)
- Execute Python code in a controlled environment
- Uses project's virtual environment for consistent dependencies
- Temporary file management for code execution
- Capture stdout, stderr, and exit codes
- Support for custom working directories

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
from mcp_python_toolbox.core import CodeExecutor

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

### Running Tests

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

- Implements the [Model Context Protocol](https://github.com/modelcontextprotocol/servers) specification
- Built with modern Python development tools and best practices
- Uses industry-standard formatting (Black) and linting (Pylint) tools
