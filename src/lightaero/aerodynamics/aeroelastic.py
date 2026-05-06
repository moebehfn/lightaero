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

"""Aeroelastic discipline: coupled VLM + Euler-Bernoulli beam iteration.

Iterates VLM and structural solvers to predict spanwise deflection and twist.
See: docs/theory/aerodynamics.md
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from lightaero.aerodynamics.solver import VLMDiscipline
from lightaero.geometry.wing import WingGeometry, build_wing_geometry
from lightaero.registry import DisciplineBase, register
from lightaero.schemas.types import AeroOutput, StructuralOutput
from lightaero.structures.solver import StructuralDiscipline

__all__ = ["AerostructDiscipline", "AerostructOutput"]

_CONV_TOL: float = 0.01  # m  - convergence threshold on deflection
_MAX_ITER: int = 15  # safety cap on iteration count


@dataclass
class AerostructOutput:
    """Combined aerostructural result from AerostructDiscipline.

    Attributes:
        aero: Final AeroOutput (CL, CDi, CM, lift_N, drag_N, span_cl,
              span_load, span_drag) from the last VLM evaluation.
        struct: Final StructuralOutput (tip_deflection_m, root_stress_Pa,
                wing_mass_kg, oew_kg, span_deflection, tip_twist_rad,
                span_twist) from the last structural evaluation.
        n_iter: Number of coupling iterations performed.
        converged: True if convergence criterion was met before _MAX_ITER.
    """

    aero: AeroOutput
    struct: StructuralOutput
    n_iter: int
    converged: bool


def _rebuild_wing(
    wing: WingGeometry,
    deflection_z: np.ndarray,
    delta_twist: np.ndarray,
) -> WingGeometry:
    """Rebuild a WingGeometry with updated deflection and elastic twist.

    Args:
        wing: Original (or previous-iteration) WingGeometry.
        deflection_z: Nodal vertical deflections (m), shape (n_panels+1,).
        delta_twist: Elastic twist increment at each y_station (rad),
            shape matching wing.y_stations. Added to wing.twist.

    Returns:
        New frozen WingGeometry with the given deflection and twist.
    """
    return build_wing_geometry(
        half_span=wing.half_span,
        n_panels=wing.n_panels,
        y_stations=wing.y_stations,
        chord=wing.chord,
        sweep_le=wing.sweep_le,
        taper=wing.taper,
        twist=wing.twist + delta_twist,
        airfoil_sections=wing.airfoil_sections,
        deflection_z=deflection_z,
    )


@register("aerostruct", "vlm_euler_beam")
class AerostructDiscipline(DisciplineBase):
    """Static aeroelastic discipline: VLM coupled to Euler-Bernoulli beam.

    See: docs/theory/aerodynamics.md
    """

    def __init__(self) -> None:
        self._vlm = VLMDiscipline()
        self._struct = StructuralDiscipline()

    def __call__(self, **inputs: Any) -> AerostructOutput:
        """Evaluate the coupled aerostructural discipline.

        Args:
            **inputs: Named physical quantities in SI units.
                wing (WingGeometry): Undeformed wing geometry.
                alpha_rad (float): Angle of attack in radians.
                altitude_m (float): Altitude in metres.
                MTOW_kg (float): Maximum take-off weight in kg.
                V_ms (float) | M (float): Freestream speed or Mach number (not both).

        Returns:
            AerostructOutput: Combined results including aero, struct, n_iter, and converged status.
        """
        wing: WingGeometry = inputs["wing"]
        MTOW_kg: float = float(inputs["MTOW_kg"])

        # Forward aero inputs to VLM (alpha, altitude, speed)
        aero_inputs = {k: inputs[k] for k in ("alpha_rad", "altitude_m") if k in inputs}
        if "V_ms" in inputs:
            aero_inputs["V_ms"] = inputs["V_ms"]
        elif "M" in inputs:
            aero_inputs["M"] = inputs["M"]

        # State at start of iteration
        deflection_z = np.zeros(wing.n_panels + 1, dtype=float)
        delta_twist = np.zeros_like(wing.twist)  # shape (n_stations,)

        # y_nodes used to map structural twist (at VLM nodes) to y_stations
        y_nodes = np.concatenate([[0.0], wing.y_cp])

        aero: AeroOutput | None = None
        struct: StructuralOutput | None = None
        converged = False

        for _n_iter in range(1, _MAX_ITER + 1):
            wing_def = _rebuild_wing(wing, deflection_z, delta_twist)

            aero = self._vlm(wing=wing_def, **aero_inputs)
            struct = self._struct(
                wing=wing_def,
                span_load=aero.span_load,
                span_drag=aero.span_drag,
                MTOW_kg=MTOW_kg,
            )

            new_deflection = np.asarray(struct.span_deflection, dtype=float)
            change = float(np.max(np.abs(new_deflection - deflection_z)))

            # Interpolate elastic twist from y_nodes to y_stations for geometry rebuild
            new_delta_twist = np.interp(wing.y_stations, y_nodes, np.asarray(struct.span_twist, dtype=float))

            deflection_z = new_deflection
            delta_twist = new_delta_twist

            if change < _CONV_TOL:
                converged = True
                break

        return AerostructOutput(
            aero=aero,
            struct=struct,
            n_iter=_n_iter,
            converged=converged,
        )
