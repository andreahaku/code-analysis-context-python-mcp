"""Dependency mapper for Python projects."""

import json
from pathlib import Path
from typing import Any, Dict, List, Sequence, Set, Tuple

import networkx as nx
from mcp.types import TextContent

from ..utils.ast_parser import ASTParser
from ..utils.diagram_generator import DiagramGenerator
from ..utils.file_scanner import FileScanner


async def analyze_dependency_graph(args: Dict[str, Any]) -> Sequence[TextContent]:
    """
    Analyze module dependencies and imports.

    Features:
    - Import graph construction
    - Circular dependency detection
    - Coupling metrics
    - Dependency hotspots
    - Mermaid diagrams
    """
    project_path = args.get("project_path", ".")
    detect_circular = args.get("detect_circular", False)
    calculate_metrics = args.get("calculate_metrics", False)
    generate_diagram = args.get("generate_diagram", False)
    focus_module = args.get("focus_module")
    max_depth = args.get("depth", 5)
    include_globs = args.get("include_globs", ["**/*.py"])
    exclude_globs = args.get("exclude_globs")

    project_root = Path(project_path).resolve()
    project_name = project_root.name

    # Scan files
    files = FileScanner.scan_files(project_path, include_globs, exclude_globs)

    if not files:
        return [
            TextContent(
                type="text",
                text=json.dumps({"error": "No Python files found"}, indent=2),
            )
        ]

    # Parse all files and build dependency graph
    graph = nx.DiGraph()
    module_info_map = {}

    for file_path in files:
        module_info = ASTParser.parse_file(file_path)
        if not module_info:
            continue

        module_name = FileScanner.get_module_path(file_path, project_root)
        module_info_map[module_name] = module_info

        # Add node
        graph.add_node(module_name, path=str(file_path.relative_to(project_root)))

        # Add edges for dependencies
        dependencies = ASTParser.get_dependencies(module_info, project_root)
        for dep in dependencies:
            if dep in module_info_map or any(
                dep.startswith(FileScanner.get_module_path(f, project_root))
                for f in files
            ):
                graph.add_edge(module_name, dep)

    # Focus on specific module if requested
    if focus_module:
        graph = _focus_subgraph(graph, focus_module, max_depth)

    # Build nodes and edges for output
    nodes = []
    for node_id in graph.nodes():
        node_path = graph.nodes[node_id].get("path", node_id)
        in_degree = graph.in_degree(node_id)
        out_degree = graph.out_degree(node_id)

        # Classify node type
        node_type = _classify_module(node_path)

        nodes.append(
            {
                "id": node_id,
                "path": node_path,
                "type": node_type,
                "metrics": {
                    "inDegree": in_degree,
                    "outDegree": out_degree,
                    "centrality": round((in_degree + out_degree) / max(1, len(graph.nodes())), 3),
                },
            }
        )

    edges = []
    for from_node, to_node in graph.edges():
        edges.append({"from": from_node, "to": to_node, "type": "import"})

    # Detect circular dependencies
    circular_deps = []
    if detect_circular:
        circular_deps = _detect_circular_dependencies(graph)

    # Calculate metrics
    metrics = {}
    if calculate_metrics:
        metrics = _calculate_metrics(graph)

    # Identify hotspots
    hotspots = _identify_hotspots(nodes)

    # Build result
    result = {
        "project": {"name": project_name, "totalFiles": len(files)},
        "graph": {"nodes": nodes, "edges": edges},
        "circularDependencies": circular_deps,
        "metrics": metrics,
        "hotspots": hotspots,
        "summary": {
            "totalModules": len(nodes),
            "totalDependencies": len(edges),
            "averageDependencies": round(len(edges) / max(1, len(nodes)), 2),
            "circularCount": len(circular_deps),
        },
    }

    # Generate diagram
    if generate_diagram:
        result["diagram"] = DiagramGenerator.generate_dependency_diagram(
            nodes, edges, circular_deps
        )

    # Add recommendations
    recommendations = []
    if circular_deps:
        recommendations.append(
            f"⚠️ CRITICAL: Found {len(circular_deps)} circular dependencies. "
            "These can cause runtime errors and make code hard to maintain."
        )

    if metrics and metrics.get("coupling", 0) > 10:
        recommendations.append(
            f"High coupling detected ({metrics['coupling']:.2f}). "
            "Consider applying dependency inversion and interface segregation principles."
        )

    if hotspots:
        bottlenecks = [h for h in hotspots if h["type"] == "bottleneck"]
        if bottlenecks:
            recommendations.append(
                f"Found {len(bottlenecks)} bottleneck modules with excessive dependencies. "
                "Consider refactoring to reduce coupling."
            )

    if not recommendations:
        recommendations.append("✅ Dependency structure looks healthy!")

    result["recommendations"] = recommendations

    return [TextContent(type="text", text=json.dumps(result, indent=2))]


