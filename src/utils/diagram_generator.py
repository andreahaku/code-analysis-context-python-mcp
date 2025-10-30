"""Mermaid diagram generator."""

from typing import Dict, List


class DiagramGenerator:
    """Generate Mermaid diagrams for visualization."""

    @staticmethod
    def generate_architecture_diagram(architecture_data: Dict) -> str:
        """
        Generate Mermaid diagram for project architecture.

        Args:
            architecture_data: Architecture analysis data

        Returns:
            Mermaid diagram string
        """
        lines = ["```mermaid", "graph TD"]

        # Add project node
        project_name = architecture_data.get("project", {}).get("name", "Project")
        lines.append(f'    ROOT["{project_name}"]')

        # Add layers if available
        layers = architecture_data.get("layers", [])
        for idx, layer in enumerate(layers):
            layer_id = f"LAYER{idx}"
            layer_name = layer.get("name", f"Layer {idx}")
            module_count = layer.get("moduleCount", 0)

            lines.append(f'    {layer_id}["{layer_name}<br/>{module_count} modules"]')
            lines.append(f"    ROOT --> {layer_id}")

        # Add framework nodes if available
        frameworks = architecture_data.get("frameworks", {}).get("detected", [])
        if frameworks:
            lines.append('    FW["Frameworks"]')
            lines.append("    ROOT --> FW")

            for idx, fw in enumerate(frameworks[:5]):  # Limit to 5
                fw_id = f"FW{idx}"
                lines.append(f'    {fw_id}["{fw}"]')
                lines.append(f"    FW --> {fw_id}")

        lines.append("```")
        return "\n".join(lines)

    @staticmethod
    def generate_dependency_diagram(
        nodes: List[Dict], edges: List[Dict], circular: List = None
    ) -> str:
        """
        Generate Mermaid diagram for dependency graph.

        Args:
            nodes: List of node dictionaries
            edges: List of edge dictionaries
            circular: List of circular dependency paths

        Returns:
            Mermaid diagram string
        """
        lines = ["```mermaid", "graph TD"]

        # Add nodes with styling
        for idx, node in enumerate(nodes[:30]):  # Limit to 30 nodes
            node_id = f"N{idx}"
            node_name = node.get("id", "").split("/")[-1].replace(".py", "")
            node_type = node.get("type", "module")

            # Style based on metrics
            metrics = node.get("metrics", {})
            in_degree = metrics.get("inDegree", 0)
            out_degree = metrics.get("outDegree", 0)

            style_class = ""
            if in_degree >= 5:
                style_class = ":::hub"
            elif out_degree >= 10:
                style_class = ":::bottleneck"

            lines.append(f'    {node_id}["{node_name}"]{style_class}')

        # Add edges
        edge_count = 0
        for edge in edges[:50]:  # Limit to 50 edges
            from_path = edge.get("from", "")
            to_path = edge.get("to", "")

            # Find node indices
            from_idx = next(
                (i for i, n in enumerate(nodes[:30]) if n.get("id") == from_path), None
            )
            to_idx = next(
                (i for i, n in enumerate(nodes[:30]) if n.get("id") == to_path), None
            )

            if from_idx is not None and to_idx is not None:
                lines.append(f"    N{from_idx} --> N{to_idx}")
                edge_count += 1

        # Add style definitions
        lines.append("")
        lines.append("    classDef hub fill:#90EE90")
        lines.append("    classDef bottleneck fill:#FFB6C1")
        lines.append("```")

        return "\n".join(lines)

    @staticmethod
    def generate_class_hierarchy(classes: List[Dict]) -> str:
        """
        Generate Mermaid diagram for class hierarchy.

        Args:
            classes: List of class information

        Returns:
            Mermaid diagram string
        """
        lines = ["```mermaid", "classDiagram"]

        for cls in classes[:20]:  # Limit to 20 classes
            class_name = cls.get("name", "Unknown")
            bases = cls.get("bases", [])

            # Add inheritance relationships
            for base in bases:
                if base and base != "object":
                    lines.append(f"    {base} <|-- {class_name}")

            # Add methods
            methods = cls.get("methods", [])
            if methods:
                lines.append(f"    class {class_name} {{")
                for method in methods[:5]:  # Limit to 5 methods per class
                    method_name = method.get("name", "")
                    lines.append(f"        +{method_name}()")
                lines.append("    }")

        lines.append("```")
        return "\n".join(lines)
