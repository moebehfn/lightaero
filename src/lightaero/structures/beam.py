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

"""Euler-Bernoulli beam FEM kernel.

See: docs/theory/structures.md
"""

from __future__ import annotations

import numpy as np

__all__ = [
    "beam_section_properties",
    "size_skin_thickness",
    "build_bending_loads",
    "build_torsion_loads",
    "solve_bending_beam",
    "solve_torsion_beam",
    "compute_combined_stress",
]

# Wingbox integration limits
_X_START: float = 0.15
_X_END: float = 0.65
_N_PTS: int = 100


def _compute_shear_center_x(
    c: float,
    tc: float,
    t_sk: float,
    I_xx: float,
    x_norm: np.ndarray,
) -> float:
    """Shear center chordwise position via Bredt-Batho method.

    Args:
        c: Chord length (m).
        tc: Thickness-to-chord ratio.
        t_sk: Skin thickness (m).
        I_xx: Second moment of area about horizontal axis (m⁴).
        x_norm: Normalised chordwise integration grid.

    Returns:
        x_sc: Shear center chordwise position (m) from the leading edge.
    """
    if I_xx < 1e-30:
        return c * 0.40  # fallback

    y_norm = (
        5.0
        * tc
        * (0.2969 * np.sqrt(x_norm) - 0.1260 * x_norm - 0.3516 * x_norm**2 + 0.2843 * x_norm**3 - 0.1015 * x_norm**4)
    )
    x_u = x_norm * c  # upper skin x coords
    y_u = y_norm * c  # upper skin y coords (positive)

    # Build section outline counter-clockwise:
    # [upper skin] + [rear spar top→bottom] + [lower skin] + [front spar bottom→top]
    n_rs = 10

    # Rear spar (vertical)
    rs_y = np.linspace(y_u[-1], -y_u[-1], n_rs + 1)
    rs_x = np.full(n_rs + 1, x_u[-1])

    # Lower skin
    xl = x_u[::-1]
    yl = -y_u[::-1]

    # Front spar (vertical)
    fs_y = np.linspace(-y_u[0], y_u[0], n_rs + 1)
    fs_x = np.full(n_rs + 1, x_u[0])

    X = np.concatenate([x_u, rs_x[1:], xl[1:], fs_x[1:]])
    Y = np.concatenate([y_u, rs_y[1:], yl[1:], fs_y[1:]])

    dx = np.diff(X)
    dy = np.diff(Y)
    ds = np.sqrt(dx**2 + dy**2)
    xm = 0.5 * (X[:-1] + X[1:])
    ym = 0.5 * (Y[:-1] + Y[1:])

    Qx_cum = np.cumsum(t_sk * ym * ds)
    qb = -Qx_cum / I_xx
    q0 = -np.dot(qb, ds) / np.sum(ds)
    q_total = qb + q0

    M = float(np.dot(q_total, xm * dy - ym * dx))
    return M


def _bending_moment_from_loads(y_nodes: np.ndarray, q_nodes: np.ndarray) -> np.ndarray:
    """Bending moment distribution for a cantilever with distributed load.

    Args:
        y_nodes: Spanwise node positions (m).
        q_nodes: Distributed transverse load at each node (N/m).

    Returns:
        M: Bending moment at each node (N·m).
    """
    n = len(y_nodes)
    V = np.zeros(n)
    for i in range(n - 2, -1, -1):
        dy = y_nodes[i + 1] - y_nodes[i]
        V[i] = V[i + 1] + 0.5 * (q_nodes[i] + q_nodes[i + 1]) * dy
    M = np.zeros(n)
    for i in range(n - 2, -1, -1):
        dy = y_nodes[i + 1] - y_nodes[i]
        M[i] = M[i + 1] + 0.5 * (V[i] + V[i + 1]) * dy
    return M


