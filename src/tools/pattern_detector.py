"""Pattern detector for Python data analysis projects."""

import ast
import json
from pathlib import Path
from typing import Any, Dict, List, Sequence, Set

from mcp.types import TextContent

from ..utils.ast_parser import ASTParser
from ..utils.file_scanner import FileScanner
from ..utils.framework_detector import FrameworkDetector


async def analyze_patterns(args: Dict[str, Any]) -> Sequence[TextContent]:
    """
    Detect patterns in Python projects.

    Patterns include:
    - Pandas DataFrame operations
    - NumPy array manipulations
    - Scikit-learn pipelines and models
    - Matplotlib/Seaborn visualizations
    - FastAPI/Django endpoints
    - Async/await patterns
    - Context managers
    - Decorators
    """
    project_path = args.get("project_path", ".")
    pattern_types = args.get("pattern_types", [])
    detect_custom_patterns = args.get("detect_custom_patterns", False)
    compare_with_best_practices = args.get("compare_with_best_practices", False)
    suggest_improvements = args.get("suggest_improvements", False)
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

    # Detect frameworks
    frameworks = FrameworkDetector.detect_frameworks(files)

    # Detect patterns
    patterns = {
        "dataframe": [],
        "array": [],
        "pipeline": [],
        "model": [],
        "visualization": [],
        "api": [],
        "async": [],
        "decorator": [],
        "context_manager": [],
    }

    for file_path in files:
        file_patterns = _detect_patterns_in_file(file_path, project_root, frameworks)

        for pattern_type, items in file_patterns.items():
            patterns[pattern_type].extend(items)

    # Filter by requested types
    if pattern_types:
        patterns = {k: v for k, v in patterns.items() if k in pattern_types}

    # Detect antipatterns
    antipatterns = _detect_antipatterns(patterns, files)

    # Best practices comparison
    best_practices = []
    if compare_with_best_practices:
        best_practices = _compare_best_practices(patterns, frameworks)

    # Generate recommendations
    recommendations = []
    if suggest_improvements:
        recommendations = _generate_recommendations(patterns, antipatterns, frameworks)

    result = {
        "project": {
            "name": project_root.name,
            "type": "python",
            "totalFiles": len(files),
        },
        "frameworks": sorted(frameworks),
        "patterns": patterns,
        "summary": {
            "totalPatterns": sum(len(v) for v in patterns.values()),
            "byType": {k: len(v) for k, v in patterns.items() if v},
        },
        "antipatterns": antipatterns,
        "bestPractices": best_practices,
        "recommendations": recommendations,
    }

    return [TextContent(type="text", text=json.dumps(result, indent=2))]


def _detect_patterns_in_file(
    file_path: Path, project_root: Path, frameworks: Set[str]
) -> Dict[str, List[Dict]]:
    """Detect patterns in a single file."""
    patterns = {
        "dataframe": [],
        "array": [],
        "pipeline": [],
        "model": [],
        "visualization": [],
        "api": [],
        "async": [],
        "decorator": [],
        "context_manager": [],
    }

    try:
        content = file_path.read_text(encoding="utf-8")
        tree = ast.parse(content)
        relative_path = str(file_path.relative_to(project_root))

        # Detect DataFrame operations
        if "pandas" in frameworks:
            df_patterns = _detect_dataframe_patterns(tree, content, relative_path)
            patterns["dataframe"].extend(df_patterns)

        # Detect NumPy patterns
        if "numpy" in frameworks:
            array_patterns = _detect_array_patterns(tree, content, relative_path)
            patterns["array"].extend(array_patterns)

        # Detect sklearn patterns
        if "sklearn" in frameworks:
            ml_patterns = _detect_ml_patterns(tree, content, relative_path)
            patterns["pipeline"].extend(ml_patterns.get("pipeline", []))
            patterns["model"].extend(ml_patterns.get("model", []))

        # Detect visualization patterns
        if "matplotlib" in frameworks or "seaborn" in frameworks:
            viz_patterns = _detect_visualization_patterns(tree, content, relative_path)
            patterns["visualization"].extend(viz_patterns)

        # Detect API patterns
        if any(fw in frameworks for fw in ["fastapi", "django", "flask"]):
            api_patterns = _detect_api_patterns(tree, content, relative_path)
            patterns["api"].extend(api_patterns)

        # Detect async patterns
        async_patterns = _detect_async_patterns(tree, relative_path)
        patterns["async"].extend(async_patterns)

        # Detect decorators
        decorator_patterns = _detect_decorators(tree, relative_path)
        patterns["decorator"].extend(decorator_patterns)

        # Detect context managers
        context_patterns = _detect_context_managers(tree, relative_path)
        patterns["context_manager"].extend(context_patterns)

    except (SyntaxError, UnicodeDecodeError):
        pass

    return patterns


