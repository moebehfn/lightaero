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

"""Panel mesh generation for VLM aerodynamic analysis.

See: docs/theory/aerodynamics.md
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from lightaero.geometry.airfoil import interpolate_camber
from lightaero.geometry.wing import WingGeometry


@dataclass
class PanelMesh:
    """3D panel mesh for VLM analysis.

    See: docs/theory/aerodynamics.md

    Attributes:
        n_panels: Total panel count (int).
        xA, yA, zA: Bound vortex A-endpoint (inboard node) at quarter-chord.
        xB, yB, zB: Bound vortex B-endpoint (outboard node) at quarter-chord.
        xC, yC, zC: Control point (collocation point) at three-quarter-chord.
        nx, ny, nz: Unit normal at each control point.
        chord_cp: Chord length at each control-point.
        y_cp: Spanwise CP coordinate.
        S_ref: Full planform reference area.

    Note:
        All computation here is pure Python/NumPy. No @numba.njit functions
        are used in panel geometry. Extract array fields explicitly if
        passing to compiled functions.
    """

    n_panels: int
    xA: np.ndarray
    yA: np.ndarray
    zA: np.ndarray
    xB: np.ndarray
    yB: np.ndarray
    zB: np.ndarray
    xC: np.ndarray
    yC: np.ndarray
    zC: np.ndarray
    nx: np.ndarray
    ny: np.ndarray
    nz: np.ndarray
    chord_cp: np.ndarray
    y_cp: np.ndarray
    S_ref: float


def build_panel_mesh(wing: WingGeometry) -> PanelMesh:
    """Convert WingGeometry into a full-span 3D PanelMesh.

    See: docs/theory/aerodynamics.md

    Args:
        wing: Frozen WingGeometry from build_wing_geometry().

    Returns:
        PanelMesh: The generated mesh.
    """
    n = wing.n_panels  # number of panels per semi-span

    # ------------------------------------------------------------------
    # Step 1: Spanwise nodes for the right semi-span (n+1 nodes)
    # Using the same cosine-spacing formula as WingGeometry._cosine_y_cp
    # but for nodes (not CPs) so that CPs from wing.y_cp are consistent.
    # ------------------------------------------------------------------
    theta = np.linspace(0.0, np.pi, n + 1)
    y_nodes = (wing.half_span / 2.0) * (1.0 - np.cos(theta))  # shape (n+1,)

    # ------------------------------------------------------------------
    # Step 2: Leading-edge x-offset and chord at spanwise nodes
    # x_le(y) = cumulative integral of tan(sweep_le) over y_stations
    # ------------------------------------------------------------------
    # x_le at each y_station break (cumulative sum of dx per segment)
    dx_le = np.diff(wing.y_stations) * np.tan(wing.sweep_le[:-1])
    x_le_at_stations = np.concatenate([[0.0], np.cumsum(dx_le)])  # shape (n_sections,)

    # Interpolate to nodes and to CPs
    x_le_nodes = np.interp(y_nodes, wing.y_stations, x_le_at_stations)  # shape (n+1,)
    x_le_cp = np.interp(wing.y_cp, wing.y_stations, x_le_at_stations)  # shape (n,)

    chord_nodes = np.interp(y_nodes, wing.y_stations, wing.chord)  # shape (n+1,)

    # ------------------------------------------------------------------
    # Step 3: Camber heights at nodes and CPs for z-coordinates
    # zA/zB at nodes (x=0.25c); zC at CPs (x=0.75c)
    # ------------------------------------------------------------------
    sections_list = list(wing.airfoil_sections)
    x_qc = np.array([0.25])
    x_tqc = np.array([0.75])

    # z at bound vortex endpoints (quarter-chord of each panel node)
    z_at_nodes = np.array(
        [
            chord_nodes[j] * float(interpolate_camber(y_nodes[j], wing.y_stations, sections_list, x_qc)[0])
            for j in range(n + 1)
        ]
    )  # shape (n+1,)
    z_at_nodes += wing.deflection_z

    # z at control points (three-quarter-chord)
    z_cp = np.array(
        [
            wing.chord_cp[j] * float(interpolate_camber(wing.y_cp[j], wing.y_stations, sections_list, x_tqc)[0])
            for j in range(n)
        ]
    )  # shape (n,)
    deflection_cp = 0.5 * (wing.deflection_z[:-1] + wing.deflection_z[1:])
    z_cp += deflection_cp

    # ------------------------------------------------------------------
    # Step 4: Bound vortex endpoints (right semi-span, panels 0..n-1)
    # Panel j runs from node j (inboard) to node j+1 (outboard)
    # ------------------------------------------------------------------
    xA_r = x_le_nodes[:-1] + 0.25 * chord_nodes[:-1]  # shape (n,)
    yA_r = y_nodes[:-1]
    zA_r = z_at_nodes[:-1]

    xB_r = x_le_nodes[1:] + 0.25 * chord_nodes[1:]  # shape (n,)
    yB_r = y_nodes[1:]
    zB_r = z_at_nodes[1:]

    # ------------------------------------------------------------------
    # Step 5: Control points (right semi-span, from wing.y_cp)
    # ------------------------------------------------------------------
    xC_r = x_le_cp + 0.75 * wing.chord_cp  # shape (n,)
    yC_r = wing.y_cp.copy()
    zC_r = z_cp

    # ------------------------------------------------------------------
    # Step 6: Unit normals at control points
    # The effective angle alpha_eff = twist + camberline slope at 3qc.
    # Normal hat = (-sin(alpha_eff), 0, cos(alpha_eff)) -- then normalised.
    # For NACA sections with ny=0 (no sweep-induced spanwise normal component
    # in strip theory), the normal lies in the xz-plane.
    # ------------------------------------------------------------------
    # Camberline slope dz_c/dx at x=0.75c for each CP
    slopes = np.zeros(n)
    for j in range(n):
        y_j = wing.y_cp[j]
        # Determine the two bracketing airfoil sections
        idx = int(
            np.clip(
                np.searchsorted(wing.y_stations, y_j, side="right") - 1,
                0,
                len(wing.y_stations) - 2,
            )
        )
        y0 = float(wing.y_stations[idx])
        y1 = float(wing.y_stations[idx + 1])
        alpha = (y_j - y0) / (y1 - y0) if y1 > y0 else 0.0

        # Slope at x=0.75c from section idx
        slope_0 = _camber_slope_at_3qc(wing.airfoil_sections[idx])
        # Slope at x=0.75c from section idx+1
        slope_1 = _camber_slope_at_3qc(wing.airfoil_sections[idx + 1])

        slopes[j] = (1.0 - alpha) * slope_0 + alpha * slope_1

    alpha_eff = wing.twist_cp + slopes  # shape (n,)

    nx_r = -np.sin(alpha_eff)
    ny_r = np.zeros(n)
    nz_r = np.cos(alpha_eff)

    # Normalise to unit length (already ~1 for small angles, but be exact)
    mag = np.sqrt(nx_r**2 + ny_r**2 + nz_r**2)
    nx_r = nx_r / mag
    ny_r = ny_r / mag
    nz_r = nz_r / mag

    # ------------------------------------------------------------------
    # Step 7: Mirror for left semi-span (panels n..2n-1)
    # The left semi-span uses reversed panel ordering so that the
    # inboard-to-outboard convention is preserved (outboard = more negative y).
    # Endpoint A on the right becomes B on the left (and vice versa).
    # ------------------------------------------------------------------
    xA_l = xB_r[::-1]
    yA_l = -yB_r[::-1]
    zA_l = zB_r[::-1]

    xB_l = xA_r[::-1]
    yB_l = -yA_r[::-1]
    zB_l = zA_r[::-1]

    xC_l = xC_r[::-1]
    yC_l = -yC_r[::-1]
    zC_l = zC_r[::-1]

    nx_l = nx_r[::-1]
    ny_l = -ny_r[::-1]  # Invert spanwise normal component only
    nz_l = nz_r[::-1]

    chord_cp_l = wing.chord_cp[::-1]

    # ------------------------------------------------------------------
    # Assemble full-span arrays (left then right)
    # The left semi-span occupies indices 0 .. n-1.
    # The right semi-span occupies indices n .. 2n-1.
    # This results in a continuous -tip to +tip spanwise ordering.
    # ------------------------------------------------------------------
    xA = np.concatenate([xA_l, xA_r])
    yA = np.concatenate([yA_l, yA_r])
    zA = np.concatenate([zA_l, zA_r])

    xB = np.concatenate([xB_l, xB_r])
    yB = np.concatenate([yB_l, yB_r])
    zB = np.concatenate([zB_l, zB_r])

    xC = np.concatenate([xC_l, xC_r])
    yC = np.concatenate([yC_l, yC_r])
    zC = np.concatenate([zC_l, zC_r])

    nx = np.concatenate([nx_l, nx_r])
    ny = np.concatenate([ny_l, ny_r])
    nz = np.concatenate([nz_l, nz_r])

    chord_cp_full = np.concatenate([chord_cp_l, wing.chord_cp])
    y_cp_full = np.concatenate([yC_l, yC_r])

    # ------------------------------------------------------------------
    # Step 8: Reference area (full span, trapz over right semi-span * 2)
    # ------------------------------------------------------------------
    S_ref = float(np.trapezoid(wing.chord_cp, wing.y_cp)) * 2.0

    return PanelMesh(
        n_panels=2 * n,
        xA=xA,
        yA=yA,
        zA=zA,
        xB=xB,
        yB=yB,
        zB=zB,
        xC=xC,
        yC=yC,
        zC=zC,
        nx=nx,
        ny=ny,
        nz=nz,
        chord_cp=chord_cp_full,
        y_cp=y_cp_full,
        S_ref=S_ref,
    )


def _camber_slope_at_3qc(airfoil) -> float:
    """Camberline slope dz_c/dx at x=0.75c for a single AirfoilSection.

    See: docs/theory/aerodynamics.md

    Args:
        airfoil: AirfoilSection instance.

    Returns:
        float: Camberline slope.
    """
    if airfoil._M is not None:
        # Analytic NACA 4-digit aft-segment slope (NACA Report 460, Eq. 5 diff.)
        M = airfoil._M
        P = airfoil._P
        if M <= 0.0:
            return 0.0
        return float((M / (1.0 - P) ** 2) * (2.0 * P - 1.5))
    else:
        # UIUC tabulated: finite difference at x=0.75c
        x_fd = np.array([0.74, 0.76])
        z = airfoil.camber_at(x_fd)
        return float((z[1] - z[0]) / 0.02)
