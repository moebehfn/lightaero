import os
import subprocess

import yaml


def test_infrastructure_exists():
    """Checks for mkdocs.yml and docs/index.md."""
    assert os.path.exists("mkdocs.yml"), "mkdocs.yml missing"
    assert os.path.exists("docs/index.md"), "docs/index.md missing"


def test_mkdocs_config_valid():
    """Loads mkdocs.yml using PyYAML and verifies basic keys."""
    assert os.path.exists("mkdocs.yml"), "mkdocs.yml missing"
    with open("mkdocs.yml") as f:
        config = yaml.safe_load(f)

    assert "site_name" in config, "site_name missing in mkdocs.yml"
    assert "theme" in config, "theme missing in mkdocs.yml"
    assert "plugins" in config, "plugins missing in mkdocs.yml"

    assert config["site_name"] == "lightaero"
    assert config["theme"]["name"] == "material"


def test_site_generation():
    """Runs mkdocs build via subprocess and verifies exit code 0.

    Note: --strict mode is deferred to Phase 7 due to pre-existing
    docstring warnings in the codebase.
    """
    # Ensure site directory is clean before test if it exists
    if os.path.exists("site"):
        import shutil

        shutil.rmtree("site")

    result = subprocess.run(["mkdocs", "build"], capture_output=True, text=True)
    assert result.returncode == 0, f"mkdocs build failed: {result.stderr}"
    assert os.path.exists("site/index.html"), "site/index.html not generated"
