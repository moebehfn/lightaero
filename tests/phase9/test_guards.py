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

import math
import warnings

import numpy as np
import pytest

from lightaero.aerodynamics.solver import VLMDiscipline
from lightaero.geometry import build_ucrm_geometry
from lightaero.schemas.validation import check_regime_validity


def test_check_regime_validity_mach():
    # Mach > 0.3 should warn
    with pytest.warns(UserWarning, match=r"Mach 0.40 exceeds incompressible limit"):
        check_regime_validity(mach=0.4, aoa_rad=0.0)

    # Mach <= 0.3 should not warn
    with warnings.catch_warnings(record=True) as record:
        check_regime_validity(mach=0.3, aoa_rad=0.0)
        assert len(record) == 0


def test_check_regime_validity_aoa():
    # AoA > 10 deg should warn
    with pytest.warns(UserWarning, match=r"AoA 15.0 deg exceeds typical VLM linear limit"):
        check_regime_validity(mach=0.1, aoa_rad=math.radians(15.0))

    with pytest.warns(UserWarning, match=r"AoA -15.0 deg exceeds typical VLM linear limit"):
        check_regime_validity(mach=0.1, aoa_rad=math.radians(-15.0))

    # AoA <= 10 deg should not warn
    with warnings.catch_warnings(record=True) as record:
        check_regime_validity(mach=0.1, aoa_rad=math.radians(10.0))
        assert len(record) == 0


def test_vlm_discipline_integration_mach():
    wing = build_ucrm_geometry()
    vlm = VLMDiscipline()

    # High Mach
    with pytest.warns(UserWarning, match=r"Mach 0.40 exceeds incompressible limit"):
        vlm(wing=wing, alpha_rad=0.0, M=0.4, altitude_m=0.0)


def test_vlm_discipline_integration_aoa():
    wing = build_ucrm_geometry()
    vlm = VLMDiscipline()

    # High AoA
    with pytest.warns(UserWarning, match=r"AoA 15.0 deg exceeds typical VLM linear limit"):
        vlm(wing=wing, alpha_rad=math.radians(15.0), M=0.1, altitude_m=0.0)


def test_vlm_discipline_array_aoa():
    wing = build_ucrm_geometry()
    vlm = VLMDiscipline()

    # High AoA in array
    alpha_rad = np.zeros(wing.n_panels)
    alpha_rad[0] = math.radians(15.0)
    with pytest.warns(UserWarning, match=r"AoA 15.0 deg exceeds typical VLM linear limit"):
        vlm(wing=wing, alpha_rad=alpha_rad, M=0.1, altitude_m=0.0)