def size_skin_thickness(
    y_nodes: np.ndarray,
    chord_nodes: np.ndarray,
    tc_ratio_nodes: np.ndarray,
    q_z_nodes: np.ndarray,
    sigma_yield: float = 324e6,
    SF: float = 1.5,
    t_sk_min: float = 0.001,
) -> np.ndarray:
    """Size wing skin thickness to satisfy bending stress allowable.

    Args:
        y_nodes: Spanwise node positions (m).
        chord_nodes: Chord length at each node (m).
        tc_ratio_nodes: t/c ratio at each node.
        q_z_nodes: Distributed vertical load (N/m) at each node.
        sigma_yield: Tensile yield stress (Pa).
        SF: Safety factor.
        t_sk_min: Minimum skin thickness (m).

    Returns:
        t_sk: Sized skin thickness at each node (m).
    """
    sigma_allow = sigma_yield / SF
    M = _bending_moment_from_loads(y_nodes, q_z_nodes)
    x_norm = np.linspace(_X_START, _X_END, _N_PTS)

    n_nodes = len(chord_nodes)
    t_sk = np.full(n_nodes, t_sk_min)

    for i in range(n_nodes):
        c = chord_nodes[i]
        tc = tc_ratio_nodes[i]

        y_norm = (
            5.0
            * tc
            * (
                0.2969 * np.sqrt(x_norm)
                - 0.1260 * x_norm
                - 0.3516 * x_norm**2
                + 0.2843 * x_norm**3
                - 0.1015 * x_norm**4
            )
        )
        x = x_norm * c
        y = y_norm * c
        h = 2.0 * y
        h_max_i = float(np.max(h))
        h_f = float(h[0])
        h_r = float(h[-1])

        ds = np.sqrt(np.diff(x) ** 2 + np.diff(y) ** 2)
        y_mid = 0.5 * (y[:-1] + y[1:])

        I_xx_unit = 2.0 * float(np.sum(y_mid**2 * ds)) + (1.0 / 12.0) * h_f**3 + (1.0 / 12.0) * h_r**3

        if I_xx_unit > 0.0 and h_max_i > 0.0:
            t_req = abs(M[i]) * (h_max_i / 2.0) / (I_xx_unit * sigma_allow)
            t_sk[i] = max(t_sk_min, t_req)

    return t_sk


def beam_section_properties(
    y_nodes: np.ndarray,
    chord_nodes: np.ndarray,
    tc_ratio_nodes: np.ndarray,
    E_Pa: float = 73.1e9,
    G_Pa: float = 28.0e9,
    t_sk_array: np.ndarray | None = None,
) -> tuple:
    """Thin-walled wingbox section properties via numerical integration.

    Args:
        y_nodes: Spanwise node positions (m).
        chord_nodes: Chord at each node (m).
        tc_ratio_nodes: t/c ratio at each node.
        E_Pa: Young's modulus (Pa).
        G_Pa: Shear modulus (Pa).
        t_sk_array: Optional skin thickness at each node (m).

    Returns:
        (EI_xx, EI_zz, GJ, h_max, w_box, I_xx, I_zz, A_e, x_sc): each shape (n,).
    """
    n_nodes = len(chord_nodes)
    EI_xx = np.zeros(n_nodes)
    EI_zz = np.zeros(n_nodes)
    GJ = np.zeros(n_nodes)
    h_max = np.zeros(n_nodes)
    w_box = np.zeros(n_nodes)
    I_xx_out = np.zeros(n_nodes)
    I_zz_out = np.zeros(n_nodes)
    A_e_out = np.zeros(n_nodes)
    x_sc_out = np.zeros(n_nodes)

    x_norm = np.linspace(_X_START, _X_END, _N_PTS)

    for i in range(n_nodes):
        c = chord_nodes[i]
        tc = tc_ratio_nodes[i]
        t_sk = t_sk_array[i] if t_sk_array is not None else (tc * c) / 100.0

        y_norm = (
            5.0
            * tc
            * (
                0.2969 * np.sqrt(x_norm)
                - 0.1260 * x_norm
                - 0.3516 * x_norm**2
                + 0.2843 * x_norm**3
                - 0.1015 * x_norm**4
            )
        )

        x = x_norm * c
        y = y_norm * c
        h = 2.0 * y

        h_f = h[0]
        h_r = h[-1]

        h_max[i] = np.max(h)
        w_box[i] = c * (_X_END - _X_START)

        dx = np.diff(x)
        dy = np.diff(y)
        ds = np.sqrt(dx**2 + dy**2)

        y_mid = 0.5 * (y[:-1] + y[1:])
        x_mid = 0.5 * (x[:-1] + x[1:])

        I_xx_upper = np.sum(t_sk * y_mid**2 * ds)
        I_xx_fs = (1.0 / 12.0) * t_sk * h_f**3
        I_xx_rs = (1.0 / 12.0) * t_sk * h_r**3
        I_xx = 2.0 * I_xx_upper + I_xx_fs + I_xx_rs

        A_skin = np.sum(t_sk * ds)
        A_fs = t_sk * h_f
        A_rs = t_sk * h_r
        A_tot = 2.0 * A_skin + A_fs + A_rs

        x_centroid = (2.0 * np.sum(x_mid * t_sk * ds) + x[0] * A_fs + x[-1] * A_rs) / A_tot

        I_zz_upper = np.sum(t_sk * (x_mid - x_centroid) ** 2 * ds)
        I_zz_fs = A_fs * (x[0] - x_centroid) ** 2
        I_zz_rs = A_rs * (x[-1] - x_centroid) ** 2
        I_zz = 2.0 * I_zz_upper + I_zz_fs + I_zz_rs

        A_e = np.trapezoid(h, x)
        perimeter = 2.0 * np.sum(ds) + h_f + h_r
        J = (4.0 * A_e**2 * t_sk) / perimeter

        EI_xx[i] = E_Pa * I_xx
        EI_zz[i] = E_Pa * I_zz
        GJ[i] = G_Pa * J
        I_xx_out[i] = I_xx
        I_zz_out[i] = I_zz
        A_e_out[i] = A_e
        x_sc_out[i] = _compute_shear_center_x(c, tc, t_sk, I_xx, x_norm)

    return EI_xx, EI_zz, GJ, h_max, w_box, I_xx_out, I_zz_out, A_e_out, x_sc_out


