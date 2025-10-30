"""Context pack generator for AI-assisted development."""

import json
from pathlib import Path
from typing import Any, Dict, List, Sequence, Set

from mcp.types import TextContent

from ..utils.ast_parser import ASTParser
from ..utils.complexity_analyzer import ComplexityAnalyzer
from ..utils.file_scanner import FileScanner
from ..utils.framework_detector import FrameworkDetector


async def generate_context_pack(args: Dict[str, Any]) -> Sequence[TextContent]:
    """
    Generate optimized context packs for AI tools.

    Features:
    - Task-based file relevance scoring
    - Token budget management
    - Multiple output formats (markdown/json/xml)
    - Include architectural context
    - Dependency traversal
    - Git history integration
    """
    task = args["task"]
    project_path = args.get("project_path", ".")
    max_tokens = args.get("max_tokens", 50000)
    include_types = args.get("include_types", ["files", "arch"])
    format_type = args.get("format", "markdown")
    optimization_strategy = args.get("optimization_strategy", "relevance")
    focus_areas = args.get("focus_areas", [])
    include_line_numbers = args.get("include_line_numbers", False)

    project_root = Path(project_path).resolve()

    # Scan files
    files = FileScanner.scan_files(project_path)

    if not files:
        return [
            TextContent(
                type="text",
                text=json.dumps({"error": "No Python files found"}, indent=2),
            )
        ]

    # Detect frameworks
    frameworks = FrameworkDetector.detect_frameworks(files)

    # Analyze task to extract keywords
    task_analysis = _analyze_task(task, frameworks)

    # Score files by relevance
    scored_files = []
    for file_path in files:
        score = _calculate_relevance_score(
            file_path,
            project_root,
            task_analysis,
            focus_areas,
            optimization_strategy,
        )
        if score > 0:
            scored_files.append({"path": file_path, "score": score})

    # Sort by relevance
    scored_files.sort(key=lambda x: x["score"], reverse=True)

    # Apply token budget
    selected_files = []
    token_count = 0
    estimated_token_per_line = 4  # Rough estimate

    for item in scored_files:
        file_path = item["path"]
        try:
            lines = len(file_path.read_text(encoding="utf-8").splitlines())
            estimated_tokens = lines * estimated_token_per_line

            if token_count + estimated_tokens <= max_tokens:
                selected_files.append({
                    "path": file_path,
                    "score": item["score"],
                    "lines": lines,
                    "estimated_tokens": estimated_tokens,
                })
                token_count += estimated_tokens
            else:
                break
        except Exception:
            pass

    # Build context pack
    context_pack = {
        "task": task,
        "taskAnalysis": task_analysis,
        "strategy": optimization_strategy,
        "tokenBudget": {
            "max": max_tokens,
            "used": token_count,
            "remaining": max_tokens - token_count,
        },
        "files": [],
        "relatedTests": [],
        "patterns": [],
        "suggestions": _generate_context_suggestions(task_analysis, frameworks, selected_files),
    }

    # Include file contents based on strategy
    for item in selected_files[:20]:  # Limit to top 20 files
        file_path = item["path"]
        relative_path = str(file_path.relative_to(project_root))

        try:
            content = file_path.read_text(encoding="utf-8")
            module_info = ASTParser.parse_file(file_path)

            file_info = {
                "path": relative_path,
                "relevance": round(item["score"], 2),
                "lines": item["lines"],
                "summary": _generate_file_summary(module_info) if module_info else None,
            }

            # Include content for highly relevant files
            if item["score"] >= 0.7 and "files" in include_types:
                if include_line_numbers:
                    numbered_lines = [
                        f"{i+1:4d} | {line}"
                        for i, line in enumerate(content.splitlines())
                    ]
                    file_info["content"] = "\n".join(numbered_lines)
                else:
                    file_info["content"] = content

            context_pack["files"].append(file_info)

        except Exception:
            pass

    # Include architectural context
    if "arch" in include_types:
        context_pack["architecture"] = {
            "frameworks": sorted(frameworks),
            "projectType": FrameworkDetector.detect_project_type(frameworks),
            "layers": _identify_layers(selected_files, project_root),
        }

    # Format output
    if format_type == "markdown":
        formatted = _format_as_markdown(context_pack, include_line_numbers)
        return [TextContent(type="text", text=formatted)]
    elif format_type == "xml":
        formatted = _format_as_xml(context_pack)
        return [TextContent(type="text", text=formatted)]
    else:
        return [TextContent(type="text", text=json.dumps(context_pack, indent=2))]


