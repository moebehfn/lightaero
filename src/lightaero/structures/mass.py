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

"""Wing structural mass integration and OEW empirical estimation.

See: docs/theory/structures.md
"""

from __future__ import annotations

import math

import numpy as np

__all__ = ["wing_structural_mass", "estimate_oew"]


def wing_structural_mass(
    y_nodes: np.ndarray,
    t_sk: np.ndarray,
    h: np.ndarray,
    w: np.ndarray,
    rho_mat: float = 2780.0,
    k_struct: float = 1.5,
) -> float:
    """Integrated wing structural mass.

    Args:
        y_nodes: Spanwise node positions (m).
        t_sk: Skin thickness at each node (m).
        h: Section height at each node (m).
        w: Section width at each node (m).
        rho_mat: Material density (kg/m³).
        k_struct: Structural mass factor.

    Returns:
        mass: Total wing mass (kg).
    """
    # Rectangular thin-wall perimeter approximation
    A_cross = 2.0 * t_sk * (w + h)
    m_per_span = rho_mat * A_cross * k_struct
    m_semi = np.trapezoid(m_per_span, y_nodes)
    return 2.0 * m_semi


def estimate_oew(
    MTOW_kg: float,
    wing_mass_kg: float,
    S_ref_m2: float | None = None,
) -> float:
    """Estimate operating empty weight using Roskam log-linear regression.

    Args:
        MTOW_kg: Maximum take-off weight (kg).
        wing_mass_kg: Wing structural mass (kg).
        S_ref_m2: Reference wing area (m²).

    Returns:
        OEW: Estimated operating empty weight (kg).
    """

    MTOW_safe = max(MTOW_kg, 1.0)
    oew_roskam = 10.0 ** (-0.0833 + 0.9647 * math.log10(MTOW_safe))
    oew_floor = wing_mass_kg * 1.3
    return max(oew_roskam, oew_floor)