def _detect_dataframe_patterns(tree: ast.AST, content: str, file_path: str) -> List[Dict]:
    """Detect pandas DataFrame patterns."""
    patterns = []

    # Common DataFrame operations
    df_operations = ["read_csv", "read_excel", "groupby", "merge", "concat", "pivot", "melt"]

    for line_num, line in enumerate(content.splitlines(), 1):
        for op in df_operations:
            if op in line and ("pd." in line or "DataFrame" in line):
                patterns.append({
                    "type": "dataframe-operation",
                    "operation": op,
                    "file": file_path,
                    "line": line_num,
                    "description": f"DataFrame {op} operation"
                })
                break

    return patterns


def _detect_array_patterns(tree: ast.AST, content: str, file_path: str) -> List[Dict]:
    """Detect NumPy array patterns."""
    patterns = []

    # Common NumPy operations
    np_operations = ["array", "zeros", "ones", "arange", "linspace", "reshape", "dot"]

    for line_num, line in enumerate(content.splitlines(), 1):
        for op in np_operations:
            if op in line and ("np." in line or "numpy." in line):
                patterns.append({
                    "type": "array-operation",
                    "operation": op,
                    "file": file_path,
                    "line": line_num,
                    "description": f"NumPy {op} operation"
                })
                break

    return patterns


def _detect_ml_patterns(tree: ast.AST, content: str, file_path: str) -> Dict[str, List[Dict]]:
    """Detect scikit-learn patterns."""
    patterns = {"pipeline": [], "model": []}

    for line_num, line in enumerate(content.splitlines(), 1):
        if "Pipeline" in line:
            patterns["pipeline"].append({
                "type": "sklearn-pipeline",
                "file": file_path,
                "line": line_num,
                "description": "Scikit-learn Pipeline usage"
            })
        elif any(x in line for x in [".fit(", ".predict(", ".transform("]):
            patterns["model"].append({
                "type": "sklearn-model",
                "file": file_path,
                "line": line_num,
                "description": "Model training/prediction"
            })

    return patterns


def _detect_visualization_patterns(tree: ast.AST, content: str, file_path: str) -> List[Dict]:
    """Detect matplotlib/seaborn patterns."""
    patterns = []

    viz_functions = ["plot", "scatter", "hist", "bar", "heatmap", "figure", "subplot"]

    for line_num, line in enumerate(content.splitlines(), 1):
        for func in viz_functions:
            if func in line and ("plt." in line or "sns." in line):
                patterns.append({
                    "type": "visualization",
                    "function": func,
                    "file": file_path,
                    "line": line_num,
                    "description": f"Visualization: {func}"
                })
                break

    return patterns


def _detect_api_patterns(tree: ast.AST, content: str, file_path: str) -> List[Dict]:
    """Detect API endpoint patterns."""
    patterns = []

    for node in ast.walk(tree):
        # FastAPI patterns
        if isinstance(node, ast.FunctionDef):
            for decorator in node.decorator_list:
                decorator_name = ""
                if isinstance(decorator, ast.Name):
                    decorator_name = decorator.id
                elif isinstance(decorator, ast.Attribute):
                    decorator_name = decorator.attr

                if decorator_name in ["get", "post", "put", "delete", "patch"]:
                    patterns.append({
                        "type": "api-endpoint",
                        "method": decorator_name.upper(),
                        "function": node.name,
                        "file": file_path,
                        "line": node.lineno,
                        "description": f"API endpoint: {decorator_name.upper()} {node.name}"
                    })

    return patterns


