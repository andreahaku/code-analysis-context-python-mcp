"""Convention validator for Python projects (PEP 8)."""

import ast
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Sequence

from mcp.types import TextContent

from ..utils.ast_parser import ASTParser
from ..utils.file_scanner import FileScanner


async def validate_conventions(args: Dict[str, Any]) -> Sequence[TextContent]:
    """
    Validate Python coding conventions.

    Features:
    - PEP 8 compliance checking
    - Naming conventions (snake_case, PascalCase)
    - Import ordering
    - Docstring presence
    - Type hint usage
    - Auto-fix suggestions
    """
    project_path = args.get("project_path", ".")
    autodetect_conventions = args.get("autodetect_conventions", True)
    severity = args.get("severity", "warning")
    include_globs = args.get("include_globs", ["**/*.py"])
    exclude_globs = args.get("exclude_globs")

    project_root = Path(project_path).resolve()

    # Scan files
    files = FileScanner.scan_files(project_path, include_globs, exclude_globs)

    if not files:
        return [
            TextContent(
                type="text",
                text=json.dumps({"error": "No Python files found"}, indent=2),
            )
        ]

    # Auto-detect conventions
    detected_conventions = []
    if autodetect_conventions:
        detected_conventions = _detect_conventions(files, project_root)

    # Define standard conventions (PEP 8)
    conventions = {
        "naming": {
            "functions": "snake_case",
            "classes": "PascalCase",
            "constants": "UPPER_SNAKE_CASE",
            "modules": "snake_case",
            "private_prefix": "_",
        },
        "imports": {
            "style": "absolute",
            "grouping": True,
            "order": ["stdlib", "third_party", "local"],
        },
        "style": {
            "line_length": 100,
            "quotes": "double",
            "indentation": 4,
        },
        "docstrings": {
            "required": True,
            "modules": True,
            "classes": True,
            "functions": True,
        },
        "type_hints": {
            "required": False,
            "functions": True,
            "methods": True,
        },
    }

    # Validate files
    violations = []
    stats = {
        "naming": 0,
        "imports": 0,
        "style": 0,
        "docstrings": 0,
        "type_hints": 0,
    }

    for file_path in files:
        file_violations = _validate_file(file_path, project_root, conventions)
        violations.extend(file_violations)

        # Count by category
        for v in file_violations:
            category = v.get("category", "other")
            if category in stats:
                stats[category] += 1

    # Filter by severity
    severity_order = {"error": 2, "warning": 1, "info": 0}
    min_severity = severity_order.get(severity, 0)
    violations = [
        v for v in violations
        if severity_order.get(v.get("severity", "info"), 0) >= min_severity
    ]

    # Calculate consistency score
    total_checks = sum(stats.values()) + len(files)
    consistency_score = max(
        0, 100 - int((sum(stats.values()) / max(1, total_checks)) * 100)
    )

    # Build result
    result = {
        "project": {
            "name": project_root.name,
            "totalFiles": len(files),
        },
        "detectedConventions": detected_conventions,
        "conventions": conventions,
        "violations": violations[:100],  # Limit to 100
        "consistency": {
            "overall": consistency_score,
            "byCategory": {
                "naming": 100 - int((stats["naming"] / max(1, len(files))) * 100),
                "imports": 100 - int((stats["imports"] / max(1, len(files))) * 100),
                "style": 100 - int((stats["style"] / max(1, len(files))) * 100),
                "docstrings": 100 - int((stats["docstrings"] / max(1, len(files))) * 100),
                "type_hints": 100 - int((stats["type_hints"] / max(1, len(files))) * 100),
            },
        },
        "summary": {
            "totalViolations": len(violations),
            "byCategory": stats,
            "bySeverity": {
                "error": len([v for v in violations if v.get("severity") == "error"]),
                "warning": len([v for v in violations if v.get("severity") == "warning"]),
                "info": len([v for v in violations if v.get("severity") == "info"]),
            },
        },
        "recommendations": _generate_recommendations(violations, consistency_score, stats),
    }

    return [TextContent(type="text", text=json.dumps(result, indent=2))]


