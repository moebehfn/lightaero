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

"""Aerodynamics discipline subpackage for lightaero.

Provides VLM and aeroelastic solvers.
See: docs/theory/aerodynamics.md
"""

# triggers @register('aerostruct', 'vlm_euler_beam')
from lightaero.aerodynamics.aeroelastic import AerostructDiscipline, AerostructOutput

# triggers @register('aero', 'vlm')
from lightaero.aerodynamics.solver import VLMDiscipline

__all__ = ["VLMDiscipline", "AerostructDiscipline", "AerostructOutput"]
