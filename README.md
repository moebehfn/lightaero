# lightaero

> [!WARNING]
> **Research Disclaimer**: lightaero is a low-fidelity aerodynamics analysis library intended for academic and research purposes only. It is **not** production-ready and should not be used for industrial engineering, safety-critical applications, or any scenario where high-fidelity results are required.

lightaero provides a lightweight, easy-to-use Python framework for performing basic aerodynamic analysis and geometry generation, specifically focused on wing structures.

## Features

- Core aerodynamic analysis capabilities.
- Geometry creation for wing structures (e.g., UCRM geometry).
- 3D visualization of aerodynamic models.

## Installation

*Note: lightaero is currently in development. Packaging and 'pip install' support are planned for Phase 2.*

To use lightaero now, clone the repository and install dependencies:

```bash
git clone https://github.com/moebessd/lightaero.git
cd lightaero
pip install -r requirements.txt
```

## Quick Start

The following example demonstrates how to build a UCRM wing geometry and generate a 3D visualization:

```python
from pathlib import Path
from lightaero.geometry.ucrm import build_ucrm_geometry

# Build UCRM geometry with 4 sections
wing = build_ucrm_geometry(4)

# Generate a 3D plot and save as HTML
wing.plot_wing_3d(
    show_panels=True,
    show_sections=False,
    show_grid=False,
    pov="top",
    save_dir=Path("wing_geometry.html"),
)
```

## Citation

If you use lightaero in your research, please cite it using the metadata provided in the [CITATION.cff](./CITATION.cff) file.

## License

lightaero is released under the [Apache License 2.0](./LICENSE).

---
*For more information, see the [CONTRIBUTING.md](./CONTRIBUTING.md) guide.*
