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

"""Airfoil section primitives for Foundation.

See: docs/theory/index.md for detailed NACA equations and interpolation logic.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import numpy as np


def naca4_camber(x: np.ndarray, M: float, P: float) -> np.ndarray:
    """NACA 4-digit camberline ordinate z_c/c.

    Args:
        x: Chordwise stations x/c in [0, 1].
        M: Maximum camber as fraction of chord.
        P: Chordwise position of maximum camber.

    Returns:
        Camberline ordinate z_c/c.
    """
    x = np.asarray(x, dtype=float)
    if M <= 0.0:
        return np.zeros_like(x)
    yc = np.where(
        x < P,
        (M / P**2) * (2.0 * P * x - x**2),
        (M / (1.0 - P) ** 2) * (1.0 - 2.0 * P + 2.0 * P * x - x**2),
    )
    return yc


def naca4_thickness(x: np.ndarray, T: float) -> np.ndarray:
    """NACA 4-digit half-thickness distribution t/c.

    Args:
        x: Chordwise stations x/c in [0, 1].
        T: Maximum thickness as fraction of chord.

    Returns:
        Half-thickness t/c. Full thickness = 2 * returned value.
    """
    x = np.asarray(x, dtype=float)
    yt = (T / 0.2) * (0.2969 * np.sqrt(np.maximum(x, 0.0)) - 0.1260 * x - 0.3516 * x**2 + 0.2843 * x**3 - 0.1015 * x**4)
    return yt


@dataclass
class AirfoilSection:
    """Airfoil section with camber and thickness query methods.

    See: docs/theory/index.md for theoretical background and NACA parsing details.
    """

    _M: float | None = field(default=None, repr=False)
    _P: float | None = field(default=None, repr=False)
    _T: float | None = field(default=None, repr=False)

    _x_upper: np.ndarray | None = field(default=None, repr=False)
    _y_upper: np.ndarray | None = field(default=None, repr=False)
    _x_lower: np.ndarray | None = field(default=None, repr=False)
    _y_lower: np.ndarray | None = field(default=None, repr=False)

    @classmethod
    def from_naca4(cls, designation: str) -> AirfoilSection:
        """Construct from NACA 4-digit string, e.g. '2412'."""
        d = designation.strip().upper().replace("NACA", "").strip()
        if len(d) != 4:
            raise ValueError(f"Expected 4-digit NACA designation, got {designation!r}")
        M = int(d[0]) / 100.0
        P = int(d[1]) / 10.0
        T = int(d[2:]) / 100.0
        return cls(_M=M, _P=P if P > 0.0 else 0.4, _T=T)

    def camber_at(self, x_over_c: np.ndarray) -> np.ndarray:
        """Camberline ordinate z_c/c at chordwise positions x/c."""
        x = np.asarray(x_over_c, dtype=float)
        if x.min() < 0.0 or x.max() > 1.0:
            raise ValueError("x_over_c values must be in [0, 1]")
        if self._M is not None:
            return naca4_camber(x, self._M, self._P)
        yu = np.interp(x, self._x_upper, self._y_upper)
        yl = np.interp(x, self._x_lower, self._y_lower)
        return 0.5 * (yu + yl)

    def thickness_at(self, x_over_c: np.ndarray) -> np.ndarray:
        """Full thickness t/c at chordwise positions x/c."""
        x = np.asarray(x_over_c, dtype=float)
        if self._T is not None:
            return 2.0 * naca4_thickness(x, self._T)
        yu = np.interp(x, self._x_upper, self._y_upper)
        yl = np.interp(x, self._x_lower, self._y_lower)
        return yu - yl

    def get_profile(self, n_points: int = 50) -> tuple[np.ndarray, np.ndarray]:
        """Return (x, z) coordinates for a closed profile, normalized to chord=1."""
        x = np.linspace(0, 1, n_points)
        if self._T is not None:
            zc = naca4_camber(x, self._M, self._P)
            zt = naca4_thickness(x, self._T)
            z_upper = zc + zt
            z_lower = zc - zt
        else:
            yu = np.interp(x, self._x_upper, self._y_upper)
            yl = np.interp(x, self._x_lower, self._y_lower)
            z_upper = yu
            z_lower = yl

        x_full = np.concatenate([x, x[::-1]])
        z_full = np.concatenate([z_upper, z_lower[::-1]])
        return x_full, z_full


def load_uiuc_dat(path: Path) -> AirfoilSection:
    """Load airfoil coordinates from a UIUC .dat file (Selig or Lednicer format).

    See: docs/theory/index.md for format details.
    """
    path = Path(path)
    lines = path.read_text().splitlines()

    data_lines = []
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        try:
            parts = stripped.split()
            floats = [float(p) for p in parts]
            data_lines.append(floats)
        except ValueError:
            continue

    if not data_lines:
        raise ValueError(f"No coordinate data found in {path}")

    first_line = data_lines[0]
    is_lednicer = len(first_line) == 2 and 1.0 < first_line[0] < 500.0 and 1.0 < first_line[1] < 500.0

    if is_lednicer:
        n_upper = int(round(first_line[0]))
        n_lower = int(round(first_line[1]))
        coords = data_lines[1:]
        upper = np.array(coords[:n_upper])
        lower = np.array(coords[n_upper : n_upper + n_lower])
        x_upper, y_upper = upper[:, 0], upper[:, 1]
        x_lower, y_lower = lower[:, 0], lower[:, 1]
    else:
        coords = np.array(data_lines)
        x_all = coords[:, 0]
        y_all = coords[:, 1]
        le_idx = int(np.argmin(x_all))
        x_upper = x_all[: le_idx + 1][::-1]
        y_upper = y_all[: le_idx + 1][::-1]
        x_lower = x_all[le_idx:]
        y_lower = y_all[le_idx:]

    x_max = max(float(x_upper.max()), float(x_lower.max()))
    if x_max > 1.01:
        x_upper = x_upper / x_max
        y_upper = y_upper / x_max
        x_lower = x_lower / x_max
        y_lower = y_lower / x_max

    return AirfoilSection(
        _x_upper=x_upper,
        _y_upper=y_upper,
        _x_lower=x_lower,
        _y_lower=y_lower,
    )


def interpolate_camber(
    y_query: float,
    y_stations: np.ndarray,
    sections: list[AirfoilSection],
    x_over_c: np.ndarray,
) -> np.ndarray:
    """Linear interpolation of camberline ordinates between spanwise stations.

    See: docs/theory/index.md for the blending formula.
    """
    y_stations = np.asarray(y_stations, dtype=float)
    x_over_c = np.asarray(x_over_c, dtype=float)
    y_query = float(np.clip(y_query, y_stations[0], y_stations[-1]))

    idx = np.searchsorted(y_stations, y_query, side="right") - 1
    idx = int(np.clip(idx, 0, len(y_stations) - 2))

    y0 = float(y_stations[idx])
    y1 = float(y_stations[idx + 1])

    if y1 == y0:
        return sections[idx].camber_at(x_over_c)

    alpha = (y_query - y0) / (y1 - y0)
    camber_0 = sections[idx].camber_at(x_over_c)
    camber_1 = sections[idx + 1].camber_at(x_over_c)

    return (1.0 - alpha) * camber_0 + alpha * camber_1


def blended_profile(
    y_query: float,
    y_stations: np.ndarray,
    sections: list,
    n_points: int,
) -> tuple[np.ndarray, np.ndarray]:
    """Linearly blend normalized airfoil profiles between two spanwise stations."""
    y_stations = np.asarray(y_stations, dtype=float)
    y_query = float(np.clip(y_query, y_stations[0], y_stations[-1]))

    idx = int(
        np.clip(
            np.searchsorted(y_stations, y_query, side="right") - 1,
            0,
            len(y_stations) - 2,
        )
    )
    y0, y1 = float(y_stations[idx]), float(y_stations[idx + 1])
    alpha = 0.0 if y1 == y0 else (y_query - y0) / (y1 - y0)

    x0, z0 = sections[idx].get_profile(n_points)
    x1, z1 = sections[idx + 1].get_profile(n_points)

    return (1.0 - alpha) * x0 + alpha * x1, (1.0 - alpha) * z0 + alpha * z1