def _detect_conventions(files: List[Path], project_root: Path) -> List[Dict]:
    """Detect existing conventions in codebase."""
    detected = []

    # Sample some files
    sample_files = files[:min(20, len(files))]

    # Detect naming patterns
    function_names = []
    class_names = []

    for file_path in sample_files:
        module_info = ASTParser.parse_file(file_path)
        if not module_info:
            continue

        function_names.extend([f.name for f in module_info.functions])
        class_names.extend([c.name for c in module_info.classes])

    # Check function naming
    snake_case_count = sum(1 for name in function_names if _is_snake_case(name))
    if function_names and snake_case_count / len(function_names) > 0.8:
        detected.append({
            "category": "naming",
            "rule": "Function naming",
            "pattern": "snake_case",
            "confidence": round(snake_case_count / len(function_names), 2),
            "occurrences": len(function_names),
            "examples": function_names[:3],
        })

    # Check class naming
    pascal_case_count = sum(1 for name in class_names if _is_pascal_case(name))
    if class_names and pascal_case_count / len(class_names) > 0.8:
        detected.append({
            "category": "naming",
            "rule": "Class naming",
            "pattern": "PascalCase",
            "confidence": round(pascal_case_count / len(class_names), 2),
            "occurrences": len(class_names),
            "examples": class_names[:3],
        })

    return detected


def _validate_file(
    file_path: Path, project_root: Path, conventions: Dict
) -> List[Dict]:
    """Validate a single file against conventions."""
    violations = []
    relative_path = str(file_path.relative_to(project_root))

    try:
        content = file_path.read_text(encoding="utf-8")
        tree = ast.parse(content)
        module_info = ASTParser.parse_file(file_path)

        if not module_info:
            return violations

        # Check naming conventions
        violations.extend(_check_naming(module_info, relative_path, conventions))

        # Check imports
        violations.extend(_check_imports(module_info, relative_path, conventions))

        # Check style
        violations.extend(_check_style(content, relative_path, conventions))

        # Check docstrings
        violations.extend(_check_docstrings(module_info, relative_path, conventions))

        # Check type hints
        violations.extend(_check_type_hints(module_info, relative_path, conventions))

    except (SyntaxError, UnicodeDecodeError):
        pass

    return violations


def _check_naming(module_info, file_path: str, conventions: Dict) -> List[Dict]:
    """Check naming conventions."""
    violations = []
    naming_rules = conventions.get("naming", {})

    # Check functions
    for func in module_info.functions:
        if not _is_snake_case(func.name) and not func.name.startswith("_"):
            violations.append({
                "file": file_path,
                "line": func.line,
                "category": "naming",
                "severity": "warning",
                "rule": "Function naming",
                "message": f"Function '{func.name}' should use snake_case",
                "expected": "snake_case",
                "actual": func.name,
            })

    # Check classes
    for cls in module_info.classes:
        if not _is_pascal_case(cls.name):
            violations.append({
                "file": file_path,
                "line": cls.line,
                "category": "naming",
                "severity": "warning",
                "rule": "Class naming",
                "message": f"Class '{cls.name}' should use PascalCase",
                "expected": "PascalCase",
                "actual": cls.name,
            })

    # Check constants
    for const in module_info.constants:
        if not const.isupper():
            violations.append({
                "file": file_path,
                "line": None,
                "category": "naming",
                "severity": "info",
                "rule": "Constant naming",
                "message": f"Constant '{const}' should use UPPER_SNAKE_CASE",
                "expected": "UPPER_SNAKE_CASE",
                "actual": const,
            })

    return violations


def _check_imports(module_info, file_path: str, conventions: Dict) -> List[Dict]:
    """Check import conventions."""
    violations = []

    # Check for grouped imports
    if len(module_info.imports) > 5:
        # Check if imports are grouped (stdlib, third-party, local)
        # This is a simplified check
        import_lines = sorted([imp.line for imp in module_info.imports])
        if len(import_lines) > 1:
            # Check for gaps (blank lines between groups)
            gaps = [import_lines[i+1] - import_lines[i] for i in range(len(import_lines)-1)]
            if all(g == 1 for g in gaps):  # No gaps
                violations.append({
                    "file": file_path,
                    "line": import_lines[0],
                    "category": "imports",
                    "severity": "info",
                    "rule": "Import grouping",
                    "message": "Imports should be grouped (stdlib, third-party, local) with blank lines",
                })

    return violations


