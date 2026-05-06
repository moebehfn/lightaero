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

"""ISA atmosphere model (ISO 2533 / ICAO Doc 7488).

See: docs/theory/atmosphere.md
"""

import math

import numba

# ---------------------------------------------------------------------------
# ISA constants (ISO 2533 exact values - do not modify)
# ---------------------------------------------------------------------------
_T0: float = 288.15  # K - sea-level temperature
_p0: float = 101325.0  # Pa - sea-level pressure
_R: float = 287.05287  # J/(kg·K) - specific gas constant for dry air
_g0: float = 9.80665  # m/s2 - standard gravity (exact)
_L: float = 0.0065  # K/m - troposphere temperature lapse rate (exact)
_gamma: float = 1.4  # ratio of specific heats

# Tropopause boundary
_H_tp: float = 11000.0  # m - exact ISA tropopause base altitude
_T_tp: float = 216.65  # K - exact tropopause temperature (= T0 - L * H_tp)
_exp_tp: float = _g0 / (_R * _L)  # barometric exponent (≈ 5.2559)

# Tropopause base values - computed once as module constants to avoid
# floating-point discontinuity at the boundary.
_p_tp: float = _p0 * (_T_tp / _T0) ** _exp_tp  # Pa - ≈ 22632.1
_rho_tp: float = _p_tp / (_R * _T_tp)  # kg/m3 - ≈ 0.36392
_a_tp: float = (_gamma * _R * _T_tp) ** 0.5  # m/s - ≈ 295.07


@numba.njit(cache=True)
def _isa_scalar(h: float):
    """Scalar ISA - runs in nopython mode.

    See: docs/theory/atmosphere.md

    Args:
        h: Geometric altitude above MSL in metres.

    Returns:
        tuple: (rho, T, p, a)
    """
    if h < _H_tp:
        T = _T0 - _L * h
        p = _p0 * (T / _T0) ** _exp_tp
        rho = p / (_R * T)
        a = (_gamma * _R * T) ** 0.5
    else:
        T = _T_tp
        p = _p_tp * math.exp(-_g0 * (h - _H_tp) / (_R * _T_tp))
        rho = p / (_R * _T_tp)
        a = _a_tp
    return rho, T, p, a


def isa(altitude_m: float) -> tuple[float, float, float, float]:
    """ISA atmosphere at the given altitude above MSL.

    See: docs/theory/atmosphere.md

    Args:
        altitude_m: Geometric altitude in metres.

    Returns:
        tuple: (rho, T, p, a)
    """
    return _isa_scalar(float(altitude_m))