def _analyze_task(task: str, frameworks: Set[str]) -> Dict:
    """Analyze task to extract keywords and concepts."""
    task_lower = task.lower()

    # Determine task type
    task_type = "feature"
    if any(word in task_lower for word in ["fix", "bug", "error", "issue"]):
        task_type = "bugfix"
    elif any(word in task_lower for word in ["refactor", "improve", "optimize"]):
        task_type = "refactoring"
    elif any(word in task_lower for word in ["test", "coverage"]):
        task_type = "testing"

    # Extract keywords
    keywords = []

    # Data science keywords
    data_keywords = [
        "dataframe", "pandas", "numpy", "array", "csv", "excel",
        "plot", "visualize", "chart", "graph", "matplotlib", "seaborn",
        "model", "train", "predict", "sklearn", "machine learning", "ml",
        "pipeline", "transform", "feature", "data cleaning", "preprocessing",
    ]

    for keyword in data_keywords:
        if keyword in task_lower:
            keywords.append(keyword)

    # API keywords
    api_keywords = ["api", "endpoint", "route", "request", "response", "fastapi", "django", "flask"]
    for keyword in api_keywords:
        if keyword in task_lower:
            keywords.append(keyword)

    # Domain concepts
    domain_concepts = []
    if "pandas" in frameworks or "numpy" in frameworks:
        domain_concepts.append("data-analysis")
    if "sklearn" in frameworks:
        domain_concepts.append("machine-learning")
    if any(fw in frameworks for fw in ["fastapi", "django", "flask"]):
        domain_concepts.append("web-api")

    # Framework concepts
    framework_concepts = list(frameworks)

    return {
        "type": task_type,
        "keywords": list(set(keywords)),
        "domainConcepts": domain_concepts,
        "frameworkConcepts": framework_concepts,
    }


def _calculate_relevance_score(
    file_path: Path,
    project_root: Path,
    task_analysis: Dict,
    focus_areas: List[str],
    strategy: str,
) -> float:
    """Calculate relevance score for a file."""
    relative_path = str(file_path.relative_to(project_root))
    score = 0.0

    # Check focus areas (highest priority)
    if focus_areas:
        for area in focus_areas:
            if area in relative_path:
                score += 1.0
                break

    # Check task keywords in file path
    keywords = task_analysis.get("keywords", [])
    path_lower = relative_path.lower()

    for keyword in keywords:
        if keyword.replace(" ", "_") in path_lower or keyword.replace(" ", "") in path_lower:
            score += 0.5

    # Check domain concepts
    domain_concepts = task_analysis.get("domainConcepts", [])
    if "data-analysis" in domain_concepts:
        if any(x in path_lower for x in ["data", "analysis", "preprocessing", "etl"]):
            score += 0.3
    if "machine-learning" in domain_concepts:
        if any(x in path_lower for x in ["model", "train", "predict", "ml", "feature"]):
            score += 0.3
    if "web-api" in domain_concepts:
        if any(x in path_lower for x in ["api", "view", "endpoint", "route", "handler"]):
            score += 0.3

    # Strategy-based adjustments
    if strategy == "breadth":
        # Include more diverse files
        if "util" in path_lower or "helper" in path_lower:
            score += 0.2
    elif strategy == "depth":
        # Focus on core files
        if "core" in path_lower or "main" in path_lower or "__init__" in path_lower:
            score += 0.3

    # Boost for core files
    if any(x in path_lower for x in ["utils", "lib", "core"]):
        score += 0.1

    return min(score, 1.0)


def _generate_file_summary(module_info) -> Dict:
    """Generate summary for a file."""
    return {
        "classes": len(module_info.classes),
        "functions": len(module_info.functions),
        "lines": module_info.lines,
        "imports": len(module_info.imports),
        "hasDocstring": bool(module_info.docstring),
    }


def _identify_layers(selected_files: List[Dict], project_root: Path) -> List[str]:
    """Identify architectural layers from selected files."""
    layers = set()

    for item in selected_files:
        file_path = item["path"]
        relative = file_path.relative_to(project_root)

        if len(relative.parts) > 1:
            layers.add(relative.parts[0])

    return sorted(layers)


