"""Coverage analyzer for Python projects."""

import json
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Dict, List, Sequence, Optional

from mcp.types import TextContent

from ..utils.ast_parser import ASTParser
from ..utils.complexity_analyzer import ComplexityAnalyzer
from ..utils.file_scanner import FileScanner


async def analyze_coverage_gaps(args: Dict[str, Any]) -> Sequence[TextContent]:
    """
    Analyze test coverage using coverage.py reports.

    Features:
    - Parse .coverage database or coverage.xml
    - Identify untested modules and functions
    - Priority-based gap ranking
    - Test scaffold generation (pytest/unittest)
    - Complexity-based prioritization
    """
    project_path = args.get("project_path", ".")
    coverage_report_path = args.get("coverage_report_path")
    framework = args.get("framework", "pytest")
    threshold = args.get("threshold", {"lines": 80, "functions": 80, "branches": 75})
    priority = args.get("priority", "all")
    suggest_tests = args.get("suggest_tests", False)
    analyze_complexity = args.get("analyze_complexity", True)
    include_globs = args.get("include_globs", ["**/*.py"])
    exclude_globs = args.get("exclude_globs", ["**/test_*.py", "**/*_test.py"])

    project_root = Path(project_path).resolve()

    # Scan for Python files
    files = FileScanner.scan_files(project_path, include_globs, exclude_globs)

    if not files:
        return [
            TextContent(
                type="text",
                text=json.dumps({"error": "No Python files found"}, indent=2),
            )
        ]

    # Parse coverage report if provided
    coverage_data = {}
    if coverage_report_path:
        coverage_data = _parse_coverage_report(
            Path(coverage_report_path), project_root
        )

    # Analyze each file
    gaps = []
    tested_files = 0
    untested_files = 0
    total_lines_covered = 0
    total_lines = 0

    for file_path in files:
        relative_path = str(file_path.relative_to(project_root))

        # Get coverage for this file
        file_coverage = coverage_data.get(relative_path, {
            "lines_covered": 0,
            "lines_total": 0,
            "line_rate": 0,
            "uncovered_lines": []
        })

        # Parse file for complexity
        module_info = ASTParser.parse_file(file_path)
        if not module_info:
            continue

        complexity_data = ComplexityAnalyzer.analyze_file(file_path)

        # Calculate coverage percentages
        lines_total = file_coverage.get("lines_total", module_info.lines)
        lines_covered = file_coverage.get("lines_covered", 0)
        line_rate = file_coverage.get("line_rate", 0)

        total_lines += lines_total
        total_lines_covered += lines_covered

        if line_rate > 0:
            tested_files += 1
        else:
            untested_files += 1

        # Determine priority
        file_priority = _calculate_priority(
            line_rate,
            threshold,
            complexity_data,
            relative_path,
            analyze_complexity,
        )

        # Check if below threshold
        below_threshold = line_rate < threshold.get("lines", 80) / 100

        if below_threshold or line_rate == 0:
            gap = {
                "file": relative_path,
                "priority": file_priority,
                "coverage": {
                    "lines": round(line_rate * 100, 1),
                    "lines_covered": lines_covered,
                    "lines_total": lines_total,
                },
                "complexity": complexity_data.get("totalComplexity", 0),
                "maintainability": complexity_data.get("maintainabilityIndex", 100),
                "uncovered_lines": file_coverage.get("uncovered_lines", []),
                "reasons": _generate_reasons(
                    line_rate, threshold, complexity_data, relative_path
                ),
            }

            # Add untested functions
            gap["untestedFunctions"] = [
                {"name": func["name"], "complexity": func["complexity"], "line": func["line"]}
                for func in complexity_data.get("functions", [])
            ]

            # Generate test suggestions
            if suggest_tests:
                gap["testSuggestions"] = _generate_test_scaffolds(
                    file_path,
                    module_info,
                    framework,
                    relative_path,
                    file_priority,
                )

            gaps.append(gap)

    # Filter by priority
    if priority != "all":
        gaps = [g for g in gaps if g["priority"] == priority]

    # Sort by priority and complexity
    priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    gaps.sort(key=lambda x: (priority_order.get(x["priority"], 4), -x["complexity"]))

    # Calculate overall coverage
    overall_coverage = (
        round(total_lines_covered / total_lines * 100, 1) if total_lines > 0 else 0
    )

    # Build result
    result = {
        "project": {
            "name": project_root.name,
            "totalFiles": len(files),
            "framework": framework,
        },
        "summary": {
            "overallCoverage": {
                "lines": overall_coverage,
            },
            "testedFiles": tested_files,
            "untestedFiles": untested_files,
            "partiallyTestedFiles": len(gaps),
        },
        "threshold": threshold,
        "gaps": gaps[:50],  # Limit to top 50
        "criticalGaps": [g for g in gaps if g["priority"] == "critical"][:10],
        "recommendations": _generate_recommendations(
            gaps, overall_coverage, threshold, tested_files, untested_files
        ),
    }

    return [TextContent(type="text", text=json.dumps(result, indent=2))]


