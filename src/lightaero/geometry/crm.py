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

"""NASA Common Research Model (CRM) isolated wing geometry builder.

See: docs/theory/index.md for CRM planform parameters and references.
"""

from __future__ import annotations

import numpy as np

from lightaero.geometry.airfoil import AirfoilSection
from lightaero.geometry.wing import WingGeometry, build_wing_geometry

# NASA CRM planform constants (scaled k≈0.42765 to match S_ref=383.7 m²)
_CRM_HALF_SPAN: float = 29.4
_CRM_ROOT_CHORD: float = 13.566 * 0.42765
_CRM_TIP_CHORD: float = 2.733 * 0.42765
_CRM_SWEEP_LE: float = np.radians(27.1)


def build_crm_geometry(n_panels: int = 40) -> WingGeometry:
    """Build NASA CRM wing geometry (trapezoidal approximation)."""
    airfoil = AirfoilSection.from_naca4("0012")
    return build_wing_geometry(
        half_span=_CRM_HALF_SPAN,
        n_panels=n_panels,
        y_stations=np.array([0.0, _CRM_HALF_SPAN]),
        chord=np.array([_CRM_ROOT_CHORD, _CRM_TIP_CHORD]),
        sweep_le=np.array([_CRM_SWEEP_LE, _CRM_SWEEP_LE]),
        taper=np.array([1.0, _CRM_TIP_CHORD / _CRM_ROOT_CHORD]),
        twist=np.zeros(2),
        airfoil_sections=(airfoil, airfoil),
    )
