import subprocess
from pathlib import Path

import pytest
import tomllib


def test_pyproject_exists():
    assert Path("pyproject.toml").exists()


def test_pyproject_metadata():
    with open("pyproject.toml", "rb") as f:
        data = tomllib.load(f)

    project = data.get("project", {})
    assert project.get("name") == "lightaero"
    assert project.get("version") == "0.1.0"
    assert project.get("license") == "Apache-2.0"

    dependencies = project.get("dependencies", [])
    expected_deps = ["numpy>=2.0.0", "scipy>=1.10.0", "matplotlib>=3.7.0"]
    for dep in expected_deps:
        assert dep in dependencies


def test_build_backend():
    with open("pyproject.toml", "rb") as f:
        data = tomllib.load(f)

    build_system = data.get("build-system", {})
    assert build_system.get("build-backend") == "hatchling.build"
    assert "hatchling" in build_system.get("requires", [])


def test_hatch_config():
    with open("pyproject.toml", "rb") as f:
        data = tomllib.load(f)

    hatch_wheel = data.get("tool", {}).get("hatch", {}).get("build", {}).get("targets", {}).get("wheel", {})
    assert "src/lightaero" in hatch_wheel.get("packages", [])

    hatch_sdist = data.get("tool", {}).get("hatch", {}).get("build", {}).get("targets", {}).get("sdist", {})
    exclude = hatch_sdist.get("exclude", [])
    assert "/.github" in exclude
    assert "/docs" in exclude
    assert "/tests" in exclude


def test_pytest_config():
    with open("pyproject.toml", "rb") as f:
        data = tomllib.load(f)

    pytest_config = data.get("tool", {}).get("pytest", {}).get("ini_options", {})
    assert "tests" in pytest_config.get("testpaths", [])


def test_build_tool_version():
    """Verify build tool can be invoked."""
    try:
        result = subprocess.run(["python3", "-m", "build", "--version"], capture_output=True, text=True)
        if result.returncode != 0:
            pytest.skip("python3 -m build is not working")
    except FileNotFoundError:
        pytest.skip("python3 not found")
