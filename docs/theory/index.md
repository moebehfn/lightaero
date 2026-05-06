# Theory & Physics

This page contains detailed information about the aerodynamic physics, geometric modeling, and assumptions of the lightaero library.

## Geometry Modeling

lightaero uses a parametric approach to define wing geometries, supporting both analytic (NACA 4-digit) and tabulated (UIUC .dat) airfoil sections.

### Airfoil Sections

#### NACA 4-digit Airfoils
Analytic airfoil profiles are generated using the standard NACA 4-digit equations (NACA Report 460).

The camberline ordinate $z_c/c$ is defined by:
$$
z_c/c = 
\begin{cases} 
\frac{M}{P^2} (2Px - x^2) & 0 \le x < P \\
\frac{M}{(1-P)^2} ((1-2P) + 2Px - x^2) & P \le x \le 1
\end{cases}
$$
where $M$ is the maximum camber and $P$ is the position of maximum camber.

The half-thickness distribution $t/c$ is given by:
$$
t/c = \frac{T}{0.2} (0.2969\sqrt{x} - 0.1260x - 0.3516x^2 + 0.2843x^3 - 0.1015x^4)
$$
where $T$ is the maximum thickness.

**Important Note:** The NACA 4-digit camberline slope $dz_c/dx$ is discontinuous at $x = P$. For Vortex Lattice Method (VLM) implementations requiring panel normals, one-sided finite differences should be used near this position.

#### Tabulated Airfoils (UIUC .dat)
lightaero supports loading airfoil coordinates from UIUC-style `.dat` files. It automatically detects both Selig (TE $\to$ LE $\to$ TE) and Lednicer (separate upper and lower surface) formats.

### Wing Geometry

Wings are defined by spanwise stations where planform parameters (chord, sweep, twist, airfoil) are specified. 

#### Spanwise Interpolation
Between defined stations, the geometry is linearly interpolated. For airfoil profiles, this means blending the normalized upper and lower surface coordinates:
$$
(x, z)_{blended} = (1 - \alpha)(x, z)_0 + \alpha(x, z)_1
$$
where $\alpha$ is the fractional distance between stations.

#### Cosine Spacing
To improve accuracy near the wing root and tip (where gradients are high), lightaero uses cosine spacing for spanwise paneling:
$$
y_{node} = \frac{b}{4} (1 - \cos(\theta)), \quad \theta \in [0, \pi]
$$
where $b/2$ is the semi-span.

## Reference Models

lightaero includes several standard research geometries for benchmarking and validation.

### DLR-F4
The DLR-F4 is a generic transport wing-body configuration from the first AIAA Drag Prediction Workshop (DPW-I, 2001).
- **Reference:** Redeker, G. et al., "Drag Prediction Workshop I Test Case," AIAA Paper 2001-1086.
- **Model:** Isolated trapezoidal wing.

### DLR-F6
The DLR-F6 is a transonic transport configuration from the second AIAA Drag Prediction Workshop (DPW-II, 2003).
- **Reference:** Laflin, K. R. et al., "Data Summary from Second AIAA Computational Fluid Dynamics Drag Prediction Workshop," AIAA Paper 2004-0555.
- **Model:** Isolated wing with a Yehudi break (cranked planform).

### NASA Common Research Model (CRM)
The CRM is a modern transport configuration designed for CFD validation.
- **Reference:** Vassberg et al., "The NASA Common Research Model (CRM): A New Wing-Body Configuration for CFD Validation," AIAA Paper 2008-6919.
- **Model:** Isolated trapezoidal approximation.

### NASA uCRM
The "unmodified" CRM (uCRM) provides a more detailed station-based definition of the CRM geometry.

## Assumptions & Limitations

lightaero is intended for research-grade low-fidelity analysis and makes several simplifying assumptions to ensure computational efficiency.

Key limitations include:
- **Aerodynamics**: Incompressible, inviscid VLM (strictly valid for Mach < 0.3, AoA < 10°).
- **Structures**: Linear elastic Euler-Bernoulli beams (static analysis only).
- **Atmosphere**: ISA model based on geometric altitude.

For a detailed breakdown of validity regimes and physical limits, see the [Assumptions & Limitations](assumptions.md) page.

## Registry and Fidelity Swapping

lightaero uses a two-level namespace registry (family $\to$ key $\to$ class) to allow discipline implementations to be swapped by string key without modifying coupling logic.

### Registration Pattern

Disciplines are registered using the `@register` decorator. This populates a module-level singleton dictionary at import time.

### Fidelity Selection

This architecture allows zero-change implementation swapping. A coupling algorithm can request a discipline by its family (e.g., 'aero') and key (e.g., 'vlm' vs 'low_fi'), ensuring the interface remains identical across different fidelity levels.

### Design Decisions

- **Two-level namespace**: Organized by family + key.
- **Decorator-based**: Simple, import-time registration.
- **Minimal Interface**: `DisciplineBase` enforces a single `__call__` method.
- **Zero-Dependency Interface**: The registry and base class have no external dependencies on MDO frameworks.

## Data Contracts and Validation

lightaero uses a structured data contract for inter-discipline communication, ensuring that outputs from one discipline are valid and plausible before being passed to another.

### Output Schemas

Discipline outputs are defined as `dataclass` structures. This provides clear documentation of the expected fields and types.

### Plausibility Bounds

Each output schema is accompanied by a companion specification dictionary. This dictionary defines:

- **Type**: The expected Python type (e.g., `float`, `np.ndarray`).
- **Bounds**: Plausible physical ranges for scalars.
- **Shape**: Expected dimensions for arrays.

### Unit Violation Detection

Bounds serve as a primary defense against unit mismatches. For example, a lift coefficient ($C_L$) of 1000 would fail a plausibility check (typically bounded between -2.0 and 5.0), indicating that the values might have been provided in degrees or another non-dimensionless unit.

### Runtime Validation

The `validate_discipline_output` function enforces these contracts at runtime, catching bugs and unit errors immediately at the discipline boundary.
