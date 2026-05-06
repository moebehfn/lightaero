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

"""NASA uCRM isolated wing geometry builder.

See: docs/theory/index.md for uCRM planform parameters and references.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from lightaero.geometry.airfoil import AirfoilSection
from lightaero.geometry.wing import WingGeometry, build_wing_geometry

# Info taken from AIAA paper 2008-6919 by Vassberg
_UCRM_COLUMNS = [
    "eta",
    "xle",
    "yle",
    "zle",
    "twist",
    "c-plan",
    "t/c",
    "camber/c",
    "dz/c-te",
]
# fmt: off
_UCRM_POINTS = np.array(
    [
        [0.0 ,  904.294,    0.0  , 174.126,  6.7166, 536.181, 0.1542, 0.0003, 0.001 ],
        # [0.1 ,  989.505,  115.675, 175.722,  4.4402, 468.511, 0.138 , 0.0012, 0.0011],
        # [0.15, 1032.133,  173.513, 176.834,  3.6063, 434.674, 0.128 , 0.0018, 0.0012],
        # [0.2 ,  1076.03,  231.351, 177.361,  3.0131, 400.835, 0.1198, 0.0025, 0.0013],
        # [0.25, 1120.128,  289.188, 177.912,  2.2419, 366.996, 0.1137, 0.0037, 0.0014],
        # [0.3 , 1164.153,  347.026, 178.886,  1.5252, 333.157, 0.1092, 0.0061, 0.0016],
        # [0.35, 1208.203,  404.864, 180.359,  0.9379, 299.317, 0.106 , 0.0085, 0.0017],
        [0.37,  1225.82,  427.999, 181.071,  0.7635, 285.782, 0.1052, 0.0095, 0.0018],
        # [0.4 , 1252.246,  462.701, 182.289,  0.4285, 277.288, 0.1038, 0.0107, 0.0019],
        # [0.45, 1296.289,  520.539, 184.904, -0.2621, 263.13 , 0.1019, 0.0122, 0.002 ],
        # [0.5 , 1340.329,  578.377, 188.389, -0.6782, 248.973, 0.1   , 0.0136, 0.0021],
        # [0.55, 1384.375,  636.214, 192.736, -0.9436, 234.816, 0.0988, 0.0146, 0.0022],
        # [0.6 , 1428.416,  694.052, 197.689, -1.2067, 220.658, 0.0978, 0.0152, 0.0023],
        # [0.65, 1472.458,  751.89 , 203.294, -1.4526, 206.501, 0.097 , 0.0154, 0.0025],
        # [0.7 , 1516.504,  809.727, 209.794, -1.635 , 192.344, 0.0962, 0.0158, 0.0027],
        # [0.75, 1560.544,  867.565, 217.084, -1.8158, 178.186, 0.0958, 0.0161, 0.0029],
        # [0.8 , 1604.576,  925.402, 225.188, -2.0301, 164.029, 0.0955, 0.0162, 0.0031],
        # [0.85, 1648.616,  983.24 , 234.082, -2.2772, 149.872, 0.0953, 0.0161, 0.0034],
        # [0.9 , 1692.659, 1041.078, 243.635, -2.5773, 135.714, 0.0952, 0.0155, 0.0038],
        # [0.95, 1736.701, 1098.915, 253.691, -3.1248, 121.557, 0.0951, 0.0127, 0.0042],
        [1.0 , 1780.737, 1156.753, 263.827, -3.75  , 107.4  , 0.095 , 0.0009, 0.0048],
    ]
)
# fmt: on

_UCRM_GEOMETRY = pd.DataFrame(_UCRM_POINTS, columns=_UCRM_COLUMNS)

_INCH_TO_METERS = 0.0254

UCRM_S_REF = 594720.00 * _INCH_TO_METERS**2
UCRM_C_REF = 275.80 * _INCH_TO_METERS
UCRM_HALF_SPAN = 1156.75 * _INCH_TO_METERS
UCRM_AR = 4 * UCRM_HALF_SPAN**2 / UCRM_S_REF
UCRM_SWEEP_LE = np.deg2rad(35.00)
UCRM_TAPER = 0.28

UCRM_NSTATIONS = len(_UCRM_GEOMETRY)

UCRM_ROOT_CHORD = _UCRM_GEOMETRY["c-plan"].values[0] * _INCH_TO_METERS
UCRM_TIP_CHORD = _UCRM_GEOMETRY["c-plan"].values[-1] * _INCH_TO_METERS


def build_ucrm_geometry(n_panels: int = 40) -> WingGeometry:
    """Build uCRM geometry (jig/unmodified)."""
    airfoil = AirfoilSection.from_naca4("0015")
    return build_wing_geometry(
        half_span=_UCRM_GEOMETRY["yle"].values[-1] * _INCH_TO_METERS,
        n_panels=n_panels,
        y_stations=_UCRM_GEOMETRY["yle"].values * _INCH_TO_METERS,
        chord=_UCRM_GEOMETRY["c-plan"].values * _INCH_TO_METERS,
        sweep_le=np.full(len(_UCRM_GEOMETRY), UCRM_SWEEP_LE),
        taper=_UCRM_GEOMETRY["c-plan"].values / _UCRM_GEOMETRY["c-plan"].values[0],
        twist=np.deg2rad(_UCRM_GEOMETRY["twist"].values),
        airfoil_sections=tuple([airfoil] * len(_UCRM_GEOMETRY)),
    )