def _classify_module(module_path: str) -> str:
    """Classify module type based on path."""
    path_lower = module_path.lower()

    if "test" in path_lower:
        return "test"
    elif "util" in path_lower or "helper" in path_lower:
        return "utility"
    elif "model" in path_lower:
        return "model"
    elif "view" in path_lower or "api" in path_lower:
        return "api"
    elif "service" in path_lower:
        return "service"
    elif "__init__" in path_lower:
        return "package"
    else:
        return "module"


def _detect_circular_dependencies(graph: nx.DiGraph) -> List[Dict]:
    """Detect circular dependencies using cycle detection."""
    circular_deps = []

    try:
        # Find all simple cycles
        cycles = list(nx.simple_cycles(graph))

        for cycle in cycles:
            # Convert to readable format
            cycle_path = cycle + [cycle[0]]  # Close the circle
            severity = "critical" if len(cycle) <= 3 else "warning"

            circular_deps.append(
                {
                    "cycle": cycle_path,
                    "length": len(cycle),
                    "severity": severity,
                    "description": f"Circular dependency: {' → '.join(cycle_path)}",
                }
            )

    except nx.NetworkXNoCycle:
        pass  # No cycles found

    return sorted(circular_deps, key=lambda x: x["length"])


def _calculate_metrics(graph: nx.DiGraph) -> Dict:
    """Calculate coupling and cohesion metrics."""
    if not graph.nodes():
        return {
            "totalModules": 0,
            "avgDependencies": 0,
            "maxDependencies": 0,
            "coupling": 0,
            "cohesion": 0,
            "stability": 0,
        }

    # Calculate degrees
    in_degrees = [graph.in_degree(n) for n in graph.nodes()]
    out_degrees = [graph.out_degree(n) for n in graph.nodes()]

    avg_in = sum(in_degrees) / len(in_degrees)
    avg_out = sum(out_degrees) / len(out_degrees)

    # Coupling: average of in + out degrees
    coupling = avg_in + avg_out

    # Cohesion: inverse of average fanout (simplified)
    cohesion = 1 / (avg_out + 1)

    # Stability: Ce / (Ca + Ce) where Ce = efferent, Ca = afferent
    avg_stability = avg_out / (avg_in + avg_out + 1)

    return {
        "totalModules": len(graph.nodes()),
        "avgDependencies": round((avg_in + avg_out) / 2, 2),
        "maxDependencies": max(max(in_degrees), max(out_degrees)),
        "coupling": round(coupling, 2),
        "cohesion": round(cohesion, 3),
        "stability": round(avg_stability, 3),
    }


def _identify_hotspots(nodes: List[Dict]) -> List[Dict]:
    """Identify dependency hotspots (hubs and bottlenecks)."""
    hotspots = []

    for node in nodes:
        metrics = node["metrics"]
        in_degree = metrics["inDegree"]
        out_degree = metrics["outDegree"]

        # Hub: many modules depend on this (high in-degree)
        if in_degree >= 5:
            hotspots.append(
                {
                    "file": node["id"],
                    "inDegree": in_degree,
                    "outDegree": out_degree,
                    "centrality": metrics["centrality"],
                    "type": "hub",
                    "description": f"Core module: {in_degree} modules depend on this",
                }
            )

        # Bottleneck: depends on many modules (high out-degree)
        elif out_degree >= 10:
            hotspots.append(
                {
                    "file": node["id"],
                    "inDegree": in_degree,
                    "outDegree": out_degree,
                    "centrality": metrics["centrality"],
                    "type": "bottleneck",
                    "description": f"Potential bottleneck: depends on {out_degree} modules",
                }
            )

        # God object: high in both directions
        elif in_degree >= 5 and out_degree >= 10:
            hotspots.append(
                {
                    "file": node["id"],
                    "inDegree": in_degree,
                    "outDegree": out_degree,
                    "centrality": metrics["centrality"],
                    "type": "god-object",
                    "description": "God object: high coupling in both directions",
                }
            )

    return sorted(hotspots, key=lambda x: x["centrality"], reverse=True)


def _focus_subgraph(graph: nx.DiGraph, focus_module: str, max_depth: int) -> nx.DiGraph:
    """Extract subgraph focused on a specific module."""
    if focus_module not in graph:
        return graph

    # BFS to find nodes within max_depth
    nodes_to_keep = {focus_module}
    queue = [(focus_module, 0)]
    visited = {focus_module}

    while queue:
        current, depth = queue.pop(0)

        if depth >= max_depth:
            continue

        # Add predecessors (who imports this)
        for pred in graph.predecessors(current):
            if pred not in visited:
                visited.add(pred)
                nodes_to_keep.add(pred)
                queue.append((pred, depth + 1))

        # Add successors (what this imports)
        for succ in graph.successors(current):
            if succ not in visited:
                visited.add(succ)
                nodes_to_keep.add(succ)
                queue.append((succ, depth + 1))

    return graph.subgraph(nodes_to_keep).copy()
