"""File scanner utility for finding Python files."""

import fnmatch
from pathlib import Path
from typing import List, Optional


class FileScanner:
    """Scan project directories for Python files."""

    @staticmethod
    def scan_files(
        project_path: str,
        include_globs: Optional[List[str]] = None,
        exclude_globs: Optional[List[str]] = None,
    ) -> List[Path]:
        """
        Scan for Python files matching include/exclude patterns.

        Args:
            project_path: Root project directory
            include_globs: Patterns to include (default: ["**/*.py"])
            exclude_globs: Patterns to exclude

        Returns:
            List of Path objects matching criteria
        """
        if include_globs is None:
            include_globs = ["**/*.py"]

        if exclude_globs is None:
            exclude_globs = [
                "**/venv/**",
                "**/.venv/**",
                "**/env/**",
                "**/site-packages/**",
                "**/__pycache__/**",
                "**/build/**",
                "**/dist/**",
                "**/.git/**",
            ]

        project_root = Path(project_path).resolve()
        files: List[Path] = []

        # Gather all Python files
        for pattern in include_globs:
            matched = list(project_root.glob(pattern))
            files.extend(matched)

        # Filter out excluded patterns
        filtered_files = []
        for file_path in files:
            relative = file_path.relative_to(project_root)
            relative_str = str(relative)

            # Check if file matches any exclude pattern
            excluded = False
            for exclude_pattern in exclude_globs:
                if fnmatch.fnmatch(relative_str, exclude_pattern):
                    excluded = True
                    break

            if not excluded and file_path.is_file():
                filtered_files.append(file_path)

        return sorted(set(filtered_files))

    @staticmethod
    def get_module_path(file_path: Path, project_root: Path) -> str:
        """
        Convert file path to Python module path.

        Args:
            file_path: Absolute file path
            project_root: Project root directory

        Returns:
            Module path (e.g., "src.utils.file_scanner")
        """
        relative = file_path.relative_to(project_root)
        parts = list(relative.parts)

        # Remove .py extension
        if parts[-1].endswith(".py"):
            parts[-1] = parts[-1][:-3]

        # Remove __init__ if present
        if parts[-1] == "__init__":
            parts = parts[:-1]

        return ".".join(parts)