def build_bending_loads(y_nodes: np.ndarray, q_nodes: np.ndarray) -> np.ndarray:
    """Build FEM load vector for bending.

    Args:
        y_nodes: Spanwise node positions (m).
        q_nodes: Distributed transverse load (N/m).

    Returns:
        F: Load vector (N and N·m).
    """
    n_nodes = len(y_nodes)
    F = np.zeros(2 * n_nodes)
    for i in range(n_nodes - 1):
        L_e = y_nodes[i + 1] - y_nodes[i]
        q_avg = 0.5 * (q_nodes[i] + q_nodes[i + 1])
        F[2 * i] += q_avg * L_e / 2.0
        F[2 * i + 1] += q_avg * L_e**2 / 12.0
        F[2 * i + 2] += q_avg * L_e / 2.0
        F[2 * i + 3] -= q_avg * L_e**2 / 12.0
    return F


def build_torsion_loads(y_nodes: np.ndarray, t_nodes: np.ndarray) -> np.ndarray:
    """Build FEM load vector for torsion.

    Args:
        y_nodes: Spanwise node positions (m).
        t_nodes: Distributed torque (N·m/m).

    Returns:
        T: Load vector (N·m).
    """
    n_nodes = len(y_nodes)
    T = np.zeros(n_nodes)
    for i in range(n_nodes - 1):
        L_e = y_nodes[i + 1] - y_nodes[i]
        t_avg = 0.5 * (t_nodes[i] + t_nodes[i + 1])
        T[i] += t_avg * L_e / 2.0
        T[i + 1] += t_avg * L_e / 2.0
    return T


def solve_bending_beam(y_nodes: np.ndarray, EI: np.ndarray, F: np.ndarray) -> np.ndarray:
    """Solve FEM beam bending equations.

    Args:
        y_nodes: Spanwise node positions (m).
        EI: Bending stiffness at nodes (N·m²).
        F: Load vector.

    Returns:
        d: Displacement vector (m and rad).
    """
    n_nodes = len(y_nodes)
    K = np.zeros((2 * n_nodes, 2 * n_nodes))

    for i in range(n_nodes - 1):
        L_e = y_nodes[i + 1] - y_nodes[i]
        EI_e = 0.5 * (EI[i] + EI[i + 1])
        c = EI_e / L_e**3
        k = c * np.array(
            [
                [12.0, 6.0 * L_e, -12.0, 6.0 * L_e],
                [6.0 * L_e, 4.0 * L_e**2, -6.0 * L_e, 2.0 * L_e**2],
                [-12.0, -6.0 * L_e, 12.0, -6.0 * L_e],
                [6.0 * L_e, 2.0 * L_e**2, -6.0 * L_e, 4.0 * L_e**2],
            ]
        )
        idx = [2 * i, 2 * i + 1, 2 * i + 2, 2 * i + 3]
        for r in range(4):
            for col in range(4):
                K[idx[r], idx[col]] += k[r, col]

    K_ff = K[2:, 2:]
    F_f = F[2:]
    d_free = np.linalg.solve(K_ff, F_f)
    return np.concatenate(([0.0, 0.0], d_free))


