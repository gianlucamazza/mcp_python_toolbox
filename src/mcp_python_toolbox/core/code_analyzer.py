import ast
import json
import subprocess
import sys
from typing import List, Dict, Any, Optional, Union, TypedDict, cast
from pathlib import Path
import autopep8  # type: ignore
import black  # type: ignore

class CodeAnalysis(TypedDict):
    """Structure containing the analysis results of a Python file.

    Attributes:
        imports: List of dictionaries containing import statements and their aliases
        functions: List of dictionaries containing function definitions and their metadata
        classes: List of dictionaries containing class definitions and their metadata
        global_variables: List of global variable names
    """
    imports: List[Dict[str, Optional[str]]]
    functions: List[Dict[str, Any]]
    classes: List[Dict[str, Any]]
    global_variables: List[str]

class CodeAnalyzer:
    """Analyzes Python code for structure, formatting, and linting.

    This class provides tools for:
    - Parsing Python files to extract their structure
    - Formatting code using black or autopep8
    - Running pylint for code quality checks
    """

    def __init__(self, workspace_root: Union[str, Path]):
        """Initialize the analyzer with a workspace root directory.

        Args:
            workspace_root: Path to the workspace root directory
        """
        self.workspace_root = Path(workspace_root).resolve()

    def parse_python_file(self, file_path: Union[str, Path]) -> CodeAnalysis:
        """Parse a Python file and return its structure.

        Args:
            file_path: Path to the Python file to analyze

        Returns:
            CodeAnalysis containing the file's imports, functions, classes, and global variables
        """
        path = Path(file_path)
        with open(path, 'r', encoding='utf-8') as f:
            tree = ast.parse(f.read())
        
        return self._analyze_ast(tree)

    def _analyze_ast(self, tree: ast.AST) -> CodeAnalysis:
        """Analyze an Abstract Syntax Tree (AST) and extract its structure.

        This method walks through the AST and collects information about:
        - Import statements and their aliases
        - Function definitions, including arguments and decorators
        - Class definitions, including base classes and methods
        - Global variable assignments

        Args:
            tree: The AST to analyze, typically obtained from ast.parse()

        Returns:
            CodeAnalysis containing the structured information extracted from the AST
        """
        analysis: CodeAnalysis = {
            'imports': [],
            'functions': [],
            'classes': [],
            'global_variables': []
        }

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for name in node.names:
                    analysis['imports'].append({
                        'name': name.name,
                        'alias': name.asname
                    })
            elif isinstance(node, ast.ImportFrom):
                for name in node.names:
                    analysis['imports'].append({
                        'name': f"{node.module}.{name.name}",
                        'alias': name.asname
                    })
            elif isinstance(node, ast.FunctionDef):
                analysis['functions'].append({
                    'name': node.name,
                    'args': [arg.arg for arg in node.args.args],
                    'decorators': [self._get_decorator_name(cast(Union[ast.Name, ast.Call, ast.Attribute], d)) for d in node.decorator_list],
                    'docstring': ast.get_docstring(node)
                })
            elif isinstance(node, ast.ClassDef):
                analysis['classes'].append({
                    'name': node.name,
                    'bases': [self._get_base_name(cast(Union[ast.Name, ast.Attribute], base)) for base in node.bases],
                    'methods': [m.name for m in node.body if isinstance(m, ast.FunctionDef)],
                    'docstring': ast.get_docstring(node)
                })
            elif isinstance(node, ast.Assign) and all(isinstance(t, ast.Name) for t in node.targets):
                analysis['global_variables'].extend(cast(ast.Name, t).id for t in node.targets)

        return analysis

    def _get_decorator_name(self, node: Union[ast.Name, ast.Call, ast.Attribute]) -> str:
        """Convert an AST decorator node into its string representation.

        Handles simple decorators (@decorator), decorator calls (@decorator()),
        and complex attribute access (@module.decorator).

        Args:
            node: AST node representing a decorator, can be:
                - ast.Name for simple decorators
                - ast.Call for decorator calls with arguments
                - ast.Attribute for decorators with attribute access

        Returns:
            String representation of the decorator (e.g., "decorator", "module.decorator")
        """
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                return node.func.id
            elif isinstance(node.func, ast.Attribute):
                return f"{self._get_decorator_name(cast(Union[ast.Name, ast.Call, ast.Attribute], node.func.value))}.{node.func.attr}"
        elif isinstance(node, ast.Attribute):
            return f"{self._get_decorator_name(cast(Union[ast.Name, ast.Call, ast.Attribute], node.value))}.{node.attr}"
        return str(node)

    def _get_base_name(self, node: Union[ast.Name, ast.Attribute]) -> str:
        """Convert an AST base class node into its string representation.

        Handles simple base classes (class A(B)) and those with attribute
        access (class A(module.B)).

        Args:
            node: AST node representing a base class, can be:
                - ast.Name for simple base classes
                - ast.Attribute for base classes with attribute access

        Returns:
            String representation of the base class (e.g., "BaseClass", "module.BaseClass")
        """
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return f"{self._get_base_name(cast(Union[ast.Name, ast.Attribute], node.value))}.{node.attr}"
        return str(node)

    def format_code(self, code: str, style: str = 'black') -> str:
        """Format Python code according to the specified style.

        Args:
            code: Python code to format
            style: Formatting style to use ('black' or 'pep8')

        Returns:
            Formatted code as a string

        Raises:
            ValueError: If an unsupported style is specified
        """
        if style == 'black':
            try:
                formatted = black.format_str(code, mode=black.FileMode())
                return str(formatted)
            except (black.InvalidInput, ValueError):
                return code
        elif style == 'pep8':
            return str(autopep8.fix_code(code))
        else:
            raise ValueError(f"Unsupported style: {style}")

    def lint_code(self, file_path: Union[str, Path]) -> List[Dict[str, Any]]:
        """Run pylint on a Python file and return the results.

        Pylint is invoked in a fresh subprocess with JSON output. Running it
        out-of-process gives every invocation a clean ``astroid`` module cache,
        so re-linting a file after it has been modified reflects the new
        contents instead of stale cached results. The JSON reporter also avoids
        the fragile colon-splitting that broke on Windows-style paths.

        Args:
            file_path: Path to the Python file to lint

        Returns:
            List of dictionaries containing lint issues with keys:
            - path: File path where the issue was found
            - line: Line number of the issue
            - type: Pylint category of the issue (e.g. "convention",
              "warning", "error", "refactor")
            - message: Message identifier followed by its description
        """
        path = Path(file_path).resolve()

        if not path.exists():
            return [{
                'path': str(path),
                'line': '1',
                'type': 'error',
                'message': f"File not found: {path}"
            }]

        cmd = [
            sys.executable, '-m', 'pylint',
            '--output-format=json',
            '--reports=n',
            '--score=n',
            str(path)
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=str(self.workspace_root),
                timeout=30
            )
        except subprocess.TimeoutExpired:
            return [{
                'path': str(path),
                'line': '1',
                'type': 'error',
                'message': "Pylint timed out after 30 seconds"
            }]
        except subprocess.SubprocessError as exc:
            return [{
                'path': str(path),
                'line': '1',
                'type': 'error',
                'message': f"Pylint subprocess error: {exc}"
            }]

        output = result.stdout.strip()
        if not output:
            return []

        try:
            pylint_results = json.loads(output)
        except json.JSONDecodeError:
            return [{
                'path': str(path),
                'line': '1',
                'type': 'error',
                'message': f"Failed to parse pylint output: {output[:200]}"
            }]

        issues: List[Dict[str, Any]] = []
        for issue in pylint_results:
            message_id = issue.get('message-id', 'unknown')
            issues.append({
                'path': issue.get('path', str(path)),
                'line': str(issue.get('line', 1)),
                'type': str(issue.get('type', 'unknown')),
                'message': f"{message_id}: {issue.get('message', 'No message')}"
            })

        return issues