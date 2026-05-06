from pathlib import Path

import pytest


def test_files_exist():
    root = Path(__file__).parent.parent.parent
    assert (root / "LICENSE").exists()
    assert (root / "CONTRIBUTING.md").exists()
    assert (root / "CITATION.cff").exists()


def test_license_headers():
    root = Path(__file__).parent.parent.parent
    src_dir = root / "src" / "lightaero"

    python_files = list(src_dir.rglob("*.py"))
    # Exclude macOS metadata files if any were missed
    python_files = [f for f in python_files if not f.name.startswith(".")]

    header_string = "Licensed under the Apache License, Version 2.0"

    for file_path in python_files:
        with open(file_path) as f:
            content = f.read()
            assert header_string in content, f"License header missing in {file_path}"


if __name__ == "__main__":
    pytest.main([__file__])
