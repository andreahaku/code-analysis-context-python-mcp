"""Architecture analyzer for Python projects."""

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Sequence

from mcp.types import TextContent

from ..utils.ast_parser import ASTParser, ModuleInfo
from ..utils.complexity_analyzer import ComplexityAnalyzer
from ..utils.diagram_generator import DiagramGenerator
from ..utils.file_scanner import FileScanner
from ..utils.framework_detector import FrameworkDetector


async def analyze_architecture(args: Dict[str, Any]) -> Sequence[TextContent]:
    """
    Analyze Python project architecture.

    Focuses on:
    - Module structure
    - Class hierarchies
    - Function definitions
    - API endpoints (FastAPI/Django/Flask)
    - Data models and schemas
    - Jupyter notebooks
    - Data pipelines
    """
    project_path = args.get("project_path", ".")
    depth = args.get("depth", "detailed")
    include_metrics = args.get("include_metrics", True)
    include_detailed_metrics = args.get("include_detailed_metrics", False)
    min_complexity = args.get("min_complexity", 0)
    max_detailed_files = args.get("max_detailed_files", 50)
    generate_diagrams = args.get("generate_diagrams", False)
    generate_memory_suggestions = args.get("generate_memory_suggestions", False)
    include_globs = args.get("include_globs", ["**/*.py"])
    exclude_globs = args.get("exclude_globs")

    project_root = Path(project_path).resolve()
    project_name = project_root.name

    # Scan for Python files
    files = FileScanner.scan_files(project_path, include_globs, exclude_globs)

    if not files:
        return [
            TextContent(
                type="text",
                text=json.dumps(
                    {
                        "error": "No Python files found in project",
                        "project": {"name": project_name, "path": str(project_root)},
                    },
                    indent=2,
                ),
            )
        ]

    # Detect frameworks
    frameworks = FrameworkDetector.detect_frameworks(files)
    project_type = FrameworkDetector.detect_project_type(frameworks)

    # Parse all files
    modules: List[ModuleInfo] = []
    for file_path in files:
        module_info = ASTParser.parse_file(file_path)
        if module_info:
            modules.append(module_info)

    # Analyze complexity
    file_metrics = []
    total_complexity = 0
    total_lines = 0

    for module in modules:
        complexity_data = ComplexityAnalyzer.analyze_file(module.path)
        file_complexity = complexity_data.get("totalComplexity", 0)
        total_complexity += file_complexity
        total_lines += module.lines

        # Create file metric entry
        if include_detailed_metrics and file_complexity >= min_complexity:
            relative_path = str(module.path.relative_to(project_root))
            file_metrics.append(
                {
                    "path": relative_path,
                    "lines": module.lines,
                    "complexity": file_complexity,
                    "maintainability": complexity_data.get("maintainabilityIndex", 100),
                    "functions": len(module.functions) + sum(len(cls.methods) for cls in module.classes),
                    "classes": len(module.classes),
                    "imports": len(module.imports),
                }
            )

    # Sort by complexity and limit
    file_metrics.sort(key=lambda x: x["complexity"], reverse=True)
    if max_detailed_files and len(file_metrics) > max_detailed_files:
        file_metrics = file_metrics[:max_detailed_files]

    # Aggregate statistics
    avg_complexity = total_complexity / len(modules) if modules else 0
    max_complexity = max((m["complexity"] for m in file_metrics), default=0)

    # Extract layers/structure
    layers = _analyze_structure(modules, project_root)

    # Collect all classes and functions
    all_classes = []
    all_functions = []
    for module in modules:
        relative_path = str(module.path.relative_to(project_root))
        for cls in module.classes:
            all_classes.append(
                {
                    "name": cls.name,
                    "file": relative_path,
                    "line": cls.line,
                    "bases": cls.bases,
                    "methods": len(cls.methods),
                    "decorators": cls.decorators,
                }
            )

        for func in module.functions:
            all_functions.append(
                {
                    "name": func.name,
                    "file": relative_path,
                    "line": func.line,
                    "is_async": func.is_async,
                    "decorators": func.decorators,
                }
            )

    # Build result
    result = {
        "project": {
            "name": project_name,
            "path": str(project_root),
            "type": project_type,
        },
        "framework": project_type,
        "frameworks": {"detected": sorted(frameworks), "primary": project_type},
        "structure": {
            "totalModules": len(modules),
            "totalClasses": len(all_classes),
            "totalFunctions": len(all_functions),
            "totalLines": total_lines,
        },
        "layers": layers,
    }

    if include_metrics:
        result["metrics"] = {
            "totalFiles": len(modules),
            "totalLines": total_lines,
            "avgComplexity": round(avg_complexity, 2),
            "maxComplexity": max_complexity,
            "avgLinesPerFile": round(total_lines / len(modules), 2) if modules else 0,
        }

    if include_detailed_metrics:
        result["detailedMetrics"] = file_metrics

    # Add top classes and functions
    if depth in ["detailed", "deep"]:
        result["topClasses"] = all_classes[:20]
        result["topFunctions"] = all_functions[:20]

    # Generate diagrams
    if generate_diagrams:
        result["diagram"] = DiagramGenerator.generate_architecture_diagram(result)
        if all_classes:
            result["classHierarchyDiagram"] = DiagramGenerator.generate_class_hierarchy(
                all_classes[:20]
            )

    # Generate memory suggestions
    if generate_memory_suggestions:
        result["memorySuggestions"] = _generate_memory_suggestions(
            result, file_metrics, project_name, frameworks
        )

    # Add recommendations
    recommendations = []
    if max_complexity > 50:
        recommendations.append(
            f"⚠️ Found files with very high complexity (max: {max_complexity}). "
            "Consider refactoring for better maintainability."
        )
    if avg_complexity > 15:
        recommendations.append(
            f"Average complexity is {avg_complexity:.1f}. "
            "Target < 10 for easier maintenance."
        )
    if len(modules) > 100 and not layers:
        recommendations.append(
            "Large project detected. Consider organizing into clear layers/packages."
        )

    if not recommendations:
        recommendations.append("✅ Project structure looks good!")

    result["recommendations"] = recommendations

    return [TextContent(type="text", text=json.dumps(result, indent=2))]