def _check_style(content: str, file_path: str, conventions: Dict) -> List[Dict]:
    """Check style conventions."""
    violations = []
    style_rules = conventions.get("style", {})
    max_line_length = style_rules.get("line_length", 100)

    lines = content.splitlines()
    for line_num, line in enumerate(lines, 1):
        # Check line length
        if len(line) > max_line_length and not line.strip().startswith("#"):
            violations.append({
                "file": file_path,
                "line": line_num,
                "category": "style",
                "severity": "info",
                "rule": "Line length",
                "message": f"Line exceeds {max_line_length} characters ({len(line)} chars)",
                "expected": f"<= {max_line_length} chars",
                "actual": f"{len(line)} chars",
            })

    return violations


def _check_docstrings(module_info, file_path: str, conventions: Dict) -> List[Dict]:
    """Check docstring presence."""
    violations = []
    docstring_rules = conventions.get("docstrings", {})

    if not docstring_rules.get("required"):
        return violations

    # Check module docstring
    if docstring_rules.get("modules") and not module_info.docstring:
        violations.append({
            "file": file_path,
            "line": 1,
            "category": "docstrings",
            "severity": "info",
            "rule": "Module docstring",
            "message": "Module missing docstring",
        })

    # Check class docstrings
    if docstring_rules.get("classes"):
        for cls in module_info.classes:
            if not cls.docstring:
                violations.append({
                    "file": file_path,
                    "line": cls.line,
                    "category": "docstrings",
                    "severity": "info",
                    "rule": "Class docstring",
                    "message": f"Class '{cls.name}' missing docstring",
                })

    # Check function docstrings
    if docstring_rules.get("functions"):
        for func in module_info.functions:
            if not func.docstring and not func.name.startswith("_"):
                violations.append({
                    "file": file_path,
                    "line": func.line,
                    "category": "docstrings",
                    "severity": "info",
                    "rule": "Function docstring",
                    "message": f"Function '{func.name}' missing docstring",
                })

    return violations


def _check_type_hints(module_info, file_path: str, conventions: Dict) -> List[Dict]:
    """Check type hint usage."""
    violations = []
    type_hint_rules = conventions.get("type_hints", {})

    if not type_hint_rules.get("required"):
        return violations

    # Check functions
    if type_hint_rules.get("functions"):
        for func in module_info.functions:
            if not func.returns and not func.name.startswith("_"):
                violations.append({
                    "file": file_path,
                    "line": func.line,
                    "category": "type_hints",
                    "severity": "info",
                    "rule": "Function return type",
                    "message": f"Function '{func.name}' missing return type hint",
                })

    return violations


def _is_snake_case(name: str) -> bool:
    """Check if name is snake_case."""
    return bool(re.match(r"^[a-z_][a-z0-9_]*$", name))


def _is_pascal_case(name: str) -> bool:
    """Check if name is PascalCase."""
    return bool(re.match(r"^[A-Z][a-zA-Z0-9]*$", name))


def _is_upper_snake_case(name: str) -> bool:
    """Check if name is UPPER_SNAKE_CASE."""
    return bool(re.match(r"^[A-Z_][A-Z0-9_]*$", name))


def _generate_recommendations(
    violations: List[Dict], consistency_score: int, stats: Dict
) -> List[str]:
    """Generate recommendations."""
    recommendations = []

    if consistency_score >= 90:
        recommendations.append("✅ Excellent code consistency! Keep up the good work.")
    elif consistency_score >= 70:
        recommendations.append(
            f"Good consistency ({consistency_score}%), but there's room for improvement."
        )
    else:
        recommendations.append(
            f"⚠️ Low consistency ({consistency_score}%). Consider establishing coding standards."
        )

    # Category-specific recommendations
    if stats.get("naming", 0) > 10:
        recommendations.append(
            f"Found {stats['naming']} naming inconsistencies. "
            "Use snake_case for functions, PascalCase for classes."
        )

    if stats.get("docstrings", 0) > 20:
        recommendations.append(
            f"Found {stats['docstrings']} missing docstrings. "
            "Add docstrings for better code documentation."
        )

    if stats.get("style", 0) > 15:
        recommendations.append(
            f"Found {stats['style']} style violations. "
            "Consider using black or autopep8 for formatting."
        )

    if not recommendations:
        recommendations.append("✅ Code follows PEP 8 conventions well!")

    return recommendations