def _generate_context_suggestions(
    task_analysis: Dict, frameworks: Set[str], selected_files: List[Dict]
) -> List[str]:
    """Generate suggestions for context usage."""
    suggestions = []

    task_type = task_analysis.get("type")
    keywords = task_analysis.get("keywords", [])

    # Type-specific suggestions
    if task_type == "feature":
        suggestions.append(
            "Consider following existing code patterns in similar features"
        )

    if task_type == "bugfix":
        suggestions.append(
            "Review related test files and look for edge cases"
        )

    if task_type == "refactoring":
        suggestions.append(
            "Ensure backward compatibility and update related tests"
        )

    # Framework-specific suggestions
    if "pandas" in frameworks and any("dataframe" in k for k in keywords):
        suggestions.append(
            "Use vectorized operations instead of loops for better performance"
        )

    if "sklearn" in frameworks:
        suggestions.append(
            "Consider using sklearn Pipeline for reproducible workflows"
        )

    if any(fw in frameworks for fw in ["fastapi", "django", "flask"]):
        suggestions.append(
            "Follow RESTful API best practices and proper error handling"
        )

    # File count suggestions
    if len(selected_files) < 5:
        suggestions.append(
            "Limited context available - consider broader search terms"
        )
    elif len(selected_files) > 15:
        suggestions.append(
            "Large context - focus on most relevant files first"
        )

    return suggestions


def _format_as_markdown(context_pack: Dict, include_line_numbers: bool) -> str:
    """Format context pack as Markdown."""
    lines = []

    # Header
    lines.append(f"# AI Context Pack: {context_pack['task']}")
    lines.append("")

    # Task Analysis
    lines.append("## Task Analysis")
    lines.append("")
    task_analysis = context_pack["taskAnalysis"]
    lines.append(f"- **Type**: {task_analysis['type']}")
    lines.append(f"- **Keywords**: {', '.join(task_analysis['keywords']) if task_analysis['keywords'] else 'none'}")
    lines.append(f"- **Domain**: {', '.join(task_analysis['domainConcepts']) if task_analysis['domainConcepts'] else 'general'}")
    lines.append(f"- **Strategy**: {context_pack['strategy']}")
    lines.append("")

    # Token Budget
    budget = context_pack["tokenBudget"]
    lines.append("## Token Budget")
    lines.append("")
    lines.append(f"- Max: {budget['max']:,}")
    lines.append(f"- Used: {budget['used']:,}")
    lines.append(f"- Remaining: {budget['remaining']:,}")
    lines.append("")

    # Architecture
    if "architecture" in context_pack:
        arch = context_pack["architecture"]
        lines.append("## Architecture")
        lines.append("")
        lines.append(f"- **Type**: {arch['projectType']}")
        lines.append(f"- **Frameworks**: {', '.join(arch['frameworks'])}")
        lines.append(f"- **Layers**: {', '.join(arch['layers'])}")
        lines.append("")

    # Files
    lines.append("## Relevant Files")
    lines.append("")

    for file_info in context_pack["files"]:
        lines.append(f"### {file_info['path']}")
        lines.append("")
        lines.append(f"**Relevance**: {file_info['relevance']} | **Lines**: {file_info['lines']}")
        lines.append("")

        if file_info.get("summary"):
            summary = file_info["summary"]
            lines.append(f"- Classes: {summary['classes']}")
            lines.append(f"- Functions: {summary['functions']}")
            lines.append(f"- Imports: {summary['imports']}")
            lines.append("")

        if file_info.get("content"):
            lines.append("```python")
            lines.append(file_info["content"])
            lines.append("```")
            lines.append("")

    # Suggestions
    if context_pack.get("suggestions"):
        lines.append("## Suggestions")
        lines.append("")
        for suggestion in context_pack["suggestions"]:
            lines.append(f"- {suggestion}")
        lines.append("")

    return "\n".join(lines)


def _format_as_xml(context_pack: Dict) -> str:
    """Format context pack as XML."""
    lines = []
    lines.append('<?xml version="1.0" encoding="UTF-8"?>')
    lines.append(f'<contextPack task="{context_pack["task"]}">')
    lines.append(f'  <strategy>{context_pack["strategy"]}</strategy>')

    # Token budget
    budget = context_pack["tokenBudget"]
    lines.append(f'  <tokenBudget max="{budget["max"]}" used="{budget["used"]}" remaining="{budget["remaining"]}" />')

    # Files
    lines.append('  <files>')
    for file_info in context_pack["files"]:
        lines.append(f'    <file path="{file_info["path"]}" relevance="{file_info["relevance"]}" lines="{file_info["lines"]}">')
        if file_info.get("content"):
            lines.append(f'      <content><![CDATA[{file_info["content"]}]]></content>')
        lines.append('    </file>')
    lines.append('  </files>')

    lines.append('</contextPack>')
    return "\n".join(lines)