def _analyze_structure(modules: List[ModuleInfo], project_root: Path) -> List[Dict]:
    """Analyze project structure and identify layers."""
    layers_map: Dict[str, List[str]] = {}

    for module in modules:
        relative_path = module.path.relative_to(project_root)
        parts = list(relative_path.parts)

        if len(parts) > 1:
            layer_name = parts[0]
        else:
            layer_name = "root"

        if layer_name not in layers_map:
            layers_map[layer_name] = []

        layers_map[layer_name].append(str(relative_path))

    layers = []
    for layer_name, files in layers_map.items():
        layers.append(
            {"name": layer_name, "moduleCount": len(files), "files": files[:10]}
        )

    return sorted(layers, key=lambda x: x["moduleCount"], reverse=True)


def _generate_memory_suggestions(
    result: Dict, file_metrics: List[Dict], project_name: str, frameworks: set
) -> List[Dict]:
    """Generate memory suggestions for llm-memory MCP."""
    suggestions = []

    # High complexity files (committed scope)
    high_complexity_files = [f for f in file_metrics if f["complexity"] >= 20]
    if high_complexity_files:
        files_text = "\n".join(
            f"- {f['path']} (complexity: {f['complexity']}, {f['lines']} lines)"
            for f in high_complexity_files[:10]
        )

        suggestions.append(
            {
                "scope": "committed",
                "type": "insight",
                "title": f"High Complexity Files in {project_name}",
                "text": f"Critical refactoring targets:\n{files_text}\n\n"
                f"These files exceed complexity threshold of 20.",
                "tags": ["complexity", "refactoring", "technical-debt", "python"],
                "files": [f["path"] for f in high_complexity_files[:5]],
                "confidence": 0.9,
            }
        )

    # Architecture overview (local scope)
    suggestions.append(
        {
            "scope": "local",
            "type": "pattern",
            "title": f"{project_name} Architecture Pattern",
            "text": f"Framework: {result['framework']}\n"
            f"Project Type: {result['project']['type']}\n"
            f"Structure: {result['structure']['totalModules']} modules, "
            f"{result['structure']['totalClasses']} classes, "
            f"{result['structure']['totalFunctions']} functions\n\n"
            f"This project is organized with {len(result.get('layers', []))} layers.",
            "tags": ["architecture", "python", result["framework"], "overview"],
            "confidence": 0.95,
        }
    )

    # Framework patterns (global scope)
    for framework in list(frameworks)[:3]:
        patterns = FrameworkDetector.get_framework_specific_patterns(framework)
        if patterns:
            suggestions.append(
                {
                    "scope": "global",
                    "type": "pattern",
                    "title": f"{framework.title()} Common Patterns",
                    "text": f"{framework.title()} projects commonly use:\n"
                    + "\n".join(f"- {p}" for p in patterns[:5]),
                    "tags": [framework, "patterns", "python", "best-practices"],
                    "confidence": 0.85,
                }
            )

    return suggestions
