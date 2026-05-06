# Copyright 2026 lightaero
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import ast
import os

import pytest


def get_clean_body_length(docstring):
    if not docstring:
        return 0

    body_lines = []
    sections = ["Args:", "Returns:", "Raises:", "Yields:", "Note:", "Example:", "Examples:", "Attributes:"]

    for line in docstring.splitlines():
        stripped = line.strip()
        if any(stripped.startswith(s) for s in sections):
            break
        body_lines.append(line)

    return len([l for l in body_lines if l.strip()])


def has_doc_link(docstring):
    if not docstring:
        return False
    return "See: docs/theory/" in docstring or "docs/theory/" in docstring


@pytest.mark.parametrize(
    "rel_path",
    [
        "src/lightaero/aerodynamics/__init__.py",
        "src/lightaero/aerodynamics/aeroelastic.py",
        "src/lightaero/aerodynamics/aic.py",
        "src/lightaero/aerodynamics/force.py",
        "src/lightaero/aerodynamics/panel_mesh.py",
        "src/lightaero/aerodynamics/solver.py",
        "src/lightaero/atmosphere/isa.py",
        "src/lightaero/geometry/airfoil.py",
        "src/lightaero/geometry/crm.py",
        "src/lightaero/geometry/dlrf4.py",
        "src/lightaero/geometry/dlrf6.py",
        "src/lightaero/geometry/ucrm.py",
        "src/lightaero/geometry/wing.py",
        "src/lightaero/registry/registry.py",
        "src/lightaero/schemas/types.py",
        "src/lightaero/schemas/validation.py",
        "src/lightaero/structures/__init__.py",
        "src/lightaero/structures/beam.py",
        "src/lightaero/structures/mass.py",
    ],
)
def test_docstring_minimization(rel_path):
    # Base directory of the project
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    full_path = os.path.join(base_dir, rel_path)

    if not os.path.exists(full_path):
        pytest.skip(f"File {rel_path} does not exist")

    with open(full_path) as f:
        tree = ast.parse(f.read())

    # Track if we found a link in any docstring in this file
    found_link = False

    # Check module docstring
    module_doc = ast.get_docstring(tree)
    if module_doc:
        length = get_clean_body_length(module_doc)
        assert length <= 10, f"Module docstring in {rel_path} too long: {length} lines"
        if has_doc_link(module_doc):
            found_link = True

    # Check classes and functions
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            doc = ast.get_docstring(node)
            if doc:
                length = get_clean_body_length(doc)
                assert length <= 10, f"Docstring in {rel_path} for {node.name} too long: {length} lines"
                if has_doc_link(doc):
                    found_link = True

    assert found_link, f"File {rel_path} missing 'See: docs/theory/...' link in module or class/function docstrings"
