"""Complexity analyzer using Radon."""

from pathlib import Path
from typing import Dict, List, Optional

from radon.complexity import cc_visit
from radon.metrics import mi_visit, h_visit


class ComplexityAnalyzer:
    """Analyze code complexity metrics."""

    @staticmethod
    def analyze_file(file_path: Path) -> Dict:
        """
        Analyze complexity metrics for a file.

        Args:
            file_path: Path to Python file

        Returns:
            Dictionary with complexity metrics
        """
        try:
            content = file_path.read_text(encoding="utf-8")

            # Cyclomatic complexity
            cc_results = cc_visit(content)
            total_complexity = sum(result.complexity for result in cc_results)
            avg_complexity = total_complexity / len(cc_results) if cc_results else 0
            max_complexity = max((r.complexity for r in cc_results), default=0)

            # Maintainability index
            try:
                mi = mi_visit(content, multi=True)
            except Exception:
                mi = 100  # Default to perfect score on error

            # Halstead metrics
            try:
                h = h_visit(content)
                halstead_volume = h.total.volume if h.total else 0
                halstead_difficulty = h.total.difficulty if h.total else 0
            except Exception:
                halstead_volume = 0
                halstead_difficulty = 0

            # Function-level complexity
            functions = [
                {
                    "name": result.name,
                    "complexity": result.complexity,
                    "line": result.lineno,
                    "rank": ComplexityAnalyzer._complexity_rank(result.complexity),
                }
                for result in cc_results
            ]

            return {
                "totalComplexity": total_complexity,
                "avgComplexity": round(avg_complexity, 2),
                "maxComplexity": max_complexity,
                "maintainabilityIndex": round(mi, 2) if isinstance(mi, float) else 100,
                "halsteadVolume": round(halstead_volume, 2),
                "halsteadDifficulty": round(halstead_difficulty, 2),
                "functions": functions,
            }

        except Exception as e:
            return {
                "totalComplexity": 0,
                "avgComplexity": 0,
                "maxComplexity": 0,
                "maintainabilityIndex": 100,
                "halsteadVolume": 0,
                "halsteadDifficulty": 0,
                "functions": [],
                "error": str(e),
            }

    @staticmethod
    def _complexity_rank(complexity: int) -> str:
        """
        Rank complexity level.

        A: 1-5 (simple)
        B: 6-10 (moderate)
        C: 11-20 (complex)
        D: 21-30 (very complex)
        F: 31+ (extreme)
        """
        if complexity <= 5:
            return "A"
        elif complexity <= 10:
            return "B"
        elif complexity <= 20:
            return "C"
        elif complexity <= 30:
            return "D"
        else:
            return "F"

    @staticmethod
    def get_high_complexity_functions(
        complexity_data: Dict, threshold: int = 10
    ) -> List[Dict]:
        """Get functions exceeding complexity threshold."""
        return [
            func
            for func in complexity_data.get("functions", [])
            if func["complexity"] >= threshold
        ]
