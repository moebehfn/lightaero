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

"""Aerodynamic force integration for VLM.

See: docs/theory/aerodynamics.md
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import numba
import numpy as np

from lightaero.aerodynamics.aic import _biot_savart_finite, _biot_savart_semi_infinite

if TYPE_CHECKING:
    from lightaero.aerodynamics.panel_mesh import PanelMesh


@numba.njit(cache=True)
def _induced_velocity_kernel(
    xA: np.ndarray,
    yA: np.ndarray,
    zA: np.ndarray,
    xB: np.ndarray,
    yB: np.ndarray,
    zB: np.ndarray,
    mid_x: np.ndarray,
    mid_y: np.ndarray,
    mid_z: np.ndarray,
    gamma: np.ndarray,
    u_inf_x: float,
    u_inf_y: float,
    u_inf_z: float,
    epsilon: float,
) -> np.ndarray:
    """Accumulated induced velocity at each bound-vortex midpoint.

    See: docs/theory/aerodynamics.md

    Args:
        xA, yA, zA: Bound vortex start points, shape (n,).
        xB, yB, zB: Bound vortex end points, shape (n,).
        mid_x, mid_y, mid_z: Evaluation points (bound vortex midpoints), shape (n,).
        gamma: Circulation strengths, shape (n,).
        u_inf_x, u_inf_y, u_inf_z: Freestream unit direction.
        epsilon: Rankine core regularisation fraction.

    Returns:
        v_ind: shape (n, 3) - x, y, z induced velocity at each midpoint.
    """
    n = len(gamma)
    v_ind = np.zeros((n, 3))
    for k in range(n):
        gk = gamma[k]
        if gk == 0.0:
            continue
        for j in range(n):
            Px, Py, Pz = mid_x[j], mid_y[j], mid_z[j]
            ux_b, uy_b, uz_b = _biot_savart_finite(
                xA[k],
                yA[k],
                zA[k],
                xB[k],
                yB[k],
                zB[k],
                Px,
                Py,
                Pz,
                gk,
                epsilon,
            )
            ux_r, uy_r, uz_r = _biot_savart_semi_infinite(
                xB[k],
                yB[k],
                zB[k],
                u_inf_x,
                u_inf_y,
                u_inf_z,
                Px,
                Py,
                Pz,
                gk,
                epsilon,
            )
            ux_l, uy_l, uz_l = _biot_savart_semi_infinite(
                xA[k],
                yA[k],
                zA[k],
                u_inf_x,
                u_inf_y,
                u_inf_z,
                Px,
                Py,
                Pz,
                -gk,
                epsilon,
            )

            v_ind[j, 0] += ux_b + ux_r + ux_l
            v_ind[j, 1] += uy_b + uy_r + uy_l
            v_ind[j, 2] += uz_b + uz_r + uz_l
    return v_ind


def near_field_forces(
    mesh: PanelMesh,
    gamma: np.ndarray,
    rho: float,
    V_ms: float,
    S_ref: float,
    alpha_rad: float | np.ndarray,
) -> tuple:
    """Compute near-field aerodynamic forces and coefficients.

    See: docs/theory/aerodynamics.md

    Args:
        mesh: Panel mesh object.
        gamma: Circulation strengths.
        rho: Air density.
        V_ms: Freestream speed.
        S_ref: Reference area.
        alpha_rad: Angle of attack in radians.

    Returns:
        tuple: (CL, CDi_kj, CM, lift_N, drag_N, span_cl, span_load, span_drag)
    """
    n = mesh.n_panels
    q_inf = 0.5 * rho * V_ms**2

    if isinstance(alpha_rad, np.ndarray):
        # V_inf = V_ms * [cos(alpha), 0, sin(alpha)] for each panel
        V_inf = np.stack([V_ms * np.cos(alpha_rad), np.zeros(n), V_ms * np.sin(alpha_rad)], axis=1)
        # lift_dir = [-sin(alpha), 0, cos(alpha)] for each panel
        lift_dir = np.stack([-np.sin(alpha_rad), np.zeros(n), np.cos(alpha_rad)], axis=1)
        # drag_dir = [cos(alpha), 0, sin(alpha)] for each panel
        drag_dir = np.stack([np.cos(alpha_rad), np.zeros(n), np.sin(alpha_rad)], axis=1)
    else:
        V_inf = V_ms * np.array([np.cos(alpha_rad), 0.0, np.sin(alpha_rad)])
        lift_dir = np.array([-np.sin(alpha_rad), 0.0, np.cos(alpha_rad)])
        drag_dir = np.array([np.cos(alpha_rad), 0.0, np.sin(alpha_rad)])

    epsilon = 1e-6 * 2.0 * float(np.max(np.abs(mesh.y_cp)))

    bound_mid_x = 0.5 * (mesh.xA + mesh.xB)
    bound_mid_y = 0.5 * (mesh.yA + mesh.yB)
    bound_mid_z = 0.5 * (mesh.zA + mesh.zB)

    v_ind = _induced_velocity_kernel(
        mesh.xA,
        mesh.yA,
        mesh.zA,
        mesh.xB,
        mesh.yB,
        mesh.zB,
        bound_mid_x,
        bound_mid_y,
        bound_mid_z,
        gamma,
        1.0,
        0.0,
        0.0,
        float(epsilon),
    )

    if isinstance(alpha_rad, np.ndarray):
        V_local = V_inf + v_ind
    else:
        V_local = V_inf[np.newaxis, :] + v_ind

    dl = np.stack(
        [
            mesh.xB - mesh.xA,
            mesh.yB - mesh.yA,
            mesh.zB - mesh.zA,
        ],
        axis=1,
    )

    F = rho * gamma[:, np.newaxis] * np.cross(V_local, dl)

    if isinstance(alpha_rad, np.ndarray):
        # Row-wise dot product: sum(F * dir, axis=1)
        lift_j = np.sum(F * lift_dir, axis=1)
        drag_j = np.sum(F * drag_dir, axis=1)
    else:
        lift_j = F @ lift_dir
        drag_j = F @ drag_dir

    lift_N = float(np.sum(lift_j))
    drag_N = float(np.sum(drag_j))

    CL = lift_N / (q_inf * S_ref)
    CDi_kj = drag_N / (q_inf * S_ref)

    span_cl = 2.0 * gamma / (V_ms * mesh.chord_cp)
    safe_dy = np.where(
        np.abs(mesh.yB - mesh.yA) > 1e-14,
        np.abs(mesh.yB - mesh.yA),
        1e-14,
    )

    span_load = lift_j / safe_dy
    span_drag = drag_j / safe_dy

    n_half = n // 2
    # Use right semi-span for MAC and reference point calculations (indices n_half:)
    y_right = mesh.y_cp[n_half:]
    chord_right = mesh.chord_cp[n_half:]

    MAC = (2.0 / S_ref) * float(np.trapezoid(chord_right**2, y_right))
    x_le_panel = mesh.xC[n_half:] - 0.75 * chord_right
    x_le_mac = float((2.0 / S_ref) * np.trapezoid(x_le_panel * chord_right, y_right))
    x_ref = x_le_mac + 0.25 * MAC

    moment_arm = mesh.xC - x_ref
    CM = float(-np.sum(lift_j * moment_arm) / (q_inf * S_ref * MAC))

    return CL, CDi_kj, CM, lift_N, drag_N, span_cl, span_load, span_drag


def profile_drag_cd0(
    rho: float,
    V_ms: float,
    T_K: float,
    S_ref: float,
    y_cp_half: np.ndarray,
    chord_cp_half: np.ndarray,
    tc_cp_half: np.ndarray,
) -> float:
    """Profile drag coefficient via turbulent flat-plate strip theory.

    See: docs/theory/aerodynamics.md

    Args:
        rho: Air density (kg/m³).
        V_ms: Freestream speed (m/s).
        T_K: Static temperature (K) for Sutherland viscosity.
        S_ref: Reference wing area (m²).
        y_cp_half: Spanwise CP positions for the right semi-span, shape (n_half,).
        chord_cp_half: Chord at each CP, shape (n_half,).
        tc_cp_half: Thickness-to-chord ratio at each CP, shape (n_half,).

    Returns:
        CD0: Total zero-lift profile drag coefficient (dimensionless).
    """
    # Sutherland's law for dynamic viscosity
    _mu_ref = 1.716e-5  # Pa·s at T_ref
    _T_ref = 273.15  # K
    _S = 110.4  # K  (Sutherland constant for air)
    mu = _mu_ref * (T_K / _T_ref) ** 1.5 * (_T_ref + _S) / (T_K + _S)

    Re_c = rho * V_ms * chord_cp_half / mu
    Re_c = np.maximum(Re_c, 1e4)  # floor to avoid division instability at near-zero V

    Cf = 0.074 / Re_c**0.2
    FF = 1.0 + 2.0 * tc_cp_half
    cd0_strip = 2.0 * Cf * FF  # both surfaces

    # Integrate dD0 = cd0 * c * dy over right semi-span, multiply by 2 for both sides
    q_inf = 0.5 * rho * V_ms**2
    dD0 = q_inf * cd0_strip * chord_cp_half  # force per unit span
    D0_semi = float(np.trapezoid(dD0, y_cp_half))
    CD0 = 2.0 * D0_semi / (q_inf * S_ref)
    return CD0


def trefftz_cdi(
    mesh: PanelMesh,
    gamma: np.ndarray,
    V_ms: float,
    S_ref: float,
) -> float:
    """Compute induced drag in the Trefftz plane.

    See: docs/theory/aerodynamics.md

    Args:
        mesh: Panel mesh object.
        gamma: Circulation strengths.
        V_ms: Freestream speed.
        S_ref: Reference area.

    Returns:
        CDi_tp: Induced drag coefficient.
    """
    n = len(gamma)
    y_j, z_j = mesh.yC, mesh.zC
    yA_k, zA_k, yB_k, zB_k = mesh.yA, mesh.zA, mesh.yB, mesh.zB

    eps2 = (1e-6 * 2.0 * float(np.max(np.abs(y_j)))) ** 2
    w_tp = np.zeros(n)
    v_tp = np.zeros(n)

    for j in range(n):
        Pj_y, Pj_z = y_j[j], z_j[j]
        for k in range(n):
            gk = gamma[k]
            dyB, dzB = Pj_y - yB_k[k], Pj_z - zB_k[k]
            dyA, dzA = Pj_y - yA_k[k], Pj_z - zA_k[k]
            rB2, rA2 = max(dyB**2 + dzB**2, eps2), max(dyA**2 + dzA**2, eps2)

            w_tp[j] += (gk / (2.0 * np.pi)) * (dyB / rB2 - dyA / rA2)
            v_tp[j] += (-gk / (2.0 * np.pi)) * (dzB / rB2 - dzA / rA2)

    CDi_tp = -np.sum(gamma * (w_tp * (mesh.yB - mesh.yA) - v_tp * (mesh.zB - mesh.zA))) / (V_ms**2 * S_ref)
    return float(CDi_tp)
