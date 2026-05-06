import pathlib

import pytest
import yaml


def test_ci_workflow_exists():
    """Verify that the CI workflow file exists."""
    workflow_path = pathlib.Path(".github/workflows/ci.yml")
    assert workflow_path.exists(), "CI workflow file .github/workflows/ci.yml is missing"


def test_ci_workflow_triggers():
    """Verify that the CI workflow triggers on push and pull_request to master."""
    workflow_path = pathlib.Path(".github/workflows/ci.yml")
    if not workflow_path.exists():
        pytest.skip("CI workflow file does not exist yet")

    with open(workflow_path) as f:
        config = yaml.safe_load(f)

    on = config.get("on", {})

    # Check push
    push = on.get("push", {})
    assert "branches" in push
    assert "master" in push["branches"]

    # Check pull_request
    pr = on.get("pull_request", {})
    assert "branches" in pr
    assert "master" in pr["branches"]


def test_ci_workflow_matrix():
    """Verify the python version matrix."""
    workflow_path = pathlib.Path(".github/workflows/ci.yml")
    if not workflow_path.exists():
        pytest.skip("CI workflow file does not exist yet")

    with open(workflow_path) as f:
        config = yaml.safe_load(f)

    # Jobs are usually under 'jobs'
    jobs = config.get("jobs", {})
    test_job = jobs.get("test", {}) or jobs.get("build", {})
    assert test_job, "Could not find a 'test' or 'build' job"

    strategy = test_job.get("strategy", {})
    matrix = strategy.get("matrix", {})
    python_versions = matrix.get("python-version", [])

    expected_versions = ["3.10", "3.11", "3.12", "3.13"]
    for version in expected_versions:
        assert version in python_versions or float(version) in python_versions


def test_ci_workflow_steps():
    """Verify presence of linting, formatting, and testing steps."""
    workflow_path = pathlib.Path(".github/workflows/ci.yml")
    if not workflow_path.exists():
        pytest.skip("CI workflow file does not exist yet")

    with open(workflow_path) as f:
        config = yaml.safe_load(f)

    jobs = config.get("jobs", {})
    test_job = jobs.get("test", {}) or jobs.get("build", {})
    steps = test_job.get("steps", [])

    step_runs = [step.get("run", "") for step in steps if "run" in step]
    full_text = " ".join(step_runs)

    assert "ruff check" in full_text
    assert "ruff format --check" in full_text
    assert "pytest" in full_text


def test_ci_workflow_permissions():
    """Verify security configurations."""
    workflow_path = pathlib.Path(".github/workflows/ci.yml")
    if not workflow_path.exists():
        pytest.skip("CI workflow file does not exist yet")

    with open(workflow_path) as f:
        config = yaml.safe_load(f)

    permissions = config.get("permissions", {})
    assert permissions.get("contents") == "read"
