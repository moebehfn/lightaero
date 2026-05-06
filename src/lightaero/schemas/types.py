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

"""Output schemas and companion runtime spec dicts.

These schemas define the inter-discipline data contract for lightaero.

See: docs/theory/index.md
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

# ---------------------------------------------------------------------------
# ISA Atmosphere
# ---------------------------------------------------------------------------


@dataclass
class ISAOutput:
    rho: float
    T: float
    p: float
    a: float


ISA_OUTPUT_SPEC: dict = {
    "rho": {"type": float, "bounds": (1e-4, 1.5)},
    "T": {"type": float, "bounds": (150.0, 320.0)},
    "p": {"type": float, "bounds": (1e3, 1.1e5)},
    "a": {"type": float, "bounds": (200.0, 360.0)},
}

# ---------------------------------------------------------------------------
# Aerodynamics
# ---------------------------------------------------------------------------


@dataclass
class AeroOutput:
    CL: float
    CDi: float
    CD0: float  # profile (viscous) drag coefficient
    CD: float  # total drag coefficient = CDi + CD0
    CM: float
    lift_N: float
    drag_N: float
    span_cl: np.ndarray
    span_load: np.ndarray
    span_drag: np.ndarray
    circulation: np.ndarray


AERO_OUTPUT_SPEC: dict = {
    "CL": {"type": float, "bounds": (-2.0, 5.0)},
    "CDi": {"type": float, "bounds": (0.0, 1.0)},
    "CD0": {"type": float, "bounds": (0.0, 0.1)},
    "CD": {"type": float, "bounds": (0.0, 1.0)},
    "CM": {"type": float, "bounds": (-5.0, 5.0)},
    "lift_N": {"type": float, "bounds": (None, None)},
    "drag_N": {"type": float, "bounds": (None, None)},
    "span_cl": {"type": np.ndarray, "shape_dim": 1},
    "span_load": {"type": np.ndarray, "shape_dim": 1},
    "span_drag": {"type": np.ndarray, "shape_dim": 1},
    "circulation": {"type": np.ndarray, "shape_dim": 1},
}

# ---------------------------------------------------------------------------
# Structures
# ---------------------------------------------------------------------------


@dataclass
class StructuralOutput:
    tip_deflection_m: float
    root_stress_Pa: float
    wing_mass_kg: float
    oew_kg: float
    span_deflection: np.ndarray
    tip_twist_rad: float
    span_twist: np.ndarray
    span_stress: np.ndarray


STRUCTURAL_OUTPUT_SPEC: dict = {
    "tip_deflection_m": {"type": float, "bounds": (-10.0, 20.0)},
    "root_stress_Pa": {"type": float, "bounds": (0.0, 1e9)},
    "wing_mass_kg": {"type": float, "bounds": (100.0, 1e5)},
    "oew_kg": {"type": float, "bounds": (500.0, 5e5)},
    "span_deflection": {"type": np.ndarray, "shape_dim": 1},
    "tip_twist_rad": {"type": float, "bounds": (-1.5, 1.5)},
    "span_twist": {"type": np.ndarray, "shape_dim": 1},
    "span_stress": {"type": np.ndarray, "shape_dim": 1},
}

# ---------------------------------------------------------------------------
# Propulsion
# ---------------------------------------------------------------------------


@dataclass
class PropulsionOutput:
    thrust_N: float
    TSFC_kg_per_N_per_s: float


PROPULSION_OUTPUT_SPEC: dict = {
    "thrust_N": {"type": float, "bounds": (0.0, 5e6)},
    "TSFC_kg_per_N_per_s": {"type": float, "bounds": (1e-6, 1e-3)},
}

# ---------------------------------------------------------------------------
# Mission
# ---------------------------------------------------------------------------


@dataclass
class MissionOutput:
    L_over_D: float
    SAR_m_per_kg: float
    CL_opt: float
    altitude_opt_m: float
    thrust_required_N: float
    fuel_flow_kg_per_s: float


MISSION_OUTPUT_SPEC: dict = {
    "L_over_D": {"type": float, "bounds": (1.0, 30.0)},
    "SAR_m_per_kg": {"type": float, "bounds": (0.0, 1e6)},
    "CL_opt": {"type": float, "bounds": (0.1, 2.0)},
    "altitude_opt_m": {"type": float, "bounds": (0.0, 20000.0)},
    "thrust_required_N": {"type": float, "bounds": (0.0, 5e6)},
    "fuel_flow_kg_per_s": {"type": float, "bounds": (0.0, 100.0)},
}