def _detect_async_patterns(tree: ast.AST, file_path: str) -> List[Dict]:
    """Detect async/await patterns."""
    patterns = []

    for node in ast.walk(tree):
        if isinstance(node, ast.AsyncFunctionDef):
            patterns.append({
                "type": "async-function",
                "name": node.name,
                "file": file_path,
                "line": node.lineno,
                "description": f"Async function: {node.name}"
            })

    return patterns


def _detect_decorators(tree: ast.AST, file_path: str) -> List[Dict]:
    """Detect decorator patterns."""
    patterns = []

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.decorator_list:
            for decorator in node.decorator_list:
                decorator_name = ""
                if isinstance(decorator, ast.Name):
                    decorator_name = decorator.id
                elif isinstance(decorator, ast.Attribute):
                    decorator_name = f"{decorator.value.id if isinstance(decorator.value, ast.Name) else ''}.{decorator.attr}"

                if decorator_name and not decorator_name.startswith("app."):
                    patterns.append({
                        "type": "decorator",
                        "name": decorator_name,
                        "function": node.name,
                        "file": file_path,
                        "line": node.lineno,
                        "description": f"Decorator: @{decorator_name}"
                    })

    return patterns


def _detect_context_managers(tree: ast.AST, file_path: str) -> List[Dict]:
    """Detect context manager patterns (with statements)."""
    patterns = []

    for node in ast.walk(tree):
        if isinstance(node, ast.With):
            for item in node.items:
                context_name = ""
                if isinstance(item.context_expr, ast.Call):
                    if isinstance(item.context_expr.func, ast.Name):
                        context_name = item.context_expr.func.id
                    elif isinstance(item.context_expr.func, ast.Attribute):
                        context_name = item.context_expr.func.attr

                if context_name:
                    patterns.append({
                        "type": "context-manager",
                        "name": context_name,
                        "file": file_path,
                        "line": node.lineno,
                        "description": f"Context manager: {context_name}"
                    })

    return patterns


def _detect_antipatterns(patterns: Dict, files: List[Path]) -> List[Dict]:
    """Detect common antipatterns."""
    antipatterns = []

    # Check for excessive DataFrame copies
    df_operations = patterns.get("dataframe", [])
    if len(df_operations) > 50:
        antipatterns.append({
            "type": "excessive-dataframe-operations",
            "severity": "warning",
            "description": f"Found {len(df_operations)} DataFrame operations. Consider optimizing with vectorization.",
            "suggestion": "Use vectorized operations and avoid loops over DataFrames"
        })

    return antipatterns


def _compare_best_practices(patterns: Dict, frameworks: Set[str]) -> List[Dict]:
    """Compare against best practices."""
    best_practices = []

    if "pandas" in frameworks:
        best_practices.append({
            "pattern": "DataFrame Operations",
            "status": "follows" if patterns.get("dataframe") else "not-detected",
            "details": "Using pandas for data manipulation",
            "suggestions": None
        })

    if "sklearn" in frameworks:
        has_pipelines = len(patterns.get("pipeline", [])) > 0
        best_practices.append({
            "pattern": "ML Pipelines",
            "status": "follows" if has_pipelines else "missing",
            "details": "Using sklearn Pipelines for ML workflows" if has_pipelines else "No pipelines detected",
            "suggestions": "Consider using sklearn Pipeline for reproducible ML workflows" if not has_pipelines else None
        })

    return best_practices


def _generate_recommendations(patterns: Dict, antipatterns: List[Dict], frameworks: Set[str]) -> List[str]:
    """Generate improvement recommendations."""
    recommendations = []

    if antipatterns:
        recommendations.append(f"⚠️ Found {len(antipatterns)} antipatterns. Review and refactor.")

    if "pandas" in frameworks and len(patterns.get("dataframe", [])) == 0:
        recommendations.append("💡 No DataFrame operations detected. Ensure pandas is being used effectively.")

    if patterns.get("async") and len(patterns["async"]) > 10:
        recommendations.append("✅ Good use of async patterns for concurrent operations.")

    if not recommendations:
        recommendations.append("✅ Code patterns look good!")

    return recommendations
