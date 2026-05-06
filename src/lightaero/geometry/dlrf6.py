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

"""DLR-F6 isolated wing geometry builder.

See: docs/theory/index.md for DLR-F6 planform parameters and references.
"""

from __future__ import annotations

import numpy as np

from lightaero.geometry.airfoil import AirfoilSection
from lightaero.geometry.wing import WingGeometry, build_wing_geometry

# DLR-F6 planform constants - AIAA 2004-0555 / DPW-II
_HALF_SPAN = 23.75
_ROOT_CHORD = 7.757
_BREAK_Y = 8.7875
_BREAK_CHORD = 5.14
_TIP_CHORD = 2.0
_SWEEP_LE = np.radians(27.1)


def build_dlrf6_geometry(n_panels: int = 40) -> WingGeometry:
    """Return the DLR-F6 isolated wing as a WingGeometry.

    Args:
        n_panels: Number of semi-span VLM panels.

    Returns:
        Frozen WingGeometry with DLR-F6 cranked trapezoidal planform.
    """
    root = AirfoilSection.from_naca4("0012")
    brk = AirfoilSection.from_naca4("0012")
    tip = AirfoilSection.from_naca4("0012")
    return build_wing_geometry(
        half_span=_HALF_SPAN,
        n_panels=n_panels,
        y_stations=np.array([0.0, _BREAK_Y, _HALF_SPAN]),
        chord=np.array([_ROOT_CHORD, _BREAK_CHORD, _TIP_CHORD]),
        sweep_le=np.array([_SWEEP_LE, _SWEEP_LE, _SWEEP_LE]),
        taper=np.array([1.0, _BREAK_CHORD / _ROOT_CHORD, _TIP_CHORD / _ROOT_CHORD]),
        twist=np.array([0.0, 0.0, 0.0]),
        airfoil_sections=(root, brk, tip),
    )
