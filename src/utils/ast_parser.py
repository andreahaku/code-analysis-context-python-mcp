"""AST parser for Python code analysis."""

import ast
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Set


@dataclass
class FunctionInfo:
    """Information about a function."""

    name: str
    line: int
    is_async: bool
    is_method: bool
    decorators: List[str]
    args: List[str]
    returns: Optional[str]
    docstring: Optional[str]


@dataclass
class ClassInfo:
    """Information about a class."""

    name: str
    line: int
    bases: List[str]
    decorators: List[str]
    methods: List[FunctionInfo]
    docstring: Optional[str]


@dataclass
class ImportInfo:
    """Information about imports."""

    module: str
    names: List[str]
    is_from: bool
    line: int


@dataclass
class ModuleInfo:
    """Complete module analysis."""

    path: Path
    imports: List[ImportInfo]
    classes: List[ClassInfo]
    functions: List[FunctionInfo]
    constants: List[str]
    docstring: Optional[str]
    lines: int


class ASTParser:
    """Parse Python AST for code analysis."""

    @staticmethod
    def parse_file(file_path: Path) -> Optional[ModuleInfo]:
        """
        Parse a Python file and extract information.

        Args:
            file_path: Path to Python file

        Returns:
            ModuleInfo or None if parsing fails
        """
        try:
            content = file_path.read_text(encoding="utf-8")
            tree = ast.parse(content, filename=str(file_path))

            imports = ASTParser._extract_imports(tree)
            classes = ASTParser._extract_classes(tree)
            functions = ASTParser._extract_functions(tree)
            constants = ASTParser._extract_constants(tree)
            docstring = ast.get_docstring(tree)
            lines = len(content.splitlines())

            return ModuleInfo(
                path=file_path,
                imports=imports,
                classes=classes,
                functions=functions,
                constants=constants,
                docstring=docstring,
                lines=lines,
            )
        except (SyntaxError, UnicodeDecodeError) as e:
            # Skip files with syntax errors or encoding issues
            return None

    @staticmethod
    def _extract_imports(tree: ast.AST) -> List[ImportInfo]:
        """Extract import statements."""
        imports = []

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(
                        ImportInfo(
                            module=alias.name,
                            names=[alias.asname or alias.name],
                            is_from=False,
                            line=node.lineno,
                        )
                    )
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                names = [alias.name for alias in node.names]
                imports.append(
                    ImportInfo(module=module, names=names, is_from=True, line=node.lineno)
                )

        return imports

    @staticmethod
    def _extract_classes(tree: ast.AST) -> List[ClassInfo]:
        """Extract class definitions."""
        classes = []

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                bases = [ASTParser._get_name(base) for base in node.bases]
                decorators = [ASTParser._get_name(dec) for dec in node.decorator_list]
                methods = [
                    ASTParser._function_to_info(method, is_method=True)
                    for method in node.body
                    if isinstance(method, (ast.FunctionDef, ast.AsyncFunctionDef))
                ]

                classes.append(
                    ClassInfo(
                        name=node.name,
                        line=node.lineno,
                        bases=bases,
                        decorators=decorators,
                        methods=methods,
                        docstring=ast.get_docstring(node),
                    )
                )

        return classes

    @staticmethod
    def _extract_functions(tree: ast.AST) -> List[FunctionInfo]:
        """Extract top-level function definitions."""
        functions = []

        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                functions.append(ASTParser._function_to_info(node, is_method=False))

        return functions

    @staticmethod
    def _function_to_info(
        node: ast.FunctionDef | ast.AsyncFunctionDef, is_method: bool
    ) -> FunctionInfo:
        """Convert function AST node to FunctionInfo."""
        decorators = [ASTParser._get_name(dec) for dec in node.decorator_list]
        args = [arg.arg for arg in node.args.args]

        returns = None
        if node.returns:
            returns = ASTParser._get_name(node.returns)

        return FunctionInfo(
            name=node.name,
            line=node.lineno,
            is_async=isinstance(node, ast.AsyncFunctionDef),
            is_method=is_method,
            decorators=decorators,
            args=args,
            returns=returns,
            docstring=ast.get_docstring(node),
        )

    @staticmethod
    def _extract_constants(tree: ast.AST) -> List[str]:
        """Extract module-level constants (UPPER_CASE variables)."""
        constants = []

        for node in tree.body:
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        name = target.id
                        # Check if it's an uppercase constant
                        if name.isupper():
                            constants.append(name)

        return constants

    @staticmethod
    def _get_name(node: ast.AST) -> str:
        """Get name from AST node."""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            value = ASTParser._get_name(node.value)
            return f"{value}.{node.attr}"
        elif isinstance(node, ast.Subscript):
            value = ASTParser._get_name(node.value)
            return f"{value}[...]"
        elif isinstance(node, ast.Call):
            func = ASTParser._get_name(node.func)
            return f"{func}(...)"
        else:
            return ast.unparse(node) if hasattr(ast, "unparse") else "Unknown"

    @staticmethod
    def get_dependencies(module_info: ModuleInfo, project_root: Path) -> Set[str]:
        """
        Extract internal project dependencies from imports.

        Args:
            module_info: Parsed module information
            project_root: Project root directory

        Returns:
            Set of internal module names
        """
        dependencies = set()

        for import_info in module_info.imports:
            # Skip standard library and external packages
            if ASTParser._is_local_import(import_info.module, project_root):
                dependencies.add(import_info.module)

        return dependencies

    @staticmethod
    def _is_local_import(module_name: str, project_root: Path) -> bool:
        """Check if import is from local project."""
        if not module_name:
            return False

        # Check if starts with common external package names
        external_prefixes = [
            "pandas",
            "numpy",
            "sklearn",
            "matplotlib",
            "seaborn",
            "fastapi",
            "django",
            "flask",
            "pytest",
            "unittest",
        ]

        for prefix in external_prefixes:
            if module_name.startswith(prefix):
                return False

        # Check if file exists in project
        parts = module_name.split(".")
        possible_path = project_root / "/".join(parts)

        return (
            (possible_path.with_suffix(".py")).exists()
            or (possible_path / "__init__.py").exists()
        )