def _parse_coverage_report(
    report_path: Path, project_root: Path
) -> Dict[str, Dict]:
    """Parse coverage report (XML format)."""
    coverage_data = {}

    if not report_path.exists():
        return coverage_data

    try:
        # Try XML format (coverage.xml)
        if report_path.suffix == ".xml":
            tree = ET.parse(report_path)
            root = tree.getroot()

            for package in root.findall(".//package"):
                for cls in package.findall("classes/class"):
                    filename = cls.get("filename", "")
                    line_rate = float(cls.get("line-rate", 0))

                    # Get covered and total lines
                    lines = cls.findall("lines/line")
                    lines_total = len(lines)
                    lines_covered = sum(1 for line in lines if line.get("hits", "0") != "0")

                    # Get uncovered lines
                    uncovered_lines = [
                        int(line.get("number", 0))
                        for line in lines
                        if line.get("hits", "0") == "0"
                    ]

                    coverage_data[filename] = {
                        "lines_covered": lines_covered,
                        "lines_total": lines_total,
                        "line_rate": line_rate,
                        "uncovered_lines": uncovered_lines,
                    }

    except Exception as e:
        # Could not parse coverage report
        pass

    return coverage_data


def _calculate_priority(
    line_rate: float,
    threshold: Dict,
    complexity_data: Dict,
    file_path: str,
    analyze_complexity: bool,
) -> str:
    """Calculate priority based on coverage and complexity."""
    complexity = complexity_data.get("totalComplexity", 0)

    # Determine criticality based on file location
    path_lower = file_path.lower()
    is_core = any(x in path_lower for x in ["utils", "lib", "core", "services", "models"])
    is_important = any(x in path_lower for x in ["api", "views", "handlers"])

    # Critical: core files with no coverage or very high complexity
    if is_core and line_rate == 0 and complexity > 30:
        return "critical"
    if is_core and line_rate < threshold.get("lines", 80) / 100:
        return "critical"

    # High: important files with low coverage or high complexity
    if is_important and line_rate < 0.5:
        return "high"
    if complexity > 50 and line_rate < 0.5:
        return "high"

    # Medium: below threshold
    if line_rate < threshold.get("lines", 80) / 100:
        return "medium"

    # Low: everything else
    return "low"


def _generate_reasons(
    line_rate: float, threshold: Dict, complexity_data: Dict, file_path: str
) -> List[str]:
    """Generate reasons for coverage gap."""
    reasons = []

    if line_rate == 0:
        reasons.append("No test coverage")
    elif line_rate < threshold.get("lines", 80) / 100:
        target = threshold.get("lines", 80)
        current = round(line_rate * 100, 1)
        reasons.append(
            f"Line coverage {current}% below threshold {target}%"
        )

    # Check complexity
    complexity = complexity_data.get("totalComplexity", 0)
    if complexity > 50:
        reasons.append(f"Very high complexity ({complexity}) - error-prone")
    elif complexity > 30:
        reasons.append(f"High complexity ({complexity}) - needs testing")

    # Check file location
    path_lower = file_path.lower()
    if "util" in path_lower or "lib" in path_lower or "core" in path_lower:
        reasons.append("Core utility - high impact if bugs present")
    elif "api" in path_lower or "view" in path_lower:
        reasons.append("API/View layer - user-facing")

    return reasons


