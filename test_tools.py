#!/usr/bin/env python3
"""Test script to demonstrate all MCP tools on this project itself."""

import asyncio
import json
from pathlib import Path

from src.tools.architecture_analyzer import analyze_architecture
from src.tools.pattern_detector import analyze_patterns
from src.tools.dependency_mapper import analyze_dependency_graph
from src.tools.coverage_analyzer import analyze_coverage_gaps
from src.tools.convention_validator import validate_conventions
from src.tools.context_pack_generator import generate_context_pack


async def test_architecture():
    """Test architecture analyzer."""
    print("\n" + "="*80)
    print("TESTING: Architecture Analyzer")
    print("="*80 + "\n")

    result = await analyze_architecture({
        "project_path": ".",
        "depth": "detailed",
        "include_metrics": True,
        "include_detailed_metrics": True,
        "generate_diagrams": False,
        "min_complexity": 10,
        "max_detailed_files": 10,
    })

    data = json.loads(result[0].text)
    print(f"Project: {data['project']['name']}")
    print(f"Type: {data['project']['type']}")
    print(f"Frameworks: {', '.join(data['frameworks']['detected'])}")
    print(f"\nStructure:")
    print(f"  - Modules: {data['structure']['totalModules']}")
    print(f"  - Classes: {data['structure']['totalClasses']}")
    print(f"  - Functions: {data['structure']['totalFunctions']}")
    print(f"  - Total Lines: {data['structure']['totalLines']}")

    if data.get("metrics"):
        print(f"\nMetrics:")
        print(f"  - Avg Complexity: {data['metrics']['avgComplexity']}")
        print(f"  - Max Complexity: {data['metrics']['maxComplexity']}")

    print(f"\nRecommendations:")
    for rec in data.get("recommendations", []):
        print(f"  - {rec}")


async def test_patterns():
    """Test pattern detector."""
    print("\n" + "="*80)
    print("TESTING: Pattern Detector")
    print("="*80 + "\n")

    result = await analyze_patterns({
        "project_path": ".",
        "pattern_types": ["async", "decorator", "context_manager"],
        "compare_with_best_practices": True,
        "suggest_improvements": True,
    })

    data = json.loads(result[0].text)
    print(f"Frameworks Detected: {', '.join(data['frameworks'])}")
    print(f"\nPattern Summary:")
    for pattern_type, count in data['summary']['byType'].items():
        print(f"  - {pattern_type}: {count}")

    print(f"\nTotal Patterns Found: {data['summary']['totalPatterns']}")

    if data.get("recommendations"):
        print(f"\nRecommendations:")
        for rec in data["recommendations"]:
            print(f"  - {rec}")


async def test_dependencies():
    """Test dependency mapper."""
    print("\n" + "="*80)
    print("TESTING: Dependency Mapper")
    print("="*80 + "\n")

    result = await analyze_dependency_graph({
        "project_path": ".",
        "detect_circular": True,
        "calculate_metrics": True,
        "include_globs": ["src/**/*.py"],
    })

    data = json.loads(result[0].text)
    print(f"Total Modules: {data['summary']['totalModules']}")
    print(f"Total Dependencies: {data['summary']['totalDependencies']}")
    print(f"Circular Dependencies: {data['summary']['circularCount']}")

    if data.get("metrics"):
        print(f"\nMetrics:")
        print(f"  - Coupling: {data['metrics']['coupling']}")
        print(f"  - Cohesion: {data['metrics']['cohesion']}")
        print(f"  - Stability: {data['metrics']['stability']}")

    if data.get("hotspots"):
        print(f"\nHotspots Found: {len(data['hotspots'])}")
        for hotspot in data["hotspots"][:3]:
            print(f"  - {hotspot['file']} ({hotspot['type']}) - centrality: {hotspot['centrality']}")

    print(f"\nRecommendations:")
    for rec in data.get("recommendations", []):
        print(f"  - {rec}")


