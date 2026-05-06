import os

import pytest
import yaml


def test_site_url_configured():
    """Verify that site_url in mkdocs.yml is correctly set."""
    with open("mkdocs.yml") as f:
        config = yaml.safe_load(f)
    assert config["site_url"] == "https://moebehfn.github.io/lightaero/"


def test_workflow_exists():
    """Verify that the deployment workflow file exists."""
    assert os.path.exists(".github/workflows/docs.yml")


def test_workflow_configuration():
    """Verify the deployment workflow configuration."""
    workflow_path = ".github/workflows/docs.yml"
    if not os.path.exists(workflow_path):
        pytest.skip("docs.yml does not exist yet")

    with open(workflow_path) as f:
        workflow = yaml.safe_load(f)

    # Check triggers
    on = workflow.get("on", {})
    if isinstance(on, list):
        assert "workflow_dispatch" in on
    else:
        assert "workflow_dispatch" in on
        assert "push" in on
        assert "master" in on["push"]["branches"]

    # Check permissions
    assert workflow.get("permissions", {}).get("contents") == "write"

    # Check job details
    deploy_job = workflow.get("jobs", {}).get("deploy", {})
    assert deploy_job.get("runs-on") == "ubuntu-latest"

    steps = deploy_job.get("steps", [])

    # Check python version
    setup_python = next((s for s in steps if "actions/setup-python" in s.get("uses", "")), None)
    assert setup_python is not None
    assert str(setup_python.get("with", {}).get("python-version")) == "3.11"

    # Check deployment command
    deploy_step = next((s for s in steps if "mkdocs gh-deploy" in s.get("run", "")), None)
    assert deploy_step is not None
    assert "--force" in deploy_step["run"]
