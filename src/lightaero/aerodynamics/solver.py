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

"""VLM discipline wrapper: VLMDiscipline.

See: docs/theory/aerodynamics.md
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np

from lightaero.aerodynamics.aic import assemble_aic, build_rhs
from lightaero.aerodynamics.force import (
    near_field_forces,
    profile_drag_cd0,
    trefftz_cdi,
)
from lightaero.aerodynamics.panel_mesh import build_panel_mesh
from lightaero.atmosphere.isa import isa
from lightaero.geometry.wing import WingGeometry
from lightaero.registry import DisciplineBase, register
from lightaero.schemas.types import AERO_OUTPUT_SPEC, AeroOutput
from lightaero.schemas.validation import (
    check_regime_validity,
    validate_discipline_output,
)


@register("aero", "vlm")
class VLMDiscipline(DisciplineBase):
    """Low-fidelity VLM aerodynamics discipline.

    See: docs/theory/aerodynamics.md

    Note:
        Inputs: wing (WingGeometry), alpha_rad (float), V_ms (float), altitude_m (float).
        Returns: AeroOutput TypedDict.
        AIC matrix is cached based on geometry hash.
    """

    def __init__(self) -> None:
        self._aic_cache: np.ndarray | None = None
        self._aic_key: tuple | None = None
        self._results: AeroOutput | None = None

    def __call__(self, **inputs: Any) -> AeroOutput:
        """Evaluate VLM aerodynamics at the given flight condition.

        See: docs/theory/aerodynamics.md

        Args:
            **inputs (Any): wing, alpha_rad, V_ms (or M), altitude_m.

        Returns:
            AeroOutput: Validated results.
        """

        wing: WingGeometry = inputs["wing"]
        altitude_m: float = float(inputs["altitude_m"])
        rho, T_K, _, a = isa(altitude_m)

        if inputs.get("M", None) is not None and inputs.get("V_ms", None) is not None:
            raise ValueError("VLMDiscipline only accepts M or V_ms but not both")
        elif inputs.get("M", None) is None and inputs.get("V_ms", None) is None:
            raise ValueError("VLMDiscipline requires either M or V_ms as input.")
        elif inputs.get("M", None) is None and inputs.get("V_ms", None) is not None:
            V_ms: float = float(inputs["V_ms"])
            M = V_ms / a
        else:
            M: float = float(inputs["M"])
            V_ms = M * a

        if M >= 1.0:
            raise ValueError(f"Mach number {M:.2f} >= 1.0. Prandtl-Glauert correction is valid only for subsonic flow.")

        # Prandtl-Glauert compressibility factor
        beta = math.sqrt(1.0 - M**2)

        mesh = build_panel_mesh(wing)

        # Handle spanwise-varying alpha_rad (scalar, station-wise, or panel-wise)
        alpha_in = inputs["alpha_rad"]
        if isinstance(alpha_in, (list, np.ndarray)):
            alpha_in = np.asarray(alpha_in, dtype=np.float64)
            if len(alpha_in) == len(wing.y_stations):
                # Interpolate from stations to right semi-span control points
                alpha_cp_right = np.interp(wing.y_cp, wing.y_stations, alpha_in)
            elif len(alpha_in) == wing.n_panels:
                alpha_cp_right = alpha_in
            else:
                raise ValueError(
                    f"alpha_rad array length {len(alpha_in)} must match "
                    f"n_stations ({len(wing.y_stations)}) or n_panels ({wing.n_panels})"
                )
            # Full-span mirror: left semi-span (-tip -> root) + right semi-span (root -> tip)
            alpha_rad = np.concatenate([alpha_cp_right[::-1], alpha_cp_right])
        else:
            alpha_rad = float(alpha_in)

        # Safety Guards: Check for validity regime (Mach < 0.3, AoA < 10 deg)
        check_regime_validity(M, float(np.max(np.abs(alpha_rad))))

        epsilon = 1e-6 * 2.0 * wing.half_span

        cache_key = (
            wing.chord.tobytes(),
            wing.sweep_le.tobytes(),
            wing.y_stations.tobytes(),
            wing.n_panels,
            wing.half_span,
        )
        if self._aic_key != cache_key or self._aic_cache is None:
            self._aic_cache = assemble_aic(mesh, epsilon=epsilon)
            self._aic_key = cache_key
        AIC = self._aic_cache

        RHS = build_rhs(mesh, alpha_rad=alpha_rad, V_ms=V_ms)
        gamma = np.linalg.solve(AIC, RHS)

        CL, CDi_kj, CM, lift_N, drag_i_N, span_cl, span_load, span_drag = near_field_forces(
            mesh,
            gamma,
            rho,
            V_ms,
            mesh.S_ref,
            alpha_rad,
        )
        CDi_tp = trefftz_cdi(mesh, gamma, V_ms, mesh.S_ref)

        # Panel-local cos-sweep Prandtl-Glauert correction (A3).
        # Each strip sees an effective Mach M_eff = M * cos(local LE sweep).
        # This replaces the global beta = sqrt(1 - M^2) for span quantities.
        sweep_cp = np.interp(wing.y_cp, wing.y_stations, wing.sweep_le)
        M_eff_cp = np.clip(M * np.cos(sweep_cp), 0.0, 0.99)
        beta_cp = np.sqrt(1.0 - M_eff_cp**2)
        beta_cp = np.maximum(beta_cp, 0.01)  # numerical floor

        # Full-span mirror: left semi-span (-tip -> root) + right semi-span (root -> tip)
        beta_full = np.concatenate([beta_cp[::-1], beta_cp])

        span_cl = span_cl / beta_full
        span_load = span_load / beta_full
        span_drag = span_drag / beta_full

        # Reintegrate CL and lift_N from corrected spanwise distributions (right semi-span)
        q_inf = 0.5 * rho * V_ms**2
        CL = 2.0 * float(np.trapezoid(span_cl[wing.n_panels :] * wing.chord_cp, wing.y_cp)) / mesh.S_ref
        lift_N = CL * q_inf * mesh.S_ref

        # CDi, CM, drag_N: global Prandtl-Glauert (less sensitive to span variation)
        CDi_tp /= beta
        CM /= beta

        # Profile drag via strip theory (right semi-span only; symmetric)
        tc_stations = np.array([float(sec.thickness_at(np.array([0.35]))[0]) for sec in wing.airfoil_sections])
        tc_cp = np.interp(wing.y_cp, wing.y_stations, tc_stations)

        CD0 = profile_drag_cd0(
            rho=rho,
            V_ms=V_ms,
            T_K=T_K,
            S_ref=mesh.S_ref,
            y_cp_half=wing.y_cp,
            chord_cp_half=wing.chord_cp,
            tc_cp_half=tc_cp,
        )
        CD_total = float(CDi_tp) + CD0

        # Total Drag Force: Induced (corrected) + Viscous Profile
        drag_i_total_N = CDi_tp * q_inf * mesh.S_ref
        drag_v_total_N = CD0 * q_inf * mesh.S_ref
        drag_total_N = drag_i_total_N + drag_v_total_N

        self._results: AeroOutput = AeroOutput(
            CL=float(CL),
            CDi=float(CDi_tp),
            CD0=CD0,
            CD=CD_total,
            CM=float(CM),
            lift_N=float(lift_N),
            drag_N=float(drag_total_N),
            span_cl=span_cl,
            span_load=span_load,
            span_drag=span_drag,
            circulation=gamma,
        )

        if inputs.get("validate_output", True):
            validate_discipline_output(self._results, AERO_OUTPUT_SPEC)
        return self._results

    def __str__(self) -> str:
        if self._results is None:
            return "VLMDiscipline: No results yet. Call the discipline with valid inputs to compute aerodynamics."
        return "\n".join([
            f"Lift Coefficient           (CL) : {self._results.CL:.4e}",
            f"Drag Coefficient           (CD) : {self._results.CD:.4e}",
            f"Induced Drag Coefficient   (CDi): {self._results.CDi:.4e}",
            f"Zero-Lift Drag Coefficient (CD0): {self._results.CD0:.4e}",
            f"Coefficient of Moment      (CM) : {self._results.CM:.4e}",
        ])