def _generate_test_scaffolds(
    file_path: Path,
    module_info,
    framework: str,
    relative_path: str,
    priority: str,
) -> List[Dict]:
    """Generate test scaffolds for untested code."""
    suggestions = []

    # Determine test file path
    test_file_path = _get_test_file_path(relative_path, framework)

    # Generate scaffold based on file type
    if module_info.classes:
        # Class-based tests
        scaffold = _generate_class_test_scaffold(
            module_info.classes[0], framework, relative_path
        )
        suggestions.append({
            "type": "class",
            "framework": framework,
            "testFilePath": test_file_path,
            "scaffold": scaffold,
            "description": f"Tests for {len(module_info.classes)} classes",
            "priority": priority,
            "estimatedEffort": "medium",
        })
    elif module_info.functions:
        # Function-based tests
        scaffold = _generate_function_test_scaffold(
            module_info.functions[:3], framework, relative_path
        )
        suggestions.append({
            "type": "function",
            "framework": framework,
            "testFilePath": test_file_path,
            "scaffold": scaffold,
            "description": f"Tests for {len(module_info.functions)} functions",
            "priority": priority,
            "estimatedEffort": "low",
        })

    return suggestions


def _get_test_file_path(relative_path: str, framework: str) -> str:
    """Get test file path based on framework conventions."""
    path = Path(relative_path)
    name = path.stem

    if framework == "pytest":
        return f"tests/test_{name}.py"
    else:
        return f"tests/{name}_test.py"


def _generate_class_test_scaffold(
    class_info, framework: str, relative_path: str
) -> str:
    """Generate test scaffold for class."""
    module_path = relative_path.replace("/", ".").replace(".py", "")
    class_name = class_info.name

    if framework == "pytest":
        return f'''"""Tests for {class_name}."""

import pytest
from {module_path} import {class_name}


class Test{class_name}:
    """Test suite for {class_name}."""

    def test_initialization(self):
        """Test {class_name} initialization."""
        instance = {class_name}()
        assert instance is not None

    def test_basic_functionality(self):
        """Test basic {class_name} functionality."""
        instance = {class_name}()
        # Add your test logic here
        pass
'''
    else:  # unittest
        return f'''"""Tests for {class_name}."""

import unittest
from {module_path} import {class_name}


class Test{class_name}(unittest.TestCase):
    """Test suite for {class_name}."""

    def test_initialization(self):
        """Test {class_name} initialization."""
        instance = {class_name}()
        self.assertIsNotNone(instance)

    def test_basic_functionality(self):
        """Test basic {class_name} functionality."""
        instance = {class_name}()
        # Add your test logic here
        pass


if __name__ == "__main__":
    unittest.main()
'''


def _generate_function_test_scaffold(
    functions: List, framework: str, relative_path: str
) -> str:
    """Generate test scaffold for functions."""
    module_path = relative_path.replace("/", ".").replace(".py", "")

    if framework == "pytest":
        tests = []
        for func in functions:
            func_name = func.name
            tests.append(f'''
def test_{func_name}():
    """Test {func_name} function."""
    # TODO: Implement test for {func_name}
    pass
''')

        return f'''"""Tests for module functions."""

import pytest
from {module_path} import {", ".join(f.name for f in functions)}

{''.join(tests)}
'''
    else:  # unittest
        tests = []
        for func in functions:
            func_name = func.name
            tests.append(f'''
    def test_{func_name}(self):
        """Test {func_name} function."""
        # TODO: Implement test for {func_name}
        pass
''')

        return f'''"""Tests for module functions."""

import unittest
from {module_path} import {", ".join(f.name for f in functions)}


class TestModuleFunctions(unittest.TestCase):
    """Test suite for module functions."""
{''.join(tests)}


if __name__ == "__main__":
    unittest.main()
'''


def _generate_recommendations(
    gaps: List[Dict],
    overall_coverage: float,
    threshold: Dict,
    tested_files: int,
    untested_files: int,
) -> List[str]:
    """Generate coverage recommendations."""
    recommendations = []

    critical_gaps = [g for g in gaps if g["priority"] == "critical"]
    if critical_gaps:
        recommendations.append(
            f"⚠️ CRITICAL: Found {len(critical_gaps)} high-priority coverage gaps in core files. "
            "These should be addressed immediately."
        )

    target = threshold.get("lines", 80)
    if overall_coverage < target:
        gap = target - overall_coverage
        recommendations.append(
            f"Line coverage is {overall_coverage}%, {gap:.1f}% below target. "
            "Focus on testing untested core utilities first."
        )

    if untested_files > 0:
        recommendations.append(
            f"{untested_files} files lack adequate coverage. "
            "Prioritize core utilities and API layers."
        )

    high_complexity = [g for g in gaps if g["complexity"] > 50]
    if high_complexity:
        recommendations.append(
            f"{len(high_complexity)} high-complexity files (complexity > 50) need tests. "
            "Complex code is error-prone."
        )

    if not recommendations:
        recommendations.append("✅ Coverage looks good! Keep maintaining high test coverage.")

    return recommendations
