#!/usr/bin/env python3
"""
Code Analysis & Context Engineering MCP Server

Provides deep codebase understanding for Python projects with focus on data analysis frameworks.
"""

import asyncio
import logging
from typing import Any, Sequence

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

# Tool imports
from .tools.architecture_analyzer import analyze_architecture
from .tools.pattern_detector import analyze_patterns
from .tools.dependency_mapper import analyze_dependency_graph
from .tools.coverage_analyzer import analyze_coverage_gaps
from .tools.convention_validator import validate_conventions
from .tools.context_pack_generator import generate_context_pack

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Tool definitions
TOOLS: list[Tool] = [
    Tool(
        name="arch",
        description="Analyze architecture, modules, patterns. Supports pandas/numpy/sklearn/fastapi/django",
        inputSchema={
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Project root"},
                "inc": {"type": "array", "items": {"type": "string"}, "description": "Include globs"},
                "exc": {"type": "array", "items": {"type": "string"}, "description": "Exclude globs"},
                "depth": {"type": "string", "enum": ["o", "d", "x"], "description": "overview/detailed/deep"},
                "types": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": ["mod", "class", "func", "api", "model", "view", "notebook", "pipeline", "dataflow"],
                    },
                    "description": "Analysis types",
                },
                "diagrams": {"type": "boolean", "description": "Mermaid diagrams"},
                "metrics": {"type": "boolean", "description": "Code metrics"},
                "details": {"type": "boolean", "description": "Per-file metrics"},
                "minCx": {"type": "number", "description": "Min complexity filter"},
                "maxFiles": {"type": "number", "description": "Max files in details"},
                "memSuggest": {"type": "boolean", "description": "LLM memory suggestions"},
                "autoFw": {"type": "boolean", "description": "Auto-detect framework"},
                "fw": {"type": "string", "enum": ["pandas", "numpy", "sklearn", "fastapi", "django", "flask", "jupyter"], "description": "Force framework"},
            },
        },
    ),
    Tool(
        name="deps",
        description="Dependency graph, circular deps, coupling metrics",
        inputSchema={
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Project root"},
                "inc": {"type": "array", "items": {"type": "string"}, "description": "Include globs"},
                "exc": {"type": "array", "items": {"type": "string"}, "description": "Exclude globs"},
                "depth": {"type": "number", "description": "Max depth"},
                "circular": {"type": "boolean", "description": "Detect circular"},
                "metrics": {"type": "boolean", "description": "Coupling/cohesion"},
                "diagram": {"type": "boolean", "description": "Mermaid diagram"},
                "focus": {"type": "string", "description": "Focus on module"},
                "external": {"type": "boolean", "description": "Include site-packages"},
            },
        },
    ),
    Tool(
        name="patterns",
        description="Detect data analysis patterns, best practices",
        inputSchema={
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Project root"},
                "types": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": ["dataframe", "array", "pipeline", "model", "viz", "api", "orm", "async", "decorator", "context"],
                    },
                    "description": "Pattern types",
                },
                "inc": {"type": "array", "items": {"type": "string"}, "description": "Include globs"},
                "exc": {"type": "array", "items": {"type": "string"}, "description": "Exclude globs"},
                "custom": {"type": "boolean", "description": "Custom patterns"},
                "best": {"type": "boolean", "description": "Compare best practices"},
                "suggest": {"type": "boolean", "description": "Improvement suggestions"},
            },
        },
    ),
    Tool(
        name="coverage",
        description="Test coverage gaps, actionable suggestions",
        inputSchema={
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Project root"},
                "report": {"type": "string", "description": "Coverage report path"},
                "fw": {"type": "string", "enum": ["pytest", "unittest", "nose"], "description": "Test framework"},
                "threshold": {
                    "type": "object",
                    "properties": {
                        "lines": {"type": "number"},
                        "functions": {"type": "number"},
                        "branches": {"type": "number"},
                        "statements": {"type": "number"},
                    },
                    "description": "Min thresholds",
                },
                "priority": {"type": "string", "enum": ["crit", "high", "med", "low", "all"], "description": "Filter priority"},
                "inc": {"type": "array", "items": {"type": "string"}, "description": "Include globs"},
                "exc": {"type": "array", "items": {"type": "string"}, "description": "Exclude globs"},
                "tests": {"type": "boolean", "description": "Generate scaffolds"},
                "cx": {"type": "boolean", "description": "Analyze complexity"},
            },
        },
    ),
    Tool(
        name="conventions",
        description="Validate naming, structure, code conventions (PEP 8)",
        inputSchema={
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Project root"},
                "rules": {"type": "object", "description": "Convention rules"},
                "auto": {"type": "boolean", "description": "Auto-detect conventions"},
                "inc": {"type": "array", "items": {"type": "string"}, "description": "Include globs"},
                "exc": {"type": "array", "items": {"type": "string"}, "description": "Exclude globs"},
                "severity": {"type": "string", "enum": ["err", "warn", "info"], "description": "Min severity"},
            },
        },
    ),
    Tool(
        name="context",
        description="Build AI context pack for task",
        inputSchema={
            "type": "object",
            "properties": {
                "task": {"type": "string", "description": "Task description"},
                "path": {"type": "string", "description": "Project root"},
                "tokens": {"type": "number", "description": "Token budget"},
                "include": {
                    "type": "array",
                    "items": {"type": "string", "enum": ["files", "deps", "tests", "types", "arch", "conv", "notebooks"]},
                    "description": "Content types",
                },
                "focus": {"type": "array", "items": {"type": "string"}, "description": "Priority files/dirs"},
                "history": {"type": "boolean", "description": "Git changes"},
                "format": {"type": "string", "enum": ["md", "json", "xml"], "description": "Output format"},
                "lineNums": {"type": "boolean", "description": "Line numbers"},
                "strategy": {"type": "string", "enum": ["rel", "wide", "deep"], "description": "Optimization strategy"},
            },
            "required": ["task"],
        },
    ),
]


