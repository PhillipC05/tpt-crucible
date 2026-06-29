"""
Root conftest.py — adds all python/* packages to sys.path so pytest
finds them without a manual PYTHONPATH export.
"""
import sys
from pathlib import Path

_repo_root = Path(__file__).parent
_python_dir = _repo_root / "python"

for package_dir in sorted(_python_dir.iterdir()):
    if package_dir.is_dir() and (package_dir / "pyproject.toml").exists():
        sys.path.insert(0, str(package_dir))
