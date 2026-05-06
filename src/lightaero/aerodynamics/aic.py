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

"""AIC matrix assembly for VLM with Rankine core regularisation.

See: docs/theory/aerodynamics.md
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

import numba
import numpy as np

if TYPE_CHECKING:
    from lightaero.aerodynamics.panel_mesh import PanelMesh


# ---------------------------------------------------------------------------
# Biot-Savart kernels (scalar, numba @njit)
# ---------------------------------------------------------------------------


@numba.njit(cache=True)
def _biot_savart_finite(
    Ax: float,
    Ay: float,
    Az: float,
    Bx: float,
    By: float,
    Bz: float,
    Px: float,
    Py: float,
    Pz: float,
    gamma: float,
    epsilon: float,
) -> tuple:
    """Induced velocity at P by finite vortex segment A->B with strength gamma.

    Args:
        Ax, Ay, Az: Coordinates of segment start point A.
        Bx, By, Bz: Coordinates of segment end point B.
        Px, Py, Pz: Coordinates of evaluation point P.
        gamma: Vortex strength (circulation).
        epsilon: Rankine core fraction.

    Returns:
        (ux, uy, uz): Velocity components induced at P.
    """
    # r0 = B - A  (segment direction vector)
    r0x = Bx - Ax
    r0y = By - Ay
    r0z = Bz - Az

    # r1 = P - A
    r1x = Px - Ax
    r1y = Py - Ay
    r1z = Pz - Az

    # r2 = P - B
    r2x = Px - Bx
    r2y = Py - By
    r2z = Pz - Bz

    # cross = r1 x r2
    cx = r1y * r2z - r1z * r2y
    cy = r1z * r2x - r1x * r2z
    cz = r1x * r2y - r1y * r2x

    cross_sq = cx * cx + cy * cy + cz * cz

    r0_len = math.sqrt(r0x * r0x + r0y * r0y + r0z * r0z)

    # Rankine core: replace near-zero denominator
    denom = max(cross_sq, (epsilon * r0_len) ** 2)

    if denom == 0.0:
        return 0.0, 0.0, 0.0

    r1_len = math.sqrt(r1x * r1x + r1y * r1y + r1z * r1z)
    r2_len = math.sqrt(r2x * r2x + r2y * r2y + r2z * r2z)

    if r1_len < 1e-14 or r2_len < 1e-14:
        return 0.0, 0.0, 0.0

    # Dot products for cosine terms
    cos1 = (r0x * r1x + r0y * r1y + r0z * r1z) / (r0_len * r1_len)
    cos2 = (r0x * r2x + r0y * r2y + r0z * r2z) / (r0_len * r2_len)

    factor = (gamma * r0_len) / (4.0 * math.pi * denom) * (cos1 - cos2)

    ux = factor * cx
    uy = factor * cy
    uz = factor * cz
    return ux, uy, uz


@numba.njit(cache=True)
def _biot_savart_semi_infinite(
    Ax: float,
    Ay: float,
    Az: float,
    dx: float,
    dy: float,
    dz: float,
    Px: float,
    Py: float,
    Pz: float,
    gamma: float,
    epsilon: float,
) -> tuple:
    """Induced velocity at P by semi-infinite vortex starting at A.

    Args:
        Ax, Ay, Az: Start point of the semi-infinite segment.
        dx, dy, dz: Unit direction vector of the semi-infinite leg.
        Px, Py, Pz: Coordinates of evaluation point P.
        gamma: Vortex strength.
        epsilon: Rankine core fraction.

    Returns:
        (ux, uy, uz): Velocity components induced at P.
    """
    # r1 = P - A
    r1x = Px - Ax
    r1y = Py - Ay
    r1z = Pz - Az

    r1_len = math.sqrt(r1x * r1x + r1y * r1y + r1z * r1z)

    if r1_len < 1e-14:
        return 0.0, 0.0, 0.0

    # cross = d x r1
    cx = dy * r1z - dz * r1y
    cy = dz * r1x - dx * r1z
    cz = dx * r1y - dy * r1x

    cross_sq = cx * cx + cy * cy + cz * cz

    # Rankine core using r1 as the reference length
    denom = max(cross_sq, (epsilon * r1_len) ** 2)

    if denom == 0.0:
        return 0.0, 0.0, 0.0

    # cos(theta) = (d . r1) / (|d| * |r1|), |d|=1 by convention
    cos_theta = (dx * r1x + dy * r1y + dz * r1z) / r1_len

    factor = gamma / (4.0 * math.pi * denom) * (1.0 + cos_theta)

    ux = factor * cx
    uy = factor * cy
    uz = factor * cz
    return ux, uy, uz


# ---------------------------------------------------------------------------
# AIC kernel (double loop, numba @njit)
# ---------------------------------------------------------------------------


@numba.njit(cache=True)
def assemble_aic_kernel(
    xA: np.ndarray,
    yA: np.ndarray,
    zA: np.ndarray,
    xB: np.ndarray,
    yB: np.ndarray,
    zB: np.ndarray,
    xC: np.ndarray,
    yC: np.ndarray,
    zC: np.ndarray,
    nx: np.ndarray,
    ny: np.ndarray,
    nz: np.ndarray,
    epsilon: float,
    u_inf_x: float,
    u_inf_y: float,
    u_inf_z: float,
) -> np.ndarray:
    """Assemble AIC matrix kernel via explicit double loop.

    Args:
        xA (np.ndarray): Inboard bound vortex x-endpoints, shape (n,).
        yA (np.ndarray): Inboard bound vortex y-endpoints, shape (n,).
        zA (np.ndarray): Inboard bound vortex z-endpoints, shape (n,).
        xB (np.ndarray): Outboard bound vortex x-endpoints, shape (n,).
        yB (np.ndarray): Outboard bound vortex y-endpoints, shape (n,).
        zB (np.ndarray): Outboard bound vortex z-endpoints, shape (n,).
        xC (np.ndarray): Control point x-coordinates, shape (n,).
        yC (np.ndarray): Control point y-coordinates, shape (n,).
        zC (np.ndarray): Control point z-coordinates, shape (n,).
        nx (np.ndarray): Unit normal x-components, shape (n,).
        ny (np.ndarray): Unit normal y-components, shape (n,).
        nz (np.ndarray): Unit normal z-components, shape (n,).
        epsilon (float): Rankine core fraction.
        u_inf_x (float): Freestream unit direction x-component.
        u_inf_y (float): Freestream unit direction y-component.
        u_inf_z (float): Freestream unit direction z-component.

    Returns:
        np.ndarray: AIC matrix of shape (n, n).
    """
    n = xA.shape[0]
    AIC = np.zeros((n, n))

    for i in range(n):
        Px = xC[i]
        Py = yC[i]
        Pz = zC[i]
        nxi = nx[i]
        nyi = ny[i]
        nzi = nz[i]

        for j in range(n):
            # Bound segment A_j -> B_j, gamma = +1
            ux_b, uy_b, uz_b = _biot_savart_finite(
                xA[j],
                yA[j],
                zA[j],
                xB[j],
                yB[j],
                zB[j],
                Px,
                Py,
                Pz,
                1.0,
                epsilon,
            )

            # Right trailing leg: B_j -> infinity, gamma = +1
            ux_r, uy_r, uz_r = _biot_savart_semi_infinite(
                xB[j],
                yB[j],
                zB[j],
                u_inf_x,
                u_inf_y,
                u_inf_z,
                Px,
                Py,
                Pz,
                1.0,
                epsilon,
            )

            # Left trailing leg: A_j -> infinity, gamma = -1
            ux_l, uy_l, uz_l = _biot_savart_semi_infinite(
                xA[j],
                yA[j],
                zA[j],
                u_inf_x,
                u_inf_y,
                u_inf_z,
                Px,
                Py,
                Pz,
                -1.0,
                epsilon,
            )

            # Sum all contributions and project onto control-point normal
            ux = ux_b + ux_r + ux_l
            uy = uy_b + uy_r + uy_l
            uz = uz_b + uz_r + uz_l

            AIC[i, j] = ux * nxi + uy * nyi + uz * nzi

    return AIC


# ---------------------------------------------------------------------------
# Python wrapper: assemble_aic
# ---------------------------------------------------------------------------


def assemble_aic(mesh: PanelMesh, epsilon: float) -> np.ndarray:
    """Assemble the AIC matrix for a PanelMesh.

    See: docs/theory/aerodynamics.md

    Args:
        mesh: PanelMesh object.
        epsilon: Rankine core fraction.

    Returns:
        AIC: Aerodynamic Influence Coefficient matrix.

    Raises:
        AssertionError: If condition number of AIC exceeds 1e8.
    """
    AIC = assemble_aic_kernel(
        mesh.xA.astype(np.float64),
        mesh.yA.astype(np.float64),
        mesh.zA.astype(np.float64),
        mesh.xB.astype(np.float64),
        mesh.yB.astype(np.float64),
        mesh.zB.astype(np.float64),
        mesh.xC.astype(np.float64),
        mesh.yC.astype(np.float64),
        mesh.zC.astype(np.float64),
        mesh.nx.astype(np.float64),
        mesh.ny.astype(np.float64),
        mesh.nz.astype(np.float64),
        float(epsilon),
        1.0,
        0.0,
        0.0,  # freestream unit direction
    )

    cond = np.linalg.cond(AIC)
    assert cond < 1e8, (
        f"AIC condition number {cond:.3e} >= 1e8: mesh may be degenerate (n_panels={mesh.n_panels}, epsilon={epsilon})"
    )

    return AIC


# ---------------------------------------------------------------------------
# Python function: build_rhs
# ---------------------------------------------------------------------------


def build_rhs(mesh: PanelMesh, alpha_rad: float | np.ndarray, V_ms: float = 1.0) -> np.ndarray:
    """Build the right-hand side vector for the VLM linear system.

    See: docs/theory/aerodynamics.md

    Args:
        mesh: PanelMesh with unit normals.
        alpha_rad: Angle of attack (radians).
        V_ms: Freestream speed (m/s).

    Returns:
        RHS: shape (n_panels,).
    """
    if isinstance(alpha_rad, (np.ndarray, list)):
        alpha_rad = np.asarray(alpha_rad, dtype=np.float64)
        vx = V_ms * np.cos(alpha_rad)
        vy = np.zeros_like(alpha_rad)
        vz = V_ms * np.sin(alpha_rad)
    else:
        vx = V_ms * math.cos(alpha_rad)
        vy = 0.0
        vz = V_ms * math.sin(alpha_rad)

    # RHS[i] = -(V_inf . n_hat_i)
    RHS = -(vx * mesh.nx + vy * mesh.ny + vz * mesh.nz)
    return RHS.astype(np.float64)


# ---------------------------------------------------------------------------
# Module-level warmup: force numba compilation at import time
# ---------------------------------------------------------------------------
# This avoids a 1-3 second JIT compilation penalty on the first real call.
# The try/except swallows shape errors on dummy arrays; the point is to
# trigger @njit compilation regardless of the dummy data's geometric validity.

if not hasattr(assemble_aic_kernel, "_numba_type_"):
    _dummy = np.zeros(2, dtype=np.float64)
    try:
        assemble_aic_kernel(
            _dummy,
            _dummy,
            _dummy,
            _dummy,
            _dummy,
            _dummy,
            _dummy,
            _dummy,
            _dummy,
            _dummy,
            _dummy,
            _dummy,
            1e-6,
            1.0,
            0.0,
            0.0,
        )
    except Exception:
        pass
