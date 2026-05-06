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

"""StructuralDiscipline: compose beam.py and mass.py into a single discipline call."""

from __future__ import annotations

from typing import Any

import numpy as np

from lightaero.registry import DisciplineBase, register
from lightaero.schemas.types import STRUCTURAL_OUTPUT_SPEC, StructuralOutput
from lightaero.schemas.validation import validate_discipline_output
from lightaero.structures.beam import (
    beam_section_properties,
    build_bending_loads,
    build_torsion_loads,
    compute_combined_stress,
    size_skin_thickness,
    solve_bending_beam,
    solve_torsion_beam,
)
from lightaero.structures.mass import estimate_oew, wing_structural_mass

__all__ = ["StructuralDiscipline"]


@register("structures", "euler_beam")
class StructuralDiscipline(DisciplineBase):
    def __call__(self, **inputs: Any) -> Any:
        wing = inputs["wing"]

        # Aero results are full-span [-tip -> tip]. Use right semi-span [root -> tip]
        # for structural analysis (indices n_panels:).
        span_load = np.asarray(inputs["span_load"], dtype=float)[wing.n_panels :]
        if "span_drag" in inputs:
            span_drag = np.asarray(inputs["span_drag"], dtype=float)[wing.n_panels :]
        else:
            span_drag = np.zeros_like(span_load)

        MTOW_kg = float(inputs["MTOW_kg"])
        # Spar thickness provided by the optimizer (x2)
        # Interpolate from stations (if provided at stations) to nodal discretization
        t_spar_in = np.asarray(inputs["spar_thickness"], dtype=float)

        y_nodes = np.concatenate([[0.0], wing.y_cp])
        chord_nodes = np.concatenate([[wing.chord[0]], wing.chord_cp])

        tc_stations = np.array([sec.thickness_at(np.array([0.35]))[0] for sec in wing.airfoil_sections])
        tc_nodes = np.interp(y_nodes, wing.y_stations, tc_stations)

        # Size skin thickness to bending allowable before computing stiffness
        q_z_nodes = np.concatenate([[span_load[0]], span_load])
        if len(t_spar_in) == len(wing.y_stations):
            t_sk = np.interp(y_nodes, wing.y_stations, t_spar_in)
        elif len(t_spar_in) == wing.n_panels:
            t_sk = np.concatenate([[t_spar_in[0]], t_spar_in])
        else:
            t_sk = size_skin_thickness(y_nodes, chord_nodes, tc_nodes, q_z_nodes)

        EI_xx, EI_zz, GJ, h, w, I_xx, I_zz, A_e, x_sc_nodes = beam_section_properties(
            y_nodes=y_nodes,
            chord_nodes=chord_nodes,
            tc_ratio_nodes=tc_nodes,
            E_Pa=inputs.get("E_Pa", 73.1e9),
            G_Pa=inputs.get("G_Pa", 28.0e9),
            t_sk_array=t_sk,
        )

        q_x_nodes = np.concatenate([[span_drag[0]], span_drag])

        # Torque arm = (x_sc - x_aero_center) where x_aero_center = 0.25 * chord
        x_sc_cp = np.interp(wing.y_cp, y_nodes, x_sc_nodes)
        torque_arm_cp = x_sc_cp / wing.chord_cp - 0.25  # dimensionless
        torque_cp = span_load * torque_arm_cp * wing.chord_cp
        torque_nodes = np.concatenate([[torque_cp[0]], torque_cp])
        T_y = build_torsion_loads(y_nodes, torque_nodes)

        # --- Geometric nonlinearity: follower-force iteration ---
        # Re-project aero loads onto the deformed beam axis at each iteration.
        # q_z_eff = q_z * cos(θ), q_x_eff += q_z * sin(θ) (follower correction)
        # Iterate until tip deflection converges to within 1 cm.
        _GNL_TOL = 0.01  # m
        _GNL_MAX_ITER = 10

        q_z_eff = q_z_nodes.copy()
        q_x_eff = q_x_nodes.copy()
        tip_prev = 0.0

        for _iter in range(_GNL_MAX_ITER):
            F_z = build_bending_loads(y_nodes, q_z_eff)
            F_x = build_bending_loads(y_nodes, q_x_eff)
            w_full = solve_bending_beam(y_nodes, EI_xx, F_z)
            u_full = solve_bending_beam(y_nodes, EI_zz, F_x)
            tip_def = float(w_full[-2])
            if abs(tip_def - tip_prev) < _GNL_TOL:
                break
            tip_prev = tip_def
            # Nodal slope from Hermite DOF vector: θ_i = w_full[2*i + 1]
            theta = w_full[1::2]  # shape (n_nodes,)
            cos_t = np.cos(theta)
            sin_t = np.sin(theta)
            q_z_eff = q_z_nodes * cos_t
            q_x_eff = q_x_nodes + q_z_nodes * sin_t  # follower in-plane component

        phi_full = solve_torsion_beam(y_nodes, GJ, T_y)

        tip_deflection_m = float(w_full[-2])
        tip_twist_rad = float(phi_full[-1])

        stress = compute_combined_stress(
            y_nodes,
            w_full,
            u_full,
            EI_xx,
            EI_zz,
            h,
            w,
            I_xx,
            I_zz,
            phi_full=phi_full,
            GJ=GJ,
            A_e=A_e,
            t_sk=t_sk,
        )
        root_stress_Pa = float(stress[0])

        wing_mass_kg = wing_structural_mass(y_nodes, t_sk, h, w)
        oew_kg = estimate_oew(MTOW_kg, wing_mass_kg)

        result: StructuralOutput = StructuralOutput(
            tip_deflection_m=tip_deflection_m,
            root_stress_Pa=root_stress_Pa,
            wing_mass_kg=wing_mass_kg,
            oew_kg=oew_kg,
            span_deflection=w_full[::2],
            tip_twist_rad=tip_twist_rad,
            span_twist=phi_full,
            span_stress=stress,
        )
        if inputs.get("validate_output", True):
            validate_discipline_output(result, STRUCTURAL_OUTPUT_SPEC)
        return result
