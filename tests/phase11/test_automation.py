import os
import subprocess

# Try to use tomllib (Python 3.11+) or fall back to a simple string check
try:
    import tomllib
except ImportError:
    tomllib = None


def test_generation_script_exists():
    assert os.path.exists("scripts/generate_docs_assets.py")


def test_pyproject_contains_plotly():
    with open("pyproject.toml", "rb") as f:
        if tomllib:
            data = tomllib.load(f)
            docs_deps = data.get("project", {}).get("optional-dependencies", {}).get("docs", [])
            assert any("plotly" in dep.lower() for dep in docs_deps)
        else:
            content = f.read().decode("utf-8")
            assert "plotly" in content.lower()


def test_docs_workflow_integration():
    workflow_path = ".github/workflows/docs.yml"
    assert os.path.exists(workflow_path)
    with open(workflow_path) as f:
        content = f.read()
    assert "Generate 3D visualization assets" in content
    assert "scripts/generate_docs_assets.py" in content


def test_script_execution_produces_html():
    output_file = "tmp/test_fig.html"
    os.makedirs("tmp", exist_ok=True)
    if os.path.exists(output_file):
        os.remove(output_file)

    # Run the script
    result = subprocess.run(
        ["python", "scripts/generate_docs_assets.py", "--output", output_file], capture_output=True, text=True
    )
    assert result.returncode == 0, f"Script failed with error: {result.stderr}"
    assert os.path.exists(output_file)
    with open(output_file) as f:
        content = f.read()
    assert "Plotly" in content or "plotly" in content


def test_gitignore_ignores_asset():
    with open(".gitignore") as f:
        content = f.read()
    assert "docs/assets/fig.html" in content