def solve_torsion_beam(y_nodes: np.ndarray, GJ: np.ndarray, T: np.ndarray) -> np.ndarray:
    """Solve FEM beam torsion equations.

    Args:
        y_nodes: Spanwise node positions (m).
        GJ: Torsional stiffness at nodes (N·m²).
        T: Torque load vector (N·m).

    Returns:
        phi: Twist angle vector (rad).
    """
    n_nodes = len(y_nodes)
    K = np.zeros((n_nodes, n_nodes))
    for i in range(n_nodes - 1):
        L_e = y_nodes[i + 1] - y_nodes[i]
        GJ_e = 0.5 * (GJ[i] + GJ[i + 1])
        k = (GJ_e / L_e) * np.array([[1.0, -1.0], [-1.0, 1.0]])
        K[i : i + 2, i : i + 2] += k

    K_ff = K[1:, 1:]
    T_f = T[1:]
    phi_free = np.linalg.solve(K_ff, T_f)
    return np.concatenate(([0.0], phi_free))


def compute_combined_stress(
    y_nodes: np.ndarray,
    w_full: np.ndarray,
    u_full: np.ndarray,
    EI_xx: np.ndarray,
    EI_zz: np.ndarray,
    h: np.ndarray,
    w: np.ndarray,
    I_xx: np.ndarray,
    I_zz: np.ndarray,
    phi_full: np.ndarray | None = None,
    GJ: np.ndarray | None = None,
    A_e: np.ndarray | None = None,
    t_sk: np.ndarray | None = None,
) -> np.ndarray:
    """Von Mises stress at each spanwise node.

    See: docs/theory/structures.md

    Args:
        y_nodes (np.ndarray): Spanwise node positions (m).
        w_full (np.ndarray): Bending DOF vector (vertical).
        u_full (np.ndarray): Bending DOF vector (lateral).
        EI_xx (np.ndarray): Bending stiffness array about xx.
        EI_zz (np.ndarray): Bending stiffness array about zz.
        h (np.ndarray): Section height at each node (m).
        w (np.ndarray): Section width at each node (m).
        I_xx (np.ndarray): Second moment of area about xx (m^4).
        I_zz (np.ndarray): Second moment of area about zz (m^4).
        phi_full (np.ndarray | None): Torsion DOF vector. Optional.
        GJ (np.ndarray | None): Torsional stiffness array. Optional.
        A_e (np.ndarray | None): Enclosed wingbox area at each node (m²). Optional.
        t_sk (np.ndarray | None): Skin thickness at each node (m). Optional.

    Returns:
        np.ndarray: Von Mises stress at each node (Pa).
    """
    n_nodes = len(y_nodes)
    stress = np.zeros(n_nodes)
    use_torsion = phi_full is not None and GJ is not None and A_e is not None and t_sk is not None

    for i in range(n_nodes - 1):
        L_e = y_nodes[i + 1] - y_nodes[i]

        EI_xx_e = 0.5 * (EI_xx[i] + EI_xx[i + 1])
        w_A, th_A, w_B, th_B = w_full[2 * i : 2 * i + 4]
        kappa_x = (6.0 * (w_A - w_B) / L_e**2) + (4.0 * th_A + 2.0 * th_B) / L_e
        M_x = EI_xx_e * kappa_x

        EI_zz_e = 0.5 * (EI_zz[i] + EI_zz[i + 1])
        u_A, thz_A, u_B, thz_B = u_full[2 * i : 2 * i + 4]
        kappa_z = (6.0 * (u_A - u_B) / L_e**2) + (4.0 * thz_A + 2.0 * thz_B) / L_e
        M_z = EI_zz_e * kappa_z

        sigma_b = abs(M_x) * (h[i] / 2.0) / max(I_xx[i], 1e-30) + abs(M_z) * (w[i] / 2.0) / max(I_zz[i], 1e-30)

        if use_torsion:
            GJ_e = 0.5 * (GJ[i] + GJ[i + 1])
            T_elem = GJ_e * (phi_full[i + 1] - phi_full[i]) / L_e
            denom = 2.0 * max(A_e[i], 1e-30) * max(t_sk[i], 1e-9)
            tau = abs(T_elem) / denom
            sigma_vm = (sigma_b**2 + 3.0 * tau**2) ** 0.5
        else:
            sigma_vm = sigma_b

        if sigma_vm > stress[i]:
            stress[i] = sigma_vm

    return stress
