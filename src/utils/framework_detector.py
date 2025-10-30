"""Framework detection utility."""

from pathlib import Path
from typing import List, Set
import ast


class FrameworkDetector:
    """Detect Python frameworks used in a project."""

    # Framework detection patterns
    FRAMEWORK_PATTERNS = {
        "pandas": ["pandas", "pd"],
        "numpy": ["numpy", "np"],
        "sklearn": ["sklearn", "scikit-learn", "scikit_learn"],
        "matplotlib": ["matplotlib", "matplotlib.pyplot", "plt"],
        "seaborn": ["seaborn", "sns"],
        "fastapi": ["fastapi", "FastAPI"],
        "django": ["django"],
        "flask": ["flask", "Flask"],
        "jupyter": ["jupyter", "ipython", "IPython"],
        "tensorflow": ["tensorflow", "tf"],
        "pytorch": ["torch", "pytorch"],
        "scipy": ["scipy"],
        "plotly": ["plotly"],
        "streamlit": ["streamlit", "st"],
    }

    @staticmethod
    def detect_frameworks(files: List[Path]) -> Set[str]:
        """
        Detect frameworks used in project files.

        Args:
            files: List of Python files to analyze

        Returns:
            Set of detected framework names
        """
        detected = set()

        for file_path in files:
            frameworks = FrameworkDetector._detect_in_file(file_path)
            detected.update(frameworks)

        return detected

    @staticmethod
    def _detect_in_file(file_path: Path) -> Set[str]:
        """Detect frameworks in a single file."""
        detected = set()

        try:
            content = file_path.read_text(encoding="utf-8")
            tree = ast.parse(content)

            # Extract all imports
            imports = []
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.append(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        imports.append(node.module)

            # Check against patterns
            for framework, patterns in FrameworkDetector.FRAMEWORK_PATTERNS.items():
                for pattern in patterns:
                    for import_name in imports:
                        if import_name.startswith(pattern) or import_name == pattern:
                            detected.add(framework)
                            break

        except (SyntaxError, UnicodeDecodeError):
            pass

        return detected

    @staticmethod
    def detect_project_type(frameworks: Set[str]) -> str:
        """
        Determine primary project type based on frameworks.

        Args:
            frameworks: Set of detected frameworks

        Returns:
            Project type string
        """
        if "fastapi" in frameworks:
            return "fastapi"
        elif "django" in frameworks:
            return "django"
        elif "flask" in frameworks:
            return "flask"
        elif "pandas" in frameworks or "numpy" in frameworks:
            return "data-analysis"
        elif "tensorflow" in frameworks or "pytorch" in frameworks:
            return "machine-learning"
        elif "jupyter" in frameworks:
            return "jupyter"
        else:
            return "python"

    @staticmethod
    def get_framework_specific_patterns(framework: str) -> List[str]:
        """
        Get framework-specific code patterns to look for.

        Args:
            framework: Framework name

        Returns:
            List of pattern identifiers
        """
        patterns_map = {
            "pandas": ["DataFrame", "Series", "read_csv", "groupby", "merge"],
            "numpy": ["array", "ndarray", "arange", "zeros", "ones"],
            "sklearn": ["Pipeline", "fit", "predict", "transform", "fit_transform"],
            "fastapi": ["FastAPI", "APIRouter", "@app.", "Depends", "HTTPException"],
            "django": ["models.Model", "views", "urls", "settings"],
            "flask": ["Flask", "@app.route", "render_template", "request"],
            "matplotlib": ["plt.plot", "plt.figure", "plt.show", "plt.subplot"],
            "seaborn": ["sns.plot", "sns.heatmap", "sns.distplot"],
        }

        return patterns_map.get(framework, [])