async def test_coverage():
    """Test coverage analyzer."""
    print("\n" + "="*80)
    print("TESTING: Coverage Analyzer")
    print("="*80 + "\n")

    result = await analyze_coverage_gaps({
        "project_path": ".",
        "threshold": {"lines": 80},
        "priority": "all",
        "analyze_complexity": True,
        "include_globs": ["src/**/*.py"],
    })

    data = json.loads(result[0].text)
    print(f"Overall Coverage: {data['summary']['overallCoverage']['lines']}%")
    print(f"Tested Files: {data['summary']['testedFiles']}")
    print(f"Untested Files: {data['summary']['untestedFiles']}")

    print(f"\nCoverage Gaps Found: {len(data['gaps'])}")
    if data.get("criticalGaps"):
        print(f"Critical Gaps: {len(data['criticalGaps'])}")
        for gap in data['criticalGaps'][:3]:
            print(f"  - {gap['file']} ({gap['priority']}) - {gap['coverage']['lines']}% coverage")

    print(f"\nRecommendations:")
    for rec in data.get("recommendations", []):
        print(f"  - {rec}")


async def test_conventions():
    """Test convention validator."""
    print("\n" + "="*80)
    print("TESTING: Convention Validator")
    print("="*80 + "\n")

    result = await validate_conventions({
        "project_path": ".",
        "autodetect_conventions": True,
        "severity": "warning",
        "include_globs": ["src/**/*.py"],
    })

    data = json.loads(result[0].text)
    print(f"Overall Consistency: {data['consistency']['overall']}%")
    print(f"\nConsistency by Category:")
    for category, score in data['consistency']['byCategory'].items():
        print(f"  - {category}: {score}%")

    print(f"\nViolations:")
    print(f"  - Total: {data['summary']['totalViolations']}")
    for severity, count in data['summary']['bySeverity'].items():
        if count > 0:
            print(f"  - {severity}: {count}")

    print(f"\nDetected Conventions:")
    for conv in data.get("detectedConventions", []):
        print(f"  - {conv['rule']}: {conv['pattern']} (confidence: {conv['confidence']})")

    print(f"\nRecommendations:")
    for rec in data.get("recommendations", []):
        print(f"  - {rec}")


async def test_context_pack():
    """Test context pack generator."""
    print("\n" + "="*80)
    print("TESTING: Context Pack Generator")
    print("="*80 + "\n")

    result = await generate_context_pack({
        "task": "Add support for analyzing Jupyter notebooks",
        "project_path": ".",
        "max_tokens": 10000,
        "include_types": ["files", "arch"],
        "format": "json",
        "optimization_strategy": "relevance",
        "focus_areas": ["src/tools", "src/utils"],
    })

    data = json.loads(result[0].text)
    print(f"Task: {data['task']}")
    print(f"Strategy: {data['strategy']}")
    print(f"\nTask Analysis:")
    print(f"  - Type: {data['taskAnalysis']['type']}")
    print(f"  - Keywords: {', '.join(data['taskAnalysis']['keywords']) if data['taskAnalysis']['keywords'] else 'none'}")
    print(f"  - Domain: {', '.join(data['taskAnalysis']['domainConcepts'])}")

    print(f"\nToken Budget:")
    print(f"  - Max: {data['tokenBudget']['max']:,}")
    print(f"  - Used: {data['tokenBudget']['used']:,}")
    print(f"  - Remaining: {data['tokenBudget']['remaining']:,}")

    print(f"\nRelevant Files Found: {len(data['files'])}")
    for file_info in data['files'][:5]:
        print(f"  - {file_info['path']} (relevance: {file_info['relevance']})")

    print(f"\nSuggestions:")
    for suggestion in data.get("suggestions", []):
        print(f"  - {suggestion}")


async def main():
    """Run all tests."""
    print("\n" + "="*80)
    print("CODE ANALYSIS PYTHON MCP - TOOL DEMONSTRATION")
    print("Testing all 6 tools on this project itself")
    print("="*80)

    try:
        await test_architecture()
        await test_patterns()
        await test_dependencies()
        await test_coverage()
        await test_conventions()
        await test_context_pack()

        print("\n" + "="*80)
        print("ALL TESTS COMPLETED SUCCESSFULLY!")
        print("="*80 + "\n")

    except Exception as e:
        print(f"\n❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
