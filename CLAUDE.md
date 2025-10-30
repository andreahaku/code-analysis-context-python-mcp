# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an **MCP (Model Context Protocol) server** that provides deep codebase analysis for Python projects, specifically designed for data analysis engineers working with pandas, numpy, sklearn, fastapi, django, and other Python frameworks.

The server exposes 6 analysis tools via the MCP protocol. It's a complete, production-ready implementation with 3,787 lines of code across 18 modules.

## Development Commands

### Setup & Installation
```bash
# Development installation with all dependencies
pip install -e ".[dev]"

# Install only runtime dependencies
pip install -e .
```

### Running & Testing
```bash
# Test the MCP server by analyzing itself
python3 test_tools.py

# Run the MCP server (for use with Claude Desktop or other MCP clients)
python3 -m src.server

# Or use the installed script
code-analysis-python-mcp
```

### Code Quality
```bash
# Format code (100 char line length)
black src tests
isort src tests

# Linting
flake8 src tests

# Type checking (strict mode enabled in pyproject.toml)
mypy src

# Run tests with coverage
pytest --cov=src --cov-report=html --cov-report=term
```

## Architecture Overview

### High-Level Design

**MCP Server Pattern**: The architecture follows a clear separation between the MCP protocol layer and analysis logic:

1. **`src/server.py`** - MCP protocol handler
   - Defines 6 Tool schemas with short parameter names (e.g., `path`, `inc`, `exc`)
   - Maps short params to long params via `map_params()` function
   - Routes tool calls to appropriate analyzers
   - All tools are async functions returning `Sequence[TextContent]`

2. **`src/tools/`** - 6 independent analysis tools (each ~300-500 LOC)
   - Each tool is a standalone async function accepting a dict of long-form params
   - Tools return JSON results wrapped in TextContent
   - No shared state between tools

3. **`src/utils/`** - Reusable analysis utilities
   - **`ast_parser.py`**: Parses Python files using `ast` module, extracts classes/functions/imports
   - **`complexity_analyzer.py`**: Uses `radon` library for cyclomatic complexity, maintainability index
   - **`file_scanner.py`**: Glob-based file discovery with include/exclude patterns
   - **`framework_detector.py`**: Detects 14+ frameworks by analyzing imports
   - **`diagram_generator.py`**: Creates Mermaid diagrams for architecture and dependencies

4. **`src/analyzers/`** - Framework-specific analyzers (currently empty, ready for extension)

### Parameter Mapping Convention

The MCP layer uses **short parameter names** for token efficiency:
- `path` → `project_path`
- `inc` → `include_globs`
- `exc` → `exclude_globs`
- `fw` → `framework`
- `cx` → complexity
- `memSuggest` → `generate_memory_suggestions`

The `map_params()` function in `src/server.py` handles all conversions before calling tools.

### Tool Implementation Pattern

Each tool follows this structure:
```python
async def analyze_something(args: Dict[str, Any]) -> Sequence[TextContent]:
    # 1. Extract parameters
    project_path = args.get("project_path", ".")

    # 2. Scan files using FileScanner
    files = FileScanner.scan_files(project_path, include_globs, exclude_globs)

    # 3. Parse files using ASTParser or analyze with specific utilities
    for file_path in files:
        module_info = ASTParser.parse_file(file_path)
        complexity = ComplexityAnalyzer.analyze_file(file_path)

    # 4. Build result dict
    result = {"project": {...}, "summary": {...}, "details": [...]}

    # 5. Return as JSON text
    return [TextContent(type="text", text=json.dumps(result, indent=2))]
```

### Key Dependencies & Their Roles

- **`astroid`**: Enhanced AST parsing (used in `ast_parser.py`)
- **`radon`**: Cyclomatic complexity and maintainability metrics
- **`networkx`**: Dependency graph construction and circular detection
- **`mcp`**: Official MCP SDK for protocol implementation

### Data Flow

1. MCP Client calls tool (e.g., `arch`) with short params
2. `server.py` validates params, maps to long names
3. Tool function uses utilities to scan/parse/analyze files
4. Results aggregated into structured dict
5. Dict serialized to JSON and returned as TextContent
6. MCP client receives and displays results

## Important Implementation Details

### AST Parsing Strategy
The `ASTParser` class returns `ModuleInfo` dataclasses containing:
- Classes (name, line, bases, decorators, methods, docstring)
- Functions (name, line, is_async, is_method, decorators, args, returns, docstring)
- Imports (module, names, is_from, line)
- Constants (module-level UPPER_CASE variables)

Error handling: Files with syntax errors or encoding issues are silently skipped.

### Complexity Analysis
Uses Radon's `cc_visit()` for cyclomatic complexity and returns:
- Total/average/max complexity per file
- Per-function complexity with A-F ranking (A=1-5, B=6-10, C=11-20, D=21-30, F=31+)
- Maintainability index (0-100, higher is better)
- Halstead metrics (volume, difficulty)

### Framework Detection
Pattern matching on import statements. Supports:
- Data: pandas, numpy, sklearn, scipy, plotly
- Web: fastapi, django, flask, streamlit
- ML: tensorflow, pytorch
- Notebooks: jupyter, ipython

Framework detection drives context-aware analysis in other tools.

### Circular Dependency Detection
Uses NetworkX's `simple_cycles()` to find all circular import paths. Each cycle includes:
- Full path (list of module names forming the cycle)
- Length (number of modules in cycle)
- Severity (critical if ≤3 modules, warning otherwise)

### Coverage Analysis Priority System
Prioritizes files for testing based on:
- **Critical**: Core files (utils/lib/core) with no coverage + high complexity (>30)
- **High**: Important files (api/views) with <50% coverage OR complexity >50
- **Medium**: Below threshold
- **Low**: Everything else

Location detection uses path string matching (case-insensitive).

### Context Pack Generation
Task-based relevance scoring algorithm:
1. Parse task description to extract keywords
2. Score each file based on:
   - Focus areas (score += 1.0)
   - Keyword matches in path (score += 0.5 per match)
   - Domain concepts (data-analysis/ML/web-api) (score += 0.3)
   - Strategy adjustments (breadth/depth/relevance)
3. Sort by score, apply token budget
4. Include top files with optional content embedding

Supports multiple output formats (JSON/Markdown/XML) with line numbers.

## Testing This Project

The `test_tools.py` script demonstrates all 6 tools by analyzing this codebase itself. It's both a test suite and a usage example.

Expected results when running on this project:
- 18 modules, 9 classes, 61 functions, 3,787 lines
- 38 patterns (17 async, 21 decorators)
- 0 circular dependencies
- Average complexity: 36.8 (identifies itself as needing refactoring!)
- 100% naming consistency (follows PEP 8)

## Adding New Tools

To add a new MCP tool:
1. Add Tool schema to `TOOLS` list in `src/server.py`
2. Add mapping logic in `map_params()` function
3. Create tool function in `src/tools/your_tool.py`
4. Import and route in `call_tool()` function
5. Tool must be async and return `Sequence[TextContent]`

## Configuration File Support

Projects being analyzed can include `.code-analysis.json` with:
- Custom include/exclude globs
- Naming conventions
- Coverage thresholds
- Framework hints

This file is not currently parsed by the tools (future enhancement).