def map_params(tool: str, args: dict[str, Any]) -> dict[str, Any]:
    """Map short parameter names to long names for internal use."""
    if not args:
        return {}

    mapped: dict[str, Any] = {}

    # Common mappings
    if "path" in args:
        mapped["project_path"] = args["path"]
    if "inc" in args:
        mapped["include_globs"] = args["inc"]
    if "exc" in args:
        mapped["exclude_globs"] = args["exc"]

    # Tool-specific mappings
    if tool == "arch":
        if "depth" in args:
            mapped["depth"] = {"o": "overview", "d": "detailed", "x": "deep"}[args["depth"]]
        if "types" in args:
            mapped["analyze_types"] = args["types"]
        if "diagrams" in args:
            mapped["generate_diagrams"] = args["diagrams"]
        if "metrics" in args:
            mapped["include_metrics"] = args["metrics"]
        if "details" in args:
            mapped["include_detailed_metrics"] = args["details"]
        if "minCx" in args:
            mapped["min_complexity"] = args["minCx"]
        if "maxFiles" in args:
            mapped["max_detailed_files"] = args["maxFiles"]
        if "memSuggest" in args:
            mapped["generate_memory_suggestions"] = args["memSuggest"]
        if "autoFw" in args:
            mapped["detect_framework"] = args["autoFw"]
        if "fw" in args:
            mapped["framework"] = args["fw"]

    elif tool == "deps":
        if "depth" in args:
            mapped["depth"] = args["depth"]
        if "circular" in args:
            mapped["detect_circular"] = args["circular"]
        if "metrics" in args:
            mapped["calculate_metrics"] = args["metrics"]
        if "diagram" in args:
            mapped["generate_diagram"] = args["diagram"]
        if "focus" in args:
            mapped["focus_module"] = args["focus"]
        if "external" in args:
            mapped["include_external"] = args["external"]

    elif tool == "patterns":
        if "types" in args:
            mapped["pattern_types"] = args["types"]
        if "custom" in args:
            mapped["detect_custom_patterns"] = args["custom"]
        if "best" in args:
            mapped["compare_with_best_practices"] = args["best"]
        if "suggest" in args:
            mapped["suggest_improvements"] = args["suggest"]

    elif tool == "coverage":
        if "report" in args:
            mapped["coverage_report_path"] = args["report"]
        if "fw" in args:
            mapped["framework"] = args["fw"]
        if "threshold" in args:
            mapped["threshold"] = args["threshold"]
        if "priority" in args:
            p = args["priority"]
            mapped["priority"] = {"crit": "critical", "med": "medium"}.get(p, p)
        if "tests" in args:
            mapped["suggest_tests"] = args["tests"]
        if "cx" in args:
            mapped["analyze_complexity"] = args["cx"]

    elif tool == "conventions":
        if "rules" in args:
            mapped["conventions"] = args["rules"]
        if "auto" in args:
            mapped["autodetect_conventions"] = args["auto"]
        if "severity" in args:
            s = args["severity"]
            mapped["severity"] = {"err": "error", "warn": "warning"}.get(s, s)

    elif tool == "context":
        if "task" in args:
            mapped["task"] = args["task"]
        if "tokens" in args:
            mapped["max_tokens"] = args["tokens"]
        if "include" in args:
            mapped["include_types"] = args["include"]
        if "focus" in args:
            mapped["focus_areas"] = args["focus"]
        if "history" in args:
            mapped["include_history"] = args["history"]
        if "format" in args:
            f = args["format"]
            mapped["format"] = "markdown" if f == "md" else f
        if "lineNums" in args:
            mapped["include_line_numbers"] = args["lineNums"]
        if "strategy" in args:
            st = args["strategy"]
            mapped["optimization_strategy"] = {"rel": "relevance", "wide": "breadth", "deep": "depth"}.get(st, st)

    return mapped


async def call_tool(name: str, arguments: dict[str, Any]) -> Sequence[TextContent]:
    """Call the appropriate tool based on name."""
    try:
        mapped_args = map_params(name, arguments)

        if name == "arch":
            result = await analyze_architecture(mapped_args)
        elif name == "deps":
            result = await analyze_dependency_graph(mapped_args)
        elif name == "patterns":
            result = await analyze_patterns(mapped_args)
        elif name == "coverage":
            result = await analyze_coverage_gaps(mapped_args)
        elif name == "conventions":
            result = await validate_conventions(mapped_args)
        elif name == "context":
            result = await generate_context_pack(mapped_args)
        else:
            raise ValueError(f"Unknown tool: {name}")

        return result

    except Exception as e:
        logger.error(f"Error executing {name}: {str(e)}", exc_info=True)
        return [TextContent(
            type="text",
            text=f"Error executing {name}: {str(e)}"
        )]


async def main() -> None:
    """Main entry point for the MCP server."""
    logger.info("Starting Code Analysis Python MCP Server v0.1.0")

    # Create server instance
    server = Server("code-analysis-context-python-mcp")

    # Register tool list handler
    @server.list_tools()
    async def list_tools() -> list[Tool]:
        return TOOLS

    # Register tool call handler
    @server.call_tool()
    async def handle_call_tool(name: str, arguments: dict[str, Any]) -> Sequence[TextContent]:
        return await call_tool(name, arguments)

    # Run the server
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options()
        )


if __name__ == "__main__":
    asyncio.run(main())
